"""No workflow may ASSERT a loop cap. It reads one, or its bound is genuinely 1.

THE CLASS, NOT THE FIVE SITES THAT HAPPENED TO BE FOUND. `routing.MAX_LOOPS`
moved from 1 to 3 in `b89f7f5`, and five hand-written sentences across the build
and planning families went on saying *"looping back ONCE"*, *"one loop-back is
the cap"* and *"This is the last automated pass"*. A review pass found one of
them; the enumeration written from that pass named seven files, three of which
were CORRECT and one of which it had missed entirely. Enumerating instances is
what produced that result, so this test keys on the property instead.

WHY IT MATTERS MORE THAN AN INACCURATE NOTE. Two of the five sites were inside a
`correction_pass` PROMPT, so on passes 1 and 2 of 3 a refine model was told it
was the last automated pass and disposed its findings accordingly — deferring
what it would otherwise have fixed, because it believed nothing came after. That
is a false statement changing MODEL behaviour, not merely operator perception.
The other three understate the automated budget an operator reads to decide
whether more passes were available, by 3x.

THE PROPERTY. A string that names a specific cap is fine when the number is
DERIVED — an f-string reading `MAX_LOOPS`, or a branch selecting on the
caller's remaining passes. It is a defect when it is asserted flat, unless the
module's effective bound really is 1. The research family declares its own
`MAX_LOOPS = 1` deliberately (see `routing.py`), so its identical wording is TRUE
and must not be "fixed".

WHAT A NEW MEMBER LOOKS LIKE, and why this fails it: a new workflow copying the
idiom into a `notes.append` gets `routing.MAX_LOOPS` as its bound, 3 != 1, and
this test names the file and the sentence.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.assistant import routing

_ROOT = Path(__file__).resolve().parents[2] / "modules" / "assistant"

# The shapes a cap claim takes in this tree. Deliberately about the CLAIM rather
# than about known-bad strings: each of these asserts "there is exactly one more
# pass, or none", which is the thing that can be false.
CLAIMS = (
    "last automated pass",
    "one loop-back is the cap",
    "looping back once",
    "loop-back once",
    "looping back onc",          # catches "Looping back ONCE — " before the dash
)

# A claim is COUNTED rather than asserted when the branch selecting it tests one
# of these. Then the sentence is a function of the real bound and cannot drift.
COUNT_NAMES = ("MAX_LOOPS", "loops_left", "loops_used")

# A child that never loops, whose claim is made true by the PARENT that loops it.
# The value is checked, not trusted: the named module's own MAX_LOOPS must be 1,
# so a parent that later raises its bound fails here instead of leaving a stale
# waiver behind. This is the only exemption and it carries no prose.
LOOPED_BY = {
    "research_verify_workflow.py":
        "modules.assistant.research.research.research_workflow",
}


def _claims_in(path: Path) -> list[tuple[int, str, bool]]:
    """(line, text, counted) for every cap claim in one module.

    DOCSTRINGS ARE EXCLUDED, and the distinction is the point rather than a
    convenience: this test is about what reaches an OPERATOR or a MODEL. A
    docstring explaining *why* the flat sentence was wrong necessarily quotes it,
    and flagging the explanation would make the fix un-documentable — the
    cheapest way out of which is to delete the explanation, losing the reason.
    """
    tree = ast.parse(path.read_text())
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent          # type: ignore[attr-defined]

    docstrings = {
        id(n.body[0].value) for n in ast.walk(tree)
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and n.body and isinstance(n.body[0], ast.Expr)
        and isinstance(n.body[0].value, ast.Constant)
        and isinstance(n.body[0].value.value, str)
    }

    found: list[tuple[int, str, bool]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in docstrings:
            continue
        low = node.value.lower()
        if not any(c in low for c in CLAIMS):
            continue
        found.append((node.lineno, node.value.strip()[:60], _is_counted(node)))
    return found


def _is_counted(node: ast.AST) -> bool:
    """True when a branch selecting this string tests a real loop count.

    Walks OUT to the enclosing conditionals rather than scanning the whole
    function: a function that happens to mention `MAX_LOOPS` somewhere else
    would otherwise launder a flat assertion sitting beside it. That is the
    scope-of-the-assertion failure this suite has been bitten by before.
    """
    cur = getattr(node, "parent", None)
    while cur is not None:
        test = getattr(cur, "test", None)
        if test is not None:
            names = {n.id for n in ast.walk(test) if isinstance(n, ast.Name)}
            names |= {n.attr for n in ast.walk(test) if isinstance(n, ast.Attribute)}
            if names & set(COUNT_NAMES):
                return True
        cur = getattr(cur, "parent", None)
    return False


def _bound_of(path: Path) -> int:
    """The bound a claim in this file is measured against."""
    if path.name in LOOPED_BY:
        mod = __import__(LOOPED_BY[path.name], fromlist=["MAX_LOOPS"])
        return getattr(mod, "MAX_LOOPS", routing.MAX_LOOPS)
    src = path.read_text()
    for line in src.splitlines():
        if line.startswith("MAX_LOOPS"):
            # `MAX_LOOPS = 1` — a literal own bound.
            tail = line.split("=", 1)[1].strip()
            if tail.isdigit():
                return int(tail)
            break
    # Everything else resolves through routing, directly or via build_helper.
    return routing.MAX_LOOPS


ALL_MODULES = sorted(p for p in _ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def test_the_census_finds_modules_to_judge() -> None:
    """The sweep is non-empty — a glob that matches nothing passes vacuously."""
    assert len(ALL_MODULES) > 20, (
        f"only {len(ALL_MODULES)} modules under {_ROOT}. This census is the whole "
        f"test; if the tree moved, it is silently checking nothing.")


def test_no_module_asserts_a_loop_cap_its_bound_does_not_support() -> None:
    offences: list[str] = []
    counted = 0
    for path in ALL_MODULES:
        for lineno, text, is_counted in _claims_in(path):
            if is_counted:
                counted += 1
                continue
            bound = _bound_of(path)
            if bound != 1:
                offences.append(
                    f"{path.relative_to(_ROOT)}:{lineno} asserts a cap of one "
                    f"({text!r}) while its effective bound is {bound}")
    assert not offences, (
        "a loop cap is ASSERTED where it must be READ:\n  " + "\n  ".join(offences)
        + "\n\nEither derive the sentence from the module's own bound — "
          "`f\"Loop-back {loops} of {routing.MAX_LOOPS}\"`, or a branch selecting "
          "on `loops_left` — or, if the workflow genuinely caps at one, give it "
          "`MAX_LOOPS = 1` so the claim is checkable. The research family does "
          "the latter deliberately.")
    assert counted, (
        "no COUNTED claim was found anywhere. Every site was rewritten to derive "
        "its number from the bound, so zero means the detector stopped matching "
        "the rewritten form and this test now passes over anything.")


def test_every_LOOPED_BY_exemption_names_a_parent_that_really_caps_at_one() -> None:
    """The one waiver shape is a checked claim, not a note.

    A child with no loop of its own is judged against the parent that loops it.
    Recording that as prose would rot the moment the parent's bound moved; this
    resolves the named module and reads its actual `MAX_LOOPS`.
    """
    assert LOOPED_BY, "the exemption map is empty — the check below is vacuous"
    for child, parent_path in LOOPED_BY.items():
        assert any(p.name == child for p in ALL_MODULES), (
            f"{child} is exempted and does not exist — a stale waiver silently "
            f"widens what this test permits")
        mod = __import__(parent_path, fromlist=["MAX_LOOPS"])
        assert getattr(mod, "MAX_LOOPS", None) == 1, (
            f"{child} is exempted because {parent_path} caps at one, and it no "
            f"longer does. The child's prose is now false.")


def test_a_flat_assertion_would_be_caught(tmp_path: Path) -> None:
    """POSITIVE CONTROL on the detector, against the exact shape it exists for.

    Without this, a rename of a claim string or a change to the AST walk would
    make the census match zero literals and report green over the whole tree —
    which reads identically to "every module is clean".
    """
    f = tmp_path / "fake_workflow.py"
    f.write_text('def go(notes):\n'
                 '    notes.append("Looping back ONCE — this is the last automated pass.")\n')
    claims = _claims_in(f)
    assert claims, "the detector no longer matches the literal it was written for"
    assert not claims[0][2], "a flat notes.append was misread as counted"


def test_a_derived_sentence_is_not_caught(tmp_path: Path) -> None:
    """NEGATIVE CONTROL: the fix this test demands must pass it.

    A detector that flagged the corrected form as well would make the offence
    unfixable, and the cheapest response to that is to delete the test.
    """
    f = tmp_path / "fake_workflow.py"
    f.write_text('MAX_LOOPS = 3\n'
                 'def go(notes, loops):\n'
                 '    notes.append(f"Loop-back {loops} of {MAX_LOOPS}."\n'
                 '                 + (" This is the last automated pass."\n'
                 '                    if loops == MAX_LOOPS else ""))\n')
    claims = _claims_in(f)
    assert claims, "the detector stopped seeing the sentence at all"
    assert all(c[2] for c in claims), (
        "the corrected, count-derived form is reported as an assertion")


@pytest.mark.parametrize("stem", ["build_workflow.py", "build_minor_workflow.py",
                                  "plan_project_workflow.py", "build_helper.py"])
def test_the_operator_facing_sites_still_say_something_and_say_it_counted(stem: str) -> None:
    """The instances that produced the class still hold the property.

    Named as well as swept, because the sweep alone would also pass if these
    files stopped mentioning the cap at all — and DELETION IS NOT THE FIX. The
    operator reads these notes to decide whether more automated passes were
    available, so silence costs the same decision the false sentence did.
    """
    path = next(p for p in ALL_MODULES if p.name == stem)
    claims = _claims_in(path)
    assert claims, f"{stem} no longer tells the operator anything about the cap"
    assert all(c[2] for c in claims), (
        f"{stem} still asserts a cap flat: "
        f"{[(c[0], c[1]) for c in claims if not c[2]]}")


@pytest.mark.parametrize("stem", ["build_refine_workflow.py",
                                  "build_refine_minor_workflow.py"])
def test_both_refine_prompts_take_their_finality_from_the_caller(stem: str) -> None:
    """The two MODEL-facing sites, whose defect was the expensive one.

    These told a correction-pass model *"This is the last automated pass"* on
    every pass, so on 1 and 2 of 3 it disposed findings believing nothing came
    after. The sentence is now `helper.finality_note(loops_left)`, so the claim
    is the caller's loop state rather than a constant — and this asserts the
    WIRING, which the census cannot see once the literal has moved out of the
    file.
    """
    path = next(p for p in ALL_MODULES if p.name == stem)
    src = path.read_text()
    assert "helper.finality_note(loops_left)" in src, (
        f"{stem} no longer derives its finality sentence from the caller — a "
        f"constant here is invisible to the census, because the census reads "
        f"literals and this file would have none")
    assert "loops_left" in src.split("def run_refine", 1)[1].split(")", 1)[0], (
        f"{stem}'s entry function does not take `loops_left`, so whatever it "
        f"passes to finality_note is not the parent's remaining budget")
