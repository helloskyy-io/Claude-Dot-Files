"""A launch that came back is not a launch that ANSWERED.

THE CLASS: a subprocess reply whose OUTPUT is read as evidence while its
OUTCOME is never consulted. `run_bounded` renders a hang as `returncode=124,
stdout=""`, so an unread return code turns "git did not answer" into "the answer
is nothing" — and at a caller that phrases nothing as a negative, into a
confident wrong fact.

WHY A CHECK AND NOT THREE CORRECTIONS. The sibling guard
`test_every_subprocess_the_fleet_launches_is_bounded.py` proves every launch has
a CEILING. Nothing proved any bounded reply was READ, and the gap was discharged
instead by a sentence in `TimedOutProcess`'s docstring asserting that every
converted caller already branched on `returncode`. Six sites route through
`run_bounded`; the sentence named three behaviours, one of which belongs to a
function that is not one of the seven, and `observe_outcome`'s `git status` read —
which IS one of the seven — dropped the code and printed "Uncommitted changes:
none" for a worktree it had never read. A reviewer found it two passes later.
The claim was the wrong instrument: a docstring cannot go red.

THE CHECK IS PER-BINDING, NOT PER-NAME, AND THAT IS WHAT MAKES IT CATCH THE
ORIGINATING DEFECT. In the defective code `rc` was bound, dropped, then rebound
and read eleven lines further down. "Is this name used somewhere in the
function" is GREEN on it — which is also why ruff's F841 said nothing and why
nobody's linter would have. What this asks instead is whether THIS binding is
read before the name is bound again.

TWO SHAPES, because the defect arrived through the second one:

  * DIRECT — `r = run_bounded(...)`. The reply object itself is bound, so
    `r.returncode`, `is_timed_out(r)`, or handing `r` onward whole (returning it,
    passing it to a call) all count as consulting the outcome.
  * VIA A CODE-RETURNING HELPER — a function whose `return` is a tuple carrying
    some reply's `.returncode`. Every caller then unpacks a code, and the code
    must be read for THAT unpacking. This shape has no members in the tree today,
    because the fix for the originating defect deleted the only one: `_git` now
    raises instead of returning `tuple[int, str]`. A rule with no members is
    exactly what should be kept — it is the shape that came back once already,
    and the controls below are what prove the rule still discriminates while its
    population is empty.

WHAT THIS GUARD DOES NOT LOOK AT — each a real gap, stated because a guard read
as broader than it is does more harm than a narrow one:

  * **Whether reading the code leads anywhere.** `if r.returncode != 0: pass`
    satisfies it. It asks that the outcome was consulted, not that the
    consultation was wise; the latter is what code review is for.
  * **Launches that never bind their reply.** `subprocess.run(cmd)` as a bare
    expression statement is outside the population — there is no binding to
    trace. The bounded-launch guard sees those; this one does not.
  * **`Popen`.** A streaming child has no single reply object and its outcome
    arrives through `returncode` after `wait()`, on a path this visitor does not
    model. The two sites are the same two the sibling guard exempts by name.
  * **Reply objects that escape into a container or a closure.** `results.append(
    run_bounded(...))` binds nothing, and a reply captured by a nested function
    is read outside the range this traces. Neither shape exists in the tree; both
    would pass silently.
  * **Helpers that return a code through anything but a tuple literal** — a
    dataclass, a dict, a bare `int`. The one member this class ever had returned
    a tuple; a second spelling would need adding here, and the failure direction
    is that a new spelling escapes rather than that a good one is blocked.

THE POPULATION FIGURE IS DERIVED, NOT ASSERTED. `test_the_census_matches_the_
tree` fails when the number of launch bindings changes, so the sentence "seven
sites route through `run_bounded`" cannot go stale the way the docstring this
guard replaces did. That is the discipline this file exists to demonstrate: a
coverage claim is either an assertion that goes red, or it is a hedge.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_TREE = Path(__file__).resolve().parents[2]
_ROOTS = (_TREE / "modules", _TREE / "scripts")

# The launch helpers whose reply carries an outcome nobody may drop. Spelled as
# attribute-or-bare so `shared.run_bounded(...)` and `run_bounded(...)` are one
# rule; `subprocess.run` is here because the two layers that must not import the
# assistant tree bound it inline with their own budget.
_LAUNCHERS = frozenset({"run_bounded", "run"})

# Reading any of these consults the OUTCOME rather than the payload.
_OUTCOME_ATTRS = frozenset({"returncode", "timed_out"})
_OUTCOME_CALLS = frozenset({"is_timed_out"})

# DELIBERATE DISCARDS, BY NAME AND WITH THE REASON, so the exemption cannot
# spread by resemblance. `wait_for_ci` is the one site in the fleet where the
# return code is not merely unread but MUST NOT be the discriminator: `gh pr
# checks` exits non-zero whenever any check is FAILING or PENDING, so a red
# pipeline and a broken `gh` are identical through it. That loop separates
# "answered" from "failed" by whether the payload PARSES — which is a stricter
# test than the code, not a weaker one — and a timed-out reply lands in the same
# failed-read branch an unparseable one already did.
_OUTCOME_NOT_THE_DISCRIMINATOR = frozenset({
    "wait_for_ci",
})


def _own_nodes(node: ast.AST):
    """Walk `node`, but STOP at a nested function — its body is its own scope.

    `ast.walk` descends through everything, and that is wrong twice over here.
    It double-counts: `observe_outcome`'s census picked up the `run_bounded` call
    inside its nested `_git`, and `_git`'s own census picked up the same line, so
    a one-line helper read as two population members. And it mis-scopes: a name
    bound inside the helper could have been satisfied by a load in the enclosing
    function that never sees it. Caught by this file's own derived census
    disagreeing with the count in its docstring, which is the census earning its
    keep on the pass that wrote it.
    """
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _own_nodes(child)


class _Bindings(ast.NodeVisitor):
    """Every binding of a launch reply, and whether that binding was consulted.

    Scoped per function by `_own_nodes`, which prunes at a nested `def`, so a
    name bound in a helper cannot be satisfied by a load in its parent and a
    helper's launch belongs to the helper alone.
    """

    def __init__(self, rel: str) -> None:
        self.rel = rel
        self.unchecked: list[tuple[str, str, int, str]] = []
        self.total_bindings = 0
        self._fn_stack: list[str] = []

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _is_launch(node: ast.AST) -> bool:
        if not isinstance(node, ast.Call):
            return False
        f = node.func
        if isinstance(f, ast.Attribute):
            return f.attr in _LAUNCHERS
        return isinstance(f, ast.Name) and f.id in _LAUNCHERS

    @staticmethod
    def _code_index(fn: ast.FunctionDef) -> int | None:
        """Which tuple slot does this helper return a `.returncode` in?"""
        for node in ast.walk(fn):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
                for i, elt in enumerate(node.value.elts):
                    if isinstance(elt, ast.Attribute) and elt.attr == "returncode":
                        return i
        return None

    @staticmethod
    def _binding_lines(body: list[ast.stmt], name: str) -> list[int]:
        out = []
        for node in body:
            for n in _own_nodes(node):
                if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Store):
                    out.append(n.lineno)
        return sorted(out)

    @classmethod
    def _consulted(cls, body: list[ast.stmt], name: str,
                   bound_at: int, rebound_at: int, *, plain_load: bool) -> bool:
        """Is THIS binding of `name` consulted before the name is bound again?

        `plain_load` IS THE DIFFERENCE BETWEEN THE TWO SHAPES, and getting it
        wrong in either direction breaks the guard. When the binding is a REPLY
        OBJECT, merely mentioning it proves nothing — `r.stdout` is the payload,
        and reading the payload while ignoring the outcome IS the defect. When
        the binding is a RETURN CODE, the name IS the outcome, so any load of it
        counts and demanding an attribute would flag every correct caller.
        """
        for node in body:
            for n in _own_nodes(node):
                if not (bound_at < getattr(n, "lineno", -1) < rebound_at):
                    continue
                if (plain_load and isinstance(n, ast.Name) and n.id == name
                        and isinstance(n.ctx, ast.Load)):
                    return True
                # `x.returncode` / `x.timed_out`
                if (isinstance(n, ast.Attribute) and n.attr in _OUTCOME_ATTRS
                        and isinstance(n.value, ast.Name) and n.value.id == name):
                    return True
                # `is_timed_out(x)`, or `x` handed onward whole to any call
                if isinstance(n, ast.Call):
                    fname = n.func.id if isinstance(n.func, ast.Name) else (
                        n.func.attr if isinstance(n.func, ast.Attribute) else "")
                    for a in n.args:
                        if isinstance(a, ast.Name) and a.id == name:
                            if fname in _OUTCOME_CALLS:
                                return True
                            return True  # handed onward: the callee owns it now
                # `return x`
                if (isinstance(n, ast.Return) and isinstance(n.value, ast.Name)
                        and n.value.id == name):
                    return True
        return False

    # --- the walk ------------------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef):  # noqa: N802
        self._fn_stack.append(node.name)
        self._scan(node)
        self.generic_visit(node)
        self._fn_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # noqa: N815

    def _scan(self, fn: ast.FunctionDef) -> None:
        if fn.name in _OUTCOME_NOT_THE_DISCRIMINATOR:
            return
        # SHAPE 1 — the reply object itself is bound.
        for stmt in fn.body:
            for n in _own_nodes(stmt):
                if not (isinstance(n, ast.Assign) and self._is_launch(n.value)):
                    continue
                for t in n.targets:
                    if not isinstance(t, ast.Name):
                        continue
                    self.total_bindings += 1
                    later = [b for b in self._binding_lines(fn.body, t.id) if b > n.lineno]
                    if not self._consulted(fn.body, t.id, n.lineno,
                                           later[0] if later else 10**9,
                                           plain_load=False):
                        self.unchecked.append(
                            (self.rel, fn.name, n.lineno,
                             f"`{t.id}` is bound from a launch and its outcome is "
                             f"never read before the name is bound again"))
        # SHAPE 2 — a nested helper hands back a return code.
        for inner in fn.body:
            if not isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            idx = self._code_index(inner)
            if idx is None:
                continue
            for stmt in fn.body:
                for n in _own_nodes(stmt):
                    if not (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                            and isinstance(n.value.func, ast.Name)
                            and n.value.func.id == inner.name):
                        continue
                    for t in n.targets:
                        if not (isinstance(t, ast.Tuple) and len(t.elts) > idx):
                            continue
                        slot = t.elts[idx]
                        if not isinstance(slot, ast.Name):
                            continue
                        self.total_bindings += 1
                        later = [b for b in self._binding_lines(fn.body, slot.id)
                                 if b > n.lineno]
                        if not self._consulted(fn.body, slot.id, n.lineno,
                                               later[0] if later else 10**9,
                                               plain_load=True):
                            self.unchecked.append(
                                (self.rel, fn.name, n.lineno,
                                 f"`{slot.id}` receives `{inner.name}`'s return code "
                                 f"and THIS binding is never read"))


def _scan_tree() -> tuple[list[tuple[str, str, int, str]], int]:
    unchecked: list[tuple[str, str, int, str]] = []
    total = 0
    for root in _ROOTS:
        for path in sorted(root.rglob("*.py")):
            v = _Bindings(str(path.relative_to(_TREE)))
            v.visit(ast.parse(path.read_text(encoding="utf-8")))
            unchecked.extend(v.unchecked)
            total += v.total_bindings
    return unchecked, total


def test_no_bounded_reply_is_read_without_its_outcome() -> None:
    """THE RULE. A reply's payload may not be used unless its outcome was read."""
    unchecked, _ = _scan_tree()
    assert not unchecked, (
        "a launch reply is read without consulting whether the launch ANSWERED "
        "— an empty stdout from a timeout is indistinguishable from a "
        "legitimately empty answer:\n"
        + "\n".join(f"  {rel}:{ln} in `{fn}` — {why}" for rel, fn, ln, why in unchecked)
        + "\n\nEither read `.returncode` / `is_timed_out(...)` for that binding, "
          "or add the function to `_OUTCOME_NOT_THE_DISCRIMINATOR` with the "
          "reason the code cannot be the discriminator there."
    )


