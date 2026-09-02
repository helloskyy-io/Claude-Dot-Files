"""Every entrypoint declaring a repo path REFUSES one that escapes, and accepts one that does not.

PROVEN THE WAY THE DEFECT WAS PROVEN — BY EXECUTION, NOT BY INSPECTION. The
sibling guard `test_no_runner_joins_an_UNRESOLVED_operator_path` reads the source
and asserts a shape is absent. That is necessary and it is not sufficient: a
runner can declare every path correctly, never write a join, and still route the
value somewhere the resolver never saw. So this file runs the real `main()` with a
real escaping argument and reads what it actually did.

BOTH ARMS, BECAUSE A GUARD THAT REFUSES EVERYTHING IS NOT A GUARD. The escape arm
asserts refusal; the legitimate arm asserts that a path inside the repo is NOT
refused. Only the pair discriminates — a resolver hard-wired to `raise` passes the
first arm perfectly.

DISCOVERED FROM THE PARSER, NOT FROM A TABLE. Each runner exposes `main`, and its
parser records what it declared in `_repo_paths`; this file reads that mapping and
synthesizes an argv from it. There is no per-runner list of flags to keep in sync,
so a runner that adds a sixth repo path is covered by that act. The one thing
hand-written is `_ARGV_SHAPE` — the non-path arguments a runner needs to reach its
resolution at all — and a runner missing from it FAILS rather than being skipped,
which is the difference between a gap that shouts and a gap that hides.

WHY IT ASSERTS ON THE MESSAGE AND NOT ONLY ON THE EXIT CODE. Every one of these
runners exits 1 for a dozen reasons. `resolves outside the repo` is the specific
diagnostic the operator needs — an escaping argument reported as `not found` sends
them to create a directory rather than to fix the argument, which
`test_preflight.test_an_ESCAPE_is_reported_before_a_MISSING_path` pins at the
resolver. This pins it at the entrypoint, where the operator reads it.

WHAT THIS DOES NOT LOOK AT:

  * **Runners with no declared repo path.** `run_build`, `run_build_minor`,
    `run_review_pr` and `run_plan_revision` take none, so there is nothing here to
    escape and they are absent from the parametrization rather than passing it.
    The vacuity floor below is what stops that absence growing quietly.
  * **The LIVE path.** Every invocation is `--dry-run` or reaches the resolver
    before dispatching, so nothing here proves the escaping value would also have
    been refused after a worktree was cut. It proves it never gets that far, which
    is the stronger property and the one `preflight` exists for.
  * **Paths deliberately outside the repo** — `--task-file`, `--phase`. They are
    declared with plain `add_argument` and are not in `_repo_paths`, so this file
    is silent about them by construction. Anchoring a RELATIVE one to the repo root
    is a separate property with a separate guard —
    `test_a_task_SOURCE_path_is_anchored_to_the_repo.py`.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

import pytest

_TEMPORAL = Path(__file__).resolve().parents[2]
_SCRIPTS = _TEMPORAL / "scripts"
REPO_ROOT = Path(__file__).resolve().parents[5]

for _p in (str(_SCRIPTS), str(_TEMPORAL)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# A path that escapes however deep the checkout sits. `resolve_operator_paths`
# collapses it to `/` before testing containment, and `/` is not inside any repo.
_ESCAPE = "../" * 40 + "tmp/escape-probe-under-test"

# The NON-PATH arguments each runner needs to reach its path resolution. Repo
# paths are never listed here — those are read off the parser. A runner absent
# from this map fails `test_every_runner_with_a_repo_path_is_exercised` rather
# than being silently skipped.
_ARGV_SHAPE: dict[str, list[str]] = {
    "run_plan_refine.py": ["--dry-run"],
    "run_plan.py": ["--dry-run"],
    "run_plan_draft.py": ["--dry-run"],
    "run_plan_sprint.py": ["--dry-run"],
    "run_triage_candidates.py": ["--dry-run"],
    "run_research.py": ["--dry-run"],
    "run_research_draft.py": ["--dry-run"],
    # `--pr` is `required=True` on this one: a verify pass has nothing to open,
    # so an invocation without it exits at the parser and never reaches the
    # resolver this file is about. The number is arbitrary and unreachable —
    # `--dry-run` returns before any `gh` call.
    "run_research_refine.py": ["--dry-run", "--pr", "1"],
    # No `--dry-run` exists on this one; it is stopped by the resolver before it
    # can dispatch, and the fixture below replaces the dispatch so that a
    # REGRESSION fails loudly here instead of cutting a worktree and spending.
    "run_plan_project.py": [],
}

# Values that are real, in-repo and of the right kind, for the legitimate arm.
# `docs` and `README.md` exist in every checkout of this repo, so no runner needs
# its own fixture and none of them can pass by accident on a stale path.
_LEGITIMATE = {True: "docs", False: "README.md"}   # keyed by is-a-directory


def _module(name: str):
    return importlib.import_module(name[:-len(".py")])


def _repo_paths_of(name: str) -> dict[str, object]:
    """What the runner's own parser recorded, by building it the way `main` does.

    Read by running `main` with `--help`, which argparse answers by raising
    SystemExit after the parser is fully constructed — so the declarations are
    complete and nothing downstream of the parse has run.
    """
    module = _module(name)
    captured: dict[str, tuple[bool, bool]] = {}
    from preflight import RepoPathParser

    original = RepoPathParser.parse_with_preflight

    def spy(self, argv=None):
        captured.update(self._repo_paths)
        raise SystemExit(0)

    RepoPathParser.parse_with_preflight = spy
    try:
        with pytest.raises(SystemExit):
            module.main([])
    finally:
        RepoPathParser.parse_with_preflight = original
    return captured


def _runners_declaring_repo_paths() -> list[str]:
    out = []
    for runner in sorted(_SCRIPTS.glob("run_*.py")):
        if "add_repo_path(" in runner.read_text():
            out.append(runner.name)
    return out


_SUBJECTS = _runners_declaring_repo_paths()


def _cases() -> list[tuple[str, str]]:
    """(runner, dest) for EVERY declared repo path, one case per path.

    ONE PATH AT A TIME, AND THE ALTERNATIVE IS WHY. Escaping all of a runner's
    paths in a single invocation is the obvious shape and it is strictly weaker:
    the resolver reports the first escape it finds, so that arm passes
    identically whether the mechanism resolves EVERY declared path or only the
    first one — and "resolves only the first" is precisely the bug class this
    change exists to end, since it is what a hand-written dict does when someone
    adds a fourth flag and updates three entries. Escaping one path while the
    others are legitimate is what discriminates.
    """
    return [(runner, dest)
            for runner in _SUBJECTS
            for dest in _repo_paths_of(runner)]


_CASES = _cases()


class _Dispatched(Exception):
    """Raised in place of a real dispatch. Reaching it is a RESULT, not an error.

    Which result depends on the arm, and that is why it is a distinct exception
    rather than a `pytest.fail`. On the escape arm, arriving here means the
    escaping path was NOT refused — the defect itself. On the legitimate arm it
    means the path was accepted and the run proceeded, which is exactly what that
    arm is asserting. One sentinel, read two ways by the two callers.
    """


@pytest.fixture(autouse=True)
def never_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test in this file may spend a model call or cut a worktree.

    `run_plan_project` has no `--dry-run`, and the legitimate arm deliberately
    feeds every runner a path that resolves — so that runner reaches its dispatch
    on every legitimate invocation. Stubbing it is therefore load-bearing rather
    than belt-and-braces: an autonomous suite that can start a real dispatch is a
    worse defect than the one this file guards.

    TWO IMPORT SHAPES, AND MISSING THE SECOND MADE THIS FIXTURE A NO-OP FOR SIX OF
    THE SEVEN RUNNERS. It used to scan `dir(module)` for a `run_`-prefixed callable,
    which only `run_plan_project` has — it does `from …plan_project_workflow import
    run_plan_project`. The other six bind a MODULE (`from … import
    plan_sprint_workflow as wf`) and call `wf.run_plan_sprint(...)`; a module is not
    `callable()` and its name is not `run_`-prefixed, so nothing was patched and the
    fixture's own docstring claimed a guarantee it was not providing. Masked only
    because `_ARGV_SHAPE` hands those six `--dry-run`, so `main` returns before the
    dispatch — i.e. the safety net was load-bearing in exactly the case it was
    absent. Both shapes are now walked, and `test_the_fixture_ACTUALLY_patched…`
    below asserts the walk found something for every runner, so a third import shape
    fails loudly instead of silently reinstating this.
    """
    for name in _SUBJECTS:
        module = _module(name)
        _patched[name] = _stub_dispatches(monkeypatch, module)


