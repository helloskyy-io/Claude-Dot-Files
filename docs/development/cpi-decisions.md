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

## 2026-05-27 — Two project handoffs evaluated (Daryl tactical-bandaid + Vault Phase 1 retrospective)

Two PM handoffs arrived the same day routing project-level content to claude-dot-files via the governance rule. Both followed correct routing process (governance worked as designed); both rejected on content grounds. Captured here as calibration signal — the underlying issue surfaced is doc scope ambiguity, addressed by clarification commit alongside this entry.

### Handoff 1 — PM2/PM3 Daryl tactical-bandaid append (skyy-net MDC project)

PM3 wrote a 60+ line tech-debt entry about a tactical bandaid for the customer-browser Phase 1 launch (Daryl test-deployment), proposing it land in `cpi-decisions.md` DEFERRED section. PM2 routed it here per claude-dot-files-governance.

**REJECTED as project-scope.** Reasoning:
- Entry is project-level tech debt (specific customer Daryl, specific VM docker-internal-005, specific service SkyyGate, Sprint-3 phase references, project commit SHAs). Zero claude-dot-files tooling implications.
- Content also violates standards-authoring discipline (dates, sprint refs, commit SHAs, customer/service specifics, narrative retrospective material) — would set bad precedent for cpi-decisions.md content shape.
- Routing process was correct; content interpretation was not. Redirected to skyy-net's `/development/common/loose_ends/` or customer-browser phase doc as a deferred-with-retirement entry.

### Handoff 2 — PM2 Vault Phase 1 closeout (4 cross-project tooling candidates)

PM2 surfaced 4 candidates from an 8-defect closeout of MDC Vault Phase 1: chart-render verification agent, engineer task brief template/skill, "no manual workarounds" rule promotion, and a CPI log entry.

**Dispositions:**

- **Item 1 — chart-render verification agent → REDIRECTED to project-side.**
  - Evidence: 4 of 8 production defects in single project, single cycle
  - Reasoning: stack-specific (Helm + K8s + cluster access required), assumes project-specific configuration (cluster targeting, chart paths, lifecycle states, §6 matrix), N=1 across projects. claude-dot-files stays stack-agnostic per architectural intent.
  - Right home: `mdc-master-planning/.claude/agents/chart-render-reviewer.md` as project-level agent. Claude Code supports per-project `.claude/agents/`.
  - **Watch-criteria for future claude-dot-files-level ship:** second project's deployment cycle hits the same chart-defect class with same root cause → two-project evidence justifies generalizing into stack-aware skill or agent.

- **Item 2 — engineer task brief template/skill → REDIRECTED to project-side.**
  - Evidence: PM-authoring-time discipline gap. PM's own framing: "my hand, sharper next time."
  - Reasoning: a claude-dot-files skill can't force a PM to use a checklist in interactive mode. For autonomous workflows, the brief is the operator's input — checklist must be applied before invocation, which is PM workflow not Claude tooling. Also requires project-specific standards links to be useful.
  - Right home: template in mdc-master-planning's `docs/standards/` or `docs/guide/` ("How to write an engineer task brief for a service-deployment workflow"). PMs paste from template each time.
  - **Watch-criteria for future claude-dot-files-level ship:** if 2+ projects independently develop similar task-brief templates, generalize.

- **Item 3 — "no manual workarounds for missed automation" rule promotion → REJECTED.**
  - Reasoning: already covered by `engineering-quality.md` sections "No bandaids — solve root causes," "Push back on shortcuts," and "When the user asks for the easy path anyway." Adding a more specific rule duplicates content and pushes always-loaded layer toward bloat.
  - "Manual workaround for missed automation" is one specific instance of "bandaid over root cause" — existing rules apply.
  - MDC memory entry stays as MDC's session-specific reminder; that's the right home for project-experienced lessons that global rules already cover.

- **Item 4 — CPI log entry → SHIPPED** (this entry).

### Meta-process observation

Two consecutive same-day handoffs misrouted project-level content to claude-dot-files. The routing mechanism (governance rule) worked perfectly — both PMs raised before editing. The content interpretation was off in both cases.

Underlying contributor: scope ambiguity in `docs/guide/cpi-cycle.md` ("Both feed cpi-decisions.md" without distinguishing project-level from tooling-level findings). Clarified in the same session alongside this entry — new "What belongs in cpi-decisions.md (and what doesn't)" subsection with explicit examples and the test ("would another claude-dot-files-using project benefit from this decision being recorded?").

