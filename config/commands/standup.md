Run a standup: read the standup tracker, sweep the platform's git-native memory surfaces, **bring the tracker up to what is actually true**, and report only what needs a human.

**You take exactly ONE kind of action: updating the standup tracker.** Everything else is read-only — do not merge, dispatch, comment on PRs, close issues, or edit any file. The tracker is the single exception, and it exists because a reconciler that can see an item is finished but cannot say so re-reports that dead item every day forever. The tracker's own rules authorise this: *"Operator and PM sessions only, in the standup"* — this IS the standup.

> **THE BAR THIS COMMAND IS MEASURED AGAINST: every line you render must need something from the operator.** A finished item, a stale reference, an item whose blocker is gone — none of those are standup material. They are tracker maintenance, and you do that maintenance yourself before rendering. **If the operator reads a row and thinks "that's already done", this command has failed**, regardless of how accurate the rest of the brief was.

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


For each repo in the Stage 0 set (run `gh` from inside the repo dir so it infers the repo, or pass `--repo`), gather EVERYTHING — do not filter here; enumeration is complete and unfiltered, filtering happens in Stage 3:

1. **Open PRs + their machine state.** `gh pr list --state open --json number,title,author,createdAt,headRefName`. For each, read the disposition: `gh pr view <N> --json comments --jq '.comments[].body'` and find the LATEST comment containing a `pr_review:` yaml block. Classify:
   - **`verdict: HOLD`** → a BLOCKER. Attach its `next_steps` VERBATIM (the redispatch `dispatch_context` or the needs-assistance `reframe:`/`bp:`/`recommendation:`). The disposition engine already wrote the action — you deliver it, you do not re-derive it.
   - **`verdict: MERGE`** but PR still open → "ready to merge."
   - **No `pr_review:` block yet** → "awaiting review" with the PR's age.
2. **Open Issues.** `gh issue list --state open --json number,title,labels,body,createdAt,updatedAt`. **Drop the `standup-tracker` issue from these results** — it was already rendered in Stage 0, it is not a pending decision, and it must never be aging-flagged. Every OTHER open issue is a pending decision by construction. Two sources feed this surface: planning-STOP outcomes (labels `research-required` / `evidence-faulty`, carrying a `plan_stop:` yaml block — parse it and surface its `next_steps` verbatim, those are the ready-to-fire options) and **deferred work filed by `review-pr`** (carrying evidence, a pinned SHA, and a proposed next action — surface that action verbatim so the operator rules rather than investigates). Report nothing rather than inventing items if the surface is empty.
   - **Flag AGING issues.** Any open issue whose `updatedAt` predates the current window — i.e. it was already open at the last standup and nothing has changed — gets flagged explicitly as aging. That is the exact failure mode this convention exists to prevent, and it means one of two things: the item is **blocked** (and the blocker is the real item to surface), or it **never qualified** in the first place.
3. **Closed-as-invalid since the window** — `gh issue list --state closed --json number,title,closedAt,stateReason`. Surface any issue closed as invalid/not-planned as a **`review-pr` calibration signal**, not as cleanup. A pattern of invalid issues is evidence of a miscalibrated filer and is acted on as a tooling defect. This is the mechanism that makes the queue improve the tool rather than merely hold work — do not suppress or tidy it away.
4. **Recently merged** (within the window). `gh pr list --state merged --json number,title,mergedAt,author` and keep those merged within `--since`. For each, pull the one-line outcome from its reflection/disposition comment if present.

## Stage 2 — UPDATE ALL THREE SOURCES, before you render anything

**Reconciliation without resolution is theatre.** Stage 1 just told you what is no longer true. Fix it AT THE SOURCE now — in all three places — and only then decide what the operator sees.

**The three sources, and what "mark it done" means in each:**

