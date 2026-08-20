"""External I/O for the build workflow — Layer 3.

Everything BUILD-SPECIFIC that touches the outside world lives here. The CI
reads that used to sit alongside `run_child` were promoted to
`assistant_activities` when their consumer count reached six across three
families (§10.1 rule 3) — a plan or research parent could not reach them here
without importing the build family, and four of them consequently dispatched
`review-pr` on a verdict nobody read. Under step 3 these gain
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
from pathlib import Path

from .build_inputs import ChildResult


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
