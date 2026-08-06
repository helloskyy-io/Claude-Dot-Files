"""The repo-root memory guardrail actually binds this process.

Testing Standard § Test Resource Safety (binding) requires every pytest run to
be memory-bounded so a runaway test fails as a MemoryError rather than as a host
outage — a self-recursive `asyncio.sleep` mock once grew pytest to ~28 GB and
OOM-killed a control-plane VM on every workflow test run.

The guardrail is only worth having if it is ACTIVE, and "the conftest exists" is
not the same claim. The first test below reads the live rlimit of the very
process running it, so it fails if the root conftest is ever skipped — which is
precisely what happens if `pytest.ini` stops pinning rootdir and a subdirectory
invocation computes a rootdir below the repo root.
"""

from __future__ import annotations

import importlib.util
import resource
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[5]
_ROOT_CONFTEST = _REPO_ROOT / "conftest.py"

_GIB = 1024**3


def _load_root_conftest():
    """Import the root conftest under a private name.

    Not `import conftest` — that resolves to whichever conftest is first on
    sys.path and would silently test the wrong file.

    Executing the module re-runs its bottom-level `_apply_memory_cap()` call as a
    side effect, re-applying the DEFAULT cap. That is idempotent and harmless
    here — every caller below either restores the limit via `restore_rlimit` or
    raises before reaching `setrlimit` — but it is worth knowing before adding a
    test that assumes loading is inert.
    """
    spec = importlib.util.spec_from_file_location("repo_root_conftest", _ROOT_CONFTEST)
    assert spec and spec.loader, f"could not load {_ROOT_CONFTEST}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def restore_rlimit():
    """Save and restore RLIMIT_AS around a test that deliberately changes it."""
    original = resource.getrlimit(resource.RLIMIT_AS)
    yield
    resource.setrlimit(resource.RLIMIT_AS, original)


def test_the_running_pytest_process_is_memory_bounded() -> None:
    """The binding property, read off the live process."""
    soft, _hard = resource.getrlimit(resource.RLIMIT_AS)
    assert soft != resource.RLIM_INFINITY, (
        "RLIMIT_AS is unbounded in this pytest process — the root conftest.py "
        "guardrail did not load. Check that pytest.ini still pins rootdir to the "
        "repo root; without it a subdirectory invocation collects no root conftest "
        "and a runaway test takes down the host instead of failing as a test."
    )
    assert soft <= 8 * _GIB, (
        f"RLIMIT_AS soft limit is {soft / _GIB:.1f} GiB, above the 8 GiB default. "
        "Raising the cap to accommodate a test that should have been bounded is "
        "the documented way to break this rule."
    )


def test_root_conftest_is_where_the_guardrail_lives() -> None:
    assert _ROOT_CONFTEST.is_file(), (
        f"{_ROOT_CONFTEST} is missing — the guardrail must sit at the repo root "
        "so it loads for every pytest invocation, not just via testing/run-all.sh"
    )


def test_cap_honours_the_env_override(monkeypatch: pytest.MonkeyPatch, restore_rlimit) -> None:
    """The requested cap is applied, floored by any inherited HARD limit.

    The `min(requested, hard)` clamp is not an implementation detail to assert
    around — asserting a bare `== 2 GiB` couples this test to the host. On a
    systemd unit with `LimitAS=` or a memory-constrained CI container the hard
    limit can sit below 2 GiB, and the test would go red for a reason that has
    nothing to do with whether the override is honoured. Verified: under
    `ulimit -Hv 1048576` the bare form fails while this one passes.
    """
    conftest = _load_root_conftest()
    _soft_before, hard = resource.getrlimit(resource.RLIMIT_AS)
    expected = 2 * _GIB if hard == resource.RLIM_INFINITY else min(2 * _GIB, hard)

    monkeypatch.setenv("PYTEST_MEM_CAP_GIB", "2")
    conftest._apply_memory_cap()

    soft, _hard = resource.getrlimit(resource.RLIMIT_AS)
    assert soft == expected, (
        f"env override ignored — soft limit is {soft}, expected {expected} "
        f"(requested 2 GiB, inherited hard limit {hard})"
    )


@pytest.mark.parametrize("bad", ["not-a-number", "0", "-1", "", "inf", "-inf", "nan"])
def test_a_malformed_cap_refuses_to_run_rather_than_running_unbounded(
    monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    """Fail loud. A malformed cap that silently fell back to "no limit" would
    leave the suite unbounded while the conftest reported success — a guardrail
    that appears to address the problem while leaving it live.

    `inf`/`nan` are here because they are the cases that pass BOTH obvious
    guards: `float()` accepts them, and `<= 0` rejects neither (NaN compares
    false against everything; inf is positive). Before the finiteness check they
    reached `int(cap_gib * 1024**3)` and aborted collection with a bare
    OverflowError/ValueError that named neither the env var nor the remedy.
    """
    conftest = _load_root_conftest()
    monkeypatch.setenv("PYTEST_MEM_CAP_GIB", bad)
    with pytest.raises(RuntimeError, match="refusing to run unbounded"):
        conftest._apply_memory_cap()
