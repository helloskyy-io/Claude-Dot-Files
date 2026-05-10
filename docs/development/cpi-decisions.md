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

## 2026-05-04 — ad-hoc reflection (global CLAUDE.md structure)

User-initiated reflection during a session about whether the global CLAUDE.md is too coding-specific for an account that may eventually be used for non-coding work (health/wearables analysis, biomedical research, datacenter orchestration, etc.).

### SHIPPED

- **ADRs vs `docs/standards/` clarification** — added a subsection to global CLAUDE.md documenting that this user's convention is "standards documents serve the role of ADRs." AI was occasionally proposing ADR creation when standards docs would accomplish the same goal. Real recurring confusion → ship.
- **Standards Governance — planning-artifacts clause** — extended the Standards Governance section with explicit "planning artifacts (phase docs, roadmaps, loose-ends, sprints) are NOT covered by this rule and engineers MAY edit them." Plus the contradiction-resolution rule (engineer updates phase doc to remove tension, surfaces standards-side amendment as candidate). Captures real friction the user's PM hit.

### DEFERRED — watch-list

- **Global CLAUDE.md restructure for non-coding contexts**
  - Evidence: hypothetical (no non-coding usage yet)
  - Friction: ~70% of global CLAUDE.md is coding-specific (Code Style, Git, Workflow invocation template, Personal Tooling, Standards Governance, CPI Decisions Log, Dependencies & Tools). When non-coding sessions start, all this coding context will load and bias the AI.
  - Decision: defer per engineering-quality rule (don't build for hypothetical future use)
  - Reasoning: current work is 100% coding; restructure now is preemptive. Better to wait until non-coding usage shows real interference, then restructure with concrete data on what's interfering.
  - **Watch-criteria:** ship the restructure when EITHER (a) non-coding Claude work begins and the coding rules cause concrete friction (wrong suggestions, biased framing, off-topic context loading), OR (b) the user explicitly starts new domain work and wants prep work done in advance.
  - **Recommended restructure approach (when triggered):** move coding-specific sections out of global CLAUDE.md into a `software-engineering-context` skill with description "Use when working in any code repository, modifying source code, dispatching autonomous workflows, or doing software engineering tasks." Skills auto-load via description-matching — same lazy-loading the user already gets via per-repo CLAUDE.md references to standards docs, but using the canonical Claude Code primitive.
  - **Alternative (also valid):** router pattern in CLAUDE.md ("for coding load X, for biomedical load Y") — works empirically (the user already uses this in repos) but is less idiomatic than skills. Either approach is fine; skills are slightly preferred.
  - **Architectural intent clarification (appended 2026-05-09):** user confirmed that claude-dot-files is intentionally scoped to coding projects (any kind) until/unless the repo is split to handle other use cases. "Project agnostic" in this repo means "coding-project agnostic" — NOT "domain agnostic." Implications: (1) the "Friction" framing above slightly overstates the issue — coding context loading in coding sessions is correct, not a bias; (2) the restructure is not pending architectural debt, it's a future fork/split decision that arrives when non-coding scope is added; (3) for now, all global rules and skills should assume coding context as the design baseline. Future CPI cycles should not re-raise this as a freestanding concern — only revisit if/when the user signals scope expansion.

---

## 2026-05-08 — ad-hoc reflection (PM3 flagged via architecture session)

PM3 working on mdc-master-planning PR #24 surfaced standards-amendment candidates to the user. User correctly applied the new claude-dot-files-governance rule (shipped 2026-05-04) and brought the candidates to the architecture session for evaluation. Most items were project-specific (MDC standards work), but two genuine global-validation signals surfaced.

### REJECTED as project-scope

- **PM3's "SHIPPED — Migration Standard §2 cleanup"** — purely MDC-internal mechanical fix (post-restructure path re-pointing). Not architectural. Doesn't belong in this log; it's just a normal commit in MDC.
- **PM3's "DEFERRED — API Standard §2 URL-rename gap"** — moot at evaluation time (user amending API Standard §2 directly in MDC during the same conversation). Pure project-scope.

### Validation signals (no action — confirms recent shipped work is holding)

- **Standards Governance rule held under real load** — Single occurrence. PM3 dispatch surfaced 2 standards-amendment candidates as PR-body notes rather than auto-editing standards. PM split dispositions (one shipped to project standards, one deferred). Confirms the human-in-the-loop discipline shipped 2026-04-23 is internalized in autonomous workflow behavior. **Watch-criteria:** if a future autonomous workflow auto-edits standards docs without surfacing first, we know the rule isn't holding.

- **4-agent parallel review surfaces unique findings — SECOND OCCURRENCE** — Single-run validation 2 days ago (commit 11d020a, plan-revision adding security-auditor) caught security-auditor's host_type false-positive + standards-architect's TBD §6 citation. Today's plan-revision dispatch caught a sibling stale-reference in the same Migration Standard that the original task scope missed — standards-architect's lens specifically. **This is now N=2 across two distinct plan-revision runs.**
  - **Watch-criteria for shipping a docs/guide/workflows.md design-rationale update:** N=3 occurrences across distinct runs, OR a clear cross-cutting pattern emerges (e.g., "standards-architect consistently catches misses the other three agents wouldn't"). Currently at N=2; one more would justify documentation of the design choice.

### Meta-process observation

The new `claude-dot-files-governance.md` rule (shipped 2026-05-04) worked correctly under its first real test even before PM3 had pulled it. PM3's prior memory file plus user correction enforced the right behavior; the user then used the architecture-session escalation path correctly to bring the items here for evaluation. This is the system self-governing as designed.

---

## 2026-05-09 — review-runs cycle (mdc-master-planning + skyy-command)

mdc: 2 plan-revision task-execution runs (~$33), prior CPI cycle e7c8715 fixes validated via Pattern resolution metrics. skyy-command: 5 logs across 8 days — 2× revision-major + 1× build-phase + 1× sprint-review + 1× review-runs.

### SHIPPED

- **4-agent parallel review documentation** (commit added in this session)
  - Evidence: 2026-05-08 watch-criteria N=3 met. mdc plan-revision-003734 dispatched standards-architect alongside architect+planner+security-auditor and surfaced an API Standard §2 URL-rename gap that none of the other 3 agents caught — third confirming instance of the "standards-architect catches what others miss" pattern.
  - Action: added "Review-agent count rationale" section to docs/guide/workflows.md explaining why plan-revision uses 4 agents while other workflows use 3, plus the single-message multi-agent dispatch pattern.

### DEFERRED — watch-list

- **Sequential review-agent dispatch despite explicit instruction** (NEW pattern)
  - Evidence: skyy-command HC-1 (4/4 multi-agent runs sequential, never seen parallel in available logs), mdc H1 (regression in 1/2 plan-revision runs — 0% parallel in 005323 vs 33% in 003734, ~43% cost differential per tool-message)
  - **Critical context:** the parallel-dispatch instruction the reviewers recommended adding **already exists in 4/5 workflow scripts** with strong explicit language ("SINGLE assistant message containing three Agent tool calls", "Do NOT call them one at a time across separate turns"). The naive ship would be a no-op. The actual problem is instruction non-compliance, not missing instruction.
  - Decision: defer; do not ship redundant instruction text
  - Reasoning: per engineering-quality rule, don't build ahead of evidence. We don't yet understand WHY the existing instruction isn't being followed. Could be model-side compliance variability, prompt contamination, context-bloat reducing instruction salience, or something else.
  - **Watch-criteria:** if cycle-3 evidence shows continued sequential dispatch in any repo, run the diagnostic diff (extract actual prompts from parallel vs serial runs, compare). If prompts are identical → model-side, ship a worked example showing the literal multi-tool_use block format. If prompts differ → identify the contamination source and fix that.

- **Pattern D Bash CWD rule may have wrong premise** (NEW)
  - Evidence: skyy-command MC-2 (1 event, exact-shape recurrence after 2026-05-03 ship e7c8715). The chained `cd lib/temporal && python3 -m pytest ...` failed because CWD was already `lib/temporal` (chained `cd` from CWD that already has subdir as leaf).
  - Decision: defer until recurrence confirms premise issue
  - Reasoning: single occurrence after recent ship; could be one-off OR could indicate the rule's premise (that CWD resets between Bash calls) doesn't hold reliably in this harness.
  - **Watch-criteria:** if MC-2 shape recurs in any repo, ship the 2-line empirical test (`pwd` → separate Bash call → `pwd` → confirm whether CWD persists) → revise Pattern D based on findings.

- **L1 — ScheduleWakeup invoked in non-loop workflows** (slow-burn pattern at N=3 windows)
  - Evidence: third occurrence across three review-runs windows, one event per window — plan-new-20260430-153526 (2026-05-03 cycle), plan-revision (2026-05-09 same-day predecessor), plan-revision-005323 (this cycle).
  - Decision: defer per discipline; not yet at ship threshold
  - Reasoning: each window is single-observation but the cumulative pattern across windows is now slow-burn at N=3.
  - **Watch-criteria:** ship reinforcement on run #4 if recurrence continues. If next cycle has zero ScheduleWakeup events in non-loop workflows, downgrade to REJECTED (intermittent, not systemic).

- **H2 — Bash-iteration cost in review-runs analysis itself** (NEW, claude-dot-files-level)
  - Evidence: 2026-05-09 mdc same-day predecessor (review-runs-20260509-191558) issued 47 tool calls / 42 Bash, of which ~25 were jq query iterations on the same 2 files. $2.80 for analysis vs $1.53 prior cycle.
  - Decision: defer single-occurrence per engineering-quality rule
  - Reasoning: N=1 observation that the iteration pattern is meaningful overhead. Pattern produced a usable report so it's not blocking. Mitigation would be a reusable jq snippet library or `tools/log-stats.sh` companion to skip query-tuning.
  - **Watch-criteria:** if next review-runs cycle on similar data shows >30 Bash calls / >10 jq variations on same files, ship a workflow-level snippet library or helper script.

### Recurrences (CPI Pattern A and C re-defers)

- **CPI Pattern A — 25K-token Read overflow** — DEFERRED at 2026-05-03 cycle. Recurring in BOTH repos this cycle: mdc 5 events / 2 runs (flat per-run rate ~2.5 events/run, vs prior 2.0), skyy-command 2 events / 1 run. Watch-criteria from prior deferral: ">2× current rate after project-side allowlist work lands." **Project-side allowlist still has not landed in either repo, so the criteria precondition is not met.** Continue to defer prompt-side reinforcement; project-side allowlist is the unblocking action.

- **CPI Pattern C — `find | xargs` whitespace silent data loss** — DEFERRED at 2026-05-03 cycle. Watch-criteria: "ship `find -print0 | xargs -0` rule on second occurrence." Zero occurrences this cycle. Continue to defer.

### REJECTED as project-scope (surface to project sessions per claude-dot-files-governance)

- **mdc-master-planning known-large-file allowlist** — Pattern A recurrence in mdc requires project-side action. Reviewer recommended adding a paragraph to mdc's CLAUDE.md naming `development/sprints.md`, `development/common/loose_ends/sprint_*_loose_ends.md`, `development/common/networking/phase_*.md`, `development/service/<service>/phase*.md` as known-large where Read MUST pass `limit:200` on first read. Lives in mdc-master-planning session.

- **skyy-command known-large-file addition** — Pattern A recurrence on `sprint_1_loose_ends.md` in skyy-command (2 events / 1 run). Same shape as mdc allowlist. Add to skyy-command's CLAUDE.md.

- **skyy-command repo-layout cheat sheet** — MC-1 path fabrication recurrence (7 events / 1 run, same class as prior HC-2). Reviewer recommended a 6-10 line cheat sheet in skyy-command's CLAUDE.md showing canonical internal layout and the test-runner convention. Lives in skyy-command session.

### Validation signals (no action — confirms recent shipped work is holding)

- **Pattern E (`.claire/` typo) shipped 2026-05-03** — 27/5 → 0/0 across both repos this cycle. Holding cleanly.
- **Pattern B (Read-before-Edit hardening) shipped 2026-05-03** — 24/7 → 3/2 in skyy-command (~12% of prior rate). Substantially improved. mdc shows zero "File has not been read yet" events in either plan-revision.
- **Pattern D (Bash CWD reset rule) shipped 2026-05-03** — original 80/9 shape extinct (skyy-command 1/1), but new shape MC-2 appeared (1 occurrence). Mixed validation; see deferred entry above.
- **N=3 watch-criteria for 4-agent parallel review documentation** — MET this cycle. Shipped (above).

### Meta-process observation

The reviewers' recommendations on the dominant finding (sequential dispatch) were both based on the assumption that the parallel-dispatch instruction was missing — when in fact it exists in strong language across 4 of 5 workflow scripts. This is a useful calibration signal: review-runs analyses should verify against the current state of workflow scripts before recommending text-additions. Worth noting for future review-runs prompt evolution that the analyst should grep the workflow scripts for existing instruction before recommending new instruction text.

### Architecture-session item surfaced ad-hoc (2026-05-09)

- **No `--base-branch` flag in workflow scripts** (NEW, claude-dot-files-level)
  - Evidence: User's mdc-master-planning PM session needed to dispatch revision-major.sh against `feature/standards-cleanup` (not main). Workflow scripts have no `--base-branch` flag — operator must (a) checkout the feature branch before running, AND (b) inject explicit `gh pr create --base feature/standards-cleanup` instruction into the prompt or the engineer's PR will target main.
  - Decision: defer per engineering-quality rule (single occurrence)
  - Reasoning: defensive-prompt workaround works for this dispatch. Adding the flag to all 5 task-execution workflows (revision, revision-major, build-phase, plan-new, plan-revision) is real script work; defer until recurrence justifies the build cost.
  - **Watch-criteria:** if a second feature-branch dispatch comes up in any repo, ship `--base-branch <name>` to the workflow scripts. Implementation must do BOTH: (a) checkout the base branch before worktree creation, (b) auto-inject `gh pr create --base <name>` into the engineer's prompt.

---

## How to read this log

**For run #2 prep:** scan DEFERRED sections. Items with `Watch-criteria` met by run #2 evidence become Tier 1 ship candidates. Items still deferred get re-deferred with updated counts.

**For workflow archeology:** SHIPPED items have commit references — `git show <sha>` shows what actually changed.

**For diminishing-returns assessment:** ratio of deferred-then-resurfaced vs deferred-and-never-recurred is the real signal of CPI maturity. High recurrence rate → we're undercalibrating (shipping too few). High never-recurred rate → we're correctly calibrating (deferring noise from one-offs).
