---
name: planning-methodology
description: How to plan features, phases, and work breakdowns. Use when creating implementation plans, breaking down features into tasks, identifying dependencies, assessing risks, or writing phase docs. Covers the HOW of planning regardless of project type. Pairs with documentation-structure for where plans live.
---

# Planning Methodology

This skill is about **how to plan work effectively**. It does not cover WHERE plans live (that's `documentation-structure`) or architectural decision-making (that's `architecture-decisions`) or initial project setup (that's `project-definition`). This is the daily planning skill — the one that activates most often.

## First Principles

### A Plan Is a Hypothesis
A plan is your best guess at the work needed, made BEFORE you start. Reality will be different. The value is not in being right — it's in having a structured starting point that you can verify, adjust, and track against.

### Plans Exist to Prevent Drift
The main risk in software development is drifting from the goal without noticing. Plans create checkpoints where you can ask "are we still going where we meant to?" A feature without a plan is a feature with no way to detect drift.

### Precision Beats Verbosity
A specific, actionable plan is better than a vague thorough one. "Add error handling" is worse than "Add try/catch around the db.query call in auth.ts:45, log errors to audit_log, return 500 with safe error message." Specificity enables execution.

### The Plan IS the Prompt
For autonomous workflows, the plan document becomes the prompt Claude executes. A bad plan produces bad output. Invest in the plan — it pays back 10x in execution quality.

## When to Plan vs When to Just Start

Not every task needs a plan. Planning has costs (time, cognitive load) and should only be used when it pays back.

### Plan When:
- **Scope is larger than a couple files** — more than ~3 files affected
- **Multiple distinct stages** are required (data model → API → UI)
- **Dependencies exist** between pieces of work
- **Multiple people or agents** will work on it
- **Risk of drift** is real (complex or ambiguous requirements)
- **You'll hand it off** (to autonomous workflow, to a teammate, to future you)
- **You can't hold the whole thing in your head** at once

### Just Start When:
- **Single file change** with obvious approach
- **Bug fix** where the root cause is known
- **Exploration or prototyping** where the design isn't clear yet
- **Trivial additions** like typo fixes, formatting
- **Well-known pattern** you've implemented before

**Rule of thumb:** If you can describe the whole change in one sentence and you're confident about every step, skip the plan. Otherwise, plan.

## The Planning Process

Follow these steps in order. Don't skip ahead — each stage informs the next.

### Stage 1: Understand the Goal

Before planning HOW, get clear on WHAT and WHY.

**Questions to answer:**
- What is the user-visible outcome?
- Why does this matter? What problem does it solve?
- What does "done" look like?
- What are the explicit constraints (time, tech, scope)?
- What are the implicit constraints (team conventions, existing architecture)?
- What assumptions am I making that I should verify?

**Output:** A 1-2 sentence statement of the goal. If you can't write this clearly, you don't understand the goal yet. Stop and clarify.

### Stage 2: Identify Requirements

Separate WHAT the system must do from HOW you'll build it.

**Categories:**

**Functional requirements** — what the system must do:
- User can [action] and get [result]
- System responds to [event] by [behavior]
- API endpoint accepts [input] and returns [output]

**Non-functional requirements** — how well the system must do it:
- Performance: latency, throughput, scale
- Security: auth, data protection, audit
- Reliability: uptime, error handling, recovery
- Maintainability: testability, extensibility
- Observability: logging, metrics, tracing

**Constraints** — what must be true:
- Tech stack limitations
- Budget limitations
- Timeline limitations
- Team expertise
- Existing architecture

**Rule:** If you can't list at least the functional requirements explicitly, you're not ready to plan. Go back to Stage 1.

### Stage 3: Break Down the Work

Decompose the goal into discrete, ordered tasks.

#### Principles of Good Task Breakdown

**Each task should be:**
- **Atomic** — does one thing well
- **Verifiable** — you can tell when it's done
- **Ordered** — dependencies are clear
- **Actionable** — specific enough to start immediately
- **Sized right** — small enough to complete without losing focus, large enough to be meaningful

**Good task size:** A task should take 30 minutes to 4 hours of focused work. Larger tasks should be broken down. Smaller tasks should be batched.

#### Anti-patterns in Task Breakdown

**Too vague:** "Implement auth" — this is a feature, not a task
**Too granular:** "Import useState from React" — this is a line of code
**Too coupled:** "Add login + signup + password reset" — this is three tasks
**Too abstract:** "Make the code better" — not actionable

#### The Task Template

For each task, capture:
```markdown
- [ ] **Task name** — clear verb + what (File: `path/to/file.ts` if known)
  - **Action:** Specific thing to do
  - **Why:** Reason this task exists (connects to a requirement)
  - **Dependencies:** None | Requires task X
  - **Risk:** Low | Medium | High
```

### Stage 4: Identify Dependencies

Not all tasks can start immediately. Figure out what blocks what.

**Types of dependencies:**

**Sequential:** Task B needs Task A's output
- Data models must exist before API endpoints that use them
- API must exist before UI that calls it

**Parallel:** Tasks can happen at the same time
- Backend API and frontend mock can be built in parallel
- Unit tests and integration tests for the same feature can be parallelized

**External:** Waiting on something outside the plan
- Third-party API credentials from another team
- Infrastructure provisioning
- Design decisions from stakeholders

**Document dependencies explicitly.** A plan without dependency mapping can produce tasks in wrong order and create rework.

### Stage 5: Identify Risks

For each task (or group of related tasks), ask "what could go wrong?"

**Common risk categories:**

**Technical risk:**
- Unknown library behavior
- Integration complexity
- Performance unknowns
- Concurrency/race conditions

**Scope risk:**
- Requirements might expand mid-implementation
- Edge cases not fully understood
- Dependencies on unclear external systems

**Time risk:**
- Task is more complex than it looks
- Investigation might take significant time
- Testing might reveal deeper issues

**People risk** (for team work):
- Knowledge silos
- Availability
- Parallel work conflicts

**For each significant risk, document:**
- What the risk is
- How likely it is (low/medium/high)
- What the impact would be if it happens
- How to mitigate it (prevent, detect, or respond)

### Stage 6: Define Success Criteria

How will you know the plan is complete? What does "done" look like?

**Good success criteria are:**
- **Observable** — you can check them externally
- **Specific** — not "it works" but "X happens when Y"
- **Complete** — cover the important behaviors
- **Testable** — ideally automatable

**Examples:**

Bad:
- [ ] Feature is done
- [ ] Code is good
- [ ] Users are happy

Good:
- [ ] User can log in with email + password
- [ ] Login rejects expired tokens with 401
- [ ] Session persists across browser restart
- [ ] Tests pass with >80% coverage on auth module
- [ ] No regressions in existing auth flow
- [ ] Security audit finds no critical issues

### Stage 7: Phase the Work

For larger plans, group tasks into phases that can be delivered incrementally.

**Principles of phasing:**

**Each phase should be independently deliverable** — even if only Phase 1 ships, it should be valuable on its own.

**Each phase should be testable** — you should be able to verify it works before moving to the next.

**Later phases should build on earlier phases** — not replace them.

**Favor vertical slices over horizontal layers:**
- ❌ Horizontal: Phase 1 = all data models, Phase 2 = all APIs, Phase 3 = all UI (nothing works until Phase 3)
- ✅ Vertical: Phase 1 = one full feature end-to-end, Phase 2 = second feature, Phase 3 = third (each phase ships something useful)

**Common phasing patterns:**
- **MVP → Enhancement → Polish** — ship the minimum, iterate
- **Happy path → Edge cases → Error handling** — build the simple case first
- **Core → Integration → Observability** — build it, connect it, monitor it

## Plan Document Structure

When writing a plan, follow this structure. See `documentation-structure` skill for where plans live (usually `docs/development/features/<feature>/phase-N.md`).

```markdown
# Phase N: [Phase Name]

## Status
[Not started | In progress | Complete]

## Overview
[1-2 sentence summary of what this phase delivers]

## Goal
[What success looks like — ties back to Stage 1]

## Requirements
### Functional
- ...
### Non-functional
- ...
### Constraints
- ...

## Architecture Changes
[If this phase changes architecture — otherwise omit]
- ...

## Tasks

### [Logical Group 1]
- [ ] **Task name** — description (File: `path`)
  - Action: ...
  - Why: ...
  - Dependencies: ...
  - Risk: Low/Medium/High

### [Logical Group 2]
- [ ] ...

## Dependencies
- Phase X must be complete
- Requires external dependency Y

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Risks & Mitigations
- **Risk:** [description]
  - **Mitigation:** [how to handle]

## Notes
[Context, open questions, decisions made during planning]
```

## Updating Plans Mid-Flight

Reality will diverge from the plan. That's expected. What matters is how you respond.

### When Reality Matches the Plan
- Mark tasks as complete as you finish them
- Keep moving

### When You Discover Something Unexpected
- Stop and update the plan before continuing
- Document what changed and why
- Adjust remaining tasks and dependencies
- Re-evaluate risks if the change is significant

### When the Plan Is Wrong
- Don't silently work against a broken plan
- Either fix the plan or stop and replan
- Stale plans that nobody updates become misinformation

**Rule:** A plan should always reflect current reality. If it doesn't, update it or delete it.

## Red Flags in Planning

Watch for these — they indicate planning problems:

### Vague Goals
"Improve performance" without specifics. Nobody can plan toward a vague goal. Get specific before planning.

### Unplanned Dependencies
Tasks listed in order but not explicitly noting dependencies. Will cause false parallelism and rework.

### Missing Success Criteria
No way to know when the work is done. Leads to endless scope creep or premature declaration of completion.

### Too Many Phases
More than 5 phases in a single plan suggests the feature is too big. Split it into multiple features.

### No Risk Identification
Assumes everything will go smoothly. Reality won't cooperate.

### Implementation Details Mixed With Requirements
Planning HOW before WHAT leads to solving the wrong problem.

### Plan That's Never Updated
Stale plans are worse than no plans — they mislead.

### Plan Without a Verification Stage
Tasks that build things but don't verify they work. Leads to "done" code that doesn't actually function.

## Operational Considerations

Plans that produce running software must address how it gets deployed and stays running. These are the questions that always come up in review — address them in the plan to prevent rework.

### Deployment Strategy
- **Where do the files live?** Specify exact paths. If introducing a new directory convention (e.g., `scripts/services/`), call it out as new.
- **How does it get to the machine?** Install script? Ansible? Manual? Symlinks?
- **Does `install.sh` need updating?** If the feature adds new targets that should deploy across machines, the install script must know.
- **Does it need permissions or privileges?** Executable bit? Systemd enablement? Cron entries?

### Configuration Management
- **What values might change between environments?** Polling intervals, target repos, timeouts, feature toggles.
- **Don't hardcode what should be configurable.** Use a config file for anything an operator might want to change without editing code.
- **Convention:** For services, use a config file (YAML, env, or JSON) in a standard location. Document all config options with defaults.
- **For simple scripts:** Environment variables or flags are fine. Config files are for services with many knobs.

### Naming for Extensibility
- **Will there be more of these later?** If the feature is the first of a kind (first service, first monitor, first integration), name it for the category, not the specific instance.
- **Bad:** `pr-watcher` (too specific — what about issue watching?)
- **Good:** `gh-monitor` (category-level — PR comments become one handler among many)
- **Rule:** If you can imagine a second instance of this thing, name the first one broadly enough to accommodate the second.

### Scalability Considerations
- **Multi-machine:** If deployed on multiple machines, will they conflict? (Both polling the same comments?)
- **Multi-repo:** Does it handle one repo or many?
- **Backlog:** What happens if the machine is off when work arrives?
- **Rate limiting:** Does the external service have API rate limits?
- **Concurrency:** What happens if two tasks arrive simultaneously?

Don't solve all of these in v1 — but **acknowledge them** in the plan so the design doesn't prevent future scaling.

### Insufficient Context Handling
- **What happens when the builder (human or AI) doesn't have enough context to proceed?**
- For autonomous workflows: the AI should ask for clarification (post a comment, flag in output) rather than guess.
- For plans: if a task can't be completed without additional information, mark it as blocked and state what's needed.
- **Rule:** Guessing is worse than asking. A clarifying question takes 30 seconds. A wrong implementation takes hours to undo.

## Integration With Other Skills

### documentation-structure
- Tells you WHERE plans live (usually `docs/development/features/<feature>/phase-N.md`)
- Provides the phase doc template
- Establishes file naming conventions

### architecture-decisions
- When planning surfaces an architectural decision, write an ADR
- Reference the ADR from the plan
- Planning is the trigger for many ADRs

### testing-methodology
- Every phase should include testing tasks
- Tests are NOT a separate phase — they're integrated
- Use testing-methodology to scope test work within the plan

### project-definition (rare, new projects only)
- Planning happens within existing projects
- New project definition handles the initial "here is the entire project" planning
- Phase plans come AFTER project definition

## Integration With Workflows

### revision.sh (minor revisions)
- Usually doesn't need a plan — revisions are small enough to just do
- If a revision needs planning, it's probably a revision-major, not a revision

### revision-major.sh (significant rework)
- Uses this skill to plan the fix before implementing
- Plan should assess what's broken, what needs to change, and in what order
- The plan becomes part of the PR for reviewability

### build-phase.sh (feature build)
- This is the primary consumer of planning methodology
- The plan document IS the input to the workflow
- Claude executes the plan task by task
- Quality of the plan directly determines quality of the output

### plan-new.sh (new projects)
- Uses project-definition skill for the initial project setup
- Then uses planning-methodology for phase-level plans within the project

## Quick Decision Guide

**Before starting any non-trivial work:**

1. Can I describe this in one sentence and do I know every step? → Just start
2. Does this affect more than 3 files? → Plan it
3. Does this have multiple distinct stages? → Plan it
4. Will someone else (person or agent) execute this? → Plan it
5. Am I handing off for autonomous execution? → Plan it carefully

**When creating the plan:**

1. Start with the goal, not the tasks
2. Identify requirements before breaking down work
3. Use the task template for every task
4. Explicit dependencies, not implicit order
5. Risk identification is not optional
6. Success criteria must be observable
7. Phase for independent delivery
8. Write it in the right location per documentation-structure

**After creating the plan:**

1. Read it back — does it actually describe complete work?
2. Can someone (or Claude) execute this without asking questions?
3. Does every task have a clear "done" state?
4. Are dependencies and risks explicit?
5. Is the plan in the right place with the right name?

## Summary Checklist

**Core planning:**
- [ ] Is this work significant enough to plan? (Not trivial)
- [ ] Do I understand the goal clearly?
- [ ] Have I listed functional requirements?
- [ ] Have I listed non-functional requirements?
- [ ] Are tasks atomic, verifiable, ordered, actionable, and sized right?
- [ ] Are dependencies explicit?
- [ ] Have I identified the main risks?
- [ ] Are success criteria observable and specific?
- [ ] For larger plans: are phases independently deliverable?
- [ ] Is the plan in the right location per documentation-structure?
- [ ] Does the plan include verification tasks (tests)?
- [ ] Would a fresh reader (or Claude) execute this without asking questions?

**Operational (for features that produce running software):**
- [ ] Where do the output files live? Are paths explicit?
- [ ] How does it deploy? Is install.sh updated if needed?
- [ ] What's configurable vs hardcoded? Is there a config file if needed?
- [ ] Is the name extensible? (Will there be more of these?)
- [ ] Are scalability concerns acknowledged? (Multi-machine, multi-repo, backlog, rate limits)
- [ ] What happens when context is insufficient? (Clarify, don't guess)
