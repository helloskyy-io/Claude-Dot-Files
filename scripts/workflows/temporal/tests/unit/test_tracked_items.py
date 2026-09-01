"""The four tracked stores are ONE design, and this is what makes that true.

THE OPERATOR'S REQUIREMENT, 2026-08-26, in their words: the four stores must
"match and look uniform in design across all 4 stores." Uniformity that is only
intended drifts the moment four different callers file into four directories
that no single reader ever opens together. These tests are what turn it into a
property.

TWO KINDS OF CHECK LIVE HERE AND THEY FAIL FOR DIFFERENT REASONS:

  * THE SHAPE checks walk whatever is actually on disk and assert every item
    obeys §3 — same six fields, same order, id matching filename and store.
    These fail when a FILER writes something malformed.
  * THE CONTRACT check reads the VENDORED standard and asserts our `STORES`
    table still matches its §1/§2 tables. This fails when UPSTREAM moves and we
    re-vendor without noticing. That is §7's entire point: `candidates.md`
    changed shape three times in three days and every consumer discovered each
    change as a failed dispatch, because nothing compared the two.

The second is the one worth having. A filer that writes a bad file is caught by
the first check on the next run; a contract that silently diverges is caught by
nothing, and produces a store that looks fine and cannot be read.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from modules.assistant.tracked import tracked_items as own

from planning_corpus import PLANNING_ROOT, require_planning_corpus  # noqa: E402

import sys as _cg_sys  # noqa: E402
from pathlib import Path as _cg_Path  # noqa: E402
_cg_sys.path.insert(0, str(_cg_Path(__file__).resolve().parents[5]
                           / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import require_planning_corpus  # noqa: E402


REPO = Path(__file__).resolve().parents[5]
# The standard and the stores live in the planning repo since 2026-08-31.
STANDARD = PLANNING_ROOT / "standards/documentation/tracked_items_standard.md"
TRACKED = PLANNING_ROOT / "tracked"


def _items() -> list[Path]:
    return sorted(p for s in own.STORES.values()
                  for p in (TRACKED / s.name).glob("*.md"))


# --------------------------------------------------------------------------
# THE CONTRACT — our table against the standard that owns it
# --------------------------------------------------------------------------

def test_the_vendored_standard_is_PRESENT_before_anything_is_checked_against_it() -> None:
    """A GUARD WHOSE INPUT CAN VANISH IS A GUARD ITS INPUT CAN SWITCH OFF.

    Every test below reads this file. If it is missing they would all pass
    vacuously — the exact class `sizing_floor` was rewritten for on 2026-08-25,
    and the reason this assertion is separate rather than folded into the next
    test: a missing standard must fail LOUDLY and by name, not as an empty
    parametrize that reports green.
    """
    require_planning_corpus()
    assert STANDARD.is_file(), (
        f"{STANDARD.relative_to(REPO)} is missing. It is VENDORED from "
        f"MDC-Master-Planning — restore it with scripts/helpers/vendor-standards.sh"
    )


def test_every_store_PREFIX_matches_what_the_standard_declares() -> None:
    """§2's identity table is the contract. Ours must be the same table.

    Parsed from the standard rather than restated here, because a restated
    table is a second source that rots — the repo rule this whole exercise
    exists to serve.
    """
    require_planning_corpus()
    text = STANDARD.read_text()
    declared: dict[str, str] = {}
    for line in text.splitlines():
        # §2's rows read `| Issues | `I-` |`; §1's carry a directory too.
        cells = [c.strip().strip("*` ") for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and re.fullmatch(r"[A-Z]-", cells[1]):
            declared[cells[0].lower().split()[0]] = cells[1]

    assert declared, "parsed no prefix rows out of §2 — the table shape changed"

    ours = {s.name: s.prefix for s in own.STORES.values()}
    by_holds = {
        "issues": ours["issues"], "operations": ours["operations"],
        "candidates": ours["candidates"], "standards": ours["standards"],
    }
    assert set(declared.values()) == set(by_holds.values()), (
        f"prefix set diverged from the standard: standard={sorted(declared.values())} "
        f"ours={sorted(by_holds.values())}. The contract is versioned "
        f"({own.CONTRACT_VERSION}) — if the standard moved, this repo conforms to it."
    )


def test_the_SHARED_CORE_is_exactly_what_section_3_lists() -> None:
    """§3's six fields, in §3's order. Field ORDER is part of the uniformity."""
    require_planning_corpus()
    block = re.search(r"```yaml\n(.*?)```", STANDARD.read_text(), re.S)
    assert block, "§3's frontmatter example is gone — the contract shape changed"
    declared = tuple(
        line.split(":")[0].strip()
        for line in block.group(1).splitlines() if ":" in line
    )
    assert declared == own.CORE_FIELDS, (
        f"core fields diverged: standard={declared} ours={own.CORE_FIELDS}"
    )


def test_all_four_store_DIRECTORIES_exist() -> None:
    """A store the standard names and the repo lacks is a filer's crash later."""
    require_planning_corpus()
    missing = [s.name for s in own.STORES.values() if not (TRACKED / s.name).is_dir()]
    assert not missing, f"tracked stores not created: {missing}"


