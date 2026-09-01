"""No AST guard recognises a module by its BARE NAME — swept repo-wide.

WHY THIS FILE EXISTS, AS THE MEASUREMENT RATHER THAN AS A PRINCIPLE. A guard
that matches `<module>.<function>(...)` by comparing the bare name —
`node.func.value.id == "re"` — is evaded by one import statement:

    import re as _r          ->  _r.compile(r"^x$")      invisible
    from re import compile   ->  compile(r"^x$")         invisible

The evaded call is not reported as a violation. It is ABSENT FROM THE POPULATION,
which is the direction that reads as a clean tree, and the guard stays green.

WHY THIS LIVES BESIDE `test_test_tree_hygiene.py` AND NOT IN A COMPONENT, for the
reason that file already writes down: the property is repo-wide, and the defect
it holds was found three times in three different components. A gate scoped to
one of them would have closed one spelling and left the other two.

THE FOUR OCCURRENCES, WHICH ARE THE EVIDENCE:

  * `test_a_census_guard_proves_its_own_predicate.py` — `_walks_the_tree`
    resolved `ast` aliases and `_parses_a_literal` hard-coded `"ast"`, so the two
    disagreed about the same call. A grandfathered guard paying its debt as
    `_ast.parse("<snippet>")` would have read as uncontrolled forever. Fixed at
    the site, and the fix is `_ast_aliases`.
  * `test_every_subprocess_the_fleet_launches_is_bounded.py` — `from subprocess
    import run` was promoted from unlooked-at to refused, and `import subprocess
    as sp` was found still open ONE IMPORT STATEMENT AWAY, by a reviewer. The
    identical pair on `os` then survived both passes and was found by this
    sweep.
  * `test_journal_regex_anchors.py` — a class-check written to end a recurring
    sweep-residue class, itself blind to an aliased `re`, AND its own
    compensating honesty test blind in the same way. Three mutations green
    against a 35-passing baseline. This is the finding that produced this file.
  * `test_a_gh_reply_is_checked_for_SHAPE_not_only_parsed.py` — `json.loads`
    matched by the bare name, so a `gh` reply decoded through `import json as
    _j` was not reported unguarded, it was ABSENT FROM THE CENSUS. Found by the
    sweep this file's own predicate performs, in a component none of the other
    three touch, and it is the reason the count in this heading is four.

Four independent authors, four components, one defect. Converting the sites did
not converge — the guard written to stop the class had the class. What converges
is a check that keys on the CLASS, so the next recogniser fails at the moment it
is written.

⚠ THAT HEADING SAID **THREE** WHEN IT SHIPPED, and the fourth bullet is the one
the same correction pass had already fixed two files away. A population claim
that undercounts its own diff is the exact defect this family exists to refuse,
written into the file that exists to refuse it — caught by review, recorded here
rather than quietly renumbered, because the pattern is the point.

TWO ANSWERS SATISFY THIS, and both are import-aware:

  * RESOLVE — walk the module's `import` statements and match every name it is
    bound to. Right when the module has legitimate non-matching uses (`os` is
    imported everywhere for `environ` and `path`; refusing an alias would be a
    rule about aliasing).
  * REFUSE — report the aliased or from-imported spelling as a finding in its own
    right. Right when a module is imported for exactly one reason, which is why
    `subprocess` takes this arm.

The failure is being NEITHER: comparing the bare name and never looking at an
import statement.

⚠ WHAT THIS DOES NOT COVER, because a sweep is only as good as its predicate:

  * IT SEES A STRING LITERAL COMPARED AGAINST A `.id` ATTRIBUTE. A recogniser
    that binds the name to a variable first (`want = "re"` … `node.id == want`)
    is invisible. No guard in this tree does that today, and the failure
    direction is that a new spelling escapes rather than that a good guard is
    blocked.
  * IT ASKS WHETHER THE FILE LOOKS AT IMPORTS FOR THAT MODULE AT ALL, not
    whether the resolution is correct or reaches the matcher. A file that
    resolves `re` in one function and hard-codes it in another satisfies this.
    That is the same standing `test_a_census_guard_proves_its_own_predicate`
    takes for its own controls: this asks that the question was asked.
  * IT IS A CHECK ON MODULES, NOT ON NAMES GENERALLY. `node.func.value.id ==
    "notes"` matches a local variable and aliasing does not apply; the
    membership test is `sys.stdlib_module_names`, so only importable modules are
    held to the rule.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]

# This repo's own worktrees live under `.claude/`; scanning them would count
# another branch's files as this branch's. RELATIVE parts, not absolute — an
# absolute-path match skips every file when the suite runs from inside a
# worktree, which is a scan that visits nothing and reports a clean tree. Same
# list and same reasoning as `test_test_tree_hygiene.py`.
SKIP_PARTS = {".git", ".claude", "__pycache__", "node_modules", ".venv"}

# Sites that legitimately compare a module's bare name without resolving it,
# each with the reason. Empty, and an entry added here is a claim a reader can
# check — which is the point of declaring rather than skipping. Keyed
# `"<file>:<module>"` rather than by line, so an unrelated edit above the site
# does not silently retire the exemption.
_DECLARED: dict[str, str] = {}


def _sources() -> list[Path]:
    return [
        path for path in sorted(REPO_ROOT.rglob("*.py"))
        if not SKIP_PARTS & set(path.relative_to(REPO_ROOT).parts)
    ]


def module_names_matched_in(tree: ast.Module) -> list[tuple[int, str]]:
    """`(lineno, module)` for every stdlib module compared against a `.id`.

    TAKES A PARSED TREE RATHER THAN A PATH so the recogniser can be exercised
    against a literal snippet — `test_the_recogniser_discriminates` below. A
    census guard that never drives its own predicate reports green the moment
    the predicate stops matching, which is the defect this whole family exists
    to refuse.

    Both comparison shapes, because a recogniser writes either one: `node.func.
    value.id == "re"` and `node.func.value.id in {"re", "regex"}`.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not (isinstance(node.left, ast.Attribute) and node.left.attr == "id"):
            continue
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, ast.Eq):
                literals = ([comparator.value]
                            if isinstance(comparator, ast.Constant) else [])
            elif isinstance(op, ast.In):
                # A set/tuple/list of literals. A NAME here (`in aliases`) is the
                # resolved form and contributes nothing, which is correct.
                literals = [c.value for c in ast.walk(comparator)
                            if isinstance(c, ast.Constant)]
            else:
                continue
            found += [(node.lineno, lit) for lit in literals
                      if isinstance(lit, str) and lit in sys.stdlib_module_names]
    return found


