"""The retired memory-taxonomy labels survive only where they are a RECORD.

`Kind 1` / `Kind 2` / `Kind 3` were replaced on 2026-08-16 by the names
`persistent-memory-protocol/roadmap.md` § *Reading the old names* maps them to —
**the working record**, **the typed exit record**, **measurement samples**. The
operator's rule for the sweep was one sentence: *rename it where it is still
binding; leave it where it is a record.* This gate holds the first half.

CITE § *Reading the old names*, NOT § *The four kinds of record*. The enclosing
section declares FOUR classes — *invocation state*, *the working record*, *the
journal*, *measurement samples* — and **the typed exit record is invocation
state's one contracted member rather than a class of its own**. The three names
above are the old-label *translation*, which is what § *Reading the old names*
is. An author tripping this gate on a document about a run's in-flight state or
about the journal must not be handed a three-name menu with no name for their
case; the roadmap's ⚠ against reading *invocation state* as a leftovers bin is
the same failure one level up.

THE REPRESENTATION RULE, because breaking it is what every pass here has done.
**Every predicate below consumes the record's own representation — a file as
normalised text, a map entry as its joined leaf-plus-continuations — and none
reads a raw line as a stand-in for it.** A raw line is a *proxy* for a document,
and each of the four passes that believed this sweep complete was defeated by
that proxy exactly once: three by a line-based `grep`, and the fourth by
`labelled` below, which was assembled line by line inside this very module and
then subtracted from an entry-granular set. The rule is stated as a rule so the
next predicate added here is a conformance question rather than a rediscovery.

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
    future file named `..._kind_two_...` would be invisible **as a name** — and
    would be a false POSITIVE in every live document citing it, because such a
    name carries the separator. That is the costly direction, and the benign
    corpus below covers only the separator-less `kind1` form that has shipped.
  * **Paraphrase.** *"the second kind of record"* carries the retired cut in
    words this pattern has no purchase on.
  * **Whether a RECORD surface is correctly classified.** The allowlist below is
    a judgement, declared once and asserted non-empty — not derived.
  * **Decoration this joiner does not know, and decoration that is not at the
    START of a line.** `_normalised` strips the tree glyphs, a leading `#` and a
    leading `>` before it joins, because those are what lines open with in this
    repo's Python, shell, YAML and markdown. It does NOT strip `//`, `/*`, `*`,
    `--`, `;` or `<!--`, so a label wrapped across two lines decorated by one of
    those is invisible exactly as the `#` case was — the fix is to add the
    marker to `_joinable`, and
    `test_the_UNSTRIPPED_MARKERS_are_the_residual_and_are_NOT_seen` below holds
    that gap as a checkable claim rather than a sentence. Stripping is
    line-LEADING only on purpose: a `#` mid-line is content, and stripping
    there would invent joins no renderer makes, so a right-hand decoration (a
    box-drawing `│` closing a column, a `*/`) still separates the two halves of
    a label.
  * **A label split MID-WORD.** `Ki` / `nd 1` survives every normalisation here,
    because no amount of whitespace or decoration handling puts the word back
    together. `test_a_label_split_MID_WORD_is_the_residual_and_is_NOT_seen`
    below holds this limit as a checkable claim rather than a sentence.

WHAT THIS GATE COSTS, which is not the same list as what it cannot see:

  * **Joining lines can BRIDGE two unrelated ones into a false positive.** The
    line-joining premise is what makes a wrapped label visible, and it cannot
    distinguish a wrapped label from an ordinary sentence ending in the English
    word *"kind"* followed by a line opening with `1`. That bridge is not new —
    plain prose has joined that way since this module shipped — but routing
    every file through `_joinable` extends it to `#`-commented and `>`-quoted
    boundaries, which is where such a pair is likelier. It is a LOUD failure:
    the suite goes red and names the file, so nothing hides.
    **IF IT FIRES ON INNOCENT PROSE, THE FIX IS NOT A NEW `RECORD_SURFACES`
    ENTRY.** That allowlist declares a surface to be a historical RECORD, and
    using it to silence a bridging false positive misclassifies a live document
    forever to quiet one line. Reword the prose, or narrow `RETIRED_LABEL` —
    and if neither is acceptable, that is a finding about the pattern, not a
    surface to exempt.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import NamedTuple

import pytest

_REPO = Path(__file__).resolve().parents[4]
_MAP = _REPO / "docs" / "file_structure.txt"

import sys as _s  # noqa: E402
_s.path.insert(0, str(_REPO / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import PLANNING_ROOT  # noqa: E402

import sys as _cg_sys  # noqa: E402
from pathlib import Path as _cg_Path  # noqa: E402
_cg_sys.path.insert(0, str(_cg_Path(__file__).resolve().parents[4]
                           / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import require_planning_corpus  # noqa: E402


# TWO ROOTS. The prose this sweeps moved to the planning repo while the code it
# describes stayed here. Sweeping one root would leave the half that actually
# CONTAINS the retired vocabulary unread, and report clean — the precise
# "reads nothing, looks green" failure the vacuity test below exists to catch,
# arriving through the corpus rather than through `git ls-files`.
_ROOTS = (_REPO, PLANNING_ROOT)

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
    "development/edge-assistant/memory-management-framework/":
        "the retired component's own docs — the record of what it built",
    "development/sprints.md":
        "the completed MMF sprint entry",
    "development/common/cpi-decisions.md":
        "the append-only decisions log, including the ruling that made these "
        "exclusions",
    "development/edge-assistant/persistent-memory-protocol/roadmap.md":
        "§ Reading the old names is the translation table that keeps every "
        "other exclusion readable, and the applied amendment preserves its "
        "original entry verbatim. FILE-WIDE, and that is broader than the two "
        "sections that need it: this is a LIVE document and the taxonomy's "
        "declared single writer, so it could reintroduce a label as binding "
        "vocabulary and this gate would be silent. Scoped file-wide anyway "
        "because narrowing it needs a section parser whose own correctness "
        "nothing would assert — a disclosed gap traded for an undisclosed one. "
        "The residual is stated here so the judgement is reviewable rather "
        "than invisible",
    "development/edge-assistant/persistent-memory-protocol/research/":
        "research papers and their digests — a record of what was read",
    "tracked/candidates/":
        "the SAME proposal rows as the entry below, moved on 2026-08-26 when "
        "candidates.md became one file per item. Nothing about the content "
        "changed — the three labels this catches were written in 2026-07 and "
        "migrated verbatim — so the exemption follows the rows to their new "
        "home rather than the rows losing it by being moved. Rewriting a "
        "migrated proposal's own words to satisfy a later taxonomy would "
        "falsify the record this exemption exists to preserve",
    "research/":
        "candidates.md's proposal rows, and the pool's synthesis and topic "
        "queues, are records of what was proposed at the time. This is the one "
        "standards-tree path autonomous runs may WRITE to every cycle, so the "
        "exemption is the widest here and the least reviewed — it holds "
        "because appending to a proposal queue IS recording what was proposed "
        "at the time, which is the shape the operator's rule exempts",
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
# `personal-tooling.md` names `scripts/workflows/*.sh` and
# `scripts/workflows/children/*.sh`, and that enumeration is correct.
#
# ⚠ `scripts/workflows/activities/` WAS ADDED HERE ON 2026-08-18 AND REMOVED THE
# SAME DAY. The stated reason was that nothing in the Python tree executes it —
# established by grepping for `subprocess` near the filename and finding only
# comments. THAT WAS WRONG. `assistant_activities.run_claude` sources it on EVERY
# dispatch:
#
#     runner = _WORKFLOWS / "activities" / "run-claude.sh"
#     argv = ["bash", "-c", f'source "{runner}"; run_claude "$1"', "_", prompt]
#
# It is the live dispatcher for the whole V2 fleet — it passes `--max-turns`,
# owns the completion contract and the turn-cap failure. Exempting it hid a live
# surface from this sweep. The lesson is narrower than the bug: a `bash -c
# source` invocation is invisible to a grep for `subprocess`.
#
# The Python tree under `scripts/workflows/temporal/` is live and IS swept.
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


def _is_record(path: str, *, is_dir: bool = False) -> str | None:
    """The reason `path` is a record surface, or None if it is live.

    `is_dir` says whether `path` NAMES A DIRECTORY, and the caller is expected
    to know: a directory key in `RECORD_SURFACES` is spelled with a trailing
    slash, so a caller holding a slash-less directory path had to append one to
    get a true answer. That was `_map_entries_describing_live_paths`' job for
    one revision — it called this twice, once with `path` and once with
    `path + "/"` — which is a caller routing around its own predicate. The
    parser already knows; it passes what it knows.
    """
    if is_dir and not path.endswith("/"):
        path += "/"
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
        # `sprint.md`'s — which is a widened gate nobody decided to widen.
        #
        # NO COUNT OF THE ENTRIES IS STATED HERE, and the omission is the point:
        # the sentence that used to end this comment counted them, was wrong
        # three times inside one PR (5, then a reviewer's "correction" to 4,
        # against a truth of 6), and the argument needs no arithmetic. The
        # file-versus-directory split is now ASSERTED, per entry, by
        # `test_the_exemption_semantics_hold_for_EVERY_declared_surface` below.
        if path == prefix or (prefix.endswith("/") and path.startswith(prefix)):
            return reason
    return None


def _prefix_path(prefix: str) -> Path:
    """A RECORD_SURFACES key resolved against whichever root holds it."""
    for root in _ROOTS:
        if (root / prefix).exists():
            return root / prefix
    return _REPO / prefix          # absent: the staleness test below says so


def _tracked() -> list[tuple[Path, str]]:
    """Every tracked file in both roots, as (absolute path, repo-relative)."""
    out: list[tuple[Path, str]] = []
    for root in _ROOTS:
        listing = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            capture_output=True, text=True, check=True,
        ).stdout.split("\n")
        out.extend((root / line, line) for line in listing if line)
    return out


def _normalised(path: Path) -> str:
    """The file as ONE line, which is what makes a wrapped label visible.

    This is the whole point of the module: the sweep this gate backstops read
    the tree line by line, and the one survivor it missed was a label split
    across a newline by ordinary paragraph wrapping.

    IT COLLAPSED WHITESPACE AND NOTHING ELSE, WHICH MADE THE HEADLINE CLAIM
    TRUE OF PROSE AND FALSE OF CODE. `_joinable` below already diagnosed this
    for `docs/file_structure.txt` — *"that claim was only ever true of PROSE,
    where wrapping inserts whitespace and nothing else"* — and then the fix was
    applied only inside `_map_entries`, so exactly one file in the tree got it.
    Every other file came through here, where a label wrapped across two
    COMMENTED or QUOTED lines still joined as `# THE KIND # 1 ADDRESS`, and
    `RETIRED_LABEL`'s separator class is `[ _-]`, which contains neither `#`
    nor `>`. Measured on this module's own functions before the fix: of five
    wrapped fixtures, the Python comment, the shell comment and the blockquote
    were BLIND; only the markdown list continuation and plain prose were seen.

    That is the largest population this gate sweeps, not a hypothetical: two of
    the five spellings that actually shipped in this repo lived in Python — a
    `#` comment and an identifier — and both were found by a later pass.

    So the decoration stripping is applied here, per line, by CALLING
    `_joinable` rather than by typing a second regex. One definition, so the
    two cannot drift — this module's own back-pointer discipline, and the same
    reason `_is_record` is the single predicate both consumers ask.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    return re.sub(r"\s+", " ", " ".join(_joinable(line) for line in text.splitlines()))


