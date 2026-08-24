"""Phase 9 r1 and r2 — one naming authority, and no entrypoint is it.

WHY THIS FILE EXISTS RATHER THAN A LINE IN THE BAG SWEEP. `test_every_parent_
opens_a_run_bag.py` asks whether an entrypoint opens a bag; this asks where the
NAME it opens it under came from. They are different properties and the phase
doc measured that the first cannot see the second: `_missing_bag_open` walks the
AST for any `ast.Call` whose callee is named `open_run_bag` and asserts NOTHING
WHATEVER about its arguments. Converting three of eleven entrypoints from
`run_id=mint_run_id()` to a supplied name leaves that sweep GREEN — which is
exactly the *two naming authorities live at the same time* state r1 exists to
end, arriving through the guard that was supposed to prevent it.

  Worse, and fixed in the same change: that sweep's own failure message told the
  next author to write `journal.open_run_bag(run_id=journal.mint_run_id(), …)`.
  A guard teaching the shape its own phase forbids is not a neutral omission —
  it is an instruction, read at the one moment somebody is looking for one.

THE PROPERTY, IN THREE PARTS, because each fails differently:

  1. NO ENTRYPOINT NAMES THE MINTING AUTHORITY. Not calls — NAMES. An import
     that is never called is a half-done migration waiting for someone to
     finish it the wrong way, and it costs nothing to refuse.
  2. NOTHING IS MINTED INLINE AT THE CALL SITE. `run_id=` must be a plain name
     or attribute, never a call. This is what catches an author who bypasses
     the authority entirely and writes `run_id=uuid.uuid4().hex`.
  3. EVERY ENTRYPOINT DECLARES THE INPUT. A run id cannot arrive from outside a
     process that has no argument to receive it on, so an entrypoint missing
     `add_identity_arguments` is one whose name can only ever be minted.

⚠ WHAT THIS DOES NOT COVER, stated here and in the failure text:

  * IT IS A SOURCE GREP. It proves the shape is WRITTEN, not that the value is
    threaded correctly at runtime — the behavioural half is
    `test_dispatch_identity.py`, which drives the boundary itself.
  * IT SAYS NOTHING ABOUT WHETHER r2 IS SATISFIED. r2 stays UNCHECKED in the
    phase doc until the Temporal port agrees the name's shape, and no test can
    close it, because what is missing is a decision in another component and
    not code. This holds the local half: the mechanism is built, and it cannot
    silently un-build itself.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from journal_entrypoint_facts import (ENTRYPOINTS_DIR, REPO_ROOT,  # noqa: E402
                                      entrypoints as _entrypoints)

# The one function in this fleet that names a run, and the helper that declares
# the argument the name arrives on. Both are single-sourced: `mint_run_id` in
# `modules/journal/journal_activities.py`, `add_identity_arguments` in
# `scripts/dispatch_identity.py`.
MINTING_AUTHORITY = "mint_run_id"
IDENTITY_ARGUMENTS = "add_identity_arguments"

BAG_OPEN = "open_run_bag"

# The dispatch boundary every entrypoint has to route THROUGH, and the flag
# whose early return it must sit after. Declaring the arguments is not the same
# property as using them — see the two predicates below.
IDENTITY_BOUNDARY = "resolve_identity"
DRY_RUN_FLAG = '"--dry-run"'

# The dispatch boundary that is ALLOWED to mint — the client side of a dispatch,
# which runs once per invocation and is not replayed code. Pinned as a set of one
# so that a second minting site anywhere in the live tree fails this file rather
# than quietly becoming a second authority, which is the failure r1 names.
PERMITTED_MINTING_SITES = {"dispatch_identity.py"}

LIVE_TREE = REPO_ROOT / "scripts" / "workflows" / "temporal"


def _names_used(tree: ast.AST) -> set[str]:
    """Every identifier the source MENTIONS, by AST — attributes included.

    `journal.mint_run_id()` is an `ast.Attribute`; `mint_run_id()` after a
    `from … import` is an `ast.Name`; a bare `mint_run_id` passed as a value is
    also an `ast.Name`. All three are the defect, so all three are collected.

    READ BY AST AND NOT BY SUBSTRING, for the reason `_missing_bag_open` states:
    the sibling preflight sweep shipped a substring check, and a COMMENT naming
    the forbidden helper satisfied it. This file's own header names
    `mint_run_id` repeatedly, so a grep here would report on its documentation.
    """
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            # BOTH THE ALIAS AND THE ORIGINAL, and the original is the one that
            # matters. `from … import mint_run_id as m` binds only `m`, so a
            # reader collecting `asname or name` records `m` and never learns
            # which function it points at — the authority is reached and the
            # guard sees nothing. Found by this file's own parametrised control,
            # which is why that row exists.
            for alias in node.names:
                used.add(alias.name)
                if alias.asname:
                    used.add(alias.asname)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                used.update(alias.name.split("."))
    return used


def _mints_its_own_name(directory: pathlib.Path) -> list[str]:
    """Entrypoints that so much as NAME the minting authority."""
    return [p.name for p in _entrypoints(directory)
            if MINTING_AUTHORITY in _names_used(
                ast.parse(p.read_text(), filename=str(p)))]


def _run_id_minted_inline(directory: pathlib.Path) -> list[str]:
    """Entrypoints whose `open_run_bag(run_id=…)` argument is a CALL.

    A call is a value made HERE. A name or an attribute is a value that arrived
    from somewhere, which is the whole property — and it forces the id to exist
    as a binding before the bag opens, so the two-line shape is the point rather
    than a style preference.

    ⚠ THE TEST IS "NO CALL ANYWHERE IN THE SUBTREE", NOT "THE TOP NODE IS NOT A
    CALL", and the difference is a live bypass rather than a refinement. This
    read `isinstance(kw.value, (ast.Name, ast.Attribute))` and passed
    `uuid.uuid4().hex` — which parses as `Attribute(value=Call(...), attr='hex')`,
    an Attribute whose value is minted one node down. The control below caught
    it. `identity.run_id` is `Attribute(value=Name(...))` and contains no call,
    which is exactly the line the property wants drawn.
    """
    offenders = []
    for path in _entrypoints(directory):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if (getattr(node.func, "id", None) != BAG_OPEN
                    and getattr(node.func, "attr", None) != BAG_OPEN):
                continue
            for kw in node.keywords:
                if kw.arg != "run_id":
                    continue
                made_here = any(isinstance(n, ast.Call)
                                for n in ast.walk(kw.value))
                if made_here or not isinstance(kw.value, (ast.Name, ast.Attribute)):
                    offenders.append(f"{path.name}:{node.lineno} "
                                     f"(run_id={ast.unparse(kw.value)})")
    return offenders


def _bypassing_the_identity_boundary(directory: pathlib.Path) -> list[str]:
    """Entrypoints that never NAME `resolve_identity`.

    ⚠ THIS IS THE PROPERTY r4's WORD "ENFORCED" RESTS ON, and it had no guard.
    MEASURED on this branch: rewriting one entrypoint to declare the flags and
    then hand `args.run_id` straight to `open_run_bag` left the ENTIRE unit suite
    green — 2278 passed. Every other check in this file is satisfied by that
    shape, because the id still arrives from outside and nothing mints.

    ⚠ IT ASKS FOR A CALL, NOT FOR THE NAME, and the difference was measured the
    same way. A first version used `_names_used`, which collects imported names —
    so `from dispatch_identity import resolve_identity` satisfied it, and the
    bypass mutation above stayed GREEN because the half-migrated file kept its
    import. That is the realistic shape of a half-migration: an author rewrites
    the call and leaves the import line alone.

    What is lost is everything the boundary alone does: `--writer` with no
    `--run-id` stops being refused, and an invocation passing BOTH is recorded as
    the run rather than as a member of one — which is `A standalone child is the
    case the bag was never designed for`'s first wrong answer, reached silently,
    by an entrypoint that looks migrated. Declaring the arguments proves a name
    can arrive; only calling the boundary proves it is READ.
    """
    offenders = []
    for path in _entrypoints(directory):
        tree = ast.parse(path.read_text(), filename=str(path))
        called = any(isinstance(node, ast.Call)
                     and (getattr(node.func, "id", None) == IDENTITY_BOUNDARY
                          or getattr(node.func, "attr", None) == IDENTITY_BOUNDARY)
                     for node in ast.walk(tree))
        if not called:
            offenders.append(path.name)
    return offenders


def _resolving_before_the_dry_run_return(directory: pathlib.Path) -> list[str]:
    """Entrypoints declaring `--dry-run` whose boundary call is not after it.

    A dry run states *nothing invoked, nothing posted*, and `resolve_identity`
    mints a name and PRINTS it when none was supplied — so a preview that reaches
    it announces a run id for a run that will never exist, and an operator
    retrying with that name creates the bag the dry run promised not to.

    It is the same exemption that keeps a dry run from opening a bag, and it was
    stated only in `resolve_identity`'s docstring. This package's own thesis is
    that a rule kept as prose gets violated by the next edit; all seven
    `--dry-run` entrypoints conform today, which is exactly when the guard is
    cheap to add.

    LINE ORDER, NOT DATA FLOW, and the limit is named rather than implied: this
    compares the first `--dry-run`-guarded early return against the first
    `resolve_identity` call. A file that reached the boundary through a helper
    called before the return would pass. That shape does not exist here — the
    boundary is called inline in all eleven — and the check for THAT is
    `_bypassing_the_identity_boundary` above.
    """
    offenders = []
    for path in _entrypoints(directory):
        source = path.read_text()
        if DRY_RUN_FLAG not in source:
            continue
        lines = source.splitlines()
        returns = [i for i, line in enumerate(lines)
                   if "dry" in line and line.lstrip().startswith(("if ", "return "))]
        calls = [i for i, line in enumerate(lines) if f"{IDENTITY_BOUNDARY}(" in line
                 and not line.lstrip().startswith(("#", "*"))]
        if not returns or not calls:
            offenders.append(f"{path.name} (dry-run branch or boundary call not "
                             f"located: returns={len(returns)} calls={len(calls)})")
            continue
        if min(calls) < min(returns):
            offenders.append(f"{path.name} (resolve_identity at line {min(calls) + 1}, "
                             f"dry-run branch at line {min(returns) + 1})")
    return offenders


def _missing_identity_arguments(directory: pathlib.Path) -> list[str]:
    """Entrypoints that declare no way for a name to arrive."""
    return [p.name for p in _entrypoints(directory)
            if IDENTITY_ARGUMENTS not in _names_used(
                ast.parse(p.read_text(), filename=str(p)))]


# --- the sweep -------------------------------------------------------------------

def test_no_entrypoint_MINTS_the_run_id_it_opens_a_bag_under() -> None:
    """THE REQUIREMENT (r2's local half). A half-done migration goes red HERE."""
    discovered = _entrypoints(ENTRYPOINTS_DIR)
    assert discovered, f"no entrypoints discovered under {ENTRYPOINTS_DIR} — the sweep is inert"

    offenders = _mints_its_own_name(ENTRYPOINTS_DIR)
    assert not offenders, (
        f"these entrypoints name the run-id minting authority: {offenders}.\n"
        f"A name generated inside the process that is supposed to have RECEIVED "
        f"it is a fresh name on every at-least-once retry and a different name "
        f"on a replayed second pass — one run, an unbounded fan of names, filed "
        f"as several runs (Persistent Memory Protocol Phase 9 r2).\n"
        f"REMEDY: take the name from the argument it arrives on —\n"
        f"    identity = resolve_identity(argv)\n"
        f"    journal.open_run_bag(run_id=identity.run_id, writer=identity.writer, …)\n"
        f"and declare the arguments with `add_identity_arguments(<parser>)`. "
        f"`scripts/dispatch_identity.py` is the client-side boundary and the "
        f"only place permitted to mint.\n"
        f"SCOPE OF THIS SWEEP: {ENTRYPOINTS_DIR.relative_to(REPO_ROOT)}/run_*.py "
        f"and nothing else. A run started from anywhere else is INVISIBLE here.")


def test_no_entrypoint_mints_a_run_id_INLINE_by_any_other_route() -> None:
    """The authority is not the only way to make a name — `uuid4().hex` is one too.

    Part 1 of this file refuses the authority by name, which an author bypasses
    simply by not using it. This refuses the SHAPE: whatever `run_id=` is given
    must be a value that already existed.
    """
    offenders = _run_id_minted_inline(ENTRYPOINTS_DIR)
    assert not offenders, (
        f"these entrypoints compute the run id AT the bag-open call: {offenders}. "
        f"`run_id=` must be a plain name or attribute — a value that arrived "
        f"from outside this process, not one made at the call site. Refusing "
        f"only `mint_run_id` by name would leave `run_id=uuid.uuid4().hex` "
        f"green, which is the same defect through a different spelling.")


def test_every_entrypoint_DECLARES_the_argument_a_name_arrives_on() -> None:
    """A name cannot arrive from outside a process with nowhere to receive it.

    This is the half that catches an entrypoint added AFTER the migration. It
    would not name `mint_run_id` (nothing tells it to any more) and it would not
    mint inline, so both checks above pass it — while it silently has no way to
    be handed a run id at all, and its `resolve_identity` mints on every run.
    """
    missing = _missing_identity_arguments(ENTRYPOINTS_DIR)
    assert not missing, (
        f"these entrypoints declare no identity arguments: {missing}. Call "
        f"`add_identity_arguments(<parser>)` where the parser is built, so "
        f"`--run-id` and `--writer` exist. Without them the name can only ever "
        f"be minted here, which is what Phase 9 r2 forbids — and the failure is "
        f"SILENT, because minting is also the correct behaviour when nothing "
        f"supplies a name.")


def test_every_entrypoint_ROUTES_THROUGH_the_identity_boundary() -> None:
    """r4: the discriminator is not merely declared, it is READ.

    The test above proves a name CAN arrive. This proves the entrypoint looks at
    it — which is where `--writer` with no `--run-id` is refused, and where a
    member of a run is distinguished from the run itself. An entrypoint that
    declares the flags and reads `args.run_id` directly passes every other check
    in this file and loses both.
    """
    bypassing = _bypassing_the_identity_boundary(ENTRYPOINTS_DIR)
    assert not bypassing, (
        f"these entrypoints never call `{IDENTITY_BOUNDARY}`: {bypassing}. "
        f"Declaring `--run-id`/`--writer` and then reading the parsed values "
        f"directly is NOT the migration: the boundary is what validates the "
        f"name, what refuses a `--writer` with no run to join, and what mints "
        f"and announces when nothing supplied a name.\n"
        f"  write: `identity = resolve_identity(argv)` and pass "
        f"`run_id=identity.run_id, writer=identity.writer`.")


def test_no_DRY_RUN_entrypoint_resolves_an_identity_before_its_early_return() -> None:
    """The `--dry-run` exemption, held by a check rather than by a docstring.

    A dry run that reaches `resolve_identity` announces a minted run id for a run
    that never happens. The rule was written in one docstring; this is the sweep
    that keeps the next edit from moving the call two lines up.
    """
    offenders = _resolving_before_the_dry_run_return(ENTRYPOINTS_DIR)
    assert not offenders, (
        f"these `--dry-run` entrypoints resolve an identity too early: "
        f"{offenders}. A dry run states 'nothing invoked, nothing posted', and "
        f"`resolve_identity` mints and PRINTS a name when none was supplied — so "
        f"a preview would announce a run id an operator can then retry into a "
        f"real bag. Move the call below the dry-run early return, which is the "
        f"same exemption that keeps a dry run from opening a bag.")


def test_the_minting_authority_has_exactly_ONE_caller_in_the_live_tree() -> None:
    """r1: exactly one authority names a run, and one place invokes it.

    THE POPULATION IS DISCOVERED, NOT LISTED. Every `.py` under the live V2 tree
    outside its own package and outside the tests. A second minting site is how
    "the run id" stops resolving to one thing — measured in this repo already,
    where re-enumerating archived run logs returned files named for scripts that
    no longer exist, because two naming authorities were live at once.
    """
    callers = []
    for path in sorted(LIVE_TREE.rglob("*.py")):
        if "__pycache__" in path.parts or "tests" in path.parts:
            continue
        if path.parts[-2:] == ("journal", "journal_activities.py"):
            continue          # the authority's own definition
        if path.name == "__init__.py":
            continue          # re-export, not a call
        tree = ast.parse(path.read_text(), filename=str(path))
        if MINTING_AUTHORITY in _names_used(tree):
            callers.append(path.name)

    assert set(callers) == PERMITTED_MINTING_SITES, (
        f"the run-id minting authority is named by {sorted(callers)}; exactly "
        f"{sorted(PERMITTED_MINTING_SITES)} may name it.\n"
        f"A second minting site is a second naming authority, and a value that "
        f"means two things is not fixed by documenting both meanings (Phase 9 "
        f"r1). If a new dispatch boundary genuinely needs to mint, add it here "
        f"WITH the reason it is a client side rather than work that gets "
        f"retried — that distinction is the whole argument.")


# --- non-vacuity -----------------------------------------------------------------

def test_this_sweep_EXAMINED_something() -> None:
    """A sweep whose predicate found nothing satisfies every assertion above.

    Both counts, because they fail independently: the entrypoint population can
    drift to zero, and `_names_used` can stop seeing identifiers at all while
    the population is intact.
    """
    discovered = _entrypoints(ENTRYPOINTS_DIR)
    assert len(discovered) >= 10, (
        f"only {len(discovered)} entrypoints discovered; this fleet has eleven "
        f"and is about to have twenty. The predicate has drifted from the tree.")

    names = _names_used(ast.parse(discovered[0].read_text()))
    assert BAG_OPEN in names, (
        f"`{BAG_OPEN}` was not among the {len(names)} identifiers read out of "
        f"{discovered[0].name}, which certainly calls it. `_names_used` has "
        f"stopped seeing identifiers, so every assertion in this file is "
        f"passing over an empty set.")


# --- the negative controls -------------------------------------------------------
#
# THE FIXTURES ARE SELF-CONTAINED AND NOT THIS REPO'S TREE. A control sharing a
# fixture with the code under mutation over-fires, and the over-firing reads as a
# stronger guard rather than as a defect in the control.

def test_the_sweep_FAILS_on_a_HALF_DONE_migration(tmp_path: pathlib.Path) -> None:
    """THE DEFECT THIS FILE WAS WRITTEN FOR, demonstrated rather than asserted.

    Three files: two converted, one not. The existing bag sweep reports zero
    offenders here — all three call `open_run_bag` — which is precisely why that
    sweep could not hold this property. This must name exactly the unconverted
    one, so the assertion DISCRIMINATES rather than merely going red.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_converted.py").write_text(
        "from dispatch_identity import add_identity_arguments, resolve_identity\n"
        "def main(argv=None):\n"
        "    identity = resolve_identity(argv)\n"
        "    open_run_bag(run_id=identity.run_id, writer=identity.writer)\n")
    (scripts / "run_also_converted.py").write_text(
        "from dispatch_identity import add_identity_arguments, resolve_identity\n"
        "def main(argv=None):\n"
        "    ident = resolve_identity(argv)\n"
        "    journal.open_run_bag(run_id=ident.run_id, writer=ident.writer)\n")
    (scripts / "run_not_yet.py").write_text(
        "from dispatch_identity import add_identity_arguments\n"
        "def main(argv=None):\n"
        "    journal.open_run_bag(run_id=journal.mint_run_id(), writer=None)\n")

    assert len(_entrypoints(scripts)) == 3, "the fixture itself must be discovered"
    assert _mints_its_own_name(scripts) == ["run_not_yet.py"], (
        "the sweep must name exactly the unconverted file — flagging all three "
        "would pass a red/green control while being useless, and flagging none "
        "is the state the bag sweep is actually in")


def test_the_INLINE_check_catches_a_mint_that_avoids_the_authority(
        tmp_path: pathlib.Path) -> None:
    """The bypass the by-name check cannot see, pinned separately.

    `run_uuid.py` never names `mint_run_id`, so part 1 passes it. Its run id is
    still made at the call site. Two conforming files alongside it, so the
    assertion has to discriminate.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_uuid.py").write_text(
        "import uuid\n"
        "def main(argv=None):\n"
        "    journal.open_run_bag(run_id=uuid.uuid4().hex, writer=None)\n")
    (scripts / "run_name.py").write_text(
        "def main(argv=None):\n"
        "    rid = resolve_identity(argv).run_id\n"
        "    journal.open_run_bag(run_id=rid, writer=None)\n")
    (scripts / "run_attr.py").write_text(
        "def main(argv=None):\n"
        "    identity = resolve_identity(argv)\n"
        "    journal.open_run_bag(run_id=identity.run_id, writer=None)\n")

    assert _mints_its_own_name(scripts) == [], (
        "none of these names the authority — if this fails, the control is not "
        "isolating the property it claims to")
    offenders = _run_id_minted_inline(scripts)
    assert [o.split(":")[0] for o in offenders] == ["run_uuid.py"], (
        f"the inline check must name exactly the file that computes its id at "
        f"the call site; got {offenders}")


