"""`disposition.md`'s sizing table must agree with `config.yaml`, and its prose with itself.

THE TABLE IS AN INSTRUMENT, NOT A DESCRIPTION. `review-pr` reads it to size the
redispatch it emits — "an under-sized tool stalls at its turn cap, an over-sized
one spends a review cycle on a one-line fix" is the prompt's own sentence. So a
figure that drifts from `config.yaml` does not merely read wrong: it routes a
correction to a tier that cannot finish it, and the failure surfaces as a run
truncated at its cap rather than as a wrong number anybody would look for.

WHY A GUARD AND NOT CARE. Every one of the five rows was hand-transcribed from
`config.yaml`, and the transcription was CORRECT when written — verified figure
by figure. That is exactly the shape that rots: nothing links the two files, so
the next `max_turns` edit lands in `config.yaml` alone and the table is silently
stale until a reviewer sizes against it. This repo has already ruled that a
hand-kept derived value needs a completeness check rather than diligence.

MEASURED 2026-08-20, WHICH IS WHY THE PROSE HALF EXISTS TOO. PR #124 edited the
sentence below the table to change "will not fit in 100 turns" -> "200 turns",
and left "seen by FIVE lenses rather than one" standing in the same sentence —
while the table two rows above had said **two** since the 2026-08-18 agent
consolidation folded `refactoring-evaluator` into `code-reviewer` and
`standards-auditor` into `quality-control`. One number in the sentence was
updated and the other was not. **The sentence IS the sizing rule**, so a reviewer
reading it bought three review lenses that do not exist.

THE CLASS: a figure in this prompt that RESTATES a fact owned elsewhere. Two
directions, both checked here — the table against `config.yaml`, and the prose
against the table. A guard pinning the five numbers that exist today would be
green on the sixth row.

WHAT THIS DOES NOT CHECK, stated because a check read as broader than it is does
more harm than a narrow one:

  * **Whether a turn cap is the RIGHT cap.** That is argued at each key in
    `config.yaml`, at length. This asks only that the prompt reports what the
    config says.
  * **The `model` column.** It is prose ("**sonnet** to write, **opus** to
    verify"), not a figure, and the model keys it names are documented in
    `config.yaml`'s own agent-tier canon block, which is explicitly
    DOCUMENTATION ONLY. Pinning it would pin the wording, not the fact.
  * **Prose figures elsewhere in the prompt.** Only the one sentence that
    restates the table is parsed. A general "every number in this file is
    derived" contract is a much larger one and would need each number to name
    its source; this closes the pair that actually drifted.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[5]
CONFIG = REPO / "config.yaml"
PROMPT = (Path(__file__).resolve().parents[2]
          / "modules/assistant/review_pr/prompts/disposition.md")

# tool -> the `max_turns:` keys its children consume, in the order the table
# prints them. Two entries means a two-child workflow printed as "A + B".
_TOOL_CHILDREN = {
    "build.sh":          ("build-draft", "build-refine"),
    "build_minor.sh":    ("build-draft-minor", "build-refine-minor"),
    "research.sh":       ("research-draft", "research-refine"),
}


def _table_rows() -> dict[str, str]:
    """`{tool: turn-cap cell}` parsed from the sizing table."""
    rows: dict[str, str] = {}
    for line in PROMPT.read_text().splitlines():
        m = re.match(r"^\|\s*`([a-z_]+\.sh)`\s*\|([^|]*)\|([^|]*)\|", line)
        if m:
            rows[m.group(1)] = m.group(3).strip()
    assert len(rows) >= 5, (
        f"the sizing-table parser found {len(rows)} rows in {PROMPT.name}, "
        f"expected at least 5 — the table's shape changed and this guard has "
        f"stopped reading it, which is a guard that passes on anything"
    )
    return rows


@pytest.mark.parametrize("tool", sorted(_TOOL_CHILDREN))
def test_every_turn_cap_in_the_table_matches_config_yaml(tool: str) -> None:
    caps = yaml.safe_load(CONFIG.read_text())["max_turns"]
    expected = " + ".join(str(caps[k]) for k in _TOOL_CHILDREN[tool])

    row = _table_rows()
    assert tool in row, (
        f"`{tool}` has no row in {PROMPT.name}'s sizing table, but the prompt's "
        f"`dispatch_tool` enum offers it. A reviewer can name a tool it cannot size."
    )
    assert row[tool] == expected, (
        f"{PROMPT.name} sizes `{tool}` at '{row[tool]}' but `config.yaml` "
        f"declares {expected} for {' + '.join(_TOOL_CHILDREN[tool])}.\n\n"
        f"`review-pr` READS this table to size the redispatch it emits, so a stale "
        f"figure routes a correction to a tier that stalls at its cap. `config.yaml` "
        f"is the owner — update the table, not the config, unless the cap itself is "
        f"what you meant to change."
    )


def test_every_enum_member_HAS_a_sizing_row() -> None:
    """The enum and the table are two lists of the same tools; they must not diverge.

    The enum grew from three members to five in PR #124. Nothing made the table
    grow with it — it happened to be extended in the same pass, by hand.
    """
    text = PROMPT.read_text()
    m = re.search(r"dispatch_tool: <([^>]+)>", text)
    assert m, "the `dispatch_tool` enum line is no longer parseable"
    members = {t.strip().strip("`") for t in m.group(1).split("|")}
    missing = members - set(_table_rows())
    assert not missing, (
        f"these `dispatch_tool` members have no row in the sizing table: "
        f"{sorted(missing)}. The prompt tells the reviewer to size every redispatch, "
        f"and offers a tool it gives no figures for."
    )


def test_the_prose_lens_count_matches_the_table() -> None:
    """The sizing SENTENCE restates the table's lens count. It drifted; pin it.

    This is the check that would have caught PR #124's "five lenses" against a
    table saying "two" — the two figures sit three lines apart and one of them
    was edited in the very pass that left the other stale.
    """
    text = PROMPT.read_text()
    row = _table_rows()

    # The table's `build.sh` lens cell, e.g. "**two, parallel** — code-reviewer …"
    build_line = next(l for l in text.splitlines()
                      if l.startswith("| `build.sh`"))
    lens_cell = build_line.split("|")[4]
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
    declared = next((n for w, n in words.items() if re.search(rf"\*\*{w}\b", lens_cell)), None)
    assert declared is not None, (
        f"the `build.sh` lens cell no longer states a bolded count: {lens_cell!r}"
    )

    m = re.search(r"seen by (\w+) lenses rather than (\w+)", text)
    assert m, "the sizing sentence no longer states a lens comparison"
    prose_major, prose_minor = words.get(m.group(1)), words.get(m.group(2))

    assert prose_major == declared, (
        f"the sizing sentence says `build.sh` is '{m.group(1)}' lenses but the table "
        f"declares '{declared}'. THE SENTENCE IS THE SIZING RULE — a reviewer sizes "
        f"the redispatch from it, so a stale count sells review capacity that does "
        f"not exist. (Measured: it read 'five' from before the 2026-08-18 agent "
        f"consolidation, in a sentence PR #124 edited without fixing.)"
    )

    minor_cell = next(l for l in text.splitlines()
                      if l.startswith("| `build_minor.sh`")).split("|")[4]
    minor_declared = next((n for w, n in words.items()
                           if re.search(rf"\*\*{w}\b", minor_cell)), None)
    assert prose_minor == minor_declared, (
        f"the sizing sentence contrasts against '{m.group(2)}' lens(es) but the "
        f"`build_minor.sh` row declares '{minor_declared}'"
    )

    assert row  # the parser floor above ran
