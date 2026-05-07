# Global Instructions

These rules apply to all projects and sessions.

## Communication

- Don't add docstrings, comments, or type annotations to code you didn't change.
- Ask before making changes beyond what was requested.

## Code Style

- Prefer readability over cleverness.
- Use early returns over deeply nested conditionals.
- Don't over-engineer. Solve the current problem, not hypothetical future ones.
- Three similar lines of code is better than a premature abstraction.

## Safety

- Never commit files containing secrets (.env, credentials, tokens, API keys).
- Never hardcode secrets — use environment variables.
- Never force push without explicit approval.
- Never run destructive commands (rm -rf, DROP TABLE, git reset --hard) without confirmation.

## Git

- Use conventional commit format: `type: short description` (e.g., `fix: resolve null check in auth middleware`).
- Don't push unless asked.
- Don't amend commits unless asked — create new commits instead.

## Terminal Commands & Prompts

- When generating shell commands for the user to copy-paste, NEVER use heredoc syntax (`$(cat <<'EOF'...)`, `<<'CONTEXT'`, etc.). Heredocs break on copy-paste every time.
- ALWAYS use a single double-quoted string on one line for workflow script prompts.
- ALWAYS use absolute paths to scripts (the user may be in a different repo).
- Flags FIRST, positionals LAST in workflow invocations: `script.sh --verbose --pr 22 --task-file /tmp/task.md`. Protects the positional payload from being stepped on by line-wrap and keeps options visible at the start.
- For long or multi-paragraph task/context inputs to workflow scripts, use `--task-file <path>` instead of inlining. Write the payload to `/tmp/claude-<name>.md` first, then reference it with `--task-file /tmp/claude-<name>.md`. This bypasses command-line parsing entirely — quotes, newlines, backticks, and special characters all pass through literally.
- **ALL commands given to the user must be a SINGLE LINE.** No exceptions. No multi-line code blocks, no embedded newlines, no `sudo bash -c '...'` blocks spanning lines. If a command can't fit on one line, write it to `/tmp/claude-<descriptive-name>.sh` and give the user `sudo bash /tmp/claude-<descriptive-name>.sh` as the single-line invocation. This applies to EVERYTHING: workflow dispatches, operational commands (kubectl, bootstrap, burn-down), diagnostic commands, git sequences. Terminal whitespace handling corrupts multi-line pastes every time. Chain 2-3 simple related commands with `&&` on one line when script-to-tmp is overkill.

### Workflow invocation template

When dispatching a workflow (revision.sh, revision-major.sh, build-phase.sh, plan-new.sh, plan-revision.sh), produce **one single-line command** in this exact shape:

```
cd <absolute-path-to-target-repo> && <absolute-path-to-workflow-script> [flags] --task-file /tmp/claude-<name>.md
```

Order: `cd` → `&&` → script absolute path → flags (`--verbose`, `--pr <N>`) → `--task-file` LAST so the file path stays visible/editable. The `cd` matters because workflows operate against the current working directory. Default to including `--verbose` unless the user says otherwise (he wants live streaming). Don't wrap the invocation in a bash launcher script — the single-line command IS the deliverable. Write the long task payload to `/tmp/claude-<name>.md` separately with the Write tool first, then present only the invocation line.

## Personal Tooling

Autonomous workflow scripts live at `~/Repos/claude-dot-files/scripts/workflows/`:
- `revision.sh` — small code fixes
- `revision-major.sh` — significant rework with code-reviewer + refactoring-evaluator + standards-auditor review
- `build-phase.sh` — implement from a plan document
- `plan-new.sh` — define a new project from scratch (architect + planner + security-auditor review)
- `plan-revision.sh` — revise existing planning docs (architect + planner + security-auditor + standards-architect review)
- `review-runs.sh` — CPI analysis of workflow JSONL logs
- `sprint-review.sh` — comprehensive end-of-sprint review (security + refactoring + testing + Opus synthesis)

Task-execution workflows (revision, revision-major, build-phase, plan-new, plan-revision, sprint-review) run in isolated git worktrees and produce PRs. All support `--pr <N>` (update existing PR), `--verbose` (live stream), and `--task-file <path>` (read long payload from file). Analysis workflows (review-runs) run against the current repo state, produce reports, and do not create PRs. Always use absolute paths when suggesting invocations. Run `/get-started` at session start for full workflow context, role definitions, and workflow-selection guidance.

### Architectural decisions: standards, not ADRs

This user's convention: architectural decisions are captured as standards documents in `docs/standards/<topic>.md`, not as separate numbered ADR files in `docs/architecture/`. Standards documents serve the same role ADRs do — they document binding decisions about how things should be done, with rationale and alternatives considered.

Do NOT propose creating `docs/architecture/adr-NNN.md` files when adding a `docs/standards/<topic>.md` file accomplishes the same goal. The architecture-decisions skill's methodology still applies (trade-off analysis, rationale, alternatives considered, consequences) — but the artifact is a standards doc, not a numbered ADR. The `docs/architecture/` directory in this user's projects is reserved for high-level system-architecture descriptions and tech-stack overviews, not per-decision artifacts.

### Standards Governance

Standards documents (`docs/standards/`, `docs/architecture/`) are a curated product with human-in-the-loop control. Autonomous workflows and agents may SURFACE standards implications (gaps, drift, deviations, ADR candidates) but must NOT auto-create, auto-modify, or auto-stub standards artifacts. All standards changes flow through the interactive session for human review before merge.

**Planning artifacts (phase docs, roadmap.md, loose-ends entries, sprint docs, epic breakdowns) are explicitly NOT covered by this rule** — they are dispatch-scope and engineers MAY edit them autonomously. When a phase doc and a standard contradict, the engineer SHOULD update the phase doc to remove the contradiction in the dispatch's PR (since the standard is binding) AND surface the standards-side amendment as a candidate for human review. This avoids the "next sprint reads the phase doc, doesn't notice the tension, flips a coin" failure mode.

### CPI Decisions Log

Persistent record of every CPI decision (ship / defer / reject) lives at `~/Repos/claude-dot-files/docs/development/cpi-decisions.md` (or `/opt/skyy-net/claude-dot-files/docs/development/cpi-decisions.md` on the VM). The log preserves context across sessions so deferred findings don't slip away between cycles.

**When CPI cycles produce findings:**
1. Discuss in the interactive session, decide ship/defer/reject for each finding
2. SHIPPED items get implemented + committed
3. DEFERRED items get appended to `cpi-decisions.md` with explicit watch-criteria (e.g., "ship on second occurrence")
4. REJECTED items get appended with reasoning so future reviewers don't re-litigate

**Before a new CPI cycle:** scan the DEFERRED sections. New findings that match prior watch-criteria become Tier-1 ship candidates with confirmed evidence. New findings unrelated to prior deferrals are evaluated fresh.

**Append-only:** entries don't get deleted. When a previously-deferred item finally ships, the original deferral entry gets amended with "→ SHIPPED at <commit>" rather than removed. This preserves the calibration history (how often did we correctly defer noise vs incorrectly defer real patterns).

The `review-runs.sh` and `sprint-review.sh` workflows automatically cross-reference the log when generating new reports — findings that match prior deferrals are flagged as recurrences with the original context.

## Dependencies & Tools

- Check if a tool/package is already in the project before adding a new one.
- Prefer standard library solutions over adding dependencies for trivial tasks.