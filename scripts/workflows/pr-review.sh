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
COMPLETION_PATTERN='^VERDICT: (MERGE|HOLD)'
source "${SCRIPT_DIR}/lib/run-claude.sh"
source "${SCRIPT_DIR}/lib/shared-prompts.sh"

PROMPT="You are executing the PR-REVIEW workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}), disposition pass ${THIS_PASS}.

You are the DISPOSITION ENGINE — the fresh-eyes product owner the producing run cannot be on its own work. The run that produced this PR is commitment-biased: it authored these choices, so it defends them and rationalizes its own findings away. You have no such investment. Your job is to force EVERY surfaced item to a terminal disposition, verifying each claim against the actual code rather than trusting the producing run's account of it.

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
- Deferred Work entries (each deferral is an item)
- Existing conditions / pre-existing issues it flagged but didn't fix
- Friction / reflection notes that imply an unresolved problem
- Anything in the DIFF that looks wrong but went unmentioned (your fresh eyes — the producing run's blind spots are exactly what you exist to catch)

Give each item a stable kebab-slug id (reuse prior-pass ids per Stage 1) and a category from this fixed enum (extend if truly needed, NEVER rename — recurrence mining keys on these): correctness | security | standards-implication | scope | deferral | existing-condition | friction | test-gap | doc-drift.

## Stage 3: DISPOSITION (the core — no rubber stamps)
For EACH enumerated item, reach exactly one terminal disposition using genuine /decide (reframe: is this the real issue, or a symptom of an upstream one?) + /best-practices (what does the correct approach demand?) reasoning:

- **FIXED** — already correctly resolved in this PR. VERIFY against the code (Read/Grep/Glob) that it truly is; do not take the producing run's word.
- **REJECTED** — not a real issue. State WHY with reasoning (agent misread, non-issue in context, the concern doesn't apply). Rejection-with-reasoning is a valid disposition; \"recommend we move on\" is NOT — it is silent dismissal and is FORBIDDEN.
- **DEFERRED** — genuinely out of scope / non-blocking, WITH a pointer to where it is tracked (issue #, planning doc, loose-ends file). A deferral without a location is silent dismissal and is forbidden.

The producing run's excuses (\"out of scope\", \"existing condition\", \"pre-existing\") are claims to VERIFY, not conclusions to accept. Run each down to the real issue before dispositioning. This is the anti-rug-sweeping core of the workflow.

For items that genuinely need a fix NOW (in-scope, blocking, not deferrable), do NOT fix them and do NOT dispatch. Instead mark them for a fix dispatch and, in Stage 5, write the scoped dispatch_context.

## Stage 4: VERDICT
Reach exactly one terminal verdict:
- **MERGE** — every item dispositioned, nothing blocking. (You do NOT merge — a human/parent does. This verdict means \"clean, safe to merge,\" with a one-line rationale.)
- **HOLD** — not mergeable. Enumerate reasons, each tagged by WHY it is human-shaped or fix-shaped:
  - \`operator-action\` (sudo/infra/secrets — only the operator can do it)
  - \`standards\` (a standards-ratification decision — PM3 + human)
  - \`sprints\` (a sprints.md sequencing decision — operator-owned)
  - \`scope\` (a scope question a human must answer)
  - \`fix-needed\` (a fix dispatch would resolve it — carries dispatch_context in Stage 5)
  - \`no-reflection\` (producing run left no reflection — likely early-stopped)

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
  verdict: MERGE | HOLD
  findings:
    - id: <stable-slug>
      category: <from the fixed enum>
      disposition: fixed | rejected | deferred
      pointer: <where tracked, if deferred>
  hold_reasons:
    - tag: operator-action | standards | sprints | scope | fix-needed | no-reflection
      note: <one line>
      dispatch_context: |          # ONLY on fix-needed tags — the scoped, ready-to-fire revision task
        <the exact scoped task a future revision.sh --pr ${PR_NUMBER} would carry:
         which findings to fix, what to change, and explicitly what NOT to touch.
         Written so a human or a parent workflow can fire it verbatim.>
  redispatched: false             # always false — this engine never dispatches
\`\`\`

**gh-monitor safety (binding):** the comment MUST NOT contain any line that STARTS with \`@claude\` — gh-monitor would parse it and auto-dispatch a workflow. If you must reference a dispatch command illustratively, put it inside a code fence (gh-monitor strips fences before matching). Your dispatch_context describes the task in prose/yaml; it never emits a live \`@claude\` trigger line.

## Stage 6: PRINT THE VERDICT
As the FINAL line of your output, print exactly one of:
    VERDICT: MERGE
    VERDICT: HOLD
This is the completion signal. Printing it is how the run is known to have completed (a headless run that ends without it is treated as an early-stop). Do not print it until the comment is posted.

${DECISION_LOG_AND_REFLECTION}

RULES:
- DECIDE-ONLY: never merge, close, fix, dispatch, or edit standards/sprints. Those are HOLD reasons, never actions.
- Every item ends FIXED / REJECTED-with-reasoning / DEFERRED-with-pointer. \"Recommend we move on\" is forbidden.
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
