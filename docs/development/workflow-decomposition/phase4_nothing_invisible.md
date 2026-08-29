# Nothing a run relies on is invisible

**Component:** [Workflow Decomposition](roadmap.md) · **Status:** not started · **Gate:** none — the object it extends is already running

> **RE-PLANNED ON 2026-08-28 BY OPERATOR RULING, AND THIS IS A SCOPE CHANGE RATHER THAN A REWORDING.** This phase used to ask for an *audit* of the fleet's derived values: enumerate them, publish each one's marker and algorithm and override and scope of effect, and hold the enumeration honest with a check that reads its population off the tree. That requirement pre-committed to a check; the check ran cold and returned Branch B — three of six derived values reached none of the five named resolvers, and `@derived`, `DERIVED_VALUES`, `register_derivation` and `DERIVATION_SITES` returned **zero hits across 225 Python files**. The plan then offered two branches: introduce a marker convention across the tree, or fall back to the hand-kept list the requirement existed to forbid.
>
> **The operator ruled that both are the wrong question. The requirement was an audit tool for a mess; the ruling removes the mess.** Derivation should not be enumerated, because it should not happen in eight places. The orchestrator computes the run's context once at the boundary and injects it — the general form is dependency injection, and every CI system solves it this way rather than asking a step to work out which repository it is in.
>
> **The Branch A / Branch B fork is DELETED, not weakened**, along with the read-it-off-the-tree clause that forced it. There is no marker convention, no 225-file sweep, no check deriving a population, and no hand-kept list. § *The fork that was deleted, and why the record is kept* preserves what it said, because [`roadmap.md`](roadmap.md) and this component's candidates cite it.

> **This phase was a merge of two phases planned separately on 2026-08-18** — *A derived value you can audit* and *Every producer names its consumer* — **and on 2026-08-28 it was SPLIT back apart.** The produced half is now [Every producer names its consumer](phase6_every_producer_names_its_consumer.md); **this document is the derived half and nothing else.** This phase keeps its number and its filename, because a number is identity and never rollout order.
>
> **The phase's NAME is unchanged and now over-promises slightly.** *Nothing a run relies on is invisible* covers both halves; this document covers one. The name is left alone deliberately — [`sprint.md`](../sprint.md) cites it verbatim and is not a dispatch's to edit. **Read the name as the pair of phases, and this document as the derived half of it.**

## What this phase does

A run in this fleet depends on two classes of thing it never announces.

**The first is what it worked out for itself.** A workflow does not learn everything from flags. It reads the repository root off git, reads the component it is planning from a path it was handed, builds a per-run worktree name, resolves a journal root, and parses a pull-request number back out of a URL. Those are **derived** values, and deriving them is the right design — a constant restated in two places diverges silently, which is why the [Architecture Standard](../../standards/architecture/architectural_standard.md) carries `derive ≠ declare` as a seam. But derivation has one failure mode a flag does not:

> **A wrong flag fails loudly at parse time. A wrong derivation produces a *plausible* wrong run** — the workflow competently plans the wrong component, opens a real pull request, and nothing anywhere goes red.

**The second is what it wrote for somebody else** — a surface written by one part of the system and read by no other. **That half is [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) as of 2026-08-28.** **This document finishes the first one.**

**And it finishes it by making the question smaller rather than by auditing it.** The defence against a wrong derived value is not a table of every derivation in the tree. It is that a run has **one** place its derived values come from, that place is built once at the boundary, and the run says out loud what it built before it does anything that costs money. A value that is a field on that object cannot drift from the enumeration, because it **is** the enumeration.

**Terms used here.** A **run context** is the frozen object a dispatch constructs at its boundary, carrying everything the run derived rather than was told, and hands down to everything it calls. A **derived value** is anything a run computes rather than being told. A **marker** is a fact a derivation anchors on, like the presence of a `.git` directory, as opposed to a similarity judgement. The **echo** is the run stating its context in its own output before the first side effect. **Scope of effect** is the answer to *what else is wrong if this value is wrong*. **Constructed vs received** is the discriminator between a run that built its own context and one that was handed one by a parent.

