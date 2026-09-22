"""What a COMPLETE run bag contains — the journal's own contract, declared once.

`validate.py` answers INTEGRITY: do the bytes match the manifest. It says so in
its own header and that contract is deliberate. Nothing answered COMPLETENESS —
*did this run's record come out whole* — so every consumer that needed the
answer was about to derive it, and the first two derivations already disagreed:
a file count called a bag with only `harvest/index.json` populated, and called a
bag whose harvest honestly found nothing incomplete.

**BagIt has the mechanism and this is it.** A BagIt Profile is a declaration,
separate from canonical validation, of what a conforming bag of a given kind
must carry — required tags, required payload entries — validated alongside the
structural check rather than folded into it (BagIt Profiles Specification). This
module is that profile for a run bag, expressed in Python because its two
interesting rules are conditional and a JSON profile cannot state them:

  * `harvest/events.jsonl` is required **iff** the harvest found surfaces. A
    harvest that ran over an empty population writes `index.json` with
    `"surfaces": []` and no events file, and that is COMPLETE — the index is the
    proof it ran. Requiring the events file unconditionally fails every correct
    empty-population harvest, which is the same "silent on an empty population"
    error the harvest itself is written to avoid.
  * A bag is INCOMPLETE when the run's own child log is on disk and the bag does
    not contain it. The emit is a parent-side act at child completion
    (`assistant_activities` reads the transcript after the child returns), so a
    parent that dies while its child runs leaves a complete log on disk and an
    empty, structurally valid bag. Measured 2026-09-18: a 30-minute child that
    opened a pull request, recorded nowhere. The log is the independent witness,
    and comparing the two is the only thing that makes this check able to fail.

THE PRODUCER OWNS THIS, NOT THE READER. Completeness is a fact about what the
journal writes; a consumer that carried its own definition would be the second
carrier of it, and the next consumer a third. Readers import `assess_completeness` — named at length, and not
`assess`, because the convergence module already owns that name and a guard
there sweeps for anything branching on it; two `assess` functions in one tree
make that guard unable to tell routing-on-convergence from any other verdict.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .bag import BAG_INFO_FILE, PAYLOAD_DIR, read_tag_file

__all__ = ["Assessment", "assess_completeness", "orphan_logs", "EVENTS", "HARVEST_INDEX",
           "HARVEST_EVENTS", "COMPLETE", "INCOMPLETE", "UNREADABLE"]

EVENTS = f"{PAYLOAD_DIR}/events.jsonl"
HARVEST_INDEX = f"{PAYLOAD_DIR}/harvest/index.json"
HARVEST_EVENTS = f"{PAYLOAD_DIR}/harvest/events.jsonl"

COMPLETE = "complete"
INCOMPLETE = "incomplete"
UNREADABLE = "unreadable"

#: A child log's FIRST event carries `"cwd": "<repo>/.claude/worktrees/<name>"`
#: — the worktree the child actually ran in — and the bag names the same
#: worktree in `Journal-Worktree`. That is the join, and it is deliberately the
#: `cwd` rather than any mention of the name: a later run that prints the path
#: (a `git worktree list`, a reviewer reading the plan's tree) mentions it
#: without being it, and joining on mention attributes another run's log to this
#: bag. `session_id` identifies the child inside both the log and the transcript
#: the parent emits, so the comparison is by session and never by file count —
#: one parent legitimately runs several children into one bag.
_SESSION = re.compile(r'session_id\\?"\s*:\s*\\?"([0-9a-f-]{8,})')
_CWD = re.compile(r'"cwd"\s*:\s*"([^"]+)"')

#: Repo log directory -> [(log path, worktree basename, sessions)]. One read per
#: log per process: the sweep asks about every bag, and re-reading a repo's logs
#: for each of them turned a two-second check into minutes.
_LOG_INDEX: dict[Path, list[tuple[Path, str, frozenset[str]]]] = {}


def _index(logs_dir: Path) -> list[tuple[Path, str, frozenset[str]]]:
    cached = _LOG_INDEX.get(logs_dir)
    if cached is not None:
        return cached
    entries: list[tuple[Path, str, frozenset[str]]] = []
    for log in sorted(logs_dir.glob("*.jsonl")):
        try:
            text = log.read_text(errors="replace")
        except OSError:
            continue
        cwd = _CWD.search(text)
        if not cwd:
            continue
        entries.append((log, Path(cwd.group(1)).name, frozenset(_SESSION.findall(text))))
    _LOG_INDEX[logs_dir] = entries
    return entries


@dataclass(frozen=True)
class Assessment:
    """One bag against the profile. `verdict` is the answer; `reasons` is why."""
    run_id: str
    workflow: str
    verdict: str
    reasons: tuple[str, ...] = ()
    orphaned_logs: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.verdict == COMPLETE


def _sessions(text: str) -> set[str]:
    return set(_SESSION.findall(text))


def orphan_logs(bag: Path, tags: dict[str, str]) -> list[Path]:
    """Child logs on disk for this run's worktree that the bag does not contain.

    Returns [] when the join cannot be made — no origin repo, no worktree, no
    log directory. **An absent join is not evidence of completeness**, and the
    caller must not read it as such; `assess_completeness` records it as a reason instead.
    """
    repo, worktree = tags.get("Journal-Origin-Repo"), tags.get("Journal-Worktree")
    if not repo or not worktree:
        return []
    logs_dir = Path(repo) / ".claude" / "logs"
    if not logs_dir.is_dir():
        return []
    events = bag / EVENTS
    held = _sessions(events.read_text(errors="replace")) if events.is_file() else set()
    return [log for log, wt, sessions in _index(logs_dir)
            if wt == worktree and not (sessions & held)]


def assess_completeness(bag: Path) -> Assessment:
    """Evaluate one bag against the profile. Reads; writes nothing."""
    info = bag / BAG_INFO_FILE
    if not info.is_file():
        return Assessment(bag.name, "", UNREADABLE, (f"no {BAG_INFO_FILE}",))
    try:
        tags = dict(read_tag_file(info))
    except Exception as exc:                                    # noqa: BLE001
        return Assessment(bag.name, "", UNREADABLE,
                          (f"{BAG_INFO_FILE} unreadable — {exc}",))

    workflow = tags.get("Journal-Workflow", "")
    reasons: list[str] = []

    events = bag / EVENTS
    if not events.is_file():
        reasons.append(f"{EVENTS} absent — the run emitted nothing")
    elif events.stat().st_size == 0:
        reasons.append(f"{EVENTS} is empty")

    index = bag / HARVEST_INDEX
    harvest_events = bag / HARVEST_EVENTS
    if not index.is_file():
        reasons.append(f"{HARVEST_INDEX} absent — no evidence the harvest ran")
    else:
        try:
            surfaces = json.loads(index.read_text()).get("surfaces", [])
        except Exception as exc:                                # noqa: BLE001
            reasons.append(f"{HARVEST_INDEX} unparseable — {exc}")
            surfaces = None
        if surfaces:
            if not harvest_events.is_file():
                reasons.append(
                    f"{HARVEST_INDEX} names {len(surfaces)} surface(s) and "
                    f"{HARVEST_EVENTS} is absent")
        elif surfaces == [] and harvest_events.is_file():
            reasons.append(
                f"{HARVEST_EVENTS} present while {HARVEST_INDEX} reports no "
                f"surfaces — the two disagree about what was harvested")

    if not tags.get("Journal-Origin-Repo") or not tags.get("Journal-Worktree"):
        reasons.append("no origin repo or worktree recorded — the child logs on "
                       "disk cannot be joined to this bag, so its completeness "
                       "is UNVERIFIABLE rather than proven")
    orphans = tuple(str(p) for p in orphan_logs(bag, tags))
    if orphans:
        reasons.append(
            f"{len(orphans)} child log(s) on disk for worktree "
            f"{tags.get('Journal-Worktree')} that this bag does not contain — "
            f"the run's work happened and its record did not land")

    verdict = INCOMPLETE if reasons else COMPLETE
    return Assessment(bag.name, workflow, verdict, tuple(reasons), orphans)
