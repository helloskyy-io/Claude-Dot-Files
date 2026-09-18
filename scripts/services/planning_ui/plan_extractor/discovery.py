"""Discovery: enumerate every ``.md`` under ``development/``, then classify.

**A glob is a silent filter, and this phase's spine forbids silent filters.**
``development/**/roadmap.md`` and ``^phase(\\d+)([a-z]?)_[a-z0-9_-]+\\.md$``
describe what a well-formed corpus *should* contain. Used as the discovery
mechanism they answer a different question — *what did I happen to match* — and
everything they miss leaves no trace. That is never-silently-drop failing at the
FILE layer, which is worse than the line layer: a dropped line is one finding, a
dropped file is a whole component or phase absent from the graph.

So: enumerate, classify, and report what classifies as nothing but is component-
or phase-SHAPED.

The taxonomy is deliberately wide. ``development/`` holds ~40 ``.md`` files that
are legitimately not graph nodes — research papers, ``requirements.md``,
``review-resolutions.md``, ``dependencies.md``, ``surfaced_standards_changes.md``,
``sprints_archive_*.md``, ``development/CLAUDE.md``. **These are
recognised-and-not-a-node classes, not unclassified ones.** Without them the
report carries forty benign rows, the findings that matter are buried, and the
cheapest fix an implementer reaches for is a hardcoded suppression list — which
is the glob's silent filter, reintroduced one layer up.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import corpus_io
from .fences import fenced_mask
from .contract import COMPONENT_RECORD_PATTERN, Contract
from .model import (
    COMPONENT_SHAPED_NO_ROADMAP,
    SECTION_UNCLASSIFIED,
    UNCLASSIFIED_FILE,
    UNCLASSIFIED_PHASE_SHAPED,
    Collector,
    Provenance,
)

# The Documentation Standard's hard external constraint on a phase filename.
# It is a CLASSIFIER, not a discovery mechanism.
PHASE_FILENAME_RE = re.compile(r"^phase(\d+)([a-z]?)_[a-z0-9_-]+\.md$")

# Headings that make a document phase-shaped independently of its filename.
PHASE_SHAPE_HEADINGS = (
    "## Requirements for completion",
    "## Implementation steps",
)

# --- Classification vocabulary --------------------------------------------
ROADMAP = "roadmap"
PHASE_DOC = "phase_doc"
SPRINTS = "sprints"
SPRINTS_ARCHIVE = "sprints_archive"
DEPENDENCIES = "dependencies"
RESEARCH = "research"
REQUIREMENTS = "requirements"
REVIEW_RESOLUTIONS = "review_resolutions"
SURFACED_STANDARDS = "surfaced_standards_changes"
REPO_INSTRUCTIONS = "repo_instructions"
UNCLASSIFIED = "unclassified"
#: `<name>/<name>.md` — a component's decision record, where a corpus declares one.
COMPONENT_RECORD = "component_record"

#: Classes that are recognised and are deliberately not graph nodes. Naming them
#: is what keeps the unclassified tail meaningful.
def not_a_node_classes(contract: Contract | None = None) -> frozenset[str]:
    """Recognised classes that are deliberately not graph nodes.

    Two structural ones this tool owns, plus one per recognised document name
    the corpus declares — so a repository that recognises a document type this
    one does not still gets a named class rather than an unclassified tail.
    """
    names = (contract or Contract()).not_a_node
    return frozenset({SPRINTS_ARCHIVE, RESEARCH, REPO_INSTRUCTIONS} | {_class_for(n) for n in names})


def _class_for(entry: str) -> str:
    """The class name a `not_a_node` entry classifies as. The one pattern
    entry, `{component}.md`, is one class for every match."""
    if entry == COMPONENT_RECORD_PATTERN:
        return COMPONENT_RECORD
    return entry.removesuffix(".md").replace("-", "_")


NOT_A_NODE_CLASSES = frozenset(
    {
        SPRINTS_ARCHIVE,
        DEPENDENCIES,
        RESEARCH,
        REQUIREMENTS,
        REVIEW_RESOLUTIONS,
        SURFACED_STANDARDS,
        REPO_INSTRUCTIONS,
    }
)


@dataclass(frozen=True)
class DiscoveredFile:
    """One enumerated ``.md`` and the class it was assigned."""

    path: str  # repo-relative POSIX
    classification: str
    #: Which classifier it came closest to, for an unclassified file.
    nearest: str = ""


def enumerate_markdown(
    root: Path,
    subdir: str = "development",
    collector: Collector | None = None,
    contract: Contract | None = None,
) -> list[str]:
    """Every ``.md`` under ``<root>/<subdir>``, repo-relative, sorted.

    Thin wrapper over :func:`corpus_io.iter_markdown`, which owns the walk for
    the whole package — including the symlink-leaves-the-root check, which the
    three hand-copied walks this replaced did not have. A directory the
    contract declares `not_corpus` is not walked: it holds no corpus, so
    classifying what is in it would report findings about documents nobody
    maintains as planning — measured on a repository whose past review
    records sit under `development/common/reviews/`.
    """
    return corpus_io.iter_markdown(
        root, subdir, collector=collector,
        exclude_prefixes=(contract or Contract()).not_corpus,
    )


def classify(rel_path: str, contract: Contract | None = None) -> str:
    """Assign one class to an enumerated file, by path and name only.

    Deliberately does NOT read the file: classification by content is what the
    shape tests below do, and keeping the two separate means an unreadable file
    still gets a class rather than vanishing.
    """
    parts = rel_path.split("/")
    name = parts[-1]

    if name == "roadmap.md":
        return ROADMAP
    if rel_path == "development/sprints.md":
        return SPRINTS
    if name.startswith("sprints_archive"):
        return SPRINTS_ARCHIVE
    if name == "CLAUDE.md":
        return REPO_INSTRUCTIONS
    if "research" in parts[:-1]:
        return RESEARCH
    # A document a corpus recognises and deliberately does not make a node.
    # WHICH names those are is the corpus's, not this tool's: the conventional
    # three ship in `contract`, and a repository adds its own in `corpus.toml`.
    # They are one class here — the census and the graph care that the document
    # is named, not what its name was.
    matched = (contract or Contract()).not_a_node_entry(rel_path)
    if matched is not None:
        # The CLASS is the document's own stem, so the report keeps naming
        # `requirements` and `review-resolutions` separately rather than
        # flattening them into one bucket. What the contract decides is WHICH
        # names are recognised, not what they are then called.
        return _class_for(matched)
    if PHASE_FILENAME_RE.match(name) or (contract or Contract()).is_phase_document(rel_path):
        return PHASE_DOC
    return UNCLASSIFIED


def is_phase_shaped(
    root: Path,
    rel_path: str,
    sprint_linked: frozenset[str],
    collector: Collector | None = None,
) -> str:
    """Return the reason a file is phase-shaped, or ``""``.

    The stated test, not an intuition: *a file linked from a ``sprints.md``
    item, or carrying a ``## Requirements for completion`` /
    ``## Implementation steps`` heading, that matches no phase filename
    pattern.* Tuning this predicate until exactly the known cases fall out would
    be the same defect the enumerate-then-classify rule exists to prevent.

    **The heading must be unfenced**, the same ruling every other walk in this
    package applies: a heading inside a fenced block is an EXAMPLE of the shape,
    not the shape. This walk read fenced headings until ``fences`` was extracted
    as a leaf module — :mod:`~.roadmaps` imports this one, so while the
    delimiter lived in ``roadmaps`` this was the one member of the class that
    could not ask. Latent when closed (0 fenced phase-shape headings on the live
    corpus, and the derived artifact does not move), which is exactly why it
    could sit open: nothing failed.
    """
    if rel_path in sprint_linked:
        return "linked from a sprints.md item"
    text = corpus_io.read_text(root, rel_path, collector)
    if text is None:
        # Reported by read_text. NOT phase-shaped is the honest answer here: the
        # predicate reads a heading and the heading could not be read. The file
        # itself is already a finding, so nothing is dropped.
        return ""
    lines = text.splitlines()
    fenced = fenced_mask(lines)
    for heading in PHASE_SHAPE_HEADINGS:
        if any(
            line.strip() == heading
            for line, masked in zip(lines, fenced)
            if not masked
        ):
            return f"carries a `{heading}` heading"
    return ""


def component_shaped_directories(root: Path, discovered: list[str]) -> list[str]:
    """Directories that hold planning documents and carry no ``roadmap.md``.

    The stated test: *a directory under ``development/<domain>/<name>/`` holding
    at least one planning document and no ``roadmap.md``.* ``development/service/
    <name>/`` with no roadmap is the case — invisible to every glob, because no glob
    reaches a component that has no roadmap.

    Only directories at exactly ``development/<domain>/<name>`` are considered.
    A deeper directory (``.../old/``, ``.../research/``) is a subdirectory of a
    component, not a component, and admitting it would flood the report with the
    thing the wide taxonomy exists to prevent.
    """
    with_roadmap: set[str] = set()
    holding_docs: set[str] = set()
    for rel in discovered:
        parts = rel.split("/")
        if len(parts) != 4:  # development / <domain> / <name> / <file>.md
            continue
        directory = "/".join(parts[:3])
        holding_docs.add(directory)
        if parts[-1] == "roadmap.md":
            with_roadmap.add(directory)
    return sorted(holding_docs - with_roadmap)


def run_discovery(
    root: Path,
    collector: Collector,
    sprint_linked: frozenset[str] = frozenset(),
    contract: Contract | None = None,
) -> list[DiscoveredFile]:
    """Enumerate, classify, and report everything that classifies as nothing.

    ``sprint_linked`` is the set of repo-relative paths any ``sprints.md`` item
    links to. It is passed in rather than computed here because the sprint
    parser owns that read — discovery must not become a second source of it.
    """
    discovered: list[DiscoveredFile] = []
    for rel in enumerate_markdown(root, collector=collector, contract=contract):
        classification = classify(rel, contract)
        nearest = ""
        if classification == UNCLASSIFIED:
            reason = is_phase_shaped(root, rel, sprint_linked, collector)
            if reason:
                nearest = PHASE_DOC
                collector.add_finding(
                    UNCLASSIFIED_PHASE_SHAPED,
                    SECTION_UNCLASSIFIED,
                    f"phase-shaped file matches no phase filename pattern ({reason})",
                    Provenance(rel),
                    expected=PHASE_FILENAME_RE.pattern,
                    detail=(
                        "Classified as a phase document for graph purposes so it is "
                        "not absent; the filename remains non-conforming and the "
                        "rename is corpus work with a separate reviewer."
                    ),
                )
            else:
                collector.add_finding(
                    UNCLASSIFIED_FILE,
                    SECTION_UNCLASSIFIED,
                    "file under development/ classifies as no known class",
                    Provenance(rel),
                    expected=(
                        "roadmap.md | phase{N}_{name}.md | sprints.md | "
                        "dependencies.md | requirements.md | review-resolutions.md | "
                        "surfaced_standards_changes.md | research/ | CLAUDE.md"
                    ),
                )
        discovered.append(DiscoveredFile(rel, classification, nearest))

    unplanned = component_shaped_directories(root, [d.path for d in discovered])
    if (contract or Contract()).unplanned_components_conformant:
        # Counted by the extractor, never reported here: this corpus rules an
        # unplanned component conformant, and a finding would say otherwise
        # on every run.
        unplanned = []
    for directory in unplanned:
        collector.add_finding(
            COMPONENT_SHAPED_NO_ROADMAP,
            SECTION_UNCLASSIFIED,
            "directory holds planning documents and carries no roadmap.md, "
            "so no glob-based discovery reaches it",
            Provenance(directory),
            expected="development/<domain>/<name>/roadmap.md",
        )

    return discovered
