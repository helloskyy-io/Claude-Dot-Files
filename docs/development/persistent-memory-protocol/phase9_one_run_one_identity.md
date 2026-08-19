# Phase 9 — One run, one identity, one bag

**Component:** [Persistent Memory Protocol](roadmap.md) · **Status:** not started · **Gate:** none. It depends on [Phase 1](phase1_the_run_bag.md), which is complete.

## What this phase does

[Phase 1](phase1_the_run_bag.md) built the folder a run writes into and keyed it by a run id. It did not say **who names a run**, because at the time there was only one shape a run could take: a parent, started from a terminal, minting its own name on the way in.

Two decisions made after Phase 1 was planned end that. Under the Temporal port an entrypoint becomes a client that starts a workflow, and a name minted inside a retried step is a **new name on every attempt**. Under [Workflow Decomposition Phase 3](../workflow-decomposition/phase3_dual_mode_children.md) nine children that today can only be started by a parent get runners of their own — so an invocation that is not a parent, and may or may not be a run, can now begin.

This phase settles both with one rule: **the fleet has exactly one authority that names a run, the name is handed *to* the journal rather than made *by* it, and every shape an invocation can take resolves to exactly one bag under exactly one name.**

**Terms used here.** A **bag** is one run's folder in the journal, never edited after the run ends (the name is BagIt's, the file-layout standard the folder follows — never a Docker container). A **run id** is the name of one dispatch and the key its bag is filed under. A **writer subfolder** is the per-writer directory inside a bag that lets concurrent children write without sharing a file. An **entrypoint** is a file a run starts from; a **child** is a workflow another workflow starts.

---

## Why this is a phase and not a line in another one

**It cannot go in [Phase 1](phase1_the_run_bag.md).** That phase is complete and its requirements are a record of what was built. A number names a phase for life, and re-opening a closed one to add work is how a completion record stops meaning anything.

**It could go in [Phase 3](phase3_the_emit_rule.md), and should not.** Phase 3 already owns two members of the identity family — the machine id (r6) and event identity under retry (r7a) — so run identity looks like a third. Two things argue against folding it in. Phase 3 is the largest phase in this component, carrying twelve requirements plus a write-path inventory whose two halves need different mechanisms; adding a fourth concern to it makes the phase a project. And **the deadlines differ**: Phase 3 is gated on nothing and pressed by nothing, while this phase has two external clocks — it must land before [Workflow Decomposition Phase 3](../workflow-decomposition/phase3_dual_mode_children.md) ships nine new entrypoints, and before the Temporal port's Stage B wraps anything as an activity. A phase with a deadline buried inside a phase without one is a deadline nobody schedules against.

**And it is the phase two other components have to read.** Both of the clocks above belong to somebody else. A constraint stated inside Phase 3's twelfth requirement is a constraint the port's planner will not find.

---

## Requirements for completion

1. **There is exactly one authority in the fleet that names a run, and it is named in this document.** The per-model-invocation `run_id` the run log mints inside `run_claude` is a **different value with the same name** — a parent and its three children carry four of them, and none addresses the run. It is either retired or explicitly distinguished, in code and in prose, so that "the run id" resolves to one thing when read by a person or by a tool.
2. **The run id is an INPUT to bag-open, not minted inside it.** A caller supplies the name; the journal records it. This is the property that survives an at-least-once retry, and it is the property a deterministic replay requires — a name generated inside replayed code is a different name on the second pass.
3. **Opening a bag twice under one run id yields one bag, not two — demonstrated.** That is the shape a retry takes, and it is the only requirement here whose failure is silent: two bags for one run reads as two runs forever after.
4. **A child started on its own is journaled, and the rule for which bag it writes into is stated and ENFORCED.** Its own bag when the invocation is the run; a writer subfolder of its parent's bag when it is not. **The input that distinguishes the two cases is named and passed, never inferred** — inferring it from an environment variable, a working directory or the absence of one is how a child silently becomes its own run.
5. **The enumerating sweep's population covers every shape that can start a run**, and any shape it deliberately excludes is named in its failure text rather than left to a reader to discover. Today the predicate is one glob over one directory; nine entrypoints are about to be added to that directory by another component, and a sweep that silently covers or silently misses them is equally useless.

