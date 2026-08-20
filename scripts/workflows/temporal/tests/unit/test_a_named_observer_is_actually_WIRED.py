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
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from observer_registry import (MODULE_SYMBOL, NS_REF,  # noqa: E402
                               workflows_declaring)

# The name suffix every authorization comparator in this tree carries. Matched by
# SUFFIX rather than by an import list, exactly as
# `test_authorization_is_observed._COMPARATOR` does.
#
# TWO SPELLINGS, AND THIS FILE SHIPPED CLAIMING BOTH WHILE READING ONE. The
# comment here asserted that `act.statuses_this_run_had_no_right_to` and
# `plan_sprint`'s module-private `_rulings_this_run_had_no_right_to` "are the
# same shape and both must be found" — true of the sibling file, whose
# `_value_guards` matches `fn.attr if isinstance(fn, ast.Attribute) else fn.id`,
# and FALSE of this one, which resolved both the registry prose and the call
# sites through `NS_REF` alone. `NS_REF` matches `act.`/`own.`-prefixed names, so
# a module-private comparator was invisible on BOTH sides.
#
# THAT IS THE FAILURE THIS FILE EXISTS TO REFUSE, in the file that refuses it.
# `observer_registry.MODULE_SYMBOL` lists `_rulings_this_run_had_no_right_to` by
# name specifically so `names_code` accepts a mechanism string pointing at it —
# the registry format ANTICIPATES such an entry. The first one written would have
# passed `names_code`, been invisible to `unresolved` (NS_REF-only) and invisible
# here, and the registry would have read as coverage over a boundary nothing
# checks. Both sides now admit both spellings, and `test_the_extractor_MISSES_NO_
# COMPARATOR_the_registry_prose_NAMES` is what keeps them admitting the same set
# rather than this comment saying so.
_COMPARATOR = "this_run_had_no_right_to"

# Every way a comparator can be SPELLED in mechanism prose, whatever namespace it
# hangs off. Used only to cross-check the structured extractor below — a regex
# this loose would flag ordinary sentences if it decided the population itself.
_ANY_SPELLING = re.compile(rf"\b([a-z_][a-z_0-9]*{_COMPARATOR})\b")


def _called_names(tree: ast.Module) -> set[str]:
    """Every call in the module, spelled the way the registry would name it.

    `act.candidate_sizes(...)` -> `"act.candidate_sizes"`; a bare
    `_rulings_this_run_had_no_right_to(...)` -> `"_rulings_this_run_had_no_right_
    to"`. Two shapes because the registry has two spellings, and a set keyed the
    same way on both sides is what lets the rule be a plain subtraction.

    NAMESPACED CALLS STAY NAMESPACED, because the registry writes `act.` and
    `own.` and the two namespaces hold different things. Matching on the
    attribute alone would let a call to `own.statuses_this_run_had_no_right_to`
    satisfy an entry that named `act.statuses_this_run_had_no_right_to`, which is
    a different guard over a different file — and adding bare names must not
    reopen that in the other direction either, which is why a bare call is stored
    under its bare name and never under a namespace it does not have.
    """
    named: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
            named.add(f"{fn.value.id}.{fn.attr}")
        elif isinstance(fn, ast.Name):
            named.add(fn.id)
    return named


def _comparators_named(mechanisms) -> set[str]:
    """Every comparator the registry's prose points at, in either spelling.

    THE TWO RESOLVERS ARE `observer_registry`'S, NOT COPIES. `names_code` accepts
    an entry that matches `NS_REF` **or** `MODULE_SYMBOL`, so those two are
    exactly the set of spellings a mechanism string may legally use; asking the
    same pair here is what makes this population equal to the one the registry
    admits, instead of a second opinion that drifts from it.
    """
    found: set[str] = set()
    for mechanism in mechanisms:
        found |= {f"{ns}.{attr}" for ns, attr in NS_REF.findall(mechanism)
                  if attr.endswith(_COMPARATOR)}
        found |= {sym for sym in MODULE_SYMBOL.findall(mechanism)
                  if sym.endswith(_COMPARATOR)}
    return found


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
    called = _called_names(source)
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

# The two module-private cases, added 2026-08-20 with the spelling this file used
# to claim and not read. `plan_sprint._rulings_this_run_had_no_right_to` is the
# live example — module-private, listed by `observer_registry.MODULE_SYMBOL`, and
# callable only bare.
_MODULE_PRIVATE_WIRED = """
def _rulings_this_run_had_no_right_to(before, after):
    return []

def run():
    if _rulings_this_run_had_no_right_to(before, after):
        raise RuntimeError("no")
"""

_MODULE_PRIVATE_MENTIONED = """
NOTES = {"a prohibition": "_rulings_this_run_had_no_right_to watches it"}

def _rulings_this_run_had_no_right_to(before, after):
    return []
"""


@pytest.mark.parametrize("label,snippet,key,expected", [
    ("a wired guard", _WIRED, "act.sizes_this_run_had_no_right_to", True),
    ("named in prose, never called", _MERELY_MENTIONED,
     "act.sizes_this_run_had_no_right_to", False),
    ("called on the other namespace", _WRONG_NAMESPACE,
     "act.sizes_this_run_had_no_right_to", False),
    ("a wired module-private guard", _MODULE_PRIVATE_WIRED,
     "_rulings_this_run_had_no_right_to", True),
    ("module-private, defined and named, never called", _MODULE_PRIVATE_MENTIONED,
     "_rulings_this_run_had_no_right_to", False),
    ("a bare call does not discharge a namespaced entry", _MODULE_PRIVATE_WIRED,
     "act._rulings_this_run_had_no_right_to", False),
], ids=["wired", "prose-only", "wrong-namespace", "module-private-wired",
        "module-private-prose-only", "bare-is-not-namespaced"])
