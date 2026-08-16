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
literally true before the first side effect. Six of this fleet's eleven
entrypoints call `act.worktree_add` themselves and hand the workflow module an
already-cut worktree, so a bag opened inside the workflow module would fire after
a worktree existed on disk in more than half the fleet. The entrypoint is where
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
    """The identity of ONE dispatch, minted once, at the top.

    NOT the per-child `run_id` the run log mints inside `run_claude` — that one is
    per model invocation, so a parent and its three children carry four different
    values and no single one addresses the run. A bag is one run's folder, so its
    key is minted where the run begins and nowhere else.

    Threading this value down to the children is Phase 3's job, because that is
    the phase that emits. Phase 1 opens the folder.
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
    """
    path = CONFIG_PATH if config_path is None else config_path
    if not path.is_file():
        return {}
    import yaml  # a hard preflight dependency; see scripts/preflight.py
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _git(repo_root: Path, *args: str) -> str:
    """One-line `git` output, or `""` when git cannot answer.

    THE EMPTY STRING IS A LEGITIMATE ABSENCE, NOT A SWALLOWED ERROR, and it is
    named at both call sites below: a repo with no `origin` remote genuinely has
    no remote URL, and a fresh repo with no commits genuinely has no HEAD. Those
    are facts about the repo worth recording as `-`, not failures worth stopping
    a run over — the journal root's properties are what r9 refuses on, and this
    is metadata.
    """
    probe = subprocess.run(["git", *args], cwd=str(repo_root),
                           capture_output=True, text=True)
    return probe.stdout.strip() if probe.returncode == 0 else ""


def open_run_bag(*, run_id: str, repo_root: Path, workflow_key: str,
                 worktree_name: str | None = None,
                 config_path: Path | None = None,
                 env: Mapping[str, str] | None = None) -> Bag:
    """Resolve the journal root and open this run's bag. Raises to stop the run.

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
    """
    root = resolve_journal_root(config=load_journal_config(config_path), env=env)

    remote = _git(repo_root, "remote", "get-url", "origin")
    commit = _git(repo_root, "rev-parse", "HEAD")

    return open_bag(root, run_id, info={
        "Journal-Workflow": workflow_key,
        "Journal-Origin-Repo": str(repo_root),
        "Journal-Origin-Remote": remote or "-",
        "Journal-Origin-Commit": commit or "-",
        "Journal-Worktree": worktree_name or "-",
    })
