---
id: C-obarkm4s
title: **No phase in the temporal-integration plan rules §A4's open question — whether a prompt is an INPUT or a RESOURCE — so a replayed workflow loads TODAY'S prompt text rather than the one that ran, and the decision has no owner**
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: temporal-integration
---

**The addendum's four sections are all `📋 OPEN`, and this plan closes two of them.** [Phase 4](../../docs/development/temporal-integration/phase4_the_claude_cli_activity.md) closes §A1, [Phase 1](../../docs/development/temporal-integration/phase1_the_starter_control_plane.md) closes §A3, §A2's doctrine is applied at Phase 4 — and §A4 is never named anywhere in the component. Its open bullet states the fork itself: *"If a prompt is versioned with the code, a Temporal replay of an old execution loads today's prompt, not the one that ran. If it is an input, it sits on the workflow's payload and hits the limits §A1 already flags."* **The plan already catches the exactly-analogous defect for a random value and not for the prompt** — Phase 2 rules `review_pr_workflow.py:171`'s `uuid.uuid4().hex` because *"a random value does not replay"*, and nothing asks the same question of the prompt text, which is the substance of the work rather than an incidental beside it. Population measured on this branch: sixty-four `.md` prompt files under `scripts/workflows/temporal/`. [Phase 6](../../docs/development/temporal-integration/phase6_the_rest_of_the_fleet.md) applies `temporal_standard.md` §10.1 to prompt fragments, but that rules WHERE a fragment lives, not whether it is an input — the two questions are independent and only one is answered. **Remedy:** rule input-versus-resource at the phase that first makes a parent a workflow, or give it a phase of its own; which of those is `plan-feature`'s call and not this run's. **Filed as a proposal rather than a defect** because nothing built behaves wrongly today — nothing replays yet — so it is a decision that would be ADDED, not one that is misbehaving

**Source:** PR #130 (`plan-verify`, cold sizing pass)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