| Source | Done looks like | You write |
|---|---|---|
| **Standup tracker** (issue #26) | the work is finished on a surface you checked | `state: resolved` + `resolved: <today>` |
| **GitHub Issues** | the thing it asked for exists, or the condition it described is gone | **`gh issue close <N> --comment <evidence>`** — a done issue is CLOSED, never reported as done |
| **`direction.md`** | *(you never resolve these)* | nothing — `status` is the operator's alone. You may only correct a row whose stated facts have changed |

**Closing an issue is the point, not a side effect.** An issue reported as "this is already done" every morning is the exact stacking the operator asked this command to stop. If you verified it is done, close it with the evidence in the comment and it never appears again.

For EVERY item in EVERY source, reach one of these — and **write the first three back to the source**:

| Finding | What you write |
|---|---|
| **Demonstrably DONE** — you checked the surface and it is finished | Resolve it / close it, per the table above. **It does not appear in the brief.** One tally line instead. |
| **Blocker is GONE** — the thing it waited on has landed | Clear `blocked on:` and set `state: queued`. It appears, because it may now be ready to authorise. |
| **Materially CHANGED** — still open but the line misdescribes it | Rewrite the line to what is true now. It appears, with what changed. |
| **Still accurate and still open** | Touch nothing. It appears. |
| **Cannot verify** | Touch nothing. It appears, marked unverified — **never assert a state you did not check.** |

**Evidence, per resolution, stated in the tally.** *"T-05 — PR #31 merged, all three tiers exist, 297 tests"* is evidence. *"T-05 looks done"* is not, and resolving on that stamps a lie the pruning rule will later act on.

Then apply the whole updated body with `gh issue edit <N> --body-file <path>`. **Preserve the tracker's structure exactly** — its section order, its per-line fields, `owner:` and `blocked on:` included even when the answer is "none". You are updating values, never reshaping the document.

### THE FILTER — one rule, applied to every row

**A row reaches a table if and only if it is OPEN.** Not open-ish, not recently-closed, not resolved-but-unpruned. Open.

| Source | Reaches the table | Never reaches it |
|---|---|---|
| Tracker | `state:` is `blocked`, `queued` or `in-progress` | `state: resolved` — **at ANY age**, pruned or not |
| Issues | the issue is OPEN right now | closed, at any point, for any reason |
| `direction.md` | `status: open` | `applied` or `rejected` |

**A TIMER whose date is still in the future does not render either.** An item parked on a date — a decision deliberately deferred until enough time passes — needs nothing from the operator until that date is close. Rendering it daily until then is the same noise as rendering a finished item: eleven mornings of a row nobody can act on. **Render a timer only within 3 days of its date, or once it has passed.** Outside that window it is a count in the tally, nothing more.

**`resolved` and `closed` are terminal. A terminal item never appears in a table again**, whether you resolved it thirty seconds ago or it has been sitting stamped for a week waiting out its pruning window. The pruning delay exists so a wrong resolution stays *re-openable on the tracker* — it is not a reason to keep showing the operator finished work.

The only place a completed item is ever mentioned is **the single closing tally line**, as a count and a list of IDs. Never a row, never a table, never a section.

**Also excluded, for a different reason:** anything already rendered under another section. One item, one row, one place.

### Pruning is an action you take, not something you report

Resolved and **≥14 days old** → delete it from the tracker body. Its own rule says *"delete at the first standup ≥14 days after that date"*, and this is that standup. Count it in the tally; do not render it and do not offer it as a candidate.

## Stage 3 — The brief: three tables, then the catchup

**This exists so the operator can plan a day in five minutes.** Not triage a queue, not read a report — decide what to work on. Anything that does not serve that is noise, and noise here costs the operator half an hour of sorting.

> ## ZERO COMPLETED ITEMS. NONE. NOT ONE.
>
> **Every row in every table below is outstanding work.** If it is done, finished, shipped, closed, resolved, superseded, or no longer applicable, it is NOT in a table — it was cleared at the source in Stage 2 and it appears nowhere but the closing tally count.
>
> This is not a preference about tidiness. **A list where half the rows are already done is worse than no list**, because the operator must now verify every row before trusting any of it — which is the exact half-hour this command exists to save. One finished row poisons the whole table.
>
> **Before you render, re-read every row and ask: is this outstanding?** Any row where the honest answer is "no, that landed" comes out.

**You know which items are YOURS** — the PRs and issues this session created, dispatched, or is tracking. No label tells you; involvement is known by the actor.

### Every row carries TWO FULL SENTENCES. This is the rule most often broken — usually by me.

Sentence one: **what it is**, in plain language, assuming the reader has not seen the underlying artifact. Sentence two: **why it matters now** — what it blocks, what it costs, or what decision it is waiting on.

A truncated title is not a description. A restatement of the title in longer words is not a description. **The test: could the operator decide whether to work on this today, without opening anything?** If not, rewrite the row.

Jargon from the artifact means nothing to a reader who did not write it. Say what the thing *is*.

### The four sections, in this order and no others

**1 · Standup tracker** — operating state and continuity. **OPEN ONLY**: `blocked`, `queued`, `in-progress`. No `resolved` line, at any age.

| Item | What it is, and why it matters now | Status |
|---|---|---|

**2 · Open issues** — discrete deferred work. **OPEN ONLY**: if `gh` reports it closed, it is not here.

| # | What it is, and why it matters now | Status |
|---|---|---|

**3 · Direction decisions** — rulings only the operator can make. **OPEN ONLY**: `status: open`, never `applied` or `rejected`.

**A DIRECTION ROW MUST NOT SURVIVE A STANDUP IN THE SAME STATE**, exactly as an issue must not. Three exits, and the third is real:

- **`applied`** — ruled, and the change it implies has landed
- **`rejected`** — ruled against, with the reasoning in the row
- **carried, WITH the specific thing it waits on** — a named spike, a named decision, a dated event. *"Still thinking about it"* is not a blocker and does not qualify

**Say which exit each row is heading for**, and if the answer is carried, name the blocker. These are the only items on the board that nobody but the operator can move, so a row that survives untouched is not deferred work — it is a decision the project is making by default, in the direction of not deciding.

| ID | The ruling, and what it unblocks | Status |
|---|---|---|

**4 · Sprint catchup** — the part that is NOT a queue.

Three short paragraphs, prose, no table:

- **Recently** — what actually landed since the last standup, as outcomes. Not a commit list.
- **Where we are** — which sprint the work is sitting in right now, and what state that sprint is genuinely in.
- **Next** — the two or three moves that follow from where we are. Name them concretely enough to start one.

**This is the section that lets the operator plan rather than triage**, so write it as if handing over to someone who was away for a day.

### Then stop

One closing line: the tally of what Stage 2 cleared, and anything you could not verify. **No summary of the above** — a table plus a paragraph restating it is the failure this whole rewrite exists to end.

**Empty is a valid section.** Say so in one line rather than manufacturing rows.

## Rules

- **You write in exactly TWO places: the standup tracker, and closing a done issue.** `gh issue edit <tracker> --body-file` and `gh issue close <N> --comment <evidence>`. Everything else is a read — never `merge`, never comment on a PR, never edit a file in the repo.
- **Resolve on EVIDENCE, never on impression.** A line moves to `resolved` because you checked the surface and it is done — a merged PR, a file that exists, a passing suite you ran. "It looks finished" is not evidence, and a wrongly-resolved line is worse than a stale one because the stamp makes it invisible.
- **Never set `status: ready`.** That flag is the operator's authorisation and only they set it. You set `state`, and you stamp `resolved:`.
- Deliver pre-written actions verbatim; do not re-reason a HOLD's next-step — the disposition engine already did that work and the operator wants it as-written.
- Empty is a valid report. If a surface has nothing, say so in one line; do not manufacture items to fill a section.
- Keep it scannable — this is a standup, not an essay. Outcomes and actions, not process narration.
