"""A path composed onto a trusted base must be CONTAINED — swept, not remembered.

WHY THIS FILE EXISTS AT ALL, stated as the measurement rather than as a principle.
Three review passes over this package each found exactly one instance of one
defect, in a different module each time:

  * pass 2 — `redact()`'s first-segment check, which `Path("data/../../x").
    parts[:1] == ("data",)` walks straight through, so a redaction marker
    overwrote a file beside the bag in the journal root;
  * pass 2 — a symlink under `data/`, which `is_file()` follows, so it was hashed
    into the manifest as payload and redaction truncated the link's target;
  * pass 3 — `validate.py`'s manifest join, where `bag_path / name` with `name`
    read out of an untrusted `manifest-sha256.txt` hashed a file OUTSIDE the bag
    and reported `result: PASS` over an empty payload;
  * pass 3 — `_refuse_folded_value`'s LABEL parameter, the same forging escape as
    its value parameter, left open by the pass that closed the value.

Four instances, one shape: **an externally-supplied string composed onto a
trusted base.** Enumerating instances did not converge — each pass closed one
spelling and the next found a structurally adjacent one. What converges is
changing what the check keys on, which is what this file does.

THIS IS THE PACKAGE'S OWN ARGUMENT APPLIED TO THE PACKAGE. `journal_activities`
argues that "a rule written in prose has not once prevented a write path being
added without its emit", and answers it for bag-open with an enumerating sweep
(`test_every_parent_opens_a_run_bag.py`). The containment rule was prose plus
three hand-written copies and one hole. It is now one named function
(`bag.contained_relpath`) plus the sweep below.

⚠ WHAT THIS DOES NOT COVER, because a sweep is only as good as its predicate:

  * IT SWEEPS `modules/journal/*.py` AND NOTHING ELSE. A join written in a
    different package that addresses a bag is invisible here. The scope is named
    in the failure message so a reader hitting it learns the boundary.
  * IT SEES `Path / str` COMPOSITION, not `os.path.join`, not `f"{base}/{x}"`,
    and not `open(base + x)`. Those are three other spellings of the same defect.
    A test asserts below that this package uses none of them, which is what keeps
    the narrow predicate honest: the predicate is narrow AND the alternatives are
    absent, rather than the predicate being narrow and nobody having checked.
  * IT PROVES THE JOIN IS GUARDED, NOT THAT THE GUARD IS RIGHT. The battery in
    the second half is what tests the guard itself.
"""

from __future__ import annotations

import ast
import os
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
PACKAGE = REPO_ROOT / "scripts" / "workflows" / "temporal" / "modules" / "journal"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "workflows" / "temporal"))

from modules.journal import bag as bagmod           # noqa: E402
from modules.journal.bag import (BagError, PAYLOAD_DIR, contained_relpath,   # noqa: E402
                                 open_bag)
from modules.journal.validate import validate_bag   # noqa: E402

# Every `base / x` in this package whose right operand is neither a constant nor
# a `contained_relpath(...)` call, keyed by the SOURCE TEXT of that operand so the
# pin survives a line move and breaks when the expression changes. Each carries
# the reason the value is already trustworthy — which is the whole point: an
# entry here is a claim someone made and can be checked, where an unguarded join
# nobody listed is a claim nobody made.
#
# A NEW JOIN FAILS THIS TEST. That is the mechanism. Adding a row is a two-line
# edit and it forces the author to write down why the value cannot escape, which
# is the sentence that was missing all four times.
_TRUSTED_JOINS = {
    ("bag.py", "run_id"):
        "open_bag rebinds run_id through `bag.validated_run_id` immediately "
        "above this line, which is the ONE place the permitted character set is "
        "expressed — an ALLOWLIST of [A-Za-z0-9._-] plus an explicit refusal of "
        "`.` and `..`, so no separator, no line terminator and no character "
        "nobody enumerated survives the join. ⚠ THIS ROW USED TO READ 'refuses "
        "a run_id containing a separator or a relative segment', which was true "
        "of the deny-list Phase 9 r6 replaced and would have gone on licensing "
        "the next author with a reason that no longer described the guard. That "
        "deny-list refused `a/b` and admitted a newline; the run id is also a "
        "tag VALUE, and `test_journal_tag_lines.py` is the sweep for that half.",
    ("bag.py", "slug if ordinal == 1 else f'{slug}-{ordinal}'"):
        "writer_dir slugifies through _SAFE_SEGMENT_RE, which maps every "
        "character outside [A-Za-z0-9._-] to '-', so no separator survives and "
        "no segment can be a bare '..' that mkdir would follow.",
    ("bag.py", "rel"):
        "seal() joins paths that payload_files() derived by walking the bag's "
        "own data/ directory — they come off the filesystem, not off a caller.",
    ("validate.py", "rel"):
        "same as seal(): payload_files() output, derived from the tree itself.",
    ("validate.py", "name"):
        "_parse_manifest passes every manifest entry through contained_relpath "
        "before it reaches this dict, and refuses the line otherwise. This is "
        "the join that reported PASS over /etc/hostname before that existed.",
}

