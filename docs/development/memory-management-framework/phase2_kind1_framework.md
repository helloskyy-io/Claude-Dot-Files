# Phase 2 — Document Kind 1 as a framework

**Component:** [Memory Management Framework](roadmap.md) · **Status: ✅ COMPLETE (2026-08-08)**

**Deliverable: [`docs/guide/memory-model.md`](../../guide/memory-model.md).** [`operations.md` § The memory model](../../guide/operations.md) is reduced to orientation plus a pointer — its table and rationale were **moved**, not copied, so there remains exactly one description of the model.

> **That sentence was false when the draft pass wrote it, and it is the finding this phase should be remembered for.** The draft reduced `operations.md`'s section but left the four-surface table, the two-question selection rule, the collapse claim, the tracker-substrate rationale and the discipline paragraph in place — a second description, which is what this phase exists to prevent. **Three independent reviewers and the fidelity pass each landed on a variant of the same thing:** a claim the artifact makes *about itself* that the artifact does not satisfy. The build-refine pass made the sentence true. **The generalisable lesson is about the verify step below, not about this instance:** *"check the doc against `operations.md` for duplication"* is a plausibility check by construction — it asks the author to re-read, which is the one thing an author cannot do neutrally. **A self-referential claim needs a mechanically falsifiable check** — grep for the strings the claim says are gone — and future phases in this component should phrase their verify steps that way.

Kind 1 — durable memory in git, read by humans and AI — is built, in daily use, and undocumented **as a framework**. It exists as prose describing behaviour in [`operations.md` § The memory model](../../guide/operations.md) and as behaviour spread across workflow prompts. This phase turns it into a stated interface, because [Phase 3](phase3_typed_exit_record.md) has to render into it and [Phase 4](phase4_fleet_migration.md) has to not break it.

**This is an authoring task, not a research question.** What the research owed Kind 1 was the *interface Kind 2 needs from it*, and that is covered.

---

## Requirements for completion

Done when a reader who has never seen this fleet can answer all four of these from the framework doc alone, without reading a workflow script:

1. **Which surface does a given outcome go to, and why that one?** Stated as a selection rule, not implied by a table of examples.
2. **What does each surface hold, for how long, and who reads it?** Including the fact that *open is the to-do bit* and what follows from it — no state files, no bookmarks, nothing marking an item as current.
3. **What exactly does the `pr_review:` block contain?** Field by field, sourced from the emitting script, with each field's consumer named — including the two fields the plan's first draft missed: the `converged` flag and the stable finding `id` slugs the child is already required to reuse verbatim across passes.
4. **What would break if a field changed?** A consumer list per surface, so a later schema change can be checked against it rather than discovered by a broken standup.
5. **How does a later dispatch RETRIEVE a prior pass's record?** Not "where is it posted" but *how is it addressed* — the surface must be locatable without paging the whole thread.

Plus: the doc is placed in the **guide** bucket (user-facing operating manual — see [`documentation-structure`](../../../config/skills/documentation-structure.md)), and any rule it wants to make binding is **surfaced as a standards-amendment candidate in the [roadmap](roadmap.md)**, never written into `docs/standards/` by this phase.

---

## Dependencies

- **None.** Independent of [Phase 1](phase1_measure_the_channel.md); the two can run in parallel.
- **Required by:** [Phase 3](phase3_typed_exit_record.md) — it cannot specify a schema without knowing what the human record carries as prose, because anything the schema does not model, the render loses. [Phase 4](phase4_fleet_migration.md) verifies fleet-wide against the consumer list this phase produces.
- **Existing material to build from, not replace:** [`operations.md` § The memory model](../../guide/operations.md) already carries the three-surface table and the *why three* rationale. This phase extends that section or adds a sibling; it does not fork a second description of the same thing. **Two descriptions of one memory model is the failure mode this phase is meant to prevent, not create.**

---

## Implementation steps

### Establish the ground truth before writing anything

- [x] Read the emitting script for the `pr_review:` block (`scripts/workflows/children/review-pr.sh`) and record the block's actual field set, including optional fields and their absence semantics
- [x] Read `config/commands/standup.md` and record exactly what `/standup` parses from each of the three surfaces — this is the consumer list, and it must come from the consumer, not from the producer's idea of what it emits
- [x] Grep the fleet for every other reader of these surfaces (`grep -rn "pr_review\|gh issue list\|gh pr list" scripts/ config/`) and add each to the consumer list
- [x] Record any field that is **emitted but read by nobody** — those are candidates for removal, and naming them is more useful than documenting them as though they matter
- [x] Record any field a consumer reads that the producer does not reliably emit — that is a live defect, and it is found by this comparison or not at all

