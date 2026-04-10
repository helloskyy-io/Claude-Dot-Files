# Architecture

This directory captures architectural decisions and system design for this repo. It answers **WHY** we built things the way we did, not WHAT we're building (that's `docs/development/`) or HOW to use things (that's `docs/guide/` or `docs/standards/`).

## What Goes Here

### Architecture Decision Records (ADRs)

The primary content. ADRs are short documents that capture a single architectural decision: the context, the decision, the consequences, and the alternatives considered.

**Format:** `ADR-###-short-title.md` (numbered sequentially)

**Template:** See the ADR template in `config/skills/documentation-structure.md`.

**Rules:**
- Immutable once accepted — don't edit an accepted ADR except to change status to Superseded
- Write as you decide, not retrospectively
- One decision per ADR
- Link forward and backward when superseding

### Other Architecture Documents (optional)

- `system-overview.md` — high-level architecture description
- `component-diagram.md` — component relationships (Mermaid or similar)
- `data-flow.md` — how data moves through the system
- `tech-stack.md` — what technologies we use and why
- `integrations.md` — external system connections

## Current State

No ADRs written yet. This directory exists to establish the convention. ADRs will be added as architectural decisions are made going forward.

## When to Write an ADR

Write an ADR when:
- You're making a decision that will affect how the system works
- The decision has non-obvious trade-offs
- Future contributors (including future you) will need to understand WHY
- There are multiple valid alternatives and you want to document why you chose one

Don't write an ADR for:
- Routine implementation choices
- Decisions with no meaningful alternatives
- Changes that are purely cosmetic
- Decisions you made 6 months ago without documenting — those are lost context

## Related

- `config/skills/documentation-structure.md` — full documentation structure skill (activates automatically when working with docs)
- `docs/development/roadmap.md` — what we're building
- `docs/standards/` — how we do things consistently
- `docs/guide/` — user-facing documentation
