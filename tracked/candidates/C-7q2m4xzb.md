---
id: C-7q2m4xzb
title: Nothing guards duplication in the Python runner corpus, so Phase 3's nine adapters land in the one blind spot its own copying-risk note points at a guard to cover
status: open
count: 1
filed: 2026-08-27
filed_by: plan-verify
component: workflow-decomposition
size:
decision:
---

**PROPOSAL — give the runner corpus a duplication guard, or state in [Phase 3](../../docs/development/workflow-decomposition/phase3_dual_mode_children.md) that it has none.** Either is a fix; what is not acceptable is the current state, where the phase names a guard that structurally cannot fire on the population it is worried about.

**Measured 2026-08-27, and both halves of [Phase 2](../../docs/development/workflow-decomposition/phase2_family_alignment.md)'s alignment apparatus are scoped to prompt markdown.**

1. **The duplication ratchet reads `ASSISTANT.rglob("prompts/*.md")`** (`scripts/workflows/temporal/tests/unit/test_prompt_blocks_are_shared_not_copied.py:137`). Its population is prompt blocks under `modules/assistant/**/prompts/`. A Python file under `scripts/` is not in it, cannot add a row to `ACCEPTED`, and cannot turn the module red.
2. **`FAMILY_RULINGS` is keyed on prompt-fragment stems** (`scripts/workflows/temporal/tests/unit/fork_vs_parameterize.py:308`), and its validator rejects any ruling that names no category from the `_minor` tier contract. All eight categories — `operational-safety`, `evidence-discipline`, `finding-disposition`, `orchestration-mechanics`, `stage-ordering`, `review-depth`, `tier-identity`, `artifact-shape` — are categories of *prompt guidance*. A ruling covering nine Python runners cannot name one, so it cannot be expressed in that mechanism at all.

**The consequence, which is what makes this a finding rather than a note.** [Phase 3](../../docs/development/workflow-decomposition/phase3_dual_mode_children.md) is about to write **nine near-identical runners in one sitting from one template**, and its own § Notes calls that *"a copying event waiting to happen."* Its implementation step says to check them against the shared-prompt rule *"and this phase must not hand it nine new rows"* — but that guard cannot receive a row from a Python file, so a builder who runs the suite and sees green has been told nothing. The nine land unguarded while a guard appears to be watching, which is worse than landing unguarded knowingly.

**It has already happened at seven, and that is the evidence rather than the worry.** [[C-8tv8ewto]] records seven existing runners carrying a byte-identical `try/except RuntimeError -> print -> return 1` block. It was found by a review agent on PR #93, not by any guard, and the ratchet was green throughout. Nine more runners takes the corpus to twenty on one template.

**Proposed action — one of three, and the ruling is the deliverable.**

1. **Extend a duplication guard's population to the runner corpus** (`scripts/workflows/temporal/scripts/run_*.py`), with a frozen baseline the way the prompt ratchet did — the pattern already worked here once and its ratchet-both-ways property is what made the list shrink.
2. **Lean on `preflight.py` as the shared mechanism instead of a guard**, which is [[C-8tv8ewto]]'s `parse_or_exit(parser, argv)` promoted before the nine are written rather than after. This is the cheapest option and it fixes the seven at the same time; it does not cover the *next* duplicated block.
3. **Accept that the runner corpus is unguarded and say so in Phase 3**, so requirement 6's family ruling is understood as prose a reviewer applies rather than as something a suite holds.

**Not a duplicate of [[C-8tv8ewto]], and the two should be ruled together.** That item proposes promoting **one specific block** and would stand unchanged whichever way this is ruled; this asks whether the corpus has a *guard*. Option 2 above is the case where ruling this one adopts that one, which is exactly why they want reading side by side.

**Not [[C-yq30mgwd]] either** — that is about a child holding a drifted near-copy of a *pool fragment*, which is a prompt-side blind spot inside the ratchet's own population. This is about a population the ratchet does not have.

**Source:** `plan-verify` cold read of `docs/development/workflow-decomposition`, 2026-08-27. The determined half — that the phase's claim about the guard's coverage is false as measured — was corrected in [Phase 3](../../docs/development/workflow-decomposition/phase3_dual_mode_children.md)'s § *What this phase inherits from Phase 2's blind trial* in the same PR; choosing among the three remedies above is a design decision and was left here.
