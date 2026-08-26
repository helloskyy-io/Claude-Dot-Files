---
id: C-dhot2cyq
title: Route `plan-project`'s loop-back by WHAT THE RUNWAY NAMES, so a runway against a component's research is not spent on the one child that cannot close it
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**`plan-project`'s loop-back can only reach `plan-sprint`, and the comment justifying that reasons entirely about TRIAGE** — *"every candidate already carries a decision, so re-triaging would re-litigate rulings"* — because when it was written the research step was inert by construction and no research artifact could appear in a plan-project PR. **`plan-candidates` is what changed that**, which is why this is filed from this PR rather than earlier. **The consequence:** a `review-pr` runway naming a component's `synthesis.md` (a thin citation, an unverified span — exactly what `research-verify` and `research-critic` exist to catch) is dispatched `MAX_LOOPS` times at `plan-sprint`, which cannot edit a research pool, and the run then reports *"The automated loop is SPENT"* over a defect nobody addressed. The operator pays three opus dispatches and reads notes pointing at the sprint plan. **Done-state today: yes** — `research_workflow._verify_then_dispose` already routes a research runway to `research_verify` with `correction_pass=True`, so the shape exists and the work is choosing the child by runway content. **NOT a defect in what this PR built:** every documented behaviour of `plan-candidates` is correct and tested; this is a routing capability the parent has never had. **Not an expansion of C-hii1c5ox:** that is about a filer choosing a component name. This is about which child a correction pass reaches. Disjoint remedies, different files. **Not filed as an issue** — capability that would be ADDED, per [`finding-routing.md` § 4](../../finding-routing.md).

**Source:** PR for `plan-candidates` (build-refine pass 2, 2026-08-14)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
