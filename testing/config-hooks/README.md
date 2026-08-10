# `config-hooks` — tests for `config/hooks/`

Tier 3 tests for the hook scripts in [`config/hooks/`](../../config/hooks/).
Run them like any other component:

```bash
./testing/run-all.sh unit config-hooks
```

## Why the tests do not live beside the code they test

Testing Standard § Tier 3 says a code unit owns its tests at its own level, so
the conforming path would be `config/hooks/tests/unit/`. It is not used here,
and the reason is `install.sh`.

`install.sh` symlinks **whole directories** — `config/hooks` → `~/.claude/hooks`
— with no per-file granularity (`SYMLINK_TARGETS` in `install.sh`). A
`config/hooks/tests/` directory would therefore appear inside the operator's
live Claude Code hooks directory on every machine the repo is installed on.
That is not merely untidy: pytest **writes** into the tree it collects
(`__pycache__/`, `.pytest_cache/`), so running the suite would mutate a live
config directory as a side effect. `config/` is the repo's declared source of
truth for synced Claude Code configuration, and test code is not configuration.

So the tests live under `testing/` instead, in a component directory named for
the unit under test. `config-hooks`, not `hooks`, so the path reads as "the
tests for `config/hooks`" rather than "hooks belonging to the test harness".

**Nothing in the runner was changed to accommodate this.**
`testing/suites/python.sh` discovers `*/tests/<category>` at any depth and
derives the component name from the parent of `tests/`, so this directory is
found by the same walk that finds every other component. If a placement is not
discovered by the unmodified runner, the placement is wrong — not the runner.

## What is here

| File | Covers |
|---|---|
| `tests/unit/test_block_dangerous.py` | `config/hooks/block-dangerous.sh` — issue #52 |

`notify-done.sh` has no tests yet.

## These were characterization tests, and are now a specification

`test_block_dangerous.py` started by pinning what the hook did **today**,
including behaviour that was arguably wrong, because widening or narrowing a
security control is a human-ruled decision and not a side effect of writing its
tests. That pass found four defects (issue #61). The operator ruled on all
four, they are fixed, and the "characterized, not endorsed" assertions that
carried them are gone.

A test going red still means the hook's behaviour changed — decide whether that
was intended before changing either side. The file's own module docstring
carries the full rules.

**The hook now states its own claims and this suite executes them.** Each
pattern carries `# MUST BLOCK:` / `# MUST ALLOW:` comments (both mandatory) and
each threat-model bullet carries `PASSES THROUGH:` / `BLOCKED ANYWAY:`; all of
them are parsed out of `block-dangerous.sh` and asserted against it. Three of
the four defects were the same shape — a pattern and what it claimed to cover
had drifted apart — so the claims are the fix for the class rather than for the
instances. Adding a pattern without saying what it blocks *and* what it must
not fails the suite.

**Executed claims are not enough on their own, and this is the part to read
before adding a pattern.** A claim proves the pattern agrees with what its
author wrote down; it cannot prove the author wrote down the right thing. The
first version of this mechanism shipped a right boundary of `([[:space:]]|$)`
on the `curl … | (sh|bash|zsh)` pattern with every claim beside it true and the
whole suite green, and `curl … | bash;true` went through. So the suite also
re-runs **every** command in the dangerous corpus with a shell separator
(`;true`, `&`, ` && echo ok`, `|cat`) appended and requires it to still be
denied. That check depends on nobody anticipating anything, and it is what
found the five right-boundary gaps the claims did not.
