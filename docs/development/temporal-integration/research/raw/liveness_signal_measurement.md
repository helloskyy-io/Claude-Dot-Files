# Measuring the three liveness legs against a live `claude -p` run

```
Topic:          How stalled (no output), looping (byte-identical output) and stranded
                (never claimed) are each MEASURED against a live headless `claude -p`
                process — what signals exist, what thresholds are defensible, and what
                a false positive costs on each leg.
Feeds:          Sprint milestone "Observable exit criteria" (docs/development/sprint.md:243),
                under "## Sprint: Autonomous Operation" — the line states "Includes the
                three-legged liveness predicate — stalled, looping and stranded detected
                separately" → docs/development/autonomous-operation/autonomous-operation.md,
                the detection design. CORRECTED 2026-08-19 — this paper was written for the
                "Sprint: Fleet Reliability" section, which dissolved when this pool moved to
                docs/development/temporal-integration/research/. It cited sprint.md:182, which
                today holds an unrelated milestone ("V1 parity suite"), and a
                fleet-reliability phase doc that will never be written. The predicate itself
                survives under the same name in Autonomous Operation, whose phase doc exists.
                The paper's content is unaffected — only the destination pointer was stale.
                Note this paper is shelved under the Temporal Integration pool and does not
                feed it; see synthesis.md § Housekeeping.
Last validated: 2026-08-07
Revalidate:     high — 3 weeks
Confidence:     DEFINITIVE — the fleet's own invocation and parsing (read from source);
                the observed stream-json event vocabulary, the 30-second `tool_progress`
                heartbeat cadence, and which tools that heartbeat covers (enumerated
                from 58 JSONL logs in this repo, as of 2026-08-07); **the `heartbeat`
                field, its 30-second cadence and its exclusion of the `Agent` tool, all
                first-party documented in the Agent SDK TypeScript reference and
                version-gated at Agent SDK v0.3.214** — note the provenance in §2.4: those
                characters were retrieved by raw `curl` during this paper's verification
                pass, NOT by this analyst's own tooling, which truncates that page;
                `tool_progress`, `task_progress` and `task_started` as version-gated SDK
                message types (TypeScript Agent SDK CHANGELOG, raw); `RateLimitEvent` and
                `TaskProgressMessage` as typed Python SDK classes; systemd WatchdogSec
                semantics; Kubernetes probe semantics; SQS visibility-timeout and DLQ
                semantics; GitHub Actions' lack of an idle timeout; the phi-accrual
                threshold trade-off.
                DIRECTIONAL — Temporal Schedule-To-Start framing; OpenClaw's
                byte-identical rule (raw doc, thresholds unstated); CircleCI's 10-minute
                default (first-party but support-article, not reference docs).
                DERIVED — every threshold proposal in §4, the false-positive asymmetry
                table in §5, and the dispatched-vs-claimed record design in §4.3.
                GAP (stated, with search method) — the CLI-level `headless.md` still
                documents no complete stream-json event-type reference, and
                `vcs_state_changed` and `code_change_published` were not found in any
                source consulted (§2.4). This gap is MUCH narrower than the first revision
                of this paper claimed: `tool_progress`, its `heartbeat` field,
                `rate_limit_event` and `thinking_tokens` are all documented, and the
                earlier "not documented" finding for them was a false negative produced by
                a fetch layer that silently truncated the reference page.
Critic:         PASS-WITH-FIXES, three rounds (r1→r2: withdrew the false "undocumented
                heartbeat" headline — the NOT-PRESENT finding behind it came from a fetch
                that silently truncated the TypeScript SDK reference; corrected the false
                "`rate_limit_event` has no class in types.py" against a re-fetched
                `types.py` that defines `RateLimitEvent`; re-enumerated the log corpus and
                split 125 `tool_progress` events into 121 heartbeats covering `Bash` and
                `TaskOutput` only versus 4 non-heartbeat `Agent` retry notices, removing
                subagent coverage from the §4.1 detector and promoting `task_progress`
                into the signal list; refreshed every live-corpus count to 58 files with
                an as-of date. r2→r3: fixed a BLOCKING version miscite — `task_progress`
                is changelogged at v0.2.51, not v0.2.47, re-confirmed per-entry after a
                bulk enumeration had misassociated the heading, and corrected in all six
                places it appeared; un-hedged the `heartbeat` field from CONTESTED to
                DEFINITIVE now that three independent non-summarizing retrievals settled
                it, quoting the reference's own 30-second-cadence and Agent-exclusion
                text under an explicit provenance note that the authoring tooling cannot
                reach that page; shrank the §2.4 gap from six event types to two
                (`vcs_state_changed`, `code_change_published`); marked §8 item 9 RESOLVED;
                corrected the claim that `python.md` truncates — that is this tool, not
                the document; tightened `[^types]`'s `thinking_tokens` wording to the
                no-class claim the argument actually rests on. Two critic findings were
                REJECTED after re-checking primary evidence and the rejections held —
                the 4-of-4 `subagent_retry` count (2 of 4) and the changelog's supposed
                v0.3.214 gate on `heartbeat`) — 2026-08-07
```

> **Altitude: COMPONENT.** The three-legged taxonomy is settled upstream (product-pool
> synthesis candidate 10 [^synth10], from `paperclip_assessment.md` §4.4 [^pc44],
> `openclaw_assessment.md` §4.7 [^oc47], `hermes_assessment.md` §5.2 [^hm52]). This paper
> does not re-derive it and does not argue it. It answers only *how each leg is measured*.
> Anything above that altitude is confined to §9 (Escalation).

> **Mixed volatility (Research Standard §3).** The header takes the highest tier present.
> **§2 and §4 are HIGH-volatility** — they describe the Claude Code output surface, which
> demonstrably changed inside this repo's own log history (§2.5). **§3, §5.1 and §6 are
> LOW-volatility** — systemd, Kubernetes, SQS and the 1996–2004 failure-detector
> literature have not moved and a refresh may skip re-verifying them.

---

## 1. Primer — what "measuring liveness" means here, and what it is not

A **liveness detector** answers "is this thing still working?" from outside the thing.
The classical result that shapes every design in this paper is that in an asynchronous
system it cannot answer that question correctly: as Hayashibara et al. put it, the
FLP impossibility "is based on the fact that, in such a system, a crashed process cannot
be distinguished from a very slow one." [^phi] Every practical detector therefore trades
**completeness** (eventually suspecting everything that really died — Chandra and Toueg's
Strong completeness: "There is a time after which every process that crashes is
permanently suspected by all correct processes" [^phi]) against **accuracy** (not
suspecting the healthy). The trade is not eliminable; it is only priced.

That pricing is the whole content of this paper, because the workload prices it unusually.
A `claude -p` dispatch in this fleet is **10–60 minutes of headless agent work**; one
observed `result` event in `.claude/logs/build-refine-20260806-223719.jsonl` reports
`"duration_ms":1433359` — 23.9 minutes for a single run.[^logbr] Killing a healthy run of
that length destroys real money and real uncommitted work. Killing a wedged one saves a
few dollars. **The asymmetry runs the opposite way on each of the three legs**, which is
why they must be detected — and *acted on* — separately.

**Three predicates, not one.** The upstream pool states the distinction: liveness ≠
progress ≠ permission-to-continue, and a single timeout conflates them.[^hm54]

| Leg | The failure | Process state | What a naive detector gets wrong |
|---|---|---|---|
| **Stalled** | emitting nothing | alive, or dead with a live parent | fires on every legitimately long tool call |
| **Looping** | emitting the *same* thing | alive, busy, burning budget | invisible to any heartbeat — the run looks maximally healthy |
| **Stranded** | never started | no process at all | indistinguishable from "started and quiet" unless dispatch was recorded |

**There is no supervisor today.** `run-claude.sh` invokes `claude` in a pipeline, waits,
and inspects the log *after* exit; a workflow script *is* the supervisor and it is
blocking.[^runclaude] Nothing in `scripts/workflows/` wraps the `claude` invocation in
`timeout` or installs a signal-based watchdog over it (searched: `LOG_FILE=`, `timeout `,
`SIGTERM`, `trap ` across `scripts/workflows/` — **the only matches on the `claude`
invocation path** are log-path assignments, `build.sh`/`build-minor.sh` temp-log cleanup
traps, and `wait-for-ci.sh`'s own `CI_TIMEOUT`; the two `timeout ` hits are a `wait-for-ci.sh`
progress `echo` and a prose comment in `plan_master_workflow.py`, neither of which wraps
anything).[^grep-timeout] Detection therefore has to be *added*, and this paper
describes what it would have to read.

---

## 2. The signal surface — what a supervisor can actually observe

### 2.1 How the fleet invokes and what it captures (definitive — read from source)

`run_claude` builds exactly this command and streams it to a per-run JSONL log, optionally
through a formatter:[^runclaude]

```
claude -p "$prompt" --model "$WORKFLOW_MODEL" --output-format stream-json --verbose \
       --max-turns "$MAX_TURNS" --dangerously-skip-permissions "${extra_args[@]}"
```

`--include-partial-messages` is **not** passed. Per Anthropic's headless documentation,
token-level deltas require it: *"Use `--output-format stream-json` with `--verbose` and
`--include-partial-messages` to receive tokens as they're generated."* [^headless] So the
fleet's stream is at **message granularity, not token granularity** — the finest-grained
liveness signal available is deliberately switched off today. That is a knob, not a wall.

What the fleet already parses (definitive — `format-stream.sh` and
`print_cycle_totals`):[^fmt][^runclaude]

- `type == "system"` with `subtype == "init"` → `model`, `session_id`
- `type == "assistant"` → `.message.content[]` blocks of type `text`, `tool_use`, `thinking`
- `type == "user"` → `.message.content[] | select(.type == "tool_result")`
- `type == "result"` → `subtype`, `num_turns`, `total_cost_usd`, `duration_ms`, `result`
- `type == "error"` → `.message // .error`
- Post-hoc: `grep -q '"subtype":"error_max_turns"'` on the whole log, and a
  `COMPLETION_PATTERN` regex over the final `result` text.

### 2.2 The documented event surface (definitive — first-party `.md`)

Anthropic's headless page documents these event shapes with field tables:[^headless]

- **`system` / `init`** — session metadata: `model`, `tools`, `mcp_servers`, `plugins`,
  `plugin_errors`, `mcp_server_errors`, `capabilities`. *"It is the first event in the
  stream unless startup events precede it."*
- **`system` / `api_retry`** — `attempt`, `max_retries`, `retry_delay_ms`, `error_status`,
  `error` (one of `authentication_failed`, `oauth_org_not_allowed`, `billing_error`,
  `rate_limit`, `overloaded`, `invalid_request`, `model_not_found`, `server_error`,
  `max_output_tokens`, `unknown`), `uuid`, `session_id`.
- **`system` / `plugin_install`** — `status` ∈ {`started`, `installed`, `failed`, `completed`}.
- **`stream_event`** — token deltas, gated on `--include-partial-messages`; the documented
  filter is `select(.type == "stream_event" and .event.delta.type? == "text_delta")`.
- **`result`** — *"The last line of the stream is a `result` message with the final
  response text, cost, and session metadata."*
- **`parent_tool_use_id`** on `assistant`/`user` messages identifies subagent output;
  *"Messages from the main conversation carry `null` in that field."*

Process-level facts, also documented:[^headless]

- *"Claude Code exits with code 0 on success and a non-zero code when the run fails, so
  your scripts can branch on the exit status."*
