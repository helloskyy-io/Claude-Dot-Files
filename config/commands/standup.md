Run a standup: read the standup tracker, sweep the platform's git-native memory surfaces, and report what needs attention. **You are a read-only reporter — take NO actions. Do not merge, dispatch, comment, close, or edit anything — the standup tracker included. Output the standup brief in-chat and stop.**

The platform's memory lives entirely in git surfaces — there are no state files to read and no bookmarks to keep. "Open" IS the to-do bit: an open PR or issue is current by definition. Your job is to route human attention to those surfaces, which are otherwise write-only for anyone who wasn't watching live.

Parse `$ARGUMENTS` for an optional `--since <window>` (e.g. `--since 48h`, `--since 3d`). Default window: **24h**. The window only governs the "recently merged" section; open state is always current.

## Stage 0 — Repo set, then the standup tracker

**Enumerate the repo set.** Read `gh-monitor.repo-folders` from `~/Repos/claude-dot-files/config.yaml` (or `/opt/skyy-net/claude-dot-files/config.yaml`); fall back to `~/Repos` and `/opt/skyy-net` if unreadable. For each folder, scan its immediate subdirectories for git repos with a GitHub remote. Silently skip folders that don't exist and repos with no GitHub remote. Stage 1 reuses this set.

**Then find the standup tracker — before sweeping anything.** It is a GitHub issue titled `standup-tracker`, discovered **by title, never by number**, so it stays portable across planning repos:

```
gh issue list --repo <each repo> --state open --search "standup-tracker in:title" --json number,title,body,updatedAt
```

Read it first because **it is the frame the sweep lands inside** — a PR the sweep reports as "open" reads completely differently once the tracker says it is `IN FLIGHT` and what the next move on it was. If more than one repo has a tracker, render each under its repo name. If none exists, say so in one line and continue; most repos won't have one.

### What the tracker is, and why it is not an issue

It is a **third kind of memory** — not a third location. GitHub Issues are the substrate because the document is edited daily by several sessions and one API call beats a branch and a merge conflict on the artifact least able to afford being stale. The semantics are its own:

| Surface | Holds | Lifecycle |
|---|---|---|
| Sprint | planned development work | items close; the plan persists |
| Issue | one discrete unit of deferred work | filed → dispositioned → **closed** |
| **Standup tracker** | operating state, next moves, continuity | **never closes**; items are **pruned** |

It exists because live-operational work — a multi-day vendor migration, an incident — belongs to no other surface: not development, so not a sprint item; no single done-state, so not an issue. Without it that work lives in session context and dies at a session boundary.

**Three consequences, all binding:**

1. **EXCLUDE it from the Stage 1 open-issue enumeration.** It must not appear twice, and it must **never be aging-flagged** — a permanent artifact is not a stalled one. The anti-rot flag exists for issues that should have closed; firing it on the one document designed to persist is backwards.
2. **Never apply the issue-disposition obligation to it.** That obligation binds a *container* that is supposed to close. The tracker's obligation binds each *line* (below). Do not merge the two taxonomies — forcing the tracker into the issue enum would require inventing a fifth exit for *pruned*, which is a schema violation, not a convenience.
3. **Render its structure; do not re-derive it.** The tracker's sections are **readiness states** — an item moves `BLOCKED` → `READY` → `IN FLIGHT` → `RESOLVED` — and that ordering is exactly how an operator triages: *what can I actually do right now.* Preserve the order and preserve each line's fields verbatim, including `owner:` and `blocked on:` even when the answer is "none". Those fields are deliberate forward compatibility: an agent asking *"what is ready, and which of it is mine?"* answers it from `READY` + `owner:` with no schema change. **If you normalise or reformat the sections, that property is lost.** The tracker's body documents its own format — treat the body as the shape-of-record rather than working from any spec here.

## Stage 1 — Sweep (dumb, complete enumeration)

**Read `docs/standards/architecture/research/direction.md` if it exists.** It holds recommendations about what the project *believes* — a differentiator overstated, a claim resting on an unnamed assumption — surfaced by research and **awaiting the operator's ruling**. Every row with `status: open` is a decision only the human can make. If the file is absent, say so in one line and move on.


For each repo in the Stage 0 set (run `gh` from inside the repo dir so it infers the repo, or pass `--repo`), gather EVERYTHING — do not filter here; enumeration is complete and unfiltered, filtering happens in Stage 2:

1. **Open PRs + their machine state.** `gh pr list --state open --json number,title,author,createdAt,headRefName`. For each, read the disposition: `gh pr view <N> --json comments --jq '.comments[].body'` and find the LATEST comment containing a `pr_review:` yaml block. Classify:
   - **`verdict: HOLD`** → a BLOCKER. Attach its `next_steps` VERBATIM (the redispatch `dispatch_context` or the needs-assistance `reframe:`/`bp:`/`recommendation:`). The disposition engine already wrote the action — you deliver it, you do not re-derive it.
   - **`verdict: MERGE`** but PR still open → "ready to merge."
   - **No `pr_review:` block yet** → "awaiting review" with the PR's age.
