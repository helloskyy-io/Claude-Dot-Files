"""A prompt may not send every dispatch to the same file in a shared directory.

THE DEFECT CLASS. `/tmp` is shared by every dispatch on the machine. A prompt that
names a FIXED path there hands two concurrent runs one file, and the loser of the
race reads or publishes the winner's content — silently, with no error, because
both writes succeed.

MEASURED, TWICE, ON ONE NIGHT:

  * `/tmp/pr-comments.json` — PRESCRIBED by `fidelity_read_and_compare`, which
    `build_refine` and `build_refine_minor` load. 19 `build-refine*` runs on
    2026-08-19/20 produced **13 overlapping pairs**. The loser reviews another
    PR's comment history believing it is its own.
  * `/tmp/claude-pr-body.md` — only an EXAMPLE, in a re-read rule, and worse for
    it: the logs show that exact path copied **verbatim 133 times across 45
    runs**. An example in a prompt is a prescription in practice. This one
    PUBLISHES — the PR gets another PR's body.

WHY THE GUARD AND NOT CARE. The commit that fixed the class reintroduced it in
the same commit. Its sweep DETECTED on the bare path and REPLACED on a backticked
one, so it found four files, changed two, and reported four — and that count went
into the commit message as a completeness claim. Two prompts derived from shell
heredocs carry ESCAPED backticks (``\\`path\\```), which the replacement could not
express. `review-pr` found the two survivors; nothing in the suite could.

WHAT COUNTS AS SAFE. A path is per-dispatch when its name carries something that
differs between concurrent runs — `${PR_NUMBER}`, `$$`, a branch, a timestamp.
`review_pr`'s own `/tmp/claude-review-pr-${PR_NUMBER}-<ts>.md` is the shape to
copy, and is why reviews were never exposed to this and can run concurrently.

WHAT THIS DOES NOT LOOK AT:
  * Paths built at runtime in Python. This reads PROMPTS — the instructions a
    model follows — not the fleet's own file handling.
  * Whether a per-dispatch name is actually unique. `${PR_NUMBER}` collides
    between two runs on the SAME PR; that is a different and much rarer race.
  * Directories other than `/tmp`. A repo-relative scratch path is not shared
    between machines and is not this class.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROMPTS = Path(__file__).resolve().parents[4] / "scripts" / "workflows" / "temporal" / \
    "modules" / "assistant"

# A `/tmp` path with a file extension. The extension is what separates a PATH
# from a bare directory mention — `/tmp` alone, or `/tmp/claude-1000/...` as a
# scratch ROOT, is not a prescription to write one named file.
TMP_PATH = re.compile(r"/tmp/[A-Za-z0-9_.${}<>-]*\.[a-z]{2,5}")

# What makes a name differ between two concurrent dispatches.
PER_DISPATCH = ("${PR_NUMBER}", "$$", "<branch>", "<ts>", "<timestamp>", "${RUN_ID}")

# A path named only to EXPLAIN the defect — prose about the old fixed form, not
# an instruction to use it. Each entry states why, because an exemption without
# a reason is how this list grows until the guard means nothing.
EXPLANATORY = {
    "/tmp/pr-comments.json":
        "named in `fidelity_read_and_compare`'s own warning about why the "
        "filename carries ${PR_NUMBER}. The INSTRUCTION beside it is already "
        "per-dispatch; removing the prose would delete the reason.",
}


def _prompts() -> list[Path]:
    found = sorted(PROMPTS.rglob("*.md"))
    assert len(found) > 20, (
        f"only {len(found)} prompts found under {PROMPTS} — the walk is wrong and "
        f"every assertion below would pass vacuously")
    return found


def _fixed_paths(text: str) -> list[str]:
    """`/tmp` paths in `text` whose names cannot differ between two dispatches."""
    return [m for m in TMP_PATH.findall(text)
            if not any(tok in m for tok in PER_DISPATCH)
            and m not in EXPLANATORY]


def test_no_prompt_SENDS_EVERY_DISPATCH_to_one_file() -> None:
    offenders = [(p.relative_to(PROMPTS), m)
                 for p in _prompts() for m in _fixed_paths(p.read_text())]
    assert not offenders, (
        "these prompts name a FIXED path in `/tmp`, which every dispatch on the "
        "machine shares:\n"
        + "\n".join(f"  {p}: {m}" for p, m in offenders)
        + "\n\nTwo concurrent runs get one file and the loser silently reads or "
          "publishes the winner's content. Carry something per-dispatch in the "
          f"name — one of {list(PER_DISPATCH)}. `review_pr`'s "
          "`/tmp/claude-review-pr-${PR_NUMBER}-<ts>.md` is the shape to copy.\n"
          "If the path is only being DESCRIBED, add it to EXPLANATORY with a reason."
    )


def test_THE_WALK_HAS_A_POPULATION_and_the_detector_SEES_BOTH_BACKTICK_FORMS() -> None:
    """POSITIVE CONTROL, and the escaped form is first because it is what escaped.

    The sweep this guard replaces detected on the bare path and replaced on a
    backticked one, so two heredoc-derived prompts carrying ``\\`path\\``` were
    counted as fixed and left unfixed. A control that only exercised the plain
    form would reproduce exactly that blind spot.
    """
    cases = {
        "escaped backticks": r"revising a /tmp staging file (e.g. \`/tmp/claude-pr-body.md\`) later",
        # NOT a name from EXPLANATORY: the exemption list filters the detector,
        # so a control reusing an exempted name tests the exemption rather than
        # the shape. Caught by this control failing on its first run.
        "plain backticks": "write it to `/tmp/some-fetch.json`, then read it",
        "bare": "gh pr view > /tmp/some-thing.json",
        "in a command": "gh api ... > /tmp/claude-review.md && cat /tmp/claude-review.md",
    }
    for name, src in cases.items():
        assert _fixed_paths(src), f"the detector missed the {name} form: {src!r}"

    for name, src in {
        "pr-numbered": "write to `/tmp/claude-review-pr-${PR_NUMBER}-<ts>.md`",
        "branch-named": r"revising \`/tmp/claude-pr-body-<branch>.md\` several turns later",
        "pid": "use /tmp/pr-$$.json",
        "a scratch ROOT, not a file": "your scratchpad is /tmp/claude-1000/session/scratchpad",
    }.items():
        assert not _fixed_paths(src), (
            f"the detector fires on {name}, which is SAFE — it would fail a "
            f"correct tree and teach the next reader to delete it: {src!r}")


@pytest.mark.parametrize("path,reason", sorted(EXPLANATORY.items()))
def test_every_EXEMPTION_is_still_present_and_still_explanatory(path: str, reason: str) -> None:
    """An exemption for a path nobody mentions any more is a lie that survives.

    This list may only shrink. If the prose that earned the exemption is gone,
    the entry goes with it — otherwise the next fixed path with that name is
    exempt by inheritance.
    """
    assert any(path in p.read_text() for p in _prompts()), (
        f"{path} is exempted in EXPLANATORY but appears in no prompt. Remove the "
        f"entry — its stated reason was: {reason}")