- On SIGTERM, *"Claude Code aborts the in-progress turn, terminates the process tree of any
  running Bash command, runs [`SessionEnd` hooks](/docs/en/hooks#sessionend), and exits
  with code 143."* — **the kill path is defined and cleans up.** This matters for §5.
- Background subagents: *"that wait is capped at ten minutes by default so a stuck
  background agent cannot hold the process open indefinitely"* (v2.1.182+), tunable via
  `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`. **Anthropic already ships one internal
  anti-stall bound**; it is not the one we need, but it is precedent.
- Slow consumers: Claude Code *"waits for the queued output to drain before exiting,
  scaling the wait with how much is still queued, capped at 30 seconds."*

The Python Agent SDK's typed message classes (raw `types.py`) expose, for `ResultMessage`:
`subtype`, `duration_ms`, `duration_api_ms`, `is_error`, `num_turns`, `session_id`,
`stop_reason`, `total_cost_usd`, `usage`, `result`, `structured_output`, `model_usage`,
`permission_denials`, `deferred_tool_use`, `errors`, `api_error_status`, `uuid`,
`terminal_reason`.[^types] **No message class in that file carries a wall-clock timestamp**
— a grep of every line containing `time` (case-insensitive) returns only session-store
`mtime`/`last_modified`/`created_at` fields and timeout settings.[^types] The typed SDK is
therefore a *lossy* view of the wire format (see §2.3).

### 2.3 The observed event surface — what our own logs actually contain (definitive, empirical)

Method: `.claude/logs/*.jsonl` in this repo was enumerated by glob (**58 files as of
2026-08-07**, counted from the enumerated list, not from a tool-reported total), then
pattern-matched with ripgrep.

> **Every count in this section is an AS-OF figure against a LIVE, GROWING directory.**
> The fleet writes a new log per dispatch, so file counts and per-type totals move between
> passes — this correction pass observed the corpus grow from 57 to 58 files, and two
> logs that had no `result` event when the paper was first written acquired one. Counts
> are reproducible only against the same as-of date; treat any of them as a snapshot, not
> a constant. Ratios and shapes (which tools carry a heartbeat, the cadence) are the
> durable findings; the absolute totals are not.

**Event types observed** in `research-20260806-204414.jsonl` — enumerated line by line, and
counted from the enumeration: **478 leading events** matching
`^{"type":"<name>"[,"subtype":"<name>"]`. *(The file is longer: its terminal `result` event
does not begin with `{"type":"result"` — field order differs from the April-2026 logs. Two
enumerations make this precise: anchored `^{"type":"result"` matches 24 files, all dated
2026-04; unanchored `"type":"result"` matches 54 files. **The result event's field order
changed between April and August 2026**[^result-enum] — a third independent piece of §2.5's
volatility evidence. The fleet is unaffected because `format-stream.sh` and `print_cycle_totals`
select on `.type` via `jq`, which is field-order independent.[^fmt][^runclaude])* The types
present are: `system` (subtypes `init`, `thinking_tokens`, `task_started`,
`task_progress`, `task_updated`, `task_notification`, `background_tasks_changed`,
`vcs_state_changed`, `code_change_published`), `rate_limit_event`, `assistant`, `user`,
`tool_progress`.[^log204414]

**Finding A — the stream carries a real, periodic heartbeat, and it covers two of the
three tool shapes it appears under.** `tool_progress` events appear with
`"heartbeat":true`, a synthetic `tool_use_id` of the form `<parent-tool-id>-heartbeat-<N>`,
and a monotonically increasing `elapsed_time_seconds`. Enumerating every such event in
`research-refresh-20260805-111000.jsonl` gives the cadence directly:[^logrr]

```
30, 30, 60, 90, 30, 60, 90, 120, 150, 180, 210, 240, 30, 60, 90, 120, 150, 180, 210
```

**A 30-second cadence, restarting per tool call.** *(Sampling caveat: this file holds all
19 `Bash` heartbeats in the corpus and no others,[^tp-enum] so the sequence above is
evidence of the `Bash` cadence specifically. The 102 `TaskOutput` heartbeats were
enumerated but their inter-arrival sequence was not — §8 item 1 covers it.)*

**`tool_progress` occurrences are NOT all heartbeats, and the difference is
load-bearing.** Enumerating across the whole corpus and differencing the enumerations
(as of 2026-08-07):[^tp-enum]

| Enumeration | Occurrences | Files | `tool_name` |
|---|---|---|---|
| `"type":"tool_progress"` | 125 | 6 | `TaskOutput`, `Bash`, `Agent` |
| …of which `"heartbeat":true` | **121** | **5** | `TaskOutput` (102), `Bash` (19) |
| …of which **no** `heartbeat` field | **4** | 2 | `Agent` (4) |

The four `Agent` events are a **structurally different message**, not a missed heartbeat:
each carries `"elapsed_time_seconds":0` (not a rising clock), no `heartbeat` key, and a
`subagent_type`; two of the four additionally carry a `subagent_retry` object with
`attempt` / `max_retries` / `retry_delay_ms`.[^tp-enum] The TypeScript Agent SDK CHANGELOG
names exactly this shape at **v0.3.214**: *"Added optional `subagent_type` and
`subagent_retry` fields to `tool_progress` messages so clients can show a subagent waiting
out an API rate-limit retry"*.[^tschangelog] These are one-shot retry notices, emitted
when a subagent stalls on a rate limit — the opposite of a periodic liveness tick.

***Correction to a claim carried by the previous revision of this paper.*** That revision
read "125 occurrences carrying three `tool_name` values" as "the heartbeat covers three
`tool_name` values", and concluded the heartbeat covered *both* long-quiet cases — a long
`Bash` command and a subagent `Task`. **It does not.** The heartbeat covers `Bash` and
`TaskOutput` only. **A quiet subagent produces no `tool_progress` heartbeat at all**, so a
heartbeat-anchored detector is blind on exactly the leg §4.1 most needs covered. What
covers the subagent case instead is a *different* event — see Finding D.

**Finding B — only two event types carry a wall-clock timestamp.** In
`research-20260806-204414.jsonl`, matching `"timestamp":` returns lines 3, 4, 5, 6, 7, 10,
11, 12, 13, 14, 17, 18 … ; cross-referencing against the type enumeration, those are
exactly the `assistant` and `user` events. Lines 1 (`system`/`init`), 2
(`rate_limit_event`), 8–9 and 15–16 (`system`/`thinking_tokens`) do **not**
match.[^log204414][^ts-grep] Matching the full remainder of a `tool_progress` heartbeat
line (`"heartbeat":true[^}]*`) shows it terminates at `session_id` then `uuid` — **no
timestamp**.[^logrr] Timestamps observed are ISO-8601 with milliseconds, e.g.
`"timestamp":"2026-08-07T00:44:22.822Z"`.

*Consequence (derived):* a supervisor cannot rely on in-band timestamps for
silence measurement, because the events most useful as heartbeats are exactly the ones
without them. **The supervisor must stamp arrival time itself** — which it can, since it
owns the pipe. In-band `timestamp` is a useful *cross-check* against clock skew and log
replay, not the primary clock.

**Finding C — `rate_limit_event` exposes quota state mid-run.** Observed shape:
`{"type":"rate_limit_event","rate_limit_info":{"status":"allowed","resetsAt":1786068000,`
`"rateLimitType":"five_hour","overageStatus":"allowed","overageResetsAt":1786063200,`
`"isUsingOverage":false …`[^log204414] This is out of scope here (it feeds topic 6,
per-credential quota headroom) but is recorded because a supervisor reading the stream
gets it for free. It is a **typed, first-party message**: `class RateLimitEvent` in the
Python SDK's `types.py`, docstring *"Rate limit event emitted when rate limit info
changes."*, fields `rate_limit_info` / `uuid` / `session_id`.[^types]

**Finding D — `task_progress` is the subagent-side progress signal, and it is both older
and better documented than the heartbeat.** `system`/`task_progress` events are the most
abundant progress signal in the corpus: **6,479 occurrences across 35 of the 58 files**,
including **17 of the 25 April-2026 logs** — so unlike the heartbeat (§2.5), this signal
is not new.[^taskprog-enum] Observed shape, from
`research-20260806-204414.jsonl`:[^taskprog-enum]

```
{"type":"system","subtype":"task_progress","task_id":"a899e4e7f350a1d5f",
 "tool_use_id":"toolu_018kkQTypRBWfx7BftoaUuJv","description":"Reading …",
 "subagent_type":"research-analyst",
 "usage":{"total_tokens":23795,"tool_uses":1,"duration_ms":2992},
 "last_tool_name":"Read","uuid":"…","session_id":"…"}
```

It is first-party documented at **v0.2.51**: *"Added `task_progress` events for real-time
background agent progress reporting with cumulative usage metrics, tool counts, and
duration"*[^tschangelog] — a description that matches the observed `usage.tool_uses` /
`usage.duration_ms` / `last_tool_name` fields exactly. It is typed in the Python SDK as
`class TaskProgressMessage(SystemMessage)`.[^types]

*Boundary, stated rather than assumed:* `task_progress` is **event-driven, not periodic**.
It fires per subagent tool use (`usage.tool_uses` increments by one each time), so it
reports that a subagent is *doing things*, not that it is *alive*. A subagent wedged
inside one long tool call, or thinking for minutes, emits nothing — the same blind spot a
heartbeat exists to close, and it is not closed for subagents by any signal observed here.
That is a real hole in the stalled leg, and §8 item 2 is where it gets tested. **This is
the signal §4.1's detector must add**, because the heartbeat structurally cannot cover
this case (Finding A).

### 2.4 What is and is not documented — a corrected finding

> **This section previously asserted the opposite of what it now says, and the reversal is
> itself the finding.** The prior revision reported `tool_progress`, `heartbeat`,
> `rate_limit_event` and `thinking_tokens` as **NOT PRESENT** in the Agent SDK TypeScript
> reference, and built a headline conclusion, a §6 "largest weakness", and a §9 portfolio
> risk on top of it. **That negative finding was invalid.** It came from asking a
> summarizing fetch layer to enumerate occurrences in a page far larger than its input
> budget; the layer silently truncated the page and answered from the prefix. Re-running
> the same fetch during this correction pass reproduces the false negative *and* returns an
> explicit
> `[Content truncated due to length...]` marker — so the absence was never measured. Per
> Research Standard §3, a negative finding is only as good as its search method; this one
> had none, and is **withdrawn** rather than restated. A full-text retrieval of the same
> page during verification found **all four** of those event types documented there. The
> section below states what is documented, what is not, and — because this analyst's own
> tooling still cannot read that page — exactly which retrieval produced which span.

**Search method (this pass).** The candidate page set was established by fetching
`code.claude.com/docs/llms.txt` and enumerating every documentation URL under
`agent-sdk/`, then fetching the ones that could plausibly carry stream-event
definitions.[^llmstxt] Sources read **whole** (the fetch returned the complete
document, verified by reading its closing lines): `headless.md`;[^headless] the Python
SDK's raw `types.py`, with every `^class ` line enumerated;[^types] the TypeScript Agent
SDK's raw `CHANGELOG.md`;[^tschangelog] `agent-sdk/agent-loop.md`;[^agentloop]
`agent-sdk/subagents.md`; `agent-sdk/streaming-output.md`. Sources **confirmed truncated**
and therefore usable only for positive matches, never for absence:
`agent-sdk/typescript.md` and `agent-sdk/python.md`.[^ts-ref] Also fetched: the npm
registry record for `@anthropic-ai/claude-agent-sdk` (`version: 0.3.224`,
`types: sdk.d.ts`) and the package file manifest — the shipped `sdk.d.ts` is **333,809
bytes**, which is why no fetch route available to this analyst can read the full type
union.[^npmpkg]

**Result — DOCUMENTED (definitive, first-party, versioned):**

| Signal | Where documented | Confidence |
|---|---|---|
| `tool_progress` (the message type) | TS SDK CHANGELOG **v0.3.214**: *"Added optional `subagent_type` and `subagent_retry` fields to `tool_progress` messages so clients can show a subagent waiting out an API rate-limit retry"*[^tschangelog] | definitive |
| `task_progress` | TS SDK CHANGELOG **v0.2.51**: *"Added `task_progress` events for real-time background agent progress reporting with cumulative usage metrics, tool counts, and duration"*;[^tschangelog] `class TaskProgressMessage(SystemMessage)` in `types.py`;[^types] and in `typescript.md`'s options table: *"forward them on [`task_progress`](#sdktaskprogressmessage) events via the `summary` field"*[^ts-ref] | definitive |
| `task_started` | TS SDK CHANGELOG **v0.2.45**: *"Added `task_started` system message to the SDK stream, emitted when subagent tasks are registered"*;[^tschangelog] `class TaskStartedMessage(SystemMessage)`[^types] | definitive |
| `rate_limit_event` | `class RateLimitEvent` in `types.py`, docstring *"Rate limit event emitted when rate limit info changes."*, fields `rate_limit_info` / `uuid` / `session_id`[^types] | definitive |
| `task_updated`, `task_notification` | `class TaskUpdatedMessage(SystemMessage)`, `class TaskNotificationMessage(SystemMessage)`[^types] | definitive |
| **`heartbeat`** (the field on `tool_progress`) | TS reference, `### SDKToolProgressMessage`: `heartbeat?: boolean`, plus prose giving the 30-second cadence, the `Agent`-tool exclusion, and the **v0.3.214** gate — quoted in full below[^ts-ref] | definitive |
| `thinking_tokens` | TS reference, `### SDKThinkingTokensMessage`[^ts-ref] | definitive |

Anthropic also states first-party that the stream carries more than the loop needs:
*"Both SDKs also yield observability events such as rate-limit status and task
notifications that are not required to drive the loop"*, directing readers to the
per-language message-type references for the complete lists.[^agentloop]

**Result — the `heartbeat` field: DOCUMENTED (definitive). Settled, and settled against
this paper's two earlier revisions.** The Agent SDK TypeScript reference carries a
`### SDKToolProgressMessage` section defining `heartbeat?: boolean` on the
`SDKToolProgressMessage` type, and states the behaviour in prose:[^ts-ref]

> *"While a tool call runs in the main conversation, Claude Code emits a `tool_progress`
> message every 30 seconds with `heartbeat: true`. Each heartbeat carries the tool name and
> elapsed seconds, so you can distinguish a long-running call from a stalled session.
> Claude Code doesn't emit heartbeats for the Agent tool, whose subagents stream their own
> progress, or for tool calls inside a subagent. The `heartbeat` field requires Agent SDK
> v0.3.214 or later."*

and, for the `Agent`-tool variant §2.3 Finding A measured:[^ts-ref]

> *"On `tool_progress` messages for the Agent tool, `subagent_type` names the running
> subagent type, such as `general-purpose`. `subagent_retry` is present while that subagent
> waits out an API error backoff, such as a rate limit or overload, with one message per
> retry attempt. Both fields require Agent SDK v0.3.214 or later."*

The same document carries `### SDKThinkingTokensMessage` and `### SDKRateLimitEvent`
sections, so those two are documented as well.[^ts-ref]

**Read what this does to §2.3.** Every empirical finding in Finding A is confirmed by the
documentation, and vice versa: the 30-second cadence, the `heartbeat: true` marker, the
elapsed-seconds field, and — the one that changes the §4.1 design — **the explicit
exclusion of the `Agent` tool**. The paper derived that exclusion from 4 log events before
this text was available; the vendor states it as intended behaviour. It is not a sampling
artifact. The reference goes one step further than the logs could: heartbeats are also
absent *"for tool calls inside a subagent"*, which the corpus had no way to show.

> **PROVENANCE — stated rather than laundered, because it matters for reproducibility.**
> The characters quoted above were **not** retrieved by this analyst. This paper's authoring
> tooling has no shell, and its fetch layer returns `[Content truncated due to length...]`
> on this URL — the truncation is reproducible and is the defect that produced the original
> false negative. The spans were obtained by **raw, non-summarizing `curl` during this
> paper's verification pass, reproduced independently three times**, against a document
> measuring **4,830 lines / 263,071 bytes with no truncation**, with the quoted text at
> lines 4,393–4,417.[^ts-ref][^critic-report] Under Research Standard §3 that is a
> traceable method and a
> legitimate verbatim source — the exact characters were returned by a non-summarizing
> retrieval — but a reader reproducing this paper must know that `curl`, not the research
> agent's fetch tool, is what reaches line 4,388.

*(Two earlier revisions got this wrong in opposite directions: revision 1 asserted the
field was undocumented, on a truncated fetch; revision 2 correctly refused to assert the
quotes it could not retrieve, but consequently under-claimed a fact that was already
settled. The first was a fabrication risk, the second a calibration error. Only the first
is dangerous to a downstream consumer, but both are wrong.)*

**Result — GAP (stated, with method):** only **`vcs_state_changed`** and
**`code_change_published`** remain. Neither was found in any source consulted — not
`headless.md`, not `types.py` (no class), not the SDK CHANGELOG, and not in the TypeScript
reference under the verification pass's full-text
retrieval.[^types][^headless][^tschangelog][^ts-ref] These two are the paper's only
surviving undocumented event types, and neither is load-bearing for any leg of the liveness
predicate. **The gap this section originally reported has shrunk from six event types to
two**, and the two that remain are the ones nothing depends on.

**The CLI-level gap survives intact.** Nothing above is in `headless.md` — the page the
fleet's own `claude -p --output-format stream-json` invocation is documented by. Read
whole this pass, it contains no occurrence of `tool_progress`, `heartbeat`,
`task_progress`, `rate_limit_event`, `thinking_tokens`, `vcs_state_changed` or
`code_change_published`.[^headless] Anthropic's own issue tracker names this exact gap:
`anthropics/claude-code` issue **#24596**, titled *"[DOCS] CLI `--output-format
stream-json` lacks event type reference"*, created **2026-02-10**, labelled `documentation`
and `stale`, 2 comments, **closed**.[^issue24596] *(The issue body was returned only as a
summarizing paraphrase and is therefore not quoted; only the structured JSON fields are
cited.)* A CLI consumer following the documented surface would not learn these events
exist; they are documented in the **SDK** reference and changelog, one layer up.

**What this means for the phase doc, restated:** the heartbeat is a **versioned SDK
feature with a changelog**, not an undocumented implementation detail. That is a *stronger*
foundation than the previous revision claimed, and it changes the mitigation posture: the
risk is now ordinary dependency risk on a documented, version-gated surface (watchable by
diffing the SDK CHANGELOG per release), not the unbounded "could vanish silently" risk
§6(c) previously asserted. The schema in §2.3 is still what we *observed* — but it is no
longer unpromised.

### 2.5 The surface moves — evidence of volatility (definitive)

Three independent signals justify the HIGH tier:

0. **The `result` event's field order changed** between the April-2026 and August-2026 logs
   in this repo (§2.3). Harmless to us — the fleet selects on `.type` via `jq` — but it is
   direct evidence that the wire format is edited without ceremony.[^result-enum]

1. **Our own logs changed shape.** All **121** `tool_progress` heartbeats occur in **5**
   logs dated 2026-08-03 through 2026-08-06; the 25 logs from 2026-04 contain none.[^tp-enum]
   A signal that did not exist four months ago is newer than the code that would depend on
   it. *(Tempered by §2.4: it is a **documented** new signal, and the SDK CHANGELOG dates
   its neighbours — `task_progress` at v0.2.51, the `tool_progress` subagent fields at
   v0.3.214.[^tschangelog] Volatility here means "actively developed", not "unannounced".
   Note the contrast with `task_progress`, which is present in 17 of the 25 April logs and
   is therefore the *older* and more settled of the two progress signals.[^taskprog-enum])*
2. **The docs are version-gated at patch granularity.** `headless.md` alone conditions
   behavior on v2.1.163, v2.1.169, v2.1.182, v2.1.203, v2.1.204, v2.1.205, v2.1.211,
   v2.1.214, v2.1.219, v2.1.221 and v2.1.223 — **eleven distinct version numbers**, reached
   by enumerating every version string on the fetched page and counting the enumerated
   list.[^headless] Behavior relevant to supervision (background-wait caps,
   SIGTERM semantics, stdin handling, exit-drain windows) is among what changed.

### 2.6 Out-of-band signals (definitive; independent of the stream)

These are *not* subject to §2.4's gap and are worth more than their crudeness suggests:

| Signal | How read | What it distinguishes |
|---|---|---|
| Process exit code | shell `$?` | 0 = success; 143 = SIGTERM'd; other non-zero = failure[^headless] |
| Log file **existence** | `test -f "$LOG_FILE"` | dispatch happened at all |
| Log file **mtime** | `stat` | last byte written — the true no-output clock, free of schema risk |
| Log file **size** delta | `stat` | output volume, not just recency |
| First line is `system`/`init` | `head -1` | the CLI got far enough to open a session |
| Presence of terminal `result` | scan | run reached its own end |
| Worktree git state | `git -C <wt> status` | whether *work* happened, vs. output happening |

**Log mtime is the schema-independent stalled signal.** It requires no event vocabulary,
survives any patch release, and is exactly what `tee`/redirect give us for free. Its
weakness is the mirror of its strength: it cannot tell a heartbeat from real content —
which is what makes `tool_progress` worth reading *in addition*, never *instead*.

---

## 3. Comparative landscape — the prior art, per leg *(LOW volatility; refresh may skip)*

### 3.1 Stalled — how other systems set a no-output threshold

| System | Shape | Threshold | Action on trip |
|---|---|---|---|
| **systemd `WatchdogSec=`** | in-band push; the *service* pings | operator-set; `0` = disabled by default | failed state + `SIGABRT`, optional restart[^sdservice] |
| **Kubernetes liveness probe** | out-of-band pull, periodic | `periodSeconds` × `failureThreshold` | kubelet restarts the container[^k8slife] |
| **Kubernetes startup probe** | out-of-band pull, *once*, gates the others | sized to worst-case startup | kills after the budget[^k8sprobes] |
| **CircleCI** | no-output timer on the job's stdout | **10 minutes default**, per-step override | kills the step[^circle] |
| **GitHub Actions** | wall-clock only | `timeout-minutes` **default 360**; step max 360 | cancels the job[^ghactions] |
| **Temporal Heartbeat Timeout** | in-band push from the activity | *"the maximum time between Activity Heartbeats"* | activity task fails, retry policy applies[^temporal] |
| **phi-accrual (Cassandra, Akka)** | out-of-band, *adaptive* | suspicion φ against a sliding window of observed inter-arrivals | caller chooses per φ level[^phi][^akka] |

Four shape lessons, each load-bearing here:

**(a) systemd's cadence rule.** The service is told the budget via `WATCHDOG_USEC=` and
*"It is recommended that a daemon sends a keep-alive notification message to the service
manager every half of the time returned here."* [^sdwd] A supervisor sets its threshold at
**≥ 2× the producer's emission interval**, never at 1×. Applied to the observed 30-second
`tool_progress` cadence, the floor for any heartbeat-based detector is 60 s — and that is a
*floor*, not a threshold.

**(b) Kubernetes' startup probe exists precisely because one threshold cannot serve two
phases.** The docs state the problem in the terms this paper needs: *"Sometimes, you have
to deal with applications that require additional startup time on their first
initialization. In such cases, it can be tricky to set up liveness probe parameters without
compromising the fast response to deadlocks that motivated such a probe."* The resolution:
*"The solution is to set up a startup probe with the same command, HTTP or TCP check, with
a `failureThreshold * periodSeconds` long enough to cover the worst case startup time"*,
after which *"the liveness probe takes over to provide a fast response to container
deadlocks."* [^k8sprobes] **This is the single most transferable design in the survey:
phase-scoped thresholds, not one global number.**

**(c) CI systems disagree on whether idle timeouts should exist at all.** CircleCI ships
one — *"A command will be killed if a certain period of time has passed with no output. By
default, this is 10 minutes"*, surfacing as `Too long with no output (exceeded 10m0s):
context deadline exceeded`.[^circle] GitHub Actions ships **none**: its workflow-syntax
reference documents only `jobs.<job_id>.timeout-minutes` (*"The maximum number of minutes
to let a job run before … automatically cancels it. Default: 360"*) and a per-step
equivalent, with **no idle or no-output mechanism documented anywhere on that
page**.[^ghactions] Two mature CI vendors, opposite answers — evidence that the
no-output threshold is a *policy* choice about false-positive tolerance, not a
best-practice with one right value.

**(d) phi-accrual replaces the binary verdict with a continuous one.** Rather than
"suspect / don't", it emits a suspicion level derived from the observed distribution of
past inter-arrival times, and lets each consumer pick its own threshold. The paper states
the trade-off exactly: *"A low threshold is prone to generate many wrong suspicions but
ensures a quick detection in the event of a real crash. Conversely, a high threshold
generates fewer mistakes but needs more time to detect actual crashes."* [^phi] Its worked
example is a **graduated action ladder** — at a low threshold the master "temporarily stops
sending new jobs"; at a moderate threshold it "cancels all unfinished computations … and
resubmits them"; only at a high threshold does it remove the worker and release
resources.[^phi] **The ladder, not the maths, is what transfers** (see §5.4).

### 3.2 Looping — how repetition is detected in LLM output

**Cheap and exact — byte-identity.** OpenClaw's shipped guard detects the *"same `(tool,
args, result)` triple within the window"*, and states its conservatism as a rule: *"The
guard never aborts while results are changing; only byte-identical results across the
window trigger it."* Escalation is graduated: *"Warnings come first. Blocking follows once
a pattern persists past the warning threshold."* [^oc-loop] **Numeric thresholds are not
stated in that document** — confirmed by asking the raw `.md` directly for window size and
counts, which returned an explicit "no concrete numbers".[^oc-loop] The upstream pool
recorded the same gap independently.[^oc47]

**Cheap and approximate — n-gram repetition.** The decoding literature treats repetition as
a first-class defect: Holtzman et al. show that *"using likelihood as a decoding objective
leads to text that is bland and strangely repetitive"*, and that *"decoding strategies alone
can dramatically effect the quality of machine text, even when generated from exactly the
same neural language model."* [^holtzman] The standard operational countermeasures are
exposed as generation parameters — Hugging Face documents `no_repeat_ngram_size` as *"If
set to int > 0, all ngrams of that size can only occur once"* and `repetition_penalty` as
*"The parameter for repetition penalty. 1.0 means no penalty."* [^hfgen] These are
*generation-side* mitigations, not supervision-side detectors, but they establish that
n-gram overlap is the accepted cheap proxy for repetition.

**Structural — loops in the agent graph.** LangGraph bounds the agent loop rather than
detecting it: `GraphRecursionError` means *"Your LangGraph `StateGraph` reached the maximum
number of steps before hitting a stop condition"*, with the documented causes being *"an
infinite loop caused by code"* with circular edges, or a complex graph legitimately
reaching the bound.[^langgraph] Our fleet already has the equivalent: `--max-turns` plus
`run-claude.sh`'s explicit `error_max_turns` banner.[^runclaude]

**Published work on the failure class.** Hou et al., *When Agents Do Not Stop: Uncovering
Infinite Agentic Loops in LLM Agents* (arXiv 2607.01641, 2 July 2026), frames it as *"an
agent may repeatedly execute model calls, tools, workflow transitions, or agent handoffs
when the feedback path is not effectively bounded"*, and detects it **statically** — their
IAL-Scan *"abstracts heterogeneous agent code into a framework independent Agent IR, builds
an Agentic Loop Dependence Graph (ALDG)"* and checks *"whether these paths can repeatedly
reach costly or state growing operations without an effective bound."* [^ial] *(Fetched via
the arXiv abstract page; treat as directional.)* **Note what this does and does not give
us:** it is a code-analysis tool for agent *frameworks*, not a runtime detector for a
running process. It corroborates that the failure class is real and named; it does not
supply a runtime threshold.

**Semantic comparison — stated as the boundary.** No source surveyed offers a cheap
semantic no-progress detector. What is cheap is: hashing `(tool_name, input)` pairs and
`tool_result` bytes from the stream (both are present in `assistant`/`user` events and
already parsed by `format-stream.sh`[^fmt]), and n-gram overlap over assistant `text`
blocks. What is *not* cheap is judging whether two textually-different actions constitute
progress — that needs a second model call per window, which is a cost and a new failure
mode. **Search method for this negative:** the survey above plus a targeted arXiv/web sweep
for LLM-agent loop/no-progress detection; results returned static analysis (IAL-Scan),
generation-side penalties, and framework step caps, but no runtime semantic-progress
detector with a published threshold.

### 3.3 Stranded — how never-claimed work is detected

| System | Mechanism | What makes "never claimed" visible |
|---|---|---|
| **SQS** | visibility timeout | the message is *in the queue*; a consumer receiving it makes it invisible. Default **30 seconds**, extendable via `ChangeMessageVisibility`, hard-capped at **12 hours from first receipt**[^sqsvis] |
| **SQS DLQ** | redrive policy | *"The `maxReceiveCount` is the number of times a consumer can receive a message from a source queue before it is moved to a dead-letter queue"*[^sqsdlq] |
| **Temporal** | Schedule-To-Start Timeout | *"the maximum amount of time that is allowed from when an Activity Task is scheduled to when a Worker starts that Activity Task"*; default ∞; **non-retryable by design**[^temporal] |
| **Hermes** | `stranded_in_ready` | a `ready` task with no claim inside `kanban.stranded_threshold_seconds` (30 min default), escalating to error at 2× and critical at 6×[^hm52] |

Three properties are worth copying, and one is worth refusing:

- **The claim record is the mechanism.** SQS's visibility timeout only works because the
  broker knows a receive happened. Temporal's Schedule-To-Start only works because the
  scheduling event is durable and separate from the start event. Without two distinct
  recorded facts — *dispatched* and *claimed* — the distinction is unmeasurable.
- **Schedule-To-Start is deliberately non-retryable**, because a retry would put the task
  back on the same queue that is not being drained.[^temporal] The correct response to
  stranded is **route or escalate**, never retry-in-place.
- **Identity-agnostic detection.** Hermes' design note is that the stranded signal
  *"Catches typo'd assignees, deleted profiles, and down external worker pools in one
  signal — identity-agnostic, no per-board allowlist to curate"*[^hm52] — a detector that
  needs a registry of valid workers fails exactly when the registry is wrong.
- **Refuse the fallback queue.** Hermes parks an unresolvable assignee with a typed event
  rather than falling back;[^hm53] the upstream synthesis carries this as a negative design
  constraint.[^synth10] Reproduced here only because it is a *measurement* consequence:
  parking keeps the stranded record intact and greppable; a fallback erases it.

---

## 4. What this provides — the measurement design a phase doc can cite

> Everything in §4 is **derived** — the paper's own inference over the sources in §2–§3.
> The inputs are cited; the inference is ours and is not marked definitive.

### 4.1 Stalled — a two-clock, phase-scoped predicate

**Signals (in priority order):**
1. `LOG_FILE` mtime — schema-independent, always available (§2.6).
2. `tool_progress` with `heartbeat:true` and rising `elapsed_time_seconds` — 30 s cadence.
   **Covers `Bash` and `TaskOutput` ONLY; it does NOT cover `Agent`/subagent quiet periods,
   nor tool calls inside a subagent** — this is documented vendor behaviour, not an
   observation: *"Claude Code doesn't emit heartbeats for the Agent tool, whose subagents
   stream their own progress, or for tool calls inside a subagent"*.[^ts-ref] Documented and
   version-gated at **Agent SDK v0.3.214**, so a detector may feature-gate on it (§2.4).
3. **`system`/`task_progress` — the subagent-side signal, and the only thing that covers
   the `Agent` case at all** (§2.3, Finding D). Documented since SDK v0.2.51, present in
   the April logs, ~6.5k occurrences across 35 files.[^taskprog-enum][^tschangelog]
   **Event-driven, not periodic** — it proves a subagent is calling tools; it does not
   prove a quiet subagent is alive. Use it as an *arrival* signal, never as a cadence.
4. Turn boundaries — an `assistant` event carrying a `tool_use` block, or a `user` event
   carrying a `tool_result`; these are the only timestamped events (§2.3, Finding B).
5. `system`/`api_retry` — proves the process is alive *and* explains why it is quiet;[^headless]
   its subagent-side analogue is the `subagent_retry` object on an `Agent` `tool_progress`
   event, which says a subagent is waiting out a rate limit rather than wedged.[^tschangelog][^tp-enum]

> **Design consequence, stated explicitly because the previous revision got it wrong.** A
> detector anchored on the heartbeat alone has **no coverage of the subagent leg**. Every
> workflow in this fleet dispatches subagents, and a subagent `Task` is one of the two
> long-quiet cases the stalled leg exists for. The cadence-anchored rule below therefore
> applies **only while heartbeats are flowing for the tool actually running**; during a
> subagent-dominated stretch the detector must fall back to the mtime floor plus
> `task_progress` arrivals, and must NOT tighten its threshold on the strength of a
> heartbeat that structurally will not arrive.

**Proposed predicate.** Following Kubernetes' phase split[^k8sprobes] and systemd's ≥2×
cadence rule[^sdwd]:

- **Startup phase** — from process spawn until the `system`/`init` event. A generous
  budget; the documented `MCP_TIMEOUT` startup wait alone is 30 s by default and Claude Code
  waits for pending MCP servers before the first turn.[^headless] *No liveness verdict is
  issued in this phase.*
- **Steady phase** — from `init` to the terminal `result`. Silence measured as
  `now − max(log_mtime, last_heartbeat_arrival)`.
- **Drain phase** — after `result`, the process may still be finishing. Documented bounds:
  background Bash killed ~5 s after the final result; background subagents waited on up to
  **10 minutes** by default; output drain capped at **30 s**.[^headless] A supervisor must
  not declare stalled inside this window; **the 10-minute background-agent ceiling is the
  binding constraint** and any drain-phase threshold must exceed it.

**Threshold shape: adaptive, not fixed.** A fixed number cannot serve a workload whose
legitimate quiet periods span orders of magnitude. Three defensible options, ranked by
cost:

| Option | Rule | Cost | Weakness |
|---|---|---|---|
| **Fixed, generous** | e.g. 15 min of zero bytes | trivial | wrong for both tails; misses fast deaths, still risks slow-run kills |
| **Cadence-anchored** (recommended first) | ≥ 2× observed heartbeat cadence *while heartbeats are flowing* (⇒ ≥ 60 s), falling back to a generous fixed floor when they are not | small | applies to `Bash`/`TaskOutput` only — **structurally silent during subagent work** (§2.3 Finding A), so the fallback path is the common path, not the exception |
| **Accrual / phi-style** | suspicion from the run's own inter-event distribution[^phi] | needs history + tuning | over-engineered for a fleet whose measured silent-death rate is 0.9%[^runclaude] |

**Do not adopt phi-accrual yet.** It is the right answer for a fleet with enough runs to
estimate a distribution and enough failures to justify the tuning. `run-claude.sh` records
the measured silent-death rate as **0.9% (4/443 runs, 3 of them from April)** and the
deliberate decision to make it *visible rather than recoverable*.[^runclaude] The evidence
does not yet support an adaptive detector; it supports a cadence-anchored one with a
generous floor. Revisit if the rate climbs under unattended operation — which is exactly
the reopen condition already written into the code.[^runclaude]

### 4.2 Looping — hash windows over what the stream already gives us

**Cheaply measurable, no new signal required** (all fields already parsed by
`format-stream.sh`[^fmt]):

- `H_call = hash(tool_name, canonicalized tool input)` from `assistant` → `content[].tool_use`
- `H_result = hash(tool_result text)` from `user` → `content[] | select(.type=="tool_result")`
- `H_text = hash(assistant text block)`, plus n-gram overlap between consecutive text blocks

**The predicate, taken from OpenClaw and stated conservatively:** fire only when
`(H_call, H_result)` is **byte-identical** across a window of consecutive occurrences —
*"The guard never aborts while results are changing"*.[^oc-loop] Byte-identity is what makes
the detector's false-positive rate near zero: a legitimately-retrying agent whose results
differ by even one byte is never flagged.

**Two known blind spots, stated rather than papered over:**
- **A→B→A oscillation** produces changing consecutive results and defeats byte-identity on
  a naive sliding window. A multiset-over-window comparison (k distinct hashes repeating in
  cycle) catches it; that is a design choice for the phase doc, not a research finding.
- **Semantically-identical, textually-different work** (the agent re-reads the same file
  with a one-character different pattern each turn) is invisible to any hash. This is the
  boundary named in §3.2; it needs a judge, and a judge is a cost and a new failure mode.

**Numeric window size is a GAP.** OpenClaw does not publish one;[^oc-loop] no other surveyed
source publishes one for this shape of workload. **This is a test-plan item (§8), not a
number to invent.**

### 4.3 Stranded — what must be recorded at DISPATCH time

**The measurement problem stated exactly:** "never claimed" and "claimed and silent" are
distinguishable only if *dispatch* and *claim* are two separately-recorded facts. This is
the one property all four prior-art systems share (§3.3).

**What the fleet records today (definitive — read from source):**

- Every workflow assigns `LOG_FILE="${LOG_DIR}/<workflow>-${TIMESTAMP}.jsonl"` before
  invoking `run_claude`.[^grep-timeout] The redirect/`tee` creates the file when the
  command starts. **File existence ≈ dispatch occurred.**
- The **first line being `system`/`init`** — observed as line 1 in every log inspected — is
  the claim record: the CLI got far enough to open a session, and the event carries
  `session_id`, `model` and `cwd`.[^logbr-init]

*(derived)* **Therefore the dispatched-vs-claimed distinction is already latent in the
filesystem and needs only to be made explicit.** The minimum durable record, in the spirit
of Temporal's separate schedule and start events[^temporal]:

| Field | Written when | Purpose |
|---|---|---|
| `dispatch_id` | before spawn | the durable identity (topic 1's subject — do not re-derive here) |
| `dispatched_at` | before spawn | the Schedule-To-Start clock starts here |
| `target` (host / worktree / workflow) | before spawn | routing, and identity-agnostic diagnosis[^hm52] |
| `claimed_at` | on the `system`/`init` event | closes the Schedule-To-Start window |
| `session_id` | on the `system`/`init` event | ties the record to the run |

**Threshold.** Unlike stalled, this one is easy, because the legitimate variance is small:
process spawn to `system`/`init` is bounded by documented startup work — a 30-second default
`MCP_TIMEOUT` startup wait, plus `SessionStart`/`Setup` hooks that stream `hook_started` /
`hook_progress` / `hook_response` events *before* `init`.[^headless] **A minutes-scale
threshold is defensible**; Hermes' 30-minute default[^hm52] is calibrated for a fleet where
the worker may be a machine that is simply off, and is the right order for the *pooled,
remote* case rather than the current local-spawn case. Use Hermes' **severity ladder shape**
(warn / error at 2× / critical at 6×[^hm52]) rather than its absolute number.

**Action on trip: escalate, never retry in place** — Temporal's Schedule-To-Start is
non-retryable by design for exactly this reason.[^temporal]

### 4.4 What the fleet already does right, and should keep

`wait-for-ci.sh` is the fleet's existing precedent for timeout policy and it encodes the
correct doctrine in a comment: it waits `CI_TIMEOUT=600` seconds (*"10 min — long enough for
typical gates, short enough not to strand a run"*), then **proceeds rather than failing**,
because *"killing the run because Actions is slow trades a large loss for a small one. But
it must be LOUD, so the child states the gate is unknown rather than reporting a clean-
looking review."* It sets `CI_UNSETTLED=true` and always returns 0.[^waitci] It also carries
a separate `CI_GRACE=45` startup grace — **the same phase-split Kubernetes' startup probe
implements**,[^k8sprobes] arrived at independently. Any liveness design should match this
posture, not contradict it.

---

## 5. False-positive cost — per leg, separately

> **§5.1 is LOW volatility** (classical results). §5.2–§5.4 are derived from this fleet's
> own numbers and posture and should be re-checked when those change.

### 5.1 Why the asymmetry has to be priced per leg

The failure-detector literature gives the frame: completeness and accuracy trade against
each other and the appropriate point *"is strongly related to application
requirements"* — the paper explicitly names the continuum between conservative detection
("reducing the risk of wrongly suspecting a running process") and aggressive detection
("quickly detecting the occurrence of a real crash").[^phi] The SRE literature gives the
operational cost of getting it wrong in the noisy direction: *"When pages occur too
frequently, employees second-guess, skim, or even ignore incoming alerts, sometimes even
ignoring a 'real' page that's masked by the noise"*, and *"Paging a human is a quite
expensive use of an employee's time."* [^sre] *(SRE quotes come from a rendered page via an
extracting fetch — treat as directional.)*

### 5.2 The three prices *(derived — inputs: §1's run duration, `run-claude.sh`'s measured rate, §2.6's kill semantics)*

| | **Stalled** | **Looping** | **Stranded** |
|---|---|---|---|
| **False positive =** | kill a healthy long-running run | interrupt an agent doing legitimate repetitive work | chase a run that started fine |
| **Direct cost** | up to ~60 min of model spend, destroyed | one blocked tool batch; run continues[^oc-loop] | operator attention only |
| **Indirect cost** | **uncommitted work in the worktree is lost** — the fleet's own turn-cap path warns "NOTHING was committed or pushed"[^runclaude] | a confused agent that must re-plan | alert fatigue[^sre] |
| **Recoverable?** | Partly — SIGTERM is clean (aborts the turn, kills the Bash process tree, runs `SessionEnd` hooks, exit 143)[^headless], but the *work* is not resumable: the fleet deliberately ships no resume[^runclaude] | Yes — byte-identity makes the FP rate structurally tiny[^oc-loop] | Yes, trivially |
| **False NEGATIVE cost** | one run's spend + wall-clock, at a measured 0.9% base rate[^runclaude] | **unbounded** — cost exhaustion and repeated side effects are the named consequences of an unbounded agentic loop[^ial] | work silently never happens; "the operator finds out by noticing that nothing happened"[^sprint] |
| **⇒ Detection should** | **RECORD and ALERT. Do not kill by default.** | **BLOCK the batch, graduated, warn first**[^oc-loop] | **ALERT and ESCALATE; never retry in place**[^temporal] |

### 5.3 Reading the table

- **Stalled has the worst false-positive economics of the three and the mildest
  false-negative economics.** A false negative costs one run's budget at a 0.9% base
  rate;[^runclaude] a false positive destroys up to an hour of unrecoverable work. **The
  ratio argues for a conservative threshold and for not killing.** This is the same
  conclusion `wait-for-ci.sh` reached for a different timeout, in a comment, in
  production.[^waitci]
- **Looping inverts it.** The false negative is the unbounded one — cost exhaustion,
  context growth, repeated external side effects.[^ial] And byte-identity makes the false
  positive structurally rare.[^oc-loop] **This is the one leg where an automatic
  intervention is justified**, and OpenClaw's graduated warn-then-block is the shape.
- **Stranded is nearly free to get wrong in either direction**, so it can afford the most
  sensitive threshold of the three. Its only real cost is operator attention, and the
  standing product decision is a notifier plus an inbox rather than a
  dashboard.[^synth10]

### 5.4 The design consequence: separate the verdict from the action

phi-accrual's worked example does exactly this — a low suspicion level stops *new* work
from being sent, a moderate level cancels and resubmits, and only a high level releases the
resource.[^phi] Combined with §5.2, the recommendation is:

> **A liveness verdict is a record. Escalation to alert is a policy. Killing is a separate,
> higher-bar decision that only the looping leg currently earns.**

This also keeps the detector honest under §2.4's residual schema risk: a detector that only
*records* cannot be catastrophically wrong when an event type changes shape in a patch
release. It is equally the right posture for the heartbeat's **coverage** hole (§2.3,
Finding A) — a recording detector that is structurally blind during subagent work produces
a gap in the record, which is visible; a killing detector with the same blind spot produces
a wrong kill, which is not recoverable.

---

## 6. Honest boundary — where liveness detection fails or misleads

**(a) Liveness ≠ progress ≠ correctness.** A run emitting a `tool_progress` heartbeat every
30 seconds is alive. A run whose byte hashes keep changing is making *progress*. Neither
says the work is *correct*. The fleet already knows this: `run-claude.sh`'s
`COMPLETION_PATTERN` exists precisely because *"A headless (`claude -p`) run ends on ANY
text-only turn, including a premature 'waiting on dispatched agents…' message: the harness
reports exit 0 with nothing produced."* [^runclaude] **A perfectly live, perfectly
non-looping, perfectly claimed run can exit 0 having done nothing.** That is the
false-completion guard's territory (topic 4), not this paper's — and the boundary is worth
stating loudly so the phase doc does not expect liveness to cover it.

**(b) The impossibility is real, not an engineering shortfall.** No threshold makes a
crashed process distinguishable from a very slow one in an asynchronous system.[^phi] Every
number in §4 is a bet about the workload's tail, not a fact about it.

**(c) The best signal has a coverage hole, and the paper's own reading of it was wrong
once.** The previous revision named §2.4 ("the best signal is undocumented") as the paper's
largest weakness. **That weakness was not real** — `tool_progress` is a documented,
version-gated SDK message type, and the NOT-PRESENT finding behind the claim was an
artifact of a truncated fetch (§2.4). The real weakness is narrower and more concrete:
**the heartbeat covers `Bash` and `TaskOutput` and not `Agent`** (§2.3, Finding A), so it
is silent during exactly the subagent-heavy stretches this fleet spends most of its wall
clock in. A cadence-anchored detector that does not know this will read normal subagent
work as silence.

Better still, the coverage hole is now **documented rather than inferred** — the vendor
states the `Agent`-tool exclusion outright[^ts-ref] — so a phase doc can design against it
with confidence instead of hedging against a sampling artifact.

Two residual risks remain, both smaller than the one previously claimed:
- *Schema drift.* Being documented is not being permanent: a field that ships in v0.3.214
  can be withdrawn in a later release, and the reference page carries no stability or
  deprecation guarantee. If `heartbeat` is removed or renamed, a cadence-anchored detector
  degrades to "everything looks stalled" or "nothing ever looks stalled" depending on which
  way the fallback is written. **Mitigation is a design requirement, not a caveat:** the
  mtime-based floor (§2.6) must be the primary and the heartbeat the refinement, never the
  reverse. What has changed since the first revision is that this drift is now *watchable*
  and *gateable* — the field has an explicit version gate to feature-detect on, and the SDK
  ships a CHANGELOG that has named every neighbouring change (v0.2.45, v0.2.51, v0.2.72,
  v0.3.214), so a per-release diff is a real mitigation.[^tschangelog][^ts-ref]
- *Method risk in this paper.* The defect corrected here — a summarizing fetch layer
  truncating a large document and answering confidently from the prefix — is not specific
  to this source. Any negative finding in this pool sourced from a large page deserves the
  same suspicion. This one survived a full authoring pass and was caught only by an
  independent verifier using a different fetch mechanism. **A second instance of the same
  class appeared in the round-2 correction:** a bulk enumeration over the SDK CHANGELOG
  attached the `task_progress` entry to the wrong version heading (v0.2.47 instead of
  v0.2.51), and was caught only by re-querying each entry individually against its nearest
  preceding heading.[^tschangelog] Bulk enumeration through a summarizing layer is
  unreliable for *association* as well as for absence.

**(d) When this whole layer is NOT needed.** The measured silent-death rate is **0.9%
(4/443)**, and `run-claude.sh` records the deliberate ruling that recovery machinery *"would
add failure modes (unverified commits pushed onto a healthy-looking PR, salvage loops) to
serve a sub-1% event that a message already resolves — hand recovery took ~10 minutes once
the operator knew where to look."* [^runclaude] **That argument survives this paper.** The
case for building detection now rests on two things the ruling itself names: it holds
*"with a human watching"*, and the reopen condition is *"if the rate climbs under
unattended/pooled operation."* The fleet-reliability sprint is that unattended future. **If
the fleet stays attended, the honest answer is that the stalled leg is not worth building
and the looping leg still is** — because looping's false-negative cost is unbounded
regardless of who is watching.

**(e) Detection can make things worse.** Every source that ships a detector also ships a
suppression mechanism — Paperclip's 30-minute re-arm window and coalescing of duplicate
wakeups,[^pc44] Hermes' claim *extension* for a live-but-slow worker,[^hm54] SQS's
`ChangeMessageVisibility` heartbeat extension.[^sqsvis] A detector without dedupe/re-arm is
a pager loop. **Budget for the suppression side or do not ship the detector.**

**(f) The three legs are not exhaustive, and this paper does not claim they are.** The
taxonomy is taken as given from upstream;[^synth10] it covers the failure modes those three
products found. Credential expiry mid-run, quota exhaustion, and a run that completes
falsely are all live-process failures this predicate will not see. They have their own
topics in this pool.

**(g) Sampling weakness in the empirical half.** Findings A–D rest on 58 log files from one
machine, one operator, and two time windows (April and August 2026) — and the corpus is
**live and growing**, so every count in §2.3 is an as-of figure that a re-run will not
reproduce exactly. **Five** files contain heartbeats; **two** contain the non-heartbeat
`Agent` variant. A four-event sample would **not** on its own be enough to prove `Agent`
events *never* carry a heartbeat — but it no longer has to: the vendor documents the
exclusion outright, and extends it to tool calls inside a subagent, which the corpus could
not have shown.[^ts-ref] **This is the one place where documentation rescued a thin
sample**, and it is worth noting that the inference from four events turned out to match
the specification exactly. Likewise, 58
logs establish *existence* and *cadence* but **not** the distribution of legitimate quiet
periods, which is exactly what a threshold needs. §8 item 1 exists because of this.

---

## 7. Citations

**Source-fidelity note (per Research Standard §3).** Fetches that returned full raw source
text — and from which spans are quoted as verbatim — are `headless.md`, both AWS SQS pages,
`types.py`, the TypeScript Agent SDK `CHANGELOG.md`, `agent-sdk/agent-loop.md`,
`agent-sdk/subagents.md`, `agent-sdk/streaming-output.md`, `systemd.service.xml`, and all
local files (read directly). Fetches that returned *extracted short spans* from a raw
source are marked "(extracted)": k8s probe docs, `sd_watchdog_enabled.xml`, Temporal,
OpenClaw, HF `configuration_utils.py`. Fetches from *rendered* pages via a summarizing
layer are marked "(rendered — reduced confidence)": CircleCI support article, Google SRE
book, LangChain docs, arXiv abstract pages. The phi-accrual quotes were transcribed by
reading the PDF's pages 1–2 directly.

**Two sources exceed this paper's authoring fetch layer and carry a standing warning.**
`agent-sdk/typescript.md` and `agent-sdk/python.md` exceed that layer's input budget; it
returns a prefix and, when asked, an explicit `[Content truncated due to length...]` marker.
**Positive matches from that prefix are usable; absences from it are not evidence.** The
truncation is a property of the tool, not of the documents — a raw `curl` returns both
whole (263,071 and 195,188 bytes respectively). `typescript.md` is quoted in this paper
**from that raw retrieval, performed during the verification pass, not by the authoring
agent**; `[^ts-ref]` states the provenance and the line numbers so a reader can reproduce
it. The first revision of this paper treated an absence from `typescript.md` as a finding,
and that is the defect these revisions correct (§2.4).

**Counts** (58 logs; 56 with a `result` event; 125 `tool_progress` of which 121 heartbeats
in 5 files and 4 non-heartbeat `Agent` events in 2; 6,479 `task_progress` across 35 files;
11 version gates) were reached by enumerating the population and counting the enumeration,
never by asking a layer for a total. **All log-corpus counts are as of 2026-08-07 against a
live, growing directory** (§2.3) — they are snapshots, not constants. One enumeration
instability was observed and is disclosed rather than hidden: two fetches of the same raw
`CHANGELOG.md` returned overlapping-but-unequal match sets, so only *positive* matches from
it are cited, and its silence on `heartbeat` is reported as "not found in two searches",
never as proof of absence.

### First-party product documentation and code

[^headless]: Anthropic, *Run Claude Code programmatically* (headless), raw markdown.
  Documents `--output-format stream-json`, `--include-partial-messages`, `system/init`,
  `system/api_retry`, `system/plugin_install`, `parent_tool_use_id`, exit codes, SIGTERM
  semantics (exit 143), the 10-minute background-subagent wait ceiling, the 30-second
  output-drain cap, and the 30-second default `MCP_TIMEOUT`.
  https://code.claude.com/docs/en/headless.md
[^types]: Anthropic, `claude-agent-sdk-python`, `src/claude_agent_sdk/types.py` (raw, read
  whole — re-fetched and re-enumerated 2026-08-07 for this correction pass).
  `ResultMessage` / `SystemMessage` / `AssistantMessage` / `UserMessage` / `StreamEvent`
  field lists; every `^class ` line enumerated. **Present:** `class RateLimitEvent` with
  docstring *"Rate limit event emitted when rate limit info changes."* and fields
  `rate_limit_info: RateLimitInfo`, `uuid: str`, `session_id: str`; also
  `class TaskProgressMessage(SystemMessage)`, `class TaskStartedMessage(SystemMessage)`,
  `class TaskUpdatedMessage(SystemMessage)`, `class TaskNotificationMessage(SystemMessage)`,
  `class RateLimitInfo`. **No class in this file corresponds to** `tool_progress`,
  `heartbeat` or `thinking_tokens` — that is the claim the argument rests on, and it is
  exact. *(Wording tightened: the bare strings are not wholly absent — `max_thinking_tokens`
  occurs as an unrelated options field. No `ToolProgress` or `ThinkingTokens` class exists,
  and no message class carries a `heartbeat` field.)* A grep of every line containing
  `time` (case-insensitive) returns only session-store `mtime`/`last_modified`/`created_at`
  fields and timeout settings — no message class carries a wall-clock timestamp. Repo
  `default_branch: main`, `pushed_at: 2026-08-07T04:15:32Z` (GitHub API).
  *(This footnote previously supported the claim that `rate_limit_event` has no class in
  this file. That claim was false and has been removed; `RateLimitEvent` is quoted above
  from a re-fetch.)*
  https://raw.githubusercontent.com/anthropics/claude-agent-sdk-python/main/src/claude_agent_sdk/types.py
[^ts-ref]: Anthropic, *Agent SDK reference — TypeScript*, raw markdown. **Retrieval
  provenance, stated because it is not reproducible with this paper's authoring tooling:**
  the spans below were obtained by raw, non-summarizing `curl` of this URL during the
  paper's verification pass and reproduced independently **three times**, against a document
  measuring **4,830 lines / 263,071 bytes with no truncation**. This analyst's own fetch
  layer returns `[Content truncated due to length...]` on the same URL and cannot reach the
  cited lines; a prompted enumeration through it reports `tool_progress`, `heartbeat` and
  `rate_limit_event` as having no matching lines, which is a **known false negative** and is
  the defect §2.4 documents. Under Research Standard §3 the `curl` retrieval is a legal
  verbatim source (exact characters returned by a non-summarizing fetch); the authoring
  layer's output is not, and is used for nothing here. Cited spans, at the line numbers
  reported by that retrieval:
  **L4388** `### \`SDKToolProgressMessage\``; **L4393** `type SDKToolProgressMessage = {`;
  **L4400** `  heartbeat?: boolean;`;
  **L4415** *"While a tool call runs in the main conversation, Claude Code emits a
  `tool_progress` message every 30 seconds with `heartbeat: true`. Each heartbeat carries the
  tool name and elapsed seconds, so you can distinguish a long-running call from a stalled
  session. Claude Code doesn't emit heartbeats for the Agent tool, whose subagents stream
  their own progress, or for tool calls inside a subagent. The `heartbeat` field requires
  Agent SDK v0.3.214 or later."*;
  **L4417** *"On `tool_progress` messages for the Agent tool, `subagent_type` names the
  running subagent type, such as `general-purpose`. `subagent_retry` is present while that
  subagent waits out an API error backoff, such as a rate limit or overload, with one message
  per retry attempt. Both fields require Agent SDK v0.3.214 or later."*;
  **L4527** `### \`SDKThinkingTokensMessage\``; **L4560** `### \`SDKRateLimitEvent\``.
  Separately, retrieved from within the truncated prefix by this analyst's own fetch and
  therefore independently visible here: the `agentProgressSummaries` option row, *"When
  `true`, generate one-line progress summaries for subagents and forward them on
  [`task_progress`](#sdktaskprogressmessage) events via the `summary` field. Applies to
  foreground and background subagents"*.
  *(Sibling page `agent-sdk/python.md` also exceeds this analyst's fetch budget and
  truncates for it — a raw retrieval returns it whole at 195,188 bytes / 3,737 lines. The
  truncation is a property of the authoring tool, not the document. Its confirmed absence of
  `heartbeat`, `tool_progress`, `ToolProgress` and `SDKToolProgressMessage` is consistent
  with the Python SDK's `types.py` (§2.2) and is not cited as evidence of anything else.)*
  https://code.claude.com/docs/en/agent-sdk/typescript.md
[^tschangelog]: Anthropic, `claude-agent-sdk-typescript`, `CHANGELOG.md` (raw, read whole;
  repo `default_branch: main`, `pushed_at: 2026-08-07T04:00:57Z`, `archived: false`, GitHub
  API). First version heading `## 0.3.224`, last `## 0.1.0`. Entries cited: **v0.3.214**
  *"Added optional `subagent_type` and `subagent_retry` fields to `tool_progress` messages
  so clients can show a subagent waiting out an API rate-limit retry"*; **v0.2.51** *"Added
  `task_progress` events for real-time background agent progress reporting with cumulative
  usage metrics, tool counts, and duration"*; **v0.2.45** *"Added `task_started` system
  message to the SDK stream, emitted when subagent tasks are registered"*; **v0.2.72**
  *"Added `agentProgressSummaries` option to enable periodic AI-generated progress summaries
  for running subagents (foreground and background), emitted on `task_progress` events via
  the new `summary` field"*. Every version attribution above was re-fetched and re-confirmed
  individually (asking for the entry line plus its nearest preceding `## ` heading, one
  query per entry) after a bulk enumeration over this file misattributed the `task_progress`
  entry to v0.2.47 — six releases early. **That defect is the reason for the method:** this
  file's bulk enumerations are unreliable (two fetches returned overlapping-but-unequal match
  sets, and the one that did associate headings associated them wrongly), so it is used for
  individually-confirmed positive matches only, and its silence is reported as "not found",
  never as absence. Two independent searches for `heartbeat` (exact-string, and
  case-insensitive) returned no match here — the field is documented in the reference page,
  not the changelog (§2.4).
  https://raw.githubusercontent.com/anthropics/claude-agent-sdk-typescript/main/CHANGELOG.md
[^agentloop]: Anthropic, *How the agent loop works* (raw markdown, read whole) — the five
  core message types, and *"Both SDKs also yield observability events such as rate-limit
  status and task notifications that are not required to drive the loop"*, pointing to the
  per-language message-type references for the complete lists. Also read whole this pass and
  containing none of the disputed event names: `agent-sdk/subagents.md`,
  `agent-sdk/streaming-output.md`. https://code.claude.com/docs/en/agent-sdk/agent-loop.md
[^npmpkg]: npm registry, `@anthropic-ai/claude-agent-sdk` — `/latest` record (JSON):
  `version: 0.3.224`, `types: sdk.d.ts`. unpkg file manifest for that version (JSON,
  enumerated): `sdk.d.ts` **333,809 bytes**, `sdk-tools.d.ts` 150,397, `bridge.d.ts` 12,972,
  `browser-sdk.d.ts` 4,246 — the size that makes the full type union unreadable through this
  fetch layer. `browser-sdk.d.ts` fetched: no `ToolProgress` / `tool_progress` / `heartbeat`.
  `bridge.d.ts` fetched: the only `heartbeat` in the shipped package is unrelated to the
  stream — *"CCRClient heartbeat interval seed. Defaults to 20s."* on the remote-control
  bridge's `heartbeatIntervalMs`. https://registry.npmjs.org/@anthropic-ai/claude-agent-sdk/latest
[^critic-report]: This paper's verification passes, 2026-08-07 — the retrieval channel that
  reached `agent-sdk/typescript.md` when the authoring tooling could not. Three independent
  non-summarizing `curl` retrievals (two critic passes and the orchestrating loop) returned
  a matching 4,830-line / 263,071-byte document and matching line numbers for every span
  quoted in `[^ts-ref]`; the underlying source is first-party Anthropic documentation, and
  the spans are cited to it there rather than to this footnote. Retained as the provenance
  record. Two of its findings were **rejected by this analyst after re-checking the primary
  evidence, and the rejections held**: that all four `Agent` `tool_progress` events carry a
  `subagent_retry` object (only two do — §2.3, Finding A), and that the TS SDK CHANGELOG
  establishes the `heartbeat` field's v0.3.214 gate (it does not; the reference page does,
  in a separate sentence — §2.4). Recorded because a verification channel is evidence, not
  authority, and this paper's corrections ran in both directions.
[^issue24596]: `anthropics/claude-code` issue #24596, *"[DOCS] CLI `--output-format
  stream-json` lacks event type reference"* — `state: closed`, `created_at:
  2026-02-10T05:44:02Z`, labels `documentation` + `stale`, 2 comments (GitHub API JSON;
  issue body was summarized by the fetch layer and is therefore not quoted).
  https://api.github.com/repos/anthropics/claude-code/issues/24596
[^llmstxt]: Anthropic, Claude Code documentation index (`llms.txt`) — enumerated to
  establish which pages exist. https://code.claude.com/docs/llms.txt

### Prior art — watchdogs, probes, timeouts, queues

[^sdservice]: systemd, `man/systemd.service.xml` (raw XML) — `WatchdogSec=`: the service
  must call `sd_notify` regularly with `WATCHDOG=1`; *"If the time between two such calls is
  larger than the configured time, then the service is placed in a failed state"* and is
  terminated with `SIGABRT`; the budget is passed as `WATCHDOG_USEC=`; defaults to 0
  (disabled). (Whitespace normalized from the XML source.)
  https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.service.xml
[^sdwd]: systemd, `man/sd_watchdog_enabled.xml` (raw, extracted) — *"It is recommended that
  a daemon sends a keep-alive notification message to the service manager every half of the
  time returned here."*
  https://raw.githubusercontent.com/systemd/systemd/main/man/sd_watchdog_enabled.xml
[^k8slife]: Kubernetes, *Pod Lifecycle* (raw markdown, extracted) — liveness/readiness/
  startup probe roles; liveness identifies deadlock-like states and the kubelet restarts on
  failure past the configured tolerance.
  https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/pods/pod-lifecycle.md
[^k8sprobes]: Kubernetes, *Configure Liveness, Readiness and Startup Probes* (raw markdown,
  extracted) — *"Protect slow starting containers with startup probes"*; the
  liveness-parameter tension; `failureThreshold * periodSeconds` sized to worst-case
  startup; liveness takes over afterwards.
  https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes.md
[^circle]: CircleCI Support, *Build Fails with "Too long with no output (exceeded 10m0s):
  context deadline exceeded"* (rendered — reduced confidence) — *"A command will be killed
  if a certain period of time has passed with no output. By default, this is 10 minutes."*
  https://support.circleci.com/hc/en-us/articles/360045268074-Build-Fails-with-Too-long-with-no-output-exceeded-10m0s-context-deadline-exceeded
[^ghactions]: GitHub, *Workflow syntax for GitHub Actions* (raw markdown) —
  `jobs.<job_id>.timeout-minutes` *"The maximum number of minutes to let a job run before
  {% data variables.product.prodname_dotcom %} automatically cancels it. Default: 360"*;
  step-level maximum 360; **no idle/no-output timeout documented on the page**.
  https://raw.githubusercontent.com/github/docs/main/content/actions/reference/workflows-and-actions/workflow-syntax.md
[^temporal]: Temporal, *Detecting Activity failures* (raw `.mdx`, extracted) —
  Schedule-To-Start *"the maximum amount of time that is allowed from when an Activity Task
  is scheduled to when a Worker starts that Activity Task"*, default ∞, non-retryable by
  design; Start-To-Close *"the maximum time allowed for a single Activity Task Execution"*;
  Heartbeat Timeout *"the maximum time between Activity Heartbeats"*.
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/detecting-activity-failures.mdx
  (repo `default_branch: main`, `pushed_at: 2026-08-06T23:52:06Z`)
[^sqsvis]: AWS, *Amazon SQS visibility timeout* — *"The default visibility timeout for a
  queue is 30 seconds"*; *"the visibility timeout has a maximum limit of 12 hours from when
  the message is first received"*; *"Implement a heartbeat mechanism to periodically extend
  the visibility timeout, ensuring the message remains invisible until processing is
  complete."*
  https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html
[^sqsdlq]: AWS, *Using dead-letter queues in Amazon SQS* — *"The `maxReceiveCount` is the
  number of times a consumer can receive a message from a source queue before it is moved to
  a dead-letter queue."*
  https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
  *(The GitHub mirror `awsdocs/amazon-sqs-developer-guide` has `default_branch: "archived"`,
  `archived: true`, and its tree no longer contains `doc_source/` — verified via the GitHub
  API before recording the raw-fetch failure, so the 404 is a real absence, not a wrong
  branch guess.)*
[^akka]: Apache Pekko (the Akka fork) `PhiAccrualFailureDetector` javadoc (rendered —
  reduced confidence) — *"Implementation of 'The Phi Accrual Failure Detector' by
  Hayashibara et al."*; restates the threshold trade-off verbatim from the paper; and
  documents `acceptableHeartbeatPause` as a *"Duration corresponding to number of
  potentially lost/delayed heartbeats that will be accepted before considering it to be an
  anomaly."* Cited only to establish that the algorithm ships in production systems and that
  a lost-heartbeat tolerance is a distinct knob from the threshold — no numeric claim.
  https://pekko.apache.org/japi/pekko/1.1/org/apache/pekko/remote/PhiAccrualFailureDetector.html

### Failure-detection and repetition literature

[^phi]: N. Hayashibara, X. Défago, R. Yared, T. Katayama, *The φ Accrual Failure Detector*,
  Proceedings of the 23rd IEEE International Symposium on Reliable Distributed Systems
  (SRDS'04), 2004. Quotes transcribed from pages 1–2 of the PDF: the conservative/aggressive
  trade-off; *"A low threshold is prone to generate many wrong suspicions but ensures a
  quick detection in the event of a real crash. Conversely, a high threshold generates fewer
  mistakes but needs more time to detect actual crashes."*; the graduated master/worker
  action ladder; *"a crashed process cannot be distinguished from a very slow one"*;
  Property 1 (Strong completeness), *"There is a time after which every process that crashes
  is permanently suspected by all correct processes"* (attributed there to Chandra & Toueg,
  ref. [4]). https://classes.cs.uchicago.edu/archive/2026/spring/23380-1/papers/hayashibara_phi.pdf
[^holtzman]: A. Holtzman, J. Buys, L. Du, M. Forbes, Y. Choi, *The Curious Case of Neural
  Text Degeneration*, arXiv:1904.09751 (rendered abstract page — reduced confidence).
  https://arxiv.org/abs/1904.09751
[^ial]: X. Hou, S. Wang, Y. Zhao, H. Wang, *When Agents Do Not Stop: Uncovering Infinite
  Agentic Loops in LLM Agents*, arXiv:2607.01641, submitted 2 July 2026 (rendered abstract
  page — reduced confidence). https://arxiv.org/abs/2607.01641
[^hfgen]: Hugging Face `transformers`, `src/transformers/generation/configuration_utils.py`
  (raw, extracted) — `no_repeat_ngram_size`: *"If set to int > 0, all ngrams of that size can
  only occur once."*; `repetition_penalty`: *"The parameter for repetition penalty. 1.0 means
  no penalty."*
  https://raw.githubusercontent.com/huggingface/transformers/main/src/transformers/generation/configuration_utils.py
[^langgraph]: LangChain, *GRAPH_RECURSION_LIMIT* (rendered — reduced confidence) — *"Your
  LangGraph `StateGraph` reached the maximum number of steps before hitting a stop
  condition."*; causes listed as *"an infinite loop caused by code"* and legitimately complex
  graphs. https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT
[^oc-loop]: OpenClaw, `docs/tools/loop-detection.md` (raw, extracted) — *"same `(tool, args,
  result)` triple within the window"*; *"The guard never aborts while results are changing;
  only byte-identical results across the window trigger it."*; *"Warnings come first.
  Blocking follows once a pattern persists past the warning threshold."* **No numeric window
  size or call count is stated** — confirmed by asking the raw document directly.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/loop-detection.md
[^sre]: B. Beyer et al. (eds.), *Site Reliability Engineering*, ch. "Monitoring Distributed
  Systems" (rendered — reduced confidence) — *"Every page should be actionable."*; *"When
  pages occur too frequently, employees second-guess, skim, or even ignore incoming alerts,
  sometimes even ignoring a 'real' page that's masked by the noise."*; *"Paging a human is a
  quite expensive use of an employee's time."*
  https://sre.google/sre-book/monitoring-distributed-systems/

### This repository (read directly — definitive)

[^runclaude]: `scripts/workflows/activities/run-claude.sh` — the `claude -p` invocation;
  `print_cycle_totals`' `select(.type == "result")` over `total_cost_usd` / `num_turns`; the
  `error_max_turns` termination block recording *"Measured rate is 0.9% (4/443 runs, 3 of
  them from April)"*, *"NOTHING was committed or pushed"*, and the reopen condition; the
  `COMPLETION_PATTERN` block and its headless early-stop rationale.
[^fmt]: `scripts/workflows/common/format-stream.sh` — the exact event types and fields the
  fleet parses today (`system`/`init`, `assistant` content blocks, `user` tool results,
  `result`, `error`).
[^waitci]: `scripts/workflows/activities/wait-for-ci.sh` — `CI_TIMEOUT=600`, `CI_GRACE=45`,
  `CI_POLL=15`; proceeds-not-fails on timeout with `CI_UNSETTLED=true`; the rationale
  comment *"killing the run because Actions is slow trades a large loss for a small one"*.
[^grep-timeout]: Repository search across `scripts/workflows/` for `LOG_FILE=`,
  `mkdir -p.*logs`, `timeout `, `SIGTERM`, `trap ` — establishes the per-workflow
  `LOG_FILE` assignment pattern and the absence of any `timeout`/signal wrapper on the
  `claude` invocation. Re-run 2026-08-07: `timeout ` matches exactly two lines, neither of
  them a wrapper — `wait-for-ci.sh:49` (a progress `echo`, `"→ Waiting for CI on
  ${head_sha:0:8} (timeout ${CI_TIMEOUT}s)…"`) and
  `temporal/modules/assistant/plan/plan_master/plan_master_workflow.py:158` (a prose
  comment, *"Adding one would spend a timeout per pass to observe nothing."*). The
  `build.sh`/`build-minor.sh` cleanup traps come from the `trap ` arm of the search, not
  the `timeout ` arm. The substantive finding is unchanged: nothing wraps `claude`.
[^sprint]: `docs/development/sprint.md` § *Fleet Reliability* — the milestone this paper
  feeds, and *"the operator finds out by noticing that nothing happened."*
[^log204414]: `.claude/logs/research-20260806-204414.jsonl` — event-type enumeration
  (lines 1–478) and `rate_limit_event` shape.
[^ts-grep]: `.claude/logs/research-20260806-204414.jsonl`, matches for
  `"(timestamp|startedAt|started_at|elapsed_ms|elapsedMs)":` — lines 3, 4, 5, 6, 7, 10, 11,
  12, 13, 14, 17, 18 …, all ISO-8601, cross-referenced against the type enumeration.
[^logrr]: `.claude/logs/research-refresh-20260805-111000.jsonl` — every
  `"elapsed_time_seconds":N,"heartbeat":true` occurrence enumerated (30/60/90/120/150/180/
  210/240 sequences), and the heartbeat line's terminal fields (`session_id`, `uuid`, no
  `timestamp`).
