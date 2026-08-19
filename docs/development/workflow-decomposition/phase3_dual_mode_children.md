# Phase 3 — Dual-mode children

**Component:** [Workflow Decomposition](roadmap.md) · **Status:** not started · **Gate:** none — the ruling this phase waited on was made on 2026-08-19

## What this phase does

Twenty workflows live in `scripts/workflows/temporal/modules/assistant/`. **Eleven of them can be started by a person; nine cannot.** The nine are all children, and the gap is not a missing feature inside them — each one's core function is written, tested and reachable in-process. What is missing is the outer half of a shape the other eleven already have: a runner that defines the CLI contract, and a thin shim that hands its arguments through.

This phase closes that gap, for all nine, and proves it by running each of them alone.

**Why that is worth a phase, and not a chore:** a child in this fleet is not good out of the box. Getting one to behave takes repeated isolated runs — change the prompt, run it, read what came back, change it again. A child with no standalone entrypoint can only be exercised **through its parent**, which means every iteration pays for the whole chain. Measured the same week the ruling was made: `research_verify` needed three fix rounds, each one re-run through a full parent chain, while `plan-feature` was corrected standalone in one.

> **Children EARN autonomous operation; they do not start with it.** A child that cannot be run alone cannot be exercised, so it can never earn anything. The ability to exercise a child cannot be the reward for a child already working.

### The contradiction this phase used to be blocked on, and how it was resolved

This phase was planned on 2026-08-18 as a roadmap entry with no phase doc, because two live statements said opposite things. [`workflow-scripts.md`](../../standards/workflow-scripts.md) then read that running a child by hand was *"recovery … never the interface"*; the roadmap checkbox said every child runs standalone and under a parent *"equally well"*. No evidence decided between them — it was a design ruling, and [`research/synthesis.md`](research/synthesis.md) explicitly declined to make it.

**The operator ruled on 2026-08-19: standalone invocation is an INTERFACE.** The standard was the side that was wrong and has been corrected in place — [`workflow-scripts.md` § Composition](../../standards/workflow-scripts.md) now reads *"A parent invokes children, AND every child is independently runnable by hand. Both are first-class; standalone is an interface, not a recovery hatch."* There is no longer a contradiction to plan around, and the nine are a backlog rather than a deliberate narrowing.

**Terms used here.** A **runner** is the `run_<workflow>.py` that owns the CLI contract — the arguments, their help text, and the exit code. A **shim** is the `<workflow>.sh` beside it, thin by design: it resolves the interpreter and passes every argument through untouched, so there is exactly one place the CLI is defined. A **core function** is the plain callable a parent imports and calls directly. The shape is **two entrypoints, one core** — the field's converged answer, and already this fleet's, for the eleven that have it.

---

## Requirements for completion

1. **Each of the nine children has a runner and a shim**, on the same two-entrypoints-one-core pattern the eleven existing pairs use. A parent still calls the core function directly; nothing about how a parent invokes a child changes.
2. **The five known failure surfaces are handled explicitly, not inherited by copying.** Verbosity, exit-code semantics, interactive-prompt blocking, stream discipline, and working-directory assumptions — each is a place a standalone caller and a parent want different behaviour. See § *The five places standalone and parent-driven diverge*.
3. **The shim-naming guard covers all twenty**, extended in the same change that adds the nine. `test_shim_usage_names_itself.py` exists because three earlier entry scripts shipped with usage text copied from whichever script they were cloned from. Adding nine adapters without extending the guard risks that defect at three times today's scale.
4. **`research_refresh_parent` has an entrypoint of its own.** Not "becomes invocable" — it already is. See § *The roadmap checkbox's premise is wrong as measured*.
5. **Each of the nine is DEMONSTRATED to run alone, end to end**, with the invocation and what came back recorded. Constructing a runner is not the deliverable; the deliverable is a child a person can exercise, and only running it shows that. This is the phase's end-to-end proof and requirements 1–4 are not complete without it.

---

## Dependencies

