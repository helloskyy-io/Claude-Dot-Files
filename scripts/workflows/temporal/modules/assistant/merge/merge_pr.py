"""Land a reviewed PR set, and drain the intake. TWO INDEPENDENT OPERATIONS.

WHY AN ACTIVITY AND NOT A CHILD. Walk the job and ask what needs judgement:
which PRs form the set (derivable from the run's output URLs), is CI green
(`ci_verdict`), did the reviewer say MERGE (it is in the durable block on the
thread), what order to merge in (a rule, written below), drain (`harvest`).
**Nothing is left to judge, so nothing needs a model** — and `plan-candidates`
records what it costs to get this wrong: the same job built as a model child was
*"1,605 lines, a 173-line prompt, and eight review holds every one of which was a
consequence of it being"* a child. It is also what the Architecture Standard
requires: *"Activity — External I/O, workflow-agnostic and idempotent. **A parent
may not inline any of it**."*

THE DRAIN AND THE MERGE ARE NOT ONE TRANSACTION, and modelling them as one is a
defect this module exists having already avoided. An intake is an ALREADY-RULED
finding — `review-pr` ruled it when it filed it — and the drain is GLOBAL, so it
carries intakes from other PRs including ones that will never merge. There is no
shared invariant, so there is no saga: coupling them would let a `gh` hiccup in an
unrelated queue block a reviewed, green PR from landing. `run_merge` therefore
reports both outcomes and lets NEITHER block the other.

ORDER MATTERS IN EXACTLY ONE PLACE — inside the PR set — and the asymmetry is
what decides it:

  * code merged, record not  -> an open PR. Visible, and the next run closes it.
  * record merged, code not  -> the planning repo asserts work that is not in.
    Silent, and false.

So the code PR lands first and the record PR second: **fail toward the state a
human can see.**

IDEMPOTENT THROUGHOUT, WHICH IS THE REAL ANSWER TO PARTIAL FAILURE. Merging a
merged PR is a no-op; `intake.harvest` survives a partial drain through
`_already_filed`. The remedy for any half-finished run is to run it again, which
is retry-to-convergence rather than ordering gymnastics.

INVOCATION IS THE APPROVAL, so there is no confirmation flag. Every auto-merge
system in the industry — Bors, Mergify, Prow/tide, `gh pr merge --auto` — merges
on green **plus a human approval**: they automate WHEN, never WHETHER. An operator
running this against a named PR IS that approval. A `--yes` prompt on top would be
theatre, because nobody re-reads the diff at the prompt.

WHAT MAKES IT SAFE IS THE PRECONDITIONS, and they are the whole of the safety.
Branch protection is rejected permanently on this account (a paid feature,
`cpi-decisions.md` 2026-08-16), and `tests.yml` runs on `pull_request` but nothing
ENFORCES it — so a red PR can be merged by hand today. Checking CI here is
literally required-status-checks, implemented where we can have it.

**A SIGNAL THAT CANNOT BE READ IS A REFUSAL, NEVER AN ALL-CLEAR.** Every
unreadable state below returns a refusal reason. The failure direction is "did not
merge", which costs one re-run; the other direction costs a merge nobody cleared.
"""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from ...journal import emit as journal_emit
from ...journal.events import Destination, Provenance
from .. import routing
from ..assistant_activities import ci_verdict
from ..review_pr import review_pr_activities as review_act
from ..review_pr import review_pr_helper as review_helper
from ..tracked import intake, tracked_items as ti


@dataclass(frozen=True)
class MergeReport:
    """What one invocation did. Both halves, independently."""

    merged: tuple[str, ...] = ()
    refused: tuple[tuple[str, str], ...] = ()      # (pr, why)
    drained: tuple[int, ...] = ()                  # intake issue numbers
    drain_error: str | None = None

    @property
    def ok(self) -> bool:
        return not self.refused and self.drain_error is None


