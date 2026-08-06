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
import sys
import os
from datetime import datetime
from pathlib import Path

_WORKFLOWS = Path(__file__).resolve().parents[3]          # scripts/workflows
_SHARED_PROMPTS = Path(__file__).resolve().parent / "prompts"

PR_URL = re.compile(r"https://github\.com/[^\s)]+/pull/(\d+)")


def v1_constant(script: str, name: str) -> str:
    """Read a constant from the V1 bash script rather than re-declaring it.

    THIS FUNCTION EXISTS BECAUSE RE-DECLARATION CAUSED THREE PRODUCTION FAILURES.
    The V2 port restated V1's constants and contracts instead of deriving from
    them, so divergence was silent and only surfaced at runtime — most expensively
    when a draft ran at MAX_TURNS=120 against V1's 250 and burned a full budget
    producing nothing recoverable. V1's own logs already held the answer: the same
    task class had completed in 130 turns.

    Deriving makes divergence impossible rather than merely detectable. Delete
    this only when the V1 script it reads is deleted.
    """
    path = _WORKFLOWS / "children" / script if "/" not in script else _WORKFLOWS / script
    if not path.exists():
        raise FileNotFoundError(f"V1 script not found for constant derivation: {path}")
    m = re.search(rf"^{name}=(\S+)", path.read_text(), re.M)
    if not m:
        raise ValueError(f"{name} not found in {path} — V1 changed shape; do not guess a value")
    return m.group(1).strip("\"'")


def worktree_add(repo_root: Path, name: str, ref: str) -> Path:
    """Create an isolated worktree, matching V1's behaviour exactly.

    ISOLATION IS AN INVARIANT, NOT A PARAMETER. An earlier V2 skipped the
    worktree on `--pr` runs via a ternary, which put a run directly on the
    operator's main working tree — a live host here. A run dying mid-write would
    leave that tree dirty on a checked-out foreign branch with no discard path.
    V1 always creates one (`git worktree add -f` on the PR branch); so does this.
    """
    wt = repo_root / ".claude" / "worktrees" / name
    subprocess.run(["git", "fetch", "-q", "origin", ref.replace("origin/", "")],
                   cwd=str(repo_root), capture_output=True, text=True)
    r = subprocess.run(["git", "worktree", "add", "-f", str(wt), ref],
                       cwd=str(repo_root), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"worktree add failed for {ref}: {r.stderr.strip()}")
    return wt