def test_the_census_matches_the_tree() -> None:
    """THE POPULATION IS DERIVED, WHICH IS THE POINT OF THIS WHOLE FILE.

    The claim this guard replaces — "every converted caller is already correct" —
    was prose, and prose has no failure mode. This number goes red when a launch
    binding is added or removed, so the docstring's "seven sites" cannot rot: the
    next person to add one is told, here, that they are now in this population.
    """
    _, total = _scan_tree()
    assert total == 7, (
        f"the walk found {total} launch-reply binding(s), not the 7 recorded when "
        f"this was written. That is not a failure — it is the census telling you "
        f"the population moved. Confirm the new site reads its outcome, then "
        f"update this number and the docstring's count together."
    )


def test_every_exemption_still_names_a_live_function() -> None:
    """A STALE EXEMPTION IS A HOLE THAT LOOKS LIKE A DECISION.

    `wait_for_ci` renamed or deleted must not leave a silent carve-out behind
    that the next function to take the name inherits for free.
    """
    names = set()
    for root in _ROOTS:
        for path in sorted(root.rglob("*.py")):
            for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.add(n.name)
    assert _OUTCOME_NOT_THE_DISCRIMINATOR <= names, (
        f"an exemption names a function that no longer exists: "
        f"{sorted(_OUTCOME_NOT_THE_DISCRIMINATOR - names)}"
    )


