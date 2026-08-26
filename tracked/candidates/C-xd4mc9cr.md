---
id: C-xd4mc9cr
title: Close the V2 port's ranked coverage gaps — eight named functions, ranked by risk, produced by PR #31 as its *"state the untested surface, do not build it"* deliverable
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**A proposal, not a defect: "we have no test for X" is not a defect in X** — nothing claims any of these eight is wrong. **It had already decayed unnoticed**, which is why it left the issue queue: item 2 (`render()`) is now covered by `test_shared_render_catches_a_digit_bearing_placeholder`, landed via unrelated work; item 8 (`pr_number_from_url`) has a happy-path test but still none for its deliberate raise; the issue's own caveat *"without closing #30 none of it runs on the merge path"* is moot — **#30 is closed and the gate ships**. Still at zero: **item 1 `paper_currency`** and **item 4 `pass_numbers`**. Items 5-7 remain blocked on an integration tier that does not exist; building the one `tmp_path` git-repo fixture unblocks all three at once. **TRIAGE NOTE — item 1 is separable and stronger than the rest, and should probably be ruled `ship` on its own merits:** `paper_currency` computes staleness verdicts a prompt instructs the model to obey without recomputing, and its own docstring records why it exists — *"A model once marked four of eight papers past window when one was… Correct arithmetic, wrong anchor, and the error was invisible because the reasoning looked sound."* Documented past failure, authoritative output, zero tests, and nothing is likely to touch `research_activities.py` soon — which is precisely the case where a targeted one-off beats opportunistic coverage. The other seven are better taken at the point of change

**Source:** issue #36

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
