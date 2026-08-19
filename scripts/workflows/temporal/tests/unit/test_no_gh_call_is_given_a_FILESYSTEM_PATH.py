"""`gh --repo` takes `OWNER/REPO`. Every `--repo` in this fleet is a PATH.

THE COLLISION IS THE WHOLE DEFECT AND IT IS INVISIBLE AT THE CALL SITE. Every
workflow here takes `--repo` as a filesystem path — the flag's own help says
"target repo — a FILESYSTEM PATH, never a gh slug" — and carries it as
`task.repo_target`. `gh` has a flag of the same name that means something else.
Passing one to the other is a single plausible-looking line:

    cmd = ["pr", "checks", pr, "--json", "name,state"]
    if repo:
        cmd += ["--repo", repo]        # `repo` is /home/puma/Repos/...

MEASURED 2026-08-19 ON PR #124. Both `ci_verdict` and `wait_for_ci` did this, so
every `gh pr checks` in a `--repo` build dispatch failed for the full 600-second
deadline with:

    expected the "[HOST/]OWNER/REPO" format, got "/home/puma/Repos/claude-dot-files"

The gate then did exactly the right thing — refused to read UNREADABLE as
passing — and held a PR whose four checks were green throughout. **A correct
guard reporting a true failure with the wrong cause**, which cost an operator
ruling and ten minutes of retries.

THE HOUSE PATTERN IS CWD, NOT `--repo`, and `gh()`'s own docstring already says
so: it sets the subprocess cwd from `repo_root` and lets `gh` derive the repo
from it. The two call sites this test was written for were the only places that
departed from it.

WHAT THIS CHECKS: no `gh` argv anywhere in the fleet carries `--repo`. That is
stricter than "carries a path" on purpose — a slug would work, and permitting it
would put the burden back on a reader to tell which kind of string a variable
holds, which is the burden that produced the bug.

WHAT IT DOES NOT CHECK: our own runners' `--repo`, which is a different flag on
a different program and is correct. The two are told apart by whether `gh` is the
program being invoked, which is why this reads argv construction rather than
grepping for the string.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

MODULES = Path(__file__).resolve().parents[2] / "modules"


def _python_files() -> list[Path]:
    found = sorted(MODULES.rglob("*.py"))
    assert len(found) > 20, (
        f"only {len(found)} modules found under {MODULES} — the walk is wrong, "
        f"and a guard that reads nothing passes silently"
    )
    return found


def _gh_argv_lists(tree: ast.AST) -> list[ast.List]:
    """Every list literal that looks like a `gh` argv being built."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.List):
            continue
        strings = [e.value for e in node.elts
                   if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        if not strings:
            continue
        # `["gh", "pr", ...]` or `["pr", "checks", ...]` handed to a gh runner
        if strings[0] == "gh" or (
                len(strings) > 1 and strings[0] in {"pr", "issue", "api", "run", "repo"}):
            out.append(node)
    return out


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: p.name)
def test_no_gh_argv_carries_a_repo_flag(path: Path) -> None:
    tree = ast.parse(path.read_text())
    offenders = []
    for lst in _gh_argv_lists(tree):
        for e in lst.elts:
            if isinstance(e, ast.Constant) and e.value == "--repo":
                offenders.append(f"line {lst.lineno}")
    # An argv extended later — `cmd += ["--repo", repo]` — is the exact shape that
    # shipped, so the append form is checked too. THE VARIABLE IS TRACKED rather
    # than guessed from its name: `build_helper.py` legitimately builds
    # `args += ["--repo", task.repo_target]` for one of OUR runners, and a
    # name-based rule flagged it. Only a name first ASSIGNED a gh-shaped argv
    # counts, which is the difference between the two cases and is decidable.
    gh_vars = {
        node.targets[0].id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.List) and node.value in _gh_argv_lists(tree)
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.AugAssign) or not isinstance(node.value, ast.List):
            continue
        if getattr(node.target, "id", None) not in gh_vars:
            continue
        if any(isinstance(e, ast.Constant) and e.value == "--repo"
               for e in node.value.elts):
            offenders.append(f"line {node.lineno} (`{node.target.id} += [...]`)")
    assert not offenders, (
        f"{path.name} builds a `gh` argv carrying `--repo` at {', '.join(offenders)}. "
        f"`gh --repo` wants OWNER/REPO and every `--repo` in this fleet is a "
        f"FILESYSTEM PATH, so the call fails with a message about the format and "
        f"the gate above it reads the failure as unreadable rather than as a bad "
        f"address.\n\nSet the subprocess cwd from `repo_root` instead — the pattern "
        f"`gh()`'s own docstring names as the house rule."
    )


def test_the_detector_would_SEE_the_shape_that_shipped() -> None:
    """The #124 regression, reproduced, so the failing path runs every time."""
    shipped = ('cmd = ["pr", "checks", pr, "--json", "name,state"]\n'
               'if repo:\n'
               '    cmd += ["--repo", repo]\n')
    tree = ast.parse(shipped)
    assert _gh_argv_lists(tree), "the argv recogniser no longer sees a gh command list"
    aug = [n for n in ast.walk(tree)
           if isinstance(n, ast.AugAssign) and isinstance(n.value, ast.List)
           and any(isinstance(e, ast.Constant) and e.value == "--repo"
                   for e in n.value.elts)]
    assert aug, "the `cmd += [\"--repo\", ...]` shape is invisible to the walk"