# --------------------------------------------------------------------------
# THE SHAPE — every item on disk, whatever wrote it
# --------------------------------------------------------------------------

@pytest.mark.parametrize("path", _items(), ids=lambda p: p.stem)
def test_every_tracked_item_carries_the_SAME_core_in_the_SAME_order(
        path: Path) -> None:
    """ONE SHAPE ACROSS FOUR STORES, checked per file.

    Parametrised per item so a failure names the offending file rather than
    reporting "something in tracked/ is wrong".
    """
    fields, _ = own.parse(path)
    present = [k for k in fields if k in own.CORE_FIELDS]
    assert tuple(present) == own.CORE_FIELDS, (
        f"{path.name}: core fields are {present}, expected {list(own.CORE_FIELDS)} "
        f"in that order"
    )


@pytest.mark.parametrize("path", _items(), ids=lambda p: p.stem)
def test_every_item_id_matches_its_FILENAME_and_its_STORE(path: Path) -> None:
    """§2: the filename IS the id, and the prefix says which store without a lookup."""
    fields, _ = own.parse(path)
    assert fields["id"] == path.stem, (
        f"{path.name}: frontmatter id is {fields['id']!r} — an id quoted in a "
        f"commit must resolve to a file by name"
    )
    store = own.store_of(fields["id"])
    assert store.name == path.parent.name, (
        f"{path.name} sits in {path.parent.name}/ but its prefix says {store.name}"
    )
    assert re.fullmatch(r"[A-Z]-[0-9a-z]{8}", fields["id"]), (
        f"{fields['id']!r} is not §2's shape: prefix plus 8 lowercase base36"
    )


@pytest.mark.parametrize("path", _items(), ids=lambda p: p.stem)
def test_every_item_carries_a_usable_count_and_date(path: Path) -> None:
    """`count` drives triage order (§3.1), so a non-integer breaks the sort."""
    fields, _ = own.parse(path)
    count = int(fields["count"])
    assert count >= 1, f"{path.name}: count is {count}; a filed item has been seen once"
    date.fromisoformat(fields["filed"])
    assert fields["title"].strip(), f"{path.name}: empty title"
    assert fields["filed_by"].strip(), f"{path.name}: empty filed_by"


@pytest.mark.parametrize("path", _items(), ids=lambda p: p.stem)
def test_no_item_carries_a_field_its_store_does_not_define(path: Path) -> None:
    """§4 extensions are per-store and closed. An unknown field is a typo or a
    fifth store nobody declared."""
    fields, _ = own.parse(path)
    store = own.store_of(fields["id"])
    allowed = set(own.CORE_FIELDS) | set(store.extra_fields)
    unknown = sorted(set(fields) - allowed)
    assert not unknown, (
        f"{path.name}: {unknown} not defined for the {store.name} store; §4 gives "
        f"it {list(store.extra_fields)}"
    )


def test_the_per_item_sweep_SEES_every_file_that_is_actually_on_disk() -> None:
    """THE PER-ITEM CHECKS ABOVE ARE PARAMETRISED, AND AN EMPTY PARAMETRIZE REPORTS
    SKIP RATHER THAN FAILURE.

    Today the stores are empty and four skips are the honest answer. Once they
    are populated, a `_items()` that silently stopped matching — a renamed
    store, a changed suffix, a glob typo — would go on reporting skips and
    every shape check would evaporate without one red line. This compares the
    sweep against an independent walk, so the collector has to be right.
    """
    independent = sorted(
        p for p in TRACKED.rglob("*.md") if p.parent.name in own.STORES)
    assert sorted(_items()) == independent, (
        "the per-item collector and the filesystem disagree — every parametrised "
        "check above is running on the wrong set"
    )


