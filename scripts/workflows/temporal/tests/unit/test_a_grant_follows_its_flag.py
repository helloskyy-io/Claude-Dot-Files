"""A write grant on an operator-supplied path is DERIVED from that path, never named.

THE CLASS, NOT THE THREE WORKFLOWS THAT HAPPENED TO CARRY THE LITERAL. Four plan
workflows expose `--candidates` on their runner, and it is the flag through which
a DIFFERENT repository's pool is targeted — `--repo` points at a tree whose pool
need not sit at this repo's path. Three of the four hard-coded the grant as
`^docs/standards/architecture/research/candidates\\.md$` anyway.

WHAT THAT COSTS, AND IT IS A CORRECT RUN THAT PAYS. The prompt is handed
`CANDIDATES_PATH` — the operator's path — and told to append a proposal there.
`FORBIDDEN_PATHS` denies `^docs/standards/` wholesale. The grant that would except
it names a file the run was never pointed at, so `boundary_crossings` reads the
model obeying its own instructions as a boundary crossing and fails the run at the
LAST guard, after every turn has been spent. It presents as *"the flag is broken"*,
not as *"the grant is a literal"*, which is why it survived four workflows.

WHY A PROPERTY TEST AND NOT A GREP. A workflow can carry the literal in a comment
or a docstring and still derive its grant correctly — this file does exactly that
in the paragraph above. Grepping for the string would flag it and teach the next
author to delete the explanation rather than the defect. So this CALLS each grant
with a pool that is deliberately not this repo's and asserts the returned patterns
match it.

DISCOVERED FROM THE RUNNERS, NOT LISTED. The obligation is created by exposing the
flag, so the flag is what the sweep keys on: any `run_*.py` declaring
`--candidates` must reach a workflow whose grant honours it. A fifth workflow with
that flag is covered on the day its runner is written, and a workflow that stops
exposing the flag drops out on its own.

WHAT THIS DOES NOT LOOK AT:

  * **Other operator paths.** `--sprint` and `--research` are not swept. `--sprint`
    was already derived, and `--research` reaches the grant only through
    `direction.md`, which is checked below as part of the candidates sweep for
    `triage-candidates` alone.
  * **Whether the grant is too WIDE.** A workflow returning `^.*$` passes this and
    is a far worse defect. Width is each workflow's own test's business; this
    asserts only that the grant FOLLOWS the argument.
  * **The prompt.** That the model is handed the same path it is granted is
    `prompt_values`' contract, held by `test_dry_run_previews_the_dispatched_prompt`.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import re
from pathlib import Path

import pytest

_TEMPORAL = Path(__file__).resolve().parents[2]
_RUNNERS = sorted((_TEMPORAL / "scripts").glob("run_*.py"))

# A pool that is deliberately NOT this repo's, and whose every segment differs, so
# a grant that ignored the argument cannot match it by accident.
_ELSEWHERE = Path("some/other/pool/candidates")
_ELSEWHERE_DIR = Path("some/other/pool")


def _typed(param: inspect.Parameter, value: Path) -> Path | str:
    """`value` as whatever the parameter is annotated to take.

    `from __future__ import annotations` is in force across the fleet, so
    `param.annotation` is the SOURCE TEXT (`'str'`, `'Path'`) and never the type
    object. Comparing it against `str` therefore always says "not a str" — which
    silently handed `plan_sprint.permitted_paths` a Path and blew up inside
    `re.escape`, three frames from anything naming the cause.
    """
    return value.as_posix() if str(param.annotation) == "str" else value


def _workflow_module_of(runner: Path) -> str | None:
    """The dotted module a runner imports as `wf`, read off its import statements."""
    for node in ast.walk(ast.parse(runner.read_text())):
        if not isinstance(node, ast.ImportFrom):
            continue
        for alias in node.names:
            if alias.asname == "wf":
                return f"{node.module}.{alias.name}"
    return None


def _runners_exposing_candidates() -> list[tuple[str, str]]:
    """(runner name, workflow module) for every entrypoint declaring `--candidates`."""
    out = []
    for runner in _RUNNERS:
        if '"--candidates"' not in runner.read_text():
            continue
        module = _workflow_module_of(runner)
        if module:
            out.append((runner.name, module))
    return out


_SUBJECTS = _runners_exposing_candidates()


def test_the_sweep_finds_the_runners_that_expose_the_flag() -> None:
    """VACUITY FLOOR. An assertion over an empty set reads exactly like coverage.

    Four runners declared `--candidates` when this was written. If the count
    drops, either a workflow lost the flag — in which case say so here — or the
    reader broke and every assertion below is passing over nothing.
    """
    # FOUR -> THREE on 2026-08-19. `plan-sprint` dropped `--candidates` when the
    # rebuild took away the job that needed it, so the population this floor
    # bounds genuinely shrank. The floor is a POSITIVE CONTROL on the sweep — a
    # discovery that matched nothing would make every assertion below vacuous —
    # so it tracks the real count rather than pinning a number the tree has left.
    assert len(_SUBJECTS) >= 3, (
        f"expected at least three runners exposing `--candidates`; found "
        f"{[name for name, _ in _SUBJECTS]}. Fix the reader, do not weaken this.")


@pytest.mark.parametrize("runner,module", _SUBJECTS, ids=[n for n, _ in _SUBJECTS])
def test_a_workflow_grants_the_candidates_path_it_was_actually_GIVEN(
        runner: str, module: str) -> None:
    """THE GUARD. Call the grant with a non-default pool; it must match that pool.

    The call is built from the signature rather than from a per-workflow table:
    every parameter named for the candidates path gets `_ELSEWHERE`, every other
    gets a plausible default. A workflow that never accepts the path at all fails
    at the signature check, which is the state three of the four were in.
    """
    wf = importlib.import_module(module)
    grant = getattr(wf, "permitted_paths", None)
    assert callable(grant), (
        f"{module} exposes `--candidates` on its runner but has no "
        f"`permitted_paths` function. A module-level tuple cannot honour an "
        f"argument — that is the whole defect this sweep exists for.")

    params = inspect.signature(grant).parameters
    assert any("candidates" in p for p in params), (
        f"{module}.permitted_paths{tuple(params)} takes no candidates path, so "
        f"`--candidates` on {runner} cannot reach the boundary. The grant must "
        f"derive from the argument; naming this repo's pool as a literal fails a "
        f"CORRECT run at the last guard whenever the flag points elsewhere.")

    args = []
    for name in params:
        if "candidates" in name:
            args.append(_typed(params[name], _ELSEWHERE))
        elif "research" in name:
            args.append(_ELSEWHERE_DIR)
        elif "component" in name:
            args.append(Path("docs/development/alpha"))
        elif "sprint" in name:
            args.append("docs/development/sprint.md")
        else:  # a parameter this sweep has never seen — say so rather than guess
            pytest.fail(f"{module}.permitted_paths takes an unrecognised "
                        f"parameter `{name}`; teach this sweep what to pass it.")

    # AN ITEM IN THE POOL, NOT THE POOL ITSELF, since the 2026-08-26 flip. The
    # pool is a DIRECTORY now and a run never writes a directory — it writes an
    # item inside one. Asserting the directory matched would have gone red on a
    # correct grant and, worse, a grant that still matched the bare directory
    # would pass while granting nothing a run can actually write.
    placed = (_ELSEWHERE / "C-a1b2c3d4.md").as_posix()
    patterns = grant(*args)
    assert any(re.search(p, placed) for p in patterns), (
        f"{module}.permitted_paths returned {patterns}, none of which matches "
        f"`{placed}` — an item in the pool it was handed. A run pointed at "
        f"that pool is told to place a proposal there and then failed by "
        f"`boundary_crossings` for doing it, after every turn has been spent.")


@pytest.mark.parametrize("runner,module", _SUBJECTS, ids=[n for n, _ in _SUBJECTS])
def test_the_grant_still_reaches_the_DEFAULT_pool(runner: str, module: str) -> None:
    """NEGATIVE CONTROL. A grant returning `^.*$` would pass the test above.

    This is the arm that would fail if a fix widened the boundary instead of
    deriving it: the default pool must still be granted, and a SIBLING file in
    that same directory must not be. Both halves, because a grant that dropped
    its `$` anchor satisfies the first and fails the second.
    """
    wf = importlib.import_module(module)
    params = inspect.signature(wf.permitted_paths).parameters
    default = "tracked/candidates"
    args = []
    for name in params:
        if "candidates" in name:
            args.append(_typed(params[name], Path(default)))
        elif "research" in name:
            args.append(Path("docs/standards/architecture/research"))
        elif "component" in name:
            args.append(Path("docs/development/alpha"))
        elif "sprint" in name:
            args.append("docs/development/sprint.md")

    patterns = wf.permitted_paths(*args)
    placed = f"{default}/C-a1b2c3d4.md"
    assert any(re.search(p, placed) for p in patterns), (
        f"{module} no longer grants items in the default pool: {patterns}")

    # A SIBLING DIRECTORY, and it must stay out. `candidates.bak/C-x.md` is the
    # shape a dropped `$`-anchor or an unescaped `.` would let through, and it is
    # the reason the pattern ends `/[^/]+\.md$` rather than `.*`.
    sibling = "tracked/candidates.bak/C-a1b2c3d4.md"
    granting = [p for p in patterns if re.search(p, sibling)]
    assert not granting, (
        f"{module} grants `{sibling}` through {granting}. Deriving the grant must "
        f"not widen it — the pattern needs its `$` anchor and `re.escape` on the "
        f"interpolated segment.")
