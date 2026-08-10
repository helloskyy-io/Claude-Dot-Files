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
├── scripts/mutate.sh       the mutation harness (see "Adding a test" below)
├── config-hooks/tests/     TIER 3 · tests for config/hooks/ — see its README
└── logs/                   per-suite output (gitignored)

scripts/workflows/temporal/tests/
└── unit/                   TIER 3 · the code unit owns its tests
```

There is no `suites/bash.sh` and that is deliberate — the standard says to
create a suite runner only for a framework actually in use, and there is not
one `.bats` file here. It ships with the first bats test, not before it.

**`testing/scripts/mutate.sh` drives pytest only** — `run_leg` hardcodes
`python3 -m pytest "$TARGET"`. Mutation evidence is binding
([`docs/standards/testing/README.md`](../docs/standards/testing/README.md)
lists it as **YES**), so a test written in a framework this harness cannot
drive cannot satisfy that rule today. Know this while planning a framework,
not mid-implementation: it is the structural reason a bats suite for
`config/hooks/` was not viable when it was first considered (issue #52).

`config-hooks/` is the one component whose tests do NOT sit beside the code
they cover, because `install.sh` symlinks `config/hooks` wholesale into
`~/.claude/hooks` and a `tests/` directory there would land in the operator's
live config on every machine. The reasoning is in
[`config-hooks/README.md`](config-hooks/README.md). It is discovered by the
unmodified runner like any other component — that is the bar a placement has
to clear.

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
not a test. Use the harness rather than doing it by hand:

```bash
testing/scripts/mutate.sh <file> <old-string> <new-string> <pytest-target>
```

It runs baseline → mutated → restored and reports whether the guard actually
fired. Each leg is judged by **pytest's exit code**, not by grepping the
output for the word "failed" — a mutation that breaks collection prints
"1 error" and exits 2, which has no "failed" in it, so a substring check
called a fired guard a miss.

**Exit 2 is ambiguous and the harness resolves it, so read the message rather
than the code.** The same "1 error during collection" means *the guard fired
hard* when a mutated **data** subject (a crontab entry, a workflow YAML) makes
the guard's own module-level parsing reject it — and means *nothing ran at
all* when the mutation left the **Python file under test** unimportable, since
pytest could never import it (issue #72). The discriminator is **differential**:
the harness imports `<file>` before mutating and again after, and calls it a
harness error only when the mutation is what broke the import. If `<file>`
does not import standalone even unmutated — a module needing pytest's own
`conftest.py` and `sys.path` setup, which many in this repo do — the probe
cannot speak, so the leg falls back to RED and the run says so on stderr.
Confirm by hand there that a test really ran.

**Exit 3/4/5 abort the run outright** as harness errors rather than being read
as a result: 5 ("no tests collected") means the target was wrong, not that the
mutation had no effect; 4 is a pytest usage error; 3 is pytest's own internal
error, which is never a test result. `mutate.sh` carries the full exit-code
table with the ambiguity of each spelled out — including why exit 0 is
ambiguous too and why that one needs no fix.

It refuses a mutation string that is not present, because a mutation that
changes nothing proves nothing — and it refuses one that matches more than
once, because only the first occurrence is replaced and "the first" is often a
mention in a comment header rather than the live code. That case is the nasty
one: the mutation changes no behaviour, every leg stays green, and the harness
reports a guard failure that never happened. Narrow the string until it is
unambiguous — including the surrounding quotes is usually enough
(`"'git reset --hard'"`, not `'git reset --hard'`).

**Do not hand-roll this loop.** CPython validates cached bytecode on
whole-second mtime *plus* source byte size, so a length-preserving edit applied
within one second silently runs the STALE `.pyc` — the test passes having
tested nothing. `PYTHONDONTWRITEBYTECODE=1` does **not** fix it: that suppresses
*writing* a cache, not *reading* one. The harness gives every leg **and every
import probe** its own `PYTHONPYCACHEPREFIX`, which is the only reliable
defeat — the probe ran without one once, and a cache entry answered it
"imports fine" for a file pytest could not import at all. Two bugs were caught this way within a minute of the
tests existing — both in the fix that shipped alongside them.

## The gate

`.github/workflows/tests.yml` runs this suite plus a `ruff --select F821`
executability sweep on every PR and every push to `main`. It has no `paths:`
filter on purpose — see the standards README for why the obvious one is
silently wrong.
