"""A relative `--task-file` or `--phase` is resolved against the REPO, not the cwd.

THE DEFECT, measured 2026-08-19 by execution. Dispatched from
`scripts/workflows/temporal/`:

    $ python3 scripts/run_build.py --phase docs/development/workflow-decomposition/\\
          phase2_family_alignment.md --repo <repo>
    ✗ [Errno 2] No such file or directory: 'docs/development/…/phase2_family_alignment.md'

The file exists. Every reader of a task source in this fleet was
`Path(arg).read_text()`, which is relative to whatever directory the operator
happened to be standing in, so a repo-relative argument worked from the repo root
and nowhere else. An absolute path worked; the operator had to already know that,
and the message did not say it.

THIS IS ISSUE #48 ONE LAYER DOWN, and that is why the remedy is the same shape.
#48 was the REPO ROOT falling back to `Path.cwd()` in six of seven entrypoints;
`resolve_repo_root`'s docstring is the ruling — in this fleet the invocation
directory is never a meaningful base, because a dispatch names its target with
`--repo` and the operator's shell is incidental. Nobody had applied that reasoning
to the arguments read RELATIVE to it.

THE SWEEP, BEFORE GENERALISING. The brief named `run_build.py --phase`. Reading
the tree, ALL EIGHT runners had the shape and there were nine read sites: the two
build parents through `task.task_file or task.plan_path`, five runners through
`Path(a.task_file).read_text() if a.task_file else ""`, and
`run_plan_revision._read_task_file`, which has its own two-message contract. The
generalisation is what the sweep showed, not what the brief assumed.

WHAT THIS IS NOT, and the distinction decided the fix. `preflight.RepoPathParser`,
`test_preflight.py`, `test_an_entrypoint_REFUSES_an_escaping_operator_path.py` and
`test_no_runner_joins_an_UNRESOLVED_operator_path.py` ALL state that `--task-file`
and `--phase` point outside the repo ON PURPOSE and are declared with plain
`add_argument` for that reason. That ruling stands: **nothing here contains these
paths.** An absolute task source outside the tree is read exactly as given, and a
relative one that climbs out is resolved and read without complaint. What changed
is the BASE for a relative argument, which is the one thing an operator cannot
control from a dispatch line. Converting them to `add_repo_path` would have been a
different and unmade ruling.

WHAT THIS DOES NOT LOOK AT:

  * **Containment.** By construction, per the paragraph above.
  * **Whether a call sits on the LIVE path.** The sweep is syntactic: a runner
    that called the helper inside dead code would pass. What that costs is bounded
    by the behavioural tests below, which drive the real readers.
  * **String-level assembly.** `Path(a.task_file)` is caught; an
    `f"{root}/{a.task_file}"` is not, for the same reason its sibling sweep gives
    — every runner interpolates argument values into its banner.
  * **The value handed to the MODEL.** `PLAN_PATH` is NOT the operator's raw
    string. Both build parents pass it through
    `build_activities.path_for_the_model`, which renders an in-repo path
    repo-relative, resolves an escaping relative one to absolute, and leaves a
    genuinely out-of-repo absolute one alone — so what the model is SHOWN and what
    this file's helpers READ are two different answers on purpose.
    `test_no_prompt_hands_the_model_a_MAIN_CHECKOUT_path.py` owns that axis. NOT
    `test_model_gets_the_worktree_path.py`, which sweeps
    `modules/assistant/research/*/` and keys on `RESEARCH_DIR`: it does not reach
    the build family, and believing otherwise is how the build family's render
    arrived uncovered. This file is silent about the axis either way.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.assistant import assistant_activities as act
from modules.assistant.build import build_activities as build_act
from modules.assistant.build.build_inputs import BuildInput

_TEMPORAL = Path(__file__).resolve().parents[2]
_RUNNERS = sorted((_TEMPORAL / "scripts").glob("run_*.py"))
_BUILD = sorted((_TEMPORAL / "modules" / "assistant" / "build").rglob("*.py"))
_SWEPT = _RUNNERS + _BUILD

# The dests every runner in this fleet uses for a task source. Named rather than
# guessed from the flag text because `--phase` binds `plan_path`, so keying on the
# flag would miss the argument the defect was actually measured on.
_TASK_SOURCE_ATTRS = frozenset({"task_file", "plan_path"})


def _path_calls_on_a_task_source(tree: ast.AST) -> list[tuple[int, str]]:
    """Every `(line, attr)` where `Path(...)` is built from a task-source attribute.

    STATED POSITIVELY AND ABOUT THE TREE, the way its sibling sweep states its own
    property: the omission of an anchoring call has no syntax, but the thing the
    omission is FOR does. A raw argparse string is not a path until something
    turns it into one, and `Path(...)` is how both defect sites did it —
    `Path(a.task_file)` in five runners and
    `Path(task.task_file or task.plan_path)` in the two build parents. The whole
    argument subtree is walked, so a `or` between two of them is caught rather
    than only the first.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == "Path"):
            continue
        for arg in node.args:
            for inner in ast.walk(arg):
                if (isinstance(inner, ast.Attribute)
                        and inner.attr in _TASK_SOURCE_ATTRS):
                    found.append((inner.lineno, inner.attr))
    return found


