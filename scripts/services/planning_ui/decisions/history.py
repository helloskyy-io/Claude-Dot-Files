"""How long a thing has sat, and across how many triage passes — from `git log`.

**Nothing is stored and nothing is exported.** The checkout's history IS the
active artifact, so every figure here is recomputed per run. A sidecar recording
"when we last looked at this" would be a second copy of an answer the repository
already holds, and it can disagree with the thing it duplicates.

Two subprocess reads, both against the checkout and neither over a network:

* ``git log --name-status --find-renames -- tracked/`` — one call for every item
  in all four stores, giving each item's last activity AND the per-store commit
  series the §0 exit test counts passes against. Every flag on it is load-bearing
  and each one closes a way of counting wrong:

  - ``--name-status`` rather than ``--name-only``, because **a commit that only
    ADDS items is filing, not triage**, and counting it as a pass inflates every
    score in a store being harvested into;
  - ``--find-renames`` rather than ``--no-renames``, because git otherwise
    spells a rename as a delete plus an add and the delete half reads as a
    ruling — one ``git mv`` then credited every other item in the store with a
    pass it never received;
  - ``-c core.quotePath=false``, because git C-quotes any path carrying a quote,
    a backslash or a non-ASCII byte, and a quoted path matches none of the shape
    tests below — so the item drops out of history silently.

* ``git blame --line-porcelain -- development/sprints.md`` — one call for every
  line of the hand-maintained § Sprint: Unplaced list. Per-LINE, because a
  file-level date would make every entry as old as the most recent edit anywhere
  in the document, erasing the exact signal the section was built to expose.

**Both read the history a merge in progress WILL have, not only ``HEAD``'s.**
The merge rule for the committed artifacts regenerates them before the merge
commit exists (``planning_ui/githooks/``), and a page derived then must equal the one
the merge commit derives afterwards — otherwise ``--check`` fails on the very
commit the hook produced. ``git blame`` does this on its own: when
``MERGE_HEAD`` exists it treats the working tree as a child of both heads.
``git log`` does not, so the log is walked from ``HEAD`` AND every
``MERGE_HEAD`` — the union that is exactly the merge commit's ancestry, since
the merge commit itself lists no files under ``--name-status``. What stays
unknowable until the commit exists is a line the merge itself authored (a
hand-resolved conflict in ``sprints.md``): blame reports it uncommitted, the
merge commit will date it to itself, and ``--check`` names the page.

Both are read-only ``git`` subcommands, and ``git`` is the only program either
package may run. That is checked structurally by
:mod:`~planning_ui.decisions.readonly_scan`, which allow-lists the
executable as well as the subcommands rather than trusting this docstring.

**A checkout with no ``.git`` yields no history rather than raising.** The page
still renders, the age columns say so, and :data:`~.model.HISTORY_UNAVAILABLE`
names it once — a page silently missing its age columns reads as a page whose
items have all just been filed.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

GIT_TIMEOUT_SECONDS = 30

#: Record and field separators for the log parse. ASCII RS/US, because a commit
#: subject can contain anything a human types and a newline-delimited parse of
#: `--name-only` output has to distinguish "next path" from "next commit".
_RECORD_SEP = "\x1e"
_FIELD_SEP = "\x1f"


@dataclass(frozen=True)
class Activity:
    """One commit, as the last time something changed."""

    commit: str
    #: Unix committer timestamp. Used for ORDERING — an ISO-8601 string with a
    #: varying UTC offset does not sort lexicographically, and the exit test
    #: counts passes by ordering.
    timestamp: int
    #: ISO-8601 committer date, for display.
    when: str

    @property
    def day(self) -> str:
        return self.when[:10]


@dataclass
class History:
    """Everything derived from the checkout's history, for one run."""

    available: bool = False
    #: Whether ``git blame`` on ``sprints.md`` succeeded. Tracked separately
    #: from :attr:`available`: the log can succeed while the blame fails — a
    #: newly-added, never-committed ``sprints.md`` — and a table 5 whose age
    #: column is silently all-dashes reads as a section nobody has touched.
    blame_available: bool = False
    #: repo-relative item path -> the last commit that touched it.
    item_activity: dict[str, Activity] = field(default_factory=dict)
    #: store name -> the commits that TRIAGED it, newest first. A commit that
    #: only ADDS files is filing, not triage — see :meth:`passes_since_activity`.
    store_commits: dict[str, list[Activity]] = field(default_factory=dict)
    #: store name -> commit sha -> the item paths that commit touched, whatever
    #: the change kind. Used to exclude an item from its own pass count.
    store_touches: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    #: 1-indexed line of development/sprints.md -> the commit that last set it.
    sprint_line_activity: dict[int, Activity] = field(default_factory=dict)

    def days_since(self, activity: Activity | None, as_of: date) -> int | None:
        if activity is None:
            return None
        moment = datetime.fromtimestamp(activity.timestamp, tz=timezone.utc).date()
        return (as_of - moment).days

    def item_age_days(self, path: str, as_of: date) -> int | None:
        return self.days_since(self.item_activity.get(path), as_of)

    def passes_since_activity(self, store: str, path: str) -> int | None:
        """How many triage passes the item has survived without changing.

        A **pass** is a commit that **modified or deleted** an item already in
        the store, and did not touch this item — somebody went through the store
        and ruled on something, and this item was not it. A modification is a
        ruling being recorded and a deletion is §4.2 pruning, which follows one.

        **A commit that only ADDS files is not a pass.** Filing is not triage,
        and counting it as one inflates every item's score in a store that is
        being harvested into — which is exactly the state `tracked/candidates/`
        was in when this was written, after 34 intake issues landed in it on one
        day. That is the closest a checkout can come to §0's "three consecutive
        triage passes", and it is stated on the page rather than left for a
        reader to assume.

        ``None`` when history is unavailable, never ``0`` — a zero here reads as
        "freshly triaged", which is the opposite of what an absent history means.
        """
        if not self.available:
            return None
        mine = self.item_activity.get(path)
        if mine is None:
            return None
        touches = self.store_touches.get(store, {})
        return sum(
            1
            for commit in self.store_commits.get(store, [])
            if commit.timestamp > mine.timestamp and path not in touches.get(commit.commit, ())
        )


