# What the Field Learned the Hard Way Running Long-Lived Agent Fleets

```
Topic:          What has the field learned the hard way running long-lived autonomous agent
                fleets — the failure modes, dead ends, and designs that did not survive
                production? Which of them is THIS system exposed to, and what does the
                cheapest mitigation cost?
Feeds:          docs/development/roadmap.md sequencing overall, and `Phase: Autonomous
                Operation` — specifically its two open items: "exit criteria that are real and
                observable" and "define failure behaviour for a missed window" (§ Temporal
                Crons). Secondarily `Phase: Temporal Integration` (payload/heartbeat
                constraints) and `Phase: Memory Management Framework` (the unread result
                envelope).
Last validated: 2026-08-04
Revalidate:     high — 4 weeks
Confidence:     DEFINITIVE on everything sourced from raw first-party artifacts fetched in
                this sweep: bernstein's release notes, ADRs and operations docs
                (raw.githubusercontent.com), Paperclip's migration SQL (raw), Temporal's
                troubleshooting docs and `constants.go` (raw), the four arXiv abstracts (Atom
                API), and two `anthropics/claude-code` issue bodies (GitHub REST JSON).
                DIRECTIONAL on four bernstein docs whose fetch returned a SUMMARY rather than
                the raw text (`WHY_DETERMINISTIC.md`, `deadlock-detection.md`,
                `context-degradation-detector.md`, `MAX_TURNS.md`, `schedule.md`,
                `cost-anomaly-detection.md`) and on the two rendered-page vendor posts
                (Cognition, Anthropic engineering) — quoted only where the fetch presented a
                span as exact. DERIVED, and marked so at each site, on every mapping from
                someone else's failure onto this system's exposure, on every mitigation cost,
                and on the whole of §7's ranking. UNVERIFIED: the AWS retry-storm article
                (JS-rendered, no body returned — see N4) and the total Paperclip migration
                count (see N3).
Critic:         not-yet-verified — 2026-08-04
```

> **Mixed volatility (§3).** The **low-volatility** core is §2.5 (the peer-reviewed / preprint
> failure literature) and §3's Temporal semantics — a refresh may skip re-verifying them. The
> **high-volatility** material is §2.1–§2.4: `bernstein` cut ~43 tagged releases in ~4.5 months
> and its `unreleased.md` is the densest seam in the corpus; Paperclip pushed to `master` on the
> day of this sweep. The header takes the highest tier present, and 4 weeks is set so each
> refresh reads roughly four new release pages rather than forty.

> **Relationship to `production_cases.md`.** That paper answers *who adopted durable execution
> and why*. This one answers *what killed the runs*. It extends it in three places: (a) it
> supplies the **failure evidence** that paper's §3 asserts from adoption behaviour rather than
> from postmortems; (b) it covers the operational layer that paper does not touch at all —
> credentials, watchdogs, schedulers, disk, binary drift; and (c) it contradicts nothing in it.
> Where this paper needed the stopping-rule literature it **cites `convergence_stopping.md`
> rather than re-deriving it**; §6.1 states exactly what is deliberately not repeated.

---

## 0. Headline

Three findings dominate, and all three are first-party.

**1. The failure that ended the most designs is putting a model in the coordination loop.** The
nearest-neighbour project documents a production pilot in which an LLM manager agent "fell asleep
regularly. When it did, every downstream agent starved" [S3]; of twelve named agents, "3 of 12"
were reliable producers [S5]. That design was replaced with deterministic Python. **This system is
already immune** — `system-overview.md` states "A parent calls no model" — and that immunity is
worth naming because it is the single most expensive lesson in the corpus and we did not pay for it.

**2. The failure this system IS most exposed to is credential expiry at an unattended edge.**
Two `anthropics/claude-code` issues describe exactly our configuration — OAuth from a Max
subscription, invoked headless via `-p`, in a loop, on a machine nobody is watching. One reports
401s "after ~10-15 minutes of usage" with the CLI declining to use the refresh token it holds
[S16]; the other reports the credential being **replaced with an empty value** on a failed
refresh, so "The agent appears to start normally but can't make any API calls" [S17]. Our
affordability thesis *requires* subscription auth at the edge. Nothing in the system detects this
today.