---

## The evidence this rests on, and it is first-party

**This fleet has already performed exactly this consolidation once, on a value of the same shape, at the same call sites.** [`assistant_activities.py:1483`](../../../scripts/workflows/temporal/modules/assistant/assistant_activities.py), `base_ref`, records it in its own docstring:

> *"Every runner used to compute this inline as `ref = f"origin/{pr_branch(...)}" if pr_number else "HEAD"` … ELEVEN call sites in all. The expression now lives once, in `base_ref`, because a fix applied by hand to a list of eleven is a fix applied to ten: the eleventh passed its base inline and the first sweep of this did not see it."*

**The per-run worktree name is the same value shape, at the same eleven runners, and it has not been consolidated.** Measured exhaustively on 2026-08-28 (`grep -rn 'time\.time()'` plus `worktree_name *=|wt *= *f"` across `scripts/` and `modules/`, excluding tests) — **eleven sites in three different spellings**:

| Sites | Spelling | Notes |
|---|---|---|
| 8 runners — `run_plan_feature.py:123`, `run_plan_project.py:71`, `run_plan_revision.py:164`, `run_plan_sprint.py:98`, `run_plan_verify.py:321`, `run_triage_candidates.py:81`, `run_research.py:58`, `run_research_minor.py:57` | `f"<key>-{int(time.time())}"` | the key is already in scope at every one |
| 2 runners — `run_build.py:79`, `run_build_minor.py:79` | `f"build-{int(__import__('time').time())}"` | **a second spelling, and `run_build_minor` has DRIFTED** — its `workflow_key` is `"build-minor"` and its worktree is named `build-…` |
| 1 workflow module — `review_pr_workflow.py:185` | `f"review-pr-{task.pr_number}-{int(time.time())}"` | a third shape, in a workflow rather than a runner |

**Three of those eleven were missed by the sweep that commissioned this re-plan**, which named eight and named one file that does not exist. That is not a criticism of the sweep — it is the property `base_ref`'s docstring predicts, reproduced, on the next value of the same shape. **A hand-sweep of a scattered derivation misses members; the remedy is to stop scattering it.**

**And `review_pr` shows what the scatter costs beyond duplication.** [`run_review_pr.py:126-130`](../../../scripts/workflows/temporal/scripts/run_review_pr.py) passes `worktree_name=None` into the run bag with the comment *"The ONE workflow that cuts no worktree — it reviews a PR in place … so `-` in a bag means 'this run had none' and never 'somebody forgot the argument'."* **The workflow it then calls cuts one**, at `review_pr_workflow.py:185`, via the same `worktree_add` whose docstring opens *"ISOLATION IS AN INVARIANT, NOT A PARAMETER."* So a real worktree exists on disk and the run's own record says it does not. **Nothing is lying; the two halves were written in two places and only one of them was updated.** That is the class this phase closes.

---

## Requirements for completion

1. **A frozen run context exists, and it is constructed once, at the dispatch boundary.** It extends the `RunIdentity` frozen dataclass already at [`dispatch_identity.py:114`](../../../scripts/workflows/temporal/scripts/dispatch_identity.py) rather than sitting beside it. It carries, at minimum: the run id, the writer, whether the name was minted, the repository root, the journal root, the workflow key, the per-run worktree name, the pull-request number if there is one, and the target the run was pointed at — the component under plan or the research pool. It is frozen after construction, and nothing downstream re-derives a field it carries.

2. **No entrypoint and no workflow module assembles a run-scoped derived value for itself.** The worktree name is derived once, inside the context, from the workflow key the context already holds — closing the eleven sites in § *The evidence this rests on*. **A check holds it**, and the check is a syntactic one over the tree it can actually see: no file under `scripts/` or `modules/` may construct a worktree name. *This is not the deleted population check wearing new clothes — it asserts an ABSENCE at a shape a grep can match, rather than deriving a population of derivations, which is the thing measured not to exist.*

