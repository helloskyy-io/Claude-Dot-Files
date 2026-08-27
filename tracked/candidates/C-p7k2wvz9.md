---
id: C-p7k2wvz9
title: An OPEN phase's completion criteria name two stores deleted on 2026-08-26, so a build dispatch would write a replay test against files that do not exist — and nothing in the tree checks for a reference to a deleted store
status: open
count: 1
filed: 2026-08-27
filed_by: plan-feature
component:
size:
decision:
---

**MEASURED, not inferred.** `git ls-files | grep -E '(^|/)(candidates|direction)\.md$'` returns nothing — both files were deleted by the four-store migration on 2026-08-26. `docs/development/persistent-memory-protocol/phase4_rebuild_is_a_test.md` is an OPEN, unbuilt phase, and it names `direction.md` **six times** and `candidates.md` **twelve times in total**, including in its own completion criteria:

- **Requirement 1** — *"Replay of the journal reproduces `candidates.md` and `direction.md`"*
- **Requirement 2(b)** — *"materialising a housekeeping record into `candidates.md` is exactly the junk this separation exists to prevent"*
- **Requirement 6** — *"`candidates.md` and `direction.md` are now rebuilt from the journal, and the doc that describes them says so"*

**The consequence is a build dispatch, not a typo.** Phase 4's whole deliverable is a test that replays the journal into two named stores and diffs the result. Both names are gone, one of them (`direction.md`) with its entire `D-NNN` series and its 90-day rotation — which the phase doc leans on explicitly as the case that exercises "the live store deliberately holds *less* than the journal" (`:136`). A run handed this doc cold builds a replay target that cannot resolve, or silently substitutes `tracked/candidates/` for a two-store test and loses the asymmetry the test was designed around. **Requirement 1 as written can never be checked**, which is the exact shape [`engineering-quality.md` § *Finding disposition*](../../config/rules/engineering-quality.md) calls a criterion whose target is gone.

**The wider residue, so the size is honest rather than implied.** Excluding `tracked/` itself, the two deleted filenames appear across the planning corpus in `persistent-memory-protocol/` (phase docs 1–5, 7, 8, roadmap, research pool) and `memory-management-framework/` (phases 1, 2, 6, roadmap), plus `cpi-decisions.md:1069` asserting in the present tense that a want *"is now served by `direction.md`"*. **Most of these are legitimate dated records and must be left alone** — the operator's standing rule for a vocabulary sweep is *rename it where it is still binding; leave it where it is a record.* The defect is confined to the sentences that are still binding, and PMP Phase 4's requirements are the clearest instance because the phase has not been built.

**PROPOSAL, and it is the gate rather than the sweep.** Fixing PMP Phase 4's wording is a defect for whoever next verifies that component; this row is for the missing control. `testing/scripts/tests/unit/test_retired_vocabulary_is_gone_from_live_surfaces.py` already exists and already solves this exact problem for a *different* retired vocabulary — the `Kind 1` / `Kind 2` / `Kind 3` labels — and its own docstring records the argument: **"Five spellings, four passes. Enumerating instances does not converge; changing what the check keys on does."** The four-store migration retired a second vocabulary (`candidates.md`, `direction.md`, `D-NNN`, the standup-tracker issue, `tracked-intake` outside its one permitted use) and shipped **no** equivalent gate, so the same four-pass convergence failure is now running unobserved in the planning corpus.

**Done-state today, which is why this is a candidate and not a phase checkbox.** Extend that module — or add a sibling keyed the same way — with a second retired-vocabulary set for the deleted stores, reusing its existing machinery unchanged: whitespace-normalised whole-file reads rather than line-based grep, and a declared allowlist for the surfaces that are genuinely records (`cpi-decisions.md`, the research pools, `config/commands/standup.md`'s dated correction note, the migration-explaining docstrings under `scripts/`). Nothing new has to be invented; the instrument exists and the corpus of legitimate records is already the shape its allowlist takes.

**Distinctness, in this store's convention.** NOT [[C-zwzepum0]], whose class is *a claim about how another file BEHAVES* — that class was judged un-gateable for want of syntactic signature, and a deleted filename has the strongest signature there is. NOT [[C-523klr8n]], whose remedy is *derive rather than restate*; there is no second copy to derive a store name from. NOT [[C-9yi1yv2h]], which is about a research paper whose `Feeds:` destination was deleted — a paper-lifecycle state question, not a text-reference check. NOT [[C-w8h0cg9l]] or [[C-j7piza3v]], both of which are about `file_structure.txt`'s leaf/annotation parsing.

**Source:** `plan-feature` verification pass over `docs/development/workflow-decomposition/`, 2026-08-27. That component's own docs were found clean of this class — the residue is entirely in siblings the run could not write to, which is why it is filed here rather than fixed.
