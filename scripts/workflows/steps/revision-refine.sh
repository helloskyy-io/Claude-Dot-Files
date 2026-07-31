#!/usr/bin/env bash
#
# revision-refine.sh — the REVISION-REFINE step (CHILD of revision.sh)
# Reviews and corrects a draft PR with a FRESH context. Requires --pr.
#
# NOT INVOKED DIRECTLY by PMs — the parent `revision.sh` runs
# `revision-draft.sh` first, then calls this against the PR it produced.
#
# WHY THIS IS A SEPARATE RUN: it did not write the code. That is the entire
# point. A context that both authors a change and judges it defends the
# change — findings get dismissed rather than fixed. This run starts clean,
# holds the disposition authority the draft step deliberately lacks, and
# receives the ORIGINAL TASK so it can check fidelity (did this deliver what
# was asked?) and not merely internal quality. Handoff between the two runs
# is git: the PR, its diff, and the draft run's own reflection.
#
# Stages:
#   1. FIDELITY — original task vs what was delivered (present/missing/extra)
#   2. PEER REVIEW — code-reviewer + refactoring-evaluator + standards-auditor
#                    in parallel, then quality-control sequentially
#   3. RESOLVE — disposition EVERY finding (fixed/rejected/deferred/surfaced)
#                and fix. DEFERRED requires a FETCHED pointer, never a plausible one.
#   4. VERIFY — scoped regression after the corrections
#   5. SUBMIT — commit, push, update the PR
#
# Usage:
#   ./revision-refine.sh --pr <N> "the original task text"
#   ./revision-refine.sh --pr <N> --task-file /tmp/task.md --verbose
#
# Flags:
#   --pr <number>   REQUIRED — the draft PR to review and correct
#   --repo <path>   Target repo (explicit identity, never derived from cwd)
#   --verbose, -v   Stream formatted Claude output live
#
# Logging:
#   Every run writes a structured JSONL log to .claude/logs/revision-refine-<ts>.jsonl
#
# See docs/guide/workflows.md for the full
# architectural context behind this workflow.
# See docs/standards/workflow-scripts.md for the standard this script follows.

set -euo pipefail

# ---------------------------------------------------------------------------
# Script location (for finding lib/format-stream.sh)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORMATTER="${SCRIPT_DIR}/../lib/format-stream.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_TURNS=200

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
  --pr <number>        REQUIRED — the draft PR to review and correct
  --repo <path>        Target repo for the worktree. Use when dispatching from
                       OUTSIDE the target repo (e.g. from a planning repo) —
                       the target identity is explicit, never derived from the
                       invocation directory (Temporal Standard §7.5 principle).
                       Default: the repo containing the current directory.
  --verbose, -v        Stream formatted Claude output live
  --ci-unsettled       Set by the parent when CI had NOT finished for the draft's
                       head SHA before this step started. Makes the run state
                       that its CI verdict is unknown rather than reporting a
                       clean review that was never gate-checked.

Examples (flags FIRST, positionals LAST — protects the positional from
line-wrap and keeps options visible):
  $(basename "$0") "the auth flow needs to use sessions instead of JWT"
  $(basename "$0") --pr 5 "address all findings from PR #5"
  $(basename "$0") --verbose --pr 22 --task-file /tmp/rework.md
  $(basename "$0") --repo /opt/skyy-net/skyy-command --task-file /tmp/task.md

This workflow is for SIGNIFICANT rework — not minor fixes.
For minor corrections, use revision-minor.sh. This step is normally run by the
parent (scripts/workflows/revision.sh), not invoked directly.
EOF
}

DESCRIPTION=""
TASK_FILE=""
PR_NUMBER=""
REPO_TARGET=""
VERBOSE=false
CI_UNSETTLED=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)
            if [[ $# -lt 2 ]]; then
                echo "Error: --repo requires a path" >&2
                exit 1
            fi
            REPO_TARGET="$2"
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
        --help|-h)
            show_usage
            exit 0
            ;;
        --ci-unsettled)
            CI_UNSETTLED=true
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
# --pr is REQUIRED: refine always operates on an existing draft PR, and it needs
# the ORIGINAL task (positional or --task-file) to check fidelity against it.
if [[ -z "$PR_NUMBER" ]]; then
    echo "Error: --pr <number> is required — revision-refine reviews an existing draft PR." >&2
    echo "       (It is normally invoked by the parent: scripts/workflows/revision.sh)" >&2
    exit 1
