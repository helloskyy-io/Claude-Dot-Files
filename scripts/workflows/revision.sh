#!/usr/bin/env bash
#
# revision.sh — the REVISION workflow (PARENT)
# Significant rework of existing code, delivered as a reviewed PR.
#
# This is a PARENT workflow: pure bash orchestration over two independent
# child runs. It calls no model itself, so it has no MODEL_KEY and no
# COMPLETION_PATTERN — each child carries its own.
#
#   1. steps/revision-draft.sh   — writes the change, opens an UNREVIEWED PR
#   2. steps/revision-refine.sh  — FRESH context: reviews and corrects it
#
# WHY TWO RUNS INSTEAD OF ONE LONG ONE — this is the whole point of the split:
# the author of a change defends it. When one context both writes code and
# dispositions the review findings about it, findings get dismissed rather
# than fixed. Measured repeatedly on this fleet: defects survived engineer
# self-review, four in-context review agents, and manual verification, then
# fell to a fresh-eyes pass costing a few dollars. Splitting the run puts a
# process boundary exactly where judgement happens. Neither child inherits the
# other's context; the handoff is git (the PR, its diff, the draft's own
# reflection) plus the original task, which BOTH children receive so refine
# can check fidelity — did this deliver what was asked? — and not merely
# internal quality.
#
# This is also the shape a durable-execution engine wants: deterministic
# control flow outside, non-deterministic work inside independent activities.
# Composition works today in bash; Temporal would add durability, not
# composition.
#
# Usage:
#   ./revision.sh "description of changes needed" [options]
#   ./revision.sh --task-file path/to/task.md [options]
#
# Options:
#   --pr <number>        Rework an EXISTING PR (draft updates it in place)
#   --repo <path>        Target repo (explicit identity, never derived from cwd)
#   --verbose, -v        Stream formatted Claude output live
#
# For minor single-pass corrections that do not need a review cycle,
# use revision-minor.sh instead.
#
# See docs/guide/workflows.md for the dual-flow model.
# See docs/standards/workflow-scripts.md for the standard this script follows.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRAFT="${SCRIPT_DIR}/steps/revision-draft.sh"
REFINE="${SCRIPT_DIR}/steps/revision-refine.sh"

show_usage() {
    cat <<EOF
Usage: $(basename "$0") "description of changes needed" [options]
       $(basename "$0") --task-file path/to/task.md [options]

Runs the two-step revision cycle:
  1. revision-draft   — writes the change, opens an unreviewed PR
  2. revision-refine  — FRESH context: fidelity check, peer review, corrections

Arguments:
  "description"        The rework task (short single-line descriptions)
  --task-file <path>   Read the task from a file — for multi-paragraph tasks or
                       anything with quotes/newlines. Mutually exclusive with
                       the positional description.

Options:
  --pr <number>        Rework an EXISTING PR instead of opening a new one
  --repo <path>        Target repo (default: the repo containing the cwd)
  --verbose, -v        Stream formatted Claude output live

Examples (flags FIRST, positionals LAST):
  $(basename "$0") "restructure the auth flow to use sessions"
  $(basename "$0") --pr 42 "address the findings from PR #42"
  $(basename "$0") --repo /opt/skyy-net/skyy-command --task-file /tmp/task.md

For minor single-pass fixes, use revision-minor.sh.
EOF
}

DESCRIPTION=""
TASK_FILE=""
PR_NUMBER=""
REPO_TARGET=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task-file)
            [[ $# -ge 2 ]] || { echo "Error: --task-file requires a path" >&2; exit 1; }
            TASK_FILE="$2"; shift 2 ;;
        --pr)
            [[ $# -ge 2 ]] || { echo "Error: --pr requires a PR number" >&2; exit 1; }
            PR_NUMBER="$2"; shift 2 ;;
        --repo)
            [[ $# -ge 2 ]] || { echo "Error: --repo requires a path" >&2; exit 1; }
            REPO_TARGET="$2"; shift 2 ;;
        --verbose|-v)
            VERBOSE=true; shift ;;
        --help|-h)
            show_usage; exit 0 ;;
        -*)
            echo "Error: unknown option '$1'" >&2; exit 1 ;;
        *)
            if [[ -z "$DESCRIPTION" ]]; then DESCRIPTION="$1"; shift
            else echo "Error: unexpected positional argument '$1'" >&2; exit 1; fi ;;
    esac
done

if [[ -n "$DESCRIPTION" && -n "$TASK_FILE" ]]; then
    echo "Error: cannot use both a positional description and --task-file" >&2; exit 1