_PARSED = {p: ast.parse(p.read_text()) for p in _SWEPT}


def test_the_sweep_FOUND_the_modules_it_claims_to_read() -> None:
    """VACUITY FLOOR. An assertion over an empty set reads exactly like coverage."""
    assert len(_RUNNERS) >= 10, f"only found {[p.name for p in _RUNNERS]}"
    assert len(_BUILD) >= 8, f"only found {[p.name for p in _BUILD]}"


def test_the_sweep_can_SEE_a_task_source_attribute_at_all() -> None:
    """SECOND VACUITY FLOOR, and the one that matters.

    Every check below is scoped by `_TASK_SOURCE_ATTRS`. If both dests were
    renamed, the sweep would return empty for every module and go green while
    reporting on nothing — so the count of modules that MENTION a task source is
    asserted, independently of whether any of them wraps it in a `Path`.
    """
    mentions = {p.name for p, tree in _PARSED.items()
                if any(isinstance(n, ast.Attribute) and n.attr in _TASK_SOURCE_ATTRS
                       for n in ast.walk(tree))}
    assert len(mentions) >= 4, (
        f"only {sorted(mentions)} mention a task-source attribute at all. The "
        f"dests were probably renamed; fix `_TASK_SOURCE_ATTRS` rather than "
        f"weakening this, or every assertion below is inert.")


@pytest.mark.parametrize("module", _SWEPT, ids=lambda p: p.name)
def test_no_module_builds_a_PATH_from_a_task_source_by_hand(module: Path) -> None:
    """THE GUARD. `Path(a.task_file)` is the defect, spelled out."""
    offenders = _path_calls_on_a_task_source(_PARSED[module])
    assert not offenders, (
        f"{module.name} builds a Path directly from a task source at "
        f"{[f'line {n}: .{a}' for n, a in offenders]}. That path is relative to "
        f"the process CWD, so a repo-relative argument works only from the repo "
        f"root — measured on `run_build.py --phase` from a subdirectory. Use "
        f"`assistant_activities.anchor_task_source` / `resolve_task_source` / "
        f"`task_context`, which anchor to the repo root and say so when the file "
        f"is missing.")


def test_the_anchoring_helper_HAS_CONSUMERS() -> None:
    """A guard that only forbids a shape passes just as well when nobody reads a
    task source at all. This asserts the positive: the helper is actually called.
    """
    users = {p.name for p, tree in _PARSED.items()
             if any(isinstance(n, ast.Attribute)
                    and n.attr in ("anchor_task_source", "resolve_task_source",
                                   "task_context")
                    for n in ast.walk(tree))}
    assert len(users) >= 6, (
        f"only {sorted(users)} call an anchoring helper. Eight runners and the "
        f"build family read a task source; if that has dropped, either the reads "
        f"moved somewhere this sweep does not look, or the anchoring was removed.")


# --- the behaviour, driven rather than asserted -------------------------------

def _repo_and_decoy(tmp_path: Path) -> tuple[Path, Path]:
    """A repo holding the real file, and a cwd holding a DECOY of the same name.

    THE DECOY IS WHAT MAKES THESE TESTS DISCRIMINATE. Without it a reader that
    resolved against the cwd would still find nothing there and raise, and a
    reader that resolved against the repo would find the file — both look like a
    pass for the wrong reason once the test only checks that SOMETHING was read.
    The two files carry different bytes, so the assertion is on WHICH one won.
    """
    repo, elsewhere = tmp_path / "repo", tmp_path / "elsewhere"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "plan.md").write_text("FROM THE REPO")
    (elsewhere / "docs").mkdir(parents=True)
    (elsewhere / "docs" / "plan.md").write_text("FROM THE CWD — WRONG")
    return repo, elsewhere


