"""The map states WHERE THINGS ARE, and a check that cannot read it must say so.

WHY THIS EXISTS. `docs/file_structure.txt` is a reference document whose one job is
location. Measured on this repo the day the check landed: **745 of 1,079 lines were
continuation prose — 69% of the map was essay**, written into a tree diagram where it
breaks the column alignment that is the diagram's only reason to exist.

THE VACUITY ARM IS THE HALF THAT MATTERS. The first version of this check read
`skyynet-master-planning`'s prose-form map, parsed 4 entries out of 136 lines, and
printed `clean`. A green result produced by reading almost nothing is an ABSENT check,
and it is more dangerous than no check because somebody trusts it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[3] / "helpers" / "file_structure_check.py"


def _repo(tmp_path: Path, map_text: str) -> Path:
    repo = tmp_path / "r"
    (repo / "docs").mkdir(parents=True)
    for d in ("alpha", "beta", "gamma", "delta"):
        (repo / d).mkdir()
        (repo / d / "f.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "docs" / "file_structure.txt").write_text(map_text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    return repo


def _run(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), "--repo-root", str(repo), "--check"],
                          capture_output=True, text=True)


FULL = ("r/\n├── alpha/      # one\n├── beta/       # two\n"
        "├── gamma/      # three\n└── delta/      # four\n")


def test_a_ONE_LINE_PER_ENTRY_MAP_PASSES(tmp_path: Path) -> None:
    """The positive control. Without it every assertion below is satisfied by a
    check that refuses everything."""
    r = _run(_repo(tmp_path, FULL))
    assert r.returncode == 0, r.stdout
    assert "clean" in r.stdout


def test_PROSE_WEDGED_INTO_THE_MAP_IS_A_FINDING(tmp_path: Path) -> None:
    """THE MUTATION: one entry grows an explanation. A map states location; rationale
    injected into reference is what destroyed the alignment on the real file."""
    r = _run(_repo(tmp_path, FULL.replace(
        "├── beta/       # two\n",
        "├── beta/       # two\n│                # and here is why it is two, at length\n")))
    assert r.returncode == 1
    assert "PROSE INSIDE THE MAP" in r.stdout and "1 continuation" in r.stdout


def test_AN_ENTRY_NAMING_NOTHING_IS_A_FINDING(tmp_path: Path) -> None:
    """A map naming a deleted file is worse than silence, because a reader trusts it."""
    r = _run(_repo(tmp_path, FULL.replace("└── delta/", "└── deleted_last_year/")))
    assert r.returncode == 1
    assert "NAMES NOTHING IN THE REPO" in r.stdout


def test_A_MAP_THIS_CHECK_CANNOT_READ_IS_REFUSED_NOT_CALLED_CLEAN(tmp_path: Path) -> None:
    """⚠ THE VACUITY CONTROL, and the reason the tool has a coverage floor at all.

    A prose map with a couple of tree lines parsed as 4 entries and printed `clean`.
    The mutation here is that shape: almost all prose, one real entry, three top-level
    directories unaccounted for. It must REFUSE rather than pass.

    A "does the file contain tree characters" test was tried first and did not fire,
    because such a file has a few. Presence of the syntax proves nothing; whether the
    map accounts for the repo is the question.
    """
    prose = ("Annotated repo map\n==================\n"
             + "This map rolls its directories up rather than enumerating them.\n" * 20
             + "├── alpha/      # the only one named\n")
    r = _run(_repo(tmp_path, prose))
    assert r.returncode == 1, r.stdout
    assert "is not a pass" in r.stdout.lower() or "NOT a pass" in r.stdout
    assert "clean" not in r.stdout, (
        "a map the checker cannot read must never report clean — that is an absent "
        f"check wearing a green result: {r.stdout}")
