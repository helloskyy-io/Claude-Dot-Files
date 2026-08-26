---
id: C-qtyemd45
title: Enforce *merge `origin/main` and re-run before pushing* in the parent's push step rather than as a prompt instruction — a gate that lands while a branch is open is a gate the branch has never run
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

main` is **not branch-protected** (verified 2026-08-15), so nothing stops a stale-green PR merging with an unmet gate. A new `test_prompt_budgets.py` landed mid-branch and `plan_feature.md` failed it at 17,821 bytes with no budget line; it was caught only because that run happened to merge `main` a second time before pushing. **Belongs in code, not a prompt** — the prompt-economy standard's test 3 asks whether the harness can enforce it, and here it can, deterministically and without a model turn.

**Source:** PR #92 `plan-feature` reflections (3 passes, 2026-08-14/15)

**Routing note, for `triage-candidates`.** This reads as a proposed amendment to the TEXT of a named standard, which [§1](../../docs/standards/documentation/tracked_items_standard.md) routes to `tracked/standards/` rather than here. **It was not moved during the migration**: an id is immutable (§2), a prefix change is an id change, and this id may be cited elsewhere in the planning corpus. Rule on it — if it moves, mint a fresh `S-` id, carry the reasoning, and leave a pointer here.

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
