# Workflow Review — skyy-command — 2026-05-09

**Source repo:** `/opt/skyy-net/skyy-command`
**Source machine:** `skyy-net`
**Analysis date:** 2026-05-09
**Logs analyzed:** 5 runs, 2026-05-02 → 2026-05-09 (8-day window)

## Runs Analyzed

- **Count:** 5 logs (all terminated `result: success`, `is_error: false`)
- **Date range:** 2026-05-02 21:20 → 2026-05-09 14:04
- **Workflow types:** `revision-major` (2), `build-phase` (1), `sprint-review` (1), `review-runs` (1)
- **Repo:** `/opt/skyy-net/skyy-command`
- **Prior review on this repo:** `review-skyy-command-2026-05-03.md` (15 runs, 2026-04-26 → 2026-05-02)
- **Note on overlap:** `revision-major-20260502-212017` was the last run in the prior review's window. Re-analyzed here for continuity, but findings unique to it are not double-counted as new evidence.

### Aggregate metrics

| metric | this period (5 runs) | prior review (15 runs) |
|---|---|---|
| total cost | $88.36 | $264.74 |
| avg cost / run (excl. review-runs) | $21.74 | $17.65 |
| avg turns / run (excl. review-runs) | 142 | 143 |
| max observed context window | 307k (`build-phase-20260508-001140`) | 353k |
| total `is_error: true` events | 21 | 79 |
| errors / run | 4.2 | 5.3 |
| prompt-cache read ratio | 0.97 – 0.99 | 0.95 – 0.99 |

The window is short (8 days) and small (5 logs). Confidence ratings below are calibrated for that — most patterns get Medium or Low.

### Per-run summary

| log | type | turns | $ | errors | max-ctx |
|---|---|---|---|---|---|
| `revision-major-20260502-212017` | revision-major | 215 | $25.63 | 3 | 285k |
| `sprint-review-20260503-191820` | sprint-review | 35 | $18.20 | 3 | 251k |
| `review-runs-20260503-132051` | review-runs | 19 | $1.42 | 0 | 90k |
| `build-phase-20260508-001140` | build-phase | 168 | $23.07 | 5 | 307k |
| `revision-major-20260509-140439` | revision-major | 148 | $20.04 | 10 | 288k |

The 2026-05-09 revision-major run is by far the most error-dense (10 errors in 148 turns); excluding it, the other four runs averaged 2.75 errors each.

---

## High-Confidence Findings

### HC-1 — Sequential review-agent dispatch (4/4 multi-agent runs)

**Evidence:** Every multi-agent run in this cycle dispatched its review trio across **three separate assistant messages**, each containing one `Agent` call:

| run | agent dispatch sequence |
|---|---|
| `revision-major-20260502-212017` | code-reviewer → refactoring-evaluator → standards-auditor (3 messages) |
| `revision-major-20260509-140439` | code-reviewer → refactoring-evaluator → standards-auditor (3 messages) |
| `build-phase-20260508-001140` | code-reviewer → refactoring-evaluator → standards-auditor (3 messages) |
| `sprint-review-20260503-191820` | security-auditor → refactoring-evaluator → test-writer (3 messages) |

By framework definition, multiple `Agent` calls in a *single* assistant message run concurrently; calls split across separate messages run sequentially because each message is generated only after the prior tool results return. **0 of 4** multi-agent runs achieved parallel dispatch.

