"""The `--check` gate must be satisfiable, and must still catch real drift."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from planning_ui import cli


def test_the_gate_ignores_the_commit_it_was_generated_at():
    """Committing the artifact moves HEAD, which must not read as drift.

    Including `provenance.commit` in the comparison makes the gate
    unsatisfiable: generating at X and committing creates Y, so the next
    derivation stamps Y and disagrees with the committed X forever. This check
    is a blocking merge gate, so that refuses every pull request in the repo.
    """
    at_x = cli._serialise({"nodes": [1], "provenance": {"commit": "aaa", "commit_date": "d1"}})
    at_y = cli._serialise({"nodes": [1], "provenance": {"commit": "bbb", "commit_date": "d2"}})

    assert at_x != at_y, "the raw payloads differ — that is the trap"
    assert cli._comparable(at_x) == cli._comparable(at_y)


def test_the_gate_still_catches_a_corpus_change():
    """Excluding the stamp must not blunt the thing the gate is for."""
    before = cli._serialise({"nodes": [1], "provenance": {"commit": "aaa"}})
    after = cli._serialise({"nodes": [1, 2], "provenance": {"commit": "aaa"}})

    assert cli._comparable(before) != cli._comparable(after)


def test_the_stamp_survives_in_the_written_artifact():
    """It is excluded from the COMPARISON, not from the file."""
    graph = json.loads(cli._serialise({"provenance": {"commit": "aaa", "commit_date": "d1"}}))
    assert graph["provenance"]["commit"] == "aaa"


# ---------------------------------------------------------------------------
# Phase 6 · three artifacts (four since phase 3), one derivation, and a check that names the drift
# ---------------------------------------------------------------------------
PAGE = (
    "# The Decisions That Sit\n\n"
    "- **Commit read:** `aaa`\n"
    "- **Commit date:** 2026-09-12T00:00:00+00:00\n"
    "- **Input digest:** `sha256:1` over 3 files\n"
    "- **Ages counted back to:** 2026-09-10\n\n"
    "| a |\n|---|\n| 1 |\n"
)


def test_a_markdown_page_ignores_its_commit_stamp_but_not_its_content():
    """The same rule as the graph, on the pages: where-from is not compared,
    what-it-says is."""
    moved = PAGE.replace("`aaa`", "`bbb`").replace("2026-09-12T00", "2026-09-13T00")
    assert cli._comparable_markdown(PAGE) == cli._comparable_markdown(moved)
    assert cli._comparable_markdown(PAGE) != cli._comparable_markdown(PAGE.replace("| 1 |", "| 2 |"))
    # The stamp survives in the page; it is excluded from the COMPARISON only.
    assert "Commit read" in PAGE


def test_the_check_reads_the_reference_date_back_off_the_committed_page():
    """A check that used today's date would call every committed page stale
    by tomorrow; reading the page's own date compares like with like."""
    assert cli.read_as_of(PAGE) == date(2026, 9, 10)
    assert cli.read_as_of("# no stamp\n") is None


def test_rendering_every_artifact_walks_the_corpus_once(monkeypatch, tmp_path: Path):
    """The decisions page renders from the extraction result it is handed.

    `decisions.derive` used to call `extract` itself; a CLI that used it would
    have walked the corpus twice and the pages could disagree about what it
    contained. The control: `extract` is replaced with something that raises,
    AFTER the one derivation, and rendering must still succeed.
    """
    import importlib

    from planning_ui.plan_extractor import extract

    # The module, not the same-named function the package re-exports.
    decisions_derive = importlib.import_module("planning_ui.decisions.derive")

    root = tmp_path / "corpus"
    (root / "development" / "common" / "w").mkdir(parents=True)
    (root / "development" / "common" / "w" / "roadmap.md").write_text(
        "# W\n\n**Status:** 🟠 PLANNED\n\n**Depends on:** NONE\n"
    )
    (root / "development" / "sprints.md").write_text("# Sprints\n")
    result = extract(root)

    def forbidden(*_a, **_k):
        raise AssertionError("a second walk of the corpus")

    monkeypatch.setattr(decisions_derive, "extract", forbidden)
    artifacts = cli.render(result, date(2026, 9, 12), tmp_path)
    assert set(artifacts) == set(cli.artifacts(tmp_path).values())
    assert "Ages counted back to:** 2026-09-12" in artifacts[cli.artifacts(tmp_path)["decisions.md"]]
    # The fourth artifact carries the same provenance block as the graph, so
    # the check's one stamp-stripping rule covers both.
    where = cli.artifacts(tmp_path)
    assert (
        json.loads(artifacts[where["view-inputs.json"]])["provenance"]
        == json.loads(artifacts[where["plan-graph.json"]])["provenance"]
    )


