"""A corrector pointed at a held PR without `--correction-pass` must not proceed.

THE DEFECT, MEASURED ON MDC PR #204. `disposition.md` tells an operator to
dispatch a corrector child by hand against a held PR. The flag that tells the
child it is correcting — `correction_pass`, which drives the `${CORRECTION_NOTE}`
substitution — was settable only by the parent workflow. So the hand dispatch ran
its DEFAULT job: it re-derived all six estimates, concurred with all six, changed
two words, and reported *"no determined defect"*. **$8.60, 64 turns, 710 seconds,
nine findings still open, and a success report on top.**

WHY THE RUN COULD NOT HAVE KNOWN. Every signal was on the thread — the
disposition comment naming nine findings sat right there — and the run had no
reason to read it, because nothing told it it was correcting. That is what makes
this class invisible rather than merely wrong: the run was CORRECT for the pass
it was actually given.

THE TWO HALVES ARE TESTED SEPARATELY BECAUSE THEY FAIL SEPARATELY. Exposing the
flag makes the correction POSSIBLE; the refusal makes forgetting it VISIBLE. A
flag with no check is one typo from the same $8.60, and a check with no flag
leaves the operator refused with no way through.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from assistant.review_pr import review_pr_activities as act  # noqa: E402
from assistant.review_pr import review_pr_helper as helper  # noqa: E402

RUNNERS = ("run_plan_refine.py", "run_plan_sprint.py")
_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _block(*pairs: tuple[str, str]) -> str:
    """A `pr_review:` block asserting one `disposition:` per finding."""
    findings = "\n".join(
        f"    - id: {fid}\n      disposition: {disp}\n      hold_kind: redispatch"
        for fid, disp in pairs)
    return f"pr_review:\n  run_id: r1\n  findings:\n{findings}"


@pytest.mark.parametrize("runner", RUNNERS)
def test_the_flag_is_REACHABLE_from_the_standalone_entry_point(runner: str) -> None:
    """THE FIRST HALF. The parent could set it and an operator could not."""
    out = subprocess.run([sys.executable, str(_SCRIPTS / runner), "--help"],
                         capture_output=True, text=True, timeout=60).stdout
    assert "--correction-pass" in out, (
        f"{runner} does not expose --correction-pass, so a hand-dispatched "
        f"correction cannot be told it is correcting. The flag is plumbed into "
        f"the workflow and drives ${{CORRECTION_NOTE}}; only the CLI was missing.")


def test_an_EMPTY_thread_is_reported_as_clear_not_as_unreadable() -> None:
    """`[]` and `None` are different answers and the caller branches on both."""
    assert helper.latest_pass_block([]) is None
    assert helper.latest_pass_block(["a", "b"]) == "b"


def test_only_the_LATEST_block_decides_what_is_still_held(monkeypatch) -> None:
    """A finding held in pass 1 and FIXED in pass 2 is not still held.

    THE UNION WOULD BE WRONG FOREVER. Each pass restates the whole finding set
    with its current disposition, so a finding appears in every block from the
    one that opened it onward. Reading the union would report a closed hold and
    refuse every subsequent legitimate run on that PR.
    """
    monkeypatch.setattr(act, "pr_review_blocks", lambda pr, root: [
        _block(("F-1", "hold"), ("F-2", "hold")),
        _block(("F-1", "fixed"), ("F-2", "hold")),
    ])
    assert act.unclosed_hold("204", Path(".")) == ["F-2"]


def test_a_thread_with_NOTHING_held_does_not_refuse_the_run(monkeypatch) -> None:
    """THE CONTROL. A check that refuses everything is not a check."""
    monkeypatch.setattr(act, "pr_review_blocks", lambda pr, root: [
        _block(("F-1", "fixed"), ("F-2", "rejected"))])
    assert act.unclosed_hold("204", Path(".")) == []


def test_an_UNREADABLE_thread_is_NOT_reported_as_clean(monkeypatch) -> None:
    """`None`, not `[]` — and the distinction is the whole point.

    A missing `gh`, a rate limit or an offline machine must not block work, so
    the caller degrades to a warning. Answering `[]` would convert every
    unreadable thread into a clean bill of health — the same invisible-success
    shape this module exists to close, re-entering through the error path.
    """
    def _boom(pr, root):
        raise RuntimeError("gh: command not found")

    monkeypatch.setattr(act, "pr_review_blocks", _boom)
    assert act.unclosed_hold("204", Path(".")) is None
