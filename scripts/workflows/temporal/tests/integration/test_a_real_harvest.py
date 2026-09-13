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
FIXTURE_SLUG = "helloskyy-io/Claude-Dot-Files"
FIXTURE_PR = f"https://github.com/{FIXTURE_SLUG}/pull/175"
# A CLOSED, HARVESTED INTAKE: filed by a reviewer child with the same
# `gh issue create --label tracked-intake` the FILED-INTAKE line reports, and
# closed by the tracked-items harvest on 2026-09-01. Closed conveyors are not
# edited, which makes it the most stable issue body this repository holds.
FIXTURE_INTAKE = f"https://github.com/{FIXTURE_SLUG}/issues/163"


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
    assert len(events) == 2 + surface.comments_harvested, "title, body, comments"
    title_event, body_event = events[:2]

    # AGREEMENT WITH A SECOND, INDEPENDENT READ of the same surface: the title
    # on the first event and the body on the second are byte-identical to what
    # `gh` hands back directly. This is what "verbatim" means here, checked
    # rather than asserted.
    def direct(field: str) -> str:
        read = subprocess.run(
            ["gh", "api", "repos/helloskyy-io/Claude-Dot-Files/issues/175",
             "--jq", field],
            capture_output=True, text=True, timeout=60, cwd=str(REPO_ROOT))
        assert read.returncode == 0, read.stderr
        return read.stdout

    # `--jq` prints the string plus ONE newline; the body itself ends in two,
    # and a `rstrip` here would have called the record verbatim while it was
    # not. Exactly one newline is added, and nothing is removed.
    assert title_event.content + "\n" == direct(".title")
    assert body_event.content + "\n" == direct(".body")
    assert title_event.destination.address == FIXTURE_PR
    assert body_event.destination.address == FIXTURE_PR

    out = capsys.readouterr().out
    assert f"harvest: {FIXTURE_PR} — title + body + " in out


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


@needs_gh
@pytest.mark.parametrize("carrier", ["printed-line", "block"])
def test_a_review_that_FILES_an_intake_has_its_body_in_the_bag_VERBATIM(
        _journal_root_is_never_the_operators: Path, tmp_path: Path, monkeypatch,
        capsys, carrier: str) -> None:
    """Issue #185's integration case: the review ENTRYPOINT, end to end, with only
    the model faked — `run_review_pr.main` → the real `run_review` reading the
    intake off the child's report → `ReviewResult.issue_urls` → the `finally`'s
    harvest, with real `gh`, reading the intake into this run's bag. The PR the
    review was dispatched against lands beside it, which is the two-surface
    shape a live review that filed something produces.

    ONCE PER CARRIER. `printed-line` is the `FILED-INTAKE:` line on the child's
    text; `block` is the `filed_intakes:` list in its posted `pr_review:` block
    with NO line printed — the live shape, measured on the archive: the current
    child's top-level text is one 27-character block, so the block is the copy
    that lands. Each case carries the intake on ONE surface only, so a reader
    that silently stopped reading either would go red here, not in a log.

    THE CHILD IS FAKED AT ITS BOUNDARIES AND NOWHERE ELSE. `_FakeWorkflow`
    replaces the model invocation, the worktree cut and the thread reads — the
    I/O a review does around the child — and hands back the prose the child
    would have printed. Everything between that prose and the bag is the
    production path. The unit tier proves the parse; this proves the vendor's
    body reaches the record byte for byte.

    THE JOURNAL ROOT IS THE SESSION SANDBOX (`tests/conftest.py`), REQUESTED BY
    NAME rather than this tier's per-test `journal_root`: `main()` resolves its
    root through `CONFIG_PATH`, which that session fixture redirects, so the bag
    is found where the entrypoint actually put it. It is also why this module
    can drive `main()` without joining the population
    `test_the_suite_never_writes_to_the_operators_journal.py` pins — that census
    is over `tests/unit/` and the redirect fixture is over the whole tree.
    """
    journal_root = _journal_root_is_never_the_operators
    import run_review_pr as kickoff
    from review_run_fakes import _FakeWorkflow, _record

    # A repository for the run to be "in": preflight wants a git toplevel, and
    # the harvest reads the slug off `origin` to address the bare `--pr`.
    repo = tmp_path / "repo"
    repo.mkdir()
    for cmd in (["git", "init", "-q"],
                ["git", "remote", "add", "origin",
                 f"https://github.com/{FIXTURE_SLUG}.git"]):
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True)

    # The child's typed record must name the PR the parent dispatched against
    # (rule R5b), so the fake's default `owner/repo#67` is replaced by the
    # fixture PR in this repository.
    completion_ref = {"substrate": "github", "kind": "pull", "id": "175", "uri": FIXTURE_PR}
    if carrier == "printed-line":
        prose = f"Disposition posted.\nFILED-INTAKE: {FIXTURE_INTAKE}\nVERDICT: MERGE\n"
        block, counts = _FakeWorkflow.DEFAULT_BLOCK, "1 on the printed FILED-INTAKE line, 0"
    else:
        prose = "## Stage 1: VERIFY + GATHER"
        block = _FakeWorkflow.DEFAULT_BLOCK + f"  filed_intakes:\n    - {FIXTURE_INTAKE}\n"
        counts = "0 on the printed FILED-INTAKE line, 1"
    fake = _FakeWorkflow(_record(run_id="@ISSUED@", completion_ref=completion_ref), prose,
                         block=block, block_carries_nonce=True)
    wf = fake.install(monkeypatch, tmp_path)
    monkeypatch.setattr(wf._shared, "repo_slug", lambda *a, **k: FIXTURE_SLUG)

    run_id = f"integration-review-185-{carrier}"
    assert kickoff.main(["--pr", "175", "--repo", str(repo), "--run-id", run_id]) == 0

    out = capsys.readouterr().out
    assert (f"Filed 1 intake(s), handed to the harvest ({counts} in the posted block's "
            f"filed_intakes): {FIXTURE_INTAKE}") in out
    assert f"harvest: {FIXTURE_PR} — title + body + " in out
    assert f"harvest: {FIXTURE_INTAKE} — title + body + " in out

    bag = h.resolve_bag(journal_root, run_id)
    index, = h.read_harvest_indexes(bag.path)
    by_url = {entry["url"]: entry for entry in index["surfaces"]}
    assert set(by_url) == {FIXTURE_PR, FIXTURE_INTAKE}, "both surfaces, nothing else"
    assert by_url[FIXTURE_INTAKE]["kind"] == "issue" and by_url[FIXTURE_INTAKE]["captured"]

    events = {e.event_id: e for e in (
        decode_event(line) for line in
        (bag.path / "data" / h.HARVEST_WRITER / EVENTS_FILE)
        .read_text(encoding="utf-8").splitlines())}
    body_event = events[by_url[FIXTURE_INTAKE]["body"]["event_id"]]
    assert body_event.kind is EventKind.COMPLETION
    assert body_event.destination.address == FIXTURE_INTAKE

    # BYTE-IDENTITY AGAINST AN INDEPENDENT READ, the same check the PR case
    # makes: `--jq` appends exactly one newline to the string it prints.
    direct = subprocess.run(
        ["gh", "api", f"repos/{FIXTURE_SLUG}/issues/163", "--jq", ".body"],
        capture_output=True, text=True, timeout=60, cwd=str(REPO_ROOT))
    assert direct.returncode == 0, direct.stderr
    assert body_event.content + "\n" == direct.stdout
    assert body_event.content.startswith("---\nstore:"), (
        "an intake body opens with its frontmatter; this one does not read as one")
