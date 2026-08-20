# Phase 9 — `review-runs`, written in the Python tree

**Status: ⬜ NOT STARTED.** Listed in [rollout order](roadmap.md) beside [Phases 2](phase2_durable_dispatch_identity.md) and [3](phase3_the_retry_boundary.md) — the phases that need no Temporal server. **Its number is 9 because 9 was the next free identifier**, not because it is built ninth; the roadmap states that numbers are identity and not order, and this phase is the first entry that exercises the rule.

**This phase exists because a downstream consumer was gated on something it does not need.** [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) waits on the *Python port of `review-runs`* and says so twice in its own documents — *"This is the only gate; the Temporal server is not one"* — and PMP split that phase out of its own Phase 8 specifically so its only consumer would not sit behind a server nobody has stood up. Carrying the port inside [Phase 6](phase6_the_rest_of_the_fleet.md) put it back there: Phase 6 is gated on [Phase 5](phase5_the_first_dispatch.md), which is gated on [Phase 1](phase1_the_starter_control_plane.md), which *is* the server. **Splitting the write out is what makes the roadmap's own "not waiting on the server" cell true.**

**Two halves, and only one of them is here.** *Written in Python* is this phase. *Orchestrated by Temporal* stays in [Phase 6](phase6_the_rest_of_the_fleet.md) requirement 2, where every other workflow's orchestration lives. PMP Phase 6's gate resolves to **this phase, not to that requirement** — a batch read over the journal needs a program, not a scheduler.

---

## Requirements for completion

1. **`review-runs` exists in the Python tree** as a module under `scripts/workflows/temporal/modules/`, with an entrypoint shim beside the fleet's others. It is **written, not moved** — there is no Python counterpart to port.
2. **It produces a CPI report from the same inputs the incumbent reads**, and the report is demonstrated on a real window rather than asserted. The bash script's inputs are its contract: the per-repo `.claude/logs/*.jsonl` pile, and [`cpi-decisions.md`](../cpi-decisions.md) for recurrence detection.
3. **Its evidence source is reachable through one seam**, so that [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) can point it at the journal without rewriting the sweep. **This phase does not build the journal-sourced reader** — PMP Phase 6 does, and that phase's requirement 7 states the interface it needs. What this phase owes it is a program whose input is a parameter rather than a hard-coded walk.
4. **Nothing here depends on a Temporal server, a worker, or a schedule** — demonstrated by running it from a shell on this workstation, which is how the incumbent runs today.
5. **The bash script keeps working until this one replaces it.** Both exist through this phase; retiring the bash entrypoint is [Phase 6](phase6_the_rest_of_the_fleet.md)'s to do, in the same change that orchestrates the Python one.

---

## Dependencies

**Inside this component:** none. It is a change to Python that already has a tree to live in, and it needs no Temporal runtime — the same property [Phases 2](phase2_durable_dispatch_identity.md) and [3](phase3_the_retry_boundary.md) have, and the reason all three are the work that proceeds if [Phase 1](phase1_the_starter_control_plane.md) stalls on a machine.

**Outside this component:** none that block it. [Workflow Decomposition](../workflow-decomposition/roadmap.md) gates *porting a shape still being changed*; this phase ports no shape, because there is nothing in the Python tree to reshape.

**What this phase unblocks:** [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md), which is the whole reason it is a phase. And [Phase 6](phase6_the_rest_of_the_fleet.md) requirement 2, which orchestrates what this phase writes.

---

## What this phase rests on

**No paper in this component's pool backs it**, and none needs to. It is a program being written against an existing shape, and both halves of that shape are already recorded:

| Source | What it supplies |
|---|---|
| [`cpi-cycle.md`](../../guide/cpi-cycle.md) | The operating manual for the cycle this workflow serves — what the sweep reads, what a finding is, and how [`cpi-decisions.md`](../cpi-decisions.md) is cross-referenced for recurrences. **The behavioural contract, and it is user-facing doc rather than a plan** |
| [`workflow-scripts.md`](../../standards/workflow-scripts.md) | The composition contract every workflow in this fleet conforms to |
| [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) requirement 7 | The one forward constraint: the sweep reaches its evidence through a storage seam, so redirecting it later is a change of input rather than a rewrite |

**The closest comparable in the tree is `triage_candidates`** — the other workflow authored directly in Python with no bash ancestor. Read it before starting; it is what "written, not moved" looks like when it is finished.

---

## §Runtime Verification

