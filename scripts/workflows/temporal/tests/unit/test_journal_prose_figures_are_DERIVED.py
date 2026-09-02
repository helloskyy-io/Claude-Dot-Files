"""Every count this package's prose rests on is DERIVED, not remembered.

WHY THIS FILE EXISTS, AS THE MEASUREMENT RATHER THAN AS A PRINCIPLE. This
package is roughly half prose, and its prose keeps being wrong about the tree it
describes. Four separate instances, each found by a different reader, none found
by the pass that wrote it:

  * three docstrings said "six of eleven … more than half the fleet" when the
    count was five, and survived three review passes;
  * two documents said "eight entrypoints return from their dry-run branch" when
    only SEVEN of the eleven entrypoints have a `--dry-run` at all;
  * the repo map called the bag's states "open/sealed/pruned", and `pruned` is
    not a word this design uses anywhere — the third state is `redacted`;
  * the PR body explained a measured figure with a cause that measurement
    contradicted.

Each was corrected by hand and the next reader found the next one. THAT is the
signal: the failure is not that someone miscounted, it is that a count can be
written here with nothing on the other end of it. `test_the_worktree_cutting_
count_this_argument_RESTS_ON` pinned the first instance and the second one was
three lines above it, unguarded, in the same docstring.

SO THE CHECK KEYS ON THE CLASS: a figure about the entrypoint population, or an
enumeration of the bag's states, must be BOUND to something that computes it —
or DECLARED, with the reason it is not derivable. An unregistered figure fails.
That is the same escape-hatch shape `test_journal_containment.py` and
`test_journal_state_is_derived_in_one_place.py` already use for path joins and
state derivations: the author who writes a new figure is told to bind it, rather
than a later reader being told they were misled.

⚠ WHAT THIS DOES NOT COVER, because a sweep is only as good as its predicate:

  * IT SEES TWO SURFACE FORMS — `<N> entrypoint(s)` and `<N> of [the] <total>`,
    where `<total>` is itself derived — in the files listed in `_PROSE` below.
    A figure written as "over half of them" or "most of the fleet" is invisible,
    and so is one in a file outside that list. Both scopes are printed in the
    failure text so a reader hitting this learns the boundary.
  * IT BINDS A NUMBER TO A DERIVER BY QUOTING THE SENTENCE. If the sentence is
    reworded, the binding lapses and the figure is reported as unregistered —
    which is the intended direction of failure, and the reason the registry is
    keyed by source text rather than by line number.
  * IT CHECKS THAT A FIGURE IS TRUE, NOT THAT A CLAIM IS. "Ten entrypoints do X"
    is verified as a count; whether X is the right property to care about is a
    review question this cannot reach.
  * IT CANNOT REACH A CAUSAL CLAIM AT ALL. "The tenth entered the swept set when
    the rule was made total" has no ground truth in the tree — only "what" is
    derivable, never "why". That sub-class stays a review-discipline problem and
    this file deliberately does not pretend to cover it.
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
TEMPORAL = REPO_ROOT / "scripts" / "workflows" / "temporal"

sys.path.insert(0, str(TEMPORAL))
sys.path.insert(0, str(TEMPORAL / "tests"))

from planning_corpus import PLANNING_ROOT  # noqa: E402

# THE ENTRYPOINT POPULATION IS IMPORTED, NOT RE-DERIVED. A second copy of
# "which files are the parents" in this file would be the very defect the file
# exists to catch, one layer up — and it comes from the shared helper rather
# than from `test_every_parent_opens_a_run_bag` directly, because a test module
# importing a test module is a coupling with no declared owner that resolves
# only under pytest's default import mode (`test_test_tree_hygiene`).
from journal_entrypoint_facts import (ENTRYPOINTS_DIR,  # noqa: E402
                                      ORDERING_UNCOVERED as _ORDERING_UNCOVERED,
                                      entrypoints as _entrypoints,
                                      side_effect_lines as _side_effect_lines)

# The prose this package owns. `docs/file_structure.txt` is in scope because the
# map is what CLAUDE.md tells a reader to trust, and its journal annotations
# restate figures owned here — which is exactly where `pruned` got in.
_PROSE = (
    sorted((TEMPORAL / "modules" / "journal").glob("*.py"))
    + [TEMPORAL / "scripts" / "validate_bag.py",
       TEMPORAL / "scripts" / "verify_citations.py",
       TEMPORAL / "tests" / "conftest.py"]
    # THIS FILE IS EXCLUDED FROM ITS OWN SWEEP, and the reason is not
    # convenience: its negative controls QUOTE the defective prose verbatim, so
    # a sweep including it would report its own fixtures forever and the only
    # way to keep it green would be to stop quoting the thing that shipped.
    + sorted(p for p in (TEMPORAL / "tests" / "unit").glob("test_journal_*.py")
             if p.name != pathlib.Path(__file__).name)
    # `journal_entrypoint_facts.py` CARRIES FIGURES AND WAS NOT SWEPT. The
    # extraction that created it moved registered figures out of the modules
    # above and into it, leaving the guard green, the claim false and the
    # registry entries dead — the exact shape this module exists to catch,
    # committed by the pass that shipped the module. A file that states a figure
    # is prose regardless of whether it holds tests.
    + [TEMPORAL / "tests" / "unit" / "journal_entrypoint_facts.py",
       TEMPORAL / "tests" / "unit" / "test_every_parent_opens_a_run_bag.py",
       TEMPORAL / "tests" / "unit" / "test_the_suite_never_writes_to_the_operators_journal.py",
       TEMPORAL / "tests" / "integration" / "test_a_real_bag_validates.py",
       # ⚠ PHASE 2's SEVEN FILES, NAMED EXPLICITLY BECAUSE THE GLOB ABOVE
       # MISSES ALL OF THEM. The unit glob is `test_journal_*.py` and the new
       # tests are `test_content_store.py`, `test_citations.py`, and so on — so
       # a population figure or a state enumeration written into any of them
       # was invisible and the guard stayed green. That is the SAME gap this
       # file already records against `journal_entrypoint_facts.py` two
       # comments up, recurring one phase later because the remedy was a list
       # of names rather than a rule about which files hold prose.
       TEMPORAL / "tests" / "unit" / "test_content_store.py",
       TEMPORAL / "tests" / "unit" / "test_citations.py",
       TEMPORAL / "tests" / "unit" / "test_content_activities.py",
       TEMPORAL / "tests" / "unit" / "test_source_fetch.py",
       TEMPORAL / "tests" / "unit" / "test_verify_citations.py",
       TEMPORAL / "tests" / "integration" / "test_citations_verify_offline.py",
       PLANNING_ROOT / "development" / "edge-assistant" / "persistent-memory-protocol" / "phase2_content_store.md",
       PLANNING_ROOT / "development" / "edge-assistant" / "persistent-memory-protocol" / "phase1_the_run_bag.md",
       REPO_ROOT / "docs" / "file_structure.txt"]
)

# Shared with `test_promotion_guard_prose_figures_are_DERIVED`. The two
# sweeps each carried their own copy and the copies had already diverged —
# this one stopped at `twelve`, so a figure written "thirteen entrypoints"
# was invisible to it rather than merely unregistered. That is this file's
# own defect class, in its own supporting data.
from prose_number_words import NUMBER_WORDS as _NUMBER_WORDS  # noqa: E402

import sys as _cg_sys  # noqa: E402
from pathlib import Path as _cg_Path  # noqa: E402
_cg_sys.path.insert(0, str(_cg_Path(__file__).resolve().parents[5]
                           / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import require_planning_corpus  # noqa: E402

_WORD_OF = {v: k for k, v in _NUMBER_WORDS.items()}


# --- the derivers: each computes one figure from the tree ------------------------

def _entrypoint_sources() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in _entrypoints(ENTRYPOINTS_DIR)}


def _total() -> int:
    return len(_entrypoint_sources())


def _cut_their_own_worktree() -> int:
    return sum("act.worktree_add(" in src for src in _entrypoint_sources().values())


def _reach_a_worktree() -> int:
    """Cut one themselves, or hand off by name to a module that does."""
    total = 0
    for name, src in _entrypoint_sources().items():
        if "act.worktree_add(" in src or _side_effect_lines(ast.parse(src)):
            total += 1
    return total


def _dry_run_and_bag_lines(src: str) -> tuple[int | None, int | None]:
    """The first `dry_run` reference and the first `open_run_bag` CALL, by AST.

    ⚠ READ FROM THE SYNTAX TREE, AND READ FROM RAW TEXT UNTIL 2026-09-02, WHEN A
    DOCSTRING INVERTED IT. The old form took the first LINE mentioning each
    string. `run_build_draft.py` carries this phase's family ruling in its module
    docstring, which names `journal.open_run_bag(...)` at line 33 while the file's
    real call is at line 172 — so the runner was counted as NOT returning from
    its dry-run branch before bag-open, which is the opposite of what it does.
    The count would have shipped one low with a green suite, in a guard whose
    entire purpose is that a stated count is true.

    A `dry_run` REFERENCE, not a mention: a `Name` or an `Attribute` the code
    actually reads. A docstring is an `ast.Constant` and contributes nothing.
    """
    tree = ast.parse(src)
    dry = [n.lineno for n in ast.walk(tree)
           if (isinstance(n, ast.Name) and n.id == "dry_run")
           or (isinstance(n, ast.Attribute) and n.attr == "dry_run")]
    bag = [n.lineno for n in ast.walk(tree)
           if isinstance(n, ast.Call)
           and getattr(n.func, "attr", getattr(n.func, "id", None)) == "open_run_bag"]
    return (min(dry) if dry else None), (min(bag) if bag else None)


def _return_from_a_dry_run_before_bag_open() -> int:
    """Entrypoints whose `--dry-run` path returns before the bag is opened.

    LINE ORDER IS THE RIGHT INSTRUMENT AND THE WEAK ONE, so it is stated. The
    property the prose claims is "returns before reaching bag-open"; what is
    cheaply computable is "reads `dry_run` above the `open_run_bag` call". The
    two agree on every entrypoint today, and the five that have no `--dry-run`
    at all — which is what made the claimed EIGHT unreachable — are counted
    correctly by either.
    """
    total = 0
    for src in _entrypoint_sources().values():
        dry, bag = _dry_run_and_bag_lines(src)
        if dry is not None and bag is not None and dry < bag:
            total += 1
    return total


def _do_not_catch_OSError() -> int:
    """Entrypoints whose bag-open handler would let a bare `OSError` escape.

    ⚠ IT IS THE HANDLER AROUND THE BAG-OPEN CALL, NOT ANY HANDLER IN THE FILE,
    and getting that wrong is how this deriver first read 9 against a prose
    figure of 10 that was correct. `run_plan_revision.py` catches `OSError` in
    `_read_task_file`, an unrelated helper whose failure has nothing to do with
    the journal — counting it made an entrypoint look protected on a path where
    it is not. The claim the prose makes is about what happens to an exception
    RAISED BY `open_run_bag`, so the derivation follows the exception: the
    `try` whose body reaches that call, and only its handlers.
    """
    total = 0
    for src in _entrypoint_sources().values():
        caught: set[str] = set()
        for node in ast.walk(ast.parse(src)):
            if not isinstance(node, ast.Try):
                continue
            reaches_bag_open = any(
                isinstance(inner, ast.Call)
                and getattr(inner.func, "attr", getattr(inner.func, "id", None))
                == "open_run_bag"
                for statement in node.body for inner in ast.walk(statement))
            if not reaches_bag_open:
                continue
            for handler in node.handlers:
                if handler.type is not None:
                    caught.update(n.id for n in ast.walk(handler.type)
                                  if isinstance(n, ast.Name))
        if "OSError" not in caught:
            total += 1
    return total


def _ordering_uncovered() -> int:
    return len(_ORDERING_UNCOVERED)


def _covered_by_the_ordering_check() -> int:
    """Distinct from `_reach_a_worktree` even though both read 8 today.

    They answer different questions — "how many entrypoints reach a worktree"
    versus "how many the ordering assertion can see" — and binding a sentence
    about coverage to the worktree count would leave the coverage claim silently
    unguarded the day `_ORDERING_UNCOVERED` grows. Two derivers that agree today
    is not one deriver.
    """
    return _total() - _ordering_uncovered()


_DERIVERS = {
    "the entrypoint population": _total,
    "cut their own worktree": _cut_their_own_worktree,
    "reach a worktree before workflow-module code": _reach_a_worktree,
    "return from a dry-run branch before bag-open": _return_from_a_dry_run_before_bag_open,
    "do not catch OSError": _do_not_catch_OSError,
    "outside the ordering check's reach": _ordering_uncovered,
    "inside the ordering check's reach": _covered_by_the_ordering_check,
}

# `(file name, the quoted figure)` → which deriver must produce that number.
# KEYED BY THE FIGURE'S OWN TEXT so an entry survives a line move and LAPSES
# when the sentence is reworded — a reworded claim is a new claim.
_BOUND_FIGURES = {
    # MOVED HERE BY THIS PR'S OWN EXTRACTION, from the two modules above.

    # ── SEVENTEEN-ENTRYPOINT ERA. `Dual-mode children` gave six children runners
    #    of their own on 2026-09-02; every row above it was keyed on a sentence
    #    naming ELEVEN and is gone rather than kept beside its successor, because
    #    this registry's own rule is that a reworded claim is a new claim.
    ("journal_activities.py", "ELEVEN of this fleet's seventeen entrypoints"):
        "cut their own worktree",
    ("journal_activities.py", "fifteen of seventeen"):
        "reach a worktree before workflow-module code",
    ("journal_activities.py", "seventeen entrypoints"): "the entrypoint population",
    ("journal_activities.py", "seventeen entrypoint"): "the entrypoint population",
    ("journal_activities.py", "Sixteen of the seventeen entrypoints"): "do not catch OSError",
    ("conftest.py", "seventeen entrypoints"): "the entrypoint population",
    ("test_journal_bag.py", "seventeen entrypoints"): "the entrypoint population",
    ("test_journal_root.py", "Sixteen of the seventeen entrypoints"): "do not catch OSError",
    ("test_journal_root.py", "sixteen of seventeen entrypoints"): "do not catch OSError",
    ("test_every_parent_opens_a_run_bag.py", "SEVENTEEN entrypoints"):
        "the entrypoint population",
    ("test_every_parent_opens_a_run_bag.py", "ELEVEN of those seventeen"):
        "cut their own worktree",
    ("test_every_parent_opens_a_run_bag.py", "FIFTEEN of the seventeen"):
        "reach a worktree before workflow-module code",
    ("test_every_parent_opens_a_run_bag.py", "Seventeen of the seventeen entrypoints"):
        "return from a dry-run branch before bag-open",
    ("test_every_parent_opens_a_run_bag.py", "fifteen of seventeen"):
        "inside the ordering check's reach",
    ("test_every_parent_opens_a_run_bag.py", "two of the seventeen entrypoints"):
        "outside the ordering check's reach",
    ("test_every_parent_opens_a_run_bag.py", "FIFTEEN of seventeen entrypoints"):
        "reach a worktree before workflow-module code",
    ("test_the_suite_never_writes_to_the_operators_journal.py", "seventeen entrypoints"):
        "the entrypoint population",
    ("journal_entrypoint_facts.py", "15 OF 17"):
        "inside the ordering check's reach",
}

# `(file name, the quoted figure)` → why no deriver can produce it. A figure
# about a state the tree no longer holds, or about a fleet that never existed,
# has no ground truth to check against — and saying so in two lines is what
# stops the exemption being confused with an oversight.
_DECLARED_NON_DERIVATIONS = {
    ("journal_entrypoint_facts.py", "one entrypoint"):
        "NOT A POPULATION FIGURE. It reads 'calls that create something, in one "
        "entrypoint' — the scope of one call to the function, not a count of how "
        "many of the eleven do anything. No deriver could produce it because it "
        "is not a claim about the fleet, and binding it to one would make a "
        "derived number answer a question nobody asked.",
    # ⚠ EIGHT ROWS WERE DELETED FROM THIS REGISTRY ON 2026-09-02 AND THE REASON
    #   IS THE MECHANIC, NOT THE ROWS. `_figures_in`'s second pattern anchors on
    #   the CURRENT total, so a historical `<N> of <old total>` stops matching
    #   the moment the population moves: its row goes dead IN SILENCE, and the
    #   inner `<old total> entrypoints` fragment surfaces as a NEW figure
    #   claiming the old number. Taking the fleet from eleven to seventeen
    #   dissolved every compound at once. Two rows here — `journal_activities`'s
    #   `eleven-entrypoint fleet` and `nine of eleven` — were among them; the
    #   sentence they exempted now names its era ("in the eleven-entrypoint fleet
    #   of 2026-08"), which is readable AND carries no figure for any future
    #   total to dissolve.
    #
    #   THE ROWS WERE FOUND BY `test_no_registry_row_is_STALE`, NOT BY READING.
    #   A review pass reading the diff found two of the eight; the check found
    #   all eight the first time it ran. That is the argument for the check over
    #   a sixth hand correction, and it is the same argument this file already
    #   makes for its own class sweep two comments down.
    ("phase2_content_store.md", "two entry points"):
        "NOT A POPULATION FIGURE, AND THE COLLISION IS IN THE PREDICATE RATHER "
        "THAN IN THE PROSE. Phase 2 requirement 8 reads 'the store's two entry "
        "points' — capture and resolve — which is ordinary English about two "
        "functions, not a count of this fleet's kickoff entrypoints. It matches "
        "because `_figures_in` tolerates `entry\\s?points?`, and every one of "
        "the thirty-five registered figures in this file is written UNSPACED. "
        "Narrowing the pattern to `entrypoints?` would drop the collision "
        "without losing a single real figure — that is a change to a guard's "
        "reach, so it is surfaced for the operator rather than made by a "
        "correction pass, and this row is what keeps the sweep honest until "
        "then. The same collision was hit one module over by the pass that "
        "wrote the store, which reworded its own docstring; a phase doc in "
        "another repository is not this repo's to reword.",
    ("journal_entrypoint_facts.py", "five entrypoints"):
        "HISTORY, AND IT WAS BOUND TO A DERIVER UNTIL 2026-09-02. The sentence "
        "records what the ORDERING CHECK'S FIRST VERSION could see: five of the "
        "eleven-era entrypoints cut their own worktree and the other six had no "
        "detectable side effect. `cut their own worktree` derives 11 today, so "
        "the binding turned a true statement about a past tree into a reported "
        "contradiction — and 'correcting' it to 11 would have left the very next "
        "clause reading 11 + 6 = 11. A figure whose sentence also states its "
        "complement cannot be renumbered one term at a time.",
    ("test_every_parent_opens_a_run_bag.py", "seven entrypoints"):
        "`test_preflight`'s ORIGINAL defect — six of SEVEN, in the "
        "seven-entrypoint era. It is the exemplar this file was built on, and "
        "it is history, not a claim about today's tree.",
    # ⚠ THE ROW THAT WAS HERE IS GONE BECAUSE THE SENTENCE NO LONGER CARRIES A
    #   FIGURE AT ALL. It read "a fleet where ten of eleven entrypoints had
    #   quietly stopped opening bags"; when the population moved to seventeen the
    #   compound stopped matching and the bare fragment `eleven entrypoints`
    #   surfaced as a NEW claim about today's tree. A hypothetical does not need
    #   a number to make its point, so it was reworded to "all but one" — which
    #   is the same claim, immune to the next change, and needs no registry row.
    ("phase1_the_run_bag.md", "11 entrypoints"):
        "PHASE 1'S OWN RECORD, in another repository and about the eleven-"
        "entrypoint fleet it shipped against. The compound forms this file used "
        "to bind — `Seven of the 11 entrypoints`, `9 of the 11 entrypoints` — "
        "stopped matching when `Dual-mode children` took the population to "
        "seventeen, leaving these fragments. It is a dated record of what was "
        "true, not a claim about today, and a phase doc in another repository is "
        "not this repo's to reword — the same reasoning `phase2_content_store.md` "
        "carries below. SURFACED for that component's own doc pass rather than "
        "silently corrected here.",
    ("phase1_the_run_bag.md", "eleven entrypoints"):
        "the same record, in the superseded-measurement note at the foot of that "
        "document. Declared for the same reason.",
    ("file_structure.txt", "eight entrypoints"):
        "a quoted-wrong figure in the map's annotation for this guard: the "
        "`--dry-run` count it was built after. Seven is the derived value and it "
        "is bound, twice, where it is CLAIMED rather than quoted.\n"
        "⚠ IT WAS ONE OF TWO UNTIL 2026-09-02. Its sibling was keyed `six of "
        "eleven` and dissolved when the population moved — see the comment at "
        "the head of this registry. The row's reasoning is unaffected: what "
        "changed is that the annotation's other quoted figure no longer matches "
        "the sweep's pattern at all, so it needs no exemption.",
}

# ⚠ THE ENTRY ABOVE WAS ADDED BECAUSE THIS GUARD CAUGHT ITS OWN AUTHOR,
# in the same sitting, on the map annotation describing the guard itself. That is
# the argument for a class check over a fifth hand correction, delivered by the
# check rather than by this comment — and it is why quoting a wrong figure is a
# DECLARED case rather than an accident: the record of what was wrong has to
# survive, and it must not be mistaken for a claim about the tree.

# The bag's state vocabulary, read from the module that owns it rather than
# retyped here. `lifecycle` carries two values and the two flags are
# independent — which is why "FOUR bag states" was wrong about the SHAPE as
# well as about the names.
_STATE_VOCABULARY = {"open", "sealed", "redacted", "incomplete"}


def _figures_in(text: str) -> list[str]:
    """Every entrypoint-population figure in one file, as its own source text.

    TWO SURFACE FORMS, AND THE SECOND IS BUILT FROM THE DERIVED TOTAL. `<N>
    entrypoints` is the plain shape; `<N> of [the] eleven` is the shape with the
    noun elided, which real sentences here use often enough that omitting it
    would leave the sweep passing vacuously over them. Anchoring the second form
    on the derived total means the pattern follows the tree rather than pinning
    a literal.

    THE NUMBER MUST BIND TO THE NOUN. "five modules reach an entrypoint" is not
    a claim about five entrypoints, so a pattern that allowed arbitrary text
    between the number and the noun would report it and teach an author to
    write vaguer prose to escape the guard.
    """
    number = "|".join(list(_NUMBER_WORDS) + [r"\d{1,3}"])
    total_word = _WORD_OF[_total()]
    patterns = (
        rf"\b({number})\s+(?:of\s+(?:the\s+)?)?entry\s?points?\b",
        rf"\b({number})\s+of\s+(?:[^\d\s]+\s+){{0,3}}?(?:{total_word}|{_total()})"
        rf"(?:\s+entry\s?points?)?\b",
    )
    spans = [(m.start(), m.end(), m.group(0))
             for pattern in patterns
             for m in re.finditer(pattern, text, re.IGNORECASE)]

    # THE LONGEST MATCH AT A POSITION WINS. The two forms overlap — "FIVE of
    # this fleet's eleven entrypoints" contains "eleven entrypoints" — and
    # registering both would make an author bind one sentence twice, which is
    # the busywork that gets a guard deleted. A span wholly inside another is
    # the same claim seen through a narrower window.
    found: list[str] = []
    for start, end, raw in sorted(spans, key=lambda s: (s[0], -s[1])):
        if any(o_start <= start and end <= o_end and (o_start, o_end) != (start, end)
               for o_start, o_end, _ in spans):
            continue
        # WHITESPACE-NORMALISED, so a registry key survives the docstring
        # being re-wrapped. A figure that spans a line break is the common
        # case here, not the exception, and keying on the raw text would
        # lapse every binding the first time a paragraph reflows.
        figure = " ".join(raw.split())
        if figure not in found:
            found.append(figure)
    return found


def _claimed_value(figure: str) -> int:
    head = re.match(r"\s*(\w+)", figure).group(1)
    return _NUMBER_WORDS.get(head.lower(), None) if not head.isdigit() else int(head)


def test_every_entrypoint_figure_in_this_packages_prose_is_BOUND() -> None:
    """The class check: a count with nothing on the other end of it fails here.

    Not "these four numbers are right" — that is what three passes of hand
    correction already delivered, and the fourth reader found a fifth number.
    An author writing a new figure gets told to bind it or declare it, which is
    the only version of this that converges.
    """
    require_planning_corpus()
    unregistered: list[str] = []
    wrong: list[str] = []

    for path in _PROSE:
        text = path.read_text(encoding="utf-8")
        for figure in _figures_in(text):
            key = (path.name, figure)
            if key in _DECLARED_NON_DERIVATIONS:
                continue
            if key not in _BOUND_FIGURES:
                unregistered.append(f"{path.name}: {figure!r}")
                continue
            deriver = _DERIVERS[_BOUND_FIGURES[key]]
            actual, claimed = deriver(), _claimed_value(figure)
            if actual != claimed:
                wrong.append(
                    f"{path.name}: {figure!r} claims {claimed}; "
                    f"{_BOUND_FIGURES[key]!r} derives {actual}")

    assert not wrong, (
        "PROSE STATES A FIGURE THE TREE CONTRADICTS:\n  " + "\n  ".join(wrong) +
        "\n\nCorrect the prose. A count restated beside the code that derives it "
        "is how every previous instance of this drifted.")
    assert not unregistered, (
        "A FIGURE ABOUT THE ENTRYPOINT POPULATION IS NEITHER BOUND NOR DECLARED:\n  "
        + "\n  ".join(unregistered) +
        f"\n\nAdd it to `_BOUND_FIGURES` with the deriver that computes it "
        f"(available: {sorted(_DERIVERS)}), or to `_DECLARED_NON_DERIVATIONS` "
        f"with the reason no deriver can — a historical or hypothetical figure "
        f"has no ground truth in the tree. Swept: {[p.name for p in _PROSE]}.")


def test_the_swept_prose_is_NOT_EMPTY() -> None:
    """A sweep that finds nothing passes exactly like a sweep that finds nothing wrong.

    Every file in `_PROSE` must exist, and the sweep as a whole must find
    figures — a rename or a moved doc that silently emptied the population is
    the failure mode this file could not otherwise report.
    """
    require_planning_corpus()
    missing = [p.as_posix() for p in _PROSE if not p.is_file()]
    assert not missing, f"swept prose file(s) no longer exist: {missing}"

    found = sum(len(_figures_in(p.read_text(encoding="utf-8"))) for p in _PROSE)
    assert found >= 15, (
        f"the sweep found only {found} figures across {len(_PROSE)} files; it "
        f"found 23 when written. A predicate that has stopped matching passes "
        f"vacuously and reports nothing.")


def test_no_prose_enumerates_a_bag_STATE_that_does_not_exist() -> None:
    """`open/sealed/pruned` shipped in the repo map, and `pruned` is not a state.

    Requirement 8's whole argument is that a bag's state is `lifecycle` plus two
    INDEPENDENT flags, and that collapsing them makes a bag that lost data to a
    full disk indistinguishable from one a human deliberately redacted. A map
    entry that names a fourth state, and one drawn from retention vocabulary at
    that, teaches exactly the collapse the requirement forbids — to the reader
    CLAUDE.md sends to that map as ground truth.

    The predicate is narrow on purpose: a slash-joined run of lowercase words on
    a line that mentions a bag state. That is the shape an enumeration takes, and
    a wider one would flag every path and every `open|sealed` alternation in the
    package.
    """
    require_planning_corpus()
    offenders: list[str] = []
    for path in _PROSE:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not re.search(r"bag\s+states?", line, re.IGNORECASE):
                continue
            for run in re.findall(r"\b[a-z]+(?:/[a-z]+)+\b", line):
                unknown = [w for w in run.split("/") if w not in _STATE_VOCABULARY]
                if unknown:
                    offenders.append(f"{path.name}:{number}: {run!r} names {unknown}")

    assert not offenders, (
        "PROSE ENUMERATES A BAG STATE THIS DESIGN DOES NOT HAVE:\n  "
        + "\n  ".join(offenders) +
        f"\n\nThe vocabulary is {sorted(_STATE_VOCABULARY)}: `lifecycle` is "
        f"open|sealed, and `redacted`/`incomplete` are independent flags.")


def test_the_state_sweep_CATCHES_the_word_that_shipped() -> None:
    """The negative control, because a green sweep proves nothing on its own.

    Runs the predicate over the line as it actually shipped in
    `docs/file_structure.txt`, and over a conforming rewrite of the same line.
    """
    shipped = "#   concurrent child, BagIt RFC 8493 manifest. FOUR bag states — open/sealed/pruned"
    conforming = "#   concurrent child, BagIt manifest. Bag state — open/sealed plus two flags"

    def offends(line: str) -> bool:
        if not re.search(r"bag\s+states?", line, re.IGNORECASE):
            return False
        return any(w not in _STATE_VOCABULARY
                   for run in re.findall(r"\b[a-z]+(?:/[a-z]+)+\b", line)
                   for w in run.split("/"))

    assert offends(shipped), "the sweep must flag the line that actually shipped"
    assert not offends(conforming), "a conforming enumeration must not be flagged"


def test_the_figure_sweep_CATCHES_a_wrong_count_and_an_unbound_one() -> None:
    """Two negative controls, one per way this guard can be useless.

    A guard that only ever runs over conforming text is a guard nobody has seen
    fire. The first control is the defect that shipped — a figure bound to a
    deriver that contradicts it. The second is the one the class turns on: a
    NEW figure, correct or not, that nobody bound.
    """
    total_word = _WORD_OF[_total()]

    wrong_shape = f"eight entrypoints return from their dry-run branch"
    figures = _figures_in(wrong_shape)
    assert figures, "the sweep must see the shipped form at all"
    assert _claimed_value(figures[0]) == 8
    assert _return_from_a_dry_run_before_bag_open() != 8, (
        "the deriver must contradict the figure that shipped — if it ever "
        "agrees, this control has stopped controlling anything")

    elided = f"so in eight of {total_word} a bag opened in the workflow module"
    assert _figures_in(elided), (
        "the elided form must be seen; it is how half this package's figures "
        "are written and a sweep blind to it would pass vacuously over them")

    bound_to_nothing = "four entrypoints do something nobody registered"
    figure = _figures_in(bound_to_nothing)[0]
    assert ("nowhere.py", figure) not in _BOUND_FIGURES
    assert ("nowhere.py", figure) not in _DECLARED_NON_DERIVATIONS

    # AND THE NUMBER MUST BIND TO THE NOUN, or the guard teaches vaguer prose.
    assert not _figures_in("five modules reach an entrypoint today"), (
        "a count of MODULES is not a claim about the entrypoint population")


def _rows_matching_no_prose(
        registries: tuple[tuple[dict, str], ...] | None = None) -> list[str]:
    """THE PREDICATE. Every registry key whose figure is no longer in its file.

    THE REGISTRIES ARE A PARAMETER SO THE CONTROL BELOW DRIVES THIS FUNCTION
    ITSELF, and that is not a style choice — it was MEASURED. Written to read
    the two module globals directly, the control had to drive `_figures_in`
    instead, and a mutation replacing this function's comparison with `if False`
    left the whole module GREEN. A control that re-implements the predicate
    stops describing it the moment either one moves, which is the defect
    `test_test_tree_hygiene`'s residual test records at length one directory
    over — committed here by the pass that was fixing this registry.
    """
    by_name = {path.name: path for path in _PROSE}
    stale: list[str] = []
    for registry, label in (registries or ((_BOUND_FIGURES, "_BOUND_FIGURES"),
                                           (_DECLARED_NON_DERIVATIONS,
                                            "_DECLARED_NON_DERIVATIONS"))):
        for name, figure in registry:
            path = by_name.get(name)
            if path is None:
                stale.append(f"{label}: {name!r} is not in `_PROSE` at all")
                continue
            if not path.is_file():
                stale.append(f"{label}: ({name!r}, {figure!r}) — file is gone")
                continue
            if figure not in _figures_in(path.read_text(encoding="utf-8")):
                stale.append(f"{label}: ({name!r}, {figure!r}) matches nothing in {name}")
    return stale


def test_no_registry_row_is_STALE() -> None:
    """A row that binds nothing is a carve-out nobody is using, and it is silent.

    THE OTHER DIRECTION FROM THE SWEEP ABOVE, which asks whether every figure in
    the prose has a row. This asks whether every row still has a figure, and it
    is the half that fails without a symptom: an unmatched key costs nothing to
    have and shows up in no output.

    A DEAD `_DECLARED_NON_DERIVATIONS` ROW IS THE DANGEROUS HALF. It is an
    EXEMPTION keyed on `(file, text)`, so the next figure that happens to take
    the same key is excused from binding without anyone deciding that — the
    guard stays green and the class it protects quietly loses a member.

    MEASURED, AND IT IS WHY THIS EXISTS RATHER THAN TWO DELETED LINES. The pull
    request that moved the entrypoint population from eleven to seventeen
    reworded ~20 sentences and orphaned every row keyed on the old wording, in
    one commit, with nothing reporting it. The run that did it removed the rows
    it noticed and surfaced the missing check as a proposal; a review then found
    two survivors — one of them orphaned by a rewording in the same hunk that
    edited its own reason text. Enumerating dead rows does not converge, because
    every population change dissolves every historical compound at once.

    THE EXEMPLAR IS `test_no_exemption_is_stale` IN
    `test_a_census_guard_proves_its_own_predicate`, one module over, which
    solves the identical problem for that file's grandfather list. This is the
    same rule applied to the registry that had none.

    WHAT THIS DOES NOT LOOK AT: whether a row that DOES match is bound to the
    RIGHT deriver. The sweep above owns that, by recomputing the figure.
    """
    require_planning_corpus()
    stale = _rows_matching_no_prose()
    assert not stale, (
        "REGISTRY ROWS THAT BIND NOTHING:\n  " + "\n  ".join(sorted(stale)) +
        "\n\nDelete them. A row keyed on prose that has been reworded or removed "
        "contributes no coverage, and a dead `_DECLARED_NON_DERIVATIONS` row "
        "silently exempts the next figure that takes the same key.")


def test_THE_STALENESS_CHECK_CATCHES_A_ROW_THAT_BINDS_NOTHING() -> None:
    """CONTROL. The predicate must fire on a dead key and stay quiet on a live one.

    Driven through `_figures_in` on literal text rather than through the
    registries, so the arms are attributable to the row under test and not to
    whatever the tree currently says.
    """
    swept = {path.name for path in _PROSE}
    assert "journal_activities.py" in swept, (
        "the control drives the real sweep against a real swept file; if that "
        "file leaves `_PROSE` the arms below stop meaning anything")

    dead = (({("journal_activities.py", "nine of eleven"): "why"}, "FAKE"),)
    assert len(_rows_matching_no_prose(dead)) == 1, (
        "the predicate must report the dead key that actually shipped — "
        "`nine of eleven` stopped matching when the population moved to "
        "seventeen and the row went on exempting nothing")

    live = (({("journal_activities.py", "seventeen entrypoints"): "why"}, "FAKE"),)
    assert _rows_matching_no_prose(live) == [], (
        "a row keyed on prose that is still there must NOT be reported — a "
        "staleness check that fires on live rows gets its assertion deleted")

    gone = (({("a_file_that_is_not_swept.py", "seventeen entrypoints"): "why"}, "FAKE"),)
    assert len(_rows_matching_no_prose(gone)) == 1, (
        "a row naming a file outside `_PROSE` binds nothing either, and is the "
        "shape a renamed module leaves behind")

    # AND THE REGISTRIES REALLY ARE THE POPULATION. A helper reading an empty
    # dict would report no stale rows forever, which is this file's own class.
    assert len(_BOUND_FIGURES) + len(_DECLARED_NON_DERIVATIONS) >= 15, (
        f"only {len(_BOUND_FIGURES) + len(_DECLARED_NON_DERIVATIONS)} registry "
        f"rows; there were 24 when this control was written. A staleness check "
        f"over an empty registry passes vacuously.")