3. **A run states its context once, on the live path, before the first side effect** — and the run that dispatches prints it, not only the rehearsal. **It is printed when the context was CONSTRUCTED by this process and not when it was handed in**, which is the discriminator `RunIdentity.minted` already carries for the run id. See § *Requirement 3's trade is RULED, and the ruling is "there is no trade"*.

4. **The `--dry-run` preview and the live run print the same object.** A rehearsal that builds its own copy previews something that is not what runs, and this family has shipped that bug once already.

5. **A wrong derivation is DEMONSTRATED to be visible.** Point a run at the wrong component, capture the echo verbatim, and show the output names what it derived **before the run costs anything**. Requirements 1–4 are not complete without it, and it is not asserted from reading the code.

### The produced half — MOVED, and this is a pointer rather than a deletion

**What were requirements 4 and 5 on 2026-08-18 are now [Every producer names its consumer](phase6_every_producer_names_its_consumer.md)'s requirements 1 and 3, carried verbatim**, together with the sections that supported them. **Nothing was dropped in the move.** Those numbers are not reused here.

---

## Dependencies

- **[Decompose the build families and codify the shape](roadmap.md)** — complete. The activities layer this mechanism lives in came out of it.
- **Nothing outside this component.** No sibling component and no external system gates this.
- **[Dual-mode children](phase3_dual_mode_children.md) — not a gate, and the direction reversed on 2026-08-28.** This phase used to sit after that one. Under the ruling it sits **before** it, and the reason is producer-and-consumer rather than preference: that phase adds nine standalone entrypoints, and an entrypoint handed a run context is cheaper to write than one that assembles its own and is converted later. **Nine new runners written before the context exists are nine new members of the eleven-site class this phase is closing.** This phase's own proof runs against `plan-feature`, which exists, so nothing here waits on those nine.
- **[What configuration a run absorbed](phase5_configuration_a_run_absorbed.md)** — no dependency in either direction, **and the boundary between them is worth stating because they sound alike.** This phase is about what a run **derived**; that one is about what a run **absorbed** from `~/.claude/`. Different question, different mechanism, and the digest is that phase's. *If this phase lands first, that phase's digest has an obvious home as one more field on the context — a pairing, not a dependency.*
- **[Every producer names its consumer](phase6_every_producer_names_its_consumer.md)** — the produced half, split out of this document on 2026-08-28. Neither gates the other. **The echo this phase builds is itself a producer**, so that phase's gate is what should catch it if it is ever removed.

---

## What this phase decides

### Requirement 3's trade is RULED, and the ruling is "there is no trade"

**This requirement used to be a separate requirement carrying an open trade, and it is now folded into requirement 3 with a decision.** The old wording asked that *"a parent can silence the echo without destroying the record,"* and the plan recorded honestly that nobody had measured the cost: echoing costs output, and the caller that most wants quiet — a parent running nine children — is the caller that most needs the derivation recorded.

**The ruling deleted the premise.** That trade was about an echo scattered through a run. **One structured line at the top of a run is a different proposition**, and it does not need a suppression flag:

- **The precedent is in the module being extended.** `resolve_identity` already announces a minted run id **on stderr, and unconditionally** — its own comment says so — for exactly this class of value, with the reasoning that *"a name nobody was told is a bag nobody can [find]"*. A second unconditional line beside it is consistent with a ruling this fleet already made and shipped.
- **The discriminator that matters already exists and it is not verbosity.** A parent that constructs a context and hands it to nine children should print it once; a child that was **handed** one should not reprint what its parent already said. That is `RunIdentity.minted` generalised — **constructed here, or received** — and it is a fact the object already tracks rather than a flag somebody has to remember to pass.
- **So `verbose` does not gate the context line.** `verbose` governs a workflow's own chatter. The context line is not chatter; it is the run saying what it is about to spend money on.

