"""RECURRENCE — deciding that a finding is one somebody already filed.

`Tracked Items Standard` §3.1 says what to do once you know: increment `count`,
append a dated line, do not open a second item. **It does not say how you know**,
and that is the whole problem this module exists for. Incrementing is trivial;
MATCHING is the judgement.

WHY THIS IS NOT A MATCHER, AND WILL NOT BECOME ONE. The corpus's own rule is that
placement is decided **from the item's body, never its title** — titles state a
CONSEQUENCE (§3), and consequences read alike across genuinely different items.
Measured upstream the day that rule landed: a title-driven triage nominated four
issues for re-filing and **one of four survived reading the bodies.** An
automatic merge keyed on titles would reproduce that error and bury a real
finding under someone else's, which is strictly worse than a duplicate: a
duplicate costs a triage ruling, a wrong merge costs the finding.

**So this ranks and the filer rules.** It answers *"which few of these hundred
items are worth reading before you file?"* and stops there.

WHAT THE STORES ACTUALLY GIVE US, measured 2026-08-26 rather than assumed:

  * `standards` — `target` + `anchor` on 7 of 7. A REAL key: two amendments to
    the same anchor of the same standard are the same amendment, near enough
    that the filer should have to argue otherwise.
  * `candidates` — `component` on 43 of 121. Narrows when present and is absent
    more often than not, so it is a filter and never a key.
  * `issues` — `repo` on 3 of 3, and all three the same repo. Discriminates
    nothing today.
  * `operations` — human-only (§1.2). Nothing here applies to it, and no
    autonomous filer reaches it.

That distribution is why scoring exists at all: for three stores out of four
there is no field that identifies an item, so the text has to carry it — and the
text is ranked, not trusted.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from . import tracked_items as ti

#: Words that appear everywhere in this corpus and identify nothing. Deliberately
#: SHORT: a long stop-list is a second thing to maintain, and rare-term weighting
#: below already drives common words toward zero on its own. These are only here
#: because they are common enough to cost tokens in the rendered block.
_STOP = frozenset("""
a an the and or but if then than that this these those is are was were be been
being it its of to in on at by for with from as not no nor so such only own same
too very can will just should now what which who whom when where why how all any
both each few more most other some
""".split())

_WORD = re.compile(r"[a-z][a-z0-9_-]{2,}")


@dataclass(frozen=True)
class Match:
    """One existing item worth reading before filing, and WHY it surfaced."""

    id: str
    title: str
    path: Path
    score: float
    #: `key` when a structured field matched exactly; `text` when only the
    #: wording did. The distinction is the whole of how far a filer should trust
    #: it, so it travels with the result rather than being inferred from score.
    basis: str


def _terms(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP}


def _document_frequency(docs: list[set[str]]) -> dict[str, int]:
    df: dict[str, int] = {}
    for terms in docs:
        for term in terms:
            df[term] = df.get(term, 0) + 1
    return df


def similar(root: Path, store: ti.Store, text: str, *,
            key: dict[str, str] | None = None, limit: int = 5) -> list[Match]:
    """Existing items worth reading before filing `text` into `store`.

    `key` is the structured fields of the item being filed — `target`/`anchor`
    for a standards candidate, `component` for a candidate. An EXACT match on a
    store's identifying key is reported as `basis="key"` and sorts above
    everything, because that is the only signal here strong enough to argue
    from. Everything else is `basis="text"` and is a reading list.

    SCORED ON RARE TERMS, NOT ON OVERLAP. Two items sharing "the workflow does
    not" share nothing; two sharing "heartbeat" probably share a subject. Each
    shared term is weighted by the inverse of how many items in the store carry
    it, so a word that appears in a hundred items contributes almost nothing and
    a word that appears in two contributes most of the score. This is ordinary
    IDF and it is written out rather than imported because the whole scorer is
    six lines and a dependency here would be the larger cost.

    RETURNS AN EMPTY LIST FOR AN EMPTY STORE, which is the honest answer and not
    a failure — the first item filed into a store has nothing to recur against.
    """
    directory = root / store.name
    if not directory.is_dir():
        return []

    items: list[tuple[str, dict[str, str], str, Path]] = []
    for path in sorted(directory.glob("*.md")):
        try:
            fields, body = ti.parse(path)
        except ValueError:
            # A FILE THIS CANNOT READ IS NOT THIS FUNCTION'S TO RAISE ON.
            # `candidate_rows` already refuses the whole store when an item will
            # not parse, loudly and by name. Raising here too would turn a
            # convenience into a second gate with the same message, and skipping
            # it costs only that one item's chance to be recommended.
            continue
        items.append((fields.get("id", path.stem), fields,
                      f"{fields.get('title', '')}\n{body}", path))
    if not items:
        return []

    docs = [_terms(t) for _, _, t, _ in items]
    df = _document_frequency(docs)
    total = len(items)
    mine = _terms(text)

    key = {k: v.strip() for k, v in (key or {}).items() if v and v.strip()}
    identifying = _IDENTIFYING.get(store.name, ())

    out: list[Match] = []
    for (cid, fields, _, path), terms in zip(items, docs):
        shared = mine & terms
        score = sum(math.log(1 + total / df[t]) for t in shared)
        basis = "text"
        if identifying and all(
                fields.get(f, "").strip() == key.get(f, "\0") for f in identifying):
            basis = "key"
        if basis == "key" or score > 0:
            out.append(Match(cid, fields.get("title", ""), path, score, basis))

    out.sort(key=lambda m: (m.basis != "key", -m.score))
    return out[:limit]


#: The fields that, matching EXACTLY and TOGETHER, mean "this is the same item".
#: Only `standards` has one — §4.1 requires a named target and an actionable
#: anchor, so two items sharing both are two proposals to change one place. No
#: other store carries a field that identifies rather than merely narrows, and
#: inventing one here would manufacture confidence the data does not support.
_IDENTIFYING: dict[str, tuple[str, ...]] = {
    "standards": ("target", "anchor"),
}


def recurrence_block(root: Path, store: ti.Store, text: str, *,
                     key: dict[str, str] | None = None, limit: int = 5) -> str:
    """What a filer reads BEFORE filing. Rendered for a prompt, not for a human.

    STATES THE RULING IT WANTS AND THE ONE IT REFUSES. The block never says
    "this is a duplicate" — it says which items to read and what the answer
    changes. A prompt that reported a match would get one, because a model
    handed a confident-looking answer rarely overturns it.
    """
    hits = similar(root, store, text, key=key, limit=limit)
    if not hits:
        return (f"**`tracked/{store.name}/` holds nothing resembling this.** File it "
                f"as a new item.")

    exact = [m for m in hits if m.basis == "key"]
    lines = "\n".join(
        f"- `{m.id}` — {m.title}"
        + ("  ← **same `target` and `anchor`**" if m.basis == "key" else "")
        for m in hits)

    lead = (
        "**An existing item names the SAME standard and the SAME anchor.** Two "
        "proposals to change one place are one proposal: read it, and unless it "
        "is arguing something genuinely different, this is a RECURRENCE.\n\n"
        if exact else
        "**These are the items whose wording is closest to yours — a reading "
        "list, not a verdict.** They were ranked on rare shared terms, which "
        "surfaces subjects rather than phrasing.\n\n")

    return (
        f"{lead}{lines}\n\n"
        f"**Decide from the BODY, never the title.** Titles state a CONSEQUENCE "
        f"and therefore read alike across genuinely different items — measured "
        f"upstream, a title-driven pass nominated four for merging and one of "
        f"four survived reading them.\n\n"
        f"**If it IS the same item:** increment its `count`, append a dated line "
        f"under `## Recurrences` naming this run, and file nothing new (§3.1). "
        f"**If it is not:** file yours and say in one line which you checked and "
        f"why it differs. **A duplicate costs one triage ruling; a wrong merge "
        f"buries a finding under someone else's — so when they are close and you "
        f"cannot tell, FILE.**")
