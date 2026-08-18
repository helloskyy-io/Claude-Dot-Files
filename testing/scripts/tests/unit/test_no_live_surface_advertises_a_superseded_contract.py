"""A workflow's contract is stated on several surfaces; a change must reach all.

THE MOST RECURRENT FINDING CLASS IN THE CORPUS, measured rather than felt. The
1,092 `pr_review:` findings across 23 PRs were classified on 2026-08-18; the
largest class — *a document still describes a contract the code has replaced* —
is **33 findings across 12 PRs**, ahead of every other shape. Nothing was
watching it, because a stale sentence and a current one are the same file type.

WHAT IT COSTS, ON THE RUN THAT PRODUCED THIS GATE. PR #105 changed what
`research-minor` IS: a TOPIC rather than one question, and a cycle that writes a
synthesis. It updated the prompt. It missed the CLI `--help`, the module
docstring, the `.sh` header comment and the operator guide — four surfaces
stating the replaced contract, on `main`, for a day. The guide row is the one an
operator READS WHEN CHOOSING AN INSTRUMENT, so the stale text actively pointed at
the mis-scoping the PR existed to fix, and PR #106 was held on it.

WHY A GATE AND NOT A SWEEP. It was swept three times. I swept the CLI by hand; a
research run swept the module docstring and the `.sh`; `review-pr` then found the
guide. **Three passes, three surfaces, and the finder each time was whoever
happened to look** — which is the definition of a control that does not exist.

SCOPE, AND IT IS DELIBERATELY NARROW. Only surfaces that TELL SOMEONE WHAT A TOOL
DOES are scanned: the operator guide, the CLI entrypoints, and the prompt files a
run is handed. Deliberately NOT scanned:

  * `tests/` — a test that pins a retired string is how the string stays retired
  * workflow module docstrings — they explain WHY a contract changed, and quoting
    the old wording is the explanation, not a claim
  * `docs/standards/architecture/research/`, `cpi-decisions.md`, `candidates.md`
    — append-only records, dated, true as of their date
  * the research pools — a paper is evidence stamped with `Last validated`

That split is the operator's own rule for a vocabulary sweep, unchanged: *rename
it where it is still binding; leave it where it is a record.*

HOW TO ADD ONE. A row per superseded contract: the phrase, and what replaced it.
The row is what makes the NEXT contract change a trade rather than a discovery.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]

# The surfaces that answer "what does this tool do" for a human or a model.
LIVE_SURFACES = (
    ROOT / "docs" / "guide",
    ROOT / "scripts" / "workflows" / "temporal" / "scripts",
    ROOT / "scripts" / "workflows" / "temporal" / "modules",
)

# Under `modules/`, only the prompt files — a module's own docstring is allowed
# to quote a retired contract while explaining its replacement, and several now do.
def _is_scanned(p: Path) -> bool:
    if "prompts" in p.parts:
        return p.suffix == ".md"
    if p.parts[-2:-1] == ("scripts",):
        return p.suffix in {".py", ".sh"}
    return "guide" in p.parts and p.suffix == ".md"


# phrase (regex, case-insensitive) -> what replaced it, shown on failure.
#
# MATCH THE CLAIM, NEVER THE WORDS. A bare `no synthesis` fails on two innocent
# lines — `plan_feature.md`'s *"if the pool is EMPTY or has no synthesis, say so"*
# and `write_minor.md`'s explanation of why one is now written. Both describe a
# real runtime CONDITION a pool can be in; neither asserts a contract. The gate
# found both on its own first run, which is the whole argument for the
# can-actually-FAIL control below: an over-matching pattern and a stale document
# are indistinguishable from a red bar.
SUPERSEDED: dict[str, str] = {
    r"(one paper|minor cycle|no topic list|no fan-?out)[^.\n]{0,40}no synthesis"
    r"|no synthesis exists":
        "research-minor HAS written a synthesis since 2026-08-17 (write_minor.md "
        "Stage 3). Say 'ONE topic, ONE paper, plus the synthesis a planner reads'.",
    r"research ONE question|ONE question as ONE paper|research one question":
        "research-minor takes a TOPIC, not a question — PR #105. A topic spans "
        "several concerns and the paper covers them.",
}


def _files() -> list[Path]:
    out = []
    for root in LIVE_SURFACES:
        out += [p for p in root.rglob("*") if p.is_file() and _is_scanned(p)]
    assert len(out) > 20, (
        f"only {len(out)} live surfaces found — the glob is wrong, and a gate that "
        f"scans nothing passes silently"
    )
    return sorted(out)


@pytest.mark.parametrize("pattern", sorted(SUPERSEDED), ids=lambda s: s[:34])
def test_no_live_surface_states_a_superseded_contract(pattern: str) -> None:
    rx = re.compile(pattern, re.I)
    hits = []
    for p in _files():
        for n, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
            if rx.search(line):
                hits.append(f"{p.relative_to(ROOT)}:{n}  {line.strip()[:96]}")
    assert not hits, (
        f"a live surface still states a superseded contract.\n\n"
        f"  REPLACED BY: {SUPERSEDED[pattern]}\n\n  "
        + "\n  ".join(hits)
        + "\n\nThese surfaces are what an operator reads when choosing an instrument "
        "and what a run is handed as its contract. If the text is a RECORD rather "
        "than a claim, it does not belong on one of these surfaces — move it to the "
        "commit message, a module docstring, or the decisions log."
    )


def test_the_gate_can_actually_FAIL(tmp_path: Path) -> None:
    """A control whose failing path has never run is not a control.

    The real tree can only ever exercise the passing case once it is clean, which
    is exactly when a broken predicate stops being visible — the failure the
    retired-vocabulary gate's own docstring records, four passes running.
    """
    rx = next(re.compile(p, re.I) for p in SUPERSEDED if "no synthesis" in p)
    for must in ("ONE paper, no topic list, no synthesis",
                 "MINOR CYCLE — one paper, no synthesis. The paper IS the deliverable.",
                 "`SKIPPED — minor cycle, no synthesis exists`"):
        assert rx.search(must), (
            f"the pattern no longer matches {must!r} — the exact text this gate was "
            f"written to catch. It has been narrowed or escaped into inertness."
        )
    for innocent in ("If the pool is EMPTY or has no synthesis, say so plainly",
                     "a pool with two minor papers and no synthesis has nothing "
                     "rolling them up",
                     "ONE topic, ONE paper, plus the synthesis a planner reads"):
        assert not rx.search(innocent), (
            f"the pattern over-matches {innocent!r}. That line states a runtime "
            f"CONDITION, not a contract — a gate that reds on it teaches the next "
            f"author to weaken the gate."
        )
