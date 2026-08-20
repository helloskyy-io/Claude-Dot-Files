# Phase 9 — `review-runs`, written in the Python tree

**Status: ⬜ NOT STARTED.** Listed in [rollout order](roadmap.md) after [Phase 3](phase3_the_retry_boundary.md) and before [Phase 4](phase4_the_claude_cli_activity.md), with [Phases 2](phase2_durable_dispatch_identity.md) and 3 — the phases that need no Temporal server. **Its number is 9 because 9 was the next free identifier**, not because it is built ninth; the roadmap states that numbers are identity and not order, and this phase is the first entry that exercises the rule.

**This phase exists because a downstream consumer was gated on something it does not need.** [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) waits on the *Python port of `review-runs`* and says so twice in its own documents — *"This is the only gate; the Temporal server is not one"* — and PMP split that phase out of its own Phase 8 specifically so its only consumer would not sit behind a server nobody has stood up. Carrying the port inside [Phase 6](phase6_the_rest_of_the_fleet.md) put it back there: Phase 6 is gated on [Phase 5](phase5_the_first_dispatch.md), which is gated on [Phase 1](phase1_the_starter_control_plane.md), which *is* the server. **Splitting the write out is what makes the roadmap's own "not waiting on the server" cell true.**

**Two halves, and only one of them is here.** *Written in Python* is this phase. *Orchestrated by Temporal* stays in [Phase 6](phase6_the_rest_of_the_fleet.md) requirement 2, where every other workflow's orchestration lives. PMP Phase 6's gate resolves to **this phase, not to that requirement** — a batch read over the journal needs a program, not a scheduler.

---

## Requirements for completion

1. **`review-runs` exists in the Python tree** as a module under `scripts/workflows/temporal/modules/`, with an entrypoint shim and a `run_*.py` beside the fleet's others. It is **written, not moved** — there is no Python counterpart to port. **Which domain folder it lands in is the build's choice and the reasoning is recorded** — `modules/` is domain-shaped (`assistant/{build,plan,research,review_pr}/`, `journal/`) and this workflow is a meta-review of the fleet rather than a member of any existing family, so the placement is a judgement rather than a lookup. [Phase 6](phase6_the_rest_of_the_fleet.md)'s domain-boundary test then decides which *worker* it registers on, which is a separate question.
2. **It produces a CPI report from the same inputs the incumbent reads**, and the report is demonstrated on a real window rather than asserted. The bash script's inputs are its contract: the per-repo `.claude/logs/*.jsonl` pile, and [`cpi-decisions.md`](../cpi-decisions.md) for recurrence detection.
3. **Its evidence source sits behind a NAMED READ INTERFACE, not merely a path parameter** — enumerate the evidence units, read one, and report what the record does not contain, with **no filesystem semantics leaking past it**. Those are [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) requirement 7's own three operations, expressed over the incumbent's data model. **A path override is NOT this**, and shipping one is how the promise below becomes false: PMP Phase 6 would re-author the evidence assembly, which is exactly the rewrite this requirement exists to prevent. **This phase ships the interface plus its log-backed implementation; PMP Phase 6 adds the journal-backed one** — and PMP requirement 2 needs *both* runnable over one overlapping window, so the first implementation must survive the second rather than be replaced by it.
4. **Where the report goes is ruled, not inherited.** The incumbent writes its report into this repo's committed `docs/development/reviews/`, so **findings about any analysed repo land in this repo's git history** — which is public. That may well remain the right answer (one searchable location for the whole cycle), but it is a **cross-repository disclosure decision and this phase is the last cheap moment to make it deliberately.** Record the destination, record whether quoting log evidence from a non-public repo is in bounds, and record which it is: an accepted decision, or a constraint on what may be quoted.
5. **The evidence it reads is treated as UNTRUSTED INPUT.** Run transcripts contain whatever earlier runs ingested — PR bodies, issue text, fetched pages, external tool output. This sweep feeds that content to a model and commits the result, and [Phase 6](phase6_the_rest_of_the_fleet.md) requirement 4 later puts it on a schedule, at which point no human is watching. **Prompt text is not a containment mechanism.** The sweep declares what it may read and what it may write rather than inheriting the fleet-wide invocation, and the evidence-source parameter is bounded by the entrypoint's existing repo-path containment or explicitly ruled out-of-repo with a stated reason.
6. **Nothing here depends on a Temporal server, a worker, or a schedule** — demonstrated by running it from a shell on this workstation, which is how the incumbent runs today.
7. **The bash script keeps working until this one replaces it.** Both exist through this phase; retiring the bash entrypoint is [Phase 6](phase6_the_rest_of_the_fleet.md)'s to do, in the same change that orchestrates the Python one.

