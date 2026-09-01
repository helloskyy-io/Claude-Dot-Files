"""A guard that walks the tree must prove its own question still discriminates.

THE CLASS THIS HOLDS IS THE GUARDS THEMSELVES, and it exists because the pass
that wrote the two newest ones got this wrong twice in one afternoon.

A structural guard has two halves. The WALK finds call sites; the PREDICATE
decides whether each one satisfies the property. Both new guards shipped with a
vacuity floor on the walk (`test_the_census_is_not_vacuous`) and NOTHING on the
predicate — so had `bounded` or `_guarded` begun answering unconditionally after
an AST-shape change, a keyword folded into `**kwargs`, or an ordinary refactor,
every rule test would have passed forever AND every floor would still have
passed, because the walk was still finding sites. A permanent green over an
accumulating defect, which is strictly worse than no guard at all: no guard
prompts a review, a green guard replaces one.

Reviewers caught it in both files. That is the reason this test exists rather
than a third fix: the same defect appearing independently in two artifacts from
one author in one pass is a CLASS, and the answer to a class is a check, not
three corrections. The Testing Standard already requires this
(§ *Structural tests need a positive control*); what it could not do is notice
when somebody skipped it.

HOW THE PROPERTY IS RECOGNISED. A census guard is a test module that walks the
production tree — recognised by what it DOES, `ast.parse(<something>.read_text(
...))`. That is the population. Each one must ALSO exercise its predicate
against at least one literal source snippet, i.e. build its own visitor over an
`ast.parse` of a string rather than of a file.

THE RECOGNISER USED TO KEY ON A PRIVATE VARIABLE NAME, AND THAT IS THE DEFECT
THIS FILE SHIPPED WITH. It required a module-level `_ROOTS`, and the bullet
below used to claim "the two spellings covered are the two the tree uses".
Most of this population spells its roots `_TEMPORAL`, `_SCRIPTS`, `_RUNNERS`,
`FLEET`, or a bare local — so whether the rule applied to a guard was decided by
its author's choice of variable name, and every uncontrolled guard sat outside a
check that was green. The file condemning permanent greens was one. Keying on
the BEHAVIOUR is the fix, because a module cannot walk the tree without doing
the thing being matched; the uncontrolled ones are grandfathered by name in a
list that may only shrink.

THE POPULATION FIGURES ARE DERIVED BY `test_the_census_matches_the_tree` AND
WRITTEN IN NO PROSE HERE. The version of this docstring that shipped said
"Measured: **18** modules here walk the production tree; **2** carry `_ROOTS`",
repeated that first figure in the comment below, and derived a third from the
pair. Both were wrong, and they were wrong ON ARRIVAL — the commit that wrote
the sentence added a walker in the same commit. Nothing went red, so every
guard added after it would have made the claim further wrong in silence.

That is the failure this whole PR is about, committed by the file that states
the rule: a coverage claim must either be a derived assertion that goes red, or
must not be written as a universal. This file takes the first arm for its
population and the second arm for its recogniser's boundary, and says which is
which below. The repository gates this class in four corpora now —
`test_journal_prose_figures_are_DERIVED.py` for the journal package,
`testing/scripts/tests/unit/test_measurement_figures_are_cited.py` for the
phase docs that opt in, `test_candidates_prose_matches_the_table.py` for
`candidates.md`, and `test_a_prose_COUNT_of_a_collection_is_DERIVED.py`, added
alongside this correction, for prose in this directory that counts a collection
the same module defines. That last one is what holds the one figure below.

WHAT THIS GUARD DOES NOT LOOK AT:

  * **Whether the control is any GOOD.** A module containing
    `ast.parse("x = 1")` and asserting nothing satisfies it. This asks that a
    control exists, which is the part that was actually missing; whether it
    discriminates is what code review is for.
  * **Guards that read source some other way.** A module that reads files with
    `compile()`, `tokenize`, or a regex over `read_text()` and never calls
    `ast.parse` is not in the population. `ast.parse` is matched through its
    import bindings, so `import ast as _ast` is covered; `from ast import parse`
    is not. Each would need adding here, and the failure direction is that a new
    spelling escapes rather than that a good guard is blocked.
  * **A READ THAT IS NOT IN ARGUMENT POSITION, AND THIS IS THE LARGEST HOLE.**
    The match is `ast.parse(<expr>.read_text(...))` — the read inlined into the
    parse call. A module that binds the source first walks the tree just as much
    and is invisible here. Several do, each in a different shape, and they are
    NAMED RATHER THAN COUNTED so this bullet cannot rot the way the sentence
    above it did — a count here would have been wrong within the same edit,
    because writing the fourth member is what produced the fourth bullet:

      - `test_authorization_is_observed.py` assigns `src = …read_text(…)` on the
        line before the parse;
      - `test_journal_prose_figures_are_DERIVED.py` gets its sources from a dict
        comprehension of `read_text` values, so no single assignment carries it;
      - `test_journal_state_is_derived_in_one_place.py` parses a function
        PARAMETER, and the read happens at a call site in another function;
      - `test_a_prose_COUNT_of_a_collection_is_DERIVED.py`, added by the same
        correction that wrote this bullet, needs the source text for its
        comment scan and so binds it before parsing. It is named here rather
        than quietly reshaped to satisfy the recogniser, because a guard edited
        to fit a matcher is how a population stops meaning anything;
      - `test_ci_gate.py` passes the source to a named predicate
        (`_dispatches_review_ungated`) which parses it, so the parse and the read
        are in different functions. It LEFT this population by gaining exactly
        what this file asks for: the extraction that lets a literal control drive
        the predicate is the same edit that un-inlines the read. Named rather
        than re-inlined, per the sentence above — and it is the sharpest evidence
        for the redesign this bullet defers, since the recogniser now scores a
        guard lower for being controlled.

    Closing this is not a wider regex. `_parses_a_literal` decides "is a control"
    by the *same* inlining test, negated — so admitting them without redesigning
    both predicates together would mark every one CONTROLLED with no control,
    which is a permanent green and strictly worse than the hole. That
    redesign wants data flow, it is a design task rather than a correction, and
    it is stated in the PR body rather than attempted in the last minutes of a
    correction pass — the mechanism that produced this finding class four times.
    This bullet is the second arm of the rule above: not derived, and therefore
    not written as a universal.
  * **Whether a grandfathered module's debt is ever paid.** The 11 names in
    `_WITHOUT_A_CONTROL_YET` are excused from the rule, not from the class.
    Nothing here forces one of them to gain a control — only that the list
    cannot GROW and cannot go stale. A list that stops shrinking is invisible
    to this file and visible to a reader, which is the honest split.
  * **Non-AST structural guards.** Several modules in this tree assert
    properties by regex or by `Path.rglob` alone. They have the same failure
    mode and are outside this population — named so the boundary is a decision
    rather than an oversight.
"""

