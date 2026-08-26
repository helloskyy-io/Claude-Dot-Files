---
id: C-2xgap6o1
title: Automate the fleet's deployment — server side, edge provisioning, and the git-push-redeploys path that cross-edge CPI depends on
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**Surfaced while settling how CPI crosses the edge/server boundary, and deliberately NOT folded into that component.** The persistent-memory synthesis §13 settles CPI sequencing by having Edge1 make changes and push to git, **which redeploys the server side** — so an automated deployment path is a dependency of a decision already taken, not a nice-to-have. **This is delivery, not memory**, and putting it in a memory component would bury a whole domain inside a feature. **Sized as its own sprint** by the operator: server setup, edge provisioning, and the redeploy trigger are three separate build surfaces. **Placed rather than described in the synthesis**, because a proposal that lives only in a synthesis dies the next time a research cycle rewrites that file — which for this pool is expected rather than hypothetical.

**Source:** persistent-memory-protocol synthesis, 2026-08-12

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
