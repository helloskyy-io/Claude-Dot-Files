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
import urllib.parse
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

#: The line after a field that is prose continuing it: not blank, not another
#: field, not a heading, fence, blockquote or list marker.
_CONTINUATION = re.compile(r"^(?![ \t]*$)(?!\*\*[^:*]+:\*\*)(?![#>`\-*|])(?![ \t]*[-*] )")

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
    #: Required fields whose value runs onto the following line(s).
    wrapped: tuple[str, ...] = ()

    @property
    def missing(self) -> list[str]:
        """What keeps this standard out of the index: a field absent, or WRAPPED.

        A WRAPPED FIELD IS A DEFECT, NOT A STYLE. The contract says three header
        LINES, and the parser reads one line per field on purpose (see `_FIELD`).
        A value continued onto the next line renders as its first line only —
        MDC's index carried "*adding a step to an* Breaking it looks like: *a
        component that exists on a running system and in no*" in the entry every
        session reads first (MDC-PM3, 2026-09-14). Refusing is cheaper than
        teaching the parser continuation, which would reopen the swallowing
        `_FIELD` was narrowed to stop.
        """
        out = [r for r in REQUIRED if not self.fields.get(r, "").strip()]
        out += [f"{r} (wrapped onto a second line — a field is ONE line)"
                for r in REQUIRED if r in self.wrapped]
        return out


#: Friendlier headings for the buckets that have one; the order they read best in.
#: A bucket absent from either map still renders — titled from its own folder name and
#: sorted last, so a new topic folder appears in the index the day it is created rather
#: than the day somebody remembers to add it here.
_BUCKET_TITLES = {
    "architecture": "Architecture (read first for any design work)",
    "claude-code": "Tooling standards (the claude-dot-files corpus)",
    "documentation": "Documentation and process",
    "findings": "Findings and routing",
    # Spellings no rule derives from a folder name. An override is honest about
    # that where a smarter title-caser would only be wrong less often.
    "api": "API",
    "argocd": "ArgoCD",
    "deploy-a-saurus": "Deploy-A-Saurus",
    "yaml": "YAML",
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
    fields, wrapped = {}, []
    for m in _FIELD.finditer(head):
        fields[m.group(1).strip()] = m.group(2)
        following = head[m.end():].split("\n", 2)[1:2]
        if following and _CONTINUATION.match(following[0]):
            wrapped.append(m.group(1).strip())
    return Standard(path=path, fields=fields, vendored=bool(_VENDORED.search(text)),
                    wrapped=tuple(wrapped))


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


#: A relative markdown link with a `.md` target; URLs, mailto, bare anchors and
#: absolute paths are somebody else's problem. Same shape as the repo gate in
#: `test_relative_links_resolve.py`; this one travels with the tool so a corpus
#: with no suite beside it can still ask.
_REL_LINK = re.compile(r"\]\((?!https?:|mailto:|#|/)([^)\s#]+\.md)(?:#[^)]*)?\)")
_FENCE_LINE = re.compile(r"^[ \t]*```")
_INLINE_CODE = re.compile(r"`[^`\n]*`")


def dead_links(items: list[Standard]) -> list[tuple[Path, int, str]]:
    """Every relative `.md` link in an OWNED standard whose target is not a file.

    Fenced blocks and inline code are illustrations, not navigation, and are
    skipped — the documentation standard's worked examples of link shape are
    written as code on purpose. Only owned standards: a mirror's links resolve
    in its owner's tree, which is where the owner checks them.
    """
    out = []
    for s in items:
        if s.vendored:
            continue
        fenced = False
        for n, line in enumerate(s.path.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            if _FENCE_LINE.match(line):
                fenced = not fenced
                continue
            if fenced:
                continue
            for m in _REL_LINK.finditer(_INLINE_CODE.sub("", line)):
                if not (s.path.parent / urllib.parse.unquote(m.group(1))).is_file():
                    out.append((s.path, n, m.group(1)))
    return out


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

    LINKS ARE REPO-RELATIVE, NOT ABSOLUTE. An absolute link bakes the invocation
    path into the artifact, so `--check` read a byte-identical `CLAUDE.md` as STALE
    from every worktree — and named `--write` as the fix, which would have committed
    a throwaway worktree path into every entry (I-q5c8jmxa, measured on two
    worktrees: the byte delta was exactly 18 links × the suffix length, twice). A
    relative link renders the same from any checkout, so the check agrees with
    itself wherever it runs, including CI.

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
            out += [f"### {_BUCKET_TITLES.get(bucket, re.sub(r'[-_]+', ' ', bucket).title())}", ""]
        for s in grouped[bucket]:
            link = (root / s.path).resolve().relative_to(root.resolve()).as_posix()
            out.append(f"- **[{_title(s.path)}]({link})** — "
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
    ap.add_argument("--links", action="store_true",
                    help="also resolve every relative .md link in the owned standards")
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
    dead = dead_links(items) if a.links else []
    if dead:
        print(f"DEAD LINKS — {len(dead)} relative link(s) in owned standards point at no file:")
        for path, n, target in dead:
            print(f"  {path.relative_to(root)}:{n}  {target}")
        print()
    if mirror_gaps:
        print(f"VENDORED, AND THE OWNER'S TO FIX — not this repo's work ({len(mirror_gaps)}):")
        for s in mirror_gaps:
            print(f"  {s.path.relative_to(root)} — missing {', '.join(s.missing)}")
        print()
    # `drift` BELONGS IN THIS CONDITION, and leaving it out printed the opposite of
    # the truth: a stale index reported "clean" on the last line of a run that exited
    # 1, and the last line is what a reader takes away. Observed 2026-09-08 driving
    # the staleness gate with a mutation — the gate was right and its summary was not.
    if not (gaps or stray or drift or dead):
        print("clean: every owned standard carries the three header lines and is indexed"
              + (", and every relative link resolves." if a.links else "."))
    return 1 if (a.check and (gaps or stray or drift or dead)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