def resolves_imports_of(tree: ast.Module, module: str) -> bool:
    """Does this file look at `import` statements for `module`?

    RECOGNISED BY BEHAVIOUR, NOT BY A HELPER'S NAME. Every import-aware guard in
    this tree — whether it RESOLVES or REFUSES — reaches the same two attributes
    to do it: `alias.name` on an `ast.Import`, `node.module` on an
    `ast.ImportFrom`. That is a fact the language records, rather than a
    convention a file may or may not have adopted, and it is the same argument
    `_walks_the_tree` makes for recognising a census guard by what it does.
    """
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Compare)
                and isinstance(node.left, ast.Attribute)
                and node.left.attr in {"name", "module"}):
            continue
        for comparator in node.comparators:
            if any(isinstance(c, ast.Constant) and c.value == module
                   for c in ast.walk(comparator)):
                return True
    return False


def _findings() -> list[tuple[str, int, str]]:
    """`(relative-path, lineno, module)` for every bare-name match with no resolution."""
    out: list[tuple[str, int, str]] = []
    for path in _sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = str(path.relative_to(REPO_ROOT))
        for lineno, module in sorted(set(module_names_matched_in(tree))):
            if resolves_imports_of(tree, module):
                continue
            if f"{path.name}:{module}" in _DECLARED:
                continue
            out.append((rel, lineno, module))
    return out


def test_the_sweep_reads_the_tree() -> None:
    """A SCAN THAT VISITS NOTHING REPORTS A CLEAN TREE.

    `SKIP_PARTS` and `REPO_ROOT` are the two ways this file goes silently blind:
    a wrong `parents[N]` roots it in the wrong directory and an over-broad skip
    empties the walk. Both look identical to a repo with no defect in it.

    A FLOOR RATHER THAN AN EQUALITY, and rather than a snapshot count in the
    message. The population is "every Python file in the repository", which
    moves on ordinary commits — an equality would go red as noise and a
    remembered figure would rot, which is the defect this whole family is about.
    What the floor has to separate is "reading the tree" from "reading nothing",
    and any number far below the tree and far above zero does that.
    """
    sources = _sources()
    assert len(sources) >= 100, (
        f"the walk found {len(sources)} Python file(s) under {REPO_ROOT}, which "
        f"is not a repository — check `REPO_ROOT`'s `parents[N]` and "
        f"`SKIP_PARTS`. Both fail this way silently, and a walk that visits "
        f"nothing is the same colour as a tree with no defect in it")


