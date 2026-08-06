# Decide-Only Disposition: Does a Judging Stage With No Authoring Authority Reduce Defects?

```
Topic:          Does a judging stage that has fresh context AND no authority to edit the work
                actually reduce defects — or does it just add a stage? Specifically: are the two
                claimed mechanisms (fresh context; no authoring authority) separately evidenced?
Feeds:          docs/standards/architecture/problem-statement.md § "What is known" element 2
                ("one that authors, one that judges with no stake in the work, one that
                dispositions"); validates docs/standards/workflow-scripts.md § Composition
                (the author ≠ judge and decide ≠ act seams) and
                docs/standards/architecture/system-overview.md § "Where the seams are".
Last validated: 2026-08-06
Revalidate:     medium — 2 months
                (Justification per §5: the paper is mixed-volatility and takes its fastest-decaying
                claim. The classical inspection core [S1][S2][S3] is Low and will not move. But two
                load-bearing inputs are fast: the vendor-position layer flipped once inside ten
                months — Cognition's "Don't Build Multi-Agents" [S22] was superseded by its own
                follow-up [S23] on 2026-04-22 — and five cited results are 2026 preprints. Taking
                the Medium band's fast end rather than High because nothing here is a pricing page
                or an API surface; the underlying question is a research question, and research
                questions do not resolve in four weeks.)
Confidence:     DEFINITIVE that same-actor same-context self-correction fails on reasoning
                ([S4][S5][S6][S7], all first-party abstracts fetched from the arXiv API) and that
                LLM judges carry measurable self-preference, position and verbosity biases
                ([S14][S15][S16]).
                DEFINITIVE (transcribed from scanned page images, see §6.0) that the human
                antecedent states the decide≠act rule explicitly and gives a reason — Fagan 1976
                [S1] — and that it was never isolated as a variable.
                DIRECTIONAL that FRESH CONTEXT improves defect detection on review-shaped tasks:
                the on-domain evidence is real but thin — one single-author 2026 preprint with a
                controlled design [S9], one benchmark result on aggregation rather than sequence
                [S10], one first-party vendor engineering post [S23].
                UNVERIFIED / GAP — and this is the paper's central negative finding — that NO
                AUTHORING AUTHORITY does anything on its own. No study located, in fifty years of
                human inspection research or in the LLM literature, isolates "the reviewer cannot
                edit" as an experimental variable. Search method in §6.1 N1/N2.
                DERIVED (marked inline) on the adjudication of the pool's internal contradiction
                and on the regime discriminator taken from [S18]'s own stated prediction.
Critic:         not-yet-verified — 2026-08-06
```

---

## 0. Verdict, stated first because the rest is 6,000 words

**The design's two claimed mechanisms are not equally evidenced, and the repo currently states them as one thing. They should be separated.**

| Mechanism | Status | Best evidence |
|---|---|---|
| **Fresh context** — the judge does not carry the author's reasoning | **Supported, directionally, on-domain.** Removing production history measurably beat keeping it in a controlled 360-review experiment; the field's own critical survey explicitly excludes the cross-actor case from its negative results; the nearest commercial system reports the same mechanism in production. | [S9], [S5], [S23] |
| **No authoring authority** — the judge cannot quietly patch what it found | **Unevidenced as an isolated variable.** It is a 1976 design rule with a stated rationale and no isolating experiment since, in humans or in LLMs. The one adjacent measured result is a *warning*, not a support: reviewer precision and critique uptake are empirically separable. | [S1] (rule + rationale), [S25] (the warning), N1/N2 (the gap) |

**So: element 2 is half-validated.** "Distinct actors at distinct layers" has on-domain support for the *distinct context* part. "One that judges with **no stake in the work**" — the authority-separation part, the part the seams table calls `decide ≠ act` — rests on an unexamined 1976 heuristic and on this repo's own priors. That is an acceptable finding, not a failure; but the standard should not claim measured backing it does not have, and §7 gives the experiment that would settle it in one afternoon of dispatches.

**Three corrections to the existing pool follow from this paper and are listed as candidates in §4.6.** The most important: `case_against.md`'s D7 is contradicted by its own primary source, which carves out exactly this repo's topology.

---

## 1. Primer — three regimes that the literature constantly conflates

Almost every published result on "can an LLM check its own work" belongs to exactly one of three regimes. They give **opposite answers**, and reading a result from one regime as evidence about another is the single most common error in this literature and the fastest way for this paper to have gone wrong.

| Regime | Shape | What the evidence says |
|---|---|---|
| **R1 — Intrinsic self-correction** | One model, one context window, generates then critiques then revises, with no external signal | **It fails.** Performance *degrades*. [S4][S6][S7] |
| **R2 — External feedback** | A signal from outside the generator: a sound verifier, a test suite, a compiler, a separately-trained critic, or a fresh instance with no production history | **It works, conditionally.** Gains are large where the external signal is *sound*; smaller and noisier where the external signal is itself an LLM. [S5][S6][S8][S9] |
| **R3 — Multi-agent decomposition** | Several agents coordinating, often concurrently, often writing to shared state | **Contested, and mostly negative under matched compute.** [S18][S19][S22] |

**This repo's design is R2 wearing R3's clothes, and that ambiguity is what the pool is arguing about.** Concretely, from the shipped scripts:

- `build-draft` authors a change and opens an unreviewed PR.
- `build-refine` — a **separate `claude` process with no inherited context** — reviews and corrects it. This actor *can* edit.
- `review-pr` — a third separate process — is **decide-only**. Its prompt states: *"You do not fix the code yourself (you are decide-only)"* and *"You take almost NO actions. You do NOT merge, close, fix, dispatch, or edit standards/sprints"* (`scripts/workflows/children/review-pr.sh` lines 196, 204). It emits one disposition comment and one terminal `VERDICT: MERGE | HOLD - redispatch | HOLD - needs-assistance` line, which the parent parses (`scripts/workflows/build-minor.sh` line 281).
- A human or the parent acts on that ruling. On `HOLD - redispatch` the parent loops back exactly once.

Two properties matter for classifying it: the actors are **sequential, never concurrent**, and only one of the three **writes to the artifact**. That combination is the fulcrum of §3.6.

