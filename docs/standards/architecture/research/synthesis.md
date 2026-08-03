> **Provenance:** carried over from the CSCI-6905.604 research project (`research_project/PRODUCT_NOTES.md`), 2026-08-03.
> That repo is slated for deletion; this file was explicitly marked as needing to survive it, and named a
> `development/research/` entry in a planning repo as its candidate home. This is that home.
>
> **It is not yet a standard-conformant synthesis.** It is the capture doc as written — the product-relevant
> distillation of the paper's findings. The next `research.sh` run rewrites it per the Research Standard's
> synthesis contract (§4). Leaving it un-reshaped on purpose: it is the honest input for that test.

---

# Product Notes — Federated Agentic Orchestration

> **⚠ THIS FILE MUST SURVIVE THE CLASS CLEANUP.**
> It currently lives inside the CSCI-6905.604 repo because that is where the work happened. That repo is slated for deletion (see `~/Repos/CSCI-6905.604/CLEANUP.md`). **Move this file to a permanent home before deleting anything.**
> Candidate homes: a new repo for this product, or a `development/research/` entry in an existing planning repo. It is **not** Jarvis — `skyynet-master-planning` is scoped to the Home Assistant product.

**Status:** capture doc, founding phase. Nothing here is ratified. The discipline is to capture the idea, not fabricate the design.
**Created:** 2026-07-25, during the CSCI-6905.604 research project.
**Why it exists:** the research paper and the product kept generating ideas for each other. Paper-bound material went into the paper. This file is where the product-bound material lives so it survives the conversation that produced it.

---

## 1. The product concept

A two-tier system for running durable, self-improving agentic workflows across a team or an organization, without either (a) giving up orchestration the way per-user tools do, or (b) paying per-token platform costs the way centralized products do.

- **Server tier** — a durable workflow engine (Temporal) plus a **shared library of reusable workflow modules**. Runs no agent compute, holds no user credentials, executes no model inference. It orchestrates and nothing else.
- **Edge tier** — a small worker daemon on a user's own machine, alongside whatever capability that machine is authenticated for: a coding agent under the user's own subscription, an API client, a local model server, an HTTP adapter, or plain non-AI operations.

The elegance is that credentials never leave the edge. Multi-tenancy is achieved by each user authenticating on their own machine, not by pooling compute at a server. That sidesteps the credential-proxying problem entirely rather than working around it.

**The thing that is actually novel** is not any individual component — it is the shared workflow library as a first-class artifact. Anyone can run a workflow engine. What no one has published is a *catalog* of composable, standards-conforming workflow modules that an organization distributes to its members, the way a package registry distributes libraries.

---

## 2. Settled architecture decisions

These came out of the paper work and are considered stable.

| Decision | Rationale |
|---|---|
| **Two tiers, server + edge** | Server owns orchestration state; edge owns auth, compute, and ephemeral local state |
| **Edge owns what edge is better suited for** | The governing design axiom. Auth, local compute, session state stay at the edge. Workflow definitions, orchestration state, coordination signals, cross-run artifacts live at the server. |
| **The server never impersonates the edge** | No shared credentials at server = no credential-proxying concern. This is a design line, not a constraint reluctantly accepted. |
| **Heterogeneous edges** | An edge is "an authenticated compute endpoint that can run a worker." The protocol is indifferent to what capability the edge provides — coding agent, API client, local model, HTTP adapter, non-AI operation. |
| **Edges never talk to each other** | All coordination flows through workflows. Keeps the topology a star, not a mesh. |
| **Object storage is the third server-tier component** | Large artifacts (transcripts, diffs, tool logs) go to S3-compatible storage; only references land in workflow event history. Keeps histories bounded. |

### Scaling model — two orthogonal axes

- **Horizontal** — the library widens. More modules; more workflows within a module.
- **Vertical** — compositions deepen. Activities → workflows → parent workflows → higher-order orchestrations → scheduled invocation.

The axes multiply rather than sum. An activity added at the base becomes reachable by every composition above it. Each new composite becomes a unit that horizontal growth can then reuse. **Maintenance burden tracks component count; expressible capability tracks reachable combinations.** The gap between those two is what the module design discipline buys.

