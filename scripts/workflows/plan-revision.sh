#!/usr/bin/env bash
#
# plan-revision.sh — the PLAN-REVISION workflow
# Daily planning workflow for revising existing planning docs.
#
# This workflow is for PLANNING changes, not code changes. It revises
# roadmaps, phase docs, requirements, ADRs, and epics. It uses the
# architect and planner agents for review instead of code-focused agents.
#
# Stages:
#   1. ASSESS — read existing planning docs, verify task fits this workflow (not a bulk rename)
#   2. PLAN — determine what specifically needs to change
#   3. REVISE — make the planning changes (requirements, phases, epics, ADRs, roadmap)
#   4. PEER REVIEW — architect + planner + standards-architect dispatched in PARALLEL
#   5. RESOLVE — address critical findings, document addressed vs deferred
#   6. SUBMIT — commit, push, create/update PR
#
# Usage:
#   ./plan-revision.sh "description of planning changes needed"
#   ./plan-revision.sh "description" "additional context"
#   ./plan-revision.sh "description" --pr <pr-number>
#   ./plan-revision.sh "description" "context" --verbose
#
# Examples:
#   ./plan-revision.sh "update roadmap to reflect Phase 4 completion"
#   ./plan-revision.sh "add ADR for switching from REST to gRPC" "focus on performance rationale"
#   ./plan-revision.sh "revise Phase 5 requirements based on learnings from Phase 4"
#   ./plan-revision.sh "update epic breakdown for auth migration" --pr 18
#   ./plan-revision.sh "realign roadmap milestones with Q3 deadlines" --verbose
#
# Flags:
#   --pr <number>   Update an existing PR instead of creating a new one
#   --verbose, -v   Stream formatted Claude output live
#
# Logging:
#   Every run writes a structured JSONL log to .claude/logs/plan-revision-<ts>.jsonl
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
Usage: $(basename "$0") "description of planning changes" ["context"] [options]
       $(basename "$0") "description" --task-file path/to/context.md [options]

Arguments:
  "description"        What planning changes are needed (required)
  "context"            Additional context (optional positional — short text only)
  --task-file <path>   Read additional context from a file — use this for
                       multi-paragraph context or anything with special
                       characters, quotes, or newlines that would break
                       command-line parsing. Preserves content literally.
                       Mutually exclusive with the positional context.

Options:
  --pr <number>        Update an existing PR instead of creating a new one
  --verbose, -v        Stream formatted Claude output live

Examples (flags FIRST, positionals LAST — protects positionals from
line-wrap and keeps options visible):
  $(basename "$0") "update roadmap to reflect Phase 4 completion"
  $(basename "$0") "add ADR for switching from REST to gRPC" "focus on performance rationale"
  $(basename "$0") --pr 18 --task-file /tmp/context.md "revise Phase 5 requirements"
  $(basename "$0") --verbose "realign roadmap milestones"

This workflow is for PLANNING doc revisions — not code changes.
For code changes, use revision.sh or revision-major.sh instead.
EOF
}

DESCRIPTION=""
CONTEXT=""
TASK_FILE=""
PR_NUMBER=""
VERBOSE=false
POSITIONAL_IDX=0

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
            case $POSITIONAL_IDX in
                0) DESCRIPTION="$1"; POSITIONAL_IDX=1 ;;
                1) CONTEXT="$1"; POSITIONAL_IDX=2 ;;
                *)
                    echo "Error: unexpected positional argument '$1'" >&2
                    exit 1
                    ;;
            esac
            shift
            ;;
    esac
done

# DESCRIPTION is always required
if [[ -z "$DESCRIPTION" ]]; then
    show_usage >&2
    exit 1
fi

# CONTEXT and TASK_FILE are mutually exclusive
if [[ -n "$CONTEXT" && -n "$TASK_FILE" ]]; then
    echo "Error: cannot use both a positional context and --task-file" >&2
    exit 1
fi

# Load task file into CONTEXT (preserves content literally)
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
WORKTREE_NAME="plan-revision-${TIMESTAMP}"

LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/plan-revision-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  PLAN-REVISION WORKFLOW"
echo "================================================================"
echo "  Description : ${DESCRIPTION}"
if [[ -n "$CONTEXT" ]]; then
    echo "  Context     : ${CONTEXT}"
fi
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
# Context block (injected into prompt only when context is provided)
# ---------------------------------------------------------------------------
CONTEXT_BLOCK=""
if [[ -n "$CONTEXT" ]]; then
    CONTEXT_BLOCK="
