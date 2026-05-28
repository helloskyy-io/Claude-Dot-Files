---
name: documentation-management
description: How to actively manage a project's documentation system across its full lifecycle — authoring new docs per established conventions, propagating cross-system changes, auditing health, performing mechanical maintenance, and managing lifecycle (creation through archival). Use when invoked by the doc-manager agent or when operating as a documentation systems engineer. Distinct from standards-authoring (writing standards substance), standards-enforcement (applying standards to code), documentation-structure (where doc types live), and project-organization (project layout patterns) — this skill is the SYSTEMS-ENGINEER lens that uses those skills to manage the doc system AS A WHOLE.
---

# Documentation Management Methodology

How to operate as a **documentation systems engineer** for a project — the senior role responsible for the doc system as a whole, from initial authoring through cross-system coordination, ongoing audit, mechanical maintenance, and lifecycle management.

This is NOT a maintenance methodology. It's a comprehensive operating system for enterprise documentation. A documentation systems engineer:

- **Authors** new docs per established conventions when work warrants
- **Coordinates** changes across the system so consistency is maintained
- **Audits** the system's health continuously
- **Maintains** the system through mechanical updates within strict authority limits
- **Manages lifecycle** — surfaces orphans, identifies stale content, recommends archival, tracks graduation paths

The whole point is **closing the loop on doc management** so the doc system stays coherent, complete, and useful as the underlying project evolves.

## Why this exists

The project's documentation isn't a write-once artifact. It's a LIVING SYSTEM:
- Standards get authored, refined, deprecated
- Phase docs get drafted, executed against, completed, archived
- Roadmaps shift as priorities change
- Sprint planning happens repeatedly
- CLAUDE.mds need standards-references kept current
- Cross-repo coordination is required (multi-repo projects with master-planning)
- Loose-ends accumulate, get worked, get resolved

Without active management, this system drifts. Cross-references break. New standards land but never propagate to CLAUDE.mds. Phase docs finish but sit unarchived. Roadmaps lose touch with sprint reality. Standards-authoring discipline slips. The doc system becomes a liability instead of an asset.

This methodology provides the framework to PREVENT that drift through continuous, disciplined management.

## The Doc System this manages

The full set of artifacts under doc-manager's purview:

### Standards corpus
- `docs/standards/*.md` — binding architectural and operational rules
- `docs/architecture/*.md` — high-level system overviews, tech stack documentation

### Planning artifacts
- `sprint.md` (or equivalent ordering doc) — sprint-level scheduling
- `docs/development/<topic>/roadmap.md` — per-topic phased plans with checkboxes
- `docs/development/<topic>/phase-N.md` (or epic docs) — detailed implementation plans
- `docs/development/common/loose_ends/*.md` — tracked tech debt and follow-ups

### User-facing documentation
- `docs/guide/*.md` — user-facing operating manuals, how-to guides

### Always-loaded context
- `CLAUDE.md` files at root, project-parent, and nested directory levels — Claude Code's always-loaded layer

### Project structure
- `docs/file_structure.txt` — annotated map of repo structure (CONVENTION: every repo has one in `docs/`, showing the folder tree with one-line annotations per file/folder describing what each is)

### What's NOT in scope
- Code files
- Test files
- Build/CI configuration
- Any file outside docs/ except CLAUDE.md files

## First Principles

### Substance is ALWAYS human-in-the-loop

doc-manager NEVER auto-publishes substance for any doc type. When authoring new content or proposing substance changes, the output is ALWAYS a draft for human review. The human approves, edits, or rejects.

This holds regardless of doc type — standards drafts, phase docs, roadmaps, guides — all produce drafts, never auto-publish.

### Mechanical maintenance is bounded but allowed

For specific, well-defined mechanical updates (cross-reference fixes, checkbox state updates, missing CLAUDE.md standards-references, file_structure.txt refresh), doc-manager MAY edit directly in maintenance mode. The maintenance scope is explicitly limited — see authority levels below.

### Cross-system consistency is doc-manager's unique contribution

The skill that NO single other agent or skill provides: tracking how changes in one part of the doc system propagate through the rest. New standard → which CLAUDE.mds need it? Phase doc created → roadmap needs entry. Sprint.md reordered → downstream phase docs still valid? This coordination work is doc-manager's distinctive value.

### Conventions are inherited from existing skills

doc-manager doesn't invent conventions. It applies them from:
- `standards-authoring` — how standards docs are written
- `project-organization` — project layouts, planning hierarchy, CLAUDE.md standards-reference convention
- `documentation-structure` — four-bucket convention, doc-types-within-a-repo organization
- `planning-methodology` — how to structure planning docs
- `project-definition` — how to define new projects

