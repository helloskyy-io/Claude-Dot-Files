---
id: C-xh8nvwqn
title: Rule whether the persistent memory protocol is its OWN COMPONENT or a PHASE of the Memory Management Framework
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**The research explicitly could not settle it, and said so.** §5.1: no source bears on component-vs-phase, and the paper names the trap — mechanism-list length reads as an argument for a dedicated component while being equally consistent with a phase. **It decides where the roadmap and phase docs get written**, so it gates planning rather than building, and four in-progress sprints consume the answer (CPI, Workflow Decomposition, Memory Management, Temporal Integration). **Placed as a candidate rather than written straight into `direction.md`**: a `D-` row requires a `Source: C-NNN` and is `plan-sprint`'s write, so placing one directly would skip the convention and self-grant that authority. **Lens verdicts (gate 5): `/decide` — not dissolved**, the upstream question is genuinely open and the evidence is absent rather than unread. **`/best-practices` — SURVIVES**: component boundaries are ratified by an owner, not derived from a mechanism count. **2026-08-13 — the substance is now argued, and the `decision` is still the operator's.** A `plan-revision` run implemented the **own-component** reading and stated its reasoning against §0's test in [`persistent-memory-protocol/roadmap.md` § *Why this is a component and not a phase*](../../../development/persistent-memory-protocol/roadmap.md) — deliberately **not** from the mechanism count this row warns about, but from a comparison of two stated ownership sentences, with three further checks (it inverts authority over MMF's own outputs; MMF is six-of-six complete so a seventh phase would falsify its completion claim; its scope sentence names git, which synthesis §10 rules is the coding edge's binding rather than the protocol's). **`decision` left BLANK on purpose** — setting it is `plan-sprint`'s write and the ruling is the operator's. If the operator rules the other way the remedy is mechanical: the phase docs move into `memory-management-framework/` and renumber from 7.

**Source:** PR #84 (cross-node memory prior art)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
