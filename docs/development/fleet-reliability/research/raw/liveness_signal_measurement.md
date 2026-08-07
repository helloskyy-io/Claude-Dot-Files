# Measuring the three liveness legs against a live `claude -p` run

```
Topic:          How stalled (no output), looping (byte-identical output) and stranded
                (never claimed) are each MEASURED against a live headless `claude -p`
                process — what signals exist, what thresholds are defensible, and what
                a false positive costs on each leg.
Feeds:          Sprint milestone "The three-legged liveness predicate — stalled, looping
                and stranded, each detected separately" (docs/development/sprint.md:182)
                → the fleet-reliability phase doc's detection design (not yet written).
Last validated: 2026-08-07
Revalidate:     high — 3 weeks
Confidence:     DEFINITIVE — the fleet's own invocation and parsing (read from source);
                the observed stream-json event vocabulary and the 30-second
                `tool_progress` heartbeat cadence (enumerated from 57 JSONL logs in this
                repo); systemd WatchdogSec semantics; Kubernetes probe semantics; SQS
                visibility-timeout and DLQ semantics; GitHub Actions' lack of an idle
                timeout; the phi-accrual threshold trade-off.
                DIRECTIONAL — Temporal Schedule-To-Start framing; OpenClaw's
                byte-identical rule (raw doc, thresholds unstated); CircleCI's 10-minute
                default (first-party but support-article, not reference docs).
                DERIVED — every threshold proposal in §4, the false-positive asymmetry
                table in §5, and the dispatched-vs-claimed record design in §4.3.
                GAP (stated, not guessed) — Anthropic documents NO complete stream-json
                event-type reference; `tool_progress`, `heartbeat`, `thinking_tokens`,
                `rate_limit_event`, `vcs_state_changed` and `code_change_published` are
                observed in our logs and NOT found in first-party docs (§2.4).
Critic:         not-yet-verified — 2026-08-07
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
`SIGTERM`, `trap ` across `scripts/workflows/` — the only matches are log-path
assignments, `build.sh`/`build-minor.sh` temp-log cleanup traps, and `wait-for-ci.sh`'s
own `CI_TIMEOUT`).[^grep-timeout] Detection therefore has to be *added*, and this paper
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

Method: `.claude/logs/*.jsonl` in this repo was enumerated by glob (57 files, counted from
the enumerated list, not from a tool-reported total), then pattern-matched with ripgrep.

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

**Finding A — the stream carries a real, periodic heartbeat, and nobody documents it.**
`tool_progress` events appear with `"heartbeat":true`, a synthetic
`tool_use_id` of the form `<parent-tool-id>-heartbeat-<N>`, and a monotonically increasing
`elapsed_time_seconds`. Enumerating every such event in
`research-refresh-20260805-111000.jsonl` gives the cadence directly:[^logrr]

```
30, 30, 60, 90, 30, 60, 90, 120, 150, 180, 210, 240, 30, 60, 90, 120, 150, 180, 210
```

**A 30-second cadence, restarting per tool call.** Enumerating `tool_progress` across the
whole log corpus yields 125 occurrences in 6 of the 57 files, carrying three distinct
`tool_name` values: `TaskOutput`, `Bash`, and `Agent`.[^tp-enum] The heartbeat therefore
covers *both* of the long-quiet-period cases that matter — a long `Bash` command and a
subagent `Task` — which is precisely where a naive no-output detector would false-fire.

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
gets it for free.

### 2.4 GAP — there is no complete first-party event-type reference (stated as a finding)

**Search method:** fetched `code.claude.com/docs/llms.txt` and enumerated all documentation
URLs; fetched `headless.md` in full; fetched the Agent SDK TypeScript reference
`agent-sdk/typescript.md` and asked it to enumerate occurrences of `tool_progress`,
`heartbeat`, `timestamp`, `thinking_tokens`, `task_progress`, `rate_limit_event`; fetched
the Python SDK's raw `types.py` and enumerated every `class ` line and every line
containing `time`.

**Result:** `task_progress` is documented (as `SDKTaskProgressMessage`, with a `summary`
field populated when subagent progress summaries are enabled).[^ts-ref] `tool_progress`,
`heartbeat`, `rate_limit_event` and `thinking_tokens` were **NOT PRESENT** in that
reference,[^ts-ref] do not appear in `headless.md`,[^headless] and have no class in the
Python SDK's `types.py`.[^types] `vcs_state_changed` and `code_change_published` likewise
were not found in any page fetched.

Anthropic's own issue tracker corroborates the absence. `anthropics/claude-code` issue
**#24596**, titled *"[DOCS] CLI `--output-format stream-json` lacks event type reference"*,
was created **2026-02-10**, is labelled `documentation` and `stale`, has 2 comments, and is
**closed**.[^issue24596] *(The issue body was returned to us only as a summarizing
paraphrase and is therefore not quoted; only the structured JSON fields are cited.)*

**What this means for the phase doc, stated plainly:** the single most valuable liveness
signal in the stream (`tool_progress` with `heartbeat: true`) is an **undocumented
implementation detail**. A detector built on it is building on sand — it can vanish or
change shape in a patch release with no changelog obligation. Do not guess a schema; the
schema above is what we *observed*, not what is *promised*.

### 2.5 The surface moves — evidence of volatility (definitive)

Three independent signals justify the HIGH tier:

0. **The `result` event's field order changed** between the April-2026 and August-2026 logs
   in this repo (§2.3). Harmless to us — the fleet selects on `.type` via `jq` — but it is
   direct evidence that the wire format is edited without ceremony.[^result-enum]

1. **Our own logs changed shape.** All 125 `tool_progress` heartbeats occur in logs dated
   2026-08-03 through 2026-08-06. The 25 logs from 2026-04 contain none.[^tp-enum] A signal
   that did not exist four months ago is not a stable foundation.
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
2. `tool_progress` with `heartbeat:true` and rising `elapsed_time_seconds` — 30 s cadence,
   covers `Bash`, `Task`/`TaskOutput` and `Agent` (§2.3, Finding A). **Undocumented (§2.4).**
3. Turn boundaries — an `assistant` event carrying a `tool_use` block, or a `user` event
   carrying a `tool_result`; these are the only timestamped events (§2.3, Finding B).
4. `system`/`api_retry` — proves the process is alive *and* explains why it is quiet.[^headless]

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
| **Cadence-anchored** (recommended first) | ≥ 2× observed heartbeat cadence *while heartbeats are flowing* (⇒ ≥ 60 s), falling back to a generous fixed floor when they are not | small | depends on an undocumented signal (§2.4) — must degrade safely to the fixed floor |
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

This also keeps the detector honest under §2.4's schema risk: a detector that only *records*
cannot be catastrophically wrong when an undocumented event type disappears in a patch
release.

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

**(c) The best signal is undocumented.** §2.4 is the paper's largest weakness. If
`tool_progress`/`heartbeat` is removed or renamed, a cadence-anchored detector silently
degrades to "everything looks stalled" or "nothing ever looks stalled" depending on which
way the fallback is written. **Mitigation is a design requirement, not a caveat:** the
mtime-based floor (§2.6) must be the primary and the heartbeat the refinement, never the
reverse.

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

**(g) Sampling weakness in the empirical half.** Findings A–C rest on 57 log files from one
machine, one operator, and two time windows (April and August 2026). Six files contain
heartbeats. That is enough to establish *existence* and *cadence*; it is **not** enough to
characterise the distribution of legitimate quiet periods, which is exactly what a
threshold needs. §8 item 1 exists because of this.

---

## 7. Citations

**Source-fidelity note (per Research Standard §3).** Fetches that returned full raw source
text — and from which spans are quoted as verbatim — are `headless.md`, both AWS SQS pages,
`types.py`, `systemd.service.xml`, and all local files (read directly). Fetches that
returned *extracted short spans* from a raw source are marked "(extracted)": k8s probe
docs, `sd_watchdog_enabled.xml`, Temporal, OpenClaw, HF `configuration_utils.py`. Fetches
from *rendered* pages via a summarizing layer are marked "(rendered — reduced confidence)":
CircleCI support article, Google SRE book, LangChain docs, arXiv abstract pages, the Agent
SDK TypeScript reference. The phi-accrual quotes were transcribed by reading the PDF's
pages 1–2 directly. Counts (57 logs, 54 with `result`, 125 `tool_progress` events, 6 files,
10 version gates) were reached by enumerating the population and counting the enumeration,
never by asking a layer for a total.

### First-party product documentation and code

[^headless]: Anthropic, *Run Claude Code programmatically* (headless), raw markdown.
  Documents `--output-format stream-json`, `--include-partial-messages`, `system/init`,
  `system/api_retry`, `system/plugin_install`, `parent_tool_use_id`, exit codes, SIGTERM
  semantics (exit 143), the 10-minute background-subagent wait ceiling, the 30-second
  output-drain cap, and the 30-second default `MCP_TIMEOUT`.
  https://code.claude.com/docs/en/headless.md
[^types]: Anthropic, `claude-agent-sdk-python`, `src/claude_agent_sdk/types.py` (raw).
  `ResultMessage` / `SystemMessage` / `AssistantMessage` / `UserMessage` / `StreamEvent`
  field lists; every `class ` line and every line containing `time` enumerated. Repo
  `default_branch: main`, `pushed_at: 2026-08-07T04:15:32Z` (GitHub API).
  https://raw.githubusercontent.com/anthropics/claude-agent-sdk-python/main/src/claude_agent_sdk/types.py
[^ts-ref]: Anthropic, *TypeScript SDK reference* (rendered — reduced confidence).
  `task_progress` / `SDKTaskProgressMessage` documented with a `summary` field;
  `tool_progress`, `heartbeat`, `timestamp`, `thinking_tokens`, `rate_limit_event` returned
  NOT PRESENT. https://code.claude.com/docs/en/agent-sdk/typescript.md
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
  `claude` invocation.
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
[^tp-enum]: `.claude/logs/*.jsonl` — all `tool_progress` events enumerated across the
  corpus: 125 occurrences in 6 files, `tool_name` ∈ {`TaskOutput`, `Bash`, `Agent`}, all in
  logs dated 2026-08-03 … 2026-08-06; none in the 25 logs dated 2026-04.
[^result-enum]: `.claude/logs/*.jsonl` — two ripgrep enumerations over the same 57-file
  population: anchored `\{"type":"result"` matches 24 files (all dated 2026-04); unanchored
  `"type":"result"` matches 54 files (55 occurrences; `revision-major-20260410-115958.jsonl`
  carries two). The three files with no `result` at all are
  `review-runs-20260410-120558.jsonl`, `plan-sprint-20260807-101659.jsonl` and
  `research-20260807-101449.jsonl`; the latter two are dated today and plausibly in flight.
  Counts obtained by enumerating both lists and differencing them, not from a tool total.
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
2. **Does `tool_progress`/`heartbeat` cover every long tool call, or only some?** Observed
   for `Bash`, `TaskOutput` and `Agent` in 6 of 57 logs.[^tp-enum] Deliberately trigger a
   long `WebFetch`, a long `Grep` over a large tree, and a long MCP tool call, and record
   whether heartbeats appear. If coverage is partial, the cadence-anchored threshold must
   fall back per tool type.
3. **What the stream looks like when a run really dies.** Kill a `claude -p` run with
   SIGKILL (not SIGTERM) mid-tool-call and capture the tail of the JSONL. Compare against a
   SIGTERM'd run (documented: exit 143, `SessionEnd` hooks run[^headless]). This is the
   ground truth the stalled detector is trying to recognise, and no document supplies it.
4. **The three `result`-less logs.** Enumeration found 54 of 57 logs containing a
   `"type":"result"` event; the three without are `review-runs-20260410-120558.jsonl` and
   two logs dated 2026-08-07 (plausibly in-flight when this paper was written). Inspect the
   April one: it is either a real silent death (adding a fifth to the measured 4/443) or a
   benign artifact. **Either answer changes §5's base rate.**
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
8. **Does a semantic no-progress judge earn its cost?** Only after items 1 and 5. Sample
   windows that byte-identity did *not* flag, judge them offline, and measure how many were
   genuinely stuck. If the answer is near zero, §3.2's boundary is permanent and the phase
   doc should say so.

---

## 9. Escalation — above this paper's altitude, recorded not acted on

*(Surfaced per the dispatch's altitude constraint. These are for the reviewer and a planning
run, not for this paper to resolve.)*

1. **The undocumented-signal dependency is a portfolio risk, not just this design's risk.**
   `tool_progress`/`heartbeat` is undocumented (§2.4) and appeared between 2026-04 and
   2026-08 (§2.5). Any component that reads Claude Code's stream inherits the same exposure.
   Whether the fleet should maintain a pinned, tested schema snapshot of the observed event
   vocabulary is an architecture-layer question.
2. **`--include-partial-messages` is an unexercised liveness lever.** Turning it on would
   give sub-second output cadence and make the stalled leg nearly trivial, at the cost of
   log volume and parse cost. That is a fleet-wide invocation change, above this component.
3. **The 0.9% ruling and the sprint may be in tension.** `run-claude.sh` argues detection
   machinery is not worth building at the measured rate under attended operation;[^runclaude]
   the sprint schedules it because unattended operation is coming.[^sprint] Both are correct
   under their own assumptions. **Which assumption holds is an operator decision**, and it
   determines whether the stalled leg ships now or waits — §6(d).
