---
id: C-mxzcul3x
title: plan-new` greenfield — handle `git init`, initial commit and remote setup rather than requiring a repo
status: rejected
count: 1
filed: 2026-08-26
filed_by: triage-candidates
decision: reject
---

found during the 1Password vault manager test, 2026-04-11. **Reject: delivered.** `scripts/helpers/init-project.sh` runs `git init --initial-branch=main`, makes the initial commit and creates the GitHub remote; `plan-new` correctly requires an existing repo

**Source:** sprint plan, Future Idea I

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