[^tp-enum]: `.claude/logs/*.jsonl` — **re-enumerated 2026-08-07 for this correction pass**,
  over a 58-file population. Four ripgrep enumerations, differenced against each other:
  `"type":"tool_progress"` → 125 occurrences in 6 files; `"heartbeat":true` → **121
  occurrences in 5 files**; `"tool_name":"TaskOutput","parent_tool_use_id"` → 102 in 4 files;
  `"tool_name":"Bash","parent_tool_use_id"` → 19 in 1 file (102 + 19 = 121, closing the
  heartbeat set). The residual 4 are `"tool_name":"Agent"` — 2 in
  `build-refine-20260806-223719.jsonl` (lines 526–527), 2 in `research-20260804-155357.jsonl`
  (lines 1132, 1135) — each with `"elapsed_time_seconds":0`, no `heartbeat` key, and a
  `subagent_type`; lines 526 and 1132 additionally carry
  `"subagent_retry":{"agent_id":…,"attempt":1,"max_retries":10,"retry_delay_ms":…,"error_status":null,"error_category":"unknown"}`,
  while 527 and 1135 terminate at `subagent_type`. All 121 heartbeats fall in logs dated
  2026-08-03 … 2026-08-06; none in the 25 logs dated 2026-04. *(The previous revision
  reported these 125 events as carrying a heartbeat across three `tool_name` values. Only
  121 carry one, across two.)* **As-of figure against a live, growing directory (§2.3).**
