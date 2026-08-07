# Phase 2 — Document Kind 1 as a framework

**Component:** [Memory Management Framework](roadmap.md) · **Status: not started**

Kind 1 — durable memory in git, read by humans and AI — is built, in daily use, and undocumented **as a framework**. It exists as prose describing behaviour in [`operations.md` § The memory model](../../guide/operations.md) and as behaviour spread across workflow prompts. This phase turns it into a stated interface, because [Phase 3](phase3_typed_exit_record.md) has to render into it and [Phase 4](phase4_fleet_migration.md) has to not break it.

**This is an authoring task, not a research question.** What the research owed Kind 1 was the *interface Kind 2 needs from it*, and that is covered.

---

## Requirements for completion

Done when a reader who has never seen this fleet can answer all four of these from the framework doc alone, without reading a workflow script:

1. **Which surface does a given outcome go to, and why that one?** Stated as a selection rule, not implied by a table of examples.
2. **What does each surface hold, for how long, and who reads it?** Including the fact that *open is the to-do bit* and what follows from it — no state files, no bookmarks, nothing marking an item as current.
3. **What exactly does the `pr_review:` block contain?** Field by field, sourced from the emitting script, with each field's consumer named.
4. **What would break if a field changed?** A consumer list per surface, so a later schema change can be checked against it rather than discovered by a broken standup.

Plus: the doc is placed in the **guide** bucket (user-facing operating manual — see [`documentation-structure`](../../../config/skills/documentation-structure.md)), and any rule it wants to make binding is **surfaced as a standards-amendment candidate in the [roadmap](roadmap.md)**, never written into `docs/standards/` by this phase.

---

## Dependencies

- **None.** Independent of [Phase 1](phase1_measure_the_channel.md); the two can run in parallel.
- **Required by:** [Phase 3](phase3_typed_exit_record.md) — its archive-as-by-product step needs the `pr_review:` field set and consumer list this phase produces. [Phase 4](phase4_fleet_migration.md) verifies against the consumer list.
- **Existing material to build from, not replace:** [`operations.md` § The memory model](../../guide/operations.md) already carries the three-surface table and the *why three* rationale. This phase extends that section or adds a sibling; it does not fork a second description of the same thing. **Two descriptions of one memory model is the failure mode this phase is meant to prevent, not create.**

---

## Implementation steps

### Establish the ground truth before writing anything

- [ ] Read the emitting script for the `pr_review:` block (`scripts/workflows/children/review-pr.sh`) and record the block's actual field set, including optional fields and their absence semantics
- [ ] Read `config/commands/standup.md` and record exactly what `/standup` parses from each of the three surfaces — this is the consumer list, and it must come from the consumer, not from the producer's idea of what it emits
- [ ] Grep the fleet for every other reader of these surfaces (`grep -rn "pr_review\|gh issue list\|gh pr list" scripts/ config/`) and add each to the consumer list
- [ ] Record any field that is **emitted but read by nobody** — those are candidates for removal, and naming them is more useful than documenting them as though they matter
- [ ] Record any field a consumer reads that the producer does not reliably emit — that is a live defect, and it is found by this comparison or not at all

### Write the framework

- [ ] State the surface-selection rule as a rule: which outcome class goes to a PR thread, which to an Issue, which to the standup tracker, and what makes them non-interchangeable. Collapsing any two is a recurring failure and the doc should say which two get collapsed and what happens when they are
- [ ] State the lifecycle of each surface explicitly, including the asymmetry: PR threads close at merge, Issues close when ruled, the tracker **never closes** and is pruned instead. A tracker that grows month over month is failing — that is a property of the framework, not a housekeeping note
- [ ] Document the `pr_review:` block as an interface: field, type, who emits it, who reads it, what absence means. Cite the emitting script rather than re-typing a schema that would then drift from it — per [Documentation Standard § Single-source codified fields](../../standards/documentation/documentation_standard.md), the doc points, it does not copy
- [ ] State what *open is the to-do bit* buys and what it costs: no bookmarks to maintain, and no way to express "current but not actionable" except by prose in the item
- [ ] State the discipline that makes the whole thing work — every surface is written by the actor that knows something and read by an actor that needs it; nothing is written "for the record" — and the corollary that an account is not the artifact, so a pointer is verified by fetching it

### Name the seam Kind 2 will attach to

- [ ] State which parts of Kind 1 are **rendered output** (and could therefore be produced from a typed record) versus **independently authored prose** (and could not) — this is the boundary [Phase 3](phase3_typed_exit_record.md) has to respect, and getting it wrong means a schema that silently drops what the operator actually reads
- [ ] Enumerate the prose the human record carries that a schema would have to model explicitly or lose — the reviewing agent's working shown to the operator is the known example. **This enumeration is the cost of arrangement A and the doc must not hide it**
- [ ] State the open question this phase does **not** answer: which channel owns the to-do bit when a typed record carries a verdict and the PR carries open/closed. [Phase 1](phase1_measure_the_channel.md) measures the disagreements; [Phase 3](phase3_typed_exit_record.md) rules. Recording it here as open is correct; ruling on it here is not

### Verify

- [ ] Walk the four completion questions above against the finished doc as a reader who has not seen the scripts — each must be answerable without opening one
- [ ] Verify every cross-reference resolves and every cited line number matches the current file, not a remembered one
- [ ] Check the doc against the existing `operations.md` section for contradiction and for duplication — a second statement of the same rule is drift waiting to happen, and the fix is a cross-reference
- [ ] Confirm nothing under `docs/standards/` was modified by this phase; anything that wants to be binding is listed in the roadmap's Standards-amendment candidates instead

---

## Notes and gotchas

- **The tracker is a GitHub issue only because of the substrate**, not because it is an issue semantically — it never closes, and items flow through it. Documenting it under the Issues surface would be a category error the framework exists to prevent.
- **`/standup` is strictly read-only, including the tracker.** Any framework statement implying an automated writer to the tracker contradicts the shipped behaviour.
- **Resist the pull to make this a standard.** It describes a system that works and is human-facing; the guide bucket is where it belongs. A rule that must bind autonomous runs is a candidate for `docs/standards/`, surfaced through the roadmap and ratified by a human.
