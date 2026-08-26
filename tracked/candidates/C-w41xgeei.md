---
id: C-w41xgeei
title: A version pin or startup probe for the CLI-shape facts the V2 path depends on
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

Two facts are depended on and declared nowhere: **`result.permission_denials` exists**, and **`--json-schema` moves prose out of `.result`**. **Partially mitigated by PR #71 and explicitly not closed by it** — that PR split R1 so an absent-or-mistyped `permission_denials` reports `denials_unreadable` rather than `permission_denied`, which means a CLI shape change is now *visible in the per-reason rate* instead of masquerading as a fleet-wide safety trip. It is still detected only after the fact, once per run, by an operator reading reasons. A startup probe would catch it once, before the run. **Proposal: the probe is capability that does not exist**; the mis-binning it would have caused was the defect, and that half is fixed

**Source:** PR #71

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
