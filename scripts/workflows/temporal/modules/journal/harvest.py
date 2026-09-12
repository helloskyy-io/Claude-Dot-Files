"""The post-exit harvest — what a run wrote to GitHub, fetched after it ended.

PHASE 10 OF THE PERSISTENT MEMORY PROTOCOL, and it is the other half of the
emit rule. Phase 3 wraps every place FLEET CODE writes to a store, so the write
and its journal entry happen together. A child that runs `gh pr comment
--body-file …` because a prompt told it to has no call site to wrap: the
instruction is a sentence in a prompt, and the process that carried it out has
exited before anything could react. **And those are the writes this component
exists for** — the pull-request body, the decision log, the reflection comment
are where the reasoning lives. A record holding every file write and none of the
prose answers *what changed* and never *why*.

So this module READS THE DESTINATION INSTEAD OF THE PATH. Once a child has
finished, a parent invokes `harvest_activities.harvest_github_surfaces`, which
asks each GitHub surface the run wrote to what it holds now and emits every
body verbatim into the run's bag on Phase 3's contract — `Destination(store=
"github", address=<the object's URL>)`, a `COMPLETION` with no prior intent,
which is the typed shape `Emitter.unpairable_write` already names for this case.
No second contract, no new event kind.

## Harvest, not intercept — the alternative is named so it is not re-derived

The obvious alternative is to route every model-issued `gh` through a
fleet-owned wrapper. It is rejected, and the reason would otherwise be
rediscovered mid-build: **an interception is only as complete as the set of
paths it covers, and the model chooses its own paths.** This fleet runs with
permissions bypassed; a child that reaches the API through `curl`, a differently
spelled command, or a tool that did not exist when the wrapper was written
bypasses it — SILENTLY, because the wrapper's own view is that nothing was
written. The harvest is complete with respect to *what actually landed*,
whatever route it took. Its failure mode is a WINDOW, bounded and measurable,
and a bounded measurable gap is strictly better than an unbounded invisible one.
`reconcile_surface` below is that measurement.

## What is in scope and what is deliberately not

IN: the pull request this run opened or was dispatched against — its body and
every comment on it — and any issue the caller can name. A review verdict this
fleet posts is an ordinary comment (`gh pr comment`, the `pr_review:` block), so
it is covered by the comment arm and needs no arm of its own.

OUT: **GitHub's computed review state** — approvals, requested changes, merge
status, checks. Nothing a run *authored*; a service's derived view that changes
after the run has ended, with no moment at which capturing it would be
capturing a write.

⚠ ALSO OUT, BY LIMIT RATHER THAN BY DESIGN: **issues the run authored that its
parent cannot name.** The only issue-authoring path in the fleet today is the
reviewer's `gh issue create --label tracked-intake`, and `ReviewResult` carries
no issue numbers — the intake body carries `filed_by: review-pr` and no run id.
A time-and-author search would attribute one concurrent run's intake to another
run's bag, which is the *confidently wrong about authorship* failure this
module's docstring warns about below. So the issue arm is built, tested, and
REFERENCE-DRIVEN: it harvests an issue when handed its URL, and no production
caller can hand it one yet. The remedy is an identity on the intake — the run id
in its frontmatter — which is a prompt change plus a search key, not a harvest
change.

## The window, and the surface being mutable

A comment posted AFTER the harvest ran is not captured. That is the window, and
r3 requires it stated, bounded and measured rather than assumed small:

  * it OPENS when the child exits and CLOSES at `harvested_at`, which is the
    instant the surface was read — recorded on the `Journal-Harvest` tag and in
    the index beside the events;
  * the bag SAYS what its harvest covered: one tag line per surface, and
    `HARVEST_INDEX_FILE` in the harvest writer's own subfolder naming every
    comment id, the event that holds it, its author and both timestamps;
  * `reconcile_surface` re-reads the surface later and counts: comments
    harvested against comments the surface holds NOW, split into those posted
    inside the window and captured, those posted after it (the window's cost),
    and those posted inside it and NOT captured — which is a harvest defect and
    the only one of the three that fails the check.

⚠ A HARVESTED COMMENT MAY HAVE BEEN EDITED OR DELETED BEFORE THE HARVEST RAN.
GitHub comments are mutable and this record is not — which is the argument for
harvesting them at all. What the record holds is what the surface held at
`harvested_at`, and the bag says so. The vendor facts this turns on, looked up
rather than remembered (docs.github.com, fetched 2026-09-12): an edit changes
`updated_at` and leaves `created_at`, so `edited` is `updated_at != created_at`;
a deletion returns 204 and the comment is simply absent from the list — there
is no tombstone; `per_page` is capped at 100; `gh api --paginate --slurp`
returns an array of pages; and the primary limit is 5,000 authenticated
requests per hour, against which one surface costs two.

## Attribution, and its one stated hole

`Provenance` is decided per body from the author login: the fleet's own login
is `FLEET_AUTHORED`, anything else is `FETCHED` — external text this fleet did
not compose, which is the phase doc's own description of a PR comment. **On this
fleet the operator and the fleet share ONE GitHub identity**, so a comment the
operator typed by hand under that login is recorded as fleet-authored. Stated
rather than papered over: the field cannot separate two authors who present the
same credential, and nothing short of a second account changes that.

The full reasoning is `phase10_the_model_issued_harvest.md` under
`/opt/skyy-net/skyynet-master-planning/development/edge-assistant/persistent-memory-protocol/`.
Its CONSUMER is Phase 6's evidence sweep, named there and in that phase's
producer/consumer table — this module produces the prose that sweep reads.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .bag import BAG_INFO_FILE, BAGIT_FILE, Bag, utc_now, validated_run_id
from .emit import Emitter
from .events import Destination, GapClass, Provenance

__all__ = ["HarvestError", "SurfaceUnreadable", "SurfaceRef", "Comment",
           "Snapshot", "HarvestedSurface", "HarvestReport", "Reconciliation",
           "parse_ref", "surface_refs", "repo_slug_of", "fetch_surface",
           "resolve_bag", "harvest_run", "read_harvest_indexes",
           "reconcile_surface", "render_reconciliation",
           "GH_TIMEOUT_SECONDS", "PER_PAGE", "LABEL_HARVEST",
           "HARVEST_WRITER", "HARVEST_INDEX_FILE", "HARVEST_INDEX_SCHEMA"]

#: The wall-clock ceiling on one `gh api` read. Bounded here rather than via
#: `assistant_activities.run_bounded` for the reason `journal_activities._git`
#: gives: this package is the lower layer and does not import the assistant
#: tree. Sixty seconds is generous for two requests and is the difference
#: between a degraded endpoint costing a minute and costing the run.
GH_TIMEOUT_SECONDS = 60.0

#: The documented maximum for `per_page` on the issue-comments endpoint. Asked
#: for explicitly, because the documented DEFAULT is 30 and a harvest that
#: relied on it would page four times as often for nothing.
PER_PAGE = 100

#: The bag-info tag one harvested surface leaves — r3(b), *the bag says what
#: its harvest covered and when it ran*. Declared in `bag.DESCRIPTIVE_JOURNAL_
#: LABELS` and written through `Bag.add_tag`, which is the one sanctioned
#: writer of a tag line.
LABEL_HARVEST = "Journal-Harvest"

#: The harvest emits as a WRITER of its own, in its own payload subfolder, for
#: the reason every writer has one: its events must not interleave into a
#: member's file. A second harvest of the same run lands in `harvest-2`, and
#: dedupe-on-identity collapses the duplicates on read.
HARVEST_WRITER = "harvest"

#: The per-harvest index, written into the harvest writer's subfolder beside
#: its `events.jsonl`. It carries NO BODIES — those are on the events, verbatim
#: — only what a later reconciliation needs: which comment id landed on which
#: event, its author, both timestamps, and the instant the surface was read.
HARVEST_INDEX_FILE = "index.json"
HARVEST_INDEX_SCHEMA = 1

#: What the harvest launches `gh` through. Injected so the unit tier can drive
#: every branch of the fetch without a network; the default is the real thing.
Runner = Callable[[list[str]], subprocess.CompletedProcess]


class HarvestError(RuntimeError):
    """The harvest could not run at all — a precondition, never a surface.

    `RuntimeError` so it joins the `except RuntimeError` every entrypoint already
    carries. THE RUN STOPS HERE (r2): a run id that resolves to no bag means
    there is nowhere to write, and writing into a guessed bag would record one
    run's prose as another's — the one thing worse than no record.
    """


class SurfaceUnreadable(RuntimeError):
    """One GitHub surface could not be read. Recorded as a gap; the run continues.

    The message is operator-facing and reaches the console and the harvest
    report. It NEVER reaches the journal: the gap event carries
    `GapClass.SURFACE_UNREADABLE` and the surface's address, for the reason
    `events.GapClass` gives — a `why` derived from a reply is a side channel.
    """


# ---------------------------------------------------------------------------
# Surface references — what a caller hands the harvest, and what it becomes
# ---------------------------------------------------------------------------

# `\A…\Z`, never `^…$`: `test_journal_regex_anchors` refuses `$` in this package
# because it matches before a trailing newline. The repo halves refuse `/` and
# whitespace, the kind is one of the two GitHub spells, the number is digits,
# and anything after the number — a `#issuecomment-…` fragment, a `/files`
# tail — is accepted and discarded, because a comment URL still names its PR.
_SURFACE_URL = re.compile(
    r"\Ahttps://github\.com/([^/\s]+)/([^/\s]+)/(pull|issues)/([0-9]+)(?:[#?/].*)?\Z",
    re.S)
_BARE_NUMBER = re.compile(r"\A#?([0-9]+)\Z")
_SLUG_RE = re.compile(r"\A[^/\s]+/[^/\s]+\Z")


@dataclass(frozen=True)
class SurfaceRef:
    """One GitHub surface: a pull request or an issue, in a named repository.

    THE REPOSITORY IS PART OF THE REFERENCE, because a run can write to more
    than one — `plan_project` opens its PR in the planning repo while its
    dispatch may sit in another — and a bare number is meaningless without it.
    `gh api repos/<repo>/…` addresses the object by slug, so the harvest is
    independent of which checkout it happens to run from.
    """

    repo: str
    kind: str      # "pull" | "issue" — the two GitHub spells them differently
    number: int

    @property
    def url(self) -> str:
        segment = "pull" if self.kind == "pull" else "issues"
        return f"https://github.com/{self.repo}/{segment}/{self.number}"

    @property
    def write_path(self) -> str:
        """The event's `write_path` stem. Deterministic per surface, so a second
        harvest of the same run derives the same identities and dedupes."""
        return f"harvest:github:{self.repo}#{self.number}"


def parse_ref(text: str, *, default_repo: str | None) -> SurfaceRef:
    """A URL or a bare number into a `SurfaceRef`, or a refusal naming why.

    A BARE NUMBER IS A PULL REQUEST IN `default_repo`. The one bare number the
    fleet hands this is `--pr N`, which every entrypoint documents as a pull
    request in the target repo; an issue arrives as a URL or not at all. With
    no default repo a bare number is REFUSED rather than guessed — the run's
    remote could not be read, and inventing a slug would harvest the wrong
    repository's PR N under this run's id.
    """
    stripped = text.strip()
    match = _SURFACE_URL.match(stripped)
    if match:
        owner, name, kind, number = match.groups()
        return SurfaceRef(repo=f"{owner}/{name}",
                          kind="pull" if kind == "pull" else "issue",
                          number=int(number))
    match = _BARE_NUMBER.match(stripped)
    if match:
        if not default_repo:
            raise HarvestError(
                f"surface reference {text!r} is a bare number and this run's "
                f"repository slug could not be established (no readable "
                f"`origin` remote). Refusing to guess which repository's "
                f"#{match.group(1)} to harvest — pass the full URL.")
        return SurfaceRef(repo=default_repo, kind="pull", number=int(match.group(1)))
    raise HarvestError(
        f"surface reference {text!r} is neither a github.com pull/issue URL "
        f"nor a bare number. The harvest reads only what it can address.")


def surface_refs(refs: Iterable[str | None], *,
                 default_repo: str | None) -> tuple[SurfaceRef, ...]:
    """Every distinct surface named by `refs`, in first-seen order.

    `None` AND EMPTY ENTRIES ARE SKIPPED, because that is what a parent holds
    when its run was not dispatched against a PR, or when its child reported no
    URL. A run that produced NO surface is a legitimate harvest of nothing
    (r2: *"including when the run produced several PRs or none"*), and it is
    reported as such rather than refused.
    """
    seen: list[SurfaceRef] = []
    for raw in refs:
        if raw is None or not str(raw).strip():
            continue
        ref = parse_ref(str(raw), default_repo=default_repo)
        if ref not in seen:
            seen.append(ref)
    return tuple(seen)


def repo_slug_of(remote_url: str) -> str | None:
    """`owner/name` out of a github.com remote URL, or None when it is not one.

    The three spellings git actually produces for this host — `git@github.com:
    o/n.git`, `https://github.com/o/n(.git)`, `ssh://git@github.com/o/n.git` —
    and nothing looser: a remote on another host yields None, and the caller
    then refuses bare numbers rather than harvesting from the wrong forge.
    """
    text = remote_url.strip()
    for prefix in ("git@github.com:", "https://github.com/",
                   "ssh://git@github.com/", "http://github.com/"):
        if text.startswith(prefix):
            slug = text[len(prefix):]
            if slug.endswith(".git"):
                slug = slug[:-4]
            slug = slug.rstrip("/")
            return slug if _SLUG_RE.match(slug) else None
    return None


# ---------------------------------------------------------------------------
# The fetch — two requests per surface, shape-checked, bounded
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Comment:
    id: int
    url: str
    author: str
    created_at: str
    updated_at: str
    body: str

    @property
    def edited(self) -> bool:
        """The vendor's representation of an edit: `updated_at` moves,
        `created_at` does not. There is no other flag."""
        return self.updated_at != self.created_at


@dataclass(frozen=True)
class Snapshot:
    """What one surface held at one instant."""

    ref: SurfaceRef
    url: str
    author: str
    created_at: str
    updated_at: str
    body: str
    comment_count: int              # the surface's OWN count — the denominator
    comments: tuple[Comment, ...]
    fetched_at: str


def _run_gh(cwd: Path) -> Runner:
    def run(args: list[str]) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(["gh", *args], cwd=str(cwd),
                                  capture_output=True, text=True,
                                  timeout=GH_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            # ONE REPLY SHAPE FOR THE CALLER, the same conversion `run_bounded`
            # performs one layer up: a timeout is a non-zero reply with a
            # stderr that says so, not a second exception family.
            return subprocess.CompletedProcess(
                exc.cmd, returncode=124, stdout="",
                stderr=f"timed out after {GH_TIMEOUT_SECONDS:.0f}s")
    return run


def _gh_json(runner: Runner, args: list[str], *, expect: type,
             surface: SurfaceRef):
    """One `gh api` reply, parsed and SHAPE-CHECKED, or `SurfaceUnreadable`.

    A NON-ZERO EXIT, A NON-JSON BODY AND A WRONG SHAPE ARE ONE FAILURE CLASS
    HERE. `gh` exits 1 on a 404 with the API's message on stderr; a truncated
    reply is valid-looking text that is not JSON; a scalar is JSON that is not
    the object asked for. Each would otherwise surface as a different
    exception type past a handler written for one of them — the class this
    fleet's `gh_json` already closes — so all three become the one typed
    refusal the gap path is written against.
    """
    reply = runner(args)
    if reply.returncode != 0:
        raise SurfaceUnreadable(
            f"{surface.url}: `gh {' '.join(args)}` exited "
            f"{reply.returncode} — {reply.stderr.strip()[:200]}")
    try:
        parsed = json.loads(reply.stdout)
    except ValueError as exc:
        raise SurfaceUnreadable(
            f"{surface.url}: `gh {' '.join(args)}` replied with something "
            f"that is not JSON ({exc})") from exc
    if not isinstance(parsed, expect):
        raise SurfaceUnreadable(
            f"{surface.url}: `gh {' '.join(args)}` replied with "
            f"{type(parsed).__name__}, not {expect.__name__}")
    return parsed


def _str_field(obj: dict, key: str, *, surface: SurfaceRef,
               what: str) -> str:
    value = obj.get(key)
    if value is None and key == "body":
        # A PR OPENED WITH NO DESCRIPTION HAS `body: null`, AND THAT IS A REAL
        # STATE — an empty body is recorded as empty, not refused.
        return ""
    if not isinstance(value, str):
        raise SurfaceUnreadable(
            f"{surface.url}: {what} carries no string {key!r} "
            f"(got {type(value).__name__})")
    return value


def _comment_from(obj: object, *, surface: SurfaceRef) -> Comment:
    if not isinstance(obj, dict):
        raise SurfaceUnreadable(
            f"{surface.url}: a comment entry is {type(obj).__name__}, not an object")
    ident = obj.get("id")
    if not isinstance(ident, int):
        raise SurfaceUnreadable(f"{surface.url}: a comment carries no integer id")
    user = obj.get("user") or {}
    login = user.get("login") if isinstance(user, dict) else None
    return Comment(
        id=ident,
        url=_str_field(obj, "html_url", surface=surface, what=f"comment {ident}"),
        # A DELETED ACCOUNT LEAVES `user: null` ON ITS COMMENTS — the vendor's
        # ghost. Recorded as a named absence rather than refused: the body is
        # still what the surface holds and is still worth capturing.
        author=login if isinstance(login, str) else "",
        created_at=_str_field(obj, "created_at", surface=surface,
                              what=f"comment {ident}"),
        updated_at=_str_field(obj, "updated_at", surface=surface,
                              what=f"comment {ident}"),
        body=_str_field(obj, "body", surface=surface, what=f"comment {ident}"))


def fetch_surface(ref: SurfaceRef, *, cwd: Path,
                  runner: Runner | None = None,
                  clock: Callable[[], str] = utc_now) -> Snapshot:
    """What `ref` holds right now: its body and every comment, paginated.

    TWO REQUESTS. `repos/{repo}/issues/{n}` answers for a pull request as well
    as for an issue — GitHub's issue object IS the PR's conversation head, and
    it carries the surface's own `comments` count, which is the denominator r3
    asks for and is independent of how the pages came back. Then
    `…/issues/{n}/comments` with `--paginate --slurp`, which the CLI documents
    as *"an array of all pages"*; the pages are flattened here.

    `fetched_at` IS TAKEN BEFORE THE FIRST REQUEST, not after the last. The
    window closes when the surface is READ; a comment that lands between the
    two requests is either in the second reply or later than the stamp, and
    stamping afterwards would call such a comment "inside the window and
    missed" when it was neither.
    """
    run = runner if runner is not None else _run_gh(cwd)
    fetched_at = clock()
    head = _gh_json(run, ["api", f"repos/{ref.repo}/issues/{ref.number}"],
                    expect=dict, surface=ref)
    user = head.get("user") or {}
    login = user.get("login") if isinstance(user, dict) else None
    count = head.get("comments")
    if not isinstance(count, int):
        raise SurfaceUnreadable(
            f"{ref.url}: the surface carries no integer `comments` count, so "
            f"the harvest has no denominator to report against")
    pages = _gh_json(
        run, ["api", "--paginate", "--slurp",
              f"repos/{ref.repo}/issues/{ref.number}/comments?per_page={PER_PAGE}"],
        expect=list, surface=ref)
    comments: list[Comment] = []
    for page in pages:
        if not isinstance(page, list):
            raise SurfaceUnreadable(
                f"{ref.url}: a paginated page is {type(page).__name__}, not a "
                f"list — `--slurp` promises an array of arrays")
        comments.extend(_comment_from(entry, surface=ref) for entry in page)
    return Snapshot(
        ref=ref,
        url=_str_field(head, "html_url", surface=ref, what="the surface"),
        author=login if isinstance(login, str) else "",
        created_at=_str_field(head, "created_at", surface=ref, what="the surface"),
        updated_at=_str_field(head, "updated_at", surface=ref, what="the surface"),
        body=_str_field(head, "body", surface=ref, what="the surface"),
        comment_count=count,
        comments=tuple(comments),
        fetched_at=fetched_at)


# ---------------------------------------------------------------------------
# The harvest itself
# ---------------------------------------------------------------------------

def resolve_bag(journal_root: Path, run_id: str) -> Bag:
    """`run_id` → the existing OPEN bag for it, or a loud refusal. Requirement 2.

    NOT `open_bag`, DELIBERATELY. `open_bag` CREATES when the folder is absent,
    and a harvest that created a bag would be writing a run's prose into a
    folder no run opened — attributed to a run id that may be a typo, a stale
    variable, or another machine's run. This resolves and refuses: the folder
    must exist, must carry both BagIt tag files, and must not be sealed. Each
    refusal names the path it looked at.
    """
    run_id = validated_run_id(run_id)
    path = journal_root / run_id
    if not path.is_dir():
        raise HarvestError(
            f"run id {run_id!r} resolves to no bag: {path} does not exist. The "
            f"harvest writes ONLY into the bag the run opened; it does not "
            f"create one, because a bag it created would attribute this run's "
            f"prose to whatever id it was handed.")
    for name in (BAGIT_FILE, BAG_INFO_FILE):
        if not (path / name).is_file():
            raise HarvestError(
                f"run id {run_id!r} resolves to {path}, which is not a bag: "
                f"{name} is missing. Refusing to write into a folder that no "
                f"`open_run_bag` produced.")
    bag = Bag(path=path, run_id=run_id)
    if bag.lifecycle == "sealed":
        raise HarvestError(
            f"bag {run_id} at {path} is already SEALED. Its manifest is a "
            f"statement about a finished run; appending harvested events under "
            f"it would make that statement false. Nothing in the fleet seals a "
            f"bag before the harvest today, so this is a state to investigate "
            f"rather than route around.")
    return bag


def _provenance(author: str, fleet_login: str | None) -> Provenance:
    if fleet_login and author == fleet_login:
        return Provenance.FLEET_AUTHORED
    return Provenance.FETCHED


@dataclass(frozen=True)
class HarvestedSurface:
    """One surface's harvest — what was captured, and what was not."""

    ref: SurfaceRef
    harvested_at: str
    captured: bool
    #: The event holding the body, or None when the append became a gap.
    body_event: str | None = None
    #: The surface's own count at harvest time — the denominator.
    comments_on_surface: int = 0
    #: `(comment id, event id or None)`, in surface order.
    comment_events: tuple[tuple[int, str | None], ...] = ()
    bytes_harvested: int = 0
    #: Operator-facing detail when `captured` is False. Never in the record.
    failure: str = ""

    @property
    def comments_harvested(self) -> int:
        return sum(1 for _, event in self.comment_events if event is not None)