def _joinable(line: str) -> str:
    """A continuation line with its comment marker removed, ready to be joined.

    THE DECORATION IS NOT WHITESPACE, AND THAT DEFEATED THE JOIN. A continuation
    line opens with the tree's vertical glyphs and then a `#` comment marker, so
    joining one to its leaf produced `... The retired Kind │   │   #   1/2/3 ...`
    — and `RETIRED_LABEL`'s separator class is `[ _-]`, which contains neither
    `│` nor `#`. A label wrapped **inside this file** therefore stayed invisible
    even after the joining was added, in the one file whose handling this module
    singles out, while the module's headline claim is that normalising
    whitespace makes a wrapped label visible.

    That claim was only ever true of PROSE, where wrapping inserts whitespace
    and nothing else. It was FOUND BY MUTATION, not by reading: wrapping every
    labelled map line left the gate green both before and after the joining fix,
    which is the signature of a fixture the instrument cannot reach rather than
    of a guard that discriminates. Reading the code would not have shown it —
    the joining looks obviously correct, and it is, for the wrong file.

    `>` IS IN THE CLASS BECAUSE THIS IS NOW THE WHOLE TREE'S JOINER, not just
    the map's. `_normalised` calls it for every tracked file, so the decoration
    it must strip is whatever a line in this repo opens with: the map's tree
    glyphs, a `#` comment marker in Python, shell, YAML and markdown headings,
    and a `>` blockquote marker in markdown — which is how a wrapped label
    inside quoted evidence stayed invisible. The class is line-LEADING only, by
    design: a `#` in the middle of a line is content, and stripping there would
    invent joins the renderer never makes.
    """
    return re.sub(r"^[│├└─>\s]*#*\s*", "", line)


