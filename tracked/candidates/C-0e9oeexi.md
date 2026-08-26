---
id: C-0e9oeexi
title: Key `plan-project`'s resume on the PLANNING deliverable — a component with research complete and no `roadmap.md` needs `plan-feature` — instead of on a research marker that is gone by then
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**`scaffold_candidate_components` decides *does this component still need work?* from the `<!-- plan-candidates: seeded, no research yet -->` marker in its `synthesis.md`, and `research-write` strips that marker as its first act — so the resume signal cannot see the planning step at all.** **The consequence, verified by reading the three files that form the chain:** a component whose research SUCCEEDED and whose `plan-feature` then failed reads as `extends` on every later `--pr` redispatch. It never re-enters `to_research`, never re-enters the `origin` map that drives the loop, and nothing anywhere in the pipeline asks whether a scaffolded component has a `roadmap.md`. `review-pr --type planning` judges a diff, not corpus completeness, so it is not the backstop either. The component leaves the automated pipeline silently, with fully-verified research and no plan. **What WAS fixed in this PR, and why that is not this:** the parent now catches a mid-loop failure and tells the operator, in the raised message, that the component is orphaned and what the standalone recovery command is. That closes the DEFECT — an operator inheriting a false impression of completeness — and leaves the capability gap: the pipeline still cannot recover on its own. **Done-state today: yes, and small** — the resume classifier reads `(<component>/roadmap.md).is_file()` alongside the marker it already reads, so *needs planning* stops being derived from *needs research*. **NOT an expansion of C-btl25fvg**, and the distinction is the whole reason this is separate: C-btl25fvg has `research-verify` record its own success so an INTERRUPTED verify is re-verified. Its remedy is a marker written by the verifier — which, on this scenario, would correctly read *verified* and still skip the component, because the step that failed was the one after it. Different failing step, different signal, and C-btl25fvg's fix does not reach this case. **Not filed as an issue** — capability that would be ADDED, per [`finding-routing.md` § 4](../../finding-routing.md). *(Id taken by re-reading this file at HEAD and comparing against `origin/main` immediately before writing: `origin/main` ran to C-gbclnzsq, this branch to C-w8455f0l, and the merge of the two was resolved before this row was appended.)*

**Source:** PR for `plan-feature` (build-refine pass 2, 2026-08-14)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