#### Ground truth — four asserted facts this phase found FALSE

Recorded here rather than only in the framework doc, because three of them are facts *this doc itself* asserted and a reader of the plan should see the correction beside the assertion. All measured at `bcdb519`.

**Finding 1 — `/standup` is not read-only, and has not been since `1e7d6ce` / `88c4e81`. It is a writer on THREE of the four surfaces.** `gh issue edit <tracker> --body-file` (`config/commands/standup.md:83`, `:107`), `gh issue close <N> --comment <evidence>` (`:66`, `:69`), and **deleting rotated rows from `direction.md` plus correcting stale ones** (`:67`, `:105`). The read-only claim stood in this doc's gotchas *and* in three places in `operations.md`. **Consequence:** a consumer list omitting a writer is worse than no list — Phase 4 verifies fleet-wide against that list. Corrected in both docs; see [`memory-model.md` §2.3](../../guide/memory-model.md).

> **Finding 1 was itself corrected in the build-refine pass, and how it failed is the more useful half.** The draft pass wrote *"it writes in exactly two places,"* citing `config/commands/standup.md:3, § Rules`. Both halves were wrong: **line 3 states the opposite** (it forbids closing issues and editing files), and § Rules (`:174`) is `standup.md`'s **summary of itself**, which undercounts its own Stage 2 table twelve screens above it. So the pass that corrected a stale claim by reading an account instead of the artifact produced a second wrong claim — the exact failure [`memory-model.md` §1.2](../../guide/memory-model.md) names. **`standup.md` also contradicts itself** (`:3` forbids what `:66`/`:105`/`:174` direct); that is a live defect in a Kind 1 consumer, **surfaced, not fixed** — this phase does not edit prompts.

**Finding 2 — there are FOUR Kind 1 surfaces, not three.** [`direction.md`](../../standards/architecture/research/direction.md) satisfies all five interface properties: durable, human- and machine-readable, carries outcome *and* reasoning, has a to-do bit (`status: open`), addressable (`D-NNN`), survives context death. **Its to-do bit is a column in a committed markdown table, not GitHub `open`, and its writer is in the V2 Python tree.** So this fleet already runs **two bindings** of Kind 1 — which converts the interface/binding split from an argument into an observation. Documented as §2.4 and used as the evidence for §9's inherit/re-implement table.

**Finding 3 — Phase 1 E6's "nine fields" is not an enumeration of the `pr_review:` block, and reading it as one would mis-scope Phase 3.** E6 enumerated the *Kind 2 envelope* — the union of values 15 branch sites read. The block emits **~31 leaf fields**; the overlap is **4** (`verdict`≈`outcome`, `hold_kind`, `findings[].id`, `findings[].disposition`). Nothing in E6's ruling is withdrawn. What the two sets together establish is the shape of the problem: **the durable record carries roughly seven times what any machine reads**, and that ratio is the cost of arrangement A stated as a number. See §4.4.

**Finding 4 — the block marker is declared three incompatible ways, and two of them are wrong.** `review-pr.sh:142` (`test("pr_review:")`) and `review_pr_activities.py:51` (plain substring) match any comment merely *mentioning* the key; only `replay_pr_review_blocks.py:45` is fence-anchored. Measured over all 39 PRs: **18 matches vs 15, i.e. 3 false positives on 2 of the 8 PRs carrying a block.** PR #31's blocks run `pass: 1, 2, 4` because a `build-refine` comment between them was counted — **there was never a pass 3**; PR #66's single block is labelled `pass: 3` and is pass 1.

> **This changes something Phase 1 recorded as structural.** E7's *"pass numbers are not dense"* (`phase1:309`) instructs Phase 5 to derive consecutiveness from block ordering rather than the integer. **That instruction is correct and stands** — but the reason given, that non-density is a property of the archive, is wrong: it is this over-match, and it is fixable in two files. `pass:` is a durable field of the durable record and it is currently wrong on the most recently reviewed PR in the repo. **Phase 2 documents the convention and names the defect; it does not fix it** — this phase documents what exists, and the remedy is a code change. Surfaced without a tracker pointer rather than filed, per `review-pr.sh` § FILING AUTHORITY (a producing run surfaces; it does not file its own).

### Write the framework

