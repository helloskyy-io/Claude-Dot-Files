# Phase 2 — The content store and offline hash verification

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** none — unblocked today, and it is the cheapest item in this component

## What this phase does

When a run quotes a source, it currently records where the source was and trusts that it will still be there and still say the same thing. Neither is safe: pages change, repositories move, and re-checking a citation means fetching it again over the network — slowly, subject to rate limits, and against whatever the page says *today* rather than what it said when the claim was made.

This phase fixes that by keeping the bytes. When a run reads a source, the source's actual content is saved to a cache and given a name computed from those bytes — a checksum, so the name changes if a single byte does. A checker then re-reads every citation **from that cache alone**: it recomputes the checksum to confirm the bytes have not changed, and confirms the quoted words still appear in them. It touches nothing on the network, so it works offline and gives the same answer every time.

**Terms used here.** The **journal** is the whole record: one folder per run, never edited after the run ends. The **content store** is the byte cache this phase builds — the sources themselves, filed under their checksums. A **checksum** is a short value computed from a file's bytes; two files with the same checksum are the same file, and changing one byte changes the checksum. To **rebuild** a store is to read the journal back and regenerate what it holds. An **edge** is one machine running this fleet.

---

## Why this is second, and why it was nearly not planned at all

[`bernstein_capability_mining.md`](../../standards/architecture/research/raw/bernstein_capability_mining.md) §4.6 ranked this **Tier 1**, costed it **S–M**, named its roadmap home, and called it *"the item with the shortest path from 'read about it' to 'we are using it.'"*

**It was never placed** — not in `candidates.md`, not `direction.md`, not a roadmap, not an issue. The fleet then spent 2026-08-12 bounding by hand the exact cost it solves. That is the reason it is second rather than sixth: it is small, it is unblocked, and it has already been lost once by not being written into a plan.

Three payoffs from one mechanism, and they are independent of each other:

1. **It mechanises what `research-critic` does by hand.** The critic re-fetches every citation from the network to check it exists and says what the paper claims. Store the bytes, hash them, re-check the quoted span offline — same guarantee, no network, no rate limit, and repeatable.
2. **It makes a multi-edge store checkable for corruption.** [Phase 7](phase7_s3_aggregation.md) ships records to object storage, and a record whose bytes can be re-checked on arrival is a different object from one that is merely stored. **Read this claim narrowly, and § *What "verify" actually checks* below is the reason:** a self-computed manifest is regenerable by anyone who can write the bag, so it proves integrity against **accident and transport corruption**, not against a party with write access. **Authenticity is a separate property and this mechanism does not supply it** — stated flatly here so the claim is not later used to skip an authentication step at [Phase 7](phase7_s3_aggregation.md).
3. **It gives a no-new-evidence stop condition that is computed rather than judged.** An `evidence_set_hash` equal to a prior stage's means the stage saw exactly the same evidence. That is a stop condition derived from a hash, not from a model's opinion that nothing new turned up — and this fleet has already measured what a model-asserted convergence flag is worth, and replaced one with a computed signal for precisely this reason.

---

## Requirements for completion

1. **Every cited artifact is stored by content hash** under the journal root. Nothing is inlined by value.
2. **`verify` resolves every citation from the content store alone** and runs correctly **with the network disabled** — demonstrated with the network actually off, not asserted.
3. **Three outcomes are distinguished by exit code**: verified / missing / tampered. A source that is absent and a source that has changed are different failures with different remedies, and collapsing them makes the verifier useless for diagnosis.
4. **A quoted span that no longer occurs in its source is reported as a distinct failure** from an altered source hash. A source can change without invalidating a quote, and a quote can vanish from an unchanged source only if the citation was wrong to begin with.
5. **`evidence_set_hash` is computed per stage**, and equality with the prior stage's is exposed as a stop condition — computed, not consumed by anything yet. Whether anything *routes* on it is a separate decision this phase does not make.
6. **Code diffs are carried as a commit SHA** and resolved from git, never copied into the store.
7. **The store's shape, its path derivation, and its fetch policy are specified** — § *What the store is, concretely* below. Each of the three is a way this mechanism becomes an attack surface if left to build time.
8. **Capture and resolve are ACTIVITIES**, not helpers a caller remembers to call — the same reason [Phase 1](phase1_the_run_bag.md) requirement 11 gives, applied to the store's two entry points. A source read through a path that does not capture is a citation nobody can re-check offline, and it fails silently.

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

*(The parent↔child half of this rule is already shipped in the typed exit record, which carries a reference rather than a payload. This phase applies the same rule to the **record**: the journal names an artifact and its hash; the bytes live in the content store.)*

### What "verify" actually checks, and what it cannot

`bernstein activity verify <run>` *"resolves every citation from the content store alone"*, *"re-hashes them to detect an altered source, and confirms the quoted span still occurs in them"*. The browser modality does the same for DOM bytes: verification *"reattaches the DOM bytes by hash and re-evaluates the assertion"*.

**What it proves:** the bytes this claim was made against are the bytes still on disk, and the quoted span is still in them.

**What it does not prove, stated so nobody over-reads the guarantee:**