class _Entry(NamedTuple):
    """One map entry, carrying what the parser knew rather than a re-derivation.

    `is_dir` is read off the map's own trailing slash at parse time. It exists
    because `path` cannot carry it: the path is composed by joining stack
    segments that have had their slashes stripped, so a consumer receiving only
    `path` has to guess a directory back by string surgery — which is exactly
    what `_map_entries_describing_live_paths` used to do.
    """

    lines: list[int]
    text: str
    path: str
    is_dir: bool


def _map_entries() -> list[_Entry]:
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
    entries: list[_Entry] = []
    for number, line in enumerate(_MAP.read_text(encoding="utf-8").splitlines(), 1):
        leaf = _LEAF.match(line)
        if not leaf:
            # A CONTINUATION LINE CARRIES THE TREE'S VERTICAL GLYPH; A TRAILER
            # LINE DOES NOT, and the difference is load-bearing rather than
            # cosmetic. The map ends with 27 lines that are not tree lines at
            # all — the `---`, the symlink-strategy legend, the machine-local
            # list. Attaching them to `entries[-1]` gave them the exemption
            # status of whichever leaf happened to be last, which is live today
            # only by luck: reorder the tree so the final leaf sits under
            # `docs/development/memory-management-framework/` and the whole
            # trailer silently becomes a record surface. So the trailer gets its
            # OWN entry, with no path, and the rule below is that a pathless
            # entry is LIVE — never dropped, which would exempt it by omission.
            if "│" in line:
                if entries and entries[-1].path:
                    head = entries[-1]
                    entries[-1] = head._replace(
                        lines=[*head.lines, number],
                        text=f"{head.text} {_joinable(line)}",
                    )
                    continue
            if entries and not entries[-1].path:
                tail = entries[-1]
                entries[-1] = tail._replace(
                    lines=[*tail.lines, number],
                    text=f"{tail.text} {_joinable(line)}",
                )
            elif line.strip():
                entries.append(_Entry([number], line, "", False))
            continue
        prefix, name = leaf.groups()
        level = len(prefix) // _MAP_INDENT
        stack[level] = name.rstrip("/")
        for deeper in [k for k in stack if k > level]:
            del stack[deeper]
        # The root line (`claude-dot-files/`) carries no `──` and is therefore
        # not a level, which is what makes the reconstruction repo-relative.
        entries.append(_Entry(
            [number], line,
            "/".join(stack[k] for k in sorted(stack)),
            name.endswith("/"),
        ))
    return entries


