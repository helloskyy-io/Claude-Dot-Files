"""Paper + `citations.json` → capture → offline `verify`, in skyynet-master-planning#36's shape.

THE REFERENCE CASE. #36 ("research: Self Improvement — measured baseline and
method transfer", merged 2026-09-15) is the run that proved the store was
empty: 28 cited sources, every quoted span byte-checked at a pinned SHA by the
run itself, and no `citations.json` — so `capture_cited_sources` reported `NOT
RUN`, nothing went red, and bag `729f3eaa…` holds no bytes for any of them. The
fixture under `tests/fixtures/pr36_citations/` is a sidecar in the SHAPE that
run should have written — five (claim, verbatim span, SHA-pinned URL) rows over
four sources, one source quoted twice — with the bytes each URL "served".

⚠ EVERY BYTE OF THE FIXTURE IS SYNTHETIC, AND THAT IS DELIBERATE. The first
version froze the real files four of #36's URLs served (98 KB of a metrics
spec, an SDK types module, a triage cron, a routing module) — full third-party
files, under Apache-2.0 and MIT, committed to a PUBLIC repo with none of the
notices those licences require. The mechanism under test needs bytes that
CONTAIN the quoted spans; it does not need the bytes any real URL served. So
the four sources are fabricated here, their URLs sit under RFC 2606's reserved
`.invalid` host so nothing can resolve them by accident, each row's `sha` is
its file's sha1 standing in for a commit, and `sources.json` pins sha256 per
file so an edited fixture fails before it can make `verify` pass. The proof on
REAL citations is not this test — it is SN-PM3's next research run, with the
sidecar writer in place, populating a real content store.

WHAT IS REAL AND WHAT IS SCAFFOLDING, stated so nobody reads more into a green
run than it proves. REAL: the store, the citation record, the gap emitter,
`verify` and the verify entrypoint — all production code, none substituted —
and the call shape `run_research.py` makes (`origin/main` resolves against a
real remote). SCAFFOLDING: the fetch layer — `_fixture_fetch` returns the
fixture bytes for a URL instead of opening a socket, and it is the ONLY
substitution — the bytes themselves, and the paper file the tmp pool carries,
which is a stub naming the fixture's four sources.

THE GUARD'S TWO DIRECTIONS ARE BOTH DEMONSTRATED. Forward: sidecar present →
five citations stored → `verify` resolves every one with the network denied at
the C library and reports coverage. Reverse: the same cited paper with no
sidecar → `record_capture_gap` fires, the bag is marked incomplete, and a typed
`sources_uncaptured` gap event is on disk. And the invariant between them: one
row whose fetch fails is a recorded capture-failure with the other four stored,
no gap, no exception.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from modules.assistant.research.capture_cited_sources import (
    GAP_WRITE_PATH, SIDECAR_NAME, capture_cited_sources, record_capture_gap)
from modules.journal.bag import LABEL_GAP, open_bag
from modules.journal.citations import read_citations
from modules.journal.content_activities import capture_fetched_source
from modules.journal.emit import Emitter
from modules.journal.events import EVENTS_FILE, EventKind, GapClass, decode_event
from modules.journal.verify import EXIT_OK, VERIFIED, verify_bag

COMPONENT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = COMPONENT_ROOT / "tests" / "fixtures" / "pr36_citations"
ENTRYPOINT = COMPONENT_ROOT / "scripts" / "verify_citations.py"

assert ENTRYPOINT.is_file(), f"the verify entrypoint is not at {ENTRYPOINT}"

ROWS: list[dict] = json.loads((FIXTURE / SIDECAR_NAME).read_text(encoding="utf-8"))
SOURCES: dict[str, dict] = json.loads(
    (FIXTURE / "sources.json").read_text(encoding="utf-8"))["sources"]
URLS = sorted({r["url"] for r in ROWS})


def _bytes_for(url: str) -> bytes:
    """The fixture bytes the URL stands for, checked against the manifest.

    The sha256 check is what makes the fixture TAMPER-EVIDENT rather than merely
    present: a fixture file edited to make a span match would fail here before
    it could make `verify` pass.
    """
    entry = SOURCES[url]
    data = (FIXTURE / entry["file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry["sha256"], (
        f"fixture bytes for {entry['file']} no longer match the manifest — the "
        f"source was altered, and every span check over it is void")
    return data


def _fixture_fetch(*, bag, stage, claim_id, quote, url, policy=None):
    """`capture_source` with the network replaced by the frozen bytes. Nothing
    downstream of the fetch is substituted."""
    return capture_fetched_source(bag=bag, stage=stage, claim_id=claim_id,
                                  quote=quote, source_ref=url, data=_bytes_for(url))


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          timeout=60, env={**os.environ,
                                           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                                           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
    assert proc.returncode == 0, f"git {' '.join(args)} failed: {proc.stderr}"
    return proc.stdout


def _run_tree(tmp_path: Path, *, with_sidecar: bool, cite: bool = True) -> tuple[Path, Path]:
    """A worktree the way a research run leaves one: `origin/main` holding the
    pool before the run, HEAD holding the paper the run wrote (and its sidecar).

    `(worktree, pool)`. The remote is real so `origin/main` resolves exactly as
    `run_research.py` asks for it — the call shape is the production one.
    """
    remote = tmp_path / "remote.git"
    remote.mkdir()
    _git(remote, "init", "--bare", "-q", "-b", "main")
    wt = tmp_path / "worktree"
    wt.mkdir()
    _git(wt, "init", "-q", "-b", "main")
    pool = wt / "development" / "self-improvement" / "research"
    (pool / "raw").mkdir(parents=True)
    (pool / "raw" / "older_paper.md").write_text(
        "# An older paper\nCites https://example.org/legacy — predates the sidecar.\n",
        encoding="utf-8")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", "pool before the run")
    _git(wt, "remote", "add", "origin", str(remote))
    _git(wt, "push", "-q", "-u", "origin", "main")

    _git(wt, "checkout", "-q", "-b", "research/self-improvement")
    body = "# Measured baseline and method transfer\n\n"
    if cite:
        body += "".join(f"- [{r['claim_id']}] {r['url']} — \"{r['quote']}\"\n" for r in ROWS)
    else:
        body += "No source is cited by URL in this paper.\n"
    (pool / "raw" / "measured_baseline_and_method_transfer.md").write_text(body, encoding="utf-8")
    if with_sidecar:
        (pool / SIDECAR_NAME).write_bytes((FIXTURE / SIDECAR_NAME).read_bytes())
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", "research: the paper and its sidecar")
    return wt, pool


def _network_denier(tmp_path: Path) -> Path | None:
    """The same LD_PRELOAD shim `test_citations_verify_offline.py` compiles,
    imported rather than retyped so the two tiers deny the network one way."""
    from tests.integration.test_citations_verify_offline import _network_denier as build
    return build(tmp_path)


# --- forward: sidecar → store → verify offline -----------------------------------

def test_a_run_that_WRITES_the_sidecar_fills_the_store_and_verify_resolves_it_OFFLINE(
        tmp_path: Path, journal_root: Path) -> None:
    """SUCCESS CRITERIA 1 AND 2 in one walk, in the reference case's shape."""
    wt, pool = _run_tree(tmp_path, with_sidecar=True)
    bag = open_bag(journal_root, "pr36-forward")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal_root)

    report = capture_cited_sources(pool_dir=pool, bag=bag, stage="research",
                                   capture_fn=_fixture_fetch,
                                   worktree=wt, base="origin/main")

    assert report.sidecar == pool / SIDECAR_NAME
    assert report.captured == len(ROWS) == 5 and not report.failed and not report.skipped
    assert report.malformed == [], report.malformed
    # The denominator is THIS RUN's paper, not the pool: the legacy paper's URL
    # is not counted, which is what keeps a mature pool from tripping the guard.
    assert report.papers == ["development/self-improvement/research/raw/"
                             "measured_baseline_and_method_transfer.md"]
    assert report.cited == len(URLS) == 4
    assert report.captured_urls == set(URLS)
    assert "coverage 4/4 cited sources captured" in report.as_note()

    assert record_capture_gap(report, emitter=emitter, pool_dir=pool) is False
    assert not bag.incomplete

    # Offline, in-process first: every stored citation resolves from the store.
    in_proc = verify_bag(bag.path)
    assert in_proc.ok and in_proc.counts()[VERIFIED] == 5, in_proc.counts()
    assert sum(in_proc.counts().values()) == 5, in_proc.counts()

    # Then with the network DENIED below the interpreter, through the entrypoint.
    library = _network_denier(tmp_path)
    if library is None:
        pytest.skip("no C compiler here — the denial shim cannot be built")
    env = dict(os.environ, LD_PRELOAD=str(library))
    control = subprocess.run(
        [sys.executable, "-c",
         "import urllib.request;"
         "urllib.request.urlopen('https://example.com', timeout=5).read(16)"],
        env=env, capture_output=True, timeout=120)
    assert control.returncode != 0, "the denial shim did not take effect"

    verified = subprocess.run([sys.executable, str(ENTRYPOINT), str(bag.path)],
                              env=env, capture_output=True, text=True, timeout=120)
    assert verified.returncode == EXIT_OK, (
        f"verify did not resolve #36's citations offline:\n{verified.stdout}\n{verified.stderr}")
    assert f"{VERIFIED}: 5" in verified.stdout, verified.stdout
    # `source_ref` on every stored row is the SHA-pinned raw URL the run verified
    # against — the reproducibility the paper claims, carried into the bag.
    stored = read_citations(bag.path)
    assert {c.source_ref for c in stored} == set(URLS)
    assert {c.quote for c in stored} == {r["quote"] for r in ROWS}