**Date:** 2026-08-20 · **Host:** `puma-workstation-mint` · **Runtime verified:** the absence of any `review-runs` counterpart in the Python tree, the size of the incumbent, and the shape of the nearest comparable module. **No Temporal server and no worker exist**; none is needed for this phase, which is the point.

```
$ wc -l scripts/workflows/review-runs.sh
375 scripts/workflows/review-runs.sh

$ find scripts/workflows/temporal -name '*review_runs*'
(no output)

$ ls scripts/workflows/temporal/modules/assistant/plan/triage_candidates/
__init__.py
prompts
triage_candidates_activities.py
triage_candidates_workflow.py

$ cd scripts/workflows/temporal/modules/assistant/plan/triage_candidates && wc -l *.py prompts/*.md
    0 __init__.py
  125 triage_candidates_activities.py
  484 triage_candidates_workflow.py
  197 prompts/triage_candidates.md
  806 total
```

**What those three observations say together.** The incumbent is 375 lines of bash. Nothing in the Python tree answers to its name, so requirement 1's *written rather than moved* is a measured fact and not a framing. And the nearest thing that was written rather than moved came out at 609 Python lines plus a 197-line prompt — which is the order of magnitude to expect here, not the 375 the bash suggests.

**Re-derive these before the build dispatch fires.** They are a plan-time reading and the tree moves.

---

## Implementation steps

- [ ] **Re-run § *Runtime Verification* and refresh it.**
- [ ] **Read [`cpi-cycle.md`](../../guide/cpi-cycle.md) first.** It is the behavioural contract, and it is more specific about what the sweep must produce than the bash script is.
- [ ] **Read `triage_candidates` end to end** — module, activities, prompt, entrypoint shim, tests. This phase's output should be indistinguishable in shape.
- [ ] **Write the module** under `scripts/workflows/temporal/modules/`, with its entrypoint shim and `run_*.py` beside the fleet's others.
- [ ] **Put the evidence source behind one seam.** The walk over `.claude/logs/*.jsonl` is *an* implementation of "where the evidence comes from", not the definition of it. [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) supplies the second implementation; this phase owes it a place to plug in.
- [ ] **Run it against a real window and record the run in this doc**, alongside the incumbent's output over the same window. **Do not average a disagreement away** — a difference is either the new sweep seeing more or seeing a subset it can parse, and only reading it tells you which.
- [ ] **Leave `review-runs.sh` in place.** It is the working reference until [Phase 6](phase6_the_rest_of_the_fleet.md) orchestrates the replacement, and this phase's own requirement 5 says so.
- [ ] **Do not register it with a worker and do not give it a schedule.** Both are [Phase 6](phase6_the_rest_of_the_fleet.md)'s, and doing either here re-imports the gate this phase exists to remove.

---

## Notes, decisions and gotchas

- **The gate this phase removes was structural, not an oversight.** Requirement 2 of [Phase 6](phase6_the_rest_of_the_fleet.md) read *"`review-runs` exists in the Python tree AND runs under Temporal"* — one requirement holding two deliverables with different gates. A conjunction inherits the *later* of its parts' gates, silently, and that is how a consumer needing no server ended up four phases behind one.
- **A workflow with no bash ancestor has no parity oracle, and this one is worse than most.** The fleet's parity suite compares a Python module against the bash script it was converted from. Here there is no conversion, and the output is prose findings rather than a diffable artifact. **Requirement 2 asks for a demonstrated report over a real window, not for parity** — and the honest cross-check against the incumbent is [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md)'s requirement 2, which runs both over one overlapping window once the journal is the source.
- **`review-sprint` is not in scope here and is not the same question.** It has never executed; [Phase 6](phase6_the_rest_of_the_fleet.md) requirement 3 rules whether it earns a port at all. `review-runs` is the one of the four with a live role and a run history, which is why it gets a phase and the others get a ruling.
- **Writing it does not decide where CPI's evidence lives.** That is PMP's, and this phase deliberately does not pre-empt it — requirement 3 is a seam, not a store.

---

## What this phase does not settle

**Whether the CPI sweep should source the journal.** [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) decides that and builds it; this phase only has to not make it a rewrite.

**Whether `review-runs` earns a Temporal schedule.** [Phase 6](phase6_the_rest_of_the_fleet.md) requirement 4 rules catch-up behaviour per schedule, and a CPI sweep is a plausible candidate for *skip a missed window* rather than *catch up*. **The ruling belongs there, with the other schedules, so it is made against the same criteria** rather than once here in isolation.
