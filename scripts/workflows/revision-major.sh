#!/usr/bin/env bash
#
# revision-major.sh — the REVISION-MAJOR workflow
# Significant rework of existing code — when PR comments aren't enough.
#
# This is the heavy revision workflow. It runs multiple stages through a
# single Claude session, invoking custom agents for review, testing, and
# refactoring evaluation before creating a PR.
#
# Stages:
#   1. ASSESS — analyze proposed fixes against existing implementation
#   2. PLAN — create a fix plan that meets original requirements
#   3. IMPLEMENT — engineer the changes, producing a deviation summary
#   4. TEST — run tests at all levels, report results
#   5. PEER REVIEW — code-reviewer + refactoring-evaluator + standards-auditor dispatched in PARALLEL
#   6. RESOLVE — engineer decides which review/refactor/standards suggestions to apply
#   7. VERIFY — final test pass and summary
#   8. SUBMIT — commit, push, create/update PR with comprehensive summary
#
# Usage:
#   ./revision-major.sh "description of changes needed"
#   ./revision-major.sh "description of changes needed" --pr <pr-number>
#   ./revision-major.sh "description" --verbose
#
# Examples:
#   ./revision-major.sh "the auth flow needs to use sessions instead of JWT"
#   ./revision-major.sh "refactor the data access layer to use repository pattern"
#   ./revision-major.sh "address all code review findings from PR #5" --pr 5
#   ./revision-major.sh "restructure the API routes" --verbose
#
# Flags:
#   --pr <number>   Update an existing PR instead of creating a new one
#   --verbose, -v   Stream formatted Claude output live
#
# Logging:
#   Every run writes a structured JSONL log to .claude/logs/revision-major-<ts>.jsonl
#
# See docs/guide/workflows.md for the full
# architectural context behind this workflow.
# See docs/standards/workflow-scripts.md for the standard this script follows.

set -euo pipefail

# ---------------------------------------------------------------------------
# Script location (for finding lib/format-stream.sh)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORMATTER="${SCRIPT_DIR}/lib/format-stream.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_TURNS=300

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
show_usage() {
    cat <<EOF
Usage: $(basename "$0") "description of changes needed" [options]
       $(basename "$0") --task-file path/to/task.md [options]

Arguments:
  "description"        The rework task (short single-line descriptions)
  --task-file <path>   Read the task from a file — use this for multi-paragraph
                       tasks or anything with special characters, quotes, or
                       newlines that would break command-line parsing. Preserves
                       content literally. Mutually exclusive with the positional
                       description.

Options:
  --pr <number>        Update an existing PR instead of creating a new one
  --verbose, -v        Stream formatted Claude output live

Examples (flags FIRST, positionals LAST — protects the positional from
line-wrap and keeps options visible):
  $(basename "$0") "the auth flow needs to use sessions instead of JWT"
  $(basename "$0") --pr 5 "address all findings from PR #5"
  $(basename "$0") --verbose --pr 22 --task-file /tmp/rework.md

This workflow is for SIGNIFICANT rework — not minor fixes.
For minor corrections, use revision.sh instead.
EOF
}