from __future__ import annotations

import ast
from pathlib import Path

_HERE = Path(__file__).resolve().parent

# `(walkers, of which controlled)` — MEASURED, then written here, and written
# nowhere else. One literal rather than one in the comparison and a second in
# the failure text: the message is read by exactly the person about to change
# the number, so a message that disagreed with its own assertion would mislead
# at the worst possible moment. That double-write is the class this file is
# being corrected for, so it may not appear in the correction.
# 23 -> 24 and 12 -> 13 AT THE MERGE OF #126 WITH #124, and BOTH numbers moved
# because each side contributed one census guard that already carries its own
# control: `test_a_named_observer_is_actually_WIRED` from the triage-sizes
# branch, `test_a_PARENT_forwards_what_its_CHILD_reads` from the Phase 2
# promotion. Neither side could see the other's, so each was correct at 23/12
# alone — this is the census doing exactly what it is for, at the one moment
# the two populations meet. `_WITHOUT_A_CONTROL_YET` is unchanged: no
# grandfathered guard gained a control here.
# 24 -> 26 and 13 -> 15 AT THE MERGE WITH THE TOOLING-DEFECTS BRANCH, which
# brings `test_a_task_SOURCE_path_is_anchored_to_the_repo` and
# `test_no_prompt_hands_the_model_a_MAIN_CHECKOUT_path`. BOTH numbers moved by
# two, and that is the check that they each carry a control: a guard arriving
# without one moves the first number only, and would additionally have tripped
# the unexcused-guard test, which stayed green. Verified rather than assumed —
# `_walks_the_tree` returns True for both files.
# 26 -> 27 and 15 -> 16 for `test_a_new_branch_STARTS_FROM_THE_DEFAULT_BRANCH`.
# BOTH numbers move, and the second one only after this census refused the
# guard's first control: it wrote a temp file and read it back, which still
# routes through `read_text` and so proved nothing about a predicate that had
# started answering unconditionally. The predicate is now split so a control
# can drive it on a literal, which is what this rule has always asked for.
# 29 -> 30 and 18 -> 19 for `test_a_refused_bag_mutation_CHANGES_NOTHING`, which
# arrived WITH its control because this census refused it without one. Both
# numbers move together, which is the shape a correctly-built new guard makes.
#
# 30 -> 31 AND 19 -> 20 AT THIS MERGE, and the number is DERIVED rather than
# picked. `main` and this branch each added one controlled guard while the other
# was open, so both sides raised the pin and neither side's figure is right for
# the merged tree: this branch wrote (30, 19), `main` wrote (28, 17), and the
# tree holds 31 and 20. Resolved by running the census and reading what it found,
# because a pin is a COUNT OF THE TREE and a conflict here has exactly one
# correct answer that neither parent knows.
#
# 31 -> 32 AND 20 -> 21 for `test_plan_project_loop`'s import census, which walks
# the parent's own source to hold the narrowing: `plan-project` may import
# `triage-candidates` and `review-pr` and no other child. It arrived WITHOUT a
# control, this census refused it, and the predicate was split into
# `_child_workflow_imports` so three literals could drive it — a satisfying
# shape, a violating one, and a module with no child imports at all. Both numbers
# move together, which is the shape a correctly-built new guard makes.
# 32 -> 33 AND 21 -> 22 for `test_no_loop_back_re_enters_the_AUTHOR`, which holds
# the one structural property the plan family was missing: a parent's loop-back
# re-enters its CORRECTOR, never its author. It arrived WITH its control — three
# literals driving `_loop_callees`, one of them a `while` that is not a loop-back
# and must contribute nothing — and the control earned its place immediately by
# catching the predicate collecting the loop's own TEST as a callee.
# 33 -> 35 AND 22 -> 24 for Workflow Decomposition Phase 4's two guards —
# `test_a_worktree_NAME_comes_from_the_RUN_CONTEXT` (no `worktree_add` call
# assembles the name it cuts with) and `test_dispatch_context` (the entrypoint
# sweeps behind requirements 3 and 4). BOTH numbers move by TWO, which is the
# check that each arrived WITH a control: the first ships eight positive
# spellings and six negative ones driven on literals, the second controls its
# build/echo, ordering, gating and dry-run predicates the same way. Verified
# rather than assumed — `_walks_the_tree` returns True for both files.
# 35 -> 36 when PMP Phase 2 added `test_verify_citations.py`, and the second
# number moved with it because that guard ships its control rather than being
# grandfathered: its import-closure walk asserts `source_fetch` is ABSENT from
# `verify`'s graph, and the discriminator beside it starts the same walk at
# `content_activities`, which legitimately does import the fetcher. An absence
# with no demonstrated presence is the vacuity this file exists to refuse.
_PINNED = (36, 25)


