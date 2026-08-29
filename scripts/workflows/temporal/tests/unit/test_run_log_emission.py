"""The EMISSION side of the run-log surface: the join key joins, and the bin exists.

`phase6_read_what_it_writes.md` requirement 1 says a surface whose stated join key
returns an empty join has not been stated, and step 2 makes two payload fixes the
condition of the readers being worth writing:

  * **`run_id` carries the SAME VALUE in all three member events.** It did not:
    `run_claude` stamped the resource report with `log_file.stem`
    (`{model_key}-{stamp}-{nonce}`) against `parent_route`'s and `convergence`'s
    bare `uuid4().hex`. The nonce is a SUFFIX of the stem, so the three members
    joined only by suffix-matching a filename — a LOCATION rather than an
    ADDRESS, in `memory-model.md` §6.1's terms — and a reader written against the
    field name alone got an empty join that read as a corpus with no overlaps.
  * **`workflow_key` is on the payload**, because `model_key` cannot name a
    workflow: `research-draft` and `research-verify` share the model key
    `research`.

The tests below assert both against the shipped appenders, with a control on the
defect's own shape so the join test cannot pass by accident.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import uuid
from pathlib import Path

import pytest

from modules.assistant import assistant_activities as act
from modules.assistant import resource_telemetry as rt

REPO_ROOT = Path(__file__).resolve().parents[5]
_RUN_LOG = REPO_ROOT / "scripts" / "helpers" / "measure" / "run_log.py"


def _run_log():
    spec = importlib.util.spec_from_file_location("_run_log_emission", _RUN_LOG)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_run_log_emission"] = module
    spec.loader.exec_module(module)
    return module


def _write_all_three(log_file: Path, *, invocation_id: str, resources_run_id: str) -> None:
    act.append_parent_route(log_file, {"run_id": invocation_id, "pr": "99",
                                       "routed_outcome": "hold"})
    act.append_convergence(log_file, {"run_id": invocation_id, "pr": "99",
                                      "state": "not_converged"})
    report = rt.ResourceReport(run_id=resources_run_id, model_key="review-pr",
                              workflow_key="review-pr", measured=True)
    act.append_run_resources(log_file, rt.report_dict(report))


def _joined(log_dir: Path) -> set[str]:
    """`run_id`s carried by ALL THREE member types in this directory."""
    rl = _run_log()
    sets = [
        {e.get("run_id") for _, e in rl.events(log_dir, t)}
        for t in sorted(rl.MEMBER_EVENT_TYPES)
    ]
    return set.intersection(*sets) - {None}


# --- the join key joins ------------------------------------------------------

def test_all_three_member_events_agree_on_run_id(tmp_path: Path) -> None:
    """The property requirement 1 needs before it can call this a surface."""
    invocation_id = uuid.uuid4().hex
    log_file = tmp_path / f"review-pr-20260811-120000-{invocation_id}.jsonl"
    _write_all_three(log_file, invocation_id=invocation_id, resources_run_id=invocation_id)
    assert _joined(tmp_path) == {invocation_id}


def test_the_STEM_shaped_run_id_is_the_DEFECT_and_produces_an_EMPTY_join(
        tmp_path: Path) -> None:
    """The control, on the defect's own shape rather than on a random value.

    A mutation that merely blanked the field would fail the test above too and
    would prove nothing about THIS bug. What shipped was a value that is a
    superstring of the right one — greppable, plausible, and joining nothing —
    so the control has to be that exact shape. It also demonstrates why a
    suffix-match "fix" is not one: the reader would have to know the filename
    convention to recover an identity the record claims to carry.
    """
    invocation_id = uuid.uuid4().hex
    log_file = tmp_path / f"review-pr-20260811-120000-{invocation_id}.jsonl"
    _write_all_three(log_file, invocation_id=invocation_id, resources_run_id=log_file.stem)
    assert _joined(tmp_path) == set(), (
        "the stem-shaped run_id joined anyway, so this control is not "
        "discriminating and the join test above proves nothing"
    )
    assert log_file.stem.endswith(invocation_id), (
        "the fixture no longer reproduces the defect: the stem must END with the "
        "nonce, which is what made the wrong value look right"
    )


def test_run_claude_stamps_the_report_with_THE_RUN_S_OWN_run_id() -> None:
    """The only check that can see the defect where it actually lived.

    Every other test here goes through the appenders directly, because exercising
    `run_claude` end to end means invoking the CLI. So the wrong value could be
    restored inside `run_claude` and the whole suite would stay green — which is
    how it shipped in the first place.

    ASSERTED ON THE CLAIM, NOT ON THE KNOWN-BAD STRING. A check for the literal
    `log_file.stem` retires itself the moment it passes: it can only ever catch
    the one wrong value already found, and `log_file.name` or a re-derived nonce
    would sail past it. What has to be true is that the identity handed to
    `resource_telemetry.finish` is THE SAME NAME the log path was built from, so
    this reads the keyword's AST node and requires a bare `run_id`.
    """
    tree = ast.parse(Path(act.__file__).read_text())
    function = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "run_claude"
    )
    calls = [
        node for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "finish"
    ]
    assert len(calls) == 1, (
        f"expected exactly one resource_telemetry.finish() call inside "
        f"run_claude, found {len(calls)} — this check no longer knows what it is "
        f"reading"
    )
    keywords = {k.arg: k.value for k in calls[0].keywords}
    for name in ("invocation_id", "workflow_key"):
        assert name in keywords, f"finish() is not given {name}"
        assert isinstance(keywords[name], ast.Name) and keywords[name].id == name, (
            f"finish(..., {name}=...) is given "
            f"{ast.dump(keywords[name])[:80]} rather than the bare `{name}` this "
            f"function received. The run log's join key must carry the SAME value "
            f"in all three member events; a derived value — a filename stem, a "
            f"re-generated nonce — joins nothing and looks correct."
        )


# --- the bin exists ----------------------------------------------------------

def test_the_resource_report_carries_a_workflow_key_distinct_from_model_key() -> None:
    """`research` is one model key over two workflows, so only this field bins.

    Asserted on the report rather than on a live dispatch: `finish()` is where
    identity is stamped, including on the unmeasured path, and an unmeasured run
    has to be countable AND attributable or the blind spot cannot be broken down
    by workflow.
    """
    report = rt.finish(None, limits={}, unmeasured_reason="no session bus",
                       invocation_id="abc", model_key="research",
                       workflow_key="research-verify")
    assert report.measured is False
    assert report.model_key == "research"
    assert report.workflow_key == "research-verify"
    assert "workflow_key" in rt.report_dict(report)


def test_run_claude_REFUSES_a_log_file_with_no_run_id(tmp_path: Path) -> None:
    """The half-supplied case is what wrote the wrong value, so it raises.

    A caller that allocated the log path already holds the nonce that named it —
    it had to, to build the name — so being unable to supply it means the path
    came from somewhere else, and stamping the report with a nonce `run_claude`
    invented would attribute one run's resources to another run's identity.
    """
    # `repo_root=tmp_path`, not the real root: this suite runs from a worktree
    # and `run_claude` refuses a worktree repo_root FIRST, so the real root would
    # make this test pass on the wrong exception.
    with pytest.raises(ValueError, match="no invocation_id"):
        act.run_claude(
            "prompt", model_key="review-pr", workflow_key="review-pr",
            completion_pattern="x", repo_root=tmp_path,
            log_file=tmp_path / "review-pr-20260811-120000-abc.jsonl",
        )


def test_run_claude_requires_a_workflow_key(tmp_path: Path) -> None:
    """No default, so a new call site cannot acquire the hole by forgetting.

    Same shape as `convergence.assess`'s `pass_evaluable`. A default of
    `model_key` would have been the silent-wrong-bin version of this bug.
    """
    with pytest.raises(TypeError, match="workflow_key"):
        act.run_claude("prompt", model_key="review-pr", completion_pattern="x",
                       repo_root=tmp_path)


# --- the appender's own reservation still holds ------------------------------

def test_a_payload_may_still_not_shadow_its_own_type(tmp_path: Path) -> None:
    """Re-asserted here because the surface's index is the `type` key.

    `run_log.events` filters on it, so a payload that could set it would make
    itself invisible to every reader this phase added — the denominator would
    disappear with no test going red anywhere else.
    """
    log_file = tmp_path / "review-pr-20260811-120000-abc.jsonl"
    with pytest.raises(ValueError, match="may not carry its own"):
        act.append_run_resources(log_file, {"type": "parent_route"})
