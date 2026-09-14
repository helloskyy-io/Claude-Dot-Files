"""The harvest as an ACTIVITY a parent invokes — Phase 10 requirement 7.

THE SAME ARGUMENT PHASE 1 r11 MAKES FOR BAG-OPEN AND PHASE 3 r12 MAKES FOR THE
EMIT, applied to the one write path that has no call site to wrap. As a library
each parent is asked to remember to call after its child exits, the harvest is
optional — and this fleet's own history is that an optional control is a
skipped control. So it is one function with one signature, invoked by every
entrypoint in the `finally` of a `try` around its workflow handoff — on the
return, the raise and the interrupt alike, because THE WINDOW OPENS AT CHILD
EXIT and a child whose parent raised after it posted still wrote to GitHub —
and `tests/unit/test_every_parent_HARVESTS_its_github_surfaces.py` is the
enumerating sweep that fails the entrypoint that does not — in the family of
`test_every_parent_opens_a_run_bag`, which is where r4's standing check lives.
The first cut invoked it on the success path only, one line after the
workflow returned; every failed run harvested nothing and recorded no gap.

WHAT IS BUILDABLE TODAY AND WHAT IS PORT-TIME, the same split as the other two
activities: layer placement, invocation and fail-stop are here; orchestrator-
driven retry and recorded execution are properties of a worker that does not
exist. Retry is safe when it comes: a second harvest of one run lands in its
own writer subfolder and derives the same event identities, so
`dedupe_on_identity` collapses it on read.

FAIL-STOP MEANS TWO THINGS HERE, AND THEY ARE DIFFERENT. A run id that resolves
to no bag, or a reference that cannot be addressed, RAISES (`HarvestError`, a
`RuntimeError` every entrypoint's handler prints) — r2's *fails loudly rather
than writing into a bag it guessed at*. A surface that cannot be READ does not
raise: it becomes a typed gap and an `incomplete` flag, and the harvest reports
it and continues — r5, and Phase 3's own ruling that the post-exit harvest is a
case-(c) member on which *the run continues*. The pull request already exists
by the time this runs; stopping the parent would not un-post it, and would cost
the operator the banner that names it.

WHY THE PARENT INVOKES IT AND NOT `run_claude`. The child-exit boundary inside
`run_claude` does not know which PR the child made — the parent extracts that
URL from the child's output and carries it in its result, and a `--pr` run
carries its number in the context. The parent is the only actor holding both,
so the parent passes them — and on the failure path it holds only the first,
so it passes `None` for the second and a run that died before reporting a URL
harvests the dispatched PR alone, or nothing, recorded as such. Everything
else — the journal root, the run id, the repository slug, the fleet's own
login — is derived here once so every call site stays one line.

CONSUMER: Phase 6's evidence sweep reads what this emits (`phase6_cpi_reads_
the_journal.md` r3's producer/consumer table); `scripts/reconcile_harvest.py`
reads the index this leaves beside the events.

AND THIS IS WHERE PHASE 3 CASE (d)'s DURABLE REPORT IS DISPATCHED FROM, for
two reasons that are both about this activity's placement rather than its
job. The `finally` above is the one place in the fleet that runs while the
failure which ended the run is still in flight, AND the one call that holds
the run's surfaces — so when that failure is `JournalUnwritable`, this is the
only actor positioned to say so on a pull request. `in_flight_journal_failure`
reads the exception in flight; `report_case_d_durably` hands it to the
reporter the assistant layer registered (`emit.register_case_d_reporter`),
because posting a comment is a store write and this package composes none. A
run in case (d) HARVESTS NOTHING: its journal is gone, and writing into a bag
whose `incomplete` flag just failed to land would produce a bag that lost data
and reads as complete. The harvest's OWN case (d) — the journal dying between
the workflow's last emit and this call — takes the same path and then raises.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

from .emit import (UNWRITABLE_JOURNAL_MARKER, JournalUnwritable,
                   current_case_d_reporter, in_flight_journal_failure)
from .bag import validated_run_id
from .harvest import (HarvestError, HarvestReport, Runner, gh_runner,
                      harvest_run, parse_ref, repo_slug_of, resolve_bag)
from .journal_activities import load_journal_config, origin_remote
from .root import resolve_journal_root

__all__ = ["harvest_github_surfaces", "HarvestError", "fleet_login",
           "report_case_d_durably"]


def fleet_login(runner: Runner) -> str | None:
    """The login `gh` is authenticated as, or None when it cannot say.

    ONE REQUEST, AND ITS FAILURE IS A DEGRADED ANSWER RATHER THAN A STOPPED
    HARVEST. Without it every harvested body is `FETCHED` — the conservative
    class, which a downstream poller treats as untrusted. That is the right
    direction to fail in: nothing fleet-authored is mistaken for external text
    by being labelled external, whereas the reverse would be.
    """
    reply = runner(["api", "user", "--jq", ".login"])
    if reply.returncode != 0:
        return None
    login = reply.stdout.strip()
    return login or None


def report_case_d_durably(failure: JournalUnwritable, *, refs: Iterable[str | None],
                          repo_root: Path, bag_path: Path | None,
                          default_repo: str | None) -> str:
    """Post case (d)'s durable working-record line to the first surface `refs` names.

    RETURNS THE ADDRESS IT POSTED TO, OR "" — AND PRINTS WHICH, because this runs
    on the failure path and a second exception here would replace the report
    of the first. Three ways to return "" and each says so on the process
    channel, which is the one channel that needs nothing built: no reporter is
    registered (a process running no fleet workflow), no ref can be addressed
    (a run that made no PR and was dispatched against none), or the reporter
    could not post (it prints its own reason).

    ONE COMMENT, ON THE FIRST ADDRESSABLE REF, IN THE ORDER THE PARENT PASSED
    THEM — the dispatched PR before the reported one before any filed intake.
    A report on every surface would be the same fact three times, and the
    harvest's reader counts every copy.
    """
    reporter = current_case_d_reporter()
    if reporter is None:
        print(f"⚠ {UNWRITABLE_JOURNAL_MARKER}: no case-(d) reporter is registered "
              f"in this process, so the durable working-record line was NOT "
              f"posted — the process exit is the only channel carrying it",
              file=sys.stderr, flush=True)
        return ""
    for raw in refs:
        if raw is None or not str(raw).strip():
            continue
        try:
            ref = parse_ref(str(raw), default_repo=default_repo)
        except HarvestError as exc:
            print(f"⚠ {UNWRITABLE_JOURNAL_MARKER}: ref {raw!r} cannot carry the "
                  f"durable report — {exc}", file=sys.stderr, flush=True)
            continue
        address = reporter(failure, ref.url, repo_root, bag_path)
        if address:
            print(f"⚠ {UNWRITABLE_JOURNAL_MARKER}: durable report posted at "
                  f"{address}", file=sys.stderr, flush=True)
        return address
    print(f"⚠ {UNWRITABLE_JOURNAL_MARKER}: this run names no surface, so the "
          f"durable working-record line has nowhere to go — the process exit is "
          f"the only channel carrying it", file=sys.stderr, flush=True)
    return ""


def harvest_github_surfaces(*, run_id: str, repo_root: Path,
                            refs: Iterable[str | None],
                            journal_root: Path | None = None,
                            runner: Runner | None = None,
                            config_path: Path | None = None) -> HarvestReport | None:
    """Harvest every GitHub surface `refs` names into `run_id`'s bag. The activity.

    `refs` IS WHATEVER THE PARENT HOLDS: the `--pr` number from its context, the
    URL its child reported, both, or neither — and, for every run that includes
    a review pass (the standalone reviewer AND the five parents that embed
    it), every intake issue that reviewer reported filing, trailing those
    two. The embedding parents passed the pair alone until 2026-09-14 and the
    miss was silent — `BuildResult.issue_urls` records it. `None` and empty
    entries are skipped, so a parent passes `(ctx.pr_number, pr_url)`
    unconditionally and a run that made no PR harvests nothing — recorded as
    such, not refused.

    `journal_root` IS THE BOUNDARY'S ANSWER, TAKEN RATHER THAN RE-DERIVED,
    exactly as `open_run_bag` takes it: the context resolved the root once, and
    two resolutions could disagree. When nobody supplies it — the operator tool,
    the tests — it is resolved read-only here, because a harvest must not bring
    the root it is writing into existence.

    THE RESULT IS PRINTED HERE, ONE LINE PER SURFACE, rather than returned for
    each parent to render. Every parent's banner renders its own way; a harvest
    line that looks the same everywhere is one an operator learns to read.

    RAISES `HarvestError` (r2). A surface it cannot read is a gap in the report,
    not an exception.

    RETURNS `None` — AND HARVESTS NOTHING — WHEN A `JournalUnwritable` IS IN
    FLIGHT: the run this is cleaning up after is in Phase 3 case (d), its
    journal is gone, and this activity's job becomes posting the durable half
    of that report (`report_case_d_durably`) before the in-flight failure
    reaches the entrypoint's handler. Its OWN case (d) — the journal dying
    between the workflow's last emit and this call — posts the same report and
    then RAISES, so the process channel carries it too.
    """
    refs = tuple(refs)
    # THE BAG'S PATH IS THE REPORT'S, NOT A RESOLVED BAG: in case (d) the bag
    # may be exactly what is gone, so it is named rather than stat'ed. Rebound
    # through `validated_run_id` first — the same allowlist `resolve_bag` and
    # `open_bag` join under — so the path cannot escape the root.
    run_id = validated_run_id(run_id)
    default_repo = repo_slug_of(origin_remote(repo_root))
    # THE IN-FLIGHT CHECK IS FIRST, AND THE ROOT IS NOT RESOLVED ON ITS PATH.
    # This runs inside every entrypoint's `finally` while the failure that
    # ended the run may still be propagating, so anything that raises between
    # here and the report REPLACES that failure and the durable half is never
    # posted. `resolve_journal_root` is exactly such a thing when the root is
    # what is gone — so on the in-flight path the bag is named from the root
    # the caller already holds, or not at all (`bag: -` in the report).
    # `origin_remote` returns "" rather than raising, and `run_id` was accepted
    # by the bag that opened, so neither line above can preempt the report.
    in_flight = in_flight_journal_failure()
    if in_flight is not None:
        report_case_d_durably(
            in_flight, refs=refs, repo_root=repo_root,
            bag_path=journal_root / run_id if journal_root is not None else None,
            default_repo=default_repo)
        return None
    root = journal_root if journal_root is not None else resolve_journal_root(
        config=load_journal_config(config_path), create=False)
    bag_path = root / run_id
    # r2 FIRST, BEFORE THE LOGIN PROBE. `harvest_run` resolves the bag again —
    # three stat calls, idempotent — but it takes the login as a VALUE, and the
    # probe is a network request. Resolving here is what makes "a run id with
    # no bag costs nothing and touches nothing" true of the activity and not
    # only of the mechanism; the first cut probed first, and the test written
    # to hold the order had been loosened to let the probe through.
    resolve_bag(root, run_id)
    run = runner if runner is not None else gh_runner(repo_root)
    try:
        report = harvest_run(
            journal_root=root, run_id=run_id, repo_root=repo_root, refs=refs,
            default_repo=default_repo, fleet_login=fleet_login(run), runner=run)
    except JournalUnwritable as own:
        report_case_d_durably(own, refs=refs, repo_root=repo_root,
                              bag_path=bag_path, default_repo=default_repo)
        raise
    print(report.as_note(), flush=True)
    return report
