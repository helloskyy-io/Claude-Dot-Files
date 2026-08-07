# Memory Management Framework — Roadmap

**Status: 📋 PLANNED — nothing in this component is built. Five phases, none started.**

*Phases are listed in logical rollout order. Phase numbers are creation-order identifiers and do not reflect rollout sequence; execution order across components lives in [`sprint.md`](../sprint.md).*

---

## What this component is

Two kinds of memory exist because a context window ends and the work does not. They differ in **who reads them**.

- **Kind 1 — durable memory in git, read by humans and AI.** Built and in use, undocumented as a framework: PR threads carry change-outcomes, Issues carry no-change outcomes, the standup tracker carries continuity. *Open* IS the to-do bit. Described as prose in [`operations.md` § The memory model](../../guide/operations.md).
- **Kind 2 — a typed record the child writes at exit, on a channel the parent owns, read by CODE.** Not built. A parent must decide *in code, with no model in the loop*, which child to invoke next.

This component owns: the typed record and its schema; what a parent may route on without a model in the loop; how that relates to the durable human-readable record already in git; and the fail-safe contract when the record is absent or malformed.

**It does not own:** whether to build this (settled — [`sprint.md`](../sprint.md)); the product-level thesis about code-routed control flow (settled — `docs/standards/architecture/research/raw/code_routed_control_flow.md` §6.6, "ordinary as stated"); or the Temporal port ([`temporal-integration/`](../temporal-integration/temporal-integration.md)). Citing those is correct; re-opening them is not.

---

## Why five phases, and why the splits fall where they do

