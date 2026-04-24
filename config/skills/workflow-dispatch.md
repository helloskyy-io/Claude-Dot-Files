---
name: workflow-dispatch
description: How to pick the right autonomous workflow and write an effective task prompt or @claude PR comment. Use when preparing to dispatch a workflow script (revision, revision-major, build-phase, plan-new, plan-revision), drafting an @claude PR comment for gh-monitor, or deciding which workflow fits a task.
---

# Workflow Dispatch

Two questions every dispatch answers: (1) which workflow fits this task? (2) how do I write a task prompt the engineer can act on?

## Workflow Selection

| Task | Workflow | Use when |
|---|---|---|
| Small code fix | `revision.sh` | Single file or small area, clear bounded scope, one concept |
| Significant code rework | `revision-major.sh` | Multiple files, architecture changes, refactor, review feedback |
| Implement from a plan doc | `build-phase.sh` | Phase/feature doc exists; engineer follows it step-by-step |
| Revise planning docs | `plan-revision.sh` | Updating roadmap, phase docs, requirements, ADRs, epics |
| Define new project | `plan-new.sh` | Greenfield — project scope, stack, architecture undefined |

### Anti-patterns (DON'T)

- **Bulk rename across many files** → `revision.sh` with `sed -i` or `Edit(replace_all: true)`. NEVER `plan-revision.sh` — it burns turns on per-occurrence Edits (observed: 301 turns / $37 on one miscategorized run).
- **Small single-concept fix** → `revision.sh`. NOT `revision-major.sh` — the 3-agent peer review pipeline is wasted overhead on trivial fixes.
- **Code-only change** → `revision*.sh` or `build-phase.sh`. NOT `plan-revision.sh` — wrong agents (architect+planner+standards-architect, not code-reviewer).
- **Planning without a written plan** → `plan-revision.sh` updates EXISTING docs. `plan-new.sh` creates docs from scratch. If neither fits, the scope hasn't been thought through yet.

### Size heuristic (MAX_TURNS budget indicates expected complexity)

| Workflow | MAX_TURNS | Complexity signal |
|---|---|---|
| revision | 100 | Fast, focused, low-stakes |
| revision-major | 300 | Multi-file, review-heavy |
| build-phase | 300 | Implementation from a plan |
| plan-revision | 300 | Multi-doc planning changes |
| plan-new | 500 | Greenfield, extensive planning |

### When a task is too big — split or escalate

If a task is likely to exceed the chosen workflow's MAX_TURNS budget, don't just dispatch and hope. Either escalate to a larger workflow or split the task. Warning signs that a task is too big for the chosen workflow:

- Touches many files that aren't related by a single concept
- Requires multiple unrelated decisions (feature A + refactor B + standards update C)
- Mixes code + docs + standards changes in one task
- Contains "and also…" phrasing — usually a natural seam to split along
- Task file exceeds ~300 lines of description (the description itself signals scope creep)

**Escalate when the task is cohesive but large:**
- `revision.sh` turns insufficient → `revision-major.sh` (more turns + 3-agent review)
- `revision-major.sh` turns insufficient → write a phase doc first, then `build-phase.sh`
- No plan exists and task is complex → `plan-new.sh` or `plan-revision.sh` FIRST, then `build-phase.sh`

