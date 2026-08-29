---
id: S-30whkiii
title: A finding about the work in hand that is real but genuinely separate work has no disposition, so it must either be fixed now or hold the whole PR
status: open
count: 2
filed: 2026-08-28
filed_by: review-pr
target: docs/standards/finding-routing.md
anchor: §5 gate 0
---

**PROPOSED AMENDMENT — §5 gate 0's closed list has no exit for real-but-separate.**

Gate 0 states: *"`deferred`, `noted`, `escalated` and `surfaced` DO NOT EXIST for this class. Not discouraged, not a last resort — absent."* The three that remain are `fixed`, `rejected`, `hold`.

**That is deliberate and the reason is sound** — it is the anti-disposal-chute rule, and it works.

**But `review-pr` hit its edge on PR #145 and reported it:** six defects found by the PR's own later stages had no permitted disposition, and only the HOLD verdict carried them forward. **A reviewer who judged any of them minor and merged would have lost them**, because the closed list offers no way to say *"real, about the work in hand, and genuinely a separate piece of work."*

**Consequence:** the rule's success condition and its failure condition look identical from inside a run — both produce a finding with no home — so the run cannot tell *"I should fix this"* from *"this has nowhere to go."*

**Remedy — one of two, and the operator picks:** (a) a fourth disposition scoped so it cannot become a chute (permitted only when the reviewer also holds, so it never substitutes for one), or (b) an explicit statement that HOLD **is** the intended carrier for this case, which costs nothing and removes the ambiguity. **(b) is the cheaper reading and may already be the intent** — the rule simply never says so.

## Recurrences

- 2026-08-28 · 2026-08-28: recurred on the PR #145 correction pass, from a different child. `plan-feature` found the PR red on a test outside its write grant, reported it, and said so itself: *"a red PR is the work in hand, and gate 0 says that may only be fixed, rejected or held. The boundary forced a fourth thing."* Same gap, opposite direction from the reviewer's sighting — there the finding had no disposition, here the ACTOR had no permitted one.
