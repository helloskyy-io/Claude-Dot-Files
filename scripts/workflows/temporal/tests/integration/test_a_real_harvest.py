"""One real harvest against one real pull request — PMP Phase 10's integration tier.

THE UNIT TIER PROVES THE MECHANISM AGAINST A FAKE `gh`; THIS PROVES THE VENDOR
STILL ANSWERS THE WAY THE MECHANISM ASSUMES. Every fact `harvest.py` rests on
— `gh api --paginate --slurp` returning an array of pages, the issue object
carrying a `comments` count, `html_url` on every comment, `updated_at` beside
`created_at` — is a claim about a service that can change without this
repository changing. A harvest that quietly returned nothing would look exactly
like a run that posted nothing (r4's stated failure), and this is the check
that reads the real surface.

THE FIXTURE IS A MERGED PULL REQUEST IN THIS REPOSITORY: `#175`, the PR that
shipped the emit rule this harvest is the other half of. Merged, so its body
and its eight comments are as stable as anything on a mutable surface can be;
the assertions are on SHAPE and on AGREEMENT WITH A SECOND READ rather than on
fixed counts, so a comment added to it later widens the numbers without
breaking the test. It writes into a `tmp_path` journal, never the operator's.

SKIPS — DISTINCTLY FROM PASSING — WHEN `gh` IS NOT AUTHENTICATED. CI runs with
`contents: read` and no token, so `gh api` refuses there; the skip reason names
that so a green tier is not mistaken for a harvested one. On any machine where
a dispatch has ever run, `gh` is authenticated and this runs for real.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from modules.journal import harvest as h
from modules.journal.bag import open_bag
from modules.journal.events import EVENTS_FILE, EventKind, decode_event
from modules.journal.harvest_activities import harvest_github_surfaces

REPO_ROOT = Path(__file__).resolve().parents[5]
FIXTURE_PR = "https://github.com/helloskyy-io/Claude-Dot-Files/pull/175"


def _gh_authenticated() -> bool:
    try:
        probe = subprocess.run(["gh", "auth", "status"], capture_output=True,
                               text=True, timeout=30, cwd=str(REPO_ROOT))
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


needs_gh = pytest.mark.skipif(
    not _gh_authenticated(),
    reason="`gh` is not authenticated here — the harvest cannot read GitHub. "
           "CI has no token by design; run this on a machine that dispatches.")


@needs_gh
def test_a_real_pull_request_is_harvested_VERBATIM_into_a_scratch_bag(
        journal_root: Path, capsys) -> None:
    open_bag(journal_root, "integration-1", info={"Journal-Workflow": "test"})
    report = harvest_github_surfaces(run_id="integration-1", repo_root=REPO_ROOT,
                                     refs=(None, FIXTURE_PR),
                                     journal_root=journal_root)
    assert report.ok, report.as_note()
    surface, = report.surfaces
    assert surface.comments_on_surface >= 1, "the fixture PR has comments"
    assert surface.comments_harvested == surface.comments_on_surface, (
        "pagination or the count disagree with the surface's own denominator")

    events = [decode_event(line) for line in
              (report.writer_dir / EVENTS_FILE).read_text(encoding="utf-8").splitlines()]
    assert all(e.kind is EventKind.COMPLETION for e in events)
    assert len(events) == 1 + surface.comments_harvested

    # AGREEMENT WITH A SECOND, INDEPENDENT READ of the same surface: the body on
    # the first event is byte-identical to what `gh` hands back directly. This
    # is what "verbatim" means here, checked rather than asserted.
    direct = subprocess.run(
        ["gh", "api", "repos/helloskyy-io/Claude-Dot-Files/issues/175", "--jq", ".body"],
        capture_output=True, text=True, timeout=60, cwd=str(REPO_ROOT))
    assert direct.returncode == 0, direct.stderr
    # `--jq` prints the string plus ONE newline; the body itself ends in two,
    # and a `rstrip` here would have called the record verbatim while it was
    # not. Exactly one newline is added, and nothing is removed.
    assert events[0].content + "\n" == direct.stdout
    assert events[0].destination.address == FIXTURE_PR

    out = capsys.readouterr().out
    assert f"harvest: {FIXTURE_PR} — body + " in out


@needs_gh
def test_the_vendor_facts_the_design_rests_on_STILL_HOLD(journal_root: Path) -> None:
    """The documented shapes, re-read from the live API rather than remembered.

    `--paginate --slurp` yields a list of lists; the head object carries an
    integer `comments`; every comment carries `id`, `html_url`, `created_at`,
    `updated_at` and `body`. A vendor change to any of these is a change to
    this test's outcome, which is the point.
    """
    snapshot = h.fetch_surface(h.SurfaceRef("helloskyy-io/Claude-Dot-Files", "pull", 175),
                               cwd=REPO_ROOT)
    assert snapshot.comment_count == len(snapshot.comments)
    raw = subprocess.run(
        ["gh", "api", "--paginate", "--slurp",
         "repos/helloskyy-io/Claude-Dot-Files/issues/175/comments?per_page=2"],
        capture_output=True, text=True, timeout=60, cwd=str(REPO_ROOT))
    pages = json.loads(raw.stdout)
    assert isinstance(pages, list) and all(isinstance(p, list) for p in pages)
    assert all(len(p) <= 2 for p in pages), "per_page was not honoured"
    assert sum(len(p) for p in pages) == snapshot.comment_count


@needs_gh
def test_a_reconciliation_of_a_fresh_harvest_reports_NO_shortfall(journal_root: Path,
                                                                  capsys) -> None:
    """The per-run check, end to end, on a surface nothing has changed between."""
    bag = open_bag(journal_root, "integration-2", info={"Journal-Workflow": "test"})
    harvest_github_surfaces(run_id="integration-2", repo_root=REPO_ROOT,
                            refs=(FIXTURE_PR,), journal_root=journal_root)
    entry, = h.read_harvest_indexes(bag.path)[-1]["surfaces"]
    now = h.fetch_surface(h.SurfaceRef(entry["repo"], entry["kind"], entry["number"]),
                          cwd=REPO_ROOT)
    rec = h.reconcile_surface(entry, now)
    assert rec.ok, h.render_reconciliation(rec)
    assert rec.missed == () and rec.harvested >= 1
