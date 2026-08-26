---
id: C-abz9426g
title: The 25-paper research pool serves three consumers under one directory, so every cycle re-derives its size as a defect
status: open
count: 1
filed: 2026-08-06
filed_by: review-pr
component: research-workflow
---

Surfaced by the cycle-4 research run on PR #33 (branch `research/product-pool-cycle-4`, reviewed at `79f39e757be939dd6f760d53a2cef1c8f1c6d203`). Filed by `review-pr` under Research Standard §7 — the split is a **structural change to a documented stable consumption surface**, which §7 and the research write-boundary both put outside a research run's authority. It is a planning/operator action with no existing home.

## Consequence

`docs/standards/architecture/research/` now holds **25 papers serving three distinct consumers** under one directory and one `synthesis.md`. Two costs are already being paid:

1. **Every cycle re-derives the pool's size as a defect.** Cycle 3 recorded the 21-topic overrun as *"a finding about the rubric"* needing an upstream amendment to the sizing bands. Cycle 4 re-examined it and found the opposite — §2 already prescribes the remedy and the amendment was not owed. That is two cycles of analyst effort spent on a question the standard answers, and it will recur every cycle until the split happens.
2. **One `synthesis.md` serves three audiences.** It is the documented read-this-instead-of-the-pool surface, and a reader wanting the competitive read pages through the thesis and the plan to find it.

## What the standard already says

`docs/standards/research/research_standard.md` §2:

> **An assessment materially above the Large band is a scoping signal, not a band failure (binding).** The bands are **per component**, and §6 binds topics to destinations. A component whose topic list runs well past 8–10 usually has **more than one destination** — *a plan, plus a thesis, plus a competitive read are three consumers, not one* — and the correct response is to check whether it is one component before widening the band.

The standard's own worked example describes this pool exactly. The rule needs **applying**, not amending.

## Evidence

- Reviewed at PR #33 SHA `79f39e757be939dd6f760d53a2cef1c8f1c6d203`.
- Cycle-4 sizing assessment: `docs/standards/architecture/research/topics.md` — **25 topics, Tier Large**, splitting cleanly into **thesis (9) / plan (12) / competitive read (4)**, each at or near a normal band.
- Also stated in `docs/standards/architecture/research/synthesis.md` § *Homeless findings*, bullet 3.
- Constraint to respect: `docs/standards/architecture/research/README.md` documents `synthesis.md` as a stable consumption surface at a fixed path — a split changes that path for existing consumers.

## Proposed next action

**Operator ruling on whether to split, then a planning run executes it.** The split the sizing assessment proposes:

| Sub-pool | Papers | Backs |
|---|---|---|
| thesis | 9 | `problem-statement.md` — the differentiators and the novelty claim |
| plan | 12 | `Phase: Temporal Integration` and siblings — the build's validating evidence |
| competitive read | 4 | `roadmap.md` § *Tools to Evaluate* — the comparator set |

Two things to decide alongside it, because a split that ignores them costs more than it saves:

- **Does each sub-pool get its own `synthesis.md`, or does one stay canonical?** Three syntheses means three revalidation cadences and three standup inputs; one canonical synthesis means the split is filesystem-only.
- **What happens to the ~13 cross-cutting references** between papers that would land in different sub-pools (e.g. `edge_identity_trust.md` ↔ `temporal.md`). Relative links break on a move.

Note this is also **partly an altitude question**: §1 puts ~98% of research at `development/<path>/<component>/research/`, and the *plan* sub-pool (12 papers) arguably belongs there rather than under `standards/architecture/`. Worth ruling on in the same pass rather than splitting twice.



---

*Migrated from `Claude-Dot-Files#38` on 2026-08-26. Re-triaged from Issue to Candidate: the remedy is capability that does not exist, which §1.1 routes to a proposal.*
