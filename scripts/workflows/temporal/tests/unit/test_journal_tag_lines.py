"""A caller-supplied string reaching a TAG-LINE COMPOSER must be guarded — swept.

WHY THIS FILE EXISTS, AS THE MEASUREMENT RATHER THAN AS A PRINCIPLE. This package
has one defect shape it keeps re-acquiring: **an externally-supplied string
composed onto a line whose structure means something.** `test_journal_
containment.py` is the same sweep for the PATH spelling of it, and its header
records four instances found by three review passes. This is the TAG-LINE
spelling, and the count there is five:

  * a redaction `reason` carrying `\\n`, which forged `Journal-Incomplete: true`
    on a real bag. Fixed against `_append_tag_line`.
  * the same escape through `open_bag`'s creation loop, which did not call the
    check at all — fixed one pass later, against the parameter that had been
    exploited.
  * the same escape through the LABEL rather than the value, left open by the
    pass that closed the value.
  * `External-Identifier`, which is the run id and **never reached the check at
    all**: `open_bag` iterates `(info or {}).items()` — the caller-supplied half
    — while the run id is placed straight into the module-owned `entries` dict.
    Harmless only because the id was minted internally from a fixed alphabet;
    Phase 9 r2 makes it arrive from a caller, which is what turns it live.
  * the check itself, which refused `\\n` and `\\r` while `read_tag_file` parses
    with `str.splitlines()` — a method that ALSO breaks on `\\v`, `\\f`, `\\x1c`,
    `\\x1d`, `\\x1e`, `\\x85`, `\\u2028` and `\\u2029`. Eight spellings walked
    through a guard aimed at two, and each of them writes one physical line that
    reads back as two entries.

Five instances, one shape. Enumerating instances did not converge — each pass
closed one spelling and the next found a structurally adjacent one. What
converges is changing what the check KEYS ON, which is what this file and
`bag.folds_a_tag_line` do together: the guard asks the parser instead of holding
a list, and the sweep asks the tree instead of holding a memory.

⚠ AND IT IS BOTH HALVES DELIBERATELY, because Phase 1 measured that each catches
what the other cannot: reverting the guard leaves a sweep green, reverting the
declaration leaves a behavioural battery green, *"neither substitutes for the
other."* An inline `if` plus one `pytest` case satisfies the words of r6 and
reproduces its failure.

⚠ WHAT THIS DOES NOT COVER, because a sweep is only as good as its predicate:

  * IT SWEEPS `modules/journal/*.py` AND NOTHING ELSE, the same scope as the
    containment sweep. A tag line composed in another package is invisible here,
    and the scope is named in the failure message so a reader hitting it learns
    the boundary rather than assuming there is none.
  * IT SEES `f"{label}: {value}"`, not `label + ": " + value`, not
    `"%s: %s" % (…)`, not `"{}: {}".format(…)`. A test below asserts this package
    uses none of those, which is what keeps the narrow predicate honest — the
    predicate is narrow AND the alternatives are absent, rather than the
    predicate being narrow and nobody having checked.
  * IT PROVES THE COMPOSITION IS DECLARED, NOT THAT THE GUARD IS RIGHT. The
    battery in the second half tests the guard itself, and the round trip is the
    property it tests against.
"""

from __future__ import annotations

import ast
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
PACKAGE = REPO_ROOT / "scripts" / "workflows" / "temporal" / "modules" / "journal"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "workflows" / "temporal"))

from modules.journal.bag import (BAG_INFO_FILE, BagError,  # noqa: E402
                                 LABEL_INCOMPLETE, RUN_ID_MAX_LENGTH,
                                 RUN_ID_PERMITTED,
                                 RUN_ID_PERMITTED_DESCRIPTION,
                                 folds_a_tag_line, open_bag,
                                 read_tag_file, validated_run_id)

# Every interpolated expression that reaches a tag-line composer in this package
# and is not a module constant, keyed by `(module, source text of the
# expression)`. Each row carries the reason the value is already safe — which is
# the whole point: a row is a claim somebody made and can be checked, where an
# unguarded composition nobody listed is a claim nobody made.
#
# A NEW COMPOSITION FAILS THIS TEST. That is the mechanism. Adding a row is a
# two-line edit and it forces the author to write down why the value cannot
# forge a line, which is the sentence that was missing all five times.
_DECLARED_TAG_VALUES = {
    ("bag.py", "label"):
        "every one of the three composers calls `_refuse_folded_value` first, "
        "which calls `_refuse_forged_label` — a label that is empty, padded, "
        "colon-bearing or line-folding is refused before this line.",
    ("bag.py", "value"):
        "same call: `_refuse_folded_value` puts the value through "
        "`folds_a_tag_line`, which asks `read_tag_file`'s own parser rather "
        "than holding a list of line terminators.",
}

