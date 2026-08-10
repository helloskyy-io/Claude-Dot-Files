"""The computed convergence predicate: its rules, its residual arm, its guards.

`phase5_convergence_stopping.md` step 4 requires EVERY documented
false-convergence mode to be named with the specific check that separates it
from real convergence, and each check to have a test PROVEN ABLE TO FAIL. This
module is that requirement.

THE SHAPE EVERY GUARD HERE TAKES. A test asserting "this input does not
converge" is satisfied by a predicate that never converges, so each guard is
paired with a control asserting the SAME input with the defect removed DOES
converge. The pairing is the evidence; the individual assertion is not.

AND THE MUTATIONS ARE DERIVED FROM THE CLAIM, NOT FROM WHAT IS EASY TO BREAK.
Each control below removes exactly the property its rule names — a dropped id
for `prior_findings_dropped`, a re-opened id for `oscillating_findings`, an
unroutable pass for `pass_not_evaluable` — rather than breaking something the
assertion would have caught by accident.

THE ESCALATED RULING IS TESTED AS A RULING, not as an implementation detail. It
is the one unforced choice this phase makes and it moves a headline number, so
both readings are exercised and the test states which one ships and why.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.assistant import convergence as cv
from modules.assistant import exit_record as er
from modules.assistant import routing
from modules.assistant.review_pr import review_pr_helper as helper

State = cv.ConvergenceState
Reason = cv.IndeterminateReason


def _pass(**dispositions: str) -> tuple[tuple[str, str], ...]:
    """One pass as `(id, disposition)` pairs. `_pass(a="hold", b="fixed")`."""
    return tuple(dispositions.items())


# --- the residual arm: every input reaches a NAMED state ---------------------

def test_a_pass_that_did_not_route_is_never_evidence() -> None:
    """A DEGRADED PASS THAT EMITS NOTHING — the first documented mode.

    An empty finding set from a truncated, turn-capped or crashed pass is
    byte-identical to an empty set from a clean pass. The only thing that tells
    them apart is evidence the pass completed, which the caller supplies from the
    typed exit record having routed. The fleet's measured turn-cap rate is 0.9%
    (4 of 443): rare, real, and silent.
    """
    assessment = cv.assess([_pass(a="hold"), _pass(a="fixed")], pass_evaluable=False)
    assert assessment.state is State.INDETERMINATE
    assert assessment.reason is Reason.PASS_NOT_EVALUABLE


def test_the_degraded_pass_control_the_SAME_input_converges_when_it_routed() -> None:
    """Negative control for the rule above — and the pairing IS the evidence.

    Without this, a predicate hard-wired to INDETERMINATE would satisfy the test
    above. The input is identical; only the caller's evidence changes.
    """
    assessment = cv.assess([_pass(a="hold"), _pass(a="fixed")], pass_evaluable=True)
    assert assessment.state is State.CONVERGED


def test_an_unreadable_history_is_its_OWN_reason_not_the_degraded_one() -> None:
    """The reason IS the payload — a rate limit is not a degraded review.

    The computed arm's instrument is the state GROUPED BY reason, so folding
    "the thread read was exhausted" into "the pass did not route" would report
    every `gh` blip as a broken reviewer. Same defect this component recorded at
    R2 (`route(None)` reporting `permission_denied`) and again at R1a.
    """
    assessment = cv.assess([], pass_evaluable=True)
    assert assessment.state is State.INDETERMINATE
    assert assessment.reason is Reason.HISTORY_UNREADABLE
    assert assessment.reason is not Reason.PASS_NOT_EVALUABLE


def test_pass_one_routes_to_the_residual_arm_and_NEVER_to_converged() -> None:
    """Requirement 5: absence of a comparable prior pass is never convergence.

    A first pass that closed everything it found has demonstrated nothing about
    a loop it has not yet looped — and this is the single case most likely to
    read as convergence to a naive implementation, because the open set is
    genuinely empty.
    """
    assessment = cv.assess([_pass(a="fixed", b="fixed")], pass_evaluable=True)
    assert assessment.state is State.INDETERMINATE
    assert assessment.reason is Reason.NO_PRIOR_PASS
    assert assessment.open_ids == ()


def test_pass_one_control_the_same_empty_set_DOES_converge_with_a_prior() -> None:
    """Negative control: the emptiness is not what withholds convergence."""
    assessment = cv.assess(
        [_pass(a="hold", b="hold"), _pass(a="fixed", b="fixed")], pass_evaluable=True,
    )
    assert assessment.state is State.CONVERGED


def test_every_indeterminate_state_carries_a_reason_and_no_other_state_does() -> None:
    """The residual arm is a NAMED STATE THAT IS RECORDED, enforced at construction.

    Documented on the enum and enforced nowhere is how
    `review_pr_workflow`'s reporting ended up one None away from an
    AttributeError inside the code that exists to explain machinery failures.
    """
    with pytest.raises(ValueError, match="must name its reason"):
        cv.ConvergenceAssessment(State.INDETERMINATE)
    with pytest.raises(ValueError, match="belongs only to the computed"):
        cv.ConvergenceAssessment(State.CONVERGED, Reason.NO_PRIOR_PASS)


# --- the stopping condition: EMPTY, not UNCHANGED ----------------------------

def test_a_stalled_pass_does_NOT_converge_and_is_named_as_stalled() -> None:
    """PR #58 pass 2 to 3, replayed: open held at 2, nothing added, nothing closed.

    THIS IS THE MEASURED REASON THE CONDITION IS EMPTINESS AND NOT STABILITY. A
    rule reading "the open set stopped changing" fires here and is WRONG; over
    the 12 archived pairs that rule fires 3 times and is wrong once, while
    "the open set is empty" fires twice and is wrong never.
    """
    assessment = cv.assess(
        [_pass(a="hold", b="hold"), _pass(a="hold", b="hold")], pass_evaluable=True,
    )
    assert assessment.state is State.NOT_CONVERGED
    assert assessment.stalled is True
    assert assessment.opened == () and assessment.closed == ()


def test_a_pass_that_is_MOVING_is_not_stalled_even_though_it_is_open() -> None:
    """Negative control for `stalled` — it must discriminate, not just be True.

    A flag that were always True on a NOT_CONVERGED assessment would satisfy the
    test above and tell an operator nothing.
    """
    assessment = cv.assess(
        [_pass(a="hold", b="hold"), _pass(a="fixed", b="hold", c="hold")],
        pass_evaluable=True,
    )
    assert assessment.state is State.NOT_CONVERGED
    assert assessment.stalled is False
    assert assessment.closed == ("a",) and assessment.opened == ("c",)


def test_the_all_ids_delta_is_TELEMETRY_and_never_the_stopping_condition() -> None:
    """A converging pass adds ids, and adding them must not withhold convergence.

    PR #42 pass 2 is the archive's clearest instance: THREE newly-added ids, all
    disposed within the same pass, on the one block that both converged and
    merged. A predicate reading "did this pass find anything new" would have
    refused to stop there — which is exactly what the all-ids delta measures,
    and why it is carried as telemetry instead.
    """
    assessment = cv.assess(
        [_pass(a="hold", b="hold"),
         _pass(a="fixed", b="fixed", c="rejected", d="deferred", e="noted")],
        pass_evaluable=True,
    )
    assert assessment.state is State.CONVERGED
    assert assessment.added_ids == ("c", "d", "e"), "the delta was not recorded"


# --- convergence by forgetting ----------------------------------------------

def test_dropping_a_prior_finding_makes_the_open_set_INCOMPARABLE() -> None:
    """A pass that does not restate what it inherited is not conforming.

    `disposition.md` INVARIANT 1 requires every prior finding to be carried
    forward until it reaches an explicit disposition. A pass that drops one has
    an open set that is not comparable to the prior one, so its emptiness proves
    nothing — and the cheapest way to fake convergence is to stop mentioning the
    findings. Measured at 0 of 12 archived pairs, which is what makes this a
    guard against a mode with no natural alarm rather than a live bug.
    """
    assessment = cv.assess(
        [_pass(a="hold", b="hold"), _pass(a="fixed")], pass_evaluable=True,
    )
    assert assessment.state is State.INDETERMINATE
    assert assessment.reason is Reason.PRIOR_FINDINGS_DROPPED


def test_forgetting_control_restating_the_dropped_id_converges() -> None:
    """Negative control: it is the DROP that withholds it, not the disposition.

    The mutation is derived from the rule's own claim — the same two findings,
    with the one the pass forgot restated as closed.
    """
    assessment = cv.assess(
        [_pass(a="hold", b="hold"), _pass(a="fixed", b="fixed")], pass_evaluable=True,
    )
    assert assessment.state is State.CONVERGED


def test_a_finding_forgotten_TWO_passes_ago_is_still_forgotten() -> None:
    """The drop check reads EVERY prior pass, because a pairwise one expires.

    Found by review, not by the mutation loop, and it is the shape the loop was
    blind to: every mutation was a single edit judged over a TWO-pass history,
    and this defect only appears at three. Against `passes[-2]` alone the run
    below flags pass 2 correctly and then reports pass 3 **CONVERGED** with `b`
    never dispositioned — so the cheapest way to fake convergence, stop
    mentioning a finding and keep not mentioning it, costs the forger exactly
    one extra pass. It is the same reasoning `_ever_reopened` already applies:
    any window shorter than the history is a number nobody measured.
    """
    history = [_pass(a="hold", b="hold"), _pass(a="fixed"), _pass(a="fixed")]

    two = cv.assess(history[:2], pass_evaluable=True)
    assert two.reason is Reason.PRIOR_FINDINGS_DROPPED, "the pairwise case regressed"

    three = cv.assess(history, pass_evaluable=True)
    assert three.state is State.INDETERMINATE, (
        "a finding dropped two passes ago is still undispositioned, and the pass "
        "that inherits the drop inherits the incomparability with it"
    )
    assert three.reason is Reason.PRIOR_FINDINGS_DROPPED


def test_the_whole_history_check_does_not_flag_a_CONFORMING_three_pass_run() -> None:
    """Control for the rule above: widening the window must not widen the alarm.

    The same three-pass shape with nothing forgotten. Without this, a drop check
    that simply returned INDETERMINATE on every history longer than two passes
    would satisfy the test above and destroy the predicate.
    """
    assessment = cv.assess(
        [_pass(a="hold", b="hold"), _pass(a="fixed", b="hold"), _pass(a="fixed", b="fixed")],
        pass_evaluable=True,
    )
    assert assessment.state is State.CONVERGED


# --- oscillation: the window check ------------------------------------------

def test_a_finding_closed_and_REOPENED_withholds_convergence_later() -> None:
    """AN OSCILLATING FINDING SET — the second documented mode.

    Two passes alternating between two sets each look new to a PAIRWISE
    comparison and never converge; only a comparison over a longer window sees
    the cycle. Here the cycle has already run once and the current pass looks
    clean — a pairwise rule stops, and the whole history says at least one
    closure on this thread did not hold.
    """
    assessment = cv.assess(
        [_pass(a="hold", b="fixed"),
         _pass(a="hold", b="hold"),
         _pass(a="fixed", b="fixed")],
        pass_evaluable=True,
    )
    assert assessment.state is State.INDETERMINATE
    assert assessment.reason is Reason.OSCILLATING_FINDINGS


def test_oscillation_control_the_same_three_passes_without_the_reopen() -> None:
    """Negative control — and it isolates the reopen from the length.

    Three passes, the same ids, the same final state; only `b`'s middle
    disposition changes. Without this, a predicate that refused to converge on
    any history longer than two would satisfy the test above.
    """
    assessment = cv.assess(
        [_pass(a="hold", b="fixed"),
         _pass(a="hold", b="fixed"),
         _pass(a="fixed", b="fixed")],
        pass_evaluable=True,
    )
    assert assessment.state is State.CONVERGED


def test_a_pairwise_comparison_would_have_MISSED_the_reopen() -> None:
    """The window is load-bearing, asserted rather than argued.

    Handing the predicate only the last two passes of the oscillating history
    produces CONVERGED. That is the failure the window exists to prevent, and
    demonstrating it here is what proves the window is doing work.
    """
    full = [_pass(a="hold", b="fixed"),
            _pass(a="hold", b="hold"),
            _pass(a="fixed", b="fixed")]
    assert cv.assess(full, pass_evaluable=True).state is State.INDETERMINATE
    assert cv.assess(full[-2:], pass_evaluable=True).state is State.CONVERGED


def test_the_reopen_scan_reads_the_WHOLE_history_and_not_adjacent_pairs() -> None:
    """A gap in the middle is what makes the window load-bearing rather than tidy.

    An adjacent-pair scan finds every reopen a CONFORMING history contains, by
    discreteness: closed at pass j and open at pass i>j implies a closed→open
    step somewhere between them. The chain only breaks where an id is ABSENT
    from an intermediate pass — and C3 does not catch that at a later pass,
    because it compares the CURRENT pass against every prior one and `a` is back
    by then. So this is the shape the whole-history window exists for, and
    shrinking `_ever_reopened`'s inner loop to the adjacent pass survived every
    other test in this module.
    """
    history = [
        _pass(a="fixed", b="hold"),   # `a` closed
        _pass(b="hold"),              # `a` absent — the gap that breaks the chain
        _pass(a="hold", b="hold"),    # `a` open again: a reopen only the window sees
        _pass(a="fixed", b="fixed"),  # everything closed; C5 is reachable
    ]
    assessment = cv.assess(history, pass_evaluable=True)
    assert assessment.reason is Reason.OSCILLATING_FINDINGS, (
        "a closure that did not hold, hidden behind a pass that omitted the id, "
        "was read as a clean convergence"
    )


def test_the_reopen_control_the_same_gap_with_no_REOPEN_converges() -> None:
    """Negative control: the gap alone must not withhold convergence.

    Without this, a window that flagged any absent-then-present id would satisfy
    the test above and refuse to converge on every history with a gap.
    """
    history = [
        _pass(a="hold", b="hold"),
        _pass(b="hold"),
        _pass(a="hold", b="hold"),
        _pass(a="fixed", b="fixed"),
    ]
    assert cv.assess(history, pass_evaluable=True).state is State.CONVERGED


# --- the escalated ruling ----------------------------------------------------

def test_escalated_is_CLOSED_so_the_predicate_can_fire_on_a_pr_that_escalated() -> None:
    """THE PHASE'S ONE UNFORCED RULING, and the measurement behind it.

    Phase 1 E7 counted `escalated` as open and said the corpus could not
    constrain the choice. It now can: PR #67 carries two escalated findings
    unchanged from pass 1 through pass 4. An escalated finding has been moved to
    another authority, so this reviewer cannot close it on ANY future pass —
    counting it open makes the predicate structurally unable to fire on any PR
    that ever escalates, which is the never-fires mode E7's re-scoping existed
    to escape.
    """
    assessment = cv.assess(
        [_pass(a="hold", b="escalated"), _pass(a="fixed", b="escalated")],
        pass_evaluable=True,
    )
    assert assessment.state is State.CONVERGED
    assert assessment.escalated_open == ("b",), (
        "the cost of the ruling was not recorded — convergence with work "
        "outstanding elsewhere is only defensible if the ids are carried"
    )


def test_hold_is_the_only_disposition_that_keeps_the_loop_open() -> None:
    """The partition, asserted per member rather than as a set comparison.

    A set comparison passes if both sides are wrong in the same way; this asserts
    the BEHAVIOUR each membership produces.
    """
    for closed in sorted(cv.CLOSED_DISPOSITIONS):
        assert cv.open_ids([("x", closed)]) == frozenset(), closed
    for still_open in sorted(cv.OPEN_DISPOSITIONS):
        assert cv.open_ids([("x", still_open)]) == frozenset({"x"}), still_open


def test_an_UNKNOWN_disposition_counts_as_open() -> None:
    """Fail-safe, and the two errors are not equal.

    Treating an unrecognised value as closed can EMPTY the open set and report
    convergence never observed; treating it as open can only spend a pass the
    bound already limits. All 300 archived findings carry a known disposition,
    so this changes no current number — it bounds what a future re-run can
    silently conclude.
    """
    assessment = cv.assess(
        [_pass(a="hold"), _pass(a="mostly-fixed-honest")], pass_evaluable=True,
    )
    assert assessment.state is State.NOT_CONVERGED
    assert assessment.open_ids == ("a",)
    assert assessment.unknown_dispositions == ("mostly-fixed-honest",)


def test_the_partition_is_EXACTLY_the_schemas_disposition_vocabulary() -> None:
    """The completeness gate: a seventh disposition cannot ship unclassified.

    A HAND-KEPT LIST RETIRES ITSELF THE MOMENT IT PASSES. This enumerates the
    real population — `CHILD_SCHEMA`'s enum, which is what the child is actually
    permitted to emit — instead of restating today's six values, so the NEXT
    member added fails here rather than defaulting silently into whichever half
    the code happens to reach first.
    """
    schema = er.CHILD_SCHEMA["properties"]["findings"]["items"]
    vocabulary = set(schema["properties"]["disposition"]["enum"])
    partition = cv.CLOSED_DISPOSITIONS | cv.OPEN_DISPOSITIONS
    assert vocabulary, "the schema lost its disposition enum"
    assert partition == vocabulary, (
        f"the convergence partition and the schema's vocabulary have diverged — "
        f"unclassified: {sorted(vocabulary - partition)}, "
        f"classified but unemittable: {sorted(partition - vocabulary)}. Rule the "
        f"new member open or closed in convergence.py; do not let it default."
    )
    assert not (cv.CLOSED_DISPOSITIONS & cv.OPEN_DISPOSITIONS), (
        "a disposition is in both halves — the partition is not one"
    )


# --- the module is what it claims to be --------------------------------------

def test_the_predicate_is_dependency_free_so_the_replay_can_load_it_by_path() -> None:
    """The claim `convergence.py`'s docstring makes about itself, checked.

    The replay tool loads this module BY PATH to validate the SHIPPED predicate
    rather than a copy. That only works while the module imports no sibling; a
    single `from .. import` would make the tool import the whole workflow tree,
    and the failure would surface as an unrelated `temporalio` ImportError in a
    measurement helper.
    """
    ALLOWED = {"__future__", "collections.abc", "dataclasses", "enum"}
    tree = ast.parse(Path(cv.__file__).read_text())
    imported = {
        node.module if isinstance(node, ast.ImportFrom) else alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported, "the AST scan found no imports at all — it is not reading the module"
    assert imported <= ALLOWED, (
        f"convergence.py grew a dependency: {sorted(imported - ALLOWED)}. The "
        f"replay tool loads this module BY PATH; a sibling import makes that "
        f"drag in the whole workflow tree."
    )


def test_nothing_in_the_tree_routes_on_the_convergence_signal() -> None:
    """THE PHASE'S CENTRAL RESTRAINT, ASSERTED RATHER THAN PROMISED.

    `routing.MAX_LOOPS` is still the only stopping authority. The archive
    contains two confirming observations of the predicate firing, which
    falsifies "it never fires" and is nowhere near a rate — so gating on it now
    would be legislating from a measurement that does not support it, which the
    phase's own completion requirement forbids.

    The check is on the CLASS, not on today's call sites: every conditional in
    `modules/` whose test reads the convergence vocabulary is enumerated, and
    the enumeration must equal a list of functions that provably cannot route.
    A list of the FILES that are clean today would retire itself the moment it
    passed; a list of the reporting-only FUNCTIONS does not — it grows only by a
    deliberate edit, which is the human gate.

    IT IS AN AST WALK BECAUSE THE LINE SCAN IT REPLACES WAS A FORMATTING
    ASSERTION, and this PR's own code walked around it three ways. That scan
    took lines whose STRIPPED TEXT began `if `/`while `/`elif ` and mentioned
    `ConvergenceState`. It could not see:

      1. a condition wrapped across lines — the mention lands on a continuation
         line that starts with neither keyword. Ruff or black produces this
         shape from any long condition, so the most likely future violation was
         the one the guard was blind to;
      2. a conditional EXPRESSION (`x if state is … else y`), which begins with
         neither keyword on any line;
      3. a hoisted local (`fired = state is CONVERGED` … `if fired:`), which
         hides the mention behind a name forever.

    All three existed in `review_pr_workflow` while the scan reported zero
    branches, and the phase doc claimed the check covered *"any `if`/`while`/
    `elif` whose condition mentions"* them. The mutation that "turned it red"
    had been shaped to the check rather than to the property.

    WHAT IT COVERS: `if`/`elif`/`while`/`assert`, conditional expressions and
    comprehension filters, whose test subtree names the convergence module, its
    types, or a local bound within the same function from an expression that
    does. WHAT IT DOES NOT: a value carried across a function boundary as a
    plain `bool`. `_convergence_notes`' `agrees` parameter is exactly that, and
    it is named here rather than left for a reader to discover — inter-procedural
    taint is a bigger instrument than this guard is worth, and the boundary is
    only safe while the reporting-only list below stays short.
    """
    VOCABULARY = {"convergence", "ConvergenceState", "ConvergenceAssessment",
                  "IndeterminateReason", "assess"}
    # Functions whose conditionals read the signal to decide what to SAY or
    # RECORD. Neither can route: one returns a bool-or-None, the other returns
    # lines of text. `run_review` — the function that actually routes — is
    # deliberately absent, and that is the property this list protects.
    REPORTING_ONLY = {
        ("review_pr/review_pr_helper.py", "shadow_agreement"),
        ("review_pr/review_pr_workflow.py", "_convergence_notes"),
    }

    def _mentions(node: ast.AST, tainted: set[str]) -> bool:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and (sub.id in VOCABULARY
                                              or sub.id in tainted):
                return True
            if isinstance(sub, ast.Attribute) and sub.attr in VOCABULARY:
                return True
        return False

    modules = Path(er.__file__).resolve().parent
    found: set[tuple[str, str]] = set()
    sites: list[str] = []
    for path in sorted(modules.rglob("*.py")):
        if path.name == "convergence.py" or "tests" in path.parts:
            continue
        rel = str(path.relative_to(modules))
        tree = ast.parse(path.read_text())
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            tainted: set[str] = {
                a.arg for a in fn.args.args + fn.args.kwonlyargs
                if a.annotation is not None and _mentions(a.annotation, set())
            }
            # Two sweeps: an assignment can taint a name used by a conditional
            # written above it in source order (a loop body, a nested def).
            for _ in range(2):
                for node in ast.walk(fn):
                    if isinstance(node, (ast.Assign, ast.AnnAssign)) \
                            and node.value is not None \
                            and _mentions(node.value, tainted):
                        targets = (node.targets if isinstance(node, ast.Assign)
                                   else [node.target])
                        tainted |= {t.id for t in targets if isinstance(t, ast.Name)}
            for node in ast.walk(fn):
                tests = []
                if isinstance(node, (ast.If, ast.While, ast.IfExp)):
                    tests = [node.test]
                elif isinstance(node, ast.Assert):
                    tests = [node.test]
                elif isinstance(node, ast.comprehension):
                    tests = list(node.ifs)
                for test in tests:
                    if _mentions(test, tainted):
                        found.add((rel, fn.name))
                        sites.append(f"{rel}:{node.lineno} in {fn.name}()")

    assert found <= REPORTING_ONLY, (
        "something now BRANCHES on the computed convergence signal outside the "
        "reporting-only functions: "
        + "; ".join(sorted(s for s in sites
                           if (s.split(":")[0], s.split(" in ")[1][:-2])
                           not in REPORTING_ONLY))
        + ". Phase 5 records it and gates nothing; the loop-back bound is still "
          "the only stopping authority until the measurement supports replacing "
          "it. If this branch genuinely only decides what to REPORT, add its "
          "function to REPORTING_ONLY with the reason — that edit is the gate."
    )
    assert found == REPORTING_ONLY, (
        f"the reporting-only list names functions that no longer branch on the "
        f"signal: {sorted(REPORTING_ONLY - found)}. A stale allowlist is a "
        f"widened gate — shrink it to what is actually there."
    )
    assert routing.MAX_LOOPS == 1, (
        "the loop-back bound moved. It stays in force until the convergence "
        "measurement supports replacing it, which two observations do not."
    )


# --- the live path: recorded, shadowed, and routing nothing ------------------

def _log_events(tmp_path: Path) -> list[dict]:
    return [json.loads(line) for line in
            (tmp_path / "run.jsonl").read_text().splitlines() if line.strip()]


def _window(monkeypatch, blocks: list[str]) -> None:
    """Give the workflow a multi-pass thread: one `gh` read, count and window."""
    from modules.assistant.review_pr import review_pr_activities as act
    monkeypatch.setattr(act, "thread_snapshot", lambda *a, **k: (len(blocks), blocks))


def test_the_convergence_event_is_written_and_carries_its_evidence(
        monkeypatch, tmp_path) -> None:
    """Without a durable event the predicate has no denominator.

    Same gap `append_parent_route` closed for the computed abstention arm, and
    it is closed here at the same time the signal is first emitted rather than a
    phase later — a metric defined over a field nothing writes is a plan, not an
    instrument.
    """
    from test_exit_record import _FakeWorkflow, _record
    from modules.assistant.review_pr.review_pr_helper import ReviewInput

    # The id must match `_record()`'s default finding — the render↔record
    # invariant runs first and raises on any mismatch, which is the guarantee
    # `convergence_history` relies on rather than a coincidence to work around.
    block = ("pr_review:\n  converged: false\n  findings:\n"
             "    - id: a-stable-slug\n      disposition: fixed\n")
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n", block=block)
    wf = fake.install(monkeypatch, tmp_path)

    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    events = [e for e in _log_events(tmp_path) if e.get("type") == "convergence"]
    assert len(events) == 1, "the convergence observable was not persisted"
    event = events[0]
    assert event["run_id"] == fake.run_id, "the event cannot be joined to its run"
    # Pass 1 on this fake: one block on the thread, so no prior pass.
    assert event["state"] == "indeterminate"
    assert event["reason"] == "no_prior_pass"
    assert result.convergence.state is State.INDETERMINATE


def test_the_parent_route_event_is_UNCHANGED_by_the_addition(
        monkeypatch, tmp_path) -> None:
    """Phase 4 is gated on the `parent_route` run set — this addition must not touch it.

    Asserted as an exact key set rather than a spot check: a widened payload is
    the shape that would quietly change what Phase 4 counts, and `type` is
    written from the parameter so a caller cannot shadow it through the payload.
    """
    from test_exit_record import _FakeWorkflow, _record
    from modules.assistant.review_pr.review_pr_helper import ReviewInput

    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    routes = [e for e in _log_events(tmp_path) if e.get("type") == "parent_route"]
    assert len(routes) == 1
    assert set(routes[0]) == {
        "type", "run_id", "pr", "routed_outcome", "undetermined_reason",
        "hold_kind", "shadow_verdict", "shadow_parseable", "channels_agree",
    }, "the parent stratum's payload changed while Phase 4 is gated on it"


def test_an_undetermined_route_still_produces_an_assessment(
        monkeypatch, tmp_path) -> None:
    """Totality reaches the live path, not just the pure function.

    A pass whose typed record did not route produces no thread read at all, so
    the easy implementation is to skip the predicate entirely and leave the run
    with no convergence event. That is a silent hole in the denominator.
    """
    from test_exit_record import _FakeWorkflow
    from modules.assistant.review_pr.review_pr_helper import ReviewInput

    fake = _FakeWorkflow(None, "VERDICT: HOLD - needs-assistance\n", block=None)
    wf = fake.install(monkeypatch, tmp_path)
    wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    events = [e for e in _log_events(tmp_path) if e.get("type") == "convergence"]
    assert len(events) == 1
    assert events[0]["state"] == "indeterminate"
    assert events[0]["reason"] == "pass_not_evaluable"


def test_an_exhausted_thread_read_reports_history_unreadable_not_a_bad_pass(
        monkeypatch, tmp_path) -> None:
    """The reason is the payload, on the live path this time.

    A `gh` rate limit must not be counted as a degraded review. The pass routed
    fine; the reader did not run.
    """
    from test_exit_record import _FakeWorkflow, _record, _no_sleep
    from modules.assistant.review_pr import review_pr_activities as act
    from modules.assistant.review_pr.review_pr_helper import ReviewInput

    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    _no_sleep(monkeypatch)

    def _boom(*a, **k):
        raise RuntimeError("gh pr view failed: API rate limit exceeded")

    monkeypatch.setattr(act, "thread_snapshot", _boom)
    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    events = [e for e in _log_events(tmp_path) if e.get("type") == "convergence"]
    assert events[0]["reason"] == "history_unreadable", (
        "an unreadable thread was reported as a degraded pass — the two have "
        "different remedies and the arm is grouped by this field"
    )
    assert result.verdict is routing.Verdict.MERGE, "the read failure changed a route"


def test_the_incumbent_flag_is_shadowed_and_a_disagreement_is_reported(
        monkeypatch, tmp_path) -> None:
    """E7's ruling: `converged` is a label the computation should reproduce.

    The block here asserts `converged: true` on a pass with an open finding, so
    the computation must differ — and must SAY so, in the event and in the
    operator note. A shadow that only ever agreed would record nothing.

    THE WORD IS "DIFFERS", NOT "DISAGREEMENT", and the test pins that rather
    than treating it as phrasing. The two rules answer different questions — the
    flag is a single-pass severity heuristic, the computation is set emptiness
    across passes — so a difference is a definitional one at least as often as
    it is a defect, and an operator told "DISAGREEMENT" goes looking for a bug
    that may not exist.
    """
    from test_exit_record import _FakeWorkflow, _record
    from modules.assistant.review_pr.review_pr_helper import ReviewInput

    prior = ("pr_review:\n  converged: false\n  findings:\n"
             "    - id: a\n      disposition: hold\n")
    now = ("pr_review:\n  converged: true\n  findings:\n"
           "    - id: a\n      disposition: hold\n")
    record = _record(run_id="@ISSUED@", outcome="hold", hold_kind="redispatch",
                     findings=[{"id": "a", "disposition": "hold"}])
    fake = _FakeWorkflow(record, "VERDICT: HOLD - redispatch\n", block=now,
                         prior_blocks=1)
    wf = fake.install(monkeypatch, tmp_path)
    # The window: the prior pass's block plus this pass's, in comment order.
    _window(monkeypatch, [prior, now])

    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    event = [e for e in _log_events(tmp_path) if e.get("type") == "convergence"][0]
    assert event["asserted_converged"] is True
    assert event["state"] == "not_converged"
    assert event["agrees"] is False
    differs = [n for n in result.notes if "DIFFERS from the incumbent flag" in n]
    assert differs, f"the shadow difference was not surfaced: {result.notes}"
    assert "answer different questions" in differs[0], (
        "the note names a difference without saying the two rules ask different "
        "things, which is what sends an operator hunting a defect"
    )


def test_the_operator_note_says_the_signal_routes_nothing(
        monkeypatch, tmp_path) -> None:
    """An operator seeing `converged` will assume something acted on it.

    Nothing does. The note has to say so in its own words rather than leaving
    the reader to infer it from the absence of an effect — this phase's whole
    posture is that the signal is measured before it is trusted.
    """
    from test_exit_record import _FakeWorkflow, _record
    from modules.assistant.review_pr.review_pr_helper import ReviewInput

    prior = ("pr_review:\n  converged: false\n  findings:\n"
             "    - id: a-stable-slug\n      disposition: hold\n")
    now = ("pr_review:\n  converged: true\n  findings:\n"
           "    - id: a-stable-slug\n      disposition: fixed\n")
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                         block=now, prior_blocks=1)
    wf = fake.install(monkeypatch, tmp_path)
    _window(monkeypatch, [prior, now])

    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    notes = [n for n in result.notes if n.startswith("Computed convergence")]
    assert len(notes) == 1, f"the signal was not surfaced: {result.notes}"
    assert "converged" in notes[0]
    assert "ROUTES NOTHING" in notes[0]
    assert f"MAX_LOOPS={routing.MAX_LOOPS}" in notes[0]


def test_an_assessment_with_NOTHING_TO_REPORT_emits_no_note_but_still_an_event(
        monkeypatch, tmp_path) -> None:
    """The denominator lives in the log; the note is for a human, so it is rationed.

    Pass 1 is the archive's most common block by a wide margin (12 of 25), and
    its note reads "indeterminate (no_prior_pass) over 1 pass(es); 0 open" —
    nothing an operator can act on, printed on every dispatch. Burying the four
    informative cases in that is how the first real one gets skimmed past, and
    this phase's headline is that the informative case has not happened yet.

    The control is that the EVENT is still written: rationing the note must not
    ration the measurement, or the rate this phase gates on stops accruing.
    """
    from test_exit_record import _FakeWorkflow, _record
    from modules.assistant.review_pr.review_pr_helper import ReviewInput

    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n")
    wf = fake.install(monkeypatch, tmp_path)
    result = wf.run_review(ReviewInput(pr_number="67"), tmp_path)

    assert not [n for n in result.notes if n.startswith("Computed convergence")], (
        "a no_prior_pass assessment with nothing open printed an operator note"
    )
    events = [e for e in _log_events(tmp_path) if e.get("type") == "convergence"]
    assert len(events) == 1 and events[0]["reason"] == "no_prior_pass", (
        "the note was rationed and the measurement went with it"
    )


def test_the_history_puts_this_passs_TYPED_findings_last(monkeypatch) -> None:
    """`convergence_history` is where the hybrid shows, so it is asserted here.

    The most recent term comes from the typed record and every earlier one from
    a durable block. If this pass's own block leaked into the history, the same
    pass would appear twice and every id would look restated — which reads as a
    perfectly conforming, perfectly stalled loop.
    """
    prior = ("pr_review:\n  findings:\n    - id: a\n      disposition: hold\n")
    mine = ("pr_review:\n  findings:\n    - id: a\n      disposition: fixed\n")
    record = er.ExitRecord(
        er.RoutedOutcome.MERGE, outcome=er.Outcome.MERGE,
        findings=({"id": "a", "disposition": "fixed"},),
    )
    history = helper.convergence_history([prior, mine], record)
    assert history == ((("a", "hold"),), (("a", "fixed"),)), (
        "the window's last entry is THIS pass's block and the typed record "
        "replaces it; keeping both puts one pass in the history twice"
    )
    assert cv.assess(history, pass_evaluable=True).state is State.CONVERGED


def test_the_history_keeps_MULTIPLE_prior_passes_in_ORDER(monkeypatch) -> None:
    """Order is the predicate's only source of consecutiveness, so it is asserted.

    Every other test here hands in at most ONE prior block, and against a single
    prior any ordering is the same ordering — reversing the priors survived the
    whole suite. `pass:` cannot supply the sequence (issue #68 measured it wrong
    on the most recently reviewed PR), so if this list is not oldest-first the
    predicate compares against the wrong neighbour and `_ever_reopened` reads a
    closure as a re-opening.
    """
    def block(disposition: str) -> str:
        return f"pr_review:\n  findings:\n    - id: a\n      disposition: {disposition}\n"

    # Deliberately NOT palindromic — the first fixture here was `hold, fixed,
    # hold`, which survives reversal unchanged, so it proved nothing. A control
    # whose input is symmetric under the defect is not a control.
    window = [block("hold"), block("hold"), block("fixed"), block("fixed")]
    record = er.ExitRecord(
        er.RoutedOutcome.MERGE, outcome=er.Outcome.MERGE,
        findings=({"id": "a", "disposition": "fixed"},),
    )
    history = helper.convergence_history(window, record)
    assert history == ((("a", "hold"),), (("a", "hold"),), (("a", "fixed"),),
                       (("a", "fixed"),)), "the prior passes are not oldest-first"
    assert cv.assess(history, pass_evaluable=True).state is State.CONVERGED, (
        "reversed, this same history reads as a finding closed and then re-opened "
        "and the predicate withholds convergence for the rest of the PR"
    )


# --- the window reader -------------------------------------------------------

def test_pr_review_blocks_returns_EVERY_block_in_comment_order(
        monkeypatch, tmp_path) -> None:
    """The window the oscillation check reads, asserted as a sequence.

    A reader that returned a set, or the last two, or deduplicated, would leave
    every ordered test above passing on synthetic input while the live predicate
    saw a different history. Order is the only thing that makes "consecutive"
    meaningful here — `pass:` cannot supply it (issue #68) — so it is asserted
    positionally rather than by membership.
    """
    from test_exit_record import _with_comments

    act = _with_comments(monkeypatch, [
        "```yaml\npr_review:\n  findings:\n    - id: one\n```",
        "Quoting the prior block:\n```yaml\npr_review:\n  findings:\n    - id: one\n```\n"
        "and mine:\n```yaml\npr_review:\n  findings:\n    - id: two\n```",
    ])
    count, blocks = act.thread_snapshot("66", tmp_path)
    assert [sorted(helper.finding_ids_in_block(b)) for b in blocks] == \
        [["one"], ["two"]], (
            "the window is not one entry per PASS in comment order — a quoting "
            "comment carries two blocks and only the last is that pass's; "
            "counting the quote injects a phantom pass that duplicates an "
            "earlier one"
        )
    assert count == len(blocks) == 2, (
        "the count and the window disagree about what a pass is, which is the "
        "skew deriving both from one reply exists to make impossible"
    )


def test_latest_pr_review_block_is_the_LAST_of_the_window_not_a_second_read(
        monkeypatch, tmp_path) -> None:
    """One extraction, two consumers — asserted so a tidying edit cannot re-split it.

    The address was typed twice for one commit when the window reader was added.
    `exit-protocol.md` §6 covers the record's ADDRESS as well as its schema, and
    the measured instance of that defect (issue #68) is this exact marker, so
    the delegation is a property rather than an implementation choice.
    """
    from test_exit_record import _with_comments

    act = _with_comments(monkeypatch, [
        "```yaml\npr_review:\n  findings:\n    - id: one\n```",
        "```yaml\npr_review:\n  findings:\n    - id: two\n```",
    ])
    assert act.latest_pr_review_block("66", tmp_path) == \
        act.pr_review_blocks("66", tmp_path)[-1]


def test_an_absent_converged_key_reads_as_NONE_and_not_as_false() -> None:
    """`None` is a third value on the live path too, not only in the replay tool.

    Absence dates a block to before the flag shipped. Folding it into `false`
    would make the shadow score every pre-flag block as a DISAGREEMENT with
    whatever the computation said — an agreement rate that is wrong in the
    direction of alarm, on a signal whose whole purpose is to be trusted or not.
    The archive still contains such blocks, so this is a live input shape.
    """
    assert helper.asserted_converged_in_block("pr_review:\n  pass: 1\n") is None
    assert helper.asserted_converged_in_block(
        "pr_review:\n  converged: false\n") is False
    assert helper.asserted_converged_in_block(
        "pr_review:\n  converged: true\n") is True


def test_the_event_payload_is_DERIVED_from_the_dataclass_not_retyped() -> None:
    """A field added for a later gating decision must reach the durable record.

    The payload was hand-copied field by field at the call site with no gate, so
    a new field on `ConvergenceAssessment` would have landed in the return value
    and in nothing durable — *a metric defined over a field nothing writes is a
    plan, not an instrument*, which is the sentence the dataclass exists under.
    Asserted as an exact key set in both directions: every field is present, and
    nothing appears that is not a field or the one named derived value.
    """
    from dataclasses import fields as dc_fields

    assessment = cv.assess(
        [_pass(a="hold"), _pass(a="escalated", b="weird")], pass_evaluable=True,
    )
    event = assessment.as_event()
    assert set(event) == {f.name for f in dc_fields(assessment)} | {"stalled"}, (
        "the event and the dataclass disagree about what an assessment carries"
    )
    # JSON-serialisable, because it goes to a JSONL log: enums as their values,
    # tuples as lists. A raw enum here serialises as a repr and breaks the join.
    assert event["state"] == "not_converged" and event["reason"] is None
    assert event["open_ids"] == ["b"] and isinstance(event["escalated_open"], list)
    json.dumps(event)


def test_an_INDETERMINATE_assessment_agrees_with_NOTHING() -> None:
    """Pass 1 is the archive's most common block, and it made no decision.

    The comparability rule had no test at all: dropping the indeterminate arm
    from it left every suite green while recording `agrees: true` for any pass-1
    block whose `converged:` happened to be `false` — which is most of them. A
    rate built on that counts a declined decision as a correct one.
    """
    pass_one = cv.assess([_pass(a="fixed")], pass_evaluable=True)
    assert pass_one.reason is Reason.NO_PRIOR_PASS
    assert helper.shadow_agreement(pass_one, False) is None, (
        "an assessment that declined to decide was scored as agreeing with the "
        "incumbent flag"
    )
    assert helper.shadow_agreement(pass_one, True) is None

    # Controls: it is the INDETERMINACY that makes it incomparable, not the
    # inputs — the same shapes with a decided state do compare.
    decided = cv.assess([_pass(a="hold"), _pass(a="fixed")], pass_evaluable=True)
    assert decided.state is State.CONVERGED
    assert helper.shadow_agreement(decided, True) is True
    assert helper.shadow_agreement(decided, False) is False
    # ... and an absent flag stays a third value, never folded into `false`.
    assert helper.shadow_agreement(decided, None) is None
