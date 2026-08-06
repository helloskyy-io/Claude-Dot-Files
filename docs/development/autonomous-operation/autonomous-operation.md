# Autonomous Operation

**Not designed. Not planned. Do not build toward it yet** — the loop is only safe once memory is typed and durable execution can resume a failed leg. This doc exists so the earlier sprints are built with it in view, not because planning has started.

Distinct from **Autonomous Execution**, which was about building the workflows themselves. This is about running the fleet with nobody pressing the button.

## The tier above parents

Where a parent composes children into one task-complete unit of work, this composes **parents** into a loop that keeps going: what ran, what it concluded, and what should run next — decided from memory, in code, with no human in the loop and no AI choosing the route.

- **A driver that runs many parent workflows in sequence**, choosing each next dispatch from persisted state rather than from a script written in advance. This is the payoff of the Memory Management Framework — the typed result a parent leaves behind is what the next decision reads.
- **Exit criteria that are real and observable** — a `HOLD` on a PR needing human judgement, a convergence signal, a budget ceiling. None of this is designed. The one thing already known: it must be able to stop and hand back, and *stop* has to be a state something can **observe**, not a turn count.

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
