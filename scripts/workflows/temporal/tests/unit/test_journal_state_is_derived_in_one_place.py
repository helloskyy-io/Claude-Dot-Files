"""The three state fields have ONE derivation — swept, not remembered.

WHY THIS FILE EXISTS, AS THE MEASUREMENT RATHER THAN AS A PRINCIPLE. Requirement
8 says a bag's state is `lifecycle: open|sealed` plus two independent flags, and
that a reader is always told all three. Two readers derived them independently:

  * `Bag.lifecycle` and `validate_bag` each turned "does `manifest-sha256.txt`
    exist" into the string `sealed`;
  * `Bag.redacted`/`Bag.incomplete` and `validate_bag` each turned a
    `bag-info.txt` label into a flag, down to an independently retyped
    `.strip().lower() == "true"`.

Both copies were correct the day they were written, which is precisely why the
defect survived four review passes: nothing is wrong until one side is edited.
**When they drift, `Bag.incomplete` disagrees with `BagReport.incomplete` about
the same bag** — the state collapse requirement 8 exists to forbid, arriving by
drift instead of by design. The trigger was named as "Phase 3 adds the third
reader", and a third hand-written copy is exactly how this package's containment
rule acquired its hole (see `test_journal_containment.py`, four instances of one
shape found one per review pass).

SO THE CHECK KEYS ON THE CLASS, NOT ON THE TWO INSTANCES. Enumerating readers
does not converge — the next reader is the one nobody enumerated. What converges
is a sweep that fails when a state field is derived anywhere except the one
function that owns the rule. This is the same mechanism the package already uses
twice: `test_every_parent_opens_a_run_bag.py` for bag-open and
`test_journal_containment.py` for path containment.

TWO SWEEPS, BECAUSE THERE ARE TWO DERIVATIONS:

  * **A label becoming a flag** — any comparison against a lifecycle label. A
    writer PASSES a label (`_append_tag_line(path, LABEL_GAP, …)`); only a reader
    COMPARES one, so comparison is the precise signature of derivation and the
    predicate does not have to ban the constants outright.
  * **A lifecycle string being produced** — the literals `open`/`sealed` in a
    value position. Comparing against them (`if bag.lifecycle == "sealed"`) is
    CONSUMPTION of an already-derived value and stays legal; assigning,
    returning, or branching one into existence is derivation.

⚠ WHAT THIS DOES NOT COVER, because a sweep is only as good as its predicate:

  * IT SWEEPS THE JOURNAL PACKAGE PLUS EVERY NON-TEST MODULE THAT IMPORTS IT,
    computed rather than listed — so Phase 3's emitters are in scope the moment
    they import the package, and a reader that reaches a bag without importing
    the package is invisible. The scope is printed in the failure message.
  * IT SEES A DERIVATION IN PYTHON, not one in a shell script or a jq filter
    reading `bag-info.txt` directly.
  * IT PROVES THE RULE IS DERIVED IN ONE PLACE, NOT THAT THE RULE IS RIGHT. The
    battery in the second half is what tests the derivation itself, including
    that the two shipped readers actually agree across the whole state matrix.
"""

from __future__ import annotations

import ast
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
TEMPORAL = REPO_ROOT / "scripts" / "workflows" / "temporal"
PACKAGE = TEMPORAL / "modules" / "journal"

sys.path.insert(0, str(TEMPORAL))

from modules.journal import bag as bagmod                        # noqa: E402
from modules.journal.bag import (BagState, bag_state, lifecycle_of,  # noqa: E402
                                 open_bag)
from modules.journal.validate import validate_bag                # noqa: E402

# The labels that produce a STATE FIELD. `LABEL_SCHEMA_VERSION` is deliberately
# absent: `validate_bag` compares it to report a structural problem, which is not
# one of the three fields and is derived nowhere else. A guard that swept it too
# would be banning a comparison that has no second copy to drift from.
_STATE_LABELS = {"LABEL_REDACTION", "LABEL_INCOMPLETE", "LABEL_GAP",
                 "LABEL_SEALED_AT"}

