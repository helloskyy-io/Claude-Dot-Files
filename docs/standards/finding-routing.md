# Finding Routing Standard

**This document owns one question end to end: a run — or a human — has found something. Where does it go?**

It exists because that question had no owner. The rules lived in six documents, four local and two mirrored, and they disagreed at the seams. **Every section marked `INTERFACE` is general and is a candidate for upstream promotion to `MDC-Master-Planning`; every section marked `BINDING` is this repo's own and never promotes.** That split is deliberate — it is the same interface-versus-binding discipline [`memory-model.md`](../guide/memory-model.md) applies to the working record, applied one level up.

**Where this and a mirrored standard overlap, the mirrored one wins** and this document cites rather than restates it. See §6.

---

## 0 · The measured problem this exists to solve

Not a hypothesis. Across two repos in three days:

- **18 issues filed, two full working days spent triaging them, zero days of development.** That ratio is the defect, not any individual issue.
- **None was fabricated and none was wrong on the facts.** Roughly half were **real findings in the wrong container**.
- In this repo, **10 issues in one day**; on classification, **4 of 12 were proposals rather than defects**, and **2 of those 4 were filed by the operator's own interactive session** — so this binds humans, not only dispatches.
- **Four issues against one file, from one pass, in one minute**, each individually correct.
- Two issues describing **one mechanism with zero shared vocabulary**: *"credential-interpolation defect"* and *"adoption coordinates self-authorised by value shape."* No keyword search connects them.

**The correct reading, and it governs every rule below: we are not asking for fewer findings. We are asking for fewer containers.** A filer made more conservative loses real defects and keeps the misplaced ones.

---

## 1 · `INTERFACE` — What a finding is, and the four classes

A **finding** is anything an actor concludes that it is not going to act on immediately in the work at hand. Every finding is exactly one of:

| Class | Definition | Goes to |
|---|---|---|
| **DEFECT** | Something already built or already decided **behaves wrongly** — or a decision the existing research and planning do not supply is now **blocking** | the issue queue (§3) |
| **PROPOSAL** | **Capability that does not exist** and would be *added* | the proposal queue (§3) |
| **RULING** | The resolution is a **preference or a commitment**, not work. No amount of further work produces the answer | a **candidate carrying `decision: requires review`** (§3) |
| **OPERATING STATE** | A **condition** rather than a task — ongoing, multi-day, no single done-state | the continuity surface (§3) |

**A finding that is not one of these four is not a finding.** It is an observation, and observations belong in the run's own report where they die with it, which is correct.

## 2 · `INTERFACE` — Question 0: defect or proposal, and it comes FIRST

**Ask this before any other routing question.**

**Why first, and this is measured rather than asserted:** a proposal answers *"nothing changed"* and *"yes, it has a done-state"* — *"add a link checker"* has a perfectly clean done-state. **Any rule keyed on those two properties files a proposal as a defect**, not by being misread but by working as written. That is exactly what happened here, and it is why a third of a queue was capability.

**Bias toward PROPOSAL when a finding reads either way.** The costs are asymmetric and known: a proposal misfiled as a proposal costs a triage pass; a proposal misfiled as a defect costs an operator's day.

**"We have no test for X" is not a defect in X.** X may be perfectly correct — the finding is that coverage is missing, and coverage is capability.

**No actor is expected to know where a proposal belongs in the plan** — sprint, phase, or nothing. Only that it *is* a proposal. Deciding the rest is separate triage with its own criteria, and demanding it inline is what produces proposals filed as defects.

## 3 · `INTERFACE` — The selection rule

Question 0 first. Then, for a **defect**:

- **Something changed** → the **change record** (a PR thread). It and its ruling die together at merge, because the change is then history.
- **Nothing changed, and it has a done-state** → the **issue queue**. It can be finished, so it must be able to close.
- **Nothing changed, and it has no done-state** → the **continuity surface**. Operating state is a condition, not a task.
- **Nothing changed, and the resolution is a ruling rather than work** → the **ruling queue**.

**That is the whole rule.** It is stated as a rule and not as a table of examples on purpose: an example-driven table answers the cases someone thought of, and the failure here is always the case nobody thought of.

## 4 · `INTERFACE` — A surface has an AUTHORITY and a MECHANISM, and both must be checked

**This section is the one whose absence orphaned three findings**, and it is the part most likely to be missing from any standard that predates it.

**Naming an actor as the writer of a surface is not sufficient. The actor must also be ABLE to write it by the mechanism that surface requires.**

**THREE mechanisms exist** and they are not interchangeable:

