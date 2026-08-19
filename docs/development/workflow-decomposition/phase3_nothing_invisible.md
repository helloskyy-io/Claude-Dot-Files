# Phase 3 — Nothing a run relies on is invisible

**Component:** [Workflow Decomposition](roadmap.md) · **Status:** not started · **Gate:** none — both mechanisms it finishes are already running

> **This phase is a merge of two phases that were planned separately on 2026-08-18** — *A derived value you can audit* and *Every producer names its consumer*. They share one shape and neither carried enough work to stand alone as a document: each takes a thing the system already relies on but never states, and makes it say itself out loud. The merge landed on the **lower** number, 3. The higher number is not reused — see [`roadmap.md`](roadmap.md) § Phases for the retired-number record.

## What this phase does

A run in this fleet depends on two classes of thing it never announces.

**The first is what it worked out for itself.** A workflow does not learn everything from flags. It reads the repository root off git, reads the component it is planning from a path it was handed, and builds several more values from those two. Those are **derived** values, and they are the right design — a constant restated in two places diverges silently, which is why the [Architecture Standard](../../standards/architecture/architectural_standard.md) carries `derive ≠ declare` as a seam. But derivation has one failure mode a flag does not:

> **A wrong flag fails loudly at parse time. A wrong derivation produces a *plausible* wrong run** — the workflow competently plans the wrong component, opens a real pull request, and nothing anywhere goes red.

**The second is what it wrote for somebody else.** Decomposition multiplies the number of surfaces a run emits: each child returns a result, each parent writes observables, each measurement tool prints an answer. A surface written by one part of the system and read by no other part is not neutral — it costs the run that produces it, it looks like coverage to a reader, and nothing goes red when it stops being correct, because nothing was ever checking. That has happened here, measured: **three parent-written observables shipped with no reader at all.**

Both halves fail the same way — **silently, and while looking like success.** Both already have a partial defence built, and both are missing the part that would make the defence general. This phase finishes them together.

**Terms used here.** A **derived value** is anything a run computes rather than being told — the repo root, the component under plan, a path built from another path. A **marker** is a fact the derivation anchors on, like the presence of a `.git` directory, as opposed to a similarity judgement. An **echo** is the run stating, in its own output, what it derived and from what. **Scope of effect** is the answer to *what else is wrong if this value is wrong*. A **producer** is something a run writes that another part of the system is meant to read; a **consumer** is the named thing that reads it. A **declaration module** is code that defines a surface's shape without producing anything itself.

---

## Requirements for completion

### The derived half

1. **Every derived value in the fleet is enumerated** with its marker, its algorithm in one sentence, its override if it has one, and its scope of effect. Published where a reader looks — not recoverable only by reading the call chain.
2. **A live run echoes what it derived.** Not a rehearsal: `plan-feature` already prints its component, its phase-doc count and its grants **under `--dry-run` only**, and prints none of it on the run that actually dispatches. The echo has to be on the path that does the work.
3. **A parent can silence the echo without destroying the record.** `verbose` is already threaded through this fleet as an explicit parameter rather than sniffed from the terminal, and the caller that most wants quiet output — a parent running nine children — is exactly the caller that most needs the derivation recorded. Silencing the console must not silence the record.

### The produced half

4. **"Producer" is defined**, in a sentence a check can be built from, and the definition names what it deliberately excludes. **This requirement stays unchecked, and the definition does not exist yet** — see § *The definition is the whole of the produced half, and this plan does not supply it*.
5. **The gate reaches producers outside `scripts/helpers/measure/`**, with the population read **off disk, never off a hand-kept list**, and **every exclusion named and asserted** by name in the check itself.

### The proof, which is one demonstration with two halves

6. **A wrong derivation and an unread producer are both DEMONSTRATED to be visible.** Point a run at the wrong component, capture the echo, and show the output names what it derived before the run costs anything. Add a producer with no named consumer and watch the suite go red. Requirements 1–5 are not complete without both; neither is asserted from reading the code.

**Requirement 3 carries an unresolved trade, and it stays unchecked until somebody rules it.** Echoing costs output; the parent that wants silence is the one that needs the echo most. Nobody has measured the cost, and the evidence is explicit that this is argued convention across every source found, not data. **Rule it in this phase, in one sentence, and record the ruling** — do not let it be decided implicitly by whichever stream the first implementation happens to write to.

---

## Dependencies

- **[Phase 1](roadmap.md)** — complete. The activities layer both mechanisms live in came out of it.
- **Nothing outside this component.** No sibling component and no external system gates this.
- **Not gated on [Phase 5](phase5_dual_mode_children.md), and it does touch it.** Phase 5 adds nine standalone entrypoints, and a standalone caller is exactly the caller that wants the echo loud while a parent wants it quiet. Whichever lands first, requirement 3's ruling is the contract the other one builds against — so **if [Phase 5](phase5_dual_mode_children.md) runs first, its nine adapters inherit that ruling rather than each inventing one.**
- **[Phase 6](phase6_configuration_a_run_absorbed.md) is the strongest case for the produced half existing.** It adds one producer (a configuration digest) and one consumer (a reader over bags) in the same phase, deliberately. This gate is what keeps the next such pairing honest when the two halves are *not* planned together.

