# `installer` — tests for `install.sh`

Tier 3 tests for the repo-root installer. Run them like any other component:

```bash
./testing/run-all.sh unit installer
```

## Why the tests do not live beside the code they test

`install.sh` sits at the repo root, and Testing Standard § Tier 3 puts a unit's
tests at its own level — which here would be a repo-root `tests/`. That
directory would be discovered by `testing/suites/python.sh` as a component
named for the repo itself, which reads as "the repo's tests" rather than "the
installer's", and it would sit beside `conftest.py` and `pytest.ini`, which
already claim the root for repo-wide pytest configuration. So the tests live
under `testing/` in a component directory named for the unit under test, the
same placement `config-hooks/` uses for the same reason (its README carries the
fuller argument). **Nothing in the runner was changed to accommodate this** —
`python.sh` discovers `*/tests/<category>` at any depth.

## What is here

| File | Covers |
|---|---|
| `tests/unit/test_install_places_the_managed_floor.py` | Workflow Decomposition Phase 7 requirement 4 — the managed floor is placed byte-for-byte, a stale or x-bit-stripped copy is re-placed, and the installer **refuses loudly** (exit 1; names the resolved path, the privilege lacked, and sudo's own reason) when it cannot write the managed directory. Also: the hook script is placed **before** the drop-in that declares it, a missing source writes **nothing** (never a partial floor), and a trailing slash on the managed directory is normalised |

The user-tier symlink step has no dedicated tests here; its wiring is held
from the other side by `testing/config-hooks/tests/unit/test_the_safety_hook_is_wired.py`,
which reads `SYMLINK_TARGETS` out of `install.sh`.

## How root is avoided

`install.sh` reads `CDF_MANAGED_DIR` (default `/etc/claude-code`, the only
directory Claude Code reads the managed tier from). The tests point it at temp
directories and put stub `claude`, `yq` and `sudo` executables first on PATH:
a `sudo` that refuses exercises the refusal; a `sudo` that "grants" (unlocks the
directory for one command) exercises the privileged branch. The real `install`,
`cmp` and `jq` are what runs. Every run is `--non-interactive` — the path a
dispatch or CI job takes, where a silent skip would go unnoticed longest.

## What is NOT covered here, and where it is

- **Whether Claude Code reads a hook from `/etc/claude-code/` under
  `--dangerously-skip-permissions`** — the fact the phase turns on. That is a
  host-run measurement against the real binary:
  `scripts/helpers/managed-tier-probe/`.
- **Whether this machine's `/etc/claude-code/` is current** —
  `test_the_managed_floor_is_wired.py` asks it conditionally, where an
  installation exists.
- The interactive `sudo` prompt path.
