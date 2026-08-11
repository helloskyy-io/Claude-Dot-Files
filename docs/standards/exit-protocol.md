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

So the five properties above are the contract. GitHub is **one binding of it**. Any document describing Kind 1 must state which parts are substrate-specific and which are the interface. **That enumeration exists: [`memory-model.md` §9](../guide/memory-model.md) states it as a single inherit-versus-re-implement table, and this protocol cites it rather than restating it** — per [Documentation Standard § Single-source codified fields](documentation/documentation_standard.md), a second copy of that table would drift from the one that gets maintained. *(Roadmap candidate 7, applied.)*

**Consequence for the envelope:** a Kind 2 record carries a **substrate-agnostic reference** to its Kind 1 record. Today that resolves to a PR URL; on another substrate it resolves to something else. The field is not optional, and its form is `completion_ref` in §2 — **four parts, of which exactly one names the substrate and none is typed as a URL.** A component whose work product is not code in git has no PR to point at, and this fleet is going there.

---

## 2 · The envelope

**Small, versioned, and every field has a named consumer.** A field no consumer reads is not load-bearing and does not belong here — say so explicitly rather than leaving it ambiguous.

| Requirement | Status |
|---|---|
| Field list | **WRITTEN — §2.1 and §2.2 below**, derived from Phase 1 E6's enumeration. Phase 3 added two child-authored fields and re-typed a third; each addition names the requirement that forced it, in §2.1's *Required by* column |
| Per-field: named consumer, publish classification (publishable / internal) | **WRITTEN — the two rightmost columns of §2.1 and §2.2** |
| Reference to the Kind 1 record (§1) | **WRITTEN — `completion_ref`, §2.1.** Substrate-discriminated, never typed as a URL |
| Transport | **MEASURED — `--output-format json --json-schema`, the parent reading `structured_output`.** Phase 1 E1(g), 2026-08-08, on CLI 2.1.224 — *confirms* the roadmap's preference, judged on isolation and Temporal replay cost rather than availability alone. The file variant would ask a child under `--dangerously-skip-permissions` to write outside its worktree, which is the isolation boundary the fleet's safety argument rests on. **One constraint the measurement added and nobody predicted: the schema is an inline shell argument**, so its size and quoting are a build-time concern for every caller. See [`phase1_measure_the_channel.md`](../development/memory-management-framework/phase1_measure_the_channel.md) § E1. **Phase 3 measured one thing more, and it changes what a caller must do — §2.4.** |
| Size bound | **WRITTEN — §2.5.** The one corroborated figure in the evidence base is Tekton's 4096 bytes. **Do not cite the GitHub Actions 1 MB / 50 MB caps** — unverified in the fetched primary |

**No field is added on behalf of a consumer that does not exist.** A known-future consumer is served by the extension rule in §5, not by a field reserved today. Every protocol that stayed composable did this; the ones that anticipated their consumers bloated and forked.

**The record has three strata, and the split is a fact about who can physically produce each value — not a taxonomy.** The child authors what only the child knows; the runtime produces what the child cannot see; the parent computes what neither is entitled to decide. §2.1, §2.2 and §2.3 are those three, in that order, and step 2 of Phase 3 rules on why.

### 2.1 · Child-authored — arrives in `structured_output`

The model calls the `StructuredOutput` tool; these are its parameters. **Every one must be a field the child can ALWAYS fill** — Phase 1 E2(c) measured that a schema the model cannot satisfy produces *silence on a clean run*, not an error, so an over-constrained required field is a self-inflicted absence.

| Field | Type | Required by | Publish |
|---|---|---|---|
| `schema_version` | string; `"1"` today | The parent's version-skew rule (§5) — a child in a worktree on an older revision writes to a parent on `main`, so skew is the normal case here | publishable |
| `run_id` | string; opaque nonce the parent generated and put in the prompt | **The parent's run-identity check** — [Phase 3 § step 3](../development/memory-management-framework/phase3_typed_exit_record.md). Binds *this* record to *this* invocation, independently of the path it arrived on. **[Phase 4](../development/memory-management-framework/phase4_fleet_migration.md) gave it a second consumer: which durable block is this pass's.** That inference was positional — ordering plus a posted-count delta — so a third party posting a fenced `pr_review:` example between the child's comment and the parent's read made the parent compare this pass's record against a stranger's findings | **publishable — CHANGED by Phase 4, see below** |

