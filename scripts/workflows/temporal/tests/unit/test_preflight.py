"""Preconditions fail BEFORE anything is created.

Two failures shared one shape: the run got far enough to create a worktree and
then died, leaving it orphaned on disk with nothing pointing at it.

  A missing dependency crashed mid-run, and the traceback named an import
  rather than the invocation (#49).

  Six of seven entrypoints rooted on `Path.cwd()`, so invoking from a
  subdirectory put `.claude/worktrees/` and `.claude/logs/` inside it, where
  cleanup never looks and a later sweep deletes the logs with the workspace
  (#48).

Both are cheapest to catch before the first side effect, which is what this
module exists to guarantee.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from preflight import (RepoPathParser, preflight, require_dependencies,
                       resolve_operator_paths, resolve_repo_root)

REPO_ROOT = Path(__file__).resolve().parents[5]


def test_a_subdirectory_resolves_to_the_repo_root() -> None:
    """THE #48 regression. `Path.cwd()` would return the subdirectory."""
    deep = REPO_ROOT / "scripts" / "workflows" / "temporal" / "scripts"
    assert deep.is_dir(), "fixture path moved"
    assert resolve_repo_root(str(deep)) == REPO_ROOT


def test_the_repo_root_resolves_to_itself() -> None:
    """Negative control: the common case must not be broken by the fix."""
    assert resolve_repo_root(str(REPO_ROOT)) == REPO_ROOT


def test_outside_a_repository_raises_with_a_usable_message(tmp_path: Path) -> None:
    """It must say what to do, not just that something went wrong.

    An operator reading this has passed the wrong `--repo` or is standing in
    the wrong directory; both are one action away from fixed.
    """
    with pytest.raises(RuntimeError) as exc:
        resolve_repo_root(str(tmp_path))
    assert "not inside a git repository" in str(exc.value)
    assert "--repo" in str(exc.value), "the message does not name the remedy"


def test_a_missing_dependency_raises_before_anything_runs() -> None:
    """THE #49 regression, checked on a package that cannot exist."""
    with pytest.raises(RuntimeError) as exc:
        require_dependencies(("a_package_that_does_not_exist_anywhere",))
    assert "missing required package" in str(exc.value)
    assert "Nothing was created" in str(exc.value)


def test_the_real_dependencies_are_present() -> None:
    """Positive control. A check that always raised would pass the test above."""
    require_dependencies()


def test_dependencies_are_checked_BEFORE_the_repository(tmp_path: Path) -> None:
    """Order matters: fail on the cheaper, more actionable problem first.

    Outside a repo AND missing a package, the operator should be told about the
    package — it needs no repository to fix, so reporting the other first makes
    them solve two things one at a time.
    """
    import preflight as pf
    original = pf._REQUIRED
    pf._REQUIRED = ("a_package_that_does_not_exist_anywhere",)
    try:
        with pytest.raises(RuntimeError) as exc:
            preflight(str(tmp_path))
        assert "missing required package" in str(exc.value)
    finally:
        pf._REQUIRED = original


def test_every_entrypoint_actually_calls_preflight() -> None:
    """The fix is worthless in the six files that forget it.

    Discovered rather than listed — a new entrypoint is covered the day it
    lands, which is the same reason the isolation net stopped being a hand list.
    """
    scripts = sorted((REPO_ROOT / "scripts" / "workflows" / "temporal" / "scripts").glob("run_*.py"))
    assert scripts, "no entrypoints discovered — the sweep is inert"
    missing = [s.name for s in scripts if "preflight(" not in s.read_text()]
    assert not missing, f"entrypoints that can still strand a worktree: {missing}"


def test_no_entrypoint_roots_on_the_invocation_directory() -> None:
    """`Path.cwd()` as a repo root is the #48 defect itself."""
    scripts = sorted((REPO_ROOT / "scripts" / "workflows" / "temporal" / "scripts").glob("run_*.py"))
    offenders = [s.name for s in scripts
                 if "repo_root = Path(" in s.read_text() and "Path.cwd()" in s.read_text()]
    assert not offenders, f"these root on the invocation dir rather than the repo: {offenders}"


