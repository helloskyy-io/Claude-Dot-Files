---
id: C-8rhxo6st
title: Extending the measurement-figures gate to cover QUANTITIES, so a memory or size figure restated in the roadmap is caught the way a count already is
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**The repo already built the right-shaped remedy for restated figures and keyed it one class too narrowly.** `testing/scripts/tests/unit/test_measurement_figures_are_cited.py` sweeps every roadmap line mentioning a phase and fails when a figure is restated instead of cited; its own docstring records that four consecutive passes each fixed what they could see while the frontier never shrank, and concludes *"Changing what the check keys on does."* **Its `FIGURE` pattern (`:45-51`) matches `N of M`, `~N%`, mutation counts and `N assessable/scorable/archived` — and no quantity with a unit.** **Measured on the run that placed this row:** `roadmap.md` carried `666 MiB` on a line that also mentions Phase 6, so it sat squarely inside the gate's sweep and passed clean; the restatement was caught by a human reviewer instead. **Consequence of leaving it:** the gate reads as covering restated figures and covers only the shapes someone happened to enumerate, which is worse than an absent gate — a green check is taken as evidence the class is handled, so the next quantity restated into a summary is found the same way this one was, by luck. **PROPOSAL, not a defect, and the line matters here:** nothing behaves wrongly — the gate does exactly what its pattern says, and every figure shape it was written for is still caught. This asks for coverage that has never existed, which per [`finding-routing.md` § 4](../../docs/standards/finding-routing.md) makes it a candidate whatever its done-state looks like. **Deliberately scoped to quantities and NOT to the general class.** The same run also found retracted *reasoning* restated in a summary (a roadmap Key Decision stating a growth rule its phase doc rules wrong), which is the same failure one abstraction up — but a regex cannot key on that, and proposing a gate for it would be proposing a thing nobody knows how to build. **The narrow half is a units alternation on an existing pattern; the wide half is an open question and is named here rather than bundled in.** **Done-state today: yes** — extend `FIGURE` with `\b\d+(\.\d+)?\s*(MiB\

**Source:** PR #80

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
