# Workflow Review — mdc-master-planning — 2026-05-03

**Source repo:** `/opt/skyy-net/mdc-master-planning`
**Source machine:** `skyy-net`
**Analysis date:** 2026-05-03
**Logs analyzed:** 7 runs, 2026-04-28 13:57 UTC → 2026-04-30 21:48 UTC (~2.3-day window)

## Runs Analyzed

- **Count:** 7 runs (5 review-stage, 2 small-revision)
- **Workflow mix:** 3× `plan-new`, 2× `plan-revision`, 2× `revision`
- **Outcomes:** 7/7 success (no `error_max_turns`, no hard failures)
- **Aggregates:** ~$84.21 total cost, ~123.5 min total wall time

| Log | Cost | Min | Turns | Token-overflow | Errored tool results |
|---|---:|---:|---:|---:|---:|
| `revision-20260430-214828` | $2.11 | 2.8 | 47 | 0 | 1 |
| `plan-new-20260430-190555` | $11.61 | 25.9 | 142 | 5 | 7 |
| `revision-20260430-164612` | $4.31 | 7.9 | 78 | 0 | 0 |
| `plan-new-20260430-153526` | $16.75 | 9.8 | 171 | 0 | 1 |
| `plan-new-20260428-193753` | $16.91 | 32.3 | 193 | 1 | 3 |
| `plan-revision-20260428-155539` | $11.29 | 16.0 | 198 | 0 | 1 |
| `plan-revision-20260428-135739` | $21.23 | 28.7 | 270 | 8 | 14 |

- **Prior review:** `review-2026-04-24-mdc-master-planning.md` (20 plan-revision runs)

---

## High-Confidence Findings

### H1. The 25K-token Read overflow is unresolved and concentrated in two hot files

**Evidence:** 14 `File content exceeds maximum allowed tokens (25000)` events across 4 of 7 runs:

| Occurrences | File | Run breakdown |
|---:|---|---|
| 5 | `development/common/networking/phase_calico_api_server.md` | plan-new-20260430-190555 (events 113, 119, 174, 180) |
| 8 | `development/common/loose_ends/sprint_1_loose_ends.md` (~63K tokens) and `development/sprints.md` (~29K tokens) | plan-revision-20260428-135739 (events 18, 30, 238, 260, 270, 272, 282, 314) |
| 1 | `development/common/networking/phase_calico_api_server.md` (during Sprint 2-1e plan-new) | plan-new-20260428-193753 |

In every case the failed Read had `limit=None` and `offset=None`. After each failure the agent recovers with a chunked read (limit + offset), but in `plan-revision-20260428-135739` it ends up reading `sprint_1_loose_ends.md` **34 times** in one run — many of those chunks could have been a single `Grep` for the section the agent actually wanted.

**Recommendation:** The prior review (2026-04-24) already flagged this. The mitigation hasn't held. Two reinforcements:

1. Add `phase_calico_api_server.md` (and the `phase_*.md` family in `development/common/networking/`) to CLAUDE.md's known-large-file list alongside `sprint_*.md`/`genesis/phase*.md`.
2. For the bulk-rename / cross-file-edit class of `plan-revision` task, prompt the agent to **Grep for the target section before Reading** — when it knows the line offset, a 30-line window beats a full-file read.

**Impact:** Each overflow is one wasted turn plus the chunked-recovery turns that follow. In the heaviest run that's ~10–15 turns of pure recovery, contributing materially to its $21 cost.

**Confidence:** High — pattern in 4/7 runs in this window, matches the prior review's H2 verbatim, and the 8-overflow run is the highest-cost run in the set.

---

### H2. `find | xargs sed` against `.md` paths with spaces fails silently-loud

**Evidence:** `plan-revision-20260428-135739` event 114:

```
find . -name '*.md' -not -path './.claude/*' -not -path './node_modules/*' \
  | xargs sed -i -E -f /tmp/claude-migration-sprint1.sed
```

Result (event 115): `Exit code 123 — sed: can't read ./guide/03.: No such file or directory / sed: can't read Hardware: No such file or directory / sed: can't read Requirements/Hardware: No such file or directory / sed: can't read Requirements.md: No such file or directory`

The repo contains directories like `guide/03. Hardware Requirements/` — `xargs` split the unquoted whitespace and sed received truncated paths. Files in those directories were silently skipped from the bulk identifier rename.

**Recommendation:** For any `find … | xargs` pattern, use `-print0 … | xargs -0`. Better yet, codify in CLAUDE.md or the `revision.sh` / `plan-revision.sh` initial prompt: *"When piping `find` to `xargs`, always use `-print0 | xargs -0`."* The same rule applies if the agent reaches for `find … -exec`.

