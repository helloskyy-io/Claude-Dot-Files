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
found by a `plan-feature` run reading the component cold, not by the sweep that
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
_NUMBERED_REQ = re.compile(r"^\s*\d+\.\s+\*\*(.+?)\*\*")

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
        m = _OPEN_BOX.match(line) or _NUMBERED_REQ.match(line)
        if not m:
            continue
        # ONE ENTRY PER LINE, not per surface name: a criterion naming both
        # deleted files is one defect with one remedy, and reporting it twice
        # makes a two-line failure read as four.
        if _SURFACE.search(m.group(1)):
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