> **`run_id` moved from `internal` to `publishable`, and Phase 3's *"the two copies differ in exactly one field"* is therefore superseded.** The nonce now appears in the durable `pr_review:` block, because the block's address is otherwise positional and a position is not an identity. What it costs: the routing copy and the published copy are now identical, so the sentence that described the filter as one field wide no longer has a field to describe. What it buys: the render↔record invariant and the convergence history select the same block by the same nonce, and a stranger's block cannot be mistaken for this pass's. **It is an opaque `uuid4` hex with no meaning outside the run**, which is why the reclassification is cheap — it names a run log, not a secret.
| `outcome` | enum `merge` \| `hold` | **B6, B7, P3, P5** | publishable |
| `hold_kind` | enum `redispatch` \| `needs_ruling`; required iff `outcome == hold` | **B6, P3, P5** — every parent branches on the sub-kind, so `hold` alone does not route | publishable |
| `completion_ref.substrate` | enum; `github` today, extended additively per §5 | The resolver that turns the ref into an address. **This is the field that makes the reference substrate-agnostic**; without it a reader must infer the binding from the shape of a string | publishable |
| `completion_ref.kind` | enum, **scoped to the substrate**; `pull` \| `issue` on `github` | **P6** — the sole reason `plan_revision_workflow.py`'s `rfind` tie-break exists. This field deletes that code | publishable |
| `completion_ref.id` | string; opaque within the substrate | **B3, P4** — both fleets recover it today by string surgery on a URL | publishable |
| `completion_ref.uri` | string; a **substrate-defined resolvable address**, not a URL by contract | **B1, B2, P4**, and the human-facing banners at `build.sh:210,292` | publishable |
| `findings[].id` | string slug | **Phase 5** identity, and Phase 3 step 8's render↔record invariant | publishable |
| `findings[].disposition` | enum `hold` \| `fixed` \| `deferred` \| `rejected` \| `noted` \| `escalated` | **Phase 5**'s stopping predicate — the field that partitions a block's findings into open and closed. Present on **300 of 300** archived findings (re-counted 2026-08-09 at 41 PRs; it was 195 of 195 at 38). Phase 5 rules the partition: CLOSED is `fixed`/`deferred`/`rejected`/`noted`/`escalated`, OPEN is `hold` plus anything unrecognised | publishable |

### 2.2 · Runtime-produced — the parent reads them off the CLI result envelope

**The child cannot author these and must not be asked to.** They are facts about the process, observed by the thing that ran it.

| Field | Type | Required by | Publish |
|---|---|---|---|
| `permission_denials.count` | integer | **Phase 1 E1(f)** — an operator reviewing whether a dispatch tried something the hook stopped. The denial run exited **0** with `is_error: false` and `subtype: success`, so nothing else can answer it | publishable |
| `permission_denials.entries[].tool_name` | string | Same consumer: *which* control fired | publishable |
| `permission_denials.entries[].tool_use_id` | string | Same consumer: *which call* fired it — the key that locates the denied invocation in the run log | publishable |
| `permission_denials.entries[].tool_input` | — | **NOT CARRIED.** Dropped at read time and never stored in either copy | **internal — never published, never routed** |

> **`matched_rule` was declared here and is withdrawn, because it does not exist on the envelope.** This row read *"`matched_rule` | string | Same consumer: **why** it fired"* and the reader filled it with `.get("matched_rule", "")` — so the one question §2.2 says this stratum exists to answer was **empty on every real run**, silently, because the default hid the absence. The single observed denial entry (Phase 1, *"`permission_denials[]` non-empty, observed once (1 of 9 runs, forced)"*) is `{tool_name, tool_use_id, tool_input}`; the CLI emits no `matched_rule` at all. **The field list was written from the design table and the reader was written from the field list, so nothing in the chain ever compared either against the measurement.** `tool_use_id` replaces it because it is measured present and answers a question an operator actually has after a trip. Re-open this if the CLI ever publishes a rule identifier.