def test_no_entrypoint_INLINES_the_operator_path_escape_check() -> None:
    """THE CLASS: a path-escape check on operator input has ONE implementation.

    KEYED ON THE CHECK, NOT ON THE TWO RUNNERS THAT HAPPENED TO CARRY IT. Two
    entrypoints held this block byte-identically — resolve against the repo,
    refuse what is not `is_relative_to` it, refuse what does not exist. Listing
    those two and calling it done leaves the third copy to be written by whoever
    adds the next runner, and it will be written from one of the two rather than
    from whichever has been hardened since.

    THE DRIFT IS ONE-DIRECTIONAL AND INVISIBLE, which is what makes this worth a
    sweep rather than a review note. Symlink resolution, a denylist, a `.git`
    check — every future tightening lands in the entrypoint the author had open.
    The other keeps accepting what the first now refuses, both files still read
    as careful, and no diff shows the divergence because neither changed.

    WHAT THIS DOES NOT LOOK AT, so it is not read as covering more than it does:

      * It does not check that the entrypoint validates the RIGHT paths. A
        runner that resolves `component` and forgets `--candidates` passes here;
        `resolve_operator_paths` is a mechanism, not a policy. `RepoPathParser`
        is what makes the SET a policy — it is derived from the declarations
        rather than retyped — but that is a property of the parser, not of this
        sweep.
      * It does not reach `is_relative_to` anywhere but the entrypoints. A
        workflow module doing its own escape check is a different question, and
        `boundary_crossings` is the mechanism for that altitude.
      * It cannot see a runner that takes an operator path and checks NOTHING.
        That is the more dangerous state and it is invisible to this sweep,
        because the absence of a check has no syntax. **That gap was real and it
        was live:** five of ten runners were in exactly that state, and ALL FIVE
        accepted `../../../../tmp/...` and read through it. It is now closed
        from the other side by
        `test_no_runner_joins_an_UNRESOLVED_operator_path.py`, which gives the
        absence syntax by keying on the JOIN the absence exists to permit rather
        than on the missing call. This sweep still owns the copied-check half —
        the two are complementary and neither subsumes the other.

    READ BY AST, NOT BY SUBSTRING, AND THAT IS NOT FASTIDIOUSNESS. This check
    was first written as `"is_relative_to" in text and "resolve_operator_paths"
    not in text`, and a mutation control put the inline block back into
    `run_plan_draft.py` and the sweep STAYED GREEN — because the comment above
    the call still said *"see `resolve_operator_paths` for why two copies of a
    boundary check drift"*. The prose explaining the rule satisfied the check for
    the rule. A guard reading a region that includes its own documentation
    reports on the documentation, and it does so silently.
    """
    scripts_dir = REPO_ROOT / "scripts" / "workflows" / "temporal" / "scripts"
    scripts = sorted(scripts_dir.glob("run_*.py"))
    assert scripts, "no entrypoints discovered — the sweep is inert"

    def inlines_the_check(path: Path) -> bool:
        tree = ast.parse(path.read_text())
        uses = any(isinstance(n, ast.Attribute) and n.attr == "is_relative_to"
                   for n in ast.walk(tree))
        calls = any(isinstance(n, ast.Call)
                    and (getattr(n.func, "id", None) == "resolve_operator_paths"
                         or getattr(n.func, "attr", None) == "resolve_operator_paths")
                    for n in ast.walk(tree))
        return uses and not calls

    offenders = [s.name for s in scripts if inlines_the_check(s)]
    assert not offenders, (
        f"these entrypoints inline their own operator-path escape check instead "
        f"of calling `preflight.resolve_operator_paths`: {offenders}. §10.1 rule "
        f"3 is mechanical — the consumer count decides — and a second copy of a "
        f"boundary check is the shape that drifts with nothing in a diff to show "
        f"for it.")


def test_the_shared_resolver_refuses_an_escape_and_a_missing_path(tmp_path: Path) -> None:
    """The promotion PINNED, so it is a behaviour rather than a refactor.

    Both messages are asserted because they are the diagnostics: an operator who
    typed `../../elsewhere` needs to be told it escaped, not that it is missing.
    """
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "c.md").write_text("x")

    with pytest.raises(RuntimeError) as escape:
        resolve_operator_paths(tmp_path, {"component": "../outside"})
    assert "resolves outside the repo" in str(escape.value)
    assert "component ../outside" in str(escape.value), "the message must echo the ARGUMENT"

    with pytest.raises(RuntimeError) as missing:
        resolve_operator_paths(tmp_path, {"candidates": "docs/nope.md"})
    assert "candidates not found" in str(missing.value)

    with pytest.raises(RuntimeError) as not_a_dir:
        resolve_operator_paths(tmp_path, {"component": "docs/c.md"},
                               directories=("component",))
    assert "component is not a directory" in str(not_a_dir.value)

    ok = resolve_operator_paths(tmp_path, {"component": "docs", "candidates": "docs/c.md"},
                                directories=("component",))
    assert ok == {"component": tmp_path / "docs", "candidates": tmp_path / "docs" / "c.md"}


