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

## Economics retier — all Fable removed from the fleet (SHIPPED 2026-07-27)

**Trigger:** Max(20x) weekly bars at Monday midday — session 32%, all-models 34%, Fable 39%, with the week 20.8% elapsed. Burn at **1.63× sustainable** (Fable 1.87×); projected exhaustion Wednesday evening (Fable) / Thursday morning (all-models), during the operator's last week of school.

**Diagnosis (measured, not assumed):**
- **Fable draws from the same weekly pool** — confirmed in Anthropic's help center: *"Fable 5 draws from your plan's regular weekly usage limits… you can never use more than your weekly limit."* The 50% Fable cap is a ceiling INSIDE the allowance, not extra capacity.
- **Arithmetic decomposition:** Fable bar (39%) > all-models bar (34%) is impossible on a shared denominator → the Fable bar measures against its own ceiling (50% of weekly). So Fable = 39% × 50% = **19.5% of the weekly pool**; everything else = 14.5%. **Fable was ~57% of total burn** from ~10 placements.
- **Why the weekly bar suddenly binds:** Anthropic **permanently doubled the 5-hour cap (2026-05-06)**. That cap used to act as a de-facto rate limiter that incidentally protected the weekly budget; with it doubled, nothing throttles mid-day work and it all flows into the weekly. (Hypothesis that the weekly limit had *shrunk* was checked and DISPROVED — the +50% Claude Code weekly boost is still active, extended through **2026-08-19**.)
- **Opus 5 also burns more than 4.8 at identical price** — thinking-by-default bills at output rate (~10–20% more tokens/request reported; one practitioner comparison measured ~2× on real tasks). A fleet-wide increase independent of our assignments.
- Compounding: two entirely new workflow families (research, pr-review) under active parallel testing = genuinely more work, not just costlier work.

**Shipped (operator-directed): ZERO Fable placements fleet-wide.**
- Workflows: `plan-new`, `plan-revision`, `pr-review` fable → **opus**. No workflow is on fable.
- Agents: `architect` fable → **opus** (keeps +web — its only path to current industry ground truth); `security-auditor` fable → **opus** (keeps +web — CVE currency is impossible from training data); `research-analyst` fable → **opus** (keeps +web — it IS the source-gathering agent, §3 requires 10–20 cited sources; web is not optional); `quality-control` opus → **sonnet**; `standards-architect` opus → **sonnet**.
- **quality-control → sonnet rationale (architect recommendation, operator-confirmed):** it ran on sonnet from creation until the unvalidated 2026-07-25 bump; documented positive evidence exists AT sonnet (2026-05-29 post-fix dispatch: correct hedging, no fabrication, caught the SYS_TIME↔Raft systemic link). The fabrication incident was a methodology defect fixed by methodology, not a capability ceiling. Crucially, **pr-review now exists** — an independent opus-tier fresh-eyes pass that verifies claims against code — so a QC miss is no longer terminal. QC is also among the highest-frequency agents (every multi-agent workflow), making its tier a fleet-wide multiplier.

**Projected effect:** Fable portion ~19.5% → ~9.8% (opus is half price), plus QC/standards-architect opus→sonnet savings. Total burn ~34% → ~24%, i.e. **1.63× → ~1.1× sustainable**. Helps substantially; may still be tight *this* week since 34% is already spent.

**Watch-criteria:**
- **PM interactive sessions are NOT governed by config.yaml.** An all-day PM session on Fable with growing context is plausibly the largest single Fable consumer. If the Fable bar keeps climbing after this retier, the remaining source is interactive sessions, not workflows.
- **2026-08-19 cliff:** the +50% Claude Code weekly boost expires → allowance −33%. Burn must be sustainable at 1.0× *before* then, or the same usage exhausts around Tuesday.
- **Quality watch on the downgrades:** if pr-review starts catching integration-class issues QC should have caught, QC returns to opus (with evidence this time). If architect/security-auditor quality drops without fable, note it — but neither had validation data at fable, so this is a return to a proven baseline, not a degradation.
- **Fable re-entry:** only with headroom + measured per-run cost. `pr-review` is the first candidate back — it was the cheapest fable placement at **$4.17/run measured** and had the only positive fable evidence (meal-2 disposition quality).
- **Untested lever:** `CLAUDE_EFFORT` / settings `effortLevel` (low/medium/high/xhigh). Since Opus 5's increase is specifically thinking-by-default, lower effort on mechanical workflows could cut burn without a tier drop. Not verified in headless `claude -p` — worth a measured experiment if more headroom is needed.

---

## Tooling cycle 3 — comprehensive instrument fixes (SHIPPED 2026-07-27)

**Source:** PM3 consolidated feedback across 3 runs / 2 PMs / 2 tools (pr-review meal #3 on a research PR, the research.sh run that produced it, PM2's independent revision→pr-review→redispatch→pass-2 cycle on skyy-command #224). Operator directive: **isolate and fix the instruments before acting on their measurements** — all content findings deliberately parked. PM3 named the **depth-2 problem**: research.sh → pr-review.sh → revision.sh were introduced back-to-back without isolation, so defects in the researcher surface via the reviewer and both must be fixed in one cycle.

**P2.1 — `--pr` completion-contract false-negative (highest severity, WORSE than reported).** PM2 saw revision.sh exit 1 with the full early-stop banner after a perfect run (3 fixes, 174/174 bats, 158/158 py, pushed, comment posted). Cause: `COMPLETION_PATTERN` matches a PR URL, emitted only on PR *creation*; the `--pr` path *updates* an existing PR and emits nothing. **Audit found ZERO of the six `--pr` paths instructed printing the URL — the contract was unsatisfiable on every redispatch fleet-wide**, which is exactly the path pr-review's fix loop uses. A parent/Temporal layer reading exit codes would classify successful fixes as failed and retry them (re-applying applied fixes). Fixed: all six `--pr` paths now print the PR URL as their final line via `gh pr view <N> --json url --jq .url`.

**P1.1 — disposition enum could not express HOLD (data integrity).** Meal #3 had 10 HOLD items; the schema admitted only `fixed|rejected|deferred`, so the engine emitted all ten as `disposition: fixed` plus an invented `note_disposition_override` field. **A machine consumer reading the documented schema saw ten resolved findings.** Fixed: `hold` added to the enum with required `hold_kind: redispatch|needs-assistance`, plus a new **schema-integrity invariant — never invent a field; an inexpressible state is a SCHEMA BUG to report, not a field to fabricate.**

**P1.2 — laundered ≠ homeless (mis-attribution).** Meal #3 counted a research PR's 9 action candidates as laundered deferrals. The engine was right they had no home, but the cause was that *the corpus has no surface for "research action candidate awaiting ratification"* — a standards gap, not a producing-run failure. Fixed: taxonomy split — **laundered** (pointer exists, resolves dead → producing-run failure, counts against it) vs **homeless** (legitimate item, no valid surface exists → standards gap, escalates as needs-assistance with new `why_human: missing-surface`, never counted against the run). Both still block MERGE.

**P1.3 — predecessor PR's Deferred Work (engine's own unprompted discovery).** The engine reported this was *"the single highest-yield step of this review, and the prompt does not call for it."* Its generalization is now the rule: **a deferral whose stated trigger condition THIS PR satisfies is a first-class finding.** Added to Stage-1 gather.

**P1.4 — laundered as a RATE, not a count.** Reported as `2` when both of that PR's deferrals were laundered — 100%. Now `laundered_deferrals: {caught, of_total}` + `homeless_items`.

**P1.5 — precheck context + STOP-predicate split.** A pass-1 precheck run from `main` returned a false "already done — STOP" (the second adopter lived in the unmerged PR). Fixed with three requirements: state the branch/worktree context, use a different check than the one that surfaced the finding (retained — it is why this was caught), and **split the STOP predicate** ('not yet warranted' vs 'already done' are different states; only the latter justifies STOP).

**P1.6 — protect-list codified as named INVARIANTS** so future token-trimming cannot quietly remove them: absence-is-non-terminal (a silently dropped item is the subtlest burial), cross-pass re-laundering detection, verify-fixes-not-just-prescribe (pass 2 caught a regression introduced by its own pass-1 prescription — the property that makes an autonomous parent loop safe), refusal to self-grant on HiL surfaces while still returning reframe/bp/recommendation, and pointer-verification-by-fetch.

