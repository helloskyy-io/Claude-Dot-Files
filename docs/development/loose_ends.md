# Loose Ends

Deferred items from architectural reviews and CPI cycles. Each entry includes context and recommended trigger for revisiting.

## How to use this doc

Add entries when deferring work that:
- Is genuinely out-of-scope for current focus
- Won't be addressed in the current session
- Is large enough to warrant separate context-rebuild later

For per-cycle CPI decisions (ship/defer/reject with watch-criteria), use `docs/development/cpi-decisions.md`. This file is for broader architectural deferrals identified outside of CPI cycles.

---

## STOP→issue writer — the memory model's second leg has no writer (identified 2026-07-27) → RESOLVED same day

**→ RESOLVED 2026-07-27 (commit shipping addendum 2 of the tune-3 handoff).** The operator caught the same gap independently and ratified the STOP→issue writer (Research §7). plan-new + plan-revision now file a labeled GitHub issue (`research-required` / `evidence-faulty`) on any research-sufficiency or evidence-integrity STOP — body carries the finding + both ready-to-fire next-step options + a `plan_stop:` yaml block; COMPLETION_PATTERN extended to accept the issue URL (a STOP that failed to record itself fails loud). `/standup` reads and surfaces them. The issue-surface leg is now written and read. Original entry retained below for the calibration record.

---



**Context:** `/standup` (shipped 2026-07-27) routes attention to two git-native memory surfaces — PR threads (change outcomes: reflections + `pr_review:` disposition yaml) and GitHub Issues (no-change outcomes: STOPs, pending decisions, per Research §7/§5.5). The PR leg is written and read. **The Issue leg is READ by /standup but WRITTEN by nothing** — audited: zero `gh issue create` across all workflows. The STOP conditions we shipped (research-sufficiency + evidence-integrity in plan-new/plan-revision; review-pr needs-assistance) report in-PR / in-output, not as labeled issues. So a STOP that only prints to a dispatch log is exactly the write-only failure /standup exists to prevent.

**Recommended action:** a STOP→issue writer — the STOP conditions file a labeled GitHub issue (`research-required`, `evidence-faulty`, + stop-classes) with the two-option next-step in the body, so no-change outcomes become durable surfaces /standup already knows how to read. Its own small spec: which workflows file, which labels, what body format (must carry the embedded next-step options /standup lifts verbatim).

**Trigger to revisit:** when a real STOP outcome gets lost because it only lived in a dispatch log (first occurrence ships it); or when the CPI-framework work begins (the autonomous standup consumer needs the issue surface populated). Until then /standup is empty-tolerant on the issue section — not blocking, but the leg is incomplete.

## Enterprise Quality Hardening — Architect Findings (2026-05-28)

Architectural review identified these gaps for moving from "above the bar for personal dotfiles" to "professional team-level tooling." Categorized by effort + priority.

### Infrastructure: testing + CI

- **Tests for the system itself.** Zero `tests/` directory. `block-dangerous.sh` has ~40 regex patterns with no fixtures, no attack corpus, no negative tests. `install.sh` untested. **Approach when triggered:** add `tests/` with `bats-core` for `block-dangerous.sh` (attack corpus + negative corpus) and `install.sh` (symlink creation, backup behavior). ~1 day initial setup. **Trigger:** before adding new hook patterns, or when block-dangerous.sh complexity grows.

- **CI on this repo.** No `.github/workflows/`. PRs merge without `shellcheck`, `bash -n`, JSON/YAML lint, hook-pattern regression tests, markdown link-check. **Approach when triggered:** `.github/workflows/ci.yml` with the above checks. **Trigger:** after testing infrastructure exists.

- **Safety hook threat model documentation.** Inline threat-model header was added to `config/hooks/block-dangerous.sh` (step 4-b) enumerating bypass classes the hook does NOT address (obfuscated commands, variable indirection, aliasing, here-strings, subshell smuggling) and the operator-context risk profile. **What's still deferred:** a full `docs/architecture/threat-model.md` with attack-corpus fixtures and a negative corpus that the hook can be tested against. **Trigger:** anyone other than operator starts using these workflows, OR an autonomous LLM demonstrates evidence of obfuscation attempts in logs.

### Operations: drift + recovery + visibility

- **Multi-machine drift detection.** No `install.sh --verify`, no per-machine state file (last-installed-commit), no way to ask "is laptop running stale config?" **Approach when triggered:** `install.sh --verify` mode + `~/.claude/.install-state` recording commit SHA + timestamp. **Trigger:** when adding a third machine, or when drift causes a real issue.

