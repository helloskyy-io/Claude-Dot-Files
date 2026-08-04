# Synthesis — product-level research

**Cycle:** 2026-08-04 · **Pool:** 21 papers · **Tier:** Large / architecture-layer · **This cycle added 5**

Read this instead of the pool. It says what the evidence means for the product's direction and ends in reviewable candidates. Nothing here is binding — research is evidence, and a finding becomes a rule only by being codified into a standard through human review.

**What changed since the last cycle, and why this synthesis reads differently.** The previous cycle asked *is the combination novel?* and answered no. `problem-statement.md` was then rewritten against that answer: it no longer claims novelty for the four elements, states them as *the known recipe*, and states the intent as **"to execute it better than anyone else, and to acquire the lessons rather than re-learn them."** The altitude also corrected — this repo is **Jarvis, the assistant edge**, under SkyyCommand under SkyyNet, not a standalone product.

That makes this cycle's question a different one: **is the trajectory right, and what are we missing for the end goal?** Every paper this cycle was written to produce roadmap items, not verdicts. **The consumer is a master-planning pass**, and the deliverable is a feature list with costs.

---

## Inputs

**This cycle's five.** All PASS-WITH-FIXES after three critic rounds each. **Zero fabricated sources across ~190 citations** — every correction was a miscited span, a wrong unit, an uncorroborated count, or confidence inflation, never an invented source.

