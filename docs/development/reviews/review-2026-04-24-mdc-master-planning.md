# Workflow Review — 2026-04-24

## Runs Analyzed

- **Count:** 20 `plan-revision` runs
- **Date range:** 2026-04-11 23:39 UTC → 2026-04-24 02:17 UTC (~13 days)
- **Workflow type:** `plan-revision` (exclusively)
- **Outcomes:** 19 success, 1 `error_max_turns` (20260422-192501)
- **Aggregates:** 1,606 total turns, ~$190.73 total cost, ~7h 44m total wall time
  - First 10 runs (Apr 11-16): mean 51.7 turns / $4.49 / run
  - Last 10 runs (Apr 17-24): mean 108.9 turns / $14.59 / run — **cost per run ~3.25× higher in the recent half**
- **Prior reviews:** None found in `docs/development/reviews/` (first review)

---

## High-Confidence Findings

### H1. Review agents are invoked sequentially, not in parallel (0% parallelism)

**Evidence:** Every assistant turn in all 10 sampled recent runs dispatched ≤1 tool call (multi-tool-per-turn = 0). In `plan-revision-20260424-021745.jsonl`, the three review agents were dispatched on four separate turns:
- Turn 16: `Agent:Explore`
- Turn 51: `Agent:architect`
- Turn 73: `Agent:planner`
- Turn 94: `Agent:standards-architect`

Same serial pattern in 20260420-235455, 20260422-210555, 20260422-221207, 20260423-004607, 20260423-170958, 20260423-224015, 20260423-224047, 20260424-020413.

**Recommendation:** The `architect`, `planner`, and `standards-architect` agents perform **independent** review passes against the same artifact. They should be dispatched in a single assistant message with three parallel `Agent` tool calls. The Explore agent (when used) may legitimately go first if its output seeds the review prompts; otherwise it can also go parallel.

**Impact:** Serial dispatch extends each run's wall clock by roughly the sum of the three agents' runtimes instead of the max. At ~5–10 min per review agent observed in recent runs, parallelizing cuts review-stage wall time ~2× and shaves cache-creation tokens for the redundant intermediate turns.

**Confidence:** High — pattern in 10/10 sampled runs, including all 7 runs from the April 22-24 window.

---

### H2. Large planning docs are Read without `limit` and hit the 25K-token ceiling

**Evidence:** 22 `File content exceeds maximum allowed tokens (25000)` errors across 7 runs. Hot files:

| Occurrences | File |
|---|---|
| 12 | `development/common/loose_ends/sprint_1_loose_ends.md` (currently 715 lines / 117 KB) |
| 7 | `development/common/genesis/phase1d_k3s-1_provision.md` (currently 577 lines / 71 KB) |
| 2 | `development/common/genesis/phase1d_cluster1_provision.md` (pre-rename) |

Runs with heaviest hits: 20260423-004607 (7), 20260423-170958 (7), 20260422-210555 (2), 20260422-221207 (2), 20260417-141054 (2).

**Recommendation:** `CLAUDE.md` already codifies the mitigation: *"For known-large files (roadmap.md, standards docs, .jsonl logs), use limit:200 on first read or run wc -l to check size first"* — but the agent isn't following it. Two reinforcement options:

1. Add `loose_ends/sprint_*.md` and `genesis/phase*.md` to the explicit "known-large" list in `CLAUDE.md`.
2. Have `plan-revision.sh`'s initial prompt block remind the agent to `wc -l` before the first Read of any file under `development/common/loose_ends/` or `development/common/genesis/`.

**Impact:** Each hit costs one retry turn (Read-with-limit) plus the wasted token count on the failed Read. Across 22 occurrences that's ~22 extra turns. Secondary impact: when hit inside a subagent, the agent usually fragments into many chunked reads, compounding turn spend.

**Confidence:** High — pattern in 7 runs, clear cause (CLAUDE.md guidance) and effect (token-count-ceiling error).

---