**The top of the vertical axis is where the system's character changes.** A workflow invoked on a schedule rather than by human dispatch acts without being asked. That is the structural precondition for continuous-improvement loops: a loop that reflects across prior runs has to be something the system runs, not something a person remembers to run.

---

## 3. Module design standards

The ten standards are already written up — they were abstracted from the existing production standards corpus into universal form for the paper. See `drafts/section_5_module_design_standards.md` in this folder.

Summary: three-layer discipline (workflow / helper / activity), semantic wrapping, typed input contracts, activity registry, structured result contract, idempotency by construction, controlled error vocabularies, composition over reimplementation, standardized file layout, semantic boundaries in the observability surface.

**For the product**, the open work is:
- Adapting them from the infrastructure-automation domain to the agent-orchestration domain
- Deciding which are binding versus advisory for third-party module authors
- A module manifest format (what a module declares about itself)
- Versioning and compatibility semantics between library, server, and edge worker

---

## 4. Observability contract

Settled at concept level, not designed.

Every activity returns a structured payload:

```
{
  outcome:    ok | changed | skipped | failed
  summary:    one-line human-readable
  structured: { duration, cost, model, tool_call_count, ... }
  artifacts:  { transcript_url, diff_url, tool_log_url, ... }
  error_code: CONTROLLED_VOCABULARY_CODE | null
}
```

Compact structured data lands in event history (queryable, cheap). Large artifacts go to object storage; only URLs land in history. Temporal's External Payload Storage does this automatically for oversized payloads.

**Why this matters:** this is what makes continuous-improvement loops possible without bespoke instrumentation. A workflow that reflects on prior runs queries event history and aggregates structured fields. Free-form text results would force it to parse strings.

**Distributed-log reality to design around:** orchestration-level data (which workflows ran, in what order, with what outcome) lives at the server. Everything else — activity logs, agent session transcripts, tool output, OS logs — lives at the edge. The artifact-upload step is what bridges them, and it is a required protocol step, not an optional one.

---

## 5. Ideas captured, not yet designed

### 5.1 Multi-method convergence gating for improvement decisions

Do not rely on a single signal to decide whether something needs fixing. Sample several verification methods and gate on what they converge on.

Candidate signals, roughly mapped onto Ambroise et al.'s verification hierarchy:
- **Execution-grounded:** recurrence frequency across runs, error-code distribution, retry counts, cost outliers
- **Tool-grounded:** does a test fail, does a linter flag it, does a build break
- **Model-as-judge:** an agent reviewing the artifact and critiquing it
- **Human:** the review queue disposition

**Why gating on convergence matters:** it is a direct answer to the self-confirming-loop failure mode. A single model critiquing its own output can talk itself into anything. Three independent signals agreeing is much harder to fake.

### 5.2 Recurrence as the cheapest possible signal

Frequency is the single most under-used improvement signal, and it is structurally unavailable to any in-session reflective loop because the loop does not survive between runs to count anything.

If the same defect class appears in thirty-one of forty runs, that is a no-brainer fix and it required no model reasoning to identify. A durable execution record makes this a database query.

**Design implication:** the structured result contract should be designed so that recurrence is *cheap to compute*. That means stable error codes, stable step names, and stable failure categorization — not free-text messages that differ slightly every run.

### 5.3 Retry authority must be negotiated across the substrate/capability boundary

Discovered while researching the coding-agent integration. Capability endpoints increasingly have their own retry logic. A capability retrying ten times inside an activity that the orchestrator will itself retry three times produces thirty attempts and thirty times the spend.

**Open design question:** does the edge worker suppress the capability's internal retry and let the orchestrator own it, or does the orchestrator set `max_attempts=1` and delegate resilience downward? Probably the former — the orchestrator has visibility the capability lacks (rate-limit budget across all workflows, cost ceilings, priority) — but this needs deciding, and it needs to be a documented part of the edge worker's contract.

### 5.4 Host affinity breaks edge fungibility for recovery

The federation model implies edges registered for a task queue are interchangeable. That holds for fresh dispatch. It **fails for resumption** when a capability's session state is scoped to a local directory: resuming a partially-complete session requires the same host, not merely a compatible one.