def test_the_predicate_SEPARATES_a_wired_guard_from_a_mentioned_one(
        label: str, snippet: str, key: str, expected: bool) -> None:
    """Both answers, on source written for this test alone.

    THE THIRD CASE IS THE ONE WORTH HAVING. `wired` and `prose-only` differ by
    the presence of a call, which almost any recogniser separates. `wrong-
    namespace` differs only in the NAME the attribute hangs off — it is the case
    a predicate matching on `node.func.attr` alone gets wrong, and getting it
    wrong means an `own.` guard over one file silently discharges an `act.` entry
    about another.

    THE LAST THREE ARE THE WIDENING'S OWN CONTROLS. `module-private-wired` is the
    case this file could not see at all until 2026-08-20; `module-private-prose-
    only` proves the widening did not buy that by accepting a DEFINITION as a
    call, which is the cheapest wrong way to make the first case pass; and
    `bare-is-not-namespaced` proves it did not reopen the `wrong-namespace` hole
    from the other side, by letting a bare call satisfy an `act.` entry.
    """
    called = _called_names(ast.parse(snippet))
    assert (key in called) is expected, (
        f"{label}: the predicate saw {sorted(called)}")


def test_the_extractor_MISSES_NO_COMPARATOR_the_registry_prose_NAMES() -> None:
    """THE CLASS CHECK: the structured extractor sees every spelling the prose uses.

    KEYED ON THE PROPERTY, NOT ON THE SPELLING THAT WAS MISSING. `_comparators_
    named` reads mechanism prose through `NS_REF` and `MODULE_SYMBOL`, and the
    defect this closes was that the second of those was absent — a whole spelling
    the registry admits, dropped silently, in a file whose comment said it was
    read. Adding `MODULE_SYMBOL` fixes the instance. What stops the NEXT spelling
    from being dropped the same way is asking the question generically: sweep the
    same prose with a regex that knows only the name SUFFIX, and require the
    structured extractor to have found every comparator it turns up.

    WHY THE LOOSE REGEX IS NOT THE POPULATION ITSELF. It would match a comparator
    named inside a sentence about some other workflow, or a name in an example,
    and demanding a call for those would fail correct entries. It is a strictly
    wider net used only as a CONTROL: the structured extractor may not miss what
    it catches, and the two agreeing is the assertion.

    ITS DISCRIMINATING POWER TODAY IS ZERO, AND THAT IS SAID HERE RATHER THAN
    DISCOVERED LATER. No registry currently names a module-private comparator —
    measured: `plan-feature` 4/4, `plan-verify` 4/4, `triage-candidates` 2/2,
    `plan-sprint` 0/0 — so both sets agree whatever `_comparators_named` reads,
    and reverting the widening leaves this green. `test_the_extractor_READS_
    BOTH_SPELLINGS` below is what actually fails on that revert; this one becomes
    load-bearing the moment the first such entry is written, which is exactly the
    moment nobody will be looking.
    """
    missed: list[str] = []
    for mod, _, name in _WORKFLOWS:
        mechanisms = list(mod.MAY_NOT_OBSERVERS.values())
        structured = {c.rsplit(".", 1)[-1] for c in _comparators_named(mechanisms)}
        loose = {m for text in mechanisms for m in _ANY_SPELLING.findall(text)}
        for dropped in sorted(loose - structured):
            missed.append(f"{name}: {dropped}")
    assert not missed, (
        f"these comparators are named in mechanism prose and the structured "
        f"extractor does not see them: {missed}. `_comparators_named` resolves "
        f"through `observer_registry.NS_REF` and `MODULE_SYMBOL` — the two "
        f"spellings `names_code` accepts — so a comparator the prose names and "
        f"this misses passes `names_code`, is invisible to `unresolved`, and is "
        f"invisible to the wiring rule above: the entry reads as coverage over a "
        f"boundary nothing checks. Teach the resolver the spelling in "
        f"`observer_registry`, where both consumers pick it up.")


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


def test_the_extractor_READS_BOTH_SPELLINGS() -> None:
    """`_comparators_named` on prose written for this test alone.

    THE CONTROL THE SWEEP ABOVE CANNOT BE. That one compares two readings of the
    LIVE registries, and every live mechanism string spells its comparators
    `act.`-prefixed — so it agrees with itself under a resolver that has never
    heard of the module-private spelling. This asserts on a mechanism string that
    contains both, which is the only place the widening is currently observable.

    It also pins the discrimination the loose regex must NOT be allowed to erode:
    `act.candidate_sizes` is a snapshot READER named in the same sentence and it
    is deliberately absent from the result, because demanding a direct call for
    readers would fail three correct entries — see the module docstring.
    """
    mechanism = ("act.candidate_decisions and act.candidate_sizes snapshotted "
                 "either side of the run, compared by "
                 "act.sizes_this_run_had_no_right_to for the candidate columns "
                 "and by _rulings_this_run_had_no_right_to for the ruling")
    assert _comparators_named([mechanism]) == {
        "act.sizes_this_run_had_no_right_to",
        "_rulings_this_run_had_no_right_to"}, (
        "the module-private spelling is one `observer_registry.MODULE_SYMBOL` "
        "admits and `names_code` accepts, so an entry may legally use it; an "
        "extractor that reads only `NS_REF` drops it silently and the wiring "
        "rule never asks about it.")