### H3. `Grep` tool called with the wrong parameter name (`file_path` instead of `path`)

**Evidence:** 8 `InputValidationError: ... An unexpected parameter 'file_path' was provided` errors across 5 runs:
- 20260420-235455 (2×), 20260422-210555 (2×), 20260423-224015 (2×), 20260423-170958 (1×), 20260424-021745 (1×)

Representative calls all pass a single file as the search target:
```
{"pattern": "...", "file_path": "/opt/skyy-net/.../architectural_standard.md", "output_mode": "content"}
```

**Recommendation:** The correct parameter is `path`. This is a recurring tool-schema confusion on Grep, likely reinforced by the similar `file_path` parameter on `Read`/`Edit`/`Write`. Options:
- Add a one-line note to the plan-revision prompt: *"When grepping a single file, use `path`, not `file_path`"*.
- Or change behavior upstream if the tool router accepts both.

**Impact:** 1 wasted turn per occurrence; agent recovers immediately. Low per-incident cost but persistent across weeks of runs.

**Confidence:** High — 8 occurrences across 5 distinct runs, always the same mistake.

---

## Medium-Confidence Findings

### M1. Max-turns runaway on the one non-review task in the set

**Evidence:** `plan-revision-20260422-192501.jsonl` — the only run in the 20 that did **not** frame as a review.

- First assistant text: `"## Stage 1: ASSESS — Surveying all references to the old cluster names across planning, standards, and config templates."`
- Tool distribution: **191 Edits** across 23 files, 47 Reads, 31 Bash, 26 Grep, **0 Agent invocations**
- Hot files: `roadmap.md` (32 edits), `phase1d_cluster1_provision.md` (31), `sprints.md` (17), `k8s_deployment_standard.md` (15), `networking_standard.md` (10), `persistent_storage.md` (10)
- Terminated at 301 turns / $37.06 / `error_max_turns`

The task was a **bulk rename** of K3s cluster identifiers across the repo. The agent never transitioned from Stage 1 (assess) into the review phase — it spent all 300 turns doing per-occurrence Edits.

**Recommendation:**
- For bulk rename-style tasks, prefer a single `sed -i` pass over per-occurrence `Edit`. One `Bash` call replaces dozens of `Edit` turns.
- Alternatively, use `Edit` with `replace_all: true` to catch all occurrences in a file in one call (only 5 of 191 edits used `replace_all`).
- If the workflow is genuinely "plan revision + review", the script should reject prompts that are predominantly rename/refactor in scope, or the operator should dispatch these via `revision.sh` instead of `plan-revision.sh`.

**Needs:** Confirmation from the operator whether this task belonged on `plan-revision.sh` at all, or whether it got miscategorized.

**Impact:** $37 single-run cost + never completed; would likely have needed a second run to finish review even if it hadn't timed out.

**Confidence:** Medium — single run but severe failure mode; pattern-adjacent evidence: heavy-Edit totals (38-54 per run) on Apr 22-24 suggest rename/renormalization work is flowing through plan-revision regularly.

---

### M2. "File has not been read yet" Write/Edit errors

**Evidence:** 10 occurrences across 6 runs:
- 20260422-192501 (3×), 20260413-191538 (2×), 20260423-224047 (2×), 20260417-141054 (1×), 20260420-235455 (1×), 20260422-210555 (1×)

Example error: `<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>`

