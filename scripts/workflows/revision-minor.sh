#!/usr/bin/env bash
#
# revision-minor.sh — the REVISION-MINOR workflow (PARENT)
# Minor scoped corrections, delivered as a reviewed PR.
#
# This is a PARENT workflow: pure bash orchestration over two independent
# child runs. It calls no model itself, so it has no MODEL_KEY and no
# COMPLETION_PATTERN — each child carries its own.
#
#   1. children/revision-draft-minor.sh   — writes the change, opens an UNREVIEWED PR
#   2. children/revision-refine-minor.sh  — FRESH context: reviews and corrects it
#   3. review-pr.sh                 — decide-only: MERGE, or HOLD + a runway
#
# review-pr is called at the TOP level, not from children/, and that is
# deliberate. children/ means "ONLY a parent invokes this" — revision-draft-minor
# alone produces an unreviewed PR that is never a deliverable. review-pr is a
# complete, useful act on ANY returned PR whatever produced it, so it stays
# independently dispatchable. A parent calling a top-level workflow is normal;
# the composition graph is not a tree, which is what makes these recombinable.
#
# ON A HOLD THE PARENT LOOPS BACK EXACTLY ONCE. Self-correction plateaus at
# ~3-5 passes; past it the same model justifies rather than corrects (watched
# directly: PR #224 pass 8 re-reviewed pass 7's unchanged tree and re-issued the
# same runway). Counting across the pipeline — refine 1, review-pr 2, refine 3,
# review-pr 4 — one loop-back lands inside the band and two would clear it. The
# research sets the number, so it is not a flag.
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
#   ./revision-minor.sh "description of changes needed" [options]
#   ./revision-minor.sh --task-file path/to/task.md [options]
#
# Options:
#   --pr <number>        Rework an EXISTING PR (draft updates it in place)
#   --repo <path>        Target repo (explicit identity, never derived from cwd)
#   --verbose, -v        Stream formatted Claude output live
#
# The LIGHT tier. Same three-child shape as revision.sh — deliberately, so
# there is one mental model rather than two — but the middle child runs ONE
# review lens (code-reviewer) instead of four, on a cheaper model with half the
# turn budget. That is the whole difference, and it is a real one: roughly $7
# against $25-50. If the review keeps surfacing structural or standards
# problems, the task was mis-sized and belongs on revision.sh.
#
# See docs/guide/workflows.md for the dual-flow model.
# See docs/standards/workflow-scripts.md for the standard this script follows.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRAFT="${SCRIPT_DIR}/children/revision-draft-minor.sh"
REFINE="${SCRIPT_DIR}/children/revision-refine-minor.sh"
PR_REVIEW="${SCRIPT_DIR}/children/review-pr.sh"

