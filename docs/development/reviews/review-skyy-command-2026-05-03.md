# Workflow Review — skyy-command — 2026-05-03

**Source repo:** `/opt/skyy-net/skyy-command`
**Source machine:** `skyy-net`
**Analysis date:** 2026-05-03
**Logs analyzed:** 15 runs, 2026-04-26 through 2026-05-02

## Runs Analyzed

- **Count:** 15 logs (all terminated `result: success`, `is_error: false`)
- **Date range:** 2026-04-26 22:32 → 2026-05-02 21:20
- **Workflow types:** `revision-major` (12), `build-phase` (2), `revision` (1)
- **Repo:** `/opt/skyy-net/skyy-command`
- **Prior review on this repo:** `review-2026-04-24-skyy-command.md` (last 18 completed runs, 2026-04-17 → 2026-04-24)

### Aggregate metrics

| metric | this period | prior review |
|---|---|---|
| avg turns / run | 143 | 133 |
| avg cost / run | $17.65 | $16.53 |
| total cost across runs | $264.74 | $297.50 |
| max observed context window | 353,350 tokens (`revision-major-20260428-193939`) | 369,244 |
| failing-tool-result events total | 79 (across 15 runs) | 78 (across 18 runs) |
| sub-agent invocation pattern | `code-reviewer` + `refactoring-evaluator` + `standards-auditor` (+ optional `Explore` up-front, 2 runs) | same |
| prompt-cache read ratio | 0.95 – 0.99 (excellent) | 0.93 – 0.99 |

Trend: error density per run is ticking up modestly (5.3 errors/run vs 4.3 prior), driven primarily by two new patterns (HC-1 and HC-3 below). All runs still completed successfully and average cost is essentially flat.

---

## High-Confidence Findings

### HC-1 — `.claire/` typo for `.claude/` in worktree paths (27 events, 5 runs) — NEW

**Evidence:** The agent fabricates the worktree path `/opt/skyy-net/skyy-command/.claire/worktrees/<name>/...` instead of `/opt/skyy-net/skyy-command/.claude/worktrees/<name>/...`. Every such Read/Grep/Glob fails with `Path does not exist: /opt/skyy-net/skyy-command/.claire/worktrees/...`.

| run | `.claire` events |
|---|---|
| `revision-major-20260430-004350` | 9 |
| `revision-major-20260427-122958` | 5 |
| `revision-major-20260427-005902` | 3 |
| `revision-major-20260429-141313` | 2 |
| `revision-major-20260426-223228` | 2 |

Sample:
```json
Read {"file_path": "/opt/skyy-net/skyy-command/.claire/worktrees/revision-major-20260430-004350/lib/temporal/tests/integration/tailscale/test_baseline_push_scenarios.py"}
Grep {"path": "/opt/skyy-net/skyy-command/.claire/worktrees/revision-major-20260430-004350/lib/temporal/tests", "pattern": "get_event_loop|new_event_loop"}
```

**Root cause hypothesis:** Model-side substitution error when generating long absolute paths. `.claude` and `.claire` differ by one character; the model is one-shotting the path from memory rather than tab-completing or echoing back what it read. Notably, this typo was completely absent in the prior review's 18 runs — it has emerged since 2026-04-26.

**Recommendation:**
1. Add an explicit rule to the workflow kickoff preamble: "The worktree directory is `.claude/worktrees/`, not `.claire/`. Always use relative paths from the worktree root (e.g., `lib/temporal/...`) instead of typing the full absolute path."
2. Consider a path-rewrite hook that catches `.claire/` in tool inputs and rewrites it to `.claude/` (cheap insurance — single regex).
3. The agent should prefer relative paths (`lib/temporal/...`) over absolute paths once it knows the worktree CWD; this kills the bug class entirely because relative paths don't include `.claude`.

**Impact:** 27 events × ~1k tokens per error round-trip ≈ 27k tokens of pure waste. Concentrated in `revision-major-20260430-004350` (9 events, 10 total errors in that run — most of its noise).

