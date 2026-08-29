# The model-issued harvest — Persistent Memory Protocol

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** [The emit rule](phase3_the_emit_rule.md)

## What this phase does

[The emit rule](phase3_the_emit_rule.md) wraps every place *fleet code* writes to a store, so the write and its journal entry happen together. **This phase covers the other half: the writes the model itself issues.**

A child runs `gh pr comment --body-file …` because a prompt told it to. There is no call site to wrap — the instruction is a sentence in a prompt, and the process that carries it out has already exited by the time anything could react. **And these are the writes this component exists for.** The PR body, the decision log, the reflection comment are the first artifacts the design names, and they are where the reasoning lives. A record that holds every file write and none of the prose is a record that answers *what changed* and never *why*.

So this phase builds a **post-exit harvest**: once a child has finished, fleet code fetches what that run wrote to its GitHub surfaces, keyed by run id, and emits it into the bag verbatim like any other event. And it builds the thing that keeps the harvest honest afterwards, which is the part a one-time demonstration cannot supply.

**Terms used here.** The **journal** is the whole record: one folder tree per machine, one folder per run, never edited after the run ends. A **bag** is one run's folder (the name comes from BagIt, the file-layout standard it follows — a folder on disk, never a Docker container). To **emit** is to write one entry into the journal. A **store** is any place other than the journal that a run writes to. A **fleet-code write** is one made by a call site in `scripts/`; a **model-issued write** is one the model performs itself, on an instruction from a prompt. The **harvest window** is the interval between a child exiting and the harvest running.

---

## Why this is its own phase and not a checklist item of the emit rule

**The two halves need different mechanisms, and the plan has said so since it was drafted.** [The emit rule](phase3_the_emit_rule.md) § *The write-path inventory* states the consequence outright: *"a build that enumerates only the first half populates the table, wires every row, closes requirement 1, and never emits a single PR comment — and nothing goes red."* A wrap and a harvest share no code, no failure mode and no test shape.

**They also depend on different things.** The fleet-code half needs a run id and a filesystem. The harvest needs the GitHub API, a pull request that exists, and the run to have *ended* — which is the one precondition no wrapper can hold, because a wrapper runs inside the thing it wraps.

**And the harvest is the half with a finding already filed against it.** [`C-6i1u3b1f`](../../../tracked/candidates/C-6i1u3b1f.md) records that the harvest's only backing in the plan was **one checklist item — a single demonstration, not a check** — and that [Rebuildability is a test](phase4_rebuild_is_a_test.md)'s negative test is scoped to the stores in *its* test set, which do not include a GitHub surface. Left as a checklist item inside a phase that already carries thirteen requirements, the standing check is the item that gets dropped when the phase runs long. **Its remedy is requirement 4 below.**

**The residual risk of splitting, stated rather than hidden.** For as long as this phase has not landed, the emit rule's headline claim — *if any store gets it, the journal gets it* — is **true of files and false of prose**. That is why this phase is listed immediately after it and before [Rebuildability is a test](phase4_rebuild_is_a_test.md): a completeness test run over a journal knowingly missing the half where the reasoning lives produces a green check over a half-record, which is the *half-readable reads as coverage* failure the component's own retention rule forbids.

---

## Requirements for completion

1. **Everything a run wrote to a GitHub surface appears in its bag, verbatim** — the pull-request body, every comment on it including the decision log and the post-run reflection, the review verdict and any issue body the run authored. Emitted as ordinary journal events with the destination as a field, on [the emit rule](phase3_the_emit_rule.md)'s contract and not a second one.
2. **The harvest is keyed by run id and lands in that run's bag**, including when the run produced several PRs or none. A harvest that cannot resolve a run id to a bag **fails loudly** rather than writing into a bag it guessed at.
3. **The harvest window's failure mode is stated, bounded and measured.** A comment posted after the harvest runs is not captured. This requirement is met by (a) naming where the window opens and closes, (b) making the residual visible in the record rather than invisible — a bag says what its harvest covered and when it ran — and (c) reporting how many comments arrived inside the window against how many the surface holds now, with the denominator.
4. **A standing check covers the harvest half, in the family of the enumerating sweeps this component already uses.** Not a one-time demonstration. Either a sweep asserting that every workflow which posts to a GitHub surface produces a harvested completion in its own bag, or a per-run reconciliation counting store-side comments against harvested completions and failing on a shortfall. **Which of the two is this phase's build decision; that there must be one is the requirement.** [`C-6i1u3b1f`](../../../tracked/candidates/C-6i1u3b1f.md) is the filed form of this.
5. **A harvest that fails is never silent** — it takes [the emit rule](phase3_the_emit_rule.md)'s four write-failure cases as given and adds none of its own. A failed harvest appends a typed gap event naming the surface it could not read, and marks the bag `incomplete`, so [Rebuildability is a test](phase4_rebuild_is_a_test.md) counts it rather than diffing over it.
6. **The capture-time secret filter applies to harvested bytes on the same path**, before anything reaches the journal root. A PR comment is external text this fleet did not compose, and it enters the record through a path the fleet-code wrap never touches.
7. **The harvest is an ACTIVITY**, on the same reasoning as [the journal root and the run bag](phase1_the_run_bag.md) requirement 11 — a step a parent invokes rather than a library call somebody remembers. **Same split as elsewhere:** layer placement, invocation and fail-stop are buildable today; orchestrator-driven retry and recorded execution are port-time.