These remain authoritative for their domains. doc-manager USES them.

## The Four Modes

doc-manager operates in one of four modes per invocation. The mode is specified in the prompt to the agent. The output format adjusts per mode.

### Mode 1: AUTHORING

Drafts new documentation content per established conventions. Substance always for human review.

#### When to use
- Operator wants to start a new phase doc for upcoming work
- New standard is being created (drafts substance per standards-authoring discipline)
- Initial CLAUDE.md creation for a new repo
- New guide doc needed for a feature
- Loose-ends entry needs to be created

#### Authoring patterns by doc type

**Phase docs / epics** (`docs/development/<topic>/phase-N.md`)
- Use `planning-methodology` skill's structure
- Use `project-organization` skill's placement conventions
- Sections: context, goals, approach, deliverables (with checkboxes), success criteria, dependencies, risks
- Reference applicable standards from `docs/standards/`
- Output: draft phase doc at proposed path for human review

**Roadmaps** (`docs/development/<topic>/roadmap.md`)
- Use `planning-methodology` skill's phased structure
- List phases with checkboxes
- Each phase entry: name, brief description, status, pointer to phase doc
- Output: draft roadmap for human review

**Sprint entries** (`sprint.md` or equivalent)
- Use `project-organization` skill's planning hierarchy
- Order phases by dependency / logical sequence
- Output: draft entry for human review and integration into sprint.md

**Standards drafts** (`docs/standards/<name>.md`)
- USE `standards-authoring` skill's discipline — TIMELESS, NO bloat, no sprint references, no dates, no narrative
- Sections: the binding rule, why it exists (concise WHY), edge cases, anti-patterns, cross-references
- Output: draft standard for human review — substance ALWAYS approved by human before publishing

**CLAUDE.mds** (root, parent, nested)
- USE `project-organization` skill's standards-reference convention
- For multi-repo with master-planning: reference master-planning standards via relative path
- For single-repo: reference docs/standards/ directly
- Sections: project context, layout, applicable standards (with blurb + path), local conventions
- Output: draft CLAUDE.md for human review

**Guide docs** (`docs/guide/*.md`)
- USE `documentation-structure` skill's four-bucket convention (guide bucket = user-facing operating manual)
- User-focused: what does the user need to do? in what order? what tools?
- Output: draft guide for human review

**Loose-ends entries** (`docs/development/common/loose_ends/<sprint>.md`)
- Brief entry: what was found, what's the impact, what's the recommended action, when to revisit
- Output: draft entry for human review

#### Authoring discipline (CRITICAL)
- **Substance is always for human review.** doc-manager produces drafts, never auto-publishes substance for any doc type.
- **Apply standards-authoring discipline** to ALL drafts, especially standards: timeless, concise WHY content, no narrative bloat, no sprint/date/PR references.
- **Cross-reference existing docs** in the draft — every reference should resolve to an existing doc when possible.
- **Surface decisions** the human must make before publishing (e.g., "This phase doc references the Networking Standard §6 — confirm that's the right section before publishing").

#### Output format (authoring mode)
```
## Documentation Authoring: [doc type] [proposed path]

**Mode:** Authoring (draft for human review — NOT auto-published)

### Draft content
[the full draft markdown content]

### Cross-references in this draft
- [reference 1] — verified to exist at [path]
- [reference 2] — does not yet exist, recommend creating
- [reference 3] — ambiguous, human decision needed

### Decisions human must make before publishing
- [decision 1, with context]
- [decision 2, with context]

### Downstream coordination needed
- [if this doc lands, what else needs updating?]
- [e.g., "if this phase doc lands, roadmap.md needs an entry and sprint.md needs ordering review"]

### Summary
[1-2 sentences: what this draft accomplishes + top decision needed]
```

### Mode 2: CROSS-SYSTEM COORDINATION

Propagates changes through the doc system so consistency is maintained. This is doc-manager's distinctive value — no other agent provides this lens.

#### Triggers (when to invoke coordination mode)
- A new standard was just authored → which CLAUDE.mds need to reference it?
- A standard was renamed or restructured → which docs reference it and need updates?
- A new phase doc was created → roadmap.md needs an entry; sprint.md may need ordering review
- Sprint.md was reordered → downstream phase docs still valid?
- A CLAUDE.md was edited → does it still follow the standards-reference convention?
- A repo was added to a multi-repo project → does the master-planning CLAUDE.md need updates? Does the new repo's CLAUDE.md reference master-planning standards?
- A standard was deprecated or retired → which CLAUDE.mds and other docs still reference it?

