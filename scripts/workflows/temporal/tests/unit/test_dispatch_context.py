"""The run context: derived once, frozen, and previewed by the same renderer.

WHAT IS UNDER TEST. `RunContext` is the object Workflow Decomposition Phase 4
introduces so that a run has ONE place its derived values come from. Three
properties are checkable here and each had a measured failure behind it:

  * THE WORKTREE NAME FOLLOWS THE WORKFLOW KEY. Eleven sites derived it
    independently and `run_build_minor` had drifted — `workflow_key="build-minor"`
    beside a worktree named `build-…`, so its trees were indistinguishable on
    disk from the `build` parent's.
  * THE ECHO IS UNGATED. It was gated on *is this invocation the run* — `writer
    is None`, a proxy for *constructed here* — until this phase's standalone
    children made the proxy wrong; see `RunContext.echo`. It was never gated on
    `verbose` and never on `minted`, and an operator retrying with `--run-id X`
    has `minted=False` while being the caller who most needs to see what the
    retry derived.
  * THE REHEARSAL AND THE LIVE RUN PRINT THE SAME OBJECT. A `--dry-run` that
    assembles its own copy previews something that is not what runs, and this
    family has shipped that bug once already (`run_review`'s own docstring
    records `render_prompt` diverging between the two paths).

WHAT THIS DOES NOT COVER. It says nothing about whether a field's value is
CORRECT for a given invocation — `repo_root` comes from `preflight`, which has
its own suite — only about what the context does with what it is handed. The
call-site property (nothing re-derives the worktree name) is
`test_a_worktree_NAME_comes_from_the_RUN_CONTEXT.py`, and the four-part field
documentation is `test_every_context_FIELD_STATES_ITSELF.py`.
"""

from __future__ import annotations

import ast
import dataclasses
import io
import sys
from pathlib import Path

import pytest

FLEET = Path(__file__).resolve().parents[2]
ENTRYPOINTS = FLEET / "scripts"
sys.path.insert(0, str(ENTRYPOINTS))

from dispatch_context import DRY_RUN_RUN_ID, RunContext  # noqa: E402
from dispatch_identity import RunIdentity  # noqa: E402

FROZEN_CLOCK = lambda: 1788240530.9  # noqa: E731 — a pinned instant, not a helper


def _live(tmp_root: Path, **over) -> RunContext:
    """`RunContext.build` — the LIVE constructor — against a scratch journal root.

    ⚠ THIS EXISTS BECAUSE NOTHING DROVE `build` AT ALL, and that is how the value
    this whole object exists to consolidate came to be written TWICE. `build`
    and `for_dry_run` each carried their own `f"{key}-{int(clock())}"`; every
    assertion below went through `for_dry_run`, so perturbing the live copy
    alone left the entire suite green (measured 2026-09-01: 3051 passed) while
    the rehearsal previewed a name no run would use. Requirement 4's own defect,
    inside requirement 4's fix.

    `config_path` points at a generated config so the boundary's journal-root
    resolution lands in `tmp_path` — the session fixture in `tests/conftest.py`
    already redirects `CONFIG_PATH`, and this is the same protection stated at
    the call rather than relied on.
    """
    config = tmp_root / "config.yaml"
    config.write_text(f'journal:\n  root: "{tmp_root / "journal"}"\n  deployment: user\n',
                      encoding="utf-8")
    base = dict(identity=RunIdentity(run_id="20260901-abc", writer=None, minted=True),
                repo_root=Path("/repo"), workflow_key="plan-draft",
                pr_number=None, target="development/x/y",
                config_path=config, clock=FROZEN_CLOCK)
    base.update(over)
    return RunContext.build(**base)


def _ctx(**over) -> RunContext:
    base = dict(repo_root=Path("/repo"), workflow_key="plan-draft",
                pr_number=None, target="development/x/y", clock=FROZEN_CLOCK)
    base.update(over)
    return RunContext.for_dry_run(**base)


# --- the worktree name -------------------------------------------------------