---

## Dependencies

**Inside this component:** none. It is a change to Python that already has a tree to live in, and it needs no Temporal runtime — the same property [Phases 2](phase2_durable_dispatch_identity.md) and [3](phase3_the_retry_boundary.md) have, and the reason all three are the work that proceeds if [Phase 1](phase1_the_starter_control_plane.md) stalls on a machine.

**Outside this component:** none that *block* it. [Workflow Decomposition](../workflow-decomposition/roadmap.md) gates *porting a shape still being changed*; this phase ports no shape, because there is nothing in the Python tree to reshape.

**But it is not free of that component, and the non-blocking claim should not be read as no-interaction.** This phase authors a shim and a `run_*.py`, and [Workflow Decomposition Phase 3](../workflow-decomposition/roadmap.md) is what rules the five divergences those artifacts settle — verbosity, exit codes, interactive prompts, stream discipline, working directory — for the whole fleet at once. **If that ruling has landed, conform to it; if it has not, adopt `triage_candidates`' current answers and expect one reconciliation pass.** That phase also states its shim-naming guard covers *"all twenty"* workflows, a figure read off a tree this phase makes twenty-one. **That count is Workflow Decomposition's to update and not this phase's to edit** — it is named here so the build reports it rather than trips over it.

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

$ wc -l scripts/workflows/temporal/scripts/triage_candidates.sh \
        scripts/workflows/temporal/scripts/run_triage_candidates.py \
        scripts/workflows/temporal/tests/unit/test_triage_candidates_split.py
   14 scripts/workflows/temporal/scripts/triage_candidates.sh
   88 scripts/workflows/temporal/scripts/run_triage_candidates.py
 1507 scripts/workflows/temporal/tests/unit/test_triage_candidates_split.py
 1609 total
