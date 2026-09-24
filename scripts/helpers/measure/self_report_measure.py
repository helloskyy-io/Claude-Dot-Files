#!/usr/bin/env python3
"""The self-report and recurrence, measured — three rates, each an asserted signal against a computed one.

    self_report_measure.py                              # configured journal, sibling planning repo
    self_report_measure.py --repo helloskyy-io/MDC-Master-Planning
    self_report_measure.py --emit samples      > /tmp/samples.jsonl      # for the hand check
    self_report_measure.py --emit reflections  > /tmp/reflections.jsonl  # for the r6 sweep
    self_report_measure.py --stdin < /tmp/inputs.json   # hand labels and sweep hypotheses

Self Improvement Phase 2 (`phase2_the_self_report_and_recurrence_measured.md`).

  r1  E1B. Every `review-pr` typed finding is classified ALREADY-STATED or NEW
      against what the producing runs wrote about themselves on the pull
      request BEFORE the pass's own comment. Classification is the predecessor
      `judge_marginal_yield.py`'s rule — its bullet extraction, its token
      reduction and its threshold, IMPORTED — applied per record rather than
      per title list. LEXICAL, so the NEW share is biased UPWARD; the report
      says so beside the figure, and prints the predecessor's own population
      rule (every non-judge comment, no cut) over the same records as the
      control.
  r2  THE RECURRENCE-CLAIM CHECK. Every Post-Run Reflection sentence in one
      repo's pull-request comments that claims recurrence is corroborated when
      it names a tracked item whose `count` is at least 2, or a typed finding
      id that at least two review passes carried. Anything else is listed.
  r3  THE V1 CALIBRATION RATIO. Every DEFERRED entry in the CPI log, and every
      tracked item, is deferred-then-recurred, deferred-and-never-recurred, or
      unclassified with its reason — with 90 days as the censoring horizon:
      an entry not seen to recur is only NEVER-recurred once it has been
      watchable for 90 days.
  r4  Every record is read through `journal_evidence` (runs, typed records,
      PR threads) and `planning_evidence` (tracked stores, CPI log). Each PR's
      thread is the bag's harvest where it carries one and the forge where it
      does not, and the report counts which.
  r6  `--emit reflections` hands the reflection channel to a model-read sweep;
      `--stdin` takes its HYPOTHESES back in the three declared forms below and
      prints each check TWICE — computed alone, and with the hypotheses — so
      the recorded rate never contains a model's assertion, and whether a
      hypothesis changed a computation is printed rather than inferred.

THE HAND-OFF FORMS (r6, stated before any sweep runs):

  r1 takes A FINDING ID TO LOOK UP — `{"pr": "owner/name#N", "finding_id":
     "...", "claim": "stated"|"new"}`. The check reports whether the computed
     classification of that finding agrees. It never changes the r1 rate.
  r2 takes A CLAIM TO CORROBORATE — `{"pr": "owner/name#N", "comment_id": N,
     "sentence": "..."}`. A sentence found VERBATIM in that comment's
     reflection and not already in the population is added, then corroborated
     by the same computed rule. A sentence not found is refused and counted.
  r3 takes A DEFERRAL TO RE-CHECK — `{"entry_line": N, "evidence_line": M}`.
     The entry is recurred when line M lies in a LATER section of the log and
     carries a recurrence marker that is not a watch-criterion. The LINK is the
     sweep's assertion; the position and the marker are checked.

A FIGURE TOO CLEAN TO BE TRUE IS THE TELL (phase doc § Decisions). `--emit
samples` draws a seeded sample of each check's classifications; hand labels
come back through `--stdin` and the disagreement rate prints beside the figure.

PUBLISH CLASSIFICATION (`measure/README.md`). Rates, counts, run ids, PR
numbers and line numbers are publishable. The uncorroborated claims (r2) and
the samples are MODEL-AUTHORED TEXT: printed here for the person reading, and
never to be copied into a committed doc or a PR comment. This module never
writes a file, never sees a path, and calls no model.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import journal_baseline as jb
import journal_evidence as je
import judge_marginal_yield as jmy
import planning_evidence as pe
from modules.assistant.review_pr.review_pr_helper import (PR_REVIEW_BLOCK, findings_section,
                                                          run_id_in_block)

#: r3's censoring horizon — the phase doc's "90-day prune".
CENSOR_DAYS = 90
DEFAULT_SAMPLE = 30

#: r2's population. The phase doc names "again", "second occurrence" and
#: "recurrence"; the ordinal and the inflections are the same claim spelled
#: another way. A sentence DESCRIBING the recurrence rule matches too, and that
#: is what the hand sample's precision measures.
CLAIM = re.compile(r"\bagain\b|\b(?:second|third|fourth|fifth|\d+(?:st|nd|rd|th)) "
                   r"(?:occurrence|time|instance)\b|\brecurr\w*|🔁", re.I)
#: r3's evidence marker, on a LATER line that cites an entry.
RECURRENCE_MARKER = re.compile(r"🔁|\brecurr(?:ed|ing|ence|ences)\b|\b(?:second|third|fourth) "
                               r"occurrence\b|\bagain\b", re.I)
#: A marker preceded by this is a WATCH-CRITERION, not an event: "ship on
#: second occurrence", "defer until recurrence". Measured: without it WI-1's
#: criterion line counted as Pattern C recurring.
_CRITERION = re.compile(r"\b(?:on|until|upon|at)\s+(?:the\s+|a\s+)?\Z", re.I)
#: r3's in-place amendment that states a recurrence. `→ SHIPPED` is NOT one:
#: it records that the item was built, and a planned phase can build a
#: deferral that never came back (cpi-decisions.md line 974 is exactly that).
AMENDED = re.compile(r"🔁|\brecurred\b", re.I)
SHIPPED = re.compile(r"→ SHIPPED")
#: A CPI entry's citable key: `Pattern A`, `TS-1`, `WI-2`, `L1`, `H2`, `F-3`.
CPI_KEY = re.compile(r"\A(Pattern [A-Z]|[A-Z]{1,3}-\d+|[A-Z]\d+)\b")
_HEADING = re.compile(r"\A(#{1,6})\s+(.*)\Z")
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z*`(\"'])")
_TITLE = re.compile(r"^[ \t]*(?:-[ \t]*)?title:[ \t]*(.+?)[ \t]*$", re.M)
_ITEM_START = re.compile(r"^[ \t]*-[ \t]*id:[ \t]*([^\s#]+)", re.M)
_SLUG = re.compile(r"[a-z0-9][a-z0-9_]*(?:-[a-z0-9_]+)+")
_FENCED = re.compile(r"^[ \t]*```.*?^[ \t]*```[ \t]*$", re.M | re.S)


# --- sources (r4) ---------------------------------------------------------------

@dataclass
class Corpus:
    window: jb.Window
    records: list                 # je.ReviewRecord in window
    bag_threads: dict             # run_id -> {(repo, pr): Thread}
    repo_threads: dict            # (repo, pr) -> Thread, every harvest merged
    thread_dates: dict            # (repo, pr) -> [bag date]
    forge: dict = field(default_factory=dict)   # (repo, pr) -> Thread | None
    forge_errors: list = field(default_factory=list)
    use_forge: bool = True
    runner: object = None

    def thread_for(self, record) -> tuple[object, str]:
        """The record's thread: its own bag's harvest, else the forge. (thread, source)."""
        key = (record.repo, record.pr)
        own = self.bag_threads.get(record.run_id, {}).get(key)
        if own is not None:
            return own, "harvest"
        return self.forge_thread(key)

    def forge_thread(self, key) -> tuple[object, str]:
        if not self.use_forge:
            return None, "unreached (--no-forge)"
        if key not in self.forge:
            try:
                self.forge[key] = je.forge_thread(key[0], key[1], runner=self.runner)
            except je.JournalEvidenceError as exc:
                self.forge[key] = None
                self.forge_errors.append(f"{key[0]}#{key[1]}: {type(exc.__cause__).__name__}")
        return (self.forge[key], "forge") if self.forge[key] is not None else (None, "unreached (forge refused)")


def load(journal: je.JournalEvidence, window: jb.Window, *, use_forge: bool, runner) -> Corpus:
    records, bag_threads, merged, dates = [], {}, {}, defaultdict(list)
    units = sorted(((ref, journal.read(ref)) for ref in journal.units()), key=lambda p: p[1].date)
    for ref, unit in units:
        if unit.date < jb.RELIABILITY_FLOOR:
            continue
        records += [r for r in journal.review_records(ref) if r.date and window.holds(r.date)]
        threads = {(t.repo, t.pr): t for t in journal.threads(ref)}
        bag_threads[ref.run_id] = threads
        if not window.holds(unit.date):
            continue
        for key, t in threads.items():
            dates[key].append(unit.date)
            base = merged.get(key)
            comments = dict(base.comments) if base else {}
            comments.update(dict(t.comments))      # later bag wins: units are date-sorted
            merged[key] = je.Thread(t.repo, t.pr, "harvest", t.body or (base.body if base else ""),
                                    tuple(sorted(comments.items())))
    return Corpus(window, records, bag_threads, merged, dict(dates), use_forge=use_forge, runner=runner)


# --- reading a thread -------------------------------------------------------------

def block_of(text: str) -> str | None:
    m = PR_REVIEW_BLOCK.search(text)
    return m.group(1) if m else None


def judge_comment(thread, child_run_id: str) -> int | None:
    """The comment id whose `pr_review:` block carries this pass's nonce."""
    for cid, text in thread.comments:
        for m in PR_REVIEW_BLOCK.finditer(text):
            if run_id_in_block(m.group(1)) == child_run_id:
                return cid
    return None