---

### HC-2 — Stale path assumptions: `cd <subdir>: No such file or directory` (80 events, 9 runs) — NEW

**Evidence:** The agent issues `cd backend && ...`, `cd lib/temporal && ...`, `cd components/temporal && ...` etc. and the subdirectory does not exist (typically because the repo restructure renamed `components/temporal` → `lib/temporal`, or because the agent is already inside a subdirectory and shell state is reset between Bash calls).

Top occurrences:
- `revision-major-20260429-180014`: `cd: backend: No such file or directory` and `cd: components/temporal: No such file or directory` repeated; `ls: cannot access '/opt/skyy-net/skyy-command/lib/'` (testing bare `lib/` from wrong CWD)
- `revision-major-20260430-232927`: `cd: lib/temporal: No such file or directory` (called from inside `lib/temporal/`)
- `revision-major-20260427-130712`, `revision-major-20260427-122958`, `revision-major-20260429-141313`: `cd: components/temporal: No such file or directory` (path no longer exists after the rename)
- `revision-major-20260426-223228`: `cd: backend: No such file or directory` (legacy path)

**Root cause:** Two distinct sub-causes:
1. **Stale repo layout in model memory.** `components/temporal` was renamed to `lib/temporal` and `backend/` is no longer a top-level directory in some contexts. The model still emits the old paths from training/prior-conversation memory.
2. **Bash CWD reset between turns.** Shell state does not persist across Bash calls. The agent runs `cd lib/temporal && pwd`, gets a result, then on the next turn issues `cd lib/temporal && pytest ...` from a CWD that is *already* `.../lib/temporal`. This mostly looks benign because `&&` chains it, but when the agent writes a bare `cd backend` (no chain) it produces a stranded `cd` followed by a separate command that fails because the directory wasn't switched.

**Recommendation:**
1. Add to the workflow preamble: "`cd` does not persist between Bash calls — every Bash command starts at the worktree root. Either chain with `&&` in a single call, or use absolute paths."
2. Stack Reference / repo-layout cheat sheet at workflow start: "`lib/temporal/` is the live path. `components/temporal/` was renamed; references to it are stale."
3. Lower priority: detect bare `cd` followed by unrelated Bash and warn the agent.

**Impact:** 80 events × ~500 tokens per failed shell round-trip ≈ 40k tokens. Concentrated in 5 runs that account for 60% of the events.

---

### HC-3 — "File has not been read yet" Edit/Write-before-Read errors (24 events, 7 runs) — RECURRING

**Evidence:** `<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>`

Per-run counts: `revision-major-20260430-232927` (3), `revision-major-20260429-180014` (4), `revision-major-20260430-004350` (2), `revision-major-20260427-145357` (1), `revision-major-20260426-223228` (1), and others.

Variant: `<tool_use_error>File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.</tool_use_error>` — 2 events in `revision-major-20260427-130712`.

This pattern was flagged in the prior review (HC-3 there: 17 events / 10 runs). It now appears at 24 events / 7 runs — slightly worse per-run intensity but in fewer runs. The recommendation from the prior review (Read again after autoformatter / Read-immediately-before-Edit) was not implemented.

**Recommendation:** Reiterate from prior review and elevate priority:
1. Bake into the system preamble: "Before any Edit or Write to an existing file, the most recent Read of that file must be in this turn or the previous turn — never older. If a hook or formatter may have rewritten the file (after `git checkout`, `ruff format`, test runs, codemods), Read again immediately before Edit."
2. The "modified since read" variant is a hook/formatter race — investigate whether a `pre-edit` hook is running `ruff format` and rewriting the file the agent just read.

**Impact:** 24 wasted Edit attempts × (1 forced Read + retry Edit) ≈ 48 wasted turns ≈ 3% of turn budget over the 15-run window.

---

## Medium-Confidence Findings

### MC-1 — `pytest` missing in invoked Python env (6 events, 3 runs) — NEW

