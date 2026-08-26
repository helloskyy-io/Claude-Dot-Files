---
id: C-lrnl9dnu
title: **A fleet ACTIVITY may declare a parameter nothing in its body reads, and the one guard that forbids exactly that — `test_a_PARENT_forwards_what_its_CHILD_reads` — asks it only of ENTRYPOINTS, so a dead argument spreads by copy instead of failing on the day it is written**
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**Measured on this PR, and it had already spread.** `ci_verdict` and `wait_for_ci` kept a `repo: str \

**Source:** PR #124 (`build-refine`, pass 4)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
