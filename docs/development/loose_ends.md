# Loose Ends

Deferred items from architectural reviews and CPI cycles. Each entry includes context and recommended trigger for revisiting.

## How to use this doc

Add entries when deferring work that:
- Is genuinely out-of-scope for current focus
- Won't be addressed in the current session
- Is large enough to warrant separate context-rebuild later

For per-cycle CPI decisions (ship/defer/reject with watch-criteria), use `docs/development/cpi-decisions.md`. This file is for broader architectural deferrals identified outside of CPI cycles.

---

## Enterprise Quality Hardening — Architect Findings (2026-05-28)

Architectural review identified these gaps for moving from "above the bar for personal dotfiles" to "professional team-level tooling." Categorized by effort + priority.

### Infrastructure: testing + CI

- **Tests for the system itself.** Zero `tests/` directory. `block-dangerous.sh` has ~40 regex patterns with no fixtures, no attack corpus, no negative tests. `install.sh` untested. **Approach when triggered:** add `tests/` with `bats-core` for `block-dangerous.sh` (attack corpus + negative corpus) and `install.sh` (symlink creation, backup behavior). ~1 day initial setup. **Trigger:** before adding new hook patterns, or when block-dangerous.sh complexity grows.

- **CI on this repo.** No `.github/workflows/`. PRs merge without `shellcheck`, `bash -n`, JSON/YAML lint, hook-pattern regression tests, markdown link-check. **Approach when triggered:** `.github/workflows/ci.yml` with the above checks. **Trigger:** after testing infrastructure exists.

- **Safety hook threat model documentation.** `block-dangerous.sh` doesn't enumerate bypass classes considered (env-var smuggling, encoded shell, `bash -c "$(printf ...)"`, `eval`, here-strings, alias rebinding). **Approach when triggered:** write `docs/architecture/threat-model.md` listing attack classes the hook addresses and explicitly out-of-scope ones. **Trigger:** anyone other than operator starts using these workflows, OR an autonomous LLM demonstrates evidence of bypass attempts in logs.

### Operations: drift + recovery + visibility

- **Multi-machine drift detection.** No `install.sh --verify`, no per-machine state file (last-installed-commit), no way to ask "is laptop running stale config?" **Approach when triggered:** `install.sh --verify` mode + `~/.claude/.install-state` recording commit SHA + timestamp. **Trigger:** when adding a third machine, or when drift causes a real issue.

- **Disaster recovery story.** `install.sh` backs up but no documented rollback, no `uninstall.sh`. VM + workstation are backed up; laptop is not. **Approach when triggered:** `uninstall.sh` script + rollback procedure in `docs/guide/`. **Trigger:** before deploying to a machine without backup, OR if a bad install ever requires manual recovery.

- **Cost rollup tooling.** JSONL logs capture `total_cost_usd` per run but no aggregator. Operator currently watches metrics daily by hand. **Approach when triggered:** `scripts/helpers/cost-report.sh` walking `.claude/logs/*.jsonl` and rolling up by day/workflow/project. **Trigger:** if June 15 billing change makes manual tracking insufficient, OR operator wants budget alerts.

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

- **Quality-control agent severity calibration.** Whether the "over-surfacing is desired" bias produces useful signal or noise. Evaluate after first real workflow dispatch with quality-control in place.

- **doc-manager mode invocation patterns.** Whether the PM correctly recognizes triggers from `proactive-doc-management.md` and invokes the right mode. Evaluate after first natural "let's update docs" pass.