**Evidence:**
- `revision-major-20260430-232927`: `/home/puma/miniconda3/envs/skyy-net/bin/python ... ModuleNotFoundError: No module named 'pytest'`
- `revision-major-20260430-143306`: same — 2 events
- `revision-major-20260429-180014`: `/home/puma/miniconda3/bin/pytest` (returned the path but the next call failed with `No module named 'pytest'`)

The agent assumes `pytest` is installed in the active conda env but it is not. After a few failures the agent typically pivots to running tests via `testing/run-all.sh` (the master runner) which works.

**Recommendation:**
1. Add to skyy-command CLAUDE.md: "Tests are run via `testing/run-all.sh`, not by invoking `pytest` directly. The `skyy-net` conda env does not have `pytest` as a top-level binary."
2. Or: install `pytest` in the `skyy-net` conda env so the agent's first instinct works. Lower-friction than retraining the agent's habits.

**Needs:** confirmation of which option the user wants — install pytest in the env, or document the run-all.sh route.

**Impact:** 6 wasted Bash round-trips × ~1k tokens ≈ 6k tokens. Low absolute waste but creates a confused "tests don't work" stretch in the run.

---

### MC-2 — File content exceeds 25k token cap (8 events, 3 runs) — UPTICK

**Evidence:** `File content (XXXXX tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters...`
- `build-phase-20260430-231525`: 32,146-token file
- `build-phase-20260428-213627`: 28,025-token file (×2)
- `revision-major-20260427-005902`: 25,730-token file

Prior review: 4 events in 3 runs. Current: 8 events in 3 runs — modest uptick. The CLAUDE.md guidance ("for known-large files use limit:200 on first read") is partially working but not enforced.

**Recommendation:** Reiterate the prior review's MC-2 recommendation — curate a "known-large" allowlist in the workflow kickoff with explicit initial-read budgets. Top offenders this period appear to be Helm values files and the cluster_provision module as it has grown.

---

### MC-3 — Hot unbounded re-reads of the same file (every run) — IMPROVED FROM PRIOR

**Evidence (max same-file unbounded reads in this period vs prior):**

| run | top file | reads (this period) | prior period peak |
|---|---|---|---|
| `revision-major-20260427-122958` | `install_k3s.py` | 5 | 17 (`cluster_provision_helper.py`) |
| `revision-major-20260430-232927` | `activity_result.py`, `_common.py` | 4 each | |
| `build-phase-20260430-231525` | 4 different files | 4 each | |

The peak per-file count dropped from 17x to 5x — meaningful improvement, but still 4–5x on multiple runs every cycle. The 3-or-more-times-unbounded pattern persists in essentially every multi-hundred-turn run.

**Recommendation:** Same as prior review HC-2 — "after the first full read of a file, subsequent reads must use offset+limit or Grep." The improvement suggests the message is partially landing but is not yet hard discipline.

**Impact:** Reduced from "single largest preventable token sink" (prior review) to a meaningful but not dominant cost. Good trajectory.

---

### MC-4 — Permission-denied on `sudo` and `rm -rf` (12 events, 3 runs)

**Evidence:**
- `revision-major-20260427-145357`: 3 consecutive `sudo docker images` denials, then the run aborted at 25 turns / $1.85. Effectively a wasted invocation — the agent could not get past the auth wall.
- `revision-20260428-213512`: 2 `sudo apt-get install -y bats` denials — the agent then pivoted to a different approach.
- `revision-major-20260429-180014`: 1 `Permission to use Bash with command rm -rf logs && git status --short has been denied` (`rm -rf` triggers the permission gate even in `bypassPermissions` mode).

**Recommendation:**
1. Workflow preamble: "Do not invoke `sudo` — these workflows run unprivileged. If an inspection requires `sudo` (e.g., `docker images` from a non-docker-group user), state the limitation and proceed without it."
2. For `rm -rf`, either pre-allow specific patterns (`rm -rf logs`, `rm -rf .pytest_cache`) or have the agent use `git rm` / individual deletions.
3. The aborted 25-turn run is a wasted-invocation case worth attention — the workflow burned $1.85 and produced nothing because the first action was a forbidden `sudo`.

