# Workflow Review — mdc-master-planning — 2026-05-09

**Source repo:** `/opt/skyy-net/mdc-master-planning`
**Source machine:** `skyy-net`
**Analysis date:** 2026-05-09
**Logs analyzed:** 4 logs total — 2 `plan-revision` task-execution + 2 `review-runs` analysis (one of which is the prior CPI cycle's own log, one is the same-day predecessor of this run)

## Runs Analyzed

- **Count:** 2 task-execution runs + 2 analysis runs
- **Date range:** 2026-05-03 13:21 UTC (oldest review-runs) → 2026-05-09 19:21 UTC (this review-runs' predecessor)
- **Workflow mix:** 2× `plan-revision`, 2× `review-runs`
- **Outcomes:** 4/4 success
- **Aggregates (task-execution only):** $33.20 cost, ~33.6 min wall time, 117 turns
- **Aggregates (analysis runs):** $4.33 cost, ~10.8 min wall time, 71 turns

| Log | Cost | Min | Turns | Tool-msgs | Multi-tool msgs | Token-overflow | Errored tool results |
|---|---:|---:|---:|---:|---:|---:|---:|
| `plan-revision-20260508-003734` (Sprint 2-1f/g Django) | $11.55 | 20.1 | 62 | 78 | 26 (33%) | 3 | 3 |
| `plan-revision-20260508-005323` (Sprint 2-1h kube-vip HA) | $21.66 | 13.5 | 55 | 102 | 0 (0%) | 2 | 4 |
| `review-runs-20260509-191558` (this run's same-day predecessor) | $2.80 | 5.7 | 48 | 34 | 11 (32%) | 0 | 0 |
| `review-runs-20260503-132135` (prior CPI cycle) | $1.53 | 5.1 | 23 | — | — | 0 | 0 |

**Prior reviews of this repo:** `review-mdc-master-planning-2026-05-09.md` (same-day predecessor — overwritten by this run), `review-mdc-master-planning-2026-05-03.md` (7 runs), `review-2026-04-24-mdc-master-planning.md` (20 runs).

**Sample-size caveat:** the two `plan-revision` runs are the only NEW task-execution data in this window — both were already analyzed by the same-day predecessor at 19:15 UTC. This re-analysis preserves the predecessor's task-execution findings (which I independently verify match the logs) and adds one fresh finding from analyzing the predecessor's own log as data.

---

## High-Confidence Findings

### H1. Parallel review-agent dispatch regressed in 1/2 runs (preserved from same-day predecessor; independently verified)

**Evidence:** The two plan-revision runs in this window — same day, same git tree, ~16 min apart — show opposite review-agent dispatch patterns:

| Run | Tool-msgs | Multi-tool msgs | % parallel | Cost/tool-msg |
|---|---:|---:|---:|---:|
| `003734` (Django plan revision) | 78 | 26 | 33% | $0.148 |
| `005323` (kube-vip plan revision) | 102 | 0 | 0% | $0.212 |

Verified by re-deriving with `jq` group-by-message-id: `003734` had 26 multi-tool messages out of 78 tool-bearing assistant messages; `005323` had **zero** multi-tool messages across 102 tool-bearing assistant messages. The serial-dispatch run cost ~43% more per tool-message ($0.212 vs $0.148) and was the more expensive run overall ($21.66 vs $11.55) despite being shorter wall-clock.

**Recommendation:** Same as the same-day predecessor. The CPI cycle 2-3 fix (commit `e7c8715`) is not stable across runs in this window. Worth diffing the actual review-stage prompts the agent generated for `003734` vs `005323` — if one matched a parallel exemplar verbatim and the other reverted to per-agent dispatch, that's a prompt-contamination signal. If both look identical, the regression is on the model side and prompt reinforcement will need to land elsewhere.

**Impact:** ~$10 cost differential on a single run. Across an N=2 sample this is too small to project, but if it stabilizes at 50/50 the cost impact compounds.

**Confidence:** High on the evidence (clear cost differential, message-id grouping confirms zero-vs-26 multi-tool count). Low on sample size — N=2 is enough to flag, not enough to claim a settled regression. **Watch-criteria:** if run #3 (next plan-revision in this repo) also shows fully-serial dispatch, ship a prompt-side reinforcement of "review agents MUST be in one assistant message."

---

### H2. The same-day predecessor `review-runs` agent was Bash-iteration-heavy on jq queries (NEW finding from analyzing the predecessor's own log)

**Evidence:** `review-runs-20260509-191558` issued **47 tool calls**: 42 Bash, 3 Read, 1 Grep, 1 Write. Of the 42 Bash calls, ~25 were variations on the same `for f in plan-revision-005323 plan-revision-003734; do echo "..."; jq ...` pattern with slight changes to the inner jq query — iterative refinement against the same two files.

Sampled commands (truncated by jq's stream):
- `for f in ...; do echo "..."; jq -c 'select(.type==...' done` (×8 with varying selects)
- `for f in ...; do echo "..."; jq -r 'select(...)' done` (×6)
- `# Find which files caused token overflows by correlating...` (heuristic-rebuild iterations)
- `# Easier approach: list error tool_use_ids, then grep for them...`

The same-day predecessor's analysis IS thorough and well-structured, so the Bash-iteration cost paid off in report quality. But the pattern is exposing: the workflow-analysis methodology has no precomputed jq template for the standard counts (overflows, errored results, multi-tool messages, tool-name distribution, token-overflow file attribution), so the agent re-invents them per-run.

**Recommendation:** This is a **claude-dot-files-level observation, not a project-side fix.** Surfacing it for the architecture session per the claude-dot-files-governance rule. A reusable jq snippet library in the `review-runs` workflow prompt (or a `tools/log-stats.sh` companion script) would let the analysis agent skip the iteration cycle and spend turns on reasoning instead of query-tuning. NOT acting on this from the project session.

**Impact:** $2.80 / 48 turns / 5.7 min for this run. The next review-runs cycle on the same data could be cheaper if the jq library lands. Not blocking — the workflow IS producing usable reports.

**Confidence:** High on the observation (47 tool calls is a measured count; 42 Bash is a sort-uniq result). Medium on the recommendation — N=1 observation that the iteration pattern repeats; need to see the next review-runs cycle to confirm this is systemic vs first-time-against-this-data.

---

## Medium-Confidence Findings

### M1. 25K-token Read overflow recurs in 2/2 plan-revision runs (CPI Pattern A — recurrence, watch-criteria NOT met)

**Evidence:** 5 token-overflow events confirmed by re-grepping the logs:

| Run | File | Token count | Note |
|---|---|---:|---|
| `003734` | `development/sprints.md` | 38,399 | Known-large since 2026-04-24 review |
| `003734` | `development/common/loose_ends/sprint_2_loose_ends.md` | 30,474 | Known-large class |
| `003734` | `development/common/loose_ends/sprint_2_loose_ends.md` | 30,474 | Same file, second hit |
| `005323` | `development/sprints.md` | 39,525 | Known-large |
| `005323` | `development/service/argocd/phase1_long_lived_bot_token.md` | 28,032 | **NEW hot file (605 lines, Sprint 1-3b shipped 2026-04-25)** |

In all five cases, the failed `Read` had `limit=null` and `offset=null`. The agent ran `wc -l` upfront (good — size *discovery* discipline is followed) but didn't translate line count into a `limit:` parameter. `sprints.md` at 529 lines is ~75 tokens/line; once long structured prose accumulates it overflows.

**Recurrence — CPI Pattern A:** DEFERRED at 2026-05-03 review-runs cycle. Watch-criteria: *"if persists at >2× current rate after project-side allowlist work lands, OR if project-side allowlist proves insufficient → revisit prompt-side reinforcement."* Project-side allowlist has **not landed** (verified: `mdc-master-planning/CLAUDE.md` line 54 names `sprints.md` only as a navigation entry, no known-large guidance). Per-run rate is ~2.5 events/run vs 2.0 events/affected-run last cycle — **flat, not 2×.** **Watch-criteria NOT met.** Continue to defer prompt-side reinforcement.

**Recommendation (project-side, dispatch-scope):** Add to `mdc-master-planning/CLAUDE.md` a short paragraph naming the four known-large files / classes (`development/sprints.md`, `development/common/loose_ends/sprint_*_loose_ends.md`, `development/common/networking/phase_*.md`, `development/service/argocd/phase1_long_lived_bot_token.md`) where `Read` MUST pass `limit:200` on first read. This unblocks the deferred CPI Pattern A rather than escalating it.

**Impact:** ~3 wasted turns per overflow plus chunked-recovery turns (typically 2–3 chunks per file). 5 overflows × ~3 turns ≈ 15 wasted turns across $33 of run cost — single-digit dollars on the margin.

**Confidence:** Medium — pattern in 2/2 plan-revision runs in this window, but `phase1_long_lived_bot_token.md` is a single-occurrence new hot file. Trend matches prior cycles.

---

### M2. Edit "String to replace not found" — both occurrences in the serial-dispatch run

**Evidence:** 2 `<tool_use_error>String to replace not found in file.</tool_use_error>` events both in `005323`:

1. After post-review revision pass, attempted to replace a `Server-005 acts as both server and agent…` line that didn't match actual file content.
2. Same review pass, attempted to replace a multi-line `T4.5 — Verify VIP serves K3s API…` block that had been edited intermediately by a prior Edit.

`003734` had **zero** Edit-target-not-found errors despite issuing 17 Edit calls.

**Recommendation:** This may be cause-or-coincidence with H1's serial-dispatch issue. When review agents run in parallel, the post-review Edit pass operates on a single coherent target string (one summary in context). When agents run serially, the agent makes Edits between subagent invocations, and the Edit-target text drifts from what the model recalls. **If H1 stabilizes (parallel becomes the norm again), M2 likely resolves with it.** If H1 does NOT stabilize, the targeted fix is a post-Edit Read reminder before the next Edit on the same file region.

**Confidence:** Medium — strong correlation in N=1 vs N=1 in this window, but causation requires the next serial-dispatch run to also cluster these errors.

---

### M3. `phase1_long_lived_bot_token.md` joins the known-large class

**Evidence:** `005323` overflowed `phase1_long_lived_bot_token.md` at 28,032 tokens. File is 605 lines today; Sprint 1-3b shipped it 2026-04-25 and ~7 review-resolution edits have accreted since. Same growth pattern as `phase_calico_api_server.md` flagged in the 2026-04-24 review and `genesis/phase*.md` family before that — phase docs accumulate review-resolution context until they overflow.

**Recommendation:** Roll into the M1 project-side allowlist update — naming the `development/service/<service>/phase*.md` family, not just this file, captures the class.

**Confidence:** Medium — 1 occurrence on this specific file but the class-pattern is well-mapped from prior cycles.

---

## Low-Confidence Findings

### L1. `ScheduleWakeup` invoked once inside `005323` (recurrence of L1 from the predecessor review)

**Evidence:** `005323` issued one `ScheduleWakeup` call — same anomaly noted at L1 in both the same-day predecessor review and the 2026-05-03 review (`plan-new-20260430-153526`). All three are non-loop workflows where self-pacing shouldn't be invoked.

**Watch for:** Recurrence inside non-loop workflows. Three observations across three windows (one per window) is now a slow-burn pattern. Not yet at a ship threshold; **flag for run #4 watch.**

**Confidence:** Low per-window — single observation. Cumulative across three windows it's edging toward Medium.

---

### L2. Repeat-reads of `sprint_2_loose_ends.md` in 003734 (9× total) — verified as legitimate cross-referencing, not unbounded re-reading

**Evidence:** `003734` Read `sprint_2_loose_ends.md` 9 times (2 unbounded → overflow + 7 chunked). The chunked reads were narrowly-targeted at distinct loose-ends entries (`2-7a.1`, `2-0a.4`, `2-0a.16`, `2-4a.3` etc.) so each read returned different content. This is correct behavior for a workflow cross-referencing many loose-ends sections.

**Watch for:** This is NOT the prior-review "unbounded re-reads" failure mode. Included here only to clarify the data so it isn't flagged as a regression in some future cycle.

**Confidence:** Low — single observation; included as an annotation, not as a finding.

---

## Patterns Resolved Since Last Review

- **Prior 2026-05-03 H3 — Parallel review-agent dispatch is the new norm**: **Partial regression** (see H1). 1/2 runs in this window vs 4/5 in the 2026-05-03 cycle.
- **Prior 2026-05-03 H2 — `find | xargs` whitespace silent data loss**: No new occurrences. **CPI Pattern C deferral remains valid; second-occurrence ship trigger NOT met.**
- **Prior 2026-04-24 H3 — Grep `file_path` parameter misuse**: **Stays resolved.** Zero occurrences in either plan-revision run this window (vs 1 in 2026-05-03 and 8 in 2026-04-24). Trajectory remains the right direction.
- **Prior 2026-04-24 M2 — "File has not been read yet"**: Zero occurrences in this window's plan-revision runs. Two-run sample isn't enough to call it resolved, but no new evidence to revive either.

---

## Recurrences from CPI Decisions Log

Cross-referenced against `/opt/skyy-net/claude-dot-files/docs/development/cpi-decisions.md`:

- **CPI Pattern A — 25K-token Read overflow** — DEFERRED at 2026-05-03 review-runs cycle. **Recurrence at ~2.5 events/run** (5 events / 2 runs) vs 2.0 events/affected-run prior. **Watch-criteria NOT met** (not 2× the rate; project-side allowlist hasn't landed yet so the rate-comparison precondition doesn't fire). **Disposition: continue to defer prompt-side reinforcement; recommend project-side allowlist as the next action (M1 above).**

- **CPI Pattern C — `find | xargs` whitespace silent data loss** — DEFERRED at 2026-05-03. Watch-criteria: *"ship the `find -print0 | xargs -0` rule on second occurrence in any repo."* Current cycle: **0 occurrences.** **Watch-criteria NOT met. Disposition: continue to defer.**

- **2026-05-08 ad-hoc reflection — "4-agent parallel review surfaces unique findings"** — N=2 at the time of that reflection. Watch-criteria: *"N=3 occurrences across distinct runs"*. Run `003734` in this window adds a third confirming instance (4-agent parallel dispatch including standards-architect + security-auditor + planner + architect; standards-architect surfaced API Standard §2 URL-rename gap). **Watch-criteria MET — N=3.** This is the trigger for documenting the 4-agent parallel dispatch as a design choice in workflow-guide rationale. **Surfacing for the architecture session per claude-dot-files-governance — NOT acting on it from this project session.**

- **2026-05-03 sprint-review TS-2 — surface-only mode boundary case** — Not exercised in this window (no sprint-review runs).

---

## Metrics

| Metric | This window (2 plan-revision runs) | Prior (7 runs, 2026-05-03) | Two priors back (20 runs, 2026-04-24) |
|---|---|---|---|
| Success rate | 2/2 = 100% | 7/7 = 100% | 19/20 = 95% |
| Mean cost / run | $16.61 | $12.03 | $9.54 (overall) |
| Mean duration / run | ~16.8 min | ~17.6 min | — |
| Mean turns / run | 58.5 | ~157 | ~80 |
| Multi-tool message rate | 14% (across both runs combined) | 14.7% | ~0% |
| Parallel review-agent dispatch | 1/2 review-stage runs | 4/5 | 0/10 |
| 25K-token overflow events | 5 (2 runs) | 14 (4 runs) | 22 (7 runs) |
| Grep `file_path` misuse | 0 | 1 | 8 |
| `find \| xargs` whitespace events | 0 | 1 | — |
| `string-to-replace-not-found` Edit errors | 2 (1 run) | not measured | not measured |

**Trend direction:**
- **Cost-per-run rising** (+$4.58 vs 2026-05-03; +$7.07 vs 2026-04-24). Two-run sample too small for a trend claim; flag and watch.
- **Turns-per-run dropped sharply** (58.5 vs ~157) — apples-to-oranges; this window's runs were narrower-scope phase-doc revisions, not multi-day plan-new.
- **Parallel review-agent dispatch dropped** from 4/5 (80%) to 1/2 (50%) — see H1.

**Cost concentration:** $33.20 total task-execution cost — $21.66 (65%) in the single serial-dispatch run.

**Meta-cost on review-runs cycles themselves:** $2.80 (this window's predecessor) vs $1.53 (2026-05-03 cycle). The increase is mostly the predecessor's deeper analysis (47 tool calls vs 22, including jq-iteration overhead per H2) — not a workflow regression, but worth noting that analysis cost will compound if H2 isn't addressed.

---

## Summary

Both plan-revision runs in this 2026-05-08 window completed successfully and produced merged-or-mergeable PRs (PR #24 Django, PR #25 kube-vip HA). The dominant finding is **a partial regression in parallel review-agent dispatch** (H1) — one run preserved the 4-agent-in-parallel pattern, the other reverted to fully-serial and cost ~43% more per tool-message; with N=2 this is flagged for run #3 watch rather than treated as a settled regression. **CPI Pattern A (25K-token overflow) recurs at flat per-run rate** and remains correctly deferred — the project-side `CLAUDE.md` allowlist work (M1) is the unblocking action. **The 2026-05-08 ad-hoc reflection's N=3 watch-criteria for documenting 4-agent parallel review IS now met** — surfacing for the architecture session, alongside H2's observation that the review-runs analysis itself could benefit from a reusable jq snippet library to reduce per-cycle iteration cost.
