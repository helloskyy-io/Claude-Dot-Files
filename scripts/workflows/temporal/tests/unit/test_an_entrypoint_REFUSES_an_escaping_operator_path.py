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
    is silent about them by construction.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

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
    "run_plan_verify.py": ["--dry-run"],
    "run_plan_feature.py": ["--dry-run"],
    "run_plan_sprint.py": ["--dry-run"],
    "run_triage_candidates.py": ["--dry-run"],
    "run_research.py": ["--dry-run"],
    "run_research_minor.py": ["--dry-run"],
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


def _repo_paths_of(name: str) -> dict[str, tuple[bool, bool]]:
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

    Patched by NAME on each runner module (`run_plan_project`, `run_plan_sprint`,
    …), which is how every runner in this tree imports its workflow entry.
    """
    for name in _SUBJECTS:
        module = _module(name)
        for attribute in dir(module):
            if attribute.startswith("run_") and callable(getattr(module, attribute)):
                monkeypatch.setattr(
                    module, attribute,
                    lambda *a, **k: (_ for _ in ()).throw(_Dispatched(attribute)),
                    raising=False)


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
    """
    unshaped = [name for name in _SUBJECTS if name not in _ARGV_SHAPE]
    assert not unshaped, (
        f"{unshaped} declare a repo path but have no argv shape here, so nothing "
        f"drives them. Add the non-path arguments each needs to reach its "
        f"resolution — the repo paths themselves are read off the parser.")


@pytest.mark.parametrize("runner", _SUBJECTS, ids=lambda n: n)
def test_an_ESCAPING_path_is_refused_before_anything_is_created(
        runner: str, capsys: pytest.CaptureFixture[str]) -> None:
    """THE GUARD, one runner at a time, driven the way an operator drives it."""
    declared = _repo_paths_of(runner)
    assert declared, f"{runner} matched `add_repo_path(` but declared nothing"

    argv = list(_ARGV_SHAPE[runner])
    for dest in declared:
        argv += [_ESCAPE] if _is_positional(runner, dest) else [f"--{dest.replace('_', '-')}", _ESCAPE]

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
        f"{runner} accepted an escaping path (exit {exit_code}). These run under "
        f"`--dangerously-skip-permissions`, so this is an unattended run reading "
        f"and writing wherever it was pointed.\n{captured.out}\n{captured.err}")
    assert "resolves outside the repo" in captured.err, (
        f"{runner} refused the invocation but not as an ESCAPE. An operator told "
        f"`not found` goes and creates the directory; the argument is the "
        f"problem.\n{captured.err}")


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
    for dest, (is_dir, _) in declared.items():
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