def test_an_ESCAPE_is_reported_before_a_MISSING_path(tmp_path: Path) -> None:
    """The three passes run in order, and the order is operator-facing.

    An escaping path does not exist either, so a resolver that checked existence
    first would report `not found` for `../../elsewhere` — sending the operator
    to create a directory rather than to fix the argument. Both entrypoints
    ordered it this way and the promotion has to keep it.
    """
    with pytest.raises(RuntimeError) as exc:
        resolve_operator_paths(tmp_path, {"component": "../outside/nothing"})
    assert "resolves outside the repo" in str(exc.value)
    assert "not found" not in str(exc.value)


def test_an_OPTIONAL_path_is_exempt_from_EXISTENCE_and_not_from_CONTAINMENT(
        tmp_path: Path) -> None:
    """The exemption is one pass wide, and the wrong reading of it is the defect.

    `optional` exists for the research family, whose pool legitimately may not
    exist yet — nothing in it `mkdir`s, and its dry run reports `0 due papers`
    for an absent pool rather than failing. Requiring existence there would turn
    an escape fix into a behaviour change.

    BOTH HALVES ARE ASSERTED BECAUSE ONLY THE PAIR MEANS ANYTHING. An `optional`
    that also skipped the containment pass would read identically at every call
    site and would silently re-open the hole this whole change closes, on exactly
    the two runners that take an unconstrained positional.
    """
    absent = resolve_operator_paths(tmp_path, {"pool": "docs/not-yet"},
                                    directories=("pool",), optional=("pool",))
    assert absent == {"pool": tmp_path / "docs" / "not-yet"}, (
        "an optional path that does not exist must resolve, not raise")

    with pytest.raises(RuntimeError) as escape:
        resolve_operator_paths(tmp_path, {"pool": "../outside"},
                               directories=("pool",), optional=("pool",))
    assert "resolves outside the repo" in str(escape.value), (
        "`optional` exempted the path from CONTAINMENT, which is the one pass it "
        "must never reach")


def test_declaring_a_repo_path_is_what_CHECKS_it(tmp_path: Path) -> None:
    """THE PROPERTY. The registry is derived from the declarations, never retyped.

    Built as a parser rather than asserted about, because the claim is about what
    happens when somebody uses the class normally: two paths declared, neither
    named again anywhere, and both resolved. A runner cannot accept a repo path
    through this parser and skip the check — there is no step between the two to
    forget, which is what five hand-written call sites did not have.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "c.md").write_text("x")

    def parser() -> RepoPathParser:
        p = RepoPathParser(prog="fixture")
        p.add_argument("--repo", dest="repo_target")
        p.add_repo_path("component", kind="dir")
        p.add_repo_path("--candidates", default="docs/c.md")
        p.add_argument("--unrelated", default="../../not-a-path")
        return p

    a, repo_root, resolved = parser().parse_with_preflight(
        ["docs", "--repo", str(tmp_path)])
    assert repo_root == tmp_path.resolve()
    assert set(resolved) == {"component", "candidates"}, (
        f"the resolved set is {sorted(resolved)}; it must be exactly what was "
        f"DECLARED as a repo path — no more, and nothing hand-listed")
    assert resolved["component"] == tmp_path.resolve() / "docs"
    assert a.unrelated == "../../not-a-path", (
        "a plain `add_argument` must be left alone — `--task-file` and `--phase` "
        "point outside the repo on purpose. Their RELATIVE form is anchored to "
        "the repo root by `assistant_activities.anchor_task_source`, which is a "
        "different question from containment and happens elsewhere")

    with pytest.raises(RuntimeError) as exc:
        parser().parse_with_preflight(
            ["docs", "--candidates", "../../../elsewhere.md", "--repo", str(tmp_path)])
    assert "resolves outside the repo" in str(exc.value)


def test_a_parser_declaring_repo_paths_without_repo_FAILS_LOUDLY(tmp_path: Path) -> None:
    """Silence here would reintroduce #48 one layer up.

    Without `--repo`, `preflight(None)` roots on the invocation directory — so a
    parser that declared repo paths and forgot the flag would contain them
    against whatever directory the operator happened to be standing in, and every
    check would pass while meaning nothing.
    """
    p = RepoPathParser(prog="fixture")
    p.add_repo_path("--candidates", default="docs/c.md")

    with pytest.raises(RuntimeError) as exc:
        p.parse_with_preflight([])
    assert "no `--repo` argument" in str(exc.value)
    assert "repo_target" in str(exc.value), "the message must name the dest to fix"


def test_add_repo_path_REFUSES_a_kind_it_does_not_understand() -> None:
    """A third spelling would assert neither `is_dir()` nor anything else.

    `kind="directory"` is the obvious near-miss, and silently accepting it would
    leave the caller believing a check was installed that never runs — the same
    shape as the defect this whole change closes, one layer smaller.
    """
    p = RepoPathParser(prog="fixture")
    with pytest.raises(ValueError) as exc:
        p.add_repo_path("--pool", kind="directory")
    assert "kind must be 'file' or 'dir'" in str(exc.value)


def test_a_declared_path_with_NO_VALUE_and_NO_DEFAULT_fails_by_name(tmp_path: Path) -> None:
    """`must_exist=True` plus `default=None` used to drop the path silently.

    The declaration reads as *"must exist if given"*, and unsupplied it fell out of
    the resolved mapping — so the caller's `resolved["pool"]` raised a bare
    `KeyError: 'pool'` naming neither the argument nor the reason, three frames from
    anything the operator typed. Nothing declares this shape today; refusing it at
    the point the contradiction exists is what stops the first runner that writes it
    from debugging a KeyError.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    p = RepoPathParser(prog="fixture")
    p.add_argument("--repo", dest="repo_target")
    p.add_repo_path("--pool", kind="dir")          # no default, must_exist defaults True

    with pytest.raises(RuntimeError) as exc:
        p.parse_with_preflight(["--repo", str(tmp_path)])
    assert "pool" in str(exc.value), "the message must name the argument to fix"
    assert "must_exist" in str(exc.value), "and the contradiction that caused it"


