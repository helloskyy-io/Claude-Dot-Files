# Workflow Decomposition — Roadmap

**Status: 🟡 IN PROGRESS.** Phase 1 is complete, Phase 2 is live, Phases 3 and 4 are ahead.

**This roadmap was written after Phase 1 shipped.** The component ran for eleven days on a burn-test triage list ([`burn-test-intake-2026-08-02.md`](../burn-test-intake-2026-08-02.md)) with no roadmap, no phase docs and an empty research pool. Phase 1's boxes below are therefore a **record of what was built**, not requirements it was built against. Phases 2–4 are real planning.

---

## In plain words

A workflow used to be one long script that did everything. If it failed at step nine, you started again at step one. If two workflows needed the same instruction, you copied it.

This component takes them apart. A **parent** decides what happens next; a **child** does one job. Each boundary between them is a place work can be reviewed, retried, or resumed — and children can be recombined instead of copied.

Two things follow from that, and they are the second half of the work: children in the same family must not drift apart, and a child should work the same whether a human runs it or a parent does.

---

## What this component owns

- **The parent/child split** — which workflows are parents, which are children, and where the boundary falls
- **The composition contract** — what a parent may do, what a child must return
- **Family alignment** — how children that share a job stay aligned, and where they are allowed to differ
- **The invocation contract** — how a workflow learns what to do from how it was called

**It does not own:** durability or resumption ([Temporal Integration](../temporal-integration/temporal-integration.md)), what a run records ([PMP](../persistent-memory-protocol/roadmap.md)), or making a child better at its job ([Self Improvement](../sprint.md)).

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

### Phase 2 — Family alignment 🟡 IN PROGRESS

*Children in a family do not diverge except where they need to.*

- [x] The shared-fragment mechanism — a block with two consumers lives in `modules/assistant/prompts/` and is referenced by placeholder
- [x] The duplication ratchet — a frozen baseline that fails on new copying **and** on a fixed entry left behind, so it can only shrink
- [x] The promotion rule extended to prompts, in [`workflow-scripts.md`](../../standards/workflow-scripts.md)
- [ ] **Bring the fleet up to the rule** — the measured backlog, largest groups first
- [ ] **Rule fork-vs-parameterize** — the half a test cannot judge: a copy that has already drifted reads as intent, not accident
- [ ] **Extend the producer-with-no-consumer gate** beyond `scripts/helpers/measure/`

### Phase 3 — The invocation contract ⬜

*A workflow derives what it needs from how it was called.* Dual-mode is *who called me*; scope derivation is *what was I pointed at*.

- [ ] **Every child runs standalone and under a parent, equally well**
- [ ] **`plan-project` derives feature scope from its target** — feature scope is the project chain's tail, and a path states it rather than a flag
- [ ] **`research_refresh_parent` has no entrypoint** — a parent nothing can invoke, found while counting for the box above

### Phase 4 — The missing children and parents ⬜ GATED

*The set we do not have yet.* Standalone because it is the largest phase and the only one with no evidence behind it.

- [ ] **Design the set** — which children should exist and where the boundaries fall
- [ ] **"No god workflows" as an actual rule** — what a single workflow may not do, stated so it can be checked
- [ ] **Build them**

---

## The order, and what each part waits on

**Phases 2 and 3 have no external gate** and can be planned and built now.

**Phase 4 waits on two things, in order:** the operator's list of what the set should contain, then research. It is the phase this component's own history argues hardest for — Phase 1 was built without either, which is why this roadmap is being written at the end instead of the beginning.

**Research:** [`research/`](research/) is scaffolded and empty. Phase 4 is what should fill it.

---

## What is deliberately not built

- **A god workflow** — one entrypoint that does everything. Phase 4 turns this from a preference into a rule with a checkable boundary.
- **Retry and resumption inside children** — that is durability, and it belongs to the Temporal port. See its retry-boundary item: `gh()` already carries a bounded retry for transient outages, and nesting that inside an activity retry multiplies attempts.