@pytest.fixture()
def redirected(monkeypatch, tmp_path: Path) -> Path:
    """`main()` pointed at a scratch corpus, with its artifacts under it —
    at `development/derived/`, the real path, so the walk's own-output exclusion
    is exercised rather than sidestepped."""
    root = tmp_path / "corpus"
    (root / "development" / "common" / "w").mkdir(parents=True)
    (root / "development" / "common" / "w" / "roadmap.md").write_text(
        "# W\n\n**Status:** 🟠 PLANNED\n\n## P 🟠 PLANNED — **~2h**\n\n"
        "**Implementation:** [phase1_p.md](phase1_p.md)\n\n**Depends on:** NONE\n"
    )
    (root / "development" / "common" / "w" / "phase1_p.md").write_text("# P\n")
    (root / "development" / "sprints.md").write_text("# Sprints\n")
    # One knob now, because the root IS the parameter: every artifact path is
    # derived from it rather than patched alongside it.
    monkeypatch.setattr(cli, "default_root", lambda: root)
    return root


def test_generate_then_check_is_green_and_a_roadmap_edit_names_every_artifact(
    redirected: Path, capsys
):
    """Requirements 1 and 3 end to end, on a scratch corpus.

    The green leg is also the fixed-point check: the pages the generator wrote
    sit inside the tree the next derivation walks, and the check still agrees.
    """
    assert cli.main(["--as-of", "2026-09-12"]) == 0
    written = [p.name for p in cli.render(cli.derive(redirected), date(2026, 9, 12), redirected)]
    assert len(written) >= 5, "the artifact set is read from render(), never hand-typed"
    for name in written:
        assert (redirected / "development" / "derived" / name).exists()
    assert cli.main(["--check"]) == 0
    assert capsys.readouterr().out.count("current ") == len(written)

    roadmap = redirected / "development" / "common" / "w" / "roadmap.md"
    roadmap.write_text(roadmap.read_text().replace("🟠 PLANNED", "🟡 IN PROGRESS"))
    assert cli.main(["--check"]) == 1
    out = capsys.readouterr().out
    for name in (p.name for p in cli.render(cli.derive(redirected), date(2026, 9, 12), redirected)):
        assert f"STALE development/derived/{name}" in out, out


def test_a_missing_artifact_is_named_as_missing(redirected: Path, capsys):
    assert cli.main(["--as-of", "2026-09-12"]) == 0
    (redirected / "development" / "derived" / "consistency-report.md").unlink()
    assert cli.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "MISSING development/derived/consistency-report.md" in out
    assert "current development/derived/plan-graph.json" in out
    assert "current development/derived/decisions.md" in out
    assert "current development/derived/view-inputs.json" in out


def test_a_regeneration_on_a_later_day_is_still_current_to_the_check(redirected: Path):
    """The page states the date its clocks count back to and the check reads it
    back — so a page generated on the 10th is current on the 12th, and one
    the check compared against today would not be."""
    assert cli.main(["--as-of", "2026-09-10"]) == 0
    assert cli.main(["--check"]) == 0
    # And an explicit `--as-of` on the check that differs from the page's IS
    # drift — the page's clocks are part of its content.
    assert cli.main(["--check", "--as-of", "2026-09-12"]) == 1


