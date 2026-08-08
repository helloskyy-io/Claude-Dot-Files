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

- **<work item>** — Why deferred: <brief reason>. Tracked at: <location>. Verified by: <the exact command you ran and what you observed>

**VERIFICATION IS BY FETCH, NEVER BY PLAUSIBILITY.** A pointer you did not open is a guess dressed as a citation, and it is the single most common way real work disappears. Before writing any 'Tracked at' value you MUST run the command that opens it and record the result in 'Verified by':

- an issue -> `gh issue view <N> --json number,title,state,body` — confirm it is OPEN and its body actually covers THIS item
- a file/doc/phase-doc entry -> Read or Grep the live file on the DEFAULT branch (not your worktree — your branch's copy may contain an edit that never merges) and quote the line you found
- a follow-up PR -> `gh pr view <N>` — confirm it is open and in scope

**Write what you observed, not that you checked.** 'Verified by: gh issue view 230 -> OPEN, body covers the Python-tier gate' is an attestation. 'Verified present' is a claim about yourself, and it is the exact shape that has shipped false twice.

**If you cannot verify it, you may not defer to it.** Fix the item, or SURFACE it plainly with no pointer at all. An honest 'no home for this' is worth more than a plausible pointer to nothing — and a naked surfaced item gets picked up downstream, while a laundered one gets filed away as handled.

**INVALID deferral targets — these are not homes, they are disappearances:**
- **THIS PR** (its body, its description, its comments, 'tracked in this PR') — it dies at merge. This is the most common laundering shape and it is never acceptable.
- A tracker you are 'about to' create — create it FIRST, then cite the real number.
- A checked `- [x]` line or a completed section — that records something FINISHED, and pointing pending work at it is how the work stops existing.
- A person, a session, or 'the next run'.

Do this at the moment you DECIDE to defer, not when you write this comment up. By the time you are formatting the table the decision is already closed and you are documenting, not deciding.

If nothing was deferred, omit this section.

## Post-Run Reflection

Omit any section below that has nothing to report — silence means no issues. Be specific when noting friction ("task file ambiguous on X" is useful; "it was fine" is not).

- **Friction:** ambiguity in the task, missing context, tool gotchas encountered, points where guidance was thin
- **Project-level suggestions (this repo):** standards gaps, documentation improvements, conventions that should be documented
- **Tooling-level suggestions (claude-dot-files):** workflow prompt improvements, skill gaps, rule refinements that would benefit future runs

If all three sections are empty, state: "No friction or suggestions from this run."