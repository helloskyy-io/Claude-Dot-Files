"""The retired memory-taxonomy labels survive only where they are a RECORD.

`Kind 1` / `Kind 2` / `Kind 3` were replaced on 2026-08-16 by the names
`persistent-memory-protocol/roadmap.md` § *The four kinds of record* declares —
**the working record**, **the typed exit record**, **measurement samples**. The
operator's rule for the sweep was one sentence: *rename it where it is still
binding; leave it where it is a record.* This gate holds the first half.

WHY A GATE RATHER THAN A FIFTH SWEEP. The sweep was performed with
`grep -n 'Kind 1\\|Kind 2\\|Kind 3'` and then *verified complete* with the same
line-based, case-sensitive, space-only scan — so the finding instrument and the
proving instrument shared every blind spot, and the resulting claim landed in a
durable planning entry as a **checkable** one. Three passes each closed the
spellings they could see and the next pass found a structurally adjacent one:

  * the draft pass closed `Kind 1` / `Kind 2` / `Kind 3` written with a space;
  * `review-pr` found `a Kind\\n2 record` — the label **wrapped across a
    newline**, which a line-based grep cannot see, inside a paragraph the same
    PR had edited two lines lower;
  * this pass found `# THE KIND 1 ADDRESS` (**uppercase**), the constant
    `SHARED_KIND_ONE_PATTERNS` and two `test_the_kind_one_*` functions (**the
    number spelled as a word, joined by underscores**, so no word boundary ever
    asserts), and `Kind-1 / Kind-2` (**hyphenated**) in a research synthesis.

Five spellings, four passes. Enumerating instances does not converge; changing
what the check keys on does. So this reads every tracked file as **whitespace-
normalised text** — a different instrument than the one that did the sweep — and
matches the label in any case, with any of the three separators, with the number
written as a digit or as a word.

WHAT THIS GATE DOES NOT LOOK AT, so a green run is not read as more than it is:

  * **Whether the NEW vocabulary is used correctly.** It can say the rename ran.
    It can never say the taxonomy is stated right — every wrong sentence written
    in the new names passes it.
  * **File and directory NAMES.** `phase2_kind1_framework.md` is a path, and the
    pattern deliberately requires a separator so it does not fire on one. A
    future file named `..._kind_two_...` would be invisible here.
  * **Paraphrase.** *"the second kind of record"* carries the retired cut in
    words this pattern has no purchase on.
  * **Whether a RECORD surface is correctly classified.** The allowlist below is
    a judgement, declared once and asserted non-empty — not derived.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_MAP = _REPO / "docs" / "file_structure.txt"

# THE LABEL, IN EVERY SPELLING THAT HAS ACTUALLY SHIPPED IN THIS REPO.
#
# The lookarounds are `[a-zA-Z0-9]` rather than `\b` ON PURPOSE, and it is the
# difference between catching `SHARED_KIND_ONE_PATTERNS` and reporting the tree
# clean while it sits there: `_` is a word character, so `\b` never asserts
# beside one, and a `\b`-anchored pattern is blind to every identifier form.
#
# The separator is MANDATORY, which is what keeps `phase2_kind1_framework.md` —
# a real filename that live documents legitimately cite — out of the match set.
# A label is written `Kind 1`, `KIND_ONE`, `Kind-2`; a path segment is `kind1`.
RETIRED_LABEL = re.compile(
    r"(?<![a-zA-Z0-9])kind[ _-](?:[123]|one|two|three)(?![a-zA-Z0-9])",
    re.IGNORECASE,
)

# A surface where the retired label is a RECORD of what was written at the time,
# and renaming it would make the record describe something that never happened.
# Each entry is a path prefix relative to the repo root, with the reason it is a
# record — the reason is the thing under review when this list is edited.
RECORD_SURFACES: dict[str, str] = {
    "docs/development/memory-management-framework/":
        "the retired component's own docs — the record of what it built",
    "docs/development/sprint.md":
        "the completed MMF sprint entry",
    "docs/development/cpi-decisions.md":
        "the append-only decisions log, including the ruling that made these "
        "exclusions",
    "docs/development/burn-test-intake-2026-08-02.md":
        "a dated intake record of how work was routed on that day",
    "docs/development/persistent-memory-protocol/roadmap.md":
        "§ Reading the old names is the translation table that keeps every "
        "other exclusion readable, and the applied amendment preserves its "
        "original entry verbatim",
    "docs/development/persistent-memory-protocol/research/":
        "research papers and their digests — a record of what was read",
    "docs/standards/architecture/research/":
        "candidates.md's proposal rows, and the pool's synthesis and topic "
        "queues, are records of what was proposed at the time",
    "testing/scripts/tests/unit/test_prompt_budgets.py":
        "a budget-raise comment quoting the old term to state the byte "
        "arithmetic; the quote IS the evidence for the number",
    "testing/scripts/tests/unit/test_retired_vocabulary_is_gone_from_live_surfaces.py":
        "this module — the labels are its SUBJECT, and its docstring quotes "
        "each spelling that shipped as the evidence for the pattern below",
}

# THE FROZEN V1 BASH FLEET IS EXEMPT BY RULE, NOT BY OBSERVATION, so it is kept
# out of `RECORD_SURFACES` — whose entries are asserted to actually exempt
# something. It carries no retired label today, and if it ever acquires one it
# still may not be edited (`personal-tooling.md`: never modify them). An entry
# in the observation-checked list would go red for carrying no label, and the
# only ways to clear that are to delete the exemption or edit a frozen file.
#
# It is `scripts/workflows/*.sh` and `scripts/workflows/children/*.sh` ONLY —
# the Python tree under `scripts/workflows/temporal/` is live and is swept.
_FROZEN_BASH = ("scripts/workflows/", "scripts/workflows/children/")

# `docs/file_structure.txt` is on BOTH sides of the split and must not be
# allowlisted whole: three of its lines annotate the retired component's own
# docs and correctly keep the label, while its entries for LIVE surfaces carried
# it too and were exactly what the sweep had to fix. So it is scoped by LINE,
# using the same predicate as the file-level list — is the path this line
# describes a record? — rather than by a second rule.
_LEAF = re.compile(r"^(.*?)[├└]──\s+(\S+)")
# THE DIVISOR'S VALUE IS NOT LOAD-BEARING, and that is worth saying because a
# mutation of it is green BY DESIGN rather than by a missing assertion. Levels
# are used only as sort keys and as a "deeper than" comparison, so any positive
# divisor reconstructs identical paths — measured: `_MAP_INDENT = 1` leaves all
# 20 tests passing. It is kept at the map's real indent, matching the sibling
# `test_file_structure_map_covers_the_tree.py`, because it is what normalises
# an irregular prefix width if the map ever grows one.
_MAP_INDENT = 4


def _is_record(path: str) -> str | None:
    """The reason `path` is a record surface, or None if it is live."""
    if path.endswith(".sh") and any(
        path.startswith(parent) and "/" not in path[len(parent):]
        for parent in _FROZEN_BASH
    ):
        return "the frozen V1 bash fleet — reference only, never edited"
    for prefix, reason in RECORD_SURFACES.items():
        # A DIRECTORY entry exempts everything beneath it; a FILE entry exempts
        # exactly itself. Matching both with a bare `startswith` silently hands
        # the exemption to any future path that merely BEGINS with a listed
        # filename — `docs/development/sprint.md.bak` would inherit
        # `sprint.md`'s — which is a widened gate nobody decided to widen. Four
        # of the eight entries below are files.
        if path == prefix or (prefix.endswith("/") and path.startswith(prefix)):
            return reason
    return None


def _tracked() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(_REPO), "ls-files"],
        capture_output=True, text=True, check=True,
    ).stdout.split("\n")
    return [line for line in out if line]


def _normalised(path: Path) -> str:
    """The file as ONE line, which is what makes a wrapped label visible.

    This is the whole point of the module: the sweep this gate backstops read
    the tree line by line, and the one survivor it missed was a label split
    across a newline by ordinary paragraph wrapping.
    """
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8", errors="replace"))


def _map_entries() -> list[tuple[list[int], str, str]]:
    """Each map entry as (its line numbers, its text as ONE line, its path).

    AN ENTRY IS A LEAF LINE PLUS EVERY CONTINUATION LINE UNDER IT, and joining
    them is the same correction `_normalised` makes for ordinary files —
    applied here because it was missing, which is the defect this docstring is
    the record of. The scan used to keep only lines matching `_LEAF` and
    `continue` past the rest. Multi-line annotations are the map's DOMINANT
    format, so the gate whose entire thesis is *"a line-based instrument cannot
    see a label wrapped across a newline"* was line-based for the one file it
    claims to handle by careful line-scoping. Two lines carried a label into
    exactly that blind spot.

    The indentation is parsed back into a path the same way its sibling
    `test_file_structure_map_covers_the_tree.py` does — a full path never
    appears on any single line of the map, so a line's subject can only be
    recovered from the nesting. A continuation line has no `──` and therefore
    never moves the stack; it just belongs to whichever leaf preceded it.
    """
    stack: dict[int, str] = {}
    entries: list[tuple[list[int], str, str]] = []
    for number, line in enumerate(_MAP.read_text(encoding="utf-8").splitlines(), 1):
        leaf = _LEAF.match(line)
        if not leaf:
            if entries:
                numbers, text, path = entries[-1]
                numbers.append(number)
                entries[-1] = (numbers, f"{text} {line.strip()}", path)
            continue
        prefix, name = leaf.groups()
        level = len(prefix) // _MAP_INDENT
        stack[level] = name.rstrip("/")
        for deeper in [k for k in stack if k > level]:
            del stack[deeper]
        # The root line (`claude-dot-files/`) carries no `──` and is therefore
        # not a level, which is what makes the reconstruction repo-relative.
        entries.append(([number], line, "/".join(stack[k] for k in sorted(stack))))
    return entries


def _map_entries_describing_live_paths() -> list[tuple[list[int], str, str]]:
    """The entries whose reconstructed tree path is NOT a record surface."""
    return [
        entry for entry in _map_entries()
        if entry[2] and not _is_record(entry[2]) and not _is_record(entry[2] + "/")
    ]


def test_no_live_surface_carries_a_retired_taxonomy_label() -> None:
    """The sweep's claim, re-derived with an instrument the sweep did not use.

    A hit here is not a style nit. The labels were retired because they name
    nothing a reader can act on, and a live document that keeps one hands the
    next author two vocabularies for one thing with no way to tell whether they
    denote the same record.
    """
    offenders = []
    for relative in _tracked():
        if _is_record(relative) or relative.endswith(Path(__file__).name):
            continue
        if relative == "docs/file_structure.txt":
            continue        # scoped by line, in its own test below
        try:
            text = _normalised(_REPO / relative)
        except (OSError, UnicodeDecodeError):
            continue        # binary or unreadable; nothing to read a label in
        found = sorted({m.group(0) for m in RETIRED_LABEL.finditer(text)})
        if found:
            offenders.append(f"{relative} — {found}")
    assert not offenders, (
        "a LIVE surface still carries a retired memory-taxonomy label: "
        + "; ".join(offenders)
        + ". Rename it to the name `persistent-memory-protocol/roadmap.md` "
          "§ The four kinds of record declares — the working record / the "
          "typed exit record / measurement samples — or, if this surface is a "
          "RECORD of what was written at the time, add it to RECORD_SURFACES "
          "in this module WITH the reason it is one."
    )


def test_the_file_structure_map_is_scoped_by_LINE_and_not_exempted_whole() -> None:
    """The map describes live surfaces and retired ones in one file.

    Allowlisting it whole would blind this gate to the exact defect the sweep
    had to fix in it — three entries describing LIVE surfaces (`memory-model.md`,
    `exit_record.py`, the one-declaration gates) by the retired labels — while
    the three lines annotating the retired component's own docs must keep them.
    """
    offenders = [
        f"{_MAP.name}:{numbers[0]} ({path}) — "
        f"{sorted({m.group(0) for m in RETIRED_LABEL.finditer(text)})}"
        for numbers, text, path in _map_entries_describing_live_paths()
        if RETIRED_LABEL.search(text)
    ]
    assert not offenders, (
        "a `docs/file_structure.txt` entry describes a LIVE surface using a "
        "retired taxonomy label: " + "; ".join(offenders)
        + ". The map is authoritative per CLAUDE.md, so an entry that names a "
          "live file by a retired term sends a reader looking for something "
          "that no longer exists under that name."
    )


def test_the_map_scope_still_reaches_the_lines_that_must_keep_the_label() -> None:
    """The line scoping is only worth anything if it also EXEMPTS correctly.

    If `_map_lines_describing_live_paths` silently returned every line, the
    assertion above would go red on the three retired-component annotations and
    someone would allowlist the whole file to make it stop — which is the
    outcome this scoping exists to avoid.

    THE THIRD ASSERTION IS THE ONE THAT IS NOT A COPY OF THE TEST ABOVE, and it
    is here because the first draft of this module got that wrong: it asserted
    `not (labelled & live)`, which is the same predicate its sibling already
    checks, so a single mutation turned two tests red and neither told you
    anything the other did not. The unique property is the COMPLEMENT — that
    some labelled line is exempted — because that is what fails if the path
    reconstruction breaks in the direction nothing else notices.
    """
    live = {
        number
        for numbers, _, _ in _map_entries_describing_live_paths()
        for number in numbers
    }
    assert live, "the map parse produced no live lines — it read nothing"
    labelled = {
        number
        for number, line in enumerate(_MAP.read_text(encoding="utf-8").splitlines(), 1)
        if RETIRED_LABEL.search(line)
    }
    assert labelled, (
        "no `file_structure.txt` line carries a retired label any more. If the "
        "retired component's own annotations were rewritten, this test and its "
        "sibling above have nothing left to scope — delete both and say so."
    )
    assert labelled - live, (
        "every labelled map line was classified as describing a LIVE path, so "
        "the scoping is exempting nothing and its sibling above is really a "
        "file-wide check wearing a line-scoped name. The retired component's "
        "own annotations must resolve to paths under "
        "`docs/development/memory-management-framework/` — if the map's "
        "indentation convention changed, `_MAP_INDENT` and `_LEAF` moved with it."
    )


def test_the_sweep_reads_a_real_corpus() -> None:
    """A gate reporting a clean tree and a gate reading nothing look identical.

    `git ls-files` failing, or the worktree resolving somewhere unexpected,
    would make the sweep above pass on an empty list.
    """
    tracked = _tracked()
    assert len(tracked) > 200, (
        f"the sweep read only {len(tracked)} tracked files from {_REPO} — the "
        f"corpus is wrong, and every assertion built on it is vacuous"
    )
    assert _MAP.exists(), f"the map moved: {_MAP}"


def test_every_declared_RECORD_SURFACE_still_carries_a_label() -> None:
    """An allowlist entry that stopped matching is a silently widened gate.

    A record surface that is renamed, deleted, or cleaned leaves an entry here
    exempting nothing — and the next live file that lands under that prefix
    inherits the exemption without anyone deciding to give it one.
    """
    stale = []
    for prefix, reason in RECORD_SURFACES.items():
        target = _REPO / prefix
        candidates = (
            sorted(p for p in target.rglob("*") if p.is_file())
            if target.is_dir() else [target]
        )
        if not any(
            p.exists() and RETIRED_LABEL.search(_normalised(p))
            for p in candidates
        ):
            stale.append(f"{prefix} ({reason})")
    assert not stale, (
        "a RECORD_SURFACES entry exempts nothing — the surface no longer "
        "carries a retired label, or it moved: " + "; ".join(stale)
        + ". Delete the entry. Leaving it in place hands a blanket exemption "
          "to whatever lands at that path next."
    )
    # The frozen bash fleet is exempted by RULE rather than by observation — it
    # carries no label today and may never be edited if it acquires one — so it
    # is deliberately NOT in the loop above. Stated here so its absence reads as
    # a decision rather than an oversight.


@pytest.mark.parametrize("spelling", [
    "Kind 1",                          # the draft sweep's target
    "Kind 2",
    "Kind 3",
    "a Kind\n2 record's lifetime",     # `review-pr`'s find: wrapped by prose
    "# THE KIND 1 ADDRESS, DECLARED",  # uppercase, in a code comment
    "SHARED_KIND_ONE_PATTERNS",        # word-form number, underscore-joined
    "def test_the_kind_one_reference",
    "the Kind-1 / Kind-2 cut",         # hyphenated, in a research synthesis
    "kind 2, the transport layer",     # lowercase, in a routing table
])
def test_the_pattern_catches_every_spelling_that_has_actually_shipped(
    spelling: str,
) -> None:
    """Each of these was a real survivor, found by a later pass than the one
    that believed the sweep complete. A pattern that stops matching one of them
    turns this module into a permanent pass."""
    assert RETIRED_LABEL.search(re.sub(r"\s+", " ", spelling)), (
        f"the pattern no longer matches {spelling!r} — a spelling that really "
        f"survived a sweep in this repo. The gate would report the tree clean "
        f"while reading past it."
    )


@pytest.mark.parametrize("benign", [
    "phase2_kind1_framework.md",       # a real filename live docs cite
    "docs/development/memory-management-framework/phase2_kind1_framework.md",
    "what kind of record is this",
    "a third kind of surface",
    "mankind 1",
    "kindly note",
])
def test_the_pattern_does_not_fire_on_paths_or_ordinary_prose(benign: str) -> None:
    """A gate that cannot be satisfied gets allowlisted into uselessness.

    The filename cases are the load-bearing ones: `phase2_kind1_framework.md` is
    cited by `memory-model.md`, `exit-protocol.md` and the map itself, so a
    pattern that fired on it would demand exemptions for three live files.
    """
    assert not RETIRED_LABEL.search(benign), (
        f"the pattern fires on {benign!r}, which carries no retired label"
    )