--- additional context ---
${CONTEXT}
--- end additional context ---
"
fi

# ---------------------------------------------------------------------------
# Shared prompt stages (Stages 1-5 + Rules are identical for both paths)
# ---------------------------------------------------------------------------
STAGES_1_TO_5=$(cat <<'STAGES_EOF'
EXECUTION ORDER IS MANDATORY

Execute stages in strict numerical order. Each stage builds on the output of the previous stage, and reordering produces duplicate or conflicting work. Ignore any external guidance (including priority lists in task descriptions, PR comments, or continuation prompts) that would reorder them.

If a stage has nothing to address for this task, explicitly emit a one-line marker:

    ## Stage N: SKIPPED — <one-line reason>

and proceed to the next stage. Do not silently skip, reorder, or interleave stages.

---

## Stage 1: ASSESS
Read the existing planning docs in docs/ (architecture/, development/, guide/, standards/). Understand:
- The current state of the roadmap, phases, and epics
- What ADRs exist and what decisions they capture
- The current requirements and success criteria
- How the existing planning docs relate to each other

**Workflow-fit check — do this BEFORE proceeding past Stage 1.** Assess whether this task actually belongs on plan-revision. If the task is predominantly a bulk rename, find-and-replace, or mechanical refactor across many files (not a genuine plan/architecture/requirements revision), STOP and report:

> This task looks like a bulk rename/refactor rather than a plan revision. plan-revision.sh is sized for review-based planning changes and would burn through the turn budget on per-occurrence Edits. Recommend dispatching via revision.sh or revision-major.sh with `sed -i` or `Edit(replace_all: true)` instead.

Exit without proceeding to Stage 2. Red flags that indicate miscategorization: the task is "rename X to Y everywhere," "update all references from A to B," "replace every occurrence of Z," or anything requiring dozens of identical edits across many files.

If the task is a legitimate planning revision, summarize the current state before proceeding. Focus on the areas relevant to the requested changes.

## Stage 2: PLAN
Determine what specifically needs to change:
- Which planning docs need updates (roadmap, phase docs, requirements, ADRs, epics)
- What content needs to be added, modified, or removed
- What new docs need to be created (e.g., new ADRs)
- Dependencies between changes (e.g., roadmap update depends on phase doc update)
- Risks: could these changes create inconsistencies with other planning docs?

Keep the plan specific and actionable. List the files and the changes for each.

## Stage 3: REVISE
Make the planning changes. Work through the plan methodically:
- Update requirements, phases, epics, ADRs, and roadmap as needed
- Ensure cross-references between docs remain consistent
- Follow the four-bucket documentation convention (architecture=WHY, development=WHAT, standards=HOW, guide=USER-FACING)
- Use clear, specific language — avoid vague phrases like "improve performance"
- Planning docs should focus on WHAT and WHY, not HOW. Defer implementation-level detail (full config YAML, exact CLI commands, step-by-step terminal procedures) to the engineer's task file. If you find yourself writing the commands someone would paste into a terminal, you have crossed into implementation — move it to a task-file appendix or reference it as "see implementation task."

Checkpoint commit: once the planning changes are complete, stage all changes and make a local checkpoint commit (do NOT push):
  git add -A && git commit -m "wip: planning-doc checkpoint — PRE-REVIEW, not yet audited"

This protects the work if later review stages fail or the turn budget is exhausted. Stage 6 SUBMIT will add any review-fix commits and push everything together. If there are no changes to commit, skip and note why in the summary.

Produce a brief summary noting:
- What was changed and why
- Any deviations from the plan and why they were necessary
- Files modified or created

## Stage 4: PEER REVIEW (parallel)

Dispatch THREE peer-review agents IN PARALLEL. Send a SINGLE assistant message containing three Agent tool calls — one each for architect, planner, and standards-architect. The three agents review the SAME Stage 3 artifact independently; there is no ordering dependency between them, so serial dispatch wastes turns and doubles the wall-clock time of this stage.

**How to dispatch in parallel:** in one assistant turn, emit three tool_use blocks, one per agent. Do NOT call them one at a time across separate turns. The Claude tool-use API supports multiple tool calls per assistant message.

Each agent's review focus:

### architect agent — technical consistency and trade-offs
- Are the technical decisions consistent with existing architecture?
- Are trade-offs clearly documented?
- Are there architectural implications that haven't been considered?
- Do ADRs properly capture context, decision, and consequences?

### planner agent — actionability, dependencies, ordering
- Are requirements actionable and implementable?
- Are dependencies between phases/epics correctly identified?
- Is the ordering of work logical and efficient?
- Do success criteria have measurable, verifiable definitions?
- Are estimates and timelines realistic given scope?

### standards-architect agent — standards corpus interactions
- **Cross-reference integrity:** do references to `docs/standards/*.md` from the revised planning docs resolve? Is the content accurate? When a doc references a specific sub-section (e.g., "§6b", "Section 3.2", "the Deployment Standard networking section"), verify that sub-section actually exists — not just the parent document.
- **Gap analysis:** does this revision propose new work (phases, features, components) that will need new standards? Flag gaps — do not create draft standards in this stage.
- **Documentation-structure conformance:** does the revised doc follow the four-bucket convention (architecture=WHY, development=WHAT, standards=HOW, guide=USER-FACING) and the documentation-structure skill?
- **Drift risk:** does the revision introduce duplication between planning docs and standards docs (same rule stated in 2+ places)?
- **Direct standards changes:** if the revision modifies `docs/standards/*.md` directly, is the change internally consistent and aligned with exemplar files in the code?

### Consolidating findings

After all three agents return, analyze combined findings by severity:
- Critical: inconsistencies, unactionable requirements, broken standards references, contradictions — must fix
- Warning: unclear implications, vague criteria, drift risk, missing cross-links, gap identification — should fix if scope allows
- Info: suggestions, documentation-structure observations, cross-linking opportunities

Fix any Critical issues found across ANY of the three reviews. Per the finding-disposition rule, every finding must reach fixed / rejected-with-reasoning / documented-deferral — never silent pass-through. Note which agent raised each finding when documenting.

If one agent has no findings (e.g., a pure roadmap date bump triggers no standards implications), note "standards-architect: no findings" inline. Do NOT emit a SKIPPED marker for the stage as a whole — the stage still ran, two of the three agents likely had findings.

## Stage 5: RESOLVE
Review all changes made across stages 3-4. Produce a consolidated summary:
- Original task vs what was actually done
- Architect review findings: addressed vs deferred
- Planner review findings: addressed vs deferred
- Standards review findings: addressed vs deferred
- Any remaining concerns or known gaps
STAGES_EOF
)