def test_the_fixture_is_SYNTHETIC_and_self_contained() -> None:
    """THE LICENCE CONTROL. The fixture once redistributed full third-party
    files without their notices; this holds the replacement to its claim.
    Every source is small, plain text, named by the manifest, sha256-pinned,
    and reachable only at an `.invalid` host — and every quoted span is in the
    bytes exactly once, which is what `verify` will re-check."""
    manifest = json.loads((FIXTURE / "sources.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    assert "license" not in json.dumps(manifest).lower(), (
        "a licence row is a third-party file's shape, and this fixture holds none")
    on_disk = {p.name for p in FIXTURE.iterdir()} - {SIDECAR_NAME, "sources.json"}
    assert on_disk == {e["file"] for e in SOURCES.values()}, (
        f"fixture files and manifest disagree: {on_disk ^ {e['file'] for e in SOURCES.values()}}")
    for url, entry in SOURCES.items():
        assert url.startswith("https://sources.invalid/"), url
        data = _bytes_for(url)
        assert len(data) < 2048, f"{entry['file']} is {len(data)} bytes — a real file's size"
        data.decode("utf-8")                         # plain text, not an archive
    for row in ROWS:
        assert _bytes_for(row["url"]).decode("utf-8").count(row["quote"]) == 1, row["claim_id"]
        assert row["sha"] == hashlib.sha1(_bytes_for(row["url"])).hexdigest(), row["claim_id"]


# --- reverse: cited paper, no sidecar → the gap ------------------------------------

def test_a_CITED_paper_with_NO_sidecar_marks_the_bag_INCOMPLETE(tmp_path: Path,
                                                                 journal_root: Path) -> None:
    """SUCCESS CRITERION 3 — the positive control. This is #36 exactly: the run
    verified every span and wrote no sidecar. Before this guard the only trace
    was a `NOT RUN` note; now the bag says it is missing something, typed."""
    wt, pool = _run_tree(tmp_path, with_sidecar=False)
    bag = open_bag(journal_root, "pr36-reverse")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal_root)

    report = capture_cited_sources(pool_dir=pool, bag=bag, stage="research",
                                   capture_fn=_fixture_fetch,
                                   worktree=wt, base="origin/main")
    assert report.sidecar is None and report.captured == 0
    assert report.cited == 4
    assert report.store_is_empty_for_a_cited_paper

    assert record_capture_gap(report, emitter=emitter, pool_dir=pool) is True
    assert bag.incomplete, "the flag downstream branches on was not set"
    gap_lines = [v for k, v in bag.info() if k == LABEL_GAP]
    assert gap_lines and all(GapClass.SOURCES_UNCAPTURED.value in g for g in gap_lines), (
        f"bag-info carries no sources_uncaptured gap: {bag.info()}")

    events = [decode_event(line) for line in
              (bag.payload_dir / EVENTS_FILE).read_text(encoding="utf-8").splitlines() if line]
    gaps = [e for e in events if e.kind is EventKind.GAP]
    assert len(gaps) == 1
    assert gaps[0].gap_class is GapClass.SOURCES_UNCAPTURED
    assert gaps[0].write_path == GAP_WRITE_PATH
    assert gaps[0].destination.store == "content_store"
    assert gaps[0].destination.address == str(pool)

    note = report.as_note()
    assert "CONTENT STORE EMPTY" in note and "INCOMPLETE" in note and "sources_uncaptured" in note
    assert "coverage 0/4" in note


