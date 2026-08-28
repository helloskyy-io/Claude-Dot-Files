# Dual-mode children

**Component:** [Workflow Decomposition](roadmap.md) · **Status:** not started · **Gate:** none — the ruling this phase waited on was made on 2026-08-19

## What this phase does

Twenty workflows live under `scripts/workflows/temporal/modules/assistant/`, across the four workflow families `build/`, `plan/`, `research/` and `review_pr/`. **Eleven of them can be started by a person; nine cannot.**

> **Count the four families, not the directory's subdirectories.** This sentence used to read *"live in `modules/assistant/`"* with no qualifier, and that stopped being enough on 2026-08-26: `modules/assistant/tracked/` now sits beside the four families and is a **library package** — `tracked_items.py`, `intake.py`, `recurrence.py` — with no workflow in it and no entrypoint owed. A builder recounting from the directory listing gets five subdirectories and finds one that does not fit the arithmetic. **The twenty and the nine are unchanged by it; only the sentence that produces them was wrong.** Re-verified on disk 2026-08-28 — see § *Re-verification — 2026-08-28*.

The nine are all children, and the gap is not a missing feature inside them — each one's core function is written, tested and reachable in-process. What is missing is the outer half of a shape the other eleven already have: a runner that defines the CLI contract, and a thin shim that hands its arguments through.

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
5. **Each of the nine is DEMONSTRATED to run alone, end to end**, with the invocation and what came back recorded. Constructing a runner is not the deliverable; the deliverable is a child a person can exercise, and only running it shows that. This is the phase's end-to-end proof and requirements 1–4, 6 and 7 are not complete without it.
6. **The nine adapters are ruled as ONE family, once, before the first is written** — not pair-by-pair afterwards. [Family alignment](phase2_family_alignment.md) shipped with its per-pair ruling procedure measured at **κ = 0.000** and demoted to advisory; per-FAMILY ruling is the granularity that replaced it. Nine near-identical runners written from one template in one sitting are a single category of guidance, and this phase inherits the obligation to rule them that way. See § *What this phase inherits from the blind trial in *Family alignment**.
7. **The mechanism the nine share is EXTRACTED before they are written**, not detected afterwards. **No guard in this repo can see duplication in a Python runner** — the fact that makes requirement 6 cost a design decision rather than a lookup. See § *The runner corpus has no duplication guard, and this phase's own notes assume one*.

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

### What this phase inherits from the blind trial in *Family alignment*

[`sprint.md`](../sprint.md) records that [Family alignment](phase2_family_alignment.md) shipped with an open question this phase inherits, and until 2026-08-28 the inheritance existed only in that sentence. It is named here because it changes how the nine get built.

**What was measured.** [`fork_vs_parameterize_blind_trial.md`](fork_vs_parameterize_blind_trial.md) scored two blind raters against revealed history at **κ = 0.000**, against the field's benchmark of 0.271. *Family alignment*'s requirement named that threshold in advance as the trigger to change granularity, so it fired: **ruling moved from per-pair to per-family**, a per-pair verdict is now advisory, and the rulings that emptied the frozen duplication baseline live as `FAMILY_RULINGS` — *one per category of guidance, not one per pair*.

**Why it lands on THIS phase and not on whichever happens to be next.** This phase's own § Notes already says the nine adapters are *"a copying event waiting to happen … written in one sitting, from one template, by one run."* That is the exact population the demoted procedure would otherwise be asked to rule on afterwards — **and it would rule at chance.** The remedy is not a better reviewer; it is **ruling the category before the copies exist**, which is what per-family granularity means in practice and is the only order in which it is cheap.

**Concretely, requirement 6 is satisfied when** the nine adapters carry ONE ruling naming which parts of a runner are family-invariant — argument parsing shape, exit-code translation, the `resolve_repo_root` call, the usage block's self-naming — and which are legitimately per-child, with each deliberate variant carrying *Family alignment*'s `differs from <sibling> because <reason>` line. **Nine separate rulings is the failure, not the fallback.**

**What this does NOT claim.** κ = 0.000 came from seven pairs and two LLM raters, and the trial names both limits itself. It is not evidence that per-pair ruling is impossible — it is the reason this phase does not *depend* on per-pair ruling being reproducible, which is a weaker and sufficient claim.

### The runner corpus has no duplication guard, and this phase's own notes assume one

**Measured 2026-08-28, and both halves of [Family alignment](phase2_family_alignment.md)'s alignment apparatus are scoped to prompt markdown.**