# Spellings of a tag line this package must not use, because the sweep cannot
# see them. Not a style rule — each one re-opens the class silently.
_UNSWEEPABLE_SPELLINGS = ('": " +', '" + ": "', '"%s: %s"', '"{}: {}"',
                          '.format(', "': ' +")


def _modules() -> list[pathlib.Path]:
    return sorted(p for p in PACKAGE.glob("*.py") if "__pycache__" not in p.parts)


def _constant_names(tree: ast.AST) -> set[str]:
    """Module-level UPPERCASE names, whether assigned here or imported.

    Both, for the reason the containment sweep gives: `validate.py` gets its
    label constants by import while `bag.py` assigns them, and a predicate that
    saw only assignments would pad the declaration map with rows that prove
    nothing. An allowlist padded with false entries is an allowlist nobody reads.
    """
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    names.add(target.id)
        elif isinstance(node, ast.ImportFrom):
            names.update(a.asname or a.name for a in node.names
                         if (a.asname or a.name).isupper())
    return names


def _tag_line_composers(paths: list[pathlib.Path]) -> list[tuple[str, str, int]]:
    """`(module, interpolated-expression source, lineno)` for each composed tag line.

    THE SHAPE IS A WHOLE LINE: `f"{label}: {value}"`, optionally with a trailing
    newline. Four elements at most — an interpolated label, a literal opening
    with the separator, an interpolated value, and nothing after it but
    whitespace. That is exactly what a tag line IS, and all three composers in
    this package have precisely that shape.

    THE PREDICATE IS TIGHT ON PURPOSE, AND THE LOOSER VERSION WAS MEASURED. A
    first version matched any f-string whose first element was an interpolation
    followed by a colon, which is true of `f"{path}:{lineno} is not …"` — and it
    reported FIVE `validate.py` error messages as tag-line compositions. Five
    rows all saying "this is a message, not a tag line" is an allowlist nobody
    reads, which is the failure mode the containment sweep's own header names.
    What distinguishes them is that a message CONTINUES after its value and a
    tag line does not.

    ⚠ THE HONEST BOUNDARY: `f"{label}: {value} # note"` is a tag-line
    composition this predicate does not match. It is also not a shape anything
    here writes, and the "no other spelling" test plus the guard call at each
    composer are what stand behind that. Named rather than left for a reader to
    discover, because a sweep is only as good as its predicate.
    """
    return [entry for path in paths
            for entry in _composers_in_tree(
                path.name, ast.parse(path.read_text(encoding="utf-8"),
                                     filename=str(path)))]


def composers_in_source(name: str, source: str) -> list[tuple[str, str, int]]:
    """The same predicate, driven from SOURCE TEXT rather than from a path.

    THIS EXISTS SO THE CONTROL CAN RUN ON A LITERAL SNIPPET, in-process, with no
    file involved — `test_a_census_guard_proves_its_own_predicate` requires that
    of every guard which walks the production tree, and its argument is sharp: a
    predicate that has silently stopped matching anything satisfies every
    assertion in this file AND its vacuity floor, because all of them are
    computed from the same empty result.

    ⚠ THE READ-AND-PARSE ABOVE STAYS INLINE DELIBERATELY. Routing it through
    here instead took this file OUT of that meta-guard's population — it is
    recognised by DOING `ast.parse(<x>.read_text(...))`, which is a fact the
    language records rather than a convention. Caught by the meta-guard itself,
    which is the whole reason it is pinned to a count.
    """
    return _composers_in_tree(name, ast.parse(source, filename=name))


