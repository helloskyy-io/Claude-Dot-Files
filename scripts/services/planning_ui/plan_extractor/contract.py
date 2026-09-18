"""The corpus contract — what this tool assumes a planning repository IS.

**Everything here used to be compiled into the modules that consumed it**, as
tuples naming this repository's directories and documents. That is what made
the package unable to read any corpus but the one it grew up in: a second
planning repo would have failed in as many places as it differed, and each
failure would have been reported as a corpus defect rather than as a layout
nobody had told the tool about.

So the split this module draws is the one that matters:

**CONVENTION** — true of every planning repository, because a standard says
so. The four ``tracked/`` stores, a component's ``roadmap.md``, phase
documents named ``phaseN_``. These are defaults and a repository does not
restate them.

**LOCAL** — true of ONE repository: which of its directories are not corpus,
which document names it uses for things that are legitimately not graph
nodes, and anything it excludes from the amendment census. These have no
defaults worth shipping, so a repository states them in ``corpus.toml`` at its
root, and a repository that states nothing gets the conventions alone.

``tomllib`` is standard library from 3.11, so reading it adds no dependency —
which §1.1 rule 5 requires and which is also why this is not YAML.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

#: Excluded from the amendment census wherever the corpus lives, because each
#: would make the census report the thing it measures against:
#: ``tracked/standards/`` is the canonical amendment surface, and the standard
#: defining the convention quotes the convention throughout.
CONVENTION_CENSUS_EXCLUSIONS: tuple[str, ...] = (
    "tracked/standards/",
    "standards/documentation/tracked_items_standard.md",
)

#: Document names that are recognised and are deliberately not graph nodes.
#: Naming them is what keeps the unclassified tail meaningful — an unnamed
#: document class would be reported as a finding on every run.
CONVENTION_NOT_A_NODE: tuple[str, ...] = (
    "requirements.md",
    "dependencies.md",
    "review-resolutions.md",
)

#: The documents the codified-block check is enforced over. DATA, not
#: structure: § Single-source codified fields binds planning documents today,
#: and a ruling that widens or narrows it is a list change here.
CONVENTION_CODIFIED_SCOPE: tuple[str, ...] = ("development/",)

#: The one pattern entry a document list admits: a file named after the
#: directory it sits in.
COMPONENT_RECORD_PATTERN = "{component}.md"

CORPUS_FILE = "corpus.toml"

#: What a directory must have to be a planning repository this tool can read.
#: Each entry is (path, what its absence means) — the message is half the
#: value, because a corpus that fails must say WHICH condition it failed
#: rather than derive an empty graph.
#: `standards/` and `tracked/` are NOT here, deliberately. The tool reads both
#: and tolerates either being absent — a repository with no tracked items has
#: an empty decisions page, and a dependency on a standard that is not there
#: reports a broken edge. Both are findings about a corpus, which is what this
#: tool is for. Requiring them would refuse a young planning repo that is
#: simply early, and refusing what you can report is the stricter-than-needed
#: contract this phase exists to avoid inventing.
REQUIRED: tuple[tuple[str, str], ...] = (
    ("development", "no `development/` — the tree every component is discovered under"),
    ("development/sprints.md", "no `development/sprints.md` — the sprint plan the graph reads"),
)


def unmet_condition(root: Path) -> str | None:
    """The first requirement ``root`` fails, or ``None`` if it is a corpus.

    One viewer serves one planning repository — the one the caller named —
    so this is only ever asked about that root. It says which condition
    failed rather than deriving an empty graph.

    Never read as an empty corpus: a missing `development/` is not zero
    components, and reporting it as zero is the silent-drop this package
    exists to refuse one level up.
    """
    if not root.is_dir():
        return f"{root} is not a directory"
    for relative, complaint in REQUIRED:
        if not (root / relative).exists():
            return complaint
    return None


def is_planning_repo(root: Path) -> bool:
    return unmet_condition(root) is None


@dataclass(frozen=True)
class Contract:
    """What one repository's corpus looks like: conventions plus its own."""

    census_exclusions: tuple[str, ...] = CONVENTION_CENSUS_EXCLUSIONS
    not_a_node: tuple[str, ...] = CONVENTION_NOT_A_NODE
    #: Directories under the repository root that hold no corpus at all.
    not_corpus: tuple[str, ...] = field(default_factory=tuple)
    codified_scope: tuple[str, ...] = CONVENTION_CODIFIED_SCOPE
    #: Where THIS corpus is checked out on hosts that follow its convention,
    #: e.g. a platform whose root CLAUDE.md says every repo lives under one
    #: directory and is linked by absolute path. A link written against it is
    #: HOST-ABSOLUTE: it resolves on such a host and nowhere else. The resolver
    #: strips the prefix so the graph is correct from any checkout, and every
    #: such link is reported for its owner to rewrite. Empty means the corpus
    #: has no such convention, and an absolute link is simply a broken one.
    canonical_checkout: str = ""
    #: Whether a sprint work item must carry a `· L<n> ·` layer. The
    #: Documentation Standard's item shape does not ask for one; MDC's
    #: `sprints.md` §6 does, from its Deployment Layer Model, so MDC declares
    #: it. Read against a corpus that never had layers, the requirement
    #: reported every item as unparsed — 72 findings about a rule that corpus
    #: does not have.
    sprint_layer_required: bool = False
    #: Whether a component directory with planning documents and no
    #: `roadmap.md` is a finding. SkyyNet's sprint plan rules the opposite —
    #: *"a component with no plan yet is UNPLANNED, not non-conformant"* — so
    #: there such a directory is counted, not reported.
    unplanned_components_conformant: bool = False

    #: Filenames that are PHASE DOCUMENTS beyond the conventional `phaseN_`
    #: shape. SkyyNet's sprint plan rules *"`<name>/<name>.md` is its phase
    #: doc"* — one per component, named after it, linked from sprint items as
    #: the phase — so that corpus declares `{component}.md` here. Read as a
    #: phase document it is a node, a sprint item linking it is phase-linked,
    #: and a roadmap's `**Implementation:**` may name it.
    phase_documents: tuple[str, ...] = ()

    def not_a_node_entry(self, rel_path: str) -> str | None:
        """The `not_a_node` entry a document matches by name, or ``None``."""
        return _match_entry(self.not_a_node, rel_path)

    def is_phase_document(self, rel_path: str) -> bool:
        """Whether a corpus-declared phase-document name matches."""
        return _match_entry(self.phase_documents, rel_path) is not None

    def excluded_from_census(self, rel: str) -> bool:
        return any(
            rel == prefix or rel.startswith(prefix)
            for prefix in self.census_exclusions + self.not_corpus
        )