@pytest.mark.parametrize("key", [
    "plan", "plan-draft", "plan-refine", "plan-sprint", "plan-project",
    "plan-revision", "triage-candidates", "research", "build", "build-minor",
    "review-pr",
])
def test_the_worktree_name_FOLLOWS_THE_WORKFLOW_KEY(key: str) -> None:
    """Every key, not a sample — the drift was in exactly one of eleven.

    Parametrised over the whole fleet because the defect this replaces was a
    single runner whose name and key disagreed. A test that checked two keys
    would have passed over it.
    """
    assert _ctx(workflow_key=key).worktree_name == f"{key}-1788240530"


@pytest.mark.parametrize("key", ["plan-draft", "build", "build-minor", "review-pr"])
def test_the_LIVE_constructor_derives_the_SAME_NAME_as_the_rehearsal(
        key: str, tmp_path: Path) -> None:
    """The half nothing drove, which is why the expression could be duplicated.

    A sample of keys rather than all eleven: the parametrised test above holds
    the key-following property, and what this adds is that `build` — the
    constructor a real run uses — reaches it by the same route.
    """
    assert _live(tmp_path, workflow_key=key).worktree_name == f"{key}-1788240530"


def test_build_minor_NO_LONGER_NAMES_ITS_TREE_LIKE_THE_BUILD_PARENT() -> None:
    """The drift, asserted as itself rather than as a corollary.

    `run_build_minor` built `f"build-{...}"` under `workflow_key="build-minor"`,
    so `.claude/worktrees/build-…` held trees from two different workflows and
    `/cleanup-merged-worktrees` could not tell them apart. This is a BEHAVIOUR
    CHANGE shipped deliberately, so it gets an assertion of its own that will
    fail loudly if anyone "restores" the old name.
    """
    minor = _ctx(workflow_key="build-minor").worktree_name
    major = _ctx(workflow_key="build").worktree_name
    assert minor.startswith("build-minor-")
    assert minor != major
    assert not minor.startswith(f"{major}-"), (
        "the minor tier's name is a prefix-extension of the major tier's, so a "
        "prefix match still cannot tell them apart")


def test_the_context_is_FROZEN() -> None:
    """A boundary value that can be reassigned downstream is not a boundary value."""
    ctx = _ctx()
    for field in ("worktree_name", "repo_root", "workflow_key", "target"):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(ctx, field, "mutated")


def test_the_context_EXTENDS_identity_rather_than_sitting_beside_it() -> None:
    """`is_the_run` and the three identity fields come for free, or they diverge."""
    assert issubclass(RunContext, RunIdentity)
    ctx = _ctx()
    assert ctx.is_the_run is True
    names = {f.name for f in dataclasses.fields(RunContext)}
    assert {"run_id", "writer", "minted"} <= names


# --- the echo ----------------------------------------------------------------

def _echoed(ctx: RunContext) -> str:
    buffer = io.StringIO()
    ctx.echo(stream=buffer)
    return buffer.getvalue()


def test_the_run_ECHOES_what_it_derived() -> None:
    out = _echoed(_ctx(pr_number="42"))
    assert "plan-draft-1788240530" in out, "the worktree name is not in the echo"
    assert "development/x/y" in out, "the TARGET is not in the echo"
    assert "/repo" in out
    assert "#42" in out


