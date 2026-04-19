---
name: test-suite-architecture
description: How to organize tests into a discoverable, runnable hierarchy — test placement, suite wiring, master runner integration, and scoped regression. Use when placing new tests, organizing existing tests into a suite, wiring tests into a master runner, assessing test coverage against a roadmap, or reviewing whether tests follow the project's testing standard. Pairs with testing-methodology (how to write tests) and testing-scaffolding (how to set up test infrastructure from scratch).
---

# Test Suite Architecture

This skill is about **where tests live and how they connect** — not how to write them (that's `testing-methodology`) or how to set up a framework from scratch (that's `testing-scaffolding`). This skill covers the structural decisions that determine whether tests accumulate into a regression suite or get created and abandoned.

## First Principles

### Tests Are a Deliverable, Not a Side Effect

Every test created during development must be placed in a discoverable location and wired into the project's test hierarchy. A test that passes once and is never run again is waste — it cost time to write and delivers zero ongoing confidence.

### The Hierarchy Enables Scoping

A well-organized test suite lets you run at three scopes:
1. **One component's tests** — fast feedback during development
2. **One category of tests** (all unit, all integration) — targeted validation
3. **Everything** — sprint-end regression before promoting to main

If you can't run at all three scopes, the hierarchy is broken.

### Discovery Is Automatic

Tests should be findable by convention, not registration. If a test file is in the right directory with the right name, the runner finds it. Manual test manifests, import lists, or registration calls are anti-patterns — they rot as tests are added and removed.

### Structure Follows the Project Standard

Every project with a testing standard (`docs/standards/testing.md` or equivalent) defines its own hierarchy. This skill teaches the methodology for FOLLOWING that standard. If no standard exists, this skill helps you recognize what's needed and flag it — but creating the standard is a planning task, not a test-writing task.

## Discovering the Project's Test Structure

Before placing or organizing tests, understand the project's testing conventions. Do NOT guess.

### Discovery Process

1. **Look for a testing standard**
   - `docs/standards/testing.md` — authoritative if it exists
   - `CLAUDE.md` — may reference testing conventions
   - `CONTRIBUTING.md` — may document test placement expectations

2. **Look for a master runner**
   - `testing/run-all.sh`, `scripts/test-all.sh`, `Makefile` test target
   - `package.json` test scripts
   - CI configuration files (show canonical test commands)

3. **Look for the test hierarchy**
   - `testing/` directory at repo root (master runner, suite runners, cross-component fixtures)
   - `<component>/tests/` directories (component-scoped tests)
   - Categorization: `tests/unit/`, `tests/integration/`, `tests/e2e/`

4. **Look for existing test patterns**
   - Read 2-3 existing test files — pattern recognition beats specification-reading
   - Note: framework (pytest, go test, bats), naming (`test_*.py`, `*_test.go`), fixtures (`conftest.py`, `testdata/`)

5. **If no conventions exist, flag the gap**
   - Surface it as a standards gap — "this project has no testing standard"
   - Do NOT invent a hierarchy ad-hoc — that creates the scattered-tests problem this skill exists to prevent

## The Three-Tier Hierarchy

Most projects benefit from a three-tier test organization. The specific paths vary by project; the pattern is universal.

### Tier 1: Master Runner

A single entry point that discovers and runs all test suites. One command for full regression.

Characteristics:
- Lives at the project's testing root (e.g., `testing/run-all.sh`)
- Discovers component test directories by walking the source tree
- Runs suites in order: unit → integration → e2e
- Supports filtering by category and component name
- Logs per-suite output
- Returns non-zero exit code if any suite fails

Invocation patterns the runner should support:
```
./testing/run-all.sh                        # everything
./testing/run-all.sh unit                   # all unit tests
./testing/run-all.sh unit <component>       # one component's unit tests
./testing/run-all.sh integration            # all integration tests
./testing/run-all.sh e2e                    # all end-to-end tests
```

### Tier 2: Framework Suite Runners

Per-language wrappers that handle discovery and execution for their ecosystem. Each runner invokes its framework against the component test directories.

Common patterns:
- Python: thin wrapper around `pytest` with path and config arguments
- Go: wrapper around `go test` with package paths
- Bash: wrapper around `bats` with file discovery
- Helm: wrapper around `helm template` / `helm lint` / `helm unittest`