**What this gives up, stated.** An operator who genuinely wants a silent run gets one line on stderr anyway. That is the same cost `resolve_identity` already imposes and the same argument justifies it. **If a future measurement shows the line is a real cost, the remedy is a flag on the context's construction, not a per-call-site suppression** — do not reintroduce the scattered version.

### The five properties, and what the object does to them

**The five-property frame is CONVENTION, not measurement, and the paper it rests on says so.** [`research/synthesis.md`](research/synthesis.md) records that the industry position on facet 2 is *"argued by convention across five sources, never evidenced by data"*, and states it as a gap (§6.2). The table below is still the right frame — five sources agreeing is worth acting on — but nothing downstream should read its columns as measured.

| Property | State today | What this phase does |
|---|---|---|
| **Anchored on a marker** | ✅ satisfied — `resolve_repo_root` runs `git rev-parse --show-toplevel`, which reads `.git` and never guesses | nothing; record it as satisfied so it is not rebuilt |
| **Explicit override** | ✅ satisfied — `--repo` exists and is documented as *a FILESYSTEM PATH, never a gh slug* | nothing |
| **Published algorithm** | ❌ absent | **the object's field and its docstring.** Not a table somebody maintains — the algorithm sits on the field that carries the value |
| **Echo of what was derived** | ⚠️ partial — exists under `--dry-run`, absent on the live path | requirements 3 and 4 |
| **Stated scope of effect** | ❌ absent | **the object's field docstrings**, same place, same reason |

Source: [`research/synthesis.md`](research/synthesis.md) § *Facet 2's real work is three missing properties*, resting on [`raw/invocation_contract.md`](research/raw/invocation_contract.md) §2.2 (M1–M5), §4.2 and §5.2.

**The change from the previous plan is where properties 3 and 5 live**, and it is the whole of the ruling's effect on this table. They used to be columns in a published enumeration that a check held honest against the tree. They are now **docstrings on the fields of one object**, which cannot go stale relative to a population because there is no population — there is one object, and a field either exists on it or does not.

### "Prefer derivation" is NOT the rule, and writing it would contradict a shipped decision

The tempting generalisation from this phase is *derive where you can*. **Do not write it.** This repo already made the opposite call in one specific place and made it correctly: **repo identity is declared** — `--repo`, explicitly never derived from the working directory — **while component scope is derived** from the path the run was pointed at.

Derivation is a **per-value decision with a stated reason**, not a policy. A run context does not change this: it changes where a derived value is *computed and recorded*, not which values are derived. **A value that should be declared is declared, and then travels on the context as a declared value.**

### The scope of effect is not decoration — it is what makes the echo readable

`resolve_repo_root`'s own comments already record what a wrong answer costs: `.claude/worktrees/` and `.claude/logs/` both hang off it, so a run rooted at a subdirectory scatters worktrees and logs where `/cleanup-merged-worktrees` never looks, and a later cleanup deletes the logs along with the workspace — after which cost accounting for those runs is unrecoverable. **Six of seven V2 entrypoints once dropped repo-root resolution and used the working directory instead.**

That paragraph is the model for a field's scope-of-effect docstring. An echo that prints a path tells a reader *what* was derived; the scope of effect is what tells them whether to care.

### Where the rule is published, and it is a smaller ask than it was

**The TABLE is gone as a deliverable.** The enumeration is the object's fields, so there is nothing to publish separately and nothing for a check to hold honest against a tree. **Two destinations previously considered and rejected stay rejected and are now moot**: a table inside `workflow-scripts.md` (a standard states the rule, never the inventory) and a table in [`docs/guide/workflows.md`](../../guide/workflows.md) (right audience, wrong distance from the code).

**The RULE survives and still needs an address.** It is now: *a run-scoped derived value is a field on the run context, computed once at the dispatch boundary and passed down; it is not re-derived by a callee.* That is a standards amendment against [`workflow-scripts.md`](../../standards/workflow-scripts.md) § *9. Repo Root Operation*, which today governs the one derivation this fleet already rules on and is the section a widened rule extends. **It also finishes a sentence [`docs/guide/workflows.md`](../../guide/workflows.md) already starts** — *"Isolation is established once by the parent and passed down — a child never creates its own worktree"* — which is this rule, stated for one value.

