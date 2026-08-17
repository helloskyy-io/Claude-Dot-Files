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
from modules.journal import validate as validate_mod             # noqa: E402
from modules.journal.bag import (BagState, bag_state, lifecycle_of,  # noqa: E402
                                 open_bag)
from modules.journal.validate import validate_bag                # noqa: E402

# EVERY LABEL THIS PACKAGE DEFINES, AND THE RULE IS THAT SIMPLE ON PURPOSE. An
# earlier draft of this file swept four of the five and justified the exclusion
# by "`Event-Schema-Version` is not one of the three state fields" — a rule its
# own contents then broke, because `Journal-Sealed-At` is not one of the three
# either. It is swept because a reader could conclude `sealed` from that tag's
# PRESENCE, which mints a second lifecycle derivation by another spelling; and
# once that is the reason, an inclusion rule of "the ones I judged risky" is a
# judgement call made once and inherited forever.
#
# So the set is total and the escape hatch is a DECLARATION, exactly as
# `test_journal_containment.py` handles the same problem for path joins: a
# comparison that is not a state derivation is listed below with the reason it
# is not. That turns a false positive from a blocked author into a two-line
# claim someone can check.
_STATE_LABELS = {"LABEL_REDACTION", "LABEL_INCOMPLETE", "LABEL_GAP",
                 "LABEL_SEALED_AT", "LABEL_SCHEMA_VERSION"}

# `(module, comparison source text)` → why this comparison does not derive one
# of the three state fields. Keyed by SOURCE TEXT so an entry survives a line
# move and lapses when the expression changes.
_DECLARED_NON_DERIVATIONS = {
    ("validate.py", "label == bagmod.LABEL_SCHEMA_VERSION"):
        "reports a MISSING schema version as a structural problem. It reads no "
        "state field: a bag with no version is neither open nor sealed by "
        "virtue of that, and no second copy of this check exists to drift from.",
}

# The two lifecycle values. Named here as data rather than reached for as
# literals, so this file does not become the third copy of the thing it guards.
_LIFECYCLE_VALUES = {"open", "sealed"}

# The one function permitted to turn labels into flags, and the one permitted to
# produce a lifecycle string. Both live in `bag.py`; a second name here would be
# this guard licensing the defect it exists to catch.
_LABEL_DERIVER = ("bag.py", "bag_state")
_LIFECYCLE_DERIVER = ("bag.py", "lifecycle_of")


def imports_the_journal_package(source: str, path: pathlib.Path) -> bool:
    """Does this module import the journal package, under ANY spelling?

    RESOLVED FROM THE AST, NOT MATCHED AS A SUBSTRING, and the difference is the
    whole future-proofing claim. The first draft asked whether the text contained
    `"modules.journal"` or `"from .journal"`. That was true of every importer
    that exists today and false of at least four legal spellings of the same
    import — `from modules import journal`, `from . import journal`,
    `from ..journal import bag`, `import modules.journal.bag as b` — none of
    which violates any convention this repo documents. A Phase 3 emitter written
    that way would have been outside the sweep while the docstring claimed it was
    inside it, which is a worse failure than not sweeping at all: an undisclosed
    hole in the guarantee the file is trusted for.

    Every import is resolved to the dotted path it actually names — walking `..`
    levels up from the importing file — and compared against the package's own.
    """
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:                     # not our module to reason about
        return False

    package_path = PACKAGE.relative_to(TEMPORAL).as_posix().replace("/", ".")
    named: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            named.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                anchor = path.parent
                for _ in range(node.level - 1):
                    anchor = anchor.parent
                if not anchor.is_relative_to(TEMPORAL):
                    continue
                prefix = anchor.relative_to(TEMPORAL).as_posix().replace("/", ".")
                base = f"{prefix}.{base}" if base else prefix
            # BOTH the module and each imported NAME: `from modules import
            # journal` names the package in the second position, not the first.
            named.append(base)
            named.extend(f"{base}.{alias.name}" if base else alias.name
                         for alias in node.names)
    return any(name == package_path or name.startswith(f"{package_path}.")
               for name in named)


def _swept_modules() -> list[pathlib.Path]:
    """The journal package, plus every non-test module that imports it.

    COMPUTED, NOT LISTED. A hard-coded file list is a second enumeration of the
    thing this file argues cannot be enumerated — it would have to be edited by
    the same author who adds the reader it is supposed to catch.
    """
    package = [p for p in PACKAGE.glob("*.py") if "__pycache__" not in p.parts]
    importers = [
        path for path in TEMPORAL.rglob("*.py")
        if "__pycache__" not in path.parts and "tests" not in path.parts
        and not path.is_relative_to(PACKAGE)
        and imports_the_journal_package(path.read_text(encoding="utf-8"), path)
    ]
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


