"""The read interface over the planning corpus's deferral records — the tracked
stores and the CPI decisions log.

Self Improvement Phase 2 (`phase2_the_self_report_and_recurrence_measured.md`)
r3 computes a calibration ratio over `cpi-decisions.md` and the tracked stores,
and its checklist verifies that *"the tool imports no path enumeration of its
own"*. `journal_evidence.py` is that interface for the journal and says it is
the only module that knows a bag is a directory; THIS IS ITS SIBLING FOR THE
TWO PLANNING FILES, so the figure module above both reads neither by path.

WHAT THIS IMPORTS AND DOES NOT RE-DERIVE:

  * a tracked item's frontmatter and which store an id belongs to —
    `modules/assistant/tracked/tracked_items.py` (`parse`, `STORES`), the
    module every filer writes through. The Tracked Items Standard §3 core is
    read from there, never from a second parser.

WHAT THIS PARSES, BECAUSE NOTHING ELSE DOES: the CPI log's DEFERRED entries.
The log is append-only prose with no schema, so the parse is STRUCTURAL and
narrow, and the rule is stated where it is applied (`_deferrals`). A shape it
does not recognise is not guessed at — it is simply not an entry, and the
figure module's hypothesis channel (r6) is where a missed deferral is named.

THE CORPUS ROOT IS DERIVED AS A SIBLING, the rule `planning_corpus.py` states
for the test suite: the two repos sit beside each other on every machine that
holds both. `--planning` names another. A root that does not hold the corpus is
a refusal, never an empty population — an empty store reads exactly like a
store where nothing ever recurred.

Nothing here writes, and nothing here calls a model.
"""

from __future__ import annotations

import datetime as _dt
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_TEMPORAL = _HERE.parents[1] / "workflows" / "temporal"
if str(_TEMPORAL) not in sys.path:
    sys.path.insert(0, str(_TEMPORAL))

from modules.assistant.tracked.tracked_items import STORES, parse  # noqa: E402

__all__ = ["PlanningEvidence", "TrackedItem", "CpiSection", "CpiDeferral",
           "open_planning", "PlanningEvidenceError", "PLANNING_REPO", "CPI_LOG"]

PLANNING_REPO = "skyynet-master-planning"
#: The CPI log, relative to the planning root — `standards-governance.md`
#: § CPI Decisions Log names it.
CPI_LOG = ("development", "common", "cpi-decisions.md")

#: A deferral subsection: `### DEFERRED …` or `### WATCH …`, upper case as the
#: log writes them. `### RECORDED, not watched` is not one — it says so.
_DEFERRED_HEADING = re.compile(r"\A###\s+(?:DEFERRED|WATCH)\b(?P<rest>.*)\Z")
#: A subsection title that labels a LIST of deferrals rather than naming one.
_CONTAINER_TITLE = re.compile(r"watch-list|watch-criteria stated|trigger-gated", re.I)
#: An entry's bold lead, in the four shapes the log writes: `- **title**`,
#: `1. **title**`, `**3. title**` and a paragraph opening `**title**`. A lead
#: ending in `:` is a LABEL (`**Watch (all three):**`), not an entry.
_ENTRY = re.compile(r"\A(?:-\s+|\d+\.\s+)?\*\*(?:\d+\.\s*)?(?P<title>.+?)\*\*")
_DATE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")


class PlanningEvidenceError(RuntimeError):
    """The planning corpus could not be read."""


@dataclass(frozen=True)
class TrackedItem:
    id: str
    store: str
    status: str
    count: int | None       # None when the frontmatter's `count` is not an integer
    filed: str              # YYYY-MM-DD, or "" when absent or malformed


@dataclass(frozen=True)
class CpiSection:
    """One `## ` section of the log: its heading's date, first line and text."""

    date: str               # the first YYYY-MM-DD in the heading, "" if none
    line: int               # 1-based line of the heading
    text: str


@dataclass(frozen=True)
class CpiDeferral:
    """One DEFERRED entry. `title` is the entry's bold lead or its heading's
    tail; `text` runs to the next entry, subsection or section."""

    line: int
    section_line: int
    section_date: str
    title: str
    text: str


