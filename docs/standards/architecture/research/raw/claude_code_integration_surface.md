# Claude Code Integration Surface — Engineering Reference

```
Topic:          What can a program actually invoke Claude Code to do, and through which surfaces?
Feeds:          Phase: Temporal Integration -> the claude_cli activity domain
Last validated: 2026-07-25
Revalidate:     high — 4 weeks
Confidence:     Definitive on flags and documented behaviour as of the validation date; the CLI surface changes frequently and undocumented behaviour is unverified.
Critic:         PASS — 2026-07-25
```

**Purpose:** Enumerate the documented, externally-observable contract of the Claude Code CLI so a Temporal activity wrapper can be designed against stable interfaces rather than internals.

**Scope discipline:** Sources are Anthropic first-party documentation (`code.claude.com/docs`) plus behavior observed by running `claude --help` / `claude auth status` locally. No deobfuscated-source analysis, internal codenames, or reimplementation material is used or cited.

**Version anchor:** Claude Code `2.1.220`, observed locally 2026-07-25. Flags and behaviors below carry version gates in the docs; the CLI is a moving target and every claim should be re-verified against the version pinned on the worker host.

---

## §1 Invocation surface

**Headless entry point.** `claude -p "<prompt>"` (alias `--print`) runs non-interactively and exits. All CLI options work with `-p`. ([headless](https://code.claude.com/docs/en/headless), [cli-reference](https://code.claude.com/docs/en/cli-reference))

**Input methods.** Prompt as trailing positional argument; or piped stdin (`cat file | claude -p "query"`); or both. Piped stdin is capped at **10 MB** as of v2.1.128 — exceeding it exits non-zero with an error. If neither is supplied, the CLI errors: `Input must be provided either through stdin or as a prompt argument when using --print`. `--input-format stream-json` accepts newline-delimited JSON messages for realtime input. ([headless](https://code.claude.com/docs/en/headless), [errors](https://code.claude.com/docs/en/errors))

**Output formats** (`--output-format`, print mode only):

| Value | Shape |
|---|---|
| `text` (default) | Plain final response on stdout |
| `json` | Single JSON object: `result`, `session_id`, usage, `total_cost_usd`, per-model cost breakdown |
| `stream-json` | Newline-delimited JSON events; last line is a `result` message |

`--json-schema '<JSON Schema>'` with `--output-format json` adds a validated `structured_output` field. Invalid schema → `Error: --json-schema is not a valid JSON Schema` and non-zero exit (v2.1.205+). `format` is accepted but treated as an annotation, not enforced. ([headless](https://code.claude.com/docs/en/headless))

**Flags most relevant to a wrapper:**

| Flag | Effect |
|---|---|
| `--model`, `--fallback-model a,b` | Model override; ordered fallback on overload (print mode) |
| `--permission-mode` | `default`, `manual`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions` |
| `--allowedTools` / `--disallowedTools` | Permission rules, e.g. `"Bash(git diff *)"`. A bare name in `--disallowedTools` removes the tool from context; a scoped rule only denies matching calls |
| `--tools "Bash,Edit,Read"` | Restricts the built-in tool set (`""` = none). Does not affect MCP tools |
| `--add-dir` | Grants file access to extra dirs. **Does not** load most `.claude/` config from them — `.claude/skills/` and `.claude/agents/` are documented exceptions |
| `--settings <file-or-json>` | Overrides matching keys for the session; file must be ≤2 MiB |
| `--setting-sources user,project,local` | Restricts which settings scopes load |
| `--mcp-config` / `--strict-mcp-config` | Load MCP servers from explicit config; ignore all others |
| `--bare` | Skips discovery of hooks, skills, plugins, MCP, auto-memory, CLAUDE.md, **and OAuth/keychain reads**. Documented as "recommended for scripted and SDK calls" |
| `--safe-mode` | Disables all customizations, keeps auth/model/tools/permissions |
| `--max-turns N` / `--max-budget-usd X` | Turn cap (errors at limit) and hard spend cap; print mode only |
| `--session-id <uuid>` | Caller-specified session ID |
| `--no-session-persistence` | Not written to disk, not resumable (print mode) |
| `--worktree <name>` / `-w` | Creates a git worktree under `.claude/worktrees/<name>` and runs there |

**Working-directory semantics.** The project root is the process cwd at launch, and sessions are stored per project directory. `CLAUDE_PROJECT_DIR` is the stable project root and does not change when directories are added mid-session; `--add-dir` widens file access without moving the root. Background Bash tasks are killed ~5 s after the final result, while background subagents are waited on with a 10-minute default cap (`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`). ([mcp](https://code.claude.com/docs/en/mcp), [headless](https://code.claude.com/docs/en/headless))

---

## §2 Session and state management

**On-disk location.** Transcripts are JSONL at `~/.claude/projects/<project>/<session-id>.jsonl`, where `<project>` is the working-directory path with non-alphanumerics replaced by `-`. Docs state explicitly: *"The entry format is internal to Claude Code and changes between versions, so scripts that parse these files directly can break on any release."* Relocatable via `CLAUDE_CONFIG_DIR`. Retention: `cleanupPeriodDays`, default 30. ([sessions](https://code.claude.com/docs/en/sessions))

**Resumption.** `--continue` resumes the most recent session in cwd; `--resume <id|name>` resumes a specific one. Sessions created with `-p` do **not** appear in the picker but are resumable by ID. **Session-ID lookup is scoped to the current project directory and its git worktrees** — resuming from a different directory yields `No conversation found with session ID: <id>`. ([sessions](https://code.claude.com/docs/en/sessions))

Restored: conversation history including tool calls and results, model, agent, permission mode (except `plan` and `bypassPermissions`, never restored), active goal, unexpired scheduled tasks. **Not** restored: `--mcp-config`, `--settings`, `--plugin-dir`, `--fallback-model`, `--add-dir` directories, background Bash/monitor tasks. Settings files are re-read at launch. ([sessions](https://code.claude.com/docs/en/sessions))

**Session ID.** Supplied by the caller via `--session-id <uuid>`, or read back from the `session_id` field of the `json` / `stream-json` result. `--fork-session` mints a new ID from an existing transcript.

**Survival of a killed process.** Docs state sessions are "saved continuously to local transcript files as you work," implying partial transcripts persist. Whether a session interrupted mid-tool-call resumes cleanly is **not documented** — see §8 test plan. `Failed to resume the conversation` is a documented failure that exits code 1 and is described as possibly transient. Concurrent resume of one session is documented as interleaving "messages from both into one transcript."

**Compaction.** On by default (`autoCompactEnabled`; `DISABLE_AUTO_COMPACT=1` to disable). Older tool outputs are cleared first, then the conversation is summarized. Tunables: `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (token capacity) and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (1–100); **the default trigger percentage is not documented.** Compaction is observable via `PreCompact`/`PostCompact` hooks and the `SessionStart` matcher `compact`; whether a discrete compaction event appears in `stream-json` is **not documented**. Repeated thrashing produces an error rather than an infinite loop. ([how-claude-code-works](https://code.claude.com/docs/en/how-claude-code-works), [env-vars](https://code.claude.com/docs/en/env-vars), [hooks](https://code.claude.com/docs/en/hooks))

**In-flight tool calls on termination.** On SIGTERM, Claude Code "aborts the in-progress turn, terminates the process tree of any running Bash command, runs `SessionEnd` hooks, and exits with code 143." Whether the aborted tool call is recorded in the transcript is **not documented**.

---

## §3 Authentication mechanics

**Precedence order** (first match wins) ([iam](https://code.claude.com/docs/en/iam)):

1. Cloud provider (`CLAUDE_CODE_USE_BEDROCK` / `_VERTEX` / `_FOUNDRY`)
2. `ANTHROPIC_AUTH_TOKEN` → `Authorization: Bearer`
3. `ANTHROPIC_API_KEY` → `X-Api-Key`. **In `-p` mode the key is always used when present** (no interactive approval gate)
4. `apiKeyHelper` script output
5. `CLAUDE_CODE_OAUTH_TOKEN`
6. Subscription OAuth from `/login`

A signed-in Claude apps gateway session sits outside this list and outranks all of it.

**`claude setup-token`.** Opens the browser authorization flow and **prints a one-year OAuth token to the terminal; it is not saved anywhere.** Set it as `CLAUDE_CODE_OAUTH_TOKEN`. Requires a Pro/Max/Team/Enterprise plan and can only make model requests — no Remote Control, no claude.ai connectors. **`--bare` does not read `CLAUDE_CODE_OAUTH_TOKEN`**; bare-mode scripts must use `ANTHROPIC_API_KEY` or `apiKeyHelper` via `--settings`. ([iam](https://code.claude.com/docs/en/iam))

**Credential storage.** macOS Keychain; Linux `~/.claude/.credentials.json` mode `0600` (confirmed locally); Windows `%USERPROFILE%\.claude\.credentials.json`. Relocated by `CLAUDE_CONFIG_DIR` on Linux/Windows. `apiKeyHelper` is re-invoked after 5 minutes or on HTTP 401 (`CLAUDE_CODE_API_KEY_HELPER_TTL_MS` to override); failure/timeout/empty output surfaces as `Your apiKeyHelper script is failing` within three attempts.

**Expiry.** Interactive: `Login expired · Please run /login`. Non-interactive equivalent: `Failed to authenticate: OAuth session expired and could not be refreshed`. A startup warning fires within 3 days of expiry (v2.1.203+). **Exit code on auth failure is not documented.** ([errors](https://code.claude.com/docs/en/errors))

**Service accounts.** Docs recommend `setup-token`/`CLAUDE_CODE_OAUTH_TOKEN` for "CI pipelines, scripts, or other environments where interactive browser login isn't available," and note that `forceLoginOrgUUID` blocks environment-credential sessions in managed orgs. There is **no documented guidance on running the CLI under a dedicated system service account**. Usefully, `claude auth status` emits JSON (`loggedIn`, `authMethod`, `apiProvider`, `orgId`, `subscriptionType`) and exits 0 — a cheap pre-flight probe for a worker.

---

## §4 Configuration surface

**Settings files and precedence** — managed > CLI args > local (`.claude/settings.local.json`) > project (`.claude/settings.json`) > user (`~/.claude/settings.json`). Permission rules **merge** across scopes rather than override. Managed settings live at `/etc/claude-code/managed-settings.json` (Linux), `/Library/Application Support/ClaudeCode/` (macOS), `C:\Program Files\ClaudeCode\` (Windows). Note: in `-p` mode, **settings files that fail validation are silently ignored** with no error surfaced (observed in `claude --help`). ([settings](https://code.claude.com/docs/en/settings))

**MCP scopes** ([mcp](https://code.claude.com/docs/en/mcp)):

| Scope | Stored in | Loads in |
|---|---|---|
| Local (default) | `~/.claude.json`, keyed by project path | That project only |
| Project | `.mcp.json` at repo root | That project, shared via VCS |
| User | `~/.claude.json` | All projects |

Precedence: local > project > user > plugin > claude.ai connectors. Project `.mcp.json` servers require **approval** (`enableAllProjectMcpServers`, `enabledMcpjsonServers`), and approvals from committed settings are ignored in an untrusted workspace — a real hazard for a worker that clones repos. Transports: `stdio`, `sse`, `http`/`streamable-http`, `ws`. `MCP_TIMEOUT` governs startup (30 s default). Tool naming: `mcp__<server>__<tool>`, or `mcp__plugin_<plugin>_<server>__<tool>` when plugin-bundled.

**Hooks.** ~25 events spanning session lifecycle, per-turn, tool-use loop, subagent/team, environment, compaction, and MCP. Contract: JSON on stdin including `session_id`, `transcript_path`, `cwd`, `permission_mode`, `hook_event_name`. Exit 0 → stdout parsed as JSON decisions; **exit 2 → blocking error** on blockable events (PreToolUse, UserPromptSubmit, Stop, PreCompact, PostToolBatch, …); any other code → non-blocking, stderr shown. JSON output can set `continue: false`, inject `additionalContext`, rewrite tool input via `updatedInput`, or return a `permissionDecision`. Handler types: `command`, `http`, `mcp_tool`, `prompt`, `agent`. Configured in any settings scope, plugin `hooks/hooks.json`, or skill/agent frontmatter; kill switch `disableAllHooks`. ([hooks](https://code.claude.com/docs/en/hooks))

**Skills** — `~/.claude/skills/<name>/SKILL.md` (personal), `.claude/skills/<name>/SKILL.md` (project; discovered by walking up to repo root plus on-demand in nested dirs), `<plugin>/skills/`. Conflict order: enterprise > personal > project, and any level overrides a bundled skill; plugin skills are namespaced `plugin-name:skill-name`. Invoked as `/skill-name`, which works in `-p` mode. Live-reloaded on file change. ([skills](https://code.claude.com/docs/en/skills))

**Subagents** — `.claude/agents/` (project) and `~/.claude/agents/` (user), scanned recursively; managed-settings `.claude/agents/` outranks both. Identity comes only from the `name` frontmatter field, and duplicate names in one directory resolve by **filesystem read order — explicitly not a documented precedence**. Invoked via `--agent <name>` or inline `--agents '<json>'`. ([sub-agents](https://code.claude.com/docs/en/sub-agents))

**Plugins** — marketplace plugins are **copied** into `~/.claude/plugins/cache`, with per-plugin data at `~/.claude/plugins/data/<id>/`. Install scopes user / project / local; session-only sideload via `--plugin-dir` / `--plugin-url` (blockable with `disableSideloadFlags`). Plugins contribute skills, agents, hooks, MCP servers, LSP servers, and monitors. ([plugins-reference](https://code.claude.com/docs/en/plugins-reference))

**Machine- vs project-scoped — the split that matters for a multi-project worker:**

| Machine-scoped | Project-scoped |
|---|---|
| `~/.claude/settings.json`, `~/.claude/CLAUDE.md`, `~/.claude/skills/`, `~/.claude/agents/`, `~/.claude/memory/` | `.claude/settings.json`, `.claude/settings.local.json`, `CLAUDE.md`, `.claude/skills/`, `.claude/agents/`, `.mcp.json` |
| `~/.claude.json` (OAuth session, MCP servers, per-project state, caches) | — |
| `~/.claude/.credentials.json`, `~/.claude/projects/`, `~/.claude/plugins/` | — |

`--bare`, `--safe-mode`, and `--setting-sources` are the documented levers for suppressing machine-scoped config leakage into a worker-run activity.

---

## §5 Failure and error surfaces

**Exit codes.** There is **no first-party exit-code table.** Documented and observed values:

| Code | Meaning | Source |
|---|---|---|
| 0 | Success | Observed (`claude auth status`) |
| 1 | Unknown option; `Failed to resume the conversation`; worktree entry failure | Observed locally + [errors](https://code.claude.com/docs/en/errors), [worktrees](https://code.claude.com/docs/en/worktrees) |
| 137 | Installation killed before finishing (OOM/kill) | [errors](https://code.claude.com/docs/en/errors) |
| 143 | SIGTERM during `-p` run, after abort + `SessionEnd` hooks | [headless](https://code.claude.com/docs/en/headless) |

Codes for auth failure, rate limit exhaustion, `--max-turns` exceeded, and `--max-budget-usd` exceeded are **not documented**.

**Built-in retry.** Claude Code already retries transient failures (5xx, 529 overload, timeouts, 429, dropped connections) up to **10 times** with exponential backoff. `CLAUDE_CODE_MAX_RETRIES` (capped at 15 as of v2.1.186); `CLAUDE_CODE_RETRY_WATCHDOG=1` retries 429/529 **indefinitely** — explicitly intended for unattended CI/automation. Explicitly **not** retried: TLS validation failures, server errors after visible output has streamed, Bedrock content-type mismatches. ([errors](https://code.claude.com/docs/en/errors))

**Retry observability in-stream.** `system/api_retry` events carry `attempt`, `max_retries`, `retry_delay_ms`, `error_status` (HTTP code or null), and a categorical `error` field with values: `authentication_failed`, `oauth_org_not_allowed`, `billing_error`, `rate_limit`, `overloaded`, `invalid_request`, `model_not_found`, `server_error`, `max_output_tokens`, `unknown`. **This enum is the single most useful classification primitive available to a wrapper.** ([headless](https://code.claude.com/docs/en/headless))

**Rate limiting.** Surfaces as human-readable strings — `You've hit your session limit · resets 3:45pm`, `You've hit your weekly limit · resets Mon 12:00am`, `Request rejected (429)`, `Server is temporarily limiting requests (not your usage limit)`. Reset times appear **inside the message text**; there is **no documented structured retry-after field**. Session and weekly windows are shared across models, so switching models does not restore access.

**Timeouts.** `API_TIMEOUT_MS` (600000 default), `API_FORCE_IDLE_TIMEOUT` (5-min streaming idle), `BASH_DEFAULT_TIMEOUT_MS` (120000), `BASH_MAX_TIMEOUT_MS` (600000), `MCP_TIMEOUT`, `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` (600000). **There is no documented wall-clock timeout on an entire `-p` invocation** — only `--max-turns` and `--max-budget-usd` bound total work.

**Signals and streams.** SIGTERM is fully documented (abort turn → kill Bash process tree → run `SessionEnd` hooks → exit 143). **SIGINT behavior in `-p` mode is not documented**, nor is SIGKILL cleanup. Docs state that in `-p` mode errors appear on **stdout with structured error codes** while warnings go to stderr; the `result` message carries `is_error`. Slow-consumer output drain on exit is capped at 30 s (v2.1.214+).

---

## §6 Concurrency and resource behavior

**Multiple processes.** Supported and documented as a normal pattern: "Run the command again with a different name in another terminal to start a second isolated session." Git worktrees are the documented isolation mechanism for **file edits**. Subagent worktrees are `git worktree lock`ed while running, and a periodic sweep releases locks left by exited processes (v2.1.210+). ([worktrees](https://code.claude.com/docs/en/worktrees))

**Shared state hazards** — documented as shared across concurrent sessions on one machine: `~/.claude.json` (OAuth session, MCP servers, per-project state, caches); `~/.claude/.credentials.json`; `~/.claude/projects/<project>/` transcript storage; and, for worktrees of the same repo, `.git`, project-scope plugins, and **permission approvals written back to the main checkout's `.claude/settings.local.json`** (v2.1.211+).

**Whether concurrent writes to `~/.claude.json`, `.credentials.json`, or `settings.local.json` are atomic or lock-protected is not documented.** This is the single largest unknown for a multi-worker design.

Documented parallel-invocation guidance is limited to worktrees, subagents, agent teams, and background sessions; there is **no documented per-machine process limit**. **Resource footprint is not documented** — cost guidance exists (≈$13/developer/active-day enterprise average) and per-team-size rate-limit sizing (1–5 users → 200k–300k TPM/user), but no CPU/RSS/file-descriptor figures. ([costs](https://code.claude.com/docs/en/costs))

---

## §7 Observability

**`stream-json` event inventory.** Message types: `system` (subtypes `init`, `api_retry`, `plugin_install`), `assistant`, `user`, `result`, `stream_event` (partial deltas), `task_progress`, `hook_started`/`hook_progress`/`hook_response`, `prompt_suggestion`. Subagent messages carry `parent_tool_use_id`; main-conversation messages carry `null`. By default only subagent `tool_use`/`tool_result` blocks are emitted — `--forward-subagent-text` (v2.1.211+) adds subagent text and thinking; `--include-hook-events` adds the hook lifecycle; `--include-partial-messages` adds token deltas. ([headless](https://code.claude.com/docs/en/headless), [agent-sdk/typescript](https://code.claude.com/docs/en/agent-sdk/typescript))

**Result message fields** (SDK type definitions): `type`, `subtype` (`"turn" | "session"`), `is_error`, `duration_ms`, `duration_api_ms`, `num_turns`, `result`, `session_id`, `total_cost_usd`, `usage.{input_tokens, output_tokens}`, `permission_denials[]` (`tool_name`, `reason`), `modelUsage[]` (per-model input/output/cache-creation/cache-read tokens). **`system/init`** reports model, tools, MCP servers, `plugins[]`, `plugin_errors[]`, and a `capabilities[]` array (v2.1.205+) — docs explicitly recommend feature-detecting on `capabilities` **rather than comparing version strings**.

**OpenTelemetry.** First-class, enabled by `CLAUDE_CODE_ENABLE_TELEMETRY=1` plus standard OTEL exporter vars. Metrics include `claude_code.cost.usage` (USD), `.token.usage` (attribute `type`: input/output/cacheRead/cacheCreation), `.session.count`, `.lines_of_code.count`, `.commit.count`, `.active_time.total`. Events include `api_request` (`cost_usd`, token counts, `duration_ms`, `request_id`), `api_error` (`status_code`, `attempt`), `tool_decision`, `tool_result` (`success`, `duration_ms`, `error_type`), `auth`, `mcp_server_connection`. Correlation keys: `session.id`, `prompt.id`, `message.uuid`, `client_request_id`, `tool_use_id`. Traces behind `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`. ([monitoring-usage](https://code.claude.com/docs/en/monitoring-usage))

**Transcript retrieval.** Four documented programmatic paths: `-p --output-format json|stream-json`; `claude -p --resume <id> --output-format json "summarize…"`; the `transcript_path` handed to hooks and statusline commands (a `SessionEnd` hook can archive it); and the Agent SDK. Direct JSONL parsing is documented as unsupported and version-fragile.

**Cost accounting.** `total_cost_usd` and `modelUsage[]` per run; `claude_code.cost.usage` via OTel; Analytics APIs for org-level per-user reporting. Local cost figures are computed from token counts at **list rates** and "may differ from your actual bill." Rate-limit budget headroom is **not exposed programmatically** — `/usage` is interactive-only. ([costs](https://code.claude.com/docs/en/costs))

---

## §8 Integration implications

### Recommended activity shape

**Input:** `{ prompt | prompt_file, cwd, session_id (caller-generated UUID), model, permission_mode, allowed_tools[], settings_json, mcp_config, max_turns, max_budget_usd, env_overrides }`.

**Invocation:** `claude -p --output-format stream-json --verbose --include-partial-messages --session-id <uuid> --max-turns N --max-budget-usd X …`, cwd set to a per-workflow git worktree. Use `--bare` (or at minimum `--setting-sources` + `--strict-mcp-config`) so a run is reproducible independent of whatever is in `~/.claude` on that host — with the caveat that `--bare` forbids `CLAUDE_CODE_OAUTH_TOKEN`, forcing `ANTHROPIC_API_KEY`/`apiKeyHelper`.

**Output:** the parsed `result` message plus a captured event log.

**Timeouts:** set the Temporal `start_to_close_timeout` above the model's own ceiling — `API_TIMEOUT_MS` (10 min) × expected turns plus the background-agent wait ceiling (10 min). Emit Temporal heartbeats on every `stream-json` line; heartbeat details should carry the last `session_id` and turn count so a retry can decide whether to resume.

**Retry policy:** set Temporal `maximum_attempts` low (2–3). Claude Code already performs up to 10 internal backoff retries; layering aggressive Temporal retries on top multiplies spend. Prefer letting the CLI absorb transient failures, and consider `CLAUDE_CODE_RETRY_WATCHDOG=1` for long unattended runs.

### Failure classification

| Class | Detection | Disposition |
|---|---|---|
| Retryable | `system/api_retry` with `error` ∈ {`rate_limit`, `overloaded`, `server_error`}; exit 143 (SIGTERM); `Request timed out`; connection errors | Retry, ideally with `--resume` |
| Terminal — auth | `error: authentication_failed` / `oauth_org_not_allowed`; `Failed to authenticate: OAuth session expired…`; `Invalid API key` | Fail fast, alert operator; retrying cannot succeed |
| Terminal — config | Exit 1 on unknown option; `--json-schema is not a valid JSON Schema`; `Settings file exceeds the 2MiB limit` | Non-retryable |
| Terminal — policy | `error: invalid_request`, `model_not_found`, `billing_error`; usage-policy refusal | Non-retryable |
| Ambiguous | Budget cap hit; `--max-turns` exceeded; `Prompt is too long` | Treat as terminal-for-this-attempt; requeue as new work with adjusted parameters |

Classify on the `system/api_retry` `error` enum and `result.is_error` first, and treat exit codes as a **secondary** signal until the test plan below establishes their meanings on the pinned version.

### Artifacts to persist

Per activity: full `stream-json` event log; the `result` object (`total_cost_usd`, `modelUsage[]`, `num_turns`, `duration_ms`, `duration_api_ms`, `permission_denials[]`); `system/init` (`capabilities`, `plugins`, `plugin_errors`); `session_id`; the `claude --version` string; and the resolved worktree path + final git SHA. Do **not** persist raw transcript JSONL as a parsed structure — copy it opaquely if at all, since its schema is explicitly unstable. Prefer an OTel collector on the worker host for cross-run cost/latency aggregation.

### Idempotency hazards

Claude Code invocations are **not idempotent**: an activity retry re-runs an agent that writes files, runs commands, and may push commits. Mitigations, in order of strength:

1. **Worktree-per-attempt.** Give each attempt a fresh `--worktree`, so a retry starts from a clean base rather than on top of a half-finished edit. Note `-p` runs do **not** clean up their worktrees — the wrapper owns `git worktree remove`.
2. **Caller-supplied `--session-id`.** Makes the attempt addressable and lets a retry choose resume-vs-restart deliberately.
3. **Deny mutating tools by default.** `--disallowedTools` / `--tools` to prevent network and push operations unless a specific activity requires them.
4. **Deterministic config.** `--bare` or `--setting-sources` + `--strict-mcp-config`, so a retry on a different worker sees identical configuration.

### Edge vs orchestrator state split

**Must stay at the edge:** credentials (`~/.claude/.credentials.json`, keychain), the git worktree and working files, transcript JSONL, MCP stdio server processes, plugin cache. **Safe to return to the orchestrator:** `session_id`, `result` text / `structured_output`, cost and token totals, `num_turns`, permission denials, error classification, git SHA, worktree path (as a locality hint). Because session resumption is **directory-scoped**, a resumed activity must be pinned to the same worker host and directory — model this as a Temporal task-queue affinity constraint, not as portable state.

### Open questions — local test plan

These cannot be answered from documentation and must be measured against the pinned version:

1. **Exit-code map.** Run `-p` under each of: valid auth, unset/invalid `ANTHROPIC_API_KEY`, expired OAuth, `--max-turns 1` on a multi-turn task, `--max-budget-usd 0.001`, unknown flag, unreadable cwd. Record exit code, stdout, stderr for each.
2. **SIGINT semantics.** Send SIGINT (not SIGTERM) mid-turn; confirm whether `SessionEnd` hooks run, what exit code results, and whether the transcript is left resumable.
3. **Kill-mid-tool resumability.** SIGKILL during a long Bash tool call, then `--resume <id>`. Does the session resume? Is the orphaned `tool_use` block repaired, or does the API reject the malformed history?
4. **Concurrent `~/.claude.json` writes.** Launch N=20 simultaneous `-p` runs across different projects; check for corruption, lost MCP entries, or credential-file clobbering.
5. **Concurrent same-session resume.** Two `-p --resume <same-id>` processes at once — confirm interleaving behavior and whether either fails.
6. **Rate-limit surface in `stream-json`.** Drive a run into a session limit; capture the exact `api_retry` payload and whether the reset timestamp appears anywhere structured or only in prose.
7. **Compaction observability.** Force auto-compaction in a `-p` run and diff the `stream-json` output for any compaction marker; measure the default trigger percentage empirically against `/context` figures.
8. **`--bare` + `--worktree` interaction.** Confirm the trust-check bypass, worktree creation, and that no `~/.claude` config leaks in.
9. **Wall-clock unbounded runs.** Confirm there is genuinely no total-invocation timeout by running a long task with `--max-turns` high; this determines whether the wrapper must impose its own kill timer.
10. **Stdout-vs-stderr split.** Verify empirically where each error class lands in `-p` mode; the docs' claim that errors go to stdout conflicts with the observed `error: unknown option` on stderr.
