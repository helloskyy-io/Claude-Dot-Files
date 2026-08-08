"""Unit tests for the `pr_review:` block replay tool.

The E7 measurement's headline numbers are only trustworthy if the extractor
finds every block, distinguishes an ABSENT `converged` key from a `false` one,
and attributes each per-finding `disposition` to the finding it belongs to.
That last one is what makes the OPEN-subset delta computable at all — and the
open subset is the only one that can go empty, because the block is cumulative
(pass N restates every prior id with its disposition updated in place).

A tool that silently read absent-as-false, or that let finding N's disposition
leak onto finding N-1, would report a different and wrong cross-tab. Each such
property is asserted below with an input that breaks it.

Flat comment-delimited functions, matching `test_check_settings.py` in this
directory; `class Test` grouping appears nowhere else in the repo.
"""

from __future__ import annotations

from measure.replay_pr_review_blocks import (
    ATTEMPT,
    CATEGORY,
    CONVERGED,
    DISPOSITION,
    FENCE,
    FINDING_ENTRY,
    FINDING_ID,
    PASS,
    VERDICT,
    open_ids,
)

# Shaped from a real archived comment (PR #58 pass 3), trimmed. The mixed
# dispositions are the real shape: a cumulative block carries closed findings
# alongside open ones.
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
      disposition: fixed
    - id: f821-allowlist-drift
      title: something else breaks
      category: correctness
      disposition: hold
```

Trailing prose.
"""


def _body():
    return FENCE.findall(REAL_COMMENT)[0]


def _entries(body):
    out = []
    for m in FINDING_ENTRY.finditer(body):
        span = m.group(2)
        d = DISPOSITION.search(span)
        c = CATEGORY.search(span)
        out.append(
            {
                "id": m.group(1),
                "disposition": d.group(1) if d else None,
                "category": c.group(1) if c else None,
            }
        )
    return out


# --- FENCE ---

def test_fence_extracts_the_yaml_block_from_a_real_comment():
    blocks = FENCE.findall(REAL_COMMENT)
    assert len(blocks) == 1
    assert blocks[0].startswith("pr_review:")


def test_fence_accepts_the_yml_spelling_too():
    assert FENCE.findall("```yml\npr_review:\n  pr: 1\n```")


def test_fence_ignores_a_fenced_block_that_is_not_a_pr_review():
    assert not FENCE.findall("```yaml\nsomething_else:\n  pr: 1\n```")


def test_fence_finds_both_blocks_when_one_comment_carries_two():
    assert len(FENCE.findall(REAL_COMMENT + REAL_COMMENT)) == 2


# --- Scalar fields ---

def test_reads_pass_attempt_and_verdict():
    body = _body()
    assert PASS.search(body).group(1) == "3"
    assert ATTEMPT.search(body).group(1) == "4"
    assert VERDICT.search(body).group(1) == "HOLD"


def test_converged_false_and_true_both_parse():
    assert CONVERGED.search(_body()).group(1) == "false"
    assert CONVERGED.search("  converged: true").group(1) == "true"


def test_an_absent_converged_key_yields_no_match_not_a_false():
    # This is the denominator-honesty property. `None` dates a block to
    # before the flag shipped; `False` asserts the model said not-converged.
    # Conflating them would silently pad the `converged: false` cell.
    assert CONVERGED.search("pr_review:\n  pr: 1\n  verdict: HOLD\n") is None


def test_verdict_does_not_match_the_word_inside_a_finding_title():
    assert VERDICT.search("    title: the verdict: parser is untested") is None


# --- Finding ids ---

def test_extracts_every_id_in_order():
    assert FINDING_ID.findall(_body()) == [
        "mutate-multiline-old-miscounts",
        "f821-allowlist-drift",
    ]


def test_handles_both_indent_depths_seen_in_the_archive():
    assert FINDING_ID.findall("  - id: two-space\n      - id: six-space") == [
        "two-space",
        "six-space",
    ]


def test_does_not_capture_a_trailing_comment():
    assert FINDING_ID.findall("    - id: slug-here  # note") == ["slug-here"]


def test_does_not_match_a_non_id_list_item():
    assert FINDING_ID.findall("    - title: not an id") == []


# --- Per-finding disposition/category: the open-subset delta depends on these ---

def test_each_finding_gets_its_own_disposition_and_category():
    assert _entries(_body()) == [
        {
            "id": "mutate-multiline-old-miscounts",
            "disposition": "fixed",
            "category": "correctness",
        },
        {
            "id": "f821-allowlist-drift",
            "disposition": "hold",
            "category": "correctness",
        },
    ]


def test_a_disposition_does_not_leak_from_one_finding_to_the_previous_one():
    # The failure this guards: a field regex run over the WHOLE block would
    # give every finding the first `disposition:` in the file, collapsing the
    # open subset to all-or-nothing and making the E7 delta meaningless.
    body = (
        "findings:\n"
        "    - id: first\n"
        "      title: no disposition on this one\n"
        "    - id: second\n"
        "      disposition: hold\n"
    )
    assert _entries(body) == [
        {"id": "first", "disposition": None, "category": None},
        {"id": "second", "disposition": "hold", "category": None},
    ]


def test_open_ids_counts_only_hold_and_not_the_closed_dispositions():
    # Measured vocabulary across the archive: hold / fixed / deferred /
    # rejected / noted. Only `hold` leaves work outstanding. Counting any of
    # the other four as open would mean the subset never empties either, and
    # E7's corrected ruling would be wrong in the same way the original was.
    entries = [
        {"id": "a", "disposition": "hold"},
        {"id": "b", "disposition": "fixed"},
        {"id": "c", "disposition": "deferred"},
        {"id": "d", "disposition": "rejected"},
        {"id": "e", "disposition": "noted"},
    ]
    assert open_ids(entries) == {"a"}


def test_open_ids_is_empty_when_every_finding_is_closed():
    # PR #42 pass 2 — the one converged block in the archive — is exactly this
    # shape, and it is why the open-subset predicate fires where the all-ids
    # one cannot.
    entries = [
        {"id": "a", "disposition": "fixed"},
        {"id": "b", "disposition": "deferred"},
    ]
    assert open_ids(entries) == set()


def test_open_ids_treats_an_unknown_disposition_as_open_not_closed():
    # Fail-safe direction. A finding whose state nobody established must not
    # empty the open set — that would report convergence never observed. The
    # opposite default is the expensive one.
    assert open_ids([{"id": "a", "disposition": None}]) == {"a"}
    assert open_ids([{"id": "b", "disposition": "escalated"}]) == {"b"}


def test_open_ids_handles_an_entry_with_no_disposition_key_at_all():
    assert open_ids([{"id": "a"}]) == {"a"}
