# Phase: Continuous Process Improvement

**Status:** 🟡 IN PROGRESS — the loop runs; scheduling and the reflection channel are not yet closed
**Roadmap entry:** [`../roadmap.md`](../roadmap.md)
**Depends on:** [`autonomous-execution.md`](autonomous-execution.md) — there is nothing to analyse until workflows are producing logs

## Goal

Make the system improve its own tooling from evidence it generates itself.

The distinguishing property, and the reason this is a phase rather than a habit: **no human gathers the data.** A workflow run leaves a JSONL log and posts a reflection about its own work. Both are machine-produced records of what actually happened, and both are read systematically rather than when someone remembers to look.

## Completion criteria

- [x] Findings come from **the system's own artifacts**, not from recollection
- [x] Every finding reaches an explicit ruling — ship, defer or reject
- [x] Deferrals carry a **watch-criterion**: what would bring this back
- [x] Rejections are recorded so they are not re-litigated
- [ ] The loop runs on a schedule rather than when someone remembers
- [ ] The self-disclosure channel is mined as systematically as the log channel

## The two evidence sources

**Run logs — `review-runs.sh`.** Every dispatch writes a JSONL log. The workflow analyses a window of them across repos and produces a report: patterns, inefficiencies, recurrence against prior decisions. This is the mechanical channel — turn counts, redundant reads, cost, stage adherence.

**Self-disclosure — the Post-Run Reflection.** Every workflow ends by posting a Decision Log and reflection to its PR: friction hit, decisions where a reasonable engineer could have chosen differently, and explicit *tooling-level suggestions*. This is the place a run **tells on itself**, and it carries what a log cannot — intent, and what the run found hard.

The two are complementary and neither substitutes for the other. A log shows that a file was read seventeen times; only the reflection says the guidance was ambiguous.

## Work

- [x] **`review-runs.sh`** — reads `.claude/logs/`, produces an improvement report
- [x] **`workflow-analyst` agent** and the `workflow-analysis` skill
- [x] **Cross-repo reports** — output centralised here with source-repo metadata, rather than scattered per-repo
- [x] **`cpi-decisions.md`** — append-only ship / defer / reject with watch-criteria
- [x] **Reflection posted by every workflow** — `DECISION_LOG_AND_REFLECTION`, shared across the fleet
- [x] **`review-pr` mines reflections** — the disposition engine's primary hunting ground is the run's own words
- [ ] **Scheduled operation** — currently run by hand. Its future is `Temporal Crons`; the workflow itself does not move
- [ ] **Close the reflection loop** — tooling suggestions are *written* by every run and *read* opportunistically. Nothing sweeps them systematically the way `review-runs.sh` sweeps logs

## Decisions

**The ruling is always a human's.** Findings are surfaced; ship / defer / reject is decided in the interactive session. This is binding via [`standards-governance.md`](../../../config/rules/standards-governance.md), and it is why "automated skill capture" and auto-opened PRs of workflow changes were both rejected rather than scheduled. **The system observes itself and proposes; it does not modify itself.**

**Append-only, including the rejections.** Deferrals carry an explicit watch-criterion — *"ship on second occurrence"* — so a re-surfaced finding arrives with its own history rather than being argued from scratch. Rejections are kept for the same reason in reverse.

**The ratio is the real signal.** Deferred-then-resurfaced versus deferred-and-never-recurred measures calibration. High recurrence means we are shipping too little; high never-recurred means the deferrals were correctly reading noise.

**Report centrally, not per-repo.** Reports carry source-repo metadata and live here. Per-repo scatter made cross-repo patterns invisible, which is where the most valuable findings are.

## Superseded and forbidden

**Graduation evaluation — answered.** Whether to move beyond bash was a live question here; it is settled. Durable execution, adopted for durability and resumability, **not** to gain composition. See [Temporal Integration](../roadmap.md).

**Advanced self-improvement — partly forbidden as originally written.** "Automated skill capture" and any auto-modify-standards item conflicts directly with `standards-governance.md`, which postdates it and wins. The measurement items in it — effectiveness tracking, regression detection, cross-workflow analysis — remain valid and interesting, but must be restated as *surface-for-review* rather than *auto-apply* before they are scheduled.

**Automated PR generation from findings — needs restating.** Same conflict. Not automatically dead, since a PR is a proposal rather than a merge, but the version where a workflow drafts and a human still rules is a different item from the one written in April.

## Where this landed

- [`../../guide/cpi-cycle.md`](../../guide/cpi-cycle.md) — the operating manual for the cycle
- [`../cpi-decisions.md`](../cpi-decisions.md) — the log itself
- [`../reviews/`](../reviews/) — generated reports