class _Status:
    def __init__(self, returncode: int, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout


def test_a_pending_edit_check_that_could_not_run_is_not_reported_as_nothing_pending(
    monkeypatch, tmp_path: Path
):
    """`git status` refusing (a lock held, an unreadable .git) is a different
    fact from "no pending edits", and only the second is reassuring — the
    caller says which it got."""
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: _Status(128))
    assert cli._uncommitted_history_inputs(tmp_path) is None
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: _Status(0, ""))
    assert cli._uncommitted_history_inputs(tmp_path) == []


def test_what_a_merge_staged_is_not_a_pending_edit_but_an_unstaged_one_still_is(
    monkeypatch, tmp_path: Path
):
    """Mid-merge the log is walked from MERGE_HEAD too, so the merge's own
    staged inputs are visible to the page; an edit outside the index is not."""
    porcelain = (
        "A  tracked/issues/I-1.md\n"      # staged by the merge
        "M  development/sprints.md\n"     # staged by the merge
        "AM tracked/issues/I-2.md\n"      # staged, then edited again
        "?? tracked/candidates/C-9.md\n"  # not known to git at all
    )
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: _Status(0, porcelain))
    monkeypatch.setattr(cli, "merge_heads", lambda root: ["deadbeef"])
    assert cli._uncommitted_history_inputs(tmp_path) == [
        "tracked/issues/I-2.md",
        "tracked/candidates/C-9.md",
    ]
    # Outside a merge, everything git reports is pending.
    monkeypatch.setattr(cli, "merge_heads", lambda root: [])
    assert len(cli._uncommitted_history_inputs(tmp_path)) == 4


def test_the_serve_verb_is_the_third_caller_of_the_one_derivation(monkeypatch, redirected):
    """`serve` must start the server and nothing else: no write, no check.
    `serve()` is replaced so nothing listens; the verb's only job is to hand
    the address and the ONE repository it serves over — a root that already
    passed the contract, because the refusal runs before every verb."""
    import planning_ui.serve as serve_module

    calls: list[tuple[str, int, Path]] = []
    monkeypatch.setattr(serve_module, "serve", lambda bind, port, root: calls.append((bind, port, root)) or 0)
    assert cli.main(["serve", "--port", "9999", "--repo-root", str(redirected)]) == 0
    assert calls == [("127.0.0.1", 9999, redirected.resolve())]
    with pytest.raises(SystemExit):
        cli.main(["serve", "--check", "--repo-root", str(redirected)])


def test_serve_refuses_a_directory_that_is_not_a_corpus(tmp_path, capsys):
    """Hosted in the tooling, the package sits beside no corpus. The default
    root is wherever the caller stands, and a wrong one is refused by name
    before the server ever binds."""
    bare = tmp_path / "bare"
    bare.mkdir()
    assert cli.main(["serve", "--repo-root", str(bare)]) == 2
    assert "REFUSED" in capsys.readouterr().out


def test_a_root_that_is_not_a_planning_repository_is_refused_by_name(tmp_path, capsys):
    """Requirement 2: named at the layout that is missing, never read as an
    empty corpus — and a refusal exits distinctly from drift, so a caller can
    tell "this is not a corpus" from "this corpus has drifted"."""
    bare = tmp_path / "bare"
    bare.mkdir()
    assert cli.main(["--repo-root", str(bare), "--check"]) == 2
    out = capsys.readouterr().out
    assert "REFUSED" in out and "no `development/`" in out


def test_the_root_is_a_parameter_and_artifacts_land_in_the_repo_they_describe(
    redirected: Path, tmp_path, capsys
):
    """Requirement 3: derived artifacts belong to the corpus they are a
    reading of, never beside the package."""
    assert cli.main(["--repo-root", str(redirected), "--as-of", "2026-09-12"]) == 0
    capsys.readouterr()
    for name in cli.ARTIFACT_NAMES:
        assert (redirected / "development" / "derived" / name).exists()
    assert not (Path(cli.__file__).parent / "generated").exists()
    assert cli.main(["--repo-root", str(redirected), "--check"]) == 0
