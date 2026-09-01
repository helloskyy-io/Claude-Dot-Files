"""Where the planning corpus lives, for tests that assert against the LIVE one.

`claude-dot-files` stopped carrying `docs/standards`, `docs/development`,
`docs/guide` and `tracked/` on 2026-08-31; they are `skyynet-master-planning`'s,
the same way `skyy-command` keeps no copy of `mdc-master-planning`.

DERIVED AS A SIBLING rather than configured, because the two repos sit beside
each other on every machine that holds both — `/opt/skyy-net/` on the VM,
`~/Repos/` on a workstation — and a configured path is one more thing to be
wrong on a new machine.

A CLONE WITHOUT THE PLANNING REPO IS A LEGITIMATE STATE, not a failure: this repo
is the tooling and it runs against whatever `--repo` names. Tests that read the
live corpus SKIP there rather than fail, which is the same call
`vendor-standards.sh` makes when it cannot find its source.
"""

from __future__ import annotations

from pathlib import Path


def planning_root() -> Path:
    """The sibling planning repo, whether or not it is checked out."""
    here = Path(__file__).resolve()
    for up in here.parents:
        cand = up.parent / "skyynet-master-planning"
        if (cand / "standards").is_dir():
            return cand
    return here.parents[0] / "__no_planning_repo__"


PLANNING_ROOT = planning_root()


def require_planning_corpus():
    """Skip with a reason naming what was wanted, rather than assert on nothing."""
    import pytest
    if not (PLANNING_ROOT / "standards").is_dir():
        pytest.skip(
            f"no planning repo beside this one (looked for {PLANNING_ROOT}). "
            f"This test reads the LIVE corpus, which moved out of this repo on "
            f"2026-08-31; with no corpus there is nothing to assert about."
        )
