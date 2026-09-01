"""No pattern in this package anchors with `^`/`$` — swept over the whole package.

WHY THIS FILE EXISTS, AS THE MEASUREMENT RATHER THAN AS A PRINCIPLE. `$` does not
mean "end of string". It matches at the end of the string AND immediately before
a trailing newline, so `re.compile(r"^[0-9a-f]{64}$")` accepts `"ab…f\\n"` — an
anchored-LOOKING validator that admits a smuggled newline. `\\Z` has no such
second meaning, and `\\A` says "start of string" where `^` says either that or
"start of a line" depending on a flag written somewhere else.

This package acquired the defect and then the false closure:

  * `validated_digest` used `^…$`, so a digest carrying a trailing newline passed
    the shape gate — and that gate IS the path safety, because the on-disk path
    is composed from the digest. It RETURNED and was composed onto a path by the
    function whose docstring says such a value is refused rather than composed.
  * A review pass swept the package, converted what it found, and published the
    sweep as exhaustive. `bag._LABEL_RE` was still `^…$` at that commit. Not a
    live defect — both of its callers feed it `splitlines()` output — but a
    published closure that was false, which is worse than an open one because the
    next reviewer inherits it and does not look.

Converting the sites did not converge; the next reviewer found the residue. What
converges is a check that keys on the CLASS, so a `^` or `$` written into this
package tomorrow fails at the moment it is written rather than at the moment
somebody re-runs the sweep by hand.

⚠ THE RULE IS ABSOLUTE HERE AND THAT IS A CHOICE, not an oversight. `^…$` under
`re.MULTILINE` is correct line-scanning and nothing in this package does it; a
pattern that needs it will fail this and should be added to `_DECLARED` below
with the reason, exactly as the containment and tag-line sweeps do for their own
exemptions. An empty escape hatch is the honest state, not a missing one.

⚠ WHAT THIS DOES NOT COVER, because a sweep is only as good as its predicate:

  * IT SWEEPS `modules/journal/*.py` AND NOTHING ELSE, the same scope as the
    containment and tag-line sweeps. A pattern in another package is invisible
    here and the scope is named in the failure message so a reader hitting it
    learns the boundary rather than assuming there is none.
  * IT SEES A STRING LITERAL PASSED TO `re.compile`. A pattern built by
    concatenation at runtime, or handed to `re.match` directly without being
    compiled, is invisible. A test below asserts this package compiles every
    pattern it uses, which is what keeps the narrow predicate honest.
  * IT IS A CHECK ON SPELLING, NOT ON CORRECTNESS. `\\A…\\Z` around the wrong
    character class is still the wrong pattern, and no sweep reaches that.
"""

from __future__ import annotations

import ast
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
PACKAGE = REPO_ROOT / "scripts" / "workflows" / "temporal" / "modules" / "journal"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "workflows" / "temporal"))

# Patterns in this package that legitimately anchor with `^` or `$`, each with
# the reason it cannot use `\A`/`\Z`. Empty, and an entry added here is a claim a
# reader can check — which is the point of declaring rather than skipping.
_DECLARED: dict[str, str] = {}

# The module-level functions this package may use to run an UNCOMPILED pattern.
# `re.compile` is how a pattern becomes visible to the sweep above, so a direct
# `re.match(r"...", s)` is a pattern the sweep cannot see.
_UNCOMPILED_ENTRY_POINTS = ("match", "fullmatch", "search", "sub", "subn",
                            "split", "findall", "finditer")


def _anchor_positions(pattern: str) -> list[str]:
    """The `^` and `$` in `pattern` that are ANCHORS, in source order.

    A `^` immediately after `[` negates a character class and a `$` inside one is
    a literal, so both are skipped; so is anything backslash-escaped. Without
    this, `_SAFE_SEGMENT_RE`'s `[^A-Za-z0-9._-]+` would be reported as an anchor
    and the sweep would be answered by suppressing it.

    ⚠ A `]` IN LEADING POSITION IS A LITERAL, NOT THE CLOSE — `[]a]` and `[^]a]`
    are single classes containing `]` and `a`. A scanner that closed on it would
    read the rest of the pattern as being outside a class and report the class's
    own `$` as an anchor, which is the direction that produces a FALSE finding
    and gets answered with a `_DECLARED` suppression. No pattern in scope uses
    the idiom today; the scanner handles it because a suppression added for a
    scanner bug outlives the bug.
    """
    found: list[str] = []
    in_class = False
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "\\":
            i += 2
            continue
        if in_class:
            if char == "]":
                in_class = False
            i += 1
            continue
        if char == "[":
            in_class = True
            i += 1
            if i < len(pattern) and pattern[i] == "^":
                i += 1
            if i < len(pattern) and pattern[i] == "]":
                i += 1          # a leading `]` is a member, not the close
            continue
        if char in "^$":
            found.append(char)
        i += 1
    return found


