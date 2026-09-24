"""The read interface over the run journal — enumerate units, read one, say what it lacks.

Self Improvement Phase 1 (`phase1_the_reader.md`), the checklist's third box:
*"enumerate evidence units, read one unit, report what a unit does not
contain."* THIS MODULE IS THE ONLY PLACE THE READER KNOWS A BAG IS A DIRECTORY.
Everything above it — `journal_baseline.py` today, the recurrence checks of
Phase 2 next — gets `UnitRef`s and `Unit`s and never a path, a glob or a
directory walk. `test_journal_baseline.py` asserts that of the figure module by
AST, so a figure that starts opening files fails a test rather than a review.
**A NEW CONSUMER MODULE IS NOT COVERED UNTIL IT IS ADDED TO THAT TEST'S
`_CONSUMERS`** — the guard scans the modules it names, not the directory.

WHY AN INTERFACE AND NOT A FUNCTION. Phase 2 r4 requires every rate it computes
to read "through the reader's interface", and its checklist verifies *"the
tool imports no path enumeration of its own"*. A second enumeration is the
second carrier this component exists to prevent; the moment the journal grows
a second shape (PMP Phase 7's shared bucket), exactly one module learns it.

WHAT THIS IMPORTS AND DOES NOT RE-DERIVE — each is producer-owned:

  * completeness — `common/journal/profile.py`'s `assess_completeness`. The
    reader carries NO copy of that predicate (phase doc r4). The verdict and
    reasons are handed up verbatim.
  * a bag's lifecycle flags — `bag.bag_state`, the one place `bag-info.txt`
    labels become `incomplete` and `gaps`.
  * which directories are bags and which files are their events —
    `bag.journal_bags` and `bag.events_files`, the rules replay reads by, so
    the gapped figure r4 says IS replay's cannot drift from it.
  * an event's shape — `events.decode_event`, which refuses a schema version it
    has no upcaster for. A refused line is COUNTED on the unit, never skipped.
  * the sub-agent tool names and the run-log member set — `run_log.py`.

UNTRUSTED INPUT (phase doc r5). A transcript carries whatever an earlier run
ingested — PR bodies, fetched pages, tool output. This module PARSES it for
typed facts (counts, numbers, enum values) and hands up nothing else from the
transcript. Harvested PR text is handed up raw because Phase 2 reads it, and
`HarvestItem` says so on the type. Nothing here calls a model, and nothing
here writes: every open below is a read.

PHASE 2's HALF (`phase2_the_self_report_and_recurrence_measured.md` r4). Two
more reads, each on its own method so the baseline never pays for them:
`review_records` hands up a `review-pr` pass's typed finding ids — model-
authored slugs, marked untrusted on the type exactly as `HarvestItem` is — and
`threads` hands up the harvested pull-request conversations, grouped by
surface. `forge_thread` is the one read that is not the journal's: a run that
predates the harvest has no thread in its bag, and r4 reads those from the
forge through the harvest's OWN fetch (`harvest.fetch_surface`), so the two
sources cannot disagree about what a thread is. Every `Thread` says which
source it came from.
"""

from __future__ import annotations

import datetime as _dt
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_TEMPORAL = _HERE.parents[1] / "workflows" / "temporal"
if str(_TEMPORAL) not in sys.path:
    sys.path.insert(0, str(_TEMPORAL))

from common.journal.bag import (BAG_INFO_FILE, MANIFEST_FILE, BagError,  # noqa: E402
                                 bag_state, events_files, journal_bags, read_tag_file)
from common.journal.events import (EventError, EventKind,  # noqa: E402
                                    decode_event, dedupe_on_identity)
from common.journal.harvest import (HarvestError, SurfaceRef,  # noqa: E402
                                     SurfaceUnreadable, fetch_surface, parse_ref)
from common.journal.journal_activities import load_journal_config  # noqa: E402
from common.journal.profile import (EVENTS, HARVEST_EVENTS,  # noqa: E402
                                     assess_completeness)
from common.journal.root import resolve_journal_root  # noqa: E402
from common.journal.snapshot import SnapshotError, latest_snapshot  # noqa: E402
from common.vocabulary import Disposition, HoldKind  # noqa: E402


