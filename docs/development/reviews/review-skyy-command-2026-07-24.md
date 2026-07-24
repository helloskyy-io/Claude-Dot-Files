# Workflow Review — skyy-command — 2026-07-24

**Source repo:** `/opt/skyy-net/skyy-command`
**Source machine:** `skyy-net`
**Analysis date:** 2026-07-24
**Logs analyzed:** 61 runs, 2026-07-03 → 2026-07-24 (3-week window)

## Runs Analyzed

- **Count:** 61 logs — 57 terminated `result: success` / `is_error: false`; 4 have **no result event** (abnormal termination, see MC-2)
- **Date range:** 2026-07-03 14:25 → 2026-07-24 13:47
- **Workflow types:** `revision-major` (43), `build-phase` (14), `revision` (4)
- **Prior review on this repo:** `review-skyy-command-2026-05-09.md` (5 runs). Note: there is a **~2-month review gap** — logs from 2026-05-10 → 2026-07-02 exist on disk but were not in this analysis window. Trend comparisons below span that gap.
- **Sample-size note:** at 61 runs this is by far the largest evidence base of any skyy-command review to date (prior reviews: 15 and 5 runs). Confidence ratings are correspondingly stronger.
- **Structural note on logs:** these logs now interleave **subagent** events (tagged with `parent_tool_use_id` + `subagent_type`) with main-loop events. All error counts below are attributed main-loop vs subagent explicitly; prior reviews effectively counted main-loop only.

### Aggregate metrics

| metric | this period (57 completed runs) | prior review (5 runs, 2026-05-09) |
|---|---|---|
| total cost | $1,301.25 | $88.36 |
| avg cost / run | $22.83 | $21.74 |
| avg main-loop turns / run | 77.7 | 142 |
| avg wall time / run | 24.8 min | n/a |
| main-loop `is_error: true` events | 180 (3.0/run) | 21 (4.2/run) |
| total tool-error events incl. subagents | ~322 | n/a (not previously measured) |
| prompt-cache read ratio (sampled) | 0.97–0.99 | 0.97–0.99 |

Per-type: `revision` 4 runs avg $4.71 / 42 turns; `revision-major` 39 runs avg $20.50 / 74 turns; `build-phase` 14 runs avg $34.50 / 98 turns. Cost per run is flat vs prior cycles; main-loop error rate improved from 4.2 → 3.0 per run.

---

## High-Confidence Findings

### HC-1 — Pattern D "Bash CWD reset" rule premise is confirmed wrong: `cd lib/temporal` failures at 36 events / 30 runs

**Evidence:** `/bin/bash: line N: cd: lib/temporal: No such file or directory` (plus `cd: lib/temporal/tests` variants) occurred **36 times across 30 of 61 runs (49%), 100% in the main loop**. Examples: `revision-major-20260721-154459` (`cd lib/temporal && python -m pytest tests/unit/onepassword/... -q`), `revision-major-20260713-001502` (2×), `revision-major-20260711-135410` (2×), `revision-major-20260703-142521` (2×). In every case the error-appended CWD note shows the working directory was **already** `<worktree>/lib/temporal`, so the chained `cd lib/temporal` failed.

**Context:** This is the exact shape of the prior review's MC-2, which the CPI log deferred on 2026-05-09 with watch-criteria *"if MC-2 shape recurs in any repo, ship the 2-line empirical test → revise Pattern D."* **Watch-criteria decisively met** (1 event / 1 run → 36 events / 30 runs). The diagnostic question is also now settled without needing the empirical test: the current harness **documents** that "working directory persists between calls." The Pattern D rule shipped at `e7c8715` (2026-05-03) — *"every Bash command starts at the worktree root; chain with `&&`"* — has an inverted premise for the current harness and is actively **causing** this error class: the model dutifully chains `cd <subdir> &&` from a CWD that is already that subdir.

**Recommendation (claude-dot-files-level, for the architecture session):** revise Pattern D in all 5 task-execution workflow scripts to match the persistent-CWD reality, e.g.: *"Bash CWD persists between calls. Do not blind-chain `cd <subdir> &&` — either use paths relative to wherever you are, use absolute paths, or `cd` with the absolute worktree-rooted path (`cd <worktree>/lib/temporal && ...`), which is idempotent regardless of current CWD."* The absolute-`cd` form is the cheapest drop-in fix: it preserves the chaining habit and cannot fail on repetition.