**Design implication:** either accept host-affinity task queues for resumable work, or design workflows so that recovery restarts a step rather than resuming a session. The second is cleaner but wastes work.

---

### 5.5 Standup as the human entry point

Today there are no crons; every workflow is manually dispatched and manually reviewed at each stage. Once scheduled invocation exists, the CPI side of the system runs unattended — which creates the need for a **single, scheduled point where accumulated findings reach a human.**

**The standup command.** A daily invocation where the coordinating agent reviews the outputs of every CPI run since the last standup and presents what actually needs a human decision. Everything else stays in the logs.

Why this matters structurally:
- **It is the loop-breaker.** Autonomous improvement loops need a designated exit to human judgment or they either stall waiting for input or run unchecked.
- **It batches interruption.** Instead of pausing after every workflow, the human is interrupted once per day with a curated queue.
- **It is the quality gate.** Human-in-the-loop is preserved without human-in-the-path.

Secondary trigger: major intervals through the day for anything urgent enough not to wait for tomorrow's standup. The bar for "interrupt now" versus "raise at standup" is itself a policy worth tuning.

### 5.6 Layered CPI — improving the work, then improving the improvement

The core structure. Two layers today; more are possible.

**Layer 1 — improve the work.**

```
cron → scan repos at a known location
     → for each repo with ≥ N merged PRs since last analysis (N ≈ 10)
     → analyze the PR corpus + workflow run logs + agent self-reflection artifacts
     → produce a findings log with concrete CPI suggestions
        (targeting workflows, agents, commands, standards)
     → surface at standup as accept / reject action items
     → human disposition written BACK to the log
```

That last step is what makes it a loop rather than a report. Once dispositions are recorded, **history exists**, and every subsequent Layer-1 run must answer an additional question:

> *Did the changes accepted last cycle actually help?*

Recommendations adjust based on the answer, human still in the loop. This converts continuous process improvement into a continuous *feedback* loop — the system is not just proposing changes, it is scoring its own prior proposals.

**Layer 2 — improve the improvement.**

Same shape, one level up. Instead of analyzing PRs, it analyzes **a series of Layer-1 analyses** (N ≈ 10) and asks:

> *How do we get better at bettering ourselves and our processes?*

Findings target the Layer-1 loop itself — its trigger thresholds, its analysis prompts, its finding categories, its false-positive rate. Same standup surfacing, same human disposition, same history mechanism, same retrospective question once history accumulates.

**Design notes:**
- The threshold (10 PRs, 10 analyses) is a starting guess. It should become a tuned parameter, and Layer 2 is the thing that tunes it.
- Both layers need stable identity for findings so recurrence is computable across cycles (see §5.2). A finding that gets reworded each run is invisible to the "did it help" question.
- Layer 2 has a much slower clock than Layer 1 by construction — ten Layer-1 cycles deep. Expect its history to accumulate over months, not weeks.
- Nothing prevents a Layer 3. Whether it earns its keep is an empirical question; do not build it speculatively.

### 5.7 Workflow roadmap — what gets automated next

Ordered roughly by expected value over implementation cost:

| Workflow | Replaces | Notes |
|---|---|---|
| **PR review** | Reviewing every PR by hand | Highest immediate time savings. Also produces structured findings that feed Layer 1. |
| **Research** | Ad-hoc research sprints | Automates updating stale research and producing new research on demand (see §10 for the revalidation-cadence standard this serves). |
| **Backtracking review** | Nothing — this is new capability | At completion stages, re-examine the research → planning → implementation chain for gaps, misses, and improvements. "We did it — could we have done it better?" |
| **Ecosystem review** | Nothing — this is new capability | Holistic sweep for holes and inconsistencies across the whole system rather than within one change. |

The last two are qualitatively different from the first two: they are not automating an existing manual task, they are doing something that currently does not happen at all because nobody has the time.

### 5.8 Additive automation — the path to progressive autonomy

**The pattern:** as a workflow matures under CPI and its human-review pause stops catching anything, that pause is removed and the workflow is absorbed into a higher-level parent. What was "run workflow A, review, run workflow B, review" becomes "run parent workflow AB."

