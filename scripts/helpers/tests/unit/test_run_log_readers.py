"""The three run-log readers: every figure carries a denominator, and it is right.

`phase6_read_what_it_writes.md` requirement 6 — inherited from
`scripts/helpers/measure/README.md`, which already binds these tools' siblings —
is that every count carries its denominator and every excluded artifact is named
as excluded. That is a property of the OUTPUT, so it is asserted against the
output rather than against the code that builds it.

The properties each reader has to hold, and each is asserted with an input that
breaks it:

  * `replay_run_resources.py` NAMES the records it excludes, derives their
    exclusion from a stated COMMIT CUTOVER rather than from the numbers looking
    wrong, and labels `high_events`/`oom_kills` NOT APPLICABLE per record instead
    of reporting a zero no threshold could have moved;
  * the overlap sweep bounds from BOTH sides — a non-overlapping pair must not
    be summed, and an overlapping one must be;
  * `replay_convergence_events.py` reports Phase 5's condition 1 as NOT TAKEN
    when the archive was not read, rather than as a zero;
  * every reader refuses to emit a model-authored finding slug.

Built on FIXTURES rather than the live archive, deliberately and unlike
`test_run_log.py`'s parser-parity check: these assert what the reader does with a
corpus of a known shape, and the live archive's shape changes with every dispatch.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_MEASURE = _REPO / "scripts" / "helpers" / "measure"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_{name}", _MEASURE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"_{name}"] = module
    spec.loader.exec_module(module)
    return module


def _log(dir_: Path, name: str, *events: dict) -> Path:
    path = dir_ / name
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    return path


def _resources(**over) -> dict:
    base = {
        "type": "run_resources", "measured": True, "unmeasured_reason": None,
        "peak_anon": 400 * 1024 ** 2, "peak_total": 500 * 1024 ** 2,
        "mean_total": 300 * 1024 ** 2, "pids_peak": 40,
        "high_events": 0, "oom_kills": 0, "tool_result_bytes": 1000,
        "subagents_spawned": 0, "samples": 100, "limits": {"slice": "s.slice"},
    }
    base.update(over)
    return base


def _run(dir_, capsys, module_name: str, *argv) -> str:
    module = _load(module_name)
    assert module.main([str(dir_), *argv]) == 0
    return capsys.readouterr().out


# --- replay_run_resources: exclusions are NAMED ------------------------------

def test_a_session_scope_record_is_EXCLUDED_BY_NAME_and_by_a_commit_cutover(
        tmp_path: Path, capsys) -> None:
    """Excluded because the CODE was known-wrong, never because the number looks it.

    Records written before `a623c25` sampled the CALLER'S SESSION SCOPE, so they
    are the editor session rather than fleet telemetry — large, plausible, and
    identical across different children. Excluding them for looking wrong would
    be the same reasoning that shipped them; excluding them for being written by
    known-wrong code is a fact about the tree.
    """
    _log(tmp_path, "review-pr-20260810-164130-aaa.jsonl",
         _resources(peak_total=21 * 1024 ** 3, pids_peak=1199))
    _log(tmp_path, "review-pr-20260810-225854-bbb.jsonl", _resources())
    out = _run(tmp_path, capsys, "replay_run_resources")
    assert "review-pr-20260810-164130-aaa.jsonl" in out, (
        "the excluded record is not NAMED in the output. A silently-dropped "
        "record is indistinguishable from one that was counted."
    )
    assert "SOUND records, used by figures 2-4: 1" in out
    assert "Carrying a run_resources   : 2" in out


def test_the_measured_false_rate_counts_EXCLUDED_records_too(
        tmp_path: Path, capsys) -> None:
    """Figure 1's denominator is EVERY record, and that is not the same as sound.

    An unmeasured run has to be countable whatever else was wrong with it — the
    incident that produced this instrument was an evidence failure, not an
    outage. A figure-1 denominator that quietly used the sound subset would hide
    exactly the runs most likely to be unmeasured.
    """
    _log(tmp_path, "review-pr-20260810-164130-aaa.jsonl",
         _resources(measured=False, unmeasured_reason="no session bus",
                    peak_anon=None))
    _log(tmp_path, "review-pr-20260810-225854-bbb.jsonl", _resources())
    out = _run(tmp_path, capsys, "replay_run_resources")
    assert "unmeasured: 1 of 2" in out
    assert "no session bus" in out


def test_high_and_oom_are_NOT_APPLICABLE_per_record_rather_than_zero(
        tmp_path: Path, capsys) -> None:
    """Applicability comes from that record's own `limits`, and the archive spans both.

    A record from 2026-08-10 carries MemoryHigh=4G and MemoryMax=8G; a later one
    carries only the slice. Printing "0 throttling events over N runs" across
    both states says NOTHING WAS THROTTLED when the truth for most of the corpus
    is that no threshold existed to throttle against.
    """
    _log(tmp_path, "review-pr-20260810-225854-bbb.jsonl", _resources())
    _log(tmp_path, "review-pr-20260810-230000-ccc.jsonl",
         _resources(limits={"slice": "s.slice", "MemoryHigh": "4G",
                            "MemoryMax": "8G"}, high_events=3))
    out = _run(tmp_path, capsys, "replay_run_resources")
    # ASSERTED ON THE COUNT, NOT ON THE LABEL. The first version of this test
    # read `"high_events NOT APPLICABLE" in out and "1 of 2" in out` — and a
    # mutation hardcoding `high_applicable = True` left it GREEN, because the
    # label is a print-string literal that appears whatever the data says and
    # `"1 of 2"` was satisfied by the `oom_kills` line two rows down. It was a
    # check that could not fail, which is worse than no check.
    assert "high_events NOT APPLICABLE — no MemoryHigh in that record's " \
           "`limits`: 1 of 2" in out
    assert "oom_kills   NOT APPLICABLE — no MemoryMax in that record's " \
           "`limits`: 1 of 2" in out
    assert "high fired on 1" in out, (
        "a record where the threshold DID exist and DID fire must be counted; "
        "collapsing it into the not-applicable bin is the same defect inverted"
    )


def test_the_overlap_sweep_bounds_from_BOTH_SIDES(tmp_path: Path, capsys) -> None:
    """A one-sided assertion cannot see a plausible wrong number.

    This component's own motivating failure is a telemetry test that asserted
    only a floor, passed, and was measuring the caller's cgroup. So: two
    DISJOINT windows must produce no overlap, and two INTERSECTING ones must
    produce exactly one, summed.
    """
    disjoint = tmp_path / "disjoint"
    disjoint.mkdir()
    _log(disjoint, "a-20260811-100000-aaa.jsonl",
         _resources(started_at="2026-08-11T10:00:00+00:00",
                    ended_at="2026-08-11T10:10:00+00:00", peak_anon=1024 ** 3))
    _log(disjoint, "b-20260811-110000-bbb.jsonl",
         _resources(started_at="2026-08-11T11:00:00+00:00",
                    ended_at="2026-08-11T11:10:00+00:00", peak_anon=1024 ** 3))
    out = _run(disjoint, capsys, "replay_run_resources")
    assert "NO OVERLAPPING PAIR IN THE CORPUS" in out

    both = tmp_path / "both"
    both.mkdir()
    _log(both, "a-20260811-100000-aaa.jsonl",
         _resources(started_at="2026-08-11T10:00:00+00:00",
                    ended_at="2026-08-11T10:30:00+00:00", peak_anon=1024 ** 3))
    _log(both, "b-20260811-101000-bbb.jsonl",
         _resources(started_at="2026-08-11T10:10:00+00:00",
                    ended_at="2026-08-11T10:20:00+00:00", peak_anon=1024 ** 3))
    out = _run(both, capsys, "replay_run_resources")
    assert "overlapping intervals observed: 1" in out
    assert "2 concurrent, summed peak_anon 2.000G" in out
    assert "UPPER BOUND" in out, (
        "summing two peaks that need not have coincided is an upper bound and "
        "must be labelled as one, or a headroom decision reads it as measured"
    )


def test_figure_4_states_the_denominator_of_records_carrying_a_WINDOW(
        tmp_path: Path, capsys) -> None:
    """Zero before `b8d7aa7`, and a record with no window is not a run with no overlap."""
    _log(tmp_path, "a-20260810-225854-aaa.jsonl", _resources())            # no window
    _log(tmp_path, "b-20260811-100000-bbb.jsonl",
         _resources(started_at="2026-08-11T10:00:00+00:00",
                    ended_at="2026-08-11T10:30:00+00:00"))
    out = _run(tmp_path, capsys, "replay_run_resources")
    assert "1 of 2 sound records carry a window" in out


def test_an_AMBIGUOUS_model_key_is_excluded_from_the_per_workflow_figure(
        tmp_path: Path, capsys) -> None:
    """`research` maps to two workflows, so a record carrying only it cannot bin.

    Binning it under either name would attribute one workflow's footprint to
    another and nothing in the output would say so.
    """
    _log(tmp_path, "research-20260811-100000-aaa.jsonl",
         _resources(model_key="research"))
    _log(tmp_path, "research-20260811-110000-bbb.jsonl",
         _resources(model_key="research", workflow_key="research-write"))
    out = _run(tmp_path, capsys, "replay_run_resources")
    assert "Excluded as model_key-AMBIGUOUS: 1" in out
    assert "research-20260811-100000-aaa.jsonl" in out
    assert "research-write" in out


# --- replay_convergence_events ----------------------------------------------

def _convergence(**over) -> dict:
    base = {"type": "convergence", "run_id": "a" * 32, "pr": "99",
            "state": "not_converged", "reason": None, "passes": 2,
            "open_ids": ["a-model-authored-finding-slug"], "opened": [],
            "closed": [], "escalated_open": [], "unknown_dispositions": [],
            "added_ids": [], "stalled": False, "asserted_converged": False,
            "agrees": True}
    base.update(over)
    return base


def test_condition_1_reports_NOT_TAKEN_rather_than_a_zero(
        tmp_path: Path, capsys) -> None:
    """"We did not measure" and "we measured nothing" are different facts.

    Collapsing them is how a gap becomes invisible, which is the same reason
    figure 1 of the resources reader exists at all. Condition 1 is scored on the
    GitHub archive and needs `gh`; without `--archive` the section must say so.
    """
    _log(tmp_path, "review-pr-20260811-100000-aaa.jsonl", _convergence())
    out = _run(tmp_path, capsys, "replay_convergence_events")
    assert "Condition 1" in out and "NOT TAKEN" in out
    assert "archive NOT TAKEN" in out


def test_condition_2_says_HAS_FIRED_only_for_a_guard_with_field_evidence(
        tmp_path: Path, capsys) -> None:
    """Both directions in one fixture, because the claim is a contrast.

    A guard with mutation evidence and no field evidence is still a guard; what
    condition 2 asks for is that the difference be stated rather than smoothed
    over. So one guard must read HAS FIRED and the other NEVER, from the same
    corpus.
    """
    _log(tmp_path, "review-pr-20260811-100000-aaa.jsonl",
         _convergence(state="indeterminate", reason="oscillating_findings"))
    _log(tmp_path, "review-pr-20260811-110000-bbb.jsonl", _convergence())
    out = _run(tmp_path, capsys, "replay_convergence_events")
    assert "oscillating_findings" in out and "HAS FIRED on real data" in out
    assert "prior_findings_dropped" in out and "has NEVER fired on real data" in out


def test_the_reader_reports_the_two_rates_the_ARCHIVE_cannot_produce(
        tmp_path: Path, capsys) -> None:
    """C-059's whole trigger: the live path knows whether the pass ROUTED."""
    _log(tmp_path, "review-pr-20260811-100000-aaa.jsonl",
         _convergence(state="indeterminate", reason="pass_not_evaluable"))
    out = _run(tmp_path, capsys, "replay_convergence_events")
    assert "pass_not_evaluable : 1 of 1" in out
    assert "history_unreadable : 0 of 1" in out


