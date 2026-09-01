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
runs `git cat-file` against a local object database.
`tests/unit/test_verify_citations.py::test_the_verifier_reaches_no_fetcher`
asserts that intra-package import closure — with a discriminator beside it that
starts the same walk at `content_activities`, which legitimately does reach the
fetcher — and the phase's demonstration runs the whole thing with the process's
network denied at the C library boundary. (The named test is the real guard; the
file `test_verify_is_offline.py` this line used to cite has never existed, which
is a claim about a property nobody could go and check.)
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .bag import BAGIT_FILE, BagError
from .citations import (Citation, CitationError, is_git_ref, parse_git_ref,
                        read_citations, stage_evidence_hashes)
from .content_store import ContentStoreError, ObjectMissing, load_object

__all__ = ["VERIFIED", "MISSING", "TAMPERED", "SPAN_MISSING", "OUTCOMES",
           "EXIT_OK", "EXIT_MISSING", "EXIT_TAMPERED", "EXIT_SPAN_MISSING",
           "EXIT_STRUCTURAL", "EXIT_USAGE", "SEVERITY", "GIT_TIMEOUT_SECONDS",
           "GitResolveError", "CitationResult", "VerifyReport",
           "span_occurs_in", "git_blob", "verify_citation", "verify_bag",
           "render_report", "exit_code_for", "split_args", "main"]

VERIFIED = "verified"
MISSING = "missing"
TAMPERED = "tampered"
SPAN_MISSING = "span-missing"
OUTCOMES = (VERIFIED, MISSING, TAMPERED, SPAN_MISSING)

EXIT_OK = 0
# 2 is left to usage ALONE, matching `validate_bag.py`, so a wrong invocation and
# a real finding are never the same number. That sentence was false when it was
# written — `exit_code_for` returned this for a structural finding — and
# `EXIT_STRUCTURAL` below is what makes it true.
EXIT_USAGE = 2
EXIT_MISSING = 3
EXIT_TAMPERED = 4
EXIT_SPAN_MISSING = 5
# ⚠ ITS OWN CODE, BECAUSE IT USED TO BE 2 AND THAT MADE THE COMMENT ABOVE FALSE.
# A bag whose `citations.jsonl` cannot be parsed is a REAL FINDING — the record
# of what was claimed is unreadable — and it exited with the number reserved for
# "you invoked me wrong". Automation reading 2 as a usage error discards it, and
# the report says FAIL while the code says try-again-with-better-arguments.
# Ranked ABOVE `tampered`: a tampered object invalidates one verdict, an
# unreadable record means the verdicts were never enumerable at all.
EXIT_STRUCTURAL = 6

# The name of the structural class inside `SEVERITY`. Not an outcome a citation
# can carry — no citation was reached — so it is not in `OUTCOMES` and never
# appears in `counts()`.
STRUCTURAL = "structural"

# WHICH CODE A MIXED RUN EXITS WITH, ordered by how much of the report the
# outcome invalidates rather than by how bad it sounds. A tampered object means
# the store itself is untrustworthy, so every other verdict in the same run is
# provisional; a missing object means one check could not be made; a
# span-missing is a complete, trustworthy check with a negative answer; and a
# structural finding outranks all of them because it means the citations were
# never enumerated at all. Stated as data because a caller reading the exit code
# needs the same ordering the report used.
SEVERITY = {STRUCTURAL: 4, TAMPERED: 3, MISSING: 2, SPAN_MISSING: 1,
            VERIFIED: 0}

_EXIT_FOR = {VERIFIED: EXIT_OK, MISSING: EXIT_MISSING,
             TAMPERED: EXIT_TAMPERED, SPAN_MISSING: EXIT_SPAN_MISSING,
             STRUCTURAL: EXIT_STRUCTURAL}


