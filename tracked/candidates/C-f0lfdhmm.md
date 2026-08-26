---
id: C-f0lfdhmm
title: Add *ask what the guard does NOT look at* to the mutation instructions — negative controls structurally cannot find SCOPE defects, and every defect found on PR #92 across three passes was one
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

A control mutates a guard and counts failures, which proves the tests discriminate against the code **as scoped**; mutating a narrow guard still fails the narrow tests written for it. The four defects were a regex crossing a sentence, a grant crossing a directory, a sweep missing a filename class, and an ordering hiding a message. Pass 1 named the blind spot and filed C-w8455f0l; **pass 3 is the evidence that naming it was not enough.** The technique that actually found all four is the one to write down.

**Source:** PR #92 `plan-feature` reflections (3 passes, 2026-08-14/15)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
