# Autonomous Operation

**Not designed. Not planned. Do not build toward it yet** — the loop is only safe once memory is typed and durable execution can resume a failed leg. This doc exists so the earlier sprints are built with it in view, not because planning has started.

Distinct from **Autonomous Execution**, which was about building the workflows themselves. This is about running the fleet with nobody pressing the button.

## The tier above parents

Where a parent composes children into one task-complete unit of work, this composes **parents** into a loop that keeps going: what ran, what it concluded, and what should run next — decided from memory, in code, with no human in the loop and no AI choosing the route.

- **A driver that runs many parent workflows in sequence**, choosing each next dispatch from persisted state rather than from a script written in advance. This is the payoff of the Memory Management Framework — the typed result a parent leaves behind is what the next decision reads.
- **Exit criteria that are real and observable** — a `HOLD` on a PR needing human judgement, a convergence signal, a budget ceiling. None of this is designed. The one thing already known: it must be able to stop and hand back, and *stop* has to be a state something can **observe**, not a turn count.

### The convergence signal, and what it is safe to consume — supplied by [Memory Management Framework Phase 5](../memory-management-framework/phase5_convergence_stopping.md), 2026-08-09

Recorded here so this doc does not have to re-derive it when planning starts, and stated as a **constraint** rather than an offer.

**What exists.** Every `review-pr` dispatch now writes a `{"type": "convergence", …}` event to its run log carrying a computed state — `converged` / `not_converged` / `indeterminate` — over the open subset of the PR's findings. It **routes nothing today** and `MAX_LOOPS` is still the only stopping authority.

> **And nothing reads those events, which is the constraint this section most needs to carry.** They accrue and no committed tool consumes them, so the live path has no denominator for the two facts the GitHub archive structurally cannot produce (the `pass_not_evaluable` and `history_unreadable` rates). [Memory Management Framework Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) owns building that reader and printing Phase 5's gate conditions with their denominators. **The ruling on whether the predicate ever gates anything is the operator's, and the case where it would actually decide something is THIS component's** — #67 and #71 reached passes 3 and 4 through *separate operator dispatches*, which no `MAX_LOOPS` governs. A driver planned before those numbers exist is planning against an unmeasured signal.

**Three things a consumer must not get wrong:**

1. **`converged` is not a merge authority.** It answers *"is there anything left for another pass of this review loop to do?"* — never *"is this work finished?"*. The merge decision stays with the typed record's `routed_outcome`. A driver that read convergence as permission to merge would be reading a different question's answer.
2. **`indeterminate` is a THIRD state, not a soft `not_converged`.** It means the predicate could not evaluate — the pass did not route, the thread was unreadable, there is no prior pass, the history is non-conforming, or the finding set has churned. Every instance names its reason. **A driver that folded it into either of the other two would be inventing a decision the predicate declined to make**, and this is the arm that carries every machinery failure.
3. **`converged` can be true while work is outstanding elsewhere.** `escalated` findings count as closed for this loop — the reviewer cannot resolve them on any future pass — so a converged assessment may carry a non-empty `escalated_open` list. **Read that list.** It names work that moved to another authority, which for a driver with nobody in the loop is precisely the thing that needs handing back.

**And the constraint that matters most: the signal's input is written by the loop it would stop.** Four of five documented false-convergence modes have a check; the fifth — a reviewer marking `fixed` what is not fixed — has none, because separating it is a second review. **The phase deliberately gates nothing on this basis, and a driver that gated on it would be taking a risk this component measured and declined.** What would change that is a denominator, not a design: [Phase 5 § What would let this gate](../memory-management-framework/phase5_convergence_stopping.md).

## Scheduled entry

Scheduled dispatch belongs to the durable-execution layer rather than the edge machine, so it depends entirely on Temporal Integration landing first.

**This is only the trigger.** `review-runs.sh` gets its scheduling here, but the workflow itself exists already and belongs to Continuous Process Improvement — nothing about it moves.

Today's design puts the trigger on whichever workstation happens to be awake. A Temporal schedule survives the machine being off, is visible in one place, and its history is queryable.

**What is actually cron-shaped**, and what is not: CPI sweeps and research revalidation are time-driven and therefore candidates. PR disposition is event-driven and should stay event-driven — do not put it on a timer because the timer exists.

### Missed windows: the discriminator is window-scoped vs state-converging

Verified against the code rather than assumed, and worth writing down because it is easy to get backwards.

- **A CPI sweep is window-scoped.** `review-runs.sh` selects logs with a trailing `find -mtime -${DAYS}`, so a skipped sweep lets those days age out of *every* future window. The data is **lost permanently**. This is the case that needs a catch-up run.
- **Research revalidation is state-converging.** A paper past its date stays past its date until something refreshes it, so skipping delays the work without losing it. Skip is safe.

## Open questions

- **What are the real exit criteria**, expressed as observable state rather than a turn count?
- **Catch-up, skip, or alert per schedule** — the discriminator above decides it, but each schedule still needs the ruling applied.
- **What, if anything, should the convergence signal GATE — and it is THIS component's question, not the Memory Management Framework's.** [Phase 5 § What would let this gate](../memory-management-framework/phase5_convergence_stopping.md) condition 3 rules that convergence is *not* a merge authority, that `MAX_LOOPS = 1` is already tight enough that a within-run stopping rule buys little, and that the case where the signal would actually decide something is the **cross-dispatch** one — #67 and #71 reached passes 3 and 4 through separate operator dispatches, which no bound governs. That is this component's driver. **Trigger: [Phase 6](../memory-management-framework/phase6_read_what_it_writes.md) printing conditions 1 and 2 with their denominators.** *Placed here on 2026-08-10 because it had been carried as prose in § The convergence signal above and appeared in no question list — the Memory Management Framework owns the instrument, and a ruling that terminates in a document rather than in an actor with a trigger is how it stops existing.*