[Documentation Standard §2](../../standards/documentation/documentation_standard.md) sets the test: *each phase should stop at a logical point of functionality (something works end-to-end)*, and *if a phase grows beyond what's manageable, split it*. Applying it to this component's evidence produces five, not four (the sprint's milestone count) and not one:

1. **Measurement is its own phase because its readout can cancel work in the phases after it.** The research is explicit that T1 and T5 are cheap and *either can move the design* — if `is_error` never disagrees with the shell's propagated exit status, the "read the rest of the envelope" milestone is a no-op and must say so; if the prose grep has never missed across the archived logs, the transport upgrade buys nothing measurable at this scale and the justification order changes. A measurement folded in as the first checklist item of a design phase is a gate the same run walks straight past on its way to the design it already intended to write. As a phase boundary it is a ruling with a human in between. This is also §2's *prove manually before automating* applied literally.
2. **Documenting Kind 1 is separable from building Kind 2, and it is a precondition for one part of it.** Kind 1 is built and in use; writing it down is an authoring task with its own done-state. Phase 3's archive-as-by-product step needs to know what Kind 1 exposes, so this lands before it. It depends on nothing in Phase 1.
3. **Design-and-prove-one-pair is depth; migrating the fleet is breadth.** They have different verification: Phase 3 is done when one parent routes on one child's typed record end-to-end with the prose channel still in place; Phase 4 is done when every child emits one and no call site parses prose. Bundled, the design's proof would be indistinguishable from the migration's completeness, and the phase would become a project.
4. **Convergence stopping is gated on typed comparable records existing across two passes** and is the strongest justification for the whole component — but it is a separate capability with a separate failure mode, and it cannot start until Phase 4 has produced records to compare.

---

## Phases

### [Phase 1 — Measure the channel before designing it](phase1_measure_the_channel.md)

Establishes, by experiment against the pinned `claude` CLI and the archived run logs, the facts the design's open parameters turn on: whether `is_error` can disagree with the process exit status, what the exit codes actually are for turn-cap and auth failure (no first-party table exists), whether a turn-cap death can leave a partial typed record, how often the current prose grep has actually missed, and the union of values every existing and planned parent branches on. Produces a measured record inside the phase doc, not a design. Its readout is a gate: two of the five experiments can shrink the work in Phase 3.

- [ ] The exit-code ↔ `is_error` ↔ `subtype` tuple is recorded for each forced failure mode, on the pinned CLI version, in this fleet's child-invocation shape
- [ ] The archived `.claude/logs/` JSONL are replayed through the current `^VERDICT:` predicate and the fall-through count is stated as a number
- [ ] The `(is_error clean/dirty) × (VERDICT MERGE/HOLD)` four-cell table is populated over ≥30 runs, and empty cells are named as empty
- [ ] The union of values every branch point in `build.sh`, `build-minor.sh` and the Python parents reads is enumerated — the envelope's field list is derived from it, not from a guess
- [ ] Each experiment ends in an explicit ruling recorded in the phase doc: *changes the design / confirms the design / no-op*

### [Phase 2 — Document Kind 1 as a framework](phase2_kind1_framework.md)

Turns the memory model from prose that describes behaviour into a stated interface. Names the three surfaces, what outcome class each owns, which is chosen when, and — the part Kind 2 needs — exactly what Kind 1 exposes that a typed record may reference or be rendered into: the `pr_review:` block's fields, what `/standup` parses, and the rule that *open is the to-do bit*. Independent of Phase 1; can run alongside it.

- [ ] Every Kind 1 surface's owned outcome class, lifecycle and readers are stated in one place, with the selection rule ("which surface does this outcome go to") written as a rule rather than implied by examples
- [ ] The `pr_review:` block's field set is documented as the interface it already is, sourced from the emitting script rather than re-typed from memory
- [ ] What `/standup` reads from each surface is enumerated, so a later change to the block can be checked against a consumer list
- [ ] The framework doc is placed in the guide bucket (user-facing operating manual), and the standards-amendment candidate it surfaces is listed here rather than written

### [Phase 3 — The typed exit record: schema, fail-safe contract, one pair proven](phase3_typed_exit_record.md)

Adopts arrangement A — the child writes a small typed record at exit to a channel the parent owns, and the human record is rendered from it — and proves it on exactly one parent/child pair with the prose VERDICT line still in place as the incumbent. Specifies the envelope (tiny and versioned), the split abstention vocabulary (a computed *could-not-check* arm and an asserted *needs-a-ruling* arm), the composition rule when `is_error` and the model's verdict disagree, and the fail-safe contract borrowed wholesale from Kubernetes `podFailurePolicy`: ordered rules, first match wins, documented default, and a residual arm that is a **named recorded state**, never a silent fall-through.

- [ ] The envelope schema is written down as its own contract, with the explicit statement that every field the parent does not read is not load-bearing
- [ ] The abstention member is split in two, each arm with its own emitter, its own reliability claim, and its own remedy
- [ ] The fail-safe contract is stated as ordered rules with a documented default, and absence or unparseability routes to the arm requiring a human — verified by a test that deletes the record and asserts the route
- [ ] `review-pr` emits the record and one parent routes on it, with the prose channel still present and both paths asserted to agree over a run set
- [ ] The disagreement policy is ruled on and the ruling records both values under distinct names; if Phase 1 found the off-diagonal cells empty, the composition machinery is not built and the doc says why

### [Phase 4 — Migrate the fleet, and archive the record as a by-product](phase4_fleet_migration.md)

Rolls the proven record out across every child and retires prose parsing as a routing input. Ten workflows currently declare a PR-URL `COMPLETION_PATTERN` and their callers extract that URL by regex; the Python tree already declares the routing vocabulary in exactly one module, which makes the change far smaller than the call-site count suggests. **No prompt content changes** — what a child is told to do is unaffected by what it returns, and the 428 KB of workflow scripts is overwhelmingly prompt text this phase does not touch. Also lands the envelope observables the sprint milestone named, on the composition rule Phase 3 established, and makes the durable `pr_review:` block a copy of the exit-channel record rather than an independently composed second write.

- [ ] Every child emits the typed record; no parent branches on a value parsed out of prose
- [ ] The record's schema is declared in exactly one place per language tree, and a test asserts no second declaration exists
- [ ] `is_error`, `permission_denials[]` and `num_turns`-against-cap are read and routed per the Phase 3 composition rule — or the phase records that Phase 1 proved them redundant and closes the milestone as a no-op with the evidence attached
- [ ] The `pr_review:` block on the PR is produced from the typed record, and either the disposition table is rendered from it or a write-time invariant reconciles the two before the comment posts
- [ ] `/standup` and `review-pr` are verified against the migrated block — Kind 1's readers see no change

### [Phase 5 — Convergence-based stopping](phase5_convergence_stopping.md)

The capability the typed record exists for, and the justification that has no working incumbent to beat: *"did this pass find anything not in the previous pass's result?"* is answerable against two typed payloads and is not answerable against two prose logs. Implements finding-set comparison across passes, with the documented guards against a naive "stop when nothing new" rule — an oscillating finding set, an adaptively biased reviewer, and a degraded pass that emits nothing are all indistinguishable from convergence unless the rule is written to tell them apart.

- [ ] Findings carry stable identity across passes, so "the same finding" is a computed fact and not a string comparison on prose
- [ ] The stopping predicate is a total function whose residual arm is a named recorded state, consistent with the Phase 3 contract
- [ ] Each documented false-convergence mode is named in the doc with the specific check that separates it from real convergence, and each check has a test
- [ ] The rule is measured against archived multi-pass runs before it gates anything live, and the existing loop-back bound stays in force until the measurement supports replacing it

---

## Dependencies

**This component depends on:**

- Nothing built. Phase 1 depends only on the pinned CLI and the archived logs.
- **Evidence:** [`research/synthesis.md`](research/synthesis.md) and its two pool papers, plus three upstream product-pool papers cited but never re-derived (`code_routed_control_flow.md`, `convergence_stopping.md`, `claude_code_integration_surface.md`).

**Depends on this component:**

- **[Temporal Integration](../temporal-integration/temporal-integration.md)** — [`sprint.md`](../sprint.md) gates it on this component explicitly: Temporal buys durability and resumability, not composition, and porting before the handoff shape settles means porting a shape still being changed. Phase 4 is the point at which that shape stops moving.
- **[Autonomous Operation](../autonomous-operation/autonomous-operation.md)** — its "driver that dispatches from persisted state" is named in `sprint.md` as *the payoff of the Memory Management Framework*, and its "observable exit criteria" milestone consumes Phase 5's convergence signal.
- **[Fleet Reliability](../fleet-reliability/)** — owns the three-legged liveness predicate (stalled / looping / stranded). It needs a definite-progress signal that nothing in the fleet currently emits; see Key Decisions below for why that work sits there and not here.

**Currency watch.** `claude_code_integration_surface.md` carries `Last validated: 2026-07-25 · Revalidate: high — 4 weeks` and comes due **2026-08-22**. Phases 1, 3 and 4 all cite it. It is a product-pool paper — a component run may not refresh it, and this line is the handoff.

---

## Key Decisions

Per [Documentation Standard § Architectural Decisions — No ADRs](../../standards/documentation/documentation_standard.md), decisions scoped to this component's design are recorded here. Each rests on verified evidence and names it. None of these is a research finding promoted to a rule by this document — they are design rulings this component is making, with the evidence they rest on.

**Adopt arrangement A — one author, two copies, two lifetimes.** The child writes the typed record once at exit to a channel the parent owns; the human record is rendered from it; the durable copy on the PR is a by-product of that rendering rather than a second authoring act. *Why:* the hardest-looking constraint — durable human record, machine value needed seconds after exit — is a **storage** mismatch, not a content mismatch, and dissolves under A. *Rests on:* `dual_channel_outcome_records.md` §5, R1, R5 — derived, with its falsifiers in that paper's test plan. *Alternative rejected:* the current arrangement B (parse a typed value out of a human-authored artifact) is, across 26 sources, never shipped without a write-time gate, and is never used to route a *process outcome* — where an outcome routes a subsequent process, the arrangement is A or D, every time.

**Two viable transports; prefer the file if the schema surface proves unavailable.** Either a JSON file at a caller-declared path, or `--output-format json --json-schema` with the parent reading `structured_output`. *Why:* the file variant carries the same properties with no dependency on a high-volatility CLI feature. Phase 1's T1 decides. *Rests on:* `claude_code_integration_surface.md` §1; verified present in `--help` on CLI 2.1.224 (see Phase 1's `§Runtime Verification`).