class PlanningEvidence:
    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def label(self) -> str:
        return str(self._root)

    def tracked_items(self) -> tuple[list[TrackedItem], list[str]]:
        """Every item in every §1 store, and the files that would not parse.

        A file that fails the standard's own parser is RETURNED BY NAME, not
        dropped: an item nobody could read is one whose recurrence nobody could
        count, and the figure module lists it as unclassified.
        """
        return _read_stores(self._root / "tracked")

    def sibling_tracked_items(self) -> tuple[list[TrackedItem], list[str]]:
        """The tracked stores of every OTHER repo beside the planning root.

        FOR LOOKUP, NOT FOR A POPULATION. A reflection in `MDC-Master-Planning`
        names that repo's items, which live in its own `tracked/`; a claim
        naming one is corroborated or not by ITS count.
        """
        items, unreadable = [], []
        for repo in sorted(p for p in self._root.parent.iterdir()
                           if p.is_dir() and p != self._root and (p / "tracked").is_dir()):
            found, bad = _read_stores(repo / "tracked")
            items += found
            unreadable += [f"{repo.name}/{b}" for b in bad]
        return items, unreadable


    def cpi_log(self) -> tuple[list[CpiSection], list[CpiDeferral]]:
        path = self._root.joinpath(*CPI_LOG)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise PlanningEvidenceError(f"the CPI log is unreadable at {path}: {exc}") from exc
        return _sections(lines), _deferrals(lines)


def open_planning(root: str | None = None) -> PlanningEvidence:
    path = Path(root) if root else _sibling()
    if not (path / "tracked").is_dir() or not path.joinpath(*CPI_LOG).is_file():
        raise PlanningEvidenceError(
            f"{path} does not hold the planning corpus (no tracked/ or no "
            f"{'/'.join(CPI_LOG)}) — name one with --planning")
    return PlanningEvidence(path)


def _read_stores(tracked: Path) -> tuple[list[TrackedItem], list[str]]:
    items, unreadable = [], []
    for store in STORES.values():
        directory = tracked / store.name
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            try:
                fields, _body = parse(path)
            except (ValueError, OSError, UnicodeError) as exc:
                unreadable.append(f"{store.name}/{path.name}: {type(exc).__name__}")
                continue
            items.append(TrackedItem(
                id=fields.get("id", path.stem), store=store.name,
                status=fields.get("status", ""), count=_int(fields.get("count")),
                filed=_iso(fields.get("filed"))))
    return items, unreadable


def _sibling() -> Path:
    for up in _HERE.parents:
        candidate = up.parent / PLANNING_REPO
        if (candidate / "tracked").is_dir():
            return candidate
    return _HERE / f"__no_{PLANNING_REPO}__"


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iso(value) -> str:
    try:
        day = _dt.date.fromisoformat(str(value).strip())
    except ValueError:
        return ""
    return day.isoformat()


def _sections(lines: list[str]) -> list[CpiSection]:
    heads = [i for i, line in enumerate(lines) if line.startswith("## ")]
    out = []
    for k, i in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(lines)
        m = _DATE.search(lines[i])
        out.append(CpiSection(m.group(1) if m else "", i + 1, "\n".join(lines[i:end])))
    return out


def _deferrals(lines: list[str]) -> list[CpiDeferral]:
    """The DEFERRED entries, by structure.

    THE RULE. Inside a `## ` section, a `### DEFERRED…` or `### WATCH…`
    subsection is either ONE entry — its heading names the thing deferred
    (`### WATCH — prose figures cannot declare …`) — or a CONTAINER whose title
    only labels a list (`— watch-list`, `— watch-criteria stated`, `—
    trigger-gated`), in which case each line opening with a bold lead
    (`_ENTRY`) is one entry, running to the next. Nested sub-bullets are
    indented and never open one. A subsection ends at the next `### ` or `## `. Deferrals written anywhere else in the log (a `Decision: defer`
    line under a `### Handoff` heading) are NOT entries by this rule, and that
    is the rule's stated blind spot.
    """
    out: list[CpiDeferral] = []
    section_line, section_date = 0, ""
    mode, open_entry = None, None     # mode: None | "container" | "single"

    def close(end: int) -> None:
        nonlocal open_entry
        if open_entry is not None:
            start, title = open_entry
            out.append(CpiDeferral(start + 1, section_line, section_date, title,
                                   "\n".join(lines[start:end])))
            open_entry = None

    for i, line in enumerate(lines):
        if line.startswith("## "):
            close(i)
            m = _DATE.search(line)
            section_line, section_date, mode = i + 1, (m.group(1) if m else ""), None
            continue
        if line.startswith("### "):
            close(i)
            m = _DEFERRED_HEADING.match(line.rstrip())
            if not m:
                mode = None
                continue
            tail = m["rest"].strip().lstrip("—-: ").strip()
            if not tail or _CONTAINER_TITLE.search(tail):
                mode = "container"
            else:
                mode = "single"
                open_entry = (i, tail)
            continue
        if mode == "container":
            e = _ENTRY.match(line)
            if e and not e["title"].rstrip().endswith(":"):
                close(i)
                open_entry = (i, e["title"].strip())
    close(len(lines))
    return out
