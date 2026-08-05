"""External I/O for the revision workflow — Layer 3.

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

import subprocess
import sys
import time
from pathlib import Path

from .revision_inputs import ChildResult

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