**Calibration signal:** doc clarity catches misrouting before it ships. The fact that both handoffs were correctly REJECTED rather than absorbed is the governance discipline working — but doc ambiguity costs PM time on the upstream side. Clarification is the preventive fix.

---

### Routed from skyy-command sprint_2_loose_ends.md §2-0a.15 (5 candidate improvements, evaluated 2026-05-12)

Five workflow improvements surfaced from helloskyy-io/Skyy-Command PR #68 + PR #69 reflections (originally captured 2026-05-04, evaluated in architecture session 2026-05-12). Routing was correct per claude-dot-files-governance — project-side PMs surfaced rather than auto-edited.

**SHIPPED:**

- **(a) .gitignore-collision check before checkpoint commit** (commit TBD this cycle)
  - Evidence: skyy-command PR #68 — engineer created `lib/temporal/activities/ssh/`, `tests/unit/ssh/`, `tests/integration/ssh/`; a broad `ssh/` rule in the repo's .gitignore (intended for credential dirs) silently hid ALL three new source paths. `git status` showed nothing untracked. Caught only at checkpoint-commit time when no file create-modes appeared in the diff.
  - Asymmetric-risk justification: silent data loss class (work invisible to PR) per engineering-quality.md ship-on-first-occurrence exception.
  - Implementation: 4-line prompt addition before checkpoint commit in revision-major.sh, build-phase.sh, plan-revision.sh, plan-new.sh. Rule: "if this stage created new files or directories, run `git status` and confirm each appears as untracked; if not, grep `.gitignore` for unanchored name patterns hiding them and add `!path/` allowlist." Skipped revision.sh (minor fixes rarely create files) and sprint-review.sh (test creation is more constrained and (d) addresses the bigger concern there).
  - Diverged from proposal: PM proposed Stage 0 pre-flight scan against planned paths. Rejected — Stage 0 doesn't know planned paths (they emerge in Stage 2/3). Simpler Stage 3 verification rule catches the same failure mode at lower complexity.

- **(d) sprint-review.sh: validate specialist test-failure claims against canonical runner** (commit TBD this cycle)
  - Evidence: skyy-command PR #69 — sprint-review reported "14 backend integration tests fail under suite runner due to conftest sys.path poisoning." Operator scrutiny couldn't reproduce: canonical `./testing/run-all.sh integration` from the PR worktree showed 51 passed / 0 failed.
  - Asymmetric-risk justification: workflow correctness/trust in a production-shaped pattern (sprint-review reports drive ship/defer decisions). Per engineering-quality.md, correctness regressions in production-shaped patterns warrant ship-on-first-occurrence.
  - Implementation: added Stage 3 sub-section to sprint-review.sh — Stage 2 specialist claims MUST be validated against canonical runner output; non-reproducible claims get reclassified as "investigation needed" with specialist-claim + canonical-result + reproduction-conditions fields, NOT carried forward as confirmed failures.

**DEFERRED — watch-list:**

- **(b) Templated "Deferred" section in PR body with auto-aggregation of marker comments**
  - Evidence: skyy-command PR #68 — engineer wrote "tracked as a follow-up" into PR body free-form, no structured surface
  - Decision: defer (single occurrence, duplicates existing surface)
  - Reasoning: workflow scripts already produce a Decision Log + Post-Run Reflection PR comment (the `DECISION_LOG_AND_REFLECTION` block). `engineering-quality.md` "Finding disposition" already requires documented-deferral with a tracked location. The gap isn't "no place for deferrals" — it's "engineer didn't use the existing place." Adding another mechanism would duplicate the existing one.
  - **Watch-criteria:** if 3+ PRs across multiple workflows show deferrals scattered in prose rather than the decision log, the existing tool has a usability gap and we ship structured aggregation.

- **(e) sprint-review.sh: file-state snapshot at report-write time**
  - Evidence: skyy-command PR #69 — report cited helper line counts of 1,417/1,551/1,543 when actuals at report-read time were 1,626/1,550/1,743. The finding's spec (all crossed 1,400-line threshold) was correct; only precise numbers were stale.
  - Decision: defer (single occurrence, not asymmetric risk)
  - Reasoning: report-quality-of-life issue, not a correctness regression. The underlying finding was correct; only audit precision was reduced. Doesn't meet engineering-quality bar for single-occurrence ship.
  - **Watch-criteria:** if a sprint-review report has stale numbers that materially mislead the operator (wrong-direction, not just imprecise — e.g., "234 lines" when actual is 1,400+), ship the Stage 5 snapshot helper.

