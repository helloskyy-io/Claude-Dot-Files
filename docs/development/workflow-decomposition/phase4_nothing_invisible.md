# Nothing a run relies on is invisible

**Component:** [Workflow Decomposition](roadmap.md) · **Status:** not started · **Gate:** none — the mechanism it finishes is already running

> **This phase was a merge of two phases planned separately on 2026-08-18** — *A derived value you can audit* and *Every producer names its consumer* — **and on 2026-08-28 it was SPLIT back apart.** The produced half is now [Every producer names its consumer](phase6_every_producer_names_its_consumer.md); **this document is the derived half and nothing else.** This phase keeps its number and its filename, because a number is identity and never rollout order, and the produced half took the next free number rather than reclaiming the one it originally held.
>
> **Why the merge was right then and wrong now.** The merge's premise was that *"neither carried enough work to stand alone as a document."* That was accurate on 2026-08-18, when the produced half's central deliverable — a definition of *producer* — had no first-party referent at all. It stopped being accurate when the tracked stores landed on 2026-08-26 and supplied one, along with a named on-disk population and a named exclusion. **A better-specified deliverable is a larger one**, and the produced half is now the larger of the two.
>
> **What forced it is simpler than the sizing, though.** This phase's outcome could only be stated with the word *and*: *a wrong derivation is visible before it costs anything* **and** *a producer with no consumer turns the suite red*. Two independently demonstrable outcomes in one phase means whichever half finishes first cannot be shown as finished — so the cheap, well-evidenced derived half, whose echo nine new callers from [Dual-mode children](phase3_dual_mode_children.md) actively want, sat behind a definition nobody had written. **Two independent passes reached this, the second cold.** Full reasoning and recurrence history: [`C-v4k9pz2h`](../../../tracked/candidates/C-v4k9pz2h.md).
>
> **The phase's NAME is unchanged and now over-promises slightly.** *Nothing a run relies on is invisible* covers both halves; this document covers one. The name is left alone deliberately — [`sprint.md`](../sprint.md) cites it verbatim and is not a dispatch's to edit, so renaming here would desynchronise the two surfaces to fix a cosmetic imprecision. **Read the name as the pair of phases, and this document as the derived half of it.**

## What this phase does

A run in this fleet depends on two classes of thing it never announces.

**The first is what it worked out for itself.** A workflow does not learn everything from flags. It reads the repository root off git, reads the component it is planning from a path it was handed, and builds several more values from those two. Those are **derived** values, and they are the right design — a constant restated in two places diverges silently, which is why the [Architecture Standard](../../standards/architecture/architectural_standard.md) carries `derive ≠ declare` as a seam. But derivation has one failure mode a flag does not:

> **A wrong flag fails loudly at parse time. A wrong derivation produces a *plausible* wrong run** — the workflow competently plans the wrong component, opens a real pull request, and nothing anywhere goes red.

**The second is what it wrote for somebody else** — a surface written by one part of the system and read by no other. **That half is [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) as of 2026-08-28**, and it is named here because the two are still one idea: both fail **silently, and while looking like success**, both already have a partial defence built, and both are missing the part that would make the defence general. **This document finishes the first one.**

**Read the two together and build them apart.** A phase closes on a demonstration, and these are two demonstrations on two mechanisms — which is exactly why they are two phases now.

**Terms used here.** A **derived value** is anything a run computes rather than being told — the repo root, the component under plan, a path built from another path. A **marker** is a fact the derivation anchors on, like the presence of a `.git` directory, as opposed to a similarity judgement. An **echo** is the run stating, in its own output, what it derived and from what. **Scope of effect** is the answer to *what else is wrong if this value is wrong*. A **producer** is something a run writes that another part of the system is meant to read; a **consumer** is the named thing that reads it. A **declaration module** is code that defines a surface's shape without producing anything itself.

---

## Requirements for completion

### The derived half

1. **Every derived value in the fleet is enumerated** with its marker, its algorithm in one sentence, its override if it has one, and its scope of effect. Published where a reader looks — not recoverable only by reading the call chain. **The enumeration's POPULATION is read off the derivation sites, never hand-kept** — a check derives the set of derivation sites from the tree and fails when one is missing from the enumeration, the way [Every producer names its consumer](phase6_every_producer_names_its_consumer.md)'s gate reads its population off disk. *A hand-kept list is what this phase exists to stop: a table checked against itself cannot see the derivation that was never added to it, and requirement 2's echo is only as good as the enumeration behind it.*

