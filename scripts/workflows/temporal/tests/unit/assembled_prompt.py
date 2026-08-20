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
    assert the minor cycle is four stages. Promoting that block took the count
    to three.

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

  * **It is not `render()`.** It resolves FRAGMENTS only, by stem. Runtime
    values (`${PR_NUMBER}`, `${DESCRIPTION}`, `${RESEARCH_DIR}`) are left alone
    — a guard reading assembled text must still expect them, and a guard that
    wants a real dispatch should drive the entrypoint with a captured
    `run_claude` the way `test_promoted_fragments_render_for_every_consumer`
    does. This is the cheap middle: file-scoped assertions that survive a
    promotion.
  * **A CHILD'S OWN PROMPT FILE WINS OVER THE POOL, and this is not a nicety —
    resolving by stem alone was WRONG on a child in this tree.** `${RULES}` is
    supplied from the pool by every build child and from its OWN
    directory by `plan_revision` (`plan_revision_workflow.py:134`, the PLANNING
    ruleset — do not modify code, only docs). Pool-only resolution spliced the
    BUILD ruleset into a planning prompt, so `assembled()` returned a string no
    dispatch has ever produced, on the one child whose parity is this suite's
    oldest assertion. It went unnoticed because the parity check expands both
    sides and the error cancelled; the next assertion written over it would not
    have been so lucky. `local` mirrors what the workflow's values dict does,
    and `test_a_CHILD_S_OWN_FILE_WINS_over_a_pool_fragment_of_the_same_stem`
    holds it.
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
    """`path`'s text with every fragment placeholder replaced by its fragment.

    `path`'s OWN directory is searched before the pool, because that is the
    order the workflow's values dict resolves in — see the module docstring.
    """
    return expand(path.read_text(encoding="utf-8"), local=path.parent)


def expand(text: str, *, local: Path | None = None, pool: Path | None = None) -> str:
    """The predicate half, over a string, so a control can drive it directly.

    `local` is the consuming child's own `prompts/` directory and is consulted
    FIRST; `pool` defaults to the shared pool and exists so a control can drive
    the resolver without writing into a directory whose contents ship to a model.
    """
    pool = SHARED if pool is None else pool
    for _ in range(10):
        before = text
        for name in set(_PLACEHOLDER.findall(text)):
            fragment = _resolve(name, local, pool)
            if fragment is not None:
                text = text.replace("${" + name + "}", fragment.read_text(encoding="utf-8"))
        if text == before:
            return text
    raise ValueError(
        "pool-fragment expansion did not converge — a fragment references itself"
    )


def _resolve(name: str, local: Path | None, pool: Path) -> Path | None:
    """The child's own file, then the pool, then nothing (a runtime value)."""
    for directory in (local, pool):
        if directory is None:
            continue
        candidate = directory / f"{name.lower()}.md"
        if candidate.is_file():
            return candidate
    return None