def _composers_in_tree(name: str, tree: ast.Module) -> list[tuple[str, str, int]]:
    """The predicate proper. Both callers above reach it."""
    found = []
    constants = _constant_names(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr) or len(node.values) < 3:
            continue
        label, separator, value = node.values[:3]
        if not (isinstance(label, ast.FormattedValue)
                and isinstance(value, ast.FormattedValue)
                and isinstance(separator, ast.Constant)
                and isinstance(separator.value, str)
                and separator.value.startswith(":")):
            continue
        # Nothing after the value but whitespace — that is what makes it a
        # LINE rather than a message that happens to contain a colon.
        if any(not (isinstance(rest, ast.Constant)
                    and isinstance(rest.value, str)
                    and rest.value.strip() == "")
               for rest in node.values[3:]):
            continue
        for part in (label, value):
            if isinstance(part.value, ast.Name) and part.value.id in constants:
                continue
            found.append((name, ast.unparse(part.value), node.lineno))
    return found


# --- the sweep ---------------------------------------------------------------------

def test_every_value_reaching_a_TAG_LINE_COMPOSER_is_GUARDED_or_DECLARED() -> None:
    """THE REQUIREMENT (r6b). A new `f"{label}: {caller_string}"` goes red."""
    assert _modules(), f"no modules discovered under {PACKAGE} — the sweep is inert"

    undeclared = [(module, source, lineno)
                  for module, source, lineno in _tag_line_composers(_modules())
                  if (module, source) not in _DECLARED_TAG_VALUES]

    assert not undeclared, (
        "these expressions are interpolated into a tag line and nothing "
        "declares why they cannot forge one:\n"
        + "\n".join(f"  {m}:{ln}  f\"{{{src}}}: …\"" for m, src, ln in undeclared)
        + "\n\nFive tag-line forging escapes in this package had exactly this "
          "shape, and the last of them was the RUN ID, which reached a composer "
          "through a dict no guard iterated.\n"
          "Either route the value through `_refuse_folded_value` (or "
          "`validated_run_id`, if it is an identifier rather than free text), "
          "or add a row to `_DECLARED_TAG_VALUES` stating why it cannot carry a "
          "line break.\n"
          f"SCOPE OF THIS SWEEP: {PACKAGE.relative_to(REPO_ROOT)}/*.py and "
          "nothing else — a tag line composed in another package is invisible "
          "here.")


def test_the_declared_set_has_not_gone_STALE() -> None:
    """A row that matches no composition reads as coverage while covering nothing.

    That is the dangerous direction: the next value with that shape gets waved
    through by a reader who sees a familiar-looking entry. It is also the
    specific way r6 could rot — `test_journal_containment.py` was carrying a row
    justified by the deny-list this phase replaced, and it would have gone on
    licensing the next author with a reason that no longer described the guard.
    """
    live = {(module, source) for module, source, _ in _tag_line_composers(_modules())}
    stale = sorted(set(_DECLARED_TAG_VALUES) - live)
    assert not stale, (
        f"these _DECLARED_TAG_VALUES rows match no composition in the package "
        f"any more: {stale}. Delete them — a declaration that covers nothing is "
        f"not a declaration.")


def test_the_sweep_EXAMINED_a_non_zero_number_of_composers() -> None:
    """A sweep whose predicate found nothing satisfies both assertions above.

    Counted rather than floored at one: this package composes tag lines in three
    places and a predicate that found only one of them would be reporting on a
    third of the surface while reading as complete. Failing here is the census
    reporting that the population moved, not a defect.
    """
    composers = _tag_line_composers(_modules())
    assert len(composers) >= 6, (
        f"only {len(composers)} interpolated value(s) reaching a tag-line "
        f"composer were found in {PACKAGE.name}/; there are three composers "
        f"(`_append_tag_line`, `_set_tag_line`, `open_bag`'s creation loop), "
        f"each with a label and a value. If the predicate has narrowed, this "
        f"file is checking less than it claims. Found: {composers}")


def test_the_package_composes_a_tag_line_NO_OTHER_WAY() -> None:
    """The honest half of a narrow predicate: prove the alternatives are absent.

    A sweep that only understands f-strings is fine exactly as long as nothing
    here builds a `Label: value` line by concatenation, `%` or `.format`.
    Asserted, so the boundary is a fact about the tree rather than an assumption
    about its authors.
    """
    offenders = []
    for path in _modules():
        source = path.read_text(encoding="utf-8")
        for spelling in _UNSWEEPABLE_SPELLINGS:
            if spelling in source:
                offenders.append(f"{path.name}: {spelling}")
    assert not offenders, (
        f"these tag-line compositions are invisible to this sweep: {offenders}. "
        f"Use an f-string so the sweep can see it, or widen the predicate here "
        f"to cover the spelling.")


# --- the negative control ------------------------------------------------------------

