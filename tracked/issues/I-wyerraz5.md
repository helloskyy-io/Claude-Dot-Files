---
id: I-wyerraz5
title: Twelve structural guards can go permanently green over an accumulating defect — none exercises its own predicate
status: open
count: 1
filed: 2026-08-17
filed_by: review-pr
repo: claude-dot-files
---

Twelve test modules in `scripts/workflows/temporal/tests/unit/` assert a **structural** property by walking the production tree with `ast.parse`, and none of them exercises its own predicate against a literal source snippet. The Testing Standard § *Structural tests need a positive control* (`docs/standards/testing/testing_standard.md:357`) is binding and requires exactly that:

> A test asserting a **structural** property — a contract-grep, a registration check, a "this routes through that seam" assertion — must additionally prove it fails when the property is absent. Without it, a pattern that stops matching (a rename, a moved file, a changed call shape) turns the test into a permanent pass.

## Consequence

Each of these twelve can go **permanently green over an accumulating defect**. A structural guard has two halves — the WALK that finds call sites, and the PREDICATE that decides whether each satisfies the property. All twelve have a vacuity floor on the walk and **nothing on the predicate**. If the predicate begins answering unconditionally after an AST-shape change, a keyword folded into `**kwargs`, or an ordinary refactor, every rule test passes forever *and* every floor still passes, because the walk is still finding sites.

That is strictly worse than having no guard: no guard prompts a review, a green guard replaces one. This is not hypothetical — the same defect appeared independently in two freshly-written guards in PR #101 and was caught by reviewers, which is what motivated enumerating the rest.

## Evidence

Measured on `8540ff32fcf4935733dfcd258b3109dd2bb1f6bb` (PR #101 head):

- Population of modules walking the production tree: **19**
- Of those, exercising their predicate on a literal: **7**
- Of those, **not** exercising it: **12**

The twelve, enumerated in `_WITHOUT_A_CONTROL_YET` in `tests/unit/test_a_census_guard_proves_its_own_predicate.py`:

```
test_a_grant_follows_its_flag.py
test_convergence.py
test_dry_run_previews_the_dispatched_prompt.py
test_exit_record.py
test_journal_containment.py
test_loop_cap_prose_is_counted.py
test_model_gets_the_worktree_path.py
test_pr_url_address.py
test_preflight.py
test_run_log_emission.py
test_the_suite_never_writes_to_the_operators_journal.py
test_triage_candidates_split.py
```

Reproduce:

```
cd scripts/workflows/temporal && python3 -c "
import ast, importlib.util
from pathlib import Path
s = importlib.util.spec_from_file_location('cg', 'tests/unit/test_a_census_guard_proves_its_own_predicate.py')
cg = importlib.util.module_from_spec(s); s.loader.exec_module(cg)
pop = cg._census_guards()
print('walkers', len(pop), 'controlled', sum(cg._parses_a_literal(t) for _, t in pop))
"
```

## Why this is a backlog item and not PR #101's scope

All twelve **predate** PR #101 — it created none of the debt. What it did build is the *detector*: `test_a_census_guard_proves_its_own_predicate.py` now fails any **new** tree-walking guard that ships without a control, and `test_no_exemption_is_stale` makes the exemption list shrink-only, so the debt cannot grow or quietly become permanent. The forward-looking half is closed.

What remains is the paydown, and it is real work: each control must be written against a predicate its original author designed. Doing twelve of those unreviewed at the end of a correction pass is the exact mechanism that produced this finding, which is why PR #101 grandfathered rather than cleared them.

## Proposed next action

Pay the list down incrementally — one control per module, deleting that module's line from `_WITHOUT_A_CONTROL_YET` as each lands. Each control is a literal source snippet the module's own visitor is run over, asserting the predicate flags it (and a matching negative snippet it must not flag). The list reaching empty is the done-state; `test_no_exemption_is_stale` already fails if an entry stops needing its carve-out, so progress is self-verifying.

Sizeable enough to split across several passes; no single change is blocked on the others.

---

Filed by `review-pr` disposition pass 3 on PR #101, under the review workflow's filing authority for deferred work that is unrelated to the PR in hand, substantial, and not covered by an existing item.



---

*Migrated from `Claude-Dot-Files#103` on 2026-08-26.*