def titles_in_block(block: str) -> dict[str, str]:
    """`id -> title` over the block's `findings:` section, each item bounded by the next `- id:`."""
    section = findings_section(block)
    starts = list(_ITEM_START.finditer(section))
    out = {}
    for k, m in enumerate(starts):
        body = section[m.end():starts[k + 1].start() if k + 1 < len(starts) else len(section)]
        t = _TITLE.search(body)
        if t:
            out[m.group(1).strip("'\"")] = t.group(1).strip("'\"")
    return out


def reflection_sections(text: str) -> list[str]:
    """Each `Post-Run Reflection` heading's section: to the next heading of its level or higher.

    FENCED BLOCKS ARE DROPPED FIRST. A review pass may post its `pr_review:`
    block after its reflection heading, and a fenced `title:` line is the
    block's record, not a sentence the run wrote about itself — measured, the
    first live run counted two such lines as recurrence claims.
    """
    lines, out, i = _FENCED.sub("", text).splitlines(), [], 0
    while i < len(lines):
        m = _HEADING.match(lines[i].strip())
        if m and "post-run reflection" in m.group(2).lower():
            level, j = len(m.group(1)), i + 1
            while j < len(lines):
                n = _HEADING.match(lines[j].strip())
                if n and len(n.group(1)) <= level:
                    break
                j += 1
            out.append("\n".join(lines[i + 1:j]))
            i = j
            continue
        i += 1
    return out


