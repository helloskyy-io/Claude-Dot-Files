**FILING A CANDIDATE — one file, and the store is `tracked/candidates/`.**

Write **`tracked/candidates/<id>.md`**. **The filename IS the id**, and its shape is `C-` plus **eight random lowercase base36 characters** — `C-a1b2c3d4`. **Mint it yourself: pick eight at random and do not compute one.** There is no next-free to continue from and no maximum to read, which is the whole point — filing is a PURE WRITE, so two runs filing at once cannot collide over an id. *(Some workflows are handed a batch of pre-minted ids; if you were, use those. Most are not, and minting is the normal case rather than the fallback.)* Open it with the six core fields of [Tracked Items Standard §3](../../../../../../docs/standards/documentation/tracked_items_standard.md) in that order, then this store's own three, then the body:

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

**BEFORE YOU WRITE IT, CHECK WHETHER IT IS ALREADY THERE.** Search `tracked/candidates/` for the SUBJECT of your finding — the mechanism, the file, the failing thing — and read the two or three closest items in full. **Search on what it is ABOUT, not on how you worded it:** a title states the CONSEQUENCE, and consequences read alike across genuinely different items. Measured upstream, a title-driven pass nominated four items for merging and **one of the four survived reading the bodies.**

**A RESTATEMENT OF AN EXISTING CANDIDATE IS NOT A NEW FILE.** Increment that item's `count` and append a dated line under `## Recurrences` (§3.1). A second item for one proposal costs two triage rulings and buries the recurrence signal, which is the highest-value input triage has.

**When they are close and you genuinely cannot tell, FILE.** A duplicate costs one triage ruling; a wrong merge buries your finding under somebody else's, where nothing will surface it again. The two errors are not the same size.

**One file, no counting, nothing else to update** — which is the point of the store. Filing used to mean appending inside a table block AND hand-correcting two derived totals in prose below it, and a run that did the first and not the second pushed a red suite. There is no table and no prose total now; writing the file is the whole of it.
