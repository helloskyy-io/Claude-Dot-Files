"""No subprocess this fleet launches may run without a wall-clock ceiling.

THE CLASS, NOT THE INSTANCE. The finding that produced this file was one
missing `timeout=` in `assistant_activities.gh_attempt._run` — the single launch
point for every retried `gh` in the fleet. Enumerating that one site and fixing
it would have been the wrong shape of answer: a sweep at the time found SEVEN
more `subprocess.run` calls in this tree with the same gap, four of them `git`
rather than `gh`, one of them in `scripts/preflight.py` which is the very first
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

  * **`os.system`, `os.popen`, `subprocess.call`, `check_output`, `Popen` via an
    alias, or anything invoked through a shell string.** It matches two spelled
    attribute accesses on the `subprocess` module. A launch spelled any other
    way is unbounded and invisible here. Nothing in the tree spells it another
    way today (verified by the census assertion below), which is the only
    reason the narrow match is adequate.
  * **Whether the timeout VALUE is sane.** `timeout=0.001` passes. The value is
    argued where each constant is defined; this asks only that a bound exists.
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
_STREAMING_POPEN = {
    ("modules/assistant/assistant_activities.py", "run_claude"),
    ("modules/assistant/build/build_activities.py", "run_child"),
}


class _Launches(ast.NodeVisitor):
    """Every `subprocess.run` / `subprocess.Popen` call, with where it is."""

    def __init__(self, rel: str) -> None:
        self.rel = rel
        self.func: list[str] = []
        self.runs: list[tuple[str, str, int, bool]] = []
        self.popens: list[tuple[str, str, int]] = []

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
                bounded = any(k.arg == "timeout" for k in node.keywords)
                self.runs.append((self.rel, where, node.lineno, bounded))
            elif f.attr == "Popen":
                self.popens.append((self.rel, where, node.lineno))
        self.generic_visit(node)


def _census() -> tuple[list, list]:
    runs, popens = [], []
    for root in _ROOTS:
        for path in sorted(root.rglob("*.py")):
            rel = str(path.relative_to(_TREE))
            v = _Launches(rel)
            v.visit(ast.parse(path.read_text(encoding="utf-8")))
            runs += v.runs
            popens += v.popens
    return runs, popens


def test_the_census_is_not_vacuous() -> None:
    """A GUARD THAT FINDS NOTHING PASSES EVERYTHING.

    If `_ROOTS` goes stale — the tree is reorganised, a package moves — every
    assertion below becomes trivially true and stays green forever. This is the
    floor that makes the other two mean something, and it is deliberately a
    floor rather than an equality: the point is that the walk still reaches
    production code, not that the count never changes.
    """
    runs, popens = _census()
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
    runs, _ = _census()
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
    _, popens = _census()
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
    sites across four modules acquire an uncaught exception at once.
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
