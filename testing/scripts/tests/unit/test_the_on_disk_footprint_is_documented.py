"""State this repo writes OUTSIDE any checkout must be named where an operator reads.

THE INSTANCE THIS CAME FROM, so the rule is not mistaken for a preference. PR #99
made every non-dry-run dispatch create `~/.local/state/claude-dot-files/journal/`
on the operator's machine. That path then appeared in **no** operator-facing
document — not `CLAUDE.md`, not `README.md`, not anything under `docs/guide/`,
not `install.sh` — only inside a planning doc for the phase that built it. The
review that caught it had to grep four surfaces by hand to establish the absence.

THE CLASS, WHICH IS NOT "THE JOURNAL". `CLAUDE.md` § *Symlink Strategy* is the
operator's model of what this repo puts on their machine, and it enumerates
`~/.claude/` only. Everything else the fleet writes is outside that list:

  * `<repo>/.claude/logs/*.jsonl` — documented (README, `docs/guide/operations.md`)
  * `<repo>/.claude/worktrees/` — documented (`/cleanup-merged-worktrees`)
  * the journal root — was not, and is the one that lives outside a checkout
    entirely, so deleting the clone does not remove it

Enumerating those three would be a list that goes stale. What this keys on
instead is **the code's own set of deployment shapes**: `root.DEPLOYMENT_SHAPES`
is the dimension along which new external state paths actually appear, so a
fourth shape — or a change to `APP_DIR_NAME`, `JOURNAL_DIR_NAME`, or the XDG
default — fails here until the operator documentation says where the bytes now
land. A hand-kept list would not have caught any of those.

⚠ WHAT THIS DOES NOT COVER. A DIFFERENT module writing to a new path outside the
repo is invisible to this check — the derivable population is deployment shapes,
not "every path any future module might create". `test_journal_containment.py`
carries the same shape of caveat for its own sweep. If a second such module lands,
this file is where the predicate widens, and stating that is cheaper than
pretending the coverage is total.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[4]

sys.path.insert(0, str(_REPO / "scripts" / "workflows" / "temporal"))
sys.path.insert(0, str(_REPO / "scripts" / "workflows" / "temporal" / "tests"))

from planning_corpus import PLANNING_ROOT  # noqa: E402

from modules.journal.root import (DEPLOYMENT_SHAPES, JournalRootError,   # noqa: E402
                                  default_root_for)

import sys as _cg_sys  # noqa: E402
from pathlib import Path as _cg_Path  # noqa: E402
_cg_sys.path.insert(0, str(_cg_Path(__file__).resolve().parents[4]
                           / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import require_planning_corpus  # noqa: E402


# Where an OPERATOR looks, as opposed to where a planning document explains a
# decision to a future engineer. A phase doc under docs/development/ deliberately
# does NOT count — that is precisely the surface the journal root was already on
# when it was reported as undocumented.
_OPERATOR_SURFACES = ((_REPO, "CLAUDE.md"), (_REPO, "README.md"),
                      (PLANNING_ROOT, "guide"))

# A shape with no derivable default is a documented refusal, not a gap: the
# container shape has no path this code could name that would not be a guess.
# Asserted below rather than skipped silently, so the exemption cannot grow.
_NO_DERIVABLE_DEFAULT = ("container",)

# The environment the `user` shape's documented default is stated against. Fixed
# rather than read from the process, so the assertion is about the DOCUMENTED
# default and not about whichever machine happens to run the suite.
_DOCUMENTED_ENV = {"HOME": "/home/OPERATOR"}


def _operator_docs() -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for root, surface in _OPERATOR_SURFACES:
        target = root / surface
        if target.is_file():
            found.append(target)
        elif target.is_dir():
            found.extend(sorted(p for p in target.rglob("*.md")))
    return found


def _documented_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in _operator_docs())


def _default_path_for(shape: str) -> str | None:
    """The shape's default root with the operator's home elided, or None if it has none."""
    try:
        root = default_root_for(shape, _DOCUMENTED_ENV)
    except JournalRootError:
        return None
    return str(root).replace(_DOCUMENTED_ENV["HOME"], "~")


def test_the_operator_surfaces_this_checks_against_actually_EXIST() -> None:
    """The control on the control: an assertion over an empty corpus passes silently."""
    require_planning_corpus()
    docs = _operator_docs()
    assert len(docs) > 5, (
        f"only {len(docs)} operator-facing documents found under "
        f"{_OPERATOR_SURFACES} — this check is asserting against nothing")
    assert (_REPO / "CLAUDE.md").is_file()


def test_the_no_default_exemption_is_only_what_it_says_it_is() -> None:
    """An exemption that grows silently is a hole, so it is derived and compared."""
    without = tuple(s for s in DEPLOYMENT_SHAPES if _default_path_for(s) is None)
    assert without == _NO_DERIVABLE_DEFAULT, (
        f"the set of deployment shapes with no derivable default root has changed: "
        f"code says {without}, this file declares {_NO_DERIVABLE_DEFAULT}. A shape "
        f"that gained a default now writes to a path nobody has documented; a "
        f"shape that lost one refuses at resolution and needs saying so.")


@pytest.mark.parametrize("shape", [s for s in DEPLOYMENT_SHAPES
                                   if s not in _NO_DERIVABLE_DEFAULT])
def test_every_deployment_shape_s_default_root_is_named_where_an_operator_READS(
        shape: str) -> None:
    """THE REQUIREMENT. Undocumented state is state nobody backs up or deletes."""
    require_planning_corpus()
    path = _default_path_for(shape)
    assert path, f"{shape} lost its default root — update _NO_DERIVABLE_DEFAULT"

    assert path in _documented_text(), (
        f"deployment shape {shape!r} creates {path} on the operator's machine and "
        f"no operator-facing document names it.\n"
        f"SCOPE: {', '.join(_OPERATOR_SURFACES)} — a planning doc under "
        f"docs/development/ does NOT count, because that is exactly where this "
        f"path already was when it was found undocumented.\n"
        f"Add it to docs/guide/operations.md § What this repo puts on your machine, "
        f"with who writes it and what removes it.")


def test_the_check_would_FAIL_on_an_undocumented_shape() -> None:
    """DEMONSTRATED. A path nobody documents must not be able to pass this file.

    Uses a path that cannot appear in any document by construction, so the
    control cannot be satisfied by an unrelated mention somewhere in the corpus —
    which is the way a substring check over a large body of prose usually fails.
    """
    invented = "/var/lib/claude-dot-files-THIS-PATH-IS-NOT-DOCUMENTED-anywhere"
    assert invented not in _documented_text(), (
        "the negative control's sentinel now appears in the docs, so it proves "
        "nothing — pick another")


def test_the_check_ACCEPTS_a_path_the_docs_do_name() -> None:
    """The other half: a guard that refuses everything discriminates nothing."""
    require_planning_corpus()
    assert "~/.local/state/claude-dot-files/journal" in _documented_text()