def test_no_guard_matches_a_MODULE_by_its_bare_name() -> None:
    """THE RULE. A recogniser keyed on a bare module name is evaded by an alias."""
    findings = _findings()
    assert findings == [], (
        "these compare a module's BARE NAME against an AST node's `.id` and "
        "never look at an import statement for it, so `import <mod> as X` and "
        "`from <mod> import <fn>` walk straight past the check — and the evaded "
        "call is ABSENT from the guard's population rather than reported by it, "
        "which is the colour of a clean tree:\n"
        + "\n".join(f"  {rel}:{lineno} -> {module!r}"
                    for rel, lineno, module in findings)
        + "\n\nEither RESOLVE the module through its bindings (collect "
          "`a.asname or a.name` from every `ast.Import` of it, and the names "
          "bound by `ast.ImportFrom`, then match `.id in <that set>`) or REFUSE "
          "the aliased and from-imported spellings as findings in their own "
          "right. Pick refusal only when the module is imported for exactly one "
          "reason — `subprocess` is, `os` is not. If the literal is not a module "
          "at all, add it to `_DECLARED` in "
          f"{Path(__file__).name} with the reason.")


@pytest.mark.parametrize(
    ("snippet", "expected", "why"),
    [
        pytest.param('n.func.value.id == "re"', [(1, "re")],
                     "the equality spelling, which is what all three occurrences "
                     "were written as", id="eq"),
        pytest.param('n.func.value.id in {"re", "json"}', [(1, "re"), (1, "json")],
                     "a set of literals is the same defect written wider",
                     id="in-set"),
        pytest.param('n.func.value.id in aliases', [],
                     "the RESOLVED form — a name, not a literal, and the shape "
                     "this rule asks for", id="in-name"),
        pytest.param('n.func.value.id == "notes"', [],
                     "a local variable that is not an importable module; "
                     "aliasing does not apply and flagging it would invent a "
                     "finding", id="not-a-module"),
        pytest.param('n.func.attr == "compile"', [],
                     "a FUNCTION name, which no import can rebind out from "
                     "under the matcher", id="attr-not-id"),
        pytest.param('alias.name == "re"', [],
                     "the resolution itself — comparing against an import's own "
                     "name, not against a node's `.id`", id="import-side"),
    ],
)
def test_the_recogniser_discriminates(
        snippet: str, expected: list[tuple[int, str]], why: str) -> None:
    """WOULD THIS TEST FAIL IF THE PROPERTY WERE VIOLATED? Asked of the guard itself.

    Both directions, because the failures are asymmetric: a recogniser that
    stops matching empties the population and every assertion above goes
    permanently green, while one that matches any string turns every local
    variable named `time` or `code` into a finding and gets answered with a
    `_DECLARED` entry — which is how a sweep accumulates suppressions and stops
    being read.
    """
    assert sorted(module_names_matched_in(ast.parse(snippet))) == sorted(expected), why


@pytest.mark.parametrize(
    ("snippet", "module", "expected", "why"),
    [
        pytest.param('for a in n.names:\n    if a.name == "re":\n        pass',
                     "re", True, "`import re as X` walked via `alias.name`",
                     id="import-alias"),
        pytest.param('if n.module == "subprocess":\n    pass',
                     "subprocess", True,
                     "`from subprocess import run` walked via `node.module` — "
                     "the REFUSE arm, which counts", id="import-from"),
        pytest.param('for a in n.names:\n    if a.name == "re":\n        pass',
                     "json", False,
                     "resolving a DIFFERENT module is not resolving this one, "
                     "and reading it as one would excuse every file that "
                     "resolves anything", id="wrong-module"),
        pytest.param('x = 1', "re", False, "a file that looks at no imports",
                     id="no-imports"),
    ],
)
def test_the_resolution_recogniser_discriminates(
        snippet: str, module: str, expected: bool, why: str) -> None:
    """THE OTHER PREDICATE, WHICH DECIDES WHO IS ALREADY COMPLIANT.

    A control on the matcher alone was never enough: the rule can be perfectly
    enforced and then excused for everyone by a resolution check that answers
    True unconditionally. That is the permanent green this family exists to
    refuse, and it is the exact shape `_parses_a_literal` shipped with.
    """
    assert resolves_imports_of(ast.parse(snippet), module) is expected, why
