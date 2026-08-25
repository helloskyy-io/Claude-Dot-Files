"""A `bag.py` mutation that REFUSES a value must leave the bag byte-unchanged — swept.

WHY THIS FILE EXISTS, AS THE MEASUREMENT RATHER THAN AS A PRINCIPLE. A review
pass found two functions here that changed durable state and only then validated
the value that could be refused:

  * `Bag.redact` replaced the payload file with its marker and THEN composed the
    `Journal-Redaction` tag line. A reason that does not survive `read_tag_file`
    raised with the payload already gone and no tombstone naming it — on the one
    sanctioned path for scrubbing a leaked credential. The marker's own text
    asserts that such a record exists in `bag-info.txt`, so the bag did not
    merely lose the tombstone, it asserted a false one.
  * `Bag.mark_incomplete` appended `Journal-Incomplete: true` and THEN composed
    the `Journal-Gap` record. A folding `why` left a bag reporting a loss it
    could not describe, and the `BagError` propagated out of the handler that was
    recording a lost write — masking the original failure with a second one.

⚠ THE REVIEW NAMED TWO. ASKING THE TREE WHICH OTHER FUNCTIONS HERE MUTATE BEFORE
THEY VALIDATE FOUND A THIRD, AND IT WAS THE WORST OF THEM. `open_bag` created
`<root>/<run_id>/`, `data/` and `bagit.txt`, and only then validated the caller's
`info` entries. A refused label left a directory with no `bag-info.txt` — and
because `open_bag`'s `bag_path.exists()` fast path ADOPTS an existing directory,
every later open of that run id returned a bag whose `.info()`, `.state`,
`.redacted` and `.incomplete` all raise `FileNotFoundError`. One refused label
poisoned that run id permanently.

Three instances, one shape: **a durable mutation ordered before the refusal that
can abort it.** Fixing three spellings is what the pass before this one did with
tag-line forging, five times, and it did not converge (see
`test_journal_tag_lines.py`'s header, which is the same lesson in the same
package). What converges is changing what the check KEYS ON — so this file does
not test `redact` and `mark_incomplete`. It enumerates the mutating surface of
`bag.py` FROM THE TREE and requires every member to be classified, then drives
every refusal a classified member declares and asserts the bag is byte-identical
afterwards.

**A NEW MUTATOR FAILS THIS TEST until it is declared.** That is the mechanism.
Declaring one `TOTAL` is a two-line edit and forces the author to write down why
no caller-supplied value can abort it — which is the sentence that was missing
all three times. A row is a claim somebody made and can be checked; an
undeclared mutator is a claim nobody made.

⚠ WHAT THIS DOES NOT COVER, because a sweep is only as good as its predicate:

  * IT SWEEPS `bag.py` AND NOTHING ELSE. A mutator in another module of this
    package is invisible here; the scope is named in the failure message so a
    reader hitting it learns the boundary rather than assuming there is none.
  * IT FINDS MUTATION SYNTACTICALLY — a write-mode `open`/`os.open`, an
    unambiguous filesystem-mutating method name, or a call to another member. A
    mutation reached through a callable held in a variable, or through a module
    this file does not name, is not seen. Half A is what keeps that honest: it
    asserts every raw write in the file is inside a declared primitive, so the
    narrow predicate is narrow AND the alternatives are absent, rather than the
    predicate being narrow and nobody having checked.
  * IT PROVES THE ORDER, NOT THE REFUSAL. Whether the right values are refused
    is `test_journal_tag_lines.py`'s derived battery; this file assumes the
    refusal fires and asks only what state it fires from.
  * IT IS ABOUT REFUSALS, NOT ABOUT I/O FAILURE. `redact` still writes the
    marker and appends the tombstone as two separate operations, so an `ENOSPC`
    or a permission error landing between them leaves the same half-applied bag
    the reordering closes for a refused value. That window is unchanged by this
    work and is not what "all-or-nothing" means here — closing it needs the
    same write-ahead or create-then-rename machinery Phase 9 r7 defers, and
    saying so is cheaper than letting a reader infer a stronger guarantee from
    this file's title.
"""

from __future__ import annotations

import ast
import pathlib
import sys
import textwrap
from typing import Callable

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
BAG_PY = REPO_ROOT / "scripts" / "workflows" / "temporal" / "modules" / "journal" / "bag.py"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "workflows" / "temporal"))

