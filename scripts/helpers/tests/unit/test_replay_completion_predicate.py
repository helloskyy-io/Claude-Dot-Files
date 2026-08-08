"""Unit tests for the completion-predicate replay tool.

These guard the properties the E5 measurement's *validity* rests on, not merely
that the code runs. Two in particular would silently invalidate the reported
zero if they broke:

  * If `STRICT_VERDICT` were unanchored, it would match a verdict quoted inside
    prose and E5's "0 quoted-prior-pass matches" would be unfalsifiable.
  * If `LOOSE_VERDICT` were not actually looser than strict, the adjudication
    procedure would be comparing a set against itself and "strict == loose on
    50 of 50" would be a tautology rather than evidence.

Each assertion below is paired with an input that makes it FAIL if the property
is violated — a strict-matches case beside a strict-must-not-match case.

Flat comment-delimited functions, matching `test_check_settings.py` in this
directory; `class Test` grouping appears nowhere else in the repo.
"""

from __future__ import annotations

import json
from pathlib import Path

from measure.replay_completion_predicate import (
    ISSUE_ALTERNATIVE_WORKFLOWS,
    LOOSE_VERDICT,
    PATTERNLESS_WORKFLOWS,
    PR_OR_ISSUE_URL,
    PR_URL,
    STRICT_VERDICT,
    VERDICT_WORKFLOWS,
    last_whole_match,
    read_log,
    workflow_of,
)


def _write(tmp_path, events, name="x-20260808-010203.jsonl"):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return p


# --- STRICT_VERDICT: the anchoring E5's "0 quoted matches" depends on ---

def test_strict_matches_a_verdict_on_its_own_line():
    assert STRICT_VERDICT.search("some prose\nVERDICT: MERGE")


def test_strict_matches_each_of_the_three_routing_tokens():
    for token in (
        "VERDICT: MERGE",
        "VERDICT: HOLD - redispatch",
        "VERDICT: HOLD - needs-assistance",
    ):
        assert STRICT_VERDICT.search(token), token


def test_strict_does_not_match_a_verdict_quoted_inside_prose():
    # The anchoring is the whole defence against routing on a sentence a run
    # wrote about its own history (routing.py:39-41 states this rationale).
    assert not STRICT_VERDICT.search('the last pass returned "VERDICT: MERGE" so')


def test_strict_does_not_match_an_indented_verdict():
    # Not a bug — a documented consequence. A formatter that indents the
    # child's output would make the parent's grep blind, and this test is
    # what makes that fact visible rather than surprising.
    assert not STRICT_VERDICT.search("prose\n    VERDICT: MERGE")


def test_strict_does_not_match_an_unknown_hold_kind():
    assert not STRICT_VERDICT.search("VERDICT: HOLD - escalate")


def test_strict_matches_are_ordered_so_last_wins():
    out = "VERDICT: MERGE\nlater\nVERDICT: HOLD - redispatch"
    assert [m.group(0) for m in STRICT_VERDICT.finditer(out)] == [
        "VERDICT: MERGE",
        "VERDICT: HOLD - redispatch",
    ]


def test_last_whole_match_returns_one_shape_for_both_pattern_families():
    # STRICT_VERDICT carries capturing groups (verbatim from the shipped ERE at
    # review-pr.sh:186), so `findall()` yields TUPLES while the URL patterns
    # yield strings — the same output field with two shapes. This is the guard
    # on `last_strict_result` being a string either way.
    verdict = "VERDICT: HOLD - redispatch"
    assert isinstance(STRICT_VERDICT.findall(verdict)[-1], tuple)  # the hazard
    assert last_whole_match(STRICT_VERDICT, verdict) == verdict

    url = "https://github.com/o/r/pull/7"
    assert last_whole_match(PR_URL, f"see {url} now") == url


def test_last_whole_match_takes_the_LAST_match_and_None_when_there_is_none():
    out = "VERDICT: MERGE\nlater\nVERDICT: HOLD - redispatch"
    assert last_whole_match(STRICT_VERDICT, out) == "VERDICT: HOLD - redispatch"
    assert last_whole_match(STRICT_VERDICT, "no verdict here") is None


