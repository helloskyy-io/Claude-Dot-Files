---
id: C-9vb7pluf
title: Cross-reference OPEN issues against HEAD before a build brief is written — an issue whose fix landed in an unrelated PR stays open, and the next dispatch is briefed to fix a defect that no longer exists
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: continuous-process-improvement
---

**Measured on this dispatch, not hypothesised.** Issue #68 was filed 2026-08-08 against `review_pr_activities.py`'s unanchored `"pr_review:" in body` predicate. Its V2 half was fixed in PR #71 at `9fa69ff` (2026-08-09) — fence-anchored `PR_REVIEW_BLOCK`, seven covering tests, plus the `SHARED_KIND_ONE_PATTERNS` cross-tree gate — and the issue was never closed. On 2026-08-16 a build brief restated the defect verbatim, quoting a file:line that no longer holds that code, and Stage 1 spent a stage disproving a premise instead of building. **The failure mode is worse than the wasted turns**: the brief instructed the run to change code that is already correct and already gated, and a run that trusted its premise would have reverted a shipped fix. **This is a gap in the CPI loop, not in any one workflow** — the loop rules findings and files issues, and nothing reads the issue queue back against the tree afterwards. `gh issue list --state open` plus the fix's own test names is enough signal; the capability is the reading, which does not exist. Adjacent to C-523klr8n's shape (a declaration nobody derives) but a different surface: there the restatement is inside the repo, here it is the tracker.  **RENUMBERED from C-hurryucg on 2026-08-16**: `origin/main` had already landed a different C-hurryucg while this branch was open — the sixth such collision — so this row keeps its content and takes the next free id.

**Source:** PR #94 `build-draft` (issues #57/#65/#68)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
