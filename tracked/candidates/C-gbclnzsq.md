---
id: C-gbclnzsq
title: Gate QUOTATIONS the way figures and prose tallies are already gated: a quoted span in a docstring or comment that attributes a sentence to a named repo file must appear in that file
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**Three passes on one PR produced three quotation defects and every one was found by a human-equivalent read rather than by a gate.** Pass 2 fixed two — a sentence attributed to `candidates.md` that is not in it (twice), and *"you never decide where a shipped candidate goes"* attributed to `plan_sprint.md` when it exists only in `triage_candidates.md`, about the workflow that does NOT place. **The consequence is worse than a wrong comment: a false quotation attributed to a named file actively stops the next reader checking**, because it reads as already-verified. The plan-sprint instance told a maintainer a prose backstop existed on an authorization surface where the MAY NOT row is the whole of it. **Done-state today: yes, and the mechanism already exists three times over** — `test_candidates_prose_matches_the_table`, `test_loop_cap_prose_is_counted` and `test_measurement_figures_are_cited` are all the same shape (a claim in prose, re-derived from the artifact it names). This is the fourth and it is mechanical: find `*"..."*` spans in .py docstrings/comments whose surrounding text names a repo path, and grep the file. **Not an expansion of C-6umbp67a/C-hii1c5ox/C-dhot2cyq/C-btl25fvg** — those are about what `plan-candidates` carries, how a filer names a component, how the loop-back routes, and how verify records success; this is a repo-wide prose gate with no scaffolding in it. **Measured against this pass as a control: all 8 checkable quotations in the diff verified verbatim**, so the class is currently clean and the gate is to keep it that way rather than to fix a backlog. Proposed independently by quality-control and by pass 2's own reflection, where it would have died at merge.

**Source:** PR for `plan-candidates` (build-refine pass 3, 2026-08-14)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
