"""PMP Phase 10 — the post-exit harvest, driven against a FAKE `gh` and REAL bags.

A fake `gh` because the unit tier reaches no network; real bags on a real
filesystem for the reason `test_journal_emit.py` gives — a mocked `open()`
cannot show that a gap event, an `incomplete` flag and an index all land where
the next reader looks for them.

WHAT IS PROVEN HERE, one section each:

  * REFERENCES  — a URL, a bare number, a fragment-bearing comment URL and a
                  `None` all resolve to what the phase says they mean, and a
                  bare number with no repository is refused rather than guessed.
  * RESOLUTION  — r2: an absent bag, a folder that is not a bag, and a sealed
                  bag are each refused with the path named. Nothing is created.
  * THE HARVEST — r1: every body lands verbatim as a `completion` with the
                  GitHub URL as its destination and the fleet's login deciding
                  provenance; r3(b): the bag carries a `Journal-Harvest` tag and
                  an index naming what was covered and when.
  * THE GAP     — r5: a surface that cannot be read leaves a typed gap naming
                  it, the bag is `incomplete`, and the NEXT surface is still
                  harvested. The fetch's three failure shapes are one class.
  * THE FILTER  — r6: a credential inside a harvested comment is replaced on
                  the same path a fleet-authored comment takes, with the
                  placeholder event beside it.
  * PAGINATION  — pages are flattened, the surface's own count is the
                  denominator, and the argv asks for the documented maximum.
  * THE WINDOW  — r3(c): `reconcile_surface` sorts a later snapshot into
                  captured / late / missed / deleted / edited, and only `missed`
                  fails.

⚠ THE FAKE `gh` IS KEYED ON THE ENDPOINT PATH, NOT ON THE WHOLE ARGV, so a test
that changed a flag by accident would still be answered — which is why
`test_the_comments_request_asks_for_the_documented_page_size` asserts the argv
explicitly rather than trusting the fake to have refused it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from modules.journal import harvest as h
from modules.journal.bag import LABEL_GAP, LABEL_INCOMPLETE, open_bag, read_tag_file
from modules.journal.events import (EVENTS_FILE, EventKind, GapClass,
                                    Provenance, decode_event)
from modules.journal.harvest_activities import harvest_github_surfaces

REPO = "acme/widgets"
PR = f"https://github.com/{REPO}/pull/7"
ME = "fleet-bot"


# --- the fake `gh` -----------------------------------------------------------------

def _reply(stdout: str = "", code: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(["gh"], returncode=code, stdout=stdout,
                                       stderr=stderr)


def _comment(cid: int, body: str, *, author: str = ME,
             created: str = "2026-09-12T10:00:00Z",
             updated: str | None = None) -> dict:
    return {"id": cid, "body": body, "user": {"login": author},
            "created_at": created, "updated_at": updated or created,
            "html_url": f"{PR}#issuecomment-{cid}"}


class FakeGh:
    """Answers `gh api` by endpoint. Records every argv it was handed."""

    def __init__(self, surfaces: dict[str, tuple[dict, list[list[dict]]]],
                 login: str | None = ME) -> None:
        self.surfaces = surfaces        # "repo#n" -> (head, pages)
        self.login = login
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess:
        self.calls.append(list(args))
        endpoint = next((a for a in args if a.startswith("repos/") or a == "user"), "")
        if endpoint == "user":
            return _reply(f"{self.login}\n") if self.login else _reply(code=1, stderr="not logged in")
        parts = endpoint.split("?")[0].split("/")
        key = f"{parts[1]}/{parts[2]}#{parts[4]}"
        if key not in self.surfaces:
            return _reply(code=1, stderr=f"gh: Not Found (HTTP 404) {endpoint}")
        head, pages = self.surfaces[key]
        if "/comments" in endpoint:
            return _reply(json.dumps(pages))
        return _reply(json.dumps(head))


def _head(body: str = "the PR body", *, author: str = ME, count: int = 0) -> dict:
    return {"body": body, "user": {"login": author}, "html_url": PR,
            "created_at": "2026-09-12T09:00:00Z",
            "updated_at": "2026-09-12T09:00:00Z", "comments": count,
            "pull_request": {"url": "…"}}


@pytest.fixture
def journal(tmp_path: Path) -> Path:
    root = tmp_path / "journal"
    root.mkdir(mode=0o700)
    return root


def _bag(root: Path, run_id: str = "run-1"):
    return open_bag(root, run_id, info={"Journal-Workflow": "test"})


def _events(writer_dir: Path) -> list:
    path = writer_dir / EVENTS_FILE
    if not path.is_file():
        return []
    return [decode_event(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _harvest(root: Path, gh: FakeGh, refs, run_id: str = "run-1", **kw):
    return h.harvest_run(journal_root=root, run_id=run_id,
                         repo_root=root.parent, refs=refs, default_repo=REPO,
                         fleet_login=ME, runner=gh, **kw)


# --- references ----------------------------------------------------------------------

@pytest.mark.parametrize("text, kind, number", [
    (PR, "pull", 7),
    (f"{PR}#issuecomment-123", "pull", 7),
    (f"{PR}/files", "pull", 7),
    (f"https://github.com/{REPO}/issues/9", "issue", 9),
    ("7", "pull", 7),
    ("#7", "pull", 7),
    (" 7 ", "pull", 7),
])
def test_a_reference_resolves_to_the_surface_it_names(text, kind, number) -> None:
    ref = h.parse_ref(text, default_repo=REPO)
    assert (ref.repo, ref.kind, ref.number) == (REPO, kind, number)


def test_a_bare_number_with_NO_repository_is_REFUSED_not_guessed() -> None:
    with pytest.raises(h.HarvestError, match="bare number.*Refusing to guess"):
        h.parse_ref("7", default_repo=None)


@pytest.mark.parametrize("text", ["https://gitlab.com/a/b/-/merge_requests/1",
                                  "https://github.com/acme/pull/7",
                                  "pull/7", "seven", ""])
def test_an_unaddressable_reference_is_REFUSED(text) -> None:
    with pytest.raises(h.HarvestError):
        h.parse_ref(text, default_repo=REPO)


def test_surface_refs_DEDUPES_and_SKIPS_absences() -> None:
    refs = h.surface_refs((None, "", "7", PR, f"{PR}#issuecomment-1", "  "),
                          default_repo=REPO)
    assert [r.url for r in refs] == [PR]


def test_surface_refs_over_nothing_is_an_EMPTY_harvest_not_a_refusal() -> None:
    assert h.surface_refs((None, None), default_repo=None) == ()


@pytest.mark.parametrize("remote, slug", [
    ("git@github.com:acme/widgets.git", REPO),
    ("https://github.com/acme/widgets.git", REPO),
    ("https://github.com/acme/widgets", REPO),
    ("ssh://git@github.com/acme/widgets.git", REPO),
    ("git@gitlab.com:acme/widgets.git", None),
    ("", None),
    ("https://github.com/acme", None),
])
def test_the_repository_slug_is_read_off_the_three_spellings_git_produces(remote, slug):
    assert h.repo_slug_of(remote) == slug


# --- resolution (r2) -----------------------------------------------------------------

def test_an_ABSENT_bag_is_refused_and_NOTHING_is_created(journal: Path) -> None:
    with pytest.raises(h.HarvestError, match="resolves to no bag"):
        h.resolve_bag(journal, "never-opened")
    assert not (journal / "never-opened").exists(), (
        "the harvest created the bag it could not find — the exact guess r2 forbids")


def test_a_folder_that_is_NOT_a_bag_is_refused(journal: Path) -> None:
    (journal / "stray").mkdir(mode=0o700)
    with pytest.raises(h.HarvestError, match="is not a bag: bagit.txt is missing"):
        h.resolve_bag(journal, "stray")


def test_a_SEALED_bag_is_refused(journal: Path) -> None:
    bag = _bag(journal)
    bag.seal()
    with pytest.raises(h.HarvestError, match="already SEALED"):
        h.resolve_bag(journal, "run-1")


def test_a_forged_run_id_is_refused_by_the_SAME_allowlist_bag_open_uses(journal: Path):
    from modules.journal.bag import BagError
    with pytest.raises(BagError):
        h.resolve_bag(journal, "../escape")


# --- the harvest (r1, r3b) ------------------------------------------------------------

def test_every_body_lands_VERBATIM_as_a_completion_addressed_to_its_URL(journal: Path):
    _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head("Body — with «unicode» and\n\nblank lines", count=2),
                               [[_comment(11, "first"), _comment(12, "second — by a human",
                                                                  author="operator")]])})
    report = _harvest(journal, gh, (PR,))

    assert report.ok
    events = _events(report.writer_dir)
    assert [e.kind for e in events] == [EventKind.COMPLETION] * 3
    assert [e.content for e in events] == [
        "Body — with «unicode» and\n\nblank lines", "first", "second — by a human"]
    assert [e.destination.store for e in events] == ["github"] * 3
    assert [e.destination.address for e in events] == [
        PR, f"{PR}#issuecomment-11", f"{PR}#issuecomment-12"]
    assert [e.provenance for e in events] == [
        Provenance.FLEET_AUTHORED, Provenance.FLEET_AUTHORED, Provenance.FETCHED]
    assert [e.write_path for e in events] == [
        f"harvest:github:{REPO}#7:body", f"harvest:github:{REPO}#7:comment:11",
        f"harvest:github:{REPO}#7:comment:12"]
    assert all(e.run_id == "run-1" for e in events)


def test_the_bag_SAYS_what_the_harvest_covered_and_when(journal: Path) -> None:
    bag = _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head(count=1), [[_comment(11, "x")]])})
    report = _harvest(journal, gh, (PR,), clock=lambda: "2026-09-12T12:00:00Z")

    tags = [v for label, v in read_tag_file(bag.info_path) if label == h.LABEL_HARVEST]
    assert tags == [f"2026-09-12T12:00:00Z {PR} comments=1/1 body=captured bytes=12"]

    indexes = h.read_harvest_indexes(bag.path)
    assert len(indexes) == 1
    index = indexes[0]
    assert index["run_id"] == "run-1" and index["fleet_login"] == ME
    surface, = index["surfaces"]
    assert surface["harvested_at"] == "2026-09-12T12:00:00Z"
    assert surface["captured"] is True
    assert surface["comments_harvested"] == surface["comments_on_surface"] == 1
    assert surface["body"]["event_id"] == report.surfaces[0].body_event
    assert surface["comments"][0]["id"] == 11
    assert surface["comments"][0]["event_id"] == report.surfaces[0].comment_events[0][1]
    assert "body" not in surface["comments"][0], "the index carries no prose"


def test_a_run_with_NO_surface_harvests_nothing_and_says_so(journal: Path) -> None:
    bag = _bag(journal)
    report = _harvest(journal, FakeGh({}), (None, ""))
    assert report.surfaces == () and report.ok
    assert "nothing to capture" in report.as_note()
    assert h.read_harvest_indexes(bag.path)[0]["surfaces"] == []
    assert not bag.incomplete


def test_SEVERAL_surfaces_land_in_ONE_bag(journal: Path) -> None:
    _bag(journal)
    other = f"https://github.com/{REPO}/issues/9"
    gh = FakeGh({f"{REPO}#7": (_head("pr", count=0), [[]]),
                 f"{REPO}#9": ({**_head("issue", count=0), "html_url": other}, [[]])})
    report = _harvest(journal, gh, ("7", other))
    assert [s.ref.url for s in report.surfaces] == [PR, other]
    assert {e.destination.address for e in _events(report.writer_dir)} == {PR, other}


def test_a_SECOND_harvest_derives_the_SAME_identities_so_replay_dedupes(journal: Path):
    _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head(count=1), [[_comment(11, "x")]])})
    first = _harvest(journal, gh, (PR,))
    second = _harvest(journal, gh, (PR,))
    assert second.writer_dir.name == "harvest-2"
    from modules.journal.events import dedupe_on_identity
    both = _events(first.writer_dir) + _events(second.writer_dir)
    assert len(both) == 4 and len(dedupe_on_identity(both)) == 2


def test_provenance_DEGRADES_to_fetched_when_the_login_is_unknown(journal: Path):
    _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head(count=0), [[]])})
    report = h.harvest_run(journal_root=journal, run_id="run-1", repo_root=journal,
                           refs=(PR,), default_repo=REPO, fleet_login=None, runner=gh)
    assert _events(report.writer_dir)[0].provenance is Provenance.FETCHED


def test_a_PR_with_a_null_body_is_recorded_EMPTY_not_refused(journal: Path) -> None:
    _bag(journal)
    gh = FakeGh({f"{REPO}#7": ({**_head(count=0), "body": None}, [[]])})
    report = _harvest(journal, gh, (PR,))
    assert report.ok and _events(report.writer_dir)[0].content == ""


# --- the gap (r5) ---------------------------------------------------------------------

def test_an_UNREADABLE_surface_leaves_a_typed_gap_and_marks_the_bag(journal: Path):
    bag = _bag(journal)
    gh = FakeGh({})                                   # every surface is a 404
    report = _harvest(journal, gh, (PR,))

    assert not report.ok
    surface, = report.surfaces
    assert surface.captured is False and "404" in surface.failure
    gap, = _events(report.writer_dir)
    assert gap.kind is EventKind.GAP
    assert gap.gap_class is GapClass.SURFACE_UNREADABLE
    assert gap.destination.address == PR, "the gap NAMES the surface it could not read"
    assert "404" not in gap.content and gap.content == "", (
        "the reply's text reached the record — the closed set exists to stop that")
    assert bag.incomplete
    labels = dict((label, value) for label, value in read_tag_file(bag.info_path)
                  if label in (LABEL_INCOMPLETE, LABEL_GAP))
    assert labels[LABEL_INCOMPLETE] == "true"
    assert "surface_unreadable" in labels[LABEL_GAP]
    assert "NOT READ" in report.as_note()


def test_the_harvest_CONTINUES_past_an_unreadable_surface(journal: Path) -> None:
    _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head("pr", count=0), [[]])})
    report = _harvest(journal, gh, (f"https://github.com/{REPO}/issues/404", PR))
    assert [s.captured for s in report.surfaces] == [False, True]
    kinds = [e.kind for e in _events(report.writer_dir)]
    assert kinds == [EventKind.GAP, EventKind.COMPLETION]


@pytest.mark.parametrize("stdout, code, why", [
    ("", 1, "exited 1"),
    ("<html>rate limited</html>", 0, "not JSON"),
    ("42", 0, "int, not dict"),
])
def test_the_fetch_has_ONE_failure_class_for_three_failure_shapes(stdout, code, why):
    ref = h.SurfaceRef(REPO, "pull", 7)
    runner = lambda args: _reply(stdout, code, "boom")  # noqa: E731
    with pytest.raises(h.SurfaceUnreadable, match=why):
        h.fetch_surface(ref, cwd=Path("."), runner=runner)


def test_a_comment_entry_with_the_WRONG_shape_is_refused_not_coerced() -> None:
    ref = h.SurfaceRef(REPO, "pull", 7)
    pages = [[{"id": "eleven", "body": "x"}]]
    gh = FakeGh({f"{REPO}#7": (_head(count=1), pages)})
    with pytest.raises(h.SurfaceUnreadable, match="no integer id"):
        h.fetch_surface(ref, cwd=Path("."), runner=gh)


# --- the filter (r6) ------------------------------------------------------------------

def test_a_credential_in_a_HARVESTED_comment_is_filtered_on_the_same_path(journal: Path):
    _bag(journal)
    secret = "ghp_" + "A" * 36
    gh = FakeGh({f"{REPO}#7": (_head(count=1),
                               [[_comment(11, f"token is {secret} — do not share")]])})
    report = _harvest(journal, gh, (PR,))
    events = _events(report.writer_dir)
    kinds = [e.kind for e in events]
    assert kinds == [EventKind.COMPLETION, EventKind.REDACTION_PLACEHOLDER,
                     EventKind.COMPLETION]
    assert secret not in (report.writer_dir / EVENTS_FILE).read_text(encoding="utf-8")
    assert "github-token" in events[1].content
    assert events[2].content.startswith("token is [FILTERED")
    assert report.ok, "a filtered comment is a captured comment"


# --- pagination -------------------------------------------------------------------------

def test_pages_are_FLATTENED_and_the_surface_count_is_the_denominator(journal: Path):
    _bag(journal)
    pages = [[_comment(1, "a"), _comment(2, "b")], [_comment(3, "c")]]
    # The surface reports FOUR: one more than the pages hold, which is what a
    # comment posted between the two requests looks like. The denominator is
    # the surface's, and the record says 3/4 rather than 3/3.
    gh = FakeGh({f"{REPO}#7": (_head(count=4), pages)})
    report = _harvest(journal, gh, (PR,))
    surface, = report.surfaces
    assert surface.comments_harvested == 3 and surface.comments_on_surface == 4
    assert "3/4 comments" in report.as_note()


def test_the_comments_request_asks_for_the_documented_page_size() -> None:
    gh = FakeGh({f"{REPO}#7": (_head(count=0), [[]])})
    h.fetch_surface(h.SurfaceRef(REPO, "pull", 7), cwd=Path("."), runner=gh)
    head, comments = gh.calls
    assert head == ["api", f"repos/{REPO}/issues/7"]
    assert comments == ["api", "--paginate", "--slurp",
                        f"repos/{REPO}/issues/7/comments?per_page=100"]
    assert h.PER_PAGE == 100


def test_a_page_that_is_not_a_list_is_refused() -> None:
    gh = FakeGh({f"{REPO}#7": (_head(count=0), [{"not": "a page"}])})
    with pytest.raises(h.SurfaceUnreadable, match="array of arrays"):
        h.fetch_surface(h.SurfaceRef(REPO, "pull", 7), cwd=Path("."), runner=gh)


# --- the window (r3c) -------------------------------------------------------------------

def _snapshot(*comments: dict, count: int | None = None) -> h.Snapshot:
    parsed = tuple(h.Comment(id=c["id"], url=c["html_url"], author=c["user"]["login"],
                             created_at=c["created_at"], updated_at=c["updated_at"],
                             body=c["body"]) for c in comments)
    return h.Snapshot(ref=h.SurfaceRef(REPO, "pull", 7), url=PR, author=ME,
                      created_at="t0", updated_at="t0", body="",
                      comment_count=len(parsed) if count is None else count,
                      comments=parsed, fetched_at="now")


def _index_entry(harvested_at: str, *comments: dict) -> dict:
    return {"url": PR, "harvested_at": harvested_at,
            "comments": [{"id": c["id"], "event_id": f"ev-{c['id']}",
                          "created_at": c["created_at"],
                          "updated_at": c["updated_at"]} for c in comments]}


def test_the_reconciliation_sorts_every_comment_into_EXACTLY_ONE_set() -> None:
    at = "2026-09-12T12:00:00Z"
    captured = _comment(1, "in", created="2026-09-12T11:00:00Z")
    edited = _comment(2, "in, then edited", created="2026-09-12T11:30:00Z")
    deleted = _comment(3, "in, then deleted", created="2026-09-12T11:40:00Z")
    entry = _index_entry(at, captured, edited, deleted)

    edited_now = {**edited, "updated_at": "2026-09-12T13:00:00Z"}
    late = _comment(4, "after the window", created="2026-09-12T12:00:01Z")
    missed = _comment(5, "inside the window, never captured",
                      created="2026-09-12T11:59:59Z")
    boundary = _comment(6, "same second as the harvest", created=at)
    rec = h.reconcile_surface(entry, _snapshot(captured, edited_now, late, missed, boundary))

    assert rec.captured == (1, 2)
    assert rec.edited_since == (2,)
    assert rec.deleted_since == (3,)
    assert rec.late == (4,)
    assert rec.missed == (5, 6), "a same-second comment was there to be read"
    assert rec.harvested == 3 and rec.comments_on_surface_now == 5
    assert not rec.ok


def test_ONLY_a_missed_comment_fails_the_reconciliation() -> None:
    at = "2026-09-12T12:00:00Z"
    kept = _comment(1, "x", created="2026-09-12T11:00:00Z")
    gone = _comment(2, "y", created="2026-09-12T11:00:00Z")
    entry = _index_entry(at, kept, gone)
    late = _comment(3, "z", created="2026-09-12T12:30:00Z")
    rec = h.reconcile_surface(entry, _snapshot(kept, late))
    assert rec.ok and rec.late == (3,) and rec.deleted_since == (2,)
    text = h.render_reconciliation(rec)
    assert "late         : 1/2" in text and "verdict      : OK" in text


def test_a_comment_whose_event_became_a_GAP_counts_as_NOT_harvested() -> None:
    at = "2026-09-12T12:00:00Z"
    c = _comment(1, "x", created="2026-09-12T11:00:00Z")
    entry = _index_entry(at, c)
    entry["comments"][0]["event_id"] = None
    rec = h.reconcile_surface(entry, _snapshot(c))
    assert rec.missed == (1,) and not rec.ok


def test_indexes_are_read_OLDEST_WRITER_FIRST(journal: Path) -> None:
    bag = _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head(count=0), [[]])})
    for stamp in ("t1", "t2", "t3"):
        _harvest(journal, gh, (PR,), clock=lambda s=stamp: s)
    assert [i["ran_at"] for i in h.read_harvest_indexes(bag.path)] == ["t1", "t2", "t3"]


# --- the activity (r7) ------------------------------------------------------------------

def test_the_activity_resolves_root_slug_and_login_ONCE_and_prints(journal, capsys,
                                                                  monkeypatch):
    _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head(count=1), [[_comment(11, "x")]])})
    monkeypatch.setattr("modules.journal.harvest_activities._git",
                        lambda repo_root, *a: f"git@github.com:{REPO}.git")
    report = harvest_github_surfaces(run_id="run-1", repo_root=journal,
                                     refs=("7", None), journal_root=journal,
                                     runner=gh)
    assert report.ok
    assert gh.calls[0] == ["api", "user", "--jq", ".login"]
    assert f"harvest: {PR} — body + 1/1 comments" in capsys.readouterr().out


def test_the_activity_REFUSES_a_run_id_with_no_bag_before_touching_the_network(
        journal, monkeypatch):
    gh = FakeGh({})
    monkeypatch.setattr("modules.journal.harvest_activities._git",
                        lambda repo_root, *a: f"git@github.com:{REPO}.git")
    with pytest.raises(h.HarvestError, match="resolves to no bag"):
        harvest_github_surfaces(run_id="ghost", repo_root=journal, refs=("7",),
                                journal_root=journal, runner=gh)
    assert all(call[:2] == ["api", "user"] for call in gh.calls), (
        f"a surface was requested for a run with no bag: {gh.calls}")


def test_the_activity_needs_NO_repository_slug_when_every_ref_is_a_URL(journal,
                                                                       monkeypatch):
    _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head(count=0), [[]])})
    monkeypatch.setattr("modules.journal.harvest_activities._git",
                        lambda repo_root, *a: "")            # no origin remote
    report = harvest_github_surfaces(run_id="run-1", repo_root=journal,
                                     refs=(None, PR), journal_root=journal, runner=gh)
    assert report.ok