**Context vs. CPI log:** the 2026-05-03 CPI log entry validating prior-cycle work claimed *"Parallel review-agent dispatch is the new norm in 4/5 review-stage runs"* — however that aggregate spanned both `mdc-master-planning` and `skyy-command`. Within the skyy-command sample alone, parallel dispatch has never been observed in available logs (also true in the prior-review's per-run table where parallel% was a tool-call-level metric, not agent-dispatch-level).

**Recommendation:** Add an explicit instruction to the review-stage workflow preamble: *"Dispatch the review trio (code-reviewer, refactoring-evaluator, standards-auditor) in a SINGLE assistant message containing three `Agent` tool calls. Multiple `Agent` calls in one message run concurrently; splitting them across messages forces sequential execution and roughly triples wall time on this stage."* This is a one-sentence prompt-side fix that should immediately move skyy-command to the parallel pattern.

**Impact:** Hard to quantify without per-stage timing breakdown, but parallelizing 3 review agents typically saves 1.5–2× wall time on the review stage. Across 3 review-stage runs/week at this repo, that's a meaningful budget savings.

**Confidence:** High for the observation (4/4 unanimous). Medium for the framing as a "regression" — it's better described as a divergence between repos that has not yet been corrected in skyy-command.

---

## Medium-Confidence Findings

### MC-1 — Path fabrication / repo-layout drift recurring (revision-major-20260509-140439, 7 events)

**Evidence:** In `revision-major-20260509-140439`, the agent emitted absolute paths to files/directories that don't exist at those locations:

| attempted path | error | actual location |
|---|---|---|
| `lib/temporal/helpers/genesis_helper.py` (Read) | File does not exist | `lib/temporal/common/provision/genesis_helper.py` (4× successful reads later) |
| `lib/temporal/helpers/` (Glob) | Directory does not exist | (no `helpers/` dir; helpers live under `common/provision/`) |
| `lib/temporal/scripts/dispatcher_common.sh` (Read) | File does not exist | `lib/temporal/scripts/lib/dispatcher_common.sh` (4× successful reads later) |
| `tests/unit/test_helm_charts.py` (Read ×3, Grep ×1) | File / Path does not exist | `lib/temporal/tests/unit/test_helm_charts.py` (per Testing Standard — tests live in `lib/<name>/tests/<category>/`) |

The pattern is the agent inventing a *plausible-looking* layout from prior conversation memory or general expectation, rather than starting from a Glob/ls to confirm structure. This is the same class as prior review's HC-2 ("stale path assumptions") — a different specific path set, but the same shape.

**Root cause hypothesis:** Model-side path generation from training-data assumptions (`tests/` at repo root is a near-universal Python convention) and stale model memory of intermediate restructure states. The Testing Standard explicitly calls out `lib/<name>/tests/` as the convention for this repo, but that detail wasn't loaded into context for this run.

**Recommendation:** Implement the prior review's deferred recommendation — a **repo-layout cheat sheet** at workflow start. Concretely: a 6–10 line block in the kickoff preamble listing the canonical locations the agent will need most often:

```
Repo layout cheat sheet (skyy-command):
- backend/                Django app (API, ORM, admin UI)
- lib/temporal/           Workflows, helpers (under common/), activities, executors
- lib/temporal/tests/     Pytest tests (unit/, integration/, e2e/)
- lib/temporal/scripts/   Operational scripts; shared lib in scripts/lib/
- deployments/common/     Helm charts
- testing/run-all.sh      Master test runner — use this, not bare pytest
Tests live under lib/<name>/tests/, NOT at repo root.
```

This is a one-shot prompt addition; cost is a few tokens loaded once per run vs. the observed cost of 7 round-trip errors.

**Confidence:** Medium. 7 events concentrated in a single run, but the pattern *class* (path fabrication from prior-state memory) was the dominant noise source in the prior review (80 events). It hasn't been addressed structurally.

---

### MC-2 — Bash CWD persistence not matching the shipped Pattern D rule (1 event, but exact-shape recurrence)

**Evidence:** `revision-major-20260509-140439`:

```
Bash: cd lib/temporal && python3 -m pytest tests/unit/test_helm_charts.py -v --tb=short 2>&1 | tail -40
err:  /bin/bash: line 1: cd: lib/temporal: No such file or directory
```

The system reminder appended `Note: your current working directory is /opt/skyy-net/skyy-command/.claude/worktrees/revision-major-20260509-140439/lib/temporal.` to several immediately-prior tool errors — i.e., the CWD *was already* `lib/temporal`, so `cd lib/temporal` failed.

**Why this is interesting:** CPI cycle shipped **Pattern D — "Bash CWD reset rule"** on commit `e7c8715` (2026-05-03), based on prior-review evidence of 80 events / 9 runs of stale-CWD failures. The shipped rule said: *"every Bash command starts at the worktree root; chain with `&&` or use absolute paths."* The model in 20260509 followed the rule (chained with `&&`) — but the failure message + CWD reminder indicate the CWD did **not** reset to worktree root between calls. Either:

1. The shipped rule's premise is wrong for this repo's harness configuration (CWD persists across Bash calls in this harness), and the rule is now causing the *opposite* error class — chained `cd` from a CWD that already has the target as its leaf.
2. The CWD-persistence behavior is intermittent (e.g., depends on whether earlier Bash calls included `cd`), and the rule covers most cases but not this one.

**Recommendation:**
1. Empirically confirm whether CWD persists across Bash calls in this harness — a 2-line test (`pwd`, then `cd somewhere`, then a separate Bash call `pwd`) would establish ground truth.
2. If CWD persists: revise Pattern D — the rule should be *"track the current Bash CWD across calls; before issuing `cd <subdir>`, confirm you are at the parent. Prefer absolute paths or relative-from-root."* If CWD resets: figure out why this run saw a non-root CWD and patch the gap.
3. Until clarified, leave Pattern D as a CPI watch item — single recurrence after ship, but the recurrence is *exactly* the pattern the rule was supposed to prevent.

**Confidence:** Medium. Single event, but it directly tests a freshly shipped fix. Worth one diagnostic round.

---

## Low-Confidence Findings

### LC-1 — `sprint_1_loose_ends.md` 25K-token Read overflow (2 events, 1 run)

`sprint-review-20260503-191820` had 2 oversize-Read failures: 31,033 tokens and 27,903 tokens — same file (`mdc-master-planning/development/common/loose_ends/sprint_1_loose_ends.md`) read twice unbounded. This is the long-running **Pattern A** (deferred in the 2026-05-03 CPI cycle).

**Watch-criteria check:** the deferral set the trigger as *"if persists at >2× current rate after project-side allowlist work lands."* Project-side allowlist hasn't landed yet, so the watch-criteria is **not** evaluable. Continue to defer; no action.

**Watch-for:** if a follow-up sprint-review run hits the same file with the same failure shape, that's project-side allowlist work justified. Recommend file owner add `sprint_1_loose_ends.md` to the known-large-file list in the relevant CLAUDE.md.

---

### LC-2 — Build-phase one-off Bash failures (`build-phase-20260508-001140`, 3 events)

Three Bash failures in this single run, all idiosyncratic:

1. `git mv lib/temporal/activities/1password lib/temporal/activities/onepassword` → `fatal: source directory is empty` — agent attempted a rename before creating files in the source dir.
2. `head -40 lib/temporal/file_structure.txt` → `No such file or directory` — file_structure.txt actually lives at `docs/file_structure.txt` per the `update-file-structure` skill convention.
3. `ls docker/images/workers/provision/ && ... ls lib/temporal/activities/tailscale/tests/ 2>/dev/null` → exit 2 (the second `ls` swallowed via redirect; non-zero from compound).

These look like first-attempt-then-correct patterns, not systemic. Watch-for: whether `file_structure.txt` path confusion recurs (it would suggest CLAUDE.md should reference `docs/file_structure.txt` as canonical location).

---

### LC-3 — `rm -rf` permission denial gated correctly (1 event)

`revision-major-20260509-140439` requested `rm -rf .../docker/images/workers/bootstrap && rm .../temporal-worker.yaml` — denied at the permission gate. Agent correctly pivoted to surfacing the deletion as a deferred operator action in the PR (the run completed `result: success`). This is the gate working as intended; no action.

---

### LC-4 — Invalid script arg caught by validation (1 event)

`rebuild_worker.sh --workername bootstrap` rejected with `[ERROR] Invalid --workername: bootstrap. Valid values: provision, das`. Caught by the parameterization commit `5393b90` (recent — `chore(rebuild_worker): parameterize for all 3 worker classes`). Validation working as designed.

---

## Patterns Resolved Since Last Review

Comparing against `review-skyy-command-2026-05-03.md`:

| prior finding | prior count | this period | status |
|---|---|---|---|
| HC-1: `.claire/` typo for `.claude/` | 27 / 5 | 0 / 0 | **RESOLVED.** Pattern E ship (2026-05-03, e7c8715) is holding. |
| HC-2: Stale `cd <subdir>` / wrong-path failures | 80 / 9 | 1 / 1 + 7 / 1 path-fabrications (MC-1) | **PARTIAL.** Direct shape (`cd: components/temporal: No such file or directory`) extinct; pattern class survives as path fabrication and CWD-after-Pattern-D mismatch (MC-1, MC-2). |
| HC-3: Read-before-Edit / "File has not been read yet" | 24 / 7 | 3 / 2 | **SUBSTANTIALLY IMPROVED.** Pattern B ship (2026-05-03, e7c8715) reduced to ~12% of prior rate. |
| MC-1: `pytest` missing in invoked Python env | 6 / 3 | 0 / 0 (sprint-review pivoted to `testing/run-all.sh`) | **RESOLVED in this sample.** Watch-for in larger samples. |
| MC-2: File content >25K token cap | 8 / 3 | 2 / 1 | **STABLE.** Same single-file regime (Pattern A deferred). |
| MC-3: Hot unbounded re-reads (peak 5×) | peak 5× | peak 4× | **MARGINAL IMPROVEMENT.** sprint-review-20260503 had 0 unbounded reads / 14 bounded reads — exemplary. |
| MC-4: `sudo` and `rm -rf` permission denials | 12 / 3 | 1 / 1 (`rm -rf` only) | **IMPROVED.** No `sudo` attempts this period. |
| LC-1: InputValidationError on tool params | 4 / 2 | 0 / 0 | **RESOLVED in this sample.** |

Three Pattern-named ships (B, D, E) from the 2026-05-03 CPI cycle:
- **Pattern B (Read-before-Edit hardening):** clear win (24/7 → 3/2).
- **Pattern E (relative-paths / no `.claire/`):** clear win (27/5 → 0/0 in tool inputs).
- **Pattern D (Bash CWD reset rule):** unclear — see MC-2. The original 80-event shape is gone but a new shape appeared exactly where the rule's premise applies.

---

## Recurrences from CPI Decisions Log

Cross-referenced against `/opt/skyy-net/claude-dot-files/docs/development/cpi-decisions.md`:

- **Pattern A — 25K-token Read overflow** — DEFERRED at review-runs cycle 2026-05-03; **recurring this cycle (2 events / 1 run, `sprint_1_loose_ends.md`).** Watch-criteria is *">2× current rate after project-side allowlist work lands"* — allowlist work has **not** landed, so the criteria is not yet evaluable. **Disposition: continue to defer; surface to project-side as a candidate for the loose-ends CLAUDE.md's known-large-file list.** (See LC-1.)

- **Pattern C — `find | xargs` whitespace silent data loss** — DEFERRED at review-runs cycle 2026-05-03 (1 event mdc); **NOT recurring this cycle.** No action.

- **TS-1 / TS-2 / TS-3 / WI-1 / WI-2 / WI-3** (sprint-review run #1 deferrals) — these were single-occurrence first-run friction items deferred pending sprint-review run #2. Sprint-review has not run a second time yet (the only sprint-review log in this window is the *original* run #1). Watch-criteria not evaluable. **Disposition: continue to defer; ship watch-list reconsideration after sprint-review run #2 lands.**

- **PM3 4-agent parallel review at N=2** (deferred from 2026-05-08 ad-hoc reflection) — N=3 watch-criteria cited "if standards-architect consistently catches misses the other three agents wouldn't." This cycle's standards-auditor (not standards-architect) findings were not exceptional in any of the 3 standards-auditor runs. **Disposition: hold at N=2; not advanced this cycle.**

- **Sequential review-agent dispatch (HC-1 above)** — NOT a prior CPI item; new this cycle. The prior CPI log validation note about "parallel as new norm in 4/5 runs" was an aggregate across both repos, and this cycle's evidence shows skyy-command sits at 0/4 alone. **Recommend logging as new finding for next CPI cycle.**

---

## Metrics — detailed breakdown

### Failure-type frequency (across 4 runs producing errors; excludes 0-error review-runs log)

| pattern | count | runs affected | trend vs prior |
|---|---|---|---|
| `File does not exist` (path fabrication) | 6 | 2 | recurring (different shape from prior `cd` failure class) |
| `Path does not exist` / `Directory does not exist` | 3 | 1 | recurring |
| `File content (XXk tokens) exceeds maximum` | 2 | 1 | stable (Pattern A deferred) |
| `File has not been read yet` | 3 | 2 | substantially improved (24/7 → 3/2) |
| `cd: ... No such file or directory` | 1 | 1 | improved (80/9 → 1/1, but see MC-2) |
| Permission denied (`rm -rf`) | 1 | 1 | improved (12/3 → 1/1) |
| Bash exit-code non-zero (workflow logic, not infra) | 4 | 3 | mixed (3 idiosyncratic in build-phase, 1 worker validation rejection) |
| `Cancelled` parallel tool call | 2 | 1 | flat (1 run only, prior cycle also 1 run) |

### Sub-agent invocation pattern

- Every multi-agent run used a 3-agent trio. revision-major / build-phase used the canonical `code-reviewer + refactoring-evaluator + standards-auditor`. sprint-review-20260503 used `security-auditor + refactoring-evaluator + test-writer` (sprint-review's distinct trio per its workflow design).
- All 4 multi-agent runs dispatched **sequentially** (one Agent call per assistant message) — see HC-1.

### Read discipline

- `revision-major-20260509-140439`: 40 unbounded / 28 bounded — peak 4× same-file unbounded.
- `build-phase-20260508-001140`: 62 unbounded / 18 bounded — peak 4× same-file unbounded.
- `revision-major-20260502-212017`: 30 unbounded / 61 bounded — peak 3× same-file unbounded.
- `sprint-review-20260503-191820`: 0 unbounded / 14 bounded — **exemplary**; offset+limit used on every Read.

The sprint-review log is worth highlighting as a positive exemplar: every Read used `offset` + `limit`, suggesting the workflow's preamble or skill-side instruction is enforcing bounded discovery in a way the revision-major / build-phase preambles aren't.

### Trends

- All 5 runs terminated `result: success`.
- Cost per run is essentially flat vs prior period (~$22 median).
- Cache-read ratio remains excellent (97–99%).
- The 2026-05-09 revision-major run alone accounts for nearly half the cycle's errors (10 of 21).

---

## Summary

The harness is healthy: every run terminated successfully, three of five Pattern-named ships from the prior CPI cycle (B, D-partial, E) are validating well. **Top priority** this cycle is HC-1 — sequential review-agent dispatch in 4/4 multi-agent runs is a one-sentence preamble fix that would significantly reduce review-stage wall time (multiple Agent calls in a single message run concurrently; this cycle never used that pattern). **Second priority** is MC-1 — path fabrication recurring in the 2026-05-09 run (7 events) is the same class as prior HC-2 and was supposed to be addressed by a "repo-layout cheat sheet" recommendation that hasn't been implemented; ship it. The Pattern D (Bash CWD reset) recurrence in MC-2 is single-occurrence but tests a freshly shipped rule and is worth a diagnostic round to confirm whether the harness's CWD behavior matches the rule's premise.