**Impact:** Silent data-loss class of failure. The user happened to catch it in this run because sed printed errors, but on a quieter `find … -exec` invocation the same problem would silently skip files and the agent would mark the task done.

**Confidence:** High — single occurrence but the failure mode is generic to bulk-rename style work, which the prior review (2026-04-24 M1) already flagged as a recurring `plan-revision` task type.

---

### H3. Parallel review-agent dispatch is the new norm — prior H1 largely resolved

**Evidence:** Across the 5 review-stage runs (3× plan-new + 2× plan-revision), the architect/planner/security-auditor (or standards-architect) triad is dispatched in a **single multi-tool message** in 4 of 5 runs:

| Run | Agent dispatch pattern |
|---|---|
| `plan-new-20260430-190555` | `[architect, planner, security-auditor]` in one message (event 98) |
| `plan-new-20260430-153526` | **Serial** — three separate messages at events 174, 189, 211 |
| `plan-new-20260428-193753` | `[architect, planner, security-auditor]` in one message (event 154) |
| `plan-revision-20260428-155539` | `[architect, planner, standards-architect]` in one message (event 174) |
| `plan-revision-20260428-135739` | `[architect, planner, standards-architect]` in one message (event 226) |

Reconciliation note: this required deduping by `message.id` (the JSONL stream emits one event per `tool_use` block but the API call is one message). The prior review's "0% parallelism" claim was undercounting for the same reason — review the methodology before re-comparing.

**Recommendation:** Preserve the prompt change that enabled this. The single hold-out (`plan-new-20260430-153526`) is worth diffing against the others to identify the prompt drift.

**Impact:** Recovers ~2× wall-clock on the review phase — the prior review's projected savings appear to be landing.

**Confidence:** High — pattern in 4/5 review-stage runs, clearly linked to identical multi-tool message structure, consistent across both `plan-new` and `plan-revision`.

---

## Medium-Confidence Findings

### M1. Parallel-tool failure cascades cancel sibling calls

**Evidence:** `plan-revision-20260428-135739` events 207–210. The agent issued two parallel Bash calls in one message: `grep -nE '^### …' development/common/loose_ends/` (a directory, not a file) and `git diff --name-only main | grep -vE '\.md$' | head`. The first errored (`grep: … : Is a directory`), and the second was cancelled with `tool_use_error: Cancelled: parallel tool call Bash(grep -nE …) errored`.

This is a behavior of the parallel-tool runtime, not a bug, but the agent should know: **parallel tool calls share fate**. If one of them is risky, don't bundle it with calls that the agent will need anyway.

**Recommendation:** Either (a) prompt-side reminder when the agent opts into parallel Bash: *"Don't pair a probably-correct call with a probably-wrong one — failures cancel siblings"*; or (b) accept this as a normal outcome since recovery is one extra turn.

**Needs:** Sample is one occurrence — watch whether it recurs as parallelism increases. Aggregate parallel-tool usage across the 7 runs is now 14.7% of tool-bearing messages (up from ~0% in the prior review window), so the surface is growing.

**Confidence:** Medium — single direct evidence but the underlying mechanism is permanent and the cost rises as parallelism does.

---

### M2. "File has not been read yet" errors persist after subagent boundaries

**Evidence:** 5 occurrences across 4 runs:
- `plan-new-20260430-190555` (1×, event 149-region)
- `plan-new-20260430-153526` (1×)
- `plan-revision-20260428-155539` (1×)
- `plan-revision-20260428-135739` (3× at events 149, 176, 178)

In `plan-revision-20260428-135739` the three errors cluster between events 149–178, which is **before** the agent dispatch at event 226 — so they're not subagent-boundary-related in this window. They look more like the agent forgetting Read state across a long sequence of Edits.

**Recommendation:** Watch whether the cluster correlates with run length (this run was 270 turns and accumulated all 3). If long runs reliably bunch these errors, a post-Edit reminder isn't going to help — the model just loses track. Safer mitigation is to keep the per-stage scope tighter.

**Confidence:** Medium — pattern in 4 runs, but recovery cost is one extra Read per occurrence. Low per-incident cost.

---

### M3. Bulk-rename `plan-revision` runs dominate cost — 25% of total spend in one run

**Evidence:** `plan-revision-20260428-135739` ($21.23, 28.7 min, 270 turns) is the most expensive run in the window and matches the prior review's M1 profile exactly: bulk identifier rename across ~30 .md files, 14 errored tool results, 8 token overflows, 49 grep calls, 94 reads, 36 bash calls. The prior review flagged this class of task as miscategorized for `plan-revision`.

