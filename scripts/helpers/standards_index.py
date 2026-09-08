#!/usr/bin/env python3
"""Audit the standards corpus against the header contract, and say what is unreachable.

UNDERSCORED, UNLIKE ITS HYPHENATED SIBLINGS, and the reason is testability rather than
taste: `scripts/helpers/tests/conftest.py` puts this directory on `sys.path` so a test can
`import` the module, which `similar-candidates.py` cannot be. CI depends on this check, so
its predicates are driven on fixtures rather than trusted — the same split `check_settings.py`
already uses beside `check-settings.sh`.

WHY A CHECK BEFORE A GENERATOR. `documentation_standard.md` § CLAUDE.md Governance
ratified that the index is GENERATED from each standard's header — and the header
contract landed the same day BECAUSE the generator had nothing to generate from.
Measured across both corpora on 2026-09-08: `**Read when:**` existed on ONE standard,
`**Binding scope:**` on 12 of ~50 in MDC and none of 18 here. Building the generator
first would have produced an index of blanks and called it done.

WHAT IT REPORTS, and each is a different remedy:

  * a standard missing one of the three required header lines — the backfill worklist
  * a standard on disk that this repo's `CLAUDE.md` references NOWHERE — unreachable to
    any session routing through the index. Measured in MDC: three real standards, plus
    two retired files nobody deleted, and nothing had noticed either
  * a VENDORED standard missing a header — reported SEPARATELY and never as this repo's
    work. A mirror is a verbatim copy; its header is the owner's to author, and mixing
    the two buckets would hand an operator findings they are forbidden to act on

EXIT CODES: 0 clean, 1 findings, 2 could not run.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

#: The three lines § Standards Corpus Organization requires, spelled exactly.
REQUIRED = ("Binding scope", "Read when", "Breaking it looks like")

#: A header line: `**Label:** value`, at the start of a line.
_FIELD = re.compile(r"^\*\*([^:*]+):\*\*\s*(.*)$", re.M)

#: Everything above the first `##`. The contract says the header block lives there,
#: so a `**Read when:**` written *inside* a section is not a header and is not counted —
#: which is the difference between a parsed contract and a substring search.
_FIRST_SECTION = re.compile(r"^##\s", re.M)

#: Written by `vendor-standards.sh` onto every mirrored copy. Its presence means this
#: repo does not own the file and may not edit it.
_VENDORED = re.compile(r"^<!--\s*VENDORED", re.M)


class Standard(NamedTuple):
    path: Path
    fields: dict[str, str]
    vendored: bool

    @property
    def missing(self) -> list[str]:
        return [r for r in REQUIRED if not self.fields.get(r, "").strip()]


def read_standard(path: Path) -> Standard:
    text = path.read_text(encoding="utf-8", errors="replace")
    cut = _FIRST_SECTION.search(text)
    head = text[: cut.start()] if cut else text
    return Standard(path=path,
                    fields={m.group(1).strip(): m.group(2) for m in _FIELD.finditer(head)},
                    vendored=bool(_VENDORED.search(text)))


def standards_in(root: Path) -> list[Standard]:
    """Every standard under `standards/`, README excluded.

    NO FILTER FOR RETIRED FILES, deliberately. MDC carries two `OLD_*` standards that
    should be deleted rather than indexed; a check that skipped them would report the
    corpus clean while a session could still read them. They surface as missing headers,
    and the remedy — delete — is the operator's to choose, not this script's to assume.
    """
    d = root / "standards"
    if not d.is_dir():
        return []
    return [read_standard(p) for p in sorted(d.rglob("*.md")) if p.name != "README.md"]


def unindexed(root: Path, items: list[Standard]) -> list[Standard]:
    """Standards this repo's `CLAUDE.md` names nowhere.

    Keyed on the FILENAME rather than a link, because an index entry that cites the
    standard by any means at all is reachable — the failure being caught is the one
    where the file is absent from the index entirely.
    """
    index = root / "CLAUDE.md"
    if not index.is_file():
        return []
    text = index.read_text(encoding="utf-8", errors="replace")
    return [s for s in items if s.path.name not in text]


def _default_root() -> tuple[Path | None, tuple]:
    """The repo that owns `standards/`, when the caller did not say.

    CWD FIRST, then the siblings of the repo this script lives in — the same order
    `similar-candidates.py` uses and for the same reason: a repo that owns its own
    corpus answers for itself, and only a repo without one looks sideways. Ambiguity is
    refused rather than guessed; auditing the wrong ecosystem's corpus is worse than
    asking which.
    """
    cwd = Path.cwd()
    if (cwd / "standards").is_dir():
        return cwd, ()
    siblings = sorted(d for d in Path(__file__).resolve().parents[2].parent.iterdir()
                      if d.is_dir() and (d / "standards").is_dir())
    if len(siblings) == 1:
        return siblings[0], ()
    return None, tuple(siblings)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="standards_index",
        description="Audit a standards corpus against the header contract.")
    ap.add_argument("--repo-root", type=Path, default=None,
                    help="the repo owning `standards/` — a FILESYSTEM PATH")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 on findings, for CI; without it this only reports")
    a = ap.parse_args(argv)

    root, ambiguous = (a.repo_root, ()) if a.repo_root else _default_root()
    if root is None:
        print(f"cannot tell which repo owns `standards/` — candidates: "
              f"{[str(c) for c in ambiguous]}. Pass --repo-root.", file=sys.stderr)
        return 2
    items = standards_in(root)
    if not items:
        print(f"no standards under {root}/standards — nothing to audit.", file=sys.stderr)
        return 2

    owned = [s for s in items if not s.vendored]
    mirrors = [s for s in items if s.vendored]
    gaps = [s for s in owned if s.missing]
    stray = unindexed(root, owned)
    mirror_gaps = [s for s in mirrors if s.missing]

    print(f"{root}: {len(items)} standards — {len(owned)} owned, {len(mirrors)} vendored\n")
    if gaps:
        print(f"MISSING HEADER LINES — {len(gaps)} of {len(owned)} owned standards:")
        for s in gaps:
            print(f"  {s.path.relative_to(root)}")
            print(f"      missing: {', '.join(s.missing)}")
        print()
    if stray:
        print(f"NOT REFERENCED BY {root.name}/CLAUDE.md — unreachable to a session "
              f"routing through the index ({len(stray)}):")
        for s in stray:
            print(f"  {s.path.relative_to(root)}")
        print()
    if mirror_gaps:
        print(f"VENDORED, AND THE OWNER'S TO FIX — not this repo's work ({len(mirror_gaps)}):")
        for s in mirror_gaps:
            print(f"  {s.path.relative_to(root)} — missing {', '.join(s.missing)}")
        print()
    if not (gaps or stray):
        print("clean: every owned standard carries the three header lines and is indexed.")
    return 1 if (a.check and (gaps or stray)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