def _literal_parts(node: ast.expr) -> list[str] | None:
    """The string literals inside a pattern expression, or `None` if unreadable.

    ⚠ THIS RETURNING `None` IS A FINDING, NOT A SKIP, and the distinction is the
    whole reason it is written this way. The first draft of this file matched
    `ast.Constant` alone, which made `content_store._HEX_DIGEST_RE` —
    `re.compile(r"\\A[0-9a-f]{%d}\\Z" % DIGEST_HEX_LENGTH)`, the gate that IS
    r7(b)'s path safety — INVISIBLE to the sweep. Reverting that pattern to
    `^…$` left the sweep green. Found by mutating this file's own new assertion
    rather than by reading it, which is the only way it could have been found:
    a blind sweep and a clean package are the same colour.

    So an expression this cannot read fails `test_no_pattern_is_unreadable`
    below. A pattern nobody can check must not look like a pattern that checked
    out.
    """
    if isinstance(node, ast.Constant):
        return [node.value] if isinstance(node.value, str) else None
    # `"literal" % (…)` and `"literal" + …`: the anchors live in the literal
    # halves, and a substituted value cannot introduce one without being a
    # literal itself somewhere this walk reaches.
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.Add)):
        left = _literal_parts(node.left)
        if left is None:
            return None
        if isinstance(node.op, ast.Mod):
            return left
        right = _literal_parts(node.right)
        return None if right is None else left + right
    # An f-string: the constant segments carry the anchors, the interpolations
    # are opaque and contribute nothing this sweep can rule on.
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif not isinstance(value, ast.FormattedValue):
                return None
        return parts
    return None


def compile_calls_in(tree: ast.Module) -> list[tuple[int, ast.expr]]:
    """`(lineno, first-argument-expression)` for every `re.compile(…)` call.

    TAKES A PARSED TREE RATHER THAN A PATH so the recogniser can be exercised
    against a literal snippet — see `test_the_recogniser_answers_correctly_on_a_
    LITERAL`.
    """
    return [(node.lineno, node.args[0])
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and node.func.attr == "compile"
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "re"
            and node.args]


def _compile_calls(path: pathlib.Path) -> list[tuple[int, ast.expr]]:
    return compile_calls_in(ast.parse(path.read_text(encoding="utf-8")))


def _compiled_patterns(path: pathlib.Path) -> list[tuple[int, str]]:
    """`(lineno, pattern-fragment)` for every readable `re.compile(…)` in a module.

    One entry per literal FRAGMENT, so a pattern assembled from two literals is
    checked in both halves rather than in whichever one came first.
    """
    out: list[tuple[int, str]] = []
    for lineno, expr in _compile_calls(path):
        for part in _literal_parts(expr) or ():
            out.append((lineno, part))
    return out


def _sources() -> list[pathlib.Path]:
    return sorted(PACKAGE.glob("*.py"))


def test_the_sweep_finds_patterns_at_all() -> None:
    """A predicate that stopped matching is green and asserts nothing."""
    total = sum(len(_compiled_patterns(p)) for p in _sources())
    assert total, (
        f"no `re.compile(<literal>)` found under {PACKAGE}; either the patterns "
        "moved or the AST predicate went blind")


@pytest.mark.parametrize("source", _sources(), ids=lambda p: p.name)
def test_no_pattern_is_unreadable_to_the_sweep(source: pathlib.Path) -> None:
    """A pattern this file cannot read must not pass silently.

    The sweep below can only rule on literals it can recover. An expression it
    cannot recover is reported HERE, so "no anchors found" never means "nothing
    was looked at" — which is exactly what it meant before this test existed.
    """
    unreadable = [lineno for lineno, expr in _compile_calls(source)
                  if _literal_parts(expr) is None]
    assert not unreadable, (
        f"{source.name} builds a regex the anchor sweep cannot read at line(s) "
        f"{unreadable}; keep the pattern a literal (optionally `%`-formatted or "
        "an f-string) so `_literal_parts` can recover it, or extend "
        f"`_literal_parts` in {pathlib.Path(__file__).name} to cover the form")


@pytest.mark.parametrize("source", _sources(), ids=lambda p: p.name)
def test_no_pattern_anchors_with_caret_or_dollar(source: pathlib.Path) -> None:
    """`\\A` and `\\Z` mean one thing each; `^` and `$` do not."""
    offenders = [
        (lineno, pattern, anchors)
        for lineno, pattern in _compiled_patterns(source)
        if (anchors := _anchor_positions(pattern)) and pattern not in _DECLARED
    ]
    assert not offenders, (
        f"{source.relative_to(PACKAGE.parent.parent)} anchors with `^`/`$`:\n"
        + "\n".join(f"  line {lineno}: {pattern!r} -> {''.join(anchors)}"
                    for lineno, pattern, anchors in offenders)
        + "\n`$` also matches before a TRAILING NEWLINE, so an anchored-looking "
          "validator accepts one. Use `\\A`/`\\Z`, or add the pattern to "
          f"`_DECLARED` in {pathlib.Path(__file__).name} with the reason it "
          f"cannot. Scope: {PACKAGE}/*.py only.")