Suite runners live in a dedicated directory (e.g., `testing/suites/`) and are invoked by the master runner. Only create runners for frameworks actually in use.

### Tier 3: Component Test Directories

Individual test files organized by category within each component's directory. This is where co-located tests live.

Common layout (co-located with component source):
```
components/<name>/
├── <source files>
└── tests/
    ├── unit/
    │   └── test_<module>.py
    ├── integration/
    │   └── test_<interaction>.py
    ├── fixtures/
    │   └── sample_data.yaml
    └── conftest.py
```

Cross-component tests (e2e, multi-component integration) live at the repo level:
```
testing/
├── e2e/
│   └── test_<workflow>.py
└── fixtures/
    └── common/
```

## Test Placement Decision Tree

When you need to place a new test, follow this decision tree:

```
Does this test require running infrastructure (cluster, VM, database)?
├── YES → Does it test a full workflow path end-to-end?
│         ├── YES → testing/e2e/
│         └── NO  → <component>/tests/integration/
└── NO  → Does it test one component in isolation?
          ├── YES → <component>/tests/unit/
          └── NO  → Does it test the interaction between specific components?
                    ├── YES → Pick the "owning" component or testing/integration/
                    └── NO  → Ask — the placement is ambiguous
```

### Key Rules

- **Unit tests go with their component** — `<component>/tests/unit/`
- **Integration tests usually go with the primary component** — `<component>/tests/integration/`
- **E2E tests go at the repo level** — `testing/e2e/` — they span components
- **Never place tests in ad-hoc directories** — no `scripts/test_something.py`, no `tools/check_x.py` using test_ prefix
- **Never place tests alongside source files** (except in Go, where the toolchain requires it) — use the `tests/` subdirectory

## Wiring Tests Into the Hierarchy

Placing a file in the right directory is necessary but not sufficient. The test must be **discoverable** by the suite runner.

### Verification Checklist

After placing a test file:

1. **Naming matches framework convention** — `test_*.py` for pytest, `*_test.go` for Go, `*.bats` for bats
2. **Imports resolve** — if the test imports component code, the import path works from the test's location
3. **Fixtures are available** — if the test uses shared fixtures, they're in `<component>/tests/fixtures/` or `testing/fixtures/`
4. **Discovery works** — run the component's test suite and verify the new test is found:
   ```
   ./testing/run-all.sh unit <component>
   ```
   If the master runner doesn't exist yet, use the framework directly:
   ```
   pytest <component>/tests/unit/
   ```
5. **The test passes** — a discovered test that fails is worse than no test (it blocks the suite)

### Common Discovery Problems

- **Missing `__init__.py`** in Python test directories — pytest may not discover tests without it (depends on configuration)
- **Wrong naming convention** — `check_auth.py` won't be found by pytest (needs `test_` prefix)
- **Broken imports** — test can't import the code it's testing because `sys.path` isn't configured
- **conftest.py scope** — fixtures defined in one component's conftest aren't available to another component's tests (this is correct behavior — don't try to share implicitly)

## Scoped Regression

Autonomous workflows should NOT run the full test suite on every change. Instead, use scoped regression:

### The Pattern

1. **Run new/modified tests** — validate the current change works
2. **If pass → run the affected component's full test suite** — catches regressions within the component
3. **Stop there** — do NOT run the global suite during per-PR workflow runs

### Why Not Run Everything?

- **Time** — a full suite may take minutes; scoped regression takes seconds
- **Tokens** — autonomous workflows have turn budgets; burning them on unrelated tests is waste
- **Signal** — if 267 tests pass and 1 fails in an unrelated component, is that your change or a pre-existing issue? Scoped regression keeps the signal clean.

### When to Run Everything

- Sprint-end regression before promoting to main
- After major refactors that touch shared infrastructure
- After dependency upgrades
- When the master runner itself changes

## Scaling for Project Size

The three-tier hierarchy scales naturally:

### Small Project (one repo, few components)

```
my-project/
├── src/
│   └── ...
├── tests/
│   ├── unit/
│   │   └── test_<module>.py
│   └── integration/
│       └── test_<interaction>.py
└── testing/
    └── run-all.sh
```