from modules.journal import bag as bagmod  # noqa: E402
from modules.journal.bag import BagError, open_bag  # noqa: E402

SCOPE = "modules/journal/bag.py"

# --- half A: the primitives ------------------------------------------------------

# The four functions permitted to touch the filesystem directly. Everything else
# in `bag.py` mutates THROUGH one of these, which is what lets half B find the
# members by name instead of by tracing every call.
_PRIMITIVES = {"_write_tag_file", "_append_tag_line", "Bag.writer_dir", "open_bag"}

# Method names that are unambiguously a filesystem mutation. `rename`/`replace`
# are deliberately absent from this set and handled below by receiver, because
# `str.replace` is used in this module and a name-only rule would flag it.
_MUTATING_METHODS = {"mkdir", "makedirs", "write_text", "write_bytes", "touch",
                     "unlink", "rmdir", "symlink_to", "hardlink_to", "mknod"}
_MUTATING_MODULE_CALLS = {("os", "rename"), ("os", "replace"), ("os", "remove"),
                          ("os", "rmdir"), ("os", "unlink"), ("os", "mkdir"),
                          ("os", "makedirs"), ("os", "chmod"), ("os", "truncate")}


def _qualified_functions(tree: ast.Module) -> list[tuple[str, ast.AST]]:
    """`(qualified name, node)` for every function and method defined at top level."""
    found: list[tuple[str, ast.AST]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.append((node.name, node))
        elif isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found.append((f"{node.name}.{member.name}", member))
    return found


def _is_write_mode_open(call: ast.Call) -> bool:
    """A builtin `open` or `os.open` requesting anything other than a pure read."""
    func = call.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    if name != "open":
        return False
    # ⚠ ONLY `os.open` TAKES FLAGS. Branching on the attribute alone — which is
    # how this shipped — sent `Path.open("w")` down the flag path, where a mode
    # STRING never matches an `O_*` name, and it returned False. A future
    # primitive written `path.open("w")` would have been invisible to BOTH halves
    # of this file: the exact narrow-predicate failure the docstring above says
    # half A exists to prevent, in the guard that says it. Nothing in `bag.py`
    # uses the idiom today, which is why it was silent rather than wrong.
    if isinstance(func, ast.Attribute) and getattr(func.value, "id", None) == "os":
        flags = ast.dump(call.args[1]) if len(call.args) > 1 else ""
        return any(f in flags for f in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_APPEND", "O_TRUNC"))
    # Everything else spelled `open` takes a mode STRING — but not in the same
    # position: the builtin is `open(path, mode)` and a method is `p.open(mode)`,
    # because the path is the receiver. The first attempt at this fix read
    # `args[1]` for both and left `Path.open("w")` still invisible; the literal
    # control below is what said so, which is the whole reason it exists.
    slot = 0 if isinstance(func, ast.Attribute) else 1
    mode = None
    if len(call.args) > slot and isinstance(call.args[slot], ast.Constant):
        mode = call.args[slot].value
    for keyword in call.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            mode = keyword.value.value
    return isinstance(mode, str) and any(c in mode for c in "wax+")


def _raw_writes(node: ast.AST) -> list[int]:
    """Line numbers of the direct filesystem mutations inside one function."""
    lines: list[int] = []
    for inner in ast.walk(node):
        if not isinstance(inner, ast.Call):
            continue
        func = inner.func
        if _is_write_mode_open(inner):
            lines.append(inner.lineno)
        elif isinstance(func, ast.Attribute):
            receiver = getattr(func.value, "id", None)
            if func.attr in _MUTATING_METHODS or (receiver, func.attr) in _MUTATING_MODULE_CALLS:
                lines.append(inner.lineno)
    return lines


def _called_names(node: ast.AST) -> set[str]:
    names = set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.Call):
            func = inner.func
            names.add(func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", ""))
    return names


def test_every_raw_write_in_bag_py_is_inside_a_declared_primitive() -> None:
    """Half A — what keeps half B's by-name member census honest.

    If a fifth function starts writing to disk directly, the member census below
    would not have to grow to accommodate it and the class would silently widen.
    """
    tree = ast.parse(BAG_PY.read_text(encoding="utf-8"))
    stray = {name: _raw_writes(node)
             for name, node in _qualified_functions(tree)
             if name not in _PRIMITIVES and _raw_writes(node)}
    assert not stray, (
        f"{SCOPE} writes to the filesystem outside the four declared primitives "
        f"{sorted(_PRIMITIVES)}: {stray}. Either route the write through a "
        f"primitive, or add the function to `_PRIMITIVES` here AND to "
        f"`_MUTATORS` below with its classification — a mutator nobody "
        f"classified is a mutator nobody asked 'what happens when it refuses?'")


# --- the positive control on half A's predicate ----------------------------------

# ⚠ DRIVEN AGAINST LITERAL SNIPPETS, NOT AGAINST THE TREE, and the distinction is
# the whole point. A walk over `bag.py` stays green if `_raw_writes` silently
# stops recognising anything — it simply finds no strays and reports success
# forever. `test_a_census_guard_proves_its_own_predicate.py` holds this class for
# every structural guard in this directory; these are this guard's contribution.
# The SATISFYING and the VIOLATING case are both here, because a predicate that
# answers "yes" to everything passes a test that only feeds it violations.

def _writes_in(source: str) -> list[int]:
    node = ast.parse(textwrap.dedent(source)).body[0]
    return _raw_writes(node)


@pytest.mark.parametrize("source,expected,why", [
    ('def f(p):\n    with open(p, "w") as h:\n        h.write("x")\n',
     True, "a builtin open in write mode"),
    ('def f(p):\n    with open(p, "a", encoding="utf-8") as h:\n        h.write("x")\n',
     True, "append mode — how `_append_tag_line` creates the file it appends to"),
    ('def f(p):\n    fd = os.open(p, os.O_WRONLY | os.O_CREAT, 0o600)\n',
     True, "os.open with creating flags — how `_write_tag_file` writes"),
    ('def f(p):\n    os.mkdir(str(p), 0o700)\n',
     True, "a directory created — `open_bag` and `writer_dir` both do this"),
    ('def f(p):\n    p.write_text("x")\n',
     True, "a Path write"),
    ('def f(p):\n    with open(p, encoding="utf-8") as h:\n        return h.read()\n',
     False, "a READ-mode open is not a mutation"),
    ('def f(p):\n    fd = os.open(p, os.O_RDONLY)\n',
     False, "os.open with no creating flag is not a mutation"),
    ('def f(s):\n    return s.replace("a", "b")\n',
     False, "`str.replace` — the false positive this predicate is shaped to avoid, "
            "and it is LIVE in `bag.contained_relpath`"),
    ('def f(p):\n    return p.read_bytes()\n',
     False, "a Path read"),
    ('def f(p):\n    with p.open("w") as h:\n        h.write("x")\n',
     True, "`Path.open` in write mode — a permanent false negative until the "
           "`os`-receiver branch was added, because a mode string never matches "
           "an `O_*` flag name"),
    ('def f(p):\n    with p.open() as h:\n        return h.read()\n',
     False, "`Path.open` with no mode is a read"),
])
def test_the_raw_write_predicate_discriminates(source: str, expected: bool, why: str) -> None:
    """Half A's question, asked of source this tree does not contain."""
    assert bool(_writes_in(source)) is expected, (
        f"`_raw_writes` answered {not expected} for {why}. Half A is what keeps "
        f"the member census honest, so a predicate that has stopped "
        f"discriminating makes every assertion in this file trivially true.")


def test_the_member_predicate_sees_a_call_through_a_primitive() -> None:
    """Half B's question: a member mutates by CALLING a primitive, not by writing."""
    mutating = ast.parse(textwrap.dedent(
        'def f(self):\n    _append_tag_line(self.info_path, "L", "v")\n')).body[0]
    inert = ast.parse(textwrap.dedent(
        'def f(self):\n    return read_tag_file(self.info_path)\n')).body[0]
    bare = {name.split(".")[-1] for name in _MUTATORS}
    assert _called_names(mutating) & bare, (
        "`_called_names` no longer sees a call to a declared primitive, so the "
        "member census below would find nothing and pass vacuously.")
    assert not (_called_names(inert) & bare), (
        "`_called_names` matched a pure reader, so the census would demand a "
        "classification for every function in the module and the list would stop "
        "meaning anything.")


# --- half B: the members ---------------------------------------------------------

# Every function in `bag.py` that mutates — directly, or by calling something
# that does. `TOTAL` means no caller-supplied value can abort it, and carries the
# reason; anything else declares the refusals it can raise, and half C drives
# each one and asserts the bag did not move.
TOTAL = "TOTAL"

_MUTATORS: dict[str, str] = {
    "_write_tag_file": TOTAL,
    "_append_tag_line": "refusable",
    "_set_tag_line": "refusable",
    "Bag.writer_dir": TOTAL,
    "Bag.seal": TOTAL,
    "Bag.redact": "refusable",
    "Bag.mark_incomplete": "refusable",
    "open_bag": "refusable",
}

_TOTAL_REASONS = {
    "_write_tag_file":
        "a primitive: it validates nothing and raises no `BagError`. It is the "
        "thing the refusable members must not reach before they have refused.",
    "Bag.writer_dir":
        "no caller-supplied value is refused — `_SAFE_SEGMENT_RE` rewrites any "
        "name into a slug. Its single `BagError` is ordinal exhaustion, reached "
        "only after 9999 `os.mkdir` calls have EVERY ONE raised `FileExistsError`, "
        "so the refusing path is the path on which nothing was created.",
    "Bag.seal":
        "takes no caller argument. Every value it composes is module-derived — a "
        "byte count, a file count and `utc_now()` — and none can fold a tag line "
        "or fail `_refuse_folded_value`, so it has no refusal to order against.",
}


def test_every_mutator_in_bag_py_is_classified() -> None:
    """A new mutator is red until somebody says what it does when it refuses."""
    tree = ast.parse(BAG_PY.read_text(encoding="utf-8"))
    functions = _qualified_functions(tree)

    # SEEDED FROM THE PRIMITIVES AND CLOSED TO A FIXED POINT, not read off
    # `_MUTATORS`. Asking "does this call something already declared" is one hop:
    # two new functions landing together, where the outer one mutates only by
    # calling the inner one, would surface over two red-fix cycles instead of
    # one. It also made the census depend on the list it audits, which is the
    # shape that lets a declaration go stale without anything noticing.
    found = {name for name, node in functions
             if name in _PRIMITIVES and _raw_writes(node)}
    while True:
        bare = {name.split(".")[-1] for name in found}
        grown = {name for name, node in functions
                 if name not in found and _called_names(node) & bare}
        if not grown:
            break
        found |= grown

    undeclared = found - set(_MUTATORS)
    assert not undeclared, (
        f"{sorted(undeclared)} in {SCOPE} mutate the filesystem and are not in "
        f"`_MUTATORS`. Classify each: `TOTAL` (with a reason in `_TOTAL_REASONS` "
        f"saying why no caller-supplied value can abort it) or `\"refusable\"` "
        f"(with at least one driver in `_REFUSAL_DRIVERS` below). This sweep "
        f"exists because three members of this class shipped, each found one "
        f"pass after the last.")

    gone = set(_MUTATORS) - found
    assert not gone, (
        f"{sorted(gone)} are declared in `_MUTATORS` but no longer mutate in "
        f"{SCOPE}. Remove the row rather than leaving it — a declaration for a "
        f"function that does not exist is what makes the next reader trust the "
        f"list without checking it.")


def test_every_TOTAL_mutator_states_why_it_cannot_refuse() -> None:
    """The reason is the artifact. `TOTAL` with no reason is an unexamined claim."""
    declared_total = {n for n, kind in _MUTATORS.items() if kind == TOTAL}
    assert declared_total == set(_TOTAL_REASONS), (
        f"every `TOTAL` row needs a reason and every reason needs a row. "
        f"Missing reasons: {sorted(declared_total - set(_TOTAL_REASONS))}; "
        f"orphan reasons: {sorted(set(_TOTAL_REASONS) - declared_total)}.")


# --- half C: the property --------------------------------------------------------

FOLDS = "a Journal-Incomplete: true"   # passes a `\n`/`\r` deny-list; splitlines() breaks on it


def _snapshot(path: pathlib.Path) -> dict[str, object]:
    """Every entry under `path`, as bytes for files and `None` for directories."""
    out: dict[str, object] = {}
    for entry in sorted(path.rglob("*")):
        rel = entry.relative_to(path).as_posix()
        out[rel] = None if entry.is_dir() else entry.read_bytes()
    return out


def _redact_setup(root: pathlib.Path):
    bag = open_bag(root, "run")
    (bag.writer_dir("child") / "payload").write_text("SECRET-BEARING ORIGINAL")
    return bag


def _sealed_setup(root: pathlib.Path):
    bag = _redact_setup(root)
    bag.seal()
    return bag


def _tag_file(root: pathlib.Path) -> pathlib.Path:
    return open_bag(root, "run").info_path


# `(member, driver id, setup -> subject, the call that must be REFUSED)`. Every
# refusal a member can raise on a caller-supplied value belongs here; the
# assertion is always the same one, which is what makes this a class check.
_REFUSAL_DRIVERS: list[tuple[str, str, Callable, Callable]] = [
    ("Bag.redact", "a reason that does not survive a round trip",
     _redact_setup, lambda b: b.redact("data/child/payload", FOLDS)),
    ("Bag.redact", "a reason on a SEALED bag, where a refusal also skips the reseal",
     _sealed_setup, lambda b: b.redact("data/child/payload", FOLDS)),
    ("Bag.redact", "a payload path that escapes the bag",
     _redact_setup, lambda b: b.redact("data/../../escape", "why")),
    ("Bag.redact", "a tag file, which is the record OF a redaction",
     _redact_setup, lambda b: b.redact("bag-info.txt", "why")),
    ("Bag.redact", "a payload file that is not there",
     _redact_setup, lambda b: b.redact("data/child/absent", "why")),
    ("Bag.mark_incomplete", "a `why` that does not survive a round trip",
     _redact_setup, lambda b: b.mark_incomplete("the transcript", FOLDS)),
    ("Bag.mark_incomplete", "a `what` that does not survive a round trip",
     _redact_setup, lambda b: b.mark_incomplete(FOLDS, "disk full")),
    ("Bag.mark_incomplete", "a second gap on a bag already flagged",
     lambda root: _flagged(root), lambda b: b.mark_incomplete("the reply", FOLDS)),
    ("open_bag", "an `info` VALUE that does not survive a round trip",
     lambda root: root, lambda root: open_bag(root, "fresh", info={"Journal-Worktree": FOLDS})),
    ("open_bag", "an `info` LABEL that forges a second record",
     lambda root: root, lambda root: open_bag(root, "fresh", info={FOLDS: "x"})),
    ("open_bag", "an `info` label this module owns",
     lambda root: root, lambda root: open_bag(root, "fresh", info={"External-Identifier": "x"})),
    ("open_bag", "a run id outside the permitted set",
     lambda root: root, lambda root: open_bag(root, "fresh\nJournal-Incomplete: true")),
    ("open_bag", "a run id that is a relative segment",
     lambda root: root, lambda root: open_bag(root, "..")),
    ("_append_tag_line", "a value that does not survive a round trip",
     _tag_file, lambda p: bagmod._append_tag_line(p, "Journal-Note", FOLDS)),
    ("_set_tag_line", "a value that does not survive a round trip",
     _tag_file, lambda p: bagmod._set_tag_line(p, "Payload-Oxum", FOLDS)),
]


def _flagged(root: pathlib.Path):
    bag = _redact_setup(root)
    bag.mark_incomplete("the transcript", "disk full")
    return bag


def test_every_refusable_mutator_has_at_least_one_driver() -> None:
    """A member declared refusable and never driven is a row, not a check."""
    refusable = {n for n, kind in _MUTATORS.items() if kind != TOTAL}
    driven = {member for member, _, _, _ in _REFUSAL_DRIVERS}
    assert refusable == driven, (
        f"undriven refusable members: {sorted(refusable - driven)}; drivers for "
        f"members not declared refusable: {sorted(driven - refusable)}.")


@pytest.mark.parametrize(
    "member,description,setup,call",
    _REFUSAL_DRIVERS,
    ids=[f"{m}: {d}" for m, d, _, _ in _REFUSAL_DRIVERS])
def test_a_refused_mutation_leaves_the_bag_byte_identical(
        tmp_path: pathlib.Path, member: str, description: str,
        setup: Callable, call: Callable) -> None:
    """THE class property: a refusal aborts, it does not half-apply.

    Snapshot taken AFTER setup, so what is compared is exactly the state the
    refused call was handed.
    """
    root = tmp_path / "journal"
    root.mkdir()
    subject = setup(root)

    before = _snapshot(root)
    with pytest.raises(BagError):
        call(subject)
    after = _snapshot(root)

    changed = sorted(set(before) ^ set(after)) or sorted(
        k for k in before if before[k] != after[k])
    assert before == after, (
        f"{member} refused {description!r} and CHANGED THE BAG: {changed}. A "
        f"refusal must be all-or-nothing — the value was rejected, so nothing "
        f"the caller asked for happened, so nothing on disk may have moved. "
        f"Validate the refusable value BEFORE the first write, not after it.")
