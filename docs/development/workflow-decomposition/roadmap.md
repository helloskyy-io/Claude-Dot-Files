# Workflow Decomposition — Roadmap

**Status: 🟡 IN PROGRESS.** Phase 1 is complete, [Phase 2](phase2_family_alignment.md) is live, and four more are planned. **Phases are listed in logical rollout order. Phase numbers are creation-order identifiers and do not reflect rollout sequence; execution order across components lives in [`sprint.md`](../sprint.md).**

**This roadmap was written after Phase 1 shipped.** The component ran for eleven days on a burn-test triage list — since deleted, its two orphaned rulings salvaged into [`cpi-decisions.md`](../cpi-decisions.md) (2026-08-17) — with no roadmap, no phase docs and an empty research pool. Phase 1's boxes below are therefore a **record of what was built**, not requirements it was built against.

**Phases 2–6 were decomposed on 2026-08-18 from [`research/synthesis.md`](research/synthesis.md).** What used to be a single four-box Phase 3 is now four phases, because its four boxes deliver four separate things and one of them cannot start until an operator rules. The four original checkbox lines are unchanged and are carried below under the phase that now owns each — a completion criterion is not reworded by the run that plans against it.

---

## In plain words

A workflow used to be one long script that did everything. If it failed at step nine, you started again at step one. If two workflows needed the same instruction, you copied it.

This component takes them apart. A **parent** decides what happens next; a **child** does one job. Each boundary between them is a place work can be reviewed, retried, or resumed — and children can be recombined instead of copied.

Two things follow from that, and they are the second half of the work: children in the same family must not drift apart, and a child should work the same whether a human runs it or a parent does.

A third thing follows that is easy to miss. Once a workflow can be started by a human *or* by a parent, **what it does depends on things nobody typed** — the directory it was started from, the path it was pointed at, the configuration files sitting on that machine. Those are derived values, and a wrong one does not crash: it produces a competent run of the wrong work. Making every one of them visible is the rest of this component.

---

## What this component owns

- **The parent/child split** — which workflows are parents, which are children, and where the boundary falls
- **The composition contract** — what a parent may do, what a child must return
- **Family alignment** — how children that share a job stay aligned, and where they are allowed to differ
- **The invocation contract** — how a workflow learns what to do from how it was called, and how it says so out loud
- **The record of what a run absorbed** — the digest of the configuration a dispatch ran under, written into that run's own bag

**It does not own:** designing or building workflows that do not exist yet — that is [Assistant Workflow Design](../sprint.md), which is the other side of this component's seam: decomposition takes apart what already existed, that one creates what does not. Nor durability or resumption ([Temporal Integration](../temporal-integration/temporal-integration.md)), what a run records ([PMP](../persistent-memory-protocol/roadmap.md)), or making a child better at its job ([Self Improvement](../sprint.md)).

**And it does not own the managed/user configuration tiers themselves.** [`managed-configuration/`](../managed-configuration/research/) is a scaffolded component with an empty pool and no sprint entry; designing which tier wins, and what a user's own tier may override, belongs there. This component stops at **recording what a run actually absorbed** — see [Phase 6](phase6_configuration_a_run_absorbed.md), which states that seam and flags it as an operator call.

---

## Phases

**Phase numbers are identity, not order.** The sprint decides what gets built when.

### Phase 1 — Decompose the build families and codify the shape ✅ COMPLETE

Take the monoliths apart, then write down what the shape is.

- [x] Split `build` into draft → refine → review-pr
- [x] Split `build-minor` on the same shape — one-lens middle child
- [x] Absorb `build-phase` into `build --phase` — one family, one set of children
- [x] Extract the activities layer — `run-claude`, `wait-for-ci`, `require-environment`
- [x] Write it down — [`workflow-scripts.md` § Composition](../../standards/workflow-scripts.md)

### [Phase 2 — Family alignment](phase2_family_alignment.md) 🟡 IN PROGRESS

*Children in a family do not diverge except where they need to.*

The mechanism shipped and the ratchet works — the duplication baseline fell from 48 rows to 13. What is left is the half a test was never able to decide: whether a pair that has already drifted drifted *on purpose*. This phase ends when no row in that baseline is unruled, and when the reasoning behind each ruling is written where the next reader finds it.

- [x] The shared-fragment mechanism — a block with two consumers lives in `modules/assistant/prompts/` and is referenced by placeholder
- [x] The duplication ratchet — a frozen baseline that fails on new copying **and** on a fixed entry left behind, so it can only shrink
- [x] The promotion rule extended to prompts, in [`workflow-scripts.md`](../../standards/workflow-scripts.md)
- [ ] **Bring the fleet up to the rule** — the measured backlog, largest groups first
- [ ] **Rule fork-vs-parameterize** — the half a test cannot judge: a copy that has already drifted reads as intent, not accident
- [ ] **Every row in the frozen duplication baseline is either gone or carries a written ruling** — 13 rows on 2026-08-18
- [ ] **The ruling method is validated before it is trusted** — classify a sample blind, then reveal the history, and record the disagreement
- [ ] **What a `_minor` tier's prompt is FOR is written down where a guard can cite it** — the contract no test can supply

