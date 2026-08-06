# Synthesis — product-level research

**Cycle:** 2026-08-06 (cycle 4) · **Pool:** 25 papers · **Tier:** Large / architecture-layer · **This cycle: 4 papers added, 0 retired, 0 revalidated**

Read this instead of the pool. It says what the evidence means for the product's direction and ends in reviewable candidates. Nothing here is binding — research is evidence, and a finding becomes a rule only by being codified into a standard through human review.

> ## ⚠️ THIS IS A DRAFT
>
> **The four new papers carry `Critic: not-yet-verified`.** In the decomposed research pipeline, verification is a separate fresh-context run that checks every source, applies corrections, and traces each correction through to this document per §4's trace-to-all-dependents rule. **Every claim below that rests on a cycle-4 paper is unverified evidence and every consumer must treat it as such** (§3). The 21 carried-forward papers were verified in prior cycles and their verdicts are cited below.
>
> **Highest-priority verification targets, named so the verify run does not have to find them:**
> 1. **OpenClaw's star count (385,334)** — it is the sole basis for "nearest by adoption" and it is an extraordinary number. Sourced to a GitHub API JSON field, which is first-party, but it is ~5× the previously-largest datum in this pool. If it is wrong, one designation claim falls; nothing else does.
> 2. **`decide_only_disposition.md`'s quantitative spans** — the F1 figures and p-values attributed to a single-author preprint (arXiv:2603.12123), and the Fagan page-number transcriptions, which were read from **page images** because the PDF has no text layer. The paper marks both honestly; they still need checking.
> 3. **Every long quoted span in `hermes_assessment.md`** — its analyst measured the fetch layer refusing one full-document reproduction while granting others in the same session, and returning re-wrapped text on a re-fetch. It responded correctly by keeping all spans short, but the provenance guarantee is weakened session-wide. See § *Homeless findings*.

---

## Inputs

**Added this cycle.** All four are unverified — see the draft warning above.

| Paper | Last validated | Revalidate | Critic verdict |
|---|---|---|---|
| `raw/openclaw_assessment.md` | 2026-08-06 | high — 3 weeks | **not-yet-verified** |
| `raw/hermes_assessment.md` | 2026-08-06 | high — 3 weeks | **not-yet-verified** |
| `raw/edge_identity_trust.md` | 2026-08-06 | high — 6 weeks (mixed-volatility; slow sections marked `[LOW]` in the body) | **not-yet-verified** |
| `raw/decide_only_disposition.md` | 2026-08-06 | medium — 2 months | **not-yet-verified** |

**Carried forward, unchanged. The currency table computed at dispatch marks all 21 CURRENT — no paper in the pool is past its window.**

| Paper | Last validated | Revalidate | Critic verdict |
|---|---|---|---|
| `raw/temporal.md` | 2026-08-05 | high — 6 weeks | PASS-WITH-FIXES (two independent critic passes) |
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

⚠️ **Coming due:** `subscription_economics.md` and `bernstein_capability_mining.md` around **2026-08-17**; `claude_code_integration_surface.md`, `hook_sourcing_supplement.md` and `anthropic_tos_and_enterprise.md` around **2026-08-22**.

**No papers are retired**, so no paper is excluded from this synthesis.

---

## What this cycle found

### 1. Differentiator #1 survives as a design and dies as a novelty — and both halves matter

This was the cycle's primary target: the strongest claim in `problem-statement.md`, resting entirely on a competitor's *absence*. It now rests on positive evidence, and the evidence cuts two ways at once. **Per §4 both halves trace to the same document section and must move together — reporting either one alone misleads.**

**It dies as a novelty.** The three-tier Edge/MDC/Federated table is **SPIFFE Federation with different nouns** — administratively isolated trust domains exchanging only public key material, so a foreign domain can validate identities it cannot issue. `edge_identity_trust.md` §2.1 calls this near-verbatim from the specification. Stating the topology as an invention *"would not survive first contact with a reviewer who knows SPIFFE."* The same paper finds the dispatcher-without-target-credential property shipped at mass scale in CI→cloud OIDC, and available in our own substrate — Temporal's data converter leaves payloads unencrypted *only* on client and worker hosts you control.