def _mentions_a_state_label(operand: ast.AST) -> bool:
    """A state label ANYWHERE in this operand, not only as the operand itself.

    ⚠ THE WHOLE OPERAND SUBTREE, because `label in (LABEL_REDACTION, LABEL_GAP)`
    is the idiomatic way to write "is this entry one of the flag labels" and the
    first draft of this predicate could not see it: it asked whether the operand
    WAS a label, and the operand was a `Tuple`. A guard that catches `==` and
    misses `in` catches the copy someone wrote yesterday and not the one they
    will write tomorrow.
    """
    return any(_is_state_label(node) for node in ast.walk(operand))


def find_label_derivations(source: str, filename: str) -> list[tuple[str, int, str]]:
    """`(filename, lineno, source)` for every comparison against a state label."""
    tree = ast.parse(source, filename=filename)
    owner = _functions_by_node(tree)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not any(_mentions_a_state_label(operand)
                   for operand in [node.left, *node.comparators]):
            continue
        if (filename, owner.get(node, "")) == _LABEL_DERIVER:
            continue
        if (filename, ast.unparse(node)) in _DECLARED_NON_DERIVATIONS:
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

    def consumed_by_a_comparison(node: ast.AST) -> bool:
        """⚠ THROUGH ANY CONTAINER LITERAL, not only as a direct operand.

        `(report.lifecycle, report.redacted) == ("sealed", True)` is one
        comparison, and the literal's PARENT is the tuple. Reading only the
        immediate parent reported that as a derivation — a false positive on an
        idiom this repo already uses, and a guard that fires on legitimate
        reading is a guard someone switches off within a week.
        """
        current = parent.get(node)
        while isinstance(current, (ast.Tuple, ast.List, ast.Set)):
            current = parent.get(current)
        return isinstance(current, ast.Compare)

    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and node.value in _LIFECYCLE_VALUES):
            continue
        if isinstance(node.value, bool):        # `True in {"open"}` is False, but be explicit
            continue
        if consumed_by_a_comparison(node):
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

# The one a review pass found the FIRST predicate could not see: `in` over a
# container, which is how anyone would write "is this one of the flag labels".
_RETYPED_FLAG_AS_MEMBERSHIP = '''
from .bag import LABEL_INCOMPLETE, LABEL_REDACTION

def some_new_reader(entries):
    return [v for label, v in entries
            if label in (LABEL_REDACTION, LABEL_INCOMPLETE)]
'''

_RETYPED_LIFECYCLE = '''
def some_new_reader(bag_path):
    return "sealed" if (bag_path / "manifest-sha256.txt").is_file() else "open"
'''

# Two things the sweeps must NOT fire on, in one fixture: a WRITER passing a
# label as an argument, and a caller comparing an already-derived lifecycle —
# including through a tuple, which the first predicate misread as a derivation.
_LEGITIMATE_USE = '''
from .bag import LABEL_GAP

def a_writer(bag, what):
    _append_tag_line(bag.info_path, LABEL_GAP, what)

def a_caller(bag, report):
    if bag.lifecycle == "sealed":
        bag.seal()
    assert (report.lifecycle, report.redacted) == ("sealed", True)
    return bag.state.incomplete
'''


@pytest.mark.parametrize("source", [_RETYPED_FLAG, _RETYPED_FLAG_QUALIFIED,
                                    _RETYPED_FLAG_AS_MEMBERSHIP])
def test_the_label_sweep_CATCHES_a_retyped_flag_rule(source: str) -> None:
    """Three spellings — bare name, module-qualified, and `in` over a container."""
    assert find_label_derivations(source, "some_new_module.py")


def test_the_lifecycle_sweep_CATCHES_a_retyped_lifecycle_rule() -> None:
    assert find_lifecycle_derivations(_RETYPED_LIFECYCLE, "some_new_module.py")


def test_neither_sweep_fires_on_a_WRITER_or_on_legitimate_CONSUMPTION() -> None:
    """The half that keeps the guard usable rather than merely strict.

    Both halves discriminate, which an earlier draft's did not: its fixture
    mentioned no label at all, so the label assertion passed no matter what the
    predicate did. A writer PASSING a label is the case that has to stay legal —
    every append in `bag.py` is one — and the tuple comparison is the idiom the
    lifecycle predicate used to misread.
    """
    assert not find_label_derivations(_LEGITIMATE_USE, "a_caller.py")
    assert not find_lifecycle_derivations(_LEGITIMATE_USE, "a_caller.py")


def test_a_DECLARED_non_derivation_is_exempt_and_an_undeclared_one_is_not() -> None:
    """The escape hatch exists, and it is keyed to the exact expression.

    Without this an author adding a legitimate structural check against a label
    has no move except weakening the sweep. With it, the exemption costs a
    written reason — the same trade `test_journal_containment.py` makes.
    """
    declared = 'x = 1 if label == bagmod.LABEL_SCHEMA_VERSION else 2'
    assert not find_label_derivations(declared, "validate.py")
    assert find_label_derivations(declared, "some_other_module.py"), \
        "a declaration must not exempt the same expression in another module"
    assert find_label_derivations(
        'x = label != bagmod.LABEL_SCHEMA_VERSION', "validate.py"), \
        "a declaration must lapse when the expression changes"


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