def test_an_OPTIONAL_path_with_no_value_is_simply_ABSENT_not_an_error(tmp_path: Path) -> None:
    """THE OTHER ARM — the refusal above must not swallow the legitimate case.

    `must_exist=False` with no value is a path the operator did not supply, which is
    allowed: the research runners' pool is the live instance. Without this arm the
    check above would pass just as well if it refused every unsupplied path.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    p = RepoPathParser(prog="fixture")
    p.add_argument("--repo", dest="repo_target")
    p.add_repo_path("--pool", kind="dir", must_exist=False)

    a, repo_root, resolved = p.parse_with_preflight(["--repo", str(tmp_path)])
    assert "pool" not in resolved, "an unsupplied optional path has nothing to resolve"
    assert a.pool is None


def test_a_NON_CANONICAL_repo_root_does_not_refuse_legitimate_paths(tmp_path: Path) -> None:
    """Both sides of `is_relative_to` must be canonical or the comparison means nothing.

    The operator side is always `.resolve()`d — collapsing `..` is the whole subject.
    If `repo_root` is not, every LEGITIMATE in-tree path fails containment and the
    operator is told their correct argument *resolves outside the repo*: a false
    refusal naming a remedy that does not apply, which is worse than a bare error.

    DRIVEN THROUGH `resolve_operator_paths` AND NOT THROUGH `resolve_repo_root`,
    because that is where it discriminates. `git rev-parse --show-toplevel`
    canonicalises on its own — measured — so a symlink test routed through the
    entrypoint passes with or without the fix. This one fails without it.
    """
    real = tmp_path / "real"
    (real / "docs").mkdir(parents=True)
    link = tmp_path / "via-symlink"
    link.symlink_to(real)

    resolved = resolve_operator_paths(link, {"component": "docs"},
                                      directories=("component",))
    assert resolved["component"] == real.resolve() / "docs", (
        "a legitimate in-repo path was refused or mis-resolved because `repo_root` "
        "was not canonical while the operator path was")


def test_resolve_operator_paths_still_refuses_an_escape_from_a_NON_CANONICAL_root(
        tmp_path: Path) -> None:
    """NEGATIVE CONTROL for the normalisation above.

    Canonicalising `repo_root` must not be a way to widen containment: an escaping
    path is still an escape when the root is reached through a symlink. Without this
    arm, `repo_root = repo_root.resolve()` could have been replaced by anything that
    made the previous test pass.
    """
    real = tmp_path / "real"
    (real / "docs").mkdir(parents=True)
    link = tmp_path / "via-symlink"
    link.symlink_to(real)

    with pytest.raises(RuntimeError) as exc:
        resolve_operator_paths(link, {"component": "../../../elsewhere"})
    assert "resolves outside the repo" in str(exc.value)
