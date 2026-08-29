# The journal root and the run bag — Persistent Memory Protocol

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status: 🔨 BUILT (2026-08-16) — all eleven requirements closed on the buildable half; r11's orchestrator half is port-time and stays open with prose saying why** · **Gate:** none — unblocked today

## What this phase does

This phase decides where a run's record goes on disk and what shape it takes, and builds a checker that says whether a given folder is a well-formed one. Nothing writes into it yet — that is the next phase. The outcome here is a folder that a checker says is valid.

It is first because getting the shape wrong is the expensive mistake. Once three phases are writing into a tree, changing how that tree is organised means rewriting records that were supposed to be permanent — and by then the folders are the only thing that can regenerate everything else, so changing them means changing everything.

**Terms used here.** The **journal** is the whole record: one folder tree per machine, one folder per run, never edited after the run ends. A **bag** is one run's folder — the name comes from BagIt, the file-layout standard the folder follows. *(It is a folder on disk. It is never a Docker container, and this document does not use that word for it.)* A **manifest** is a file inside the bag listing every other file in it with a checksum for each, so a reader knows what is there and whether the bytes have changed. To **emit** is to write one entry into the journal. To **rebuild** a store is to read the journal back and regenerate what that store holds. An **edge** is one machine running this fleet.

---

## Requirements for completion

