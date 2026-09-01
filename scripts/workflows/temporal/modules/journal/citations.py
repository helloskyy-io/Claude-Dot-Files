"""What a run CLAIMED, and which bytes it claimed it against.

PHASE 2 REQUIREMENTS 1, 5 AND 6. `content_store.py` holds the bytes; this module
holds the record that points at them. They are separate because they fail
separately: a store defect is corruption of something the fleet wrote, and a
citation defect is a claim that was wrong when it was made.

THE RECORD IS `claim_id`, `quote`, `source_ref` AND `page_content_hash`, which is
the phase's first checklist item, plus three fields the build could not do
without and which a v1 record cannot gain later:

  * `stage` — requirement 5 computes an evidence-set hash PER STAGE, so the stage
    has to be on the record. Deriving it from the writer directory afterwards
    would work today and would silently stop working the moment one writer runs
    two stages.
  * `capture` — WHICH GUARANTEE THIS ROW CARRIES, and it is r7(c)'s ruling
    expressed as data. See § below.
  * `recorded_at` — when the row was written. A record whose bytes are dated only
    by a filesystem timestamp loses its date the first time it is copied.

r7(c) IS RULED: POST-EXIT HARVEST, AND THE GUARANTEE IS PER-CITATION RATHER THAN
GLOBAL. The phase doc names two arms and calls both legitimate. The routed-fetcher
arm changes how the research workflow reads its sources, and the doc says
plainly that this is "not a decision this phase can take alone" — so this phase
takes the arm that stays inside it, which is also the shape the model-issued
harvest already uses for writes.

  **What that arm costs is a weaker guarantee, and the doc's own remedy was to
  amend requirement 2's sentence.** This build does something narrower and more
  useful instead: rather than downgrading one global claim, it records the
  provenance ON EACH ROW.

    `capture: "read-time"`  the bytes were captured as the source was read, so
                            the hash proves the claim was made against them.
    `capture: "harvest"`    the bytes were fetched after the run ended, so the
                            hash proves they matched AT HARVEST and nothing more.

  Two things follow. A `verify` result can never over-claim, because it reports
  the provenance it read rather than a guarantee the mechanism asserts. And the
  routed-fetcher arm stays reachable at no cost: the day a fleet-side read path
  exists it calls the same capture activity with `capture="read-time"`, and no
  stored record has to be rewritten.

REQUIREMENT 6 — A CODE DIFF IS A COMMIT SHA AND IS NEVER COPIED IN. `source_ref`
carries `git:<sha>[:<path>]` for code, and such a row has NO `page_content_hash`:
git is already content-addressed, so storing a second copy under a second
checksum would be two names for one guarantee, and the copy is the one that can
drift. `store_a_code_diff_instead` is the refusal that makes this mechanical
rather than a convention.

WHY JSON LINES AND NOT ONE DOCUMENT. A run appends citations as it goes and may
die mid-write; a partially-written array is unparseable and loses every row
before the break, while a partially-written final line loses one. Each writer
appends to its OWN file for the reason `Bag.writer_dir` exists — concurrent
writers in this fleet are real, and the cheapest correct answer to two writers is
two files.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .bag import PAYLOAD_DIR, BagError, contained_relpath, utc_now

__all__ = ["CITATIONS_FILE", "CITATION_SCHEMA_VERSION", "CAPTURE_READ_TIME",
           "CAPTURE_HARVEST", "CAPTURE_KINDS", "GIT_REF_RE", "CitationError",
           "Citation", "is_git_ref", "parse_git_ref", "record_citation",
           "read_citations", "citations_by_stage", "evidence_set_hash",
           "stage_evidence_hashes", "converged_stages", "new_citation"]

CITATIONS_FILE = "citations.jsonl"

# Its own version, separate from the bag's `Event-Schema-Version`, because a
# citation row travels: Phase 7 ships it to object storage where the bag's
# summary version does not follow it.
CITATION_SCHEMA_VERSION = 1

CAPTURE_READ_TIME = "read-time"
CAPTURE_HARVEST = "harvest"
CAPTURE_KINDS = (CAPTURE_READ_TIME, CAPTURE_HARVEST)

# `git:<40-hex-sha>` with an optional `:<path>`. Abbreviated SHAs are refused:
# an abbreviation is a prefix search whose answer can change as a repository
# grows objects, and a citation is meant to name one object forever.
GIT_REF_RE = re.compile(r"^git:([0-9a-f]{40})(?::(.+))?$")

_CLAIM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_HEX_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class CitationError(BagError):
    """A citation record could not be built, written or read as asked."""


def is_git_ref(source_ref: str) -> bool:
    return bool(GIT_REF_RE.match(source_ref or ""))


def parse_git_ref(source_ref: str) -> tuple[str, str | None]:
    """`(sha, path)` out of a `git:` ref, or a refusal.

    The path is returned unvalidated on purpose — it is handed to `git`, which
    resolves it inside the object database rather than on the filesystem, so it
    is not a path this process composes onto anything. `content_store` is where
    path composition happens and it accepts a digest and nothing else.
    """
    match = GIT_REF_RE.match(source_ref or "")
    if not match:
        raise CitationError(
            f"not a git source ref: {source_ref!r}. Expected "
            f"`git:<40-hex-sha>` with an optional `:<path>`; an abbreviated sha "
            f"is refused because a prefix can stop being unique as a repository "
            f"grows, and a citation must name one object permanently.")
    return match.group(1), match.group(2)


@dataclass(frozen=True)
class Citation:
    """One claim, the words it quoted, and the evidence it quoted them from.

    Frozen because a written record is not edited — the same rule the bag keeps
    one directory up, applied to the row rather than to the folder.
    """

    claim_id: str
    stage: str
    quote: str
    source_ref: str
    capture: str
    page_content_hash: str | None = None
    media_type: str | None = None
    recorded_at: str = ""
    schema_version: int = CITATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Every field is checked HERE, so no other module has to trust a caller.

        The record is the durable artifact: a malformed row written today is a
        row every later reader has to cope with, and there is no pass that
        rewrites it. Validating at construction means the refusal lands on the
        run that made the mistake rather than on whoever reads the journal next.
        """
        if not _CLAIM_ID_RE.match(self.claim_id or ""):
            raise CitationError(
                f"claim_id {self.claim_id!r} is not a usable identifier. "
                f"Expected up to 128 characters of letters, digits, dot, dash "
                f"or underscore, starting with a letter or digit — it is used "
                f"to name one claim across a whole journal.")
        if not (self.stage or "").strip():
            raise CitationError(
                "stage is empty. Requirement 5 computes an evidence-set hash "
                "per stage, so a row with no stage cannot be counted into one.")
        if not (self.quote or "").strip():
            raise CitationError(
                f"claim {self.claim_id}: quote is empty. A citation with no "
                f"quoted span has nothing for `verify` to re-check, which is "
                f"the whole reason the bytes were stored.")
        if self.capture not in CAPTURE_KINDS:
            raise CitationError(
                f"claim {self.claim_id}: capture {self.capture!r} is not one of "
                f"{', '.join(CAPTURE_KINDS)}. It records WHICH guarantee this "
                f"row carries — whether the hash proves the claim was made "
                f"against these bytes, or only that they matched at harvest — "
                f"so it has no default.")

        if is_git_ref(self.source_ref):
            parse_git_ref(self.source_ref)
            if self.page_content_hash is not None:
                raise CitationError(
                    f"claim {self.claim_id}: a git source ref carries no "
                    f"page_content_hash. Requirement 6 resolves code from git "
                    f"rather than copying it into the store, and a second "
                    f"checksum over a copy is a second thing that can drift.")
            return

        if not (self.source_ref or "").startswith("https://"):
            raise CitationError(
                f"claim {self.claim_id}: source_ref {self.source_ref!r} is "
                f"neither an https URL nor a `git:<sha>` ref. Those are the two "
                f"kinds of evidence this record describes, and a third would "
                f"have no defined way to be re-checked offline.")
        if not _HEX_DIGEST_RE.match(self.page_content_hash or ""):
            raise CitationError(
                f"claim {self.claim_id}: page_content_hash "
                f"{self.page_content_hash!r} is not a sha256 digest. A web "
                f"citation with no digest names no bytes, so it would verify "
                f"clean by having nothing to check.")

    @property
    def evidence_id(self) -> str:
        """What this row counts AS, in an evidence set. Never the claim, never the quote.

        Two claims quoting different spans of one page saw ONE piece of evidence,
        so the identity is the source's bytes: the digest for a stored page, and
        the git ref for code, which git has already made content-addressed.
        """
        return self.source_ref if self.page_content_hash is None else self.page_content_hash

    def to_json(self) -> str:
        """One JSON Lines row: sorted keys, no newline, nulls dropped.

        Keys are sorted so two rows with the same content are the same bytes —
        a record that re-serialised differently on each write would make a diff
        over the journal unreadable. Nulls are dropped rather than written
        because an absent `page_content_hash` on a git row is a property of the
        kind of citation, not a value that happens to be empty.
        """
        payload = {k: v for k, v in asdict(self).items() if v is not None}
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> "Citation":
        """One row back into a record, re-validated on the way in.

        RE-VALIDATED, because `citations.jsonl` is a file on disk that this
        module did not necessarily write — the same reasoning that made
        `validate._parse_manifest` contain its paths. A reader that trusted the
        row would let a hand-edited file name whatever it liked.
        """
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CitationError(f"citation row is not JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise CitationError(
                f"citation row is a {type(data).__name__}, not an object")
        known = {f for f in cls.__dataclass_fields__}
        unknown = sorted(set(data) - known)
        if unknown:
            raise CitationError(
                f"citation row carries unknown field(s) {unknown}. A field this "
                f"reader does not know is either a newer schema than it can "
                f"read or a hand edit, and guessing between those is how a "
                f"record silently loses meaning.")
        return cls(**data)


