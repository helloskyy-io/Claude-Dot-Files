# Every producer names its consumer

**Component:** [Workflow Decomposition](roadmap.md) · **Status:** not started · **Gate:** none live — the mechanism it generalises is already running in one directory

> **This phase was split out of [Nothing a run relies on is invisible](phase4_nothing_invisible.md) on 2026-08-28, and it is where that phase's *produced* half went.** It is not new work: requirements 1 and 3 below are carried verbatim from that phase's requirements 4 and 5, and requirement 5 carries the second clause of its requirement 6. **The number is 6 because it is the next free one** — [Nothing a run relies on is invisible](phase4_nothing_invisible.md) keeps its number and its filename, since a number is identity and never rollout order. See [`roadmap.md`](roadmap.md) § *Phases*.
>
> **Why the split, in one sentence:** [Nothing a run relies on is invisible](phase4_nothing_invisible.md)'s outcome could only be stated with the word *and* — *a wrong derivation is visible before it costs anything* **and** *a producer with no consumer turns the suite red* — so whichever half finished first could not be shown as finished. Full reasoning and its recurrence history: [`C-v4k9pz2h`](../../../tracked/candidates/C-v4k9pz2h.md).

## What this phase does

Decomposition multiplies the number of surfaces a run emits. Each child returns a result, each parent writes observables, each measurement tool prints an answer, each store accepts an item. **A surface written by one part of the system and read by no other part is not neutral:** it costs the run that produces it, it looks like coverage to a reader, and nothing goes red when it stops being correct — because nothing was ever checking.

That has happened here, measured twice. **Three parent-written observables shipped with no reader at all.** And the directory that governs measurement tools stated its own *"a `Read by` column with nothing in it is a finding"* rule in prose, one level up from the tools it governs — **nothing enforced it, and a tool shipped unread anyway.**

A gate exists for exactly one directory. This phase decides what the rule actually is, rules the fleet's surfaces against it, and extends the gate to the ones that qualify — then proves it by breaking it on purpose.

**Terms used here.** A **producer** is something a run writes that another part of the system is meant to read. A **consumer** is the named thing that reads it. A **cadence** is a stated schedule on which the consumer is invoked, and a **named runner** is who or what invokes it. A **declaration module** is code that defines a surface's shape without producing anything itself. A **gate** is a test that fails when a producer has no conformant consumer.

---

## Requirements for completion

1. **"Producer" is defined**, in a sentence a check can be built from, and the definition names what it deliberately excludes. *(Carried verbatim from [Nothing a run relies on is invisible](phase4_nothing_invisible.md) requirement 4.)* **This requirement stays unchecked and the definition does not exist as a check today** — what changed since it was written is that it no longer has to be invented from priors. See § *The stores supplied the definition this phase was missing*.

2. **The definition gives an explicitly-ruled answer for a surface whose named reader is invoked ON DEMAND**, with no cadence and no termination. **This requirement stays UNCHECKED and this plan does not rule it** — it is an input to the build, named here at the phase that consumes it, because ruling it from a planning run would be deciding a design question on one instance. [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md)'s two-bag reader is the named test case. **Both phase docs USED TO hold that pairing up as the exemplar of doing it right; both were corrected in place on 2026-08-28** and now name it as this phase's test case. See § *The fifth shape, and why this plan does not rule it*.

3. **The gate reaches producers outside `scripts/helpers/measure/`**, with the population read **off disk, never off a hand-kept list**, and **every exclusion named and asserted** by name in the check itself. *(Carried verbatim from [Nothing a run relies on is invisible](phase4_nothing_invisible.md) requirement 5.)* The first extension target is named rather than left as a direction — see § *The first extension target, counted off disk*.

4. **`tracked/operations/` is excluded by name, with the exclusion asserted in the check** and the reason recorded beside it. Its consumer is a human, no autonomous run may write to it, and **no check can assert that a person read something.** See § *The one exclusion the stores force*.