def test_the_sweep_FAILS_on_a_deliberately_undeclared_composition(
        tmp_path: pathlib.Path) -> None:
    """DEMONSTRATED, NOT ASSERTED — and it must DISCRIMINATE, not merely go red.

    THE FIXTURE IS SELF-CONTAINED AND NOT THIS PACKAGE. A control sharing a
    fixture with the code under test over-fires, and the failure then reads like
    a stronger guard rather than a defect in the control. Four f-strings here:
    one composing from a module constant, one that is an ordinary message rather
    than a tag line, one whose colon has no interpolation before it, and one raw
    caller value. The assertion names exactly the raw one.
    """
    module = tmp_path / "fixture.py"
    module.write_text(
        "LABEL_SEALED = 'Journal-Sealed-At'\n"
        "def a(stamp):\n"
        "    return f'{LABEL_SEALED}: {stamp}'\n"
        "def b(path):\n"
        "    return f'{path} could not be read'\n"
        "def c(count):\n"
        "    return f'Payload-Oxum: {count}'\n"
        "def d(label, reason):\n"
        "    return f'{label}: {reason}'\n")

    found = _tag_line_composers([module])
    assert sorted((m, s) for m, s, _ in found) == [
        ("fixture.py", "label"), ("fixture.py", "reason"),
        ("fixture.py", "stamp")], (
        f"the sweep must see the two real composers' non-constant values and "
        f"nothing else — got {found}. `LABEL_SEALED` is a module constant, `b` "
        f"is a message, and `c` has a literal label with no interpolation "
        f"before the colon")


def test_the_predicate_does_not_flag_an_ORDINARY_message(tmp_path: pathlib.Path) -> None:
    """The false-positive direction, which is how an allowlist becomes noise.

    ALL THREE ROWS ARE REAL LINES FROM `validate.py`, and the first is the one
    that was actually over-matched: a loose predicate keyed on "interpolation,
    then a colon" reported five of these as tag-line compositions, which would
    have put five rows into the declaration map all saying the same thing. What
    separates a message from a tag line is that a message CONTINUES after its
    value.
    """
    module = tmp_path / "fixture.py"
    module.write_text(
        "def a(path, lineno, raw):\n"
        "    return f'{path}:{lineno} is not `<checksum> <path>`: {raw!r}'\n"
        "def b(path):\n"
        "    return f'{path} line is not a `Label: value` tag line'\n"
        "def c(root, prop):\n"
        "    return f'journal root unusable: {root} — {prop}'\n")

    assert _tag_line_composers([module]) == [], (
        "none of these is a tag-line composition — the first continues past its "
        "value, the second's colon is inside prose, and the third's label is a "
        "literal with no interpolation before it. Matching them would pad the "
        "declaration map with rows that prove nothing, which is how an "
        "allowlist stops being read")


@pytest.mark.parametrize("snippet,expected", [
    ('x = f"{label}: {value}"', ["label", "value"]),
    ('x = f"{label}: {value}\\n"', ["label", "value"]),
    ('LABEL = "L"\nx = f"{LABEL}: {value}"', ["value"]),
    ('x = f"{path}:{lineno} is not `<checksum> <path>`: {raw!r}"', []),
    ('x = f"{path} line is not a `Label: value` tag line"', []),
    ('x = f"journal root unusable: {root}"', []),
    ('x = f"{label}: {value} trailing prose"', []),
    ('x = "Payload-Oxum: " + str(count)', []),
])
def test_the_predicate_answers_correctly_on_a_LITERAL_SNIPPET(
        snippet: str, expected: list[str]) -> None:
    """THE POSITIVE CONTROL, in-process, with no file and no tree walk.

    `test_a_census_guard_proves_its_own_predicate` requires this of every guard
    that reads the production tree, and its argument is the reason it is not
    optional: a predicate that has silently stopped matching anything satisfies
    the sweep, the staleness check AND the vacuity floor, because all three are
    computed from the same empty result. Only a snippet with a known answer
    breaks that circle.

    The eight rows are the discriminations the predicate has to make, each one a
    shape that actually appears in or near this package — including the two that
    a looser version got wrong (the `{path}:{lineno}` message, matched; and the
    trailing-prose case, which is the honest boundary named above).
    """
    found = [source for _, source, _ in composers_in_source("snippet.py", snippet)]
    assert found == expected


