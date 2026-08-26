---
id: C-oapy6vg8
title: Derive the hand-maintained control sets instead of maintaining them — adding one workflow required five hand-edits across `test_authorization_is_observed`, `test_disappearance_is_observed` (x2), `test_pr_url_address` and the repo-root census
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

Each set is deliberate and each says so in its own failure message — *a THIRD workflow arriving is expected to fail here once, on purpose* — and that design is right. **The cost is that it rises linearly with fleet size, and every edit is a place a future author widens the set without checking coverage.** The question is whether the sets can be derived while keeping the deliberate fail-on-arrival property.

**Source:** PR #92 `plan-feature` reflections (3 passes, 2026-08-14/15)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