**Why this is the right shape:**
- Autonomy is *earned per-step*, based on evidence that review was not adding value, rather than granted up front
- The evidence is already being collected — CPI history shows whether a given review gate ever resulted in a rejection
- It is reversible: if a merged step starts producing problems, the gate goes back in
- It compounds with §5.6 — Layer 2 is well-positioned to notice "this gate has approved 40 consecutive runs without modification" and propose the merge

**The end state:** a system that runs increasingly long autonomous chains and interrupts only when it genuinely needs a decision, with those interruptions surfacing at standup. Human attention gets spent on judgment rather than on supervision.

**The risk to design against:** removing a gate removes an observation point. A merged parent workflow should still emit the same structured findings the gated version did — the gate stops blocking, but it should not stop *recording*. Otherwise autonomy is bought by going blind.

### 5.9 The delegation question — scrutinized against the research

**The question:** research says agent performance degrades as more is asked of a single initiating agent. Should workflows therefore instruct the agent to delegate everything to sub-agents and only make decisions and direct traffic? Or does decomposition into activities and child workflows already accomplish this?

**Answer from the research: both, and they are different axes. You are probably already getting one and not the other.**

The relevant findings:

- Monolithic single-agent trajectories degrade sharply past roughly thirty tool calls or thirty-five minutes of wall-clock reasoning (`hierarchical_agents.md` §1, Zylos 2026a). Two mechanisms: context-window degradation, where early results are forgotten and the agent loses track of what is already complete; and **goal drift**, where an agent conditioned on its own accumulating trajectory inherits progressively noisier goal representations.
- Capability at long horizons is a property of `π_θ ⊕ H` — the policy *plus* the surrounding harness — not of the model alone (Dong et al. 2026 long-horizon survey).
- AiScientist's organizing principle is **"thin control over thick state"**: a top-level orchestrator coordinates specialized sub-agents that **re-ground on durable artifacts rather than reading peer outputs from memory.** Removing that durable-artifact bus costs 6.41 points on PaperBench and 31.82 on MLE-Bench Lite.

**The two axes:**

| Axis | Mechanism | What it bounds | Do we have it? |
|---|---|---|---|
| **Orchestration decomposition** | Workflow → activities → child workflows | The *orchestration* context. The workflow accumulates activity results, not agent reasoning. | **Yes, largely free** — Temporal's structure forces it |
| **Reasoning decomposition** | Agent → sub-agents within a single activity | The *reasoning* context inside one agent invocation | **Unclear — this is the gap** |

Temporal's workflow/activity split already prevents the orchestrator from accumulating agent reasoning; the workflow only ever sees structured results. That is real and it is free. But it says nothing about how much a *single activity* asks of a single agent. An activity that invokes an agent and lets it run forty tool calls has all the degradation problems the research describes, and Temporal cannot see inside it.

**The design heuristic this implies:**

> **Activity granularity should be bounded by agent context degradation, not only by logical decomposition.**

If an activity's agent invocation approaches the ~30-tool-call or ~35-minute range, that is a signal the activity is doing too much and should be split — even if it is logically one step. This is a *new* sizing criterion that would not appear from thinking about orchestration alone.

**The corollary, straight from AiScientist:** each activity should **re-ground from durable artifacts** rather than carrying accumulated context. The workflow is thin control; event history plus object storage is the thick state; each agent invocation should be short and start from the record rather than from memory of what it was doing. That is exactly what the structured result contract (§4) enables.

**What needs investigating before this is settled:**
- Instrument current workflow runs to measure tool-call count and wall-clock duration per activity. Which activities are already past the degradation threshold?
- Determine whether the coding agent's own sub-agent dispatch (Task-style delegation within one invocation) is sufficient reasoning decomposition, or whether splitting into more, smaller activities is better. The first keeps orchestration simple; the second gives the substrate visibility into each piece.
- The tradeoff is real: more activities means more durable checkpoints and better observability, but also more dispatch overhead and more artifacts to marshal. There is a sweet spot and it is empirical.

---

### 5.10 Model right-sizing — the Goldilocks constraint

**Observed, not theorized.** Routing the most capable available model to routine workflow steps consumed a large fraction of a weekly subscription allowance within days. Substituting a smaller model for those same steps dropped consumption to roughly 2–4% per day.