1. **The duplication ratchet reads `ASSISTANT.rglob("prompts/*.md")`** (`tests/unit/test_prompt_blocks_are_shared_not_copied.py:137`). Its population is prompt blocks under `modules/assistant/**/prompts/`. **A Python file under `scripts/` is not in it, cannot add a row to the frozen baseline, and cannot turn the module red.**
2. **`FAMILY_RULINGS` is keyed on prompt-fragment stems** (`tests/unit/fork_vs_parameterize.py`), and its validator rejects any ruling naming no category from the `_minor` tier contract. All eight of those categories are categories of *prompt guidance*, so **a ruling covering nine Python runners cannot be expressed in that mechanism at all.**

**The consequence, and it is why requirement 7 exists.** This phase's implementation step says to check the new adapters against the shared-prompt rule *"and this phase must not hand it nine new rows"* — **but that guard cannot receive a row from a Python file, so a builder who runs the suite and sees green has been told nothing.** The nine would land unguarded *while a guard appears to be watching*, which is worse than landing unguarded knowingly.

**It has already happened at seven, and that is evidence rather than worry.** [`C-8tv8ewto`](../../../tracked/candidates/C-8tv8ewto.md) records seven existing runners carrying a byte-identical `try/except RuntimeError -> print -> return 1` block. It was found by a review agent on a pull request, not by any guard, and the ratchet was green throughout. **Nine more takes the corpus to twenty on one template.**

#### The ruling, made here so the build does not re-litigate it

Three remedies were on the table ([`C-7q2m4xzb`](../../../tracked/candidates/C-7q2m4xzb.md)). **This phase adopts two of them and rejects one, and the rejection is the part worth reading.**

- **ADOPTED — share the mechanism before the copies exist (requirement 7).** [`C-8tv8ewto`](../../../tracked/candidates/C-8tv8ewto.md)'s `parse_or_exit(parser, argv)` in `preflight.py` is the concrete first instance, and promoting it *before* the nine are written fixes the existing seven at the same time. This is [Family alignment](phase2_family_alignment.md)'s own promotion rule — *the consumer count decides, never taste* — applied to a population that rule's mechanism cannot see.
- **ADOPTED — say plainly that the corpus is unguarded**, which is this section. Requirement 6's family ruling is therefore **prose a reviewer applies, not something a suite holds**, and a builder must not read a green suite as coverage here.
- **REJECTED — extending a similarity ratchet to `run_*.py` with a frozen baseline.** It is the obvious move and it measures the wrong thing. **The nine runners are *supposed* to be near-identical** — that is what a family is — so a magnitude-based ratchet over them either freezes an enormous baseline or fires constantly, and this component's own research is explicit that *"when ruling on a drifted pair, check fit-to-referent and drift pattern, not inter-copy similarity magnitude"* ([`research/synthesis.md`](research/synthesis.md) § *What this means for us — Phase 2*). **Detection is not available on this corpus; prevention is.** *(This rejection is a ruling, not a closed question: if the shared mechanism turns out not to cover the next duplicated block, a guard becomes worth re-opening — and the reasoning above is what it would have to beat.)*

### Where the divergence ruling lands

Requirement 2 says the five divergences are ruled once and written down, without saying **where** — and an address-less ruling is one a tenth adapter will not find.

**The natural destination is a named standard with an actionable anchor:** [`workflow-scripts.md`](../../standards/workflow-scripts.md) § *Composition*, which already carries this component's parent/child rule and was corrected in place on 2026-08-19 to make standalone an interface. That is the section the ruling extends.

**The mechanism is: SURFACE it, do not file it, and never edit the standard.** [`finding-routing.md` § 7](../../standards/finding-routing.md) is explicit that a **producing run surfaces a standards amendment in its PR body and `review-pr` files it** into [`tracked/standards/`](../../../tracked/standards/); `ratification` is the operator's alone. A build dispatch for this phase is a producing run, so it writes the amendment into its PR with the target document and an anchor precise enough to act on, and stops there.

**Until it is ratified the ruling still binds this phase** — it is recorded in this doc and the nine adapters are built against it. What surfacing buys is that the ruling survives this phase closing, rather than living only in nine source files that whoever writes the tenth has to re-derive.

### Where the family ruling lands

**Requirement 6's ruling needs its own address, and it is not the same one.** Requirement 2 rules five *behavioural divergences between standalone and parent-driven invocation*; requirement 6 rules *what is invariant across a family of nine runners*. They are different artifacts answering different questions, and giving the second no destination is the failure the section above describes — with a sharper edge, because the invariants outside those five divergences are the ones nothing else records. **When this phase closes, the twenty-first runner's author re-derives them.**

