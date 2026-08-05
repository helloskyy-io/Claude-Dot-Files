"""Shared I/O for the assistant edge's workflows — promoted per §10.1 rule 3.

Sits at module level because more than one workflow uses it: consumer count
decides, never taste. Anything here is shared BY DEFINITION, so a reader never
opens a file to learn its scope.

NOT IDEMPOTENT (§7.1 / addendum §A1): these push commits and open PRs. Under
Temporal a retry is a NEW ATTEMPT, not a replay — register with a retry policy
that reflects that.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_WORKFLOWS = Path(__file__).resolve().parents[3]          # scripts/workflows
_SHARED_PROMPTS = Path(__file__).resolve().parent / "prompts"

PR_URL = re.compile(r"https://github\.com/[^\s)]+/pull/(\d+)")


def load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"prompt file missing: {path}")
    return path.read_text()


def shared_prompt(name: str) -> str:
    """Load a promoted, module-level prompt fragment by stem."""
    return load_prompt(_SHARED_PROMPTS / f"{name}.md")


def render(template: str, values: dict[str, str]) -> str:
    """Substitute ${NAME} placeholders and fail loud on any left over.

    Deliberately not str.format/f-strings: these prompts carry JSON, yaml and
    shell, all full of literal braces. An unsubstituted placeholder reaches the
    model as an instruction about a variable, so it raises rather than ships.
    """
    out = template
    for k, v in values.items():
        out = out.replace("${" + k + "}", str(v))
    leftover = sorted(set(re.findall(r"\$\{[A-Z_]+\}", out)))
    if leftover:
        raise ValueError(f"unsubstituted prompt placeholders: {leftover}")
    return out


def extract_pr_url(output: str) -> str | None:
    """Last PR URL in a run's output — the completion contract's payload.

    Last, not first: a run may mention an existing PR before opening its own.
    """
    matches = [m.group(0) for m in PR_URL.finditer(output)]
    return matches[-1] if matches else None


def run_claude(prompt: str, *, model_key: str, completion_pattern: str,
               cwd: Path, worktree_name: str | None = None,
               verbose: bool = False) -> str:
    """Invoke the model via the existing bash activity.

    Delegates rather than reimplementing model invocation, logging and the
    completion-contract check — one implementation of the contract, not two
    that can disagree mid-migration.
    """
    runner = _WORKFLOWS / "activities" / "run-claude.sh"
    if not runner.exists():
        raise FileNotFoundError(f"run-claude activity not found: {runner}")

    wt = f' -w "{worktree_name}"' if worktree_name else ""
    script = (
        f'source "{runner}"; MODEL_KEY="{model_key}"; '
        f"COMPLETION_PATTERN='{completion_pattern}'; "
        f'VERBOSE={"true" if verbose else "false"}; run_claude "$1"{wt}'
    )
    result = subprocess.run(["bash", "-c", script, "_", prompt],
                            cwd=str(cwd), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{model_key} FAILED (exit {result.returncode}).\n{result.stderr[-2000:]}"
        )
    return result.stdout


def pr_branch(pr_number: str, repo: str | None = None) -> str:
    cmd = ["gh", "pr", "view", pr_number, "--json", "headRefName", "-q", ".headRefName"]
    if repo:
        cmd += ["--repo", repo]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh pr view {pr_number} failed: {r.stderr.strip()}")
    return r.stdout.strip()
