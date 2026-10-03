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
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from common.journal import emit as journal_emit
from common.journal.events import Destination, Provenance
from .. import routing
from .. import assistant_activities as act
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
    bounded `gh pr view` re-ask, one answer, carried rather than recomputed.

    ⚠ AND THE ANSWER MAY BE "UNREAD", WHICH IS NOT "NOT MERGED". A detail
    carrying `UNRESOLVED_MERGE_PREFIX` means the verdict was never read; the run
    still fails toward "did not merge", and the operator is told to look.
    """


def _gh_json(args: list[str], repo_root: Path) -> dict | None:
    """A `gh` read, or None when it could not be read. None is never 'fine'.

    IT GOES THROUGH THE FLEET'S BOUNDED WRAPPER, AND IT WAS THE ONE `gh` READ
    THAT DID NOT. `gh_attempt` retries a transient server-side failure on a
    read-only verb and refuses to retry anything else; this function used to
    call `subprocess.run` directly, so a 503 or a throttle on either of its two
    callers was one attempt and then a `None`. Measured over `modules/`: this
    was the only such read — the other direct launch is the merge itself, which
    must NOT be retried because repeating it may act on a different state.

    `gh pr view` is read-only, so `gh_attempt` neither retries a write nor emits
    a journal event for one; the retries here are free of consequence.

    ⚠ `None` IS NOT AN ANSWER, AND THE TWO CALLERS OWE IT OPPOSITE DIRECTIONS.
    `pr_view` fails SAFE — an unreadable answer becomes a refusal to merge, which
    costs a re-run. `_merge_state` does not, and `_merge_outcome_after_failure`
    says so at length below. (`thread_verdict` above reaches `gh` through
    `review_act.pr_review_blocks` rather than through here, and fails safe on its
    own; it is named because an earlier draft of this paragraph counted it as a
    caller of this function, which it has never been.)
    """
    try:
        result = act.gh_attempt(list(args), repo_root)
        if result.returncode != 0:
            return None
        parsed = json.loads(result.stdout)
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
    if state is routing.CiVerdict.GATE_NOT_YET_RUN:
        # SAYS WHAT WAS READ, AND NOTHING PERMANENT. Skyy-Command #337 was refused
        # with the whole declared policy listed and "this account cannot buy"
        # attached, which read as a broken gate; the truth was one line — no jobs
        # yet for this head — and the same command merged minutes later. The
        # head is re-read for the message only, best-effort: a push between the
        # two reads can name a newer sha, and an unread one is said so.
        head = act.pr_head(pr, repo_root)
        sha = f"`{head[:8]}`" if head else "its head commit (head unread)"
        why.append(f"CI is `{state.value}`, not green — 0 check jobs found for "
                   f"{sha}: GitHub has not started CI for this commit yet. "
                   f"Transient; re-run this command once the workflow runs exist "
                   f"(if it persists, every workflow may be path-filtered out of it)")
    elif state is not routing.CiVerdict.GREEN:
        # For these two `extra` is the declared gate that is ABSENT, not checks
        # that ran — labelled, so seven names do not read as seven failures.
        absent = state in (routing.CiVerdict.GATE_DID_NOT_RUN, routing.CiVerdict.CONFLICTING)
        label = "declared blocking, none reported: " if absent else ""
        detail = f" ({label}{', '.join(extra)})" if extra else ""
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

#: How many times to re-ask "did it actually merge?" when the answer cannot be
#: READ, and how long to wait. SEPARATE FROM `UNKNOWN_RETRIES` ABOVE BECAUSE IT
#: ANSWERS A DIFFERENT QUESTION: that one re-asks a field GitHub has answered
#: with `UNKNOWN`, this one re-asks a call that did not answer at all.
#:
#: `gh_attempt` retries a transient failure that names an HTTP status, and it
#: deliberately treats a status-less one as terminal — a timeout and a transport
#: error both present with no status and are both left un-retried there. Those
#: are exactly the shapes a network blip produces, so the read that decides a
#: PERMANENT journal record gets its own bounded re-ask on top.
#:
#: THE TWO COMPOSE, AND THE WORST CASE IS STATED RATHER THAN LEFT TO BE
#: DISCOVERED. A persistently 503-ing read costs `gh_attempt`'s attempts inside
#: each of these, so at most 3 x (1 + len(_GH_RETRY_BACKOFF_SECONDS)) `gh pr view`
#: invocations and the sum of both backoffs before the outcome is called unread.
#: That is bounded, it happens only after a merge has already failed, and the
#: alternative — one attempt — is what journaled a landed merge as a failure.
OUTCOME_RETRIES = 3
OUTCOME_WAIT_SECONDS = 2.0

#: The prefix an operator-facing detail carries when the merge verdict was never
#: READ. It is not decoration: the string it replaces was `gh pr merge`'s own
#: stderr, which describes the CLEANUP that failed and says nothing about whether
#: the merge landed. Presenting it as the verdict is how "the branch could not be
#: deleted" reads as "the PR did not merge".
UNRESOLVED_MERGE_PREFIX = "MERGE OUTCOME UNREAD"


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
        # recomputed — one bounded `gh pr view` re-ask per failed merge, on
        # either path.
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

    ⚠ THREE OUTCOMES, NOT TWO, AND COLLAPSING THE THIRD INTO "NOT MERGED" IS THE
    DEFECT THIS PARAGRAPH EXISTS FOR. The read can say MERGED, say something
    else, or FAIL — and a failed read used to return `detail`, which is
    `gh pr merge`'s own stderr. On this path that stderr is almost always
    `failed to delete local branch`: a sentence about the CLEANUP, presented as
    the merge verdict, on the one path where the verdict decides a permanent
    append-only record. One transient `gh` failure on the read was therefore
    enough to journal a merge that LANDED as a `store_write_failure` — the exact
    outcome moving this question inside `perform` exists to prevent, surviving on
    the path that move created.
    """
    detail = (exc.stderr or exc.stdout or "gh pr merge failed").strip()
    state = _merge_state(pr, repo_root)
    if state == "MERGED":
        return None                          # merged; only the cleanup failed
    if state is None:
        # UNREAD, AND SAID SO. The direction is still "did not merge" — that is
        # the fail-safe half of this module's thesis and it does not change here
        # — but the DETAIL must not claim a verdict nobody read. An operator
        # seeing this line has one job: look at the PR, because if it merged, the
        # journal now carries a `store_write_failure` for a write that landed and
        # the journal is append-only.
        return (f"{UNRESOLVED_MERGE_PREFIX}: `gh pr merge` exited non-zero and "
                f"`gh pr view {pr} --json state` did not return a readable "
                f"`state` in {OUTCOME_RETRIES} attempts, so whether PR {pr} "
                f"merged is UNKNOWN and is being recorded as NOT MERGED. Check "
                f"the PR by hand. `gh pr merge` said: {detail}")
    return detail