def test_no_MODEL_AUTHORED_finding_slug_reaches_the_output(
        tmp_path: Path, capsys) -> None:
    """The publish classification, asserted on what is actually printed.

    The run log is CO-RESIDENT with the CLI transcript and this output goes into
    committed docs and PR comments. `open_ids` are slugs the model wrote.
    """
    _log(tmp_path, "review-pr-20260811-100000-aaa.jsonl", _convergence())
    out = _run(tmp_path, capsys, "replay_convergence_events")
    assert "a-model-authored-finding-slug" not in out
    assert "open" in out          # the LENGTH is reported


def test_the_reader_RAISES_if_a_slug_is_carried_forward(tmp_path: Path) -> None:
    """The control on the control: the guard must be reachable from the reader.

    A publish check that no reader calls is a check that cannot fail. This
    monkeypatch-free version widens the payload so a publishable-looking key
    carries a slug value, which is the shape a careless widening would take.
    """
    module = _load("replay_convergence_events")
    _log(tmp_path, "review-pr-20260811-100000-aaa.jsonl",
         _convergence(pr="a-model-authored-finding-slug"))
    with pytest.raises(ValueError, match="non-publishable payload field"):
        module.rows(tmp_path)


# --- replay_parent_route -----------------------------------------------------

def _route(**over) -> dict:
    base = {"type": "parent_route", "run_id": "b" * 32, "pr": "99",
            "routed_outcome": "hold", "undetermined_reason": None,
            "hold_kind": "redispatch", "shadow_verdict": "HOLD - redispatch",
            "shadow_parseable": True, "channels_agree": True}
    base.update(over)
    return base


