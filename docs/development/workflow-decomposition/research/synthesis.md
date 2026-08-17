# Synthesis — workflow-decomposition research

**Cycle:** 2026-08-17 (cycle 1) · **Pool:** 1 paper · **Tier:** Small / single-concern component

Read this instead of the pool. It says what the evidence means for the Phase 2 ruling and ends in reviewable candidates. Nothing here is binding — research is evidence, and a finding becomes a rule only by being codified into a standard through human review.

## Inputs

| Paper | Last validated | Revalidate | Critic verdict |
|---|---|---|---|
| [`raw/fork_vs_parameterize_drift_signal.md`](raw/fork_vs_parameterize_drift_signal.md) | 2026-08-17 | high — 6 weeks | **not-yet-verified** — a separate fresh-context run has not yet run against this paper |

This paper also leans on an upstream, product-pool paper it cites rather than re-derives: [`docs/standards/architecture/research/raw/workflow_reuse_boundary.md`](../../../standards/architecture/research/raw/workflow_reuse_boundary.md) (`Last validated: 2026-08-03`, `Revalidate: high — 6 weeks`, `Critic: PASS-WITH-FIXES` — inside its window). Treat any claim below sourced to "upstream" as carrying that paper's own verdict, not this cycle's.

**Consume the paper before acting on this synthesis** if you are within the paper's `not-yet-verified` window and the decision is consequential — the standard treats an unverified paper as unverified evidence.

## What this means for us