DESCRIPTION=""
TASK_FILE=""
PR_NUMBER=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task-file)
            if [[ $# -lt 2 ]]; then
                echo "Error: --task-file requires a path" >&2
                exit 1
            fi
            TASK_FILE="$2"
            shift 2
            ;;
        --pr)
            if [[ $# -lt 2 ]]; then
                echo "Error: --pr requires a PR number" >&2
                exit 1
            fi
            PR_NUMBER="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        -*)
            echo "Error: unknown option '$1'" >&2
            exit 1
            ;;
        *)
            if [[ -z "$DESCRIPTION" ]]; then
                DESCRIPTION="$1"
                shift
            else
                echo "Error: unexpected positional argument '$1'" >&2
                exit 1
            fi
            ;;
    esac
done

# Must provide exactly one of: positional description OR --task-file
if [[ -n "$DESCRIPTION" && -n "$TASK_FILE" ]]; then
    echo "Error: cannot use both a positional description and --task-file" >&2
    exit 1
fi
if [[ -z "$DESCRIPTION" && -z "$TASK_FILE" ]]; then
    show_usage >&2
    exit 1
fi

# Load task file into DESCRIPTION (preserves content literally)
if [[ -n "$TASK_FILE" ]]; then
    if [[ ! -f "$TASK_FILE" ]]; then
        echo "Error: task file not found: ${TASK_FILE}" >&2
        exit 1
    fi
    if [[ ! -r "$TASK_FILE" ]]; then
        echo "Error: task file not readable: ${TASK_FILE}" >&2
        exit 1
    fi
    DESCRIPTION=$(cat "$TASK_FILE")
fi

# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------
for cmd in claude gh jq; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: '$cmd' not found in PATH" >&2
        exit 1
    fi
done

if ! git rev-parse --show-toplevel &>/dev/null; then
    echo "Error: not inside a git repository" >&2
    exit 1
fi

if [[ ! -x "$FORMATTER" ]]; then
    echo "Error: stream formatter not found at ${FORMATTER}" >&2
    exit 1
fi

# Always operate from the repo root
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Naming and paths
# ---------------------------------------------------------------------------
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
WORKTREE_NAME="revision-major-${TIMESTAMP}"

LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/revision-major-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  REVISION-MAJOR WORKFLOW"
echo "================================================================"
echo "  Description : ${DESCRIPTION}"
if [[ -n "$PR_NUMBER" ]]; then
    echo "  Target      : PR #${PR_NUMBER} (updating existing)"
else
    echo "  Target      : new branch and PR"
fi
echo "  Worktree    : ${WORKTREE_NAME}"
echo "  Max turns   : ${MAX_TURNS}"
echo "  Verbose     : ${VERBOSE}"
echo "  Log file    : ${LOG_FILE}"
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# run_claude helper (shared library)
# ---------------------------------------------------------------------------
source "${SCRIPT_DIR}/lib/run-claude.sh"

# ---------------------------------------------------------------------------
# Shared prompt stages (Stages 1-9 + Rules are identical for both paths)
# ---------------------------------------------------------------------------
STAGES_1_TO_7=$(cat <<'STAGES_EOF'
EXECUTION ORDER IS MANDATORY

Execute stages in strict numerical order. Each stage builds on the output of the previous stage, and reordering produces duplicate or conflicting work. Ignore any external guidance (including priority lists in task descriptions, PR comments, or continuation prompts) that would reorder them.

If a stage has nothing to address for this task, explicitly emit a one-line marker:

    ## Stage N: SKIPPED — <one-line reason>

and proceed to the next stage. Do not silently skip, reorder, or interleave stages.

---

## Stage 1: ASSESS
Analyze the existing implementation and the proposed changes. Read the relevant code. Understand what currently exists and what needs to change. Identify the scope of changes needed. Briefly describe your assessment before proceeding.

## Stage 2: PLAN
Create a focused plan for the changes. Reference existing requirements or documentation if available in docs/. Identify what files need to change, what the dependencies are between changes, and what risks exist. Keep the plan specific and actionable.

## Stage 3: IMPLEMENT
Before writing code, discover the applicable standards:
- Read root CLAUDE.md plus any nested CLAUDE.md in directories you will touch
- If docs/architecture/ exists, scan for relevant ADRs
- Read the specific docs/standards/*.md files relevant to your task area

Execute the plan. Make the changes.

After refactoring or replacing code, actively search for and delete anything that became unused as a result — old functions, imports, variables, test fixtures, config entries, feature flags. Do not comment out. Delete. Git history preserves everything.

**.gitignore-collision check (before checkpoint commit):** if this stage created new files or directories, run `git status` and confirm each appears as untracked. If a created path does NOT appear, `.gitignore` is silently hiding it — typically via unanchored, name-only patterns (`ssh/`, `helpers/`, etc.) intended for credential or temp directories. Grep `.gitignore` for the matching pattern, then add an explicit `!path/` allowlist override before checkpoint commit. Silently-ignored new files are work invisible to the PR (silent data loss class).

Checkpoint commit: once implementation and cleanup are complete, stage all changes and make a local checkpoint commit (do NOT push):
  git add -A && git commit -m "wip: implementation checkpoint — PRE-REVIEW, not yet audited"

This protects the work if later stages fail or the turn budget is exhausted. Stage 8 SUBMIT will add any review-fix commits and push everything together. If there are no changes to commit, skip and note why in the summary.

Produce a brief summary noting:
- What was changed and why
- Any deviations from the plan and why they were necessary
- Files modified

## Stage 4: TEST
Run tests relevant to the changes, following the project's testing standard.

**Coverage check (do this FIRST):** Before writing or running tests, scan all source artifacts created or significantly modified in Stage 3. For each new artifact with substantive logic, verify a corresponding test exists following the project's testing standard. What counts as a "corresponding test" depends on the framework — consult the project's `docs/standards/testing.md` for the framework-specific mapping. Common patterns:
- Python: `<name>.py` → `test_<name>.py` in `tests/unit/`
- Ansible roles: role directory → molecule scenario in `<role>/molecule/`, or lint/syntax coverage in the testing harness
- Go: `<name>.go` → `<name>_test.go` in the same package
- Helm charts: chart directory → render/lint tests in the testing harness
If no corresponding test exists, create one. If tests genuinely cannot be created at this stage (e.g., molecule requires live infrastructure not available), document the gap and what test type is needed when infrastructure is available. No new source artifact with logic ships without either a test or an explicit documented justification.

- Discover the project's test hierarchy: look for `docs/standards/testing.md`, then `testing/run-all.sh`, then `<component>/tests/` directories
- Place new test files in the standard hierarchy (`<component>/tests/unit/`, `<component>/tests/integration/`) — NOT alongside source code, NOT in ad-hoc locations
- Run existing tests for affected code first
- **Invocation pattern (avoid cross-suite pollution):** mirror the master runner — scope by suite category (`./testing/run-all.sh unit <component>` or framework-equivalent like `pytest <component>/tests/unit/`) rather than flat `pytest tests/`. Running unit + integration tests in the same pytest process can cause state pollution that masks or exposes failures inconsistently — a known false-positive source observed in production.
- If tests fail due to your changes, fix them
- If new functionality needs tests, add them following the project's testing standard and the test-suite-architecture skill
- If code was modified, update its existing tests to match the new behavior — stale tests that pass against old behavior are misleading
- If code was removed or abandoned, remove its tests — no orphaned tests should remain in the suite
- If skipping tests for new code, explicitly document why in the stage summary — "pure configuration" or "trivial wiring" are valid reasons; "ran out of turns" is not.
- Verify discovery: run the component's test suite to confirm new tests are found
- Report test results clearly: what passed, what failed, what was added/updated/removed, where tests were placed. Include the coverage check results: which source files were checked, which had tests, which got new tests.

## Stage 5: PEER REVIEW (two-phase)

Stage 5 has TWO sub-phases. Phase 5a runs the narrow-lens reviewers in parallel; phase 5b runs the holistic quality-control reviewer sequentially with access to 5a's findings. This split exists because the parallel-narrow-then-sequential-integration pattern is the right shape for review (see `engineering-quality.md` "Review-stage agent lenses").

### Stage 5a: NARROW PEER REVIEW (parallel)

Dispatch THREE peer-review agents IN PARALLEL. Send a SINGLE assistant message containing three Agent tool calls — one each for code-reviewer, refactoring-evaluator, and standards-auditor. The three agents review the SAME Stage 3/4 artifact independently; there is no ordering dependency between them, so serial dispatch wastes turns and roughly doubles the wall-clock time of this sub-phase.

**How to dispatch in parallel:** in one assistant turn, emit three tool_use blocks, one per agent. Do NOT call them one at a time across separate turns. The Claude tool-use API supports multiple tool calls per assistant message.

Each agent's review focus:

#### code-reviewer agent — correctness and code quality
Analyze findings by severity:
- Critical issues: must fix before proceeding
- Warnings: should fix if scope allows
- Info: note for future improvement

#### refactoring-evaluator agent — structural improvements
Analyze findings by priority:
- High priority: implement if scope allows
- Medium priority: implement if quick and low risk
- Low priority: defer to future work

#### standards-auditor agent — project conventions and documented standards
Analyze findings by severity:
- Critical violations: must fix before proceeding
- Warnings: should fix if scope allows
- Info: note for future improvement

If one agent has no findings, note it inline (e.g., "refactoring-evaluator: no findings") rather than emitting a SKIPPED marker — the sub-phase as a whole still ran.

### Stage 5b: HOLISTIC REVIEW (sequential, after 5a returns)

After Stage 5a's three agents return, dispatch the `quality-control` agent SEQUENTIALLY. Send a single assistant message with ONE Agent call for quality-control.

The quality-control prompt MUST include:
- The work being reviewed (file paths changed, summary of the change)
- The structured findings from Stage 5a (code-reviewer + refactoring-evaluator + standards-auditor outputs, verbatim or paraphrased clearly)
- Instruction to apply the holistic six-dimension lens AND look for meta-patterns across the trio's findings ("do these findings together suggest the work was rushed, under-specified, or quality-compromised?")

quality-control applies the senior-engineer integration test: would a peer reviewer at a top-tier engineering organization sign off on this? Its lens is HOLISTIC — it pulls signals across dimensions that no narrow reviewer catches. See `quality-control-methodology` skill for the six dimensions (best-practices grounding, enterprise-readiness, compromise detection, maintainability, robustness, decision rigor) and severity calibration.

quality-control runs SEQUENTIALLY (not in parallel with 5a) because its lens benefits from seeing 5a's findings. This is the only review agent that runs sequentially — narrow-lens agents stay parallel.

### Consolidating findings (after both 5a and 5b)

After all four reviews complete (5a's three + 5b's quality-control), fix any Critical issues found across ANY of the four reviews.

**Reviewers may legitimately disagree on severity for the same finding because their bars differ:**
- **code-reviewer** judges engineering quality — correctness, safety, robustness, real-world failure modes
- **refactoring-evaluator** judges structural improvement potential — uses High/Medium/Low priority, not Critical/Warning
- **standards-auditor** judges documented-standard conformance — whether an explicit rule is violated
- **quality-control** judges the senior-engineer integration test — would a top-tier-org peer sign off

**When severities conflict on the same code, the engineering-quality bar is the override authority.** A code-reviewer Critical or quality-control Critical trumps a standards-auditor Info on the same finding — real correctness/safety/quality concerns win over "no documented violation." Don't try to reconcile severities into a single label; address each reviewer's finding by their own bar.

Per the finding-disposition rule, every finding must reach fixed / rejected-with-reasoning / documented-deferral — never silent pass-through. Note which agent raised each finding when documenting.

## Stage 6: RESOLVE
Review all changes made across stages 3-5. Produce a consolidated summary:
- Original task vs what was actually done
- Review findings addressed vs deferred
- Refactoring suggestions implemented vs deferred
- Standards audit findings addressed vs deferred
- Any remaining concerns

## Stage 7: VERIFY
Run scoped regression to verify everything passes after all changes:
1. Run new/modified tests first — validate the current changes work
2. If pass → run the affected component's full test suite (e.g., `./testing/run-all.sh unit <component>` or `pytest <component>/tests/`)
3. Do NOT run the global test suite — that's for sprint-end regression, not per-PR validation

If the project has no master runner or component test suite, fall back to running the appropriate framework command scoped to the affected directories.

If anything fails, fix it. Do not proceed to Stage 10 with failing tests.
STAGES_EOF
)

# DECISION_LOG_AND_REFLECTION is defined in lib/shared-prompts.sh
source "${SCRIPT_DIR}/lib/shared-prompts.sh"

RULES=$(cat <<'RULES_EOF'
Rules:
- Follow each stage in order — do not skip stages
- Be thorough — this is a major revision, not a quick fix
- **Worktree CWD discipline:** the workflow starts you in a git worktree at a specific absolute path. NEVER `cd` to the main repo's checkout — operations there land outside the worktree's branch and are invisible to the PR (silently lost work). When running sed/find/xargs across many files, pass the worktree's absolute path explicitly. If you need a Bash command in a different directory, use `(cd <worktree-abs-path> && command)` in a subshell rather than a top-level `cd`.
- **File-reading discipline:** after the first full Read of a file, subsequent Reads MUST use `offset`+`limit` or use Grep to target a specific region. Do NOT re-read the entire file. Unbounded re-reads of already-read files are the single largest source of wasted tokens observed in production (one run hit 17× full reads of the same 1500-line file = ~45k redundant tokens). Narrow Reads after Edits are legitimate verification.
- **Large-file reading:** before the FIRST Read of any markdown file, run `wc -l` on it. If >500 lines, use `limit:200` on the first Read to avoid the 25K-token Read ceiling. Common culprits: roadmap.md, sprint/phase docs, loose_ends files, standards docs, .jsonl logs. When in doubt, check size first.
- **Read-before-Edit (HARD requirement):** before any Edit or Write to an existing file, the most recent Read of that file MUST be in this turn or the immediately previous turn. If the gap is wider — or any tool ran between (formatter like ruff/black/autopep8, linter, codemod like isort, git checkout, test runs, autoformatter-on-save, subagent boundary) — re-Read the file before Editing. The `File has not been read yet` and `File has been modified since read` errors are the signals you missed this. Recurring pattern across multiple production review cycles — this is hard discipline, not soft guidance.
- **Bash CWD persists between calls — never blind-chain a relative `cd`:** the working directory usually carries over from your previous Bash call (some configurations reset it — treat it as unpredictable). A chained relative `cd <subdir> && ...` fails whenever the CWD is already that subdir. When you need to cd, use the absolute worktree-rooted path (`cd <worktree>/lib/temporal && pytest tests/unit/`) — idempotent regardless of current CWD — or skip cd and use absolute paths in the command itself.
- **Re-Read before re-Editing anything you wrote earlier:** Edit requires a fresh Read. The classic failures: revising a /tmp staging file (e.g. `/tmp/claude-pr-body.md`) several turns after Writing it, or re-Editing a repo file many turns after its last Read (applying review findings). Either Read the file again first, or for staging files simply Write the full replacement content instead of Editing.
- **Prefer relative paths inside the worktree:** the workflow places you at the worktree root. For Read/Grep/Glob/Edit/Write of files inside the worktree, use paths relative to the root (e.g., `lib/temporal/foo.py`) rather than re-typing the long absolute worktree path. The model occasionally typos long absolute paths (e.g., `.claire/` instead of `.claude/`) — relative paths eliminate that bug class entirely.
- **Parallel tool calls in the gather phase:** when gathering context (Read/Grep/Glob), batch 3+ independent tool calls into a single assistant turn. Sequential gather wastes turns. Parallel gather is a pure efficiency win — higher-parallelism runs are not more error-prone.
- **Tool parameter naming gotchas** (these cause recurring InputValidationErrors):
  - Grep on a single file uses `path`, NOT `file_path`. Read/Edit/Write use `file_path`.
  - Read does NOT take a `command` parameter — that's Bash.
  - Glob does NOT take `head_limit` — that's a Grep option.
  - TodoWrite takes an ARRAY for `todos`, not a string.
- Fix Critical review findings before submitting
- Tests must pass before committing
- Document deviations from the plan
- If you cannot complete a stage, stop and clearly report why
RULES_EOF
)

# ---------------------------------------------------------------------------
# Workflow execution
# ---------------------------------------------------------------------------
if [[ -n "$PR_NUMBER" ]]; then
    # ---- Existing PR path -------------------------------------------------
    echo "→ Fetching PR #${PR_NUMBER} metadata..."
    PR_BRANCH=$(gh pr view "$PR_NUMBER" --json headRefName --jq '.headRefName')
    if [[ -z "$PR_BRANCH" ]]; then
        echo "Error: could not determine branch for PR #${PR_NUMBER}" >&2
        exit 1
    fi
    echo "  Branch: ${PR_BRANCH}"

    WORKTREE_PATH=".claude/worktrees/${WORKTREE_NAME}"
    mkdir -p .claude/worktrees

    echo "→ Fetching latest PR branch state..."
    git fetch origin "$PR_BRANCH"

    echo "→ Creating worktree at ${WORKTREE_PATH}..."
    git worktree add -f "$WORKTREE_PATH" "origin/${PR_BRANCH}"

    PROMPT="You are executing the REVISION-MAJOR workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

This is a SIGNIFICANT rework — not a minor fix. Follow all 8 stages thoroughly.

Task: ${DESCRIPTION}

${STAGES_1_TO_7}

## Stage 8: SUBMIT
- Stage any uncommitted changes remaining from stages 5-7 (peer-review fixes from code-reviewer, refactoring-evaluator, and standards-auditor) and commit them with the final message format: \"revision-major: <short description>\". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch (this updates PR #${PR_NUMBER})
- Report a summary of the entire workflow

${DECISION_LOG_AND_REFLECTION}

${RULES}"

    echo
    echo "→ Launching Claude in revision-major mode (updating PR #${PR_NUMBER})..."
    echo

    (
        cd "$WORKTREE_PATH"
        run_claude "$PROMPT"
    )

else
    # ---- New revision path ------------------------------------------------
    PROMPT="You are executing the REVISION-MAJOR workflow on a new branch.

This is a SIGNIFICANT rework — not a minor fix. Follow all 8 stages thoroughly.

Task: ${DESCRIPTION}

${STAGES_1_TO_7}

## Stage 8: SUBMIT
- Stage any uncommitted changes remaining from stages 5-7 (peer-review fixes from code-reviewer, refactoring-evaluator, and standards-auditor) and commit them with the final message format: \"revision-major: <short description>\". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch
- Create a new PR using 'gh pr create'. Title format: \"revision-major: <short description>\". In the body, include:
  - Summary of what was changed
  - Deviations from plan (if any)
  - Review findings addressed and deferred
  - Refactoring suggestions implemented and deferred
  - Standards audit findings addressed and deferred
  - Test results
- Report the PR URL

${DECISION_LOG_AND_REFLECTION}

${RULES}"

    echo "→ Launching Claude in revision-major mode (new branch)..."
    echo

    run_claude "$PROMPT" -w "$WORKTREE_NAME"
fi

echo
echo "================================================================"
echo "  REVISION-MAJOR WORKFLOW COMPLETE"
echo "================================================================"
echo
echo "Worktree: .claude/worktrees/${WORKTREE_NAME}"
echo "Log file: ${LOG_FILE}"
print_cycle_totals "$LOG_DIR"
echo
echo "To let Claude diagnose this run:"
echo "  claude 'read ${LOG_FILE} and tell me what happened'"
echo
echo "To clean up when done:"
echo "  /cleanup-merged-worktrees    (after PR is merged or closed)"
echo
