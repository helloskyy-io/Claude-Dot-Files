---
id: C-0us6e85c
title: A run's worktree cannot see `main`, so a conflict resolved on `main` reappears on the next run and nothing tells the operator they fixed it on the wrong side
status: open
count: 1
filed: 2026-08-28
filed_by: review-pr
component: 
size: 
decision: 
---

**PROPOSAL — warn at dispatch time when a run is about to edit a file `main` has changed since the branch was cut.**

**Reported by MDC PM3 after three recurrences of one finding on PR #171.**

`sprints.md` mirrors a figure `roadmap.md` owns. `plan-sprint` writes that mirror **from a worktree that cannot see `main`**. PM3 resolved the resulting conflict *on `main`*; it reappeared **37 minutes later**; resolved it again; it reappeared.

**It converged only when resolved on the BRANCH** — *the branch is the source, `main` is the mirror*. That is a property of the dispatch topology, and PM3 notes `review-pr`'s own reflection recorded that there is **nowhere structural to put it**, so the explanation lived in prose an operator might not read. Its `needs-assistance` shape cannot express *"you fixed it in the wrong place."*

**We have the same topology.** Every child cuts a worktree from the PR branch and none of them reads `main`.

**Consequence:** a conflict resolved on the wrong side reappears on the next run, indefinitely, and the operator has no signal distinguishing it from a tool that keeps regressing.

**Remedy:** one line of dispatch-time output — *"`docs/development/sprint.md` has changed on `main` since this branch was cut; resolve on the BRANCH, not on `main`."* PM3's assessment: it would have prevented three recurrences.