# --- LOOSE_VERDICT: strictly wider, or the adjudication measures nothing ---

def test_loose_is_strictly_looser_than_strict():
    looser_only = [
        "    VERDICT: MERGE",
        "**VERDICT: HOLD**",
        "verdict: merge",
        'the run said "VERDICT: MERGE" at the end',
    ]
    for text in looser_only:
        assert LOOSE_VERDICT.search(text), f"loose should match: {text!r}"
        assert not STRICT_VERDICT.search(text), f"strict should not: {text!r}"


def test_loose_still_requires_the_word_verdict():
    assert not LOOSE_VERDICT.search("this PR is a MERGE candidate")


# --- The two URL predicates: pull-only vs the issue alternative ---

def test_pr_url_matches_a_pull_url():
    assert PR_URL.search("opened https://github.com/o/r/pull/42 just now")


def test_pr_url_does_not_match_an_issue_url():
    # Correct for the 16 pull-only COMPLETION_PATTERN declarations. NOT correct
    # for plan-revision/plan-new — those get PR_OR_ISSUE_URL below.
    assert not PR_URL.search("https://github.com/o/r/issues/42")


def test_pr_or_issue_url_accepts_the_stop_issue_completion():
    # plan-revision.sh:220 / plan-new.sh:245 / plan_revision_workflow.py:49
    # declare `/(pull|issues)/`. Replaying those logs against the pull-only
    # pattern would score a LAWFUL completion as a miss — the exact way this
    # tool could inflate the number it exists to report honestly.
    assert PR_OR_ISSUE_URL.search("https://github.com/o/r/issues/42")
    assert PR_OR_ISSUE_URL.search("https://github.com/o/r/pull/42")


def test_pr_or_issue_url_still_rejects_an_unrelated_github_path():
    assert not PR_OR_ISSUE_URL.search("https://github.com/o/r/commit/abc123")


# --- workflow_of ---

def test_workflow_of_strips_the_run_timestamp(tmp_path):
    p = tmp_path / "build-draft-minor-20260806-173722.jsonl"
    assert workflow_of(p) == "build-draft-minor"


def test_workflow_of_leaves_a_name_without_a_timestamp_alone(tmp_path):
    assert workflow_of(tmp_path / "custom.jsonl") == "custom"


# --- read_log ---

def test_read_log_returns_the_result_envelope_and_assistant_text(tmp_path):
    p = _write(
        tmp_path,
        [
            {"type": "system", "subtype": "init"},
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "hello"}]},
            },
            {"type": "result", "subtype": "success", "result": "VERDICT: MERGE"},
        ],
    )
    env, turns, unparseable = read_log(p)
    assert env["subtype"] == "success"
    assert turns == ["hello"]
    assert unparseable == 0


def test_read_log_result_key_absent_is_distinct_from_present_and_empty(tmp_path):
    # E1(d): every error subtype drops the `result` key entirely. A reader
    # that conflated absent with "" would erase that finding.
    absent = _write(tmp_path, [{"type": "result", "subtype": "error_max_turns"}])
    env, _, _ = read_log(absent)
    assert "result" not in env

    empty = tmp_path / "y-20260808-010203.jsonl"
    empty.write_text(json.dumps({"type": "result", "result": ""}) + "\n")
    env2, _, _ = read_log(empty)
    assert "result" in env2 and env2["result"] == ""


def test_read_log_a_truncated_final_line_yields_no_envelope_rather_than_raising(
    tmp_path,
):
    # The common cause is an IN-FLIGHT run, including the one invoking this
    # tool — E5 recorded its own still-running log as a "truncated log" before
    # it finished. `main()` lists these for adjudication instead of counting
    # them as misses.
    p = tmp_path / "z-20260808-010203.jsonl"
    p.write_text(json.dumps({"type": "system"}) + '\n{"type":"resu')
    env, turns, unparseable = read_log(p)
    assert env is None and turns == []
    assert unparseable == 1