**Requirement 3 is the honest half of requirement 1**, and it is why the window is measured rather than assumed small. *"Every comment"* is unachievable against a surface anyone may keep writing to; *"every comment inside a stated window, with the shortfall counted"* is achievable and is what a reader can act on.

---

## Dependencies

- **[The emit rule](phase3_the_emit_rule.md)** — hard. The event contract, the destination field, the four write-failure cases and the capture-time filter are all its, and this phase adds no second contract. There is nothing for a harvested comment to become until they exist.
- **[One run, one identity, one bag](phase9_one_run_one_identity.md)** — indirect, through the phase above. Requirement 2 resolves a GitHub artifact to a bag by run id, so it inherits that phase's ruling on who names a run.
- **`gh` and a GitHub token** — the harvest is a network read against a vendor API, which no other phase in this component is. Its rate limits, its pagination and its edited-comment semantics are facts to look up at build time, not to plan from memory.
- **Not a dependency: [the content store](phase2_content_store.md).** A harvested comment is authored content carried verbatim, not a cited artifact resolved by checksum.
- **[CPI reads the journal](phase6_cpi_reads_the_journal.md) is this phase's CONSUMER, not its dependency**, and it is named here because until 2026-08-28 it was named nowhere. This phase's output — the pull-request body, the decision log and the reflection comment — is what that phase's evidence sweep reads to find what keeps going wrong across runs, and it enters [Phase 6](phase6_cpi_reads_the_journal.md) r3's producer/consumer table like any other producer. **A producer of the writes this component exists for, with no reader enumerated anywhere in the plan, is precisely the failure the synthesis's *pair every producer with its consumer* rule is about** — and it happened here because [Phase 6](phase6_cpi_reads_the_journal.md) r3 stated its scope as the numeric range *"Phases 1–4"*, which this phase's number falls outside of. The range is now a named list.

---

## What this phase decides

### Harvest, not intercept — and the alternative is named so it is not silently re-derived

**The obvious alternative is to intercept.** Route every model-issued `gh` invocation through a fleet-owned wrapper, and the model-issued half becomes the fleet-code half. It is genuinely tempting, and it is rejected here for a reason that would otherwise be rediscovered mid-build.

**An interception is only as complete as the set of paths it covers, and the model chooses its own paths.** This fleet runs with permissions bypassed; a child that reaches the API through `curl`, through a differently-spelled command, or through a tool that did not exist when the wrapper was written, bypasses it — and the bypass is **silent**, because the wrapper's own view is that nothing was written. That is the exact shape this component's other guards exist to close: [the journal root and the run bag](phase1_the_run_bag.md) § *And the rule stayed prose, so it leaked twice more* records four instances of one forging class, each fixed against the specific operand that had been exploited, with the next instance arriving through the operand nobody enumerated.

**The harvest reads the destination instead of the path.** It asks the surface what it holds, so it is complete with respect to *what actually landed* regardless of how it got there. Its failure mode is a **window**, which is bounded and measurable — and a bounded, measurable gap is strictly better than an unbounded, invisible one.

**Where an interception would still help, recorded so the trade is not read as a dismissal:** it would close the window, because an intercepted write is captured at the moment it happens. If the measured shortfall in requirement 3 turns out to be non-trivial, adding interception *beside* the harvest — belt and braces, harvest still authoritative — is the response. **That is a trigger, not a plan**: build it when the number says so.

### Which surfaces are in scope, and the one that is not

**In scope:** the pull request this run opened or was dispatched against — its body, and every comment on it. Issue bodies and comments the run authored. Review verdicts posted as comments.

**Out of scope, deliberately: the pull request's *review state* as GitHub computes it** — approvals, requested changes, the merge status, the checks. Those are not something a run *authored*; they are a service's derived view, they change after the run has ended, and there is no moment at which capturing them would be capturing a write. **A run's own review verdict is authored prose and is in scope; GitHub's rendering of who approved what is not.**

**⚠ And a harvested comment may have been edited or deleted before the harvest ran.** GitHub comments are mutable and this component's record is not, which is precisely the argument for harvesting them at all. **What the record then holds is what the surface held at harvest time, and the bag says so** — the harvest timestamp is part of requirement 3's window statement rather than a detail. A record that silently presents a mutable surface's *later* state as what a run wrote would be worse than no record, because it would be confidently wrong about authorship.

### Why the standing check cannot be the rebuild test