**It survives, and gets stronger, on a narrower claim.** Every model surveyed — SPIFFE, OIDC federation, Vault, Kubernetes, every cloud workload-identity product — assumes the edge credential is **mintable by an authority inside one of the tiers**. That is the whole mechanism. Ours is not: it is a per-person consumer subscription minted by a fourth party, which the edge cannot attenuate, cannot delegate, cannot present a proof-of-possession for on the backbone's behalf, and is contractually forbidden from sharing. **The topology is therefore *forced*, not *chosen*** — and a competitor cannot "just add" it without acquiring the same constraint.

**And the empirical half strengthened three times over.** Cycle 3 had one first-party statement (bernstein: *"not multi-tenant in the security sense"*). This cycle adds two more, independently:

- **OpenClaw** documents its isolation as *"usability features, not security boundaries"*, *"not hostile multi-tenant isolation"*, and *"Resistance to a compromised host is a non-goal"* — across four separate files.
- **Hermes** documents its multi-tenancy as namespacing (*"only the data is scoped"*), with managed scope self-described as *"a management-convenience boundary against a normal user, not an un-escapable sandbox."*

**Three shipping systems, three vendors, all volunteering the same limit in their own documentation.** That is no longer an absence; it is a pattern, and it is the most robust evidence in the cycle.

### 2. The price of differentiator #1, which nobody had costed

`edge_identity_trust.md` §0.3 is the finding a planner most needs and the one this pool has never had. The closest **operational** analogue to *"a federated layer dispatches work onto a machine holding a credential the dispatcher does not have"* is a **self-hosted CI runner** — and both major vendors publish guidance against exactly that configuration. GitHub: a self-hosted runner *"should almost never be used for public repositories"* and *"can be persistently compromised by untrusted code in a workflow."* GitLab corroborates independently that a Developer-role user *"could compromise the security of the environment hosting the runner."*

**This does not refute the trust model. It prices it** — and the price is ephemeral, isolated execution at the edge, which is precisely what a laptop is bad at. The paper's §5 table is the honest inventory: of nine laptop-edge failure modes, connectivity and NAT are **solved** (by pull-only dispatch, which Temporal already gives us); credential/session expiry at an unattended edge is **unsolved and undocumented anywhere**; and two are **assumed away by every mature model** — no HSM or managed attestation root, and the user being able to read every secret on their own machine.

That last one has an honest resolution the paper names: the credential is *theirs*, so the user being inside the trust boundary may be acceptable. **Saying so explicitly is the resolution; leaving it unsaid is the risk.**

### 3. The comparator set holds two categories under one heading — found independently by both analysts

`roadmap.md` § *Tools to Evaluate* treats its entries as one list. Both new comparator papers reached the same conclusion without seeing each other's work:

- **bernstein and Paperclip compete with the backbone.**
- **OpenClaw and Hermes compete with Claude Code** — the runtime our edge already *contains*.

Judged on backbone axes, Hermes *"fails trivially and teaches nothing"*; judged as an edge runtime it is the most feature-complete open comparator to the thing sitting inside our edge. The category error is why an unassessed comparator looked low-priority for three cycles.

**Consequence for the thesis:** *"nearest neighbour"* now needs an axis. **bernstein keeps it by architecture** — OpenClaw explicitly refuses the orchestrator role, listing *"Agent-hierarchy frameworks"* and *"Heavy orchestration layers"* among its published non-goals. But **OpenClaw is nearest by thesis** — credential at the edge, domain-general assistant, your own machines, supervised long-lived process. A reader who only knows bernstein will over-rate differentiators #1 and #4.

### 4. Both comparators fail test (a) and both pay off on test (b) — the Paperclip precedent holds a third and fourth time

The two-tests rule earned its keep again. Neither architecture is adoptable; **eighteen items were mined between them.**

- **OpenClaw: do not adopt, and do not build on** — *"and it agrees."* Its own `VISION.md` commits its stewards not to build the layer we would need; the topology is centre-and-peripherals where ours is peers; durability is bespoke SQLite; the trust unit is one operator per Gateway, scaled by running N whole instances.
- **Hermes: do not adopt as a backbone** — *"Kanban is deliberately single-host"*, crash detection *"assumes PIDs are host-local"*, no execution-state resume, and adopting it means running a second agent runtime underneath the one we already run.