def sentences(section: str) -> list[str]:
    out = []
    for line in section.splitlines():
        line = re.sub(r"\A\s*(?:[-*]|\d+\.)\s+", "", line).strip()
        if line:
            out += [s.strip() for s in _SENTENCE.split(line) if s.strip()]
    return out


def _norm(text: str) -> str:
    return " ".join(text.split())


# --- r1: E1b ----------------------------------------------------------------------

@dataclass(frozen=True)
class Classified:
    key: str                  # "<child_run_id>:<index>" — publishable
    pr: str                   # "owner/name#N"
    finding_id: str           # ⚠ model-authored — never printed
    disposition: str
    status: str               # stated | new | no-self-account | unclassifiable
    reason: str               # for unclassifiable
    control: str              # stated | new | no-self-account — the predecessor's population rule
    carried: bool             # an earlier pass on this thread already carried the id
    title_source: str         # block | slug
    source: str               # harvest | forge | unreached …
    date: str
    title: str = ""           # ⚠ model-authored — samples only
    bullets: tuple = ()       # ⚠ — samples only


def _stated(title: str, bullets: list[set[str]]) -> bool:
    t = jmy.sig(title)
    return bool(t) and any(len(t & b) / len(t) >= jmy.ECHO_THRESHOLD for b in bullets)


def e1b(corpus: Corpus) -> list[Classified]:
    out = []
    for r in corpus.records:
        pr = f"{r.repo}#{r.pr}" if r.pr else "(no PR)"
        base = dict(pr=pr, date=r.date)
        if not r.pr:
            out += _unclassifiable(r, base, "the record names no pull request", "-")
            continue
        if not r.child_run_id:
            out += _unclassifiable(r, base, "the record carries no run nonce to find its comment by", "-")
            continue
        thread, source = corpus.thread_for(r)
        if thread is None:
            out += _unclassifiable(r, base, f"thread {source}", source)
            continue
        judge = judge_comment(thread, r.child_run_id)
        if judge is None:
            out += _unclassifiable(r, base, "the pass's own comment is not in the thread", source)
            continue
        by_id = dict(thread.comments)
        titles = titles_in_block(block_of(by_id[judge]) or "")
        before = [text for cid, text in thread.comments if cid < judge]
        lines = jmy.reflection_lines(before)
        bullets = [s for s in map(jmy.sig, lines) if s]
        control = [s for s in map(jmy.sig, jmy.reflection_lines([t for _, t in thread.comments])) if s]
        earlier = set()
        for text in before:
            for m in PR_REVIEW_BLOCK.finditer(text):
                earlier |= set(titles_in_block(m.group(1))) | set(_ITEM_START.findall(findings_section(m.group(1))))
        for k, (fid, disposition) in enumerate(r.findings):
            title = titles.get(fid)
            title_source = "block" if title else "slug"
            title = title or fid.replace("-", " ").replace("_", " ")
            status = ("no-self-account" if not bullets else
                      "stated" if _stated(title, bullets) else "new")
            ctl = ("no-self-account" if not control else
                   "stated" if _stated(title, control) else "new")
            out.append(Classified(f"{r.child_run_id}:{k}", pr, fid, disposition, status, "", ctl,
                                  fid in earlier, title_source, source, r.date, title, tuple(lines)))
    return out


def _unclassifiable(r, base, reason, source) -> list[Classified]:
    return [Classified(f"{r.child_run_id or r.run_id}:{k}", base["pr"], fid, disp, "unclassifiable",
                       reason, "unclassifiable", False, "-", source, base["date"])
            for k, (fid, disp) in enumerate(r.findings)]


# --- r2: recurrence claims ------------------------------------------------------------

