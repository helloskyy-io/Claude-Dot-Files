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
#: `[ \t]*` AND NOT `\s*`, because `\s` matches a newline. A field whose value is
#: empty or continues on the following lines — a list, a table, a wrapped paragraph —
#: let `\s*` eat the newline, `(.*)$` then captured THE WHOLE NEXT FIELD LINE as this
#: field's value, and `finditer` resumed past it so the swallowed field was never seen.
#: The audit then reports a field missing from a file that HAS it, which inverts the
#: tool's purpose: the operator's remedy is to write a field they already wrote.
#: Found by MDC-PM3 on `stateful_patterns.md` (a `**Companion to:**` above `**Read
#: when:**`), after a cycle spent proving the content was present — a tool reporting a
#: missing field is not a shape you distrust first. It bites hardest where headers are
#: richest, and a standard carrying `Companion to:` / `Pairs with:` / `Supersedes:` is
#: the hub the index most needs to render correctly.
_FIELD = re.compile(r"^\*\*([^:*]+):\*\*[ \t]*(.*)$", re.M)

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


#: Friendlier headings for the buckets that have one; the order they read best in.
#: A bucket absent from either map still renders — titled from its own folder name and
#: sorted last, so a new topic folder appears in the index the day it is created rather
#: than the day somebody remembers to add it here.
_BUCKET_TITLES = {
    "architecture": "Architecture (read first for any design work)",
    "claude-code": "Tooling standards (the claude-dot-files corpus)",
    "documentation": "Documentation and process",
    "findings": "Findings and routing",
}
_BUCKET_ORDER = {"architecture": 0, "claude-code": 1, "workflows": 2, "services": 3,
                 "documentation": 4, "findings": 5, "research": 6, "testing": 7,
                 "temporal": 8}


def _standards_dir(root: Path) -> Path:
    """Where this repo keeps its standards, DERIVED FROM REPO CLASS.

    Same rule as `vendor-standards.sh` and the plan deriver's `development_root`,
    and here for the same reason: a planning repo's root IS its documentation
    tree, so it hoists the buckets; every other repo keeps them under `docs/`.
    See the Documentation Standard § *A repo that CONSUMES standards*, rule 1.

    ⚠ THIS TOOL LOOKED AT `<root>/standards` UNCONDITIONALLY, which is the THIRD
    instance of one bug. Pointed at a non-planning repo it found nothing and
    exited 2 — "no standards, nothing to audit" — which is a loud refusal for the
    wrong reason: the corpus was there, in the place the standard says it lives,
    and the tool looked somewhere else. The refusal is what stopped this being a
    silent pass, and it is why the same defect in the plan deriver scored a repo
    PERFECT while reading no files.
    """
    if root.name.endswith("-master-planning"):
        return root / "standards"
    docs = root / "docs" / "standards"
    return docs if docs.is_dir() else root / "standards"


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
    d = _standards_dir(root)
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


#: The generated block's fence. Everything between these two lines is rendered from
#: the headers and is replaced wholesale; everything outside is hand-written and is
#: never touched. Committed rather than built at read time, per Repository Layout §1.1 —
#: a viewer over the repo's own corpus, with staleness gated by `--check`.
BEGIN = "<!-- BEGIN GENERATED STANDARDS INDEX — edit the standards' headers, not this -->"
END = "<!-- END GENERATED STANDARDS INDEX -->"


def _title(path: Path) -> str:
    """The standard's own `# ` heading, which is what a reader will see when they land."""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ").title()


def render_index(items: list[Standard], root: Path) -> str:
    """One line per standard, from its three header lines and nothing else.

    THE ENTRY CANNOT CARRY A SECTION SUMMARY, and that is the point rather than a
    limitation. MDC's hand-written entries are 1,403 bytes at the median because most
    of each is a §-by-§ précis of the standard — neither a trigger nor a symptom, and the
    part that goes stale: the measured drift instance was a summary of a §2.3 model the
    standard had moved past. There is no header field to render one from, so generation
    deletes the class. Measured against real headers: 454 bytes per entry.

    ⚠ THAT IS A SAVING FOR MDC AND A COST FOR US, and the second half was missing until
    2026-09-08. SkyyNet's own entries are 270 bytes at the median — already terse — so
    generating this corpus makes its index BIGGER (6,056 -> ~9,400). The trade is
    different in each repo and the reason to generate here is drift, not size. Stated
    because the 68%-reduction figure was quoted at another PM as though it were a
    property of the tool.

    GROUPED BY BUCKET, because a flat list was deleting structure that is DERIVABLE.
    The hand-written index sorted its entries under `### Architecture`, `### Tooling`
    and so on — and every one of those headings is just the standard's own folder
    under `standards/`. A generator that flattened them would have forced a choice
    between derived and navigable, which is a false choice: the grouping is in the
    corpus already. `_BUCKET_TITLES` names the ones worth a friendlier heading; any
    other folder titles itself.
    """
    out = [BEGIN, ""]
    grouped: dict[str, list[Standard]] = {}
    for s in sorted(items, key=lambda x: x.path.as_posix()):
        rel = (root / s.path).resolve().relative_to(_standards_dir(root).resolve())
        grouped.setdefault(rel.parts[0] if len(rel.parts) > 1 else "", []).append(s)
    for bucket in sorted(grouped, key=lambda b: (_BUCKET_ORDER.get(b, 99), b)):
        if bucket:
            out += [f"### {_BUCKET_TITLES.get(bucket, bucket.replace('-', ' ').title())}", ""]
        for s in grouped[bucket]:
            out.append(f"- **[{_title(s.path)}]({(root / s.path).resolve()})** — "
                       f"**read when** {s.fields['Read when'].strip()} "
                       f"*Breaking it looks like:* {s.fields['Breaking it looks like'].strip()}")
        out.append("")
    out += [END]
    return "\n".join(out)


