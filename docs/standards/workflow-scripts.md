# Workflow Script Standards

Conventions for writing autonomous workflow scripts in `scripts/workflows/`.

## Purpose

Workflow scripts implement the autonomous side of the Dual Workflow Model (see `docs/guide/workflows.md`). They wrap `claude -p` invocations with structured stages, safety guards, visibility, and logging. These are the scripts you run to hand off work to Claude and come back to a PR.

## File Conventions

### Location
All workflow scripts live in `scripts/workflows/`. Helper libraries go in `scripts/workflows/lib/`.

```
scripts/
└── workflows/
    ├── lib/
    │   ├── format-stream.sh    # shared stream-json formatter
    │   └── run-claude.sh       # shared run_claude helper function
    ├── revision.sh             # minor corrections
    ├── revision-major.sh       # significant rework
    ├── build-phase.sh          # architect and build from a plan
    ├── plan-new.sh             # research and planning (new project)
    ├── plan-revision.sh        # revise existing planning docs
    └── review-runs.sh          # CPI analysis of workflow JSONL logs
```

### Naming
Script names use kebab-case matching the workflow's purpose, with `.sh` suffix:
- `revision.sh` — minor corrections workflow
- `revision-major.sh` — significant rework workflow
- `build-phase.sh` — implement from a plan document
- `plan-new.sh` — research and planning for a new project
- `plan-revision.sh` — revise existing planning docs
- `review-runs.sh` — CPI analysis of workflow JSONL logs

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

**Scope:** The subsections below apply to **task-execution workflows** — scripts that take a user-supplied task description and produce a PR (`revision.sh`, `revision-major.sh`, `build-phase.sh`, `plan-new.sh`, `plan-revision.sh`).

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

Task-execution workflow scripts must support updating an existing PR instead of creating a new one. This enables iterative revision loops — rerun the workflow against a PR after review feedback, and it commits and pushes to the PR's existing branch rather than creating a second PR.

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
./revision-major.sh --verbose --pr 22 --task-file /tmp/task.md
./revision-major.sh --pr 5 "address all findings from PR #5"

# Avoid — positional in the middle gets stepped on by terminal line-wrap
./revision-major.sh "address findings" --pr 5 --verbose
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
2. **Human reading** (occasional): `cat <log-file> | scripts/workflows/lib/format-stream.sh`
3. **Metric queries** (ongoing): `jq 'select(.type == "result")' <log-file>`

**Important:** The log directory is always in the main repo's `.claude/logs`, not inside worktrees. This keeps all logs in one place for analysis.

### 6. Stream Format Usage

Always invoke Claude with `--output-format stream-json`. This gives structured events that can be formatted for display AND saved for analysis.

The shared formatter at `scripts/workflows/lib/format-stream.sh` reads JSONL from stdin and outputs formatted human-readable text. Use it for live display in verbose mode.

### 7. Standard run_claude Helper

Every workflow script must source the shared `run_claude` helper from `scripts/workflows/lib/run-claude.sh`. This avoids duplicating the verbose/quiet invocation logic across every workflow script.

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
echo "  REVISION WORKFLOW"
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

`scripts/workflows/revision-major.sh` shows both idioms in one file: `STAGES_1_TO_9` and `RULES` are quoted (`'STAGES_EOF'`, `'RULES_EOF'`) because they're static, and the final `PROMPT` is built with double-quoted string concatenation so `${STAGES_1_TO_9}`, `${RULES}`, and `${DESCRIPTION}` can interpolate. The quoted sentinels also happen to enable reuse of the block across the new-branch and existing-PR code paths, but that's a secondary benefit — safety from accidental expansion is the primary one.

## Design Principles

### Keep Stages Explicit
Number the stages in the prompt. Give each stage a verb name (ASSESS, IMPLEMENT, TEST, COMMIT). This helps Claude track progress and helps you identify where failures happen.

### Minimal Tool Access via Prompt Constraints
Use rules in the prompt to constrain behavior. Autonomous mode uses `--dangerously-skip-permissions` which bypasses the allow/deny lists — the only restrictions come from:
1. The `block-dangerous.sh` hook (always active)
2. Rules in the workflow's prompt

Be explicit about what Claude should NOT do.

### Single claude -p vs Multiple
For small workflows (like `revision.sh`), a single `claude -p` call handles all stages in one session. Context bloat isn't a concern for small tasks.

For larger workflows (like `build-phase.sh`), break into multiple `claude -p` calls with state passed via files. This gets fresh context per stage and avoids context bloat.

### Scope Narrowly
Tell Claude to focus only on the task. Research has shown unscoped exploration ("investigate the codebase") burns tokens for no value.

### Max Turns Per Script

Current per-script values as of April 2026:

| Script | `MAX_TURNS` |
|--------|-------------|
| `revision.sh` | 60 |
| `review-runs.sh` | 60 |
| `revision-major.sh` | 150 |
| `build-phase.sh` | 300 |
| `plan-revision.sh` | 300 |
| `plan-new.sh` | 500 |

**Why these specific values:** All six were **doubled from their original values in April 2026** after production runs crashed mid-implementation when the smaller limits were exhausted — usually during the REVIEW or REFACTOR stages when a long back-and-forth with an agent pushed the turn count past the prior ceiling. Doubling gave comfortable headroom without meaningfully increasing the cap-hit rate on successful runs.

**Guidance for new scripts:** Match the size of an existing script with a similar stage count, then multiply by ~2 for safety. Start with the doubled value — it's cheaper to have unused headroom than to crash a 45-minute autonomous run at turn 149.

## Safety Conventions

### Use `--dangerously-skip-permissions`
Autonomous workflows run with `--dangerously-skip-permissions`. This is safe because:
1. Worktree isolation limits blast radius
2. `block-dangerous.sh` hook still fires (hard safety floor)
3. PR review is the final gate

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
MAX_TURNS=60

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
- **Task-execution workflow scripts MUST support `--pr <N>` flag** — enables iterative revision and gh-monitor integration (does not apply to analysis workflows like `review-runs.sh` that have no user-supplied task)
- **Task-execution workflow scripts MUST support `--task-file <path>` flag** — required for multi-paragraph/special-character payloads (same scope carve-out)
- **Workflow scripts MUST log to `.claude/logs/`** — post-mortem analysis matters
- **Workflow scripts MUST validate environment upfront** — fail fast
- **Workflow scripts MUST operate from repo root** — consistent paths
- **Workflow scripts MUST use worktree isolation** — main branch is sacred
- **Workflow scripts MUST have structured staged prompts** — not unscoped instructions
- **Workflow scripts MUST use `run_claude` helper pattern** — consistent invocation
- **Workflow scripts SHOULD follow the per-script `MAX_TURNS` values** in the table above

## Related Documentation

- `docs/guide/workflows.md` — Authoritative user-facing workflow guide (start here)
- `docs/guide/claude_code_headless.md` — Headless mode details
- `docs/guide/claude_code_orchestration.md` — Orchestration patterns
- `docs/standards/hook-scripts.md` — Hook script conventions (complementary)
- `config/CLAUDE.md` — Workflow invocation template and terminal paste rules