**REJECTED as project-side (surface to project sessions):**

- **(c) Workflow doc note: STAGE 4 should use master runner, not flat pytest**
  - Evidence: skyy-command PR #68 — engineer used `pytest tests/` instead of `./testing/run-all.sh`
  - Decision: not actionable in claude-dot-files (existing instruction covers it)
  - Reasoning: revision-major.sh Stage 4 already says "Run tests relevant to the changes, following the project's testing standard." If the engineer didn't follow the project's testing standard, the fix is project-side — make sure `docs/standards/testing.md` explicitly names the master runner as the binding invocation. Adding workflow-level reinforcement would duplicate the existing standards-discovery instruction.
  - **Surfacing for skyy-command session:** verify the testing standard names `./testing/run-all.sh` as the binding test-runner invocation.

### Architecture-session item surfaced ad-hoc (2026-05-09)

- **No `--base-branch` flag in workflow scripts** (NEW, claude-dot-files-level)
  - Evidence: User's mdc-master-planning PM session needed to dispatch revision-major.sh against `feature/standards-cleanup` (not main). Workflow scripts have no `--base-branch` flag — operator must (a) checkout the feature branch before running, AND (b) inject explicit `gh pr create --base feature/standards-cleanup` instruction into the prompt or the engineer's PR will target main.
  - Decision: defer per engineering-quality rule (single occurrence)
  - Reasoning: defensive-prompt workaround works for this dispatch. Adding the flag to all 5 task-execution workflows (revision, revision-major, build-phase, plan-new, plan-revision) is real script work; defer until recurrence justifies the build cost.
  - **Watch-criteria:** if a second feature-branch dispatch comes up in any repo, ship `--base-branch <name>` to the workflow scripts. Implementation must do BOTH: (a) checkout the base branch before worktree creation, (b) auto-inject `gh pr create --base <name>` into the engineer's prompt.

---

## Review-runs cycle 2026-07-24 — four-repo sweep (92 runs, 3-week window)

Sources: `review-skyy-command-2026-07-24.md` (61 runs), `review-mdc-master-planning-2026-07-24.md` (25), `review-mdc-ansible-collections-2026-07-24.md` (5), `review-desired-state-sturdy-wheat-pelican-2026-07-24.md` (1 — log actually records an mdc-ansible-collections run; see S5). Aggregate: ~$1,791 spend, 93–100% success rates, zero new failure classes. System assessed as mature — remaining items are fine-tuning.

**SHIPPED:**

- **S1 — CWD guidance v2 (Pattern D amendment): absolute-path `cd`** (this commit). The 2026-05-29 v1 fix (`5dfebf9`) corrected the wrong factual premise but its example (`cd lib/temporal && pytest`) still taught RELATIVE cd-chaining — which fails under persistent CWD exactly as observed: 36 events / 30 of 61 skyy-command runs + 1 mdc-ansible-collections run, all post-v1. **Calibration lesson: v1 fixed the premise layer but shipped an example that still encoded the old premise — the example is the operative layer of a prompt rule, not the prose.** v2 rewrites the rule: never blind-chain relative `cd`; cd via absolute worktree-rooted path (idempotent) or skip cd. All 6 task-execution scripts.
- **S2 — re-Read-before-re-Edit rule** (this commit). 20 of 47 skyy-command Read-before-Edit events target the engineer's own `/tmp/claude-pr-*.md` staging files (Write → later Edit without fresh Read); mdc-master-planning regressed to 11 events / 7 runs (Pattern B), consistent with the same late-re-Edit shape after review-finding passes. One bullet beside the CWD rule in all 6 scripts.
- **S3 — review-agent navigation hints** (this commit). ~110 subagent errors in the skyy-command window (33 EISDIR directory-Reads + 78 path probes), corroborated in both first-review repos. Two rules added to code-reviewer, refactoring-evaluator, standards-auditor, quality-control: Glob-not-Read for directories; verify paths with Glob before Reading (docs/task-brief paths may lag the tree).

**CLOSED / RE-DISPOSED:**