@pytest.mark.parametrize("source", _sources(), ids=lambda p: p.name)
def test_every_pattern_is_compiled_so_the_sweep_can_see_it(
        source: pathlib.Path) -> None:
    """`re.match(r"...", s)` is a pattern with no `re.compile` to be found at.

    The sweep above reads compiled literals. This is the half that keeps that
    predicate honest: the alternatives are ABSENT, rather than the predicate
    being narrow and nobody having checked.
    """
    tree = ast.parse(source.read_text(encoding="utf-8"))
    bare = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _UNCOMPILED_ENTRY_POINTS
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "re"
    ]
    assert not bare, (
        f"{source.name} calls `re.<fn>(pattern, …)` directly at line(s) "
        f"{bare}; compile the pattern to a module constant so the anchor sweep "
        "in this file can see it")


def test_the_recogniser_answers_correctly_on_a_LITERAL() -> None:
    """`compile_calls_in` + `_literal_parts`, on snippets the tree does not hold.

    The population check above is a floor; this is the control under it. A
    recogniser that quietly stopped matching `re.compile` would leave every
    per-file assertion trivially true and every one of them green.
    """
    def parts(src: str) -> list[list[str] | None]:
        return [_literal_parts(expr)
                for _, expr in compile_calls_in(ast.parse(src))]

    assert parts('X = re.compile(r"^abc$")') == [["^abc$"]]
    assert parts('X = re.compile(r"\\Aabc\\Z", re.I)') == [["\\Aabc\\Z"]]
    # `%`-formatted: the anchors live in the left literal, and this is the form
    # the sweep's own first draft could not see.
    assert parts('X = re.compile(r"^[0-9a-f]{%d}$" % N)') == [["^[0-9a-f]{%d}$"]]
    # f-string: the constant segments are recovered, the interpolation is opaque.
    assert parts('X = re.compile(f"^{PREFIX}$")') == [["^", "$"]]
    # Concatenation: both halves, so an anchor in either is checked.
    assert parts('X = re.compile("^a" + "b$")') == [["^a", "b$"]]
    # UNREADABLE, and reported as such rather than skipped.
    assert parts('X = re.compile("".join(PARTS))') == [None]

    # Not a `re.compile` call at all.
    assert parts('X = compile("^abc$")') == []
    assert parts('X = other.compile(r"^abc$")') == []
    assert parts('"""re.compile(r\'^abc$\') in a docstring"""') == []


def test_the_anchor_scanner_ignores_a_negated_character_class() -> None:
    """The scanner's own predicate, pinned.

    `[^A-Za-z0-9._-]+` is live in `bag.py` and contains a `^` that is not an
    anchor. A scanner that reported it would be answered by a `_DECLARED` entry,
    which is how a sweep starts accumulating suppressions and stops being read.
    """
    assert _anchor_positions(r"[^A-Za-z0-9._-]+") == []
    assert _anchor_positions(r"[$]") == []
    assert _anchor_positions(r"\^\$") == []
    assert _anchor_positions(r"^abc$") == ["^", "$"]
    assert _anchor_positions(r"\A[^:\s][^:]*\Z") == []
    # A `]` in leading position is a member of the class, so the `$` after the
    # real close is the only anchor in these.
    assert _anchor_positions(r"[]a]$") == ["$"]
    assert _anchor_positions(r"[^]a]$") == ["$"]
    assert _anchor_positions(r"[]$]") == []


def test_the_package_pattern_that_was_the_residue_refuses_a_trailing_newline() -> None:
    """The instance, pinned beside the class check that would now catch it.

    Both of `_LABEL_RE`'s callers feed it `splitlines()` output, so this was
    never live — and that is exactly why it survived a sweep published as
    exhaustive. What is asserted here is the pattern's own contract, so a caller
    change cannot quietly turn it into a defect.
    """
    from modules.journal.bag import _LABEL_RE

    assert _LABEL_RE.match("Label: value") is not None
    assert _LABEL_RE.match("Label: value\n") is None


def test_the_digest_gate_refuses_a_trailing_newline() -> None:
    """The other instance of the same class, in the gate that IS the path safety."""
    from modules.journal.content_store import ContentStoreError, validated_digest

    good = "a" * 64
    assert validated_digest(good) == good
    with pytest.raises(ContentStoreError):
        validated_digest(good + "\n")