def _map_entries_describing_live_paths() -> list[_Entry]:
    """The entries this gate must read: everything that is not a record surface.

    A PATHLESS ENTRY IS LIVE. The map's trailer resolves to no tree path, and
    the predicate for "not a record" has to return True for it — dropping it
    would exempt 27 lines of the authoritative map by omission, which is the
    quietest possible way to widen a gate.
    """
    return [
        entry for entry in _map_entries()
        if not (entry.path and _is_record(entry.path, is_dir=entry.is_dir))
    ]


def test_no_live_surface_carries_a_retired_taxonomy_label() -> None:
    """The sweep's claim, re-derived with an instrument the sweep did not use.

    A hit here is not a style nit. The labels were retired because they name
    nothing a reader can act on, and a live document that keeps one hands the
    next author two vocabularies for one thing with no way to tell whether they
    denote the same record.
    """
    require_planning_corpus()
    offenders = []
    for absolute, relative in _tracked():
        # THIS MODULE'S OWN EXEMPTION IS ITS `RECORD_SURFACES` ENTRY AND NOTHING
        # ELSE. It used to also carry `relative.endswith(Path(__file__).name)`,
        # a second, path-blind exemption: move this module and the declared
        # entry goes stale loudly (its own staleness test) while the `endswith`
        # keeps exempting it silently — and any same-named file anywhere in the
        # tree inherits it. One declaration, and it is the reviewed one.
        if _is_record(relative):
            continue
        if relative == "docs/file_structure.txt":
            continue        # scoped by line, in its own test below
        try:
            text = _normalised(absolute)
        except (OSError, UnicodeDecodeError):
            continue        # binary or unreadable; nothing to read a label in
        found = sorted({m.group(0) for m in RETIRED_LABEL.finditer(text)})
        if found:
            offenders.append(f"{relative} — {found}")
    assert not offenders, (
        "a LIVE surface still carries a retired memory-taxonomy label: "
        + "; ".join(offenders)
        + ". Rename it to the name `persistent-memory-protocol/roadmap.md` "
          "§ Reading the old names maps it to — the working record / the typed "
          "exit record / measurement samples. If your case is none of those, "
          "read § The four kinds of record instead: it declares FOUR classes "
          "(invocation state, the working record, the journal, measurement "
          "samples) and the typed exit record is invocation state's one "
          "contracted member, not a class. Or, if this surface is a RECORD of "
          "what was written at the time, add it to RECORD_SURFACES in this "
          "module WITH the reason it is one."
    )


