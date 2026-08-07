# Testing

How to run the suite and how to add a test. The binding rules are in
[`../docs/standards/testing/`](../docs/standards/testing/) — start with that
directory's `README.md`, which states which half of the vendored standard
applies here.

## Layout — three tiers

```
testing/
├── run-all.sh              TIER 1 · the single "run everything" entry point
├── suites/python.sh        TIER 2 · one runner per framework actually in use
└── logs/                   per-suite output (gitignored)

scripts/workflows/temporal/tests/
└── unit/                   TIER 3 · the code unit owns its tests
```

There is no `suites/bash.sh` and that is deliberate — the standard says to
create a suite runner only for a framework actually in use, and there is not
one `.bats` file here. It ships with the first bats test, not before it.

`integration/` and `e2e/` do not exist yet either. `run-all.sh` reports them
as `SKIP (no tests/integration)` rather than as passes, because a skip and a
pass must never look alike in a summary.

## Prerequisites

```bash
pip install "pytest>=7,<9" "pyyaml>=6,<7" "ruff>=0.6,<1"
```

`pyyaml` is a runtime dependency, not just a test one — `preflight` refuses to
start without it.

## Running

```bash
./testing/run-all.sh                 # everything
./testing/run-all.sh unit            # one tier
./testing/run-all.sh unit temporal   # one tier, one component
```

Exit codes: `0` all green · `1` a suite failed, or **nothing ran at all**.
That second case matters — a green report over an empty tree is the failure
the standard singles out as looking healthiest of all.

## Adding a test

Put it in the component's own `tests/<tier>/` directory. It is discovered
automatically; nothing needs registering.

**A test placed outside a tier directory FAILS the run.** `run-all.sh` refuses
to proceed while an orphan exists, because a test that exists and never
executes is worse than no test — the count grows and the coverage does not.

**Ship the guard's demonstration with the guard.** A test that cannot fail is
not a test. Break the property deliberately, watch the test go red, restore it,
and say so in the commit. Two bugs were caught this way within a minute of the
tests existing — both in the fix that shipped alongside them.

## The gate

`.github/workflows/tests.yml` runs this suite plus a `ruff --select F821`
executability sweep on every PR and every push to `main`. It has no `paths:`
filter on purpose — see the standards README for why the obvious one is
silently wrong.
