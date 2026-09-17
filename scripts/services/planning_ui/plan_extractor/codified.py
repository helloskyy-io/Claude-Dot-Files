"""The codified-block conformance check — cite the block, don't re-list it.

Documentation Standard § *Single-source codified fields* binds a planning
document to CITE a standard's profile or schema block rather than re-type its
field list, and then prescribes its own enforcement:

    gate it — a lightweight doc-conformance check … that diffs the inline list
    against the standard's block, so a drift fails **loud** instead of relying
    on a reviewer noticing.

Relying on a reviewer noticing was the state of it. This is the gate.

**The method is stated in the phase document and mirrored nowhere**; what
follows is only what the code needs to be read against. A block is four or
more field NAMES — values are never read and no YAML is parsed, because a
semantic differ is a research project and a set overlap over a stated
threshold is a worklist.

**The two outcomes are not one finding with a severity flag.** A copy that has
DIVERGED from the block it copies is already wrong: the rule was written from
a `workload-trusted` list that dropped `pod_security: restricted` and stood a
cluster up with no PSA enforcement. A copy that merely DUPLICATES is a
maintenance cost. Collapsing them would rank those level.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import corpus_io
from .contract import Contract
from .fences import advance_fence
from .model import Collector, Provenance

#: A key inside a fenced block. Indented up to eight spaces so a nested key
#: counts; `name:` with nothing after it counts too, because the field is the
#: name and this never reads a value.
KEY_RE = re.compile(r"^\s{0,8}([a-z][a-z0-9_]{2,})\s*:")

#: A table whose first column is a field list. The header cell is the tell —
#: a table of field names says so.
FIELD_HEADER_RE = re.compile(r"^\|\s*(field|key|name|setting|parameter|option)s?\s*\|", re.I)
TABLE_CELL_RE = re.compile(r"^\|\s*`?([a-z][a-z0-9_]{2,})`?\s*\|")

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

#: Below four names a set collides by coincidence across unrelated schemas.
#: Four is the floor for indexing a block AND for calling an overlap a match.
MIN_FIELDS = 4

#: A shared set smaller than half the standard's block is a document that
#: happens to mention some keys, not a copy of the block.
MIN_SHARE = 0.5

CODIFIED_BLOCK_DIVERGED = "CODIFIED_BLOCK_DIVERGED"
CODIFIED_BLOCK_DUPLICATED = "CODIFIED_BLOCK_DUPLICATED"
CODIFIED_BLOCK_UNCLASSIFIED = "CODIFIED_BLOCK_UNCLASSIFIED"
SECTION_CODIFIED = "codified blocks re-listed instead of cited"


@dataclass(frozen=True)
class Block:
    """A field set found in one document, with where to cite it from."""

    file: str
    line: int
    anchor: str
    fields: frozenset[str]


def _slug(heading: str) -> str:
    text = re.sub(r"[`*_\[\]()]", "", heading).strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _slug_target(block: Block) -> str:
    return f"{block.file}#{_slug(block.anchor)}" if block.anchor else block.file


def blocks_in(rel: str, lines: list[str]) -> list[Block]:
    """Every indexable block in one document, fenced or tabular.

    The anchor is the nearest heading ABOVE the block — what a document would
    cite it by, which is the half that makes a finding actionable.
    """
    found: list[Block] = []
    heading = ""
    open_delimiter: str | None = None
    start = 0
    names: set[str] = set()
    in_table = False
    table_names: set[str] = set()
    table_start = 0

    for number, raw in enumerate(lines, start=1):
        was_open = open_delimiter is not None
        open_delimiter, is_boundary = advance_fence(raw, open_delimiter)
        if is_boundary:
            if not was_open:                       # opened
                start, names = number, set()
            else:                                  # closed
                if len(names) >= MIN_FIELDS:
                    found.append(Block(rel, start, heading, frozenset(names)))
            continue
        if open_delimiter is not None:
            match = KEY_RE.match(raw)
            if match:
                names.add(match.group(1))
            continue

        if FIELD_HEADER_RE.match(raw):
            in_table, table_names, table_start = True, set(), number
            continue
        if in_table:
            cell = TABLE_CELL_RE.match(raw)
            if cell:
                table_names.add(cell.group(1))
                continue
            if not raw.startswith("|"):
                if len(table_names) >= MIN_FIELDS:
                    found.append(Block(rel, table_start, heading, frozenset(table_names)))
                in_table = False
            continue

        head = HEADING_RE.match(raw)
        if head:
            heading = head.group(2)

    if in_table and len(table_names) >= MIN_FIELDS:
        found.append(Block(rel, table_start, heading, frozenset(table_names)))
    return found


def index_standards(root: Path, collector: Collector) -> list[Block]:
    """Every codified block the standards tree carries."""
    return [
        block
        for rel in corpus_io.iter_markdown(root, collector=collector)
        if rel.startswith("standards/")
        for block in blocks_in(rel, corpus_io.read_lines(root, rel, collector))
    ]


#: A name carried by more than this share of ALL blocks in the corpus is
#: STRUCTURAL, not
#: distinctive — it says what kind of document this is, not which block it
#: copies. Derived from the corpus rather than authored: a hand-written list of
#: `apiVersion`/`kind`/`metadata` would be this tool asserting what Kubernetes
#: manifests look like, which is knowledge it has no business holding.
UBIQUITY = 0.10


def structural_names(index: list[Block]) -> frozenset[str]:
    """Names that cannot identify WHICH block was copied, because more than one
    block carries them.

    No threshold and nothing to tune: a name appearing in two different
    standards' blocks is structure or a common noun — `kind`, `metadata`,
    `spec`, `name`, `type`, `path` — and matching on it says only that both
    documents are YAML. **Derived, never authored:** a hand-written stopword
    list would be this tool asserting what a Kubernetes manifest looks like,
    which is knowledge it has no business holding, and it would go stale
    against a corpus that grew a new document family.

    Measured over the STANDARDS INDEX and never over the copies. Counting the
    copies would let a widely-re-listed block make its own fields look
    structural and disappear from its own check — the failure mode is that the
    more a block is duplicated, the less detectable each duplicate becomes.
    """
    seen: dict[str, int] = {}
    for block in index:
        for name in block.fields:
            seen[name] = seen.get(name, 0) + 1
    return frozenset(name for name, count in seen.items() if count > 1)


def match_share(copy: Block, standard: Block, structural: frozenset[str]) -> float:
    """Share of a standard's DISTINCTIVE names that the copy reproduces."""
    distinctive = standard.fields - structural
    if len(distinctive) < MIN_FIELDS:
        return 0.0
    shared = (copy.fields & distinctive)
    if len(shared) < MIN_FIELDS:
        return 0.0
    return len(shared) / len(distinctive)


