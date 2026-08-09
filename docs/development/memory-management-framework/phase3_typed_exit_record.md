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

- [x] Write the field list from Phase 1 E6 into this doc as the contract, with each field's named consumer beside it. A field with no consumer does not enter the envelope — **DEVIATION, stated rather than silent: the contract is written into [`exit-protocol.md` §2.1–§2.3](../../standards/exit-protocol.md), not into this doc.** The protocol's own §2 row says *"⟨PHASE 3⟩ writes the contract"*, so copying the table here as well would put two normative field lists in the tree, which [Documentation Standard § Single-source codified fields](../../standards/documentation/documentation_standard.md) forbids and which is the exact defect [Phase 2](phase2_kind1_framework.md) spent three passes removing from `operations.md`. This doc records the **rulings and their evidence**; the protocol carries the fields
- [x] **Classify each field `publishable` or `internal`.** Done in the protocol's rightmost column. **One field is classified out of the record entirely rather than merely marked internal:** `permission_denials[].tool_input` carries literal command lines and absolute worktree paths, and `code_routed_control_flow.md` P13 (*definitive*) records redaction as the documented control. It is dropped at read time, so there is no copy to leak — publish the count, the tool name and the matched rule
- [x] Note the consequence the classification creates and do not paper over it — **and the consequence is smaller than the checklist assumed, because of the choice above.** With `tool_input` dropped at read time, the routing copy and the published copy differ in exactly one field, `run_id`, which is an opaque nonce. *"One author, two copies"* is still one author and two *derived* copies — but the filter is one field wide, not a redaction pass, and a reader comparing them will find them otherwise identical
- [x] Include `schema_version` and state the version-skew rule — [protocol §5](../../standards/exit-protocol.md). Ruled conservatively and to the letter of the requirement: **additive-only extension, and an unknown value routes to the human arm at rule R4.** No compatibility matrix, no negotiation, no general versioning framework
- [x] State plainly that the rich findings payload is **not** part of what the parent branches on — protocol §2.1: `findings[]` carries two short fields per finding, and the parent's ordered rules (§4) read `routed_outcome` and `undetermined_reason` only. **`findings[]` rides along for Phase 5 and for step 8's invariant; no rule in §4 reads it**
- [x] Declare the record's size posture — [protocol §2.5](../../standards/exit-protocol.md). Tekton's 4096 bytes, `findings[]` exempt, and **a second bound the checklist did not anticipate**: the schema is an argument value, so its own size is a build-time cost for every caller and is asserted by a test at the same 4096 bytes. The GitHub Actions figures are not cited anywhere in this component
- [x] State that aggregation stays in the producer, and why — [protocol §3](../../standards/exit-protocol.md) and `disposition.md` Stage 6. The child aggregates its per-finding `hold_kind` values into one `hold_kind` on the envelope. **The why, so a refactor does not move it:** a parent that re-derived the token would be a caller with no stake in the review making a judgement about the review, and it would have to re-implement the reviewer's precedence rule (any `needs_ruling` beats every `redispatch`) in a second place — the duplicated-vocabulary defect that produced `routing.py`, one level up

#### Step 1 — Rulings, and the two places the measured contract departs from Phase 1 E6

**The envelope is ELEVEN child-authored fields where E6 ruled nine, and both additions were forced by a requirement E6 was not looking at.** E6 enumerated the union of values *existing branch points read*; it was not asked what the channel itself requires. Neither addition serves a hypothetical consumer.

| Departure | Why | Consumer |
|---|---|---|
| **`run_id` added** | Step 3 requires the record to be **run-identity bound** and the parent to match it against the invocation it dispatched. No E6 field carries an invocation identity | The parent's rule R5 |
| **`completion_ref.substrate` added** | [`exit-protocol.md` §1](../../standards/exit-protocol.md) requires the Kind 1 reference to be **substrate-agnostic**, and a three-part ref with no substrate discriminator forces every reader to infer the binding from the shape of a string. [Phase 2](phase2_kind1_framework.md) §9 is what makes this concrete rather than theoretical: this fleet already runs two bindings | The resolver; and any non-GitHub binding |
| **`completion_ref.number: integer` re-typed to `completion_ref.id: string`** | **A measured conflict with E6, reported as a finding rather than absorbed.** E6 typed it `integer`; *both* consumers hold it as a string today — `routing.py:100` returns `match.group(1)`, and bash `${PR_URL##*/}` is a string. An integer type would make every consumer cast, and it presumes a substrate whose record ids are numeric | **B3, P4** |

