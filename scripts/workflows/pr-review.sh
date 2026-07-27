#!/usr/bin/env bash
#
# pr-review.sh — the DISPOSITION ENGINE
# Mechanizes the PM disposition ritual on a returned PR: enumerate every
# surfaced item (issue, loose end, deferral, existing condition, friction),
# force each to a terminal disposition (FIXED / REJECTED / DEFERRED) via the
# fresh-eyes scrutiny a producing run cannot do on itself, and end in a
# VERDICT (MERGE | HOLD). Decide-only.
#
# DECIDE-ONLY BY DESIGN (additive-automation): this workflow takes NO actions.
# It never merges, never closes, never fixes live, never dispatches, never
# edits standards/sprints. When fixes are genuinely needed, it writes a scoped,
# ready-to-fire dispatch_context into the PR comment (a HOLD/fix-needed) — a
# human fires it today; a parent workflow / Temporal fires it once CPI evidence
# earns that autonomy. Fix-dispatch authority is earned exactly like merge
# authority. This is the Temporal child-workflow shape: return a decision; let
# the parent decide whether to act on it.
#
# Distinct from review-runs.sh: that analyzes run LOGS for process CPI; this
# reviews PR CONTENT for disposition. Different organs; they feed each other
# (the yaml findings' category recurrence is a content-side CPI signal).
#
# Invocation:
#   ./pr-review.sh --pr <N>
#   ./pr-review.sh --pr <N> --repo /opt/skyy-net/mdc-master-planning --verbose
#
# Options:
#   --pr <N>       PR number to disposition (required)
#   --repo <path>  Target repo (explicit identity, never derived; default: cwd)
#   --verbose, -v  Stream formatted Claude output live
#
# Output: a single disposition comment on the PR (human table + machine yaml).
#         Terminal line: "VERDICT: MERGE" or "VERDICT: HOLD".
# Logging: JSONL log to <repo>/.claude/logs/pr-review-<ts>.jsonl
# See docs/standards/workflow-scripts.md for the standard this script follows.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORMATTER="${SCRIPT_DIR}/lib/format-stream.sh"

MAX_TURNS=120

show_usage() {
    cat <<EOF
Usage: $(basename "$0") --pr <N> [options]

Dispositions every item surfaced on a returned PR and ends in a verdict.
Decide-only: never merges, fixes, dispatches, or edits — writes its decision
(and a ready-to-fire dispatch_context for any fix-needed HOLD) to the PR.

Options:
  --pr <N>       PR number to disposition (required)
  --repo <path>  Target repo (default: the repo containing the cwd)
  --verbose, -v  Stream formatted Claude output live

Examples:
  $(basename "$0") --pr 42
  $(basename "$0") --pr 42 --repo /opt/skyy-net/mdc-master-planning --verbose
EOF
}

PR_NUMBER=""
REPO_TARGET=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr)
            if [[ $# -lt 2 ]]; then echo "Error: --pr requires a number" >&2; exit 1; fi
            PR_NUMBER="$2"; shift 2 ;;
        --repo)
            if [[ $# -lt 2 ]]; then echo "Error: --repo requires a path" >&2; exit 1; fi
            REPO_TARGET="$2"; shift 2 ;;
        --verbose|-v)
            VERBOSE=true; shift ;;
        --help|-h)
            show_usage; exit 0 ;;
        -*)
            echo "Error: unknown option '$1'" >&2; exit 1 ;;
        *)
            echo "Error: unexpected positional argument '$1'" >&2; exit 1 ;;
    esac
done

if [[ -z "$PR_NUMBER" ]]; then show_usage >&2; exit 1; fi
if ! [[ "$PR_NUMBER" =~ ^[0-9]+$ ]]; then echo "Error: --pr requires a positive integer" >&2; exit 1; fi

# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------
for cmd in claude gh jq; do
    command -v "$cmd" &>/dev/null || { echo "Error: '$cmd' not found in PATH" >&2; exit 1; }
done