# Spellings of a path join this package must not use, because the sweep above
# cannot see them. Not a style rule — each one re-opens the class silently.
_UNSWEEPABLE_SPELLINGS = ("os.path.join(", "os.sep.join(", "posixpath.join(")


def _modules() -> list[pathlib.Path]:
    return sorted(p for p in PACKAGE.glob("*.py") if "__pycache__" not in p.parts)


def _constant_names(tree: ast.AST) -> set[str]:
    """Module-level UPPERCASE names, whether assigned here or imported.

    Both, because `validate.py` gets `PAYLOAD_DIR` and `MANIFEST_FILE` by import
    while `bag.py` assigns them. A predicate that only saw assignments would have
    reported six of `validate.py`'s eight joins as unguarded, and an allowlist
    padded with six false entries is an allowlist nobody reads.
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


def _unguarded_joins(paths: list[pathlib.Path]) -> list[tuple[str, str, int]]:
    """`(module, right-operand source, lineno)` for every join that is not obviously safe.

    Every `/` in this package is a path join — there is no arithmetic division in
    any of these modules, which `test_the_predicate_sees_only_path_joins` pins so
    this assumption cannot rot silently.
    """
    found = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        constants = _constant_names(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
                continue
            right = node.right
            if isinstance(right, ast.Constant):
                continue
            if isinstance(right, ast.Name) and right.id in constants:
                continue
            if isinstance(right, ast.Call) and \
                    getattr(right.func, "id", None) == "contained_relpath":
                continue
            found.append((path.name, ast.unparse(right), node.lineno))
    return found


# --- the sweep ---------------------------------------------------------------------

def test_every_untrusted_path_join_in_the_package_is_GUARDED_or_DECLARED() -> None:
    """THE REQUIREMENT. A new `base / caller_string` goes red rather than shipping."""
    assert _modules(), f"no modules discovered under {PACKAGE} — the sweep is inert"

    undeclared = [(module, source, lineno)
                  for module, source, lineno in _unguarded_joins(_modules())
                  if (module, source) not in _TRUSTED_JOINS]

    assert not undeclared, (
        "these path joins compose a value that is neither a module constant nor "
        "the output of `contained_relpath`, and nothing declares why it is safe:\n"
        + "\n".join(f"  {m}:{ln}  ... / {src}" for m, src, ln in undeclared)
        + "\n\nFour containment escapes in this package had exactly this shape. "
          "Either route the value through `bag.contained_relpath`, or add a row "
          "to _TRUSTED_JOINS stating why the value cannot escape.\n"
          f"SCOPE OF THIS SWEEP: {PACKAGE.relative_to(REPO_ROOT)}/*.py and nothing "
          "else — a join written elsewhere that addresses a bag is invisible here."
    )


def test_the_declared_set_has_not_gone_STALE() -> None:
    """An allowlist that outlives its entries stops being a list of claims.

    The dangerous direction is a row that no longer matches any join: it reads as
    coverage while covering nothing, and the next join with that shape gets waved
    through by a reader who sees a familiar-looking entry.
    """
    live = {(module, source) for module, source, _ in _unguarded_joins(_modules())}
    stale = sorted(set(_TRUSTED_JOINS) - live)
    assert not stale, (
        f"these _TRUSTED_JOINS rows match no join in the package any more: {stale}. "
        f"Delete them — a declaration that covers nothing is not a declaration.")


def test_the_predicate_sees_only_path_joins() -> None:
    """The load-bearing assumption, asserted rather than believed.

    The sweep treats every `/` as a path composition. That is true today and it
    is what makes the allowlist small enough to read. If arithmetic division ever
    lands in this package the sweep starts reporting numbers as unguarded joins,
    an author adds a row to silence it, and the allowlist quietly becomes noise.
    """
    numeric = []
    for path in _modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and \
                    isinstance(node.right, ast.Constant) and \
                    isinstance(node.right.value, (int, float)):
                numeric.append(f"{path.name}:{node.lineno}")
    assert not numeric, (
        f"arithmetic division appeared in the journal package at {numeric}. The "
        f"containment sweep assumes every `/` is a path join; teach it to tell "
        f"them apart before adding one.")


def test_the_package_uses_no_join_spelling_the_sweep_CANNOT_SEE() -> None:
    """The honest half of a narrow predicate: prove the alternatives are absent.

    A sweep that only understands `Path / str` is fine exactly as long as nothing
    here composes a path any other way. Asserted, so the sweep's boundary is a
    fact about the tree rather than an assumption about its authors.
    """
    offenders = []
    for path in _modules():
        source = path.read_text(encoding="utf-8")
        for spelling in _UNSWEEPABLE_SPELLINGS:
            if spelling in source:
                offenders.append(f"{path.name}: {spelling}")
    assert not offenders, (
        f"these path compositions are invisible to the containment sweep: "
        f"{offenders}. Use `base / x` so the sweep can see it, or widen the "
        f"predicate in this file to cover the spelling.")


# --- the negative control ------------------------------------------------------------

def test_the_sweep_FAILS_on_a_deliberately_unguarded_join(tmp_path: pathlib.Path) -> None:
    """DEMONSTRATED, NOT ASSERTED — and it must DISCRIMINATE, not merely go red.

    THE FIXTURE IS SELF-CONTAINED AND NOT THIS PACKAGE. A control sharing a
    fixture with the code under test over-fires, and the failure then reads like
    a stronger guard rather than a defect in the control. Three joins here: one
    constant, one routed through `contained_relpath`, one raw. The assertion
    names exactly the raw one.
    """
    module = tmp_path / "fixture.py"
    module.write_text(
        "PAYLOAD_DIR = 'data'\n"
        "def a(base):\n"
        "    return base / PAYLOAD_DIR\n"
        "def b(base, x):\n"
        "    return base / contained_relpath(x)\n"
        "def c(base, x):\n"
        "    return base / x\n")

    found = _unguarded_joins([module])
    assert [(m, s) for m, s, _ in found] == [("fixture.py", "x")], (
        f"the sweep must name exactly the unguarded join, not all three — "
        f"got {found}")


# --- the battery: the guard itself, not the call sites --------------------------------

ESCAPES = [
    "../outside.txt",
    "data/../../ANOTHER-RUN/x",
    "data/../..",
    "/etc/passwd",
    "/data/x",
    "data/child/../../../escape",
    "..",
    ".",
    "",
    "   ",
    "bag-info.txt",
    "./../data/x",
]


@pytest.mark.parametrize("escape", ESCAPES)
def test_contained_relpath_refuses_every_escape_in_the_battery(escape: str) -> None:
    """One battery, applied to the shared rule rather than to each caller.

    Applied to the rule because that is what the callers now share — before
    `contained_relpath` existed, this battery would have had to be written three
    times and would have been written twice.
    """
    with pytest.raises(BagError):
        contained_relpath(escape)


@pytest.mark.parametrize("absolute", ["/etc/passwd", "/data/x", "//data/x"])
def test_an_ABSOLUTE_path_is_refused_AS_ABSOLUTE_and_not_merely_refused(
        absolute: str) -> None:
    """A branch no mutation could reach is a branch no test is covering.

    FOUND BY MUTATING THIS FILE'S OWN SUBJECT: deleting `contained_relpath`'s
    absolute-path branch entirely broke **nothing**, because every absolute input
    in the battery also fails the under-`data/` check one line below it. The
    battery proved the inputs were refused and said nothing about which check
    refused them.

    The branch still earns its place, and the reason is the DIAGNOSIS rather than
    the refusal: `Path("/j/run") / "/etc/passwd"` does not escape the base by
    degrees, it DISCARDS it — a different bug in the caller, needing a different
    message. So the message is what this asserts, which is the only thing that
    makes the branch covered.
    """
    with pytest.raises(BagError) as exc:
        contained_relpath(absolute)
    assert "absolute path" in str(exc.value), (
        "an absolute entry must be diagnosed as absolute — being caught by the "
        "containment check instead tells the caller the wrong thing about why")


@pytest.mark.parametrize("good", ["data", "data/x.txt", "./data/x.txt",
                                  "data/child/transcript.jsonl",
                                  "data/child/../child/a"])
def test_contained_relpath_ACCEPTS_and_normalises_what_is_genuinely_inside(good: str) -> None:
    """A guard that refuses everything discriminates nothing.

    `./data/x.txt` is the case that matters beyond symmetry: it is the
    `sha256sum` convention a foreign BagIt implementation writes, and refusing
    (or failing to normalise) it made a healthy bag report `ok=False` with its
    only payload file listed as both present and `unlisted`.
    """
    normalised = contained_relpath(good)
    assert normalised == PAYLOAD_DIR or normalised.startswith(f"{PAYLOAD_DIR}/")
    assert ".." not in normalised.split("/")
    assert not normalised.startswith("./")


@pytest.mark.parametrize("escape", [e for e in ESCAPES if e.strip()])
def test_redact_refuses_the_same_battery_against_a_REAL_bag(
        tmp_path: pathlib.Path, escape: str) -> None:
    """The call site, driven with the same inputs, against a bag on disk.

    The sweep proves `redact` routes through the guard; this proves the routing
    survives the rest of the function — and it writes a real victim file beside
    the bag so an escape is observable as damage rather than inferred.
    """
    root = tmp_path / "journal"
    root.mkdir(mode=0o700)
    victim = root / "ANOTHER-RUN"
    victim.mkdir()
    (victim / "x").write_text("precious")

    bag = open_bag(root, "run")
    (bag.payload_dir / "real.txt").write_text("payload")

    with pytest.raises(BagError):
        bag.redact(escape, "should never land")
    assert (victim / "x").read_text() == "precious"


def test_a_MANIFEST_naming_a_file_outside_the_bag_cannot_report_PASS(
        tmp_path: pathlib.Path) -> None:
    """The pass-3 escape, pinned as behaviour so it cannot come back quietly.

    Reproduced exactly as it was found: an empty payload, and a manifest whose
    single entry names a real file outside the bag with its true checksum. Before
    the fix this printed `result: PASS` — every check agreed, because `missing`
    saw a file that existed, `mismatched` saw a checksum that matched, and
    `unlisted` compared against an empty `present` set.
    """
    import hashlib

    root = tmp_path / "journal"
    root.mkdir(mode=0o700)
    outside = tmp_path / "outside.txt"
    outside.write_text("not payload, and not in any bag")
    digest = hashlib.sha256(outside.read_bytes()).hexdigest()

    for entry in (f"../../{outside.name}", str(outside)):
        bag = open_bag(root, f"run-{abs(hash(entry))}")
        (bag.path / "manifest-sha256.txt").write_text(f"{digest}  {entry}\n")
        report = validate_bag(bag.path)
        assert not report.ok, f"a manifest naming {entry!r} reported PASS"
        assert report.structural, "and it must say WHY, not merely fail"
        assert report.lifecycle == "sealed", (
            "a manifest exists, so the bag is sealed — the escape must not "
            "change what state the bag is reported to be in")


def test_the_containment_check_is_what_stops_it_and_not_something_else(
        tmp_path: pathlib.Path) -> None:
    """The control on the control: prove the escape WOULD land without the guard.

    A test that asserts a bad input is refused proves nothing about which check
    refused it. This composes the same path the way the old code did and shows it
    genuinely reaches outside the bag — so the assertion above is about
    containment rather than about some incidental refusal.
    """
    root = tmp_path / "journal"
    root.mkdir(mode=0o700)
    bag = open_bag(root, "run")
    (root / "victim.txt").write_text("beside the bag")

    unguarded = bag.path / "data/../../victim.txt"
    assert os.path.realpath(unguarded) == os.path.realpath(root / "victim.txt"), (
        "the fixture no longer demonstrates an escape, so the tests above are "
        "asserting against nothing")
    with pytest.raises(BagError):
        contained_relpath("data/../../victim.txt")