**P2.2 — research.sh Stage 4 had no round budget.** One paper needed 3 correction rounds with no stated budget and no non-convergence path. Fixed: **MAX 3 rounds**, then DROP the paper from the cycle (excluded from synthesis, left in `raw/` with a `STATUS: NOT VERIFIED` header, reported as non-convergent). An honestly-excluded paper is a finding; a silently-included one is contamination.

**P2.3 — raw sources over rendered pages (highest-value methodology finding).** Measured across the cycle: **rendered-page fetches produced invented paraphrases twice; raw-source fetches (`raw.githubusercontent`, plain-text, spec JSON) were reliable every time.** Added to research-analyst, research-currency, and research-critic (the critic verifies against the same surfaces). Cheapest available reduction in critic workload.

**P2.4 — `Critic:` line in the paper header.** §4 required the synthesis to cite verdicts, but a paper read alone carried no evidence it was verified. Added to the analyst's header contract; research.sh Stage 4 and research-currency write/refresh it.

**Ship-gate note (the gates are complementary, and both fired):** implementing P1.5 introduced unescaped `"` inside the double-quoted PROMPT — `bash -n` caught it (unbalanced quotes = syntax error). The backtick class is syntactically *valid*, which is why `lint-prompts.sh` exists. **`bash -n` catches quote imbalance; the lint catches backticks. Neither alone is sufficient; run both.**

**Value evidence preserved (so nothing gets tuned away later):** meal #3 caught that a workflow's rotation ordering was **already live in `main`**, not "being built" as the producing run wrote — converting a proposal into a live-exposure finding — plus 7 broken relative links via two independent verification methods. PM2's cycle surfaced a real correctness defect (exit-code propagation) **that had already survived engineer self-review, four review agents, and PM2's own manual verification** — more review agents demonstrably do not catch that class. The research critic gate: every paper needed a correction round, and **three of five defects were in the paper's own highest-stakes claim** (a fabricated ESO condition string, a k3s version floor wrong by three patch numbers, a non-verbatim quote destined for a standards amendment) — without the gate, three papers would have fed false facts into binding rules.

