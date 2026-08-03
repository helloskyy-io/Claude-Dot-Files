# Durable Execution as a Substrate for Long-Horizon AI Agents

*Raw research synthesis for §3 Proposed Architecture. Compiled 2026-07-23.*

## 1. Durable Execution Primer

Durable execution is a runtime discipline in which the state of a computation is not held in process memory but persisted as an append-only log of events, from which the computation can be reconstructed byte-for-byte after any failure. The architectural pattern behind it is **event sourcing**: every state transition is stored as an immutable event, and current state is derived by replaying the event stream from the beginning ([Temporal event-history docs](https://docs.temporal.io/encyclopedia/event-history/event-history-python); [Temporal architecture README](https://github.com/temporalio/temporal/blob/main/docs/architecture/README.md)). A worker process crashes, a container is evicted, an availability zone burns — the event history survives, and a fresh worker resumes the computation at exactly the point it stopped, without re-executing side effects that already completed.

The guarantee is delivered through **deterministic replay**. Workflow code is required to be a pure function of its inputs and its history; every source of nondeterminism (clocks, random numbers, network calls, filesystem access) is externalized into *activities* whose results are recorded to the event log the first time they run. On replay, the workflow re-executes from the top, but activity results are served from history instead of being recomputed. This is what distinguishes durable execution from "checkpoint and restart" schemes: the runtime does not merely resume from the last snapshot, it *reconstructs* the exact program state that existed at the moment of failure ([Temporal: Beyond State Machines](https://temporal.io/blog/temporal-replaces-state-machines-for-distributed-applications)).

## 2. Temporal's Specific Model — Why It Fits AI Agents

Temporal — the successor to Uber's Cadence, built by Cadence's original authors — implements this pattern with a specific decomposition that maps cleanly onto agent architectures ([Cadence vs Temporal, Rosetta Digital](https://rosettadigital.com/cadence-vs-temporal/)). Three primitives do the work:

- **Workflows** are the deterministic orchestrator. They express the agent loop — plan, call LLM, dispatch tool, observe, iterate — as ordinary code, but must not touch the outside world directly.
- **Activities** are the non-deterministic edge. Every LLM call, every tool invocation, every retrieval-augmented lookup is an activity with its own retry policy (`max_attempts`, exponential backoff, retriable-vs-terminal error classification), its own timeouts (`start_to_close`, `heartbeat`, `schedule_to_close`), and its own idempotency key derived from the workflow ID plus operation ID ([Claude Lab production guide](https://claudelab.net/en/articles/api-sdk/claude-agent-sdk-temporal-durable-ai-workflows-production-guide)).
- **Signals, queries, and timers** let a workflow suspend indefinitely — waiting for a human review, a rate-limit window, or a scheduled reflection cycle — without holding a live process. A `workflow.wait_condition` releases worker memory entirely; when the external signal arrives, a worker is scheduled, replays history, and resumes.

For long-running agents this is nearly a shape-match. A multi-day reflective self-improvement loop looks precisely like a Temporal workflow: bounded orchestration logic that persists across hundreds of LLM calls, coordinates external tool executions, waits on human-in-the-loop signals, and can be inspected — at any point, live or post-mortem — by reading the workflow's event history through the standard query API.

## 3. 2026 AI-Specific Developments — The Convergence Timeline

The industry moved decisively in 2026 to make durable execution the default substrate for production agents.

**April 2026.** Temporal and Google published a native integration for the [Agent Development Kit (ADK)](https://temporal.io/blog/google-adk-temporal-integration-bts), announced April 20. Rather than wrapping ADK agents as HTTP services, the integration pushes *every* LLM call and *every* tool invocation into its own Temporal activity via a `TemporalModel` wrapper and an `activity_tool` helper. The blog frames the agentic loop as "a deterministic sequence of non-deterministic things" and required a PR to ADK itself to introduce abstract `time` and `uuid` providers so the loop could execute deterministically inside a Temporal workflow (all four details from the Temporal blog cited at the start of this paragraph). The integration is marked experimental as of Temporal Python 1.24.0. A secondary [architectural analysis](https://reliabilitywhisperer.substack.com/p/architectural-analysis-google-adk) covers the same integration independently. *[Verified 2026-07-27: footnote corrected — the quote and PR detail are first-party from the Temporal blog, not from the secondary analysis.]*

**Replay 2026 (Temporal's annual conference).** The [Replay 2026 announcements](https://temporal.io/blog/replay-2026-product-announcements) — reported by [The New Stack](https://thenewstack.io/temporal-replay-2026-news/) — bundled the following AI-relevant releases:
- **Serverless Workers** on AWS Lambda (Pre-release). Workers are invoked, scaled, and gracefully drained by workload signals, eliminating the need to run always-on worker fleets for spiky agent traffic.
- **Workflow Streams** (Public Preview). Durable streaming built on Signal and Update primitives, sized for LLM token batches and UI-facing progress updates.
- **External Payload Storage** (Public Preview). Large LLM responses spill to S3-backed storage; only references land in event history, keeping histories bounded despite tokenized traffic.
- **OpenAI Agents SDK integration** announced as generally available at Replay 2026, and packaged with a [Durable AI Agents Bundle](https://temporal.io/pages/durable-ai-agent-bundle) — a curated technical guide, code demo, and expert-session series. *[Verified 2026-07-27: two first-party Temporal pages disagree on maturity — the Replay blog says GA, the bundle page still lists Public Preview. Treat the maturity label as unsettled; the existence of the integration is not in dispute.]*
- **Standalone Activities** — activities can now run independently of a workflow, useful for out-of-band tool executions that still need Temporal's retry and observability semantics.

**Claude Agent SDK integration.** The [Anthropic Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) exposes a Python-native agentic loop over Claude Code, with hooks, custom in-process MCP tools, and both one-shot `query` and bidirectional `ClaudeSDKClient` interfaces. **First-party Claude ↔ Temporal integration lags behind OpenAI and Google.** A November 2025 [community forum request](https://community.temporal.io/t/support-for-claude-agent-sdk/18716) for Claude Agent SDK support remains unanswered, and the Replay 2026 announcements do not mention Anthropic by name. What exists instead is:
- The [`temporalio/claude-temporal-plugin`](https://github.com/temporalio/claude-temporal-plugin), a Claude Code plugin (Public Preview) that packages the temporal-developer skill for Claude Code users — this is *developer-side* tooling to help humans write Temporal apps inside Claude Code, not a runtime integration between an agent and Temporal.
- Community-authored production guides — most prominently the [Claude Lab article](https://claudelab.net/en/articles/api-sdk/claude-agent-sdk-temporal-durable-ai-workflows-production-guide) — that document the manual integration pattern: wrap every Claude API call in an activity, use `continue-as-new` to bound history growth, apply saga compensation on partial failures, and observe an approximate thirty-minute task-duration threshold below which the discipline is net cost. *[Verified 2026-07-27: a previously listed item — "set the client's internal retries to zero so Temporal owns retry policy" — was removed. It does not appear in the cited guide. The underlying concern is real and is now stated as the paper's own inference in the nested-retry limitation, not as a claim attributed to this source.]*

The convergence is real but asymmetric: OpenAI and Google now ship durable execution as a supported extension of their agent SDKs; Claude requires hand-rolled integration against public patterns. This gap is a load-bearing observation for the paper — it means the "obvious" substrate for a Claude Code-based self-improvement loop is not yet a paved road.

## 4. Similar Systems — Brief Comparative Landscape

- **Cadence** (Uber, open-source). Temporal originated as a 2019 fork of Cadence; both remain actively maintained, and the projects share the same event-sourcing model ([Cadence vs Temporal](https://cadenceworkflow.io/faq/cadence-vs-temporal)). *[Verified 2026-07-27: "direct predecessor / superseded" framing corrected. The cited FAQ explicitly frames the two as coequal siblings and states neither is objectively superior — it does not support a supersession claim.]*
- **Restate.dev.** Positions itself as durable execution for *entire systems* rather than single workflows — per-key session state, RPC, messaging, queuing, and workflows in one runtime. Single-binary deployment, P99 completion latency the vendor states stays below 170 ms, explicit `ctx.run()` side-effect model. Argues that agent platforms are systems, not single workflows: "sessions, state, inter-service calls, queues, approvals do not naturally fit the workflow mold" ([Restate vs Temporal](https://www.restate.dev/vs/temporal); [ZenML alternatives roundup](https://www.zenml.io/blog/temporal-alternatives)). *[Verified 2026-07-27: latency corrected from "sub-100ms" — the cited page says P99 below 170 ms. An embedded-RocksDB claim was removed; it appears on Restate's architecture docs, not the cited page. Note the cited page is vendor competitive-marketing, not neutral analysis.]*
- **Inngest.** TypeScript-first, `step.run`/`step.sleep`/`waitForEvent` primitives, event-driven, ships an AgentKit multi-agent framework. Optimized for developer-experience minimums ("minutes to a first durable function") and small teams; pricing scales per-step which can bite on high-fan-out agent traffic ([Inngest vs Temporal](https://www.inngest.com/compare-to-temporal)).
- **LangGraph durable mode.** LangGraph's checkpointer (Memory, SQLite, or Postgres) persists graph state *between nodes* but not *inside* them — a node halfway through a large loop loses its intermediate work. It also does not enforce activity-level idempotency, so non-idempotent tool calls inside a node can double-fire on resume ([Vadim's blog](https://vadim.blog/durable-execution-agents-that-survive-failure-and-resume-where-they-left-off)). This is *checkpointing*, not durable execution in the Temporal sense. *[Verified 2026-07-27: the LangChain comparison page was removed from this citation — it discusses neither the checkpointer internals nor the idempotency gap. The claim rests on Vadim's blog alone, and independently on the Diagrid teardown cited in §5.]*

## 5. What Durable Substrate Provides

Enumerated as the properties a paper's Proposed Architecture section can rely on:

1. **Crash-recovery without duplication.** The event history is the source of truth; on failure a new worker replays the log and resumes at the exact boundary, so already-committed side effects (LLM calls made, tools invoked, emails sent) are not re-executed ([Zylos research on agent runtimes](https://zylos.ai/research/2026-04-24-durable-execution-agent-runtimes/)).
2. **Verifiability via event history.** Every decision the agent made — every prompt, every model response, every tool argument, every retry — is recorded in order. Post-hoc audit, replay for debugging, and time-travel to any prior state are first-class. This is what makes the substrate suitable for a *reflective* self-improvement loop: reflection has ground-truth to reflect on.
3. **Extended time horizon.** Workflows can suspend across hours or days at zero live-process cost. Waiting for a scheduled reflection cycle, a rate-limit window, or a human review is a `wait_condition` call, not a cron-and-database dance.
4. **Human-in-the-loop primitives.** Signals and queries turn HITL from an ad-hoc pattern into a runtime feature. An approval gate spanning a weekend is the same code shape as one spanning a millisecond.
5. **Rate-limit-aware coordination.** Timers and per-activity retry policies with exponential backoff and jitter give the substrate an honest answer to LLM provider rate limits; a saturated queue backs off deterministically rather than melting into a retry storm.
6. **Idempotent tool execution.** Activity idempotency keys plus the "wrap every external call" discipline mean tool retries are safe by construction — the failure mode of double-charging a customer or double-sending an email is *eliminated at the substrate*, not managed in application code ([Claude Lab guide](https://claudelab.net/en/articles/api-sdk/claude-agent-sdk-temporal-durable-ai-workflows-production-guide)).
7. **Compensable multi-step operations.** Saga-pattern compensation activities let partially-completed multi-step plans unwind cleanly on downstream failure.
8. **Observability that is also authoritative.** Standard workflow query APIs expose live state; event histories are the same artifact used for replay. Debugging traces and the runtime record are the same object.

## 6. When Durable Is Not Needed — Honest Boundary Analysis

Durable execution is not free. The costs and boundary conditions:

- **Short, in-process tasks.** A sub-minute agentic task with no external side effects and no HITL gate does not benefit from an event log. The determinism discipline, the activity-per-side-effect decomposition, and the operational overhead of running a Temporal cluster are pure cost against that workload ([Claude Lab guide](https://claudelab.net/en/articles/api-sdk/claude-agent-sdk-temporal-durable-ai-workflows-production-guide) notes the ~30-minute threshold as a rough heuristic).
- **Pure exploration / interactive chat.** Conversational agents where the user is present for the whole run and reruns are cheap on failure gain less from durable substrate than long-horizon autonomous agents do.
- **Prototypes and research spikes.** The friction of deterministic workflow authoring — no `datetime.now()`, no `random.random()`, no unbounded imports inside workflow code, versioning discipline, `patched()` calls — is a tax that will slow experimentation. LangGraph's in-memory mode is the right shape for a two-week research loop, even if it is the wrong shape for a two-month production loop.
- **Systems where the *system* is durable, not just the workflow.** Restate's core critique applies: multi-tenant agent platforms with heavy per-session state and dense service-to-service RPC may fit Restate's model better than Temporal's ([Restate vs Temporal](https://www.restate.dev/vs/temporal)).
- **Durable execution does not solve product-layer problems.** It does not give product managers a visual editor, does not answer "which node in the workflow is currently blocked from the customer's perspective," and does not provide governed iteration boundaries for non-engineers. Runtime dashboards are engineer-facing artifacts, not product-facing ones ([Workflow Builder critique](https://www.workflowbuilder.io/blog/why-durable-execution-alone-wont-save-your-ai-agent)).
- **Version-drift hazards.** Replays diverge if model versions, prompts, tool schemas, or runtime images change without careful record-keeping. Durable substrate makes the *runtime* deterministic but requires application-level discipline to keep the *dependencies* deterministic ([Zylos research](https://zylos.ai/research/2026-04-24-durable-execution-agent-runtimes/)).

The honest positioning for the paper: durable execution is a necessary condition for verifiable multi-day self-improvement loops, but is not sufficient on its own. Version-pinning discipline, an explicit reflection schema layered above the event history, and a governed-iteration surface are all still required.

## 7. Citations

- [Announcing new Temporal capabilities from Replay 2026 — Temporal blog](https://temporal.io/blog/replay-2026-product-announcements)
- [Durable AI Agents Bundle — Temporal](https://temporal.io/pages/durable-ai-agent-bundle)
- [Temporal reveals a serverless option for its Durable Execution platform — The New Stack](https://thenewstack.io/temporal-replay-2026-news/)
- [Inside the Google ADK and Temporal integration — Temporal blog](https://temporal.io/blog/google-adk-temporal-integration-bts)
- [Temporal plugin for ADK — Google ADK docs](https://adk.dev/integrations/temporal/)
- [Architectural Analysis: Google ADK + Temporal Integration — Reliability Whisperer](https://reliabilitywhisperer.substack.com/p/architectural-analysis-google-adk)
- [Building Fault-Tolerant Long-Running AI Workflows with Claude Agent SDK × Temporal.io — Claude Lab](https://claudelab.net/en/articles/api-sdk/claude-agent-sdk-temporal-durable-ai-workflows-production-guide)
- [Claude Agent SDK for Python — anthropics/claude-agent-sdk-python (GitHub)](https://github.com/anthropics/claude-agent-sdk-python)
- [Claude Code plugin for Temporal — temporalio/claude-temporal-plugin (GitHub)](https://github.com/temporalio/claude-temporal-plugin)
- [Support for Claude Agent SDK? — Temporal Community Forum](https://community.temporal.io/t/support-for-claude-agent-sdk/18716)
- [Basic Agentic Loop with Claude and Tool Calling — Temporal docs](https://docs.temporal.io/ai-cookbook/agentic-loop-tool-call-claude-python)
- [Temporal Workflow Execution overview — Temporal docs](https://docs.temporal.io/workflow-execution)
- [Event History walkthrough (Python) — Temporal docs](https://docs.temporal.io/encyclopedia/event-history/event-history-python)
- [Temporal server architecture README — temporalio/temporal (GitHub)](https://github.com/temporalio/temporal/blob/main/docs/architecture/README.md)
- [Temporal: Beyond State Machines for Reliable Distributed Applications — Temporal blog](https://temporal.io/blog/temporal-replaces-state-machines-for-distributed-applications)
- [LangGraph vs Temporal — LangChain](https://www.langchain.com/resources/langgraph-vs-temporal)
- [Durable Execution in LangGraph — Vadim's blog](https://vadim.blog/durable-execution-agents-that-survive-failure-and-resume-where-they-left-off)
- [Restate vs Temporal — Restate](https://www.restate.dev/vs/temporal)
- [Temporal alternatives roundup — ZenML](https://www.zenml.io/blog/temporal-alternatives)
- [Inngest vs Temporal — Inngest](https://www.inngest.com/compare-to-temporal)
- [Cadence vs Temporal — Cadence](https://cadenceworkflow.io/faq/cadence-vs-temporal)
- [Cadence vs Temporal — Rosetta Digital](https://rosettadigital.com/cadence-vs-temporal/)
- [Durable Execution for AI Agent Runtimes: Checkpointing, Replay, and Recovery — Zylos Research](https://zylos.ai/research/2026-04-24-durable-execution-agent-runtimes/)
- [Why durable execution alone won't save your AI agent — Workflow Builder](https://www.workflowbuilder.io/blog/why-durable-execution-alone-wont-save-your-ai-agent)
