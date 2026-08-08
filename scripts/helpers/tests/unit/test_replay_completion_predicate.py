"""Unit tests for the completion-predicate replay tool.

These guard the properties the E5 measurement's *validity* rests on, not merely
that the code runs. Two in particular would silently invalidate the reported
zero if they broke:

  * If `STRICT_VERDICT` were unanchored, it would match a verdict quoted inside
    prose and E5's "0 quoted-prior-pass matches" would be unfalsifiable.
  * If `LOOSE_VERDICT` were not actually looser than strict, the adjudication
    procedure would be comparing a set against itself and "strict == loose on
    51 of 51" would be a tautology rather than evidence.

Each assertion below is paired with an input that makes it FAIL if the property
is violated — a strict-matches case beside a strict-must-not-match case.
"""

from __future__ import annotations

import json

from measure.replay_completion_predicate import (
    LOOSE_VERDICT,
    PR_URL,
    STRICT_VERDICT,
    read_log,
    workflow_of,
)


class TestStrictVerdict:
    def test_matches_a_verdict_on_its_own_line(self):
        assert STRICT_VERDICT.search("some prose\nVERDICT: MERGE")

    def test_matches_each_of_the_three_routing_tokens(self):
        for token in (
            "VERDICT: MERGE",
            "VERDICT: HOLD - redispatch",
            "VERDICT: HOLD - needs-assistance",
        ):
            assert STRICT_VERDICT.search(token), token

    def test_does_not_match_a_verdict_quoted_inside_prose(self):
        # The anchoring is the whole defence against routing on a sentence a run
        # wrote about its own history (routing.py:39-41 states this rationale).
        assert not STRICT_VERDICT.search('the last pass returned "VERDICT: MERGE" so')

    def test_does_not_match_an_indented_verdict(self):
        # Not a bug — a documented consequence. A formatter that indents the
        # child's output would make the parent's grep blind, and this test is
        # what makes that fact visible rather than surprising.
        assert not STRICT_VERDICT.search("prose\n    VERDICT: MERGE")

    def test_does_not_match_an_unknown_hold_kind(self):
        assert not STRICT_VERDICT.search("VERDICT: HOLD - escalate")

    def test_findall_returns_matches_in_order_so_last_wins(self):
        out = "VERDICT: MERGE\nlater\nVERDICT: HOLD - redispatch"
        assert [m[0] for m in STRICT_VERDICT.findall(out)] == [
            "MERGE",
            "HOLD - redispatch",
        ]


class TestLooseVerdict:
    def test_is_strictly_looser_than_strict(self):
        # The candidate set must be able to contain something the strict set
        # cannot, or the adjudication procedure measures nothing.
        looser_only = [
            "    VERDICT: MERGE",
            "**VERDICT: HOLD**",
            "verdict: merge",
            'the run said "VERDICT: MERGE" at the end',
        ]
        for text in looser_only:
            assert LOOSE_VERDICT.search(text), f"loose should match: {text!r}"
            assert not STRICT_VERDICT.search(text), f"strict should not: {text!r}"

    def test_still_requires_the_word_verdict(self):
        assert not LOOSE_VERDICT.search("this PR is a MERGE candidate")


class TestPrUrl:
    def test_matches_a_pull_url(self):
        assert PR_URL.search("opened https://github.com/o/r/pull/42 just now")

    def test_does_not_match_an_issue_url(self):
        # plan-revision may complete via a STOP issue instead; the PR-URL
        # predicate must not silently accept one (see E6, branch point P6).
        assert not PR_URL.search("https://github.com/o/r/issues/42")


class TestWorkflowOf:
    def test_strips_the_run_timestamp(self, tmp_path):
        p = tmp_path / "build-draft-minor-20260806-173722.jsonl"
        assert workflow_of(p) == "build-draft-minor"

    def test_leaves_a_name_without_a_timestamp_alone(self, tmp_path):
        assert workflow_of(tmp_path / "custom.jsonl") == "custom"


class TestReadLog:
    def _write(self, tmp_path, events):
        p = tmp_path / "x-20260808-010203.jsonl"
        p.write_text("\n".join(json.dumps(e) for e in events) + "\n")
        return p

    def test_returns_the_result_envelope_and_assistant_text(self, tmp_path):
        p = self._write(
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
        env, turns = read_log(p)
        assert env["subtype"] == "success"
        assert turns == ["hello"]

    def test_result_key_absent_is_distinct_from_present_and_empty(self, tmp_path):
        # E1(d): every error subtype drops the `result` key entirely. A reader
        # that conflated absent with "" would erase that finding.
        absent = self._write(
            tmp_path, [{"type": "result", "subtype": "error_max_turns"}]
        )
        env, _ = read_log(absent)
        assert "result" not in env

        empty = tmp_path / "y-20260808-010203.jsonl"
        empty.write_text(json.dumps({"type": "result", "result": ""}) + "\n")
        env2, _ = read_log(empty)
        assert "result" in env2 and env2["result"] == ""

    def test_a_truncated_final_line_yields_no_envelope_rather_than_raising(
        self, tmp_path
    ):
        # Observed in the wild: build-draft-20260808-145403.jsonl ends mid-line.
        p = tmp_path / "z-20260808-010203.jsonl"
        p.write_text(json.dumps({"type": "system"}) + '\n{"type":"resu')
        env, turns = read_log(p)
        assert env is None and turns == []

    def test_the_last_result_event_wins(self, tmp_path):
        p = self._write(
            tmp_path,
            [
                {"type": "result", "subtype": "first"},
                {"type": "result", "subtype": "second"},
            ],
        )
        env, _ = read_log(p)
        assert env["subtype"] == "second"

    def test_non_text_assistant_blocks_are_ignored(self, tmp_path):
        p = self._write(
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
        _, turns = read_log(p)
        assert turns == ["kept"]
