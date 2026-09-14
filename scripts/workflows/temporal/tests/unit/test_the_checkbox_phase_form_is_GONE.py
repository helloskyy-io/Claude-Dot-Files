"""The retired checkbox-list phase entry appears in no roadmap this tooling reads.

`documentation_standard.md` rule 8 gives a phase entry ONE shape — a heading with
its status marker and an `**Implementation:**` line — and forbids the checkbox
list it replaced. Every reader of phase entries keys on the heading shape alone
(the arm that accepted the list was deleted when the corpus finished converting:
MDC checkbox 0 / implementation 121 / inline 9 at `1a8e785`; SkyyNet 0).

WHY A GATE AND NOT JUST A DELETION. A roadmap that regressed to the list would
not fail loudly — `phase_sizing` would count no phases, `sizing_block` would
render *"lists no phases"* and withhold the `(~Nh total · ~Nh to-do)` template,
and the run would copy whatever shape its neighbours carry. That is the exact
chain that put `~128h sized ·` on MDC PR #171. The pattern that used to READ the
form now only DETECTS it, here, against the live corpus.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from planning_corpus import PLANNING_ROOT, require_planning_corpus  # noqa: E402
from modules.assistant.plan import plan_activities as A  # noqa: E402


def _roadmaps() -> list[Path]:
    dev = PLANNING_ROOT / "development"
    return sorted({p for pat in ("*/roadmap.md", "*/*/roadmap.md") for p in dev.glob(pat)})


def test_the_checkbox_phase_form_is_GONE() -> None:
    require_planning_corpus()
    roadmaps = _roadmaps()
    assert len(roadmaps) >= 4, f"vacuity floor: found {len(roadmaps)} roadmaps"

    regressed = []
    for path in roadmaps:
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        for n, line in enumerate(lines, 1):
            if A._CHECKBOX_PHASE_ENTRY.match(line):
                regressed.append(f"{path.relative_to(PLANNING_ROOT)}:{n}: {line.strip()[:80]}")
    assert not regressed, (
        "a roadmap carries the retired checkbox-list phase entry, which no reader "
        "accepts — convert it to rule 8's heading form:\n  " + "\n  ".join(regressed))


def test_the_detector_STILL_MATCHES_the_retired_form() -> None:
    """Positive control: a green gate over a pattern that matches nothing is no gate."""
    line = "- [x] **Family alignment** ([phase2_family_alignment.md](./phase2_family_alignment.md)) — done"
    assert A._CHECKBOX_PHASE_ENTRY.match(line)
    assert not A._CHECKBOX_PHASE_ENTRY.match("- [x] run the suite before pushing")
    assert not A._CHECKBOX_PHASE_ENTRY.match(
        "- [ ] **`review-runs.sh` keeps working** until [Phase 6](phase6_the_rest.md) lands"), (
        "a requirement that mentions a phase doc is not a phase entry")