- **Pattern A (25K-token Read overflow) → RESOLVED-EXTINCT.** 0 events across all 92 runs after appearing in every prior cycle (12× larger sample than any prior window). Credited to known-large-file `limit:200` dispatch guidance + harness Read defaults. Entry closed.
- **L1 (ScheduleWakeup in non-loop workflows) → REJECTED (original framing).** Usage is legitimate-by-design under the background-agent harness (fallback heartbeat while awaiting review agents; reasons in logs confirm). Narrow residual watch: short-poll (<600s) shape only — which self-extinguished 2026-07-10 in skyy-command.
- **Pattern C (`find | xargs` whitespace) → RE-DEFERRED with tightened criteria.** 11 benign usages this window (9 skyy + 2 mdc), zero data loss in 92 runs; prior criteria wording ambiguity (occurrence vs loss) resolved. New criteria: ship on first actual data loss OR first usage against whitespace-containing paths.
- **Pattern B (Read-before-Edit) → recurrence logged.** Rate still falling in skyy-command (0.77/run), regressed in mdc-master-planning (11 events / 7 runs after two clean cycles). S2 targets the dominant late-re-Edit shape; re-evaluate next cycle before any further hardening.
- **Sequential review-agent dispatch (deferred 2026-05-09) → see S4 pending.** Watch-criteria met AND diagnostic complete (prompts identical, model-side variability confirmed in mdc) — but harness background-dispatch default changed the cost premise (skyy: concurrent execution in 54/54 runs despite serial messages; mdc M3: no measured cost/wall-clock penalty for serial). Disposition pending S4 decision below.

**S4/S5 — decided via /decide + /best-practices cascade (operator-directed), SHIPPED same cycle:**

- **S4 → instruction reframe SHIPPED (dissolved, not forced).** The "SINGLE assistant message containing N Agent tool calls" mandate encoded a harness MECHANISM, not the intent — a vestige of the pre-background-agent harness where serial messages meant serial execution. Evidence killed the cost premise: skyy-command got full concurrency from serial messages (54/54 background-dispatch runs), and mdc measured NO cost/wall-clock penalty for serial ($16.2/28.2min serial vs $22.6/27.7min background — wake/idle overhead consumes the theoretical gain). Replaced in all 4 multi-agent scripts (revision-major, build-phase, plan-revision, sprint-review) with the intent contract: all narrow-lens agents dispatched before processing any results; QC only after ALL return; message shape explicitly declared irrelevant; long fallback wakeup (1200s+) while waiting. **The 2026-05-09 "sequential review-agent dispatch" deferral is CLOSED: RESOLVED-BY-HARNESS.** The prescribed worked-example ship was correctly NOT executed — it would have optimized a penalty that measurement shows no longer exists. Calibration lesson: encode intent contracts, not harness mechanics — mechanics are an unstable dependency.
- **S5 → `--repo` flag + fail-fast target-verify SHIPPED, scoped to revision-major.sh.** "Target = invocation directory" was identity-by-derivation — the exact anti-pattern the operator's own Temporal Standard §7.5 names as binding ("identities are explicit, never derived"). Evidence: 5/5 cross-repo dispatches failed this window (4 mdc runs self-rescued into engineer-created worktrees; 1 pelican dispatch landed in the entirely wrong repo AND corrupted this cycle's CPI attribution — the pelican review analyzed an mdc-ansible-collections run). Shipped: (a) `--repo <path>` flag — validated, cd-before-root-resolution, default stays cwd; (b) Stage 1 fail-fast instruction — on task/worktree repo mismatch, STOP and report DISPATCH MISCONFIGURATION rather than self-rescuing (self-rescue completed work 5/5 but corrupted telemetry and normalized wrong-worktree starts). Scoped to revision-major.sh only (the only workflow observed cross-repo — surgical-change discipline); siblings get the flag on observed need. NOT deferred for the Temporal port: the port is months out, failure rate is now, and the explicit-target design carries forward into the port's workflow input model (convergent, not throwaway). **`--base-branch` stays DEFERRED** (watch-criteria unfired) — amended: S5's flag plumbing makes it a ten-minute add when its second occurrence arrives.

**WATCH (new):**

- **Abnormal terminations without result events:** 4/61 skyy + 1/25 mdc (~6%). No causal story derivable from JSONLs alone; 2 of 4 skyy cases died immediately after launching background Bash (N=2, suggestive only). If ≥5% again next cycle, correlate with harness/session logs.

---

## Model management — centralized per-workflow model map (SHIPPED 2026-07-26)

**Trigger:** operator's PM sessions on the VM (2× opus, 1× fable) were leaking their model into dispatched workflows — headless runs inherited the dispatching session's model, producing mixed results with no control. Model identity was an ambient default, not an explicit input (§7.5-class violation: identity derived from convenience source). Fable's arrival (a 4th tier at 2× opus burn) made tier assignment a real policy question.

**Design (via /decide + /best-practices, fully operator-scrutinized):**

