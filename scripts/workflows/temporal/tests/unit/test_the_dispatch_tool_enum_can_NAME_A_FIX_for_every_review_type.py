"""Every `ReviewType` this shared prompt serves must have a tool it can name.

`review_pr/prompts/disposition.md` is the SHARED disposition body for all three
`ReviewType` values; each type adds only a `criteria_*.md` axis fragment. Its
`dispatch_tool` enum is the whole vocabulary a reviewer may emit on the
REDISPATCH exit.

THE DEFECT THIS PINS, WHICH WAS LIVE UNTIL PR #124. The enum read
`<build_minor.sh | build.sh | plan_revision.sh>` — build and planning only.
`criteria_research.md` routes "a defect verify should have caught — wrong PR
body, dead link, missing header" to REDISPATCH, and the universal core says a
research defect that is the run's own scope must be fixed or redispatched and
NEVER filed. So a research reviewer reached a mandatory exit with no legal value
to emit, and whatever it wrote was wrong: a build tool cannot correct a research
PR, and filing was forbidden.

WHY THIS IS A PROPERTY AND NOT A LIST. The gap was found by a human reading one
prompt. Stated as "the enum names research tools" it closes one instance; stated
as "every type this body serves can name a fix" it closes the class, and a
fourth `ReviewType` fails here on the day it is added rather than on the day a
reviewer stalls on it.

WHAT THIS DOES NOT LOOK AT — four things, stated because a guard that greps a
corpus is the shape that passes vacuously:
  * WHETHER THE TOOL ACTUALLY FIXES THE FINDING. It checks that a
    correction-capable tool of the right FAMILY is nameable, not that any given
    defect is within that tool's reach. `sprint.md` is the live example — it is
    a planning artifact no automated tool may edit, and the prompt says so in
    prose this guard cannot read.
  * THE PROSE ABOVE THE ENUM. Stage 4 names the same tools in a sentence; only
    the enum line is parsed here. A prose/enum divergence is invisible.
  * ORDER AND SIZING. Which of a family's tools is the right size for a given
    finding is a judgement the prompt makes and this cannot check.
  * ANY REVIEWER THAT DOES NOT READ THIS BODY. The population is the three
    `ReviewType` members; a consumer reaching REDISPATCH through some other
    prompt is out of scope.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

TEMPORAL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TEMPORAL))

from modules.assistant.review_pr.review_pr_helper import ReviewType  # noqa: E402

DISPOSITION = TEMPORAL / "modules" / "assistant" / "review_pr" / "prompts" / "disposition.md"
RUNNERS = TEMPORAL / "scripts"

#: Which family a shim belongs to, by the prefix its runner and module share.
#: `triage_candidates` is planning: it rules candidates into the plan.
_FAMILY = (
    ("build", ReviewType.BUILD),
    ("research", ReviewType.RESEARCH),
    ("plan", ReviewType.PLANNING),
    ("triage", ReviewType.PLANNING),
)


def _family_of(stem: str) -> ReviewType | None:
    for prefix, kind in _FAMILY:
        if stem.startswith(prefix):
            return kind
    return None


def _correction_capable() -> dict[str, ReviewType]:
    """Every runner that takes `--pr` TO UPDATE an existing PR, by its shim name.

    `run_review_pr.py` also declares `--pr`, and is deliberately excluded by the
    help text: its flag names the PR to REVIEW and is `required=True`. A tool
    that reads a PR is not a tool that corrects one, and collapsing the two would
    let the reviewer name itself as its own remedy.
    """
    out: dict[str, ReviewType] = {}
    for runner in sorted(RUNNERS.glob("run_*.py")):
        text = runner.read_text()
        declaration = re.search(r'add_argument\(\s*"--pr".*?\)', text, re.S)
        if declaration is None or "update an existing" not in declaration.group(0):
            continue
        stem = runner.name[len("run_"):-len(".py")]
        kind = _family_of(stem)
        assert kind is not None, (
            f"{runner.name} takes --pr to update a PR but its name matches no family "
            f"prefix in _FAMILY, so this guard cannot tell which ReviewType it "
            f"corrects. Add the prefix rather than letting it fall out of the set."
        )
        out[f"{stem}.sh"] = kind
    return out


CORRECTION_TOOLS = _correction_capable()


def _enum_members() -> list[str]:
    line = re.search(r"^\s*dispatch_tool:\s*<([^>]*)>", DISPOSITION.read_text(), re.M)
    assert line is not None, (
        f"{DISPOSITION.name} no longer declares a `dispatch_tool: <...>` enum in a "
        f"shape this guard can read. Either the field was renamed — in which case "
        f"follow it — or it was removed, in which case delete this module rather "
        f"than leaving a check that reads nothing."
    )
    return [m.strip() for m in line.group(1).split("|") if m.strip()]


ENUM = _enum_members()


def test_the_correction_tool_census_is_not_empty() -> None:
    """Vacuity floor. Both arms below iterate a derived set; an empty one forgives.

    The count is asserted as a floor rather than an equality so adding an
    eleventh runner does not fail here for no reason — but a glob that stops
    matching, or a `--pr` help string that is reworded past the predicate, drops
    the set toward zero and fails loudly.
    """
    assert len(CORRECTION_TOOLS) >= 10, (
        f"only {len(CORRECTION_TOOLS)} correction-capable runners discovered "
        f"({sorted(CORRECTION_TOOLS)}); the walk over {RUNNERS.name}/run_*.py has "
        f"stopped matching and both arms below are vacuous"
    )
    assert ENUM, "the dispatch_tool enum parsed to zero members"


@pytest.mark.parametrize("kind", list(ReviewType), ids=lambda k: k.value)
def test_the_enum_names_a_correction_tool_for_this_review_type(kind: ReviewType) -> None:
    """The REDISPATCH exit must be reachable with a legal value, for every type."""
    named = [t for t in ENUM if CORRECTION_TOOLS.get(t) is kind]
    assert named, (
        f"the dispatch_tool enum names NO tool that corrects a {kind.value} PR. "
        f"It offers {ENUM}; the correction-capable tools for this type are "
        f"{sorted(t for t, k in CORRECTION_TOOLS.items() if k is kind)}. A "
        f"{kind.value} reviewer that reaches REDISPATCH — which "
        f"criteria_{kind.value}.md routes it to — has no legal value to emit, and "
        f"filing the defect instead is forbidden when it is the run's own scope."
    )


def test_every_enum_member_IS_a_correction_capable_tool() -> None:
    """The other direction: a name in the enum must resolve to a real tool.

    Without this arm the guard above is satisfiable by typing anything, and a
    typo'd or retired shim reads as coverage. `test_no_prompt_ROUTES_the_model_
    into_the_FROZEN_fleet` catches the specific case of a frozen-fleet spelling;
    this catches a name that resolves nowhere at all.
    """
    unknown = [t for t in ENUM if t not in CORRECTION_TOOLS]
    assert not unknown, (
        f"the dispatch_tool enum names {unknown}, which are not shims over a runner "
        f"that takes --pr to update an existing PR. A reviewer emitting one of these "
        f"produces a runway nobody can execute. Known tools: {sorted(CORRECTION_TOOLS)}"
    )


def test_the_FAMILY_PREDICATE_discriminates_on_a_literal() -> None:
    """Positive control: the mapping must separate the three families, not collapse.

    A `_family_of` that returned one constant — or `None` for everything, which
    the assert inside `_correction_capable` would surface as an empty set — makes
    both arms above meaningless while they still pass on a clean tree.
    """
    assert _family_of("build_minor") is ReviewType.BUILD
    assert _family_of("research_minor") is ReviewType.RESEARCH
    assert _family_of("plan_revision") is ReviewType.PLANNING
    assert _family_of("triage_candidates") is ReviewType.PLANNING
    assert _family_of("review_pr") is None, (
        "the reviewer itself now maps to a family, so it could be named as its own "
        "remedy")


# --- the PROSE, not only the enum ------------------------------------------------
#
# THE ENUM WAS ALREADY CORRECT WHEN THIS FAILED, WHICH IS THE WHOLE POINT.
# `dispatch_tool: <...>` is the machine-readable field and the checks above hold it.
# The RUNWAY is free text, and on `image-manager#1` a reviewer wrote step 3 as
# *"redispatch (`plan_revision.sh --pr 1`)"* — a workflow deleted the day before —
# while the enum beside it named only tools that exist. It copied the name from
# THIS PROMPT, which still carried `plan_revision.sh` in three places: the
# redispatch sentence, the tier table, and the write-scope escape hatch.
#
# The same pass also named `plan_draft.sh` as a numbered runway step, having
# written the reason not to two paragraphs earlier — the prompt says NEVER NAME
# `plan_draft.sh` IN A REDISPATCH RUNWAY in bold AND marks it OPERATOR DISPATCH
# ONLY in the table. Prose that already forbids something twice does not need a
# third sentence; it needs a check.
#
# So: a workflow name appearing anywhere in this prompt must be one the enum
# permits, UNLESS the line is telling the model not to dispatch it. Anything else
# is a name a reviewer can copy into a runway.

