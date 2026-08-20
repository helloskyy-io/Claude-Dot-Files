"""A registry entry naming a comparator must name one the workflow CALLS.

THE HOLE THIS CLOSES IS ONE `test_authorization_is_observed` CANNOT SEE, and the
two files are worth reading together. That one asks whether every prohibition has
an entry and whether every symbol an entry names RESOLVES — `hasattr(act,
"sizes_this_run_had_no_right_to")`. Resolution is a property of the activities
module. It says nothing about the workflow, so a mechanism string may name a real
comparator that the workflow never invokes, and the registry then reads as
coverage while the boundary is wide open.

THAT IS NOT HYPOTHETICAL. `plan-feature` and `plan-verify` both declared

    "Set `decision`, `size`, `status`, or another filer's `component` ...":
        "act.candidate_decisions, act.candidate_sizes, act.candidate_statuses
         and act.candidate_components snapshotted either side of the run,
         compared by act.sizes_this_run_had_no_right_to, ..."

and neither called `act.sizes_this_run_had_no_right_to` anywhere. `act.candidate_
sizes` had no caller either, and `plan_activities._SIZES` — the closed vocabulary
`size` is checked against — had no reader at all. Every existing test was green:
the prohibition had an entry, the entry named code, and the code existed. The
column that routes `plan-candidates` into committing a `docs/development/<name>/`
directory was unguarded in both workflows that hold a write grant on the file.

WHY THE COMPARATOR FAMILY AND NOT EVERY NAMED SYMBOL. A registry entry legitimately
names helpers it reaches INDIRECTLY: `own.plan_boxes` is described as "act.checked_
boxes over every top-level doc", and `act.checked_boxes` is called inside
`plan_boxes` rather than in the workflow. Demanding a direct call for those would
fail three correct entries. A `*this_run_had_no_right_to` comparator has no such
excuse — it takes a before-map and an after-map that only the workflow holds, so
the workflow is the only place it can be called from. The narrow property is the
one that is actually true, and a check that is true is worth more than a broad one
carrying a waiver table.

WHAT THIS GUARD DOES NOT LOOK AT:

  * **Whether the guard it found does anything with the result.** A workflow
    could call the comparator and discard the list. `test_authorization_is_
    observed._value_guards` is the file that pairs a comparator call with the
    `if offender: raise` around it, and `test_EVERY_value_guard_NAMES_THE_VALUE_
    THAT_MOVED` is what holds its message. This asks only that the call exists,
    because that is the half that was missing.
  * **Snapshot READERS.** `act.candidate_sizes` was equally uncalled, and it is
    outside this population for the reason above — a reader may legitimately be
    reached through another helper. It is covered transitively: a comparator
    needs a before-map and an after-map, so wiring the comparator is what forces
    the reader to be called.
  * **Comparators the registry never mentions.** The population is what the
    registry NAMES. A comparator that exists, is called, and is absent from every
    mechanism string is a documentation gap this cannot see;
    `test_every_prohibition_in_the_prompt_has_an_entry` approaches that from the
    prompt side.
  * **Any workflow that declares no registry.** Discovery is
    `workflows_declaring`, shared with the two sibling registries so the three
    cannot drift about which workflows exist.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from observer_registry import NS_REF, workflows_declaring  # noqa: E402

# The name suffix every authorization comparator in this tree carries. Matched by
# SUFFIX rather than by an import list, exactly as
# `test_authorization_is_observed._COMPARATOR` does — `act.statuses_this_run_had_
# no_right_to` and `plan_sprint`'s module-private `_rulings_this_run_had_no_right_
# to` are the same shape and both must be found.
_COMPARATOR = "this_run_had_no_right_to"


def _called_attributes(tree: ast.Module) -> set[str]:
    """Every `<name>.<attr>(...)` call in the module, as `"<name>.<attr>"`.

    NAMESPACED RATHER THAN BARE, because the registry writes `act.` and `own.`
    and the two namespaces hold different things. Matching on the attribute alone
    would let a call to `own.statuses_this_run_had_no_right_to` satisfy an entry
    that named `act.statuses_this_run_had_no_right_to`, which is a different
    guard over a different file.
    """
    return {f"{node.func.value.id}.{node.func.attr}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)}


def _comparators_named(mechanisms) -> set[str]:
    """Every `act.`/`own.` comparator the registry's prose points at."""
    return {f"{ns}.{attr}"
            for mechanism in mechanisms
            for ns, attr in NS_REF.findall(mechanism)
            if attr.endswith(_COMPARATOR)}


_WORKFLOWS = workflows_declaring("MAY_NOT_OBSERVERS")


