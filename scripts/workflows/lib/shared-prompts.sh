# shared-prompts.sh — shared prompt blocks for workflow scripts
#
# Source this file from any task-execution workflow script to get the standard
# DECISION_LOG_AND_REFLECTION block. This avoids duplicating the same prompt
# text across every workflow (current count: 6 scripts using identical blocks).
#
# Usage in a workflow script:
#   source "${SCRIPT_DIR}/lib/shared-prompts.sh"
#   # then use ${DECISION_LOG_AND_REFLECTION} in your PROMPT
#
# When the prompt text needs updating, change it here once; all sourcing
# scripts pick up the change on next invocation.

# ---------------------------------------------------------------------------
# DECISION_LOG_AND_REFLECTION
#
# Standard PR-comment scaffolding for autonomous dispatch workflows. Every
# task-execution workflow appends this section to its prompt to capture
# decision rationale + post-run reflection for operator review.
# ---------------------------------------------------------------------------
DECISION_LOG_AND_REFLECTION=$(cat <<'DLR_EOF'
After pushing (and creating the PR if on the new-branch path), post a PR comment containing a Decision Log and Post-Run Reflection. Write the comment body to a temp file first (e.g., `/tmp/pr-comment-<timestamp>.md`), then post via `gh pr comment <PR-number> --body-file <temp-file>`. Do NOT inline the content into the command — multi-line content in a single arg is fragile.

The comment must contain these two sections:

## Decision Log

List NON-OBVIOUS decisions made during this run. One bullet per decision, format:
`**[High/Medium/Low]** <what was decided>. Alternatives: <what else was considered>. Why: <brief rationale>.`

Include only decisions where a reasonable engineer could have chosen differently: architecture choices, trade-off calls, scope boundary decisions, severity calls on reviewer findings, rejected reviewer suggestions.

Exclude: obvious implementation details, standards conformance, pattern application, mechanical changes that had no real alternative.

If no non-obvious decisions were made, state: "No significant decisions — task was mechanical."

Order: Low-confidence decisions FIRST (human prioritizes reviewing those).

## Deferred Work

Items intentionally NOT addressed in this PR but tracked for follow-up. The finding-disposition rule requires every deferred item to point at a tracker — this section is the structured place for those pointers so they don't get buried in prose. One bullet per item:

- **<work item>** — Why deferred: <brief reason>. Tracked at: <location — issue #, planning doc, loose-ends file, follow-up PR, etc.>

If nothing was deferred, omit this section.

## Post-Run Reflection

Omit any section below that has nothing to report — silence means no issues. Be specific when noting friction ("task file ambiguous on X" is useful; "it was fine" is not).

- **Friction:** ambiguity in the task, missing context, tool gotchas encountered, points where guidance was thin
- **Project-level suggestions (this repo):** standards gaps, documentation improvements, conventions that should be documented
- **Tooling-level suggestions (claude-dot-files):** workflow prompt improvements, skill gaps, rule refinements that would benefit future runs

If all three sections are empty, state: "No friction or suggestions from this run."
DLR_EOF
)

# ---------------------------------------------------------------------------
# HEADLESS_EXECUTION_GUARD
#
# Every workflow runs headless (`claude -p`). The harness treats a turn that
# ends with a text-only message (no tool call) as "done" and TERMINATES the
# run — silently skipping every later stage. This block makes the orchestrator
# aware of that so it never stops early while dispatched agents or other work
# are still outstanding.
#
# Origin: research.sh burn-test run 1 (research-20260726-215339 — exit 0,
# $3.12, nothing produced) + skyy #217 B-dispatch. In both, the main loop
# background-dispatched agents then ended the turn with a text-only "waiting…"
# message; the run ended before the agents' results were consumed. Second
# occurrence of the class → shipped fleet-wide per watch-criteria discipline.
# Supersedes the 2026-07-24 S4 "background dispatch is the standard mechanism"
# wording, which relied on the model reliably emitting a keep-alive tool call.
# ---------------------------------------------------------------------------
HEADLESS_EXECUTION_GUARD=$(cat <<'GUARD_EOF'
## HEADLESS EXECUTION MODEL — read before dispatching anything

You are running HEADLESS (`claude -p`), not in an interactive session. A turn that ends with a text-only message and NO tool call TERMINATES the entire run — the harness treats a text-only turn as "done," and every later stage is silently skipped (exit 0, nothing produced). Binding consequences:

- **Never end a turn while any dispatched agent, background task, or tool result is still outstanding.** Ending a turn to "wait for" or "monitor" agents kills the run before their results arrive.
- **Dispatch sub-agents as FOREGROUND agents (`run_in_background: false`).** A foreground Agent call BLOCKS the turn until the result returns, so the run cannot die mid-wait. Multiple foreground Agent calls in a single assistant message still run concurrently where the harness allows — you get concurrency AND survival. Do NOT background-dispatch and then wait; do NOT use ScheduleWakeup to "wait" for agents in a headless run.
- **Never emit a standalone progress-narration turn and stop.** Keep emitting tool calls until the deliverable exists.
- **The run is COMPLETE only when the final deliverable is produced and its completion signal is printed (for PR-producing workflows, the PR URL).** "I've dispatched the agents / I'm waiting / here's my progress" is NOT completion — it is a run-ending mistake.
GUARD_EOF
)