class GitResolveError(BagError):
    """A `git:` citation could not be produced from a git object database.

    ⚠ NOT A `ContentStoreError`, WHICH IS WHAT IT WAS. `verify_citation` now
    branches on exception TYPE to choose an outcome, and `ContentStoreError`
    means "the content store failed" — so git-not-installed and a git timeout
    were arriving in the branch that classifies store failures. The two
    resolvers fail for unrelated reasons and a caller must be able to tell them
    apart without reading prose, which is the defect this whole file just paid
    for once.
    """


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
        """The class this report exits on. `verified` when there is nothing worse.

        ⚠ STRUCTURAL IS RANKED HERE AND NOT ONLY IN `exit_code_for`. This
        property returned `verified` for a report whose `ok` was False, because
        it ranked `results` and ignored `structural` — so the obviously-named
        property said "nothing wrong" for the one report class that means the
        citations were never enumerated. Two derivations of one severity is the
        shape that produced the exit-code defect one field up.
        """
        if self.structural:
            return STRUCTURAL
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
        # `timeout=` directly rather than `assistant_activities.run_bounded`:
        # `modules/journal/` does not import upward into the workflow modules,
        # which is the dependency rule this package's `__init__` states. The
        # bound is the property the fleet-wide guard checks, and it is here.
        probe = subprocess.run(["git", "cat-file", "-p", target],
                               cwd=str(repo_root), capture_output=True,
                               timeout=GIT_TIMEOUT_SECONDS)
    except FileNotFoundError as exc:
        raise GitResolveError(
            f"cannot resolve {target}: git is not installed or not on PATH in "
            f"this environment.") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitResolveError(
            f"cannot resolve {target}: `git cat-file` did not answer within "
            f"{GIT_TIMEOUT_SECONDS:.0f}s in {repo_root}.") from exc
    except OSError as exc:
        raise GitResolveError(
            f"cannot resolve {target}: `git cat-file` could not be launched in "
            f"{repo_root} ({exc.strerror}).") from exc
    if probe.returncode != 0:
        raise GitResolveError(
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
        except GitResolveError as exc:
            return result(MISSING, str(exc))
    else:
        # ⚠ THE OUTCOME COMES FROM THE EXCEPTION TYPE, NOT FROM ITS MESSAGE.
        # This asked `"TAMPERED" in str(exc)` — of prose that embeds the store
        # directory, which embeds the run id, which `RUN_ID_PERMITTED` allows to
        # contain those letters. A run named `TAMPERED-2026` reported every
        # ABSENT object as a corrupted one. The outcome class is a fact about
        # what failed and is carried by the failure.
        #
        # Everything that is not `ObjectMissing` lands in `tampered`, which is
        # the class that means "the store is not currently to be trusted" — the
        # true statement for a corrupt object AND for one that is present and
        # unreadable. `missing` is reserved for "nothing was stored", because
        # its remedy is "re-capture the source" and that is destructive advice
        # for bytes that are merely behind a failing disk.
        try:
            data = load_object(bag_path, citation.page_content_hash)
        except ObjectMissing as exc:
            return result(MISSING, str(exc))
        except ContentStoreError as exc:
            return result(TAMPERED, str(exc))

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
    except (CitationError, OSError, ValueError) as exc:
        # A citation FILE that cannot be parsed is structural: it is not one
        # claim failing, it is the record of what was claimed being unreadable,
        # and reporting it as a per-citation outcome would understate it.
        #
        # ⚠ AND THAT INCLUDES A FILESYSTEM OR DECODE ERROR — the half
        # `validate_bag` already paid for and documented, and this function did
        # not carry across. Only `CitationError` was caught, so a
        # `citations.jsonl` holding non-UTF-8 bytes raised `UnicodeDecodeError`
        # (a `ValueError`) straight out of the sweep, and a permission failure
        # or a file that vanished mid-`rglob` raised `OSError`. One such bag
        # killed a whole-journal run and reported nothing about the other 47 —
        # verbatim the regression `validate.py` records against itself.
        return VerifyReport(path=bag_path, structural=(f"{type(exc).__name__}: {exc}",))

    results = tuple(verify_citation(bag_path, c, repo_root=repo_root)
                    for c in citations)
    return VerifyReport(path=bag_path, results=results,
                        evidence_hashes=stage_evidence_hashes(citations))


def exit_code_for(reports: list[VerifyReport]) -> int:
    """The code the run exits with: the most severe class anywhere in it.

    ONE RANKING, APPLIED ONCE. This short-circuited on `structural` and returned
    `EXIT_USAGE` before the ranking ran, so a sweep containing one unparseable
    record and one tampered object exited 2 — the number the entrypoint
    documents as "usage" — and the integrity finding was reported to a caller
    that had been told it had merely typed the command wrong.
    """
    worst = max((r.worst for r in reports), key=lambda o: SEVERITY[o],
                default=VERIFIED)
    return _EXIT_FOR[worst]


def split_args(args: list[str]) -> tuple[Path | None, list[str]]:
    """`(repo_root, targets)` out of an argument list. One parse, two callers.

    EXTRACTED BECAUSE THE SECOND COPY WAS ALREADY WRONG. `verify_citations.py`
    needs to know whether any TARGET was given, so it can fall back to the
    configured journal root — and it asked that question with a filter over the
    raw arguments, which counted `--repo`'s own VALUE as a target. The result
    was that `verify_citations.py --repo <path>`, with no bag named, printed a
    usage message instead of verifying the configured root. Two hand-written
    parses of one grammar is the shape this package keeps finding in itself.

    Raises `ValueError` when `--repo` is given without a path, so the caller
    owns the exit code and the message reaches whichever stream it writes to.
    """
    repo_root: Path | None = None
    targets: list[str] = []
    index = 0
    while index < len(args):
        if args[index] == "--repo":
            if index + 1 >= len(args):
                raise ValueError("--repo needs a path")
            repo_root = Path(args[index + 1]).expanduser()
            index += 2
            continue
        targets.append(args[index])
        index += 1
    return repo_root, targets


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

    EXIT CODES: 0 verified · 2 usage · 3 missing · 4 tampered · 5 span-missing ·
    6 structural (a bag exists and its citation record cannot be read).
    """
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        repo_root, targets = split_args(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE

    if not targets:
        print("usage: verify_citations.py [--repo <path>] <bag-dir-or-journal-root> [...]",
              file=sys.stderr)
        return EXIT_USAGE

    reports: list[VerifyReport] = []
    for raw in targets:
        target = Path(raw).expanduser()
        # A PATH THE OPERATOR NAMED THAT IS NOT THERE IS USAGE, and it is
        # separated here so that `EXIT_STRUCTURAL` means one thing only: a bag
        # that exists and whose record cannot be read. Collapsing the two is
        # what put a real finding behind the usage code.
        if not target.is_dir():
            print(f"not a directory: {target}", file=sys.stderr)
            return EXIT_USAGE
        if (target / BAGIT_FILE).is_file():
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
