"""Opening a run's bag — the I/O boundary a run crosses before it does anything.

WHY THIS IS AN ACTIVITY AND NOT A LIBRARY FUNCTION (requirement 11). As a library
each workflow is asked to remember to call, the protocol is optional — and
optional is how three controls in this fleet have already failed: an observable
shipped with no reader, a rule governing three event types stated inside one
function's docstring, and a completion gate one runner had and another did not.
Each was correct as written, each was skippable, and each was skipped. A rule
written in prose has not once prevented a write path being added without its
emit. Temporal Standard §3 puts I/O in the activities layer, so this is where the
journal's I/O belongs; §7.1 requires idempotency, which `open_bag` provides.

⚠ AND AN ACTIVITY BOUNDARY DOES NOT, BY ITSELF, MAKE THE CALL HAPPEN. Nothing in
an orchestrator forces a workflow to invoke a particular activity first; one that
omits the call simply omits it. So "the code lives in the activities layer"
delivers tidiness, not the guarantee. Requirement 9's refuse-to-start cannot
supply it either — r9 fires only once bag-open has ALREADY been invoked, and a
run that never calls it never reaches r9. What delivers it is
`tests/unit/test_every_parent_opens_a_run_bag.py`, the enumerating sweep, built
on the shape `test_every_entrypoint_actually_calls_preflight` already proved out.

WHAT IS BUILDABLE TODAY AND WHAT IS PORT-TIME, stated so neither half is claimed
falsely. Layer placement, invocation as the run's first step, fail-stop on error
and the enumerating test are all here. Orchestrator-driven retry and recorded
execution are properties of a worker that does not exist; the vendored Temporal
Standard places worker configuration and the activity map at port time, and the
port carries that half.

WHY THE CALL SITE IS THE ENTRYPOINT AND NOT THE WORKFLOW MODULE, TODAY. r9 says a
root that cannot be resolved means *the run does not start*, and that is only
literally true before the first side effect. FIVE of this fleet's eleven
entrypoints call `act.worktree_add` themselves and hand the workflow module an
already-cut worktree, and THREE more hand off by name to a `*_workflow` module
that cuts one — so in eight of eleven a bag opened inside the workflow module
would fire after a worktree existed on disk. (This paragraph said "six … more
than half" through three passes; the count is five, the argument survives on
eight of eleven, and `test_the_worktree_cutting_count_this_argument_RESTS_ON` now
pins both numbers so the next reader who counts finds the prose true.)
The entrypoint is where
`preflight` already lives for exactly this reason. At port time the entrypoint
becomes a client that starts the workflow on a task queue, and this call moves to
the workflow's first activity invocation — the sweep's predicate moves with it.
"""

from __future__ import annotations

import subprocess
import uuid
from collections.abc import Mapping
from pathlib import Path

from .bag import Bag, open_bag
from .root import JournalRootError, resolve_journal_root

__all__ = ["mint_run_id", "open_run_bag", "load_journal_config", "JournalRootError"]

# `config.yaml` sits at the repo root of THIS repo — the fleet's own
# configuration, not the target repo's. Resolved from this file's location for
# the same reason `preflight.resolve_repo_root` refuses `Path.cwd()`: the
# invocation directory is not an input to where the fleet's config lives.
_FLEET_ROOT = Path(__file__).resolve().parents[5]
CONFIG_PATH = _FLEET_ROOT / "config.yaml"


