"""A number written in prose about a collection in the same file must be true.

THE CLASS, AND WHY IT GOT A GATE ON THE FIFTH PASS RATHER THAN A FIFTH CORRECTION.
PR #101 spent four correction passes on one subject and each pass closed one
figure that prose stated and nothing recomputed. The record, all of it measured
rather than remembered:

  * a guard's docstring said "Measured: 18 modules here walk the production
    tree; 2 carry `_ROOTS`" — the tree held 19 and 3, and it held 19 the moment
    the sentence was written, because the commit that wrote the sentence added
    the nineteenth walker;
  * the sweep that keeps the suite out of the operator's journal said its
    population was "discovered by AST rather than listed" and its recogniser
    found two of the five modules it names;
  * `candidates.md` declared "Six `ship` rows were already applied" above a list
    of eleven ids;
  * and this file's own subject — "The 12 names in `_WITHOUT_A_CONTROL_YET`" —
    sat twenty-nine lines below a comment asserting that no count was restated
    in that file.

Four instances, four different files, three different corpora, one shape.
Enumerating them has not converged in five attempts. The repository already
gates this class in three places and the pattern each uses is the same one:
DERIVE THE NUMBER, DO NOT REMEMBER IT.

  * `test_journal_prose_figures_are_DERIVED.py` — entrypoint-population figures
    in the journal package, bound sentence-by-sentence to derivers.
  * `testing/scripts/tests/unit/test_measurement_figures_are_cited.py` — a
    cite-don't-restate rule for the phase docs that opt in.
  * `testing/scripts/tests/unit/test_candidates_prose_matches_the_table.py` —
    every declared total in `candidates.md` § Where things stand.

The guards under `tests/unit/` were the fourth corpus and had no gate at all,
which is why the defect kept landing there. This is that gate.

WHAT IT KEYS ON, AND WHY THE SCOPE IS THIS NARROW. Prose that counts a
collection the same module DEFINES — "the 12 names in `_WITHOUT_A_CONTROL_YET`",
"the two entries in `_STREAMING_POPEN`". That shape is decidable: the numeral is
in the text, the collection is in the AST, and comparing them needs no judgement
about tense, intent or whether a sentence is history. Measured over
`tests/unit/` when this was written: two matches, both true, zero false
positives — so the gate costs nobody an argument today and fails the moment
either collection moves. `_WITHOUT_A_CONTROL_YET` is *designed to shrink*, so
the first sanctioned edit to it is the first thing this catches.

WHAT THIS DOES NOT LOOK AT, because a check read as broader than it is does more
harm than a narrow one:

  * **A figure about the TREE rather than about a collection in the file.**
    "18 modules here walk the production tree" is invisible here — no collection
    named, nothing to compare against. That half of the class is answered a
    different way, by each guard pinning its own census with an assertion
    (`test_a_census_guard_proves_its_own_predicate.test_the_census_matches_the_
    tree` and its siblings), and this file cannot check that the pin exists.
  * **A count written without naming the collection.** "the twelve grandfathered
    guards" carries no backticked name, so it is out. Naming the collection is
    the thing that makes the claim checkable, and the failure direction is that
    a vaguer sentence escapes rather than that a precise one is blocked.
  * **A collection built by a call rather than a literal.** A frozenset of a
    literal set is read; one assembled by a comprehension or a function call has
    no size the AST can state, and is skipped rather than guessed at.
  * **Whether the sentence is TRUE about anything else it claims.** "the 12
    names are excused from the rule" is checked for `12`; whether they are
    excused, and whether excusing them was right, is a review question.
  * **Prose outside this directory.** The other three corpora have their own
    gates, named above. A figure in a phase doc about a collection in a test
    module is in nobody's population.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

_HERE = Path(__file__).resolve().parent

_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                 "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
                 "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
                 "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
                 "twenty": 20}

# `<numeral> [up to three words] in `_SOME_NAME`` — the shape that is decidable.
# Markdown emphasis around the numeral is tolerated because these docstrings use
# it, and the defect this file exists for was written with it.
_COUNT_OF = re.compile(
    r"\*{0,2}(\d+|" + "|".join(_NUMBER_WORDS) + r")\*{0,2}"
    r"\s+(?:\w+\s+){0,3}?in\s+`(_[A-Z][A-Z_0-9]*)`",
    re.IGNORECASE,
)


def _prose(source: str, tree: ast.Module) -> list[str]:
    """Docstrings and comments — the places a figure is written for a human.

    Comments are read as well as docstrings because the instance that motivated
    this file had one copy in each, and correcting only the docstring is exactly
    how the second copy survived a review pass.
    """
    blobs = [d for node in ast.walk(tree)
             if isinstance(node, (ast.Module, ast.FunctionDef,
                                  ast.AsyncFunctionDef, ast.ClassDef))
             for d in [ast.get_docstring(node)] if d]

    # CONSECUTIVE COMMENT LINES ARE ONE BLOB, AND THIS IS NOT TIDINESS. A claim
    # that wraps — the numeral on one line, the backticked collection on the
    # next — is invisible to a per-line scan, and these comment blocks are
    # wrapped at 79 columns, so wrapping is the NORMAL case rather than the
    # exception. Found by mutating this file: N3 falsified a live count in a
    # sibling and, while reading the output, a SECOND stale copy was visible
    # one comment block away that this check had not reported, because the
    # sentence broke across a newline. Docstrings never had this problem
    # (`ast.get_docstring` returns the whole string), which is exactly why it
    # was easy to miss.
    block: list[str] = []
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            block.append(stripped.lstrip("#").strip())
            continue
        if block:
            blobs.append(" ".join(block))
            block = []
    if block:
        blobs.append(" ".join(block))
    return blobs


def _literal_collections(tree: ast.Module) -> dict[str, int]:
    """Module-level names bound to a collection whose size the AST can state.

    A `frozenset({...})` / `set(...)` / `tuple(...)` wrapper is unwrapped one
    level, because that is how these modules spell an immutable constant. A
    comprehension or a function call has no statable size and is absent from
    this mapping, which is what puts it outside the population rather than
    making it a failure.
    """
    sizes: dict[str, int] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if isinstance(value, ast.Call) and len(value.args) == 1:
            value = value.args[0]
        if isinstance(value, (ast.Set, ast.List, ast.Tuple)):
            size = len(value.elts)
        elif isinstance(value, ast.Dict):
            size = len(value.keys)
        else:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                sizes[target.id] = size
    return sizes


def _claims(path: Path) -> list[tuple[str, str, int, int]]:
    """`(module, collection, claimed, actual)` for every checkable claim."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    sizes = _literal_collections(tree)
    out = []
    for blob in _prose(source, tree):
        for match in _COUNT_OF.finditer(blob):
            raw, name = match.group(1), match.group(2)
            if name not in sizes:
                continue
            claimed = int(raw) if raw.isdigit() else _NUMBER_WORDS[raw.lower()]
            out.append((path.name, name, claimed, sizes[name]))
    return out