@dataclass(frozen=True)
class HarvestReport:
    run_id: str
    bag_path: Path
    writer_dir: Path
    ran_at: str
    surfaces: tuple[HarvestedSurface, ...]

    @property
    def ok(self) -> bool:
        """Every surface read, and every body landed. A gap is not ok."""
        return all(s.captured and s.body_event is not None
                   and s.comments_harvested == len(s.comment_events)
                   for s in self.surfaces)

    def as_note(self) -> str:
        """One line per surface, in the shape a parent prints beside its banner."""
        if not self.surfaces:
            return (f"harvest: no GitHub surface named for run {self.run_id} — "
                    f"nothing to capture, recorded as such")
        lines = []
        for s in self.surfaces:
            if not s.captured:
                lines.append(f"harvest: {s.ref.url} NOT READ — gap recorded, "
                             f"bag marked incomplete ({s.failure})")
                continue
            lines.append(
                f"harvest: {s.ref.url} — body"
                f"{'' if s.body_event else ' (GAP)'} + "
                f"{s.comments_harvested}/{s.comments_on_surface} comments, "
                f"{s.bytes_harvested:,} bytes, at {s.harvested_at}")
        return "\n".join(lines)


def harvest_run(*, journal_root: Path, run_id: str, repo_root: Path,
                refs: Iterable[str | None], default_repo: str | None,
                fleet_login: str | None, runner: Runner | None = None,
                clock: Callable[[], str] = utc_now) -> HarvestReport:
    """Fetch every named surface and emit it into `run_id`'s bag. The mechanism.

    ORDER OF OPERATIONS, AND WHY. The bag is resolved FIRST — r2's refusal
    fires before any request is made, so a typo'd run id costs nothing and
    harvests nothing. Then the references are parsed, so an unaddressable one
    is refused before the network is touched. Only then is each surface read,
    in the order given, and each is emitted completely before the next is
    read: a surface that cannot be read becomes a gap and the harvest moves
    on, because the other surfaces are no less real for it.

    EVERY BODY GOES THROUGH `Emitter.unpairable_write`, WHICH IS WHERE THE
    CAPTURE-TIME FILTER LIVES (r6). Harvested bytes are external text; they
    take exactly the path a fleet-authored comment takes, and a filter that
    fires leaves a `redaction_placeholder` beside the event as it would for any
    other write. Nothing here composes a byte for the journal on its own.

    THE INDEX IS WRITTEN LAST, and its absence is therefore meaningful: a
    harvest that died between the events and the index leaves events with no
    index, which `read_harvest_indexes` reports as such rather than inventing.
    """
    bag = resolve_bag(journal_root, run_id)
    targets = surface_refs(refs, default_repo=default_repo)
    emitter = Emitter.for_run(bag, writer=HARVEST_WRITER, journal_root=journal_root)
    ran_at = clock()
    harvested: list[HarvestedSurface] = []
    index_surfaces: list[dict] = []

    for ref in targets:
        try:
            snapshot = fetch_surface(ref, cwd=repo_root, runner=runner, clock=clock)
        except SurfaceUnreadable as exc:
            # r5: NEVER SILENT. A typed gap naming the surface, the bag marked
            # incomplete, and the run continues — the surface's content exists
            # somewhere and did not land, which is case (c) exactly. `lost_bytes`
            # is 0 because the count is UNKNOWN, not because nothing was lost;
            # the closed field set has no "unknown" and the flag is what
            # downstream branches on.
            emitter.record_gap(write_path=ref.write_path,
                               gap_class=GapClass.SURFACE_UNREADABLE,
                               destination=Destination(store="github",
                                                       address=ref.url),
                               lost_bytes=0, detail=str(exc))
            failed = HarvestedSurface(ref=ref, harvested_at=clock(),
                                      captured=False, failure=str(exc))
            harvested.append(failed)
            index_surfaces.append(_index_entry(failed, None))
            continue

        body_event = emitter.unpairable_write(
            write_path=f"{ref.write_path}:body",
            destination=Destination(store="github", address=snapshot.url),
            content=snapshot.body,
            provenance=_provenance(snapshot.author, fleet_login))
        total = len(snapshot.body.encode("utf-8"))
        comment_events: list[tuple[int, str | None]] = []
        for comment in snapshot.comments:
            event = emitter.unpairable_write(
                write_path=f"{ref.write_path}:comment:{comment.id}",
                destination=Destination(store="github", address=comment.url),
                content=comment.body,
                provenance=_provenance(comment.author, fleet_login))
            comment_events.append((comment.id, event))
            total += len(comment.body.encode("utf-8"))
        surface = HarvestedSurface(
            ref=ref, harvested_at=snapshot.fetched_at, captured=True,
            body_event=body_event, comments_on_surface=snapshot.comment_count,
            comment_events=tuple(comment_events), bytes_harvested=total)
        harvested.append(surface)
        index_surfaces.append(_index_entry(surface, snapshot))
        # THE TAG IS COMPOSED FROM VALUES THIS MODULE VALIDATED — `ref.url` is
        # built from a regex-matched slug and digits, never from the reply's
        # `html_url` — because a tag line is the one place an externally
        # supplied string can forge a lifecycle flag, and `add_tag` refuses a
        # folded value rather than trusting the caller.
        bag.add_tag(LABEL_HARVEST,
                    f"{snapshot.fetched_at} {ref.url} "
                    f"comments={surface.comments_harvested}/{snapshot.comment_count} "
                    f"body={'captured' if body_event else 'gap'} "
                    f"bytes={total}")

    index = {
        "schema": HARVEST_INDEX_SCHEMA,
        "run_id": run_id,
        "ran_at": ran_at,
        "fleet_login": fleet_login or "",
        "surfaces": index_surfaces,
    }
    relpath = (emitter.writer_dir / HARVEST_INDEX_FILE).relative_to(bag.path)
    bag.write_payload(relpath.as_posix(),
                      json.dumps(index, sort_keys=True, ensure_ascii=False,
                                 indent=1))
    return HarvestReport(run_id=run_id, bag_path=bag.path,
                         writer_dir=emitter.writer_dir, ran_at=ran_at,
                         surfaces=tuple(harvested))


