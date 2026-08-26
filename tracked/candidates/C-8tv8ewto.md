---
id: C-8tv8ewto
title: Promote the seven runners' identical `try/except RuntimeError -> print(f"\n✗ {exc}") -> return 1` block, so the family's operator-facing failure message has ONE implementation instead of seven
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**Seven consumers now carry it byte-identically, and this file's own promotion rule is a consumer count rather than taste** — `resolve_operator_paths` was promoted at TWO under §10.1 rule 3 (*"if and only if more than one workflow uses it… the consumer count decides, never taste"*), and this block is at seven. **The consequence is the drift `resolve_operator_paths`' own docstring names, one altitude down:** the next change to how a bad invocation is reported — a hint line, an exit code that distinguishes a refusal from a crash, routing to `logging` — lands in whichever runner the author had open, and the other six keep the old shape with nothing in any diff to show the divergence. **NOT a defect in what this PR built, and that is why it is a proposal rather than a fix:** the block predates this change (it wrapped the bare `preflight()` call in six of seven V2 entrypoints before `RepoPathParser` existed); this PR made it MORE uniform, not less. **Deliberately not extracted here** — `code-style.md` prefers three similar lines to a premature abstraction and `engineering-quality.md` § *Surgical changes* forbids refactoring adjacent working code inside a security fix; touching all seven runners would have put churn in the same diff as an authorization boundary, where a reviewer most needs to see only what changed. **Done-state today: yes, and it is one function** — a `parse_or_exit(parser, argv)` in `preflight.py`, which already owns `RepoPathParser`. **Raised by `refactoring-evaluator` at Medium on this PR, which recommended surfacing rather than doing it.** *(Id taken by re-reading this file at HEAD and confirming `git log 9e054ea..origin/main` was empty immediately before writing: `origin/main` had not moved since this branch's merge commit, and C-emxcrzti was the highest on either side.)*

**Source:** PR #93 `plan-verify` (build-refine, 2026-08-16)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
