#!/usr/bin/env bash
#
# plan-new.sh — the PLAN-NEW workflow
# Research and planning workflow for defining new projects from scratch.
#
# This is the heaviest autonomous workflow. Unlike build workflows that fix
# existing code or build-phase that implements from a plan, this workflow
# CREATES the plan. It takes a project name and optional context, then walks
# through the full project definition process: requirements gathering, tech
# stack selection, architecture design, phase breakdown, and documentation
# setup — producing a comprehensive project foundation.
#
# The project-definition skill (config/skills/project-definition.md) contains
# the full methodology. This script orchestrates Claude through it.
#
# Stages:
#   1. REQUIREMENTS — gather functional, non-functional, constraints
#   2. STAKEHOLDERS — identify who cares, define success criteria
#   3. TECH STACK — select and document as standards docs
#   4. ARCHITECTURE — high-level system overview
#   5. PHASES — break into independently deliverable phases
#   6. EPICS — identify major features per phase
#   7. DEPENDENCIES — map internal and external
#   8. SECURITY — initial security review
#   9. ROADMAP — assemble into /opt/skyy-net/skyynet-master-planning/development/sprints.md
#  10. DOCUMENTATION — set up four-bucket docs layout, CLAUDE.md, file_structure.txt
#  11. ARCHITECT REVIEW — review tech stack, architecture, system overview for consistency
#  12. PLANNER REVIEW — review phases, epics, dependencies for actionability and completeness
#  13. SECURITY REVIEW — security-auditor reviews security doc for completeness and gaps
#  14. RESOLVE — address critical findings from all three reviews
#  15. SUBMIT — commit, push, PR with comprehensive summary
#
# Usage:
#   ./plan-new.sh "project name"
#   ./plan-new.sh "project name" "additional context here"
#   ./plan-new.sh "project name" "additional context here" --verbose
#   ./plan-new.sh "project name" --pr <pr-number>
#
# Examples:
#   ./plan-new.sh "skyycommand"
#   ./plan-new.sh "skyycommand" "AI-driven VM placement engine for Proxmox clusters"
#   ./plan-new.sh "webhook-gateway" "lightweight service for routing GitHub webhooks" --verbose
#   ./plan-new.sh "skyycommand" "focus on the inference pipeline first" --pr 15
#
# Flags:
#   --pr <number>   Update an existing PR instead of creating a new one
#   --verbose, -v   Stream formatted Claude output live
#
# Logging:
#   Every run writes a structured JSONL log to .claude/logs/plan-new-<ts>.jsonl
#
# See /opt/skyy-net/skyynet-master-planning/guide/workflows.md for the full
# architectural context behind this workflow.
# See /opt/skyy-net/skyynet-master-planning/standards/workflow-scripts.md for the standard this script follows.

set -euo pipefail

# ---------------------------------------------------------------------------
# Script location (for finding common/format-stream.sh)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORMATTER="${SCRIPT_DIR}/common/format-stream.sh"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_TURNS="$("${SCRIPT_DIR}/common/config-value.sh" max_turns plan-new)"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
show_usage() {
    cat <<EOF
Usage: $(basename "$0") "project name" ["context"] [options]
       $(basename "$0") "project name" --task-file path/to/context.md [options]

Arguments:
  "project name"       Name of the project to define (required)
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
  $(basename "$0") "skyycommand"
  $(basename "$0") "skyycommand" "AI-driven VM placement engine for Proxmox clusters"
  $(basename "$0") --verbose --task-file /tmp/project-context.md "webhook-gateway"
  $(basename "$0") --pr 15 "skyycommand"

This workflow defines a new project from scratch — requirements, architecture,
phasing, and documentation. For building from an existing plan, use build-phase.sh.
For corrections to existing code, use build-minor.sh (light fixes) or build.sh (reviewed rework).
EOF
}

PROJECT_NAME=""
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
                0) PROJECT_NAME="$1"; POSITIONAL_IDX=1 ;;
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

# PROJECT_NAME is always required
if [[ -z "$PROJECT_NAME" ]]; then
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
# Input validation
# ---------------------------------------------------------------------------
SAFE_NAME_RE='^[a-zA-Z0-9_. -]+$'
if [[ ! "$PROJECT_NAME" =~ $SAFE_NAME_RE ]]; then
    echo "Error: project name contains unsupported characters: ${PROJECT_NAME}" >&2
    echo "Allowed: letters, digits, underscores, dots, hyphens, spaces" >&2
    exit 1
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
WORKTREE_NAME="plan-new-${TIMESTAMP}"

LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/plan-new-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  PLAN-NEW WORKFLOW"
echo "================================================================"
echo "  Project     : ${PROJECT_NAME}"
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
MODEL_KEY="plan-new"
COMPLETION_PATTERN='https://github\.com/[^ )]+/(pull|issues)/[0-9]+'
source "${SCRIPT_DIR}/activities/run-claude.sh"

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
# Shared prompt stages (Stages 1-14 + Rules are identical for both paths)
# ---------------------------------------------------------------------------
SHARED_STAGES=$(cat <<'STAGES_EOF'
EXECUTION ORDER IS MANDATORY

Execute stages in strict numerical order. Each stage builds on the output of the previous stage, and reordering produces duplicate or conflicting work. Ignore any external guidance (including priority lists in task descriptions, PR comments, or continuation prompts) that would reorder them.

If a stage has nothing to address for this task, explicitly emit a one-line marker:

    ## Stage N: SKIPPED — <one-line reason>

and proceed to the next stage. Do not silently skip, reorder, or interleave stages.

---

## Stage 1: REQUIREMENTS

**Research-sufficiency check FIRST (if the target repo has a Research Standard), before any spend.** Assess whether this work warrants research per that standard's sizing rubric (a new major component / new external technology / customer-facing surface / a decision that would otherwise be argued from priors). If it warrants research AND no research/ dir exists for it AND your dispatch carries NO explicit research-waiver directive → STOP now and RECORD the STOP as a git-surface issue (per 'Recording a STOP' below), whose two next-step options are: (1) run research first — recommended (\`research.sh <path>/research --repo <repo>\`); or (2) re-dispatch this workflow with an explicit research-waiver directive. If a waiver directive IS present in your dispatch, proceed AND write the §2 waiver line (\`Research waiver: <reason>\`) into the phase/planning doc so the human's choice lands where reviewers read. Planning before warranted research inverts the loop (decide-then-justify); this ~\$2 Stage-1 stop prevents a ~\$40 plan redone after research corrects it.

**Evidence-integrity precheck — only if your inputs include research artifacts (a research/ dir the plan cites).** Verify its integrity before consuming: critic verdicts present, papers inside their revalidation window (not past-window treated as authority), load-bearing claims non-contradictory. Structurally faulty evidence → STOP, do NO planning on it, and RECORD the STOP as a git-surface issue (per 'Recording a STOP' below), stop_class \`evidence-faulty\`.

**Recording a STOP (both checks above).** A STOP must land on a git surface, not just terminal output — a fail-fast that records itself only to a dispatch log is invisible to future humans AND to the eventual parent workflow (the grave-memory anti-pattern). So on ANY STOP above, open a GitHub ISSUE in the target repo, print its URL as your final line, and do NO planning after filing — the issue IS the deliverable of a STOP:
- Ensure the label exists, then file: \`gh label create <label> --color FBCA04 --description 'plan STOP' 2>/dev/null || true\`, then \`gh issue create --title '<title>' --label <label> --body-file <tmpfile>\`.
- **Title:** \`plan-new STOPPED: research required for <component> (§2)\` (sufficiency) or \`evidence-integrity failure: <paper>\` (integrity). **Label:** \`research-required\` (sufficiency) or \`evidence-faulty\` (integrity).
- **Body:** the finding; then BOTH next-step options as ready-to-fire dispatch contexts (option 1: the exact \`research.sh\` command; option 2: re-dispatch this workflow with the research-waiver directive); then a machine-readable yaml block (same schema family as \`pr_review:\`):
\`\`\`yaml
plan_stop:
  repo: <owner/repo>
  component: <component / research dir>
  stop_class: research-required | evidence-faulty
  finding: <one line>
  next_steps:
    - option: research-first
      dispatch: <the exact research.sh command>
    - option: waiver
      dispatch: <re-dispatch this workflow with the research-waiver directive>
  resolves_when: <the research PR that \"Closes #N\", or the waiver re-dispatch that cites #N>
\`\`\`
- The resolving artifact closes it (research PR body says \`Closes #N\`; a waiver re-dispatch cites #N). gh-monitor safety: NO line in the issue body may START with \`@claude\` — put any dispatch-command illustration inside a code fence.
- Then print the issue URL as your FINAL line — it is the STOP's completion signal (exit-0-means-done holds for stop-outcomes too).

Gather and document the project requirements. The project-definition skill has the full methodology.

Create `docs/development/requirements.md` covering:
- **Functional requirements:** User stories, features, scenarios, acceptance criteria
- **Non-functional requirements:** Performance, scalability, availability, security, maintainability, observability
- **Constraints:** Budget, timeline, tech stack, team, existing systems, regulatory
- **Assumptions:** Make them explicit — each assumption is a risk
- **Out of scope:** What this project is NOT building

Be specific. "Users can authenticate" is vague. "Users can sign up with email + password, log in, reset passwords, and stay logged in across sessions" is specific.

## Stage 2: STAKEHOLDERS
Identify stakeholders and define success criteria.

Add to the requirements doc or create a dedicated section:
- **Users:** Who uses it?
- **Owners:** Who pays for it, who decides?
- **Operators:** Who keeps it running?
- **Developers:** Who builds and maintains it?
- **Integrators:** Who connects from other systems?

Define measurable success criteria:
- Observable, specific, tied to requirements, time-bounded
- Include anti-success criteria (early warning signs of going off track)

## Stage 3: TECH STACK
Select the technology stack. Each major decision gets a standards doc at `docs/standards/<topic>.md`. **This repo does NOT use numbered ADRs** — a standard states the rule in the present tense and is amended in place.

Evaluate and document decisions for:
- Language(s), runtime, framework
- Database, cache, queue (if needed)
- Deployment target, infrastructure-as-code
- CI/CD, monitoring, testing frameworks
- Authentication approach

For each decision, write a standards doc following the project's standards format. Create a summary in `docs/standards/architecture/tech-stack.md`.

Guiding principles: boring is beautiful, team expertise matters, operational simplicity wins, start simple.

## Stage 4: ARCHITECTURE
Design the high-level architecture.

Create `/opt/skyy-net/skyynet-master-planning/standards/architecture/architecture_standard.md` with:
- **Component diagram:** Major pieces and how they connect
- **Data flow:** Request lifecycle, write path, read path, background processing
- **External integrations:** Third-party APIs, webhooks, identity providers
- **Key design patterns:** Architecture style, communication patterns

## Stage 5: PHASES
Break the project into independently deliverable phases.

Follow the phasing principles:
- **Phase 0: Foundation** — repo setup, CI/CD, dev environment, observability, standards
- **Phase 1: Walking skeleton** — simplest end-to-end version proving the architecture
- **Phase 2-N: Feature phases** — vertical slices, each independently useful
- **Final phase: Hardening** — performance, security, documentation polish

Create phase docs with goals, prerequisites, scope, success criteria, and major tasks.
Detail Phase 0 and Phase 1 fully. Later phases can be lighter.

## Stage 6: EPICS
Identify major epics (feature groupings) within each phase.

An epic is larger than a task, smaller than a phase — a user-facing or technical capability that spans multiple files and commits, with its own success criteria.

Create epic docs in `docs/development/features/<feature-name>/overview.md` for significant epics. Phase docs should reference these.

## Stage 7: DEPENDENCIES
Map dependencies between phases, epics, and external systems.

- **Internal:** Phase ordering, data model dependencies, feature prerequisites
- **External:** Third-party API credentials, infrastructure provisioning, design assets

Document explicitly — a dependency list prevents working in the wrong order.

## Stage 8: SECURITY
Conduct an initial security review of the project foundation.

Address:
- What data is sensitive? (PII, payment, credentials, proprietary)
- What's the auth model?
- Known attack vectors for the chosen stack?
- Applicable compliance (GDPR, HIPAA, SOC2, PCI-DSS)?
- Secrets management strategy?
- Backup/recovery strategy?
- Abuse scenarios?

Create `docs/standards/architecture/security.md` capturing foundational security decisions.

## Stage 9: ROADMAP
Assemble everything into the top-level roadmap.

Create `/opt/skyy-net/skyynet-master-planning/development/sprints.md` with:
- Overview (1-2 paragraph summary of what and why)
- Top-level success criteria from Stage 2
- Phase listing with status, descriptions, and links to phase docs
- Current status and blockers
- Related documentation links

## Stage 10: DOCUMENTATION
Set up the full project documentation scaffolding.

Set up the four-bucket documentation layout:
```
docs/
├── architecture/     (THE WHY: architecture standards, system design, security)
├── development/      (THE WHAT: roadmap, requirements, phases, features)
├── standards/        (THE HOW: conventions and patterns)
├── guide/            (OPERATING MANUAL: user-facing docs)
└── file_structure.txt
```

Create:
- README files in empty directories explaining what will go there
- Initial standards docs (code-style.md, git-workflow.md, testing.md)
- `docs/file_structure.txt` — annotated map of the repo
- Project root `CLAUDE.md` with project name, tech stack reference, how to run/build/test, standards references, and project-specific rules
- `README.md` — repo description for humans

**.gitignore-collision check (before checkpoint commit):** plan-new typically creates many new files and directories. Run `git status` and confirm each appears as untracked. If a created path does NOT appear, `.gitignore` is silently hiding it — typically via unanchored, name-only patterns (`ssh/`, `helpers/`, etc.) intended for credential or temp directories. Grep `.gitignore` for the matching pattern, then add an explicit `!path/` allowlist override before checkpoint commit. Silently-ignored new files are work invisible to the PR (silent data loss class).

Checkpoint commit: once all project-definition and documentation scaffolding through Stage 10 is complete, stage all changes and make a local checkpoint commit (do NOT push):
  git add -A && git commit -m "wip: project-definition checkpoint — PRE-REVIEW, not yet audited"

This protects the work if later review stages or resolution fail or the turn budget is exhausted. Stage 15 SUBMIT will add any review-fix commits and push everything together. If there are no changes to commit, skip and note why in the summary.

## Stage 11: ARCHITECT REVIEW
Use the architect agent to review the work produced in Stages 3-4 for internal consistency.

The architect should evaluate:
- **Tech stack coherence:** Do the selected technologies work well together? Are there conflicts or redundancies?
- **Architecture alignment:** Does the system overview align with the tech stack decisions and standards?
- **Component boundaries:** Are responsibilities clearly separated? Are there missing or overlapping components?
- **Scalability and operational concerns:** Are there obvious bottlenecks or operational gaps in the design?
- **Standards consistency:** Do the standards reference each other correctly? Are trade-offs internally consistent?

Review the architect's findings. Critical concerns must be noted for Stage 13.

## Stage 12: PLANNER REVIEW
Use the planner agent to review the work produced in Stages 5-7 for actionability and completeness.

The planner should evaluate:
- **Phase ordering:** Are phases in the right sequence? Are prerequisites satisfied before dependent phases?
- **Epic completeness:** Do epics cover the requirements? Are there gaps or orphaned requirements?
- **Dependency accuracy:** Are all internal and external dependencies captured? Are there circular dependencies?
- **Success criteria quality:** Are success criteria measurable and specific, not vague? Can you objectively tell when each phase is done?
- **Task granularity:** Are phases broken down enough to be actionable? Are any phases too large or too vague?

Review the planner's findings. Critical concerns must be noted for Stage 14.

## Stage 13: SECURITY REVIEW
Use the security-auditor agent to review the security documentation from Stage 8.

The security auditor should evaluate:
- **Secrets inventory completeness:** Is every secret identified? Does each have storage, injection per environment, access controls, and rotation strategy documented?
- **Attack surface coverage:** Are the relevant attack vectors identified? Are mitigations concrete and actionable?
- **Auth model soundness:** Is the authentication approach well-defined? Are there privilege escalation risks?
- **Compliance gaps:** Are applicable compliance requirements identified and addressed?
- **Abuse scenarios:** Are realistic abuse scenarios considered with mitigations?
- **Missing concerns:** Are there security implications of the tech stack or architecture that Stage 8 missed?

Review the security auditor's findings. Critical concerns must be noted for Stage 14.

## Stage 13b: HOLISTIC REVIEW (quality-control, sequential)

After the architect, planner, and security-auditor reviews (Stages 11, 12, 13) all complete, dispatch the `quality-control` agent SEQUENTIALLY. Send a single assistant message with ONE Agent call for quality-control.

The quality-control prompt MUST include:
- The planning artifacts being reviewed (tech stack, architecture, phases, epics, security doc, roadmap — Stages 3-9 outputs)
- The structured findings from Stages 11, 12, 13 (architect + planner + security-auditor outputs, verbatim or paraphrased clearly)
- Instruction to apply the holistic six-dimension lens to the PLAN AS A WHOLE AND look for meta-patterns across the three reviewers' findings ("do these findings together suggest the plan is compromised, under-specified, or not enterprise-grade?")

quality-control applies the senior-engineer integration test to the new project's planning: would a peer reviewer at a top-tier engineering organization sign off on this project foundation? Planning-stage focus areas:
- Is the planned approach industry-best-practice grounded across tech stack, architecture, and phase decomposition?
- Will the planned solution be enterprise-ready, or will it produce "good enough" results?
- Are there compromises baked INTO the plan (e.g., "we'll skip X for now", "we'll figure out Y later") without justification?
- Does the plan explain WHY decisions were made, or just WHAT will be done?

See `quality-control-methodology` skill for the full six-dimension lens (best-practices grounding, enterprise-readiness, compromise detection, maintainability, robustness, decision rigor), severity calibration, and planning-review application context.

quality-control runs SEQUENTIALLY (after Stages 11/12/13) because its lens benefits from seeing those narrow-lens findings to detect meta-patterns. Critical concerns from quality-control must be noted for Stage 14.

## Stage 14: RESOLVE
Address findings from the architect review (Stage 11), planner review (Stage 12), security review (Stage 13), and holistic quality-control review (Stage 13b).

For each finding:
- **Critical findings:** Must be addressed now. Update the relevant documents to fix the issue.
- **Warnings:** Should be addressed if the fix is straightforward. Otherwise, document as a known limitation.
- **Info items:** Note for future improvement but do not act on them now.

Produce a resolution summary in `docs/standards/architecture/review-resolutions.md`:
- What was found (brief list of findings from each review stage)
- What was addressed and how
- What was deferred and why
STAGES_EOF
)

# DECISION_LOG_AND_REFLECTION is defined in common/shared-prompts.sh
source "${SCRIPT_DIR}/common/shared-prompts.sh"

RULES=$(cat <<'RULES_EOF'
Rules:
- Follow each stage in order — do not skip stages
- Be thorough — this is a full project definition, not a quick sketch
- **Worktree CWD discipline:** the workflow starts you in a git worktree at a specific absolute path. NEVER `cd` to the main repo's checkout — operations there land outside the worktree's branch and are invisible to the PR (silently lost work). When running sed/find/xargs across many files, pass the worktree's absolute path explicitly. If you need a Bash command in a different directory, use `(cd <worktree-abs-path> && command)` in a subshell rather than a top-level `cd`.
- **Read-before-Edit (HARD requirement):** before any Edit or Write to an existing file, the most recent Read of that file MUST be in this turn or the immediately previous turn. If the gap is wider — or any tool ran between (formatter, linter, codemod, git checkout, autoformatter-on-save, subagent boundary) — re-Read the file before Editing. The `File has not been read yet` and `File has been modified since read` errors are the signals you missed this. Recurring pattern across multiple production review cycles — this is hard discipline, not soft guidance.
- **Bash CWD persists between calls — never blind-chain a relative `cd`:** the working directory usually carries over from your previous Bash call (some configurations reset it — treat it as unpredictable). A chained relative `cd <subdir> && ...` fails whenever the CWD is already that subdir. When you need to cd, use the absolute worktree-rooted path (`cd <worktree>/lib/temporal && pytest tests/unit/`) — idempotent regardless of current CWD — or skip cd and use absolute paths in the command itself.
- **Re-Read before re-Editing anything you wrote earlier:** Edit requires a fresh Read. The classic failures: revising a /tmp staging file (e.g. `/tmp/claude-pr-body.md`) several turns after Writing it, or re-Editing a repo file many turns after its last Read (applying review findings). Either Read the file again first, or for staging files simply Write the full replacement content instead of Editing.
- **Prefer relative paths inside the worktree:** the workflow places you at the worktree root. For Read/Grep/Glob/Edit/Write of files inside the worktree, use paths relative to the root rather than re-typing the long absolute worktree path. The model occasionally typos long absolute paths (e.g., `.claire/` instead of `.claude/`) — relative paths eliminate that bug class entirely.
- The project-definition skill (config/skills/project-definition.md) has the full methodology — reference it for detailed guidance on each stage
- Do not re-read files whose content you already know and haven't modified since you last read them
- For known-large files (sprint.md, standards docs, .jsonl logs), use limit:200 on first read or run wc -l to check size first — unbounded reads on large files cause errors
- Scale the process to the project size (see the skill's "Scaling the Process" section)
- Every major tech stack decision needs a standards doc
- Success criteria must be measurable, not vague
- Phase 0 and Phase 1 must be fully detailed; later phases can be lighter
- If you cannot complete a stage, stop and clearly report why
- Stay focused on project definition — do not start implementing features
- Each document must have a single focused purpose — do not duplicate content across documents. If two docs need the same information, one is the source of truth and the other references it. Redundancy causes drift.
- If the project directory already has scaffolding (from init-project.sh or similar), respect and build on it — do not overwrite existing .gitignore, CLAUDE.md, README.md, or folder structure unless they conflict with the plan
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

    PROMPT="You are executing the PLAN-NEW workflow on PR #${PR_NUMBER} (branch: ${PR_BRANCH}).

This workflow defines a new project from scratch. Follow all 15 stages thoroughly.

Project name: ${PROJECT_NAME}
${CONTEXT_BLOCK}
${HEADLESS_EXECUTION_GUARD}

${SHARED_STAGES}

## Stage 15: SUBMIT
- Stage any uncommitted changes remaining from stages 11-14 (review fixes, resolutions) and commit them with the final message format: \"feat: define ${PROJECT_NAME} project foundation\". If everything was already captured by the Stage 10 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch (this updates PR #${PR_NUMBER})
- **As your FINAL line, print the PR URL** — run \`gh pr view ${PR_NUMBER} --json url --jq .url\` and print the result. This is the run's completion signal. On this path you UPDATE an existing PR rather than creating one, so nothing else emits the URL; a run that ends without it is misread as an early-stop failure even though the work succeeded.
- Report a summary of the entire workflow including:
  - Deliverables created (documents, standards, configs)
  - Key decisions made and their rationale
  - Any stages that were scaled down and why

${DECISION_LOG_AND_REFLECTION}

${RULES}"

    echo
    echo "→ Launching Claude in plan-new mode (updating PR #${PR_NUMBER})..."
    echo

    (
        cd "$WORKTREE_PATH"
        run_claude "$PROMPT"
    )

else
    # ---- New branch path --------------------------------------------------
    PROMPT="You are executing the PLAN-NEW workflow on a new branch.

This workflow defines a new project from scratch. Follow all 15 stages thoroughly.

Project name: ${PROJECT_NAME}
${CONTEXT_BLOCK}
${HEADLESS_EXECUTION_GUARD}

${SHARED_STAGES}

## Stage 15: SUBMIT
- Stage any uncommitted changes remaining from stages 11-14 (review fixes, resolutions) and commit them with the final message format: \"feat: define ${PROJECT_NAME} project foundation\". If everything was already captured by the Stage 10 checkpoint and no review fixes were needed, skip this commit — the checkpoint is enough and the PR body carries the real summary.
- Push the branch
- Create a new PR using 'gh pr create'. Title format: \"plan-new: ${PROJECT_NAME} foundation\". In the body, include:
  - Summary of all deliverables created
  - Key decisions made (tech stack, architecture, phasing)
  - Standards written and their conclusions
  - Phase breakdown overview
  - Success criteria defined
  - Documentation structure set up
  - Any stages that were scaled down and why
- Report the PR URL

${DECISION_LOG_AND_REFLECTION}

${RULES}"

    echo "→ Launching Claude in plan-new mode (new branch)..."
    echo

    run_claude "$PROMPT" -w "$WORKTREE_NAME"
fi

echo
echo "================================================================"
echo "  PLAN-NEW WORKFLOW COMPLETE"
echo "================================================================"
echo
echo "Worktree: .claude/worktrees/${WORKTREE_NAME}"
echo "Log file: ${LOG_FILE}"
print_cycle_totals "$LOG_DIR"
echo
echo "To read the log in human-readable form:"
echo "  cat ${LOG_FILE} | ${FORMATTER}"
echo
echo "To let Claude diagnose this run:"
echo "  claude 'read ${LOG_FILE} and tell me what happened'"
echo
echo "To clean up when done:"
echo "  /cleanup-merged-worktrees    (after PR is merged or closed)"
echo