@dataclass(frozen=True)
class Claim:
    key: str                  # "<owner/name>#<pr>:<comment id>:<n>" — publishable
    sentence: str             # ⚠ model-authored — stdout only
    status: str               # corroborated | uncorroborated
    by: str                   # "count" | "finding id" | ""
    note: str
    judge: bool               # the sentence is in a review pass's comment
    from_sweep: bool = False


def pick_repo(corpus: Corpus, requested: str | None) -> str | None:
    if requested:
        return requested
    counts = Counter(repo for repo, _ in corpus.repo_threads)
    return max(sorted(counts), key=lambda r: counts[r]) if counts else None


def repo_threads(corpus: Corpus, repo: str) -> list[tuple[object, str]]:
    """The repo's PR threads: every harvest in window, then the forge for the PRs
    only a typed record names."""
    out = [(t, "harvest") for key, t in sorted(corpus.repo_threads.items()) if key[0] == repo]
    have = {t.pr for t, _ in out}
    for pr in sorted({r.pr for r in corpus.records if r.repo == repo and r.pr and r.pr not in have}):
        thread, source = corpus.forge_thread((repo, pr))
        if thread is not None:
            out.append((thread, source))
    return out


def recurring_finding_ids(records) -> set[str]:
    """Finding ids at least two review passes carried — a computed recurrence."""
    passes = Counter(fid for r in records for fid in {f for f, _ in r.findings})
    return {fid for fid, n in passes.items() if n >= 2}


def corroborate(sentence: str, counts: dict[str, int | None], recurring: set[str]) -> tuple[str, str, str]:
    named = sorted(set(re.findall(r"\b[CIOS]-[0-9a-z]{8}\b", sentence)))
    for item in named:
        if (counts.get(item) or 0) >= 2:
            return "corroborated", "count", f"names {item}, count {counts[item]}"
    for slug in _SLUG.findall(sentence.lower()):
        if slug in recurring:
            return "corroborated", "finding id", "names a finding id two or more passes carried"
    if named:
        seen = ", ".join(f"{i} count {counts.get(i, 'unknown')}" for i in named)
        return "uncorroborated", "", f"names {seen}"
    return "uncorroborated", "", "names no tracked item and no recurring finding id"


def recurrence_claims(threads, counts, recurring) -> tuple[list[Claim], dict]:
    claims, reach = [], Counter()
    for thread, source in threads:
        reach[source] += 1
        for cid, text in thread.comments:
            judge = block_of(text) is not None
            n = 0
            for section in reflection_sections(text):
                for s in sentences(section):
                    if CLAIM.search(s):
                        status, by, note = corroborate(s, counts, recurring)
                        claims.append(Claim(f"{thread.repo}#{thread.pr}:{cid}:{n}", s, status, by, note, judge))
                        n += 1
    return claims, dict(reach)


# --- r3: the calibration ratio --------------------------------------------------------

@dataclass(frozen=True)
class Deferral:
    key: str                  # "cpi:<line>" or the tracked id — publishable
    origin: str               # "cpi" | "<store>"
    label: str                # CPI title (committed prose) or tracked id
    group: str                # recurred | never | unclassified
    reason: str
    evidence: str = ""        # CPI: "line N"


def _lines(section: pe.CpiSection):
    """(line number, text) per line of a section.

    THE UNIT IS THE LINE, NOT THE PARAGRAPH. The log writes one item per list
    line and runs lists without blank lines, so a paragraph holds several
    items: measured, a paragraph-level match credited *"Pattern B → recurrence
    logged"* to L1, whose own line on it says REJECTED.
    """
    return [(section.line + k, line) for k, line in enumerate(section.text.splitlines())]


def is_recurrence(line: str) -> bool:
    return any(not _CRITERION.search(line[:m.start()]) for m in RECURRENCE_MARKER.finditer(line))


def _cites(entry: pe.CpiDeferral, text: str) -> bool:
    key = CPI_KEY.match(entry.title)
    if key and re.search(rf"(?<![\w-]){re.escape(key.group(1))}(?![\w-])", text):
        return True
    return len(entry.title) >= 20 and entry.title in text


def cpi_groups(sections, deferrals, today: _dt.date) -> list[Deferral]:
    out = []
    for d in deferrals:
        later = [s for s in sections if s.line > d.section_line]
        evidence = next((n for s in later for n, line in _lines(s)
                         if _cites(d, line) and is_recurrence(line)), None)
        label = d.title[:80]
        if evidence is not None:
            out.append(Deferral(f"cpi:{d.line}", "cpi", label, "recurred", "a later line cites it with a recurrence marker", f"line {evidence}"))
        elif AMENDED.search(d.text):
            out.append(Deferral(f"cpi:{d.line}", "cpi", label, "recurred", "amended in place with a recurrence", f"line {d.line}"))
        elif SHIPPED.search(d.text):
            out.append(Deferral(f"cpi:{d.line}", "cpi", label, "unclassified",
                                "amended → SHIPPED — the log records the ship, not whether it recurred first"))
        else:
            out.append(_censor(f"cpi:{d.line}", "cpi", label, d.section_date, today))
    return out


