"""Re-check every citation in a bag from the stored bytes alone. No network.

REQUIREMENTS 2, 3, 4 AND 7(d). This module is `content_store.load_object` run
over everything — not a second implementation of resolving, which is what r7(d)
rules and what keeps the bulk check and the single read from ever disagreeing.

FOUR OUTCOMES, FOUR EXIT CODES, AND COLLAPSING THEM IS THE FAILURE THIS EXISTS
TO PREVENT. Requirement 3 names three and requirement 4 splits a fourth out of
them, and each has a different remedy, which is the test for whether a
distinction is worth an exit code:

  `verified`      the stored bytes hash to the digest the citation names, and the
                  quoted span still occurs in them. Nothing to do.
  `missing`       nothing is stored under that digest, or git cannot produce that
                  object. The check could not be MADE — re-capture the source.
  `tampered`      bytes are stored under that digest and they hash to something
                  else. The STORE failed; the citation may be perfectly good.
                  Nothing else in the journal should be trusted until this is
                  understood.
  `span-missing`  the bytes are intact and the quote is not in them. The STORE is
                  fine and the CITATION was wrong when it was made. This is the
                  one outcome that is an epistemic finding rather than an
                  integrity one, which is exactly why requirement 4 refuses to
                  let it share an exit code with a changed hash.

WHAT A CLEAN RUN PROVES, AND THE THREE THINGS IT DOES NOT. It proves the bytes
this claim was made against are the bytes still on disk and the quoted span is
still in them. It does NOT prove the claim is true — a correct quotation from a
wrong source verifies clean. It does NOT prove the live source still says this;
the store is a snapshot, and an upstream page that changed after capture is a
currency question this phase does not own. It does NOT prove the record is
authentic: a digest computed by the party that can write the store is
regenerable by that party, so this detects accident and transport corruption and
not a party with write access.

AND IT REPORTS THE CAPTURE PROVENANCE PER CITATION rather than asserting a
guarantee. A `harvest` row's hash proves its bytes matched at harvest, not that
the claim was made against them; a `read-time` row's does. The verifier says
which, per row, because a single global sentence about the guarantee is exactly
what gets over-read.

OFFLINE IS A PROPERTY OF THE CODE, NOT A PROMISE IN A DOCSTRING. Nothing in this
module's import graph opens a socket: it reads files and, for a `git:` citation,
runs `git cat-file` against a local object database. `test_verify_is_offline.py`
asserts the import graph, and the phase's demonstration runs the whole thing with
the process's network denied at the C library boundary.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .bag import BAGIT_FILE
from .citations import (Citation, CitationError, is_git_ref, parse_git_ref,
                        read_citations, stage_evidence_hashes)
from .content_store import ContentStoreError, load_object

__all__ = ["VERIFIED", "MISSING", "TAMPERED", "SPAN_MISSING", "OUTCOMES",
           "EXIT_OK", "EXIT_MISSING", "EXIT_TAMPERED", "EXIT_SPAN_MISSING",
           "EXIT_USAGE", "SEVERITY", "GIT_TIMEOUT_SECONDS", "CitationResult",
           "VerifyReport", "span_occurs_in", "git_blob", "verify_citation",
           "verify_bag", "render_report", "exit_code_for", "main"]

VERIFIED = "verified"
MISSING = "missing"
TAMPERED = "tampered"
SPAN_MISSING = "span-missing"
OUTCOMES = (VERIFIED, MISSING, TAMPERED, SPAN_MISSING)

EXIT_OK = 0
# 2 is left to usage, matching `validate_bag.py`, so a wrong invocation and a
# real finding are never the same number.
EXIT_USAGE = 2
EXIT_MISSING = 3
EXIT_TAMPERED = 4
EXIT_SPAN_MISSING = 5

# WHICH CODE A MIXED RUN EXITS WITH, ordered by how much of the report the
# outcome invalidates rather than by how bad it sounds. A tampered object means
# the store itself is untrustworthy, so every other verdict in the same run is
# provisional; a missing object means one check could not be made; a
# span-missing is a complete, trustworthy check with a negative answer. Stated
# as data because a caller reading the exit code needs the same ordering the
# report used.
SEVERITY = {TAMPERED: 3, MISSING: 2, SPAN_MISSING: 1, VERIFIED: 0}

_EXIT_FOR = {VERIFIED: EXIT_OK, MISSING: EXIT_MISSING,
             TAMPERED: EXIT_TAMPERED, SPAN_MISSING: EXIT_SPAN_MISSING}

# `git cat-file` against a local object database answers in milliseconds. The
# bound exists because an unbounded subprocess in a checker is how a verify run
# hangs a machine, and this fleet bounds every subprocess it launches.
GIT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class CitationResult:
    """One citation's verdict, and enough context to act on it."""

    claim_id: str
    stage: str
    outcome: str
    capture: str
    source_ref: str
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.outcome == VERIFIED