[^taskprog-enum]: `.claude/logs/*.jsonl` — `"subtype":"task_progress"` enumerated per file
  and the file list counted from the enumeration: **6,479 occurrences across 35 of the 58
  files** (2026-08-07), of which 17 files are dated 2026-04 — so the signal predates the
  heartbeat. Full observed shape quoted in §2.3 Finding D from
  `research-20260806-204414.jsonl` line 123; fields `task_id`, `tool_use_id`, `description`,
  `subagent_type`, `usage{total_tokens,tool_uses,duration_ms}`, `last_tool_name`, `uuid`,
  `session_id` — **no wall-clock `timestamp`**. `usage.tool_uses` increments by one per
  event, which is the evidence for "event-driven, not periodic". **As-of figure against a
  live, growing directory.**
[^result-enum]: `.claude/logs/*.jsonl` — **re-enumerated 2026-08-07**. Two ripgrep
  enumerations over the same 58-file population: anchored `^\{"type":"result"` matches **24
  files** (25 occurrences; all dated 2026-04); unanchored `"type":"result"` matches **56
  files** (57 occurrences; `revision-major-20260410-115958.jsonl` carries two). The **two**
  files with no `result` at all are `review-runs-20260410-120558.jsonl` and
  `research-20260807-104422.jsonl` — the latter in flight during this correction pass.
  Counts obtained by enumerating both lists and differencing them, not from a tool total.
  **This number is an as-of figure against a live, growing directory, not a frozen fact:**
  when this paper was first written the population was 57 files and *three* lacked a
  `result`; `plan-sprint-20260807-101659.jsonl` and `research-20260807-101449.jsonl` were in
  flight and have since acquired one, exactly as the paper predicted. The April file is the
  only durable member of the set and remains §8 item 4.
