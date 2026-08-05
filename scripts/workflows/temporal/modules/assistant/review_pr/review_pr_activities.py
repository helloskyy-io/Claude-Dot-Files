"""External I/O for review-pr — Layer 3.

Under step 3 these gain `@activity.defn` and nothing else changes.

IDEMPOTENCY (§7.1, and addendum §A1): `run_disposition` is NOT idempotent — the
run it launches posts a comment and may file GitHub Issues. A Temporal retry is
therefore a NEW ATTEMPT, not a replay. Register it with a retry policy that
reflects that; a default policy would silently double-post.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _gh(args: list[str], repo: str | None = None) -> str:
    cmd = ["gh", *args]
    if repo:
        cmd += ["--repo", repo]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def fetch_pr(pr_number: str, repo: str | None = None) -> dict:
    """PR metadata. Raises rather than returning a partial dict."""
    raw = _gh(["pr", "view", pr_number, "--json", "headRefName,state,title"], repo)
    return json.loads(raw)


def count_prior_passes(pr_number: str, repo: str | None = None) -> int:
    """How many disposition comments already exist on this PR.

    Counts comments carrying a `pr_review:` yaml block — the machine-readable
    marker, not prose mentioning the phrase. That key is a WIRE FORMAT and not a
    filename; do not "fix" it to match the renamed script.
    """
    raw = _gh(["pr", "view", pr_number, "--json", "comments"], repo)
    comments = json.loads(raw).get("comments", [])
    return sum(1 for c in comments if "pr_review:" in c.get("body", ""))


def load_prompt(path: Path) -> str:
    """Read a co-located prompt file.

    Separated from the helper because reading a file is I/O — the helper stays
    pure so its tests need no filesystem.
    """
    if not path.exists():
        raise FileNotFoundError(f"prompt file missing: {path}")
    return path.read_text()


def load_shared_block(name: str, shared_sh: Path) -> str:
    """Extract one heredoc block from the legacy `common/shared-prompts.sh`.

    TRANSITIONAL. Addendum §A4 settles that shared prompt fragments promote to a
    parent level per §10.1 rule 3 once a second consumer exists. Until the
    research children port and make that second consumer real, this reads the
    bash original rather than duplicating its text — a copy would drift, and
    drift in a shared block is the failure the promotion rule exists to prevent.
    """
    text = shared_sh.read_text()
    marker = f"{name}=$(cat <<'"
    start = text.find(marker)
    if start == -1:
        raise ValueError(f"shared block {name} not found in {shared_sh}")
    heredoc_tag = text[start + len(marker):text.index("'", start + len(marker))]
    body_start = text.index("\n", start) + 1
    body_end = text.index(f"\n{heredoc_tag}", body_start)
    return text[body_start:body_end]


def run_disposition(prompt: str, worktree: Path, model_key: str,
                    completion_pattern: str, verbose: bool = False) -> str:
    """Invoke the model in the worktree and return its full output.

    Delegates to the existing bash run-claude activity rather than
    reimplementing model invocation, logging and the completion-contract check.
    That is deliberate for the transition: one implementation of the contract,
    not two that can disagree.
    """
    # Resolved from THIS module's location, never from the worktree — the
    # worktree is caller-supplied and may be anywhere, including a repo root
    # whose parents[2] is the user's home directory.
    runner = Path(__file__).resolve().parents[4] / "activities" / "run-claude.sh"
    if not runner.exists():
        raise FileNotFoundError(f"run-claude activity not found: {runner}")
    script = (
        f'source "{runner}"; MODEL_KEY="{model_key}"; '
        f'COMPLETION_PATTERN=\'{completion_pattern}\'; '
        f'VERBOSE={"true" if verbose else "false"}; run_claude "$1"'
    )
    result = subprocess.run(
        ["bash", "-c", script, "_", prompt],
        cwd=str(worktree), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"review-pr run failed (exit {result.returncode}). "
            f"The PR was NOT dispositioned.\n{result.stderr[-2000:]}"
        )
    return result.stdout
