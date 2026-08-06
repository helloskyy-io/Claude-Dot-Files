# Synthesis — product-level research

**Cycle:** 2026-08-06 (cycle 4) · **Pool:** 25 papers · **Tier:** Large / architecture-layer · **This cycle: 4 papers added, 0 retired, 0 revalidated**

Read this instead of the pool. It says what the evidence means for the product's direction and ends in reviewable candidates. Nothing here is binding — research is evidence, and a finding becomes a rule only by being codified into a standard through human review.

**This synthesis is a DRAFT.** Every paper added this cycle carries `Critic: not-yet-verified`. A separate fresh-context run verifies each citation, applies corrections, and traces every correction through to this document per [§4](../../research/research_standard.md)'s trace-to-all-dependents rule. Treat the four new papers' claims as unverified evidence until that run lands.

**What a standup should read: § *The four things that changed* and the candidate table.**

---

## Inputs

**Added this cycle.** All four conform to the §3 content arc (primer → model → comparative landscape → what this provides → honest boundary → citations) and all four carry an explicit test plan.

| Paper | Last validated | Revalidate | Critic verdict |
|---|---|---|---|
| `raw/openclaw_assessment.md` | 2026-08-06 | high — 3 weeks | **not-yet-verified** — 802 lines. Load-bearing auth findings rest on fenced verbatim reproductions of raw first-party markdown; trust-boundary and durability quotes came through a *summarizing* fetch and are self-marked reduced-confidence. §5(b) records a **measured hallucination inside the run**: a summarizing fetch returned two thesis-convenient quoted spans that a verbatim re-fetch of the same page did not contain. Both were discarded |
| `raw/hermes_assessment.md` | 2026-08-06 | high — 3 weeks | **not-yet-verified** — 1,020 lines, 13 raw first-party docs. Identification chain is JSON-API-grounded. One count explicitly **refused** (the npm version list self-contradicts, so no cadence claim is drawn). The load-bearing `_local`/`_gateway` claim is self-flagged as **derived across three sources none of which states it**, with its falsifier named |
| `raw/multi_edge_identity_trust.md` | 2026-08-06 | high — 6 weeks | **not-yet-verified** — 655 lines, 25 external + 5 internal sources, **zero rendered HTML fetched** (raw GitHub, GitHub API JSON, IETF `.txt` RFCs, and one PDF paged manually), so no claim inherits that fabrication surface. Deliberately above the §3 10–20 band across four distinct literatures, and says so |
| `raw/decide_only_disposition.md` | 2026-08-06 | high — 6 weeks, on-trigger | **not-yet-verified** — 1,182 lines, 31 external sources. arXiv fetches demonstrably verbatim (preserved source typos and unrendered LaTeX macros). Five sources summarized, marked reduced-confidence at point of use, nothing load-bearing on their wording. Two circulated adoption percentages **not cited** because they came only from a search summary |

**Carried forward, unchanged. The currency table computed at dispatch marks all 21 CURRENT — no paper in the pool is past its window.**

