"""V1/V2 parity for plan-revision's PROMPT TEXT, byte for byte.

WHY THIS MODULE EXISTS, precisely. `plan-revision.sh` does not hold its prompt
in one place: it captures ~23kB in two quoted heredocs (`STAGES_1_TO_5`,
`RULES`) and interpolates them into two `PROMPT="..."` assignments. A previous
port of a sibling family lifted only the `PROMPT=` strings, and the heredoc
bodies went with them — three prompts shipped at ~935 bytes each, saying "follow
all 8 stages" with no stages. Every run exited 0. It surfaced days later, and
only because a human asked for a stage-by-stage comparison.

Byte counts alone would not have caught it either, because nothing compares a
byte count to anything. This module compares the shipped files to THE SOURCE:
it re-extracts both heredocs and both PROMPT strings out of the bash script on
every run and asserts equality. A prompt that loses content fails here rather
than in a $40 run that reports success.

MIGRATION-SCOPED: the reference is the bash original, so this retires with it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from assembled_prompt import assembled, expand

from modules.assistant.plan import plan_activities as act
from modules.assistant.plan.plan_revision import plan_revision_workflow as wf

REPO_ROOT = Path(__file__).resolve().parents[5]
V1 = REPO_ROOT / "scripts" / "workflows" / "plan-revision.sh"

# Measured off the V1 script at port time, in BYTES of UTF-8 (these prompts are
# full of em-dashes, so a character count reads ~1% low and is not the same
# number). Floors, not equalities: V1 may legitimately gain prose, and this
# suite's job is to catch LOSS. The exact-equality check is `test_*_is_byte_
# identical_to_v1` below; these two exist so a reader sees the magnitude.
V1_STAGES_BYTES = 18_452
# 4_749, lowered from 4_757 on 2026-08-07 — 8 bytes, and the reason is recorded
# because this floor exists precisely so a shrink cannot pass unexplained.
# `sprint/phase docs, loose_ends files, standards docs` became `sprint/phase
# docs, roadmaps, standards docs` on BOTH sides, when the loose-ends store was
# retired and every instruction naming it was removed. The equality check above
# still binds V2 to V1; this floor only moves by hand, with a note.
V1_RULES_BYTES = 4_749


# --- Extraction from the bash source -----------------------------------------
#
# Both extractors are exercised by positive controls further down: an extractor
# that quietly returned "" would make every equality assertion below compare
# empty to empty and pass, which is the exact hollow-green this module exists
# to prevent.

def _heredoc(name: str) -> str:
    """The body of `NAME=$(cat <<'EOF' ... EOF)`, as bash would assign it.

    `$( )` strips trailing newlines, so the captured group IS the value.
    """
    m = re.search(rf"^{name}=\$\(cat <<'(\w+)'\n(.*?)\n\1\n\)", V1.read_text(), re.S | re.M)
    assert m, f"{name} is no longer a quoted heredoc in {V1.name} — V1 changed shape"
    return m.group(2)


_BASH_ESCAPES = {"$": "$", "`": "`", '"': '"', "\\": "\\", "\n": ""}


def _unescape(s: str) -> str:
    """Resolve backslash escapes exactly as bash does inside a double-quoted string.

    Only `$`, backtick, `"`, `\\` and a line-continuation newline are special;
    every other backslash is a literal one. That distinction is load-bearing
    here — the stage body deliberately contains literal `\\$2` and escaped
    backticks that must NOT be unescaped, because they sit inside a QUOTED
    heredoc where bash never touched them.
    """
    out: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] in _BASH_ESCAPES:
            out.append(_BASH_ESCAPES[s[i + 1]])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _prompts() -> list[str]:
    """Both `PROMPT="..."` assignments, unescaped, in source order.

    Order is the file's: index 0 is the --pr path, index 1 the new-branch path.
    """
    raw = re.findall(r'PROMPT="((?:[^"\\]|\\.)*)"', V1.read_text(), re.S)
    assert len(raw) == 2, (
        f"expected exactly 2 PROMPT assignments in {V1.name}, found {len(raw)}. "
        "V1 gained or lost a path; the port covers a different set of prompts than V1 ships."
    )
    return [_unescape(p) for p in raw]


# (shipped file, what it must equal in V1)
PROMPT_FILES = [
    pytest.param("stages_1_to_5.md", lambda: _heredoc("STAGES_1_TO_5"), id="stages_1_to_5"),
    pytest.param("rules.md", lambda: _heredoc("RULES"), id="rules"),
    pytest.param("update_pr.md", lambda: _prompts()[0], id="update_pr"),
    pytest.param("new_branch.md", lambda: _prompts()[1], id="new_branch"),
]


def test_the_v1_script_is_still_where_this_suite_looks() -> None:
    """Guards the path, not the prompts.

    If `plan-revision.sh` moves or is deleted, every check below would fail with
    a file-not-found that says nothing about prompt fidelity — and this module
    is supposed to RETIRE with that script, deliberately, not rot silently.
    """
    assert V1.is_file(), (
        f"{V1} is missing. If V1 was deleted on purpose, delete this module too — "
        "a parity suite with no reference is not a passing test, it is an absent one."
    )


@pytest.mark.parametrize(("filename", "v1_source"), PROMPT_FILES)
def test_prompt_file_is_byte_identical_to_v1(filename: str, v1_source) -> None:
    """NOTHING FROM THE REFERENCE MAY GO MISSING. Additions are permitted.

    THIS ASSERTED EXACT EQUALITY UNTIL 2026-08-13, AND THAT WAS STRICTER THAN
    ITS OWN STATED PURPOSE. This module's docstring says the job is to catch
    LOSS — "Floors, not equalities: V1 may legitimately gain prose, and this
    suite's job is to catch LOSS" — and its failure message names truncation as
    the failure mode. Equality is a proxy for that, and the proxy had a second
    effect nobody chose: it froze this prompt permanently, so no improvement to
    plan-revision's stages could ever ship. That surfaced when two evidenced
    fixes from a run's own reflection could not be applied.

    Containment keeps the whole purpose. Every non-empty reference line must
    still be present, so truncation, deletion and silent replacement all fail
    here exactly as before — a chunk swapped for different text of similar
    length is caught, because the original lines are gone. What now passes is
    the one case equality wrongly rejected: text ADDED alongside everything the
    reference carries.
    """
    # ASSEMBLED, NOT READ. A reference line that has been PROMOTED into
    # `modules/assistant/prompts/` is not lost — it moved, and the dispatched
    # prompt still carries it. Reading the file alone reported four lines as LOST
    # the first time a promotion touched this child, which is a false positive on
    # the one property this module exists to protect. See `assembled_prompt.py`
    # for why that direction of error is the dangerous one across the tree.
    shipped = assembled(wf.PROMPTS / filename)
    # BOTH SIDES ASSEMBLED, AGAINST THE SAME TWO DIRECTORIES, and the symmetry
    # is the point. V1's PROMPT strings carry literal `${RULES}` /
    # `${HEADLESS_EXECUTION_GUARD}` splice points, so expanding only the shipped
    # side reports those tokens as lost content. Each side is resolved against
    # this child's own `prompts/` first and the pool second — which is the order
    # `plan_revision_workflow.prompt_values` itself resolves in, and it is NOT
    # optional here: `${RULES}` is the PLANNING ruleset in this child and the
    # BUILD ruleset in the pool, so a pool-only expansion compares this planning
    # prompt against instructions telling it to change code. That makes the
    # comparison about the PROSE around the splice rather than about where the
    # prose is stored — and a shipped file that drops a placeholder entirely
    # still fails, because the expanded reference then carries a fragment's
    # lines that the shipped side does not.
    expected = expand(v1_source(), local=wf.PROMPTS)
    missing = [ln for ln in expected.splitlines() if ln.strip() and ln not in shipped]
    assert not missing, (
        f"prompts/{filename} has LOST content relative to {V1.name}: "
        f"{len(missing)} reference line(s) are absent, first is {missing[0][:90]!r}. "
        "This is the failure mode the port was built to prevent — a run against a "
        "truncated prompt exits 0 and reports success on the instructions it did receive."
    )


@pytest.mark.parametrize(
    ("filename", "floor"),
    [
        pytest.param("stages_1_to_5.md", V1_STAGES_BYTES, id="stages_1_to_5"),
        pytest.param("rules.md", V1_RULES_BYTES, id="rules"),
    ],
)
def test_the_interpolated_bodies_are_the_expected_magnitude(filename: str, floor: int) -> None:
    """A second, independent check on the two bodies that carry the content.

    Independent because the equality test above compares V2 to V1: if BOTH were
    gutted by the same edit, it would still pass. This one compares against a
    number measured by a human at port time, which no edit can move.
    """
    actual = len((wf.PROMPTS / filename).read_bytes())
    assert actual >= floor, (
        f"prompts/{filename} is {actual} bytes, below the {floor} measured at port "
        f"time — {floor - actual} bytes of instructions have gone missing."
    )


def test_extractors_are_not_silently_returning_nothing() -> None:
    """Positive control for both extractors.

    Testing Standard § Structural tests need a positive control. Every equality
    assertion above is only as good as the thing it compares to: an extractor
    that returned "" for a renamed heredoc would make them compare empty to
    empty and report green over a total loss.
    """
    assert len(_heredoc("STAGES_1_TO_5").encode()) >= V1_STAGES_BYTES
    assert len(_heredoc("RULES").encode()) >= V1_RULES_BYTES
    assert all(len(p) > 500 for p in _prompts())

    with pytest.raises(AssertionError):
        _heredoc("NO_SUCH_HEREDOC")


def test_the_unescaper_distinguishes_bash_escapes_from_literal_backslashes() -> None:
    """Positive control for `_unescape`.

    An unescaper that stripped EVERY backslash would still make the wrapper
    comparisons pass (the wrappers contain only real escapes) while corrupting
    the stage body, which carries literal `\\$` and escaped backticks that bash
    never touched. Pin both directions.
    """
    assert _unescape(r'say \"hi\" in \`code\`') == 'say "hi" in `code`'
    assert _unescape(r"a ~\$2 stop and \d and \w") == r"a ~$2 stop and \d and \w"


# --- The assembled prompt, through the real call path ------------------------

def _assembled(monkeypatch: pytest.MonkeyPatch, **kwargs) -> str:
    """Run the workflow with the model and gh stubbed, returning the real prompt.

    Deliberately NOT a hand-built values dict compared against the templates: the
    original defect was a workflow that assembled the WRONG THING, and a test
    that rebuilds the assembly cannot see that. This drives `run_plan_revision`
    itself and captures what it actually handed over.
    """
    captured: dict[str, str] = {}

    def fake_run_claude(prompt: str, **_) -> str:
        captured["prompt"] = prompt
        return "done https://github.com/o/r/pull/7\n"

    monkeypatch.setattr(act, "run_claude", fake_run_claude)
    monkeypatch.setattr(act, "pr_branch", lambda pr, root: "plan/some-branch")
    wf.run_plan_revision(repo_root=Path("/repo"), worktree=Path("/wt"), **kwargs)
    return captured["prompt"]


@pytest.mark.parametrize(
    ("kwargs", "must_contain"),
    [
        pytest.param({"description": "bump the roadmap"},
                     "on a new branch", id="new-branch"),
        pytest.param({"description": "bump the roadmap", "pr_number": "18"},
                     "on PR #18 (branch: plan/some-branch)", id="update-pr"),
    ],
)
def test_the_assembled_prompt_carries_both_interpolated_bodies(
    monkeypatch: pytest.MonkeyPatch, kwargs: dict, must_contain: str
) -> None:
    """THE check this module is named for, on both paths.

    A wrapper that renders cleanly while its `${STAGES_1_TO_5}` resolves to
    nothing is a ~1.4kB prompt that still reads as a complete instruction set.
    Assert the bodies are PRESENT in the thing handed to the model, not merely
    present on disk.
    """
    prompt = _assembled(monkeypatch, **kwargs)

    assert must_contain in prompt, "the wrong path's wrapper was selected"
    # CONTAINMENT, not contiguous substring — same reasoning as
    # `test_prompt_file_is_byte_identical_to_v1` above. The check is "the body
    # arrived", and requiring it to appear as one unbroken run additionally
    # forbade INSERTING anything into the stages, which is not what this test is
    # for. Every reference line must still be present; the ~935-byte failure
    # (wrapper intact, stages gone) fails here exactly as it did before.
    for body in ("STAGES_1_TO_5", "RULES"):
        absent = [ln for ln in _heredoc(body).splitlines() if ln.strip() and ln not in prompt]
        assert not absent, (
            f"the assembled prompt is missing {len(absent)} line(s) of the {body} body, "
            f"first {absent[0][:80]!r}. This is the ~935-byte failure exactly: the "
            "wrapper is intact and the body is gone."
        )
    assert len(prompt.encode()) >= V1_STAGES_BYTES + V1_RULES_BYTES, (
        f"the assembled prompt is {len(prompt.encode())} bytes — smaller than the two "
        "interpolated bodies alone, so at least one of them did not arrive"
    )


def test_the_planning_rules_ship_not_the_shared_build_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`${RULES}` is the same placeholder name in two families and different text.

    The promoted `prompts/rules.md` carries the BUILD ruleset. Resolving to it
    would hand a planning run instructions about test suites and refactoring
    while dropping "do not modify code, scripts, or configuration files" — a
    substitution that renders cleanly and passes every completeness check.
    """
    prompt = _assembled(monkeypatch, description="bump the roadmap")

    assert "This is a PLANNING build — do not modify code, scripts, or configuration files" in prompt
    assert act.shared_prompt("rules") not in prompt, (
        "the shared BUILD rules were substituted into a planning prompt"
    )
