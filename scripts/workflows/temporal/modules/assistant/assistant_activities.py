"""Shared I/O for the assistant edge's workflows — promoted per §10.1 rule 3.

Sits at module level because more than one workflow uses it: consumer count
decides, never taste. Anything here is shared BY DEFINITION, so a reader never
opens a file to learn its scope.

NOT IDEMPOTENT (§7.1 / addendum §A1): these push commits and open PRs. Under
Temporal a retry is a NEW ATTEMPT, not a replay — register with a retry policy
that reflects that.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import os
import time
import uuid
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from . import resource_telemetry
from . import routing

_WORKFLOWS = Path(__file__).resolve().parents[3]          # scripts/workflows
_SHARED_PROMPTS = Path(__file__).resolve().parent / "prompts"

# RE-EXPORTED, NOT RE-TYPED — `routing.py` owns the PR-URL address, the same way
# it owns `parse_verdict`. This module carried a byte-identical anchored copy
# while a THIRD declaration (`routing.pr_number_from_url`) had no host anchor at
# all; see `routing.PR_URL` for why the weak one was the one that mattered.
PR_URL = routing.PR_URL



def _resource_limits() -> dict:
    """`resource_limits:` from config.yaml. Absent means unbounded, not defaulted.

    No fallback dict. A silent default would be a ceiling nobody chose, which is
    indistinguishable at read time from one somebody measured — and the entire
    reason this module exists is that an unexamined ceiling took a host down.
    """
    import yaml  # a hard preflight dependency; see scripts/preflight.py
    path = _WORKFLOWS.parents[1] / "config.yaml"
    if not path.is_file():
        return {}
    return (yaml.safe_load(path.read_text()) or {}).get("resource_limits") or {}


def max_turns(key: str) -> int:
    """This workflow's turn budget, from config.yaml's `max_turns:` map.

    THE VALUE MATTERS AND HAS COST REAL MONEY. A draft once ran at 120 against
    the 250 its task class needed and burned a full budget producing nothing
    recoverable — V1's own logs already held the answer, 130 turns for the same
    work. That is why this is read rather than guessed, and why a missing key
    raises instead of defaulting.

    KEYED BY WORKFLOW, NOT BY MODEL. `research-write` and `research-verify`
    share MODEL_KEY "research" and have separately-measured budgets of 150 and
    200. Keying off the model would silently collapse them, which is the exact
    class of silent divergence this read exists to prevent.

    WHAT THIS REPLACED, so it does not come back: `v1_constant()` recovered
    these integers by running a regex over the V1 bash scripts at runtime. It
    was a real fix for a real problem — re-declaration had caused three
    production failures, and deriving made divergence impossible rather than
    merely detectable. But it made the Python fleet unable to START if the bash
    fleet were deleted, pointing the dependency at precisely the fleet that is
    meant to go away, and it parsed an executable as data. Config belongs in
    the config file. Both fleets read it now; neither reads the other.
    """
    import yaml  # a hard preflight dependency; see scripts/preflight.py
    path = _WORKFLOWS.parents[1] / "config.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"config.yaml not found at {path}")
    doc = yaml.safe_load(path.read_text()) or {}
    value = (doc.get("max_turns") or {}).get(key)
    if value is None:
        raise KeyError(
            f"no '{key}' in the max_turns: map of {path} — add it there rather "
            f"than hardcoding a cap at the call site"
        )
    return int(value)

# ── EVERY SUBPROCESS THIS FLEET LAUNCHES HAS A CEILING ─────────────────────
#
# A `gh` or a `git` that never RETURNS is invisible to every guard in this tree.
# The retry below, `wait_for_ci`'s deadline loop, and every `returncode` check
# here all run AFTER the call comes back — so a TCP connection that neither
# answers nor resets, which is the ordinary shape of a degraded endpoint and
# GitHub was degraded on 2026-08-17, parks the dispatch forever with no ceiling
# and no log line. The retry this module adds is bounded in ADDED LATENCY and
# said nothing about wall-clock until this constant existed.
#
# ONE NUMBER, DELIBERATELY. Per-command budgets would each need defending and
# would go stale silently as call sites move.
#
# AND IT IS A POLICY CHOICE, NOT A MEASUREMENT — said plainly because every
# other constant in this module cites one (`_RETRYABLE_HTTP`'s shapes and
# `_GH_RETRY_BACKOFF_SECONDS`' pauses were both captured from the live outage),
# and a reader is entitled to know which kind of number this is. 120s is a
# false-positive tolerance: how long a legitimate call may take before the fleet
# would rather be wrong than keep waiting. Nothing was timed to produce it.
#
# WHICH CALL EXCEEDS IT FIRST, AND WHAT THAT LOOKS LIKE. `git fetch` in
# `worktree_add` is the only size-dependent launch here — every `gh` call is a
# bounded API read — so a large target repo on a slow link is the realistic
# false positive. The operator sees "did not answer within 120s", which reads
# as a hang rather than as "your repo is large". If that ever happens the fix is
# a larger budget for THAT call, not a larger one here.
_SUBPROCESS_TIMEOUT_SECONDS = 120.0


class TimedOutProcess(subprocess.CompletedProcess):
    """A launch that never answered, wearing the shape every caller already reads.

    DISTINGUISHED BY TYPE, NOT BY EXIT CODE. `returncode` is 124 so a log line
    carries the `timeout(1)` convention a reader recognises, but a classifier
    keyed on that number would be wrong the first time `gh` or `git` exits 124
    for a reason of its own. `isinstance` cannot collide with a real reply.

    NON-ZERO SO A SITE THAT ALREADY BRANCHES ON `returncode` IS CORRECT — AND A
    SITE THAT DOES NOT IS NOT. Returning this instead of letting `TimeoutExpired`
    escape is what keeps a brand-new exception path out of a running fleet, and
    for the sites that raise, poll, or degrade on a non-zero code a timeout
    belongs in the branch they already have.

    THIS PARAGRAPH USED TO ASSERT THAT EVERY CONVERTED CALLER WAS ALREADY
    CORRECT, AND THAT CLAIM IS WHAT SHIPPED THE DEFECT. It was a universal
    supported by three named behaviours; six production sites route through
    `run_bounded`, one of the three named behaviours (`""` for absent metadata)
    describes `journal_activities._git`, which bounds itself and is not one of
    them, and `observe_outcome`'s `git status` read — which was one of them —
    discarded its return code entirely and printed "Uncommitted changes: none"
    for a worktree it had never read. A reviewer found it two passes later. The
    claim is not restated in a fixed form here on purpose: `run_bounded` cannot
    know what its callers do, so the property belongs where it can be CHECKED —
    `test_a_bounded_reply_is_CHECKED_not_only_read.py` walks the call sites and
    goes red on the seventh one that reads `.stdout` without reading `rc`.

    READ IT THROUGH `is_timed_out`, NOT THROUGH `isinstance` DIRECTLY. The type
    is the in-process signal and `timed_out` is the one that survives a
    serialization boundary; see that predicate for why the distinction matters
    to the Temporal port.
    """

    timed_out = True


def is_timed_out(r: subprocess.CompletedProcess) -> bool:
    """Did this reply come from a call that never answered?

    ONE PREDICATE, TWO SIGNALS, BECAUSE ONE OF THEM DOES NOT SURVIVE A BOUNDARY.
    `isinstance` is exact and free in-process. It is also Python type identity,
    and the stated port plan (`sprint.md` § Temporal Integration — *"semantic
    wrappers: `@activity.defn` over the plain functions"*) puts an activity
    boundary between `run_bounded` and its callers. Across it the subclass is
    gone, and a hang would silently read as an ordinary non-zero reply: safe
    today only by ACCIDENT, because the synthesized stderr happens to carry no
    `HTTP nnn` token so `_gh_transient_reason` still refuses it — one wording
    change away from flipping.

    `timed_out` is a plain bool and survives. Checking both means the port
    cannot quietly delete a distinction two operator-facing log lines depend on,
    and it costs one `getattr`.
    """
    return isinstance(r, TimedOutProcess) or getattr(r, "timed_out", False)


def run_bounded(cmd: list[str], *, cwd: Path | str | None = None,
                timeout: float = _SUBPROCESS_TIMEOUT_SECONDS
                ) -> subprocess.CompletedProcess:
    """`subprocess.run` with a wall-clock ceiling and no new exception path.

    THE SINGLE LAUNCH POINT FOR THIS FLEET, and
    `test_every_subprocess_the_fleet_launches_is_bounded.py` is what keeps it
    single: no module under `modules/` may reach `subprocess.run` without a
    `timeout=`, so the next launch added anywhere either comes through here or
    states its own bound out loud. The check is on the CLASS rather than on the
    seven other sites that existed when it was written — six of them `git` and
    only one `gh` — and a guard listing the sites it knew about would have been
    green on the eighth.

    PARTIAL OUTPUT IS DISCARDED, WHICH IS A DELIBERATE NARROWING.
    `TimeoutExpired` carries whatever the child had written before it was
    killed, and quoting half an answer into the failure message invites exactly
    the conflation this module spent a PR removing — a fragment of a reply is
    not a reply, and a reader who sees JSON in a stderr message will try to read
    it. What the message states instead is the one fact that is certain: the
    call did not finish inside its budget.

    THE CEILING BINDS THIS PROCESS, NOT THE PROCESS TREE. `subprocess.run`
    SIGKILLs the direct child on expiry and then, on POSIX, `wait()`s for it —
    verified against this interpreter's own `inspect.getsource(subprocess.run)`
    rather than assumed, because the Windows branch does re-enter `communicate()`
    unbounded and reading the wrong branch turns this note into a false alarm.
    So `run_bounded` DOES return inside its budget. What it does not do is reap
    a GRANDCHILD: `git fetch` spawns `git-remote-https`, and SIGKILLing `git`
    orphans that. It holds a pipe nobody reads and blocks nobody; it is a leak,
    not a hang, and bounding it means process groups, which is a larger decision
    than this function should make on its own. THE SCOPE CONDITION ON "leak, not
    a hang" IS THAT THIS PROCESS IS SHORT-LIVED — a dispatch exits and the OS
    reaps. Under a long-lived Temporal worker the orphans accumulate for the
    worker's lifetime instead, so the conclusion changes when the port does.
    """
    try:
        return subprocess.run(cmd, cwd=str(cwd) if cwd is not None else None,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return TimedOutProcess(
            cmd, 124, stdout="",
            stderr=f"`{' '.join(str(c) for c in cmd)}` did not answer within "
                   f"{timeout:.0f}s and was killed. A hung call is not a server "
                   f"condition a repeat would satisfy, so it is not retried.")


def worktree_add(repo_root: Path, name: str, ref: str) -> Path:
    """Create an isolated worktree, matching V1's behaviour exactly.

    ISOLATION IS AN INVARIANT, NOT A PARAMETER. An earlier V2 skipped the
    worktree on `--pr` runs via a ternary, which put a run directly on the
    operator's main working tree — a live host here. A run dying mid-write would
    leave that tree dirty on a checked-out foreign branch with no discard path.
    V1 always creates one (`git worktree add -f` on the PR branch); so does this.

    A FAILED FETCH IS FATAL WHEN THE REF IS A REMOTE ONE. V1 ran its fetch under
    `set -euo pipefail`, so a fetch that failed aborted the script. Here it was
    unchecked, and the silent case is the dangerous one: when `origin/<branch>`
    already exists locally from an earlier run, `git worktree add` then SUCCEEDS
    against stale content and the run plans on top of a base that has moved —
    the kind of wrong answer that gets acted on. The check is scoped to
    `origin/`-prefixed refs, and as of `base_ref` EVERY fleet caller passes one —
    both arms are `origin/`-prefixed, so the fetch is always checked and the
    unchecked path is unreachable from inside this fleet. The scoping stays
    because the signature is public and a caller may still hand it a local ref
    (`HEAD`, a bare branch name) that resolves without the network; V1's own
    new-branch path did no fetch at all.

    STRIP THE PREFIX, NOT THE SUBSTRING. `removeprefix` and not `replace` here:
    branch names legitimately contain "origin/" mid-string (`sync-origin/main`,
    `team/origin/legacy-migration`), and `replace` would fetch a ref that does
    not exist. Paired with the fatal check above that turns a mangled name into
    a hard failure whose message names the wrong branch — wrong AND misleading.
    """
    wt = repo_root / ".claude" / "worktrees" / name
    remote_branch = ref.removeprefix("origin/")
    f = run_bounded(["git", "fetch", "-q", "origin", remote_branch],
                    cwd=repo_root)
    if f.returncode != 0 and ref.startswith("origin/"):
        raise RuntimeError(
            f"git fetch origin {remote_branch} failed: {f.stderr.strip()}. "
            f"Refusing to cut a worktree from {ref} — a stale local copy of that ref "
            f"would succeed here and put the run on a base that has already moved."
        )
    r = run_bounded(["git", "worktree", "add", "-f", str(wt), ref],
                    cwd=repo_root)
    if r.returncode != 0:
        raise RuntimeError(f"worktree add failed for {ref}: {r.stderr.strip()}")
    return wt


def observe_outcome(worktree: Path, branch: str | None = None) -> str:
    """Read what git ACTUALLY did. Never assert a negative without reading.

    THIS EXISTS BECAUSE A FAILURE BANNER LIED. A run that exhausted its turn cap
    printed "NOTHING was committed or pushed" — and it had committed and pushed,
    9 files and +798/-111, landing on the PR branch. The operator read the banner,
    concluded the work was lost, and dispatched a second full-budget run against
    work that was already there.

    The banner asserted what the harness BELIEVED rather than reading what git
    DID, because the turn-cap path exits before observing state. A false negative
    on the failure path is worse than a crash: a crash is obviously wrong, while
    a confident wrong answer gets acted on.

    Returns a human-readable observation. If it cannot determine the state it
    SAYS SO — it never reports a negative it did not verify.

    `_git` RAISES RATHER THAN RETURNING A CODE, AND THAT IS THE FIX FOR A LIVE
    DEFECT RATHER THAN A STYLE PREFERENCE. It used to return `tuple[int, str]`,
    which makes *ignore the failure signal* a WELL-TYPED EXPRESSION: the middle
    read here was `rc, dirty = _git("status", "--porcelain")` and never looked at
    `rc` again. Once `run_bounded` began rendering a hang as `returncode=124,
    stdout=""`, an unread `git status` became indistinguishable from a clean
    worktree, and this function — whose only production caller is `run_claude`'s
    `code != 0` path, WITHOUT a `branch` argument, so the banner is exactly two
    facts — printed "Uncommitted changes: none" for a worktree nothing had read.
    Half a banner, fabricated, on the one path whose documented cost of being
    wrong is a duplicate full-budget dispatch.

    No linter saw it: `rc` is rebound and read eleven lines down, so it is not an
    unused variable. Raising is what makes the ignoring unwritable — dropping the
    failure now costs an `except … : pass`, which is loud, greppable, and already
    banned by `engineering-quality.md`.

    THE RAISE IS CAUGHT PER FACT, NOT AROUND THE BODY, so a read that fails costs
    ONLY ITS OWN LINE. Aborting the whole observation would discard the HEAD this
    function had already successfully read, and reporting what it CAN determine
    is the entire point.
    """
    class _Unreadable(RuntimeError):
        """git did not answer this question. Never means "the answer is no"."""

    def _git(*args: str) -> str:
        r = run_bounded(["git", *args], cwd=worktree)
        if r.returncode != 0:
            raise _Unreadable(" ".join(args))
        return r.stdout.strip()

    if not worktree.exists():
        return f"Worktree {worktree} no longer exists — cannot determine what landed."

    lines: list[str] = []
    try:
        head = _git("log", "-1", "--format=%h %s")
    except _Unreadable:
        return f"Could not read git state in {worktree}. Inspect it by hand before re-running."
    lines.append(f"HEAD in worktree: {head}")

    try:
        dirty = _git("status", "--porcelain")
    except _Unreadable:
        lines.append("Uncommitted changes: COULD NOT BE READ — do not assume none.")
    else:
        lines.append(f"Uncommitted changes: {'YES — ' + str(len(dirty.splitlines())) + ' file(s)' if dirty else 'none'}")

    if branch:
        try:
            unpushed = _git("log", f"origin/{branch}..HEAD", "--oneline")
        except _Unreadable:
            lines.append(f"Could not compare against origin/{branch} — do not assume either way.")
        else:
            lines.append(
                f"Commits NOT yet on origin/{branch}: {len(unpushed.splitlines()) if unpushed else 0}"
                + (f"\n  {unpushed}" if unpushed else "")
            )

    lines.append(f"Worktree retained at: {worktree}")
    return "\n".join(lines)


def anchor_task_source(repo_root: Path, arg: str) -> Path:
    """THE ANCHORING RULE ITSELF, and the only statement of it.

    Absolute in, absolute out. Relative in, resolved against the REPO ROOT — never
    against `Path.cwd()`, which is the whole defect. Split out from
    `resolve_task_source` because `run_plan_revision._read_task_file` needs the
    anchoring and NOT the diagnostic: it distinguishes "not found" from "not
    readable" as V1 did, and `test_plan_revision.py` pins both messages. Without
    this split that runner would have to restate the rule, which is the one thing
    a rule with six consumers must not permit.

    PURE — no filesystem access beyond `Path.resolve()`'s symlink walk, no
    existence check. What to do about a path that does not exist is the caller's
    to decide, and the two callers decide differently.
    """
    supplied = Path(arg)
    return (supplied if supplied.is_absolute() else repo_root / supplied).resolve()


def resolve_task_source(repo_root: Path, arg: str, label: str) -> Path:
    """A free-form operator FILE argument, anchored to the REPO and never to cwd.

    THE DEFECT, measured 2026-08-19. `run_build.py --phase docs/development/.../
    phase2_family_alignment.md --repo <path>`, dispatched from
    `scripts/workflows/temporal/`, died with a bare `[Errno 2] No such file or
    directory: 'docs/development/.../phase2_family_alignment.md'`. Every reader of
    a `--task-file` or `--phase` in this fleet was `Path(arg).read_text()`, which
    is relative to whatever directory the operator happened to be standing in, so
    a repo-relative argument worked only from the repo root. An absolute path
    worked; the operator had to know that, and the message did not say it.

    THIS IS ISSUE #48 ONE LAYER DOWN. That one was the REPO ROOT falling back to
    `Path.cwd()`, and `resolve_repo_root`'s docstring is the ruling: in this fleet
    the invocation directory is never a meaningful base, because a dispatch names
    its target with `--repo` and the operator's shell is incidental. The same
    reasoning reaches the task-source arguments, and nothing had applied it.

    WHAT THIS DELIBERATELY DOES NOT DO, because a spec already rules on it.
    `preflight.RepoPathParser` and two guard modules all state that `--task-file`
    and `--phase` *"are read from wherever the operator points them, on purpose"*
    and are declared with plain `add_argument` for that reason. **That ruling is
    untouched: nothing here refuses a path outside the repo.** An absolute path is
    used exactly as given, and a relative one that climbs out (`../notes.md`) is
    resolved and read without complaint. What changes is only the BASE for a
    relative argument — repo root rather than cwd — which is the one thing the
    operator cannot control from a dispatch line.

    THE COST, STATED. An operator standing outside the repo who means
    `--task-file notes.md` relative to THEIR cwd now gets `<repo>/notes.md`. That
    is a real behaviour change and it is why the failure message below prints the
    base, the raw argument and the resolved path together: the one case this makes
    worse must be self-diagnosing in a single line. Absolute paths — which is what
    `terminal-output.md` tells operators to write, and what every dispatch in the
    guide uses — are unaffected.

    `label` NAMES THE FLAG THE OPERATOR TYPED, not the dest. `--phase` and
    `--task-file` share this function and an error naming `plan_path` sends the
    reader to the source rather than to their own command line.
    """
    resolved = anchor_task_source(repo_root, arg)
    if not resolved.is_file():
        raise RuntimeError(
            f"{label} {arg} names no file: {resolved}\n"
            f"A RELATIVE {label} is resolved against the repo root "
            f"({repo_root}), never against the directory you invoked from — so a "
            f"repo-relative path works from anywhere. If you meant a path relative "
            f"to your shell's current directory, pass it absolute."
        )
    return resolved


def task_context(repo_root: Path, arg: str | None,
                 label: str = "--task-file") -> str:
    """The text of an OPTIONAL task-file argument, or "" when none was given.

    Five runners spelled this `Path(a.task_file).read_text() if a.task_file else ""`
    — the conditional and the read, once each. Both halves are now here so the
    anchoring above cannot be applied to four of them and forgotten in the fifth,
    which is the shape `RepoPathParser`'s docstring calls "a check a runner must
    remember".
    """
    return resolve_task_source(repo_root, arg, label).read_text() if arg else ""


def load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"prompt file missing: {path}")
    return path.read_text()


def shared_prompt(name: str) -> str:
    """Load a promoted, module-level prompt fragment by stem."""
    return load_prompt(_SHARED_PROMPTS / f"{name}.md")


def render(template: str, values: dict[str, str], *,
           opaque: frozenset[str] = frozenset()) -> str:
    """Substitute ${NAME} placeholders and fail loud on any left over.

    Deliberately not str.format/f-strings: these prompts carry JSON, yaml and
    shell, all full of literal braces. An unsubstituted placeholder reaches the
    model as an instruction about a variable, so it raises rather than ships.

    `opaque` names keys whose VALUE IS OPERATOR CONTENT rather than a prompt
    fragment. Those are inserted last, in one pass, and never re-scanned.
    """
    # PASS 1 — fragments only, substituted TO A FIXED POINT. A prompt fragment
    # can itself contain placeholders (a stages file carries ${PR_NUMBER}), so a
    # single pass leaves them unresolved whenever the block is inserted after
    # its own placeholders were processed. Bash had no such problem: it expanded
    # the whole string at once. Iterate until stable, bounded so a
    # self-referential fragment fails loudly rather than spinning.
    fragments = {k: v for k, v in values.items() if k not in opaque}
    out = template
    for _ in range(10):
        before = out
        for k, v in fragments.items():
            out = out.replace("${" + k + "}", str(v))
        if out == before:
            break
    else:
        raise ValueError("prompt substitution did not converge — check for a self-referential fragment")

    # THE GUARD RUNS BEFORE OPERATOR CONTENT GOES IN, and that ordering is the
    # whole point. [A-Z_0-9] — DIGITS MATTER: an earlier [A-Z_]+ silently missed
    # ${STAGES_1_TO_4}, so a prompt shipped with its entire stage body replaced
    # by a literal placeholder and this check raised nothing.
    # An opaque key is legitimately still present here — pass 2 fills it — so
    # exclude those and only those. Everything else must already be resolved.
    still_expected = {"${" + k + "}" for k in opaque}
    leftover = sorted(set(re.findall(r"\$\{[A-Z_][A-Z_0-9]*\}", out)) - still_expected)
    if leftover:
        raise ValueError(f"unsubstituted prompt placeholders: {leftover}")

    # PASS 2 — operator content, ONE pass, never re-scanned and never checked.
    #
    # WHY THIS IS SEPARATE. A task file is prose a human wrote, and prose about
    # this system routinely contains a literal ${LIKE_THIS} token — describing
    # the placeholder bug, quoting a prompt, explaining the guard. Scanned with
    # everything else, that token either gets SUBSTITUTED into the model's task
    # statement (silently changing what was asked) or trips the leftover check
    # and kills the dispatch. Both happened: two runs died the same afternoon,
    # both on briefs that were *describing* this exact mechanism, and there was
    # no way to escape a token.
    #
    # Inserting last and not re-scanning means operator text is passed through
    # LITERALLY, which is the only correct behaviour for content the system did
    # not author.
    for k in opaque:
        if k in values:
            out = out.replace("${" + k + "}", str(values[k]))
    return out

# Re-exported under the name this module already published, so no caller moved.
extract_pr_url = routing.extract_pr_url


def claude_log_path(repo_root: Path, model_key: str, *, run_id: str) -> Path:
    """RESERVE a fresh log path for one invocation. Unique by construction.

    THE LOG IS THE CHANNEL, and that is not obvious from the transport ruling.
    `structured_output` rides in the CLI's own stdout, so the CHILD writes
    nothing outside its worktree — but `run-claude.sh` redirects that stdout
    into $LOG_FILE, so a path exists and the PARENT owns it. "The transport has
    no staleness class" is a claim about the transport; the fleet's channel is
    transport plus plumbing (`phase3_typed_exit_record.md` step 3).

    FRESHNESS IS ENFORCED, NOT ASSUMED. `build_workflow` invokes `review-pr`
    twice in one run, either side of the loop-back. If one path were reused, a
    second child that died before writing would leave pass 1's record in place
    and the parent would route on a pass that produced nothing — making the
    absent-record arm unreachable in exactly the scenario it exists for.

    IT WAS ENFORCED ONE LEVEL ABOVE WHERE IT WAS CLAIMED, AND THAT IS THIS
    FUNCTION'S OWN DEFECT CLASS. For one pass this checked `exists()` and
    returned, RESERVING NOTHING: the file is created later, by a DIFFERENT
    PROCESS, at `run-claude.sh`'s `> "$LOG_FILE"` — `O_TRUNC`. The name was
    `{model_key}-{second-granular stamp}`, and `MODEL_KEY` is a constant shared
    by every PR that workflow reviews, while `run_review_pr` sets
    `worktree = repo_root` and `build_workflow` passes `repo_root` — so the log
    directory is SHARED ACROSS CONCURRENT DISPATCHES, not per-worktree. Two
    dispatches entering in the same wall-clock second both saw no file, both
    proceeded, and one truncated the other's log. R5's identity check stops the
    foreign record deciding a merge, so the observable outcome was a COMPLETED
    run binned as `record_absent` — indistinguishable from a mid-stream death in
    the very per-reason rate this phase exists to produce. Corrupted in the
    direction that looks normal.

    TWO INDEPENDENT FIXES, BOTH DELIBERATE:

    1. **The name carries the run nonce, so it is unique BY CONSTRUCTION.** Not
       a wider timestamp — a finer clock only shrinks the window that a
       check-then-create leaves open. `run_id` is the identity the parent
       already issues and the child already echoes into the record, so the log's
       filename now greps against the record inside it; truncating the nonce
       would break exactly that.
    2. **The name is RESERVED atomically** (`O_CREAT|O_EXCL` via
       `touch(exist_ok=False)`), because check-then-create across a process
       boundary is TOCTOU by construction whatever the name looks like. This is
       what makes the docstring's promise true rather than probable: on the
       residual collision the allocation FAILS LOUD instead of silently
       truncating. The reserved file is empty, which every reader here already
       handles — `_log_events` yields nothing from it and R2 fires.

    The `FileExistsError` is an `OSError`, which `run_review_pr` catches as an
    operator-facing runtime state rather than a traceback.
    """
    log_dir = repo_root / ".claude" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = log_dir / f"{model_key}-{stamp}-{run_id}.jsonl"
    try:
        path.touch(exist_ok=False)
    except FileExistsError as exc:
        raise FileExistsError(
            f"refusing to reuse an existing run log: {path}. A second invocation "
            f"landing on one path either truncates the first run's record or leaves "
            f"a stale one for this run's parent to read. The name carries this "
            f"run's nonce, so reaching this means the nonce was reused."
        ) from exc
    return path


def _log_events(log_file: Path) -> Iterator[dict]:
    """Decoded JSONL events from a run log, in order. Missing log yields nothing.

    ONE DECLARATION OF "how a run log is read", because the invariant is not
    obvious and both readers below depend on it: the stream interleaves non-JSON
    on stderr paths, so a routing read must SKIP a malformed line rather than
    raise. Losing the record to a stray warning would route a clean run to a
    human for a reason that has nothing to do with the run.
    """
    if not log_file.exists():
        return
    for line in log_file.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def result_event(log_file: Path) -> dict | None:
    """The CLI's `result` event from a run log, or None if the log has none.

    None is a REAL answer, not an error: a run killed before it emitted one has
    no result event, and the fail-safe contract's R2 fires on it — `record_absent`,
    because no event implies no key.
    """
    found = None
    for event in _log_events(log_file):
        if event.get("type") == "result":
            found = event          # last wins; there is one, but do not assume it
    return found


def assistant_text(log_file: Path) -> str:
    """This run's own assistant text blocks, in order, newline-joined.

    THIS IS WHERE THE MODEL'S PROSE LIVES WHEN A SCHEMA IS DECLARED. Measured on
    CLI 2.1.224: `--json-schema` replaces `.result` with the serialised
    structured output, so a prose shadow read from `.result` would find nothing
    on every conforming run and report a disagreement that is an artifact of
    where it looked. `run-claude.sh`'s completion gate reads the same surface,
    for the same reason.

    NESTED TURNS ARE EXCLUDED, AND THAT IS WIDER THAN "SUB-AGENT TURNS". Events
    produced under any tool invocation carry a `parent_tool_use_id`; the
    top-level model's carry null. This docstring used to say the field marks a
    sub-agent, which is not what it marks — measured 2026-08-11 on an archived
    build-draft log, every `parent_tool_use_id` resolved to a **`Bash`** tool_use
    (backgrounded commands), not to a sub-agent spawn. The exclusion is
    unaffected because it is conservative in the safe direction: a nested turn is
    never this run's verdict, whoever produced it. The claim was fixed rather
    than the code, because the code was right and the sentence was not.
    """
    chunks: list[str] = []
    for event in _log_events(log_file):
        if event.get("type") != "assistant":
            continue
        if event.get("parent_tool_use_id") is not None:
            continue
        for block in (event.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                chunks.append(block.get("text", ""))
    return "\n".join(chunks)


def append_parent_route(log_file: Path, event: dict) -> None:
    """Append the PARENT-COMPUTED stratum to the run log, as one JSONL event.

    WITHOUT THIS THE COMPUTED ABSTENTION ARM HAS NO RATE.
    `phase3_typed_exit_record.md` step 4 specifies both arms as predicates over
    a run's events — the asserted arm reads `structured_output.hold_kind`, which
    the child writes, and the computed arm reads `routed_outcome` grouped by
    `undetermined_reason`, which NOTHING wrote. `exit-protocol.md` §2.3's two
    parent-computed fields lived only in a return value that dies with the
    process and in free-text operator notes, so the arm the protocol calls the
    reliable one was the one Phase 4 could not count.

    The log is the natural home: it already carries the child's stratum, so both
    predicates evaluate over one artifact rather than two. `type` is namespaced
    away from the CLI's own event types so a future CLI cannot collide with it,
    and appending keeps the CLI's own stream byte-identical.

    WHAT THIS WRITES IS FROZEN WHILE PHASE 4 IS GATED ON IT.
    `phase4_fleet_migration.md` reads the run set these events produce, so the
    keys and the `parent_route` type string are not a refactoring surface, and
    `test_exit_record.py` asserts the line this function writes byte for byte.
    That clause is LOCAL — it is about Phase 4 reading this specific event.

    THE RULE FOR ADDING A FOURTH OBSERVABLE IS NOT HERE ANY MORE, AND THAT IS THE
    POINT. This docstring used to carry it — "a later phase adding its OWN
    observable adds its OWN event type beside this one" — and `append_run_resources`
    then cited it as "`append_parent_route`'s OWN RULE", which is a surface's
    governing rule being quoted out of a neighbour's docstring. It now lives
    where the surface is declared: `scripts/helpers/measure/run_log.py` for the
    member set and the publish classification a check can read, and the
    `memory-model.md` amendment drafted as candidate 10 of the Memory Management
    Framework roadmap for the prose, which is the operator's to ratify.
    """
    _append_run_event(log_file, "parent_route", event)


def append_run_resources(log_file: Path, event: dict) -> None:
    """Append this run's MEASURED resource facts, as its own JSONL event.

    ITS OWN TYPE, BESIDE THE OTHERS, PER THE RUN LOG'S GROWTH RULE — declared in
    `scripts/helpers/measure/run_log.py` and stated in prose by the
    `memory-model.md` amendment drafted as candidate 10. Nothing here widens an
    existing payload and no existing key changes meaning. *(That rule used to be
    cited out of `append_parent_route`'s docstring, which is how a convention
    becomes unfindable.)*

    WHAT IT IS FOR. The open question is whether a run's footprint is governed by
    the NUMBER of subagents or the VOLUME each pulls into context — opposite
    fixes, and `peak_anon` alone cannot separate them. Recording both beside it
    turns that from an argument into a regression over enough runs. An
    `unmeasured` run is written too, with its reason: "no data" and "data showing
    nothing" are different facts and collapsing them hides the gap.
    """
    _append_run_event(log_file, "run_resources", event)


def append_convergence(log_file: Path, event: dict) -> None:
    """Append Phase 5's COMPUTED CONVERGENCE observable, as its own JSONL event.

    A SEPARATE EVENT TYPE, NOT A WIDER `parent_route`. Phase 4 is gated on the
    run set `append_parent_route` produces, so the cheapest way to guarantee
    this addition disturbs nothing is for it to share no payload with that one.
    The two join on `run_id`, which both carry — and which is the run log's
    declared join key (`scripts/helpers/measure/run_log.JOIN_KEY`).

    WITHOUT THIS THE PREDICATE HAS NO DENOMINATOR. The convergence assessment
    lives in a return value that dies with the process; the archive's
    `pr_review:` blocks carry the model's ASSERTED flag but nothing carries the
    computed one, so an agreement rate between the two could only ever be
    reconstructed by a second offline reader — the duplicated-parser defect this
    component exists to remove. That is the same gap
    `phase3_typed_exit_record.md` step 4 closed for the computed abstention arm,
    and it is closed here at the same time as the signal is first emitted rather
    than a phase later.
    """
    _append_run_event(log_file, "convergence", event)


def _append_run_event(log_file: Path, event_type: str, event: dict) -> None:
    """One appender for every parent-written run-log event.

    The two public callers above differ only in their `type`, and typing the
    open-append-serialise sequence twice is how the second one acquires a
    different encoding or a missing newline.

    `type` IS RESERVED, AND IT IS ENFORCED RATHER THAN ASSERTED IN PROSE. This
    docstring previously claimed *"`type` is written FIRST and from the
    parameter, so a caller cannot shadow it through `event`"* — which is the
    opposite of what a dict display does: `{"type": a, **event}` applies `event`
    LAST, so `event["type"]` wins. The claimed protection was inverted, and
    nothing compared the claim to the line under it.

    It is not a hypothetical. `append_convergence`'s payload is built by
    splatting `ConvergenceAssessment.as_event()`, which is DERIVED FROM
    `dataclasses.fields` precisely so that adding a field is enough to make it
    durable — so a future field named `type` reaches here with no human in the
    loop, silently re-types the event, and every reader filtering
    `type == "convergence"` stops seeing it. The denominator this component
    exists to create would disappear with no test going red. Raising is
    preferable to reordering: a caller that hands in a `type` has a bug either
    way, and silently overriding its key is the same class of defect one layer
    down.
    """
    if "type" in event:
        raise ValueError(
            f"a run-log event may not carry its own `type` key: {event['type']!r} "
            f"was handed in for an event this appender types {event_type!r}. The "
            f"event type is the run log's only index; a payload that can set it "
            f"can make itself unreadable to every consumer that filters on it."
        )
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": event_type, **event}) + "\n")


def run_claude(prompt: str, *, model_key: str, workflow_key: str,
               completion_pattern: str,
               repo_root: Path, worktree: Path | None = None,
               max_turns: int = 120, verbose: bool = False,
               exit_record_schema: str | None = None,
               log_file: Path | None = None, run_id: str | None = None) -> str:
    """Invoke the model via the existing bash activity.

    Delegates rather than reimplementing model invocation, logging and the
    completion-contract check — one implementation of the contract, not two
    that can disagree mid-migration.

    `workflow_key` IS REQUIRED AND HAS NO DEFAULT, which is deliberate and is the
    shape `convergence.assess`'s `pass_evaluable` already uses: a new call site
    cannot acquire the hole by forgetting the argument. It is NOT `model_key` —
    `config.yaml` states above `research-write:` that the two are not 1:1, since
    `research-write` and `research-verify` share the model key `research`. Only
    this value lets a per-workflow figure name its own bins; a reader keying off
    `model_key` merges those two and cannot say which records it merged.

    THE LOG'S NAME STILL CARRIES THE MODEL KEY, not this one. Every archived log
    and both filename parsers (`replay_completion_predicate.workflow_of`,
    `run_log.model_key_of`) read that shape, and changing it to fix a payload gap
    would move a published figure to add a field.

    `run_id` IS OPTIONAL; A `log_file` WITHOUT ONE RAISES. The asymmetry is the
    contract and it is stated this way round deliberately — this used to read
    "hand in both or neither", which promised an enforcement of the mirror case
    that does not exist and is not wanted: a caller supplying only `run_id` gets
    a path built FROM that nonce, so the filename and the record agree by
    construction and there is nothing to reject. The claim was corrected rather
    than the code, because the code was right and the sentence was not.
    The run log's join key has
    to carry the SAME VALUE in all three of its member events, and it did not:
    this function used to stamp the resource report with `log_file.stem`
    (`{model_key}-{stamp}-{nonce}`) while `parent_route` and `convergence` carry
    the bare `uuid4().hex` the caller issued. The nonce is a suffix of the stem,
    so the three members joined only by suffix-matching a filename — the
    addressing-by-inference `memory-model.md` §6.1 calls a LOCATION rather than
    an ADDRESS, and a reader written against the field name alone got an empty
    join that read as a corpus with no overlaps. Refusing the half-supplied case
    is what makes the value correct by construction rather than by discipline.

    TWO LOCATIONS, TWO JOBS. `repo_root` is where LOGS live and MUST be the real
    repository — never a worktree, or the log is deleted with the worktree it sat
    inside and cost accounting for that leg becomes impossible. `worktree` is
    where the model EXECUTES. An earlier version passed the worktree as
    repo_root, which buried every V2 log and reproduced a defect already reported
    against review-pr.

    CONTRACT ORDER MATTERS. `run-claude.sh` asserts LOG_FILE, MAX_TURNS,
    VERBOSE, FORMATTER and MODEL_KEY with `: "${VAR:?...}"` at SOURCE time, so
    every one must be exported BEFORE the source line. An earlier version
    sourced first and assigned after, which tripped the guard at source time and
    exited 127 — the delegation did not satisfy the contract it delegated to.
    """
    runner = _WORKFLOWS / "activities" / "run-claude.sh"
    formatter = _WORKFLOWS / "common" / "format-stream.sh"
    for required in (runner, formatter):
        if not required.exists():
            raise FileNotFoundError(f"required activity not found: {required}")

    if ".claude/worktrees" in str(repo_root):
        raise ValueError(
            f"repo_root must be the REPOSITORY, not a worktree: {repo_root}. "
            f"Logs written inside a worktree are deleted with it."
        )
    cwd = worktree or repo_root
    # A caller that needs to READ the record allocates the path itself, so it
    # knows where to read it from AND can bind the log's name to the nonce it
    # issued. A caller that does not still gets a name unique by construction —
    # the nonce is generated here rather than defaulted away, because a default
    # is how the shared-name collision got written in the first place.
    #
    # THE HALF-SUPPLIED CASE RAISES rather than falling back, because the
    # fallback is what wrote the wrong join key. A caller that allocated the path
    # KNOWS the nonce — it had to, to build the name — so being unable to supply
    # it means the path came from somewhere else, and stamping the report with a
    # nonce this function invented would attribute one run's resources to
    # another's identity.
    if log_file is not None and run_id is None:
        raise ValueError(
            f"run_claude was given a log_file ({log_file.name}) with no run_id. "
            f"The run log's three member events must agree on `run_id`, and a "
            f"caller that allocated the log path already holds the nonce that "
            f"named it. Pass both, or neither."
        )
    if log_file is None:
        run_id = run_id or uuid.uuid4().hex
        log_file = claude_log_path(repo_root, model_key, run_id=run_id)

    env = {
        **os.environ,
        "LOG_FILE": str(log_file),
        "MAX_TURNS": str(max_turns),
        "VERBOSE": "true" if verbose else "false",
        "FORMATTER": str(formatter),
        "MODEL_KEY": model_key,
        "COMPLETION_PATTERN": completion_pattern,
        # NO BYTECODE CACHE, AND THIS IS A CORRECTNESS CONTROL RATHER THAN A
        # TUNING KNOB. Every build and plan prompt mandates a mutate-restore
        # loop: change a guard, run the tests, restore the file, run again. A
        # `cp` restore can land inside the mtime resolution `.pyc` validation
        # keys on, so the interpreter reuses the MUTATED bytecode against
        # restored source. Observed 2026-08-14: a test failed showing mutated
        # behaviour against a file `diff` proved unchanged, costing a debugging
        # cycle, and one control reported `2 failed` against a prediction of 1.
        # A restored tree can lie in BOTH directions — a mutation that appears
        # to hit, and one that appears to miss.
        #
        # WHY HERE AND NOT IN A PROMPT. A prompt line asking the model to clear
        # the cache before every control is an administrative control: re-read
        # on every turn, dependent on the model remembering, and billed against
        # a shared fragment already at its byte budget. This eliminates the
        # failure class instead. `__pycache__/` and `*.pyc` are gitignored, so a
        # fresh `git worktree add` starts with ZERO cached bytecode — never
        # writing one therefore means never reading a stale one, for the whole
        # life of a dispatch. Measured: 183.04s vs a 189.53s cached baseline
        # over 3,152 tests, so it costs nothing.
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    # SET **OR CLEARED**, never merely set. `env` starts from `os.environ`, so
    # an ambient `EXIT_RECORD_SCHEMA` — exported by an operator, or inherited by
    # a dispatch launched from inside a schema-declaring run — would reach the
    # child even when this caller declared none. That hands `--json-schema` to
    # the FROZEN V1 fleet (`exit-protocol.md` §7), whose whole guarantee is that
    # its command line is byte-identical when the variable is unset, and flips
    # its completion gate onto the assistant-text branch, where V1's
    # `COMPLETION_PATTERN` (a PR URL) does not appear — turning successful V1
    # runs into false early-stop failures. "Unset" has to be something this
    # caller controls, not something the environment gets a vote on.
    if exit_record_schema:
        env["EXIT_RECORD_SCHEMA"] = exit_record_schema
    else:
        env.pop("EXIT_RECORD_SCHEMA", None)
    # STREAM AND CAPTURE. `capture_output=True` produced a 70-minute run with
    # zero visible output, so --verbose did nothing and an operator could not
    # distinguish a working run from a hung one — the reported symptom was
    # "it's not working" when it was. Popen lets output be watched live AND
    # collected for the completion-contract check.
    print(f"→ {model_key}  log: {log_file}", flush=True)
    print(f"→ {model_key}  exec: {cwd}  (max_turns={max_turns})", flush=True)
    # MEASURED, or explicitly not. The scope is what makes the kernel account
    # for this child separately from the session; it BOUNDS NOTHING — every cap
    # was reverted at `6725111` and `resource_limits` holds one lowercase key,
    # so `wrap()` emits no `-p` at all. This comment used to say the scope
    # "stops one child taking the host down with it", which asserted an
    # enforcement that does not exist; the 2026-08-10 outage's cause is still
    # UNIDENTIFIED and its attribution to a sub-agent fan-out is retracted.
    # When a scope cannot be created the child still runs and the report records
    # WHY it was not measured — a run nobody could measure has to remain
    # countable, or the gap stops being visible.
    argv = ["bash", "-c", f'source "{runner}"; run_claude "$1"', "_", prompt]
    limits = _resource_limits()
    scoped, scope_reason = resource_telemetry.scope_available()
    if scoped:
        scope_unit = f"claude-{model_key}-{uuid.uuid4().hex[:12]}.scope"
        argv = resource_telemetry.wrap(argv, unit=scope_unit, limits=limits)
    else:
        # "UNMEASURED", not "UNBOUNDED". Every path is unbounded — the scoped
        # one applies no ceiling either — so a warning naming a missing BOUND
        # let an operator read the scoped path as bounded. What is actually lost
        # here is the MEASUREMENT, which is the whole reason the scope exists.
        print(f"⚠ {model_key}: running UNMEASURED (no kernel accounting for this "
              f"child; nothing is capped on either path) — {scope_reason}", flush=True)

    proc = subprocess.Popen(
        argv, cwd=str(cwd), env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    sampler = resource_telemetry.measure(proc, unit=scope_unit) if scoped else None
    captured: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        captured.append(line)
        if verbose:
            sys.stdout.write(line)
            sys.stdout.flush()
    code = proc.wait()
    output = "".join(captured)

    # BEFORE the failure branch below, deliberately. A run that died is the one
    # whose resource numbers are most worth having, and an early `raise` would
    # throw them away at exactly the moment they became evidence.
    # `run_id=run_id`, NOT `log_file.stem` — the run log's join key carries one
    # value across all three of its member events, and the stem is a filename
    # that merely ends with it. See this function's docstring.
    report = resource_telemetry.finish(
        sampler, limits=limits, unmeasured_reason=None if scoped else scope_reason,
        run_id=run_id, model_key=model_key, workflow_key=workflow_key)
    report.tool_result_bytes, report.subagents_spawned = resource_telemetry.from_log(log_file)
    append_run_resources(log_file, resource_telemetry.report_dict(report))
    print(f"→ {model_key}  {resource_telemetry.human(report)}", flush=True)

    if code != 0:
        # OBSERVE before reporting. A turn-cap exit may have committed and
        # pushed real work; asserting otherwise costs a duplicate full-budget run.
        raise RuntimeError(
            f"{model_key} FAILED (exit {code}). Log: {log_file}\n"
            f"--- observed git state (read, not assumed) ---\n"
            f"{observe_outcome(cwd)}\n"
            f"--- end observed state ---\n"
            f"{output[-2000:]}"
        )
    return output


# ── THE `gh` RETRY, AND THE TWO GUARDS THAT KEEP IT HONEST ──────────────────
#
# On 2026-08-17 GitHub ran a Partial System Outage and a single
# `gh repo view --json nameWithOwner` in preflight took one
# `HTTP 503: No server is currently available to service your request`. The
# whole dispatch died before doing any work: one blip, one wasted run.
#
# The retry is HERE and not in each caller for the reason `gh_json` below
# already argues about exception families — a caller cannot be expected to know
# which failures this function's implementation can emit, and the next `gh`
# reader re-acquires the gap by writing the obvious two lines. Exactly one
# caller had written them (`review_pr_workflow._read_thread_for_invariant`),
# for one path, after a flaky read nearly discarded a completed review.
#
# THE RISK IS NOT UNDER-RETRYING, IT IS OVER-RETRYING, and both guards below
# exist to fail toward "do not retry". Retrying a deterministic failure turns a
# fast truthful error into a slow one; retrying a MUTATION double-posts, which
# is not hypothetical here — issue #41 records duplicate comments on an issue an
# operator had to rule on.

# A later identical call may get a different answer for these, and only these.
# 403 is deliberately NOT here: it is both "you may not do this" (terminal) and
# "you have exceeded a secondary rate limit" (transient), and the status alone
# cannot separate them. `_RATE_LIMIT_PHRASES` is what rescues the second.
_RETRYABLE_HTTP = frozenset({429, 502, 503, 504})

# Lowercased. Used ONLY to promote a 403; never to promote any other status, so
# a 404 whose prose happens to mention a rate limit stays terminal.
_RATE_LIMIT_PHRASES = ("rate limit", "abuse detection", "too many requests")

# Both shapes `gh` actually emits, MEASURED against the live outage rather than
# assumed: `HTTP 503: No server is currently available…` on the GraphQL path,
# and `gh: Not Found (HTTP 404)` on the REST path.
_HTTP_STATUS = re.compile(r"HTTP (\d{3})")

# `gh`'s grammar is `gh <noun> <verb>`, and these verbs read. Anything absent
# from this set — `create`, `comment`, `merge`, `edit`, `close`, and every verb
# GitHub adds later — is NOT retried. An allowlist rather than a denylist
# because the cost of the two mistakes is not symmetric: a read that fails to
# retry costs one dispatch, a mutation that retries posts twice.
#
# `api` IS ABSENT ON PURPOSE. Its method is a flag (`-X`, `-f`), not a verb, so
# the positional rule below cannot decide it, and nothing in the fleet routes
# `gh api` through here today. Add it with the first caller and with a rule that
# reads the flags — do not assume it is a read because the common case is.
_READ_ONLY_GH_VERBS = frozenset({"view", "list", "checks", "status", "diff"})

# THREE ATTEMPTS, ≤8 SECONDS OF ADDED LATENCY. Two pauses because one retry is a
# coin flip on a blip and four starts disguising an outage as latency — the
# operator's stated concern is runs that will not stop. 2.0s because the 503s
# measured during this outage cleared within seconds; 6.0s rather than the 8.0
# its sibling uses because this sits UNDERNEATH
# `review_pr_workflow._THREAD_READ_BACKOFF_SECONDS`, and the composition on that
# one path is 3×3 = 9 attempts and ~34s of PAUSES.
#
# ~34s IS THE ADDED-LATENCY BOUND AND IT IS NOT THE WALL-CLOCK ONE, which this
# comment said nothing about until `_SUBPROCESS_TIMEOUT_SECONDS` existed. The
# wall-clock bound is `attempts × timeout + pauses`: 3×120 + 8 ≈ 6min here, and
# 9×120 + 34 ≈ 18min composed — because `504 Gateway Timeout` is in the
# retryable set and by definition arrives slowly. An attempt count stopped
# bounding wall-clock the moment each attempt acquired a ceiling; bounding it
# would take a monotonic deadline on the outer loop, which is a change to
# `review_pr_workflow` and not to this tuple. Both figures are asserted in
# `test_the_retry_under_the_review_threads_retry_stays_bounded`.
# Shape matches that sibling deliberately: a tuple of pauses, with the final
# attempt outside the loop and uncaught so the real error surfaces.
_GH_RETRY_BACKOFF_SECONDS = (2.0, 6.0)


def _one_line(text: str, limit: int = 120) -> str:
    """Anything, flattened short enough to belong on a console line.

    `' '.join(args)` is fine in an exception, which is read once. It is not fine
    in a retry notice: `gh pr comment --body-file` aside, several call sites pass
    multi-line prose, and a retry that dumps a PR body into the operator's
    console teaches them to stop reading the retries.

    NAMED FOR WHAT IT DOES, NOT FOR ITS FIRST CALLER. This was `_gh_label(args)`
    and three of its four uses passed `[stderr]` rather than an argv — so the
    name told the next author that arg-aware logic (redacting `--body-file`,
    say) belonged here, and that change would silently have reformatted every
    error string in this module's console output.
    """
    flat = text.replace("\n", " ")
    return flat if len(flat) <= limit else flat[:limit - 3] + "..."


def _gh_transient_reason(stderr: str) -> str | None:
    """Why this `gh` error is worth trying again, or None if it is not.

    KEYED ON THE HTTP STATUS `gh` PRINTS, not on prose. Prose is server-supplied
    English that changes without notice; the status token is the one part of the
    message that means the same thing every time.

    READS STDERR ONLY, WHICH IS A DELIBERATE NARROWING. `gh api` writes the
    response BODY to stdout and its own diagnostic to stderr (measured), so
    classifying on stderr keeps server-controlled content out of the decision.

    EVERY STATUS FOUND MUST BE RETRYABLE, NOT MERELY ONE OF THEM. A message
    carrying both a 404 and — for any reason, including a quoted body — a 503 is
    treated as terminal. The asymmetry is the point: the failure mode of being
    wrong here is a run that will not stop.

    NO STATUS AT ALL IS TERMINAL. That is correct for the cases it was measured
    against (`unknown flag: --not-a-flag`, and GraphQL's
    `Could not resolve to a PullRequest`, which is a 404 wearing no status) and
    it is the fail-safe direction for everything else. See this module's tests
    for what that costs — a transport error and a GraphQL-layer 5xx both present
    with no status and are both left un-retried.
    """
    codes = {int(c) for c in _HTTP_STATUS.findall(stderr)}
    if not codes:
        return None
    lowered = stderr.lower()
    rate_limited = any(p in lowered for p in _RATE_LIMIT_PHRASES)
    for code in sorted(codes):
        if code in _RETRYABLE_HTTP:
            continue
        if code == 403 and rate_limited:
            continue
        return None
    if rate_limited:
        return f"HTTP {sorted(codes)[0]}, throttled"
    return f"HTTP {sorted(codes)[0]}, server-side"


def _gh_is_read_only(args: list[str]) -> bool:
    """Whether re-running this invocation is free of consequence.

    A 502 on a MUTATION may mean the mutation landed and only the reply was
    lost. Nothing in the reply can distinguish that from a mutation that never
    ran, so the only safe answer for a write is: do not retry, raise, and let a
    human or a caller with more context decide.

    POSITIONAL, AND IT DOES NOT PARSE FLAGS — it takes the second non-flag token
    as the verb. That is imprecise, and every direction the imprecision runs is
    toward NOT retrying: a global flag placed before the noun shifts the window
    so the noun lands in the verb slot and matches nothing, and a flag VALUE that
    happens to spell a read verb still sits behind its own noun. A full parse
    would need to track which flags take values, i.e. a model of `gh`'s CLI that
    goes stale silently.

    WHAT IT DOES NOT LOOK AT: whether the SERVER considers the call a write. A
    read verb pointed at an endpoint with side effects — none exist in this
    fleet — would be retried on its say-so.
    """
    verbs = [a for a in args if not a.startswith("-")]
    return len(verbs) >= 2 and verbs[1] in _READ_ONLY_GH_VERBS


def _gh_timed_out_line(label: str, spent: int, attempts: int,
                       args: list[str]) -> str:
    """A TIMEOUT IS A THIRD FACT, AND IT MUST NOT WEAR EITHER REFUSAL'S LINE.

    It is not `TERMINAL` in the sense the first refusal means — that one says
    *the request is wrong and GitHub told us so*, which points at us. It is not
    the write refusal either — that one says *GitHub is unwell and we stopped
    anyway because a repeat may double-apply*. A hang says GitHub is unwell AND
    told us nothing at all.

    NOT RETRIED, FOR READS AS WELL AS WRITES. Both guards in this module default
    to "do not retry" and so does this one, but state the bound honestly rather
    than better than it is:

      * with a timeout TERMINAL, a wedged endpoint costs 1 attempt here and 3
        under `_THREAD_READ_BACKOFF_SECONDS` — 3×120s ≈ 6min;
      * were it another transient class, the same path would be 9×120s + 34s
        ≈ 18min.

    AND ~18min IS ALREADY REACHABLE WITHOUT IT, which is the part a confident
    sentence would have hidden. `504 Gateway Timeout` is in the retryable set
    and by definition arrives slowly, so nine attempts that each answer 504 just
    under the ceiling compose to the same ~18min. What the terminal
    classification buys is therefore the EXPECTED case, not the bound: a wedged
    endpoint stays wedged, so the all-hangs path is the likely one, and paying
    6min for it rather than 18 is the whole trade. Bounding the worst case would
    need a monotonic DEADLINE on the outer loop rather than an attempt count,
    because attempt counts stopped bounding wall-clock the moment each attempt
    acquired a ceiling.
    """
    line = (f"→ gh {label}: attempt {spent}/{attempts} gave NO ANSWER within "
            f"{_SUBPROCESS_TIMEOUT_SECONDS:.0f}s — TIMED OUT (not retried): a "
            f"hung call names no server condition a repeat would satisfy, and "
            f"repeating it would move this path's wedged-endpoint cost from "
            f"~6min to ~18min")
    if not _gh_is_read_only(args):
        # The one thing `run_bounded`'s generic message cannot say, because only
        # here is the invocation known to be a mutation. A killed `gh pr comment`
        # may have been applied server-side, and "it was not retried" does not
        # answer the operator's actual question.
        line += (" — AND THIS IS NOT A READ: the write may have been applied "
                 "server-side before the kill, so verify before re-running")
    return line


def gh_attempt(args: list[str],
               repo_root: Path | None) -> subprocess.CompletedProcess:
    """`gh`, retried past transient server-side failures, returned UNJUDGED.

    THIS FUNCTION NEVER RAISES ON A NON-ZERO EXIT, and that is the whole reason
    it exists beside `gh` rather than inside it. Two callers need the retries
    without the raise: `gh issue list` in `plan_activities` degrades to a "COULD
    NOT BE READ" note, and `ci_verdict` below classifies by
    PARSING because `gh pr checks` exits non-zero whenever checks are failing or
    pending. Folding the raise in here would break both, so
    `test_gh_attempt_RETURNS_a_failure_rather_than_raising_it` pins it.

    `repo_root` IS OPTIONAL, AND THE REASON THIS SENTENCE ONCE GAVE IS NO LONGER
    TRUE. It used to read "`ci_verdict` addresses the PR with an explicit
    `--repo` and must keep using the process cwd" — but PR #128 removed that
    `--repo`, precisely because our own flag of that name carries a filesystem
    path, and both CI reads derive the repo from the cwd like everything else.
    `None` now means only "this caller has no tree to anchor to", which in the
    live fleet is no caller at all.

    THE SENTENCE THAT FOLLOWED THIS ONE WAS THE SAME FALSE CLAIM THE CI GATE
    SHIPPED, IN A SECOND PLACE. It said the `None` input "proves an unanchored
    read degrades to `this repo declares no gate` rather than silently passing"
    — but degrading to "this repo declares no gate" IS silently passing:
    `routing.ci_gate` answers `NO_CHECKS` with a SKIPPED note and `hold=None`,
    which every parent reads as PROCEED. Two files described that fail-open as
    the fail-safe, which is why a review pass reading either one moved on.
    `repo_root` is REQUIRED on both CI reads as of 2026-08-20, so no test hands
    them a `None` tree to demonstrate a degrade; the one that hands them `None`
    demonstrates that the call is REFUSED. See `ci_verdict` below.

    A RETRY IS VISIBLE OR IT NEVER HAPPENED. Every attempt past the first prints
    what failed, how it was classified, and how long the pause is; a run that
    eventually succeeded prints which attempt did it. Silent retries are how
    nobody ever learns whether the answer to "is it GitHub or us?" is on record.
    """
    label = _one_line(" ".join(args))
    attempts = len(_GH_RETRY_BACKOFF_SECONDS) + 1
    spent = 0

    def _run() -> subprocess.CompletedProcess:
        # ONE definition of the invocation, called from two places. The "final
        # attempt outside the loop" property below is about CONTROL FLOW, not
        # about the text of this line — and two copies of it drift the moment
        # someone changes the budget on one of them. That drift is not
        # hypothetical: this comment used to name `timeout=` as the example, and
        # `run_bounded` is where the timeout landed.
        return run_bounded(["gh", *args], cwd=repo_root)

    for pause in _GH_RETRY_BACKOFF_SECONDS:
        r = _run()
        spent += 1
        if is_timed_out(r):
            print(_gh_timed_out_line(label, spent, attempts, args), flush=True)
            return r
        if r.returncode == 0:
            if spent > 1:
                print(f"✓ gh {label}: succeeded on attempt {spent}/{attempts}",
                      flush=True)
            return r
        reason = _gh_transient_reason(r.stderr)
        # NOT SILENT, because "it did not retry" is the half of this an operator
        # cannot infer from the absence of a line — a run that never retried and
        # a run whose retry code is broken look identical in a log that only
        # speaks when it retries.
        #
        # AND THE TWO REFUSALS SAY DIFFERENT THINGS, because they are different
        # facts and the operator's question is "is it GitHub or us?". A
        # deterministic failure is about the request; a transient failure refused
        # on a write is about GitHub, and the run stopped anyway because a repeat
        # might double-apply. One label for both answers the question wrongly
        # half the time.
        if reason is None:
            print(f"→ gh {label}: attempt {spent}/{attempts} failed, TERMINAL "
                  f"(not retried) — {_one_line(r.stderr.strip())}", flush=True)
            return r
        if not _gh_is_read_only(args):
            print(f"→ gh {label}: attempt {spent}/{attempts} failed, TRANSIENT "
                  f"({reason}) but NOT A READ — not retried, because repeating "
                  f"it may apply the write twice — "
                  f"{_one_line(r.stderr.strip())}", flush=True)
            return r
        print(f"⚠ gh {label}: attempt {spent}/{attempts} failed, TRANSIENT "
              f"({reason}) — retrying in {pause}s", flush=True)
        time.sleep(pause)

    # The last attempt is deliberately OUTSIDE the loop, so a persistent failure
    # returns the real `gh` reply rather than one classified and swallowed.
    r = _run()
    spent += 1
    if is_timed_out(r):
        # ONE definition of the line, for the same reason `_run` has one
        # definition of the invocation. This was written twice and the two
        # copies had already diverged before anyone ran them: the ✗ line below
        # would otherwise report "FAILED after 3 attempts" for a run whose last
        # attempt never got an answer at all.
        print(_gh_timed_out_line(label, spent, attempts, args), flush=True)
    elif r.returncode == 0:
        # GATED THE SAME WAY ITS TWIN IN THE LOOP IS, and it was not. With
        # `_GH_RETRY_BACKOFF_SECONDS = ()` — the one-character way to turn
        # retries off — the loop never runs, every `gh` call in the fleet lands
        # here with `spent == 1`, and every successful read printed a ✓ line.
        # The kill switch for this feature also flooded the console.
        if spent > 1:
            print(f"✓ gh {label}: succeeded on attempt {spent}/{attempts}",
                  flush=True)
    else:
        print(f"✗ gh {label}: FAILED after {spent}/{attempts} attempts — "
              f"{_one_line(r.stderr.strip())}", flush=True)
    return r


def gh(args: list[str], repo_root: Path) -> str:
    """Run `gh` INSIDE the target repo rather than passing --repo.

    `--repo` in our CLIs is a FILESYSTEM PATH; `gh --repo` wants an OWNER/NAME
    slug. Conflating them is how an earlier version passed None to gh and let it
    derive the repo from the process cwd — which is exactly what the flag's own
    documentation promises never happens. Setting cwd keeps the identity
    explicit without needing to parse a remote URL into a slug.

    Non-zero is a `RuntimeError` as it always was; what changed is that a
    transient server-side failure on a read no longer reaches that raise on its
    first occurrence.

    THE ATTEMPT COUNT IS NOT IN THIS MESSAGE, AND THAT IS DELIBERATE. Only
    `gh_attempt` knows it — deriving it here from the final stderr gets it wrong
    for the mixed case (a 503 that becomes a 404 on the next attempt), and a
    figure that is right most of the time is the kind a reader stops checking.
    It prints the count on the line immediately above this raise instead.
    """
    r = gh_attempt(args, repo_root)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed in {repo_root}: {r.stderr.strip()}")
    return r.stdout


# Both shapes `gh --json` can legitimately answer with, and nothing else — a
# scalar or a null is a reply `gh` cannot have sent. Named so a caller that
# genuinely accepts either says which "either" it means, rather than leaning on
# a default nobody chose.
GH_JSON_SHAPES = (dict, list)


def gh_json(args: list[str], repo_root: Path, *,
            expect: type | tuple[type, ...]):
    """`gh` plus its parse, so a `gh` FAILURE IS ONE EXCEPTION TYPE.

    ONE FAILURE SURFACE, BECAUSE CALLERS GUARD AGAINST A TYPE AND NOT AN EVENT.
    `gh` above raises `RuntimeError` on a non-zero exit and validates nothing
    about stdout, so every caller that then ran `json.loads` had a SECOND way to
    fail — `json.JSONDecodeError`, which is a `ValueError` and shares no base
    class with the first. That is not a hypothetical distinction: the retry in
    `review_pr_workflow._read_thread_for_invariant` exists precisely so a flaky
    `gh` read cannot discard a completed review, it catches `RuntimeError`, and a
    zero-exit reply with a truncated or non-JSON body therefore skipped the retry
    entirely — zero attempts — and crashed the parent build loop, which catches
    `(RuntimeError, FileNotFoundError)` and not `ValueError`. The fix belongs
    HERE rather than in each caller's except-clause: a caller cannot be expected
    to know which exception families this function's implementation can emit, and
    the next `gh` reader would have re-acquired the same gap by writing the
    obvious two lines.

    The raw body is quoted (truncated) into the message, because "expecting value
    at line 1 column 1" says nothing about whether the answer was an HTML error
    page, an empty string or a half-written array.

    A DECODE FAILURE IS NOT RETRYABLE HERE, AND THIS FUNCTION ADDS ZERO
    ATTEMPTS. `gh` exited 0: the transport succeeded and the server named no
    condition a later identical call would satisfy. Nothing available at this
    point distinguishes a truncated body from a server that answered fully and
    wrongly, and "retry until it parses" is precisely the loop that turns a
    deterministic wrong answer into a slow one.

    THE SEPARATION IS THE WHOLE REASON THE RETRY LIVES BELOW THIS LINE. The
    paragraph above exists because a 503 and a zero-exit-unparseable-body were
    once conflated by callers; normalising them to one exception TYPE is what
    callers need, and it is exactly what a retry must not be built on. Retrying
    `RuntimeError` here would re-run the terminal failures `gh_attempt`
    deliberately refused — every 404, every bad flag — because by the time the
    exception exists the cause has been erased. So the classification happens in
    `gh_attempt`, where the exit code and the stderr are still separate facts,
    and this function is a pure parse over whatever survived that.

    If a truncated body is ever MEASURED rather than inferred, it earns its own
    named classification with its own evidence — not a quiet membership in the
    transient set.

    "ZERO ATTEMPTS" IS TRUE AT THIS LAYER AND FALSE ONE LAYER UP, which is worth
    saying rather than leaving a reader to trust the sentence further than it
    goes. `review_pr_workflow._read_thread_for_invariant` catches bare
    `RuntimeError` around `thread_snapshot`, which reaches this function — so on
    that ONE path a decode failure is retried up to three times after all. That
    is a consequence of the normalisation described above, not an accident: the
    exception type is deliberately the same, so a caller that retries the type
    retries both members of it. It is left as it is because that caller's
    alternative is discarding a ~40-minute review, and it is BOUNDED — pinned,
    with the composed count, by
    `test_a_decode_failure_IS_retried_by_the_one_caller_that_retries_the_TYPE`.
    """
    raw = gh(args, repo_root)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"gh {' '.join(args)} in {repo_root} exited 0 but did not return JSON: "
            f"{exc}. First 200 bytes of the reply: {raw[:200]!r}"
        ) from exc
    # PARSING IS NOT THE SAME AS ANSWERING, which is the half this function used
    # to leave to its callers. `{"message": "Not Found"}` and `[]` and `"x"` all
    # decode without complaint, and the caller then does `.get("comments")` or
    # `i["number"]` and dies of `AttributeError` or `TypeError` — two more
    # exception families, in the one function whose entire purpose is that
    # callers guard against ONE type.
    #
    # `expect` IS REQUIRED RATHER THAN DEFAULTED, and that is the whole design.
    # A permissive `(dict, list)` default would have been dead by policy — every
    # production caller here reads by key or by index, so every one of them has
    # an answer — and enforcing "state your shape" is then either an AST census
    # over the tree (which was written, and which missed any caller outside its
    # roots) or the signature, which the interpreter enforces for free at every
    # call site there will ever be. Use `GH_JSON_SHAPES` to say "either" out loud.
    if not isinstance(parsed, expect):
        wanted = expect if isinstance(expect, tuple) else (expect,)
        raise RuntimeError(
            f"gh {' '.join(args)} in {repo_root} exited 0 and returned valid JSON "
            f"of the wrong shape: expected {' or '.join(t.__name__ for t in wanted)}, "
            f"got {type(parsed).__name__}. First 200 bytes: {raw[:200]!r}"
        )
    return parsed


def repo_slug(repo_root: Path) -> str:
    """This dispatch's target repository as `owner/name`.

    THE IDENTITY HALF OF THE PR-URL CONTRACT. `--repo` in our CLIs is a
    FILESYSTEM PATH and `gh` is run with `cwd` set to it, so the slug is never
    stated anywhere a parent can compare against — which is why a `completion_ref`
    naming a different repository was, until Phase 4, indistinguishable from a
    correct one. `gh` resolves it from the checkout's own remote, so the answer
    is the repository the dispatch is actually operating in rather than one
    inferred from a task description.

    Raises through `gh` on failure rather than returning None: a parent that
    cannot name its own repository cannot check that a child stayed inside it,
    and the fail-safe direction for an unanswerable identity question is loud.
    """
    return gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
              repo_root).strip()


def default_branch(repo_root: Path) -> str:
    """The target repo's default branch, ASKED rather than assumed to be `main`.

    This fleet is meant to run against other repositories, and a hardcoded
    "main" is wrong in every repo that never renamed from `master` or that
    develops on `trunk`. `gh` answers from the remote, which is the same
    authority `repo_slug` and `pr_branch` use.
    """
    return gh(["repo", "view", "--json", "defaultBranchRef",
               "-q", ".defaultBranchRef.name"], repo_root).strip()


def base_ref(pr_number: str | None, repo_root: Path) -> str:
    """WHERE A RUN'S WORKTREE IS CUT FROM: the PR's branch, or the default branch.

    THE OPERATOR'S CHECKOUT POSITION IS NOT AN INPUT TO THIS, and that is the
    whole point. Every runner used to compute this inline as

        ref = f"origin/{pr_branch(...)}" if pr_number else "HEAD"

    and `HEAD` is whatever branch the operator's clone happens to be sitting on.
    When that was an open PR's branch, the new run branched FROM that PR and its
    own PR silently carried the other one's commits — a PR whose diff is not the
    change it claims, and whose review then judges work that belongs to someone
    else.

    MEASURED 2026-08-20: three of eight open PRs had it. #132 and #127 were both
    cut while the checkout sat on #126's branch; #127 carried two of #126's
    commits, in a version #126's own review had already superseded. Nothing
    warned, and nothing could — the runners did exactly what they were told.

    The rule is the operator's, stated plainly: a run either CONTINUES the same
    PR (`--pr`) or STARTS FROM THE DEFAULT BRANCH. There is no third base.

    `origin/` ON BOTH ARMS, deliberately. A local branch can be stale, and the
    point of a known base is that it is current; `worktree_add` fetches any
    `origin/`-prefixed ref and treats a failed fetch as fatal, so the remote form
    is the one that cannot quietly resolve to yesterday's tree.

    ONE HELPER AND NOT ELEVEN EXPRESSIONS. The inline form reached eleven call
    sites, which is why fixing it in ten of them would have been the likeliest
    outcome of doing this by hand — and is exactly what the first pass did. The
    eleventh (`research_refresh_parent`) passes its base INLINE rather than
    through a `ref = ...` line, so both the hand sweep and the first version of
    the guard written to replace it looked straight past it. `test_a_new_branch_STARTS_FROM_THE_DEFAULT_BRANCH`
    keys on the class rather than on today's ten.
    """
    if pr_number:
        return f"origin/{pr_branch(pr_number, repo_root)}"
    return f"origin/{default_branch(repo_root)}"


def pr_branch(pr_number: str, repo_root: Path) -> str:
    return gh(["pr", "view", pr_number, "--json", "headRefName",
               "-q", ".headRefName"], repo_root).strip()


# ---------------------------------------------------------------------------
# CI READS — promoted out of the BUILD family per §10.1 rule 3.
#
# These lived in `build/build_activities.py`, so a plan or research parent could
# not read a CI verdict without importing the build family. Four of them
# therefore dispatched `review-pr` with the verdict never read. The `gh`
# plumbing they call (`gh_attempt`, `run_bounded`) has always been here, so this
# is the module they were reaching INTO — the promotion removes the inversion
# rather than creating a new dependency.
#
# The PURE half — `CiVerdict`, `POLICY_PATH` and the `ci_gate` cascade — went to
# `routing`, which is where the fleet's other pure routing decisions live.
# ---------------------------------------------------------------------------

# How long CI is given to settle before a review reads its result. The bash
# activity polled the GitHub API; this preserves the behaviour and the boundary.
CI_POLL_SECONDS = 20
CI_MAX_WAIT_SECONDS = 600




def read_check_policy(repo_root: Path) -> tuple[list[str], list[str], bool]:
    """Read the repo's own declaration of which checks gate it.

    Returns (blocking, advisory, readable). `readable` is False ONLY when the
    file exists and cannot be parsed — which is a DIFFERENT FACT from the file
    being absent, and collapsing the two is how the skip path becomes the new
    exit. A repo may legitimately have no gate; a repo whose declaration is
    broken has not said so.
    """
    path = repo_root / routing.POLICY_PATH
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


def ci_verdict(pr: str, *, repo_root: Path) -> tuple[routing.CiVerdict, list[str]]:
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

    `repo_root` IS REQUIRED, AND THAT REQUIREMENT IS WHAT MAKES THE VERDICT MEAN
    ANYTHING. It carried `= None` until 2026-08-20, and the None path skipped
    `read_check_policy` ENTIRELY: `blocking` stayed empty, so a tree whose only
    check was FAILURE returned NO_CHECKS — and `routing.ci_gate` answers
    NO_CHECKS by appending a SKIPPED note and returning `hold=None`, which every
    parent reads as PROCEED. Driven and measured on PR #124:
    `ci_verdict("1", repo_root=None)` over `[{"name": "suite", "state":
    "FAILURE"}]` returned NO_CHECKS and the gate raised no hold. A red tree
    reached `review-pr`. The merge gate this fleet spent three passes wiring into
    six parents was fail-OPEN through its own front door.

    THE PROPERTY, STATED SO IT CAN BE GUARDED: no path through this function
    returns a NON-HOLDING verdict without having actually read a check policy.
    A required parameter is what establishes it — the skip branch is not
    *handled*, it does not EXIST, so a future caller cannot re-enter the hole by
    forgetting a keyword and no reviewer has to reason about a fourth case.
    `test_ci_gate.py::test_a_NON_HOLDING_gate_is_unreachable_without_a_policy_READ`
    is the guard; its sibling pins the signature so the default cannot be quietly
    restored.

    NOTHING ABOUT NO_CHECKS MOVED. A repo that genuinely declares no gate still
    proceeds, and that is a ruled decision (`routing.CiVerdict`, 2026-08-13) that
    remains correct. What changed is that reaching NO_CHECKS now requires having
    LOOKED — a policy never read is not a policy that does not exist.
    """
    blocking, advisory, readable = read_check_policy(repo_root)
    if not readable:
        return routing.CiVerdict.UNREADABLE_POLICY, []

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
    # `run_bounded`, because a CEILING is not a RETRY and its deadline
    # loop cannot enforce one on a call that has not returned.
    #
    # `repo_root` FOR THE TREE, AND THIS IS THE ADDRESS, NOT A PREFERENCE.
    # `--repo` is not in `cmd` — the block above says so — so the ONLY thing
    # deciding which repository `gh` reads is the subprocess cwd. Passing `None`
    # there means "the directory the operator happened to be in", and
    # `preflight.resolve_repo_root` exists precisely because that is not the
    # tree we are gating: nothing in this fleet chdirs, and a `--repo` dispatch
    # is the supported mode in which the two differ.
    #
    # BOTH DIRECTIONS ARE LIVE FAILURES, and one of them is this gate's own
    # defect class reopened one layer down. If the cwd repo happens to have a PR
    # numbered the same and it is green, the gate returns GREEN FOR A DIFFERENT
    # REPOSITORY'S PR, `ci_gate` returns no hold, and MERGE becomes reachable on
    # a red tree. If the cwd repo has no such PR, every read fails for the full
    # deadline and a clean PR takes UNREADABLE_CHECKS — which is the 2026-08-19
    # incident recorded fifteen lines above, recurring with a different cause.
    # That comment ends "the gate was right; the address was wrong"; the address
    # was still wrong until this line passed the tree.
    #
    # Nothing about the non-zero path moves. `gh pr checks` exits non-zero on
    # failing or pending checks with no HTTP status in stderr, so the classifier
    # calls that TERMINAL and spends exactly one attempt, and `gh_attempt`
    # returns the reply unjudged — which is why parsing, below, is still the
    # discriminator.
    result = gh_attempt(cmd, repo_root)

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
        return routing.CiVerdict.UNREADABLE_CHECKS, []

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
            return routing.CiVerdict.GATE_DID_NOT_RUN, sorted(blocking)
        return routing.CiVerdict.NO_CHECKS, undeclared

    failed = [str(c["name"]) for c in gating
              if str(c.get("state", "")).upper() not in {"SUCCESS", "SKIPPED", "NEUTRAL"}]
    return (routing.CiVerdict.RED, failed) if failed else (routing.CiVerdict.GREEN, undeclared)


# A check has SETTLED only in one of these. Everything else — IN_PROGRESS,
# QUEUED, WAITING, REQUESTED, or anything GitHub adds later — means keep
# waiting. Naming the terminal set rather than the pending one is what stops
# a new state silently reading as done.
_TERMINAL_CHECK_STATES = frozenset({
    "SUCCESS", "FAILURE", "SKIPPED", "NEUTRAL",
    "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STALE", "ERROR",
})


def wait_for_ci(pr: str, *, repo_root: Path) -> bool:
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
    IT RETURNS ON ALL THREE — this function NEVER raises a CI OUTCOME, and that
    qualifier is load-bearing rather than hedging. `repo_root` became REQUIRED
    and typed `Path` on 2026-08-20; hand it `None` anyway and the policy read
    below dies on `None / POLICY_PATH` before the deadline even starts. That is
    a call-shape error and not a fourth state — the distinction is argued under
    `repo_root` at the foot of this docstring, and
    `test_ci_gate.py::test_neither_CI_READ_can_be_called_without_a_tree` drives
    that exact call on both reads.

    THE QUALIFIER IS SAID HERE, BESIDE THE TABLE, BECAUSE IT USED TO BE SAID
    ONLY THIRTY LINES BELOW IT. A caller reads a contract table and stops; this
    block's own history two paragraphs down is what that costs. The table is
    unchanged and still lists no raise, which is what
    `test_docstrings_do_not_promise_a_raise.py` checks — and that guard sees
    only the table, never this prose, which is why the prose has to be right on
    its own:

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

    `repo_root` IS REQUIRED, for the reason `ci_verdict` states at length and for
    a smaller stake of its own. This returns a settled bool rather than the gate
    verdict, so an unanchored poll cannot by itself put MERGE within reach — but
    it reads no policy, so it stops waiting for a gate it does not know to
    expect, and it can burn the whole 600-second deadline against a tree nobody
    chose. The two CI reads take the same parameter under the same rule because a
    gate whose halves disagree about whether the tree is optional is a gate with a
    seam in it. The three outcomes above are CI outcomes; handing this something
    that is not a tree is a call-shape error rather than one of them.
    """
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
        # `cwd=repo_root` IS THE ADDRESS. Same reason as `ci_verdict`'s read
        # above, and these two were the only unanchored `gh` launches in the
        # fleet: `--repo` is not in `cmd`, so cwd is the only thing choosing the
        # repository, and `None` chooses the operator's shell. A poll loop
        # pointed at the wrong repo does not fail fast — it burns the whole
        # 600-second deadline first.
        result = run_bounded(cmd, cwd=repo_root)

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
