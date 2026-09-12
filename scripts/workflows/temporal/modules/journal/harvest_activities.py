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
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .harvest import (HarvestError, HarvestReport, Runner, gh_runner,
                      harvest_run, repo_slug_of, resolve_bag)
from .journal_activities import load_journal_config, origin_remote
from .root import resolve_journal_root

__all__ = ["harvest_github_surfaces", "HarvestError", "fleet_login"]


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


def harvest_github_surfaces(*, run_id: str, repo_root: Path,
                            refs: Iterable[str | None],
                            journal_root: Path | None = None,
                            runner: Runner | None = None,
                            config_path: Path | None = None) -> HarvestReport:
    """Harvest every GitHub surface `refs` names into `run_id`'s bag. The activity.

    `refs` IS WHATEVER THE PARENT HOLDS: the `--pr` number from its context, the
    URL its child reported, both, or neither. `None` and empty entries are
    skipped, so a parent passes `(ctx.pr_number, pr_url)` unconditionally and
    a run that made no PR harvests nothing — recorded as such, not refused.

    `journal_root` IS THE BOUNDARY'S ANSWER, TAKEN RATHER THAN RE-DERIVED,
    exactly as `open_run_bag` takes it: the context resolved the root once, and
    two resolutions could disagree. When nobody supplies it — the operator tool,
    the tests — it is resolved read-only here, because a harvest must not bring
    the root it is writing into existence.

    THE RESULT IS PRINTED HERE, ONE LINE PER SURFACE, rather than returned for
    each parent to render. Every parent's banner renders its own way; a harvest
    line that looks the same everywhere is one an operator learns to read.

    RAISES `HarvestError` (r2) and lets `JournalUnwritable` through (case (d)).
    A surface it cannot read is a gap in the report, not an exception.
    """
    root = journal_root if journal_root is not None else resolve_journal_root(
        config=load_journal_config(config_path), create=False)
    # r2 FIRST, BEFORE THE LOGIN PROBE. `harvest_run` resolves the bag again —
    # three stat calls, idempotent — but it takes the login as a VALUE, and the
    # probe is a network request. Resolving here is what makes "a run id with
    # no bag costs nothing and touches nothing" true of the activity and not
    # only of the mechanism; the first cut probed first, and the test written
    # to hold the order had been loosened to let the probe through.
    resolve_bag(root, run_id)
    run = runner if runner is not None else gh_runner(repo_root)
    report = harvest_run(
        journal_root=root, run_id=run_id, repo_root=repo_root, refs=refs,
        default_repo=repo_slug_of(origin_remote(repo_root)),
        fleet_login=fleet_login(run), runner=run)
    print(report.as_note(), flush=True)
    return report