fi
if ! [[ "$PR_NUMBER" =~ ^[0-9]+$ ]]; then
    echo "Error: --pr requires a positive integer" >&2
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

# Explicit target repo (--repo) — validate and switch BEFORE resolving the root.
# The target identity is explicit, never derived from the invocation directory
# (same principle as Temporal Standard §7.5). Without --repo, the invocation
# directory's repo is the target, as before.
if [[ -n "$REPO_TARGET" ]]; then
    if [[ ! -d "$REPO_TARGET" ]]; then
        echo "Error: --repo path not found: ${REPO_TARGET}" >&2
        exit 1
    fi
    if ! git -C "$REPO_TARGET" rev-parse --show-toplevel &>/dev/null; then
        echo "Error: --repo path is not a git repository: ${REPO_TARGET}" >&2
        exit 1
    fi
    cd "$REPO_TARGET"
fi

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
WORKTREE_NAME="revision-refine-${TIMESTAMP}"

LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/revision-refine-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  REVISION-REFINE WORKFLOW"
echo "================================================================"
# A --task-file description can run to 90+ lines; echoing it whole buries the
# rest of the banner, and the split prints one banner per child. Show the shape,
# not the payload — the full text is in the prompt and the JSONL log.
DESC_LINES=$(printf '%s\n' "$DESCRIPTION" | wc -l)
DESC_SUMMARY=$(printf '%s\n' "$DESCRIPTION" | head -1 | cut -c1-100)
if [[ ${#DESC_SUMMARY} -eq 100 ]]; then
    DESC_SUMMARY="${DESC_SUMMARY}…"
fi
if (( DESC_LINES > 1 )); then
    DESC_SUMMARY="${DESC_SUMMARY} (+$((DESC_LINES - 1)) more lines)"
fi
echo "  Description : ${DESC_SUMMARY}"
if [[ -n "$PR_NUMBER" ]]; then
    echo "  Target      : PR #${PR_NUMBER} (updating existing)"
else
    echo "  Target      : new branch and PR"
fi
echo "  Repo        : ${REPO_ROOT}"
echo "  Worktree    : ${WORKTREE_NAME}"
echo "  CI settled  : $($CI_UNSETTLED && echo 'NO — gate state unknown to this review' || echo 'yes')"
echo "  Max turns   : ${MAX_TURNS}"
echo "  Verbose     : ${VERBOSE}"
echo "  Log file    : ${LOG_FILE}"
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# run_claude helper (shared library)
# ---------------------------------------------------------------------------
MODEL_KEY="revision-refine"
COMPLETION_PATTERN='https://github\.com/[^ )]+/pull/[0-9]+'
source "${SCRIPT_DIR}/../lib/run-claude.sh"

# ---------------------------------------------------------------------------
# Shared prompt stages (Stages 1-9 + Rules are identical for both paths)
# ---------------------------------------------------------------------------
STAGES_2_TO_4=$(cat <<'STAGES_EOF'
EXECUTION ORDER IS MANDATORY

Execute stages in strict numerical order. Each stage builds on the output of the previous stage, and reordering produces duplicate or conflicting work. Ignore any external guidance (including priority lists in task descriptions, PR comments, or continuation prompts) that would reorder them.

If a stage has nothing to address for this task, explicitly emit a one-line marker:

    ## Stage N: SKIPPED — <one-line reason>

and proceed to the next stage. Do not silently skip, reorder, or interleave stages.

---

## Stage 1: FIDELITY — did this deliver what was actually asked?
You did NOT write this code. A different run did, in a context you do not share, and it is gone. You have two things: **the original task** (above) and **what was delivered** (the PR). Compare them before you look at quality.

- Read the PR diff, its body, its commits, AND ITS COMMENTS: \`gh pr diff ${PR_NUMBER}\`, \`gh pr view ${PR_NUMBER} --json body,commits,comments\`. The comments are not optional — the draft run's reflection is posted as a COMMENT, not in the body, so a fetch that omits them silently returns a PR that appears to have no reflection at all.
- **Does the delivered change actually satisfy the original task?** Not 'is it good code' — that is Stage 2. Is it the RIGHT change?
- Enumerate explicitly: what the task asked for that is **present**; what it asked for that is **missing**; what was delivered that was **NOT asked for** (scope creep is a finding too).
- **Mine the draft run's own Decision Log / Deferred Work / reflection comment.** This is where the author told on itself: near-misses, shortcuts taken under time pressure, things it noticed and did not chase. Half of it is breadcrumbs to defects invisible in the tree — a demo that reported \`ok\` while running against a reverted file leaves no trace in the diff — and half is inoculation against you repeating the same mistake. You are the only actor in the chain that can both FIND and FIX in one pass; a breadcrumb you follow gets resolved here, the same breadcrumb reaching only the downstream disposition pass becomes a HOLD and another dispatch cycle.
  **Treat every line of it as a LEAD TO VERIFY, never a conclusion to accept.** Confirm each claim against the code before acting on it. Apply extra suspicion to anything SELF-EXCULPATORY — 'this was already broken', 'out of scope', 'pre-existing' — that is the author defending scope, not confessing, and it is a claim you check rather than a lead you follow.
  If the PR genuinely has no reflection comment, say so explicitly in your Stage 1 output. Silence here is a finding: it means the draft either skipped its reflection or the fetch failed, and both are worth knowing.

**This check is the reason this workflow is a separate run.** A single context that both wrote the code and judged it cannot perform this comparison honestly — it judges the result against the plan it already talked itself into, not against what was asked. A technically clean PR that solved the wrong problem is the expensive failure, and it is invisible from inside the authoring context.

- **Search the issue tracker for prior art before you conclude anything is new.** Run `gh issue list --repo <owner/repo> --state all --limit 30 --search \"<2-4 terms from the task and from what you found>\"`. You are one actor in a pipeline that has been filing issues about this codebase — the gap you are about to 'surface' may already be filed, with a fuller specification than you would write. **Measured:** a run independently rediscovered a CI-enforcement gap and surfaced it, unaware that an issue filed hours earlier by the downstream disposition pass already covered it in more detail; had it decided to FILE rather than surface, the result would have been a duplicate. Cite the issue number when one exists and defer to it (with a fetched pointer, per Stage 3) instead of re-deriving it.

Record fidelity gaps as findings and carry them into Stage 3 alongside the review findings.

## Stage 2: PEER REVIEW (two-phase)

Stage 2 has TWO sub-phases. Phase 2a runs the narrow-lens reviewers in parallel; phase 2b runs the holistic quality-control reviewer sequentially with access to 2a's findings. This split exists because the parallel-narrow-then-sequential-integration pattern is the right shape for review (see `engineering-quality.md` "Review-stage agent lenses").

### Stage 2a: NARROW PEER REVIEW (parallel)

Dispatch all THREE peer-review agents — code-reviewer, refactoring-evaluator, and standards-auditor — back-to-back BEFORE processing any results. They review the SAME artifact — the draft run's diff on this PR branch, as read in Stage 1 — independently; there is no ordering dependency between them.

**The dispatch contract (headless-safe):** dispatch all three as FOREGROUND agents (`run_in_background: false`) in a single assistant message — foreground agents run concurrently where the harness allows AND the turn BLOCKS until every result returns. This is mandatory in a headless run: a text-only turn with no tool call ends the run, so you must NEVER background-dispatch and then wait (the wait becomes a run-killing text-only turn) and must NEVER use ScheduleWakeup to wait for agents here. quality-control (next sub-stage) runs only after ALL three narrow-lens results are in hand.

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

### Stage 2b: HOLISTIC REVIEW (sequential, after 2a returns)

After Stage 2a's three agents return, dispatch the `quality-control` agent SEQUENTIALLY. Send a single assistant message with ONE Agent call for quality-control.

The quality-control prompt MUST include:
- The work being reviewed (file paths changed, summary of the change)
- The structured findings from Stage 2a (code-reviewer + refactoring-evaluator + standards-auditor outputs, verbatim or paraphrased clearly)
- Instruction to apply the holistic six-dimension lens AND look for meta-patterns across the trio's findings ("do these findings together suggest the work was rushed, under-specified, or quality-compromised?")

quality-control applies the senior-engineer integration test: would a peer reviewer at a top-tier engineering organization sign off on this? Its lens is HOLISTIC — it pulls signals across dimensions that no narrow reviewer catches. See `quality-control-methodology` skill for the six dimensions (best-practices grounding, enterprise-readiness, compromise detection, maintainability, robustness, decision rigor) and severity calibration.

quality-control runs SEQUENTIALLY (not in parallel with 5a) because its lens benefits from seeing 2a's findings. This is the only review agent that runs sequentially — narrow-lens agents stay parallel.

### Consolidating findings (after both 5a and 5b)

After all four reviews complete (5a's three + 5b's quality-control), fix any Critical issues found across ANY of the four reviews.

**Reviewers may legitimately disagree on severity for the same finding because their bars differ:**
- **code-reviewer** judges engineering quality — correctness, safety, robustness, real-world failure modes
- **refactoring-evaluator** judges structural improvement potential — uses High/Medium/Low priority, not Critical/Warning
- **standards-auditor** judges documented-standard conformance — whether an explicit rule is violated
- **quality-control** judges the senior-engineer integration test — would a top-tier-org peer sign off

**When severities conflict on the same code, the engineering-quality bar is the override authority.** A code-reviewer Critical or quality-control Critical trumps a standards-auditor Info on the same finding — real correctness/safety/quality concerns win over "no documented violation." Don't try to reconcile severities into a single label; address each reviewer's finding by their own bar.

Per the finding-disposition rule, every finding must reach fixed / rejected-with-reasoning / documented-deferral — never silent pass-through. Note which agent raised each finding when documenting.

## Stage 3: RESOLVE — disposition AND fix
You hold the disposition authority the draft run deliberately does not, because you did not author the work. Use it: **every finding from Stages 1 and 2 gets an explicit disposition, and you FIX what should be fixed.** This is not a summary stage.

For each finding (fidelity gaps, code-reviewer, refactoring-evaluator, standards-auditor, quality-control), exactly ONE of these four. There is no fifth, and you may not invent one:

- **FIXED** — you corrected it here. Say what you changed.
- **REJECTED** — not a real issue; state the reasoning that makes it not one. \"Recommend we move on\" / \"acceptable as-is\" / \"low value\" are not reasoning.
- **DEFERRED** — real, and an EXISTING durable home already covers it. Allowed ONLY with a pointer you FETCHED: run the command, record what you saw. See the Deferred Work rules at the end of this prompt — they are binding here, at the moment of decision, not merely when you write the comment up. **If you cannot verify a home, this is not a DEFERRED; it is a SURFACED.**
- **SURFACED** — real, genuinely outside this change's scope, and NO verified home exists. State it plainly in the PR body with no pointer at all, so \`pr-review\` and the operator can dispose of it. Do NOT invent a tracker — surfacing IS the action, and a naked surfaced item gets picked up downstream while a plausible-looking pointer gets filed away as handled.

Fix by default. You are the cheap place to fix a finding: the code is fresh, the context is loaded, and the alternative is a PR round-trip. Reserve DEFERRED and SURFACED for things that genuinely widen scope.

**A word about your own bias, because it is not the one you were built to escape.** You did not author this code, so you have no stake in defending its *decisions* — that is the whole point of running you as a separate pass. But you DO have a stake in your own disposition table looking complete, and that motive produces a different failure: attesting to verification you did not perform. Both false pointers this workflow has shipped were written by a reviewer with nothing to defend, and both read as \"Verified present.\" Removing authorship removed the motive to defend decisions; it did not remove the motive to attest diligence. **Apply to your own table the rule you are applying to the draft's work: an account is not the artifact.** A table with seven confidently-pointed deferrals and two dead pointers is worse than a table with five deferrals and two honest \"no home for this\" entries.

Then produce a consolidated summary: original task vs what was delivered (Stage 1), each finding with its disposition, and any remaining concerns.

## Stage 4: VERIFY
Run scoped regression to verify everything passes after all changes:
1. Run new/modified tests first — validate the current changes work
2. If pass → run the affected component's full test suite (e.g., `./testing/run-all.sh unit <component>` or `pytest <component>/tests/`)
3. Do NOT run the global test suite — that's for sprint-end regression, not per-PR validation

If the project has no master runner or component test suite, fall back to running the appropriate framework command scoped to the affected directories.

**Then check the DELIVERED CI gate — you are the only actor who can.** Run \`gh pr checks ${PR_NUMBER}\` (and \`gh run view <id> --log-failed\` on any failure). The draft run structurally could not do this: pushing is its terminal act, so CI had not finished when it exited. A gate that is RED on a clean runner but green on the author's machine is the signature failure this catches — tests coupled to host state (a group, a mount, an installed binary, an env var) only ever asserted something true of the machine that wrote them. **A local pass is not evidence the gate is green.** Treat a red or host-coupled check as a Stage 3 finding and fix it here.

If anything fails, fix it. Do not proceed to Stage 5 with failing tests.
STAGES_EOF
)

# DECISION_LOG_AND_REFLECTION is defined in lib/shared-prompts.sh
source "${SCRIPT_DIR}/../lib/shared-prompts.sh"

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

    # CI-settled state comes from the PARENT, which waits for check runs before
    # starting this step. When it could not confirm settlement, the run must SAY
    # SO — a clean review summary that was never gate-checked reads identically
    # to a verified one, and that is the confusion the marker exists to prevent
    # (same discipline as a health_verified: false marker).
    if $CI_UNSETTLED; then
        CI_STATUS_NOTE="## CI GATE STATE: UNKNOWN

The parent could not confirm CI had finished for this PR's head commit before starting you. Still run \`gh pr checks ${PR_NUMBER}\` in Stage 4 — results may have landed since. But if checks are still pending when you reach Stage 5, you MUST state in your summary and in the PR body: **'CI had not settled; gate state unknown to this review.'** Do not report a clean review without that qualifier. An unqualified clean summary asserts a gate you never saw."
    else
        CI_STATUS_NOTE="## CI GATE STATE: SETTLED

The parent confirmed CI finished for this PR's head commit before starting you, so \`gh pr checks ${PR_NUMBER}\` in Stage 4 returns real verdicts, not pending ones. You are expected to have checked them."
    fi

    PROMPT="You are executing the REVISION-REFINE workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

This is a SIGNIFICANT rework — not a minor fix. Follow all 5 stages thoroughly.

Task: ${DESCRIPTION}

${HEADLESS_EXECUTION_GUARD}

${CI_STATUS_NOTE}

${STAGES_2_TO_4}

## Stage 5: SUBMIT
- Stage any uncommitted changes remaining from stages 2-4 (fidelity and peer-review fixes) and commit them with the final message format: \"revision-refine: <short description>\". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- **Update the PR's SELF-DESCRIPTION**: the PR body must describe what the PR NOW contains, and docs/file_structure.txt must reflect any files added/removed/renamed. A fix that leaves the PR's own description stale mechanically manufactures findings for the next review pass (measured: 1-2 per round, and one pass found ZERO code defects — only self-description drift).
- Push the branch (this updates PR #${PR_NUMBER})
- **As your FINAL line, print the PR URL** — run \`gh pr view ${PR_NUMBER} --json url --jq .url\` and print the result. This is the run's completion signal. On this path you UPDATE an existing PR rather than creating one, so nothing else emits the URL; a run that ends without it is misread as an early-stop failure even though the work succeeded.
- Report a summary of the entire workflow

${DECISION_LOG_AND_REFLECTION}

${RULES}"

    echo
    echo "→ Launching Claude in revision-refine mode (updating PR #${PR_NUMBER})..."
    echo

    (
        cd "$WORKTREE_PATH"
        run_claude "$PROMPT"
    )

fi

echo
echo "================================================================"
echo "  REVISION-REFINE WORKFLOW COMPLETE"
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