**Impact:** 36 wasted round-trips this window, plus the follow-on confusion turns after each failure. This is now the second-largest main-loop error class (20% of main-loop errors).

**Confidence:** High — 36 events / 30 runs / 3 weeks, clear cause-effect, premise independently confirmed by harness documentation.

---

### HC-2 — Read-before-Edit failures persist (47 events / 27 runs), and 43% concentrate on the workflow's own `/tmp/claude-pr-*.md` staging files

**Evidence:** `File has not been read yet` occurred **47 times across 27 of 61 runs (44%), 100% in the main loop**. Decomposition of target files:

| target | events |
|---|---|
| `/tmp/claude-pr-body*.md`, `/tmp/claude-pr-comment*.md`, `/tmp/claude-*-pr-body.md` | **20 (43%)** |
| memory files (`MEMORY.md`, memory entries) | 3 |
| scattered repo source/test files (1–2 each) | 24 |

The dominant sub-shape is workflow-mechanics-induced: the engineer **Writes** the PR body to `/tmp/claude-pr-body.md` (per the terminal-output rule), then several turns later tries to **Edit** it (tweaking the body after review findings) without a fresh Read — tripping the read-recency requirement. The memory-file sub-shape is similar: `MEMORY.md` content arrives via system-reminder, not a Read, so a direct Edit fails.

**Trend context:** per-run rate is actually still improving — 3.4/run (2026-05-03, pre-Pattern-B) → 1.5/run (2026-05-09) → **0.77/run now**. The general Pattern B hardening is holding; this is not a regression of the rule. But it remains the **single largest** main-loop error class (26% of main-loop errors), and nearly half of it is one mechanical, targetable shape.

**Recommendation (claude-dot-files-level):** add one line to the PR-submission stage of the task-execution scripts: *"When revising `/tmp/claude-pr-*.md` after its initial Write, Read it first in the same turn — or simply Write the full replacement body instead of Editing."* This targets 43% of remaining events with one sentence; do NOT re-harden the general rule (diminishing returns, per-run rate already halving each cycle).

**Confidence:** High for the pattern and the sub-shape concentration (20 events across many distinct runs). Medium for the projected impact of the fix (self-correcting failures are cheap; the win is ~20 round-trips per 3 weeks plus retry noise).

---

### HC-3 — Review-subagent navigation friction is now the largest overall error cluster (~110 events): EISDIR directory-Reads + nonexistent-path probes

**Evidence:** With subagent events now visible in the logs, two clusters attribute almost entirely to the read-only review agents (code-reviewer, refactoring-evaluator, standards-auditor, quality-control — tools: Read/Grep/Glob only):

- **EISDIR (`illegal operation on a directory, read '...'`): 33 events / 23 runs, 100% subagent.** Agents attempt to Read a directory to list it (they have no Bash/ls), fail, then fall back to Glob.
- **`File does not exist` / `Path does not exist`: ~101 events total, of which 78 (77%) are subagent.** Review agents probe plausible-but-absent paths. One confirmed contributing mechanism (`revision-major-20260721-154459`, refactoring-evaluator): the agent grepped `docs/file_structure.txt`, found `test_onepassword_inpod_roundtrip.py` listed, and probed a path that did not exist in the tree at that commit — i.e., **file_structure.txt drift feeds subagent path probes** (see MC-3).

Every one of these is self-correcting (the agent retries with Glob or a corrected path), but at ~110 events across 61 runs this is the largest error cluster in the window, and each failed probe costs a subagent round-trip inside four reviewer agents per run.

**Recommendation (claude-dot-files-level):** two cheap additions to the review-agent definitions (or the review-stage dispatch prompt): (1) *"You cannot Read a directory — use Glob (`<dir>/*`) to list contents."* (2) *"Verify paths with Glob before Reading; do not trust paths quoted from docs — `docs/file_structure.txt` may lag the tree."* Optionally, include the changed-file list (already known to the dispatching stage from `git diff --stat`) directly in each reviewer's prompt so reviewers start from ground truth instead of re-discovering it.

**Confidence:** High for pattern existence and attribution (33 + 78 events, unambiguous `subagent_type` tags). Medium for impact — friction is real but individually cheap.

---

### HC-4 — RESOLVED BY HARNESS (positive): sequential review-agent dispatch no longer costs wall-clock — background agents run concurrently