> **The population rule rests on an analogy that does NOT hold, and the fork it opens must be settled BEFORE this phase is scheduled. This plan states the fork and rules neither branch.**
>
> The clause above justifies itself by [Every producer names its consumer](phase6_every_producer_names_its_consumer.md)'s gate — but **that gate's population is _files in a directory_**, `_MEASURE.glob("*.py")` at `scripts/helpers/tests/unit/test_measure_readme_names_a_consumer.py:61`, which is a syntactic definition. **A derivation site has no syntactic definition in this tree.** Measured 2026-08-28: `@derived`, `DERIVED_VALUES`, `register_derivation` and `DERIVATION_SITES` return **zero hits across 225 Python files**. There is no decorator, no registry and no naming convention marking one.
>
> - **Branch A — a cheap syntactic PROXY may already exist.** Five named resolvers carry most of the fleet's derivation: `resolve_repo_root` and `resolve_operator_paths` (`scripts/preflight.py`), `resolve_identity` (`scripts/dispatch_identity.py`), `resolve_journal_root` (`modules/journal/root.py`), `resolve_task_source` (`modules/assistant/assistant_activities.py`). *"Call sites of these named functions"* is a population a check can derive off the tree without anyone marking anything. **The doubt is coverage, not mechanism** — and a gap is already visible: `pr_number_from_url` (`modules/assistant/routing.py:212`), `base_ref` and `pr_branch` (`assistant_activities.py`) share no naming convention with the five, and the per-run worktree name is assembled inline in the runners.
> - **Branch B — if no proxy covers the set, the requirement resolves into one of two things it cannot absorb.** Either a **marker convention across the tree** — every derivation site made to carry a decorator or a registry entry, which is a larger and different phase nobody has scoped and which touches code this phase otherwise only reads — **or the hand-kept list this very requirement exists to forbid.**
>
> **THE CHECK THAT SETTLES IT — RUN COLD ON 2026-08-28, AND IT RETURNED BRANCH B (see § *The five properties* below for the result):** take the known derived values from the implementation checklist below, and ask of each whether it reaches one of the five named resolvers. **Every one does → Branch A; the proxy is the population and requirement 1 is buildable as written. Any one does not → Branch B is live**, and this phase must be re-scoped and re-sized before it is scheduled, because its estimate assumes Branch A.
>
> **Do not resolve this by widening the requirement to "a list that is reviewed."** That is Branch B's second horn wearing the first one's language, and it is the failure requirement 1 names in its own last sentence.
2. **A live run echoes what it derived.** Not a rehearsal: `plan-feature` already prints its component, its phase-doc count and its grants **under `--dry-run` only**, and prints none of it on the run that actually dispatches. The echo has to be on the path that does the work.
3. **A parent can silence the echo without destroying the record.** `verbose` is already threaded through this fleet as an explicit parameter rather than sniffed from the terminal, and the caller that most wants quiet output — a parent running nine children — is exactly the caller that most needs the derivation recorded. Silencing the console must not silence the record.

### The produced half — MOVED, and this is a pointer rather than a deletion

**Requirements 4 and 5 are now [Every producer names its consumer](phase6_every_producer_names_its_consumer.md)'s requirements 1 and 3, carried verbatim**, together with the sections that supported them: the producer definition, the first extension target, the `tracked/operations/` exclusion, and the argument for a gate over a convention. **Nothing was dropped in the move.** The numbers 4 and 5 are not reused here, so a cross-reference written before 2026-08-28 to this document's requirement 4 or 5 points at something with an unambiguous new address rather than at a different requirement.

### The proof

4. **A wrong derivation is DEMONSTRATED to be visible.** Point a run at the wrong component, capture the echo, and show the output names what it derived **before the run costs anything**. Requirements 1–3 are not complete without it, and it is not asserted from reading the code.

> **This requirement is half of a sentence, and the other half went with the split.** The 2026-08-18 wording was: *"A wrong derivation and an unread producer are both DEMONSTRATED to be visible. Point a run at the wrong component, capture the echo, and show the output names what it derived before the run costs anything. Add a producer with no named consumer and watch the suite go red."* **Its second clause is [Every producer names its consumer](phase6_every_producer_names_its_consumer.md)'s requirement 5, verbatim.** Separating the conjuncts is the split; **no requirement was weakened, added or dropped**, and this is the only completion criterion in this component that a planning run has reworded.

**Requirement 3 carries an unresolved trade, and it stays unchecked until somebody rules it.** Echoing costs output; the parent that wants silence is the one that needs the echo most. Nobody has measured the cost, and the evidence is explicit that this is argued convention across every source found, not data. **Rule it in this phase, in one sentence, and record the ruling** — do not let it be decided implicitly by whichever stream the first implementation happens to write to. **The ruling lands in [`workflow-scripts.md`](../../standards/workflow-scripts.md) § Composition, beside the VERDICT-over-stdout contract it constrains**, on the same principle § *Where the enumeration is published* applies to requirement 1: an address-less ruling is one the build picks silently. It is surfaced for `review-pr` to file as a `tracked/standards/` amendment; this phase does not write a standard.

