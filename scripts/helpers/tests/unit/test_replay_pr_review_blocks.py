"""Unit tests for the `pr_review:` block replay tool.

The E7 measurement's two headline numbers — "delta empty 0 of 7" and "`converged:
true` asserted 1 of 14" — are only trustworthy if the extractor finds every block
and distinguishes an ABSENT `converged` key from a `false` one. A tool that
silently read absent-as-false would have reported a different, wrong cross-tab.
Both properties are asserted below with an input that breaks them.
"""

from __future__ import annotations

from measure.replay_pr_review_blocks import (
    ATTEMPT,
    CONVERGED,
    FENCE,
    FINDING_ID,
    PASS,
    VERDICT,
)

# Shaped from a real archived comment (PR #58 pass 3), trimmed.
REAL_COMMENT = """\
Some human-readable prose first.

| Item | Disposition |
|---|---|
| a | fixed |

```yaml
pr_review:
  pr: 58
  pass: 3
  attempt: 4
  verdict: HOLD
  converged: false
  findings:
    - id: mutate-multiline-old-miscounts
      title: something breaks
      category: correctness
    - id: f821-allowlist-drift
      title: something else breaks
      category: correctness
```

Trailing prose.
"""


class TestFence:
    def test_extracts_the_yaml_block_from_a_real_comment(self):
        blocks = FENCE.findall(REAL_COMMENT)
        assert len(blocks) == 1
        assert blocks[0].startswith("pr_review:")

    def test_accepts_the_yml_spelling_too(self):
        assert FENCE.findall("```yml\npr_review:\n  pr: 1\n```")

    def test_ignores_a_fenced_block_that_is_not_a_pr_review(self):
        assert not FENCE.findall("```yaml\nsomething_else:\n  pr: 1\n```")

    def test_finds_both_blocks_when_one_comment_carries_two(self):
        assert len(FENCE.findall(REAL_COMMENT + REAL_COMMENT)) == 2


class TestScalarFields:
    def test_reads_pass_attempt_and_verdict(self):
        body = FENCE.findall(REAL_COMMENT)[0]
        assert PASS.search(body).group(1) == "3"
        assert ATTEMPT.search(body).group(1) == "4"
        assert VERDICT.search(body).group(1) == "HOLD"

    def test_converged_false_and_true_both_parse(self):
        body = FENCE.findall(REAL_COMMENT)[0]
        assert CONVERGED.search(body).group(1) == "false"
        assert CONVERGED.search("  converged: true").group(1) == "true"

    def test_an_absent_converged_key_yields_no_match_not_a_false(self):
        # This is the denominator-honesty property. `None` dates a block to
        # before the flag shipped; `False` asserts the model said not-converged.
        # Conflating them would silently pad the `converged: false` cell.
        assert CONVERGED.search("pr_review:\n  pr: 1\n  verdict: HOLD\n") is None

    def test_verdict_does_not_match_the_word_inside_a_finding_title(self):
        assert VERDICT.search("    title: the verdict: parser is untested") is None


class TestFindingIds:
    def test_extracts_every_id_in_order(self):
        body = FENCE.findall(REAL_COMMENT)[0]
        assert FINDING_ID.findall(body) == [
            "mutate-multiline-old-miscounts",
            "f821-allowlist-drift",
        ]

    def test_handles_both_indent_depths_seen_in_the_archive(self):
        assert FINDING_ID.findall("  - id: two-space\n      - id: six-space") == [
            "two-space",
            "six-space",
        ]

    def test_does_not_capture_a_trailing_comment(self):
        assert FINDING_ID.findall("    - id: slug-here  # note") == ["slug-here"]

    def test_does_not_match_a_non_id_list_item(self):
        assert FINDING_ID.findall("    - title: not an id") == []