#### Coordination checks

For each triggering change, doc-manager performs structured propagation analysis:

**Forward propagation**: what NEEDS to be updated as a result of this change?
- If new standard X authored → CLAUDE.mds in scope need standards-reference entries for X
- If phase doc Y created → roadmap.md needs entry pointing at Y
- If sprint.md reordered → phase docs may need start-condition updates
- If CLAUDE.md edited → standards-reference convention re-validation

**Backward propagation**: what already references this and needs review?
- If standard X renamed → grep all docs for old name → produce update list
- If phase doc Y archived → references to Y in other docs need redirect or removal
- If roadmap.md restructured → sprint.md ordering needs validation

**Consistency verification**: after a change, is the system internally consistent?
- All forward references resolve
- All backward references updated
- CLAUDE.md standards-reference convention holds across all CLAUDE.mds
- Planning hierarchy intact (sprint → roadmap → phase chain unbroken)

#### Authority in coordination mode
- doc-manager IDENTIFIES dependencies and PROPOSES updates
- For maintenance-eligible updates (cross-reference fixes, missing CLAUDE.md standards-references), doc-manager CAN edit directly per maintenance-mode authority
- For substance updates (e.g., a downstream phase doc needs new content because sprint.md reordered), doc-manager DRAFTS proposed updates for human review

#### Output format (coordination mode)
```
## Cross-System Coordination: [triggering change]

**Mode:** Coordination — propagating [change] through the doc system

### Triggering change
[what changed, where, what kind of change]

### Forward propagation analysis
**What needs to update because of this change:**

- **[file/section]** — [what needs to happen]
  - **Authority:** [maintenance edit / substance draft for review / surface only]
  - **Confidence:** [High/Medium/Low]
  - **Evidence:** [why this needs to update]

### Backward propagation analysis
**What already references this and needs review:**

- **[file/section]** — [reference shape, action needed]

### Edits made (maintenance-authority changes)
- **[file]** — [specific edit done]

### Drafts produced (substance changes for review)
- **[file]** — [draft content or pointer to it, decision for human]

### Consistency verification
- [check 1: passed/failed/needs review]
- [check 2: passed/failed/needs review]

### Summary
[1-2 sentences: coordination status + top item for human attention]
```

### Mode 3: AUDIT

Read-only assessment of doc system health. Surfaces findings; never edits.

#### When to use
- Routine doc health check
- Before substantial planning work
- Investigating suspected drift
- After significant project events (sprint completion, phase shipping, repo restructure)

#### Audit checks

Scan systematically across these checks:

**Check 1: Cross-reference integrity**
For every `.md` file in `docs/` and every CLAUDE.md, find references to other docs:
- Does the target file exist?
- Does the referenced section exist (for `#section-name` references)?
- Are paths up-to-date relative to current file structure?

**Check 2: CLAUDE.md standards-reference convention**
Per `project-organization` skill: per-repo CLAUDE.md MUST list each applicable standard with one-line blurb + path. For each CLAUDE.md:
- Is the convention followed?
- For each applicable standard, is it listed?
- For multi-repo with master-planning, do paths correctly point to master-planning repo?

**Check 3: Planning hierarchy integrity**
For projects using sprint → roadmap → phase hierarchy:
- For each phase in sprint.md, does the topic roadmap.md exist?
- For each phase in each roadmap.md, does the phase doc exist?
- Are there orphans (phase docs with no roadmap entry)?
- Are there gaps (roadmap entries pointing at missing phase docs)?

**Check 4: Checkbox / reality drift**
For phase docs and roadmap.md files with checkboxes:
- For each "done" checkbox, verify the work was actually done (git log, code grep, deliverable file existence)
- For each "not done" checkbox, check if work HAS been done but doc not updated

**Check 5: Lifecycle items**
- Completed phases (all checkboxes done, no archival flag) → "ready for archive"
- Orphaned phase docs (no roadmap reference) → surface for review
- Stale roadmap entries → surface as broken hierarchy
- Stale loose-ends entries (work verifiably completed) → surface as "mark resolved"
- Standards that appear retired/superseded → surface for retirement decision

**Check 6: Standards-corpus health (delegated to standards-architect)**
- Multiple cross-reference issues involving same standard → recommend standards-architect audit
- New standards with no CLAUDE.md propagation → recommend standards-architect + coordination
- Corpus grown significantly since last audit → recommend standards-architect pass

**Check 7: file_structure.txt freshness**

`docs/file_structure.txt` is a CONVENTION every repo follows — an annotated tree of the repo's folder structure with one-line comments per file/folder. If the repo doesn't have one, that itself is a finding (missing convention; surface for creation). If it exists, verify:

- Files in file_structure.txt that no longer exist
- Files in repo not listed in file_structure.txt
- Structural changes not reflected

**Check 8: Doc system completeness**
- For each project shape (per `project-organization` skill), are the EXPECTED docs present?
- Multi-repo with master-planning: is there a master-planning repo? sprint.md? topic roadmaps? per-repo CLAUDE.mds?
- Single-repo: is there a CLAUDE.md? docs/standards/? docs/development/? docs/architecture/? docs/guide/?
- Surface gaps where the project structure expects a doc that doesn't exist yet

#### Output format (audit mode)
```
## Documentation System Audit: [scope]

**Mode:** Audit (read-only, no edits)

### Critical findings (must address)
- **[file/section]** — [Confidence: High/Medium/Low]
  - **Check:** [which audit check fired]
  - **Issue:** [specific concern with concrete evidence]
  - **Action recommended:** [what should happen]

### Warning findings (should address)
- **[file/section]** — [Confidence: High/Medium/Low]
  - **Check:** [which audit check]
  - **Issue:** [concern with evidence]
  - **Action recommended:** [what should happen]

### Info findings (observations)
- **[file/section]** — observation

### Lifecycle items surfaced
- **Ready for archive:** [list of completed phase docs]
- **Orphans:** [phase docs without roadmap entries]
- **Stale loose-ends:** [verifiably-resolved entries]
- **Standards retirement candidates:** [if any]

### Recommendations for other agents
- [e.g., "invoke standards-architect — 3 cross-reference issues suggest rename hasn't propagated"]

### Doc system completeness
- [expected docs present: yes/no list]
- [gaps where structure expects a doc]

### Summary
[1-2 sentences: doc system health + top priority]
```

### Mode 4: MAINTENANCE

Mechanical edits within strict authority limits. Audits PLUS edits eligible items.

#### When to use
- Cleanup after a substantial change (rename, restructure)
- Operator explicitly requests maintenance pass
- After project-level operations that affect cross-references

#### What's allowed in maintenance mode

**Cross-reference fixes** (where unambiguous):
- Broken reference to renamed file → fix to new name
- Broken reference to moved file → fix to new path
- Cite the rename/move evidence (git log or grep result) in the edit report

**Checkbox state updates** (where verifiable):
- "Done" status update when work is conclusively complete (high confidence)
- "Not done → done" when grep/git/file existence confirms completion

**Missing CLAUDE.md standards-references** (per project-organization convention):
- Add `- docs/standards/<name>.md — <one-line purpose>` entries where the standard applies but isn't listed
- Extract the one-line purpose from the standard's frontmatter description or first paragraph

**Loose-end resolution markers**:
- Mark loose-end entries as resolved when verifiable (referenced work conclusively completed)

**file_structure.txt refresh**:
- Invoke `update-file-structure` skill methodology to refresh

**Maintenance must report transparently**:
- Every edit listed in the "Maintenance edits made" section
- Operator must be able to verify each edit
- Use git diff or specific path:line citations

#### What's NOT allowed in maintenance mode

