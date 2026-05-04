#!/usr/bin/env bash
#
# sprint-review.sh — the SPRINT-REVIEW workflow
# Comprehensive end-of-sprint review covering security, refactoring, testing,
# and synthesis across the whole repo.
#
# This is a holistic sprint-end workflow. Unlike per-PR reviews which look at
# specific changes, sprint-review takes a wholistic view of the codebase:
# - Whole-repo security audit (latent vulnerabilities, not just sprint diff)
# - Whole-repo refactoring assessment (structural patterns, tech debt)
# - Suite-quality testing review (coverage gaps + tool assessment)
# - Full test suite execution (unit + integration + e2e)
# - Auto-creates missing tests for sprint components (low-risk pattern)
# - Opus synthesizes specialist reports into an executive summary
#
# Output: a PR containing the consolidated review report at
# docs/development/reviews/sprint-review-YYYY-MM-DD.md plus any newly created
# test files. The PR body has structured sections per specialist agent.
#
# Replaces: sprint-test.sh (the prior testing-only sprint workflow). This
# workflow is broader — testing is one lens among several.
#
# Stages:
#   1. DISCOVER — sprint boundary, planning docs, prior reviews, repo structure
#   2. ANALYZE (parallel) — security-auditor + refactoring-evaluator + testing
#      review dispatched in a single message
#   3. RUN TESTS — full suite via master runner (unit + integration + e2e)
#   4. BUILD MISSING TESTS — auto-create unit/integration tests for sprint
#      components (refactoring/security findings remain surface-only)
#   5. SYNTHESIZE — Opus reads all specialist reports + test results, produces
#      executive summary with cross-cutting themes and priority order
#   6. SUBMIT — write consolidated review file, commit, create PR with
#      structured body sections
#
# Design philosophy: WHOLISTIC, not nitpicking. Per-PR reviews already cover
# individual changes. This workflow asks "how is the codebase doing as a
# whole?" — a different lens.
#
# Usage:
#   ./sprint-review.sh
#   ./sprint-review.sh --sprint "Sprint 1"
#   ./sprint-review.sh --verbose
#   ./sprint-review.sh --sprint "Sprint 2" --verbose
#   ./sprint-review.sh --pr 42 --verbose
#
# Examples (flags FIRST):
#   sprint-review.sh --verbose
#   sprint-review.sh --sprint "Sprint 1 — Cluster Provisioning" --verbose
#   sprint-review.sh --pr 42 --verbose --task-file /tmp/sprint-context.md
#
# Flags:
#   --sprint <name>      Human-readable sprint identifier for the report title
#   --pr <number>        Update an existing PR instead of creating a new one
#   --task-file <path>   Read additional context from a file
#   --verbose, -v        Stream formatted Claude output live
#
# Logging:
#   Every run writes a structured JSONL log to .claude/logs/sprint-review-<ts>.jsonl
#
# See docs/standards/workflow-scripts.md for the standard this script follows.

set -euo pipefail

# ---------------------------------------------------------------------------
# Script location (for finding lib/format-stream.sh)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORMATTER="${SCRIPT_DIR}/lib/format-stream.sh"

# Resolve the claude-dot-files repo root from the script's own location.
# Used to point the workflow at cpi-decisions.md regardless of the analyzed
# repo's path (skyy-command, mdc-master-planning, etc. on workstation or VM).
CLAUDE_DOT_FILES_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_TURNS=600

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
show_usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Comprehensive end-of-sprint review (security + refactoring + testing + synthesis).
Creates a PR with the consolidated review report and any new test files.

Options:
  --sprint <name>      Human-readable sprint identifier for the report title
  --pr <number>        Update an existing PR instead of creating a new one
  --task-file <path>   Read additional context (focus areas, known concerns) from a file
  --verbose, -v        Stream formatted Claude output live

Examples (flags FIRST):
  $(basename "$0") --verbose
  $(basename "$0") --sprint "Sprint 1 — Cluster Provisioning" --verbose
  $(basename "$0") --pr 42 --verbose --task-file /tmp/sprint-context.md
