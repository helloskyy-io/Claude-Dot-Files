# Phase 6 — The rest of the fleet, and the two that never ran

**Status: ⬜ NOT STARTED.** Sixth in [rollout order](roadmap.md), and the last phase this component plans in detail.

With one family proven end to end, the rest follow the same shape. **This phase is the one where the port stops being a demonstration and becomes the way work happens** — every surviving workflow orchestrated, schedules replacing timers, and the worker inventory telling the truth.

Two workflows do not get the benefit of the doubt. `plan-new` and `review-sprint` are **1,228 lines between them and neither has ever executed** (the figure is [`sprint.md`](../sprint.md)'s). Porting code nobody has run is porting an assumption, and this phase rules on them rather than carrying them.

---

## Requirements for completion

1. **Every workflow that earns a port is orchestrated by Temporal**, and nothing depends on a workflow that was not ported.
2. **`review-runs` runs under Temporal.** [Phase 9](phase9_review_runs_in_the_python_tree.md) writes it in the Python tree; this requirement is the orchestration half only, and it is where `review-runs.sh` is retired. **The two halves were one requirement until 2026-08-20 and that was the defect** — a conjunction inherits the later of its parts' gates, so a deliverable [PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) needs and that requires no server sat behind [Phase 5](phase5_the_first_dispatch.md) and therefore behind [Phase 1](phase1_the_starter_control_plane.md).
3. **`plan-new` and `review-sprint` are ruled** — each either ported, or retired with a written reason. **A ruling either way satisfies this requirement; leaving them unruled does not.**
4. **Schedules replace timers.** A schedule survives the machine being off, which is the property two other components are waiting on.
5. **The worker inventory is accurate** — every worker, its task queue, its registered workflows and its registered activities, reconciled against the code in the same change that alters either.

---

## Dependencies

**Inside this component:** [Phase 5](phase5_the_first_dispatch.md), and — **for requirement 2 alone** — [Phase 9](phase9_review_runs_in_the_python_tree.md), because there has to be a `review-runs` in the Python tree before there is one to orchestrate. Every ruling this phase applies was made earlier.

**Outside this component:** [Workflow Decomposition](../workflow-decomposition/roadmap.md), for the same reason and with more force than in [Phase 5](phase5_the_first_dispatch.md) — this phase ports *every* family, so every family's shape has to be settled rather than just one.

**What this phase unblocks, and these are the consumers requirement 2 and requirement 4 exist for:**

| Waiting on | Consumer |
|---|---|
| **`review-runs` orchestrated** (requirement 2) | Nothing outside this component. **[PMP Phase 6](../persistent-memory-protocol/phase6_cpi_reads_the_journal.md) waits on [Phase 9](phase9_review_runs_in_the_python_tree.md), not on this requirement** — its gate is the Python program, not the scheduler, and [Phase 9](phase9_review_runs_in_the_python_tree.md) is ungated, so that consumer can be pulled forward without waiting on this phase at all |
| **Schedules** (requirement 4) | [PMP Phase 8](../persistent-memory-protocol/phase8_the_poller.md) — a scheduled workflow that reads a to-do bit and starts work with no human trigger |
| **Schedules** (requirement 4) | [Autonomous Operation](../autonomous-operation/autonomous-operation.md) — scheduled dispatch that survives the machine being off |
| **The port as a whole** | [Autonomous Operation](../autonomous-operation/autonomous-operation.md) — the driver that composes parents into a loop |

---

## What this phase rests on

**No paper in this component's pool backs this phase**, and no paper needs to. It is the application, at fleet scale, of rulings that [Phase 2](phase2_durable_dispatch_identity.md), [Phase 3](phase3_the_retry_boundary.md) and [Phase 4](phase4_the_claude_cli_activity.md) made against evidence, and of the shape [Phase 5](phase5_the_first_dispatch.md) proved.

What it does rest on:

- The vendored [Worker Deployment Standard](../../standards/temporal/worker_deployment_standard.md) — **§1.3** the domain-boundary test, which decides how many workers this fleet gets; **§3** the worker inventory and its same-PR obligation; **§10** cutover discipline, which governs the order in which a routing change and a worker deploy may land.
- The [Temporal Standard](../../standards/temporal/temporal_standard.md) **§10.1** promotion rule, which decides where shared code and shared prompt fragments live: a fragment is promoted out of a workflow's folder **if and only if more than one workflow uses it** — consumer count decides, never taste.
- [`temporal-integration.md`](temporal-integration.md)'s migration path, step 3: the Temporal file layout, and why `children/` dissolves.

---

## How many workers, and the rule that decides it

**This is the question this phase has to answer that no earlier phase does**, because [Phase 5](phase5_the_first_dispatch.md) builds exactly one worker and never has to choose.

The [domain-boundary test](../../standards/temporal/worker_deployment_standard.md) §1.3: two workflows belong on the same worker if they share at least two of — the same core external dependency, the same failure domain, the same operational cadence. **One or zero shared, and they go on separate workers.**

**Our segmentation has an axis upstream's does not.** Ours are segmented by **machine** as well as by capability, because Claude Code must run on the machine holding the repo — a repo-locality constraint with no upstream equivalent, and the reason [§A3](../../standards/temporal/claude-dot-files-addendum.md) exists. [Phase 1](phase1_the_starter_control_plane.md) closes §A3 and names the scheme; **this phase applies it, and must not redesign it.** Queue names are expensive to change once workers deploy against them, which is precisely why the ruling was pulled forward to the first phase.

**The worker set inherits [Phase 4](phase4_the_claude_cli_activity.md)'s slot rule, and inherits it per worker.** Requirement 8 there binds every worker that registers the `claude_cli` activity: the activity slot count comes from the host's real concurrency budget rather than the SDK's default of 100, and `ThreadPoolExecutor(max_workers=...)` is at least that number. **The budget is per host, so the number is decided per worker and not once for the fleet** — the machine axis means these workers sit on different machines with different budgets. Applying one number everywhere would be the same mistake as the default, one step further along.

**One rule from the standard is easy to skip and expensive to skip:** every declared domain must have a **built worker, empty if it has no workflows yet.** A declared-but-unbuilt domain is the bait that creates a catch-all worker — a workflow whose real domain has no running worker gets parked on the nearest *built* one, and parking becomes permanent. **SDK caveat, verified upstream:** the Python SDK rejects a worker with both an empty workflow list and an empty activity list, so an empty shell registers a single no-op sentinel activity. That is an SDK-satisfying placeholder, not a workflow.

---

## Implementation steps

- [ ] **Enumerate the population off the tree.** Every workflow module, every activity module, every prompt file — read from disk, never from a table. A table checked against itself cannot see the entry that was never added to it.
- [ ] **Apply the domain-boundary test to that population** and decide the worker set. Record the reasoning per worker, not just the result.
- [ ] **Stand up every declared domain's worker, empty if it has no workflows yet.** Do not defer one because it would be empty.
- [ ] **Wrap and orchestrate family by family**, in an order the build chooses and records — each family finished before the next starts, so a problem is attributable.
- [ ] **Apply [Phase 3](phase3_the_retry_boundary.md)'s per-call-class ruling to every newly-wrapped activity**, extending the audit [Phase 5](phase5_the_first_dispatch.md) began. The rule does not change; the population does.
- [ ] **Orchestrate `review-runs`** — [Phase 9](phase9_review_runs_in_the_python_tree.md) has already written it — and retire `review-runs.sh` in the same change.
- [ ] **Rule `plan-new`.** Port it, or retire it with the reason written down. **The default is retire** — a workflow that has never executed has never been shown to be wanted, and the burden is on the port.
- [ ] **Rule `review-sprint`** on the same basis, separately. Two rulings, not one; they are two workflows and may deserve different answers.
- [ ] **Replace timers with Temporal schedules**, and record which schedules exist and what each one starts.
- [ ] **Decide catch-up behaviour per schedule.** A schedule that was missed while the machine was off either runs late or is skipped, and the right answer differs by workflow — a window-scoped job and a state-converging job want opposite defaults. **Do not pick one global answer.**
- [ ] **Apply the promotion rule to shared code and shared prompt fragments** — promoted out of a workflow's folder if and only if a second consumer exists, demoted back when one goes away. **Do not create a shared junk drawer**; one location everything sources regardless of consumer count is a pattern this fleet has already retired.
- [ ] **Follow the cutover ordering.** A routing change waits for the receiving worker to be polling; never the reverse. The standard records a live incident from getting this backwards, where a dispatch fail-fasted against a queue with no poller.
- [ ] **Update the worker inventory in the same change**, every time. It is a factual registry whose source of truth is the code, and it is the one part of that vendored standard an engineer may edit directly.
- [ ] **Confirm nothing depends on a workflow that was not ported**, and record how that was confirmed.
- [ ] **Re-run § *Runtime Verification*** against every standing worker.

---

## §Runtime Verification

**Date:** 2026-08-19 · **Host:** `puma-workstation-mint` · **Runtime verified:** the population this phase acts on, read off the tree at plan time. **No workers exist yet**; the build replaces this block with observations of the standing fleet.

```
$ find scripts/workflows/temporal/modules -name '*_workflow.py' | wc -l
20

$ find scripts/workflows/temporal/modules -name '*_activities.py' | sort
scripts/workflows/temporal/modules/assistant/assistant_activities.py
scripts/workflows/temporal/modules/assistant/build/build_activities.py
scripts/workflows/temporal/modules/assistant/plan/plan_activities.py
scripts/workflows/temporal/modules/assistant/plan/plan_feature/plan_feature_activities.py
scripts/workflows/temporal/modules/assistant/plan/plan_project/plan_project_activities.py
scripts/workflows/temporal/modules/assistant/plan/plan_verify/plan_verify_activities.py
scripts/workflows/temporal/modules/assistant/plan/triage_candidates/triage_candidates_activities.py
scripts/workflows/temporal/modules/assistant/research/research_activities.py
scripts/workflows/temporal/modules/assistant/review_pr/review_pr_activities.py
scripts/workflows/temporal/modules/journal/journal_activities.py
```

**Four purpose families are visible in that layout** — `build`, `plan`, `research`, `review_pr` — plus a `journal` module. **That is a starting hypothesis for the domain-boundary test, not its answer.** The test is about shared external dependencies, shared failure domains and shared cadence; a directory layout is evidence about none of the three, and the machine axis cuts across all of it.

**`review-runs` has no module in that tree**, which is why requirement 2 says *written* rather than *moved*.

**Re-derive these counts at build time.** They are a plan-time reading and the tree moves; the enumeration step above exists so the build never trusts this block's numbers.

---

## Notes, decisions and gotchas

- **The burden of proof runs against porting the two that never ran.** A workflow with no execution history has no evidence that anyone wants it, no evidence that it works, and — since it has never run — no evidence about its failure modes to design a retry policy against. **Retiring it is the cheap, reversible choice**; porting it spends effort on an assumption. Rule each on its own merits, and say what a future need would look like if it is retired.
- **`review-runs` is different and the difference is the point.** It has a live role and a run history, and a downstream phase in another component is waiting on it. It is the one of the four whose port is justified before anyone argues about it — **which is why it left this phase entirely on 2026-08-20 and became [Phase 9](phase9_review_runs_in_the_python_tree.md).** § *Runtime Verification* above is dated 2026-08-19 and still reads *"which is why requirement 2 says written rather than moved"*; that is a historical record and is left standing as one. **The `written rather than moved` requirement is now [Phase 9](phase9_review_runs_in_the_python_tree.md)'s requirement 1**; requirement 2 here is orchestration only.
- **Catch-up behaviour is per schedule and getting it wrong is silent.** A missed window-scoped run should usually be skipped; a missed state-converging run should usually be caught up. A single global setting will be wrong for one of them and nothing will go red.
- **The promotion rule is mechanical and that is its value.** Nothing becomes shared because it *might* be reused; it becomes shared when a second consumer appears, and it demotes when one goes away. Consumer count decides, never taste — and anything at a parent level is shared by definition, so a reader never has to open a file to learn its scope.
- **A component with a real end.** When this phase closes, the port is done: the fleet runs on durable execution, and what remains in this component is deployment work gated outside it — [Phase 7](roadmap.md) and [Phase 8](roadmap.md).

---

## What this phase does not settle

**Which workflows exist to port.** [Assistant Workflow Design](../sprint.md) designs and builds workflows that do not exist yet, and it is a long-running component that gains phases as the fleet gains capabilities. **This phase ports what exists when it runs** — it does not hold the door open for work another component has not started, and a workflow authored after this phase closes registers on an already-built worker rather than triggering a re-port.

**Whether the operator wants `plan-new` or `review-sprint` at all.** Requirement 3 asks for a ruling and names the default; it does not make the ruling, because *"is this workflow wanted?"* is a product judgement and not a technical one. The evidence the ruling should weigh — that neither has executed — is already recorded in [`sprint.md`](../sprint.md).
