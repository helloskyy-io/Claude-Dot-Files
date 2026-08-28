---
id: C-w16p97vt
title: A fix lands at the site a finding named while the same claim lives at N others, so every unfixed sibling is a guaranteed finding on the next pass
status: open
count: 1
filed: 2026-08-28
filed_by: review-pr
component: 
size: 
decision: 
---

**PROPOSAL — after closing a finding, sweep the component for the same claim shape and report the site count; and state whether a finding's site list is EXHAUSTIVE or a SAMPLE.**

**TWO INDEPENDENT ROOT-CAUSE ANALYSES REACHED THIS, ON DIFFERENT PRs, ON THE SAME DAY.**

**MDC PM3, PR #171** — six passes, $83.43, 13 dispatch runs. Of 23 dispositions after pass 1, **fourteen findings did not exist when the review started**; they appeared during the fixing. RC1 accounts for ~6 of them in **five distinct forms** — a fix landing at one site while the same claim lived at N:

| finding | fixed at | same claim also at |
|---|---|---|
| `dependency-population-figures-contested` | `roadmap.md`, 1 site | a phase doc — **6 sites** untouched, plus an acceptance gate |
| `plan-asserts-candidate-state` | 4 sites, then 4, then 3 | **11 total**, discovered across three passes |
| `ordinal-pointers-resolve-to-wrong-requirements` | phase renumbered | its three inbound ordinal pointers |

**CDF, PR #145** — three passes. Pass 1 found *"a ruling with no address"* **twice** and wrote a runway naming those two; the **third** instance surfaced in pass 2, costing a whole loop. `pr-body-claims-contradicted-by-own-diff` held in **all three passes** — fixed twice, back twice. Roughly **a third of all holds were repeat members of a class already identified.**

**IT IS STRUCTURAL, NOT A SKILL PROBLEM, AND THAT IS THE STRONGEST EVIDENCE HERE.** The same failure hit an autonomous dispatch, a human operator working carefully by hand, AND an interactive session that had just written the finding up. PM3's account: *"read a finding titled 'figures contested in one doc', fixed the doc I had noticed, and never opened the doc the prescription actually named."*

**ALREADY REQUESTED ONCE AND NEVER BUILT.** A `plan-revision` reflection asked for exactly it — *"for each finding you just fixed, grep the file for other instances of the same claim or the same defect shape"* — and a later `review-pr` pass then cited the unbuilt request as its own evidence: *"three of my five new findings are exactly that failure."*

**Consequence:** every unfixed sibling is a guaranteed finding on the next pass, so the loop cannot converge faster than the class is enumerated. It is the dominant generator of the passes both repos are paying for.

**Remedy, two halves and they need each other:**
1. **Post-fix sweep (the fixer's half).** For every finding closed, grep the component for the same claim shape and report the site count in the report. Mechanical.
2. **Exhaustive-or-sample (the reviewer's half).** A finding's prescription enumerates every site it knows of and says explicitly whether that enumeration is complete. *"4 of an unknown total"* is actionable; *"4 sites"* implies a closure that does not exist — and the fixer cannot close what the finding did not enumerate.

**PM3's estimate:** RC1+RC2 plus the anchor validator account for ~7 of 14 generated findings — about two passes and ~$25 per feature, before counting operator time.