**Split the abstention member in two.** A computed *could-not-check* arm and an asserted *needs-a-ruling* arm. *Why:* every mature observable vocabulary surveyed has an abstention member — Kubernetes probes' `Unknown`, Argo's `Error` distinct from `Failed`, Monitoring Plugins' `Unknown`=3, pytest's exit 5 — and **all of them mean "the checker could not evaluate," never "the work is ambiguous."** `HOLD - needs-assistance` means the second. They have different reliability and different remedies, so one member doing both jobs is one member measuring nothing. *Rests on:* `non_model_observables.md` §5.5, §0 finding 3, P5. **This is the concrete change the sprint item does not contain.**

**Borrow the fail-safe contract; do not design one.** Kubernetes `podFailurePolicy` — ordered rules, first match wins, documented default — is the evaluation semantics; the residual arm is a **named state that gets recorded**, not a silent default. *Why:* routing on values the model did not author is mature and boring outside the agent corpus, and three first-party vocabularies converge on the same two members (GitLab `on_success`/`on_failure`, Airflow `all_success`/`one_failed`, GitHub Actions `success()`/`failure()`). Treating this as a design novelty is the error. *Rests on:* `non_model_observables.md` §2.1–2.2, §3.2, synthesis §5.

**When an asserted verdict and a computed observable disagree, record both under distinct names.** GitHub Actions' `outcome`/`conclusion` split is the shape — the raw observation is never overwritten, the policy-adjusted value is what routing sees by default. *Why:* no surveyed system documents precedence between an asserted and a computed result, because none has an asserting producer. There is no prior art to borrow, so the fleet picks, and picking "keep both" costs nothing and preserves the ability to change the ruling later. *Rests on:* `non_model_observables.md` §3.3, N1. **Constrained by Phase 1:** if the off-diagonal cells never occur, adopt the two-name shape and build no composition machinery.