**De-confliction (the Hermes analyst explicitly asked the synthesis to do this): there are no true double-counts, but there are three genuine convergences that must be planned as single work items, not as six.**

| Convergence | Sources | Why it is one item |
|---|---|---|
| **Pre-worker recovery design** | OpenClaw's per-subsystem restart-recovery contract + durable dispatch id; Hermes' three-guard liveness (live-PID extend / dead-PID reclaim / absolute cap) | Different guards, one design session, and **both papers independently say "before workers are written."** Planning them separately produces two partial contracts. |
| **The liveness predicate set** | Paperclip's **stalled** (no output); OpenClaw's **looping** (byte-identical output); Hermes' **stranded** (never claimed) | Three papers each supply one leg of a three-legged taxonomy **none of them states**. Liveness ≠ progress ≠ permission-to-continue. This is the cycle's best example of the pool producing something no single source contains. |
| **The typed-result surface** | OpenClaw's `structured_output` + schema-per-call; Hermes' three-verdict `done`/`continue`/`wait` completion contract | Adjacent destinations (`Phase: Memory Management Framework` kind 2, and `Phase: Autonomous Operation` exit criteria) but one vocabulary decision underneath. |

**One mined item unblocks a gap the pool has carried for two cycles.** Hermes' credential pools show that per-edge quota headroom is **derivable from observed provider cap-errors**, without provider telemetry — which **corrects the quota-headroom gap's stated blocker** (*"does the Claude Code result envelope expose remaining quota at all?"*). The gap was marked *not sequenceable*; it now is. **Caveat the analyst raised against its own finding, preserved here:** Hermes' *mechanism* is rotation across multiple credentials and we hold one subscription. **The telemetry transfers; the rotation does not.**

### 5. Element 2 is half-validated, and the standard states two mechanisms as one

`decide_only_disposition.md` — run after three displacements — did not confirm the seam the fleet is built on. It split it.

| Claimed mechanism | Status |
|---|---|
| **Fresh context** — the judge does not carry the author's reasoning | **Supported, directionally, on-domain.** One controlled review-shaped experiment has fresh-context review beating same-session self-review, and — decisively — reviewing *twice* in-session did **not** beat once, which rules out repetition as the explanation. The negative self-correction literature explicitly scopes itself away from the cross-actor case. |
| **No authoring authority** — the judge cannot quietly patch what it found | **UNEVIDENCED as an isolated variable.** Fifty years of human inspection research and the entire LLM-evaluation literature contain **no study that varies "the reviewer may edit" while holding everything else constant.** |

Fagan states the rule in 1976 — *"no specific solution hunting is to take place during inspection… it is intended just to find errors!"* — but his only quality measurement varies seven things at once. **The rule is universally stated and never tested.**

**The actionable consequence:** `workflow-scripts.md § Composition` justifies **both** mechanisms with a single argument — *"A run that both authors work and rules on the review findings about it will defend its own work"* — which is a **provenance** argument and supports only the first. The standard currently implies measured backing that does not exist for the second. That is a standards-amendment candidate, and it is the honest kind: the design may well be right, but the stated justification over-claims.

**Three further findings from the same paper, each independently actionable:**

- **The judge is compromised even with fresh context.** Self-preference bias is causally linked to self-recognition; **`review-pr`'s judge is the same model family as the author** — the configuration the evidence penalises. Cross-family judging is close to a one-line change.
- **The judge may be reviewing the wrong artifact.** `review-pr`'s prompt says *"You are NOT re-reviewing the code"* — it audits the producing run's **self-report**. **Every cited review result measures a reviewer reading the artifact.** The evidence transfers more weakly than the surface similarity suggests, and no literature search fixes this.
- **A precise reviewer does not imply a corrected artifact.** Detection quality and critique uptake are empirically separable. A decide-only architecture makes uptake *a separate stage that is currently unmeasured*.

### 6. A live contradiction inside the pool, adjudicated — and one ranked finding is contradicted by its own source

`case_against.md` and `convergence_stopping.md` are **not in conflict; they are non-overlapping** — different task domains, different topologies (concurrent agents that *act* on shared state vs. sequential agents that *read and report*), different objective functions. The verdict came from independently fetched primaries, not from the sibling papers.

