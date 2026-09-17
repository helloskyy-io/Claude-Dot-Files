"""The fence delimiter, and the one walk that answers "is this line fenced".

**A leaf module on purpose.** It imports nothing from this package, so every
walker can reach it — which is the whole point. The delimiter used to live in
:mod:`~.roadmaps`, and :mod:`~.sprints` could not import it from there because
:mod:`~.roadmaps` imports :mod:`~.sprints`; so ``sprints`` spelled its own
``startswith`` toggle and was the one walk that shared neither the pattern nor
the length rule with its four siblings. A shared answer that half the callers
are structurally barred from asking is not a shared answer.

The same wall is why :func:`~.discovery.is_phase_shaped` reads a fenced heading
as a real one (``MDC-Master-Planning#229``): ``roadmaps`` imports ``discovery``
too. This module is below both, so the blocker that item names is gone —
closing it is still that item's work, and its behaviour is unchanged here.
"""

from __future__ import annotations

import re


#: A fenced code block delimiter, with its RUN LENGTH captured. Tracked so a
#: roadmap that SHOWS the format in a fence — this component's own roadmap
#: does — is not read as using it.
#:
#: **LENGTH-AWARE, and that is what makes the answer shared rather than merely
#: co-located.** A run closes only a block opened by the same character with a
#: run no longer than its own, per CommonMark. Read length-blind, a four-
#: backtick block wrapping a three-backtick example is CLOSED by the inner
#: delimiter, and every line after it is read as prose. A corpus that nests a
#: ```bash example inside a ````markdown quotation — and says so in its own
#: text — is the case, and it is common wherever a document quotes another.
#: Length-blind, the ``` ```bash ``` at ``:714`` shut it, line ``:715`` — a
#: shell comment — became an unfenced :data:`HEADING_RE` match, and
#: :func:`~.amendments._section_bounds` truncated the amendment section 49
#: lines early: **six explicitly-deferred human rulings reported as zero owed.**
#:
#: The info-string rules are deliberately NOT applied (an opener's info string
#: may not contain backticks; a closing fence carries none). They are a larger
#: change: applying them terminates all four currently-unterminated corpus
#: files, which moves the population behind
#: :data:`~.model.UNPARSED_LINE`. The length rule alone is what is measured
#: safe.
FENCE_RE = re.compile(r"^\s*(?P<delimiter>`{3,}|~{3,})")


def advance_fence(line: str, open_delimiter: str | None) -> tuple[str | None, bool]:
    """``(the delimiter open after this line, whether this line is a delimiter)``.

    **The single answer to "is this a fence boundary", and every walk in this
    package asks it.** Five walks used to spell their own toggle — four around
    :data:`FENCE_RE` and one around a bare ``startswith`` — and all five were
    length-blind identically, which reads as agreement and is not. A shared
    mask is not enough on its own: the walks that must know WHAT a fence
    swallowed cannot use a boolean mask, so the thing they share has to be the
    delimiter decision itself.

    ``True`` in the second slot means the line OPENED or CLOSED a block. A run
    that is shorter than the open delimiter, or of the other character, is
    CONTENT — that is the nesting case, and it is why the second slot is not
    simply ``FENCE_RE.match(line) is not None``.

    A caller building a per-line mask wants ``is_delimiter or was_open``; a
    caller reporting a loss wants the three cases apart.
    """
    match = FENCE_RE.match(line)
    delimiter = match.group("delimiter") if match else None
    if open_delimiter is None:
        if delimiter is None:
            return None, False
        return delimiter, True
    if (
        delimiter is not None
        and delimiter[0] == open_delimiter[0]
        and len(delimiter) >= len(open_delimiter)
    ):
        return None, True
    return open_delimiter, False


def fenced_mask(lines: list[str]) -> list[bool]:
    """Per line: ``True`` where the line is a fence delimiter or inside a fence.

    **One walk, every reader.** :data:`FENCE_RE` was already the one delimiter,
    and every walker still spelled its own loop around it — which is how the
    guard reached one of the readers of a ``roadmap.md`` and not the others.
    The delimiter line itself is masked: it is not content, and a walker that
    reads it as content sees ```` ```markdown ```` as a heading.

    Callers that need to know WHAT a fence swallowed — the unterminated-fence
    findings in :mod:`~.dependencies` and :mod:`~.measurements` — keep their own
    walk, because the loss is theirs to report and a boolean mask cannot carry
    it. Neither compiles a second delimiter.
    """
    mask: list[bool] = []
    open_delimiter: str | None = None
    for line in lines:
        was_open = open_delimiter is not None
        open_delimiter, is_delimiter = advance_fence(line, open_delimiter)
        mask.append(is_delimiter or was_open)
    return mask