def _index_entry(surface: HarvestedSurface, snapshot: Snapshot | None) -> dict:
    entry: dict = {
        "url": surface.ref.url,
        "repo": surface.ref.repo,
        "kind": surface.ref.kind,
        "number": surface.ref.number,
        "harvested_at": surface.harvested_at,
        "captured": surface.captured,
        "comments_on_surface": surface.comments_on_surface,
        "comments_harvested": surface.comments_harvested,
        "bytes_harvested": surface.bytes_harvested,
    }
    if snapshot is None:
        return entry
    by_id = {cid: event for cid, event in surface.comment_events}
    entry["body"] = {
        "event_id": surface.body_event,
        "bytes": len(snapshot.body.encode("utf-8")),
        "author": snapshot.author,
        "created_at": snapshot.created_at,
        "updated_at": snapshot.updated_at,
        "edited": snapshot.updated_at != snapshot.created_at,
    }
    entry["comments"] = [{
        "id": c.id,
        "url": c.url,
        "event_id": by_id.get(c.id),
        "bytes": len(c.body.encode("utf-8")),
        "author": c.author,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "edited": c.edited,
    } for c in snapshot.comments]
    return entry


# ---------------------------------------------------------------------------
# The reconciliation — r3(c)'s measurement and r4's per-run check
# ---------------------------------------------------------------------------

