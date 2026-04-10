---
name: refactoring-methodology
description: How to evaluate code for refactoring opportunities and execute refactors safely. Use when assessing code quality, deciding what to refactor vs leave alone, evaluating refactoring suggestions, or performing structural code improvements. Pairs with code-reviewer for review findings and testing-methodology for verification.
---

# Refactoring Methodology

This skill is about **when and how to improve existing code structure without changing its behavior**. It covers evaluating refactoring opportunities, deciding what's worth changing, and executing changes safely.

## First Principles

### Refactoring Preserves Behavior
A refactor changes HOW code is structured, not WHAT it does. If the output changes, it's not a refactor — it's a bug fix or a feature change. Tests should pass before and after.

### Refactoring Costs Compound But So Do Benefits
Every refactor has an upfront cost (time, risk of breakage). A good refactor reduces ongoing cost (faster changes, fewer bugs, easier onboarding). The key question is: does the ongoing benefit outweigh the upfront cost?

### Perfect Code Is Not the Goal
The goal is code that's good enough to work with comfortably. Refactoring past "easy to change" into "theoretically perfect" is wasted effort.

### Context Matters
What's good code in one context is over-engineering in another. A one-off script doesn't need the same structure as a core library. Don't apply the same refactoring bar everywhere.

## When to Refactor vs When to Leave It Alone

This is the most important decision. Not all code smells need fixing.

### Refactor When:
- **You're about to modify the code anyway** — refactor before adding the feature, not separately
- **The code is actively slowing development** — people avoid touching it, bugs keep recurring
- **The code prevents a needed change** — the structure won't accommodate the new requirement
- **Multiple people have struggled** with the same code independently
- **Tests exist and pass** — you have a safety net

### Leave It Alone When:
- **It works and nobody touches it** — legacy code that's stable is low priority
- **You don't have tests** — refactoring without tests is gambling
- **The code is being replaced soon** — don't polish what's about to be demolished
- **The improvement is cosmetic only** — renaming for taste, reorganizing without benefit
- **You're procrastinating** — refactoring feels productive but sometimes it's just avoidance
- **The scope would cascade** — one change requires changing 50 files, destabilizing the system

### The Rule of Three
A common heuristic: if you see the same problem in three places, refactor. Once is a fluke. Twice is coincidence. Three times is a pattern that needs a solution.

## Evaluating Code for Refactoring Opportunities

When reviewing code, look for these categories of issues:

### Structural Issues (High Value to Fix)

**God objects/functions** — one thing does everything
- Symptom: file >300 lines, function >50 lines, class with 20+ methods
- Fix: split into focused components with single responsibility
- Why it matters: impossible to test, modify, or understand in isolation

**Tight coupling** — changing one thing forces changes in many others
- Symptom: modifying A requires changes to B, C, and D
- Fix: introduce interfaces/abstractions at boundaries
- Why it matters: changes cascade unpredictably

**Wrong abstraction** — an abstraction that makes simple things hard
- Symptom: callers routinely need to "work around" the abstraction
- Fix: replace the abstraction with a simpler one, or inline it entirely
- Why it matters: wrong abstractions are worse than no abstraction (Sandi Metz principle)

**Duplicated logic** — same logic in multiple places
- Symptom: bug fix needs to be applied in 3+ locations
- Fix: extract shared logic into a function/module
- Why it matters: one copy gets fixed, the others don't

### Naming Issues (Medium Value to Fix)

**Misleading names** — name doesn't match behavior
- `processData()` that actually deletes records
- `temp` or `data` that's used for 200 lines
- Fix only if the code is being modified anyway — not worth a standalone refactor

**Inconsistent naming** — same concept has different names
- `user` in one file, `account` in another, `person` in a third — all the same thing
- Fix: pick one and use it everywhere

### Complexity Issues (High Value to Fix)

**Deep nesting** — 4+ levels of indentation
- Fix: early returns, guard clauses, extract functions
- This is almost always worth fixing regardless of context

**Complex conditionals** — boolean expressions nobody can parse
- `if (!(!isActive || (isAdmin && !isSuspended)) && ...)`
- Fix: extract into named functions: `if (canAccess(user))`

**Implicit state machines** — state transitions scattered across files
- Fix: make the state machine explicit with defined states and transitions

### Dead Code (Always Fix)

**Unused functions, variables, imports** — just delete them
- Git remembers. Don't comment out, delete.
- The cost of dead code is confusion: "Is this used? Should I be using it?"

## Evaluating Refactoring Suggestions

When reviewing suggestions from a code-reviewer or refactoring-evaluator agent, apply these filters:

### Accept If:
- The suggestion makes future changes easier (measurable benefit)
- The code is being modified as part of this task anyway
- Tests exist to verify the refactor doesn't break behavior
- The suggestion addresses a real problem, not a style preference
- The scope is contained (not a cascading change)

### Reject If:
- It's a style preference with no functional benefit
- The code is stable and rarely changed
- No tests exist to verify the refactor
- The scope would destabilize unrelated code
- The benefit is theoretical, not practical
- It introduces a new pattern that doesn't match the rest of the codebase