- **Disaster recovery story.** `install.sh` backs up but no documented rollback, no `uninstall.sh`. VM + workstation are backed up; laptop is not. **Approach when triggered:** `uninstall.sh` script + rollback procedure in `docs/guide/`. **Trigger:** before deploying to a machine without backup, OR if a bad install ever requires manual recovery.

- **Cost rollup tooling — basic version SHIPPED (step 4-b).** `lib/run-claude.sh` now provides `print_cycle_totals` which is called from every workflow's completion banner. Output shows current-month total cost + total turns across all runs, alongside the per-run summary. **What's still deferred:** budget alerts, per-project / per-workflow breakdown, dashboards. **Trigger:** if monthly totals approach budget limits and the operator wants automated alerts.

- **Proactive observability between CPI cycles.** No success-rate dashboard, p50/p95 turns/cost per workflow, hook-block frequency, rate-limit hits. **Approach when triggered:** `scripts/helpers/metrics.sh` rolling up trends; possibly static HTML dashboard. **Trigger:** when CPI cycles lag behind needed feedback velocity.

### Documentation: standards + onboarding

- **Author standards for the 8+ implicit architectural decisions.** Symlinks-vs-Stow, hook trust model under `--dangerously-skip-permissions`, polling vs webhook gh-monitor, JSONL log contract, four-bucket docs, worktree-per-task isolation, bash-over-Python workflows. These are real decisions with real trade-offs; only some are recorded. **Approach when triggered:** use `standards-architect` agent to draft each as a `docs/standards/<topic>.md`, operator reviews. Promote via batched standards-authoring sessions. **Trigger:** after `docs/architecture/system-overview.md` lands (provides the index of what needs full standards).

- **Onboarding doc** (`docs/guide/onboarding.md`). Operator is the only developer currently. **Approach when triggered:** "first 30 minutes" path with architecture tour + workflow decision tree. **Trigger:** before onboarding a second engineer.

### Operational polish

- **`gh-monitor` heartbeat / dead-man-switch.** Currently fails silently. **Approach:** heartbeat file or Healthchecks.io ping. **Trigger:** when a missed PR reply is traced to silent timer failure.

