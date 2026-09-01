"""Requirement 11 — a run that does not open a bag goes RED, not journal-less.

WHY A SWEEP AND NOT A PLACEMENT. Putting bag-open in the activities layer
delivers tidiness, not a guarantee: nothing in an orchestrator forces a workflow
to invoke a particular activity first, and a workflow that omits the call simply
omits it. As a library each entrypoint is asked to remember to call, the
protocol is OPTIONAL — and optional is how three controls in this fleet have
already failed. An observable shipped with no reader. A rule governing three
event types stated inside one function's docstring. A completion gate one runner
had and another did not. Each was correct as written, each was skippable, and
each was skipped.

Requirement 9's refuse-to-start cannot supply it either, and the reason is worth
stating because it reads like it should: **r9 fires only once bag-open has
ALREADY been invoked.** An entrypoint that never calls it never reaches r9. Two
guards, two failures, neither substituting for the other.

THE SHAPE IS `test_every_entrypoint_actually_calls_preflight`, which this repo
already ships one directory over and which was written for the same class of
defect — six of seven entrypoints having dropped a precondition. That test's
discovery predicate is reused deliberately rather than re-derived: two sweeps
disagreeing about what an entrypoint IS would leave a file each thought the
other covered.

WHY THE SWEPT UNIT IS THE ENTRYPOINT AND NOT THE WORKFLOW MODULE. This tree has
two defensible readings of "parent" and they do not agree: `test_isolation_
invariants.py` classifies six workflow modules as parents by `act.worktree_add(`,
while ELEVEN entrypoints are 1:1 with a run. FIVE of those eleven call
`worktree_add` themselves and hand the workflow module an already-cut worktree,
and three more hand off by name to a module that cuts one, so a bag opened inside
the workflow module would fire AFTER a worktree existed on disk in NINE of the
eleven — and r9 says the run *does not start*. The
entrypoint is where `preflight` already lives, for exactly this reason. At port
time the entrypoint becomes a client that starts the workflow on a task queue,
and the call moves to the workflow's first activity invocation; this predicate
moves with it.

⚠ WHAT THIS DOES NOT COVER, stated here AND in the failure message because an
enumerating test is only as good as its discovery predicate:

  * A run initiated from outside `scripts/workflows/temporal/scripts/run_*.py`
    is invisible to this sweep. That is the swept scope and it is named in the
    failure text so a reader hitting it learns the boundary rather than assuming
    there is none.
  * It says nothing about whether any individual write is EMITTED. An entrypoint
    that opens a bag and then writes to a store through a path nobody wrapped
    still produces a gap; Phase 4's rebuild test is the guard for that class.
  * It does not reach model-issued writes at all. When the child itself runs
    `gh pr comment` there is no fleet call site to wrap, and that half is
    Phase 3's post-exit harvest.
  * A source grep proves the CALL IS WRITTEN, not that it EXECUTES. A call
    placed inside an unreachable branch would pass. `test_the_call_precedes_the
    _first_side_effect` below closes the most likely version of that by ORDER;
    proving execution needs the integration tier.
  * `--dry-run` IS A DELIBERATE EXEMPTION, and it is the concrete instance of the
    point above rather than a hypothetical one: Seven of the eleven entrypoints
    return from their dry-run branch before reaching bag-open, so on that path
    the call is present and does not run. That is intended — a dry run states
    "nothing invoked, nothing posted", and creating a directory would falsify it
    and litter the journal with empty bags from previews. No run happens on that
    path, so no run lacks a bag. Stated here because every other boundary of
    this guard is stated, and an unstated exemption is the one a later reader
    mistakes for an oversight. (The other four have no `--dry-run` at all, which
    is why this said EIGHT for four passes and no reading of the tree supported
    it; `test_journal_prose_figures_are_DERIVED.py` now derives the number.)
  * The ORDERING check covers nine of eleven; the two it cannot reach are
    named in `_ORDERING_UNCOVERED` below, with why.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# THE ENTRYPOINT POPULATION LIVES IN ONE MODULE, imported by both guards that
# need it. `test_journal_prose_figures_are_DERIVED` derives its counts from the
# same discovery this file asserts against, and a second copy of "which files
# are the parents" would be the defect both exist to catch, one layer up. A test
# module may not import a test module (`test_test_tree_hygiene`), so the shared
# names sit in a helper — the Testing Standard's own remedy. Aliased to the
# private spellings this file already uses, so the assertions below read
# unchanged.
from journal_entrypoint_facts import (BAG_OPEN, ENTRYPOINTS_DIR,  # noqa: E402
                                      NON_STARTING_FILES,
                                      ORDERING_UNCOVERED as _ORDERING_UNCOVERED,
                                      REPO_ROOT,
                                      SIDE_EFFECT_ATTRS as _SIDE_EFFECT_ATTRS,
                                      entrypoints as _entrypoints,
                                      shim_target,
                                      side_effect_lines as _side_effect_lines,
                                      unclassified)


def _modules_imported_by(paths: list[Path]) -> set[str]:
    """Every module name actually IMPORTED by the given files, by AST.

    Both import shapes, and the dotted tail of each: `import a.b.c` contributes
    `a`, `a.b` and `c`; `from a.b import c as d` contributes `a`, `a.b` and `c`.
    The bare tail is what callers compare a module's `stem` against.
    """
    names: set[str] = set()
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.update(alias.name.split("."))
                    names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.update(node.module.split("."))
                    names.add(node.module)
                for alias in node.names:
                    names.add(alias.name)
    return names


def _missing_bag_open(directory: Path) -> list[str]:
    """Entrypoints under `directory` that never call `open_run_bag`.

    READ BY AST, NOT BY SUBSTRING, and the sibling sweep in `test_preflight.py`
    is why: its first version was a substring check, and a mutation that put the
    forbidden block back stayed GREEN because a COMMENT mentioning the helper
    satisfied the grep. A guard reading a region that includes its own
    documentation reports on the documentation — silently. This file's comments
    name `open_run_bag` repeatedly, so a substring check here would be that bug
    reintroduced knowingly.
    """
    missing = []
    for path in _entrypoints(directory):
        tree = ast.parse(path.read_text(), filename=str(path))
        calls = any(
            isinstance(node, ast.Call)
            and (getattr(node.func, "id", None) == BAG_OPEN
                 or getattr(node.func, "attr", None) == BAG_OPEN)
            for node in ast.walk(tree))
        if not calls:
            missing.append(path.name)
    return missing


def _bag_open_outside_the_handler(directory: Path) -> list[str]:
    """Entrypoints whose `open_run_bag` is not inside a `RuntimeError` handler.

    ⚠ THE MESSAGE BELOW ALREADY DEMANDED THIS AND NOTHING CHECKED IT. The sweep
    above asks that the call EXISTS; its own failure text says *"inside the try
    block that prints RuntimeError"*, and that half was prose. Measured
    2026-09-01 on `run_plan.py`: the block sat ABOVE the handler in one file of
    eleven, so `resolve_identity`'s refusal of a bad `--run-id` and
    `open_run_bag`'s refusal of a full journal — the two failures Phase 1 r9 and
    Phase 9 exist to make diagnosable — reached the operator as a traceback there
    and as a one-line diagnostic in the other ten. Nothing went red, because a
    guard that checks presence cannot see placement.

    KEYED ON THE HANDLER'S EXCEPTION SET, NOT ON "IS IT IN A TRY". A `try` whose
    `except` catches only `ValueError` would satisfy the weaker property while
    letting exactly these two escape, and `RuntimeError` is the type every layer
    in this fleet raises with an operator-facing remedy attached
    (`JournalRootError` and `BagError` both subclass it, deliberately, so this
    one clause catches them).
    """
    offenders = []
    for path in _entrypoints(directory):
        tree = ast.parse(path.read_text(), filename=str(path))
        guarded = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            if not any(_names_runtime_error(h) for h in node.handlers):
                continue
            for stmt in node.body:
                for inner in ast.walk(stmt):
                    if _is_bag_open(inner):
                        guarded.add(inner.lineno)
        every = {n.lineno for n in ast.walk(tree) if _is_bag_open(n)}
        for line in sorted(every - guarded):
            offenders.append(f"{path.name}:{line}")
    return offenders


def _is_bag_open(node: ast.AST) -> bool:
    return (isinstance(node, ast.Call)
            and (getattr(node.func, "id", None) == BAG_OPEN
                 or getattr(node.func, "attr", None) == BAG_OPEN))


def _names_runtime_error(handler: ast.ExceptHandler) -> bool:
    """`except RuntimeError`, or a tuple containing it. A bare `except:` counts."""
    if handler.type is None:
        return True
    parts = (handler.type.elts if isinstance(handler.type, ast.Tuple)
             else [handler.type])
    return any(getattr(p, "id", None) == "RuntimeError" for p in parts)


# --- the sweep -------------------------------------------------------------------

def test_every_entrypoint_actually_opens_a_run_bag() -> None:
    """THE REQUIREMENT. A parent added without the call goes red on the merge path."""
    discovered = _entrypoints(ENTRYPOINTS_DIR)
    assert discovered, f"no entrypoints discovered under {ENTRYPOINTS_DIR} — the sweep is inert"

    missing = _missing_bag_open(ENTRYPOINTS_DIR)
    assert not missing, (
        f"these entrypoints start a run with no journal bag: {missing}. Every run "
        f"opens one as its first step (Persistent Memory Protocol Phase 1 r11) — "
        f"inside the try block that prints RuntimeError, before the first side "
        f"effect:\n"
        f"    identity = resolve_identity(argv)\n"
        f"    journal.open_run_bag(run_id=identity.run_id, "
        f"writer=identity.writer,\n"
        f"                         repo_root=repo_root, workflow_key=...)\n"
        f"⚠ THIS MESSAGE USED TO SAY `run_id=journal.mint_run_id()`, which Phase "
        f"9 r2 forbids: a name minted inside the process that is supposed to have "
        f"RECEIVED it is a fresh name on every retry. A guard teaching the shape "
        f"its own phase forbids is an instruction, read at the one moment "
        f"somebody is looking for one — `test_the_run_id_ARRIVES_from_outside.py` "
        f"is what holds the corrected shape, because this sweep asserts nothing "
        f"about arguments and never could.\n"
        f"SCOPE OF THIS SWEEP: {ENTRYPOINTS_DIR.relative_to(REPO_ROOT)}/run_*.py "
        f"and nothing else. A run initiated from anywhere else is INVISIBLE here.")


def test_bag_open_is_INSIDE_the_handler_that_prints_the_refusal() -> None:
    """The placement half, which the sweep above only ever stated in prose.

    A bag-open above the handler turns two operator-facing refusals — an
    unusable `--run-id`, a full or misconfigured journal root — into tracebacks,
    for precisely the failures whose whole design argument is that they must be
    diagnosable WITHOUT a working journal. Measured on `run_plan.py`: one file of
    eleven had drifted, and every other check in this module passed it.
    """
    offenders = _bag_open_outside_the_handler(ENTRYPOINTS_DIR)
    assert not offenders, (
        f"these bag-opens are not inside a `try` that catches `RuntimeError`: "
        f"{offenders}.\n"
        f"  failing property: `JournalRootError` and `BagError` both subclass "
        f"`RuntimeError` so that ONE handler prints the remedy the layer that "
        f"knew what failed wrote. Outside it, the operator gets a traceback for "
        f"a misconfiguration.\n"
        f"  remedy: move the boundary block inside the entrypoint's existing "
        f"`except (RuntimeError, ...)` block — `print(f\"\\n\u2717 {{exc}}\", "
        f"file=sys.stderr); return 1`.")


def test_THE_PLACEMENT_PREDICATE_DISCRIMINATES(tmp_path: Path) -> None:
    """CONTROLS on `_bag_open_outside_the_handler`, on a self-contained tree.

    A SCRATCH DIRECTORY, NOT THE FLEET, and that is the point: a control sharing
    a fixture with the code under mutation over-fires on things the assertion
    would only have caught by accident. These four files are written here and
    nowhere else, so each verdict is attributable to exactly one shape.
    """
    cases = {
        "run_guarded.py":
            "def main(a):\n"
            "    try:\n"
            "        journal.open_run_bag(run_id=ctx.run_id)\n"
            "    except (RuntimeError, FileNotFoundError):\n"
            "        return 1\n",
        "run_outside.py":
            "def main(a):\n"
            "    journal.open_run_bag(run_id=ctx.run_id)\n"
            "    try:\n"
            "        work()\n"
            "    except RuntimeError:\n"
            "        return 1\n",
        "run_wrong_exception.py":
            "def main(a):\n"
            "    try:\n"
            "        journal.open_run_bag(run_id=ctx.run_id)\n"
            "    except ValueError:\n"
            "        return 1\n",
        "run_nested_guarded.py":
            "def main(a):\n"
            "    try:\n"
            "        if a.x:\n"
            "            journal.open_run_bag(run_id=ctx.run_id)\n"
            "    except RuntimeError:\n"
            "        return 1\n",
    }
    for name, src in cases.items():
        (tmp_path / name).write_text(src, encoding="utf-8")

    found = {o.split(":")[0] for o in _bag_open_outside_the_handler(tmp_path)}
    assert found == {"run_outside.py", "run_wrong_exception.py"}, (
        f"the predicate reported {found}; it must flag the call above the handler "
        f"and the one under a handler that cannot catch the refusal, and must not "
        f"flag a correctly-guarded call or one nested inside the guarded block")


def test_the_sweep_is_not_vacuous() -> None:
    """A sweep that examined nothing would satisfy every assertion above.

    The count is asserted as non-trivial rather than pinned to eleven: pinning
    it would make adding an entrypoint fail this file for the wrong reason,
    while a bare `assert discovered` cannot tell one file from the whole fleet.
    """
    discovered = _entrypoints(ENTRYPOINTS_DIR)
    assert len(discovered) >= 10, (
        f"only {len(discovered)} entrypoints discovered under {ENTRYPOINTS_DIR}; "
        f"this fleet has eleven. The predicate has drifted from the tree.")


# --- r5: the population covers every shape that can START a run -------------------

def test_every_file_beside_the_entrypoints_is_SWEPT_or_DECLARED() -> None:
    """Phase 9 r5. A new run-starting shape cannot land here invisibly.

    THE GLOB WAS THE WHOLE PREDICATE, and it was enough for exactly as long as
    `run_*.py` was the only shape a run could start from. Two things end that:
    Workflow Decomposition Phase 3 puts NINE new runners in this directory, and
    the Temporal port turns an entrypoint into a client. Nine landing as
    `run_*.py` are swept and go red until each opens a bag — which pushes
    whoever lands them, under time pressure and with a failing test as the
    argument, toward *every invocation opens its own bag*: four bags for one
    piece of work. Nine landing under any other name are invisible, which is
    the opposite failure. The sweep was about to make that decision for us.

    SO EVERY FILE IS CLASSIFIED AND THE DEFAULT IS TO FAIL. Swept, or a thin
    shim whose exec target is swept, or declared non-starting WITH the reason.
    A file nobody classified is a claim nobody made.
    """
    loose = unclassified(ENTRYPOINTS_DIR)
    assert not loose, (
        f"these files sit beside the entrypoints and nothing says what they "
        f"are: {loose}.\n"
        f"THE THREE SHAPES THIS SWEEP KNOWS, and every file must be one:\n"
        f"  * a kickoff entrypoint — `run_*.py`, swept by this file, which must "
        f"open a bag before its first side effect;\n"
        f"  * a thin shim — `<workflow>.sh` that execs a swept `run_*.py` and "
        f"passes every argument through untouched. It starts nothing itself;\n"
        f"  * a declared non-starter — add a row to `NON_STARTING_FILES` in "
        f"`journal_entrypoint_facts.py` stating WHY it cannot begin a run.\n"
        f"EXCLUDED SHAPES ARE NAMED, NOT ASSUMED: "
        f"{sorted(NON_STARTING_FILES)} are declared non-starting, and a run "
        f"initiated from outside "
        f"{ENTRYPOINTS_DIR.relative_to(REPO_ROOT)}/ altogether is invisible to "
        f"every check in this file.")


def test_every_shim_hands_off_to_an_entrypoint_this_sweep_COVERS() -> None:
    """A shim pointed somewhere else is a run-starting shape with no guard.

    The shim contract is that it resolves the interpreter and passes arguments
    through, so the runner owns the CLI and there is one place it is defined.
    That contract is what makes a shim safe to leave unswept — and it is checked
    here rather than trusted, because a shim that execs an unswept file starts a
    run this sweep cannot see, which is r5's second silent half.
    """
    swept = {p.name for p in _entrypoints(ENTRYPOINTS_DIR)}
    shims = sorted(ENTRYPOINTS_DIR.glob("*.sh"))
    assert shims, f"no shims discovered under {ENTRYPOINTS_DIR} — the check is inert"

    stray = {p.name: shim_target(p) for p in shims
             if shim_target(p) not in swept}
    assert not stray, (
        f"these shims hand off to something this sweep does not cover: {stray}. "
        f"A shim's whole safety argument is that it can only start the "
        f"`run_*.py` beside it — one that execs anything else is a run-starting "
        f"shape with no bag guard on it.")


# --- the negative control ---------------------------------------------------------

def test_the_sweep_FAILS_on_a_deliberately_non_conforming_parent(tmp_path: Path) -> None:
    """DEMONSTRATED, NOT ASSERTED. A guard that cannot go red manufactures confidence.

    THE FIXTURE IS SELF-CONTAINED AND NOT THIS REPO'S TREE. A control sharing a
    fixture with the code under mutation over-fires, and the failure reads like
    a stronger guard rather than a defect in the control. Three files here, two
    conforming and one not, so the assertion has to DISCRIMINATE rather than
    merely go red — a sweep that flagged everything would pass a control that
    only checked "something failed".
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_good.py").write_text(
        "from modules.journal import journal_activities as journal\n"
        "def main():\n"
        "    journal.open_run_bag(run_id='x', repo_root='.', workflow_key='good')\n")
    (scripts / "run_also_good.py").write_text(
        "from modules.journal.journal_activities import open_run_bag\n"
        "def main():\n"
        "    open_run_bag(run_id='x', repo_root='.', workflow_key='also-good')\n")
    (scripts / "run_forgot.py").write_text(
        "def main():\n"
        "    worktree = worktree_add('.', 'wt', 'HEAD')\n"
        "    return run_something(worktree)\n")

    assert len(_entrypoints(scripts)) == 3, "the fixture itself must be discovered"
    assert _missing_bag_open(scripts) == ["run_forgot.py"], (
        "the sweep must name exactly the non-conforming file — flagging all "
        "three would pass a red/green control while being useless")


