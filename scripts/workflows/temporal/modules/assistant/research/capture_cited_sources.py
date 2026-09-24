"""Capture the sources a research paper cited, inside the run that cited them.

WHY IN-WINDOW RATHER THAN AT HARVEST. The content store's guarantee is that the
bytes on disk are the bytes a claim can be re-checked against. With model-native
reads that can never be a READ-TIME guarantee — the analyst reads an EXTRACTION
returned by its fetch tool, and fleet code never sees it — so the honest
guarantee is fetch-time, recorded as `capture="harvest"`. What in-window capture
buys is the WINDOW: seconds after the claim was made, inside the run that made
it, instead of whenever a later harvest happens to run. That does not change the
guarantee's kind; it shrinks the interval in which a source can change or vanish.

THE INPUT IS A SIDECAR, NOT THE PAPER'S PROSE, AND THAT IS THE DESIGN DECISION
HERE. The store REFUSES a citation with no quoted span — "a citation with no
quoted span has nothing for `verify` to re-check, which is the whole reason the
bytes were stored" — so a URL alone is not capturable. Papers carry URLs and
carry verbatim spans, but nothing pairs them machine-readably, and pairing them
by proximity would be a GUESS that produces a citation whose span is not in the
bytes: a guaranteed `span-missing` finding manufactured by the capture path. The
run writes the pairs it already knows — it verified every span against the
bytes at a resolved SHA when it wrote the paper, so the (url, quote, sha) tuple
already exists in the run's hands and the sidecar is where it puts it down.

⚠ CAPTURE MUST NEVER FAIL THE RESEARCH RUN. The paper is the deliverable; the
capture is evidence about it. A source that 404s, times out, redirects to a
refused address or trips any other part of the fetch policy is a RECORDED
capture-failure on that citation. A dead research run because a footnote link
rotted is the wrong failure, and it is the one this module is written to make
impossible: every per-citation error is caught, and the sweep returns a report
rather than raising.

⚠ AND THE OPPOSITE FAILURE IS NOT ALLOWED TO BE SILENT EITHER. The property above
made the whole path fail QUIETLY: `NOT RUN — no citations.json` was a line in the
parent's notes that nobody read, and every real research run captured nothing.
Measured on skyynet-master-planning#36 — 28 cited sources, no sidecar, an empty
store, a green run. `record_capture_gap` is the answer: when the run's papers
cite sources and NONE reached the store, a typed gap event marks the bag's
content-store coverage incomplete. The two rules compose: a per-citation failure
is a row in the report; a store with nothing in it for a paper full of URLs is a
gap. Neither one raises out of here.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..assistant_activities import default_branch, run_bounded
from .research_activities import in_worktree

#: The run's machine-readable citation list, at the root of the pool it wrote.
#: ONE PER RUN rather than one per paper: a run may touch several papers, and a
#: single list is what the run can write once at the end without re-opening each.
SIDECAR_NAME = "citations.json"

#: What a well-formed row carries. The first three are REQUIRED — a row missing
#: any of them is not capturable and is counted as skipped. `sha` is the commit
#: the span was byte-checked against, recorded so the row states its own
#: reproducibility; `paper` is the `raw/<topic>.md` the claim lives in. Both are
#: optional because a rendered page has no SHA and a synthesis has no single
#: paper — but when present they must be well-formed, and `validate_rows` says so.
REQUIRED_FIELDS = ("claim_id", "quote", "url")
OPTIONAL_FIELDS = ("sha", "paper")

_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
#: What "well-formed" means per optional field, keyed by the tuple above so a
#: field added there without a check here is a KeyError at the first row that
#: carries it, not a silently unvalidated column. Each returns the problem, or "".
_OPTIONAL_FIELD_PROBLEM = {
    "sha": lambda v: "" if _SHA_RE.match(v) else (
        "is not a full 40-hex commit — the row states no reproducible ref"),
    "paper": lambda v: "" if v.startswith("raw/") else "is not under raw/",
}
_URL_RE = re.compile(r"https?://[^\s<>()\[\]`'\"]+")

#: The gap's write path and destination. The path names WHAT was lost — the
#: run's cited sources — and the destination names WHERE they were meant to land.
#: The store label is the `Destination.store` vocabulary's shape (`tracked_issues`),
#: NOT the store's on-disk segment: composing that here would be a reach into the
#: content store from outside its boundary, and a guard says so.
GAP_WRITE_PATH = "research:cited-sources"
CONTENT_STORE = "content_store"


@dataclass
class CaptureReport:
    """What the sweep did, in a shape a parent can put in its notes."""
    captured: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)   # (url, reason)
    skipped: int = 0
    sidecar: Path | None = None
    parse_error: str = ""
    #: Distinct source URLs the run's papers name — the denominator of coverage.
    #: `None` means the paper set could not be read, which is different from 0.
    cited: int | None = None
    #: Distinct URLs that reached the store — the numerator. `captured` counts
    #: ROWS (two claims on one source are two citations); coverage compares
    #: sources with sources, so a paper quoting one page twice is 1/1, not 2/1.
    captured_urls: set[str] = field(default_factory=set)
    #: The papers `cited` was counted over, so a reader can check the count.
    papers: list[str] = field(default_factory=list)
    #: WHY rows were skipped, and any optional field that was present and wrong
    #: on a row that was still captured. Not failures — nothing was attempted —
    #: and not silent either: each names the run's own artifact defect.
    malformed: list[str] = field(default_factory=list)

    @property
    def store_is_empty_for_a_cited_paper(self) -> bool:
        """THE GUARD'S PREDICATE. The paper names sources and NONE was stored.

        `cited is None` counts as cited: if the paper set could not be read then
        coverage is unknown, and an EMPTY store under unknown coverage must not
        read as complete on the strength of a check that did not run. But the
        store having to be EMPTY is the whole predicate, and it holds on that
        arm too — a run that captured ten rows and then lost its `git diff` to
        a timeout has a store with bytes in it, which is not `SOURCES_UNCAPTURED`
        by that class's own definition; its note says `coverage UNKNOWN` and
        that is the true statement. A run whose papers cite nothing (a
        retirement-only cycle, a synthesis rewrite) is NOT this case: nothing
        was there to capture. And a PARTIAL sidecar — two rows for a paper that
        names twenty sources — is not this case either: the coverage figure in
        the note carries it, and the gap is reserved for the store holding
        nothing at all.
        """
        if self.captured:
            return False
        return self.cited is None or self.cited > 0

    def coverage_line(self) -> str:
        if self.cited is None:
            return "coverage UNKNOWN — the run's paper set could not be read"
        if self.cited == 0:
            return "coverage n/a — the run's papers cite no source by URL"
        return f"coverage {len(self.captured_urls)}/{self.cited} cited sources captured"

    #: What the note leads with whenever the gap fires. ONE STRING, prefixed by
    #: `_loud` on every arm of `as_note`, so the note and `record_capture_gap`
    #: cannot disagree about when the gap fires: both read the predicate above.
    #: The malformed-sidecar arm returned early without it once — the gap fired
    #: and the note said only `NOT RUN`, which is the quiet line this banner
    #: exists to replace.
    GAP_BANNER = ("⚠ CONTENT STORE EMPTY FOR A CITED PAPER — the bag is marked "
                  "INCOMPLETE (gap: sources_uncaptured). ")

    def _loud(self, note: str) -> str:
        if self.store_is_empty_for_a_cited_paper:
            return self.GAP_BANNER + note
        return note

    def as_note(self) -> str:
        cov = self.coverage_line()
        if self.parse_error:
            return self._loud(
                f"source capture: NOT RUN — {self.parse_error}. The paper is "
                f"unaffected; no citation was captured for this run. {cov}.")
        if self.sidecar is None:
            return self._loud(
                "source capture: NOT RUN — no `citations.json` beside the paper. "
                "The run cited sources it did not pair with quoted spans, so "
                f"nothing could be stored against a claim. {cov}.")
        bits = [f"{self.captured} captured"]
        if self.failed:
            bits.append(f"{len(self.failed)} failed")
        if self.skipped:
            bits.append(f"{self.skipped} skipped")
        note = self._loud("source capture: " + ", ".join(bits) + f". {cov}.")
        for url, reason in self.failed[:5]:
            note += f"\n  FAILED {url} — {reason}"
        if len(self.failed) > 5:
            note += f"\n  … and {len(self.failed) - 5} more"
        for why in self.malformed[:5]:
            note += f"\n  MALFORMED {why}"
        return note


def read_sidecar(pool_dir: Path) -> tuple[list[dict], str]:
    """`(rows, error)` — never raises, because a malformed sidecar is a finding.

    A run that wrote unparseable JSON has produced a bad artifact, not a reason
    to lose the paper it also produced.
    """
    side = pool_dir / SIDECAR_NAME
    if not side.is_file():
        return [], ""
    try:
        loaded = json.loads(side.read_text(encoding="utf-8"))
    except Exception as e:
        return [], f"{SIDECAR_NAME} is not readable JSON ({e})"
    if not isinstance(loaded, list):
        return [], f"{SIDECAR_NAME} must be a JSON array of citation objects"
    return [r for r in loaded if isinstance(r, dict)], ""


def validate_rows(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """`(capturable, problems)` — the sidecar's well-formedness, row by row.

    REPORTED, NEVER RAISED, for the module's reason: the sidecar is the run's
    artifact, and a wrong row is a finding about that artifact rather than a
    reason to stop the sweep over the rows beside it. A row lands in
    `capturable` only when every required field is a non-empty string; an
    optional field that is present but wrong (a 7-char SHA, a `paper` outside
    `raw/`) is a problem on a row that is STILL captured — the fetch does not
    need the SHA, and losing the bytes over a bookkeeping field would be the
    capture path manufacturing its own gap.
    """
    capturable: list[dict] = []
    problems: list[str] = []
    for i, row in enumerate(rows):
        missing = [k for k in REQUIRED_FIELDS
                   if not str(row.get(k) or "").strip()]
        if missing:
            problems.append(f"row {i}: missing {missing}")
            continue
        url = str(row["url"]).strip()
        # SCHEME AND NO WHITESPACE, nothing stricter: a URL with parentheses or
        # brackets in its path is legal and fetchable, and refusing it here
        # would be the capture path dropping a real source over a lint rule.
        if not url.startswith(("http://", "https://")) or any(c.isspace() for c in url):
            problems.append(f"row {i}: url is not an http(s) URL: {url!r}")
            continue
        for name in OPTIONAL_FIELDS:
            value = str(row.get(name) or "").strip()
            if value and (why := _OPTIONAL_FIELD_PROBLEM[name](value)):
                problems.append(f"row {i}: {name} {value!r} {why}")
        capturable.append(row)
    return capturable, problems


def papers_changed(pool_dir: Path, worktree: Path, base: str) -> list[Path] | None:
    """The `raw/*.md` papers THIS RUN wrote or changed, from git — or `None`.

    THE POPULATION IS THE DIFF, NOT THE POOL. A pool carries every paper ever
    written into it, and the corpus this fleet reads has 25 that predate the
    sidecar; counting their URLs would trip the guard on every run over a mature
    pool, for history no run can fix. The papers on the branch against the
    default branch are exactly the ones whose citations the capture describes —
    "the paper that MERGES", in the entrypoint's words.

    `None` MEANS UNREADABLE, NOT EMPTY. A `git` that fails here leaves the
    coverage unknown, and the report treats unknown as incomplete rather than
    as zero-cited-so-nothing-to-do.
    """
    try:
        rel = pool_dir.resolve().relative_to(worktree.resolve())
    except ValueError:
        return None
    proc = run_bounded(
        ["git", "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD",
         "--", str(rel / "raw")],
        cwd=worktree)
    if proc.returncode != 0:          # includes the 124 a hang is rendered as
        return None
    return [worktree / line.strip() for line in proc.stdout.splitlines()
            if line.strip().endswith(".md")]


def cited_sources(papers: list[Path]) -> int:
    """Distinct source URLs across the papers — the coverage denominator.

    URLS, NOT CITATION MARKERS. A `[A6]` marker is the paper's own vocabulary
    and two papers number theirs differently; a URL is what the run could have
    fetched, so it is the honest count of what the store could have held. A
    source cited twice is one source, which is also how the store sees it.
    """
    urls: set[str] = set()
    for paper in papers:
        if paper.is_file():
            urls.update(m.rstrip(".,;:") for m in
                        _URL_RE.findall(paper.read_text(encoding="utf-8",
                                                        errors="replace")))
    return len(urls)


def capture_cited_sources(*, pool_dir: Path, bag, stage: str,
                          capture_fn=None, policy=None,
                          worktree: Path | None = None,
                          base: str | None = None) -> CaptureReport:
    """Fetch and store every source the run paired with a quoted span.

    `capture_fn` IS INJECTED so this module can be driven without a network and
    without importing the fetcher into a test's process. Production passes
    `journal.capture_source`; the default resolves it lazily for the same reason
    the fetcher is kept off `verify`'s import closure.

    `worktree` AND `base` TOGETHER NAME THE RUN'S PAPER SET, for the coverage
    figure and the guard. Both optional so the sweep can be driven over a bare
    pool with no git behind it — then `cited` stays `None` and the report says
    coverage is unknown, which is the truth about a pool nobody diffed.
    """
    if (worktree is None) != (not base):
        raise ValueError(f"`worktree` and `base` name the paper set TOGETHER; got "
                         f"worktree={worktree!r}, base={base!r}. One without the "
                         f"other would leave coverage silently unknown.")
    report = CaptureReport()
    if worktree is not None and base:
        papers = papers_changed(pool_dir, worktree, base)
        if papers is not None:
            report.papers = [str(p.relative_to(worktree)) for p in papers]
            report.cited = cited_sources(papers)

    rows, err = read_sidecar(pool_dir)
    if err:
        report.parse_error = err
        return report
    if not rows:
        return report
    report.sidecar = pool_dir / SIDECAR_NAME

    capturable, report.malformed = validate_rows(rows)
    report.skipped = len(rows) - len(capturable)

    if capture_fn is None:                       # pragma: no cover - thin binding
        from common.journal import capture_source as capture_fn      # noqa: PLC0415

    for row in capturable:
        url = str(row.get("url")).strip()
        quote = str(row.get("quote")).strip()
        claim_id = str(row.get("claim_id")).strip()
        try:
            capture_fn(bag=bag, stage=stage, claim_id=claim_id, quote=quote,
                       url=url, policy=policy)
            report.captured += 1
            report.captured_urls.add(url)
        except Exception as e:                   # noqa: BLE001 - the whole point
            # EVERY exception, deliberately. The fetch policy raises its own
            # refusals, the store raises its own, and a bug in either is still
            # not a reason to lose a completed paper. The reason is recorded so
            # an operator can tell a rotted link from a policy refusal.
            report.failed.append((url, f"{type(e).__name__}: {e}"))
    return report


def record_capture_gap(report: CaptureReport, *, emitter, pool_dir: Path) -> bool:
    """Mark the bag incomplete when a cited paper left the store empty. Returns
    whether a gap was recorded.

    THE LOUDNESS, AND WHERE IT STOPS. A gap event with `GapClass.SOURCES_
    UNCAPTURED` goes through `Emitter.record_gap`, which writes the event and
    sets the bag's `incomplete` flag — the same contract the harvest uses for a
    surface it could not read. `lost_bytes` is 0 because the count is UNKNOWN:
    the bytes were never fetched, so nothing measured them.

    NOT RECORDED for a per-citation failure with the rest captured, and not
    recorded for a paper that cites nothing — the first is a row in the report
    and the second is a store correctly holding nothing. The predicate is the
    report's own, so the note and the gap cannot disagree about when it fires.

    ⚠ A GAP THAT CANNOT BE WRITTEN IS CASE (d) AND PROPAGATES. `record_gap`
    raises `JournalUnwritable` when the flag cannot land; that is the one
    exception this module lets out, because a silent failure to record a gap is
    the exact thing the gap exists to prevent. `capture_into_the_run_bag`
    turns it into a note rather than a dead run.
    """
    if not report.store_is_empty_for_a_cited_paper:
        return False
    from common.journal.events import Destination, GapClass       # noqa: PLC0415
    emitter.record_gap(write_path=GAP_WRITE_PATH,
                       gap_class=GapClass.SOURCES_UNCAPTURED,
                       destination=Destination(store=CONTENT_STORE,
                                               address=str(pool_dir)),
                       lost_bytes=0,
                       detail=report.coverage_line())
    return True


def capture_into_the_run_bag(*, research_dir: Path, repo_root: Path, worktree: Path,
                             bag, emitter=None, base: str | None = None,
                             capture_fn=None) -> list[str]:
    """The whole in-window capture, for EVERY research entrypoint: anchor the
    pool into the run's worktree, sweep the sidecar, record the gap, and return
    the notes the entrypoint prints. NEVER RAISES.

    ONE OWNER, THREE CALLERS. `run_research.py`, `run_research_draft.py` and
    `run_research_refine.py` each open a bag, cut a worktree and dispatch the
    prompts that write `citations.json`; a capture that lived inline in one of
    them left the other two dispatching a sidecar nothing read — the #36 shape
    again, on a supported path, with no note at all. The family ruling in
    `run_build_draft.py` makes the standalone children real entrypoints, so the
    capture is a function they call rather than a block they copy. A standalone
    draft captures the draft's citations and a standalone refine the refined
    paper's: each bag records what ITS run cited, which is the truth about that
    run even when a later run changes the paper.

    ⚠ THE FAILURE PATH IS AS LOUD AS THE FOUND-NOTHING PATH. The sweep can die
    before it reads a row — the worktree may be gone, the emitter may be
    missing — and the first version of this block answered every one of those
    with *"no gap could be recorded"* and a complete-looking bag: the silent
    empty store, moved to the except branch. Here a dead sweep yields an EMPTY
    report (`cited=None`, `captured=0`), which is the predicate's
    unknown-and-empty arm, so the gap still fires. Only a gap that itself cannot
    be written ends without one, and that line says so in the same voice as the
    gap.

    ⚠ AND A DEAD `gh` IS NOT A DEAD SWEEP. `default_branch` asks `gh` — a network
    call — and it names only the DENOMINATOR: the paper set the coverage figure
    is counted over. The second version of this block resolved it inside the
    sweep's guard, so a `gh` failure skipped the sweep, fetched nothing, and
    recorded `sources_uncaptured` over a sidecar that was capturable the whole
    time — the capture path manufacturing the empty store it exists to detect.
    Now a failed resolution is a NOTE, the sweep runs with no paper set
    (`cited=None`, coverage UNKNOWN), every capturable row is still fetched, and
    the gap fires only when the store is genuinely empty afterwards.

    `emitter` DEFAULTS TO THE RUN'S REGISTERED ONE, which `open_run_bag`
    registers — never a second `Emitter.for_run`, which would allocate a second
    writer subfolder and split the run's events across two. `base` and
    `capture_fn` are injected for the same reason the sweep injects them: so the
    path can be driven with no `gh` and no network.
    """
    notes: list[str] = []
    pool = research_dir
    # AN EMPTY REPORT IS THE DEAD-SWEEP REPORT: `cited=None`, `captured=0` — the
    # predicate's unknown-and-empty arm. It is replaced only if the sweep returns.
    report = CaptureReport()
    sweep_ran = False
    try:
        pool = in_worktree(research_dir, repo_root, worktree)
        paper_set: dict = {"worktree": worktree, "base": base}
        if base is None:
            try:
                paper_set["base"] = f"origin/{default_branch(repo_root)}"
            except Exception as exc:                  # noqa: BLE001 - the denominator only
                # The sweep goes on WITHOUT a paper set: `cited` stays `None`,
                # the note says coverage is UNKNOWN, and the rows are fetched.
                paper_set = {"worktree": None, "base": None}
                notes.append(f"⚠ source capture: the default branch could not be "
                             f"resolved ({type(exc).__name__}: {exc}), so the run's "
                             f"paper set was not read and coverage is UNKNOWN. The "
                             f"sidecar was still swept.")
        report = capture_cited_sources(pool_dir=pool, bag=bag, stage="research",
                                       capture_fn=capture_fn, **paper_set)
        sweep_ran = True
        notes.append(report.as_note())
    except Exception as exc:                          # noqa: BLE001 - never fails the run
        notes.append(f"⚠ source capture: NOT RUN — the sweep itself failed "
                     f"({type(exc).__name__}: {exc}). The paper is unaffected; the "
                     f"content store holds NOTHING for this run and coverage is UNKNOWN.")

    try:
        if emitter is None:
            from common.journal.emit import current_emitter          # noqa: PLC0415
            emitter = current_emitter()
        if emitter is None:
            raise RuntimeError("no emitter is registered for this run — open_run_bag "
                               "did not register one, so the gap has nowhere to land")
        recorded = record_capture_gap(report, emitter=emitter, pool_dir=pool)
        if recorded and not sweep_ran:
            # `as_note` was never reached on this arm, so the gap says so here,
            # in the ONE banner string the note leads with when the sweep ran
            # and found nothing — a second spelling would drift from it.
            notes.append(CaptureReport.GAP_BANNER.strip())
    except Exception as exc:                          # noqa: BLE001 - never fails the run
        notes.append(f"⚠ the sources_uncaptured gap could NOT be recorded "
                     f"({type(exc).__name__}: {exc}). The bag does NOT say its content "
                     f"store is incomplete — read it as incomplete.")
    return notes