def _merge_state(pr: str, repo_root: Path) -> str | None:
    """The PR's `state`, re-asking a read that did not answer. `None` means UNREAD.

    `None` IS NOT `"OPEN"`, and the whole value of this function is keeping those
    two apart for its caller. `_gh_json` returns `None` for an unreadable answer
    and a readable `{"state": "OPEN"}` is a different fact — the first says the
    question was not answered, the second answers it.

    A REPLY THAT PARSES BUT CARRIES NO `state` IS ALSO UNREAD, and it is folded
    in here rather than left to the caller: `{}` decodes cleanly, and
    `view.get("state")` on it returns the same `None` an unreadable call does. A
    caller that read those two as one fact would report "could not be read" for
    a shape defect, or worse, read a missing field as an answer.

    BOUNDED, AND EXHAUSTING THE RE-ASKS IS NOT THE SAME AS THE PR BEING OPEN. The
    caller must still say the outcome was unread, which is what
    `UNRESOLVED_MERGE_PREFIX` is for.
    """
    for attempt in range(OUTCOME_RETRIES):
        view = _gh_json(["pr", "view", pr, "--json", "state"], repo_root)
        state = view.get("state") if view is not None else None
        if isinstance(state, str) and state:
            return state
        if attempt < OUTCOME_RETRIES - 1:
            time.sleep(OUTCOME_WAIT_SECONDS)
    return None


#: The committed artifacts whose INPUT DIGEST spans the whole markdown corpus.
#: Their presence is what makes a repo need the refresh below; a repo without
#: them (this one) is never touched by it.
DERIVED_DIR = "development/derived"

