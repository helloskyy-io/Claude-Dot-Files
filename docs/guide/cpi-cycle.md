# Continuous Process Improvement (CPI) Cycle

This is the operating manual for the CPI cycle — the recurring review-decide-log loop that improves the autonomous workflows over time. The cycle uses `review-runs.sh` (or `sprint-review.sh`) to surface findings from real workflow runs, an interactive architecture session to decide each finding's fate, and `cpi-decisions.md` as the persistent log that carries context across cycles.

## What CPI is, and why we run it

Autonomous workflows produce JSONL logs of every run — every tool call, every error, every prompt. Patterns hide in those logs: inefficiencies, repeated failures, manual corrections the user keeps making, missed opportunities. Reading them by hand doesn't scale. CPI is the discipline of having an AI analyst (the `workflow-analyst` agent invoked by `review-runs.sh`) batch-analyze recent logs, surface findings with confidence scores, and bring them to the architecture session for human decision.

The output is incremental, evidence-based improvements to workflow scripts, agents, skills, rules, and docs — driven by what the logs actually show, not by speculation.

## Cadence

- **Weekly-ish** is the natural rhythm. Every 5-10 days of accumulated workflow runs is enough to surface real patterns; less and you're looking at noise.
- **When warranted, not on a strict schedule.** If the last cycle just shipped fixes, give the new prompts time to produce post-fix logs before reviewing again. Running CPI on the same week's logs twice rarely surfaces new signal.
- **Sprint-review is its own cycle.** `sprint-review.sh` runs at end-of-sprint and is comprehensive (security + refactoring + tests). CPI / `review-runs` runs more frequently and is meta-review of the workflow tooling itself. They feed the same decisions log but answer different questions.

## Prerequisites

- The repo whose logs you want to analyze must have run autonomous workflows recently — `review-runs.sh` operates on `<repo>/.claude/logs/*.jsonl`.
- You run `review-runs.sh` **from inside the repo whose logs you want to analyze** (the repo with the workflow runs in it, e.g., a project repo where `build-phase.sh` or `revision.sh` ran).
- The report itself is always written to `claude-dot-files/docs/development/reviews/` regardless of which repo's logs were analyzed — single searchable location across all analyzed repos.
- The CPI decisions log lives at `claude-dot-files/docs/development/cpi-decisions.md`.

## The cycle in steps

### Step 1 — Pre-cycle: scan deferred items

Before running a new cycle, read the **DEFERRED — watch-list** sections of `cpi-decisions.md`. Each deferred item has explicit watch-criteria — what would trigger reconsideration on recurrence. This primes you to recognize Tier-1 ship candidates (findings where prior-cycle deferral + this-cycle recurrence = sufficient evidence to ship).

`review-runs.sh` does this automatically — its prompt instructs the analyst to read `cpi-decisions.md` and flag recurrences with the original deferral context. But the human side of the loop benefits from the same priming.

### Step 2 — Run `review-runs.sh`

```bash
cd /path/to/repo-with-logs
~/Repos/claude-dot-files/scripts/workflows/review-runs.sh --days 7 --verbose
```

Flags:
- `--days <N>` — analyze logs from the last N days (default: 7)
- `--last <N>` — analyze the N most recent logs (mutually exclusive with `--days`)
- `--verbose` — stream formatted output live

The workflow scans `<repo>/.claude/logs/*.jsonl`, invokes Claude with the workflow-analysis methodology, reads the CPI decisions log, and writes a structured report to `claude-dot-files/docs/development/reviews/review-<repo-name>-<date>.md`.

If multiple repos have logs (a workstation often does), run the workflow once per repo. Each report is filename-tagged with the source repo so they don't collide.

### Step 3 — Read the report together

The report is the input to the architecture session. Open it alongside `cpi-decisions.md` and walk through findings in this order:

1. **Recurrences from CPI Decisions Log** — findings flagged as matching a prior watch-criteria. These have the strongest evidence (prior deferral + new recurrence). Default to ship unless reasoning has changed.
2. **High-confidence findings** — pattern in 3+ runs, clear cause-effect. Default to ship if actionable; defer with watch-criteria only if scope is too large for this cycle.
3. **Medium-confidence findings** — pattern in 2 runs, or strong single observation. Default to defer with explicit watch-criteria. Engineering-quality rule applies: don't build ahead of evidence.
4. **Low-confidence findings** — single observations. Note for next cycle; don't act unless asymmetric risk class (silent data loss, security, correctness regression) is at stake.

