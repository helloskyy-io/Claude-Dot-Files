"""A promotion guard may not state a figure about the corpus it guards.

THE CLASS, AND IT IS MEASURED RATHER THAN FEARED. The three modules that police
prompt duplication are mostly prose, and their prose keeps being falsified BY
THE CHANGE THAT SHIPS IT. Five instances, none found by the pass that wrote it:

  * `test_tier_siblings…` claimed "there are 19 near-duplicate pairs" as the
    entire stated evidence for scoping itself to tier siblings. It was 22 when
    written — 19 was the undercount from a length prefilter the same module
    rejects as unsafe — and the next PR's reconciliation moved the truth TO 19,
    so a wrong number became accidentally right and nobody learned anything.
  * `test_promoted_fragments…` banner said "the refine pair's six fragments"
    over a list of eight, left by the commit that added the other two. One pass
    later the same list held eleven.
  * The same module's docstring said "Nine fragments were promoted" while
    `_PROMOTED` held eleven.
  * `test_prompt_blocks…` said "what is left is seven CROSS-FAMILY sets". There
    are eight, and two of them are not cross-family.
  * The same module named three same-named prompts "at 85.8%, 76.1% and 62.1%".
    Two of those three were falsified by promotions in the PR that wrote them.

Each was corrected by hand and the next reader found the next one. THAT is the
signal: the failure is not that someone miscounted, it is that a number can be
written in these files with nothing on the other end of it. This module is the
same escape-hatch shape `test_journal_prose_figures_are_DERIVED` already uses
for the journal package — bind the figure to something that computes it, or
DECLARE it historical with the reason. An unregistered figure fails, so the
author who writes a new one is told to bind it rather than a later reader being
told they were misled.

⚠ WHAT THIS DOES NOT COVER, because a sweep is only as good as its predicate:

  * **IT SEES ONE SURFACE FORM** — an integer or number-word, then up to two
    intervening words, then one of `_NOUNS` (the things this corpus counts:
    pairs, blocks, fragments, sets, entries, consumers, children). A figure
    written as "most of the fleet", "roughly half" or "85.8%" is INVISIBLE, and
    two of the five instances above were of exactly that kind. They were fixed
    by deleting the figure, not by binding it, and this sweep would not catch
    their return.
  * **SPELLED-OUT "one" AND "two" ARE NOT SWEPT** — see `_SWEPT_WORDS`. A real
    corpus figure that happens to equal 1 or 2 and is written as a word gets no
    binding demanded of it.
  * **IT CHECKS THAT A FIGURE IS TRUE, NOT THAT A CLAIM IS.** "Eight sets remain"
    is verified as a count; "and they are all cross-family" is a claim no count
    can reach, and that half is precisely what was wrong in one instance above.
  * **IT SWEEPS `_PROSE` ONLY.** A figure about this corpus written into a PR
    body, a standard, or `docs/file_structure.txt` is out of scope here.
  * **A DECLARED figure is never re-checked.** Declaring is an escape hatch with
    a reason attached, not a proof; a wrong declaration is invisible forever.
  * **THE REGISTRY IS CORPUS-WIDE, NOT PER-FILE.** A key registered for one
    module's prose would also excuse a figure in another module's, if it fell
    inside that figure's window. The keys are long, specific historical quotes
    so a collision is unlikely, but nothing PREVENTS it — this is the same
    "reads a neighbour's evidence" shape `_WINDOW` was added to fix, one level
    out, and it is named here rather than claimed to be absent.
  * **AN INLINE TRAILING COMMENT** (`code  # eleven fragments`) is not swept:
    only lines whose first non-space character is `#` are collected.
"""

from __future__ import annotations

import ast
import pathlib
import re

UNIT = pathlib.Path(__file__).resolve().parent

# THIS MODULE IMPORTS NOTHING FROM THE GUARDS IT SWEEPS, and that is a
# constraint rather than an oversight. `test_test_tree_hygiene` forbids a test
# module importing another — the names are `_`-private, the coupling has no
# declared owner, and it resolves only under pytest's default import mode. The
# first version of this file imported all three guards for its derivers and
# failed that gate. The sweep needs only paths and a regex, so the derivers went
# rather than the rule; see `_BOUND` for where one goes when it is first needed.