def mint_run_id() -> str:
    """THE FLEET'S ONE NAMING AUTHORITY FOR A RUN. Phase 9 r1.

    There is exactly one function in this fleet that names a run and this is it.
    Nothing else — no entrypoint, no workflow module, no child — may generate a
    run id, and `tests/unit/test_the_run_id_ARRIVES_from_outside.py` is what
    holds that rather than this sentence: it fails when a `run_*.py` so much as
    NAMES this function, and it pins the caller set to the single dispatch
    boundary below.

    ⚠ AND THE ENTRYPOINTS NO LONGER CALL IT. Phase 9 r2: a name generated inside
    the work is a fresh name on every retry and a different name on a replayed
    second pass, so the name arrives from OUTSIDE the process — as `--run-id`.
    Its one caller is `scripts/dispatch_identity.resolve_identity`, which is
    the client side of the dispatch and is not replayed code; at port time
    that is the Temporal client, and the call moves with it rather than being
    removed. Read that module's docstring for where a caller gets a name when
    there is no orchestrator, and what supplies it once there is.

    NOT the per-model-invocation nonce `run_claude` mints, WHICH IS NOW SPELLED
    `invocation_id` (Phase 9 r1). A parent and its three children carry four of
    those and none addresses the run; they used to share this one's name, so
    "the run id" resolved to two different things depending on which file you
    were reading. The name `run_id` now belongs to the run, fleet-wide, in every
    Python identifier. **One spelling is deliberately unchanged**: the run log's
    JSONL field and the `run_id:` line in posted `pr_review:` blocks, because
    those are written records — the roadmap's standards-amendment 4 already
    schedules that field's meaning change for Phase 3's cut-over, and renaming
    it here would break the readers of every block already on a PR. It is
    declared once, as `run_log.JOIN_KEY`, rather than restated.

    Threading this value down to the children is Phase 3's job, because that is
    the phase that emits. Phase 1 opens the folder; Phase 9 says who names it.
    """
    return uuid.uuid4().hex


def load_journal_config(config_path: Path | None = None) -> Mapping[str, object]:
    """`config.yaml` as a mapping, or an empty one when the file is absent.

    ABSENT IS NOT AN ERROR HERE AND A MALFORMED FILE IS. A missing `config.yaml`
    means "no override", which resolves to the documented default for the
    deployment shape — that is the designed path, not a degradation. A file that
    exists and does not parse is a different thing entirely: it means the
    operator's intent is unreadable, and defaulting past it would put the journal
    somewhere they did not choose.

    A PARSE FAILURE IS RERAISED AS `JournalRootError`, WHICH IS THE MODULE'S
    DOCUMENTED CONTRACT. `yaml.YAMLError` is not a `RuntimeError`, so letting it
    escape would give all eleven entrypoints a raw traceback for the one class of
    problem r9 exists to diagnose cleanly — a misconfiguration. The refusal names
    the file and the parser's own message, which is what an operator needs when
    the journal that would have recorded the failure is the thing that failed.

    AND SO IS AN UNREADABLE ONE, WHICH IS THE THIRD BRANCH OF THE SAME RULE. The
    two paragraphs above each fixed one way this function could raise a
    non-`RuntimeError` — an unparseable file, then a file that parses to a
    scalar — and the file being unreadable in the first place was left raising a
    bare `PermissionError` from `read_text`. It is reachable exactly where r9 is
    argued hardest: on the systemd shape the service account and the checkout's
    owner can differ, and this is the FIRST call `open_run_bag` makes, so the
    traceback arrives before anything else could report it.

    THE RULE, RATHER THAN A THIRD PATCH: every call on the resolution path raises
    `JournalRootError` or nothing. `test_every_way_the_config_can_fail_is_a_RuntimeError`
    holds the population instead of this docstring, because three consecutive
    fixes to one function is what a missing check looks like.
    """
    path = CONFIG_PATH if config_path is None else config_path
    try:
        if not path.is_file():
            return {}
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise JournalRootError(
            f"config.yaml could not be read: {path}\n"
            f"  failing property: {exc.strerror or exc}\n"
            f"  remedy: make the file readable by the account the fleet runs as, "
            f"or remove it to accept the documented default for this deployment "
            f"shape. Defaulting past a config that exists would put verbatim "
            f"transcripts somewhere the operator did not choose.") from exc
    import yaml  # a hard preflight dependency; see scripts/preflight.py
    try:
        loaded = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise JournalRootError(
            f"config.yaml could not be parsed: {path}\n"
            f"  failing property: not valid YAML — {exc}\n"
            f"  remedy: fix the syntax. The journal root is read from this file, "
            f"and defaulting past an unreadable one would put verbatim "
            f"transcripts somewhere the operator did not choose.") from exc

    # PARSING IS NOT THE SAME AS BEING A CONFIG, and this is the half the
    # `YAMLError` fix above missed. A truncated or garbled file that yields a
    # scalar or a list parses perfectly and is truthy, so it sails past the
    # `or {}` guard and raises `AttributeError` on the first `.get` — which is
    # not a `RuntimeError`, so none of the eleven entrypoint handlers catches it
    # and the operator gets a traceback for exactly the misconfiguration r9
    # exists to report cleanly. Same failure, adjacent branch.
    if not isinstance(loaded, Mapping):
        raise JournalRootError(
            f"config.yaml is not a mapping: {path}\n"
            f"  failing property: parsed as {type(loaded).__name__}, not a "
            f"mapping of top-level keys\n"
            f"  remedy: the file should be `key: value` at the top level. A "
            f"partially-written or truncated config parses cleanly as a scalar "
            f"and would otherwise be read as though it had no `journal:` section "
            f"at all.")
    return loaded


