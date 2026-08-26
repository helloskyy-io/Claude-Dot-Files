# Tracked items

Four stores of items that persist across sessions and await a decision or an action.

**The rules are not here.** [Tracked Items Standard](../docs/standards/documentation/tracked_items_standard.md) is binding and owns all of them: identity (§2), the shared core every item opens with (§3), recurrence (§3.1), per-store fields and pruning (§4), and the placement order that makes a tracked store the **last** option rather than the first (§6). That standard is **vendored** from MDC-Master-Planning — amendments go upstream and are re-vendored, never edited here.

**This directory is at the repo root deliberately.** `tracked/issues/` resolves identically in every repo that adopts the contract; nested under a repo-specific directory there would be two implementations by construction.

This file records only what is local: which stores exist here, and who runs their triage.

| Store | Holds | Triage cadence · runner here |
|---|---|---|
| [`issues/`](issues/) | a **defect**, found while building something unrelated to it | sprint close-out · the sprint's owner |
| [`operations/`](operations/) | a note-to-self of something that needs doing | every `/standup` · **the operator — no machine writes here** |
| [`candidates/`](candidates/) | a **proposal** — a capability or improvement to be considered | `triage-candidates` · the planning pass |
| [`standards/`](standards/) | an amendment to a **named** standard, with an actionable anchor | standards pass · **operator** |

**The discriminator is DEFECT vs PROPOSAL** (§1.1), and it predates this standard: with no proposal bucket, every proposal qualified as an issue. Step 1 of that triage is *is it in the current build's scope* — if it is, the build fixes it and nothing is filed.

**`operations/` is human-in-the-loop only** (§1.2). A machine that wants something remembered files an issue, a candidate or a standards amendment — all three have admission tests a machine can apply. *"Someone should look at this"* is not one.

## Reading this is not reading the directory

A folder of forty files is unreadable by hand, and is not meant to be. The store is optimised for **safe concurrent writing**; the rendered view is optimised for reading, is derived from these files, and is **never the source and never edited**.

## What writes here

[`modules/assistant/tracked/tracked_items.py`](../scripts/workflows/temporal/modules/assistant/tracked/tracked_items.py) is the only writer, and it is the contract in code: it mints ids, orders the core fields, refuses a field a store does not define, and refuses the two fields that are the operator's alone (`ready`, `ratification`). `test_tracked_items.py` checks every item on disk against §3 **and** parses the vendored standard to check that module's table against it — so a contract that moves upstream fails here rather than at a dispatch. It caught the `T-` → `O-` rename that way on 2026-08-26, one day after being written.

**Contract version `v1`** (§7).