def observe_outcome(worktree: Path, branch: str | None = None) -> str:
    """Read what git ACTUALLY did. Never assert a negative without reading.

    THIS EXISTS BECAUSE A FAILURE BANNER LIED. A run that exhausted its turn cap
    printed "NOTHING was committed or pushed" — and it had committed and pushed,
    9 files and +798/-111, landing on the PR branch. The operator read the banner,
    concluded the work was lost, and dispatched a second full-budget run against
    work that was already there.

    The banner asserted what the harness BELIEVED rather than reading what git
    DID, because the turn-cap path exits before observing state. A false negative
    on the failure path is worse than a crash: a crash is obviously wrong, while
    a confident wrong answer gets acted on.

    Returns a human-readable observation. If it cannot determine the state it
    SAYS SO — it never reports a negative it did not verify.
    """
    def _git(*args: str) -> tuple[int, str]:
        r = subprocess.run(["git", *args], cwd=str(worktree),
                           capture_output=True, text=True)
        return r.returncode, r.stdout.strip()

    if not worktree.exists():
        return f"Worktree {worktree} no longer exists — cannot determine what landed."

    lines: list[str] = []
    rc, head = _git("log", "-1", "--format=%h %s")
    if rc != 0:
        return f"Could not read git state in {worktree}. Inspect it by hand before re-running."
    lines.append(f"HEAD in worktree: {head}")

    rc, dirty = _git("status", "--porcelain")
    lines.append(f"Uncommitted changes: {'YES — ' + str(len(dirty.splitlines())) + ' file(s)' if dirty else 'none'}")

    if branch:
        rc, unpushed = _git("log", f"origin/{branch}..HEAD", "--oneline")
        if rc == 0:
            lines.append(
                f"Commits NOT yet on origin/{branch}: {len(unpushed.splitlines()) if unpushed else 0}"
                + (f"\n  {unpushed}" if unpushed else "")
            )
        else:
            lines.append(f"Could not compare against origin/{branch} — do not assume either way.")

    lines.append(f"Worktree retained at: {worktree}")
    return "\n".join(lines)


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
    # SUBSTITUTE TO A FIXED POINT. A prompt fragment can itself contain
    # placeholders — stages_2_to_4.md carries ${PR_NUMBER} — so a single pass
    # leaves them unresolved whenever the block is inserted after its own
    # placeholders were processed. Bash had no such problem: it expanded the
    # whole string at once. Iterate until stable, bounded so a self-referential
    # fragment fails loudly rather than spinning.
    out = template
    for _ in range(10):
        before = out
        for k, v in values.items():
            out = out.replace("${" + k + "}", str(v))
        if out == before:
            break
    else:
        raise ValueError("prompt substitution did not converge — check for a self-referential fragment")
    # [A-Z_0-9] — DIGITS MATTER. An earlier [A-Z_]+ silently missed
    # ${STAGES_1_TO_4}, so a prompt shipped with its entire stage body replaced
    # by a literal placeholder and this check raised nothing. The guard was
    # blind to the one thing it existed to catch.
    leftover = sorted(set(re.findall(r"\$\{[A-Z_][A-Z_0-9]*\}", out)))
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
               repo_root: Path, worktree: Path | None = None,
               max_turns: int = 120, verbose: bool = False) -> str:
    """Invoke the model via the existing bash activity.

    Delegates rather than reimplementing model invocation, logging and the
    completion-contract check — one implementation of the contract, not two
    that can disagree mid-migration.

    TWO LOCATIONS, TWO JOBS. `repo_root` is where LOGS live and MUST be the real
    repository — never a worktree, or the log is deleted with the worktree it sat
    inside and cost accounting for that leg becomes impossible. `worktree` is
    where the model EXECUTES. An earlier version passed the worktree as
    repo_root, which buried every V2 log and reproduced a defect already reported
    against review-pr.

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

    if ".claude/worktrees" in str(repo_root):
        raise ValueError(
            f"repo_root must be the REPOSITORY, not a worktree: {repo_root}. "
            f"Logs written inside a worktree are deleted with it."
        )
    cwd = worktree or repo_root
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
    # STREAM AND CAPTURE. `capture_output=True` produced a 70-minute run with
    # zero visible output, so --verbose did nothing and an operator could not
    # distinguish a working run from a hung one — the reported symptom was
    # "it's not working" when it was. Popen lets output be watched live AND
    # collected for the completion-contract check.
    print(f"→ {model_key}  log: {log_file}", flush=True)
    print(f"→ {model_key}  exec: {cwd}  (max_turns={max_turns})", flush=True)
    proc = subprocess.Popen(
        ["bash", "-c", f'source "{runner}"; run_claude "$1"', "_", prompt],
        cwd=str(cwd), env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    captured: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        captured.append(line)
        if verbose:
            sys.stdout.write(line)
            sys.stdout.flush()
    code = proc.wait()
    output = "".join(captured)

    if code != 0:
        # OBSERVE before reporting. A turn-cap exit may have committed and
        # pushed real work; asserting otherwise costs a duplicate full-budget run.
        raise RuntimeError(
            f"{model_key} FAILED (exit {code}). Log: {log_file}\n"
            f"--- observed git state (read, not assumed) ---\n"
            f"{observe_outcome(cwd)}\n"
            f"--- end observed state ---\n"
            f"{output[-2000:]}"
        )
    return output


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