def tracked_groups(items, unreadable, today: _dt.date) -> list[Deferral]:
    out = [Deferral(f"file:{u}", "tracked", u, "unclassified", "the item would not parse") for u in unreadable]
    for it in items:
        if it.count is None:
            out.append(Deferral(it.id, it.store, it.id, "unclassified", "`count` is not an integer"))
        elif it.count >= 2:
            out.append(Deferral(it.id, it.store, it.id, "recurred", f"count {it.count}"))
        else:
            out.append(_censor(it.id, it.store, it.id, it.filed, today))
    return out


def _censor(key, origin, label, date, today) -> Deferral:
    if not date:
        return Deferral(key, origin, label, "unclassified", "no date to measure its watch from")
    days = (today - _dt.date.fromisoformat(date)).days
    if days < CENSOR_DAYS:
        return Deferral(key, origin, label, "unclassified",
                        f"censored — watched {days} days, under the {CENSOR_DAYS}-day horizon")
    return Deferral(key, origin, label, "never", f"watched {days} days")


# --- hypotheses (r6) --------------------------------------------------------------------

def apply_e1b_hypotheses(found: list[Classified], hyps: list) -> dict:
    tally = Counter()
    for h in hyps:
        matches = [c for c in found if c.pr == h.get("pr") and c.finding_id == h.get("finding_id")
                   and c.status in ("stated", "new")]
        if not matches:
            tally["no classified finding to look up"] += 1
        elif all(c.status == h.get("claim") for c in matches):
            tally["computation agrees"] += 1
        else:
            tally["computation disagrees"] += 1
    return dict(tally)


def apply_claim_hypotheses(threads, claims, hyps, counts, recurring) -> tuple[list[Claim], dict]:
    by_comment = {(f"{t.repo}#{t.pr}", cid): text for t, _ in threads for cid, text in t.comments}
    have = {(c.key.rsplit(":", 1)[0], _norm(c.sentence)) for c in claims}
    added, tally = [], Counter()
    for k, h in enumerate(hyps):
        text = by_comment.get((h.get("pr"), h.get("comment_id")))
        sentence = _norm(str(h.get("sentence", "")))
        if text is None:
            tally["refused — comment not in the repo's threads"] += 1
            continue
        if not sentence or sentence not in _norm("\n".join(reflection_sections(text))):
            tally["refused — sentence not verbatim in that comment's reflection"] += 1
            continue
        if any(ck == f"{h['pr']}:{h['comment_id']}" and (sentence in s or s in sentence) for ck, s in have):
            tally["already in the population"] += 1
            continue
        status, by, note = corroborate(sentence, counts, recurring)
        added.append(Claim(f"{h['pr']}:{h['comment_id']}:h{k}", sentence, status, by, note,
                           block_of(text) is not None, from_sweep=True))
        tally["added"] += 1
    return added, dict(tally)


def apply_calibration_hypotheses(groups, sections, deferrals, hyps) -> tuple[list[Deferral], dict]:
    by_line = {d.line: d for d in deferrals}
    lines = {n: (s, line) for s in sections for n, line in _lines(s)}
    out, tally = {g.key: g for g in groups}, Counter()
    for h in hyps:
        entry = by_line.get(h.get("entry_line"))
        hit = lines.get(h.get("evidence_line"))
        if entry is None:
            tally["refused — entry_line is not a DEFERRED entry"] += 1
        elif hit is None or hit[0].line <= entry.section_line:
            tally["refused — evidence is not in a later section"] += 1
        elif not is_recurrence(hit[1]):
            tally["refused — evidence line carries no recurrence marker"] += 1
        elif out[f"cpi:{entry.line}"].group == "recurred":
            tally["already recurred"] += 1
        else:
            g = out[f"cpi:{entry.line}"]
            out[g.key] = Deferral(g.key, g.origin, g.label, "recurred", "sweep-supplied link, date and marker checked",
                                  f"line {h['evidence_line']}")
            tally["reclassified recurred"] += 1
    return list(out.values()), dict(tally)


# --- hand check -----------------------------------------------------------------------

def hand_agreement(computed: dict[str, str], labels: dict) -> str:
    matched = [(computed[k], v) for k, v in labels.items() if k in computed]
    if not matched:
        return "no hand labels matched a classified key"
    disagree = sum(a != b for a, b in matched)
    lo, hi = jb.wilson(disagree, len(matched))
    return (f"hand sample n={len(matched)} ({len(labels) - len(matched)} labels matched nothing), "
            f"disagreements {disagree} ({100 * disagree / len(matched):.0f}%, 95% CI {100 * lo:.0f}–{100 * hi:.0f}%)")


# --- the report --------------------------------------------------------------------------

def _share(label: str, k: int, n: int) -> str:
    if not n:
        return f"{label}: no denominator"
    lo, hi = jb.wilson(k, n)
    return f"{label}: {k}/{n} ({100 * k / n:.0f}%, 95% CI {100 * lo:.0f}–{100 * hi:.0f}%)"


