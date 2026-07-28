Run a standup: sweep the platform's git-native memory surfaces and report what needs attention. **You are a read-only reporter — take NO actions. Do not merge, dispatch, comment, close, or edit anything. Output the standup brief in-chat and stop.**

The platform's memory lives entirely in git surfaces — there are no state files to read and no bookmarks to keep. "Open" IS the to-do bit: an open PR or issue is current by definition. Your job is to route human attention to those surfaces, which are otherwise write-only for anyone who wasn't watching live.

Parse `$ARGUMENTS` for an optional `--since <window>` (e.g. `--since 48h`, `--since 3d`). Default window: **24h**. The window only governs the "recently merged" section; open state is always current.

## Stage 1 — Sweep (dumb, complete enumeration)

Enumerate the repo set: read `gh-monitor.repo-folders` from `~/Repos/claude-dot-files/config.yaml` (or `/opt/skyy-net/claude-dot-files/config.yaml`); fall back to `~/Repos` and `/opt/skyy-net` if unreadable. For each folder, scan its immediate subdirectories for git repos with a GitHub remote. Silently skip folders that don't exist and repos with no GitHub remote.

For each repo (run `gh` from inside the repo dir so it infers the repo, or pass `--repo`), gather EVERYTHING — do not filter here; enumeration is complete and unfiltered, filtering happens in Stage 2:

1. **Open PRs + their machine state.** `gh pr list --state open --json number,title,author,createdAt,headRefName`. For each, read the disposition: `gh pr view <N> --json comments --jq '.comments[].body'` and find the LATEST comment containing a `pr_review:` yaml block. Classify:
   - **`verdict: HOLD`** → a BLOCKER. Attach its `next_steps` VERBATIM (the redispatch `dispatch_context` or the needs-assistance `reframe:`/`bp:`/`recommendation:`). The disposition engine already wrote the action — you deliver it, you do not re-derive it.
   - **`verdict: MERGE`** but PR still open → "ready to merge."
   - **No `pr_review:` block yet** → "awaiting review" with the PR's age.
2. **Open Issues.** `gh issue list --state open --json number,title,labels,body,createdAt,updatedAt`. Each open issue is a pending decision by construction. Two sources feed this surface: planning-STOP outcomes (labels `research-required` / `evidence-faulty`, carrying a `plan_stop:` yaml block — parse it and surface its `next_steps` verbatim, those are the ready-to-fire options) and **deferred work filed by `pr-review`** (carrying evidence, a pinned SHA, and a proposed next action — surface that action verbatim so the operator rules rather than investigates). Report nothing rather than inventing items if the surface is empty.
   - **Flag AGING issues.** Any open issue whose `updatedAt` predates the current window — i.e. it was already open at the last standup and nothing has changed — gets flagged explicitly as aging. That is the exact failure mode this convention exists to prevent, and it means one of two things: the item is **blocked** (and the blocker is the real item to surface), or it **never qualified** in the first place.
3. **Closed-as-invalid since the window** — `gh issue list --state closed --json number,title,closedAt,stateReason`. Surface any issue closed as invalid/not-planned as a **`pr-review` calibration signal**, not as cleanup. A pattern of invalid issues is evidence of a miscalibrated filer and is acted on as a tooling defect. This is the mechanism that makes the queue improve the tool rather than merely hold work — do not suppress or tidy it away.
4. **Recently merged** (within the window). `gh pr list --state merged --json number,title,mergedAt,author` and keep those merged within `--since`. For each, pull the one-line outcome from its reflection/disposition comment if present.

## Stage 2 — Format the brief (this is where filtering happens)

**You know which items are YOURS** — the PRs and issues this session created, dispatched, or is tracking, from your own task list, memory, and dispatch history. Everything else belongs to another PM's lane. No labels or registry tell you this; involvement is known by the actor. Format accordingly:

1. **Since last standup** — merged work from the window, one line each. Outcomes, not narration ("PR #42 merged: etcd-freshness guard added" — not a play-by-play).
2. **Blockers needing THIS session's human** — your-lane HOLD PRs and your-lane open issues, each with its PRE-WRITTEN next-step attached verbatim so the operator decides, never re-derives. This is the section that earns the command.

   **State the disposition obligation on every open issue: an issue MUST NOT survive a standup in the same state.** The four exits are: **resolved now** / **scheduled into existing planning** / **planned as new work** / **closed as invalid**. Prompt the operator to pick one — acknowledging an issue is not ruling on it, and an un-ruled issue is how the previous convention rotted.
3. **Next logical steps** — drawn from your open work's runway sections and this session's task list.
4. **Other PMs' lanes — progress notes ONLY.** One line per foreign PR/issue: "PM2: guide restructure open, N commits since window — theirs." **You MUST NOT frame a foreign item as actionable for this session.** Foreign items are addressed in the window of the PM that created them; cross-lane takeover is the failure mode where the operator loses the thread of who's building what. Note them for awareness; never as your to-do.
5. **Timers / watch-items** — only if this session's memory carries any (optional; omit if none).

## Rules

- Read-only. Every `gh` call is a read (`list`, `view`); never `create`, `merge`, `comment`, `close`, `edit`. If you find yourself about to act, stop — the standup only reports.
- Deliver pre-written actions verbatim; do not re-reason a HOLD's next-step — the disposition engine already did that work and the operator wants it as-written.
- Empty is a valid report. If a surface has nothing, say so in one line; do not manufacture items to fill a section.
- Keep it scannable — this is a standup, not an essay. Outcomes and actions, not process narration.
