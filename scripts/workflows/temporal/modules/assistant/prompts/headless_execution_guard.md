## HEADLESS EXECUTION MODEL — read before dispatching anything

You are running HEADLESS (`claude -p`), not in an interactive session. A turn that ends with a text-only message and NO tool call TERMINATES the entire run — the harness treats a text-only turn as "done," and every later stage is silently skipped (exit 0, nothing produced). Binding consequences:

- **Never end a turn while any dispatched agent, background task, or tool result is still outstanding.** Ending a turn to "wait for" or "monitor" agents kills the run before their results arrive.
- **Dispatch sub-agents as FOREGROUND agents (`run_in_background: false`).** A foreground Agent call BLOCKS the turn until the result returns, so the run cannot die mid-wait. Multiple foreground Agent calls in a single assistant message still run concurrently where the harness allows — you get concurrency AND survival. Do NOT background-dispatch and then wait; do NOT use ScheduleWakeup to "wait" for agents in a headless run.
- **Never emit a standalone progress-narration turn and stop.** Keep emitting tool calls until the deliverable exists.
- **The run is COMPLETE only when the final deliverable is produced and its completion signal is printed (for PR-producing workflows, the PR URL).** "I've dispatched the agents / I'm waiting / here's my progress" is NOT completion — it is a run-ending mistake.