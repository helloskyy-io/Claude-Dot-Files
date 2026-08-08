# The memory model

Long-running work outlives any single session. Context windows do not. So the platform keeps **no state files and no bookmarks** — memory lives entirely in durable records, and the record's own to-do bit is what marks work as current.

This document is the framework. [`operations.md` § The memory model](operations.md#the-memory-model) is the one-paragraph orientation that points here; there is deliberately **one** description of this model and it is this file.

## Read this document in two layers, because they have different lifetimes

**Kind 1 — the durable record — is an INTERFACE. GitHub is one binding of it.** PR threads, Issues and the standup tracker are how this fleet implements Kind 1 today; every one of those is a GitHub fact, not a property of the interface. A component whose work product is not code in git — an edge device, a robot, a datacenter node — has no PR to comment on and no issue to close, and it still needs durable memory.

The split is not hypothetical here. **This fleet already runs two bindings** (§2.4): three surfaces are GitHub objects whose to-do bit is `open`, and one is a committed markdown table whose to-do bit is a `status:` column. Both satisfy the same five properties. Everything stated at the interface layer below already holds across a substrate change *that has happened*, not one that is imagined.

So every section that could be answered two ways answers both:

- **§1 (with §1.1–§1.2), §3.1, §5.1, §6.1 — the interface.** What any substrate must provide. A new substrate re-implements these.
- **§2, §3.2, §4, §5.2, §6.2 — this fleet's binding.** How GitHub (and the file surface) provides them today. A new substrate inherits none of this and must supply its own.
- **§7 — the seam between them**, and the only part that is neither: what a typed record would have to model to render this binding without losing what §1 property 3 requires.

§9 states the split as a single inherit-versus-re-implement table.

> **Kind 2 — the typed exit record** — is the machine-readable counterpart: emitted at exit on a channel the parent owns, read by code within seconds. It is **not built**; it is [Phase 3](../development/memory-management-framework/phase3_typed_exit_record.md) of the [Memory Management Framework](../development/memory-management-framework/roadmap.md). This document exists partly so Phase 3 knows exactly what Kind 1 carries — because under the arrangement Phase 3 adopts, anything the typed record does not model, the render loses. §7 enumerates what is at risk.

---

## 1 · The interface — five properties, stated without a substrate

A Kind 1 record is any record with all five. **No property below is stated in terms of GitHub, git, a file or a URL** — where those nouns appear it is as a contrast (what a substrate would otherwise need) or as a redirect to §7.3, never as part of what a property requires. That is the claim, and it is the one a grep can check.

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

Which record a given outcome goes to is decided by **two questions, in this order** — neither of which mentions a substrate:

1. **Did something change?** A changed-artifact outcome and a no-change outcome are different records, because they are read by different actors at different times: the first is read *now*, by whoever accepts or rejects the change; the second is read *later*, by whoever plans work.
2. **Does it have a single done-state?** An outcome that can be finished belongs to a record that closes. An outcome that is a *condition* — ongoing operating state, a multi-day migration, a live incident — has no done-state, so a closing record cannot hold it and it needs a record that persists and is pruned instead.

Those two questions produce exactly three classes, and this fleet's surfaces map onto them one-to-one (§2). **A fourth class exists and is a genuine one:** an outcome whose resolution is not work at all but a *ruling* — a preference, a priority, a commitment that no amount of further work would uncover. §2.4.

### 1.2 · The discipline that makes it work

Two rules, and they are the reason the model does not rot:

- **Every record is written by the actor that knows something and read by an actor that needs it. Nothing is written "for the record."** A record with no reader is not memory, it is exhaust — and it costs the reader of the *other* records their attention.
- **An account is not the artifact.** A summary, a decision log, a prior pass's prescription, an agent's finding — all are *claims about* the work, none of them are the work. Every reviewing actor is bound to verify against the artifact, and **to verify a pointer by fetching it, never by plausibility.**

---

## 2 · This fleet's binding — four surfaces

Three GitHub surfaces plus one file surface. They are not interchangeable, and collapsing any two of them is a recurring failure (§2.5).

| Surface | Holds | To-do bit | Lifecycle | Written by | Read by |
|---|---|---|---|---|---|
| **PR threads** | change-outcomes — what got built, the run's own decision log and reflection, and the `pr_review:` disposition ruling on it | PR `open` | closes at merge | every PR-producing workflow; `review-pr` posts the disposition comment | `/standup`, `review-pr.sh` (prior-pass detection), `review_pr_activities.py`, the operator |
| **Issues** | no-change outcomes — deferred work `review-pr` filed, and planning STOPs | issue `open` | filed → ruled → **closed** | `review-pr` (sole autonomous filer), `plan-new` / `plan-revision` (STOP issues), the operator | `/standup` (**and closes them**), every build child's prior-art search, the operator |
| **Standup tracker** | continuity — operating state, next moves, work in flight | per-line `state:` | **never closes**; items are **pruned** | `/standup` (sole automated writer), operator and PM sessions | `/standup`, the operator |
| **`direction.md`** | rulings only the operator can make — a real finding whose answer is a preference, not a fact | row `status: open` | appended → ruled → **rotated out** at 90 days | `plan-sprint` appends (V2 tree only); **`/standup` deletes rotated rows and corrects stale ones** (§2.3); **the operator alone sets `status`** | `/standup` (renders), `plan-sprint` (reads the ruling back via `candidates.md`), the operator |

### 2.1 · The selection rule, bound

Apply §1.1's two questions:

- **Something changed** → **PR thread**. The change and its ruling live together, and both die at merge because the change is then history.
- **Nothing changed, and it has a done-state** → **Issue**. It can be finished, so it must be able to close.
- **Nothing changed, and it has no done-state** → **standup tracker**. Operating state is a condition, not a task.
- **Nothing changed, and the resolution is a ruling rather than work** → **`direction.md`**. No amount of further work would produce the answer; only the operator can.

**That is the whole rule.** It is stated as a rule and not implied by examples on purpose: an example-driven table answers the cases someone thought of, and the failure mode here is always the case nobody thought of.

### 2.2 · Why the tracker is a GitHub issue anyway

**It is an issue only because of the substrate, and documenting it under the Issues surface would be a category error.** Several sessions edit it daily; one API call beats a branch and a merge conflict on the artifact least able to afford being stale. Its semantics are its own: it never closes, items flow through it, and **a tracker that grows month over month is failing** — that is a property of the framework, not a housekeeping note.

Two consequences bind every reader:

- **Exclude it from the open-issue enumeration.** It must not appear twice, and it must **never be aging-flagged** — a permanent artifact is not a stalled one.
- **Never apply the issue-disposition obligation to it.** That obligation binds a *container* that is supposed to close; the tracker's obligation binds each *line*. Merging the two taxonomies would require inventing a fifth exit for *pruned*, which is a schema violation and not a convenience.

### 2.3 · `/standup` is a WRITER, and the corrected record of that matters

**`/standup` writes on three of the four surfaces**, derived from its Stage 2 body rather than from its own § Rules summary — which is the distinction §1.2 is about, and getting it wrong is how the first two attempts at this paragraph were both undercounts:

| Write | Surface | Declared at |
|---|---|---|
| `gh issue edit <tracker> --body-file` — reconciles per-line `state:`, prunes `resolved` ≥14 days | standup tracker | `config/commands/standup.md:83`, `:107` |
| `gh issue close <N> --comment <evidence>` — closes an issue whose work it verified done | Issues | `:66`, `:69` |
| **deletes** a ruled row ≥90 days old whose reasoning is recorded downstream; **may correct** a row whose stated facts changed | **`direction.md`** | `:67`, `:105` |

Everything else it does is a read. **It never sets `status:`** — the ruling stays the operator's; what it does is rotate and repair.

**Two corrections are stacked here, and the second is the instructive one.** The original claim in `operations.md` and in [Phase 2](../development/memory-management-framework/phase2_kind1_framework.md)'s own gotchas — *"strictly read-only, including the tracker"* — was true before commits `1e7d6ce` and `88c4e81` and stale after them. **The replacement claim, "writes in exactly two places", was also wrong**, and it was wrong for a subtler reason: it was taken from `standup.md`'s § Rules summary of itself (`:174`), which undercounts its own Stage 2 table (`:67`). *An account is not the artifact* (§1.2) — and a command's summary of itself is an account. The consumer/writer map is what [Phase 4](../development/memory-management-framework/phase4_fleet_migration.md) verifies fleet-wide against, and a map that omits a writer is worse than no map.

**`standup.md` itself states its write set two contradictory ways** — `:3` forbids closing issues and editing files, `:66`/`:105`/`:174` direct exactly that. That is a live defect in a Kind 1 consumer; it is surfaced rather than fixed, because this phase documents what exists and does not edit prompts.

**Why the write exists, so it is not read as scope creep:** a reconciler that can see an item is finished but cannot say so re-reports that dead item every morning, forever. The write is what makes the read worth doing. **No autonomous *dispatch* writes to the tracker** — that remains true, and it is a different claim: `/standup` runs in an operator session, which is the human-in-the-loop.

### 2.4 · `direction.md` — the fourth surface, and the proof the interface is real

[`docs/standards/architecture/research/direction.md`](../standards/architecture/research/direction.md) is a committed markdown table of `D-NNN` rows. Check it against §1: durable (in git), human- and machine-readable (`/standup` parses it, `plan-sprint` reads rulings back), carries outcome *and* reasoning (`Recommendation` and `Why it matters`, one sentence each), has a to-do bit (`status: open`), addressable (`D-NNN`, never reused, never renumbered), survives context death. **Five for five.**

**And its to-do bit is not GitHub `open`.** It is a column in a file. Its lifecycle is not close-at-merge or filed-then-closed but **ruled-then-rotated**: a ruled row is a receipt, its durable reasoning goes back down into `candidates.md`, and the receipt is then deleted. Its appending writer is in the V2 Python tree, its rotating writer is a slash command, and neither may rule. **The rule itself is stated once, in the file** — [`direction.md` § Rotation](../standards/architecture/research/direction.md); this document cites it rather than re-typing it, for the same reason §4 cites the emitting script.

Nothing about that record is a GitHub fact. It is the same interface on a different substrate, **shipped, in daily use, in this repo** — which is why §1's five properties are a description and not an aspiration.

### 2.5 · Which two get collapsed, and what happens

Collapsing surfaces is the recurring failure, and it is not symmetric — one pair collapses far more often than the others.

**Issue ↔ tracker is the collapse that actually happens.** Both are GitHub issues; the substrate invites it. The failure is bidirectional and both directions have been observed:

- **Continuity filed as an issue** → it can never close, so it ages, gets flagged as stalled, and every standup asks the operator to dispose of something that is not disposable. The anti-rot flag fires on the one document designed to persist.
- **Deferred work parked in the tracker** → it loses the standing disposition obligation an issue carries (*an issue must not survive a standup in the same state*), so it becomes a line in a growing document that nobody rules on. **This is the carried-work-ledger shape, and this repo ran one for ten weeks:** two of its entries described work completed the same day the file was finally read, and one had a run flag six weeks earlier that its trigger had fired. A store that accepts anything gets read by nobody.

**PR thread ↔ Issue collapses in one direction only:** a run parking its own deferred work in its own PR body. That pointer dies at merge, which makes it the most effective burial available — the PR reads clean and the item stops existing. It is why `review-pr` holds the sole autonomous filing authority and why the reviewed PR is never a valid pointer.

**`direction.md` ↔ Issue** collapses when a ruling is filed as work. An issue asks *who will do this*; the row asks *what do we believe*. Filed as an issue it sits open and unactionable, because nobody can action a preference.

---

## 3 · What each surface holds, for how long, and who reads it

### 3.1 · At the interface layer

Three lifecycle shapes exist, and **a substrate must provide all three or the model does not fit on it**:

| Shape | To-do bit clears when | Record then |
|---|---|---|
| **Transactional** | the change is accepted or abandoned | becomes history; is not pruned, because the change it describes is permanent |
| **Task** | the work is done or ruled invalid | closes; remains retrievable by address |
| **Continuous** | *never* — the bit is per-item, not per-record | persists; individual items are pruned on an explicit schedule |

**The asymmetry is the point.** A substrate offering only closing records cannot hold continuity, and the work goes back to living in session context and dying at a session boundary. A substrate offering only persistent records cannot express *finished*, and every reader must re-verify every item.

**A continuous record needs a pruning rule or it is a ledger.** That is a property of the interface, not of GitHub: the bound on a never-closing record's size is the only thing standing between it and the carried-work shape in §2.5.

### 3.2 · Bound to this fleet

| Surface | Retention | Pruning rule | Growth failure signal |
|---|---|---|---|
| PR threads | permanent; closed at merge | none — history | thread size (§6.3) |
| Issues | until ruled; closed with evidence | none needed — closing *is* the bound | an issue surviving a standup in the same state |
| Standup tracker | permanent document, transient lines | `state: resolved` + ≥14 days → deleted from the body | month-over-month growth |
| `direction.md` | permanent file, transient rows | ruled ≥90 days ago **and** reasoning recorded in the source candidate → row deleted | rows accumulating unruled |

**`direction.md`'s pruning rule carries a precondition the others do not, and it is the interesting one:** a row rotates out *only once its reasoning lives somewhere that never deletes*. That is property 3 (outcome **and** reasoning) enforced at the deletion boundary — the receipt may go because the reasoning stayed. The rule's authoritative statement is in [`direction.md` § Rotation](../standards/architecture/research/direction.md); the row above is the consumer-map entry, not a second copy of it.

---

## 4 · The `pr_review:` block — this fleet's machine-facing half of the record

> **Binding layer, throughout.** §4 names scripts and line numbers on purpose; a different substrate inherits none of it. The word *interface* is not used below in §1's sense — this block is a **wire format**, which is a narrower thing.

`review-pr` posts one comment per pass with two parts: a human-readable disposition table, and a fenced `yaml` block keyed `pr_review:`. **The block is the machine-facing half of Kind 1 on this substrate**, and it is the record Phase 3's typed envelope will be rendered into or reconciled against.

> **The authoritative schema is the emitting prompt: [`scripts/workflows/children/review-pr.sh`](../../scripts/workflows/children/review-pr.sh) Stage 5, `:342-423`.** Per [Documentation Standard § Single-source codified fields](../standards/documentation/documentation_standard.md) the doc points and does not copy — field semantics, enums and absence rules live in that block and are not re-typed here. What follows is the thing that exists nowhere else: **the consumer map.**

**`pr_review:` is a WIRE FORMAT, not a filename.** Renaming the key orphans `/standup`'s parse, both pass-counters, cross-pass stable-id tracking, and every block already posted on a live PR (`review-pr.sh:46-53`).

### 4.1 · The consumer map — who reads what

Verified by grep across both fleets (`grep -rn "pr_review\|gh issue list\|gh pr list" scripts/ config/`), excluding prompt strings.

| Field | Read by | What the reader does with it |
|---|---|---|
| *block presence* | `review-pr.sh:141-142` (`PRIOR_PASS`) · `review_pr_activities.py:45-51` | counts prior passes → sets `THIS_PASS`. **Both over-match — see §6.4** |
| *block presence* | `replay_pr_review_blocks.py:45` | Phase 1 E3 + E7 corpus extraction |
| `verdict` | `/standup` `standup.md:48-51` | `HOLD` → render as a blocker; `MERGE` on an open PR → "ready to merge" |
| `next_steps[]` | `/standup` `standup.md:48-51` | delivered **verbatim** to the operator — the disposition engine already reasoned; standup does not re-derive |
| `pass` | *(human only)* | E7 measured it **non-dense** — #31 runs 1, 2, 4 — so "the previous pass" must come from block ordering, never from the integer |
| `findings[].id` | `replay_pr_review_blocks.py` | Phase 5's identity input. Convention measured to hold **25 of 25** on the added direction |
| `findings[].disposition` | `replay_pr_review_blocks.py` | partitions findings into open/closed. Present on **195 of 195** archived findings |

### 4.2 · Emitted and read by nobody — named, because naming them is more useful than documenting them as though they matter

Phase 1 E6 verified three keys have zero programmatic readers: **`converged`**, **`attempt`**, **`hold_kind`**. This pass extends that list from the emitting script; the rest of the block is human-facing today:

`pr`, `redispatched` (always `false` by contract), `laundered_deferrals.{caught,of_total}`, `homeless_items`, and per-finding `title`, `category`, `consequence`, `remedy`, `pointer`, `pointer_verified`, `reviewed_sha`, and per-next-step `item`, `kind`, `note`, `issue_url`, `issue_repo`, `qualified`, `dispatch_tool`, `dispatch_context`, `precheck`, `why_human`, `reframe`, `bp`, `recommendation`.

**"No programmatic reader" is not "no consumer."** `laundered_deferrals` is a CPI rate signal read by a human at review time; `reframe`/`bp`/`recommendation` are delivered verbatim to the operator by `/standup`. What the list means is narrower and more useful: **these fields cannot break a routing decision, so a schema change to any of them is a documentation problem, not an outage** (§5.2).

### 4.3 · Read but not reliably emitted — the live gap this comparison exists to find

**The routing token is not in the block.** Every parent branches on the prose line `VERDICT: MERGE | HOLD - redispatch | HOLD - needs-assistance` (`build.sh:277`, `build-minor.sh:281`, `routing.py:72`). The yaml carries `verdict: MERGE | HOLD` — **which cannot express the hold kind**, the very thing all four branch points need. The sub-kind exists only per-finding as `hold_kind`, which the model aggregates into the prose line by the rule at `review-pr.sh:434-438`.

**Consequence:** a consumer reading the durable record instead of the transient stdout — which is exactly what a later dispatch must do, since stdout is gone — **cannot recover the routing decision without re-aggregating it**, and re-aggregating means a caller with no stake in the review making a judgement about the review. Phase 1 E6 ruled this into the envelope as `hold_kind`, promoting a key with no code reader into one with four. Recorded here as the Kind 1 side of the same gap.

### 4.4 · Reconciled against Phase 1 E6 — and where this pass disagrees

**E6's "nine fields" is not an enumeration of this block, and reading it as one would be a mistake with consequences.** E6 enumerated the *Kind 2 envelope* — the union of values every parent branches on, derived from 15 branch sites. This section enumerates what `review-pr` *emits into Kind 1*. They are different sets with a small intersection:

| | count | derived from |
|---|---|---|
| E6's envelope | **9** | what parents read |
| `pr_review:` block | **~31 leaf fields** | what the reviewer writes |
| overlap | **4** — `verdict`≈`outcome`, `hold_kind`, `findings[].id`, `findings[].disposition` | — |

**The disagreement, stated as a finding:** E6's ruling is correct on its own terms and this pass takes nothing back from it. What the two sets together show is the actual shape of the problem — **the durable record carries roughly seven times what any machine reads, and the four fields machines do need are exactly the four the two sets share.** That ratio is not waste; it is §7's prose, and it is the cost of arrangement A stated as a number.

---

## 5 · What breaks if a field changes

### 5.1 · At the interface layer — the three changes that are never local

Independent of substrate, a Kind 1 record has exactly three change classes that reach beyond the record:

| Change | Blast radius | Why it is not local |
|---|---|---|
| **The to-do bit's name, location or value set** | every reader, unconditionally | It is the only field a reader must interpret to decide whether the record is current. Property 4 is what replaces the state file; changing it changes what "current" means fleet-wide |
| **The address** (§6.1) — the container id, the block marker, or the ordering rule | every *later* actor, silently | A retrieval that used to resolve now returns nothing, and **an absent record is indistinguishable from a record that says nothing was found.** This failure is quiet by construction |
| **A field's identity stability across revisions of the same record** | every cross-revision computation | If an identifier is reused for a different thing, or a stable thing gets a new identifier, every delta over that record is wrong and nothing fails loudly |

**Everything else is local.** A field with a named consumer breaks that consumer, loudly, at its next run. **The rule that keeps it that way: a field enters a Kind 1 record with a named consumer, or it is prose** — and prose is §7's problem, not this section's.

### 5.2 · Bound to this fleet — the check-list a schema change runs against

| If you change… | Check | Breaks how |
|---|---|---|
| the key `pr_review:` | `review-pr.sh:142`, `review_pr_activities.py:51`, `replay_pr_review_blocks.py:45`, `/standup` `standup.md:48-51`, **every block already posted** | pass-counting silently resets to zero; standup reports every PR as "awaiting review" |
| `verdict`'s value set | `/standup` `standup.md:48-51` | a value standup does not recognise renders as neither blocker nor ready — it vanishes from the brief |
| `next_steps[]`'s shape | `/standup` `standup.md:48-51` | the runway stops reaching the operator; `review-pr` still writes it, nobody delivers it |
| `findings[].id` stability | `replay_pr_review_blocks.py`, [Phase 5](../development/memory-management-framework/phase5_convergence_stopping.md) | the convergence predicate reads a false delta. **Silent** |
| `findings[].disposition`'s enum | same | a value outside the **archive's measured vocabulary** — `{hold, fixed, deferred, rejected, noted, escalated}`, counted across all 195 archived findings ([Phase 1](../development/memory-management-framework/phase1_measure_the_channel.md) E7) — is scored as *open* by the closed-set reading, so the open set can never empty. **Silent.** Note this is the set a replaying reader must handle, **not** the set the emitter declares: `review-pr.sh:361` declares four (`fixed \| rejected \| deferred \| hold`), and `noted` / `escalated` reach the archive from earlier passes. **Narrowing the emitter does not narrow the archive** |
| the prose `VERDICT:` line | `build.sh:277`, `build-minor.sh:281`, `routing.py:72`, `run-claude.sh:201-204` | the parent's completion gate fails loud (child side) or synthesises `HOLD - needs-assistance` (parent side) |
| anything in §4.2 | no code | nothing breaks; **a human loses information and nothing tells them** |
| the tracker's section order or per-line fields | `/standup` `standup.md:39` | the readiness ordering (`BLOCKED`→`READY`→`IN FLIGHT`→`RESOLVED`) is how the operator triages; normalising it destroys the property |
| `direction.md`'s `status` value set | `/standup` `standup.md:43`, `:143`, `:105` (rotation) | a row with an unrecognised status renders forever or never |

**The two silent rows are the ones that matter.** Both are in the convergence path, both fail by producing a wrong answer rather than no answer, and neither has a consumer that would notice. They are the reason [Phase 4](../development/memory-management-framework/phase4_fleet_migration.md) verifies fleet-wide against this list rather than against the emitting script.

---

## 6 · Retrievability — the addressing convention

**This is the half of the interface nobody had written down.** A surface a later actor cannot *address* is a surface only a human can read, which is the gap the whole [Memory Management Framework](../development/memory-management-framework/roadmap.md) exists to close.

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
| Block marker | a fenced ```` ```yaml ```` block whose **first line is `pr_review:`** | `review-pr.sh:342-344` (emitter); `replay_pr_review_blocks.py:45` (the only executable statement of it) |
| Ordering rule | comment creation order on the thread; **last wins** | `/standup` `standup.md:48` — *"the LATEST comment containing a `pr_review:` yaml block"* |
| Sequence number | the block's `pass:` key, written by the producer | `review-pr.sh:346`; counter at `:141-143` |

For the other three surfaces the address is simpler and complete: **Issues** — `owner/repo#N`, one record per container, no ordering needed. **Tracker** — discovered *by title* (`standup-tracker in:title`), never by number, so it stays portable across repos; per-line `id` inside. **`direction.md`** — `D-NNN`, never reused, never renumbered, plus the source `C-NNN` linking it to `candidates.md`.

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
| `review_pr_activities.py:51` | `"pr_review:" in body` — plain substring | **18** |
| `replay_pr_review_blocks.py:45` | fence-anchored regex requiring an actual ```` ```yaml ```` block | **15** |

**Measured at `bcdb519` over all 39 PRs: 3 false positives, on 2 of the 8 PRs that carry any block.** Both pass-counters match any comment that merely *mentions* the string — a Post-Run Reflection, a build-refine summary, a brief quoting the wire format.

The consequence is not hypothetical; it is in the archive:

- **PR #31** — comments carry blocks at `pass: 1`, `pass: 2`, then `pass: 4`. The comment between them is a `build-refine` reconciliation note with no block. It was counted. **There was never a pass 3.**
- **PR #66** — one block, labelled `pass: 3`. The two comments before it are the build-draft and build-refine reflections. **It is pass 1.**

**This changes something Phase 1 recorded as structural.** [Phase 1](../development/memory-management-framework/phase1_measure_the_channel.md) E7 § *Two structural facts Phase 5 needs and the archive does not advertise*, item 1, states *"pass numbers are not dense"* and instructs Phase 5 to derive consecutiveness from block ordering rather than the integer. That instruction is correct and should stand — but the *reason* given, that non-density is a property of the archive, is wrong: **it is this over-match, and it is fixable.** §6.1's rule that ordering outranks a written counter is the general form of the same lesson.

**The record written into Kind 1 is wrong in both cases** — `pass:` is a durable field of the durable record, and it is off by two on the most recently reviewed PR in the repo. Phase 2 documents the convention and names the defect; **it does not fix it** — this phase documents what exists, and the remedy is a code change in two files.

### 6.5 · Cross-reference — the CPI deferral this section closes

[`cpi-decisions.md`](../development/cpi-decisions.md) § *DEFERRED — a correction pass cannot machine-read the prior pass's runway* (2026-08-07) carries the watch-criteria **"ship as part of the Memory Management phase doc, or immediately if a correction pass MISREADS a runway."** That trigger fired; §6.1–6.4 are where it lands. The deferral's second clause is worth reading against §6.4: it distinguished *paging 37 KB and getting it right* from *acting on the wrong prior finding*. The over-match is the second class — not a wrong finding, but a wrong pass number written durably — and it is recorded rather than treated as the smaller problem.

---

## 7 · The seam Kind 2 attaches to — rendered output versus authored prose

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

**Any rule this document implies should become binding is surfaced as a standards-amendment candidate in the [Memory Management Framework roadmap](../development/memory-management-framework/roadmap.md), never written into `docs/standards/`.**

---

## 9 · Inherit versus re-implement — what a different substrate is actually signing up for

The question this table answers: *a new component's work product is not code in git — what does it get for free, and what must it build?*

| | Inherited — substrate-independent | Re-implemented — this fleet's binding |
|---|---|---|
| **Contract** | §1's five properties | — |
| **Selection** | §1.1's two questions; the three outcome classes plus the ruling class | §2.1's mapping onto PR / Issue / tracker / `direction.md` |
| **Lifecycles** | §3.1's three shapes; the rule that a continuous record needs a pruning bound | §3.2's specific retentions and thresholds (merge, close, 14 days, 90 days) |
| **To-do bit** | that there is one, on the record, binary | that it is GitHub `open` — **and note this fleet already has an exception**: `direction.md`'s is a `status:` column (§2.4) |
| **Change safety** | §5.1's three non-local change classes | §5.2's per-field consumer list |
| **Address** | §6.1's four parts, and that sequence derives from ordering | §6.2's PR number / yaml fence / comment order / `pass:` key |
| **Discipline** | §1.2 — written by an actor that knows, read by an actor that needs; an account is not the artifact | the specific fetch commands that verify a pointer — **not stated here**; they live in `engineering-quality.md` § *A deferral is PLACED* and in each workflow's own prompt (§8) |
| **The seam** | that authored reasoning exists and must be modelled or consciously dropped | §7.2's fourteen specific items, which are `review-pr`-shaped |

**Read the right column as the migration cost.** It is four rows of mechanism and one row of enumeration — and none of the left column moves. That is the claim the split was made to support, and §2.4 is the instance that already tested it.