**Requirement 2 stays UNCHECKED until its shape is agreed with the Temporal port, and that is deliberate.** The port has its own reasons to name a dispatch — workflow id, run id, and two orthogonal reuse policies — and this component lands first, so what is written here is a *constraint on a shared design* rather than a specification imposed on a component that has not been planned. See § *The identity is a joint design* below. **Built is not proven**: the mechanism can be built and demonstrated against a local retry, and the requirement still does not close until the port's side of the name exists.

---

## Dependencies

- **[Phase 1](phase1_the_run_bag.md)** — hard, and **satisfied**. The bag, its key and the writer subfolder all exist.
- **[Phase 3](phase3_the_emit_rule.md)** — *this phase is a dependency OF Phase 3*, not the other way round. Phase 3 threads the run id down to the children that emit; it needs to know what the value is and who owns it first.
- **[Workflow Decomposition Phase 3](../workflow-decomposition/phase3_dual_mode_children.md)** — not a gate in either direction, and **that is the problem this phase exists to prevent**. Whichever lands first sets the contract for the other, and nine adapters each inventing their own answer is the failure mode that component names for itself one phase over.
- **[Temporal Integration](../temporal-integration/temporal-integration.md)** — not a gate. Its Stage B is a *deadline*, not a precondition: after Stage B, changing where a name is minted means changing wrapped activities rather than plain functions.

---

## What this phase decides

### The measured starting position, stated so nobody re-derives it

As of 2026-08-19, verified in the tree:

| Fact | Where |
|---|---|
| The run id is `uuid.uuid4().hex`, generated inside the journal package | `modules/journal/journal_activities.py` — `mint_run_id` |
| Eleven entrypoints call it inline, as `open_run_bag(run_id=mint_run_id(), …)` | `scripts/workflows/temporal/scripts/run_*.py` |
| That exact call shape is pinned by a test | `tests/unit/test_every_parent_opens_a_run_bag.py` |
| The swept population is one glob over one directory | `tests/unit/journal_entrypoint_facts.py` — `ENTRYPOINTS_DIR`, `run_*.py` |
| A second, unrelated `run_id` exists, minted per model invocation | `mint_run_id`'s own docstring says so |

**Nothing above is wrong for the world Phase 1 shipped into**, and the phase doc that built it says why the entrypoint is the right place for the call. What changed is the number of shapes an invocation can take.

### Why an identity minted inside the work is the defect and not a detail

The reliability pool that now sits under [Temporal Integration](../temporal-integration/temporal-integration.md) surveyed six systems that name a unit of work — Temporal, GitHub Actions, GitLab, systemd, message queues, and the IETF `Idempotency-Key` draft — and found none that mints the name inside the work. Its ruling is that generation belongs on the *input* side and that moving it costs one parameter, and it states that this must precede Stage B of the port.

**The corroboration is local and it is not hypothetical.** That pool also recorded that identity-by-generated-name has already failed in this repo once: re-enumerating the archived run logs returned files named for scripts that no longer exist, because two naming authorities were live at the same time. This phase's requirement 1 is that finding applied forward.

*Cited from [`temporal-integration/research/synthesis.md`](../temporal-integration/research/synthesis.md) §3 and its candidate table, which is the consumption surface for that pool; the underlying paper is `raw/durable_dispatch_identity.md` (Critic: PASS-WITH-FIXES, 2026-08-07). **This document did not open the raw paper** — the synthesis carries the claim with its section pointers, and re-reading the pool behind a synthesis is what the Research Standard tells a consumer not to do.*

### A standalone child is the case the bag was never designed for, and it has two wrong answers

[Workflow Decomposition Phase 3](../workflow-decomposition/phase3_dual_mode_children.md) builds nine runners so that every child *"runs standalone and under a parent, equally well."* Applied to the journal, "equally well" has two readings and they produce opposite records:

- **Every invocation opens its own bag.** A parent and its three children then file four bags for one piece of work, and the join that makes the journal answer *"what happened"* is gone. This is the failure the plan's own § *One location, a folder per run* warns about in a different costume — it rejected path-keying precisely because it scattered one logical run across several folders.
- **Only parents open bags.** Then a child run started by a person leaves no record at all, and the component's central claim — *if any store gets it, the journal gets it* — is false for a whole invocation mode.

