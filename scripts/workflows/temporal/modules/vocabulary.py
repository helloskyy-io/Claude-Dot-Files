"""One declaration per concept the typed exit record and the journal event share.

REQUIREMENT 3 OF PERSISTENT MEMORY PROTOCOL PHASE 3, AND IT IS A MODULE RATHER
THAN A RULE BECAUSE A RULE IS WHAT DRIFTED. The two contracts are separate — the
phase doc's § *One vocabulary, two contracts* gives the reason, and it is not a
preference: `exit-protocol.md` §2 forbids a field added for a consumer that does
not exist, and §2.5 bounds the record at 4096 bytes, while a journal event
carries authored content verbatim and adds six fields no parent branches on. So
an extension is not available and two contracts are what exist.

Two contracts that name the same concept twice is the failure that follows, and
it is a REAL risk rather than a tidiness worry: `outcome` spelled `merge`/`hold`
in one and `MERGE`/`HOLD` in the other makes a rebuild's diff report a
difference that is not one. This module is where each shared concept is spelled,
once. Both sides import it; neither restates it.

WHY IT SITS AT `modules/` AND NOT INSIDE EITHER PACKAGE. `modules/journal/`
imports no workflow module — `test_the_journal_package_imports_no_workflow_module`
holds that, and Phase 6's reader depends on it, because dragging in
`modules.assistant` drags in `temporalio` behind it. So the vocabulary cannot
live beside `exit_record.py`. Putting it inside `modules/journal/` instead would
invert the problem: `exit_record.py` is dependency-free by design and importing
the journal package would execute its whole `__init__`. A leaf at `modules/`
belongs to neither and is importable by both, which is the only placement that
leaves both properties intact.

STDLIB ONLY, NO I/O, NO CLOCK — the same discipline `routing.py` and
`exit_record.py` keep, and for the same reason: a vocabulary that could fail to
import is a vocabulary that stops being the single declaration.

WHAT IS DELIBERATELY *NOT* HERE. A concept named by only one of the two
contracts stays where it is used. `RoutedOutcome` and `UndeterminedReason` are
the parent's computed stratum (`exit-protocol.md` §2.3) and no journal event
carries them, so hoisting them here would make this module a dumping ground for
the exit record's enums rather than the shared surface it is. The test that
holds this is `test_shared_vocabulary_is_declared_once.py`, which asserts the
spelling agreement in both directions rather than the membership of this file.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["Outcome", "HoldKind", "Disposition", "TerminalState",
           "SHARED_CONCEPTS"]


class Outcome(str, Enum):
    """What a run asserts about the work it did.

    Authored by the child on the exit record (`exit-protocol.md` §2.1) and
    carried verbatim into the journal as the outcome of the run that emitted the
    event. `str`-valued so `json.dumps` serialises it without an encoder, which
    is what keeps the journal's on-disk spelling and the exit record's wire
    spelling the same string rather than two conversions that agree today.
    """

    MERGE = "merge"
    HOLD = "hold"


class HoldKind(str, Enum):
    """The sub-kind every parent branches on — `hold` alone does not route.

    NEEDS_RULING is the ASSERTED abstention arm: the evaluation completed and
    the answer is that a human must decide. It stays a model assertion by
    construction — a predicate that could detect "this needs a human" would be
    the ground truth it is asking for.
    """

    REDISPATCH = "redispatch"
    NEEDS_RULING = "needs_ruling"


class Disposition(str, Enum):
    """What happened to one finding. The one vocabulary both contracts enumerate.

    THIS IS THE CONCEPT THE DRIFT RISK IS REAL ON, because it is spelled in three
    places today: the exit record's `findings[].disposition` schema enum, the
    `pr_review:` block a reviewer writes, and `convergence.py`'s open/closed
    partition. `memory-model.md` §4.1 records the partition — CLOSED is `fixed` /
    `deferred` / `rejected` / `noted` / `dissolved` / `escalated`, OPEN is `hold`
    plus anything unrecognised — and a journal event replaying a finding row has
    to spell it the way the partition reads it or the rebuild diff is noise.
    """

    HOLD = "hold"
    FIXED = "fixed"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    NOTED = "noted"
    ESCALATED = "escalated"
    DISSOLVED = "dissolved"


class TerminalState(str, Enum):
    """How a run — or one emit unit inside it — ENDED. Never how it was judged.

    SEPARATE FROM `Outcome` AND THE SEPARATION IS THE POINT. `Outcome` is a
    judgement about the work; this is a fact about the process. A run can end
    `COMPLETED` while asserting `HOLD`, and it can end `JOURNAL_UNWRITABLE`
    having asserted nothing at all. Collapsing them would make the phase doc's
    case (d) — the journal is gone, so the run stops — indistinguishable from a
    reviewer holding a PR, which is the one signal this component's failure path
    depends on being separately visible.

    `JOURNAL_UNWRITABLE` is requirement 4 case (d)'s named terminal state and
    `EMIT_FAILED` is case (b)'s. They are two states because they need two
    remedies: case (b) means the journal took no more writes at a known boundary
    and the store write was withheld, which is recoverable by re-running; case
    (d) means the journal root itself is gone, and re-running writes nothing.
    """

    COMPLETED = "completed"
    EMIT_FAILED = "emit_failed"
    JOURNAL_UNWRITABLE = "journal_unwritable"
    STORE_WRITE_FAILED = "store_write_failed"


#: The concepts this module declares, as `(name, member-values)`. Enumerated so a
#: conformance test can walk it rather than restating the membership — the same
#: "walk the declaration, never re-type it" discipline `exit_record._validate`
#: applies to `CHILD_SCHEMA`. A concept added here is checked in both contracts
#: without editing the test.
SHARED_CONCEPTS: dict[str, tuple[str, ...]] = {
    "Outcome": tuple(m.value for m in Outcome),
    "HoldKind": tuple(m.value for m in HoldKind),
    "Disposition": tuple(m.value for m in Disposition),
    "TerminalState": tuple(m.value for m in TerminalState),
}
