---
id: C-73bf2gvm
title: Research and design a memory PROTOCOL — the record types, their stores, their wire formats and the rule for adding a fourth — as one designed set rather than three arrived at separately
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**FEATURE / RESEARCH REQUEST, not a defect — nothing is broken.** The framework works and is shipping. But it was researched as a TWO-channel design (`dual_channel_outcome_records`), a third type is being added by inference, and the durable record alone now spans **five surfaces, two substrates and two different to-do mechanics** — each defensible alone, none designed as a set. **The research already cites OpenTelemetry but only for record SHAPE (§2.5, attributes-vs-body); its metrics model — the industry's actual answer to where measurement data lives — was never opened.** Measurement is not in the *deliberately NOT commissioned* list either, so it was never considered and rejected; nobody asked. Operator's framing: *a select well-designed few that cover the bases and allow for future growth*. Ship the current design at 80% first, then refine through this.

**Source:** operator, 2026-08-10

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
