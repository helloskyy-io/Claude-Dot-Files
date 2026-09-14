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
  * THE HARVEST — r1: the title, the body and every comment land verbatim as
                  a `completion` with the GitHub URL as its destination and the
                  fleet's login deciding provenance; r3(b): the bag carries a
                  `Journal-Harvest` tag and an index naming what was covered
                  and when.
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


def _head(body: str = "the PR body", *, author: str = ME, count: int = 0,
          title: str = "the PR title") -> dict:
    return {"title": title, "body": body, "user": {"login": author}, "html_url": PR,
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


@pytest.mark.parametrize("remote, resolves_to, slug", [
    ("git@master-planning-github:acme/widgets.git", "github.com", REPO),
    ("ssh://git@planning-alias/acme/widgets.git", "github.com", REPO),
    ("git@my-gitlab:acme/widgets.git", "gitlab.com", None),
    ("git@unknown-alias:acme/widgets.git", "unknown-alias", None),
])
def test_an_SSH_ALIAS_is_resolved_to_its_host_before_the_forge_is_judged(
        monkeypatch, remote, resolves_to, slug):
    """The host string in the remote is a proxy; where ssh resolves it is the thing."""
    monkeypatch.setattr(h, "ssh_host_of", lambda alias: resolves_to)
    assert h.repo_slug_of(remote) == slug


def test_ssh_host_of_READS_THE_USERS_CONFIG_and_falls_back_to_the_alias() -> None:
    assert h.ssh_host_of("github.com") == "github.com"
    assert h.ssh_host_of("no-such-alias-zzz") == "no-such-alias-zzz"


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
    assert [e.kind for e in events] == [EventKind.COMPLETION] * 4
    assert [e.content for e in events] == [
        "the PR title", "Body — with «unicode» and\n\nblank lines", "first",
        "second — by a human"]
    assert [e.destination.store for e in events] == ["github"] * 4
    assert [e.destination.address for e in events] == [
        PR, PR, f"{PR}#issuecomment-11", f"{PR}#issuecomment-12"]
    assert [e.provenance for e in events] == [
        Provenance.FLEET_AUTHORED, Provenance.FLEET_AUTHORED,
        Provenance.FLEET_AUTHORED, Provenance.FETCHED]
    assert [e.write_path for e in events] == [
        f"harvest:github:{REPO}#7:title", f"harvest:github:{REPO}#7:body",
        f"harvest:github:{REPO}#7:comment:11", f"harvest:github:{REPO}#7:comment:12"]
    assert all(e.run_id == "run-1" for e in events)


def test_the_TITLE_lands_verbatim_as_its_own_event_addressed_to_the_SURFACE(
        journal: Path) -> None:
    """The run authored the title (`gh pr create` names a format for it) and a
    retitle leaves no history, so it is one more verbatim event — addressed to
    the surface itself, as the body is, because there is no narrower URL for a
    headline."""
    _bag(journal)
    title = "build-draft: PMP Phase 10 — «the» model-issued harvest"
    gh = FakeGh({f"{REPO}#7": (_head("body", count=0, title=title), [[]])})
    report = _harvest(journal, gh, (PR,))

    assert report.ok
    title_event, body_event = _events(report.writer_dir)
    assert title_event.kind is EventKind.COMPLETION
    assert title_event.content == title
    assert title_event.destination.store == "github"
    assert title_event.destination.address == PR == body_event.destination.address
    assert title_event.write_path == f"harvest:github:{REPO}#7:title"
    assert title_event.event_id == report.surfaces[0].title_event
    surface, = h.read_harvest_indexes(report.bag_path)[0]["surfaces"]
    assert surface["title"] == {"event_id": title_event.event_id,
                                "bytes": len(title.encode("utf-8"))}
    assert surface["bytes_harvested"] == len(title.encode("utf-8")) + len(b"body")


def test_a_TITLE_the_surface_carries_as_a_non_string_is_REFUSED_not_recorded_empty() -> None:
    """`body: null` is a real state and is recorded as empty; a title is never
    null on GitHub, so its absence is a surface defect, not a value."""
    gh = FakeGh({f"{REPO}#7": ({**_head(count=0), "title": None}, [[]])})
    with pytest.raises(h.SurfaceUnreadable, match="no string 'title'"):
        h.fetch_surface(h.SurfaceRef(REPO, "pull", 7), cwd=Path("."), runner=gh)


def test_the_bag_SAYS_what_the_harvest_covered_and_when(journal: Path) -> None:
    bag = _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head(count=1), [[_comment(11, "x")]])})
    report = _harvest(journal, gh, (PR,), clock=lambda: "2026-09-12T12:00:00Z")

    tags = [v for label, v in read_tag_file(bag.info_path) if label == h.LABEL_HARVEST]
    assert tags == [f"2026-09-12T12:00:00Z {PR} comments=1/1 body=captured bytes=24"]

    indexes = h.read_harvest_indexes(bag.path)
    assert len(indexes) == 1
    index = indexes[0]
    assert index["run_id"] == "run-1" and index["fleet_login"] == ME
    surface, = index["surfaces"]
    assert surface["harvested_at"] == "2026-09-12T12:00:00Z"
    assert surface["captured"] is True
    assert surface["comments_harvested"] == surface["comments_on_surface"] == 1
    assert surface["title"]["event_id"] == report.surfaces[0].title_event
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
    assert len(both) == 6 and len(dedupe_on_identity(both)) == 3


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
    title_event, body_event = _events(report.writer_dir)
    assert report.ok and body_event.content == "" and title_event.content == "the PR title"


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