**Split when the task is multiple things bundled:**
- Identify natural boundaries — separate features, separate components, separate phases, separate layers
- **Sequential split** if piece 2 depends on piece 1: dispatch piece 1, wait for merge, then dispatch piece 2 with the merged state as starting point
- **Parallel split** if pieces are independent: dispatch separate PRs concurrently (different branches, gh-monitor's per-PR concurrency allows this)
- Each split piece gets its own task file with its own objective, scope fence, and done criteria — don't reference "the other piece" across files

**Red flag: workflows hitting close to MAX_TURNS regularly.** If a workflow consistently uses 80%+ of its turn budget, tasks coming in are too big. Either split more aggressively going forward or escalate the default workflow choice for that type of work.

**Red flag: PR review finds "we also fixed X while here."** The engineer expanded scope because the task didn't fence it tightly enough. Next time, split or narrow the scope.

## Anatomy of a Good Task Prompt

Every task prompt — whether inline, written to a `--task-file`, or posted as an `@claude` comment — answers five things:

1. **Primary objective** — one sentence. Specific enough that two engineers would produce the same general result.
2. **Scope fence** — what's IN and what's explicitly OUT. Prevents "while I'm here" drift.
3. **Context** — what's been tried, why this matters, links to related PRs/issues/docs.
4. **Constraints** — standards to follow, compatibility requirements, deadlines, team preferences.
5. **Done criteria** — how the engineer (and you, reviewing) know it's complete.

The task prompt describes **WHAT** and **WHY**. Do NOT prescribe **HOW** — that's the engineer's job. Telling an engineer "use a regex" closes off better approaches.

### Long task inputs → --task-file

Multi-paragraph tasks with code blocks, quotes, or special characters: write to `/tmp/claude-<name>.md` and pass via `--task-file`. Bypasses command-line parsing breakage.

## Templates

### revision.sh (small code fix)

Single paragraph, inline is enough:

```
Fix the null check in login() — currently crashes on email with '+'. Add a test case for 'user+tag@example.com'. Do not touch other auth code.
```

### revision-major.sh (significant rework)

Use --task-file. Structure:

```markdown
## Objective
<one sentence — what's changing and why>

## Scope
**In:** <files/areas/modules to change>
**Out:** <explicitly NOT touched>

## Context
<why this matters, what's been tried, related PRs/issues/docs>

## Constraints
- <standards, compatibility, conventions>
- <deadline if any>

## Done criteria
- <observable outcomes>
- <test requirements>
```

### build-phase.sh (implement from a plan)

Plan path is the primary input. Task file holds ONLY context not in the plan:

```
build-phase.sh /path/to/phase-doc.md --task-file /tmp/context.md
```

Context file (optional, brief):
- Anything NOT in the plan doc the engineer needs to know
- Known gotchas or prior failure modes
- Dependencies that came online since the plan was written

### plan-revision.sh (update existing planning docs)

Use --task-file for anything beyond trivial bullet updates:

```markdown
## What to revise
<specific planning docs and sections>

## Why
<motivation — decision needed, new information, roadmap adjustment>

## Dependencies
<other docs that may need updates to stay consistent>

## Out of scope
<what to NOT touch>
```

### plan-new.sh (greenfield project definition)

Describe the project briefly while capturing hard constraints:

```markdown
## Project
<name, one-sentence purpose>

## Constraints
**Stack:** <must-have languages, frameworks, infra>
**Must-NOT:** <technologies excluded>
**Team context:** <who maintains, existing tooling>
**Target environment:** <deployment, scale, compliance>

## Expected deliverables
<documentation buckets, phase docs, ADRs>
```

## @claude PR Comment Format

For `gh-monitor` to pick up a comment, it must start with a route prefix:

```
@claude revision: <short description>
@claude revision-major: <short description>
@claude plan-revision: <short description>
@claude build-phase: <short description>
@claude help
```

Keep the comment concise — this is inline, not a full task file. If the task needs more than a sentence or two of context, dispatch manually with `--task-file` instead.

## Common Mistakes

- **Vague objective** — "fix auth" → better: "fix the login null-check that fails when email contains `+`"
- **No scope fence** — engineer drifts into unrelated files
- **Prescribing HOW instead of WHAT** — "use a regex to validate" closes off better approaches
- **Wrong workflow** — bulk rename on `plan-revision.sh` (301 turns, $37, no deliverable)
- **Missing done criteria** — engineer declares done when code compiles, not when behavior is verified
- **Inlining long context** — multi-paragraph task hits command-line parsing issues; use `--task-file`

## Related

- `docs/standards/workflow-scripts.md` — workflow script implementation standards
- `docs/guide/workflows.md` — user-facing workflow documentation
- Global `CLAUDE.md` Personal Tooling section — invocation templates