1. **The root is a config value, and nothing depends on a home directory.** One documented default per deployment shape. The reason this is a requirement rather than a convenience is in § *Why the root is configurable* below.
2. **A run's record is one folder keyed by `run_id`.** Never by path. Never by API key.
3. **Concurrent children write to their own subfolder** inside the run folder, so no two writers ever share a file.
4. **The folder is a valid BagIt bag** per [RFC 8493](https://www.rfc-editor.org/rfc/rfc8493.html) — a `data/` payload directory, a `manifest-sha256.txt` listing every payload file with its checksum, and a `bagit.txt` declaring version and encoding.
5. **A validator re-hashes the payload and reports pass/fail**, and it is wired into the test suite.
6. **`bag-info.txt` carries the event schema version**, and the versioning rule is written down beside it. **Not `bagit.txt`** — RFC 8493 requires that file to consist of exactly two lines (`BagIt-Version` and `Tag-File-Character-Encoding`), so putting anything else there makes the bag non-conforming and forfeits the entire reason BagIt was chosen.
7. **The payload spec is stated as a table with a reason per row** — what goes in the journal, what stays out, and why for each exclusion — **and it states what happens to `.claude/logs/`** (§ *The surface this replaces* below). **Every row also carries a classification slot**; § *Why the payload spec carries a classification slot it does not yet fill* below.
8. **The bag's state is `open` or `sealed`, plus two independent flags — `redacted` and `incomplete`** (§ *Bag lifecycle* below). **The validator always reports all three fields**, never one label that hides the others. `incomplete` is [Phase 3](phase3_the_emit_rule.md)'s write-failure marking.
9. **The root's permissions and ownership are part of the resolution contract**, not left to umask (§ *Why the root is configurable*) — **and a root that cannot be resolved to a writable directory means the run does not start**, rather than starting and recording nothing.
10. **No database is recorded as a decision with a revisit trigger**, not as an omission.
11. **Opening the bag is an ACTIVITY that a parent invokes as its first step, AND a test enumerates every parent and asserts it does.** The activity boundary alone does not make the call happen; the enumerating test is what makes it structural. § *Why this is an activity and not a library* below, which also splits what is buildable today from what only the orchestrator can supply.

---

## Dependencies

**None for the buildable half.** This phase depends on nothing built or unbuilt, and it is deliberately the one phase in this component with no upstream gate, so the folder structure exists before anything needs it.

**⚠ One half of requirement 11 is port-time, and saying so is what stops a dispatch either stalling or checking the box on a plain function.** *Layer placement, invocation as the parent's first step, fail-stop on error, and the enumerating test* are all buildable today. **Orchestrator-driven retry and recorded execution are not** — they are properties of a worker that does not exist, and the vendored [Temporal Standard](../../standards/temporal/README.md) places worker configuration and the activity map at port time. Requirement 11 closes on the buildable half; the port carries the rest. [Phase 2](phase2_content_store.md) r8 and [Phase 3](phase3_the_emit_rule.md) r12 split the same way.

It is depended on by every other phase in the component.

---

## What this phase decides, and the reasoning behind each

### One location, a folder per run, many formats

The journal is **one root location per edge**, with subfolders and files as needed. Each artifact keeps the format that suits it — the transcript stays JSONL, authored markdown stays markdown, execution facts are typed JSON, code is a SHA. **The protocol is what knows how to read each kind.**

This is not a filing convention. It is what makes three later things cheap:

- **It generalises "two formats."** [`state_passing`](research/raw/state_passing_between_workflow_children.md) §4.3.2 found no single format serves humans and machines equally well and that mature systems do not try. There are as many formats as artifact kinds; **what has to be single is the folder they all live in, not the encoding.**
- **It makes Phase 7 trivial.** Syncing a directory tree to object storage is a solved, boring operation. Syncing "a database plus some files plus some GitHub state" is not.
- **It makes [Phase 4](phase4_rebuild_is_a_test.md)'s rebuild test tractable.** Replay operates on one run's folder, in order, rather than on a query across a shared store.
- **It gives [Phase 5](phase5_snapshots_then_retention.md)'s retention its unit.** A run folder is the thing that gets deleted, entire — which is what makes a deletion explicable (*this run rotated out*) rather than a record you can half-read.

**Provenance.** The operator identified the shape before any of this research: it is what Claude Code itself does — one store under `~/.claude/`, broken out into per-project folders. Same shape, independently arrived at.

### Key by `run_id`, never by path — and this is the one place not to copy Claude Code

Claude Code's layout keys by mangled path, which produces separate directories for `-home-puma-Repos-claude-dot-files` and `-home-puma-Repos-claude-dot-files--claude-worktrees-build-1786019575`. **Every worktree becomes its own project.** This fleet runs everything in worktrees, so path-keying would scatter one logical run across several folders and make a run's record unassemblable.

*(And Claude Code has **no** manifest — it relies on naming convention, validating the folder structure and not the contents. BagIt validates. That is the second reason not to copy it.)*

### The manifest is BagIt, and it is not invented here

**Without a per-run manifest declaring what is in the folder and how to read each part, deciphering degrades into guessing by file extension, and every new artifact kind silently breaks every existing reader.**

BagIt describes itself as *"a filesystem convention, not a serialization format"*, which is this phase's own thesis in the standard's words. It is better than a hand-rolled manifest on three counts, each of which discharges a requirement of another phase for free:

| BagIt gives | Which requirement it discharges |
|---|---|
| The manifest **is** checksums, so validating a bag is re-hashing its payload | [Phase 2](phase2_content_store.md)'s verification mechanism, applied to the bag itself |
| `bag-info.txt` is the defined home for arbitrary bag metadata | Requirement 6 — the schema-version field has a specified home |
| Bags transfer as loose directory trees **or** serialized | Phase 7's object-storage sync |

**⚠ What the manifest does NOT give, so the third row above is not over-read:** a `manifest-sha256.txt` is regenerable by anyone who can write the bag. It proves integrity against **accident and transport corruption**; it proves nothing against a party with write access. Authenticity is a different property, and [Phase 7](phase7_s3_aggregation.md) § *Where a shared bucket would change things* is where it is addressed.

**⚠ And "a party with write access" is not only a Phase 7 problem — it exists from this phase onward, locally.** The root is `0700` and owned by the fleet user, and **every run this fleet dispatches executes as that same user with permissions bypassed.** So the append-only record is fully writable and deletable by the very processes it is a record of, and after [Phase 4](phase4_rebuild_is_a_test.md) it is the sole authority for the [`tracked/`](../../../tracked/) stores. **Append-only here is a convention the fleet keeps, not a property the filesystem enforces**, and this doc says so rather than letting "immutable" be read as a guarantee. What that buys is real — it defends against accident, against a partial write, and against the ordinary ways a record rots. What it does not defend against is a compromised or misbehaving run. **Whether that is accepted, or whether the emit path should write through a separate user or a write-once store, is a decision — and it is the local half of the same question [Phase 7](phase7_s3_aggregation.md) asks about a bucket.** It is named here so the local half is not assumed answered by the remote half.

**And the bag-level version is a summary, not the authority.** [Phase 3](phase3_the_emit_rule.md) puts `schema_version` on **every event**, and that is the value an upcaster reads. A bag can span a schema change, and an event aggregated to S3 travels away from its bag entirely — either case makes a per-bag version insufficient on its own.

**Do not invent a manifest format.** If BagIt turns out to be insufficient for some artifact kind, the finding is *what BagIt cannot express*, recorded here — not a replacement.

### Bag lifecycle — open, sealed, redacted, and incomplete

**A bag is not always complete, and pretending otherwise breaks two later phases.** RFC 8493 requires every file listed in a payload manifest to be present for a bag to be *complete*, so the naive reading of "a bag either validates or it does not" fails three times over: a run in flight has no finalized manifest; a **redaction** replaces a payload file with a marker, which would leave every redacted bag reporting missing files — indistinguishable from data loss, and turning [Phase 2](phase2_content_store.md)'s integrity signal into noise; and a run whose journal write failed has a bag that is genuinely missing something, which is the one case that must never look like either of the others.

Four states, and the validator distinguishes them:

| State | What it means | Manifest |
|---|---|---|
| **open** | the run is in flight, or died before sealing | not yet written; validation reports *open*, not *failed* |
| **sealed** | the run finished and the manifest was written | complete — every payload file present and matching |
| **redacted** | a payload file was replaced by a marker under the one stated exception to immutability (§ *Schema versioning* below) | **regenerated** over what remains, with a `bag-info.txt` record naming what was replaced and when |
| **incomplete** | a write into this bag **failed**, so something that should be here is not | regenerated if the bag was sealed, and the bag carries at least one gap event naming what was lost, when, and why |

**Only the first two are values of one field; the other two are independent flags, and the validator's output contract says so.** A redaction only ever applies to a bag that was sealed, and `incomplete` can accompany either — so the reported state is `lifecycle: open | sealed` plus `redacted: true|false` plus `incomplete: true|false`, **always all three**, rather than one label that hides the rest. Three consumers depend on that string ([Phase 4](phase4_rebuild_is_a_test.md)'s gap accounting, [Phase 5](phase5_snapshots_then_retention.md) r9, [Phase 7](phase7_s3_aggregation.md) r4), and a validator that printed `redacted` where `sealed` was also true would strand all three. Collapsing them is the failure mode worth naming: redaction and gapping both leave a bag with fewer intact files than its manifest once listed, and both regenerate the manifest, so a single field would make **a bag that lost data to a full disk indistinguishable from one a human deliberately redacted.** The first is a defect to investigate; the second is the system working, and it is the one sanctioned change to an otherwise-immutable record.

**Redaction regenerates the manifest, leaves a tombstone, and emits its own journal event.** That is what keeps a redacted bag honestly valid rather than quietly broken.

**⚠ There is no *partially deleted* state, and that is a consequence of [Phase 5](phase5_snapshots_then_retention.md)'s retention rule rather than an omission.** Retention removes **whole run folders**; it never trims a payload. A bag whose transcript had been rotated away while its authored output remained would be a run you can half-read, and half-readable reads as coverage — so that state is not in the table because nothing is allowed to produce it.

*(A crashed run leaving an `open` bag is the case the design test most cares about, so `open` is a first-class state and not an error. **`open` and `incomplete` are also different**: `open` means nobody has sealed this yet, which is normal; `incomplete` means a write was attempted and did not land, which never is.)*

**The rule this state serves belongs to [Phase 3](phase3_the_emit_rule.md)** — *a gap may exist; a silent gap may not.* This phase supplies the place that fact is recorded, because a bag's states have to be enumerated before anything writes into it. Phase 3 § *When the journal cannot be written* is the authoritative statement of when the state is set.

