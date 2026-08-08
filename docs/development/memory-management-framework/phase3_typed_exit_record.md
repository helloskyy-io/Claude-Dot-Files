# Phase 3 — The typed exit record: schema, fail-safe contract, one pair proven

**Component:** [Memory Management Framework](roadmap.md) · **Status: not started**

The design phase, and the one that proves it works on exactly **one** parent/child pair with the incumbent prose channel still in place. Rolling it across the fleet is [Phase 4](phase4_fleet_migration.md) — deliberately separate, because a phase that both designs and migrates cannot tell you which of the two it got wrong.

The shape is settled by evidence and recorded in the [roadmap's Key Decisions](roadmap.md#key-decisions): **arrangement A** — the child writes a small typed record at exit to a channel the parent owns, and the human record is rendered from it. This phase specifies it, builds it once, and proves it — **including the channel's own properties**, which are not properties of the record's format and are where the incumbent's real protections live.

---

## Requirements for completion

Done when **all** of the following hold:

1. **The envelope is written down as its own contract** — the field list from [Phase 1](phase1_measure_the_channel.md) E6, each field with its named consumer and its **publish classification**, and the explicit statement that every field the parent does not read is not load-bearing.
2. **The record's authorship is ruled on** — model-authored under prompt instruction, or harness-derived from what the model wrote. These are different designs and only one of them is arrangement A.
3. **The abstention member is split in two** — a computed *could-not-check* arm and an asserted *needs-a-ruling* arm, each with its own emitter, reliability claim, and remedy.
4. **The fail-safe contract is total across all four absence modes** — absent, unparseable, **stale**, and **unknown `schema_version`** — each routing to the arm requiring a human, and each proven by its own test.
5. **The channel's properties are specified, not just the record's** — fresh per invocation, run-identity-bound, anchored outside the worktree.
6. **One parent routes on the typed record end-to-end**, with the prose VERDICT line still emitted, and both paths asserted to agree across a run set. Disagreement is a **loud failure** during this phase, not a preference.
7. **The disposition table is rendered from the record** (or reconciled to it by a write-time invariant), the archived copy carries only the publishable subset, and `/standup` is verified against the result.
8. **Three rulings are recorded:** the disagreement policy, the to-do-bit ownership, and the cross-language schema ownership.

**Out of scope, and explicitly so:** other children, other parents, retiring the prose channel. `build-minor.sh` is a **second** bash parent that greps the verdict (`:281`) — it is deliberately not migrated here, and [Phase 4](phase4_fleet_migration.md) owns it. Naming it prevents "one parent" from quietly meaning "the only parent."

---

## Dependencies

- **[Phase 1](phase1_measure_the_channel.md) — hard, but per-requirement rather than wholesale.** E6 supplies the field list; E1 supplies the transport ruling and decides whether the `is_error` composition rule has anything to compose; E2 decides whether the contract must defend against a *partial* record. **Only requirements 8's disagreement policy and to-do-bit ruling block on E3** — if E3 turns out to need prospective instrumentation, the rest of this phase proceeds and those two wait.
- **[Phase 2](phase2_kind1_framework.md) — hard.** Its enumeration of what the human record carries as prose is what tells this phase which fields the schema must model and which would be lost; its consumer list and retrievability convention are what requirement 7 is verified against.
- **Cites but does not re-derive:** `claude_code_integration_surface.md` §5 and §7. **Due 2026-08-22** — if this phase runs after that, state the staleness rather than relying on it silently.
- **Constrains:** [Temporal Integration](../temporal-integration/temporal-integration.md). The handoff shape stops moving at [Phase 4](phase4_fleet_migration.md), not here.

---

## §Runtime Verification

Adopted practice, not a binding local rule — see the [roadmap's note on doc shape](roadmap.md). Required in substance because this phase writes to and reads from the `claude` CLI's output surface.

- [ ] Re-run the verification block in [Phase 1](phase1_measure_the_channel.md#runtime-verification) and record the result here, with the date and host. **Do not cite Phase 1's block as though it were current** — the CLI updates frequently, and a version recorded weeks earlier is a description, not a verification
- [ ] Record the CLI version this phase's design is built against, and state it as the pinned version in the envelope's `schema_version` rationale
- [ ] Confirm the transport chosen by Phase 1 E1 still behaves as measured, in a worktree, under `--dangerously-skip-permissions`, at a real child's turn budget

---

## Implementation steps

### 1. Specify the envelope

> **Amended by [Phase 1](phase1_measure_the_channel.md) E1 (2026-08-08) — three runtime-produced fields are ruled in or out by measurement, so this step does not re-litigate them.**
> - **`is_error` does NOT enter the envelope as a routing field.** Measured `is_error == (exit != 0)` on 8 of 8 forced modes; it carries nothing the propagated exit status does not.
> - **`num_turns` enters as telemetry only, never as a branch input.** The turn-cap run reported `num_turns: 2` against a cap of **1**; `subtype` states the same fact exactly and `run-claude.sh:167` already reads it.
> - **`permission_denials` is REQUIRED, and its consumer is named.** The forced-denial run exited **0** with `is_error: false` and `subtype: "success"` — every signal the fleet reads today said clean while the fleet's only in-run safety control had fired. The array and its stream event are the entire trace.
>
> **Amended by E2 (2026-08-08) — the schema is a tool the model chooses to call, so every required field must be one the child can ALWAYS fill.** A model that cannot satisfy the schema does not error; it silently omits `structured_output` on an otherwise-clean `success` run (measured). The split abstention vocabulary in step 4 is what makes "always fillable" achievable and is load-bearing for that reason, not decorative.

- [ ] Write the field list from Phase 1 E6 into this doc as the contract, with each field's named consumer beside it. A field with no consumer does not enter the envelope
- [ ] **Classify each field `publishable` or `internal`.** The archived copy goes into a PR comment, and `permission_denials[]` entries carry `tool_name` and `tool_input` — literal command lines and absolute worktree paths. Publishing those verbatim exposes the run's command history and filesystem layout permanently, and `code_routed_control_flow.md` P13 (marked *definitive*) records that redaction is the documented control here. For denials, publish the count and the matched rule; never the raw `tool_input`
- [ ] Note the consequence the classification creates and do not paper over it: **the published copy is not byte-identical to the routing copy**, so "one author, two copies" means one author and two *derived* copies, one of them filtered
- [ ] Include `schema_version` and state the version-skew rule: a parent on `main` will read records written by children in worktrees on older revisions, so skew is the normal case here, not the edge case. Rule it explicitly and **conservatively** — the evidence establishes schema evolution across independently-versioned producers and consumers as a documented hard problem with a documented industry retreat. An additive-only extension rule plus "unknown version routes to a human" is enough; a general versioning framework is not what this phase is for
- [ ] State plainly that the rich findings payload is **not** part of what the parent branches on. The parent's contract is the small envelope; the payload rides along and is never a routing input
- [ ] Declare the record's size posture. The one corroborated cap figure in this evidence base is Tekton's 4096 bytes; the general lesson is **carry references, not payloads**. Do not cite the widely-repeated GitHub Actions 1 MB / 50 MB figures — they were not found in the fetched primary
- [ ] State that aggregation stays in the producer: the child derives its verdict from its own per-finding values and states it, and a parent never re-derives a judgement about the child's judgement. Say **why** so a future refactor does not quietly move it

### 2. Rule on who authors the record

This ruling comes before the mechanism, because the two answers are different architectures and only one of them is what this component decided to build.

- [ ] **Rule it explicitly.** The `verdict`, the `hold_kind` and the findings are class-(iii) model assertions — the model chose them. So either the child is **told in its prompt** to emit the typed record (making the record model-authored, and making prompt text part of the migration surface), or a wrapper **parses** the record out of what the model wrote in prose or yaml — which is arrangement B with extra steps, and arrangement B is what this component exists to replace
- [ ] Whichever is ruled, state the consequence for [Phase 4](phase4_fleet_migration.md)'s sizing. The wire-format spec for the `pr_review:` block **already lives inside the prompt strings** (`children/review-pr.sh` and the Python tree's `disposition.md`), so a model-authored record means editing the highest-drift-risk surface in the repo, twice over
- [ ] Note the composite case honestly: some envelope fields are runtime-produced (`is_error`, `num_turns`) and cannot be model-authored at all. The record is therefore assembled from two sources, and the doc says which fields come from which

### 3. Specify the channel, not just the record

The incumbent's protections are properties of `mktemp` and an anchored regex, not of the prose format. A migration that carries the format across and leaves the channel unspecified is a **net weakening**, which this component's own bar forbids.

- [ ] **Fresh per invocation.** `build.sh` calls `review-pr` twice in one run, either side of the loop-back, and allocates a fresh `mktemp` log for each. If one path is reused, a second child that dies before writing leaves pass 1's record in place and the parent routes `MERGE` for a pass that produced nothing — making the "absent → human" arm unreachable in exactly the scenario it exists for. The parent allocates a fresh path per invocation and treats a pre-existing file at that path as an error
- [ ] **Run-identity bound.** The record carries an identity for the invocation that produced it, and the parent matches it against the invocation it dispatched. Freshness by path allocation and identity in the payload are two independent checks and both are cheap
- [ ] **Anchored outside the worktree.** Children run `git add -A && git commit`, and `research-refresh.sh` runs `git worktree remove --force`. A record written inside the worktree is either committed into the PR branch — a machine-readable dump of run internals, permanently in git history — or deleted by cleanup before a retrying parent reads it. The fleet has already shipped this bug once in a different guise; `run-claude.sh`'s own docstring records burying every V2 log by passing the worktree as the repo root
- [ ] If the transport is `structured_output` rather than a file, record that these three requirements are satisfied **by construction** and are closed rather than built — the record rides in the CLI's result envelope, with no path to own and no staleness class

### 4. Specify the split abstention vocabulary

- [ ] Define the **computed** arm — *could-not-check*. Emitted by a deterministic process over the run's artifacts or the runtime's own state. Name what can emit it and what cannot
- [ ] Define the **asserted** arm — *needs-a-ruling*. Emitted only by the model, and only about the work. This is what `HOLD - needs-assistance` means today, and it stays a model assertion by construction: a predicate that could detect "this needs a human" would be the ground truth it is asking for
- [ ] State the different reliability of each: the computed arm is reliable because its emitter has no incentive to guess; the asserted arm is the one the literature predicts will be **under-emitted**, and that prediction is unmeasured
- [ ] State the different remedy for each: a *could-not-check* is a defect in the checker with a fix; a *needs-a-ruling* is a request for a person and has no fix
- [ ] Record how each arm will be measured separately once emitted, so the under-emission prediction becomes a number rather than a worry

### 5. Specify the fail-safe contract

- [ ] Write the routing rules as an **ordered list, first match wins, with a documented default** — the Kubernetes `podFailurePolicy` shape, borrowed rather than designed. Routing on values the model did not author is mature and boring outside the agent corpus; this phase should look boring
- [ ] Make the residual arm a **named state that is recorded**, not a silent fall-through. Every surveyed system has an answer for the unmatched case and none of them is "fall through"
- [ ] Enumerate all four absence modes and route each to the human arm: **absent**, **unparseable**, **stale** (present but from a prior invocation), and **unknown or unsupported `schema_version`** (parses cleanly, means something else). The fourth is the one a schema-shaped contract misses, and given worktree skew it is the likeliest to occur
- [ ] **Absence must be reachable from `subtype: success` — write it as its own ordered rule.** Amended by [Phase 1](phase1_measure_the_channel.md) E2 (2026-08-08): a run where the model declines to call the `StructuredOutput` tool completes with exit **0**, `subtype: success`, `is_error: false`, a populated `.result`, and **no `structured_output` key**. The contract may not read "absent record ⟹ the run died"; that run did not die. Its residual-arm population explicitly includes *"the model declined to call the tool"*
- [ ] **A non-empty `permission_denials[]` routes to the human arm and never to automatic redispatch.** Auto-redispatching a child that just tripped the fleet's only in-run safety control is an unbounded retry loop against the one control there is
- [x] ~~If Phase 1 E2 found a partial record can exist, add a **consumer-side completeness check the parent enforces**~~ — **DROPPED by E2's ruling (2026-08-08).** 0 of 4 forced deaths (turn-cap, budget, `SIGTERM`, schema violation) produced a partial record: in every case the key is **absent entirely**, never truncated or invalid. There is no state between a validated object and no key, so neither the completeness check nor the producer-side atomic write is built. This is the transport's measured advantage over a file, and dropping the requirement is the measurement's whole point
- [ ] Write the justification paragraph on the **stationary error rate**, not on producer exceptionalism: the residual arm is load-bearing because the bad case recurs at a rate, not because it is a defect awaiting a fix. CI has well-formed-plausible-wrong results too and it is measured; a CI-literate reviewer will break the other claim

### 6. Rule the three open questions

- [ ] **Disagreement policy.** Record both the asserted verdict and the computed observable under distinct names — the raw observation is never overwritten, and the policy-adjusted value is what routing reads by default. **Amended by [Phase 1](phase1_measure_the_channel.md) E3 (2026-08-08): the off-diagonal cells are empty (0 of 14) and, more importantly, they are empty BY CONSTRUCTION — the asserted verdict rides in the same envelope key E1 measured as absent on every run where `is_error` is true, so the two rows cannot both be populated for one run at any N.** Adopt the two-name shape and **build nothing else**, and record the *structural* reason rather than the count, so a future reader does not re-take the measurement at a larger N expecting a different answer
- [ ] **Who owns the to-do bit.** Kind 1 uses open/closed; a typed record carries a verdict; the corpus's only nearby answer is *neither closes the loop*. **Amended by [Phase 1](phase1_measure_the_channel.md) E3 (2026-08-08) — this is ruled by measurement and the ruling is `open`.** The last typed verdict disagreed with the PR's terminal disposition in **6 of 7** PRs where both existed, and **31 of 38 PRs carry no typed verdict at all**. State the loser's purpose explicitly: the typed `verdict` is a **routing input for the next dispatch decision with a lifetime of one parent invocation**, not a durable record of whether work remains — and add **no machinery to reconcile the two**, which would be the composition engine the row above just declined to build
- [ ] **Cross-language schema ownership.** Two fleets exist. "Declared once per language tree" is enforceable only by an intra-tree test, which would let the bash and Python envelopes diverge with every test in both trees green — the same duplicated-vocabulary defect that produced `routing.py`, one level up. Rule between a single language-neutral schema artifact both trees load, and two declarations plus a cross-tree conformance test in `testing/suites/`. Either is defensible; silence is not
- [ ] Record all three in the [roadmap's Key Decisions](roadmap.md#key-decisions) so they are readable without opening a phase doc

### 7. Build it once and prove it

- [ ] `review-pr` writes the record at exit on the specified channel, and continues to emit the prose VERDICT line unchanged
- [ ] One parent reads the record and routes on it, with the prose parse retained as a **shadow**: both are computed, the typed one decides, and a mismatch fails loud
- [ ] Tests, one per absence mode: record absent → human arm; record unparseable → human arm; **record stale (left by a prior invocation at the same path) → human arm**; record with an unknown `schema_version` → human arm; record present and valid → routes as the record says. The stale case is the one a first-invocation-only test passes despite, so it must be written deliberately
- [ ] Test: the shadow comparison actually fires — mutate the typed record so the two paths disagree, and assert the loud failure occurs. A comparison that cannot fail records a protection that does not exist
- [ ] Run the shadowed pair over a real run set and record the agreement count and every disagreement with its cause
- [ ] Verify the vocabulary is declared per the requirement-8 ruling, and that no second declaration was introduced

### 8. Render the human record from the typed one

Kept in this phase rather than [Phase 4](phase4_fleet_migration.md) because it concerns exactly the child this phase already opens and proves, and its failure mode — an operator loses prose they relied on — is unrelated to the migration's failure mode of an unenumerated call site.

- [ ] The `pr_review:` block posted to the PR becomes a copy of the exit-channel record, filtered to the publishable subset. One author, two derived copies, two lifetimes
- [ ] Either render the human disposition table from the typed record (preferred — one source), or, if co-authoring persists, add the write-time invariant: every table row has a matching finding id in the record and vice versa, checked **before** the comment posts. Today they are two prose regions written in one act with no declared precedence, which is the one thing none of the surveyed instances of that arrangement permit
- [ ] Whichever is chosen, **declare that the typed region wins** — no source lets the prose region carry semantics
- [ ] Preserve the retrievability convention [Phase 2](phase2_kind1_framework.md) specified, so a later correction pass can address the block rather than page the thread
- [ ] Verify against Phase 2's consumer list that every reader still reads what it needs. `/standup` parses this block and must be checked, not assumed

### Close-out

- [ ] Every requirement above is met and its evidence is in this doc
- [ ] The prose channel is still live and unchanged — retiring it is [Phase 4](phase4_fleet_migration.md)'s decision, made against this phase's agreement data
- [ ] Any standards implication is surfaced in the [roadmap](roadmap.md#standards-amendment-candidates), not written. The `§ Composition` amendment in particular waits until this phase has *proven* the replacement — amending a standard on the strength of a plan is how a standard becomes wrong

---

## Notes and gotchas

- **The case for this phase is robustness and measurement, not a demonstrated defect.** No evidence shows the incumbent producing a wrong route; it is fail-closed, its vocabulary is three closed tokens, and it fails loud on absence. What the evidence establishes is narrower and sufficient: it is the one arrangement the corpus never ships without a write-time gate, and its failure mode is **silent** — a prose format change moves the token and the fail-closed default converts that into a spurious human-assistance route rather than an error. Phase 1 E5 is what turns this from an argument into a number.
- **Three of the incumbent's protections live in the channel, not the format** — `mktemp` freshness, per-invocation isolation, and the anchored URL regex that guarantees the extracted PR number is digits from github.com. Step 3 carries the first two; [Phase 4](phase4_fleet_migration.md) carries the third. A migration that moves the format and leaves these behind is weaker than what ships.
- **Arrangement A has a real cost and this doc must carry it.** Everything the human reads must be expressible in the typed record, or the render loses it. GitHub's SARIF consumer implements a documented subset and ignores the rest — that is the general shape of the loss, and Phase 2's prose enumeration is what keeps it from being discovered by an operator noticing something missing.
- **Do not cite SARIF or Conventional Commits as precedent for arrangement A.** SARIF is arrangement C (sibling fields on one object); Conventional Commits presupposes a rebaseable pre-merge artifact and a posted PR comment is not one.
- **Do not put the machine channel in git notes or commit trailers.** That family is metadata *about* a durable artifact and the corpus never routes a process outcome with it.