```

**What those observations say together.** The incumbent is 375 lines of bash. Nothing in the Python tree answers to its name, so requirement 1's *written rather than moved* is a measured fact and not a framing.

**And the comparable is much bigger than its module directory.** `triage_candidates` is **806 lines in the module plus 1,609 outside it** — its shim, its runner, and a 1,507-line unit test. **The second command exists because the first one alone under-measures the comparable by two thirds**, and this phase's implementation steps require all of the same artifacts. Test modules in this repo carry long rationale headers by convention, so the 1,507 is not a proxy for assertion count — but it is real work, and pricing this phase off the 806 alone would have been pricing three of its six artifacts.

**Re-derive these before the build dispatch fires.** They are a plan-time reading and the tree moves.

---

## Implementation steps

- [ ] **Re-run § *Runtime Verification* and refresh it.**
- [ ] **Read [`cpi-cycle.md`](../../guide/cpi-cycle.md) first.** It is the behavioural contract, and it is more specific about what the sweep must produce than the bash script is.
- [ ] **Read `triage_candidates` end to end** — module, activities, prompt, entrypoint shim, tests. This phase's output should be indistinguishable in shape.
- [ ] **Write the module** under `scripts/workflows/temporal/modules/`, with its entrypoint shim and `run_*.py` beside the fleet's others.
- [ ] **Write the read interface first, then its log-backed implementation.** Name the three operations — enumerate, read one, report gaps — and assert no filesystem semantics leak past them. The walk over `.claude/logs/*.jsonl` is *an* implementation of "where the evidence comes from", not the definition of it, and [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) supplies the second. **Write the interface even though only one implementation exists** — a seam introduced after the second consumer arrives is the rewrite requirement 3 exists to prevent.
- [ ] **Rule the output destination and write the ruling down** — requirement 4. Do this before the first report is generated, not after it is committed.
- [ ] **Bound what the sweep may read and write** — requirement 5. Declare the evidence-source parameter through the entrypoint's existing repo-path containment, or rule it deliberately out-of-repo with the reason stated beside it. Declare the tool surface explicitly rather than inheriting the fleet-wide invocation.
- [ ] **Run it against a real window and record the run in this doc**, alongside the incumbent's output over the same window. **Do not average a disagreement away** — a difference is either the new sweep seeing more or seeing a subset it can parse, and only reading it tells you which.
- [ ] **Leave `review-runs.sh` in place.** It is the working reference until [Phase 6](phase6_the_rest_of_the_fleet.md) orchestrates the replacement, and this phase's own requirement 7 says so.
- [ ] **Do not register it with a worker and do not give it a schedule.** Both are [Phase 6](phase6_the_rest_of_the_fleet.md)'s, and doing either here re-imports the gate this phase exists to remove.

---

## Notes, decisions and gotchas

- **The gate this phase removes was structural, not an oversight.** Requirement 2 of [Phase 6](phase6_the_rest_of_the_fleet.md) read *"`review-runs` exists in the Python tree AND runs under Temporal"* — one requirement holding two deliverables with different gates. A conjunction inherits the *later* of its parts' gates, silently, and that is how a consumer needing no server ended up four phases behind one.
- **A workflow with no bash ancestor has no parity oracle, and this one is worse than most.** The fleet's parity suite compares a Python module against the bash script it was converted from. Here there is no conversion, and the output is prose findings rather than a diffable artifact. **Requirement 2 asks for a demonstrated report over a real window, not for parity** — and the honest cross-check against the incumbent is [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md)'s requirement 2, which runs both over one overlapping window once the journal is the source.
- **`review-sprint` is not in scope here and is not the same question.** It has never executed; [Phase 6](phase6_the_rest_of_the_fleet.md) requirement 3 rules whether it earns a port at all. `review-runs` is the one of the four with a live role and a run history, which is why it gets a phase and the others get a ruling.
- **Writing it does not decide where CPI's evidence lives.** That is PMP's, and this phase deliberately does not pre-empt it — requirement 3 is a seam, not a store.
- **The sweep is a reader of untrusted content and the schedule is what makes that matter.** Today a human runs it and reads the result. Under [Phase 6](phase6_the_rest_of_the_fleet.md) requirement 4 nobody does, and the input is transcript text that earlier runs pulled from PRs, issues and fetched pages. **That is indirect prompt injection into a write-capable process whose output is committed**, and requirement 5 exists because the incumbent's only defence is a sentence in its prompt telling the model which file to write. **A sentence is not a boundary.**
- **The output crossing a repo boundary is the part nobody has ruled.** Reports about a private repo are committed into this one. Requirement 4 does not assume that is wrong — it refuses to let it stay *unexamined*, because the moment to examine it is while the program is being written rather than after a year of reports.

---

## What this phase does not settle

**Whether the CPI sweep should source the journal.** [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) decides that and builds it; this phase only has to not make it a rewrite.

**Whether `review-runs` earns a Temporal schedule.** [Phase 6](phase6_the_rest_of_the_fleet.md) requirement 4 rules catch-up behaviour per schedule, and a CPI sweep is a plausible candidate for *skip a missed window* rather than *catch up*. **The ruling belongs there, with the other schedules, so it is made against the same criteria** rather than once here in isolation.
