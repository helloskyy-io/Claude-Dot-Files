"""An unbuilt phase must not be obliged to produce something that cannot exist.

WHAT THIS CATCHES, MEASURED. The 2026-08-26 store migration deleted
`candidates.md` and `direction.md`. `persistent-memory-protocol` Phase 4 —
**unbuilt** — still carries *"Replay of the journal reproduces `candidates.md`
and `direction.md`"* as a completion criterion. A build dispatch reading that
would write a replay test against files that are not in the tree, discover it
cannot pass, and either fake the test or stall. The plan promises work that is
now impossible.

THE DISCRIMINATOR IS THE CHECKBOX ITSELF, which is why this needs no exemption
list and no per-file judgement:

  * `- [ ]` is an OBLIGATION. It says *this will be true when the phase is done*.
    Naming a surface that no longer exists makes it unsatisfiable.
  * `- [x]` is a RECORD. It says *this was true when it was done* — against the
    tree as it stood then. Rewriting it to name today's surfaces would falsify
    the record, which is the failure the whole record-versus-instruction rule
    exists to prevent.

Same rule the operator set for the store sweep — *fix the instruction, leave the
record* — with the checkbox state doing the classifying instead of a human. That
is the whole reason this gate is cheap: the corpus already marks which is which.

WHY A SEPARATE MODULE FROM `test_retired_vocabulary_is_gone_from_live_surfaces`.
That one keys on retired LABELS and exempts by PATH PREFIX, because a whole
component's docs are a record of what it built. This keys on retired SURFACES,
where record and obligation sit in the SAME FILE two lines apart — `pmp/roadmap.md`
carries both. A path exemption cannot express that; a checkbox state can.

MISSED BY THE 2026-08-26 SWEEP, and the reason is worth keeping. That sweep
searched for INSTRUCTIONS naming a deleted store and left RECORDS alone — a
sound rule that scoped the search to prose. **A completion criterion is neither:
it is a promise about the future, in a document that also holds records.** It was
found by a `plan-draft` run reading the component cold, not by the sweep that
created the problem.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]

#: Surfaces deleted by the four-store migration. **Each is asserted GONE below**,
#: so this list cannot silently describe a file that came back — an entry whose
#: file exists again is a stale entry, not a passing check.
DELETED_SURFACES: dict[str, str] = {
    "candidates.md": "the markdown candidates table, replaced by `tracked/candidates/` on 2026-08-26",
    "direction.md": "the D-NNN ruling queue, deleted on 2026-08-26 — a `requires review` candidate is the ruling queue now",
}

#: An UNCHECKED completion criterion. Anchored to the box so a mention inside
#: ordinary prose is not read as a promise.
_OPEN_BOX = re.compile(r"^\s*[-*]\s*\[ \]\s*(.+)$")

#: A numbered requirement in a phase doc — the other shape a phase's obligations
#: take. `phase4_rebuild_is_a_test.md` carries its requirements this way, and its
#: requirement 1 is the instance that produced this module.
#:
#: **The bold segment IDENTIFIES the requirement; the WHOLE LINE is the promise.**
#: The first cut captured only `\*\*(.+?)\*\*` and so read a requirement's title
#: while ignoring its body — which is where the surface name usually sits, after
#: the em-dash. That let requirement 6 of `phase4_rebuild_is_a_test.md` pass:
#: *"**The change in authority is documented …** — `candidates.md` and
#: `direction.md` are now rebuilt from the journal"*. Title clean, body naming two
#: deleted files, gate green. Matched on the bold opener, measured on the line.
_NUMBERED_REQ = re.compile(r"^\s*\d+\.\s+\*\*")

#: A numbered item's `[x]`. The checkbox path gets its record/obligation
#: discriminator from the box; a numbered requirement has no box, and the corpus
#: marks a settled one by opening its bold segment with `✅` — **8 occurrences
#: across two components, and no other status marker is used this way.** Same
#: rule as the checkbox, same reason: a record describes the tree as it stood and
#: rewriting it would falsify it.
_NUMBERED_RECORD = re.compile(r"^\s*\d+\.\s+\*\*✅")

_SURFACE = re.compile(r"`?\b(candidates|direction)\.md\b`?")


def _planning_docs() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "docs/development/*/roadmap.md",
         "docs/development/*/phase*.md"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    return [REPO / p for p in out]


def test_the_deleted_surfaces_are_ACTUALLY_DELETED() -> None:
    """THE PREMISE, CHECKED. Every check below assumes these files are gone.

    If one returns, its criteria become satisfiable again and this gate would be
    failing correct documents — so the list is verified against the tree rather
    than trusted. A stale entry here is worse than no gate: it fails a plan that
    is right.
    """
    tracked = subprocess.run(["git", "ls-files"], cwd=REPO,
                             capture_output=True, text=True, check=True).stdout
    for name, why in DELETED_SURFACES.items():
        present = [p for p in tracked.splitlines() if p.endswith("/" + name)]
        assert not present, (
            f"`{name}` is in the tree at {present} — {why}. Either it came back "
            f"and this entry is stale, or a new file took the name. Remove the "
            f"entry or rename the file; leaving it fails correct plans."
        )


def test_there_are_planning_docs_to_check() -> None:
    """A vacuity floor: an empty walk asserts nothing and reports green."""
    docs = _planning_docs()
    assert len(docs) >= 4, f"found {len(docs)} planning docs, expected the corpus"


@pytest.mark.parametrize("doc", _planning_docs(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_no_OPEN_obligation_names_a_deleted_surface(doc: Path) -> None:
    """An unchecked box or a numbered requirement is a promise. It must be keepable.

    A CHECKED box naming the same surface passes, deliberately — it records what
    was done against the tree as it stood, and rewriting it would make the record
    describe something that never happened.
    """
    offences: list[str] = []
    for n, line in enumerate(doc.read_text().splitlines(), 1):
        box = _OPEN_BOX.match(line)
        if box:
            promise = box.group(1)
        elif _NUMBERED_RECORD.match(line):
            continue                # a settled item — a RECORD, left alone
        elif _NUMBERED_REQ.match(line):
            promise = line          # title AND body — see `_NUMBERED_REQ`
        else:
            continue
        # ONE ENTRY PER LINE, not per surface name: a criterion naming both
        # deleted files is one defect with one remedy, and reporting it twice
        # makes a two-line failure read as four.
        if _SURFACE.search(promise):
            offences.append(f"    :{n}  {line.strip()[:110]}")

    assert not offences, (
        f"{doc.relative_to(REPO)} carries {len(offences)} OPEN obligation(s) "
        f"naming a surface that no longer exists:\n"
        + "\n".join(offences)
        + "\n\n  " + "\n  ".join(f"`{k}` — {v}" for k, v in DELETED_SURFACES.items())
        + "\n\n  An unbuilt phase promising work against a deleted file cannot be "
          "completed as written: a build dispatch reaches the criterion, finds "
          "nothing to test, and either fakes it or stalls. Repoint the criterion "
          "at what replaced the surface. **A CHECKED box naming the same file is "
          "a RECORD and is left alone** — this gate does not touch those."
    )


def test_a_requirements_BODY_is_read_not_just_its_bold_title() -> None:
    """POSITIVE CONTROL for the widening. Without it the narrowing is invisible.

    `_NUMBERED_REQ` used to capture the bold title alone, so a requirement whose
    title was clean and whose BODY named a deleted surface passed. That is the
    shape requirement 6 of `phase4_rebuild_is_a_test.md` actually had, and the
    gate was green on it for a day. If someone re-narrows the key to the title,
    every other test here still passes — this one is what fails.
    """
    title_clean_body_dirty = (
        "6. **The change in authority is documented where readers will find it** "
        "— `candidates.md` and `direction.md` are now rebuilt from the journal"
    )
    assert _NUMBERED_REQ.match(title_clean_body_dirty), "the line is a requirement"
    assert _SURFACE.search(title_clean_body_dirty), (
        "the surface name is in the BODY, past the em-dash. A key that stops at "
        "the closing `**` cannot see it — which is the bug this control holds."
    )

    title_dirty = "1. **Replay reproduces `candidates.md`** — byte-identical"
    assert _SURFACE.search(title_dirty), "titles are still read"

    prose = "3. Two hundred rows were migrated on 2026-08-26."
    assert not _NUMBERED_REQ.match(prose), (
        "an ordinary numbered sentence is NOT a requirement — the bold opener is "
        "what distinguishes an obligation from a prose enumeration, and widening "
        "the measurement must not widen the match."
    )


def test_a_SETTLED_numbered_item_is_a_record_and_is_left_alone() -> None:
    """The numbered path's record/obligation split, held the same way as the box.

    Widening the measurement to the whole line exposed that the numbered path had
    NO discriminator — it had merely been hidden, because a title alone rarely
    names a surface. `mmf/roadmap.md:8` is the real instance: a `✅`-marked entry
    recording a 2026-08-10 correction, which the widened key flagged as a broken
    promise. It is a record. Rewriting it would falsify it.
    """
    record = (
        "8. **✅ THE ROW-PRESENCE HALF IS ALREADY RECONCILED — corrected "
        "2026-08-10.** `architectural_standard.md` now carries a `direction.md` note"
    )
    assert _NUMBERED_REQ.match(record), "it is still shaped like a requirement"
    assert _SURFACE.search(record), "and it does name a deleted surface"
    assert _NUMBERED_RECORD.match(record), (
        "but `✅` marks it settled, so it is a RECORD and this gate skips it — "
        "the same rule `- [x]` gets, applied to the shape that has no box."
    )

    obligation = "6. **The change in authority is documented** — `candidates.md` is rebuilt"
    assert not _NUMBERED_RECORD.match(obligation), (
        "an unmarked numbered requirement is an OPEN promise and stays in scope"
    )
