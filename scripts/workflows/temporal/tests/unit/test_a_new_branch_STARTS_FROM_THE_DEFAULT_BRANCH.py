"""A run with no `--pr` is cut from the DEFAULT BRANCH, never from `HEAD`.

THE DEFECT, MEASURED 2026-08-20. Every runner computed its worktree base inline:

    ref = f"origin/{pr_branch(...)}" if pr_number else "HEAD"

`HEAD` is whatever branch the operator's clone happens to be sitting on. When
that was an open PR's branch, the new run branched FROM that PR, and its own PR
silently carried the other one's commits — a PR whose diff is not the change it
claims, reviewed against work belonging to someone else.

THREE OF EIGHT OPEN PRs HAD IT. #132 and #127 were both cut while the checkout
sat on #126's branch. #127 carried two of #126's commits in a version #126's own
review had already superseded, and #132's review caught the same shape from the
other side and classified it `stale-stack-lands-known-defects`. Nothing warned,
and nothing could: the runners did exactly what they were told.

THE RULE IS THE OPERATOR'S, STATED PLAINLY: a run either CONTINUES the same PR
(`--pr`) or STARTS FROM THE DEFAULT BRANCH. There is no third base, and the
operator's checkout position is not an input to the question.

WHY THE CHECK IS ON THE CLASS AND NOT ON ELEVEN FILES. The inline expression reached
ELEVEN call sites before anyone noticed, and a fix applied by hand to a list of
eleven is a fix applied to ten — which is what happened here on the first pass — this repo has the receipt, in the frozen-fleet guard
that was closed one spelling at a time three times. So this walks every module
under the fleet and fails on the SHAPE, wherever it appears, including in a file
that does not exist yet.

WHAT THIS DOES NOT LOOK AT:
  * It does not check that `base_ref` returns the right thing — that is
    `test_base_ref_*` below, driven against a fake `gh`.
  * It does not reach a base computed at runtime from a variable this walk
    cannot see. A runner that builds its ref by string concatenation through
    three locals is invisible here, as it is to any source-level check.
  * It says nothing about `worktree_add`'s fetch behaviour, which is the
    sibling guarantee and is held elsewhere.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

FLEET = Path(__file__).resolve().parents[2]
SEARCH = [FLEET / "scripts", FLEET / "modules"]


def _fleet_sources() -> list[Path]:
    found = [p for root in SEARCH for p in root.rglob("*.py")
             if "tests" not in p.parts]
    assert len(found) > 20, (
        f"only {len(found)} fleet modules found under {SEARCH} — the walk is "
        f"wrong, and every assertion below would pass vacuously")
    return found


def _worktree_bases(path: Path) -> list[tuple[int, str]]:
    """Every `worktree_add` call whose REF ARGUMENT can be the literal "HEAD".

    KEYED ON THE SEAM, NOT ON A NAMING CONVENTION, and the first version of this
    module got that wrong. It matched assignments to a name called `ref`, which
    is how ten of the eleven call sites happened to be written — and
    `research_refresh_parent_workflow` passes its base INLINE:

        worktree = act.worktree_add(repo_root, worktree_name, "HEAD")

    That site is a member of the class and the old key could not express it, so
    the guard shipped a population narrower than the class its own docstring
    claimed. `review-pr` found it as `head-base-guard-cannot-see-an-inline-
    argument`. The key is now `worktree_add`'s third argument however it is
    supplied: a literal, or a local whose assignment can produce one.

    `git rev-parse HEAD` IS NOT AN OFFENDER and this is why the key matters. Two
    other literal "HEAD"s live in the fleet — `journal_activities` and
    `plan_project_workflow` both ask git for the CURRENT COMMIT SHA, which is
    correct and unrelated to where a worktree is cut. A guard keyed on "any HEAD
    literal" would fail both and teach the next reader to weaken it.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:  # a module that will not parse is a different failure
        return []
    return _bases_in_tree(tree)


def _bases_in_tree(tree: ast.Module) -> list[tuple[int, str]]:
    """THE PREDICATE, OVER A PARSED TREE, so a control can drive it on a literal.

    TAKES A TREE AND NOT A STRING, which is the convention the census guard's own
    helpers use (`_walks_the_tree`, `_parses_a_literal`) and it is load-bearing
    twice over. The census recognises a tree-walker by
    `ast.parse(path.read_text(...))` and a CONTROL by an `ast.parse` of anything
    that is not a file read. A first attempt split this on the SOURCE string,
    which moved the only `ast.parse` out of the reading path — and the module
    dropped out of the census population altogether rather than gaining a
    control. Parsing here and passing the tree keeps both signatures where they
    belong.
    """
    # locals whose assignment can yield "HEAD", so a two-step site is reachable
    head_locals: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for sub in ast.walk(node.value):
                if isinstance(sub, ast.Constant) and sub.value == "HEAD":
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            head_locals[tgt.id] = node.lineno

    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        if name != "worktree_add":
            continue
        # ref is the third positional, or the `ref=` keyword
        arg = node.args[2] if len(node.args) > 2 else next(
            (k.value for k in node.keywords if k.arg == "ref"), None)
        if arg is None:
            continue
        if isinstance(arg, ast.Constant) and arg.value == "HEAD":
            hits.append((node.lineno, 'worktree_add(..., "HEAD")'))
        elif isinstance(arg, ast.Name) and arg.id in head_locals:
            hits.append((node.lineno, f"worktree_add(..., {arg.id}) "
                                      f"assigned at line {head_locals[arg.id]}"))
    return hits