The asymmetry that matters is what happens at the ceiling. A metered API degrades into a cost problem. A subscription ceiling is a **hard stop** — the capability disappears entirely until the window resets, potentially for days. That converts model selection from a cost optimization into an availability decision.

**The resulting policy:** the largest model is not the default, it is the escalation path. Routine steps run on a right-sized model; the frontier model is reserved for cases where the smaller one has demonstrably stalled — the "we genuinely do not know what to do next" case. This is the goldilocks principle: the best model for a job is the smallest one that reliably completes it.

**Design implication for the orchestration layer:** model selection belongs in the workflow definition, not in the edge configuration, because the workflow is the only place that knows what class of step is being dispatched. Escalation should be a workflow branch — attempt with the small model, evaluate, escalate on failure — rather than a static per-edge setting.

**Open question:** how does escalation interact with the earned-autonomy rule (§5.8)? A component that has graduated to unsupervised operation on a small model has not necessarily earned that status on an escalated one, and vice versa.

### 5.11 Separating creation from evaluation — structural bias removal

**The observation:** a workflow step that both produces work and evaluates it inherits the reasoning that motivated the original choice. Criticism then competes against the model's own recent commitments, and the model defends. Splitting production and evaluation into separate dispatches severs that inheritance — the evaluator receives the artifact and the record, not the deliberation, and has nothing of its own to defend.

**Why this matters more than it first appears:** self-confirming loops are one of three named failure modes in the recursive-self-improvement literature (`reflection_literature.md`, Ambroise et al. 2026). Most proposed mitigations are prompt-level — instructing the model to be critical. This is a *structural* mitigation: it works because of how the workflow is decomposed, not because of what the prompt says.

**Honest limit:** a separated evaluator can still be wrong in the same direction as the producer, particularly when both run the same model. Author≠critic model diversity is a further improvement on top of separation, not an alternative to it.

**Applies to the current build:** worth auditing existing workflows for steps that both create and judge. Any such step is a candidate for splitting.

### 5.11a The seam rule — corrected framing

**The earlier framing in §5.11 was memory management. That is the secondary effect. The primary one is correctness.**

Fresh context is a **correctness mechanism**, not a capacity mechanism. The capacity argument — long chains accumulate history, early steps lose weight — is real but not why this matters. The reason it matters is that a run which authored a choice defends it, and that bias is structural. It cannot be prompted away, because the instruction to be critical does not remove the material the model is reasoning from.

**The evidence that settles it:** several review agents operating *inside* a build produced weaker findings than a single fresh-context re-dispatch of the same artifact. Same task, same models, same prompts. The only variable was position relative to authorship.

**The rule, stated properly:**

> **Split where the next step JUDGES the previous one. Keep together where the next step CONTINUES it.**

Not "split when long." Length is a symptom; authorship is the cause.

**Why the asymmetry:**
- A **continuation** inherits useful context. Forcing it across a boundary pays handoff cost for nothing.
- A **judgment** inherits the reasoning behind the thing being judged — which is exactly what it must not have. The handoff cost is always worth paying.

**Audit item:** walk the existing workflows and mark every step boundary as continuation or judgment. Any judgment step currently sitting inside the context that produced its input is a defect, regardless of how well it appears to be working.

### 5.12 Two memory models, two build models

**Memory:**
1. **In-context** — long-running process, state held in the model's context window. Degrades as steps accumulate; earlier steps lose weight as later ones are added.
2. **Externalized** — separate dispatches stacked, with state held outside the process. The current implementation uses Git for this: pull requests and issues serve as the durable record between workflow steps.

Git-as-memory is a genuinely useful stopgap and worth understanding before replacing it. It is queryable, durable, and already has review semantics built in. The event history replaces it not because Git is bad at this but because Git has no notion of an in-flight step.

**Build:**
1. **Single-process agent run** — can spawn sub-agents, but the whole thing is one black box to anything outside it, and memory is context-bound.
2. **Durable multi-run** — assembled units, rearrangeable, each with its own boundary and record.

**The synthesis, and it is the architecture this paper proposes, arrived at independently from operational reasoning:**

> If the durable units simply use the coding agent as their delivery mechanism, both models are available without building either from scratch.

