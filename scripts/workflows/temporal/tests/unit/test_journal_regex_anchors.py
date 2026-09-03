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

    `re` IS MATCHED THROUGH ITS IMPORT BINDINGS, and that was NOT true when this
    file first shipped. Both recognisers required the bare name — `node.func.
    value.id == "re"` — so `import re as _r` / `_r.compile(r"^x$")`, the aliased
    `_r.match(r"^x$", s)`, and `from re import compile as _c` / `_c(r"^x$")`
    were all invisible, verified by three mutations against a green suite. The
    honesty test in the bullet above SHARED that blind spot, so a blind sweep
    and a clean package stayed the same colour — which is the one condition this
    file's own docstring says is why its earlier blindness was ever found. Not
    live when caught (all three regex-using modules import `re` plainly), but
    the closure stated two paragraphs up was published and false.

    THAT DEFECT HAS ITS OWN CLASS AND ITS OWN CHECK. A guard recogniser that
    hard-codes a module's bare name is evaded by an alias in any file, not only
    this one; `testing/scripts/tests/unit/test_a_guard_RESOLVES_the_module_it_
    MATCHES.py` sweeps the repository for it, and this file is in that
    population.
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
_DECLARED: dict[str, str] = {
    # `config_digest._ARRAY_RE`, which finds the `SYMLINK_TARGETS=( … )` block
    # inside `install.sh`. The single `^` is a LINE anchor under `re.MULTILINE`
    # and `\A`/`\Z` would defeat the pattern outright: the array is in the middle
    # of a 358-line file, so anchoring to the start of the STRING matches nothing.
    # The line anchoring is the property — it is what stops a mention of the name
    # in a comment or in a `"${SYMLINK_TARGETS[@]}"` expansion being read as the
    # declaration. Nothing here validates untrusted input; the entries the block
    # yields are validated separately by `_SEGMENT_RE`, which does use `\A`/`\Z`.
    #
    # ⚠ THIS ROW ONCE SAID "BOTH `^`", AND THE SECOND ONE WAS A DEFECT. The
    # closing paren used to be anchored too (`^\)`), which silently required the
    # array to span several lines with the paren first on its own — so the
    # one-line `SYMLINK_TARGETS=(agents rules)` matched nothing and the digest
    # went dark against a perfectly legal installer. The close is now `[^)]*\)`,
    # unanchored, and only the NAME is line-anchored. A row here is a claim a
    # reader can check, so it is corrected rather than left describing the
    # pattern it used to key.
    r"^SYMLINK_TARGETS=\(([^)]*)\)":
        "line anchor under re.MULTILINE — locates a block inside a file, and "
        "does not validate anything",

    # `config_digest._APPEND_RE`, which DETECTS `SYMLINK_TARGETS+=( … )` so the
    # parse can refuse it by name. Same line anchor for the same reason and with
    # the same non-role: it validates nothing and decides nothing about a value —
    # it answers only "does this installer append to the array somewhere", and an
    # append reached through a `"${SYMLINK_TARGETS[@]}"` mention is not one.
    r"^SYMLINK_TARGETS\+=\(":
        "line anchor under re.MULTILINE — detects a block inside a file, and "
        "does not validate anything",
}

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


def re_bindings(tree: ast.Module) -> tuple[set[str], dict[str, str]]:
    """Every name in this module that reaches `re`, in both spellings.

    Returns `(module_names, function_names)` — the names `re` ITSELF is bound to
    (`re`, plus any `import re as X`), and a `{local-name: re-function}` map for
    `from re import compile [as X]`.

    SHARED BY BOTH RECOGNISERS BELOW, AND THAT SHARING IS THE POINT. The two
    used to hard-code `"re"` independently, so the sweep and the test that keeps
    the sweep honest had the identical blind spot: an aliased `^…$` was invisible
    to the sweep AND invisible to the check that the sweep can see everything,
    and the suite was green either way. `re` is seeded unconditionally because a
    control drives these on a snippet with no import statement in it at all.

    `from re import *` IS CLOSED RATHER THAN DECLARED. It binds `compile` and
    every entry point under its own name, so the star is expanded to exactly the
    names this file cares about. Nothing in the tree uses it; a hole that costs
    one line to close does not earn a bullet in the boundary list.
    """
    modules = {"re"}
    functions: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {a.asname or a.name for a in node.names if a.name == "re"}
        elif isinstance(node, ast.ImportFrom) and node.module == "re":
            for alias in node.names:
                if alias.name == "*":
                    functions |= {n: n for n in ("compile", *_UNCOMPILED_ENTRY_POINTS)}
                else:
                    functions[alias.asname or alias.name] = alias.name
    return modules, functions


