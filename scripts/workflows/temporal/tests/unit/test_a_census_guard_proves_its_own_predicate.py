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
production tree — spelled here as owning a module-level `_ROOTS` and calling
`ast.parse`. That is the population. Each one must ALSO exercise its predicate
against at least one literal source snippet, i.e. build its own visitor over an
`ast.parse` of a string rather than of a file.

WHAT THIS GUARD DOES NOT LOOK AT:

  * **Whether the control is any GOOD.** A module containing
    `ast.parse("x = 1")` and asserting nothing satisfies it. This asks that a
    control exists, which is the part that was actually missing; whether it
    discriminates is what code review is for.
  * **Census guards spelled some other way.** A module that walks the tree
    without a `_ROOTS` name, or that reads files with `compile()` instead of
    `ast.parse`, is not in the population. The two spellings covered are the
    two the tree uses; a third would need adding here, and the failure
    direction is that a new guard escapes rather than that a good one is
    blocked.
  * **Non-AST structural guards.** Several modules in this tree assert
    properties by regex or by `Path.rglob` alone. They have the same failure
    mode and are outside this population — named so the boundary is a decision
    rather than an oversight.
"""

from __future__ import annotations

import ast
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _census_guards() -> list[tuple[str, ast.Module]]:
    """Test modules that walk the production tree, with their parsed source."""
    found = []
    for path in sorted(_HERE.glob("test_*.py")):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        walks = any(
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "_ROOTS" for t in n.targets)
            for n in tree.body
        ) and "ast.parse" in src
        if walks and path.name != Path(__file__).name:
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
                    if not _parses_a_literal(tree)]
    assert uncontrolled == [], (
        "these walk the production tree and never exercise their own predicate "
        "against a literal snippet, so a predicate that starts answering "
        "unconditionally passes every one of their assertions AND their vacuity "
        "floor:\n"
        + "\n".join(f"  {n}" for n in uncontrolled)
        + "\n\nAdd a parametrized control: `ast.parse(<a snippet string>)` fed "
          "to the module's own visitor, asserting the expected verdict for a "
          "satisfying case AND a violating one.")


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
