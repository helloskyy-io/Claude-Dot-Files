"""One declaration per shared concept — PMP Phase 3 requirement 3, as a test.

⚠ THIS FILE EXISTS BECAUSE `modules/vocabulary.py` CITED IT AND IT DID NOT EXIST.
Its docstring said *"The test that holds this is
`test_shared_vocabulary_is_declared_once.py`, which asserts the spelling
agreement in both directions"* — and the module's whole argument, stated three
times across this package, is that *a rule written only as prose has not once
prevented the thing it forbids.* The one invariant the module was added to
protect was itself protected by prose, and `SHARED_CONCEPTS` — the dict built so
a conformance test could walk it — was imported by nothing.

WHAT IS ASSERTED, AND WHY IT IS IDENTITY RATHER THAN VALUE. Two enums spelled
alike compare UNEQUAL member-to-member, so `exit_record.Outcome.MERGE ==
vocabulary.Outcome.MERGE` is `False` the moment the class is re-declared — while
every string comparison in the fleet keeps passing, because both serialise to
`"merge"`. A value test would therefore go green on exactly the drift this file
exists to catch. The identity test is what fails.

THE SPELLINGS ARE WALKED FROM `SHARED_CONCEPTS`, never re-typed here. A concept
added to the module is checked in both contracts without editing this file,
which is the discipline `exit_record._validate` already applies to
`CHILD_SCHEMA`.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules import vocabulary
from modules.assistant import convergence
from modules.assistant.review_pr import exit_record
from modules.journal import events

MODULES = Path(__file__).resolve().parents[2] / "modules"


def test_SHARED_CONCEPTS_enumerates_every_enum_the_module_declares() -> None:
    """The walk's own denominator: a concept absent from the dict is unchecked.

    Every test below iterates `SHARED_CONCEPTS`, so a fifth enum added to
    `vocabulary.py` and left out of the dict would be silently exempt from all
    of them — a guard whose population is maintained by hand beside the thing it
    guards. This asserts the two are the same set.
    """
    declared = {name for name in vocabulary.__all__ if name != "SHARED_CONCEPTS"}
    assert set(vocabulary.SHARED_CONCEPTS) == declared, (
        f"`SHARED_CONCEPTS` and `__all__` disagree: "
        f"{declared ^ set(vocabulary.SHARED_CONCEPTS)}. Every conformance test "
        f"in this file walks the dict, so a concept missing from it is a "
        f"concept nothing checks.")


def redeclares(tree: ast.Module, concept: str) -> bool:
    """Does this tree DECLARE a class named `concept`, rather than import one?

    THE PREDICATE, EXTRACTED SO A LITERAL CAN DRIVE IT. The controls below feed
    it parsed snippets rather than files, because a walker that only ever runs
    over the production tree passes every assertion it makes the day its
    recogniser stops recognising anything — `test_a_census_guard_proves_its_own_
    predicate` is the guard that refuses exactly that, and this file arrived
    under it.

    IT TAKES A TREE RATHER THAN SOURCE TEXT so the parse stays at the call site:
    the production test parses a FILE and the controls parse a STRING, and the
    census reads those two shapes to tell a tree-walker from its control. A
    helper that swallowed the parse would hide both.
    """
    return any(isinstance(node, ast.ClassDef) and node.name == concept
               for node in ast.walk(tree))


@pytest.mark.parametrize("source,expected", [
    ("from ..vocabulary import Outcome\n", False),
    ("from modules.vocabulary import Outcome as Outcome\n", False),
    ("Outcome = 1\n", False),
    ('"""A docstring mentioning class Outcome(str, Enum)."""\n', False),
    ("class Outcome(str, Enum):\n    MERGE = 'merge'\n", True),
    ("if True:\n    class Outcome(str, Enum):\n        MERGE = 'merge'\n", True),
])
def test_the_redeclaration_predicate_answers_a_LITERAL_both_ways(
        source: str, expected: bool) -> None:
    """The positive control, and its discriminator.

    An import binds the same name a declaration does, so a `hasattr` check
    cannot separate them — the first two rows are what that check would get
    wrong. The fourth is the substring bug: a docstring naming the class is
    prose, and a text scan would call it a declaration. The last proves the walk
    reaches a nested body rather than only the module's top level.
    """
    assert redeclares(ast.parse(source), "Outcome") is expected


@pytest.mark.parametrize("concept", sorted(vocabulary.SHARED_CONCEPTS))
def test_no_shared_concept_is_RE_DECLARED_in_either_contract(concept: str) -> None:
    """Neither contract may declare a class of a shared concept's name.

    ASKED OF THE SYNTAX TREE, not of the imported object: an import binds the
    same name as a declaration, so `hasattr` cannot tell "imported from the one
    declaration" from "declared again here". A `ClassDef` can only be the second.
    """
    for relpath in ("assistant/review_pr/exit_record.py", "journal/events.py"):
        tree = ast.parse((MODULES / relpath).read_text(encoding="utf-8"))
        assert not redeclares(tree, concept), (
            f"modules/{relpath} declares `{concept}` again. Two enums spelled alike "
            f"compare unequal member-to-member while both still serialise to "
            f"the same string, so a rebuild diffing them reports a difference "
            f"that is not one — and every string test keeps passing.")


def test_the_exit_record_and_the_journal_share_the_SAME_OBJECTS() -> None:
    """Identity, not equality — the only test that fails on a re-declaration."""
    assert exit_record.Outcome is vocabulary.Outcome
    assert exit_record.HoldKind is vocabulary.HoldKind
    assert events.Outcome is vocabulary.Outcome
    assert events.TerminalState is vocabulary.TerminalState


def test_the_CHILD_SCHEMA_disposition_enum_is_the_shared_spelling() -> None:
    """The exit record's schema string is derived from the declaration.

    It was a hand-written list until this phase, and a hand-written list beside
    an enum is the drift the module exists to prevent — the schema is what a
    child is validated against, so a disposition present in one and absent from
    the other is a finding row the fleet refuses or replays wrongly.
    """
    schema_enum = (exit_record.CHILD_SCHEMA["properties"]["findings"]["items"]
                   ["properties"]["disposition"]["enum"])
    assert schema_enum == sorted(vocabulary.SHARED_CONCEPTS["Disposition"])


def test_the_convergence_partition_covers_EVERY_declared_disposition() -> None:
    """The third consumer of one spelling, and the one that silently miscounts.

    `convergence.py` partitions dispositions into CLOSED and OPEN and counts
    anything unrecognised as OPEN. A disposition added to `vocabulary.py` and
    not to that partition therefore does not fail anything — it makes a
    converged loop report as unconverged, forever, with no error. That is the
    asymmetry `convergence.py` documents as deliberate for a value nobody
    declared; it is not what should happen to one this fleet declares itself.
    """
    partitioned = convergence.CLOSED_DISPOSITIONS | convergence.OPEN_DISPOSITIONS
    declared = set(vocabulary.SHARED_CONCEPTS["Disposition"])
    assert declared == partitioned, (
        f"`convergence.py` partitions {sorted(partitioned)} and "
        f"`vocabulary.Disposition` declares {sorted(declared)}. A declared "
        f"disposition missing from the partition counts as OPEN by the "
        f"unknown-is-open rule, so the loop never converges and nothing raises.")


@pytest.mark.parametrize("concept", sorted(vocabulary.SHARED_CONCEPTS))
def test_every_member_serialises_to_the_string_the_dict_records(
        concept: str) -> None:
    """`str`-valued so `json.dumps` needs no encoder, on both sides of the wire.

    The journal's on-disk spelling and the exit record's wire spelling are the
    same string because they are the same object AND that object is a `str`
    subclass. Drop the `str` base and both contracts still import one enum while
    `json.dumps` refuses it outright or writes `"Outcome.MERGE"` into the record.

    ⚠ ASSERTED THROUGH `json.dumps` AND NOT THROUGH `str()`, which is a
    correction this test earned by being run. On 3.11+ `str()` of a `(str, Enum)`
    member is `"Outcome.MERGE"` while `json.dumps` writes `"merge"` — the
    serialiser reads the underlying `str` content, not `__str__`. Asserting
    `str()` failed on all four concepts against code that is correct, which is a
    test asserting a property nothing depends on.
    """
    enum = getattr(vocabulary, concept)
    assert tuple(m.value for m in enum) == vocabulary.SHARED_CONCEPTS[concept]
    for member in enum:
        assert json.dumps(member) == json.dumps(member.value), (
            f"`{concept}.{member.name}` does not serialise as its value, so "
            f"`encode_event` writes something other than the shared spelling "
            f"into the durable record")
