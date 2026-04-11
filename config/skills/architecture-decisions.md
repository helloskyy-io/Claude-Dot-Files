---
name: architecture-decisions
description: How to make and document architectural decisions — when to write an ADR, trade-off analysis, reversibility considerations, researching alternatives, and the ADR format. Use when making significant technical choices, evaluating trade-offs between approaches, writing ADRs, or deciding whether a decision is architecture-worthy.
---

# Architecture Decisions

This skill is about **making and documenting decisions that shape the system**. It covers when to treat something as an architectural decision, how to analyze trade-offs rigorously, and how to capture decisions for future readers.

The ADR template and placement rules live in `documentation-structure`. This skill focuses on the THINKING, not the formatting.

## First Principles

### Decisions Compound
Each architectural decision either enables or constrains future decisions. A decision made today shapes what's possible tomorrow. Good decisions make the future easier; bad ones create technical debt that compounds.

### You Pay Twice: Once to Decide, Once to Live With It
The cost of a decision is the decision-making process PLUS the consequences of living with it. Quick decisions with lasting consequences are often more expensive than slow decisions with minor impacts.

### Document the Why, Not the What
Code captures WHAT you built. Only documentation captures WHY. Six months from now, the reason for a decision is the only thing that's hard to recover. Preserve it.

### Reversibility Changes Everything
Some decisions are **one-way doors** — hard to reverse. Others are **two-way doors** — easy to reverse. Treat them differently. Spend more time on one-way doors. Move quickly on two-way doors.

## What Counts as an Architectural Decision?

Not every technical choice is an architectural decision. Writing an ADR for every variable name would be noise. Writing ADRs only for mega-decisions would lose valuable context.

### Write an ADR When:

**The decision affects how the system works structurally:**
- Choice of programming language, framework, or major library
- Database or storage technology choice
- API design pattern (REST vs GraphQL vs RPC)
- Authentication and authorization approach
- Deployment architecture (monolith vs microservices)
- Data modeling decisions that span many features

**The decision has non-obvious trade-offs:**
- Multiple valid approaches existed
- You chose one over others for specific reasons
- Someone could reasonably challenge your choice later
- The trade-offs are worth preserving for future readers

**Future contributors will need the context:**
- Someone 6 months from now might ask "why did we do it this way?"
- The reasoning isn't self-evident from the code
- Changing it later would require understanding the original constraints

**The decision is hard to reverse:**
- Schema changes that would require migrations
- Library choices that touch many files
- Infrastructure decisions with vendor lock-in
- Patterns that the team has built on top of

### Don't Write an ADR For:

- Routine implementation choices (variable names, file organization)
- Decisions with no meaningful alternatives (the language requires it)
- Purely cosmetic choices (formatting, indentation)
- Decisions made 6 months ago without documentation — that context is already lost, don't pretend otherwise
- Changes that are trivially reversible

**Rule of thumb:** If you can explain the decision in a sentence and nobody would question it, skip the ADR. If you need to explain WHY you chose X over Y, write the ADR.

## The Reversibility Spectrum

Not all decisions are equal. Classify before deciding how much effort to spend.

### Two-Way Doors (Easy to Reverse)
Examples: variable names, file organization, internal helper functions, UI layout choices, minor configuration values.

**How to approach:**
- Decide quickly
- Don't write an ADR
- Revisit later if it's wrong
- Let real usage inform the decision

**Time investment:** Minimal. Just pick one and move on.

### Medium Doors (Moderate to Reverse)
Examples: API endpoint shapes, component architecture, testing patterns, module boundaries.

**How to approach:**
- Spend moderate time on the decision
- Consider 2-3 alternatives
- Document the reasoning inline in code comments or short design notes
- Write an ADR if the team will build on this decision repeatedly

**Time investment:** Hours to days. Not weeks.

### One-Way Doors (Hard to Reverse)
Examples: core language/framework, database technology, authentication model, distributed vs centralized architecture, data schema foundations.

**How to approach:**
- Invest significant time upfront
- Research alternatives thoroughly (at least 3)
- Prototype if uncertain
- Consult stakeholders
- Write a detailed ADR
- Consider reversibility as a deciding factor — sometimes the reversible option is worth picking even if it's slightly worse

**Time investment:** Days to weeks. Getting it wrong is expensive.

### Special Case: "Can Be Reversed But At Cost"
Many decisions claim to be reversible but have real migration costs. A database migration is "reversible" only in the sense that it's possible, not that it's cheap.

**Rule:** If reversal requires more than a day's work, treat it as closer to a one-way door.

## The Decision-Making Process

For decisions worth an ADR, follow this process.

### Stage 1: Understand the Problem

Before considering solutions, get clear on the problem.

**Questions:**
- What are we trying to accomplish?
- What forces are at play? (performance, cost, team expertise, existing systems)
- What constraints exist? (budget, timeline, tech stack, regulatory)
- What assumptions am I making that I should verify?
- Who is affected by this decision?
- When does this decision need to be made?

**Output:** A paragraph describing the problem, the forces, and the constraints. This becomes the Context section of the ADR.

