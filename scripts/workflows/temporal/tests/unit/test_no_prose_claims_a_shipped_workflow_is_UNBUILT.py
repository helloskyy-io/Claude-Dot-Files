"""No prose in the fleet may say a workflow does not exist when its module does.

THE CLASS, AND IT WAS FOUND THREE TIMES IN ONE PR. `plan-feature` shipped naming
its judge and saying it was unbuilt, in three places:

  * `plan_feature_workflow.py`'s docstring — *"it DOES NOT EXIST YET… nothing in
    this tree calls it. Do not read any reference to it as a dependency."*
  * `prompts/plan_feature.md` — *"`plan-verify` … does not exist yet"*, which is
    SENT TO THE MODEL on every `plan-feature` dispatch.
  * `run_plan_feature.py`'s completion banner — printed at the operator.

The PR that built `plan-verify` falsified all three and updated none. Three
separate review lenses found them independently, which is the measurement that
says a check is cheaper than the reading.

WHY THIS IS WORSE THAN A STALE COMMENT. Each of the three is read by a different
party and each misleads differently. The prompt tells a MODEL its output has no
cold reader, which changes what it writes. The banner tells an OPERATOR there is
no next step to run. And the docstring says *"do not read any reference to it as a
dependency"* — a maintainer acting on that would refactor away a live call from
`plan_project._plan_one`. A false statement in the block a reader trusts stops
them checking, which is exactly the property that makes it expensive.

WHAT IT KEYS ON. A workflow NAME in backticks, adjacent to a phrase asserting
non-existence, in any Python module, prompt or shim under the fleet — against the
set of workflows that have a module on disk. The existence half is derived from
the tree, so a workflow landing tomorrow retires every claim about it that day,
with no list to maintain.

WHAT IT DOES NOT LOOK AT, stated so it is not read as covering the wider class:

  * **Any claim other than existence.** *"`X` is what enforces `Y`"* is the same
    family and is not reached here. C-084 proposes the general mechanism.
  * **Prose naming a workflow with no module** — that is a correct claim about
    something genuinely unbuilt, and the whole point is to leave it alone.
  * **The distance between the name and the phrase.** They must be within one
    sentence-ish window; a paragraph asserting non-existence three sentences from
    the name passes.
  * **HISTORICAL statements**, which are legitimate and common in this tree.
    *"used to say"*, *"no longer"*, *"until this landed"* and their neighbours are
    exempted explicitly. That exemption is the one place this guard trades recall
    for the ability to write an honest changelog in a docstring.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FLEET = Path(__file__).resolve().parents[2]
_MODULES = FLEET / "modules" / "assistant"


def _shipped_workflows() -> set[str]:
    """Every workflow with a `*_workflow.py` on disk, by hyphenated name.

    DERIVED FROM THE TREE so the set retires claims on its own. A hand list would
    need the same edit this guard exists to make unnecessary.
    """
    return {p.stem.removesuffix("_workflow").replace("_", "-")
            for p in _MODULES.rglob("*_workflow.py")}


# The name in backticks, then up to ~90 characters, then a non-existence phrase.
# Backticks are required: this fleet writes every workflow name that way, and
# without them `plan-verify` matches inside prose about verification generally.
_CLAIM = re.compile(
    r"`(?P<name>[a-z][a-z-]+)`(?P<gap>[^`\n]{0,90}?)"
    r"(?P<claim>do(?:es)? not exist|does not yet exist|DOES NOT EXIST"
    r"|is not built|does not exist yet|has not been built|is unbuilt)",
    re.I)

# Historical statements are legitimate and this tree is full of them — a docstring
# recording that a claim USED to be false is the honest form, and flagging it
# would teach authors to delete the history instead of the defect.
_HISTORICAL = re.compile(
    r"used to|no longer|until (?:this|it) (?:landed|lands)|"
    r"stopped being true|this paragraph used to|was false|shipped .{0,20}saying",
    re.I)

_SEARCHED = ("*.py", "*.md", "*.sh")


def _prose_files() -> list[Path]:
    files: list[Path] = []
    for pattern in _SEARCHED:
        files += [p for p in FLEET.rglob(pattern)
                  if "tests" not in p.relative_to(FLEET).parts]
    return sorted(files)


def _stale_claims() -> list[tuple[str, int, str, str]]:
    shipped = _shipped_workflows()
    out = []
    for path in _prose_files():
        for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if _HISTORICAL.search(line):
                continue
            for m in _CLAIM.finditer(line):
                if m.group("name") in shipped:
                    out.append((path.relative_to(FLEET).as_posix(), n,
                                m.group("name"), line.strip()[:160]))
    return out


def test_no_prose_says_a_workflow_that_SHIPPED_does_not_exist() -> None:
    """THE GUARD. The next workflow to land retires every claim about it, or fails here."""
    stale = _stale_claims()
    assert not stale, (
        "prose asserts a workflow does not exist, and its module is on disk:\n  "
        + "\n  ".join(f"{p}:{n} (`{w}`) — {line}" for p, n, w, line in stale)
        + "\n\nThe PR that BUILDS a workflow owns every sentence it falsifies. "
          "Correct the claim, or phrase it as history (`used to say`, `no longer`, "
          "`until this landed`) if the record is worth keeping — the historical "
          "form is exempted deliberately.")


def test_the_reader_can_SEE_the_workflows_and_the_phrases() -> None:
    """VACUITY FLOOR, in both halves, because either one silently empties the guard.

    A rename of `*_workflow.py`, a change in how names are written, or a reword of
    the phrase list makes the sweep pass over nothing — which is indistinguishable
    from a clean tree.
    """
    shipped = _shipped_workflows()
    assert len(shipped) >= 12, f"only found {sorted(shipped)} — the discovery broke"
    assert "plan-verify" in shipped and "plan-feature" in shipped

    files = _prose_files()
    assert len(files) >= 50, f"the prose sweep found only {len(files)} files"

    # The claim reader must still match the shape it was written against.
    probe = "**`plan-verify` is the fresh-context reviewer, and it does not exist yet.**"
    m = _CLAIM.search(probe)
    assert m and m.group("name") == "plan-verify", (
        f"the claim reader no longer matches the sentence this module was written "
        f"against: {probe!r}")


@pytest.mark.parametrize("line,flagged", [
    ("**`plan-verify` is the reviewer, and it does not exist yet.**", True),
    ("`plan-verify` DOES NOT EXIST YET — it is named here as the handoff", True),
    ("NOT SIZED — `plan-verify` estimates the phases, and it does not exist yet.", True),
    # A workflow with no module: a correct claim, and the guard must leave it be.
    ("`plan-forecast` does not exist yet, so nothing reads this.", False),
    # History, which is how a correction is honestly recorded.
    ("This paragraph used to say `plan-verify` does not exist yet.", False),
    ("`plan-verify` no longer does not exist — it landed 2026-08-15.", False),
    # Nothing to do with existence.
    ("`plan-verify` reads the roadmap cold and sizes every phase.", False),
])
def test_the_reader_DISCRIMINATES(line: str, flagged: bool) -> None:
    """The seven cases the phrase rule and the history exemption have to separate."""
    shipped = _shipped_workflows()
    hit = (not _HISTORICAL.search(line)
           and any(m.group("name") in shipped for m in _CLAIM.finditer(line)))
    assert hit is flagged
