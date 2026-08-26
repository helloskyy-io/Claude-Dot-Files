---
id: C-8z8v04wk
title: **Build our own CI/CD, initial deployment and its documentation** — the merge gate today runs post-hoc on `push: branches:[main]`, so a red commit lands and is reported afterwards. Branch protection is ruled out permanently (paid feature, `cpi-decisions.md` 2026-08-16). Candidate orchestrators discussed: **Temporal** (already the fleet's direction) or **Argo**. **Scope is wider than the merge gate**: continuous integration, continuous delivery, how a machine is stood up from nothing, and the documentation for both. **Its own feature and its own sprint**, gated on research the operator kicks off after a brainstorm
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: temporal-integration
---

Raised because the ruling existed only in conversation, so every fresh context re-derived the question and re-proposed branch protection. The rejection is logged; **this row is the affirmative half — what we build INSTEAD**

**Source:** operator ruling, restated across ~10 sessions and recorded on no surface until 2026-08-16

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