No `components/` directory — tests live in a top-level `tests/`. The master runner is simpler (one framework, one directory to scan). The hierarchy is shallow but the pattern is the same.

### Medium Project (one repo, many components)

```
my-project/
├── components/
│   ├── auth/
│   │   └── tests/unit/
│   ├── api/
│   │   └── tests/unit/
│   └── worker/
│       └── tests/unit/
└── testing/
    ├── run-all.sh
    ├── suites/python.sh
    ├── e2e/
    └── fixtures/
```

Component-scoped tests, a master runner that walks `components/*/tests/`, and e2e tests at the repo level.

### Large Project (multi-repo)

```
/opt/project/
├── main-repo/
│   ├── components/*/tests/
│   └── testing/run-all.sh      ← primary master runner
├── infra-repo/
│   └── testing/run-all.sh      ← repo-scoped runner
└── deploy-repo/
    └── testing/run-all.sh      ← repo-scoped runner
```

Each repo has its own master runner. The primary repo's runner is the "run everything" entry point and may invoke sibling repo runners for cross-repo regression. Cross-repo integration tests live in the primary repo's `testing/e2e/`.

## Fixtures

### Component-Specific Fixtures

Test data, mock responses, and sample configs used by one component's tests. Live alongside those tests:

```
<component>/tests/fixtures/
├── sample_config.yaml
└── mock_api_response.json
```

### Cross-Component Fixtures

Shared test data used by multiple components or by e2e tests. Live at the repo level:

```
testing/fixtures/
└── common/
    └── sample_project_config.yaml
```

### Rules

- Component fixtures go in `<component>/tests/fixtures/` — not inline in test files, not in `/tmp/`, not in the component's source directory
- Cross-component fixtures go in `testing/fixtures/` — used sparingly, most fixtures should be component-scoped
- Fixture files should be committed — they're part of the test suite, not ephemeral data

## Ansible Role Testing

Ansible roles have a distinct testing pattern from application code. The industry standard is **Molecule** — it's the Ansible equivalent of pytest. Every mature Ansible codebase uses it.

### The Ansible Testing Pyramid

| Level | What | Tools | Infra needed | Equivalent to |
|---|---|---|---|---|
| **Static analysis** | YAML lint + Ansible best practices | `yamllint`, `ansible-lint` | None | Unit tests |
| **Syntax check** | Playbook/role parsing | `ansible-playbook --syntax-check` | None | Unit tests |
| **Molecule** | Role functional testing + idempotence | `molecule test` | Docker or real VMs | Integration tests |
| **Playbook integration** | Full playbook execution against staging | Manual or CI | Staging environment | E2E tests |

### Molecule Directory Structure

Every Ansible role should have a molecule directory, even if the scenario can't run yet. The directory IS the commitment to test — without it, molecule testing gets perpetually deferred.

```
<role>/
├── tasks/
│   └── main.yml
├── defaults/
│   └── main.yml
├── handlers/
│   └── main.yml
└── molecule/
    └── default/
        ├── molecule.yml       # driver config, platforms, provisioner
        ├── converge.yml       # playbook that runs the role
        ├── verify.yml         # assertions (Testinfra or Ansible)
        └── prepare.yml        # optional pre-test setup
```

### The Molecule Test Sequence