# --- the battery: the guard itself ----------------------------------------------------
#
# EVERY CHARACTER `str.splitlines()` BREAKS ON, derived rather than remembered.
# The deny-list this replaced named two of these ten. Building the battery by
# ASKING the parser is the same move `folds_a_tag_line` makes, applied to the
# test — a battery listing characters an author thought of would test exactly
# the guard that failed.
LINE_BREAKERS = sorted(
    {chr(c) for c in range(0x2100)
     if len(f"a{chr(c)}b".splitlines()) > 1})


def test_the_battery_is_DERIVED_and_covers_more_than_the_deny_list_did() -> None:
    """The battery's own premise, asserted rather than assumed.

    If this drops to two, the derivation has stopped working and every
    parametrised case below is testing the newline the old check already caught.
    """
    assert len(LINE_BREAKERS) >= 8, (
        f"only {len(LINE_BREAKERS)} line-breaking characters derived: "
        f"{[repr(c) for c in LINE_BREAKERS]}. `str.splitlines()` breaks on at "
        f"least eight; the derivation has stopped working and this battery is "
        f"now testing the two characters the deny-list already refused.")
    assert "\n" in LINE_BREAKERS and " " in LINE_BREAKERS, (
        "the derived set must contain both the obvious terminator and one the "
        "deny-list never mentioned")


@pytest.mark.parametrize("breaker", LINE_BREAKERS)
def test_a_value_carrying_ANY_line_breaker_is_refused_at_bag_creation(
        tmp_path: pathlib.Path, breaker: str) -> None:
    """The forging attempt, run against a real bag, for every terminator.

    The payload is the real escape: a value that folds into what reads as
    `Journal-Incomplete: true` sets a flag no caller asked for, and an
    `incomplete` bag is one this component says LOST DATA. Eight of these ten
    characters passed the check that shipped.
    """
    root = tmp_path / "journal"
    root.mkdir(mode=0o700)
    forged = f"wt{breaker}{LABEL_INCOMPLETE}: true"
    with pytest.raises(BagError):
        open_bag(root, "run", info={"Journal-Worktree": forged})


@pytest.mark.parametrize("breaker", LINE_BREAKERS)
def test_a_RUN_ID_carrying_any_line_breaker_is_refused(breaker: str) -> None:
    """The instance that reached no check at all before this phase.

    `External-Identifier` is placed into `open_bag`'s module-owned `entries`
    dict, which `_refuse_folded_value` never iterated — so the run id was the
    one caller-supplied string with no guard on it whatsoever.
    """
    with pytest.raises(BagError):
        validated_run_id(f"run{breaker}{LABEL_INCOMPLETE}: true")


@pytest.mark.parametrize("outside,why", [
    ("\x00", "a NUL — refused by the filesystem, and by nothing in the old check"),
    (" ", "a line separator no deny-list in this package ever mentioned"),
    ("%", "percent-encoding ambiguity in a Phase 7 object key"),
    (":", "the tag-line separator itself — it forges a value into a label"),
    ("/", "a path separator, and an S3 key delimiter"),
    ("\n", "the newline the deny-list did catch, kept so the battery is a superset"),
    (" ", "whitespace, which a tag-file reader strips and a continuation line uses"),
    ("\t", "a tab, which reads back stripped from the ends of a value"),
    ("\\", "a Windows path separator"),
    ("é", "non-ASCII, which an object key must percent-encode"),
    ("\x1b", "the ANSI introducer — a run id that rewrites the report about itself"),
])
def test_a_run_id_carrying_a_character_OUTSIDE_the_permitted_set_is_refused(
        outside: str, why: str) -> None:
    """FROM THE DECLARATION, NOT FROM A REMEMBERED CHARACTER.

    The phase's checklist asks for exactly this seeding: at least one character
    no existing deny-list mentions, plus a newline. A test naming only `\\n` is
    passed by a one-line call to the deny-list this requirement replaced, which
    is the thing r6 forbids — so the rows here are chosen to be un-passable by
    any deny-list that was ever written in this package.
    """
    assert outside not in RUN_ID_PERMITTED, (
        f"{outside!r} is inside the permitted set, so this row proves nothing "
        f"about the allowlist — the row's premise ({why}) is wrong")
    with pytest.raises(BagError):
        validated_run_id(f"run{outside}id")