### [Phase 3 — A derived value you can audit](phase3_auditable_derivation.md) ⬜

*Dual-mode is who called me; scope derivation is what was I pointed at. This phase is the second one, and it is smaller than it looks.*

The derivation this component set out to build **already shipped** — `plan-project` and `plan-feature` both take a path and read scope off it, anchored on the git root with `--repo` as the explicit override. What did not ship is the part that makes a derived value safe to trust: the algorithm written down somewhere a reader finds it, the run saying out loud what it derived, and each value stating what breaks if it derived wrongly. This phase finishes those three properties on code that runs today, and proves the third by pointing a run at the wrong thing and watching it say so.

- [ ] **`plan-project` derives feature scope from its target** — feature scope is the project chain's tail, and a path states it rather than a flag
- [ ] **Every derived value is listed with its marker, its algorithm and its override** — published, not inferred from reading the code
- [ ] **A run echoes what it derived, and a parent can silence the echo without losing the record**
- [ ] **Each derived value states its scope of effect** — what changes downstream if this one is wrong
- [ ] **A wrong derivation is demonstrated to be visible** — point a run at the wrong component and show the echo naming it

### [Phase 4 — Every producer names its consumer](phase4_producer_names_its_consumer.md) ⬜

*A surface a run writes that nothing reads is not a feature, it is a leak.*

One directory already has this gate: every tool in `scripts/helpers/measure/` must appear in a table naming who reads it, and the population is read off disk so a tool cannot dodge the check by never adding its row. That gate exists because three parent-written observables shipped with no reader at all. Nothing generalises it, so the next unread producer will ship the same way. This phase defines what a producer is across the fleet and extends the gate to reach them.

- [ ] **Extend the producer-with-no-consumer gate** beyond `scripts/helpers/measure/`
- [ ] **What counts as a producer is defined** — and what is deliberately excluded, by name rather than by omission
- [ ] **The population is read off disk, never off the table** — the same property that makes the existing gate work
- [ ] **A new producer with no named consumer fails the suite** — demonstrated by adding one, not asserted

### [Phase 6 — What configuration a run absorbed](phase6_configuration_a_run_absorbed.md) ⬜

*A dispatch reads agents, skills, rules and hooks from `~/.claude/`, so an interactive edit silently changes what every later dispatch on that machine does.*

The smallest thing that fixes the visible half is one digest: record what configuration a run absorbed as a sixth `Journal-` tag in that run's bag, and write the reader that compares two of them. Divergence detection then falls out as a reader over bags that already exist, instead of a drift detector nobody has justified building. This phase deliberately stops there, and it carries one measurement it must not build past: whether Claude Code's own Managed settings tier survives the flags a dispatch might pass.

- [ ] **Centrally managed config, with a user tier beside it** — agents, skills, rules and hooks are read from `~/.claude/`, so an interactive edit silently changes what every dispatch on that machine does and no two machines can be shown to match. The fleet's set becomes managed; the user keeps a tier they own and can extend. *Gate: PMP Part 1 — if the run bag records the config a run used, the divergence half shrinks to a reader.* **`run-claude` already refuses an inherited model; this is the same seam applied to everything else a dispatch absorbs.**
- [ ] **A run's bag records a digest of the configuration it ran under** — a sixth `Journal-` tag beside the five that exist
- [ ] **A reader answers "did these two runs use the same configuration"** from bags alone
- [ ] **Whether the Managed tier survives `--setting-sources` and `--safe-mode` is MEASURED** — unchecked, and nothing may be designed on it until it is

### Phase 5 — Dual-mode children ⬜ NO PHASE DOC — gated on an operator ruling

*Every child runs standalone and under a parent, equally well — or deliberately does not.*

Nine workflow modules, all of them children, have no standalone runner: the four build halves, and five of the research children. That gap is measured and the fix is mechanical. **What is not settled is whether it is a gap at all.** [`workflow-scripts.md`](../../standards/workflow-scripts.md) states that running a child by hand is *recovery … never the interface*; the first box below states the opposite. Both are live, and no evidence decides between them — it is a design ruling. Until it is made, nine adapters is either a backlog or a deliberate narrowing, and a phase doc written now would be a detailed plan for one of two different phases.

- [ ] **The standing contradiction is ruled** — is standalone invocation an interface, or recovery only? Unchecked because it is an operator's call, and because the evidence explicitly declines to make it
- [ ] **Every child runs standalone and under a parent, equally well**
- [ ] **`research_refresh_parent` has no entrypoint** — a parent nothing can invoke, found while counting for the box above

