# Phase 4 — Nothing a run relies on is invisible

**Component:** [Workflow Decomposition](roadmap.md) · **Status:** not started · **Gate:** none — the mechanism it finishes is already running

> **This phase was a merge of two phases planned separately on 2026-08-18** — *A derived value you can audit* and *Every producer names its consumer* — **and on 2026-08-28 it was SPLIT back apart.** The produced half is now [Phase 6](phase6_every_producer_names_its_consumer.md); **this document is the derived half and nothing else.** Phase 4 keeps its number and its filename, because a number is identity and never rollout order, and the produced half took the next free number rather than reclaiming the one it originally held.
>
> **Why the merge was right then and wrong now.** The merge's premise was that *"neither carried enough work to stand alone as a document."* That was accurate on 2026-08-18, when the produced half's central deliverable — a definition of *producer* — had no first-party referent at all. It stopped being accurate when the tracked stores landed on 2026-08-26 and supplied one, along with a named on-disk population and a named exclusion. **A better-specified deliverable is a larger one**, and the produced half is now the larger of the two.
>
> **What forced it is simpler than the sizing, though.** This phase's outcome could only be stated with the word *and*: *a wrong derivation is visible before it costs anything* **and** *a producer with no consumer turns the suite red*. Two independently demonstrable outcomes in one phase means whichever half finishes first cannot be shown as finished — so the cheap, well-evidenced derived half, whose echo nine new callers from [Phase 3](phase3_dual_mode_children.md) actively want, sat behind a definition nobody had written. **Two independent passes reached this, the second cold.** Full reasoning and recurrence history: [`C-v4k9pz2h`](../../../tracked/candidates/C-v4k9pz2h.md).
>
> **The phase's NAME is unchanged and now over-promises slightly.** *Nothing a run relies on is invisible* covers both halves; this document covers one. The name is left alone deliberately — [`sprint.md`](../sprint.md) cites it verbatim and is not a dispatch's to edit, so renaming here would desynchronise the two surfaces to fix a cosmetic imprecision. **Read the name as the pair of phases, and this document as the derived half of it.**

## What this phase does

A run in this fleet depends on two classes of thing it never announces.

**The first is what it worked out for itself.** A workflow does not learn everything from flags. It reads the repository root off git, reads the component it is planning from a path it was handed, and builds several more values from those two. Those are **derived** values, and they are the right design — a constant restated in two places diverges silently, which is why the [Architecture Standard](../../standards/architecture/architectural_standard.md) carries `derive ≠ declare` as a seam. But derivation has one failure mode a flag does not:

> **A wrong flag fails loudly at parse time. A wrong derivation produces a *plausible* wrong run** — the workflow competently plans the wrong component, opens a real pull request, and nothing anywhere goes red.

**The second is what it wrote for somebody else** — a surface written by one part of the system and read by no other. **That half is [Phase 6](phase6_every_producer_names_its_consumer.md) as of 2026-08-28**, and it is named here because the two are still one idea: both fail **silently, and while looking like success**, both already have a partial defence built, and both are missing the part that would make the defence general. **This document finishes the first one.**

**Read the two together and build them apart.** A phase closes on a demonstration, and these are two demonstrations on two mechanisms — which is exactly why they are two phases now.

**Terms used here.** A **derived value** is anything a run computes rather than being told — the repo root, the component under plan, a path built from another path. A **marker** is a fact the derivation anchors on, like the presence of a `.git` directory, as opposed to a similarity judgement. An **echo** is the run stating, in its own output, what it derived and from what. **Scope of effect** is the answer to *what else is wrong if this value is wrong*. A **producer** is something a run writes that another part of the system is meant to read; a **consumer** is the named thing that reads it. A **declaration module** is code that defines a surface's shape without producing anything itself.

---

## Requirements for completion

### The derived half