**Needs:** clarification on whether sudo should be allowed in any workflow context. If never, this becomes a hard rule in the preamble.

---

## Low-Confidence Findings

### LC-1 — InputValidationError on tool param names (4 events, 2 runs) — IMPROVED

Down from 12 events / 7 runs in the prior review to 4 / 2 here:
- `Grep(file_path=...)` instead of `path=` — `build-phase-20260430-231525`, `build-phase-20260428-213627`. Same bug, much rarer.

Watch-for: whether this drifts back up; if so, the prior recommendation (single-sentence guard in preamble) becomes worth implementing.

### LC-2 — `.claude/worktrees` doubled-prefix typo

`build-phase-20260428-213627`: `Path does not exist: /opt/skyy-net/skyy-command/.claude/worktrees/build-phase-phase-20260428-213627/...` — doubled `phase-phase` segment. One-off observation. Watch-for: whether path duplication becomes a pattern.

### LC-3 — Cancelled parallel tool calls (4 events, 1 run)

`revision-major-20260427-130712` saw 4 `<tool_use_error>Cancelled: parallel tool call Bash(...) errored` events. Appears to be a runtime cancellation (one parallel call errored, sibling calls cancelled). Single-run observation.

### LC-4 — Aborted micro-run (`revision-major-20260427-145357`)

25 turns, $1.85, 3 `sudo` permission denials, then terminated successfully. This run produced minimal work and ended with no PR-meaningful output. Worth investigating whether the workflow should detect "burned ≥3 permission denials" and surface that loud rather than terminating cleanly.

### LC-5 — Stage-2 test failures within run not reflected in final result

`build-phase-20260428-213627` and `revision-major-20260428-193939` both had `FAILED components/temporal/tests/unit/test_fetch_cloud_image.py::...` mid-run, but the workflow continued and finished `result: success`. This may be intentional (the agent fixed the failures before finalizing) — verify the final tests passed before merging the resulting PR.

---

## Patterns Resolved Since Last Review

Comparing against `review-2026-04-24-skyy-command.md`:

| prior finding | status |
|---|---|
| HC-1: InputValidationError (wrong param names — 12 events / 7 runs) | **Mostly resolved.** Down to 4 / 2 (LC-1 here). Trajectory good. |
| HC-2: Unbounded re-reads of hot files (peak 17×) | **Improved, not resolved.** Peak dropped to 5×; still occurs in nearly every run (MC-3 here). |
| HC-3: File-not-read-yet errors (17 events / 10 runs) | **Not resolved.** Now 24 / 7 — same per-period total, more concentrated (HC-3 here). |
| MC-2: Reads >25k tokens (4 / 3) | **Slight regression.** Now 8 / 3 (MC-2 here). |
| MC-1: Low parallel-tool-call usage (median 13%) | **Slight improvement.** Median this period ~16%, with one run at 40% (`revision-major-20260426-223228`). |

---

## New patterns since last review

- **HC-1 (`.claire/` typo)** — completely absent before 2026-04-26, present in 5 of the last 7 days' runs. Sharp emergence; treat as priority.
- **HC-2 (stale `cd <subdir>` references to `components/temporal`, `backend/` etc.)** — 80 events. Tied to repo restructure timing.
- **MC-1 (pytest missing in env)** — 6 events. Tied to test verification habits, not in prior review.

---

## Metrics — detailed breakdown

### Failure-type frequency (across 15 runs, 79 total `is_error` tool-results)