class _MergeRefused(RuntimeError):
    """`gh pr merge` failed AND the PR is not merged — the store write truly failed.

    RAISED FROM INSIDE `perform`, WHICH IS THE WHOLE POINT. `gh pr merge --squash
    --delete-branch` is ONE process whose exit code covers the merge AND the
    cleanup, and the cleanup fails routinely here — `--delete-branch` cannot
    remove a branch checked out in a worktree, and this fleet dispatches from
    `.claude/worktrees/`. Measured on the first real invocation: PR #166 MERGED
    and `gh` exited non-zero.

    Before PMP Phase 3 that only cost a wrong console message, which
    `_merge_outcome_after_failure` already corrected in a handler. With the emit
    wired, correcting it in a handler is TOO LATE: `paired_write` sees `perform`
    raise, appends a `store_write_failure` event, and the journal is append-only —
    so a merge that LANDED is recorded, permanently and uncorrectably, as a write
    that did not. `applied_intents` then declines that intent forever, and a Phase
    4 rebuild concludes the merge never happened while the run's own report says
    it did. The record exists to be trusted over the report, so it is the record
    that has to be right.

    So the outcome is resolved BEFORE `perform` returns or raises, and this class
    is how the resolved detail reaches the caller without being re-derived: one
    `gh pr view`, one answer, carried rather than recomputed.
    """


def _gh_json(args: list[str], repo_root: Path) -> dict | None:
    """A `gh` read, or None when it could not be read. None is never 'fine'."""
    try:
        out = subprocess.run(["gh", *args], cwd=repo_root, capture_output=True,
                             text=True, check=True, timeout=120).stdout
        parsed = json.loads(out)
        return parsed if isinstance(parsed, dict) else None
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
        return None


def thread_verdict(pr: str, repo_root: Path) -> str | None:
    """The LATEST `pr_review:` block's verdict. None means it could not be read.

    LATEST, NOT THE UNION — the same rule `unclosed_hold` follows and for the
    same reason: every pass restates the finding set, so a PR held on pass 1 and
    cleared on pass 2 must read as cleared. Reading the union would refuse every
    PR that was ever held, permanently.
    """
    try:
        blocks = review_act.pr_review_blocks(pr, repo_root)
    except Exception:
        return None
    latest = review_helper.latest_pass_block(blocks)
    if latest is None:
        return None
    m = review_helper.BLOCK_VERDICT.search(latest)
    return m.group(1) if m else None


def refusals(pr: str, repo_root: Path) -> list[str]:
    """Every reason this PR may not merge. Empty means clear.

    ALL OF THEM, NOT THE FIRST — an operator fixing one blocker and rediscovering
    the next on the following run pays a round trip per reason.
    """
    why: list[str] = []

    verdict = thread_verdict(pr, repo_root)
    if verdict is None:
        why.append("no readable `pr_review:` verdict on the thread — this PR has "
                   "not been disposed, or the thread could not be read")
    elif verdict != routing.Verdict.MERGE.value:
        why.append(f"the latest review pass returned `{verdict}`, not MERGE")

    state, extra = ci_verdict(pr, repo_root=repo_root)
    if state is not routing.CiVerdict.GREEN:
        detail = f" ({', '.join(extra)})" if extra else ""
        why.append(f"CI is `{state.value}`, not green{detail} — this check IS the "
                   f"required-status-check this account cannot buy")

    view = pr_view(pr, repo_root)
    if view is None:
        why.append("`gh pr view` could not be read, so mergeability is unknown")
    elif view.get("state") != "OPEN":
        why.append(f"the PR is `{view.get('state')}`, not OPEN")
    elif view.get("mergeStateStatus") != "CLEAN":
        why.append(f"mergeStateStatus is `{view.get('mergeStateStatus')}`, not CLEAN "
                   f"— GitHub has not cleared this to merge")
    return why


#: How many times to re-ask when GitHub says `UNKNOWN`, and how long to wait.
#: FOUND ON THE FIRST REAL USE of this activity, against PR #166. `UNKNOWN` does
#: not mean "not mergeable" — it means GitHub has not COMPUTED mergeability yet,
#: and the query itself is what triggers the computation. Measured: one refusal
#: on `UNKNOWN`, then three consecutive `CLEAN` answers with no other change.
#:
#: SO A BARE REFUSAL ON `UNKNOWN` WOULD FIRE ON MOST FIRST INVOCATIONS, which is
#: the failure this repo learned to recognise elsewhere today: a stated failure
#: mode that triggers every time trains the reader to ignore the check. Retrying
#: is what every auto-merge tool does here, and it keeps the refusal meaningful
#: for the states that are real.
UNKNOWN_RETRIES = 3
UNKNOWN_WAIT_SECONDS = 2.0