*Two notes on the boxes above, both kept out of the text because a planning run does not reword a completion criterion.* **"The box above"** in the third box means the managed-config box, which now lives at [Phase 6](phase6_configuration_a_run_absorbed.md). And the third box's premise is **wrong as measured**: `research_refresh_parent` *is* invocable — `run_research.py --refresh` and `research.sh <dir> --refresh` both reach it (verified 2026-08-18 at `scripts/workflows/temporal/scripts/run_research.py:30`). The real defect is narrower: it has no entrypoint **of its own**, no `research_refresh.sh` beside the other shims. A run that decomposes the box as written will scope the wrong fix. Source: [`research/raw/invocation_contract.md`](research/raw/invocation_contract.md) §5.1.

## The order, and what each part waits on

**Only [Phase 5](#phase-5--dual-mode-children--no-phase-doc--gated-on-an-operator-ruling) has a gate, and it is a ruling rather than a dependency** — it needs a decision, not a system that does not exist yet. Everything else is buildable today.

**Phase 6's stated gate is already open.** It reads *"PMP Part 1 — if the run bag records the config a run used"*; the run bag shipped with [PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md) and already carries five `Journal-` tags. Adding a sixth is an addition to a mechanism that exists.

The component has a real end: when these phases close, decomposition is done. What used to be Phase 4 — the set of workflows that do not exist yet — moved to [Assistant Workflow Design](../sprint.md), because building what is missing is not the same act as taking apart what is here.

**Research:** [`research/`](research/) holds two papers, each with its own destination. [`raw/fork_vs_parameterize_drift_signal.md`](research/raw/fork_vs_parameterize_drift_signal.md) (`Last validated: 2026-08-17`, `Revalidate: high — 6 weeks`, `Critic: PASS-WITH-FIXES`) backs [Phase 2](phase2_family_alignment.md). [`raw/invocation_contract.md`](research/raw/invocation_contract.md) (`Last validated: 2026-08-18`, `Revalidate: high — 4 weeks`, `Critic: PASS-WITH-FIXES`) backs [Phase 3](phase3_auditable_derivation.md), [Phase 5](#phase-5--dual-mode-children--no-phase-doc--gated-on-an-operator-ruling) and [Phase 6](phase6_configuration_a_run_absorbed.md). [`synthesis.md`](research/synthesis.md) rolls both up. Neither paper is a ruling on the item it feeds — research is evidence, and a ruling is a separate act.

**Dependencies on other components:**

| This component | Depends on | Which way |
|---|---|---|
| [Phase 6](phase6_configuration_a_run_absorbed.md) | [PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md) — the run bag it adds a tag to | satisfied; PMP Phase 1 is complete |
| [Phase 6](phase6_configuration_a_run_absorbed.md) | [`managed-configuration/`](../managed-configuration/research/) — owns the tier design this phase stops short of | seam, not a gate. **Operator call: confirm the split** |
| [Temporal Integration](../temporal-integration/temporal-integration.md) | this whole component | it is gated on us — porting a shape still being changed means porting it twice |

---

## What is deliberately not built

- **A drift detector, a provenance command, or a cross-machine agreement proof.** [Phase 6](phase6_configuration_a_run_absorbed.md) builds one digest, one tag and one reader, and stops. The field ships all three of the others; none is justified until the digest shows what actually diverges. **This is a scope decision, not an assumption about fleet size** — see that phase's § *Why one digest and not the rest*.
- **A god workflow — NOT YET, and deliberately not NEVER.** A single workflow running a long chain unattended is the eventual goal; it is blocked by child performance rather than by design, since human review is currently load-bearing. What has to be true first belongs to [Assistant Workflow Design](../sprint.md), gated on Self Improvement. Decomposition neither builds one nor forbids one.
- **Agents as independently retryable units.** Operator ruling: a Tier-3 agent — independently addressable and independently retryable — is the canonical answer for a **metered API** integration, not for a **subscription-based CLI overlay**. It would need the CLI baked into worker images and a credential per pod. **The accepted trade, stated so nobody re-derives it as a gap:** agents stay inside Claude Code's process model and are therefore not independently retryable, and the parallel-narrow-then-sequential-integration pattern stays enforced by prompt discipline rather than by structure. A known limit, deliberately taken — and it rules out one shape of answer before Assistant Workflow Design's research starts.
- **Retry and resumption inside children** — that is durability, and it belongs to the Temporal port. See its retry-boundary item: `gh()` already carries a bounded retry for transient outages, and nesting that inside an activity retry multiplies attempts.
- **Claude Code's `--bare` flag, despite an upstream paper recommending it for reproducibility.** `--bare` skips hooks — and the `PreToolUse` hook is the only safety control operating during a headless run — and it refuses OAuth/keychain reads, which is the subscription credential this whole edge runs on. The recommendation is correct for an API-keyed worker and does not transfer here. Named so it is not adopted by association. Source: [`research/raw/invocation_contract.md`](research/raw/invocation_contract.md) §4.3.
