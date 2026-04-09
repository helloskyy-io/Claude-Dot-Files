---
name: testing-scaffolding
description: How to set up a test suite from scratch in a new or existing project that doesn't have one yet. Covers framework selection, standard folder structures, and initial configuration for Python, Go, Rust, TypeScript, and JavaScript. Use ONLY when scaffolding new test infrastructure — for daily test work, use testing-methodology instead.
---

# Testing Scaffolding

This skill is for the rare scenario of **setting up tests in a project that doesn't have them yet**. For daily test work (writing, running, evaluating, fixing), use `testing-methodology` instead.

## Before Scaffolding

1. **Verify tests don't already exist.** Check for any test directories, test files, test config, or test scripts in `package.json` / `Makefile`. If ANY testing infrastructure exists, use `testing-methodology` to extend it instead of replacing it.

2. **Check for project standards.** If `docs/standards/testing.md` exists in the project, follow it exactly. Project standards override these generic defaults.

3. **Ask the user about framework preference.** Multiple valid choices exist per language. Don't guess — confirm before scaffolding.

## Framework Selection

### Python
- **pytest** — modern default, fixture system, great plugin ecosystem. Use this unless there's a specific reason not to.
- **unittest** — standard library, verbose, class-based. Use for projects that want zero dependencies.

### JavaScript / TypeScript
- **Vitest** — modern default, Vite-native, fast. Use for new projects.
- **Jest** — mature, widely used, slower. Use for legacy projects or when ecosystem specifically requires it.
- **Mocha + Chai** — older, more configurable. Rarely the right choice today.
- **Playwright** / **Cypress** — for E2E tests specifically (separate from unit test framework).

### Go
- **Built-in `testing` package** — always. Go has one way to test, use it.
- **testify** — adds assertion helpers, optional. Many projects use it.

### Rust
- **Built-in test framework** — always. Cargo has integrated test support.
- **proptest** — for property-based testing (advanced, optional).

### Ruby
- **RSpec** — BDD-style, most common for Rails.
- **Minitest** — simpler, used by the Rails core.

## Folder Structures

### Python

Top-level `tests/` directory mirroring `src/`:

```
project/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       ├── auth.py
│       └── models.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # shared fixtures (pytest auto-discovers)
│   ├── test_auth.py           # mirrors src/mypackage/auth.py
│   └── test_models.py
├── pyproject.toml
└── pytest.ini                 # or [tool.pytest.ini_options] in pyproject.toml
```

**Naming conventions:**
- Test files: `test_<module>.py`
- Test functions: `test_<behavior>()`
- Test classes (optional): `TestClassName`
- Fixtures: `conftest.py` — pytest auto-discovers

**Larger projects:** Nest `tests/` to mirror source structure (`tests/api/test_routes.py`).

**Minimal `pyproject.toml` pytest config:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

**Run:** `pytest` or `pytest tests/test_auth.py::test_login`

### Go

Go tests live **alongside source files** in the same package directory. This is enforced by the toolchain.

```
project/
├── go.mod
├── go.sum
├── auth/
│   ├── auth.go
│   └── auth_test.go           # same package, same directory
├── models/
│   ├── user.go
│   └── user_test.go
├── internal/
│   └── cache/
│       ├── cache.go
│       └── cache_test.go
└── testdata/                  # fixtures, golden files (ignored by go build)
    └── golden/
        └── expected_output.json
```

**Naming conventions:**
- Test files: `<file>_test.go` — must be in the same directory as the code
- Test functions: `TestFunctionName(t *testing.T)`
- Benchmarks: `BenchmarkName(b *testing.B)`
- Examples: `ExampleFunctionName()`
- Table-driven tests are idiomatic — prefer them
- `testdata/` directories are ignored by `go build` — use them for fixtures
- For black-box testing, use `package foo_test` (external test package)

**Run:** `go test ./...` or `go test ./auth/`

### Rust

Inline unit tests plus a top-level `tests/` directory for integration tests.

```
project/
├── Cargo.toml
├── src/
│   ├── lib.rs
│   ├── auth.rs                # unit tests at bottom of this file
│   └── models.rs
└── tests/                     # integration tests (each file is a separate crate)
    ├── auth_integration.rs
    └── common/
        └── mod.rs             # shared test helpers
```

**Naming conventions:**
- Unit tests: `#[cfg(test)] mod tests { ... }` at the bottom of each source file
- Integration tests: separate files in `tests/`, each compiled as its own crate
- Test functions: `#[test] fn test_name() { ... }`
- Shared helpers for integration tests go in `tests/common/mod.rs`

**Run:** `cargo test` or `cargo test --test auth_integration`

### TypeScript / JavaScript

Two dominant patterns. Pick one and be consistent across the project.

**Pattern A — colocated tests (recommended for component-heavy projects):**
```
project/
├── src/
│   ├── auth/
│   │   ├── auth.ts
│   │   ├── auth.test.ts       # colocated with source
│   │   └── auth.mock.ts       # test doubles
│   └── models/
│       ├── user.ts
│       └── user.test.ts
├── package.json
├── vitest.config.ts
└── tsconfig.json
```

**Pattern B — separate test directory:**
```
project/
├── src/
│   ├── auth.ts
│   └── models.ts
├── tests/
│   ├── setup.ts               # global test setup
│   ├── auth.test.ts
│   └── models.test.ts
├── package.json
└── vitest.config.ts
```

**Naming conventions:**
- Test files: `<module>.test.ts` or `<module>.spec.ts`
- Use `describe()` / `it()` or `test()` blocks
- Mocks/fixtures: colocate as `*.mock.ts` or put in `tests/fixtures/`
- E2E tests (Playwright, Cypress): separate `e2e/` directory at project root

**Run:** `npx vitest` or `npx jest`

## Initial Configuration

### Minimum Viable Test Setup

After creating the folder structure, add:

1. **Framework installed** — as a dev dependency
2. **Config file** — minimum needed to run tests
3. **One smoke test** — proves the setup works
4. **Package.json / Makefile script** — standard invocation command
5. **CI integration** (optional at scaffolding time) — can be added later

### Write the First Test
The first test should be a **smoke test** that verifies the most basic functionality works. This proves the setup is correct before writing real tests.

Example (Python):
```python
# tests/test_smoke.py
def test_package_imports():
    import mypackage
    assert mypackage is not None
```

Example (Go):
```go
// auth/auth_test.go
package auth

import "testing"

func TestPackageCompiles(t *testing.T) {
    // This test exists to verify the test infrastructure works.
    // Replace or delete once real tests are added.
}
```

## After Scaffolding

Once the test infrastructure exists:
1. **Switch to `testing-methodology`** for writing actual tests
2. **Document the setup** in `docs/standards/testing.md` for the project
3. **Add test invocation to CI** if not already done
4. **Reference the standards** from the project's `CLAUDE.md`

## General Principles

These apply regardless of language when scaffolding:

1. **Mirror source structure.** Test files should be easy to find from the source file and vice versa.
2. **Follow the language's convention.** Don't fight the toolchain. Go tests go next to the code. Python tests go in `tests/`. Rust unit tests go inline.
3. **Shared fixtures in a dedicated location.** Python: `conftest.py`. Go: `testdata/`. JS/TS: `fixtures/` or `*.mock.ts`. Rust: `tests/common/mod.rs`.
4. **Start minimal.** One smoke test is better than twenty tests for nonexistent functionality.
5. **Install only what you need.** Don't add Jest AND Vitest AND Mocha "just in case."
