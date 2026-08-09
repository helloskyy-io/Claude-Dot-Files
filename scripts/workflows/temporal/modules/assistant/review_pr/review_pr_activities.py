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

import json
import re
from pathlib import Path

from .. import assistant_activities as _shared
from . import review_pr_helper as helper

# Re-exported so callers use one name regardless of where it is implemented.
load_prompt = _shared.load_prompt
render = _shared.render

V1_SCRIPT = "review-pr.sh"


def fetch_pr(pr_number: str, repo_root: Path) -> dict:
    """PR metadata. Raises rather than returning a partial dict."""
    raw = _shared.gh(
        ["pr", "view", pr_number, "--json", "headRefName,state,title"], repo_root
    )
    return json.loads(raw)


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
    raw = _shared.gh(["pr", "view", pr_number, "--json", "comments"], repo_root)
    return sum(
        1 for c in json.loads(raw).get("comments", [])
        if helper.PR_REVIEW_BLOCK.search(c.get("body", "") or "")
    )


def latest_pr_review_block(pr_number: str, repo_root: Path) -> str | None:
    """The LATEST `pr_review:` block on this PR, or None if there is none.

    The address, applied: container id is the PR number, the block marker is the
    fence-anchored regex, and the ordering rule is comment creation order with
    LAST WINS (`memory-model.md` §6.2). Sequence is derived from that ordering
    rather than from the block's own `pass:` counter — a counter written by the
    producer can be wrong, and §6.4 measures that it was.
    """
    raw = _shared.gh(["pr", "view", pr_number, "--json", "comments"], repo_root)
    blocks = [
        m.group(1)
        for c in json.loads(raw).get("comments", [])
        for m in [helper.PR_REVIEW_BLOCK.search(c.get("body", "") or "")]
        if m
    ]
    return blocks[-1] if blocks else None


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
        max_turns=int(_shared.v1_constant(V1_SCRIPT, "MAX_TURNS")), verbose=verbose,
        exit_record_schema=exit_record_schema, log_file=log_file,
    )