5. **An unread producer is DEMONSTRATED to turn the suite red.** Add a producer with no named consumer and watch it fail; add one whose consumer cell is empty and watch that fail too. Requirements 1–4 are not complete without it, and none of it is asserted from reading the code.

**Requirement 2 is this phase's one open question and it is deliberately left open.** Both answers are defensible — the cadence clause may be required only of surfaces that *accumulate*, leaving an on-demand reader conformant; or an on-demand reader may be non-conformant, in which case [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md)'s reader needs a stated invoker. **What is not defensible is discovering the question while building the second of the two phases**, which is why it is a requirement here rather than a note.

---

## Dependencies

- **[Nothing a run relies on is invisible](phase4_nothing_invisible.md)** — sibling, not a gate. That phase's echo is itself a producer, and this gate is what should catch it if it is ever removed. Neither blocks the other.
- **[What configuration a run absorbed](phase5_configuration_a_run_absorbed.md) — not a gate, but this phase is deliberately sequenced AFTER it.** That phase ships one producer and one consumer in the same phase, which is the shape this gate exists to keep honest when the two halves are *not* planned together. **Rolling out second means the on-demand shape requirement 2 must rule on exists in the tree as a worked instance rather than as a hypothetical.** See § *The fifth shape*.
- **[Tracked Items Standard](../../standards/documentation/tracked_items_standard.md) — read-only, and vendored.** This phase borrows §0's property as a definition and rules the fleet against it. It does not amend the standard, and it does not own the stores, their triage or their cadences. Amendments go upstream.
- **Nothing outside this component.** No sibling component and no external system gates this.

---

## What this phase decides

### The stores supplied the definition this phase was missing

When the produced half was planned on 2026-08-18 it rested on priors plus two local occurrences of one shape, and its central deliverable — a definition of *producer* — had no first-party referent at all. **The four tracked stores landed on 2026-08-26 and supplied one.** That does not make requirement 1 done. It makes it *a ruling against a written property* instead of *an invention*.

**The property, stated by somebody else and ratified.** [Tracked Items Standard §0](../../standards/documentation/tracked_items_standard.md) names three things every store must have, and calls a store missing any of them out of conformance:

1. **An admission test** — a stated rule for what does NOT belong.
2. **A triage cadence with a named runner.**
3. **An exit** — every item reaches a terminal state.

**That is the produced half's definition with the cadence added, and the cadence is the part the measure-tool version was missing.** The existing gate asks *does a reader exist*. §0 asks *does something empty this, on a schedule, run by someone named*. **A surface with a reader nobody runs is the failure this phase exists to catch, and only the second question sees it.**

**The fleet already carries a worked instance, in code, with its reasoning attached.** `modules/assistant/tracked/intake.py`'s docstring states the three conditions of Tracked Items §5.0 as the whole of the exemption that lets an intake surface exist at all — *"A named harvest cadence exists. `harvest()` is it, and `/standup` calls it. An intake with no harvest is a second store and a §8 violation."* — and says the module is built to keep them true rather than to assume them.

**So the candidate sentence a check can be built from is:** *a producer is a surface something else is meant to read; it is conformant when its reader is named, the reader is invoked on a named cadence, and the surface empties or terminates.* **Requirement 2 is the reason that sentence is a candidate rather than the answer.**

### The fifth shape, and why this plan does not rule it

The definition above is **strictly stronger** than the one the shapes below were originally ruled against, which asked only whether a reader was named. **Apply the stronger one to [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md)'s deliverable and it fails.** The sixth `Journal-` tag is the producer; the two-bag comparison reader is the consumer. The reader is **named** ✅. It is invoked on a **named cadence** ❌ — nothing schedules it; a person runs it when two runs are suspected to disagree. The surface **empties or terminates** ❌ — bags accumulate and are never edited after sealing.