@pytest.mark.parametrize("char", sorted(RUN_ID_PERMITTED))
def test_EVERY_character_in_the_declared_set_is_ACCEPTED(char: str) -> None:
    """The other direction, parametrised over the STATED CONSTANT itself.

    A guard that refuses everything discriminates nothing, and a permitted set
    the code does not actually permit is a declaration that lies. Driving the
    constant means the two cannot drift: widening `RUN_ID_PERMITTED` without
    widening the regex fails here.
    """
    assert validated_run_id(f"run{char}id") == f"run{char}id"


def test_a_run_id_that_is_a_RELATIVE_SEGMENT_is_refused_AS_ONE() -> None:
    """A branch no character check could reach is a branch nothing is covering.

    `.` and `..` are composed entirely of permitted characters, so the regex
    admits both — and joined onto the journal root they address the root itself
    or its parent. The diagnosis is what this asserts, not merely the refusal:
    being told "character outside the permitted set" about a string whose every
    character IS permitted sends the caller somewhere there is nothing to find.
    """
    for segment in (".", ".."):
        with pytest.raises(BagError) as exc:
            validated_run_id(segment)
        assert "relative path segment" in str(exc.value), (
            f"{segment!r} must be diagnosed as a relative segment; being caught "
            f"by the character check would tell the caller the wrong thing")


def test_a_run_id_at_and_over_the_LENGTH_CEILING() -> None:
    """The boundary in both directions, because an off-by-one here is silent.

    A ceiling that refuses the value AT it makes the stated maximum a lie, and
    one that admits the value past it makes the ceiling decorative.
    """
    assert validated_run_id("a" * RUN_ID_MAX_LENGTH)
    with pytest.raises(BagError) as exc:
        validated_run_id("a" * (RUN_ID_MAX_LENGTH + 1))
    assert "ceiling" in str(exc.value)


@pytest.mark.parametrize("shape", ["a1b2c3d4" * 4, "build-2026-08-24-a1b2c3",
                                   "review_pr.retry.2", "wf-id-9f3c",
                                   "plan-refine-2026-08-24T09-31-00Z"])
def test_the_set_ADMITS_the_shapes_the_joint_design_is_likely_to_produce(
        shape: str) -> None:
    """Phase 9's checklist: the set must admit the WIDEST name the design allows.

    A set ruled against today's `uuid4().hex` is trivially `[0-9a-f]` and would
    refuse every row here — a dated slug, a workflow-id-shaped name, a retry
    ordinal. Because § *The identity is a joint design* leaves open that the run
    id becomes whatever the orchestrator calls a dispatch, and a character
    admitted into v1 bag names cannot be withdrawn afterwards, refusing these
    now would be a migration later.
    """
    assert validated_run_id(shape) == shape


def test_the_ROUND_TRIP_is_the_property_a_permitted_value_must_satisfy(
        tmp_path: pathlib.Path) -> None:
    """For any accepted value, reading the tag file returns exactly what was written.

    THIS IS THE PROPERTY THE PERMITTED SET IS DEFINED AGAINST, stated as a test
    rather than as a sentence. It is what makes "defined against `read_tag_file`'s
    actual parser" checkable: a character the guard admits and the parser splits
    on would show up here as two entries where one was written, whatever anybody
    believed about which characters are line terminators.
    """
    root = tmp_path / "journal"
    root.mkdir(mode=0o700)
    metadata = {"Journal-Worktree": "build-1787600656",
                "Journal-Origin-Repo": "/opt/skyy-net/claude-dot-files",
                "Journal-Origin-Remote": "git@github.com:helloskyy-io/x.git",
                "Journal-Origin-Commit": "-"}
    bag = open_bag(root, "run.id-2026_08", info=dict(metadata))

    entries = read_tag_file(bag.path / BAG_INFO_FILE)
    assert ("External-Identifier", "run.id-2026_08") in entries
    for label, value in metadata.items():
        assert (label, value) in entries, (
            f"{label} did not survive the round trip: written {value!r}, read "
            f"{[v for l, v in entries if l == label]!r}")
    assert len(entries) == len(set(l for l, _ in entries)), (
        "a label repeated after one write means a value folded into a second "
        "entry — the forging defect, arriving through a value the guard accepted")