def report_e1b(found: list[Classified], corpus: Corpus, hand, hyps) -> list[str]:
    rated = [c for c in found if c.status in ("stated", "new")]
    out = ["## r1 — E1b: typed findings already stated by the producing runs, or new",
           f"  population : {len(found)} typed findings in {len(corpus.records)} review-pr records "
           f"with structured_output, window {corpus.window.start}..{corpus.window.end}"]
    for status in ("no-self-account", "unclassifiable"):
        n = sum(c.status == status for c in found)
        out.append(f"  EXCLUDED {status:<16}: {n}")
    for reason, n in sorted(Counter(c.reason for c in found if c.status == "unclassifiable").items()):
        out.append(f"      {n:>5}  {reason}")
    sources = Counter(c.pr for c in found if c.source == "harvest"), Counter(c.pr for c in found if c.source == "forge")
    out.append(f"  thread source, per PR : harvest {len(sources[0])}, forge {len(sources[1])}"
               f"{'; forge refused ' + str(len(corpus.forge_errors)) if corpus.forge_errors else ''}")
    if rated:
        new = sum(c.status == "new" for c in rated)
        dates = sorted(c.date for c in rated)
        fig = jb.Proportion("E1b new to the judge", new, len(rated), corpus.window, dates[0], dates[-1])
        out.append("  " + jb.render(fig) + "   <- THE RATE")
        out.append("  " + jb.render(jb.Proportion("E1b already stated", len(rated) - new, len(rated),
                                                  corpus.window, dates[0], dates[-1])))
        for d in sorted({c.disposition for c in rated}):
            sub = [c for c in rated if c.disposition == d]
            out.append("    " + _share(f"new, disposition {d:<12}", sum(c.status == "new" for c in sub), len(sub)))
        for carried, label in ((False, "first raised on this pass"), (True, "carried from an earlier pass")):
            sub = [c for c in rated if c.carried is carried]
            out.append("    " + _share(f"new, {label}", sum(c.status == "new" for c in sub), len(sub)))
        ctl = [c for c in found if c.control in ("stated", "new")]
        out.append("  CONTROL — the predecessor's population rule (every non-judge comment, no cut at the pass):")
        out.append("    " + _share("new to the judge", sum(c.control == "new" for c in ctl), len(ctl)))
        out.append("    (judge_marginal_yield.py's 2026-08-16 figure: about half new — cpi-decisions.md § 2026-08-16)")
        out.append(f"  titles : {sum(c.title_source == 'block' for c in rated)} from the pass's pr_review block, "
                   f"{sum(c.title_source == 'slug' for c in rated)} from the id slug (block lacked the id)")
    out += ["  METHOD : judge_marginal_yield's rule, imported — a finding is STATED when ONE reflection or",
            f"           Decision Log bullet posted BEFORE the pass's comment covers >= {jmy.ECHO_THRESHOLD} of its",
            "           title's significant words. The judge's own comments are excluded.",
            "  BIAS   : LEXICAL — a finding the run described in other words scores NEW, so the NEW share is",
            "           an UPPER bound. Earlier refine runs answering an earlier pass count as the producing",
            "           runs, so a CARRIED finding is likelier STATED; the split above shows by how much."]
    if hand is not None:
        out.append("  " + hand_agreement({c.key: c.status for c in rated}, hand))
    if hyps is not None:
        out.append(f"  sweep hypotheses (finding ids to look up) : {hyps or 'none supplied'} "
                   "— the rate above is unchanged by them by construction")
    return out + [""]


def report_claims(repo, claims, reach, added, tally, hand) -> list[str]:
    out = [f"## r2 — the recurrence-claim check, repo {repo}",
           f"  threads read : {sum(reach.values())} ({', '.join(f'{k} {v}' for k, v in sorted(reach.items())) or 'none'})"]
    if not claims:
        return out + ["  no reflection sentence claims recurrence — no denominator", ""]
    corr = sum(c.status == "corroborated" for c in claims)
    out.append("  " + _share("claims corroborated (computed)", corr, len(claims)) + "   <- THE RATE")
    out.append(f"    by count {sum(c.by == 'count' for c in claims)}, by finding id "
               f"{sum(c.by == 'finding id' for c in claims)}; in a review pass's comment "
               f"{sum(c.judge for c in claims)}, in a producing run's {sum(not c.judge for c in claims)}")
    if tally is not None:
        both = claims + added
        out.append(f"  WITH THE SWEEP'S CLAIMS: {tally or 'none supplied'}")
        out.append("    " + _share("claims corroborated (computed + sweep-added population)",
                                   sum(c.status == "corroborated" for c in both), len(both)))
        out.append(f"    changed the computed result: {'YES' if added else 'no'}")
    out += ["  METHOD : a Post-Run Reflection sentence matching the claim pattern is CORROBORATED when it",
            "           names a tracked item with count >= 2, or a finding id >= 2 typed records carried.",
            "  BIAS   : a real recurrence described without an id is UNCORROBORATED, and a sentence that",
            "           describes the recurrence RULE is in the population — the rate is a LOWER bound."]
    if hand is not None:
        out.append("  " + hand_agreement({c.key: c.status for c in claims}, hand))
    out.append("  UNCORROBORATED — model-authored text, for the reader of this output; never publish it:")
    for c in claims + (added or []):
        if c.status == "uncorroborated":
            tag = " [sweep]" if c.from_sweep else ""
            out.append(f"    {c.key}{tag}  ({c.note})")
            out.append(f"        {c.sentence[:300]}")
    return out + [""]