[^logbr]: `.claude/logs/build-refine-20260806-223719.jsonl` — `"type":"result",
  "duration_ms":1433359,"uuid":"55e3cae8-…"`.
[^logbr-init]: `.claude/logs/build-refine-20260806-223719.jsonl` line 1 —
  `{"type":"system","subtype":"init","cwd":"…","session_id":"4310528b-…","tools":[…`.

### Upstream product pool (cited as settled; not re-derived)

[^synth10]: `docs/standards/architecture/research/synthesis.md`, candidate 10 — *"Adopt the
  three-legged liveness taxonomy: stalled (no output) / looping (identical output) /
  stranded (never claimed). Three papers each supply one leg; none states the set. Liveness
  ≠ progress ≠ permission-to-continue"*; and candidate 22 (notifier + inbox, not a
  dashboard).
[^pc44]: `docs/standards/architecture/research/raw/paperclip_assessment.md` §4.4 — the
  stalled leg; output-silence rather than liveness ping; the three-way conjunction (not
  running AND not waiting AND not being recovered); the 30-minute re-arm window; wakeup
  coalescing.
[^oc47]: `docs/standards/architecture/research/raw/openclaw_assessment.md` §4.7 — the
  looping leg; byte-identity as deliberate conservatism; records the unstated-threshold gap.
