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

MAX_TURNS_KEY = "review-pr"


def fetch_pr(pr_number: str, repo_root: Path) -> dict:
    """PR metadata. Raises rather than returning a partial dict."""
    return _shared.gh_json(
        ["pr", "view", pr_number, "--json", "headRefName,state,title"], repo_root
    )


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
    reader writes a wrong number into Kind 1 permanently. Tracked as issue #68.

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
    raw = _shared.gh_json(["pr", "view", pr_number, "--json", "comments"], repo_root)
    window = [
        matches[-1].group(1)
        for c in raw.get("comments", [])
        if (matches := list(helper.PR_REVIEW_BLOCK.finditer(c.get("body", "") or "")))
    ]
    return len(window), window


def pr_review_blocks(pr_number: str, repo_root: Path) -> list[str]:
    """This PR's `pr_review:` blocks, one per pass, in comment-creation order.

    A thin projection of `thread_snapshot`, kept because two callers want only
    the window and naming the projection is cheaper than teaching each of them
    to discard the count.
    """
    return thread_snapshot(pr_number, repo_root)[1]


def latest_pr_review_block(pr_number: str, repo_root: Path) -> str | None:
    """The LATEST `pr_review:` block on this PR, or None if there is none.

    NO PRODUCTION CALLER TODAY, and that is worth knowing before reading the
    rest. `run_review` takes the whole window from `thread_snapshot` and names
    this pass's block with `helper.this_pass_block`, which is where the
    positional inference now lives and which `phase4_fleet_migration.md`'s
    run-nonce checkbox replaces. This stays as the one-line composition of those
    two, because several docstrings point at it as the place the "latest block"
    rule is written down and moving that prose would cost more than the line.

    The address, applied: container id is the PR number, the block marker is the
    fence-anchored regex, and the ordering rule is comment creation order with
    LAST WINS (`memory-model.md` §6.2). Sequence is derived from that ordering
    rather than from the block's own `pass:` counter — a counter written by the
    producer can be wrong, and §6.4 measures that it was.

    LAST WINS *WITHIN* A COMMENT TOO, which is why this is `finditer` and not
    `search`. A comment may legitimately carry more than one block: INVARIANT 1
    of `disposition.md` requires each pass to carry prior findings forward, so a
    disposition that quotes the block it supersedes above its own is a shape the
    prompt invites. `search` returns the FIRST match, so on such a comment this
    returned the SUPERSEDED block — and the render↔record invariant then compared
    this pass's typed record against the previous pass's findings and hard-failed
    a correct run, *after* the comment was already posted. `replay_pr_review_blocks`
    has always used `findall` here; this was the third reader disagreeing with the
    other two about what "the latest block" means.

    THE SAME RULE `count_prior_passes` APPLIES, AND THEY ARE NOW ONE FUNCTION.
    That count is COMMENTS THAT CARRY A BLOCK, because the delta it feeds
    (`posted <= prior_pass` in `review_pr_workflow`) is a count of passes and one
    pass posts one comment however many blocks it quotes. `thread_snapshot`
    derives both from one reply under that single rule, so the count and the
    window can no longer disagree about what a pass is — they briefly did, and a
    quoting comment made `ConvergenceAssessment.passes` exceed `this_pass`.

    EXPRESSED ON `pr_review_blocks` RATHER THAN RE-EXTRACTING. The extraction
    was typed twice for one commit when the window reader was added, which is
    the duplicated-reader defect `exit-protocol.md` §6 covers — and the measured
    instance of it (issue #68) is this exact marker.
    """
    return helper.this_pass_block(pr_review_blocks(pr_number, repo_root))


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
                    log_file: Path | None = None) -> str:
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
        prompt, model_key=model_key, completion_pattern=completion_pattern,
        repo_root=repo_root, worktree=worktree or repo_root,
        max_turns=_shared.max_turns(MAX_TURNS_KEY), verbose=verbose,
        exit_record_schema=exit_record_schema, log_file=log_file,
    )