def report_calibration(groups, today, tally, base, hand, sources) -> list[str]:
    out = [f"## r3 — the V1 calibration ratio, as of {today.isoformat()} ({CENSOR_DAYS}-day censoring horizon)",
           f"  reads : {sources}"]

    def block(label, gs):
        c = Counter(g.group for g in gs)
        ratio = f"{c['recurred'] / c['never']:.2f}" if c["never"] else "undefined (no never-recurred entry)"
        return [f"  {label:<24} recurred {c['recurred']:>4} : never-recurred {c['never']:>4}  -> ratio {ratio};"
                f"  unclassified {c['unclassified']:>4}; total {len(gs)} (= {c['recurred']} + {c['never']} + {c['unclassified']})"]
    cpi = [g for g in groups if g.origin == "cpi"]
    tracked = [g for g in groups if g.origin != "cpi"]
    out += block("CPI DEFERRED entries", cpi) + block("tracked items", tracked) + block("both", groups)
    for store in sorted({g.origin for g in tracked}):
        c = Counter(g.group for g in tracked if g.origin == store)
        out.append(f"    {store:<12} recurred {c['recurred']}, never {c['never']}, unclassified {c['unclassified']}")
    if tally is not None:
        out.append(f"  WITH THE SWEEP'S DEFERRALS TO RE-CHECK: {tally or 'none supplied'}")
        out += ["  " + line.strip() for line in block("both, with the sweep", base)]
        changed = Counter(g.group for g in base) != Counter(g.group for g in groups)
        out.append(f"    changed the computed result: {'YES' if changed else 'no'}")
    out += ["  METHOD : a CPI entry RECURRED when a LINE in a later section cites its key (`TS-1`, `Pattern A`)",
            "           or full title AND carries a recurrence marker that is not a watch-criterion (`ship on",
            "           second occurrence`), or its own text was amended with one (`→ SHIPPED` alone is not);",
            "           a tracked item when count >= 2. Neither seen: NEVER once watched for the horizon.",
            "  BIAS   : a recurrence logged without citing the entry is missed — NEVER is an upper bound and",
            "           the ratio a LOWER bound. Censoring only ever removes would-be NEVERs, so the ratio",
            "           over young entries is not comparable with the ratio over old ones."]
    if hand is not None:
        out.append("  " + hand_agreement({g.key: g.group for g in groups}, hand))
    out.append("  RECURRED:")
    for g in groups:
        if g.group == "recurred":
            out.append(f"    {g.key:<16} {g.reason}{' — ' + g.evidence if g.evidence else ''}   {g.label[:70]}")
    out.append("  UNCLASSIFIED, with the reason:")
    for g in groups:
        if g.group == "unclassified":
            out.append(f"    {g.key:<16} {g.reason}   {g.label[:70]}")
    return out + [""]


# --- emit modes ---------------------------------------------------------------------------

