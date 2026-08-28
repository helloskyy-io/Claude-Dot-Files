# The memory model

Long-running work outlives any single session. Context windows do not. So the platform keeps **no state files and no bookmarks** — memory lives entirely in durable records, and the record's own to-do bit is what marks work as current.

This document is the framework. [`operations.md` § The memory model](operations.md#the-memory-model) is the one-paragraph orientation that points here; there is deliberately **one** description of this model and it is this file.

## Read this document in two layers, because they have different lifetimes

**The working record — the durable record whose life ends when its to-do bit clears — is an INTERFACE. GitHub is one binding of it.** PR threads, Issues and the standup tracker are how this fleet implements the working record today; every one of those is a GitHub fact, not a property of the interface. A component whose work product is not code in git — an edge device, a robot, a datacenter node — has no PR to comment on and no issue to close, and it still needs durable memory.

The split is not hypothetical here. **This fleet already runs two bindings** (§2.4, §2.5): three surfaces are GitHub objects whose to-do bit is `open`, and **two are committed markdown tables** whose to-do bit is a `status:` column. Both bindings satisfy the same five properties. Everything stated at the interface layer below already holds across a substrate change *that has happened*, not one that is imagined.

**Two file surfaces rather than one is what makes the split an observation instead of an illustration.** A single exception is an anecdote and invites the reading that the interface was generalised from one odd case. The file binding has two members with *different lifecycles* — one rotates its rows out, one never deletes a row — so what they share is the five properties and nothing else. That is what "interface" means, and it is measurable here rather than argued.

So every section that could be answered two ways answers both:

- **§1 (with §1.1–§1.2), §3.1, §5.1, §6.1 — the interface.** What any substrate must provide. A new substrate re-implements these.
- **§2, §3.2, §4, §5.2, §6.2 — this fleet's binding.** How GitHub (and the file surface) provides them today. A new substrate inherits none of this and must supply its own.
- **§7 — the seam between them**, and the only part that is neither: what a typed record would have to model to render this binding without losing what §1 property 3 requires.

§9 states the split as a single inherit-versus-re-implement table.

**Where to start, because the second half is not orientation.** §1–§3 are the model: read them to understand how the platform remembers anything. §4–§7 are reference for whoever changes what a surface emits or parses — a per-field consumer map, a blast-radius table, the addressing convention and the typed-exit-record seam. If you are orienting rather than changing a field, §1–§3 and §9 are the document.

> **The typed exit record is the machine-readable counterpart:** emitted at exit on a channel the parent owns, read by code within seconds. It is **built and in daily use**; its contract is [`exit-protocol.md`](../standards/exit-protocol.md) and it is now owned by the [Persistent Memory Protocol](../development/persistent-memory-protocol/roadmap.md). It was delivered as [Phase 3](../development/memory-management-framework/phase3_typed_exit_record.md) of the Memory Management Framework, **retired 2026-08-16** — that phase doc is the record of how it was built, not a live plan. This document exists partly so that record knows exactly what the working record carries, because under the arrangement Phase 3 adopted, anything the typed record does not model, the render loses. §7 enumerates what is at risk.
>
> **The names on this axis are the [Persistent Memory Protocol](../development/persistent-memory-protocol/roadmap.md)'s, and it is their single writer.** It cuts the fleet's memory on **what ends each record's life** rather than on who reads it, because audience turned out not to predict behaviour — its § *Reading the old names* maps the numbered labels this document used to carry.

---

## 1 · The interface — five properties, stated without a substrate

A working record is any record with all five. **No property below is stated in terms of GitHub, git, a file or a URL** — where those nouns appear it is as a contrast (what a substrate would otherwise need) or as a redirect to §7.3, never as part of what a property requires. That is the claim, and it is the one a grep can check.

| # | Property | What it means | What breaks without it |
|---|---|---|---|
| **1** | **Durable** | Outlives the process that wrote it, and outlives the machine it ran on | Work is re-derived every time a context ends |
| **2** | **Readable by humans *and* by later automated runs** | One artifact serves both audiences; not a log for one and a summary for the other | Two artifacts drift, and the one nobody checks becomes wrong silently |
| **3** | **Carries the outcome *and* its reasoning** | Not just *what* was decided but *why*, in enough detail that a later actor can re-adjudicate rather than re-derive | A later pass repeats a rejected approach because the rejection's reasoning died with the run |
| **4** | **Has a to-do bit** | A machine-legible flag saying whether this record still needs something. Binary, on the record itself | Something outside the record must track currency — a state file, a bookmark, a person's memory |
| **5** | **Retrievable by address, not by replay** | A later actor can locate *this* record from an identifier, without reading everything ever written | Retrieval cost grows with history, and eventually only a human will pay it (§6) |

**And one property that is a consequence rather than a member: it survives context death.** That falls out of 1 + 5. A record that is durable but not addressable survives storage and not use.

**The to-do bit is property 4 and it is load-bearing.** Everything the platform does *not* have — no state files, no bookmarks, no "current work" registry — is bought by it. The bit lives on the record, so the record is self-describing and there is no second thing to keep in sync.

**Measured, not asserted — and the measurement lives at the binding layer, where it belongs.** The rival design is that a *separate* typed channel owns the to-do bit and the record merely describes. [Phase 1](../development/memory-management-framework/phase1_measure_the_channel.md) E3(b) tested that against this fleet's archive and it lost twice over: where both bits existed they disagreed far more often than they agreed, and in the large majority of cases the typed bit did not exist at all, so the record's own bit was not merely primary — it was the only one. **§7.3 carries the figures**, because they are facts about a GitHub archive rather than about the interface. Property 4 belongs to the durable record.

### 1.1 · The selection rule, at the interface layer

**QUESTION 0, asked before the other two, because everything downstream is wrong without it: is this a DEFECT or a PROPOSAL?**

- **A defect** — something already built or already decided behaves wrongly, or a decision the existing research and planning do not supply is now blocking. Continue to questions 1 and 2.
- **A proposal** — capability that does not exist yet and would be *added*. **It goes to [`tracked/candidates/`](../../tracked/candidates/) and it is NEVER an issue**, however clean its done-state looks. Stop here; questions 1 and 2 do not apply to it.

**Why this is question 0 rather than a note.** Without it a proposal answers *"nothing changed"* and *"yes, it has a done-state"* — because *"add a link checker"* has a perfectly clean done-state — and the rule routes it to **Issue**. That is not a misreading of the rule; it is the rule working as written, and it is measured: across two repos in one cycle roughly a third of everything filed was a proposal wearing a defect's clothes, and clearing them cost two working days against zero days of development.

**The asymmetry is deliberate.** The issue store is the human-in-the-loop queue and is reserved for the hardest cases, so **question 0 is biased toward the proposal store**: when a finding could plausibly be read either way, it is a proposal. A proposal misfiled as a candidate costs a triage pass; a proposal misfiled as an issue costs an operator's day.

Once question 0 says *defect*, which record it goes to is decided by **two further questions, in this order** — neither of which mentions a substrate:

1. **Did something change?** A changed-artifact outcome and a no-change outcome are different records, because they are read by different actors at different times: the first is read *now*, by whoever accepts or rejects the change; the second is read *later*, by whoever plans work.
2. **Does it have a single done-state?** An outcome that can be finished belongs to a record that closes. An outcome that is a *condition* — ongoing operating state, a multi-day migration, a live incident — has no done-state, so a closing record cannot hold it and it needs a record that persists and is pruned instead.

Those two questions produce exactly three classes. **A fourth class exists and is a genuine one:** an outcome whose resolution is not work at all but a *ruling* — a preference, a priority, a commitment that no amount of further work would uncover. §2.4.

**Four outcome classes, five surfaces — and the fifth surface holds PROPOSALS, which are not outcomes at all.** Questions 1 and 2 route things that already *are* outcomes. A proposal has not been dispositioned yet, so it has no outcome class to route by — which is exactly why it needs question 0 in front, and why the earlier version of this section, which said the rule *"never selects"* the proposal store, produced the misfiling described above. **The rule does select it: question 0 does.** Entries are *created* there and acquire an outcome class later, at which point questions 1 and 2 apply to them normally. A rule that appeared to route to every surface would have to pretend an untriaged proposal is a decided thing, and §2.5 records what that costs: *a blank decision is not the same as `open`*, and collapsing the two is what put seven untriaged candidates on a surface whose own rules forbid them.

### 1.2 · The discipline that makes it work

Two rules, and they are the reason the model does not rot:

- **Every record is written by the actor that knows something and read by an actor that needs it. Nothing is written "for the record."** A record with no reader is not memory, it is exhaust — and it costs the reader of the *other* records their attention.
- **An account is not the artifact.** A summary, a decision log, a prior pass's prescription, an agent's finding — all are *claims about* the work, none of them are the work. Every reviewing actor is bound to verify against the artifact, and **to verify a pointer by fetching it, never by plausibility.**

---

## 2 · This fleet's binding — one API surface and four file surfaces

**REBOUND 2026-08-26, AND THE INTERFACE DID NOT MOVE.** §1's five properties are unchanged; what changed underneath them is the whole substrate. This section used to read *"three GitHub surfaces plus two file surfaces"* — Issues, the standup tracker, `direction.md` and `candidates.md`. Issues are **retired** for tracked work, the tracker and the candidates table **moved into `tracked/`**, and `direction.md` was **deleted outright**. That is four of the five, in one direction: **off GitHub's API and into the repo.**

**That is the argument of this document arriving, not failing.** §1 was written without a substrate precisely so a rebinding of this size would be a table change rather than a rewrite — and it was.

They are not interchangeable, and collapsing any two of them is a recurring failure (§2.6).

| Surface | Holds | To-do bit | Lifecycle | Written by | Read by |
|---|---|---|---|---|---|
| **PR threads** | change-outcomes — what got built, the run's own decision log and reflection, and the `pr_review:` disposition ruling on it | PR `open` | closes at merge | every PR-producing workflow; `review-pr` posts the disposition | the operator, and the next run through the PR body |
| **`tracked/issues/`** | a **defect** — code, docs or the planning corpus — found while building something unrelated | `status: open` | filed → ruled → `resolved` / `rejected`, then pruned | `review-pr` (sole autonomous filer), by **intake** | sprint close-out |
| **`tracked/operations/`** | continuity — operating state, next moves, work in flight. **No single done-state** | `status:` | items are **pruned**, never closed | **the operator alone** — no autonomous write, ever (§1.2) | every `/standup` |
| **`tracked/candidates/`** | a **proposal**, and the reasoning behind every `ship` / `requires review` / `reject`. **`requires review` IS the ruling queue** | `status: open` | filed → ruled → `adopted` / `rejected` | producing runs place their own; `triage-candidates` rules `decision` | `triage-candidates`, `plan-feature`, `plan-verify`, `plan-sprint` |
| **`tracked/standards/`** | a proposed amendment to a **named** standard, with an actionable anchor | `status: open` | filed → `ratified` / `amended` / `rejected` | **`review-pr` only** — a producing run surfaces it in its PR (2026-08-27 ruling) | the standards pass |

> **THE RULING CLASS LOST ITS OWN SURFACE AND GAINED NOTHING, WHICH IS THE POINT.** `direction.md` was a fifth surface holding `D-NNN` rows for findings only the operator could rule on. Every row pointed at a candidate that already carried `decision: requires review` — the same signal, in a store that already had a triage cadence — so the second surface added an id and nothing else. It had a reader and **no ruler**, and five rows sat unruled for three weeks. **A `requires review` candidate is the ruling queue now.** Giving this class a surface again is what [Tracked Items §8](../standards/documentation/tracked_items_standard.md) calls a violation.

> **`review-pr` still files without a commit, and the mechanism is new.** A file surface needs an edit, a commit and a push; a decide-only reviewer has none of those and must not. It files a `tracked-intake` GitHub issue — the same API call it always made — which a named harvest moves into the store and closes. See §5.0 of the standard: the exemption is conditional on that harvest existing.

### 2.1 · The selection rule, bound

Apply §1.1's questions, **starting with question 0**:

- **A PROPOSAL — capability that does not exist yet** → **[`tracked/candidates/`](../../tracked/candidates/)**. Never an issue, whatever its done-state looks like. Bias toward this when a finding reads either way: a proposal misfiled here costs a triage pass, a proposal misfiled as an Issue costs an operator's day.
- **Something changed** → **PR thread**. The change and its ruling live together, and both die at merge because the change is then history.
- **Nothing changed, and it has a done-state** → **[`tracked/issues/`](../../tracked/issues/)**. It can be finished, so it must be able to close.
- **Nothing changed, and it has no done-state** → **[`tracked/operations/`](../../tracked/operations/)**. Operating state is a condition, not a task.
- **Nothing changed, and the resolution is a ruling rather than work** → **a candidate carrying `decision: requires review`**. No amount of further work would produce the answer; only the operator can.

**That is the whole rule.** It is stated as a rule and not implied by examples on purpose: an example-driven table answers the cases someone thought of, and the failure mode here is always the case nobody thought of.

**`tracked/candidates/` is reached by question 0 and by nothing else** — questions 1 and 2 never select it, because a proposal has no outcome class for them to read. *(Corrected 2026-08-09: this paragraph previously said nothing was routed there at all, which left a proposal to fall through questions 1 and 2 into the issue surface. That is the measured misfiling this correction exists to stop.)*

**A run is not expected to know where a proposal belongs in the plan** — only that it is a proposal. Deciding whether it becomes a sprint, a phase, or nothing is a separate triage job with its own criteria, and asking a dispatch to do it inline is what produced feature requests filed as Issues in the first place.

The rule also owns what happens *once triaged*: `requires review` is set on the candidate and it stays there as the pointer; `ship` → an existing phase doc or a new sprint section.

### 2.2 · Why the tracker STOPPED being a GitHub issue

**It was an issue only because of the substrate, and the substrate's argument reversed.** Several sessions edit it daily, and one API call beat a branch and a merge conflict on the artifact least able to afford being stale. **File-per-item removes the conflict instead of routing around it:** two sessions touching different items never collide, and two touching one item have a real conflict that deserves a human. `tracked/operations/` since 2026-08-26.

One consequence binds every reader, and it survived the move unchanged:

- **Never apply the issue-disposition obligation to it.** That obligation binds a *container* that is supposed to close; an operations item's binds the *item*. Merging the two taxonomies would need an exit for *pruned*, which is a schema violation rather than a convenience.

**And one is new: no machine writes here.** §1.2 reserves this store to humans. A run that wants something remembered files an issue, a candidate or a standards amendment — all three have admission tests a machine can apply, and *"someone should look at this"* is not one.

### 2.3 · `/standup` is a WRITER, and the corrected record of that matters

**`/standup` writes on three surfaces**, derived from its Stage 2 body rather than from its own § Rules summary — which is the distinction §1.2 is about, and getting it wrong is how the first two attempts at this paragraph were both undercounts:

| Write | Surface | Declared at |
|---|---|---|
| **edits item files** — reconciles `state:`, prunes a `resolved` item ≥14 days after last activity | `tracked/operations/` | `config/commands/standup.md:5` |
| **drains the intake** — harvests every `tracked-intake` issue into its store and closes it | all four `tracked/` stores | `:6` |
| `gh issue close <N> --comment <evidence>` — closes an issue whose work it verified done | GitHub Issues | `:7` |

Everything else it does is a read. **It never sets `ready:`** — that is an authorisation to act, and it is the operator's alone (§4).

**Why the write exists, so it is not read as scope creep:** a reconciler that can see an item is finished but cannot say so re-reports that dead item every morning, forever. The write is what makes the read worth doing. **No autonomous *dispatch* writes to the tracker** — that remains true, and it is a different claim: `/standup` runs in an operator session, which is the human-in-the-loop.

### 2.4 · `tracked/candidates/` — the file surface, and the proof the interface is real

`tracked/candidates/` is a directory of committed markdown items, one file per candidate, each opening with the six-field core of [Tracked Items §3](../standards/documentation/tracked_items_standard.md). Check it against §1: durable (in git), human- and machine-readable, addressable (`C-` plus eight random base36, and **the filename IS the id**), carrying a to-do bit (`status`), and reaching a terminal state (`adopted` / `rejected`, then pruned).

**Five for five, on a substrate with no API at all.** Nothing about that record is a GitHub fact — it is the same interface on a different substrate, shipped and in daily use, which is the whole claim §1 makes.

**Its lifecycle shape is Task** — every item is obliged to reach a ruling — with a retention term on top, which §3.1 separates from the bit itself.

> **THIS SECTION USED TO DESCRIBE TWO SURFACES AND A TABLE.** §2.4 was `direction.md` and §2.5 was `candidates.md`, both `NNN`-keyed markdown tables, and §2.6 below recorded that the pair "collapses in the direction of the operator's file". **They did collapse — in the other direction, deliberately.** `direction.md` is deleted and `candidates.md` became a store of files. The property the split was protecting, *a ruling only the operator can make*, is now `decision: requires review` on a candidate.

> **AND FILE-PER-ITEM IS NOT A COSMETIC CHANGE TO THIS ARGUMENT.** A single table makes every concurrent write a merge conflict on the artifact least able to afford being stale — measured on the old `candidates.md`: nine renumbering events and six id collisions in a day. Two sessions touching different items now never conflict; two touching one item have a real conflict that deserves a human. **The store optimises for safe writing and the rendered view optimises for reading**, and the view is never the source.

### 2.6 · Which two get collapsed, and what happens

Collapsing surfaces is the recurring failure, and it is not symmetric — one pair collapses far more often than the others.

**Defect ↔ continuity is the collapse that actually happens**, and moving both into `tracked/` did not stop it — it only stopped the substrate *inviting* it. The failure is bidirectional and both directions have been paid for:

- **Continuity filed as an issue** → it can never close, so it ages, gets flagged as stalled, and every standup asks the operator to dispose of something that is not disposable.
- **Deferred work parked in operations** → it loses the standing disposition obligation an issue carries, and it is now also a **§1.2 violation**, because no machine may write there at all.

**PR thread ↔ any store collapses in one direction only:** a run parking its own deferred work in its own PR body. That pointer dies at merge, which makes it the most expensive collapse of the set — the finding is not misfiled, it is gone.

> **TWO COLLAPSES THIS SECTION USED TO NAME NO LONGER EXIST, and one of them was resolved by being committed rather than avoided.** *"Issue ↔ tracker"* was keyed on both being GitHub issues; neither is now. *"`candidates.md` ↔ `direction.md`"* warned that two `NNN`-keyed tables in one directory would collapse toward the operator's file — **they collapsed the other way on 2026-08-26**, by deleting `direction.md`, because the ruling it held was already a candidate's `decision`. A predicted collapse that gets resolved deliberately is the document working.

---

## 3 · What each surface holds, for how long, and who reads it

### 3.1 · At the interface layer

Four lifecycle shapes exist, discriminated by **what ends a record's life** — the axis [`persistent-memory-protocol/roadmap.md` § The four kinds of record](../development/persistent-memory-protocol/roadmap.md) cuts the whole taxonomy on, applied here to the shapes a record can take. **A substrate must be able to express all four, or the model does not fit on it.** *(PMP roadmap standards-amendment candidate 1, applied.)*

| Shape | What ends its life | Record then |
|---|---|---|
| **Transactional** | the change it describes is accepted or abandoned | becomes an immutable past record; is not pruned, because the change it describes is permanent |
| **Task** | the work is done or ruled invalid | closes; stays retrievable by address for as long as its surface retains it, which is a per-surface term (§3.2) |
| **Continuous** | *nothing ends the record* — the to-do bit is per-item, not per-record | persists; individual items are pruned on an explicit schedule |
| **Append-only history** *(PMP's **journal**)* | a retention budget rotates the record out, and never past the last snapshot | it is gone; what a reader needs from it survives in the snapshot the rotation may not pass |

**Read *express* precisely: it is not *already has a surface of*.** The requirement is that the substrate can carry a record of each shape, which is what makes the model portable onto it. This fleet's own binding instantiates three and leaves Append-only history unbuilt (§3.2) — **a missing surface, not a failing substrate**, and the distinction is the difference between a fit test that rejects the substrate this document is written on and one that does not.

**The discriminator was *when the to-do bit clears*, and it could not reach a shape with no bit.** Append-only history has none — a past event never *needs* anything, so there is nothing on it for a bit to describe. *What ends its life* asks the same question without presupposing the mechanism of the answer.

**The pair it has to separate is Continuous and Append-only history, and what separates them is the unit the word *record* denotes.** For Continuous the **store is the record** and its items are parts of it, which is why nothing ends it and why its bit is per-item. For append-only history **each appended entry is a record** — the store is a sequence of them, not one long-lived record — so a retention budget ending one entry is that record's life ending, and the row above says so at that unit. Read at the wrong unit the two rows collapse into *nothing ends it*, which is exactly the failure the old column had.

**These four are not [PMP](../development/persistent-memory-protocol/roadmap.md)'s four classes, and the shared number is a coincidence worth disarming.** Rows 1–3 are shapes the **working record** class takes; row 4 is the **journal** class, which takes only this shape and is its one intended instance. PMP's other two classes get no row here at all — see below.

**Append-only history is not a §1 record, and saying so is what keeps §1 intact.** §1's five properties define the *working* record, and property 4 — *has a to-do bit* — is one a past event cannot satisfy. It is a shape the substrate must be able to express **for the model to fit on it**, not a fourth kind of §1 record; the two sit side by side as separate classes in the taxonomy cited above. The requirement on a substrate widened; the interface did not.

**What this discriminator does NOT separate, stated so the table is not read as finer than it is.** It says nothing about *how* a record is disposed of once its life ends — two records of the same shape can end identically and then be retained on entirely different terms. That is a per-surface property and §3.2 is where it lives, with this fleet's instances. **So read the *Record then* column as what the shape implies, never as a guarantee any surface owes**: it is why the Task row defers retention to §3.2 rather than promising a record stays addressable, which §2.4's 90-day rotation would falsify. It also does not reach the two classes that are not durable records at all — **invocation state** and **measurement samples** — because neither satisfies §1; PMP § *The four kinds of record* is where the two exclusions are argued, and this document does not re-argue them. A reader looking here for either will not find a row, and that absence is the answer rather than a gap.

**The asymmetry is the point.** A substrate offering only closing records cannot hold continuity, and the work goes back to living in session context and dying at a session boundary. A substrate offering only persistent records cannot express *finished*, and every reader must re-verify every item. **And a substrate offering only records that end cannot hold history at all** — every question about *why* is answered by re-deriving it from whatever survived, which is the condition the [Persistent Memory Protocol](../development/persistent-memory-protocol/roadmap.md) exists to end.

**A store whose contents are not each obliged to reach a disposition needs an explicit size bound, or it is a ledger.** That is a property of the interface, not of GitHub, and **two of the four shapes are in that condition, for different reasons and with different bounds.** A *Continuous* record's own bit never clears, so its bound is a **pruning rule on its items** — the only thing standing between it and the carried-work shape in §2.6. An *Append-only history* record has no to-do bit to reach a disposition on, so the bound falls on the store instead and is a **retention budget**; the budget is what makes deleting old records safe and the snapshot is what keeps the deletion lossless.

**Read the condition precisely — it does not bind the Task shape.** A Task-shaped record whose entries are retained after they close is not unbounded in the sense that matters, because every entry is obliged to reach a disposition; §2.5 is the instance, and mistaking retention for the ledger failure would argue for deleting the one record that makes a rotation safe.

### 3.2 · Bound to this fleet

| Surface | Retention | Pruning rule | Growth failure signal |
|---|---|---|---|
| PR threads | permanent; closed at merge | none — history | thread size (§6.3) |
| Issues | until ruled; closed with evidence | none needed — closing *is* the bound | an issue surviving a standup in the same state |
| Standup tracker | permanent document, transient lines | `state: resolved` + ≥14 days → deleted from the body | month-over-month growth |
| `tracked/candidates/` | one file per item | `adopted` 14 days after last activity; `rejected` at six months, so a rejection stays findable | rows accumulating unruled |

**`tracked/candidates/` prunes like every other store ([Tracked Items §4.2](../standards/documentation/tracked_items_standard.md)) — but its health signal is on a second axis:** every row must reach a `decision`, and *"leaving a row blank is not a disposition."* The growth signal is therefore blank decisions rather than row count — a file of 45 fully-triaged rows is healthy and a file of 5 untriaged ones is not, which is the opposite of what a size check would report.

**Append-only history has no binding in this fleet yet, and the table above is five surfaces rather than six for that reason.** Every surface here is Transactional, Task or Continuous; nothing in daily use is append-only history. Building it — the journal, its retention budget and its snapshots — is the [Persistent Memory Protocol](../development/persistent-memory-protocol/roadmap.md)'s work, and this table gains a row when that lands rather than before. **A row written ahead of the surface would be a retention rule nobody is obliged to follow**, which is the failure §3.1's bound exists to name.

---

## 4 · The `pr_review:` block — this fleet's machine-facing half of the record

> **Binding layer, throughout.** §4 names scripts and line numbers on purpose; a different substrate inherits none of it. The word *interface* is not used below in §1's sense — this block is a **wire format**, which is a narrower thing.

`review-pr` posts one comment per pass with two parts: a human-readable disposition table, and a fenced `yaml` block keyed `pr_review:`. **The block is the machine-facing half of the working record on this substrate**, and it is the record Phase 3's typed envelope will be rendered into or reconciled against.

> **The authoritative schema is the emitting prompt: [`scripts/workflows/children/review-pr.sh`](../../scripts/workflows/children/review-pr.sh) Stage 5, `:342-423`.** Per [Documentation Standard § Single-source codified fields](../standards/documentation/documentation_standard.md) the doc points and does not copy — field semantics, enums and absence rules live in that block and are not re-typed here. What follows is the thing this document adds rather than restates: **the consumer map.**

**`pr_review:` is a WIRE FORMAT, not a filename.** Renaming the key orphans `/standup`'s parse, both pass-counters, cross-pass stable-id tracking, and every block already posted on a live PR (`review-pr.sh:46-53`).

### 4.1 · The consumer map — who reads what

Verified by grep across both fleets (`grep -rn "pr_review\|gh issue list\|gh pr list" scripts/ config/`), excluding prompt strings.

| Field | Read by | What the reader does with it |
|---|---|---|
| *block presence* | `review-pr.sh:141-142` (`PRIOR_PASS`) · `review_pr_activities.py` `count_prior_passes` | counts prior passes → sets `THIS_PASS`. **`review-pr.sh` still over-matches — see §6.4. The V2 reader was fixed by [Phase 3](../development/memory-management-framework/phase3_typed_exit_record.md) step 8** and is now fence-anchored, declared once at `review_pr_helper.PR_REVIEW_BLOCK` |
| *block presence* | `replay_pr_review_blocks.py:45` | Phase 1 E3 + E7 corpus extraction |
| `verdict` | `/standup` `standup.md:48-51` | `HOLD` → render as a blocker; `MERGE` on an open PR → "ready to merge" |
| `next_steps[]` | `/standup` `standup.md:48-51` | delivered **verbatim** to the operator — the disposition engine already reasoned; standup does not re-derive |
| `pass` | *(human only)* | E7 measured it **non-dense** — #31 runs 1, 2, 4 — so "the previous pass" must come from block ordering, never from the integer |
| `findings[].id` | `replay_pr_review_blocks.py` | Phase 5's identity input. Convention measured to hold **25 of 25** on the added direction |
| `findings[].disposition` | `replay_pr_review_blocks.py` · `review_pr_helper.finding_dispositions_in_block` · `modules/assistant/convergence.py` | partitions findings into open/closed. Present on **300 of 300** archived findings (re-counted 2026-08-09; it was 195 of 195 at 38 PRs). **Phase 5 rules the partition: CLOSED is `fixed`/`deferred`/`rejected`/`noted`/`dissolved`/`escalated`, OPEN is `hold` plus anything unrecognised** |
| `converged` | `review_pr_helper.CONVERGED_FLAG`, via `review_pr_workflow` | **NEW as of [Phase 5](../development/memory-management-framework/phase5_convergence_stopping.md) (2026-08-09) — this key's first programmatic reader.** The parent reads the model's assertion back and shadows it against its own computed signal; the pair is written to the run log. **Read, never routed on** |
| `run_id` | `review_pr_helper.RUN_ID_IN_BLOCK`, via `_this_pass_index` | **NEW as of [Phase 4](../development/memory-management-framework/phase4_fleet_migration.md) (2026-08-10), and the block's first ADDRESSING field.** It answers *which block on this thread is this pass's* by identity rather than by ordering — the question §6.2's last-wins rule answers positionally and cannot answer correctly when a third party posts a fenced `pr_review:` example between the child's comment and the parent's read. **The parent falls back to ordering when no block carries it and says so in its notes**, because every block in the archive predates the field; a fallback that were silent would be the positional inference back under a new name. Emitted by the V2 prompt only — [`children/review-pr.sh`](../../scripts/workflows/children/review-pr.sh) is the frozen fleet and does not carry it |

### 4.2 · Emitted and read by nobody — named, because naming them is more useful than documenting them as though they matter

Phase 1 E6 verified three keys have zero programmatic readers: `converged`, **`attempt`**, **`hold_kind`**. **`converged` LEFT this list on 2026-08-09** and now sits in §4.1 — [Phase 5](../development/memory-management-framework/phase5_convergence_stopping.md) gave it a reader that shadows it against a computed signal. *Recorded as a move rather than a silent edit, because "read by nobody" is the sentence §5.2 leans on when it says a schema change to these fields is a documentation problem rather than an outage — and that is no longer true of this one.* This pass extends the remaining list from the emitting script; the rest of the block is human-facing today:

`pr`, `redispatched` (always `false` by contract), `laundered_deferrals.{caught,of_total}`, `homeless_items`, and per-finding `title`, `category`, `consequence`, `remedy`, `pointer`, `pointer_verified`, `reviewed_sha`, and per-next-step `item`, `kind`, `note`, `issue_url`, `issue_repo`, `qualified`, `dispatch_tool`, `dispatch_context`, `precheck`, `why_human`, `reframe`, `bp`, `recommendation`.

**"No programmatic reader" is not "no consumer."** `laundered_deferrals` is a CPI rate signal read by a human at review time; `reframe`/`bp`/`recommendation` are delivered verbatim to the operator by `/standup`. What the list means is narrower and more useful: **these fields cannot break a routing decision, so a schema change to any of them is a documentation problem, not an outage** (§5.2).

### 4.3 · Read but not reliably emitted — the live gap this comparison exists to find

**The routing token is not in the block.** Every parent branches on the prose line `VERDICT: MERGE | HOLD - redispatch | HOLD - needs-assistance` (`build.sh:277`, `build-minor.sh:281`, `routing.py:72`). The yaml carries `verdict: MERGE | HOLD` — **which cannot express the hold kind**, the very thing all four branch points need. The sub-kind exists only per-finding as `hold_kind`, which the model aggregates into the prose line by the rule at `review-pr.sh:434-438`.

**Consequence:** a consumer reading the durable record instead of the transient stdout — which is exactly what a later dispatch must do, since stdout is gone — **cannot recover the routing decision without re-aggregating it**, and re-aggregating means a caller with no stake in the review making a judgement about the review. Phase 1 E6 ruled this into the envelope as `hold_kind`, promoting a key with no code reader into one with four. Recorded here as the working record's side of the same gap.

### 4.4 · Reconciled against Phase 1 E6 — and where this pass disagrees

**E6's "nine fields" is not an enumeration of this block, and reading it as one would be a mistake with consequences.** E6 enumerated the *typed exit record's envelope* — the union of values every parent branches on, derived from 15 branch sites. This section enumerates what `review-pr` *emits into the working record*. They are different sets with a small intersection:

| | count | derived from |
|---|---|---|
| E6's envelope | **9** | what parents read |
| `pr_review:` block | **~31 leaf fields** | what the reviewer writes |
| overlap | **4** — `verdict`≈`outcome`, `hold_kind`, `findings[].id`, `findings[].disposition` | — |

**The disagreement, stated as a finding:** E6's ruling is correct on its own terms and this pass takes nothing back from it. What the two sets together show is the actual shape of the problem — **the durable record carries roughly seven times what any machine reads, and the four fields machines do need are exactly the four the two sets share.** That ratio is not waste; it is §7's prose, and it is the cost of arrangement A stated as a number.

---

## 5 · What breaks if a field changes

### 5.1 · At the interface layer — the three changes that are never local

Independent of substrate, a working record has exactly three change classes that reach beyond the record:

| Change | Blast radius | Why it is not local |
|---|---|---|
| **The to-do bit's name, location or value set** | every reader, unconditionally | It is the only field a reader must interpret to decide whether the record is current. Property 4 is what replaces the state file; changing it changes what "current" means fleet-wide |
| **The address** (§6.1) — the container id, the block marker, or the ordering rule | every *later* actor, silently | A retrieval that used to resolve now returns nothing, and **an absent record is indistinguishable from a record that says nothing was found.** This failure is quiet by construction |
| **A field's identity stability across revisions of the same record** | every cross-revision computation | If an identifier is reused for a different thing, or a stable thing gets a new identifier, every delta over that record is wrong and nothing fails loudly |

**Everything else is local.** A field with a named consumer breaks that consumer, loudly, at its next run. **The rule that keeps it that way: a field enters a working record with a named consumer, or it is prose** — and prose is §7's problem, not this section's.

### 5.2 · Bound to this fleet — the check-list a schema change runs against

| If you change… | Check | Breaks how |
|---|---|---|
| the key `pr_review:` | `review-pr.sh:142`, `review_pr_activities.py:51`, `replay_pr_review_blocks.py:45`, `/standup` `standup.md:48-51`, **every block already posted** | pass-counting silently resets to zero; standup reports every PR as "awaiting review" |
| `verdict`'s value set | `/standup` `standup.md:48-51` | a value standup does not recognise renders as neither blocker nor ready — it vanishes from the brief |
| `next_steps[]`'s shape | `/standup` `standup.md:48-51` | the runway stops reaching the operator; `review-pr` still writes it, nobody delivers it |
| `findings[].id` stability | `replay_pr_review_blocks.py`, [Phase 5](../development/memory-management-framework/phase5_convergence_stopping.md) | the convergence predicate reads a false delta. **Silent** |
| `findings[].disposition`'s enum | same | a value outside the **archive's measured vocabulary** — `{hold, fixed, deferred, rejected, noted, escalated}`, counted across all 195 archived findings ([Phase 1](../development/memory-management-framework/phase1_measure_the_channel.md) E7) — is scored as *open* by the closed-set reading, so the open set can never empty. **Silent.** **There are TWO live emitters and they declare DIFFERENT enums.** `review-pr.sh:361` (V1 bash) declares four — `fixed \| rejected \| deferred \| hold`. `disposition.md:223` (the V2 prompt) declares six — the four plus `noted \| escalated`. So `noted` and `escalated` are **not** historical residue from earlier passes; they are written by a currently-wired producer, and any pass through the V2 path can emit them. A reader built to the V1 declaration is wrong about the fleet running today. **Narrowing the emitter does not narrow the archive** |
| the prose `VERDICT:` line | `build.sh:277`, `build-minor.sh:281`, `routing.py:72`, `run-claude.sh` § *Completion contract* | the parent's completion gate fails loud (child side) or synthesises `HOLD - needs-assistance` (parent side). **The gate's surface now depends on the caller:** without a declared schema it reads `.result`; with one it reads the LAST assistant text block, because declaring a schema replaces `.result` with the serialised structured output ([Exit Protocol §2.4](../standards/exit-protocol.md)) |
| anything in §4.2 | no code | nothing breaks; **a human loses information and nothing tells them** |
| the tracker's section order or per-line fields | `/standup` `standup.md:39` | the readiness ordering (`BLOCKED`→`READY`→`IN FLIGHT`→`RESOLVED`) is how the operator triages; normalising it destroys the property |

**The two silent rows are the ones that matter.** Both are in the convergence path, both fail by producing a wrong answer rather than no answer, and neither has a consumer that would notice. They are the reason [Phase 4](../development/memory-management-framework/phase4_fleet_migration.md) verifies fleet-wide against this list rather than against the emitting script.

---

## 6 · Retrievability — the addressing convention

**This is the half of the interface nobody had written down.** A surface a later actor cannot *address* is a surface only a human can read, which is the gap the [Memory Management Framework](../development/memory-management-framework/roadmap.md) was built to close and the [Persistent Memory Protocol](../development/persistent-memory-protocol/roadmap.md) now owns.

### 6.1 · At the interface layer — four parts, and all four are required

Retrieval is *addressing*, not *location*. "It is posted on the PR" is a location; it is not an address, because it does not tell a later actor how to get **the right one** without reading everything. An address has four parts:

| Part | Answers | Absent ⇒ |
|---|---|---|
| **Container id** | which unit of work is this about? | the actor must search rather than fetch |
| **Block marker** | where inside the container does the record start and end? | the actor must parse prose, and cannot distinguish a record from a mention of one |
| **Ordering rule** | which of several records in one container is the latest? | the actor may act on a superseded record — and will not know it did |
| **Sequence number** | which revision is this, and what did the previous one say? | a correction pass cannot establish what it is correcting |

**Sequence must be derivable from the ordering rule, not only from a written-in counter.** A counter written by the producer can be wrong; the ordering of records that actually exist cannot be. Where the two disagree, ordering wins — this is a general rule and §6.4 is why it is stated as one.

### 6.2 · Bound to this fleet

| Part | Binding | Declared at |
|---|---|---|
| Container id | the PR number | `--pr <N>` |
| Block marker | a fenced ```` ```yaml ```` block whose **first line is `pr_review:`** | **two emitters** — `review-pr.sh:342-344` (V1) and `disposition.md:201-203` (V2); `replay_pr_review_blocks.py:45` (the only executable statement of it) |
| Ordering rule | comment creation order on the thread; **last wins** | `/standup` `standup.md:48` — *"the LATEST comment containing a `pr_review:` yaml block"* |
| Sequence number | the block's `pass:` key, written by the producer | **two emitters** — `review-pr.sh:346` (counter at `:141-143`) and `disposition.md` (V2 writes the same key) |

For the other surfaces the address is simpler and complete: **PR threads** — `owner/repo#N`, one record per container, no ordering needed. **The `tracked/` stores** — `<PREFIX>-<8 random base36>`, never reused, and **the filename IS the id**, so an id in a commit message resolves to a file without a lookup. An id is terminal: it resolves to one item and to nothing further.

### 6.3 · What retrieval costs today

The CPI deferral that names this phase reports a correction pass **paging a 37 KB comment dump** to find a block it had every reason to fetch directly.

**That figure is now the low end.** Measured across all 39 PRs at `bcdb519` — 57 comments, **858 KB** of comment body in total:

| | KB |
|---|---|
| Median thread carrying a block | **83** |
| Largest thread carrying a block (#31) | **177** |
| Whole corpus, to extract 15 blocks | **858** |

**And Phase 1 paid it twice.** E3's to-do-bit cross-tab and E7's convergence replay both read this corpus, and both did it the same way — `replay_pr_review_blocks.py` fetches **every comment of every PR** and regex-extracts, because no cheaper address exists. That is the baseline: *to read 15 records the fleet reads 858 KB*, and the ratio degrades with every comment posted, on threads a record was never the largest thing in. (Phase 1's E5 is sometimes cited here; it is not this cost — E5 replayed `.claude/logs/*.jsonl`, a different corpus.)

**Stated so the improvement is measurable rather than asserted:** any Phase 3 retrieval mechanism is measured against *bytes read to reach one record*, currently ≈57 KB per record extracted, worst case 177 KB for a single thread.

### 6.4 · The convention is written down three incompatible ways, and two of them are wrong

The block marker in §6.2 is stated by three readers, and they do not agree:

| Reader | Predicate | Matches over the archive |
|---|---|---|
| `review-pr.sh:142` | `test("pr_review:")` — unanchored regex over the whole comment body | **18** |
| ~~`review_pr_activities.py:51`~~ | ~~`"pr_review:" in body` — plain substring~~ — **FIXED by [Phase 3](../development/memory-management-framework/phase3_typed_exit_record.md) step 8**; now `review_pr_helper.PR_REVIEW_BLOCK`, fence-anchored and declared once | 18 → **15** |
| `replay_pr_review_blocks.py:45` | fence-anchored regex requiring an actual ```` ```yaml ```` block | **15** |

> **Two of the three are now one declaration, and the third is a deliberate carve-out.** Phase 3 fixed the V2 reader and added the working record's *address* to the [Exit Protocol](../standards/exit-protocol.md) §6 one-declaration rule (roadmap candidate 6). `review-pr.sh:142` is the **frozen V1 bash fleet** (§7) and is not fixed, so issue **#68** stays open on that half.
>
> **There is no fourth declaration in `/standup`, and this note previously said there was.** Three passes carried *"`standup.md:56` matches by mention in prose"* before anyone read the line. It says *"find the LATEST comment containing a `pr_review:` **yaml block**"* — it names the block form, so the characterization was simply wrong. The distinction that matters is not that the two differ but *how*: the three code declarations are **executable matchers with a comparable `.pattern`**, which is what makes "declared once and loaded" checkable and gateable; a prompt has nothing to load and no pattern to compare, so §6's rule has no purchase on it. **Phase 4's fleet-wide sweep does not inherit this item.** If Phase 4 wants prompt files in scope, that is a scope decision it makes explicitly rather than a debt handed to it from here.

**Measured at `bcdb519` over all 39 PRs: 3 false positives, on 2 of the 8 PRs that carry any block.** Both pass-counters match any comment that merely *mentions* the string — a Post-Run Reflection, a build-refine summary, a brief quoting the wire format.

The consequence is not hypothetical; it is in the archive:

- **PR #31** — comments carry blocks at `pass: 1`, `pass: 2`, then `pass: 4`. The comment between them is a `build-refine` reconciliation note with no block. It was counted. **There was never a pass 3.**
- **PR #66** — one block, labelled `pass: 3`. The two comments before it are the build-draft and build-refine reflections. **It is pass 1.**

**This changes something Phase 1 recorded as structural.** [Phase 1](../development/memory-management-framework/phase1_measure_the_channel.md) E7 § *Two structural facts Phase 5 needs and the archive does not advertise*, item 1, states *"pass numbers are not dense"* and instructs Phase 5 to derive consecutiveness from block ordering rather than the integer. That instruction is correct and should stand — but the *reason* given, that non-density is a property of the archive, is wrong: **it is this over-match, and it is fixable.** §6.1's rule that ordering outranks a written counter is the general form of the same lesson.

**The record written into the working record is wrong in both cases** — `pass:` is a durable field of it, and it is off by two on the most recently reviewed PR in the repo. Phase 2 documents the convention and names the defect; **it does not fix it** — this phase documents what exists, and the remedy is a code change in two files.

### 6.5 · Cross-reference — the CPI deferral this section closes

[`cpi-decisions.md`](../development/cpi-decisions.md) § *DEFERRED — a correction pass cannot machine-read the prior pass's runway* (2026-08-07) carries the watch-criteria **"ship as part of the Memory Management phase doc, or immediately if a correction pass MISREADS a runway."** That trigger fired; §6.1–6.4 are where it lands. The deferral's second clause is worth reading against §6.4: it distinguished *paging 37 KB and getting it right* from *acting on the wrong prior finding*. The over-match is the second class — not a wrong finding, but a wrong pass number written durably — and it is recorded rather than treated as the smaller problem.

---

## 7 · The seam the typed exit record attaches to — rendered output versus authored prose

[Phase 3](../development/memory-management-framework/phase3_typed_exit_record.md) adopts **arrangement A**: the child writes a typed record once at exit, and the human record is *rendered* from it. The cost is stated in the roadmap and it is exact — **everything the human reads must be expressible in the typed record, or the render loses it.**

So the boundary has to be drawn before the schema is written, and drawn wrong it produces a schema that silently drops what the operator actually reads.

### 7.1 · Rendered — derivable from a typed record, safe to generate

The disposition **table** (id · category · disposition · pointer), the verdict token, the pass and attempt numbers, the `laundered_deferrals` rate and `homeless_items` count, per-finding `remedy`, `pointer_verified` and `reviewed_sha`, and the `next_steps` list *as a list*. All of it is enumerable, and all of it already exists in the yaml.

### 7.2 · Authored — prose a schema must model explicitly or lose

**Enumerated, not gestured at. This is the cost of arrangement A and this document does not hide it.** Fourteen items.

**Read these three first — they have no yaml field at all today** (rows 3, 4 and 11, marked ⚠), so a render-from-record drops them silently rather than degrading visibly:

1. **the per-finding disposition reasoning** — the *why* behind each ruling
2. **the one-line verdict rationale** — the first thing a human reads
3. **the Post-Run Reflection** — friction and tooling signal, and a primary CPI input

The other eleven exist in the yaml and are at risk only of being treated as derivable when they are authored.

| # | The prose | Where it lives | Why a schema cannot infer it |
|---|---|---|---|
| 1 | `findings[].title` — the consequence in one line | yaml | E7 measured it **rewritten between passes under a stable id**: #45's finding states the defect on pass 1 and the fix on pass 2. It is authored per pass, not a label |
| 2 | `findings[].consequence` — what breaks | yaml | The gate that separates a finding from a note (`review-pr.sh:237`). Unenumerable by construction |
| 3 | ⚠ **the disposition reasoning** — the table's "Reasoning" column | **rendered table only** | The yaml carries `disposition` + `remedy` + `pointer`; the *why* has no field. **This is the single largest loss item** — the rejection reasoning is exactly what stops a later pass re-litigating a settled call, i.e. property 3 of §1 |
| 4 | ⚠ **the one-line verdict rationale** | **rendered comment only** | No field. It is what a human reads before anything else |
| 5 | `next_steps[].reframe` — the `/decide` reframed question | yaml | **The reviewing agent's working shown to the operator.** Its whole purpose is to be audited at standup speed; a schema can hold the string but cannot generate it |
| 6 | `next_steps[].bp` — the best-practice alignment | yaml | As above; the pair is what makes a recommendation auditable rather than trusted |
| 7 | `next_steps[].recommendation` — the reasoned resolution | yaml | Multi-line, follows from 5 + 6 |
| 8 | `next_steps[].dispatch_context` — the scoped fix task | yaml | The runway's actual payload. A correction pass executes this text |
| 9 | `next_steps[].precheck` — the machine-checkable precondition | yaml | Carries four stated requirements *and* a precedence clause resolving conflicts with 8. Prose about prose |
| 10 | `next_steps[].note` / `qualified` | yaml | `qualified` states *how* each of three filing criteria was met — an argument, not a flag |
| 11 | ⚠ **the Post-Run Reflection** appended to the disposition comment | **comment only** | Friction and tooling suggestions. No field, and it is a primary CPI input |
| 12 | the **"WHAT HAPPENS NEXT"** runway, *ordered* | rendered list | `next_steps` is a yaml sequence with no ordering contract; the rendered list is ordered for a human. Order is information |
| 13 | **re-laundering flags** (invariant 2) | prose | *"this dead pointer reappeared"* is a cross-pass observation with no field |
| 14 | **prior-prescription verification** (invariant 3) | prose | *"the fix I prescribed last pass landed / regressed"* — no field |

**Read the ⚠ rows together and they are one problem: the reasoning has no schema.** Items 3, 4 and 11 are precisely the parts that satisfy §1 property 3 — *the outcome **and its reasoning***. A typed record that carries every enumerable field and none of these still fails the interface it is supposed to serve. Phase 3 must either model them as free-text fields or state explicitly that the rendered comment remains independently authored alongside the record. **Either is defensible. Silence is not**, and silence is what produces the operator noticing something missing months later.

### 7.3 · The open question this document does NOT answer

**Which channel owns the to-do bit when a typed record carries a verdict and the durable record carries open/closed.**

**This is where §1's property-4 measurement lives**, because it is a fact about a GitHub archive rather than about the interface. [Phase 1](../development/memory-management-framework/phase1_measure_the_channel.md) E3(b): the typed verdict disagreed with the PR's disposition in **6 of 7** cases where both existed, and **31 of 38** PRs carry no typed verdict at all. On that evidence `open` owns the bit on this binding.

**What remains open is not who wins — it is what the loser is for.** [Phase 3](../development/memory-management-framework/phase3_typed_exit_record.md) rules on that, and its own checklist demands it. **Recording the question here as open is correct; ruling on it here is not.**

---

## 8 · Where this model is enforced rather than described

This is a guide document — it describes a system in daily use, and it binds nothing. Two pointers so that is not mistaken for the whole picture:

- The **[Exit Protocol](../standards/exit-protocol.md)** is where the machine half is heading. It is a **draft scaffold and explicitly not binding**; its §1 states the interface-versus-binding split this document implements.
- Rules that autonomous runs must obey — pointer verification by fetch, the deferral placement questions, the prohibition on carried-work ledgers — live in `engineering-quality.md` and in each workflow's own prompt, not here.

**Any rule this document implies should become binding is surfaced as a standards-amendment candidate in the [Persistent Memory Protocol roadmap](../development/persistent-memory-protocol/roadmap.md#standards-amendment-candidates), never written into `docs/standards/`.** That section states outright that *"this roadmap is the writer for these entries"*. It used to name the [Memory Management Framework](../development/memory-management-framework/roadmap.md) instead, and the pointer moved when that component was **retired on 2026-08-16** — a candidate filed into an unmaintained document is the surfaced-but-never-placed failure this model exists to stop.

---

## 9 · Inherit versus re-implement — what a different substrate is actually signing up for

The question this table answers: *a new component's work product is not code in git — what does it get for free, and what must it build?*

| | Inherited — substrate-independent | Re-implemented — this fleet's binding |
|---|---|---|
| **Contract** | §1's five properties — **of the working record.** §3.1's Append-only history is not a §1 record and this row does not reach it; its contract is [PMP](../development/persistent-memory-protocol/roadmap.md)'s | — |
| **Selection** | §1.1's two questions; the three outcome classes plus the ruling class; that a surface may be *created into* rather than routed to | §2.1's mapping onto PR / Issue / tracker / `direction.md`, and `candidates.md` sitting outside the rule (§2.1) |
| **Lifecycles** | §3.1's four shapes; the rule that a store whose contents are not each obliged to reach a disposition needs an explicit size bound | §3.2's specific retentions and thresholds (merge, close, 14 days, 90 days, never) — **four shapes, and only three of them are bound here yet** (§3.2) |
| **To-do bit** | that every §1 record has one, on the record, binary — **and that §3.1's Append-only history has none**, so a substrate builds it a retention budget rather than a bit that could never clear | that it is GitHub `open` — **and note this fleet already has two exceptions**: `direction.md`'s and `candidates.md`'s are both `status:` columns (§2.4, §2.5) |
| **Change safety** | §5.1's three non-local change classes | §5.2's per-field consumer list |
| **Address** | §6.1's four parts, and that sequence derives from ordering | §6.2's PR number / yaml fence / comment order / `pass:` key |
| **Discipline** | §1.2 — written by an actor that knows, read by an actor that needs; an account is not the artifact | the specific fetch commands that verify a pointer — **not stated here**; they live in `engineering-quality.md` § *A deferral is PLACED* and in each workflow's own prompt (§8) |
| **The seam** | that authored reasoning exists and must be modelled or consciously dropped | §7.2's fourteen specific items, which are `review-pr`-shaped |

**Read the right column as the migration cost.** It is four rows of mechanism and one row of enumeration — and none of the left column moves. That is the claim the split was made to support, and **§2.4 and §2.5 are two instances that already tested it** — on the same substrate, with different lifecycles, which is what makes the left column's stability an observation rather than a hope.
