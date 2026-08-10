"""A measurement figure lives in ONE place, and every other mention cites it.

WHY THIS EXISTS RATHER THAN A SIXTH ROUND OF CORRECTIONS. Four consecutive passes
over the Memory Management Framework's Phase 5 each headlined the same defect —
a figure corrected at its source and left standing in a summary — and each fixed
the instances it could see. The frontier moved every time and never shrank:

  * the draft pass wrote *"a summary line is a copy, and a correction that lands
    in the source without landing in its copies has not landed"* in its own
    reflection, and violated it five times in the same PR;
  * the refine pass fixed those five and re-introduced it wherever ITS OWN
    corrections had copies;
  * the review pass found four more, including two in the roadmap — the file a
    later run reads to learn what is proven — and one where a document
    contradicted itself twelve lines apart;
  * a re-run of the replay one day later returned different figures again,
    because the archive is a moving denominator by construction.

Enumerating instances does not converge. Changing what the check keys on does.
`candidates.md` C-050 already names this mechanism — *"in every case the
contents had a gate and the count did not, so each divergence was invisible to a
green suite"* — and this is that gate for the one corpus where the count decides
whether a stopping predicate is allowed to gate anything.

THE RULE IS NARROW ON PURPOSE: cite, do not restate. It does not ask any prose to
be correct, which no test can check. It asks that a figure with a denominator
appear only where the measurement is taken, so that re-taking the measurement is
a one-file edit and every other mention is a pointer that cannot go stale.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MMF = REPO_ROOT / "docs" / "development" / "memory-management-framework"
PHASE5 = MMF / "phase5_convergence_stopping.md"
ROADMAP = MMF / "roadmap.md"

# A figure carrying a denominator, or one stated in the units this measurement is
# quoted in. Deliberately syntactic: the defect is not any particular number, it
# is the SHAPE "a count someone else derived, re-typed where a reader will meet
# it first". A new figure in a new spelling is caught by the same pattern.
FIGURE = re.compile(
    r"\b\d+ of \d+\b"                     # 2 of 12, 0 of 0, 300 of 300
    r"|~\s*\d+\s*%"                       # ~20%
    r"|\b\d+ (?:mutations?|caught|surviving|survivors?)\b"
    r"|\b~?\d+ (?:assessable|scorable|archived) \w+",
    re.IGNORECASE,
)

# The one place a Phase 5 figure may be written. Everything else cites it.
SOURCE_HEADING = "## §Measurement"


def _phase5_outside_measurement() -> list[tuple[int, str]]:
    lines = PHASE5.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith(SOURCE_HEADING))
    end = next(i for i in range(start + 1, len(lines))
               if lines[i].startswith("## "))
    return [(i + 1, line) for i, line in enumerate(lines)
            if not start <= i < end]


def _roadmap_phase5_lines() -> list[tuple[int, str]]:
    """Roadmap lines that speak about Phase 5.

    Scoped by mention rather than by section, because the roadmap's STATUS
    PARAGRAPH is outside the Phase 5 section and carried a superseded Phase 5
    figure for a full day — a section-scoped check would have read clean. Other
    phases' figures are untouched by this gate; they have their own sources.
    """
    lines = ROADMAP.read_text(encoding="utf-8").splitlines()
    return [(i + 1, line) for i, line in enumerate(lines)
            if "Phase 5" in line or "phase5_convergence_stopping" in line]


def test_phase5_states_its_figures_in_exactly_one_section() -> None:
    """§Measurement is the source; the rest of the document points at it.

    THE FAILURE THIS PREVENTS IS NOT UNTIDINESS. `phase5:92` withdrew an
    early-fire confidence interval and stated its own purpose in doing so —
    *"stated here so a later run does not re-derive a bound from the circular
    counter"* — while two checklist lines in the SAME FILE still quoted the
    withdrawn interval and the withdrawn denominator. A resuming engineer reads
    the implementation checklist, not the measurement section, so the document's
    stated defence against re-derivation was defeated by the document.
    """
    assert PHASE5.exists(), f"the phase doc moved: {PHASE5}"
    offenders = [
        f"{PHASE5.name}:{number} — {sorted(set(FIGURE.findall(line)))}"
        for number, line in _phase5_outside_measurement()
        if FIGURE.search(line)
    ]
    assert not offenders, (
        "a measurement figure is stated outside § Measurement: "
        + "; ".join(offenders)
        + ". Replace it with a citation to § Measurement. That is the only form "
          "of the statement that survives the next re-measurement — and the "
          "archive this phase measures grows with every reviewed PR, so the "
          "next re-measurement is not hypothetical."
    )


def test_the_roadmap_cites_phase5s_figures_and_never_restates_them() -> None:
    """The roadmap is what a later run reads to learn what is proven.

    Its two Phase 5 checkbox lines stated, as this phase's completion evidence,
    an early-fire rate of zero and a clean mutation sweep — the first being the
    exact figure requirement 5 needs to license replacing the loop-back bound,
    and both retracted by the phase doc in the same PR. A reader of the roadmap
    concluded the guard evidence was complete and the signal safe to gate on.
    """
    assert ROADMAP.exists(), f"the roadmap moved: {ROADMAP}"
    scoped = _roadmap_phase5_lines()
    assert scoped, "no Phase 5 lines found in the roadmap — the gate read nothing"
    offenders = [
        f"{ROADMAP.name}:{number} — {sorted(set(FIGURE.findall(line)))}"
        for number, line in scoped
        if FIGURE.search(line)
    ]
    assert not offenders, (
        "the roadmap restates a Phase 5 measurement figure: "
        + "; ".join(offenders)
        + ". Cite `phase5_convergence_stopping.md § Measurement` instead. The "
          "roadmap is the phase index a later dispatch reads first, so a "
          "superseded number here is the one most likely to be acted on."
    )


def test_the_gate_can_actually_SEE_a_restated_figure() -> None:
    """The two assertions above pass trivially if the pattern matches nothing.

    A gate reporting a clean corpus and a gate reading nothing are
    indistinguishable from their result, and this repo has shipped the second
    while believing the first. This pins the pattern against the exact strings
    the four passes each had to correct by hand.
    """
    for restatement in (
        "would have fired 2 of 12 assessable blocks, **0 early**",
        "**22 mutations, 22 caught, 0 surviving**",
        "a true early-fire rate up to ~20%",
        "roughly 60 assessable blocks, a few months of ordinary operation",
        "0 of 13 pairs drop an id",
    ):
        assert FIGURE.search(restatement), (
            f"the figure pattern no longer matches {restatement!r} — a real "
            f"restatement that four passes each corrected by hand. The gate "
            f"would report the corpus clean while reading nothing."
        )
    # And it does not fire on prose that merely contains digits, so the rule is
    # "cite the figure", not "never write a number".
    for benign in (
        "see [Phase 5 § Measurement](phase5_convergence_stopping.md)",
        "five modes, four checks",
        "`MAX_LOOPS = 1` is already tight enough",
    ):
        assert not FIGURE.search(benign), (
            f"the figure pattern fires on {benign!r}, which states no "
            f"measurement — a gate that cannot be satisfied gets disabled"
        )