1. **Every derived value in the fleet is enumerated** with its marker, its algorithm in one sentence, its override if it has one, and its scope of effect. Published where a reader looks — not recoverable only by reading the call chain. **The enumeration's POPULATION is read off the derivation sites, never hand-kept** — a check derives the set of derivation sites from the tree and fails when one is missing from the enumeration, the way [Phase 6](phase6_every_producer_names_its_consumer.md)'s gate reads its population off disk. *A hand-kept list is what this phase exists to stop: a table checked against itself cannot see the derivation that was never added to it, and requirement 2's echo is only as good as the enumeration behind it.*
2. **A live run echoes what it derived.** Not a rehearsal: `plan-feature` already prints its component, its phase-doc count and its grants **under `--dry-run` only**, and prints none of it on the run that actually dispatches. The echo has to be on the path that does the work.
3. **A parent can silence the echo without destroying the record.** `verbose` is already threaded through this fleet as an explicit parameter rather than sniffed from the terminal, and the caller that most wants quiet output — a parent running nine children — is exactly the caller that most needs the derivation recorded. Silencing the console must not silence the record.

### The produced half — MOVED, and this is a pointer rather than a deletion

**Requirements 4 and 5 are now [Phase 6](phase6_every_producer_names_its_consumer.md)'s requirements 1 and 3, carried verbatim**, together with the sections that supported them: the producer definition, the first extension target, the `tracked/operations/` exclusion, and the argument for a gate over a convention. **Nothing was dropped in the move.** The numbers 4 and 5 are not reused here, so a cross-reference to *"Phase 4 requirement 4"* written before 2026-08-28 points at something that has an unambiguous new address rather than at a different requirement.

### The proof

4. **A wrong derivation is DEMONSTRATED to be visible.** Point a run at the wrong component, capture the echo, and show the output names what it derived **before the run costs anything**. Requirements 1–3 are not complete without it, and it is not asserted from reading the code.

> **This requirement is half of a sentence, and the other half went with the split.** The 2026-08-18 wording was: *"A wrong derivation and an unread producer are both DEMONSTRATED to be visible. Point a run at the wrong component, capture the echo, and show the output names what it derived before the run costs anything. Add a producer with no named consumer and watch the suite go red."* **Its second clause is [Phase 6](phase6_every_producer_names_its_consumer.md)'s requirement 5, verbatim.** Separating the conjuncts is the split; **no requirement was weakened, added or dropped**, and this is the only completion criterion in this component that a planning run has reworded.

**Requirement 3 carries an unresolved trade, and it stays unchecked until somebody rules it.** Echoing costs output; the parent that wants silence is the one that needs the echo most. Nobody has measured the cost, and the evidence is explicit that this is argued convention across every source found, not data. **Rule it in this phase, in one sentence, and record the ruling** — do not let it be decided implicitly by whichever stream the first implementation happens to write to.

---

## Dependencies

