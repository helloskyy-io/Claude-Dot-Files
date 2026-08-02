---
name: standards-authoring
description: How to write and maintain timeless, rule-focused standards documents. Use when authoring a new standards doc, revising or amending an existing one, evaluating whether content belongs in a standard vs. a phase doc, or auditing a standards corpus for bloat. Pairs with standards-enforcement (which is about applying standards to code) and is loaded by the standards-architect agent during corpus audits.
---

# Standards Authoring Methodology

Standards documents are STABLE RULE REFERENCES. They tell future readers — humans AND AI — what to do, not how we got here. Every dispatch loads relevant standards into context, so bloat costs tokens at every prompt load and compounds over the codebase's lifetime.

This skill defines the writing/maintenance discipline. Pair it with `standards-enforcement` (which is about applying standards to code) and `documentation-structure` (which is about WHERE docs live).

## First Principles

### Standards are timeless

A reader picking up the standard 6 months from now should not need to know what sprint, PR, or date is referenced. The rule applies regardless of the historical context that produced it. If applying the rule requires knowing a temporal qualifier ("after Sprint 5"), that qualifier belongs in a phase doc or roadmap, not the standard.

### Standards bind rules, not narrative

"How we got here" is git history. "Discovered live during Sprint 1-4" is a PR description. "Originally we did X, then changed to Y" is git blame. Standards are the destination, not the journey.

### WHY content stays — but must be concise. HISTORY content goes.

Two kinds of content can appear in a standard, and they have different fates:

- **WHY content** — rationale that helps the reader judge edge cases. Example: "Use `limit:200` on first read because the Read tool truncates at 25K tokens." The WHY enables judgment when the rule's exact case isn't covered. **KEEP — but tight.**
- **HISTORY content** — narrative about how the rule came to exist. Example: "Validated during Sprint 1-4 PR #50." The HISTORY adds tokens without adding judgment capability. **REMOVE.**

The discriminator: would removing this sentence change the reader's ability to apply the rule correctly? If no, it's bloat. If yes, it's WHY content worth keeping.

### Concision is part of the rule

WHY content earns its place by being short. **One sentence. Maybe two for genuinely subtle invariants.** A paragraph of WHY for a single rule is bloat in disguise — the rationale has been padded with examples, narrative, or restatement until it crosses the line from "judgment aid" into "explainer essay."

Concision tests:
- Can the WHY be stated in one sentence? If yes, that's the version.
- Does the second sentence add new information, or just restate the first? If the latter, cut it.
- Does the WHY drift into "originally...", "we decided...", "in Sprint X..."? That's HISTORY masquerading as WHY — cut it.
- Is the WHY longer than the rule itself? Suspicious. Re-read it asking what the reader actually needs to make a judgment call.

A standards doc with 30 rules each having a 2-line WHY is a 90-line standard. A standards doc with 30 rules each having a 6-line WHY is a 210-line standard. The bloat compounds at every prompt load, every audit, every revision. Tight WHY is durable; verbose WHY rots into dated narrative over time.

### Standards are loaded into AI context every dispatch

Bloat compounds. A 50-line dated narrative attached to one rule is read by every workflow run that pulls that standard. Across hundreds of dispatches over a project's lifetime, that's tens of thousands of wasted tokens. Multiply by the number of bloated standards in the corpus.

This isn't theoretical — it's measurable cost paid at every prompt load.

## What does NOT belong in a standards document

Hard rules. None of these belong anywhere in a standards doc:

### Temporal markers

- **Dates** — `Created: 2026-04-17`, `Last Updated: 2026-04-28`. Git tracks this. Don't duplicate.
- **Status banners** — `Status: Active Standard`, `Status: Draft`. The file existing in `docs/standards/` IS the active state. A draft status is signal that the standard isn't ready and shouldn't be there yet.
- **"As of [date]..."** — anything qualified by a date will be stale tomorrow. Either the rule applies or it doesn't.
- **Version numbers tied to system state** — "applies to v1.2 onwards" belongs in a roadmap, not a standard. A standard captures what's binding now.

### Project-tracking metadata

- **Sprint references** — "validated during Sprint 1-4", "TBD at Sprint 2-3", "codified in Sprint 6-2 PR #62". Sprints and PRs are project-tracking artifacts; standards are timeless rules. Sprint references inside binding rules will outlive the sprints they reference.
- **PR numbers** — "PR #50 added this rule", "see PR #62". PR descriptions exist for narrative context. Standards don't need to repeat them.
- **Commit references** — "added at commit abc123". Git log is authoritative for this.

### Narrative and discovery prose

- **"Discovered during..."** — the rule's existence reflects whatever lesson produced it; the lesson's origin doesn't help future readers apply the rule.
- **"Originally we did X, then we changed to Y because..."** — git history captures evolution. Standards capture the current state.
- **"Lessons learned:..."** — retrospective material belongs in postmortem docs or sprint retrospectives.

### Point-in-time state

- **Verified-snapshot tables** — "Verified MDC1 topology (2026-04-26): hosts X, Y, Z". Snapshots are immediately stale and blur the line between rule and roadmap.
- **Current inventories** — "Implementation status (this MDC, 2026-04-25): X applications running". Belongs in a phase doc or operational runbook.
- **Active configurations** — current cluster configurations, service inventories. Same problem.

### Roadmap content

- **TBD-with-sprint-pointer** — "TBD, will define at Sprint 2-3". If the rule isn't binding now, it doesn't belong in the standards corpus. The TBD is roadmap material.
- **Phased rollout language** — "Phase 1: rule applies to X. Phase 2: expands to Y." Phases are roadmap; standards are binding rules.
- **Future-dependent rules** — "Once Phase 4 lands, MUST do X." If the rule isn't binding yet, it's a roadmap entry, not a standard.

