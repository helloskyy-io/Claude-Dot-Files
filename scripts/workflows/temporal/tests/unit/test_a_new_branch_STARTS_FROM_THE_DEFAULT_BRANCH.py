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

WHY THE CHECK IS ON THE CLASS AND NOT ON TEN FILES. The inline expression reached
TEN call sites before anyone noticed, and a fix applied by hand to a list of ten
is a fix applied to nine — this repo has the receipt, in the frozen-fleet guard
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


def _head_bases(path: Path) -> list[tuple[int, str]]:
    """Assignments to a `ref`-ish name whose value can be the literal "HEAD".

    Keyed on the ASSIGNED NAME plus the literal, not on the exact expression:
    the inline form appeared as a one-liner, as a parenthesised two-liner, and
    with three different `pr_number` spellings. Matching the text would have
    found some of them, which is the failure mode this module exists to end.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:  # a module that will not parse is a different failure
        return []
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if not any(n in ("ref", "base", "base_ref") for n in names):
            continue
        for sub in ast.walk(node.value):
            if isinstance(sub, ast.Constant) and sub.value == "HEAD":
                hits.append((node.lineno, names[0]))
    return hits


def test_no_runner_cuts_a_worktree_from_the_OPERATORS_CHECKOUT() -> None:
    offenders = [(p, ln, name) for p in _fleet_sources()
                 for ln, name in _head_bases(p)]
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
    for expected in ("run_plan_feature.py", "run_plan_verify.py",
                     "build_workflow.py", "research_workflow.py"):
        assert expected in sources, (
            f"{expected} is not in the walk's population, so this module is no "
            f"longer checking the runners it was written for")


def test_THE_DETECTOR_FIRES_on_the_shape_it_was_written_for(tmp_path: Path) -> None:
    """A POSITIVE CONTROL ON THE DETECTOR, not on the fleet.

    Every shape the defect actually took, including the two that a text match
    would have missed. Without this, a detector that silently stopped matching
    would report the tree clean.
    """
    cases = {
        "one_liner.py": 'ref = f"origin/{b}" if pr else "HEAD"\n',
        "parenthesised.py": 'ref = (f"origin/{b}"\n       if pr else "HEAD")\n',
        "plain.py": 'ref = "HEAD"\n',
        "named_base.py": 'base = "HEAD" if not pr else "x"\n',
    }
    for name, src in cases.items():
        f = tmp_path / name
        f.write_text(src)
        assert _head_bases(f), f"the detector missed {name}: {src!r}"

    ok = tmp_path / "fixed.py"
    ok.write_text("ref = act.base_ref(pr_number, repo_root)\n")
    assert not _head_bases(ok), (
        "the detector fires on the CORRECTED form, so it would fail a fixed "
        "tree and teach the next reader to delete it")


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