That independent re-derivation is a good signal. The architecture was reached twice from different directions — once from literature synthesis, once from running out of headroom on a long workflow.

### 5.13 The build decision rule

Every new capability presents a binary choice:

| Option | Consequence |
|---|---|
| **Extend an existing workflow** | Adds length to a context-bound process; the earliest steps lose weight |
| **Build a new composable unit** | Breaks the context chain; state comes from the durable record instead |

This is the decision that determines whether the system stays healthy as it grows. Defaulting to extension is how a workflow silently crosses the degradation threshold described in §5.9.

**Corollary — change velocity is bounded by CPI throughput.** Each new component must be "trained" by feedback before it can be trusted, and that training is serial per component. Changing many things at once overwhelms the loop: too many components are simultaneously unproven, and the feedback cannot be attributed cleanly to any one of them. Improvement velocity is therefore capped by how fast the CPI cycle can validate new units, not by how fast they can be written.

---

## 6. Implementation findings — coding agent as an edge capability

Full detail: `research/raw/claude_code_integration_surface.md` (~3,400 words, first-party sourced, with a 10-item local test plan).

Headline items:

| Finding | Design impact |
|---|---|
| Internal retry (up to 10 attempts, plus an indefinite-retry watchdog env var) | See §5.3 — retry authority must be divided explicitly |
| `system/api_retry` event in stream-json carries a structured error enum | This is a better failure classifier than exit codes, and maps almost directly onto the controlled error vocabulary standard |
| No first-party exit-code table beyond 0/1/137/143 | Must be measured empirically; test plan item |
| Session resume is directory-scoped | See §5.4 — forces host affinity for resume-based recovery |
| `--bare` mode skips hooks/skills/plugins/MCP but refuses subscription OAuth | Reproducible-execution mode requires API-key auth, not subscription auth. Two different edge configurations. |
| Concurrent-write safety on shared config/credential files is undocumented | Highest-risk unknown for multi-worker hosts. Test before designing around it. |

**Next action on this:** run the 10-item test plan locally. An hour of experiments answers most of what the docs leave open — exit-code mapping, SIGINT semantics, kill-mid-tool resumability, N-concurrent-worker corruption.

---

## 7. Naming — unresolved

- **OWL** (Open Workflow Library) — good for the library/catalog component. Suggests wisdom and synthesis; works if the library is ever open-sourced.
- **System name** — undecided. `Cerebral` was floated. Constraints the operator stated: avoid tech-slang and overused terms; prefer something from outside the tech space that connotes mind or coordination. `Temporal`, `Neural`, and `Orchestrator` are all taken.
- For the research paper, the architecture is referred to generically as "the proposed architecture" with no product name. That decision does not bind the product.

---

## 8. Deferred — explicitly out of scope for a first build

Named here so they are not silently forgotten, and not designed here because designing them now would be premature.

- **Packaging and installers** — server deployment (helm / docker-compose) and edge worker deployment (systemd unit)
- **Versioning and compatibility matrix** — library version ↔ server version ↔ edge worker version
- **Onboarding a new edge type** — what interface contract makes something a compatible edge
- **Module distribution** — a package registry for workflow modules; no npm-equivalent exists for Temporal today
- **Multi-organization federation** — sharing modules through a public catalog while keeping orchestration state private; module signing, cross-tenant isolation
- **Product-layer surfaces** — visual editor, non-engineer iteration surface, customer-facing run status. A durable workflow engine supplies none of these and they are a real gap.

---

## 9. Where the supporting research lives

All under `research/raw/` in this folder. **These are worth preserving alongside this file.**

| File | What it covers | Product relevance |
|---|---|---|
| `durable_execution.md` | Temporal model, 2026 AI-specific primitives, vendor integration landscape, honest boundary analysis of when durability is overkill | High — the substrate |
| `claude_code_integration_surface.md` | Invocation, session, auth, config, failure, concurrency, observability + test plan | Highest — the edge |
| `reflection_literature.md` | Self-improvement lineage, verification hierarchy, the gap analysis | High — the CPI loop design |
| `hierarchical_agents.md` | Composition patterns, durable-artifact mechanisms across three independent systems | Medium — composition model |
| `production_cases.md` | Who built what, who reinvented durability, what failed | Medium — validation |
| `anthropic_tos_and_enterprise.md` | Subscription vs commercial terms, the auth boundary, enterprise feature inventory | High — the business model depends on this being right |