**That is the pairing both phase docs USED TO cite as the exemplar of doing it right.** Both sentences were written against the weaker definition, and **both were corrected in place on 2026-08-28** — [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md) § *Notes and gotchas* and [Nothing a run relies on is invisible](phase4_nothing_invisible.md) § *Dependencies* now name the pairing as this phase's unruled test case rather than its exemplar. **The correction is to the record, not to the requirement: the shape below still needs ruling, and requirement 2 stays unchecked.** Source: [`C-k3nd8vwp`](../../../tracked/candidates/C-k3nd8vwp.md), reached by a cold read.

The shapes to rule on, and the fifth is the one nothing covers:

| Shape | Example | Ruling |
|---|---|---|
| A tool that answers a question | the `measure/` tools | **in** — the existing population |
| A record a run writes for a later run | a run bag's tags, a typed exit record | **probably in**, and this is where the real value is |
| A declaration module | code defining a surface's shape, loaded rather than run | **out, by name** |
| A surface whose only legitimate consumer is a human | [`tracked/operations/`](../../../tracked/operations/) | **out, by name** — see below |
| **A surface read ON DEMAND by a named machine reader** | **[What configuration a run absorbed](phase5_configuration_a_run_absorbed.md)'s two-bag reader** | **UNRULED — requirement 2** |

**Why §0's own wording does not settle it.** §0's three properties govern **stores** — surfaces that accumulate items awaiting a decision — and its exit clause is about items reaching a terminal state. This phase generalises them to **producers**, a wider class that includes surfaces nothing accumulates in. The generalisation is a good one and requirement 2 does not reopen it; the gap is that the wider class contains a member the narrower one never had to cover.

**This plan does not rule it, and that is a decision rather than an omission.** Ruling it here would set a fleet-wide conformance property from a single instance, on a planning run's judgement, with no build having exercised either answer. The plan's job is to make sure it is ruled *before* the gate code is written rather than discovered after — which requirement 2 and the first implementation step do.

### The first extension target, counted off disk

Requirement 3 says *"outside `scripts/helpers/measure/`"*, which is a direction rather than a population. **Counted on disk 2026-08-28, `scripts/helpers/` holds seven tools outside `measure/`:** `check_settings.py`, `check-settings.sh`, `harvest-intake.py`, `init-project.sh`, `lint-prompts.sh`, `similar-candidates.py`, `vendor-standards.sh`. **None is in any gate's population**, and the gate that exists reads only `scripts/helpers/measure/`.

> **Count it again at build time rather than trusting this list.** A pass eight days before this one counted six and missed `similar-candidates.py` — which is not an obscure file; it is invoked by name in the filing guidance every producing workflow receives. **That miss is the argument for requirement 3's off-disk clause in miniature**: a hand-kept population of seven was wrong within a week of being written down, and the only reason it was caught is that somebody re-counted.

**One of the seven is the case that matters most, and it is not the most obvious one.** `harvest-intake.py` is the *consumer* half of the intake pair — the thing whose being run is a stated **condition of an exemption**, not a convenience. It is invoked from `/standup` by prose in [`config/commands/standup.md`](../../../config/commands/standup.md), and **prose in a command file is exactly the shape this phase already ruled insufficient**: the `measure/` README stated its own `Read by` rule in prose and a tool shipped unread anyway. **If that line is ever dropped, the intake keeps accepting, nothing empties it, and no suite goes red.**

**Rule the seven in or out one at a time rather than adding them wholesale.** `vendor-standards.sh` and `init-project.sh` are plausibly operator-invoked tools with no produced surface at all; `check_settings.py` and `lint-prompts.sh` have their own tests. **The finding is that none of them has been ASKED**, not that all seven are defects.

### The one exclusion the stores force

[`tracked/operations/`](../../../tracked/operations/) is **human-in-the-loop only** — [Tracked Items Standard §1.2](../../standards/documentation/tracked_items_standard.md) forbids any workflow, dispatch or agent writing to it, and its triage cadence is *every standup, run by the operator*.