def _stub_dispatches(monkeypatch: pytest.MonkeyPatch, module) -> list[str]:
    """Replace every dispatch entry reachable from a runner module. Returns what.

    `attr=attribute` binds the name at lambda-DEFINITION time. Bound late, every
    stub reported whichever attribute the loop finished on, so a failure message
    would name the wrong function — cosmetic until the moment it is read, which is
    always a moment somebody is already confused.
    """
    patched: list[str] = []

    def stub(where, attribute: str, label: str) -> None:
        monkeypatch.setattr(
            where, attribute,
            lambda *a, _label=label, **k: (_ for _ in ()).throw(_Dispatched(_label)),
            raising=False)
        patched.append(label)

    for attribute in dir(module):
        value = getattr(module, attribute)
        if attribute.startswith("run_") and callable(value):
            stub(module, attribute, f"{module.__name__}.{attribute}")
        elif isinstance(value, ModuleType) and value.__name__.startswith("modules."):
            for inner in dir(value):
                if inner.startswith("run_") and callable(getattr(value, inner)):
                    stub(value, inner, f"{attribute}.{inner}")
    return patched


_patched: dict[str, list[str]] = {}


def test_the_fixture_ACTUALLY_patched_a_dispatch_for_every_runner() -> None:
    """The safety net is asserted, not assumed — because it was absent for six of seven.

    A fixture that silently patches nothing is indistinguishable from one that
    works, right up until a case is added without `--dry-run` and a unit test cuts
    a worktree and spends a model call. That is the same class as the defect this
    whole file guards: an omission with no syntax, made visible by asserting the
    thing that should have happened.
    """
    assert set(_patched) == set(_SUBJECTS), (
        f"the fixture did not run for {set(_SUBJECTS) - set(_patched)}")
    unpatched = [name for name, hits in _patched.items() if not hits]
    assert not unpatched, (
        f"{unpatched} had no dispatch entry stubbed, so nothing stops a real "
        f"dispatch if any of their cases stops passing `--dry-run`. A runner that "
        f"imports its workflow a third way needs a branch in `_stub_dispatches`.")