### Defer If:
- The suggestion is valid but the scope is too large for the current task
- The suggestion requires a wider discussion (it changes team conventions)
- Better handled as a separate PR after the current work ships

## Executing Refactors Safely

### The Refactoring Workflow

1. **Verify tests pass BEFORE starting** — if tests are broken, fix them first or stop
2. **Make one structural change at a time** — don't combine refactoring with feature work in the same commit
3. **Run tests after each change** — catch breakage immediately
4. **Commit frequently** — small, reversible commits. If something goes wrong, revert the last commit, not the last hour
5. **Review the diff** — does the refactor actually improve things? Is the before/after clearly better?

### Safe Refactoring Patterns

**Extract function** — pull logic into a named function
- Safest refactor. Almost never breaks things.
- Makes code more readable and testable.

**Rename** — change a name to match behavior
- Safe if the rename tool catches all references.
- Watch for string-based references (config files, serialization).

**Move** — relocate code to a better home
- Moderate risk. Update all import paths.
- Verify no circular dependencies introduced.

**Inline** — replace an abstraction with its implementation
- Moderate risk. The abstraction might be used elsewhere.
- Good when an abstraction is more complex than the code it wraps.

**Replace conditional with polymorphism** — turn if/else chains into strategy pattern
- Higher risk. Changes how the code is structured.
- Only do this when the conditional is truly painful.

**Introduce interface/boundary** — decouple components
- Higher risk. Changes how components interact.
- Worth it when coupling is causing real pain.

### Dangerous Refactoring Patterns

**Large-scale rename across many files** — one typo breaks everything. Use automated tooling, not manual find-and-replace.

**Changing function signatures** — every caller must be updated. Miss one and it's a runtime error.

**Splitting a module** — dependencies may break in unexpected ways. Verify all import paths.

**Changing data shapes** — serialized data, APIs, and storage may depend on the current shape. Migration strategy required.

## What NOT to Refactor

### Over-engineering traps

**Premature abstraction** — creating an interface for one implementation. Wait until there are actually two cases before abstracting.

**Design pattern overdose** — applying patterns because you know them, not because you need them. The code should drive the pattern, not the other way around.

**Configuration-driven everything** — making everything configurable when the values never change. Hard-code what doesn't change.

**Future-proofing** — building for requirements that don't exist yet. You'll probably build the wrong thing.

### The three similar lines rule

From the global CLAUDE.md: "Three similar lines of code is better than a premature abstraction." Not everything needs to be DRY. Some duplication is fine when:
- The duplicated code might diverge in the future
- The abstraction would be harder to understand than the duplication
- The scope of duplication is small (2-3 occurrences)

## Measuring Refactoring Impact

How to tell if a refactor was worth it:

### Positive Signals:
- Subsequent changes in the area are faster
- Fewer bugs in the refactored area
- New team members understand the code faster
- Test coverage improved as a side effect
- Code review comments decrease in the area

### Negative Signals:
- The refactor introduced new bugs
- Subsequent changes are NOT easier (wrong abstraction)
- The refactor triggered a cascade of unplanned changes
- Nobody can explain why the refactor was done

## Integration With Other Skills

### testing-methodology
- Tests are the safety net for refactoring. No tests = no refactor.
- Run tests before, during (after each change), and after.
- If refactoring reveals untested paths, add tests first.

### code-reviewer agent
- Code review often surfaces refactoring suggestions
- Use this skill to evaluate which suggestions to accept vs defer vs reject

### planning-methodology
- Large refactors should be planned like features
- Break into phases, identify risks, define success criteria
- Don't combine large refactors with feature work

### architecture-decisions
- Structural refactors sometimes require architectural decisions
- If the refactor changes component boundaries, write an ADR

## Integration With Workflows

### revision.sh
- Minor revisions should NOT include refactoring unless directly related to the fix
- The prompt says "don't refactor unrelated code" — follow it

### revision-major.sh
- The refactoring evaluation stage uses this skill
- Accept, reject, or defer each suggestion based on the criteria above
- Focus on refactors that make the major revision's goals achievable

### build-phase.sh
- Refactoring is sometimes needed before a feature can be built
- If so, make it a separate task in the plan — don't mix refactoring with feature work in the same commit

## Summary Checklist

When evaluating refactoring:
- [ ] Is this code actively causing problems? (not just "could be better")
- [ ] Are tests in place to verify the refactor?
- [ ] Is the scope contained? (not cascading)
- [ ] Is the code being modified as part of current work? (opportunistic)
- [ ] Does the refactor address a real pattern (3+ occurrences)?
- [ ] Is the suggested abstraction simpler than the duplication?
- [ ] Am I refactoring or procrastinating?

When executing refactoring:
- [ ] Tests pass before I start
- [ ] One structural change per commit
- [ ] Tests run after each change
- [ ] The diff clearly shows improvement
- [ ] No behavior change (unless that's the explicit goal)
