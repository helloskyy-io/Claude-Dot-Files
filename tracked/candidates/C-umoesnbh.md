---
id: C-umoesnbh
title: A reviewer's recommended loop-back re-enters at draft and skips the two children that size and total the plan, so a revision lands numbers computed before the edit
status: open
count: 1
filed: 2026-08-28
filed_by: review-pr
component: 
size: 
decision: 
---

**PROPOSAL — `review-pr` recommends `plan_revision.sh` for loop-back, which re-enters at the DRAFT stage and skips `plan-verify` and `plan-sprint` entirely.**

**The evidence is MDC PM3's pass-2 measurement, and it makes the argument better than our own observation did:** *three of five new findings on pass 2 were introduced by the commit that fixed pass 1*, and **"a point-fix pass reliably generates the next pass's headline."**

**Why skipping the two children matters specifically.** `plan-verify` is what sizes phases and what the phase-count guard runs inside; `plan-sprint` is what derives the sprint header from those sizes. A revision that edits a roadmap and re-enters at draft therefore lands phase edits that **nothing re-sizes and nothing re-totals** — the exact class the sizing-floor and phase-link guards exist to catch, routed around by the recommendation itself.

**Consequence if unfixed:** the reviewer's own recommended remedy is the one path that bypasses the guards written for the thing being remedied. A run that takes the advice produces a plan whose numbers were computed before the edit.

**Remedy:** rule what `review-pr` recommends for a plan-stage loop-back — either re-enter through the full child chain, or state in the recommendation which guards the shortcut skips, so the operator is choosing rather than inheriting.

*Surfaced from PR #144's mining pass and independently by MDC PM3 (their A2). Held rather than fixed because what the reviewer recommends is a design call the operator has not made.*
