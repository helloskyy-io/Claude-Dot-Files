"""A parent must hand its child every task field that child BRANCHES on.

WHY THIS MODULE EXISTS. `build_workflow.py` called `run_draft(...)` with
`task_file=` and without `plan_path=`. `plan_path` is the ONLY argument
`run_draft` branches on — it selects the plan-driven template pair — and
`task_file` is a parameter `run_draft` accepted and never read. So
`build.sh --phase <doc>` rendered the description-driven wrapper with the whole
phase document injected as an opaque `${DESCRIPTION}`, and every plan-driven
instruction this repo ships was unreachable from the major tier, while the
`build_minor` sibling — which forwards `plan_path` — always reached it.

WHY NO EXISTING GUARD COULD SEE IT, which is the part worth keeping. Every
render guard in this tree drives the CHILD entrypoint directly, supplying
`plan_path` from a fixture. Those guards prove the child renders correctly WHEN
HANDED a plan. None of them proves a parent hands it one. **A test that
constructs the input a caller is supposed to build cannot see a caller that
builds it wrong**, so the seam between parent and child was covered from both
sides and never across.

TWO ARMS, AND THEY ARE THE TWO HALVES OF THE SAME DEFECT:

  1. DEAD PARAMETER — a child entrypoint declares an argument its body never
     reads. That is a slot a caller can fill believing it did something. It was
     true of `run_draft.task_file` AND of `run_refine.task_file`; the review
     that found the first did not find the second, which is why this arm is a
     sweep rather than two deletions.

  2. DROPPED FORWARD — a parent omits an argument the child DOES read, when the
     parent has a value of that name available from its own inputs.

BOTH ARMS ARE DERIVED, NOT LISTED. There is no whitelist of known-good calls: a
new parent, a new child or a renamed field enters the population automatically.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import sys
from pathlib import Path

import pytest

TEMPORAL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TEMPORAL))

MODULES = TEMPORAL / "modules" / "assistant"


def _read_names(fn: ast.FunctionDef) -> set[str]:
    """Every bare name the function body mentions.

    Deliberately generous: a parameter used only inside an f-string, a nested
    comprehension or a default expression still counts as read. The arm below
    fails only on a parameter mentioned NOWHERE, which is the unambiguous case.
    """
    return {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}


def _params(fn: ast.FunctionDef) -> list[str]:
    return [a.arg for a in fn.args.args + fn.args.kwonlyargs]


def _entrypoints() -> dict[str, dict]:
    """Every `run_*` workflow entrypoint, with the params its body actually reads."""
    out: dict[str, dict] = {}
    for path in sorted(MODULES.rglob("*_workflow.py")):
        for fn in ast.parse(path.read_text()).body:
            if isinstance(fn, ast.FunctionDef) and fn.name.startswith("run_"):
                params = _params(fn)
                out[fn.name] = {
                    "path": path,
                    "params": params,
                    "read": [p for p in params if p in _read_names(fn)],
                }
    return out


ENTRYPOINTS = _entrypoints()


def test_the_entrypoint_census_is_not_empty() -> None:
    """Vacuity floor for both arms.

    Every assertion below iterates this mapping. If the discovery pattern stops
    matching — a rename, a move out of `*_workflow.py` — both arms pass while
    checking nothing, which is the failure this repo keeps finding in its own
    guards rather than in its code.
    """
    assert len(ENTRYPOINTS) >= 10, (
        f"only {len(ENTRYPOINTS)} workflow entrypoints discovered under {MODULES}; "
        "the discovery pattern has stopped matching and both arms are vacuous"
    )


@pytest.mark.parametrize("name", sorted(ENTRYPOINTS))
def test_no_workflow_entrypoint_declares_a_parameter_it_never_READS(name: str) -> None:
    """An accepted-and-discarded argument is a slot a caller can fill for nothing.

    This is not tidiness. A caller reading the signature sees a parameter named
    for a task source and reasonably concludes that passing it is how the task
    reaches the child. `build_workflow` did exactly that with `task_file` while
    the argument the child branches on went unpassed — the dead parameter is what
    made the omission look like a complete call.
    """
    info = ENTRYPOINTS[name]
    dead = [p for p in info["params"] if p not in info["read"]]
    assert not dead, (
        f"{info['path'].name}::{name} declares {dead}, which its body never "
        f"reads. Delete the parameter (and the arguments passing it), or use it. "
        f"A caller that fills a dead slot believes it has handed the child a task "
        f"source it never received."
    )


def _dataclass_fields(module_name: str, annotation: str) -> list[str]:
    """Field names of `annotation` if it is a dataclass in `module_name`.

    A parent receives its whole task as one frozen dataclass (`BuildInput`), so
    `task.plan_path` is available to it even though `plan_path` is not one of its
    own parameters. Without this the second arm would never look at the build
    family at all — which is the family the defect was in.
    """
    obj = getattr(importlib.import_module(module_name), annotation, None)
    if obj is None or not dataclasses.is_dataclass(obj):
        return []
    return [f.name for f in dataclasses.fields(obj)]


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(TEMPORAL).with_suffix("").parts)


def _call_sites() -> list[dict]:
    """Every call to a known workflow entrypoint, with what the caller forwards."""
    sites: list[dict] = []
    for path in sorted(MODULES.rglob("*.py")):
        tree = ast.parse(path.read_text())
        for caller in ast.walk(tree):
            if not isinstance(caller, ast.FunctionDef):
                continue
            available = set(_params(caller))
            for arg in caller.args.args + caller.args.kwonlyargs:
                if isinstance(arg.annotation, ast.Name):
                    available |= set(
                        _dataclass_fields(_module_name(path), arg.annotation.id)
                    )
            for node in ast.walk(caller):
                if not isinstance(node, ast.Call):
                    continue
                callee = (node.func.attr if isinstance(node.func, ast.Attribute)
                          else getattr(node.func, "id", ""))
                if callee not in ENTRYPOINTS or callee == caller.name:
                    continue
                params = ENTRYPOINTS[callee]["params"]
                forwarded = {k.arg for k in node.keywords if k.arg}
                # Positional arguments map by position — `run_review(input, root)`
                # forwards `task` without naming it, and reading only keywords
                # would report it as dropped.
                forwarded |= set(params[:len(node.args)])
                sites.append({
                    "where": f"{path.name}:{node.lineno}",
                    "callee": callee,
                    "forwarded": forwarded,
                    "available": available,
                })
    return sites


CALL_SITES = _call_sites()


def test_the_call_site_census_reaches_the_build_family() -> None:
    """Second vacuity floor, and it is specifically about the dataclass expansion.

    `available` for a build parent is almost entirely dataclass fields — its own
    parameters are `(task, repo_root, worktree_name)`. If `_dataclass_fields`
    silently returned nothing (a moved `BuildInput`, an import failure swallowed
    into `getattr`), the arm below would pass on every build call site while
    asserting nothing about the family the defect was in.
    """
    assert CALL_SITES, "no parent-to-child call sites discovered"
    build = [s for s in CALL_SITES if s["callee"] in ("run_draft", "run_draft_minor")]
    assert build, "the build draft children have no discovered caller"
    assert all("plan_path" in s["available"] for s in build), (
        "BuildInput's fields are not reaching the availability set, so the arm "
        "below cannot see a dropped task source on any build parent"
    )


@pytest.mark.parametrize(
    "site", CALL_SITES, ids=lambda s: f"{s['where']}->{s['callee']}"
)
def test_a_PARENT_forwards_every_task_field_its_CHILD_reads(site: dict) -> None:
    """What the child reads and the parent holds, the parent must hand over.

    SCOPED TO NAME AGREEMENT, DELIBERATELY. A child parameter the parent has no
    value for is not a finding — `run_refresh` takes a `pr_number` its parent
    never has, and `run_plan_feature` takes a `context` `plan_project` does not
    carry. Only a name the parent demonstrably holds and the child demonstrably
    reads is asserted, which keeps this free of exemptions.
    """
    required = {p for p in ENTRYPOINTS[site["callee"]]["read"] if p in site["available"]}
    dropped = sorted(required - site["forwarded"])
    assert not dropped, (
        f"{site['where']} calls {site['callee']}() without {dropped}, which that "
        f"child reads and this caller holds. A task source the child branches on "
        f"and never receives makes a whole instruction set unreachable, and no "
        f"guard that drives the child directly can see it."
    )


# --- positive controls --------------------------------------------------------
#
# BOTH PREDICATES DRIVEN ON A LITERAL, per the Testing Standard's
# *Structural tests need a positive control* and the class-check in
# `test_a_census_guard_proves_its_own_predicate.py`. The walks above are floored;
# a floor is green over a PREDICATE that has begun answering unconditionally —
# an AST shape this code stopped recognising, a keyword folded into `**kwargs` —
# while the census still finds sites. These snippets are not in the tree, so they
# exercise the failing branch the live corpus can never reach.


def _fn(src: str) -> ast.FunctionDef:
    return ast.parse(src).body[0]


def test_the_READ_PREDICATE_discriminates_on_a_literal() -> None:
    """A parameter mentioned nowhere reads as dead; one mentioned anywhere does not."""
    dead = _fn("def run_x(*, a, b):\n    return a\n")
    assert _params(dead) == ["a", "b"]
    assert [p for p in _params(dead) if p in _read_names(dead)] == ["a"], (
        "the dead-parameter arm no longer sees an unmentioned parameter"
    )

    # Read only inside an f-string and only inside a comprehension — both count,
    # and both are shapes a naive `body[0]`-style check would miss.
    live = _fn("def run_y(*, a, b):\n    return [f'{a}' for _ in b]\n")
    assert [p for p in _params(live) if p in _read_names(live)] == ["a", "b"], (
        "the dead-parameter arm now reports a USED parameter as dead, which would "
        "make it fail on correct code"
    )


def test_the_FORWARDING_PREDICATE_discriminates_on_a_literal() -> None:
    """Keyword and positional forwards are both seen; an omission is not forgiven."""
    call = next(n for n in ast.walk(_fn(
        "def parent(task):\n"
        "    child.run_z(one, two=task.two, three=task.three)\n"
    )) if isinstance(n, ast.Call))
    params = ["one", "two", "three", "four"]
    forwarded = {k.arg for k in call.keywords if k.arg} | set(params[:len(call.args)])
    assert forwarded == {"one", "two", "three"}, (
        f"the forwarding reader saw {sorted(forwarded)}; a positional argument or a "
        f"keyword has stopped being counted, which would make omissions invisible"
    )
    assert sorted({"two", "four"} - forwarded) == ["four"], (
        "the omission arm no longer reports a required-and-unforwarded argument"
    )