EOF
}

SPRINT_NAME=""
PR_NUMBER=""
TASK_FILE=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --sprint)
            if [[ $# -lt 2 ]]; then
                echo "Error: --sprint requires a name" >&2
                exit 1
            fi
            SPRINT_NAME="$2"
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
        --task-file)
            if [[ $# -lt 2 ]]; then
                echo "Error: --task-file requires a path" >&2
                exit 1
            fi
            TASK_FILE="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        -*)
            echo "Error: unknown option '$1'" >&2
            exit 1
            ;;
        *)
            echo "Error: unexpected positional argument '$1'" >&2
            echo "This workflow takes no positional arguments. Use --sprint for a sprint name." >&2
            exit 1
            ;;
    esac
done

# Load task file into CONTEXT (preserves content literally)
CONTEXT=""
if [[ -n "$TASK_FILE" ]]; then
    if [[ ! -f "$TASK_FILE" ]]; then
        echo "Error: task file not found: ${TASK_FILE}" >&2
        exit 1
    fi
    if [[ ! -r "$TASK_FILE" ]]; then
        echo "Error: task file not readable: ${TASK_FILE}" >&2
        exit 1
    fi
    CONTEXT=$(cat "$TASK_FILE")
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
TODAY=$(date +%Y-%m-%d)
WORKTREE_NAME="sprint-review-${TIMESTAMP}"
REPORT_FILE_REL="docs/development/reviews/sprint-review-${TODAY}.md"

LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/sprint-review-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"

# Build sprint label for the prompt
SPRINT_LABEL="${SPRINT_NAME:-"(unspecified — derive from planning docs)"}"

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  SPRINT-REVIEW WORKFLOW"
echo "================================================================"
echo "  Sprint     : ${SPRINT_LABEL}"
if [[ -n "$PR_NUMBER" ]]; then
    echo "  Target     : PR #${PR_NUMBER} (updating existing)"
else
    echo "  Target     : new branch and PR"
fi
if [[ -n "$TASK_FILE" ]]; then
    echo "  Task file  : ${TASK_FILE}"
fi
echo "  Report     : ${REPORT_FILE_REL}"
echo "  Worktree   : ${WORKTREE_NAME}"
echo "  Max turns  : ${MAX_TURNS}"
echo "  Verbose    : ${VERBOSE}"
echo "  Log file   : ${LOG_FILE}"
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# run_claude helper (shared library)
# ---------------------------------------------------------------------------
source "${SCRIPT_DIR}/lib/run-claude.sh"

# ---------------------------------------------------------------------------
# Context block (injected into prompt only when context is provided)
# ---------------------------------------------------------------------------
CONTEXT_BLOCK=""
if [[ -n "$CONTEXT" ]]; then
    CONTEXT_BLOCK="
--- additional context (focus areas, known concerns) ---
${CONTEXT}
--- end additional context ---
"
fi

# ---------------------------------------------------------------------------
# Decision Log + Deferred Work + Post-Run Reflection (standard PR-comment spec)
# ---------------------------------------------------------------------------
DECISION_LOG_AND_REFLECTION=$(cat <<'DLR_EOF'
After pushing (and creating the PR if on the new-branch path), post a PR comment containing a Decision Log, Deferred Work section, and Post-Run Reflection. Write the comment body to a temp file first (e.g., `/tmp/pr-comment-<timestamp>.md`), then post via `gh pr comment <PR-number> --body-file <temp-file>`. Do NOT inline the content into the command — multi-line content in a single arg is fragile.

The comment must contain these three sections:

## Decision Log

List NON-OBVIOUS decisions made during this run (workflow execution decisions — distinct from the specialist findings documented in the PR body). One bullet per decision, format:
`**[High/Medium/Low]** <what was decided>. Alternatives: <what else was considered>. Why: <brief rationale>.`

Include only decisions where a reasonable engineer could have chosen differently: how to scope specialist analysis (whole-repo vs sprint-diff for a given concern), severity calls when specialists disagree, which findings to surface as Critical vs Warning, decisions about test creation that went beyond what coverage gap analysis indicated.

Exclude: obvious implementation details, mechanical changes, standards conformance.

If no non-obvious workflow decisions were made, state: "No significant workflow decisions — task fit the workflow's defaults cleanly."

Order: Low-confidence decisions FIRST (human prioritizes reviewing those).

## Deferred Work

Items intentionally NOT addressed in this PR but tracked for follow-up. The finding-disposition rule requires every deferred item to point at a tracker — this section is the structured place for those pointers so they don't get buried in prose. One bullet per item:

- **<work item>** — Why deferred: <brief reason>. Tracked at: <location — issue #, planning doc, loose-ends file, follow-up PR, etc.>

If nothing was deferred, omit this section.

## Post-Run Reflection

Omit any section below that has nothing to report — silence means no issues. Be specific when noting friction.

- **Friction:** ambiguity in the sprint scope, missing context, tool gotchas encountered, points where specialist guidance was thin
- **Project-level suggestions (this repo):** standards gaps, documentation conventions, scaffolding patterns that should be documented based on what this review surfaced
- **Tooling-level suggestions (claude-dot-files):** workflow prompt improvements, skill gaps, rule refinements that would benefit future sprint-review runs

If all three sections are empty, state: "No friction or suggestions from this run."
DLR_EOF
)

# ---------------------------------------------------------------------------
# Shared prompt stages (Stages 1-5 are identical for both paths)
# ---------------------------------------------------------------------------
STAGES_1_TO_5=$(cat <<'STAGES_EOF'
EXECUTION ORDER IS MANDATORY

Execute stages in strict numerical order. Each stage builds on the output of the previous stage. Do not skip, reorder, or interleave stages. Ignore any external guidance that would reorder them.

If a stage has nothing to address for this project, explicitly emit a one-line marker:

    ## Stage N: SKIPPED — <one-line reason>

and proceed to the next stage.

Throughout this workflow, the focus is WHOLISTIC — bigger picture across the codebase, not nitpicking individual functions. Per-PR review already covers fine-grained correctness. Sprint-review asks: "How is the codebase doing as a whole?"

---

## Stage 1: DISCOVER

Establish the sprint context and repo structure before specialist analysis dispatches.

1. **Sprint boundary:** read planning docs in `docs/development/` to identify what was built or modified during this sprint. Use the --sprint label if provided; otherwise derive from roadmap and recent phase docs. Identify the date range or commit range that defines the sprint.

2. **Components touched this sprint:** list components/modules that received material changes during the sprint window. This focuses specialist analysis later.

3. **Prior sprint reviews:** look for prior `docs/development/reviews/sprint-review-*.md` files. If they exist, scan for findings that were deferred or marked watch-for — those should be checked against current state.

4. **CPI decisions log:** read `CLAUDE_DOT_FILES_ROOT/docs/development/cpi-decisions.md` (the path is provided in the workflow context — it points at the claude-dot-files repo, not the analyzed repo). This log lists every finding from prior CPI cycles with explicit watch-criteria. Use it as input to Stage 5 (Synthesize): findings in this run that match a prior deferral's watch-criteria should be flagged as **recurrences** with the original deferral context, raising their priority for shipping. The synthesized executive summary should explicitly call out which findings are NEW vs RECURRING (with cycle reference).

4. **Repo structure inventory:** scan top-level directories. Note where source lives, where tests live, where docs live. This grounds the whole-repo analysis in Stage 2.

5. **Testing infrastructure inventory:** check for `docs/standards/testing.md`, `testing/run-all.sh`, suite runners under `testing/suites/`, master-runner invocation patterns. Stage 3 (Run Tests) and Stage 4 (Build Missing Tests) depend on this.

Produce a brief inventory that grounds the rest of the workflow.

## Stage 2: PARALLEL ANALYSIS (3 specialists, single dispatch)

Dispatch THREE peer-review specialists IN PARALLEL. Send a SINGLE assistant message containing three Agent tool calls — one each for security-auditor, refactoring-evaluator, and a testing review (use the test-writer agent in review-mode — read-only, no test creation in this stage). The three specialists analyze the SAME codebase from independent lenses; serial dispatch wastes turns and roughly triples the wall-clock time of this stage.

**How to dispatch in parallel:** in one assistant turn, emit three tool_use blocks. Do NOT call them one at a time across separate turns.

### security-auditor — WHOLE-REPO security audit

Scope: the entire codebase, not just sprint diff. The point of sprint-review's security pass is finding LATENT vulnerabilities (issues that have always existed but were never reviewed) — different from per-PR review which catches new bugs.

Focus areas:
- Entry points: network handlers, API surfaces, user input boundaries, file I/O
- Authentication and authorization paths
- Secret handling (env vars, config files, hardcoded credentials)
- Privilege boundaries (sudo, capabilities, RBAC)
- Cross-component trust assumptions
- Cumulative changes from this sprint specifically (additional focus, not exclusive)

Severity: Critical / High / Medium / Low. Be specific — cite file paths and line numbers. Don't manufacture findings; if the codebase looks clean in a category, say so.

### refactoring-evaluator — WHOLE-REPO structural assessment

Scope: the entire codebase. Different from per-PR refactoring evaluation (which focuses on changed code) — this is the holistic "has the codebase grown unevenly" lens.

Focus areas:
- Files that have grown too large (rule of thumb: >500 lines warrants a look)
- Duplicated patterns across components that could become shared abstractions
- Inconsistent abstractions for similar concerns
- Modules that should split or merge based on coupling/cohesion
- Tech debt that has grown organically across multiple sprints
- Architecture deviations from documented intent

Priority: High / Medium / Low. Cite file paths. If the codebase looks structurally healthy, say so — this is genuinely a "first time we look at this" lens, so noise is possible. Calibrate by asking "would a senior engineer joining this codebase actually refactor this, or shrug and move on?"

### testing review — suite quality + tooling assessment

Use the test-writer agent in review-mode (read-only — no test creation in this stage; that's Stage 4). Dispatch with explicit instruction to NOT create files, only assess.

Focus areas:
- Coverage gaps for sprint components (per-component unit test status)
- Integration test gaps (component pairs that interact but lack interaction tests)
- E2E coverage (workflow paths that touch sprint components)
- Test suite tooling assessment: is the master runner working as intended? Are framework configs current? Are suite runners doing the right thing? Should pytest/molecule/etc. versions be upgraded?
- Hierarchy health: orphaned tests, misplaced tests, false-discovery files (test_* that aren't tests)
- Test quality concerns: brittle tests, missing edge cases, over-mocking, tests that assert implementation rather than behavior

Severity: Critical / High / Medium / Low.

### After all three specialists return

Each agent's findings will be referenced in Stage 5 (Synthesize) and the final report. For now, save their structured outputs and proceed to Stage 3.

If one agent has no findings, note inline (e.g., "refactoring-evaluator: no significant whole-repo refactoring findings") rather than emitting a SKIPPED marker — the stage as a whole still ran.

**Reviewer severity disagreement principle:** the three specialists may flag overlapping concerns at different severities (e.g., security-auditor flags an auth path as High, refactoring-evaluator notes the same code is structurally messy at Medium). When this happens, **engineering-quality bar is the override authority** — the higher-severity call wins, with the lower-severity perspective documented as additional context. Do NOT try to reconcile to a single label.

## Stage 3: RUN TESTS

Execute the test suites and capture results. Use the master runner if available, fall back to framework commands if not.

### Unit Tests
- Run `./testing/run-all.sh unit` (or framework equivalent like `pytest <component>/tests/unit/` for each sprint component)
- Capture: total tests, passed, failed, errors, time

### Integration Tests
- Run `./testing/run-all.sh integration` or equivalent
- Capture: total tests, passed, failed, errors, time

### End-to-End Tests
- Run `./testing/run-all.sh e2e` or equivalent
- If no e2e tests exist, note "no e2e tests configured"
- Capture: total tests, passed, failed, errors, time

If ANY test suite fails to execute (command not found, import errors, missing fixtures), report the failure clearly — do not silently skip.

If the project has no master runner and no test infrastructure at all, report that clearly and skip to Stage 4 with recommendations to establish testing infrastructure.

## Stage 4: BUILD MISSING TESTS

Using the coverage gaps identified by the testing review in Stage 2, create missing tests. This stage is allowed to create test files (low-risk pattern carried over from sprint-test.sh) — but stays surface-only on refactoring and security findings (those are reviewed by humans before action).

### Unit Tests
For each sprint component flagged with missing or partial unit coverage:
- Create `<component>/tests/unit/` directory if it doesn't exist
- Write unit tests covering core functionality (happy path, edge cases, error cases)
- Add a component-level `conftest.py` if needed for shared fixtures

### Integration Tests
For each pair of sprint components that interact but lack integration coverage:
- Create `<component>/tests/integration/` and write tests that exercise the interaction boundary
- Focus on the contract: does component A correctly call component B? Does it handle errors from B?
- If the interaction requires running services that aren't available, write the test with appropriate skip markers (`@pytest.mark.skipif`) and document why

### E2E Tests
For sprint workflows that lack e2e coverage:
- Create tests in `testing/e2e/` (repo-level, since e2e tests span all components)
- Write e2e tests that exercise full workflow paths end-to-end
- If the e2e test requires infrastructure that isn't available, write the test with skip markers and document the infrastructure requirements

### What this stage does NOT do (surface-only for first 3+ runs)

Per the engineering-quality rule (human-in-the-loop for new capabilities), this workflow is in surface-only mode for refactoring and security findings:
- Do NOT auto-apply refactoring suggestions from refactoring-evaluator. Those go in the report and PR body for human review.
- Do NOT auto-apply security fixes from security-auditor. Same — report and surface, don't fix.
- Do NOT modify source code in this stage. Test files are the only allowed creation.

After this stage, produce a summary:
- Tests created: [count by category — unit, integration, e2e]
- Tests requiring infrastructure: [list with skip reasons]

## Stage 5: SYNTHESIZE

Read all specialist reports from Stage 2, the test results from Stage 3, and the test-creation summary from Stage 4. Produce an executive summary that captures cross-cutting themes and priority order.

The synthesis lens:
- **What's the holistic state of the codebase?** One paragraph, honest assessment.
- **Cross-cutting themes:** patterns that appear in multiple specialist reports (e.g., "auth-related code shows both security findings and structural complexity findings — both point at the same area")
- **Priority order:** which findings warrant immediate action vs. backlog. Use Critical / High / Medium / Low across all specialists, with engineering-quality-bar override for severity disagreements.
- **Sprint-vs-historical:** distinguish findings introduced this sprint (warrant immediate fix) from latent issues that have always existed (judgment call on action).

The executive summary becomes the lead section of the consolidated review report and the PR body.
STAGES_EOF
)

# ---------------------------------------------------------------------------
# Rules block (consistent across PR-producing workflows)
# ---------------------------------------------------------------------------
RULES=$(cat <<'RULES_EOF'
Rules:
- Follow each stage in order — do not skip stages
- This is a SPRINT REVIEW — focus WHOLISTIC, not nitpicking. Per-PR review already covers fine-grained correctness; sprint-review is the "how is the codebase doing as a whole?" lens.
- **Surface-only mode for refactoring and security findings:** do NOT auto-apply refactoring suggestions or security fixes. Findings go in the report and PR body for human review. Test creation IS allowed (Stage 4) — that's the established low-risk pattern carried over from sprint-test.sh.
- Do NOT modify source code outside Stage 4's test-file creation. The workflow's job is to surface findings, not unilaterally fix them.
- **Worktree CWD discipline:** the workflow starts you in a git worktree at a specific absolute path. NEVER `cd` to the main repo's checkout — operations there land outside the worktree's branch and are invisible to the PR (silently lost work). When running sed/find/xargs across many files, pass the worktree's absolute path explicitly. If you need a Bash command in a different directory, use `(cd <worktree-abs-path> && command)` in a subshell rather than a top-level `cd`.
- **File-reading discipline:** after the first full Read of a file, subsequent Reads MUST use `offset`+`limit` or use Grep to target a specific region. Do NOT re-read the entire file. Unbounded re-reads of already-read files are the single largest source of wasted tokens observed in production. Narrow Reads after Edits are legitimate verification.
- **Large-file reading:** before the FIRST Read of any markdown file, run `wc -l` on it. If >500 lines, use `limit:200` on the first Read to avoid the 25K-token Read ceiling. Common culprits: roadmap.md, sprint/phase docs, loose_ends files, standards docs, .jsonl logs. When in doubt, check size first.
- **Read-before-Edit (HARD requirement):** before any Edit or Write to an existing file, the most recent Read of that file MUST be in this turn or the immediately previous turn. If the gap is wider — or any tool ran between (formatter, linter, codemod, git checkout, test runs, autoformatter-on-save, subagent boundary) — re-Read the file before Editing. The `File has not been read yet` and `File has been modified since read` errors are the signals you missed this. Recurring pattern across multiple production review cycles — this is hard discipline, not soft guidance.
- **Bash CWD does not persist between calls:** every Bash command starts at the worktree root regardless of any previous `cd` in earlier Bash calls. To run a command in a subdirectory, either chain with `&&` in the SAME Bash call or use absolute paths. Bare `cd <subdir>` followed by a separate Bash call to run something will execute in the wrong location.
- **Prefer relative paths inside the worktree:** the workflow places you at the worktree root. For Read/Grep/Glob/Edit/Write of files inside the worktree, use paths relative to the root rather than re-typing the long absolute worktree path. The model occasionally typos long absolute paths (e.g., `.claire/` instead of `.claude/`) — relative paths eliminate that bug class entirely.
- **Parallel tool calls in the gather phase:** when gathering context (Read/Grep/Glob), batch 3+ independent tool calls into a single assistant turn. Sequential gather wastes turns. Parallel gather is a pure efficiency win.
- **Tool parameter naming gotchas** (these cause recurring InputValidationErrors):
  - Grep on a single file uses `path`, NOT `file_path`. Read/Edit/Write use `file_path`.
  - Read does NOT take a `command` parameter — that's Bash.
  - Glob does NOT take `head_limit` — that's a Grep option.
  - TodoWrite takes an ARRAY for `todos`, not a string.
- Don't fabricate findings — if a specialist's category looks clean, say so. Empty sections are valid and signal a healthy state.
- Be specific: cite file paths and line numbers in findings. Vague findings are not actionable.
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

    PROMPT="You are executing the SPRINT-REVIEW workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

This is a comprehensive end-of-sprint review covering security, refactoring, testing, and synthesis. The focus is WHOLISTIC — across the codebase, not nitpicking individual changes. Follow all 6 stages thoroughly.

Sprint: ${SPRINT_LABEL}
CLAUDE_DOT_FILES_ROOT: ${CLAUDE_DOT_FILES_ROOT}
${CONTEXT_BLOCK}
${STAGES_1_TO_5}

## Stage 6: SUBMIT

- Write the consolidated review report to \`${REPORT_FILE_REL}\` containing all sections (executive summary from Stage 5, security findings, refactoring observations, testing review + suite tooling assessment, test results, tests created summary).
- Stage all changes (the report file + any test files created in Stage 4) and commit with the final message format: \"sprint-review: <sprint label or date> — comprehensive end-of-sprint review\"
- Push the branch (this updates PR #${PR_NUMBER})
- Update the PR body to mirror the report's section structure:
  - **Executive Summary** (Opus synthesis from Stage 5 — top findings, priority order, codebase health assessment in 2-3 paragraphs)
  - **Security Findings** (security-auditor section — Critical/High/Medium/Low with file:line citations)
  - **Refactoring Observations** (refactoring-evaluator section — High/Medium/Low priorities)
  - **Testing Review** (coverage gaps, suite tooling assessment, hierarchy health)
  - **Test Results** (unit/integration/e2e pass-fail counts)
  - **Tests Created** (table of new test files from Stage 4)
  - Link to the full report file at the bottom: \"Full report: ${REPORT_FILE_REL}\"

  Keep PR body sections scannable — full detail belongs in the report file. Use bullet points and tables. Do NOT repeat reviewer findings verbatim across both PR body and report file; PR body summarizes, report file has full detail.

${DECISION_LOG_AND_REFLECTION}

${RULES}"

    echo
    echo "→ Launching Claude in sprint-review mode (updating PR #${PR_NUMBER})..."
    echo

    (
        cd "$WORKTREE_PATH"
        run_claude "$PROMPT"
    )

else
    # ---- New branch path --------------------------------------------------
    PROMPT="You are executing the SPRINT-REVIEW workflow on a new branch.

This is a comprehensive end-of-sprint review covering security, refactoring, testing, and synthesis. The focus is WHOLISTIC — across the codebase, not nitpicking individual changes. Follow all 6 stages thoroughly.

Sprint: ${SPRINT_LABEL}
CLAUDE_DOT_FILES_ROOT: ${CLAUDE_DOT_FILES_ROOT}
${CONTEXT_BLOCK}
${STAGES_1_TO_5}

## Stage 6: SUBMIT

- Write the consolidated review report to \`${REPORT_FILE_REL}\` containing all sections (executive summary from Stage 5, security findings, refactoring observations, testing review + suite tooling assessment, test results, tests created summary).
- Stage all changes (the report file + any test files created in Stage 4) and commit with the final message format: \"sprint-review: <sprint label or date> — comprehensive end-of-sprint review\"
- Push the branch
- Create a new PR using 'gh pr create'. Title format: \"sprint-review: <sprint label or date>\". The PR body should mirror the report's section structure:
  - **Executive Summary** (Opus synthesis from Stage 5 — top findings, priority order, codebase health assessment in 2-3 paragraphs)
  - **Security Findings** (security-auditor section — Critical/High/Medium/Low with file:line citations)
  - **Refactoring Observations** (refactoring-evaluator section — High/Medium/Low priorities)
  - **Testing Review** (coverage gaps, suite tooling assessment, hierarchy health)
  - **Test Results** (unit/integration/e2e pass-fail counts)
  - **Tests Created** (table of new test files from Stage 4)
  - Link to the full report file at the bottom: \"Full report: ${REPORT_FILE_REL}\"

  Keep PR body sections scannable — full detail belongs in the report file. Use bullet points and tables. Do NOT repeat reviewer findings verbatim across both PR body and report file; PR body summarizes, report file has full detail.
- Report the PR URL

${DECISION_LOG_AND_REFLECTION}

${RULES}"

    echo "→ Launching Claude in sprint-review mode (new branch)..."
    echo

    run_claude "$PROMPT" -w "$WORKTREE_NAME"
fi

echo
echo "================================================================"
echo "  SPRINT-REVIEW WORKFLOW COMPLETE"
echo "================================================================"
echo
echo "Worktree: .claude/worktrees/${WORKTREE_NAME}"
echo "Report  : ${REPORT_FILE_REL} (in worktree, will be in PR)"
echo "Log file: ${LOG_FILE}"
echo
echo "To let Claude diagnose this run:"
echo "  claude 'read ${LOG_FILE} and tell me what happened'"
echo
echo "To clean up when done:"
echo "  /cleanup-merged-worktrees    (after PR is merged or closed)"
echo