# GRANDFATHERED — walks the tree, has no literal control, PREDATES this rule.
#
# THIS LIST IS THE MEASUREMENT THAT REPLACED A FALSE SENTENCE. The recogniser
# below used to require a module-level `_ROOTS`, and this file's docstring said
# "the two spellings covered are the two the tree uses" — so a file's private
# variable name decided whether the rule applied to it, and the guard was green
# over a handful of already-compliant members while every uncontrolled one sat
# outside it. That is the permanent-green failure the docstring condemns,
# committed by the docstring's own file.
#
# NO POPULATION FIGURE IS RESTATED HERE. Those live in
# `test_the_census_matches_the_tree` and nowhere else: the previous version of
# this comment carried a second copy of "18 modules ... 2 carry `_ROOTS`", the
# copy went stale with the docstring's, and correcting one would have left the
# other.
#
# THE ONE COUNT THIS FILE DOES STATE — the docstring's count of the names in
# this list — is stated on purpose and is GATED, by
# `test_a_prose_COUNT_of_a_collection_is_DERIVED.py`, which compares a prose
# count of a collection against the collection. That is the first arm of the
# rule rather than an exception to it: a reader needs the size, and the number
# is now held by something that goes red. It went red on exactly this line
# during the correction that wrote this comment, when a name came out of the
# list below and the sentence still said the old figure.
#
# EXEMPT BY NAME, NOT BY SHAPE, AND THE LIST MAY ONLY SHRINK. Adding a control
# to one of these means deleting its line; `test_no_exemption_is_stale` fails
# when a name here stops needing the carve-out, so the debt cannot quietly
# become permanent. A guard written AFTER today gets no entry and fails.
#
# WHY GRANDFATHERING RATHER THAN FIXING THEM HERE: each needs a control written
# against a predicate its own author designed, and writing that many in the last
# minutes of a correction pass — unreviewed, by someone who did not write any of
# the predicates — is the mechanism that produced this finding in the first
# place. Enumerating the debt makes it visible and makes the NEXT guard fail;
# clearing it is real work with a real design in it, tracked at issue #103.
_WITHOUT_A_CONTROL_YET = frozenset({
    "test_a_grant_follows_its_flag.py",
    "test_convergence.py",
    "test_dry_run_previews_the_dispatched_prompt.py",
    "test_exit_record.py",
    "test_journal_containment.py",
    "test_loop_cap_prose_is_counted.py",
    "test_model_gets_the_worktree_path.py",
    "test_pr_url_address.py",
    "test_preflight.py",
    "test_run_log_emission.py",
    "test_triage_candidates_split.py",
})