- **Nothing outside this component.** No sibling component and no external system gates this.
- **[Phase 4](phase4_nothing_invisible.md) and this phase meet at requirement 2's verbosity clause, and neither blocks the other.** Phase 4 rules what a run echoes about what it derived, and what a parent may silence. A standalone caller is the caller that wants that echo loud. **If Phase 4 lands first, these nine adapters inherit its ruling; if this phase lands first, it makes the ruling nine times more valuable and nine times more expensive to get wrong.** Either order works — what does not work is nine adapters each inventing their own answer.
- **Not gated on [Phase 5](phase5_configuration_a_run_absorbed.md) or [Phase 2](phase2_family_alignment.md).**

---

## What this phase decides

### The nine, counted off the tree

Twenty workflow modules exist; eleven have a `run_*.py` / `*.sh` pair in `scripts/workflows/temporal/scripts/`. The nine without, verified against the tree on 2026-08-19:

| Family | Children with no standalone runner |
|---|---|
| build | `build_draft`, `build_draft_minor`, `build_refine`, `build_refine_minor` |
| research | `research_write`, `research_write_minor`, `research_verify`, `research_refresh`, `research_refresh_parent` |

**All nine are children and all nine already work** — each is imported and called by its parent today. Nothing here is a rewrite. The arithmetic is worth stating because it is the phase's whole scope claim: 20 modules − 11 pairs = 9, and the two lists above and in § Runtime Verification were counted independently and agree.

### The five places standalone and parent-driven diverge

These are not hypothetical. Each is a first-party observation recorded in [`raw/invocation_contract.md`](research/raw/invocation_contract.md), and each is a decision the nine adapters must make deliberately rather than inherit from whichever sibling they were cloned from.

- **Verbosity inversion** — a person running one child wants to see what it is doing; a parent running nine wants one line each. This fleet already gets the mechanism right: `verbose` is an explicit parameter, never sniffed from the terminal. **Do not add TTY detection here.** No first-party source found recommends detection without an explicit override, and the fleet's existing choice is the safer one.
- **Exit-code semantics** — a parent reads a return value; a shell reads `$?`. A child whose failure is a returned object and whose runner exits `0` is a child that looks fine to every caller that is not a parent.
- **Interactive-prompt blocking** — anything that would wait for a human hangs forever under a parent and looks like a stall rather than a question.
- **Stream discipline** — what goes to stdout is a result somebody may pipe; what goes to stderr is narration. A child that mixes them is unusable in a shell and merely noisy under a parent, which is why the defect survives.
- **Working-directory assumptions** — **measured: six of seven V2 entrypoints once dropped repo-root resolution and used the working directory instead.** A standalone caller can be anywhere in the tree. `preflight.resolve_repo_root` is the existing answer and the nine must use it rather than re-deriving one.

### The roadmap checkbox's premise is wrong as measured, and the fix is narrower than it reads

The pre-existing checkbox says *"`research_refresh_parent` has no entrypoint — a parent nothing can invoke."* **That is false as measured**, and a build dispatch decomposing it as written will scope the wrong fix.

`research_refresh_parent` **is** invocable: `run_research.py --refresh` imports it and calls `run_research_refresh`, and `research.sh <dir> --refresh` reaches the same path — the shim's own usage block documents it. The real defect is narrower: **it has no entrypoint of its own**, no `research_refresh.sh` beside the other shims, so it is reachable only as a mode of a sibling's runner. It is the same defect as the other eight, one layer less visible.

**The checkbox is carried verbatim into [`roadmap.md`](roadmap.md) anyway**, because a planning run does not reword a completion criterion. This paragraph is the correction, and requirement 4 is what a builder works from. Source: [`raw/invocation_contract.md`](research/raw/invocation_contract.md) §5.1.

### What this phase does not do

- **It does not change how a parent invokes a child.** A parent imports the core function and calls it. Adding an outer entrypoint does not make that path go through a subprocess, and routing parent calls through the shim would trade a function call for a process spawn and lose the return value's type.
- **It does not make a child good.** It makes a child *exercisable*, which is the precondition for making it good and is a different claim. Improving what a child produces belongs to Self Improvement.
- **It does not add TTY detection, or any other implicit mode switch.** See the verbosity bullet above.
- **It does not touch the eleven that already have pairs**, except to extend the naming guard across all twenty.

---

## Implementation steps

