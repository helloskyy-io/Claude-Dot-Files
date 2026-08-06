"""Repo-root pytest configuration — the memory guardrail lives here.

Testing Standard § Test Resource Safety (binding): every pytest run MUST be
memory-bounded so a runaway test fails AS A TEST (MemoryError) rather than as a
host outage. The failure that made this binding: a single unit test with a
self-recursive `asyncio.sleep` mock ran pytest to ~28 GB, OOM-killed the guest,
and took down the whole control-plane VM — repeatedly, on every workflow test
run.

This file is the mechanism because it loads for EVERY pytest invocation — a
direct `pytest <path>` or `testing/run-all.sh` — so the bound cannot be skipped
by choosing a different entry point. `pytest.ini` beside it pins rootdir here,
which is what puts this file on the collection path no matter which
subdirectory is passed as an argument.

The cap is deliberately far above the suite's real peak (this suite's full run
is a few tens of MB). It is a backstop against runaway allocation, not a budget:
raising it to accommodate a test that should have been bounded is the documented
way to break this rule.
"""

from __future__ import annotations

import os
import resource

# Matches the reference implementation (skyy-command/conftest.py). Env-tunable
# under the same name so an operator debugging a genuine large-fixture case has
# one knob with one meaning across repos.
_DEFAULT_CAP_GIB = 8.0
_ENV_VAR = "PYTEST_MEM_CAP_GIB"


def _apply_memory_cap() -> None:
    raw = os.environ.get(_ENV_VAR)
    if raw is None:
        cap_gib = _DEFAULT_CAP_GIB
    else:
        try:
            cap_gib = float(raw)
        except ValueError as exc:
            # Fail loud. A malformed cap silently falling back to "unbounded" is
            # exactly the state this file exists to make impossible.
            raise RuntimeError(
                f"{_ENV_VAR}={raw!r} is not a number — refusing to run unbounded"
            ) from exc
        if cap_gib <= 0:
            raise RuntimeError(f"{_ENV_VAR}={raw!r} must be positive — refusing to run unbounded")

    cap_bytes = int(cap_gib * 1024**3)
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    # Never attempt to exceed an inherited hard limit — setrlimit would raise and
    # abort collection for a reason unrelated to any test.
    if hard != resource.RLIM_INFINITY:
        cap_bytes = min(cap_bytes, hard)
    resource.setrlimit(resource.RLIMIT_AS, (cap_bytes, hard))


_apply_memory_cap()