def read_harvest_indexes(bag_path: Path) -> list[dict]:
    """Every harvest index in a bag, oldest writer first.

    A bag harvested twice holds `harvest/` and `harvest-2/`; both are read, and
    a reconciliation over the LATEST is what answers "what does the record
    hold", because the later harvest saw everything the earlier one did plus
    whatever landed between. A writer subfolder with events and no index is
    reported by its absence here — the caller sees fewer indexes than
    subfolders — rather than reconstructed.
    """
    payload = bag_path / "data"
    found: list[tuple[int, dict]] = []
    if not payload.is_dir():
        return []
    for child in payload.iterdir():
        if not child.is_dir():
            continue
        if child.name != HARVEST_WRITER and \
                not child.name.startswith(f"{HARVEST_WRITER}-"):
            continue
        index_path = child / HARVEST_INDEX_FILE
        if not index_path.is_file():
            continue
        ordinal = 1 if child.name == HARVEST_WRITER else int(child.name.rsplit("-", 1)[1])
        found.append((ordinal, json.loads(index_path.read_text(encoding="utf-8"))))
    return [index for _, index in sorted(found, key=lambda pair: pair[0])]


@dataclass(frozen=True)
class Reconciliation:
    """One surface's harvest, compared against what the surface holds NOW.

    FOUR DISJOINT SETS OVER THE UNION OF THEN AND NOW, so every comment is in
    exactly one and the counts add up to something a reader can check:

      * `captured`       — on the surface now AND in the record.
      * `late`           — on the surface now, created AFTER `harvested_at`,
                           not in the record. THE WINDOW'S COST. Expected,
                           counted, never a failure.
      * `missed`         — on the surface now, created AT OR BEFORE
                           `harvested_at`, not in the record. A HARVEST DEFECT:
                           the comment was there to be read and was not. The
                           only set that fails the check.
      * `deleted_since`  — in the record, absent from the surface now. The
                           record is what the surface held; this is why it was
                           harvested at all.

    And one overlay: `edited_since`, captured comments whose `updated_at` moved
    after the harvest. The record holds the earlier text, and says so.
    """

    url: str
    harvested_at: str
    comments_on_surface_now: int
    captured: tuple[int, ...]
    late: tuple[int, ...]
    missed: tuple[int, ...]
    deleted_since: tuple[int, ...]
    edited_since: tuple[int, ...]

    @property
    def ok(self) -> bool:
        return not self.missed

    @property
    def harvested(self) -> int:
        return len(self.captured) + len(self.deleted_since)


