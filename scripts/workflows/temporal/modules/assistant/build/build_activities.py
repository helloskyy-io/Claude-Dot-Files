"""External I/O for the build workflow — Layer 3.

Everything that touches the outside world lives here. Under step 3 these gain
`@activity.defn` and nothing else changes; that is the whole reason for putting
them in their own module now rather than inlining them in the workflow.

IDEMPOTENCY WARNING, carried from the addendum (§A1). `run_child` is NOT
idempotent — the children it invokes push commits and open PRs. Under Temporal a
retry is therefore a NEW ATTEMPT, not a replay of the same work, and these must
be registered with a retry policy that reflects that. Do not let a default
policy silently re-run a child that already opened a PR.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from enum import Enum
from pathlib import Path

from .build_inputs import ChildResult

# How long CI is given to settle before a review reads its result. The bash
# activity polled the GitHub API; this preserves the behaviour and the boundary.
CI_POLL_SECONDS = 20
CI_MAX_WAIT_SECONDS = 600


def run_child(script: Path, args: list[str], *, stream: bool = True) -> ChildResult:
    """Invoke a child workflow and capture its output.

    Streams to the operator's terminal while capturing, because the output is
    both a live progress signal and the handoff channel — the child's terminal
    line carries the PR URL or the verdict token.
    """
    if not script.exists():
        raise FileNotFoundError(f"child workflow not found: {script}")

    proc = subprocess.Popen(
        [str(script), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    captured: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        captured.append(line)
        if stream:
            sys.stdout.write(line)
            sys.stdout.flush()

    return ChildResult(exit_code=proc.wait(), output="".join(captured))


# The checks this repo OWNS and has ruled merge-blocking. Everything else that
# runs on a PR is advisory, and §"what is consequently not covered" is stated
# with it rather than left implicit.
#
# WHY A NAMED SET AND NOT "ALL". Four checks run here and only one is ours.
# `suite` is our test runner. `CodeQL` and `Analyze (…)` are GitHub default
# setup — we did not configure them, cannot fix them, and CodeQL produced a
# 12-failure burst on 2026-08-06 with no cause on our side. Gating on them
# would let the scanner breaking halt the fleet.
#
# AND THE DISTINCTION THAT DECIDES IT: `gh pr checks` reports JOB STATUS. A
# CodeQL job failure means the scan did not COMPLETE — not that it FOUND
# something. Gating on job status conflates infrastructure with findings.
#
# NOT COVERED, stated plainly: a PR whose CodeQL job failed merges UNSCANNED.
# The push-to-`main` scan catches it after the fact, which is the mitigation
# that makes this carve-out honest rather than convenient.
BLOCKING_CHECKS = ("suite",)


class CiVerdict(str, Enum):
    """Three states, and the third is the one that gets fudged."""

    GREEN = "green"
    RED = "red"
    NO_CHECKS = "no_checks"


def ci_verdict(pr: str, *, repo: str | None = None) -> tuple[CiVerdict, list[str]]:
    """Read the settled verdict for the checks this repo gates on.

    Returns the verdict and the names of any BLOCKING checks that failed.

    NO_CHECKS IS NOT GREEN, and saying so is the whole point of the third state.
    A repo with no workflows — or a PR whose workflows were all path-filtered
    out — returns no checks, and reading that as a pass is the filtered-gate
    defect wearing different clothes. The caller reports it as an explicit skip.

    A check that is PENDING at this point is treated as absent rather than as
    failing: `wait_for_ci` has already blocked for it, so a still-pending check
    means the wait timed out, which the caller already knows about separately.
    """
    cmd = ["gh", "pr", "checks", pr, "--json", "name,state"]
    if repo:
        cmd += ["--repo", repo]
    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        checks = json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        # Unreadable output is NOT green. Fail into the state that stops.
        return CiVerdict.NO_CHECKS, []

    gating = [c for c in checks if c.get("name") in BLOCKING_CHECKS]
    if not gating:
        return CiVerdict.NO_CHECKS, []

    failed = [c["name"] for c in gating
              if str(c.get("state", "")).upper() not in {"SUCCESS", "SKIPPED", "NEUTRAL"}]
    return (CiVerdict.RED, failed) if failed else (CiVerdict.GREEN, [])


def wait_for_ci(pr: str, *, repo: str | None = None) -> bool:
    """Block until the PR's checks settle. Returns False if they did not.

    A False return is NOT a failure to propagate — it means the review runs
    against unsettled CI and must be told so, which is what --ci-unsettled
    carries. Treating a slow pipeline as a workflow error would strand PRs that
    are merely waiting.
    """
    deadline = time.monotonic() + CI_MAX_WAIT_SECONDS
    cmd = ["gh", "pr", "checks", pr, "--json", "state"]
    if repo:
        cmd += ["--repo", repo]

    while time.monotonic() < deadline:
        result = subprocess.run(cmd, capture_output=True, text=True)
        # `gh pr checks` exits non-zero when checks are failing OR pending, so the
        # exit code alone cannot distinguish "settled and red" from "still running".
        # Absence of PENDING in the payload is the settled signal.
        if "PENDING" not in result.stdout.upper():
            return True
        time.sleep(CI_POLL_SECONDS)

    return False