def test_a_TITLE_append_that_became_a_gap_makes_the_harvest_NOT_ok(
        journal: Path, monkeypatch) -> None:
    """`HarvestReport.ok` requires the title event exactly as it requires the
    body's — a surface whose headline did not land is not a captured surface.
    The append is failed for the `:title` path ALONE, the way `ENOSPC` would
    fail one write and not the next, so the gap record itself still lands."""
    import errno
    from modules.journal.emit import Emitter
    real_append = Emitter._append

    def failing_title_append(self, event):
        # The gap record is filed under the SAME write path, so the failure is
        # keyed on the completion alone — otherwise the record of the loss
        # would be lost with it, which is case (d) and a different test.
        if event.kind is EventKind.COMPLETION and event.write_path.endswith(":title"):
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_append(self, event)

    monkeypatch.setattr(Emitter, "_append", failing_title_append)
    bag = _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head(count=1), [[_comment(11, "x")]])})
    report = _harvest(journal, gh, (PR,))

    assert not report.ok
    surface, = report.surfaces
    assert surface.captured and surface.title_event is None
    assert surface.body_event is not None and surface.comments_harvested == 1
    kinds = [e.kind for e in _events(report.writer_dir)]
    assert kinds == [EventKind.GAP, EventKind.COMPLETION, EventKind.COMPLETION]
    assert bag.incomplete
    entry, = h.read_harvest_indexes(bag.path)[0]["surfaces"]
    assert entry["title"]["event_id"] is None
    # The figure counts what the surface HELD, gapped title included — the
    # gap record beside it carries the 12 lost bytes, not this field.
    assert surface.bytes_harvested == entry["bytes_harvested"] == 12 + 11 + 1
    assert "title (GAP)" in report.as_note()


