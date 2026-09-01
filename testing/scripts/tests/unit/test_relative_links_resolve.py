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

from vendored_standards import EXPECTED, VENDOR_SCRIPT, vendored_paths

REPO_ROOT = Path(__file__).resolve().parents[4]

import sys as _s  # noqa: E402
_s.path.insert(0, str(REPO_ROOT / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import PLANNING_ROOT  # noqa: E402

# TWO ROOTS, ONE GATE. The prose moved to the planning repo while the tooling it
# documents stayed here, so a link now breaks in either tree and the check that
# used to see both halves must keep seeing both. Scanning only this repo after
# the split would have left the ENTIRE doc corpus unguarded while still
# reporting green — the exact silent-pass shape the vacuity floors below exist
# to catch, arriving by a route no floor was watching.
ROOTS = (REPO_ROOT, PLANNING_ROOT)


def _rel(p: Path) -> Path:
    """The path relative to whichever root owns it."""
    for root in ROOTS:
        try:
            return p.relative_to(root)
        except ValueError:
            continue
    return p

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
# EDITED. Their links point at files that exist in MDC-Master-Planning and do
# not exist here. That is correct, not drift — 109 of the 129 links this check
# first flagged were exactly that. Fixing them would be local drift and
# `vendor-standards.sh --check` would fail on it.
#
# IT IS SEVEN FILES, NOT FOUR DIRECTORIES. This exemption was spelled
# `{"documentation", "research", "testing", "temporal"}` and matched on the
# DIRECTORY, which exempted 11 files where 6 are vendored. The other five —
# the four `README.md` applicability notes and `temporal/claude-dot-files-
# addendum.md` — are LOCAL, editable here, and say so of themselves; their
# links were silently unchecked. Measured when this was narrowed: all five
# already resolve, so the widening costs nothing and closes the hole.
#
# `test_markdown_tables_render_whole.py` records the same over-broad claim
# being made and corrected in its own docstring. The set is read off the
# script that DECLARES it rather than restated, because a hand-kept copy in a
# second module is exactly the stale declaration these gates exist to catch.
# The set is DERIVED, not listed, and it lives in `vendored_standards.py`
# because two gates need the same answer. See that module for why it is six
# files rather than four directory names, and what the four-directory spelling
# this exemption used to carry silently got wrong.

# `research/raw/` holds papers whose links are CITATION targets — fragments of
# fetched URLs like `/docs/en/hooks`. They were never repo paths.
def _owned(rel: Path) -> bool:
    parts = rel.parts
    if "raw" in parts:
        return False
    if any((root / rel).resolve() in vendored_paths() for root in ROOTS):
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
    for root in ROOTS:
        for pattern in SEARCHED:
            for p in root.rglob(pattern):
                rel = p.relative_to(root)
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
            bad.append((target, str(_rel(path))))
    return bad


def test_the_VENDORED_EXEMPTION_names_the_SEVEN_FILES_the_script_declares() -> None:
    """Vacuity guard on the exemption above, which is derived rather than listed.

    If the derivation stopped matching, `vendored_paths()` would be empty and this gate would
    start flagging the six mirrors' upstream-relative links — 109 of them —
    sending a contributor to "fix" files that must not be edited here. If it
    over-matched, local files would go unchecked, which is the hole this
    exemption was narrowed to close.
    """
    names = sorted(p.name for p in vendored_paths())
    assert names == sorted(EXPECTED), (
        f"the vendored set derived from {VENDOR_SCRIPT.name} is {names}. Either "
        f"it genuinely changed — update this assertion and the comment above — "
        f"or the parse broke, in which case this gate's exemption is wrong in "
        f"one of the two directions the comment describes.")

    missing = sorted(str(_rel(p)) for p in vendored_paths()
                     if not p.is_file())
    assert not missing, (
        f"the script declares vendored files not in the tree: {missing}. The "
        f"exemption matches on resolved paths, so a wrong path means a mirror "
        f"is checked as if it were local.")


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


# A link that names BOTH a file and a heading inside it. The check above proves
# the file exists; this one proves the heading does.
ANCHORED = re.compile(r"\[[^\]]+\]\((?!https?:|mailto:|#|/)([^)\s#]+\.md)#([a-z0-9][a-z0-9-]*)\)")

# GitHub's slug: lowercase, punctuation dropped, spaces to hyphens. Approximate
# on purpose — it is applied to BOTH sides, so a heading this gets wrong is
# still matched by a link written from the same heading.
_SLUG_STRIP = re.compile(r"[^a-z0-9 -]")


def _slugs(md: Path) -> set[str]:
    out = set()
    for h in re.findall(r"^#{1,6}\s+(.*?)\s*$", md.read_text(errors="replace"), re.M):
        out.add(_SLUG_STRIP.sub("", h.lower()).strip().replace(" ", "-"))
    return out


def test_every_link_ANCHOR_resolves() -> None:
    """A link naming a heading must name one that exists.

    WHY THIS IS SEPARATE FROM THE FILE CHECK ABOVE. That one deliberately
    DISCARDS the fragment — `LINK`'s trailing group is non-capturing — so a link
    to the right file and a dead heading has always passed. Measured when this
    landed: **six** such links, on a suite that was green.

    THE COST IS PAID AT EXACTLY THE WRONG MOMENT. A build that renames or deletes
    headings is the one most likely to break these, and it is also the one whose
    author is least able to notice — the run that surfaced this deleted and
    created about six headings other files point at, found the breakage only by
    writing a throwaway checker, and said so.

    APPROXIMATE SLUGGING IS FINE HERE AND WOULD NOT BE IN A RENDERER. The same
    transform is applied to the heading and to the link, so a heading this gets
    wrong still matches a link written from it. What it catches is a heading that
    is GONE, which is the failure that actually happens.
    """
    files = [f for f in _files() if f.suffix == ".md"]
    assert len(files) > 50, f"only {len(files)} markdown files scanned"

    broken = []
    for f in files:
        for m in ANCHORED.finditer(f.read_text(errors="replace")):
            target = (f.parent / m.group(1)).resolve()
            if not target.is_file():
                continue          # the file check above owns this case
            if m.group(2) not in _slugs(target):
                broken.append((_rel(f), m.group(1), m.group(2)))

    assert not broken, (
        f"{len(broken)} link(s) name a heading that does not exist:\n"
        + "\n".join(f"  {f}\n    -> {t}#{a}" for f, t, a in broken)
        + "\n\nThe file resolves; the heading does not. Either the heading was "
        "renamed or deleted, or the anchor was written from a heading that never "
        "existed. Check the target's headings rather than adjusting the slug."
    )
