# Synthesis — product-level research

**Cycle:** 2026-08-03 (second cycle today) · **Pool:** 16 papers · **Tier:** Large / architecture-layer · **This cycle added 5**

Read this instead of the pool. It says what the evidence means for the product's direction and ends in reviewable candidates. Nothing here is binding — research is evidence, and a finding becomes a rule only by being codified into a standard through human review.

**What changed since the last cycle, and why this synthesis reads differently.** The previous cycle reasoned entirely from `docs/development/roadmap.md`, because that was the only frame on disk. `docs/standards/architecture/problem-statement.md` has since been written, and it states a *thesis*: four elements combined, affordability as the enabler, and a claim that the backbone generalises across edges. This cycle asked the question that frame makes possible — **does the architecture close the gap it claims to, and is the combination novel and sound?** The answer is not the comfortable one.

## Inputs

| Paper | Last validated | Revalidate | Critic verdict | Status |
|---|---|---|---|---|
| `raw/combination_prior_art.md` | 2026-08-03 | high — 4 weeks | **PASS-WITH-FIXES** (3 correction rounds; all 39 citations fetched, zero fabrications; E2 upgraded ⚠️→✅ against a source section unread in rounds 1–2; four absence claims falsified by its own cited sources and corrected) | current |
| `raw/code_routed_control_flow.md` | 2026-08-03 | high — 6 weeks | **PASS** (3 rounds; CrewAI removed from the enumeration after its own docs falsified the claim; a 100× figure error corrected and the argument re-run; P2 downgraded definitive→derived) | current |
| `raw/subscription_economics.md` | 2026-08-03 | high — 2 weeks | **PASS** (3 rounds; no fabricated price or source at any round; one phantom source attribution withdrawn) | current |
| `raw/case_against.md` | 2026-08-03 | high — 4 weeks | **PASS-WITH-FIXES** (3 rounds; all three load-bearing Anthropic quotations verbatim and in context; N6's propagating trace extended to a second site) | current |
| `raw/backbone_edge_generality.md` | 2026-08-03 | high — 6 weeks | **PASS-WITH-FIXES** (3 rounds; interval raised low→high on a §3 mixed-volatility ruling; two Kubernetes miscitations corrected; one benchmark attribution corrected) | current |
| `raw/convergence_stopping.md` | 2026-08-03 | high — 6 weeks | PASS (2 rounds) | current |
| `raw/workflow_reuse_boundary.md` | 2026-08-03 | high — 6 weeks | PASS-WITH-FIXES | current |
| `raw/python_sdk_long_activities.md` | 2026-08-03 | high — 4 weeks | PASS-WITH-FIXES | current |
| `raw/durable_execution.md` | 2026-07-27 | low — 6 months | PASS | current |
| `raw/hierarchical_agents.md` | 2026-07-25 | medium — 3 months | PASS | current |
| `raw/claude_code_integration_surface.md` | 2026-07-25 | high — 4 weeks | PASS | current |
| `raw/hook_sourcing_supplement.md` | 2026-07-25 | high — 4 weeks | PASS | current |
| `raw/anthropic_tos_and_enterprise.md` | 2026-07-24 | high — 4 weeks | PASS | current |
| `raw/reflection_literature.md` | 2026-07-23 | medium — 3 months | PASS | current |
| `raw/production_cases.md` | 2026-07-23 | medium — 3 months | PASS | current |
| `raw/temporal.md` | 2026-07-04 | high — 4 weeks | PASS | ⚠️ **PAST WINDOW** (due 2026-08-01) |

**Currency correction — the previous synthesis was wrong about this.** It stated four papers were past window. Under §5's mechanical gate only **`temporal.md`** is: `anthropic_tos_and_enterprise.md` (due 2026-08-21), `claude_code_integration_surface.md` and `hook_sourcing_supplement.md` (both due 2026-08-22) are current. That error propagated into two of this cycle's drafts via the dispatch and was caught by two critics independently. Nothing in this synthesis rests on a past-window claim.

**A second correction the previous cycle recorded and this one reverses:** `system-overview.md` was excluded as substantively stale. **It has been rewritten and is accurate.** The prior synthesis's § *A stale destination* and candidate #10 are superseded and should not be actioned.

**No papers were retired.** See `topics.md`.

## What the pool now establishes

### 1. The novelty claim does not hold. Someone has built the combination

This is the cycle's headline and it moves against the product's own framing.

`combination_prior_art.md` searched for a system combining all four elements plus the edge deployment shape, and found one: **[`sipyourdrink-ltd/bernstein`](https://github.com/sipyourdrink-ltd/bernstein)** — Apache-2.0, Python, 777 stars, PyPI v3.13.0, created 2026-03-22, **last pushed the day of the search**. Its own GitHub description is close to a restatement of elements 3 and 4: *"Deterministic orchestrator for CLI coding agents… No model in the coordination loop, so parallel runs in per-task git worktrees replay byte-identically."*

Element by element, from its own first-party docs: **E1** a WAL with `write()+flush()+fsync()`, hash chain, and idempotency-filtered replay on restart. **E3** the project's *headline marketing claim* — *"There are no LLM calls in this loop. No model decides which task to run next"* — with a documented motivating failure (a prior LLM scheduler that fell asleep and starved twelve workers). **E4** a tick loop over a durable backlog with a "VP cell" above worker cells. **E5** a central coordinator plus worker hosts running local CLI agents under their own installed auth (*derived* — no bernstein doc states where model credentials live).

**E2 is the finding that took three rounds and moved twice.** The paper first judged it partial, on the reasoning that bernstein's judging layers do not feed future behaviour. Verification falsified that twice from bernstein's own documentation: the autofix telemetry path is a closed loop, and `quality-pipeline.md` documents *"the wire from janitor results into model escalation"* — a judge's verdict recorded durably and changing the router's behaviour *"on the next call to `select()` for a **fresh** task."* The final verdict is **4-of-4**.

**What survives is narrow, and the paper marks it as a question rather than a finding.** Every documented lever a bernstein verdict moves on a *future, unseen* task is model/tier selection on a fixed ladder — never *how the work is done*; the method-changing channel is the lesson path bernstein implemented and left unwired (*"nothing files lessons automatically yet"*). Whether *"a verdict that changes method rather than model choice"* is genuinely unbuilt is **UNTESTED**: 40 of bernstein's 52 doc directories are unread, and kodo's cross-cycle summaries and tutti's `Record` stage are named, unexamined falsifier candidates. **A planning run must not treat this narrowing as validated novelty.**

**The pattern is a stronger refutation than the single match.** Three independent projects are assembling these elements right now with complementary gaps — bernstein (E3 strong), **kodo** (the strongest E2 found anywhere: independent architect and tester agents with rejection authority — but E3 ❌, an LLM orchestrator routing by tool calls), **tutti** (typed artifact passing with code-decided `depends_on`). And **`paperclipai/paperclip`** — MIT, **75,535 stars**, pushed 2026-08-04 — has E1, E4, and a heartbeat-based any-agent-any-runtime shape, with E3 simply *undocumented*: the largest player in the space does not say whether its sequencing is code-prescribed or model-chosen.

### 2. Element 3 is sound but ordinary — and this repo already does it

`code_routed_control_flow.md` tested the premise under elements 3 and 4: routing decisions made by code over typed state, no model in the loop.

**The two-way framing does not describe the field.** LangGraph, Microsoft Agent Framework, Google ADK, Temporal and Restate all document *the same middle* as their canonical routing example — a model emits a closed-vocabulary typed value, ordinary code branches on it. Microsoft's docs ship `Literal["NotSpam","Spam","Uncertain"]` with the residual arm going to a human, plus *"the default case provides a safety net for unexpected values."* CrewAI is the checked case that does **not** fit, and the paper reports it as disconfirming rather than dropping it.

**The premise as worded is ordinary, not distinguishing** — and the sharpest evidence is internal: `revision.sh` line 277 already code-routes today via `grep -oE '^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$'` plus a `case`, with a fail-closed default. The only delta between what ships and element 3 is the *transport*. Two narrower re-cuts are defensible and uncovered by the literature: routing across whole workflow runs in separate processes resumed from persisted state, and routing on values the model did not author.

**"No model in the loop" is false of the decision in every located instance.** The model still decides; it decides in a typed field. And **no head-to-head study of code-routed versus model-routed control flow was located** — the preference is asserted by every vendor and measured by none. Two 2026 preprints measure orchestration as a net *loss* (both directional). A widely-cited routing system reports ~90% classification accuracy with up to a **3%** false-switch rate; composed over a five-step chain that is ~66% (derived, and the independence assumption is almost certainly false).

**The stronger argument for typed results is not routing at all.** It is `convergence_stopping.md`'s P11 — the convergence and residual-risk machinery this pool already committed to *cannot run* on prose. That argument has no working incumbent to beat; the routing argument does.

### 3. Affordability does not survive in its stated form

`subscription_economics.md` tested the enabler claim. **"A long-running loop costs the same as a short one" is false.** The defensible version: *below the plan ceiling, the marginal dollar cost of a turn is zero.*

Three first-party findings drive it. **The cap is a second meter, and Anthropic says it binds on this exact workload** — *"A single burst of heavy activity, such as a large workflow fanout, can exhaust the weekly allowance before the session window resets."* **The overage path is metered billing at list prices** — usage credits are *"billed at standard API rates"*, so the subscription is a prepaid block on the metered curve. And **`claude -p`, this architecture's own edge invocation, has been formally announced as moving off the subscription pool** to dollar-denominated credits at API rates — *paused, not withdrawn*; the June 15 pause banner is still live.

**The measured subsidy is 1x–2.5x, not 10x** (Anthropic's own budgeting guidance: ~$215/mo typical and ~$500/mo power seat against $200/mo Max 20x). The largest metered discount is structurally unavailable — Anthropic states agentic sessions have *"no batch mode."* And falling prices are partly illusory here: Sonnet 5 carries a scheduled **50% increase on 2026-09-01**, and current models use a tokenizer producing *"approximately 30% more tokens for the same text."*

**A correction candidate to the problem statement, marked derived in the paper:** by the problem statement's own definitions, elements 1, 3 and 4 are engineering-time or explicitly model-free. Only element 2 is token-expensive. *"The enabler of the other three"* is unsupported; *"the enabler of element 2"* is.

**The property the problem statement wants exists in the market — at GitHub, not Anthropic.** Copilot meters human prompts, not model turns: *"actions Copilot takes autonomously… do not"* count.

**Two gaps, both findings.** Anthropic publishes **no absolute usage-limit quantity** on any current first-party surface — the ceiling cannot be planned against analytically, only measured. And **no survey of the individual-experimenter population exists**; every located instrument samples enterprises. The affordability claim is therefore *unfalsified rather than verified*, and unfalsified because nobody measured the population it is about.

### 4. The gap claim is stale, and the sharpest counter-evidence is Anthropic's own

`case_against.md` was commissioned to be the adversary. Its most damaging finding: between 2026-03-25 and 2026-05-28, **three vendors shipped durable agent loops** (AWS AgentCore session storage, Cloudflare "Project Think", and Anthropic itself), with a fourth shipping the same pattern undated.

Anthropic's dynamic-workflows announcement — **generally available**, verified first-party — covers four of the problem statement's enumerated elements in three sentences: orchestration scripts written as code, *"a job that's interrupted picks up where it left off instead of starting over,"* *"other agents try to refute what they found,"* and *"the run keeps iterating until the answers converge."*

**What survives is the scoping, not the gap**: multi-participant, credentials-at-edge, server-runs-no-agent-compute. That is a narrower and more defensible claim than "the industry did not make the loop durable."

**The finding that most favours the thesis is reported first, and it is a real one:** N1 — **no published argument was located that agent loops should *not* be durable.** The disagreement in the literature is entirely about *which* durability implementation is adequate. The restart-over-resume case is the paper's own architectural argument from Kubernetes level-triggered design and crash-only software, marked derived throughout, and the paper says plainly it is its weakest attack line.

**A live contradiction the pool cannot settle**, and the paper is honest that the two claims are not peers: Cognition (a practitioner blog, since softened) argues separating decision-making disperses context; `convergence_stopping.md` measures separation *improving* review F1. Neither measures this system's topology.

**N6 corrects a fact inside the pool.** The "~30-minute threshold" cited in `durable_execution.md` traces to a **community-authored guide, not to any vendor** — and it appears at two sites, §3 unhedged and §6 hedged. **No first-party durable-execution vendor publishes a horizon threshold.**

### 5. The generality claim is the weakest-evidenced thing in the problem statement

`backbone_edge_generality.md` splits it into four claims and rules on each.

**C1 — "the backbone does not change" holds as a shape, with a correction: no surveyed platform kept a domain-free core.** **C2 — "each new edge costs less than the last" is unsupported as stated.** The product-line literature measures variants *within one domain*; the nearest cross-domain measurement says the opposite — *"our operational overhead increased linearly with each added destination."* The supportable claim is cost *externalisation* to edge authors, not declining total cost. **C3 — "an edge is a machine running the same protocol" holds for supervisory work and fails for control**, on two colliding first-party quotes: Temporal's *"the Activity may be executed multiple times"* against Microsoft's *"you can't safely or meaningfully undo some operations."* Adding the word **supervisory** to the backbone's description converts this from false-as-written to true. **C4 — "every new edge arrives with an assistant already fluent in the backbone" is the least testable**, and both smart-home agent benchmarks independently name *workflow scheduling* as the worst agent category — which is the backbone's own job.

**The most significant finding is an absence, and it is methodized:** no platform was located that started in one domain and *successfully* added a genuinely unrelated second domain **on an unchanged core**. Every candidate either stayed inside one domain family or changed its core. The general workflow engines (Temporal, Airflow, Camunda) are not counterexamples **because they carry no domain ontology at all** — they have no edges in the sense under test.

**The binding constraint survives, but via Fowler's own carve-out** — *"Yagni only applies to capabilities built into the software to support a presumptive feature, it does not apply to effort to make the software easier to modify"* — i.e. *"would this still make sense if the edge were a robot?"* is legitimate as a **review discipline**, explicitly not as licence to build edge machinery now.

**A blank worth naming:** the regulatory and certification claims for a physical edge are **not asserted** — every authoritative source was paywalled, 403'd or truncated. Plausibly the largest cost item on an industrial or robotics edge, and currently unpriced.

### 6. Carried forward, unchanged

The Temporal port's shape findings stand: an async `claude_cli` activity over `asyncio.create_subprocess_exec` (the sync shape can neither heartbeat nor be cancelled while blocked), transcripts as pointers rather than payloads, and the retry economics that no heartbeat fixes. The `--setting-sources` safety blocker remains untested and remains the one item where the roadmap and the pool agree the next step is an experiment. The stopping-rule provenance correction from the previous cycle stands and is untouched by this one.

## What this means for the product

**The thesis is not refuted, but its stated form is.** Three of its five load-bearing claims are wrong as written, and each has a narrower true version underneath:

| Claimed | Supported |
|---|---|
| Nobody has combined these four | At least one project has all four; three more are assembling them; the field is converging *now* |
| Typed code-routing is a distinguishing element | It is the documented default across five frameworks, and `revision.sh` already does it |
| Flat-rate makes long loops cost the same as short ones | Below the ceiling the marginal turn is free; the ceiling is a second meter that binds on exactly this workload |
| The industry did not make the loop durable | Three vendors shipped durable loops in a nine-week window, one of them Anthropic |
| Each new edge costs less than the last | Nearest evidence says per-edge cost stayed linear; the supportable claim is cost externalisation |

**What still looks genuinely un-held by anyone**, on this evidence: the *combination of the deployment shape with the rest* — multi-participant, credentials never leaving the edge, a server tier running no agent compute — for which **no instance was located at all**, and which is the economic half of the novelty question. Everything else in the thesis has an incumbent.

The honest reading is that **the contribution the problem statement should defend is the scoping, not the gap** — and that the shared workflow library, which the problem statement already calls "the genuinely novel artifact," survives this cycle better than any of the four elements does.

## Action candidates

Reviewable items, sized for a standup. Nothing is ratified. Per §7 this run surfaces candidates and writes nothing outside `research/` — routing is the reviewer's and the operator's.

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Rewrite the problem statement's novelty section.** "Nobody has put them together" is falsified by a named, live, Apache-2.0 project that has all four. The claim to defend instead is the *scoping* — multi-participant, credentials at the edge, server running no agent compute — for which no instance was found | change direction | `combination_prior_art.md` |
| 2 | **Re-cut or retire element 3 as a novelty claim.** Code-branching on a model-emitted typed value is the documented default across five frameworks, and `revision.sh` already ships it. Two narrower readings are defensible and uncovered: routing across *separate processes resumed from persisted state*, and routing on values *the model did not author* | change direction | `code_routed_control_flow.md` |
| 3 | **Correct the affordability claim to "below the ceiling, the marginal turn is free."** And correct "the enabler of the other three" to "the enabler of element 2" — by the problem statement's own definitions only element 2 spends tokens | change direction | `subscription_economics.md` |
| 4 | **Date the gap claim, or drop it.** Three vendors shipped durable agent loops in a nine-week window and one is Anthropic. A market-position claim with a revalidation half-life of weeks sits in a document carrying no date on it | change direction | `case_against.md` |
| 5 | **Three wording edits to `problem-statement.md`, all cheap now and expensive after a context rebuild:** correct C2 to cost *externalisation* rather than declining total cost; add **supervisory** to the backbone's description (converts C3 from false-as-written to true and pre-empts the sharpest robotics objection); mark C4 a hypothesis rather than the stated source of compounding | adopt | `backbone_edge_generality.md` §8.2 |
| 6 | **Measure the ceiling — it cannot be researched.** Anthropic publishes no absolute usage quantity anywhere first-party. A burn test is the only way to know whether the workload fits, and it must run *after* 2026-08-19 or record that a reported temporary limit boost is in effect | new concept | `subscription_economics.md` T2/T4 |
| 7 | **Read bernstein's 40 unread doc directories before any planning run cites the method-vs-model narrowing.** It is the one surviving novelty candidate and it is explicitly untested; three named falsifier candidates are unexamined | adopt | `combination_prior_art.md` §4.4, test item 4 |
| 8 | **Promote "decide-only disposition" to first topic of the next cycle.** It was already queued; the new frame makes it the sharpest testable claim inside element 2, *and* `case_against.md` surfaced a live sourced contradiction (Cognition vs. `convergence_stopping.md`) that only an experiment resolves | adopt | `case_against.md` T5; `topics.md` |
| 9 | **Refresh `temporal.md`** — the pool's only past-window paper. The prior cycle's candidate to rewrite rather than diff it at that refresh still stands | no change | `temporal.md` header |
| 10 | **Correct the prior synthesis's two errors where anything inherited them:** four papers were said to be past window (only `temporal.md` is), and `system-overview.md` was said to be stale (it has been rewritten and is current). Prior candidate #10 is superseded | no change | this synthesis, § *Inputs* |
| 11 | **Price the regulatory blank before scoping any physical edge.** Certification and conformity regimes are unpriced and unresearched — every authoritative source was paywalled or blocked — and are plausibly the largest cost item on an industrial or robotics edge | new concept | `backbone_edge_generality.md` §8.4, §9 item 6 |

### Trace: what candidate #1 touches

Per §4, a corrected fact enumerates **every** dependent. The novelty claim reaches:

1. `docs/standards/architecture/problem-statement.md` § *What we are combining, and why it is novel* — **the claim's origin**, including the sentence *"Nobody has put them together, and the combination is the contribution."*
2. `problem-statement.md` § *Status and evidence*, which points at this pool as the supporting evidence — the pool now partly contradicts the document it supports.
3. `problem-statement.md` § *Where this repo sits* — "iteration one" is unaffected, but the framing of what iteration one is *first at* is.
4. `docs/standards/architecture/research/README.md`, whose "what lands here" section describes recording convergence with the coursework's design principles. That convergence is now larger than recorded: it includes independent projects, not only literature.
5. Any future planning doc citing the synthesis for novelty. **Unenumerated and unverified** — the reviewer should check, because no planning run has consumed this pool yet, so the blast radius is plausibly zero today and grows with every run that does.

## Homeless findings

Named here rather than parked elsewhere, per §7 — a homeless finding means the surface is missing.

- **Research Standard §3 has no confidence class for an authoritative speaker in an informal artifact.** Carried from the prior cycle, still homeless, and hit again this cycle: the four classes conflate how authoritative the speaker is with how formal the artifact is. The standard is **vendored MIRROR** from `MDC-Master-Planning`, so it cannot be amended here — the amendment goes upstream and is re-vendored, and **this repo has no surface that holds "an upstream standards amendment we owe."** That missing surface is the finding.

- **A second, sharper amendment now owed upstream: §3/§4's sourcing rule names the wrong hazard.** Two analysts independently traced a blocking finding to the same root cause, and it is not the rendered-vs-raw distinction the standard codifies. In one case a date came from a **search-engine summary synthesised across results**, never from a fetched page. In the other, a **summarizing fetch silently elided a clause** from a first-party URL, and the shortened quote was labelled verbatim. The rule that catches both is narrower than "prefer raw sources": *a span may be labelled verbatim only if its exact character sequence was returned by a fetch, and a fetch that summarizes cannot establish that.* Same homeless surface as above.

- **A defined shape for production feedback.** Carried from the prior cycle and still homeless. One instance exists as a dated intake record; a dated one-off is not a channel.

- **The sizing rubric's bands are calibrated for components whose destination is a plan.** This component's destination is a *thesis*, which carries more falsifiable claims per unit of build — 16 topics against a Large band of 8–10. Recorded as an observation about the rubric, not acted on. Same vendored-standard problem: it cannot be fixed here.

## Gaps this cycle did not cover

- **Decide-only disposition — does a judging stage with no authoring authority actually reduce defects?** Per-cycle cap. Now first in line and higher-priority than before (candidate #8).
- **Whether an agentic `claude -p` run decomposes into resumable per-turn legs.** Still uncovered. Decides the port's shape, not whether the thesis holds.
- **Duplicated prompt *prose*.** No located literature; needs a scoping pass before it earns a dispatch.
- **Inter-process handoff contracts — the wire format.** Phase-level, redirected not deferred; see `topics.md`. Note this cycle's element-3 finding *reinforces* the redirect: the transport is the only delta between what ships and the thesis element.
- **Reflection-channel mining** and **bash → Python Stage A conversion** — both phase-level.
- **Certification and conformity regimes for a physical edge** — new this cycle, and unanswerable without paid standards access (candidate #11).