_PROHIBITION_WORDS = ("never", "not a redispatch", "operator dispatch only",
                      "do not name", "cannot reach", "silently skipped")

_TOOL_IN_PROSE = re.compile(r"\b([a-z][a-z0-9_]*\.sh)\b")
_ENUM_LINE = re.compile(r"^\s*dispatch_tool:")


def _prose_tool_lines(text: str) -> dict[str, list[int]]:
    """Every `<name>.sh` in the body, by the 1-indexed lines it appears on."""
    out: dict[str, list[int]] = {}
    for n, line in enumerate(text.splitlines(), 1):
        if _ENUM_LINE.match(line):
            continue                    # the enum itself, held by the checks above
        for m in _TOOL_IN_PROSE.findall(line):
            out.setdefault(m, []).append(n)
    return out


def _prose_offenders(text: str, permitted: set[str]) -> list[str]:
    lines = text.splitlines()
    bad = []
    for name, where in sorted(_prose_tool_lines(text).items()):
        if name in permitted:
            continue
        for n in where:
            low = lines[n - 1].lower()
            if any(w in low for w in _PROHIBITION_WORDS):
                continue                # the line exists to forbid it — legitimate
            bad.append(f"{name} at line {n}")
    return bad


def test_no_prose_line_NAMES_A_TOOL_THE_ENUM_DOES_NOT_PERMIT() -> None:
    offenders = _prose_offenders(DISPOSITION.read_text(encoding="utf-8"), set(ENUM))
    assert not offenders, (
        "this prompt names a dispatch tool the `dispatch_tool` enum does not permit, "
        "on a line that is not forbidding it:\n  " + "\n  ".join(offenders) + "\n\n"
        f"The enum is {sorted(ENUM)}. A reviewer writes its runway as FREE TEXT and "
        "copies tool names from this body, so a name here the enum rejects reaches an "
        "operator as a step that dispatches nothing. Either add the tool to the enum, "
        "or say plainly on that line that it must not be dispatched."
    )


def test_the_PROSE_PREDICATE_discriminates() -> None:
    """Positive AND negative control, on literals.

    Without the negative arm this is indistinguishable from a ban on naming any
    script, which would fail on the prompt's own prohibitions — the lines that
    exist precisely to stop a reviewer dispatching something.
    """
    text = ("Redispatch with plan_revision.sh --pr 1.\n"
            "NEVER name plan_draft.sh in a redispatch runway.\n"
            "Use build_minor.sh for a scoped correction.\n")
    found = _prose_tool_lines(text)
    assert set(found) == {"plan_revision.sh", "plan_draft.sh", "build_minor.sh"}
    assert _prose_offenders(text, {"build_minor.sh"}) == ["plan_revision.sh at line 1"]