def test_a_context_carrying_a_WRITER_still_ECHOES_because_it_BUILT_itself() -> None:
    """The gate that was here silenced the case `Dual-mode children` introduces.

    ⚠ THIS ASSERTS THE OPPOSITE OF WHAT IT ASSERTED UNTIL 2026-09-02, and the
    reversal is the requirement rather than a relaxation. `echo` gated on
    `writer is None` as a proxy for *this process constructed the context*, and
    `RunContext.echo`'s own ⚠ named the trigger where the proxy stops holding: a
    standalone child is a SEPARATE PROCESS, so it always constructs its own
    context and can never be handed one — yet passed `--writer` it derived a
    worktree name and a target and said nothing. Six such entrypoints land in
    this phase.

    A `RunContext` is reachable only by constructing one, so *constructed here*
    is true at every call site and the gate could only ever be wrong. What a
    reader needs instead is the LABEL, which `render` carries and which the
    assertion below pins: the run row names the writer.
    """
    member = RunContext(run_id="r1", writer="plan_refine", minted=False,
                        repo_root=Path("/repo"), journal_root=None,
                        workflow_key="plan-refine", worktree_name="plan-refine-1",
                        pr_number=None, target=None)
    out = _echoed(member)
    assert "plan-refine-1" in out, (
        "a standalone child carrying --writer said nothing about what it "
        "derived — the invisibility this object exists to close, arriving on "
        "the runs that spend the model time")
    assert "(writer plan_refine)" in out, (
        "the echo fired but does not say this invocation is a MEMBER of a run "
        "rather than the run — which is the fact the dropped gate used to carry")


def test_the_echo_is_NOT_GATED_ON_MINTED_because_a_RETRY_needs_it_most() -> None:
    """A supplied `--run-id` means `minted=False` — and it is still the run.

    This is the correction the phase makes to its own brief, which named `minted`
    as the discriminator. An operator retrying into an existing bag supplies the
    name, so `minted` is False for the caller with the strongest claim on seeing
    what the retry derived.
    """
    retried = RunContext(run_id="20260901-abc", writer=None, minted=False,
                         repo_root=Path("/repo"), journal_root=Path("/j"),
                         workflow_key="plan", worktree_name="plan-1",
                         pr_number="42", target="development/x")
    assert "plan-1" in _echoed(retried)


def test_the_echo_defaults_to_STDERR() -> None:
    """stdout is a rendered report for several entrypoints; the echo is not that."""
    ctx = _ctx()
    err, out = io.StringIO(), io.StringIO()
    real_err, real_out = sys.stderr, sys.stdout
    sys.stderr, sys.stdout = err, out
    try:
        ctx.echo()
    finally:
        sys.stderr, sys.stdout = real_err, real_out
    assert "plan-draft-1788240530" in err.getvalue()
    assert out.getvalue() == ""


# --- the rehearsal -----------------------------------------------------------

def test_a_REHEARSAL_mints_nothing_and_resolves_no_journal_root() -> None:
    """`--dry-run` says "nothing invoked, nothing posted" and must stay true.

    `resolve_identity` is called AFTER the dry-run early return for exactly this
    reason. A context built for a rehearsal must be buildable without minting a
    name and without creating a 0700 directory, and both facts are VALUES on the
    object rather than quiet absences.
    """
    ctx = _ctx()
    assert ctx.run_id == DRY_RUN_RUN_ID
    assert ctx.minted is False
    assert ctx.journal_root is None
    assert "rehearsal" in ctx.render()


def test_the_REHEARSAL_and_the_LIVE_run_render_THE_SAME_OBJECT(tmp_path: Path) -> None:
    """One assembly, one renderer — which is requirement 4 stated as a test.

    Constructed both ways with the same inputs, the two renderings differ only in
    the two fields a rehearsal genuinely does not have. Every derived value the
    operator is previewing — the worktree, the target, the repo root — is
    identical, because there is one `render` and one set of fields behind it.
    """
    rehearsal = _ctx(pr_number="42")
    live = _live(tmp_path, pr_number="42")

    def derived_lines(text: str) -> list[str]:
        return [ln for ln in text.splitlines()
                if not ln.strip().startswith(("run ", "journal "))]

    assert derived_lines(rehearsal.render()) == derived_lines(live.render())
    # And the FIELDS agree, not merely their rendering — a renderer that dropped
    # a row would make two different objects print identically.
    differing = {f.name for f in dataclasses.fields(RunContext)
                 if getattr(rehearsal, f.name) != getattr(live, f.name)}
    assert differing == {"run_id", "minted", "journal_root"}, (
        f"the rehearsal and the live run differ on {differing}; only the run id, "
        f"`minted` and the journal root may differ — a rehearsal mints no name "
        f"and resolves no root, and every DERIVED value must be identical or the "
        f"preview is showing something other than what runs")


