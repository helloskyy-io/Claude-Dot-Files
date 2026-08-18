"""No subprocess this fleet launches may run without a wall-clock ceiling.

THE CLASS, NOT THE INSTANCE. The finding that produced this file was one
missing `timeout=` in `assistant_activities.gh_attempt._run` — the single launch
point for every retried `gh` in the fleet. Enumerating that one site and fixing
it would have been the wrong shape of answer: a sweep at the time found SEVEN
more `subprocess.run` calls in this tree with the same gap — six of them `git`
rather than `gh`, one of them in `scripts/preflight.py`, which is the very first
thing a dispatch executes. A guard listing the sites it knew about would have
been green on the eighth.

WHAT THE GAP ACTUALLY COSTS. Every other guard in this tree runs AFTER the call
comes back: `gh_attempt`'s classifier reads a returncode, `wait_for_ci`'s
deadline is consulted between iterations, `worktree_add`'s fatal-fetch check
reads stderr. A TCP connection that neither answers nor resets — the ordinary
shape of a degraded endpoint, and GitHub was degraded on 2026-08-17 — is
therefore invisible to all of them. The dispatch parks, with no ceiling and no
log line, and the retry that was added to survive an outage never runs.

TWO LAUNCH SHAPES, TWO RULES, because they are genuinely different:

  * `subprocess.run` BLOCKS on a call nobody is watching. It must carry a
    `timeout=`. Almost every site satisfies this by going through
    `assistant_activities.run_bounded`, which converts `TimeoutExpired` into an
    ordinary non-zero reply so no caller grows a second exception family; the
    two that pass `timeout=` themselves are lower layers that must not import
    the assistant tree, and each says so where it does it.

  * `subprocess.Popen` STREAMS. Both sites in this tree launch a child that is
    expected to run for an hour and whose liveness IS its output — the
    operator watches the stream. A fixed ceiling there would be a different and
    much larger decision (what is the longest legitimate build?), so they are
    named below rather than bounded, and a NEW streaming launch fails this test
    until somebody makes that decision on purpose.

WHAT THIS GUARD DOES NOT LOOK AT, stated because a check read as broader than
it is does more harm than a narrow one:

  * **`Popen` via an alias, or a launch assembled through a variable.** The
    matcher wants a spelled `subprocess.<attr>` access. The OTHER spellings a
    reader would worry about — `os.system`, `os.popen`, `subprocess.call`,
    `check_call`, `check_output`, and `from subprocess import run` — are not a
    gap, because `test_no_launch_arrives_by_another_spelling` refuses them
    outright rather than trusting that nobody will write one. That test is what
    makes this narrow match adequate; this bullet used to claim the census
    below verified it, and the census did no such thing.
  * **Whether the timeout VALUE is sane.** `timeout=0.001` passes. The value is
    argued where each constant is defined; this asks only that a bound exists.
    `timeout=None` does NOT pass — it is a keyword spelling of no bound at all,
    which is the one value that would re-open the hole this file was written
    for, and it is rejected explicitly.
  * **The `Popen` sites' actual behaviour.** They are exempted by NAME. If one
    stops streaming and starts blocking on `communicate()`, this test still
    passes and the exemption's reasoning has silently stopped being true.
  * **Anything outside `scripts/workflows/temporal/`.** `scripts/helpers/measure/`
    launches `gh` through raw `subprocess.run` in two operator-invoked
    measurement tools; a failure there is visible to the person who typed the
    command. Out of the population on purpose, not by oversight.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_TREE = Path(__file__).resolve().parents[2]

# The production tree. `tests/` is excluded because a test that hangs fails the
# suite loudly and in front of whoever ran it — the harm this guard exists to
# prevent is a DISPATCH that hangs, unattended, with nobody reading a terminal.
_ROOTS = (_TREE / "modules", _TREE / "scripts")

# (path relative to the temporal tree, enclosing function). Each entry is a
# STREAMING child launch: the parent blocks on `for line in proc.stdout`, the
# output reaches the operator's terminal live, and the child is a full workflow
# or model run that legitimately takes an hour. Bounding these means choosing a
# longest-legitimate-build, which is a decision nobody has made and which this
# guard must not make by accident.
#
# THE CONDITION THAT REMOVES THIS EXEMPTION, because an allowlist with no expiry
# is a permanent quiet carve-out. It is NOT "when a ceiling for a streaming
# child is decided" — that trigger was written first and CANNOT FIRE, because
# the fleet has already ruled the other way: for the STALLED leg (a streaming
# child emitting nothing) `docs/development/fleet-reliability/research/
# synthesis.md` §4 rules "record and alert; do NOT kill", pricing the false
# positive at "up to ~60 min of unrecoverable paid work". An exemption whose
# expiry depends on a decision already made in the opposite direction is
# permanent while looking temporary, which is the thing this comment exists to
# refuse.
#
# So it goes when `docs/development/sprint.md` § Temporal Integration's
# unchecked "A `claude_cli` activity domain — heartbeating for 10-60 minute
# runs" lands: heartbeating is the liveness answer that ruling implies, and that
# item already owns this trigger. Until then, what is true is worth stating —
# neither site watches for silence (`run_claude` blocks on
# `for line in proc.stdout` with nothing observing the gap between lines), so a
# wedged model child is as unbounded as a wedged `gh` was, one layer up and for
# longer.
_STREAMING_POPEN = {
    ("modules/assistant/assistant_activities.py", "run_claude"),
    ("modules/assistant/build/build_activities.py", "run_child"),
}


# Launch spellings that carry no `timeout=` at all (`os.system`, `os.popen`) or
# that would slip past an attribute matcher. None of them appears in the tree;
# the rule is that none of them may, rather than that none happens to.
_OTHER_LAUNCH_SPELLINGS = frozenset({"call", "check_call", "check_output", "getoutput",
                                     "getstatusoutput"})


def where_or_module(stack: list[str]) -> str:
    return stack[0] if stack else "<module>"


class _Launches(ast.NodeVisitor):
    """Every `subprocess.run` / `subprocess.Popen` call, with where it is."""

    def __init__(self, rel: str) -> None:
        self.rel = rel
        self.func: list[str] = []
        self.runs: list[tuple[str, str, int, bool]] = []
        self.popens: list[tuple[str, str, int]] = []
        self.other: list[tuple[str, str, int, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):  # noqa: N802
        self.func.append(node.name)
        self.generic_visit(node)
        self.func.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # noqa: N815

    def visit_Call(self, node: ast.Call):  # noqa: N802
        f = node.func
        if (isinstance(f, ast.Attribute)
                and isinstance(f.value, ast.Name) and f.value.id == "subprocess"):
            # The OUTERMOST enclosing function, not the innermost. `_run` and
            # `_git` are closures whose names say nothing to a reader of the
            # failure message; `gh_attempt` and `observe_outcome` do.
            where = self.func[0] if self.func else "<module>"
            if f.attr == "run":
                # `timeout=None` IS NOT A BOUND. It is the default spelled out,
                # and it is the one edit that re-opens this hole while looking
                # like a deliberate answer to this very test.
                bounded = any(
                    k.arg == "timeout"
                    and not (isinstance(k.value, ast.Constant) and k.value.value is None)
                    for k in node.keywords)
                self.runs.append((self.rel, where, node.lineno, bounded))
            elif f.attr == "Popen":
                self.popens.append((self.rel, where, node.lineno))
            elif f.attr in _OTHER_LAUNCH_SPELLINGS:
                self.other.append((self.rel, where, node.lineno, f"subprocess.{f.attr}"))
        elif (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                and f.value.id == "os" and f.attr in {"system", "popen"}):
            self.other.append((self.rel, where_or_module(self.func), node.lineno,
                               f"os.{f.attr}"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):  # noqa: N802
        # `from subprocess import run` defeats the attribute matcher entirely.
        if node.module == "subprocess":
            for alias in node.names:
                self.other.append((self.rel, "<import>", node.lineno,
                                   f"from subprocess import {alias.name}"))
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):  # noqa: N802
        # AND SO DOES `import subprocess as sp`, FOR THE IDENTICAL REASON. The
        # matcher above tests `f.value.id == "subprocess"`, so `sp.run(cmd)` is
        # invisible to it — exactly the hole `from subprocess import run` was
        # promoted from "unlooked-at" to "refused" to close, one import
        # statement away. The docstring claimed alias spellings were refused
        # outright while only one of the two was; the tree already demonstrates
        # the aliasing habit is live (`test_exit_record.py` imports `ast` as
        # `_ast`). A plain `import subprocess` is untouched — it is what the
        # bounded sites use.
        for alias in node.names:
            if alias.name == "subprocess" and alias.asname:
                self.other.append((self.rel, "<import>", node.lineno,
                                   f"import subprocess as {alias.asname}"))
        self.generic_visit(node)


def _census() -> tuple[list, list, list]:
    runs, popens, other = [], [], []
    for root in _ROOTS:
        for path in sorted(root.rglob("*.py")):
            rel = str(path.relative_to(_TREE))
            v = _Launches(rel)
            v.visit(ast.parse(path.read_text(encoding="utf-8")))
            runs += v.runs
            popens += v.popens
            other += v.other
    return runs, popens, other


def test_the_census_is_not_vacuous() -> None:
    """A GUARD THAT FINDS NOTHING PASSES EVERYTHING.

    If `_ROOTS` goes stale — the tree is reorganised, a package moves — every
    assertion below becomes trivially true and stays green forever. This is the
    floor that makes the other two mean something, and it is deliberately a
    floor rather than an equality: the point is that the walk still reaches
    production code, not that the count never changes.
    """
    runs, popens, _other = _census()
    assert len(runs) >= 3, (
        f"the AST walk found {len(runs)} `subprocess.run` call(s) under "
        f"{[str(r.relative_to(_TREE)) for r in _ROOTS]} — it is no longer "
        f"reading the production tree, and every check in this file is vacuous")
    assert len(popens) >= 2, (
        f"the walk found {len(popens)} `subprocess.Popen` call(s); it found the "
        f"streaming dispatches when this was written and now does not")


def test_every_blocking_launch_carries_a_timeout() -> None:
    """THE RULE. A `subprocess.run` with no `timeout=` can park a dispatch forever.

    The fix is almost always `assistant_activities.run_bounded`, which supplies
    the ceiling and returns a `TimedOutProcess` — a non-zero reply, so the
    `returncode != 0` branch the call site already has is already correct.
    Passing `timeout=` directly is right only for a module that must not import
    the assistant tree (`modules/journal/`, `scripts/preflight.py`), and both of
    those say so at the call.
    """
    runs, _p, _o = _census()
    unbounded = [(rel, where, line) for rel, where, line, ok in runs if not ok]
    assert unbounded == [], (
        "these launch a subprocess with no wall-clock ceiling, so a command "
        "that never returns parks the dispatch with no bound and no log line:\n"
        + "\n".join(f"  {rel}:{line} in {where}()" for rel, where, line in unbounded)
        + "\n\nRoute it through `assistant_activities.run_bounded`, or pass "
          "`timeout=` and say at the call why this layer cannot use it.")


def test_a_new_streaming_launch_must_be_decided_on_purpose() -> None:
    """`Popen` IS EXEMPT BY NAME, NOT BY SHAPE, so the exemption cannot spread.

    The two entries in `_STREAMING_POPEN` are long-running children whose
    liveness is their output. That reasoning does not transfer to a `Popen`
    somebody adds next year to launch a short command — and a rule of the form
    "`Popen` is fine" would have covered it silently. Adding an entry here is
    cheap and forces the question to be asked once.
    """
    _r, popens, _o = _census()
    found = {(rel, where) for rel, where, _ in popens}
    unexpected = sorted(found - _STREAMING_POPEN)
    assert unexpected == [], (
        "these launch a subprocess via `Popen` and are not one of the known "
        "streaming child dispatches:\n"
        + "\n".join(f"  {rel} in {where}()" for rel, where in unexpected)
        + "\n\nIf it streams a long-running child, add it to `_STREAMING_POPEN` "
          "with the reason. If it does not, it wants a ceiling.")
    assert not (_STREAMING_POPEN - found), (
        f"an exemption in `_STREAMING_POPEN` no longer matches any call site: "
        f"{sorted(_STREAMING_POPEN - found)}. A stale exemption is a hole "
        f"nobody can see.")


def test_no_launch_arrives_by_another_spelling() -> None:
    """THE RULE ABOVE IS ONLY AS WIDE AS THE SPELLINGS IT CAN SEE.

    `subprocess.check_output(cmd)` takes a `timeout=` and is invisible to the
    `run` matcher. `os.system` cannot take one at all. `from subprocess import
    run` defeats the attribute match entirely. Each is a way to add an unbounded
    launch and leave this file green — so rather than assert that nobody would,
    they are refused outright.

    NOT A STYLE RULE. `subprocess.run` and `Popen` cover every launch this tree
    needs, and the cost of the ban is that somebody occasionally writes one
    extra line. The cost of not having it is a guard whose own docstring claims
    a coverage it does not have, which is worse than no guard.
    """
    _r, _p, other = _census()
    assert other == [], (
        "these reach a subprocess by a spelling this guard's `timeout=` rule "
        "cannot inspect:\n"
        + "\n".join(f"  {rel}:{line} in {where} — {what}"
                    for rel, where, line, what in other)
        + "\n\nUse `assistant_activities.run_bounded`, or `subprocess.run` with "
          "an explicit `timeout=`.")


# ── THE PREDICATE'S OWN CONTROL ────────────────────────────────────────────
#
# Everything above asks the tree a question. Nothing above proves the QUESTION
# still discriminates: if `bounded` began returning True unconditionally — an
# AST shape change, a keyword folded into `**kwargs`, a refactor of the visitor
# — every rule test passes forever AND the vacuity floors still pass, because
# the walk is still finding call sites. The Testing Standard's
# "structural tests need a positive control" is aimed exactly at this, and the
# control has to be a snippet the guard has never seen rather than the tree.

@pytest.mark.parametrize(
    ("snippet", "expect_bounded", "why"),
    [
        pytest.param("subprocess.run(cmd, timeout=1)", True, "an explicit bound",
                     id="bounded"),
        pytest.param("subprocess.run(cmd)", False, "no bound at all", id="bare"),
        pytest.param("subprocess.run(cmd, capture_output=True)", False,
                     "other keywords are not a bound", id="other-kwargs"),
        pytest.param("subprocess.run(cmd, timeout=None)", False,
                     "the default, spelled out", id="timeout-None"),
        pytest.param("subprocess.run(cmd, timeout=SOME_CONSTANT)", True,
                     "a named bound is still a bound", id="named-constant"),
    ],
)
def test_the_bounded_predicate_discriminates(snippet: str, expect_bounded: bool,
                                             why: str) -> None:
    """WOULD THIS TEST FAIL IF THE PROPERTY WERE VIOLATED? Asked of the guard itself."""
    v = _Launches("<control>")
    v.visit(ast.parse(snippet))
    assert len(v.runs) == 1, f"the matcher did not see the launch in: {snippet}"
    assert v.runs[0][3] is expect_bounded, (
        f"`{snippet}` was read as {'bounded' if v.runs[0][3] else 'unbounded'}; "
        f"it is {'bounded' if expect_bounded else 'unbounded'} — {why}")


@pytest.mark.parametrize(
    ("snippet", "why"),
    [
        pytest.param("subprocess.check_output(cmd)", "check_output", id="check_output"),
        pytest.param("subprocess.call(cmd)", "call", id="call"),
        pytest.param("os.system(cmd)", "os.system", id="os-system"),
        pytest.param("from subprocess import run", "a direct import", id="import-from"),
        pytest.param("import subprocess as sp", "an aliased import", id="import-as"),
    ],
)
def test_the_other_spelling_detector_discriminates(snippet: str, why: str) -> None:
    """AND ITS CONTROL, for the same reason. A refuser that refuses nothing passes."""
    v = _Launches("<control>")
    v.visit(ast.parse(snippet))
    assert v.other, f"{why} was not detected as an alternative spelling: {snippet}"


def test_the_control_does_not_flag_ordinary_code() -> None:
    """THE NEGATIVE HALF. A detector that fires on everything also fires on nothing."""
    v = _Launches("<control>")
    v.visit(ast.parse("import subprocess\nx = json.loads(r.stdout)\nos.path.join(a, b)\n"))
    assert v.other == [] and v.runs == [] and v.popens == []


@pytest.mark.parametrize(
    ("cmd", "why"),
    [
        pytest.param(["gh", "pr", "view"], "a `gh` read", id="gh"),
        pytest.param(["git", "fetch"], "a `git` fetch", id="git"),
    ],
)
def test_run_bounded_turns_a_hang_into_an_ordinary_non_zero_reply(
    monkeypatch, cmd: list[str], why: str,
) -> None:
    """THE MECHANISM THE RULE ABOVE POINTS AT, PINNED SO THE POINTER STAYS TRUE.

    Every converted call site keeps its existing `returncode != 0` branch and
    grows no `except`. That only holds while `run_bounded` swallows
    `TimeoutExpired` and returns instead — the moment it re-raises, six call
    sites across three modules acquire an uncaught exception at once.
    """
    import subprocess
    import sys

    sys.path.insert(0, str(_TREE))
    from modules.assistant import assistant_activities as act

    def hang(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    monkeypatch.setattr(act.subprocess, "run", hang)

    r = act.run_bounded(cmd)   # must not raise

    assert isinstance(r, act.TimedOutProcess), f"{why} did not report a timeout"
    assert r.returncode != 0, (
        "a timeout returned zero — every converted call site reads this as "
        "success and carries on with an empty answer")
    assert "did not answer within" in r.stderr
    assert r.stdout == "", (
        "partial output leaked into the reply; a fragment of an answer is not "
        "an answer and a caller will try to parse it")