# --- positive controls -------------------------------------------------------
# Testing Standard § *Structural tests need a positive control*. The predicate is
# exercised against literal snippets the tree does not contain, so a visitor that
# started answering unconditionally fails HERE rather than passing forever.

_DIRECT_DROPPED = """
def observe():
    r = run_bounded(["git", "status"])
    return r.stdout.strip()
"""

_DIRECT_READ = """
def observe():
    r = run_bounded(["git", "status"])
    if r.returncode != 0:
        return "unknown"
    return r.stdout.strip()
"""

_REBOUND_AND_READ_LATER = """
def observe():
    rc = run_bounded(["git", "log"])
    out = rc.stdout
    rc = run_bounded(["git", "status"])
    if rc.returncode != 0:
        return "unknown"
    return out
"""

_HELPER_DROPPED = """
def observe():
    def _git(*args):
        r = run_bounded(["git", *args])
        return r.returncode, r.stdout.strip()
    rc, head = _git("log")
    if rc != 0:
        return "unknown"
    rc, dirty = _git("status")
    return "none" if not dirty else "yes"
"""

_HELPER_READ = """
def observe():
    def _git(*args):
        r = run_bounded(["git", *args])
        return r.returncode, r.stdout.strip()
    rc, dirty = _git("status")
    if rc != 0:
        return "unknown"
    return "none" if not dirty else "yes"
"""


def _control(src: str) -> list[tuple[str, str, int, str]]:
    v = _Bindings("<control>")
    v.visit(ast.parse(src))
    return v.unchecked


@pytest.mark.parametrize("label,src,flagged", [
    ("direct binding, outcome dropped", _DIRECT_DROPPED, True),
    ("direct binding, outcome read", _DIRECT_READ, False),
    ("first binding dropped, name reused and read later", _REBOUND_AND_READ_LATER, True),
    ("helper code dropped at one of two call sites", _HELPER_DROPPED, True),
    ("helper code read", _HELPER_READ, False),
])
def test_the_predicate_discriminates(label: str, src: str, flagged: bool) -> None:
    """THE HALF THAT MATTERS MOST IS `_REBOUND_AND_READ_LATER`.

    That snippet is the originating defect in miniature, and it is the one a
    per-NAME check calls clean: `rc` is plainly used. Only asking "was THIS
    binding read before the name moved on" separates it from `_DIRECT_READ`.
    """
    found = _control(src)
    assert bool(found) is flagged, (
        f"{label}: expected {'a finding' if flagged else 'no finding'}, got {found}"
    )
