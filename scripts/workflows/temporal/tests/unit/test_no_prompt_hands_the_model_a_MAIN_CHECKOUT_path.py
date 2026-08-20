"""A path rendered into a prompt must resolve inside the WORKTREE the model runs in.

THE DEFECT, verified by rendering rather than by reading. The major build tier
began rendering `${PLAN_PATH}` on 2026-08-19 — before that the value never reached
a prompt at all — and it rendered the RAW operator string:

    run_draft(repo_root=/main/checkout, worktree=/tmp/wt,
              plan_path="/main/checkout/docs/development/x/phase2.md")
    -> "Plan document: /main/checkout/docs/development/x/phase2.md"

The model runs in `/tmp/wt` and was handed a MAIN CHECKOUT path. It then reads the
main checkout's copy of the plan doc rather than its branch's — so a correction
pass on a branch that revised its own phase doc builds against the superseded spec
— and any edit it makes to that doc lands outside the worktree and outside the PR.

THIS IS AN OLD CLASS ARRIVING SOMEWHERE NEW, WHICH IS WHY IT WAS MISSED.
`test_model_gets_the_worktree_path.py` was written for exactly this failure after
PR #84 and PR #86 wrote research papers into the main checkout. It sweeps
`modules/assistant/research/*/` and keys on the name `RESEARCH_DIR`, so the build
family's brand-new render arrived uncovered by the guard named after its own bug.
The producing run classified it "pre-existing, unmeasured"; it was pre-existing on
the MINOR tier and newly reachable on the one it had just wired.

WHAT THIS CHECKS, AND WHY IT IS TWO CHECKS.

  1. **The composition, at runtime.** `path_for_the_model` + the child's render must
     together put no `repo_root`-absolute path in front of the model. That is a
     property of the rendered OUTPUT, so it is asserted on the output.

  2. **The wiring, statically, over a population DERIVED FROM THE WHOLE TREE.** A
     property that holds for a composition nobody calls is worth nothing. Every
     parent→child edge in `modules/assistant/` is found by resolving `<alias>.run_*`
     calls through the parent's own imports; for each edge, the parameters the CHILD
     renders directly into a placeholder are computed from the child's own dict
     literals, and each path-shaped one must arrive through `path_for_the_model`.

     THE HARDCODED PAIR LIST THIS REPLACED WAS THE REVIEW FINDING. Written as
     `_TIERS = [(build, draft), (build_minor, draft_minor)]`, it re-derived the
     rendered PARAMETERS but not the POPULATION — so a third build tier, or
     `plan_revision` gaining a rendered path, would have escaped the guard silently
     while the module's own docstring claimed to cover the class. That is the shape
     this whole PR exists to retire, reproduced in the fix for it.

WHY "DIRECTLY rendered" AND NOT MERELY "APPEARS IN A PLACEHOLDER VALUE". The broad
form flags eight edges that are all correct: the research children re-anchor
`research_dir` internally with `act.in_worktree()` and render the LOCAL (`"RESEARCH_
DIR": str(pool)`), while the parameter itself survives only inside a PR title
(`f"research: {research_dir}"`). An over-matching gate that reds on eight correct
call sites teaches the next author to weaken it, which is worse than no gate. So
the predicate is: a dict value whose ENTIRE name set is one parameter. That is the
"go and read this path" shape and nothing else.

WHAT THIS DOES NOT LOOK AT:

  * **Containment.** Nothing here refuses a path outside the repo — four spec
    surfaces state `--task-file` and `--phase` may point outside on purpose, and
    that ruling is untouched. An out-of-repo ABSOLUTE path is rendered verbatim, and
    the control below pins that so the fix cannot degrade into "strip absolute
    paths".
  * **What the model READS with.** `task_text` correctly uses the RESOLVED absolute
    path to open the file; the split between reading and showing is deliberate and
    `path_for_the_model`'s docstring owns it.
  * **The research family's `RESEARCH_DIR`**, by the ruling above: it is rendered
    from a local rather than from the parameter, and `test_model_gets_the_worktree_
    path.py` owns that axis with the mechanism (`in_worktree`) that fits it.
  * **A rendered path argument whose NAME says nothing about paths.** The wiring
    check only demands anchoring for parameters containing `path`, `file` or `dir`,
    because `description` and `pr_number` are directly rendered too and anchoring
    either would be nonsense. A future `spec_ref` or `source_doc` carrying a
    filesystem location would pass. This is a real hole and it is named rather than
    hidden: the cheapest close is to keep naming such arguments after what they are.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest import mock

import pytest

from modules.assistant import assistant_activities as shared_act
from modules.assistant.build import build_activities as build_act
from modules.assistant.build.build_draft import build_draft_workflow as draft
from modules.assistant.build.build_draft_minor import build_draft_minor_workflow as draft_minor

_ASSISTANT = Path(shared_act.__file__).resolve().parent

_REPO_ROOT = Path("/main/checkout")
_WORKTREE = Path("/tmp/wt")
_RELATIVE = "docs/development/x/phase2_scratch.md"
_IN_REPO_ABSOLUTE = str(_REPO_ROOT / _RELATIVE)
_OUT_OF_REPO = "/tmp/elsewhere/brief_scratch.md"
_CLIMBING_RELATIVE = "../shared/brief_scratch.md"

_ANCHOR = "path_for_the_model"

# Parameter names that carry a filesystem location. See the docstring's last bullet
# for what this heuristic cannot see.
_PATH_TOKENS = ("path", "file", "dir")

# The children whose render is exercised at runtime below. The STATIC check derives
# its own population from the tree; this list is only the two entrypoints that
# accept a `plan_path` today, and `test_the_runtime_pairs_match_the_derivation`
# fails if the tree ever disagrees with it.
_RENDERING_CHILDREN = [
    pytest.param(draft, "run_draft", id="build_draft"),
    pytest.param(draft_minor, "run_draft_minor", id="build_draft_minor"),
]


# --- the readers ----------------------------------------------------------------

def _directly_rendered_parameters(source: str) -> set[str]:
    """Parameters this module renders AS a whole placeholder value.

    `{"PLAN_PATH": plan_path or ""}` counts — the entire value is that one
    parameter, so the model is being pointed at it. `{"SUBMIT_PROMPT":
    act.submit_prompt(pr, f"research: {research_dir}")}` does not: the parameter is
    one ingredient of a sentence, not a location the model is told to open.
    """
    tree = ast.parse(source)
    entrypoints = [n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name.startswith("run_")]
    if not entrypoints:
        return set()
    params = {a.arg for a in entrypoints[0].args.args + entrypoints[0].args.kwonlyargs}

    rendered: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                continue
            names = {n.id for n in ast.walk(value) if isinstance(n, ast.Name)}
            if len(names) == 1 and names <= params:
                rendered |= names
    return rendered


def _child_edges() -> list[tuple[Path, Path, str, str, ast.expr]]:
    """Every (parent, child, entrypoint, kwarg, expression) the assistant tree wires.

    The alias in `<alias>.run_x(...)` is resolved through the parent's own
    `from ... import ... as ...` statements to a module STEM, then located in the
    tree. An alias that resolves to no module or to several is skipped rather than
    guessed at — `test_the_derivation_found_the_build_edges` is what stops that
    skip from quietly emptying the population.
    """
    edges = []
    for parent in sorted(_ASSISTANT.rglob("*_workflow.py")):
        tree = ast.parse(parent.read_text())
        aliases = {a.asname or a.name: a.name
                   for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                   for a in n.names}
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr.startswith("run_")
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in aliases):
                continue
            candidates = list(_ASSISTANT.rglob(aliases[node.func.value.id] + ".py"))
            if len(candidates) != 1:
                continue
            child = candidates[0]
            rendered = _directly_rendered_parameters(child.read_text())
            for kw in node.keywords:
                if kw.arg and kw.arg in rendered:
                    edges.append((parent, child, node.func.attr, kw.arg, kw.value))
    return edges


def _path_edges() -> list[tuple[Path, Path, str, str, ast.expr]]:
    return [e for e in _child_edges() if any(t in e[3] for t in _PATH_TOKENS)]


def _edge_id(edge) -> str:
    parent, child, entrypoint, kwarg, _expr = edge
    return f"{parent.parent.name}->{child.parent.name}.{kwarg}"


# --- 1. the composition, at runtime -------------------------------------------

def _render(child, entrypoint: str, plan_path: str | None) -> str:
    """Capture what the child hands the model, with nothing else running.

    Patched on the child's OWN `act` alias rather than on `assistant_activities`:
    the modules in this fleet do not all alias the same object, and patching the
    wrong one lets a real dispatch through.
    """
    captured: dict[str, str] = {}

    def _capture(prompt: str, **_kw) -> str:
        captured["prompt"] = prompt
        return "https://github.com/o/r/pull/9"

    with mock.patch.object(child.act, "run_claude", _capture), \
            mock.patch.object(child.act, "pr_branch", lambda n, r: "a-branch-name"):
        getattr(child, entrypoint)(
            description="the task", repo_root=_REPO_ROOT, worktree=_WORKTREE,
            plan_path=plan_path,
        )

    assert "prompt" in captured, (
        f"{entrypoint} never called `run_claude`, so nothing was rendered and "
        f"every assertion below would pass over an empty capture."
    )
    return captured["prompt"]


@pytest.mark.parametrize("child,entrypoint", _RENDERING_CHILDREN)
def test_an_ABSOLUTE_in_repo_phase_is_shown_to_the_model_repo_relative(
        child, entrypoint: str) -> None:
    """THE GATE. `--phase <abs in-repo>` must not put the main checkout in a prompt."""
    prompt = _render(child, entrypoint,
                     build_act.path_for_the_model(_REPO_ROOT, _IN_REPO_ABSOLUTE))

    assert str(_REPO_ROOT) not in prompt, (
        f"{entrypoint} rendered a path under {_REPO_ROOT} while the model runs in "
        f"{_WORKTREE}. It would read the MAIN CHECKOUT's copy of the doc — the "
        f"branch's revisions invisible to it — and any edit it made would land "
        f"outside the PR entirely."
    )
    assert _RELATIVE in prompt, (
        f"{entrypoint} rendered neither the main-checkout path nor the "
        f"repo-relative form {_RELATIVE!r}. The path did not reach the model at "
        f"all, which passes the assertion above for the wrong reason."
    )


@pytest.mark.parametrize("child,entrypoint", _RENDERING_CHILDREN)
def test_a_RELATIVE_phase_is_unchanged(child, entrypoint: str) -> None:
    """The case that always worked must keep working, byte for byte.

    A relative string resolves correctly wherever the model is standing, which is
    the whole reason the in-repo answer above is the relative form.
    """
    shown = build_act.path_for_the_model(_REPO_ROOT, _RELATIVE)
    assert shown == _RELATIVE
    assert _RELATIVE in _render(child, entrypoint, shown)


@pytest.mark.parametrize("child,entrypoint", _RENDERING_CHILDREN)
def test_an_OUT_OF_REPO_absolute_phase_is_still_rendered_VERBATIM(
        child, entrypoint: str) -> None:
    """THE CONTROL, and it is what stops the fix going vacuous.

    "Render nothing absolute" and "render nothing under the repo root" pass the
    gate above identically. They differ here: a plan doc genuinely outside the repo
    has no worktree-local copy to point at, rewriting it would be inventing an
    answer, and `--phase` is deliberately allowed to point outside the repo. If
    this ever goes red, the fix has started refusing paths — which is the
    containment ruling nobody has made.
    """
    shown = build_act.path_for_the_model(_REPO_ROOT, _OUT_OF_REPO)
    assert shown == _OUT_OF_REPO
    assert _OUT_OF_REPO in _render(child, entrypoint, shown)


@pytest.mark.parametrize("child,entrypoint", _RENDERING_CHILDREN)
def test_a_CLIMBING_relative_phase_is_resolved_rather_than_passed_through(
        child, entrypoint: str) -> None:
    """THE THIRD CASE, and the first fix for this defect got it wrong.

    `--phase ../shared/notes.md` is a supported input — `resolve_task_source`'s
    docstring says so in as many words — and it is anchored at the REPO ROOT for
    reading. Passed through verbatim it would be read by the model from the
    WORKTREE, which is not a sibling of the repo: anchored at
    `/main/shared/notes.md`, opened at `/tmp/shared/notes.md`. Same defect as the
    absolute case, one input over, and it survived the fix written for it.
    """
    shown = build_act.path_for_the_model(_REPO_ROOT, _CLIMBING_RELATIVE)
    assert shown == "/main/shared/brief_scratch.md", (
        f"an escaping relative --phase rendered as {shown!r}. It must be the "
        f"RESOLVED absolute path — the one form that means the same thing from the "
        f"repo root and from the worktree."
    )
    prompt = _render(child, entrypoint, shown)
    assert _CLIMBING_RELATIVE not in prompt and shown in prompt


# --- 2. the wiring, statically, over the derived population ---------------------

def test_the_derivation_found_the_build_edges() -> None:
    """VACUITY FLOOR. Every skip in `_child_edges` is a chance to find nothing."""
    found = {_edge_id(e) for e in _path_edges()}
    assert found == {"build->build_draft.plan_path",
                     "build_minor->build_draft_minor.plan_path"}, (
        f"the parent->child edges carrying a directly-rendered PATH argument are "
        f"{sorted(found)}. Two are expected. If a third appeared it is now covered "
        f"— extend this expectation deliberately. If one vanished, either the "
        f"readers broke or a render was removed, and the check below is asserting "
        f"over less than this module claims."
    )


def test_the_reader_distinguishes_a_RENDERED_parameter_from_a_MENTIONED_one() -> None:
    """CONTROL ON `_directly_rendered_parameters`, on synthetic source.

    The real tree can only exercise the passing case, and both halves of this
    predicate have a way to be wrong: too broad flags the eight correct research
    edges, too narrow flags nothing at all and the gate above is decoration.
    """
    source = (
        "def run_x(*, plan_path, research_dir, pr_number, worktree):\n"
        "    pool = anchor(research_dir, worktree)\n"
        "    values = {'PLAN_PATH': plan_path or '',\n"
        "              'RESEARCH_DIR': str(pool),\n"
        "              'SUBMIT': submit(pr_number, f'research: {research_dir}')}\n"
        "    return values\n"
    )
    rendered = _directly_rendered_parameters(source)
    assert "plan_path" in rendered, (
        "the reader missed a parameter rendered as a whole placeholder value — the "
        "exact shape it exists to find. Everything downstream is now vacuous.")
    assert "research_dir" not in rendered, (
        "the reader counted a parameter that only appears INSIDE a sentence. That "
        "over-match reds eight correct call sites in the research family, and a "
        "gate that reds on correct code gets weakened rather than obeyed.")
    assert "pr_number" not in rendered, (
        "`pr_number` reaches the placeholder only as one argument of a call, so it "
        "is not a location the model is pointed at.")


def test_every_rendered_path_reaches_the_child_ANCHORED() -> None:
    """THE WIRING FACT. The composition tested above must be the one that runs."""
    unanchored = []
    for parent, child, entrypoint, kwarg, expr in _path_edges():
        calls = {getattr(n.func, "id", None) or getattr(n.func, "attr", None)
                 for n in ast.walk(expr) if isinstance(n, ast.Call)}
        if _ANCHOR not in calls:
            unanchored.append(
                f"{parent.parent.name}.{entrypoint} passes {kwarg}="
                f"{ast.unparse(expr)} to {child.parent.name}")

    assert not unanchored, (
        "these parents hand a child a path argument that the child renders straight "
        "into a prompt, without anchoring it:\n\n  "
        + "\n  ".join(unanchored)
        + f"\n\nAn operator may supply it as an absolute path into the MAIN "
          f"CHECKOUT, and the model runs in the worktree — so it must go through "
          f"`{_ANCHOR}(repo_root, ...)`, which renders an in-repo path relative, "
          f"resolves an escaping relative one, and leaves a genuinely out-of-repo "
          f"absolute one alone."
    )


def test_the_runtime_pairs_match_the_derivation() -> None:
    """The two halves of this module must be looking at the same children.

    `_RENDERING_CHILDREN` is a literal because the runtime half needs real imported
    modules and a call signature it can satisfy. This is what stops it drifting
    away from the population the static half derives — which is precisely the
    failure the static half was rewritten to remove.
    """
    derived = {e[1].parent.name for e in _path_edges()}
    exercised = {p.values[0].__name__.rsplit(".", 1)[-1].removesuffix("_workflow")
                 for p in _RENDERING_CHILDREN}
    assert derived == exercised, (
        f"the static check derives {sorted(derived)} from the tree while the "
        f"runtime checks exercise {sorted(exercised)}. Add the missing child to "
        f"`_RENDERING_CHILDREN` — a child covered by the wiring check alone is "
        f"only proven to CALL the anchor, never that the anchor's output is safe."
    )


def test_the_static_reader_is_LOOKING_AT_a_real_call() -> None:
    """CONTROL ON `_child_edges`: it must not match indiscriminately.

    A reader that matched every call would put the whole tree in the population and
    the assertions above would be about noise. `build_activities` dispatches no
    child workflow at all, so nothing in it may appear as a parent.
    """
    parents = {e[0].stem for e in _child_edges()}
    assert parents, "`_child_edges` found no parent->child edge anywhere in the tree"
    assert "build_activities" not in parents
    assert {"build_workflow", "build_minor_workflow"} <= parents, (
        f"the reader found parents {sorted(parents)}, which does not include the "
        f"two build parents it is known to wire. Fix the reader; the checks above "
        f"are asserting against whatever it happened to find."
    )


def test_the_reader_reads_the_CHILD_and_not_the_parent() -> None:
    """The two build children must expose `plan_path` as directly rendered.

    Asserted through `inspect.getsource` on the imported modules rather than through
    `_child_edges`, so a path-resolution bug in the edge finder cannot make this
    agree with it for the wrong reason.
    """
    for child in (draft, draft_minor):
        rendered = _directly_rendered_parameters(inspect.getsource(child))
        assert "plan_path" in rendered, (
            f"{child.__name__} no longer renders `plan_path` as a whole placeholder "
            f"value. Either it stopped rendering it — in which case this module is "
            f"obsolete and should be deleted deliberately — or the reader is broken."
        )