def test_the_sweep_finds_the_runners_that_declare_a_repo_path() -> None:
    """VACUITY FLOOR. Seven runners declared one when this was written.

    If the count drops, either a runner stopped taking an operator path — say so
    here — or the reader broke and every arm below is passing over nothing.
    """
    assert len(_SUBJECTS) >= 7, (
        f"expected at least seven runners declaring a repo path; found "
        f"{_SUBJECTS}. Fix the reader, do not weaken this.")


def test_every_runner_with_a_repo_path_is_exercised() -> None:
    """A new runner must fail HERE, not be skipped.

    `_ARGV_SHAPE` is the one hand-written thing in this file. Left as a lookup
    with a default, a runner missing from it would quietly contribute no
    coverage; asserted, it costs one line to add and cannot be forgotten.

    ⚠ THIS BODY WENT MISSING FOR ONE PASS. `test_no_ARGV_SHAPE_ENTRY_NAMES_A_
    RUNNER_THAT_IS_GONE` was inserted BETWEEN this docstring and the assertion
    below, so this test had a docstring-only body and asserted nothing while its
    `unshaped` check ran under the other name. Two defects in one edit: a guard
    reported green while examining nothing, and two independent properties
    short-circuited, so a change that both orphaned a key and added an unshaped
    runner reported only the first. `test_no_TEST_IN_THIS_SUITE_ASSERTS_NOTHING`
    now holds the class.
    """
    unshaped = [name for name in _SUBJECTS if name not in _ARGV_SHAPE]
    assert not unshaped, (
        f"{unshaped} declare a repo path but have no argv shape here, so nothing "
        f"drives them. Add the non-path arguments each needs to reach its "
        f"resolution — the repo paths themselves are read off the parser.")


def test_no_ARGV_SHAPE_ENTRY_NAMES_A_RUNNER_THAT_IS_GONE() -> None:
    """THE OTHER DIRECTION, and it is the one that fails SILENTLY.

    The assertion below catches a runner with no shape — a gap that shouts. A
    shape with no runner is the mirror defect and nothing saw it: `_ARGV_SHAPE`
    keyed `run_research_minor.py` for five days after that runner was deleted
    (2026-08-28), because an unused key in a lookup costs nothing to have. It is
    dead config in the one hand-maintained map in a file whose neighbours all
    derive their populations, and the next one arrives the next time a workflow
    is renamed — this fleet renamed four in a fortnight.

    Cheap here, and unavailable anywhere else: nothing in the suite reads this
    map except the two assertions in this module.
    """
    scripts = {p.name for p in _SCRIPTS.glob("run_*.py")}
    orphaned = sorted(set(_ARGV_SHAPE) - scripts)
    assert not orphaned, (
        f"{orphaned} have argv shapes but no runner on disk. A renamed or "
        f"deleted workflow leaves its key behind, and an unused key contributes "
        f"no coverage while reading exactly like coverage.")