**And `permission_denials` moves stratum without changing status.** E6 listed it alongside the child-authored fields; E1(f) had already established it is produced by the runtime and invisible to the child. The protocol states it as runtime-produced (§2.2). It is **still required, still has E1(f)'s named consumer, and still routes to the human arm** — nothing about the ruling weakens; the record just says who can physically write it.

### 2. Rule on who authors the record

This ruling comes before the mechanism, because the two answers are different architectures and only one of them is what this component decided to build.

- [x] **Rule it explicitly. RULED: MODEL-AUTHORED UNDER PROMPT INSTRUCTION**, and the mechanism forces it rather than merely permitting it. Phase 1 E2 measured that `--json-schema` is implemented as a **`StructuredOutput` tool the model must call** — there is no path by which the runtime fills those parameters, so a wrapper-parses design is not available under the chosen transport even if it were wanted. It is also arrangement B with extra steps, and arrangement B is what this component exists to replace. **The prompt is therefore part of the contract surface**, and §6's last bullet (prompt-borne emission is part of the conformance surface) is what keeps that honest
- [x] State the consequence for [Phase 4](phase4_fleet_migration.md)'s sizing — **and it is smaller than the checklist feared, because of a ruling that landed after the checklist was written.** The wire-format spec does live inside prompt strings in two places, `children/review-pr.sh` and the Python tree's `disposition.md`. But the bash fleet is **frozen** ([`exit-protocol.md` §7](../../standards/exit-protocol.md)), so `children/review-pr.sh`'s prompt is never edited: it keeps emitting prose and nothing else. **Phase 4's prompt-editing surface is one file per V2 child, not two per child** — the "twice over" is retired by the freeze, not by an argument
- [x] Note the composite case honestly — done, and the doc that says which fields come from which is [`exit-protocol.md` §2.1–§2.3](../../standards/exit-protocol.md). **Three strata, not two:** the child authors what only the child knows, the runtime produces what the child cannot see (`permission_denials`), and the parent computes what neither is entitled to decide (`routed_outcome`). The checklist named `is_error` and `num_turns` as the runtime half; **both were ruled OUT of the envelope entirely by Phase 1 E1(a) and E1(b)**, so the runtime stratum's actual content is `permission_denials` alone

#### Step 2 — What the ruling costs, stated so it is paid deliberately

**A model-authored record inherits the producer's error rate, and that is the whole reason §4 is total.** The record's *presence* is model-dependent, not transport-dependent (E2(c)): a schema the model finds unsatisfiable produces silence on a clean run rather than an error. Two consequences are load-bearing and are built, not noted:

1. **Every required field must be one the child can always fill.** The abstention vocabulary in step 4 is what makes that reachable — without an in-schema way to say *"a human must decide"*, a model facing a case it cannot resolve has no option but to not call the tool at all.
2. **The parent may not treat the record's own claims about itself as evidence.** `run_id` is model-echoed, so it proves nothing on its own — it is checked *against* the value the parent generated, which is why R5 is a comparison and not a presence test. A record cannot report its own absence, and it cannot vouch for its own identity either.

### 3. Specify the channel, not just the record

The incumbent's protections are properties of `mktemp` and an anchored regex, not of the prose format. A migration that carries the format across and leaves the channel unspecified is a **net weakening**, which this component's own bar forbids.