- **[Phase 1](roadmap.md)** — complete. The activities layer this mechanism lives in came out of it.
- **Nothing outside this component.** No sibling component and no external system gates this.
- **Not gated on [Phase 3](phase3_dual_mode_children.md), and it does touch it.** Phase 3 adds nine standalone entrypoints, and a standalone caller is exactly the caller that wants the echo loud while a parent wants it quiet. Whichever lands first, requirement 3's ruling is the contract the other one builds against — so **if [Phase 3](phase3_dual_mode_children.md) runs first, its nine adapters inherit that ruling rather than each inventing one.**
- **[Phase 6](phase6_every_producer_names_its_consumer.md)** — the produced half, split out of this document on 2026-08-28. Neither gates the other. **This phase's echo is itself a producer**, so Phase 6's gate is what should catch it if it is ever removed; the roadmap orders 4 before 6 partly for that reason.
- **[Phase 5](phase5_configuration_a_run_absorbed.md)** — no dependency in either direction. *(This bullet used to say Phase 5 was "the strongest case for the produced half existing", pairing one producer with one consumer in the same phase. **That claim belongs to [Phase 6](phase6_every_producer_names_its_consumer.md) now, and it needs a correction rather than a move** — Phase 6's candidate definition requires a named cadence, and Phase 5's reader has none, so the pairing is that phase's unruled test case rather than its exemplar. See [`C-k3nd8vwp`](../../../tracked/candidates/C-k3nd8vwp.md).)*

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

### The produced half's sections moved to Phase 6

**Three sections left this document on 2026-08-28 and are in [Phase 6](phase6_every_producer_names_its_consumer.md) rather than deleted:**

- *The definition is the whole of the produced half, and this plan does not supply it* — the three shapes to rule on, and the argument for why extending the gate to the wrong population produces a check people route around. **It gained a fourth and a fifth shape there**, and a first-party definition to rule against.
- *Why prose beside a hand-kept table is not enough* — the two independent occurrences of one shape that argue for a gate over a convention.
- The produced half's implementation steps and its exclusions.

**What is worth keeping HERE from that half is one sentence, because it applies to this half too:** the enumeration in requirement 1 has a population, and **a hand-kept population is what both halves exist to forbid.** A table checked against itself cannot see the derivation that was never added to it, which is why requirement 1 says the check derives its population from the tree.

### What this phase does not do

- **It does not touch dual-mode invocation.** That is [Phase 3](phase3_dual_mode_children.md).
- **It does not add a new derived value.** Every value in scope already exists; this phase makes the existing ones legible.
- **It does not build a config digest.** What a run absorbed from `~/.claude/` is a different question with a different mechanism — [Phase 5](phase5_configuration_a_run_absorbed.md).
- **It does not extend the producer/consumer gate, define a producer, or rule any surface in or out.** All of that is [Phase 6](phase6_every_producer_names_its_consumer.md) as of 2026-08-28. **The one thing this phase owes that phase is a fact rather than work:** the echo it builds is itself a producer, and it should appear in Phase 6's population rather than be exempted for having been built here.

---

## Implementation steps

**The derived half:**

- [ ] Build the check that DERIVES the population of derivation sites from the tree, so the enumeration cannot silently miss one — the same property `test_measure_readme_names_a_consumer.py` already has for producers.
- [ ] Enumerate the derived values across the fleet's entrypoints and activities. The known set to start from, each verified against the tree rather than this list: the repository root; the component under plan; paths built from an already-contained path; the per-run worktree name; the pull-request number parsed back out of a URL; the set of papers a refresh run considers due.
- [ ] For each, record marker / algorithm / override / scope of effect. Where a value has no override, say so and say why — an absence stated is a decision, an absence unstated is an oversight.
- [ ] Rule requirement 3's trade in one sentence and write the ruling down: what the echo costs, which stream carries it, and what a parent may suppress.
- [ ] Move the echo onto the live path so the run that dispatches prints what it derived. Keep the `--dry-run` preview building its values through the same assembly the live run uses — a rehearsal that constructs its own copy previews something that is not what runs, and this family has shipped that bug once already.
- [ ] Publish the enumeration where a reader looks for it, and cross-reference it from the code that derives each value so the two cannot drift apart unnoticed.

*The produced half's implementation steps moved to [Phase 6](phase6_every_producer_names_its_consumer.md) with the split, unchanged.*

**The proof, and it is requirement 4:**

- [ ] Add a test that a run's output names the component it derived. **The echo is itself a producer** — this test is its consumer, and [Phase 6](phase6_every_producer_names_its_consumer.md)'s gate should be what catches it if it is ever removed. If that phase has not landed, record here that the echo is a producer it is expected to cover.
- [ ] Run against a deliberately wrong component path, capture the output verbatim, and confirm the derived value is named before any side effect. Record the transcript in this doc.
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

**The produced half's verification moved with it** — see [Phase 6](phase6_every_producer_names_its_consumer.md) § Runtime Verification, which records that that phase orchestrates no external runtime and carries a mutation demonstration instead.

---

## Notes and gotchas

- **The echo is not logging.** Logging is for the person diagnosing a failure; the echo is for the person about to spend an hour of model time on the wrong component. It goes where they will see it before the run commits to anything, which is why requirement 4 checks *before any side effect* rather than *somewhere in the transcript*.
- **`--dry-run` already does most of this well, and that is the trap.** Reading the dry-run block makes the echo look built. It is built in the one mode where nothing is at stake.
- **Do not use this phase to add validation.** Containment of operator-supplied paths is already handled one layer up, by a parser where declaring a repo path and checking it are the same act. This phase is about visibility, not safety; conflating them will produce a change that touches the security-relevant path for a legibility reason.
- **The producer-gate notes moved with the split.** Its shape, and the ratchet-as-backlog pattern for a large ruled-in population, are in [Phase 6](phase6_every_producer_names_its_consumer.md) § Notes and gotchas.