# These probes read purely LOCAL git metadata — a remote URL from `.git/config`,
# a HEAD sha — so 30s is already an order of magnitude past anything healthy.
# Deliberately shorter than the assistant tree's 120s network budget: nothing
# here touches the network, and a bound copied from a call that does would be
# defending a risk this function does not carry.
_PROBE_TIMEOUT_SECONDS = 30.0


def _git(repo_root: Path, *args: str) -> str:
    """One-line `git` output, or `""` when git cannot answer.

    THE EMPTY STRING IS A LEGITIMATE ABSENCE, NOT A SWALLOWED ERROR, and it is
    named at both call sites below: a repo with no `origin` remote genuinely has
    no remote URL, and a fresh repo with no commits genuinely has no HEAD. Those
    are facts about the repo worth recording as `-`, not failures worth stopping
    a run over — the journal root's properties are what r9 refuses on, and this
    is metadata.
    """
    # BOUNDED, AND BOUNDED HERE RATHER THAN VIA `assistant_activities.run_bounded`.
    # This package is the lower layer — nothing under `modules/journal/` imports
    # the assistant tree, and reaching upward for a helper would invert that to
    # save four lines. The ceiling itself is not optional: a `git` that hangs
    # while this probe reads repo METADATA would park a run before it has opened
    # its bag, and the empty-string contract above already says exactly what to
    # do when the probe cannot answer.
    try:
        probe = subprocess.run(["git", *args], cwd=str(repo_root),
                               capture_output=True, text=True,
                               timeout=_PROBE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        # SAID OUT LOUD, because the return value cannot say it. `""` means "no
        # remote" or "no HEAD" in the bag, and a timed-out probe would write the
        # same `-` — the no-data-versus-data-showing-nothing conflation this
        # family refuses everywhere else. The record format is not the place to
        # fix that; the console is, and it costs one line.
        print(f"⚠ journal: `git {' '.join(args)}` did not answer within "
              f"{_PROBE_TIMEOUT_SECONDS:.0f}s in {repo_root} — recording this "
              f"metadata as absent, which is NOT the same as it being absent",
              flush=True)
        return ""
    if probe.returncode != 0:
        # THE SAME LINE FOR THE SAME CONFLATION, AND IT WAS MISSING. The branch
        # above prints because `""` cannot distinguish "no remote" from "the
        # probe failed" — and this branch returned the identical `""` in
        # silence, one line below it. The docstring's "an empty string is a
        # legitimate absence" is true of a repo with no `origin` and false of a
        # git that answered 128, so only the callable case may be quiet.
        print(f"⚠ journal: `git {' '.join(args)}` failed in {repo_root} "
              f"({probe.returncode}): {probe.stderr.strip()[:200]} — recording "
              f"this metadata as absent, which is NOT the same as it being absent",
              flush=True)
        return ""
    return probe.stdout.strip()


def open_run_bag(*, run_id: str, writer: str | None, repo_root: Path,
                 workflow_key: str, worktree_name: str | None,
                 config_path: Path | None = None,
                 env: Mapping[str, str] | None = None) -> Bag:
    """Resolve the journal root and open this run's bag. Raises to stop the run.

    `writer` IS PHASE 9 r4's DISCRIMINATOR, AND IT HAS NO DEFAULT FOR THE REASON
    `worktree_name` HAS NONE. It answers the one question the bag was never
    designed for: is this invocation THE RUN, or is it PART of one?

      * `writer=None` — this invocation IS the run. The bag is its own.
      * `writer="research_verify"` — this invocation is a MEMBER of the run named
        by `run_id`. The bag is adopted and a writer subfolder is allocated
        inside it, so a parent and its three children file ONE bag with one
        subfolder each rather than four bags for one piece of work.

    ⚠ IT IS PASSED, NEVER INFERRED, AND THAT IS THE WHOLE REQUIREMENT. A child
    can be started by a parent, by a person, or by a person reproducing what a
    parent did, and those three are INDISTINGUISHABLE from inside the process —
    same environment, same working directory, same argv but for this. Inferring
    the answer from an environment variable or a cwd is exactly how a child
    silently becomes its own run, which is one of the two wrong answers Phase 9
    § *A standalone child is the case the bag was never designed for* rejects.
    The other wrong answer is "only parents open bags", which leaves a child a
    person started with no record at all. A default here would pick one of them
    for every caller that forgets, so there is no default.

    ⚠ AND A SECOND MEMBER OF ONE RUN CAN RACE THE FIRST. Two children dispatched
    concurrently under one `run_id`, with no parent having opened the bag, both
    reach `open_bag` and one loses the `mkdir`. That is Phase 9 r7, it is
    deliberately not closed here, and `open_bag`'s docstring states what it
    costs. It does not arise when a PARENT opens the bag first — Phase 1 r11
    makes bag-open the parent's first step, so by the time children run the
    directory exists and every one of them adopts.

    `worktree_name` HAS NO DEFAULT, AND THAT IS THE POINT. It was optional, and
    nine of eleven entrypoints omitted it — so nine of eleven runs would have
    written `Journal-Worktree: -` forever, under a phase rule that says a field
    absent from v1 records is absent for good. Eight of those nine had the string
    in hand within five lines of the call. This package's own thesis is that an
    optional control is a skipped control; a keyword with no default applies it
    to the package's own parameter, and the next entrypoint added fails at the
    call rather than writing a placeholder nobody notices. Pass `None`
    explicitly to state that a workflow cuts no worktree — `run_review_pr` is the
    one that genuinely does not.

    THE ORIGINATING REPO IS A FIRST-CLASS FIELD, recorded here rather than left
    to Phase 3. The run log it supersedes is keyed per repo CHECKOUT while the
    journal is one root per EDGE, so without this nothing downstream could
    express "this depends on which repo the run was in" — and a field absent from
    version-1 records is absent forever.

    BOTH THE WORKTREE PATH AND THE REMOTE ARE RECORDED, because they answer
    different questions. `repo_root` under this fleet is usually a worktree, which
    is the run's actual working directory; the remote is the stable project
    identity that every worktree of that project shares.

    RAISES `RuntimeError` (`JournalRootError` or `BagError`), which every
    entrypoint's existing precondition handler already prints. That is r9: the
    run does not start, and the message names the resolved path and the failing
    property so recovery does not itself need a working journal.

    ⚠ AND THAT CONTRACT IS ENFORCED HERE, AT THE BOUNDARY, BECAUSE IT WAS NOT.
    `resolve_journal_root` only wraps the `OSError` from CREATING a missing
    component — which is the first-run case. From the second run onward the root
    already exists, `os.access` answers about permission and not about space, and
    the first call that actually fails on a full disk is `open_bag`'s own `mkdir`
    or tag-file write, raising a bare `OSError`. Ten of the eleven entrypoints
    catch `(RuntimeError, FileNotFoundError[, ValueError])`, so the operator got a
    traceback for precisely the steady-state failure — a full journal — that r9's
    whole argument is built on being diagnosable without a working journal.
    """
    root = resolve_journal_root(config=load_journal_config(config_path), env=env)

    remote = _git(repo_root, "remote", "get-url", "origin")
    commit = _git(repo_root, "rev-parse", "HEAD")

    try:
        return _open(root, run_id, writer, repo_root, workflow_key,
                     worktree_name, remote, commit)
    except OSError as exc:
        raise JournalRootError(
            f"journal root unusable: {root}\n"
            f"  failing property: the bag for run {run_id} could not be written "
            f"— {exc.strerror}"
            f"{f' at {exc.filename}' if getattr(exc, 'filename', None) else ''}\n"
            f"  remedy: free space under the root, or point `journal.root:` in "
            f"config.yaml at a filesystem with room. A full journal stops every "
            f"run including the one you would use to diagnose it, which is why "
            f"this message names the path rather than raising a traceback."
        ) from exc


def _open(root: Path, run_id: str, writer: str | None, repo_root: Path,
          workflow_key: str, worktree_name: str | None, remote: str,
          commit: str) -> Bag:
    """The bag-creating half of `open_run_bag`, split out only so the `OSError`
    boundary above wraps every filesystem call that WRITES the bag rather than
    the subset that happened to be on one line.

    ⚠ IT IS NOT EVERY FILESYSTEM CALL THE ACTIVITY MAKES, AND THIS SENTENCE USED
    TO SAY IT WAS. Two run before it: `load_journal_config`, which now raises
    `JournalRootError` on its own for every way a config can fail to be read; and
    `_git`, which needs no wrapper here for a checked reason rather than an
    assumed one — `preflight.resolve_repo_root` runs the same `subprocess.run(["git",
    …], cwd=repo_root)` shape from the same directory before any entrypoint
    reaches this activity, so a missing `git` binary or an unreachable
    `repo_root` has already been refused there. `_git` cannot be the first to
    discover either.
    """
    bag = open_bag(root, run_id, info={
        "Journal-Workflow": workflow_key,
        "Journal-Origin-Repo": str(repo_root),
        "Journal-Origin-Remote": remote or "-",
        "Journal-Origin-Commit": commit or "-",
        "Journal-Worktree": worktree_name or "-",
    })

    # THE SUBFOLDER IS ALLOCATED HERE AND NOTHING IS WRITTEN INTO IT, which is
    # the phase boundary rather than an omission. Phase 1 and Phase 9 own WHERE a
    # run's record goes; Phase 3 owns WHAT gets written there. Allocating at
    # bag-open is what makes "one run, one bag, one subfolder per writer"
    # observable before any emitter exists — and `writer_dir`'s allocation is by
    # `os.mkdir` winning or losing, so two members asking for the same name get
    # different directories rather than sharing a file.
    #
    # ⚠ A RETRY OF ONE MEMBER GETS A NEW SUBFOLDER (`w`, then `w-2`), because
    # `writer_dir` allocates rather than adopts. That is Phase 1's ruled
    # behaviour and it is left alone: its whole purpose is that no two writers
    # ever share a file, and making it adopt would hand a retry the directory a
    # concurrent sibling is writing into. The cost is a subfolder per attempt,
    # which is visible in the bag rather than silent.
    if writer is not None:
        bag.writer_dir(writer)
    return bag
