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

For each repo in the Stage 0 set (run `gh` from inside the repo dir so it infers the repo, or pass `--repo`), gather EVERYTHING — do not filter here; enumeration is complete and unfiltered, filtering happens in Stage 2:

1. **Open PRs + their machine state.** `gh pr list --state open --json number,title,author,createdAt,headRefName`. For each, read the disposition: `gh pr view <N> --json comments --jq '.comments[].body'` and find the LATEST comment containing a `pr_review:` yaml block. Classify:
   - **`verdict: HOLD`** → a BLOCKER. Attach its `next_steps` VERBATIM (the redispatch `dispatch_context` or the needs-assistance `reframe:`/`bp:`/`recommendation:`). The disposition engine already wrote the action — you deliver it, you do not re-derive it.
   - **`verdict: MERGE`** but PR still open → "ready to merge."
   - **No `pr_review:` block yet** → "awaiting review" with the PR's age.
2. **Open Issues.** `gh issue list --state open --json number,title,labels,body,createdAt,updatedAt`. **Drop the `standup-tracker` issue from these results** — it was already rendered in Stage 0, it is not a pending decision, and it must never be aging-flagged. Every OTHER open issue is a pending decision by construction. Two sources feed this surface: planning-STOP outcomes (labels `research-required` / `evidence-faulty`, carrying a `plan_stop:` yaml block — parse it and surface its `next_steps` verbatim, those are the ready-to-fire options) and **deferred work filed by `pr-review`** (carrying evidence, a pinned SHA, and a proposed next action — surface that action verbatim so the operator rules rather than investigates). Report nothing rather than inventing items if the surface is empty.
   - **Flag AGING issues.** Any open issue whose `updatedAt` predates the current window — i.e. it was already open at the last standup and nothing has changed — gets flagged explicitly as aging. That is the exact failure mode this convention exists to prevent, and it means one of two things: the item is **blocked** (and the blocker is the real item to surface), or it **never qualified** in the first place.
3. **Closed-as-invalid since the window** — `gh issue list --state closed --json number,title,closedAt,stateReason`. Surface any issue closed as invalid/not-planned as a **`pr-review` calibration signal**, not as cleanup. A pattern of invalid issues is evidence of a miscalibrated filer and is acted on as a tooling defect. This is the mechanism that makes the queue improve the tool rather than merely hold work — do not suppress or tidy it away.
4. **Recently merged** (within the window). `gh pr list --state merged --json number,title,mergedAt,author` and keep those merged within `--since`. For each, pull the one-line outcome from its reflection/disposition comment if present.

## Stage 2 — Format the brief (this is where filtering happens)

**You know which items are YOURS** — the PRs and issues this session created, dispatched, or is tracking, from your own task list, memory, and dispatch history. Everything else belongs to another PM's lane. No labels or registry tell you this; involvement is known by the actor. Format accordingly:

1. **Where we left off — the standup tracker.** The opening section, ahead of everything else. Render the tracker's sections in ITS order (`BLOCKED` → `READY` → `IN FLIGHT` → `RESOLVED`), lines verbatim with their `owner:` / `blocked on:` fields intact.

   **The obligation is per LINE, not on the document.** "Reviewed the tracker" is not a disposition — that is the exact non-attendance failure that killed the loose-ends convention, relocated one level up: a document nobody rules on, only acknowledges. For every unresolved line under `BLOCKED` / `READY` / `IN FLIGHT`, prompt the operator for one of three:

   - **acted on** — moves to `RESOLVED` with a date
   - **re-stated** — with what changed
   - **explicitly carried** — WITH the reason it cannot move. "Still carried" alone is not a reason.

   **Then surface the pruning obligation.** Flag every `RESOLVED` item dated **≥7 days ago** for deletion. Items are meant to *flow through* this document — **a tracker that grows month over month is failing**, and prompting for the prune is what keeps that true. You flag; the operator prunes.

2. **Since last standup** — merged work from the window, one line each. Outcomes, not narration ("PR #42 merged: etcd-freshness guard added" — not a play-by-play).
3. **Blockers needing THIS session's human** — your-lane HOLD PRs and your-lane open issues, each with its PRE-WRITTEN next-step attached verbatim so the operator decides, never re-derives. This is the section that earns the command.

   **State the disposition obligation on every open issue: an issue MUST NOT survive a standup in the same state.** The four exits are: **resolved now** / **scheduled into existing planning** / **planned as new work** / **closed as invalid**. Prompt the operator to pick one — acknowledging an issue is not ruling on it, and an un-ruled issue is how the previous convention rotted.
4. **Next logical steps** — drawn from your open work's runway sections and this session's task list.
5. **Other PMs' lanes — progress notes ONLY.** One line per foreign PR/issue: "PM2: guide restructure open, N commits since window — theirs." **You MUST NOT frame a foreign item as actionable for this session.** Foreign items are addressed in the window of the PM that created them; cross-lane takeover is the failure mode where the operator loses the thread of who's building what. Note them for awareness; never as your to-do.
6. **Timers / watch-items** — only if this session's memory carries any (optional; omit if none).

## Rules

- Read-only. Every `gh` call is a read (`list`, `view`); never `create`, `merge`, `comment`, `close`, `edit`. If you find yourself about to act, stop — the standup only reports.
- **This applies to the standup tracker in particular, where the temptation is strongest.** You have just enumerated its stale lines and its prunable ones; do not edit it. Updates happen in the standup conversation, by the operator and the PM session — never by an autonomous dispatch, and never by this command.
- Deliver pre-written actions verbatim; do not re-reason a HOLD's next-step — the disposition engine already did that work and the operator wants it as-written.
- Empty is a valid report. If a surface has nothing, say so in one line; do not manufacture items to fill a section.
- Keep it scannable — this is a standup, not an essay. Outcomes and actions, not process narration.
