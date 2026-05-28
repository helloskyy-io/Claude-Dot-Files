---
name: quality-control-methodology
description: Senior-engineer holistic quality review methodology — the six-dimension lens (best-practices grounding, enterprise-readiness, compromise detection, maintainability, robustness, decision rigor) used to assess whether work meets the bar a top-tier engineering organization would sign off on. Use when applying quality-control to code, plans, or sprint deliverables.
---

# Quality-Control Methodology

The senior-engineer integration test applied to engineering work. Asks the question no narrow reviewer asks: "would a peer reviewer at a top-tier engineering organization (Anthropic, Google, AWS) sign off on this, or would they push back?"

This methodology is HOLISTIC — it pulls signals across multiple dimensions and challenges the work as an integrated whole, not as isolated correctness/style/security concerns.

## Why this lens exists

Other reviewers apply narrow lenses:
- **code-reviewer**: "is this code correct?" (correctness, bugs, edge cases)
- **refactoring-evaluator**: "could this be structured better?" (improvements)
- **standards-auditor**: "does this match our documented standards?" (conformance)
- **security-auditor**: "are there vulnerabilities?" (security risks)

None of them ask: "is this our BEST EFFORT? Is the QUALITY where it needs to be?" That gap lets the easy-path slip through review because no single reviewer is assigned to challenge it holistically.

The quality-control methodology fills that gap.

## The Six Dimensions

For every review, scan systematically across all six dimensions. Don't react only to what catches your eye — actively probe each dimension with at least one concrete check.

### 1. Best-practices grounding

Are the decisions defensible against current industry knowledge?

- For each significant decision, articulate what authoritative industry knowledge says about this kind of task
- Compare the engineer's choice to the industry best practice
- Where they diverge: is the divergence justified? Documented? Or silent?

Reference the `engineering-quality.md` rule "Best practices vs project standards" for the structural discipline this lens enforces.

### 2. Enterprise-readiness

Will this hold up at production scale, under load, over time?

Concrete checks:
- Failure modes: what happens when external dependencies fail?
- Error handling robustness: does error propagation reach a layer that can handle it?
- Performance characteristics: behavior under realistic data volume?
- Concurrency: behavior under simultaneous access?
- Partial failure: behavior when some operations succeed and others fail?
- Resource constraints: memory, CPU, disk, network under stress?

If the work is "good enough for the demo case" but won't scale, it's not enterprise-ready.

### 3. Compromise detection

Were quality shortcuts taken for speed or ease that should have been resisted?

Look for these specific tells:
- "Good enough" implementations where the correct version was clearly achievable
- Edge cases waved away in comments instead of handled
- Approaches that work for the demo but won't generalize
- Tests that exercise happy path only
- Patterns copied without thinking about fit
- "I'll just do X for now" tells in the code or commits
- Generic helper-function dumping grounds (`utils.py`, `helpers.py`) instead of proper placement
- Magic numbers / magic strings without explanation
- Try/except blocks that suppress problems instead of handle them

This dimension cross-references the engineering-quality.md "Best practices vs project standards" and "Push back on shortcuts" sections.

### 4. Maintainability

Would a future engineer be able to maintain this confidently?