def emit_samples(found, claims, groups, size: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    rated = [c for c in found if c.status in ("stated", "new")]
    out = []
    for c in rng.sample(rated, min(size, len(rated))):
        out.append({"check": "e1b", "key": c.key, "pr": c.pr, "title": c.title,
                    "self_account_bullets": list(c.bullets), "computed": c.status})
    for c in rng.sample(claims, min(size, len(claims))):
        out.append({"check": "recurrence", "key": c.key, "sentence": c.sentence,
                    "computed": c.status, "note": c.note})
    for g in groups:
        if g.origin == "cpi" or g.group == "recurred":
            out.append({"check": "calibration", "key": g.key, "label": g.label,
                        "computed": g.group, "reason": g.reason, "evidence": g.evidence})
    return [json.dumps(o, ensure_ascii=False) for o in out]


def emit_reflections(corpus: Corpus) -> list[str]:
    out = []
    keys = set(corpus.repo_threads) | {(r.repo, r.pr) for r in corpus.records if r.pr}
    for key in sorted(keys):
        thread = corpus.repo_threads.get(key)
        source = "harvest"
        if thread is None:
            thread, source = corpus.forge_thread(key)
        if thread is None:
            continue
        for cid, text in thread.comments:
            for section in reflection_sections(text):
                out.append(json.dumps({"pr": f"{key[0]}#{key[1]}", "comment_id": cid, "source": source,
                                       "author": "review-pr" if block_of(text) else "producing run",
                                       "reflection": section}, ensure_ascii=False))
    return out


# --- main ---------------------------------------------------------------------------------

def main(argv: list[str] | None = None, *, today: _dt.date | None = None, runner=None, stdin=None) -> int:
    ap = argparse.ArgumentParser(prog="self_report_measure", description=__doc__.split("\n")[0])
    ap.add_argument("--root", help="a journal root; default is the configured one")
    ap.add_argument("--planning", help=f"the planning repo; default is the sibling {pe.PLANNING_REPO}")
    ap.add_argument("--since", metavar="YYYY-MM-DD", help=f"never earlier than {jb.RELIABILITY_FLOOR}")
    ap.add_argument("--until", metavar="YYYY-MM-DD", help="window end, inclusive; default today (UTC)")
    ap.add_argument("--repo", help="r2's repo as owner/name; default: the one with the most harvested threads")
    ap.add_argument("--no-forge", action="store_true", help="read harvested threads only")
    ap.add_argument("--emit", choices=("report", "samples", "reflections"), default="report")
    ap.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stdin", action="store_true",
                    help='read {"hand": {...}, "hypotheses": {...}} as JSON from standard input')
    a = ap.parse_args(argv)
    now = today or _dt.datetime.now(_dt.timezone.utc).date()
    try:
        window = jb.make_window(a.since or jb.RELIABILITY_FLOOR, a.until, now)
    except ValueError as exc:
        print(f"self_report_measure: bad window — {exc}", file=sys.stderr)
        return 2
    inputs = {}
    if a.stdin:
        try:
            inputs = json.load(stdin or sys.stdin)
        except ValueError as exc:
            print(f"self_report_measure: --stdin is not JSON — {exc}", file=sys.stderr)
            return 2
    hand, hyps = inputs.get("hand") or {}, inputs.get("hypotheses")
    try:
        journal = je.open_journal(a.root)
        planning = pe.open_planning(a.planning)
        corpus = load(journal, window, use_forge=not a.no_forge, runner=runner)
        items, unreadable = planning.tracked_items()
        elsewhere, _ = planning.sibling_tracked_items()
        sections, deferrals = planning.cpi_log()
    except (je.JournalEvidenceError, pe.PlanningEvidenceError) as exc:
        print(f"self_report_measure: {exc}", file=sys.stderr)
        return 2
    if not corpus.records:
        print(f"self_report_measure: no review-pr record with structured_output in "
              f"{window.start}..{window.end} under {journal.label} — this run measured nothing", file=sys.stderr)
        return 2
    if a.emit == "reflections":
        print("\n".join(emit_reflections(corpus)))
        return 0

    found = e1b(corpus)
    # r2 LOOKS UP an id in every store it can read — a repo's reflections name
    # that repo's items — while r3's POPULATION stays the planning corpus's.
    counts = {it.id: it.count for it in elsewhere + items}
    recurring = recurring_finding_ids(corpus.records)
    repo = pick_repo(corpus, a.repo)
    threads = repo_threads(corpus, repo) if repo else []
    claims, reach = recurrence_claims(threads, counts, recurring)
    groups = cpi_groups(sections, deferrals, now) + tracked_groups(items, unreadable, now)

    if a.emit == "samples":
        print("\n".join(emit_samples(found, claims, groups, a.sample_size, a.seed)))
        return 0

    added, claim_tally, base, cal_tally, e1b_tally = [], None, groups, None, None
    if hyps is not None:
        e1b_tally = apply_e1b_hypotheses(found, hyps.get("e1b") or [])
        added, claim_tally = apply_claim_hypotheses(threads, claims, hyps.get("recurrence") or [], counts, recurring)
        base, cal_tally = apply_calibration_hypotheses(groups, sections, deferrals, hyps.get("calibration") or [])

    out = ["# The self-report and recurrence, measured — three rates, asserted against computed",
           "",
           f"reads   : journal root {journal.label} (review-pr records and harvested threads, through journal_evidence)",
           f"          planning corpus {planning.label} (tracked stores and the CPI log, through planning_evidence)",
           "          the forge, through the harvest's own fetch, for a PR no in-window bag harvested"
           + (" — DISABLED (--no-forge)" if a.no_forge else ""),
           "writes  : nothing — stdout only",
           f"window  : {window.start}..{window.end}" + (f"  (requested start {window.requested_start} CLAMPED to "
                                                         f"the reliability floor)" if window.clamped else ""),
           f"as of   : {now.isoformat()}",
           ""]
    out += report_e1b(found, corpus, hand.get("e1b") if a.stdin else None, e1b_tally)
    out += report_claims(repo, claims, reach, added, claim_tally, hand.get("recurrence") if a.stdin else None)
    out += report_calibration(groups, now, cal_tally, base, hand.get("calibration") if a.stdin else None,
                              f"{len(deferrals)} CPI DEFERRED entries; {len(items)} tracked items"
                              f" ({len(unreadable)} unreadable); r2 also looks ids up in"
                              f" {len(elsewhere)} items of sibling repos' stores")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
