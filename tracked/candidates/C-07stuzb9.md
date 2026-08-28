---
id: C-07stuzb9
title: Roadmap prose and phase-doc titles still cite phases by number with no check, so one PR added 125 such lines while its headings — the half a parser reads — stayed clean
status: open
count: 1
filed: 2026-08-28
filed_by: review-pr
component: 
size: 
decision: 
---

**PROPOSAL — a gate for Documentation Standard rule 4 in prose, not just in headings.**

**Measured on PR #145: 125 added lines cite a phase by number, and 0 headings do.** Rule 8's heading shape is read by `phase_sizing`, so it was obeyed exactly. Rule 4 — *"a phase is cited BY NAME, never by number"* — has no reader, and was violated across the same diff by the same run, which `review-pr` confirmed could have read the rule (ancestry check).

**The pattern is the finding, not the count:** *the rule with a parser behind it held; the rule without one drifted, in one document, in one pass.*

**`plan-verify` independently reported that this generalises** — *"this component is one of several whose roadmap headings are converted to names while its prose and phase-doc titles are not."* Rule 4 makes conversion opportunistic, so the mixed state is expected and long-lived.

**Consequence:** every by-number citation is a reference that breaks silently when a phase is split or renumbered — and PR #145 split a phase, so the citations it added are already at risk.

**Remedy:** a gate over prose in `docs/development/**`, keyed on `Phase <digit>` and **exempting records** the way `test_retired_vocabulary_is_gone_from_live_surfaces.py` does — a completed phase's own doc legitimately narrates by number. The exemption is the hard half and it is why this is a proposal rather than a fix.
