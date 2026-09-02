"""Every kickoff entrypoint supports `--dry-run`, because the onboarding says it does.

WHY THIS IS A SWEEP AND NOT THREE FIXES. The three runners that lacked the flag
were `run_build.py`, `run_build_minor.py` and `run_plan_revision.py` — and the
gap is invisible from inside any one of them. All four BUILD CHILDREN had the
flag while the build PARENT did not, so a reader checking "does this family
support dry runs?" got yes from every file they were likely to open. The
operator-facing documentation asserts the flag universally: *"`--dry-run` costs
nothing … use it first, every time."* An entrypoint that rejects it makes that
sentence false at exactly the moment a new engineer follows it, and the failure
is `error: unrecognized arguments`, which reads like the operator's mistake.

This is the same class as the bag sweep next door — a control that each file is
asked to remember, where optional is how it fails. The predicate is imported
from `journal_entrypoint_facts` rather than re-derived, for the reason that file
states: two sweeps disagreeing about what an entrypoint IS leave a file each
thought the other covered.

WHAT THIS DOES NOT COVER. It checks that the flag is DECLARED and BRANCHED ON,
not that the rehearsal is accurate — a dry run that printed a worktree name the
live run would not use is a defect this sweep cannot see. `RunContext.for_dry_run`
exists so the rehearsal renders through the same method the live run does, and
that is what keeps the preview honest; this test only guarantees the entrypoint
has one to render.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from journal_entrypoint_facts import ENTRYPOINTS_DIR, REPO_ROOT, entrypoints


def _declares_dry_run(tree: ast.AST) -> bool:
    """An `add_argument("--dry-run", ...)` anywhere in the file."""
    return any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "add_argument"
        and n.args
        and isinstance(n.args[0], ast.Constant)
        and n.args[0].value == "--dry-run"
        for n in ast.walk(tree)
    )


def _branches_on_dry_run(tree: ast.AST) -> bool:
    """The parsed value is actually READ.

    Declaring the flag and ignoring it is worse than rejecting it: the run
    proceeds to spend, and the operator believes they rehearsed.
    """
    return any(
        isinstance(n, ast.Name) and n.id == "dry_run"
        or isinstance(n, ast.Attribute) and n.attr == "dry_run"
        for n in ast.walk(tree)
    )


def _without_rehearsal(directory: Path) -> list[str]:
    bad = []
    for path in entrypoints(directory):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not _declares_dry_run(tree):
            bad.append(f"{path.name} — declares no --dry-run")
        elif not _branches_on_dry_run(tree):
            bad.append(f"{path.name} — declares --dry-run and never reads it")
    return bad


def test_every_entrypoint_supports_dry_run() -> None:
    discovered = entrypoints(ENTRYPOINTS_DIR)
    assert discovered, "discovery predicate matched nothing — the sweep is vacuous"

    missing = _without_rehearsal(ENTRYPOINTS_DIR)
    assert not missing, (
        "an entrypoint cannot be rehearsed, and the operator guide says every one "
        "can:\n  " + "\n  ".join(missing) + "\n\n"
        f"SCOPE OF THIS SWEEP: {ENTRYPOINTS_DIR.relative_to(REPO_ROOT)}/run_*.py. "
        "A dry run must print BEFORE `resolve_identity` and before any bag opens, "
        "so the rehearsal's claim that nothing was minted stays true. Copy the "
        "block from `run_build_draft.py`, which is the shape the family uses."
    )


def test_the_sweep_is_NOT_VACUOUS(tmp_path: Path) -> None:
    """Positive controls — both failure shapes must actually be caught.

    Predicted: two findings, one per file. A sweep that cannot fail is a sweep
    that reports clean forever, which is indistinguishable from working.
    """
    (tmp_path / "run_silent.py").write_text(
        "import argparse\n"
        "def parse_args():\n"
        "    p = argparse.ArgumentParser()\n"
        "    p.add_argument('--verbose', action='store_true')\n"
        "    return p.parse_args()\n",
        encoding="utf-8",
    )
    (tmp_path / "run_declared_but_ignored.py").write_text(
        "import argparse\n"
        "def parse_args():\n"
        "    p = argparse.ArgumentParser()\n"
        "    p.add_argument('--dry-run', action='store_true')\n"
        "    return p.parse_args()\n",
        encoding="utf-8",
    )
    found = _without_rehearsal(tmp_path)
    assert len(found) == 2, f"expected both shapes caught, got {found}"
    assert any("declares no --dry-run" in f for f in found)
    assert any("never reads it" in f for f in found)


# --- the predicates, exercised on literals rather than only on the tree ----------
#
# WITHOUT THESE THE SWEEP ABOVE IS UNFALSIFIABLE. `_declares_dry_run` returning
# True unconditionally would pass every assertion in this file AND its vacuity
# floor, because the population it walks currently satisfies it — a guard that
# reports clean forever is indistinguishable from one that works. So each
# predicate is fed a snippet that must satisfy it and one that must not.

_DECLARES = [
    ('p.add_argument("--dry-run", action="store_true")', True),
    ("p.add_argument('--dry-run', action='store_true')", True),
    ('p.add_argument("--verbose", "-v", action="store_true")', False),
    # NAMED IN A STRING BUT NEVER DECLARED — the exact shape `run_plan_project.py`
    # had: a comment reading "this entrypoint has no `--dry-run`". A substring
    # search over the source calls that a declaration; the AST does not, which is
    # why this walks the tree rather than grepping. It is also how the fourth
    # runner was found after a grep-shaped read of the same tree reported three.
    ('x = "see --dry-run"  # p.add_argument("--dry-run")', False),
    ('parser.add_argument("--dry-run", help="no spend")', True),
]

_BRANCHES = [
    ("if dry_run:\n    pass", True),
    ("if a.dry_run:\n    pass", True),
    ("task, dry_run = parse_args(argv)", True),
    ("if verbose:\n    pass", False),
    ('x = "dry_run"', False),
]


@pytest.mark.parametrize("snippet,expected", _DECLARES)
def test_the_DECLARATION_predicate_discriminates(snippet: str, expected: bool) -> None:
    assert _declares_dry_run(ast.parse(snippet)) is expected


@pytest.mark.parametrize("snippet,expected", _BRANCHES)
def test_the_BRANCH_predicate_discriminates(snippet: str, expected: bool) -> None:
    assert _branches_on_dry_run(ast.parse(snippet)) is expected