---

## What this phase decides

### The five properties, and which two are already satisfied

| Property | State today | What this phase does |
|---|---|---|
| **Anchored on a marker** | ✅ satisfied — `resolve_repo_root` runs `git rev-parse --show-toplevel`, which reads `.git` and never guesses | nothing; record it as satisfied so it is not rebuilt |
| **Explicit override** | ✅ satisfied — `--repo` exists and is documented as *a FILESYSTEM PATH, never a gh slug* | nothing |
| **Published algorithm** | ❌ absent | requirement 1 |
| **Echo of what was derived** | ⚠️ partial — exists under `--dry-run`, absent on the live path | requirements 2 and 3 |
| **Stated scope of effect** | ❌ absent | requirement 1 |

Source: [`research/synthesis.md`](research/synthesis.md) § *Facet 2's real work is three missing properties*, resting on [`raw/invocation_contract.md`](research/raw/invocation_contract.md) §2.2 (M1–M5), §4.2 and §5.2.

### "Prefer derivation" is NOT the rule, and writing it would contradict a shipped decision

The tempting generalisation from this phase is *derive where you can*. **Do not write it.** This repo already made the opposite call in one specific place and made it correctly: **repo identity is declared** — `--repo`, explicitly never derived from the working directory — **while component scope is derived** from the path the run was pointed at.

Derivation is a **per-value decision with a stated reason**, not a policy. A rule saying otherwise would quietly reopen a question that is settled and working.

### The scope of effect is not decoration — it is what makes the echo readable

`resolve_repo_root`'s own comments already record what a wrong answer costs: `.claude/worktrees/` and `.claude/logs/` both hang off it, so a run rooted at a subdirectory scatters worktrees and logs where `/cleanup-merged-worktrees` never looks, and a later cleanup deletes the logs along with the workspace — after which cost accounting for those runs is unrecoverable. **Six of seven V2 entrypoints once dropped repo-root resolution and used the working directory instead.**

That paragraph is the model for requirement 1's scope-of-effect column. An echo that prints a path tells a reader *what* was derived; the scope of effect is what tells them whether to care.

### The definition is the whole of the produced half, and this plan does not supply it

**Requirement 4 is unchecked because nobody has written the definition yet, and this plan deliberately does not write it either.** Extend the gate to the wrong population and it becomes a check people route around; extend it to too narrow a one and it catches nothing the existing gate did not. Three shapes have to be ruled on explicitly, and none is decided here:

- **A tool that answers a question** — the existing population. Clearly in.
- **A record a run writes for a later run** — a run bag's tags, a typed exit record, a log line something is meant to route on. Probably in, and this is where the real value is.
- **A declaration module** — code defining a surface's shape, loaded by the tools rather than run beside them. Clearly out, and it must be out **by name**.

The line to hold while ruling: **a producer is defined by *something is meant to read this*, not by *this writes to a file*.** A check keyed on the second catches every temp file in the tree and gets disabled within a month.

**This is the weakest part of the phase and it is stated rather than hidden.** The derived half rests on a critic-passed paper; this half rests on priors plus two locally-measured occurrences of one shape, and its central deliverable is a definition the plan does not supply. A build dispatch that writes the definition badly will produce a gate that looks green and rules the wrong population.

### Why prose beside a hand-kept table is not enough, stated once

The rule this half generalises was already written in prose in the directory it governs — the README said in its own words that a `Read by` column with nothing in it was the directory's own finding, one level up. **Nothing enforced it, and a tool shipped unread anyway.** That is the argument for a gate rather than a convention, and it is the same argument the duplication ratchet in [Phase 2](phase2_family_alignment.md) rests on. Two independent occurrences of one shape is why this survived the merge as its own requirement set rather than becoming a note.

### What this phase does not do

- **It does not touch dual-mode invocation.** That is [Phase 5](phase5_dual_mode_children.md).
- **It does not add a new derived value.** Every value in scope already exists; this phase makes the existing ones legible.
- **It does not build a config digest.** What a run absorbed from `~/.claude/` is a different question with a different mechanism — [Phase 6](phase6_configuration_a_run_absorbed.md).
- **It does not delete an unread producer.** Finding one is the output; ruling what happens to it is a separate decision with its own criteria, and an automated remedy here would delete a surface whose consumer simply has not been built yet.
- **It does not check that a consumer is any good.** Naming a reader is a much weaker claim than the reader being correct, and this gate makes only the weaker one. Say so where the check lives, so nobody over-reads a green suite.

---

## Implementation steps

**The derived half:**