**Surface it, do not file it, and never edit the standard:** [`finding-routing.md` §7](../../standards/finding-routing.md) gives a producing run the surfacing and `review-pr` the filing, and a build dispatch for this phase is a producing run.

### The fork that was deleted, and why the record is kept

**[`roadmap.md`](roadmap.md), [`phase6_every_producer_names_its_consumer.md`](phase6_every_producer_names_its_consumer.md) and this component's candidates all cite a Branch A / Branch B fork that no longer exists in this plan.** It is recorded here rather than erased, so a reader arriving from one of those citations is not left guessing.

**What it said.** Requirement 1 used to demand that the enumeration's population be read off the derivation sites rather than hand-kept, justified by [Every producer names its consumer](phase6_every_producer_names_its_consumer.md)'s gate, whose population is `_MEASURE.glob("*.py")`. **The analogy did not hold**: files-in-a-directory is a syntactic definition and a derivation site has none. Branch A hoped the five named resolvers were a usable proxy; Branch B was the case where they were not, forcing either a tree-wide marker convention or the hand-kept list the requirement forbade.

**What settled it.** The check ran cold on 2026-08-28 and returned **Branch B** — three of six named values reached no resolver, and four marker patterns returned zero hits across 225 Python files.

**Why neither branch was taken.** The operator ruled that the fork was a symptom. A requirement that needs a tree-wide marker convention to enumerate its own subject is an audit tool built for a mess; the cheaper move is to stop having eight places to audit. **The clause is deleted rather than weakened, and neither horn was chosen** — which is why nothing in this document reads "we picked the hand-kept list."

**One property of the deleted clause is preserved and should not be lost:** *a table checked against itself cannot see what was never added to it.* Requirement 2's absence check is that property, done at a shape a grep can actually match.

### What this phase does not do

- **It does not touch dual-mode invocation.** That is [Dual-mode children](phase3_dual_mode_children.md).
- **It does not add a new derived value.** Every value in scope already exists; this phase gives them one home and one voice.
- **It does not build a config digest.** What a run absorbed from `~/.claude/` is [What configuration a run absorbed](phase5_configuration_a_run_absorbed.md).
- **It does not put every computed value on the context.** The context carries values that are **run-scoped** — true for the whole run, derived once at the boundary. `paper_currency` and `due_papers` are computed per research pool inside the work and are deliberately excluded; putting a mid-run computation on a frozen boundary object would be the wrong shape and would make the object a grab-bag.
- **It does not extend the producer/consumer gate, define a producer, or rule any surface in or out.** All of that is [Every producer names its consumer](phase6_every_producer_names_its_consumer.md). **The one thing this phase owes that phase is a fact rather than work:** the echo it builds is itself a producer, and it should appear in that phase's population rather than be exempted for having been built here.
- **It does not add validation.** Containment of operator-supplied paths is handled one layer up. This phase is about visibility, not safety.

---

## Implementation steps

- [ ] Extend `RunIdentity` into the run context: add the repository root, journal root, workflow key, worktree name, pull-request number and the run's target, keeping it a frozen dataclass. Give each field a docstring carrying its marker, its algorithm in one sentence, its override if it has one, and its scope of effect.
- [ ] Decide and record where the journal root is resolved. It is resolved **inside** `open_run_bag` today; a context that carries it either resolves it at the boundary or is populated from the bag's answer. **Either is defensible and the choice is not obvious** — resolving at the boundary means a bad journal root stops the run one step earlier, and it also means `open_run_bag` stops owning a decision it has always owned. Write down which and why.
- [ ] Derive the worktree name once, inside the context, from the workflow key it already carries. **Reconcile `review_pr` explicitly** — either it cuts a worktree and the context says so, or it does not; today `run_review_pr.py` records `worktree_name=None` while `review_pr_workflow.py` cuts `review-pr-<n>-<ts>`.
- [ ] Replace the eleven inline assemblies with the context's field. **`run_build_minor.py` is a behaviour change, not a refactor** — its worktree is currently named `build-…` under `workflow_key="build-minor"`, so deriving from the key renames it. That is the drift being fixed; say so in the commit rather than letting it look incidental.
- [ ] Add the check that no file under `scripts/` or `modules/` constructs a worktree name, and mutate it in both directions to prove it discriminates.
- [ ] Print the context once, on stderr, at the top of the live run and before the first side effect, gated on **constructed-here** rather than on `verbose`.
- [ ] Rebuild the `--dry-run` preview to print the same object the live run prints, rather than its own assembly of the same values.
- [ ] Run the full suite and confirm nothing that depended on the quiet path or on a worktree name's current spelling broke.