| pattern | count | runs affected | trend vs prior |
|---|---|---|---|
| `cd: ... No such file or directory` (stale paths) | 80* | 9 | NEW |
| `.claire/` path typo | 27 | 5 | NEW |
| `File has not been read yet` | 24 | 7 | recurring |
| `File does not exist` | 16 | 5 | recurring |
| Permission denied (sudo, rm -rf) | 12 | 3 | recurring |
| `exceeds maximum allowed tokens` | 8 | 3 | uptick |
| `No module named pytest` | 6 | 3 | NEW |
| `InputValidationError` | 4 | 2 | improved |
| Cancelled parallel tool call | 4 | 1 | new (single run) |
| `File has been modified since read` | 2 | 1 | recurring |
| `String to replace not found` | 2 | 1 | recurring |
| `EISDIR` | 2 | 1 | recurring |

*`cd: ... No such file or directory` count includes shell stderr lines; not all are 1:1 with `is_error: true` tool results because some appear inside successful Bash calls (compound commands where the `cd` failed but a later `||` recovered).

### Per-run summary

| log | turns | $ | err | max-ctx | parallel% |
|---|---|---|---|---|---|
| `revision-major-20260502-212017` | 215 | $25.63 | 3 | 286k | 11% |
| `revision-major-20260430-232927` | 230 | $26.75 | 9 | 274k | 12% |
| `build-phase-20260430-231525` | 119 | $15.69 | 3 | 254k | 14% |
| `revision-major-20260430-143306` | 82 | $7.31 | 5 | 164k | 20% |
| `revision-major-20260430-004350` | 172 | $20.99 | 10 | 289k | 27% |
| `revision-major-20260429-180014` | 240 | $26.59 | 10 | 261k | 16% |
| `revision-major-20260429-141313` | 139 | $23.77 | 5 | 334k | 15% |
| `build-phase-20260428-213627` | 127 | $20.01 | 7 | 309k | 16% |
| `revision-20260428-213512` | 87 | $7.12 | 3 | 174k | 10% |
| `revision-major-20260428-193939` | 193 | $29.50 | 4 | 353k | 18% |
| `revision-major-20260427-145357` | 25 | $1.85 | 3 | 85k | 0% |
| `revision-major-20260427-130712` | 135 | $16.44 | 5 | 285k | 24% |
| `revision-major-20260427-122958` | 86 | $8.90 | 2 | 182k | 12% |
| `revision-major-20260427-005902` | 209 | $27.96 | 4 | 311k | 17% |
| `revision-major-20260426-223228` | 89 | $6.23 | 6 | 125k | 40% |

### Trends

- Cost per run is essentially flat: median ~$20.01 (this period) vs ~$15 (prior). Slight uptick driven by 4 runs in the 200+ turn / $25+ band.
- All 15 runs terminated successfully. No infrastructure failures.
- The two most error-dense runs (`revision-major-20260430-004350`: 10 errors, 9 of them `.claire` typos; `revision-major-20260429-180014`: 10 errors, mix of stale paths and File-not-read) account for ~25% of total errors.
- Sub-agent invocation pattern is now extremely consistent: every revision-major / build-phase run uses the canonical `code-reviewer + refactoring-evaluator + standards-auditor` triple. The single 25-turn outlier (revision-major-20260427-145357) skipped the trio because it aborted before reaching review stage.
- Parallelism: median ~16% (up from 13%). One run hit 40% — `revision-major-20260426-223228`, which spent most of its turns in Read+Grep batched discovery.

---

## Summary

The harness is healthy: every run terminated `result: success`, cache-read ratio is excellent (95–99%), and prior review's top pattern (InputValidationErrors) has dropped 67%. The **top priority** this cycle is HC-1 — the `.claire/` typo emerged sharply since 2026-04-26, accounted for 27 events across 5 runs, and is the single dominant noise source in the worst-affected run (9 of 10 errors in `revision-major-20260430-004350`); the cheapest fix is a one-sentence preamble rule plus encouraging relative paths from the worktree root. **Second priority** is HC-2 — stale `cd <old-path>` references (80 events) tied to the `components/temporal` → `lib/temporal` rename — best addressed by a repo-layout cheat sheet at workflow start. The carry-over HC-3 (Read-before-Edit/Write) was not addressed since the prior review and now needs a hard-discipline rule, not just guidance.