def test_the_harvest_CONTINUES_past_an_unreadable_surface(journal: Path) -> None:
    _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head("pr", count=0), [[]])})
    report = _harvest(journal, gh, (f"https://github.com/{REPO}/issues/404", PR))
    assert [s.captured for s in report.surfaces] == [False, True]
    kinds = [e.kind for e in _events(report.writer_dir)]
    assert kinds == [EventKind.GAP, EventKind.COMPLETION, EventKind.COMPLETION]


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
    assert kinds == [EventKind.COMPLETION, EventKind.COMPLETION,
                     EventKind.REDACTION_PLACEHOLDER, EventKind.COMPLETION]
    assert secret not in (report.writer_dir / EVENTS_FILE).read_text(encoding="utf-8")
    assert "github-token" in events[2].content
    assert events[3].content.startswith("token is [FILTERED")
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
    return h.Snapshot(ref=h.SurfaceRef(REPO, "pull", 7), url=PR, title="t", author=ME,
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


def test_a_GAPPED_comment_DELETED_since_is_still_a_miss_not_a_vanishing() -> None:
    """The one shape the first cut sorted into NO set: seen, lost, then deleted.

    `then` was built only from comments with an event, so a gapped comment
    absent from the surface now was in neither `then` nor `now` and the
    verdict read OK over a bag that had lost it. The index says the harvest
    saw it; the record does not hold it; that is a miss whatever the surface
    did afterwards.
    """
    at = "2026-09-12T12:00:00Z"
    kept = _comment(1, "x", created="2026-09-12T11:00:00Z")
    lost = _comment(2, "y", created="2026-09-12T11:30:00Z")
    entry = _index_entry(at, kept, lost)
    entry["comments"][1]["event_id"] = None
    rec = h.reconcile_surface(entry, _snapshot(kept))       # 2 is gone now
    assert rec.missed == (2,) and rec.deleted_since == () and not rec.ok, (
        f"a comment the harvest saw and lost vanished from the reconciliation: {rec}")


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
    monkeypatch.setattr("modules.journal.harvest_activities.origin_remote",
                        lambda repo_root: f"git@github.com:{REPO}.git")
    report = harvest_github_surfaces(run_id="run-1", repo_root=journal,
                                     refs=("7", None), journal_root=journal,
                                     runner=gh)
    assert report.ok
    assert gh.calls[0] == ["api", "user", "--jq", ".login"]
    assert f"harvest: {PR} — title + body + 1/1 comments" in capsys.readouterr().out


def test_the_activity_REFUSES_a_run_id_with_no_bag_before_touching_the_network(
        journal, monkeypatch):
    gh = FakeGh({})
    monkeypatch.setattr("modules.journal.harvest_activities.origin_remote",
                        lambda repo_root: f"git@github.com:{REPO}.git")
    with pytest.raises(h.HarvestError, match="resolves to no bag"):
        harvest_github_surfaces(run_id="ghost", repo_root=journal, refs=("7",),
                                journal_root=journal, runner=gh)
    assert gh.calls == [], (
        f"`gh` was launched for a run with no bag — the refusal must cost "
        f"nothing and touch nothing, and the login probe is a request: {gh.calls}")


def test_the_activity_needs_NO_repository_slug_when_every_ref_is_a_URL(journal,
                                                                       monkeypatch):
    _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head(count=0), [[]])})
    monkeypatch.setattr("modules.journal.harvest_activities.origin_remote",
                        lambda repo_root: "")                # no origin remote
    report = harvest_github_surfaces(run_id="run-1", repo_root=journal,
                                     refs=(None, PR), journal_root=journal, runner=gh)
    assert report.ok


# --- Phase 3 case (d): the durable report is dispatched from here ------------------

class _Reporter:
    """A fake case-(d) poster. Records what it was handed; posts nowhere."""

    def __init__(self, address: str = f"{PR}#issuecomment-999") -> None:
        self.calls: list[tuple] = []
        self.address = address

    def __call__(self, failure, surface_url, repo_root, bag_path) -> str:
        self.calls.append((failure, surface_url, repo_root, bag_path))
        return self.address


def _in_a_finally(fn, exc: BaseException):
    """Run `fn` the way every entrypoint runs the harvest: in the `finally` of a
    `try` whose body raised `exc`. Returns what `fn` returned; `exc` propagates."""
    box: list = []
    try:
        raise exc
    finally:
        box.append(fn())