- [x] State the surface-selection rule as a rule: which outcome class goes to a PR thread, which to an Issue, which to the standup tracker, and what makes them non-interchangeable. Collapsing any two is a recurring failure and the doc should say which two get collapsed and what happens when they are
- [x] State the lifecycle of each surface explicitly, including the asymmetry: PR threads close at merge, Issues close when ruled, the tracker **never closes** and is pruned instead. A tracker that grows month over month is failing — that is a property of the framework, not a housekeeping note
- [x] Document the `pr_review:` block as an interface: field, type, who emits it, who reads it, what absence means. Cite the emitting script rather than re-typing a schema that would then drift from it — per [Documentation Standard § Single-source codified fields](../../standards/documentation/documentation_standard.md), the doc points, it does not copy
- [x] State what *open is the to-do bit* buys and what it costs: no bookmarks to maintain, and no way to express "current but not actionable" except by prose in the item
- [x] State the discipline that makes the whole thing work — every surface is written by the actor that knows something and read by an actor that needs it; nothing is written "for the record" — and the corollary that an account is not the artifact, so a pointer is verified by fetching it

### Specify retrievability — the half of the interface nobody wrote down

A surface a later actor cannot *address* is a surface that only a human can read, which is the gap this whole component exists to close. `docs/development/cpi-decisions.md` carries a deferral whose watch-criteria are literally *"ship as part of the Memory Management phase doc"*: **a correction pass cannot machine-read the prior pass's runway** — it has the excellent `pr_review:` yaml and had to page a 37 KB comment dump to find it. That trigger has fired; this section is where it lands.

- [x] State how a subsequent dispatch locates the **latest** `pr_review:` block on a PR without reading the whole thread — the addressing convention, whatever it turns out to be (a marker, a query, an ordering rule). This is the deliverable, not the mechanism's implementation
- [x] Include the same for the pass number: a correction pass must be able to establish *which pass it is* and *what the prior pass ruled* from the surface, since `review-pr` already tracks `THIS_PASS` / `PRIOR_PASS` and already requires prior finding ids to be reused verbatim
- [x] Record the retrieval cost as it stands today (the 37 KB paging), so the improvement is measurable rather than asserted
- [x] Cross-reference the CPI entry so the deferral's resolution is traceable from both ends

### Name the seam Kind 2 will attach to

- [x] State which parts of Kind 1 are **rendered output** (and could therefore be produced from a typed record) versus **independently authored prose** (and could not) — this is the boundary [Phase 3](phase3_typed_exit_record.md) has to respect, and getting it wrong means a schema that silently drops what the operator actually reads
- [x] Enumerate the prose the human record carries that a schema would have to model explicitly or lose — the reviewing agent's working shown to the operator is the known example. **This enumeration is the cost of arrangement A and the doc must not hide it**
- [x] State the open question this phase does **not** answer: which channel owns the to-do bit when a typed record carries a verdict and the PR carries open/closed. [Phase 1](phase1_measure_the_channel.md) measures the disagreements; [Phase 3](phase3_typed_exit_record.md) rules. Recording it here as open is correct; ruling on it here is not

### Verify

- [x] Walk the five completion questions above against the finished doc as a reader who has not seen the scripts — each must be answerable without opening one
- [x] Verify every cross-reference resolves and every cited line number matches the current file, not a remembered one
- [x] Check the doc against the existing `operations.md` section for contradiction and for duplication — a second statement of the same rule is drift waiting to happen, and the fix is a cross-reference
- [x] Confirm nothing under `docs/standards/` was modified by this phase; anything that wants to be binding is listed in the roadmap's Standards-amendment candidates instead

---

## Notes and gotchas

- **The tracker is a GitHub issue only because of the substrate**, not because it is an issue semantically — it never closes, and items flow through it. Documenting it under the Issues surface would be a category error the framework exists to prevent.
- ~~**`/standup` is strictly read-only, including the tracker.** Any framework statement implying an automated writer to the tracker contradicts the shipped behaviour.~~ **FALSE as of this phase's ground-truth pass — see Finding 1 below.** `/standup` writes in exactly two places (`config/commands/standup.md:3`, § Rules). The gotcha inverted the risk: the framework statement that would have contradicted shipped behaviour was the one this bullet asked for.
- **Resist the pull to make this a standard.** It describes a system that works and is human-facing; the guide bucket is where it belongs. A rule that must bind autonomous runs is a candidate for `docs/standards/`, surfaced through the roadmap and ratified by a human.