def test_an_ABSOLUTE_task_source_is_used_exactly_as_given(tmp_path: Path) -> None:
    """The half that must NOT change: outside-the-repo remains legitimate."""
    outside = tmp_path / "outside" / "brief.md"
    outside.parent.mkdir(parents=True)
    outside.write_text("x")
    repo = tmp_path / "repo"
    repo.mkdir()
    assert act.anchor_task_source(repo, str(outside)) == outside.resolve()


@pytest.mark.parametrize("field", ["task_file", "plan_path"], ids=["task-file", "phase"])
def test_a_RELATIVE_task_source_is_read_from_the_REPO_not_the_cwd(
        field: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE MEASURED DEFECT, driven through the real reader both build tiers use.

    BOTH FIELDS, because the brief named only `--phase` and the sweep found
    `--task-file` carries the identical shape. A fix verified on one of them would
    leave the other live.
    """
    repo, elsewhere = _repo_and_decoy(tmp_path)
    monkeypatch.chdir(elsewhere)
    task = BuildInput(**{field: "docs/plan.md"})
    assert build_act.task_text(task, repo) == "FROM THE REPO"


def test_a_MISSING_task_source_names_the_base_it_was_resolved_against(
        tmp_path: Path) -> None:
    """The one case this change makes WORSE must be self-diagnosing in one line.

    An operator who meant a cwd-relative path now gets the repo copy or nothing.
    The message therefore has to carry the raw argument, the base and the result —
    a bare `[Errno 2]` naming only the string they typed is what sent the measured
    run looking in the wrong place.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(RuntimeError) as exc:
        act.resolve_task_source(repo, "docs/absent.md", "--phase")
    message = str(exc.value)
    assert "--phase" in message, "the message must name the flag the operator typed"
    assert "docs/absent.md" in message, "…and the argument they typed"
    assert str(repo) in message, "…and the base it was resolved against"
    assert "absolute" in message, "…and the way out for a cwd-relative path"


def test_an_ABSENT_task_file_argument_reads_as_no_context(tmp_path: Path) -> None:
    """`task_context(root, None)` is "" and must not become a Path of anything."""
    assert act.task_context(tmp_path, None) == ""


# --- the control --------------------------------------------------------------

def test_the_detector_FIRES_on_each_shape_it_claims_to_cover() -> None:
    """DISCRIMINATOR, on SELF-CONTAINED source rather than a copy of a real module.

    Derived from what `_path_calls_on_a_task_source` claims — that it catches a
    `Path(...)` built from a task-source attribute, including one buried in the
    `or` the two build parents used. A control sharing a fixture with the code
    under test over-fires and proves nothing about either.

    The negative sample is the shape the tree now uses. Without it, a detector
    that flagged every `Path(...)` call would satisfy all three positives and fail
    every module in the fleet.
    """
    positives = {
        "bare read": "c = Path(a.task_file).read_text()\n",
        "the or-chain both parents used":
            "d = Path(task.task_file or task.plan_path).read_text()\n",
        "phase alone": "p = Path(args.plan_path)\n",
        "nested in a call": "p = Path(str(a.task_file))\n",
    }
    for label, source in positives.items():
        assert _path_calls_on_a_task_source(ast.parse(source)), (
            f"the detector did not fire on the `{label}` shape, which this "
            f"module claims to cover. Every green result above is unproven for it.")

    clean = (
        "c = act.task_context(repo_root, a.task_file)\n"
        "p = act.resolve_task_source(repo_root, task.plan_path, '--phase')\n"
        "q = act.anchor_task_source(repo_root, path_str)\n"
        "w = Path(worktree) / 'docs'\n"
        "print(f'{a.task_file}')\n"
        "values = {'PLAN_PATH': task.plan_path}\n"
    )
    assert not _path_calls_on_a_task_source(ast.parse(clean)), (
        "the detector fired on the shape the fleet now uses — the helper calls, a "
        "Path built from something else, the raw argument echoed in a banner, and "
        "the raw argument rendered into a prompt value. Flagging those would make "
        "the guard unusable the same week.")