**Two concrete rulings, and the first is material:**

1. **`case_against.md`'s D7 should be downgraded or withdrawn.** D7 derives *"a separate judge loses the author's context"* from Cognition's *Don't Build Multi-Agents*. **That post's own text excludes the transfer:** *"it never does work in parallel with the subtask agent, and the subtask agent is usually only tasked with answering a question, not writing any code."* **A ranked finding in the pool currently argues against the very seam its cited source endorses** — and a planning run could act on it.
2. **`case_against.md` §5.4's UNVERIFIED item is now closed.** The follow-up post exists, was fetched, and its refined principle — *"multi-agent systems work best today when writes stay single-threaded and the additional agents contribute intelligence rather than actions"* — **is the `decide ≠ act` seam, restated by the pool's strongest cited authority against layering.**

**The one genuine conflict is about cost, not defects.** The matched-compute objection stands unanswered: the correct control is not "author alone" but *"author given the judge's budget to keep authoring."* No on-domain paper runs it. That is the experiment, and it is designed against this repo's real surfaces in §7 of the paper.

### 7. One concrete Temporal build consequence, and one build-blocking unknown

**Consequence (documented):** self-hosted Temporal's default is `noopAuthorizer`, which **allows every API request**; the **namespace is the only credential boundary offered**; and authorisation is code we write. There is no free multi-tenancy in the substrate.

**Unknown (a negative finding with method, and it is load-bearing):** whether a worker can be *prevented from polling a task queue it should not serve* has **no first-party documentation** — searched via raw fetches of the security, namespaces and multi-tenant-patterns pages plus enumeration of the production-deployment and self-hosted-guide directories. A custom Authorizer *might* gate polling; the paper marks that a **derived hypothesis** and puts it in its test plan. **The pinned-edge design assumes an answer this gap does not supply.**

---

## Action candidates

Reviewable items, sized for a standup. Nothing is ratified. Per §7 this run surfaces candidates in this document and **writes nothing outside `research/`** — routing is the reviewer's and the operator's.