# The prose these guards own. A file that STATES a figure is prose whether or
# not it also holds tests — that distinction is what let the journal package's
# figures escape into a helper module and go unswept for a release.
# `fork_vs_parameterize.py` and `assembled_prompt.py` are HELPERS, and that is
# precisely why they are here: the comment above records that a helper module is
# how this corpus's figures escaped the sweep once already, and the first is now
# the corpus's densest prose surface — a normative docstring two of the three
# test modules import.
_PROSE = [
    UNIT / "test_prompt_blocks_are_shared_not_copied.py",
    UNIT / "test_promoted_fragments_render_for_every_consumer.py",
    UNIT / "test_tier_siblings_do_not_DRIFT_by_a_sentence.py",
    UNIT / "fork_vs_parameterize.py",
    UNIT / "assembled_prompt.py",
]

from prose_number_words import NUMBER_WORDS as _NUMBER_WORDS  # noqa: E402

# What this corpus counts. The sweep fires on `<N> <noun>`, so widening this
# tuple widens the guard.
_NOUNS = ("pair", "pairs", "block", "blocks", "fragment", "fragments",
          "set", "sets", "entry", "entries", "consumer", "consumers",
          "child", "children")

# `<N> [adjective…] <noun>`. The intervening slot exists because the first
# version of this regex required adjacency and could not match "19
# near-duplicate pairs" — the very sentence that motivated the module. It is
# capped at two words so the number stays attached to what it counts rather
# than reaching across a clause into an unrelated noun.
# SPELLED-OUT ONE AND TWO ARE NOT SWEPT, and this is a measured narrowing
# rather than a convenience. In English prose they are overwhelmingly
# grammatical, not quantitative — "more than one child", "two blocks differing
# 30% in length" — and sweeping them produced six false positives against three
# real ones on the first run. Every failure this module was built from was 6 or
# larger (6→8, 7→8, 9→11, 19→22). DIGITS are swept at every value, including
# "2 pairs": writing a small number as a digit is deliberate quantification.
_SWEPT_WORDS = tuple(w for w, n in _NUMBER_WORDS.items() if n >= 3)

# `(?<![\d.])` keeps the sweep off the tail of a decimal: without it "0.479
# pair" is read as the figure "479 pair" and demands a binding for a similarity
# ratio.
_FIGURE = re.compile(
    r"(?<![\d.])\b(\d{1,3}|" + "|".join(_SWEPT_WORDS) + r")\s+"
    r"(?:[\w-]+\s+){0,2}"
    r"(" + "|".join(_NOUNS) + r")\b",
    re.IGNORECASE,
)


# --- the registry ----------------------------------------------------------------
#
# Keyed by the SENTENCE FRAGMENT the figure lives in, not by line number: a
# reworded sentence lapses its binding and is reported as unregistered, which is
# the intended direction of failure.

# EMPTY TODAY, AND THAT IS THE FIX RATHER THAN A GAP. Every live figure these
# three guards used to state has been replaced by the shape it was describing
# ("mostly cross-family sets"; "the list's own length is the figure"), because a
# guard's docstring is read far more often than it is re-measured. The registry
# exists for the next author who has a reason to state one — and because a bound
# figure is the only acceptable way to do so. `_stale_bindings` below is driven
# with a synthetic registry so the machinery is exercised while this is empty.
_BOUND: dict[str, callable] = {}

