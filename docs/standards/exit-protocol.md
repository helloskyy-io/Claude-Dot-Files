# Exit Protocol

> ## ⚠ STATUS: DRAFT — NOT BINDING. Do not conform to this document yet.
>
> This is a **scaffold**, authored 2026-08-08 before the thing it describes exists. It states the **shape** the protocol must have; almost every **value** in it is an open question owned by a numbered phase, marked `⟨PHASE N⟩` inline.
>
> **An engineer building a Memory Management Framework phase should read this for orientation and write the answers into it — not treat it as a contract to satisfy.** A section still carrying `⟨PHASE N⟩` markers is a section whose answer has not been measured.
>
> **What makes it binding:** all five phases complete, the protocol proven across the fleet rather than on one pair, and an explicit operator ratification recorded here with its date. Not before. A protocol ratified on one proven pair is a guess with a version number.

---

## What this governs

**How one unit of work hands off to the next, when the thing deciding what runs next is code and not a model.**

A child finishes. Something must decide — *in code, with no model in the loop* — what happens now: merge, retry, escalate to a human, stop. Today that decision is made by parsing a token out of prose a model wrote. This protocol replaces the parsing with a typed record the child emits deliberately.

**It governs:** the record's envelope, the vocabulary of outcomes it may carry, the fail-safe contract when the record is absent or malformed, how the record relates to the durable human-readable record, versioning, and conformance.

**It does not govern:** what a child *does*, how it is dispatched, isolation, or scheduling. Those are `workflow-scripts.md` and the Temporal standards. **This protocol is about the seam, not the units on either side of it.**

## Why this is a protocol and not an implementation detail

Because the value is compositional and arrives only when it is uniform.

Once every child emits the same envelope, a parent can route *any* child to *any* child without bespoke parsing — the connector does not need to know what the unit does. That is the property that makes a graph of units assemblable rather than hand-wired, and it is the same property that makes CI job vocabularies (`on_success`/`on_failure`, `all_success`/`one_failed`, `success()`/`failure()`) work: **the runtime routes on a value it did not have to understand.**

**Routing on values the producer did not author is mature and boring outside the agent corpus.** Treating it as a design novelty is the error this protocol exists to avoid. Where a shape exists — Kubernetes `podFailurePolicy` for fail-safe evaluation, the GitHub Actions `outcome`/`conclusion` split for asserted-vs-computed disagreement — **borrow it and cite it. Do not design one.**

---

## 1 · Two kinds of memory, and why both are in scope

They differ by **who reads them**, and a handoff carries a reference to both.

**Kind 1 — the durable record.** Human- and AI-readable, carries the outcome *and its reasoning*, has a **to-do bit**, is retrievable by a later run without replaying everything, and survives context death.

**Kind 2 — the typed record.** Machine-readable, emitted at exit on a channel the parent owns, read by code within seconds of exit. Small, versioned, total.

### Kind 1 is an INTERFACE, not GitHub — this is binding on the shape even in draft

In this repo Kind 1 is currently implemented as PR threads, Issues, and the standup tracker, with *open* as the to-do bit. **Every one of those is a GitHub fact, not a property of the interface**, and a component whose work product is not code in git — an edge device, a robot, a datacenter node — has no PR to comment on and no issue to close.

So the five properties above are the contract. GitHub is **one binding of it**. Any document describing Kind 1 must state which parts are substrate-specific and which are the interface. ⟨PHASE 2⟩ enumerates this.

**Consequence for the envelope:** a Kind 2 record carries a **substrate-agnostic reference** to its Kind 1 record. Today that resolves to a PR URL; on another substrate it resolves to something else. The field is not optional and its form is ⟨PHASE 3⟩.

---

## 2 · The envelope

**Small, versioned, and every field has a named consumer.** A field no consumer reads is not load-bearing and does not belong here — say so explicitly rather than leaving it ambiguous.

| Requirement | Status |
|---|---|
| Field list | ⟨PHASE 3⟩ writes the contract, **derived from Phase 1 E6's completed enumeration — nine fields, not the roadmap's estimated "roughly five"**, and `plan-revision`'s issue-URL completion is a second caller the estimate omitted. The enumeration is done; the per-field contract is not |
| Per-field: named consumer, publish classification (publishable / internal) | ⟨PHASE 3⟩ |
| Reference to the Kind 1 record (§1) | ⟨PHASE 3⟩ |
| Transport | **MEASURED — `--output-format json --json-schema`, the parent reading `structured_output`.** Phase 1 E1(g), 2026-08-08, on CLI 2.1.224 — *confirms* the roadmap's preference, judged on isolation and Temporal replay cost rather than availability alone. The file variant would ask a child under `--dangerously-skip-permissions` to write outside its worktree, which is the isolation boundary the fleet's safety argument rests on. **One constraint the measurement added and nobody predicted: the schema is an inline shell argument**, so its size and quoting are a build-time concern for every caller. See [`phase1_measure_the_channel.md`](../development/memory-management-framework/phase1_measure_the_channel.md) § E1 |
| Size bound | ⟨PHASE 3⟩. The one corroborated figure in the evidence base is Tekton's 4096 bytes. **Do not cite the GitHub Actions 1 MB / 50 MB caps** — unverified in the fetched primary |

**No field is added on behalf of a consumer that does not exist.** A known-future consumer is served by the extension rule in §5, not by a field reserved today. Every protocol that stayed composable did this; the ones that anticipated their consumers bloated and forked.

## 3 · The outcome vocabulary

