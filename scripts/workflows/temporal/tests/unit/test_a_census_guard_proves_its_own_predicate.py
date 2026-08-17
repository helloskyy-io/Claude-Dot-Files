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
Measured: **18** modules here walk the production tree; **2** carry `_ROOTS`,
and both were written by the pass that wrote this file. The other 16 spell it
`_TEMPORAL`, `_SCRIPTS`, `_RUNNERS`, `FLEET`, or a bare local — so whether the
rule applied to a guard was decided by its author's choice of variable name, and
12 uncontrolled guards sat outside a check that was green. The file condemning
permanent greens was one. Keying on the BEHAVIOUR is the fix, because a module
cannot walk the tree without doing the thing being matched; the 12 are
grandfathered by name in a list that may only shrink.

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
  * **Whether a grandfathered module's debt is ever paid.** The 12 names in
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


# GRANDFATHERED — walks the tree, has no literal control, PREDATES this rule.
#
# THIS LIST IS THE MEASUREMENT THAT REPLACED A FALSE SENTENCE. The recogniser
# below used to require a module-level `_ROOTS`, and this file's docstring said
# "the two spellings covered are the two the tree uses". Measured: 18 modules
# under `tests/unit/` walk the production tree and 2 carry `_ROOTS` — the two
# written by the same pass as this guard. The other 16 spell their roots
# `_TEMPORAL`, `_SCRIPTS`, `_RUNNERS`, `FLEET`, or a bare local, so a file's
# private variable name decided whether the rule applied to it. The guard was
# green over a population of two already-compliant members while 12 uncontrolled
# ones sat outside it, which is the permanent-green failure its own docstring
# condemns, committed by the docstring's own file.
#
# EXEMPT BY NAME, NOT BY SHAPE, AND THE LIST MAY ONLY SHRINK. Adding a control
# to one of these means deleting its line; `test_no_exemption_is_stale` fails
# when a name here stops needing the carve-out, so the debt cannot quietly
# become permanent. A guard written AFTER today gets no entry and fails.
#
# WHY GRANDFATHERING RATHER THAN FIXING ALL 12 HERE: each needs a control
# written against a predicate its own author designed, and writing 12 of those
# in the last minutes of a correction pass — unreviewed, by someone who did not
# write any of the predicates — is the mechanism that produced this finding in
# the first place. Enumerating the debt makes it visible and makes the NEXT
# guard fail; clearing it is real work with a real design in it.
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
    "test_the_suite_never_writes_to_the_operators_journal.py",
    "test_triage_candidates_split.py",
})


def _walks_the_tree(tree: ast.Module) -> bool:
    """Does this module parse a file it read off disk?

    RECOGNISED BY BEHAVIOUR, NOT BY A PRIVATE VARIABLE NAME. `ast.parse(
    <anything>.read_text(...))` is what a tree-walking guard DOES, and it is a
    fact the language records rather than a convention a module may or may not
    have adopted. `ast` is matched through its import bindings so an aliased
    `import ast as _ast` — which one module in this tree already uses — cannot
    walk out of the population.
    """
    aliases = {"ast"}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            aliases |= {a.asname or a.name for a in n.names if a.name == "ast"}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "parse"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in aliases and node.args):
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) \
                and arg.func.attr == "read_text":
            return True
    return False


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
    """
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "parse"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "ast"):
            continue
        if not node.args:
            continue
        arg = node.args[0]
        reads_a_file = (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute)
                        and arg.func.attr == "read_text")
        if not reads_a_file:
            return True
    return False


def test_the_population_is_not_vacuous() -> None:
    """TWO CENSUS GUARDS EXIST. If this finds none, the rule below is decoration.

    A floor rather than an equality: more of these are expected and welcome, and
    an equality would make adding one fail for the wrong reason.
    """
    guards = _census_guards()
    assert len(guards) >= 2, (
        f"found {len(guards)} census guard(s) under {_HERE.name}/ — there were 2 "
        f"when this was written, so the recogniser has stopped matching the "
        f"population it audits and every assertion below is trivially true. "
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
    walking = {name for name, _ in _census_guards()}
    controlled = {name for name, tree in _census_guards() if _parses_a_literal(tree)}
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

    assert _parses_a_literal(controlled) is True, (
        "a module that parses a literal snippet was read as having no control")
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
