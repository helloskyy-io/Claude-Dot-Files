**FILING A CANDIDATE — one file, and the store is `tracked/candidates/`.**

Write **`tracked/candidates/<id>.md`**, using an id from the batch you were offered. **The filename IS the id.** Open it with the six core fields of [Tracked Items Standard §3](../../../../../../docs/standards/documentation/tracked_items_standard.md) in that order, then this store's own three, then the body:

```
---
id: C-a1b2c3d4
title: <one line — the CONSEQUENCE, not the mechanism>
status: open
count: 1
filed: <today, YYYY-MM-DD>
filed_by: <this workflow's name>
component: <the docs/development/<name>/ it belongs to, or blank if you genuinely cannot tell>
size:
decision:
---

<what it is, why it matters, and the proposed action>
```

**`decision` and `size` stay BLANK.** They are `triage-candidates`'s output and blank is the truth: untriaged. **`status` is `open`.** Its terminal values are `adopted` and `rejected`, and neither is yours to write.

**A RESTATEMENT OF AN EXISTING CANDIDATE IS NOT A NEW FILE.** Increment that item's `count` and append a dated line under `## Recurrences` (§3.1). A second item for one proposal costs two triage rulings and buries the recurrence signal, which is the highest-value input triage has.

**One file, no counting, nothing else to update** — which is the point of the store. Filing used to mean appending inside a table block AND hand-correcting two derived totals in prose below it, and a run that did the first and not the second pushed a red suite. There is no table and no prose total now; writing the file is the whole of it.
