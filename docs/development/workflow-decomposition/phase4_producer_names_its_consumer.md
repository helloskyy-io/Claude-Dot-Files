# Phase 4 — Every producer names its consumer

**Component:** [Workflow Decomposition](roadmap.md) · **Status:** not started · **Gate:** none

## What this phase does

Decomposition multiplies the number of things a run writes. Each child emits a result, each parent writes observables, each measurement tool prints an answer. A surface written by one part of the system and read by no other part is not neutral: it costs the run that produces it, it looks like coverage to a reader, and nothing goes red when it stops being correct — because nothing was ever checking.

This has happened here, measured, and it is why the gate exists in the first place: **three parent-written observables shipped with no reader at all.**

One directory now has a defence. Every tool in `scripts/helpers/measure/` must appear in a table naming who reads it, and the check reads the population **off disk** rather than off the table — because the way a tool arrives with no stated consumer is not by leaving a cell blank, it is by never adding the row. One module is excluded by name, and the exclusion is itself asserted, because an exclusion that is not named is a hole.

That defence stops at one directory. This phase decides what a producer is across the fleet and extends the gate to reach the rest.

**Terms used here.** A **producer** is something a run writes that another part of the system is meant to read. A **consumer** is the named thing that reads it. A **declaration module** is code that defines a surface's shape without producing anything itself — it is not a producer and must be excluded by name rather than by being forgotten.

---

## Requirements for completion

1. **"Producer" is defined**, in a sentence a check can be built from, and the definition names what it deliberately excludes.
2. **The gate reaches producers outside `scripts/helpers/measure/`.** Which surfaces it reaches is this phase's ruling, made against the definition in requirement 1 rather than by convenience.
3. **The population is read off disk, never off a hand-kept list.** This is the property that makes the existing gate work and it is the one most likely to be lost in generalising it.
4. **A new producer with no named consumer fails the suite** — demonstrated by adding one and watching it go red, not asserted from reading the code.
5. **Every exclusion is named and asserted.** An unlisted exemption is indistinguishable from an omission the next time somebody reads the check.

---

## Dependencies

- **Nothing outside this component.**
- **[Phase 3](phase3_auditable_derivation.md) produces a consumer for this gate to check** — its echo is a new producer, and its test that a run names what it derived is that producer's consumer. Neither phase blocks the other; if [Phase 3](phase3_auditable_derivation.md) lands first, its echo is a live worked example for this one.
- **[Phase 6](phase6_configuration_a_run_absorbed.md) is the strongest case for this gate existing.** It adds one producer (a configuration digest) and one consumer (a reader over bags) in the same phase, deliberately. This gate is what keeps the next such pairing honest when the two halves are not planned together.

---

## What this phase decides

### What counts as a producer, and what does not

The definition is the whole phase — extend the gate to the wrong population and it becomes a check people route around. Three shapes to rule on explicitly, none of them decided here:

- **A tool that answers a question** — the existing population. Clearly in.
- **A record a run writes for a later run** — a run bag's tags, a typed exit record, a log line something is meant to route on. Probably in, and this is where the real value is.
- **A declaration module** — code defining a surface's shape, loaded by the tools rather than run beside them. Clearly out, and it must be out **by name**.

The line to hold while ruling: a producer is defined by *something is meant to read this*, not by *this writes to a file*. A check keyed on the second catches every temp file in the tree and gets disabled within a month.

### Why prose beside a hand-kept table is not enough, stated once

The rule this phase generalises was already written in prose in the directory it governs — the README said in its own words that a `Read by` column with nothing in it was the directory's own finding, one level up. **Nothing enforced it, and a tool shipped unread anyway.** That is the argument for a gate rather than a convention, and it is the same argument the duplication ratchet in [Phase 2](phase2_family_alignment.md) rests on. Two independent occurrences of one shape is why this is a phase and not a note.

### What this phase does not do

- **It does not delete an unread producer.** Finding one is the output; ruling what happens to it is a separate decision with its own criteria, and an automated remedy here would delete a surface whose consumer simply has not been built yet.
- **It does not check that the consumer is any good.** Naming a reader is a much weaker claim than the reader being correct, and this gate makes only the weaker one. Say so where the check lives, so nobody over-reads a green suite.

---

## Implementation steps

- [ ] Write the definition of a producer, with its exclusions, and check it against the existing gate's population — if the definition would not have caught the three observables that motivated it, the definition is wrong.
- [ ] Enumerate candidate producer surfaces across the fleet and rule each in or out against that definition. Record the out-rulings with reasons; an unexplained exclusion is the hole this phase exists to close.
- [ ] Extend the gate to the ruled-in surfaces, reading each population off disk.
- [ ] Assert every exclusion by name, in the check itself, the way the existing gate asserts its one exclusion.
- [ ] **Demonstrate requirement 4 by mutation:** add a producer with no named consumer and confirm the suite goes red. Record what was added and what the failure said.
- [ ] Add the same mutation in reverse — a producer whose row exists but whose consumer cell is empty — and confirm it also fails. Two ways to be wrong, two checks.
- [ ] Write down what this gate does NOT look at, beside the check, so a future reader does not over-read it.
- [ ] Run the full suite.

---

## Runtime Verification

**Not applicable, and stated rather than omitted.** This phase orchestrates no external runtime. Its surface is pytest modules and the tables they read; the [Documentation Standard's Live-Runtime Verification rule](../../standards/documentation/documentation_standard.md) has nothing to bite on here. Requirement 4's mutation demonstration is the verification this phase does carry, and it is in the checklist above rather than in a section of its own.

---

## Notes and gotchas

- **The existing gate is small and the reasons for its shape are not obvious.** Read it before extending it: the disk-side population read, and the named-and-asserted exclusion, are both deliberate and both easy to drop while generalising.
- **A gate that reports many findings at once gets suppressed.** If the ruled-in population turns out to be large and mostly unread, that is a finding for the operator before it is a red suite — freezing a baseline the way [Phase 2](phase2_family_alignment.md)'s ratchet does is the pattern that already worked here, and it may be the right shape for this one too.
