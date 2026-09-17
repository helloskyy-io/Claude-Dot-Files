"""The two I/O operations every parser in this package needs: walk, and read.

**They live here because the copies had drifted, and the drift falsified the
package's own spine.** Before this module the walk existed three times and the
read nine times, and the nine reads carried *three different policies* for a
file that cannot be read: crash the request, skip it silently, or skip it
silently after replacing undecodable bytes. Two of those three are the
never-silently-drop rule failing at the file layer — the layer the phase doc
calls the more dangerous of the two, because a dropped line is one finding and a
dropped file is a whole component or phase absent from the graph with nothing to
indicate it.

The walk had a matching gap: it admitted any ``.md`` that ``is_file()`` accepts,
which includes a symlink physically under the corpus whose target is outside the
checkout. ``safe_paths`` reports an escape for a link target *authored in the
text* and never opens it; a symlinked source file walked straight past that
guard. Same invariant, other end of the pipe.

One implementation, one policy: **an unreadable file is a named finding and a
symlink leaving the root is reported and never opened.**

**The escape check lives on the READ as well as on the walk**, and ``collector``
is a required argument of every function here. Both were once true only of the
walk, with an optional collector defaulting to *suppress* — so the invariant
held for callers that happened to enumerate through this module and passed a
collector, and silently did not for the ones that did neither. A guard with a
caller list is not a guard.
"""

from __future__ import annotations

from pathlib import Path

from .model import (
    FILE_UNREADABLE,
    PATH_ESCAPES_ROOT,
    SECTION_UNCLASSIFIED,
    Collector,
    Provenance,
)
from .safe_paths import real_path_within_root


def _already_reported(collector: Collector, code: str, file: str) -> bool:
    """Whether this exact (code, file) is already a finding.

    Three walks overlap — ``development/`` for discovery, the whole checkout for
    the amendment census and again for the broken-link sweep — so one unreadable
    file or one escaping symlink is met up to three times. It is ONE defect in
    the corpus and must be ONE row in the report; a reader who sees the same
    path three times learns to skim the section.

    **``collector`` is required, and that is the point.** It used to be optional
    and this function answered ``True`` — i.e. *suppress* — for ``None``, so any
    caller that omitted it silently disabled the reporting the module exists to
    guarantee. The never-silently-drop rule cannot be one default argument away
    from off.
    """
    return any(f.code == code and f.provenance.file == file for f in collector.findings)


def _report_escape(collector: Collector, rel: str, what: str) -> None:
    """One wording for an escape, whether met by the walk or by the read."""
    if _already_reported(collector, PATH_ESCAPES_ROOT, rel):
        return
    collector.add_finding(
        PATH_ESCAPES_ROOT,
        SECTION_UNCLASSIFIED,
        f"{what} leaves the checkout root",
        Provenance(rel),
        expected="a regular file inside the checkout",
        detail="Reported and never opened.",
    )


#: The generator's own output, excluded from EVERY walk. Not an input
#: exclusion — output is not corpus — but a fixed-point one: the committed
#: pages render amendment-shaped tables and enumerate link targets, so a walk
#: that read them would derive pages that differ from the ones it read, and
#: `--check` could never agree with `generate`. Measured the first time the
#: pages were committed: the amendment census read the decisions page's
#: "amendments awaiting ratification" table as a §8 second surface.
DERIVED_OUTPUT = ("development/derived/",)


def iter_markdown(
    root: Path,
    subdir: str = "",
    *,
    collector: Collector,
    exclude_prefixes: tuple[str, ...] = (),
) -> list[str]:
    """Every ``.md`` under ``<root>/<subdir>``, repo-relative and sorted.

    Dot-directories and :data:`DERIVED_OUTPUT` are excluded outright (the
    phase doc names the first; the second is the tool's own output) and so are
    ``exclude_prefixes``, which is how the broken-link sweep states its own
    ``backup/``/``assets/`` exclusions rather than hardcoding them in the walk.

    **Sorting is load-bearing**: ``Path.rglob`` order is filesystem-dependent,
    and the emitted graph must be byte-identical across two runs on an unchanged
    checkout.

    A file whose real path leaves ``root`` is **excluded from the result and
    reported** — never opened.
    """
    base = root / subdir if subdir else root
    if not base.is_dir():
        return []
    out: list[str] = []
    for candidate in base.rglob("*.md"):
        rel = candidate.relative_to(root).as_posix()
        if any(part.startswith(".") for part in rel.split("/")):
            continue
        if rel.startswith(DERIVED_OUTPUT):
            continue
        if exclude_prefixes and rel.startswith(exclude_prefixes):
            continue
        if not candidate.is_file():
            continue
        if not real_path_within_root(root, candidate):
            _report_escape(collector, rel, "enumerated file is a symlink whose target")
            continue
        out.append(rel)
    return sorted(out)


def read_text(root: Path, rel: str, collector: Collector) -> str | None:
    """Read a corpus file, or report why it could not be read and return ``None``.

    ``errors="replace"`` on every read, without exception: the corpus is
    human-authored and a stray byte must not be able to take a page down. An
    ``OSError`` — a permission denial, a broken symlink, a file deleted between
    the walk and the read — becomes a :data:`~.model.FILE_UNREADABLE` finding
    rather than a crash *or* a quiet omission.

    **Callers must handle ``None``.** Returning ``""`` would let a caller carry
    on against an empty file, which is the silent-drop shape wearing a different
    type.

    The within-root check is repeated HERE rather than left to the walk, because
    not every path reaching this function came from the walk — a tracked item's
    ``target:``, an anchor's host document, a link target. A guard that holds
    only for callers who happened to enumerate first is a guard with a caller
    list, and the caller list is what drifts.
    """
    if not real_path_within_root(root, root / rel):
        _report_escape(collector, rel, "file to read is a symlink whose target")
        return None
    if not (root / rel).is_file():
        # The same regular-file test the walk applies, repeated here for the
        # same reason the escape check is: not every path reaching this function
        # came from the walk. A FIFO or a character device inside the corpus
        # would otherwise be OPENED, and a read from a FIFO with no writer blocks
        # forever — a request that never returns, with no finding to say why.
        collector.add_finding(
            FILE_UNREADABLE,
            SECTION_UNCLASSIFIED,
            "path to read is not a regular file",
            Provenance(rel),
            expected="a regular file inside the checkout",
            detail="Reported and never opened.",
        )
        return None
    try:
        return (root / rel).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        if not _already_reported(collector, FILE_UNREADABLE, rel):
            collector.add_finding(
                FILE_UNREADABLE,
                SECTION_UNCLASSIFIED,
                f"file enumerated but could not be read: {exc.strerror or exc}",
                Provenance(rel),
                expected="a readable UTF-8 file",
                detail="The graph is smaller than the corpus by exactly this file.",
            )
        return None


def read_lines(root: Path, rel: str, collector: Collector) -> list[str] | None:
    """:func:`read_text`, split into lines. ``None`` when the file is unreadable."""
    text = read_text(root, rel, collector)
    return None if text is None else text.splitlines()
