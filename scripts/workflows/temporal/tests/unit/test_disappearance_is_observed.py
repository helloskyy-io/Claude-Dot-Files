"""Every before/after snapshot names what watches it for ABSENCE.

THE CLASS, NOT THE TWO CHANNELS THAT HAPPENED TO BE FOUND. Every comparator this
family owns reports ADDITION and MUTATION and is blind to DISAPPEARANCE:

  * `statuses_this_run_had_no_right_to` judges `before.keys() & after.keys()`,
    so a deleted id is in neither intersection;
  * `boundary_crossings` exempts a permitted path unconditionally, so the one
    file an override exists FOR is the one file whose removal is invisible;
  * `Counter` subtraction keeps positive counts, so an erased `[x]` is nothing.

Four channels were demonstrated by execution, each returning a PR URL and a green
run: `triage-candidates` deleting an operator-ruled `direction.md` row,
`plan-sprint` deleting the sprint plan, `plan-sprint` renaming the sprint plan
out of the tree, and `plan-sprint` erasing a completion tick. A review pass found
the first two. The other two were the same defect one channel over, and nothing
in the suite would have found them — which is the whole argument for this module.

WHAT THIS KEYS ON. Not the guards that exist — the SNAPSHOTS, discovered from the
source by AST. A snapshot is the thing the blindness is a property of: taking one
is what creates the obligation to say what happens if a key, or the whole file,
is gone by the after-read. Add a `before_anything = reader(...)` to a workflow
and it has no registry entry, so the suite goes red until somebody answers the
question. Reword an entry's key and it orphans. Neither failure depends on anyone
remembering that this module exists.

AND THE FILE-LEVEL HALF IS STRUCTURAL RATHER THAN REGISTERED.
`grants_that_vanished` takes the workflow's own `permitted` tuple, so a write
grant added later is covered the moment it is declared. The AST assertion at the
bottom is what stops the two calls drifting apart — a `boundary_crossings` whose
grants nothing watches for deletion is the exact state `plan-sprint` shipped in.

THE BEHAVIOURAL HALF LIVES IN `test_triage_candidates_split.py`, beside the
guards themselves: this module proves every snapshot is CLAIMED by a mechanism
and that the mechanism EXISTS; that one proves it fires.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from observer_registry import names_code, unresolved

from modules.assistant.plan import plan_activities as act
from modules.assistant.plan.plan_sprint import plan_sprint_workflow as sprint
from modules.assistant.plan.triage_candidates import triage_candidates_workflow as triage

WORKFLOWS = [
    pytest.param(triage, id="triage-candidates"),
    pytest.param(sprint, id="plan-sprint"),
]

# `modules/`, from a module inside it: plan_activities.py -> plan -> assistant.
# One level further up is the component root, which would sweep `tests/` too and
# charge a test's ASSERTION about `boundary_crossings` as a live call site.
MODULES_ROOT = Path(act.__file__).resolve().parents[2]

# The family's before-snapshot idiom: `before`, `before_status`, `before_tree`.
_SNAPSHOT = re.compile(r"^before(_[a-z_0-9]+)?$")


def _bound_names(target: ast.expr) -> list[str]:
    """Every name this assignment target binds, unpacking tuples and lists."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [n for element in target.elts for n in _bound_names(element)]
    return []


