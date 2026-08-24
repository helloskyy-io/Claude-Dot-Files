"""Who names a run, and how the name reaches the process that records it.

PHASE 9 OF THE PERSISTENT MEMORY PROTOCOL, and this module is the answer to its
first two requirements. Phase 1 built the folder a run writes into and keyed it
by a run id. It did not say who NAMES a run, because at the time there was only
one shape a run could take: a parent, started from a terminal, minting its own
name on the way in. Two decisions ended that — the Temporal port makes an
entrypoint a client that starts a workflow, and Workflow Decomposition Phase 3
gives nine children runners of their own — so an invocation that is not a
parent, and may or may not be a run, can now begin.

  `mint_run_id`         — the fleet's ONE naming authority (in the journal package)
  `add_identity_arguments` — the two CLI inputs, defined once for all entrypoints
  `resolve_identity`    — the dispatch boundary: validate, or mint and announce

WHY A NAME MINTED INSIDE THE WORK IS THE DEFECT AND NOT A DETAIL. The reliability
pool under `docs/development/temporal-integration/` surveyed six systems that
name a unit of work — Temporal, GitHub Actions, GitLab, systemd, message queues
and the IETF `Idempotency-Key` draft — and found NONE that mints the name inside
the work. Under an at-least-once orchestrator a name minted inside a retried step
is a new name on every attempt, and under a deterministic replay it is a
different name on the second pass; either way one run acquires an unbounded fan
of names and the journal files it as several runs. Generation belongs on the
INPUT side, and moving it costs one parameter.

  The corroboration is local and not hypothetical: re-enumerating this repo's
  archived run logs once returned files named for scripts that no longer exist,
  because two naming authorities were live at the same time.

THE TWO INPUTS, AND WHY THERE ARE TWO RATHER THAN ONE.

  `--run-id <id>`   the name of the run this invocation belongs to.
  `--writer <name>` present ⇔ this invocation is PART of that run, not the run.

One input cannot carry both facts. An orchestrator supplies `--run-id` for a
PARENT too — a parent under Temporal is handed its name like everything else —
so the presence of a run id says nothing about whether the invocation IS the run.
The four combinations resolve as:

  --run-id X --writer w   a MEMBER of run X. Adopts X's bag, takes a subfolder.
  --run-id X              IS run X. Its own bag. (A retry supplies the same X.)
  --writer w              REFUSED. A writer with no run to join is the exact
                          "child silently becomes its own run" failure this
                          requirement exists to prevent — silently opening its
                          own bag, or silently writing nowhere, are both wrong
                          and neither should be reachable by omission.
  (neither)               IS the run, and nothing named it yet. See below.

⚠ NEVER INFERRED FROM THE ENVIRONMENT — NOT FROM AN ENV VAR, NOT FROM THE
WORKING DIRECTORY, NOT FROM THE ABSENCE OF ONE. A child can be started by a
parent, by a person, or by a person reproducing what a parent did, and those
three are INDISTINGUISHABLE from inside the process. Only a value passed in
distinguishes them. An env var reads like a passed value and is not one: it is
inherited by every descendant, so a parent that exports it hands its own name to
a grandchild that should have had its own, and a person who exported it once in a
shell hands it to every unrelated run in that terminal afterwards.

WHERE A CALLER GETS THE NAME WHEN THERE IS NO ORCHESTRATOR YET — the question
Phase 9's checklist asks to be written down rather than left to each caller.

  TODAY: nobody supplies it, and `resolve_identity` mints one HERE, at the dispatch
  boundary, and PRINTS it. That last part is the half that matters: a run whose
  name was minted and never announced cannot be retried into its own bag,
  because the operator has no way to name it. The line names the flag to pass
  back.

  ONCE THERE IS AN ORCHESTRATOR: the orchestrator supplies it, as `--run-id`,
  and this function validates rather than mints. Nothing else changes — which is
  the point of putting the name on the input side before the port arrives.

  WHY MINTING HERE IS NOT THE DEFECT THIS MODULE EXISTS TO FIX. The property
  Phase 9 r2 protects is that the name is stable across retries and replays of
  the WORK. This module is not the work — it is the CLIENT side of the dispatch,
  it runs once per invocation before any workflow code, and at port time it
  becomes the Temporal client that starts the workflow. A client is not retried;
  an activity is. Minting on the client side IS "generation on the input side",
  which is what the survey above concluded. What r2 forbids is `run_*.py` making
  a name for itself, and `tests/unit/test_the_run_id_ARRIVES_from_outside.py`
  holds exactly that: no entrypoint may so much as name `mint_run_id`.

  ⚠ r2 STAYS UNCHECKED IN THE PHASE DOC ANYWAY, and that is deliberate rather
  than an oversight to be tidied. Built is not proven: the mechanism is built and
  demonstrated against a local retry here, and the requirement does not close
  until the Temporal port's side of the name exists — whether its workflow id can
  BE the run id, or has to be joined to a second name. That is the port's ruling
  to make with this module's three properties as inputs: a name supplied by the
  caller, stable across the whole run, and mapped onto whatever the orchestrator
  already calls a dispatch.

WHY THIS LIVES IN `scripts/` AND NOT IN `modules/journal/`. The journal package
is DEPENDENCY-FREE ON THE WORKFLOW TREE and does I/O that has to be recorded and
retried; this module parses argv. It is a launch concern, exactly like
`preflight.py` beside it, and `preflight` is the precedent: a helper the
entrypoints share so the CLI contract is defined in one place rather than eleven.
The naming authority itself stays in the journal package, because the run id is
the bag's key and the package that owns the key owns the alphabet it is drawn
from.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from modules.journal.bag import BagError, validated_run_id
from modules.journal.journal_activities import mint_run_id

__all__ = ["RunIdentity", "add_identity_arguments", "resolve_identity"]


@dataclass(frozen=True)
class RunIdentity:
    """One invocation's answer to *which run am I, and am I the whole of it?*

    `minted` is carried rather than derived because the two cases are operator-
    facing and differ: a supplied name is one the caller can reproduce, and a
    minted one is a name that exists nowhere until this process says it out loud.
    """

    run_id: str
    writer: str | None

    #: True when nothing supplied the name and this boundary made one.
    minted: bool

    @property
    def is_the_run(self) -> bool:
        """This invocation IS the run, rather than a member of one."""
        return self.writer is None


def add_identity_arguments(parser: argparse.ArgumentParser) -> None:
    """The two identity inputs, defined ONCE for every entrypoint.

    Defined here rather than in each `run_*.py` for the reason `preflight` is
    shared: eleven copies of a CLI contract agree until one is edited, and this
    fleet is about to gain nine more entrypoints from Workflow Decomposition
    Phase 3. `test_the_run_id_ARRIVES_from_outside.py` asserts that every
    discovered entrypoint routes through this function rather than declaring its
    own `--run-id`, so a tenth spelling of the same flag cannot appear quietly.
    """
    parser.add_argument(
        "--run-id", dest="run_id", default=None,
        help="name of the run this invocation belongs to. Supplied by the "
             "orchestrator, or by a parent dispatching this child, or by you to "
             "retry into an existing bag. Minted and announced if omitted. "
             "Permitted characters: A-Z a-z 0-9 . _ -")
    parser.add_argument(
        "--writer", dest="writer", default=None,
        help="this invocation is PART of the run named by --run-id, not the run "
             "itself: its records go to a writer subfolder of that run's bag "
             "under this name. Omit when this invocation IS the run. Requires "
             "--run-id.")


def resolve_identity(argv: list[str] | None = None, *, announce: bool = True) -> RunIdentity:
    """Turn the two identity inputs into this invocation's identity.

    TAKES `argv`, NOT THE ENTRYPOINT'S PARSED NAMESPACE, and the reason is
    uniformity rather than convenience. The eleven entrypoints do not agree on
    what a parse produces — four return a typed workflow input, one returns a
    `(task, dry_run)` pair, one returns a bare `Namespace`, the rest keep it
    local to `main` — and threading a namespace through each would mean four
    signature changes in files whose return types the suite asserts against.
    Re-reading two flags costs nothing and gives every entrypoint, including the
    nine Workflow Decomposition Phase 3 is about to add, the identical two lines.

    THIS IS NOT A SECOND DECLARATION OF THE FLAGS. The throwaway parser below is
    built by `add_identity_arguments` — the same function every entrypoint's real
    parser calls — so there is one statement of what the flags are and two
    readers of it. The entrypoint's own parser is what rejects a typo and what
    prints the help; this only reads values it has already accepted.

    Raises `BagError` (a `RuntimeError`) on a name outside the permitted set or
    on a `--writer` with no run to join, so every entrypoint's existing
    precondition handler prints it and the run does not start. That is Phase 1
    r9's shape applied to identity: a run whose name is unusable must fail before
    it creates anything, not after.

    ⚠ CALL THIS AFTER THE `--dry-run` EARLY RETURN, NEVER BEFORE. A dry run
    states "nothing invoked, nothing posted"; minting a name and announcing it
    would make that false, and it is the same exemption that keeps a dry run from
    opening a bag. `announce=False` is for callers that legitimately need an
    identity without printing one — the test suite, and nothing else today.
    """
    reader = argparse.ArgumentParser(add_help=False)
    add_identity_arguments(reader)
    args, _ = reader.parse_known_args(argv)

    supplied = args.run_id
    writer = args.writer

    if writer is not None and not writer.strip():
        raise BagError(
            "--writer was given an empty name. It is the discriminator between "
            "'this invocation IS the run' and 'this invocation is part of one', "
            "so an empty value is a caller bug rather than an empty selection — "
            "omit the flag to say this invocation is the run.")

    if writer is not None and supplied is None:
        raise BagError(
            f"--writer {writer!r} was given with no --run-id. A writer subfolder "
            f"belongs to a run's bag, and there is no run named here to put it "
            f"in.\n"
            f"  failing property: this invocation claims to be PART of a run "
            f"while naming no run.\n"
            f"  remedy: pass --run-id <id> as well to join that run, or drop "
            f"--writer to state that this invocation IS the run and gets its own "
            f"bag. Guessing between those two is how a child silently becomes "
            f"its own run, which is why neither is a default.")

    if supplied is not None:
        # VALIDATED HERE TOO, not only inside `open_bag`, because this boundary
        # is where an unusable name is CHEAPEST to refuse — before preflight,
        # before a worktree, before anything exists to strand. `open_bag`'s own
        # call is not redundant: it is the guard for every other caller of the
        # journal package, and a boundary check is not a substitute for one at
        # the thing being guarded.
        return RunIdentity(run_id=validated_run_id(supplied), writer=writer,
                           minted=False)

    run_id = mint_run_id()
    if announce:
        # STDERR, AND UNCONDITIONALLY. A name nobody was told is a bag nobody can
        # retry into, and this is the only moment the name exists and nothing has
        # recorded it. stderr rather than stdout because several entrypoints'
        # stdout is a rendered report an operator or a tool reads.
        print(f"journal: run id {run_id} (minted here — pass "
              f"`--run-id {run_id}` to retry this run into the same bag)",
              file=sys.stderr, flush=True)
    return RunIdentity(run_id=run_id, writer=None, minted=True)