def _ast_aliases(tree: ast.Module) -> set[str]:
    """The names `ast` is bound to in this module.

    SHARED BY BOTH PREDICATES, AND THAT IS THE POINT. `_walks_the_tree` resolved
    aliases and `_parses_a_literal` hard-coded `"ast"`, which made the two
    disagree about the same call. The dangerous direction was silent: a
    grandfathered module gaining a control spelled `_ast.parse("<snippet>")`
    would still read as uncontrolled, `test_no_exemption_is_stale` would never
    fire, and its carve-out would become permanent — the one outcome that test
    exists to prevent. One module in this tree already imports it that way.
    """
    aliases = {"ast"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases |= {a.asname or a.name for a in node.names if a.name == "ast"}
    return aliases


def _parse_calls(tree: ast.Module):
    """Every `<ast-alias>.parse(<arg>, …)` call's first argument."""
    aliases = _ast_aliases(tree)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "parse"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in aliases and node.args):
            yield node.args[0]


def _reads_a_file(node: ast.expr) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "read_text")


def _walks_the_tree(tree: ast.Module) -> bool:
    """Does this module parse a file it read off disk?

    RECOGNISED BY BEHAVIOUR, NOT BY A PRIVATE VARIABLE NAME. `ast.parse(
    <anything>.read_text(...))` is what a tree-walking guard DOES, and it is a
    fact the language records rather than a convention a module may or may not
    have adopted. `ast` is matched through its import bindings so an aliased
    `import ast as _ast` — which one module in this tree already uses — cannot
    walk out of the population.
    """
    return any(_reads_a_file(arg) for arg in _parse_calls(tree))