def test_the_ARGUMENT_check_catches_an_entrypoint_that_can_never_BE_told(
        tmp_path: pathlib.Path) -> None:
    """The post-migration defect: correct-looking, and unable to receive a name.

    `run_silent.py` mints nothing and computes nothing inline — both other
    checks pass it. It also declares no `--run-id`, so no caller can ever hand
    it one and every invocation is a fresh run.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_silent.py").write_text(
        "def main(argv=None):\n"
        "    identity = resolve_identity(argv)\n"
        "    journal.open_run_bag(run_id=identity.run_id, writer=identity.writer)\n")
    (scripts / "run_declared.py").write_text(
        "from dispatch_identity import add_identity_arguments, resolve_identity\n"
        "def main(argv=None):\n"
        "    add_identity_arguments(p)\n"
        "    identity = resolve_identity(argv)\n"
        "    journal.open_run_bag(run_id=identity.run_id, writer=identity.writer)\n")

    assert _mints_its_own_name(scripts) == [], "neither file mints"
    assert _run_id_minted_inline(scripts) == [], "neither file mints inline"
    assert _missing_identity_arguments(scripts) == ["run_silent.py"], (
        "the argument check must name exactly the entrypoint with nowhere for a "
        "name to arrive — this is the case the other two checks cannot see")


@pytest.mark.parametrize("snippet,expected", [
    ("journal.mint_run_id()", True),
    ("mint_run_id()", True),
    ("from modules.journal import mint_run_id", True),
    ("from modules.journal import mint_run_id as m", True),
    ("import modules.journal.mint_run_id", True),
    ("helper(mint_run_id)", True),
    ("identity = resolve_identity(argv)", False),
    ("journal.open_run_bag(run_id=identity.run_id)", False),
    ("# see mint_run_id for why the name arrives from outside", False),
    ('"""This entrypoint is named by mint_run_id elsewhere."""', False),
])
def test_the_NAME_PREDICATE_answers_correctly_on_a_LITERAL_SNIPPET(
        snippet: str, expected: bool) -> None:
    """THE POSITIVE CONTROL, in-process, with no file and no tree walk.

    `test_a_census_guard_proves_its_own_predicate` requires this of every guard
    that reads the production tree, and its argument is why it is not optional: a
    predicate that has silently stopped seeing identifiers satisfies every
    assertion in this file AND its vacuity floor, because both are computed from
    the same empty set. A snippet with a known answer is the only thing that
    cannot be satisfied that way.

    The last two rows are the substring bug ruled out by construction: a comment
    and a docstring that both NAME the authority and neither of which reaches it.
    A grep-based version of this guard reports both as offenders, and this file's
    own header would make it report itself.
    """
    assert (MINTING_AUTHORITY in _names_used(ast.parse(snippet))) is expected


@pytest.mark.parametrize("spelling,source", [
    ("attribute call", "journal.mint_run_id()"),
    ("bare call", "mint_run_id()"),
    ("imported name", "from modules.journal import mint_run_id"),
    ("passed as a value", "helper(mint_run_id)"),
    ("aliased import", "from modules.journal import mint_run_id as m"),
])
def test_every_SPELLING_of_reaching_the_authority_is_seen(
        tmp_path: pathlib.Path, spelling: str, source: str) -> None:
    """Four ways to reach one function, and a narrow reader sees one of them.

    The aliased import is the interesting row: `import … as m` binds `m`, and a
    checker looking only at bound names would miss that the ORIGINAL was named.
    `_names_used` collects `alias.name` as well, which is why it is there.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_x.py").write_text(f"def main():\n    {source}\n"
                                      if not source.startswith("from")
                                      else f"{source}\ndef main():\n    pass\n")
    assert _mints_its_own_name(scripts) == ["run_x.py"], (
        f"the {spelling} spelling of reaching the minting authority was not "
        f"seen; a guard that catches three of four spellings catches none")