2. **Open Issues.** `gh issue list --state open --json number,title,labels,body,createdAt,updatedAt`. **Drop the `standup-tracker` issue from these results** — it was already rendered in Stage 0, it is not a pending decision, and it must never be aging-flagged. Every OTHER open issue is a pending decision by construction. Two sources feed this surface: planning-STOP outcomes (labels `research-required` / `evidence-faulty`, carrying a `plan_stop:` yaml block — parse it and surface its `next_steps` verbatim, those are the ready-to-fire options) and **deferred work filed by `review-pr`** (carrying evidence, a pinned SHA, and a proposed next action — surface that action verbatim so the operator rules rather than investigates). Report nothing rather than inventing items if the surface is empty.
   - **Flag AGING issues.** Any open issue whose `updatedAt` predates the current window — i.e. it was already open at the last standup and nothing has changed — gets flagged explicitly as aging. That is the exact failure mode this convention exists to prevent, and it means one of two things: the item is **blocked** (and the blocker is the real item to surface), or it **never qualified** in the first place.
3. **Closed-as-invalid since the window** — `gh issue list --state closed --json number,title,closedAt,stateReason`. Surface any issue closed as invalid/not-planned as a **`review-pr` calibration signal**, not as cleanup. A pattern of invalid issues is evidence of a miscalibrated filer and is acted on as a tooling defect. This is the mechanism that makes the queue improve the tool rather than merely hold work — do not suppress or tidy it away.
4. **Recently merged** (within the window). `gh pr list --state merged --json number,title,mergedAt,author` and keep those merged within `--since`. For each, pull the one-line outcome from its reflection/disposition comment if present.

## Stage 2 — Format the brief (this is where filtering happens)

**You know which items are YOURS** — the PRs and issues this session created, dispatched, or is tracking. No label tells you; involvement is known by the actor. Everything else is another lane.

### RECONCILE BEFORE YOU RENDER — this is not optional

**A standup that reports state it did not verify trains the operator to distrust it.** Before rendering any line, check it against the surfaces you just swept:

- A tracker item pointing at a PR — **is that PR still open?** Merged or closed means the line is stale.
- A tracker item pointing at an issue — **is it still open?**
- A tracker item describing work — **did commits land in the window that contradict it?**

**Report the discrepancy, never the stale line.** *"T-12 says the port is step 2 of three; 22 commits since the last standup completed it"* is the useful output. Rendering T-12 verbatim is not. If you cannot verify a line, **say you could not** — never assert its state either way.

### OUTPUT IS TABLES

**Every section is a table.** Prose only where a table genuinely cannot carry the meaning — a table plus a paragraph restating it is the failure this rule exists to stop. **Each row carries at least two full sentences** of description: what it is, and why it matters now. A truncated title is not a description, and the operator should never have to open a file to know whether a row needs them.

Render these, in order, each as its own table:

**1 · Where we left off — the standup tracker.** Sections in ITS order (`BLOCKED` → `READY` → `IN FLIGHT` → `RESOLVED`), fields intact including `owner:` and `blocked on:`. Every unresolved line ends in **acted on** (moves to `RESOLVED` with a date) / **re-stated** (with what changed) / **explicitly carried** (WITH the reason it cannot move — "still carried" is not a reason). Flag every `RESOLVED` item dated **≥14 days ago** for pruning; you flag, the operator prunes.

**2 · Sprint items.** From `sprint.md`. What each sprint is, and its state right now — reconciled, not as written.

**3 · Open issues.** Every one. **An issue MUST NOT survive a standup in the same state** — the four exits are *resolved now* / *scheduled into existing planning* / *planned as new work* / *closed as invalid*. Acknowledging an issue is not ruling on it.

**4 · Direction decisions awaiting the operator.** From `direction.md`, every row with `status: open`. **These are the items nobody else can rule on** — they change what the project believes, and no amount of further work substitutes for the decision. Omit the table entirely if the file has no open rows; do not render an empty one.

**5 · Since last standup.** Merged work in the window, outcomes not narration.

**6 · Blockers needing this session's human.** Your-lane HOLD PRs with their PRE-WRITTEN next-step attached **verbatim** — the disposition engine already wrote it; you deliver it, you never re-derive it.

**7 · Other lanes — awareness only.** One row each. **You MUST NOT frame a foreign item as actionable for this session.** Cross-lane takeover is how the operator loses the thread of who is building what.

**8 · Timers / watch-items.** Only if any exist.

**Empty is a valid report.** If a surface has nothing, say so in one line rather than manufacturing rows to fill a table.

## Rules

- Read-only. Every `gh` call is a read (`list`, `view`); never `create`, `merge`, `comment`, `close`, `edit`. If you find yourself about to act, stop — the standup only reports.
- **This applies to the standup tracker in particular, where the temptation is strongest.** You have just enumerated its stale lines and its prunable ones; do not edit it. Updates happen in the standup conversation, by the operator and the PM session — never by an autonomous dispatch, and never by this command.
- Deliver pre-written actions verbatim; do not re-reason a HOLD's next-step — the disposition engine already did that work and the operator wants it as-written.
- Empty is a valid report. If a surface has nothing, say so in one line; do not manufacture items to fill a section.
- Keep it scannable — this is a standup, not an essay. Outcomes and actions, not process narration.
