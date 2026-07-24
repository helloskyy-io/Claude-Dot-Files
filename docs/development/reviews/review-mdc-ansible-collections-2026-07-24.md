# Workflow Review — mdc-ansible-collections — 2026-07-24

**Source repo:** `/opt/skyy-net/mdc-ansible-collections`
**Source machine:** `skyy-net`
**Analysis date:** 2026-07-24
**Logs analyzed:** 5 logs, 2026-07-13 → 2026-07-20 (2× revision, 3× revision-major)

## Runs Analyzed

| # | Log File | Workflow | Outcome | Duration | Cost | Turns |
|---|----------|----------|---------|----------|------|-------|
| 1 | `revision-20260713-211954` | revision | Success (PR #19, nvcc conformance path fix) | ~3.2m | $1.36 | 23 |
| 2 | `revision-major-20260713-182147` | revision-major | Success (PR #18, install_cuda/install_nvidia_driver) | ~23.8m | $7.69 | 57 |
| 3 | `revision-major-20260716-015018` | revision-major | Success (PR #20, NVIDIA container-toolkit roles) | ~27.9m | $8.74 | 71 |
| 4 | `revision-major-20260716-030335` | revision-major | Success (PR #21, k3s secrets-encryption) | ~17.1m (5 segments) | $11.10 (cumulative) | 86 (47+1+1+4+33) |
| 5 | `revision-20260720-192505` | revision | Success (PR #22, install_nextcloud_server role) | ~3.9m | $1.69 | 25 |

All 5 runs succeeded and produced merged PRs (confirmed against `git log`: a013ba3/#23, d708fde, 5fc72a6/#22, 6abd21c/#21). **Zero user interventions** across all 5 logs (no top-level user text messages beyond the workflow prompts). This is the **first review for mdc-ansible-collections** — the unlabeled `review-2026-04-10.md` was checked and contains zero references to Ansible/roles/molecule, so it covers a different repo; the per-repo reviews from 04-24 and 05-03/05-09 cover skyy-command and mdc-master-planning.

## High-Confidence Findings

### HC-1 — Parallel review-agent dispatch is now the norm (SUCCESS — preserve; resolves prior deferred pattern)

- **Evidence:** In all 3 revision-major runs, the three narrow-lens review agents were dispatched in a **single assistant message** (three `Agent` tool_use blocks sharing one message ID: `msg_011CczXjRJLKgZjoX8RNHZHi` in 182147, `msg_011Cd4ufv2CLAbHgD4LpSPxa` in 015018, `msg_011Cd515sPgocc7qdviU29nA` in 030335), with the 4th agent (quality-control) dispatched **sequentially after** in a separate message — exactly the parallel-narrow-lens-then-sequential-integration pattern the workflow scripts and `engineering-quality.md` prescribe.
- **Confidence:** High — 3/3 multi-agent runs in this window, unambiguous message-ID evidence.
- **Impact:** Directly contradicts the 2026-05-09 CPI deferral "Sequential review-agent dispatch despite explicit instruction" (skyy-command HC-1 / mdc H1). The watch-criteria was "if cycle-3 evidence shows continued sequential dispatch, run the diagnostic diff." Cycle-3 evidence in this repo shows **full compliance** — no diagnostic needed from this repo's side.
- **Recommendation:** No action. Amend the CPI deferred entry with this repo's compliance data; if skyy-command's next review shows the same, downgrade the deferral to resolved.

### HC-2 — Clean run record: previously-shipped CPI fixes are holding in this repo

- **Evidence across all 5 logs:**
  - **Pattern A (25K-token Read overflow):** 0 events (grep for token-limit errors: 0 in all 5 files).
  - **Pattern B (Read-before-Edit):** 0 "has not been read yet" events in all 5 files.
  - **Pattern E (`.claire/` long-path typo class):** 0 events.
  - **Pattern C (`find | xargs` data loss):** 0 error events.
  - **ScheduleWakeup in non-loop workflows (L1):** 0 actual tool calls in all 5 runs (grep hits were tool-name listings in init events only).
- **Confidence:** High — consistent absence across 5 runs.
- **Impact:** The 2026-05-03/05-09 shipped fixes generalize to this repo. Error tool_results totaled ~14 across all 5 runs (~2.8/run), all self-recovered without user help.
- **Recommendation:** Preserve. Per L1's own watch-criteria ("if next cycle has zero ScheduleWakeup events in non-loop workflows, downgrade to REJECTED"), this repo's data supports the downgrade.

## Medium-Confidence Findings

### MC-1 — Recurrence: Bash CWD **persists** between calls — Pattern D's premise is wrong (watch-criteria MET)

- **Evidence:** `revision-20260713-211954` — Bash call #2: `cd skyy_net/common/roles/install_cuda && find . -type f ...`; Bash call #3: `cd skyy_net/common/roles/conformance && ...` failed with `/bin/bash: line 1: cd: skyy_net/common/roles/conformance: No such file or directory` — the relative `cd` failed because the CWD **persisted** at `install_cuda` from the prior call. Recovery: call #5 switched to an absolute worktree path.
- **Confidence:** Medium as an in-window pattern (1 event / 1 run), but this is the **second cross-cycle occurrence** of the exact MC-2 shape deferred at 2026-05-09 (skyy-command, chained `cd lib/temporal && pytest` failing for the same reason). The deferral's watch-criteria — "if MC-2 shape recurs in any repo, ship the 2-line empirical test → revise Pattern D" — is now **met**.
- **Corroboration:** The current harness Bash tool documentation explicitly states "Working directory persists between calls" — the shipped Pattern D rule text ("every Bash command starts at worktree root") asserts the opposite. The rule's premise is contradicted by the harness itself.
- **Recommendation (claude-dot-files-level):** Revise the Pattern D rule text in the 5 task-execution scripts from "every Bash command starts at worktree root" to "CWD persists between Bash calls — always `cd` from an absolute path or use absolute paths; never chain a relative `cd` assuming worktree-root start." This is a text correction to a shipped rule whose premise is now demonstrated wrong in two repos.

### MC-2 — Cross-repo path fabrication for standards/skills files

- **Evidence (2 events / 2 runs):**
  - `revision-major-20260716-030335`: Read of `/opt/skyy-net/mdc-master-planning/standards/development/security/credential_lifecycle_standard.md` → "Path does not exist" (actual path: `standards/development/secrets/credential_lifecycle.md` — wrong directory AND wrong filename, fabricated from naming priors).
  - `revision-major-20260713-182147`: Read of `/opt/skyy-net/claude-dot-files/config/skills/quality-control-methodology/SKILL.md` → "Path does not exist" (fabricated skill path).
- **Confidence:** Medium — 2 events / 2 runs, same class as skyy-command MC-1 path fabrication (rejected there as project-scope, fixed via CLAUDE.md cheat-sheet).
- **Self-healing observed:** the 030335 run recognized the miss, found the real path, and **indexed the Credential Lifecycle Standard in this repo's CLAUDE.md** as part of its PR (visible in the current CLAUDE.md standards list) — the project-side fix pattern applying itself.
- **Recommendation (project-side, per claude-dot-files-governance):** No claude-dot-files action. In the mdc-ansible-collections session, verify CLAUDE.md's standards index stays complete as new standards get cited; the 030335 self-fix already closed the biggest gap. The claude-dot-files skill-path fabrication (182147) is a single event — watch.

## Low-Confidence Findings

- **LC-1 — Read called on a directory** (2 EISDIR events / 1 run, 030335, target: the worktree root itself). Recovered immediately. Watch for recurrence; if it becomes a per-run tax, the fix is prompt-side ("Read requires a file path, not a directory").
- **LC-2 — Read invoked with invalid parameter name `parameter`** (1 event, revision-20260713: `InputValidationError ... An unexpected parameter \`parameter\` was provided`). One-off tool-schema slip; recovered. Watch only.
- **LC-3 — Long chained-Bash exploration in minor-revision runs.** Both revision runs used large `cat`/`sed`/`find` chains via Bash instead of Read/Grep (20 Bash / 0 Read in 20260720). Cost-wise this **worked well** — both runs finished in 23–25 turns for ~$1.4–1.7 — but two mid-chain `Exit code 1` failures (20260720, 20260713) show the fragility of `&&`-chains, and `find ... | while read f` is whitespace-unsafe (same class as CPI Pattern C, though repo paths contain no spaces and no data was lost). Not recommending a change — the economics favor the current behavior — but if a chained-cat failure ever silently truncates output that a later stage depends on, escalate to Pattern C treatment.
- **LC-4 — Session fragmentation in 030335.** The log contains 5 init events / 5 result events (turns 47+1+1+4+33, cumulative $11.10) — harness continuation segments, not user interventions (the segments resume mid-work, e.g. addressing a standards-auditor Critical). This was the most expensive run in the window. Single observation; watch whether multi-segment runs correlate with cost outliers in future cycles.

## Patterns Resolved Since Last Review

No prior review exists for this repo, so no repo-local baseline. Against the **global** CPI watch-list, this repo's data resolves or supports resolving:

- **Sequential review-agent dispatch (deferred 2026-05-09)** → contradicted by 3/3 parallel-compliant runs here (HC-1).
- **L1 ScheduleWakeup in non-loop workflows (deferred 2026-05-09)** → 0 occurrences; supports the REJECTED downgrade path named in its watch-criteria.
- **Patterns A / B / C / E** → 0 events each in this window (HC-2).

## Recurrences from CPI Decisions Log

- **Pattern D "Bash CWD reset rule may have wrong premise" (MC-2) — DEFERRED at 2026-05-09 review-runs cycle — RECURRING this cycle (revision-20260713-211954, exact shape: relative `cd` failing because CWD persisted). Watch-criteria MET** ("if MC-2 shape recurs in any repo"). Now N=2 across repos, and the harness's own Bash documentation confirms CWD persistence. Ship the Pattern D text revision (see MC-1 above). This is the one ship candidate from this review.
- **Pattern A (25K Read overflow) — DEFERRED 2026-05-03, re-deferred 2026-05-09** — 0 events this cycle in this repo. Precondition (project-side allowlist) still governs; no new evidence either way from this repo.
- **Pattern C (`find | xargs`) — DEFERRED 2026-05-03** — 0 error events. Note the whitespace-unsafe `find | while read` near-miss class in LC-3; does not meet the "second occurrence" bar (no failure occurred).
- **Sequential-dispatch deferral (2026-05-09)** — recurrence check ran; result is compliance, not recurrence (HC-1).

## Metrics

- **Success rate:** 5/5 runs produced merged PRs; 0 user interventions; 0 aborted runs.
- **Turns:** revision avg 24 (23, 25); revision-major avg 71 (57, 71, 86).
- **Cost:** revision avg $1.53; revision-major $7.69–$11.10 (avg ~$9.18). Output tokens: 13–15K (revision), 55–70K total (revision-major).
- **Duration:** revision ~3–4 min; revision-major ~17–28 min.
- **Failure types (all recovered, ~14 error tool_results total):** fabricated cross-repo paths (2), CWD-relative cd failure (1), EISDIR directory Read (2), invalid Read parameter (1), mid-chain Bash exit-1 (2), transient file/glob misses (rest).
- **Review-agent value confirmed again:** standards-auditor caught a **Critical** miscitation in 030335 (pervasive wrong attribution of the `--secrets-encryption` mandate to "Container Clustering Standard §4.5") that the engineer then corrected across 9 occurrences before merge — another instance of the "review agents catch what the engineer baked in" pattern.
- **Disposition discipline visible:** 015018 surfaced the pre-existing stale `skyy_net/common/README.md` instead of scope-creeping (backfilled later in commit 4a46cf9); 182147 deferred 3 items all with findable pointers; 030335 deferred 1 with a tracker.

## Summary

This repo's workflow health is excellent: 5/5 successful PR-producing runs with zero user interventions, full parallel-dispatch compliance in every multi-agent run, and zero recurrence of the previously-shipped failure patterns (A/B/C/E, ScheduleWakeup). The one actionable item is a cross-cycle recurrence whose watch-criteria is now met: the Pattern D "CWD resets" rule premise is demonstrably wrong (CWD persists between Bash calls, per both observed failures and current harness docs) and the rule text in the 5 task-execution scripts should be revised. Everything else is either self-healed project-side (CLAUDE.md standards indexing) or watch-only noise.
