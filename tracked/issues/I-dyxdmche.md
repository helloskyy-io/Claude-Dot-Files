---
id: I-dyxdmche
title: A ratified `ship` candidate lost its milestone when Fleet Reliability dissolved, so nothing in the plan will ever pick it up
status: open
count: 1
filed: 2026-08-19
filed_by: review-pr
repo: claude-dot-files
---

**Found during `review-pr` disposition pass 1 on PR #122.** Pinned to `origin/main` at `4d6512753259cb563d2fe0db70699459b0ab54bb`.

## The consequence

`C-011` in `candidates.md` (the table this store replaced on 2026-08-26) (line 99) is a **ratified `ship` decision**:

> `| C-011 | Ship three cheap guards: credential expiry, false completion, safety-hook wiring test (~9 h) | | fleet_failure_modes.md §7 | ship | open | **Ship:** three things built with a stated cost. Placed as a *Fleet Reliability* milestone |`

Its Note names its placement — *"Placed as a Fleet Reliability milestone."* **That milestone no longer exists.** The `Fleet Reliability` sprint section dissolved on 2026-08-19; its research pool moved to `docs/development/temporal-integration/research/`, three of its milestones moved into other sections, and *"Three cheap guards"* was **dropped, not merged**:

```
$ grep -ni "cheap guard" docs/development/sprint.md
(no match)
```

So a decision the operator already ruled `ship` (~9 h of costed work) now has **no carrier anywhere in the plan**. It was never reversed — it was orphaned. `status: open` reads as outstanding work that something will eventually pick up; nothing will, because the milestone that would have picked it up was deleted.

Two research papers still write to it and are stranded with it — `credential_expiry_detection.md` and `false_completion_detection.md`, both `current`, both critic-verified PASS-WITH-FIXES, both carrying `Feeds:` lines that name the dissolved milestone at `docs/development/sprint.md:180` (a blank line today).

## Evidence

| Claim | Verified how |
|---|---|
| `C-011` is `decision: ship`, `status: open`, Note names a Fleet Reliability milestone | `git show origin/main:docs/standards/architecture/research/candidates.md \| grep -n C-011` → line 99 |
| No "cheap guards" milestone survives | `grep -ni "cheap guard" docs/development/sprint.md` → no match |
| The two papers still point at it | `grep -n -A3 "^Feeds:" docs/development/temporal-integration/research/raw/{credential_expiry,false_completion}_detection.md` → both cite `sprint.md:180` + "the fleet-reliability phase doc (not yet written)" |
| `sprint.md:180` is not that milestone | `sed -n '180p' docs/development/sprint.md` → blank line inside the Temporal Integration section |
| Not already tracked | `gh issue list --state open --limit 60` → nothing covers it. #38 is the *product* pool (`docs/standards/architecture/research/`), a different directory and a different defect; #97 is standards-amendment entries in a retired roadmap |

## Proposed next action

One ruling, with a done-state today:

- **Re-carry it** — re-create a "three cheap guards" milestone under whichever sprint section now owns unattended-run safety (`Autonomous Operation` is the natural reader; its two sibling candidates C-012 and C-029 landed at `sprint.md:243`–`:244`), and update `C-011`'s Note to name it; **or**
- **Retire it** — record that the guards work was intentionally dropped with Fleet Reliability, set `C-011`'s `status` accordingly, and mark the two papers superseded.

Either ruling also settles where the two stranded papers live. Their *directory* is not part of the ruling — Research Standard §1 and `docs/standards/research/README.md` make a component pool's location derivable (`docs/development/<phase>/research/`, "no question about which phase a pool belongs to"), so once the milestone has a section the papers follow it mechanically.

**Sibling candidates worth checking in the same sitting** (same dissolution, same stale Note, but their milestones *survived* so they are not orphaned): `C-012` ("build the blocked-work notifier" → `sprint.md:244`) and `C-029` ("three-legged liveness taxonomy" → `sprint.md:243`) both still read *"Placed as a Fleet Reliability milestone."*

**Same class as #97** (an item's carrier was retired and the item was not carried forward), different artifact and different items — filed separately so each can be ruled on its own.

---

*Filed by `review-pr` under its deferred-work filing authority. Both producing runs on PR #122 surfaced this and neither could place it: the authoring run's deferral pointed at `synthesis.md § Housekeeping` in its own PR (a file the Research Standard rewrites every cycle), and the `research-verify` run stated plainly that this half had no home.*



---

*Migrated from `Claude-Dot-Files#125` on 2026-08-26.*
