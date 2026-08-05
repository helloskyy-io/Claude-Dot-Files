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
import os
from datetime import datetime
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
               repo_root: Path, worktree_name: str | None = None,
               max_turns: int = 120, verbose: bool = False) -> str:
    """Invoke the model via the existing bash activity.

    Delegates rather than reimplementing model invocation, logging and the
    completion-contract check — one implementation of the contract, not two
    that can disagree mid-migration.

    CONTRACT ORDER MATTERS. `run-claude.sh` asserts LOG_FILE, MAX_TURNS,
    VERBOSE, FORMATTER and MODEL_KEY with `: "${VAR:?...}"` at SOURCE time, so
    every one must be exported BEFORE the source line. An earlier version
    sourced first and assigned after, which tripped the guard at source time and
    exited 127 — the delegation did not satisfy the contract it delegated to.
    """
    runner = _WORKFLOWS / "activities" / "run-claude.sh"
    formatter = _WORKFLOWS / "common" / "format-stream.sh"
    for required in (runner, formatter):
        if not required.exists():
            raise FileNotFoundError(f"required activity not found: {required}")

    log_dir = repo_root / ".claude" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"{model_key}-{stamp}.jsonl"

    env = {
        **os.environ,
        "LOG_FILE": str(log_file),
        "MAX_TURNS": str(max_turns),
        "VERBOSE": "true" if verbose else "false",
        "FORMATTER": str(formatter),
        "MODEL_KEY": model_key,
        "COMPLETION_PATTERN": completion_pattern,
    }
    wt = f' -w "{worktree_name}"' if worktree_name else ""
    result = subprocess.run(
        ["bash", "-c", f'source "{runner}"; run_claude "$1"{wt}', "_", prompt],
        cwd=str(repo_root), env=env, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{model_key} FAILED (exit {result.returncode}). Log: {log_file}\n"
            f"{result.stderr[-2000:]}"
        )
    return result.stdout


def gh(args: list[str], repo_root: Path) -> str:
    """Run `gh` INSIDE the target repo rather than passing --repo.

    `--repo` in our CLIs is a FILESYSTEM PATH; `gh --repo` wants an OWNER/NAME
    slug. Conflating them is how an earlier version passed None to gh and let it
    derive the repo from the process cwd — which is exactly what the flag's own
    documentation promises never happens. Setting cwd keeps the identity
    explicit without needing to parse a remote URL into a slug.
    """
    r = subprocess.run(["gh", *args], cwd=str(repo_root),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed in {repo_root}: {r.stderr.strip()}")
    return r.stdout


def pr_branch(pr_number: str, repo_root: Path) -> str:
    return gh(["pr", "view", pr_number, "--json", "headRefName",
               "-q", ".headRefName"], repo_root).strip()