- **Not that the claim is true.** A correctly-quoted span from a wrong source verifies clean. Verification is an integrity check, not an epistemic one — it replaces the *mechanical* half of what `research-critic` does and leaves the judgement half exactly where it is.
- **Not that the live source still says this.** The store is a snapshot. An upstream page that changed after capture verifies clean against the capture and is a different finding, reachable only by re-fetching — which is the currency question [`research-currency`](../../../config/agents/research-currency.md) owns, not this phase.
- **Not that the record is authentic.** A manifest or digest computed by the storing party is regenerable by any party with write access. This detects accident and transport corruption; it does not detect a party who can write. See payoff #2 above and [Phase 7](phase7_s3_aggregation.md) § *Where a shared bucket would change things*.
- **Not that a back-filled capture proves anything about the run it came from.** Requirement 2 demonstrates against *a real prior run*, and a run predating the capture path has no stored bytes — so its sources must be fetched now, and the hash then proves the bytes matched **at back-fill**, not that the claim was made against them. **Requirement 2 is met by a run captured at read time.** A back-filled corpus is labelled a mechanism demonstration and nothing more.

All three limits are why requirement 3's outcomes are distinct: a verifier that returns one boolean invites exactly this over-reading.

### What the store is, concretely — requirement 7

Three sub-decisions the draft left to build time. Each is where a byte cache turns into an attack surface, and each is one sentence now.

**(a) Shape: per-run or root-level shared.** The draft implied both — *"content-addressed, so the same source cited by two runs is stored once"* is a cross-run store, while [Phase 1](phase1_the_run_bag.md) makes a run's record a self-validating bag. **They are not compatible without a stated answer**, because a root-level store sits outside every bag's payload, so a bag shipped to S3 validates clean with its cited bytes absent at the destination — and [Phase 7](phase7_s3_aggregation.md) claims exactly that validation. Pick one and state the cost: **per-run** means bags are self-contained and bytes are duplicated; **root-level shared** means dedup, bags are not self-contained, and Phase 7 must ship a bag's referenced objects with it (which its checkbox now says).

**And root-level shared creates a reclamation obligation that per-run does not.** Under the per-run shape, deleting a bag deletes its bytes and nothing is left over. Under the shared shape, [Phase 5](phase5_snapshots_then_retention.md)'s retention removes bags and **nothing reclaims the objects they referenced**, so the content store grows without bound while the journal is nominally bounded. **Ruling this sub-decision therefore also names who does the reachability pass** — [Phase 5](phase5_snapshots_then_retention.md)'s checklist carries it, conditional on this answer. The obligation is written into the decision that creates it rather than left as a note in the phase that discovers it.

**(b) Path derivation: from the computed digest ALONE.** Content addressing is safe only if the on-disk path is a function of the digest *this store computed* — e.g. `sha256/ab/cdef…`, algorithm-prefixed so a future algorithm change cannot collide the namespace. **If any source-controlled string enters the path** — a per-URL cache key, a domain folder, a filename or extension from the URL or a `Content-Disposition` header — a crafted URL or a redirect writes outside the store, which sits under the journal root next to the bags. Human-facing names, URLs and content types are **metadata inside the citation record, never path components.**

**(c) Fetch policy, if this phase fetches at all.** If the capture path merely **tees an existing tool's output**, say so and state that it inherits that tool's policy — that sentence is the whole requirement. If it is a **new fetcher**, the URL is model-influenceable (and may come from a previously-fetched document), so the policy is stated: `https` only; redirects re-validated on each hop; refusal of URLs resolving to private, loopback or link-local addresses; a timeout; a per-object size cap; and bytes stored **as received**, or with a decoded-size cap if content-encoding is decoded. Without it, this is an SSRF primitive whose responses are **durably stored and re-servable offline**, on a store nothing bounds until [Phase 5](phase5_snapshots_then_retention.md).

**(d) `verify` is the bulk run of a read-path invariant, not a separate command.** A store whose integrity is checked only when someone invokes the checker is checked in practice never. **All reads go through one resolver that re-hashes on resolve and fails closed**, and `verify` is that resolver run over everything. Cheap here; a cross-cutting refactor once three phases read the store directly.

### The evidence set hash is computed, not routed on

Requirement 5 stops at *computed and exposed*. **Nothing gates on it in this phase**, deliberately.

**The fleet's own convergence signal is the precedent and it is worth following exactly:** it was built as a computed signal, shadowed beside the incumbent, and **gated nothing** — because two positive observations are not a rate, and a stopping rule that fires early ends productive work silently with no failing test. The same argument applies here without modification. Whoever proposes routing on `evidence_set_hash` owns producing the firing-rate evidence first.

---

## Implementation checklist

- [ ] Specify the citation record: `claim_id`, `quote`, `source_ref`, `page_content_hash`
- [ ] Rule requirement 7(a): per-run or root-level shared, with the cost stated and Phase 7's checkbox reconciled
- [ ] Specify the content store layout under the journal root — the on-disk path derived from the **computed digest alone**, algorithm-prefixed
- [ ] Build the capture path: store raw bytes plus sha256 at the moment a source is read — and state the fetch policy, or state that it tees an existing tool and inherits that tool's policy
- [ ] Build the single resolver that re-hashes on resolve and fails closed; `verify` is that resolver run in bulk — **both as activities** (requirement 8)
- [ ] Build `verify`: resolve, re-hash, re-check span; three exit codes; span-miss reported separately from hash-mismatch
- [ ] Demonstrate with the network disabled, and record how the network was disabled — **on a run captured at read time**, not a back-fill
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