def _match_entry(entries: tuple[str, ...], rel_path: str) -> str | None:
    """The entry a document matches by name, or ``None``. `{component}.md`
    matches a file named after the directory it sits in."""
    parts = rel_path.split("/")
    name = parts[-1]
    for entry in entries:
        if entry == COMPONENT_RECORD_PATTERN:
            if len(parts) >= 2 and name == parts[-2] + ".md":
                return entry
        elif entry == name:
            return entry
    return None


@lru_cache(maxsize=None)
def contract_for(root: Path) -> Contract:
    """The corpus's contract, read once per root — for the readers that are
    asked per link and hold a root but no contract."""
    return load(root.resolve())


def load(root: Path) -> Contract:
    """Read ``corpus.toml`` if the repository has one; conventions if not.

    A repository with no local shape needs no file, and a malformed one is
    raised rather than defaulted: a tool that silently falls back to the
    conventions would read a smaller corpus than the operator declared and
    report the difference as findings about their documents.
    """
    path = root / CORPUS_FILE
    if not path.is_file():
        return Contract()
    # `read_text` rather than `open`: a handle could have been opened for
    # writing and the read-only guard cannot tell the difference. Nothing in
    # this package opens one.
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    corpus = raw.get("corpus", {})
    return Contract(
        census_exclusions=CONVENTION_CENSUS_EXCLUSIONS
        + tuple(corpus.get("census_exclusions", ())),
        not_a_node=CONVENTION_NOT_A_NODE + tuple(corpus.get("not_a_node", ())),
        not_corpus=tuple(corpus.get("not_corpus", ())),
        codified_scope=tuple(corpus.get("codified_scope", CONVENTION_CODIFIED_SCOPE)),
        canonical_checkout=str(corpus.get("canonical_checkout", "")).rstrip("/"),
        phase_documents=tuple(corpus.get("phase_documents", ())),
        sprint_layer_required=bool(corpus.get("sprint_layer_required", False)),
        unplanned_components_conformant=bool(corpus.get("unplanned_components_conformant", False)),
    )


@lru_cache(maxsize=None)
def canonical_checkout_for(root: Path) -> str:
    """The corpus's declared host path, read once per root.

    Asked per link — thousands of times in one derivation — so the file is
    read once. The cache is keyed on the resolved root, which is what makes
    two corpora in one process keep their own answers.
    """
    return load(root.resolve()).canonical_checkout