[Rebuildability is a test](phase4_rebuild_is_a_test.md) replays the journal and diffs the result against a live store. **That works for a store the fleet can rebuild**, and its own § *Which stores are in the test set* names GitHub-hosted surfaces as the expected hard case: a PR thread's rendered state depends on GitHub's ordering and on edits made outside any run, so it may land in that phase's *not covered* table rather than in its test set.

**So the guarantee for this half cannot be inherited; it has to be built here.** Requirement 4's check does not attempt to rebuild a PR thread. It asserts something weaker and achievable: **that a run which posted to a GitHub surface has a harvested completion for it.** A shortfall is a red test, and the reason the check exists is that a harvest which quietly stops working looks exactly like a run that posted nothing.

### The third category is not this phase's

[The emit rule](phase3_the_emit_rule.md) § *The write-path inventory* names a third category — writes made by **no run at all**, chiefly an operator editing a `tracked/` item by hand. **That is not a model-issued write and this phase does not cover it.** It is called out here only because the two are easy to conflate: both are invisible to a tree search, and both would be reverted by a replay that does not know about them. Their mechanisms are unrelated — the operator's natural emit is the git commit; a model's is a network read against a vendor API. The third category is ruled by the emit rule's requirement 9, or scoped out by [Rebuildability is a test](phase4_rebuild_is_a_test.md) requirement 5.

---

## Implementation checklist

- [ ] Enumerate every workflow that posts to a GitHub surface, and the surfaces each one posts to — from the tree, with the command that enumerated it
- [ ] Look up and record the vendor facts this design turns on: comment pagination, the edited/deleted comment representation, and the rate limit a per-run harvest sits inside — **from the official documentation, cited in § *Runtime Verification*, not from memory**
- [ ] Build the harvest: fetch the run's PR body, comments and authored issue bodies by run id, and emit each verbatim on [the emit rule](phase3_the_emit_rule.md)'s event contract with the destination as a field
- [ ] Resolve run id → bag, and **fail loudly when it does not resolve** rather than writing into a guessed bag (requirement 2)
- [ ] Record the harvest's own window in the bag — when it ran, and which surfaces it covered (requirement 3)
- [ ] Route harvested bytes through the capture-time secret filter on the same path as any other payload (requirement 6)
- [ ] Build the harvest as an activity a parent invokes, with fail-stop on error (requirement 7)
- [ ] Emit a typed gap event and mark the bag `incomplete` when a surface cannot be read, and confirm [Rebuildability is a test](phase4_rebuild_is_a_test.md) counts that bag as gapped rather than diffing it (requirement 5)
- [ ] **Build the standing check** (requirement 4) — decide between the enumerating sweep and the per-run reconciliation, state which and why, and confirm it goes RED when the harvest is disabled
- [ ] Demonstrate a full `research_minor` cycle whose PR body and every comment appear in its bag verbatim, with the command and the observed byte count
- [ ] Post a comment *after* the harvest window on that same cycle, and confirm the shortfall appears in the record as a counted gap rather than as silence
- [ ] Tests per the [Testing Standard](../../standards/testing/README.md): `unit/` for run-id-to-bag resolution, the gap path, and the filter on harvested bytes; `integration/` for one real harvest against a real pull request
- [ ] Record the window shortfall with its denominator in § *Measurement*

---

## Runtime Verification

*(Populated when the phase runs. **Required** — this phase orchestrates an external runtime: the GitHub API, reached through `gh`.)*

The commands run verbatim, the output actually observed, the date and the host. Documentation describes intent; running systems define reality — and every vendor fact this design rests on (pagination, edited-comment representation, rate limits) is a claim about a service that can change without this document changing.

---

## Measurement

*(Populated when the phase runs.)*

Two figures, both with denominators:

- **Comments harvested against comments the surface holds now**, for the demonstration cycle. This is the harvest window's cost, stated as a fraction rather than as a reassurance. It is also the number that decides whether the interception discussed above ever gets built.
- **Runs with a harvested completion against runs that posted to a GitHub surface**, which is requirement 4's check expressed as a rate. A green check over one run and a green check over every run are different claims, and only the second is what this phase promises.

---

## Notes and open items

- **This phase is where the component's design test becomes true or stays half-true.** *"If I have a question it always starts in the journal"* is a claim about reasoning, and the reasoning is in the prose this phase captures. Descoping it leaves a record that holds every file the fleet wrote and none of the argument for writing it.
- **The harvest reads a surface the fleet does not control, and that is a standing dependency rather than a one-time integration.** A vendor API change breaks the harvest silently unless requirement 4's check is in place, which is the second reason that check is a requirement and not a checklist item.
- **Nothing here bounds how long the record of a GitHub surface stays useful.** The captured prose is authored output and falls under the same storage budget as everything else — [snapshots, then retention](phase5_snapshots_then_retention.md) governs it, and there is no exemption for it.