show_usage() {
    cat <<EOF
Usage: $(basename "$0") "description of changes needed" [options]
       $(basename "$0") --task-file path/to/task.md [options]

Runs the three-child minor-revision cycle:
  1. revision-draft-minor   — writes the change, opens an unreviewed PR
  2. revision-refine-minor  — FRESH context: fidelity, ONE review lens, corrections
  3. review-pr              — decide-only disposition: MERGE, or HOLD with a runway

On HOLD(redispatch) the parent loops back ONCE (refine -> review-pr) and then
stops regardless of outcome. On HOLD(needs-assistance) it stops immediately —
more passes cannot produce a human ruling.

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

For multi-file or architectural rework, use revision.sh.
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
# failure would arrive wrapped in "revision-draft-minor FAILED", which reads like a
# model failure rather than a typo in the path.
if [[ -n "$TASK_FILE" && ! -r "$TASK_FILE" ]]; then
    echo "Error: task file not readable: ${TASK_FILE}" >&2; exit 1
fi
for child in "$DRAFT" "$REFINE" "$PR_REVIEW"; do
    [[ -x "$child" ]] || { echo "Error: child workflow not executable: ${child}" >&2; exit 1; }
done

# One trap for every temp log this run creates (draft's, plus one per review-pr).
TMP_LOGS=()
cleanup_tmp_logs() { [[ ${#TMP_LOGS[@]} -gt 0 ]] && rm -f "${TMP_LOGS[@]}"; return 0; }
trap cleanup_tmp_logs EXIT

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
echo "  REVISION-MINOR WORKFLOW (parent: draft → refine → review-pr)"
echo "================================================================"
if [[ -n "$PR_NUMBER" ]]; then
    echo "  Target      : PR #${PR_NUMBER} (rework in place)"
else
    echo "  Target      : new branch and PR"
fi
echo "  Child 1     : revision-draft-minor   (writes the change)"
echo "  Child 2     : revision-refine-minor  (fresh context: one lens, corrects)"
echo "  Child 3     : review-pr              (decide-only: MERGE | HOLD + runway)"
echo "  On HOLD     : ONE loop-back (refine → review-pr), then stop. Never twice."
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# Step 1 — DRAFT
# ---------------------------------------------------------------------------
DRAFT_ARGS=("${CHILD_ARGS[@]}")
[[ -n "$PR_NUMBER" ]] && DRAFT_ARGS+=(--pr "$PR_NUMBER")

echo "→ [1/3] revision-draft-minor…"
echo
DRAFT_LOG="$(mktemp)"
TMP_LOGS+=("$DRAFT_LOG")
if ! "$DRAFT" "${DRAFT_ARGS[@]}" "${TASK_ARGS[@]}" 2>&1 | tee "$DRAFT_LOG"; then
    echo >&2
    echo "✗ revision-draft-minor FAILED — stopping before refine." >&2
    echo "  Nothing was reviewed. Inspect the draft output above; the worktree (if any) persists." >&2
    exit 1
fi

# The PR URL printed as the child's final line IS the handoff. It is also the
# child's completion contract, so a run that produced no URL did not finish.
PR_URL=$(grep -oE 'https://github\.com/[^ )]+/pull/[0-9]+' "$DRAFT_LOG" | tail -1)
if [[ -z "$PR_URL" ]]; then
    echo >&2
    echo "✗ revision-draft-minor produced no PR URL — cannot hand off to refine." >&2
    echo "  The draft step must open (or update) a PR and print its URL as its final line." >&2
    exit 1
fi
DRAFT_PR="${PR_URL##*/}"

echo
echo "================================================================"
echo "  [1/3] draft complete → PR #${DRAFT_PR}"
echo "  ${PR_URL}"
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# Activities (external I/O — never inline in a parent)
# ---------------------------------------------------------------------------
# A parent is orchestration only: it decides IF, WHEN and WHAT to call. Anything
# that touches the outside world is an ACTIVITY and lives in activities/, per
# the Temporal Standard §3.1 ("no external I/O, deterministic") — a workflow
# that made a network call could not replay, so this is not a style preference,
# it is the boundary the engine enforces. wait_for_ci polls the GitHub API; it
# is an activity, and every PR-producing parent will want it.
#
# NOTE what deliberately stays HERE: parsing the verdict line and extracting the
# PR URL. Those are pure string→decision, no I/O, and they ARE the "if/then,
# what to call next" that a parent exists to hold.
source "${SCRIPT_DIR}/activities/wait-for-ci.sh"

# ---------------------------------------------------------------------------
# run_refine <label> [--correction-pass]  — the review-and-correct child
# ---------------------------------------------------------------------------
run_refine() {
    local label="$1"; shift
    local args=("${CHILD_ARGS[@]}" "$@")
    $CI_UNSETTLED && args+=(--ci-unsettled)

    echo "→ ${label} revision-refine-minor on PR #${DRAFT_PR}…"
    echo
    if ! "$REFINE" "${args[@]}" --pr "$DRAFT_PR" "${TASK_ARGS[@]}"; then
        echo >&2
        echo "✗ revision-refine-minor FAILED on PR #${DRAFT_PR}." >&2
        echo "  The PR EXISTS and is unreviewed — it must not be merged as-is." >&2
        echo "  Re-run just the review step:" >&2
        echo "    ${REFINE} --pr ${DRAFT_PR} <the same task>" >&2
        return 1
    fi
}

# ---------------------------------------------------------------------------
# run_pr_review <label> — the disposition child; echoes its routing token
# ---------------------------------------------------------------------------
# review-pr lives at the TOP level, not in children/, and is called in place.
# children/ means "only a parent invokes this" — revision-draft-minor alone produces
# an unreviewed PR that is never a deliverable. review-pr is a complete, useful
# act on ANY returned PR regardless of which workflow produced it, so it stays
# independently dispatchable. A parent calling a top-level workflow is normal:
# the composition graph is not a tree, and that is what makes these recombinable
# rather than a fixed hierarchy.
run_pr_review() {
    local label="$1"
    local log; log="$(mktemp)"
    TMP_LOGS+=("$log")

    echo "→ ${label} review-pr on PR #${DRAFT_PR}…"
    echo
    if ! "$PR_REVIEW" "${CHILD_ARGS[@]}" --pr "$DRAFT_PR" 2>&1 | tee "$log"; then
        echo >&2
        echo "✗ review-pr FAILED on PR #${DRAFT_PR}." >&2
        echo "  The PR was drafted and refined but NOT dispositioned. Run it by hand:" >&2
        echo "    ${PR_REVIEW} --pr ${DRAFT_PR}" >&2
        return 1
    fi

    # The terminal VERDICT line IS the interface — review-pr aggregates the
    # per-finding hold_kind values into one routing token so the caller never
    # re-derives a judgement the reviewer already made.
    VERDICT_LINE=$(grep -oE '^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$' "$log" | tail -1)
    if [[ -z "$VERDICT_LINE" ]]; then
        echo >&2
        echo "✗ review-pr produced no parseable VERDICT line — cannot route." >&2
        echo "  Treating as needs-assistance. Inspect PR #${DRAFT_PR} by hand." >&2
        VERDICT_LINE="VERDICT: HOLD - needs-assistance"
    fi
}

finish() {
    echo
    echo "================================================================"
    echo "  $1"
    echo "================================================================"
    echo
    echo "  ${PR_URL}"
    echo
    [[ -n "${2:-}" ]] && { echo "$2"; echo; }
    echo "To clean up when done:"
    echo "  /cleanup-merged-worktrees    (one worktree per child run)"
    echo
}

# ---------------------------------------------------------------------------
# Step 2 — REFINE (fresh context, same task, against the draft's PR)
# ---------------------------------------------------------------------------
wait_for_ci "$DRAFT_PR"
run_refine "[2/3]" || exit 1

# ---------------------------------------------------------------------------
# Step 3 — PR-REVIEW, then route on its verdict
# ---------------------------------------------------------------------------
# EXACTLY ONE loop-back. Not a tuning knob, and deliberately not configurable.
#
# Self-correction plateaus at roughly 3-5 passes: the same model carries the
# same blind spots, and past the plateau it stops correcting and starts
# justifying. Watched directly on this fleet — PR #224 reached EIGHT review-pr
# passes, and pass 8 reviewed the same tree as pass 7 with no commits between
# them, re-issuing the same runway.
#
# Counting the correction passes across the PIPELINE, not within any one child:
#   refine = 1 · review-pr = 2 · [loop] refine = 3 · review-pr = 4
# One loop-back lands at four, inside the band. Two would reach six, past it.
# Stopping at zero loop-backs would discard the passes that genuinely do improve
# the work — the plateau is a ceiling, not an argument against the first climb.
#
# So the bound is set by the research, not by a budget guard, and a knob here
# would only invite someone to tune past the point where the extra passes
# produce justification instead of correction.
wait_for_ci "$DRAFT_PR"
run_pr_review "[3/3]" || exit 1

case "$VERDICT_LINE" in
    "VERDICT: MERGE")
        finish "REVISION-MINOR COMPLETE — PR #${DRAFT_PR} drafted, refined, dispositioned MERGE" \
               "  review-pr found nothing holding this PR. Ready to merge."
        exit 0 ;;

    "VERDICT: HOLD - needs-assistance")
        # No loop, ever. A human ruling is not something more passes can produce,
        # so spending them is pure waste.
        finish "REVISION-MINOR COMPLETE — PR #${DRAFT_PR} HELD, needs a human" \
               "  review-pr found at least one item only YOU can rule on. No automated
  loop-back was attempted: more passes cannot produce a human decision.
  The runway is in the pr_review: block on the PR."
        exit 0 ;;
esac

# HOLD - redispatch → the one loop-back
echo
echo "================================================================"
echo "  [3/3] HOLD (redispatch) — the runway closes with a scoped fix."
echo "  Looping back ONCE: refine → review-pr. This is the last automated pass."
echo "================================================================"
echo

wait_for_ci "$DRAFT_PR"
run_refine "[loop 1/2]" --correction-pass || exit 1

wait_for_ci "$DRAFT_PR"
run_pr_review "[loop 2/2]" || exit 1

if [[ "$VERDICT_LINE" == "VERDICT: MERGE" ]]; then
    finish "REVISION-MINOR COMPLETE — PR #${DRAFT_PR} MERGE after one correction loop" \
           "  The runway closed unattended. Ready to merge."
    exit 0
fi

finish "REVISION-MINOR COMPLETE — PR #${DRAFT_PR} still HELD after the correction loop" \
       "  The automated loop is SPENT — one loop-back is the cap, because passes
  beyond it produce justification rather than correction. This PR now needs you.
  What remains is in the latest pr_review: block on the PR
  (${VERDICT_LINE#VERDICT: })."
exit 0
