---
id: C-hurryucg
title: Give the build family's review stage the BRANCH as its subject rather than the producing run's own diff — commits already on the branch when a dispatch starts pass through no review lens at all and merge with it
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**The consequence is that a majority of what a PR delivers to the default branch can reach it unreviewed, and nothing reports that.** Measured on PR #93: six commits — `df3c98c`, `a223ccb`, `8df6029`, `42ccfb6`, `5c03389`, `92e2671` — were on `build/plan-verify` before the draft ran, so `build-refine`'s four review lenses, which are dispatched against the draft's diff, never saw them. They are not incidental: they change a PreToolUse safety hook, both hook timeouts in `settings.json`, the CI-gate verdict enum and the shipped build prompts. **The gap is not theoretical — `review-pr` reviewed them from the other side and found a real defect** (`wait_for_ci`'s docstring documenting a `raises` outcome the function never produces, which a caller would turn back into the read-failure/gate-absence conflation that cost PR #92 three rebuilds). **What this run VERIFIED rather than assumed:** the six commits are on the branch and not on `origin/main` (`git log --oneline origin/main..HEAD`); `build-refine`'s Stage 2 dispatches name the draft's diff as the subject; and this correction pass reproduced the finding by execution — monkeypatching `subprocess.run` to make every `gh pr checks` reply unparseable and calling `wait_for_ci("1")`, which RETURNED `False`. **Nearest neighbour is C-qtyemd45 and it is a different mechanism:** that one is about a gate that never RAN on the branch; this is about a review that ran with the wrong subject. **Shape of the remedy, not a design:** the reviewing stage takes `origin/main...HEAD` rather than the producing run's own commits, or the range is stated and the uncovered commits named in the PR body so the omission is at least visible.

**Source:** PR #93 for `plan-verify` (build-refine correction pass, 2026-08-15)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