# The two lifecycle values. Named here as data rather than reached for as
# literals, so this file does not become the third copy of the thing it guards.
_LIFECYCLE_VALUES = {"open", "sealed"}

# The one function permitted to turn labels into flags, and the one permitted to
# produce a lifecycle string. Both live in `bag.py`; a second name here would be
# this guard licensing the defect it exists to catch.
_LABEL_DERIVER = ("bag.py", "bag_state")
_LIFECYCLE_DERIVER = ("bag.py", "lifecycle_of")


def _swept_modules() -> list[pathlib.Path]:
    """The journal package, plus every non-test module that imports it.

    COMPUTED, NOT LISTED. A hard-coded file list is a second enumeration of the
    thing this file argues cannot be enumerated — it would have to be edited by
    the same author who adds the reader it is supposed to catch.
    """
    package = [p for p in PACKAGE.glob("*.py") if "__pycache__" not in p.parts]
    importers = []
    for path in TEMPORAL.rglob("*.py"):
        if "__pycache__" in path.parts or "tests" in path.parts:
            continue
        if path.is_relative_to(PACKAGE):
            continue
        text = path.read_text(encoding="utf-8")
        if "modules.journal" in text or "from .journal" in text:
            importers.append(path)
    return sorted(package + importers)


def _functions_by_node(tree: ast.AST) -> dict[ast.AST, str]:
    """Every node mapped to the name of the function it sits inside (or `""`).

    Innermost wins, which matters for a comprehension inside a nested helper.
    """
    owner: dict[ast.AST, str] = {}

    def walk(node: ast.AST, current: str) -> None:
        for child in ast.iter_child_nodes(node):
            name = child.name if isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef)) else current
            owner[child] = name
            walk(child, name)

    owner[tree] = ""
    walk(tree, "")
    return owner


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)}


def _is_state_label(node: ast.AST) -> bool:
    """`LABEL_INCOMPLETE` or `anything.LABEL_INCOMPLETE`.

    Both spellings, because `bag.py` uses the bare name and `validate.py` reaches
    it as `bagmod.LABEL_INCOMPLETE` — and the ONE that was checked in review was
    the bare one.
    """
    if isinstance(node, ast.Name):
        return node.id in _STATE_LABELS
    if isinstance(node, ast.Attribute):
        return node.attr in _STATE_LABELS
    return False


def find_label_derivations(source: str, filename: str) -> list[tuple[str, int, str]]:
    """`(filename, lineno, source)` for every comparison against a state label."""
    tree = ast.parse(source, filename=filename)
    owner = _functions_by_node(tree)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not any(_is_state_label(operand)
                   for operand in [node.left, *node.comparators]):
            continue
        if (filename, owner.get(node, "")) == _LABEL_DERIVER:
            continue
        found.append((filename, node.lineno, ast.unparse(node)))
    return found


def find_lifecycle_derivations(source: str, filename: str) -> list[tuple[str, int, str]]:
    """`(filename, lineno, source)` for every lifecycle literal in a VALUE position.

    A literal that is an operand of a comparison is consumption — asking whether
    an already-derived value is `sealed` — and is left alone. Anything else
    brings one of the two lifecycle values into existence.

    Docstrings and prose cannot reach here: the match is exact equality against
    the two values, and no docstring is the single word `open`.
    """
    tree = ast.parse(source, filename=filename)
    owner = _functions_by_node(tree)
    parent = _parents(tree)
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and node.value in _LIFECYCLE_VALUES):
            continue
        if isinstance(node.value, bool):        # `True in {"open"}` is False, but be explicit
            continue
        if isinstance(parent.get(node), ast.Compare):
            continue
        if (filename, owner.get(node, "")) == _LIFECYCLE_DERIVER:
            continue
        found.append((filename, node.lineno, ast.unparse(node)))
    return found


def _scope_note() -> str:
    swept = ", ".join(sorted(p.name for p in _swept_modules()))
    return (f"\n\nSCOPE: this sweep reads the journal package plus every non-test "
            f"module that imports it — currently: {swept}. A derivation outside "
            f"that set is INVISIBLE here; if you are adding a reader elsewhere, "
            f"widen `_swept_modules` rather than working around this.")