**Closed.** A value outside the vocabulary is a malformed record and routes per §4.

**Abstention splits in two.** Every mature observable vocabulary surveyed has an abstention member — Kubernetes probes' `Unknown`, Argo's `Error` distinct from `Failed`, Monitoring Plugins' `Unknown`=3, pytest's exit 5 — and **all of them mean "the checker could not evaluate," never "the work is ambiguous."** Those are different conditions with different reliability and different remedies:

- a **computed** *could-not-check* arm — the evaluation did not complete
- an **asserted** *needs-a-ruling* arm — the evaluation completed and the answer is that a human must decide

One member doing both jobs measures neither. Members, names and their emitters: ⟨PHASE 3⟩.

**When an asserted verdict and a computed observable disagree, record both under distinct names.** The GitHub Actions `outcome`/`conclusion` split is the shape: the raw observation is never overwritten; the policy-adjusted value is what routing sees by default. Precedence: ⟨PHASE 3⟩. **The conditional is now resolved — Phase 1 E3(a), 2026-08-08: the off-diagonal cells are empty *by construction*, not merely unobserved.** So the two-name shape is adopted and **no composition machinery is built** — and note the reason is structural rather than a small-N argument, which means it does not weaken as the corpus grows.

## 4 · The fail-safe contract

**Total. It must have an answer for every input, including inputs nobody anticipated.**

Shape borrowed from Kubernetes `podFailurePolicy`: **ordered rules, first match wins, documented default.** The residual arm is a **named state that gets recorded** — never a silent fall-through.

Four conditions must each route explicitly, and each needs its own test: **absence · unparseability · staleness · unknown `schema_version`**. ⟨PHASE 3⟩ writes the ordering.

**Why total rather than best-effort:** the producer's malformedness is a **stationary rate with a distribution**, not a defect with a fix. That is the real difference from a CI step — *not* that the producer is uniquely unreliable. CI producers emit well-formed wrong results too, and it is measured. **"Our producer is special" is a claim a CI-literate reviewer will break;** the reason to be total is that the bad case recurs.

**`permission_denials[]` is safety observability, not a routing option.** Recorded and surfaced every run regardless of any routing ruling, and a non-empty list routes to the human arm and **never** to automatic redispatch. Auto-retrying a child that just tripped the only in-run safety control is an unbounded loop against that control.

## 5 · Versioning and extension

- Every record carries `schema_version`. An unknown value routes per §4 — it is never ignored and never guessed at.
- **Extensions are additive.** A new consumer gets a new optional field; it does not get a reserved field today or a breaking change tomorrow.
- A field is removed only after no consumer reads it, demonstrated rather than asserted.

Exact mechanism and compatibility window: ⟨PHASE 3⟩.

## 6 · Conformance

- **One declaration.** The schema is declared once and loaded, never re-typed per consumer. A duplicated vocabulary passes every test in both copies while diverging — that is how `parse_verdict` came to be typed twice, and the copy that decided merges had zero tests.
- Every child emits a conforming record; every parent routes only on the record. ⟨PHASE 4⟩.
- A guard ships with a demonstration that it fails when the property is violated — **mutation evidence, per the Testing Standard.**
- Prompt-borne emission is part of the conformance surface: the verdict and findings are model-authored, so the *instruction* to emit is in prompt text, and a check must verify the emit instruction still corresponds to the field the parent reads.

---

## 7 · What this deliberately does not cover

Stated as decisions so they read as scope rather than as gaps.

**The V1 bash fleet is FROZEN, not migrated and not retired.** It stays as the working fallback precisely because V2 is not fully designed or proven; we invest nothing in upgrading it. So *"no parent branches on prose"* is **false for the bash fleet on purpose**, and any conformance claim is scoped to the V2 tree.

> **Exit condition, stated so "frozen fallback" does not quietly become "permanent second fleet":** the bash fleet stops being the fallback when V2 has demonstrated reliability across the paths it covers. Ruling owner: operator, jointly with [Temporal Integration](../development/temporal-integration/temporal-integration.md).

**Liveness and stall detection are out of scope** — *"did it stall?"* is Fleet Reliability's three-legged predicate, not an exit-time observable. This protocol describes a unit that **finished**.

**Git notes and commit trailers are excluded as a transport.** That family is metadata *about* a durable artifact, is never used to route a process outcome, and carries unresolved transfer semantics. **The negative is recorded so it is not re-proposed.**

**SARIF and Conventional Commits are not precedent here.** SARIF's `level`/`message` are sibling fields on one object — a different arrangement; what resembles this is GitHub's *consumer* side, and the transferable lesson is the subset contract, not the shape. Conventional Commits presupposes a rebaseable pre-merge artifact; a posted PR comment is not rebaseable.

---

## Provenance

Derived from `docs/development/memory-management-framework/roadmap.md` § Key Decisions and its research pool (`research/synthesis.md` plus `non_model_observables.md` and `dual_channel_outcome_records.md`, both critic-verified). **That roadmap is the authority until this document is ratified** — where the two disagree today, the roadmap wins.

**Related standards:** [`workflow-scripts.md`](workflow-scripts.md) § Composition states the incumbent VERDICT-over-stdout contract this protocol is designed to replace; that section is amended **after** the replacement is proven, not before.

## Ratification

*Unratified. When all five phases are complete and the protocol has been exercised across the fleet, the operator records the ratification date and commit here, and this banner and every `⟨PHASE N⟩` marker is removed in the same change.*
