---
id: C-ffmdiiv6
title: Each planning stage appends its own PR-body section and none retracts an earlier one, so a multi-stage PR reliably tells its reviewer two contradictory facts about its own contents
status: open
count: 1
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
