"""Reader for the four ``tracked/`` stores, with the §7 contract check.

**These four are the least expensive input this phase parses, by a wide
margin** — four folders of identical frontmatter with an admission test at the
door. Every other surface is prose a human wrote for a human.

The §7 contract check runs **before anything consumes the stores**. §7 exists
because ``candidates.md`` changed shape three times in three days and this repo
discovered each change *as a failed dispatch*. So: a per-item deviation is a
finding, and a **store-wide** deviation halts the run with the mismatch named —
never a shorter table that reads as a complete one.

Frontmatter is parsed line by line rather than through a YAML loader, because
requirement 1 binds provenance at node granularity and a YAML load discards the
line each key was read from.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import corpus_io
from .model import (
    TRACKED_CONTRACT_MISMATCH,
    TRACKED_DUPLICATE_FIELD,
    TRACKED_STORE_ABSENT,
    SECTION_TRACKED,
    TRACKED_CORE_FIELD_MISSING,
    TRACKED_ID_MALFORMED,
    TRACKED_ITEM_UNPARSEABLE,
    Collector,
    Provenance,
)

#: Tracked Items Standard §7. Any change to §2 or §3 increments it.
CONTRACT_VERSION = "v1"

#: §3 — required in every store.
CORE_FIELDS: tuple[str, ...] = ("id", "title", "status", "count", "filed", "filed_by")

#: §4 — per-store extensions. Values are (prefix, extra fields).
STORES: dict[str, tuple[str, tuple[str, ...]]] = {
    "issues": ("I", ("repo",)),
    "operations": ("O", ("ownership", "blocked_on", "ready")),
    "candidates": ("C", ("component", "size", "decision")),
    "standards": ("S", ("target", "anchor", "ratification")),
}

ID_RE = re.compile(r"^(?P<prefix>[A-Z])-(?P<body>[a-z0-9]{8})$")
FIELD_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*):(?P<value>.*)$")


class ContractMismatch(Exception):
    """A store's shape no longer matches the expected §3 core.

    Raised rather than degraded-around. Producing a shorter table from a store
    whose contract has moved is exactly the failure §7 was written to stop.
    """

    def __init__(self, store: str, detail: str) -> None:
        super().__init__(
            f"tracked/{store}/ does not match contract {CONTRACT_VERSION}: {detail}"
        )
        self.store = store
        self.detail = detail


@dataclass
class TrackedItem:
    store: str
    path: str  # repo-relative
    fields: dict[str, str] = field(default_factory=dict)
    field_lines: dict[str, int] = field(default_factory=dict)
    body: str = ""

    def line_of(self, key: str) -> int:
        return self.field_lines.get(key, 0)


@dataclass
class TrackedStores:
    items: dict[str, list[TrackedItem]] = field(default_factory=dict)
    contract_version: str = CONTRACT_VERSION
    halted: str = ""

    def all_items(self) -> list[TrackedItem]:
        out: list[TrackedItem] = []
        for store in sorted(self.items):
            out.extend(self.items[store])
        return out


def _parse_frontmatter(
    text: str,
) -> tuple[dict[str, str], dict[str, int], str, str, list[tuple[str, int]]]:
    """Split ``---`` frontmatter into fields, their line numbers, and the body.

    Returns ``(fields, field_lines, body, error, duplicates)``. ``error`` is
    non-empty when the file carries no closing delimiter — a malformed item
    file, which §3.1's migration note names as the frontmatter-era successor to
    the column shift.

    ``duplicates`` carries every ``(key, line)`` whose key was already set.
    **First value wins and the second is REPORTED, not discarded**: a second
    ``status:`` or ``decision:`` line is a corpus defect whose two readings
    disagree, and a reader that quietly keeps one of them is the confident
    wrong result §3.1 names — one layer down from the column shift, exactly as
    the phase doc predicted.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, {}, text, "no opening `---` frontmatter delimiter", []

    fields: dict[str, str] = {}
    field_lines: dict[str, int] = {}
    duplicates: list[tuple[str, int]] = []
    for index in range(1, len(lines)):
        stripped = lines[index].strip()
        if stripped == "---":
            return fields, field_lines, "\n".join(lines[index + 1 :]), "", duplicates
        if not stripped:
            continue
        match = FIELD_RE.match(lines[index])
        if not match:
            # A continuation or a list entry. Not a scalar field; not dropped —
            # it simply carries no key, and the caller's core check will see the
            # absence if it mattered.
            continue
        key = match.group("key")
        if key in fields:
            duplicates.append((key, index + 1))
            continue
        fields[key] = match.group("value").strip()
        field_lines[key] = index + 1
    return fields, field_lines, "", "no closing `---` frontmatter delimiter", duplicates


def _check_contract(store: str, items: list[TrackedItem]) -> None:
    """§7: compare the expected core against what the store actually carries.

    A **store-wide** deviation halts. A per-item deviation does not — that is a
    finding, reported by :func:`read_stores`. The distinction matters: one
    malformed item is a corpus defect, while a core field absent from every item
    in a store means the contract moved underneath this reader.
    """
    if not items:
        return
    _prefix, extras = STORES[store]
    known = set(CORE_FIELDS) | set(extras)

    union: set[str] = set()
    intersection: set[str] | None = None
    for item in items:
        keys = set(item.fields)
        union |= keys
        intersection = keys if intersection is None else (intersection & keys)

    missing_everywhere = sorted(set(CORE_FIELDS) - union)
    if missing_everywhere:
        raise ContractMismatch(
            store,
            "core field(s) "
            + ", ".join(repr(f) for f in missing_everywhere)
            + f" absent from all {len(items)} items",
        )

    unknown_everywhere = sorted((intersection or set()) - known)
    if unknown_everywhere:
        raise ContractMismatch(
            store,
            "every item carries unexpected field(s) "
            + ", ".join(repr(f) for f in unknown_everywhere)
            + " — the shared core has moved",
        )


