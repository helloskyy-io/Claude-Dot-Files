---
id: S-otizrcwj
title: The one-paragraph-per-phase ceiling is violated by 32 of 32 roadmap entries in this repo, so it constrains nothing and misleads anyone who quotes it
status: open
count: 1
filed: 2026-08-29
filed_by: operator
target: docs/standards/documentation/documentation_standard.md
anchor: § Development Planning Files — Structure/Rules
---

**The rule, verbatim:**

> - One paragraph per phase describing what it achieves (not how)
> - Keep concise — **if a phase description exceeds one paragraph, the scope is too broad**

**Measured 2026-08-29 across every roadmap in this repo**, counting blank-line-separated
paragraphs under each `###` phase entry:

| component | entries | over one paragraph | counts |
|---|---|---|---|
| `memory-management-framework` | 6 | **6** | 4, 6, 5, 6, 5, 68 |
| `persistent-memory-protocol` | 12 | **12** | 3, 8, 4, 5, 4, 4, 4, 5, 5, 5, 17, 26 |
| `temporal-integration` | 9 | **9** | 5, 6, 5, 7, 6, 5, 5, 5, 33 |
| `workflow-decomposition` | 5 | **5** | 3, 5, 6, 7, 18 |

**32 of 32. Not one entry in this repo has ever met it.**

**The consequence is not untidiness — it is that the rule is quotable.** PR #145's
`roadmap.md:5` quoted this section as binding, asserted *"Pruned to that shape"*, and was
false in all seven of its entries. `review-pr` correctly held on that sentence for three
passes. Removing the sentence (done, on that branch) fixes the artifact and leaves the
rule exactly as quotable by the next planning pass — which is why this is filed rather
than closed there.

**And the rule is a SCOPE DIAGNOSTIC, not a prose limit**, which is what makes enforcing
it expensive: *"if a phase description exceeds one paragraph, the scope is too broad"*
says a long entry means the PHASE is wrong, not the writing. Enforcing it literally means
re-scoping 32 phases across four components, not trimming text.

**Three ways this could go, and the choice is the operator's:**

1. **Amend the rule to what the corpus does.** State a real ceiling — a sentence per
   phase in the roadmap with detail pushed to the phase doc, or a byte budget like the
   prompts carry — and one that an artifact can actually meet.
2. **Keep it and make it a gate.** A check that fails a roadmap entry over the ceiling.
   Honest, and it turns 32 entries into work before anything else ships.
3. **Keep it as advisory and SAY SO.** The cheapest, and it removes the trap: a rule
   marked advisory cannot be quoted as binding by the next plan.

**Recommendation: (3) now, (1) when someone has read enough roadmaps to name the real
shape.** The active harm is the quotability, and (3) removes it in one line. (2) is the
most rigorous and is the one to reject explicitly rather than defer silently — it prices
in 32 re-scopings to fix a problem whose measured cost so far is one false sentence.

**Not to be confused with `roadmap-outgrows-its-bound-shape` (#156)**, which asks for a
growth MECHANISM — how a roadmap is kept from ratcheting. This item is about a stated
ceiling that no artifact has ever been inside.

**Ratification is the operator's** ([standards-governance.md](../../docs/standards/finding-routing.md)):
this file proposes an amendment and applies none.