def record_citation(directory: Path, citation: Citation) -> Path:
    """Append one citation row to `<directory>/citations.jsonl`. Returns the file.

    `directory` IS A WRITER DIRECTORY, allocated by `Bag.writer_dir`, and that is
    what makes the append safe without a lock: no two writers share this file.
    A single `write` of a line under `O_APPEND` is what the fleet relies on, and
    it is correct precisely because the contention it would otherwise face has
    been removed one layer up rather than handled here.
    """
    if not directory.is_dir():
        raise CitationError(
            f"cannot record a citation: {directory} is not a directory. "
            f"Citations are written into a writer directory allocated by "
            f"`Bag.writer_dir`, which is what makes concurrent writers safe.")
    target = directory / CITATIONS_FILE
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(citation.to_json() + "\n")
    return target


def read_citations(bag_path: Path) -> list[Citation]:
    """Every citation in one bag, from every writer, in a stable order.

    ⚠ THE DISCOVERED PATHS ARE CONTAINED BEFORE THEY ARE READ, for the reason
    `validate._parse_manifest` contains its manifest entries: a symlink under
    `data/` pointing outside the bag would otherwise let a file that never
    travelled with the bag supply its citations. A symlinked citations file is
    skipped rather than followed, and the bag validator reports the symlink
    itself as a structural finding.

    Rows are returned in `(stage, claim_id, source_ref)` order rather than in
    file order, so a set of citations has one spelling regardless of which
    writer wrote which part of it — which is what lets the evidence-set hash be
    a function of the evidence rather than of the scheduling.
    """
    payload = bag_path / PAYLOAD_DIR
    if not payload.is_dir():
        return []

    found: list[Citation] = []
    for path in sorted(payload.rglob(CITATIONS_FILE)):
        if path.is_symlink() or not path.is_file():
            continue
        relpath = path.relative_to(bag_path).as_posix()
        try:
            contained_relpath(relpath)
        except BagError as exc:
            raise CitationError(
                f"{path} is not contained by {bag_path}: {exc}") from exc
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                found.append(Citation.from_json(raw))
            except CitationError as exc:
                raise CitationError(f"{path}:{lineno}: {exc}") from exc
    return sorted(found, key=lambda c: (c.stage, c.claim_id, c.source_ref))