It succeeded this time (didn't hit max_turns), but the failure mode is well-mapped:
- `find | xargs sed` failure (H2 above)
- Repeated full-file reads on `sprint_1_loose_ends.md` (H1 above)
- 14 errored tool results in one run (highest in the set)

**Recommendation:** Restate the prior review's recommendation: bulk-rename / cross-file structural migrations belong on `revision.sh` (with `sed -i` or `Edit.replace_all`), not on `plan-revision.sh`. The doc-migration class of work that runs through `plan-revision` is what the script's review agents are designed for — **the agent should still use single-shot bulk-edit Bash**, not 100+ per-occurrence Edits.

**Confidence:** Medium — single-run severe-cost pattern, but pattern-matches prior review's M1 (bulk-rename). Two data points across two review windows.

---

## Low-Confidence Findings

### L1. The `revision-20260430-214828` "ToolSearch then ScheduleWakeup" path

**Evidence:** Both `revision` runs and several `plan-new` runs invoke `ToolSearch` early to load tool schemas. `plan-new-20260430-153526` also issued one `ScheduleWakeup` call. Neither is necessarily a problem — but the `ScheduleWakeup` was unusual for a build-out workflow that should run to completion in one session.

**Watch for:** Recurrence of `ScheduleWakeup` inside non-loop workflows. If the agent is self-pacing inside a `plan-new` run, it likely lost context about whether the workflow is dynamic-loop or one-shot.

**Confidence:** Low — single observation.

---

### L2. Grep `file_path` parameter mistake nearly extinct

**Evidence:** Only 1 occurrence (`plan-new-20260430-190555`), down from 8 across 5 runs in the prior review window.

**Watch for:** Recurrence — but on this trajectory, it's resolving on its own.

**Confidence:** Low — small numbers but trending the right direction.

---

## Patterns Resolved Since Last Review

- **Prior H1 (sequential agent dispatch):** **Resolved in 4/5 review-stage runs** (see H3 above). Single hold-out is `plan-new-20260430-153526`. Methodology note: prior review's "0% parallelism" undercount was an artifact of not deduping by `message.id`.
- **Prior H3 (Grep `file_path` parameter):** Largely resolved — 1 occurrence (vs 8 prior).
- **Prior H2 (25K-token overflow):** **NOT resolved** — see H1 above. Pattern persists with the same hot files (`sprint_1_loose_ends.md`, `sprints.md`) plus a new one (`phase_calico_api_server.md`).
- **Prior M1 (bulk-rename miscategorization):** **NOT resolved** — see M3 above. The 2026-04-28 plan-revision repeated the failure mode but didn't time out this time.

---

## Metrics

| Metric | This window (7 runs) | Prior window (20 runs) |
|---|---|---|
| Success rate | 7/7 = 100% | 19/20 = 95% |
| Mean cost/run | $12.03 | $9.54 (overall) / $14.59 (last 10) |
| Mean duration/run | ~17.6 min | ~20 min |
| Mean turns/run | ~157 | ~80 (overall) / ~109 (last 10) |
| Multi-tool messages | 91 (14.7% of tool-bearing) | 0% reported (undercount artifact) |
| Parallel agent triad | 4/5 review runs | 0/10 sampled |
| 25K-token overflow events | 14 (4 runs) | 22 (7 runs) |
| `file has not been read yet` | 5 (4 runs) | 10 (6 runs) |
| Grep `file_path` misuse | 1 (1 run) | 8 (5 runs) |

**Trend direction:** Cost-per-run roughly flat; turns-per-run **up** (157 vs 109) but driven by review-stage runs that newly include parallel-agent dispatch and chunked Read-after-overflow behavior. Parallelism is rising — multi-tool message rate went from effectively 0 to 14.7%, with one outlier run at 33.8%.

**Cost concentration:** $84.21 total — $38.84 (46%) in the two heaviest runs (`plan-revision-20260428-135739` at $21.23 and `plan-new-20260428-193753` at $16.91).

---

## Summary

All 7 runs in the 2026-04-28 → 2026-04-30 window completed successfully (0 failures), and the prior review's H1 (sequential review-agent dispatch) is largely resolved — 4 of 5 review-stage runs now dispatch architect/planner/(security-auditor|standards-architect) in a single multi-tool message. Top remaining priority is **prior H2 (25K-token Read overflow), which is still open**: 14 occurrences across 4 runs, dominated by full-file reads of `sprint_1_loose_ends.md`, `sprints.md`, and the new hot file `phase_calico_api_server.md` — the agent should be Greping for the target section before reading these. Second priority is teaching the agent to use `find -print0 | xargs -0` for cross-file bulk operations after one such pipeline silently skipped files in directories whose names contained spaces.