def test_a_JournalUnwritable_IN_FLIGHT_posts_the_durable_report_and_harvests_NOTHING(
        journal, monkeypatch, capsys) -> None:
    """The run died of case (d); the harvest is the actor that says so durably.

    Three properties. The reporter is handed the in-flight failure, the FIRST
    addressable ref (the dispatched PR before the reported one), and the bag's
    path. Nothing is written into the bag — its `incomplete` flag just failed
    to land, and a harvest that appended would produce a bag that lost data and
    reads as complete. And `gh` is never launched: the journal is gone, the
    surface can wait for the next harvest.
    """
    from modules.journal import emit as emitmod
    from modules.journal.emit import JournalUnwritable

    bag = _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head(count=1), [[_comment(11, "x")]])})
    monkeypatch.setattr("modules.journal.harvest_activities.origin_remote",
                        lambda repo_root: f"git@github.com:{REPO}.git")
    reporter = _Reporter()
    failure = JournalUnwritable("JOURNAL-UNWRITABLE: root gone")

    with emitmod.reporting_case_d_through(reporter), pytest.raises(JournalUnwritable):
        _in_a_finally(lambda: harvest_github_surfaces(
            run_id="run-1", repo_root=journal, refs=(None, "7", PR),
            journal_root=journal, runner=gh), failure)

    assert reporter.calls == [(failure, PR, journal, bag.path)]
    assert gh.calls == [], "the journal is gone; nothing was fetched into it"
    assert not (bag.payload_dir / h.HARVEST_WRITER).exists(), "nothing was written"
    assert not bag.incomplete, "nothing flagged either — the flag is what failed"
    err = capsys.readouterr().err
    assert "durable report posted at" in err and reporter.address in err


def test_a_ROOT_that_is_GONE_cannot_preempt_the_in_flight_report(
        journal, monkeypatch, capsys) -> None:
    """The in-flight check runs before the root is resolved, and this is why.

    The harvest sits in every entrypoint's `finally` while the failure that
    ended the run propagates. Anything that raises between the start of the
    activity and the report REPLACES that failure — and when the journal root
    is what is gone, `resolve_journal_root` is exactly such a thing. So on the
    in-flight path the root is not resolved: the bag is named from the
    caller's `journal_root` or not at all, the report is posted with `bag: -`,
    and the exception that reaches the entrypoint is the JournalUnwritable
    that ended the run, not a JournalRootError about the harvest's own lookup.
    """
    from modules.journal import emit as emitmod
    from modules.journal.emit import JournalUnwritable
    from modules.journal.root import JournalRootError

    def _gone(**kwargs):
        raise JournalRootError("the journal root is not there")

    monkeypatch.setattr("modules.journal.harvest_activities.resolve_journal_root", _gone)
    monkeypatch.setattr("modules.journal.harvest_activities.load_journal_config",
                        lambda path: {})
    monkeypatch.setattr("modules.journal.harvest_activities.origin_remote",
                        lambda repo_root: f"git@github.com:{REPO}.git")
    reporter = _Reporter()
    failure = JournalUnwritable("JOURNAL-UNWRITABLE: root gone")

    with emitmod.reporting_case_d_through(reporter), pytest.raises(JournalUnwritable) as raised:
        _in_a_finally(lambda: harvest_github_surfaces(
            run_id="run-1", repo_root=journal, refs=(PR,),
            journal_root=None, runner=FakeGh({})), failure)

    assert raised.value is failure, "the harvest's own lookup replaced the run's failure"
    assert reporter.calls == [(failure, PR, journal, None)]