def read_stores(root: Path, collector: Collector) -> TrackedStores:
    """Read all four stores. Halts (records ``halted``) on a contract mismatch."""
    stores = TrackedStores()
    for store in sorted(STORES):
        prefix, _extras = STORES[store]
        directory = root / "tracked" / store
        items: list[TrackedItem] = []
        if not directory.is_dir():
            collector.add_finding(
                TRACKED_STORE_ABSENT,
                SECTION_TRACKED,
                f"tracked store `tracked/{store}/` is absent from the checkout",
                Provenance(f"tracked/{store}"),
                expected="one of the four §1 stores",
            )
            stores.items[store] = items
            continue

        # Enumerated through corpus_io like every other tree in the package.
        # A store-local `directory.glob("*.md")` walked around the escape guard
        # and around the dot-directory exclusion, and it was the ONE surface the
        # package treats as trustworthy — so the bypass was least visible
        # exactly where it mattered most.
        for rel in corpus_io.iter_markdown(root, f"tracked/{store}", collector=collector):
            text = corpus_io.read_text(root, rel, collector)
            if text is None:
                continue  # reported by read_text as FILE_UNREADABLE
            fields, field_lines, body, error, duplicates = _parse_frontmatter(text)
            for key, line in duplicates:
                collector.add_finding(
                    TRACKED_DUPLICATE_FIELD,
                    SECTION_TRACKED,
                    f"tracked item repeats frontmatter key `{key}`; the first value is used",
                    Provenance(rel, line),
                    expected="one line per §3 core field",
                    detail="Two readings of one field disagree. Reported, not resolved.",
                )
            if error:
                collector.add_finding(
                    TRACKED_ITEM_UNPARSEABLE,
                    SECTION_TRACKED,
                    f"tracked item is not readable as a §3 frontmatter block: {error}",
                    Provenance(rel, 1),
                    expected="`---` … `---` YAML frontmatter carrying the §3 shared core",
                )
                continue
            items.append(
                TrackedItem(
                    store=store,
                    path=rel,
                    fields=fields,
                    field_lines=field_lines,
                    body=body,
                )
            )

        try:
            _check_contract(store, items)
        except ContractMismatch as exc:
            stores.halted = str(exc)
            collector.add_finding(
                TRACKED_CONTRACT_MISMATCH,
                SECTION_TRACKED,
                str(exc),
                Provenance(f"tracked/{store}"),
                expected=(
                    f"Tracked Items Standard §3 shared core at contract "
                    f"{CONTRACT_VERSION}: {', '.join(CORE_FIELDS)}"
                ),
                detail=(
                    "The run halts here rather than producing a shorter table. §7 "
                    "exists because an unversioned contract between two repos was "
                    "discovered as a failed dispatch, three times in three days."
                ),
            )
            stores.items[store] = items
            return stores

        _report_item_deviations(store, prefix, items, collector)
        stores.items[store] = items

    return stores


def _report_item_deviations(
    store: str, prefix: str, items: list[TrackedItem], collector: Collector
) -> None:
    _p, extras = STORES[store]
    for item in items:
        for name in CORE_FIELDS:
            if name not in item.fields:
                collector.add_finding(
                    TRACKED_CORE_FIELD_MISSING,
                    SECTION_TRACKED,
                    f"tracked item is missing the §3 core field `{name}`",
                    Provenance(item.path, 1),
                    expected=f"`{name}:` in the frontmatter",
                )
            elif not item.fields[name]:
                collector.add_finding(
                    TRACKED_CORE_FIELD_MISSING,
                    SECTION_TRACKED,
                    f"tracked item carries `{name}:` with an empty value",
                    Provenance(item.path, item.line_of(name)),
                    expected=f"a non-empty `{name}:` per §3",
                )

        item_id = item.fields.get("id", "")
        match = ID_RE.match(item_id)
        expected_name = f"{item_id}.md"
        if not match:
            collector.add_finding(
                TRACKED_ID_MALFORMED,
                SECTION_TRACKED,
                f"tracked item id `{item_id}` does not match §2 `<PREFIX>-<8 lowercase alphanumerics>`",
                Provenance(item.path, item.line_of("id")),
                expected="`<PREFIX>-<8 chars>`, e.g. S-a1b2c3d4",
            )
        else:
            if match.group("prefix") != prefix:
                collector.add_finding(
                    TRACKED_ID_MALFORMED,
                    SECTION_TRACKED,
                    f"tracked item id prefix `{match.group('prefix')}-` does not match "
                    f"its store (`tracked/{store}/` takes `{prefix}-`)",
                    Provenance(item.path, item.line_of("id")),
                    expected=f"`{prefix}-<8 chars>`",
                )
            if item.path.rsplit("/", 1)[-1] != expected_name:
                collector.add_finding(
                    TRACKED_ID_MALFORMED,
                    SECTION_TRACKED,
                    f"tracked item filename does not match its id (`{expected_name}` expected)",
                    Provenance(item.path, item.line_of("id")),
                    expected=f"`{expected_name}` per §2",
                )

        for name in extras:
            if name not in item.fields:
                collector.add_finding(
                    TRACKED_CORE_FIELD_MISSING,
                    SECTION_TRACKED,
                    f"tracked item is missing the §4 `{store}` field `{name}`",
                    Provenance(item.path, 1),
                    expected=f"`{name}:` in the frontmatter",
                )