**Its consumer is a person, and no check can assert that a person read something.** A gate that tries to prove the operations store is being consumed will either assert something it cannot see — and be wrong quietly — or assert a proxy like file mtime, and be routed around within a month. **So it is excluded by name, with the exclusion asserted in the check**, the same treatment `run_log.py` already gets, for the same reason: an exclusion that is not named is a hole.

Get this wrong in the permissive direction and the gate red-flags the operator's own notebook. Get it wrong in the restrictive direction and *"a human reads it"* becomes the excuse that exempts anything. **Requirement 4 exists so the boundary is drawn once, in the check, rather than argued each time.**

### Why prose beside a hand-kept table is not enough, stated once

The rule this phase generalises was already written, in prose, in the directory it governs. **Nothing enforced it and a tool shipped unread anyway.** That is the argument for a gate rather than a convention, and it is the same argument the duplication ratchet in [Family alignment](phase2_family_alignment.md) rests on. **Two independent occurrences of one shape** is why this survived the 2026-08-18 merge as its own requirement set rather than becoming a note — and why it is now its own phase.

### What this phase does not do

- **It does not touch derived values, the enumeration or the echo.** That is [Nothing a run relies on is invisible](phase4_nothing_invisible.md), and the split is what makes each of them closable.
- **It does not delete an unread producer.** Finding one is the output; ruling what happens to it is a separate decision with its own criteria, and an automated remedy here would delete a surface whose consumer simply has not been built yet.
- **It does not check that a consumer is any good.** Naming a reader is a much weaker claim than the reader being correct, and this gate makes only the weaker one. **Say so where the check lives**, so nobody over-reads a green suite.
- **It does not amend the Tracked Items Standard.** That standard is vendored (MIRROR) and its amendments go upstream. This phase reads §0 and rules against it.
- **It does not build a config digest.** That is [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md), whose pair is this phase's test case.

---

## Implementation steps

- [ ] **Rule requirement 2 FIRST, before the definition is finalised** — does the cadence clause bind every producer, or only surfaces that accumulate? Use [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md)'s two-bag reader as the worked test case, and record the ruling and its reasoning here. Nothing below is safe until this is answered.
- [ ] Start from [Tracked Items Standard §0](../../standards/documentation/tracked_items_standard.md)'s three properties rather than from a blank page — admission test, named cadence with a named runner, exit — and read `modules/assistant/tracked/intake.py`'s docstring for the worked instance before writing a word of the definition.
- [ ] Write the definition of a producer with its exclusions, and check it against the existing gate's population — **if the definition would not have caught the three observables that motivated the gate, the definition is wrong.** This step is requirement 1.
- [ ] **Add the second honest test: the definition must catch an intake surface whose harvest stopped being invoked.** If it does not, it is too weak, and the failure it misses is one Tracked Items §8 calls a violation.
- [ ] Re-count `scripts/helpers/` outside `measure/` off disk rather than trusting § *The first extension target*, then rule each tool in or out one at a time, recording the reason for every out-ruling. **`harvest-intake.py` is the one to rule first** — it is a stated condition of an exemption, invoked only by prose in a command file.
- [ ] Enumerate the remaining candidate producer surfaces across the fleet and rule each in or out against the definition. An unexplained exclusion is the hole this phase exists to close.
- [ ] Extend the gate to the ruled-in surfaces, reading each population off disk.
- [ ] Assert every exclusion by name in the check itself, **including `tracked/operations/` with its reason** — requirement 4.
- [ ] Write down what this gate does NOT look at, beside the check, so a future reader does not over-read a green suite.
- [ ] **Demonstrate requirement 5 by mutation:** add a producer with no named consumer, confirm the suite goes red, and record what was added and what the failure said.
- [ ] Add the mutation in reverse — a producer whose row exists but whose consumer cell is empty — and confirm it also fails. Two ways to be wrong, two checks.
- [ ] Confirm [Nothing a run relies on is invisible](phase4_nothing_invisible.md)'s echo is caught by this gate if it has landed; if it has not, record here that the echo is a producer this gate is expected to cover, so [Nothing a run relies on is invisible](phase4_nothing_invisible.md) inherits it rather than rediscovering it.
- [ ] **Surface, in the PR body, any standards amendment this phase's definition implies** — with the target document and an anchor precise enough to act on. **Do not edit a standard, and do not file the item yourself:** a producing run surfaces and `review-pr` files. See § *The ruling needs an address, and the address is not this document*.
- [ ] Run the full suite and confirm nothing that depended on an unguarded surface broke.

