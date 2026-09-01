"""Every field of the run context says what it is, or the suite goes red.

WHY THIS EXISTS, AND IT IS NOT THE ENUMERATION THE RE-PLAN DELETED. Workflow
Decomposition Phase 4 originally asked for a published table of every derived
value in the fleet, held honest by a check that read its population off the tree.
That check ran cold and returned nothing usable: `@derived`, `DERIVED_VALUES`,
`register_derivation` and `DERIVATION_SITES` returned ZERO hits across 225 Python
files, and three of six known derived values reached none of the five named
resolvers. There is no enumerable population of derivations, so the requirement
was deleted rather than weakened.

A FROZEN DATACLASS'S FIELDS *ARE* AN ENUMERABLE POPULATION. `dataclasses.fields()`
returns them by construction — no marker convention, no tree sweep, no hand-kept
list — which is the reason the deleted requirement is not needed rather than a
smaller version of it. The population problem that killed it does not exist here.

AND FIELD EXISTENCE IS NOT FIELD DOCUMENTATION, WHICH IS THE WHOLE OF THIS
MODULE. The re-plan is right that a field cannot drift from the enumeration —
it IS the enumeration. That says nothing about whether the field is DOCUMENTED,
and two of the five safe-derivation properties, the published ALGORITHM and the
stated SCOPE OF EFFECT, are exactly that documentation. Without this, all five
requirements could pass with eight of nine fields carrying nothing, and a tenth
field added a year later would carry nothing with nothing going red. That is the
deleted clause's own property — *a table checked against itself cannot see what
was never added to it* — reappearing one level down.

⚠ WHAT THIS CANNOT DO, said plainly so nobody over-reads it. It asserts each of
the four parts is PRESENT and NON-EMPTY. It does NOT assert any of them is TRUE:
a field naming the wrong marker passes here. That limit is accepted rather than
worked around — the truth of an algorithm sentence is a judgement, and the
failure this requirement addresses is ABSENCE, not error. It also says nothing
about any object other than `RunContext`; a second frozen boundary object would
need its own line in `_POPULATION`.

THE SHAPE IS THIS REPO'S, NOT INVENTED HERE — `test_promotion_guard_prose_
figures_are_DERIVED.py` and `test_a_prose_COUNT_of_a_collection_is_DERIVED.py`
both bind a claim to something that computes it rather than to a restatement.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

FLEET = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FLEET / "scripts"))

from dispatch_context import RunContext, context_field_documentation  # noqa: E402
from dispatch_identity import derivation  # noqa: E402

#: The four things every field must say about itself. `marker` and `override`
#: are the two properties this fleet already satisfied structurally; `algorithm`
#: and `scope` are the two that were absent, and they are why this check exists.
#: Read off `derivation()`'s own contract rather than restated, so adding a fifth
#: part there cannot leave this checking four.
REQUIRED = tuple(sorted(derivation(marker="x", algorithm="x",
                                   override="x", scope="x")))

#: How many fields `RunContext` was written with. Named once so the floor below
#: and its failure message cannot state different numbers — which they did, at
#: `>= 6` against a message saying nine.
_WRITTEN_WITH = 9

#: Every frozen boundary object whose fields carry derived values. One entry
#: today. A second object added without a row here is invisible to this check —
#: which is a real limit and is why it is a named constant rather than a literal.
_POPULATION = (RunContext,)


def _fields(cls):
    return list(dataclasses.fields(cls))


@pytest.mark.parametrize("cls", _POPULATION, ids=lambda c: c.__name__)
def test_the_population_is_NOT_EMPTY(cls) -> None:
    """THE VACUITY FLOOR. Every assertion below is per-field; zero fields passes.

    A refactor that split the context, renamed it, or turned it into a plain
    class would leave `dataclasses.fields()` returning an empty list or raising,
    and the parametrised checks below would report green over nothing.
    """
    assert dataclasses.is_dataclass(cls), f"{cls.__name__} is not a dataclass"
    assert len(_fields(cls)) >= _WRITTEN_WITH, (
        f"{cls.__name__} has {len(_fields(cls))} fields — it was written with "
        f"{_WRITTEN_WITH}, so either the object has been gutted or this check is "
        f"no longer reading it. The floor is the FULL count deliberately: a floor "
        f"below it (this said `>= 6`) lets three fields be dropped while the "
        f"message still insists nine were expected, which is a message and an "
        f"assertion disagreeing about the same fact.")

    # AND THE MODULE'S OWN ACCESSOR AGREES WITH `dataclasses.fields()`. The
    # object exports `context_field_documentation()` as the one place the
    # population is obtained; a helper nothing calls is a claim nothing checks.
    assert set(context_field_documentation()) == {f.name for f in _fields(cls)}, (
        "`context_field_documentation()` and `dataclasses.fields()` disagree "
        "about the population, so the module's stated accessor is not the one "
        "this guard reads")
    # The three inherited from `RunIdentity` must be in the population too: a
    # subclass that stopped extending it would silently halve what is checked.
    names = {f.name for f in _fields(cls)}
    assert {"run_id", "writer", "minted"} <= names, (
        f"{cls.__name__} no longer carries identity's own fields, so this check "
        f"has stopped covering the three values a run derives FIRST")


@pytest.mark.parametrize("cls", _POPULATION, ids=lambda c: c.__name__)
def test_every_field_NAMES_its_marker_algorithm_override_and_scope(cls) -> None:
    """The four-part statement, on every field, read off the object itself."""
    missing = []
    for f in _fields(cls):
        for part in REQUIRED:
            value = f.metadata.get(part)
            if not (isinstance(value, str) and value.strip()):
                missing.append(f"{cls.__name__}.{f.name}: {part}")
    assert not missing, (
        "these fields do not say what they are:\n"
        + "\n".join(f"  {m}" for m in missing)
        + "\n\nEvery field carries `field(metadata=derivation(marker=…, "
          "algorithm=…, override=…, scope=…))`. `override` states the flag or "
          "says it has none — an absent override and an undocumented one are "
          "not the same fact. `scope` answers *what else is wrong if this value "
          "is wrong*, which is what makes the run's echo readable rather than "
          "decorative."
    )


@pytest.mark.parametrize("cls", _POPULATION, ids=lambda c: c.__name__)
def test_a_scope_of_effect_says_what_BREAKS_not_what_the_value_IS(cls) -> None:
    """The one quality floor, and it is deliberately the only one.

    A `scope` reading "the repository root" restates the field and answers
    nothing; the property is *what else is wrong if this is wrong*. Length is a
    crude proxy and it is the honest one available — the truth of the sentence is
    a judgement no check reaches, so this asserts only that somebody wrote a
    sentence rather than a noun phrase. `algorithm` gets the same floor for the
    same reason.
    """
    thin = [f"{f.name}.{part} = {f.metadata[part]!r}"
            for f in _fields(cls) for part in ("scope", "algorithm")
            if len(f.metadata[part].split()) < 8]
    assert not thin, (
        "these are noun phrases where a statement belongs:\n"
        + "\n".join(f"  {t}" for t in thin)
        + "\n\n`scope` answers *what else is wrong if this value is wrong*. "
          "`resolve_repo_root`'s own comments are the model: worktrees and logs "
          "both hang off it, so a root at a subdirectory scatters both where "
          "cleanup never looks — and then deletes the logs with the workspace."
    )


def test_THE_CHECK_FIRES_when_a_field_stops_stating_itself() -> None:
    """A CONTROL ON THE PREDICATE, driven on a throwaway dataclass.

    DERIVED FROM THE CLAIM THE MODULE MAKES ABOUT ITSELF, not from whatever is
    easy to break: the module claims a field ADDED LATER cannot arrive
    undocumented, so the control adds one. Each case names which part is absent,
    because a control that fires for the wrong reason proves nothing.
    """
    ok = derivation(marker="a git directory on disk", algorithm="reads it",
                    override="the --repo flag", scope="everything hangs off it")

    def sample(**overrides):
        meta = {**ok, **overrides}
        @dataclasses.dataclass(frozen=True)
        class Sample:
            documented: str = dataclasses.field(metadata=ok)
            added_later: str = dataclasses.field(metadata=meta)
        return Sample

    for part in REQUIRED:
        cls = sample(**{part: ""})
        holes = [f"{f.name}:{p}" for f in dataclasses.fields(cls) for p in REQUIRED
                 if not (isinstance(f.metadata.get(p), str) and f.metadata[p].strip())]
        assert holes == [f"added_later:{part}"], (
            f"blanking {part!r} on one field produced {holes} — the predicate is "
            f"not isolating the part it claims to")

    # A field with NO metadata at all — the shape a new field takes when its
    # author writes `name: str` and stops.
    @dataclasses.dataclass(frozen=True)
    class Undocumented:
        documented: str = dataclasses.field(metadata=ok)
        added_later: str = ""

    holes = [f.name for f in dataclasses.fields(Undocumented)
             if not all(f.metadata.get(p) for p in REQUIRED)]
    assert holes == ["added_later"], (
        f"a field declared with no metadata was not caught: {holes}")


def test_THE_CHECK_IS_SILENT_on_a_fully_stated_field() -> None:
    """A NEGATIVE CONTROL. A check that fails correct code gets deleted, rightly."""
    @dataclasses.dataclass(frozen=True)
    class Fine:
        value: str = dataclasses.field(metadata=derivation(
            marker="the presence of a .git directory, read rather than guessed",
            algorithm="git rev-parse --show-toplevel, run in the repo target",
            override="none — this value is declared by the caller",
            scope="wrong means every path below it is resolved somewhere else"))

    assert all(all(f.metadata.get(p, "").strip() for p in REQUIRED)
               for f in dataclasses.fields(Fine))