**Evidence:** All 54 multi-agent runs still dispatch their 4 review agents (3 narrow-lens + quality-control) **one Agent call per assistant message** — by the prior review's HC-1 framing, "0% parallel dispatch, again." But the execution model has changed: agents now run in the **background** by default. Concrete timeline from `revision-major-20260723-124929`: code-reviewer dispatched 13:02:29, refactoring-evaluator 13:02:37, standards-auditor 13:02:50 (8–13s apart, each dispatch returning an immediate task-started acknowledgment), quality-control at 13:08:25 — i.e., the three narrow-lens agents ran **concurrently** for ~5.5 min, then QC ran sequentially after them exactly as the engineering-quality rule requires. `revision-major-20260717-012616` shows `run_in_background=true` explicitly. Event-order analysis of `revision-major-20260703-142521` confirms: dispatch → immediate ack → next dispatch, with all three agents' interleaved subagent events filling the gap before QC.

**Disposition recommendation:** close the 2026-05-09 CPI deferral ("Sequential review-agent dispatch despite explicit instruction") as **RESOLVED-BY-HARNESS**. The residual wall-clock penalty is ~10–20 seconds of dispatch stagger, not 3× serial agent runtime. Optional cleanup: the workflow scripts' "SINGLE assistant message containing three Agent tool calls" instruction is now unnecessary (and unfollowed); it can be softened to "dispatch all three narrow-lens reviewers back-to-back before processing any results" to match reality.

**Confidence:** High (54/54 runs show the pattern; concurrency confirmed by timestamps and event ordering in multiple runs).

---

### HC-5 — RESOLVED (positive): Pattern A 25K-token Read overflow is extinct — 0 events in 61 runs

**Evidence:** zero occurrences of oversize-Read errors across all 61 logs (grep for the error class returned nothing). Pattern A had persisted through **every** prior review cycle (8/3 → 2/1 events/runs, deferred twice in the CPI log with "project-side allowlist" as the unblocking action). Whether the fix came from harness-side Read defaults (2000-line cap), the skyy-command CLAUDE.md known-large-file guidance, or workflow discipline, the pattern is gone at a 12× larger sample size than any prior window.

**Disposition recommendation:** amend the CPI log's Pattern A entry to note extinction at this cycle (61-run sample). No further action.

**Confidence:** High.

---

## Medium-Confidence Findings

### MC-1 — ScheduleWakeup short-poll anti-pattern appeared, then self-corrected mid-window

**Evidence:** 22 ScheduleWakeup calls across 8 runs, all while waiting on background review agents. Early runs used **short polls** for harness-tracked work — against guidance ("don't poll for harness-tracked work; schedule a long fallback"): `build-phase-20260708-012318` (120/150/120/180s), `build-phase-20260708-141037` (270s), `revision-major-20260708-132527` (270/240s), `build-phase-20260710-033836` (120s). From `build-phase-20260710-173737` onward, every run uses the correct 1200–1500s fallback-heartbeat shape with explicit `stop` calls, and reasons cite "completion notifications are the primary wake signal."

**Also disposes prior CPI item L1** ("ScheduleWakeup invoked in non-loop workflows," deferred at N=3 windows): usage in non-loop workflows is now *legitimate by design* — the harness expects a long fallback while background agents run. The residual watch item is only the **short-poll** shape, which has already disappeared (last occurrence 2026-07-10 03:38).

**Recommendation:** no ship. Update L1's CPI entry: re-contextualized by the background-agent harness; downgrade to watch-only for short-poll (<600s) recurrences while waiting on harness-tracked tasks.

**Confidence:** Medium-high for the trend (clean before/after split at 2026-07-10); the self-correction likely tracks a harness/guidance update rather than anything to ship.

### MC-2 — Abnormal terminations: 4 of 61 runs (6.6%) end with no result event

**Evidence:** `revision-major-20260713-160910` (dies immediately after TaskCreate stage-recording, 253 lines; re-dispatched ~6 min later as `-161524`, which succeeded), `revision-major-20260712-230303` (dies right after launching a background test run), `revision-major-20260712-181148` (dies right after launching background pytest, 0 tool errors up to that point), `build-phase-20260706-193738` (dies mid-thinking-stream). No rate-limit rejections or overage events appear in any of the 61 logs, so throttling is not the visible cause. In each case the operator appears to have re-dispatched manually and the retry succeeded.

**Recommendation:** watch, don't ship. Two of four died immediately after starting a background Bash task, which is suggestive but N=2. If next cycle shows continued ~5%+ abnormal-termination rate, correlate with harness/session logs (outside these JSONLs) — the workflow logs alone cannot distinguish crash vs operator kill.