def citations_by_stage(citations: list[Citation]) -> dict[str, list[Citation]]:
    """Group rows by the stage that recorded them, stages in sorted order."""
    grouped: dict[str, list[Citation]] = {}
    for citation in citations:
        grouped.setdefault(citation.stage, []).append(citation)
    return {stage: grouped[stage] for stage in sorted(grouped)}


def evidence_set_hash(citations: list[Citation]) -> str:
    """One hash over the SET of evidence a group of citations rests on.

    REQUIREMENT 5, AND WHAT IT IS FOR: two stages with equal hashes saw exactly
    the same evidence, which is a stop condition computed from bytes rather than
    asserted by a model. This fleet has already replaced one model-asserted
    convergence flag with a computed signal for that reason.

    A SET, DEDUPLICATED AND SORTED. Ten claims quoting one page are one piece of
    evidence, so counting them ten times would make the hash a function of how
    much a stage wrote rather than of what it read. An empty set hashes to the
    hash of the empty string, which is a real value and not a sentinel — and
    `stage_evidence_hashes` is where "no evidence" is kept distinguishable from
    "the same evidence", because two empty stages genuinely did see the same
    nothing.
    """
    identities = sorted({c.evidence_id for c in citations})
    return hashlib.sha256("\n".join(identities).encode("utf-8")).hexdigest()