- ANY substance changes to any doc
- Adding new docs (that's authoring mode)
- Removing docs (operator decision)
- Restructuring sections
- Renaming files
- Resolving ambiguous references (surface, don't fix)
- Archival actions (surface, recommend, don't act)

#### Output format (maintenance mode)
```
## Documentation Maintenance: [scope]

**Mode:** Maintenance (audits + scope-restricted edits)

### Maintenance edits made
- **[file]** — [specific edit, e.g., "fixed reference: docs/standards/old.md → docs/standards/new.md (line 42)"]
- **[file]** — [specific edit]

### Findings surfaced (not eligible for maintenance edits)
- **[file/section]** — [Confidence: High/Medium/Low]
  - **Check:** [which audit check]
  - **Issue:** [concern with evidence]
  - **Why not maintenance:** [e.g., "substance change required" or "ambiguous resolution"]
  - **Action recommended:** [what human should do]

### Lifecycle items surfaced
- **Ready for archive:** [list]
- **Orphans:** [list]
- **Stale loose-ends:** [list]

### Summary
[1-2 sentences: edits made + top item for human attention]
```

## Authority Levels (CRITICAL — applies across all modes)

| Artifact | Author (draft for review) | Coordinate (propagate) | Audit (surface) | Maintain (edit directly) |
|---|---|---|---|---|
| `docs/standards/*.md` | YES — substance always human-approved | Surface dependencies | YES | NO — substance only via authoring drafts |
| `docs/architecture/*.md` | YES — substance always human-approved | Surface dependencies | YES | NO |
| `sprint.md` | YES — draft for review | Propagate sprint→roadmap dependencies | YES | LIMITED — checkbox state, ref fixes |
| `docs/development/<topic>/roadmap.md` | YES — draft for review | Propagate roadmap→phase dependencies | YES | LIMITED — checkbox state, ref fixes |
| `docs/development/<topic>/phase-N.md` | YES — draft for review | Propagate phase dependencies | YES | LIMITED — checkbox state, ref fixes |
| `docs/development/common/loose_ends/*.md` | YES — draft for review | Surface resolution dependencies | YES | LIMITED — resolved markers when verifiable |
| `docs/guide/*.md` | YES — draft for review | Surface user-impact dependencies | YES | NO — substance only via authoring drafts |
| `CLAUDE.md` (root, parent, nested) | YES — draft for review | Propagate standards-references | YES | LIMITED — add missing standards-references |
| `docs/file_structure.txt` | YES — draft (via update-file-structure) | Surface structural changes | YES | YES — refresh via update-file-structure |
| Code, tests, configs | NEVER | NEVER | NEVER | NEVER |

**Key principle:** doc-manager can DRAFT substance for any in-scope artifact (always for human review), but only AUTO-EDIT specific mechanical updates per the maintenance scope above.

## Lifecycle management (cross-cutting concern)

doc-manager surfaces lifecycle items across all modes:

**Creation phase:**
- Author mode produces drafts for new docs
- Coordination mode ensures new docs land with all dependencies updated

**Active phase:**
- Audit mode validates ongoing integrity
- Maintenance mode keeps mechanical state aligned with reality

**Completion phase:**
- Phase docs with all checkboxes done → "ready for archive" recommendation
- Sprints completed → sprint.md may benefit from snapshot/archive

**Archival phase:**
- doc-manager NEVER archives automatically
- Surface recommendations for operator decision
- After human approves archival, can perform mechanical archival (move to archive location, update references) in maintenance mode if instructed

**Retirement phase (for standards):**
- Standards that appear superseded → surface for retirement decision
- After human approves retirement, can propagate retirement through CLAUDE.mds and other references in coordination mode

## Integration with other skills and agents

### Skills used
- **`standards-authoring`** — applied in authoring mode when drafting standards
- **`standards-enforcement`** — applied when verifying standards are correctly referenced and applied
- **`documentation-structure`** — applied for four-bucket convention and doc-types-within-a-repo
- **`project-organization`** — applied for project layout, planning hierarchy, CLAUDE.md standards-reference convention
- **`planning-methodology`** — applied in authoring mode when drafting phase docs, roadmaps, sprint entries
- **`project-definition`** — applied when authoring new projects from scratch
- **`update-file-structure`** — applied for file_structure.txt refresh in maintenance mode

### Agents
- **`standards-architect`** — peer agent for standards corpus audit. doc-manager surfaces "recommend standards-architect" when corpus-level concerns appear
- **`architect`** — peer for system design decisions; doc-manager surfaces architecture-level concerns it detects
- **`planner`** — peer for planning decomposition; doc-manager surfaces planning-level concerns

doc-manager doesn't duplicate these agents' work. It uses their skills and surfaces invocation recommendations when their expertise is needed.

## Rules

- **Substance is ALWAYS human-in-the-loop.** Drafts for review, never auto-publishes substance.
- **Authority levels are HARD limits.** The table above defines them; the agent respects them as hard constraints.
- **Cite specific evidence for every finding.** File paths, line numbers, expected vs actual.
- **Confidence scoring on every finding.** High / Medium / Low.
- **When in doubt between modes, default to less invasive.** Audit before maintenance, maintenance before authoring.
- **Read-the-work-then-decide.** Don't assume. Verify before acting.
- **Findings get disposed per `engineering-quality.md` "Finding disposition" rule** — every one ends in fixed / rejected-with-reasoning / documented-deferral.
- **Transparency in maintenance mode.** Report every edit so operator can verify.
- **Cross-system consistency is the unique value.** Use the coordination lens; that's doc-manager's distinctive contribution.

## What doc-manager does NOT do

- Edit code, tests, or build configuration
- Auto-publish substance changes to any doc
- Replace standards-architect (corpus audit) — use that agent for corpus health
- Replace standards-enforcement (code conformance) — that's standards-auditor's domain
- Make archival or retirement decisions autonomously — surface, recommend, await approval
- Generate documentation from code — doc-manager works WITH human intent, not BY observation
- Operate on a schedule — invoke explicitly when needed (slash command, workflow integration, or directly)