**The question this cycle answers:** holding only two already-drifted prompt texts — no authoring history, no author to ask — what tells a reviewer a deliberate variant from a neglected copy? The upstream paper already settled the *general* parameterize-vs-fork question (the field's discriminator is expected future co-evolution, not textual overlap) and explicitly declined to extend it to prompt prose. This cycle's paper is the extension, and it answers a narrower and more useful question than the one the roadmap item names: not "is this drift intentional" in the abstract, but "what can a reviewer with no history actually check."

Three findings change how the open roadmap item should be read:

1. **Intent is a property of a person's awareness, not of a text — so no artifact-only method can be complete, and the roadmap item's phrasing ("a copy that has already drifted reads as intent") is a heuristic, not a rule that can be automated.** The paper's own §6.1 makes the honest admission: any retrospective method "is not recovering intent; it is forecasting co-evolution and calling the forecast intent." This caps how far any tooling investment on this half of Phase 2 can go — the ceiling is a human judgement with reasoning written down, which is where the standard already puts it.

2. **The one implemented, precision-evaluated method for prose (RepliComment, 79% precision) compares each copy to its own referent, never the two copies to each other — and drift *magnitude* (the 85.8/76.1/62.1% figures) is not a signal anyone in the corpus uses; drift *pattern* (whole-block presence/absence vs. named-entity substitution) is.** This directly undercuts the intuitive next move ("diff the two harder" or "set a similarity threshold"). It also means the standard's own similarity figures are decorative for ruling purposes even where they're checkable — and the paper found they currently aren't: neither the test docstring nor `workflow-scripts.md` names which three prompts they describe or how the percentage was computed.

3. **The field's own conservative default — when the author can't be asked, assume deliberate — does not transfer to us, and importing it silently would reproduce the exact harm the ratchet exists to prevent.** Juergens et al. defaulted inconclusive cases to "intentional" because that direction was conservative *for their research claim* (it made their hypothesis harder to confirm). Our decision has the opposite shape: defaulting to "deliberate" preserves the copy, which is the documented failure (`stages_1_to_4.md` / `_from_plan.md` forking silently and one sibling losing eleven testing rules). A borrowed default with an unexamined rationale would point this repo the wrong way.

**One measurement this repo can run that the literature never could:** commit history exists here even though the ruling method must not consult it while classifying. A sealed blind classification, scored afterward against history, converts the paper's derived four-signal ordering into a measured one — Kapser & Godfrey couldn't do this because they had no ground truth; we do.

## Action candidates

Reviewable items, sized for a standup. Nothing is ratified. Per §7 this run surfaces candidates here and writes nothing outside `research/` — routing is the reviewer's and the operator's.

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Rule Phase 2's fork-vs-parameterize item as: a human judgement, with the reasoning written down (signal 4 short-circuits the rest) — never an automated gate.** The κ = 0.271 inter-rater reliability ceiling (three expert judges, eleven categories, "fair" agreement) and the structural point that intent is an awareness property, not a text property, together rule out a scored/automated version of this ruling. | adopt | `raw/fork_vs_parameterize_drift_signal.md` §2.2, §6.1–6.2 |
| 2 | **When ruling on a specific drifted pair, check fit-to-referent and drift pattern (whole-block vs. named-entity vs. in-place rewording) — not inter-copy similarity percentage.** The one implemented retrospective method for prose targets referent-fit; no source uses magnitude as a signal. This directly informs how a human applies candidate 1's judgement. | adopt | `raw/fork_vs_parameterize_drift_signal.md` §3.3, §4.2 |
| 3 | **Do not import Juergens et al.'s "default to intentional when the author is unreachable" convention.** It was conservative for a research hypothesis, not for a merge decision; our failure mode runs the opposite direction (default-to-deliberate preserves silently-forked copies). Any local heuristic that leans on the literature's default without this caveat would be a methodological error. | reject (of the naive import) | `raw/fork_vs_parameterize_drift_signal.md` §6.3 |
| 4 | **Either publish the method behind the standard's 85.8% / 76.1% / 62.1% similarity figures and name the three prompts, or drop the numbers.** They appear in exactly two places (the ratchet test's docstring and `workflow-scripts.md:715`), neither states which prompts or how the percentage was computed, and the paper's own finding is that magnitude isn't a signal anyone uses — so dropping costs nothing. Homeless in the sense that this run cannot fix it (write boundary), but it is a small, well-scoped fix for whoever touches those two files next. | new concept *(cheap correction, not a new capability — flagged as adopt-shaped)* | `raw/fork_vs_parameterize_drift_signal.md` §7 item 5, §3.4 |
| 5 | **Run the blind-classify-then-reveal-history validation (test plan items 1–2).** Two reviewers classify the five currently-drifted prompt groups from text alone, then are scored against the real commit history. Cheap, and it is a check no cited study could run because none had usable ground truth. | adopt | `raw/fork_vs_parameterize_drift_signal.md` §7 items 1–2 |
| 6 | **No change to the `from_plan.md` byte-identical pair or any other specific pair.** Neither this paper nor this synthesis rules on a script — that's explicitly out of scope, and the pair may be a legitimate pending-fork. | no change *(the restraint is the finding)* | `raw/fork_vs_parameterize_drift_signal.md` §5.3, §6.5 |

**Homeless finding:** candidate 4 has no home this run can write to (component write boundary forbids editing `workflow-scripts.md` or the test file) — surfaced here for the reviewer, per §7.

## Gaps this cycle did not cover

- **No prompt/LLM-engineering literature on divergence between copies of a prompt exists yet** — established by full-text search of the 2026 *Promptware Engineering* survey; the term "prompt drift" in that literature means output-behaviour change over time, not copy divergence. If this literature appears later, it is the first thing a refresh should re-check (§3.5 of the paper is flagged high-volatility for exactly this reason).
- **Whether fit-to-referent scoring is computable for a prose referent (a child's job description) rather than a formal one (a method signature) is untested** — the paper's single highest-value open question, named as test-plan item 3.
- Three adjacent lines of enquiry were named and not pursued, per this component's edges: whether the current child set is the right one (Assistant Workflow Design), whether a shared fragment survives a resumed/retried run (Temporal Integration), and whether a prompt block makes a child better at its job (Self Improvement).