DECISION_LOG_AND_REFLECTION=$(cat <<'DLR_EOF'
After pushing (and creating the PR if on the new-branch path), post a PR comment containing a Decision Log and Post-Run Reflection. Write the comment body to a temp file first (e.g., `/tmp/pr-comment-<timestamp>.md`), then post via `gh pr comment <PR-number> --body-file <temp-file>`. Do NOT inline the content into the command — multi-line content in a single arg is fragile.

The comment must contain these two sections:

## Decision Log

List NON-OBVIOUS decisions made during this run. One bullet per decision, format:
`**[High/Medium/Low]** <what was decided>. Alternatives: <what else was considered>. Why: <brief rationale>.`

Include only decisions where a reasonable engineer could have chosen differently: architecture choices, trade-off calls, scope boundary decisions, severity calls on reviewer findings, rejected reviewer suggestions.

Exclude: obvious implementation details, standards conformance, pattern application, mechanical changes that had no real alternative.

If no non-obvious decisions were made, state: "No significant decisions — task was mechanical."

Order: Low-confidence decisions FIRST (human prioritizes reviewing those).

## Post-Run Reflection

Omit any section below that has nothing to report — silence means no issues. Be specific when noting friction ("task file ambiguous on X" is useful; "it was fine" is not).

- **Friction:** ambiguity in the task, missing context, tool gotchas encountered, points where guidance was thin
- **Project-level suggestions (this repo):** standards gaps, documentation improvements, conventions that should be documented
- **Tooling-level suggestions (claude-dot-files):** workflow prompt improvements, skill gaps, rule refinements that would benefit future runs

If all three sections are empty, state: "No friction or suggestions from this run."
DLR_EOF
)

