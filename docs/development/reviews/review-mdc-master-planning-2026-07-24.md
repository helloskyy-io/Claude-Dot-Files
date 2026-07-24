# Workflow Review — mdc-master-planning — 2026-07-24

**Source repo:** `/opt/skyy-net/mdc-master-planning`
**Source machine:** `skyy-net`
**Analysis date:** 2026-07-24
**Logs analyzed:** 25 logs, 2026-07-06 12:46 → 2026-07-20 22:03 (19× `plan-revision`, 4× `revision-major`, 1× `plan-new`, 1× `build-phase`)

## Runs Analyzed

- **Count:** 25 dispatches; 24 completed, 1 aborted mid-run with no result event (`plan-revision-20260706-124620` — ended mid-deliverable, re-dispatched 34 min later as `plan-revision-20260706-132047` on the same home-assistant Phase 1 task)
- **Date range:** 2026-07-06 → 2026-07-20 (15 days)
- **Outcomes:** 24/24 completed runs report `subtype: success`; sampled result texts confirm substantive deliverables (VM-orchestration §5.2 conformance pass, control-plane-migration planning foundation, cross-repo secret-seeding revision)
- **Aggregates:** $481.19 total, mean $20.05/run, mean 85 turns/run, mean 31.9 min/run, ~12.8 hours total wall-clock
- **Note on log shape:** these logs include subagent (review-agent) events inline, distinguished by `parent_tool_use_id`. All per-run analysis below separates main-loop from child-agent activity; earlier-cycle reviews did not have child events in-stream, so raw tool-count comparisons across cycles are not apples-to-apples.

**Prior reviews of this repo:** `review-mdc-master-planning-2026-05-09.md` (4 logs), `review-mdc-master-planning-2026-05-03.md` (7 logs), `review-2026-04-24-mdc-master-planning.md` (20 logs).

---

## High-Confidence Findings

### H1. Sequential review-agent dispatch persists at 17/24 runs — CPI watch-criteria MET, diagnostic complete: model-side, not prompt-side

**Evidence:** Every completed run executed the peer-review stage with the correct agent set (architect + planner + security-auditor + standards-architect + quality-control for planning workflows; code-reviewer + refactoring-evaluator + standards-auditor + quality-control for code workflows). But dispatch mode split:

- **17/24 runs** launched every narrow-lens agent with explicit `run_in_background: false`, one Agent call per assistant message — fully serial, each agent blocking the next. Includes the newest run in the window (`plan-revision-20260720-220314`).
- **7/24 runs** used background dispatch (`run_in_background: true` or omitted → background default): `20260708-160820`, `20260709-160623`, `20260709-205801`, `20260711-013809`, `20260711-144815`, `20260713-182141`, `20260720-203226`. These achieve concurrency; their `ScheduleWakeup` calls are wait-fallbacks ("Waiting on four parallel Stage 4a review agents; fallback poll if no completion notification arrives").

**Diagnostic (per the 2026-05-09 CPI deferral's watch-criteria):** the deferral said "if cycle-3 evidence shows continued sequential dispatch, run the diagnostic diff... If prompts are identical → model-side." `plan-revision.sh` has not changed since 2026-05-29 (commit `5dfebf9`), so all 19 plan-revision runs saw the identical Stage 4a instruction — which is strong and explicit ("Send a SINGLE assistant message containing four Agent tool calls... Do NOT call them one at a time across separate turns"). Same-day pairs diverge (20260720-203226 parallel vs 20260720-220314 serial). **Conclusion: model-side compliance variability, confirmed.** The deferral's prescribed next step on this branch is "ship a worked example showing the literal multi-tool_use block format."

**Important complication before shipping (see M3):** this cycle's data shows NO measured cost or wall-clock penalty for serial dispatch. Serial plan-revision runs averaged ~$16.2 / 28.2 min; background-parallel plan-revision runs averaged ~$22.6 / 27.7 min (scope-confounded, but the direction is the opposite of the May cycle's 43%-per-tool-message claim). Background runs pay for idle/wake cycles (5–6 result events per run vs 1) and fallback polls. The ship decision should weigh whether the instruction itself is still right for the current harness, not just how to get compliance.

**Recommendation:** claude-dot-files-level — surface to the architecture session (not actionable from this project session). Two defensible paths: (a) ship the worked example per the deferral plan, or (b) revise the Stage 4a instruction to explicitly sanction background dispatch as the parallel mechanism and measure again. Path (b) matches what the compliant runs actually did.

**Impact:** wall-clock of the review stage in 17 runs; no demonstrated dollar impact this cycle.

**Confidence:** High (17/24 vs 7/24 is a clear measured split; script provenance verified).

---

### H2. Cross-repo revision-major dispatches get a wrong-repo worktree and self-correct — 4/4 runs, and it drives the dominant error cluster