**Justify the design by the stationary error rate, not by producer exceptionalism.** *Why:* CI has the well-formed-plausible-wrong-result problem too, and it is measured — 170 reruns for 95% confidence a pass is not flaky; 31.08% of SWE-Bench+'s *passed* patches suspicious on manual screening; `continue-on-error` shipped as a keyword that makes a green build over a failed step deliberate. What genuinely differs is that a CI step's malformedness is **a defect with a fix** whereas an LLM's is **a stationary rate with a distribution** — which changes the *fail-safe contract* (it must be total and must assume the bad case recurs), not the taxonomy. *Rests on:* `non_model_observables.md` §0 finding 2, P13. *Consequence:* "our producer is special" is a claim a CI-literate reviewer will break, and it appears in a standard today — see Standards-amendment candidates.

**Lead with the measurement argument, not the routing argument.** Convergence detection *requires* typed comparable finding records and has no working incumbent to beat. The routing argument does have one: `build.sh`'s prose grep is fail-closed, its vocabulary is three closed tokens, `review-pr` fails loud on absence, and **no evidence in the pool shows that arrangement producing a wrong route.** *Why:* a doc claiming the current arrangement is broken is overclaiming, and Phase 1's T5 exists to find out whether it can be claimed at all. *Rests on:* `convergence_stopping.md` P11; `dual_channel_outcome_records.md` §7.0.1–7.0.2.

**Do not put the machine channel in git notes or commit trailers.** That family is arrangement-B metadata *about* a durable artifact and is never used to route a process outcome; notes additionally carry an unresolved transfer-semantics question. *Rests on:* `dual_channel_outcome_records.md` R7, N4. **The negative is the finding** — recorded so it is not re-proposed.

**Do not cite SARIF or Conventional Commits as precedent for arrangement A.** SARIF's `level` and `message` are sibling fields on one `result` object — arrangement C, not A; what looks like A is GitHub's *consumer* side, and the transferable lesson is the subset contract and the 10 MB cap. Conventional Commits presupposes a mutable pre-merge artifact (its documented remedy for a wrong value is an interactive rebase); a posted PR comment is not rebaseable. Both are good evidence for a *failure mode* and bad evidence for an adoption. *Rests on:* `dual_channel_outcome_records.md` §7.0.6–7.0.7.

**Do not cite the GitHub Actions 1 MB / 50 MB output caps anywhere in this component.** They were not found in the fetched primary and are unverified wherever they are met. The one corroborated cap figure in this evidence base is Tekton's 4096 bytes. *Rests on:* `code_routed_control_flow.md` N4.

**The stall/liveness axis belongs to Fleet Reliability, not here.** "Did it stall?" is answerable in principle from runtime observables, but its precondition — a definite-progress signal — is unmet, and [`sprint.md`](../sprint.md) already places *the three-legged liveness predicate (stalled / looping / stranded)* in Fleet Reliability. *Why here at all:* the research surfaced it as an open scope call naming this component as a possible destination, and leaving a raised scope question unruled is how it gets built twice. **What this component owes it:** Phase 1's T4-adjacent question — whether a definite-progress predicate is derivable from the `stream-json` event stream — is recorded as a finding for Fleet Reliability to consume, not built here. *Rests on:* `non_model_observables.md` P8, P9, §5.1; sprint scope. **This ruling has a sprint implication and is surfaced for the operator, not written into the sprint file.**