- Code readability: can a senior engineer understand the intent quickly?
- Comment quality: do comments explain WHY (when WHY isn't obvious), not WHAT?
- Naming clarity: do names accurately describe what the thing does?
- Surprising behavior: is anything non-obvious explained?
- Hidden complexity: is anything clever where simple would do?

### 5. Robustness

Does this handle failure modes, edge cases, and adversarial inputs?

- Error propagation: does it surface to where it can be handled?
- Input validation: at system boundaries (user input, external APIs, file I/O, network calls, subprocess output)?
- Unexpected state: behavior when reality doesn't match assumptions?
- Race conditions: behavior under concurrent access?
- Timeout/retry logic: behavior when operations stall?
- Defensive coding baseline: per `engineering-quality.md` "Defensive coding is the baseline"

### 6. Decision rigor

Is the engineer's documented reasoning actually sound, or is it weak post-hoc justification?

Read the PR body, commit messages, decision logs:
- "I chose X because Y" — is Y actually a strong reason, or is it convenient?
- Missing rationale for non-obvious choices
- Assertions presented as facts without supporting evidence
- Trade-offs claimed but unexplored
- Decisions documented but not actually thought through

This dimension specifically targets the failure mode where engineers transparently document weak decisions and reviewers don't challenge them.

## Severity Categorization

For each finding, apply the discriminator: **would a senior peer reviewer at a top-tier engineering organization push back on this?** If yes, it's a finding. If no, it's not.

Then categorize:

- **Critical** — ship-blocker. The quality compromise is significant enough that shipping creates real risk (production incident likelihood, future re-work cost, security concern, data integrity issue). A senior reviewer would block the PR.

- **Warning** — significant concern. The quality compromise is real but doesn't block shipping. A senior reviewer would push back but might accept with explicit justification. Examples: missing edge-case handling unlikely to fire, "good enough" implementation that should be improved, weak decision rationale that should be strengthened.

- **Info** — polish. A senior reviewer would mention this casually. Examples: minor naming improvements, comments that could be clearer, opportunities for cleanup.

## Over-Surfacing Discipline

When in doubt between severity levels, lean HIGHER. Specifically:
- In doubt between Warning and Info → Warning
- In doubt between Info and no-finding → Info

The operator can downgrade or dismiss. Missing a finding is the worse failure mode.

This bias is deliberate. The whole reason this methodology exists is that under-surfacing has been the recurring failure pattern. The remedy is structural over-surfacing.

## Application Contexts

### Code Review (revision-major, build-phase)

Apply all six dimensions to code changes. Focus weight on:
- Enterprise-readiness (does the code hold up under realistic conditions?)
- Compromise detection (any shortcuts in the implementation?)
- Decision rigor (is the engineer's reasoning sound?)

These three are the most-skipped lenses in code review.

### Planning Review (plan-revision, plan-new)

Apply the six dimensions to the PLAN itself — not yet-existing code:
- Best-practices grounding: is the planned approach industry-best-practice?
- Enterprise-readiness: will the planned solution be enterprise-grade, or will it produce "good enough" results?
- Compromise detection: are there compromises baked INTO the plan (e.g., "we'll skip X for now") without justification?
- Decision rigor: does the plan explain WHY decisions were made, or just WHAT will be done?

Plans can be compromised before any code is written. Catch it at planning time.

### Sprint Review (sprint-review)

Apply the six dimensions across the sprint's whole body of work. Focus on cumulative quality:
- Is the sprint's output enterprise-grade AS A WHOLE?
- Do compromises accumulate across the sprint?
- Did the team's quality bar hold across the sprint, or did it slip on later work?

## Avoiding Overlap With Other Reviewers

Quality-control deliberately doesn't duplicate the other reviewers' work:
- If something is a code-reviewer finding (correctness bug), let code-reviewer catch it
- If something is a refactoring-evaluator finding (better structure exists), let refactoring-evaluator catch it
- If something is a standards-auditor finding (project convention violated), let standards-auditor catch it
- If something is a security-auditor finding (vulnerability), let security-auditor catch it

Quality-control's unique contribution is the **integrated senior-engineer lens** — finding things no narrow reviewer catches because they require pulling multiple signals together.

When you notice something a narrow reviewer would catch through its own lens, mention it briefly with a pointer to that reviewer ("code-reviewer should also flag this"), but don't make it your primary finding.

## Output Format Reference

The agent invoking this methodology should report findings using this structure:

```
## Quality-Control Audit: [scope]

### Critical findings (ship-blockers)
- **[file/section]** — [Confidence: High/Medium/Low]
  - **Dimension:** [one or more of the six]
  - **Issue:** [specific concern with concrete evidence]
  - **Why a senior reviewer would block:** [reasoning]
  - **Recommendation:** [specific action]

### Warning findings (significant concerns)
- **[file/section]** — [Confidence: High/Medium/Low]
  - **Dimension:** [one or more of the six]
  - **Issue:** [concern with evidence]
  - **Recommendation:** [specific action]

### Info findings (polish)
- **[file/section]** — observation

### Dimensions assessed
- Best-practices grounding: [aligned / divergent / not-applicable]
- Enterprise-readiness: [strong / has-concerns / weak]
- Compromise detection: [no-compromises / minor / significant]
- Maintainability: [strong / acceptable / weak]
- Robustness: [strong / acceptable / weak]
- Decision rigor: [strong / acceptable / weak]

### Summary
[1-2 sentences: holistic quality assessment + top priority finding]
```

## Integration With Other Skills and Rules

- **`engineering-quality.md` rule** — the always-loaded discipline this methodology enforces. The "Best practices vs project standards" section's pre-implementation checkpoint is the engineer-side discipline; quality-control is the review-side check that catches what slipped through.
- **`standards-enforcement` skill** — for looking up project standards relevant to the work being reviewed
- **`standards-authoring` skill** — for assessing whether quality-control findings point at standards that need updating
- **`documentation-structure` skill** — for understanding where docs live and how they relate to the work being reviewed
