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

Anything below is raised with `MDC-Master-Planning` rather than ignored. Each states what the section requires, why it does not land here, and what the two repos have to settle.

| Section | What it requires | The open question |
|---|---|---|
| **Sprint Foundations Pattern** | every sprint's first cluster is `§N-1`, with sub-items `N-1a`, `N-1b` | Numbered-cluster machinery. Both repos are moving away from numbered sprints, so this likely no longer fits either. **What replaces it?** |
| **Sprint Close-Out** | close-out gated on the `R`-items in `common/close_out/sprint_end_recurring.md` | That artifact is MDC's. Upstream is minimizing this section. **Adopt the minimized form when it lands.** |
| **Development Planning Files § 0** | component-vs-phase, prescribing `roadmap.md` + `phase{N}_{name}.md` | The *decision* is layout-independent and binds; the *file prescription* is master-planning's. Tracked as `C-078`: **promote §0 out of the layout-specific section upstream.** |
| **The Standup Tracker** | the tracker artifact and its lifecycle | Role difference rather than disagreement — that artifact lives upstream and this repo is its READER via `/standup`. Nothing to settle unless ownership moves. |

**A section listed here is still read.** It is not exempt from thought, it is waiting on an answer — and the answer belongs in a conversation with upstream, not in this file.

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
