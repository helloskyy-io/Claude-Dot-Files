---
id: I-5nd985bz
title: candidates.md names plan-feature as the writer of `status`, and plan-feature's own prompt fails the run if it writes it, so a landed candidate never closes
status: open
count: 1
filed: 2026-08-18
filed_by: review-pr
repo: claude-dot-files
---

Surfaced by the `plan-feature` run that planned `docs/development/workflow-decomposition` (2026-08-18). Filed as a defect rather than a candidate because nothing new is being *added*: a write path that `candidates.md` documents as live has a named writer that is mechanically forbidden from using it.

## Consequence

`candidates.md` § *Two flags, orthogonal* names the writer of the `status` column:

> **`status`** | `open` · `closed` | **A later process.** `plan-feature` when the item lands in a phase doc; the build that completes it

`plan-feature`'s own shipped prompt forbids exactly that, in two places, and enforces it by snapshot comparison:

- `modules/assistant/plan/plan_feature/prompts/plan_feature.md:27` — the MAY-NOT column: *"Set `decision`, `status`, or another filer's `component` in the candidates file"*
- `:78` — *"All three candidate columns — `decision`, `status`, `component` — are compared cell by cell on every row that already existed."* Writing one **fails the whole run**, including the work the run did correctly.

So the first of the two write paths the file documents **has no writer at all**. A `ship` row whose work lands in a phase doc keeps `status: open` for the rest of the file's life, and `status` is that surface's to-do bit. The queue over-reports outstanding work in exactly the way #69 described for `reject` rows — and #69 is closed, having fixed a different subset while quoting this path as the one that still functioned.

This is the third recorded instance of the class on this one surface: nine `reject` rows closed by hand on 2026-08-10, #69 for the `reject` path, and now the `plan-feature`-on-landing path.

## What I verified

- `docs/standards/architecture/research/candidates.md` § *Two flags, orthogonal* on this branch (unmodified from `main`) — confirms `plan-feature` is the named writer.
- `scripts/workflows/temporal/modules/assistant/plan/plan_feature/prompts/plan_feature.md` lines 27 and 78 — confirms the prohibition and that it is mechanically checked.
- `grep` for a `status: closed` write across `modules/assistant/plan/` — **no writer exists**; the only hit is `plan_activities.py:232`, which *validates* the column's vocabulary rather than writing it.
- `gh issue view 69` → **CLOSED**. Its body is scoped to `reject` rows and explicitly treats `plan-feature`-on-landing as a working path, so this is not an expansion of it and there is nothing open to amend.
- `gh issue list --state open` → #104, #103, #97, #38, #26. None covers which process writes `status`.

## Placement, per Documentation Standard § Deferred Work

- **Question 1 — does it have a done-state today?** Yes. Rule the writer and wire it; nothing waits on an unbuilt system or a named trigger. So it is not a phase checkbox.
- **Question 2 — is it an expansion of something that already exists?** No. #69 is closed and covered a different subset; no open issue or phase item owns the research pool's write paths.

Both questions point away from a checkbox and away from an expansion, which is why this is a new issue rather than a row.

## Proposed next action

Rule **which process closes a landed row**, then make the documentation and the enforcement agree. The ruling is the substance; three defensible answers:

1. **Grant `plan-feature` the `status` cell on rows it lands**, narrowly — `open` → `closed` only, only on rows whose work it just wrote into a phase doc, with the existing snapshot check narrowed to match. Keeps the documented model; costs a carefully-scoped hole in a guard that currently has none.
2. **Move the writer to `triage-candidates` or a dedicated sweep** and correct `candidates.md` to name it. Keeps `plan-feature`'s write boundary absolute, which is the property that makes its run auditable.
3. **State that a landed row is closed by the build that completes it, and delete the `plan-feature` clause.** Cheapest, and honest only if some build actually does it — which is the same unowned-writer question one step further down.

Option 2 is the smallest change that leaves no guard weakened. Whichever is chosen, the fix includes correcting the sentence in `candidates.md` that names a writer that cannot write — that file is under `docs/standards/`, so the edit is human-ratified and rides a PR.



---

*Migrated from `Claude-Dot-Files#110` on 2026-08-26.*