[^hm52]: `docs/standards/architecture/research/raw/hermes_assessment.md` §5.2 — the
  stranded leg; `stranded_in_ready`, 30-minute default, error at 2× / critical at 6×;
  identity-agnostic detection.
[^hm53]: ibid. §5.3 — an unresolvable assignee PARKS with a typed event; never falls back.
[^hm54]: ibid. §5.4 — live-PID extension vs dead-PID reclaim vs absolute runtime cap;
  *"liveness, progress and permission-to-continue are three different predicates and a
  single timeout conflates them."*

---

## 8. Test plan — what research cannot settle

1. **The distribution of legitimate quiet periods.** *The* blocking unknown. Parse every
   log in `.claude/logs/` into inter-event arrival gaps, per workflow and per phase
   (pre-`init` / steady / post-`result`), and report the p50/p95/p99/max. **No threshold in
   §4.1 is defensible until this histogram exists** — §6(g) is why. Cheap: it reads existing
   logs, spends no dispatches.
2. **How far does the heartbeat's coverage hole extend?** *Narrowed, not closed.* The
   subagent half is **settled by documentation** — no heartbeats for the Agent tool, nor for
   tool calls inside a subagent[^ts-ref] — and matches the log enumeration (heartbeats for
   `Bash` 19 and `TaskOutput` 102, none for `Agent`).[^tp-enum] What remains untested is
   coverage across *main-conversation* tools the corpus happens not to exercise long enough:
   deliberately trigger a long `WebFetch`, a long `Grep` over a large tree, and a long MCP
   tool call, and record whether heartbeats appear. The reference says *"a tool call [that]
   runs in the main conversation"* without enumerating tools, so partial coverage is still
   possible and would force a per-tool fallback. Separately, measure whether `task_progress`
   arrivals are dense enough to serve as the subagent-side liveness proxy §4.1 now leans on,
   and how long they can legitimately go quiet.