def pr_view(pr: str, repo_root: Path) -> dict | None:
    """`state` and `mergeStateStatus`, re-asking while GitHub says `UNKNOWN`.

    RETURNS THE LAST ANSWER, INCLUDING A STILL-`UNKNOWN` ONE. Exhausting the
    retries is not the same as the field being clean, and the caller must still
    refuse — this bounds the wait, it does not convert an unknown into a yes.
    """
    view = None
    for attempt in range(UNKNOWN_RETRIES):
        view = _gh_json(["pr", "view", pr, "--json", "state,mergeStateStatus"],
                        repo_root)
        if view is None or view.get("mergeStateStatus") != "UNKNOWN":
            return view
        if attempt < UNKNOWN_RETRIES - 1:
            time.sleep(UNKNOWN_WAIT_SECONDS)
    return view


def merge_one(pr: str, repo_root: Path, *, dry_run: bool = False) -> str | None:
    """Squash-merge one PR and delete its branch. Returns an error, or None.

    SQUASH, matching every merge on this repo since #20, so `main` stays linear.
    """
    if dry_run:
        return None

    # PMP PHASE 3: A MERGE IS A STORE WRITE AND IT EMITS LIKE EVERY OTHER ONE.
    # This call site does NOT go through `assistant_activities.gh_attempt` — it
    # cannot, because that function retries and a merge must never be retried —
    # so the emit is applied here rather than inherited. That divergence is
    # exactly why requirement 9's inventory enumerates call sites rather than
    # trusting one choke point: a path that had a good reason to bypass the choke
    # point is a path with no emit, and nothing goes red.
    #
    # THE CONTENT IS THE INVOCATION, NOT PROSE. A merge authors nothing; what the
    # record needs is WHICH PR was merged, under which options, by which run. An
    # empty `content` would make the event indistinguishable from a write whose
    # body could not be read.
    def _merge() -> None:
        # ⚠ THE EXIT CODE COVERS THE CLEANUP TOO, AND THE CLEANUP IS NOT THE
        # MERGE — so this callable asks the OUTCOME before it returns or raises,
        # rather than letting a handler correct it afterwards. `--delete-branch`
        # fails when the branch is checked out in a worktree, which it always is
        # here; measured on PR #166, which MERGED while `gh` exited non-zero.
        #
        # THE PLACEMENT IS THE FIX AND NOT A STYLE CHOICE. `paired_write` writes
        # the journal from whether `perform` raises, and the journal is
        # append-only — so resolving this one handler-frame later records a
        # completed merge as a `store_write_failure` that can never be corrected,
        # and `applied_intents` declines it forever.
        try:
            subprocess.run(["gh", "pr", "merge", pr, "--squash",
                            "--delete-branch"],
                           cwd=repo_root, capture_output=True, text=True,
                           check=True, timeout=300)
        except subprocess.CalledProcessError as exc:
            detail = _merge_outcome_after_failure(exc, pr, repo_root)
            if detail is None:
                return          # MERGED; only `--delete-branch` failed
            raise _MergeRefused(detail) from exc

    emitter = journal_emit.current_emitter()
    try:
        if emitter is None:
            _merge()
        else:
            emitter.paired_write(
                write_path="gh:pr:merge",
                destination=Destination(store="github"),
                content=f"gh pr merge {pr} --squash --delete-branch",
                provenance=Provenance.FLEET_AUTHORED,
                perform=_merge)
        return None
    except journal_emit.StoreWriteFailed as recorded:
        # The `store_write_failure` event is already appended, and by the time we
        # are here that is the RIGHT record: `_merge` returned normally for every
        # case where the PR actually merged, so a raise reaching this point means
        # the merge did not land. The ORIGINAL failure is what the branches below
        # are written against, so it is unwrapped rather than replaced by the
        # emit wrapper's own class.
        cause = recorded.__cause__
        if isinstance(cause, _MergeRefused):
            return str(cause)
        if isinstance(cause, (subprocess.SubprocessError, OSError)):
            return str(cause)
        raise
    except _MergeRefused as exc:
        # The emitter was absent, so `_merge` was called directly. Same answer:
        # the outcome was resolved inside it and the detail is carried, not
        # recomputed — one `gh pr view` per failed merge, on either path.
        return str(exc)
    except (subprocess.SubprocessError, OSError) as exc:
        return str(exc)


