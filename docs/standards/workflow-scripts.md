# Workflow Script Standards

Conventions for writing autonomous workflow scripts in `scripts/workflows/`.

## Purpose

Workflow scripts implement the autonomous side of the Dual Workflow Model (see `docs/guide/workflows.md`). They wrap `claude -p` invocations with structured stages, safety guards, visibility, and logging. These are the scripts you run to hand off work to Claude and come back to a PR.

## File Conventions

### Location (BINDING)

**The target layout is Skyy-Command's `lib/temporal/`, and this repo's current layout is a waypoint toward it.** Diverging here means two near-identical architectures with different shapes, and a painful reconciliation if this ever becomes a module inside that system. Where we already match, match exactly; where we do not, know why and know when it resolves.

#### Target layout (Temporal Standard §10)

```
activities/            generic executors, DOMAIN-organized (git/, runtime/, config/, ssh/, …)
common/                shared LIBRARY CODE — logging, audit, delegation, types. NOT workflows.
modules/               workflows, organized {module}/{purpose}/{name}/
  common/                workflows owned by no module
  {module}/              ONE PER EDGE — assistant/, home_automation/, robotics/, …
    {purpose}/             a slice of work — build/, research/, provision/
      {name}/                ONE workflow, and everything it needs
        {name}_workflow.py     orchestration (Layer 1)
        {name}_helper.py       pure compiler (Layer 2)
        {name}_activities.py   semantic wrappers (Layer 3a)
        {name}_inputs.py       typed input models
        *.md                   prompts and resources, CO-LOCATED
tests/                 tests for the workflows
scripts/               kickoff entrypoints, until an SDK path replaces them
```

**One workflow per folder (BINDING).** Verified against the live tree: `modules/common/provision/agent_join/` and `modules/common/ingest_github_token/` each hold a single workflow's trio plus its inputs. Older workflows in that same repo sit flat in the purpose folder — `genesis_*`, `cluster_provision_*` and `baseline_tailnet_push_*` side by side — and `temporal_standard.md` §3.2 still describes *that* as the rule, explicitly rejecting "a nested folder named after each workflow file." **RULED UPSTREAM 2026-08-05 (`temporal_standard.md` §10.1, vendored at `6fe3829`).** Folder-per-workflow is binding: *"Every workflow lives in a folder named for it, and every file in that folder carries the `{name}_` prefix. A workflow file at a purpose- or module-root is non-conformant."* The question this section previously raised is closed; §10.1 is the authority and the paragraphs below restate only what binds us.

Four §10.1 rules bear directly on how we lay work out:

