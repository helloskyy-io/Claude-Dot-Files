---
id: S-5jo0ecfg
title: The binding Architecture Standard routes defects and proposals to two surfaces that no longer exist, and never names the standards store
status: open
count: 1
filed: 2026-08-26
filed_by: review-pr
target: docs/standards/architecture/architectural_standard.md
anchor: "§4 Memory — the Surface table, and its opening line \"Open is the to-do bit\""
---

**Surfaced on PR #141 (`plan-verify: size and judge memory-management-framework`), which did not touch this file.** The producing run reported the underlying disagreement as MMF roadmap candidate 8 and correctly declined to write a binding standard; candidate 8 has no home in `tracked/standards/` and none in the Persistent Memory Protocol roadmap, so this intake is that home.

## Consequence

`architectural_standard.md` § 4 Memory is marked **(binding)** and is the document `finding-routing.md` cites for the surface set. Its table currently reads:

| Surface | Holds |
|---|---|
| PR threads | change-outcomes, decision logs, disposition rulings |
| **GitHub Issues** | defects |
| Standup tracker | continuity |
| **`candidates.md`** | proposals |

**Two of those four surfaces no longer exist.**

- **GitHub Issues** were retired at `b874e79` (*"sweep: retire the GitHub-Issues instructions, all thirteen files"*). The vendored [Tracked Items Standard § 5](../../docs/standards/documentation/tracked_items_standard.md) is titled *"GitHub Issues are retired (binding)"*. Two binding documents now say opposite things about where a defect goes.
- **`candidates.md`** was deleted at `91925af` (*"flip: the candidates store IS `tracked/candidates/`, and the table is deleted"*). The path in the standard resolves to nothing.

The store set is now `tracked/issues/`, `tracked/candidates/`, `tracked/standards/` and `tracked/operations/` — and `tracked/standards/`, the store this very item lands in, **has no row in § 4 at all**.

So an actor — human or autonomous — that follows the binding Architecture Standard files a defect onto a retired substrate and a proposal into a deleted file, and never learns that a standards-amendment store exists. That is a routing failure in the one document whose stated job is to name the surface set.

**The section's opening line is stale by the same change and it is the same edit, not a second one.** § 4 opens *"No state files, no bookmarks. Open is the to-do bit."* stated without exception. The tracked stores' to-do bit is a `status:` column, not a GitHub `open` state — so the clause is false for three of the four live stores. It is listed here rather than separately because the surfaces are the reason the clause needs its exception: rebinding the table without restating the to-do bit leaves § 4 self-contradictory.

## What I verified

Reviewed at `origin/main` = `6533983`, and `HEAD..origin/main` is empty, so the branch under review is current.

- `sed -n '49,76p' docs/standards/architecture/architectural_standard.md` — the table above, verbatim, under a `(binding)` heading.
- `find . -name 'direction.md' -not -path './.git/*'` → no results. `grep -n "direction.md" docs/standards/architecture/architectural_standard.md` → exit 1.
- `ls tracked/` → `issues/ candidates/ standards/ operations/` all populated.
- **Absence of an existing item, by two independent checks:** `grep -rn "architectural_standard" tracked/` returns only two incidental mentions inside candidate bodies (`C-523klr8n` quoting `:46`, `C-ocjitn3a` referencing § 3's `author ≠ judge`) — neither is an amendment to § 4. And enumerating `^target:` across `tracked/standards/` returns seven items, none targeting this file.
- `docs/development/persistent-memory-protocol/roadmap.md` § *Standards-amendment candidates* carries eight entries (it declares itself *"the writer for these entries"*); none is against § 4. MMF roadmap candidate 4 **is** carried there as entry 5 — candidate 8 is not.

## Proposed action

Rebind § 4's table to the four `tracked/` stores plus PR threads and the standup tracker, and qualify the opening line so it admits a `status:` column as a to-do bit alongside GitHub `open`. One edit, one section, human-ratified.

**Root cause worth recording with the fix:** the surface roster is *restated* in at least three documents rather than derived or cited — this standard, `docs/guide/memory-model.md` (rebound at `6533983`) and `docs/development/sprint.md`'s Memory Management Framework prose (still stale). `C-523klr8n` is open against exactly that mechanism and cites `architectural_standard.md:46`'s own principle, *"a constant restated in two places diverges silently"*. **This is a fresh occurrence of that candidate's mechanism and its `count` should be incremented when this is triaged.** The generalisable scoping rule, which the PR #141 run wrote in its own reflection: *a store rename sweeps every document that NAMES the store, not every document that INSTRUCTS a write to it.*

*Filed via intake `#142` and harvested on 2026-08-26.*
