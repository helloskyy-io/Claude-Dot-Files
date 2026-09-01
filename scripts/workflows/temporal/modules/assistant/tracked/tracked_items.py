"""The Tracked Items contract, in code — four stores, one shape.

THIS MODULE IS THE CONSUMER SIDE OF A VERSIONED CONTRACT IT DOES NOT OWN.
`/opt/skyy-net/skyynet-master-planning/standards/documentation/tracked_items_standard.md` §2 and §3 are the
contract; that document is its owner and this conforms to it. The standard is
VENDORED, so a disagreement is resolved upstream and re-vendored, never by
editing either side here.

WHY ONE MODULE FOR FOUR STORES RATHER THAN FOUR FILERS. The stores differ in
exactly two ways — their prefix and their per-store fields (§4) — and agree on
everything else: identity, the six-field core, the recurrence rule, the
placement order. Four filers would drift on the agreeing 90%, and the drift
would be invisible because each store is only read by its own consumer. One
table plus one writer makes uniformity structural rather than aspirational,
which is what the operator asked for on 2026-08-26: the four stores must "match
and look uniform in design", not merely share a directory.

WHAT THIS DELIBERATELY DOES NOT DO:

  * It does not RULE. `decision`, `ready` and `ratification` are triage and
    operator outputs (§4); nothing here writes them. A filer files.
  * It does not decide PLACEMENT. §6 orders four options and a tracked store is
    the LAST — resolve-now, a phase checkbox and expanding an existing item all
    come first. This module is what you call once that decision is already made
    against you, and calling it earlier is the failure §0 describes.
  * It does not delete. Ids are immutable and never reused, terminal state
    included (§2), so a resolved item keeps its file.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# §7. Bumped upstream when §2 or §3 change; a consumer that writes a different
# shape than the standard declares is detectable at dispatch instead of at
# failure, which is the whole reason the number exists. `candidates.md` changed
# shape three times in three days and every consumer found out as a crash.
CONTRACT_VERSION = "v1"

# §2. Lowercase base36 at eight characters. RANDOM, and the reason is NOT
# collision probability: sequential allocation requires READING the store to
# learn the next id, so two concurrent filers read the same maximum and write
# the same id. Random makes filing a pure write. Measured on `candidates.md`
# before it moved off `C-NNN`: nine renumbering events, then six collisions in
# one day, three on a single PR, every one of them silent.
_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
_ID_LEN = 8

TRACKED_ROOT = Path("tracked")


@dataclass(frozen=True)
class Store:
    """One store's §1/§4 row. The prefix and the extras are the ONLY variation."""

    name: str
    prefix: str
    holds: str
    extra_fields: tuple[str, ...]
    terminal: tuple[str, ...]
    #: Fields the operator alone may set (§4). No tool writes these, ever.
    operator_only: tuple[str, ...] = ()

    @property
    def directory(self) -> Path:
        return TRACKED_ROOT / self.name


# §1 and §4, transcribed. The admission tests live in the standard rather than
# here on purpose: they are prose judgements a reader applies, and a copy of a
# prose rule is a copy that rots. What IS here is the machine-checkable half.
STORES: dict[str, Store] = {
    "issues": Store(
        name="issues",
        prefix="I-",
        holds="a DEFECT, found while building something unrelated to it",
        extra_fields=("repo",),
        terminal=("resolved", "rejected"),
    ),
    "operations": Store(
        name="operations",
        prefix="O-",
        holds="a note-to-self of something that needs doing; the standup's surface",
        extra_fields=("state", "ownership", "blocked_on", "ready"),
        terminal=("resolved",),
        operator_only=("ready",),
    ),
    "candidates": Store(
        name="candidates",
        prefix="C-",
        holds="a PROPOSAL — a capability, detector or improvement to be considered",
        extra_fields=("component", "size", "decision"),
        terminal=("adopted", "rejected"),
    ),
    "standards": Store(
        name="standards",
        prefix="S-",
        holds="a proposed amendment to a NAMED standard, with an actionable anchor",
        extra_fields=("target", "anchor", "ratification"),
        terminal=("ratified", "amended", "rejected"),
        operator_only=("ratification",),
    ),
}