# `(where the importing file lives, what it writes)`. A RELATIVE import names the
# journal package only from certain locations, so the location is part of the
# case — a parametrisation that varied only the statement asserted something
# false and was corrected by running it.
_DEEP = TEMPORAL / "modules" / "assistant" / "emit" / "an_emitter.py"
_BESIDE = TEMPORAL / "modules" / "an_emitter.py"
_ONE_DOWN = TEMPORAL / "modules" / "assistant" / "an_emitter.py"


@pytest.mark.parametrize("author,statement", [
    (_DEEP, "from modules.journal import bag"),      # the spelling in use today
    (_DEEP, "from modules.journal.bag import bag_state"),
    (_DEEP, "import modules.journal.bag"),
    (_DEEP, "import modules.journal.bag as b"),
    (_DEEP, "from modules import journal"),          # names the package SECOND
    (_BESIDE, "from . import journal"),              # relative, beside the package
    (_BESIDE, "from .journal import bag"),
    (_ONE_DOWN, "from ..journal.bag import bag_state"),   # up out of a subpackage
])
def test_importer_discovery_sees_EVERY_spelling_of_the_import(
        author: pathlib.Path, statement: str) -> None:
    """The claim the whole design leans on: Phase 3's emitters are in scope.

    A substring match on `"modules.journal"` was true of every importer that
    exists today and false of four of these, none of which breaks any documented
    convention. The guarantee was therefore stronger in the docstring than in the
    code — the exact shape of defect this file exists to catch, in this file.
    """
    assert imports_the_journal_package(statement + "\n", author), statement


@pytest.mark.parametrize("author,statement", [
    (_DEEP, "import os"),
    (_DEEP, "from modules.assistant import plan_activities"),
    (_DEEP, "from ..assistant import plan_activities"),
    # RESOLVED, NOT PATTERN-MATCHED: from three packages down, `.journal` names
    # `modules.assistant.emit.journal`, which is a different module that happens
    # to share a name. A checker that keyed on the word would claim this file.
    (_DEEP, "from . import journal"),
    (_DEEP, "from .journal import bag"),
])
def test_importer_discovery_does_not_claim_UNRELATED_modules(
        author: pathlib.Path, statement: str) -> None:
    """Sweeping everything would be the other way to be useless."""
    assert not imports_the_journal_package(statement + "\n", author), statement


def test_a_sealed_bag_still_reports_SEALED_when_the_payload_cannot_be_read(
        tmp_path, monkeypatch) -> None:
    """The one behavioural change this refactor makes, asserted rather than commented.

    `validate_bag` used to set the lifecycle AFTER walking the payload, so an
    `OSError` mid-walk returned `open` for a bag whose manifest was plainly on
    disk — the report collapsing under exactly the partial-read case its
    docstring promises to survive. The state is now derived from the tag files
    and the manifest before the walk, so the partial report still carries what
    was known.

    MONKEYPATCHED RATHER THAN `chmod`-ED, deliberately: a mode-based fixture is a
    no-op for root, and this suite's own history includes a test that asserted a
    property of the machine it ran on and put the merge gate red three times.
    """
    bag = _bag_in_state(tmp_path, "run-unreadable", sealed=True, redacted=False,
                        incomplete=False)
    assert validate_bag(bag.path).lifecycle == "sealed"      # before the fault

    def refuse(*_args, **_kwargs):
        raise OSError(5, "Input/output error", str(bag.payload_dir))

    monkeypatch.setattr(validate_mod, "payload_files", refuse)
    report = validate_bag(bag.path)

    assert report.lifecycle == "sealed", \
        "a sealed bag whose payload could not be walked is not an open bag"
    assert not report.ok
    assert any("could not be read" in problem for problem in report.structural), \
        report.structural


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


def test_a_malformed_flag_value_leaves_the_flag_FALSE_and_says_so(tmp_path) -> None:
    """The refusal to guess, and the report that keeps the refusal honest.

    Neither guess is safe: `true` asserts a gap nobody recorded, and a silent
    `false` is an operator reading `incomplete: false` off a line no code could
    parse — this component's own worst outcome. So the boolean stays false AND
    the line is surfaced, and the validator turns that into a structural finding
    so the bag does not read as `ok`.
    """
    state = bag_state(manifest_exists=False, info_entries=[
        (bagmod.LABEL_INCOMPLETE, "perhaps"),
        (bagmod.LABEL_GAP, "the PR body — disk full"),
    ])
    assert state == BagState(lifecycle="open", redacted=False, incomplete=False,
                             redactions=(), gaps=("the PR body — disk full",),
                             unreadable=("Journal-Incomplete: perhaps",))

    bag = open_bag(tmp_path, "run-malformed")
    with bag.info_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{bagmod.LABEL_INCOMPLETE}: perhaps\n")
    report = validate_bag(bag.path)
    assert not report.incomplete
    assert not report.ok, "an unreadable lifecycle value must not report as fine"
    assert any("cannot be read" in problem for problem in report.structural), \
        report.structural


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
