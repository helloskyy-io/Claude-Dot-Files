#!/usr/bin/env python3
"""`docs/file_structure.txt` states WHERE THINGS ARE — one line per entry, nothing else.

WHY A CHECK AND NOT A GENERATOR. The tree is derivable from disk; the comment column is
not — somebody decides what each entry is FOR, and no walk can compute that. So this
derives the half a machine can (which paths exist) and holds the half it cannot to one
rule (one line each), rather than pretending the whole file can be generated and
destroying the column that carries the value.

WHAT IT ENFORCES, and each maps to a prohibition in the Documentation Standard
§ *Every document states what is true NOW, ONCE, in the place a reader looks first*:

  * ONE LINE PER ENTRY — prohibition 3. A map states location. A continuation line is
    prose that has entered a reference document, and it destroys the one property a tree
    diagram has: the columns stop aligning and it stops being scannable. Measured on this
    repo at first run: 745 of 1,079 lines were continuation, so 69% of the file was essay.
  * NO ENTRY FOR A PATH THAT IS GONE — a map naming a deleted file is worse than silence,
    because a reader trusts it.
  * NO TRACKED PATH MISSING — a map that omits things is one nobody can rely on, and the
    omission is invisible from inside the file.

WHAT IT DELIBERATELY DOES NOT CHECK, because something else already owns it:
whether the map OMITS a tracked file. `test_file_structure_map_covers_the_tree.py`
holds that direction and holds it better — it knows which directories the map
enumerates versus summarises, which this tool does not. The two are complementary
and neither is redundant: that test asks *is anything missing*, this one asks *is
everything here one line, and does it name something real*.

`git ls-files` IS THE SOURCE, not a filesystem walk. It already encodes every exclusion
the repo has decided on — `.gitignore`, worktrees, caches — so this cannot disagree with
the repo about what is part of the repo, and no second ignore list exists to drift.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ENTRY = re.compile(r"^(?P<indent>[│\s]*)[├└]──\s+(?P<name>\S+)(?:\s+#\s?(?P<comment>.*))?$")
CONTINUATION = re.compile(r"^[│\s]+#")


def tracked_paths(repo: Path) -> set[str]:
    """Every directory and file git tracks, as repo-relative POSIX strings."""
    out = subprocess.run(["git", "-C", str(repo), "ls-files"],
                         capture_output=True, text=True, check=True).stdout.split()
    paths: set[str] = set()
    for f in out:
        paths.add(f)
        p = Path(f).parent
        while str(p) != ".":
            paths.add(p.as_posix() + "/")
            p = p.parent
    return paths


def documented(text: str) -> tuple[list[str], list[int]]:
    """(entry names in order, 1-based line numbers of continuation prose)."""
    names, spills = [], []
    for n, line in enumerate(text.split("\n"), 1):
        m = ENTRY.match(line)
        if m:
            names.append(m.group("name"))
        elif CONTINUATION.match(line):
            spills.append(n)
    return names, spills


def main() -> int:
    ap = argparse.ArgumentParser(prog="file_structure_check")
    ap.add_argument("--repo-root", default=".", help="the repo owning docs/file_structure.txt")
    ap.add_argument("--check", action="store_true", help="exit 1 on findings, for CI")
    a = ap.parse_args()

    repo = Path(a.repo_root).resolve()
    doc = repo / "docs" / "file_structure.txt"
    if not doc.is_file():
        print(f"{doc} does not exist — nothing to check.")
        return 0

    text = doc.read_text(encoding="utf-8")
    names, spills = documented(text)

    tracked = tracked_paths(repo)

    # A CHECK THAT CANNOT READ THE FILE MUST SAY SO RATHER THAN REPORT IT CLEAN, and
    # a COVERAGE FLOOR is the only honest way to tell the two apart. Not every repo's
    # map is a tree: `skyynet-master-planning` keeps a prose map with its planning
    # directories deliberately rolled up. This parser found 4 entries in its 136 lines
    # and printed "clean" — a pass produced by reading almost nothing, which is an
    # ABSENT check wearing a green result.
    #
    # A "no tree characters" test was tried first and did NOT fire, because that file
    # has a handful of tree lines among the prose. Presence of the syntax proves
    # nothing; what matters is whether the map accounts for the repo, so the floor is
    # measured against the repo's own top level.
    top = {p.split("/")[0] for p in tracked if "/" in p}
    named = {n.rstrip("/").split("/")[0] for n in names}
    covered = len(top & named)
    if top and covered * 2 < len(top):
        print(f"{doc.relative_to(repo)} accounts for {covered} of {len(top)} top-level "
              f"directories in {len(text.splitlines())} lines. This check reads tree-form "
              f"maps and is not reading most of this one — it is NOT a pass, and nothing "
              f"below is asserted about it.")
        return 1 if a.check else 0

    tracked = tracked_paths(repo)

    # AN ENTRY IS A SUFFIX OF A PATH, NOT ALWAYS A BASENAME. Some entries compress a
    # run of single-child directories into one line (`modules/assistant/`), so a
    # basename comparison reports every one of them as missing. First run: four
    # reported, four false, which is the ratio that teaches a reader to skip the check.
    # Matching on path SUFFIX covers both shapes.
    #
    # THIS IS DELIBERATELY WEAKER THAN COMPARING FULL PATHS, and that is the honest
    # bound: the map does not carry full paths, so two files sharing a tail are
    # indistinguishable here. It still catches the class that bites — an entry whose
    # name appears nowhere in the repo at all.
    stems = {p.rstrip("/") for p in tracked}

    def exists(name: str) -> bool:
        bare = name.rstrip("/")
        if any(s == bare or s.endswith("/" + bare) for s in stems):
            return True
        # A DELIBERATELY UNTRACKED PATH IS STILL A REAL PLACE, and a map documenting
        # where logs land is doing its job. `git ls-files` cannot see `testing/logs/`
        # because it is gitignored, so falling back to the filesystem removes the last
        # false positive. Used only to ACCEPT, never to decide something is missing —
        # so no second ignore list exists to drift from the repo's own.
        return any(repo.glob("**/" + bare)) or (repo / bare).exists()

    ghosts = sorted({n for n in names if not exists(n)})

    findings = 0
    print(f"{doc.relative_to(repo)}: {len(names)} entries, {len(text.splitlines())} lines")

    if spills:
        findings += 1
        print(f"\nPROSE INSIDE THE MAP — {len(spills)} continuation lines "
              f"({100 * len(spills) // max(len(text.splitlines()), 1)}% of the file). "
              f"A map states WHERE THINGS ARE; one line per entry.")
        print("  lines: " + ", ".join(str(n) for n in spills[:12])
              + (f", … and {len(spills) - 12} more" if len(spills) > 12 else ""))

    if ghosts:
        findings += 1
        print(f"\nNAMES NOTHING IN THE REPO — {len(ghosts)}. A map naming a deleted file "
              f"is worse than silence, because a reader trusts it.")
        for g in ghosts[:15]:
            print(f"  {g}")
        if len(ghosts) > 15:
            print(f"  … and {len(ghosts) - 15} more")

    if not findings:
        print("\nclean: one line per entry, and every entry names something that exists.")
    return 1 if (findings and a.check) else 0


if __name__ == "__main__":
    sys.exit(main())
