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

# Re-exported so callers use one name regardless of where it is implemented.
load_prompt = _shared.load_prompt
render = _shared.render

MAX_TURNS = 120


def fetch_pr(pr_number: str, repo_root: Path) -> dict:
    """PR metadata. Raises rather than returning a partial dict."""
    raw = _shared.gh(
        ["pr", "view", pr_number, "--json", "headRefName,state,title"], repo_root
    )
    return json.loads(raw)


def count_prior_passes(pr_number: str, repo_root: Path) -> int:
    """How many disposition comments already exist on this PR.

    Counts comments carrying a `pr_review:` yaml block — the machine-readable
    marker, not prose mentioning the phrase. That key is a WIRE FORMAT, not a
    filename; do not "fix" it to match the renamed script.
    """
    raw = _shared.gh(["pr", "view", pr_number, "--json", "comments"], repo_root)
    return sum(
        1 for c in json.loads(raw).get("comments", []) if "pr_review:" in c.get("body", "")
    )


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
                    completion_pattern: str, verbose: bool = False) -> str:
    """Invoke the disposition pass. Delegates to the promoted runner."""
    return _shared.run_claude(
        prompt, model_key=model_key, completion_pattern=completion_pattern,
        repo_root=repo_root, max_turns=MAX_TURNS, verbose=verbose,
    )