@pytest.mark.parametrize("runner,escaping", _CASES, ids=lambda v: v)
def test_an_ESCAPING_path_is_refused_before_anything_is_created(
        runner: str, escaping: str, capsys: pytest.CaptureFixture[str]) -> None:
    """THE GUARD, one declared path at a time, driven the way an operator drives it.

    Every other path on the invocation is legitimate, so a pass here says *this
    particular argument* was resolved — not merely that something on the command
    line was.
    """
    declared = _repo_paths_of(runner)
    assert declared, f"{runner} matched `add_repo_path(` but declared nothing"

    argv = list(_ARGV_SHAPE[runner])
    for dest, spec in declared.items():
        is_dir = spec.is_dir
        value = _ESCAPE if dest == escaping else _LEGITIMATE[is_dir]
        argv += [value] if _is_positional(runner, dest) else [f"--{dest.replace('_', '-')}", value]

    try:
        exit_code = _module(runner).main(argv)
    except _Dispatched as reached:
        pytest.fail(
            f"{runner} carried an escaping path all the way to `{reached}` — the "
            f"resolution never refused it. Under "
            f"`--dangerously-skip-permissions` this is an unattended run "
            f"dispatched against a tree outside the repository.")
    captured = capsys.readouterr()

    assert exit_code == 1, (
        f"{runner} accepted an escaping `{escaping}` (exit {exit_code}). These "
        f"run under `--dangerously-skip-permissions`, so this is an unattended "
        f"run reading and writing wherever it was pointed."
        f"\n{captured.out}\n{captured.err}")
    assert "resolves outside the repo" in captured.err, (
        f"{runner} refused the invocation but not as an ESCAPE. An operator told "
        f"`not found` goes and creates the directory; the argument is the "
        f"problem.\n{captured.err}")
    assert escaping in captured.err, (
        f"{runner} refused an escape but named a DIFFERENT argument than "
        f"`{escaping}`, the one that actually escaped. Every other path on this "
        f"invocation was legitimate, so this is the resolver reporting on a path "
        f"it was not asked about.\n{captured.err}")


@pytest.mark.parametrize("runner", _SUBJECTS, ids=lambda n: n)
def test_a_LEGITIMATE_in_repo_path_is_not_refused(
        runner: str, capsys: pytest.CaptureFixture[str]) -> None:
    """THE OTHER ARM. A resolver hard-wired to raise passes the escape arm.

    This asserts only that the run is not refused AS AN ESCAPE — several of these
    runners will still exit 1 further down, because `docs` is a real directory
    but not a real component and holds no `roadmap.md`. Asserting exit 0 here
    would mean fabricating a component fixture per runner and would prove less:
    the property under test is the containment check, and how far past it each
    runner gets is its own test's business.
    """
    declared = _repo_paths_of(runner)
    argv = list(_ARGV_SHAPE[runner])
    for dest, spec in declared.items():
        is_dir = spec.is_dir
        value = _LEGITIMATE[is_dir]
        argv += [value] if _is_positional(runner, dest) else [f"--{dest.replace('_', '-')}", value]

    try:
        _module(runner).main(argv)
    except _Dispatched:
        # Reaching the dispatch means the path was accepted and the run
        # proceeded, which IS this arm's assertion. `run_plan_project` takes this
        # branch on every legitimate invocation because it has no `--dry-run`.
        pass
    captured = capsys.readouterr()

    assert "resolves outside the repo" not in captured.err, (
        f"{runner} rejected an in-repo path as an escape: {argv}\n{captured.err}")


def _is_positional(runner: str, dest: str) -> bool:
    """Whether the runner spells this repo path as a positional.

    Read off the source rather than guessed from the dest: `research_dir` is a
    positional and `--candidates` is a flag, and inferring from the underscore
    would break the first time somebody declares `--task_file`.
    """
    source = (_SCRIPTS / runner).read_text()
    return f'add_repo_path("{dest}"' in source