def _run_git(root: Path, args: list[str]) -> str | None:
    """Run a read-only ``git`` subcommand against the checkout, or return ``None``.

    ``check=False`` plus an explicit return, matching
    :mod:`plan_extractor.provenance`: a missing ``.git`` and a missing ``git``
    binary are both *expected states* of a read-only mount, not errors to
    swallow. Anything else propagates.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _parse_log(output: str, stores: tuple[str, ...]) -> History:
    history = History(available=True)
    for record in output.split(_RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        header, _, body = record.partition("\n")
        parts = header.split(_FIELD_SEP)
        if len(parts) != 3:
            continue
        sha, raw_timestamp, iso = parts
        try:
            timestamp = int(raw_timestamp)
        except ValueError:
            continue
        activity = Activity(commit=sha, timestamp=timestamp, when=iso)

        touched_by_store: dict[str, set[str]] = {}
        triaged_stores: set[str] = set()
        for line in body.splitlines():
            fields = line.split("\t")
            if len(fields) < 2:
                continue
            status = fields[0]
            # A rename/copy carries TWO paths — `R100\told\tnew`. Both are
            # activity on their items; neither is a ruling.
            paths = [p.strip() for p in fields[1:] if p.strip()]
            kind = status[:1]
            for path in paths:
                if not path.endswith(".md"):
                    continue
                segments = path.split("/")
                if len(segments) != 3 or segments[0] != "tracked" or segments[1] not in stores:
                    continue
                store = segments[1]
                touched_by_store.setdefault(store, set()).add(path)
                # `M`odified is a ruling being recorded; `D`eleted is §4.2
                # pruning, which follows one. `A`dded is filing, and filing is
                # not triage.
                #
                # **`R`enamed and `C`opied are NEITHER, and that is why renames
                # are detected rather than suppressed.** Under `--no-renames`
                # git spells a rename as `D` of the old path plus `A` of the
                # new one, and the `D` half satisfies the rule above — so ONE
                # reorganising commit credited EVERY OTHER item in the store
                # with a triage pass it did not receive, inflating the §0 exit
                # test, which is this page's headline derivation. A rename moves
                # an item; it rules on nothing.
                if kind in ("M", "D"):
                    triaged_stores.add(store)
                # `git log` walks newest-first, so the FIRST commit to mention a
                # path is its last activity. setdefault, not assignment.
                history.item_activity.setdefault(path, activity)

        for store, paths in touched_by_store.items():
            history.store_touches.setdefault(store, {})[sha] = paths
            if store in triaged_stores:
                history.store_commits.setdefault(store, []).append(activity)
    return history


#: The sha ``git blame`` reports for a line that is not committed yet.
_UNCOMMITTED_SHA = "0" * 40


def _iso_from(timestamp: int, tz_offset: str) -> str:
    """Rebuild ``%cI`` from blame's ``committer-time`` + ``committer-tz``.

    Blame's porcelain output gives the epoch and the offset as SEPARATE fields
    and never an ISO string, so an implementation that forgets the offset silently
    renders every blamed line in UTC — while ``git log %cI`` preserves the
    committer's own offset. For a commit made late at night outside UTC the same
    real moment then shows a DIFFERENT calendar day in table 5 than in tables 1-4,
    which is a page disagreeing with itself about how long something has sat.
    """
    moment = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    match = _TZ_RE.match(tz_offset.strip())
    if match:
        sign, hours, minutes = match.groups()
        delta = timedelta(hours=int(hours), minutes=int(minutes))
        moment = moment.astimezone(timezone(-delta if sign == "-" else delta))
    return moment.isoformat()


_TZ_RE = re.compile(r"^([+-])(\d{2})(\d{2})$")


def _parse_blame(output: str) -> dict[int, Activity]:
    """Map each 1-indexed line of the blamed file to the commit that set it.

    A line git attributes to the all-zero sha is **not committed yet** — a local
    edit sitting in the working tree. It is skipped rather than recorded, because
    recording it would date the entry to *now* and render an uncommitted edit as
    a freshly-touched entry. That is the same "reads as freshly triaged" failure
    this module refuses for the whole-history-unavailable case, one line down.
    """
    lines: dict[int, Activity] = {}
    sha = ""
    final_line = 0
    timestamp = 0
    tz_offset = ""
    for raw in output.splitlines():
        if raw.startswith("\t"):
            if sha and final_line and sha != _UNCOMMITTED_SHA:
                lines[final_line] = Activity(
                    commit=sha, timestamp=timestamp, when=_iso_from(timestamp, tz_offset)
                )
            sha, final_line, timestamp, tz_offset = "", 0, 0, ""
            continue
        if raw.startswith("committer-time "):
            try:
                timestamp = int(raw.split(" ", 1)[1])
            except ValueError:
                timestamp = 0
            continue
        if raw.startswith("committer-tz "):
            tz_offset = raw.split(" ", 1)[1]
            continue
        head = raw.split(" ")
        if len(head) >= 3 and len(head[0]) == 40 and all(c in "0123456789abcdef" for c in head[0]):
            sha = head[0]
            try:
                final_line = int(head[2])
            except ValueError:
                final_line = 0
    return lines


def merge_heads(root: Path) -> list[str]:
    """The commits a merge in progress is bringing in — ``MERGE_HEAD``, one sha
    per line for an octopus — or ``[]`` when no merge is in progress.

    Read from the file ``git`` names rather than resolved as a ref, because
    ``rev-parse MERGE_HEAD`` returns the first line only.
    """
    located = _run_git(root, ["rev-parse", "--git-path", "MERGE_HEAD"])
    if located is None:
        return []
    path = Path(located.strip())
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def read_history(root: Path, stores: tuple[str, ...], sprints_rel: str) -> History:
    """Derive every history-backed column, in two read-only ``git`` calls."""
    # Walked from HEAD only when no merge is in progress — the default — and
    # from every head of one otherwise, so an item the incoming side filed has
    # the age the merge commit will give it. See the module docstring.
    incoming = merge_heads(root)
    revisions = ["HEAD", *incoming] if incoming else []
    log = _run_git(
        root,
        [
            # Git C-quotes any path carrying a quote, a backslash or a non-ASCII
            # byte unless this is off, and a quoted path fails every
            # `tracked/<store>/<id>.md` shape test in `_parse_log` — so the item
            # vanishes from history entirely and renders as though nothing were
            # known about it, which is indistinguishable from history being
            # unavailable for that one row.
            "-c",
            "core.quotePath=false",
            "log",
            f"--format={_RECORD_SEP}%H{_FIELD_SEP}%ct{_FIELD_SEP}%cI",
            "--name-status",
            # Renames are DETECTED, not suppressed — see `_parse_log`. Under
            # `--no-renames` a rename becomes a delete plus an add, and the
            # delete half reads as a triage pass over every other item in the
            # store.
            "--find-renames",
            *revisions,
            "--",
            "tracked/",
        ],
    )
    if log is None:
        return History(available=False)

    history = _parse_log(log, stores)

    blame = _run_git(root, ["blame", "--line-porcelain", "--", sprints_rel])
    if blame is None:
        # The log succeeded and the blame did not — `sprints.md` newly added and
        # never committed, or unreadable. Recorded so the caller can SAY the
        # column is absent, rather than rendering a dash that reads as "nothing
        # has changed here recently".
        history.blame_available = False
        return history
    history.blame_available = True
    history.sprint_line_activity = _parse_blame(blame)
    return history
