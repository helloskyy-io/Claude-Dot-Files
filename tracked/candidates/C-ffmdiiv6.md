---
id: C-ffmdiiv6
title: Each planning stage appends its own PR-body section and none retracts an earlier one, so a multi-stage PR reliably tells its reviewer two contradictory facts about its own contents
status: open
count: 3
filed: 2026-08-28
filed_by: review-pr
component: 
size: 
decision: 
---

**PROPOSAL — the stage that falsifies a claim in the PR body retracts it.**

**Reported by MDC PM3 on 2026-08-28 with the clearest instance yet.** PR #171's body carried, ten lines apart:

> *"**Four per-item hour figures** (`~35h`, `~22h`, `~34h`, `~24h`, totalling the ~115h above)"*
> *"**No hours, no days, no points, anywhere in this PR.**"*

**Both were written by the tooling and both were true when written.** `plan-feature` wrote the NOT-SIZED section and was correct — it does not size. `plan-verify` and `plan-sprint` then appended sections carrying figures, and nothing retracted the earlier claim. The body also still cited `~115h` after `plan-verify` superseded it with `~128h`.

**Structural, not a slip: each stage APPENDS its own section and no stage reconciles the body as a whole.** It recurs on every multi-stage PR.

**Three sightings, two repos.** MDC's `review-pr` flagged the class twice on PR #171 alone (`pr-body-denies-sprints-edit`, `pr-body-denies-the-sizing-this-pr-contains`); ours flagged it once on PR #145 as runway item 7, where it was fixed as a one-off rather than recognised as a class.

**Consequence:** the PR body is what a human reads to decide whether to merge, and a multi-stage planning PR reliably presents it two contradictory facts about its own contents. Worse, the contradiction is self-cancelling — a reader who spots it distrusts both halves, including the true one.

**Remedy (PM3's, and it is the cheapest):** the stage that falsifies an earlier claim strikes it. For sizing that is `plan-verify`, since writing the figures is what makes the NOT-SIZED section false.

**Distinct from the stale-restatement class we deliberately did NOT fix.** There, restating a format in a prompt would have drifted from the file it described. Here the false claim is already written into a durable artifact and needs withdrawing by whoever falsified it — no prompt restates anything.

## Recurrences

- 2026-08-28 · 2026-08-28: second sighting, our own PR #145, and it caught the REVIEWER this time. `review-pr` pass 1 prescribed a fix for the stale body total; the fix landed exactly as written and `plan-verify` invalidated it fifteen minutes later by re-sizing. Pass 2 named the gap in its own prompt: *a prescription that lands correctly and is then invalidated by a later stage of the same dispatch has no name in this prompt.* Its remedy sharpens the candidate's: the fix is to REMOVE the literal, not to re-type it — re-typing is what put it back. Applied to #145's body on 2026-08-28.
- 2026-08-28 · 2026-08-28: third sighting, and the first from another repo. MDC PM3's PR #171 RCA files it as RC4 with two flagged instances (passes 3 and 5): `plan-feature` wrote 'No hours, no days, no points, anywhere in this PR' — correct, it does not size — and `plan-verify` then appended ten hour figures with nothing retracting the claim. Their remedy matches ours exactly: the stage that falsifies an earlier claim retracts it, cheapest at `plan-verify`.


## The remedy we proposed is ALREADY BUILT, and that is the finding

**2026-08-28.** Both this item and MDC PM3's RC4 proposed *"the stage that falsifies an earlier claim retracts it."* **That instruction already exists**, in `prompts/submit_and_push.md` — the shared fragment EVERY producing child receives:

> **RE-READ THE WHOLE BODY AGAINST THE TREE, not just the part you wrote.** … Open every path it names and confirm it exists; check every count and filename against what is on disk now.

It is emphatic, it cites its own measured evidence, and **it predicted PR #145 exactly**: *"a fix that leaves the PR's own description stale mechanically manufactures findings for the next review pass (measured: 1-2 per round, and one pass found ZERO code defects — only self-description drift)."*

**#145 produced 1–3 body findings per round, across three rounds, with that text in context every time.**

**So writing the instruction is not the remedy — the strongest available version of it is already written and was ignored three times by three different actors.** The fragment names the cause itself: ***"there is no run whose job the body is, so it is nobody's until it is everybody's."***

**That is a shared-ownership problem, and instructions do not fix those.** The two remedies that could:

1. **Give the body ONE owner.** The last stage before `review-pr` reconciles it whole; earlier stages append and do not verify. Ownership beats exhortation, and it is testable — the owner either ran the check or did not.
2. **A mechanical check.** Every figure and path in the body re-derived and diffed against the tree, in code, the way `phase_sizing` is. No model judgement, so no model to ignore it.

**[[C-hdme5l4k]] is the same class, filed narrower and earlier**, for `research_verify`. Its `count` has been incremented; this item carries the general shape.
