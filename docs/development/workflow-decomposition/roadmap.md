# Workflow Decomposition — Roadmap

**Status: 🟡 IN PROGRESS.** Phase 1 is complete, Phase 2 is live, Phases 3 and 4 are ahead.

**This roadmap was written after Phase 1 shipped.** The component ran for eleven days on a burn-test triage list — since deleted, its two orphaned rulings salvaged into [`cpi-decisions.md`](../cpi-decisions.md) (2026-08-17) — with no roadmap, no phase docs and an empty research pool. Phase 1's boxes below are therefore a **record of what was built**, not requirements it was built against. Phases 2–4 are real planning.

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

**It does not own:** designing or building workflows that do not exist yet — that is [Assistant Workflow Design](../sprint.md), which is the other side of this component's seam: decomposition takes apart what already existed, that one creates what does not. Nor durability or resumption ([Temporal Integration](../temporal-integration/temporal-integration.md)), what a run records ([PMP](../persistent-memory-protocol/roadmap.md)), or making a child better at its job ([Self Improvement](../sprint.md)).

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

### Phase 3 — Split the remaining long-running workflows ⬜

*The research and plan families never got the split that `build` did.* Same treatment, same reason: separate the work from its review and its correction, so each boundary is a place to retry rather than a place to restart.

- [ ] **The research family** — `research_write` and `research_verify` are already separate children, but the cycle around them is not split the way `build_draft` → `build_refine` is
- [ ] **The plan family** — `plan_feature`, `plan_sprint`, `plan_verify` run as a chain with no correction stage of their own
- [ ] **Name what should NOT be split** — a workflow whose work and review are genuinely one act, and why

### Phase 4 — The invocation contract ⬜

*A workflow derives what it needs from how it was called.* Dual-mode is *who called me*; scope derivation is *what was I pointed at*.

- [ ] **Every child runs standalone and under a parent, equally well**
- [ ] **`plan-project` derives feature scope from its target** — feature scope is the project chain's tail, and a path states it rather than a flag
- [ ] **Centrally managed config, with a user tier beside it** — agents, skills, rules and hooks are read from `~/.claude/`, so an interactive edit silently changes what every dispatch on that machine does and no two machines can be shown to match. The fleet's set becomes managed; the user keeps a tier they own and can extend. *Gate: PMP Part 1 — if the run bag records the config a run used, the divergence half shrinks to a reader.* **`run-claude` already refuses an inherited model; this is the same seam applied to everything else a dispatch absorbs.**
- [ ] **`research_refresh_parent` has no entrypoint** — a parent nothing can invoke, found while counting for the box above

## The order, and what each part waits on

**Phases 2, 3 and 4 have no external gate.** The component has a real end: when they close, decomposition is done. What used to be Phase 4 — the set of workflows that do not exist yet — moved to [Assistant Workflow Design](../sprint.md), because building what is missing is not the same act as taking apart what is here.

**Research:** [`research/`](research/) is scaffolded and empty. Phase 4 is what should fill it.

---

## What is deliberately not built

- **A god workflow** — one entrypoint that does everything. Turning that from a preference into a checkable rule belongs to [Assistant Workflow Design](../sprint.md), which decides what the set contains.
- **Agents as independently retryable units.** Operator ruling: a Tier-3 agent — independently addressable and independently retryable — is the canonical answer for a **metered API** integration, not for a **subscription-based CLI overlay**. It would need the CLI baked into worker images and a credential per pod. **The accepted trade, stated so nobody re-derives it as a gap:** agents stay inside Claude Code's process model and are therefore not independently retryable, and the parallel-narrow-then-sequential-integration pattern stays enforced by prompt discipline rather than by structure. A known limit, deliberately taken — and it rules out one shape of answer before Phase 4's research starts.
- **Retry and resumption inside children** — that is durability, and it belongs to the Temporal port. See its retry-boundary item: `gh()` already carries a bounded retry for transient outages, and nesting that inside an activity retry multiplies attempts.