def _merge_outcome_after_failure(exc: subprocess.CalledProcessError, pr: str,
                                 repo_root: Path) -> str | None:
    """ONE definition of "did it actually merge?", asked INSIDE `perform`.

    It was split out when the emit wrapper gave the question a second caller, and
    it now has one again — because the answer moved to the only place it can be
    correct. Asked from a handler, it corrects the console message after the
    journal has already recorded the opposite; asked from inside `perform`, the
    journal and the report are derived from one answer and cannot disagree.

    `None` means MERGED. A returned string is the operator-facing detail, and the
    caller carries it out on `_MergeRefused` rather than re-deriving it.
    """
    detail = (exc.stderr or exc.stdout or "gh pr merge failed").strip()
    view = _gh_json(["pr", "view", pr, "--json", "state"], repo_root)
    if view is not None and view.get("state") == "MERGED":
        return None                          # merged; only the cleanup failed
    return detail


def run_merge(prs: list[str], repo_root: Path, *, stores_root: Path | None = None,
              issues_repo: Path | None = None, dry_run: bool = False) -> MergeReport:
    """Land `prs` in the order given, and drain the intake. Neither blocks the other.

    `prs` IS ORDERED BY THE CALLER and the order is load-bearing: the code PR
    first, the record PR second (see the module docstring). This function does not
    reorder, because it cannot tell which is which — the caller knows.

    A REFUSAL STOPS THE SET, NOT JUST ITS OWN MEMBER. If the code PR will not
    merge, merging the record PR alone produces exactly the silent-and-false state
    the ordering exists to avoid. Later members are reported as refused with the
    reason naming the member that stopped it, so the report says what happened
    rather than going quiet.

    THE DRAIN RUNS REGARDLESS, INCLUDING AFTER A REFUSAL. Intakes are already-ruled
    findings with no dependence on this PR; withholding them because an unrelated
    merge failed would be the coupling this module refuses.
    """
    merged: list[str] = []
    refused: list[tuple[str, str]] = []

    for pr in prs:
        if refused:
            refused.append((pr, f"not attempted: `{refused[0][0]}` earlier in the "
                                f"set did not merge, and landing a record without "
                                f"its code asserts work that is not in"))
            continue
        why = refusals(pr, repo_root)
        if why:
            refused.append((pr, "; ".join(why)))
            continue
        err = merge_one(pr, repo_root, dry_run=dry_run)
        if err:
            refused.append((pr, f"merge failed: {err}"))
        else:
            merged.append(pr)

    drained: list[int] = []
    drain_error: str | None = None
    if stores_root is not None:
        root = (stores_root / ti.TRACKED_ROOT).resolve()
        if not root.is_dir():
            drain_error = (f"no tracked store at {root} — expected the four stores "
                           f"of Tracked Items Standard §1. Nothing harvested.")
        else:
            try:
                moved, failed = intake.harvest(
                    root, cwd=issues_repo or repo_root, dry_run=dry_run)
                drained = [n for n, _ in moved]
                if failed:
                    drain_error = ("; ".join(f"#{n}: {why}" for n, why in failed)
                                   + " — left OPEN deliberately; a malformed intake "
                                     "is a finding, and closing it would lose it")
            except Exception as exc:                       # noqa: BLE001
                drain_error = f"{type(exc).__name__}: {exc}"

    return MergeReport(merged=tuple(merged), refused=tuple(refused),
                       drained=tuple(drained), drain_error=drain_error)
