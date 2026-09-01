"""An operator-named target that is not there is USAGE — swept over both tools.

WHY THIS FILE EXISTS, AS THE MEASUREMENT RATHER THAN AS A PRINCIPLE. Phase 2 hit
this defect twice, in the same shape, one review pass apart:

  * `verify.main` short-circuited to `EXIT_USAGE` on any structural finding, so
    a citation record that could not be read exited with the number documented
    as "you invoked this wrongly". Fixed by splitting `EXIT_STRUCTURAL` out.
  * `validate.main` did the mirror image and was left standing by that fix:
    `if (target / BAGIT_FILE).is_file() or not target.is_dir()` routed a path
    that is not there INTO `validate_bag`, so a mistyped argument printed a full
    `result: FAIL` report — asserting `lifecycle`, `redacted`, `incomplete` and a
    payload size about a bag that does not exist — and exited 1, the code that
    means a bag's bytes did not match its manifest.

The second was found by a reviewer sweeping OUTWARD from the diff into the
sibling nobody edited, and the pass that fixed the first had the two `main()`
bodies open side by side while rejecting an unrelated finding about them. So the
lesson is not "check the sibling": it is that a rule applied by hand to one
`main()` is a rule nothing holds. This sweep DERIVES the population and applies
the rule to each member, so a third bag-inspection tool inherits it on the day it
is written rather than on the day someone mistypes a path at it.

THE POPULATION IS DERIVED, NOT LISTED. It is every non-kickoff entrypoint under
`scripts/` that imports `modules.journal.validate` or `modules.journal.verify` —
which is what "a tool that inspects a bag an operator names" means in this tree.
A tool added later joins the sweep by importing the checker it wraps, which it
must do to be one.

⚠ WHAT THIS DOES NOT COVER, because a sweep is only as good as its predicate:

  * IT DOES NOT REACH `validate_bag()` OR `verify_bag()`. Those deliberately
    RETURN a structural report for a path that is not a directory, because a
    programmatic sweep over a journal wants a report per bag rather than an
    exception on the first bad one. The split is between what a library returns
    and what an operator is told, and only the second half is asserted here.
  * IT ASSERTS THE CODE AND THE SILENCE, NOT THE WORDING. A tool that exits 2
    and prints nothing to stdout passes even if its stderr message is unhelpful.
  * IT SEES A TARGET THAT DOES NOT EXIST. A target that exists and is the wrong
    KIND of thing — a regular file, a directory holding no bags — is a separate
    question each tool answers in its own docstring.
"""

from __future__ import annotations

import ast
import importlib
import pathlib
import sys
from pathlib import Path

import pytest

from modules.journal.bag import open_bag

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
TEMPORAL = REPO_ROOT / "scripts" / "workflows" / "temporal"
ENTRYPOINTS_DIR = TEMPORAL / "scripts"

_CHECKER_MODULES = ("modules.journal.validate", "modules.journal.verify")

# The code every member of this population must return for a target that is not
# there. It is spelled once so that a tool answering "2" for a coincidental
# reason and a tool answering it for this reason are the same assertion.
EXIT_USAGE = 2