def stage_evidence_hashes(citations: list[Citation]) -> dict[str, str]:
    """`{stage: evidence_set_hash}` for every stage present. Requirement 5's output."""
    return {stage: evidence_set_hash(rows)
            for stage, rows in citations_by_stage(citations).items()}


def converged_stages(citations: list[Citation]) -> list[tuple[str, str]]:
    """`(stage, prior_stage)` for every stage whose evidence equals its predecessor's.

    REQUIREMENT 5 STOPS HERE, AND SO DOES THIS FUNCTION. It is COMPUTED AND
    EXPOSED; nothing in this fleet routes on it and nothing should until somebody
    produces firing-rate evidence for it. The precedent is this fleet's own
    convergence signal, which was built, shadowed beside the incumbent and gated
    nothing — because two positive observations are not a rate, and a stopping
    rule that fires early ends productive work silently with no failing test.

    "Predecessor" is the previous stage in sorted order, which is a property of
    the NAMES rather than of execution. That is honest about what the record
    holds: nothing in a v1 citation row orders the stages, so an ordering
    inferred from anything else here would be a guess wearing a computation's
    clothes. A caller that knows its own stage order passes its own list.
    """
    hashes = stage_evidence_hashes(citations)
    names = list(hashes)
    return [(names[i], names[i - 1]) for i in range(1, len(names))
            if hashes[names[i]] == hashes[names[i - 1]]]


def new_citation(*, claim_id: str, stage: str, quote: str, source_ref: str,
                 capture: str, page_content_hash: str | None = None,
                 media_type: str | None = None) -> Citation:
    """A citation stamped with the current time. The one constructor callers use.

    `recorded_at` is defaulted here rather than in the dataclass because a
    frozen record read back off disk must keep the timestamp it was written
    with, and a field defaulting to "now" inside `__init__` would silently
    restamp every row `from_json` rebuilt.
    """
    return Citation(claim_id=claim_id, stage=stage, quote=quote,
                    source_ref=source_ref, capture=capture,
                    page_content_hash=page_content_hash, media_type=media_type,
                    recorded_at=utc_now())
