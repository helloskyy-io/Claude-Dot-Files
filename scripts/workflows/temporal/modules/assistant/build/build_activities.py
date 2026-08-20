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

from .. import assistant_activities as shared
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

    UNREADABLE_CHECKS IS THE SAME LESSON ONE LAYER OUT, AND IT COST PR #92
    THREE REBUILDS ON 2026-08-14. `UNREADABLE_POLICY` already says that a
    declaration which cannot be READ is a different fact from one that does not
    exist. The CHECK LIST had no such state: a failed `gh pr checks` returns an
    empty stdout, which became `[]`, which is indistinguishable from "the gate
    reported nothing" — so a broken read rendered as GATE_DID_NOT_RUN, which is
    HOLD_REDISPATCH, which rebuilds. Three passes of build-refine ran against a
    PR that was OPEN, MERGEABLE and green on all four checks the entire time.

    The distinction earns its place because THE REMEDIES ARE OPPOSITE. A gate
    that did not run is usually a conflicted PR, and redispatching an engineer
    to resolve it is the right move. A gate that cannot be READ is an
    environment failure, and redispatching cannot fix it — it can only spend the
    loop budget discovering that again.
    """

    GREEN = "green"
    RED = "red"
    NO_CHECKS = "no_checks"
    GATE_DID_NOT_RUN = "gate_did_not_run"
    UNREADABLE_POLICY = "unreadable_policy"
    UNREADABLE_CHECKS = "unreadable_checks"


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

    cmd = ["pr", "checks", pr, "--json", "name,state"]
    # `--repo` IS NOT PASSED, and this comment is why rather than an omission.
    # Every workflow in this fleet takes `--repo` as a FILESYSTEM PATH — the
    # flag's own help says "never a gh slug" — and this function used to hand
    # that value straight to `gh`, which wants `OWNER/REPO`:
    #
    #     expected the "[HOST/]OWNER/REPO" format, got "/home/puma/Repos/..."
    #
    # Measured 2026-08-19 on PR #124: every read failed for the full 600s
    # deadline, the gate correctly refused to read unreadable as passing, and the
    # parent held a PR whose four checks were green the whole time. The gate was
    # right; the address was wrong.
    #
    # `gh` derives the repo from the process cwd, which `gh_attempt` sets from
    # `repo_root` — the pattern `gh()`'s own docstring states as the house rule
    # ("cwd rather than `--repo`"). These two calls were the outliers.
    # `gh_attempt`, NOT `subprocess.run`: THIS IS THE ONE-SHOT READ, and a single
    # transient 503 here parses as nothing, which is UNREADABLE_CHECKS, which is
    # a HOLD a human has to clear. `wait_for_ci` below is deliberately left
    # WITHOUT THE RETRY because its own deadline loop already re-reads — a retry
    # underneath a poll loop only makes each poll slower. It still goes through
    # `shared.run_bounded`, because a CEILING is not a RETRY and its deadline
    # loop cannot enforce one on a call that has not returned.
    #
    # `None` for the tree, not `repo_root`: this call addresses the PR with an
    # explicit `--repo` and has always run in the process cwd. Passing the tree
    # would change which repo `gh` infers when `--repo` is absent, which is a
    # different change from adding a retry.
    #
    # Nothing about the non-zero path moves. `gh pr checks` exits non-zero on
    # failing or pending checks with no HTTP status in stderr, so the classifier
    # calls that TERMINAL and spends exactly one attempt, and `gh_attempt`
    # returns the reply unjudged — which is why parsing, below, is still the
    # discriminator.
    result = shared.gh_attempt(cmd, None)

    # A REPLY THAT DOES NOT PARSE IS ITS OWN STATE, AND BOTH HALVES OF THIS WERE
    # WRONG. `if result.stdout.strip() else []` turned every FAILED `gh` — which
    # writes its error to stderr and leaves stdout empty — into an empty check
    # list, indistinguishable from a gate that reported nothing. With a gate
    # declared that renders as GATE_DID_NOT_RUN, which is HOLD_REDISPATCH, which
    # rebuilds: PR #92 ran build-refine three times while OPEN, MERGEABLE and
    # green on all four checks.
    #
    # And the `except` returned NO_CHECKS while calling it "the state that
    # stops" — NO_CHECKS appears in no HOLD branch in `build_workflow`, so it
    # PROCEEDS. Unparseable CI output could reach a MERGE verdict on a repo that
    # declares a gate. The comment described the intent; the enum member
    # delivered its opposite.
    #
    # `gh pr checks` exits non-zero whenever checks are FAILING or PENDING, so
    # the return code cannot be the discriminator here either. Parsing is.
    try:
        checks = json.loads(result.stdout)
        if not isinstance(checks, list):
            raise ValueError(f"expected a JSON list, got {type(checks).__name__}")
    except (json.JSONDecodeError, ValueError):
        return CiVerdict.UNREADABLE_CHECKS, []

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
            # The absent gate's names travel here so the runway can name them.
            # The CALLER must not read this as "checks that ran" — the
            # UNDECLARED-CHECKS branch does exactly that on the same value and
            # reported `suite` as unclassified while this branch reported it as
            # declared. Both messages fired on one run. See the guard in
            # build_workflow.
            return CiVerdict.GATE_DID_NOT_RUN, sorted(blocking)
        return CiVerdict.NO_CHECKS, undeclared

    failed = [str(c["name"]) for c in gating
              if str(c.get("state", "")).upper() not in {"SUCCESS", "SKIPPED", "NEUTRAL"}]
    return (CiVerdict.RED, failed) if failed else (CiVerdict.GREEN, undeclared)


# A check has SETTLED only in one of these. Everything else — IN_PROGRESS,
# QUEUED, WAITING, REQUESTED, or anything GitHub adds later — means keep
# waiting. Naming the terminal set rather than the pending one is what stops
# a new state silently reading as done.
_TERMINAL_CHECK_STATES = frozenset({
    "SUCCESS", "FAILURE", "SKIPPED", "NEUTRAL",
    "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STALE", "ERROR",
})


def wait_for_ci(pr: str, *, repo: str | None = None,
                repo_root: Path | None = None) -> bool:
    """Block until the PR's declared gate has REPORTED and settled.

    A False return is NOT a failure to propagate — it means the review runs
    against unsettled CI and must be told so, which is what --ci-unsettled
    carries. Treating a slow pipeline as a workflow error would strand PRs that
    are merely waiting.

    SETTLED IS NOT THE SAME AS PRESENT, AND CONFLATING THEM COST A BUILD ITS
    WHOLE LOOP BUDGET ON 2026-08-14. This returned True the instant no PENDING
    appeared — including when ZERO checks existed, because GitHub had not yet
    created the run for a push seconds earlier. That was harmless while an
    absent gate merely printed a warning and proceeded. Once an absent gate
    became a HOLD, the same race turned into: push, see nothing, hold, loop
    back, push, see nothing... three times, then spent, with the PR green and
    clean by the time a human looked.

    So when the repo declares blocking checks, their ABSENCE is now an unsettled
    state and this keeps waiting. Only a gate that never appears within the
    deadline reaches the caller as absent — which is the real signal, and the
    usual cause is a conflicted PR whose merge ref cannot be computed.

    THREE STATES, NOT TWO, AND THE THIRD IS WHY THE FIX ABOVE WAS NOT ENOUGH.
    IT RETURNS ON ALL THREE — this function NEVER raises:

      True   the declared gate has reported and nothing is PENDING
      False  CI was read successfully and the gate never appeared
      False  CI could not be READ AT ALL within the deadline — and a warning
             naming the last `gh` error goes to stderr, which is what separates
             this False from the one above it for a human. For the CALLER the
             separation is not here at all: `ci_verdict` reads the same replies
             immediately afterwards and classifies this one as
             `CiVerdict.UNREADABLE_CHECKS`. One function decides the verdict;
             this one only waits, and `build_workflow` forbids `exit 1` here.

    THIS BLOCK ITSELF SHIPPED THE DEFECT IT DESCRIBES. It read `raises  CI could
    not be READ AT ALL`, and an earlier pass did make it raise — the raise was
    reverted and the contract was not, so the docstring documented an outcome the
    code twelve lines below it explicitly says it does not produce. A caller
    trusting it writes an `except` that can never fire and reads the returned
    `False` as "the gate never appeared", which is exactly the read-failure /
    gate-absence conflation this whole function exists to remove. Nothing in the
    suite pinned the contract either way, so it stayed green throughout.
    `test_docstrings_do_not_promise_a_raise.py` is that pin now.

    The third state used to collapse into the second. `gh pr checks` exits non-zero
    whenever checks are FAILING or PENDING, so the return code cannot separate a
    red pipeline from a broken `gh` — and the settled test ran against raw
    stdout BEFORE parsing, so an empty reply read as "settled with no gate yet".
    A failed read therefore burned the whole deadline and returned the same
    `False` that means "gate absent", which the caller turns into a HOLD and a
    rebuild. Measured on a PR that was OPEN, MERGEABLE and green throughout.
    """
    blocking: list[str] = []
    if repo_root is not None:
        blocking, _advisory, _readable = read_check_policy(repo_root)

    deadline = time.monotonic() + CI_MAX_WAIT_SECONDS
    cmd = ["gh", "pr", "checks", pr, "--json", "name,state"]
    # `--repo` IS NOT PASSED, and this comment is why rather than an omission.
    # Every workflow in this fleet takes `--repo` as a FILESYSTEM PATH — the
    # flag's own help says "never a gh slug" — and this function used to hand
    # that value straight to `gh`, which wants `OWNER/REPO`:
    #
    #     expected the "[HOST/]OWNER/REPO" format, got "/home/puma/Repos/..."
    #
    # Measured 2026-08-19 on PR #124: every read failed for the full 600s
    # deadline, the gate correctly refused to read unreadable as passing, and the
    # parent held a PR whose four checks were green the whole time. The gate was
    # right; the address was wrong.
    #
    # `gh` derives the repo from the process cwd, which `gh_attempt` sets from
    # `repo_root` — the pattern `gh()`'s own docstring states as the house rule
    # ("cwd rather than `--repo`"). These two calls were the outliers.

    readable_replies = 0
    last_read_error = ""

    while time.monotonic() < deadline:
        # `run_bounded`, NOT raw `subprocess.run`: this loop's deadline is only
        # consulted BETWEEN iterations, so a single `gh` that never returns makes
        # `CI_MAX_WAIT_SECONDS` a number nothing enforces. The retry is still
        # deliberately absent here — the loop already re-reads — but a ceiling is
        # not a retry, and a timed-out reply lands in the same failed-read branch
        # below that an unparseable one does, which is already the right answer.
        result = shared.run_bounded(cmd)

        # PARSE FIRST, AND LET A FAILED READ BE ITS OWN STATE. `gh pr checks`
        # exits non-zero whenever checks are FAILING or PENDING, so the return
        # code cannot be the discriminator — a red pipeline and a broken `gh`
        # look identical through it. What separates "gh answered" from "gh
        # failed" is whether the payload parses.
        #
        # THIS IS THE DEFECT THAT COST PR #92 THREE REBUILDS. The previous
        # version tested `"PENDING" not in result.stdout.upper()` BEFORE
        # parsing, so an empty stdout — every failed `gh` invocation — read as
        # "settled", then parsed to an empty name set, which read as "the
        # declared gate has not appeared yet". A failed read was therefore
        # indistinguishable from a missing gate: it burned the full deadline,
        # returned False, and the caller turned that into a HOLD. Measured
        # 2026-08-14 on a PR that was OPEN, MERGEABLE and green on all four
        # checks the whole time. The cost is not the ten minutes, it is an
        # entire rebuild per occurrence.
        try:
            checks = json.loads(result.stdout or "")
            if not isinstance(checks, list):
                raise ValueError(f"expected a JSON list, got {type(checks).__name__}")
        except (json.JSONDecodeError, ValueError) as exc:
            last_read_error = (result.stderr or str(exc)).strip()[:300]
            time.sleep(CI_POLL_SECONDS)
            continue

        readable_replies += 1

        # Read the state off the PARSED payload rather than by scanning the raw
        # text. Same class of bug one size smaller: a check merely NAMED
        # something like `pending-review` would have matched the substring and
        # held a settled pipeline open forever.
        states = {str(c.get("state", "")).upper() for c in checks}
        # SETTLED IS AN ALLOW-LIST OF TERMINAL STATES, NOT A DENY-LIST OF ONE.
        # This tested `"PENDING" not in states`, which asks what the guard is
        # looking FOR and never what it is blind to — `gh pr checks` also emits
        # IN_PROGRESS and QUEUED, and both read as settled under that test.
        #
        # OBSERVED 2026-08-16 while polling PR #94: `IN_PROGRESS  suite`, with
        # `suite` the declared blocking gate. Under the old test that is
        # "settled, and the gate is present" — so the review proceeds against a
        # pipeline still running, which is the same false-green this fleet spent
        # two days removing from three other controls.
        #
        # The set is deliberately CLOSED: a state GitHub adds later is unknown,
        # and unknown must mean keep waiting rather than proceed.
        if states <= _TERMINAL_CHECK_STATES:
            if not blocking:
                return True
            names = {str(c.get("name")) for c in checks}
            # Every declared gate has reported: genuinely settled.
            if names & set(blocking):
                return True
            # Settled-looking but the gate is absent — keep waiting for it to appear.
        time.sleep(CI_POLL_SECONDS)

    # NEVER GOT A READABLE ANSWER. This still returns False rather than raising:
    # `build_workflow` states the rule outright — "HOLD, never `exit 1`: killing
    # the run discards a diff two passes just built" — and the gate immediately
    # after this call is what classifies an unreadable CI, via
    # `CiVerdict.UNREADABLE_CHECKS`. One function decides the verdict; this one
    # only waits.
    if readable_replies == 0:
        print(
            f"WARNING: could not read CI status for PR {pr} in "
            f"{CI_MAX_WAIT_SECONDS}s — every `gh pr checks` reply was "
            f"unparseable. Last error: {last_read_error or '(no stderr)'}",
            file=sys.stderr,
        )

    return False
