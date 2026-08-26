---
id: C-0wbwye5a
title: **A workflow's two entry wrappers can hold different general guidance and no guard can see it, so a new-branch run and a resume-a-PR run of the SAME child follow different rules**
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**Measured in this tree, at the duplication guard's own predicate.** `build_draft_minor` dispatches from one of two wrappers — `prompts/new_branch.md` when starting fresh, `prompts/update_pr.md` when resuming a PR — and the two are near-copies maintained by hand. Splitting both at blank lines, keeping blocks of 120 bytes or more, and scoring each `update_pr` block against its best `new_branch` counterpart with `difflib` at `autojunk=False`: four blocks in `update_pr.md` have no counterpart above 0.55. **Two of the four are legitimately path-specific** — the SELF-DESCRIPTION bullet and the print-the-PR-URL step exist only because there is a PR. **Two are not**: *IF THE TASK IS TO CHARACTERIZE EXISTING BEHAVIOUR* and *CAN IT FAIL?* are general discipline, and a `build-draft-minor` run started on a new branch is simply never told either. **Git says which way it went:** `44706eb` and `8be3600` each added content to `update_pr.md` and to `build_draft/prompts/stages_1_to_4.md` in the same commit, and to `new_branch.md` in neither. **WHY NO GUARD REACHES IT, which is what makes this a proposal rather than a note.** Every duplication and drift detector in the tree compares across CHILDREN: `test_prompt_blocks_are_shared_not_copied` keys blocks by owning child and needs `len(owners) > 1`, so two files inside ONE child collapse to a single owner and register as no duplication at all; `test_tier_siblings_do_not_DRIFT_by_a_sentence` iterates `TIER_PAIRS`, which are pairs of children. The intra-child axis has no detector at any granularity. **Not an expansion of C-yq30mgwd**, which is the child-to-pool axis — a different pair of surfaces and a different remedy (C-yq30mgwd needs a detector that reads the pool; this needs one that reads two files inside one child). **Not C-at80groo either** — that asks what a `_minor` TIER must contain, and this is one tier disagreeing with itself. **Done-state today: yes.** The predicate already exists and is quoted above; what does not exist is a guard that applies it within a child, and a ruling on whether the wrapper pair is the right unit or whether the real unit is (wrapper + stages body), which is the shape this phase's blind trial found had mis-formed one of its own comparison pairs. **PROPOSAL, not a defect:** nothing is wrong that this PR introduced, and the two orphan blocks predate it by weeks.

**Source:** PR for Phase 2 (`build-draft`), surfaced by this phase's own blind trial

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
