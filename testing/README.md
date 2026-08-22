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
├── scripts/tests/unit/     TIER 3 · the harness's own tests, and the repo-wide
│                                    test-tree and docs/prose gates no code unit owns
├── config-hooks/tests/     TIER 3 · tests for config/hooks/ — see its README
└── logs/                   per-suite output (gitignored)

scripts/workflows/temporal/tests/
├── unit/                   TIER 3 · the code unit owns its tests
└── integration/            TIER 3 · tests that read machine-local state a real
                                     dispatch produced, and cannot build it
                                     themselves — so they SKIP on a clean runner
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

`e2e/` does not exist yet. `run-all.sh` reports an absent category as
`SKIP (no tests/<category>)` rather than as a pass, because a skip and a pass
must never look alike in a summary.

**`integration/` now exists** (`scripts/workflows/temporal/tests/integration/`,
added with the journal package) — and it has a limit worth knowing before you
add to it. Its tests read bags that real dispatches left on this machine, which
a clean checkout does not have, so every test in it is `skipif`-gated and the
whole tier reports **PASS having asserted nothing** on a CI runner. That is the
category-present-but-nothing-ran case, which is a different thing from the
category being absent, and `run-all.sh` cannot currently tell them apart — no
pytest exit code carries an executed-test count. It is the same gap
[`C-abieu0fg`](../docs/standards/architecture/research/candidates.md) already
describes for `mutate.sh`'s legs, met here through a second tool. **So an
integration test is never the evidence that a guard works** — write the unit
test that runs everywhere, and let the integration tier confirm the shape
against real output.

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

**A pytest exit 2 is ambiguous and the harness resolves it differentially** —
the same "1 error during collection" means the guard fired hard (a mutated
crontab or YAML that the guard's own parsing rejects) or that nothing ran at
all (the mutation left the Python file under test unimportable, issue #72). So
the harness imports `<file>` before and after mutating, and blames the mutation
only when that is what changed. When `<file>` does not import standalone even
unmutated it says so on stderr and falls back to reading the leg as red; that
note is your cue to confirm by hand that a test really ran. *pytest's* exits 3,
4 and 5 abort the run rather than being read as a result.

**`mutate.sh`'s exit-code tables are the reference and they are not repeated
here** — both sit above `classify_leg`, one for the codes pytest hands in and
one for the codes the script hands out, and each answers, for every code,
whether it can mean both "the suite ran" and "it never ran". Read them before
changing the classification, and before calling this from anything other than
your own shell. *(This paragraph previously declared that policy and then
restated the second table seven lines below it, which is the restated-figure
class this repo has measured as non-convergent. One source now.)*

The tables also record the ambiguities deliberately left open rather than
claimed closed — an all-skipped leg exiting 0, the abstained discriminator, and
the `addopts` channel — with the mechanism for each placed as a candidate — **C-45bhs5cm**, **C-xhb460zu** and **C-73bf2gvm** respectively. *(The middle one was missing until 2026-08-11: its only record was prose inside this directory's 728-line script, which `plan-sprint` does not read, so the claim above was true of two of three.)* Do
not read the absence of a caveat here as the absence of one.

The single fact worth carrying away without opening the file: **`1` and `3` are
separate on purpose.** `1` sends you to the guard; `3` says the guard was never
judged. Conflating them is how a working guard gets deleted — and the
separation is enforced rather than documented, because every termination the
script did not deliberately choose is classified as a `3` by its EXIT trap.

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
