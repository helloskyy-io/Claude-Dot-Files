---
name: documentation-structure
description: How to structure project documentation — what folders to use, what goes in each, document formats and templates, file naming conventions. Use when creating or organizing files in docs/, deciding where content belongs, writing ADRs, phase docs, standards docs, or user guides. Also use when setting up a new project's documentation layout.
---

# Documentation Structure

This skill is the foundation for all documentation work. It defines WHERE things go, HOW to format them, and WHAT the conventions are. Other skills reference this one for placement and format rules.

## First Principles

### Documentation Has Three Concerns
Every piece of documentation answers one of three questions:

1. **WHY** — why we made a decision, what trade-offs were considered
2. **WHAT** — what we're building, what the roadmap is, what the work is
3. **HOW** — how to do things (conventions, standards, processes)

Plus one audience concern:

4. **OPERATING MANUAL** — what a user of the product needs to know

These map directly to the four documentation buckets.

### Documentation Must Match Reality
Documentation that drifts from reality is worse than no documentation. If a doc becomes stale, either update it or delete it. Never let it mislead.

### Write for Your Future Self and Your Team
You're not writing for today. You're writing for the person (future you included) who joins the project 6 months from now and needs to understand why things are the way they are.

## The Four Buckets + Meta-Files

```
docs/
├── file_structure.txt      ← META (map of the repo — not in any bucket)
├── development/            ← THE WHAT (roadmap, phases, and the research that drives them)
├── standards/              ← THE HOW (conventions, patterns)
│   └── architecture/       ← THE WHY (system design) — a standards sub-bucket, not a peer
└── guide/                  ← THE OPERATING MANUAL (user-facing docs)
```

**Key principle:** Every doc belongs in exactly one bucket. If you're unsure which, ask: "Is this about WHAT we're doing (development), HOW we do things — including WHY the system is shaped this way (standards), or how to USE it (guide)?"

**Architecture nests under standards rather than sitting beside it.** A system overview is a statement of how the system is built and is read alongside the conventions that govern it, not as a separate corpus — and in practice an architecture bucket at top level stays nearly empty while inviting anything vaguely design-shaped to be filed there. Binding decisions are standards documents; architecture holds the high-level description those decisions add up to. This also matches the platform corpus, so a repo adopting both conventions does not have to reconcile two shapes.

### Meta-Files (at docs/ root level)

Some files are navigation tools or metadata about the repo itself, not content. These live at `docs/` root level, NOT in a bucket:

- **`file_structure.txt`** — annotated tree of the repo with per-directory comments explaining what each contains
- **`index.md`** (optional) — landing page for docs if needed
- **`README.md`** (rare — usually the repo-level README is sufficient)

**Why meta-files belong at the root:** They describe the docs structure itself, not any specific concern. Putting them in a bucket would be like filing the library catalog under "Philosophy."

### Bucket 1: `docs/standards/architecture/`

**Purpose:** Captures architectural decisions and system design. The WHY.

**What goes here:**
- **Standards docs** — the binding rules, one per topic (primary content)
- **System overview** — `architecture_standard.md` with high-level description
- **Component diagrams** — Mermaid or similar, showing relationships
- **Data flow** — `data-flow.md` describing how data moves
- **Tech stack** — `tech-stack.md` listing technologies and why they were chosen
- **Integration points** — `integrations.md` for external system connections

**What does NOT go here:**
- Implementation details (those go in code or standards)
- How-to guides (those go in guide/)
- Task lists (those go in development/)

**When to create:**
- Before making a significant architectural decision (surface the standards candidate as you decide; a human ratifies it)
- When onboarding needs context about system design
- When patterns emerge that warrant explicit documentation

### Bucket 2: `docs/development/`

**Purpose:** Active work tracking. The WHAT we're building and when.