def snapshot_names(source: str) -> list[str]:
    """Every `before…` local bound from a CALL, anywhere in the source.

    Bound from a call specifically: `before = {}` or `before = x` is a rename or
    a default, not a reading of the world taken to be compared against a later
    one. It is the READ that creates the obligation.

    EVERY BINDING FORM PYTHON HAS, and that breadth is the point rather than
    completeness for its own sake. This module exists so that a snapshot added
    later cannot slip through unwatched; a census that recognised only
    `x = f()` would have left `x: T = f()`, `a, b = f()` and `(x := f())` as
    three spellings of the same escape — the module reopening its own class one
    AST node type away. Found by a reviewer attacking this probe's SCOPE rather
    than its subject, which is the technique that found two of the four channels
    this commit closes.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            targets: list[ast.expr] = list(node.targets)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Call):
            targets = [node.target]
        elif isinstance(node, ast.NamedExpr) and isinstance(node.value, ast.Call):
            targets = [node.target]
        else:
            continue
        found.update(n for t in targets for n in _bound_names(t)
                     if _SNAPSHOT.match(n))
    return sorted(found)


def _source(mod) -> str:
    return Path(mod.__file__).read_text()


# --- the probe, against its own vacuity --------------------------------------

@pytest.mark.parametrize("mod", WORKFLOWS)
def test_the_probe_finds_the_snapshots_at_all(mod) -> None:
    """POSITIVE CONTROL. Every assertion below compares two sets.

    A probe that matched nothing would make one of them empty, and an
    empty-vs-empty comparison passes over a workflow whose every snapshot is
    unwatched — which reads identically to full coverage.
    """
    names = snapshot_names(_source(mod))
    assert len(names) >= 3, (
        f"{mod.__name__}: found {names}. The probe looks for `before…` locals "
        f"bound from a call; if that idiom changed, this module checks nothing.")


def test_the_probe_would_see_a_newly_added_snapshot() -> None:
    """POSITIVE CONTROL on the property this module exists to enforce.

    The failure being prevented is a NEW snapshot arriving with nothing watching
    it for absence. That only fails the suite if the probe sees the new binding,
    so the probe is shown a synthetic one — and a non-call binding beside it,
    which is a rename rather than a reading of the world.
    """
    src = ("def run():\n"
           "    before_rows = reader(p)\n"
           "    before = other.reader(p)\n"
           "    before_alias = before_rows\n"
           "    after = reader(p)\n")
    assert snapshot_names(src) == ["before", "before_rows"]


@pytest.mark.parametrize("binding,expected", [
    ("    before_typed: dict[str, str] = reader(p)\n", ["before_typed"]),
    ("    before_a, before_b = reader(p)\n", ["before_a", "before_b"]),
    ("    before_left, (before_mid, other) = reader(p)\n",
     ["before_left", "before_mid"]),
    ("    if (before_walrus := reader(p)):\n        pass\n", ["before_walrus"]),
], ids=["annotated", "tuple-unpack", "nested-unpack", "walrus"])
def test_the_probe_sees_EVERY_binding_form_python_offers(
        binding: str, expected: list[str]) -> None:
    """SCOPE CONTROL, and the reason it exists is worth stating.

    A census recognising only `x = f()` would treat the other three spellings as
    exemptions nobody chose — this module reopening its own class one AST node
    type away, and doing it invisibly, since a snapshot the probe cannot see
    produces no failure to investigate. Found by attacking this probe's scope
    rather than its subject, which is what found two of the four channels the
    commit closes.
    """
    assert snapshot_names("def run():\n" + binding) == expected


# --- the correspondence -------------------------------------------------------

@pytest.mark.parametrize("mod", WORKFLOWS)
def test_every_snapshot_declares_what_watches_it_for_absence(mod) -> None:
    unwatched = [n for n in snapshot_names(_source(mod))
                 if n not in mod.DISAPPEARANCE_OBSERVERS]
    assert not unwatched, (
        f"{mod.__name__} takes snapshots nothing is registered against: "
        f"{unwatched}\n\nAdd each to DISAPPEARANCE_OBSERVERS naming what "
        f"notices a key — or the whole file — being GONE by the after-read. "
        f"Every comparator in this family judges only what is present on both "
        f"sides, so absence is never covered by the guard you already wrote.")


@pytest.mark.parametrize("mod", WORKFLOWS)
def test_no_entry_describes_a_snapshot_that_is_gone(mod) -> None:
    """A stale entry is a mechanism guarding nothing, and it reads as coverage.

    Kept separate from the assertion above so a failure says which direction the
    drift went: a snapshot removed while its watcher stays wired is dead code
    that a later reader will trust.
    """
    names = set(snapshot_names(_source(mod)))
    orphaned = [k for k in mod.DISAPPEARANCE_OBSERVERS if k not in names]
    assert not orphaned, (
        f"{mod.__name__}.DISAPPEARANCE_OBSERVERS registers snapshots the "
        f"workflow no longer takes: {orphaned}\n\nEither the local was renamed "
        f"— in which case re-answer 'what watches this for absence?' under the "
        f"new name rather than renaming the key — or the snapshot went, in "
        f"which case remove the mechanism too.")


@pytest.mark.parametrize("mod", WORKFLOWS)
def test_every_named_mechanism_resolves(mod) -> None:
    """An entry naming a function that does not exist is worse than a blank one.

    This is the attestation failure a free-text registry is wide open to, and it
    is the one this pass was warned about by name: writing `act.some_guard`
    beside a snapshot costs one line and looks exactly like a guard.
    """
    missing = [f"{name!r} -> {sym}"
               for name, mechanism in mod.DISAPPEARANCE_OBSERVERS.items()
               for sym in unresolved(mod, mechanism)]
    assert not missing, (
        f"{mod.__name__} names watchers that do not exist:\n  "
        + "\n  ".join(missing))


@pytest.mark.parametrize("mod", WORKFLOWS)
def test_no_entry_asserts_coverage_without_naming_it(mod) -> None:
    """There is no `JUDGEMENT` exit here, and that asymmetry is deliberate.

    A prohibition can legitimately have no artifact — a design and a milestone
    are both prose in one file. Absence always has one: either something
    compares the key sets, or nothing does. So an entry must name code, and the
    honest way to have no watcher is to not take the snapshot.
    """
    thin = [name for name, mechanism in mod.DISAPPEARANCE_OBSERVERS.items()
            if not names_code(mechanism)]
    assert not thin, (
        f"{mod.__name__} entries that assert coverage without carrying it: "
        f"{thin}")


# --- the file-level half: a grant declared is a grant watched -----------------

def _callee(call: ast.Call) -> str:
    func = call.func
    return func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")


def _arg(call: ast.Call, index: int, keyword: str) -> str | None:
    """The unparsed argument, positional or keyword. `None` if it was not passed."""
    if len(call.args) > index:
        return ast.unparse(call.args[index])
    for kw in call.keywords:
        if kw.arg == keyword:
            return ast.unparse(kw.value)
    return None


def _functions_with_boundary_calls() -> list[tuple[Path, ast.FunctionDef]]:
    """Every function in the tree that checks a path boundary. The whole tree.

    Scoped to `modules/` rather than to the planning family on purpose: the
    obligation belongs to the MECHANISM, so a build- or research-family workflow
    adopting `boundary_crossings` next year inherits this check without anyone
    remembering to widen it.
    """
    out: list[tuple[Path, ast.FunctionDef]] = []
    for path in sorted(MODULES_ROOT.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if any(_callee(c) == "boundary_crossings"
                   for c in ast.walk(node) if isinstance(c, ast.Call)):
                out.append((path, node))
    return out


def test_the_boundary_probe_finds_the_calls_it_is_meant_to() -> None:
    """POSITIVE CONTROL: the two workflows that declare a grant are both seen."""
    found = {p.name for p, _ in _functions_with_boundary_calls()}
    assert found == {"triage_candidates_workflow.py", "plan_sprint_workflow.py"}, (
        f"the boundary probe found {found}; if a workflow stopped being seen, "
        f"the assertion below is passing over it rather than checking it")


def test_every_declared_grant_is_also_watched_for_DELETION() -> None:
    """A WRITE GRANT IS NOT A DELETE GRANT, checked where the grant is declared.

    `permitted` wins over `forbidden` in `boundary_crossings` unconditionally.
    That is required — a workflow forbidden from `docs/standards/` must still
    write the two research files it exists for — and it means the exemption list
    is precisely the list of files whose removal the boundary check cannot see.
    `plan-sprint` shipped in exactly that state: deleting `sprint.md` returned a
    PR URL and a green run.

    So the two calls must carry the SAME grant expression. Comparing the
    unparsed argument rather than merely requiring both calls to be present is
    what catches the drift that matters — watching one grant tuple while
    exempting a different one is invisible in a diff and reads as coverage.
    """
    for path, fn in _functions_with_boundary_calls():
        calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call)]
        boundary = [_arg(c, 3, "permitted") for c in calls
                    if _callee(c) == "boundary_crossings"]
        vanish = [_arg(c, 2, "permitted") for c in calls
                  if _callee(c) == "grants_that_vanished"]
        for grant in boundary:
            assert grant is not None, (
                f"{path.name}:{fn.name} calls boundary_crossings with no "
                f"`permitted` argument; this check cannot tell which grants it "
                f"is exempting, so it cannot tell what is unwatched")
            assert grant in vanish, (
                f"{path.name}:{fn.name} exempts {grant} from its path boundary "
                f"and never checks those paths still EXIST. Pass the same "
                f"expression to act.grants_that_vanished. A permitted path is a "
                f"licence to edit the file, never to make it cease to exist — "
                f"and boundary_crossings is blind to that by construction, "
                f"because the exemption fires before the comparison.")


# --- `grants_that_vanished` itself, discriminating ----------------------------

_GRANT = (r"^docs/development/sprint\.md$",)
_SPRINT = "docs/development/sprint.md"


def test_a_granted_file_that_was_DELETED_is_reported() -> None:
    assert act.grants_that_vanished({}, {_SPRINT: act.ABSENT}, _GRANT) == [_SPRINT]


def test_a_granted_file_that_was_merely_EDITED_is_not() -> None:
    """DISCRIMINATOR. Editing is the whole point of the grant.

    Without this pair the function could return every granted path it saw and
    every assertion above would still pass — while failing every correct run.
    """
    assert act.grants_that_vanished({_SPRINT: "a"}, {_SPRINT: "b"}, _GRANT) == []


def test_a_granted_file_that_was_CREATED_is_not_reported() -> None:
    """`triage-candidates` legitimately creates `direction.md` from nothing.

    This is why the rule keys on the AFTER side being ABSENT rather than on the
    two sides differing: a run told to create a file must not fail for creating
    it, and `direction_ceiling` explicitly instructs it to.
    """
    grant = (r"direction\.md$",)
    assert act.grants_that_vanished({}, {"r/direction.md": "digest"}, grant) == []


def test_a_file_a_PREVIOUS_child_deleted_is_not_charged_to_this_run() -> None:
    """ABSENT on BOTH sides is somebody else's deletion, already on the branch.

    The same reasoning that makes the snapshot pair straddle the model run
    rather than diff against `origin/main`: this family's workflows share a
    branch, and a guard that charged one run for another's edit would fail a
    correct run — after which the obvious "fix" is to weaken it.
    """
    assert act.grants_that_vanished({_SPRINT: act.ABSENT}, {_SPRINT: act.ABSENT},
                                    _GRANT) == []


def test_an_UNGRANTED_path_going_absent_is_not_this_check_s_business() -> None:
    """It is `boundary_crossings`'s, where ABSENT vs BASELINE is a content change.

    Keeping the two disjoint is what makes the pair legible: this one answers
    "did a file we were allowed to write disappear?", that one answers "did we
    touch something we were not allowed to touch?"
    """
    assert act.grants_that_vanished({}, {"docs/development/phase-1.md": act.ABSENT},
                                    _GRANT) == []