def test_read_log_counts_malformed_lines_rather_than_dropping_them_silently(tmp_path):
    # A malformed line MID-file is real corruption, not benign truncation: it
    # shrinks the reconstructed console stream and would change a count with no
    # trace. The count is what distinguishes "no signal" from "signal lost".
    p = tmp_path / "w-20260808-010203.jsonl"
    p.write_text(
        json.dumps({"type": "system"})
        + "\n{not json at all}\n"
        + json.dumps(
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "t"}]}}
        )
        + "\n"
        + json.dumps({"type": "result", "subtype": "success"})
        + "\n"
    )
    env, turns, unparseable = read_log(p)
    assert env is not None and turns == ["t"]
    assert unparseable == 1


def test_read_log_counts_a_non_dict_json_line_as_unparseable(tmp_path):
    p = tmp_path / "v-20260808-010203.jsonl"
    p.write_text('"a bare string"\n' + json.dumps({"type": "result"}) + "\n")
    _, _, unparseable = read_log(p)
    assert unparseable == 1


def test_read_log_the_last_result_event_wins(tmp_path):
    p = _write(
        tmp_path,
        [
            {"type": "result", "subtype": "first"},
            {"type": "result", "subtype": "second"},
        ],
    )
    env, _, _ = read_log(p)
    assert env["subtype"] == "second"


def test_read_log_non_text_assistant_blocks_are_ignored(tmp_path):
    p = _write(
        tmp_path,
        [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Bash"},
                        {"type": "text", "text": "kept"},
                    ]
                },
            }
        ],
    )
    _, turns, _ = read_log(p)
    assert turns == ["kept"]


# --- The BUCKET MAPPING. It had no coverage, and it shipped a wrong number:
# --- `review-runs` declares no COMPLETION_PATTERN, fell through to the pr_url
# --- bucket, and the tool reported 8 strict negatives where the honest in-scope
# --- figure was 2. Five of eight were artifacts of the tool's own bucketing,
# --- in the one tool whose entire purpose is reporting that number honestly.


def test_every_patternless_workflow_really_declares_no_completion_pattern():
    """The list is a claim about the tree, so check it against the tree.

    A stale entry here silently un-scores a workflow that DOES have a contract,
    which is the same defect as the one it was added to fix, pointing the other
    way.
    """
    root = Path(__file__).resolve().parents[4]
    for wf in PATTERNLESS_WORKFLOWS:
        candidates = list(root.glob(f"scripts/workflows/**/{wf}.sh"))
        assert candidates, f"{wf} is listed as patternless but no such script exists"
        for c in candidates:
            assert "COMPLETION_PATTERN" not in c.read_text(), (
                f"{c} DOES declare a COMPLETION_PATTERN — it has a contract and must be "
                "scored. Remove it from PATTERNLESS_WORKFLOWS."
            )


def test_no_workflow_lacking_a_pattern_is_missing_from_the_list():
    """The inverse, and the one that actually failed.

    A new patternless workflow that nobody adds here falls through to the pr_url
    bucket and is scored against a contract it never claimed — manufacturing a
    miss. This fails the moment that happens, naming the file.
    """
    root = Path(__file__).resolve().parents[4]
    scripts = list(root.glob("scripts/workflows/*.sh")) + list(
        root.glob("scripts/workflows/children/*.sh")
    )
    assert scripts, "found no workflow scripts — this guard would pass vacuously"
    for s in scripts:
        if "COMPLETION_PATTERN" in s.read_text():
            continue
        assert s.stem in PATTERNLESS_WORKFLOWS, (
            f"{s.name} declares no COMPLETION_PATTERN and is not in "
            "PATTERNLESS_WORKFLOWS, so it is being scored against a contract it "
            "does not have."
        )


def test_the_three_buckets_are_disjoint():
    """Order-dependent if/elif means an overlap would silently resolve by
    position rather than by intent."""
    sets = [set(VERDICT_WORKFLOWS), set(ISSUE_ALTERNATIVE_WORKFLOWS), set(PATTERNLESS_WORKFLOWS)]
    for i, a in enumerate(sets):
        for b in sets[i + 1:]:
            assert not (a & b), f"a workflow is in two buckets: {a & b}"