**The destination is [`workflow-scripts.md`](../../standards/workflow-scripts.md) § *Required Features*.** That section already enumerates what every workflow script must carry — the verbose flag, the JSONL logging, the `run_claude` helper, repo-root operation — which *is* the fleet's existing statement of runner invariants. The family ruling extends it with the invariants this phase settles: argument-parsing shape, exit-code translation, the `resolve_repo_root` call, and the usage block's self-naming. **The anchor is that section's scope paragraph**, which today splits task-execution from analysis workflows and is where a third distinction — invariant versus legitimately per-child — belongs.

**It does NOT go where [Family alignment](phase2_family_alignment.md)'s rulings go, and that is the whole point of requirement 7's section above.** `FAMILY_RULINGS` in `tests/unit/fork_vs_parameterize.py` is keyed on prompt-fragment stems and its validator rejects any ruling naming no category from the `_minor` tier contract — all eight of those categories are categories of *prompt guidance*. **A ruling about nine Python runners cannot be expressed in that mechanism at all**, so a build dispatch must not try to file it there and read the resulting silence as coverage.

**The mechanism is the same as requirement 2's: SURFACE it, do not file it, never edit the standard.** [`finding-routing.md` § 7](../../standards/finding-routing.md) gives a producing run the surfacing and `review-pr` the filing. **Two amendments, two anchors, surfaced as two items** — bundling them into one is a defect, because a reviewer would have to rule on both together and they can be ratified independently.

**Until it is ratified the ruling still binds this phase**, exactly as requirement 2's does: it is recorded in this doc and the nine adapters are built against it.

### What this phase does not do

- **It does not change how a parent invokes a child.** A parent imports the core function and calls it. Adding an outer entrypoint does not make that path go through a subprocess, and routing parent calls through the shim would trade a function call for a process spawn and lose the return value's type.
- **It does not make a child good.** It makes a child *exercisable*, which is the precondition for making it good and is a different claim. Improving what a child produces belongs to Self Improvement.
- **It does not add TTY detection, or any other implicit mode switch.** See the verbosity bullet above.
- **It does not touch the eleven that already have pairs**, except to extend the naming guard across all twenty.

---

## Implementation steps

- [ ] Read the two-entrypoints-one-core shape off an existing pair before writing any of the nine — the runner owns the CLI, the shim resolves the interpreter and passes everything through, and the core function stays the parent's path.
- [ ] Rule the five divergences in § *The five places standalone and parent-driven diverge* once, written down, before the first adapter — nine adapters each answering these independently is exactly the drift [Phase 2](phase2_family_alignment.md) exists to stop.
- [ ] **Write that ruling as ONE family ruling covering all nine, per requirement 6** — naming what is invariant across the nine and what is legitimately per-child, and giving each deliberate variant *Family alignment*'s `differs from <sibling> because <reason>` line. Do this before the first adapter is written; ruling nine copies afterwards is the granularity that phase's trial measured at chance.
- [ ] **Extract the shared mechanism BEFORE writing any of the nine, per requirement 7** — starting with [`C-8tv8ewto`](../../../tracked/candidates/C-8tv8ewto.md)'s `parse_or_exit(parser, argv)` in `preflight.py`, which fixes the existing seven at the same time. **Do not wait for a guard to catch the duplication; no guard on this corpus can.**
- [ ] Re-run § *Re-verification — 2026-08-28*'s inventory commands and confirm the arithmetic still reads 20 − 11 = 9 before building anything; a workflow added since the last dating changes the scope this phase is sized on.
- [ ] Confirm requirement 3's ruling with [Phase 4](phase4_nothing_invisible.md)'s echo contract if that phase has landed; if it has not, record the answer here so [Phase 4](phase4_nothing_invisible.md) inherits it rather than contradicting it.
- [ ] Build the four build-family adapters: `build_draft`, `build_draft_minor`, `build_refine`, `build_refine_minor`.
- [ ] Build the five research-family adapters: `research_write`, `research_write_minor`, `research_verify`, `research_refresh`, `research_refresh_parent`.
- [ ] Give `research_refresh_parent` an entrypoint of its own rather than leaving it as a flag on a sibling's runner, and decide what happens to `run_research.py --refresh` — keeping it as an alias and removing it are both defensible; leaving the question unanswered is not.
- [ ] Extend `test_shim_usage_names_itself.py` to the full population of twenty, and confirm it fails on a deliberately mis-named usage block before trusting that it passes.
- [ ] Check each new adapter against the shared-prompt rule **for any PROMPT content it carries — and do not expect the ratchet to see the Python.** Its population is `prompts/*.md`; the runner corpus is outside it, which is what requirement 7 exists to compensate for. See § *The runner corpus has no duplication guard*.
- [ ] **Demonstrate requirement 5:** run each of the nine standalone, with the cheapest invocation that reaches real work, and record the command and what came back. A child that constructs but does not run has not met this phase's bar.
- [ ] Verify each parent still invokes its children unchanged, with the existing parent-path tests green.
- [ ] **Surface the five-divergence ruling in the PR body as a standards amendment** against [`workflow-scripts.md`](../../standards/workflow-scripts.md) § *Composition*, with the target and anchor named. **Do not edit the standard and do not file the item** — a producing run surfaces and `review-pr` files. See § *Where the divergence ruling lands*.
- [ ] **Surface requirement 6's family ruling in the PR body as a SECOND, separate standards amendment** against [`workflow-scripts.md`](../../standards/workflow-scripts.md) § *Required Features*, naming what is invariant across the nine runners and what is legitimately per-child. **Two anchors, two items — do not bundle it with the step above**, and do not attempt to file it into `FAMILY_RULINGS`, which structurally cannot hold a ruling about Python. See § *Where the family ruling lands*.
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