**Confidence:** Medium for the rate (4/61 clear-cut); Low for any causal story.

### MC-3 — `docs/file_structure.txt` drift feeds subagent path fabrication (project-scope)

**Evidence:** confirmed instance in `revision-major-20260721-154459`: refactoring-evaluator grepped `file_structure.txt`, got a hit for `test_onepassword_inpod_roundtrip.py`, then failed to Read/Grep it — the file was listed in the doc but absent from the tree at that point. skyy-command's CLAUDE.md instructs agents to treat `file_structure.txt` as canonical layout, which makes drift directly misleading. The repo is already actively maintaining the file (commit `cccb730` added missing test-tree entries), which cuts both ways: maintenance happens, but lag windows exist.

**Recommendation (project-scope — surface to the skyy-command session, not a claude-dot-files edit):** consider a one-line caveat in skyy-command CLAUDE.md ("file_structure.txt is the canonical *map*, but verify existence with Glob before Reading — it may lag the tree mid-sprint"), and keep the post-session `/update-file-structure` habit. Pairs with HC-3's agent-side guidance.

**Confidence:** Medium — one fully-traced instance, but the mechanism explains a portion of the 78 subagent path-probe failures and matches the repo's own recent doc-gap commit.

---

## Low-Confidence Findings

### LC-1 — New-harness tool-schema friction (~12 scattered events)

TaskCreate called with missing `description`/`subject` (5), Grep given an unexpected `-l` parameter (3), Read given `offset` in a context that rejected it (2), Read input JSON-parse failures (2). All self-corrected on retry. **Watch-for:** if TaskCreate schema errors persist next cycle, a one-line schema reminder in the stage-recording instruction would fix it; today it's tool-adoption noise.

### LC-2 — Ripgrep 20-second timeouts (3 events)

Three `Ripgrep search timed out after 20 seconds` events, each on broad unanchored patterns over the whole worktree. Self-corrected by narrowing. **Watch-for:** recurrence at >5 events/cycle would justify a "scope Grep to a subtree" hint.

### LC-3 — CPI Pattern C (`find | xargs` whitespace safety): 9 usages, 0 failures

Nine `find … | xargs grep` invocations this window, none `-print0`-safe, all over whitespace-free code paths, none failed or lost data. The watch-criteria ("ship on second *occurrence* of silent data loss") is **not** met — usage is not loss. Continue to defer.

### LC-4 — Multi-session log artifact

`revision-major-20260703-142521.jsonl` contains 4 result events (multiple sessions appended into one log file). Cosmetic; slightly skews per-run metrics for that file. **Watch-for:** if log-per-run invariant matters for future analysis tooling, note it in the review-runs prompt.

---

## Patterns Resolved Since Last Review

Compared against `review-skyy-command-2026-05-09.md` (and 2026-05-03 where relevant):

| prior finding | prior count | this period (61 runs) | status |
|---|---|---|---|
| HC-1: sequential review-agent dispatch | 4/4 runs sequential | 54/54 sequential *messages*, but concurrent *execution* | **RESOLVED-BY-HARNESS** (background agents; see HC-4) |
| MC-1: path fabrication (main loop) | 7 / 1 run | 23 main-loop events / 61 runs (0.38/run vs 1.4/run) | **IMPROVED** per-run; class survives, now dominated by subagents (HC-3) |
| MC-2: Pattern D CWD premise | 1 / 1 run | **36 / 30 runs** | **CONFIRMED + GROWN** — promoted to HC-1 this cycle |
| HC-3 (05-03): Read-before-Edit | 3 / 2 runs (1.5/run at 05-09) | 47 / 27 runs (0.77/run) | **PER-RUN RATE STILL FALLING**; dominant residue is the /tmp PR-body sub-shape (HC-2) |
| LC-1 (05-09): Pattern A 25K Read overflow | 2 / 1 run | **0 / 61 runs** | **RESOLVED** (HC-5) |
| `.claire/` typo (Pattern E) | 0 / 0 | 0 / 61 | **HOLDING** |
| `pytest` missing in env | 0 / 0 | 0 observed in error clusters | **HOLDING** |
| `sudo` / `rm -rf` permission denials | 1 / 1 | 2 permission-prompt events (both `cd`-related, not destructive) | **HOLDING** |

---

## Recurrences from CPI Decisions Log