#: The planning repo's own currency check, run FROM THE TOOLING the way the
#: githook runs it. parents[5] is `scripts/`: merge/ assistant/ modules/
#: temporal/ workflows/.
PLANNING_UI = Path(__file__).resolve().parents[5] / "services" / "planning-ui.sh"


def refresh_against_base(pr: str, repo_root: Path, *,
                         dry_run: bool = False) -> str | None:
    """Re-merge the base into a stale planning PR, regenerate, verify, push. Then REFUSE.

    `None` means NOTHING WAS DONE and the existing gates run unchanged. A string
    is a refusal reason, whatever happened — including success, because a push
    makes a new head with zero workflow runs and the merge must wait for them.

    WHY THIS EXISTS. `development/derived/*` carry an input digest over the
    whole corpus and CI checks them against the MERGE REF, so any commit landing
    on the base makes every open planning PR's artifacts stale — even a branch
    whose own conflicts are resolved. The `regenerate-on-merge` githook already
    regenerates correctly, but it is LOCAL and GitHub merges server-side with no
    hooks. This runs the merge locally so the hook can. Measured on skyynet #67:
    MERGE FIRST, REGENERATE SECOND — the other order derives the pre-merge corpus.

    THE HOOK IS DRIVEN, NOT REIMPLEMENTED. `git merge` and `git commit` run in
    a throwaway worktree of `repo_root`, whose hooks and `merge.binary.driver`
    are the clone's own. A clone without them stops on a whole-file conflict in
    `derived/` — taken from the base, then left to `--check` to judge.

    NO WAIT, BY DESIGN. After the push this refuses as transient and the caller
    re-runs; the next read finds `GATE_NOT_YET_RUN` and says so. A merge path
    that waits is a merge path that can hang (MDC-PM1, shape 3).

    ⚠ `--check` IS THE LAST WORD AND NOTHING IS PUSHED WITHOUT IT. A conflict
    outside `derived/` is a human's to resolve and is never auto-resolved.
    """
    if not (repo_root / DERIVED_DIR).is_dir():
        return None
    view = _gh_json(["pr", "view", pr, "--json",
                     "headRefName,baseRefName,isCrossRepository"], repo_root)
    if not view or view.get("isCrossRepository") is not False:
        # Unreadable, or a fork we cannot push to: change nothing. The gates
        # below refuse on their own when the read fails, and CI judges the rest.
        return None
    head, base = view.get("headRefName"), view.get("baseRefName")
    if not head or not base:
        return None

    def git(*args: str, cwd: Path = repo_root) -> subprocess.CompletedProcess:
        return act.run_bounded(["git", *args], cwd=cwd)

    fetch = git("fetch", "--no-tags", "origin",
                f"+refs/heads/{base}:refs/remotes/origin/{base}",
                f"+refs/heads/{head}:refs/remotes/origin/{head}")
    if fetch.returncode != 0:
        return (f"could not fetch `{base}` and `{head}` to see whether `{base}` "
                f"has moved under {DERIVED_DIR}/: {fetch.stderr.strip()}")
    tip = git("rev-parse", f"origin/{base}")
    fork = git("merge-base", f"origin/{base}", f"origin/{head}")
    if tip.returncode != 0 or fork.returncode != 0:
        return (f"could not tell whether `{base}` has moved under `{head}`: "
                f"{(tip.stderr + fork.stderr).strip()}")
    if tip.stdout.strip() == fork.stdout.strip():
        return None                       # THE COMMON CASE: current, nothing to do

    if dry_run:
        return (f"`{base}` has moved since `{head}` branched: a real run would "
                f"merge it, regenerate {DERIVED_DIR}/, verify and push, then "
                f"refuse until CI runs on the new head")

    wt = Path(tempfile.mkdtemp(prefix=f"merge-pr-{pr}-"))
    added = git("worktree", "add", "--detach", str(wt), f"origin/{head}")
    if added.returncode != 0:
        wt.rmdir()
        return f"could not create a worktree to refresh `{head}`: {added.stderr.strip()}"
    try:
        return _merge_regenerate_push(pr, head, base, wt, git)
    finally:
        git("worktree", "remove", "--force", str(wt))