@dataclass(frozen=True)
class VerifyReport:
    """Every citation in one bag, plus requirement 5's per-stage evidence hashes."""

    path: Path
    results: tuple[CitationResult, ...] = ()
    evidence_hashes: dict[str, str] = field(default_factory=dict)
    structural: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """DERIVED, NEVER STORED — same rule `BagReport.ok` keeps one module over.

        A `PASS` printed above a tampered object is the single worst thing a
        checker can emit, and a stored field is what makes one constructible.
        """
        return not self.structural and all(r.ok for r in self.results)

    def counts(self) -> dict[str, int]:
        return {outcome: sum(1 for r in self.results if r.outcome == outcome)
                for outcome in OUTCOMES}

    @property
    def worst(self) -> str:
        """The outcome this report exits on. `verified` when there is nothing worse."""
        return max((r.outcome for r in self.results),
                   key=lambda o: SEVERITY[o], default=VERIFIED)


def span_occurs_in(quote: str, data: bytes) -> bool:
    """Whether the quoted span still occurs in these bytes.

    DECODED PERMISSIVELY AND COMPARED ON WHITESPACE-NORMALISED TEXT, and both
    halves are deliberate. `errors="replace"` means a page that is not valid
    UTF-8 produces a span answer rather than an exception — a decode failure
    would be reported as an integrity problem when the integrity is fine.
    Normalising runs of whitespace is what makes a quote survive the source
    being re-wrapped, which is the overwhelmingly common shape of a quote a
    human or a model copied out of rendered text.

    WHAT IT DOES NOT DO: it does not strip markup, so a quote taken from
    rendered HTML may not occur in the HTML bytes. That is a real limit, it
    produces a `span-missing` rather than a wrong `verified`, and closing it
    means storing a rendered form beside the raw one — a bigger mechanism than
    this phase is scoped to, and one that would put a DERIVED artifact in a
    store whose whole guarantee is that it holds what was received.
    """
    text = data.decode("utf-8", errors="replace")
    return " ".join(quote.split()) in " ".join(text.split())


def git_blob(repo_root: Path, sha: str, path: str | None) -> bytes:
    """The bytes of a code citation, out of the local git object database.

    REQUIREMENT 6 — CODE IS RESOLVED FROM GIT AND NEVER COPIED INTO THE STORE.
    Git is already content-addressed, so a second copy under a second checksum
    would be two names for one guarantee and the copy is the one that can drift.

    NO TAMPERED OUTCOME IS POSSIBLE HERE and that is a property of git rather
    than an omission: git verifies an object against its own name on read, so a
    corrupt object fails to be produced at all and arrives here as `missing`.
    """
    target = f"{sha}:{path}" if path else sha
    try:
        probe = subprocess.run(["git", "cat-file", "-p", target],
                               cwd=str(repo_root), capture_output=True,
                               timeout=GIT_TIMEOUT_SECONDS)
    except FileNotFoundError as exc:
        raise ContentStoreError(
            f"cannot resolve {target}: git is not installed or not on PATH in "
            f"this environment.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ContentStoreError(
            f"cannot resolve {target}: `git cat-file` did not answer within "
            f"{GIT_TIMEOUT_SECONDS:.0f}s in {repo_root}.") from exc
    if probe.returncode != 0:
        raise ContentStoreError(
            f"{target} is MISSING from the git object database at {repo_root}: "
            f"{probe.stderr.decode('utf-8', errors='replace').strip()[:200]}")
    return probe.stdout


def verify_citation(bag_path: Path, citation: Citation, *,
                    repo_root: Path | None = None) -> CitationResult:
    """One citation, resolved from the store alone and re-checked. Never fetches.

    THE ORDER OF THE TWO CHECKS IS THE DIAGNOSIS. Resolve first — which
    re-hashes, and separates `missing` from `tampered` — and only then look for
    the span. A span check run against bytes that failed their own hash would
    report a wrong quote when the real finding is a corrupt store.
    """
    def result(outcome: str, detail: str = "") -> CitationResult:
        return CitationResult(claim_id=citation.claim_id, stage=citation.stage,
                              outcome=outcome, capture=citation.capture,
                              source_ref=citation.source_ref, detail=detail)

    if is_git_ref(citation.source_ref):
        if repo_root is None:
            return result(MISSING,
                          "a git citation needs a repository to resolve against; "
                          "none was given to this run")
        sha, path = parse_git_ref(citation.source_ref)
        try:
            data = git_blob(repo_root, sha, path)
        except ContentStoreError as exc:
            return result(MISSING, str(exc))
    else:
        try:
            data = load_object(bag_path, citation.page_content_hash)
        except ContentStoreError as exc:
            message = str(exc)
            return result(TAMPERED if "TAMPERED" in message else MISSING, message)

    if not span_occurs_in(citation.quote, data):
        return result(
            SPAN_MISSING,
            f"the stored bytes are intact and the quoted span does not occur in "
            f"them. The store is fine; this citation was wrong when it was made. "
            f"Quote: {citation.quote[:120]!r}")
    return result(VERIFIED)