**Evidence:** All 4 `revision-major` runs in this window were dispatched from mdc-master-planning but targeted **skyy-command** code. The workflow provisioned an mdc worktree; each engineer recognized the mismatch and created its own skyy-command worktree. `revision-major-20260713-182141`'s result says it outright: *"The workflow provisioned a worktree in mdc-master-planning (docs-only), but this task targets skyy-command. I created a dedicated skyy-command worktree..."* The other three runs' logs show engineer-named cross-repo worktrees (`revision-major-phase8-join-20260709`, `join-overrides-20260709`, `sc4-appset-deployer`).

The cross-repo navigation that follows produces the window's largest error cluster (~19 of 49 total tool errors):
- **Read-on-directory probes** (`EISDIR: illegal operation on a directory` on worktree roots, `ENOTDIR` on `.git/HEAD`): ~9 events across 5 runs — the agent verifies a worktree exists by calling Read on the directory instead of `ls`/`test -d`.
- **Stale/guessed cross-repo paths** (`Path does not exist` on files like `.../join-overrides-20260709/lib/temporal/activities/cluster_provision_activities.py`): ~8 events across 4 runs — paths assembled from memory of a differently-named worktree or a pre-refactor layout.

**Recommendation:** claude-dot-files-level — flagging for the architecture session: `revision-major.sh` (and siblings) could take or infer a target-repo parameter so the worktree is provisioned in the right repo, eliminating both the self-correction turn cost and most of this error class. The engineers' self-correction behavior itself is good and worth preserving — no run failed because of this.

**Impact:** ~19 error events + recovery turns spread over 4 runs; revision-major runs are the two most expensive in the window ($40.93 and $27.23).

**Confidence:** High (4/4 revision-major runs, explicit self-report in one result text, error cluster mechanically tied to cross-repo paths).

---

### H3. Read-before-Edit failures regressed: 11 events across 7 runs (was 0 in this repo last cycle)

**Evidence:** `<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>` — main-loop events (review subagents are read-only, so none of these are child noise):

| Run | Events |
|---|---:|
| `plan-revision-20260708-160820` | 3 |
| `plan-revision-20260706-132047` | 3 |
| `plan-revision-20260712-160701` | 1 |
| `plan-revision-20260709-203923` | 1 |
| `revision-major-20260709-171529` | 1 |
| `revision-major-20260709-160623` | 1 |
| `plan-revision-20260706-124620` | 1 |

CPI Pattern B (Read-before-Edit hardening, shipped 2026-05-03 commit `e7c8715`) had driven this to zero in mdc by the 2026-05-09 review. It's back at ~0.44 events/run. Each is cheap to recover (the agent Reads then re-Edits), but 11 events across 28% of runs says the hard time-bound rule ("most recent Read MUST be in this turn or immediately previous turn") is not holding under the longer multi-file revision passes this window's runs perform.

**Recommendation:** claude-dot-files-level recurrence — log in cpi-decisions.md. Before adding text, worth checking whether the events cluster after review-stage resolution passes (file edited early in run, re-edited 40+ turns later after review findings) — if so, the fix may be a Stage 5 "re-Read files you are about to re-Edit" line rather than more Stage 3 emphasis.

**Impact:** ~2 wasted turns/event, ~22 turns across the window; low dollars, but it is a shipped-fix regression, which matters for CPI calibration.

**Confidence:** High (11 events / 7 runs / consistent error signature).

---

## Medium-Confidence Findings

### M1. Path fabrication against mdc's own tree continues at low grade — ~7 events / 6 runs

**Evidence:** guessed paths that don't exist, distinct from H2's cross-repo cluster: `development/epics.md` (`20260709-205801`), `ugrep` warnings on two guessed `github-automation` doc paths (same run), `development/service/secrets/research/secrets_abstraction_findings.md` (`20260706-184350`), a nonexistent `gpu_operations` doc (`20260711-144815`), one file-not-found each in `20260711-190010` and `20260711-175925` (×2). The repo's CLAUDE.md already warns "the model frequently fabricates paths from training-data priors" and mandates reading `docs/file_structure.txt` first.

**Recommendation:** project-side, dispatch-scope: none needed beyond the existing rule — the rate is low (~0.3/run) and every event recovered in one turn via Glob/ls. Watch that it stays flat.

**Confidence:** Medium (recurring but low-rate; each event is cheap).

### M2. Phase-number collision from near-simultaneous dispatches — two "Phase 5" home-assistant docs, later renumbered

**Evidence:** `plan-revision-20260711-175906` and `plan-revision-20260711-175925` were dispatched **19 seconds apart**, reviewing two different NEW home-assistant docs both numbered Phase 5: `phase5_edge_radio_buildout.md` and `phase5_elk_m1_alarm_panel.md`. The tree today holds `phase5_edge_radio_buildout.md` and `phase6_elk_m1_alarm_panel.md` — the ELK M1 doc was renumbered after the fact (commit `076e8f2` created it as Phase 5). The Documentation Standard makes phase numbers immutable creation-order identifiers, so a collision forces exactly this kind of after-the-fact renumber.