**Watch:** whether the `--pr` URL instruction is reliably followed (if a redispatch still exits 1 after this, the instruction isn't landing and the pattern needs a per-path variant); whether `hold` dispositions now populate correctly instead of `fixed`+override; whether the laundered/homeless split changes the ratio meaningfully once PM3's missing-surface work lands.

---

## Prompt-escaping outage #2 + the gate that certified it clean (FIXED 2026-07-27)

**Trigger:** `pr-review.sh` dead at exit 127 (`until: command not found`) — the cycle-3 P1.3 text I shipped hours earlier contained **two unescaped `"` pairs whose content had whitespace** (line 208 `"deferred until a second adopter exists"`, line 330 `"VERIFIED DEAD — PR merged, nothing filed"`). PM3's addendum caught the second site; fixing only the first would have left it broken.

**Same CLASS as the morning's backtick outage ("prompt strings are code"), different VECTOR — and `lint-prompts.sh`, built that morning for the first vector, reported the tree CLEAN while the file could not launch.** PM3's framing is the durable lesson: **a gate that passes a broken file is worse than no gate**, because it converts "I should test this" into "the gate says it's fine."

**Why `bash -n` was blind (both times, differently):** with an EVEN number of stray quotes they **balance** — the file is *valid bash that means something else*: `PROMPT=<truncated>` becomes an assignment prefix and the following prose becomes a command. (My earlier P1.5 quote bug was caught by `bash -n` only because *its* quotes happened to be unbalanced — luck, not coverage.)

**The mechanics, precisely (PM3's analysis, confirmed):** a stray `"` pair is only fatal when its content contains **whitespace**. `"waiting"` (no spaces) closes and reopens the string and bash concatenates the bare word seamlessly — harmless, which is why `research.sh`'s `text-only "waiting" turn` never broke. `"deferred until a second adopter exists"` splits the assignment into multiple words → the remainder parses as a command.

**Fix shipped:**
1. Both quote sites converted to single quotes.
2. **`lint-prompts.sh` rebuilt as an EXECUTION check, not a pattern check.** It extracts every prompt-assignment block (inline `PROMPT="…"` and unquoted-heredoc `PROMPT=$(cat <<EOF`) and *constructs* it in a sandbox — `env -i` with a PATH containing **only `cat`** — failing if bash does anything other than assign a string. Nothing from the real system can execute.
3. **Binding authoring rule** added to `docs/standards/workflow-scripts.md`: single quotes for example phrases, escaped backticks for code refs, never `$( )` in prose; both gates required before committing a prompt edit.

**One correction to the proposed fix:** PM3 suggested extracting the block and running `bash -n` on it. That would NOT have caught this — the extracted block *parses fine*; it is valid syntax with different meaning. The check must **execute** the assignment, not parse it. Shipped accordingly.

**Validation (all three, on a clean tree that passes):** reintroduced the backtick vector → CAUGHT; reintroduced the quote vector → CAUGHT (the one the old gate missed); injected a `$( )` vector **never enumerated anywhere in its rules** → CAUGHT. The execution check generalizes to vectors nobody has met yet, which was the whole point.

**Self-inflicted bug found during the fix (worth recording):** my first extractor used `^[[:space:]]*\(` as a block terminator, which matched the *prose* line `(1) STATE THE CONTEXT…` and silently truncated the block — the lint then failed for the wrong reason on a healthy file. Terminators narrowed to `echo` / `run_claude` / a lone `)`. Lesson: a linter's own heuristics are code too, and "fails for the wrong reason" is as bad as "passes when broken."

**Recurrence note:** two escaping outages in ~10 hours, both from prompt-text edits, both invisible to `bash -n`, the second invisible to the gate built for the first. The durable answer was to stop enumerating vectors and start executing.

**Watch:** whether the execution check produces false positives on future prompt shapes (a legitimate `$( )` in a prompt would flag — none exist today); whether the narrow terminator list needs extending as new script shapes appear.

---

## Cycle 4 — FINDING QUALITY: we built the noun and forgot the verb (SHIPPED 2026-07-27)

**Trigger:** operator review of pr-review pass 2 on mdc-master-planning #137. On one runway item, verbatim: *"literally NOTHING you just said gives me an issue to rule on… I have to have an issue, not something random that may or may not even exist."* The item: *"PR body says LARGE (5 topics); §2's rubric puts 5 in MEDIUM. Recommendation: relabel MEDIUM."* That is a **discrepancy, not an issue** — nothing is at stake either way. The same underlying fact, correctly framed: *"three key areas of the secrets substrate have NO research coverage — remedy: extend the research pool by 3 mini-papers."* Consequence + remedy, rulable in ten seconds.

**ROOT CAUSE (PM3, and it generalizes): we specced a DISPOSITION taxonomy and never specced a REMEDY taxonomy.** Everything the schema knew was state or routing (`disposition`, `hold_kind`, `why_human`); the recommendation itself was freeform prose. So facing "5 topics vs a rubric," the only remedies in the engine's working vocabulary were *fix the artifact* or *ask the human* — **"go get more evidence" was not a thing it knew it was permitted to recommend, because we never gave it that word.** An unbounded action field then collapses to the cheapest action that makes the discrepancy disappear: relabel it. Not model laziness — a missing verb.

**Shipped in pr-review.sh:**
1. **`remedy:` controlled vocabulary (required per finding, extend-never-rename):** `fix-in-place` | `reject` | `defer-to-existing-work` | **`extend-upstream-artifact`** (the missing one — the upstream input is incomplete, more research/planning needed) | `create-missing-surface` | `ratify-standard-change` | `operator-action`. Forcing a selection is what makes the engine *reach* for "extend the research" instead of settling for "relabel."
2. **Consequence gate:** every candidate must state what breaks / is risked / gets decided wrongly. If it can't, it is a reflection NOTE, not a finding — notes don't enter a runway that costs an operator ruling per entry. Titles name the consequence, never the mismatch. Added `title:` and required `consequence:` to the schema.
3. **Readability self-check** (Stage 5, pre-post): *reading only the title and remedy, would the operator know what to do?*
4. **NO BUNDLING (binding, operator directive):** pass 2 delivered **17 decisions inside 6 entries** — one entry was nine separate ratifications, another four separate amendments sharing a single `reframe:`/`bp:` pair. Operator: *"there is literally no way the lenses were run on these items."* He's right — they were run on the BUNDLE, which is **lens theater**. One finding = one entry = one ruling; each carries its own reframe/bp/recommendation/remedy; every finding gets a recommendation including rejected and deferred ones; a bundle is a **defect, not a formatting choice**. Note the interaction with #1: bundling and freeform-remedy reinforce each other — no single verb covers nine items, so bundles *force* vague remedies.
5. **Current-tree check:** pass 2 prescribed four Research Standard amendments that had **already landed hours earlier** (`fad9a16`) because it read the artifact's state rather than the repo's. It already did this correctly for CODE (catching a workflow shipped in another PR) — the discipline existed but wasn't applied to DOCS. Now required for any remedy touching a standard/doc outside the PR.

**Generalized to the global rule (PM3 correctly reassigned this half — `config/rules/engineering-quality.md` is claude-dot-files-governed):** added **"Finding QUALITY — every finding states its consequence and its remedy"** as the sibling clause to the existing "Finding disposition" section. Disposition governs *whether an item is resolved*; quality governs *whether the human can act on it*. Both now live in the same section so no agent reads one without the other. Binds every finding-surfacing agent — code-reviewer, standards-auditor, quality-control, security-auditor, refactoring-evaluator, research-critic, architect, planner.

**CPI-of-CPI lesson (the durable one):** the original schema was designed to enforce DOCTRINE — `fixed|rejected|deferred` exists to prevent rug-sweeping, a *state* question — and every tuning round since refined the state machine while leaving the action space unbounded. **When a schema constrains outcomes, check whether it also constrains actions. An unbounded action field always collapses to the cheapest available action.**

**Watch-criteria:** sample runway entries for **remedy diversity** — if `fix-in-place` dominates 90%+, the vocabulary is being under-used and the consequence gate isn't biting. Also watch entry-count vs ruling-count (they should now be 1:1) and whether `extend-upstream-artifact` ever gets selected (if never, the missing verb is still missing in practice).

---

## Cycle 5 — combined PM2+PM3 production findings (SHIPPED 2026-07-28)

**Source:** PM2 round-2 (7-pass disposition on skyy-command #224) + PM3 (skyy-command #225, mdc-master-planning #138). Four findings reached **independently by both PMs from different evidence** — treated as two-occurrence patterns, i.e. ship candidates with confirmed evidence, not watch-items.

**The shared headline, both lanes: a green suite is not evidence.** Both cycles produced a live credential defect behind fully passing tests, found by REVIEW not by testing. PM2's: a failed `kubectl apply` reported as success (introduced by a *correct* decision, *competently* implemented, with *new tests written*, past engineer self-review + four review agents + PM2's own line-level verification; caught by a ~$3 redispatch). PM3's: three uncovered credential exits in a redaction seam whose entire purpose was to be the single covered exit — one *introduced* by deleting a per-adapter scrub.

**SHIPPED (10 of 12):**

1. **⊕ `--repo` on `revision.sh`** — safety. cwd DRIFTS as a side effect of running other workflows; both PMs observed it independently (one session left cwd in `claude-dot-files/scripts/workflows` — the repo project sessions are forbidden to edit — another inside a worktree after a background dispatch). `revision.sh` is the most-used, least-watched workflow, so a wrong-repo worktree there is likeliest to go unnoticed. It was also the only sibling without the flag while `pr-review.sh`'s own header states the principle: *"target repo, explicit identity, never derived."*
2. **Turn-cap mitigation (partial — see deferred)** — `revision.sh` gains a **workflow-fit check** (STOP and recommend `revision-major.sh` when the task needs the review arsenal; mis-sizing cost $9.74 stranded + $27.29 to redo) and **turn-budget discipline** (commit as soon as a unit is verified; never carry completed work uncommitted; on approaching the cap, stop-commit-push-report). Addresses the loss pragmatically; the full salvage/resume path is deferred below.
3. **⊕ Test-shape check + negative controls** — `revision-major.sh` + `build-phase.sh` Stage 4: (a) does the test invoke the code the way REAL callers do (a direct call vs the callers' `$( )` exercises a different execution context — errexit cleared in the subshell — so the test *cannot* observe the failure); (b) **verified negative control required for structural/contract tests** — prove the assertion fires when the property is violated. PM2's engine proved the gap by execution (stripped `>&2` from 3 of 4 call sites; suite still 21/21 green).
4. **PR self-description at workflow level** — `revision.sh` / `revision-major.sh` / `build-phase.sh` on `--pr` must update the PR body + `file_structure.txt`. **This kills a perpetual-motion machine:** fix → review flags self-description drift → fix creates fresh drift; measured 1–2 manufactured findings per round, with one pass finding ZERO code defects and only drift. PM2 folded it in by hand and pass 4 returned zero metadata findings. Precondition for #5's stopping rule to behave.
5. **⊕ Convergence rule + attempt counter** — `pr-review`: **the first pass whose findings are ALL preventive IS convergence → MERGE** (measured: open-count sat at 1 for three passes while severity fell live-bug → diagnostics → preventive-only; #224 had converged at pass 6 while the verdict still read HOLD). New `attempt:` field, **written not derived** (a capped run leaves no commit and no comment, so a git-derived count scores it zero; a run that dies at its cap does NOT consume an attempt), plus `converged:`.
6. **Per-commit reflection check** — the `no-reflection` HOLD now fires per-COMMIT: a PR where a trivial later run posted "no significant decisions" while the commit making every real choice posted nothing is an attestation gap, even though a reflection technically exists.
7. **Fixer sibling-matching + execution-context enumeration** — `revision.sh` / `revision-major.sh`: match local precedent wholesale (the file already contained TWO correct sibling implementations; the extraction adopted neither and each fix round closed exactly one half), and when code moves into a new execution context enumerate everything that context changes (command substitution clears errexit AND captures stdout — two defects, one root cause, found three passes apart).
8. **Characterize-the-difference** — a REJECTED disposition turning on a difference must characterize HOW they differ, not confirm THAT they do. (One hardcoded a key name, the other parameterized it — one implementation typed twice. Re-verified and re-affirmed across three passes without asking *how*.)
9. **Boundary lens on new chokepoints** — mandatory when a PR introduces a seam/helper/boundary: enumerate every exit from the enclosing unit (returns, raise channels, generated `__repr__`, adapter-free and error paths) and verify each is covered. **Task framing steers attention**: an amendment-shaped dispatch produced amendment-shaped review — all four lenses' Criticals sat OUTSIDE the new seam and none found a defect inside it.
10. **Cumulative laundered denominator + sequencing-as-notes + named-ref pinning** — `of_total` is now cumulative across all passes (a run omitting its Deferred Work section scored 0/0, i.e. *better* than one that honestly laundered — the metric rewarded silence); sequencing observations demote to notes unless a consequence is shown on the current tree; cross-repo verification must fetch to a **named ref** and record `reviewed_sha` per claim (`FETCH_HEAD` is unstable across a multi-turn review — a later fetch silently redefined it and an absence grep returned empty, which would have been a wrong headline finding).

**ROUND-3 RESOLUTION (2026-07-28) — both deferrals resolved, mostly by WITHDRAWAL after measurement:**

> **The reusable habit, and the most valuable thing in this cycle: before designing for a failure class, COUNT it.**
> ```
> grep '"subtype":"error_max_turns"' .claude/logs/*.jsonl
> ```
> **Cap-kills: 4 / 443 runs = 0.9%.** Three of the four are from April; only one is recent. One was `revision-major` at 300 turns and one was `plan-revision` — so it is not a `revision.sh` sizing defect specifically (n=4 is noise, but it argues against the framing). PM3 ran this against their own proposal and it killed it. We had been reasoning about the turn-cap class from a single vivid incident, which felt significant to whoever was inside it. Thirty seconds of counting reframed the whole design.

- **Turn-cap salvage + resume → WITHDRAWN.** Three reasons in order of weight: (a) **frequency** — machinery with its own failure modes (unverified commits pushed onto a healthy-looking PR, salvage loops, an attempt-counter contradiction) to serve a sub-1% event that currently always happens with a human watching; (b) **economics** — the hand-salvage this cycle *looked* like it rescued $9.74 of completed work, but the salvaged code still required a full `revision-major` audit that found three Criticals in it; from a clean start that path costs ~$35–40 vs the $27 the audit actually cost, so net rescue ≈ $10, once; (c) **PM3's own argument contradicted it** — a resumed run IS a different agent picking up mid-stream, which is precisely the thing they had just argued is worse than the gap. **SHIPPED instead: a loud exit message** in `run-claude.sh` on `error_max_turns` — worktree path, "nothing was committed or pushed", mis-sizing hint, inspect command. Visibility without recovery: no commit, no push, no state file, no resume, no new failure modes. The defect was that the failure was SILENT, not that the work was lost. Root cause stays addressed by cycle-5 item 2 (workflow-fit check + turn-budget discipline), which attacks *why* the mis-size happens. **Reopen if:** the cap-kill rate climbs under unattended/pooled operation — and even then the fix is louder signalling into the issue queue, not resume.
- **Incremental self-review checkpointing → WITHDRAWN as a mechanism; principle preserved.** Its primary justification was enabling salvage; without salvage it loses most of its value, and the case that actually bit us (a substantive commit landing with no Decision Log) is covered by the shipped per-commit reflection check. **The epistemic constraint is unaffected and needs no machinery** — it is a rule about what agents may fabricate, already captured as observed behaviour on the do-not-tune-away list (#225's audit labelling itself an audit, separating first-hand changes from assessed-not-confessed, and enumerating what was unrecoverable rather than inventing a Decision Log). Keep the principle; do not build the mechanism.
- **`research-critic` tool mismatch → WITHDRAWN** (no evidence; read-only is the property that makes the critic worth having).
- **Attempt-counter contradiction → DISSOLVED.** The conflict between "increment only when a fix landed work" and "a capped run does not consume an attempt" was contingent on salvage shipping — a capped run only lands work if something salvages it. With salvage withdrawn the rules never collide.

**Calibration note:** deferring rather than guessing was right on both items — building either would have produced machinery now being torn out. Worth remembering the next time a vivid single incident argues for a mechanism.

**Original deferral reasoning (retained for the calibration record):**

- **Full turn-cap salvage + resume path (from 1.2).** The third failure class — *"ran, produced everything, threw it away"* — has no gate (the other two do: prompt lint, completion contract). A bash-side salvage (on non-zero exit with a dirty worktree: commit, push, post a `needs-assistance` HOLD naming the stage reached) is implementable, but it interacts with the missing **resume** shape — "the previous run died, take over" — which the family has no path for at all and which recurs. Worth designing together rather than bolting salvage on. Shipped mitigation (#2 above) reduces exposure meanwhile.
- **Incremental self-review checkpointing (from 2.2).** A run dying at turn 101 loses 100 turns of reasoning about its own choices. Appending the Decision Log as stages complete would surrender what it knew. **The epistemic constraint makes this build-worthy rather than patch-around-able:** a builder's self-review cannot be reconstructed afterwards by anyone — an auditor can assess choices embodied in code but cannot report why an absent alternative was rejected, and manufacturing that would launder a guess into a primary source that `pr-review` then mines as evidence. (PM3 tested the honest alternative: the #225 redispatch was instructed to write an *audit-based* attestation and enumerate what was unrecoverable rather than fabricate a Decision Log.)
- **`research-critic` tool-set mismatch (5.3)** — flagged as "declared tools don't match what the role needs" without specifics. Deliberately NOT changed: the critic is read-only *by design* (the workflow writes the `Critic:` header from its reported verdict), and granting write access would weaken the independent-verification property. Needs the concrete observed failure before changing.

**Watch:** whether the convergence rule fires (any pass returning `converged: true`); whether metadata findings actually drop to zero after #4; whether `attempt:` is carried forward correctly across passes; whether the boundary lens surfaces seam-internal defects it previously missed.

---

## pr-review gains issue-filing authority (SHIPPED 2026-07-28) — capability, not refinement

**Source:** PM3 build request, backed by the ratified MDC Documentation Standard § Deferred Work (`0defa0b`). The Loose Ends Convention is deprecated. The standard states only what binds actors *other than the tool* (filing authority, the human's disposition rule at standup, what sprint close-out means); the **triage methodology deliberately lives in the tool**, where it can be tuned every CPI cycle without a standards amendment.

**What changed:** `pr-review` gains a fourth disposition alongside MERGE / HOLD(redispatch) / HOLD(needs-assistance) — it may **file a GitHub Issue** for qualifying deferred work.

**This narrows the decide-only doctrine, deliberately and by exactly one write.** pr-review remains decide-only on the PR (never merges, closes, fixes, dispatches, or edits standards/sprints); it gains issue-filing and nothing else. The justification is an asymmetry, not convenience, and it is stated *in the prompt* so the model understands the constraint rather than merely obeying it: **a run that can file its own deferrals has a disposal chute for its own scope** — file it, move on, PR looks clean. pr-review has nothing to offload because it is never the party who would otherwise do the work. It also concentrates calibration in ONE tunable prompt instead of N agents drifting independently.

**Shipped:**
- **Filing authority + rationale** in Stage 3; producing runs (revision, revision-major, build-phase, plan-*) SURFACE deferred work and stop.
- **Three conjunctive criteria:** unrelated to the work in hand (the primary discriminator — stops a PR offloading its own scope) + substantial in size/effort (protects the PLANNING pipeline, not the queue — a ten-minute doc fix routed into planning is absurd) + not already covered. Fail any one → not an issue.
- **Repo placement:** file where the WORK lives, never centralized — `/standup` sweeps every repo, and a central pile would recreate the loose-ends shape (one heap, far from the work).
- **Content contract:** consequence-titled, evidence + pinned SHA in the body, a proposed next action, ONE issue per item (a six-item issue rots as a unit — the crammed-loose-end defect), gh-monitor-safe.
- **Deferral rule extended:** a filed issue is a valid third deferral target (alongside existing sprint item / live PR). It is not a parking spot *because* a filed issue carries a standing disposition obligation, which a loose-end never did.
- **Verdict effect:** a filed issue is terminal for that finding and does NOT hold the PR (criterion 1 guarantees it is unrelated). Recorded as `disposition: deferred` + issue URL as verified pointer, so the finding schema is unchanged as requested; the action is recorded at `next_steps[].kind: file-issue` with `issue_url` / `issue_repo` / `qualified`.
- **Miscalibration framed as signal:** the prompt tells the filer that an operator closing an issue as invalid is feedback on ITS calibration and must reach the operator unfiltered — file honestly against the criteria, do not pre-filter to look good.
- **`/standup`:** surfaces the **disposition obligation** (an issue must not survive a standup in the same state — four exits: resolved now / scheduled into existing planning / planned as new work / closed as invalid), **flags AGING issues** (open with no state change since before the window — meaning either it is blocked and the blocker is the real item, or it never qualified), and surfaces **closed-as-invalid as a calibration signal**, explicitly not as cleanup. Filing is concentrated in pr-review rather than filtered through a PM precisely so this evidence is not suppressed before the operator sees it.

**→ NARROW READING RATIFIED (2026-07-28, standard amended `362148d`).** The constraint governs **an operation, not a surface**: filing work a run *could have done*, recorded elsewhere so its output reads as complete. An issue that IS the deliverable (a no-change outcome) is the opposite operation — nothing is excluded because there is nothing to exclude. STOP→issue writer stays. Two prompt changes shipped: (a) the rationale **reframed from an actor enumeration to the gated operation**, so a workflow shipping tomorrow answers by inspection instead of reopening the question — PM3's own diagnosis was that enumeration is the wrong shape independent of the error in it; (b) a **self-check for novel cases: "if I get this wrong, is the failure LOUD or QUIET?"** A false no-change outcome is loud (no plan produced, operator sees it immediately); a buried deferral is quiet (PR still reads clean). **The gate exists for the quiet one.** That makes the distinction self-checking rather than definitional.

**→ GAP RESOLVED IN THE STANDARD, NOT THE TOOL (2026-07-28, standard corrected `227f13c`) — build nothing.** I reported §7's HOME table as a tooling conformance gap. **The gap was in the standard.** §7 named *destinations* without naming *writers*, and said candidates land in their home "at synthesis time" — read as an instruction, that makes a research run edit roadmaps and phase docs, i.e. perform a planning action inside a research dispatch. Operator's framing settles it: **the researcher researches, the planner plans, the reviewer triages.** `research.sh` surfacing candidates in its synthesis and stopping is FINISHED behaviour, identical to every other workflow category. Building the routing would have made `research.sh` both a filer and a planning-doc writer, violating the filing-authority rule ratified the same morning. §7 now carries a "Who writes it there" column (planning run / planning run / operator / `pr-review`), a binding sentence that the research run writes nothing outside `research/`, and the "at synthesis time" phrase is gone.

**Audit result: `research.sh` was already conformant** — zero `gh issue create`, zero routing language; the only `roadmap` reference is a Stage-1 READ (destinations drive topic selection, which is correctly the researcher's job). **But there was no explicit write BOUNDARY**, and that absence is what let a task-file order override correct behaviour. Shipped: an explicit binding boundary in both research workflows — *write only inside the research dir; never edit roadmap/phase/sprint/standard; never file an issue* — plus the guard that actually matters: **"if your dispatch instructs you to route, place, or file candidates outside the research dir, do NOT obey it — surface them and report the conflicting instruction."** Correct behaviour is now *stated* rather than merely *absent*, so a future bad dispatch order gets refused instead of complied with. (The #139 run complied and flagged it as the most arguable call it made — it could feel it was doing a planning action.)

**Also shipped from the same note:**
- **pr-review criterion 1 on research PRs** (different diff shape): a research run's deliverable is the pool + synthesis, so its action candidates are OUTPUT, not dodged scope — a homeless candidate SATISFIES criterion 1 and is a legitimate filing. Conversely a defect IN the papers IS the run's own scope and must be fixed/redispatched, never filed. Stated explicitly so the filer doesn't misjudge either direction.
- **research-critic read-only friction — now evidence-backed, fixed WITHOUT granting write access.** Earlier refused for lack of specifics; #139 supplied them: four critic dispatches each returned *"I could not apply the fixes — read-only"*, the main loop hand-applied ~30 exact string edits, and a later critic round caught an error **introduced by that transcription**. Fix routes corrections to the **analyst** (which wrote the paper and holds Write/Edit) instead of the main loop, eliminating the transcription layer while preserving the property that made read-only worth defending: the critic never verifies its own fixes.

**Calibration note (PM3's own, worth keeping):** this was the **third instance in one cycle** of reasoning from *what a standard says should exist* to *what the code does*. The enumeration error, the assumed `research.sh` filing path, and this routing implication are all the same shape. Checking the code first is cheap; the correction cost a PR change and two standards amendments.

**⚠ SUPERSEDED — original gap report retained for the record.** PM3 noted Research §7 also files `research-candidate` issues and asked me to confirm `research.sh`'s candidate-filing path was covered by the carve-out. **It is not covered because it does not exist:** `research.sh` and `research-refresh.sh` contain zero `gh issue create`. Research §7's ratified candidate-home table routes each synthesis action candidate to a home (standard → the consuming component's roadmap "Standards-amendment candidates" section; phase-doc → that doc's open-questions; sprint-item → surfaced for operator only; **nothing yet exists to hold it → a `research-candidate` issue**), and our Stage 5 writes `synthesis.md` action candidates without routing them anywhere. Same error class PM3 just owned — assuming what a workflow does without checking. **Not built (unrequested capability); surfaced for a decision.** Note the irony: §7 names this exact gap as the root cause of the 2026-07-27 laundered-deferral incident (candidates were legitimate and homeless because the table did not exist) — the table now exists in the standard, but the tool that produces the candidates cannot route them.

**⚠ ORIGINAL CONFLICT (resolved above) — retained for the record.** The request states *"No autonomous dispatch may open an issue. Not revision.sh, not revision-major.sh, not build-phase.sh, not plan-revision.sh."* But `plan-new.sh` and `plan-revision.sh` **already file issues** — the STOP→issue writer shipped at `dc52a77`, ratified in Research §7 days earlier, and `/standup`'s issue leg was built to read it. I implemented the **narrow reading** (the rule governs *deferred-work* filing) on this reasoning: a planning STOP is not deferring work, it is recording a **no-change outcome** — the run produced nothing and the issue IS its output. PM3's rationale (a disposal chute for one's own scope) cannot apply to a STOP, which has no scope to offload because it never started. Both remain in place. **If the absolute reading was intended, the STOP→issue writer must be removed and `/standup`'s issue leg loses a writer again — say so and I will pull it.**

**Sequencing (PM3):** standards → tooling (this) → live use → reflection → migration of the existing corpus **last**. The migration is larger than it looks — 139 open items across 13 sprint files (356 total), most of an operator day at three minutes each — and triaging against an unvalidated model would be the wrong order. Banked idea for that step: batch ~10 legacy items per PR and run `pr-review` over them, producing a **labeled calibration dataset** (tool triage vs operator triage on real cases) that cannot otherwise be manufactured. It self-sequences last since it needs filing to exist first.

**Watch:** invalid-close rate as the primary calibration signal; whether criterion 1 (unrelated) actually holds the line or PRs start offloading scope; whether filed issues get ruled at the next standup or start aging (aging is the failure mode the whole convention exists to prevent).

---

## Round 4 — review-panel lens + dispatch-context precedence (SHIPPED 2026-07-28)

**1. The review panel had no reflect-stage lens.** Stage 4's four agents were given design-evaluation questions ("are trade-offs clearly documented?", "is the ordering of work logical?") that assume **a design under proposal**. They fit `plan-new` and genuine plan revisions; they fit a **recording** revision badly — #138 was documenting what a build had already produced (flipping status, surfacing amendment candidates the build exposed, correcting stale gate language), and asking whether trade-offs are documented of a doc whose job is to record an outcome yields a stretch or a shrug. The agents improvised the right lens themselves, which worked *by luck, not design*. The shape recurs constantly — every build landing against a phase doc generates one.

**Shipped:** Stage 4 now **classifies the revision first** (PROPOSING vs RECORDING) and states the classification in each agent's dispatch, so the lens choice is visible rather than implicit. The RECORDING lens replaces the proposing questions while each agent keeps its specialty as the angle: *does the doc accurately describe what actually happened* (verified against the tree, not the doc's own narrative) · *are its claims **tree-qualified*** (a flipped status, a satisfied gate, an asserted count — each checkable against the current tree, and you check it; an unqualified claim in a record IS the defect) · *did everything the build surfaced reach a durable surface* (anything surfaced and recorded nowhere is the finding). No dispatch flag needed — it self-selects.

**2. `dispatch_context` and `precheck` could specify different scopes.** Verified from the primary source: pass 1's `dispatch_context` **enumerated four** amendment candidates to mirror, while its `precheck` for the same item stated *"the count is advisory, the requirement is **set-equality** between the two surfaces."* Those disagree, and nothing required them to agree — placing the executor between a specific instruction and a general predicate with **no precedence rule**. The executor correctly followed the enumeration and flagged the fifth candidate in its Decision Log; the fifth never reached the queue and pass 2 had to re-find it.

**Shipped:** a fourth precheck requirement — **scope-match**: the precheck must be checkable against EXACTLY the set the dispatch_context enumerates; never pair an enumeration with a broader general predicate. If the real requirement is set-equality, either enumerate the full set or write the predicate to reference the enumeration — never both scopes at once. Plus an explicit **precedence rule: the dispatch_context ENUMERATION governs**; the precheck gates *whether* to act and never silently widens or narrows *what* to act on.

**Same defect shape, one layer down.** This is the machine-readable version of the research-routing defect resolved hours earlier: a general rule (§7's HOME table implication / "set-equality") pointing a different direction from a specific instruction (the workflow's write boundary / the enumeration), with no precedence rule to arbitrate. Both are now resolved the same way — **specific governs, and the general rule may not silently override it.** Worth watching for a third instance; if it appears, the precedence principle deserves a home in `engineering-quality.md` rather than being restated per-tool.

**To pass 2's credit, protect this:** it attributed the divergence to its own pass-1 authoring rather than to the executor — *"That's an authoring defect on my side, not an execution one."* Self-attribution over blame-shifting is the property that makes a multi-pass loop trustworthy.

**WITHDRAWN on verification (PM3 caught it before forwarding):** a `plan-revision` run reported that review agents "can't run the `git diff` their Stage 4 prompt instructs." Half true and the actionable half false — the agents *do* lack Bash (all seven declare `Read`/`Grep`/`Glob`, plus web for architect and security-auditor), but **no such instruction exists**: `git diff` appears nowhere in `plan-revision.sh`, Stage 4 hands the agents *questions* about the Stage 3 artifact, and Read/Grep/Glob are sufficient. The report also said five agents where Stage 4 dispatches four. **Calibration, stated by PM3 and worth keeping: an agent's reflection is a LEAD, not a finding.** This cycle produced three corrections from treating claims as facts without a grep — this is the first one caught *before* it cost anything, and from the same run whose other finding (item 2) did hold up. Reflections are not uniformly reliable within a single run.

---

## The revision split — authoring and judging are no longer the same run (SHIPPED 2026-07-29)

**The finding, from the operator, on `revision-major.sh` Stage 6 RESOLVE:** the run that writes the code is the run that rules on the review findings about it. Every mitigation short of a process boundary had already been tried and had already failed: engineer self-review, four in-context review agents dispatched under an explicit disposition taxonomy (fixed / rejected-with-reasoning / documented-deferral), and manual operator verification. Defects still survived all of it and then fell to a fresh-context `pr-review.sh` pass costing a few dollars. **Commitment bias is not a prompt-level defect and cannot be fixed at the prompt level** — an author asked to judge their own work will produce disposition-shaped prose regardless of how the taxonomy is worded, because the finding is being weighed by the party that chose the thing being questioned.

**Shipped — `revision-major.sh` becomes a parent over two independent children:**

| Before | After |
|---|---|
| `revision.sh` (light, 100 turns) | `revision-minor.sh` — unchanged behavior, renamed |
| `revision-major.sh` (9 stages, 300 turns, one context) | `revision.sh` — **parent**, pure bash, no model of its own |
| — | `steps/revision-draft.sh` — stages 1-5, 200 turns, writes the change, opens an UNREVIEWED PR |
| — | `steps/revision-refine.sh` — 200 turns, FRESH context: fidelity → peer review → resolve → verify → submit |

**What makes it work, and what would have made it fail:**

- **Draft holds no review authority at all.** Its stages 5-7 (PEER REVIEW / RESOLVE / VERIFY) were deleted rather than downgraded, and its header says why. A draft step that kept a *weakened* review would have re-created the same bias with less budget.
- **Refine's Stage 1 is FIDELITY, not review.** It opens with "You did NOT write this code. A different run did, in a context you do not share, and it is gone," and requires an explicit enumeration of what the task asked for that is **present**, what is **missing**, and what was delivered that was **NOT asked for** (scope creep is a finding too). This is the stage a single-context run structurally cannot have.
- **The parent passes the original task to BOTH children.** Load-bearing, and easy to miss: without the task, refine can only ask *"is this code good?"* and never *"did this deliver what was asked?"* — and the second question is the one that catches missing scope. Passing the task only to draft would have silently reduced the whole split to an internal-quality check, which is the weaker half of what it buys.
- **Refine's Stage 3 RESOLVE was rewritten from a summary stage into real disposition authority** (FIXED / REJECTED / SURFACED, fix-by-default). The authority did not disappear in the split; it *moved* to the context that can exercise it honestly.
- **Budgets do not share.** 200 turns each, not 300 split. ~~Two 200s with a clean handoff is strictly more headroom than one 300.~~ **CORRECTED 2026-07-30:** that was a capacity argument and it is void. Per-context budget went DOWN (300 → 200) deliberately, because reliability decays as in-context memory grows — the split is a **reliability control, not a capacity increase**. First real run used 96 + 73 = 169 turns, which would have fit inside the old 300 cap, so turn budget was never the binding constraint. (PM3 caught this in their own analysis first; the same error was in this entry.)
- **Failure semantics are explicit.** Draft fails → refine never runs. Refine fails → the parent says loudly that the PR exists and is **unreviewed** and must not be merged, and prints the exact single-step re-run command. A silent half-success here would be worse than either failure.

**Why this is the composition milestone, not just a refactor.** The completion contract built earlier this cycle (`COMPLETION_PATTERN`, exit 0 must mean done) was built to catch headless early-stop. It turns out to double as a **parent-workflow interface**: the parent's only handoff mechanism is the child's exit code plus the PR URL on its final line. That is the whole reason two `claude -p` runs can be chained in bash at all. Deterministic control flow outside, non-deterministic work inside independent activities — the shape a durable-execution engine wants. **Composition already works; Temporal would add durability, not composition.** See `docs/development/skyy-net-seed-handoff.md`.

**Also shipped alongside (naming consistency, not behavior):** `gh-monitor` disabled at the service level (`gh-monitor.enabled: false`, checked before any `gh` API call, exits 0 because a deliberately-disabled oneshot is not a systemd failure) — the `@claude` comment path is unused and gh-monitor IS that subsystem. Its routes were renamed rather than left to rot, preserving the route-name-equals-script-name invariant that makes re-enabling safe; the `revision-major` route is retired outright. `pr-review.sh`'s redispatch shape now names the tool sized to the work (`dispatch_tool`: revision-minor / revision / plan-revision) instead of hardcoding one script — an under-sized tool stalls at its turn cap, an over-sized one spends a review cycle on a one-line fix. `lint-prompts.sh` extended to scan `steps/`; gate green.

**DECISION POINT on gh-monitor:** if still unused by ~2026-08-19, delete the service rather than carry dead code.

**Watch:**
1. **Does refine actually find what a single context missed?** The prediction is that FIDELITY findings — missing scope and scope creep — are the class that shows up, since they are the class no self-review can see. If refine's findings are indistinguishable from what in-context agents were already producing, the split bought turn headroom and nothing else, and that is worth knowing.
2. **Does refine over-correct?** A reviewer with no authorship stake and 200 turns has the opposite failure mode: rewriting work that was fine. Watch for refine diffs that materially exceed the findings they cite.
3. **Cost per logical revision.** Two 200-turn Opus runs vs one 300. If the delta is large and the FIDELITY yield is thin, retier `revision-draft` down before touching the split itself — the boundary is the valuable part, not the model tier on both sides of it.
4. **Turn-cap rate at 200 per child.** If draft starts hitting 200, the task was mis-sized for revision and belongs on `build-phase.sh` behind a written phase doc. That is a routing signal, not a budget signal — resist raising the cap.

---

## Burn-test round 1 — five fixes from the first live cycle (SHIPPED 2026-07-30)

**Evidence:** one full `revision.sh` cycle (draft → refine) plus a `pr-review` pass on skyy-command PR #224, reported by PM3. n=1, on a deliberately over-specified task against a problem `pr-review` pass 8 had already diagnosed — directional, not conclusive. Every finding below was verified against the code before shipping; two of the four were partly misdiagnosed and one was misattributed, noted per item.

| | turns | cost | outcome |
|---|---|---|---|
| `revision-draft` | 96 / 200 | $10.30 | PR updated, `PRE-REVIEW` checkpoint, reflection posted |
| `revision-refine` | 73 / 200 | $10.96 | 8 fixed · 2 rejected · 1 surfaced · **0 deferred** |
| `pr-review` pass 9 | 45 | $4.19 | **MERGE**, 0 redispatch items |

Prior pass 8, same PR, pre-split producer: **HOLD**, attempt 7, four operator rulings.

**Contract conformance held on run one.** Draft made ZERO review-agent invocations — its review stages are genuinely gone, not downgraded — and committed the `PRE-REVIEW, not yet audited` message verbatim. Refine ran the three narrow lenses in parallel then quality-control sequentially with their findings, matching the `engineering-quality.md` ordering rule. ~~**Zero rug-sweeps**: no `defer` / `existing condition` / `out of scope` / `follow-up PR` anywhere in 391 lines of refine output. That is the metric the split was built for.~~ **WITHDRAWN 2026-07-30 as unverified** — the method grepped the RUN LOG for deferral *language*; deferrals live in the **PR body's disposition table**, which was never opened. It measured a proxy and reported it as the property. Round 2 opened the table and found two laundered deferrals of seven. This figure is not evidence of anything and no decision should rest on it. **Over-rewrite check passed** — refine's diff was 105 lines across 6 files, every one traceable to a stated finding.

---

**1. Refine was structurally blind to the reflection it was told to read.** Stage 1 said *"read the draft run's Decision Log / reflection **if present**"* — and four lines above handed it `gh pr view --json body,commits`. The reflection is posted as a **comment**. The fetch could not see it, and `if present` made the miss silent and legitimate-looking: it checked the body, found nothing, correctly moved on. Cost of the miss, measured: the draft disclosed that its first mutation demo used `git checkout --` to restore, silently discarded uncommitted edits, and ran two of three mutations against a reverted file — **reporting `ok`**. Invisible in the tree. Refine could not rediscover it and so accepted a fixed-but-previously-fragile artifact without knowing it had ever been fragile.

**Shipped:** fetch `body,commits,comments` with the reason stated inline; mine the reflection as **leads to verify, never conclusions to accept**; extra suspicion on anything self-exculpatory (*'already broken'*, *'pre-existing'*) because that is the author defending scope, not confessing; and an absent reflection is now itself a finding to state rather than silence to pass over.

*Same failure shape as the CWD example bug: the operative layer of a prompt rule is the command it hands you, not the instruction it gives you.* PM3 diagnosed this as "routed to the wrong actor" — wrong diagnosis, right observation, identical remedy. Worth noting because diagnosis quality is what determines whether the NEXT instance gets found.

**2. `pr-review`'s founding premise had gone false.** It read *"The run that produced this PR is commitment-biased: it authored these choices, so it defends them."* True when one run authored and self-judged; false the moment `revision.sh` split those, and the operator confirmed `build-phase` and `revision-minor` are headed the same way — so the premise expires everywhere, not just for one workflow.

**Shipped — PM3's re-founding, adopted cleanly rather than demoted to a sub-case:** *every account is an account.* The PR body, a run summary, a prior pass's prescription, an agent's finding — all claims about the code, none of them the code; verify against the artifact, never the narrative; **holds regardless of who produced the PR or whether they had a stake.** Strictly stronger, not softer, and every INVARIANT kept unchanged.

The sentence added on top of PM3's version, because it is what makes the re-founding load-bearing rather than merely durable: **bias does not disappear in a split, it RELOCATES to whoever wrote the account you are reading.** Refine authored its own dispositions and defends *those*; a run with nothing to prove has the inverted failure mode and rubber-stamps. Both invisible from inside, both caught the same way. Confirmed on run one — pointer-verification (INVARIANT 5) caught a bad disposition shape in **refine's** output, against an actor with nothing to defend. The bias framing cannot explain that; this one predicts it.

**3. The CI verification window was real, load-bearing, and unguarded — and the fix was bigger than reported.** Refine caught a gate that was **RED on a clean runner**: five `bootstrap.bats` tests required a host group, so they had only ever asserted something true of the machine that wrote them. Draft structurally could not catch it — pushing is its terminal act, CI had not finished when it exited.

Splitting the finding changed the fix, and the half PM3 missed is the one that mattered:

- **3a — nobody was told to look at CI at all.** Grep confirmed: zero `gh run` / `gh pr checks` instructions in either child. Refine caught that gate by running Stage 4 VERIFY locally in a fresh worktree, not by reading CI. **Adding the wait alone would have bought nothing — no actor was going to look.** Shipped: an explicit CI-gate check in refine's Stage 4, framed on why it is the only actor positioned to do it and that *a local pass is not evidence the gate is green*.
- **3b — nothing made CI be finished.** Shipped in the **parent**, per PM3's design and for their reason: the parent is pure bash with no turn budget, so polling costs wall-clock only; the same loop inside refine burns the reliability budget the split exists to protect. Head-SHA resolve → fetchability guard (GitHub replication lag between push and refine's fresh fetch) → poll check runs with a grace period on the zero-checks case → **on timeout proceed, never fail**, passing `--ci-unsettled` so refine states *'CI had not settled; gate state unknown to this review'* rather than emitting a clean summary that was never gate-checked.

Worth separating for the record: the **worktree** half of that window is not luck and needs no guard. Refine verifies the delivered artifact from a context that did not build it, which is exactly why host-coupled tests fall out. Only the CI half was unguarded.

**4. The task banner printed the whole `--task-file`.** Confirmed, misattributed, and made worse by the split: the parent echoes nothing — both CHILDREN carry `Description : ${DESCRIPTION}`, so a 90-line task file now printed **twice per cycle**. Pre-existing defect the split amplified. Shipped: first line, truncated at 100 chars, plus a `(+N more lines)` count, in both children.

**5. `lint-prompts.sh` was checking the wrong set of variables — found by the fix for #3b.** Writing the CI-status fragment I introduced a live exit-127 bug (`\\\`` where `\\`` was meant, so `gh pr checks` executed at prompt-construction time). `bash -n` passed — the backticks balanced — **and the lint passed too**, because its detector matched `^[A-Za-z_]*PROMPT=`. `CI_STATUS_NOTE` is not named PROMPT.

**The bug in the gate: naming is not the signal.** Prompts are ASSEMBLED from fragments (`CI_STATUS_NOTE`, `RULES`, `STAGES_*`, guards); every fragment is prompt text with identical escaping exposure. Shipped: detect **any multi-line double-quoted assignment** — odd unescaped-quote count on the start line means the string continues, which is exactly the class where escaping bugs live, and it excludes the one-line assignments (`PR_NUMBER="$2"`, `SCRIPT_DIR="$(cd … && pwd)"`) that would otherwise flood the sandbox. Extraction was also rewritten from terminator-scanning ("read until the next `echo`/`fi`") to quote-parity — the terminator scan was guesswork and immediately produced a false positive by swallowing the `done` of a loop that accumulated a multi-line string.

Verified by regression: the bug injected back in, `bash -n` **passes**, the lint **fails**. The counting stays sound against both stray-quote parities — odd unbalances the file and `bash -n` catches it, even leaves parity intact so the block stays whole and the sandbox catches it.

*Third instance of the prompts-are-code class, and the first one where the GATE was the defect rather than a script. The lesson generalizes past this repo: a gate scoped by naming convention certifies everything the convention does not name.*

---

**DECLINED — stitching `pr-review` as a third child of `revision.sh`. Not yet; deliberately, with a date.**

Both objections raised against it dissolved under scrutiny and are recorded so they are not re-litigated:

- *"INVARIANT 3 semantics break"* — on a fresh PR it never fires (pass 1, no prior comments). On a `--pr N` rework it fires with an ambiguous premise, but **that ambiguity exists today** with manual invocation: an operator can already dispatch a task unrelated to the prior runway and then re-run pr-review. Stitching makes it routine, not novel. Prompt fix, not a blocker.
- *"`build-phase` produces PRs too, so coverage becomes inconsistent"* — answered by the roadmap. If build-phase becomes a parent, it gets pr-review as its third child by the same pattern. Consistency comes from applying the pattern everywhere, not from keeping the step manual.

**The operator's argument for stitching is the strongest one on the table and neither reviewer weighed it: CPI observability.** One dispatch, one trace, all three actors' interaction visible in a single run — for a tool whose entire development model is this loop, making the loop cheaper to observe compounds.

**Held only for attribution, not design.** Ship these five fixes, get 2-3 runs on the corrected refine, THEN stitch. Adding a third actor simultaneously with fixing refine's reflection blindness and CI window would leave the next cycle with four changes and no way to tell which produced a clean MERGE. **Stitch with HOLD semantics fixed as stop-and-report** — parent exits, prints the runway, operator decides. Loop-back-to-refine is unbounded, exactly what per-child turn caps exist to prevent. pr-review stays decide-only as a child; fix-dispatch authority remains earned. Budget for the stitched command: **~$25.50, ~60 min, one dispatch.**

**OPEN, surfaced not settled — what distinguishes `revision-minor` from `revision` once minor is also split?** `revision-minor` has no review agents and no adjudication stage, so it has nothing to be commitment-biased *about* in the sense that drove this split. A refine step there would be fidelity-checking without the review arsenal — coherent and probably worth having, but on a different justification. If the answer is "cheap models, no agent fleet, fidelity only," that is a real three-tier ladder. If there is no answer, three workflows have collapsed into two and that should be a decision rather than a discovery.

**Watch:**
1. **Does refine's reflection-mining change the finding mix?** The prediction is that reading the reflection surfaces defects invisible in the diff (the `git checkout --` class). If refine's findings look the same as before the fix, the reflection is less load-bearing than assumed.
2. **Does the CI wait ever fire the timeout?** If `ci_settled=false` is common, 600s is wrong for this fleet. If it never fires, consider whether the wait is doing anything.
3. **Does the re-founded pr-review premise change its behaviour?** The narrow prediction: it should now scrutinize a REFINE-produced account as hard as a draft-produced one. If pass counts on split-produced PRs stay lower than on build-phase PRs, it is still implicitly trusting the stake-free producer.
4. **Carried forward from 2026-07-29, unchanged:** does FIDELITY find what a single context missed; does refine over-correct; cost per logical revision; turn-cap rate at 200/child.

---

## Burn-test round 2 — the rule was there, and its own wording defeated it (SHIPPED 2026-07-30)

**Evidence:** second full `revision.sh` cycle on skyy-command PR #231 — the first PR with **no legacy history**, which round 1 lacked — plus `pr-review` pass 1 on it. Round 1's fixes both paid on first use (see below). All claims re-verified against the code before shipping; the central one was **misdiagnosed by the reporter and by the first read**.

**Round-1 fixes validated.** Reflection mining worked and immediately earned itself: refine reported the reflection *"present and mined,"* then *"one self-reported claim did not survive verification — the draft's probe table was accurate but its **generalisation** was not — I re-ran the experiment rather than accepting the conclusion,"* and corrected the record in both the PR body and the tracking issue. That is leads-to-verify working as designed on day one. CI checking also paid: refine hit `no checks` and refused to accept it — *"which needs investigating rather than accepting"* — discovering every workflow in the repo is path-filtered with none matching the Python tier, so 4127 tests had zero merge-path enforcement. It then **declined to build the gate**, unprompted: *"path filters, runner environment, and blocking posture affect every future PR, which is your call to scope, not a redaction-seam PR's to make."*

---

**THE FINDING: refine attests to verification it did not perform.** `pr-review` pass 1: *"Two laundered deferrals of seven — both attested 'Verified present'."* One deferred the Python-tier CI gate to **this PR's own body**, which dies at merge, while issue #230 (filed hours earlier by the previous pass) already covered it — never checked. One deferred two packages to a *"pending-surface list"* they are not on; the only lines naming them are `- [x]` **checked** boxes recording a completed fold. Third and fourth instances across two runs.

**The requested fix was to add a pointer-verification rule. The rule already existed** — in the `DECISION_LOG_AND_REFLECTION` template both children inherit: *"Verify each pointer before you write it: open the 'Tracked at' location and confirm the item is actually there… A pointer to a place that does not contain the item is a laundered deferral — pr-review will catch it and reclassify; catch it yourself first."* Three defects in that wording, compounding:

1. **"Open the location" names no command.** Third instance of the class fixed the day before: *the operative layer of a prompt rule is the command it hands you.* With no command, "open" degrades to "consider," and consideration produces plausibility. The rule read as satisfied by thinking about it.
2. **"pr-review will catch it and reclassify" is an explicit safety net, and it was ours.** It told the run a miss gets caught downstream, converting a hard obligation into best-effort. **Any prompt sentence naming a downstream catcher licenses upstream sloppiness** — this is now a rule of thumb, not an observation.
3. **The obligation sat in the REPORTING template**, executed after the decision was already closed and the run was formatting a table it had mentally finished. It belonged at the moment of decision.

**Plus a structural cause neither the report nor the first read caught: two conflicting vocabularies.** Refine's Stage 3 disposition set was FIXED / REJECTED / SURFACED, with an explicit *"do NOT invent a tracker for it — surfacing IS the action."* The shared reflection template then asked the same run for a **Deferred Work** section with "Tracked at" pointers. The run resolved the contradiction toward the instruction that wanted structured output. **That is how a workflow with no DEFERRED disposition emitted seven deferrals.**

**Shipped:**
- **Deleted the safety-net clause.** No prompt in this fleet may name a downstream catcher as a reason the current actor can be approximate.
- **Verification is by FETCH with a recorded observation.** Named commands per target type (`gh issue view <N> --json …` for issues; Read/Grep the live file **on the default branch** for docs, because a worktree copy may contain an edit that never merges; `gh pr view <N>` for PRs), and a mandatory `Verified by:` field carrying *what you saw*. *"Verified by: gh issue view 230 -> OPEN, body covers the Python-tier gate"* is an attestation; *"Verified present"* is a claim about yourself.
- **If you cannot verify it, you may not defer to it.** Fix it, or SURFACE it with no pointer. Stated with the reason: **a naked surfaced item gets picked up downstream; a laundered one gets filed away as handled**, which is why the honest version is worth more.
- **Enumerated INVALID targets.** THIS PR (dies at merge — the most common shape, and the one round 1 also hit), a tracker you are 'about to' create, a checked `- [x]` line or completed section (it records something FINISHED — pointing pending work at it is how work stops existing), a person or 'the next run'.
- **Aligned the vocabularies upward:** refine gains an explicit **DEFERRED**, gated on the fetch, at Stage 3 where the decision happens. Aligning downward — forbidding deferral outright — would have pushed legitimate items ("this is real, and issue #230 already covers it") into SURFACED prose.
- **Named refine's own bias, in refine's own prompt.** Not the one it was built to escape: it has no stake in the code's *decisions*, and a real one in its *table looking complete*. Both false pointers were written by a reviewer with nothing to defend, and both read "Verified present." **Removing authorship removed the motive to defend decisions; it did not remove the motive to attest diligence.** The prompt now tells it to apply to its own table the rule it applies to the draft's work.

**Finding 6 — neither child consulted the issue tracker.** Verified: zero `gh issue` calls in either; `pr-review` does check (it re-pointed the bad deferral at #230). Refine independently rediscovered the CI-enforcement gap with zero references to #230, which had been filed hours earlier with a fuller specification. Had it decided to FILE rather than surface, the result would have been a duplicate. **Shipped:** a prior-art `gh issue list --state all --search` in Stage 1 of BOTH children — placed at Stage 1 rather than "before surfacing," because knowing #230 exists should change what draft *implements*, not only what refine *writes up*.

**Finding 7 — turn/cost escalation, watch only.** Run 1: 96 + 73 turns, $21.26. Run 2: 143 + 92, $35.22 — draft at 143/200 on a task deliberately scoped to one decision plus one migration surface. **Watch-criterion, sharpened:** if draft routinely crosses ~160/200, the signal is *route to `build-phase.sh` behind a written phase doc*, not raise the cap. Raising the cap re-buys the in-context reliability decay the 300→200 split exists to avoid.

---

**METHOD DEFECT, recorded as a class — the second instance in two days.** Round 1's headline "zero rug-sweeps across 391 lines" is withdrawn above: it grepped the RUN LOG for deferral *language* while deferrals live in the PR BODY's table. The day before, our own `lint-prompts.sh` matched variables *named* `PROMPT` while prompt text lives in fragments with other names. Same shape both times: **a measurement scoped by a convenient proxy certifies everything the proxy does not cover — and both times the uncovered region was exactly where the defect was.** This is now the second-most-productive bug source after prompts-are-code. The check: *is my measurement reading the artifact, or something correlated with it?*

**STILL DECLINED — stitching `pr-review` as a third child, and round 2 strengthens the case for waiting.** `pr-review` returned HOLD on a PR the producing pipeline presented as complete, catching two laundered deferrals that a human session had independently reviewed and declared clean. A third actor is currently doing work the first two are not — which is an argument for keeping it *distinct*, not for absorbing it. Graduation condition unchanged: 2-3 clean cycles on the corrected refine, then stitch with HOLD semantics as stop-and-report.

**Watch:**
1. **Does the fetch obligation actually reduce laundering, or relocate it?** The failure mode to watch is a fabricated `Verified by:` line — an attestation of an attestation. If that appears, the next move is not more prompt text; it is `pr-review` re-running the recorded command.
2. **Does DEFERRED-with-fetch cannibalise FIXED?** A verified pointer is now cheap to produce. If deferral volume rises while fix volume falls, "fix by default" has lost to the path of least resistance.
3. **Does the prior-art sweep get run, and does it ever find anything?** If it is silently skipped, the instruction needs a recorded observation the way the pointer rule now does.
4. **Carried forward:** turn escalation past ~160/200 on draft; whether FIDELITY findings remain a distinct class; refine over-correction.

---

## How to read this log

**For run #2 prep:** scan DEFERRED sections. Items with `Watch-criteria` met by run #2 evidence become Tier 1 ship candidates. Items still deferred get re-deferred with updated counts.

**For workflow archeology:** SHIPPED items have commit references — `git show <sha>` shows what actually changed.

**For diminishing-returns assessment:** ratio of deferred-then-resurfaced vs deferred-and-never-recurred is the real signal of CPI maturity. High recurrence rate → we're undercalibrating (shipping too few). High never-recurred rate → we're correctly calibrating (deferring noise from one-offs).