| Mechanism | What it needs | Who can |
|---|---|---|
| **API** — a PR comment | a token. **No worktree, no branch, no commit, no push** | any run, including a decide-only reviewer |
| **COMMIT** — any file in the repo | an edit, a commit **and a push** | only a run that produces a PR |
| **INTAKE** — an API write a named cadence converts into a COMMIT | a token to file; a harvest to land it | **any run**, and it is what makes a decide-only reviewer able to reach a file surface |

**A decide-only reviewer can write an API surface and structurally cannot write a file surface.** Routing a class of finding to a file surface while naming the reviewer as its writer produces findings that are correctly classified, correctly refused entry to the wrong queue, and then have nowhere to go. **Measured: three proposals, correctly identified, stranded in a PR body — which is a grave.**

> **THE THIRD MECHANISM EXISTS BECAUSE THIS SECTION'S PROBLEM GOT WORSE BEFORE IT GOT SOLVED.** When every tracked store became a file (Tracked Items Standard §5, 2026-08-25), the API escape hatch this section describes stopped existing for any class at all, and `review-pr` — the largest producer of findings here — could place *nothing*. **INTAKE is the resolution, and it is bounded rather than a loophole:** [§5.0](documentation/tracked_items_standard.md) exempts an intake issue from the retirement **on condition that a named cadence empties it**. An intake nobody drains is a second store, which §8 there calls a violation rather than a grey area. **So an INTAKE row is only honest while its harvest is named** — ours is `scripts/helpers/harvest-intake.py`, run by `/standup`.

**So every routing rule states the mechanism alongside the writer, and any rule that names a writer without checking the mechanism is incomplete.**

### `INTERFACE` — the disposal-chute argument is DEFECT-SPECIFIC

Filing authority for **defects** sits with the reviewer, not the discoverer, and the reasoning is sound: *"a run that can file its own deferrals has a disposal chute for its own scope — file it, move on, the PR looks clean."*

**That argument does not reach proposals.** A proposal is capability that does not exist, so **by construction it is not work the run was asked to do and not scope it could be dodging.** The asymmetry the rule rests on is simply absent.

**Therefore: a producing run MAY place its own proposals, in its own PR.** It has the commit mechanism, the proposal lands in the same artifact the human reviews, and the reviewer retains the authority that matters — **ruling whether the classification was right**, and holding the PR if a proposal was a defect in disguise.

## 5 · `INTERFACE` — The gates, in order, before anything is filed

**0 · IS THIS ABOUT THE WORK IN HAND? Then THREE dispositions exist and the rest are UNREACHABLE.**

**This is not a criterion. It is a closed list.**

| Disposition | When |
|---|---|
| **`fixed`** | you corrected it |
| **`rejected`** | it is not a real defect — state the reasoning that makes it not one |
| **`hold`** | it is real and you are not fixing it here: `redispatch` (a correction pass fixes it) or `needs_ruling` (only a human can decide) |

**A REVIEWER'S ITEM IS NOT AUTOMATICALLY ONE FINDING. When its OBSERVATION is right and its PROPOSED REMEDY is wrong, that is TWO findings and both get recorded** — the observation takes `fixed` or `hold`, the remedy takes `rejected` with the reasoning that makes it the wrong fix. **Do not average them into one disposition**: `fixed` alone hides that you declined the reviewer's approach, and `rejected` alone reads as denying a real defect. *(Stated 2026-08-14.)*

The list of dispositions above is closed; the number of findings a reviewer's paragraph contains is not.

**`deferred`, `noted`, `escalated` and `surfaced` DO NOT EXIST for this class.** Not discouraged, not a last resort — absent. **A finding about the work in hand is never a new issue, never a candidate, and never someone else's queue item.** It is fixed, rejected with reasoning, or held.

**What counts as "the work in hand":**

- an artifact this dispatch **created or edited**, including one it created *correctly but incompletely*
- a commit made **to unblock** this dispatch
- **output this dispatch produced** that does not conform to a rule binding it

*"I noticed X while doing Y"* is not enough — the question is whether **X is part of Y**.

**WHY THE LIST IS CLOSED RATHER THAN GUIDED, and this is the part to understand rather than obey.** Six versions of this rule have been written as criteria and all six leaked, because **the incentives run the other way and criteria do not beat incentives.** A run works under a turn cap: filing a finding costs one line, fixing it costs the rest of the budget. Every time the vocabulary offers an exit, a run under pressure takes it — not from laziness, but because the exit was reachable and looked legitimate. **The only fix that has ever worked on this class is removing the outcome, not adding a condition on it.**

**And the cost of the exit is specific: the work that produced the gap merges, and the gap becomes a queue item nobody owns.** The dispatch had the context, the files open, and the authority. A later actor has none of the three and must rebuild all of them — which is why *"file it and move on"* is not a transfer of work but a multiplication of it.

