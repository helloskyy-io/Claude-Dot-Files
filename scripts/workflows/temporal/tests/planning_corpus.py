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
live corpus SKIP there rather than fail.

**AND THAT SKIP IS A REAL COVERAGE GAP, NOT A NEUTRAL FALLBACK.** `tests.yml`
rules on this exact question for `vendor-standards.sh --check`, which EXITS 1
rather than skipping when its upstream clone is absent — so the CI job omits the
step entirely rather than emit *"a green check that verified nothing, which is
worse than the gap it hides"* (tracked at #55). The corpus gates take the other
branch because they are collected by a single suite runner that cannot omit
individual modules, so the honest accounting is: **on a runner with no planning
repo these gates report green having asserted nothing.** The fix is the same one
#55 needs — a checkout of the sibling private repo — and it is one decision, not
two. Filed as `C-bjn8dpi6`.
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


def skip_module_without_corpus() -> None:
    """The same guard, at COLLECTION time, for modules that read at import.

    A module that parametrizes over the corpus, or builds a constant from it,
    touches the filesystem before any test function runs — so a per-test skip
    never executes and the module raises `FileNotFoundError` during collection,
    which pytest reports as an ERROR and the runner as a red suite. Two modules
    are that shape: the OPEN-criterion sweep parametrizes over `git ls-files`,
    and the roll-up gate reads the planning map into module constants.

    MEASURED: they took `main` red on the first push after the corpus moved, on a
    tree whose local `run-all.sh` was green — the difference being a runner that
    checks out one repo.
    """
    import pytest
    if not (PLANNING_ROOT / "standards").is_dir():
        pytest.skip(
            f"no planning repo beside this one (looked for {PLANNING_ROOT}). "
            f"This module reads the LIVE corpus at COLLECTION time, so it is "
            f"skipped whole rather than failing to import.",
            allow_module_level=True,
        )