# §3. Every item in every store opens with exactly these, in this order. The
# ORDER is part of the uniformity the operator asked for — four stores whose
# files list the same fields in different sequences read as four designs.
CORE_FIELDS: tuple[str, ...] = (
    "id", "title", "status", "count", "filed", "filed_by",
)

_ID_RE = re.compile(r"\b([A-Z])-([0-9a-z]{8})\b")
_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def store_of(item_id: str) -> Store:
    """Which store an id belongs to, from the id alone.

    §2's stated payoff for spending two characters on a prefix: an id in a PR
    body or a commit message says what kind of thing it is with no lookup.
    """
    for store in STORES.values():
        if item_id.startswith(store.prefix):
            return store
    raise ValueError(
        f"{item_id!r} carries no known store prefix — expected one of "
        + ", ".join(sorted(s.prefix for s in STORES.values()))
    )


def existing_ids(root: Path) -> set[str]:
    """Every id already used, across ALL FOUR stores. `root` is the tracked dir.

    DELIBERATELY CROSS-STORE. Ids are unique corpus-wide rather than per-store,
    because they are quoted bare — a commit saying "closes I-a1b2c3d4" is
    resolved by the reader, and a reader who has to know which store to look in
    first has lost the payoff the prefix was bought for.
    """
    return {
        path.stem
        for store in STORES.values()
        for path in (root / store.name).glob("*.md")
    }


def mint(store: Store, taken: set[str]) -> str:
    """One fresh id for `store`, avoiding `taken`.

    A PURE WRITE IS THE POINT, and `taken` is a courtesy rather than a
    correctness requirement: at 36**8 the space is ~2.8e12, so at the scale any
    of these stores will reach the chance of a collision is under one in a
    million. Passing the empty set is CORRECT usage for a filer that cannot
    cheaply enumerate the store — that is precisely the race that sequential
    allocation could not avoid and this design does not have.
    """
    while True:
        candidate = store.prefix + "".join(
            secrets.choice(_ID_ALPHABET) for _ in range(_ID_LEN))
        if candidate not in taken:
            return candidate


def parse(path: Path) -> tuple[dict[str, str], str]:
    """Split an item file into its frontmatter mapping and its body.

    HAND-PARSED RATHER THAN `yaml.safe_load`, and the reason is the failure
    direction. Every value in §3's core is a scalar string or an integer, so
    there is nothing here YAML buys — while a YAML parser applied to a `title`
    that a filer wrote as `Sizing: the floor and the brief disagree` reads the
    colon as structure and fails, or worse, silently reshapes the item. A title
    STATES A CONSEQUENCE (§3) and consequences contain colons.
    """
    text = path.read_text()
    match = _FRONTMATTER.match(text)
    if not match:
        raise ValueError(
            f"{path} has no frontmatter block — every tracked item opens with "
            f"one, per Tracked Items Standard §3"
        )
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"{path}: frontmatter line is not `key: value`: {line!r}")
        fields[key.strip()] = value.strip()
    return fields, text[match.end():]


def render(fields: dict[str, str], body: str) -> str:
    """Serialise back, CORE FIRST AND IN §3's ORDER, then the store's extras.

    Field order is not cosmetic here. Four stores whose files list the same
    fields in different sequences are four designs sharing a directory, and the
    uniformity the operator asked for is the thing being built.
    """
    ordered = [k for k in CORE_FIELDS if k in fields]
    ordered += [k for k in fields if k not in CORE_FIELDS]
    lines = "\n".join(f"{k}: {fields[k]}" for k in ordered)
    return f"---\n{lines}\n---\n{body}"