**Neither is a default anybody should reach by accident, which is why requirement 4 makes the discriminator an explicit input.** A child that receives a run id joins that bag through a writer subfolder; a child that receives none *is* the run and opens its own. The value travels the same way every other invocation fact does.

**⚠ And the guard fires either way, which is the part that makes this urgent rather than tidy.** The bag sweep enumerates `run_*.py` in one directory. Nine new runners landing there are swept, and the suite goes red until each opens a bag — pushing whoever lands them toward the first wrong answer above, under time pressure, with a failing test as the argument. Nine landing anywhere else are invisible, which is the second. **The sweep is about to make this decision for us unless it is made first.**

### The identity is a joint design, not a requirement imposed on the port

This is the same shape the roadmap already records for the machine id, and the reasoning transfers whole: this component lands first, so what it writes is an *input* to the port's design rather than a constraint on it. What this phase needs from the eventual answer is three properties and no mechanism —

- a name **supplied by the caller**, so a retry and a replay both reproduce it;
- a name that is **stable across the whole run**, not per step and not per model invocation;
- a name that **maps onto whatever the orchestrator already calls a dispatch**, rather than sitting beside it as a second identity.

The third is the one that decides whether this is cheap or a migration. If the port's workflow id can *be* the run id, this phase is a parameter change. If it cannot, there are two names for one thing and something has to join them — which is a decision, and it is the port's to make with this constraint in hand.

**Where "neither wins by default" lives.** The roadmap's § *Constraints that run BOTH ways with the Temporal port* already names [the local Temporal addendum](../../standards/temporal/claude-dot-files-addendum.md) as the artifact the machine-identity decision lands in. Run identity is the second constraint with the same shape and the same destination.

---

## Implementation checklist

- [ ] Enumerate every place a run id is generated or read today, from the tree rather than from this document, and record the command that enumerated it
- [ ] Rule requirement 1: retire the second `run_id` or rename one of the two, and state which and why — a value that means two things is not fixed by documenting both meanings
- [ ] Move generation to the caller: the run id becomes a parameter of bag-open with no default, on the same argument the `worktree_name` parameter already carries in that function
- [ ] Decide and write down where a caller gets the name when there is no orchestrator yet, and what supplies it once there is
- [ ] Make opening a bag twice under one run id idempotent, and add the test that demonstrates it — the failure being silent is the reason it is a test and not a note
- [ ] Rule requirement 4: name the input that distinguishes *this invocation is the run* from *this invocation is part of one*, and pass it explicitly
- [ ] Wire the standalone-child case: a child with a run id writes to a writer subfolder of that bag; a child without one opens its own
- [ ] Widen the sweep's population to every shape that can start a run, and state the excluded shapes in its failure text
- [ ] Verify against a real parent-plus-children run that one run produces one bag with one subfolder per writer, and record what was observed
- [ ] Verify a standalone child invocation produces exactly one bag and no orphan, and record what was observed
- [ ] Re-read this document's § *The measured starting position* against the tree and correct any row that has moved
- [ ] Run the full suite

---

## Notes and gotchas

- **The pinned call shape is a feature, not an obstacle.** `test_every_parent_opens_a_run_bag` asserts a literal call form, so changing where the id comes from will fail that test loudly. That is the guard working: the change is meant to be visible at every call site.
- **`--dry-run` is already an exemption from the sweep** and must stay one. A dry run states *"nothing invoked, nothing posted"*, and a bag would falsify it.
- **Do not solve requirement 4 by looking at the environment.** A child can be started by a parent, by a person, or by a person reproducing what a parent did — and those look identical from inside the process. Only a value passed in distinguishes them.
- **Retiring the second `run_id` is a rename with reach.** It appears in the run log this component is superseding, and the roadmap already carries a standards amendment saying that log's join key **changes meaning** from per-model-invocation to per-run. This phase is where that change becomes real, so the amendment's trigger and this phase should be read together.
- **This phase records no hours.** Sizing is `plan-verify`'s.
