---
id: C-2asq6d9x
title: Give `plan-sprint` a reader for the per-phase hour estimates `plan-verify` now writes, so the sprint plan totals real numbers instead of judging every item against a 160-hour calibration
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**`plan-verify` shipped the estimates and `plan-sprint` cannot see them, so the pipeline now produces a number nothing consumes.** Verified by reading the workflow rather than assumed: `plan_sprint.md` states *"You never open a phase doc"*; the `EXISTING_WORK` block it is handed enumerates component directories, their `research/synthesis.md`, the product pool's papers and the open GitHub issues, and **names no `roadmap.md` anywhere**; and `grep -rn 'hour\

**Source:** PR for `plan-verify` (build-draft, 2026-08-15)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
