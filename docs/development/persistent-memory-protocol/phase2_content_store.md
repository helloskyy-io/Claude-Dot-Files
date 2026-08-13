# Phase 2 — The content store and offline hash verification

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** none — unblocked today, and it is the cheapest item in this component

Stores the bytes behind every claim, addressed by content hash, and ships a verifier that resolves every citation **from the content store alone** — re-hashing to detect an altered source and confirming the quoted span still occurs in it. **The check touches only the content store, so it holds with the network disabled.**

---

## Why this is second, and why it was nearly not planned at all

[`bernstein_capability_mining.md`](../../standards/architecture/research/raw/bernstein_capability_mining.md) §4.6 ranked this **Tier 1**, costed it **S–M**, named its roadmap home, and called it *"the item with the shortest path from 'read about it' to 'we are using it.'"*

**It was never placed** — not in `candidates.md`, not `direction.md`, not a roadmap, not an issue. The fleet then spent 2026-08-12 bounding by hand the exact cost it solves. That is the reason it is second rather than sixth: it is small, it is unblocked, and it has already been lost once by not being written into a plan.

Three payoffs from one mechanism, and they are independent of each other:

1. **It mechanises what `research-critic` does by hand.** The critic re-fetches every citation from the network to check it exists and says what the paper claims. Store the bytes, hash them, re-check the quoted span offline — same guarantee, no network, no rate limit, and repeatable.
2. **It makes a shared multi-edge store trustworthy.** [Phase 7](roadmap.md#phase-7--s3-aggregation-local-write-first-gated-a-second-edge-and-a-classification-ruling) ships records to a store every edge reads. A record that can be *proven* unaltered is a different object from one that is merely stored, and hashing is what makes the difference.
3. **It gives a no-new-evidence stop condition that is computed rather than judged.** An `evidence_set_hash` equal to a prior stage's means the stage saw exactly the same evidence. That is a stop condition derived from a hash, not from a model's opinion that nothing new turned up — and this fleet has already measured what model-asserted convergence flags are worth ([MMF Phase 5](../memory-management-framework/phase5_convergence_stopping.md) replaced one with a computed signal for precisely this reason).

---

## Requirements for completion

1. **Every cited artifact is stored by content hash** under the journal root. Nothing is inlined by value.
2. **`verify` resolves every citation from the content store alone** and runs correctly **with the network disabled** — demonstrated with the network actually off, not asserted.
3. **Three outcomes are distinguished by exit code**: verified / missing / tampered. A source that is absent and a source that has changed are different failures with different remedies, and collapsing them makes the verifier useless for diagnosis.
4. **A quoted span that no longer occurs in its source is reported as a distinct failure** from an altered source hash. A source can change without invalidating a quote, and a quote can vanish from an unchanged source only if the citation was wrong to begin with.
5. **`evidence_set_hash` is computed per stage**, and equality with the prior stage's is exposed as a stop condition — computed, not consumed by anything yet. Whether anything *routes* on it is a separate decision this phase does not make.
6. **Code diffs are carried as a commit SHA** and resolved from git, never copied into the store.

---

## Dependencies

- **[Phase 1](phase1_the_run_bag.md)** — needs a journal root to put the bytes under. `bernstein` §4.6 notes a cache directory is sufficient for the narrow version, so this phase is *not* blocked on Phase 1 being complete; it is sequenced after it so the store lands in its final home rather than being relocated.

Nothing else. In particular it does **not** need the emit rule ([Phase 3](phase3_the_emit_rule.md)) — a content store is useful the moment one run cites one source.

---

## What this phase decides

### By reference plus a hash, never content by value

**This is a rule about the whole system, and this phase is where it becomes mechanical.** It converged from three independent places:

- **`bernstein`'s artifact + hash contract** — every activity returns an artifact plus the hashes needed to replay it.
- **Every ceiling in [`state_passing`](research/raw/state_passing_between_workflow_children.md) §4.1** — Temporal 2 MiB per event, Temporal Cloud 40 KB per memo, Argo 1 MB, Airflow *"small amounts"*. Every mature system draws this line, and each drew it after being hurt.
- **Our own `upstream_block` docstring**, which records that inlining a synthesis cost 48k characters and tripled a prompt.

**And our own by-value channel is a single `execve` argument, capped by the kernel at 131,072 bytes.** The largest fixed template is already at **58%** of it and the substituted blocks are unbounded. Exceeding it is not degradation — it is a hard `E2BIG` naming neither the prompt nor the block that grew.

*(The parent↔child half of this rule is already shipped in [MMF Phase 3](../memory-management-framework/phase3_typed_exit_record.md). This phase applies it to the **record**: the journal names an artifact and its hash; the bytes live in the content store.)*

### What "verify" actually checks, and what it cannot

`bernstein activity verify <run>` *"resolves every citation from the content store alone"*, *"re-hashes them to detect an altered source, and confirms the quoted span still occurs in them"*. The browser modality does the same for DOM bytes: verification *"reattaches the DOM bytes by hash and re-evaluates the assertion"*.

**What it proves:** the bytes this claim was made against are the bytes still on disk, and the quoted span is still in them.

**What it does not prove, stated so nobody over-reads the guarantee:**

- **Not that the claim is true.** A correctly-quoted span from a wrong source verifies clean. Verification is an integrity check, not an epistemic one — it replaces the *mechanical* half of what `research-critic` does and leaves the judgement half exactly where it is.
- **Not that the live source still says this.** The store is a snapshot. An upstream page that changed after capture verifies clean against the capture and is a different finding, reachable only by re-fetching — which is the currency question [`research-currency`](../../../config/agents/research-currency.md) owns, not this phase.

Both limits are why requirement 3's three outcomes matter: a verifier that returns one boolean invites exactly this over-reading.

### The evidence set hash is computed, not routed on

Requirement 5 stops at *computed and exposed*. **Nothing gates on it in this phase**, deliberately.

[MMF Phase 5](../memory-management-framework/phase5_convergence_stopping.md) is the precedent and it is worth following exactly: it built a computed convergence signal, shadowed it, and **gated nothing** — because two positive observations are not a rate, and a stopping rule that fires early ends productive work silently with no failing test. The same argument applies here without modification. Whoever proposes routing on `evidence_set_hash` owns producing the firing-rate evidence first.

---

## Implementation checklist

- [ ] Specify the citation record: `claim_id`, `quote`, `source_ref`, `page_content_hash`
- [ ] Specify the content store layout under the journal root — content-addressed, so the same source cited by two runs is stored once
- [ ] Build the capture path: store raw bytes plus sha256 at the moment a source is read
- [ ] Build `verify`: resolve, re-hash, re-check span; three exit codes; span-miss reported separately from hash-mismatch
- [ ] Demonstrate with the network disabled, and record how the network was disabled
- [ ] Demonstrate detection of a deliberately altered stored byte
- [ ] Compute `evidence_set_hash` per stage and expose it; **route nothing on it**
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for hashing and span-matching, `integration/` for a verify pass over a real prior research run
- [ ] Record in § *Measurement*: how many citations were verified, how many failed, and the wall-clock against a network re-fetch of the same set

---

## Measurement

*(Populated when the phase runs. Figures come from commands run in the tree and are pasted with the command.)*

The comparison that makes the case is **offline verify wall-clock versus network re-fetch wall-clock over the same citation set**, with the citation count as the denominator. `bernstein` §4.6 is documentation-level evidence, not behavioural — its own paper says so in §7.1 — so this fleet's own number is what settles whether the mechanism is worth what it cost.

---

## Notes and open items

- **This phase does not change `research-critic`.** It builds the mechanism the critic could use. Migrating the critic onto it is a separate change with its own evidence bar, and folding it in here would make this phase's outcome unverifiable independently of the critic's behaviour.
- **Cost is `S–M` per `bernstein` §4.6** — S for the narrow version (a fetch cache storing raw bytes plus sha256 per URL, and a verifier re-checking each quoted span), M for the full lineage artifact. **This phase is scoped to the S version.** If the M version is wanted, it is a later phase and the trigger is a named need, not tidiness.
