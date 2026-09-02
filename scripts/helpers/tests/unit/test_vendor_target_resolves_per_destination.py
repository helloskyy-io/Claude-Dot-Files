"""`--target` must write where the TARGET keeps the file, and `--check` must report.

TWO BUGS, BOTH FOUND BY CONSUMING THE MIRROR RATHER THAN READING THE SCRIPT, and
both reported success while doing the wrong thing — the class that survives
review.

  1 · `--target` probed the destination ROOT and then wrote every file to THIS
      ecosystem's sub-layout. MDC nests development standards one tier deeper, so
      two of four landed at a path nobody reads while the originals stayed
      authoritative-looking and stale. It printed `✓ mirrored` four times and
      exited 0. Two of four matched only because `documentation/` happens to sit
      at the same depth in both repos — a coincidence doing the work of a rule.

  2 · `--check` died on a destination that is not yet a mirror. An original has no
      banner, so no `^---$`; grep exits 1, `pipefail` propagates it and `set -e`
      killed the script — exit 2, no output, with the `[[ -z "$n" ]]` guard
      written for exactly that case left unreachable. A check that dies silently
      on a first-time destination reads as "nothing to report" when it means
      "did not run".
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "vendor-standards.sh"
SMP = Path("/opt/skyy-net/skyynet-master-planning")


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT), *args],
                          capture_output=True, text=True, timeout=300)


@pytest.fixture
def nested_target(tmp_path: Path) -> Path:
    """A destination whose layout differs from ours, holding a bannerless ORIGINAL.

    Both halves matter: the nesting is what bug 1 got wrong, and the missing
    banner is what killed bug 2.
    """
    if not (SMP / "standards").is_dir():
        pytest.skip(f"no planning repo at {SMP}; this drives the real script")
    dst = tmp_path / "standards" / "development" / "testing"
    dst.mkdir(parents=True)
    (tmp_path / "standards" / "documentation").mkdir(parents=True)
    src = (SMP / "standards" / "testing" / "testing_standard.md").read_text()
    (dst / "testing_standard.md").write_text(src.split("\n---\n", 1)[1])
    return tmp_path


def test_check_REPORTS_on_a_bannerless_destination(nested_target: Path) -> None:
    """It must not exit silently. Reporting drift is fine; saying nothing is not."""
    r = _run("--check", "--target", str(nested_target))
    assert (r.stdout + r.stderr).strip(), (
        "--check produced NO output against a pre-mirror destination — that is "
        "the silent death, and it reads as 'nothing to report'")
    assert "testing_standard.md" in r.stdout + r.stderr


def test_the_mirror_lands_ON_the_existing_file_wherever_the_target_keeps_it(
        nested_target: Path) -> None:
    """THE GUARD. A duplicate is worse than a failure: two answers, one question."""
    _run("--target", str(nested_target))
    found = sorted(nested_target.rglob("testing_standard.md"))
    assert len(found) == 1, (
        f"{len(found)} copies after mirroring — it duplicated instead of "
        f"replacing: {[str(p) for p in found]}")
    assert found[0].parent.name == "testing", "wrote to our layout, not the target's"
    assert found[0].read_text().startswith("<!-- VENDORED"), "not replaced"


def test_AMBIGUITY_is_refused_rather_than_guessed(nested_target: Path) -> None:
    """THE CONTROL. Probing must not become guessing.

    Two files of one name in a target means a human decides which is the
    standard — mirroring over the wrong one is unrecoverable from inside the tool.
    """
    _run("--target", str(nested_target))
    other = nested_target / "standards" / "elsewhere"
    other.mkdir(parents=True)
    shutil.copy(next(nested_target.rglob("testing_standard.md")), other)

    r = _run("--target", str(nested_target))
    assert "Refusing to guess" in r.stdout + r.stderr, (
        "an ambiguous destination was resolved by picking one")