def _census() -> list[tuple[str, str, int, int]]:
    return [claim
            for path in sorted(_HERE.glob("test_*.py"))
            if path.name != Path(__file__).name
            for claim in _claims(path)]


def test_the_census_matches_the_tree() -> None:
    """THE POPULATION IS DERIVED — this file may not exempt itself from its rule.

    A floor would be green over a regex that had stopped matching, and a regex
    that has stopped matching is the whole failure mode of a prose gate. Two
    claims were checkable when this was written; failing here means the number
    moved, which is information rather than a defect.
    """
    claims = _census()
    assert len(claims) == 2, (
        f"{len(claims)} checkable prose count(s) found under {_HERE.name}/; "
        f"there were 2 when this was pinned. Found: "
        f"{[(m, n) for m, n, _, _ in claims]}.\n"
        f"If somebody WROTE a new one, that is the gate working — confirm it is "
        f"true and raise this number.\n"
        f"If the count DROPPED without a sentence being deleted, the pattern has "
        f"stopped matching the prose it audits and every assertion below is "
        f"trivially true."
    )


def test_every_prose_count_matches_its_collection() -> None:
    """THE RULE.

    A sentence counting a collection defined in the same file is one edit away
    from being false, and no reader checks it — which is measured, not assumed:
    the instance that motivated this file survived a `build-refine` pass and a
    `review-pr` pass sitting twenty-nine lines under a comment claiming the file
    restated no counts.
    """
    wrong = [(module, name, claimed, actual)
             for module, name, claimed, actual in _census() if claimed != actual]
    assert wrong == [], (
        "these sentences state a count of a collection defined in the same "
        "file, and the collection is a different size:\n"
        + "\n".join(f"  {m}: prose says {c} for `{n}`, it holds {a}"
                    for m, n, c, a in wrong)
        + "\n\nCorrect the prose. If the number was meant to be historical, say "
          "so in words the present tense cannot be read into — this check has "
          "no way to tell a stale claim from a record of one."
    )


