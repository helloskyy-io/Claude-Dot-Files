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

Roughly a third of the document describes a planning structure this repo does not have. Ignore, do not adapt:

- **Sprint Tracking**, **Sprint Close-Out**, **Cross-Roadmap Integration Pattern** — no sprints here; this repo plans in named phases (`docs/development/roadmap.md`)
- **Development Planning Files** — assumes the master-planning layout
- **The Standup Tracker** — that artifact lives in `mdc-master-planning`; our side is the *reader* (`/standup`), not the owner
- **Deferred Work — GitHub Issues** — the mechanism is shared, but the routing described is platform-specific

## The one that explicitly excludes us — read the note

**§ CLAUDE.md Governance says, verbatim:** *"Tooling-only CLAUDE.md files (`claude-dot-files/`) are out of scope for this governance — they govern Claude Code itself, not the platform."*

So the canonical-CLAUDE.md-tree table and its mechanical inclusion rule do **not** bind this repo. **The principle underneath them does, and we adopt it locally:**

> **A CLAUDE.md references standards; it never contains standards content.** `CLAUDE.md` in this repo carries repo purpose, layout, and a pointer to each applicable standard — and no rule that exists in `docs/standards/`.

That is the same discipline as *cross-references over repetition*, applied to the file every session reads first. The upstream exclusion is about *which corpus governs us*, not about whether the principle is sound.

## Where our doc conventions live

Ours are currently split, and the split is deliberate:

- **`config/skills/documentation-structure.md`** — the four-bucket convention (architecture = WHY, development = WHAT, standards = HOW, guide = OPERATING MANUAL). A **skill**: methodology loaded on demand when authoring.
- **`config/skills/documentation-management.md`** — the lifecycle: AUTHOR / COORDINATE / AUDIT / MAINTAIN.
- **This standard** — the binding rules that govern both.

A skill teaches *how to do it well*; a standard states *what must be true*. Do not merge them.

## Related

- `../temporal/README.md` — the same vendoring pattern, applied to the Temporal corpus
- `../../../CLAUDE.md` — the standards index this repo's sessions read first
- `../../file_structure.txt` — the annotated repo map the standard requires
