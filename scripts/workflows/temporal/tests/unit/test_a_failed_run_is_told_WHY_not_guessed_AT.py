"""The completion gate must report the cause the log states, not the one it assumes.

THE DEFECT, MEASURED 2026-08-20. When a dispatch produced no `VERDICT:` line,
`run-claude.sh` printed *"headless early-stop suspected — most common cause: the
main loop ended a turn with a text-only message"*. That diagnosis was hardcoded,
and the log's own result row carried `is_error: true` beside a plain-English
reason the gate never read:

    "You've hit your session limit · resets 3:20am (America/New_York)"
    "API Error: The response stopped arriving. The response above may be incomplete."

FOUR RUNS, THREE WORKFLOWS, TWO DISTINCT REAL CAUSES, all four reported as a
suspected early stop: `plan-revision` (2026-08-13, transport), `review-pr` twice
and `build-refine-minor` once (2026-08-20, one transport and two quota).

WHY IT IS A DEFECT AND NOT A COSMETIC ONE. The two causes have OPPOSITE remedies.
A transport or quota failure is re-dispatched unchanged and needs no code touched.
An early stop means the prompt permits a text-only turn to end the run, and the
prompt has to change. Naming the second when the first happened sends the operator
to rewrite a prompt that was never wrong — and on the night this was found, it also
made four completed-then-failed dispatches look like four broken workflows.

THE GATE ITSELF IS CORRECT AND STAYS. A run that finishes cleanly and emits no
verdict really has stopped early, and catching that is worth having. What changed
is that the claim is now conditional on evidence rather than asserted over it.

WHY THE BANNER IS ITS OWN FUNCTION NOW. It was welded inside `run_claude`, so the
only way to reach it was to run a whole dispatch — meaning the branch that reports
the wrong cause was the one branch nothing could execute. `_wds_undetermined` was
split out of the same file for the same reason, and this follows it rather than
inventing a second convention.

WHAT THIS DOES NOT LOOK AT:
  * It does not check that the gate FIRES — `COMPLETION_PATTERN` matching is the
    caller's half and is unchanged here. This module only asks what the banner
    says once the caller has decided to print one.
  * It does not read `.claude/logs`. The fixtures below carry the two real
    strings verbatim, so the module stays green on a machine with no history.
  * It asserts the operator is told the right cause, never that they acted on it.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
RUN_CLAUDE = REPO_ROOT / "scripts" / "workflows" / "activities" / "run-claude.sh"

pytestmark = pytest.mark.skipif(shutil.which("jq") is None, reason="jq is required")

# Anchored on the function's own boundaries, like the sibling extractor in
# `test_turn_cap_banner_reads_the_worktree`. Extracting by line span would go
# red on an unrelated edit above it, which is the wrong red.
_BANNER_FN = re.compile(r"^_completion_failure_banner\(\) \{\n.*?\n\}$",
                        re.DOTALL | re.MULTILINE)

# The two real strings, verbatim from the runs that produced them.
QUOTA = "You've hit your session limit · resets 3:20am (America/New_York)"
TRANSPORT = "API Error: The response stopped arriving. The response above may be incomplete."


def _shipped_banner() -> str:
    m = _BANNER_FN.search(RUN_CLAUDE.read_text())
    assert m, "run-claude.sh no longer defines _completion_failure_banner"
    body = m.group(0)
    # A positive control on the EXTRACTOR, not on the function: a regex that
    # matched a truncated span would run every assertion below against a stub
    # and pass the ones phrased as absence.
    assert body.count("\n") > 15, f"the extraction is too short to be the banner:\n{body}"
    return body


def _log(tmp_path: Path, rows: list[dict], junk: bool = False) -> Path:
    f = tmp_path / "run.jsonl"
    lines = [json.dumps(r) for r in rows]
    if junk:
        # Raw stderr noise mid-stream. `_log_events` documents that a reader
        # MUST survive it, and the sibling gate one function over carries a
        # `fromjson? // empty` prefilter for exactly this. Two readers of one
        # file disagreeing about whether it may contain junk is how a gate
        # deletes itself, so this fixture holds this one to the same bar.
        lines.insert(1, "warning: something wrote to stderr")
    f.write_text("\n".join(lines) + "\n")
    return f


def _run(tmp_path: Path, log: Path) -> str:
    """The shipped banner, executed as shipped, under the v2 caller's shell."""
    script = f'{_shipped_banner()}\n_completion_failure_banner "$1" "$2"\n'
    out = subprocess.run(["bash", "-c", script, "_", str(log), "^VERDICT: (MERGE|HOLD)$"],
                         capture_output=True, text=True, timeout=30)
    return out.stderr


@pytest.mark.parametrize("reason", [QUOTA, TRANSPORT], ids=["quota", "transport"])
@pytest.mark.parametrize("junk", [False, True], ids=["clean", "with_stderr_noise"])
def test_a_run_that_REPORTED_an_error_is_not_called_an_early_stop(
    tmp_path: Path, reason: str, junk: bool
) -> None:
    banner = _run(tmp_path, _log(tmp_path, [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "working"}]}},
        {"type": "result", "subtype": "success", "is_error": True,
         "num_turns": 56, "result": reason},
    ], junk=junk))

    assert reason in banner, (
        "the run stated why it failed and the banner did not repeat it. The "
        "operator now has to open the log to learn something the gate had in "
        f"hand.\n--- banner ---\n{banner}")
    assert "early-stop suspected" not in banner, (
        "the banner still calls a reported failure a suspected early stop. Those "
        "have opposite remedies — re-dispatch versus rewrite the prompt — so this "
        f"sends the operator to fix something that is not broken.\n{banner}")
    assert "does not need changing" in banner, (
        "the banner names the cause but does not tell the operator what to do "
        "with it. Naming a quota reset without saying 're-dispatch, the prompt is "
        "fine' leaves the same wrong action available.")


def test_a_CLEAN_finish_with_no_verdict_IS_still_called_an_early_stop(
    tmp_path: Path,
) -> None:
    """THE OTHER HALF, AND THE ONE A NARROW FIX WOULD HAVE BROKEN.

    The gate exists to catch a run that ends a turn on text while work is
    outstanding. Making the error case honest must not cost that: with no error
    reported and no verdict emitted, early-stop is the right diagnosis and the
    banner must still say so.
    """
    banner = _run(tmp_path, _log(tmp_path, [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "waiting"}]}},
        {"type": "result", "subtype": "success", "is_error": False,
         "num_turns": 12, "result": "waiting on dispatched agents"},
    ]))

    assert "early-stop suspected" in banner, (
        "a clean finish with no verdict is exactly the case this gate was built "
        f"for, and it no longer reports it.\n--- banner ---\n{banner}")
    assert "text-only" in banner, (
        "the early-stop arm lost the sentence naming the cause an operator can "
        "act on")


def test_the_banner_NAMES_THE_LOG_on_both_arms(tmp_path: Path) -> None:
    """Whichever arm fires, the next step is reading the log — so both must say
    where it is. An arm that drops the path sends the operator hunting."""
    for is_error, reason in ((True, QUOTA), (False, "no verdict")):
        log = _log(tmp_path, [{"type": "result", "subtype": "success",
                               "is_error": is_error, "result": reason}])
        banner = _run(tmp_path, log)
        assert str(log) in banner, (
            f"the {'error' if is_error else 'early-stop'} arm does not name the "
            f"log file.\n--- banner ---\n{banner}")
