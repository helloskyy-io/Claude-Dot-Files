---
id: C-tjuvqcww
title: Harden four filters that test `path.parts` of an ABSOLUTE path — the same shape that made `test_relative_links_resolve.py` scan **0 files from a worktree and 354 from the main checkout at the same commit**
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**Not reachable today, and that is the finding rather than a reason to skip it.** The link test's `SKIP_PARTS` held `.claude` and `worktrees`, both of which appear in every worktree path, so the filter ate the entire scan and its assertion had never once run in a dispatch; only its vacuity guard surfaced it. The four remaining instances (`test_convergence.py:804`, `test_pr_url_address.py:344`, `test_exit_record.py:1072`, `test_prompt_budgets.py:76`) skip on `tests` / `prompts`, which appear in no path we use — so they are the identical latent shape awaiting a differently-named checkout. One line each: filter on `relative_to(ROOT).parts`.

**Source:** PR #92 `plan-feature` reflections (3 passes, 2026-08-14/15)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