**The proof, and it is requirement 5:**

- [ ] Add a test that a run's output names the target it derived. **The echo is itself a producer** — this test is its consumer, and [Every producer names its consumer](phase6_every_producer_names_its_consumer.md)'s gate should be what catches it if it is ever removed. If that phase has not landed, record here that the echo is a producer it is expected to cover.
- [ ] Run against a deliberately wrong component path, capture the output verbatim, and confirm the derived target is named before any side effect. Record the transcript in this doc.

---

## Runtime Verification

**Date:** 2026-08-18 · **Host:** `puma-workstation-mint` · **Runtime verified:** `git`, which is the marker the repository-root field anchors on.

The claim being verified is that `git rev-parse --show-toplevel` returns the repository root rather than the invocation directory, so the anchor is a fact and not a guess.

```
$ git --version
git version 2.43.0

$ cd scripts/workflows/temporal && pwd
/home/puma/Repos/claude-dot-files/.claude/worktrees/plan-feature-1787093087/scripts/workflows/temporal

$ git rev-parse --show-toplevel
/home/puma/Repos/claude-dot-files/.claude/worktrees/plan-feature-1787093087
```

**Observed:** invoked three directories down, git returned the worktree root, not the working directory. The marker property holds on this host at this version.

**Re-verify when this doc is substantially revised** — and note the second-order fact this output demonstrates: the root returned here is a **worktree** root, which is the correct answer for a dispatch and would be the wrong answer for a tool expecting the main checkout. **That distinction belongs in the repository-root field's scope-of-effect docstring**, which is where a scope of effect now lives.

**The produced half's verification moved with it** — see [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) § Runtime Verification.

---

## Notes and gotchas

- **The echo is not logging.** Logging is for the person diagnosing a failure; the echo is for the person about to spend an hour of model time on the wrong component. It goes where they will see it before the run commits to anything, which is why requirement 5 checks *before any side effect* rather than *somewhere in the transcript*.
- **`--dry-run` already does most of this well, and that is the trap.** Reading the dry-run block makes the echo look built. It is built in the one mode where nothing is at stake — and requirement 4 exists so that fixing it does not leave two assemblies behind.
- **The boundary is narrower than "the entrypoint".** `resolve_identity` is called **after** the `--dry-run` early return, deliberately: a dry run states *"nothing invoked, nothing posted"*, and minting a name would make that false. A run context that mints or announces has the same exemption. **A context built for a dry run must be buildable without the announcing and without the minting**, or the dry-run contract breaks.
- **Do not let the object become a grab-bag.** The test for a field is *run-scoped and derived once at the boundary*. A value computed inside the work, from an argument the work was handed, is not a context field however convenient it would be to reach.
- **An object handed down is not the same as an object in scope.** The point of injection is that a callee cannot silently re-derive. If a callee still calls `resolve_repo_root` because it is importable, the context has been added without removing the thing it replaces, and the fleet now has two answers where it had one.
- **The producer-gate notes moved with the split.** Its shape, and the ratchet-as-backlog pattern for a large ruled-in population, are in [Every producer names its consumer](phase6_every_producer_names_its_consumer.md) § Notes and gotchas.