- [ ] Read the two-entrypoints-one-core shape off an existing pair before writing any of the nine — the runner owns the CLI, the shim resolves the interpreter and passes everything through, and the core function stays the parent's path.
- [ ] Rule the five divergences in § *The five places standalone and parent-driven diverge* once, written down, before the first adapter — nine adapters each answering these independently is exactly the drift [Phase 2](phase2_family_alignment.md) exists to stop.
- [ ] Confirm requirement 3's ruling with [Phase 4](phase4_nothing_invisible.md)'s echo contract if that phase has landed; if it has not, record the answer here so [Phase 4](phase4_nothing_invisible.md) inherits it rather than contradicting it.
- [ ] Build the four build-family adapters: `build_draft`, `build_draft_minor`, `build_refine`, `build_refine_minor`.
- [ ] Build the five research-family adapters: `research_write`, `research_write_minor`, `research_verify`, `research_refresh`, `research_refresh_parent`.
- [ ] Give `research_refresh_parent` an entrypoint of its own rather than leaving it as a flag on a sibling's runner, and decide what happens to `run_research.py --refresh` — keeping it as an alias and removing it are both defensible; leaving the question unanswered is not.
- [ ] Extend `test_shim_usage_names_itself.py` to the full population of twenty, and confirm it fails on a deliberately mis-named usage block before trusting that it passes.
- [ ] Check each new adapter against the shared-prompt rule — nine near-identical runners are precisely the shape [Phase 2](phase2_family_alignment.md)'s duplication ratchet watches for, and this phase must not hand it nine new rows.
- [ ] **Demonstrate requirement 5:** run each of the nine standalone, with the cheapest invocation that reaches real work, and record the command and what came back. A child that constructs but does not run has not met this phase's bar.
- [ ] Verify each parent still invokes its children unchanged, with the existing parent-path tests green.
- [ ] Run the full suite.

---

## Runtime Verification

**Date:** 2026-08-19 · **Host:** `puma-workstation-mint` · **Runtime verified:** the workflow entrypoint surface itself — the shim/runner inventory this phase's scope claim rests on, and the fact that a child with no entrypoint is nonetheless a working callable.

```
$ ls scripts/*.sh | wc -l
11

$ ls scripts/build_draft.sh scripts/run_build_draft.py
ls: cannot access 'scripts/build_draft.sh': No such file or directory
ls: cannot access 'scripts/run_build_draft.py': No such file or directory

$ PYTHONPATH=. python3 -c "from modules.assistant.build.build_draft import build_draft_workflow as d; print([n for n in dir(d) if n.startswith('run_')])"
['run_draft']

$ ./scripts/plan_verify.sh --help
usage: plan-verify [-h] [--repo REPO_TARGET] [--candidates CANDIDATES]
                   [--pr PR_NUMBER] [--verbose] [--dry-run]
                   component
[…]
  --dry-run             count and render; no model, no spend
```

**Three things observed:**

1. **Eleven shims exist**, against twenty workflow modules — the count this phase's scope rests on, taken off disk rather than off a list.
2. **`build_draft` has neither a shim nor a runner, and its core function `run_draft` imports and is callable.** This is the phase in one output: the work is done, the door is missing. The nine are adapters, not implementations.
3. **An existing pair answers `--help` and exits 0**, with a `--dry-run` that spends nothing. That is the target shape, and it is also how requirement 5's demonstration can be run cheaply for children whose real work is expensive.

**Re-verify before the build dispatch fires.** The counts above are the scope claim; a workflow added or an adapter landed between now and then changes the arithmetic, and this phase is sized on it.

---

## Notes and gotchas

- **Nine adapters is a copying event waiting to happen.** They will be written in one sitting, from one template, by one run — which is the exact condition that produced the drifted pairs [Phase 2](phase2_family_alignment.md) is still ruling on. Reach for the shared mechanism first and accept a slightly heavier first adapter.
- **The shim is thin ON PURPOSE and the temptation is to thicken it.** Argument parsing lives in the runner so there is one definition of the CLI contract. A shim that validates, defaults, or reorders arguments creates a second one, and the two diverge silently.
- **A child's parent is not its only caller after this phase, and its return type still matters.** The runner translates a returned object into an exit code; it does not replace the object. A child that starts returning a string because "the shell only needs a message" has broken its parent.
- **`research_refresh_parent` is a parent as well as one of the nine.** It orchestrates refresh children, so its adapter is the one place in this phase where the standalone caller is starting a chain rather than a leaf. Expect its verbosity and exit-code answers to differ from the other eight, and record why.
