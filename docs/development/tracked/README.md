# Tracked items

Four stores of items that persist across sessions and await a decision or an action.

**The rules are not here.** [Tracked Items Standard](../../standards/documentation/tracked_items_standard.md) is binding and owns all of them: identity (§2), the shared core every item opens with (§3), recurrence (§3.1), per-store fields and triage (§4), and the placement order that makes a tracked store the **last** option rather than the first (§6). That standard is **vendored** from MDC-Master-Planning — amendments go upstream and are re-vendored, never edited here.

This file records only what is local: which stores exist here, and who runs their triage.

| Store | Holds | Triage cadence · runner here |
|---|---|---|
| [`issues/`](issues/) | deferred work with a clean done-state and a proposed action | sprint close-out · the sprint's owner |
| [`tracker/`](tracker/) | operating state and continuity — live work with no single done-state | every `/standup` · whoever runs it |
| [`research/`](research/) | a question evidence could settle, awaiting triage into a research cycle | `triage-candidates` · the planning pass |
| [`standards/`](standards/) | a proposed amendment to a **named** standard, with an actionable anchor | standards pass · **operator** |

## Reading this is not reading the directory

A folder of forty files is unreadable by hand, and it is not meant to be read by hand. The store is optimised for **safe concurrent writing**; the rendered table is optimised for reading, is derived from these files, and is **never the source and never edited**.

## What writes here

[`modules/assistant/tracked/tracked_items.py`](../../../scripts/workflows/temporal/modules/assistant/tracked/tracked_items.py) is the only writer, and it is the contract in code: it mints ids, orders the core fields, refuses a field a store does not define, and refuses the two fields that are the operator's alone (`ready`, `ratification`). `test_tracked_items.py` checks every item on disk against §3 **and** checks that module's table against the vendored standard, so a contract that moves upstream fails here rather than at a dispatch.

**Contract version `v1`** (§7).