def _census_guards() -> list[tuple[str, ast.Module]]:
    """Test modules that walk the production tree, with their parsed source."""
    found = []
    for path in sorted(_HERE.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _walks_the_tree(tree) and path.name != Path(__file__).name:
            found.append((path.name, tree))
    return found


def _parses_a_literal(tree: ast.Module) -> bool:
    """Does this module ever `ast.parse` something that is not a file read?

    A control is a snippet: `ast.parse(snippet)` where `snippet` is a string
    literal or a parameter. The tree-walking call is always
    `ast.parse(path.read_text(...))`, so "the argument is not a `.read_text()`
    call" separates the two without needing to know either module's variables.

    IT SHARES `_ast_aliases` WITH `_walks_the_tree` — see that helper for why
    the two disagreeing was a silent hole rather than an inconsistency.
    """
    return any(not _reads_a_file(arg) for arg in _parse_calls(tree))


def test_the_census_matches_the_tree() -> None:
    """THE POPULATION IS DERIVED, AND THIS IS THE ONLY PLACE IT IS WRITTEN.

    A FLOOR IS WHAT LET THE FIGURE ROT, so it is gone. This used to assert
    `>= 2` and reason that "an equality would make adding one fail for the wrong
    reason" — but a floor is green over a recogniser that has silently narrowed
    AND over prose that has silently gone stale, which is both failures this
    file exists to refuse. The sibling written in the same commit
    (`test_a_bounded_reply_is_CHECKED_not_only_read.test_the_census_matches_the_tree`)
    took the equality and its figure did not rot; this one took the floor and
    its figure was wrong on arrival. The comparison is the whole argument.

    Failing here is not a defect. It is the census reporting that the population
    moved, and the fix is one number plus whatever prose quoted it.
    """
    guards = _census_guards()
    controlled = [name for name, tree in guards if _parses_a_literal(tree)]
    assert (len(guards), len(controlled)) == _PINNED, (
        f"the walk found {len(guards)} census guard(s) of which {len(controlled)} "
        f"carry a positive control; it was {_PINNED[0]} and {_PINNED[1]} when "
        f"this was pinned.\n"
        f"If you ADDED a guard: confirm it exercises its own predicate against a "
        f"literal snippet, then raise both numbers in `_PINNED`.\n"
        f"If you added a CONTROL to a grandfathered guard: only the second "
        f"number moves, and that guard's line comes out of "
        f"`_WITHOUT_A_CONTROL_YET` in the same commit — `test_no_exemption_is_"
        f"stale` will insist. That is the debt in issue #103 being paid and it "
        f"is the most likely reason you are reading this.\n"
        f"If you did none of those: the recogniser has stopped matching the "
        f"population it audits, and every assertion below is trivially true.\n"
        f"No POPULATION figure is written anywhere else in this file — that is "
        f"deliberate, and the reason `_PINNED` is the only thing to update. The "
        f"one count the docstring does state is the size of "
        f"`_WITHOUT_A_CONTROL_YET`, and "
        f"`test_a_prose_COUNT_of_a_collection_is_DERIVED.py` holds it.\n"
        f"Found: {[n for n, _ in guards]}")


def test_every_census_guard_exercises_its_predicate_on_a_literal() -> None:
    """THE RULE. A guard's walk is floored; its PREDICATE must be controlled.

    Feed the visitor a snippet the tree does not contain, and assert it gives
    the answer you expect for both a satisfying and a violating case. Without
    that, the only evidence the predicate works is that it worked on the day it
    was written against the tree as it was that day.
    """
    uncontrolled = [name for name, tree in _census_guards()
                    if not _parses_a_literal(tree)
                    and name not in _WITHOUT_A_CONTROL_YET]
    assert uncontrolled == [], (
        "these walk the production tree and never exercise their own predicate "
        "against a literal snippet, so a predicate that starts answering "
        "unconditionally passes every one of their assertions AND their vacuity "
        "floor:\n"
        + "\n".join(f"  {n}" for n in uncontrolled)
        + "\n\nAdd a parametrized control: `ast.parse(<a snippet string>)` fed "
          "to the module's own visitor, asserting the expected verdict for a "
          "satisfying case AND a violating one. Do NOT add it to "
          "`_WITHOUT_A_CONTROL_YET` — that list is closed and may only shrink.")


def test_no_exemption_is_stale() -> None:
    """THE LIST MAY ONLY SHRINK, AND THIS IS WHAT ENFORCES IT.

    A grandfather entry whose module has since gained a control, been renamed,
    or been deleted is a carve-out nobody is using and the next file to take
    that name inherits it silently. Failing here costs one deleted line; not
    failing costs a guard that looks enforced and is not.
    """
    guards = _census_guards()
    walking = {name for name, _ in guards}
    controlled = {name for name, tree in guards if _parses_a_literal(tree)}
    stale = sorted((_WITHOUT_A_CONTROL_YET - walking) | (_WITHOUT_A_CONTROL_YET & controlled))
    assert not stale, (
        f"these are grandfathered as having no positive control, and no longer "
        f"need to be — they have gained one, been renamed, or stopped walking "
        f"the tree: {stale}. Delete their lines from `_WITHOUT_A_CONTROL_YET`; "
        f"that is the list getting shorter, which is the only direction it moves."
    )


def test_the_recogniser_discriminates() -> None:
    """AND THIS FILE'S OWN CONTROL, because it is a census guard too.

    Exempting itself from its own rule is the exact shape it refuses, so the
    predicate is exercised on literals here rather than borrowed from the tree.
    """
    controlled = ast.parse(
        "import ast\n"
        "def walk(p):\n    return ast.parse(p.read_text())\n"
        "def control():\n    return ast.parse('x = 1')\n")
    walk_only = ast.parse(
        "import ast\n"
        "def walk(p):\n    return ast.parse(p.read_text(encoding='utf-8'))\n")
    aliased_control = ast.parse(
        "import ast as _ast\n"
        "def walk(p):\n    return _ast.parse(p.read_text())\n"
        "def control():\n    return _ast.parse('x = 1')\n")

    assert _parses_a_literal(controlled) is True, (
        "a module that parses a literal snippet was read as having no control")
    assert _parses_a_literal(aliased_control) is True, (
        "a control written as `_ast.parse(<snippet>)` was not seen. This is the "
        "asymmetry that used to exist between the two predicates: the walk "
        "resolved `ast` aliases and this one did not, so a GRANDFATHERED module "
        "paying its debt in the aliased spelling would never have cleared "
        "`test_no_exemption_is_stale`, and its carve-out would have become "
        "permanent in silence. One module in this tree already imports it that "
        "way")
    assert _parses_a_literal(walk_only) is False, (
        "a module that only ever parses files was read as having a control — "
        "the recogniser accepts the tree walk itself, so this whole file is a "
        "permanent pass")


def test_the_population_recogniser_discriminates() -> None:
    """THE OTHER PREDICATE, WHICH DECIDES WHO THE RULE APPLIES TO AT ALL.

    A control on `_parses_a_literal` alone was never enough: the rule can be
    perfectly enforced over the wrong population, which is exactly what this
    file did for two passes. `_ROOTS`-free and alias-imported cases are the two
    that were escaping, so both are here as literals.
    """
    plain = ast.parse(
        "import ast\n"
        "_TEMPORAL = 1\n"
        "def walk(p):\n    return ast.parse(p.read_text(encoding='utf-8'))\n")
    aliased = ast.parse(
        "import ast as _ast\n"
        "def walk(p):\n    return _ast.parse(p.read_text())\n")
    literal_only = ast.parse(
        "import ast\n"
        "def control():\n    return ast.parse('x = 1')\n")
    no_ast = ast.parse(
        "import re\n"
        "def walk(p):\n    return re.findall('x', p.read_text())\n")

    assert _walks_the_tree(plain) is True, (
        "a guard that walks the tree without a `_ROOTS` name was excluded — "
        "which is the exact defect this recogniser replaced")
    assert _walks_the_tree(aliased) is True, (
        "`import ast as _ast` walked out of the population; one module in this "
        "tree already imports it that way")
    assert _walks_the_tree(literal_only) is False, (
        "a module that only parses literals is not a census guard and must not "
        "be held to the rule")
    assert _walks_the_tree(no_ast) is False, (
        "a regex-over-source guard was admitted; it is a stated non-member and "
        "admitting it would demand an `ast.parse` control it has no use for")