`molecule test` runs these steps in order:
1. **create** — spin up test infrastructure (container, VM, or delegated)
2. **prepare** — run pre-test setup (install dependencies, configure state)
3. **converge** — run the role against the test infrastructure
4. **idempotence** — run the role AGAIN, assert zero changes (this is the most valuable Ansible-specific check — if the second run changes anything, the role isn't idempotent)
5. **verify** — run assertions to check the final state (services running, files created, ports open)
6. **destroy** — tear down test infrastructure

### Driver Selection

The molecule driver determines what infrastructure the tests run against:

| Driver | Use when | Limitations |
|---|---|---|
| **Docker** | App roles (install packages, configure services) | Can't test systemd, networking, kernel operations |
| **Delegated** | Infrastructure roles (Proxmox, K3s, networking) | Requires real VMs to be provisioned externally |
| **Vagrant/libvirt** | Roles that need full VM behavior | Slower, requires hypervisor on test host |

**Infrastructure roles** (provisioning VMs, bootstrapping clusters, configuring network overlays) **cannot be meaningfully tested in Docker.** Use the delegated driver with real VMs when available. Until then, lint + syntax + molecule scaffolding is the correct baseline.

### When Infrastructure Isn't Available

For infrastructure roles that need real VMs or clusters to test:

1. **Scaffold the molecule directory** — create `molecule/default/` with `molecule.yml`, `converge.yml`, and `verify.yml` that describe WHAT should be tested even if it can't run yet
2. **Set the driver to `delegated`** and document what infrastructure is needed in `molecule.yml`
3. **Lint + syntax check NOW** — this is the minimum that runs without infrastructure
4. **Document the gap** — "molecule scenario scaffolded, requires VLAN 105 VMs to execute, targeted for Sprint N"

The scaffolding ensures the test plan is captured in code, not just in a planning doc. When infrastructure becomes available, the scenario is ready to fill in — converge and verify steps already outline what to check.

### How Molecule Maps to the Three-Tier Hierarchy

| Hierarchy tier | Ansible equivalent | Runner |
|---|---|---|
| Tier 1: Master runner | `testing/run-all.sh` discovers ansible suite | `testing/run-all.sh` |
| Tier 2: Suite runner | `testing/suites/ansible.sh` — runs lint, syntax, molecule | `testing/suites/ansible.sh` |
| Tier 3: Component tests | Per-role `molecule/default/` scenarios | `molecule test -s default` |

The ansible suite runner should support multiple levels:
- `./testing/run-all.sh unit infra` — lint + syntax only (fast, no infra)
- `./testing/run-all.sh integration infra` — molecule scenarios (needs infra)

### Ansible-Specific Red Flags

- **Role without `molecule/` directory** — either scaffold it or document why testing is deferred
- **Molecule scenario with no verify step** — converge without assertions proves nothing; it just proves the role doesn't crash
- **No idempotence check** — the most common Ansible bug is non-idempotent roles (second run changes state). Molecule catches this automatically if configured
- **Lint disabled or heavily suppressed** — `# noqa` on every task is a smell; fix the warnings instead
- **`command`/`shell` tasks without `changed_when`** — these always report "changed" and break idempotence checks
- **Testing against localhost only** — roles that configure networking, multi-node clusters, or cross-host communication need multi-node molecule scenarios

## Integration With Workflows

### What Autonomous Workflows Must Do

When a workflow (revision-major, build-phase) creates tests during implementation:

1. **Place test files in the standard hierarchy** — follow the project's testing standard
2. **Verify discovery** — run the component suite to confirm the test is found
3. **Run scoped regression** — new tests pass → component suite passes
4. **Do NOT create runner scripts** outside `testing/suites/` — use existing framework runners
5. **Do NOT place tests in ad-hoc locations** — no `scripts/test_*.py`, no one-off verification scripts using test_ prefixes

### What Autonomous Workflows Must NOT Do

- Run the full global suite (that's for sprint-end regression)
- Create test infrastructure without following the project's testing standard
- Place tests outside the standard hierarchy "temporarily"
- Rename management commands or utilities to have test_ prefixes (these cause false discovery)

## Red Flags

Watch for these anti-patterns when reviewing test organization:

1. **Tests alongside source** (in non-Go projects) — should be in `<component>/tests/`
2. **No `tests/` directory convention** — tests scattered in random locations
3. **Ad-hoc runner scripts** — multiple test runners that don't compose into a master runner
4. **Tests that only run in CI** — if you can't run them locally, they're hard to debug
5. **Undiscoverable tests** — files named `check_*.py` or `verify_*.py` that are really tests but don't follow the naming convention
6. **Management commands named `test_*`** — Django and similar frameworks have CLI utilities that start with `test_` but aren't tests. These cause false discovery and must be renamed.
7. **Tests in `/tmp/` or ephemeral locations** — created during a workflow run and lost when the worktree is cleaned up
8. **No master runner** — you can run individual test files but there's no "run everything" command
9. **Massive fixtures inline** — large data structures hardcoded in test files instead of loaded from fixture files
10. **Ansible roles without molecule directories** — every role should have at minimum a scaffolded `molecule/default/` even if the scenario can't run yet
11. **Lint-only Ansible testing treated as permanent** — lint + syntax is the starting point, not the finish line. Molecule scenarios are the target for every role with substantive logic