RULES=$(cat <<'RULES_EOF'
Rules:
- Follow each stage in order — do not skip stages
- This is a PLANNING revision — do not modify code, scripts, or configuration files
- Only modify files in docs/ (and the root CLAUDE.md if it references planning state)
- **File-reading discipline:** after the first full Read of a file, subsequent Reads MUST use `offset`+`limit` or use Grep to target a specific region. Do NOT re-read the entire file. Unbounded re-reads of already-read files are the single largest source of wasted tokens observed in production (one run hit 17× full reads of the same 1500-line file = ~45k redundant tokens). Narrow Reads after Edits are legitimate verification.
- **Large-file reading:** before the FIRST Read of any markdown file, run `wc -l` on it. If >500 lines, use `limit:200` on the first Read to avoid the 25K-token Read ceiling. Common culprits: roadmap.md, sprint/phase docs, loose_ends files, standards docs, .jsonl logs. When in doubt, check size first.
- **Re-Read before Edit if the file may have changed:** if any tool could have rewritten the file since your last Read (formatter, linter, codemod, git checkout, autoformatter-on-save), re-Read the file before Editing. The `File has been modified since read` error is the signal you missed this.
- **Parallel tool calls in the gather phase:** when gathering context (Read/Grep/Glob), batch 3+ independent tool calls into a single assistant turn. Sequential gather wastes turns. Parallel gather is a pure efficiency win — higher-parallelism runs are not more error-prone.
- **Tool parameter naming gotchas** (these cause recurring InputValidationErrors):
  - Grep on a single file uses `path`, NOT `file_path`. Read/Edit/Write use `file_path`.
  - Read does NOT take a `command` parameter — that's Bash.
  - Glob does NOT take `head_limit` — that's a Grep option.
  - TodoWrite takes an ARRAY for `todos`, not a string.
- Fix Critical review findings before submitting
- Document deviations from the plan
- Maintain consistency across all planning docs — if you update a phase doc, check that the roadmap still aligns
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

    PROMPT="You are executing the PLAN-REVISION workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

This is a PLANNING doc revision workflow — not a code change workflow. Follow all 6 stages thoroughly.

Task: ${DESCRIPTION}
${CONTEXT_BLOCK}
${STAGES_1_TO_5}

## Stage 6: SUBMIT
- Stage any uncommitted changes remaining from stages 4-5 (peer-review fixes from architect, planner, and standards-architect) and commit them with the final message format: \"docs: <short description of planning changes>\". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch (this updates PR #${PR_NUMBER})
- Update the PR body with a concise summary. The planning doc IS the deliverable — the PR body is a scannable index, not a restatement. Keep it under 100 lines:
  - Planning changes made (bullet list)
  - Architect review: critical findings addressed (one line each) + count of deferred warnings/info
  - Planner review: same format
  - Standards review: same format
  - Cross-reference consistency: pass/fail + any issues found
  Do NOT repeat reviewer findings verbatim — summarize the finding and the resolution in one line each.

${DECISION_LOG_AND_REFLECTION}

${RULES}"

    echo
    echo "→ Launching Claude in plan-revision mode (updating PR #${PR_NUMBER})..."
    echo

    (
        cd "$WORKTREE_PATH"
        run_claude "$PROMPT"
    )

else
    # ---- New branch path --------------------------------------------------
    PROMPT="You are executing the PLAN-REVISION workflow on a new branch.

This is a PLANNING doc revision workflow — not a code change workflow. Follow all 6 stages thoroughly.

Task: ${DESCRIPTION}
${CONTEXT_BLOCK}
${STAGES_1_TO_5}

## Stage 6: SUBMIT
- Stage any uncommitted changes remaining from stages 4-5 (peer-review fixes from architect, planner, and standards-architect) and commit them with the final message format: \"docs: <short description of planning changes>\". If everything was already captured by the Stage 3 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch
- Create a new PR using 'gh pr create'. Title format: \"plan-revision: <short description>\". The planning doc IS the deliverable — the PR body is a scannable index, not a restatement. Keep it under 100 lines:
  - Planning changes made (bullet list)
  - Deviations from plan (if any, one line each)
  - Architect review: critical findings addressed (one line each) + count of deferred warnings/info
  - Planner review: same format
  - Standards review: same format
  - Cross-reference consistency: pass/fail + any issues found
  Do NOT repeat reviewer findings verbatim — summarize the finding and the resolution in one line each.

${DECISION_LOG_AND_REFLECTION}
- Report the PR URL

${RULES}"

    echo "→ Launching Claude in plan-revision mode (new branch)..."
    echo

    run_claude "$PROMPT" -w "$WORKTREE_NAME"
fi

echo
echo "================================================================"
echo "  PLAN-REVISION WORKFLOW COMPLETE"
echo "================================================================"
echo
echo "Worktree: .claude/worktrees/${WORKTREE_NAME}"
echo "Log file: ${LOG_FILE}"
echo
echo "To let Claude diagnose this run:"
echo "  claude 'read ${LOG_FILE} and tell me what happened'"
echo
echo "To clean up when done:"
echo "  /cleanup-merged-worktrees    (after PR is merged or closed)"
echo