### Step 4 — Decide each finding

Every finding ends in one of three dispositions:

- **SHIPPED** — implement and commit. Goes in the SHIPPED section of the cycle's log entry with the commit hash.
- **DEFERRED** — keep on the watch-list. Goes in the DEFERRED section with explicit watch-criteria — what specific signal would flip this to ship.
- **REJECTED** — not actually a problem in our context (analyst misunderstood, edge case doesn't apply, alternative pattern is preferred). Goes in the REJECTED section with reasoning so future cycles don't re-litigate.

**"Recommend we move on" is not a disposition.** Per the engineering-quality rule, every finding must reach an explicit decision.

### Step 5 — Apply decisions

For SHIPPED items:
- Implement the change in the appropriate file (workflow script, agent, skill, rule, docs).
- Commit. Reference the cycle date in the commit message body if it helps.
- Note the commit hash in the log entry.

For DEFERRED items:
- Append to `cpi-decisions.md` under that cycle's DEFERRED section.
- Include: evidence, decision reasoning, watch-criteria.
- Watch-criteria should be specific — "ship on second occurrence in any repo," not "ship if it gets worse."

For REJECTED items:
- Append with reasoning.
- Keeps future analysts from re-surfacing the same finding without new evidence.

### Step 6 — Log the cycle

Add a cycle entry to `cpi-decisions.md` with:

- Date heading: `## YYYY-MM-DD — review-runs cycle (<repo names>)` or `## YYYY-MM-DD — sprint-review run #N` or `## YYYY-MM-DD — ad-hoc reflection`
- One-line context (what triggered the cycle, sample size)
- `### SHIPPED`, `### DEFERRED — watch-list`, `### REJECTED` subsections as applicable
- Each finding gets evidence + decision + reasoning + (for DEFERRED) watch-criteria

The log is **append-only**. Entries don't get deleted. When a previously-deferred item ships, amend the original deferral entry with `→ SHIPPED at <commit>` rather than removing it. This preserves the calibration history (how often we correctly defer noise vs. how often we incorrectly defer real patterns).

## Decision discipline

### Engineering-quality rule applies to us too

Don't build ahead of evidence. A single-occurrence finding is tempting to ship because it's often real, but the cost of shipping false positives is prompt bloat — every wrong rule we add gets loaded into every workflow's context forever. Defer-with-watch-criteria is the default for single-occurrence findings.

The exception: **asymmetric risk classes**. Silent data loss, security incidents, correctness regressions in production-shaped patterns — these get shipped on the first occurrence because the cost of one occurrence is high enough to outweigh the prompt-bloat risk of a wrong rule. Note the asymmetric reasoning explicitly when shipping a single-occurrence finding.

### What makes a good watch-criteria

A watch-criteria is the trigger for flipping deferred → shipped. The criteria should be:

- **Specific** — "ship on second occurrence in any repo with the `find -print0` pattern," not "ship if it gets worse."
- **Observable** — something a future cycle's report will show or not show.
- **Time-bounded if relevant** — "if no recurrence in 4 cycles, downgrade to REJECTED" prevents indefinite watch-list growth.

### What counts as a finding

A finding is a pattern visible in the logs that suggests a workflow improvement. Not every error event is a finding — some are noise, some are user-induced edge cases, some are already-fixed and the logs are pre-fix. The analyst's job is to filter; the architecture session's job is to confirm.

## How `cpi-decisions.md` works

The log is the long-term memory of CPI. It serves four functions:

1. **Cross-cycle persistence** — deferred items don't slip away between sessions. Every cycle starts by scanning the watch-list.
2. **Recurrence detection** — `review-runs.sh` automatically flags new findings that match prior watch-criteria, raising their priority.
3. **Calibration history** — append-only structure shows how often we defer correctly vs. incorrectly. Useful for tuning the discipline over time.
4. **Re-litigation prevention** — REJECTED entries with reasoning prevent the same finding from coming back next cycle without new evidence.

The log lives at `claude-dot-files/docs/development/cpi-decisions.md`. Both `review-runs.sh` and `sprint-review.sh` cross-reference it in their prompts.

## Relationship to `sprint-review.sh`

| Aspect | `review-runs.sh` (CPI) | `sprint-review.sh` |
|---|---|---|
| Subject | Workflow tooling logs | Project code, tests, security |
| Cadence | Weekly-ish | End of sprint |
| Output | Findings about HOW we work | Findings about WHAT we built |
| Scope | Workflow scripts, agents, skills, rules | Project source code, tests |
| What lands in `cpi-decisions.md` | All findings — workflow tooling IS the subject | **ONLY meta-findings** about how the workflow performed — NOT the project-code findings |
| Where project findings go | n/a (subject is tooling) | Project-side: loose-ends, phase docs, sprint review report |
| Both apply | Engineering-quality discipline | Engineering-quality discipline |

They are different cycles asking different questions. CPI asks "is the workflow tooling getting better?" Sprint-review asks "is the project code getting better?" Both produce findings, but only ONE category lands in `cpi-decisions.md`: findings about claude-dot-files tooling (workflow scripts, agents, skills, rules). Project-code findings from sprint-review stay **project-side** — in the project's loose-ends tracking, phase docs, or sprint-review report. They follow the same ship/defer/reject discipline regardless of destination.

Don't conflate the cadences either — running sprint-review weekly burns tokens; running CPI per-sprint misses the weekly signal.

### What belongs in `cpi-decisions.md` (and what doesn't)

The log is for **claude-dot-files-level decisions ONLY**.

**Belongs:**
- Decisions about workflow scripts (`revision.sh`, `build-phase.sh`, etc.)
- Decisions about agents (`code-reviewer`, `standards-architect`, etc.)
- Decisions about skills (`standards-enforcement`, `project-organization`, etc.)
- Decisions about rules (`engineering-quality.md`, etc.)
- CPI methodology refinements (the cycle itself)
- Meta-findings from `sprint-review` or `review-runs` about how the workflow performed

**Does NOT belong:**
- Project-code tech debt (belongs in project's loose-ends)
- Project deployment workarounds and tactical bandaids (belongs in project's phase docs or loose-ends)
- Project-specific standards amendments (belongs in project's `docs/standards/`)
- Customer/service-specific decisions (belongs in project's tracking)
- Sprint or epic narrative (belongs in project's planning docs)
- Project-side retrospectives or post-mortems (belongs in project's sprint/phase artifacts)

**Useful test:** would another claude-dot-files-using project benefit from this decision being recorded? If yes, it's tooling-level. If no, it's project-level. PM handoffs that route project-level decisions here should be evaluated against this test and redirected when appropriate.

## Common pitfalls

- **Running CPI on too few logs** — fewer than ~5 runs and patterns are indistinguishable from coincidence. Wait until enough has accumulated.
- **Re-running CPI on the same week** — without new logs, the analyst can only re-confirm prior findings. Wait for new runs before the next cycle.
- **Shipping every finding** — leads to prompt bloat. Use defer-with-watch-criteria as the default; ship on recurrence.
- **Deferring without watch-criteria** — silent dismissal disguised as discipline. Every deferral must have a specific recurrence trigger.
- **Forgetting to log REJECTED items** — they come back next cycle without context, wasting review time.
- **Treating findings as binary** — "this is a problem" / "this isn't a problem." The richer question is "is the evidence sufficient YET?" That's why deferral is a first-class option.

## Cross-references

- `scripts/workflows/review-runs.sh` — the analysis script
- `scripts/workflows/sprint-review.sh` — the comprehensive end-of-sprint script
- `docs/development/cpi-decisions.md` — the persistent log
- `docs/development/reviews/` — generated reports
- `config/agents/workflow-analyst.md` — the analyst agent invoked by `review-runs.sh`
- `config/skills/workflow-analysis.md` — the methodology the analyst follows
- `config/rules/engineering-quality.md` — the discipline that governs ship/defer/reject decisions
