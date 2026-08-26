---
id: C-wb1xc1xs
title: A reader for the run-log `convergence` events, so the LIVE path has a denominator and not only the `gh` archive
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**Phase 5 emits a `{"type": "convergence"}` event on every `review-pr` dispatch and nothing reads it.** Its § Measurement figures all come from `replay_convergence_predicate.py` over the GitHub `pr_review:` block archive — a corpus that accrued at the same rate before this phase shipped, so the emission contributes nothing to the gate's denominator. The run-log events are a SECOND corpus carrying facts the replay structurally cannot produce: the `pass_not_evaluable` and `history_unreadable` rates (the replay hardcodes `pass_evaluable=True`, because no archived block has a typed record), and the typed term the live predicate actually reads. **Proposal, not defect** — nothing behaves wrongly; the phase's stated conditions are answerable from the archive today, and this would answer a different and better question. The shape already exists: `replay_completion_predicate.py` reads `.claude/logs/*.jsonl` the same way, and both event types carry `run_id` so `convergence` joins to `parent_route`. **Not filed as an issue** — it is capability that does not exist, and per `finding-routing.md` § 4 that makes it a candidate whatever its done-state looks like. **Lens verdicts (`finding-routing.md` §5 gate 4).** `/decide`: BUILD-WHEN-NEEDED — the five-whys bottoms out at *the emission was added a phase before its reader*, which was correct (a metric over a field nothing writes is a plan), so the remedy is the reader and the trigger is the first question only it can answer. `/best-practices`: instrument-then-read is the normal order and a write-only observable is a known smell only when it stays that way across releases; the guard is that the events accrue in the meantime and are joinable, which they are.

**Source:** PR #75

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
