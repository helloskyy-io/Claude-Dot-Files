"""A documented RETURN-CONTRACT may not list an outcome the function cannot produce.

THE CLASS, NOT THE ONE DOCSTRING THAT HAPPENED TO BE FOUND. `wait_for_ci`'s
contract block read:

      True   the declared gate has reported and nothing is PENDING
      False  CI was read successfully and the gate never appeared
      raises CI could not be READ AT ALL within the deadline

and the function never raised. An earlier pass DID make it raise; the raise was
reverted because `build_workflow` forbids `exit 1` at that point, and the
contract block was not reverted with it. Nothing in the suite pinned the
contract, so the suite stayed green while the file's most authoritative sentence
about its own behaviour was false.

WHY THIS IS THE EXPENSIVE SHAPE AND NOT A TYPO. A caller reading it writes an
`except` that can never fire and then reads the returned `False` as *the gate
never appeared* — which is precisely the read-failure/gate-absence conflation
`wait_for_ci` exists to remove, and which cost PR #92 three rebuilds. A false
statement in the block a reader is trained to trust is worse than no statement,
because it stops them checking.

WHAT THIS KEYS ON, AND WHY IT IS NOT `"raises" in docstring`. A naive sweep for
the word fires on seven functions in this tree, every one of them correct:
`_plan_one` says *"Raises what either child raises"* (it propagates), `repo_slug`
says *"Raises through `gh` on failure"* (its callee does), `_redact` discusses
`TypeError` in prose. All seven document a real outcome. Keying on the word would
have made this module noise, and noise is how a check stops being read.

So it keys on the SHAPE OF A CONTRACT BLOCK: two or more consecutive INDENTED
lines whose first token is a return-value token (`True`, `False`, `None`,
`raises`) followed by a description — the table form, where `raises` is listed as
a peer of `True` and `False` rather than mentioned in a sentence. That is a claim
about this function's own interface, and it is checkable.

THE INDENT IS LOAD-BEARING AND WAS MEASURED, NOT ASSUMED. Relaxing `^\\s+` to
`^\\s*` immediately produces a false positive on `exit_record.route`, whose prose
happens to wrap so that two consecutive lines begin *"none to compare…"* and
*"None is a check that skips itself…"*. A table is indented UNDER a paragraph;
wrapped prose sits at the base indent. `ast.get_docstring` dedents to the
smallest indent in the body, so the distinction survives for any docstring that
has prose at all — which every one of these does.

AND THE RAISE MUST BE ABLE TO ESCAPE, WHICH IS THE HALF THAT MAKES THIS WORK.
A plain `any(isinstance(n, ast.Raise))` REPORTS THE PRE-FIX `wait_for_ci` AS
CORRECT — measured against `git show cdda50b:…` rather than reasoned about. That
function raises `ValueError` inside a `try` whose own `except` catches it two
lines later, purely to route a malformed payload into the retry path. The naive
check would have been a green verdict on the exact defect this module was written
for. So a `raise` lexically inside a `try:` BODY does not count; one in an
`except`/`else`/`finally` clause, or outside any `try`, does.

WHAT IT DOES NOT LOOK AT, stated because a guard that reads broader than it is
does more harm than a narrow one:

  * **Prose.** A paragraph asserting the function raises is invisible here. Only
    the table form is checked, because only the table form is unambiguous.
  * **WHICH exception.** A block promising `raises ValueError` over a body that
    raises `RuntimeError` passes. Matching the type needs the call graph.
  * **A raise from a CALLEE.** A function whose whole contract is "my helper
    raises" has no `raise` of its own and would be flagged — write it as prose,
    which is how the seven correct cases above already write it.
  * **Whether the escaping raise is REACHABLE.** One behind a dead branch counts.
  * **Claims about OTHER objects.** `X is what enforces Y` is the wider class
    this belongs to, and this module reaches none of it — see below.

THE WIDER CLASS IS NOT CLOSED BY THIS, and saying so is the point. Prose in this
tree routinely asserts a property of a DIFFERENT object — *"the deliverable guard
is what fails a component with no phases"*, *"`plan-refine` does not exist yet"* —
and both of those were false in the same PR that produced this module. Its
sibling `test_no_prose_claims_a_shipped_workflow_is_UNBUILT` closes one more
sub-class. What is left is the general form, which needs the check C-gbclnzsq proposes.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

FLEET = Path(__file__).resolve().parents[2]

# A line in a RETURN-CONTRACT table: INDENTED, first token is a return-value
# token, then whitespace, then a description. The indent is what separates a
# table from wrapped prose — see the module docstring for the measured case.
_OUTCOME_LINE = re.compile(r"^\s+(True|False|None|raises?)\s+\S", re.I)
_PROMISES_A_RAISE = re.compile(r"^\s+raises?\s", re.I)

# Two, not one: a single indented `raises on a bad shape` is as likely to be
# prose as a contract. Two peers in a row is the table.
_MIN_BLOCK = 2


def contract_blocks(doc: str) -> list[list[str]]:
    """Maximal runs of consecutive outcome lines in a docstring."""
    blocks: list[list[str]] = []
    run: list[str] = []
    for line in doc.splitlines():
        if _OUTCOME_LINE.match(line):
            run.append(line)
            continue
        if len(run) >= _MIN_BLOCK:
            blocks.append(run)
        run = []
    if len(run) >= _MIN_BLOCK:
        blocks.append(run)
    return blocks


def escaping_raises(fn: ast.AST) -> list[ast.Raise]:
    """Every `raise` in this function that is not lexically inside a `try:` body.

    THE HALF THAT MAKES THE GUARD WORK RATHER THAN LOOK LIKE IT DOES. A raise in
    a `try:` body may be swallowed by that statement's own handler — which is
    exactly what `wait_for_ci` does with its `ValueError`, purely to route a
    malformed payload into the retry path. Counting it makes the check green on
    the defect it exists for.

    APPROXIMATE IN ONE DIRECTION ONLY, deliberately. A `try:` body whose handlers
    do NOT catch the raised type is treated as swallowing it, so this
    UNDER-reports escapes and can only produce a false FAILURE, never a false
    pass. For a guard that is the safe direction: a false failure is a sentence
    the author rewrites, a false pass is the state this module was written to end.
    """
    swallowed: set[int] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Try):
            for stmt in node.body:
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.Raise):
                        swallowed.add(id(sub))
    return [n for n in ast.walk(fn)
            if isinstance(n, ast.Raise) and id(n) not in swallowed]


def _documented_contracts():
    """(relpath, lineno, name, block, escapes) for every documented contract in the fleet."""
    for py in sorted(FLEET.rglob("*.py")):
        try:
            module = ast.parse(py.read_text(errors="replace"), str(py))
        except SyntaxError as exc:  # a file this suite cannot parse is its own finding
            pytest.fail(f"{py} does not parse: {exc}")
        for node in ast.walk(module):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for block in contract_blocks(ast.get_docstring(node) or ""):
                yield (py.relative_to(FLEET).as_posix(), node.lineno, node.name,
                       block, escaping_raises(node))


def test_no_contract_block_promises_a_raise_the_function_cannot_make() -> None:
    """THE GUARD. A new outcome table listing `raises` over a body that returns fails here."""
    offenders = [
        (path, lineno, name, [l.strip() for l in block if _PROMISES_A_RAISE.match(l)])
        for path, lineno, name, block, escapes in _documented_contracts()
        if not escapes and any(_PROMISES_A_RAISE.match(l) for l in block)
    ]
    assert not offenders, (
        "a documented return-contract lists `raises` as an outcome and no "
        "`raise` in the body can escape it:\n  "
        + "\n  ".join(f"{p}:{n} {f}() -> {lines}" for p, n, f, lines in offenders)
        + "\n\nEither make it raise, or restate the line as what the code does. "
          "`wait_for_ci` documented a raise an earlier pass had reverted, and a "
          "caller trusting that block writes an `except` that can never fire and "
          "reads the returned False as the OTHER False — the conflation the "
          "function exists to remove. If the raise comes from a CALLEE, say so in "
          "prose rather than in the table; this guard deliberately cannot see that."
    )


def test_the_sweep_can_actually_SEE_a_contract_block() -> None:
    """NEGATIVE CONTROL FOR VACUITY, and it is the failure mode that matters here.

    The guard above passes trivially if `contract_blocks` never matches anything —
    an indentation change or a reworded table would silence it with no diff to
    show for it, and a green vacuous check is indistinguishable from a green real
    one. This asserts the mechanism still finds the block it was written against.
    """
    seen = list(_documented_contracts())
    assert seen, (
        "no return-contract block was found anywhere in the fleet, so the guard "
        "above is vacuous. Either the docstring convention changed or "
        "`_OUTCOME_LINE` stopped matching it — fix the reader, do not delete "
        "this test.")
    assert any(name == "wait_for_ci" for _p, _l, name, _b, _e in seen), (
        "`wait_for_ci` is the function this module was written against and its "
        "contract block is no longer found. If it was legitimately reworded, "
        "point this assertion at whatever carries a contract block now.")


# Each case carries a base-indent prose line, because `ast.get_docstring`
# dedents to the smallest indent present: a docstring whose entire body IS the
# table loses the indent the reader keys on. Real docstrings always have prose.
def _doc(body: str) -> str:
    return f'def f():\n    """d.\n\n    Some prose at the base indent.\n\n{body}    """\n'


@pytest.mark.parametrize("source,should_fail", [
    # THE SHIPPED DEFECT, in shape: a raise listed beside True/False, no escape.
    (_doc("      True   settled\n"
          "      False  absent\n"
          "      raises could not be read\n") + "    return False\n", True),
    # THE PRE-FIX `wait_for_ci` IN MINIATURE — a raise that its OWN try swallows.
    # This is the case a naive `any(ast.Raise)` calls correct, and it is why the
    # escape analysis exists.
    (_doc("      True   settled\n"
          "      raises could not be read\n")
     + "    try:\n        raise ValueError('x')\n    except ValueError:\n        pass\n"
       "    return False\n", True),
    # The same table over a raise that genuinely escapes.
    (_doc("      True   settled\n"
          "      raises could not be read\n") + "    raise RuntimeError('x')\n", False),
    # A raise in an EXCEPT clause escapes; only the try BODY is discounted.
    (_doc("      True   settled\n"
          "      raises could not be read\n")
     + "    try:\n        pass\n    except ValueError:\n        raise RuntimeError('x')\n"
       "    return True\n", False),
    # PROSE, which is the seven-false-positive case this module refuses to flag.
    ('def f():\n    """Raises what either child raises."""\n    return 1\n', False),
    # A one-line "table" is prose about an outcome, not a contract.
    (_doc("      raises on a bad shape\n") + "    return 1\n", False),
])
def test_the_reader_DISCRIMINATES(source: str, should_fail: bool) -> None:
    """The six cases the shape rule and the escape rule have to separate."""
    node = ast.parse(source).body[0]
    promised = any(_PROMISES_A_RAISE.match(l)
                   for b in contract_blocks(ast.get_docstring(node) or "") for l in b)
    assert (promised and not escaping_raises(node)) is should_fail