def test_the_POPULATION_check_FAILS_on_an_unclassified_shape(tmp_path: Path) -> None:
    """r5's widening, demonstrated — and it must DISCRIMINATE, not merely go red.

    Four files, three of them legitimate: a swept runner, a conforming shim, and
    a declared non-starter. The fourth is a `.py` nobody classified — the shape
    that used to be invisible. The assertion names exactly that one, so a
    predicate that flagged everything would not pass.

    THE FIXTURE IS SELF-CONTAINED. `NON_STARTING_FILES` is the real declaration
    map and is read here, which is deliberate: the control drives the SHIPPED
    predicate rather than a local copy of it, so widening the predicate cannot
    leave this control silently testing the old one.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_swept.py").write_text("def main():\n    return 0\n")
    (scripts / "swept.sh").write_text(
        '#!/usr/bin/env bash\nSCRIPT_DIR="x"\n'
        'exec python3 "${SCRIPT_DIR}/run_swept.py" "$@"\n')
    declared = sorted(NON_STARTING_FILES)[0]
    (scripts / declared).write_text("# a declared non-starter\n")
    (scripts / "kickoff_something.py").write_text(
        "def main():\n    return start_a_run()\n")

    assert unclassified(scripts) == ["kickoff_something.py"], (
        "the population check must name exactly the unclassified file — the "
        "swept runner, its shim and the declared non-starter are all accounted "
        "for, and flagging them too would pass a red/green control uselessly")


def test_a_shim_pointed_at_an_UNSWEPT_file_is_caught(tmp_path: Path) -> None:
    """The second silent half: a shim that starts something nobody sweeps.

    Two shims, identical but for their exec target. If the check were keyed on
    "is it a `.sh`" rather than on where it points, both would pass — which is
    the version of this that would have shipped without a control.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_real.py").write_text("def main():\n    return 0\n")
    # The file the stray shim actually starts — a real run-starter under a name
    # the glob does not match, which is the whole shape being ruled out.
    (scripts / "kickoff_other.py").write_text("def main():\n    return 0\n")
    (scripts / "good.sh").write_text(
        'exec python3 "${SCRIPT_DIR}/run_real.py" "$@"\n')
    (scripts / "sideways.sh").write_text(
        'exec python3 "${SCRIPT_DIR}/kickoff_other.py" "$@"\n')
    (scripts / "opaque.sh").write_text(
        '#!/usr/bin/env bash\npython3 -c "import x; x.go()"\n')

    assert shim_target(scripts / "good.sh") == "run_real.py"
    assert shim_target(scripts / "sideways.sh") == "kickoff_other.py"
    assert shim_target(scripts / "opaque.sh") is None, (
        "a `.sh` that does not match the thin-shim shape must report None "
        "rather than being assumed harmless — it is doing something the shim "
        "contract does not describe")

    assert sorted(unclassified(scripts)) == ["kickoff_other.py", "opaque.sh",
                                             "sideways.sh"], (
        "a shim pointing outside the swept population, and the file it points "
        "at, must BOTH surface; and a `.sh` whose behaviour cannot be read must "
        "surface too. `good.sh` must not, or the check flags every shim")