### The surface this replaces — `.claude/logs/`, and it is already a declared surface

**The CLI transcript is not new ground.** The per-run JSONL log under `.claude/logs/` is already a declared surface, in `scripts/helpers/measure/run_log.py` — it has a member event-type set, a `run_id` join key, a publish classification, a growth rule and three committed readers. In this component's taxonomy it holds **measurement samples**: numbers that decide nothing alone and become a decision only as a rate over many runs. Phase 1's payload table admits "the CLI transcript" and "execution facts", which is that surface's content.

**So requirement 7 must answer the question rather than leave it to whoever wires Phase 3**, and the two possible answers have very different costs:

- **The journal is the run log's new home.** Then the migration path for the existing archive, the fate of `run_log.py`'s declared surface, and its `PUBLISHABLE_FIELDS` classification all move into this component — and [`memory-model.md`](../../guide/memory-model.md) needs amending, which is a candidate for human review, not a dispatch's write.
- **The journal is a second surface with a stated seam.** Then two per-run stores hold duplicate transcripts under two event vocabularies, and the reason has to be worth that.

**Deciding it implicitly during Phase 3's wiring is the outcome this requirement exists to prevent**, because that is the one place the plan itself calls expensive to unwind. Note also that the run log is keyed **per repo checkout** while the journal is one root **per edge** — so requirement 7's payload table carries the originating repo/project as a first-class field regardless of which answer wins. A field absent from v1 events is absent forever, and without it nothing downstream can express *"this depends on which repo the run was in."*

#### THE ANSWER: absorption, and the seam closes in Phase 3

**The journal is the run log's new home.** The second option is rejected, and the reason is that it has no upside to weigh: two per-run stores holding duplicate transcripts under two event vocabularies costs two writers, two readers and two chances to disagree, and **there is no question the second copy answers.** The payload table above already admits the CLI transcript and the execution facts — that *is* `run_log.py`'s content — so "a second surface" would mean declaring the same bytes twice and then maintaining the difference.

Four consequences, stated so Phase 3 wires to a decision rather than making one:

1. **`run_log.py`'s declared surface is carried, not discarded.** Its three member event types (`parent_route`, `run_resources`, `convergence`), its `run_id` join key, its `PUBLISHABLE_FIELDS` classification and its growth rule become the journal's, versioned under `Event-Schema-Version`. The classification in particular has a home waiting for it: it is the per-row value in the payload table's classification column, one altitude up.
2. **The join key changes meaning and that is the migration's real content.** `run_log.py`'s `run_id` is minted inside `run_claude` — **per model invocation**, so a parent and its three children carry four different values and no single one addresses the run. The journal's `run_id` is minted once at the top. They are different identifiers wearing one name, which is exactly why this could not be settled by "point the writer somewhere else".
3. **The existing `.claude/logs/` archive is NOT migrated**, and this is a separate decision with its own reasoning rather than a consequence of the first. It is gitignored, so no clone, CI runner or worktree can re-derive it; it is a moving denominator (175 → 178 files inside one day); and by consequence 2 it has no identifier that addresses a *run*, so a migration would have to fabricate run-level bags out of child-level records. **Synthesising a record is the one thing a journal must never do.** The archive stays where it is, read by its three committed readers exactly as today, until it ages out.
4. **The [`memory-model.md`](../../guide/memory-model.md) amendment is SURFACED, not written** — it is a `docs/guide/` document under human review, and it already has a declared writer for entries of this kind: the roadmap's § *Standards-amendment candidates*, where this lands as an entry naming when it applies. A dispatch writing it directly is what [`standards-governance.md`](../../../config/rules/standards-governance.md) exists to prevent.

**Nothing changes in `.claude/logs/` in Phase 1.** This phase opens bags and writes no events, so both surfaces exist and only one is written to. The cut-over is Phase 3's, which is where emitters live; what this section removes is Phase 3's freedom to decide it by accident.

### Concurrent children write to their own subfolder

The event-sourcing literature warns that without a correct sequence number and a single writer per aggregate, events get reordered. This fleet fans out — the 2026-08-12 verify round dispatched two critics 21 seconds apart — so concurrent writers are real today, not hypothetical.

**Giving each child its own subfolder removes the contention entirely**, because no two writers share a file. Combined with `run_id` keying, a run's record is a tree of independently-written parts.

**⚠ The boundary, stated so the simplification is checked rather than assumed.** Subfolders solve concurrent writes *to the journal*. They do **not** establish a global order, and they do **not** help if two children mutate the same *external* store. Today that cannot happen — parallel children are read-only critics and a single analyst writes — **so the day a workflow gives two concurrent children write access to one store is the day this needs a sequence number.** Cheap now, unrecoverable in old data. That trigger belongs to whoever adds such a workflow; this phase's job is to name it.

### What goes in the journal, and what stays out

**THIS TABLE IS THE PAYLOAD SPEC (requirement 7) AND IT IS THE AUTHORITATIVE ONE.** No other document restates it; where another needs a row, it cites this section. A restated table is a copy, and a copy of a superseded row is how a correction fails to land.

**The `May leave this edge?` column is the classification slot**, and it has one more column than this phase has any use for on purpose — § *Why the payload spec carries a classification slot it does not yet fill* below is the argument. Every row gets a value; today every value is the same.

