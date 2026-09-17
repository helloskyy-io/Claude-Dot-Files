"""Path resolution confined to the checkout root.

Several requirements turn corpus-authored text into a filesystem path — a graph
edge's link target, a tracked item's ``component:``, an ``anchor:`` resolved
inside its ``target:``. **A resolved path that escapes the checkout root is
reported as a finding and never opened.**

Today the corpus is operator- and dispatch-authored and the tool runs locally,
so the exposure is near-zero. It stops being near-zero the moment the drift gate
gets a CI home, because a pull-request-authored link then becomes untrusted
input to a path-reading process. Stating it now costs a module.

**Nothing here consults where the checkout sits.** Resolution is a pure function
of the link text and the source file's repo-relative path, never of ``root``'s
absolute location — that is what lets ``--check`` give one answer from the
canonical host, a worktree and a pull-request runner. A resolver that tries
an absolute link as a real path first succeeds only on the one host whose
checkout sits at that path, and the graph then carries edges no other checkout
can see.
"""

from __future__ import annotations

import posixpath
from pathlib import Path
from urllib.parse import unquote

from .contract import canonical_checkout_for

# A corpus's canonical host path — the prefix that makes a link HOST-ABSOLUTE —
# is the corpus's own declaration (`corpus.toml`, `canonical_checkout`) and is
# read through `contract.canonical_checkout_for(root)`. It was a constant naming
# one repository's path, which made this package able to read exactly that
# repository and no other.


class PathEscape(Exception):
    """A corpus-authored path resolved outside the checkout root."""

    def __init__(self, raw: str, resolved: str) -> None:
        super().__init__(f"{raw!r} resolves outside the checkout root ({resolved})")
        self.raw = raw
        self.resolved = resolved


def real_path_within_root(root: Path, candidate: Path) -> bool:
    """Whether ``candidate``'s REAL path is still under ``root``.

    **The single implementation of the within-root test.** It lived three times
    — inline in :func:`exists_in_root`, again in ``corpus_io``'s walk, and
    nowhere at all in ``provenance``, which hashed whatever bytes it was handed.
    A guard whose coverage depends on which copy a caller happened to reach is
    not a guard; a symlink under the corpus pointing outside the checkout walked
    straight past the two that existed.

    ``resolve()`` follows symlinks, so this is the check that a *source* file is
    inside the root, not merely that its unresolved path looks like it is.
    """
    try:
        candidate.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def split_anchor(target: str) -> tuple[str, str]:
    """Split ``path.md#anchor`` into ``("path.md", "anchor")``.

    A bare ``#anchor`` yields ``("", "anchor")`` — a same-file reference.
    """
    if "#" not in target:
        return target, ""
    path_part, _, anchor = target.partition("#")
    return path_part, anchor


def is_external(target: str) -> bool:
    """True for links this tool must not treat as filesystem paths.

    Absolute URLs, mailto:, and bare anchors are all legitimate markdown and are
    not graph edges. An ABSOLUTE filesystem path is deliberately NOT excluded
    here — a corpus may contain host-absolute links, and those are
    resolved-and-checked like any other so an escape is reported rather than
    silently skipped.
    """
    if not target:
        return True
    lowered = target.lower()
    # ``file://`` is a URL scheme, not a relative path. Without it the broken-link
    # measurement resolves `file:///opt/...` against the SOURCE FILE'S DIRECTORY
    # and counts the miss as a broken RELATIVE link — inflating a figure whose
    # stated method is "relative markdown links". Three such links exist on main.
    if lowered.startswith(("http://", "https://", "mailto:", "ftp://", "file://", "//")):
        return True
    return target.startswith("#")


def is_host_absolute(target: str, root: Path) -> bool:
    """True for a link written against the canonical checkout's host path.

    Takes the DECODED target (``resolve_within_root`` unquotes before calling)
    and the raw one alike — the prefix carries nothing that URL-encodes.
    A path under the same parent but outside the declared checkout — a
    sibling repository's file — is NOT host-absolute in this sense: it names a
    file outside this repository, and stripping the prefix would invent a
    repo-relative path for it. It resolves to nothing from every checkout, which
    is path-independent already.
    """
    prefix = canonical_checkout_for(root)
    if not prefix:
        return False
    return target == prefix or target.startswith(prefix + "/")


def resolve_within_root(root: Path, source_rel: str, target: str) -> str:
    """Resolve a corpus-authored relative link to a repo-relative path.

    ``source_rel`` is the repo-relative path of the file the link was read from;
    the link is resolved against that file's directory, exactly as a markdown
    renderer would.

    Returns the repo-relative POSIX path. Raises :class:`PathEscape` when the
    result lands outside ``root`` — including via an absolute path or a ``..``
    chain. **The caller reports; it never opens the path.**
    """
    raw = unquote(target)
    if raw.startswith("/"):
        # An absolute link. Two readings exist in the corpus — a host-absolute
        # path against the canonical checkout, and a repo-root-relative link —
        # and both are read off the TEXT. The host-absolute reading used to be
        # tried as a real path first (`Path(raw).resolve().relative_to(root)`),
        # which succeeds only on the one host whose checkout sits at that path:
        # the derivation then differed by checkout location, and `--check`
        # could never run on a runner. `root` is deliberately not consulted.
        if is_host_absolute(raw, root):
            raw = raw[len(canonical_checkout_for(root)) :]
        rel_guess = posixpath.normpath(raw.lstrip("/")) if raw.strip("/") else "."
        if rel_guess == ".." or rel_guess.startswith("../"):
            raise PathEscape(target, raw)
        return rel_guess

    source_dir = posixpath.dirname(source_rel)
    joined = posixpath.normpath(posixpath.join(source_dir, raw))
    if joined == ".." or joined.startswith("../"):
        raise PathEscape(target, joined)
    return joined


def exists_in_root(root: Path, rel: str) -> bool:
    """Whether a repo-relative path exists in the checkout.

    Guards against a symlink escape as well: the resolved real path must still
    be under ``root``.
    """
    if not rel:
        return False
    candidate = root / rel
    if not candidate.exists():
        return False
    return real_path_within_root(root, candidate)
