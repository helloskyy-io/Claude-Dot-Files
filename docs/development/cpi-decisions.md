# CPI Decisions Log

This log tracks every decision made during continuous process improvement cycles — what was shipped, what was deferred, what was rejected, and why. The purpose is to surface patterns across cycles: when a deferred item recurs, we have evidence to ship. When a rejected pattern reappears, we re-evaluate.

## How this works

- Each CPI cycle (`review-runs` analysis OR `sprint-review` run OR ad-hoc reflection) produces findings
- Each finding gets logged here with one of three dispositions: **SHIPPED**, **DEFERRED**, or **REJECTED**
- **DEFERRED** items have explicit **watch-criteria** — what would trigger reconsideration
- **SHIPPED** items have commit references for traceability
- Append-only structure — entries don't get deleted, just amended with status updates when previously-deferred items get shipped (or rejected items get re-evaluated)

## Update cadence

- After every `review-runs` cycle that produces shippable or deferrable findings
- After every `sprint-review` run
- After ad-hoc Reflection feedback that drives decisions

## Why "watch-criteria" matters

Single-occurrence findings are tempting to ship because they're often real. But the engineering-quality rule applies to us too: don't build ahead of evidence. Deferring with explicit watch-criteria means:

1. We don't lose the finding — it's documented here for next-cycle reference
2. We have a clear trigger for reconsideration (recurrence in N more cycles, asymmetric risk class confirmed, etc.)
3. We avoid prompt bloat from ruling-for-everything

The asymmetric exceptions (silent data loss, security incidents, correctness regressions) get noted in the watch-criteria so they're easier to recognize on recurrence.

---

## 2026-05-03 — `review-runs` cycle (mdc-master-planning + skyy-command)

22 logs total. First post-CPI-cycle-2/3 review with sufficient post-fix data.

### SHIPPED

- **Pattern B — Read-before-Edit hardening** (commit e7c8715)
  - Evidence: cross-review, 29 events total (5 mdc + 24 skyy-command)
  - Replaced soft conditional rule ("if any tool could have rewritten") with hard time-bound rule ("most recent Read MUST be in this turn or immediately previous turn")
  - Applied to all 5 task-execution scripts

- **Pattern D — Bash CWD reset rule** (commit e7c8715)
  - Evidence: 80 events / 9 runs (skyy-command HC-2)
  - New rule: every Bash command starts at worktree root; chain with `&&` or use absolute paths
  - Applied to all 5 task-execution scripts

- **Pattern E — Prefer relative paths inside worktree** (commit e7c8715)
  - Evidence: 27 events / 5 runs (skyy-command HC-1, `.claire/` typo for `.claude/`)
  - New rule encourages relative paths to eliminate long-absolute-path typo class
  - Applied to all 5 task-execution scripts

### DEFERRED — watch-list

- **Pattern A — 25K-token Read overflow**
  - Evidence: persistent across cycles. 14 events / 4 runs (mdc 2026-05-03), 8 events / 3 runs (skyy 2026-05-03), prior cycles also had this pattern
  - Decision: rule already exists, issue is enforcement not text
  - Reasoning: adding more text to existing rule won't change behavior; the right fix is project-side (curated `phase_calico_api_server.md`, `sprint_1_loose_ends.md` known-large-file allowlist in CLAUDE.md). Out of scope for claude-dot-files.
  - **Watch-criteria:** if persists at >2× current rate after project-side allowlist work lands, OR if project-side allowlist proves insufficient → revisit prompt-side reinforcement

- **Pattern C — `find | xargs` whitespace silent data loss**
  - Evidence: 1 event / 1 run (mdc-master-planning)
  - Decision: defer until recurrence
  - Reasoning: single occurrence; per engineering-quality rule, don't build ahead of evidence. Asymmetric (silent data loss class) but consistency with our discipline matters.
  - **Watch-criteria:** ship the `find -print0 | xargs -0` rule on second occurrence in any repo

### Validation signals (no action — confirms prior shipped fixes are working)

- **Parallel review-agent dispatch** is the new norm in 4/5 review-stage runs (H1 from CPI cycle 2-3 paid off)
- **Grep `file_path` parameter mistake** nearly extinct: 8→1 (mdc), 12→4 (skyy)
- **Unbounded re-reads** peak dropped from 17× to 5× in skyy-command

---

## 2026-05-03 — `sprint-review.sh` run #1 (skyy-command, first ever execution)

Cost: $18.20. Wall time: 11 min. Sprint scope: Sprint 1 — Cluster Provisioning.

**Production value delivered:** caught 2 leaked credential files (one with an n8n encryption key — committed since 2026-04-14, ~3 weeks of exposure), unauthenticated API surface across 26 Django infra views, Django Posture A regression cutting across multiple files, worker chart duplication invisible to per-PR review. Created 46 unit + integration tests. Estimated value: multiples of monthly workflow runtime cost in remediation labor saved.