### Stage 2: Research Alternatives

For one-way doors, research at least 3 alternatives. For medium doors, at least 2. For two-way doors, just pick.

**For each alternative, understand:**
- How does it work?
- What are its strengths?
- What are its weaknesses?
- What are the trade-offs vs other options?
- What's the cost of adoption? (learning curve, migration, dependencies)
- What's the cost of maintenance? (operational, update frequency, security posture)
- What does the community/industry think?
- What do people who use it in production say?

**Sources:**
- Official documentation
- Engineering blog posts from companies using it
- Community discussions (Reddit, HN, Stack Overflow for honest takes)
- GitHub issues for the projects (reveals real problems)
- Your team's experience

**Red flag:** If you can't find anyone using an option in production, that's a data point.

### Stage 3: Analyze Trade-offs

For each alternative, lay out pros and cons in the same categories so they're comparable.

**Standard categories:**

| Category | What to evaluate |
|----------|-----------------|
| Correctness | Does it solve the problem correctly? |
| Performance | Latency, throughput, resource usage |
| Reliability | Failure modes, recovery, operational history |
| Security | Attack surface, known vulnerabilities, patching |
| Scalability | How does it handle growth? |
| Maintainability | How hard is it to operate and modify? |
| Complexity | How much does it add to the system? |
| Cost | Total cost of ownership (licenses, infra, ops) |
| Learning curve | How long to become productive? |
| Team fit | Does the team know it? Can they own it? |
| Lock-in | How hard to switch later? |
| Community | Active development, community support |

Don't evaluate every alternative against every category — focus on what matters for THIS decision. But be consistent — use the same criteria for all alternatives being compared.

### Stage 4: Decide

Based on the analysis, make the choice.

**Decision frameworks:**

**Weighted scoring:** Assign importance to each criterion, score each alternative, multiply and sum. Useful when criteria have clear weights.

**Elimination:** Rule out alternatives that fail hard constraints, then choose among the rest. Useful when some criteria are non-negotiable.

**Risk-adjusted:** Pick the option with acceptable upside AND acceptable worst-case. Useful when downside risk is high.

**Reversibility-biased:** When two options are close, pick the more reversible one. Useful when confidence is low.

**Rule:** The decision framework should match the problem. Don't force a weighted scoring if your criteria don't have weights.

### Stage 5: Document the Consequences

BEFORE writing the ADR, think through what will happen as a result.

**Positive consequences:** What gets easier because of this decision?
**Negative consequences:** What gets harder?
**Neutral consequences:** What changes in how the team works?
**Downstream effects:** What other decisions does this enable or constrain?

This section is often the most valuable part of the ADR. Future readers want to know "what did we give up?" as much as "what did we get?"

### Stage 6: Write the ADR

Use the ADR template from `documentation-structure` skill. The format is already defined there — this skill focuses on what CONTENT to put in it.

**ADR section guidance:**

**Context:** Describe the problem, forces, and constraints. Enough that someone unfamiliar with the decision can understand why it was needed. Don't include the solution here.

**Decision:** State the decision clearly and specifically. "We will use X" not "We might consider using X."

**Consequences:** Honest assessment of positive AND negative outcomes. If you only list positives, your ADR is propaganda, not documentation.

**Alternatives Considered:** For each rejected alternative, explain why. "We considered Y but rejected it because Z." Don't trash the alternatives — explain the trade-off honestly. Someone reading this later might be considering the alternative for a different context.

**Rules for writing ADRs:**

1. **Write as you decide, not after.** Retrospective ADRs miss the real context because humans rationalize after the fact.

2. **Be specific.** "We'll use PostgreSQL" not "We'll use a relational database."

3. **Include dates.** When was the decision made?

4. **Include status.** Proposed / Accepted / Deprecated / Superseded.

5. **Link to evidence.** Benchmarks, research, related ADRs, code locations.

6. **One decision per ADR.** If it's really two decisions, write two ADRs.

7. **Immutable once accepted.** Don't edit accepted ADRs except to change status.

8. **Supersede, don't replace.** When a later decision invalidates an ADR, write a new ADR that supersedes it. Both stay in the history.

## Trade-off Analysis Deep Dive

Good trade-off analysis is the hardest part of decision-making. Here's how to do it well.

### Make It Explicit
Trade-offs are always present but often implicit. Forcing yourself to articulate them catches decisions that don't actually pencil out.

**Bad (implicit):** "PostgreSQL is the obvious choice."
**Good (explicit):** "PostgreSQL gives us strong consistency, mature tooling, and team expertise. In exchange, we give up MongoDB's flexible schema and DynamoDB's managed operational simplicity. For our use case (transactional financial data), consistency matters more than flexibility, so the trade-off favors PostgreSQL."

### Quantify When Possible
Numbers beat adjectives. "PostgreSQL can handle 10K writes/sec on our current hardware, which exceeds our projected 2K writes/sec" is better than "PostgreSQL scales well for us."

### Don't Cherry-Pick
Every option has downsides. If your analysis of your chosen option has no cons, you're doing it wrong. Be honest about what you're giving up.