### 2.3 · Parent-computed — the fail-safe contract's own output

Authored by neither the child nor the runtime. §4 produces these; nothing else may write them.

| Field | Type | Required by | Publish |
|---|---|---|---|
| `routed_outcome` | enum `merge` \| `hold` \| `undetermined` | **The parent's branch.** The policy-adjusted value, in the `outcome`/`conclusion` shape of §3 — the child's `outcome` above is the raw observation and is never overwritten | publishable |
| `undetermined_reason` | enum; required iff `routed_outcome == undetermined` | The residual arm's **named recorded state** (§4), and the operator reading why a run reached a human | publishable |

### 2.4 · What Phase 3 measured that changes a caller's obligations

Re-verified on **CLI 2.1.224, 2026-08-09, host `puma-workstation-mint`** — the same version Phase 1 pinned, so this is an addition to E1(g) rather than a re-take of it.

- **`--json-schema` composes with `--output-format stream-json`.** Phase 1 measured it against `--output-format json`; the fleet runs `stream-json`, and the `result` event carries a validating `structured_output` under both.
- **Declaring a schema REPLACES `.result` with the serialised structured output.** On a run that emitted prose *and* called the tool, `.result` was `{"outcome":"merge",…}` and the model's terminal `VERDICT:` line was **not in it**. `run-claude.sh`'s *Completion contract* block reads `.result`, so **a caller that adds `--json-schema` without moving that read silently deletes the fleet's only write-time gate.** The prose itself survives, in the stream's `assistant` text blocks — which is where a schema-declaring caller must read both the completion signal and any prose shadow. **Read the LAST such block, not their concatenation:** the gate exists to catch a run that *ended* early, and `.result` supplied that finality for free by being the final message; grepping every block would change the predicate to "the run ever mentioned the signal" and readmit the failure the gate is for. *(Cited by section rather than by line: this claim's referent has moved once already, and a line range in a standard goes stale on the next edit to the file it names.)*
- **The result envelope carries `session_id` and `uuid`**, so a runtime-produced process identity exists alongside the child-authored `run_id`. `run_id` is the one that binds a record to *the invocation the parent dispatched*; `session_id` only identifies the CLI process that wrote it.

### 2.5 · Size posture

**Carry references, not payloads.** The envelope's fixed part — everything in §2.1 except `findings[]` — is bounded at **4096 bytes**, the one corroborated cap figure in this evidence base (Tekton). `findings[]` grows with the review and is exempt, because it carries two short fields per finding and no prose.

**And the schema is subject to a second, separate bound that the payload is not.** It is passed to the CLI as an argument value, so its size is a *build-time* cost for every caller, not a runtime one. It is bounded at **4096 bytes compact** and is asserted at that bound by a test, because an over-large schema fails at the process boundary where the error names neither the schema nor the field that grew it.

## 3 · The outcome vocabulary

### `INTERFACE` — the vocabulary is CLOSED for a finding about the work in hand

**Three members, and the rest are unreachable:** `fixed`, `rejected`, `hold`. A finding about an artifact the run created or edited, a commit made to unblock it, or output it produced that violates a rule binding it, **is never routed to another queue.** `deferred`, `noted` and `escalated` exist only for findings about work this change did not touch.

**Every finding names the artifact it is about**, so ownership is computed from the change's own diff rather than judged. That field is the enforcement point: **a finding whose artifact is in this diff, carrying a disposition outside the three, is a malformed record.**

**Why closed rather than guided:** six versions of this rule shipped as criteria and all six leaked. Under a turn cap, filing costs one line and fixing costs the budget — so every reachable exit gets taken, and the run holding the context, the files and the authority disappears before anyone picks it up. See [`finding-routing.md` § 5 gate 0](finding-routing.md).

⟨PHASE 4⟩ adds `artifact` to the envelope as an additive field per §5, and the conformance check that reads it. **Not added to `CHILD_SCHEMA` today** — Phase 3 shipped hours ago and a required-field change mid-flight routes every conforming run to a human, which E2(c) measured as producing *silence* rather than an error.



**Closed.** A value outside the vocabulary is a malformed record and routes per §4.

**Abstention splits in two.** Every mature observable vocabulary surveyed has an abstention member — Kubernetes probes' `Unknown`, Argo's `Error` distinct from `Failed`, Monitoring Plugins' `Unknown`=3, pytest's exit 5 — and **all of them mean "the checker could not evaluate," never "the work is ambiguous."** Those are different conditions with different reliability and different remedies:

- a **computed** *could-not-check* arm — the evaluation did not complete
- an **asserted** *needs-a-ruling* arm — the evaluation completed and the answer is that a human must decide

One member doing both jobs measures neither. **Members, names and their emitters, written:**

| Member | Arm | Emitted by | Never emitted by | Means |
|---|---|---|---|---|
| `merge` | — | the child | the parent | the work is clean |
| `hold` + `hold_kind: redispatch` | — | the child | the parent | the runway closes with a scoped fix |
| `hold` + `hold_kind: needs_ruling` | **asserted** — *needs-a-ruling* | **the child, and only the child** | the parent | the evaluation completed and the answer is that a human must decide |
| `undetermined` + `undetermined_reason` | **computed** — *could-not-check* | **the parent, and only the parent** | the child — it is **not in the child's schema at all** | the evaluation did not complete |

**The split is enforced by the schema, not by convention.** `undetermined` is absent from the enum the child is given, so a child cannot assert it even by trying; and the parent never writes `outcome`, only `routed_outcome`. That is what makes each arm's rate measurable separately: a rise in `needs_ruling` is a statement about the work, a rise in `undetermined` is a statement about the machinery.

**Reliability and remedy differ, and that is the point of splitting them.** The computed arm is reliable because its emitter has no incentive to guess — every one of its reasons is a fact about a byte sequence or a process. The asserted arm is the one the literature predicts will be **under-emitted**, and that prediction is unmeasured. A `could-not-check` is a **defect in the checker with a fix**; a `needs-a-ruling` is a **request for a person and has no fix**. Both route to the human arm; only one of them is a bug.

**When an asserted verdict and a computed observable disagree, record both under distinct names.** The GitHub Actions `outcome`/`conclusion` split is the shape: the raw observation is never overwritten; the policy-adjusted value is what routing sees by default. **Precedence, written: the computed observable GATES and the asserted verdict DECIDES.** Rules R1–R5 of §4 read only computed values, and the child's `outcome` is not reachable until all five have passed; from R6 on, the child's assertion decides and the parent adds nothing. The child's `outcome` is copied into the record verbatim and is never overwritten, exactly as the shape requires — `routed_outcome` is a separate field. **The conditional is now resolved — Phase 1 E3(a), 2026-08-08: the off-diagonal cells are empty *by construction*, not merely unobserved.** So the two-name shape is adopted and **no composition machinery is built** — and note the reason is structural rather than a small-N argument, which means it does not weaken as the corpus grows.

## 4 · The fail-safe contract

**Total. It must have an answer for every input, including inputs nobody anticipated.**

Shape borrowed from Kubernetes `podFailurePolicy`: **ordered rules, first match wins, documented default.** The residual arm is a **named state that gets recorded** — never a silent fall-through.

Four conditions must each route explicitly, and each needs its own test: **absence · unparseability · staleness · unknown `schema_version`**. **The ordering, written — ten rules, first match wins, R9 is the documented default:**

| # | Condition | `routed_outcome` | `undetermined_reason` | Why it sits here |
|---|---|---|---|---|
| **R0** | the `result` event exists but **is not an object** | `undetermined` | `envelope_unreadable` | **The contract validates its own parameter.** Every rule below reads a key off this object, including the safety rule — see below |
| **R1a** | `permission_denials` **absent, or not a list** | `undetermined` | `denials_unreadable` | The parent **could not check** whether the control fired. Same arm as R1b, **different reason** — see below |
| **R1b** | `permission_denials` non-empty | `undetermined` | `permission_denied` | **Safety dominates routing.** A child that tripped the only in-run control is never redispatched, whatever it said about its own work — see below |
| **R2** | no `structured_output` key, **including no `result` event at all** | `undetermined` | `record_absent` | The measured common case, and **reachable from `subtype: success`** — see below |
| **R3** | present, but does not validate | `undetermined` | `record_unparseable` | Nothing downstream may read a field off an object that failed validation |
| **R4** | `schema_version` outside the supported set | `undetermined` | `schema_version_unknown` | **Before identity, deliberately:** a record whose version is unknown has no guaranteed typing, so its `run_id` is not yet a string one may compare |
| **R5** | `run_id` ≠ the nonce this invocation issued | `undetermined` | `record_stale` | The record is well-formed and belongs to a different invocation |
| **R5b** | `completion_ref` ≠ the reference this invocation is about | `undetermined` | `completion_ref_mismatch` | The record is FROM this invocation and is ABOUT a different durable record — see below |
| **R6** | `outcome == merge` | `merge` | — | From here the child's assertion decides and the parent adds nothing |
| **R7** | `outcome == hold`, `hold_kind == redispatch` | `hold` | — | |
| **R8** | `outcome == hold`, `hold_kind == needs_ruling` | `hold` | — | |
| **R9** | **default — nothing above matched** | `undetermined` | `unmatched` | The residual arm. A **named state that is recorded**, never a silent fall-through |

**R2 must not be read as "the run died", and the contract says so in its own words.** Phase 1 E2 measured a run that completed with exit **0**, `subtype: success`, `is_error: false`, a populated `.result` and **no `structured_output` key** — the model declined to call the `StructuredOutput` tool and asked a clarifying question instead. R2's documented population therefore includes *"the model declined to call the tool"* on an otherwise-clean run, and R2 fires on it exactly as it fires after a turn-cap death. **A parent that inferred failure from absence would be right three times out of four and wrong in the one case where every other signal already said clean.**

**`permission_denials[]` is safety observability, not a routing option.** Recorded and surfaced every run regardless of any routing ruling, and a non-empty list routes to the human arm and **never** to automatic redispatch. Auto-retrying a child that just tripped the only in-run safety control is an unbounded loop against that control. R1 is that rule, placed first so that no later rule can reach past it.

**The contract must be total over its OWN inputs, and the absence cases are not the same absence.** R1 reads `permission_denials` off the result envelope: if the envelope exists and the key does not — or the key is there and is not a list — the parent may not read that as an empty list. *"I could not check whether the safety control fired"* **routes exactly as** *"it fired"* does and **carries its own reason string**, `denials_unreadable`. And if there is **no `result` event at all** the condition is R2's, not R1's: no event implies no key, so the record is *absent* rather than unchecked. **Every one of these routes to a human, so the distinctions buy nothing in routing and everything in diagnosis.**

**R0 is that same sentence applied to the parameter itself, and it was missing for a pass while the paragraph above claimed it.** *"Total over its OWN inputs"* has to include the input's TYPE: the signature says `dict | None`, an annotation is not a check, and the implementation guarded only the `None` half — so a `result` event that arrived as a list, a string, an int or a bool raised `AttributeError` from **inside** the contract, where no caller's error handler catches it. It stayed latent because the one caller filters `isinstance(event, dict)` in a different file, which is a guarantee asserted nowhere at this boundary and one that [Phase 4](../development/memory-management-framework/phase4_fleet_migration.md)'s new call sites each re-decide for themselves. **R0 sits before R1 rather than after it** because an envelope that is not a mapping cannot answer the safety question either — *"could not check whether the control fired"* is the honest state, and it must be reached before the rule that assumes the envelope can be read at all. The claim is now **machine-checked rather than asserted**: a test enumerates every function in the module whose docstring makes the totality claim, probes each with every non-conforming type, and **fails when a third claimant is added without a probe** — so the next function to carry this sentence cannot carry it falsely.

**Why each one is a separate bin rather than a shared one, stated as a consequence.** The computed arm's instrument is `undetermined` **grouped by `undetermined_reason`** (§2.3), and nothing downstream persists the denial *count* — `append_parent_route` writes the outcome and the reason. So a shared bin is not a naming preference, it is a measurement failure with a known trigger: **if a future CLI renames or drops `permission_denials`, R1a fires on 100% of runs and every one of them reports `permission_denied`.** An operator reads a fleet-wide trip of the only in-run safety control where nothing fired, and the per-reason rate has no way to separate the two. The same argument applies one rule down — a run killed mid-stream is the most frequent machinery failure there is, and binning it under `permission_denied` sends an operator hunting a denied tool call that never happened.

> **This paragraph previously asserted that *"only the reason string distinguishes them"* while the code returned `permission_denied` for BOTH R1 conditions** — the doc claimed a property the implementation did not have, and the test asserted only the arm, so it was green either way. Fixed in the code (R1a/R1b above), here, and in a test that asserts the two reasons **differ** rather than that each is what it is. **The generalisable form is the one Phase 3 already recorded at R2: where two artifacts of one phase can disagree, the test must assert the field they would disagree ON.**

**R5b is the second half of R5, and the half an anchored pattern cannot supply.** R5 asks *did this record come from the invocation I issued*; R5b asks *is it about the record I dispatched against*. Both are answered by comparison against a value the parent generated, for the same reason: a record cannot vouch for its own identity. The threat is a `completion_ref` naming a different repository or a different PR, and it needs **no adversarial child** — children are instructed to read prior PR comments, which routinely contain other PRs' URLs, and the number derived from that field flows into `gh pr view`, `gh pr comment` and `--pr` on a downstream child that checks out and commits to that PR's branch. **The anchored URL pattern cannot detect it and never could:** `https://github\.com/[^\s)]+/pull/(\d+)`'s `[^\s)]+` **is** the owner/repo segment, so `https://github.com/someone-else/other-repo/pull/12` passes and yields `12`. *The pattern pins the host and guarantees digits; it does not pin identity.* `substrate`, `kind` and `id` compare exactly; `uri` compares by the `(owner/repo, number)` it names rather than byte-for-byte, so a trailing slash or a `/files` suffix is the same PR and a correct review is not failed on formatting.

> **⟨PHASE 4⟩ scope, stated so the row is not read as wider than it is.** R5b fires only where a caller can state the reference it dispatched against; `route`'s `expected_ref` parameter has **no default**, so a caller with none says so explicitly rather than skipping the rule silently. The one production caller today is `review_pr_workflow`, which builds it from its own `--pr` input and `gh repo view --json nameWithOwner` in the repository it is operating in — two values the child cannot influence.

**R9 exists because every surveyed system has an answer for the unmatched case and none of them is "fall through".** It is not decoration: R6–R8 do not exhaust the product of `outcome` × `hold_kind`, because a record can validate against a schema and still carry a combination no rule anticipated. **Enumerate that product; do not reason about it.** Of the six cells, two reach R9 and both are reachable today:

| | no `hold_kind` | `redispatch` | `needs_ruling` |
|---|---|---|---|
| **`merge`** | R6 → `merge` | **R9 → `unmatched`** | **R9 → `unmatched`** |
| **`hold`** | **R9 → `unmatched`** | R7 → `hold` | R8 → `hold` |

> **Why the enumeration is binding rather than illustrative.** §2.1 states `hold_kind` as *required iff `outcome == hold`* and the schema deliberately does **not** encode that — an `if/then` would be a required-field constraint the child can fail to satisfy, and Phase 1 E2(c) measured an unsatisfiable schema as *silence on a clean run* rather than an error. **A schema relaxed on purpose puts the whole conditional on the router**, and a `merge` carrying a `hold_kind` — a record whose own author said a human must decide — validates. A rule set that reads `outcome == merge` without the `hold_kind` guard routes it to `merge`, and the prose channel agrees because `merge` renders `MERGE`, so no shadow catches it. **This paragraph previously argued the product was not exhausted while naming only the `hold`-with-no-`hold_kind` cell; the argument was right and the enumeration was short by two.**

A future version's `hold_kind` reaching a parent whose supported set was widened without its rules being widened lands here too.

**Why total rather than best-effort:** the producer's malformedness is a **stationary rate with a distribution**, not a defect with a fix. That is the real difference from a CI step — *not* that the producer is uniquely unreliable. CI producers emit well-formed wrong results too, and it is measured. **"Our producer is special" is a claim a CI-literate reviewer will break;** the reason to be total is that the bad case recurs.

## 5 · Versioning and extension

- Every record carries `schema_version`. An unknown value routes per §4 — it is never ignored and never guessed at.
- **Extensions are additive.** A new consumer gets a new optional field; it does not get a reserved field today or a breaking change tomorrow.
- A field is removed only after no consumer reads it, demonstrated rather than asserted.

**Mechanism, ruled deliberately small.** `schema_version` is a **single integer as a string**, starting at `"1"`. A parent declares the set of versions it supports; a value outside that set routes to the human arm at rule R4 and is never guessed at. Adding an optional field does **not** bump it — that is what "additive" means, and a bump that fires on every additive change would route every skewed worktree to a human for no reason. It bumps only when an existing field changes type, changes meaning, or is removed.

**Compatibility window: the parent supports exactly the versions it has code for, and nothing is deprecated on a clock.** Skew is the normal case here rather than the edge case — a parent on `main` reads records written by children in worktrees cut from older revisions — so the window is a *set*, not a range, and it widens by adding a version to the set.

**Why this is the whole mechanism, and why a general framework would be worse.** Schema evolution across independently-versioned producers and consumers is a documented hard problem with a documented industry retreat, and the two live producers here are one prompt file and one Python module in the same repository. An additive-only rule plus a total fail-safe covers the failure this protocol actually has; a negotiation protocol or a compatibility matrix would be machinery for a fleet that does not exist yet, and §2's own rule against reserving fields for absent consumers applies to mechanisms too.

## 6 · Conformance

- **One declaration — of the record's SCHEMA *and* of its ADDRESS.** Both are declared once and loaded, never re-typed per consumer. A duplicated vocabulary passes every test in both copies while diverging — that is how `parse_verdict` came to be typed twice, and the copy that decided merges had zero tests.

  > **The address half is not a generalisation; it is the measured instance.** [Phase 2](../development/memory-management-framework/phase2_kind1_framework.md) found the Kind 1 block marker declared **three incompatible ways** — two readers matching any comment that merely *mentions* `pr_review:`, one fence-anchored — producing **3 false positives on 2 of the 8 archived PRs that carry a block**, and a wrong durable `pass:` on the most recently reviewed PR in the repo. Every test in every copy was green. **A schema-only reading of this rule would have called that conformant**, which is why the rule names both. Tracked as issue **#68**. *(Roadmap candidate 6, applied.)*
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

*Unratified. When all five phases are complete and the protocol has been exercised across the fleet, the operator records the ratification date and commit here, and the following are removed in the same change:*

- *the DRAFT banner at the top, and every remaining `⟨PHASE N⟩` marker;*
- ***§2's Status column***, and ***§2.4's phase-titled heading and its "this is an addition to E1(g)" framing.*** These record *where in the rollout* an answer arrived, which is how a draft tracks itself and is exactly what [Documentation Standard § *Standards state the rule, never completion-state*](documentation/documentation_standard.md) forbids a **ratified** standard from carrying. They are listed here so ratification removes them rather than inheriting them: §2's rows collapse to their rules, and §2.4 becomes *"Caller obligations under a declared schema"* with the measurement kept as a one-line backward-looking provenance note, which that section explicitly permits.*
- ***§4's two history-narrating passages*** — the paragraph beginning *"R0 is that same sentence applied to the parameter itself"* and the blockquote beginning *"This paragraph previously asserted"*. **Same rule, and they were missed by the list above until an audit found them**, which is the argument for enumerating rather than describing: each records that §4 once asserted a property the code lacked and when that was corrected, so each is rollout-tracking prose in a document that will state only the rule. At ratification the R0 paragraph collapses to its rule — *the contract validates its own parameter's TYPE, and R0 precedes R1 because an envelope that is not a mapping cannot answer the safety question* — and the blockquote goes entirely, its lesson already carried by the generalisable sentence at R2.*