**What goes here:**
- **sprint.md** — top-level roadmap with status for the whole project
- **features/** — feature specs, usually with phases nested inside (most common organization)
- **phases/** — standalone phase docs (for setup plans or non-feature-driven projects)
- **reviews/** — continuous improvement reports from workflow runs (future)
- **retrospectives/** (optional) — lessons learned from completed work

**What does NOT go here:**
- Architectural reasoning (that's standards/architecture/)
- How-to instructions (that's standards/ or guide/)
- Finished work that's no longer active (archive or delete)

**When to create:**
- Start of any new feature or phase
- Whenever you need to break down work in advance
- To track progress on ongoing initiatives

**Important:** This is the MOST volatile bucket. Docs here are created, updated, and eventually archived. Do not let completed phase docs accumulate indefinitely — move them to an `archive/` subfolder or delete once merged and verified.

### Organizing Features and Phases

There are three valid organizational models for development docs. Pick the one that matches how the project actually works.

**Model A: Feature-driven (MOST COMMON, default for software projects)**

Features are the primary unit of work. Each feature may have multiple phases.

```
development/
├── sprint.md
└── features/
    ├── auth/
    │   ├── overview.md
    │   ├── phase-1-data-model.md
    │   ├── phase-2-endpoints.md
    │   └── phase-3-ui.md
    ├── billing/
    │   ├── overview.md
    │   └── phase-1-stripe-integration.md
    └── notifications/
        └── overview.md       # single-phase feature, no nested phases
```

Use Model A when the project is organized around discrete features that each have their own development lifecycle. This is the default for most software products.

**Model B: Phase-driven (milestone-based)**

Phases are project-level milestones. Each phase contains work on multiple features.

```
development/
├── sprint.md
└── phases/
    ├── phase-1-mvp/
    │   ├── overview.md
    │   ├── auth.md
    │   ├── billing.md
    │   └── database.md
    └── phase-2-v1/
        ├── overview.md
        ├── advanced-auth.md
        └── reporting.md
```

Use Model B when the project ships in discrete versions or milestones and features are coordinated across phases (e.g., "MVP", "V1", "V2").

**Model C: Flat (setup plans or small projects)**

Phases are sequential milestones in a single project, no features involved.

```
development/
├── sprint.md
├── phase-1-cross-device-sync.md
├── phase-2-safety-guardrails.md
└── phase-3-planning-agents.md
```

Use Model C when the ENTIRE project is a phased plan (like a migration, setup, or infrastructure project). This repo uses Model C because it IS a phased migration plan, not a feature-driven product.

**How to choose:**
- **Building a product with discrete features?** → Model A
- **Shipping in milestones/versions?** → Model B
- **Executing a phased setup or migration?** → Model C
- **Mixed needs?** → Model A is the safest default, add phase docs for cross-cutting milestones if needed

**Don't switch models mid-project.** Pick one early and stick with it. Restructuring causes churn and confusion.

### Bucket 3: `docs/standards/`

**Purpose:** Rules and conventions. The HOW we do things consistently.

**What goes here:**
- Per-topic convention files:
  - `code-style.md` — language-specific style rules
  - `git-workflow.md` — branching, commit format, PR process
  - `testing.md` — project-specific testing setup (references the testing-methodology skill)
  - `api-design.md` — API naming, versioning, error handling
  - `security.md` — security requirements and practices
  - `naming-conventions.md` — how to name files, functions, variables
  - `documentation.md` — project-specific doc conventions (if any beyond this skill)

**What does NOT go here:**
- Decisions (those become standards documents — this repo does not use numbered ADRs)
- Task lists (those go in development/)
- User-facing content (that goes in guide/)

**When to create:**
- When a pattern needs enforcement across multiple files or contributors
- When "how we do X" needs to be documented for consistency
- Before a new contributor joins

**A standard, not an ADR:** a standard is "we do X this way", stated in the present tense and amended when it changes. The ADR shape — "we decided X over Y and here's why" (documents the decision). Sometimes you'll have both: an ADR that documents the decision to adopt a standard, then the standard itself.

### Bucket 4: `docs/guide/`

**Purpose:** User-facing documentation. The OPERATING MANUAL.

**What goes here:**
- **Getting started** — `getting-started.md` or `quickstart.md`
- **Concepts** — conceptual explanations of how things work
- **How-to guides** — task-oriented documentation
- **Reference** — lookup-oriented information (API references, CLI options)
- **Troubleshooting** — `troubleshooting.md` for common issues
- **FAQ** — `faq.md` if applicable

**What does NOT go here:**
- Internal design decisions (those go in standards/architecture/)
- Development work-in-progress (those go in development/)
- Team conventions (those go in standards/)

**When to create:**
- Before releasing to any user (including yourself later)
- When a feature has non-obvious usage
- When the same question gets asked multiple times

**Diátaxis framework (optional, for larger projects):**
For mature products, consider splitting guide/ into four sub-areas:
- `guide/tutorials/` — learning-oriented (for beginners)
- `guide/how-to/` — task-oriented
- `guide/reference/` — information-oriented
- `guide/concepts/` — understanding-oriented

Most projects don't need this complexity. Flat files in `guide/` are fine until you have 10+ user-facing docs.

## Maintaining `file_structure.txt`

The `file_structure.txt` file is a special meta-document that serves as a quick-scan map of the repo. It should exist at `docs/file_structure.txt` in every project.

### Purpose
- Fast reference for humans and Claude — "what's in this repo?"
- Living index that reflects current reality
- Faster than `tree` + remembering what each file does

### Format

An ASCII tree with right-aligned comments explaining each file or directory:

```
project-name/
├── src/                                   # Source code
│   ├── auth/                              # Authentication module
│   │   ├── login.ts                       # Login handler
│   │   └── session.ts                     # Session management
│   └── models/                            # Data models
│       └── user.ts                        # User model
│
├── docs/
│   ├── architecture/                      # Architecture standards and system design
│   ├── development/                       # Roadmap and phase docs
│   ├── standards/                         # Coding conventions
│   ├── guide/                             # User-facing documentation
│   └── file_structure.txt                 # This file
│
├── CLAUDE.md                              # Project instructions for Claude
├── README.md                              # Repo documentation
└── package.json                           # Dependencies
```

### Format Rules

- **ASCII tree characters:** `├── │ └──` for the hierarchy
- **Right-aligned comments:** Use `#` prefix, align with other comments for readability
- **Comment content:** Describe the purpose, not the contents (say "Authentication module" not "auth.ts, session.ts, password.ts")
- **List directories before files** at each level
- **Include all major files and directories** — skip node_modules, .git, etc.
- **Use blank lines** to separate logical sections if the tree is long

### Component Boundary Rule

If a subdirectory or component has its own `docs/file_structure.txt`, stop at that component's directory name with a comment noting it is self-documenting. Do not expand into its internals — the component owns its own map.

```
monorepo/
├── services/
│   ├── api/                               # API service (see its own docs/file_structure.txt)
│   └── worker/                            # Background worker (see its own docs/file_structure.txt)
```

### Update Triggers

Update `file_structure.txt` whenever:
- A new file or directory is added at a documented level
- A file or directory is removed
- A file's purpose changes substantively
- Directory structure is reorganized

Use the `/update-file-structure` slash command to regenerate it automatically. Claude will scan the current state and propose updates.

### Why NOT Auto-Generate It

You might wonder why we maintain this manually instead of generating it from the filesystem on demand. The answer: **the comments are the value.** Filesystem listings don't explain purpose. Manual maintenance with comments creates a document that's actually useful, not just a `tree` output.

---

## Document Formats

Each bucket has expected formats. Follow these templates.

### Standards-Doc Format (Architecture)

> **This repo does NOT use numbered ADRs.** A decision that would be an ADR elsewhere is a **standards doc** here — a living rule amended in place, not a dated immutable record. `docs/standards/architecture/` holds system-architecture descriptions and tech-stack overviews, **never per-decision files**. Binding: `config/rules/standards-governance.md`.

**Filename:** `docs/standards/<topic>.md` — named for the topic it governs, never numbered. Numbering encodes a sequence that stops being true and makes reordering expensive.

**Template:**
```markdown
# <Topic> Standard

One line: what this governs and who it binds.

## The rule (binding)

State it as a rule in the present tense. Not what was decided on a date — what is true now.

## Why, and what it cost

The trade-off analysis, the alternatives considered, and the consequences accepted.
This is the part an ADR carried and the part most worth keeping.

## Breaking it looks like

Concrete, recognisable symptoms. A rule nobody can violate-detect is a preference.

## Related
```

**Rules:**

- **A standard states the rule, NEVER the completion state.** "We do X" — not "X is planned" or "X is done". Status belongs in the sprint plan.
- **Amended in place.** When the decision changes, the doc changes and the reasoning changes with it. No status field, no supersede chain, no second doc shadowing the first — git history holds the previous text.
- **Human-ratified.** Agents and autonomous runs SURFACE candidates; a human writes the standard. This is binding and has its own rule.
- **One topic per doc.** If it needs two rulings, it is two standards.

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Trade-off 1]
- [Trade-off 2]

### Neutral
- [Change in how we work]

## Alternatives Considered

### Alternative 1: [Name]
**Description:** ...
**Pros:** ...
**Cons:** ...
**Why rejected:** ...

### Alternative 2: [Name]
**Description:** ...
**Pros:** ...
**Cons:** ...
**Why rejected:** ...

## References
- Related standards: `<topic>.md`
- External links: [URL]
- Code locations: `src/path/to/file.ts`
```

**Rules for standards:**
- **Amended in place.** A standard is a living rule; when it changes, the doc changes. Superseded.
- **Write as you decide.** Don't write standards retrospectively — the context gets lost.
- **Keep them focused.** One topic per standard. If it's really two rulings, write two standards.
- **Link forward and backward.** When superseding, link both directions.

### Phase Doc Format (Development)

**Location:** `phases/<name>/README.md` — **a phase is a folder, not a file.**

Naming the doc `README.md` means browsing to the folder renders the phase doc rather than a bare file list. Naming the *folder* for the phase — never numbering it — keeps reordering free: work rarely proceeds in the sequence it was written down, and a number encodes a sequence that stops being true.

**The folder is what makes evidence co-locatable:**

```
phases/<name>/
├── README.md               the plan
└── research/<topic>/       the evidence it cites, if any
    ├── raw/<paper>.md
    └── synthesis.md
```

Research belongs *inside* the phase that cites it, not in a central corpus. Co-location beats taxonomy: a reader of the plan finds its evidence one directory away, and a reader of the evidence never has to work out which phase it serves.

**Template:**
```markdown
# Phase N: [Phase Name]

## Status
[Not started | In progress | Complete]

## Overview
[1-2 sentence summary of what this phase delivers]

## Goals
- [Goal 1]
- [Goal 2]

## Dependencies
- Phase X must be complete
- Requires [external dependency]

## Tasks

### [Task Group 1]
- [ ] **Task name** — Description of what to do and why
- [ ] **Task name** — Description (File: `path/to/file.ts`)

### [Task Group 2]
- [ ] ...

## Success Criteria
- [ ] Criterion 1 (measurable)
- [ ] Criterion 2
- [ ] Tests passing
- [ ] Documentation updated

## Risks & Mitigations
- **Risk:** [What could go wrong]
  - **Mitigation:** [How to handle it]

## Notes
[Any additional context, decisions made mid-phase, or references]
```

**Rules for phase docs:**
- Use checkboxes so progress is visible
- Keep task descriptions specific enough to be actionable
- Link to relevant standards or code
- Update status as work progresses — don't let it go stale
- Archive or delete when the phase is complete and merged

### Epic / Feature Doc Format (Development)

**Filename:** `features/<feature-name>/overview.md`

**Template:**
```markdown
# Epic: [Feature Name]

## Phase
[Which phase(s) this epic belongs to]

## Description
[What this feature does and why it exists]

## Tasks

### [Capability Group 1]
- [ ] **Task name** — description of what to do
- [ ] **Task name** — description (File: `path/to/file`)

### [Capability Group 2]
- [ ] **Task name** — description
- [ ] **Task name** — description

## Success Criteria
- [ ] Criterion 1 (measurable)
- [ ] Criterion 2

## Related
- [Requirements: FR-N](../../requirements.md)
- [Phase doc](../../phases/phase-N.md)
```

**Rules for epic/feature docs:**
- **Every task must have a checkbox** — epics are work trackers, not just descriptions. If it doesn't have checkboxes, it's not trackable.
- Capabilities should be grouped logically
- Each task should be specific enough to be actionable (not "implement the feature")
- Success criteria must be measurable and checkboxed
- Link to requirements and phase docs — epics don't exist in isolation

### Roadmap Format (Development)

The roadmap is the top-level tracking document. It shows phases and epics with **completion checkboxes** for at-a-glance progress tracking.

**Status format for phases/epics in the roadmap:**
```markdown
## Phase Overview

| Phase | Name | Status | Key Epics |
|-------|------|--------|-----------|
| 0 | [Foundation](phases/phase-0.md) | Not started | CI/CD, Dev env |
| 1 | [Walking Skeleton](phases/phase-1.md) | Not started | Core flow |

## Phase Details

### Phase 0: Foundation
- [ ] [CI/CD Pipeline](features/ci-cd/overview.md)
- [ ] [Dev Environment](features/dev-env/overview.md)
- [ ] [Coding Standards](../standards/)

### Phase 1: Walking Skeleton
- [ ] [Vault Management](features/vault-management/overview.md)
- [ ] [Credential Management](features/credential-management/overview.md)
```

**Rules for roadmaps:**
- **Every phase and epic gets a checkbox** — the roadmap is a progress tracker, not just a list
- Phase checkboxes track overall completion (checked when ALL child epics are done)
- Epic checkboxes track individual feature completion
- Link to phase docs and epic docs — the roadmap is an index, not the detail
- Keep status current — a stale roadmap misleads

### Standards Doc Format (Standards)

**Filename:** `topic.md` (no numbering needed)

**Template:**
```markdown
# [Topic] Standards

## Purpose
[What this standard covers and why it exists]

## Rules

### [Rule Category]
- **MUST:** [Strict requirement]
- **SHOULD:** [Strong recommendation]
- **MAY:** [Optional convention]

### [Another Category]
...

## Examples

### Good
```code
[example that follows the standard]
```

### Bad
```code
[example that violates the standard]
```

## Rationale
[Why these rules exist — what problems they prevent, what benefits they provide]

## Exceptions
[When is it OK to deviate from these rules? List specific exception conditions.]

## Related
- `<topic>.md`: [Related decision]
- [Link to related standard]
```

**Rules for standards:**
- Use RFC 2119 language (MUST, SHOULD, MAY) for clarity
- Provide concrete examples of good AND bad
- Explain rationale — people follow rules they understand
- Keep focused — one standard per file
- Document exceptions to avoid false rigidity

### Guide Doc Format (Guide)

**Filename:** `topic.md` or `category-topic.md`

**Template (for explanatory guides):**
```markdown
# [Feature or Concept Name]

## What Is It?
[Brief explanation for someone unfamiliar with the topic]

## When to Use
[Scenarios where this applies]

## How It Works
[The mechanics — clear, concrete explanation]

## Usage

### Basic Example
```code
[simple, working example]
```

### Common Patterns
[How people typically use this]

## Tips & Gotchas
- [Thing to watch out for]
- [Common mistake]

## Related
- [Link to related guide]
- [Link to reference]
```

**Template (for how-to guides):**
```markdown
# How to [Accomplish Task]

## Prerequisites
- [Required knowledge]
- [Required setup]

## Steps

### 1. [First step]
[Explanation and commands]

### 2. [Second step]
[Explanation and commands]

### 3. [Third step]
[Explanation and commands]

## Verification
[How to confirm it worked]

## Troubleshooting
- **Problem:** [Common issue]
  - **Solution:** [Fix]

## Related
- [Link to concept guide]
- [Link to reference]
```

**Rules for guides:**
- Write for the reader, not yourself
- Use concrete examples, not abstract descriptions
- Test that the examples actually work
- Update when the underlying thing changes
- Link to reference material rather than duplicating it

## File Naming Conventions

### Universal Rules
- **Always kebab-case.** `my-file.md`, not `My_File.md` or `myFile.md`
- **All lowercase.** Easier to type, works across case-sensitive filesystems
- **No spaces.** Use hyphens
- **Descriptive but concise.** `api-design.md` not `api-design-standards-and-conventions.md`
- **`.md` extension** for all markdown files

### Bucket-Specific Conventions

**Architecture:**
- Standards: `<topic>.md` — named for the topic, never numbered
- Other: descriptive name (e.g., `architecture_standard.md`, `tech-stack.md`)

**Development:**
- Roadmap: always `sprint.md` at the top
- Phases: `phases/<name>/README.md` — a folder per phase, named not numbered, with `research/` inside it
- Features: `features/feature-name.md`

**Standards:**
- Topic-based: `testing.md`, `security.md`, `git-workflow.md`
- No prefixes or numbering

**Guide:**
- Topic-based: `getting-started.md`, `agents.md`
- Use subfolders when content groups (e.g., `how-to/create-feature.md`)

### Numbering Discussion

Some docs benefit from numbering (phases in order). Others don't (standards, guide topics).

**Use numbers when:**
- Order matters (phases are sequential)
- There's a sequence (Phase 1 → Phase 2 → Phase 3)
- You want to preserve historical order

**Don't use numbers when:**
- Content is topic-based and independent
- Order would be arbitrary
- You'd have to renumber when adding new items

## Cross-References Between Docs

Documents should link to each other when there's a meaningful relationship.

### Relative Paths
Always use relative paths for cross-references:
```markdown
See [the stack reference](../standards/architecture/stack_reference.md) for the reasoning.
```

Not absolute URLs or broken paths.

### Common Cross-References

| From | To | When |
|------|-----|------|
| Phase doc | Standard | "We're implementing this as the standard requires" |
| Phase doc | Standard | "Follow the testing standards when implementing" |
| Standard | Standard | "This rule follows from ..." |
| Guide | Standard | "If you're curious why, see `<topic>.md`" |
| Standard | Research | "The evidence behind this rule is ..." |
| Guide | Reference | "See the API reference for details" |

### Avoid Circular Dependencies
If Doc A references Doc B and Doc B references Doc A, ask whether they should be merged or whether one should be the authority.

## When to Create Subfolders

Start flat. Add subfolders only when flat becomes unwieldy.

### Rules of Thumb
- **<5 files:** flat, no subfolders
- **5-10 files:** consider grouping by topic
- **10+ files:** definitely group, but only if meaningful groupings exist

### When Subfolders Help
- Related files that need grouping (e.g., `phases/` contains multiple phase docs)
- Mixed content types (e.g., `guide/how-to/` vs `guide/reference/`)
- Per-feature collections (e.g., `features/auth/` with multiple related docs)

### When Subfolders Hurt
- Premature organization of content that might never grow
- One file per folder (that's not organization)
- Grouping that doesn't match how people look for things

**Rule:** If you can't name the subfolder precisely, you don't need it yet.

## What NOT to Do (Anti-Patterns)

### Don't Create Docs Without Content
Empty placeholder docs are worse than nothing. They imply coverage that doesn't exist. Create docs when you have something to say, not to fill a template.

### Don't Duplicate Content
If two docs say similar things, one should link to the other. Duplicated content drifts — one version gets updated, the other goes stale. The one that's stale becomes misinformation.

### Don't Let Docs Drift
If code changes, the doc that describes it should change too. If that's not possible (too much code flux), the doc should not exist — it's just misinformation waiting to be discovered.

### Don't Document Future State
Don't write docs for features that don't exist yet. That's aspiration, not documentation. Use development/ for planning, not guide/.

### Don't Mix Buckets in One Doc
A single doc should answer one of the four questions (WHY, WHAT, HOW, USER). If your doc mixes all four, split it into multiple docs, each in the right bucket.

### Don't Use Docs as a Dumping Ground
Not every random note belongs in `docs/`. Personal notes, WIP scratch, and temporary thoughts should live elsewhere (personal notes app, issue comments, PR descriptions).

### Don't Write Docs Instead of Code
If a doc describes behavior that could be enforced in code (types, tests, linting), prefer the code. Docs are a fallback when the code can't express the concept directly.

## Integration With Workflows

This skill is foundational for workflows that create documentation:

### `build.sh` (minor builds)
- Usually doesn't need this skill — builds are code changes, not doc changes
- If the build creates or modifies docs, this skill activates

### `build.sh` (significant rework)
- May SURFACE standards candidates for major decisions; a human writes them
- May update phase docs to reflect reality
- This skill activates for those doc operations

### build.sh --phase (feature build)
- Updates phase docs as work progresses
- May SURFACE standards candidates during the build; never write one
- May create guide docs for new features
- This skill activates heavily

### `plan-new.sh` (new project setup)
- Creates the entire documentation structure from scratch
- Uses this skill for all four buckets
- This skill is a primary dependency

## Integration With Project-Level Customization

This skill captures the **default** documentation structure. Projects can override or extend it via their own `docs/standards/documentation.md` file. That file takes precedence for project-specific needs (e.g., "this project uses docs/rfcs/ instead of docs/standards/architecture/" is a valid override).

Global methodology (this skill) → Project-specific conventions (standards/documentation.md) → Actual file organization.

## Summary Checklist

When creating or organizing documentation, ask:

- [ ] Which of the four buckets does this belong in? (or is it a meta-file?)
- [ ] Does a doc for this topic already exist?
- [ ] Am I following the template for this document type?
- [ ] Is the filename kebab-case and descriptive?
- [ ] Am I linking to related docs with relative paths?
- [ ] Is this content that will be maintained, or will it drift?
- [ ] Does this belong in docs at all, or should it be code/tests/comments?
- [ ] If this is a decision, has it been surfaced as a standards candidate?
- [ ] If this is active work, is it in the right development model (features/phases/flat)?
- [ ] If this is a convention, is it a standard?
- [ ] If this is user-facing, is it a guide?
- [ ] Does `file_structure.txt` need updating after this change?
