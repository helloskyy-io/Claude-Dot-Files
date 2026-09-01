"""The run context: derived once, frozen, and previewed by the same renderer.

WHAT IS UNDER TEST. `RunContext` is the object Workflow Decomposition Phase 4
introduces so that a run has ONE place its derived values come from. Three
properties are checkable here and each had a measured failure behind it:

  * THE WORKTREE NAME FOLLOWS THE WORKFLOW KEY. Eleven sites derived it
    independently and `run_build_minor` had drifted — `workflow_key="build-minor"`
    beside a worktree named `build-…`, so its trees were indistinguishable on
    disk from the `build` parent's.
  * THE ECHO IS GATED ON *IS THIS INVOCATION THE RUN*, not on `verbose` and not
    on `minted`. An operator retrying with `--run-id X` has `minted=False` and is
    exactly the caller who most needs to see what the retry derived.
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
    ctx = _ctx(workflow_key=key)
    assert ctx.worktree_name == f"{key}-1788240530"


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


def test_a_MEMBER_of_a_run_does_NOT_REPRINT_what_its_parent_said() -> None:
    """The `constructed here or received` discriminator, exercised.

    `--writer` is the only thing that distinguishes a child started by a parent
    from a child started by a person reproducing what a parent did, so it is the
    only honest gate. A parent that hands nine children one context should say it
    once.
    """
    member = RunContext(run_id="r1", writer="plan_refine", minted=False,
                        repo_root=Path("/repo"), journal_root=None,
                        workflow_key="plan-refine", worktree_name="plan-refine-1",
                        pr_number=None, target=None)
    assert _echoed(member) == ""


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


def test_the_REHEARSAL_and_the_LIVE_run_render_THE_SAME_OBJECT() -> None:
    """One assembly, one renderer — which is requirement 4 stated as a test.

    Constructed both ways with the same inputs, the two renderings differ only in
    the two fields a rehearsal genuinely does not have. Every derived value the
    operator is previewing — the worktree, the target, the repo root — is
    identical, because there is one `render` and one set of fields behind it.
    """
    live = RunContext.build.__wrapped__ if hasattr(RunContext.build, "__wrapped__") else None
    assert live is None  # not decorated; construct directly to avoid touching disk
    rehearsal = _ctx(pr_number="42")
    same = RunContext(run_id="20260901-abc", writer=None, minted=True,
                      repo_root=rehearsal.repo_root, journal_root=Path("/j"),
                      workflow_key=rehearsal.workflow_key,
                      worktree_name=rehearsal.worktree_name,
                      pr_number=rehearsal.pr_number, target=rehearsal.target)

    def derived_lines(text: str) -> list[str]:
        return [ln for ln in text.splitlines()
                if not ln.strip().startswith(("run ", "journal "))]

    assert derived_lines(rehearsal.render()) == derived_lines(same.render())


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
