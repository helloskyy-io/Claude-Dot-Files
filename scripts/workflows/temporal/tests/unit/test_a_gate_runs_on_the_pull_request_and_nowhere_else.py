"""Testing Standard § A gate runs on the pull request, and nowhere else.

Actions minutes are metered and shared across every private repository, so a
workflow with a `push:` trigger spends a run that decides nothing — the fleet's
merge gate reads the pull-request head. The rule was ruled once and applied to
one file; the scaffold template kept the old trigger and every repository
scaffolded from it inherited a post-merge run (measured 2026-09-20: the larger
half of the bill on both private planning repositories). Three surfaces are
held here: this repository's workflows, the template `init-project.sh` writes,
and the sibling planning repository's workflows when it is checked out.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from planning_corpus import PLANNING_ROOT

REPO_ROOT = Path(__file__).resolve().parents[5]
INIT_PROJECT = REPO_ROOT / "scripts" / "helpers" / "init-project.sh"


def _scaffold_template() -> str:
    m = re.search(r"cat > \.github/workflows/checks\.yml <<'CHECKSYML'\n(.*?)\nCHECKSYML",
                  INIT_PROJECT.read_text(), re.S)
    assert m, f"{INIT_PROJECT} no longer writes checks.yml through a CHECKSYML heredoc"
    return m.group(1)


def _surfaces() -> list[tuple[str, str]]:
    found = [(f"scaffold template in {INIT_PROJECT.name}", _scaffold_template())]
    for root in (REPO_ROOT, PLANNING_ROOT):
        for f in sorted((root / ".github" / "workflows").glob("*.y*ml")):
            found.append((str(f.relative_to(root.parent)), f.read_text()))
    return found


@pytest.mark.parametrize("name,text", _surfaces(), ids=[n for n, _ in _surfaces()])
def test_the_trigger_is_pull_request_only_with_one_run_per_branch(name: str, text: str) -> None:
    doc = yaml.safe_load(text)
    on = doc.get("on", doc.get(True))
    triggers = set(on) if isinstance(on, dict) else {on} if isinstance(on, str) else set(on)
    assert triggers == {"pull_request"}, (
        f"{name}: triggers on {sorted(triggers)} — a gate runs on the pull request "
        f"and nowhere else (Testing Standard). A `push:` run spends metered minutes "
        f"on a result nothing reads.")
    conc = doc.get("concurrency") or {}
    assert conc.get("cancel-in-progress") is True and "head_ref" in str(conc.get("group", "")), (
        f"{name}: no `concurrency` block cancelling the previous run on the same "
        f"branch — a rapid push series bills every run")


def test_the_check_would_see_a_push_trigger() -> None:
    bad = "name: x\non:\n  pull_request:\n  push:\n    branches: [main]\nconcurrency:\n  group: ${{ github.head_ref }}\n  cancel-in-progress: true\n"
    with pytest.raises(AssertionError, match="nowhere else"):
        test_the_trigger_is_pull_request_only_with_one_run_per_branch("control", bad)
