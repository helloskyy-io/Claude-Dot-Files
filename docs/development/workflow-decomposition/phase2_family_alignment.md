# Family alignment

**Component:** [Workflow Decomposition](roadmap.md) · **Status:** complete — all five requirements delivered; requirement 3 was allowed to fail and did (κ = 0.000), so ruling is per-family · **Gate:** none

## What this phase does

Children in the same family — `build_refine` and `build_refine_minor`, `research_write` and `research_write_minor` — do nearly the same job, and their prompts were written by copying. A copy that stops being updated does not announce itself: the two files still look like two files, and the reader who opens one has no way to tell that the other gained eleven rules it never received. That is not hypothetical. It happened, and every PMP phase built from a plan ran without the rule that tells a run how much rigour a change warrants.

The mechanism half is built. A block appearing verbatim in two children must live in `modules/assistant/prompts/` and be referenced by placeholder; a frozen baseline forgives the duplication that existed when the rule landed and ratchets both ways, so the list can only shrink. It has, and it ran out: **48 rows, then 13, then none** — the last thirteen are the ones this phase ruled on, and `ACCEPTED` is now empty.

What is left is the half a test was never able to decide. A copy that has already **drifted** is invisible to a verbatim matcher, and it is the more dangerous kind, because a difference reads as a decision. Deciding whether it *was* one is a judgement about a person's intent, and this phase's job is to make that judgement **reproducible and written down** rather than to automate it — which the evidence says cannot be done.

**Terms used here.** A **family** is a workflow and its `_minor` sibling, or two children that do the same job in different families. The **baseline** is the frozen list in `test_prompt_blocks_are_shared_not_copied.py` naming each block that was already duplicated when the rule landed. To **promote** a block is to move it into the shared pool and leave a placeholder behind. **Fork-vs-parameterize** is the question this phase answers: when two copies differ, was the difference chosen, or did one copy simply stop being maintained?

---

## Requirements for completion

1. **A written ruling procedure exists for a drifted pair**, and it is the four-signal ordering from [`fork_vs_parameterize_drift_signal.md`](research/raw/fork_vs_parameterize_drift_signal.md) §4.2 — fit-to-referent first, then context similarity of the two sites, then drift *pattern*, then stated rationale. It is applied by a person and never by a threshold.
2. **Every row in the frozen baseline is either gone or carries a written ruling.** 13 rows on 2026-08-18. "Gone" means promoted; "ruled" means a sentence saying which signal decided it and why.
3. **The procedure has been validated before it is trusted.** A blind classification followed by a reveal of the commit history, scored for accuracy, with the disagreement recorded — including if it is bad. An unvalidated procedure applied to 13 rows produces 13 confident guesses.

   > **MEASURED 2026-08-19, and it FAILED — see [`fork_vs_parameterize_blind_trial.md`](fork_vs_parameterize_blind_trial.md).** Two shell-less raters, classifications sealed in commit `beb103f` before any history was read, scored against a co-evolution audit. **Cohen's κ = 0.000**, below the 0.271 benchmark, so ruling moved to per-family and requirement 2 is satisfied at that granularity.
   >
   > **Two sentences in this requirement were falsified by running it, and the corrections are the finding rather than an erratum.** *(a)* It asks for the trial to be *"scored for accuracy"* and treats accuracy as the thing that decides. Accuracy and agreement pointed in OPPOSITE directions here: one rater scored 6/7 while κ was 0.000, because it returned DELIBERATE on all seven and the population is 6/7 deliberate. **A constant classifier scores 6/7 on this sample without reading anything.** Both numbers must be reported or the result is whichever one the reader is shown. *(b)* It says an unvalidated procedure produces *"13 confident guesses"* — implying the risk is scattered, low-confidence answers. The measured failure was the opposite shape: **high agreement on a single confident answer**, arrived at by the default-to-intentional convention this phase's own § *Do NOT import* forbids, and wrong on exactly the pair where that default is wrong.