- **`config.yaml models:` map** — single authority, per-WORKFLOW keys (operator preference over role abstraction: more granular, more meaningful at N=7). Resolved at dispatch time in `run-claude.sh`; every dispatch now carries explicit `--model`; FAIL LOUD on missing key — never dispatch on an inherited default. `MODEL_OVERRIDE=<model>` env var = per-dispatch A/B override.
- **Alias-default, pin-on-evidence.** Operator overturned the initial pin-everything recommendation, and the scrutiny agreed: logs already record the resolved model ID per run (init event), so alias generation-jumps remain CPI-attributable post-hoc — pinning added ceremony, not data integrity. Doctrine: aliases float (zero-maintenance capability upgrades); pin a row only on (a) critical-push stability or (b) the watch-criterion below.
- **Workflow map:** fable → plan-new, plan-revision · opus → revision-major, build-phase, sprint-review · sonnet → revision, review-runs.
- **Agent canon (4 bumps):** architect → **fable** + WebSearch/WebFetch (deepest synthesis, compounding cost-of-miss; web verify neutralizes cutoff gap) · security-auditor → **fable** + WebSearch/WebFetch (asymmetric-risk lens; third-party testing shows Fable finding auth vulns Opus 4.8 missed; CVE currency requires web) · quality-control → **opus**, standards-architect → **opus** (judgment-heavy integration lenses). Narrow lenses stay sonnet (proven in CPI: Critical catches on sonnet).
- **Web-tool grant principle:** web tools go to lenses whose ground truth lives OUTSIDE the repo (industry practice, CVE landscape). All other agents stay Read/Grep/Glob. Guardrails in both prompts: verification-not-research, web-content-untrusted, epistemics labeling (`[verified — source]` vs `[training knowledge]`).
- **settings.json:** stays clean (2026-07-24 revert ratified on re-examination); machine-local interactive defaults belong in unsynced `settings.local.json`; explicit workflow `--model` shrinks any future accidental pin's blast radius to interactive-only.

**Watch-criteria:**
- **Silent generation jump regression:** if an alias generation-jump causes a measured workflow regression, pin that row to a full model ID and validate future generations interactively before floating again.
- **Architect rubber-stamp signature:** if architect finding-counts drop notably on fable-authored plans vs its historical baseline (self-preference bias — author and critic same model), demote architect to opus.
- **Security-auditor fable value:** if 2–3 sprint-review cycles show classifier-reroute weirdness (inconsistent report depth) or no measurable finding-quality gain over sonnet, revisit.
- **Web-tool discipline:** if panel latency/burn balloons from agent web use, tighten the lookup budget in the agent prompts.

---

## Headless early-stop termination class — completion contract + foreground dispatch (SHIPPED 2026-07-26)

**Trigger:** PM3 burn-test of the new research.sh (run research-20260726-215339): exit 0, $3.12, nothing produced. The main loop background-dispatched 3 research-analysts, then ended the turn with a text-only "waiting on completion notifications" message. In a headless `claude -p` run, a text-only turn ENDS the run — the harness hit its 600s background ceiling and killed the analysts mid-fetch. No papers, no critic, no synthesis, no PR, exit 0.