def test_the_file_structure_map_is_scoped_by_LINE_and_not_exempted_whole() -> None:
    """The map describes live surfaces and retired ones in one file.

    Allowlisting it whole would blind this gate to the exact defect the sweep
    had to fix in it — three entries describing LIVE surfaces (`memory-model.md`,
    `exit_record.py`, the one-declaration gates) by the retired labels — while
    the three lines annotating the retired component's own docs must keep them.
    """
    # An entry spans up to fourteen lines, so reporting `lines[0]` sends the
    # reader to a leaf that may carry no label at all. Report the first line
    # that actually matches, and fall back to the leaf only for a label the
    # joining recovered because it was WRAPPED across two lines — which no
    # single raw line contains, and which is the case this module exists for.
    raw = _MAP.read_text(encoding="utf-8").splitlines()
    offenders = [
        f"{_MAP.name}:"
        f"{next((n for n in entry.lines if RETIRED_LABEL.search(raw[n - 1])), entry.lines[0])}"
        f" ({entry.path or '<the map trailer — no tree path>'}) — "
        f"{sorted({m.group(0) for m in RETIRED_LABEL.finditer(entry.text)})}"
        for entry in _map_entries_describing_live_paths()
        if RETIRED_LABEL.search(entry.text)
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

    If `_map_entries_describing_live_paths` silently returned every line, the
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

    BOTH SETS ARE DERIVED FROM `_map_entries`, per the representation rule in
    the module docstring. `labelled` was built by scanning RAW LINES for one
    revision, so the two sides of the subtraction below were a line-granular
    set and an entry-granular one — and a label wrapped across two lines is
    invisible to the raw side, which is the exact blindness this module was
    written to close. Nothing red would have said so: `labelled` merely
    shrinks, and if it empties the assertion below fires with a message
    instructing the reader to DELETE this test and its sibling.
    """
    entries = _map_entries()
    live = {
        number
        for entry in _map_entries_describing_live_paths()
        for number in entry.lines
    }
    assert live, "the map parse produced no live lines — it read nothing"
    labelled = {
        number
        for entry in entries
        if RETIRED_LABEL.search(entry.text)
        for number in entry.lines
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
    require_planning_corpus()
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
    require_planning_corpus()
    stale = []
    for prefix, reason in RECORD_SURFACES.items():
        target = _prefix_path(prefix)
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


def test_a_label_WRAPPED_inside_the_map_is_still_seen() -> None:
    """The module's headline claim, checked on the map rather than on prose.

    `_normalised` makes a wrapped label visible in an ordinary file because
    wrapping there inserts whitespace and nothing else. THE MAP IS NOT AN
    ORDINARY FILE: its continuation lines open with tree glyphs and a `#`, so
    joining a leaf to its continuation used to produce `Kind │  #  2` — which
    `RETIRED_LABEL` does not match, because its separator class is `[ _-]`.

    So the one file this module singles out for careful handling was the one
    file the joining did not actually reach, and every other test here was
    green. Found by mutation, and this is the guard that keeps it found: strip
    `_joinable`'s decoration handling and this goes red on its own, without
    needing a real label to be wrapped in the live map first.
    """
    leaf = "│   │       ├── memory-model.md                      # the Kind"
    continuation = "│   │       │                                        #   2 seam"
    joined = f"{leaf} {_joinable(continuation)}"
    assert RETIRED_LABEL.search(joined), (
        f"a label wrapped across two MAP lines is invisible to the joined "
        f"text: {joined!r}. `_joinable` no longer strips the tree glyphs and "
        f"the `#` comment marker, so the two halves of the label are separated "
        f"by decoration rather than by whitespace — which is the blindness "
        f"this module's whole premise is that it does not have."
    )


@pytest.mark.parametrize(("decoration", "wrapped"), [
    ("a Python comment",       "# THE KIND\n# 1 ADDRESS\n"),
    ("a shell comment",        "# the Kind\n# 2 record\n"),
    ("a markdown blockquote",  "> the retired Kind\n> 3 label\n"),
    ("a markdown list",        "- the Kind\n  1 record\n"),
    ("nothing — plain prose",  "the Kind\n1 record\n"),
])
def test_a_label_wrapped_across_two_DECORATED_lines_is_still_seen(
    tmp_path: Path, decoration: str, wrapped: str,
) -> None:
    """The headline claim, on the corpus the gate actually sweeps.

    Its sibling above holds this for `docs/file_structure.txt`, which is one
    file. THIS HOLDS IT FOR EVERY OTHER FILE, and the split is the defect: the
    decoration handling lived only inside `_map_entries`, so the map got it and
    the tree did not. Measured before the fix, on these exact five fixtures —
    the first three were BLIND and the last two were seen, which is why the two
    that were seen are parametrized here too. A fix that closes the comment
    cases while regressing plain prose would be a trade, not a fix, and the
    only thing that says so is keeping the working cases in the same table.

    The Python and shell cases are not hypothetical shapes. `# THE KIND 1
    ADDRESS` in a code comment is one of the five spellings that really
    survived a sweep in this repo, and Python is the largest body of text this
    gate reads.
    """
    probe = tmp_path / "probe.md"
    probe.write_text(wrapped, encoding="utf-8")
    assert RETIRED_LABEL.search(_normalised(probe)), (
        f"a retired label wrapped across two lines decorated by {decoration} is "
        f"invisible to `_normalised`: {wrapped!r} normalises to "
        f"{_normalised(probe)!r}. Collapsing whitespace is not enough — the "
        f"decoration is not whitespace, and `RETIRED_LABEL`'s separator class "
        f"is `[ _-]`, which contains neither `#` nor `>`. `_normalised` must "
        f"strip line-leading decoration via `_joinable` before it joins."
    )


def test_a_label_split_MID_WORD_is_the_residual_and_is_NOT_seen(
    tmp_path: Path,
) -> None:
    """The stated limit, held as a claim that can go red.

    A `WHAT THIS GATE DOES NOT LOOK AT` list is only worth something while it
    is TRUE — a residual that quietly stops being a residual leaves the list
    overstating the gap, which is the same failure as understating it. So the
    mid-word split is asserted invisible rather than described as invisible.

    IF THIS GOES RED, NOTHING IS BROKEN: somebody widened the gate past what
    the docstring admits. Delete this test and the bullet it holds, in the same
    commit, so the limits list keeps matching the instrument.
    """
    probe = tmp_path / "probe.md"
    probe.write_text("the Ki\nnd 1 record\n", encoding="utf-8")
    assert not RETIRED_LABEL.search(_normalised(probe)), (
        "a label split MID-WORD is now visible to `_normalised`. That is an "
        "improvement, not a failure — but the module docstring still lists it "
        "under WHAT THIS GATE DOES NOT LOOK AT. Update the list and delete "
        "this test together."
    )


@pytest.mark.parametrize(("marker", "wrapped"), [
    ("//   — C, C++, Go, JS",   "// the Kind\n// 1 record\n"),
    ("/* * — a C block comment", "/* the Kind\n * 1 record\n"),
    ("--   — SQL, Lua, Haskell", "-- the Kind\n-- 1 record\n"),
    (";    — ini, Lisp, asm",    "; the Kind\n; 1 record\n"),
    ("<!-- — HTML and markdown", "<!-- the Kind\n<!-- 1 record\n"),
    ("*    — an asterisk bullet", "* the Kind\n* 1 record\n"),
])
def test_the_UNSTRIPPED_MARKERS_are_the_residual_and_are_NOT_seen(
    tmp_path: Path, marker: str, wrapped: str,
) -> None:
    """The OTHER residual bullet, held to the same contract as the mid-word one.

    THE PASS THAT ADDED BOTH BULLETS TESTED ONLY ONE OF THEM. The mid-word
    split got `test_a_label_split_MID_WORD_is_the_residual_and_is_NOT_seen`
    with the module's own stated reason — *"a residual that quietly stops being
    a residual leaves the list overstating the gap"* — and the six-marker
    bullet immediately above it got a sentence. Two reviewers found that
    asymmetry independently, which is the evidence that a prose-only claim in
    this file is the shape that drifts: in the same pass, one such claim about
    `ends_the_table` in the sibling module turned out to be factually
    BACKWARDS and had gone a full review round undetected.

    So each marker the bullet names is asserted invisible here. These are not
    hypothetical shapes — `//` is the whole JS/Go family, `--` is SQL, and the
    repo already tracks `.sql`-adjacent and HTML-commented prose.

    IF ANY CASE GOES RED, NOTHING IS BROKEN: somebody taught `_joinable` that
    marker. Remove it from the bullet and from this parametrize list, in the
    same commit, so the limits list keeps matching the instrument.
    """
    probe = tmp_path / "probe.md"
    probe.write_text(wrapped, encoding="utf-8")
    assert not RETIRED_LABEL.search(_normalised(probe)), (
        f"`_joinable` now strips {marker.split(' ')[0]!r}, so a label wrapped "
        f"across two lines decorated by it is visible: {wrapped!r} normalises "
        f"to {_normalised(probe)!r}. That is an improvement, not a failure — "
        f"but the module docstring still lists this marker under WHAT THIS GATE "
        f"DOES NOT LOOK AT. Update the bullet and this parametrize list together."
    )


def test_the_exemption_semantics_hold_for_EVERY_declared_surface() -> None:
    """The blast radius of each entry, ASSERTED rather than described.

    THIS TEST IS WHAT THE DELETED COUNT WAS TRYING TO BE. `_is_record` used to
    carry a comment explaining that file entries match exactly and directory
    entries match by prefix, and it ended by counting how many of each there
    were. The count was wrong three separate times inside one PR, in a module
    whose entire thesis is that hand-verification does not converge. A count is
    the one thing a guard cannot check about itself; the SEMANTICS it stands in
    for are checkable, so they are checked here and no number is stated
    anywhere. Every entry added from now on is covered whatever shape it has.

    ONE NOTATION, ONE MEANING, ARBITRATED BY DISK. The first assertion is the
    load-bearing one: a directory key must be spelled with a trailing slash.
    Drop it and the two consumers of `RECORD_SURFACES` disagree in the worst
    possible way — the staleness test above `rglob`s the real directory and
    goes green, while `_is_record` exempts nothing under it, so the main sweep
    reds every file beneath and tells the operator to add an entry that is
    already there. The natural resolutions to that contradiction are a
    duplicate entry or widening `_is_record`.

    WHAT THIS DOES NOT REACH: whether a surface DESERVES its exemption (the
    module docstring already rules that out of scope), and whether an entry's
    stated reason is true. It proves the mechanism, never the judgement.
    """
    require_planning_corpus()
    wrong_notation = [
        f"{prefix!r} (is_dir={_prefix_path(prefix).is_dir()}, "
        f"spelled {'with' if prefix.endswith('/') else 'without'} a trailing slash)"
        for prefix in RECORD_SURFACES
        if _prefix_path(prefix).is_dir() != prefix.endswith("/")
    ]
    assert not wrong_notation, (
        "a RECORD_SURFACES key's trailing slash disagrees with what is on "
        "disk: " + "; ".join(wrong_notation)
        + ". A directory key MUST end in `/` and a file key MUST NOT — "
          "`_is_record` reads the slash while the staleness test above reads "
          "the filesystem, so a mismatch makes one of them silently wrong."
    )

    nested = [
        f"{inner!r} is unreachable behind {outer!r}"
        for outer in RECORD_SURFACES if outer.endswith("/")
        for inner in RECORD_SURFACES
        if inner != outer and inner.startswith(outer)
    ]
    assert not nested, (
        "one RECORD_SURFACES entry is nested inside another: " + "; ".join(nested)
        + ". The outer entry answers first, so the inner one's stated reason "
          "stops being why anything is exempt while its staleness check keeps "
          "passing — a reason nobody can falsify is worse than no reason."
    )

    for prefix in RECORD_SURFACES:
        if prefix.endswith("/"):
            assert _is_record(prefix + "probe.md"), (
                f"the directory entry {prefix!r} does not exempt a file beneath "
                f"it — the prefix match is broken and every record under it is "
                f"about to be reported as a live surface"
            )
            sibling = prefix.rstrip("/") + "-x/probe.md"
            assert _is_record(sibling) is None, (
                f"the directory entry {prefix!r} exempts {sibling!r}, a "
                f"DIFFERENT directory that merely begins with its name"
            )
        else:
            assert _is_record(prefix), (
                f"the file entry {prefix!r} does not exempt itself"
            )
            assert _is_record(prefix + ".bak") is None, (
                f"the file entry {prefix!r} exempts {prefix + '.bak'!r}. This "
                f"is the widened gate the exact-match rule exists to prevent: "
                f"a bare `startswith` hands a listed filename's exemption to "
                f"every path that merely begins with it"
            )
            assert _is_record(prefix + "/child.md") is None, (
                f"the file entry {prefix!r} exempts a path BENEATH it, so it "
                f"is behaving as a directory entry"
            )


@pytest.mark.parametrize(("path", "exempt"), [
    ("scripts/workflows/build.sh", True),                    # frozen, top level
    ("scripts/workflows/children/review-pr.sh", True),       # frozen, children/
    ("scripts/workflows/activities/run-claude.sh", False),   # LIVE — the V2 dispatcher
    ("scripts/workflows/temporal/anything.sh", False),       # LIVE V2 tree
    ("scripts/workflows/children/deeper/x.sh", False),       # no such tier exists
    ("scripts/workflows/build.py", False),                   # rule is `.sh` only
])
def test_the_FROZEN_BASH_bound_is_exactly_two_tiers_deep(
    path: str, exempt: bool
) -> None:
    """The widest exemption in this module, and nothing else asserts it.

    `_FROZEN_BASH` is deliberately kept out of the observation-checked loop
    above — it is exempt by RULE, and it carries no retired label today, so an
    entry there would go red for exempting nothing and the only remedies would
    be deleting the exemption or editing a file `personal-tooling.md` forbids
    editing. That decision leaves this branch of `_is_record` with no coverage
    at all, and it is the branch a careless simplification widens furthest.

    THE BOUND IS TWO THINGS AND BOTH MATTER: the `.sh` suffix, and *no deeper
    path segment*. Relax the second to a bare `startswith` and `.sh` files under
    any future subdirectory drop out of the sweep unexamined.

    `activities/` IS LISTED, AND THIS CORRECTS AN EARLIER READING OF IT AS LIVE.
    Measured before changing it: every caller of
    `scripts/workflows/activities/run-claude.sh` is a bash-fleet script, and
    nothing in the Python tree executes it — `assistant_activities.py` replaced
    it and refers to it only in comments. So it is frozen in FACT, and
    `personal-tooling.md`'s list simply predates the activities extraction.
    Sweeping it forced an edit to a file that rule forbids editing, which is how
    the stale enumeration surfaced at all. Note also that a trailing `/` means something different here than it
    does in `RECORD_SURFACES`: there it is *everything beneath*, here it is
    *direct `.sh` children only*, which is why `children/` must be listed
    separately even though it already begins with the first entry.
    """
    assert (_is_record(path) is not None) is exempt, (
        f"_is_record({path!r}) is "
        f"{'exempt' if _is_record(path) else 'live'}; expected "
        f"{'exempt' if exempt else 'live'}"
    )


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
