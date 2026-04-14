---
name: standards-enforcement
description: How to verify code conformance against project standards — CLAUDE.md chains, docs/standards/, architecture docs, and existing exemplars. Use when auditing changes for standards compliance, reviewing PR conformance, or checking that new code follows established patterns. Pairs with documentation-structure for understanding where standards live.
---

# Standards Enforcement Methodology

This skill defines **how to verify that code conforms to project standards**. It covers discovering what standards apply, finding exemplars of correct usage, auditing changes against those standards, and reporting findings with confidence scores.

## First Principles

### Standards Are Layered
Projects define standards at multiple levels. Read them in priority order:
1. **Root CLAUDE.md** — project-level instructions and overrides
2. **Nested CLAUDE.md files** — directory-specific rules in touched directories
3. **docs/standards/*.md** — explicit convention documents
4. **docs/architecture/** — design decisions that constrain implementation
5. **Existing code** — exemplar files that demonstrate established patterns

Higher layers override lower ones. If CLAUDE.md says "use tabs" and a standards doc says "use spaces," CLAUDE.md wins.

### Exemplars Are the Ground Truth
Written standards describe intent. Existing code that follows those standards demonstrates reality. When auditing, **always grep for existing exemplars** before judging new code — the project may have evolved past its written standards.

### Confidence Requires Evidence
Every finding must cite what standard it violates and what evidence supports the violation. Vague findings ("this doesn't feel right") are not actionable. Cite the standard document, the exemplar, or the CLAUDE.md rule.

### Not Every Standard Applies to Every Change
A CSS change doesn't need auditing against API design standards. Pull only the standards documents relevant to the files and patterns being changed.

## Discovery Process

Before auditing, discover what standards apply to the changes under review.

### Step 1: Read the CLAUDE.md Chain
1. Read the root `CLAUDE.md` at the repository root
2. For each directory containing changed files, check for a nested `CLAUDE.md`
3. Note any rules, conventions, or references to standards docs

### Step 2: Identify Relevant Standards
Based on what was changed, pull the specific `docs/standards/*.md` files that apply:
- Changed a workflow script? → Read `docs/standards/workflow-scripts.md`
- Changed an agent? → Read `docs/standards/agents.md`
- Changed a skill? → Read `docs/standards/skills.md`
- Changed a hook? → Read `docs/standards/hook-scripts.md`
- Changed a service? → Read `docs/standards/services.md`
- Changed a slash command? → Read `docs/standards/slash-commands.md`
- Changed documentation? → Read the documentation-structure skill

Don't read standards docs that aren't relevant to the changes.

### Step 3: Check Architecture Docs
If `docs/architecture/` exists, scan for ADRs relevant to the changed area. Architecture decisions constrain implementation — a change that contradicts an ADR is a standards violation.

### Step 4: Find Exemplars
For each type of artifact being changed, grep for existing exemplars:
- Adding a new agent? → Read 2-3 existing agents in `config/agents/`
- Adding a new skill? → Read 2-3 existing skills in `config/skills/`
- Adding a new workflow? → Read an existing workflow in `scripts/workflows/`
- Adding a new hook? → Read an existing hook in `config/hooks/`

Exemplars tell you what the project actually does, which may differ from what standards documents say. Note discrepancies.

## Audit Process

With standards discovered, audit the changes systematically.

### For Each Changed File:
1. **Identify applicable standards** — which docs/rules govern this file type?
2. **Compare against standards** — does the file follow the documented conventions?
3. **Compare against exemplars** — does the file match how similar files are structured?
4. **Check CLAUDE.md compliance** — does the file follow project-level rules?
5. **Score confidence** — how certain are you that this is a real violation?

### Confidence Scoring
Rate each finding on a 3-tier scale:

- **High confidence** — clear violation of an explicit rule with evidence (e.g., "standards doc says MUST use kebab-case, file uses camelCase")
- **Medium confidence** — deviation from established patterns without an explicit rule (e.g., "all other agents use Sonnet model, this one doesn't specify")
- **Low confidence** — possible issue but standards are ambiguous or exemplars are inconsistent (e.g., "some hooks use jq, others use grep, unclear which is standard")

Only report High and Medium confidence findings as violations. Low confidence findings go in an informational section.

## What to Look For

### Structural Conformance
- Required frontmatter fields present and correct
- File naming follows conventions (kebab-case, correct directory)
- File organization matches expected structure
- Required sections present in expected order

### Pattern Conformance
- New code follows patterns established by exemplars
- Integration points use the same patterns as existing integrations
- Naming conventions match project style
- Error handling matches project patterns

### CLAUDE.md Compliance
- Rules from root CLAUDE.md are followed
- Directory-specific rules from nested CLAUDE.md files are followed
- Referenced standards are actually read and applied

### Architecture Compliance
- Changes don't contradict ADR decisions
- New patterns align with documented architecture
- Integration points match system design

## Red Flags

Watch for these common standards violations:
- Missing required frontmatter fields in agents/skills
- Skills referenced in agent prompts but not listed in `skills:` frontmatter
- Workflow scripts missing required features (verbose flag, JSONL logging, safety pragma)
- Hook scripts reading env vars instead of stdin JSON
- Files in wrong directories or with wrong naming conventions
- New patterns that ignore existing exemplars
- Hardcoded values that should use environment variables

## Integration With Workflows

This skill is loaded by the standards-auditor agent during review stages in:
- **revision-major.sh** — Stage 7 (STANDARDS), after code review and refactoring evaluation
- **build-phase.sh** — Stage 7 (STANDARDS), same position in the review pipeline
- **revision.sh** — inline discovery reminder only (no dedicated standards stage)

The standards-auditor focuses on **project-specific conformance** — not general code quality (code-reviewer) or structural improvement (refactoring-evaluator). Its unique value is connecting changes back to the project's documented standards and existing patterns.