**All of candidates 1–16 rest on `Critic: not-yet-verified` papers.** Candidates 17–29 are carried forward from prior verified cycles.

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Restate differentiator #1 on the credential, not the topology — and state BOTH halves together.** The three-tier table is SPIFFE Federation renamed; what is unusual is an **exogenous, non-attenuable, non-delegatable, contractually non-transferable** edge credential, which makes the topology *forced rather than chosen*. **Trace note (§4):** this same edit must carry the strengthening — three shipping systems now document their multi-tenancy as not-a-security-boundary. Shipping the narrowing without the strengthening reads as a retreat; shipping the strengthening without the narrowing leaves a novelty claim a SPIFFE-literate reviewer will break | change direction | `edge_identity_trust.md` §0, §6, §7 |
| 2 | **Cost differentiator #1 with the self-hosted-CI-runner warning, and rule on the laptop trust boundary.** Both major CI vendors publish guidance against this exact configuration; the mitigation is ephemeral isolated execution, which a laptop resists. Two failure modes are **assumed away by every mature model** (no attestation root; the user can read their own secrets). The honest resolution — *the credential is theirs, so the user is inside the boundary* — is a **ruling to write down**, not a gap to leave open | adopt | `edge_identity_trust.md` §0.3, §5 |
| 3 | **Settle whether a Temporal worker can be prevented from polling a queue it should not serve — BEFORE the pinned-edge design is built on.** Undocumented first-party; the "custom Authorizer gates polling" answer is a derived hypothesis, not a fact. Cheap to test, expensive to discover late | adopt | `edge_identity_trust.md` §2.8, §9 |
| 4 | **Record that self-hosted Temporal ships `noopAuthorizer` by default and the namespace is the only credential boundary offered.** Authorisation is code we write. No free multi-tenancy in the substrate | adopt | `edge_identity_trust.md` §4 item 11 |
| 5 | **Split `roadmap.md` § *Tools to Evaluate* into backbone comparators and edge runtimes.** bernstein/Paperclip compete with the backbone; OpenClaw/Hermes compete with Claude Code. Found independently by two analysts. Cost 0, and it is why an unassessed comparator looked low-priority for three cycles | change direction | `hermes_assessment.md` §3, §8; `openclaw_assessment.md` §7 |
| 6 | **Give "nearest neighbour" an axis: bernstein by architecture, OpenClaw by thesis.** Two of the four differentiators are now most sharply tested by OpenClaw. **Verification dependency:** the *by adoption* leg rests on the 385,334-star figure and should not be stated until the verify run confirms it | change direction | `openclaw_assessment.md` §3.8 |
| 7 | **Add OpenClaw to the roadmap as ASSESSED-and-closed, not as an evaluation gate.** Proposed entry text is drafted in the paper. Its absence from the comparator set is itself the finding | adopt | `openclaw_assessment.md` §7 |
| 8 | **Add Hermes under the new edge-runtimes heading.** It has no entry to correct — this is an addition, not a rewrite | adopt | `hermes_assessment.md` §8 |
| 9 | **Plan the three pre-worker recovery items as ONE design session, not three.** OpenClaw's restart-recovery contract + durable dispatch id, and Hermes' three-guard liveness. Both papers independently say *before workers are written*. Hours of design; constrains the build | adopt | `openclaw_assessment.md` §6 items 3–4; `hermes_assessment.md` §7 item 4 |
| 10 | **Adopt the three-legged liveness taxonomy: stalled (no output) / looping (identical output) / stranded (never claimed).** Three papers each supply one leg; **none states the set.** Liveness ≠ progress ≠ permission-to-continue | new concept | `paperclip_assessment.md` §4.4; `openclaw_assessment.md` §4.7; `hermes_assessment.md` §5.2 |
| 11 | **Unblock the quota-headroom gap — headroom is derivable from observed cap-errors, no provider telemetry needed.** This **corrects the gap's own stated blocker**, which held it out of sequencing for two cycles. Adopt the provider-error taxonomy and per-credential telemetry (~1 day + hours). **Do NOT adopt the rotation mechanism** — it presumes >1 subscription and we hold one | change direction | `hermes_assessment.md` §5.1, §7 item 1 |
| 12 | **No fallback queue: an unresolvable assignee must PARK with a typed event, never silently fall back.** A **negative** design constraint on `Phase: Temporal Integration` queue topology. Cost 0 — it removes work | adopt | `hermes_assessment.md` §5.3 |
| 13 | **Amend `workflow-scripts.md § Composition`: it justifies two mechanisms with one argument that supports only the first.** Fresh context is directionally evidenced; **no-authoring-authority has no isolating study in fifty years of human inspection research or the LLM literature.** The design may be right; the stated justification over-claims. Standards-amendment candidate — human-ratified path | change direction | `decide_only_disposition.md` §4/P8, §4.6 item 3 |
| 14 | **Withdraw or downgrade `case_against.md`'s D7 — it is contradicted by its own primary source.** **Apply §5's materiality test:** D7 argues against the seam the whole fleet is built on, so if any planning run would act on it, this is an immediate human-in-the-loop re-run rather than a ride on the scheduled sweep. The reviewer rules; this run only surfaces it | change direction | `decide_only_disposition.md` §3.6, §4.6 items 1–2 |
| 15 | **Switch `review-pr` to a cross-family judge.** Self-preference bias is causally linked to self-recognition and **fresh context does not remove it**. The judge is currently same-family — the configuration the evidence penalises. Close to a one-line change | adopt | `decide_only_disposition.md` §3.7, §4/P9 |
| 16 | **Run E1b first — it costs almost nothing and reads out the judge's marginal yield.** Classify 30 PRs' disposition items and cross-classify as already-stated-by-the-run vs. new. No new dispatches; reads existing JSONL logs and PR threads. **If the judge's marginal yield is near zero, that falsifies more cheaply than E1 does** | adopt | `decide_only_disposition.md` §7 |
| 17 | **Correct differentiator #1 (generality) in `problem-statement.md`** — the nearest neighbour already generalised its execution boundary. **Amended this cycle:** OpenClaw is the mirror image — it generalised its *product* without its *boundary* (sub-agents return plain text). The sharper replacement is **domain-general AND typed at the boundary by default — nothing in the pool has both** | change direction | `bernstein_capability_mining.md` §0.1; `openclaw_assessment.md` §3.2 |
| 18 | **Replace differentiator #2's wording with the credential version.** Replacement wording is drafted | change direction | `dedicated_edge_routing.md` §7 |
| 19 | **Reconsider giving up cross-machine failover for *all* work.** **Amended this cycle: a third option exists** — pin the credential and proxy the *model call* rather than moving the work. Critically, OpenClaw documents that this **does not work for `claude-cli` runtimes**, and *that exclusion is itself the argument for today's pinned design.* The open ruling can now be closed with evidence rather than left open | new concept | `dedicated_edge_routing.md` §5, §7; `openclaw_assessment.md` §4.1 |
| 20 | **Resolve the queue-axis conflict with the vendored Worker Deployment Standard before `Phase: Temporal Integration` is planned** | new concept | `dedicated_edge_routing.md` §4.1 |
| 21 | **Ship the three cheap guards: credential expiry, false completion, safety-hook wiring test (~9 operator-hours).** **Reinforced this cycle:** credential/session expiry at an unattended edge is **unsolved and undocumented in any surveyed prior art** — this is not just our gap, it is everyone's | adopt | `fleet_failure_modes.md` §7; `edge_identity_trust.md` §5 |
| 22 | **Do NOT build an operator dashboard.** Build the blocked-work notifier (1–2 days) and give the inbox a roadmap home (0.5 days). **Sequence Hermes' stranded-work severity ladder into the same item** (candidate 10) | no change *(the negative is the finding)* | `operator_interface.md` §0, §6; `hermes_assessment.md` §5.2 |
| 23 | **Adopt the eight cost-S, dependency-free interface/doctrine items from bernstein** | adopt | `bernstein_capability_mining.md` §5 |
| 24 | **Fix the missed-window assumption in `roadmap.md` — it is backwards, verified against the code** | change direction | `fleet_failure_modes.md` §5.2 |
| 25 | **Decide the dedupe granularity as a ruling, not a build** | adopt | `paperclip_assessment.md` §4.3, §6 |
| 26 | **Drop any uniqueness framing on subscription-auth-at-the-edge.** **Now a THIRD independent precedent** — Hermes auto-seeds from `~/.claude/.credentials.json`, OpenClaw proxies model calls so credentials never leave the machine | change direction | `paperclip_assessment.md` §4.6; `hermes_assessment.md` §5; `openclaw_assessment.md` §3.4 |
| 27 | **Add the clause to `python_sdk_long_activities.md`'s heartbeat recommendation.** **AMENDED BY THIS CYCLE:** the prior cycle framed this as a Temporal Cloud *billing* hazard. `system-overview.md` § *Deployment target* rules Cloud off the table, so **the billing half is moot** and the candidate reduces to stating the throttle ceiling for correctness. Retained only so the correction is not re-derived | change direction | `temporal.md` §3.2; `python_sdk_long_activities.md` §1.4 |
| 28 | **Decide shard capacity deliberately before the first self-hosted workflow runs** — fixed at build time, not adjustable later. **Now strictly more urgent**, since self-hosting is settled rather than one branch of an open decision | adopt | `temporal.md` §3.1 |
| 29 | **Override the default retry policy on every activity wrapping a paid API** — Temporal's default is unlimited max attempts. Against a subscription this is a rate-limit hazard | adopt | `temporal.md` §2.2, §5 |

