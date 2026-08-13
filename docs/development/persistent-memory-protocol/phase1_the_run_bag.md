# Phase 1 — The journal root and the run bag

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** none — unblocked today

Stands up the container everything else writes into. Nothing emits yet; the outcome of this phase is **a folder on disk that a validator says is a well-formed run record**.

It is first because the shape is the expensive thing to get wrong. Once three phases are emitting into a tree, changing how that tree is keyed or manifested means rewriting history that was supposed to be immutable — and under [§2 of the synthesis](research/synthesis.md) the journal is the only thing that can rebuild a store, so a migration of the journal is a migration of everything.

---

## Requirements for completion

1. **The root is a config value, and nothing depends on a home directory.** One documented default per deployment shape. The reason this is a requirement rather than a convenience is in § *Why the root is configurable* below.
2. **A run's record is one folder keyed by `run_id`.** Never by path. Never by API key.
3. **Concurrent children write to their own subfolder** inside the run folder, so no two writers ever share a file.
4. **The folder is a valid BagIt bag** per [RFC 8493](https://www.rfc-editor.org/rfc/rfc8493.html) — a `data/` payload directory, a `manifest-sha256.txt` listing every payload file with its checksum, and a `bagit.txt` declaring version and encoding.
5. **A validator re-hashes the payload and reports pass/fail**, and it is wired into the test suite.
6. **`bagit.txt` carries the event schema version**, and the versioning rule is written down beside it.
7. **The payload spec is stated as a table with a reason per row** — what goes in the journal, what stays out, and why for each exclusion.
8. **No database is recorded as a decision with a revisit trigger**, not as an omission.

---

## Dependencies

**None.** This phase depends on nothing built or unbuilt. It is deliberately the one phase in this component with no upstream gate, so the container exists before anything needs it.

It is depended on by every other phase in the component.

---

## What this phase decides, and the reasoning behind each

### One location, a folder per run, many formats

The journal is **one root location per edge**, with subfolders and files as needed. Each artifact keeps the format that suits it — the transcript stays JSONL, authored markdown stays markdown, execution facts are typed JSON, code is a SHA. **The protocol is what knows how to read each kind.**

This is not a filing convention. It is what makes three later things cheap:

- **It generalises "two formats."** [`state_passing`](research/raw/state_passing_between_workflow_children.md) §4.3.2 found no single format serves humans and machines equally well and that mature systems do not try. There are as many formats as artifact kinds; **the container is what has to be single, not the encoding.**
- **It makes Phase 7 trivial.** Syncing a directory tree to object storage is a solved, boring operation. Syncing "a database plus some files plus some GitHub state" is not.
- **It makes [Phase 4](phase4_rebuild_is_a_test.md)'s rebuild test tractable.** Replay operates on one run's folder, in order, rather than on a query across a shared store.
- **It gives [Phase 5](roadmap.md#phase-5--snapshots-then-retention-gated-temporal-server)'s split retention a natural seam.** Prune the transcript *inside* a run folder and keep the rest — no record is destroyed, only its most expensive part.

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
| `bagit.txt` declares the version | Requirement 6 — the schema-version field has a specified home |
| Bags transfer as loose directory trees **or** serialized | Phase 7's object-storage sync |

**Do not invent a manifest format.** If BagIt turns out to be insufficient for some artifact kind, the finding is *what BagIt cannot express*, recorded here — not a replacement.

### Concurrent children write to their own subfolder

The event-sourcing literature warns that without a correct sequence number and a single writer per aggregate, events get reordered. This fleet fans out — the 2026-08-12 verify round dispatched two critics 21 seconds apart — so concurrent writers are real today, not hypothetical.

**Giving each child its own subfolder removes the contention entirely**, because no two writers share a file. Combined with `run_id` keying, a run's record is a tree of independently-written parts.

**⚠ The boundary, stated so the simplification is checked rather than assumed.** Subfolders solve concurrent writes *to the journal*. They do **not** establish a global order, and they do **not** help if two children mutate the same *external* store. Today that cannot happen — parallel children are read-only critics and a single analyst writes — **so the day a workflow gives two concurrent children write access to one store is the day this needs a sequence number.** Cheap now, unrecoverable in old data. That trigger belongs to whoever adds such a workflow; this phase's job is to name it.

### What goes in the journal, and what stays out

| Surface | What it is | In the journal? |
|---|---|---|
| **Authored output** — PR body, comments, decisions, triage, candidate rows | what the run **wrote** | **Yes, verbatim** |
| **CLI transcript** — every tool call and result | **how the run got there** | **Yes.** Basic logging, and it is not optional |
| **Execution facts** — cost, timing, resources, re-runs | what it took | **Yes** |
| **Code diffs** | already perfectly stored | **No** — commit SHA, fetch from git |
| **Temporal history** | orchestration, with a retention TTL | **No** — the workflow emits what it needs at completion |

**The line is one question: does a better durable store already exist for this artifact type?** For code it does — git is versioned, content-addressed and complete, so the journal carries the SHA. For the prose a run writes into GitHub it emphatically does not: comments are editable, deletable, unversioned and hosted by a service, **and they are where the reasoning lives.**

**Only Temporal's store is excluded as a *source*, and only because it expires.** Its identity scheme is bounded by retention and continue-as-new starts a fresh history — an execution log with a TTL, not a durable memory. Building analysis on it means building on a store that deletes itself on a schedule configured months earlier. Everything the fleet itself produces goes in.

**The two halves have wildly different volumes, and that is the useful part.** Measured on one `research_minor` cycle: **authored output 39,772 bytes; CLI transcript 4,823,628 bytes** — the authored record is **0.8%** of the total. That split is what [Phase 5](roadmap.md#phase-5--snapshots-then-retention-gated-temporal-server) turns into two retention rules, and it is why *"every question starts in the journal"* can stay true forever for the half that answers questions.

### Why the root is configurable, and where the defaults come from

[`XDG_STATE_HOME`](https://specifications.freedesktop.org/basedir/latest/) (default `~/.local/state`) is defined for state that persists between restarts, explicitly including logs, and is specified as *"analogous to `/var/lib`"*. That is precisely this journal.

| Deployment | Root |
|---|---|
| User-run, as today | `$XDG_STATE_HOME/<app>/` → `~/.local/state/<app>/` |
| systemd worker (the VM plan) | `/var/lib/<app>/` |
| Container edge (e.g. a Home Assistant add-on) | the add-on's mapped persistent volume |

`/opt` is for application binaries, not state; `/lib` is system libraries. Neither is right. **And it does not belong in the repo** — it is state rather than source, and gitignoring it merely hides it somewhere that is cloned and deleted along with the repo, which is the current failure: `.claude/logs/` is gitignored, so 262 MB of run history survives the run but not the machine and is invisible to every consumer that reads the repo.

**⚠ Requirement 1 exists because the edge is not defined yet.** Home-directory placement is fine for the edge we have, because Claude Code itself requires a user context. An edge that is not a full Linux environment — HAOS is the live example — may have **no user account**, and may need a sidecar to run at all. **The protocol must not depend on a home directory; the root is one config value.** That keeps the question open without blocking this phase, which matters because the second edge is not far off. See the roadmap's § *Open inputs*, item 2.

### No database — a decision, with its revisit trigger

`state_passing` §4.3.1's format table has one empty row: *queries over accumulated history*. The obvious reflex is to fill it with SQLite, and OpenClaw ships exactly that (`memory.sqlite` + `sqlite-vec`) beside its markdown facts.

**We are not, and this is a decision rather than an omission.** A per-run folder tree with a checksum manifest answers the questions we actually have. **A database would be a projection**, and [Phase 4](phase4_rebuild_is_a_test.md) makes every projection rebuildable from the journal — so this is a **future build opportunity with no refactor cost**: if a query is ever wanted that the tree genuinely cannot serve, it is install-and-import, and nothing in this component has to change to allow it.

**Revisit trigger: a real query that the tree cannot serve.** Not a feeling that a record ought to live in a database.

**OpenClaw's documented failure is the warning to carry:** its memory *"lives in files that must be explicitly loaded, which means continuity depends entirely on what gets re-read at startup"*, and summarised context is lossy. **A journal nothing loads is our 262 MB.** This phase builds the store; [Phase 6](roadmap.md#phase-6--the-poller-and-cpi-on-edge1-gated-phase-5) builds the reader, and the component is not done without it.

### Schema versioning — the known cost, decided on day one

A journal written under v1 must still replay under v3, forever. Every event-sourced system meets this, and it is brutal to retrofit.

**The settled answer: version every event, never mutate a written one, upcast on read.** `bagit.txt` is where the version lives, which is requirement 6. **The detailed mechanism is open** — see the roadmap's § *Open inputs*, item 4 — but the rule is not, and a v1 event written without a version field is unrecoverable, which is why this lands in Phase 1 rather than waiting for the mechanism.

---

## Implementation checklist

- [ ] Write the root-resolution contract: config value first, documented default per deployment shape, explicit failure when neither resolves — **no silent fallback to a home directory**
- [ ] Write the run-folder layout: `<root>/<run_id>/` as a BagIt bag, with one payload subfolder per child
- [ ] Specify `bagit.txt` contents including the schema-version field, and write the version/upcast rule beside it
- [ ] Specify `manifest-sha256.txt` generation over the payload
- [ ] Write the payload spec table into this doc's § *What goes in the journal* as the authoritative version, and confirm no other doc restates it
- [ ] Build the validator: re-hash the payload against the manifest, report pass/fail, distinguish *missing file* from *checksum mismatch*
- [ ] Add the validator to [`testing/run-all.sh`](../../../testing/run-all.sh) with a `tests/` directory per the [Testing Standard](../../standards/testing/README.md) — `unit/` for layout and manifest generation, `integration/` for a real bag produced by a real dispatch
- [ ] Demonstrate two concurrent children producing one valid bag with no collision — this is requirement 3's evidence and it must come from a real fan-out, not a synthetic one
- [ ] Record the measured size of one real run's bag, with its denominator, in § *Measurement* below

---

## Measurement

*(Populated when the phase runs. Every figure is produced by a command run against the tree and pasted with the command that produced it — a restated figure is a copy, and a copy of a superseded figure is how a correction fails to land.)*

**The baselines this phase is measured against**, both from the synthesis and both re-derivable:

| Figure | Value | Source |
|---|---|---|
| Authored output, one `research_minor` cycle | 39,772 bytes | synthesis §2, measured 2026-08-12 |
| CLI transcript, same cycle | 4,823,628 bytes | synthesis §12, same measurement |
| Current run-log archive | 175 files / 262 MB / 125 days / **zero** pruning code | `state_passing` §4.4, main checkout 2026-08-12 |

**⚠ The third row is a timestamped lower bound, not a fact.** `state_passing` §4.4 enumerated it five times in one day and got 175 → 178 files and 262 → 265 MB, because there is one file per dispatch and no pruning code. It is also gitignored, so no clone, CI runner or worktree can re-derive it. **What is stable is the shape** — 175+ files, 260+ MB, a 125-day span, zero pruning code, zero bytes in git — and any requirement here that quotes the number rather than the shape is quoting something that has already changed.

---

## Notes and open items

- **This phase writes no emitters.** If it finds itself specifying *what* a run writes rather than *where it lands and how it is read*, that is [Phase 3](phase3_the_emit_rule.md)'s scope and belongs there.
- **The three questions the journal must answer are still unanswered** (roadmap § *Open inputs*, item 3). The payload spec above is written against Phase 4's rebuild test, which is the strictest available proxy — the journal must carry enough to *regenerate* a store, not merely to describe a run. If the three questions arrive and disagree with the spec, **the spec is what changes**, and this note is the breadcrumb saying so.