**Every finding MUST name the artifact it is about**, so this is computable rather than judged: a finding whose artifact appears in this change's own diff has three dispositions available and no others. Stating the artifact is what turns this rule from the seventh attempt into an enforceable one.

**THE ONE CARVE-OUT.** If the owning work has **already merged**, it cannot be given a runway. Route to whatever is next touching that artifact; a new container is legitimate **only** when there is genuinely no open work that owns it — and *"the owner merged"* is a fact you state, not a conclusion you reach because fixing looked expensive.

---

**Everything below applies ONLY to a finding that is NOT about the work in hand** — a defect in something that already existed and this change did not touch.

**1 · CLUSTER YOUR OWN FINDINGS FIRST.** Before searching anything. Searching a queue cannot find what does not exist yet — the measured case was four issues against one file from one pass, each individually correct and none findable by the others. **Findings sharing a file, a function, a subsystem, or one remedy are ONE entry.**

**2 · SEARCH BY MECHANISM, NOT BY KEYWORD, ACROSS EVERY REPO THE WORK SPANS.** Two findings can be the same defect and share no vocabulary. Ask *"is this the same MECHANISM as something already filed, in different code?"* — not *"do the words match?"* Deferred work lives in more than one repo; a single-repo search that correctly finds nothing is not evidence of novelty.

**3 · FIX IT HERE, FIRST — this rung exists because a ladder whose every rung points outward IS an exit.**

**Before any of the destinations below, ask whether you can simply do it now.** Not *"is it small enough"* — that gate already exists elsewhere and it is the wrong question. Ask: **you have the files open, the context loaded and the authority; what does routing this cost that doing it does not?**

**The MDC side found this in their own ladder and the generalisation is theirs:** *"A vocabulary with no reachable exit is necessary and not sufficient. A routing ladder whose every rung points outward is itself an exit, regardless of what the vocabulary permits — the run does not need a word for* defer *if every question it is told to ask hands it a container."*

Their ladder had seven rungs and **every one routed outward**; the nearest thing to a fix-it rung gated on **small** rather than on **ownership**, so a not-small finding about the work in hand fell into the machinery and landed in a container **correctly, by a ladder with no other answer.** Ours had the same shape: four destinations, all outward.

**A finding you fix costs one edit. A finding you route costs a container, a triage, a re-read, and a context rebuild by someone who never had the files open.**

**4 · FOUR DESTINATIONS, and a new container is the last:**
   - **same mechanism as an existing entry** → **expand it**
   - **belongs to a standard's owner** → **route it** as an amendment candidate; do not track it as work
   - **no planning home exists for this area** → **the missing home IS the finding**; surface that, not the instance
   - **an existing deferral's PREMISE has been reversed** → **re-open it**. A pointer that resolves is not enough if the assumption under it is dead

**5 · THE LENSES.** Run `/decide` and `/best-practices` on whatever survives, and **state both verdicts in the entry.** Three outcomes:
   - **DISSOLVED** — file nothing; record the verdict so a later pass does not re-derive it
   - **RESOLVED INTO A KNOWN FIX** — **re-disposition as fix-in-place and file nothing.** This is the outcome to reach for: the lenses exist to convert human decisions into known answers, and a converted finding costs one automated pass instead of an operator's attention
   - **SURVIVES BOTH** — file it. It has earned a human

**A finding that has not been through all four gates has not earned a container.**

## 6 · Where the mirrored standards bind — cited, never restated

These are **vendored MIRROR** copies. **They win where they overlap this document**, and they are cited here so a re-vendor cannot silently contradict us:

- [`documentation_standard.md` § Deferred Work](documentation/documentation_standard.md) — *Filing authority* (who may file a defect as an issue, and why the reviewer rather than the discoverer) and *Placement* (phase checkbox first, issue second; decide from the body, never the title).
- [`research_standard.md` § Action candidates have a HOME](research/research_standard.md) — the routing table for a **research synthesis's** candidates, and the rule that *"the research run surfaces candidates in its synthesis and writes nothing outside `research/`."* **Research does not author standards; it recommends them.**

- [`tracked_items_standard.md`](documentation/tracked_items_standard.md) — **the four stores themselves**: identity (§2), the shared core every item carries (§3), recurrence via `count` (§3.1), the admission tests (§1), the DEFECT-vs-PROPOSAL discriminator (§1.1), and the INTAKE exemption (§5.0) that §4 above depends on.