def test_a_paper_that_cites_NOTHING_is_not_a_gap(tmp_path: Path, journal_root: Path) -> None:
    """The guard's other edge: no URLs, no sidecar, nothing lost. A retirement-only
    cycle or a synthesis rewrite must not mark its bag incomplete."""
    wt, pool = _run_tree(tmp_path, with_sidecar=False, cite=False)
    bag = open_bag(journal_root, "pr36-uncited")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal_root)
    report = capture_cited_sources(pool_dir=pool, bag=bag, stage="research",
                                   capture_fn=_fixture_fetch, worktree=wt, base="origin/main")
    assert report.cited == 0
    assert record_capture_gap(report, emitter=emitter, pool_dir=pool) is False
    assert not bag.incomplete
    assert "coverage n/a" in report.as_note()


# --- the invariant between them ------------------------------------------------------

def test_ONE_rotted_source_is_a_recorded_failure_NOT_a_gap_and_NOT_an_exception(
        tmp_path: Path, journal_root: Path) -> None:
    """SUCCESS CRITERION 4: the D2 fetch dies, the other four are stored and
    verify, the bag stays complete."""
    wt, pool = _run_tree(tmp_path, with_sidecar=True)
    bag = open_bag(journal_root, "pr36-one-dead")
    emitter = Emitter.for_run(bag, writer=None, journal_root=journal_root)
    dead = next(u for u in URLS if u.endswith("/triage_cron.txt"))   # D2's source

    def _one_dead(**kw):
        if kw["url"] == dead:
            raise ConnectionError("HTTP 404 — the glossary moved")
        return _fixture_fetch(**kw)

    report = capture_cited_sources(pool_dir=pool, bag=bag, stage="research",
                                   capture_fn=_one_dead, worktree=wt, base="origin/main")
    assert report.captured == 4 and report.failed == [(dead, "ConnectionError: HTTP 404 — the glossary moved")]
    assert report.captured_urls == set(URLS) - {dead}
    assert "coverage 3/4" in report.as_note() and dead in report.as_note()
    assert record_capture_gap(report, emitter=emitter, pool_dir=pool) is False
    assert not bag.incomplete
    counts = verify_bag(bag.path).counts()
    assert counts[VERIFIED] == 4 and sum(counts.values()) == 4, counts