**Second occurrence of the class** (skyy #217 B-dispatch died identically 2026-07-24) → ships now per watch-criteria discipline. **Root cause is our own:** the 2026-07-24 **S4** change ("Background dispatch is the standard mechanism… schedule a long fallback wakeup") relied on the model reliably emitting a keep-alive tool call. It doesn't. S4's 54/54 background runs survived by luck (the model happened to keep the turn alive); research.sh's run is proof the pattern is fragile. I propagated the same wording into both new research scripts — this fix corrects S4 on PM3's new headless-specific evidence.

**Fix (three parts, value-ordered per PM3):**
1. **Completion contract (generic backstop) in `run-claude.sh`:** optional `COMPLETION_PATTERN` (ERE the final result must contain). Missing → `run_claude` fails LOUD + returns nonzero. Set to a PR-URL pattern in all 8 PR-producing workflows. **Exit 0 now means done.** (review-runs.sh excluded — produces a report, not a PR.)
2. **`HEADLESS_EXECUTION_GUARD` prompt block (prevention) in `shared-prompts.sh`:** binding rule that a text-only turn ends the run; dispatch FOREGROUND (`run_in_background: false`) so the tool call blocks; never background-and-wait; never ScheduleWakeup-to-wait; run complete only when the completion signal prints. Injected into all 7 dispatching workflows (revision.sh excluded — single-loop, no dispatch; backstop only).
3. **Dispatch-wording swap:** the S4 "background is standard + fallback wakeup" sentence → "FOREGROUND agents in a single message run concurrently where the harness allows AND block the turn; sequential-but-completing beats concurrent-but-dead." Replaced in all 6 scripts carrying it (4 S4 + 2 research).

**Supersedes** the S4 background-dispatch guidance. Cost-neutral: S4's own M3 finding measured no penalty for serial dispatch, so losing background concurrency costs nothing; foreground-in-one-message keeps concurrency where the harness supports it.

**Verified:** bash -n clean (9 scripts + 3 lib); completion-contract logic 3/3 (PR-URL pass, waiting-message miss, generic-Complete miss); model-resolution 5/5 and due-gate 5/5 still green; zero stale background wording remains fleet-wide.

**Watch-criteria:**
- **False-positive completion misses:** if a legitimately-complete run fails the pattern (e.g. a workflow that completes without printing a PR URL), widen/relax that script's COMPLETION_PATTERN. review-runs.sh has no pattern by design — if it ever early-stops silently, give it a report-path token.
- **Residual early-stops despite the guard:** if a dispatching run still dies text-only after this (guard ignored), the next step is foreground-enforcement at the harness/prompt level or splitting dispatch into its own stage with a mandatory post-dispatch tool call.
- **S4 relitigating:** the sequential-review-dispatch deferral was closed RESOLVED-BY-HARNESS on background-agent concurrency; this fix moves back toward foreground. If a future CPI window shows review-stage wall-clock materially regressing, measure foreground-concurrent vs sequential explicitly (S4's M3 said no penalty — reconfirm at scale).

---

## pr-review disposition criteria — anti-rug-sweep hardening (SHIPPED 2026-07-27)

**Trigger:** operator-caught on pr-review's first meal (MDC-Master-Planning PR #136, workflow `1e09106`). The disposition engine — the tool whose ENTIRE job is to stop rug-sweeping — reasoned work away exactly as the producing run had: recommended MERGE while hiding work, deferred items to dead surfaces (the reviewed PR's own thread, locationless "the architecture session"), and pulled a "fix costs more than it's worth" dodge. Merging the PR would have buried the residuals in a session-local task list.

**Root cause (the important part): the value function was unstated.** A capable model with no stated objective optimizes cost — so it economized dispatches and rationalized issues away. The fix is to state the objective, not to patch each dodge. (PM3 handoff + operator rulings, 2026-07-27.)

**Fixes shipped (all in the pr-review.sh prompt — binding doctrine, not guidance):**
1. **Value function stated at the top** (operator's near-verbatim framing): "QC identifies issues; PR-review's purpose is to get every issue CORRECTED so the result is enterprise-ready code we're proud of. Minimizing effort, economizing dispatches, or rationalizing issues away is the opposite of your job." This is the root-cause fix; the rest are reinforcement.
2. **'Pre-existing / existing-condition' ABOLISHED** as an excuse AND removed from the category enum. No exceptions. A pre-existing issue is dispositioned like any other.
3. **'Out of scope' is an input, not a disposition** — still terminates FIXED/REJECTED/DEFERRED.
4. **Cost-of-dispatch forbidden as a rationale** — disproportionate-fix belief = HOLD(scope) for the operator to rule on; never a self-granted waiver. The economics are the operator's call.
5. **DEFERRED restricted to two cases (operator ruling 7):** work already scheduled in an existing sprint item, or already in motion in a live PR — pointer VERIFIED present (fetch-and-check like research-critic verifies a citation). Never creates a parking spot; pr-review can't write trackers, so a valid target must already exist. The reviewed PR is never a valid pointer (merging = burial).
6. **~~MERGE-AFTER-EXPORTS third verdict~~ → FOLDED TO BINARY (operator, same day).** Shipped briefly as a third verdict; operator confirmed the mental model is binary **MERGE | HOLD**, with HOLD as the catch-all runway ("do these next-steps → next pass is MERGE"). Each HOLD next-step is one of two shapes: **redispatch** (obvious fix, scoped `dispatch_context`) or **needs-assistance** (HiL — a `/decide`+`/best-practices`-reasoned recommendation for the operator, including the "can I have assistance?" case and, importantly, surfacing an architecture/planning gap bigger than the PR). Un-homed non-blocking follow-ups fold into HOLD next-steps rather than a separate export verdict. Also refined same-day: the self-report/comments are the PRIMARY hunting ground (not the already-reviewed diff — that's a secondary blind-spot/claim-verification check).

**Reconciliations made explicit (surfaced to operator + PM3):** (a) fix #1's tracker-allowlist vs ruling #7 resolved by decide-only — pr-review can't create a home, so a deferral target must already exist. (b) un-homed non-blocking work has nowhere to defer → it becomes a HOLD next-step (redispatch if its home is an obvious doc edit; needs-assistance if where it belongs is a judgment call).

**Watch-criteria:**
- **`laundered_deferrals_caught` per run** (new yaml field): deferrals the producing run pointed at a dead/invalid home that pr-review reclassified. Rising count = producing workflows learning to launder deferrals — a Layer-1 CPI signal that a producing-workflow prompt needs the same anti-launder tightening.
- **Re-test gate:** the workflow stays strictly HiL until this passes a re-test (operator directive). Meal #2 (a real build PR) is gated on this fix landing. First re-test is the re-audit of PR #136.
- **Over-correction watch:** if pr-review starts HOLDing genuinely-fine PRs (false rug-sweep positives) or rejecting valid deferrals-to-real-sprint-items, the deferred bar may be too tight — recalibrate the two-case rule.

---

## pr-review fine-tune round 2 — meal-2 CPI data + six tunes (SHIPPED 2026-07-27)

**Meal-2 (Skyy-Command #223, first build-PR under the doctrine version) confirmed the doctrine fix class:** cost-dodges 2→0; laundered-deferrals produced 1 (meal 1) → **caught 1 unprompted** (meal 2 — the engine self-caught the exact class the operator caught by hand in meal 1). Rejections upheld on re-adjudication (checked the cited contract test at its line, not the run's word) + one fresh-eyes rejection of its own. Verification exceeded spec (ran the full 4565-test collection + component suites to confirm FIXED claims — keep this). Fable earning its tier (genuine /decide dissolution on a placement rec; explicit evidence bar on a conftest rec). Economics $4.17 / 27 turns / 6 min. Pass 2: **HOLD again correctly** — re-verified pass-1's own claims and caught a **pass-1 false-positive finding** ("missing lib/ceph/" — the line existed; both pass-1 and the PM string-matched \`lib/ceph\` against a line reading \`ceph/\`). Cross-pass self-correction WORKS — keep the spot-check-prior-passes behavior.

**Two measured datapoints:** (1) first false-positive finding rate = 1/25 (FIXED/REJECTED verifications all held; the miss was an absence-claim string-match trap); (2) cross-pass self-correction is load-bearing.

**Six tunes shipped (all prompt-level, no autonomy/verdict-machinery changes — operator scope vote "tune, don't overhaul"):**
1. **Visible lens transcripts** — needs-assistance recs now print a one-line `reframe:` (/decide) + `bp:` (/best-practices) before the recommendation (yaml + human runway), so judgment is auditable at standup speed. [pr-review]
2. **`research-defect` HOLD tag** with the Research-Standard §5 materiality test (does correcting the defect change the decision outcome? NO → rides revalidation sweep; YES → HOLD/research-defect, research-currency re-run + dependent planning re-run). [pr-review]
3. **Evidence-integrity fail-fast at the PLANNING gate** — if inputs include research artifacts, verify integrity (critic verdicts present, papers in-window, load-bearing claims non-contradictory) before consuming; structurally faulty → STOP + report blocking finding. **CORRECTED same day (tune-3 revert, Research §7):** originally shipped to plan-revision + build-phase; the build-phase half was a layering defect — research is consumed at PLANNING only, builds consume plans (which carry citations) + standards, never research directly. A build STOPping because a paper's window lapsed *after its plan merged* is a false-STOP on valid work. Removed from build-phase (replaced with a §7 breadcrumb + a reflection-only research-state note — the only research touchpoint a build has); the check now lives in plan-revision AND plan-new (both are consumption gates). **Also added same day:** a distinct **research-SUFFICIENCY** fail-fast in plan-new + plan-revision Stage-1 — if the component warrants research (§2 rubric) and none exists and no waiver directive → STOP pre-spend (~$2) with a two-option report (run research first / re-dispatch with a waiver directive that writes the §2 waiver line into the phase doc), preventing a ~$40 plan built decide-then-justify. [plan-revision, plan-new; build-phase carries no research check]
4. **DLR trim from pr-review** — decide-only engine no longer carries the "after pushing, create the PR / Decision Log" tails; replaced with a lean Post-Run Reflection (the disposition table IS the decision record). [pr-review]
5. **Propagation check + pointer self-check** — plan-revision Stage-4 reviewers verify every corrected fact reached ALL dependents (evidence-reconciliation tasks); the shared Deferred-Work block gains a pointer-accuracy self-check (producing runs verify their own deferral pointers resolve before writing them). [plan-revision, shared-prompts]
6. **Machine-checkable precheck in redispatch dispatch_context** — a redispatch fix carries a concrete precondition command (a DIFFERENT check than the one that surfaced the finding) the executor must pass before applying, so a flawed finding fails loud instead of inducing a defect. Motivated by the pass-1 false-positive → PM faithful-execution → duplicate-on-main chain. [pr-review]
   - **Plus (architect addition, operator-flagged for veto): absence-claim rigor** in pr-review — "missing/absent" claims confirmed with an exact match + a second different check, since absence is the highest-risk false-positive class (the reviewer-side complement to tune 6's executor-side fix).

**Watch next:** false-HOLD rate (holds a human would have merged — no data yet); whether the precheck/absence-rigor pair drives the 1/25 false-positive rate down; whether visible reframe/bp lines stay compact or bloat the comment.

---

## Prompt-construction landmine — unescaped backticks in double-quoted PROMPTs (FIXED 2026-07-27, fleet-blocking)

**Trigger:** live dispatch (secrets research cycle) died at exit 127 before Stage 1 — `research.sh: line 230: run_in_background:: command not found`. Class: an UNESCAPED backtick inside a double-quoted `PROMPT="..."` triggers command substitution at runtime — bash executes the backtick's contents as a command during the assignment. `bash -n` passes it (syntactically valid); it only fails when the line executes, which no syntax check reaches. This is the "never ran at all" class — distinct from the completion contract's "ran but produced nothing."

**Diagnosis (empirical, corrected PM3's inferred blast radius):** PM3 confirmed research.sh live and inferred 5 others broken by the same text. Reproduced both quoting shapes: a backtick in a single-quoted heredoc (`<<'EOF'`) is literal and SAFE even when interpolated via `${VAR}` (bash does not re-scan expansion results); a backtick written directly in a double-quoted string command-substitutes. Audit of every occurrence: the 4 S4 scripts (revision-major, plan-revision, build-phase, sprint-review) carry the dispatch line INSIDE their single-quoted STAGES heredocs → SAFE. pr-review has 57 backticks in its inline double-quoted PROMPT but ALL escaped (`\``) → SAFE (why meals #1/#2 ran). **The actual bug was exactly 2 bare backticks each in research.sh + research-refresh.sh** — the `run_in_background: false` pair added in the headless fix without escaping, while every other backtick in those files was escaped. Real blast radius: 2 files, not 6.

**Fix:** escaped the 2 bare backticks in each research script. Verified: 0 bare backticks remain; the escaped form preserves the literal text and does not substitute.

**Ship-gate (the durable fix — PM3 point 3):** `scripts/helpers/lint-prompts.sh` — strips single-quoted heredoc bodies and comment lines, flags any surviving unescaped backtick in the command-substitutable regions. Zero runtime deps (no gh/PR/auth/side-effects, unlike a runtime smoke test), catches the exact class `bash -n` misses. Proven: reports the fixed fleet clean, and catches the bug the instant it's reintroduced. **Run it before committing any workflow prompt change.**

**Calibration lesson:** the ship gate (`bash -n` + functional tests) had a blind spot for prompt-construction failures — a same-day shipment took down 2 workflows and `bash -n` waved it through. The lint closes that specific gap. A fuller runtime build-test (catching all prompt-construction failures, not just backticks) remains a possible future addition, with the tradeoff that it needs per-workflow fixtures + git/gh/claude and can't cover the --pr-only pr-review without a live PR.

**Watch:** the lint's comment-skip (`^\s*#`) means a bare backtick on a markdown-header line inside a prompt would be missed — narrow, since headers rarely carry inline code. If a prompt-construction failure ever slips past the lint, escalate to the runtime build-test.

---

## How to read this log

**For run #2 prep:** scan DEFERRED sections. Items with `Watch-criteria` met by run #2 evidence become Tier 1 ship candidates. Items still deferred get re-deferred with updated counts.

**For workflow archeology:** SHIPPED items have commit references — `git show <sha>` shows what actually changed.

**For diminishing-returns assessment:** ratio of deferred-then-resurfaced vs deferred-and-never-recurred is the real signal of CPI maturity. High recurrence rate → we're undercalibrating (shipping too few). High never-recurred rate → we're correctly calibrating (deferring noise from one-offs).