| Paper | Last validated | Revalidate | Critic verdict |
|---|---|---|---|
| `raw/bernstein_capability_mining.md` | 2026-08-04 | high — 2 weeks | **PASS-WITH-FIXES** (3 rounds; ADR-005 spawn-overhead unit corrected per-batch→per-spawn *and the amortization argument rebuilt*; summarizer-derived listing counts withdrawn; cost-S tally nine→eight; §1.3 reworded fabrication→summarizer truncation; headline splice marked and both spans re-verified) |
| `raw/paperclip_assessment.md` | 2026-08-04 | high — 4 weeks | **PASS-WITH-FIXES** (3 rounds; "stalled" definition restored to all three conditions; four→five partial unique indexes with an elided one recovered; commit footprint 36→47; six non-verbatim spans de-quoted; **a round-1 repair that introduced a fabrication caught and reverted**; the coarse/fine pairing claim withdrawn as false for one of its two cases) |
| `raw/operator_interface.md` | 2026-08-04 | high — 4 weeks | **PASS-WITH-FIXES** (2 rounds; the paper's one `[verbatim]` span de-drifted against the page image; a quotation re-attributed off `problem-statement.md`, which does not contain it; a reversed tagline claim corrected. **The critic's own adjacency finding was falsified by the analyst and the critic conceded**) |
| `raw/dedicated_edge_routing.md` | 2026-08-04 | high — 6 weeks | **PASS-WITH-FIXES** (3 rounds; an unsupported StatefulSet quote removed; a vendored-standard citation repointed from a taxonomy section to the mechanism section at five sites; the physical-capability ruling narrowed from five families to three-plus-substrate; load-bearing self-assessment corrected; fetch accounting completed to all 29 sources) |
| `raw/fleet_failure_modes.md` | 2026-08-04 | high — 4 weeks | **PASS-WITH-FIXES** (3 rounds; a manufactured quotation replaced; two negative findings re-methodized after their directory listings proved ~2× short; **the critic's own replacement figure was refused by the analyst and proved wrong**, resolved at round 3 by three agreeing enumerations) |

**Carried forward, unchanged, all current per the computed gate.**

| Paper | Last validated | Revalidate | Critic verdict |
|---|---|---|---|
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
| `raw/temporal.md` | 2026-07-04 | high — 4 weeks | PASS · ⚠️ **PAST WINDOW** (due 2026-08-01) |

**No papers were retired.** `temporal.md` is the pool's only past-window paper; consumers treat it as unverified until `research-refresh.sh` runs (§5). Two papers whose `Feeds:` lines name now-deleted problem-statement sections are re-pointed in `topics.md` rather than edited — see that file for why.

---

## The answer to the cycle's question

**The trajectory is right, and the evidence is stronger than expected in one specific way: the expensive-looking work is mostly already solved by decisions already made.** Temporal ships a first-party design pattern for the edge-routing model the problem statement claims as a differentiator. The operator surface the field is unanimous about is ~70% already built here. The single most expensive lesson in the whole corpus — never put a model in the coordination loop — is a failure this system is *already immune to* and did not pay for.

**What is missing is not machinery. It is a small number of decisions that must be made before workers are written, and about nine operator-hours of guards against failures that will otherwise be discovered in production.**

Three claims in `problem-statement.md` need correcting, and one of them is a headline.

---

## 1. Differentiator #1 has moved. The nearest neighbour generalised its execution boundary

**This is the cycle's headline and it must reach `problem-statement.md`.**

The document states differentiator #1 as *"Comparable systems are built for code — their verification vocabulary is tests pass, lint clean, types correct,"* with evidence marked *"confirmed absent from the nearest neighbor, three independent ways."*

**That is no longer safe.** `bernstein_capability_mining.md` §0.1 found `docs/operations/activity-boundary.md`, which names a five-modality set — **research / browser / data / ops / coding** — requires that *"every modality returns an `ActivityResult`"*, and states that a non-coding modality *"participates through as a replayable step."* Two non-coding modalities have their own shipped docs, and **neither is verified by tests**: research verification re-hashes sources and *"confirms the quoted span still occurs"*; browser verification *"reattaches the DOM bytes by hash and re-evaluates the assertion."*

**What survives, and it is the actionable part:** bernstein's *positioning* is still entirely code-framed — its repo description, front door and all six use cases are software development — while its *execution boundary* is already modality-general. The honest restatement is **"comparable systems are *sold* for code, and the nearest one has already generalised its execution boundary without generalising its product."**

That is a weaker differentiator and **a much better piece of reference material**: the domain-general result contract we were going to have to invent has a shipped, documented shape we can read. It is capability #1 on the take list.

## 2. Differentiator #2 holds — but for the wrong stated reason, and for a bigger unstated one

Two independent papers converge here, and they pull in opposite directions.

**The stated theory is refuted.** `dedicated_edge_routing.md` §3.4 tested *"role-pull assumes fungible workers distinguished by a label"* and ruled it **does not hold**. Labels are exactly how Kubernetes, Slurm and **Temporal itself** address *physical hardware* — Temporal's own docs say *"Some Workers might exist on GPU boxes versus non-GPU boxes… each type of box would have its own Task Queue"* — and bernstein advertises `gpu_available`/`supported_models` inside a claim-based system. Dedicated hardware-bound workers are ordinary in infrastructure; they are unusual only in *agent orchestration*.

**The differentiator that survives every counter-case is the credential.** No label grants another edge the ability to authenticate as a given subscriber. The paper offers replacement wording (§7) that gives up the "different theory of a worker" framing, **ties claim #2 to the affordability thesis the document already argues**, and survives the Kubernetes objection a technical reader raises first.

**And the claim-and-contend half is understated, not overstated.** bernstein's protobuf carries a literal `role` field, `rpc ClaimTask`, `TASK_STATUS_CLAIMED`, and `rpc StealTasks` with `donor_node_id`/`receiver_node_id`, plus a claim journal resolving contention by lexicographically lowest `entry_hash`.

**The strongest position in the whole comparison is one the problem statement does not currently make.** `bernstein_capability_mining.md` §0.2: bernstein's fleet mode is *"multi-project, **not** multi-tenant in the security sense… assumed to be run by the same operator, on a network the operator trusts"*, and its federation v1 limitations explicitly list *"Cross-tenant federation across organisations."* **SkyyNet's destination — many MDCs, distinct operators, distinct trust domains — is outside the nearest neighbour's shipped scope by its own documentation.** That is a stronger and more durable claim than any scheduling-model difference.

**One real cost the narrowing exposes:** the design currently gives up cross-machine failover for *all* work, not only for work with a genuine locality requirement. Temporal's own pattern is **two-tier** — it retains a shared queue alongside pinned ones. That is the reason the verdict is "narrowed" rather than "holds."

## 3. The operator interface: the field is unanimous, and the answer is still mostly "don't build it"

`operator_interface.md` verified **ten of ten** comparable systems ship an operator surface, first-party, with **no located counter-example** — including one built on tmux by AWS Labs that turned out to ship a Web UI. So the requirement is real.

**But it is already ~70% met here, and almost none of the remainder is a dashboard.**

- **The blocked-work inbox — the element the field converges on hardest — already exists** as `HOLD` PR verdicts + Issues + `/standup`. It is *better designed* than the shipped alternatives on the two axes the human-factors literature says decide whether an inbox works: `/standup` has a **staleness detector** (the aging flag) and a **filer-calibration loop** (invalid closes treated as tooling defects). Paperclip's approvals surface documents neither; bernstein's holds expire silently by TTL.
- **Git-as-control-plane is legitimate, not a stopgap.** Atlantis has run exactly that model in production for years; its one bespoke UI screen exists for locks — state a VCS cannot represent. That yields the design rule: **build bespoke surface only for state git cannot hold.**
- **The genuine gap is liveness, not decisions.** Git has no representation for *in flight*. A dispatch that hangs at minute forty produces no PR, no issue, no artifact of any kind. **And that is precisely the axis the Temporal port supplies for free** — building a run-state view before the port is building the thing the port deletes.

**Recommended pre-port build: order 3–5 engineer-days, against a dashboard's 20–40.** The negative is the valuable half.

## 4. What the field learned the hard way — the free lessons

`fleet_failure_modes.md` is the cycle's highest-value output and its results split cleanly.

**Already immune, stated so the planner does not sequence work for them:** LLM-in-the-coordination-loop (*"A parent calls no model"* — the pilot that killed this design had a manager agent that *"fell asleep regularly. When it did, every downstream agent starved"*, with 3 of 12 agents reliable); persistent-session sleep and signal-spam; file-lock deadlock; headless early-stop; turn-cap exhaustion.

**Most exposed, and none of it deleted by the Temporal port:**

1. **Credential expiry/wipe at an unattended edge.** Two `anthropics/claude-code` issues describe *exactly* our configuration — Max OAuth, headless `-p`, in a loop, unwatched. One reports the credential replaced with an **empty value** on a failed refresh, so *"The agent appears to start normally but can't make any API calls"* and *"The human may not notice for hours."* **Our affordability thesis requires this configuration, the vendor's suggested fix is an API key which breaks that thesis, and nothing in the system detects it today.** ~2h to mitigate.
2. **A run emitting the right completion token without doing the work.** The corpus's one measured rate: *"2 real code commits out of 40 it claimed."* This is the *precondition* for an unattended driver — a driver routing on a false completion compounds it. ~4h.
3. **The only live safety control could silently stop firing.** bernstein shipped **three separate wired-but-dead guards**; our `PreToolUse` hook is the sole control during autonomous runs, and `Phase: Managed Configuration` already flags a change that would strip it. ~3h.

**Exit criteria — the roadmap asked, and the field answered.** Every criterion tried *alone* failed: message count (283 messages, 0 commits), process liveness (Paperclip added four output-progress columns; bernstein caps log-mtime liveness at three ticks because ~35 of ~40 adapters merge stderr into the log), model self-report (*"an unfinished task could be marked done with an invented summary"*), and context-window occupancy (*"no clear correlation between failures and the point at which the model's context window becomes full"*). **What survived is a conjunction of three independent things.**

**Missed-window behaviour — the roadmap's assumption is backwards, verified against the code.** It says "skip is fine" for a CPI sweep and skipping "lets a paper rot" for research revalidation. But `review-runs.sh` selects logs with `find … -mtime "-${DAYS}"` — a **trailing window relative to now**, so a skipped weekly sweep loses those seven days permanently. Research revalidation's gate is date-based and **self-healing**; it needs a consecutive-miss alarm, not catch-up. **The real discriminator is window-scoped vs. state-converging, not importance.**

## 5. Paperclip: architecture rejected, seven capabilities taken, and the roadmap item is wrong

`paperclip_assessment.md` closes the open *"evaluate after Phase 4"* item ahead of its gate. **Verdict: MINE AND DISCARD.**

Architecture rejected on four grounds — an org-chart ontology where the machine is a *separate* axis (its agent is exactly the "differently-labeled one" the problem statement rejects), durability re-derived per feature rather than supplied by a substrate, server-side secret injection, and an imported product ontology.

**But the item's own text is wrong and should be replaced, not just answered.** It attributes *"visual workflow design"* and *"PR review"* to Paperclip; the README explicitly disclaims both (*"Not a workflow builder. No drag-and-drop pipelines."* / *"Not a code review tool."*). And its framing — *"may overlap with native headless mode + triggers"* — **has been the wrong question since it was written**: Paperclip *invokes* headless Claude Code as its substrate. They are complements.

**The highest-value find is a scar, merged the day of the sweep.** Agents move work to `in_review` and depend on a review path telling them who decides next; that path silently disappears, and *"Such issues become invisible zombies. Nobody knows a decision is owed, so the work stalls forever."* Their fix explicitly **rejected** both a background auto-recovery sweep (*"invisible to the human"*) and a status banner (*"gives no action to resolve the stall"*). **That failure mode is live here today** — "Open is the to-do bit" has no notion of who owes a decision, and nothing detects a stalled one.

**Two claim corrections fall out.** Subscription-auth-at-the-edge **has precedent at scale**, so any uniqueness framing should drop. And *"the common model is central-queue role-pull"* **overstates** — the field has at least three shapes, and Paperclip is a third (directed assignment to a named agent plus atomic checkout with `409 Conflict`).

---

## The plannable list — consolidated by roadmap destination

Every item carries a cost. Costs are **derived** in their source papers with inputs named. This is the master-planning pass's working set.

### Before any worker is written — decisions, ~1 week of planning, no build

| Item | Why now | Cost | Source |
|---|---|---|---|
| **Classify every workflow repo-local vs machine-independent** | Gates queue axis, no-poller policy and placement. Nothing about topology can be decided without it | ~2h | `dedicated_edge_routing` §8.1 |
| **Decide the queue axis** — recommended `<domain>-<env>` shared **plus** `<domain>-<machine>-<env>` pinned | ⚠️ **Live standards conflict.** The vendored Worker Deployment Standard fixes the axis at `<domain>-<env>` (§2.1), makes worker→queue 1:1 (§2.2) and forbids multi-domain workers (§1.1). **A machine axis has no slot**, and one of the three workarounds trips that standard's own named god-worker anti-pattern | ~1 day | `dedicated_edge_routing` §4.1, §8.2 |
| **Set a per-workflow-class no-poller policy** | Temporal's Schedule-To-Start default is **∞ and non-retryable** — work addressed to an offline edge waits forever, silently | ~1 day + ~1 day pre-flight | `dedicated_edge_routing` §8.3 |
| **Decide Worker Deployment topology: one per machine, not one per fleet** | With one shared Deployment an offline laptop blocks every rollout. **Version history does not migrate** — this cannot be changed later | ~2h decide, ~2 days wire | `dedicated_edge_routing` §8.4 |
| **Liveness payload design** — heartbeat carries `lastOutputAt` + `lastUsefulActionAt`, not just aliveness. **The stalled predicate is a three-way conjunction: not running AND not waiting AND not already being recovered** | A detector on "not running" alone alarms on every legitimately-waiting item | hours (design), constrains build | `paperclip_assessment` §4.4 |
| **Dedupe-granularity ruling** — coarse (one open recovery per work item) **or** fine (one per distinct cause). **Alternatives with a real trade-off, not a pair to build both of** | Retrofitted into Paperclip across a 206-migration schema | ~1 day design | `paperclip_assessment` §4.3 |
| **Capability-declaration surface** — Temporal answers existence and liveness natively and **capability not at all**. Recommended: static topology profile now | SkyyNet must know before it enqueues; after it enqueues there is no fallback. **Removing role-pull does not remove capability discovery — it moves it** | ~4h (a) / ~1 day (b) | `dedicated_edge_routing` §8.6 |
| **Derive queue names from explicit config — never `gethostname()`, never a UUID** | Temporal's own sample uses `hostname-uuid`, correct for ephemeral sessions and **wrong here**: a restart orphans a queue with work in it | ~4h | `dedicated_edge_routing` §8.5 |

### Cheap guards — ~9 operator-hours for the top three, none deleted by the port

| Item | Cost | Source |
|---|---|---|
| **Credential-expiry detection at the edge** — extend the existing `probe_stderr` grep class, distinct exit code, notify | ~2h | `fleet_failure_modes` E1 |
| **False-completion guard** — fetch the pointer; require a re-readable external artifact per completion contract | ~4h | `fleet_failure_modes` E2 |
| **Wiring test for `block-dangerous.sh`** — fixture issues a known-denied command, asserts denial | ~3h | `fleet_failure_modes` E8 |
| **Missed-window policy** — skip-by-default, widen the window for window-scoped jobs, consecutive-miss alarm | ~3h | `fleet_failure_modes` E4, §5.2 |
| **`timeout(1)` per child** (subsumed by the port, but cheap now) | ~2h | `fleet_failure_modes` E3 |
| **Stamp `claude --version` into every run log** — makes binary drift minable by machinery already running | ~1h | `fleet_failure_modes` E6 |
| **Concurrency ceiling on dispatches** — a count, not a USD cap; rate-limit exhaustion already observed once | ~2h | `fleet_failure_modes` E9 |
| **Worktree/disk sweeper** on the `gh-monitor` timer — note `git worktree prune` alone is insufficient | ~2h | `fleet_failure_modes` E5 |

### Interfaces and doctrine to adopt — eight are cost-S and depend on nothing

From `bernstein_capability_mining.md` §5, which ranks twenty capabilities. The unconditional, unblocked, cost-S set: **typed refusal with a closed no-catch-all taxonomy**; the **`reason_code` / `transient` / `next_action` failure vocabulary**; the **short-lived-worker doctrine with a wall-clock kill**; **"unreadable is a failure" — no checker closes its own finding** (corroborating our author≠judge seam, from a competitor that violated it in production); **unproven ≠ valid** as a tri-state review verdict; **filtered credential env at the spawn boundary**; the **intent-capsule scope digest**; and the **loop/stall calibration numbers**. Cost M and worth it: the **typed activity boundary / `ActivityResult`** (§1 above) and **evidence-hash verification of claims**.

**Declined, with reasons recorded so they are not re-derived:** the Kubernetes operator and CRDs, the WAL/file-based state (superseded by Temporal), the mTLS machinery, Worker Sessions (Go-only), Sticky Execution as a pinning mechanism, and wake-on-task (Temporal ships it only for AWS Lambda and GCP Cloud Run).

### The operator surface — sequenced, and mostly "wait"

| Item | Cost | Note |
|---|---|---|
| **1. Blocked-work notifier** on the existing `gh-monitor` — converts the inbox from pull to push, the only change that matters when the operator is by definition absent. **Ship it with the `/standup` aging counter as its falsification criterion, or it is unfalsifiable** | 1–2 days | No Temporal dependency. The only recommendation Temporal can never supply |
| **2. Give the inbox a home in `roadmap.md`** — no code. The inbox is documented as *memory* and nowhere as a *control surface*, and no phase holds it | ~0.5 days | **Cheapest item in the pool and the one most likely to be skipped for that reason** |
| **3. Liveness heartbeat — CONDITIONAL** on the Temporal port slipping past ~2026-11 | 2–3 days, **explicitly throwaway** | Priced now so a slip does not force an improvised decision |
| **Web control surface** | 1–3 weeks | **Hold until edge count > 1** |

---

## Action candidates

Reviewable items, sized for a standup. Nothing is ratified. Per §7 this run surfaces candidates and writes nothing outside `research/` — routing is the reviewer's and the operator's.

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Correct differentiator #1 in `problem-statement.md`.** The nearest neighbour has already generalised its execution boundary to five modalities with one typed result contract, two of them verified by something other than tests. The defensible claim is *"comparable systems are sold for code; the nearest one generalised its boundary without generalising its product"* | change direction | `bernstein_capability_mining.md` §0.1 |
| 2 | **Replace differentiator #2's wording with the credential version.** "Role-pull assumes fungible workers distinguished by a label" is refuted by three comparator families plus our own substrate. Replacement wording is drafted and ties the claim to the affordability thesis | change direction | `dedicated_edge_routing.md` §7 |
| 3 | **Add the trust-domain claim to `problem-statement.md` — it is stronger than what is there.** bernstein's fleet is *"not multi-tenant in the security sense"* and lists cross-org federation as out of scope. SkyyNet's destination is outside the nearest neighbour's shipped scope, first-party | adopt | `bernstein_capability_mining.md` §0.2 |
| 4 | **Resolve the queue-axis conflict with the vendored Worker Deployment Standard before `Phase: Temporal Integration` is planned.** A machine axis has no slot in `<domain>-<env>`; one workaround trips the standard's own god-worker anti-pattern. **Standards-amendment candidate — the vendored file must not be edited here** | new concept | `dedicated_edge_routing.md` §4.1 |
| 5 | **Ship the three cheap guards: credential expiry, false completion, safety-hook wiring test. ~9 operator-hours.** They are, respectively, the failure that stops the fleet, the failure that makes the fleet lie, and the failure that makes the fleet unsafe. None is deleted by the Temporal port | adopt | `fleet_failure_modes.md` §7 |
| 6 | **Do NOT build an operator dashboard. Build the blocked-work notifier (1–2 days) and give the inbox a roadmap home (0.5 days).** The field is unanimous that a surface is required and this repo already has the hard part; the remaining gap is liveness, which the Temporal port supplies free | no change *(the negative is the finding)* | `operator_interface.md` §0, §6 |
| 7 | **Close the "evaluate Paperclip after Phase 4" gate now and rewrite the item's text.** It describes a product Paperclip explicitly disclaims, and asks an overlap question that was never the right one — Paperclip *invokes* headless Claude Code as its substrate | adopt | `paperclip_assessment.md` §7 |
| 8 | **Adopt the eight cost-S, dependency-free interface/doctrine items** — typed refusal, the failure vocabulary, short-lived workers, "unreadable is a failure", unproven≠valid, filtered credential env, intent capsule, stall calibration | adopt | `bernstein_capability_mining.md` §5 |
| 9 | **Fix the missed-window assumption in `roadmap.md` — it is backwards, verified against the code.** `review-runs.sh` uses a trailing `-mtime` window, so a skipped sweep loses those days permanently; research revalidation's date gate is self-healing. The discriminator is window-scoped vs. state-converging | change direction | `fleet_failure_modes.md` §5.2 |
| 10 | **Design the stalled predicate as a three-way conjunction before workers are written** — not running AND not waiting AND not already being recovered. Paperclip's own "invisible zombie" incident is the evidence, and the same failure mode is live here today | adopt | `paperclip_assessment.md` §4.4 |
| 11 | **Decide the dedupe granularity as a ruling, not a build.** Coarse and fine are alternatives with a real trade-off — explicitly *not* a pair to build both of | adopt | `paperclip_assessment.md` §4.3, §6 |
| 12 | **Drop any uniqueness framing on subscription-auth-at-the-edge** — it has precedent at scale in a 75,600-star product | change direction | `paperclip_assessment.md` §4.6 |
| 13 | **Reconsider giving up cross-machine failover for *all* work.** Temporal's own pattern is two-tier and retains a shared queue; the current design pins work that has no locality requirement | new concept | `dedicated_edge_routing.md` §5, §7 |
| 14 | **Refresh `raw/temporal.md`** — the pool's only past-window paper, and it is the substrate every item above depends on. Carried from two prior cycles | no change | `temporal.md` header |
| 15 | **Promote the local OTel projection out of `roadmap.md` § Future Ideas.** Writing the projection locally regardless of endpoint is cost S–M and unblocked; the observability finding argues it is a phase item, not an idea | adopt | `bernstein_capability_mining.md` §4.16, §5 row 14 |

---

## Homeless findings

Named here rather than parked elsewhere, per §7 — a homeless finding means the surface is missing.

- **This repo has no surface that holds "an upstream standards amendment we owe."** Carried from two prior cycles and hit three more times this cycle. The Research Standard is **vendored MIRROR** from `MDC-Master-Planning`, so amendments cannot be made here. Three are now owed, all evidenced: (a) §3's confidence classes conflate *how authoritative the speaker is* with *how formal the artifact is*; (b) the sourcing rule's hazard is misnamed — the real one is that **a fetch that summarizes cannot establish a character sequence, however authoritative the URL**; and (c) the new count rule below. **The missing surface is the finding.** *(The `review-pr` filing-authority change shipped in `8f16bc7` addresses filing such amendments on the upstream repo — whether that closes this is a reviewer's call, and it is why the finding is restated rather than dropped.)*

- **A count read from any API through a summarizing fetch layer is unreliable, and this is now corroborated across two analysts, two codebases and two directories.** Seven fetches produced seven different totals; **`truncated: false` was present and wrong every time.** The mechanism was isolated at round 3: **every unstable number came from asking the layer for a total; every stable one came from asking it to enumerate and counting the list yourself.** The rule — *never delegate the arithmetic; corroborate a count against an enumerable anchor* — belongs in the Research Standard beside raw-over-rendered and confirm-the-default-branch. Same missing upstream surface. **This is not a process curiosity: the under-enumeration silently narrowed the evidence base for four of eleven ranked exposures in `fleet_failure_modes.md`, and four bernstein documents bearing directly on those exposures were never known to be missing.**

- **A repair to a quote is a new quote, and carries the same verification duty — but is systematically less likely to get one**, because attention sits on the item being closed rather than the text being written. Measured twice this cycle: a round-1 repair converted a truncation defect into a fabrication while appearing to resolve it. **This defect class exists only because review is happening**, which is why no sourcing rule catches it. Same missing upstream surface.

- **A defined shape for production feedback.** Carried from two prior cycles and still homeless. One instance exists as a dated intake record; a dated one-off is not a channel.

- **The sizing rubric's bands are calibrated for components whose destination is a plan.** This component's destination is a thesis plus a roadmap plus a live competitive field — 21 topics against a Large band of 8–10. Same vendored-standard problem.

---

## Gaps this cycle did not cover

- **Decide-only disposition — does a judging stage with no authoring authority actually reduce defects?** **Displaced for the second consecutive cycle.** It remains the sharpest testable claim inside element 2, and `case_against.md` surfaced a live sourced contradiction only an experiment resolves. **A topic displaced twice is at risk of being displaced permanently — the next cycle should either run it or retire it explicitly.**
- **Multi-edge identity, trust and credential distribution.** New this cycle and only partly covered. `bernstein_capability_mining.md` establishes it is **not mineable** — bernstein's fleet is explicitly single-trust-domain, so it does not solve the problem we have. Needs its own pass.
- **Provider-shaped edges** (Codex vs Claude Code exposing different capabilities). Deferred because its destination is a `problem-statement.md` stub.
- **The quota-headroom view.** Genuinely novel and falls out of the affordability thesis — every competitor's cost surface is shaped by *metered* billing, and under a flat subscription dollars are not scarce, **per-edge rate-limit headroom is**. Nobody surveyed exposes that view. **Not sequenceable yet**: blocked on one unanswered question (does the Claude Code result envelope expose quota at all? — a minutes-long test) and one unread document.
- **Whether an agentic `claude -p` run decomposes into resumable per-turn legs** — still uncovered; decides the port's shape.
- **Duplicated prompt prose**, **inter-process handoff wire format** (phase-level, redirected), **reflection-channel mining**, and **bash → Python Stage A** — all unchanged in status.
- **Certification and conformity regimes for a physical edge** — still unanswerable without paid standards access. Now feeds a stub section, which lowers its urgency without lowering its size.
