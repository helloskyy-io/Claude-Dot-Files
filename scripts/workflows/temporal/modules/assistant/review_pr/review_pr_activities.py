"""External I/O for review-pr — Layer 3.

Thin. The shared mechanics — `gh` invocation, prompt loading, rendering and the
`run-claude.sh` delegation — live in the promoted `assistant_activities`,
because more than one workflow uses them (§10.1 rule 3). Only what is genuinely
review-pr's own sits here.

An earlier version duplicated all of it and carried two bugs PM3 found on the
first live run: `--repo` conflated a filesystem path with a `gh` OWNER/NAME
slug, and `run-claude.sh` was sourced before its five required environment
variables were set, tripping the source-time guard with exit 127. Both are fixed
once, in the promoted module — which is the argument for promotion, made
concrete.

IDEMPOTENCY (§7.1 / addendum §A1): `run_disposition` posts a comment and may
file issues. Under Temporal a retry is a NEW ATTEMPT, not a replay.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import assistant_activities as _shared
from . import review_pr_helper as helper

# Re-exported so callers use one name regardless of where it is implemented.
load_prompt = _shared.load_prompt
render = _shared.render

WORKFLOW_KEY = "review-pr"   # the run log's per-workflow bin; see run_log.py
MAX_TURNS_KEY = WORKFLOW_KEY


def fetch_pr(pr_number: str, repo_root: Path) -> dict:
    """PR metadata. Raises rather than returning a partial dict."""
    # `expect=dict`, because this reader indexes by KEY. `GH_JSON_SHAPES` — the
    # permissive "either shape `gh --json` can send" — would let a JSON array
    # through to an `AttributeError` in somebody else's function, which is the
    # second exception family `gh_json` exists to prevent. The policy argument
    # for why `expect` is stated at every call site lives at `gh_json`; what
    # belongs here is the local fact.
    reply = _shared.gh_json(
        ["pr", "view", pr_number, "--json", "headRefName,state,title"], repo_root,
        expect=dict,
    )
    # A MAPPING IS NOT AN ANSWER. `expect=dict` proves the reply is indexable and
    # nothing more; `{"message": "Not Found"}` satisfies it and then reaches
    # `pr["headRefName"]` in `run_review` as a `KeyError` — which the entrypoint
    # does NOT catch, so an operator gets a raw traceback after the journal bag
    # and the worktree already exist. `thread_snapshot` below already converts
    # this shape into the `RuntimeError` the caller handles; this is the other
    # `expect=dict` caller getting the same treatment.
    missing = [k for k in ("headRefName", "state") if not isinstance(reply.get(k), str)]
    if missing:
        raise RuntimeError(
            f"`gh pr view {pr_number}` returned a JSON object without usable "
            f"{'/'.join(missing)}. Keys present: {sorted(reply)[:10]}. This is a "
            f"reply that PARSED without ANSWERING — check the PR number and the "
            f"repo the run is pointed at."
        )
    return reply


# A review pass's record carries a 32-lowercase-hex nonce (`exit-protocol.md`).
# A fenced `pr_review:` block without one was written by something that is not
# a review pass — today, a build run's decision log borrowing the key.
_RUN_ID_IN_BLOCK = re.compile(r"^\s*run_id:\s*[0-9a-f]{32}\s*$", re.M)


def count_prior_passes(pr_number: str, repo_root: Path) -> int:
    """How many disposition comments already exist on this PR.

    Counts comments carrying a `pr_review:` yaml BLOCK — the machine-readable
    marker, not prose mentioning the phrase. That key is a WIRE FORMAT, not a
    filename; do not "fix" it to match the renamed script.

    THE PREDICATE IS FENCE-ANCHORED, AND IT WAS NOT. A plain substring test
    matched any comment that merely MENTIONS the key — a Post-Run Reflection, a
    build-refine summary, a brief quoting the wire format. Measured by Phase 2
    across all 39 PRs at `bcdb519`: 18 matches against the fence-anchored 15,
    i.e. 3 false positives on 2 of the 8 PRs carrying a block. The consequence
    is in the archive and it is DURABLE: PR #31's blocks run `pass: 1, 2, 4` —
    there was never a pass 3 — and PR #66's single block is labelled `pass: 3`
    and is pass 1. `pass:` is a field of the durable record, so an over-matching
    reader writes a wrong number into the working record permanently. Tracked as issue #68.

    The declaration lives in `review_pr_helper.PR_REVIEW_BLOCK`, not here:
    `exit-protocol.md` §6 requires the record's schema AND ITS ADDRESS to be
    declared once, and this over-match is the measured instance that widened
    that rule. `children/review-pr.sh:142` carries the same defect and is NOT
    fixed here — it is the frozen V1 fleet (§7).
    """
    return thread_snapshot(pr_number, repo_root)[0]


def thread_snapshot(pr_number: str, repo_root: Path) -> tuple[int, list[str]]:
    """The pass count and the block window, from ONE `gh` read.

    LITERALLY ONE OBSERVATION, WHICH THE TWO CALLERS ABOVE ONLY CLAIMED TO BE.
    `count_prior_passes` and `pr_review_blocks` each issued their own
    `gh pr view --json comments`, so the count and the window were two samples
    of a thread that a concurrent comment can change between them. Retrying them
    as a unit — which `_read_thread_for_invariant` does — covers a FAILURE and
    does nothing about SKEW: a count read that misses the child's just-posted
    comment paired with a window read that sees it makes
    `_assert_block_matches_record` raise *"posted no new `pr_review:` block"* and
    kill a completed, already-routed review. Deriving both from one reply is the
    only thing that closes it, and it removes a `gh` round trip from the path
    whose named failure mode is rate limiting.

    ONE ENTRY PER PASS, NOT PER BLOCK, AND THAT IS THE OTHER HALF. A pass posts
    one comment however many blocks it quotes — `count_prior_passes` has always
    said so — so the window takes the LAST block of each comment carrying one.
    A quoted block is a restatement of a pass already in the window, not a pass:
    counting it would make `ConvergenceAssessment.passes` disagree with
    `this_pass`, and a comment quoting a NON-adjacent block would inject a
    phantom pass whose closed findings read as re-opened, withholding
    convergence on that PR permanently.

    LAST-WITHIN-THE-COMMENT IS NOW A RULE THE PROMPT STATES, WHICH IT WAS NOT.
    An earlier version of this docstring cited `disposition.md`'s INVARIANT 1 as
    the producer-side guarantee. A review pass read the prompt: INVARIANT 1 says
    *carry every prior-pass FINDING forward until it reaches an explicit
    disposition* — about restating ids INSIDE the block — and the prompt said
    nothing anywhere about quoting a whole prior block or where to put it. So
    last-wins was an unbacked heuristic with a live failure: a pass appending the
    superseded block BELOW its own returns the PRIOR block here, which makes
    `_assert_block_matches_record` compare this pass's record against the
    previous pass's findings and hard-fail a correct, already-posted,
    already-routed review — the exact loss the `search`-based bug caused, in the
    mirror direction — while also putting the wrong block at the end of the
    window, so `prior_pass_blocks` leaks this pass's own block into the history.
    `disposition.md` Stage 5 now pins the order explicitly, and a false
    cross-file citation is a worse defect than a missing one because it stops
    the next reader checking.

    ORDERING IS COMMENT ORDER, NEVER THE BLOCK'S OWN `pass:` INTEGER. That
    counter is producer-written and `memory-model.md` §6.4 measured it wrong on
    the most recently reviewed PR in the repo (issue #68); PR #31's blocks run
    1, 2, 4. Consecutiveness is a property of the sequence, not of the label.
    """
    # A BLOCK IS NOT A PASS UNTIL IT CARRIES A RUN ID. Fence-anchoring (issue #68)
    # was right about the trigger it was written for — prose mentioning the phrase
    # — and silent about the one that arrived: a BUILD run posting a genuine
    # fenced `pr_review:` block for its own decision log. Nothing tells a build
    # run that key is the review workflow's address, so it borrowed it, and every
    # reader here counted it as a review pass.
    #
    # MEASURED on PR #94: two comments carry the key without being passes, and the
    # V1 reader reports 3 where the truth is 1. A wrong `pass:` propagates into the
    # durable record and into the convergence predicate that reads it.
    #
    # `run_id` IS THE DISCRIMINATOR AND IT IS ALREADY REQUIRED. `exit-protocol.md`
    # mandates a 32-lowercase-hex nonce on every review pass's record, so this
    # filters on something a real pass already has rather than on a new
    # convention nobody has adopted. Fixing it HERE rather than in the prompts is
    # deliberate: a prompt line telling build runs to pick a different key is an
    # administrative control that each run must remember, and this cannot be
    # forgotten by anyone.
    # `expect=dict` PROVES IT IS A MAPPING AND NOT THAT IT HAS THE KEY, which is
    # the half a shape check cannot carry. `{"message": "Not Found"}` is a dict;
    # `.get("comments", [])` would then hand back `[]`, this function would
    # report ZERO prior passes on a thread that has some, and the invariant
    # check downstream raises "posted no new block" — blaming the child for a
    # read failure and costing the review this retry exists to protect. A
    # missing key is a failed READ, so it is raised as the `RuntimeError` the
    # caller's retry already catches rather than silently answered as empty.
    reply = _shared.gh_json(
        ["pr", "view", pr_number, "--json", "comments"], repo_root, expect=dict)
    comments = reply.get("comments")
    if not isinstance(comments, list):
        raise RuntimeError(
            f"gh pr view {pr_number} --json comments returned a JSON object with "
            f"no usable `comments` list (got {type(comments).__name__}). Treating "
            f"that as an empty thread would under-count the prior passes on this "
            f"PR. Keys present: {sorted(reply)[:10]}")
    window = [
        matches[-1].group(1)
        for c in comments
        if (matches := [
            m for m in helper.PR_REVIEW_BLOCK.finditer(c.get("body", "") or "")
            if _RUN_ID_IN_BLOCK.search(m.group(1))
        ])
    ]
    return len(window), window


def pr_review_blocks(pr_number: str, repo_root: Path) -> list[str]:
    """This PR's `pr_review:` blocks, one per pass, in comment-creation order.

    A thin projection of `thread_snapshot`.

    NO PRODUCTION CALLERS TODAY — corrected 2026-08-11. This said it was "kept
    because two callers want only the window"; verified three ways that no such
    caller exists (grep for call sites, an AST scan of every `act.*` call in
    `review_pr_workflow.py`, which calls `thread_snapshot` directly, and a
    test-caller count of three). Retained for the tests that use it, and stated
    as retained rather than as load-bearing — a docstring claiming callers that
    do not exist makes the next editor preserve a projection nobody needs,
    which is the exact class this PR spent fifteen tombstone lines deleting
    `latest_pr_review_block` to fix.
    """
    return thread_snapshot(pr_number, repo_root)[1]


# `latest_pr_review_block` WAS HERE AND IS DELETED, not moved.
#
# It was a one-line projection — `helper.this_pass_block(pr_review_blocks(...))`
# — with no production caller, kept because several docstrings pointed at it as
# the place the "latest block" rule was written down. Phase 4 made that
# untenable rather than merely untidy: `this_pass_block` now takes the run nonce
# and answers *which block is THIS PASS'S*, which on a thread carrying a later
# third-party comment is not the same question as *which block is last*. A
# no-caller helper whose name promises the second while delegating to the first
# is a positional inference with no owner — the exact shape
# `test_selecting_from_the_END_of_a_sequence_happens_only_where_it_is_owned`
# exists to keep out of this package.
#
# The rule itself did not live here and still does not: last-wins ACROSS
# comments and WITHIN one is `thread_snapshot`'s, and `memory-model.md` §6.2 is
# its statement. Its three tests moved onto `pr_review_blocks`, which is what
# actually implements it.


def load_shared_block(name: str, shared_sh: Path) -> str:
    """Extract one heredoc block from the legacy `common/shared-prompts.sh`.

    TRANSITIONAL, and now nearly dead: the blocks this reads have been promoted
    to `modules/assistant/prompts/*.md`. Kept only until review-pr's prompt is
    re-pointed at the promoted copies, so the two cannot silently diverge in the
    meantime — a copy would drift, and drift in a shared block is precisely what
    the promotion rule exists to prevent.
    """
    text = shared_sh.read_text()
    m = re.search(rf"{name}=\$\(cat <<'(\w+)'\n(.*?)\n\1", text, re.S)
    if not m:
        raise ValueError(f"shared block {name} not found in {shared_sh}")
    return m.group(2)


def run_disposition(prompt: str, repo_root: Path, model_key: str,
                    completion_pattern: str, worktree: Path | None = None,
                    verbose: bool = False, exit_record_schema: str | None = None,
                    log_file: Path | None = None, run_id: str | None = None) -> str:
    """Invoke the disposition pass on the PR's OWN tree.

    ISOLATION IS NOT OPTIONAL HERE EITHER, and for a reason beyond safety: a
    review executed in the repo root reads whatever that root has checked out —
    `main` — not the branch under review. V1 checks the PR branch out into a
    worktree (`git worktree add -f ... origin/$PR_BRANCH`) precisely so the
    reviewer reads the code it is ruling on. An earlier V2 passed the repo root
    as the execution directory, so the disposition engine would have verified
    claims against the wrong tree while reporting full confidence.
    """
    return _shared.run_claude(
        prompt, model_key=model_key, workflow_key=WORKFLOW_KEY,
        completion_pattern=completion_pattern,
        repo_root=repo_root, worktree=worktree or repo_root,
        max_turns=_shared.max_turns(MAX_TURNS_KEY), verbose=verbose,
        exit_record_schema=exit_record_schema, log_file=log_file, run_id=run_id,
    )
