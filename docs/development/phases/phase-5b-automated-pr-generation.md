# Phase 5b: Automated PR Generation

## Status
Not started

## Overview
Extend the manual CPI review workflow (`review-runs.sh`) to automatically generate PRs with proposed improvements. Instead of producing only a markdown report that a human must manually translate into code changes, the workflow produces a PR with concrete diffs — still gated by human review and approval.

## Goals
- Enable `review-runs.sh` to optionally create a PR with proposed changes (not just a markdown report)
- Define a clear, reviewable PR template so humans can assess CPI-driven changes confidently
- Validate the end-to-end flow on real findings before integrating with scheduled operation (Phase 5c)

## Dependencies
- **Phase 5a complete** — `review-runs.sh` exists and produces structured markdown reports. First CPI cycle complete (PR #14). `workflow-analyst` agent and `workflow-analysis` skill exist. The implementation phase will reuse the analysis prompt from `review-runs.sh` and the structured output format from the `workflow-analysis` skill.
- **Phase 4a complete** — Headless mode, worktree isolation, and PR creation flow validated.
- **Phase 4c complete** — Shared workflow lib (`lib/run-claude.sh`) and all core workflow scripts operational.
- **`gh` CLI installed and authenticated** — Required for PR creation (already validated in Phase 4a).
- **PR template design (epic 2) must be defined before implementing `--pr` flag (epic 1)** — The script needs to know the PR body format to generate it. Design the template first, then implement.

## Context: Phase 5a Results

Phase 5a proved the CPI loop works manually:
- `review-runs.sh` scans `.claude/logs/` JSONL files, produces reports at `docs/development/reviews/review-YYYY-MM-DD.md`
- First formal analysis: 12 logs, 14 findings (5 high, 5 medium, 4 low confidence), 100% workflow success rate
- First cycle applied 3 high-confidence findings (PR #14): file-size read guidance, rate limit backoff, test fixture path guidance
- Current gap: translating report findings into code changes is fully manual

## Tasks

### Extend review-runs.sh with PR generation mode

- [ ] **Design two-phase execution model** — The `--pr` flag adds a second `run_claude` call after the existing analysis call. Phase 1 (analysis): runs as today, produces the review report markdown file. Phase 2 (implementation): a separate `run_claude` call in an isolated worktree, with the report file path injected into the prompt. Two calls (not one extended session) to avoid context contamination between analysis and implementation. Implementation phase uses `MAX_TURNS=75` (medium workflow, matching `revision-major.sh`). This follows the multi-stage pattern established by `build-phase.sh`.
- [ ] **Add `--pr` flag to `review-runs.sh`** — When passed, the workflow runs the analysis phase first (unchanged), then checks whether a PR should be created (sufficient logs, high-confidence findings exist). If yes, launches the implementation phase. Without `--pr`, behavior is unchanged (backward compatible).
- [ ] **Implement worktree isolation for PR mode** — When `--pr` is used, run the implementation phase in an isolated worktree (matching existing workflow patterns from revision.sh and revision-major.sh). Changes are committed and pushed from the worktree.
- [ ] **Scope changes to workflow artifacts only** — PR mode should only modify: workflow scripts (`scripts/workflows/`), agents (`config/agents/`), skills (`config/skills/`), and standards docs (`docs/standards/`). It must NOT modify: application code, `settings.json`, hook scripts (`config/hooks/`), rules (`config/rules/`), slash commands (`config/commands/`), or `CLAUDE.md` files. Rules and commands affect global Claude behavior and require higher scrutiny than workflow artifacts. Enforcement: the implementation prompt must include the allowlist, and a post-implementation `git diff --name-only` check in the bash script should validate that only allowed paths were modified before creating the PR.
- [ ] **Register `cpi:` as a conventional commit type** — Add `cpi` to the project's commit type conventions before the first CPI PR is created, so the type is standard from the start.
- [ ] **Enforce confidence threshold** — Only implement findings at or above high confidence. Medium and low confidence findings are listed in the PR body as "considered but not applied" with their confidence scores and reasoning.
- [ ] **Include the source report** — The generated markdown report (`docs/development/reviews/review-YYYY-MM-DD.md`) must be committed alongside the code changes so the PR contains both the analysis and the implementation.

### Design the PR template

- [ ] **Define PR title format** — `cpi: <short description of improvements>` (follows conventional commit style, uses `cpi` type to distinguish from manual changes)
- [ ] **Define PR body structure** — Each PR includes:
  - **Analysis window**: date range and number of logs analyzed
  - **Patterns found**: summary table with pattern name, confidence score, and category
  - **Changes made**: list of files modified with explicit mapping from finding to code change (which finding motivated which diff)
  - **Findings not applied**: medium/low confidence findings listed with scores and reasoning for deferral
  - **Recommended testing**: specific steps to verify the changes don't regress existing workflows
  - **Before/after context**: for each change, what the old behavior was and what the new behavior is
  - **Source report link**: path to the committed review report
- [ ] **Add Phase 5 critical rules checklist to PR body** — Include a checklist confirming compliance with the 7 critical rules (human review required, audit trail present, changes reversible, confidence scores included, based on multiple observations, cost-aware)

### Test the PR creation flow

- [ ] **Dry run on existing findings** — Run `review-runs.sh --pr` against current logs. Verify the PR is created, the template is followed, and the changes are limited to allowed file scopes.
- [ ] **Review PR quality** — Manually assess: are the proposed changes sensible? Is the rationale clear? Would you merge this without the AI explaining it further? If not, iterate on the prompt and template.
- [ ] **Test with insufficient data** — Run against fewer than 3 logs. Verify the workflow declines to create a PR and explains why (sample size too small per critical rule #6).
- [ ] **Test with no high-confidence findings** — Run against logs that produce only medium/low confidence findings. Verify no PR is created but findings are still reported in the markdown output.
- [ ] **Validate rollback** — Merge a test PR, then revert it. Confirm the revert is clean and no state is left behind (critical rule #4: all changes must be reversible).

## Success Criteria
- [ ] `review-runs.sh --pr` creates a well-formed PR from real log analysis with no manual intervention beyond the review/merge step
- [ ] PR body follows the defined template and includes all required sections (analysis window, patterns, changes, deferred findings, testing steps, critical rules checklist)
- [ ] Only high-confidence findings are implemented; medium/low are documented but not applied
- [ ] Changes are scoped to workflow artifacts only (scripts, agents, skills, standards) — never application code or security-sensitive config
- [ ] The workflow declines to create a PR when sample size is insufficient (fewer than 3 logs)
- [ ] The workflow declines to create a PR when no high-confidence findings exist
- [ ] A merged PR can be cleanly reverted
- [ ] Backward compatible: `review-runs.sh` without `--pr` still produces only a markdown report

## Risks & Mitigations
- **Risk:** Generated changes introduce regressions in workflow scripts
  - **Mitigation:** PR includes specific testing steps. Human must verify before merging. Changes are scoped to non-security artifacts only. All changes are reversible (critical rule #4).
- **Risk:** Low-quality or nonsensical changes erode trust in the CPI system
  - **Mitigation:** Confidence threshold enforced (high only). PR template requires before/after context so reviewer can assess quality at a glance. If quality is consistently low, pause PR generation and return to report-only mode.
- **Risk:** Prompt injection via log content — malicious or malformed log entries could influence the analysis
  - **Mitigation:** Logs are generated by Claude Code itself in controlled workflows. External input surface is minimal. Scope restrictions prevent the workflow from modifying sensitive files even if analysis is corrupted.
- **Risk:** Token cost of the implementation phase exceeds the value of the improvements
  - **Mitigation:** Critical rule #7 (cost awareness). Track token cost per CPI PR. If cost consistently exceeds savings, adjust confidence threshold upward or reduce analysis window.
- **Risk:** Drift between PR template and actual output as the workflow evolves
  - **Mitigation:** PR template defined in the workflow prompt, not in a separate file. Single source of truth. Template checklist enforces compliance.
- **Risk:** Implementation phase misinterprets analysis findings — the report says "add retry logic" but the implementation adds it incorrectly or in the wrong place
  - **Mitigation:** PR body includes an explicit mapping from each finding to the specific code change that addresses it. Reviewer can verify alignment between what was recommended and what was implemented. Before/after context makes mismatches visible.

## Notes
- This phase is intentionally narrow: extend the existing workflow, not build a new one. `review-runs.sh` already does the hard part (log analysis). Phase 5b adds the "now do something about it" step.
- Phase 5c (Scheduled Operation) depends on this phase being stable. Don't rush to scheduling — get the PR quality right first.
- The 7 critical rules from Phase 5 apply to all work in this phase. They are non-negotiable. See `docs/development/roadmap.md` Phase 5 "Critical Rules" section.
- **Deferred: workflow-scripts standard update.** Phase 5b introduces a new pattern (conditional worktree isolation via `--pr` flag). Once implementation proves the pattern works, update `docs/standards/workflow-scripts.md` to document it.
- **Deferred: deduplication against prior CPI PRs.** Becomes relevant in Phase 5c (scheduled operation). For manual Phase 5b usage, the human operator naturally avoids duplicate proposals.