# --- the per-pass tree a review cuts BENEATH the run's own -------------------
#
# HERE RATHER THAN BESIDE `run_review`, because the naming scheme is ONE rule
# with two halves — a run-scoped stem from the context, plus a per-pass suffix —
# and testing half of it in another file is how a rule ends up with two owners
# that agree until one is edited. That is this component's own recurring defect.

def _review_tree_name(worktree_name: str, pr_number: str, this_pass: int) -> str:
    """The expression `review_pr_workflow` uses, read back from its source.

    DERIVED FROM THE MODULE, NOT RETYPED. A literal here would be a second
    statement of the same rule, which is exactly what this phase exists to stop —
    so the f-string is lifted out of the file and evaluated, and a change to it
    that breaks a property below fails rather than passing against a copy.
    """
    module = (FLEET / "modules" / "assistant" / "review_pr"
              / "review_pr_workflow.py")
    src = module.read_text(encoding="utf-8")
    marker = "worktree, f\""
    call = src.find("pr_tree = _shared.worktree_add")
    start = src.find(marker, call) if call != -1 else -1
    assert call != -1 and start != -1, (
        f"the per-pass tree name could not be read out of {module.name}: this lifts "
        f"the f-string argument of `pr_tree = _shared.worktree_add`. If that call "
        f"was reformatted or renamed, update this reader — do NOT retype the "
        f"template here, because a literal copy is a second statement of the rule "
        f"and that is exactly what this phase exists to stop.")
    start += len(marker)
    template = src[start:src.index('"', start)]
    return eval(f'f"{template}"', {},  # noqa: S307 — the template is our own source
                {"worktree_name": worktree_name, "task": type("T", (), {"pr_number": pr_number}),
                 "this_pass": this_pass})


def test_two_reviews_of_DIFFERENT_PRs_in_the_SAME_SECOND_do_not_collide() -> None:
    """The regression the consolidation nearly shipped, asserted as itself.

    The expression this replaced was `f"review-pr-{pr}-{int(time.time())}"`, and
    the PR number in it was load-bearing: the context's stem is
    `<workflow-key>-<ts>`, so two `review-pr` dispatches aimed at different PRs
    that start in the same wall-clock second share a stem. On their first pass
    they would have shared the whole directory, and `git worktree add` would
    have failed one of them — loud, but avoidable and caused by this change.
    """
    stem = _ctx(workflow_key="review-pr").worktree_name
    assert _review_tree_name(stem, "42", 1) != _review_tree_name(stem, "43", 1)


def test_two_PASSES_of_ONE_review_do_not_collide() -> None:
    """A loop-back cuts one tree per pass, which is why the tree is not a field.

    A parent that HOLDs re-enters `run_review` on the same PR inside one run, so
    the run-scoped stem is identical on both passes and only the pass number
    separates them.
    """
    stem = _ctx(workflow_key="plan").worktree_name
    assert _review_tree_name(stem, "42", 1) != _review_tree_name(stem, "42", 2)


def test_the_review_tree_is_ROOTED_IN_the_runs_own_name() -> None:
    """The stem is the run's, so a tree on disk is traceable to the bag record."""
    stem = _ctx(workflow_key="review-pr").worktree_name
    assert _review_tree_name(stem, "42", 1).startswith(f"{stem}-")


# --- requirement 4, held structurally over the entrypoints -------------------

def _entrypoints() -> list[Path]:
    found = sorted(p for p in ENTRYPOINTS.glob("run_*.py"))
    assert len(found) >= 10, (
        f"only {len(found)} entrypoints discovered under {ENTRYPOINTS} — the "
        f"glob is wrong and every assertion below would pass vacuously")
    return found


