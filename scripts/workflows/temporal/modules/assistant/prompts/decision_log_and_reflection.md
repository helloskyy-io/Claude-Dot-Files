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
- **a placement YOU made in THIS PR's diff** -> verify it on your BRANCH, and say so: `Verified by: <command> on this branch; lands at merge`. **This is the one legitimate exception to the default-branch rule and it exists because another rule mandates it** — `finding-routing.md` §4 requires a PRODUCING run to place its own proposal in its own PR, which by construction is not on the default branch yet. Read literally, the two rules point opposite ways and a run trying to obey both has to invent a resolution. **State the merge caveat plainly** — it is a durable file edit whose pointer only becomes true at merge, and hiding that is how a deferral evaporates when a PR is closed unmerged and quote the line you found
- a file/doc/phase-doc entry -> Read or Grep the live file on the DEFAULT branch (not your worktree — your branch's copy may contain an edit that never merges)
- a follow-up PR -> `gh pr view <N>` — confirm it is open and in scope

**Write what you observed, not that you checked.** 'Verified by: gh issue view 230 -> OPEN, body covers the Python-tier gate' is an attestation. 'Verified present' is a claim about yourself, and it is the exact shape that has shipped false twice.

**If you cannot verify it, you may not defer to it.** Fix the item, or SURFACE it plainly with no pointer at all. An honest 'no home for this' is worth more than a plausible pointer to nothing — and a naked surfaced item gets picked up downstream, while a laundered one gets filed away as handled.

**FIRST, BEFORE PLACEMENT — is this a DEFECT or a PROPOSAL?** [Architecture Standard § 4 Memory](../../../../../docs/standards/architecture/architectural_standard.md) binds this; apply it rather than re-deriving it.

- **DEFECT** — something already built or already decided behaves wrongly, or a decision the research and planning do not supply is now blocking. Continue below.
- **PROPOSAL** — capability that does not exist and would be *added*. It belongs in **`candidates.md`**, never an Issue, whatever its done-state looks like. Bias here when a finding reads either way.

  **PLACE IT YOURSELF, IN THIS PR — do not merely surface it.** Append a row to `docs/standards/architecture/research/candidates.md` with the next free `C-NNN` id, the finding, its source, `status: open`, and a Note carrying your evidence. **Leave `decision` BLANK** — blank means untriaged, which is the truth, and `decision` is `triage-candidates`'s output alone.

  **Name the `component` this candidate belongs to — on the row YOU are appending, and on no other.** An existing `docs/development/<name>/` if it extends one, a new name if it does not. **A blank means nothing is scaffolded for it.** You are the one who knows: you have just written the proposal, and anything downstream would be guessing from a one-line summary. A blank is an unanswered question rather than an error, so leave it blank rather than inventing a name you are not sure of. **Do not fill in the cell on a row somebody else filed** — that is guessing from a summary, it is checked cell-by-cell on every pre-existing row, and it does not stay a guess: `plan-candidates` turns a component name into a committed `docs/development/<name>/`.

  **Why you and not the reviewer** ([`finding-routing.md`](../../../../../docs/standards/finding-routing.md) § 4): a file surface needs a commit and a push, and the reviewer is decide-only — it structurally cannot write there. **And the disposal-chute argument does not reach a proposal:** it forbids filing DEFECTS you could have fixed, because that offloads your own scope. A proposal is capability that does not exist, so it was never your scope and cannot be offloaded. **You still do not decide where it belongs in the plan** — sprint, phase or nothing is separate triage with its own criteria.

  **A proposal you surface without placing dies at merge.** That is measured, not cautionary: three correctly-classified proposals were left in a PR body and `/standup` does not sweep merged PR bodies.

  **UNLESS YOUR OWN WRITE BOUNDARY FORBIDS IT — then SURFACE the proposal in your PR body and place nothing.** This fragment is injected into every producing workflow, and three of them are explicitly barred from this file: `research-write` and `research-refresh` at component altitude (*"Do NOT write it into the product pool's `direction.md` or `candidates.md`"*) and `research-write-minor` (*"never touch `candidates.md` or `direction.md`"*, and a binding clause telling it to disobey any dispatch instructing it to file anything outside its own research directory). Without this sentence those runs receive two binding instructions that cannot both be followed, and the one they are told to prefer is the one that makes the proposal disappear. **Your write boundary wins; say in the PR body that you were barred from placing, so the reader knows the surfaced item still needs a home.**

**And cluster YOUR OWN findings before considering any of them separately.** Findings sharing a file, a function, a subsystem, or one remedy are **ONE item**. Measured: four separate Issues against one file, from one pass, each individually correct.

**BEFORE you pick a home, answer the two PLACEMENT questions** (`engineering-quality.md` § *A deferral is PLACED*), in this order and from the candidate's BODY rather than its title:

1. **Does it have a done-state TODAY?** If its remedy waits on a named trigger — a second adopter, a service reaching a date, a framework arriving — it is a **checkbox on the phase that owns that trigger**, not an issue. An issue filed for trigger-gated work sits open and unactionable until someone re-reads it.
2. **Is it an EXPANSION of something that already exists?** An open issue, a phase item, a CPI entry that covers the same ground gets **amended**, not duplicated. Two issues describing one thing is how a queue stops being read.

**Only what fails BOTH becomes a new issue, and the default is against filing.** A new issue is the last option, not the first — measured: applying these questions to one run's candidates took its filings from six to zero without losing a single item.

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