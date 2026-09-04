"""No live surface may dispatch an agent that no longer exists.

THE FAILURE THIS IS WRITTEN FROM. On 2026-08-18 two agents were consolidated:
`refactoring-evaluator` into `code-reviewer` (as its STRUCTURE lens) and
`standards-auditor` into `quality-control`. The consolidation updated the agent
definitions and one rules table, and missed everything else. Seventeen days
later the retired names were still being dispatched by `build-phase.sh` and
`review-sprint.sh`, still listed as live lenses in
`quality-control-methodology.md`, and still named in the finding-disposition
roster in `engineering-quality.md` — a rule loaded into every session.

THE WORST INSTANCE IS THE ONE THAT ARGUES FOR A SWEEP RATHER THAN A FIX.
`quality-control`'s own description says conformance is its PRIMARY job,
absorbed from `standards-auditor`. The skill it loads told it: *"If something is
a standards-auditor finding, let standards-auditor catch it."* The agent was
instructed to hand its primary responsibility to something that did not exist,
which is a silently-dropped finding in every review stage that ran it — the
exact outcome `engineering-quality.md` § Finding disposition forbids.

WHY AN EXPLICIT MAP RATHER THAN A DERIVATION. "Does this name refer to an agent"
is not decidable from the text: agent names are ordinary hyphenated words, and a
sweep keyed on shape would fire on prose. What IS knowable is the small set of
names this repo has retired, and that set is institutional memory which is
otherwise lost the moment the file is deleted. Add a row when an agent is
consolidated away; the row is the whole cost.

A SURFACE MAY STILL NAME A RETIRED AGENT TO EXPLAIN THE RETIREMENT — that is how
`code-reviewer.md` records what it absorbed, and it is useful. The discriminator
is the same one the sibling workflow sweep uses: name the successor in the same
paragraph, and a reader is informed rather than misrouted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENTS_DIR = REPO_ROOT / "config" / "agents"

# name → what absorbed it. Append a row whenever an agent is consolidated away.
RETIRED_AGENTS = {
    "refactoring-evaluator": "code-reviewer",
    "standards-auditor": "quality-control",
}

SURFACES = sorted(
    p for d in ("config", "docs", "scripts")
    for p in (REPO_ROOT / d).rglob("*")
    if p.suffix in {".md", ".sh"} and ".claude/worktrees" not in str(p) and p.is_file()
)


def _live_agents() -> set[str]:
    return {p.stem for p in AGENTS_DIR.glob("*.md")}


def _paragraphs(text: str) -> list[str]:
    return [b for b in text.split("\n\n") if b.strip()]


# THE DISCRIMINATOR IS RETIREMENT VOCABULARY, NOT PROXIMITY TO THE SUCCESSOR,
# and the first draft of this module got that wrong in a way worth recording.
# It forgave a mention when the successor appeared in the same paragraph — which
# reads sensibly until you apply it to the line this sweep exists to catch:
#
#     "Dispatch all THREE peer-review agents — code-reviewer,
#      refactoring-evaluator, and standards-auditor"
#
# `code-reviewer` is right there, so the proximity rule forgives
# `refactoring-evaluator` in the one sentence that actively misroutes a run. A
# dispatch instruction and a historical note both name the successor; only the
# note says what HAPPENED to the name.
_RETIREMENT_WORDS = (
    "absorbed", "consolidated", "retired", "folded", "superseded",
    "no longer exists", "does not exist", "was renamed", "renamed to",
)


def _is_historical(block: str) -> bool:
    low = block.lower()
    return any(w in low for w in _RETIREMENT_WORDS)


def _misrouting(text: str) -> list[str]:
    """Retired agent named in a paragraph that does not say it was retired."""
    out = []
    for block in _paragraphs(text):
        if _is_historical(block):
            continue
        for dead, successor in RETIRED_AGENTS.items():
            if dead in block:
                out.append(f"{dead} (absorbed into: {successor})")
    return sorted(set(out))


def test_the_agent_dir_is_where_this_module_looks() -> None:
    """Vacuity floor, plus the retirement notice for this module.

    If a retired name ever becomes live again, its row must come out — otherwise
    this sweep forbids naming an agent that exists.
    """
    live = _live_agents()
    assert live, f"no agents found under {AGENTS_DIR}"
    assert SURFACES, "no surfaces found to sweep"
    for dead, successor in RETIRED_AGENTS.items():
        assert dead not in live, (
            f"{dead} is in {AGENTS_DIR} again — it is not retired, so delete its "
            f"row from RETIRED_AGENTS before this sweep starts refusing a real agent."
        )
        assert successor in live, (
            f"{dead}'s successor {successor} does not exist — this map now points "
            f"readers at a second agent that is also gone."
        )


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.name)
def test_no_surface_dispatches_a_retired_agent(path: Path) -> None:
    bad = _misrouting(path.read_text(encoding="utf-8", errors="replace"))
    assert not bad, (
        f"{path.relative_to(REPO_ROOT)} names {bad} without naming the successor "
        f"in the same paragraph. A prompt that dispatches it gets nothing; a skill "
        f"that defers a finding to it drops the finding silently. If the mention is "
        f"deliberately historical, name what absorbed it in the same paragraph."
    )


@pytest.mark.parametrize(
    "text,expected",
    [
        ("let standards-auditor catch it", ["standards-auditor (absorbed into: quality-control)"]),
        # HISTORICAL MENTIONS — the paragraph says what happened to the name.
        ("Absorbed refactoring-evaluator into code-reviewer on 2026-08-18.", []),
        ("quality-control absorbed standards-auditor.", []),
        ("standards-auditor was consolidated away.", []),
        # THE CASE THE FIRST DRAFT FORGAVE: the successor is present, but this is
        # a dispatch instruction, not a note, and it is what misrouted a real run.
        ("Dispatch all THREE — code-reviewer, refactoring-evaluator, and standards-auditor.",
         ["refactoring-evaluator (absorbed into: code-reviewer)",
          "standards-auditor (absorbed into: quality-control)"]),
        # A note in a DIFFERENT paragraph does not excuse this one.
        ("Dispatch standards-auditor.\n\nIt was absorbed into quality-control.",
         ["standards-auditor (absorbed into: quality-control)"]),
        ("Dispatch code-reviewer and security-auditor.", []),
    ],
)
def test_the_MISROUTING_PREDICATE_discriminates(text: str, expected: list[str]) -> None:
    assert _misrouting(text) == expected
