"""The viewer's commit hook stages `development/derived/` into every commit whose
corpus moved, and every plan-family run commits in a repo that registers it. A
boundary that read the hook's output as the model's edit failed every correct run
at the last guard (predicted from source on skyynet-master-planning #47,
2026-09-20, the first plan commit after the hook began regenerating on every
commit). The exemption lives once, in `boundary_crossings`, and this file holds it
to the hook's own `git add` line so a moved output directory moves the exemption.
"""
from __future__ import annotations

import re
from pathlib import Path

from modules.assistant.plan import plan_activities as act

HOOK = (Path(__file__).resolve().parents[5]
        / "scripts" / "services" / "planning_ui" / "githooks" / "regenerate-on-merge")
FORBIDDEN = (r"^development/",)


def _staged_by_the_hook() -> str:
    m = re.search(r"^git add (\S+)$", HOOK.read_text(), re.M)
    assert m, f"{HOOK} no longer stages its output with a `git add <path>` line"
    return m.group(1)


def test_the_exemption_is_the_path_the_hook_stages() -> None:
    staged = _staged_by_the_hook().rstrip("/") + "/"
    assert any(re.match(p, staged) for p in act.HOOK_STAGED_PATHS), (
        f"the hook stages {staged!r} but HOOK_STAGED_PATHS={act.HOOK_STAGED_PATHS} "
        f"does not cover it — the next plan-family commit fails at the boundary")
    assert all(re.match(p, staged) for p in act.HOOK_STAGED_PATHS), (
        "HOOK_STAGED_PATHS exempts a path the hook does not stage")


def test_a_regenerated_artifact_is_not_a_crossing_under_any_grant() -> None:
    before = {"development/derived/roadmap.html": "a"}
    after = {"development/derived/roadmap.html": "b",
             "development/derived/new.json": "c"}
    assert act.boundary_crossings(before, after, FORBIDDEN, permitted=()) == []


def test_a_sibling_of_the_output_directory_still_crosses() -> None:
    before = {"development/derivedx/roadmap.html": "a",
              "development/edge/phase1.md": "a"}
    after = {"development/derivedx/roadmap.html": "b",
             "development/edge/phase1.md": "b"}
    assert act.boundary_crossings(before, after, FORBIDDEN, permitted=()) == [
        "development/derivedx/roadmap.html", "development/edge/phase1.md"]
