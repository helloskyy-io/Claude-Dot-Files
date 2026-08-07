---
name: project-organization
description: Project-organization patterns — multi-repo with master-planning vs single-repo /docs/, deployment-location conventions (/opt/<project>/<repo>/ for VMs, ~/Repos/<repo>/ for workstations), planning-doc hierarchy (sprint → roadmap → phase/epic), standards-reference convention in per-repo CLAUDE.md. Loads when starting work in a project repo, evaluating where standards or plans live, generating a CLAUDE.md, or navigating cross-repo references.
---

# Project Organization

How multi-component projects are structured at the repo and filesystem level, how planning docs relate to each other, and how per-repo CLAUDE.md files prime the always-loaded layer with project-specific context.

This is the meta-layer above `documentation-structure` (which is about where doc TYPES live inside a docs/ tree). Project-organization is about how REPOS themselves are organized at the filesystem level and how multi-repo projects coordinate their planning.

## First Principles

- **Cost-asymmetry favors future-proofing.** Layout decisions are cheap to make right upfront and expensive to refactor later (paths in scripts, systemd units, container mounts, CI configs all bind to layout). Always pick the layout that supports growth, even if today's project has only one repo.
- **Planning lives in one place.** For multi-repo projects, planning artifacts (standards, roadmaps, phase docs, sprint ordering) all live in a single master-planning repo. Implementation repos hold code only. This prevents drift between "the plan" and "the code."
- **CLAUDE.md primes the always-loaded layer.** Every repo's root CLAUDE.md, plus any project-parent CLAUDE.md, loads automatically into every Claude session in that directory. Use this surface deliberately to name standards, layout, and conventions the agent will need before it has the chance to fabricate from priors.

## The Two Project Shapes

### Shape 1 — Multi-repo with master-planning (default for complex projects)

```
<project-parent>/
  CLAUDE.md                         ← project-wide context: layout, per-repo summary
  <master-planning-repo>/
    CLAUDE.md
    docs/
      standards/                    ← binding architectural decisions (standards docs, never numbered ADRs)
      development/                  ← sprint.md + topic-folders with phase docs
        <topic>/sprint.md
        <topic>/phase-N.md
        common/                       ← shared cross-component planning
      architecture/                 ← high-level system/tech-stack overviews
      guide/                        ← user-facing operating manual
    sprint.md (or equivalent)       ← orders phased planning by dependency
  <implementation-repo-a>/
    CLAUDE.md                       ← per-repo: references master-planning standards
    <source code>
  <implementation-repo-b>/
    CLAUDE.md
    <source code>
```

Used when the project has multiple deployables that ship independently. Workers, services, infrastructure-as-code, observability stacks all common splits.

### Shape 2 — Single-repo with /docs/ (used for simpler projects)

```
<project-parent>/
  CLAUDE.md                         ← project-wide context
  <one-repo>/
    CLAUDE.md
    docs/
      standards/
      development/
      architecture/
      guide/
    <source code>
```

Used when the project is one deployable or library — no benefit from splitting planning out into its own repo.

### Choosing between shapes

- **Multi-repo when:** project ships multiple independent artifacts (separate deployables, separate release cadences, separate test surfaces).
- **Single-repo when:** project is a single deployable or library. Even if growth seems possible later, single-repo is fine until the second deployable actually materializes.

The migration path from single-repo to multi-repo is well-trod: split the docs/ tree into a master-planning repo, leave code in the original repo, add a project-parent CLAUDE.md. Not free, but not catastrophic.

## Deployment-Location Conventions

### On production VMs: `/opt/<project>/<repo>/`

`/opt/` is the FHS-designated location for "add-on application software packages." The `/opt/<org-or-project>/` sub-organization is widespread industry practice (Oracle, Google, major SaaS deployments).

**Always use the project-parent pattern**, even for single-repo projects that don't need it today:

```
/opt/<project>/<repo>/        ← good — supports future second repo
/opt/<repo>/                  ← avoid — forces filesystem refactor if project grows
```

The cost of one extra directory nest today is trivial. The cost of updating every path reference across scripts, systemd units, container mounts, and CI configs when the project grows is significant. Asymmetric → default to project-parent.

