"""Every relative markdown link in the repo points at a file that exists.

WHY THIS EXISTS. PR #89's only blocking finding was a broken `../` count in a
new module, and the reviewer found FOUR MORE already on `main` — eleven in
total once counted properly. Not one had ever been caught, because nothing
checked. A link is exactly the kind of invariant a test owns: mechanical,
binary, and invisible to a human reading the prose around it.

IT WAS ALSO BEING CHECKED BY HAND, REPEATEDLY. The 2026-08-13/14 session
hand-wrote this same scan four separate times — after publishing a synthesis,
after moving it, after a merge resolution, and again during the #89 review.
Four hand-rolls of one predicate is the signal that it belongs in the suite.

WHY THE DEPTH IS THE FAILURE MODE. Every one of the eleven was a `../` run off
by one or two. The path after the `../`s was right in all eleven — nobody
mistyped a filename, they miscounted directories. That is unreadable to a
reviewer and trivial to a machine.

WHAT IS DELIBERATELY NOT CHECKED: external URLs (a network dep in the unit
tier), in-page anchors (`#section`), and anything inside a worktree or cache.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]

# A markdown link whose target is neither a URL nor a bare in-page anchor.
LINK = re.compile(r"\[[^\]]+\]\((?!https?:|mailto:|#|/)([^)\s]+?)(?:#[^)]*)?\)")

SEARCHED = ("*.md", "*.py")

# MATCHED AGAINST THE PATH RELATIVE TO `REPO_ROOT`, NEVER THE ABSOLUTE ONE, and
# that is not a tidiness point — it decided whether this check ran at all.
#
# `rglob` yields ABSOLUTE paths, so `set(p.parts)` carries every segment of the
# prefix above the repo too. An autonomous dispatch works in
# `<repo>/.claude/worktrees/<name>/`, which puts BOTH `.claude` and `worktrees`
# in the prefix of every single file — so the intersection below matched
# everything, `_files()` returned zero, and the check reported nothing to scan.
# It passed from the operator's main checkout and could not run from a worktree,
# which is where EVERY autonomous run works. Measured at `4cf4c55`, same commit
# on both sides: 0 files from the worktree, 241 from the operator's checkout.
#
# The vacuity guard in the test is what surfaced it — the assertion it exists for
# has never once run in a dispatch, and without that guard the suite would have
# reported green over a scan of nothing.
SKIP_PARTS = {".git", "__pycache__", "worktrees", "node_modules", ".claude"}

# SKILLS TEACH BY EXAMPLE, AND THEIR LINKS DESCRIBE A HYPOTHETICAL REPO.
# `config/skills/documentation-structure.md` shows `[Phase doc](../../phases/
# phase-N.md)` — a literal `N` placeholder, in prose rather than a fence, as an
# illustration of what a real doc should contain. Resolving those against THIS
# tree is a category error, and a check that fails forever is a check somebody
# switches off. The trade is stated rather than hidden: a genuinely broken link
# inside a skill is not caught here. Every instance this test was built for
# (eleven, all in `scripts/`) is still covered.
SKIP_DIRS = (REPO_ROOT / "config" / "skills",)

# VENDORED STANDARDS REFERENCE THE UPSTREAM TREE, NOT OURS, AND MUST NOT BE
# EDITED. `docs/standards/{documentation,research,testing,temporal}/` are
# verbatim MIRRORs; their links point at files that exist in MDC-Master-Planning
# and do not exist here. That is correct, not drift — 109 of the 129 links this
# check first flagged were exactly that. Fixing them would be local drift and
# `vendor-standards.sh --check` would fail on it.
VENDORED = {"documentation", "research", "testing", "temporal"}

# `research/raw/` holds papers whose links are CITATION targets — fragments of
# fetched URLs like `/docs/en/hooks`. They were never repo paths.
def _owned(rel: Path) -> bool:
    parts = rel.parts
    if "raw" in parts:
        return False
    if "standards" in parts:
        i = parts.index("standards")
        if len(parts) > i + 1 and parts[i + 1] in VENDORED:
            return False
    # A TEST'S STRING LITERALS ARE FIXTURES, NOT LINKS. `test_measurement_
    # figures_are_cited.py` holds `"see [Phase 5 § Measurement](phase5_...md)"`
    # as a SAMPLE citation it then parses. Resolving it against the test's own
    # directory is meaningless. Module docstrings under `scripts/` are still
    # scanned, and that is where all eleven real breaks lived.
    if rel.name.startswith("test_") and rel.suffix == ".py":
        return False
    return True


def _files() -> list[Path]:
    out: list[Path] = []
    for pattern in SEARCHED:
        for p in REPO_ROOT.rglob(pattern):
            rel = p.relative_to(REPO_ROOT)
            if SKIP_PARTS & set(rel.parts):
                continue
            if any(d in p.parents for d in SKIP_DIRS):
                continue
            if not _owned(rel):
                continue
            out.append(p)
    return sorted(out)


def _outside_fences(text: str) -> str:
    """The document with fenced code blocks blanked out.

    A LINK INSIDE A FENCE IS AN ILLUSTRATION, NOT NAVIGATION. The skill that
    teaches documentation structure shows a phase link with a literal `phase-N.md` placeholder
    as an EXAMPLE, complete with a literal `N` placeholder. Resolving it is a
    category error, and whitelisting the file would hide any real breakage in
    the prose around the example.

    Lines are replaced rather than removed so reported line context stays true.
    """
    out, fenced = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else line)
    return "\n".join(out)


def _broken(path: Path) -> list[tuple[str, str]]:
    bad: list[tuple[str, str]] = []
    for m in LINK.finditer(_outside_fences(path.read_text(errors="replace"))):
        target = m.group(1)
        # A regex or format string can look like a link; only a target that
        # LOOKS like a path is worth resolving. This keeps `[^\]]+](value)`
        # style false positives out without whitelisting files.
        if "/" not in target and not target.endswith(
                (".md", ".py", ".sh", ".txt", ".yaml", ".yml")):
            continue
        if not (path.parent / target).resolve().exists():
            bad.append((target, str(path.relative_to(REPO_ROOT))))
    return bad


def test_every_relative_link_resolves() -> None:
    files = _files()
    assert len(files) > 100, (
        f"only {len(files)} files scanned — the glob or the skip list is wrong, "
        f"and a check that scans nothing passes silently"
    )

    broken = [(t, f) for p in files for t, f in _broken(p)]
    assert not broken, (
        f"{len(broken)} relative link(s) point at a file that does not exist:\n"
        + "\n".join(f"  {f}\n    -> {t}" for t, f in broken)
        + "\n\nEvery instance found so far was a `../` count off by one or two — "
        "the path after the `../`s was correct. Count the directories between the "
        "file and the repo root rather than copying a run from a neighbouring file "
        "at a different depth."
    )