def test_no_runner_cuts_a_worktree_from_the_OPERATORS_CHECKOUT() -> None:
    offenders = [(p, ln, name) for p in _fleet_sources()
                 for ln, name in _worktree_bases(p)]
    assert not offenders, (
        "these assignments can hand `worktree_add` the literal \"HEAD\", which "
        "is the branch the operator's clone happens to be sitting on:\n"
        + "\n".join(f"  {p.relative_to(FLEET)}:{ln}  ({name})"
                    for p, ln, name in offenders)
        + "\n\nA run either CONTINUES a PR or STARTS FROM THE DEFAULT BRANCH. "
          "Use `base_ref(pr_number, repo_root)`. Measured 2026-08-20: three of "
          "eight open PRs carried another PR's commits because of this line."
    )


def test_THE_WALK_HAS_A_POPULATION() -> None:
    """THE VACUITY FLOOR, and it is not optional here.

    The assertion above is phrased as an absence, so a walk that found no files
    — a moved directory, a renamed package — passes it while checking nothing.
    This proves the walk reaches the runners that actually cut worktrees.
    """
    sources = {p.name for p in _fleet_sources()}
    for expected in ("run_plan_draft.py", "run_plan_verify.py",
                     "build_workflow.py", "research_workflow.py"):
        assert expected in sources, (
            f"{expected} is not in the walk's population, so this module is no "
            f"longer checking the runners it was written for")


def test_THE_DETECTOR_FIRES_on_every_shape_the_defect_TOOK() -> None:
    """A POSITIVE CONTROL ON THE DETECTOR, not on the fleet.

    THE INLINE CASE IS FIRST BECAUSE IT IS THE ONE THAT ESCAPED. The first
    version of this module keyed on assignments to a name called `ref`, and the
    eleventh call site passed its base straight into the call. A control that
    only exercised the ten shapes I had already fixed would have proved the
    detector worked on the population it could see, which is the failure it was
    blind to.
    """
    cases = {
        "inline.py": 'worktree = act.worktree_add(repo, name, "HEAD")\n',
        "inline_kwarg.py": 'act.worktree_add(repo, name, ref="HEAD")\n',
        "via_local.py": 'ref = "HEAD"\nact.worktree_add(repo, name, ref)\n',
        "ternary_local.py": 'ref = f"origin/{b}" if pr else "HEAD"\nact.worktree_add(r, n, ref)\n',
        "bare_call.py": 'worktree_add(repo, name, "HEAD")\n',
    }
    for name, src in cases.items():
        assert _bases_in_tree(ast.parse(src)), f"the detector missed {name}: {src!r}"

    for name, src in {
        "fixed.py": 'act.worktree_add(repo, name, act.base_ref(pr, repo))\n',
        # `git rev-parse HEAD` asks for the CURRENT COMMIT and is correct. Two
        # such calls live in the fleet; a detector that flagged them would be
        # weakened by the next reader, rightly.
        "rev_parse.py": 'sha = act.git_output(wt, ["git", "rev-parse", "HEAD"], "hint")\n',
    }.items():
        assert not _bases_in_tree(ast.parse(src)), (
            f"the detector fires on {name}, which is CORRECT code — it would fail "
            f"a fixed tree and teach the next reader to delete it")


@pytest.mark.parametrize("pr,expected", [(None, "origin/trunk"), ("7", "origin/feature-x")])
def test_base_ref_ANSWERS_FROM_THE_REMOTE_not_from_a_hardcoded_name(
    monkeypatch, pr, expected
) -> None:
    """`main` is not universal, and this fleet is meant to run against other repos.

    The `None` arm asserts a NON-`main` default specifically: a helper that
    hardcoded "main" would pass a test whose fixture answered "main", which is
    the shape that ships a repo-specific assumption as a general one.
    """
    from modules.assistant import assistant_activities as act

    def fake_gh(args, repo_root):
        if "defaultBranchRef" in args:
            return "trunk\n"
        if args[0] == "pr":
            return "feature-x\n"
        raise AssertionError(f"unexpected gh call: {args}")

    monkeypatch.setattr(act, "gh", fake_gh)
    assert act.base_ref(pr, Path("/nowhere")) == expected
