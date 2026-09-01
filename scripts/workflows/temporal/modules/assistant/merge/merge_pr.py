"""Land a reviewed PR set, and drain the intake. TWO INDEPENDENT OPERATIONS.

WHY AN ACTIVITY AND NOT A CHILD. Walk the job and ask what needs judgement:
which PRs form the set (derivable from the run's output URLs), is CI green
(`ci_verdict`), did the reviewer say MERGE (it is in the durable block on the
thread), what order to merge in (a rule, written below), drain (`harvest`).
**Nothing is left to judge, so nothing needs a model** — and `plan-candidates`
records what it costs to get this wrong: the same job built as a model child was
*"1,605 lines, a 173-line prompt, and eight review holds every one of which was a
consequence of it being"* a child. It is also what the Architecture Standard
requires: *"Activity — External I/O, workflow-agnostic and idempotent. **A parent
may not inline any of it**."*

THE DRAIN AND THE MERGE ARE NOT ONE TRANSACTION, and modelling them as one is a
defect this module exists having already avoided. An intake is an ALREADY-RULED
finding — `review-pr` ruled it when it filed it — and the drain is GLOBAL, so it
carries intakes from other PRs including ones that will never merge. There is no
shared invariant, so there is no saga: coupling them would let a `gh` hiccup in an
unrelated queue block a reviewed, green PR from landing. `run_merge` therefore
reports both outcomes and lets NEITHER block the other.

ORDER MATTERS IN EXACTLY ONE PLACE — inside the PR set — and the asymmetry is
what decides it:

  * code merged, record not  -> an open PR. Visible, and the next run closes it.
  * record merged, code not  -> the planning repo asserts work that is not in.
    Silent, and false.

So the code PR lands first and the record PR second: **fail toward the state a
human can see.**

IDEMPOTENT THROUGHOUT, WHICH IS THE REAL ANSWER TO PARTIAL FAILURE. Merging a
merged PR is a no-op; `intake.harvest` survives a partial drain through
`_already_filed`. The remedy for any half-finished run is to run it again, which
is retry-to-convergence rather than ordering gymnastics.

INVOCATION IS THE APPROVAL, so there is no confirmation flag. Every auto-merge
system in the industry — Bors, Mergify, Prow/tide, `gh pr merge --auto` — merges
on green **plus a human approval**: they automate WHEN, never WHETHER. An operator
running this against a named PR IS that approval. A `--yes` prompt on top would be
theatre, because nobody re-reads the diff at the prompt.

WHAT MAKES IT SAFE IS THE PRECONDITIONS, and they are the whole of the safety.
Branch protection is rejected permanently on this account (a paid feature,
`cpi-decisions.md` 2026-08-16), and `tests.yml` runs on `pull_request` but nothing
ENFORCES it — so a red PR can be merged by hand today. Checking CI here is
literally required-status-checks, implemented where we can have it.

**A SIGNAL THAT CANNOT BE READ IS A REFUSAL, NEVER AN ALL-CLEAR.** Every
unreadable state below returns a refusal reason. The failure direction is "did not
merge", which costs one re-run; the other direction costs a merge nobody cleared.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .. import routing
from ..assistant_activities import ci_verdict
from ..review_pr import review_pr_activities as review_act
from ..review_pr import review_pr_helper as review_helper
from ..tracked import intake, tracked_items as ti


@dataclass(frozen=True)
class MergeReport:
    """What one invocation did. Both halves, independently."""

    merged: tuple[str, ...] = ()
    refused: tuple[tuple[str, str], ...] = ()      # (pr, why)
    drained: tuple[int, ...] = ()                  # intake issue numbers
    drain_error: str | None = None

    @property
    def ok(self) -> bool:
        return not self.refused and self.drain_error is None


def _gh_json(args: list[str], repo_root: Path) -> dict | None:
    """A `gh` read, or None when it could not be read. None is never 'fine'."""
    try:
        out = subprocess.run(["gh", *args], cwd=repo_root, capture_output=True,
                             text=True, check=True, timeout=120).stdout
        parsed = json.loads(out)
        return parsed if isinstance(parsed, dict) else None
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
        return None


def thread_verdict(pr: str, repo_root: Path) -> str | None:
    """The LATEST `pr_review:` block's verdict. None means it could not be read.

    LATEST, NOT THE UNION — the same rule `unclosed_hold` follows and for the
    same reason: every pass restates the finding set, so a PR held on pass 1 and
    cleared on pass 2 must read as cleared. Reading the union would refuse every
    PR that was ever held, permanently.
    """
    try:
        blocks = review_act.pr_review_blocks(pr, repo_root)
    except Exception:
        return None
    latest = review_helper.latest_pass_block(blocks)
    if latest is None:
        return None
    m = review_helper.BLOCK_VERDICT.search(latest)
    return m.group(1) if m else None


def refusals(pr: str, repo_root: Path) -> list[str]:
    """Every reason this PR may not merge. Empty means clear.

    ALL OF THEM, NOT THE FIRST — an operator fixing one blocker and rediscovering
    the next on the following run pays a round trip per reason.
    """
    why: list[str] = []

    verdict = thread_verdict(pr, repo_root)
    if verdict is None:
        why.append("no readable `pr_review:` verdict on the thread — this PR has "
                   "not been disposed, or the thread could not be read")
    elif verdict != routing.Verdict.MERGE.value:
        why.append(f"the latest review pass returned `{verdict}`, not MERGE")

    state, extra = ci_verdict(pr, repo_root=repo_root)
    if state is not routing.CiVerdict.GREEN:
        detail = f" ({', '.join(extra)})" if extra else ""
        why.append(f"CI is `{state.value}`, not green{detail} — this check IS the "
                   f"required-status-check this account cannot buy")

    view = _gh_json(["pr", "view", pr, "--json", "state,mergeStateStatus"], repo_root)
    if view is None:
        why.append("`gh pr view` could not be read, so mergeability is unknown")
    elif view.get("state") != "OPEN":
        why.append(f"the PR is `{view.get('state')}`, not OPEN")
    elif view.get("mergeStateStatus") != "CLEAN":
        why.append(f"mergeStateStatus is `{view.get('mergeStateStatus')}`, not CLEAN "
                   f"— GitHub has not cleared this to merge")
    return why


def merge_one(pr: str, repo_root: Path, *, dry_run: bool = False) -> str | None:
    """Squash-merge one PR and delete its branch. Returns an error, or None.

    SQUASH, matching every merge on this repo since #20, so `main` stays linear.
    """
    if dry_run:
        return None
    try:
        subprocess.run(["gh", "pr", "merge", pr, "--squash", "--delete-branch"],
                       cwd=repo_root, capture_output=True, text=True,
                       check=True, timeout=300)
        return None
    except subprocess.CalledProcessError as exc:
        return (exc.stderr or exc.stdout or "gh pr merge failed").strip()
    except (subprocess.SubprocessError, OSError) as exc:
        return str(exc)


def run_merge(prs: list[str], repo_root: Path, *, stores_root: Path | None = None,
              issues_repo: Path | None = None, dry_run: bool = False) -> MergeReport:
    """Land `prs` in the order given, and drain the intake. Neither blocks the other.

    `prs` IS ORDERED BY THE CALLER and the order is load-bearing: the code PR
    first, the record PR second (see the module docstring). This function does not
    reorder, because it cannot tell which is which — the caller knows.

    A REFUSAL STOPS THE SET, NOT JUST ITS OWN MEMBER. If the code PR will not
    merge, merging the record PR alone produces exactly the silent-and-false state
    the ordering exists to avoid. Later members are reported as refused with the
    reason naming the member that stopped it, so the report says what happened
    rather than going quiet.

    THE DRAIN RUNS REGARDLESS, INCLUDING AFTER A REFUSAL. Intakes are already-ruled
    findings with no dependence on this PR; withholding them because an unrelated
    merge failed would be the coupling this module refuses.
    """
    merged: list[str] = []
    refused: list[tuple[str, str]] = []

    for pr in prs:
        if refused:
            refused.append((pr, f"not attempted: `{refused[0][0]}` earlier in the "
                                f"set did not merge, and landing a record without "
                                f"its code asserts work that is not in"))
            continue
        why = refusals(pr, repo_root)
        if why:
            refused.append((pr, "; ".join(why)))
            continue
        err = merge_one(pr, repo_root, dry_run=dry_run)
        if err:
            refused.append((pr, f"merge failed: {err}"))
        else:
            merged.append(pr)

    drained: list[int] = []
    drain_error: str | None = None
    if stores_root is not None:
        root = (stores_root / ti.TRACKED_ROOT).resolve()
        if not root.is_dir():
            drain_error = (f"no tracked store at {root} — expected the four stores "
                           f"of Tracked Items Standard §1. Nothing harvested.")
        else:
            try:
                moved, failed = intake.harvest(
                    root, cwd=issues_repo or repo_root, dry_run=dry_run)
                drained = [n for n, _ in moved]
                if failed:
                    drain_error = ("; ".join(f"#{n}: {why}" for n, why in failed)
                                   + " — left OPEN deliberately; a malformed intake "
                                     "is a finding, and closing it would lose it")
            except Exception as exc:                       # noqa: BLE001
                drain_error = f"{type(exc).__name__}: {exc}"

    return MergeReport(merged=tuple(merged), refused=tuple(refused),
                       drained=tuple(drained), drain_error=drain_error)
