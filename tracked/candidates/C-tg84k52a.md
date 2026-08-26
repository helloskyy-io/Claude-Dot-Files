---
id: C-tg84k52a
title: Give `review-pr` a convergence stopping rule keyed on the KIND of finding a pass returns, so a PR whose remaining findings are all about its own gate infrastructure is scoped to closing them rather than accumulating new ones
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: continuous-process-improvement
---

**Measured on this PR: eight build passes and six `review-pr` dispositions, and the convergence is real rather than a treadmill — the KIND of finding shifts outward each pass.** Early passes closed content instances (six pipe-truncated rows in three files); middle passes closed coverage gaps in the class gate itself (the stray-line shape, the HTML-block residual); pass 8's findings were exclusively about the checking apparatus's own soundness — a duplicated derivation, two dead imports, an undisclosed fence asymmetry, a missing vacuity floor, a residual test asserting a property of `ast` rather than of its gate. Each pass audits a smaller and more introspective surface than the last, which is a recursion floor and not a loop. **The proposal is to make that observable rather than re-derived.** `quality-control`'s formulation: once a pass's findings are exclusively about gate infrastructure rather than about undetected instances of the original defect class, the next pass closes the open structural findings and adds no new checks, then ships. **Why this is not already covered by the existing convergence predicate:** that one counts passes and compares finding ids across them, so it cannot distinguish "pass 7 found three new things" from "pass 7 found three new things one abstraction level further out" — the second is convergence and reads to it as the first. **Cost of not having it:** each correction pass writes new tests minutes before shipping with no second reader, which is exactly where this pass's own surviving mutation was found (`stray_lines` was gutted with all 46 tests green), so an unbounded add-more-checks cycle manufactures the next pass's findings at the same rate it closes them.

**Source:** PR #96 `build-refine` pass 8, raised by `quality-control

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