def test_the_sweep_FINDS_COMPARATORS_AT_ALL() -> None:
    """POSITIVE CONTROL on the population, against this file's own vacuity.

    The rule below iterates whatever `_comparators_named` returns. A `NS_REF`
    that stopped matching, a comparator family renamed, or a discovery that
    imported nothing would all yield an empty set — and an empty set passes the
    rule silently while reporting that every registry entry is wired. That is the
    permanent green this file was written to refuse, so it may not be reachable
    from this file.

    The floor is deliberately loose: it asks that the sweep is READING the
    registries, not how many entries they happen to hold today.
    """
    named = {c for mod, _, _ in _WORKFLOWS
             for c in _comparators_named(mod.MAY_NOT_OBSERVERS.values())}
    assert _WORKFLOWS, "no workflow declaring MAY_NOT_OBSERVERS was discovered"
    assert len(named) >= 2, (
        f"the sweep found {len(named)} comparator(s) named across "
        f"{len(_WORKFLOWS)} registry(ies): {sorted(named)}. Comparators are "
        f"matched by the `{_COMPARATOR}` name suffix through `observer_registry."
        f"NS_REF`; if either changed, this file is green over registries it is no "
        f"longer reading.")


@pytest.mark.parametrize(
    "mod", [w[0] for w in _WORKFLOWS], ids=[w[2] for w in _WORKFLOWS])
def test_every_comparator_the_registry_NAMES_is_one_the_workflow_CALLS(mod) -> None:
    """THE RULE. Naming a comparator costs one line and reads exactly like coverage.

    The failure this catches is silent in the direction that matters: the entry
    describes a boundary, the reviewer reads the entry, and the boundary is not
    there. A model that writes to the column is not stopped, and nothing in the
    run reports anything at all.
    """
    source = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    called = _called_attributes(source)
    unwired = sorted(_comparators_named(mod.MAY_NOT_OBSERVERS.values()) - called)
    assert unwired == [], (
        f"{Path(mod.__file__).name} names {unwired} in a MAY_NOT_OBSERVERS "
        f"mechanism and never calls them. A comparator takes the before-map and "
        f"the after-map, both of which only this workflow holds, so there is "
        f"nowhere else it could be called from — the entry is an attestation "
        f"with no mechanism behind it. Either wire the guard (snapshot before, "
        f"read after, compare, raise) or stop claiming it in the registry.")


# --- the predicate, exercised on source this tree does not contain ----------
#
# `test_a_census_guard_proves_its_own_predicate` requires this and the
# requirement is the point: everything above is green whenever
# `_called_attributes` returns too MUCH, and "too much" is what a widened AST
# match looks like. The snippets below are self-contained string literals rather
# than fixtures shared with any workflow, so a miss here is a fact about the
# predicate rather than about somebody else's file.

_WIRED = """
def run():
    before = act.candidate_sizes(p)
    after = act.candidate_sizes(p)
    if act.sizes_this_run_had_no_right_to(before, after):
        raise RuntimeError("no")
"""

_MERELY_MENTIONED = """
NOTES = {"a prohibition": "act.sizes_this_run_had_no_right_to watches it"}

def run():
    before = act.candidate_sizes(p)
"""

_WRONG_NAMESPACE = """
def run():
    if own.sizes_this_run_had_no_right_to(before, after):
        raise RuntimeError("no")
"""


@pytest.mark.parametrize("label,snippet,expected", [
    ("a wired guard", _WIRED, True),
    ("named in prose, never called", _MERELY_MENTIONED, False),
    ("called on the other namespace", _WRONG_NAMESPACE, False),
], ids=["wired", "prose-only", "wrong-namespace"])
def test_the_predicate_SEPARATES_a_wired_guard_from_a_mentioned_one(
        label: str, snippet: str, expected: bool) -> None:
    """Both answers, on source written for this test alone.

    THE THIRD CASE IS THE ONE WORTH HAVING. `wired` and `prose-only` differ by
    the presence of a call, which almost any recogniser separates. `wrong-
    namespace` differs only in the NAME the attribute hangs off — it is the case
    a predicate matching on `node.func.attr` alone gets wrong, and getting it
    wrong means an `own.` guard over one file silently discharges an `act.` entry
    about another.
    """
    called = _called_attributes(ast.parse(snippet))
    assert ("act.sizes_this_run_had_no_right_to" in called) is expected, (
        f"{label}: the predicate saw {sorted(called)}")


def test_the_predicate_reads_the_REGISTRY_prose_not_the_code() -> None:
    """`_comparators_named` must pick the comparator out of a human sentence.

    Mechanism values are prose full of capitalised words and helper names. This
    asserts the extractor takes the comparator and leaves the readers, because
    an extractor that returned every named symbol would demand a direct call for
    `act.checked_boxes` — reached only through `own.plan_boxes` — and fail
    correct entries until somebody added a waiver table.
    """
    mechanism = ("act.candidate_decisions and act.candidate_sizes snapshotted "
                 "either side of the run, compared by "
                 "act.sizes_this_run_had_no_right_to and own.checked_boxes")
    assert _comparators_named([mechanism]) == {"act.sizes_this_run_had_no_right_to"}
