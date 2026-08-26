---
id: C-xhb460zu
title: A differential baseline the mutation probe can establish even when the pre-mutation import fails, so it answers instead of abstaining
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**The probe resolves exit 2 DIFFERENTIALLY — `HARNESS_ERROR` only when `$FILE` imported cleanly BEFORE the mutation and does not now. When it cannot establish that baseline it abstains to RED and says so, rather than asserting a cause.** That abstention is correct and is deliberately not a defect: asserting a cause it cannot establish is how #72's false certification happened. **What has no home is the PROPOSAL for removing the ambiguity** — its only record was prose inside a 728-line shell script, which `plan-sprint` does not read, so it died at merge. `testing/README.md` claimed all three deliberately-open ambiguities had a candidate; two did (C-45bhs5cm, C-73bf2gvm) and this one did not. **Lens verdicts (gate 5): `/decide` — not dissolved**, the upstream question is whether a baseline can be established at all without importing, which is a real unknown rather than a framing error. **`/best-practices` — SURVIVES**: differential mutation testing is standard, and an abstention rate is a known quality metric for one. **Not resolved into a known fix** — nobody knows the mechanism yet, which is precisely why it is research rather than a task.

**Source:** PR #74

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
