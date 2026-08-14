# Documentation Standard — vendored, and what it binds here

`documentation_standard.md` is a **verbatim MIRROR** from `helloskyy-io/MDC-Master-Planning`. Do not edit it. Amendments go upstream, then re-vendor:

```bash
scripts/helpers/vendor-standards.sh          # re-copy all vendored standards
scripts/helpers/vendor-standards.sh --check  # fail if any copy has drifted
```

**MIRROR, not FORK** — a general improvement made here is retrofitted upstream in the same work. That intent flag is required by the standard's own § *Cross-ecosystem vendored standards (binding)*, which is also what governs the Temporal copies in `../temporal/`.

---

## What binds here, and why it is worth having

These are the rules that make a doc corpus maintainable rather than merely large. All of them apply to this repo unchanged:

| Rule | What it prevents |
|---|---|
| **Standards state the rule, never completion-state** | A standard that says what has been *done* rots the moment something changes. Rules are timeless; status belongs in planning docs |
| **Single-source codified fields — cite the block, don't re-list it** | A re-typed list is a second source of truth that drifts silently. Upstream measured three such drifts, one of which shipped a cluster with no PSA enforcement |
| **Cross-references over repetition** | The same reason, generalized: content lives in one place and everything else points at it |
| **Cross-ecosystem vendored standards — mirror/fork provenance** | A vendored copy with no intent flag drifts by accident instead of by decision. Already governing this folder and `../temporal/` |
| **Repo structure documentation** | Why `docs/file_structure.txt` exists and must stay current |
| **Anti-patterns** and **Quality Checks** | The failure list, worth reading before writing any doc here |

**We were already violating the first two before this landed** — the workflow guide carried an inventory that went stale, and several standards restated content that lived elsewhere. Both were fixed by hand. The rules are what stop it recurring.

## What does NOT bind here

**The whole document binds here.** There is no ignore-list.

This section used to carry one — roughly a third of the standard was marked *"ignore, do not adapt"* on the grounds that it described a planning structure this repo does not have. That was wrong in a way that cost real work: **`Sprint Tracking` was excluded because "no sprints here", and this repo has `docs/development/sprint.md`.** The exclusion made three binding gates unreachable, including the **Capability-Parity Gate for Rewrites & Ports**, which names `bash→Temporal` explicitly while this repo is mid-port.

## Where we diverge, it is a QUESTION, not a carve-out

A permanent exclusion is a divergence nobody revisits. **A handoff gets answered once and improves both repos** — and the needs are shared, so a section that does not fit here usually does not fit upstream either.

**Four were raised on 2026-08-14 and four came back resolved** (`1ffbc27` … `dc025a6`). Three were upstream defects rather than local misfits:

| Raised | Outcome |
|---|---|
| **Sprint Foundations Pattern** mandates `§N-1` clusters, which § Sprint Structure forbids for named sprints | **Upstream defect, fixed.** A named sprint's cluster is `### Foundations`, no ordinal. The sub-letter machinery is now stated as *protection against renumbering* — so a scheme with no numbers has nothing to protect and must not invent ordinals to imitate one |
| **Sprint Close-Out** depended on MDC's `R`-item file | **Minimized, and made portable.** Close-out is a **verification gate, not a work phase** — it confirms nothing was left unplaced rather than resolving anything. The standard now requires that a recurring-check list EXIST, not which one. **Supply our own; do not build a parallel R-file** |
| **§ 0 Component vs phase** was swallowed by a layout-specific exclusion | **Promoted to its own top-level section.** The DECISION binds everywhere; the ARTIFACT SHAPES do not — and a repo with a different layout **does not get to skip the decision because its filenames differ** |
| **Standup Tracker** ownership | Reader-versus-owner asymmetry, deliberate. No action unless ownership moves |

**Two practices were codified after we reported they were habit rather than rule:** item stamps (`closed YYYY-MM-DD · ~Nh` on every delivered item) and *close-out is reopenable; delivered work is not*. Both were visible only in MDC's sprint file, and **convention does not vendor.**

**And one clause of ours was taken upstream** — *a component with no plan yet is UNPLANNED, not non-conformant* — because a conformance report that flags 11 of 13 folders trains its readers to ignore conformance reports.

## Phase numbers are IDENTITY. Do not rename them.

Recorded here because this repo came within one dispatch of renaming 16 phase files across 43 references, on the reasoning that ordinals impede reordering.

**They do not.** The standard separates three layers, and only the first is fixed:

| Layer | Mutable | Conveys |
|---|---|---|
| **Phase number** | **no** | **identity, like a ticket number** |
| Roadmap position | yes | logical order within the component |
| Sprint position | yes | execution order across components |

**The free reordering is already there** — move the line in `roadmap.md`; the filename never moves. Numbers only impede reordering if they are read *as* the order.

**Sprints are the opposite and the asymmetry is the point:** *component sprints are named, never numbered*, because there an ordinal encodes a judgement the plan exists to revise. **Phases are identities; sprints are sequences.**

## The one that explicitly excludes us — read the note

**§ CLAUDE.md Governance says, verbatim:** *"Tooling-only CLAUDE.md files (`claude-dot-files/`) are out of scope for this governance — they govern Claude Code itself, not the platform."*

So the canonical-CLAUDE.md-tree table and its mechanical inclusion rule do **not** bind this repo. **The principle underneath them does, and we adopt it locally:**

> **A CLAUDE.md references standards; it never contains standards content.** `CLAUDE.md` in this repo carries repo purpose, layout, and a pointer to each applicable standard — and no rule that exists in `docs/standards/`.

That is the same discipline as *cross-references over repetition*, applied to the file every session reads first. The upstream exclusion is about *which corpus governs us*, not about whether the principle is sound.

## Scope — this governs DOCS, not the app

`config/skills/` and `config/commands/` are **app functionality** — code and capability that Claude Code loads and executes. They are not part of the documentation corpus and this standard does not reach them. They have their own standards (`../skills.md`, `../slash-commands.md`).

That a skill happens to *teach* documentation methodology (`documentation-structure`, `documentation-management`) does not make it documentation, any more than a linter is a standard. Keep the categories apart:

- **This standard** governs `docs/` — what must be true of the corpus.
- **`../skills.md`** governs how skills are written, whatever their subject.

## On this repo's CLAUDE.md

`CLAUDE.md` at the repo root is the **standards index a session reads first** — its job is to surface which standards exist so the applicable ones get read *before* work starts. That is the mechanism, and it works.

Two files, do not confuse them:

| File | Role |
|---|---|
| `CLAUDE.md` (repo root) | The standards index for work **in this repo** |
| `config/CLAUDE.md` → `~/.claude/CLAUDE.md` | The **global** instruction stub; a redirect to `config/rules/`, and deliberately empty of content |

The rule that binds both: **a CLAUDE.md references standards, it never contains standards content.** The index points; the standard holds.

## Related

- `../temporal/README.md` — the same vendoring pattern, applied to the Temporal corpus
- `../../../CLAUDE.md` — the standards index this repo's sessions read first
- `../../file_structure.txt` — the annotated repo map the standard requires