**Recommendation:** The agent occasionally tries to Edit a file after a subagent read it (subagent Reads don't count), or tries to Write to a file it created in a prior subagent delegation. Watch for whether this concentrates after Agent returns — in which case a "re-Read after subagent" reminder in the prompt would help.

**Needs:** Correlating error position vs. subagent boundaries — sample too small in this review window to be conclusive.

**Confidence:** Medium — 6 runs, but recovery is always immediate (1 extra Read turn). Low per-incident cost.

---

### M3. Cost-per-run has ~3× since April 16

**Evidence:**
- Apr 11–16 (10 runs): mean 51.7 turns / $4.49
- Apr 17–24 (10 runs): mean 108.9 turns / $14.59
- Max: 124 turns / $15.40 (20260420-235455, successful); 301 turns / $37.06 (20260422-192501, failed)

Part of the growth is legitimate scope expansion — the recent Tailscale Phase 2, 1Password, Vault, GitHub-App, and cluster-rename plans touch more files than the early Genesis Phase-1 revisions. But H1 (serial agents) and H2 (25K-token retries) are present only in the later window and amplify the growth.

**Recommendation:** Re-measure after implementing H1 and H2 fixes; expected recovery is 20-40% on the review-heavy runs.

**Confidence:** Medium — clear trend but confounded by task-scope growth; will become clearer once the mitigations land and 5+ post-fix runs accumulate.

---

## Low-Confidence Findings

### L1. Transient environment errors (SSH / worktree already in use)

**Evidence:**
- `ssh: Could not resolve hostname master-planning-github` — 2× on 20260411-233935
- `worktree ... is already used by worktree at ...` — 1× on 20260413-200010, 1× on 20260420-235455

**Watch for:** Recurrence on new runs. If the SSH hostname resolution fails again, check `~/.ssh/config` for stale aliases. Worktree conflicts suggest a prior worktree wasn't cleaned up — the `cleanup-merged-worktrees` skill would address this.

**Confidence:** Low — 4 occurrences across 3 runs, likely transient.

---

### L2. "String to replace not found" on Edit

**Evidence:** 8 occurrences, 5 concentrated in the failed 20260422-192501 bulk-rename run. Remaining 3 are isolated.

**Watch for:** Clustering again in future rename-heavy runs. Outside the bulk-rename context this is a normal occasional mistake (agent misremembers exact wording of a block).

**Confidence:** Low — the pattern is really part of M1 (bulk-rename failure mode), not a distinct issue.

---

## Patterns Resolved Since Last Review

**None** — this is the first `review-runs` report in `docs/development/reviews/`.

---

## Metrics

| Metric | Value |
|---|---|
| Runs | 20 |
| Success rate | 19/20 = 95% |
| Hard failures | 1 (`error_max_turns`, 20260422-192501) |
| Mean turns/run (all) | 80.3 |
| Mean turns/run (first 10) | 51.7 |
| Mean turns/run (last 10) | 108.9 |
| Mean cost/run (all) | $9.54 |
| Mean cost/run (first 10) | $4.49 |
| Mean cost/run (last 10) | $14.59 |
| Median duration | ~1,200s (~20 min) |
| Parallel-tool-use turns | **0 across all 10 sampled recent runs** |
| Tool-error turns (25K overflow) | 22 (7 runs) |
| Tool-error turns (not-read-yet) | 10 (6 runs) |
| Tool-error turns (Grep bad param) | 8 (5 runs) |
| Agent usage (recent 10 runs) | architect ×10, planner ×10, standards-architect ×8, Explore ×2 |

**Trend direction:** Costs and turn counts trending **up**. ~3× cost-per-run in the last half of the window. Subagent usage stabilizing around the architect+planner+standards-architect triad (8/10 recent runs) — good pattern to preserve.

---

## Summary

The `plan-revision` workflow is reliable (19/20 success, 95%) but has accumulated efficiency drag: no parallelism on the three independent review agents, repeated Reads of oversized planning docs that blow past the 25K-token ceiling, and a recurring `Grep(file_path=…)` parameter mistake. Top priority is **parallelizing the architect + planner + standards-architect triad** in one assistant turn — same three agents, same review scopes, estimated ~2× wall-clock reduction on the review phase. Second priority is adding `loose_ends/sprint_*.md` and `genesis/phase*.md` to CLAUDE.md's known-large-file list so the agent uses `limit:200` on first Read. The one hard failure (20260422-192501, cluster-rename bulk refactor) was miscategorized — bulk renames belong on `revision.sh` with `sed -i` or `Edit.replace_all`, not on the review-oriented `plan-revision.sh`.
