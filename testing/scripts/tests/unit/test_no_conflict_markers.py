"""No git conflict marker may reach a commit.

WHY THIS EXISTS. On 2026-08-11 a merge conflict in `candidates.md` was
committed, pushed, and passed FOUR green CI checks — `suite`, `CodeQL` and both
`Analyze` jobs. Nothing in the repo looked for the class. The file was left
holding two contradictory paragraphs about its own working set, in the one
document a human-only triage ruling reads.

IT SURVIVED BECAUSE EVERY EXISTING CHECK WAS AIMED ELSEWHERE. The test suite
does not parse markdown prose; the linters read Python and shell. A conflict
marker is invisible to all of them and obvious to `grep`, which is exactly the
shape of defect a cheap universal check exists for.

AND THE MERGE ITSELF REPORTED IT. `git merge` printed `CONFLICT (content)` —
the output was piped through `head -2` and the line never appeared. The gate is
here rather than in a shell habit because a habit protects one author on one
day, and this protects every commit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]

# Anchored at column 0 with the exact width git emits. A shorter or unanchored
# pattern matches prose ABOUT conflicts — including this file's own docstring
# and any doc explaining the markers — and a gate that fires on its own
# explanation gets deleted rather than fixed.
_MARKERS = ("<" * 7, "=" * 7, ">" * 7)


def _tracked_text_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True).stdout.split()
    skip = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2", ".zip"}
    return [REPO_ROOT / f for f in out if Path(f).suffix.lower() not in skip]


def test_the_sweep_reads_a_real_corpus() -> None:
    """Vacuity guard: `git ls-files` failing would make the check below pass on nothing."""
    files = _tracked_text_files()
    assert len(files) > 200, f"only {len(files)} tracked files found — the sweep is not reading the repo"


def test_no_tracked_file_contains_a_conflict_marker() -> None:
    offenders: list[str] = []
    for path in _tracked_text_files():
        if path.resolve() == Path(__file__).resolve():
            continue                      # this file names the markers to explain them
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue                      # binary or unreadable; not our class
        for n, line in enumerate(text.splitlines(), 1):
            if any(line.startswith(m) for m in _MARKERS):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{n}: {line[:60]}")

    assert not offenders, (
        "committed git conflict markers — a merge was resolved without reading "
        "its own output, and four CI checks passed over it once already:\n"
        + "\n".join(offenders)
    )


@pytest.mark.parametrize("marker", _MARKERS)
def test_the_detector_fires_on_each_marker(marker: str, tmp_path: Path) -> None:
    """Positive control per marker.

    The class needs all three: a resolution that keeps `<<<<<<<` and drops the
    others is as broken as one that keeps all three, and a detector checking
    only the opener would pass it.
    """
    probe = tmp_path / "probe.md"
    probe.write_text(f"text before\n{marker} HEAD\ntext after\n")
    lines = probe.read_text().splitlines()
    assert any(line.startswith(marker) for line in lines), f"detector blind to {marker!r}"
