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

THE LAST SECTION IS KEYED ON A CLASS, NOT ON THE SITES THAT HAD IT. Four separate
defects shipped in `replay_run_resources.py`, all one shape — a record left out of
a figure's population without being named, or its absent value read as a zero —
and all four survived a draft, a review pass and a correction pass that had
written the correct diagnosis in a comment sitting BETWEEN two of them. Enumerating
the four would have caught none of the fifth, so the guards there assert two
properties over the whole output instead:

  * every figure's printed `accounting:` line closes — counted + excluded = total;
  * adding an UNMEASURED record to a corpus does not move any figure computed
    from measurements, and the record is named where it was excluded.

Built on FIXTURES rather than the live archive, deliberately and unlike
`test_run_log.py`'s parser-parity check: these assert what the reader does with a
corpus of a known shape, and the live archive's shape changes with every dispatch.
"""

from __future__ import annotations

import importlib.util
import json
import re
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
    assert "FLEET records (not a session-scope measurement), used by figures 2-4: 1" in out
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


def test_an_UNMEASURED_record_beside_a_real_peak_does_not_kill_the_report(
        tmp_path: Path, capsys) -> None:
    """The reader has to survive the corpus figure 1 exists to report on.

    `sound` is "not a session-scope record" and says nothing about whether the
    run was measured, so an unmeasured record sits in it carrying
    `peak_anon: None`. The outlier block read those as zero, found
    `max(others) == 0`, passed its own `> 4 * 0` test for any positive peak and
    divided by zero on the next line — killing `report()` mid-print and taking
    figure 4 and the applicability section with it. A tool that dies on an
    unmeasured run is a tool that dies on exactly the evidence it was built to
    keep countable.
    """
    _log(tmp_path, "build-draft-20260811-120000-aaa.jsonl",
         _resources(peak_anon=1024 ** 3))
    _log(tmp_path, "review-pr-20260811-130000-bbb.jsonl",
         _resources(measured=False, unmeasured_reason="no session bus",
                    peak_anon=None, peak_total=None, mean_total=None))
    out = _run(tmp_path, capsys, "replay_run_resources")
    assert "unmeasured: 1 of 2" in out
    # THE SECTIONS AFTER THE CRASH POINT, asserted by name — the failure was a
    # partial report, so "it did not raise" is not the property. Figure 4 and
    # the applicability section both come after figure 3's outlier block.
    assert "Figure 4 — the AGGREGATE" in out
    assert "high_events NOT APPLICABLE" in out


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


def test_a_SESSION_SCOPE_record_cannot_contribute_a_throttling_event(
        tmp_path: Path, capsys) -> None:
    """The cutover applies to the applicability section too, and it used not to.

    That section ran over EVERY record while figures 2-4 ran over the post-cutover
    population — so a pre-`a623c25` record, which measured the caller's EDITOR
    SESSION rather than any dispatched child, could contribute a `high_events`
    crossing to a figure about the fleet. The editor being throttled is not a
    fact about a run, and nothing in the section named the substitution.

    The fixture is the reachable shape: caps DID exist on 2026-08-10, so a
    pre-cutover record carrying `MemoryHigh` and a non-zero crossing is what the
    archive actually holds.
    """
    _log(tmp_path, "review-pr-20260810-164130-aaa.jsonl",
         _resources(limits={"slice": "s.slice", "MemoryHigh": "4G"}, high_events=7))
    _log(tmp_path, "review-pr-20260810-225854-bbb.jsonl", _resources())
    out = _run(tmp_path, capsys, "replay_run_resources")
    assert "high fired on 0" in out, (
        "the editor session's throttling was counted as a fleet run's"
    )
    assert "no MemoryHigh in that record's `limits`: 1 of 1" in out, (
        "the applicability denominator must be the post-cutover population, "
        "not every record in the archive"
    )
    assert "accounting: applicability — counted 1 + excluded 1 = 2" in out


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
    assert "NO OVERLAPPING PAIR AMONG THE 2 RECORDS THAT ENTERED THE SWEEP" in out
    # THE STRONGER CLAIM IS ONLY MADE WHEN IT IS EARNED. Nothing was excluded
    # here, so the corpus-level sentence is licensed; the paired assertion in
    # `test_the_no_overlap_claim_RETREATS_when_a_record_was_excluded` shows it
    # withdrawn on a corpus where one was.
    assert "Every windowed run in this corpus ran alone" in out

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


def test_a_window_the_sweep_CANNOT_PLACE_is_named_rather_than_dropped(
        tmp_path: Path, capsys) -> None:
    """A record missing from a sweep reads exactly like one that overlapped nothing.

    Window boundaries sort with the close before the open at an equal instant,
    deliberately, so two runs meeting exactly at a boundary do not read as
    concurrent. The cost is that a window ending at or before its own start has
    its close processed first, is never removed from the live set, and inflates
    every later sum for the rest of the sweep. It is excluded — and, because
    this directory's rule is that an exclusion is NAMED, counted and printed
    rather than skipped in silence.
    """
    _log(tmp_path, "a-20260811-100000-aaa.jsonl",
         _resources(started_at="2026-08-11T10:00:00+00:00",
                    ended_at="2026-08-11T10:00:00+00:00", peak_anon=1024 ** 3))
    _log(tmp_path, "b-20260811-101000-bbb.jsonl",
         _resources(started_at="2026-08-11T10:10:00+00:00",
                    ended_at="2026-08-11T10:20:00+00:00", peak_anon=1024 ** 3))
    out = _run(tmp_path, capsys, "replay_run_resources")
    assert "NAMED AS EXCLUDED FROM THE SWEEP" in out
    assert "1 of 2" in out
    assert "a-20260811-100000-aaa.jsonl" in out


def test_figure_4_states_the_denominator_of_records_carrying_a_WINDOW(
        tmp_path: Path, capsys) -> None:
    """Zero before `b8d7aa7`, and a record with no window is not a run with no overlap."""
    _log(tmp_path, "a-20260810-225854-aaa.jsonl", _resources())            # no window
    _log(tmp_path, "b-20260811-100000-bbb.jsonl",
         _resources(started_at="2026-08-11T10:00:00+00:00",
                    ended_at="2026-08-11T10:30:00+00:00"))
    out = _run(tmp_path, capsys, "replay_run_resources")
    assert "1 of 2 fleet records carry a window" in out


def test_an_AMBIGUOUS_model_key_is_excluded_from_the_per_workflow_figure(
        tmp_path: Path, capsys) -> None:
    """`research` maps to two workflows, so a record carrying only it cannot bin.

    Binning it under either name would attribute one workflow's footprint to
    another and nothing in the output would say so.

    AMBIGUOUS AND UNATTRIBUTABLE ARE SEPARATED, and the third record is why:
    a model key that no module declares is what a log from a RETIRED or RENAMED
    workflow looks like, since the model→workflow map is derived from the tree as
    it stands today. Both are excluded from the figure; only one of them is a
    collision, and an archive that outlives its workflows accumulates the other.
    """
    _log(tmp_path, "research-20260811-100000-aaa.jsonl",
         _resources(model_key="research"))
    _log(tmp_path, "research-20260811-110000-bbb.jsonl",
         _resources(model_key="research", workflow_key="research-write"))
    _log(tmp_path, "longretired-20260811-120000-ccc.jsonl",
         _resources(model_key="longretired"))
    out = _run(tmp_path, capsys, "replay_run_resources")
    assert "Excluded as model_key-AMBIGUOUS — several workflows claim it: 1" in out
    assert "no workflow module declares that model_key: 1" in out
    assert "research-20260811-100000-aaa.jsonl" in out
    assert "longretired-20260811-120000-ccc.jsonl" in out
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
    # THE LENGTH, ASSERTED AS THE VALUE IT MUST HAVE. This read `"open" in out`,
    # which is a substring of "no overlapping" and of the section headings, so
    # it would have stayed green with the length reporting removed entirely —
    # decorative where the point is that ONE open id was counted. The row is the
    # last line of the per-event table and its `open` column is `1`.
    assert out.strip().splitlines()[-1].split(" | ")[5] == "1"


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


def test_the_agreement_figure_states_ITS_OWN_LIMIT(
        tmp_path: Path, capsys) -> None:
    """The figure must always ship with the limit on reading it — whatever it is.

    THIS ASSERTED THE OLD LIMIT VERBATIM and had to change with the code, which
    is the honest cost of pinning prose. Until 2026-08-14 every row came from a
    run past the completion gate, so `channels_agree` was CONDITIONED on the
    prose channel having succeeded — the survivorship bias the reader exists to
    measure. `_append_shadow_pair` is now called on the failing path too, so the
    conditioning is gone and the figure is a rate.

    WHAT THIS TEST PINS IS THE INVARIANT, NOT THE WORDING: the reader names
    C-060 and states what a reader may conclude. An agreement figure printed
    with no statement of its own limit is the defect, in either direction.
    """
    _log(tmp_path, "review-pr-20260811-100000-aaa.jsonl", _route())
    out = _run(tmp_path, capsys, "replay_parent_route")
    assert "C-060" in out, "the figure must still name the candidate it came from"
    assert "DENOMINATOR'S OWN LIMIT" in out, (
        "the reader printed an agreement figure without the section stating how "
        "far it may be read — which is the bias it was built to expose"
    )
    assert "_append_shadow_pair" in out, (
        "the limit section no longer names the mechanism that removed the "
        "conditioning, so a reader cannot check the claim"
    )


# --- THE CLASS: a record left out of a figure without being named ------------
#
# `carrying no peak` is not an exotic corpus. `resource_telemetry.finish()`
# returns exactly this shape — a real window, `measured: false`, `peak_anon:
# None` — whenever the cgroup vanishes before the first sample, and returns a
# no-numbers record with a degenerate window whenever a headless context has no
# session bus to make a scope in. Both are documented expected states.

def _agent_turn() -> dict:
    """One `tool_use` block naming the sub-agent tool the CLI actually emits."""
    return {"type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Agent"}]}}


def _measured_corpus(dir_: Path) -> None:
    """Two MEASURED records: one that spawned a sub-agent, one that did not."""
    _log(dir_, "build-draft-20260811-120000-aaa.jsonl", _agent_turn(),
         _resources(workflow_key="build-draft", peak_anon=512 * 1024 ** 2,
                    started_at="2026-08-11T12:00:00+00:00",
                    ended_at="2026-08-11T12:30:00+00:00"))
    _log(dir_, "plan-sprint-20260811-140000-ccc.jsonl",
         _resources(workflow_key="plan-sprint", peak_anon=256 * 1024 ** 2,
                    started_at="2026-08-11T14:00:00+00:00",
                    ended_at="2026-08-11T14:30:00+00:00"))


def _unmeasured_record(dir_: Path) -> str:
    """One UNMEASURED record whose window OVERLAPS the measured sub-agent run.

    The overlap is the point. A record that overlapped nothing would be dropped
    from the sweep with no visible consequence, so the fixture would pass over
    the defect it exists to catch.
    """
    name = "review-pr-20260811-121500-bbb.jsonl"
    _log(dir_, name, _agent_turn(),
         _resources(workflow_key="review-pr", measured=False,
                    unmeasured_reason="no session bus", peak_anon=None,
                    peak_total=None, mean_total=None, pids_peak=None,
                    tool_result_bytes=None, subagents_spawned=None, samples=None,
                    started_at="2026-08-11T12:15:00+00:00",
                    ended_at="2026-08-11T12:45:00+00:00"))
    return name


_ACCOUNTING = re.compile(r"accounting: (.+?) — counted (\d+) \+ excluded (\d+) = (\d+)")


def test_every_figure_ACCOUNTS_for_every_record_in_its_base_population(
        tmp_path: Path, capsys) -> None:
    """counted + excluded = total, for every figure, parsed out of the output.

    THE PROPERTY IS THE IDENTITY, NOT THE FIGURES THAT HAVE IT TODAY. Each of the
    four shipped defects narrowed a population inside a figure while the printed
    denominator went on claiming the records it had dropped; each would break one
    of these sums. So would a fifth, in a figure nobody has written yet, which is
    why this parses every `accounting:` line rather than naming the four.

    Run over a corpus containing an unmeasured record, because on an all-measured
    corpus every narrowing is a no-op and all four sums close vacuously.
    """
    _measured_corpus(tmp_path)
    _unmeasured_record(tmp_path)
    out = _run(tmp_path, capsys, "replay_run_resources")
    lines = _ACCOUNTING.findall(out)
    assert len(lines) >= 4, (
        f"expected an `accounting:` line from every figure that narrows its "
        f"population; found {len(lines)}. A figure that stopped printing one is "
        f"a figure this check no longer covers, which is the silent-narrowing "
        f"failure one level up."
    )
    for label, counted, excluded, total in lines:
        assert int(counted) + int(excluded) == int(total), (
            f"{label}: {counted} counted + {excluded} excluded != {total} total. "
            f"A record is in the stated population and in neither arm, so the "
            f"figure's denominator claims a record the figure never used."
        )


def test_an_UNMEASURED_record_does_not_move_a_MEASURED_figure(
        tmp_path: Path, capsys) -> None:
    """The other half of the class, and the half `accounting:` cannot see.

    A silent narrowing breaks an accounting sum. A COERCION does not — the record
    stays in the population and contributes a zero, so every count still closes
    while the statistic itself is wrong. That was figure 3: `[r["peak_anon"] or 0
    …]` printed `median … WITH subagents: 0.250G (n=2)` where the only measured
    sub-agent run peaked at 0.500G, and both medians then read IDENTICALLY, which
    is exactly the "the two knobs do not separate" conclusion the figure exists
    to report.

    So: run the same reader over a measured corpus and over that corpus PLUS one
    unmeasured record, and require every line of the first output to survive into
    the second — unless it is a line whose job is to count the corpus. Adding a
    record that carries no numbers may change what the report SAYS ABOUT ITS
    CORPUS; it may not change what the report says about the runs that WERE
    measured.

    `_CENSUS_MARKERS` is an allowlist of lines permitted to move, and it FAILS
    CLOSED: a new census line that is not in it turns this red rather than
    silently widening what may drift. That is the intended cost.
    """
    measured_only = tmp_path / "measured"
    measured_only.mkdir()
    _measured_corpus(measured_only)
    before = _run(measured_only, capsys, "replay_run_resources")

    both = tmp_path / "both"
    both.mkdir()
    _measured_corpus(both)
    added = _unmeasured_record(both)
    after = _run(both, capsys, "replay_run_resources")

    after_lines = set(after.splitlines())
    moved = [line for line in before.splitlines()
             if line not in after_lines
             and not any(marker in line for marker in _CENSUS_MARKERS)]
    assert not moved, (
        "adding an UNMEASURED record changed a figure about the MEASURED runs:\n  "
        + "\n  ".join(moved)
        + "\nEither the figure coerced an absent value to a number, or a census "
          "line needs adding to _CENSUS_MARKERS with the reason it may move."
    )
    assert added in after, (
        "the unmeasured record is not NAMED anywhere in the output. A record "
        "that is silently absent from every figure reads exactly like one that "
        "was counted and contributed nothing."
    )


# Lines whose job IS to count the corpus, and which therefore change when the
# corpus does. Hand-kept and checked only in the fail-closed direction: a census
# line missing from this list makes the test above RED, never quietly green.
_CENSUS_MARKERS = (
    # The two corpora are two directories, so the environment line differs for a
    # reason that has nothing to do with any figure.
    "Log directory",
    "Logs in archive", "Carrying a run_resources", "FLEET records",
    "unmeasured:", "reasons   :", "Denominator:", "Excluded as",
    "accounting:", "runs that spawned", "NOT APPLICABLE",
    "of the records where", "NAMED AS EXCLUDED", "NO OVERLAPPING PAIR AMONG",
    "Excluded from the two medians", "Attributed by payload",
    "AS EMITTED reads 0 on", "UNDERCOUNTS the structural recount",
    # Figure 4's corpus-level claim, which is SUPPOSED to move: it retreats to
    # the population that entered the sweep as soon as anything is excluded.
    # `test_the_no_overlap_claim_RETREATS_when_a_record_was_excluded` asserts
    # that retreat directly, so allowing it here does not leave it unchecked.
    "Every windowed run in this corpus ran alone",
    "the corpus and not a bound", "fleet costs.",
)


def test_the_no_overlap_claim_RETREATS_when_a_record_was_excluded(
        tmp_path: Path, capsys) -> None:
    """Naming the exclusion is necessary and is not sufficient.

    A reader takes the SENTENCE, not the arithmetic four lines above it. The
    sweep printed "every windowed run in it ran alone" over a corpus in which a
    genuinely overlapping window had been dropped — so once an exclusion exists,
    the corpus-level claim has to withdraw to the population that entered.
    """
    _measured_corpus(tmp_path)
    _unmeasured_record(tmp_path)
    out = _run(tmp_path, capsys, "replay_run_resources")
    assert "THAT IS NOT A STATEMENT ABOUT THE CORPUS" in out
    assert "Every windowed run in this corpus ran alone" not in out, (
        "the corpus-level claim was made while a window was held back from the "
        "sweep — and that window overlapped one that was counted"
    )
    assert "no peak_anon to sum — unmeasured" in out, (
        "an excluded record must carry its REASON; 'excluded' without 'why' is "
        "the same collapse one level down"
    )


def test_figure_3s_medians_are_taken_over_records_that_CARRY_a_peak(
        tmp_path: Path, capsys) -> None:
    """The instance, asserted on the VALUE — the class checks are above.

    Asserted as an exact value rather than "not 0.250G": the defect produced a
    plausible number, and a test that only rules out one plausible number admits
    the next one.
    """
    _measured_corpus(tmp_path)
    _unmeasured_record(tmp_path)
    out = _run(tmp_path, capsys, "replay_run_resources")
    assert "median peak_anon WITH subagents   : 0.500G (n=1)" in out
    assert "median peak_anon WITHOUT subagents: 0.250G (n=1)" in out


def test_an_ABSENT_byte_total_renders_as_unknown_and_never_as_zero(
        tmp_path: Path, capsys) -> None:
    """`0.00Mi` and `?` are different facts, in the same row as a `?` peak.

    The per-run table rendered an absent `tool_result_bytes` as a measured zero
    beside a `peak_anon` column that correctly printed `?` — so one record read
    as "pulled no tool results into context" when the truth is that nothing about
    it was measured at all. Figure 1's collapse, one column over.
    """
    _measured_corpus(tmp_path)
    added = _unmeasured_record(tmp_path)
    out = _run(tmp_path, capsys, "replay_run_resources")
    row = next(line for line in out.splitlines() if line.startswith(f"   {added} "))
    assert row.split()[-2] == "?", f"absent byte total rendered as a number: {row!r}"
    assert row.split()[-1] == "?"


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