---

## 10. Methodology — research as a first-class repo artifact

> **This section is methodology, not product.** It describes how the product should be built, and generalizes to every product. A formal standard describing this process belongs in the platform standards corpora — raise it in the architecture sessions that own those repos rather than writing it from a product session.

### The observation

The research produced for this project (six docs, ~11,000 words, ~90 citations, one afternoon of parallel agent work) is more durable and more valuable than the paper it was produced for. It will still be useful in six months. It answers questions that would otherwise be re-litigated in the middle of implementation, when the cost of being wrong is highest.

The failure mode this prevents: **starting a sprint with an under-researched trajectory, then thrashing between implementations because the correct approach was never established.** That thrash is measured in weeks, sometimes months. A day of structured research up front is not overhead; it is the cheapest possible insurance against building the wrong thing carefully.

### The standard, in outline

**Every major product carries a `research/` directory.** Research docs are first-class artifacts alongside standards and planning docs, not scratch notes.

**Every research doc carries a header block:**

```
Topic:          <what question this answers>
Last validated: YYYY-MM-DD
Revalidate:     <trigger or cadence — see below>
Confidence:     <what parts are definitive vs directional vs unverified>
```

**Revalidation cadence is set by volatility, not by a fixed interval.** Different research decays at different rates:

| Volatility | Examples | Cadence |
|---|---|---|
| High | Vendor pricing, terms of service, product feature inventories, API surfaces | Quarterly, or on any vendor announcement |
| Medium | Framework capabilities, ecosystem landscape, competitive positioning | Every 6 months |
| Low | Distributed-systems fundamentals, academic literature synthesis, classical antecedents | Yearly, or on-trigger when a superseding result appears |

The Anthropic terms-of-service research in this project is a live example of high-volatility material: it is pinned to a February 2026 policy state, one referenced pricing change was announced-then-paused mid-research, and any of it could shift without notice. That doc needs a date and a trigger or it becomes actively misleading.

### What makes a research doc agent-consumable

The point is not just human reference — it is **feeding planning agents real context instead of prompt-alone.** A planning agent given a sourced research doc produces a materially better plan than one given a paragraph of prompt. For that to work, the doc needs:

- **Findings with citations** — every factual claim traceable to a URL or paper
- **Explicit confidence marking** — definitive (first-party documented) / directional (stated intent, personnel statements) / unverified (community-sourced, not corroborated)
- **Explicit gaps** — "not documented" stated as a finding rather than papered over with a plausible guess. A confident-sounding doc with fabricated specifics is worse than useless to an agent, which cannot tell the difference.
- **A synthesis section** — "what this means for us," separate from the findings. The agent needs the implication, not just the facts.
- **A test plan for what research cannot settle** — research ends at "nobody has documented this." The gap list is the handoff to experiment.

The six docs in `research/raw/` largely follow this shape already; the integration-surface doc marks "not documented" eight distinct times, which is exactly the discipline.

### Why this is itself CPI

The loop is Research → Standards → Planning → Implementation, and it repeats. But the research stage has its own inner loop: what did the last cycle's research miss, what did implementation discover that research should have caught, what gap analysis turned out to matter. Revalidation is not just refreshing facts — it is asking whether the *questions* were right.

Every stage, examined for how to do it better next time. The method is recursive, which is the same property that makes the product's continuous-improvement loops worth building in the first place.

---

## 11. Open questions worth research when they pull

- How does this compose with MCP? Tools are the vertical link (agent ↔ tool); this is the orchestration layer. They compose, but the module manifest probably needs to declare MCP dependencies an edge must have installed.
- What happens when the capability vendor ships their own orchestration layer? (Partially answered in the paper's timing-risk discussion: the reference architecture retains value as the design space against which a vendor solution is evaluated.)
- Does the two-tier model hold for a single-user deployment, or does it collapse into unnecessary overhead below some team size?
- What is the minimum viable server tier? Can it be a single container on the same machine as one edge, for a solo user who wants durability without infrastructure?
