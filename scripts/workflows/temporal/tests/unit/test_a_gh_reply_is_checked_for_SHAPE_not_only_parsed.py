"""A `gh` reply that PARSES is not a `gh` reply that ANSWERED.

THE CLASS, NOT THE INSTANCE. The finding that produced this file was
`plan_activities.existing_work`: it guarded `json.loads` against
`JSONDecodeError` and then did `len(issues)`, `for i in issues` and
`i["number"]`. A zero-exit body of `{"message": "Not Found"}` decodes without
complaint, `len()` succeeds, the loop iterates the dict's KEYS, and `i["number"]`
raises `TypeError` on a string index — a dead planning dispatch, four lines
below a comment promising that every way of not getting an issue list reaches
the same COULD-NOT-BE-READ note. There were three ways and the comment knew two.

A sweep for the class found a second live member the finding did not name:
`assistant_activities.gh_json`, whose entire stated purpose is that "a `gh`
FAILURE IS ONE EXCEPTION TYPE" and which returned whatever `json.loads` produced.
A caller then wrote `.get("comments", [])` on it, so a JSON array reached them as
`AttributeError` — a second exception family, emitted by the one function in the
tree that exists to prevent second exception families. Two other members
(`ci_verdict`, `wait_for_ci`) already had the check; the sibling that did not is
exactly the shape a per-instance fix leaves behind.

WHY THIS IS A GUARD AND NOT FOUR CORRECT LINES OF CODE. `gh --json` answers with
an object or an array on exit 0, so the wrong-shape case is rare and every author
who has hit it has hit it in production. The next person to parse a `gh` reply
will write the obvious two lines, exactly as the last four did, and the only
thing that makes them write the third is a test that fails.

WHAT THIS GUARD DOES NOT LOOK AT:

  * **Whether the shape check is the RIGHT one.** It requires that the decoded
    name is passed to `isinstance` somewhere in the same function. A site that
    checks `isinstance(x, object)` passes. The check is that the question was
    asked, not that it was answered well.
  * **`json.load`, `yaml.safe_load`, or a parse behind a helper.** It matches
    `json.loads` applied to something that is visibly a subprocess reply. A
    fourth spelling is invisible here.
  * **Replies that are never indexed.** A site that decodes and only ever passes
    the value onward is flagged anyway; that is the safe direction and it costs
    one `isinstance`.
  * **Anything `gh_json` hands back once the shape check passes.** `expect=dict`
    proves it is a mapping, not that it has the keys the caller wants. A `gh`
    reply missing a requested field is a different failure and nothing here
    sees it.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

_TREE = Path(__file__).resolve().parents[2]
_ROOTS = (_TREE / "modules", _TREE / "scripts")

sys.path.insert(0, str(_TREE))

from modules.assistant import assistant_activities as act  # noqa: E402


def _is_gh_call(node: ast.AST) -> bool:
    """A call to `gh(...)` under ANY of the names the fleet reaches it by.

    `assistant_activities` calls it `gh`; every other module imports the shared
    module and writes `shared.gh(...)` or `_shared.gh(...)`. Matching only the
    bare `ast.Name` made this guard one file wide — and the motivating defect
    was in `plan_activities`, one of the modules it could not see. It was caught
    only because it happened to use the `.stdout` spelling instead.
    """
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    return ((isinstance(f, ast.Name) and f.id == "gh")
            or (isinstance(f, ast.Attribute) and f.attr == "gh"))


def _is_reply(node: ast.AST) -> bool:
    """Is this expression visibly the output of a subprocess or of `gh`?

    Three spellings, all present in the tree: `<name>.stdout` (optionally
    `or ""`), an inline `gh(...)` / `shared.gh(...)` call, and — resolved in
    `_maybe`, which has the enclosing function — a name assigned from one of
    those a line earlier. Anything else — a file, a log line, a literal — is a
    different population with different failure modes and is left alone.
    """
    if isinstance(node, ast.BoolOp):
        return any(_is_reply(v) for v in node.values)
    if isinstance(node, ast.Attribute) and node.attr == "stdout":
        return True
    return _is_gh_call(node)


class _Parses(ast.NodeVisitor):
    def __init__(self, rel: str) -> None:
        self.rel = rel
        self.stack: list[ast.FunctionDef] = []
        # (file, enclosing FunctionDef NODE, line, bound name). The node and not
        # its name: `_run` and `_git` are closure names this tree reuses, and a
        # flat name -> node dict resolves both to whichever `ast.walk` saw last,
        # so an unguarded site could be checked against the wrong body.
        self.sites: list[tuple[str, ast.AST | None, int, str | None]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):  # noqa: N802
        self.stack.append(node)
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # noqa: N815

    def visit_Assign(self, node: ast.Assign):  # noqa: N802
        self._maybe(node.value, node.targets)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):  # noqa: N802
        # `return json.loads(raw)` has no name to check, which is precisely how
        # `gh_json` shipped without a shape check: there was nothing to point an
        # `isinstance` at. Recorded with a None name so it reads as a finding
        # rather than being skipped.
        self._maybe(node.value, [])
        self.generic_visit(node)

    def _maybe(self, value, targets) -> None:
        if not (isinstance(value, ast.Call)
                and isinstance(value.func, ast.Attribute)
                and value.func.attr == "loads"
                and isinstance(value.func.value, ast.Name)
                and value.func.value.id == "json"):
            return
        if not value.args:
            return
        arg = value.args[0]
        # `raw = gh(...)` one line up is the third spelling. Resolved by looking
        # for a same-function assignment of that name from a `gh` call.
        source_is_reply = _is_reply(arg)
        if not source_is_reply and isinstance(arg, ast.Name) and self.stack:
            for sub in ast.walk(self.stack[-1]):
                if (isinstance(sub, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == arg.id
                                for t in sub.targets)
                        and _is_reply(sub.value)):
                    source_is_reply = True
        if not source_is_reply:
            return
        name = next((t.id for t in targets if isinstance(t, ast.Name)), None)
        self.sites.append((self.rel, self.stack[-1] if self.stack else None,
                           value.lineno, name))


def _guarded(fn: ast.AST | None, name: str | None) -> bool:
    if name is None or fn is None:
        return False
    for sub in ast.walk(fn):
        if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                and sub.func.id == "isinstance" and sub.args
                and isinstance(sub.args[0], ast.Name) and sub.args[0].id == name):
            return True
    return False


def _census() -> list[tuple[str, str, int, bool]]:
    out = []
    for root in _ROOTS:
        for path in sorted(root.rglob("*.py")):
            rel = str(path.relative_to(_TREE))
            v = _Parses(rel)
            v.visit(ast.parse(path.read_text(encoding="utf-8")))
            for rel_, fn, line, name in v.sites:
                where = getattr(fn, "name", "<module>")
                out.append((rel_, where, line, _guarded(fn, name)))
    return out


def _gh_json_calls() -> list[tuple[str, int, bool]]:
    """Every production `gh_json(...)` call, and whether it says `expect=`."""
    out = []
    for root in _ROOTS:
        for path in sorted(root.rglob("*.py")):
            rel = str(path.relative_to(_TREE))
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                named = ((isinstance(f, ast.Name) and f.id == "gh_json")
                         or (isinstance(f, ast.Attribute) and f.attr == "gh_json"))
                if named:
                    out.append((rel, node.lineno,
                                any(k.arg == "expect" for k in node.keywords)))
    return out


def test_the_census_is_not_vacuous() -> None:
    """FOUR SITES WHEN THIS WAS WRITTEN, AND A FLOOR RATHER THAN AN EQUALITY.

    `existing_work`, `gh_json`, `ci_verdict`, `wait_for_ci`. If the walk stops
    finding them — the tree moves, a parse is renamed — every assertion below is
    trivially true. The floor is what stops this file from silently becoming
    decoration.
    """
    sites = _census()
    assert len(sites) >= 4, (
        f"the AST walk found {len(sites)} `gh`-reply parse(s); it found 4 when "
        f"this guard was written, so it is no longer reading the tree it audits")


def test_every_gh_reply_parse_checks_the_decoded_SHAPE() -> None:
    """THE RULE.

    A `except json.JSONDecodeError` proves the bytes were JSON. It says nothing
    about whether they were the JSON this caller is about to index, and the
    caller's very next line always assumes they were.
    """
    unchecked = [(rel, where, line) for rel, where, line, ok in _census() if not ok]
    assert unchecked == [], (
        "these decode a `gh` reply and never ask what SHAPE came back, so a "
        "well-formed body of the wrong type reaches an index or an attribute "
        "access and raises from somewhere that cannot explain it:\n"
        + "\n".join(f"  {rel}:{line} in {where}()" for rel, where, line in unchecked)
        + "\n\nAdd `isinstance(<decoded>, list)` (or `dict`) beside the decode "
          "guard, the way `ci_verdict` does, or call `gh_json(..., expect=…)`.")


# ── the behaviour the rule above is standing in for ────────────────────────

@pytest.mark.parametrize(
    ("body", "why"),
    [
        pytest.param('{"message": "Not Found"}', "an object where a list was meant",
                     id="object"),
        pytest.param('"a string"', "a scalar", id="scalar"),
        pytest.param("42", "a number", id="number"),
    ],
)
def test_gh_json_refuses_a_valid_JSON_reply_of_the_wrong_SHAPE(
    monkeypatch, tmp_path, body: str, why: str,
) -> None:
    """ONE EXCEPTION TYPE MEANS ONE, INCLUDING THIS CASE.

    `gh_json`'s docstring argues that a caller cannot be expected to know which
    exception families this function can emit. It then emitted `AttributeError`
    and `TypeError` from its callers' next line for anything that parsed to the
    wrong shape. The failure surfaces here now, as the `RuntimeError` every
    caller in the fleet already guards.
    """
    monkeypatch.setattr(
        act.subprocess, "run",
        lambda argv, **_k: subprocess.CompletedProcess(argv, 0, stdout=body, stderr=""))

    with pytest.raises(RuntimeError, match="wrong shape"):
        act.gh_json(["pr", "view", "1", "--json", "x"], tmp_path, expect=list)


def test_gh_json_still_returns_BOTH_legitimate_gh_shapes(monkeypatch, tmp_path) -> None:
    """THE NEGATIVE CONTROL. A guard that rejects everything also rejects a 503.

    `gh --json` answers with an object (`pr view`) or an array (`pr checks`), and
    the default must pass both — a shape check tightened past what `gh` actually
    sends would break every caller in the fleet on its first real reply.
    """
    for body, expected in (('{"a": 1}', {"a": 1}), ("[1, 2]", [1, 2])):
        monkeypatch.setattr(
            act.subprocess, "run",
            lambda argv, _b=body, **_k: subprocess.CompletedProcess(
                argv, 0, stdout=_b, stderr=""))
        assert act.gh_json(["pr", "view"], tmp_path) == expected


def test_a_narrowed_caller_gets_the_narrower_answer(monkeypatch, tmp_path) -> None:
    """`expect=dict` IS WHY THE DEFAULT BEING PERMISSIVE IS SAFE.

    `(dict, list)` catches what `gh` can never have sent. It does not catch a
    list arriving where a caller will write `.get()` — so the two callers that
    read by key say `expect=dict`, and this is the assertion that the parameter
    is load-bearing rather than decorative.
    """
    monkeypatch.setattr(
        act.subprocess, "run",
        lambda argv, **_k: subprocess.CompletedProcess(argv, 0, stdout="[]", stderr=""))

    assert act.gh_json(["pr", "view"], tmp_path) == []      # permitted by default
    with pytest.raises(RuntimeError, match="expected dict"):
        act.gh_json(["pr", "view"], tmp_path, expect=dict)


def test_every_gh_json_call_states_the_shape_it_expects() -> None:
    """THE PARAMETER EXISTING IS NOT THE PARAMETER BEING USED — AND THIS IS KEYED
    ON THE CLASS, NOT ON THE TWO CALLERS THAT EXIST.

    An earlier draft of this test read one hardcoded path and asserted
    `len(calls) == 2`. That is the instance-keyed shape this whole file argues
    against: a `gh_json` call added in `build_activities` or `plan_activities`
    that reads by key would have been invisible to it, which is precisely the
    defect the file's header describes a per-instance fix leaving behind.

    WHAT IS REQUIRED IS THAT THE QUESTION WAS ASKED, not which answer was given.
    `expect=dict` or `expect=list` are both fine; the default `(dict, list)`
    catches only what `gh` can never have sent, and a caller that knows which of
    the two it needs is the one who has to say so. Same philosophy as the
    `isinstance` rule above.
    """
    calls = _gh_json_calls()
    assert len(calls) >= 2, (
        f"found {len(calls)} `gh_json` call site(s) under {_ROOTS}; there were "
        f"2 when this was written, so the walk is no longer reading the tree")
    silent = [(rel, line) for rel, line, stated in calls if not stated]
    assert silent == [], (
        "these call `gh_json` without saying what shape they expect back, so a "
        "valid reply of the wrong type reaches an index or a `.get()` in the "
        "caller and raises from somewhere that cannot explain it:\n"
        + "\n".join(f"  {rel}:{line}" for rel, line in silent)
        + "\n\nAdd `expect=dict` or `expect=list` — whichever the next line "
          "actually assumes.")


# ── THE PREDICATES' OWN CONTROLS ───────────────────────────────────────────
#
# The two rule tests above ask the tree a question. Neither proves the QUESTION
# still discriminates: were `_is_reply` or `_guarded` to start answering
# `True`/`False` unconditionally after a refactor, both rules pass forever AND
# the vacuity floor still passes, because the walk is still finding sites. The
# Testing Standard's "structural tests need a positive control" is aimed at
# exactly this, and the control must be a snippet the guard has never seen.

_UNGUARDED = "def f(r):\n    x = json.loads(r.stdout)\n    return x[0]\n"
_GUARDED = ("def f(r):\n    x = json.loads(r.stdout)\n"
            "    if not isinstance(x, list):\n        return None\n    return x[0]\n")


@pytest.mark.parametrize(
    ("snippet", "expect_found", "expect_ok", "why"),
    [
        pytest.param(_UNGUARDED, True, False, "a bare decode of a reply", id="bare"),
        pytest.param(_GUARDED, True, True, "the same, with a shape check", id="guarded"),
        pytest.param("def f(sh, p):\n    x = json.loads(sh.gh(p))\n    return x[0]\n",
                     True, False, "the `shared.gh(...)` spelling every module but "
                     "one uses — the spelling this guard was once blind to",
                     id="attribute-gh"),
        pytest.param("def f(p):\n    raw = gh(p)\n    x = json.loads(raw)\n"
                     "    return x[0]\n",
                     True, False, "a name assigned from `gh` a line earlier",
                     id="indirect-gh"),
        pytest.param("def f(line):\n    e = json.loads(line)\n    return e['t']\n",
                     False, False, "a log line, which is a different population",
                     id="not-a-reply"),
    ],
)
def test_the_reply_and_guard_predicates_discriminate(
    snippet: str, expect_found: bool, expect_ok: bool, why: str,
) -> None:
    """WOULD THIS TEST FAIL IF THE PROPERTY WERE VIOLATED? Asked of the guard itself."""
    v = _Parses("<control>")
    v.visit(ast.parse(snippet))
    assert bool(v.sites) is expect_found, (
        f"`_is_reply` {'missed' if expect_found else 'wrongly claimed'} {why}")
    if expect_found:
        _rel, fn, _line, name = v.sites[0]
        assert _guarded(fn, name) is expect_ok, (
            f"`_guarded` read {why} as "
            f"{'checked' if not expect_ok else 'unchecked'}")


def test_the_expect_detector_discriminates() -> None:
    """AND THE `expect=` DETECTOR'S CONTROL. A detector that always says yes is
    a permanent pass wearing a rule's name."""
    import textwrap
    src = textwrap.dedent("""
        a = gh_json(x, y)
        b = shared.gh_json(x, y, expect=dict)
        c = _shared.gh_json(x, y)
    """)
    found = [(n.lineno, any(k.arg == "expect" for k in n.keywords))
             for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Call)
             and ((isinstance(n.func, ast.Name) and n.func.id == "gh_json")
                  or (isinstance(n.func, ast.Attribute) and n.func.attr == "gh_json"))]
    assert len(found) == 3, "the `gh_json` matcher missed a spelling"
    assert [ok for _l, ok in found] == [False, True, False]