def _load_run_log():
    """`run_log.py` by path, registered first — the sibling tools' pattern and
    the reason is theirs: `@dataclass` needs `sys.modules[__module__]`."""
    name = "_run_log_for_journal_evidence"
    spec = importlib.util.spec_from_file_location(name, _HERE / "run_log.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_run_log = _load_run_log()

__all__ = ["JournalEvidence", "UnitRef", "Unit", "ChildRun", "HarvestItem",
           "RotatedOut", "ReviewRecord", "Thread", "open_journal", "forge_thread",
           "JournalEvidenceError", "DISPOSITIONS"]

#: The finding-disposition vocabulary, re-exported so a figure module can bucket
#: a value without importing the workflow tree itself. A disposition outside it
#: is counted as unrecognised and never printed — the value is model-authored.
DISPOSITIONS = tuple(d.value for d in Disposition)

#: Outcome values a `ChildRun` may carry, spelled `merge`, `hold:<kind>` or
#: `undetermined` from the shared vocabulary. Anything else becomes
#: `UNRECOGNISED` AT CONSTRUCTION — the outcome and hold kind are fields of a
#: model-authored record, and a consumer trusting this record's docstring must
#: not be handed their raw text.
OUTCOMES = ("merge", *(f"hold:{k.value}" for k in HoldKind), "undetermined")
UNRECOGNISED = "unrecognised"

#: The transcript's write path and the prefix every run-log member carries —
#: `assistant_activities` writes `run-log:{event_type}` and `cli-transcript`.
TRANSCRIPT_WRITE_PATH = "cli-transcript"
RUN_LOG_PREFIX = "run-log:"

#: The CLI's refusal text when an Edit/Write targets a file not Read (or changed
#: since). The V1 report tabulated exactly these as "Read-before-Edit errors"
#: (`review-mdc-master-planning-2026-07-24.md` § Metrics) — that is the figure
#: `review-runs.sh` reported by hand, and phase doc r10 names it. Matched ONLY
#: on a tool_result the CLI flagged `is_error`, so a non-error result that
#: QUOTES the sentence (a grep of a log) is not counted.
_READ_BEFORE_EDIT = re.compile(r"File has not been read yet|File has been modified since read")

#: A child key is printed. It comes from `run_resources.workflow_key` (a
#: publishable field) or the log file name, and anything that is not the shape
#: of a fleet key is reported as unrecognised rather than echoed.
_KEY_SHAPE = re.compile(r"\A[a-z][a-z0-9-]{0,63}\Z")

#: The child whose `structured_output` carries typed findings.
REVIEW_PR = "review-pr"

#: A harvested item's write path: `SurfaceRef.write_path`'s stem, then the part.
#: The stem is the harvest's (`harvest.SurfaceRef.write_path`); the parts are
#: what `harvest_run` appends — `title`, `body`, `comment:<id>`.
_HARVEST_PATH = re.compile(
    r"\Aharvest:github:(?P<repo>[^#\s/]+/[^#\s/]+)#(?P<n>[0-9]+):"
    r"(?:(?P<part>title|body)|comment:(?P<cid>[0-9]+))\Z")

#: A run nonce — `uuid.uuid4().hex`. A `structured_output.run_id` of any other
#: shape joins nothing and is handed up as "".
_RUN_ID = re.compile(r"\A[0-9a-f]{32}\Z")


class JournalEvidenceError(RuntimeError):
    """The journal root could not be opened for reading."""


@dataclass(frozen=True)
class UnitRef:
    """An opaque handle on one evidence unit. The run id is its only public face."""

    run_id: str
    _location: object  # the interface's own; nothing above reads it


@dataclass(frozen=True)
class ChildRun:
    """One child's run inside a bag, as typed facts parsed from its records.

    Joined on the child's log address — the transcript and its run-log members
    are emitted against the same `destination.address`. Every field is a
    number, a boolean, or a value from a declared vocabulary; no transcript
    text survives into this record.
    """

    child: str                       # workflow key, or "unrecognised"
    date: str                        # YYYY-MM-DD of this run's own earliest event; "" if none is dated
    has_transcript: bool
    has_result: bool
    num_turns: int | None
    total_cost_usd: float | None
    duration_ms: int | None
    duration_api_ms: int | None
    tool_errors: int
    read_before_edit: int            # read-before-edit refusals (V1's figure)
    repeated_reads: int              # Read calls of a (path, range) already Read in the same context
    subagents: int
    # review-pr's typed record and the parent's two computed shadows
    asserted_outcome: str | None     # structured_output outcome, in OUTCOMES or UNRECOGNISED
    dispositions: tuple[str, ...]    # findings[].disposition, each in DISPOSITIONS or UNRECOGNISED
    has_structured_output: bool
    routed_outcome: str | None       # parent_route outcome, in OUTCOMES or UNRECOGNISED
    shadow_parseable: bool | None
    channels_agree: bool | None
    convergence_agrees: bool | None
    has_parent_route: bool
    has_convergence: bool


@dataclass(frozen=True)
class HarvestItem:
    """One harvested surface item. ⚠ `content` IS UNTRUSTED, model- or
    human-authored text from a forge; it is data, and no caller may feed it to
    a model or print it into a committed artifact (`run_log.py` publish rule)."""

    write_path: str
    recorded_at: str
    content: str


@dataclass(frozen=True)
class ReviewRecord:
    """One `review-pr` pass's typed record, as the pass's `result` carried it.

    ⚠ `findings` CARRIES MODEL-AUTHORED `id` SLUGS. They are the join key a
    Phase 2 check needs — a finding is looked up in its pass's `pr_review:`
    block and in later passes by id — and they are data: no caller may print
    one (`run_log.py` publish rule). The disposition beside each is narrowed to
    the shared vocabulary here, as `ChildRun.dispositions` is.
    """

    run_id: str                            # the bag's
    child_run_id: str                      # structured_output.run_id if it is a nonce, else ""
    date: str                              # the child's own earliest event, "" if undated
    repo: str                              # completion_ref's `owner/name`, "" if it names no PR
    pr: int | None
    findings: tuple[tuple[str, str], ...]  # (id, disposition) in record order


@dataclass(frozen=True)
class Thread:
    """One pull request's conversation. ⚠ `body` and every comment's text are
    UNTRUSTED, model- or human-authored forge text — `HarvestItem`'s rule.

    `comments` is ascending by comment id, which GitHub allocates in posting
    order; that order is what lets a reader ask *what had been said BEFORE a
    given comment* without trusting a timestamp inside the text.
    """

    repo: str
    pr: int
    source: str                            # "harvest" or "forge"
    body: str
    comments: tuple[tuple[int, str], ...]  # (comment id, text)


@dataclass(frozen=True)
class Unit:
    """One bag, read. `missing` is what this unit does not contain, stated."""

    run_id: str
    repo: str                        # basename of Journal-Origin-Repo, or "" if absent
    workflow: str                    # Journal-Workflow, or "" if absent
    date: str                        # YYYY-MM-DD
    dated_by: str                    # "event" (earliest recorded_at) or "mtime"
    bytes: int                       # every regular file in the bag
    has_events: bool
    children: tuple[ChildRun, ...]
    harvested: int                   # harvested surface items (title, body, comments)
    gap_events: int                  # events of kind `gap`, parent and harvest streams
    gap_labels: int                  # Journal-Gap lines
    incomplete_flag: bool            # Journal-Incomplete: true
    redactions: int                  # redaction_placeholder events
    undecodable: int                 # lines decode_event refused
    completeness: str                # assess_completeness verdict, verbatim
    completeness_reasons: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def gapped(self) -> bool:
        # THE PRODUCER'S PREDICATE, `rebuild.BagRead.gapped`, term for term —
        # r4 says this count IS PMP Phase 4 r7's figure, so it may not be a
        # wider one. `gap_labels` is reported, not counted: `mark_incomplete`
        # writes a label only beside the flag, and a label-only bag is one the
        # producer does not call gapped. A test holds the two in parity.
        return self.incomplete_flag or self.gap_events > 0


@dataclass(frozen=True)
class RotatedOut:
    """What the latest snapshot says about bags no longer on disk.

    PMP Phase 5 r8 carries gap events from rotated bags into the snapshot, each
    with its originating `run_id`; that id is what lets a gap be counted ONCE
    (PMP Phase 4 r7). `snapshot` is "" when the root holds none.

    WHY THE ROTATED-OUT DENOMINATOR IS READ FROM CARRIED IDS AND NOT FROM
    `bags_at_snapshot`. A bag is removed "entire, with a retention event saying
    so" (Phase 5 § *So a run folder is the unit*), and r8 carries that event
    forward with its `run_id` — so every rotated bag, clean or gapped, leaves
    an id here. `bags_at_snapshot` is a count with no ids, and cannot say WHICH
    of today's bags it already counted. Retention is unbuilt, so today the
    carried set is empty; Phase 5's compacted carry form, when it lands, is
    `latest_snapshot`'s to parse, and this reduction follows it.
    """

    snapshot: str
    carried_run_ids: frozenset[str]
    carried_gap_run_ids: frozenset[str]


class JournalEvidence:
    """The journal as a population of evidence units."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def label(self) -> str:
        """What to print as the source — the root, as a string."""
        return str(self._root)

    def units(self) -> list[UnitRef]:
        """Every bag directly under the root, in run-id order.

        WHICH DIRECTORIES ARE BAGS is `bag.journal_bags` — imported, not
        restated, because `rebuild.read_bags` enumerates by the same function
        and r4's gapped figure IS replay's. A copy here drifted once already:
        it omitted the `validated_run_id` filter replay applies.
        """
        return [UnitRef(bag.name, bag) for bag in journal_bags(self._root)]

    def read(self, ref: UnitRef) -> Unit:
        bag: Path = ref._location  # type: ignore[assignment]
        missing: list[str] = []
        entries: list[tuple[str, str]] = []
        info = bag / BAG_INFO_FILE
        if info.is_file():
            try:
                entries = read_tag_file(info)
            except (BagError, OSError, UnicodeError) as exc:
                missing.append(f"{BAG_INFO_FILE} unreadable ({type(exc).__name__})")
        else:
            missing.append(f"no {BAG_INFO_FILE}")
        tags = dict(entries)
        state = bag_state(manifest_exists=(bag / MANIFEST_FILE).is_file(),
                          info_entries=entries)

        # EVERY WRITER'S STREAM, not the parent's alone. A parent writes
        # `data/events.jsonl`, each member `data/<writer>/events.jsonl`
        # (`Bag.writer_dir`), the harvest `data/harvest/events.jsonl`; replay
        # (`rebuild.read_bags`) reads them all, and a reader that read two
        # fixed names would miss a member's transcript and its gap events —
        # a silently smaller denominator. `has_events` stays the contract's
        # notion: the parent's file, which `assess_completeness` names.
        has_events = (bag / EVENTS).is_file()
        if not has_events:
            missing.append(f"no {EVENTS}")
        harvest_path = bag / HARVEST_EVENTS
        streams = events_files(bag)
        parent, bad_parent = _decode_all([p for p in streams if p != harvest_path])
        harvested, bad_harvest = _decode_all([p for p in streams if p == harvest_path])

        days = [d for d in map(_day, (e.recorded_at for e in parent + harvested)) if d]
        if days:
            date, dated_by = min(days), "event"
        else:
            # A bag with no events carries no clock of its own. The directory's
            # mtime is the one `journal_completeness.py --since` uses, so the
            # two tools place such a bag in the same window.
            date = _dt.datetime.fromtimestamp(bag.stat().st_mtime, _dt.timezone.utc).date().isoformat()
            dated_by = "mtime"

        children = _children(parent)
        for c in children:
            if c.has_transcript and not c.has_result:
                missing.append(f"a {c.child} run's transcript has no result event")
            if not c.has_transcript:
                missing.append(f"a {c.child} run has run-log events and no transcript")

        assessment = assess_completeness(bag)
        repo = tags.get("Journal-Origin-Repo", "")
        return Unit(
            run_id=ref.run_id,
            repo=Path(repo).name if repo else "",
            workflow=tags.get("Journal-Workflow", ""),
            date=date, dated_by=dated_by,
            bytes=_bytes(bag),
            has_events=has_events,
            children=tuple(children),
            harvested=sum(e.kind is EventKind.COMPLETION for e in harvested),
            gap_events=sum(e.kind is EventKind.GAP for e in parent + harvested),
            gap_labels=len(state.gaps),
            incomplete_flag=state.incomplete,
            redactions=sum(e.kind is EventKind.REDACTION_PLACEHOLDER for e in parent + harvested),
            undecodable=bad_parent + bad_harvest,
            completeness=assessment.verdict,
            completeness_reasons=assessment.reasons,
            missing=tuple(missing),
        )

    def harvest(self, ref: UnitRef) -> tuple[HarvestItem, ...]:
        """The harvested PR title, body and comments of one unit, verbatim.

        SEPARATE FROM `read` so a sweep does not hold every thread in memory:
        the baseline needs only the count; Phase 2's reflection sweep needs the
        text, and asks for it one unit at a time.
        """
        path = ref._location / HARVEST_EVENTS  # type: ignore[operator]
        if not path.is_file():
            return ()
        events, _refused = _decode(path)
        return tuple(HarvestItem(e.write_path, e.recorded_at, e.content)
                     for e in events if e.kind is EventKind.COMPLETION)

    def threads(self, ref: UnitRef) -> tuple[Thread, ...]:
        """The harvested surfaces of one unit, each assembled into a `Thread`.

        A harvest item whose write path is not the harvest's shape is not a
        surface part and is not guessed at. A surface harvested with no body
        event (a `body=absent` surface) has body "". WHERE THE SAME COMMENT WAS
        HARVESTED TWICE into one bag (a re-run harvest after an edit), the
        later-recorded text wins — it is what the surface said last.
        """
        parts: dict[tuple[str, int], dict] = {}
        for item in sorted(self.harvest(ref), key=lambda h: h.recorded_at):
            m = _HARVEST_PATH.match(item.write_path)
            if not m:
                continue
            slot = parts.setdefault((m["repo"], int(m["n"])), {"body": "", "comments": {}})
            if m["part"] == "body":
                slot["body"] = item.content
            elif m["cid"]:
                slot["comments"][int(m["cid"])] = item.content
        return tuple(Thread(repo, n, "harvest", slot["body"], tuple(sorted(slot["comments"].items())))
                     for (repo, n), slot in sorted(parts.items()))

    def review_records(self, ref: UnitRef) -> tuple[ReviewRecord, ...]:
        """Every `review-pr` child in the unit that carries a `structured_output`.

        The child is found the way `read` finds it — the parent streams grouped
        on the log address, the key from `run_resources` or the log name — and
        its `result` is the transcript's LAST, as `_Trajectory` reads it. The
        PR is `completion_ref.uri`, parsed by the harvest's own `parse_ref`; a
        reference that is not a github.com PR URL leaves `repo` "" and `pr`
        None, and the record is still handed up so a consumer can count it.
        """
        bag: Path = ref._location  # type: ignore[assignment]
        harvest_path = bag / HARVEST_EVENTS
        parent, _bad = _decode_all([p for p in events_files(bag) if p != harvest_path])
        out = []
        for address, slot in _slots(parent):
            if _child_key(address, slot["members"].get("run_resources")) != REVIEW_PR:
                continue
            result = _result_event(slot.get("transcript"))
            so = (result or {}).get("structured_output")
            if not isinstance(so, dict):
                continue
            repo, pr = _pull_of(so.get("completion_ref"))
            child_run_id = so.get("run_id")
            out.append(ReviewRecord(
                run_id=ref.run_id,
                child_run_id=child_run_id if isinstance(child_run_id, str) and _RUN_ID.match(child_run_id) else "",
                date=min(slot["stamps"]) if slot["stamps"] else "",
                repo=repo, pr=pr,
                findings=tuple((f["id"], _in(f.get("disposition"), DISPOSITIONS))
                               for f in so.get("findings") or []
                               if isinstance(f, dict) and isinstance(f.get("id"), str) and f["id"]),
            ))
        return tuple(out)

    def rotated_out(self, on_disk: set[str]) -> RotatedOut:
        """The latest snapshot's carried events, reduced to run ids.

        A snapshot that cannot be read is RAISED, not treated as absent: a
        gapped-bag figure silently computed without it would be short by
        exactly the bags that have left the disk.
        """
        try:
            snap = latest_snapshot(self._root)
        except SnapshotError as exc:
            raise JournalEvidenceError(f"the latest snapshot under {self._root} is unreadable: {exc}") from exc
        if snap is None:
            return RotatedOut("", frozenset(), frozenset())
        carried = {e.get("run_id") for e in snap.carried_events if e.get("run_id")}
        gaps = {e.get("run_id") for e in snap.carried_events
                if e.get("run_id") and e.get("kind") == EventKind.GAP.value}
        return RotatedOut(snap.name, frozenset(carried - on_disk), frozenset(gaps))


def open_journal(root: str | None = None) -> JournalEvidence:
    """The configured journal root, or a named one. Never created — a reader
    that made the directory it was asked to read would report an empty journal
    as a healthy one."""
    path = Path(root) if root else resolve_journal_root(config=load_journal_config(), create=False)
    if not path.is_dir():
        raise JournalEvidenceError(f"journal root is not a directory: {path}")
    return JournalEvidence(path)


def forge_thread(repo: str, pr: int, *, runner=None) -> Thread:
    """One pull request's conversation read from the forge NOW — for a run whose
    bag carries no harvest of it (r4: *"from the forge for runs that predate
    the harvest"*).

    THROUGH THE HARVEST'S OWN FETCH, `harvest.fetch_surface`, so a forge thread
    and a harvested one are the same object read at different times — the
    source is labelled, never blended. A forge thread holds every comment
    posted since the run, so a consumer that needs what was said by a given
    moment must cut on comment order, which `Thread` preserves. A surface the
    forge will not return is RAISED as `JournalEvidenceError`, for the caller
    to count; `runner` is the harvest's injectable `gh` seam.
    """
    try:
        snap = fetch_surface(SurfaceRef(repo=repo, kind="pull", number=pr),
                             cwd=Path.cwd(), runner=runner)
    except (HarvestError, SurfaceUnreadable) as exc:
        raise JournalEvidenceError(f"{repo}#{pr}: the forge did not return the thread: {exc}") from exc
    return Thread(repo, pr, "forge", snap.body,
                  tuple(sorted((c.id, c.body) for c in snap.comments)))


# --- parsing -----------------------------------------------------------------

def _decode(path: Path):
    """Every decodable event in one `events.jsonl`, deduped, and how many lines were refused.

    DEDUPED ON IDENTITY, the journal's own replay rule (`events.dedupe_on_identity`).
    A re-run harvest appends the same events to the same writer's file, and a
    retried activity re-emits; counting both would double a run's harvested
    items, gaps and redactions — a wrong figure nothing downstream could see.
    """
    found, refused = [], 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                found.append(decode_event(line))
            except (EventError, ValueError, KeyError, TypeError):
                refused += 1
    return dedupe_on_identity(found), refused


def _decode_all(paths: list[Path]):
    """`_decode` over several writers' files, deduped once across all of them."""
    found, refused = [], 0
    for path in paths:
        events, bad = _decode(path)
        found += events
        refused += bad
    return dedupe_on_identity(found), refused


def _bytes(bag: Path) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(bag, followlinks=False):
        for name in files:
            p = Path(dirpath) / name
            if not p.is_symlink():
                total += p.stat().st_size
    return total


def _children(events) -> list[ChildRun]:
    """A bag's parent stream as child runs.

    A CHILD IS DATED BY ITS OWN EVENTS, not by its bag's first one: a parent
    that runs past midnight has children on two dates, and windowing them by
    the bag's start would drop or admit a run on a day it did not happen.
    """
    return [_child(address, slot, min(slot["stamps"]) if slot["stamps"] else "")
            for address, slot in _slots(events)]


def _slots(events) -> list[tuple[str, dict]]:
    """Group a bag's parent stream on the log address: each child's transcript,
    its run-log members and its event dates. `_children` and `review_records`
    both read this, so the two cannot disagree about which runs a bag holds."""
    by_address: dict[str, dict] = {}
    for e in events:
        if e.kind is not EventKind.COMPLETION:
            continue
        slot = by_address.setdefault(e.destination.address, {"members": {}, "stamps": []})
        day = _day(e.recorded_at)
        if day:
            slot["stamps"].append(day)
        if e.write_path == TRANSCRIPT_WRITE_PATH:
            slot["transcript"] = e.content
        elif e.write_path.startswith(RUN_LOG_PREFIX):
            member = e.write_path[len(RUN_LOG_PREFIX):]
            if member not in _run_log.MEMBER_EVENT_TYPES:
                continue
            payload = _json_object(e.content)
            if payload is not None:
                # LAST WINS: a parent that routed twice (8 of 140 children on
                # 2026-09-24) records its final route second, which is the
                # research paper's "last event per log" rule (§2.4).
                slot["members"][member] = payload
    return [(address, slot) for address, slot in sorted(by_address.items())
            if "transcript" in slot or slot["members"]]


def _result_event(text: str | None) -> dict | None:
    """A transcript's LAST `result` event — `_Trajectory`'s rule, without its counts."""
    result = None
    for line in (text or "").splitlines():
        if line.startswith("{") and '"result"' in line:
            event = _json_object(line)
            if event is not None and event.get("type") == "result":
                result = event
    return result


def _pull_of(completion_ref) -> tuple[str, int | None]:
    """`completion_ref.uri` as (`owner/name`, number) when it is a PR URL, else ("", None).

    A BARE NUMBER IS NOT RESOLVED: `parse_ref` would need a default repo, and
    guessing one would join a pass to the wrong repository's PR N.
    """
    uri = completion_ref.get("uri") if isinstance(completion_ref, dict) else None
    if not isinstance(uri, str):
        return "", None
    try:
        ref = parse_ref(uri, default_repo=None)
    except HarvestError:
        return "", None
    return (ref.repo, ref.number) if ref.kind == "pull" else ("", None)


def _day(stamp) -> str | None:
    """The `YYYY-MM-DD` a `recorded_at` stamp falls on, or None if it is not one.

    EVERY DATE THE WINDOW COMPARES IS THIS ONE SPELLING, because `Window.holds`
    compares strings. `decode_event` does not check the stamp's shape, and a
    bag may have come from another machine, so `stamp[:10]` of a stamp in any
    other spelling would be windowed by string order — silently. A stamp that
    is not `utc_now`'s spelling dates nothing; a child left with no date is
    COUNTED as undated by the report, never dropped unseen.
    """
    if not isinstance(stamp, str) or len(stamp) < 10:
        return None
    day = stamp[:10]
    try:
        return day if _dt.date.fromisoformat(day).isoformat() == day else None
    except ValueError:
        return None


def _json_object(text: str) -> dict | None:
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _child_key(address: str, resources: dict | None) -> str:
    key = (resources or {}).get("workflow_key") or _run_log.model_key_of(Path(address)) or ""
    return key if _KEY_SHAPE.match(key) else "unrecognised"


def _child(address: str, slot: dict, date: str) -> ChildRun:
    members = slot["members"]
    route = members.get("parent_route")
    conv = members.get("convergence")
    resources = members.get("run_resources")
    child = _child_key(address, resources)
    # THE DIRECTORY'S PUBLISH RULE, ENFORCED ON WHAT LEAVES THIS FUNCTION
    # (`measure/README.md` § PUBLISH CLASSIFICATION): each member's values that
    # reach a ChildRun are checked against what arrived in that member's
    # NON-publishable fields — the call every sibling reader makes.
    if resources is not None:
        _run_log.assert_publishable("run_resources", resources, {"child": child})
    if route is not None:
        _run_log.assert_publishable("parent_route", route, {
            "routed": _outcome(route.get("routed_outcome"), route.get("hold_kind"))})
    if conv is not None:
        _run_log.assert_publishable("convergence", conv, {"agrees": _bool(conv, "agrees")})
    t = _Trajectory(slot.get("transcript"))
    so = t.result.get("structured_output") if t.result else None
    so = so if isinstance(so, dict) else None
    return ChildRun(
        child=child,
        date=date,
        has_transcript="transcript" in slot,
        has_result=t.result is not None,
        num_turns=_number(t.result, "num_turns"),
        total_cost_usd=_number(t.result, "total_cost_usd"),
        duration_ms=_number(t.result, "duration_ms"),
        duration_api_ms=_number(t.result, "duration_api_ms"),
        tool_errors=t.tool_errors,
        read_before_edit=t.read_before_edit,
        repeated_reads=t.repeated_reads,
        subagents=t.subagents,
        asserted_outcome=_outcome(so.get("outcome"), so.get("hold_kind")) if so else None,
        dispositions=tuple(_in(f.get("disposition"), DISPOSITIONS)
                           for f in (so or {}).get("findings") or [] if isinstance(f, dict)),
        has_structured_output=so is not None,
        routed_outcome=_outcome(route.get("routed_outcome"), route.get("hold_kind")) if route else None,
        shadow_parseable=_bool(route, "shadow_parseable"),
        channels_agree=_bool(route, "channels_agree"),
        convergence_agrees=_bool(conv, "agrees"),
        has_parent_route=route is not None,
        has_convergence=conv is not None,
    )


def _outcome(outcome, hold_kind) -> str | None:
    if outcome is None:
        return None
    return _in(f"hold:{hold_kind}" if outcome == "hold" else outcome, OUTCOMES)


def _in(value, vocabulary) -> str:
    return value if value in vocabulary else UNRECOGNISED


def _number(record: dict | None, key: str):
    value = (record or {}).get(key)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _bool(record: dict | None, key: str) -> bool | None:
    value = (record or {}).get(key)
    return value if isinstance(value, bool) else None


class _Trajectory:
    """One pass over a transcript: the `result` event and the trajectory counts.

    STRUCTURAL, over decoded `tool_use` / `tool_result` blocks — never a string
    scan of the line, for `run_log.subagents_in`'s reason: a tool RESULT can
    quote a tool name, and a quotation is not a call. Blocks are deduped on
    their ids because the stream can repeat a message.

    REPEATED READS ARE KEYED ON (context, path, offset, limit). A sub-agent
    reading a file its parent already read is a separate context doing its own
    work, not a re-read; the context is the event's `parent_tool_use_id` (None
    for the main loop). THE RANGE IS IN THE KEY because the fleet's prompts
    MANDATE paging a large file (`limit:200` on the first Read, `offset`+`limit`
    after): keyed on path alone, 265 of 265 in-window repeats on 2026-09-24
    were distinct pages, and the figure measured compliance with that rule
    rather than waste. The SAME range read twice in one context is a re-read.

    EVERY OTHER COUNT IS RUN-WIDE, sub-agent contexts included, and that is a
    choice. F4 is the phase doc's `tool_result.is_error == true` over the run's
    whole transcript, which carries its sub-agents' tool traffic under their
    `parent_tool_use_id`; only a re-read is a property of ONE context's memory.
    """

    def __init__(self, text: str | None) -> None:
        self.result: dict | None = None
        self.tool_errors = self.read_before_edit = self.repeated_reads = self.subagents = 0
        if not text:
            return
        seen_use: set[str] = set()
        seen_result: set[str] = set()
        # offset/limit enter the key by `repr`, so a malformed (unhashable)
        # argument cannot raise; the cost is that int 1 and string "1" are
        # different keys — an UNDERCOUNT only, and the Read schema types both
        # as integers.
        read_paths: set[tuple[object, str, str, str]] = set()
        for line in text.splitlines():
            if not line.startswith("{"):
                continue
            event = _json_object(line)
            if event is None:
                continue
            kind = event.get("type")
            if kind == "result":
                self.result = event
                continue
            message = event.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if kind == "assistant" and block.get("type") == "tool_use":
                    bid = block.get("id")
                    if bid and bid in seen_use:
                        continue
                    seen_use.add(bid)
                    name = block.get("name")
                    if name in _run_log.SUBAGENT_TOOL_NAMES:
                        self.subagents += 1
                    elif name == "Read":
                        arguments = block.get("input") or {}
                        target = arguments.get("file_path")
                        if isinstance(target, str):
                            key = (event.get("parent_tool_use_id"), target,
                                   repr(arguments.get("offset")), repr(arguments.get("limit")))
                            if key in read_paths:
                                self.repeated_reads += 1
                            read_paths.add(key)
                elif kind == "user" and block.get("type") == "tool_result":
                    bid = block.get("tool_use_id")
                    if bid and bid in seen_result:
                        continue
                    seen_result.add(bid)
                    if block.get("is_error") is True:
                        self.tool_errors += 1
                        if _READ_BEFORE_EDIT.search(_result_text(block.get("content"))):
                            self.read_before_edit += 1


def _result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict)
                        and isinstance(b.get("text"), str))
    return ""