| Surface | What it is | In the journal? | Why — including why not | May leave this edge? |
|---|---|---|---|---|
| **Authored output** — PR body, comments, decisions, triage, candidate rows | what the run **wrote** | **Yes, verbatim** | No better durable store exists. GitHub comments are editable, deletable, unversioned and hosted by a service — **and they are where the reasoning lives** | shippable |
| **CLI transcript** — every tool call and result | **how the run got there** | **Yes.** Basic logging, and it is not optional | It is the only record of *why* a run did what it did, and it is what [Phase 4](phase4_rebuild_is_a_test.md) replays. It is also 99.2% of the bytes (below) and the one surface carrying unredacted credentials, which is why § *Schema versioning* designs a redaction path | shippable |
| **Execution facts** — cost, timing, resources, re-runs | what it took | **Yes** | Measurement samples: each decides nothing alone and becomes a decision only as a rate over many runs, so they are worthless unless kept across runs. This is `run_log.py`'s three declared event types (§ *The surface this replaces*) | shippable |
| **Originating repo/project** — worktree path, `origin` remote, HEAD commit | which checkout this run happened in | **Yes, as a first-class field** | The run log it supersedes is keyed **per repo checkout** while the journal is one root **per edge**, so without this nothing downstream can express *"this depends on which repo the run was in."* **A field absent from v1 events is absent forever** | shippable |
| **Code diffs** | already perfectly stored | **No** — commit SHA, fetch from git | git is versioned, content-addressed and complete. Storing a second copy adds bytes and a second thing that can disagree with the first | n/a — not stored |
| **Temporal history** | orchestration, with a retention TTL | **No** — the workflow emits what it needs at completion | **Excluded as a *source* only, and only because it expires.** Its identity scheme is bounded by retention and continue-as-new starts a fresh history: an execution log with a TTL, not a durable memory. Building analysis on it means building on a store that deletes itself on a schedule configured months earlier | n/a — not stored |

**The line is one question: does a better durable store already exist for this artifact type?** For code it does — git is versioned, content-addressed and complete, so the journal carries the SHA. For the prose a run writes into GitHub it emphatically does not: comments are editable, deletable, unversioned and hosted by a service, **and they are where the reasoning lives.**

**Only Temporal's store is excluded as a *source*, and only because it expires.** Its identity scheme is bounded by retention and continue-as-new starts a fresh history — an execution log with a TTL, not a durable memory. Building analysis on it means building on a store that deletes itself on a schedule configured months earlier. Everything the fleet itself produces goes in.

**The two halves have wildly different volumes, and that is what sizes the journal.** Measured on one `research_minor` cycle: **authored output 39,772 bytes; CLI transcript 4,823,628 bytes** — the authored record is **0.8%** of the total. At roughly 4.9 MB per complete run, [Phase 5](phase5_snapshots_then_retention.md)'s 1 GB budget holds a very large library of *whole* runs, which is what lets that phase delete run folders entire rather than trimming them.

### Why the payload spec carries a classification slot it does not yet fill

**Requirement 7's table gains one more column than this phase has any use for: what may leave this machine.** Every row gets a value.

**The reason is that a per-field answer has to be expressible before anyone wants one.** If the transcript is one opaque artifact in this table, the only answers available later are *ship the whole transcript* or *ship none of it* — and the answer that is actually wanted may well be *the results, not the command lines*. **A field absent from version-1 events is absent forever**, so the shape has to leave room even though the values are trivial today.

**They are trivial today because the storage arrangement is settled and short:** each edge has access to an S3 bucket — shared or its own — and uses it as it sees fit. Today there is one edge and the bucket holds its own data, so every row's value is *shippable*. What a *shared* bucket would require is [Phase 7](phase7_s3_aggregation.md)'s § *Where a shared bucket would change things*, and it is a design note there rather than a gate anywhere.

**This is the same argument [Phase 3](phase3_the_emit_rule.md) requirement 7 makes for the provenance class**, applied one layer down to the payload rather than to the event, and it lands here rather than in Phase 3 because **the payload spec is this phase's deliverable and not Phase 3's.**

### Why this is an activity and not a library — requirement 11

**A parent's first step resolves the root and opens the bag, as an activity the orchestrator invokes and records.** It is not a helper each workflow is asked to remember to call.

**As a library, the protocol is optional — and optional is how three controls in this fleet have already failed.** An observable shipped with no reader; a rule that governed three event types stated inside one function's docstring; a completion gate one runner had and another did not. Each was correct as written and each was skippable, and each was skipped. **A rule written in prose has not once prevented a write path from being added without its emit.**

**⚠ AND AN ACTIVITY BOUNDARY DOES NOT, BY ITSELF, MAKE THE CALL HAPPEN.** Nothing in an orchestrator forces a workflow to invoke a particular activity first — a workflow that omits the call simply omits it. So *"put the code in the activities layer"* delivers tidiness, not the guarantee this requirement is sold on, and requirement 9's refuse-to-start cannot supply it either: **r9 fires only once bag-open has already been invoked.** A workflow that never calls it never reaches r9.

**The mechanism that actually delivers it is an enumerating test, and this repo already ships the exemplar.** `scripts/workflows/temporal/tests/unit/test_preflight.py` holds `test_every_entrypoint_actually_calls_preflight`, which discovers every entrypoint under `scripts/workflows/temporal/scripts/` and asserts each one calls `preflight(`. **Requirement 11's done-state is the same shape:** a test that discovers every parent and fails when one does not open a bag — so a parent added without the call goes red on the merge path rather than producing a journal-less run.

Made structural that way, the failure mode inverts: a workflow that does not open a bag does not get a run with an absent journal, it gets **a red test**; and a workflow that opens one against an unresolvable root gets a run that **does not start** (requirement 9). Those are two different guards for two different failures, and neither substitutes for the other.

**⚠ What this does NOT cover, so the guard is not over-read.** It makes the journal structurally *present*; it says nothing about whether any individual write is *emitted*. A parent that opens a bag and then writes to a store through a path nobody wrapped still produces a gap, and neither the activity boundary nor the enumerating test can see that — **[Phase 4](phase4_rebuild_is_a_test.md)'s rebuild test is the guard for that class.** It also does not reach model-issued writes at all: when the child itself runs `gh pr comment`, there is no fleet call site to wrap, and that half is [Phase 10](phase10_the_model_issued_harvest.md)'s post-exit harvest — split out of [Phase 3](phase3_the_emit_rule.md) on 2026-08-28, so a reader briefed from here builds it once and in the right phase. **And an enumerating test is only as good as its discovery predicate** — a parent that lives outside the directory the test sweeps is invisible to it, which is why the sweep's scope is stated in the test's own failure message.