# --- positive controls -------------------------------------------------------
# Testing Standard § *Structural tests need a positive control*. The predicate
# is exercised against literal snippets the tree does not contain, so a matcher
# that started answering unconditionally fails HERE rather than passing forever.

_AGREES = '''
"""The 3 names in `_THINGS` are excused."""
_THINGS = frozenset({"a", "b", "c"})
'''

_DISAGREES = '''
"""The 4 names in `_THINGS` are excused."""
_THINGS = frozenset({"a", "b", "c"})
'''

_WORD_DISAGREES = '''
"""Both entries in `_THINGS` — and there are four of them."""
# the two entries in `_THINGS` are exempt
_THINGS = ("a", "b", "c")
'''

_WRAPPED_COMMENT = '''
# a claim that runs past the column limit and states the 4 names
# in `_THINGS` on the following line
_THINGS = frozenset({"a", "b", "c"})
'''

_UNNAMED = '''
"""Twelve guards are grandfathered, and that is the whole list."""
_THINGS = frozenset({"a"})
'''

_NOT_A_LITERAL = '''
"""The 9 names in `_THINGS` come from the tree."""
_THINGS = frozenset(_discover())
'''


def _claims_in(snippet: str) -> list[tuple[str, int, int]]:
    tree = ast.parse(snippet)
    sizes = _literal_collections(tree)
    return [(m.group(2),
             int(m.group(1)) if m.group(1).isdigit() else _NUMBER_WORDS[m.group(1).lower()],
             sizes[m.group(2)])
            for blob in _prose(snippet, tree)
            for m in _COUNT_OF.finditer(blob)
            if m.group(2) in sizes]


def test_the_matcher_discriminates() -> None:
    """A satisfying case, a violating case, and both spellings of the numeral."""
    assert _claims_in(_AGREES) == [("_THINGS", 3, 3)], (
        "a true prose count was not read at all — the matcher has stopped "
        "seeing the shape it audits")
    assert _claims_in(_DISAGREES) == [("_THINGS", 4, 3)], (
        "a FALSE prose count was not caught; this check is decoration")
    assert ("_THINGS", 2, 3) in _claims_in(_WORD_DISAGREES), (
        "a count written as a word escaped — the defect that motivated this "
        "file was written as a digit, and the sibling figures are words")
    assert _claims_in(_WRAPPED_COMMENT) == [("_THINGS", 4, 3)], (
        "a claim WRAPPED ACROSS TWO COMMENT LINES escaped. These blocks are "
        "wrapped at 79 columns, so a numeral and its backticked collection "
        "landing on different lines is the normal case, not an edge one — and "
        "this control exists because a mutation of the joining code fired ZERO "
        "tests: the joining had no positive control, which is the exact defect "
        "the file next door was written to catch")


def test_the_matcher_does_not_OVERREACH() -> None:
    """The two stated boundaries, as literals rather than as a promise.

    Both directions matter: a bare numeral with no collection named cannot be
    checked, and a collection built by a call has no size to check against.
    Admitting either would turn this gate into a source of false reds, which is
    how a gate gets deleted rather than fixed.
    """
    assert _claims_in(_UNNAMED) == [], (
        "a count that names no collection was admitted; there is nothing to "
        "compare it against and it would fail on every run")
    assert _claims_in(_NOT_A_LITERAL) == [], (
        "a collection assembled by a call was given a size — the AST cannot "
        "know one, so this would be a fabricated comparison")