# Explicit target repo (--repo) — identity is explicit, never derived (§7.5).
if [[ -n "$REPO_TARGET" ]]; then
    [[ -d "$REPO_TARGET" ]] || { echo "Error: --repo path not found: ${REPO_TARGET}" >&2; exit 1; }
    git -C "$REPO_TARGET" rev-parse --show-toplevel &>/dev/null || { echo "Error: --repo path is not a git repository: ${REPO_TARGET}" >&2; exit 1; }
    cd "$REPO_TARGET"
fi

git rev-parse --show-toplevel &>/dev/null || { echo "Error: not inside a git repository" >&2; exit 1; }
[[ -x "$FORMATTER" ]] || { echo "Error: stream formatter not found at ${FORMATTER}" >&2; exit 1; }

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Stage 0 — mechanical prechecks (bash-side, before any Claude spend)
# ---------------------------------------------------------------------------
echo "→ Fetching PR #${PR_NUMBER} metadata..."
PR_JSON=$(gh pr view "$PR_NUMBER" --json headRefName,state,mergeable,isDraft 2>/dev/null || echo "")
if [[ -z "$PR_JSON" ]]; then
    echo "Error: PR #${PR_NUMBER} not found (or gh not authenticated for this repo)" >&2
    exit 1
fi
PR_BRANCH=$(echo "$PR_JSON" | jq -r '.headRefName // ""')
PR_STATE=$(echo "$PR_JSON" | jq -r '.state // ""')
PR_MERGEABLE=$(echo "$PR_JSON" | jq -r '.mergeable // "UNKNOWN"')

if [[ "$PR_STATE" != "OPEN" ]]; then
    echo "Error: PR #${PR_NUMBER} is ${PR_STATE}, not OPEN — nothing to disposition" >&2
    exit 1
fi
if [[ -z "$PR_BRANCH" ]]; then
    echo "Error: could not determine branch for PR #${PR_NUMBER}" >&2
    exit 1
fi

# Prior-pass detection: a pr-review comment already on the thread carries a
# `pass:` marker in its yaml block. This run is the next pass. Stable-id reuse
# depends on the agent reading the prior block, so we surface its presence.
PRIOR_PASS=$(gh pr view "$PR_NUMBER" --json comments \
             --jq '[.comments[].body | select(test("pr_review:"))] | length' 2>/dev/null || echo "0")
THIS_PASS=$(( PRIOR_PASS + 1 ))

echo "  Branch     : ${PR_BRANCH}"
echo "  State      : ${PR_STATE} · mergeable=${PR_MERGEABLE}"
echo "  Pass       : ${THIS_PASS} (prior pr-review blocks on thread: ${PRIOR_PASS})"

# ---------------------------------------------------------------------------
# Naming and paths
# ---------------------------------------------------------------------------
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
WORKTREE_NAME="pr-review-${TIMESTAMP}"

LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/pr-review-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"

echo "================================================================"
echo "  PR-REVIEW WORKFLOW (disposition engine — decide-only)"
echo "================================================================"
echo "  Repo       : ${REPO_ROOT}"
echo "  PR         : #${PR_NUMBER} (${PR_BRANCH})"
echo "  Pass       : ${THIS_PASS}"
echo "  Worktree   : ${WORKTREE_NAME}"
echo "  Max turns  : ${MAX_TURNS}"
echo "  Verbose    : ${VERBOSE}"
echo "  Log file   : ${LOG_FILE}"
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# Worktree on the PR branch (fresh checkout — the fresh-eyes property)
# ---------------------------------------------------------------------------
WORKTREE_PATH=".claude/worktrees/${WORKTREE_NAME}"
mkdir -p .claude/worktrees
echo "→ Fetching latest PR branch state..."
git fetch origin "$PR_BRANCH"
echo "→ Creating worktree at ${WORKTREE_PATH}..."
git worktree add -f "$WORKTREE_PATH" "origin/${PR_BRANCH}"