# Figures that are NOT derivable, each with the reason. A declaration is a
# decision, not a shrug — every entry names why the tree cannot answer it.
_DECLARED: dict[str, str] = {
    "over eight entries":
        "quoted DEFECT: the banner this module's own docstring cites as an "
        "instance. A file's own fixtures cannot be swept or it reports them "
        "forever, and the only way to stay green would be to stop quoting the "
        "thing that shipped.",
    "across 61 blocks":
        "historical: the corpus as measured before any promotion, and the "
        "evidence for MIN_BLOCK's value. Nothing in the tree can recompute a "
        "population that no longer exists.",
    "48 -> 13":
        "historical: the before/after of the same change. The `13` half is "
        "live and IS checked, by _baseline_entries via test_a_FIXED_"
        "duplication_is_removed_from_the_baseline next door.",
    "seven one-sided-additive pairs existed":
        "historical: the population the review pass measured before six of them "
        "were reconciled in the same PR. The sentence is explicitly past-tense "
        "and the live count is derived by _one_sided_pairs.",
    "three same-named prompts":
        "quoted DEFECT: the claim that was falsified, cited as the reason the "
        "similarities are no longer restated.",
    "Promoting four blocks out of `stages_1_to_5.md`":
        "historical: what one promotion removed from one file on 2026-08-19, "
        "cited as the reason `assembled_prompt` exists. The blocks are in the "
        "pool now, so no walk of the tree can recount what left that file.",
    "eleven testing rules":
        "historical: what the forked `_from_plan` sibling had accumulated when "
        "the fork was found. A fork that no longer exists cannot be measured.",
    "nine fragments had just been promoted":
        "historical and says so in the sentence: the count when that module "
        "landed. `_PROMOTED` has grown since.",
    "accumulated 61 duplicated blocks":
        "historical: the corpus before any promotion, and the evidence the rule "
        "had never been applied to prose.",
    "61 blocks cannot be promoted in one change":
        "historical: the same pre-promotion population, cited as the reason a "
        "frozen baseline exists at all rather than a clean fail.",
    "promoted 35 duplicated blocks":
        "historical: what PR #100 promoted, cited as what the guard cost.",
    'read "there are 19 near-duplicate pairs"':
        "quoted DEFECT: the count this whole module exists because of.",
    "seven drifted pairs":
        "historical: the SAMPLE SIZE of a blind inter-rater trial, fixed when its "
        "classifications were sealed in a commit. The population it was drawn "
        "from moves with the tree; the trial's own sample cannot, and re-deriving "
        "it would silently rewrite what was measured.",
    "promoted iff >1 consumer":
        "not a corpus count — §10.1's rule stated as an inequality. The `1` is "
        "the threshold in the rule, not a measurement of anything.",
}


# How much text around a figure counts as "its sentence" for the purpose of
# finding a registry key. THE EXEMPTION MUST BE LOCAL, and this constant is the
# whole reason why. The first version of this module handed the ENTIRE flattened
# docstring to the registry lookup, so a single declared key anywhere in a
# module docstring excused EVERY figure in it. A mutation inserting "There are
# 47 near-duplicate pairs" into the tier guard's docstring passed green — the
# check was reading a neighbour's evidence, which no amount of re-reading the
# assertion would have shown.
_WINDOW = 90


def _figures_in(path: pathlib.Path) -> list[tuple[str, str]]:
    """Every `<N> <noun>` in the module's prose, with the text AROUND it.

    The second element is a LOCAL window, not the whole docstring: it is what
    the registry lookup gets to see, and scoping it is what makes a declaration
    excuse one figure rather than all of its neighbours.
    """
    src = path.read_text(encoding="utf-8")
    prose: list[str] = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            doc = ast.get_docstring(node)
            if doc:
                prose.append(doc)
    # CONSECUTIVE COMMENT LINES ARE JOINED INTO ONE UNIT. Sweeping them
    # line-by-line — as the first version did — makes a figure whose noun wrapped
    # onto the next line invisible ENTIRELY rather than merely unregistered:
    # "# the corpus holds eleven\n# fragments" has the number in one unit and the
    # noun in the next, and no regex over either can see it.
    run: list[str] = []
    for ln in src.splitlines():
        if ln.lstrip().startswith("#"):
            run.append(ln.split("#", 1)[1])
        elif run:
            prose.append(" ".join(run))
            run = []
    if run:
        prose.append(" ".join(run))
    # Also sweep string literals that are clearly explanatory notes.
    prose += re.findall(r'"([^"\n]{40,})"', src)
    out = []
    for text in prose:
        flat = " ".join(text.split())
        for m in _FIGURE.finditer(flat):
            lo = max(0, m.start() - _WINDOW)
            out.append((m.group(0), flat[lo:m.end() + _WINDOW]))
    return out


def test_every_FIGURE_in_a_promotion_guard_is_BOUND_or_DECLARED() -> None:
    unregistered: list[str] = []
    for path in _PROSE:
        for figure, sentence in _figures_in(path):
            if any(k in sentence for k in _BOUND) or any(k in sentence for k in _DECLARED):
                continue
            unregistered.append(f"{path.name}: {figure!r} in …{sentence[:110]}…")
    assert not unregistered, (
        "these guards state a figure about the corpus they police, and nothing "
        "computes it. A count written here is a race with the tree — five have "
        "already been falsified by the change that shipped them:\n  "
        + "\n  ".join(sorted(set(unregistered)))
        + "\n\nTWO WAYS TO CLOSE THIS:\n"
          "  1. BIND it — add a deriver above and an entry to _BOUND keyed by "
          "the sentence, so the figure is recomputed on every run.\n"
          "  2. DECLARE it — add it to _DECLARED with the reason the tree "
          "cannot answer it (historical measurement, quoted defect, prose that "
          "is not a corpus count). A declaration must say WHY."
    )