- [ ] Enumerate the derived values across the fleet's entrypoints and activities. The known set to start from, each verified against the tree rather than this list: the repository root; the component under plan; paths built from an already-contained path; the per-run worktree name; the pull-request number parsed back out of a URL; the set of papers a refresh run considers due.
- [ ] For each, record marker / algorithm / override / scope of effect. Where a value has no override, say so and say why — an absence stated is a decision, an absence unstated is an oversight.
- [ ] Rule requirement 3's trade in one sentence and write the ruling down: what the echo costs, which stream carries it, and what a parent may suppress.
- [ ] Move the echo onto the live path so the run that dispatches prints what it derived. Keep the `--dry-run` preview building its values through the same assembly the live run uses — a rehearsal that constructs its own copy previews something that is not what runs, and this family has shipped that bug once already.
- [ ] Publish the enumeration where a reader looks for it, and cross-reference it from the code that derives each value so the two cannot drift apart unnoticed.

**The produced half:**

- [ ] Write the definition of a producer, with its exclusions, and check it against the existing gate's population — **if the definition would not have caught the three observables that motivated the gate, the definition is wrong.** This step is requirement 4 and nothing below it is safe until it is done.
- [ ] Enumerate candidate producer surfaces across the fleet and rule each in or out against that definition. Record the out-rulings with reasons; an unexplained exclusion is the hole this half exists to close.
- [ ] Extend the gate to the ruled-in surfaces, reading each population off disk.
- [ ] Assert every exclusion by name, in the check itself, the way the existing gate asserts its one exclusion.
- [ ] Write down what this gate does NOT look at, beside the check, so a future reader does not over-read it.

**The proof, and it is requirement 6:**

- [ ] Add a test that a run's output names the component it derived. **The echo is itself a producer** — this test is its consumer, and the produced half's own gate should be what catches it if it is ever removed.
- [ ] Run against a deliberately wrong component path, capture the output verbatim, and confirm the derived value is named before any side effect. Record the transcript in this doc.
- [ ] **Demonstrate the produced half by mutation:** add a producer with no named consumer and confirm the suite goes red. Record what was added and what the failure said.
- [ ] Add the same mutation in reverse — a producer whose row exists but whose consumer cell is empty — and confirm it also fails. Two ways to be wrong, two checks.
- [ ] Run the full suite and confirm nothing that depended on the quiet path broke.

---

## Runtime Verification

**Date:** 2026-08-18 · **Host:** `puma-workstation-mint` · **Runtime verified:** `git`, which is the marker every derivation in this phase anchors on.

The claim being verified is the one requirement 1 rests on: that `git rev-parse --show-toplevel` returns the repository root rather than the invocation directory, so the anchor is a fact and not a guess.

```
$ git --version
git version 2.43.0

$ cd scripts/workflows/temporal && pwd
/home/puma/Repos/claude-dot-files/.claude/worktrees/plan-feature-1787093087/scripts/workflows/temporal

$ git rev-parse --show-toplevel
/home/puma/Repos/claude-dot-files/.claude/worktrees/plan-feature-1787093087
```

**Observed:** invoked three directories down, git returned the worktree root, not the working directory. The marker property holds on this host at this version.

**Re-verify when this doc is substantially revised** — and note the second-order fact this output demonstrates: the root returned here is a **worktree** root, which is the correct answer for a dispatch and would be the wrong answer for a tool expecting the main checkout. That distinction belongs in requirement 1's scope-of-effect entry for this value.

**The produced half orchestrates no external runtime**, and that is stated rather than omitted: its surface is pytest modules and the tables they read, so the [Documentation Standard's Live-Runtime Verification rule](../../standards/documentation/documentation_standard.md) has nothing to bite on there. Requirement 6's mutation demonstration is the verification that half carries, and it is in the checklist above rather than in a section of its own.

---

## Notes and gotchas

- **The echo is not logging.** Logging is for the person diagnosing a failure; the echo is for the person about to spend an hour of model time on the wrong component. It goes where they will see it before the run commits to anything, which is why requirement 6 checks *before any side effect* rather than *somewhere in the transcript*.
- **`--dry-run` already does most of this well, and that is the trap.** Reading the dry-run block makes the echo look built. It is built in the one mode where nothing is at stake.
- **Do not use this phase to add validation.** Containment of operator-supplied paths is already handled one layer up, by a parser where declaring a repo path and checking it are the same act. This phase is about visibility, not safety; conflating them will produce a change that touches the security-relevant path for a legibility reason.
- **The existing producer gate is small and the reasons for its shape are not obvious.** Read it before extending it: the disk-side population read, and the named-and-asserted exclusion, are both deliberate and both easy to drop while generalising.
- **A gate that reports many findings at once gets suppressed.** If the ruled-in population turns out to be large and mostly unread, that is a finding for the operator before it is a red suite — freezing a baseline the way [Phase 2](phase2_family_alignment.md)'s ratchet does is the pattern that already worked here, and it may be the right shape for this one too.
