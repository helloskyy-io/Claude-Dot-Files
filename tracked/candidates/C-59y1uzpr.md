---
id: C-59y1uzpr
title: `--pr N` resolves the repo from the PR in one child and from the working directory in another, so a cross-repo run can review an unrelated PR and report success
status: open
count: 2
filed: 2026-08-28
filed_by: review-pr
component: 
size: 
decision: 
---

**DEFECT — `--pr N` resolves the target repository inconsistently across children, so a run can review the wrong PR and report success.**

**Measured, and confirmed independently by MDC PM3:** `plan-verify` derives the repo **from the PR itself**; `review-pr` derives it **from the working directory**. Hand the same `--pr N` to both from a repo that is not the PR's own, and they act on different objects.

**The failure is silent, which is what makes it a defect rather than a papercut.** MDC's case failed cleanly *only because no PR #171 existed in this repo* — the lookup 404'd. **Had a PR #171 existed here, `review-pr` would have reviewed it, found it fine, and reported success against a PR nobody asked about.** The wrong-confidence shape is the whole finding: absence of a colliding number is not a guard.

**Consequence if unfixed:** a cross-repo dispatch reports a green review of an unrelated PR, and the number in the report looks right.

**Remedy:** one resolution rule for `--pr`, applied by every child that takes it — derive from the PR and make the working directory a cross-check that fails loudly on mismatch, rather than each child choosing its own source.

## Recurrences

- 2026-08-28 · 2026-08-28: second sighting, MDC PM3. `review_pr.sh --pr 171` from the wrong cwd failed TERMINAL while `plan_verify.sh --pr 171` from that SAME cwd resolved correctly — the two children disagreeing, observed side by side in one session. Their note is the same one we made independently: it failed cleanly only because no PR #171 existed in claude-dot-files.