## What DOES belong in a standards document

- **The rule itself** — clear, unambiguous, applicable. Use absolute language (MUST, NEVER, ALWAYS) precisely; reserve them for non-negotiable rules.
- **WHY the rule exists** — when not obvious, briefly explain rationale. The WHY enables edge-case reasoning.
- **Edge cases and exceptions** — describe when the rule doesn't apply, with the conditions for the exception.
- **Concrete examples** — patterns that illustrate correct application. Examples should be timeless (no specific PR/date references).
- **Anti-patterns** — what NOT to do, with reasoning. Useful for catching common mistakes.
- **Cross-references to related standards** — so readers can find adjacent rules. Use relative paths (e.g., `see docs/standards/agents.md`).

## Where displaced content goes

If something feels worth recording but violates the rules above, it has a home — just not in the standard:

| Content type | Belongs in |
|---|---|
| "We discovered this when..." | PR description / commit message |
| "Implementation status as of [date]" | Phase doc, roadmap, operational runbook |
| TBD items waiting on future sprints | Phase doc, roadmap, loose-ends file |
| Historical evolution of the rule | Git log / git blame |
| "Lessons learned from Sprint X" | Retrospective doc, postmortem |
| Active inventories / verified state snapshots | Operational runbook, phase doc |
| Phased rollout plans | Roadmap, phase doc |
| Sprint-time validation context | PR body that introduced the rule |

The standard captures the rule that resulted from the lesson — not the lesson itself.

## When a rule legitimately depends on system state

Sometimes the rule's applicability depends on the system being in a particular state. Two correct approaches:

1. **Wait** — write the rule when the dependency is in place. Until then, the standards corpus is silent on this topic. Better silent than misleading.
2. **Phase doc carries the rollout** — describe the staged adoption in the phase doc; let the standard codify only what's binding NOW.

Don't put "TBD at Sprint X" or "applies after Phase 4" inside a standard. The standard is for binding rules; phase docs are for roadmap.

## Red flags during writing

If you're authoring or revising a standards doc and reach for any of these phrasings, **STOP**. Each one signals you're about to add bloat:

- "As of [date]..." → dated; will be stale
- "Discovered during..." → narrative, not rule
- "Validated in PR #X" → PR-description content
- "Status: Active" → file existing IS the status
- "Verified at Sprint 1-4" → temporal qualifier
- "TBD, will codify at..." → phase-doc content
- "Implementation status as of..." → snapshot, immediately stale
- "Originally we did X, but..." → history; route to git
- "Currently MDC1 has..." → inventory; route to runbook
- "After Sprint 5..." → roadmap; route to phase doc
- "Lesson learned:..." → retrospective; route to postmortem

When you reach for "let me explain how we got here," route the explanation to git history, the PR description, or a retrospective doc instead.

## Audit guidance for standards-architect agent

The standards-architect agent uses this methodology when reviewing a standards corpus. Bloat-pattern findings, with severity:

### Critical

- **TBD-with-sprint-pointer in a binding rule** — the rule isn't actually binding; it's a roadmap entry in disguise. The standards corpus is misleading future readers about what's enforceable.
- **Contradiction between rule and project state** — e.g., a standard says "applies after Sprint 5" but Sprint 5 has shipped without the rule being in effect. Indicates the standard wasn't ready when written.

### Warning

- **Sprint/PR/date references inside binding rules** — will need cleanup as the rule outlives the references. Each reference is future cleanup work.
- **Status banners** — `Status: Active`, `Status: Draft`, `Status: Stable`. Drift signal — file existing IS the status; banners suggest the doc is being treated as a project artifact rather than a stable rule.
- **Verified-snapshot tables** — `Verified MDC1 topology (2026-04-26)` listing actual hosts/disks. Immediately stale; blurs rule vs. roadmap.
- **Point-in-time state inventories** — current Application inventories, "this MDC currently has" prose. Belongs in operational docs.

### Info

- **"Discovered live during..." narrative** — low cost to remove, low impact if left, but accumulates. Flag for next cleanup pass.
- **"Originally we did X, then..." historical evolution** — git captures this. Low impact but bloat.
- **Implementation-detail prose attached to rules** — when a rule has a paragraph of how-to-implement details that should be in a runbook.

### Audit output recommendation

When the standards-architect surfaces bloat-pattern findings, it should:

- Cite specific lines or sections where bloat appears
- Categorize each finding by type (temporal marker, narrative, snapshot, etc.)
- Recommend WHERE displaced content should go (per the table above)
- NOT auto-edit standards (per Standards Governance — surface only, human-in-the-loop for the cleanup)

## Integration With Workflows

This skill is loaded by:

- **standards-architect agent** — for corpus audits looking for bloat patterns
- **plan-revision.sh** workflows that touch `docs/standards/*` — to ensure the revision doesn't add bloat
- **plan-new.sh** workflows that author new standards — to ensure the new doc starts timeless

When standards-architect runs as part of `review-sprint.sh` or `plan-revision.sh`'s peer-review stage, bloat-pattern findings should surface in the structured report alongside the existing checks (cross-reference integrity, gap analysis, drift, etc.).

## Cross-reference

- `standards-enforcement` skill — applies standards to code (read-side discipline)
- `documentation-structure` skill — where docs live in the four-bucket convention
- `architecture-decisions` skill — methodology for the trade-off thinking that produces a standard
