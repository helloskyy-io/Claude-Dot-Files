---
id: C-v4k9pz2h
title: Workflow Decomposition Phase 4 bundles two independently demonstrable outcomes, so whichever half is finished first cannot be shown as finished and the phase cannot close on either
status: open
count: 1
filed: 2026-08-27
filed_by: plan-feature
component: workflow-decomposition
size:
decision:
---

**PROPOSAL — split [Phase 4](../../docs/development/workflow-decomposition/phase4_nothing_invisible.md) into two phases, the produced half taking the next free number (6).** Nothing behaves wrongly today; this is a decomposition boundary, and the phase is unbuilt.

**The two outcomes, and each is demonstrable without the other.**

1. **A wrong derivation is visible before it costs anything** — point a run at the wrong component, and the output names what it derived before the first side effect. Requirements 1–3.
2. **A producer with no named consumer turns the suite red** — add one, watch it fail. Requirements 4–5.

**They share a slogan, not a mechanism.** The derived half is bounded by the number of derivation sites, finishes three properties on code that already anchors on a marker and already takes an override, and rests on a critic-passed paper. The produced half is bounded by nothing yet: its first deliverable is a definition, that definition has to be ruled across the whole fleet before a line of gate code is safe, and its population is a set of surfaces nobody has enumerated. **The phase's own sizing note says it:** *"the produced half is what makes this phase large, and it is the half that could be its own."*

**The consequence, which is what makes this a finding rather than an aesthetic preference.** A phase closes when its requirements are met. Bundled, the cheap and well-evidenced half cannot be marked delivered until the expensive and under-specified half is — so the derived half's echo, which nine new standalone callers from [Phase 3](../../docs/development/workflow-decomposition/phase3_dual_mode_children.md) actively want, sits behind a definition nobody has written. The pressure that follows is to weaken the produced half's requirements so the phase can close, which is the opposite of what it exists for.

**Why it is bundled, stated so this is not re-litigated as an oversight.** The two were planned separately on 2026-08-18 and merged deliberately, on the correct reasoning at the time: *"neither carried enough work to stand alone as a document."* **That premise has weakened since.** A follow-up pass on 2026-08-27 gave the produced half a ratified definition anchor ([Tracked Items Standard §0](../../docs/standards/documentation/tracked_items_standard.md)), a named on-disk population (six tools in `scripts/helpers/` outside `measure/`, plus the intake→harvest pair), and a named exclusion (`tracked/operations/`, whose consumer is a human). It is better specified than it was, and correspondingly larger.

**Proposed action.** Rule the split at the next planning pass over this component. If adopted: requirements 1–3 and the derived half of requirement 6 stay in Phase 4; requirements 4–5 and the produced half of requirement 6 move to **Phase 6** — a new number, because [`roadmap.md`](../../docs/development/workflow-decomposition/roadmap.md) and the [Documentation Standard](../../docs/standards/documentation/documentation_standard.md) both bind that a gap is not a free number and a retired number is never reused. **If rejected, the reasoning is the remedy** and should be written into the phase doc so the third pass does not raise it again.

**Not a duplicate of [[C-qp4n7vzt]] or [[C-wb1xc1xs]].** Both of those are about the run-log observables in `persistent-memory-protocol` — one asks whether an observable's rate decides anything, the other asks for a reader for `convergence` events. Neither is about how this component's phases are bounded, and both would stand unchanged whichever way this is ruled.

**Source:** `plan-feature` follow-up design pass over `docs/development/workflow-decomposition`, 2026-08-27. The pass was explicitly constrained to a fixed five-phase list, so it surfaced the boundary rather than acting on it; this item is what carries the finding past the PR body it was surfaced in.