3. **What the stream looks like when a run really dies.** Kill a `claude -p` run with
   SIGKILL (not SIGTERM) mid-tool-call and capture the tail of the JSONL. Compare against a
   SIGTERM'd run (documented: exit 143, `SessionEnd` hooks run[^headless]). This is the
   ground truth the stalled detector is trying to recognise, and no document supplies it.
4. **The `result`-less April log.** Enumeration found 56 of 58 logs containing a
   `"type":"result"` event as of 2026-08-07; the two without are
   `review-runs-20260410-120558.jsonl` and one log in flight during this correction
   pass.[^result-enum] The two 2026-08-07 logs the previous revision flagged have since
   acquired a `result`, as it predicted — which is itself a reminder that this count is an
   as-of figure, not a fact. Inspect the April one: it is either a real silent death
   (adding a fifth to the measured 4/443) or a benign artifact. **Either answer changes
   §5's base rate.**
5. **The looping window size.** OpenClaw publishes none.[^oc-loop] Replay existing logs
   through candidate `(H_call, H_result)` window rules at k = 3, 5, 8 and count how many
   *historical, successful* runs would have been flagged. Any rule that flags a known-good
   run at k = 3 is disqualified. Include an A→B→A oscillation case.
6. **Does a `system`/`init` event reliably arrive, and how fast?** Measure spawn→`init`
   latency across dispatches with and without MCP servers and `SessionStart` hooks
   configured. This is the *only* number the stranded threshold needs (§4.3).