---

## Runtime Verification

**This phase orchestrates no external runtime, and that is stated rather than omitted.** Its surface is pytest modules and the populations they read off disk — there is no daemon, no service and no vendor API for the [Documentation Standard's Live-Runtime Verification rule](../../standards/documentation/documentation_standard.md) to bite on.

**Requirement 5's mutation demonstration is the verification this phase carries**, and it is in the implementation checklist above rather than in a section of its own. A mutation that makes a real suite go red is a stronger observation than a transcript of a version banner, and it is the one this phase's correctness actually turns on.

**The population counts this phase is scoped on WERE read off disk**, on 2026-08-28, and they are recorded in § *The first extension target, counted off disk* with the instruction to re-count rather than trust them.

---

## The ruling needs an address, and the address is not this document

Whatever requirement 1 and requirement 2 settle is a **rule other work will be judged against**, and a rule that lives only in a phase doc has to be re-derived by whoever writes the next producer. The natural destination is a named standard with an actionable anchor.

**The route is: surface it, do not file it, and never edit the standard.** [`finding-routing.md` §7](../../standards/finding-routing.md) is explicit — a producing run surfaces a standards amendment in its PR and `review-pr` files it into [`tracked/standards/`](../../../tracked/standards/); `ratification` is the operator's alone. **A build dispatch for this phase is a producing run**, so it writes the amendment into its PR body with `target:` and `anchor:` named, and stops there.

**Until something is ratified, the ruling still binds this phase** — it is recorded in this doc and the gate is built against it. What the surfaced item buys is that the ruling survives this phase closing.

---

## Notes and gotchas

- **A gate that reports many findings at once gets suppressed.** If the ruled-in population turns out to be large and mostly unread, **that is a finding for the operator before it is a red suite.** Freezing a baseline the way [Family alignment](phase2_family_alignment.md)'s ratchet does is the pattern that already worked in this repo, and it may be the right shape here — a ratchet that can only shrink converts a wall of failures into a backlog with a direction.
- **The line to hold while ruling:** a producer is defined by *something is meant to read this*, **not** by *this writes to a file*. A check keyed on the second catches every temp file in the tree and gets disabled within a month.
- **The definition being ratified elsewhere is a borrowing, not a delegation.** [Tracked Items Standard §0](../../standards/documentation/tracked_items_standard.md) governs stores. Nothing in it says the property generalises to every producer — this phase claims that, and the claim is this phase's to defend. **Do not cite §0 as though it already ruled the fleet.**
- **Requirement 2's two answers have different costs and the cheaper one is not automatically right.** Exempting on-demand readers is one clause; requiring a cadence means [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md) needs a stated invoker for its comparison reader, which is real work in another phase. **Pick on which produces the more honest gate, not on which is cheaper to write** — a definition weakened to avoid work in a sibling phase is the exact shape that gets a gate routed around.
- **This phase inherits [Nothing a run relies on is invisible](phase4_nothing_invisible.md)'s worked example of getting the population right.** The existing gate's disk-side population read and its named-and-asserted exclusion are both deliberate and both easy to drop while generalising. Read the existing gate before extending it.