### Re-verification — 2026-08-28

**Date:** 2026-08-28 · **Host:** `puma-workstation-mint` · **Runtime verified:** the same entrypoint surface, re-counted nine days on, because the tracked stores landed inside `modules/assistant/` in the interval and because the sizing note this phase carried was measured against a stale runner range.

```
$ ls scripts/workflows/temporal/scripts/*.sh | wc -l
11

$ ls scripts/workflows/temporal/scripts/run_*.py | wc -l
11

$ ls scripts/workflows/temporal/modules/assistant/
assistant_activities.py  build  convergence.py  __init__.py  plan  prompts
research  resource_telemetry.py  review_pr  routing.py  tracked

$ wc -l scripts/workflows/temporal/scripts/run_*.py | sort -n | sed -n '1p;6p;11p'
  116 scripts/workflows/temporal/scripts/run_research_minor.py
  135 scripts/workflows/temporal/scripts/run_plan_sprint.py
  372 scripts/workflows/temporal/scripts/run_plan_verify.py

$ wc -l scripts/workflows/temporal/scripts/*.sh | sort -n | sed -n '1p;11p'
  13 scripts/workflows/temporal/scripts/plan_project.sh
  18 scripts/workflows/temporal/scripts/research_minor.sh
```

**Three things observed:**

1. **Still eleven shims and eleven runners**, and still twenty workflows across the four families. **The arithmetic 20 − 11 = 9 is unchanged, and so is the list of nine** in § *The nine, counted off the tree*.
2. **`modules/assistant/tracked/` is new since the original count and is NOT a workflow family** — a library package, no workflow, no runner owed. It is why § *What this phase does* now names the four families rather than the directory.
3. **The runner range the sizing note was written against is stale, and this is the correction.** [`roadmap.md`](roadmap.md) recorded *"runners run 88–172 lines, shims 13–18"* on 2026-08-19. **Measured here: the eleven runners span 116–372 lines with a median of ~135; the shims are unchanged at 13–18.** The range moved because `run_plan_verify.py` (372) and `run_triage_candidates.py` (117) landed in the interval. **The nine adapters are modelled on these eleven, so the range is the shape of the work** — and the outlier at 372 is worth reading before assuming an adapter is a hundred-line job.

**Re-verify before the build dispatch fires.** The counts above are the scope claim; a workflow added or an adapter landed between now and then changes the arithmetic.

---

## Notes and gotchas

- **Nine adapters is a copying event waiting to happen.** They will be written in one sitting, from one template, by one run — which is the exact condition that produced the drifted pairs [Phase 2](phase2_family_alignment.md) is still ruling on. Reach for the shared mechanism first and accept a slightly heavier first adapter.
- **The shim is thin ON PURPOSE and the temptation is to thicken it.** Argument parsing lives in the runner so there is one definition of the CLI contract. A shim that validates, defaults, or reorders arguments creates a second one, and the two diverge silently.
- **A child's parent is not its only caller after this phase, and its return type still matters.** The runner translates a returned object into an exit code; it does not replace the object. A child that starts returning a string because "the shell only needs a message" has broken its parent.
- **`research_refresh_parent` is a parent as well as one of the nine.** It orchestrates refresh children, so its adapter is the one place in this phase where the standalone caller is starting a chain rather than a leaf. Expect its verbosity and exit-code answers to differ from the other eight, and record why.