**Retired candidates.** Prior cycle's **#2 (schedule the self-host-vs-Cloud decision)** and its associated Cloud-Action measurement are **retired, not deferred** — `system-overview.md` § *Deployment target* settles it: Temporal is self-hosted and Cloud is not on the table. Prior cycle's **#13 (close the Paperclip evaluation gate)** is done — `roadmap.md` already records the assessment. Prior **#12/#16/#17** are folded into candidates 22, 10 and 25 above.

---

## Homeless findings

Named here rather than parked elsewhere, per §7 — a homeless finding means the surface is missing.

- **This repo still has no surface that holds "an upstream standards amendment we owe."** Carried from four cycles. The Research Standard is **vendored MIRROR** from `MDC-Master-Planning`, so amendments cannot be made here. **The missing surface is the finding**, and the debt now stands at five owed amendments.

- **A THIRD distinct fetch-layer failure class, and this one corrupts provenance rather than content.** Prior cycles measured (i) under-enumeration — page totals reported as populations, seven fetches giving seven different answers with `truncated: false` present and wrong every time — and (ii) silent elision. This cycle adds (iii): the layer **declared a 125-character quote ceiling and refused one full-document reproduction while granting long reproductions of other documents in the same session**, and returned **re-wrapped text** on a re-fetch of a document it had already returned. The analyst responded correctly, keeping every span short and distinctive and asserting no long block as byte-exact — but **one refusal invalidates verbatim status session-wide**, because the artifact can no longer distinguish "exact characters returned" from "reproduced under a ceiling." §3's *"verbatim means the exact characters were returned"* rule is **not satisfiable by the available tooling**, and no amount of analyst discipline fixes that. The remedy the paper proposes is a `git clone` + `grep -F` re-verification pass. **Three distinct failure classes across four cycles is well past the threshold where this is an observation.**

