---
name: testing
description: Standard testing folder structures and project conventions for multiple languages. Use when setting up tests in a new project, organizing test files, or scaffolding a test suite for Python, Go, Rust, TypeScript, or JavaScript.
---

## Testing Folder Structures by Language

When setting up or organizing tests, follow the standard conventions for each language. These structures reflect community norms and tool defaults — deviating from them usually means fighting the toolchain.

---

### Python

Python projects use a top-level `tests/` directory that mirrors the `src/` package structure. Pytest is the standard runner.

```
project/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       ├── auth.py
│       └── models.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # shared fixtures
│   ├── test_auth.py           # mirrors src/mypackage/auth.py
│   └── test_models.py
├── pyproject.toml
└── pytest.ini                 # or [tool.pytest.ini_options] in pyproject.toml
```

**Conventions:**
- Test files: `test_<module>.py`
- Test functions: `test_<behavior>()`
- Test classes (optional): `TestClassName`
- Fixtures go in `conftest.py` — pytest discovers them automatically
- For larger projects, nest `tests/` to mirror source: `tests/api/test_routes.py`

**Minimal `pyproject.toml` pytest config:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

**Run:** `pytest` or `pytest tests/test_auth.py::test_login`

---

### Go

Go tests live alongside the source files in the same package directory. This is enforced by the Go toolchain — there is no separate test directory.

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

**Conventions:**
- Test files: `<file>_test.go` — must be in the same directory as the code
- Test functions: `TestFunctionName(t *testing.T)`
- Benchmarks: `BenchmarkName(b *testing.B)`
- Table-driven tests are idiomatic — prefer them for multiple cases
- `testdata/` directories are ignored by `go build` — use them for fixtures
- For black-box testing, use `package foo_test` (external test package)

**Run:** `go test ./...` or `go test ./auth/`

---

### Rust

Rust uses inline unit tests (in the same file) plus a top-level `tests/` directory for integration tests. This is built into Cargo.

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

**Conventions:**
- Unit tests: `#[cfg(test)] mod tests { ... }` at the bottom of each source file
- Integration tests: separate files in `tests/`, each compiled as its own crate
- Test functions: `#[test] fn test_name() { ... }`
- Shared helpers for integration tests go in `tests/common/mod.rs`
- Use `assert_eq!`, `assert_ne!`, `assert!` macros

**Run:** `cargo test` or `cargo test --test auth_integration`

---

### TypeScript / JavaScript

TS/JS projects vary more, but the two dominant patterns are a top-level `__tests__/` directory (Jest convention) or colocated `.test.ts` files. Pick one and be consistent.

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
├── vitest.config.ts           # or jest.config.ts
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

**Conventions:**
- Test files: `<module>.test.ts` or `<module>.spec.ts`
- Use `describe()` / `it()` or `test()` blocks
- Vitest is the modern default; Jest for legacy projects
- Mocks/fixtures: colocate as `*.mock.ts` or put in `tests/fixtures/`
- E2E tests (Playwright, Cypress): separate `e2e/` directory

**Run:** `npx vitest` or `npx jest`

---

## General Principles

These apply regardless of language:

1. **Mirror source structure.** Test files should be easy to find from the source file and vice versa. Use the same directory nesting or colocate them.
2. **Follow the language's convention.** Don't fight the toolchain. Go tests go next to the code. Python tests go in `tests/`. Rust unit tests go inline.
3. **One test file per source module.** Don't pile unrelated tests into a single file.
4. **Shared fixtures in a dedicated location.** Python: `conftest.py`. Go: `testdata/`. JS/TS: `fixtures/` or `*.mock.ts`. Rust: `tests/common/mod.rs`.
5. **Name tests for behavior, not implementation.** `test_login_rejects_expired_token` over `test_validate_token_returns_false`.
6. **Keep test setup minimal.** If a test needs 30 lines of setup, extract a helper or fixture — but only when it's used by multiple tests.