**Recommendation:** project-side, operator practice: when dispatching two plan runs into the same domain in one sitting, assign phase numbers in the dispatch prompts rather than letting each run pick "next free number" against the same pre-dispatch tree state. Not a workflow-script defect — the scripts can't see each other's in-flight work.

**Confidence:** Medium (single incident, but the mechanism is unambiguous and repo state confirms the renumber).

### M3. Background-parallel dispatch shows no measured advantage in this harness — wake/idle overhead eats the concurrency gain

**Evidence:** the 7 background-dispatch runs produce 2–6 `result` events each (main loop idles, wakes on task notifications, occasionally burns a `ScheduleWakeup` fallback poll) vs exactly 1 for every serial run. Background plan-revision runs: mean ~$22.6 / 27.7 min; serial plan-revision runs: mean ~$16.2 / 28.2 min. Scope confounds prevent a strong causal claim, but the May-cycle assumption that serial dispatch costs ~43% more per tool-message does not reproduce at the run level in this window.

**Recommendation:** claude-dot-files-level input to the H1 ship decision — measure before mandating either mode. If the review stage is 4 read-only agents of ~3–5 min each, the theoretical parallel saving (~10 min) is evidently being consumed by wait/wake cycles and notification latency.

**Confidence:** Medium (consistent run-level pattern, but confounded by task scope; needs a controlled comparison).

---

## Low-Confidence Findings

- **L1. Truncated tool-input JSON** — 2× `InputValidationError: Read was called with input that could not be parsed as JSON` (`revision-major-20260709-171529`, `-160623`), both with the raw input cut mid-path (186 and 123 bytes). Looks like output-limit truncation mid-tool-call, self-recovered. **Watch for:** recurrence at higher rate; if it grows, it's harness-level, not prompt-level.
- **L2. Hallucinated tool name `Grag`** — 1 event (`plan-revision-20260711-190010`), presumably intended `Grep`; recovered next turn. **Watch for:** any second hallucinated-tool event.
- **L3. TaskCreate schema misuse** — 1 event (`plan-revision-20260706-132047`): passed a `tasks` array instead of `subject`/`description`. **Watch for:** recurrence in workflows that use the task tools.
- **L4. Aborted run without result** — `plan-revision-20260706-124620` (224 log lines, ends mid-deliverable, no result event); the same task re-ran successfully 34 min later. Reads as operator abort/re-dispatch, not a workflow failure. **Watch for:** aborts that do NOT get a successful re-dispatch.
- **L5. Bash quoting one-offs** — 1 backtick-EOF eval error (`20260711-143655`), 2 Edit string-not-found (`build-phase-20260708-160944`, `plan-revision-20260708-013659` — flat vs prior cycle, and NOT clustered in serial-dispatch runs, weakening the May M2 correlation hypothesis).

---

## Patterns Resolved Since Last Review

Compared against `review-mdc-master-planning-2026-05-09.md` and `-2026-05-03.md`:

- **CPI Pattern A — 25K-token Read overflow: RESOLVED.** **Zero** overflow events across all 25 logs (prior: 5 events / 2 runs at 2026-05-09; 14/4 at 2026-05-03; 22/7 at 2026-04-24). The known-large-file `limit:200` guidance now present in dispatch prompts (visible in this review's own task prompt) landed the project-side fix the deferral was waiting on. This is the cleanest resolution in the CPI log's history — recommend amending the Pattern A entry to closed.
- **Grep `file_path` parameter misuse: stays resolved.** 0 events (0 in May, 1 in 2026-05-03, 8 in 2026-04-24).
- **Pattern E (`.claire/` path typo): stays extinct.** 0 events.
- **May M2 (Edit string-not-found clusters in serial runs): not supported this cycle** — 2 events, both in runs that were serial but not clustered; treat the causal hypothesis as unconfirmed.
- **May H1 (parallel dispatch regression): NOT resolved — worsened in share (7/24 parallel ≈ 29% vs 50% in May), but see H1/M3 for the reframe.**
- **Pattern B (Read-before-Edit): REGRESSED — see H3.**

---

## Recurrences from CPI Decisions Log

Cross-referenced against `/opt/skyy-net/claude-dot-files/docs/development/cpi-decisions.md`:

- **"Sequential review-agent dispatch despite explicit instruction" — DEFERRED 2026-05-09 — watch-criteria MET this cycle.** Continued sequential dispatch (17/24 runs). The prescribed diagnostic is complete: script unchanged since 2026-05-29, prompts identical across serial and parallel runs → **model-side**. Deferral's own next step: ship a worked multi-tool_use example. M3's parity data should inform whether that example mandates single-message multi-call or sanctions background dispatch. → Architecture-session decision.
- **CPI Pattern C — `find | xargs` whitespace risk — DEFERRED 2026-05-03, watch-criteria "ship on second occurrence in any repo" — MET.** Two occurrences this cycle (`revision-major-20260713-182141`, `plan-revision-20260711-142041`), both `find ... | xargs grep` without `-print0/-0`. Neither hit whitespace paths (no data loss occurred), but the criteria threshold is now cumulative N=3. → Ship the `find -print0 | xargs -0` rule, or consciously re-defer with a tightened criteria ("on first occurrence against paths containing whitespace").
- **CPI Pattern A — 25K Read overflow — DEFERRED 2026-05-03/05-09 — RESOLVED** (see above); recommend closing the entry with "→ RESOLVED via dispatch-prompt known-large-file guidance, confirmed 0/25 runs 2026-07-24."
- **CPI Pattern B — Read-before-Edit — SHIPPED 2026-05-03 — REGRESSION** (H3): 11 events / 7 runs after two clean cycles. → Log as recurrence; consider the review-resolution-pass hypothesis before adding text.
- **L1 — ScheduleWakeup in non-loop workflows — DEFERRED 2026-05-09 at N=3, "ship reinforcement on run #4."** Six ScheduleWakeup events this cycle, BUT the recorded reasons show all are **legitimate background-agent wait fallbacks** ("Waiting on four parallel Stage 4a review agents; fallback poll..."), which is sanctioned harness behavior — not the May anomaly. → Recommend REJECTING the anomaly framing (the earlier events were likely the same mechanism, unrecognized) rather than shipping reinforcement.
- **H2 (2026-05-09) — Bash-iteration cost in review-runs analysis — threshold ">30 Bash calls / >10 jq variations" NOT met by this run** (~14 Bash calls, most single-purpose). Continue to defer.

---

## Metrics

| Metric | This window (25 logs) | 2026-05-09 (2 task runs) | 2026-05-03 (7 runs) |
|---|---|---|---|
| Success rate (completed runs) | 24/24 = 100% (+1 operator abort) | 2/2 | 7/7 |
| Mean cost / run | $20.05 | $16.61 | $12.03 |
| Mean duration / run | 31.9 min | ~16.8 min | ~17.6 min |
| Mean turns / run | 85 | 58.5 | ~157 |
| Parallel review-agent dispatch | 7/24 (29%) | 1/2 (50%) | 4/5 (80%) |
| 25K-token overflow events | **0** | 5 (2 runs) | 14 (4 runs) |
| Read-before-Edit errors | **11 (7 runs)** | 0 | n/a (pre-fix: 5 mdc) |
| Grep `file_path` misuse | 0 | 0 | 1 |
| `find \| xargs` unsafe pipes | 2 (2 runs) | 0 | 1 |
| Edit string-not-found | 2 (2 runs) | 2 (1 run) | not measured |
| Total tool errors | 49 (~2.0/run) | 7 | — |

**Tool mix (all 25 logs, incl. subagents):** 1483 Read, 862 Grep, 686 Edit, 665 Bash, 208 Glob, 114 Agent, 101 Write.

**Trends:** cost/run continues rising (+$3.44 vs May, +$8 vs 2026-05-03) — but this window's runs are materially bigger (cross-repo revision-major at $40.93/$27.23, a $36.29 build-phase, multi-doc conformance passes), so scope growth, not efficiency loss, is the more defensible read; cost per turn is roughly flat (~$0.24). Error rate ~2/run is low and dominated by one structural cause (H2 cross-repo navigation). Review-stage discipline is structurally excellent: correct lens sets in 24/24 runs, quality-control correctly sequenced after narrow-lens even in background-dispatch runs (verified in `20260711-013809`: QC launched only after all four 4a agents returned), and QC prompts embed the 4a findings verbatim as designed.

---

## Summary

Healthy window: 24/24 completed runs succeeded across 4 workflow types, the long-standing 25K-token overflow pattern is fully resolved (0 events in 25 logs), and review-stage structure (agent lens sets, QC-after-narrow-lens sequencing, findings hand-off) held in every run. The top priority is the sequential-dispatch deferral, whose watch-criteria and diagnostic are now both satisfied (model-side non-compliance, 17/24 runs) — but with the new wrinkle that this cycle's data shows no measurable cost/latency penalty for serial dispatch, so the architecture session should decide between compliance-forcing and instruction revision rather than default-shipping the worked example. Second priority: cross-repo revision-major dispatches provisioning wrong-repo worktrees (4/4 runs self-correct, driving the dominant error cluster), and the Read-before-Edit regression (11 events after two clean cycles).