4. **What a `_minor` tier's prompt is FOR is stated somewhere a guard can cite.** Not "less thorough" — a contract that says which categories of guidance are tier-invariant and which are not. Without it, every reconciliation is re-argued from first principles and lands differently each time.
5. **A deliberate variant states its own rationale**, in one line, where the variant lives. This is the cheapest of the four signals and the only one that can be *created* rather than recovered.

**Requirement 3 is deliberately allowed to fail. IT DID, AND THE FALLBACK IS WHAT SHIPPED.** The blind trial showed the procedure is not reproducible on this corpus, so the ruling is recorded per *family* — one ruling per category of guidance, in `FAMILY_RULINGS` — rather than as 13 per-pair guesses. **The procedure is not retired:** it is what a reviewer applies when a guard surfaces a pair, and the trial improved it (see the trial's § 5.4). What it lost is the claim that two reviewers would reach the same answer.

---

## Dependencies

- **Nothing outside this component.** The mechanism, the ratchet and the standard's wording all shipped.
- **Inside it:** none. This phase does not need [Phase 4](phase4_nothing_invisible.md), [Phase 3](phase3_dual_mode_children.md) or [Phase 5](phase5_configuration_a_run_absorbed.md), and none of them needs it. **One-way note:** [Phase 3](phase3_dual_mode_children.md) writes nine new runners from one template in one sitting, which is the exact shape this phase's duplication ratchet exists to catch — so it must not hand that baseline nine new rows.

**Four open candidates are inputs to this phase and are not re-derived here.** They were filed by build and review passes on PR #100, they are untriaged, and each one names a decision this phase's work runs into: **C-uva9dsox** (a promotion has no fidelity check, and the pool has no content floor after promotion), **C-rm2g8ope** (whether a surfacing-only detector counts as a "test" under the standard's own sentence), **C-at80groo** (nothing defines what a `_minor` tier's prompt should contain — the evidence for requirement 4), **C-yq30mgwd** (a child may hold a drifted near-copy of a *pool* fragment and no guard can see it at any granularity). See [`candidates.md`](../../../tracked/candidates/). **Whoever builds this phase reads those four first**; three of them describe blind spots in the very guards this phase leans on.

---

## What this phase decides

### The ruling is a person's, and the evidence is explicit that it must be

Two independent reasons, and the second is the one that closes the question.

**Intent is a property of a person's awareness, not of a text.** The artifact records what happened, not whether anyone meant it. Every retrospective method in the literature is inferring an unobservable from a proxy.

**And the proxy is weak.** The one field study that measured inter-rater agreement on exactly this classification reports **κ = 0.271** — "fair" by convention, and that number is the *ceiling* on any rule built from the same signals, ours included. A gate that scores a pair and acts on the score is asserting a confidence nobody has ever measured at above fair.

**So: reasoning written down, never an automated gate.** A detector may *surface* a pair. It may not rule on one.

### Fit-to-referent and drift pattern — never similarity magnitude

The instinct is to reach for a percentage, and the evidence says the percentage is the one signal nobody uses. **Drift *pattern* is a used signal; drift *magnitude* is not.** Two copies differing only in named entities and parameters are a parameterized pair; two copies where whole blocks are present in one and absent in the other are a neglected copy — and both of those can sit at the same similarity score.

This repo already learned it the expensive way. The standard once carried three named similarity figures; **two of the three were falsified by the promotions in the very pull request that wrote them.** The figures are gone, a test now derives prose counts rather than allowing them to be typed, and this phase does not reintroduce them in another form.

> **Test-plan item 5 is already satisfied and this phase does not carry it.** The paper's §7 item 5 asks to publish the method behind `85.8% / 76.1% / 62.1%` or drop the figures. Verified 2026-08-18: they appear nowhere in `docs/standards/workflow-scripts.md` and survive in the test modules only as recorded history of their own removal. Recorded here rather than dropped silently, because the synthesis still carries it as an open candidate.

### Do NOT import the field's default-to-intentional convention

The literature, unable to reach an author, defaults to calling an unexplained difference **deliberate**. That default is conservative *for a research hypothesis* — it avoids over-claiming that developers are sloppy.

**Our failure mode runs the other way.** A neglected copy misread as a deliberate variant is exactly the defect this phase exists to catch, and the default would launder every one of them. Where a signal is genuinely absent, the honest output is *unruled*, not *deliberate*.

### Four ways a pair needs no ruling at all

Applied first, these keep the procedure from being run 13 times when it is needed fewer:

1. **The pair is byte-identical** — the verbatim ratchet already decided it.
2. **The rationale is already written down** — signal 4 short-circuits the rest.
3. **The two children genuinely do different jobs** — a child doing different work may legitimately repeat a sentence.
4. **The copies are short-lived** — a tree under active decomposition may diverge on its own before a reconciliation would pay for itself.

---

## Implementation steps

- [x] Read the four open candidates (C-uva9dsox to C-yq30mgwd) and record which of them the work about to be done depends on. Two describe blind spots in the guards this phase uses.
- [x] Write the ruling procedure — the four signals in order, the four short-circuits, and the rule that absence of a signal yields *unruled* rather than *deliberate*. Place it where a reviewer will find it at ruling time, not in a standard nobody opens mid-pass.
- [x] Pick the sample for the blind trial from the drifted pairs, and **seal the classifications before any history is consulted.** Record which signal drove each call.
- [x] Reveal the commit history for each pair in the sample and score the blind classifications against it. **Record the accuracy, including a bad one.**
- [x] Rule on the outcome: if agreement is at or below the field's κ = 0.271 benchmark, ruling moves from per-pair to per-family and requirement 2 is satisfied at that granularity instead. Write down which was chosen and why.
- [x] Apply the procedure to every remaining baseline row. For each: promote it, or record the ruling and the signal that produced it.
- [x] Verify the baseline shrank for every promotion — the ratchet fails on a fixed entry left behind, so a promotion that does not remove its row is caught by the suite rather than by a reader.
- [x] Write the `_minor` tier contract: which categories of guidance are tier-invariant, which are genuinely tier-specific. Two disposition rules already known to be tier-invariant are frozen with two consumers each, so reconciling them is a cross-family promotion rather than a contract question — do those separately and do not let the contract ruling block them.
- [x] Add the one-line `differs from <sibling> because <reason>` convention for a deliberate variant, and verify a new variant without one is visible to a reviewer.
- [x] Run the full suite and confirm the duplication and drift guards are green with the baseline at its new size.
- [x] Re-read this phase's requirement 3 against what was actually measured, and correct any sentence here that the measurement falsified.

---

## Runtime Verification

**Not applicable, and stated rather than omitted.** This phase orchestrates no external runtime — no daemon, no service, no vendor API. Its entire surface is prompt text under `modules/assistant/` and pytest modules under `scripts/workflows/temporal/tests/unit/`. The [Documentation Standard's Live-Runtime Verification rule](../../standards/documentation/documentation_standard.md) is satisfied by there being no runtime to verify; the measured facts this doc asserts (13 baseline rows, the similarity figures' absence) were read off the tree on 2026-08-18 at the branch point and are re-derivable by the suite.

---

## Notes and gotchas

- **A promotion is not free, and the direction of the risk flips.** While text is duplicated, a one-sided edit is a divergence some detector can see. Once shared, deleting a sentence removes it from every consumer at once and nothing diverges — measured on this tree, with the whole suite staying green after a shared fragment was gutted. C-uva9dsox carries the remedy; do not treat promotion as the safe default without reading it.
- **The similarity of two copies is not the finding, and a reviewer will reach for it anyway.** If a ruling's written reasoning contains a percentage, the ruling was made on the one signal the evidence says nobody uses.
- **`plan_feature` + `plan_verify` are one family, and `research_write` + `research_write_minor` are tier siblings** — a note in the baseline once called the whole remainder "cross-family" and was wrong on both counts. Check the pair before assuming what kind of pair it is.
