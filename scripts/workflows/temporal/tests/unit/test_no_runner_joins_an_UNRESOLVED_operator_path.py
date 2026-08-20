"""No runner may join an operator-supplied path onto a path outside the mechanism.

THE ABSENCE OF A CHECK NOW HAS SYNTAX, WHICH IS THE WHOLE POINT OF THIS FILE.
`test_preflight.test_no_entrypoint_INLINES_the_operator_path_escape_check` sweeps
for a COPIED check and says in its own docstring that it cannot do the other half:

    "It cannot see a runner that takes an operator path and checks NOTHING.
     That is the more dangerous state and it is invisible to this sweep,
     because the absence of a check has no syntax."

It was right, and the more dangerous state was live. Measured by execution, five of
ten runners accepted an escaping path and read through it — `run_triage_candidates`,
`run_plan_sprint`, `run_plan_project`, `run_research` and `run_research_minor`. These
run under `--dangerously-skip-permissions`, so an escaping path is an unattended run
writing wherever it is pointed.

ALL FIVE RE-MEASURED ON 2026-08-16 against the pre-fix code, because three artifacts
said "three of those" where this one said five and a count nobody had re-run is not a
record. Driven from `cf1776e`: `run_research --refresh` on an escaping pool ENUMERATED
AND READ `/tmp/…/raw/probe-paper.md` and reported it due; `run_research_minor` reported
it past its window; `run_triage_candidates` and `run_plan_sprint` each parsed 92 rows
out of an escaping `--candidates`; and `run_plan_project`, which has no `--dry-run`,
carried both escaping paths into its dispatch call (stubbed) — the worst of the five,
since it would have cut a worktree and spent against them. Five, not three; the other
three sites were corrected to match rather than this one softened.

WHY A JOIN AND NOT A MISSING CALL. An omission cannot be grepped; the thing the
omission is FOR can be. Every one of those five reached the escaping path the same
way — `repo_root / a.<flag>` — because a raw argparse string is not a path until
something joins it to a root. So the property is stated positively and about the
tree: **an argparse namespace attribute may not appear as an operand of a path
join.** A runner that declares its paths with `RepoPathParser.add_repo_path` reads
them out of the resolved mapping instead, and never writes the join at all.

DERIVED FROM THE TREE, NEVER LISTED. Both the runner set and the namespace variable
inside each runner are discovered — the runners by glob, the namespace by finding
what `parse_args`/`parse_with_preflight` was assigned to. An eleventh runner is
covered on the day it is written rather than on the day someone remembers to add
it to a list, which is the failure mode that let the original five accumulate.

`Path.relative_to` WOULD NOT HAVE CAUGHT THE ORIGINAL DEFECT AND IS NOT WHAT THIS
ASKS FOR. It is lexical: `repo_root / "../../x"` still reads as being under
`repo_root`, and `.exists()` follows `..` too. The `..` has to be COLLAPSED first,
which is `resolve_operator_paths`' subject and the reason the remedy is a resolver
rather than one more `if`.

WHAT THIS DOES NOT LOOK AT, so it is not read as covering more than it does:

  * **Paths that are deliberately outside the repo.** `--task-file` on the research
    runners and `--phase` on the build runners are read from wherever the operator
    points them, on purpose. They are never JOINED to a root, so they are invisible
    here — correctly, but it means a "no operator path escapes" reading of this file
    would be wrong. What they may do is bounded by being reads of a task source.
    Their RELATIVE form is anchored to the repo root by
    `assistant_activities.anchor_task_source`, which is a base and not a boundary;
    `test_a_task_SOURCE_path_is_anchored_to_the_repo.py` owns that property and
    this file is silent about it.
  * **Workflow modules.** Only `run_*.py` is swept. A module one altitude up doing
    its own join is a different question with a different mechanism
    (`boundary_crossings`), and this guard would report nothing about it.
  * **String-level assembly.** `os.path.join` is caught; an f-string is NOT, because
    every runner legitimately interpolates argument values into its banner and a
    sweep that flagged those would be turned off. An `f"{root}/{a.flag}"` therefore
    passes this. That is a real hole and it is stated rather than papered over.
  * **Aliasing DEEPER THAN ONE HOP.** One hop IS caught — see `_aliased_operator_locals`
    — because it was not, and that was a live escape rather than a theoretical one.
    A pass that kept `add_repo_path` for two paths, dropped the third to plain
    `add_argument`, and laundered the join through a local (`research_arg = a.research`
    then `repo_root / research_arg`) passed BOTH guards in this directory with the
    whole suite green, and `run_plan_sprint.py --dry-run --research ../../…/tmp/x`
    exited 0. Two hops (`x = a.flag; y = x; root / y`) are still invisible, as is a
    value that round-trips through a list, a dict or a function. The rule this
    enforces is therefore *"the join is visible within one alias"*, not *"no operator
    string can ever reach a join"* — the second is not decidable by a sweep, and
    claiming it would be the more dangerous error.
  * **Whether the declared KIND is right.** A file declared `kind="dir"` passes here
    and fails at runtime; `resolve_operator_paths` owns that.
  * **How WIDE the resulting grant is.** A contained path can still be granted too
    much. `test_a_grant_follows_its_flag` and `permitted_paths` own that altitude.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
_RUNNERS = sorted(_SCRIPTS.glob("run_*.py"))

# What a parse produces. `parse_args` is argparse's; `parse_with_preflight` is
# `RepoPathParser`'s, and it returns a namespace as its FIRST element — the raw
# strings are still on it, which is what makes it worth sweeping even after the
# fix. Both are matched by attribute name so the qualifier does not matter.
_PARSE_CALLS = ("parse_args", "parse_with_preflight")


def _is_parse_call(node: ast.AST) -> bool:
    return (isinstance(node, ast.Call)
            and (getattr(node.func, "attr", None) in _PARSE_CALLS
                 or getattr(node.func, "id", None) in _PARSE_CALLS))


def _namespace_names(tree: ast.AST) -> set[str]:
    """Every local name bound to the result of a parse, tuple targets included.

    `a = p.parse_args(argv)` binds one; `a, repo_root, resolved =
    p.parse_with_preflight(argv)` binds `a` and two paths that are already
    contained. Over-collecting here is deliberate and safe: `repo_root` and
    `resolved` have no attribute access in any runner, so they contribute no
    findings, while under-collecting would make the sweep silently inert.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not _is_parse_call(node.value):
            continue
        for target in node.targets:
            elements = target.elts if isinstance(target, ast.Tuple) else [target]
            names.update(e.id for e in elements if isinstance(e, ast.Name))
    return names


