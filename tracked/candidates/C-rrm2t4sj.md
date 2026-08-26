---
id: C-rrm2t4sj
title: A routing policy for a verification that could not be performed — should an unperformed check be DOWNGRADED, RECORDED, or only annotated?
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**The half of `flaky-gh-discards-a-completed-review` that is genuinely a policy question, separated from the half that was a defect.** PR #71 fixed the defect: the two `gh` reads behind the render↔record invariant are read-only, so they are retried, and on exhaustion the run completes on the already-persisted route with the check reported as UNPERFORMED. **What is left is unruled and is capability, not a bug** — today the verdict stands unchanged and the operator gets a loud note saying *"verify the posted block by hand."* The alternative is that a route which could not be verified is downgraded to `HOLD - needs-assistance` automatically. **Consequence of leaving it: an operator can act on a `MERGE` whose render↔record invariant never ran**, and nothing but a note distinguishes that from one that ran and agreed. **DURABILITY IS THE SECOND HALF OF THE SAME RULING, added by PR #71's refine pass and deliberately NOT a separate row** — the note lives in `ReviewResult.notes`, which reaches an operator watching the run and nothing else, while every other computed-arm signal (`routed_outcome`, `undetermined_reason`, `channels_agree`) is written by `append_parent_route` and is countable offline. So **no replay can say how often this invariant degraded**, which is the per-reason rate the phase exists to produce; the docstring was corrected from *"recorded"* to *"reported"* rather than left claiming a durability the code does not have. Recording it durably means a new stratum in `exit-protocol.md` §2, and whether to add one is the same decision as whether an unperformed check should downgrade — one ruling, not two, which is why this expands the row instead of opening C-jchag0xr. **It has no phase home** — `grep -E 'retry\

**Source:** PR #71

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