fi
if [[ -z "$DESCRIPTION" && -z "$TASK_FILE" ]]; then
    show_usage >&2; exit 1
fi
if [[ -n "$PR_NUMBER" && ! "$PR_NUMBER" =~ ^[0-9]+$ ]]; then
    echo "Error: --pr requires a positive integer" >&2; exit 1
fi
# Validate here as well as in the children. The children would catch it, but the
# failure would arrive wrapped in "revision-draft FAILED", which reads like a
# model failure rather than a typo in the path.
if [[ -n "$TASK_FILE" && ! -r "$TASK_FILE" ]]; then
    echo "Error: task file not readable: ${TASK_FILE}" >&2; exit 1
fi
for child in "$DRAFT" "$REFINE"; do
    [[ -x "$child" ]] || { echo "Error: child workflow not executable: ${child}" >&2; exit 1; }
done

# Rebuild the child argument list ONCE so both children receive an identical
# task. Refine needs the original task to check fidelity against what was
# delivered — passing it only to draft would silently reduce refine to an
# internal-quality check, which is the weaker of the two.
CHILD_ARGS=()
[[ -n "$REPO_TARGET" ]] && CHILD_ARGS+=(--repo "$REPO_TARGET")
$VERBOSE && CHILD_ARGS+=(--verbose)
TASK_ARGS=()
if [[ -n "$TASK_FILE" ]]; then TASK_ARGS+=(--task-file "$TASK_FILE"); else TASK_ARGS+=("$DESCRIPTION"); fi

echo "================================================================"
echo "  REVISION WORKFLOW (parent: draft → refine)"
echo "================================================================"
if [[ -n "$PR_NUMBER" ]]; then
    echo "  Target      : PR #${PR_NUMBER} (rework in place)"
else
    echo "  Target      : new branch and PR"
fi
echo "  Step 1      : revision-draft   (writes the change)"
echo "  Step 2      : revision-refine  (fresh context: reviews + corrects)"
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# Step 1 — DRAFT
# ---------------------------------------------------------------------------
DRAFT_ARGS=("${CHILD_ARGS[@]}")
[[ -n "$PR_NUMBER" ]] && DRAFT_ARGS+=(--pr "$PR_NUMBER")

echo "→ [1/2] revision-draft…"
echo
DRAFT_LOG="$(mktemp)"
trap 'rm -f "$DRAFT_LOG"' EXIT
if ! "$DRAFT" "${DRAFT_ARGS[@]}" "${TASK_ARGS[@]}" 2>&1 | tee "$DRAFT_LOG"; then
    echo >&2
    echo "✗ revision-draft FAILED — stopping before refine." >&2
    echo "  Nothing was reviewed. Inspect the draft output above; the worktree (if any) persists." >&2
    exit 1
fi

# The PR URL printed as the child's final line IS the handoff. It is also the
# child's completion contract, so a run that produced no URL did not finish.
PR_URL=$(grep -oE 'https://github\.com/[^ )]+/pull/[0-9]+' "$DRAFT_LOG" | tail -1)
if [[ -z "$PR_URL" ]]; then
    echo >&2
    echo "✗ revision-draft produced no PR URL — cannot hand off to refine." >&2
    echo "  The draft step must open (or update) a PR and print its URL as its final line." >&2
    exit 1
fi
DRAFT_PR="${PR_URL##*/}"

echo
echo "================================================================"
echo "  [1/2] draft complete → PR #${DRAFT_PR}"
echo "  ${PR_URL}"
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# Step 2 — REFINE (fresh context, same task, against the draft's PR)
# ---------------------------------------------------------------------------
echo "→ [2/2] revision-refine on PR #${DRAFT_PR}…"
echo
if ! "$REFINE" "${CHILD_ARGS[@]}" --pr "$DRAFT_PR" "${TASK_ARGS[@]}"; then
    echo >&2
    echo "✗ revision-refine FAILED on PR #${DRAFT_PR}." >&2
    echo "  The draft PR EXISTS and is unreviewed — it must not be merged as-is." >&2
    echo "  Re-run just the review step:" >&2
    echo "    ${REFINE} --pr ${DRAFT_PR} <the same task>" >&2
    exit 1
fi

echo
echo "================================================================"
echo "  REVISION WORKFLOW COMPLETE — PR #${DRAFT_PR} drafted and refined"
echo "================================================================"
echo
echo "  ${PR_URL}"
echo
echo "To clean up when done:"
echo "  /cleanup-merged-worktrees    (two worktrees this run — one per step)"
echo