def test_the_abstention_arm_is_GROUPED_BY_REASON_not_merely_counted(
        tmp_path: Path, capsys) -> None:
    """`exit-protocol.md` §4's R1a/R2 split: a `gh` rate limit is not a bad review."""
    _log(tmp_path, "review-pr-20260811-100000-aaa.jsonl",
         _route(routed_outcome="undetermined", undetermined_reason="permission_denied",
                channels_agree=False))
    _log(tmp_path, "review-pr-20260811-110000-bbb.jsonl", _route())
    out = _run(tmp_path, capsys, "replay_parent_route")
    assert "abstained     : 1 of 2" in out
    assert "permission_denied" in out


def test_a_disagreement_caused_by_the_PARENT_ABSTAINING_is_separated_out(
        tmp_path: Path, capsys) -> None:
    """A raw disagreement count reads as a channel defect and has never been one.

    Every disagreement in the archive so far is R1 — the parent applying a safety
    rule the model could not see — which is the machinery working. Reporting the
    bare count would argue for removing the prose shadow on a number that does
    not mean what it looks like.
    """
    _log(tmp_path, "review-pr-20260811-100000-aaa.jsonl",
         _route(routed_outcome="undetermined", undetermined_reason="permission_denied",
                channels_agree=False))
    out = _run(tmp_path, capsys, "replay_parent_route")
    assert "genuine channel disagreements: 0" in out


def test_the_agreement_figure_states_its_own_CONDITIONING(
        tmp_path: Path, capsys) -> None:
    """C-060, and no larger N removes it.

    Every row comes from a run that got past the completion gate, so
    `channels_agree` is conditioned on the prose channel having SUCCEEDED. An
    agreement rate printed without that is the survivorship bias it was built to
    measure.
    """
    _log(tmp_path, "review-pr-20260811-100000-aaa.jsonl", _route())
    out = _run(tmp_path, capsys, "replay_parent_route")
    assert "C-060" in out
    assert "CONDITIONAL, NOT AS A RATE" in out


# --- every reader states a denominator at all --------------------------------

@pytest.mark.parametrize("module_name, event", [
    ("replay_run_resources", _resources()),
    ("replay_convergence_events", _convergence()),
    ("replay_parent_route", _route()),
])
def test_every_reader_prints_its_corpus_denominator(
        tmp_path: Path, capsys, module_name: str, event: dict) -> None:
    """README's standing rule for this directory, asserted on all three at once."""
    _log(tmp_path, "review-pr-20260811-100000-aaa.jsonl", event)
    out = _run(tmp_path, capsys, module_name)
    assert "Logs in archive" in out
    assert "THE DENOMINATOR" in out
