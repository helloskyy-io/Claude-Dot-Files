# Testing Standard — vendored, and which half applies here

`testing_standard.md` is a **verbatim MIRROR** from `helloskyy-io/MDC-Master-Planning`. Do not edit it; amendments go upstream, then `scripts/helpers/vendor-standards.sh`.

**This file exists because roughly half the standard governs a runtime this repo does not have**, and every reviewer was re-deriving which half — reaching different answers. One such disagreement reached a PR body and cost a review cycle to settle. The rule is unchanged; this states its surface area here.

## What binds today

| Section | Binds | Why |
|---|---|---|
| **Three-tier layout** | **YES** | `testing/run-all.sh` → `testing/suites/python.sh` → per-unit `tests/{unit,integration,e2e}/`. Built and conformant |
| **pytest, not script-style** | **YES** | The V2 tree is pytest throughout |
| **Discovery completeness** | **YES** | A test outside runner discovery is a defect, enforced by `test_runner_discovery.py` |
| **Tier Enforcement** | **YES** | `.github/workflows/tests.yml` runs the master runner on every PR |
| **Test Resource Safety** | **YES** | Repo-root `conftest.py` sets `RLIMIT_AS`, env-tunable via `PYTEST_MEM_CAP_GIB` |
| **Mutation evidence** | **YES** | A guard ships with a demonstration that it fails when the property is violated |

## What does NOT bind here, and why

| Section | Status | Reason |
|---|---|---|
| **bats / bash suite runner** | **not yet** | There is not one `.bats` file in the repo. The standard is explicit: *"only create suite runners for frameworks actually in use."* A `bash.sh` suite ships with the first bats test, never before it |
| **Service / integration tiers** | **not yet** | No service runs here. `run-all.sh` reports these as `SKIP (no tests/integration)` rather than as passes — a skip and a pass must never look alike |
| **Helm / chart testing** | **N/A** | No charts. This repo deploys by symlink |
| **Database fixtures** | **N/A** | No database |

**"Not yet" is not "never".** Each of those becomes binding the day the thing it governs exists, and adding the thing without adding its tier is the violation.

## How this repo differs from the reference implementation

The standard is written in `MDC-Master-Planning`, which has **no tests and no CI** — it is a planning repo. The reference *implementation* is `skyy-command`, and comparing against it honestly:

| | skyy-command | here |
|---|---|---|
| `run-all.sh` + `suites/` | yes | yes |
| `testing/README.md` | yes | yes |
| `fixtures/` | yes | **no** — nothing needs one yet |
| CI gating the master runner | **no** — five workflows, all path-filtered, none runs the master runner | **yes** |

**We gate the master runner and the reference implementation does not.** That is a divergence in our favour, and it is surfaced upstream rather than quietly enjoyed — the standard's own Tier Enforcement clause binds both repos.

## The gate

`.github/workflows/tests.yml` runs `./testing/run-all.sh` plus a `ruff --select F821` executability sweep on every PR and every push to `main`.

**It carries no `paths:` filter, deliberately.** The obvious filter — `scripts/workflows/temporal/**` and `testing/**` — is silently wrong: the suite reads `config.yaml` (every `MODEL_KEY` must resolve there) and the V1 bash scripts under `scripts/workflows/` (turn caps are derived from them, prompts byte-compared against them). Removing a model key, the exact bug that guard exists to catch, would not have triggered a filtered gate. The suite runs in ~4 seconds; a filter saves nothing and can only ever skip something it should have caught.

## Related

- [`testing_standard.md`](testing_standard.md) — the vendored rule (MIRROR, do not edit)
- [`../../../testing/README.md`](../../../testing/README.md) — how to run the suite and add a test
- [`../temporal/README.md`](../temporal/README.md) — the same applicability treatment for the Temporal standards
