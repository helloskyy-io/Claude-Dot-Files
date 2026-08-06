# Architecture

This directory holds high-level system overviews — the WHY behind how the repo is structured. Per `config/rules/standards-governance.md`, this repo does NOT use numbered ADR files. Binding architectural decisions are captured as standards documents in `docs/standards/<topic>.md`. This directory holds:

- `problem-statement.md` — **read this first.** What problem the product solves, what this repo is the first iteration of, and why coding is the first edge rather than the product
- `architectural_standard.md` — the map: layers, composition, memory, and the seams. **Deliberately concise** — it points at the standards, roadmap and phase docs rather than restating them
- Optional supporting docs: component diagrams, data-flow descriptions, threat models

## What goes here vs `docs/standards/`

| Type | Lives in | Example |
|---|---|---|
| Binding architectural decision with alternatives considered | `docs/standards/<topic>.md` | symlinks-vs-Stow rationale → `docs/standards/sync-strategy.md` |
| High-level system overview | `docs/standards/architecture/architectural_standard.md` | "here's how the layers fit together" |
| Threat model / security architecture | `docs/standards/architecture/threat-model.md` | enumerated attack classes the hooks address |
| Implementation guidance for a standard | n/a — that's `docs/guide/` | how to use a particular workflow |

If you find yourself wanting to write an ADR (`ADR-NNN-title.md`), stop. Per the standards-governance rule, that decision belongs in `docs/standards/`. The architecture-decisions skill's methodology (trade-off analysis, rationale, alternatives, consequences) still applies — but the artifact is a standards doc, not a numbered ADR.

## Related

- `config/rules/standards-governance.md` — the binding rule on standards vs ADRs
- `config/skills/documentation-structure.md` — the four-bucket documentation convention
- `docs/standards/` — binding rules
- `docs/development/` — active work tracking (roadmap, phase docs)
- `docs/guide/` — user-facing operating manuals