**Workflow itself:** signal-to-noise excellent (1 noise finding in ~25). Severity calibration well-grounded. Sprint-vs-historical distinction worked correctly. Surface-only mode for refactoring/security findings was respected.

### DEFERRED — watch-list (all single-run evidence; defer per engineering-quality rule)

The first run of any new workflow has the highest rate of friction observations because there's no calibration baseline. We defer all and revisit in run #2 to distinguish first-run noise from real patterns.

- **TS-1 — Components touched explicit in Stage 1**
  - Evidence: 1 occurrence (Post-Run Reflection)
  - Friction: engineer found the phrasing ambiguous about whether to enumerate components or rely on git diff stats
  - Decision: defer
  - Reasoning: one engineer's confusion may be calibration vs systemic. First-run ambiguities are common.
  - **Watch-criteria:** ship clarification if a future sprint-review reflection notes the same ambiguity

- **TS-2 — Surface-only mode boundary case (test conftest fixes)**
  - Evidence: 1 occurrence (Post-Run Reflection)
  - Friction: engineer was unsure whether to fix a `conftest.py` blocking test runs. Chose conservative read (don't modify, document instead).
  - Decision: defer
  - Reasoning: engineer correctly chose conservative read; rule worked as intended. Preemptive clarification is preemptive.
  - **Watch-criteria:** ship clarification if future engineer chooses incorrectly (modifies source-code refactoring under cover of "test tooling fix"), OR if the same boundary ambiguity recurs

- **TS-3 — Deferred-work convention assumption**
  - Evidence: 1 occurrence (Post-Run Reflection)
  - Friction: workflow assumed engineer knew project's loose-ends file conventions (`sprint_X_loose_ends.md` with `2-0a.15`-style identifiers). First-time use against a less-structured repo wouldn't have these handles.
  - Decision: defer
  - Reasoning: pure speculation about future use; we've only run sprint-review on skyy-command which HAS the conventions
  - **Watch-criteria:** ship if sprint-review runs on a repo without loose-ends conventions and engineer can't figure out where to file deferrals

- **WI-1 — Reproduce-claim discipline (highest-priority deferral)**
  - Evidence: 1 occurrence (PM3 evaluation)
  - Friction: 14 integration-test-failures claim couldn't be reproduced via canonical master-runner invocation. Possible false-positive finding made it into the report.
  - Decision: defer (acknowledged tempting because false-positives are asymmetric — they cause unnecessary engineering work)
  - Reasoning: same single-occurrence logic that applied to Pattern C `find | xargs` silent data loss, which we also deferred. Evidence threshold should be consistent.
  - **Watch-criteria:** ship the canonical-runner cross-check rule on second occurrence of unreproducible test-failure findings. Worth flagging for explicit watch in run #2.

- **WI-2 — File-state snapshot timing**
  - Evidence: 1 occurrence (PM3 evaluation)
  - Friction: line counts in report were ~150 lines stale by report-write time (1417 reported vs 1626 actual)
  - Decision: defer
  - Reasoning: could be one-off (Stage 4 modified files between analysis and report) or systemic; can't tell from one run
  - **Watch-criteria:** ship if future runs show similar staleness in file metrics

- **WI-3 — Secret-remediation guidance specificity**
  - Evidence: 1 observation (PM3 evaluation, polish suggestion)
  - Friction: secret-leak findings could include copy-paste-ready `git filter-repo` invocation
  - Decision: defer
  - Reasoning: nice-to-have polish, no failure occurred — engineer surfaced findings correctly, just without operator-convenience commands
  - **Watch-criteria:** ship if operators repeatedly need to look up remediation commands manually across multiple sprint-reviews

### What sprint-review run #1 validates (no action — confirms design)

- Wholistic lens caught issues per-PR review can't (Django Posture A regression, worker chart duplication)
- Sprint-vs-historical distinction works correctly
- Surface-only mode for refactoring/security was respected
- Stage 4 actually delivered tests (46 of them) — not theatrical "we identified gaps"
- Severity calibration is well-grounded
- Cost-benefit overwhelmingly positive on this single run alone

---

## How to read this log

**For run #2 prep:** scan DEFERRED sections. Items with `Watch-criteria` met by run #2 evidence become Tier 1 ship candidates. Items still deferred get re-deferred with updated counts.

**For workflow archeology:** SHIPPED items have commit references — `git show <sha>` shows what actually changed.

**For diminishing-returns assessment:** ratio of deferred-then-resurfaced vs deferred-and-never-recurred is the real signal of CPI maturity. High recurrence rate → we're undercalibrating (shipping too few). High never-recurred rate → we're correctly calibrating (deferring noise from one-offs).
