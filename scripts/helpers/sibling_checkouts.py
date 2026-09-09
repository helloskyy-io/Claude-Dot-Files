#!/usr/bin/env python3
"""Work a dispatch left in a repo it was not pointed at — the class nobody was watching.

A dispatch is given ONE repo with `--repo` and every instrument it has watches that
one: the diff, the PR, the CI gate, the review. **A run that changes code in one repo
and planning docs in a sibling leaves the second half invisible to all of them.** It is
not on a branch anyone opened, not in a PR anyone reviews, and not in a diff anyone
reads — it is a commit sitting on a local branch in a checkout nobody looked at.

MEASURED THE DAY THIS LANDED: `mdc-master-planning` was parked on a local branch with
TEN unpushed commits, and nothing in the fleet would have said so. The reporting run
lost a planning commit this way — recovered late as a separate PR — and the phase
checkboxes it carried silently never landed.

THIS IS A REPORT, NEVER A WRITE. It runs `git` read-only in every sibling and prints
what it finds. It does not commit, push, checkout or clean anything: the whole point is
that these checkouts belong to other people's work, and a tool that tidied them would
destroy exactly the thing it exists to surface.

WHY A SIBLING SWEEP RATHER THAN A HOOK IN THE WRITER. The write that strands the work
looks completely normal from inside the run that makes it — it is a correct commit in a
correct repo. Nothing at the moment of writing distinguishes it from work that will be
pushed. The signal only exists afterwards, from outside, by looking at every checkout
at once.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def default_branch(repo: Path) -> str:
    """The remote's own idea of its default, falling back to `main`.

    ASKED OF THE REMOTE RATHER THAN ASSUMED, because a repo whose default is `master`
    would otherwise be reported as permanently off-branch — a false positive on every
    run, which is how a sweep stops being read.
    """
    head = _git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    return head.split("/", 1)[1] if "/" in head else (head or "main")


def survey(root: Path) -> list[dict]:
    out = []
    for d in sorted(root.iterdir()):
        if not (d / ".git").exists():
            continue
        branch = _git(d, "rev-parse", "--abbrev-ref", "HEAD")
        base = default_branch(d)
        ahead = _git(d, "log", "--oneline", f"origin/{base}..HEAD")
        dirty = _git(d, "status", "--porcelain")
        out.append({
            "repo": d.name,
            "branch": branch,
            "base": base,
            "off_default": bool(branch) and branch != base,
            "unpushed": len([x for x in ahead.split("\n") if x]),
            "uncommitted": len([x for x in dirty.split("\n") if x]),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(prog="sibling_checkouts")
    ap.add_argument("--root", default="/opt/skyy-net",
                    help="the directory holding the sibling checkouts")
    ap.add_argument("--exclude", default="",
                    help="comma-separated repo names to skip — the one this dispatch owns")
    ap.add_argument("--check", action="store_true", help="exit 1 on findings, for a dispatch")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    if not root.is_dir():
        print(f"{root} is not a directory — nothing to survey.")
        return 0
    skip = {s.strip() for s in a.exclude.split(",") if s.strip()}
    rows = [r for r in survey(root) if r["repo"] not in skip]
    if not rows:
        print(f"{root} holds no git checkouts{' outside the excluded set' if skip else ''} "
              f"— this sweep read nothing and asserts nothing.")
        return 1 if a.check else 0

    flagged = [r for r in rows if r["off_default"] or r["unpushed"] or r["uncommitted"]]
    print(f"{len(rows)} checkouts under {root}"
          + (f", excluding {', '.join(sorted(skip))}" if skip else ""))
    if not flagged:
        print("clean: every checkout is on its default branch with nothing unpushed "
              "or uncommitted.")
        return 0

    print(f"\nWORK OUTSIDE THIS DISPATCH'S REPO — {len(flagged)}. Each is invisible to "
          f"the diff, the PR and the CI gate:")
    for r in flagged:
        bits = []
        if r["off_default"]:
            bits.append(f"on `{r['branch']}`, not `{r['base']}`")
        if r["unpushed"]:
            bits.append(f"{r['unpushed']} unpushed commit(s)")
        if r["uncommitted"]:
            bits.append(f"{r['uncommitted']} uncommitted file(s)")
        print(f"  {r['repo']}: " + "; ".join(bits))
    print("\nThis is a REPORT. Decide per repo whether the work should be pushed, "
          "opened as a PR, or is somebody else's in progress — and do not assume it "
          "is yours because your dispatch ran nearby.")
    return 1 if a.check else 0


if __name__ == "__main__":
    sys.exit(main())