> **BOTH KNOWN GAPS ARE NOW CLOSED UPSTREAM, and this note is kept rather than deleted because the prediction is the useful part.** This section used to read: *"their routing has no row for a proposal surfaced by a non-research run, and their filing authority is stated in terms of who without asking by what mechanism."* The Tracked Items Standard closes the first (§1 names builds and autonomous dispatches as candidate filers) and §5.0 closes the second (the mechanism is named, and bounded by a cadence). **§4 and §5 here were written as the answer pending ratification; they were ratified.** What remains local is the surface list in §7, which is what this document says never promotes.

## 7 · `BINDING` — this repo's surfaces

**Local. Never promotes upstream.** Another ecosystem implements the same four classes on whatever surfaces it has.

| Class | Surface | Mechanism | Who writes it |
|---|---|---|---|
| change record | PR thread | **API** | every PR-producing run; `review-pr` posts the disposition |
| **DEFECT** | [`tracked/issues/`](../../tracked/issues/) | **COMMIT**, or **INTAKE** | **`review-pr` only.** A PR-producing run never files its own defect — that is the disposal chute below |
| **PROPOSAL** | [`tracked/candidates/`](../../tracked/candidates/) | **COMMIT**, or **INTAKE** | the **producing run**, in its own PR (§4). `review-pr` by intake **only** for a proposal the run never surfaced |
| **STANDARDS AMENDMENT** | [`tracked/standards/`](../../tracked/standards/) | **COMMIT**, or **INTAKE** | any run that surfaces one. **Filing is surfacing, not editing** — Governance permits it. `ratification` is the operator's alone |
| **OPERATING STATE** | [`tracked/operations/`](../../tracked/operations/) | **COMMIT** | **operator and PM sessions only** — no autonomous run, ever (Tracked Items §1.2) |

> **THE RULING CLASS HAS NO SURFACE OF ITS OWN, AND THAT IS THE 2026-08-26 CORRECTION.** It had one: `direction.md`, a table beside the research pool with its own `D-NNN` series. **Deleted.** Every row it held pointed at a source candidate that still existed carrying `decision: requires review, status: open` — which IS the signal "a human owes a ruling", in a store that already has a triage cadence and a named runner. The second surface added an id and nothing else, and in three weeks **nobody ruled a single row on it**: it had a reader (`/standup` rotated it) and no ruler, which is [§0](documentation/tracked_items_standard.md)'s second property failing in the open. **A `requires review` candidate IS the ruling queue.** Do not give this class a surface again; §8 names a second surface for a class that already has one as a violation.
>
> **A FIFTH CLASS, AND §6 PREDICTED IT.** The four classes in §2 had no row for a proposed amendment to a **named standard**, and §6 recorded the consequence as a known gap: Governance permitted an autonomous run to *surface* one while forbidding it to edit a standard, and there was nowhere for the surfacing to land. `tracked/standards/` is that destination, and the class is now first-class rather than a defect wearing the wrong label.
>
> **Every surface here moved from an API to a file on 2026-08-26**, which is why the mechanism column now carries two values per row. The COMMIT half is for a run that produces a PR; the INTAKE half is for one that does not. **`tracked/operations/` deliberately has no INTAKE half** — it is human-only, so there is no autonomous path to provide.

**`decision` on a candidate is `triage-candidates`'s output alone.** A run that places a proposal leaves it blank: blank means untriaged, which is the truth.

> **This authority was `plan-sprint`'s until 2026-08-12, and it MOVED — it did not widen.** `plan-sprint` did two jobs in one run, triaging candidates and maintaining the sprint plan, with nothing able to sequence between them; `triage-candidates` is the triage half split out. The `decision` column and the `direction.md` append went with the job, `plan-sprint` kept `sprint.md`, and **`plan-sprint` may no longer write `decision` at all** — its runner reads the column before and after and fails the run if any ruling changed. Exactly one workflow writes each surface, which is the property that mattered and the one thing the split had to preserve.
>

## 8 · Breaking it looks like

- An issue proposing capability that does not exist
- A second issue describing the same mechanism as an existing one in different words
- Several issues from one pass against one file or one function
- A proposal parked on the continuity surface, whose own rules forbid it
- A finding routed to a surface its named writer cannot mechanically write
- A new container opened without the four gates, or without both lens verdicts recorded
- A run declining to place a proposal because no actor is permitted to — **that is a defect in this standard, and it is filed against this standard**

---

## Provenance and promotion

Authored 2026-08-09 in `claude-dot-files` from measured failures in this repo and in `skyy-command` / `MDC-Master-Planning`. **Sections marked `INTERFACE` are offered for ratification into `MDC-Master-Planning` and re-vendoring here as a MIRROR**, at which point §7 stays behind as the local applicability note — the shape [`testing/README.md`](testing/README.md) already uses.

**Until that lands this document is local and editable.** After it lands, the `INTERFACE` half becomes read-only and amendments go upstream.