@pytest.mark.parametrize("padded", [" leading", "trailing ", "\tboth\t"])
def test_a_value_that_would_read_back_STRIPPED_is_refused(padded: str) -> None:
    """The quiet half of the round trip, and the half a fold check alone misses.

    `read_tag_file` returns `match.group(2).strip()`, so a padded value reads
    back as a DIFFERENT STRING from the one written. That breaks the stated
    property exactly as a folded value does — it simply fails silently instead
    of loudly, which makes it the worse of the two.
    """
    assert folds_a_tag_line(padded), (
        f"{padded!r} does not survive a round trip and the guard must say so")


def test_an_EMPTY_value_is_legal_and_folds_nothing() -> None:
    """A guard that refuses everything discriminates nothing.

    `f"{label}: "` reads back through `_LABEL_RE` as `(label, "")`, which is the
    value that was written. Refusing it would be the guard inventing a rule the
    parser does not have.
    """
    assert not folds_a_tag_line("")
    assert not folds_a_tag_line("an ordinary value with spaces inside it")


# --- the anchor, and the POSITION a breaker sits in ----------------------------------
#
# ⚠ EVERY CASE ABOVE PUTS ITS CHARACTER IN THE MIDDLE — `f"run{outside}id"`,
# `f"run{breaker}{LABEL_INCOMPLETE}: true"`. That tests WHICH characters the
# guard refuses and never WHERE, and the guard's own comment spends a paragraph
# on the difference: `_RUN_ID_RE` is anchored `\A`/`\Z` because `$` matches
# immediately before a trailing newline, so `^[A-Za-z0-9._-]+$` ACCEPTS
# `"abc\n"`. MEASURED on this branch: swapping the anchors for `^`/`$` left the
# entire unit suite green while `validated_run_id("abc\n")` started returning
# its argument — the single character this requirement was written to refuse,
# admitted, with nothing red. A battery derived from the declaration still has
# to be driven at both ends of the string.

@pytest.mark.parametrize("breaker", LINE_BREAKERS)
def test_a_run_id_ENDING_in_a_line_breaker_is_refused(breaker: str) -> None:
    """The trailing position, which is the one an anchor bug admits.

    A trailing terminator is not a cosmetic variant of an embedded one: the id
    is composed as `f"External-Identifier: {run_id}"` and written into
    `bag-info.txt`, so `"run\\n"` puts the NEXT tag line's label at the start of
    a line the reader attributes to nothing — and `str.splitlines()` on the file
    yields a record boundary the writer never wrote.
    """
    with pytest.raises(BagError):
        validated_run_id(f"run{breaker}")


@pytest.mark.parametrize("breaker", LINE_BREAKERS)
def test_a_run_id_BEGINNING_with_a_line_breaker_is_refused(breaker: str) -> None:
    """The leading position, tested for the reason the trailing one is.

    `\\A` is the other half of the anchor pair, and `^` without `re.MULTILINE`
    happens to hold here — which is exactly why it is asserted rather than
    assumed. An assertion that only covers the end of the string leaves half the
    anchor unpinned, and the next author tightening this regex has no signal.
    """
    with pytest.raises(BagError):
        validated_run_id(f"{breaker}run")


def test_the_PROSE_description_of_the_permitted_set_matches_the_SET() -> None:
    """The permitted set is stated in characters AND in words. Both, pinned.

    `RUN_ID_PERMITTED_DESCRIPTION` is what the refusal message prints and what
    `dispatch_identity`'s `--run-id` help text shows an operator. It used to be
    typed out by hand in both places, which is two unpinned copies of the rule
    r6 says is expressed in ONE place — the same shape as the deny-list this
    whole requirement replaced, one altitude up. Expanding the prose and
    comparing it to the set is what stops a widened allowlist from leaving an
    operator reading the old alphabet.
    """
    expanded: set[str] = set()
    for token in RUN_ID_PERMITTED_DESCRIPTION.split(" "):
        if len(token) == 3 and token[1] == "-":
            expanded.update(chr(c) for c in range(ord(token[0]), ord(token[2]) + 1))
        else:
            assert len(token) == 1, (
                f"{token!r} is neither a single character nor an `X-Y` range; the "
                f"description's grammar is what this test can expand, so a new "
                f"shape has to teach it rather than slip through")
            expanded.add(token)
    assert expanded == set(RUN_ID_PERMITTED), (
        f"the prose says {RUN_ID_PERMITTED_DESCRIPTION!r} and the set does not "
        f"agree — only in prose: {sorted(expanded - set(RUN_ID_PERMITTED))!r}, "
        f"only in the set: {sorted(set(RUN_ID_PERMITTED) - expanded)!r}")
