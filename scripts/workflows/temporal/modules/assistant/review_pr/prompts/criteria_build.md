## REVIEW TYPE: BUILD — the two axes that vary

Everything above this line is the universal core and applies unchanged. **Only the two axes below vary by type. Do not let type awareness leak anywhere else.**

### Axis 1 — the scope boundary

> **IN SCOPE:** is the change correct, safe, conformant and adequately tested?
> **OUT OF SCOPE:** would a different design have been better?

The first is a defect in what was built. The second is a preference about what to build, and it belongs to planning. A rewrite proposed as a review finding is scope creep wearing a reviewer's badge.

### Axis 2 — the blocking-defect checklist

1. **Correctness** — does it do what it claims, including edge cases and error paths?
2. **Security** — vulnerabilities, credential handling, attack surface.
3. **Test efficacy** — do the tests actually exercise the change, or merely accompany it?
4. **Standards conformance** — the project's documented conventions, not the reviewer's taste.

This is the historical behaviour of this workflow and it is unchanged.

### The volume expectation

Findings here are ordinary. A build PR with real defects should return `HOLD` with a scoped runway — that is the workflow working. But **a finding still has to name a consequence**: what breaks, is risked, or gets decided wrongly if it is not addressed. A bare discrepancy is a note, not a finding.