def test_a_MENTION_of_the_call_does_not_satisfy_the_sweep(tmp_path: Path) -> None:
    """THE SUBSTRING BUG, ruled out by construction rather than by intent.

    The sibling sweep shipped exactly this defect: prose explaining the rule
    satisfied the check for the rule. Both files below name `open_run_bag` in
    text and neither calls it, so a grep-based sweep would report zero offenders
    where the truth is two.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_comment.py").write_text(
        "# see journal.open_run_bag for why every run opens a bag\n"
        "def main():\n"
        "    return 0\n")
    (scripts / "run_docstring.py").write_text(
        '"""This entrypoint is covered by open_run_bag elsewhere."""\n'
        "def main():\n"
        "    return 0\n")

    assert sorted(_missing_bag_open(scripts)) == ["run_comment.py", "run_docstring.py"]


# --- ordering: the call must come before the first side effect ---------------------

def test_the_call_precedes_the_first_side_effect_in_every_entrypoint() -> None:
    """r9 means *the run does not start*, and that is an ORDERING claim.

    A bag opened after `worktree_add` still refuses an unresolvable root — but by
    then a worktree exists on disk, which is the stranded-worktree failure the
    preflight module was built to end. Checked by line number rather than by
    control flow, which is the honest limit: it catches a call written below the
    side effect, not one hidden behind a branch that never runs.
    """
    offenders = []
    unchecked = []
    for path in _entrypoints(ENTRYPOINTS_DIR):
        tree = ast.parse(path.read_text(), filename=str(path))
        opens = [n.lineno for n in ast.walk(tree)
                 if isinstance(n, ast.Call)
                 and (getattr(n.func, "id", None) == BAG_OPEN
                      or getattr(n.func, "attr", None) == BAG_OPEN)]
        effects = _side_effect_lines(tree)
        if not (opens and effects):
            unchecked.append(path.name)
            continue
        if min(opens) > min(effects):
            offenders.append(f"{path.name} (bag at line {min(opens)}, "
                             f"side effect at line {min(effects)})")

    assert not offenders, (
        f"these entrypoints create something before opening the run's bag: "
        f"{offenders}. r9's refusal must land before the first side effect, or "
        f"a run with an unresolvable journal root still strands a worktree.")

    # THE UNCHECKED SET IS PINNED, so this check cannot quietly stop covering an
    # entrypoint. If a file drops out of the ordering check — because its handoff
    # changed shape — that is a coverage regression and it fails HERE rather than
    # passing vacuously, which is what the first version of this test did for six
    # of eleven files.
    assert sorted(unchecked) == sorted(_ORDERING_UNCOVERED), (
        f"the ordering check now examines a different set than it claims. "
        f"Unchecked now: {sorted(unchecked)}; declared: {sorted(_ORDERING_UNCOVERED)}. "
        f"An entrypoint that silently left this check is a coverage regression — "
        f"either restore a detectable side effect, or amend _ORDERING_UNCOVERED "
        f"with the reason it cannot be checked.")


def test_the_ordering_check_FAILS_on_a_reversed_entrypoint(tmp_path: Path) -> None:
    """The ordering guard, demonstrated the same way as the sweep.

    Two files, identical but for the order of two lines. If the check were
    keyed on presence rather than position, both would pass — which is the
    version of this test that would have shipped without a control.

    IT DRIVES `_side_effect_lines` ITSELF rather than a local reimplementation of
    it. The first version of this control inlined its own copy of the predicate,
    which meant it proved a copy discriminated and said nothing about the guard —
    and when the real predicate was widened, the copy silently kept testing the
    old one.
    """
    def offenders_in(source: str) -> bool:
        tree = ast.parse(source)
        opens = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and (getattr(n.func, "id", None) == BAG_OPEN
                      or getattr(n.func, "attr", None) == BAG_OPEN)]
        effects = _side_effect_lines(tree)
        return bool(opens and effects and min(opens) > min(effects))

    correct = ("def main():\n"
               "    journal.open_run_bag(run_id='x')\n"
               "    act.worktree_add('.', 'wt', 'HEAD')\n")
    reversed_ = ("def main():\n"
                 "    act.worktree_add('.', 'wt', 'HEAD')\n"
                 "    journal.open_run_bag(run_id='x')\n")

    # The by-name workflow handoff, which the widened predicate added and the
    # narrow one could not see at all.
    handoff_reversed = ("from modules.assistant.b.b_workflow import run_b\n"
                        "def main():\n"
                        "    run_b('.')\n"
                        "    journal.open_run_bag(run_id='x')\n")
    handoff_correct = ("from modules.assistant.b.b_workflow import run_b\n"
                       "def main():\n"
                       "    journal.open_run_bag(run_id='x')\n"
                       "    run_b('.')\n")

    assert not offenders_in(correct), "the conforming order must not be flagged"
    assert offenders_in(reversed_), "the reversed order must be flagged"
    assert not offenders_in(handoff_correct), "a conforming by-name handoff must pass"
    assert offenders_in(handoff_reversed), (
        "a workflow handoff called BY NAME before bag-open must be flagged — this "
        "is the case the narrow `worktree_add`-only predicate could not see, and "
        "it is two of the eleven entrypoints")


def test_the_worktree_cutting_count_this_argument_RESTS_ON() -> None:
    """The placement argument is quantitative, so the quantity is a GUARD.

    Three docstrings said "six of eleven … more than half the fleet" and the
    count was five — while a comment sixty lines below one of them said five.
    Nothing was checking, in a package whose central claim is that a rule kept as
    prose does not hold. A reader who catches one false count discounts the rest
    of the prose, and this package is roughly half prose.

    So the numbers stop being claims. Five cut their own worktree; three more
    hand off by name to a `*_workflow` module that cuts one; nine of eleven
    either way, which is what the argument actually needs and is true.
    """
    entrypoints = _entrypoints(ENTRYPOINTS_DIR)
    cut_their_own = [p.name for p in entrypoints
                     if "act.worktree_add(" in p.read_text()]
    hand_off_by_name = [p.name for p in entrypoints
                        if p.name not in cut_their_own
                        and _side_effect_lines(ast.parse(p.read_text()))]

    assert len(cut_their_own) == 5, (
        f"the prose in this file and in journal_activities.py says FIVE "
        f"entrypoints cut their own worktree; the tree says "
        f"{len(cut_their_own)}: {sorted(cut_their_own)}. Correct the prose — a "
        f"count restated beside the code that derives it is how it drifted last time.")
    # 8 -> 9 on 2026-08-28. The `plan` parent joined the population and
    # `run_research_minor.py` left it; only the first was in THIS set, so the
    # two changes did not cancel here as they did for the total. The ARGUMENT
    # is unchanged: `run_plan.py` cuts no worktree itself and hands off by
    # name, which is the second of the two shapes this count covers.
    assert len(cut_their_own) + len(hand_off_by_name) == 9, (
        f"the placement argument rests on NINE of eleven entrypoints reaching a "
        f"worktree before any workflow-module code runs; the tree says "
        f"{len(cut_their_own) + len(hand_off_by_name)}. If that number has moved, "
        f"the argument for opening the bag at the entrypoint rather than in the "
        f"workflow module has moved with it and needs restating, not renumbering.")


# --- the other reading of "parent", so neither is silently dropped ------------------

def test_every_worktree_creating_workflow_module_is_reachable_from_an_entrypoint() -> None:
    """THE OTHER DEFINITION OF PARENT, checked in the one direction that is checkable.

    `test_isolation_invariants.py` classifies a workflow module as a parent when
    it calls `act.worktree_add`. Those modules do not open bags — their
    entrypoints do — so this asserts the property that makes that safe: every
    such module is invoked by an entrypoint, and every entrypoint opens a bag.
    A worktree-creating module NO entrypoint reaches could run with no bag and be
    invisible to the sweep above.

    READ BY AST, FOR THE REASON `_missing_bag_open` STATES ABOVE. This test's
    first version asked `p.stem not in entrypoint_text` — a substring check over
    the concatenated entrypoint sources — which is precisely the defect that
    paragraph condemns, reintroduced on a different variable. A module merely
    NAMED in a comment or a docstring anywhere across eleven heavily-commented
    files would have been reported as reachable without being imported at all.

    WHAT IT CANNOT SEE: a module invoked dynamically, or by something outside
    `scripts/`. Reachability by import-and-name is a lower bound on the call
    graph, not the call graph.
    """
    assistant = REPO_ROOT / "scripts" / "workflows" / "temporal" / "modules" / "assistant"
    parents = [p for p in sorted(assistant.rglob("*_workflow.py"))
               if "__pycache__" not in p.parts and "act.worktree_add(" in p.read_text()]
    assert parents, "no worktree-creating workflow modules found — the predicate drifted"

    imported = _modules_imported_by(_entrypoints(ENTRYPOINTS_DIR))
    unreachable = [p.stem for p in parents if p.stem not in imported]

    assert not unreachable, (
        f"these workflow modules create a worktree but no entrypoint imports "
        f"them: {unreachable}. Whatever starts them starts a run with no journal "
        f"bag, and the entrypoint sweep cannot see it.")


def test_the_reachability_check_FAILS_on_a_module_only_MENTIONED(tmp_path: Path) -> None:
    """The reachability guard's own negative control, which it shipped without.

    Two fixture entrypoints: one that genuinely imports `alpha_workflow`, one
    that only names `beta_workflow` in a comment and a docstring. A substring
    check reports both reachable; the AST check must report exactly `beta`.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_alpha.py").write_text(
        "from modules.assistant.alpha import alpha_workflow as wf\n"
        "def main():\n"
        "    return wf.run_alpha()\n")
    (scripts / "run_beta.py").write_text(
        '"""Started by beta_workflow elsewhere."""\n'
        "# beta_workflow is documented here and imported nowhere\n"
        "def main():\n"
        "    return 0\n")

    imported = _modules_imported_by(_entrypoints(scripts))
    assert "alpha_workflow" in imported, "a real import must be seen"
    assert "beta_workflow" not in imported, (
        "a module named only in prose must NOT count as reachable — that is the "
        "substring bug this check was rewritten to rule out")


@pytest.mark.parametrize("module", ["root", "bag", "validate", "journal_activities"])
def test_the_journal_package_imports_no_workflow_module(module: str) -> None:
    """The journal must be loadable by a measurement helper or a CPI sweep.

    Dependency-free on the workflow tree, like `convergence.py` and
    `run_log.py`. Phase 6's reader is the consumer this protects: a validator
    that dragged in `modules.assistant` would drag in its `temporalio` import
    with it.
    """
    source = (REPO_ROOT / "scripts" / "workflows" / "temporal" / "modules" /
              "journal" / f"{module}.py").read_text()
    assert "modules.assistant" not in source
    assert "from ..assistant" not in source