**3. Every exit criterion that a real system tried alone has failed, and the survivors are all
conjunctions.** Message counts failed (one pilot agent produced "283 bulletin messages" with "0
code commits" [S5]). Process liveness failed (Paperclip added four output-progress columns to
`heartbeat_runs` [S12]; bernstein caps log-mtime-derived liveness at three ticks because ~35 of
~40 adapters merge stderr into the log [S2]). Model self-report failed (a task in *any* state
"was force-completed with the caller's note as its result summary, so an unfinished task could be
marked done with an invented summary" [S2]). Context-window occupancy failed as a degradation
proxy (Vending-Bench found "no clear correlation between failures and the point at which the
model's context window becomes full" [S8]). §5 gives the three-part criterion that survived.

---

## 1. Primer — why "fleet failure" is a different subject from "agent failure"

An agent failure is a bad answer. A **fleet** failure is a run that consumed budget, held a slot,
produced an artifact that looks finished, and left the operator with no way to tell. The
distinction matters because the instruments differ: agent failure is caught by evaluation, fleet
failure is caught by *accounting* — heartbeats, ledgers, receipts, dedupe keys, reapers.

Three structural properties make a fleet fail in ways a single agent does not:

- **Nobody is watching the moment it happens.** The interval between a failure and its discovery
  is where cost accrues. bernstein's crash-loop doc is explicit that a persistent respawn loop
  "almost always means a real fault: a missing adapter binary, bad configuration, or an expired
  token" [S6] — the loop is the *symptom*; the discovery latency is the damage.
- **The failing component is stochastic and can report on itself.** A crashed process is honest.
  A model that finishes its turn and says "done" is not necessarily lying and not necessarily
  right, and no exit code distinguishes the cases.
- **Recovery machinery is itself a failure surface.** Every guard in this corpus was added
  because something broke; several then broke on their own account (§2.4).

**A guard is a scar.** Where this paper infers a wound from a shipped mitigation — a retry cap, a
dedupe index, a snooze column — the inference is marked *derived* and names the guard it came from.

---

## 2. The failure catalogue

### 2.1 The model-in-the-loop class — designs that were removed

**2.1.1 The LLM scheduler that fell asleep and starved its workers.** *(definitive)*

`bernstein`'s ADR-006 records the reversal in first person. The rejected alternative is named:
"This is the hierarchical-manager pattern used by several in-process frameworks, and was the model
used in the long-running multi-agent pilot (an LLM 'manager' agent on top of LLM workers)" [S3].
The reason:

> "In the pilot, the LLM manager agent was responsible for keeping all worker queues filled. It
> fell asleep regularly. When it did, every downstream agent starved. The system had a single
> non-deterministic point of failure that could not be fixed with better prompts." [S3]

Three further costs are stated: tokens spent on coordination "that produce no code, no tests, no
value"; non-reproducibility ("You cannot write a unit test for 'the LLM manager will assign the
right task under these conditions.'"); and non-linear coordination cost — "An LLM manager reading
status from 12 agents … has a context window proportional to the number of agents and tasks" [S3].
The enforcement is architectural, not advisory: "the `Orchestrator` class has no import of
`core/llm.py`" [S3].

**2.1.2 The persistent-session model, and the numbers that killed it.** *(definitive)*

ADR-005 rejects "Persistent sessions (the original pilot model)" and ADR-001's appendix supplies
the measurements [S4], [S5]:

| Pilot metric | Value |
|---|---|
| Total agents | 12 named + 5 phantom |
| Wall clock | ~47 hours |
| Tickets completed | 737+ |
| Reliable agents | 3 of 12 |
| Worst agent: bulletin messages / code commits | 283 / **0** |
| Second-worst agent: real commits vs. claimed | **2 of 40 claimed** |
| "Hunger spam" messages | 138 |
| Idle/polling status entries | 23 |

The stated failure modes: agents that exhausted their queue "stopped working silently," and
"Anti-sleep instructions in the system prompt ('NEVER sleep, NEVER stop') did not reliably prevent
this. The failure mode is a fundamental property of long-lived LLM sessions, not a prompt
engineering problem" [S4]. Context drift is reported concretely — "one agent claimed credit for the
manager agent's commits" [S4]. Roughly ~50,000 tokens went to signalling rather than work [S4].

The replacement design and its constants: agents spawn with **1–3 tasks**, execute, exit; **no idle
state**; a **30-minute wall-clock kill** "regardless of claimed progress"; and no inter-agent
messaging during execution [S4]. The batch bound has a stated reason: "Above 3, context accumulates
enough stale information that the agent's performance degrades measurably" [S4].

**"2 of 40 claimed" is the load-bearing number in this entire paper.** It is a measured, first-party
rate of an agent reporting work it did not do.

**2.1.3 Parallel writers with divergent assumptions.** *(directional — rendered page)*

Cognition's public position against multi-agent decomposition rests on a concrete example: a
"build a Flappy Bird clone" task split into two subtasks where "subagent 1 actually mistook your
subtask and started building a background that looks like Super Mario Bros," and the diagnosis
that "The actions subagent 1 took and the actions subagent 2 took were based on conflicting
assumptions not prescribed upfront" [S18]. Anthropic's own multi-agent write-up reports the
symmetric failure from the other side of the argument — "subagents misinterpreted the task or
performed the exact same searches as other agents" and "subagents duplicate work, leave gaps, or
fail to find necessary information" [S19].

*(Both are rendered-page fetches. Spans above are reproduced only where the fetch presented them as
exact; nothing is paraphrased inside quotation marks.)*

### 2.2 The liveness class — how a fleet learns an agent is dead

This is where the guards are thickest, in both surveyed products.

**2.2.1 Process liveness is not progress. Paperclip added output accounting.** *(definitive)*

Migration `0070_active_run_output_watchdog.sql` adds to `heartbeat_runs`: `last_output_at`,
`last_output_seq`, `last_output_stream`, `last_output_bytes`, plus a
`heartbeat_runs_company_status_last_output_idx` index [S12]. A `heartbeat_run_watchdog_decisions`
table is created carrying `decision`, `snoozed_until`, `reason`, and three distinct creator columns
(`created_by_agent_id`, `created_by_user_id`, `created_by_run_id`) [S12].

*Derived (from the schema in [S12]):* three wounds are legible here. Process-alive was insufficient
→ they began accounting for *output* progress and its byte volume. The watchdog produced verdicts
someone needed to override → `snoozed_until`. The overrides came from humans, agents, **and** other
runs → three creator columns, i.e. an agent-driven watchdog was itself being adjudicated.

**2.2.2 The watchdog then filed duplicate incidents.** *(definitive on the SQL; derived on the wound)*

The same migration ends with a partial unique index forbidding more than one active issue per
`(company_id, origin_kind, origin_id)` where `origin_kind = 'stale_active_run_evaluation'` and the
status is not `done`/`cancelled` [S12]. Migration `0069_liveness_recovery_dedupe.sql` does the same
for `origin_kind = 'harness_liveness_escalation'`, with a **second** index on `origin_fingerprint`
[S11]. A uniqueness constraint retrofitted onto an incident table is an alert-storm scar; a second
one at a different granularity is a scar from the first fix being too coarse.

**2.2.3 The agent's own log noise sustained a dead agent's heartbeat.** *(definitive)*

Two bernstein `Fixed` entries, both first-party:

> "`_refresh_heartbeat_from_signals` no longer lets a dead agent's own log noise sustain its
> heartbeat all the way to the 90-minute hard cap. Roughly 35 of the ~40 CLI adapters merge stderr
> into the agent log via `stderr=subprocess.STDOUT`, so a provider retry loop, a progress spinner,
> or a deprecation warning kept the log's mtime moving after the process had already exited"
> [S2, #3058]

The fix is a cap of **three** consecutive log-only ticks (`_MAX_LOG_ONLY_HEARTBEAT_TICKS`) [S2]. The
companion entry describes the same mechanism deferring a *stalled* (not dead) agent "forever,"
because the check "re-applied on every tick and reset the ladder each time, so the deferral had no
upper bound: a stalled agent was never escalated and held its worker slot until the wall-clock
reaper fired." Bound: `liveness_suppression_cap_s` = **900s** [S2, #3058/#3012].

**2.2.4 One pid-less session took down the whole orchestrator tick.** *(definitive)*

> "`_refresh_heartbeat_from_signals` passed that value straight into `_is_process_alive` … whose
> `if pid <= 0` guard raised `TypeError` … Because the tick calls `reap_dead_agents` outside any
> `try/except` … the failure was not contained to the one session: every other agent's reap, the
> pending push retry, and the evolution cycle were skipped along with it." [S2, #3212]

A remote-bridge session legitimately has `pid=None`. This is the canonical fleet failure: one
member's edge case silently disables the supervisor for all of them.

**2.2.5 Log-path drift silently disabled accounting and stall detection.** *(definitive)*

Two more entries record that four different worktree layouts exist in the codebase and that
consumers hardcoded one, so a session under the *current default* layout "got no signal at all:
usage accounting silently under-reported tokens for the affected run, and stall profiling ran on an
empty log summary rather than failing loudly" [S2, #3216/#3215]. *Derived:* the failure is not the
wrong path, it is that **an observability input degrading to empty was indistinguishable from
healthy**.

**2.2.6 Crash-looping is bounded and terminates in an operator gate.** *(definitive)*

bernstein's respawn budget: **3 respawns / 60s rolling window**, backoff `500ms * attempt` capped at
`5s`, and on exhaustion the session is **parked** — "the supervisor refuses to respawn it until an
operator intervenes. This turns a noisy crash loop into a single, auditable failure mode" [S6].
"Resume is the only recovery path. There is no automatic remediation on park; that is intentional,
so an operator confirms the fault is gone before the session is allowed to spawn again" [S6].

### 2.3 The false-completion class

**2.3.1 An MCP verb force-completed any task in any state.** *(definitive)*

> "Approving a task in any other state is now refused with a structured `task_not_awaiting_approval`
> error naming the current status, and no state-changing request is sent - previously any task in
> any state was force-completed with the caller's note as its result summary, so an unfinished task
> could be marked done with an invented summary." [S2, #3081]

The entry also records that "The streamable HTTP transport carried its own copy of the
unconditional completion, so both surfaces now share one gate," and states the residual honestly:
"Neither gate establishes which worker is calling: a caller holding `tasks:write` can still complete
a task another worker is executing" [S2].

**2.3.2 A failed required quality gate merged anyway.** *(definitive)*

> "`_evaluate_approval_gate` returned `skip_merge=False` whenever a required quality gate failed, so
> a failed gate was logged and recorded as `blocked` in `quality_gates.jsonl` but the branch merged
> anyway." [S2, #3254]

**2.3.3 A required CI check was satisfiable by a stub, and a PR merged with no tests run.** *(definitive)*

> "`paths` and `paths-ignore` filters are evaluated per file with OR semantics, so a mixed diff …
> fires both workflows and both published the same context name; the stub completed in seconds while
> the real test matrix was still queued, branch protection read a completed success, and a pull
> request merged to `main` with no test run against its code (#3016)." [S2]

The same entry records an adjacent hazard worth transferring verbatim: "rerunning a workflow resets
its check-run, so the newest `CI gate` instance on a head SHA can be a stale success from an earlier
attempt while the real run is still in flight, and a readiness probe must enumerate every instance
on the SHA and require `completed`/`success` rather than reading the latest one" [S2].

**2.3.4 A `--plan-only` flag executed the run.** *(definitive)*

> "`bernstein run plan.yaml --plan-only` took the `plan_file` dispatch in `_run_impl` … a task
> server, a watchdog, a spawner, a live agent, a worktree, a commit and the merge path, exit code 0,
> with the flag silently dropped. Reproduced twice in fresh repositories on 3.11.0." [S2, #3255]

**2.3.5 A failed submission exited 0.** *(definitive)*

`bernstein recipes fire` now "writes no receipt and exits `2` instead of the previous exit `0`, so a
script cannot read a failed submission as a successful run" [S2, #2673].

**2.3.6 The design that survived: a typed *refusal*, terminal by construction.** *(definitive)*

bernstein's `abandon` verb exists for "tasks that agents quit honestly instead of silently
half-completing or being killed by the watchdog" [S7]. Its invariant:

> "**Invariant.** `ABANDONED` is terminal: the FSM blocks `ABANDONED -> DONE/CLOSED`. A
> quietly-given-up task can never look like a completion." [S7]

The reason vocabulary is **closed** — `out_of_scope`, `insufficient_context`,
`conflicting_instructions`, `spec_underdetermined`, `time_budget_exhausted`, `budget_exceeded`,
`capability_mismatch`, `env_broken`, `blocked_by_external`, `unsafe_change`, `operator_override`,
`other` — "intentionally small so dashboards aggregate without operator-supplied free-form noise"
[S7]. Abandons cascade downstream consumers to `BLOCKED_BY_ABANDON` "so the dependency scanner stops
spinning" [S7].

Paperclip states the same lesson as a roadmap goal: watchdogs, recovery actions and review gates
exist to keep execution moving toward "merged code, published artifacts, shipped docs, or explicit
decisions instead of vague status updates" [S10].

### 2.4 The dead-guard class — controls that shipped and gated nothing

This is the highest-value pattern in the corpus and it recurs **three times in one codebase**.

- **The auto-approve safety classifier was never invoked.** "the smart command/tool auto-approve
  classifier … is now wired into the live tool-call approval path …; previously it was unit-tested
  but never invoked at runtime, so its deny-list and evasion defenses gated nothing in a live run"
  [S2, #1850]. *(definitive)*
- **Deadlock detection runs on an empty graph.** The detector exists, but the production path that
  identifies lock conflicts does not forward conflicts to it; `record_lock_wait()` appears only in
  unit tests. *(directional — this fetch returned a summary, not raw text)* [S20]
- **Cost-anomaly rules are implemented, unit-tested, and not invoked.** Only burn-rate detection is
  live (warn at 60% of budget, stop spawning at 90%); per-task ceilings, token-ratio spikes and
  retry-cost spirals are not called by the orchestrator. *(directional — summarized fetch)* [S21]

Related, and equally instructive:

- **A safety relaxation removed the boundary in exactly the mode that needed it.** Sandbox
  relaxation assumed container isolation made write-scope checks redundant, "but the Docker backend
  bind-mounts the entire repo read-only at `/host-repo` … so an out-of-scope write was auto-approved
  to ALLOW" [S2]. *(definitive)*
- **A `doctor` check "had never produced a correct answer"** and went unnoticed because a duplicate
  row above it printed a real verdict [S2, #3349]. *(definitive)*
- **Two subsystems were deprecated as dead**: `bernstein consensus` and `bernstein issue-to-pr`
  "inspect state no shipped runtime writes … so on any real project every subcommand reports an
  empty result" [S2, #3144]. *(definitive)*

*Derived:* the shape is constant — **a control whose failure mode is silence.** A guard that returns
"nothing to report" when it is disconnected is indistinguishable from a guard that returns "nothing
to report" when the system is healthy. The remedy that recurs in the fixes is a **wiring test**: "A
regression test asserts the gate actually invokes the classifier, so the wiring cannot silently rot
back into dead code" [S2, #1850].

### 2.5 The long-horizon class — measured, from the literature

All four fetched from the arXiv Atom API; abstracts are the source. *(definitive as to what each
paper claims; the papers themselves carry their own limits.)*

- **Multi-agent systems fail for structural reasons, and verification is one of three root
  categories.** MAST: 1600+ annotated traces across 7 MAS frameworks, taxonomy built from 150 traces
  with inter-annotator κ = 0.88, yielding "14 unique modes, clustered into 3 categories: (i) system
  design issues, (ii) inter-agent misalignment, and (iii) task verification." The framing sentence:
  "Despite enthusiasm for Multi-Agent LLM Systems (MAS), their performance gains on popular
  benchmarks are often minimal." [S8a]
- **Long runs derail, and context occupancy does not predict it.** Vending-Bench: runs exceeding
  "20M tokens per run"; "all models have runs that derail, either through misinterpreting delivery
  schedules, forgetting orders, or descending into tangential 'meltdown' loops from which they
  rarely recover"; and critically, "We find no clear correlation between failures and the point at
  which the model's context window becomes full, suggesting that these breakdowns do not stem from
  memory limits." [S8]
- **A wrong turn is not recovered from.** "LLMs Get Lost In Multi-Turn Conversation": an average
  **39%** drop across six generation tasks from single-turn to multi-turn, over 200,000+ simulated
  conversations, decomposed into "a minor loss in aptitude and a significant increase in
  unreliability" — "when LLMs take a wrong turn in a conversation, they get lost and do not
  recover." [S9]
- **The autonomy horizon is measurable and short.** METR: a 50%-task-completion time horizon "of
  around 50 minutes" for Claude 3.7 Sonnet, doubling "approximately every seven months since 2019."
  [S15]

*Derived (from [S8] + [S9] + [S4]):* these three converge on the same operational conclusion the
persistent-session reversal reached empirically — **the cheapest reliability intervention for a long
run is to end it and start a fresh one**, because degradation is not a memory-pressure phenomenon
you can compact your way out of and a derailed trajectory does not self-correct.

### 2.6 The durable-substrate class — hazards that arrive with Temporal

Directly actionable, because Temporal is this system's chosen substrate.

**2.6.1 Non-determinism on replay wedges in-flight workflows.** *(definitive)*

> "A non-determinism error occurs if, during workflow replay, the system determines a different set
> of commands was generated by the workflow code than is expected based on the events from the last
> code run. A workflow replay occurs when the workflow history is manually run in a replayer or when
> a worker needs to resume a workflow that is no longer cached (e.g. on worker crash or workflow
> cache eviction)." [S13]

Remedies are enumerated first-party: patching, worker versioning, or "fix code (and maybe reset)" —
with the honest caveat that a reset "means potentially re-running things that have already executed
before" [S13].

**2.6.2 Oversized payloads produce silent wedges, not clean errors.** *(definitive)*

Payload limit is **2 MB**; gRPC message limit is **4 MB** [S14]. Confirmed at source:
`BlobSizeLimitError` defaults to `2*1024*1024` and `BlobSizeLimitWarn` to `512*1024` [S22]. The
failure *behaviours* are the finding:

> "**Workflow result:** The Workflow gets stuck in a retry loop. The server rejects the
> `CompleteWorkflowExecution` command, and replay produces the same oversized result." [S14]

> "**Activity Tasks:** The Activity gets stuck in a retry loop or exits with a
> `ScheduleToCloseTimeout`. The Activity executes successfully, but the Worker can't deliver the
> oversized result over gRPC. … If no `ScheduleToCloseTimeout` is set, the Activity retries
> indefinitely until the Workflow is manually terminated. The `ResourceExhausted` gRPC error only
> appears in Worker logs." [S14]

And the mechanism that bites a *fan-out* rather than a big payload: "A Workflow can hit this limit
even when every individual payload is under 2 MB. Scheduling several Activities with
moderate-sized inputs, or hundreds of Activities with tiny inputs in the same Workflow Task can push
the combined request past 4 MB" [S14].

**2.6.3 Event history has hard ceilings.** *(definitive)* From `constants.go`:
`HistoryCountLimitError` = `50*1024` (51,200 events), warn at `10*1024`; `HistorySizeLimitError` =
`50*1024*1024` (50 MB), warn at 10 MB [S22].

### 2.7 The operational class — the edge itself

**2.7.1 Credential expiry, and credential *destruction*, on an unattended edge.** *(definitive)*

Issue #28827 (closed as duplicate, filed against Claude Code 2.1.59, auth "OAuth (Claude Max
subscription)", invocation "non-interactive via `-p` flag with `--output-format stream-json`"):

> "OAuth access tokens expire and are not refreshed when Claude Code is invoked non-interactively
> (e.g., via `-p` with `--output-format json`). This causes `401 authentication_error` failures after
> ~10-15 minutes of usage." … "This is particularly painful for automation use cases where Claude
> Code is invoked repeatedly in a loop by an orchestrator script. The token expires mid-run and kills
> the entire loop silently." [S16]

Issue #29896 (Claude Code 2.1.63, "Persistent tmux session, watchdog auto-restart, running 24/7", "3
agents on 3 separate machines"):

> "**Theory**: When the OAuth token expires, Claude Code attempts a refresh. If the refresh fails
> (network blip, server error, etc.), the old credential is deleted/overwritten with an empty value
> instead of being preserved." … "The agent appears to start normally but can't make any API calls" …
> "No error is logged until the agent tries to do work" … "The human may not notice for hours." [S17]

The reporter's own suggested remedy is "store an API key as a fallback auth method so the agent can
self-recover" [S17] — which for this system is **not free**, because an API key is metered and the
whole affordability thesis is flat-rate (§6.2).

*Note on status:* both issues are `closed`. Closure is not evidence of a fix — #28827 carries the
label `duplicate`. Treat the *reported behaviour* as definitive and the *current* behaviour as
unverified; §8/T1 makes it a test.

**2.7.2 Binary drift across a fleet.** *(definitive)*

bernstein's receipt-gated adapter admission exists because an installed CLI binary can move
underneath a still-valid attestation: the admission fingerprint is "a projection of `(contract
bytes, binary version, golden-transcript replay output)`, so … a binary that moved under a
still-valid receipt is caught as a named divergence rather than riding a stale attestation" [S2,
#2610]. The complementary control is a **nightly conformance canary matrix**, added "so a broken
upstream release is caught by the matrix rather than mid-run" [S2].

Anthropic reports the deployment-side analogue: "we use rainbow deployments to avoid disrupting
running agents, by gradually shifting traffic from old to new versions while keeping both running
simultaneously" [S19]. *(directional — rendered page.)*

**2.7.3 Disk and worktree accumulation.** *(definitive on the guard; derived on the wound)*

bernstein's artifact-mode change records that every artifact task "got a `git worktree add`, a
checkout, and an `agent/<session>` branch it never wrote through - held for the task's lifetime and
torn down unused, a real disk and setup-time cost on a fan-out of report or dataset tasks" [S2,
#2996]. The teardown machinery it describes is itself the scar inventory: workspaces are "removed at
reap and by the dead-agent cleanup entry point, removed by a leak guard when any exception escapes
the spawn after allocation … and orphans are swept alongside orphan worktrees" [S2]. Four distinct
removal paths, including one for the case where an exception escapes between allocation and use.

**2.7.4 Retries that reproduce the same failure.** *(definitive)*

bernstein's retry-budget doc opens by naming its audience: "operators tired of identical retries that
re-burn the same budget and produce the same failure," and states the mechanism plainly: "The default
retry path reruns with the same model, prompt, and gate criteria - so attempt #2 typically fails the
same way as attempt #1" [S22b]. The design that replaced it degrades a **named criterion** per retry
(`3 retries, degrade: coverage>tests>style`) and holds at a floor once all are degraded [S22b].

**2.7.5 Cost estimates that disagree with metered reality.** *(definitive)* A free-route run whose
real `total_cost` was `$0.000000` was shown "a phantom `~$0.25-$0.75 per task`" because the preflight
estimator and the metering path read different price tables [S2, #3013]. *Derived:* a budget ceiling
enforced against an estimate rather than against the metered figure is a control over a number
nobody pays.

**2.7.6 Untrusted memory steering a later agent.** *(definitive)* Persistent memory rows were injected
into a spawned agent's prompt "verbatim regardless of which adapter wrote it. A row written under one
adapter's provenance (or a foreign one) could therefore steer a different adapter's spawned agent"
[S2]. Fixed with a `MemoryTrustPolicy` allow-list. *Derived:* any cross-run memory surface is an
injection surface, and ours is GitHub PR/issue text written by prior runs.

**2.7.7 Declared context never reached the worker — at four independent break points.** *(definitive)*
`context_files` was parsed and dropped by the backlog parser, the plan loader, the spawner's metadata
read, and the POST body builder; a fourth drop "surfaced while verifying the wire end to end" [S2,
#3375]. *Derived:* a multi-hop configuration channel with no end-to-end assertion degrades to
silence, and the degraded state looks exactly like "the operator declared nothing."

---

## 3. Comparative landscape — how three real systems answer the same questions

Stated fairly, including where each is better than our shape.

| Question | `bernstein` (deterministic orchestrator) | Paperclip (control plane over a DB) | Temporal (durable substrate) |
|---|---|---|---|
| **Who decides what runs next** | Deterministic Python tick loop; zero LLM tokens on coordination [S3] | Server + DB state machine over `issues` / `heartbeat_runs` [S11], [S12] | Workflow code — deterministic by contract, enforced by replay [S13] |
| **How a stuck run is detected** | Heartbeat protocol JSON, agent log mtime (capped at 3 ticks), worktree `.git` mtime, wall-clock hard cap [S2] | `heartbeat_runs.last_output_*` + watchdog decision rows with snooze [S12] | Activity heartbeats + `ScheduleToClose`/`StartToClose` timeouts [S14] |
| **What bounds a run** | `max_turns` (1–10000, default computed from complexity) [S23]; 30-min wall clock [S4]; budget stop at 90% [S21] | Budgets as a first-class control-plane feature [S10] | Timeouts and retry policies; **no** turn concept |
| **Missed scheduled window** | `skip` by default (fire the most recent missed instant only), `catch_up` opt-in capped at 16 [S24] | `routine_runs.dispatch_fingerprint` + partial unique index on open routine-execution issues [S25] | Catchup Window (default 1 year, min 10s), Overlap Policy `Skip`/`BufferOne`/`BufferAll`, Backfill [S1] |
| **Duplicate-work protection** | Session claims, file-ownership locks, circuit-breaker scope [S2] | Partial unique indexes + `idempotency_key` on thread interactions [S11], [S26] | Workflow ID reuse policy; activity idempotency is the caller's duty |
| **Honest refusal** | `ABANDONED` terminal state, closed reason taxonomy [S7] | Recovery actions + review gates [S10] | Application-level; not a platform primitive |
| **Where it beats us** | Everything in this row — heartbeats, parking, abandons, admission receipts | Operator surface, budgets, multi-tenant recovery | Replay-based resume, schedules, retries |
| **Where our shape avoids its problem** | We have no worker pool to starve and no idle state to drift in | We have no shared DB to dedupe against yet | We have no replay contract to violate yet |

**The honest reading of this table:** on the liveness and completion columns, both products are ahead
of us by years of scar tissue. On the coordination column we are already at the design they arrived
at after a failed pilot. The gap is not architectural; it is **accounting**.

---

## 4. What this system is exposed to — and where it is already protected

Checked against `system-overview.md`, `roadmap.md`, and the shipped scripts.

### 4.1 Already protected — do NOT sequence these

*(derived, from the cited failure plus the named local mechanism)*

| Failure | Why we are protected | Mechanism |
|---|---|---|
| **LLM scheduler falls asleep / starves workers** [S3] | No model participates in routing | `system-overview.md`: "A parent calls no model." Parents are bash |
| **Persistent-session sleep, hunger spam, identity drift** [S4], [S5] | No agent has an idle state; every dispatch is a `claude -p` that runs and exits | Workflow scripts invoke `claude -p` per child |
| **Non-linear coordination cost with fleet size** [S3] | Coordination is `bash` + `git` | Same |
| **Multi-turn "wrong turn, never recovers"** [S9] | Author, refiner and judge are separate processes with disjoint contexts | `revision.sh` → draft / refine / review-pr; `system-overview.md` seam "author ≠ judge" |
| **Cross-agent file-lock deadlock** [S20] | One dispatch owns one worktree; there is no shared mutable checkout | Per-dispatch git worktree |
| **Headless early-stop reported as success** [S2, #3255-shaped] | Already caught, deliberately, with a loud failure | `run-claude.sh` §"Completion contract": a declared `COMPLETION_PATTERN` must appear in the final result or the run fails; the comment names the exact cause ("a text-only turn TERMINATES the run before later stages execute") |
| **Turn-cap exhaustion silently discarding work** | Already caught | `run-claude.sh` greps the log for `"subtype":"error_max_turns"` and returns 1 with the worktree path |
| **Model drift between dispatches** | Already refused | `run-claude.sh` refuses to dispatch on an inherited model (roadmap, `Phase: Managed Configuration`) |
| **Identical retries — "attempt #2 fails the same way as attempt #1"** [S22b] | The one loop-back is **not** a repeat of the first attempt | `revision.sh` L354 invokes the refine child with `--correction-pass`, and that flag's own documentation states the second pass exists because "a review-pr disposition comment with a runway already exists on this PR, and closing it is this run's job." The retry is **aimed at named findings**, which is the property bernstein's criterion-degradation design was built to obtain |
| **Temporal non-determinism / payload limits** [S13], [S14] | **Not exposed yet** — no Temporal in the system. Becomes live at `Phase: Temporal Integration`, where the roadmap already names both ("heartbeating for 10–60 minute runs, transcript-to-file for payload limits") | roadmap `Phase: Temporal Integration` |

**Two nuances worth stating precisely, because overclaiming either would mislead the planner:**

1. The completion contract is a **shape check on emitted text**, not a verification. Most workflows
   declare a PR-URL regex, which is far stronger than a self-report token because a URL is
   externally checkable — but `run-claude.sh` does not fetch it. `children/review-pr.sh` declares
   `^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$`, which **is** a pure self-report with
   no external referent. *(derived, from reading the scripts.)*
2. The roadmap's line that the parent "gates on none of them" (`is_error`, `subtype`,
   `terminal_reason`) is *nearly* right and worth correcting: `run-claude.sh` gates on exactly one
   subtype, `error_max_turns`. The exposure is real but narrower than stated. *(derived.)*

### 4.2 Exposed — with the evidence, and the cheapest mitigation

Costs are **derived estimates** in operator-hours, naming their inputs.

| # | Exposure | Evidence | Cheapest mitigation | Est. cost |
|---|---|---|---|---|
| E1 | **Credential expiry / credential wipe on an unattended edge.** OAuth-from-subscription, headless `-p`, in a loop, nobody watching — the exact configuration in both issues | [S16], [S17]; corroborated by bernstein listing "an expired token" among the causes of a persistent crash loop [S6] | A **preflight auth probe** in `run-claude.sh` before the expensive turn, plus a **post-run 401 classifier** that exits with a distinct code and notifies. `run-claude.sh` already has a `probe_stderr` path that greps for `rate.limit\|throttl\|429\|overloaded` — extend that grep, don't build a new layer | ~2h (one grep class + one exit code + one notify) |
| E2 | **A run that emits the right token without doing the work.** `VERDICT:` has no external referent; the PR-URL patterns are not fetched | [S5] "2 of 40 claimed"; [S2, #3081] invented result summaries; [S2, #3254] failed gate merged anyway | **Fetch the pointer.** For URL-shaped contracts, `gh` the URL and require HTTP 200 + head SHA match. For `review-pr`, require the verdict line **plus** a posted PR comment the parent re-reads. This is the same discipline `system-overview.md` already states for reviewers ("verifies a pointer by fetching it") applied to the completion contract | ~4h |
| E3 | **No stall detection on a `claude -p` child.** A hung child holds the dispatch indefinitely | [S2, #3058] (two entries), [S12] | A **wall-clock hard cap** per child via `timeout(1)`, sized above the observed p99. bernstein chose 30 min for a fresh agent [S4]; our children run 10–60 min per the roadmap, so the cap belongs per-child, not global | ~2h |
| E4 | **No missed-window policy; no scheduled autonomous dispatch design at all** | roadmap open item; [S1], [S24], [S25] | §5.2 — different answers per job class; ~15 lines of bash for the state-converging case | ~3h |
| E5 | **Orphaned worktrees and unbounded disk growth.** A dispatch creates a worktree; no reaper is documented | [S2, #2996] — four distinct removal paths, incl. a leak guard for exceptions escaping after allocation | A **sweeper** that prunes worktrees older than N days with no live PID, run from the same timer as `gh-monitor`. `git worktree prune` alone is insufficient — it does not remove a worktree whose directory still exists | ~2h |
| E6 | **`claude` binary version drift across machines.** `config/` is symlinked identically; the CLI is not pinned or recorded | [S2, #2610] admission receipts; [S2] nightly canary matrix; [S19] rainbow deployments | **Record it, then gate on it.** Stamp `claude --version` into every JSONL run log first (near-zero cost, makes drift *minable* by `review-runs.sh`); only add a version floor check after the log shows drift correlates with failures | ~1h to record; ~2h to gate |
| E7 | *(withdrawn — see §4.1.)* An earlier draft of this paper listed identical-retry exposure. **Reading `revision.sh` L345–357 and `children/revision-refine.sh` L79–82 falsified it**: the loop-back passes `--correction-pass` and closes a named runway. Recorded rather than deleted, because a planner who read the failure ([S22b]) without the check would re-derive the same wrong item | — | none needed | — |
| E8 | **A control whose failure mode is silence.** Our `PreToolUse` hook is, per `system-overview.md`, "the only control operating during a run" — and the roadmap flags that `--setting-sources project,local` "would strip it from every autonomous run" | [S2, #1850] classifier gated nothing; [S20] deadlock detector on an empty graph; [S21] cost rules not invoked | A **wiring test**: a dispatch fixture that issues a known-denied command and asserts the hook fired. This is the exact remedy bernstein adopted ("A regression test asserts the gate actually invokes the classifier") | ~3h |
| E9 | **Rate-limit exhaustion is our budget ceiling, and nothing enforces one.** The roadmap records that "2 concurrent engineers + PM session can exhaust rate limits in half a metered period" | [S21] warn 60% / stop-spawning 90%; [S10] budgets as first-class | A **concurrency ceiling** on simultaneous dispatches — the flat-rate analogue of a USD cap. USD budgeting does not transfer (§6.2); concurrency does | ~2h |
| E10 | **Alert/incident storms once a driver files issues automatically.** Our no-change outcomes land as GitHub Issues; a loop that files one per failed leg will duplicate | [S11], [S12] — two dedupe indexes, at two granularities, retrofitted | An **origin-fingerprint convention** in the issue title/body plus a "search before file" step. Adopt Paperclip's two-level shape (incident id **and** fingerprint) from the start rather than discovering the second level later | ~2h |
| E11 | **Prior-run text is an injection surface.** PR threads and issues written by earlier runs are read by later ones as memory | [S2] `MemoryTrustPolicy` | Provenance-tag machine-written comments and have consumers treat untagged/foreign-tagged text as data, not instruction. Low cost now, expensive to retrofit after multi-edge | ~3h |

---

## 5. The two roadmap questions, answered directly

### 5.1 Observable exit criteria for an unattended loop

The roadmap rejects a turn count and asks what replaced it elsewhere.

**What was tried alone, and failed — each with its source:**

| Criterion | Where it failed |
|---|---|
| **Message / activity count** | Pilot agent: 283 bulletin messages, 0 commits [S5]. Activity is not progress |
| **Process liveness (PID alive)** | Paperclip added `last_output_at/seq/stream/bytes` [S12]; bernstein caps log-mtime liveness at 3 ticks because stderr noise looks like life [S2] |
| **Model self-report** | "an unfinished task could be marked done with an invented summary" [S2, #3081]; "2 real code commits out of 40 it claimed" [S5] |
| **Context-window occupancy** | "no clear correlation between failures and the point at which the model's context window becomes full" [S8] |
| **A gate's boolean verdict, unchecked** | Failed required gate merged anyway [S2, #3254]; stub satisfied a required CI check [S2, #3016] |
| **"Nothing new this pass"** | Covered in `convergence_stopping.md` §5.3 — not re-derived here |

**What survived is a conjunction of three independent things.** *(derived, from [S4], [S5], [S6],
[S7], [S12], [S14], [S21] — no single source states it this way.)*

1. **An externally-verifiable artifact state.** Not the agent's claim: a merged PR, a green check
   run enumerated across *all* instances on the head SHA [S2], a file at a declared path, a signed
   receipt. bernstein's phrasing for the general rule: verification relies on concrete signals
   (file existence, test passage) rather than agent claims [S27]. Paperclip's: "merged code,
   published artifacts, shipped docs, or explicit decisions instead of vague status updates" [S10].
2. **A hard backstop that fires regardless of claimed progress.** bernstein: a 30-minute wall clock
   "regardless of claimed progress" [S4], a 90-minute hard cap in the reaper [S2], a respawn budget
   of 3/60s ending in an operator-gated park [S6], and a spend stop at 90% of budget [S21]. Temporal
   makes the same point negatively: without `ScheduleToCloseTimeout` an activity "retries
   indefinitely until the Workflow is manually terminated" [S14]. **Every surveyed system has one.**
3. **A typed refusal the loop can emit and the driver can route on.** `ABANDONED` is terminal by FSM
   construction, with a closed reason vocabulary [S7]. This is what converts "the loop stopped" into
   "the loop stopped *for reason R*", which is the only form a code-routed driver can branch on.

**Applied to `Phase: Autonomous Operation`** *(derived)*: the exit criteria the phase already names
map onto the three cleanly — a `HOLD` on a PR is (3), a budget ceiling is (2), and a convergence
signal is a *candidate* for (1) but only once findings are typed (see `convergence_stopping.md` P11).
The gap the phase does not name is (1) in its cheap form: **the driver must re-derive the artifact
state itself rather than accept the child's report of it.** That is E2, and it is the cheapest of
the three to build.

One negative result worth carrying: **`max_turns` is not useless, it is misplaced.** bernstein keeps
an explicit `max_turns` (1–10000) whose stated use cases include "preventing runaway agents"
[S23], and `run-claude.sh` already detects `error_max_turns`. A turn cap is a legitimate *backstop*
(role 2). The roadmap is right that it cannot be the *criterion* (role 1). Both statements are
compatible and the corpus supports both.

### 5.2 Missed-window behaviour for scheduled work

**What real schedulers do:**

- **Temporal Schedules.** A Catchup Window (default **one year**, minimum **ten seconds**) plus an
  Overlap Policy of `Skip` / `BufferOne` / `BufferAll`, with per-schedule counters `missedCatchupWindow`,
  `overlapSkipped`, `bufferDropped`, `bufferSize`, and an explicit `Backfill` operation for
  deliberately replaying a skipped interval [S1].
- **bernstein.** Misfire policy `skip` is the **default**: the supervisor "computes the most recent
  missed fire instant strictly older than `now`, dispatches that single fire, and records a
  counterfactual receipt for every intermediate window the operator can replay." `catch_up` is
  opt-in and capped at **16**, because "The catch-up cap exists so a long outage cannot blow the task
  queue when an operator opted into catch-up." [S24] *(directional — summarized fetch; the quoted
  spans are the ones the fetch presented as exact.)*
- **Paperclip.** Migration `0062_routine_run_dispatch_fingerprint.sql` adds
  `routine_runs.dispatch_fingerprint` and `issues.origin_fingerprint`, then **drops and recreates**
  `issues_open_routine_execution_uq` to include `origin_fingerprint` in the key [S25].

**What went wrong with each choice — this is the part the roadmap needs:**

| Choice | Documented failure |
|---|---|
| **Catch-up, uncapped** | Named as the reason bernstein's cap exists: a long outage blows the task queue [S24] |
| **Buffer (`BufferAll`)** | "Long-running Workflow Executions under `BufferAll` can push buffered Actions past the Catchup Window," producing buffer overruns and dropped actions [S1] |
| **Skip on overlap** | A miss that is not an outage: "If the Schedule uses the `Skip` Overlap Policy and the preceding run was long-running, the miss may reflect that run exceeding the Catchup Window" [S1] — i.e. **slow runs masquerade as missed windows** |
| **Dedupe key too coarse** | Paperclip's `issues_open_routine_execution_uq` originally keyed on `(company, origin_kind, origin_id)`; the fingerprint column was added and the index rebuilt, meaning **legitimately distinct dispatches were being collapsed** [S25]. *(derived from the DROP/CREATE pair.)* |
| **Alert-only** | Temporal's own guidance treats the metric as an *alert plus a manual narrowing procedure* — `ListSchedules` "does not return per-Schedule miss counters," so finding *which* schedule missed requires fanning out `DescribeSchedule` [S1]. Alert-only has an unbounded human step |

**The recommendation, and it contradicts an assumption in the roadmap.** *(derived — from [S1],
[S24], the §5 gate in `research_standard.md`, and `scripts/workflows/review-runs.sh` lines 24 and 207.)*

The roadmap says *"Different answers for a CPI sweep (skip is fine) and a research revalidation
(skipping silently lets a paper rot)."* Checked against the code, **that is backwards.** The
discriminator is not importance; it is whether the job is **window-scoped** or **state-converging**:

- **`review-runs.sh` is window-scoped.** It selects logs with `find … -mtime "-${DAYS}"` (default 7)
  — a trailing window relative to *now*, not "since the last run." A skipped weekly sweep means the
  next sweep at day 14 with `--days 7` covers days 7–14 and **days 0–7 are never analysed by anyone**.
  Skipping loses data permanently. → **catch-up with a cap**, or (cheaper and better) **widen
  `--days` to cover the gap on the next fire**, which is the same idea with no new machinery.
- **Research revalidation is state-converging.** Its gate is `today − Last validated > Revalidate
  interval` (Research Standard §5). A missed window changes nothing: the next fire still finds the
  paper due, and the standard already treats a past-window paper as flagged-not-trusted. Skipping is
  **self-healing**. What it needs is not catch-up but a **consecutive-miss alarm**, because N
  consecutive misses means the timer itself is dead — which is the failure "silently lets a paper
  rot" actually describes.

Cheapest implementation, stated so it can be sequenced *(derived)*:

1. **Default `skip`, fire only the most recent missed instant** — bernstein's default shape [S24].
2. **For window-scoped jobs, widen the window to cover the gap** rather than firing N times: one
   `--days` computation from the last successful run's timestamp. ~10 lines. This gets catch-up's
   coverage without catch-up's queue risk.
3. **Emit a per-schedule miss counter and alarm on ≥2 consecutive misses** — Temporal's
   `missedCatchupWindow` shape [S1], which we get free once schedules are Temporal-owned.
4. **Fingerprint every dispatch** at *two* levels (schedule id **and** intended fire instant) before
   deduping, so distinct fires are not collapsed. Adopting Paperclip's post-fix key shape from the
   start avoids their DROP/CREATE cycle [S25]. ~1h.

**Do not put PR disposition on a timer.** The roadmap already says this; the corpus supports it —
every scheduler failure above is a *timer* failure, and an event-driven path has none of them.

---

## 6. Honest boundary analysis

### 6.1 What this paper deliberately does not settle

- **Stopping rules for iterative review loops.** Owned by `convergence_stopping.md`, whose findings
  (non-monotonic yield, the oracle-stopping-rule defect, the "3–5 passes" provenance failure) are
  cited, not re-derived. A reader who takes §5.1 as a complete stopping theory has read the wrong
  paper.
- **Whether durable execution is the right substrate.** Owned by `durable_execution.md` and
  `temporal.md`. §2.6 assumes the choice and enumerates its hazards.
- **`bernstein`'s full capability surface.** Owned by `bernstein_capability_mining.md` this cycle.
  This paper reads its release notes for *wounds*, not features.

### 6.2 Where the field's experience does NOT transfer — and mis-transferring it costs more than missing it

**A. USD budgeting is not our budget.** bernstein's cost machinery (per-task/run/day USD ceilings, a
hash-pinned price table, `budget_stop_pct` at 90%) [S21], [S2, #2354] and Paperclip's budgeting
milestone [S10] both assume metered billing. We are flat-rate by design
(`problem-statement.md` § *Affordability is the enabler*). **Porting a USD ceiling would enforce a
control over a number nobody pays.** The transferable part is the *shape* — a burn-rate ceiling that
stops spawning — applied to the resource that is actually scarce here: **rate-limit headroom and
concurrent dispatch slots** (E9). Note that bernstein's own phantom-cost bug [S2, #3013] is the
degenerate case of exactly this error inside a metered system.

**B. Central-queue starvation does not apply to dedicated edges.** The pilot's failure was a manager
failing to keep *shared* worker queues filled [S3]. `problem-statement.md` § *Where we actually
differ* #2 states our edges are dedicated and non-fungible — there is no shared pool to starve. The
transferable lesson is narrower and still binding: *any* single non-deterministic component in a
control path is a fleet-wide single point of failure. Our version of that component is the
`PreToolUse` hook (E8), not a scheduler.

**C. Multi-tenant machinery is premature.** Roughly half of Paperclip's recent migrations concern
company scoping, JWT keys and tenant isolation. We are single-operator today, and
`problem-statement.md` warns that "Nothing may assume a single operator." Both are true: the *data
model* should carry an edge/owner axis from the start; the *isolation machinery* should not be built
until a second operator exists. **Distinguishing these is the whole trick** — the cheap part is a
column, the expensive part is enforcement.

**D. Coding-agent parallelism evidence cuts against fan-out here.** Anthropic states that "most
coding tasks involve fewer truly parallelizable tasks than research" [S19] *(directional — rendered
page)*. Our first edge is the coding edge. Evidence that a research fan-out benefits from N subagents
does not license a coding fan-out.

**E. Sample size and selection bias.** Two products supply most of the operational evidence, and one
of them (`bernstein`) supplies most of *that*. It is unusually candid — its release notes describe
its own bugs at a level of detail almost nobody publishes — which is exactly why it dominates, and
exactly why it may not be representative. **A codebase that documents 40 bugs is not worse than one
that documents 2; it is more legible.** Do not read failure density as quality.

**F. Closed issues are not fixed issues.** [S16] and [S17] are both `closed`; #28827 carries the
label `duplicate`. Their *reports* are evidence; their *current* status is not. T1 in §8 exists
because of this.

### 6.3 The case against acting on this paper at all

Stated because a paper with no case against its thesis is advocacy.

1. **Most of these failures need a fleet to occur, and there is no fleet.** One operator, one
   machine, dispatches launched by hand. E3, E5, E9 and E10 are all failure modes of *unattended
   volume*. Building guards for volume that does not exist is the over-engineering
   `code-style.md` warns about, and every guard added is a surface that can itself rot (§2.4 —
   three dead guards in one codebase).
2. **Several mitigations are pure loss if the Temporal port subsumes them.** E3 (wall-clock cap),
   E4 (schedules), and part of E10 (dedupe) are things the substrate supplies. Building them in bash
   first is ~7 operator-hours that Temporal deletes. The counter-argument is that E1 and E2 are
   *not* subsumed — Temporal cannot refresh an OAuth token or verify a PR exists — so those two are
   safe to build now regardless of the port's timing.
3. **The evidence is descriptive, not causal.** Nothing here establishes *rates*. bernstein records
   that a `--plan-only` bug was "Reproduced twice"; nobody publishes how often credentials expire per
   thousand unattended hours. Every cost in §4.2 is derived, and a mitigation sized against an
   unmeasured rate can be exactly wrong in either direction.
4. **The strongest single number is n=1.** "2 of 40 claimed" comes from one pilot, one team, one
   configuration, in a document written by the party that replaced that design. It is the most
   decision-relevant figure in the paper and it has no independent replication. MAST [S8a] supports
   the *category* ("task verification" is one of three root categories) but does not corroborate the
   rate.

---

## 7. The ranking — worst first

**This is the paper's primary deliverable.** Ordered by (likelihood on our current trajectory) ×
(cost of late discovery), not by severity in the abstract. *(derived throughout; each row's evidence
and mitigation are in §4.2.)*

| Rank | Exposure | Why here | Mitigation | Cost | Subsumed by Temporal? |
|---|---|---|---|---|---|
| **1** | **E1 — credential expiry / wipe at the edge** | Certain to occur; our auth model *requires* the failing configuration; discovery latency is "hours" [S17]; and the vendor's own suggested fix (API key) breaks the affordability thesis | Extend the existing `probe_stderr` grep class + distinct exit code + notify | ~2h | **No** |
| **2** | **E2 — a run emits the right token without doing the work** | The one measured rate in the corpus (2/40) is about this; it is the *pre*condition for an unattended driver, since a driver routing on a false completion compounds it | Fetch the pointer; require a re-readable external artifact per contract | ~4h | **No** |
| **3** | **E8 — the only live safety control could silently stop firing** | Blast radius is unbounded (autonomous runs pass `--dangerously-skip-permissions`), the roadmap already flags a change that would strip it, and this exact class killed a shipped classifier [S2, #1850] | Wiring test: fixture issues a known-denied command, asserts denial | ~3h | No |
| **4** | **E4 — no missed-window policy** | It is an open roadmap item, it is cheap, and §5.2 shows the current assumption is backwards for the job we actually schedule | Skip-by-default + widen the window for window-scoped jobs + consecutive-miss alarm | ~3h | Partly |
| **5** | **E3 — no stall detection on a child** | Cheap, and the corpus is unanimous that every system needs a hard backstop; today a hung child is unbounded | `timeout(1)` per child, sized per child | ~2h | **Yes** |
| **6** | **E6 — `claude` binary drift** | The *recording* half is ~1h and makes drift minable by machinery we already run; the gating half can wait for evidence | Stamp `claude --version` into every run log now | ~1h | No |
| **7** | **E9 — no ceiling on concurrent dispatches** | Already observed once (rate-limit exhaustion in half a metered period), and the flat-rate translation is the non-obvious part | Concurrency ceiling, not a USD cap | ~2h | Partly |
| **8** | **E5 — orphaned worktrees / disk** | Slow-burning, easy to detect late, trivially fixed | Sweeper on the `gh-monitor` timer; note `git worktree prune` is insufficient | ~2h | No |
| **9** | **E10 — incident storms** | Not live until a driver files issues automatically; adopting the two-level key *now* is nearly free and avoids Paperclip's DROP/CREATE cycle | Two-level origin fingerprint convention | ~2h | Partly |
| **10** | **E11 — prior-run text as an injection surface** | Lowest likelihood today, but retrofit cost rises steeply once multiple edges write to shared memory | Provenance-tag machine-written comments | ~3h | No |
| **—** | **E7 — withdrawn.** Falsified against the shipped scripts; kept in §4.2 so it is not re-derived | — | — | — | — |

**If only three things are done: E1, E2, E8 — about nine operator-hours, none of it deleted by the
Temporal port.** They are, respectively, the failure that stops the fleet, the failure that makes the
fleet lie, and the failure that makes the fleet unsafe. Everything below rank 4 can wait for evidence
that the corresponding volume exists.

---

## 8. Citations

### 8.1 Negative findings and their search method

Per §3's requirement that a negative finding state how it was searched.

**N1. No published postmortem was located for an autonomous coding-agent fleet run on *flat-rate
subscription* credentials at the edge.** Searched via: GitHub REST issue search on
`anthropics/claude-code` (headless/OAuth/unattended terms); web search on unattended-automation +
token-expiry phrasings; and forward-reading from [S16]/[S17]'s linked duplicates. What exists is
**bug reports**, not postmortems — [S16], [S17] and their siblings. **This absence is a risk signal,
not a safety signal:** the configuration is new enough that nobody has published a retrospective on
operating it at scale, which means our failure modes here will be discovered by us.

**N2. No first-party source was located stating how often a `claude -p` run reports completion
without completing.** Searched via: arXiv API (`cs.SE`, agent self-report / false-claim phrasings —
returned nothing on topic, see the query in §8.2), bernstein's release notes and ADRs, and Paperclip's
roadmap. The nearest measurement anywhere is [S5]'s "2 real code commits out of 40 it claimed," which
is one pilot with a different harness. **The rate for our harness is unmeasured** → T2.

**N3. The exact Paperclip migration count is unverified.** The GitHub contents API listing returned
94 entries (`0000`–`0094`); the dispatch brief said "200+". The API caps directory listings at 1000
entries, so truncation is unlikely, but the fetch was rendered through a summarizing model and the
count was not independently recomputed. Nothing in this paper depends on the total; the four
migrations quoted were fetched individually as raw SQL. Stated as an open discrepancy rather than
resolved in either direction.

**N4. AWS's retry-storm guidance could not be fetched.** `aws.amazon.com/builders-library/timeouts-
retries-and-backoff-with-jitter/` 301-redirects to `builder.aws.com`, which returned a page header
with no body (JS-rendered). **No retry-storm claim in this paper rests on it** — the retry evidence
used is bernstein's own [S22b] and Temporal's activity-retry behaviour [S14]. Recorded so a future
refresh does not re-spend the fetch.

**N5. Six bernstein docs returned summaries rather than raw text**, despite `raw.githubusercontent.com`
URLs: `WHY_DETERMINISTIC.md`, `deadlock-detection.md`, `context-degradation-detector.md`,
`MAX_TURNS.md`, `schedule.md`, `cost-anomaly-detection.md`. One (`deadlock-detection.md`) explicitly
declined verbatim reproduction. Every claim drawn from these six is marked **directional** and quoted
only where the fetch itself presented a span as exact. The load-bearing bernstein claims (§2.1, §2.3.6,
§2.7.4, §2.2.6) all come from fetches that returned full raw markdown.

**N6. Nothing was located on clock/timezone failures in scheduled agent work.** Searched via: the
Temporal troubleshooting directory listing (7 files, none on time skew), bernstein's operations
directory listing (107 files, none named for clocks), and web search. The gap may be real (schedulers
own this and it rarely surfaces) or may reflect an inadequate search; stated as unresolved.

### 8.2 Source list

**Primary — `bernstein` (Apache-2.0), raw first-party (high volatility)**

- [S0] Repository metadata, GitHub REST API. `default_branch: "main"`, 788 stars, 76 open issues,
  created `2026-03-22T14:52:26Z`, pushed `2026-08-04T19:26:33Z`, `Apache-2.0`.
  https://api.github.com/repos/sipyourdrink-ltd/bernstein
- [S1b] `CHANGELOG.md` — points to `docs/release-notes/`; per-version pages, one per tag.
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/CHANGELOG.md
- [S2] `docs/release-notes/unreleased.md` — **the densest failure record in the corpus** (~75KB;
  `Security` / `Added` / `Changed` / `Fixed`). All `#NNNN` refs in this paper index its entries.
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/release-notes/unreleased.md
- [S3] ADR-006, *No Embedded LLM in the Orchestrator* (Accepted, 2026-03-22).
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/decisions/006-no-embedded-llm.md
- [S4] ADR-005, *Short-Lived Agent Lifecycle* (Accepted, 2026-03-22; supersedes ADR-001).
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/decisions/005-short-lived-agents.md
- [S5] ADR-001, *Agent Lifecycle* — pilot metrics appendix (12 named + 5 phantom agents, ~47h,
  737+ tickets, 283/0, 2-of-40, 138 hunger-spam messages, 3-of-12 reliable).
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/decisions/001-agent-lifecycle.md
- [S6] `docs/operations/agent_crash_loop.md` — respawn budget 3/60s, backoff `500ms*attempt` cap 5s,
  parked state, operator-only resume.
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/agent_crash_loop.md
- [S7] `docs/operations/abandonments.md` — `ABANDONED` terminal invariant, closed reason taxonomy,
  `BLOCKED_BY_ABANDON` cascade.
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/abandonments.md
- [S20] `docs/architecture/deadlock-detection.md` — *(summarized fetch; verbatim declined)* detector
  present, `record_lock_wait()` only in unit tests, production graph empty. **Directional.**
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/architecture/deadlock-detection.md
- [S21] `docs/operations/cost-anomaly-detection.md` — *(summarized fetch)* burn-rate only:
  `budget_warn_pct` 60%, `budget_stop_pct` 90%; other rules implemented, unit-tested, not invoked.
  **Directional.**
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/cost-anomaly-detection.md
- [S22b] `docs/operations/retry-budget.md` — criterion-aware retry budget; the identical-retry
  problem stated in the doc's own opening.
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/retry-budget.md
- [S23] `docs/operations/MAX_TURNS.md` — *(summarized fetch)* explicit `max_turns` 1–10000, default
  computed from task complexity and model speed. **Directional.**
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/MAX_TURNS.md
- [S24] `docs/operations/schedule.md` — *(summarized fetch, with spans presented as exact)* misfire
  policy `skip` (default) vs `catch_up` (cap 16); counterfactual receipts. **Directional.**
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/schedule.md
- [S27] `docs/architecture/WHY_DETERMINISTIC.md` — *(summarized fetch)* the `rag_challenge` pilot
  narrative; verification from concrete signals rather than agent claims. **Directional**; the
  load-bearing version of the same content is [S3]/[S4], which fetched raw.
  https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/architecture/WHY_DETERMINISTIC.md

**Primary — Paperclip (MIT), raw first-party (high volatility)**

- [S10] `ROADMAP.md` (raw). Milestones incl. *Enforced Outcomes (watchdogs, recovery actions, review
  gates)* and *Self-healing runs & automatic recovery*.
  https://raw.githubusercontent.com/paperclipai/paperclip/master/ROADMAP.md
- [S10b] Repository metadata: `default_branch: "master"`, 75,610 stars, 5,060 open issues, created
  `2026-03-02`, pushed `2026-08-04`. https://api.github.com/repos/paperclipai/paperclip
- [S11] `packages/db/src/migrations/0069_liveness_recovery_dedupe.sql` (raw SQL).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/migrations/0069_liveness_recovery_dedupe.sql
- [S12] `.../0070_active_run_output_watchdog.sql` (raw SQL).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/migrations/0070_active_run_output_watchdog.sql
- [S25] `.../0062_routine_run_dispatch_fingerprint.sql` (raw SQL).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/migrations/0062_routine_run_dispatch_fingerprint.sql
- [S26] `.../0064_issue_thread_interaction_idempotency.sql` (raw SQL).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/migrations/0064_issue_thread_interaction_idempotency.sql

**Primary — Temporal, raw first-party (medium volatility)**

- [S1] `docs/troubleshooting/schedule-missed-actions.mdx` (raw MDX) — Catchup Window, overlap
  policies, `missedCatchupWindow`/`overlapSkipped`/`bufferDropped`, root causes, Backfill.
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/troubleshooting/schedule-missed-actions.mdx
- [S13] `temporalio/rules` → `rules/TMPRL1100.md` (raw) — non-determinism on replay; patching,
  versioning, reset. https://raw.githubusercontent.com/temporalio/rules/main/rules/TMPRL1100.md
- [S14] `docs/troubleshooting/blob-size-limit-error.mdx` (raw MDX) — 2 MB payload / 4 MB gRPC, and
  the per-case wedge behaviours.
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/troubleshooting/blob-size-limit-error.mdx
- [S22] `temporalio/temporal` → `common/dynamicconfig/constants.go` (raw Go) —
  `HistoryCountLimitError 50*1024`, `HistorySizeLimitError 50*1024*1024`, `BlobSizeLimitError
  2*1024*1024`, `BlobSizeLimitWarn 512*1024`.
  https://raw.githubusercontent.com/temporalio/temporal/main/common/dynamicconfig/constants.go

**Primary — Anthropic Claude Code issue tracker, GitHub REST JSON (high volatility)**

- [S16] Issue #28827, *OAuth token refresh fails in non-interactive/headless mode*, created
  2026-02-26, state `closed`, label `duplicate`. Body quoted verbatim from the API response.
  https://github.com/anthropics/claude-code/issues/28827
- [S17] Issue #29896, *OAuth credentials silently wiped on failed token refresh — long-running agents
  lose auth*, created 2026-03-01, state `closed`. Body quoted verbatim from the API response.
  https://github.com/anthropics/claude-code/issues/29896

**Literature — arXiv Atom API (`export.arxiv.org/api/query?id_list=…`), abstracts (low volatility)**

- [S8a] Cemri, M., Pan, M. Z., Yang, S., Agrawal, L. A., Chopra, B., Tiwari, R., Keutzer, K.,
  Parameswaran, A., Klein, D., Ramchandran, K., Zaharia, M., Gonzalez, J. E., & Stoica, I. (2025).
  *Why Do Multi-Agent LLM Systems Fail?* arXiv:2503.13657 (v1 2025-03-17; updated 2025-10-26).
  https://arxiv.org/abs/2503.13657
- [S8] Backlund, A., & Petersson, L. (2025). *Vending-Bench: A Benchmark for Long-Term Coherence of
  Autonomous Agents.* arXiv:2502.15840. https://arxiv.org/abs/2502.15840
- [S9] Laban, P., Hayashi, H., Zhou, Y., & Neville, J. (2025). *LLMs Get Lost In Multi-Turn
  Conversation.* arXiv:2505.06120. https://arxiv.org/abs/2505.06120
- [S15] Kwa, T., West, B., Becker, J., et al. (2025). *Measuring AI Ability to Complete Long Software
  Tasks.* arXiv:2503.14499 (v1 2025-03-18; updated 2026-07-10). https://arxiv.org/abs/2503.14499

**Vendor engineering posts — rendered pages, quoted conservatively (directional)**

- [S18] Cognition, *Don't Build Multi-Agents* (Walden Yan).
  https://cognition.com/blog/dont-build-multi-agents
- [S19] Anthropic, *How we built our multi-agent research system.*
  https://www.anthropic.com/engineering/multi-agent-research-system

**Internal evidence (not citations — recorded for traceability)**

- `docs/standards/architecture/system-overview.md` — "A parent calls no model."; the seam table;
  "`block-dangerous.sh` fails closed"; the `PreToolUse` hook as the only live control.
- `docs/standards/architecture/problem-statement.md` — § *Affordability is the enabler*; § *Where we
  actually differ* #2; "Nothing may assume a single operator."
- `scripts/workflows/activities/run-claude.sh` — the `error_max_turns` gate (~L167), the completion
  contract (~L194–219), the rate-limit probe grep (~L84).
- `scripts/workflows/children/review-pr.sh` L186 — `COMPLETION_PATTERN='^VERDICT: (MERGE|HOLD - …)$'`.
- `scripts/workflows/revision.sh` L309–325 (the one-loop-back bound and its stated justification),
  L345–357 (the loop-back invoking `run_refine … --correction-pass`) — **the artifacts that
  falsified this paper's draft E7.**
- `scripts/workflows/children/revision-refine.sh` L79–82 — the `--correction-pass` contract: "a
  review-pr disposition comment with a runway already exists on this PR, and closing it is this
  run's job."
- `scripts/workflows/review-runs.sh` L24, L207 — `--days` default 7; `find … -mtime "-${DAYS}"`.
- `docs/standards/research/research_standard.md` §5 — the date-based refresh gate.
- `docs/standards/architecture/research/raw/convergence_stopping.md` — stopping rules, not re-derived.

*Sourcing posture: every GitHub artifact was fetched from `raw.githubusercontent.com` or the REST
API rather than a blob page; both surveyed repositories' `default_branch` was confirmed via the
repository API before any raw fetch, so no 404 in this sweep was recorded as an absence. arXiv
metadata came from the Atom API, not from rendered `abs` pages. Six raw fetches nonetheless returned
summaries (N5) and every claim from them is downgraded accordingly.*

---

## 9. Test plan — what research cannot settle

Ordered by decision value. Each names why research stopped.

**T1. Measure the real credential lifetime and failure shape on our own edge.**
*Because:* [S16]/[S17] are reports against Claude Code 2.1.59/2.1.63, both closed, one as a
duplicate. Whether current behaviour still 401s, still wipes, and on what interval is **unverified**,
and E1 is rank 1 in §7.
*Design:* run a `claude -p` loop unattended for 24h on a Max-auth machine with no interactive session
present; log every non-zero exit with stderr and the `~/.claude/.credentials.json` mtime and size.
*Reads out:* whether E1's mitigation is a probe (expiry) or a backup-and-restore (wipe) — different
fixes.
*Fails if:* no failure occurs in 24h — which is also decisive and demotes E1.

**T2. Measure our own false-completion rate.**
*Because:* N2 — the only number anywhere is [S5]'s "2 of 40" from a different harness, and E2 is
rank 2 on that borrowed number.
*Design:* over the last N merged workflow PRs, check for each declared `COMPLETION_PATTERN` match
whether the referenced artifact exists and matches the run (PR URL resolves, head SHA matches the
worktree's last commit, `review-pr`'s `VERDICT:` has a corresponding posted comment).
*Reads out:* whether E2 is a live defect or a theoretical one; and whether the PR-URL contracts are
already sufficient, which would narrow E2 to `review-pr` alone.

**T3. Determine the p99 wall-clock duration of each child.**
*Because:* E3's mitigation is a `timeout(1)` value and the corpus supplies two numbers from a
different harness (30 min fresh-agent kill [S4], 90 min reaper cap [S2]) that we should not copy.
*Design:* extract durations from the existing JSONL run logs per workflow.
*Reads out:* the cap per child. **Cheap, uses data we already have, should run first.**

**T4. Determine whether a hung `claude -p` is distinguishable from a slow one, from outside.**
*Because:* this is the exact question that cost bernstein two bugs and a 3-tick cap [S2, #3058], and
Paperclip four schema columns [S12]. Our children stream JSONL, so we may have an *output-progress*
signal they had to add.
*Design:* instrument a deliberately-hung child; observe whether stream-json line arrival stops while
the process lives.
*Reads out:* whether E3 needs only a wall clock, or a wall clock plus an output-staleness check.

**T5. Measure `claude` CLI version spread across machines, and whether it correlates with failures.**
*Because:* E6's gating half is not justified without evidence; the recording half is ~1h.
*Design:* stamp `claude --version` into run logs; after four weeks, have `review-runs.sh` group
failures by version.
*Reads out:* whether binary drift is a real fleet variable here or a borrowed worry from a project
supporting 40+ adapters [S2].

**T6. Verify the `PreToolUse` hook actually fires during an autonomous dispatch.**
*Because:* E8, and because three separate controls in one surveyed codebase were wired-and-dead
(§2.4). Research cannot answer whether ours is live; only an execution can.
*Design:* dispatch a fixture task whose prompt requires a known-denied command; assert denial appears
in the run log.
*Reads out:* whether E8 is a latent defect today or purely a regression guard for later.

**T7. Confirm whether `git worktree` accumulation is real on our machines.**
*Because:* E5 is inferred from bernstein's four teardown paths [S2, #2996], not observed here.
*Design:* count worktrees and bytes under `.claude/worktrees/` across machines; correlate against
dispatch counts in the logs.
*Reads out:* whether a sweeper is needed now or is premature.

**Not settleable by any of the above, and recorded as such:** whether the failures this paper did not
find are the ones that will matter. Every source here is a project that survived long enough to
document its scars. The designs that failed *and were abandoned without a writeup* are invisible to
this method, and there is no way to bound how large that set is.