def splice(index_text: str, block: str) -> str | None:
    """Replace the fenced block, or None if the fence is absent.

    ABSENT IS NOT EMPTY. A CLAUDE.md with no fence has a hand-written index that this
    would otherwise silently replace with a shorter one — destroying the § summaries
    nobody has moved yet. The caller refuses; it does not guess where the block goes.
    """
    if BEGIN not in index_text or END not in index_text:
        return None
    head = index_text[: index_text.index(BEGIN)]
    tail = index_text[index_text.index(END) + len(END):]
    return head + block + tail


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


def stale_block(root: Path, items: list[Standard]) -> str | None:
    """The committed block versus what the headers render now, or None if in step.

    THE ARTIFACT IS COMMITTED, SO IT CAN GO STALE — that is the trade Repository Layout
    §1.1 makes for a viewer that costs nothing to read. The staleness gate is what makes
    the trade safe, and without it a generated index is exactly the hand-maintained one
    it replaced, with an extra step.

    Silent when the corpus is incomplete: the missing headers are already the finding,
    and reporting a block as stale when it cannot yet be rendered is noise on top of it.
    """
    index = root / "CLAUDE.md"
    if not index.is_file() or any(s.missing for s in items if not s.vendored):
        return None
    text = index.read_text(encoding="utf-8", errors="replace")
    if BEGIN not in text or END not in text:
        return None
    committed = text[text.index(BEGIN): text.index(END) + len(END)]
    fresh = render_index([s for s in items if not s.missing], root)
    return None if committed.strip() == fresh.strip() else (
        f"the committed index block is {len(committed.encode()):,} bytes and the headers "
        f"now render {len(fresh.encode()):,} — regenerate with --write")


def _emit(a, root: Path, items: list[Standard], owned: list[Standard],
          gaps: list[Standard]) -> int:
    """Render, and write only onto a corpus that can be rendered completely."""
    if gaps:
        print(f"REFUSING: {len(gaps)} of {len(owned)} owned standards are missing header "
              f"lines, so a generated index would be shorter than the hand-written one it "
              f"replaces — and the difference is work nobody has moved yet. Run without "
              f"--generate to see the list, backfill the headers, then generate.",
              file=sys.stderr)
        return 2
    block = render_index([s for s in items if not s.missing], root)
    if not a.write:
        print(block)
        return 0
    index = root / "CLAUDE.md"
    if not index.is_file():
        print(f"no {index} to write into.", file=sys.stderr)
        return 2
    spliced = splice(index.read_text(encoding="utf-8"), block)
    if spliced is None:
        print(f"{index} carries no generated-block fence. Add these two lines around the "
              f"standards list, keeping the list between them, then re-run:\n"
              f"  {BEGIN}\n  {END}\n"
              f"Refusing to guess where the block belongs — the text already there is "
              f"hand-written and is not this tool's to relocate.", file=sys.stderr)
        return 2
    index.write_text(spliced, encoding="utf-8")
    print(f"wrote {len(block.encode()):,} bytes of generated index into {index}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="standards_index",
        description="Audit a standards corpus against the header contract.")
    ap.add_argument("--repo-root", type=Path, default=None,
                    help="the repo owning `standards/` — a FILESYSTEM PATH")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 on findings, for CI; without it this only reports")
    ap.add_argument("--generate", action="store_true",
                    help="render the index block from the headers and print it")
    ap.add_argument("--write", action="store_true",
                    help="splice the rendered block into the repo's CLAUDE.md, between "
                         "its fence markers. REFUSES while any owned standard is "
                         "incomplete — a partial index would replace a complete "
                         "hand-written one and delete work nobody has moved yet.")
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

    if a.generate or a.write:
        return _emit(a, root, items, owned, gaps)

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
    drift = stale_block(root, items)
    if drift:
        print(f"INDEX BLOCK IS STALE — {drift}\n")
    if mirror_gaps:
        print(f"VENDORED, AND THE OWNER'S TO FIX — not this repo's work ({len(mirror_gaps)}):")
        for s in mirror_gaps:
            print(f"  {s.path.relative_to(root)} — missing {', '.join(s.missing)}")
        print()
    # `drift` BELONGS IN THIS CONDITION, and leaving it out printed the opposite of
    # the truth: a stale index reported "clean" on the last line of a run that exited
    # 1, and the last line is what a reader takes away. Observed 2026-09-08 driving
    # the staleness gate with a mutation — the gate was right and its summary was not.
    if not (gaps or stray or drift):
        print("clean: every owned standard carries the three header lines and is indexed.")
    return 1 if (a.check and (gaps or stray or drift)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
