---
id: C-w8h0cg9l
title: **A new row spliced into the MIDDLE of an existing `file_structure.txt` entry silently reassigns that entry's annotation to the new one, and every check in the repo stays green** — the two map guards parse leaf lines only, and `test_retired_vocabulary_is_gone_from_live_surfaces.py`, which does join a leaf to its continuations, reads the resulting mis-attribution as a valid entry
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**Measured on this PR, and it shipped.** `31a5c70` inserted the new guard's entry between the leaf line of `test_no_module_compiles_with_a_SYNTAX_WARNING.py` and its three continuation lines. The sentence *"Every tracked .py compiles clean. One"* was left dangling, and *"invalid escape in a docstring... fails to COLLECT"* was re-attributed to the `/tmp` guard. All four CI checks passed, both map-completeness guards passed, and two review passes read the region without seeing it — the map's own consumer states in its docstring that *"AN ENTRY IS A LEAF LINE PLUS EVERY CONTINUATION LINE UNDER IT"*, so the join is by nearest-preceding-leaf and a splice parses as VALID. Fixed in place here; the candidate is the missing CHECK. **Done-state today: yes, and it is validated rather than argued** — every continuation line of one entry must share one annotation column. Run against the tree at `31a5c70` that predicate returns exactly one offender, the spliced entry, with columns `[52, 53]`; run against the whole map as repaired it returns ZERO, so the check is shippable and not merely noisy. **What it does NOT catch:** a splice whose continuations happen to be aligned correctly. That is a weaker instrument than the defect deserves and is the part worth triaging — the alternative, asserting an entry's joined annotation is a complete sentence, is a heuristic and may not be worth its false positives. **`component` deliberately blank**, following C-pky2l2b6, which is the other row about this same artifact and left it blank for the same reason: the map is repo-wide tooling and no `docs/development/<name>/` owns it.

**Source:** PR #135 (`build-refine-minor`)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