def imports_a_bag_checker(tree: ast.Module) -> bool:
    """True when this module's parsed source wraps `validate` or `verify`.

    AST rather than a substring search: a filename mentioned in a docstring or a
    usage string is not an import, and this predicate's whole job is to be a
    statement about what the module DOES.

    TAKES A PARSED TREE RATHER THAN A PATH so the predicate can be exercised
    against a literal snippet — see `test_the_predicate_answers_correctly_on_a_
    LITERAL` below. A recogniser whose only evidence is that it worked against
    the tree on the day it was written is the failure
    `test_a_census_guard_proves_its_own_predicate.py` exists to refuse.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module in _CHECKER_MODULES:
                return True
            if node.module == "modules.journal":
                if any(alias.name in ("validate", "verify") for alias in node.names):
                    return True
        elif isinstance(node, ast.Import):
            if any(alias.name in _CHECKER_MODULES for alias in node.names):
                return True
    return False


def bag_inspection_entrypoints() -> list[Path]:
    return sorted(p for p in ENTRYPOINTS_DIR.glob("*.py")
                  if not p.name.startswith("run_")
                  and imports_a_bag_checker(ast.parse(p.read_text(encoding="utf-8"))))


def test_the_predicate_finds_something_at_all() -> None:
    """A sweep whose population silently emptied is green and asserts nothing.

    This is the failure `test_a_census_guard_proves_its_own_predicate` exists for,
    stated here because a rename under `scripts/` would take the whole sweep out
    without turning a single case red.
    """
    found = bag_inspection_entrypoints()
    assert found, (
        f"no entrypoint under {ENTRYPOINTS_DIR} imports {' or '.join(_CHECKER_MODULES)}; "
        "either the tools moved or the predicate went blind")


def test_the_predicate_answers_correctly_on_a_LITERAL() -> None:
    """The recogniser, exercised on snippets the tree does not contain.

    Both directions, because a predicate that answers `True` unconditionally
    passes the population check above and every case below it.
    """
    assert imports_a_bag_checker(ast.parse("from modules.journal import validate"))
    assert imports_a_bag_checker(ast.parse("from modules.journal import verify as v"))
    assert imports_a_bag_checker(ast.parse("from modules.journal.verify import main"))
    assert imports_a_bag_checker(ast.parse("import modules.journal.validate"))

    # A filename in prose or in a usage string is not an import, and a sibling
    # module of the checkers is not a checker.
    assert not imports_a_bag_checker(ast.parse('"""runs validate_bag.py"""'))
    assert not imports_a_bag_checker(ast.parse('USAGE = "modules.journal.verify"'))
    assert not imports_a_bag_checker(ast.parse("from modules.journal import bag"))
    assert not imports_a_bag_checker(
        ast.parse("from modules.journal.root import resolve_journal_root"))


@pytest.mark.parametrize("entrypoint", bag_inspection_entrypoints(),
                         ids=lambda p: p.name)
def test_a_target_that_is_not_there_is_usage_and_prints_no_report(
        entrypoint: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Exit 2, and nothing on stdout that could be read as a verdict about a bag.

    The silence is half the property. An exit code nobody looks at is repaired by
    a report that says `result: FAIL` next to a path the operator mistyped.
    """
    if str(ENTRYPOINTS_DIR) not in sys.path:
        sys.path.insert(0, str(ENTRYPOINTS_DIR))
    module = importlib.import_module(entrypoint.stem)

    code = module.main([str(tmp_path / "no-such-target")])
    captured = capsys.readouterr()

    assert code == EXIT_USAGE, (
        f"{entrypoint.name} answered {code} for a target that is not there; "
        f"{EXIT_USAGE} is usage and every other code this tool returns is a "
        "statement about a bag that exists")
    assert captured.out == "", (
        f"{entrypoint.name} printed a report for a target that is not there:\n"
        f"{captured.out}")


@pytest.mark.parametrize("entrypoint", bag_inspection_entrypoints(),
                         ids=lambda p: p.name)
def test_a_bad_target_suppresses_the_report_for_a_good_one_beside_it(
        entrypoint: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A usage error is answered ALONE, even when an earlier target was fine.

    THE BEHAVIOUR IS DELIBERATE AND IT IS PINNED HERE BECAUSE IT IS SURPRISING.
    Both tools return at the bad target rather than finishing the list, so a
    valid earlier target's report is computed and never printed. The alternative
    — print what succeeded, then the usage error — puts a `result: PASS` block
    directly above a message saying the operator named something that is not
    there, which is the same confusion between "a verdict about a bag" and "a
    problem with your invocation" that the exit-code split exists to end.

    It is asserted for the POPULATION rather than for one tool, so a third
    bag-inspection tool cannot answer this question differently by accident.

    ⚠ THE FIRST TARGET IS A REAL SEALED BAG AND THAT IS THE WHOLE TEST. The
    first draft of this case used an empty directory, which both tools already
    answer with 2 ("no bags under …") BEFORE they ever look at the second
    argument — so it passed without the second argument existing and proved
    nothing. Checked by running the empty directory alone; it returned 2 by
    itself. A bag is the only first target that reaches the report-printing
    path.
    """
    if str(ENTRYPOINTS_DIR) not in sys.path:
        sys.path.insert(0, str(ENTRYPOINTS_DIR))
    module = importlib.import_module(entrypoint.stem)

    root = tmp_path / "journal"
    root.mkdir()
    good = open_bag(root, "good").path

    code = module.main([str(good), str(tmp_path / "no-such-target")])
    assert code == EXIT_USAGE
    assert capsys.readouterr().out == "", (
        f"{entrypoint.name} printed a report before answering a usage error; a "
        "verdict about a bag and a problem with the invocation must not appear "
        "together")