def test_the_harvest_s_OWN_case_d_posts_the_report_and_RAISES(
        journal, monkeypatch, capsys) -> None:
    """The journal died between the workflow's last emit and this call.

    Induced the way `test_journal_emit` induces case (d): the `incomplete`
    flag's file is made unwritable, so a gap cannot be recorded. The report is
    posted, and the failure then reaches the entrypoint's handler — the
    process channel carries it too.
    """
    import os
    from modules.journal import emit as emitmod
    from modules.journal.emit import JournalUnwritable
    if os.geteuid() == 0:
        pytest.skip("a mode-induced refusal does not bind uid 0")

    bag = _bag(journal)
    gh = FakeGh({})                                    # the surface is a 404 → gap
    monkeypatch.setattr("modules.journal.harvest_activities.origin_remote",
                        lambda repo_root: f"git@github.com:{REPO}.git")
    reporter = _Reporter()
    bag.info_path.chmod(0o400)
    try:
        with emitmod.reporting_case_d_through(reporter), \
                pytest.raises(JournalUnwritable) as raised:
            harvest_github_surfaces(run_id="run-1", repo_root=journal, refs=(PR,),
                                    journal_root=journal, runner=gh)
    finally:
        bag.info_path.chmod(0o600)
    assert reporter.calls == [(raised.value, PR, journal, bag.path)]


def test_with_NO_reporter_registered_the_process_channel_is_named_as_the_only_one(
        journal, monkeypatch, capsys) -> None:
    from modules.journal import emit as emitmod
    from modules.journal.emit import JournalUnwritable
    from modules.journal.harvest_activities import report_case_d_durably

    with emitmod.reporting_case_d_through(None):
        posted = report_case_d_durably(JournalUnwritable("x"), refs=(PR,),
                                       repo_root=journal, bag_path=None,
                                       default_repo=REPO)
    assert posted == ""
    assert "no case-(d) reporter is registered" in capsys.readouterr().err


def test_with_NO_addressable_ref_the_report_has_nowhere_to_go_and_says_so(
        journal, capsys) -> None:
    """A run dispatched against no PR that died before creating one."""
    from modules.journal import emit as emitmod
    from modules.journal.emit import JournalUnwritable
    from modules.journal.harvest_activities import report_case_d_durably

    reporter = _Reporter()
    with emitmod.reporting_case_d_through(reporter):
        posted = report_case_d_durably(JournalUnwritable("x"),
                                       refs=(None, "", "not-a-ref"),
                                       repo_root=journal, bag_path=None,
                                       default_repo=None)
    assert posted == "" and reporter.calls == []
    err = capsys.readouterr().err
    assert "cannot carry the durable report" in err
    assert "names no surface" in err


# --- Phase 3 requirement 11: the harvest READS the durable line back ---------------

def test_a_surface_carrying_the_MARKER_is_surfaced_in_the_note_and_the_index(
        journal) -> None:
    """The reader for case (d)'s durable working-record line.

    `unwritable_journal_in_text` applied to every body the harvest reads — the
    PR body and each comment — so a posted report is SURFACED, in the note an
    operator reads beside the banner and in the index the reconcile tool
    reads, rather than stored beside a hundred other comments.
    """
    from modules.journal.emit import UNWRITABLE_JOURNAL_MARKER

    bag = _bag(journal)
    report_line = f"**{UNWRITABLE_JOURNAL_MARKER}** — this run's journal could not be written"
    gh = FakeGh({f"{REPO}#7": (_head(count=2), [[
        _comment(11, "an ordinary review comment"),
        _comment(12, report_line),
    ]])})
    report = _harvest(journal, gh, (PR,))

    surface, = report.surfaces
    assert surface.unwritable_journal_reports == 1
    note = report.as_note()
    assert "carries 1 JOURNAL-UNWRITABLE report(s)" in note
    entry, = h.read_harvest_indexes(bag.path)[0]["surfaces"]
    assert entry["unwritable_journal_reports"] == 1


def test_a_surface_WITHOUT_the_marker_is_not_flagged(journal) -> None:
    """The control: an ordinary surface reports zero and the note says nothing."""
    _bag(journal)
    gh = FakeGh({f"{REPO}#7": (_head(count=1), [[_comment(11, "ordinary")]])})
    report = _harvest(journal, gh, (PR,))
    assert report.surfaces[0].unwritable_journal_reports == 0
    assert "JOURNAL-UNWRITABLE" not in report.as_note()