def compile_calls_in(tree: ast.Module) -> list[tuple[int, ast.expr]]:
    """`(lineno, first-argument-expression)` for every `re.compile(…)` call.

    TAKES A PARSED TREE RATHER THAN A PATH so the recogniser can be exercised
    against a literal snippet — see `test_the_recogniser_answers_correctly_on_a_
    LITERAL`.

    BOTH SPELLINGS: `<re-alias>.compile(…)` and a bare `<name>(…)` bound by
    `from re import compile`. See `re_bindings`.
    """
    modules, functions = re_bindings(tree)
    found: list[tuple[int, ast.expr]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and node.args):
            continue
        func = node.func
        attribute_call = (isinstance(func, ast.Attribute)
                          and func.attr == "compile"
                          and isinstance(func.value, ast.Name)
                          and func.value.id in modules)
        bare_call = (isinstance(func, ast.Name)
                     and functions.get(func.id) == "compile")
        if attribute_call or bare_call:
            found.append((node.lineno, node.args[0]))
    return found


def uncompiled_calls_in(tree: ast.Module) -> list[int]:
    """Line numbers of every `re.<fn>(<pattern>, …)` run WITHOUT being compiled.

    TAKES A PARSED TREE FOR THE SAME REASON `compile_calls_in` DOES: this is the
    control on the sweep's own narrowness, and an uncontrolled control is what
    let both halves share one blind spot. It was written inline inside the test
    and could only ever be driven by the tree it audits.
    """
    modules, functions = re_bindings(tree)
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and ((isinstance(node.func, ast.Attribute)
              and node.func.attr in _UNCOMPILED_ENTRY_POINTS
              and isinstance(node.func.value, ast.Name)
              and node.func.value.id in modules)
             or (isinstance(node.func, ast.Name)
                 and functions.get(node.func.id) in _UNCOMPILED_ENTRY_POINTS))
    ]


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

    IT RESOLVES `re` THE SAME WAY THE SWEEP DOES, through `re_bindings`. It used
    to hard-code the bare name, which is the blind spot the sweep had — so this
    control shared the hole it exists to compensate for, and neither half could
    report the other's blindness.
    """
    bare = uncompiled_calls_in(ast.parse(source.read_text(encoding="utf-8")))
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

    # THE THREE SPELLINGS THAT USED TO BE INVISIBLE. Each was mutated into
    # `citations.py` against a 35-passing baseline and each came back GREEN,
    # which is how this hole was found rather than reasoned about.
    assert parts('import re as _r\nX = _r.compile(r"^abc$")') == [["^abc$"]]
    assert parts('from re import compile as _c\nX = _c(r"^abc$")') == [["^abc$"]]
    assert parts('from re import compile\nX = compile(r"^abc$")') == [["^abc$"]]
    # And the binding is per-module: a bare `compile(...)` with no `from re`
    # import is the BUILTIN, and reading it as a pattern would invent findings.
    assert parts('X = compile("^abc$")\nimport re') == []
    # `import re as _r` does not make an unrelated `re.compile` disappear — the
    # seeded name stays, because a module may do both.
    assert parts('import re as _r\nX = re.compile(r"^abc$")') == [["^abc$"]]
    # The star, closed rather than declared as a hole.
    assert parts('from re import *\nX = compile(r"^abc$")') == [["^abc$"]]


def test_the_UNCOMPILED_recogniser_answers_correctly_on_a_LITERAL() -> None:
    """The other recogniser's control, which it did not have.

    This is the half that keeps the sweep's narrowness honest, so it had the
    most to lose from being untested — and it had the sweep's exact blind spot:
    both keyed on the bare name `re`, so an aliased uncompiled call was
    invisible to the check that uncompiled calls are absent. A blind sweep and a
    clean package are the same colour, and so are a blind honesty test and an
    honest package.
    """
    def lines(src: str) -> list[int]:
        return uncompiled_calls_in(ast.parse(src))

    assert lines('re.match(r"^x$", s)') == [1]
    assert lines('import re as _r\n_r.match(r"^x$", s)') == [2]
    assert lines('from re import match\nmatch(r"^x$", s)') == [2]
    assert lines('from re import search as _s\n_s(r"^x$", s)') == [2]
    assert lines('from re import *\nmatch(r"^x$", s)') == [2]
    # NEGATIVE CONTROLS. A compiled pattern is what the sweep wants and must not
    # be reported here, and neither may an unrelated `.match` on some other
    # object — `_LABEL_RE.match(line)` is live in this package.
    assert lines('import re\nP = re.compile(r"\\\\Ax\\\\Z")\nP.match(s)') == []
    assert lines('other.match(r"^x$", s)') == []
    assert lines('match(r"^x$", s)') == []


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
