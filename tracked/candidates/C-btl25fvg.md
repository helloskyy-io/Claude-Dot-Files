---
id: C-btl25fvg
title: Let `research-verify` record its own success, so a component whose verify FAILED is re-verified on redispatch instead of reading as finished work
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**`plan-candidates` marks a fresh pool with `<!-- plan-candidates: seeded, no research yet -->` so an abandoned pool is RESUMED rather than skipped forever — but that marker can only recover the components a run had not reached yet.** `research-write` fully rewrites `synthesis.md` and commits before `research-verify` runs (its completion contract is a PR URL), so the marker is gone by the time verify can fail. **Measured by reproduction:** a pool whose synthesis was rewritten and never verified classifies as `extends`, is absent from `to_research`, and the parent prints *"the candidate extends it"* over an unverified synthesis that then reaches the planning PR. **The gap is not new and is not `plan-candidates`':** a sprint-section component whose verify failed was equally unrecoverable before this activity existed, because `new_sprint_sections` diffs from the redispatch's own base rather than from `origin/main`. What is new is that the seed marker made half the hole visible, and half a recovery reads as a whole one. **The remedy is a WRITE BY THE VERIFIER**, not a smarter reader: nothing downstream can distinguish *research that finished* from *research that was interrupted after the write* unless the step that finishes says so. **Done-state today: yes, and small** — one line in `research_verify` on the success path, plus reading it in `_is_unresearched`. **Out of scope here because `research-verify` is a CHILD TWO PARENTS SHARE** — `run_research` calls it as well, so changing its post-conditions from a `plan-candidates` PR changes the research parent without its tests in the diff. **Not an expansion of C-dhot2cyq:** that routes a correction pass once a runway exists; this is about a pool that never gets one. **Not filed as an issue** — capability that would be ADDED, per [`finding-routing.md` § 4](../../finding-routing.md).

**Source:** PR for `plan-candidates` (build-refine pass 2, 2026-08-14)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
