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

## These are characterization tests

`test_block_dangerous.py` pins what the hook does **today**, including
behaviour that is arguably wrong. It is not a specification of what the hook
ought to do. A test going red means the hook's behaviour changed — decide
whether that was intended before changing either side. The file's own module
docstring carries the full rules, including why the threat-model gaps are
encoded as passing-through cases rather than as failures.