def reconcile_surface(index_entry: dict, now: Snapshot) -> Reconciliation:
    """The comparison, pure: an index entry against a fresh snapshot.

    STRING COMPARISON ON ISO-8601 UTC TIMESTAMPS IS ORDER-PRESERVING, because
    both sides are `YYYY-MM-DDTHH:MM:SSZ` at second precision — the vendor's
    format and `utc_now`'s. `<=` rather than `<` on the boundary: a comment
    created in the same second the harvest read the surface was there to be
    read, and calling it late would hide a miss behind a coincidence.
    """
    harvested_at = index_entry["harvested_at"]
    then = {c["id"]: c for c in index_entry.get("comments", [])
            if c.get("event_id") is not None}
    now_by_id = {c.id: c for c in now.comments}
    captured, late, missed, edited = [], [], [], []
    for cid, comment in now_by_id.items():
        if cid in then:
            captured.append(cid)
            if comment.updated_at != then[cid]["updated_at"]:
                edited.append(cid)
        elif comment.created_at <= harvested_at:
            missed.append(cid)
        else:
            late.append(cid)
    deleted = [cid for cid in then if cid not in now_by_id]
    return Reconciliation(
        url=index_entry["url"], harvested_at=harvested_at,
        comments_on_surface_now=now.comment_count,
        captured=tuple(captured), late=tuple(late), missed=tuple(missed),
        deleted_since=tuple(deleted), edited_since=tuple(edited))


def render_reconciliation(rec: Reconciliation) -> str:
    """The two r3 figures with their denominators, and the verdict, on stdout."""
    now = rec.comments_on_surface_now
    lines = [
        f"{rec.url}",
        f"  harvested at : {rec.harvested_at}",
        f"  in record    : {len(rec.captured)}/{now} comments the surface holds now",
        f"  late         : {len(rec.late)}/{now} posted after the harvest "
        f"(the window's cost)",
        f"  missed       : {len(rec.missed)}/{now} posted before it and NOT "
        f"captured",
        f"  deleted since: {len(rec.deleted_since)} in the record, gone from "
        f"the surface",
        f"  edited since : {len(rec.edited_since)} in the record, changed on "
        f"the surface",
        f"  verdict      : {'OK' if rec.ok else 'SHORTFALL'}"
        + ("" if rec.ok else f" — comment ids {list(rec.missed)} were on the "
                             f"surface at harvest time and are not in the bag"),
    ]
    return "\n".join(lines)