def check(
    root: Path,
    collector: Collector,
    contract: Contract | None = None,
    scope: tuple[str, ...] | None = None,
) -> tuple[int, int]:
    """Report every re-listed block in ``scope``; resolve nothing.

    ``scope`` is DATA — the prefixes walked — so widening or narrowing which
    documents the rule is enforced over is a list change and not a rewrite.
    Returns (findings, unclassifiable tail).
    """
    contract = contract or Contract()
    scope = scope if scope is not None else contract.codified_scope
    index = index_standards(root, collector)
    structural = structural_names(index)
    reported = 0
    tail: list[Block] = []

    for rel in corpus_io.iter_markdown(root, collector=collector):
        if not rel.startswith(scope) or contract.excluded_from_census(rel):
            continue
        for copy in blocks_in(rel, corpus_io.read_lines(root, rel, collector)):
            best, share = None, 0.0
            for standard in index:
                ratio = match_share(copy, standard, structural)
                if ratio > share:
                    best, share = standard, ratio
            if best is None:
                continue
            if share < MIN_SHARE:
                # Overlaps a block but under the threshold: neither obviously a
                # copy nor obviously not one. Named, never dropped — a count a
                # reader cannot act on without going looking is a number.
                tail.append(copy)
                collector.add_finding(
                    CODIFIED_BLOCK_UNCLASSIFIED,
                    SECTION_CODIFIED,
                    f"shares {len(copy.fields & (best.fields - structural))} field name(s) with "
                    f"the block at `{_slug_target(best)}` — under the stated threshold, so "
                    f"neither obviously a re-listing nor obviously not one",
                    Provenance(copy.file, copy.line),
                    expected="read it and either cite the block or leave it; the check will not decide",
                )
                continue
            missing = sorted((best.fields - structural) - copy.fields)
            where = _slug_target(best)
            if missing:
                collector.add_finding(
                    CODIFIED_BLOCK_DIVERGED,
                    SECTION_CODIFIED,
                    f"re-lists the block at `{where}` and is MISSING "
                    f"{', '.join(f'`{m}`' for m in missing)} — a copy that has drifted "
                    f"is already wrong, not merely redundant",
                    Provenance(copy.file, copy.line),
                    expected="cite the block; a field the standard carries and this does not is a gap that ships",
                )
            else:
                collector.add_finding(
                    CODIFIED_BLOCK_DUPLICATED,
                    SECTION_CODIFIED,
                    f"re-lists the block at `{where}` rather than citing it",
                    Provenance(copy.file, copy.line),
                    expected="cite the block by its anchor; a second copy drifts silently",
                )
            reported += 1

    return reported, len(tail)
