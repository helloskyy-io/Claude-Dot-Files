"""The provenance stamp — the commit and the input digest a run derived from.

**Reading ``git log`` in the checkout is reading the ACTIVE artifact**, not a
snapshot: nothing is stored, nothing is cached, and the answer is recomputed per
run. It is the only history source this component uses.

``git`` is invoked as a subprocess against the checkout and never over a
network. A checkout with no ``.git`` (a tarball, a read-only pod mount of a
working tree) yields ``commit: "unknown"`` rather than raising — the digest still
identifies the inputs exactly, and a hard failure here would make the tool
unusable in the pod it is designed to run in.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .safe_paths import real_path_within_root

GIT_TIMEOUT_SECONDS = 15


def read_commit(root: Path) -> str:
    """The checkout's HEAD commit, or ``"unknown"``.

    ``check=False`` plus an explicit return is deliberate: a missing ``.git`` and
    a missing ``git`` binary are both *expected states* of a read-only mount, not
    errors to swallow. Anything else propagates.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def read_commit_date(root: Path) -> str:
    """HEAD's committer date in ISO-8601, or ``""``."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%cI"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def input_digest(root: Path, inputs: list[str]) -> str:
    """A stable digest over the exact bytes the run read.

    Sorted paths, each hashed as ``<path>\\0<sha256-of-bytes>\\0``, so the digest
    is identical across two runs on an unchanged checkout and changes when any
    input's content or the input SET changes. That is what makes the
    run-twice-byte-identical check meaningful rather than a tautology over a
    timestamp.
    """
    outer = hashlib.sha256()
    for rel in sorted(inputs):
        outer.update(rel.encode("utf-8"))
        outer.update(b"\0")
        # The same within-root test the walk and the read apply. This function
        # opens whatever path list it is handed, so without it a symlink that
        # reached the input set would put bytes from outside the checkout into
        # the stamp that claims to identify the checkout — the escape reported
        # in one section and consumed in another, in one run.
        if not real_path_within_root(root, root / rel):
            data = b"<escapes-root>"
        else:
            try:
                data = (root / rel).read_bytes()
            except OSError:
                data = b"<unreadable>"
        outer.update(hashlib.sha256(data).hexdigest().encode("ascii"))
        outer.update(b"\0")
    return f"sha256:{outer.hexdigest()}"