def _merge_regenerate_push(pr: str, head: str, base: str, wt: Path, git) -> str:
    """The body of `refresh_against_base`, inside its throwaway worktree."""
    merge = git("merge", "--no-edit", f"origin/{base}", cwd=wt)
    if merge.returncode != 0:
        diff = git("diff", "--name-only", "--diff-filter=U", cwd=wt)
        unmerged = diff.stdout.split() if diff.returncode == 0 else []
        outside = [p for p in unmerged if not p.startswith(DERIVED_DIR + "/")]
        in_progress = git("rev-parse", "-q", "--verify", "MERGE_HEAD", cwd=wt).returncode == 0
        if outside or not in_progress or diff.returncode != 0:
            git("merge", "--abort", cwd=wt)
            what = (f"conflicts outside {DERIVED_DIR}/ — {', '.join(outside)}"
                    if outside else (merge.stderr or merge.stdout or diff.stderr).strip())
            return (f"`{base}` has moved and merging it into `{head}` stopped: "
                    f"{what}. A content conflict is a human's to resolve; nothing "
                    f"was pushed")
        if unmerged:
            # derived/-only: take the base's side whole, then the pre-commit
            # hook regenerates over it — the githook's rule, "regenerate, never
            # pick hunks". `--theirs` is the base: it is the side being merged in.
            git("checkout", "--theirs", "--", *unmerged, cwd=wt)
            git("add", "--", *unmerged, cwd=wt)
        # No unmerged paths and MERGE_HEAD present is the pre-merge-commit hook's
        # veto, which asks for exactly this `git commit`.
        commit = git("commit", "--no-edit", cwd=wt)
        if commit.returncode != 0:
            git("merge", "--abort", cwd=wt)
            return (f"merged `{base}` into `{head}` but the commit failed: "
                    f"{(commit.stderr or commit.stdout).strip()}; nothing was pushed")

    check = act.run_bounded([str(PLANNING_UI), "--repo-root", str(wt), "--check"], cwd=wt)
    if check.returncode != 0:
        return (f"merged `{base}` into `{head}`, but `planning-ui.sh --check` "
                f"exited {check.returncode} on the result, so NOTHING WAS PUSHED: "
                f"{(check.stdout + check.stderr).strip()}. Is the clone's "
                f"regenerate-on-merge hook registered?")

    push = git("push", "origin", f"HEAD:refs/heads/{head}", cwd=wt)
    if push.returncode != 0:
        return (f"merged and verified `{head}` against `{base}`, but the push "
                f"was refused: {push.stderr.strip()}")
    sha = git("rev-parse", "--short=8", "HEAD", cwd=wt)
    pushed = f"`{sha.stdout.strip()}`" if sha.returncode == 0 else "the new head (sha unread)"
    return (f"`{base}` had moved: merged it into `{head}`, regenerated "
            f"{DERIVED_DIR}/, `planning-ui.sh --check` exit 0, pushed "
            f"{pushed}. Not merged on this run")


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
        # A REFRESH ALWAYS REFUSES, whatever it did: a push means CI has not run
        # on the new head, and the existing gate below says so in its own words.
        # It is listed FIRST so that the gate's `GATE_NOT_YET_RUN` reads as the
        # consequence of the push it follows — and it is kept even if the gate
        # reads GitHub before GitHub has seen the push and finds nothing wrong.
        refreshed = refresh_against_base(pr, repo_root, dry_run=dry_run)
        why = ([refreshed] if refreshed else []) + refusals(pr, repo_root)
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
                    awaiting, close_failed, malformed = intake.classify(failed)
                    advice = []
                    if malformed:
                        advice.append("a malformed intake is a finding and is left OPEN "
                                      "deliberately; fix what its reason names")
                    if awaiting:
                        advice.append("a record not yet committed must not be reported "
                                      "filed; commit the store")
                    if close_failed:
                        advice.append("a close that failed leaves a committed record; "
                                      "fix the gh error")
                    drain_error = ("; ".join(f"#{n}: {why}" for n, why in failed)
                                   + " — left OPEN: " + "; ".join(advice)
                                   + ". Then re-run the harvest")
            except Exception as exc:                       # noqa: BLE001
                drain_error = f"{type(exc).__name__}: {exc}"

    return MergeReport(merged=tuple(merged), refused=tuple(refused),
                       drained=tuple(drained), drain_error=drain_error)
