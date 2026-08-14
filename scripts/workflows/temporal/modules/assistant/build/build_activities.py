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


# WHICH CHECKS GATE MERGE IS A FACT ABOUT THE REPO, NOT ABOUT THIS PARENT.
# The parent is generic across many repos; a constant enumerating each
# consumer's job names is the parent knowing things about its consumers, and
# the failure is silent-by-default — the next repo's checks match nothing, the
# gate reports a skip, and the only signal is a line someone has to be reading.
#
# MEASURED IMMEDIATELY: this shipped as `BLOCKING_CHECKS = ("suite",)` and the
# MDC side's gating job is named `master-test-tier`. Every one of their PRs
# would have returned NO_CHECKS — the gate adopted, none of it received.
#
# So the repo declares, and the parent reads. Onboarding a repo becomes adding
# one file TO THAT REPO, which is the correct ownership direction and the
# reason this scales past the second consumer.
POLICY_PATH = Path("testing") / "check-policy.yaml"


class CiVerdict(str, Enum):
    """Five states, and the last three are the ones that get fudged.

    NO_CHECKS AND GATE_DID_NOT_RUN WERE ONE STATE UNTIL 2026-08-13, AND
    COLLAPSING THEM COST TWO PRs THEIR MERGE GATE. Both mean "no blocking check
    reported", and the causes are opposites:

      - NO_CHECKS       — the repo declares no blocking checks. There is no gate
                          to wait for, and proceeding is correct.
      - GATE_DID_NOT_RUN — the repo DOES declare blocking checks and none of them
                          reported. The gate exists and produced nothing, which
                          is not a pass and must stop the run.

    The usual cause of the second is a conflicted PR: `pull_request` workflows
    run against the merge ref, GitHub cannot compute one for a conflicted PR, so
    no run is created at all. Zero runs render as zero failures.
    """

    GREEN = "green"
    RED = "red"
    NO_CHECKS = "no_checks"
    GATE_DID_NOT_RUN = "gate_did_not_run"
    UNREADABLE_POLICY = "unreadable_policy"


def read_check_policy(repo_root: Path) -> tuple[list[str], list[str], bool]:
    """Read the repo's own declaration of which checks gate it.

    Returns (blocking, advisory, readable). `readable` is False ONLY when the
    file exists and cannot be parsed — which is a DIFFERENT FACT from the file
    being absent, and collapsing the two is how the skip path becomes the new
    exit. A repo may legitimately have no gate; a repo whose declaration is
    broken has not said so.
    """
    path = repo_root / POLICY_PATH
    if not path.is_file():
        return [], [], True
    try:
        import yaml  # a hard preflight dependency; see scripts/preflight.py
        doc = yaml.safe_load(path.read_text()) or {}
        if not isinstance(doc, dict):
            return [], [], False
        blocking = [str(x) for x in (doc.get("blocking") or [])]
        advisory = [str(e.get("name")) if isinstance(e, dict) else str(e)
                    for e in (doc.get("advisory") or [])]
    except Exception:
        return [], [], False
    return blocking, advisory, True


def ci_verdict(pr: str, *, repo: str | None = None,
               repo_root: Path | None = None) -> tuple[CiVerdict, list[str]]:
    """Read the settled verdict for the checks THE TARGET REPO gates on.

    Returns the verdict and, for RED, the blocking checks that failed; for
    UNREADABLE_POLICY, nothing; for NO_CHECKS, any checks that ran but are
    declared nowhere.

    NO_CHECKS IS NOT GREEN. A repo with no declaration, or a PR whose gating
    workflows were all path-filtered out, reports nothing — and reading that as
    a pass is the filtered-gate defect wearing different clothes.

    A PENDING check is treated as absent rather than failing: `wait_for_ci` has
    already blocked for it, so a still-pending check means that wait timed out,
    which the caller knows about separately.
    """
    blocking: list[str] = []
    advisory: list[str] = []
    if repo_root is not None:
        blocking, advisory, readable = read_check_policy(repo_root)
        if not readable:
            return CiVerdict.UNREADABLE_POLICY, []

    cmd = ["gh", "pr", "checks", pr, "--json", "name,state"]
    if repo:
        cmd += ["--repo", repo]
    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        checks = json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        # Unreadable output is NOT green. Fail into the state that stops.
        return CiVerdict.NO_CHECKS, []

    names = {str(c.get("name")) for c in checks}
    # A check that ran and appears in NEITHER list is the third state the
    # Testing Standard says does not exist — "either on the merge path, or
    # documented as advisory." Surfaced, never silently gated: a check the repo
    # has not classified must not halt the fleet, but it must not hide either.
    undeclared = sorted(names - set(blocking) - set(advisory)) if (blocking or advisory) else []

    gating = [c for c in checks if str(c.get("name")) in blocking]
    if not gating:
        # THE SPLIT. `blocking` non-empty means this repo declares a gate; none
        # of it reporting means the gate did not run, which is the opposite of
        # "this repo has no gate" and must not share its outcome.
        if blocking:
            return CiVerdict.GATE_DID_NOT_RUN, sorted(blocking)
        return CiVerdict.NO_CHECKS, undeclared

    failed = [str(c["name"]) for c in gating
              if str(c.get("state", "")).upper() not in {"SUCCESS", "SKIPPED", "NEUTRAL"}]
    return (CiVerdict.RED, failed) if failed else (CiVerdict.GREEN, undeclared)


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