Cross-referenced against `/opt/skyy-net/claude-dot-files/docs/development/cpi-decisions.md`:

- **Pattern D Bash-CWD wrong premise — DEFERRED at review-runs 2026-05-09 — RECURRING at 36 events / 30 runs this cycle. Watch-criteria ("if MC-2 shape recurs in any repo") decisively MET.** The empirical question the deferral wanted answered is settled: CWD persists between Bash calls (now harness-documented). **Tier-1 ship candidate: revise Pattern D text in all 5 task-execution scripts** (see HC-1).
- **Sequential review-agent dispatch — DEFERRED at review-runs 2026-05-09** with a diagnostic-diff watch-criteria. Sequential *messages* recurred 54/54, but the harness's background-agent default made execution concurrent — the cost premise no longer holds. **Recommend closing as RESOLVED-BY-HARNESS** rather than running the diagnostic (see HC-4).
- **L1 ScheduleWakeup in non-loop workflows — DEFERRED at N=3 windows (2026-05-09)** — recurred at 8 runs this cycle, but usage is now *by-design* (fallback heartbeat while background review agents run). **Recommend re-disposition: REJECT the original framing; keep a narrow watch on short-poll (<600s) shape only**, which already self-extinguished on 2026-07-10 (see MC-1).
- **Pattern A 25K Read overflow — DEFERRED 2026-05-03 and re-deferred 2026-05-09** — **0 events / 61 runs. Recommend amending the entry: EXTINCT at this sample size** (see HC-5).
- **Pattern C `find | xargs` silent data loss — DEFERRED 2026-05-03** — no loss occurrence this cycle (9 benign usages). **Continue to defer.**
- **H2 Bash-iteration cost in review-runs analysis itself — DEFERRED 2026-05-09** (threshold: >30 Bash calls / >10 jq variations on the same files). This analysis used ~15 batched Bash/jq passes over 61 files via a file-list + reusable extraction script — under threshold. **Continue to defer;** the batch-script approach is worth repeating.
- **TS-1/TS-2/TS-3, WI-1/WI-2/WI-3 (sprint-review run #1 deferrals)** — no sprint-review runs in this window; watch-criteria not evaluable. **Continue to defer.**

---

## Metrics

- **Volume/trend:** 61 runs in 3 weeks (~2.9/day) vs 5 runs in the prior 8-day window — dispatch volume has scaled ~5×; total spend $1,301 for the window, cost-per-run flat at ~$23.
- **Reliability:** 57/61 (93.4%) clean success; 4 abnormal terminations (MC-2), all recovered by manual re-dispatch. Zero rate-limit rejections or overage events.
- **Error profile (main loop, 180 events / 3.0 per run, down from 4.2):** Read-before-Edit 47 (26%), `cd lib/temporal` CWD-chain 36 (20%), path-not-found 23 (13%), test/command non-zero exits (iteration, largely expected) and small validation clusters make up the rest.
- **Error profile (subagents, ~140 events):** path probes ~78, EISDIR directory-Reads 33 — concentrated in the 4 read-only review agents.
- **Parallelism:** review agents run concurrently via background dispatch in effectively all 54 multi-agent runs; QC correctly sequential after the narrow-lens trio in all sampled runs.
- **Cache:** prompt-cache read ratios 0.97–0.99 (sampled) — unchanged, excellent.
- **Cost outliers:** delegation-heavy runs (`build-phase-20260708-141037` $63.16, `build-phase-20260708-012318` $60.29, `build-phase-20260706-154447` $58.47, `revision-major-20260717-012616` $50.76 at only 21 main turns) — cost concentrates in subagent work, not main-loop churn; consistent with design, not waste.

---

## Summary

The pipeline is healthy at 5× the prior dispatch volume: 93% clean completion, flat cost-per-run, falling main-loop error rate, and two long-running patterns (25K Read overflow; sequential-dispatch wall-clock cost) resolved outright. **Top priority is HC-1:** the 2026-05-03 Pattern D "CWD reset" rule is confirmed wrong-premised for the current persistent-CWD harness and is now *generating* the error class it was meant to prevent (36 events / 30 runs) — a small text revision across the 5 task-execution scripts, with the `/tmp` PR-body Read-before-Edit sub-shape (HC-2) and the review-agent Glob-not-Read hint (HC-3) as cheap second and third ships. Trend is positive overall; the main new watch item is the 6.6% abnormal-termination rate.