# ---------------------------------------------------------------------------
# run_claude helper + shared prompt blocks
# ---------------------------------------------------------------------------
MODEL_KEY="pr-review"
COMPLETION_PATTERN='^VERDICT: (MERGE-AFTER-EXPORTS|MERGE|HOLD)'
source "${SCRIPT_DIR}/lib/run-claude.sh"
source "${SCRIPT_DIR}/lib/shared-prompts.sh"

PROMPT="You are executing the PR-REVIEW workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}), disposition pass ${THIS_PASS}.

## YOUR PURPOSE — read this first, it is your value function

Quality control identifies the issues; PR review's entire purpose is to get every uncovered issue actually CORRECTED — the noted bug, the missing piece, the broken part — so the result is enterprise-ready, robust code we are genuinely proud of. You are the step that converts findings into corrections. **Minimizing effort, economizing dispatches, or rationalizing issues away is the opposite of your job.**

You do not fix the code yourself (you are decide-only). But 'converting a finding into a correction' means, for each item, exactly one of: proving it is genuinely already fixed (verified against the code), issuing a MANDATED fix (a scoped dispatch a human/parent will fire), or rejecting it with real reasoning because it is not actually an issue. Burying it, parking it nowhere, or waving it off as too-small / pre-existing / too-expensive is failure. If you find yourself building a case for why an issue does NOT need to be dealt with, stop — that instinct is the exact rug-sweep you exist to prevent.

You are the DISPOSITION ENGINE — the fresh-eyes product owner the producing run cannot be on its own work. The run that produced this PR is commitment-biased: it authored these choices, so it defends them and rationalizes its own findings away. You have no such investment. Force EVERY surfaced item to a terminal disposition, verifying each claim against the actual code rather than trusting the producing run's account of it.

**You take NO actions.** You do NOT merge, close, fix, dispatch, or edit standards/sprints. Your entire output is ONE disposition comment on the PR plus a final VERDICT line. When fixes are genuinely needed, you WRITE a scoped, ready-to-fire dispatch context into the comment — you never fire it. (A human fires it today; a parent workflow fires it once earned. Fix-dispatch authority is earned, exactly like merge authority.)

${HEADLESS_EXECUTION_GUARD}

EXECUTION ORDER IS MANDATORY. If a stage has nothing to address, emit: ## Stage N: SKIPPED — <one-line reason>.

---

## Stage 1: VERIFY + GATHER
FIRST: verify this PR targets THIS repo. If the PR's changed files reference a different repository than your worktree, STOP — report \"DISPATCH MISCONFIGURATION: PR targets <repo X>, worktree is <repo Y>; re-run with --repo <path>\" and do no further work.