def verify_bag(bag_path: Path, *, repo_root: Path | None = None) -> VerifyReport:
    """Every citation in one bag, plus the per-stage evidence hashes.

    A BAG WITH NO CITATIONS IS NOT A FAILURE, for the reason an open bag is not
    a failed bag one module over: most runs cite nothing, and a checker that
    called them broken would make its own output unreadable. It is reported as
    zero citations, which is a fact rather than a verdict.
    """
    if not bag_path.is_dir():
        return VerifyReport(path=bag_path,
                            structural=(f"{bag_path} is not a directory",))
    try:
        citations = read_citations(bag_path)
    except CitationError as exc:
        # A citation FILE that cannot be parsed is structural: it is not one
        # claim failing, it is the record of what was claimed being unreadable,
        # and reporting it as a per-citation outcome would understate it.
        return VerifyReport(path=bag_path, structural=(str(exc),))

    results = tuple(verify_citation(bag_path, c, repo_root=repo_root)
                    for c in citations)
    return VerifyReport(path=bag_path, results=results,
                        evidence_hashes=stage_evidence_hashes(citations))


def exit_code_for(reports: list[VerifyReport]) -> int:
    """The code the run exits with: the most severe outcome anywhere in it."""
    if any(r.structural for r in reports):
        return EXIT_USAGE
    worst = max((r.worst for r in reports), key=lambda o: SEVERITY[o],
                default=VERIFIED)
    return _EXIT_FOR[worst]


def render_report(report: VerifyReport) -> str:
    """Human-readable, and every outcome class is printed even at zero.

    The always is the contract, same as `validate.render_report`: a reader who
    sees `tampered: 0` learns something, and a reader of a report that simply
    omits the line cannot tell zero from not-looked-for.
    """
    counts = report.counts()
    lines = [
        f"bag        : {report.path}",
        f"result     : {'PASS' if report.ok else 'FAIL'}",
        f"citations  : {len(report.results)}",
        "  " + "  ".join(f"{outcome}: {counts[outcome]}" for outcome in OUTCOMES),
    ]
    for item in report.structural:
        lines.append(f"  structural: {item}")
    for result in report.results:
        if result.ok:
            continue
        lines.append(f"  {result.outcome}: [{result.stage}] {result.claim_id} "
                     f"({result.capture}) {result.source_ref}")
        if result.detail:
            lines.append(f"      {result.detail}")
    for stage, digest in report.evidence_hashes.items():
        lines.append(f"  evidence_set_hash[{stage}]: {digest}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Verify one bag or every bag directly under one journal root.

    `--repo` supplies the repository `git:` citations resolve against. Without
    it those citations report `missing` and say why, which is honest: this run
    could not make the check, rather than the check having failed.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    repo_root: Path | None = None
    targets: list[str] = []
    index = 0
    while index < len(args):
        if args[index] == "--repo":
            if index + 1 >= len(args):
                print("--repo needs a path", file=sys.stderr)
                return EXIT_USAGE
            repo_root = Path(args[index + 1]).expanduser()
            index += 2
            continue
        targets.append(args[index])
        index += 1

    if not targets:
        print("usage: verify_citations.py [--repo <path>] <bag-dir-or-journal-root> [...]",
              file=sys.stderr)
        return EXIT_USAGE

    reports: list[VerifyReport] = []
    for raw in targets:
        target = Path(raw).expanduser()
        if (target / BAGIT_FILE).is_file() or not target.is_dir():
            reports.append(verify_bag(target, repo_root=repo_root))
            continue
        children = sorted(p for p in target.iterdir() if p.is_dir())
        if not children:
            print(f"no bags under {target}", file=sys.stderr)
            return EXIT_USAGE
        reports.extend(verify_bag(child, repo_root=repo_root) for child in children)

    for report in reports:
        print(render_report(report))
        print()

    total = sum(len(r.results) for r in reports)
    failed = sum(1 for r in reports for result in r.results if not result.ok)
    print(f"{total - failed}/{total} citations verified across {len(reports)} bag(s)")
    return exit_code_for(reports)