- [x] **Fresh per invocation. BUILT, not closed.** `assistant_activities.claude_log_path()` allocates a per-invocation path and **raises if a file already exists there**, which is the checklist's requirement stated literally. The scenario it defends is real in this pair: `build_workflow` calls `review_pr` twice in one run, either side of the loop-back
- [x] **Run-identity bound. BUILT.** The parent generates a `run_id` nonce, puts it in the prompt, and rule R5 compares the record's echo against it; a mismatch routes to the human arm as `record_stale`. The two checks are independent as the checklist requires — path freshness is enforced by the filesystem, identity by the payload — and the second is what catches a record that arrived on a *correct* path from a *different* invocation
- [x] **Anchored outside the worktree. CLOSED by construction, and already enforced.** The child writes nothing: the record rides out in the CLI's own stdout, and the only thing that touches a filesystem is the parent's own redirect. `assistant_activities.run_claude` already **raises** when `repo_root` contains `.claude/worktrees` (`assistant_activities.py:270-274`), which is the same defect the checklist cites `run-claude.sh`'s docstring for. No write crosses the isolation boundary in either direction
- [x] The transport IS `structured_output` — **and the checklist's conclusion from that is measured HALF WRONG, which is this step's finding.** See below

#### Step 3 — Ruling: one of the three is closed by construction, two are not

The checklist's last bullet says that under `structured_output` all three requirements are *"satisfied by construction and closed rather than built — the record rides in the CLI's result envelope, with no path to own and no staleness class."* **The premise is true and the conclusion does not follow, because the fleet's plumbing materialises the envelope in a file before any parent sees it.**

`run-claude.sh:146,149` redirects the CLI's stdout — the stream carrying the `result` event, and with it `structured_output` — into `$LOG_FILE`. So there *is* a path to own. It is owned by the **parent**, not the child, which is what preserves the isolation argument; but "nobody owns a path" is false, and a design written on that sentence would allocate no path deliberately and inherit whatever the log naming happens to give it.

**What the log naming happens to give it, measured rather than assumed.** `assistant_activities.py:278-279` names the log `{model_key}-{%Y%m%d-%H%M%S}.jsonl`. That is **one-second granularity on a key that repeats within a single run** — `build_workflow` invokes `review-pr` twice. Truncation on redirect means a collision destroys the earlier log rather than leaving a stale record behind, so the *dangerous* direction is closed today by luck of a shell operator; the *lossy* direction is open. Neither is a property anyone chose.

**Ruling.** Requirement 3's third clause (anchored outside the worktree) is **closed by construction** and additionally guarded by an existing raise. Its first two clauses (fresh per invocation, run-identity bound) are **built**, because the transport removed the child's write and not the parent's. The two mechanisms cost eleven lines between them.

**The generalisable form, recorded because it will recur in [Phase 4](phase4_fleet_migration.md):** *"the transport has no staleness class"* is a claim about the transport, and the fleet's channel is transport **plus plumbing**. Phase 4 will read this bullet while migrating nine more call sites; each one has its own plumbing, and each one has to be asked the same question rather than inheriting this answer.

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
- [ ] **Rule on the three authored-prose regions that have NO field today**, enumerated by [Phase 2](phase2_kind1_framework.md) — the per-finding **disposition reasoning** (the table's "Reasoning" column), the **one-line verdict rationale**, and the **Post-Run Reflection**. They are not in the `pr_review:` yaml at all, so under arrangement A a render-from-record drops them silently. Either model them as free-text fields or state explicitly that the comment stays independently authored alongside the record. **Either is defensible; silence is the failure** — these three are precisely what makes the durable record carry *the outcome and its reasoning* rather than the outcome alone. See [`memory-model.md` §7.2](../../guide/memory-model.md)
- [ ] Preserve the retrievability convention [Phase 2](phase2_kind1_framework.md) specified, so a later correction pass can address the block rather than page the thread. **Preserve the EMITTER's shape, not the readers' —** Phase 2 measured the block marker declared three incompatible ways (`review-pr.sh:142` and `review_pr_activities.py:51` both match any comment merely *mentioning* the key; only `replay_pr_review_blocks.py:45` is fence-anchored), producing a wrong durable `pass:` on 2 of the 8 archived PRs that carry a block. Preserving the readers as-is would carry that defect into the typed channel
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
