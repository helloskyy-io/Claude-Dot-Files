# Workflow Script Standards

Conventions for writing autonomous workflow scripts in `scripts/workflows/`.

## Purpose

Workflow scripts implement the autonomous side of the Dual Workflow Model (see `docs/guide/dual_workflow_model.md`). They wrap `claude -p` invocations with structured stages, safety guards, visibility, and logging. These are the scripts you run to hand off work to Claude and come back to a PR.

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
    ├── build-phase.sh          # architect and build
    └── define-project.sh       # research and planning
```

### Naming
Script names use kebab-case matching the workflow's purpose, with `.sh` suffix:
- `revision.sh` — minor corrections workflow
- `revision-major.sh` — significant rework workflow
- `build-phase.sh` — architect and build a phase workflow
- `define-project.sh` — research and planning workflow

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

Every workflow script MUST implement these features. They are not optional.

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

### 2. Raw JSONL Logging

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

### 3. Stream Format Usage

Always invoke Claude with `--output-format stream-json`. This gives structured events that can be formatted for display AND saved for analysis.

The shared formatter at `scripts/workflows/lib/format-stream.sh` reads JSONL from stdin and outputs formatted human-readable text. Use it for live display in verbose mode.

### 4. Standard run_claude Helper

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

### 5. Environment Checks

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

### 6. Repo Root Operation

Always operate from the repo root to ensure consistent paths:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
```

This makes worktree paths, log paths, and relative file references consistent regardless of where the script is invoked from.

### 7. Worktree Isolation

All workflow scripts that modify code use git worktrees for isolation. Worktrees go in `.claude/worktrees/<workflow>-<timestamp>/` and the main working directory is never touched.

Two patterns:
- **New branch:** Use `claude -p -w <name>` — Claude Code creates the worktree with auto-prefixed branch name
- **Update existing PR:** Manually create worktree checked out to the PR's branch, then invoke claude inside it

### 8. Summary Banner

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

### 9. Completion Summary

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

### 10. Structured Prompt

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

### Max Turns Based on Complexity

| Workflow Size | Suggested `MAX_TURNS` |
|---------------|----------------------|
| Minor (revision) | 30 |
| Medium (revision-major) | 75 |
| Large (build-phase) | 150 |
| Extra large (define-project) | 200 |

Start conservative. Bump up only if runs hit the limit and fail.

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
# Usage: ./workflow-name.sh "description" [--verbose]

set -euo pipefail

# ---- Script location ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORMATTER="${SCRIPT_DIR}/lib/format-stream.sh"

# ---- Configuration ----
MAX_TURNS=30

# ---- Argument parsing ----
if [[ $# -lt 1 ]]; then
    echo "Usage: $(basename "$0") \"description\" [--verbose]"
    exit 1
fi

DESCRIPTION="$1"
shift
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --verbose|-v) VERBOSE=true; shift ;;
        *) echo "Error: unknown option '$1'" >&2; exit 1 ;;
    esac
done

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
- **Workflow scripts MUST log to `.claude/logs/`** — post-mortem analysis matters
- **Workflow scripts MUST validate environment upfront** — fail fast
- **Workflow scripts MUST operate from repo root** — consistent paths
- **Workflow scripts MUST use worktree isolation** — main branch is sacred
- **Workflow scripts MUST have structured staged prompts** — not unscoped instructions
- **Workflow scripts MUST use `run_claude` helper pattern** — consistent invocation
- **Workflow scripts SHOULD match the `MAX_TURNS` guideline** for their complexity

## Related Documentation

- `docs/guide/dual_workflow_model.md` — Architectural context
- `docs/guide/claude_code_headless.md` — Headless mode details
- `docs/guide/claude_code_orchestration.md` — Orchestration patterns
- `docs/standards/hook-scripts.md` — Hook script conventions (complementary)