def file_item(
    root: Path,
    store: Store,
    *,
    title: str,
    filed_by: str,
    status: str,
    body: str,
    extras: dict[str, str] | None = None,
    today: date | None = None,
    item_id: str | None = None,
) -> Path:
    """Write one new item and return its path. `count` starts at 1 (§3.1).

    `item_id` is injectable so a caller that already promised an id in a PR body
    can use that one rather than minting a second.
    """
    extras = dict(extras or {})
    unknown = set(extras) - set(store.extra_fields)
    if unknown:
        raise ValueError(
            f"{sorted(unknown)} are not fields of the {store.name} store — §4 "
            f"gives it {list(store.extra_fields)}"
        )
    forbidden = set(extras) & set(store.operator_only)
    if forbidden:
        raise ValueError(
            f"{sorted(forbidden)} is the OPERATOR's alone (§4) and no tool sets "
            f"it. File the item without it and let the operator rule."
        )

    directory = root / store.name
    directory.mkdir(parents=True, exist_ok=True)
    new_id = item_id or mint(store, {p.stem for p in directory.glob("*.md")})

    fields = {
        "id": new_id,
        "title": title,
        "status": status,
        "count": "1",
        "filed": (today or date.today()).isoformat(),
        "filed_by": filed_by,
    }
    fields.update(extras)

    path = directory / f"{new_id}.md"
    if path.exists():
        raise FileExistsError(f"{path} already exists — ids are never reused (§2)")
    path.write_text(render(fields, body if body.startswith("\n") else "\n" + body))
    return path


def expand(path: Path, note: str, body_text: str, *, today: date | None = None) -> None:
    """Append new evidence to an existing item WITHOUT touching its `count`.

    AN EXPANSION IS NOT A RECURRENCE, and conflating them corrupts the one signal
    triage sorts on. A recurrence says *"this happened again"* — that is what
    `count` measures. An expansion says *"the same item is larger than it was
    written"*: new scope, a second site, a consequence nobody had priced. Bumping
    `count` for one would make a single item that grew twice outrank a defect
    that genuinely recurred three times.

    WHY IT IS NOT A NEW ITEM EITHER: `review-pr` names the target explicitly
    (`EXPANSION of <ID>`), so filing a second file is a duplicate of an item the
    reviewer has already said this belongs to.
    """
    fields, body = parse(path)
    stamped = f"### {(today or date.today()).isoformat()} · {note}"
    section = "## Expansions"
    block = f"{stamped}\n\n{body_text.strip()}\n"
    if section in body:
        body = body.rstrip("\n") + f"\n\n{block}"
    else:
        body = body.rstrip("\n") + f"\n\n{section}\n\n{block}"
    path.write_text(render(fields, body))


def increment(path: Path, note: str, *, today: date | None = None) -> int:
    """Bump `count` and append a dated recurrence line. Returns the new count.

    §3.1, AND THE CLAUSE IT RETIRES. When a run surfaces something already
    filed it increments; it does not open a second item. The corpus's
    column-ownership rules forbid editing another filer's REASONING — and a
    count is not reasoning, so incrementing is not amending. The rule that told
    a run to "report the recurrence where you are already working, and edit
    nobody's row" was routing around a missing integer; this is the integer.

    RECURRENCE OUTRANKS AGE in triage: a `count: 3` from last week is a pattern
    where a `count: 1` from June may be noise.
    """
    fields, body = parse(path)
    try:
        fields["count"] = str(int(fields.get("count", "1")) + 1)
    except ValueError as exc:                       # a hand-edited non-integer
        raise ValueError(f"{path}: `count` is not an integer: "
                         f"{fields.get('count')!r}") from exc

    stamped = f"- {(today or date.today()).isoformat()} · {note}"
    if "## Recurrences" in body:
        body = body.rstrip("\n") + f"\n{stamped}\n"
    else:
        body = body.rstrip("\n") + f"\n\n## Recurrences\n\n{stamped}\n"

    path.write_text(render(fields, body))
    return int(fields["count"])