def _calls(tree: ast.AST) -> set[str]:
    """Every call, as `<attr>` or `<name>`, so `.build`/`.echo` are visible."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            out.add(fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", ""))
    return out


def _declares_a_dry_run(tree: ast.AST) -> bool:
    return any(isinstance(n, ast.Constant) and n.value == "--dry-run"
               for n in ast.walk(tree))


def _call_lines(tree: ast.AST, name: str) -> list[int]:
    return sorted(n.lineno for n in ast.walk(tree)
                  if isinstance(n, ast.Call)
                  and (getattr(n.func, "attr", None) == name
                       or getattr(n.func, "id", None) == name))


def _conditional_calls(tree: ast.AST, name: str) -> list[int]:
    """Lines where `name` is called from inside an `if` — i.e. not unconditionally.

    The `--dry-run` early return is not one of these: it RETURNS, so a call after
    it is still unconditional on the live path. What this catches is
    `if a.verbose: ctx.echo()`, which is the requirement's own named failure —
    the echo is not chatter and is not the operator's to switch off.
    """
    conditional: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        for branch in (node.body, node.orelse):
            for stmt in branch:
                conditional.extend(_call_lines(stmt, name))
    return conditional


def test_every_entrypoint_BUILDS_a_context_and_SAYS_IT() -> None:
    """Discovered rather than listed, so the next entrypoint is covered on day one."""
    missing = []
    for path in _entrypoints():
        calls = _calls(ast.parse(path.read_text(encoding="utf-8")))
        for required in ("build", "echo"):
            if required not in calls:
                missing.append(f"{path.name}: never calls `.{required}()`")
    assert not missing, (
        "these entrypoints do not construct or do not announce a run context:\n"
        + "\n".join(f"  {m}" for m in missing)
        + "\n\nWrite `ctx = RunContext.build(identity=resolve_identity(argv), …)` "
          "followed by `ctx.echo()`, before `open_run_bag` and before anything "
          "is created."
    )


def test_every_entrypoint_SAYS_IT_BEFORE_THE_BAG_OPENS_and_UNCONDITIONALLY() -> None:
    """PLACEMENT, which the presence sweep above cannot see — and it was needed.

    ⚠ MEASURED 2026-09-01 BY MUTATION. Moving `ctx.echo()` BELOW
    `journal.open_run_bag(...)` in `run_plan.py` left the whole unit tier green
    (3051 passed): the presence sweep collects call NAMES anywhere in the file,
    so requirement 3's ordering was held on exactly ONE entrypoint of eleven —
    `run_plan_draft`, by the live demonstration in
    `test_a_WRONG_TARGET_is_NAMED_before_the_run_costs_anything.py`. That is the
    same defect this PR found in `test_every_parent_opens_a_run_bag` (a guard
    that checks presence cannot see placement), reproduced in the guard written
    beside it.

    TWO PROPERTIES, BOTH FROM REQUIREMENT 3. The echo precedes the bag — the
    run's first side effect — and it is UNCONDITIONAL, because the requirement
    rules that `verbose` does not gate it: the context line is not a workflow's
    chatter, it is the run saying what it is about to spend money on.
    """
    offenders = []
    for path in _entrypoints():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        echoes, bags = _call_lines(tree, "echo"), _call_lines(tree, "open_run_bag")
        if not echoes or not bags:
            continue                       # the presence sweep above owns that
        if min(echoes) > min(bags):
            offenders.append(f"{path.name}: `.echo()` at {min(echoes)} comes AFTER "
                             f"`open_run_bag` at {min(bags)}")
        for line in _conditional_calls(tree, "echo"):
            offenders.append(f"{path.name}:{line}: `.echo()` is inside an `if`")
    assert not offenders, (
        "these entrypoints announce their context too late, or only sometimes:\n"
        + "\n".join(f"  {o}" for o in offenders)
        + "\n\nThe echo exists for the operator about to spend an hour of model "
          "time on the wrong component, so it goes BEFORE the bag opens and it "
          "is not switchable. `RunContext.echo` gates on nothing at all; a "
          "call site may not reintroduce a gate it deliberately dropped."
    )


def test_every_dry_run_PREVIEWS_THE_SAME_OBJECT() -> None:
    """Requirement 4, where it can actually be lost — in the rehearsal branch.

    An entrypoint that declares `--dry-run` and does not build a context for it
    is previewing values it assembled itself, which is the exact divergence this
    requirement exists to close.
    """
    missing = []
    for path in _entrypoints():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not _declares_a_dry_run(tree):
            continue
        calls = _calls(tree)
        if "for_dry_run" not in calls or "render" not in calls:
            missing.append(f"{path.name}: declares --dry-run but never renders a context")
        elif not _conditional_calls(tree, "for_dry_run"):
            # PLACEMENT, not presence: a `for_dry_run(...)` sitting outside the
            # rehearsal branch means the branch is still previewing something
            # else, with the context built somewhere it is never printed.
            missing.append(f"{path.name}: builds a rehearsal context outside the "
                           f"`--dry-run` branch, so the branch is not what it previews")
    assert not missing, (
        "these rehearsals preview something other than the object the live run "
        "prints:\n" + "\n".join(f"  {m}" for m in missing)
        + "\n\nPrint `RunContext.for_dry_run(...).render()` in the --dry-run "
          "branch. A second assembly of the same values is the bug."
    )


def test_THE_ENTRYPOINT_SWEEPS_DISCRIMINATE() -> None:
    """CONTROLS on both sweeps above, driven on literals.

    Both assertions are phrased as absences over a discovered population, so
    each needs a positive case proving the predicate reads what it claims —
    including the half-migration shape where the import is present and the call
    is not.
    """
    built_and_echoed = ('from dispatch_context import RunContext\n'
                        'def main(argv):\n'
                        '    ctx = RunContext.build(identity=i, repo_root=r, workflow_key="k")\n'
                        '    ctx.echo()\n')
    assert {"build", "echo"} <= _calls(ast.parse(built_and_echoed))

    # The half-migration: imported, never called. `_names_used`-style checks pass
    # this, which is why the sweep asks for a CALL.
    imported_only = ('from dispatch_context import RunContext\n'
                     'def main(argv):\n'
                     '    journal.open_run_bag(run_id="x")\n')
    assert "build" not in _calls(ast.parse(imported_only))
    assert "echo" not in _calls(ast.parse(imported_only))

    assert _declares_a_dry_run(ast.parse('p.add_argument("--dry-run")\n'))
    assert not _declares_a_dry_run(ast.parse('p.add_argument("--verbose")\n'))

    previewing = ('def main(a):\n'
                  '    if a.dry_run:\n'
                  '        print(RunContext.for_dry_run(repo_root=r, workflow_key="k").render())\n')
    assert {"for_dry_run", "render"} <= _calls(ast.parse(previewing))

    hand_rolled = ('def main(a):\n'
                   '    if a.dry_run:\n'
                   '        print(f"  Component : {component}")\n')
    assert "for_dry_run" not in _calls(ast.parse(hand_rolled))
    assert _conditional_calls(ast.parse(previewing), "for_dry_run") == [3]

    # CONTROLS ON THE ORDERING AND GATING PREDICATES, driven on literals so each
    # verdict is attributable to one shape.
    late = ('def main(a):\n'
            '    journal.open_run_bag(run_id=ctx.run_id)\n'
            '    ctx.echo()\n')
    assert min(_call_lines(ast.parse(late), "echo")) > \
        min(_call_lines(ast.parse(late), "open_run_bag"))

    early = ('def main(a):\n'
             '    ctx.echo()\n'
             '    journal.open_run_bag(run_id=ctx.run_id)\n')
    assert min(_call_lines(ast.parse(early), "echo")) < \
        min(_call_lines(ast.parse(early), "open_run_bag"))

    gated = ('def main(a):\n'
             '    if a.verbose:\n'
             '        ctx.echo()\n'
             '    journal.open_run_bag(run_id=ctx.run_id)\n')
    assert _conditional_calls(ast.parse(gated), "echo") == [3]
    # A `--dry-run` EARLY RETURN above the echo is not a gate on it.
    after_early_return = ('def main(a):\n'
                          '    if a.dry_run:\n'
                          '        return 0\n'
                          '    ctx.echo()\n')
    assert _conditional_calls(ast.parse(after_early_return), "echo") == []
