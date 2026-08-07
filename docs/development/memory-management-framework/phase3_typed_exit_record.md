# Phase 3 — The typed exit record: schema, fail-safe contract, one pair proven

**Component:** [Memory Management Framework](roadmap.md) · **Status: not started**

The design phase, and the one that proves it works on exactly **one** parent/child pair with the incumbent prose channel still in place. Rolling it across the fleet is [Phase 4](phase4_fleet_migration.md) — deliberately separate, because a phase that both designs and migrates cannot tell you which of the two it got wrong.

The shape is settled by evidence and recorded in the [roadmap's Key Decisions](roadmap.md#key-decisions): **arrangement A** — the child writes a small typed record at exit to a channel the parent owns, and the human record is rendered from it. This phase specifies it, builds it once, and proves it.

---

## Requirements for completion

Done when **all** of the following hold:

1. **The envelope is written down as its own contract** — the field list from [Phase 1](phase1_measure_the_channel.md) E6, each field with its named consumer, and the explicit statement that every field the parent does not read is not load-bearing.
2. **The abstention member is split in two** — a computed *could-not-check* arm and an asserted *needs-a-ruling* arm, each with its own emitter, its own reliability claim, and its own remedy.
3. **The fail-safe contract is total** — ordered rules, first match wins, a documented default, and a residual arm that is a **named state recorded in the record**, never a silent fall-through. Proven by a test that removes the record and asserts the route.
4. **One parent routes on the typed record end-to-end**, with the prose VERDICT line still emitted, and both paths asserted to agree across a run set. Disagreement between them is a **loud failure** during this phase, not a preference.
5. **The disagreement policy is ruled on** — the ruling names both values under distinct names, and if Phase 1 E3 found the off-diagonal cells empty, no composition machinery is built and this doc records that as the reason.
6. **The to-do-bit ownership question is ruled on** with Phase 1 E3's disagreement count in hand.

**Not required here, and explicitly out of scope:** other children, other parents, retiring the prose channel, and the durable-surface archive. Those are [Phase 4](phase4_fleet_migration.md).

---

## Dependencies

- **[Phase 1](phase1_measure_the_channel.md) — hard.** E6 supplies the field list; E1 supplies the transport ruling and decides whether the `is_error` composition rule has anything to compose; E2 decides whether the contract must defend against a *partial* record as well as an absent one; E3 supplies the disagreement table and the to-do-bit count; E5 decides how strongly this doc may state its own case.
- **[Phase 2](phase2_kind1_framework.md) — hard for the render boundary.** Its enumeration of what the human record carries as prose is what tells this phase which fields the schema must model and which would be lost.
- **Cites but does not re-derive:** `claude_code_integration_surface.md` §5 and §7 (envelope fields, the `system/api_retry` error enum, the absence of a first-party exit-code table). **Due 2026-08-22** — if this phase runs after that, state the staleness rather than relying on it silently.
- **Constrains:** [Temporal Integration](../temporal-integration/temporal-integration.md). The handoff shape stops moving at [Phase 4](phase4_fleet_migration.md), not here.

---

## §Runtime Verification

Required — this phase writes to and reads from the `claude` CLI's output surface.

- [ ] Re-run the verification block in [Phase 1](phase1_measure_the_channel.md#runtime-verification) and record the result here, with the date and host. **Do not cite Phase 1's block as though it were current** — the CLI updates frequently, and a version recorded weeks earlier is a description, not a verification
- [ ] Record the CLI version this phase's design is built against, and state it as the pinned version in the envelope's `schema_version` rationale
- [ ] Confirm the transport chosen by Phase 1 E1 still behaves as measured, in a worktree, under `--dangerously-skip-permissions`, at a real child's turn budget

---

## Implementation steps

### 1. Specify the envelope

- [ ] Write the field list from Phase 1 E6 into this doc as the contract, with each field's named consumer beside it. A field with no consumer does not enter the envelope
- [ ] Include `schema_version` and state the version-skew rule: a parent on `main` will read records written by children in worktrees on older revisions. Rule it explicitly — the evidence establishes schema evolution across independently-versioned producers and consumers as a documented hard problem with a documented industry retreat, and the ruling here should be *conservative and small*, not a general versioning framework
- [ ] State plainly that the rich findings payload is **not** part of what the parent branches on. The parent's contract is the small envelope; the payload rides along and is never a routing input
- [ ] Declare the record's size posture. The one corroborated cap figure in this evidence base is Tekton's 4096 bytes; the general lesson is **carry references, not payloads**. Do not cite the widely-repeated GitHub Actions 1 MB / 50 MB figures — they were not found in the fetched primary and are unverified
- [ ] State that aggregation stays in the producer: the child derives its verdict from its own per-finding values and states it, and a parent never re-derives a judgement about the child's judgement. Say **why** so a future refactor does not quietly move it

### 2. Specify the split abstention vocabulary

- [ ] Define the **computed** arm — *could-not-check*. Emitted by a deterministic process over the run's artifacts or the runtime's own state. Name what can emit it and what cannot
- [ ] Define the **asserted** arm — *needs-a-ruling*. Emitted only by the model, and only about the work. This is what `HOLD - needs-assistance` means today, and it stays a model assertion by construction: a predicate that could detect "this needs a human" would be the ground truth it is asking for
- [ ] State the different reliability of each: the computed arm is reliable because its emitter has no incentive to guess; the asserted arm is the one the literature predicts will be **under-emitted**, and that prediction is unmeasured
- [ ] State the different remedy for each: a *could-not-check* is a defect in the checker with a fix; a *needs-a-ruling* is a request for a person and has no fix
- [ ] Record how each arm will be measured separately once emitted, so the under-emission prediction becomes a number rather than a worry

### 3. Specify the fail-safe contract

- [ ] Write the routing rules as an **ordered list, first match wins, with a documented default** — the Kubernetes `podFailurePolicy` shape, borrowed rather than designed. Routing on values the model did not author is mature and boring outside the agent corpus; this phase should look boring
- [ ] Make the residual arm a **named state that is recorded**, not a silent fall-through. Every surveyed system has an answer for the unmatched case and none of them is "fall through"
- [ ] State that an absent or unparseable record routes to the arm requiring a human, never to the permissive branch — carrying the incumbent's fail-closed behaviour into the new channel rather than re-litigating it
- [ ] If Phase 1 E2 found that a partial record can exist, add the mechanism that makes a partial record indistinguishable from an absent one (atomic write, or a terminal completeness marker the parser requires) — a partial record that parses is strictly worse than no record
- [ ] Write the justification paragraph on the **stationary error rate**, not on producer exceptionalism: the reason the residual arm is load-bearing rather than decorative is that the bad case recurs at a rate, not that it is a defect awaiting a fix. CI has well-formed-plausible-wrong results too and it is measured; a CI-literate reviewer will break the other claim

### 4. Rule the two open questions

- [ ] **Disagreement policy.** Record both the asserted verdict and the computed observable under distinct names — the raw observation is never overwritten, and the policy-adjusted value is what routing reads by default. If Phase 1 E3 showed the off-diagonal cells are empty, adopt the two-name shape and **build nothing else**, recording the empty cells as the reason
- [ ] **Who owns the to-do bit.** Kind 1 uses open/closed; a typed record carries a verdict; the corpus's only nearby answer is *neither closes the loop*. Rule it, with Phase 1 E3's disagreement count cited, and state what the loser of the ruling is then for
- [ ] Record both rulings in the [roadmap's Key Decisions](roadmap.md#key-decisions) so they are readable without opening a phase doc

### 5. Build it once and prove it

- [ ] `review-pr` writes the record at exit to the caller-declared channel, and continues to emit the prose VERDICT line unchanged
- [ ] One parent reads the record and routes on it, with the prose parse retained as a **shadow**: both are computed, the typed one decides, and a mismatch fails loud
- [ ] Test: record absent → routes to the human arm. Test: record unparseable → routes to the human arm. Test: record present and valid → routes as the record says. These three are the fail-safe contract; without them it is a paragraph
- [ ] Test: the shadow comparison actually fires — mutate the typed record in a test so the two paths disagree, and assert the loud failure occurs. A comparison that cannot fail records a protection that does not exist
- [ ] Run the shadowed pair over a real run set and record the agreement count and every disagreement with its cause
- [ ] Verify the vocabulary is declared in exactly one place in each language tree — the Python tree already declares it once, and this phase must not reintroduce the second copy that a prior issue recorded the consequences of

### Close-out

- [ ] Every requirement above is met and its evidence is in this doc
- [ ] The prose channel is still live and unchanged — retiring it is [Phase 4](phase4_fleet_migration.md)'s decision, made against this phase's agreement data
- [ ] Any standards implication is surfaced in the [roadmap](roadmap.md#standards-amendment-candidates), not written. The `§ Composition` amendment in particular waits until this phase has *proven* the replacement — amending a standard on the strength of a plan is how a standard becomes wrong

---

## Notes and gotchas

- **The case for this phase is robustness and measurement, not a demonstrated defect.** No evidence shows the incumbent producing a wrong route; the incumbent is fail-closed, its vocabulary is three closed tokens, and it fails loud on absence. What the evidence does establish is narrower and sufficient: it is the one arrangement the corpus never ships without a write-time gate, and its failure mode is **silent** — a prose format change moves the token and the fail-closed default converts that into a spurious human-assistance route rather than an error. Phase 1 E5 is what turns this from an argument into a number.
- **Arrangement A has a real cost and this doc must carry it.** Everything the human reads must be expressible in the typed record, or the render loses it. GitHub's SARIF consumer implements a documented subset and ignores the rest — that is the general shape of the loss, and Phase 2's prose enumeration is what keeps it from being discovered by an operator noticing something missing.
- **Do not cite SARIF or Conventional Commits as precedent for arrangement A.** SARIF is arrangement C (sibling fields on one object); Conventional Commits presupposes a rebaseable pre-merge artifact and a posted PR comment is not one. Both are good evidence for a failure mode and bad evidence for an adoption.
- **Do not put the machine channel in git notes or commit trailers.** That family is metadata *about* a durable artifact and the corpus never routes a process outcome with it; notes additionally carry an unresolved transfer-semantics question.