---

## Dependencies

- **[Decompose the build families and codify the shape](roadmap.md)** — complete. The activities layer this mechanism lives in came out of it.
- **Nothing outside this component.** No sibling component and no external system gates this.
- **Not gated on [Phase 3](phase3_dual_mode_children.md), and it does touch it.** Phase 3 adds nine standalone entrypoints, and a standalone caller is exactly the caller that wants the echo loud while a parent wants it quiet. Whichever lands first, requirement 3's ruling is the contract the other one builds against — so **if [Phase 3](phase3_dual_mode_children.md) runs first, its nine adapters inherit that ruling rather than each inventing one.**
- **[Every producer names its consumer](phase6_every_producer_names_its_consumer.md)** — the produced half, split out of this document on 2026-08-28. Neither gates the other. **This phase's echo is itself a producer**, so that phase's gate is what should catch it if it is ever removed; the roadmap orders this phase first partly for that reason.
- **[What configuration a run absorbed](phase5_configuration_a_run_absorbed.md)** — no dependency in either direction. *(This bullet used to say *What configuration a run absorbed* was "the strongest case for the produced half existing", pairing one producer with one consumer in the same phase. **That claim belongs to [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) now, and it needs a correction rather than a move** — that phase's candidate definition requires a named cadence, and this one's reader has none, so the pairing is that phase's unruled test case rather than its exemplar. See [`C-k3nd8vwp`](../../../tracked/candidates/C-k3nd8vwp.md).)*

---

## What this phase decides

> **⚠ THIS PHASE'S OWN PRE-SCHEDULING CHECK HAS FIRED, AND IT RETURNED BRANCH B.** Run cold by `plan-verify` on 2026-08-28, before scheduling: **three of the six named derived values reach none of the five resolvers.** The worktree name is assembled inline in eight runners; `pr_number_from_url` (`routing.py:212`) and `due_papers` (`research_refresh_workflow.py:36`) share no convention with them; and the four marker patterns return **0 hits across 225 Python files**.
>
> **So requirement 1 resolves on Branch B, and Branch B forces a ruling this phase cannot make for itself.** [`roadmap.md`](roadmap.md) states it: *the operator decision this figure does not make is whether requirement 1's read-it-off-the-tree clause survives at all.* **Keeping it** means introducing a marker convention across the tree — which this doc itself calls *"a larger and different phase nobody has scoped"*. **Dropping it** makes the phase materially cheaper and hands the enumeration the hand-kept population the requirement exists to forbid. The estimate in the roadmap is sized for KEEPING it, at its plausible smallest — **that is a sizing assumption, not the ruling.** Do not schedule this phase before the ruling is made. **This is recorded here because a build dispatch opens this file, not the roadmap**, and a phase that pre-commits to a check must carry the check's result where the builder will read it.

### The five properties, and which two are already satisfied

**The five-property frame is CONVENTION, not measurement, and the paper it rests on says so.** [`research/synthesis.md`](research/synthesis.md) records that the industry position on facet 2 is *"argued by convention across five sources, never evidenced by data"*, and states it as a gap (§6.2). The table below is still the right frame to build against — five sources agreeing is worth acting on — but a requirement derived from it inherits that prior, and nothing downstream should read the ✅/❌ column as measured.


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

### The produced half's sections moved to *Every producer names its consumer*

**Three sections left this document on 2026-08-28 and are in [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) rather than deleted:**

- *The definition is the whole of the produced half, and this plan does not supply it* — the three shapes to rule on, and the argument for why extending the gate to the wrong population produces a check people route around. **It gained a fourth and a fifth shape there**, and a first-party definition to rule against.
- *Why prose beside a hand-kept table is not enough* — the two independent occurrences of one shape that argue for a gate over a convention.
- The produced half's implementation steps and its exclusions.

**What is worth keeping HERE from that half is one sentence, because it applies to this half too:** the enumeration in requirement 1 has a population, and **a hand-kept population is what both halves exist to forbid.** A table checked against itself cannot see the derivation that was never added to it, which is why requirement 1 says the check derives its population from the tree.

### Where the enumeration is published

Requirement 1 says the enumeration is *"published where a reader looks"* and does not say where — and an address-less deliverable is one the build picks silently from three options with three different costs. **The destination is named here**, on the same principle [Dual-mode children](phase3_dual_mode_children.md) § *Where the divergence ruling lands* and [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) § *The ruling needs an address* apply to theirs.

**Two artifacts come out of requirement 1, and they do not go to the same place.**

**The TABLE — one row per derived value, carrying marker / algorithm / override / scope of effect — goes in a `README.md` beside the code that derives, with the check reading it.** The exemplar is `scripts/helpers/measure/README.md`: a markdown table whose population is read off disk by `test_measure_readme_names_a_consumer.py`, which fails when a file on disk has no row **and** when a row names a file that is not on disk. That is the same gate requirement 1 cites for its population rule, doing the same job on the same shape, and the enumeration has to sit somewhere a check can parse it. **Which README depends on the fork above** — Branch A puts the resolvers in two files under `scripts/` and one module each under `modules/journal/` and `modules/assistant/`, so a single fleet-level `scripts/workflows/temporal/README.md` is the plausible home and none exists yet.

**The RULE — *every derived value publishes its marker, algorithm, override and scope of effect* — is a standards amendment against [`workflow-scripts.md`](../../standards/workflow-scripts.md) § *9. Repo Root Operation*,** which today states the one derivation this fleet already governs and is the section a widened rule extends. **Surface it, do not file it, and never edit the standard:** [`finding-routing.md` §7](../../standards/finding-routing.md) gives a producing run the surfacing and `review-pr` the filing, and a build dispatch for this phase is a producing run.

**Two destinations were considered and rejected, with the reason, so the build does not re-open them:**

- **The table inside `workflow-scripts.md`.** A standard states the rule and never the inventory. A table there goes stale on every value added, and the amendment path makes each refresh a ratification cycle — which is how an enumeration stops being maintained.
- **The table in [`docs/guide/workflows.md`](../../guide/workflows.md).** Right audience for *how do I override this*, wrong distance from the code: nothing there can be held honest by a check, and this phase's whole premise is that a list checked against itself cannot see what was never added to it. **Cross-reference it from the guide rather than duplicating it there.**

### What this phase does not do

- **It does not touch dual-mode invocation.** That is [Phase 3](phase3_dual_mode_children.md).
- **It does not add a new derived value.** Every value in scope already exists; this phase makes the existing ones legible.
- **It does not build a config digest.** What a run absorbed from `~/.claude/` is a different question with a different mechanism — [Phase 5](phase5_configuration_a_run_absorbed.md).
- **It does not extend the producer/consumer gate, define a producer, or rule any surface in or out.** All of that is [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) as of 2026-08-28. **The one thing this phase owes that phase is a fact rather than work:** the echo it builds is itself a producer, and it should appear in that phase's population rather than be exempted for having been built here.

---

## Implementation steps

**The derived half:**

- [ ] Build the check that DERIVES the population of derivation sites from the tree, so the enumeration cannot silently miss one — the same property `test_measure_readme_names_a_consumer.py` already has for producers.
- [ ] Enumerate the derived values across the fleet's entrypoints and activities. The known set to start from, each verified against the tree rather than this list: the repository root; the component under plan; paths built from an already-contained path; the per-run worktree name; the pull-request number parsed back out of a URL; the set of papers a refresh run considers due.
- [ ] For each, record marker / algorithm / override / scope of effect. Where a value has no override, say so and say why — an absence stated is a decision, an absence unstated is an oversight.
- [ ] Rule requirement 3's trade in one sentence and write the ruling down: what the echo costs, which stream carries it, and what a parent may suppress.
- [ ] Move the echo onto the live path so the run that dispatches prints what it derived. Keep the `--dry-run` preview building its values through the same assembly the live run uses — a rehearsal that constructs its own copy previews something that is not what runs, and this family has shipped that bug once already.
- [ ] Publish the enumeration at the destination named in § *Where the enumeration is published*, and cross-reference it from the code that derives each value so the two cannot drift apart unnoticed.

*The produced half's implementation steps moved to [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) with the split, unchanged.*

**The proof, and it is requirement 4:**

- [ ] Add a test that a run's output names the component it derived. **The echo is itself a producer** — this test is its consumer, and [Every producer names its consumer](phase6_every_producer_names_its_consumer.md)'s gate should be what catches it if it is ever removed. If that phase has not landed, record here that the echo is a producer it is expected to cover.
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

**The produced half's verification moved with it** — see [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) § Runtime Verification, which records that that phase orchestrates no external runtime and carries a mutation demonstration instead.

---

## Notes and gotchas

- **The echo is not logging.** Logging is for the person diagnosing a failure; the echo is for the person about to spend an hour of model time on the wrong component. It goes where they will see it before the run commits to anything, which is why requirement 4 checks *before any side effect* rather than *somewhere in the transcript*.
- **`--dry-run` already does most of this well, and that is the trap.** Reading the dry-run block makes the echo look built. It is built in the one mode where nothing is at stake.
- **Do not use this phase to add validation.** Containment of operator-supplied paths is already handled one layer up, by a parser where declaring a repo path and checking it are the same act. This phase is about visibility, not safety; conflating them will produce a change that touches the security-relevant path for a legibility reason.
- **The producer-gate notes moved with the split.** Its shape, and the ratchet-as-backlog pattern for a large ruled-in population, are in [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) § Notes and gotchas.
