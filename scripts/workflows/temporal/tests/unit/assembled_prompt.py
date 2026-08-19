"""What the MODEL receives, not what a prompt file contains.

WHY THIS EXISTS, and it is a defect class rather than a convenience. A guard
that reads a child's `prompts/*.md` and asserts on its text is asserting about
an artifact the model never sees whole. The moment a block is PROMOTED to
`modules/assistant/prompts/`, the text leaves the file and the guard goes quiet
— not because the instruction is gone, but because it moved. Two guards did
exactly that when this module was written:

  * `test_plan_revision_v1_parity` re-extracts the V1 heredocs and asserts every
    reference line is still present in the shipped file. Promoting four blocks
    out of `stages_1_to_5.md` made it report LOST CONTENT for text that had not
    been lost.
  * `test_research_minor` counts `## Stage` headings in `write_minor.md` to
    assert the minor cycle is four stages. Promoting the Stage-1 block took the
    count to three.

Both were RIGHT to fail — their predicate was "the file still says this" and the
file no longer did. Both were asking the WRONG QUESTION: neither cares where the
sentence is stored, both care that the dispatched prompt carries it.

THE DIRECTION OF THE RISK IS WHY THIS IS NOT COSMETIC. A promotion silently
narrows every file-scoped guard in the tree, and it does so by making them PASS
less rather than fail — the failure above was loud only because the promotion
happened to remove whole reference lines. A promotion that moves text a guard
merely COUNTS, or greps for loosely, produces no failure at all and leaves a
guard that has stopped watching. This is the same shape as C-108's second face
(deleting from the pool is invisible), one step earlier in the lifecycle.

WHAT THIS DOES NOT DO, so it is not over-read:

  * **It is not `render()`.** It resolves POOL fragments only, by stem. Runtime
    values (`${PR_NUMBER}`, `${DESCRIPTION}`, `${RESEARCH_DIR}`) are left alone
    — a guard reading assembled text must still expect them, and a guard that
    wants a real dispatch should drive the entrypoint with a captured
    `run_claude` the way `test_promoted_fragments_render_for_every_consumer`
    does. This is the cheap middle: file-scoped assertions that survive a
    promotion.
  * **It resolves to a FIXED POINT, bounded.** A pool fragment may itself carry a
    pool placeholder. Ten rounds, then it raises rather than spinning — the same
    bound and the same reason as `render()`.
  * **It does not verify a consumer SUPPLIES the fragment.** A file can name
    `${FOO}` while its workflow never passes `FOO`; that is
    `test_promoted_fragments_render_for_every_consumer`'s job and this module
    would happily expand it anyway.
"""
from __future__ import annotations

import re
from pathlib import Path

SHARED = (Path(__file__).resolve().parents[2] / "modules" / "assistant" / "prompts")

_PLACEHOLDER = re.compile(r"\$\{([A-Z_][A-Z_0-9]*)\}")


def assembled(path: Path) -> str:
    """`path`'s text with every POOL placeholder replaced by its fragment."""
    return expand(path.read_text(encoding="utf-8"))


def expand(text: str) -> str:
    """The predicate half, over a string, so a control can drive it directly."""
    for _ in range(10):
        before = text
        for name in set(_PLACEHOLDER.findall(text)):
            fragment = SHARED / f"{name.lower()}.md"
            if fragment.is_file():
                text = text.replace("${" + name + "}", fragment.read_text(encoding="utf-8"))
        if text == before:
            return text
    raise ValueError(
        "pool-fragment expansion did not converge — a fragment references itself"
    )