# --- the sweep ----------------------------------------------------------------------

def test_no_module_turns_a_bag_info_LABEL_into_a_flag_except_bag_state() -> None:
    """THE REQUIREMENT. A second copy of the label rule goes red rather than shipping."""
    offenders = [hit for path in _swept_modules()
                 for hit in find_label_derivations(
                     path.read_text(encoding="utf-8"), path.name)]
    assert not offenders, (
        "a bag-info label is being compared outside "
        f"{_LABEL_DERIVER[1]}(), which means a state flag is derived twice:\n"
        + "\n".join(f"  {name}:{line}  {src}" for name, line, src in offenders)
        + "\n\nCall `bag.bag_state(...)` and read the field off it. The rule this "
          "guards is that `Bag.incomplete` and `BagReport.incomplete` cannot "
          "disagree about one bag — which is requirement 8's collapse, arriving "
          "by drift." + _scope_note())


def test_no_module_produces_a_lifecycle_VALUE_except_lifecycle_of() -> None:
    """The other half: `sealed` is minted in one place, compared anywhere."""
    offenders = [hit for path in _swept_modules()
                 for hit in find_lifecycle_derivations(
                     path.read_text(encoding="utf-8"), path.name)]
    assert not offenders, (
        f"a lifecycle value is produced outside {_LIFECYCLE_DERIVER[1]}():\n"
        + "\n".join(f"  {name}:{line}  {src}" for name, line, src in offenders)
        + "\n\nComparing against `bag.lifecycle` is fine; deciding what the "
          "lifecycle IS belongs to one function." + _scope_note())


# --- the sweep's own negative controls -----------------------------------------------
#
# A guard that has never been shown to fail is a guard nobody has tested. These
# run the two predicates over synthetic sources holding exactly the defect that
# shipped, so the sweep is proven to DISCRIMINATE rather than merely to pass.

_RETYPED_FLAG = '''
from .bag import LABEL_INCOMPLETE

def some_new_reader(entries):
    return any(label == LABEL_INCOMPLETE and value.strip().lower() == "true"
               for label, value in entries)
'''

_RETYPED_FLAG_QUALIFIED = '''
from . import bag as bagmod

def some_new_reader(entries):
    return any(label == bagmod.LABEL_REDACTION for label, _ in entries)
'''

_RETYPED_LIFECYCLE = '''
def some_new_reader(bag_path):
    return "sealed" if (bag_path / "manifest-sha256.txt").is_file() else "open"
'''

_LEGITIMATE_CONSUMPTION = '''
def a_caller(bag):
    if bag.lifecycle == "sealed":
        bag.seal()
    return bag.state.incomplete
'''


@pytest.mark.parametrize("source", [_RETYPED_FLAG, _RETYPED_FLAG_QUALIFIED])
def test_the_label_sweep_CATCHES_a_retyped_flag_rule(source: str) -> None:
    """Both spellings — the bare name and the module-qualified one."""
    assert find_label_derivations(source, "some_new_module.py")


def test_the_lifecycle_sweep_CATCHES_a_retyped_lifecycle_rule() -> None:
    assert find_lifecycle_derivations(_RETYPED_LIFECYCLE, "some_new_module.py")


def test_neither_sweep_fires_on_legitimate_CONSUMPTION() -> None:
    """The predicate has to leave `== "sealed"` alone or every caller is an offender.

    This is the half that keeps the guard usable: a check that fires on reading a
    derived value would be turned off within a week.
    """
    assert not find_label_derivations(_LEGITIMATE_CONSUMPTION, "a_caller.py")
    assert not find_lifecycle_derivations(_LEGITIMATE_CONSUMPTION, "a_caller.py")


def test_the_swept_set_actually_contains_the_two_readers_that_drifted() -> None:
    """A sweep over an empty or wrong set passes vacuously, which reads as green.

    `validate.py` is here because it IMPORTS the package, not because anyone
    listed it — that is the property that makes Phase 3's emitters in scope.
    """
    swept = {p.name for p in _swept_modules()}
    assert {"bag.py", "validate.py"} <= swept, swept
    assert "run_build.py" in swept, (
        "an entrypoint that opens a bag is no longer being swept, so the "
        f"importer discovery has stopped working: {sorted(swept)}")


