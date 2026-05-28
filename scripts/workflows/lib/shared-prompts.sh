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