Then gather the raw material (batch independent reads in one turn):
- The PR diff: run \`gh pr diff ${PR_NUMBER}\` (or \`git --no-pager diff origin/<base>...HEAD\`) to see what actually changed.
- The PR body: \`gh pr view ${PR_NUMBER} --json body,title --jq '.title, .body'\`.
- The self-review / reflection + decision-log comments: \`gh pr view ${PR_NUMBER} --json comments --jq '.comments[].body'\`. The producing run's Decision Log, Deferred Work, and Post-Run Reflection live here.
- **Prior pr-review comment (this is pass ${THIS_PASS}):** if ${PRIOR_PASS} > 0, find the prior comment(s) containing a \`pr_review:\` yaml block and READ them. You MUST reuse each prior finding's stable \`id\` slug verbatim when the same finding persists — stable ids are what make cross-pass and cross-PR recurrence tracking work. Only genuinely-new findings get new slugs.

**If there is NO reflection/decision-log comment at all:** that is itself a finding (the producing run may have early-stopped). Record it, and it becomes a HOLD reason \`no-reflection\`.

## Stage 2: ENUMERATE
List EVERY surfaced item, from all sources above, exhaustively. Sources of items:
- Explicit findings the producing run reported (Decision Log entries, review-agent findings it addressed or rejected)
- Deferred Work entries (each deferral is an item — and the producing run's deferral is a CLAIM to re-adjudicate, never an accepted outcome)
- Any issue the producing run labeled 'pre-existing' or 'existing condition' or 'out of scope' — these are enumerated like any other item and get dispositioned like any other item; the label grants NOTHING (see Stage 3)
- Friction / reflection notes that imply an unresolved problem
- Anything in the DIFF that looks wrong but went unmentioned (your fresh eyes — the producing run's blind spots are exactly what you exist to catch)

Give each item a stable kebab-slug id (reuse prior-pass ids per Stage 1) and a category from this fixed enum (extend if truly needed, NEVER rename — recurrence mining keys on these): correctness | security | standards-implication | scope | deferral | friction | test-gap | doc-drift. (There is deliberately NO 'existing-condition' category — it is abolished; a pre-existing issue is categorized by its actual type.)

## Stage 3: DISPOSITION (the core — no rubber stamps, no rug-sweeps)
For EACH enumerated item, reach exactly one terminal disposition using genuine /decide (reframe: is this the real issue, or a symptom of an upstream one?) + /best-practices (what does the correct approach demand?) reasoning. There are exactly three terminal dispositions — FIXED, REJECTED, DEFERRED — and their bars are HIGH:

- **FIXED** — already correctly resolved in this PR. VERIFY against the code (Read/Grep/Glob) that it truly is; do not take the producing run's word.
- **REJECTED** — not a real issue. State WHY with real reasoning (agent misread, non-issue in context, the concern demonstrably doesn't apply). Rejection-with-reasoning is valid; \"recommend we move on\" / \"low value\" / \"acceptable\" is NOT — that is silent dismissal and is FORBIDDEN.
- **DEFERRED** — permitted in EXACTLY TWO cases and NO others:
  (a) the work is **already scheduled** in a future sprint item that ALREADY EXISTS → pointer = that sprint item; OR
  (b) the work is **already in motion** in a live concurrent PR/dispatch → pointer = that PR/dispatch.
  DEFERRED points at work that is ALREADY scheduled or ALREADY happening. It NEVER creates a parking spot. You cannot write trackers (you are decide-only), so a valid deferral target must already exist — if the work has no existing home, it is NOT deferrable. **The reviewed PR (its body, thread, comments) is NEVER a valid pointer — merging it is the burial.** 'The architecture session' / 'the standards queue' are not pointers unless you name the committed file that queue reads from.

**VERIFY every DEFERRED pointer like research-critic verifies a citation — open it and confirm the item is ACTUALLY THERE** (\`gh issue view\`, \`gh pr view\`, or Read the committed file). A pointer to a location that does not contain the item is a disposition FAILURE, and it means the producing run tried to launder the deferral — reclassify it (it is FIXED-needed or a required export, not deferred) and count it in Stage 5's \`laundered_deferrals_caught\`.

**Binding prohibitions (operator doctrine — these are the failure modes you exist to stop):**
- **'Pre-existing' / 'existing condition' is ABOLISHED as an excuse — no exceptions.** An item is not exempt from correction because it predates this PR. Disposition it exactly like any other finding. (\"It's just a fancy way of saying I don't want to deal with this.\")
- **'Out of scope' is an INPUT, not a disposition.** An item the producing run called out-of-scope MUST still terminate in FIXED / REJECTED-with-reasoning / DEFERRED-to-already-existing-work. The label never appears as a terminal state.
- **Cost-of-dispatch is NEVER a disposition rationale.** \"The fix costs more than the error is worth\" / \"too expensive for something trivial\" is FORBIDDEN. The economics of a fix are the OPERATOR's call, never yours. If you genuinely believe a fix is disproportionate, that is a HOLD(scope) with the trade explicitly stated for the operator to rule on — never a self-granted waiver.

The producing run's excuses are claims to VERIFY, not conclusions to accept. Run each down to the real issue before dispositioning. This is the anti-rug-sweeping core of the workflow — it is the entire reason you exist.

For items that genuinely need a fix NOW (real issue, not already-fixed, not validly-deferrable, not a genuine rejection), do NOT fix them and do NOT dispatch. Mark them for a fix dispatch and write the scoped dispatch_context in Stage 5 (they make the verdict HOLD/fix-needed). For real, non-blocking follow-ups that have NO existing home (so cannot be deferred), see Stage 4's MERGE-AFTER-EXPORTS path — they must be exported to a live surface before the PR is merged, never buried by the merge.

## Stage 4: VERDICT
Reach exactly one terminal verdict from these THREE:
- **MERGE** — every item dispositioned, nothing blocking, and every DEFERRED item's pointer was verified present at an already-existing live home (nothing to export). (You do NOT merge — a human/parent does. This verdict means \"clean, safe to merge,\" with a one-line rationale.)
- **MERGE-AFTER-EXPORTS** — the PR itself is mergeable (strictly-better text, nothing blocking), BUT there are real, non-blocking follow-ups that have NO existing home yet. Do not hold a strictly-better PR hostage — but do not let the merge bury these either. Each becomes a REQUIRED EXPORT: it must land on a live surface (a phase-doc/roadmap gate item, a loose-ends entry, cpi-decisions.md, a GitHub issue, or the operator's sprint-candidate list — in a COMMITTED file) BEFORE the human merges. List them in Stage 5's \`residual_exports\`; the human-facing table must state plainly: \"merge only after these land on their live surfaces.\" (You cannot perform the exports — you are decide-only — so this verdict hands the operator a precise pre-merge checklist.)
- **HOLD** — not mergeable. Enumerate reasons, each tagged by WHY it is human-shaped or fix-shaped:
  - \`fix-needed\` (a real issue needs correcting — carries dispatch_context in Stage 5; this is the common blocking case)
  - \`operator-action\` (sudo/infra/secrets — only the operator can do it)
  - \`standards\` (a standards-ratification decision — PM3 + human)
  - \`sprints\` (a sprints.md sequencing decision — operator-owned)
  - \`scope\` (a scope/economics question a human must rule on — including \"is this fix worth it\")
  - \`no-reflection\` (producing run left no reflection — likely early-stopped)

Verdict discipline: if ANY item is fix-needed (a real correction is owed), the verdict is HOLD, not MERGE-AFTER-EXPORTS. MERGE-AFTER-EXPORTS is only for genuinely-non-blocking follow-ups that need a home. Never downgrade a fix-needed into an export to make a PR mergeable — that is the rug-sweep wearing a new hat.

## Stage 5: POST THE DISPOSITION COMMENT
Write the comment body to a temp file (e.g. /tmp/claude-pr-review-${PR_NUMBER}-<ts>.md — NOTE: never Edit it after writing; Write the full replacement if you must change it), then post via \`gh pr comment ${PR_NUMBER} --body-file <file>\`. The comment has TWO parts:

**Part 1 — human-readable disposition table:**
| Item (id) | Category | Disposition | Reasoning / Pointer |
one row per item, plus a one-line verdict rationale.

**Part 2 — machine-readable block** (fenced \`\`\`yaml). This IS the future Temporal activity-result contract — author it exactly:
\`\`\`yaml
pr_review:
  pr: ${PR_NUMBER}
  pass: ${THIS_PASS}
  verdict: MERGE | MERGE-AFTER-EXPORTS | HOLD
  findings:
    - id: <stable-slug>
      category: <from the fixed enum — NO existing-condition>
      disposition: fixed | rejected | deferred
      pointer: <REQUIRED if deferred — the already-existing sprint item or live PR, VERIFIED present. Never the reviewed PR.>
      pointer_verified: true|false   # deferred only — did you open it and confirm the item is there?
  residual_exports:                  # on MERGE-AFTER-EXPORTS: real non-blocking follow-ups with no home yet
    - item: <finding id>
      required_home: <the live committed surface it must land on before merge>
      present: false                 # false = not yet exported; MERGE is gated until it is true
  hold_reasons:
    - tag: fix-needed | operator-action | standards | sprints | scope | no-reflection
      note: <one line>
      dispatch_context: |          # ONLY on fix-needed tags — the scoped, ready-to-fire revision task
        <the exact scoped task a future revision.sh --pr ${PR_NUMBER} would carry:
         which findings to fix, what to change, and explicitly what NOT to touch.
         Written so a human or a parent workflow can fire it verbatim.>
  laundered_deferrals_caught: <int>  # deferrals the producing run pointed at a dead/invalid home that you reclassified (Layer-1 CPI signal)
  redispatched: false                # always false — this engine never dispatches
\`\`\`

**gh-monitor safety (binding):** the comment MUST NOT contain any line that STARTS with \`@claude\` — gh-monitor would parse it and auto-dispatch a workflow. If you must reference a dispatch command illustratively, put it inside a code fence (gh-monitor strips fences before matching). Your dispatch_context describes the task in prose/yaml; it never emits a live \`@claude\` trigger line.

## Stage 6: PRINT THE VERDICT
As the FINAL line of your output, print exactly one of:
    VERDICT: MERGE
    VERDICT: MERGE-AFTER-EXPORTS
    VERDICT: HOLD
This is the completion signal. Printing it is how the run is known to have completed (a headless run that ends without it is treated as an early-stop). Do not print it until the comment is posted.

${DECISION_LOG_AND_REFLECTION}

RULES:
- Your job is to get real issues CORRECTED, not to help the PR pass. If you catch yourself arguing for why an issue can be left alone, that is the rug-sweep — stop and disposition it honestly.
- DECIDE-ONLY: never merge, close, fix, dispatch, or edit standards/sprints. Those are HOLD reasons, never actions.
- Every item ends FIXED / REJECTED-with-reasoning / DEFERRED-to-already-existing-work. \"Recommend we move on\" / \"low value\" / \"acceptable as-is\" are forbidden.
- **'Pre-existing' / 'existing condition' is abolished as an excuse — no exceptions.** Disposition such items like any other.
- **'Out of scope' is an input, not a disposition** — it still terminates in FIXED / REJECTED / DEFERRED-to-existing-work.
- **Cost-of-dispatch is never a disposition rationale.** Disproportionate-fix belief = HOLD(scope) with the trade stated for the operator; never a self-granted waiver.
- **DEFERRED only points at work already scheduled (existing sprint item) or already in motion (live PR), pointer VERIFIED present.** The reviewed PR is never a valid pointer. No existing home = not deferrable (→ fix-needed or a required export).
- Verify claims against the code; do not trust the producing run's self-account — that is the entire point of a fresh-eyes pass.
- **Bash CWD persists between calls — never blind-chain a relative \`cd\`:** cd via absolute worktree-rooted paths (idempotent) or use absolute paths.
- **Re-Read before re-Editing anything you wrote earlier:** Edit needs a fresh Read; for the /tmp comment file, Write the full replacement instead of Editing.
- **Large-file reading:** \`wc -l\` before the FIRST Read of any markdown file; >500 lines → \`limit:200\` on the first Read.
- If you cannot complete a stage, stop and clearly report why (and still print a VERDICT line if you reached one — HOLD with a reason is the honest outcome of a blocked review)."

echo "→ Launching Claude in pr-review mode (disposition pass ${THIS_PASS})..."
echo

(
    cd "$WORKTREE_PATH"
    run_claude "$PROMPT"
)

echo
echo "================================================================"
echo "  PR-REVIEW WORKFLOW COMPLETE"
echo "================================================================"
echo
echo "Worktree: .claude/worktrees/${WORKTREE_NAME}"
echo "Log file: ${LOG_FILE}"
print_cycle_totals "$LOG_DIR"
echo
echo "The verdict + disposition are posted as a comment on PR #${PR_NUMBER}."
echo "To clean up when done:"
echo "  /cleanup-merged-worktrees    (after PR is merged or closed)"
echo