**Which channel owns the to-do bit is ruled in Phase 3, informed by Phase 1.** Kind 1 uses open/closed as the to-do bit — that is its defining property. A typed record carrying a `verdict` is a second state machine over the same work, and the corpus's only answer (Kubernetes: a condition is current state, an Event is history) is *neither closes the loop*. Nothing upstream decides this. Phase 1's T3 counts the actual disagreements between `pr_review:` verdicts and their PRs' open/closed state; Phase 3 rules with that number in hand. *Rests on:* `dual_channel_outcome_records.md` §5 sub-problem 3, T3 — flagged in the synthesis as a **decision with no owner**, which this line gives one.

---

## Standards-amendment candidates

Surfaced, never written — standards are human-ratified ([`standards-governance`](../../../config/rules/standards-governance.md)). This section exists partly to resolve a routing gap the evidence named: the Research Standard's consumption table sends a standards-amendment candidate to *"the consuming component's roadmap 'Standards-amendment candidates' section (create it if absent)"*, and until this roadmap existed the candidate had nowhere to go.

1. **`docs/standards/workflow-scripts.md § Composition` codifies the VERDICT-over-stdout contract** — *"A parent needs exactly two things from a child — a reliable exit code, and one stable identifier on its final line."* The comparative evidence identifies that as the one arrangement the corpus never ships without a write-time gate, and never uses to route a process outcome. Not urgent and **not a defect claim** — the incumbent has no demonstrated failure — but the standard states a mechanism this component's Phase 3 replaces. The amendment should land after Phase 3 proves the replacement, not before.
2. **`docs/standards/workflow-scripts.md § Routing contracts` asserts the premise the evidence corrects.** It reads: *"our producer is an LLM that can emit a plausible-looking but wrong result — an assumption general-purpose orchestrators do not have to defend against."* The second clause is false as stated — CI's producers emit well-formed wrong results too, and it is measured. The rule the sentence supports (fail safe, never guess) is **strengthened**, not weakened, by the correction: the reason to be total is that the error rate is stationary, not that the producer is unique. A one-sentence rewording, no rule change.
3. **The Research Standard's §7 consumption table assumes a roadmap exists for every consuming component.** Resolved here by this component having one, but the table has no row for a component whose planning artifact is a single file — which is every other component in this repo today. Surfaced as a corpus-level observation for the standards owner, not a change this component needs.

---

## Where the research contradicted the sprint milestones

The sprint milestones were written before the research existed. Where they differ, the research wins; the reasoning lives in the pool, not in the sprint file.

| Sprint milestone says | The verified evidence says |
|---|---|
| *"`subtype` and `.result` are read today; `is_error`, `permission_denials[]` and `num_turns`-against-cap are not"* | **Correct, and the earlier framing that the parent gated on nothing was verified false.** `build.sh:60` is `set -euo pipefail` and children run under `if ! … \| tee`, so the child's non-zero status is not masked — coarse class-(i) routing already works. `run-claude.sh:167` greps `"subtype":"error_max_turns"` and `:201-204` `jq`-reads `.result`. **The sharper gap the milestone does not state:** there is no first-party exit-code table for `claude`, so class-(i) routing rests on an undocumented mapping, and whether a child can exit 0 with `is_error: true` is unknown. Phase 1 answers it |
| *"Design it … with a total fail-safe default"* | Right, and under-specified in one respect that changes the build: the abstention member must **split in two**. The sprint item has one; every mature vocabulary has the computed arm only; `HOLD - needs-assistance` is the asserted arm. Phase 3 builds two |
| Implicitly, that routing on non-model values is the novel part | It is **mature and boring outside the agent corpus** — three first-party vocabularies converge on the same two members, and Kubernetes ships a ready-made ordered-rules fail-safe contract. Borrow the shape; do not design one |
| Implicitly, that the LLM producer is what makes this hard | **Half right.** CI has the same problem, measured. What differs is defect-with-a-fix versus stationary-rate-with-a-distribution, and that changes the fail-safe contract rather than the taxonomy |
| Four milestones | **Five phases.** The measurement work the design depends on is not a milestone in the sprint item at all, and two of its five experiments can shrink the phases after it |

**One structural contradiction, recorded rather than silently resolved.** The synthesis's *Homeless findings* argues this component *"has no roadmap and correctly should not have one,"* citing a convention that a component fitting in one phase gets `<name>/<name>.md`. [Documentation Standard §0](../../standards/documentation/documentation_standard.md) is binding and names no such form: a component gets *"its own folder with a `roadmap.md` + `phase{N}_{name}.md` docs. The full structure."* The standard wins, and the work does not fit in one phase in any case. Every other component in `docs/development/` currently uses the single-file shape; **this component is the first to take the §0 structure, so it is the exemplar and there was no local one to match.**