- **The promotion rule (rule 3) is the ONLY test for what sits at a parent level.** A helper, activities or inputs module moves out of a workflow folder **if and only if more than one workflow uses it.** Consumer count decides, never taste. The payoff is that anything at a parent level is shared **by definition**, so a reader never opens a file to learn its scope. **This applies to prompt `.md` files exactly as it applies to modules** — see [§ A prompt block with two consumers is promoted](#a-prompt-block-with-two-consumers-is-promoted-and-a-test-enforces-it). The rule was stated for code, the paragraph below noted that we additionally ship prompts, and nobody extended it across — so prompt duplication accumulated with nothing watching, because a copy and an original are the same file type. **The standing count lives in the enforcing test's frozen baseline, not here**: a figure in a standard is falsified by the next PR that improves it.
- **Folder name and file prefix MUST match (rule 4).** `config_apply/` holding `home_assistant_config_apply_*.py` is non-conformant.
- **Purpose folders are optional; module folders are not (rule 5).** A purpose folder is used only *when the grouping earns its level*; a workflow with no natural purpose sibling sits directly under its module.
- **A one-file workflow folder is conformant (rule 6)**, and an **activity-only module** with no workflow at all is an allowed shape that must not be "corrected" into a trio (rule 7).

`{name}_inputs.py` is **optional** (rule 8): per §11.2 input models live in the helper by default and extract only when the helper grows unwieldy. Presence or absence is not a conformance signal.

**Co-location is why this matters more for us than for them.** An infrastructure workflow is three or four `.py` files; ours additionally carries **prompt `.md` files, sometimes several**. Prompts are the substance of an agentic workflow, and a prompt separated from its workflow drifts from it. The reference already does this for non-Python resources — `provision/baseline_tailnet_acl.hujson` and `baseline_tailnet_acl_rationale.md` sit beside the workflow they serve.

**Prompts live in files, never in string literals.** This is a portability rule with teeth: prompt text inside a shell double-quoted string has twice broken a workflow at construction time, because a quote or backtick in prose terminates the string or executes. Python removes that specific hazard and introduces a smaller one via f-string braces. Files remove both, and make prompts diffable as prose. `lint-prompts.sh` exists to catch the bash-era version of this and retires when the last prompt leaves a string literal.

**`{module}` is the DOMAIN of the work, never where it executes.** These are independent axes and collapsing them is the expensive mistake: module is a folder, execution locality is a **task queue** (see `temporal/claude-dot-files-addendum.md` §A3). The first module is `assistant/` — coding plus the general assistance that dogfoods every later edge; the rest are the edges themselves (`home_automation/`, `industrial_automation/`, `robotics/`, `bioinformatics/`).

The assistant edge starts workflows that **execute on another edge's worker**, routed by queue to the machine holding that credential and that hardware. When it does, the workflow still belongs to the module whose domain it acts in: a workflow that *operates* building equipment is `modules/home_automation/` even though Jarvis started it, while a workflow where *the assistant diagnoses* that equipment is `modules/assistant/`. Same machine, same queue, different module.

Filing by execution locality instead would pull every dogfooded workflow into `assistant/` and leave the edge modules empty. **Ask what domain the work is in, not which worker runs it.**

Note what this does NOT do: routing work *to* a dedicated edge is not cross-edge pickup. No worker polls another edge's queue and none claims from a shared pool — the dispatcher decides and the worker never competes.

**Two folders are named `common`, and they mean different things.** `common/` at the root is shared **library code** — logging setup, audit log, activity delegation. `modules/common/` holds **workflows** owned by no edge, such as a reviewer that several parents call. Do not merge them; do not put a workflow in the former.

**Folder names MUST be valid Python identifiers (BINDING, inherited).** `home_automation`, not `home-automation`. `review_pr`, not `review-pr`. Several current names are hyphenated and must be renamed at the port boundary, not after.

#### Current layout, and how each part maps

| Ours today | Target | Status |
|---|---|---|
| `activities/` | `activities/` | **Matches.** Flat today; adopt domain sub-folders as it grows past a handful of files |
| `common/` | `common/` | **Matches.** Gains `types/` when `ActivityResult` arrives |
| `scripts/workflows/*.sh` (parents, monoliths) | `modules/{module}/{purpose}/` | Waypoint |
| `children/` | **no equivalent — dissolves** | Known divergence, see below |

#### The V2 tree is built beside the bash fleet, not on top of it

**The Python/Temporal rewrite lands in `scripts/workflows/temporal/`, and the bash fleet is left untouched.** It keeps running while V2 is built, and each bash workflow is deleted only when its replacement is proven — not before, and never in a bulk move.

This is deliberate: the bash files are in daily production use, and every one of them is going to be deleted anyway. **Reorganizing them to match the target shape is throwaway work** — it churns a working system to buy nothing, since the structure being defined here governs the tree we are about to create, where it costs nothing to get right the first time.

Two shapes coexist for the duration. That is a migration, not a defect. The rename debt this avoids is the expensive kind: renaming fifty Python workflows later, rather than never renaming the bash ones at all.

#### `children/` is a bash-era device with a known expiry

**There is no `children/` directory in the Temporal model, and there should not be one here after the port.** Verified against the live tree: a child workflow is not a *kind of file in a place*, it is **a workflow that another workflow starts**. The relationship is a call, not a location, and every workflow lives in `modules/` regardless of who invokes it.

It earns its keep only because bash cannot express that relationship any other way — there is no call graph to read, so the directory carries the information. **Do not build conventions that depend on it surviving.** Specifically: do not namespace it per parent, do not add sibling directories beside it, and do not write tooling that infers a workflow's role from its path.

What *does* survive the port is the underlying rule, which is about invocation and not about directories:

- **You dispatch** parents and monoliths.
- **A parent invokes children, AND every child is independently runnable by hand.** Both are first-class; standalone is an interface, not a recovery hatch. *(Operator ruling, 2026-08-19. This line previously read "running one by hand is recovery … never the interface", which was wrong in a way that cost real budget: a child you cannot run alone is a child you can only DEBUG at parent prices, and these children are not good out of the box — getting one to perform takes repeated isolated runs. Measured the same week: `research_verify` needed three fix rounds, each re-run through a full parent chain, while `plan-feature` was corrected standalone in one. Autonomy is EARNED by a child that can be exercised, so the ability to exercise it cannot be the reward.)*
- **Children are shared, not owned.** `review-pr` is the last child of every PR-producing parent. A parent may also call a top-level workflow: the composition graph is not a tree.
- **`activities/` and `common/` are sourced, never dispatched.**

#### `activities/` — external I/O, and a parent MUST NOT inline any of it

An activity is workflow-agnostic, has a single technical responsibility, and is **idempotent**: running it twice leaves the world as it was after running it once. Polling, validating, resolving, invoking — idempotent. Pushing a commit or opening a PR is not, and therefore is not an activity.

This is not a style preference. A workflow that performs network I/O **cannot replay**, so the boundary is enforced by the engine and code that ignores it will not port. Writing an activity inline in a parent creates work that must be undone later.

*Breaking it looks like:* a parent containing a poll loop, a `gh` call, a `git fetch`, or a `sleep`.

#### `common/` — shared types and content, NOT a junk drawer

`common/` holds things that execute nothing: prompt text, formatters, shared constants, and eventually the shared result type. The split from `activities/` exists specifically so `activities/` does not become the generic dumping ground. Prompt text is content, not a capability.

For the authoritative inventory of workflows see `docs/guide/workflows.md` — that guide owns the list. This standard governs structure, not inventory.

### Naming (BINDING)

Names are **`<family>-<qualifier>`**, kebab-case, `.sh` suffix. The family is what the script *is*; the qualifier narrows it.

**The read-backwards test.** If the name reads correctly reversed, it is wrong. A PR is not *a type of thing that gets reviewed* — review is the family, `pr` is the qualifier. Hence `review-pr`, not `pr-review`; `review-sprint`, not `sprint-review`. Both of those shipped backwards and were renamed.

The payoff is that families group in `ls` (`review-pr`, `review-runs`, `review-sprint`) and naming a new script becomes a decision rather than a coin flip.

**A rename touches three coupled names, and all three must move together:** the file, the `models:` key in `config.yaml`, and the script's `MODEL_KEY`. A mismatch makes the workflow **silently unlaunchable** — `run-claude.sh` correctly refuses to dispatch on an unresolvable key, but nothing surfaces it until someone tries to run it. This has happened; `lint-prompts.sh` now checks it. Worktree and log prefixes move too, or CPI analysis attributes runs to a workflow name that no longer exists.

**Note:** Workflows are bash scripts, NOT slash commands. Slash commands live in `config/commands/` and are for prompt-template injection in interactive mode. Workflow scripts live in `scripts/workflows/` and are full bash programs that wrap `claude -p` invocations with logging, visibility, and structured stages. These are different things — don't confuse the notation.

### Executable
All workflow scripts must be executable (`chmod +x`). Sourced library files in `lib/` should NOT be marked executable — they are not standalone scripts.

### Shebang
Always use `#!/usr/bin/env bash`. Sourced library files in `lib/` should omit the shebang.

### Safety Pragma
Every workflow script starts with:
```bash
set -euo pipefail
```

This ensures:
- `e`: exit on any error
- `u`: error on unset variables
- `o pipefail`: fail if any command in a pipe fails

## Required Features

**Scope:** The subsections below apply to **task-execution workflows** — scripts that take a user-supplied task description and produce a PR (`build-minor.sh`, `children/build-draft.sh`, `children/build-refine.sh`, `build-phase.sh`, `plan-new.sh`, `plan-revision.sh`).

**Analysis workflows** that derive their inputs from the filesystem without a user-supplied task (e.g. `review-runs.sh`, which scans `.claude/logs/`) MUST still implement the non-task-specific features: verbose flag, JSONL logging, stream format, `run_claude` helper, environment checks, repo-root operation, banners, and a structured prompt. They are exempt from the task-input features (`--pr <N>`, `--task-file <path>`, flags-first positional convention) because those features have no referent — there is no task string to carry. Every subsection below is marked **(task-execution only)** where it applies narrowly.

Everything not marked **(task-execution only)** applies to all workflow scripts. None of it is optional.

### 1. `--verbose` / `-v` Flag

Workflow scripts must support a verbose flag that streams formatted Claude output live during execution. Without this flag, autonomous runs are black boxes — you can't see tool calls, agent spawns, or progress.

```bash
VERBOSE=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        # ... other flags
    esac
done
```

### 2. `--pr <N>` Flag (task-execution only)

Task-execution workflow scripts must support updating an existing PR instead of creating a new one. This enables iterative build loops — rerun the workflow against a PR after review feedback, and it commits and pushes to the PR's existing branch rather than creating a second PR.

```bash
PR_NUMBER=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr)
            if [[ $# -lt 2 ]]; then
                echo "Error: --pr requires a PR number" >&2
                exit 1
            fi
            PR_NUMBER="$2"
            shift 2
            ;;
        # ... other flags
    esac
done
```

When `--pr <N>` is set, the script should:
1. Resolve the PR's branch via `gh pr view <N> --json headRefName`
2. Fetch the latest branch state and create a worktree checked out to `origin/<branch>`
3. Invoke Claude inside the worktree; push to the same branch at the end (this updates the PR)

This is also the integration point for the gh-monitor service — it invokes workflows with `--pr <N>` when responding to `@claude` comments on PRs.

### 3. `--task-file <path>` Flag (task-execution only)

Task-execution workflow scripts must support reading the task description from a file, mutually exclusive with the positional description argument. This flag exists because command-line parsing breaks on multi-paragraph inputs containing quotes, newlines, backticks, or other special characters — a common case for real task descriptions.

```bash
TASK_FILE=""
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
        # ... other flags
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

# Load file into DESCRIPTION (preserves content literally)
if [[ -n "$TASK_FILE" ]]; then
    if [[ ! -f "$TASK_FILE" ]]; then
        echo "Error: task file not found: ${TASK_FILE}" >&2
        exit 1
    fi
    DESCRIPTION=$(cat "$TASK_FILE")
fi
```

The file is read with `cat` and passed through to the prompt verbatim. Content never crosses a shell-parsing boundary, so quotes, newlines, and special characters pass through literally.

### 4. Flags-First Convention (task-execution only)

For scripts that take a positional task description, all examples in usage text and invocations should put flags FIRST and the positional description LAST:

```bash
# Preferred — flags visible at the start, positional at the end
./build.sh --verbose --pr 22 --task-file /tmp/claude-<name>.md
./build.sh --pr 5 "address all findings from PR #5"

# Avoid — positional in the middle gets stepped on by terminal line-wrap
./build.sh "address findings" --pr 5 --verbose
```

Rationale: terminals line-wrap long commands. A trailing positional stays visible and editable even when earlier portions wrap. Flags at the front keep the options obvious at a glance.

### 5. Raw JSONL Logging

Every run writes a raw JSONL log to `.claude/logs/<workflow>-<timestamp>.jsonl` regardless of verbose mode. This enables post-mortem analysis even for runs that weren't watched live.

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/<workflow>-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"
```

**Why raw JSONL only (not pre-formatted):**
- Raw is **lossless** — no information is dropped
- Claude can read it directly for self-diagnosis (primary use case — 99% of log reads)
- `jq` can query it for metrics and analysis
- Can always be formatted on-demand for human reading via the formatter
- Formatted text is lossy and cannot be reversed back to raw

**Expected log access patterns:**
1. **Claude self-diagnosis** (most common): `claude 'read <log-file> and tell me what happened'`
2. **Human reading** (occasional): `cat <log-file> | scripts/workflows/common/format-stream.sh`
3. **Metric queries** (ongoing): `jq 'select(.type == "result")' <log-file>`

**Important:** The log directory is always in the main repo's `.claude/logs`, not inside worktrees. This keeps all logs in one place for analysis.

### 6. Stream Format Usage

Always invoke Claude with `--output-format stream-json`. This gives structured events that can be formatted for display AND saved for analysis.

The shared formatter at `scripts/workflows/common/format-stream.sh` reads JSONL from stdin and outputs formatted human-readable text. Use it for live display in verbose mode.

### 7. Standard run_claude Helper

Every workflow script must source the shared `run_claude` helper from `scripts/workflows/activities/run-claude.sh`. This avoids duplicating the verbose/quiet invocation logic across every workflow script.

The shared library requires four environment variables to be set before sourcing:
- `LOG_FILE` — path to the JSONL log file for this run
- `MAX_TURNS` — maximum conversation turns for claude
- `VERBOSE` — `true` or `false` for live streaming
- `FORMATTER` — path to the format-stream.sh formatter script

```bash
# Source the shared run_claude helper (requires LOG_FILE, MAX_TURNS, VERBOSE, FORMATTER)
source "${SCRIPT_DIR}/lib/run-claude.sh"
```

Usage is the same as before — call `run_claude` with a prompt and optional extra args:

```bash
run_claude "$PROMPT" -w "$WORKTREE_NAME"
```

### 8. Environment Checks

Every workflow script must verify its dependencies before running:

```bash
if ! command -v claude &>/dev/null; then
    echo "Error: 'claude' CLI not found in PATH" >&2
    exit 1
fi

if ! command -v gh &>/dev/null; then
    echo "Error: 'gh' CLI not found in PATH" >&2
    exit 1
fi

if ! command -v jq &>/dev/null; then
    echo "Error: 'jq' not found in PATH" >&2
    exit 1
fi

if ! git rev-parse --show-toplevel &>/dev/null; then
    echo "Error: not inside a git repository" >&2
    exit 1
fi

if [[ ! -x "$FORMATTER" ]]; then
    echo "Error: stream formatter not found at ${FORMATTER}" >&2
    exit 1
fi
```

Fail fast if anything is missing. Don't assume tools are available.

### 9. Repo Root Operation

Always operate from the repo root to ensure consistent paths:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
```

This makes worktree paths, log paths, and relative file references consistent regardless of where the script is invoked from.

### 10. Worktree Isolation

All workflow scripts that modify code use git worktrees for isolation. Worktrees go in `.claude/worktrees/<workflow>-<timestamp>/` and the main working directory is never touched.

Two patterns:
- **New branch:** Use `claude -p -w <name>` — Claude Code creates the worktree with auto-prefixed branch name
- **Update existing PR:** Manually create worktree checked out to the PR's branch, then invoke claude inside it

### 11. Summary Banner

Every run starts with a summary banner showing the configuration:

```bash
echo "================================================================"
echo "  BUILD WORKFLOW"
echo "================================================================"
echo "  Description : ${DESCRIPTION}"
echo "  Target      : ${TARGET}"
echo "  Worktree    : ${WORKTREE_NAME}"
echo "  Max turns   : ${MAX_TURNS}"
echo "  Verbose     : ${VERBOSE}"
echo "  Log file    : ${LOG_FILE}"
echo "================================================================"
```

This makes it obvious what's about to happen and where to find the log.

### 12. Completion Summary

Every run ends with a completion banner showing where the log and worktree live:

```bash
echo "================================================================"
echo "  WORKFLOW COMPLETE"
echo "================================================================"
echo "Worktree: ${WORKTREE_PATH}"
echo "Log file: ${LOG_FILE}"
echo
echo "To clean up when done:"
echo "  /cleanup-merged-worktrees"
```

### 13. Structured Prompt

Every workflow script embeds a structured prompt with numbered stages. The prompt is the specification for Claude's behavior in the autonomous run.

```bash
PROMPT=$(cat <<EOF
You are executing the [WORKFLOW NAME] workflow.

Task: ${DESCRIPTION}

Follow these stages exactly:

1. [STAGE 1 NAME]: [instructions]
2. [STAGE 2 NAME]: [instructions]
3. [STAGE 3 NAME]: [instructions]
...

Rules:
- [constraint 1]
- [constraint 2]
...

At the end, [what Claude should report].
EOF
)
```

**⚠️ Heredoc context:** The heredoc above is INTERNAL to the script — it assembles the prompt string inside the script process, and the assembled string is then passed to `claude -p` via the shell. It never crosses a terminal copy-paste boundary, so there is no risk of whitespace corruption.

This is the opposite case from `config/CLAUDE.md :: Terminal Commands & Prompts`, which forbids heredocs in USER-FACING command output (commands shown to the user to paste into their terminal). That rule exists because terminal paste reliably corrupts multi-line input. Inside a script, heredocs are fine and preferred for multi-line prompt construction — they handle quotes, backticks, and special characters without manual escaping.

**Quoted vs unquoted sentinel:** Use an unquoted `EOF` when the heredoc body must interpolate shell variables (like `${DESCRIPTION}`). Use a quoted `'EOF'` sentinel for any static block that should pass through literally — backticks, `$symbols`, and dollar-brace tokens all survive untouched, so you don't have to hunt down escape edge cases. Default to quoted when the block has no variables; it's the safer choice.

`scripts/workflows/children/build-refine.sh` shows both idioms in one file: the stage block and `RULES` are quoted (`'STAGES_EOF'`, `'RULES_EOF'`) because they're static, and the final `PROMPT` is built with double-quoted string concatenation so the stage text, `${RULES}`, and `${DESCRIPTION}` can interpolate. Safety from accidental expansion is the reason for the quoted sentinels.

## Composition (BINDING)

A **parent** is a workflow that calls other workflows and calls no model itself. It holds no `MODEL_KEY`, no turn budget, and — this is the rule — **no process code.** A parent decides *if*, *when* and *what* to call. Everything else belongs to a child or an activity.

The test is not lines of code and it is not DRY. **It is: does this touch the outside world?** I/O goes down to `activities/`; pure decision logic stays in the parent. Parsing a verdict string and extracting an identifier are decision logic and belong in the parent even if they appear in five parents. A poll loop used exactly once is still an activity.

### Why compose at all — the boundary is the point

A run that both authors work and rules on the review findings about it **will defend its own work**. This is not a prompt-quality problem and cannot be fixed by wording: engineer self-review, four in-context review agents under an explicit disposition taxonomy, and manual verification all failed to catch defects that a fresh-context pass then found in minutes.

So the run that authors is not the run that judges. Neither child inherits the other's context; the handoff is git plus the original task, and **the original task must reach both** — without it, a reviewing child can only ask *"is this code good?"* and never *"did this deliver what was asked?"*, which is the question that catches missing scope and scope creep.

**A second, independent reason, and it is the one that decides marginal cases:** every child boundary is a **retry/resume point**. A monolith has none — it fails at stage 3 and restarts from stage 1, forever, with a human watching. Under durable execution that boundary is the unit of recovery. Compose for the bias boundary; compose *again* for recoverability.

**Do not compose for its own sake.** A single-purpose workflow with nothing to reuse is correctly monolithic, and manufacturing children adds dispatch overhead for no gain. The test is *"am I about to reimplement something that already exists as a workflow or an activity?"* — if yes, compose it.

### The completion contract IS the interface

Every model-invoking workflow declares a `COMPLETION_PATTERN`: an ERE its final output must contain. Missing it fails **loud** and returns non-zero.

**`exit 0` must mean the work is done.** A headless run terminates on any turn that produces text without a tool call — invisible interactively, fatal here. A run that dispatches agents and then says *"waiting for results…"* has ended itself, reports exit 0, and produced nothing. Without the contract, "the workflow ran fine" and "the workflow did nothing" are the same signal.

The contract was built for that failure and turns out to do a second job: **it is how one workflow hands off to another.** A parent needs exactly two things from a child — a reliable exit code, and one stable identifier on its final line. That is the entire interface, and it is why composition needs no framework.

*Breaking it looks like:* a model-invoking workflow with no `COMPLETION_PATTERN`, or a final line that is prose rather than the declared identifier.

### Routing contracts

When a child's result decides what the parent does next, that result is a **contract**, not prose.

- **Closed vocabulary.** A fixed, enumerable set of values. Anchor the pattern so prose mentioning a token cannot match it.
- **The actor that decided does the aggregating.** If a verdict must be derived from several per-item fields, the child derives it and states it. A caller re-deriving a verdict from a child's internal findings is a caller with no stake making a judgement *about* the child's judgement.
- **Fail safe, never guess.** An absent or unparseable result routes to the outcome requiring a human. Never default to the permissive branch. **This matters more here than in any CI system:** our producer is an LLM that can emit a plausible-looking but wrong result — an assumption general-purpose orchestrators do not have to defend against.
- **The signal should carry its payload.** A token saying *what* to do next without saying *with what* forces the next actor to re-derive context the deciding actor already had.

### Bounded composition

**Any loop a parent runs MUST have a bounded, observable exit.** One-way composition over a fixed set of children is deterministic and cheap to reason about. A cycle that re-enters until it decides it is satisfied is neither, and is forbidden.

**Prefer convergence over counting.** The honest stopping condition is *"this pass produced nothing new"* — not *"we have done N passes."* A count is a proxy for the thing you actually care about, and it is wrong in both directions: too low stops while passes are still productive, too high burns passes after they stop being.

**Do not legislate a pass count from a single run.** A measured three-cycle run and a cited plateau band are both evidence; neither is a constant. Where a bound must exist before convergence is mechanizable, state it as a temporary floor with its reasoning, not as a discovered law.

### Turn caps are runaway guards, not budgets

An unused turn costs nothing — spend follows turns consumed. Raising a ceiling costs zero on every run that never reaches it.

**A cap cannot buy reliability; it can only truncate.** Reliability comes from scope discipline — the workflow-fit check, the routing decision, the size of the task handed to a child. All a low ceiling does to a mis-scoped run is kill it partway and strand the work.

The routing signal reads off **consumption, not termination**: a child routinely *spending* most of its budget was mis-sized and wants the next workflow up. Watch what it spends, not whether it hit the wall.

## Design Principles

### Keep Stages Explicit
Number the stages in the prompt. Give each stage a verb name (ASSESS, IMPLEMENT, TEST, COMMIT). This helps Claude track progress and helps you identify where failures happen.

### Minimal Tool Access via Prompt Constraints
Use rules in the prompt to constrain behavior. Autonomous mode uses `--dangerously-skip-permissions` which bypasses the allow/deny lists — the only restrictions come from:
1. The `block-dangerous.sh` hook (always active)
2. Rules in the workflow's prompt

Be explicit about what Claude should NOT do.

### Single claude -p vs Multiple
For small workflows (like `build.sh`), a single `claude -p` call handles all stages in one session. Context bloat isn't a concern for small tasks.

For larger workflows (like `build-phase.sh`), break into multiple `claude -p` calls with state passed via files. This gets fresh context per stage and avoids context bloat.

### Scope Narrowly
Tell Claude to focus only on the task. Research has shown unscoped exploration ("investigate the codebase") burns tokens for no value.

### Max Turns Per Script

Each workflow script sets a `MAX_TURNS` ceiling based on its stage count and observed complexity. The authoritative current values live in `docs/guide/workflows.md` alongside the workflow inventory — keep them there so they don't drift across two locations.

**Why ceilings, not formulas:** Values are raised when production runs surface real ceiling hits — most commonly during REVIEW stages when a long back-and-forth with an agent pushed past the prior limit. Each bump is a targeted response to an observed crash, not a proactive multiplier.

**Guidance for new scripts:** Pick the entry in the guide's table whose stage count and complexity most resemble your new workflow, then add ~30-50% headroom. Unused turns cost nothing; crashing a 45-minute autonomous run at turn N-1 costs a full rerun. When in doubt, err high — the ceiling exists to catch runaway loops, not to force tight budgeting.

## Safety Conventions

### Use `--dangerously-skip-permissions`
Autonomous workflows run with `--dangerously-skip-permissions`. This is safe because:
1. Worktree isolation limits blast radius
2. `block-dangerous.sh` hook still fires (hard safety floor)
3. PR review is the final gate

### The safety-layer invariant (BINDING)

**Because headless dispatches bypass permissions, the `PreToolUse` hook is the only remaining safety layer.** Point 2 above is not a defence-in-depth nicety; with point 1 scoped to a worktree and point 3 happening after the fact, that hook is the sole control operating *during* the run.

That hook is configured in the **user-level** `settings.json`.

**Therefore: any change to which setting sources load MUST prove the hook survives, before it lands.** `--setting-sources project,local` looks like a two-line improvement for making dispatch configuration explicit. It would drop user settings, and with them the hook, removing destructive-command blocking from every autonomous run. A two-line change becomes a two-line safety regression.

*Breaking it looks like:* adding, narrowing or reordering `--setting-sources`, moving hook configuration between scopes, or changing what `install.sh` symlinks — without first demonstrating that a headless run still triggers `block-dangerous.sh`.

### Validate Inputs
Validate arguments before doing anything destructive. Bad input should fail loud and early, not after creating a worktree.

### Fail Loud on Missing Dependencies
If `gh`, `claude`, `jq`, or the formatter isn't available, fail immediately with a clear error. Don't try to continue.

### Never Write to main
Workflow scripts write to worktree branches, not `main` directly. The only way changes reach `main` is through PR review and merge.

### Test Fixture Placement
Test fixtures must be placed in `/tmp/` or `tests/fixtures/`, never in `.claude/` paths. The `block-dangerous.sh` hook monitors `.claude/` paths and will trigger permission denials on writes there, causing spurious test failures. This applies to any test that creates temporary files, mock configs, or sample data.

## Template

A minimal workflow script skeleton:

```bash
#!/usr/bin/env bash
# workflow-name.sh — Description of what this workflow does
#
# Usage: ./workflow-name.sh "description" [--pr N] [--verbose]
#        ./workflow-name.sh --task-file path/to/task.md [--pr N] [--verbose]

set -euo pipefail

# ---- Script location ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORMATTER="${SCRIPT_DIR}/lib/format-stream.sh"

# ---- Configuration ----
# See "Max Turns Per Script" section above — pick a value from the table
# based on your workflow's stage count and complexity.
MAX_TURNS=100

# ---- Argument parsing ----
DESCRIPTION=""
TASK_FILE=""
PR_NUMBER=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task-file)
            [[ $# -ge 2 ]] || { echo "Error: --task-file requires a path" >&2; exit 1; }
            TASK_FILE="$2"; shift 2 ;;
        --pr)
            [[ $# -ge 2 ]] || { echo "Error: --pr requires a PR number" >&2; exit 1; }
            PR_NUMBER="$2"; shift 2 ;;
        --verbose|-v) VERBOSE=true; shift ;;
        -*) echo "Error: unknown option '$1'" >&2; exit 1 ;;
        *)
            [[ -z "$DESCRIPTION" ]] || { echo "Error: unexpected positional '$1'" >&2; exit 1; }
            DESCRIPTION="$1"; shift ;;
    esac
done

# Exactly one of: positional description OR --task-file
if [[ -n "$DESCRIPTION" && -n "$TASK_FILE" ]]; then
    echo "Error: cannot combine positional description with --task-file" >&2; exit 1
fi
if [[ -z "$DESCRIPTION" && -z "$TASK_FILE" ]]; then
    echo "Usage: $(basename "$0") \"description\" [--pr N] [--verbose]" >&2
    echo "       $(basename "$0") --task-file path/to/task.md [--pr N] [--verbose]" >&2
    exit 1
fi
if [[ -n "$TASK_FILE" ]]; then
    [[ -f "$TASK_FILE" ]] || { echo "Error: task file not found: $TASK_FILE" >&2; exit 1; }
    DESCRIPTION=$(cat "$TASK_FILE")
fi

# ---- Environment checks ----
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

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# ---- Naming and paths ----
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
WORKTREE_NAME="workflow-name-${TIMESTAMP}"
LOG_DIR="${REPO_ROOT}/.claude/logs"
LOG_FILE="${LOG_DIR}/workflow-name-${TIMESTAMP}.jsonl"
mkdir -p "$LOG_DIR"

# ---- Banner ----
echo "================================================================"
echo "  WORKFLOW NAME"
echo "================================================================"
echo "  Description: ${DESCRIPTION}"
echo "  Worktree   : ${WORKTREE_NAME}"
echo "  Verbose    : ${VERBOSE}"
echo "  Log file   : ${LOG_FILE}"
echo "================================================================"

# ---- run_claude helper (shared library) ----
source "${SCRIPT_DIR}/lib/run-claude.sh"

# ---- Workflow logic ----
PROMPT=$(cat <<EOF
You are executing the [WORKFLOW NAME] workflow.

Task: ${DESCRIPTION}

Follow these stages exactly:
1. STAGE_1: ...
2. STAGE_2: ...

Rules:
- ...

At the end, report ...
EOF
)

run_claude "$PROMPT" -w "$WORKTREE_NAME"

# ---- Completion ----
echo
echo "================================================================"
echo "  WORKFLOW COMPLETE"
echo "================================================================"
echo "Log file: ${LOG_FILE}"
```

## Prompt economy — a prompt is re-read on every turn (BINDING)

**A prompt is not read once. It is re-sent on every turn of every run, forever.** A 5 KB block added to a
prompt used by a 175-turn build is 875 KB of re-read on that run alone, and the same on the next one.

**Measured 2026-08-14.** Prompts in this tree grew **224 KB → 317 KB in seven days**, every byte of it a
correct lesson. Over the same period a run's starting context went **34k → 57k tokens** and cost per run
went **$1.90 → $13.17**. Tokens per turn — which is model-independent — went up **4x**.

### What earns a place (all four must hold)

1. **It changes what the model DOES**, not what it knows.
2. **The model would not do it by default.** Do not instruct a capable reasoner in the obvious.
3. **The harness does not already enforce it.** `Edit` errors without a prior `Read`; the tool result
   reports a reset working directory. Restating those spends bytes on every turn and changes nothing.
4. **It applies to MOST runs of that workflow.** A rule for a rare case belongs in that case's dispatch
   brief, which is paid once.

### The rule goes in the prompt; the evidence goes in the commit

Same discipline [§ Standards state the rule](../standards/documentation/documentation_standard.md) applies
to standards, and for the same reason: narrative is re-read forever and changes no behaviour.

- **In the prompt:** the instruction, and at most one clause of *why* where the why prevents a wrong reading.
- **In the commit:** the run it was measured on, the count of occurrences, what it cost, what it replaced.

**A prompt line that opens with a date, a run id, or "measured" is evidence.** Move it.

### Every prompt carries a byte budget, and a test enforces it

Budgets are declared in `testing/scripts/tests/unit/test_prompt_budgets.py` and the suite fails when one is
exceeded. **The point is not the ceiling; it is that ADDING becomes a TRADE.**

**Why a budget rather than review discipline:** prompts grew 42% in a week under review, because adding is
visible work and removing is nobody's job. A budget makes every addition compete with what it displaces.

**Raising a budget is allowed and is a normal decision** — it is a one-line change with a reason in the
commit. What is not allowed is raising it silently as a side effect of adding text.

### Proportional rigour — match the bar to the change

The instructions a prompt carries about *how thoroughly to verify* are its largest and most expensive
component. They must discriminate:

| Change | Bar |
|---|---|
| One file, one function, no contract change | minor tier; one review lens; mutation only if the change IS a guard |
| A new module, a new contract, or a schema | full tier; mutation; multi-lens review |
| Anything touching a safety control, a gate, or an authorization boundary | all of it, no exceptions |

**Applying the last row to everything is the failure this section exists to prevent.** It reads as care and
is indistinguishable, from the outside, from having no judgement about risk.

### A prompt block with two consumers is promoted, and a test enforces it

**A block that appears verbatim in two children moves to `modules/assistant/prompts/` and is referenced by placeholder.** This is the promotion rule above, applied to prose: consumer count decides, never taste. The shared pool sits above *all* families, so a fragment may be shared by a build child and a research child — family boundaries do not enter into it.

**Why it is an economy rule and not a tidiness one.** A duplicated block is re-sent on every turn of every run that loads it, so the cost is paid per-turn, per-copy, forever. It is also how a rule silently stops applying: `stages_1_to_4.md` and its `_from_plan` sibling forked, the plan variant never received eleven testing rules, and **every phase built from a plan ran without the instruction that says how much rigour to apply** — the § *Proportional rigour* table above. Nobody chose that. A copy simply stopped being updated, and no reader could tell, because a copy and an original are the same file type.

**Mechanically:** move the block to `modules/assistant/prompts/<name>.md`, put a placeholder where it was in each child, and pass `"NAME": act.shared_prompt("<name>")` in each workflow's values dict. `prompts/mutation_discipline.md` is the worked example. A shared fragment carrying its own placeholders is allowed, and **every** consumer must supply them — one that does not renders a live `${…}` and `render()` raises at dispatch rather than in the suite.

**Enforced by `test_prompt_blocks_are_shared_not_copied.py`**, which freezes the duplication that existed when the rule landed and ratchets **both ways**: a duplicated block absent from the baseline fails, and a baseline entry that is no longer duplicated also fails so its line must be deleted. The second is what makes the list shrink rather than become a permanent excuse list — a fix cannot be made without the baseline shrinking to match.

**What the test does NOT see, so the rule is not over-read: near-duplicates.** Matching is verbatim, so a copy that has already drifted by one word is invisible — and a drifted copy is the more dangerous kind, because it reads as intent rather than as an accident. Same-named prompts across sibling children have been measured well above half-identical and none appears in the baseline — the current figures are reproducible with a similarity pass over `modules/assistant/**/prompts/*.md`, and are deliberately not restated here. **That half is a judgement about which differences are deliberate, and it belongs to the fork-vs-parameterize ruling, not to a test.**

## Prompt-string authoring (BINDING — prompt strings are code)

A workflow's `PROMPT` is a double-quoted bash assignment (or an unquoted heredoc). **Everything bash treats specially inside it is EVALUATED at runtime.** Two fleet outages in one day came from this class, both invisible to `bash -n`:

| Vector | What happens | Why `bash -n` misses it |
|---|---|---|
| Unescaped **backtick** | `` `run_in_background: false` `` runs as a command → exit 127 | syntactically valid |
| Unescaped **`"` around a phrase with whitespace** | closes `PROMPT` mid-string; remaining prose parses as commands → `until: command not found` | the stray quotes **balance** (even count) — valid bash that means something else |
| Unescaped **`$( )`** | command substitution executes | syntactically valid |

**The rules:**

1. **Quoted example phrases → use SINGLE quotes.** `'deferred until a second adopter exists'`, never `"…"`. Safe by construction inside a double-quoted assignment.
2. **Code references → use ESCAPED backticks.** `` \`run_in_background: false\` ``, never bare.
3. **Never use `$( )` in prompt prose.** `${VAR}` interpolation is fine and intended; command substitution is not.
4. **A stray `"` pair with NO whitespace inside is harmless by accident** (bash concatenates the bare word) — do not rely on it. Adding one space later breaks the fleet.

**Gate (run BOTH before committing any prompt change):**

```
scripts/helpers/lint-prompts.sh && bash -n scripts/workflows/<script>.sh
```

They are complementary and **neither alone is sufficient**: `bash -n` catches *unbalanced* quotes; `lint-prompts.sh` constructs every prompt block in a sandbox (`env -i`, PATH containing only `cat`) and fails if bash does anything other than assign a string. The lint is an **execution check, not a pattern check** — that is deliberate: a per-vector pattern list built for backticks certified as clean a file that could not launch. Executing generalizes to vectors nobody has enumerated yet (validated: it catches `$( )`, which was never in its rules).

## Testing a New Workflow Script

Before marking a new workflow script as complete:

1. **Usage check:** Run without arguments, verify usage message prints
2. **Quiet mode test:** Run with a simple task, verify it completes and produces the final summary
3. **Verbose mode test:** Run with `--verbose`, verify live stream output is readable
4. **Log verification:** Verify `.claude/logs/<workflow>-<ts>.jsonl` exists and contains structured events
5. **Failure mode:** Run with bad input, verify it fails loud and early
6. **Worktree cleanup:** After a successful run, verify `/cleanup-merged-worktrees` removes artifacts

## Critical Rules

- **Workflow scripts MUST support `--verbose` flag** — visibility is not optional
- **Task-execution workflow scripts MUST support `--pr <N>` flag** — enables iterative build and gh-monitor integration (does not apply to analysis workflows like `review-runs.sh` that have no user-supplied task)
- **Task-execution workflow scripts MUST support `--task-file <path>` flag** — required for multi-paragraph/special-character payloads (same scope carve-out)
- **Workflow scripts MUST log to `.claude/logs/`** — post-mortem analysis matters
- **Workflow scripts MUST validate environment upfront** — fail fast
- **Workflow scripts MUST operate from repo root** — consistent paths
- **Workflow scripts MUST use worktree isolation** — main branch is sacred
- **Workflow scripts MUST have structured staged prompts** — not unscoped instructions
- **Workflow scripts MUST use `run_claude` helper pattern** — consistent invocation
- **Workflow scripts SHOULD follow the per-script `MAX_TURNS` values** in the table above
- **Prompt edits MUST pass `lint-prompts.sh` AND `bash -n`** — see "Prompt-string authoring"; prompt strings are code, and two fleet outages came from treating them as text

## Related Documentation

- `docs/guide/workflows.md` — Authoritative user-facing workflow guide (start here)
- `docs/guide/claude_code_headless.md` — Headless mode details
- `docs/guide/claude_code_orchestration.md` — Orchestration patterns
- `docs/standards/hook-scripts.md` — Hook script conventions (complementary)
- `config/CLAUDE.md` — Workflow invocation template and terminal paste rules