- **The sizing rubric was never applied as written, and this cycle corrects its own predecessor.** Cycle 3 recorded the 21-topic overrun as *"a finding about the rubric"* needing an upstream amendment. **§2 already prescribes the remedy** and uses this pool's own destinations as its example: *"a plan, plus a thesis, plus a competitive read are three consumers, not one — and the correct response is to check whether it is one component before widening the band."* The 25 topics split cleanly into thesis (9), plan (12) and competitive read (4), each at or near a normal band. **The overrun is a splitting signal, not a calibration failure**, and the standard needs applying rather than amending. *(This is this cycle's own inference from §2's text — not an analyst finding. The split itself is a structural change to `research/` and is a decision for the operator, not for a research run.)*

- **`decide_only_disposition.md` measures something the pool has no home for: the shipped `review-pr` audits a run's SELF-REPORT, not the artifact.** Its prompt states *"You are NOT re-reviewing the code."* Every cited review result in the entire literature measures a reviewer reading the artifact. **No further literature search closes this** — it is a category difference between what we built and what anyone has studied, and it silently weakens every evidence transfer in the paper's §3.5. There is no surface that holds *"our design does something the literature has never measured."*

- **A defined shape for production feedback.** Carried from four cycles and still homeless.

---

## Gaps this cycle did not cover

- **Whether an agentic `claude -p` run decomposes into resumable per-turn legs** — uncovered across four cycles; decides the port's shape. **Now the highest-priority uncovered topic for cycle 5.**
- **Attestation of an unmanaged edge machine** — **new, and it is the genuine research frontier under differentiator #1.** Every mature model either owns the device or has a cloud instance-identity document; on an unmanaged laptop, attestation degrades to a pre-shared secret. Narrower and sharper than differentiator #1 itself, and it deserves its own topic.
- **`zeroclaw-labs/zeroclaw`** — surfaced during OpenClaw disambiguation (Rust, *"fully autonomous AI personal assistant infrastructure"*), unassessed. A new edge-runtime comparator candidate.
- **Cross-family judging, and self-report auditing as a distinct task** — both surfaced by `decide_only_disposition.md` as follow-on topics. The first is also candidate 15; the second (N5) is the homeless finding above.
- **Re-authentication of an expired subscription session at an unattended edge** — nothing found across the RFC series, NIST, BeyondCorp or either CI vendor. Unsolved industry-wide, not just here.
- **Ephemeral isolation on an unmanaged laptop that also retains a long-lived session** — no prior art found.
- **The quota-headroom view** is no longer blocked (candidate 11) but is **not yet sized** beyond the ~1 day + hours estimate.
- **Temporal patching/versioning cost**, and the **OpenAI Agents GA-vs-Preview contradiction** — refresh-owned, unchanged.
- **A billable Temporal Cloud Action's cost for this workload** — **retired as a gap**, not deferred: Cloud is off the table.
- **Provider-shaped edges** — still stub-blocked, but note that `hermes_assessment.md` surfaced *"Hermes as a non-Claude edge"* as a coherent future option with evidence, deliberately not sequenced.
- **Duplicated prompt prose**, **inter-process handoff wire format** (phase-level, redirected), **reflection-channel mining**, **bash → Python Stage A** — unchanged in status.
- **Certification and conformity regimes for a physical edge** — still unanswerable without paid standards access.