**"No junk" discipline:** `/opt/<project>/` is for repos only. Not scratch dirs, not build artifacts, not temp space, not unrelated tools. If you need temp space, use `/tmp/` or per-repo `tmp/`. If you need build artifacts, they belong inside a repo. The project-parent dir stays clean to preserve the "one dir = one repo" navigation property.

### On workstations: `~/Repos/<repo>/` (or equivalent)

No FHS-mandated location for workstation development. Common conventions: `~/Repos/`, `~/src/`, `~/code/`, `~/projects/`, `~/dev/`. All defensible; pick one and stay consistent.

**Project-parent dir is optional on workstations.** Workstations host many unrelated projects, so a global `~/Repos/<repo>/` flat layout is common. Use a project-parent dir only when you're actively developing multiple repos for the same project — `~/Repos/<project>/<repo>/` — and the cross-repo navigation benefits outweigh the extra nesting.

### Project-parent CLAUDE.md

Claude Code walks UP the directory tree at session start, loading CLAUDE.md at every level. A project-parent CLAUDE.md (`/opt/<project>/CLAUDE.md` or workstation equivalent) primes every session inside any sibling repo with project-wide context:

- Project-wide layout (what repos exist, what each does)
- Cross-repo conventions
- Project-wide standards (or pointer to the master-planning repo if multi-repo)

Don't duplicate per-repo content in the project-parent CLAUDE.md — it's the layer that summarizes the project, not the layer that owns each repo's specifics.

## Standards-Reference Convention (per-repo CLAUDE.md)

Per-repo CLAUDE.md MUST list each applicable standard with a one-line blurb plus a path. Format:

```markdown
## Standards

- `docs/standards/<name>.md` — <one-line purpose>
- `docs/standards/<other>.md` — <one-line purpose>
```

For multi-repo with master-planning, the path points to the master-planning repo:

```markdown
- `../<master-planning-repo>/docs/standards/<name>.md` — <one-line purpose>
```

This convention exists because the always-loaded CLAUDE.md primes the agent on what standards exist before any work begins. Without this, the agent has to discover standards on each pass (often skipping discovery and fabricating from priors). With it, the standards become first-class context.

Per-repo CLAUDE.md should reference only standards the agent will need when working in THAT repo — not the entire corpus. A backend-API repo doesn't need GitOps standards in its always-loaded layer.

## Planning-Doc Hierarchy

Multi-component projects use a three-level hierarchy for planning, with checkboxes tracking completion at each level:

```
sprint.md              ← orders phased planning by dependency / logical order
  <topic>/sprint.md   ← per-topic phased overview
    <topic>/phase-N.md ← detailed implementation plan per phase
```

- **`sprint.md`** lives at the master-planning repo root (or `docs/development/sprint.md`). Orders what gets built when. Captures dependencies across topics.
- **`<topic>/sprint.md`** lives in each topic folder under `docs/development/`. Phased overview of the topic, with checkboxes for each phase.
- **`<topic>/phase-N.md`** (or epic-named-after-the-work) lives alongside the roadmap. Detailed plan for one phase, with checkboxes for individual deliverables.

### Reading-order discipline when starting work

When starting work that touches a topic, read up the hierarchy:

1. `sprint.md` — where am I in the project sequence? What just shipped? What's next?
2. `<topic>/sprint.md` — what's the topic-level plan? Which phase am I in?
3. The specific phase/epic doc — what am I implementing right now?

Don't skip levels. Reading the phase doc alone without the surrounding sequence/topic context degrades the agent's understanding of constraints, dependencies, and "why this approach."

For single-repo projects, the same hierarchy applies inside the one repo's `docs/development/` tree.

## Cross-References

- `documentation-structure` skill — the four-bucket convention (architecture / development / standards / guide) that organizes docs WITHIN a repo. Project-organization is the layer above.
- `standards-enforcement` skill — how to apply standards once discovered. Project-organization tells the agent WHERE standards live; standards-enforcement tells it HOW to use them.
- `standards-authoring` skill — how to write timeless rule-focused standards. Project-organization is silent on standards content; it covers location and reference.
- `update-file-structure` skill — maintains `file_structure.txt`, the visual map. Project-organization references the existence of file_structure.txt as canonical structure reference but doesn't duplicate it.
