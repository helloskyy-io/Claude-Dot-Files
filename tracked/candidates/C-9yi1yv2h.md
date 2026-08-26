---
id: C-9yi1yv2h
title: **A research paper whose `Feeds:` milestone was DELETED has no defined state, so it stays `current` while pointing at nothing and no reader can tell a live destination from a dissolved one** — the Research Standard defines `retired` for a paper that is no longer evidence and §84 bars a retired paper from being cited as current; neither describes a paper whose EVIDENCE is still good and whose DESTINATION is gone
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: temporal-integration
---

**Surfaced correctly and placed by nobody, which is why this row exists.** The correction pass classified it as a PROPOSAL rather than a defect, rejected `retired` as the wrong instrument with the §84 citation, and said plainly it was barred from placing it — every step correct under its write boundary, which forbids editing a standard. **`review-pr` then held the PR, because a correctly-surfaced proposal nobody places is indistinguishable at merge from one nobody had.** **What breaks without it:** five of this pool's six papers had a dissolved `Feeds:` target in one week. A planner reading one cannot tell whether the destination moved, was renamed, or was abandoned, and the paper reads as current evidence for work that may no longer be planned. **Not a defect** — nothing behaves wrongly; the standard is silent, which makes it capability that would be ADDED. **Done-state today: yes** — one clause naming the state and what a reader does with it. **Distinct from C-hdme5l4k** (corrections tracing into the PR body) **and from the `Feeds:`-liveness guard in PR #127**, which checks that a target RESOLVES and says nothing about what to do when it legitimately cannot.

**Source:** PR #122 (`research-verify`, correction pass)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