7. **Cost of the mtime-only detector versus the heartbeat-aware one.** Implement the
   schema-independent mtime floor first, run it in record-only mode for a sprint, and count
   how many verdicts it would have issued. If it issues zero false verdicts, the
   heartbeat-aware refinement may be unnecessary — and §2.4's schema risk goes away with it.
   *This option is more attractive than the previous revision implied,* because the
   heartbeat's subagent blind spot (§2.3, Finding A) means the refinement buys less
   coverage than it appeared to.
8. **Does a semantic no-progress judge earn its cost?** Only after items 1 and 5. Sample
   windows that byte-identity did *not* flag, judge them offline, and measure how many were
   genuinely stuck. If the answer is near zero, §3.2's boundary is permanent and the phase
   doc should say so.
9. ~~**Read `agent-sdk/typescript.md` whole and settle the `heartbeat` field's
   documentation status.**~~ — **RESOLVED during verification; retained as the record of
   how.** This item proposed its own fix, and the fix worked: a raw, non-summarizing `curl`
   of the page — reproduced independently three times, returning 4,830 lines / 263,071
   bytes with no truncation — confirmed `### SDKToolProgressMessage`, `heartbeat?: boolean`,
   the 30-second cadence, the Agent SDK **v0.3.214** gate, and the `Agent`-tool exclusion
   (§2.4).[^ts-ref] Three claims moved from directional to definitive, the §2.4 gap shrank
   from six event types to two, and §6(c)'s risk narrowed to ordinary schema drift. **The
   transferable lesson is a tooling requirement, not a research question:** when a source
   exceeds the fetch layer's input budget, the answer is to change the retrieval mechanism.
   Reporting the resulting absence as a finding is the failure mode, and it happened here.

---

## 9. Escalation — above this paper's altitude, recorded not acted on

*(Surfaced per the dispatch's altitude constraint. These are for the reviewer and a planning
run, not for this paper to resolve.)*

1. **~~The undocumented-signal dependency is a portfolio risk~~ — WITHDRAWN. What replaces
   it is a method risk, and it is a bigger portfolio item.** The previous revision escalated
   `tool_progress`/`heartbeat` being undocumented as a portfolio-level exposure. **It is
   documented** — the message type has changelog entries, and the `heartbeat` field itself
   is defined, described and version-gated in the TypeScript reference (§2.4) — so the
   escalation as written is void, and **the specific question it raised is closed, not
   open.** Two things survive it, and the second is the larger:
   - *(smaller, still real)* The CLI-level `headless.md` documents none of these events even
     though the fleet consumes the stream through the CLI (§2.4), and the signal appeared
     between 2026-04 and 2026-08 (§2.5). Any component reading Claude Code's stream inherits
     that. Whether the fleet should maintain a pinned, tested schema snapshot — and diff the
     SDK CHANGELOG per release, which is now a *viable* watch mechanism — is an
     architecture-layer question. Note the documentation exists one layer up from where the
     fleet reads: the **SDK** reference documents what the **CLI** page does not.
   - *(larger, and now evidenced twice)* **A summarizing fetch layer silently truncated a
     first-party document and the research pass recorded the resulting absence as a
     finding.** It survived a full authoring pass and was caught only because an independent
     verifier used a different retrieval mechanism. **The same class recurred in the
     correction round in a different form:** a bulk enumeration over a file the layer *could*
     read whole still attached a changelog entry to the wrong version heading (§6(c)) — so
     the exposure is not only truncation, it is any *association* or *absence* judgement
     delegated to a summarizing retrieval. Every negative finding in this pool sourced that
     way carries the same defect risk, and the tooling gives no signal when it happens
     unless it is specifically asked for the document's tail. Whether the research tooling
     should refuse to report absences from truncated fetches, and should retrieve to a file
     and grep locally rather than asking a model to search, is a claude-dot-files-level
     question; it belongs in the architecture session, not in this paper and not in a
     direct edit to that repo.
2. **`--include-partial-messages` is an unexercised liveness lever.** Turning it on would
   give sub-second output cadence and make the stalled leg nearly trivial, at the cost of
   log volume and parse cost. That is a fleet-wide invocation change, above this component.
3. **The 0.9% ruling and the sprint may be in tension.** `run-claude.sh` argues detection
   machinery is not worth building at the measured rate under attended operation;[^runclaude]
   the sprint schedules it because unattended operation is coming.[^sprint] Both are correct
   under their own assumptions. **Which assumption holds is an operator decision**, and it
   determines whether the stalled leg ships now or waits — §6(d).