| Paper | Last validated | Revalidate | Critic verdict |
|---|---|---|---|
| `raw/temporal.md` | 2026-08-05 | high — 6 weeks | PASS-WITH-FIXES (three rounds; all 11 counts independently re-derived) |
| `raw/bernstein_capability_mining.md` | 2026-08-04 | high — 2 weeks | PASS-WITH-FIXES |
| `raw/paperclip_assessment.md` | 2026-08-04 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/operator_interface.md` | 2026-08-04 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/dedicated_edge_routing.md` | 2026-08-04 | high — 6 weeks | PASS-WITH-FIXES |
| `raw/fleet_failure_modes.md` | 2026-08-04 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/backbone_edge_generality.md` | 2026-08-03 | high — 6 weeks | PASS-WITH-FIXES |
| `raw/case_against.md` | 2026-08-03 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/code_routed_control_flow.md` | 2026-08-03 | high — 6 weeks | PASS |
| `raw/combination_prior_art.md` | 2026-08-03 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/convergence_stopping.md` | 2026-08-03 | high — 6 weeks | PASS |
| `raw/subscription_economics.md` | 2026-08-03 | high — 2 weeks | PASS |
| `raw/workflow_reuse_boundary.md` | 2026-08-03 | high — 6 weeks | PASS-WITH-FIXES |
| `raw/python_sdk_long_activities.md` | 2026-08-03 | high — 4 weeks | PASS-WITH-FIXES |
| `raw/durable_execution.md` | 2026-07-27 | low — 6 months | PASS |
| `raw/claude_code_integration_surface.md` | 2026-07-25 | high — 4 weeks | PASS |
| `raw/hierarchical_agents.md` | 2026-07-25 | medium — 3 months | PASS |
| `raw/hook_sourcing_supplement.md` | 2026-07-25 | high — 4 weeks | PASS |
| `raw/anthropic_tos_and_enterprise.md` | 2026-07-24 | high — 4 weeks | PASS |
| `raw/production_cases.md` | 2026-07-23 | medium — 3 months | PASS |
| `raw/reflection_literature.md` | 2026-07-23 | medium — 3 months | PASS |

⚠️ **Due within days:** `subscription_economics.md` and `bernstein_capability_mining.md` both fall due around **2026-08-17**; `claude_code_integration_surface.md`, `hook_sourcing_supplement.md` and `anthropic_tos_and_enterprise.md` around **2026-08-22**. The last of those now carries a **live correction candidate** (candidate 3 below), which raises its priority above a routine refresh.

**No papers retired.** One retirement is *recommended by its own paper* and surfaced as candidate 14 rather than applied — see `topics.md` § *Retirements* for why executing it here would have suppressed the finding.

---

## The four things that changed

### 1. Two more comparators, both rejected on architecture, both mined heavily — and the pattern is now a rule

**OpenClaw** and **Hermes Agent** (`NousResearch/hermes-agent`) were assessed for the first time. Both failed test (a) and both paid heavily on test (b): **six** mineable items from OpenClaw, **twelve** from Hermes. Paperclip yielded seven, `bernstein` twenty. **Four for four.** The two-tests rule is no longer a heuristic worth restating each cycle — it is the observed shape of this entire field, and the strategy stated in `problem-statement.md` (*"acquire the lessons rather than re-learn them"*) is being vindicated at roughly ten mineable capabilities per comparator assessed.

**Both rejections are on ALTITUDE, not on quality**, and that distinction governs how the roadmap items must be worded. OpenClaw is a single-operator, single-host **personal assistant** — one long-lived Gateway per host, agents as personas inside that process, durability hand-rolled across SQLite surfaces, and a security policy stating in four places that one Gateway is one trusted operator domain. Hermes is an assistant with messaging gateways across 20+ platforms whose own docs say outright: *"Background completion durability is not durable execution"* and *"A Hermes process restart does **not** resume a running child."* Neither is a competitor to the backbone. **Describing either as an orchestrator would repeat the exact error the Paperclip roadmap item made in its first form.**

**One identification finding worth recording:** "Hermes" is dangerously overloaded — the same organisation (Nous Research) ships both the agent runtime *and* a well-known LLM family, and the agent's own subscription proxy serves those models. The paper ruled out the LLM family and `facebook/hermes` (the React Native JS engine) with a documented method. A less careful pass fuses them.

### 2. The convergent finding neither paper was looking for: Temporal supplies mechanism, nobody supplies POLICY

This is the cycle's sharpest cross-paper result, and it arrived from two independent directions.

**OpenClaw ships a crash-recovery *policy*:** a durable **charged** attempt budget that survives restarts, one durable dispatch identifier for idempotent recovery, a **two-hour staleness horizon** past which an interrupted run is *finalized rather than resumed*, and **tombstoning** as a terminal state. **Hermes ships the liveness half:** progress-based stall detection that replaced a wall-clock cap they *removed* because it kept killing busy children, plus structured terminal metadata with named fields and explicit null semantics.

**Temporal gives the retry mechanism and none of this policy.** Our current shape — `HOLD(redispatch) → one bounded loop-back` — is a budget of one, with no terminal state and no staleness rule. Paperclip's already-mined stalled-run predicate (prior candidate 16) is the third sighting of the same missing layer.

**Consequence for sequencing:** these are not features to add after the port. Hermes's structured failure metadata and progress-vs-liveness distinction are **constraints on what a `claude_cli` activity records**, and a recovery policy retrofitted onto workers already written costs more than one designed alongside them. Total for the whole policy layer: **~1–2 days of design, no build dependency.** This is the cheapest high-value item the pool has produced.

### 3. Differentiator #1 survives — but as a topology statement, not a security mechanism

The trust-boundary claim was the least-evidenced thing in `problem-statement.md` and is now the best-evidenced structurally. Three results:

**The shape is not novel, and that is the win.** Two of three tiers have ratified specifications. SPIFFE's **trust domain** *is* the MDC tier; SPIFFE **federation** *is* the federated tier, and what it moves across the boundary is **public trust material only** — *"A SPIFFE bundle is an object containing a trust domain's cryptographic keys."* The problem statement's *"holds no edge credential"* is a specification someone else already wrote and shipped. Independently corroborated by **Matrix**, which arrived at the same answer for a multi-operator fabric: publish public trust material at a well-known HTTPS URL under web PKI, sign every request with a key the peer never holds, and check expiry at verification rather than maintaining revocation. Matrix additionally supplies a **notary server** primitive SPIFFE lacks — directly useful for an intermittently-reachable MDC.

**The edge tier is where prior art runs out, and the reason is a polarity inversion.** BOINC is the best-documented "edge is a laptop" system and states its threat model outright — projects *"cannot prevent malicious behavior"* — answering with redundancy and validation rather than attestation. But **BOINC protects the project from the volunteer; this design must protect the volunteer's credential from the federation.** Nothing located does that at the compute-placement layer.

**And the honest correction: *"holds its own credential, which never leaves it"* is currently enforced by where the worker runs, not by anything cryptographic.** The credential is a file on disk. If it is a plain bearer token it is copyable by anyone with read access, and the tier boundary holds only because nothing tries to cross it. Until that is settled — **a one-hour experiment, not more research** — differentiator #1 should read *"the design places the credential at the edge and nothing in the federated tier is given a path to it."*

**A separate correction to how the claim is stated at all.** *"Distinct operators in distinct trust domains"* is outside **`bernstein`'s** shipped scope — not outside the industry's. SPIFFE Federation and Matrix both ship it. The current wording is literally precise and a casual reader takes a broader claim from it than is true.

**One item is urgent independently of the whole thesis:** Temporal self-hosted documents that without an explicit Authorizer it *"allows every API request, with no authentication or access control"* and is *"effectively open to anyone with network access."* That is basic hygiene for `Phase: Temporal Integration`, and justifying it via the three-tier differentiator would be motivated reasoning. It belongs in the phase on its own merits.

**The cost shape is the planner's headline:** writing the trust model down (S), closing the Temporal authorizer (M), SPIFFE-ID-shaped queue naming (S), and human-in-the-loop join tokens (S) cover the boundary that actually exists today. The three items that make the model *sound* expensive — a federated bundle endpoint, device-bound credentials, laptop hardware attestation — are all correctly deferred: on a missing second MDC, a missing vendor capability, and missing hardware respectively. **The three-tier model is cheap to commit to and expensive to complete, and the cheap part is the part that matters this year.**

### 4. Element 2's sharpest claim is UNEVIDENCED at exactly the joint it claims — and the topic is done

Three cycles of displacement bought a clean, uncomfortable answer. The two seams must be separated:

- **`author ≠ judge` — SUPPORTED.** Self-preference bias tracks self-recognition causally; same-actor critique is repeatedly shown to fail or actively degrade output. This repo's own strongest internal evidence — a fresh-context pass catching in minutes what engineer self-review, four in-context review agents and manual verification all missed — is on-domain.
- **`decide ≠ act` — UNEVIDENCED.** **No controlled comparison exists anywhere** holding evaluator, artifact and task constant while varying only whether the evaluator may edit. Not in the LLM-agent literature, not in automated code review, and not in fifty years of inspection literature — where *"find defects, do not design fixes"* has been doctrine since Fagan 1976 but appears **never to have been isolated as an experimental variable.**

**The risk the dispatch named landed exactly as feared:** every located result that appears to validate element 2 is a **context-separation** result, not an **authority-removal** result. `problem-statement.md`'s claim that *"the layering is what makes the improvement real"* is currently carried by the easier half of the comparison.

Three things soften this without converting it to support: the decide-only shape is **what the field converges on when it ships** (SWE-Review's reviewer that decides and gives structured feedback, OpenAI Agents SDK output guardrails that halt rather than rewrite, GitHub Copilot's comment-never-approve review, Cognition shipping review and autofix as separate wired products); the classical antecedents assign the fix to the author **by construction** (Fagan inspection, NASA IV&V's technical/managerial/financial independence, SEC treating auditing one's own work as per-se impairment); and **the counter-argument has no source either** — nobody has evidenced "a reviewer who must produce the fix reviews more carefully." Both sides are unevidenced, which is a fairer statement of the position than either side alone.

**The live contradiction resolved, and the source closed it itself.** A targeted re-fetch established that Cognition's "Don't Build Multi-Agents" **does not distinguish agents that act from agents that only read/critique** — so `case_against.md` §2.3.4's extrapolation is *unsupported by it* rather than *contradicted by it*. More usefully, the paper **verified the follow-up that `case_against.md` §5.4 could only mark UNVERIFIED**: "Multi-Agents: What's Actually Working" (04.22.26), whose refined principle — *"multi-agent systems work best today when writes stay single-threaded and the additional agents contribute intelligence rather than actions"* — is a first-party endorsement of precisely the decide-only shape. **A judge that rules and cannot edit is the canonical instance of an agent contributing intelligence rather than actions.** It does not close the gap (no contrast arm), but it converts a standing contradiction into a resolved scope difference.

---

## Corrections that trace to dependents

Per §4 a corrected fact enumerates **every** doc site and derived claim it touches, not just the most visible one.

| Correction | Traces to |
|---|---|
| **The February/April-2026 Anthropic OAuth-enforcement claim is not first-party corroborated.** OpenClaw's own docs document **no consumer-OAuth extraction path for Anthropic at all** (the routes are an API key, host-local `claude -p` reuse, and `claude setup-token`); no Anthropic first-party surface fetched records the enforcement; the one rendered article contradicts itself on its own date; and Anthropic's own support article (updated 2026-06-16) states the Agent-SDK billing change is **paused** and `claude -p` still draws from subscription limits | `anthropic_tos_and_enterprise.md` §3.3 (the claim itself, at its **2026-08-22 refresh**); `problem-statement.md` § *Affordability is the enabler* (which is **strengthened**, not weakened); `subscription_economics.md` (same direction) |
| **The Cognition contradiction is a scope difference, not a disagreement — and a newer first-party post endorses the decide-only shape** | `case_against.md` **§2.3.4** (the extrapolation), **§5.4** (the UNVERIFIED follow-up, now verified) and **D7**; `topics.md`'s gap entry (rewritten this cycle); `convergence_stopping.md` (the contradiction is withdrawn — no edit needed, but its next refresh must not re-raise it) |
| **Differentiator #4 (domain generality) is weaker still.** Paperclip generalised its execution boundary; **OpenClaw was never code-shaped at all**, and Hermes is positioned as an assistant whose front door is a messaging gateway and whose first-class session sources include **Home Assistant — our own stated next edge.** What survives is not generality but *generality plus durable multi-operator orchestration* | `problem-statement.md` § *Where we actually differ* #4; `backbone_edge_generality.md`; `bernstein_capability_mining.md` §0.1; **prior candidate 7, now under-stated and to be re-issued at the stronger wording** |
| **Subscription-auth at the edge is infrastructure, not a differentiator — third and fourth independent confirmations.** OpenClaw is load-bearing on it at very large scale; Hermes **tools** it with a rotation pool that auto-discovers `~/.claude/.credentials.json` | `problem-statement.md` § *Not differentiators* (already correct — this **confirms** it); `paperclip_assessment.md` §4.6; **prior candidate 18, now over-determined and closable** |
| **Differentiator #1's wording overstates by implication.** "Outside the closest system's shipped scope" is true; readers take "outside the industry's" | `problem-statement.md` § *Where we actually differ* #1 and its tier table; `bernstein_capability_mining.md` §0.2; **prior candidate 9, to be issued at the narrower wording rather than as drafted** |

---

## Three prior candidates are WITHDRAWN as moot

Cycle 3 was dispatched without knowing that **Temporal Cloud was ruled out on 2026-07-12**. That decision is now recorded in `system-overview.md` § *Deployment target* (self-hosted, two servers never combined, HA on k3s, systemd workers). The following are withdrawn — recorded rather than deleted, so a fifth cycle does not resurrect them:

- **Prior candidate 1** (heartbeats are billable on Cloud) — the **billing half is moot**. The *transport* half stands and is already in `python_sdk_long_activities.md`; no amendment is owed.
- **Prior candidate 2** (schedule the self-host-vs-Cloud decision) — **the decision was already made, three weeks before the candidate was written.**
- **Prior candidate 5** (Lambda's 15-minute activity cap rules it out) — **moot**: serverless workers are not the deployment.

**Prior candidates 3, 4 and 6 stand unaffected** — shard capacity as a build-time one-way door, the unlimited-max-attempts retry default, and the absence of any first-party Claude↔Temporal runtime integration are all self-hosted concerns.

---

## Action candidates

Reviewable items, sized for a standup. Nothing is ratified. Per §7 this run surfaces candidates and **writes nothing outside `research/`** — routing is the reviewer's and the operator's.

**New this cycle (1–15).** **Carried forward (16–26).**

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Design the recovery POLICY layer before workers are written** — a durable *charged* attempt budget, a staleness horizon past which an interrupted run is finalized not resumed, and a `wedged` terminal state that is surfaced rather than retried. Temporal supplies the mechanism and none of this. ~1 day | adopt | `openclaw_assessment.md` §4.2, §6; corroborated by `paperclip_assessment.md` §4.4 |
| 2 | **Adopt progress-based stall detection over a wall-clock cap, and structured terminal metadata with named fields and explicit null semantics.** Hermes *removed* its wall-clock cap because it kept killing busy children — that scar is free. Both are constraints on what a `claude_cli` activity records, so they land **before** workers, not after | adopt | `hermes_assessment.md` §4.3, §4.4 |
| 3 | **Re-scope `anthropic_tos_and_enterprise.md` §3.3's OAuth-crackdown line at its 2026-08-22 refresh.** No first-party corroboration located; the one fetched article is self-contradictory; Anthropic's own June-2026 article says the change is **paused**. This *strengthens* the affordability thesis — do not let a weakly-sourced line quietly weaken a load-bearing claim | change direction | `openclaw_assessment.md` §4.1(d), §6 |
| 4 | **Reword differentiator #1 to what is currently true**: *"the design places the credential at the edge and nothing in the federated tier is given a path to it"* — a topology statement, not a credential property. Restore the stronger wording only if candidate 5 shows the credential is sender-constrained | change direction | `multi_edge_identity_trust.md` §0.3, §7 |
| 5 | **Run T1: is the Claude Code edge credential a plain bearer token, and does its issuer support sender-constraining?** A **one-hour experiment**, not a research topic, and the single highest-leverage unknown in the trust model — it gates candidate 4's reversal and the whole device-bound-credential branch | adopt | `multi_edge_identity_trust.md` §8 T1/T2 |
| 6 | **Close Temporal's default `noopAuthorizer` in `Phase: Temporal Integration`** — self-hosted Temporal is documented as open to anyone with network access. Plugin points named (`ClaimMapper`, `Authorizer`, per-namespace read/write/worker/admin). **Urgent independently of the three-tier thesis; do not justify it via the differentiator** | adopt | `multi_edge_identity_trust.md` §6 item 8 |
| 7 | **Write the trust model down as a standard** — the three tiers and exactly what may cross each boundary, citing SPIFFE's ratified vocabulary. Cost **S**, highest value per hour in the paper's cost table, and it is the artifact that stops the claim being re-derived wrongly — a failure this repo has already documented once | adopt | `multi_edge_identity_trust.md` §6.1 item 1 |
| 8 | **Name Temporal queues the way SPIFFE names an ID** — a hierarchical, machine-parseable path that encodes what a worker may hold. **Free before workers exist, expensive after**, and it answers the roadmap's open queue-naming question | adopt | `multi_edge_identity_trust.md` §6 item 5, §6.1 item 3 |
| 9 | **Adopt `GET /v1/capabilities` as the edge's capability-advertisement primitive** — a machine-readable capability document served *by* the edge. This is the missing half of the dedicated-edge model: differentiator #2 says work is pinned to a machine, and nothing currently lets a machine *say what it is*. Cost **S** | new concept | `hermes_assessment.md` §4.1; complements `paperclip_assessment.md` §4.5 |
| 10 | **Upgrade the completion contract from one field to five, and run deterministic quality gates BEFORE the LLM judge.** Gate-before-judge is the ordering insight — cheap deterministic checks should never be paid for in model calls | adopt | `hermes_assessment.md` §4.2 |
| 11 | **Adopt "discover, never copy" as a stated credential rule** — an edge resolves a credential in scope at runtime, and OAuth refresh material is **never** propagated between edges (single-use/rotation hazard). Cost: hours. Standards-amendment candidate for the worker/edge standard | adopt | `openclaw_assessment.md` §4.3; corroborated by `hermes_assessment.md` §4.9 |
| 12 | **Create two already-answered `roadmap.md` § *Tools to Evaluate* entries — OpenClaw and Hermes — both `MINE AND DISCARD`, no evaluation gate.** The reason is not completeness: **a future reader who finds the two largest projects in this category absent from our planning will reasonably conclude we never looked.** Both entries must say *personal assistant / assistant runtime*, **never** *orchestrator* | adopt | `openclaw_assessment.md` §7; `hermes_assessment.md` §7 |
| 13 | **Re-issue prior candidate 7 at its stronger wording.** Differentiator #4 has now been narrowed three times; the honest residual is *generality plus durable multi-operator orchestration*, and Hermes treating Home Assistant as a first-class session source means **our stated next edge is already someone else's shipped integration** | change direction | `openclaw_assessment.md` §6; `hermes_assessment.md` §5d |
| 14 | **Rule on the decide-only topic: retire the research topic, keep the shipped design, promote the question to the experiment queue** — with an **on-trigger** revalidation (a published reviewer-who-fixes-vs-judge-only ablation, most likely a new arm on c-CRAB or SWE-Review) that lapses into retirement on **2026-09-17** if it has not fired. Surfaced, not applied — retiring it here would have excluded the finding from this synthesis | new concept | `decide_only_disposition.md` §11; `topics.md` § *Retirements* |
| 15 | **Split the pool into three sub-pools by destination — thesis / competitive-read / plan.** §2 prescribes this for a component materially over its band and the check has been deferred three cycles; at 25 topics it resolves cleanly (9 / 5 / 11) and each part sizes normally. **A research run must not execute it** — it moves files and re-points every `Feeds:` line | new concept | `topics.md` § *Sizing*; Research Standard §2, §6 |
| 16 | **Decide shard capacity deliberately before the first self-hosted workflow runs** — fixed at build time, not adjustable later | adopt | `temporal.md` §3.1, §8 T2 |
| 17 | **Override the default retry policy on every activity wrapping a paid API** — Temporal's default is unlimited max attempts | adopt | `temporal.md` §2.2, §5 |
| 18 | **Scope `Phase: Temporal Integration` on the basis that no first-party Claude↔Temporal RUNTIME integration exists** — the hand-rolled integration is not a temporary state to wait out | adopt | `temporal.md` §6.3 |
| 19 | **Issue the differentiator #1 trust-domain amendment at the NARROWER wording** — outside `bernstein`'s shipped scope, not outside the industry's | change direction | `bernstein_capability_mining.md` §0.2; `multi_edge_identity_trust.md` §7.4 |
| 20 | **Replace differentiator #2's wording with the credential version** — replacement wording already drafted | change direction | `dedicated_edge_routing.md` §7 |
| 21 | **Resolve the queue-axis conflict with the vendored Worker Deployment Standard before `Phase: Temporal Integration` is planned.** Now interacts with candidate 8 — settle both together | new concept | `dedicated_edge_routing.md` §4.1 |
| 22 | **Ship the three cheap guards: credential expiry, false completion, safety-hook wiring test. ~9 operator-hours** | adopt | `fleet_failure_modes.md` §7 |
| 23 | **Do NOT build an operator dashboard.** Build the blocked-work notifier (1–2 days) and give the inbox a roadmap home (0.5 days) | no change *(the negative is the finding)* | `operator_interface.md` §0, §6 |
| 24 | **Adopt the eight cost-S, dependency-free interface/doctrine items from the `bernstein` mining pass** | adopt | `bernstein_capability_mining.md` §5 |
| 25 | **Fix the missed-window assumption in `roadmap.md` — it is backwards, verified against the code** | change direction | `fleet_failure_modes.md` §5.2 |
| 26 | **Reconsider giving up cross-machine failover for *all* work** — Temporal's own pattern is two-tier. **OpenClaw supplies a third option nobody had costed: inference-proxying** (compute fungible, credential not, proxy between). Not a build item — input to the open ruling | new concept | `dedicated_edge_routing.md` §5, §7; `openclaw_assessment.md` §4.5 |

**Closed this cycle.** Prior candidate 13 (close the Paperclip gate) — done; `roadmap.md` carries the resolved entry. Prior candidate 18 (drop uniqueness framing on subscription-auth) — **over-determined**: four independent confirmations now exist and the problem statement already states it correctly. Prior candidates 1, 2 and 5 — **withdrawn as moot**, above.

---

## Homeless findings

Named here rather than parked elsewhere, per §7 — a homeless finding means the surface is missing.

- **This repo still has no surface that holds "an upstream standards amendment we owe."** Carried from four prior cycles. The Research Standard is **vendored MIRROR** from `MDC-Master-Planning`, so amendments cannot be made here. **The missing surface is the finding**, and the debt is growing: the §3-not-checked-on-the-way-in amendment, the two methodology findings, and now a fifth (below).

- **A NEW owed amendment: §2's "check whether it is one component and split it" has no owner and no trigger, so it has been deferred three cycles running.** The rubric prescribes the response; nothing forces the check. A band overshoot is visible on every cycle and skipped on every cycle because splitting is expensive and nobody's job. Candidate 15 is the specific instance; **the general defect is that §2's remedy is an instruction with no actor.**

- **The counter-argument to decide-only has no source at all.** Nobody has evidenced *"a reviewer who must produce the fix reviews more carefully because it bears the cost of being wrong."* This is homeless in an unusual way: it is not a candidate, it is the observation that **both sides of a design question this repo has already shipped are unevidenced**, and the pool has no surface that holds *"a claim we believe and cannot source in either direction."*

- **A count or a quote read through a summarizing fetch layer is unreliable — corroborated a FOURTH time, and this cycle produced the cleanest instance yet.** The OpenClaw run recorded a summarizing fetch returning **two quotation-marked spans that a verbatim re-fetch of the same page did not contain** — not a wrong total this time but fabricated *quoted text*, thesis-convenient in both cases, and caught only because the analyst re-fetched verbatim. The Hermes run independently **refused a count** because the npm version list self-contradicted. Four corroborations across four analysts and four source classes is well past observation. Same missing upstream surface.

- **A defined shape for production feedback.** Carried from four prior cycles and still homeless.

- **An "experiment queue" does not exist, and this cycle produced four items that belong in one.** Candidate 5 (is the edge credential a bearer token — one hour); the decide-only A/B against this repo's own logs; whether `review-pr`'s decide-only property is enforced by **tool permissions or merely by prompt** (the difference between a seam and a convention); and the loop-detector noise question. **These are not research topics and not build items**, and the `topics.md` gap list is the wrong home — that list holds things research did not cover, and these are things research has correctly *finished with*. They are currently accumulating in test-plan sections nobody sweeps.

---

## Gaps this cycle did not cover

- **The quota-headroom view — per-edge rate-limit capacity as the scarce resource.** Genuinely novel, falls out of the affordability thesis, and **not sequenceable yet** — blocked on one minutes-long test and one unread document. **It inherits the displacement warning the decide-only topic just discharged: it is now the oldest un-actioned item on the list.**
- **Whether an agentic `claude -p` run decomposes into resumable per-turn legs** — still uncovered; decides the port's shape.
- **`HERMES_TENANT`** — appears once in a Hermes env table and nowhere else across five directory listings and eleven fetched docs. **The one gap that could move Hermes's architecture verdict rather than refine it**, and cheap to close at that paper's 3-week refresh.
- **The OpenClaw/Clawdbot/Moltbot lineage** — a migration importer is consistent with either a rename or a courtship; not inferred, stated as a gap.
- **Whether this fleet's actual laptops have a usable hardware root of trust** — a hardware survey, not research. Gates nothing today, because the paper recommends **not** building hardware attestation.
- **Temporal patching/versioning cost** and the **OpenAI Agents GA-vs-Preview contradiction** — both left open by the prior refresh, both stated with search methods in `temporal.md` §9.
- **Provider-shaped edges** — partially served as a side-effect this cycle (both new papers report what a non-Claude edge exposes), but the destination is still a stub and the topic is not answered.
- **Duplicated prompt prose**, **inter-process handoff wire format** (phase-level, redirected), **reflection-channel mining**, and **bash → Python Stage A** — unchanged in status.
- **Certification and conformity regimes for a physical edge** — still unanswerable without paid standards access.