- **`settings.json` schema/grouping pass.** Currently a 300+ line wall with no comments/grouping. **Approach:** add comment sections (note: JSON doesn't support comments; would need conversion to JSONC or external doc). Plus a `settings-lint.sh` validator. **Trigger:** when adding new permissions becomes painful.

- **Workflow script versioning.** No `VERSION` per script. In-flight `@claude`-triggered runs would break if arg shapes change. **Approach when triggered:** `WORKFLOW_VERSION` constant + log it to JSONL. **Trigger:** when first breaking-change to workflow args is needed (probably never).

### Workflow integration deferrals

- **doc-manager invocation in workflows.** Operator decided not to integrate into `plan-revision.sh` / `plan-new.sh` for now. PM-side `proactive-doc-management.md` rule covers the use case. **Trigger:** if CPI cycles surface doc drift in PR-generated planning artifacts that the PM-side discipline doesn't catch.

---

## Watch-list (not yet at trigger threshold)

Items where the trigger condition exists but evidence hasn't yet justified action:

- **Best-practices vs project-standards rule effectiveness** (4th iteration of "don't take shortcuts" discipline). Whether the structural pre-implementation checkpoint actually reduces the easy-path failure rate. Evaluate at next CPI cycle.

- **Quality-control agent severity calibration.** ~~Whether the "over-surfacing is desired" bias produces useful signal or noise.~~ **PARTIAL FIX SHIPPED 2026-05-29:** first real outing surfaced a major failure mode — over-surfacing bias was applied uniformly to BOTH judgment findings AND factual claims, causing the agent to fabricate 6 of 8 "blockers" on PR #91 (claimed files didn't exist when they did, claimed code patterns absent when present). Root cause: methodology didn't distinguish judgment claims (over-surface OK) from factual claims (precision required). Methodology now split by claim type; agent prompt now requires Glob/Read/Grep verification before any factual claim; output format now requires explicit Evidence field with verbatim citations. **First post-fix dispatch report (2026-05-29):** structural fix is holding — agent hedged at 85% confidence on factual claims it couldn't fully verify ("I cannot run kubectl to verify") instead of confabulating certainty. No padding observed; F-5 was explicitly tagged "concur with Low disposition" rather than inflated. Value-add from integration lens preserved (F-1 forward-compat mismatch + SYS_TIME↔Raft systemic link caught, neither a narrow-lens finding). **Continued watch:** evaluate over 2-3 more dispatches. If fabrication rate stays near-zero on factual claims while judgment findings remain valuable, structural fix is proven.

- **PM1 — Stage 4 coverage-check guidance for non-discovered paths (REJECTED 2026-05-29).** Surface from skyy-command PR #94 reflection: when a task adds tooling under `scripts/` (or any non-runner-discovered path), the workflow's Stage 4 coverage-check didn't anticipate it; engineer had to wire discovery or use another CI path. **Disposition: rejected as claude-dot-files-level change.** The workflow correctly defers to `docs/standards/testing.md` for framework-specific mapping — friction is upstream in the project's testing standard, not in the workflow's defer. Engineer handled correctly (handled pragmatically, surfaced the gap). Send to PM3 lane for project-side standards-amendment evaluation. **Watch-criteria:** if 3+ dispatches across different projects all hit the same friction (workflow's testing-standard defer is insufficient because projects' standards don't address non-discovered paths), revisit — that would indicate the workflow needs to explicitly spell out "what if your project's testing standard doesn't cover this case?" One occurrence in one project is data, not pattern.

- **Bash CWD rule wording corrected (SHIPPED 2026-05-29).** Workflow scripts asserted `"Bash CWD does not persist between calls"` as a positive factual claim. Verified against Claude Code docs: documented behavior is CWD DOES persist (uses `/tmp/claude-{hex}-cwd` tracking files). Edge cases that disable persistence: custom statusLine command, subprocess invocation with `--input-format stream-json`, deleted persisted directory. Same failure mode as the QC fabrication issue (asserting facts that turn out wrong). Wording softened across all 6 task-execution workflow scripts to: "Don't rely on Bash CWD persistence... defensive practice: chain with `&&` or use absolute paths... defensive form works regardless of whether persistence is active." Operational guidance preserved; factual error removed. **Watch:** if engineers continue to report CWD friction despite the defensive wording, investigate root cause (statusLine config? subprocess invocation? specific environment difference?). 

- **Quality-control binding-vs-implementation drift detection.** Same 2026-05-29 dispatch missed Decision 3 binding-vs-implementation drift (Raft vs lease) — agent's Best-practices-grounding and Decision-rigor dimensions COULD have caught it but didn't apply that lens to the binding-language-vs-implementation comparison specifically. **Watch-criteria:** if the next 2-3 dispatches also miss binding-vs-implementation drift in similar shape (where binding standard says X but implementation does Y), ship a methodology amendment requiring explicit "verify binding language matches implementation" check as part of standards-adjacent reviews. One miss is data; pattern would warrant the fix. Premature now.

- **PM3 — gh-monitor "verb-prefix-without-@claude" silent-skip catcher (REJECTED 2026-06-03).** Surface from PM3 handoff (`/tmp/cdf-architect-gh-monitor-format-resolver-20260531.md`): proposing gh-monitor catch the case where a PM writes `revision: <description>` without the `@claude` prefix, currently silently skipped. Pitched as the "second variant" of the multi-line failure mode we shipped 2026-05-28 (commit `930c609`). **Disposition: rejected as claude-dot-files-level change.** Structurally different from the multi-line fix: that case had unambiguous intent (`@claude` was explicitly present, description just on wrong line — tool rescued INTENT). Missing-prefix case has ambiguous intent — `revision:` is a verb someone might use in normal PR discussion ("the revision: we made yesterday addressed this"). Auto-correcting would create false-positive dispatches that burn Agent SDK credit-pool dollars on workflows the user never requested. The `@claude` prefix is the explicit-consent trigger; removing that requirement crosses a meaningful tooling line. Considered a middle-ground detection-with-hint approach (post a clarifying comment "did you mean to @claude this?") but rejected for now — heuristic false-positives on normal English, accumulates complexity for diminishing returns. **Watch-criteria:** if BOTH (a) recurrence rate of verifiably-intent-was-@claude-but-prefix-missing failures reaches 5+/month, AND (b) PM-side training/discipline fixes (templates, slash command, reminder) prove ineffective, revisit with the detection-with-hint approach (not auto-correction). Honest read: PMs forget formats; the tool should tolerate honest mistakes when intent is clear, stay strict when intent is ambiguous.

- **doc-manager mode invocation patterns.** Whether the PM correctly recognizes triggers from `proactive-doc-management.md` and invokes the right mode. Evaluate after first natural "let's update docs" pass.