def _stale_bindings(prose: dict[str, str], bound: dict[str, callable]) -> list[str]:
    """Bound sentences whose figure no longer equals what its deriver computes.

    A pure function so the control below can drive it with a synthetic registry.
    `_BOUND` is empty today, so the real tree can only ever exercise the passing
    path — and a ratchet whose failing path has never run is one nobody has seen
    work. This is the same shape `_spread` uses next door, for the same reason.
    """
    wrong: list[str] = []
    for name, flat in prose.items():
        for sentence, deriver in bound.items():
            if sentence not in flat:
                continue
            m = _FIGURE.search(sentence)
            assert m, f"_BOUND key {sentence!r} contains no figure to check"
            token = m.group(1).lower()
            claimed = _NUMBER_WORDS.get(token, int(token) if token.isdigit() else None)
            assert claimed is not None, f"unparseable figure in {sentence!r}"
            actual = deriver()
            if claimed != actual:
                wrong.append(f"{name}: {sentence!r} claims {claimed}, tree says {actual}")
    return wrong


def _live_prose() -> dict[str, str]:
    return {p.name: " ".join(p.read_text(encoding="utf-8").split()) for p in _PROSE}


def test_a_BOUND_figure_still_matches_what_the_tree_computes() -> None:
    """The half that rots: the sentence stays put while the tree moves under it."""
    wrong = _stale_bindings(_live_prose(), _BOUND)
    assert not wrong, (
        "a bound figure no longer matches its deriver — recompute it, or move "
        "it to _DECLARED with the reason it is historical:\n  " + "\n  ".join(wrong)
    )


def test_the_BINDING_check_fires_when_a_figure_goes_stale() -> None:
    """Live control for `_stale_bindings`, required because `_BOUND` is empty.

    Without this the test above is a permanent pass over an empty dict, which
    is indistinguishable in a green suite from a working ratchet.
    """
    prose = {"fake.py": "the corpus holds three blocks of shared prose"}
    assert _stale_bindings(prose, {"three blocks": lambda: 3}) == [], (
        "a binding that MATCHES the tree must stay green"
    )
    stale = _stale_bindings(prose, {"three blocks": lambda: 8})
    assert stale, "the check is blind to a figure its deriver contradicts"
    assert "claims 3, tree says 8" in stale[0], f"unhelpful message: {stale[0]}"
    assert _stale_bindings({"fake.py": "no figures at all here"},
                           {"three blocks": lambda: 8}) == [], (
        "a binding whose sentence is absent must not fire here — "
        "test_every_FIGURE_… owns the lapsed-binding case"
    )


def test_no_DECLARATION_outlives_the_sentence_it_excuses() -> None:
    """A registry keyed by source text rots the moment the text is reworded.

    A dead declaration is worse than none: it silently re-permits whatever
    figure later lands near those words. This is the same ratchet the frozen
    lists next door run — the list may shrink, never linger.
    """
    prose = " ".join(_live_prose().values())
    dead = sorted(k for k in {**_BOUND, **_DECLARED} if k not in prose)
    assert not dead, (
        "these registry keys no longer appear in any swept file — the sentence "
        "was reworded or deleted. Remove the entry so the registry keeps "
        "shrinking:\n  " + "\n  ".join(dead)
    )


def test_the_SWEEP_actually_fires_on_an_unregistered_figure() -> None:
    """Negative control. `_FIGURE` is a regex over prose, and the failure mode
    that matters is it matching NOTHING — every assertion above would then pass
    against a docstring full of wrong numbers."""
    found = [f for p in _PROSE for f, _ in _figures_in(p)]
    assert len(found) > 5, (
        f"the sweep found only {len(found)} figures across {len(_PROSE)} "
        f"modules — the predicate is broken and this guard asserts nothing"
    )
    assert _FIGURE.search("there are 19 near-duplicate pairs, most of them")
    assert _FIGURE.search("the refine pair's six fragments")
    assert not _FIGURE.search("a ratio floor of 0.80 and a 120 byte minimum"), (
        "the predicate matches a bare threshold — it would demand a binding for "
        "every constant in the module and get itself deleted"
    )