def _aliased_operator_locals(tree: ast.AST, namespaces: set[str]) -> dict[str, str]:
    """Locals bound DIRECTLY to a namespace attribute — `research_arg = a.research`.

    ONE HOP, AND THE HOP IS THE WHOLE POINT. Without this the sweep matched on the
    SPELLING of the defect rather than on the defect, so moving the attribute read
    one line up defeated it — measured, not supposed: a runner keeping
    `add_repo_path` for two paths and laundering the third through a local passed
    this file, passed the execution guard beside it, and still accepted
    `../../../../tmp/…` at exit 0.

    Deliberately NOT a general taint analysis. It resolves `x = a.flag` and stops;
    it does not follow `y = x`, a list, a dict or a call. A sweep that tried would
    need the runner's whole dataflow and would start reporting on its own
    approximations — and the omission it is really guarding against is a person
    moving one line, not a person building a laundering chain. The residue is
    stated in this module's docstring rather than implied away.
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if not (isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and value.value.id in namespaces):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                aliases[target.id] = f"{value.value.id}.{value.attr}"
    return aliases


def _joined_operator_attrs(tree: ast.AST, namespaces: set[str]) -> list[tuple[int, str]]:
    """Every `(line, expression)` where operator input is joined to a path.

    Three shapes, because those are the three ways this tree spells a join:
    `root / a.flag`, `root.joinpath(a.flag)`, and `os.path.join(root, a.flag)`.
    Both operands of `/` are checked rather than only the right, so the reversed
    spelling cannot pass by being unusual.

    An operand counts if it is a namespace attribute (`a.flag`) OR a local aliased
    to one a single hop earlier (`f = a.flag; root / f`) — see
    `_aliased_operator_locals` for why the second is not optional.
    """
    aliases = _aliased_operator_locals(tree, namespaces)

    def describe(node: ast.AST) -> str | None:
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id in namespaces):
            return f"{node.value.id}.{node.attr}"
        if isinstance(node, ast.Name) and node.id in aliases:
            return f"{node.id} (aliased from {aliases[node.id]})"
        return None

    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            for side in (node.left, node.right):
                if (what := describe(side)) is not None:
                    found.append((side.lineno, what))
        elif isinstance(node, ast.Call):
            qualifier = getattr(node.func, "attr", None)
            if qualifier in ("joinpath", "join"):
                for arg in node.args:
                    if (what := describe(arg)) is not None:
                        found.append((arg.lineno, what))
    return found


_PARSED = {r.name: ast.parse(r.read_text()) for r in _RUNNERS}
_NAMESPACES = {name: _namespace_names(tree) for name, tree in _PARSED.items()}


def test_the_sweep_finds_the_runners() -> None:
    """VACUITY FLOOR. An assertion over an empty set reads exactly like coverage."""
    assert len(_RUNNERS) >= 10, (
        f"the runner sweep found only {[p.name for p in _RUNNERS]}. Fix the "
        f"reader, do not weaken this.")


def test_the_sweep_actually_LOCATED_a_namespace_in_most_runners() -> None:
    """SECOND VACUITY FLOOR, and it is the one that matters here.

    Every check below is scoped by `_namespace_names`. If that reader breaks — a
    runner renames its parse call, argparse grows a new entrypoint — it returns
    empty sets, every runner has nothing to examine, and the suite goes green
    while reporting on nothing. A guard that walks a tree can pass vacuously when
    its own scoping is wrong, so the count of things EXAMINED is asserted, not
    just the count of things found.
    """
    located = {name for name, ns in _NAMESPACES.items() if ns}
    assert len(located) >= 8, (
        f"only {sorted(located)} yielded a parse-result variable out of "
        f"{len(_RUNNERS)} runners. Every assertion below is scoped by this, so a "
        f"broken reader is indistinguishable from a clean tree.")


@pytest.mark.parametrize("runner", _RUNNERS, ids=lambda p: p.name)
def test_a_runner_never_JOINS_an_unresolved_operator_path(runner: Path) -> None:
    """THE GUARD. A raw argparse string may not become a path here.

    Read the offending expression as the defect itself: `repo_root / a.candidates`
    is an operator string joined to a root with nothing between them, and both
    `Path.relative_to` and `.exists()` are blind to the `..` it may contain. The
    remedy is one line — declare it with `add_repo_path` and read it out of the
    resolved mapping — not an extra check beside the join.
    """
    offenders = _joined_operator_attrs(_PARSED[runner.name], _NAMESPACES[runner.name])
    assert not offenders, (
        f"{runner.name} joins un-resolved operator input onto a path at "
        f"{[f'line {n}: {e}' for n, e in offenders]}. Declare it with "
        f"`RepoPathParser.add_repo_path(...)` and read the value out of the "
        f"mapping `parse_with_preflight` returns. A raw argparse string joined to "
        f"a root is exactly how five runners accepted `../../../../tmp/…` and "
        f"read through it under `--dangerously-skip-permissions`.")


def test_the_detector_FIRES_on_each_shape_it_claims_to_cover() -> None:
    """DISCRIMINATOR. Proves the reader reads, and that green above means clean.

    Derived from what this module's docstring claims about itself — *"three
    shapes, because those are the three ways this tree spells a join"* — rather
    than from whatever is easy to break. Each sample is SELF-CONTAINED source
    text, never a copy of a real runner: a control sharing a fixture with the code
    under test over-fires and proves nothing about either.

    The negative sample is the shape the fixed runners now use. Without it, a
    detector that flagged every attribute access would satisfy the three positive
    cases and fail the whole tree.
    """
    positives = {
        "slash": "a = p.parse_args(v)\nx = root / a.candidates\n",
        "reversed slash": "a = p.parse_args(v)\nx = a.candidates / root\n",
        "joinpath": "a = p.parse_args(v)\nx = root.joinpath(a.candidates)\n",
        "os.path.join": "a = p.parse_args(v)\nx = os.path.join(root, a.candidates)\n",
        "tuple target": "a, r, paths = p.parse_with_preflight(v)\nx = r / a.sprint\n",
        # THE SHAPE THAT WAS LIVE. Every other positive here was written from the
        # docstring; this one was written from a mutation that passed, and it is
        # the reason `_aliased_operator_locals` exists.
        "aliased local": "a = p.parse_args(v)\nresearch_arg = a.research\nx = root / research_arg\n",
        "aliased into joinpath": "a = p.parse_args(v)\nf = a.candidates\nx = root.joinpath(f)\n",
    }
    for label, source in positives.items():
        tree = ast.parse(source)
        assert _joined_operator_attrs(tree, _namespace_names(tree)), (
            f"the detector did not fire on the `{label}` shape, which this "
            f"module's docstring claims to cover. Every green result above is "
            f"therefore unproven for that shape.")

    clean = ("a, repo_root, resolved = p.parse_with_preflight(v)\n"
             "cands = resolved['candidates']\n"
             "derived = cands.parent / 'direction.md'\n"
             "print(f'{a.candidates}')\n"
             # The alias rule must not fire on a local read out of the RESOLVED
             # mapping and then joined — that is the shape every fixed runner
             # uses, and flagging it would make the guard unusable the same week.
             "research = resolved['research']\n"
             "paper = research / 'raw'\n")
    tree = ast.parse(clean)
    assert not _joined_operator_attrs(tree, _namespace_names(tree)), (
        "the detector fired on the shape the fixed runners use — reading a "
        "resolved path out of the mapping, deriving from it with a literal, and "
        "printing the raw argument in a banner. A guard that cannot tell those "
        "from the defect would be turned off within a week.")