def test_no_id_is_used_twice_ANYWHERE_across_the_four_stores() -> None:
    """Ids are quoted bare in commits, so they are unique corpus-wide, not per-store.

    THE REMAINING WAY TO COLLIDE IS TO COPY ONE. Random minting removed the
    race that produced nine renumberings and six collisions on `candidates.md`;
    it did not remove copy-paste, and a guard whose failure mode is now rare is
    not a guard whose value is now zero.
    """
    seen: dict[str, Path] = {}
    for path in _items():
        fields, _ = own.parse(path)
        clash = seen.get(fields["id"])
        assert clash is None, f"{fields['id']} names both {clash} and {path}"
        seen[fields["id"]] = path


# --------------------------------------------------------------------------
# THE WRITER — behaviour the stores depend on
# --------------------------------------------------------------------------

def test_a_tool_CANNOT_set_an_operator_only_field(tmp_path: Path) -> None:
    """§4: `ready` and `ratification` are the operator's alone.

    Enforced in the writer rather than trusted to prompts, because the whole
    point of Standards Governance is that an autonomous run surfaces and does
    not rule. A prompt that says so is a request; this is a refusal.
    """
    for store_name, field in (("operations", "ready"), ("standards", "ratification")):
        with pytest.raises(ValueError, match="OPERATOR"):
            own.file_item(
                tmp_path, own.STORES[store_name], title="t", filed_by="a-workflow",
                status="open", body="b", extras={field: "yes"})


def test_minting_is_a_PURE_WRITE_and_needs_no_read_of_the_store() -> None:
    """The property the whole id design exists for: no read, no maximum, no race."""
    ids = {own.mint(own.STORES["issues"], set()) for _ in range(500)}
    assert len(ids) == 500, "500 mints collided — the alphabet or length changed"
    assert all(re.fullmatch(r"I-[0-9a-z]{8}", i) for i in ids)


def test_incrementing_appends_and_never_rewrites_the_body(tmp_path: Path) -> None:
    """§3.1: incrementing is not amending.

    The corpus's column-ownership rules forbid editing another filer's
    reasoning. This asserts the original body survives verbatim, which is what
    makes "a count is not reasoning" true in code rather than in prose.
    """
    path = own.file_item(
        tmp_path, own.STORES["candidates"], title="t", filed_by="pm3", status="open",
        body="ORIGINAL REASONING, untouched.\n", extras={"component": "x"},
        today=date(2026, 8, 26))
    before = path.read_text()

    assert own.increment(path, "seen again on #140", today=date(2026, 8, 27)) == 2
    assert own.increment(path, "and again on #141", today=date(2026, 8, 28)) == 3

    after = path.read_text()
    assert "ORIGINAL REASONING, untouched." in after
    assert "count: 3" in after
    assert after.count("## Recurrences") == 1, "a second heading per recurrence"
    assert "- 2026-08-27 · seen again on #140" in after
    assert "- 2026-08-28 · and again on #141" in after
    assert before.split("---")[2].strip().startswith("ORIGINAL")


def test_a_title_containing_a_colon_survives_the_round_trip(tmp_path: Path) -> None:
    """WHY THE FRONTMATTER IS HAND-PARSED AND NOT `yaml.safe_load`.

    §3 requires a title to state the CONSEQUENCE, and consequences contain
    colons — "Sizing: the floor and the brief disagree" is the shape of a real
    one. A YAML reader takes the colon as structure. This pins the case.
    """
    title = "Sizing: the floor and the brief disagree, and the run dies at the guard"
    path = own.file_item(
        tmp_path, own.STORES["issues"], title=title, filed_by="review-pr",
        status="open", body="b", extras={"repo": "claude-dot-files"})
    fields, _ = own.parse(path)
    assert fields["title"] == title


def test_an_id_is_never_reused_even_after_a_terminal_state(tmp_path: Path) -> None:
    """§2: immutable and never reused, terminal state included."""
    store = own.STORES["issues"]
    path = own.file_item(tmp_path, store, title="t", filed_by="x", status="resolved",
                         body="b", item_id="I-aaaaaaaa")
    assert path.name == "I-aaaaaaaa.md"
    with pytest.raises(FileExistsError):
        own.file_item(tmp_path, store, title="other", filed_by="x", status="open",
                      body="b", item_id="I-aaaaaaaa")