**One honesty note about the design as built.** `review-pr` is not *purely* decide-only. Its prompt grants exactly one write authority — filing GitHub Issues for qualifying deferred work — described in the source as *"the single write authority granted below"* (line 204). The rationale given is that it is the only actor with no scope of its own to offload. This does not touch the artifact under review, so it does not compromise the mechanism, but a paper claiming "no authoring authority" should say that the shipped implementation has one carve-out. *(Confidence: definitive — read from the repo's own script.)*

### 1.1 What "no authoring authority" is actually claiming

The claim decomposes into two sub-claims that are worth separating because only one of them is plausible on its face:

- **(a) No stake.** A judge that did not write the code has nothing to defend. — This is *not* a claim about authority; it is a claim about **provenance**, and it is satisfied by any separate actor, editing or not. `build-refine` already satisfies it.
- **(b) A finding must be STATED rather than absorbed.** An actor that can fix what it finds may fix it silently; the finding then never enters the record, never reaches a human, and never accumulates into the improvement loop. — **This is the authority claim, and it is the one nobody has measured.**

Sub-claim (b) is the interesting one, and it is *not* primarily a defect-detection claim at all — it is an **observability** claim. That reframing matters for the experiment design in §7 and is the first thing this paper found that neither pool paper says. *(Confidence: **derived**, from the text of `review-pr.sh` and the problem statement's element 2. No source located frames authority separation this way — see N3.)*

---

## 2. The specific options — the four topologies actually on the table

Not "multi-agent yes/no." These four, in ascending order of separation:

| # | Topology | Who reviews | Can the reviewer edit? | Evidence class |
|---|---|---|---|---|
| **T1** | Same-session self-review | The author, same context | Yes | R1 — measured, and it is the *worst* option in the one controlled on-domain study [S9] |
| **T2** | Fresh-context reviser | A separate process, artifact only | Yes | R2 — this is `build-refine` |
| **T3** | Fresh-context decide-only judge | A separate process, artifact only | **No** | R2 — this is `review-pr`. **No published study isolates this cell.** |
| **T4** | Concurrent multi-writer subagents | Several, in parallel, on shared state | Yes | R3 — this is where the failure evidence is strongest [S19][S22] |

The pool's fight is about whether T3's evidence should be inherited from T2 (in which case it looks good) or from T4 (in which case it looks bad). §3.6 argues it should be inherited from T2, on the authority of T4's own strongest critic.

---

## 3. Comparative landscape

### 3.1 The human antecedent — the rule exists, is fifty years old, and was never isolated

Fagan's 1976 IBM Systems Journal paper is the origin of the practice and it states the decide≠act rule **explicitly, as a rule, with a reason**. From the description of inspection operation 3 (p. 193):

> "Now that the design is understood, *the objective is to find errors*."

> "Often the solution of a problem is obvious. If so, it is noted, but no specific solution hunting is to take place during inspection. (The inspection is *not* intended to redesign, evaluate alternate design solutions, or to find solutions to errors; it is intended just to find errors!) A team is most effective if it operates with only one objective at a time." [S1]

The process then separates detection from repair into distinct numbered operations (p. 194):

> "4. *Rework* — All errors or problems noted in the inspection report are resolved by the designer or coder/implementor."

> "5. *Follow-Up* — It is imperative that every issue, concern, and error be entirely resolved at this level, or errors can be 10 to 100 times more expensive to fix if found later in the process" [S1]

And the independence of the judge is a stated design goal (p. 190):

> "To preserve objectivity and to increase the integrity of the inspection, it is usually advantageous to use a moderator from an unrelated project." [S1]

**This is a startlingly exact match to the repo's three layers**: operation 3 = `review-pr` (find, do not fix), operation 4 = the redispatched `build-refine` (the author's side resolves), operation 5 = the parent/human verifying the runway closed. Table 3 of [S1] names the objectives of the five operations in a column: *Find errors* for Inspection; *Rework and resolve errors found by inspection* for Rework; *See that all errors, problems, and concerns have been resolved* for Follow-up.

**But — and this is the whole point — Fagan does not test the rule.** The only comparative quality measurement in the paper bundles it with everything else (p. 188):

> "The results showed the inspection sample to contain 38 percent less errors than the walk-through sample." [S1]

An inspection differs from a walkthrough in role definition, moderator training, checklists, individual preparation, error-type distributions, data collection, *and* the find-don't-fix rule, all at once. **A 38% delta across a bundle of seven changes is not evidence for any one of them.** The rationale Fagan gives for the rule — *"A team is most effective if it operates with only one objective at a time"* — is an assertion, not a result. *(Confidence: **definitive on the quoted spans, with the qualification in §6.0** — the PDF has no text layer and these were transcribed by me from page images. **Derived** on the "never isolated" reading; see N1 for the search method behind it.)*

### 3.2 The human counter-case, and it is strong: authors reviewing their own work DOES work in humans

The most important thing the human literature contributes is not support. It is a counter-example. Kemerer & Paulk's IEEE TSE study of Personal Software Process data — where the "reviews" are performed by **the author of the code, on the author's own code**:

> "Review activities in the PSP process are those steps performed by the developer in a traditional inspection process."

> "Two data sets of 371 and 246 programs, respectively, from a Personal Software Process (PSP) approach were analyzed using both regression and mixed models."

> "The recommended review rate of 200 LOC/hour or less was found to be an effective rate for individual reviews, identifying nearly two-thirds of the defects in design reviews and more than half of the defects in code reviews." [S2]

**A human author reviewing their own work at a controlled pace finds ~2/3 of design defects and >1/2 of code defects.** The LLM case is the *opposite*: same-context self-review scored lowest but one of four conditions [S9], and intrinsic self-correction actively degrades reasoning performance [S4].

**The asymmetry is a finding in its own right, and it cuts both ways.** It means (i) the human-inspection literature cannot be transferred wholesale to justify the LLM design — the human premise "authors can't check their own work" is false; and (ii) the LLM case for separation is *stronger* than the human case, because the LLM's self-review deficit is measured and the human's is not. *(Confidence: definitive on the [S2] quotes — abstract read directly from the publisher-hosted PDF's first page. **Derived** on the asymmetry argument, from [S2] against [S4][S9].)*

### 3.3 The human boundary: what an independent non-editing reviewer actually produces

Bacchelli & Bird's Microsoft study is the largest close look at what modern (tool-based, reviewer-cannot-edit) code review actually yields:

> "Peer code review, a manual inspection of source code by developers other than the author, is recognized as a valuable tool for reducing software defects and improving the quality of software projects"

> "manually inspected and classified the content of 570 comments in discussions contained within code reviews; and (4) surveyed 165 managers and 873 programmers"

> "Our study reveals that while finding defects remains the main motivation for review, reviews are less about defects than expected and instead provide additional benefits such as knowledge transfer, increased team awareness, and creation of alternative solutions to problems."

> "Although 'defect finding' is the top motivation and expected outcome of code review for many practitioners, the category 'defect' is the only the fourth most frequent, out of nine items, with 78 (14%) comments."

> "Review comments about defects are few, comprising one-eighth of the total in our sample, and mostly address 'micro' level and superficial concerns" [S3]

**In the human system that most closely matches T3 — a separate reviewer who annotates and cannot commit — 14% of output is about defects.** If the LLM judge behaves the same way, most of `review-pr`'s output is not defect reduction. That is directly measurable on this repo's corpus and is experiment E1b in §7. *(Confidence: definitive — read directly from the publisher-hosted PDF pages 1 and 7. Sentence (d) reproduces the paper's own grammatical slip "is the only the fourth"; it is quoted as printed.)*

### 3.4 LLM self-correction: the negative results are real and they are scoped

The R1 results are unambiguous and first-party:

> "our research indicates that LLMs struggle to self-correct their responses without external feedback, and at times, their performance even degrades after self-correction" — [S4]

> "We observe significant performance collapse with self-critique and significant performance gains with sound external verification. We also note that merely re-prompting with a sound verifier maintains most of the benefits of more involved setups." — [S6]

> "our findings reveal that self-critiquing appears to diminish plan generation performance, especially when compared to systems with external, sound verifiers and the LLM verifiers in that system produce a notable number of false positives" — [S7]

**And the field's own critical survey draws the boundary for us, in its abstract:**

> "(1) no prior work demonstrates successful self-correction with feedback from prompted LLMs, except for studies in tasks that are exceptionally suited for self-correction, (2) self-correction works well in tasks that can use reliable external feedback, and (3) large-scale fine-tuning enables self-correction." — [S5]

Two consequences, and the second is uncomfortable:

1. **Evidence that self-correction fails is not evidence that this design fails.** [S5] clause (2) is the licence for the whole architecture: external feedback works.
2. **But the word doing the work in [S6] and [S7] is "sound."** Their gains come from a *sound external verifier* — a program that is correct by construction. `review-pr` is an LLM. It is external, and it is not sound. **[S6]'s and [S7]'s positive halves are therefore NOT support for an LLM judge**, and any paper (including this one) that cites "external verification works" in defence of an LLM judge is over-claiming. What this repo has that *is* sound is CI, the test suite, and the `COMPLETION_PATTERN` contract — and [S6]'s finding that "merely re-prompting with a sound verifier maintains most of the benefits" is an argument for putting *more* weight on those and less on the judge. *(Confidence: definitive on all four abstracts, fetched from the arXiv API. **Derived** on the "not support for an LLM judge" reading — [S6] and [S7] do not discuss LLM-judge architectures as a deployment recommendation.)*

### 3.5 External critique: the on-domain evidence, and its ceiling

Five results, all on code or defect-finding rather than reasoning benchmarks:

**(a) A separately-trained critic beats human reviewers — and hallucinates.**

> "On code containing naturally occurring LLM errors model-written critiques are preferred over human critiques in 63% of cases, and human evaluation finds that models catch more bugs than human contractors paid for code review."

> "Critics can have limitations of their own, including hallucinated bugs that could mislead humans into making mistakes they might have otherwise avoided, but human-machine teams of critics and contractors catch similar numbers of bugs to LLM critics while hallucinating less than LLMs alone." — [S8]

Note the regime: CriticGPT critics are **RLHF-trained to critique** — [S5] clause (3), "large-scale fine-tuning enables self-correction." `review-pr` is a prompted general model, not a trained critic. **The transfer from [S8] to a prompted judge is unestablished.** *(derived)*

**(b) Context separation is the active ingredient — the only controlled on-domain experiment located.** 30 artifacts, 150 injected errors, 360 reviews, four conditions:

> "Over 360 reviews, CCR reached an F1 of 28.6%, outperforming SR (24.6%, p=0.008, d=0.52), SR2 (21.7%, p<0.001, d=0.72), and SA (23.8%, p=0.004, d=0.57). The SR2 result matters most for interpretation: reviewing twice in the same session did not beat reviewing once (p=0.11), which rules out repetition as an explanation for CCR's advantage. The benefit comes from context separation itself." — [S9]

This is the single best support for the fresh-context half. **It is also a single-author 2026 preprint, single-model, injected rather than natural errors, with absolute F1 under 30%.** Directional, and the paper says so. Critically for §7: it has **no arm in which the reviewer can edit**, so it does not touch the authority question at all.

**(c) Independent passes find largely disjoint defect sets, and aggregating them wins big.** SWRBench, 1000 manually verified PRs: *"we propose and validate a simple multi-review aggregation strategy that significantly boosts ACR performance, increasing F1 scores by up to 43.67%"* [S10]. The caveat that matters: these are **parallel independent reviews aggregated**, not a sequential author→judge handoff.

**(d) The information-theoretic version, with an ablation.** CodeX-Verify: *"We tested all 15 agent combinations and found that using multiple agents improves accuracy by 39.7 percentage points (from 32.8% to 72.4%) compared to single agents, with diminishing returns of +14.9pp, +13.5pp, and +11.2pp for agents 2, 3, and 4"* and *"Measuring agent correlation of rho = 0.05 to 0.25 confirms they detect different bugs"* [S12]. The mechanism named is **conditional independence of detection patterns** — which is a *context/perspective* claim, not an *authority* claim.

**(e) An industrial deployment of role separation.** *"we propose 1) code slicing algorithms for context extraction, 2) a multi-role LLM framework for KBI, 3) a filtering mechanism for FAR reduction... achieves a 2x improvement over standard LLMs and a 10x gain over previous baselines"* [S13], on C++ codebases at a company with "nearly 400 million daily active users."

**(f) The most instructive result in the whole corpus is a failure**, from a 31-day adversarial-review campaign that produced 4 real CVEs:

> "The most instructive failure: ten dedicated reviewers unanimously endorsed a non-existent Bleichenbacher padding oracle in OpenSSL's CMS module; it was killed only by a single empirical test, motivating the mandatory empirical gate." — [S11]

**Ten independent separated reviewers agreeing does not make a finding true.** Separation buys independence of *some* blind spots, not of correlated ones — which is why the same paper uses a *cross-model* critic and explicitly says *"cross-family review can catch correlated blind spots that same-family review misses"* [S11]. §5.3 takes this seriously.

### 3.6 The multi-agent case against layering — and why it does not reach T3

This is where `case_against.md` lives, and where its transfer breaks. The four strongest anti-layering results are all about topologies with a property T3 lacks.

**[S18] Tran & Kiela — matched compute.** *"When computation is normalized, single-agent systems (SAS) can match or outperform MAS"*, and *"for multi-hop reasoning tasks, many reported advantages of multi-agent systems are better explained by unaccounted computation and context effects rather than inherent architectural benefits."* Domain: multi-hop reasoning. Not review.

**But [S18]'s abstract also states the discriminator, and it points the other way for this repo:**

> "This perspective further predicts that multi-agent systems become competitive when a single agent's effective context utilization is degraded, or when more compute is expended." — [S18]

**DERIVED, and stated at full length because it is the paper's most load-bearing inference.** A `build-draft` child that has authored for tens of minutes, filled its window with tool output, its own prior reasoning, and its own justifications, is by construction a single agent whose **effective context utilization is degraded**. [S18]'s own information-theoretic model therefore *predicts* that a separate actor becomes competitive precisely in this repo's operating regime. [S18] does not say this — it says nothing about coding sessions, context length, or review. The mapping from "degraded effective context utilization" to "a long authoring session" is mine, it is the exact inference [S18] would need to have tested and did not, and **it is the hypothesis E1 in §7 is designed to falsify.** *(Derived from [S18] abstract + `build-minor.sh` topology. Marked directional-at-best; do not cite this as [S18]'s finding.)*

**[S19] Cemri et al., MAST.** *"Despite enthusiasm for Multi-Agent LLM Systems (MAS), their performance gains on popular benchmarks are often minimal"*; 14 failure modes in 3 categories: *"(i) system design issues, (ii) inter-agent misalignment, and (iii) task verification."* Category (ii) requires agents that must stay aligned *with each other* — a T4 property. A single sequential handoff of (artifact + original task) has no inter-agent state to misalign.

**[S22] Cognition, "Don't Build Multi-Agents" — and this is the finding that resolves the pool's contradiction.** The post's diagnosis is entirely about concurrent writers:

> "The decision-making ends up being too dispersed and context isn't able to be shared thoroughly enough between the agents."

> "The actions subagent 1 took and the actions subagent 2 took were based on conflicting assumptions not prescribed upfront."

> "And if they were to run multiple parallel subagents, they might give conflicting responses, resulting in the reliability issues we saw with our earlier examples of agents."

**And it carves out this repo's topology by name:**

> "However, it never does work in parallel with the subtask agent, and the subtask agent is usually only tasked with answering a question, not writing any code." — [S22]

That sentence describes a **sequential, non-writing, question-answering subagent** — T3 — as the *acceptable* pattern, inside the canonical anti-multi-agent essay. `case_against.md` §2.3.4 built its D7 finding by transferring [S22]'s parallel-writer failure onto a sequential reader, and flagged the transfer as unestablished. **It is worse than unestablished: the source's own text excludes it.**

**[S23] Cognition's follow-up, 2026-04-22, closes it.** The refined principle:

> "multi-agent systems work best today when writes stay single-threaded and the additional agents contribute intelligence rather than actions." — [S23]

*"Writes stay single-threaded"* and *"contribute intelligence rather than actions"* is the `decide ≠ act` seam, restated by the company whose earlier post was the pool's strongest cited authority against layering. The follow-up names a **Code-Review-Loop** as one of the patterns that works, reports *"Devin Review catches an average of 2 bugs per PR, of which roughly 58% are severe (logic errors, missing edge cases, security vulnerabilities)"*, and attributes the mechanism to context:

> "The review agent having a completely clean context also helps it go deeper into areas the original coding agent may not." — [S23]

**Two honesty constraints on how far this carries.** (i) [S22] and [S23] are rendered pages fetched through a summarizing layer — see §6.0; the spans are short and I mark them at reduced confidence. When I re-fetched [S22] independently, my fetch returned *"Subagent 1 and subagent 2 cannot not see what the other was doing"* where `case_against.md` recorded *"cannot see what the other was doing"* — a one-word difference in a double negative. I cannot tell from a summarizing fetch which is the page's actual text, so **I do not use that span at all**, and I flag the discrepancy rather than picking a winner. (ii) [S23] attributes the benefit to **clean context**, not to the absence of write authority. Cognition endorses the fresh-context half. It says nothing about the authority half. The layer's own note on my fetch was that the article "emphasizes separation by context, not explicit prohibition on writing" — I did not find a first-party Cognition sentence stating the review agent cannot write, and I do not assert one.

**[S24] Anthropic documents the pattern with the judge not editing:** *"In the evaluator-optimizer workflow, one LLM call generates a response while another provides evaluation and feedback in a loop"* and *"This workflow is particularly effective when we have clear evaluation criteria, and when iterative refinement provides measurable value."* The evaluator *provides feedback*; the optimizer writes. That is T3, named as a first-party documented pattern. It is an engineering-guidance page with no measurement attached — **directional**, per the authority-vs-formality rule.

### 3.7 The judge is compromised even with fresh context — self-preference is load-bearing

Fresh context removes the author's *reasoning*. It does not remove the model's *identity*.

> "One such bias is self-preference, where an LLM evaluator scores its own outputs higher than others' while human annotators consider them of equal quality."

> "By fine-tuning LLMs, we discover a linear correlation between self-recognition capability and the strength of self-preference bias; using controlled experiments, we show that the causal explanation resists straightforward confounders." — [S15]

Magnitudes, from the LLM-as-judge reference paper:

> "GPT-4 favors itself with a 10% higher win rate; Claude-v1 favors itself with a 25% higher win rate." — [S14]

**And its own caveat, which I quote because omitting it would be exactly the inflation this paper faults elsewhere:**

> "Due to limited data and small differences, our study cannot determine whether the models exhibit a self-enhancement bias." — [S14]

So: [S14] reports the numbers and disclaims their sufficiency; [S15] supplies the causal mechanism with controlled experiments; [S16] finds *"significant biases persist in certain specific tasks"* across 12 quantified bias types and concludes *"there remains room for improvement in the reliability of LLM-as-a-Judge."*

**The direct consequence for this design, and it is actionable.** `review-pr` runs the **same model family** as `build-draft` and `build-refine`. Fresh context does not touch self-preference; only cross-family judging does. [S11] built its pipeline around exactly this — a *"Cross-Model Critic (CMC)"* justified because *"cross-family review can catch correlated blind spots that same-family review misses"* [S11]. **The repo's judge is same-family, which is the configuration the evidence says is compromised.** That is a concrete, cheap, testable change (E3 in §7). *(Confidence: definitive on [S14][S15][S16][S11] abstracts; **derived** on the application to this repo's configuration.)*

[S17] adds the adjacent finding that agentic evaluation of agentic work *"dramatically outperforms LLM-as-a-Judge and is as reliable as our human evaluation baseline"* — i.e. a judge that can *read the repo and intermediate steps* beats a judge scoring final output. `review-pr` is agentic in exactly that sense (it runs `gh`, reads the diff, checks the current default branch). Relevant, supportive, and on a different task (code-generation task evaluation, not defect finding).

### 3.8 Role separation that measurably helps, on code

Two results run against the anti-layering position on *this repo's domain*:

- **[S21] Dong et al.**: an analyst/coder/tester role split *"relatively improves 29.9%-47.1% Pass@1 compared to the base LLM agent."* Sequential roles, one writer at a time.
- **[S20] Du et al.**: multiagent debate *"significantly enhances mathematical and strategic reasoning"* and *"improves the factual validity of generated content, reducing fallacious answers and hallucinations."* Note this is **not** matched-compute, which is precisely [S18]'s objection.

Neither controls compute. Both are the class of result [S18] says is confounded. **I report them as the fair statement of the other side, not as settled support.**

### 3.9 Adjudication: are `case_against.md` and `convergence_stopping.md` actually in conflict?

**Mostly no. They answer different questions, and both are right in their own regime. On one axis they genuinely conflict, and that axis is the experiment.**

| | `case_against.md` §2.3 (C3) | `convergence_stopping.md` §2.2 |
|---|---|---|
| **Claims** | Layering (author/judge/disposition) may buy nothing: single agents match MAS at matched compute; more calls can hurt; MAS failures are structural; judges are biased; the vendor most invested publishes a 3-10x cost multiplier | Separation is the active ingredient: fresh-context review beats same-session; a separate critic beats the author; independent passes find disjoint sets and aggregate to +43.67% F1 |
| **Task domain of its evidence** | Multi-hop reasoning, vote aggregation, general MAS task completion | Code review, defect injection/detection, code critique |
| **Topology of its evidence** | Concurrent agents that ACT on shared state (T4) | Sequential or parallel-independent agents that READ and REPORT (T2/T3) |
| **Objective being measured** | Task accuracy per unit of compute | Defect-detection recall on already-produced work |

**They are not contradictory; they are non-overlapping.** `case_against.md` says so itself in its §5.5 (*"None measures review, critique or defect-finding"*), and this paper confirms the reading independently from the primary abstracts rather than from the sibling paper: [S18] is multi-hop reasoning; [S19] is coding/math/general-agent *task completion*; [S22] is parallel implementation subagents. **No located result measures multi-agent underperformance on a review task.** (Search method: N4.)

**Which is better evidenced?** Neither, and for opposite reasons. `case_against.md`'s sources are stronger *as science* — [S18] is a controlled matched-budget study, [S19] has 1600+ traces and κ=0.88 — but they are **off-domain**. `convergence_stopping.md`'s sources are **on-domain** but individually weaker — its keystone [S9] is a single-author preprint. **Strong evidence about the wrong question versus weak evidence about the right one.** A consumer should not treat either as settling this.

**Where they genuinely conflict — the one real disagreement, and it is about cost, not defects.** [S18]'s matched-compute finding implies the correct control arm is **not** "author alone" but "author given the judge's token budget to keep authoring." `convergence_stopping.md` never runs that control; nor does [S9], [S10] or [S12]. If a second author pass at equal spend finds as many defects as the judge, the layering is buying a *reporting surface*, not detection — which may still be worth it under §1.1(b), but is a different justification than the one element 2 makes. **This is the single unresolved question and it is E1 in §7.**

**The discriminator, if one wants a rule rather than an experiment.** Derived from [S18]'s stated prediction (§3.6) plus [S12]'s correlation measurement: *separation pays when the incumbent actor's effective context utilization is degraded and when the separated actor's errors are conditionally independent of the incumbent's; it does not pay when the incumbent has clean context and the separated actor is same-family (correlated).* Both halves are measurable on this repo (E1, E3). *(**Derived** from [S18] + [S12] + [S11]. No source states this rule.)*

---

## 4. What this provides — enumerated properties a plan may rely on

**P1. Same-actor same-context self-review is the worst available option, and this is measured twice.** Intrinsic self-correction degrades reasoning performance [S4]; and in the one controlled review-shaped experiment, same-session self-review (F1 24.6%) and repeated same-session self-review (21.7%) both lost to fresh-context review (28.6%) [S9]. *(definitive on [S4]; directional on [S9] — single-author preprint.)*

**P2. The field's negative self-correction results are explicitly scoped away from the cross-actor case.** [S5]'s own conclusion (2) is *"self-correction works well in tasks that can use reliable external feedback."* A consumer citing "LLMs can't self-correct" against this design is misapplying the source. *(definitive)*

**P3. Fresh context is the attributed mechanism in the one controlled experiment and in the nearest commercial system.** [S9]: *"The benefit comes from context separation itself."* [S23]: *"The review agent having a completely clean context also helps it go deeper into areas the original coding agent may not."* *(directional — one preprint plus one vendor engineering post; the latter at reduced confidence per §6.0.)*

**P4. Independent reviewers find largely disjoint defect sets; unions beat individuals.** +43.67% F1 from aggregating independent reviews [S10]; +39.7pp from four agents over one, with measured inter-agent correlation ρ = 0.05–0.25 [S12]; the multi-vendor union catching what no single reviewer did [S11]. *(definitive on the quoted claims; the transfer from parallel-aggregate to sequential-handoff is unestablished.)*

**P5. A separated critic can exceed paid human reviewers on code — when it is TRAINED to critique.** *"models catch more bugs than human contractors paid for code review"* [S8]. The precondition (RLHF-trained critic) is not met by a prompted judge. *(definitive on [S8]; the gap to a prompted judge is stated, not bridged.)*

**P6. The decide≠act rule has a fifty-year-old first-party statement with an explicit rationale.** [S1], quoted in §3.1. *(definitive on the quote — see §6.0 transcription caveat. It is a documented design rule, NOT a measured result.)*

**P7. The canonical anti-multi-agent essay carves out this exact topology.** *"it never does work in parallel with the subtask agent, and the subtask agent is usually only tasked with answering a question, not writing any code"* [S22]; and its successor's principle is *"writes stay single-threaded and the additional agents contribute intelligence rather than actions"* [S23]. *(definitive on the spans, at reduced confidence per §6.0.)*

**P8. Authority separation, as an isolated variable, has NO measured support in either literature.** See N1, N2. *(This is a gap, stated as a result.)*

**P9. Fresh context does not remove self-preference bias; only cross-family judging does.** [S15] establishes the causal link between self-recognition and self-preference; [S11] builds a cross-model critic for exactly this reason. The repo's judge is same-family. *(definitive on the sources; **derived** on the application.)*

**P10. A precise reviewer does not imply a corrected artifact.** [S25]: *"reviewer detection quality and critique uptake are empirically separable"* and *"a protocol may spot errors well yet still fail to solve more problems if it does not act on those critiques."* A decide-only architecture makes uptake a *separate, measurable, and currently unmeasured* stage. *(definitive on the abstract; domain is math reasoning, transfer unestablished.)*

**P11. Layering has a published cost multiplier and no published benefit multiplier for review tasks.** The cost side is quantified by the vendor most invested in it (3-10x tokens, cited in `case_against.md` §2.3.5 from a first-party page). The benefit side, for *review* specifically, is not. *(derived, from the absence documented in N4.)*

### 4.6 Corrections this paper proposes to the existing pool

Per §7 of the Research Standard these are surfaced here for the synthesis to carry as action candidates; this paper writes nothing outside `research/`.

1. **`case_against.md` D7 should be downgraded or withdrawn.** Its derivation ("a separate judge loses the author's context") transfers [S22]'s parallel-writer finding to a sequential reader. [S22]'s own text excludes that transfer (§3.6), and [S23] — which `case_against.md` §5.4 correctly flagged as UNVERIFIED — is now **verified and fetched**, and states the opposite. **Consequence if not corrected:** a ranked finding in the pool argues against the seam that the same source endorses, and a future planning run may act on it.
2. **`case_against.md` §5.4's unverified item is now closed.** The follow-up exists at `cognition.com/blog/multi-agents-working`, dated 04.22.26 in the byline, and its refined principle is quoted in §3.6 above.
3. **`convergence_stopping.md` and this repo's standards should stop treating "fresh context" and "no authoring authority" as one mechanism.** They have different evidence bases — one directional, one empty — and `workflow-scripts.md § Composition` currently justifies both with a single argument ("A run that both authors work and rules on the review findings about it will defend its own work"), which is a *provenance* argument and supports only the first.

---

## 5. Honest boundary analysis — the case against this paper's own thesis

### 5.1 The strongest single objection: nobody has isolated the variable, including this paper

§4/P8 is not a hedge, it is the headline. Fifty years of inspection research, an active LLM-evaluation literature, and **not one study varies "the reviewer may edit" while holding everything else constant.** Fagan asserts it. Anthropic documents a pattern that has the property without discussing it. Cognition endorses single-threaded *writes* — which is about avoiding write conflicts between concurrent actors, **not** about a judge's incentives. Every citation in §4 that appears to support authority separation actually supports *context* separation or *write-conflict avoidance*, and I could not find one that does not. **If the repo's standard claims measured backing for `decide ≠ act`, the claim is not supported by anything in this paper.**

### 5.2 The human counter-case says self-review works fine

§3.2. Human authors reviewing their own code at a controlled rate find most of their own defects [S2]. The premise "the author defends their own work, and no wording fixes that" (`workflow-scripts.md § Composition`) is a claim about **LLMs**, and while it has support in that domain, the human analogy the design borrows from does not carry it. If the LLM self-review deficit narrows with model capability — and there is no reason from these sources to assume it will not — the fresh-context justification narrows with it.

### 5.3 Separation does not buy independence of *correlated* errors, and the failure mode is unanimity

[S11]'s padding-oracle result is the sharpest warning in the corpus: **ten separated reviewers unanimously endorsed a non-existent vulnerability, and only an empirical test killed it.** Nothing in a decide-only architecture defends against a plausible, confidently-stated, wrong finding — indeed the architecture *converts findings into mandated fix dispatches*, which is a mechanism for propagating a hallucinated finding into real edits. [S8] flags the same risk (*"hallucinated bugs that could mislead humans"*) and reports that **human-machine teams hallucinated less than the LLM alone**, which is an argument for keeping the human in the disposition loop rather than promoting the parent to fire fixes automatically. This repo currently keeps the human there. **Automating the fire step would be moving toward the configuration the evidence penalises.**

### 5.4 Decide-only creates an uptake problem that "can-edit" does not have

[S25] measured exactly this: a planner-executor-**reviewer** pipeline whose *"reviewer is more precise than broadcast's (0.861 vs. 0.644), yet evaluator-verified useful critique is much less likely to change the next candidate and produces lower reviewer-guided repair."* And, damningly for prompt-level fixes: *"forcing explicit acknowledgment lowers final accuracy, while embedding reviewer guidance directly in the solver's working context partially improves follow-through without closing the gap."* **A judge that cannot edit can only be as good as the handoff**, and the one measured intervention that resembles this repo's `HOLD - redispatch` runway (explicit acknowledgment) made things *worse* in that study. The domain is math reasoning, so the transfer is unestablished — but this is the sharpest published counter-argument to `decide ≠ act` in existence and it should not be softened.

### 5.5 The matched-compute objection is unanswered and it is the right objection

§3.9. Every on-domain positive result ([S9][S10][S12][S13]) compares "more actors" against "one actor at lower spend." [S18] shows that in a domain where the comparison *was* controlled, the advantage disappeared. **Until this repo runs the budget-matched control, "the judge found things the author missed" is fully consistent with "spending those tokens on anything would have found things."**

### 5.6 An independent non-editing reviewer may mostly produce non-defect commentary

[S3]: 14% of human review comments were defects, and those *"mostly address 'micro' level and superficial concerns."* If `review-pr`'s disposition comments have the same profile, the layer's value is knowledge-transfer-shaped, not defect-shaped — and this repo has no human on the receiving end of knowledge transfer during an autonomous run. **This is measurable today** (E1b) and is the cheapest way to find out the layer is not doing what it is claimed to do.

### 5.7 The judge may be reviewing the wrong artifact

`review-pr`'s prompt states: *"You are NOT re-reviewing the code"* and *"YOUR PRIMARY HUNTING GROUND is the producing run's OWN WORDS"* (lines 215-216). **This is not the design the literature studies.** Every cited review result ([S9][S10][S12][S13][S8]) measures a reviewer reading the *artifact*. A judge auditing a self-report against the artifact is a **different task**, closest in spirit to [S17]'s Agent-as-a-Judge (which reads intermediate steps) but not the same. **No located source measures self-report auditing.** (N5.) The evidence in §3.5 therefore transfers to `review-pr` more weakly than the surface similarity suggests.

### 5.8 When this layer is NOT needed

Stated plainly, because a paper that cannot name its own null case is advocacy:

- **When a sound verifier exists.** [S6]: *"merely re-prompting with a sound verifier maintains most of the benefits of more involved setups."* For a change fully covered by CI and tests, the judge is adding cost over a signal that is already correct-by-construction.
- **When the authoring run's context is short and clean.** Per [S18]'s prediction (§3.6), the separated actor's advantage is a function of the incumbent's context degradation. A three-turn `build-minor` draft may not have degraded anything.
- **When the finding will not be acted on.** [S25]. A ruling nobody fires is a ruling that cost tokens and changed nothing.
- **When the judge is same-family and the failure mode is a shared blind spot.** [S11][S15].

### 5.9 The maximal counter-position, fairly stated

[S26] argues the whole gate is obsolete: *"We argue that coding agents have crossed a threshold of capability at which traditional human code review is no longer a necessary component of a software quality pipeline"* and *"the naive integration in which agents write code and humans remain the mandatory reviewers is a dead end because it neither provides meaningful assurance nor scales with AI-assisted throughput."* It is a **position paper, not a measurement** — its own abstract says "We argue" — and it argues against *human* review while this design's judge is an agent, so it is more supportive than hostile to T3. I include it because it is the strongest published statement that a review gate can be the wrong place to spend, and a reader deserves to see it.

---

## 6. Citations

### 6.0 Sourcing posture, stated because §3's rules require it

- **arXiv abstracts** ([S4]–[S21], [S25], [S26]) were fetched from the **arXiv Atom API** (`export.arxiv.org/api/query?id_list=...`), a raw XML response, and quoted from the `<summary>` element. This is the strongest posture available here.
- **[S1], [S2], [S3]** are PDFs. They did not extract through the fetch layer; the binaries were retrieved and I read the **page images directly**. Quoted spans are therefore my transcription of a rendered page, not a returned character stream. **This is one step weaker than an API response and I mark it as such**: page numbers are given for every span so a verifier can check them, and I kept spans short. [S1] in particular is a scan of a 1976 journal with no text layer.
- **[S22], [S23], [S24]** are rendered vendor pages fetched through a summarizing layer. **Reduced confidence, short spans only.** Where a span was ambiguous across two independent fetches I discarded it rather than choose (§3.6).
- **No search-engine result summary is cited anywhere in this paper.** Search was used to locate sources; every cited claim traces to a fetch of the source itself. The Cognition follow-up [S23] is the clearest case: search suggested it existed, I enumerated `cognition.com/blog` to obtain the slug, then fetched the post.
- **Counts.** The only count asserted here is the source count, obtained by enumerating the list in §6.2 and counting the enumeration: **26**.

### 6.1 Negative findings and their search methods

**N1. No study was located, in the human software-inspection literature, that isolates "the reviewer may not fix what they find" as an experimental variable.** Fagan states the rule and gives a rationale [S1]; his one comparative quality measurement (38% fewer errors than walkthrough) varies an entire method, not one rule. Searched via: web search on `experiment reviewer permitted to fix versus only report defects effect on defect detection software inspection controlled study` (four successive reformulations within one search session, returning inspection-technique comparisons — checklist vs ad hoc, perspective-based reading, meeting vs no meeting, detection-method replications — none varying fix authority); web search on `software inspection rule "find errors" not "find solutions" moderator author role separation Fagan`; and direct reading of [S1] pp. 187-195 and [S2] p. 1. **The rule is universally *stated* and never *tested*.**

**N2. No study was located, in the LLM literature, that ablates a reviewing agent's edit authority while holding model, prompt, context and artifact constant.** Searched via: web search on `LLM agent "read-only" reviewer ablation critic without edit permission defect detection separation of roles study` and `arxiv ablation "cannot modify" reviewer agent versus reviewer that can patch code multi-agent defect detection measured`. These surfaced the pattern being *advocated* in industry commentary (vendor guides describing "a fresh-context reviewer with read-only tools and a pinned model from a different family") and *implemented* in research pipelines ([S11]'s cold-start cross-model critic; [S12]'s four specialized agents), but **in every case the read-only property is bundled with fresh context and/or a different model family, never varied alone.** The closest ablation located, [S12]'s all-15-combinations sweep, varies *which* agents participate, not their authority.

**N3. No source was located that frames authority separation as an OBSERVABILITY property** (a finding must be stated rather than absorbed) rather than a bias property. Searched incidentally across N1 and N2 and across the [S25] uptake material. The framing in §1.1(b) is this paper's own and is marked derived.

**N4. No result was located measuring multi-agent underperformance on a REVIEW or defect-finding task.** Every anti-layering result located measures reasoning ([S18]), general task completion ([S19]), or implementation ([S22]). Searched via the multi-agent sweep behind §3.6 and by reading the primary abstracts of [S18][S19][S22] directly rather than through `case_against.md`. This corroborates that paper's own §5.5 from independent fetches.

**N5. No source was located that measures a judge auditing a producing run's SELF-REPORT against the artifact** — the task `review-pr` actually performs (§5.7). Searched incidentally across the code-review sweep behind §3.5; the nearest analogue is [S17], which evaluates intermediate agentic steps against requirements, not self-reports against a diff.

**N6. No cost-per-verified-finding figure was located for a review-shaped layer.** The published multiplier (3-10x tokens) is for multi-agent systems generally. Nothing located divides a layer's cost by the defects it uniquely caught. This is E1c in §7.

### 6.2 Source list

**Human inspection and code review — classical (LOW volatility)**

- [S1] Fagan, M. E. (1976). *Design and Code Inspections to Reduce Errors in Program Development.* IBM Systems Journal 15(3), 182-211. PDF: https://www.ida.liu.se/~TDDC90/literature/lab-papers/fagan76.pdf *(scanned, no text layer; spans transcribed from page images, pp. 187, 188, 190, 193, 194)*
- [S2] Kemerer, C. F., & Paulk, M. C. (2009). *The Impact of Design and Code Reviews on Software Quality: An Empirical Study Based on PSP Data.* IEEE Transactions on Software Engineering 35. DOI 10.1109/TSE.2009.27. PDF: https://sites.pitt.edu/~ckemerer/PSP_Data.pdf *(spans read from page 1)*
- [S3] Bacchelli, A., & Bird, C. (2013). *Expectations, Outcomes, and Challenges of Modern Code Review.* ICSE 2013, 712-721. PDF: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/ICSE202013-codereview.pdf *(spans read from pages 1 and 7)*

**LLM self-correction — peer-reviewed (LOW volatility)**

- [S4] Huang, J., et al. (2023). *Large Language Models Cannot Self-Correct Reasoning Yet.* ICLR 2024. arXiv:2310.01798
- [S5] Kamoi, R., Zhang, Y., Zhang, N., Han, J., & Zhang, R. (2024). *When Can LLMs Actually Correct Their Own Mistakes? A Critical Survey of Self-Correction of LLMs.* TACL 2024. arXiv:2406.01297
- [S6] Stechly, K., Valmeekam, K., & Kambhampati, S. (2024). *On the Self-Verification Limitations of Large Language Models on Reasoning and Planning Tasks.* arXiv:2402.08115
- [S7] Valmeekam, K., Marquez, M., & Kambhampati, S. (2023). *Can Large Language Models Really Improve by Self-critiquing Their Own Plans?* arXiv:2310.08118

**External critique and code review — mixed (MEDIUM-HIGH volatility)**

- [S8] McAleese, N., Pokorny, R. M., Ceron Uribe, J. F., Nitishinskaya, E., Trebacz, M., & Leike, J. (2024). *LLM Critics Help Catch LLM Bugs.* arXiv:2407.00215
- [S9] Song, T.-E. (2026). *Cross-Context Review: Improving LLM Output Quality by Separating Production and Review Sessions.* arXiv:2603.12123 *(single-author preprint — directional)*
- [S10] Zeng, Z., et al. (2025). *SWR-Bench: Assessing LLM Performance in Real-World Code Review Comment Generation.* arXiv:2509.01494
- [S11] *Refute-or-Promote: An Adversarial Stage-Gated Multi-Agent Review Methodology for High-Precision LLM-Assisted Defect Discovery.* (2026). arXiv:2604.19049 *(preprint; outcomes externally validated — 4 CVEs, accepted C++ working paper)*
- [S12] *Multi-Agent Code Verification via Information Theory* (CodeX-Verify). (2025). arXiv:2511.16708 *(preprint; n=99 labelled samples — small)*
- [S13] *Towards Practical Defect-Focused Automated Code Review.* (2025). arXiv:2505.17928 *(industrial deployment report)*

**LLM-as-judge reliability (MEDIUM volatility)**

- [S14] Zheng, L., et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* NeurIPS 2023 D&B. arXiv:2306.05685 *(bias magnitudes quoted from the ar5iv HTML rendering, https://ar5iv.labs.arxiv.org/html/2306.05685; abstract from the arXiv API)*
- [S15] Panickssery, A., Bowman, S. R., & Feng, S. (2024). *LLM Evaluators Recognize and Favor Their Own Generations.* arXiv:2404.13076
- [S16] Ye, J., et al. (2024). *Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge.* arXiv:2410.02736
- [S17] Zhuge, M., et al. (2024). *Agent-as-a-Judge: Evaluate Agents with Agents.* arXiv:2410.10934

**Multi-agent decomposition — both sides (MEDIUM volatility)**

- [S18] Tran, D., & Kiela, D. (2026). *Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets.* arXiv:2604.02460
- [S19] Cemri, M., et al. (2025). *Why Do Multi-Agent LLM Systems Fail?* arXiv:2503.13657
- [S20] Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2023). *Improving Factuality and Reasoning in Language Models through Multiagent Debate.* arXiv:2305.14325
- [S21] Dong, Y., Jiang, X., Jin, Z., & Li, G. (2023). *Self-collaboration Code Generation via ChatGPT.* arXiv:2304.07590
- [S22] Cognition (Walden Yan). *Don't Build Multi-Agents.* https://cognition.com/blog/dont-build-multi-agents *(rendered page, summarizing fetch — reduced confidence; short spans only)*
- [S23] Cognition (Walden Yan). *Multi-Agents: What's Actually Working.* https://cognition.com/blog/multi-agents-working *(byline date 04.22.26; rendered page, summarizing fetch — reduced confidence. **Supersedes [S22] by the same author.**)*
- [S24] Anthropic. *Building Effective Agents.* https://www.anthropic.com/engineering/building-effective-agents *(rendered first-party engineering page — **directional**: documented pattern, no measurement)*

**Uptake and the maximal counter-position (HIGH volatility — 2026 preprints)**

- [S25] *Precise but Uncoupled: Reviewer Precision Does Not Guarantee Critique Uptake in Multi-Agent Math Reasoning.* (2026). arXiv:2607.15388
- [S26] *The End of Code Review: Coding Agents Supersede Human Inspection.* (2026). arXiv:2606.13175 *(position paper — "We argue"; not a measurement)*

**Intra-repo inputs (not external sources; read, not cited as evidence)**

- `docs/standards/architecture/research/raw/case_against.md` — §2.3, §5.4, §5.5, D7, T5. Critic: PASS. Adjudicated in §3.9; corrections proposed in §4.6.
- `docs/standards/architecture/research/raw/convergence_stopping.md` — §1.2, §2.2.1-2.2.6. Critic: PASS. Adjudicated in §3.9.
- `scripts/workflows/children/review-pr.sh` lines 190-220; `scripts/workflows/build-minor.sh` lines 79-82, 278-373; `scripts/workflows/activities/run-claude.sh` (JSONL logging).

---

## 7. Test plan — what research cannot settle, framed against THIS repo's surfaces

The pool's standing note is that only an experiment resolves this. That note is correct, and §6.1's N1/N2 explain why: **the isolating experiment does not exist in the literature, so it has to be run here.** Every arm below is executable against surfaces that already exist:

- **JSONL run logs** at `<repo>/.claude/logs/<workflow>-<ts>.jsonl`, written by every dispatch via `activities/run-claude.sh`; token/cost totals are already aggregated by `print_cycle_totals`, and the final result is extractable with `jq -r 'select(.type == "result") | .result'`.
- **PR comment threads** — every workflow posts a decision log + post-run reflection; `review-pr` posts one disposition comment. All retrievable: `gh pr view N --json comments --jq '.comments[].body'`.
- **Terminal `VERDICT:` lines**, a closed vocabulary parsed by the parent at `build-minor.sh:281`.
- **Git history per PR**, which gives the artifact before and after each child.

### E1 — The matched-budget control arm (THE experiment; §3.9's unresolved conflict)

**Question:** does the judge find defects that an equal spend on more authoring would not?

**Corpus:** 20 merged PRs from this repo's history, reconstructed as mutants. For each, seed K=5 defects into the merged tree using a fixed mutation catalogue spanning the categories [S3] found humans catch and miss (logic error, missing edge case, wrong config value, dropped error handling, scope creep against the original task). Seeding gives ground truth, which no natural-corpus arm can.

**Arms (each run on the same mutant PR, same model, fresh worktree):**
- **A (current):** `build-refine` → `review-pr`.
- **B (budget-matched second author):** `build-refine` → a second `build-refine` with fresh context and edit authority, given a turn cap sized so its *consumed* tokens match arm A's `review-pr` consumption (read off the JSONL, not the cap).
- **C (budget-matched single actor):** `build-refine` alone with its cap raised so consumed tokens match A's total.

**Reads out:** seeded-defect recall per arm, and cost per uniquely-detected defect.

**Falsifies element 2 if:** B ≥ A on recall. Then the layering is buying reporting, not detection, and `workflow-scripts.md § Composition` must be restated to justify the seam on observability (§1.1b) rather than on defect reduction.

### E1b — The Bacchelli profile check (cheapest experiment here; run it first)

**Question:** what fraction of `review-pr`'s output is actually about defects?

**Method:** pull every disposition comment from the last 30 PRs (`gh pr view --json comments`), extract each surfaced item, and classify against [S3]'s nine categories. Then cross-classify each item as (i) **already stated** by the producing run in its own decision log / reflection, or (ii) **new**. Requires no new dispatches and no instrumentation.

**Reads out:** the judge's *marginal* yield — items it surfaced that the run had not already told on itself. **If the new-item fraction is near zero, the layer is a re-reporter, and §5.6 is the real story.**

### E1c — Cost per verified finding (closes N6)

**Method:** from E1b, join each surfaced item to the arm's JSONL token totals; divide by the count of items that survived to a MANDATED fix and were verified as real in the follow-up diff. Compare against the same figure for `build-refine`.

### E2 — The authority ablation nobody has published (closes N2)

**Question:** does removing edit authority change what gets STATED?

**Method:** same mutant PR, same model, same fresh context, **prompt differing in exactly one respect** — arm A keeps `review-pr`'s "you are decide-only" constraint; arm D grants edit authority and instructs the actor to fix what it finds while still writing its comment. Everything else identical.

**Reads out:** (i) count of findings explicitly stated in the output comment; (ii) count of defects actually repaired in the diff; (iii) the **absorption rate** — defects repaired in arm D that appear nowhere in arm D's comment.

**This is the experiment that resolves the paper's central gap.** The hypothesis from §1.1(b) predicts arm D's absorption rate is materially above zero — a fix made and never stated. If absorption is ~0, the authority seam is buying nothing, and `decide ≠ act` should be justified on retry/resume grounds (which `workflow-scripts.md` already offers as a second, independent reason) rather than on bias grounds.

### E3 — Cross-family judge (tests P9)

**Method:** run `review-pr` twice on the same PR — same model family as the author, and a different family. Compare finding counts, overlap, and MERGE rate.

**Reads out:** whether self-preference [S15] is visible at this repo's scale. **Predicted by [S15] and [S11]:** the same-family judge issues more `MERGE`s and finds fewer items. If confirmed, pinning `review-pr` to a different family is a one-line, high-value change.

### E4 — Uptake (tests P10, [S25]'s warning)

**Method:** for every `HOLD - redispatch` in the log history, parse the mandated fixes out of the disposition comment and diff the subsequent `build-refine` commit against them. Count mandated items actually addressed, partially addressed, and ignored.

**Reads out:** the **uptake rate**, a first-class metric this repo does not currently compute. [S25] says detection quality and uptake are separable; a decide-only design is exactly the design where they can come apart, and a high-precision judge with 40% uptake is a layer working at 40% of its measured value.

### E5 — The correlated-hallucination check ([S11]'s padding oracle)

**Method:** from E1's mutant runs, count **false positives** — items the judge mandated as fixes that the seeded ground truth says were not defects — and check how many survived into an actual edit in the follow-up refine.

**Reads out:** the rate at which the layer *injects* changes for non-problems. [S11] says this is the dominant failure of separated LLM reviewers and that only an empirical gate killed it. If the rate is non-trivial, the correct response is a test/CI gate on mandated fixes, not a better judge prompt.

### What research still cannot settle even after these

- Whether the effect persists as models improve (§5.2). Every arm above is a snapshot; the design's justification is a *deficit* in same-context self-review, and deficits close.
- Whether the self-report-auditing task (§5.7, N5) behaves like the artifact-review task the literature measures. E1b's classification will hint at it; nothing here proves it.
- Whether any of this generalises past the coding edge. Element 2 is stated domain-generally; every experiment above is a coding experiment, and the problem statement's own test — *"would this still make sense if the edge were a building controller?"* — is not answerable from this corpus.