### Compare to Status Quo
The alternative "do nothing" is always on the table. What happens if we don't make any change? Sometimes the answer is "nothing much" and the decision isn't needed.

### Consider Second-Order Effects
What does this decision make easier to do next? What does it make harder? The most expensive part of a decision often isn't the decision itself — it's what it enables or prevents.

### Beware of Novelty Bias
New technology is exciting but carries risk. Boring, mature technology is often the right call. Ask: "do we need the benefits of the new thing, or are we choosing it because it's new?"

### Beware of Familiarity Bias
Conversely, don't always pick what you know. Sometimes the right answer requires learning something new. Ask: "am I choosing this because it's best, or because I don't want to learn something else?"

## When to Revisit Decisions

Decisions aren't forever. Situations change. Sometimes a good decision today becomes a bad decision tomorrow.

### Signals to Revisit a Decision:
- The constraints that drove the decision have changed
- Better alternatives now exist
- The decision is causing regular pain
- The team's expertise has shifted
- The system has grown beyond the original scope

### How to Revisit:
- Write a new ADR that references the old one
- Explain what changed and why
- If you're superseding, mark the old ADR as "Superseded by ADR-###"
- Don't just edit the old ADR — preserve history

## Red Flags in Decision-Making

Watch for these patterns — they indicate poor decisions being made:

### "Just Do It" on a One-Way Door
Jumping to a choice without analysis on a hard-to-reverse decision. Slow down.

### Researching One Option
Looking at only the option you already wanted. You're confirming, not deciding.

### Criteria Designed to Match Your Preferred Option
If the criteria happen to rank your favorite at the top, question whether you set the criteria honestly.

### "Everyone Uses X"
Popularity is weak evidence. Many companies use X for reasons that don't apply to you.

### "It's The Industry Standard"
Standards exist for reasons. But "industry standard" often means "popular" not "best for your context."

### No Mention of Trade-offs
If you can't articulate what you're giving up, you haven't actually made a trade-off analysis.

### Decisions Made by the Loudest Voice
The person advocating loudest isn't always right. Structured analysis prevents decision capture.

### Analysis Paralysis
Endless research without decision. At some point, pick something. A good decision now beats a perfect decision next quarter.

### Retrofit ADRs
Writing ADRs for decisions you made without documentation. The real context is already lost. Either skip the ADR or explicitly note it's a retrospective reconstruction.

## Integration With Other Skills

### documentation-structure
- Provides the ADR template and filename conventions
- Defines where ADRs live (`docs/architecture/ADR-###-title.md`)
- This skill focuses on the thinking; that skill on the format

### planning-methodology
- Planning often surfaces architectural decisions
- When planning, if you need to choose between approaches, that's when to invoke this skill
- Reference the resulting ADR from the plan

### project-definition
- New projects make many foundational architectural decisions
- That skill coordinates; this skill handles the decision-making for each choice
- Expect multiple ADRs during project definition

## Integration With Workflows

### revision.sh
- Minor revisions don't usually need ADRs
- If a revision surfaces a decision, pause and decide whether it needs an ADR

### revision-major.sh
- Major revisions often involve architectural re-thinking
- This skill activates to analyze the proposed changes
- New ADRs may be written as part of the revision

### build-phase.sh
- Phases sometimes encounter decisions not anticipated in planning
- This skill activates for those decisions
- Build-phase should pause and write the ADR, not plow through

### plan-new.sh
- Project definition creates many ADRs (tech stack, auth, database, etc.)
- Each foundational decision should get an ADR
- This skill is heavily used during plan-new

## Quick Decision Guide

**Is this an architectural decision?**

1. Does it affect how the system works structurally? (not just one file)
2. Are there multiple valid alternatives with non-obvious trade-offs?
3. Will future contributors need the context?
4. Is it hard to reverse?

If 2+ of these are yes → write an ADR.

**How much effort to spend?**

- Two-way door → minutes, just pick
- Medium door → hours, consider 2-3 options
- One-way door → days, research 3+ options, prototype, write detailed ADR

**Before writing the ADR:**

- Do I understand the problem clearly?
- Have I considered at least the minimum number of alternatives?
- Have I analyzed trade-offs honestly?
- Have I thought through consequences (positive AND negative)?
- Am I choosing based on good reasons, not bias?

## Summary Checklist

When making an architectural decision:

- [ ] Is this decision architecture-worthy (not routine)?
- [ ] Have I classified reversibility (two-way, medium, one-way)?
- [ ] Have I researched the appropriate number of alternatives?
- [ ] Have I analyzed trade-offs using consistent criteria?
- [ ] Have I considered downside risk (not just upside)?
- [ ] Is my chosen framework honest (not rigged)?
- [ ] Have I thought through second-order effects?
- [ ] Am I biased by novelty or familiarity?
- [ ] Can I explain the decision honestly, including what I gave up?
- [ ] Am I writing the ADR now, while the context is fresh?
- [ ] Does the ADR follow the format from documentation-structure?
- [ ] Is the ADR placed in `docs/architecture/` with correct naming?