**What an activity *is* here is a boundary the [Temporal Integration](../temporal-integration/temporal-integration.md) component also owns.** This phase states what it needs — a step that runs before any child and whose failure stops the run — rather than specifying the mechanism, and it is explicit above about which half of that only a worker can supply. Where the two designs meet, the shape is settled once and the other cites it ([roadmap § *Constraints that run BOTH ways*](roadmap.md#constraints-that-run-both-ways-with-the-temporal-port)).

**⚠ And making the journal mandatory has a cost that has to be named: a full disk becomes a fleet-wide stop.** Once Phase 3 lands, every run needs a resolvable, writable root — so a runaway transcript, or a budget an operator lowers, stops *every* run including the one you would use to diagnose it. It is reachable without an attacker. **Two things bound it, and both are stated rather than assumed:** [Phase 5](phase5_snapshots_then_retention.md)'s requirements 2–9 are labelled `(ungated)` and should land with or before Phase 3 rather than waiting for the server that only requirement 1 needs; and requirement 9's refusal message **names the resolved path and the exact failing property**, so the recovery path exists without a working journal.

### Why the root is configurable, and where the defaults come from

[`XDG_STATE_HOME`](https://specifications.freedesktop.org/basedir/latest/) (default `~/.local/state`) is defined for state that persists between restarts, explicitly including logs, and is specified as *"analogous to `/var/lib`"*. That is precisely this journal.

| Deployment | Root |
|---|---|
| User-run, as today | `$XDG_STATE_HOME/<app>/` → `~/.local/state/<app>/` |
| systemd worker (the VM plan) | `/var/lib/<app>/` |
| A machine where the fleet runs inside a Docker container (e.g. a Home Assistant add-on) | the container's mapped persistent volume |

**⚠ Requirement 9 also refuses a root inside a git working tree.** The root is a config value, and every build run this fleet dispatches edits repo config routinely — so a run can redirect the journal into its own worktree, at which point verbatim transcripts land somewhere that gets committed and pushed. *"It does not belong in the repo"* is stated below as intent; requirement 9 makes it a resolution rule, which matters more now that the root is resolved by an activity on **every** run.

**⚠ Requirement 9: the mode is part of the contract, because two of those three shapes are multi-user.** The root will hold verbatim transcripts including every Bash command line the fleet ran. Under a default umask it is world-readable, so on the systemd-worker VM shape this plan explicitly targets, any local account reads every run. The contract: **the root is created `0700` and payload files `0600`, with the mode set at creation rather than chmod-after**; and resolution **fails** if the resolved root is group- or world-writable, is a symlink whose target lies outside the configured path, or **resolves inside any git working tree**. This doc already refuses a silent home-directory fallback — this is the same discipline applied to the directory's properties rather than to its location.

**And "fails" means the run does not start** (requirement 9). This is the earliest and cheapest of the three write-failure cases [Phase 3](phase3_the_emit_rule.md) rules on: the root is resolved once, before any work happens, so a machine with a missing path, a read-only mount or a wrong-mode directory finds out immediately and costs nothing. A run that starts anyway and discovers its journal is unwritable an hour in has already spent the hour, and the record of what it spent it on is the thing that cannot be written.

`/opt` is for application binaries, not state; `/lib` is system libraries. Neither is right. **And it does not belong in the repo** — it is state rather than source, and gitignoring it merely hides it somewhere that is cloned and deleted along with the repo, which is the current failure: `.claude/logs/` is gitignored, so 262 MB of run history survives the run but not the machine and is invisible to every consumer that reads the repo.

**⚠ Requirement 1 exists because the edge is not defined yet.** Home-directory placement is fine for the edge we have, because Claude Code itself requires a user context. An edge that is not a full Linux environment — HAOS is the live example — may have **no user account**, and may need a sidecar to run at all. **The protocol must not depend on a home directory; the root is one config value.** That keeps the question open without blocking this phase, which matters because the second edge is not far off. See the roadmap's § *Open inputs*, item 1.

### No database — a decision, with its revisit trigger

`state_passing` §4.3.3's format table has one empty row: *queries over accumulated history*. The obvious reflex is to fill it with SQLite, and OpenClaw ships exactly that (`memory.sqlite` + `sqlite-vec`) beside its markdown facts.

**We are not, and this is a decision rather than an omission.** A per-run folder tree with a checksum manifest answers the questions we actually have. **A database would be one more thing the journal rebuilds**, and [Phase 4](phase4_rebuild_is_a_test.md) makes that cheap — so this is a **future build opportunity with no refactor cost**: if a query is ever wanted that the tree genuinely cannot serve, it is install-and-import, and nothing in this component has to change to allow it.

**Revisit trigger: a real query that the tree cannot serve.** Not a feeling that a record ought to live in a database. **The first such query is already scheduled and it is worth naming here** — [Phase 6](phase6_cpi_reads_the_journal.md)'s CPI sweep is a cross-run query over accumulated history, which is precisely the empty row above. Its measured wall-clock against journal size is this decision's first real test, and Phase 6 carries that measurement as a requirement so the trigger fires on evidence rather than as a mid-build surprise.

**OpenClaw's documented failure is the warning to carry:** its memory *"lives in files that must be explicitly loaded, which means continuity depends entirely on what gets re-read at startup"*, and summarised context is lossy. **A journal nothing loads is our 262 MB.** This phase builds the store; [Phase 6](phase6_cpi_reads_the_journal.md) builds the reader, and the component is not done without it.

### Schema versioning — the known cost, decided on day one

A journal written under v1 must still replay under v3, forever. Every event-sourced system meets this, and it is brutal to retrofit.

**The settled answer: version every event, never mutate a written one, upcast on read.** `bag-info.txt` is where the bag-level version lives, which is requirement 6. **The detailed mechanism is open** — see the roadmap's § *Open inputs*, item 2 — but the rule is not, and a v1 event written without a version field is unrecoverable, which is why this lands in Phase 1 rather than waiting for the mechanism.

**⚠ "Never mutate" needs ONE stated exception, and it must be designed now rather than invented during an incident.**

Three of this component's rules compose into a trap: the transcript goes in and *"it is not optional"*; authored content goes in **verbatim**; and no written event is ever mutated. The fleet runs `claude -p` with permissions bypassed, so a transcript carries the literal input of every Bash call. **The first time a token, a tokenised remote URL, or an API error body carrying a bearer credential lands in a transcript, it is sealed into a manifest-covered payload file** — and deleting it invalidates the manifest and turns [Phase 4](phase4_rebuild_is_a_test.md)'s test red. The only remaining move is *rotate the credential and accept a plaintext copy that survives until the budget rotates that run out*, which [Phase 7](phase7_s3_aggregation.md) may also have shipped to storage by then.

**[Phase 5](phase5_snapshots_then_retention.md)'s budget is not the answer to this, and saying so is the point.** A secret eventually rotating out with its run folder is not a control — it is a delay of unknown length, since the budget is a size and not an age. The controls are the two below.

**This is the one place the component is strictly weaker than what exists today.** `.claude/logs/*.jsonl` is equally unredacted — but it is machine-local and `rm`-able with no consequence. After Phase 4, the journal is not.

**So requirement 6's versioning rule defines a REDACTION event class as the stated exception:** a redaction is a **new appended event that supersedes**, the payload file is replaced by a marker, the manifest is regenerated, and the regeneration is itself a recorded event.

**⚠ A redaction must stay separately auditable from every other reason a bag's payload differs from its original manifest.** It shares its mechanism with nothing else that is permitted — retention deletes whole folders and never trims one — but it shares its *shape* with a gap: both leave a bag whose payload no longer matches what was first written, and both regenerate the manifest. Collapsing them makes **a bag a human deliberately redacted indistinguishable from one that lost bytes to a disk-full error.** That is the same argument this doc makes two sections up for keeping `incomplete` separate, and it matters more here: a redaction is the one sanctioned change to an otherwise-immutable record, so it is the state most in need of being separately auditable. **The tombstone names what was replaced and why, the validator reports `redacted` distinctly from `incomplete`, and redaction events are enumerable on their own.** **Nothing is ever silently edited; the record stays complete about the *fact* of the redaction.** The complementary control — filtering at capture time, before the payload is sealed — is [Phase 3](phase3_the_emit_rule.md)'s, because that is where capture happens. This repo already has a tested precedent for the read-side half (`scripts/workflows/temporal/modules/assistant/review_pr/exit_record.py`, which drops tool input at read time *"so there is no copy to leak"*), and that control guards a **display** surface; the journal is a durable one and needs both halves.

---

## What was built, and where it lives

| Piece | Where |
|---|---|
| Root resolution and its refusals | `scripts/workflows/temporal/modules/journal/root.py` |
| The bag: layout, manifest, lifecycle, redaction, gap records | `scripts/workflows/temporal/modules/journal/bag.py` |
| The validator | `scripts/workflows/temporal/modules/journal/validate.py` |
| The activity a run invokes first | `scripts/workflows/temporal/modules/journal/journal_activities.py` |
| The operator CLI | `scripts/workflows/temporal/scripts/validate_bag.py` |
| The root and deployment shape | `config.yaml` § `journal:` |
| The enumerating sweep (r11's actual guarantee) | `scripts/workflows/temporal/tests/unit/test_every_parent_opens_a_run_bag.py` |

### Two boundaries of the built guarantee, stated because every other one here is

- **`--dry-run` is a deliberate exemption.** Eight of the 12 entrypoints return from their dry-run branch before reaching bag-open, so on that path the call is present and does not execute. *(The other four have no `--dry-run` at all. This said EIGHT until the figure was derived rather than restated — see [`test_journal_prose_figures_are_DERIVED.py`](../../../scripts/workflows/temporal/tests/unit/test_journal_prose_figures_are_DERIVED.py), which now fails when a count in this document contradicts the tree.)* That is intended — a dry run states *"nothing invoked, nothing posted"*, and creating a directory would falsify it and fill the journal with empty bags from previews. No run happens on that path, so no run lacks a bag.
- **The ordering check reaches 9 of the 12 entrypoints.** It can see a `worktree_add` call and a workflow handoff called by name; `run_research.py`, `run_research_minor.py` and `run_review_pr.py` reach their workflow through an aliased module that also carries pure prompt-assembly functions legitimately running before the bag, so treating any call on it as a side effect would fail those three falsely. The set it does not cover is **pinned in the test**, so an entrypoint dropping out of coverage fails rather than passing vacuously. Presence is still checked for all 12.

### Redaction containment — the one sanctioned mutation needed the strictest guard and initially had the weakest

`redact()` composes a caller-supplied relative path onto a trusted bag path, which is the same class of input § *Why the root is configurable* treats adversarially one layer up — and it was the one input in the package that could not be defended by slugification, because it must preserve internal `/` to address a nested payload file. Two escapes followed and both were demonstrated against a real bag rather than reasoned about: a `..` walk (`data/../../x`) passed a first-segment check and overwrote a file beside the bag in the journal root, and a symlink under `data/` passed `is_file()`, was hashed into the manifest as though it were payload, and was followed on redaction so the write landed on the link's target.

Both are closed the way the root's containment is: normalise, resolve, then prove the result is still inside the directory it must be inside — plus a symlink refusal on every path segment, `O_NOFOLLOW` on the write, and **a symlink under `data/` reported by the validator as a structural failure**. The general rule this leaves behind: *a bag holds bytes, not pointers to bytes that live outside it* — a pointer does not survive the directory-tree transfer [Phase 7](phase7_s3_aggregation.md) depends on.

### And the rule stayed prose, so it leaked twice more — which is why it is now a function and a sweep

**The two escapes above were fixed as two instances. The next review pass found two more of the same shape**, which is the evidence that enumerating instances does not converge here:

- **The validator's manifest join.** `manifest-sha256.txt` is untrusted input — a file on disk this module did not necessarily write — and `validate_bag` composed its second field straight onto the bag's path. Demonstrated: a bag with an **empty `data/`** and the single line `<sha256 of /etc/hostname>  ../../../../etc/hostname` reported **`result: PASS`**. Every check agreed and every check was wrong for the same reason: `missing` saw a file that existed, `mismatched` saw a checksum that matched, and `unlisted` compared against an empty set. An absolute entry is worse — `Path("/j/run") / "/etc/hostname"` *discards* the base rather than escaping it. **This is requirement 5's own deliverable certifying a false statement**, on the tool an operator reaches for when the journal is what has gone wrong.
- **The tag-label parameter.** The pass that closed value-forging in `_refuse_folded_value` wrote the fix against the parameter that had been exploited. The *label* is composed onto the same line, so `open_bag(info={"X\nJournal-Incomplete: true": "y"})` forged the flag identically. Every fleet call site passes a literal, which is exactly why nothing caught it.

**Four instances, one shape: an externally-supplied string composed onto a trusted base.** Three of the four had been fixed correctly and independently, in three places, with no shared name — which is this component's own thesis (*a rule written in prose has not once prevented a write path being added without its emit*) coming true about the component. The remedy is the one r11 already argues for, applied to containment:

- **One named rule** — `bag.contained_relpath`, called by `redact()` and by the manifest parser.
- **A sweep that fails on the next one** — `tests/unit/test_journal_containment.py` walks every `base / x` composition in the package and refuses any whose right operand is neither a module constant nor `contained_relpath(...)`, unless a row declares *why that value cannot escape*. **Adding a join is what fails**, not remembering to test one.

**The two halves catch different things, measured rather than assumed.** Reverting the manifest guard leaves the sweep GREEN — the declaration is still there, it is merely no longer true — and only the behavioural battery fails. Reverting `redact()`'s guard leaves the battery green (the realpath check still catches those inputs) and only the sweep fails. Neither substitutes for the other, and a fifth escape needs both to be wrong at once.

*(Fixing normalisation also fixed a false failure in the other direction: a foreign bag using the `sha256sum` convention `./data/x.txt` had been reporting its only payload file as both present-and-matching **and** `unlisted` — `ok=false` on a healthy bag, contradicting the parser's own stated tolerance for other BagIt implementations.)*

### Making bag-open structural made the TEST SUITE a dispatch, and nothing could go red about it

**Found by running the suite and then looking at the operator's home directory** — not by an assertion, because every assertion passed the whole time. Five unit modules drive an entrypoint's `main()` to test its preconditions; every entrypoint now opens a bag; nothing stood between the two. **Twenty-four real bags accumulated under `~/.local/state/claude-dot-files/journal/` in a single day**, one per `pytest` invocation.

Three consequences, and the third is the one that matters most to this component:

1. Durable state written outside `tmp_path`, which the Testing Standard's fixture-placement rule forbids for exactly the reason it survives the run.
2. [Phase 5](phase5_snapshots_then_retention.md)'s budget is measured over the whole root, so running the tests spends an operator's retention budget.
3. **The integration tier was grading the unit suite's litter.** `test_a_real_bag_validates.py` reads whatever is under the real root and validates it *as a bag a real dispatch produced*. Its evidence base was mostly produced by the suite running two directories away — a tier that reads shared machine state cannot tell who wrote it.

**Fixed as a property rather than as five edits:** an autouse session fixture in `tests/conftest.py` points `CONFIG_PATH` at a generated config naming a temporary root — **by config and not by `XDG_STATE_HOME`, because a configured root wins over every default**, so the environment route would protect only a machine whose `journal.root:` is empty. The check is separate from the remedy and keyed on the observable — *did the real root change* — rather than on the mechanism, since the mechanism varied every time this package leaked something. It discovers the entrypoint-driving modules by AST, runs them in a subprocess, and diffs the real root before and after.

*(This is the third distinct thing in this phase that was correct-as-written, invisible to every test, and found only by executing something and looking at the result. The other two are the reseal appending a single-valued label, and the validator reporting `PASS` over a manifest naming a file outside the bag.)*

### What requirement 9 does NOT check, and why that is a decision rather than a gap

**The root's own properties are checked; its ANCESTORS' are not.** A group- or world-writable non-sticky directory *above* the root lets a different local account rename the root aside, at which point the next run recreates it, every check passes, and the fleet silently starts a fresh empty journal with the prior record gone.

**It is not covered, deliberately, and the reasoning is r9's own scope.** Requirement 9 enumerates what the resolved root must be — absolute, `0700`, owned by this user, not a symlink, not inside a git working tree, writable — and both shipped defaults have safe ancestors (`/var/lib` and `~/.local/state` are neither group- nor world-writable). Reaching an unsafe ancestor requires an operator setting `journal.root:` under a shared directory. **Adding an unrequested refusal is not free here:** § *Why this is an activity* already names the cost that every run now hard-depends on this resolution succeeding, so a new way for it to fail stops the whole fleet including the run you would diagnose with.

**The threat model this sits inside is already stated above** — *append-only here is a convention the fleet keeps, not a property the filesystem enforces*, and every run executes as the user that owns the root with permissions bypassed. An adversary with a local account and write on an ancestor is a machine misconfiguration one layer below what this component can repair. **Named here rather than left silent, because the doc describing the multi-user hazard while the code quietly declined half of it is the shape worth avoiding.** If a deployment ever puts the root under a shared parent, this is the requirement that grows a clause.

---

## Implementation checklist

- [x] Write the root-resolution contract: config value first, documented default per deployment shape, explicit failure when neither resolves — **no silent fallback to a home directory** — plus requirement 9's mode rules (`0700`/`0600` at creation; refuse a group- or world-writable root, a symlink pointing outside the configured path, or a root inside a git working tree), **with the refusal naming the resolved path and the failing property**
- [x] Write the run-folder layout: `<root>/<run_id>/` as a BagIt bag, with one payload subfolder per child
- [x] Specify `bag-info.txt` contents including the schema-version field, and write the version/upcast rule and the redaction-event exception beside it
- [x] Specify `manifest-sha256.txt` generation over the payload, and manifest **regeneration** for the `redacted` state
- [x] Specify how `incomplete` is recorded on a bag, and confirm it is independent of the other three states rather than a fourth value of one field
- [x] Write the payload spec table into this doc's § *What goes in the journal* as the authoritative version, with the originating repo/project as a field and a classification slot per row, and confirm no other doc restates it
- [x] **Answer § *The surface this replaces*** — journal-absorbs-run-log or two-surfaces-with-a-seam — and record the reasoning; if it is absorption, surface the [`memory-model.md`](../../guide/memory-model.md) amendment as a candidate rather than writing it
- [x] **Build bag-open as an activity** the parent invokes as its first step, **and the enumerating test that discovers every parent and fails when one does not call it** — demonstrated against a deliberately non-conforming parent (requirement 11)
- [x] Build the validator: re-hash the payload against the manifest, report pass/fail, distinguish *missing file* from *checksum mismatch*, and always report all three fields — `lifecycle: open|sealed`, `redacted`, `incomplete` — rather than one label that hides the others
- [x] Add the validator to [`testing/run-all.sh`](../../../testing/run-all.sh) with a `tests/` directory per the [Testing Standard](../../standards/testing/README.md) — `unit/` for layout, manifest generation and every combination of the two lifecycle values with the two flags (including a bag that is `sealed`, `redacted` **and** `incomplete`), `integration/` for a real bag produced by a real dispatch
- [x] Demonstrate two concurrent writers producing one valid bag with no collision, as a **structural test over the layout API**. The live fan-out demonstration belongs to [Phase 3](phase3_the_emit_rule.md), because nothing emits until then
- [x] Record the measured size of one real run's bag, with its denominator, in § *Measurement* below

---

## Measurement

*(Every figure is produced by a command run against the tree and pasted with the command that produced it — a restated figure is a copy, and a copy of a superseded figure is how a correction fails to land.)*

### What one real bag costs, measured 2026-08-16

**The bag is produced by a real entrypoint's inputs**, not constructed by a test: `run_triage_candidates`'s own `open_run_bag` arguments, with the run stopped before its first side effect. No model was dispatched and no worktree was cut. The harness is eight lines and is quoted in the PR that added this section.

**Measured against a temporary root rather than the default one, and that is a correction.** The first version of this measurement wrote its bag into `~/.local/state/claude-dot-files/journal/` — which is how the suite-pollution defect above went unnoticed for a pass. A bag's byte cost does not depend on where its root is, so nothing is lost by measuring in a sandbox, and a measurement that litters the thing it measures is a measurement that changes its own denominator.

```
$ du -sb /tmp/tmpixqez8jh/journal/0c4a0aa4*/
523

$ find /tmp/tmpixqez8jh/journal/0c4a0aa4*/ -type f -printf '%s\t%P\n'
469     bag-info.txt
54      bagit.txt

$ du -sh /tmp/tmpixqez8jh/journal/0c4a0aa4*/
16K
```

| Figure | Value | What it is |
|---|---|---|
| One opened bag, apparent bytes | **523** | `bagit.txt` 54 + `bag-info.txt` 469. The **per-run floor** — the whole cost of the protocol before anything emits |
| Same bag, on-disk | **16 KiB** | three directories at one 4 KiB block each, plus the two tag files. The floor an operator's `du` will report |
| The floor as a share of one complete run | **0.011%** | 523 ÷ 4,863,400 (the two synthesis baselines below, summed) |
| Runs per [Phase 5](phase5_snapshots_then_retention.md) 1 GB budget, at the projected complete size | **≈205** | 1,000,000,000 ÷ 4,863,400. **A projection, not a measurement** — nothing emits until [Phase 3](phase3_the_emit_rule.md), so the payload half is the synthesis figure and not something this phase weighed |

**⚠ This supersedes an earlier figure of 496 bytes and the reason is substantive, not a re-run.** That bag carried `Journal-Worktree: -`, because the field was an optional argument nine of eleven entrypoints omitted — so nine of eleven runs would have recorded no worktree identity, permanently, under this doc's own rule that *a field absent from v1 events is absent forever*. The argument is now required and all eleven pass one; the floor grew by the 27 bytes of a real worktree name. **The old number is not re-stated anywhere** — it measured a bag this code no longer produces.

**⚠ The last row is the only one here that is not measured, and it is labelled that way deliberately.** The first three are `du` against a bag that exists; the fourth multiplies a real denominator by a projected numerator. Phase 3 is where it becomes a measurement, and the figure it produces supersedes this row rather than joining it.

**What the floor buys, stated because 523 bytes reads like nothing:** it is what makes a run's record *addressable* — an operator with a `run_id` has a folder, and a crashed run leaves an `open` bag rather than no evidence at all. The whole of [Phase 4](phase4_rebuild_is_a_test.md)'s rebuild stands on that folder existing.

### The baselines this phase is measured against

Both from the synthesis and both re-derivable:

| Figure | Value | Source |
|---|---|---|
| Authored output, one `research_minor` cycle | 39,772 bytes | synthesis §2, measured 2026-08-12 |
| CLI transcript, same cycle | 4,823,628 bytes | synthesis §12, same measurement |
| Current run-log archive | 175 files / 262 MB / 125 days / **zero** pruning code | `state_passing` §4.4, main checkout 2026-08-12 |

**⚠ The third row is a timestamped lower bound, not a fact.** `state_passing` §4.4 enumerated it five times in one day and got 175 → 178 files and 262 → 265 MB, because there is one file per dispatch and no pruning code. It is also gitignored, so no clone, CI runner or worktree can re-derive it. **What is stable is the shape** — 175+ files, 260+ MB, a 125-day span, zero pruning code, zero bytes in git — and any requirement here that quotes the number rather than the shape is quoting something that has already changed.

---

## Notes and open items

- **This phase writes no emitters.** If it finds itself specifying *what* a run writes rather than *where it lands and how it is read*, that is [Phase 3](phase3_the_emit_rule.md)'s scope and belongs there.
- **The payload spec's basis is the rebuild requirement, stated plainly rather than deferred.** The spec is written against [Phase 4](phase4_rebuild_is_a_test.md)'s test: **the journal must carry enough to *regenerate* a store, not merely enough to describe a run.** That is the bar, it is checkable, and it is what decides whether a candidate field belongs in the table. **What it does NOT decide** is presentation — how a reader is meant to *browse* the record is a separate question this spec does not answer and does not need to.