# --- the battery: the derivation itself, and that both readers agree ------------------

def _bag_in_state(root, run_id: str, *, sealed: bool, redacted: bool,
                  incomplete: bool):
    """One bag driven into an arbitrary corner of the state matrix."""
    bag = open_bag(root, run_id)
    writer = bag.writer_dir("child")
    (writer / "note.txt").write_text("payload", encoding="utf-8")
    if sealed:
        bag.seal()
    if redacted:
        rel = (writer / "note.txt").relative_to(bag.path).as_posix()
        bag.redact(rel, reason="a credential landed in a transcript")
    if incomplete:
        bag.mark_incomplete("the comment body", "disk full")
    return bag


@pytest.mark.parametrize("sealed", [False, True])
@pytest.mark.parametrize("redacted", [False, True])
@pytest.mark.parametrize("incomplete", [False, True])
def test_the_bag_and_the_validator_NEVER_disagree_about_one_bag(
        tmp_path, sealed: bool, redacted: bool, incomplete: bool) -> None:
    """THE CONSEQUENCE THE SWEEP EXISTS TO PREVENT, asserted behaviourally.

    Eight combinations including `sealed` + `redacted` + `incomplete` together,
    which the phase doc's checklist names explicitly. The sweep is structural and
    could in principle pass over two functions that both call `bag_state` and
    then disagree anyway; this is the half that would catch that.

    ⚠ `redact()` on an OPEN bag is legal and leaves it open — a redaction is
    permitted whenever the payload file exists, and only a SEALED bag regenerates
    a manifest. So the four open+redacted rows assert exactly that, rather than
    being skipped as impossible.
    """
    bag = _bag_in_state(tmp_path, "run-1", sealed=sealed, redacted=redacted,
                        incomplete=incomplete)
    report = validate_bag(bag.path)

    assert (bag.lifecycle, bag.redacted, bag.incomplete) == \
           (report.lifecycle, report.redacted, report.incomplete)
    assert bag.state.redactions == report.redactions
    assert bag.state.gaps == report.gaps
    assert (bag.lifecycle, bag.redacted, bag.incomplete) == \
           (lifecycle_of(sealed), redacted, incomplete)


def test_bag_state_is_TOTAL_over_a_malformed_incomplete_value() -> None:
    """An unparseable flag value leaves the flag false rather than raising.

    Documented in `bag_state` as a decision, so it is asserted rather than left
    as a property of whatever the implementation happened to do. The gap records
    still carry what was lost, so nothing is hidden by the answer.
    """
    state = bag_state(manifest_exists=False, info_entries=[
        (bagmod.LABEL_INCOMPLETE, "perhaps"),
        (bagmod.LABEL_GAP, "the PR body — disk full"),
    ])
    assert state == BagState(lifecycle="open", redacted=False, incomplete=False,
                             redactions=(), gaps=("the PR body — disk full",))


@pytest.mark.parametrize("value", ["true", "TRUE", " True "])
def test_bag_state_forgives_case_and_space_on_the_flag(value: str) -> None:
    """Written as `true`; a hand-edited or folded tag line spells it differently."""
    state = bag_state(manifest_exists=True,
                      info_entries=[(bagmod.LABEL_INCOMPLETE, value)])
    assert state.incomplete and state.lifecycle == "sealed"


def test_bag_state_counts_EVERY_redaction_not_merely_the_first() -> None:
    """`redacted` is a flag; `redactions` is the record, and there can be three.

    `read_tag_file` returns a list precisely so a repeated label is not collapsed;
    this asserts the state function does not undo that one layer up.
    """
    state = bag_state(manifest_exists=True, info_entries=[
        (bagmod.LABEL_REDACTION, "first"),
        ("Bagging-Date", "2026-08-16"),
        (bagmod.LABEL_REDACTION, "second"),
    ])
    assert state.redacted and state.redactions == ("first", "second")