# --- controls for the two boundary predicates -----------------------------------
#
# Each of the two predicates added above gets a fixture it is KNOWN to split, for
# the reason every other control in this file exists: the live tree conforms, so a
# predicate that has silently stopped discriminating passes the sweep, the
# staleness check and the vacuity floor from the same empty result.

def _fixture(tmp_path: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name, body in files.items():
        (scripts / name).write_text(body)
    return scripts


def test_the_BOUNDARY_check_catches_an_entrypoint_that_reads_argv_directly(
        tmp_path: pathlib.Path) -> None:
    """The exact half-migration that left the whole suite green before this check.

    `run_bypass.py` is not a strawman — it declares the arguments, takes the name
    from outside, and mints nothing, so `_mints_its_own_name`,
    `_run_id_minted_inline` and `_missing_identity_arguments` ALL pass it. Only
    this predicate separates it from `run_ok.py`.
    """
    scripts = _fixture(tmp_path, {
        "run_ok.py":
            "from dispatch_identity import add_identity_arguments, resolve_identity\n"
            "def main(argv=None):\n"
            "    add_identity_arguments(parser)\n"
            "    identity = resolve_identity(argv)\n"
            "    journal.open_run_bag(run_id=identity.run_id, writer=identity.writer)\n",
        "run_bypass.py":
            # THE IMPORT IS LEFT IN ON PURPOSE — it is what a real half-migration
            # looks like, and a name-based predicate is green on exactly this file.
            "from dispatch_identity import add_identity_arguments, resolve_identity\n"
            "def main(argv=None):\n"
            "    add_identity_arguments(parser)\n"
            "    args = parser.parse_args(argv)\n"
            "    journal.open_run_bag(run_id=args.run_id, writer=None)\n",
    })
    assert _bypassing_the_identity_boundary(scripts) == ["run_bypass.py"]
    assert _missing_identity_arguments(scripts) == [], (
        "the control's premise: the bypassing file passes the DECLARATION check, "
        "which is why declaring the arguments is not the same property as using "
        "them")
    assert _mints_its_own_name(scripts) == [] and _run_id_minted_inline(scripts) == [], (
        "the control's second premise: it passes both minting checks too")


def test_the_DRY_RUN_ORDER_check_catches_a_boundary_call_moved_too_early(
        tmp_path: pathlib.Path) -> None:
    """Three files, three answers — the two that must not fire, and the one that must.

    `run_none.py` is the row that keeps the predicate from degenerating into "any
    entrypoint whose boundary call is near the top": four of eleven entrypoints
    declare no `--dry-run` at all and must never be reported.
    """
    scripts = _fixture(tmp_path, {
        "run_after.py":
            'p.add_argument("--dry-run", action="store_true")\n'
            "def main(argv=None):\n"
            "    if dry:\n"
            "        return _dry_run(task)\n"
            "    identity = resolve_identity(argv)\n",
        "run_before.py":
            'p.add_argument("--dry-run", action="store_true")\n'
            "def main(argv=None):\n"
            "    identity = resolve_identity(argv)\n"
            "    if dry:\n"
            "        return _dry_run(task)\n",
        "run_none.py":
            "def main(argv=None):\n"
            "    identity = resolve_identity(argv)\n",
    })
    offenders = _resolving_before_the_dry_run_return(scripts)
    assert len(offenders) == 1 and offenders[0].startswith("run_before.py"), (
        f"expected exactly `run_before.py` to be reported, got {offenders}")
