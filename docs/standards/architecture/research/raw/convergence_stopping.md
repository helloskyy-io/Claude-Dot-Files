# Convergence vs. Count: What the Evidence Says About Stopping an Iterative Review Loop

```
Topic:          When an iterative review loop re-runs against its own prior output, does the
                yield plateau — and what does the evidence establish about stopping on
                CONVERGENCE rather than on a fixed pass count?
Feeds:          `Phase: Autonomous Operation` in docs/development/roadmap.md — the milestone
                "Exit criteria that are real and observable ... 'stop' has to be a state
                something can *observe*, not a turn count"; AND the one-loop-back bound
                already shipped in scripts/workflows/revision.sh (lines 21-26, 309-325).
Last validated: 2026-08-03
Revalidate:     high — 6 weeks
Confidence:     DEFINITIVE on what each cited study measured and on the framework stopping
                APIs (first-party docs + raw arXiv metadata, all fetched). DEFINITIVE on the
                negative finding that the "3-5 passes" figure has no source describing our
                topology. DIRECTIONAL on the two 2026 single-author preprints that speak most
                directly to our shape (2605.12280, 2606.27009) — each is a first-party report
                of its own experiment, neither is replicated. DIRECTIONAL likewise on every
                other single-author preprint (2601.00828, 2603.12123, 2512.10350) and on the
                classical fixpoint-termination framing in §1.3, whose primary texts did not
                extract. DERIVED (and flagged as such) on the cumulative-coverage arithmetic
                in §2.2.6. UNVERIFIED on anything drawn from vendor blog commentary, which is
                used only where corroborated.
Critic:         PASS-WITH-FIXES (three [S32] quotes were not verbatim — one phrase, "context
                bloat", was invented inside quotation marks — now replaced with the source's
                actual wording; [S16]/[S17] and [S24] were marked definitive against this
                paper's own sourcing rule and are downgraded to directional; one AutoGen
                quote was silently compressed and is restored) — 2026-08-03
```

> **Mixed volatility (§3).** The load-bearing core of this paper — Self-Refine, Huang et al.,
> the Kamoi TACL survey, Porter et al. 1998, Böhme et al. 2021, Cousot — is **low-volatility
> academic synthesis** (§§1, 2.1, 2.2.5, 5.3-5.5); a refresh may skip re-verifying it. The
> **high-volatility** material is §2.3, §3 (framework stopping APIs move with SDK releases)
> and the 2026 preprints in §2.2 (unreplicated, may be superseded or withdrawn). The header
> takes the highest tier present.

---

## 0. Headline: the question is the right one, and the current in-code justification does not survive it

`revision.sh` today caps the correction loop at exactly one loop-back and justifies it in a
comment: *"Self-correction plateaus at ~3-5 passes."* This paper's central finding is about
that sentence's **provenance**, not its plausibility:

**No study located in this sweep establishes a plateau at 3-5 passes for a loop whose passes
are separate processes with separate contexts.** The two studies that produce a "3-5"-shaped
number both (a) run a single actor inside a single context and (b) **truncate their own sweep
at or near the plateau they report** — Self-Refine caps at 4 iterations by construction
[S1], Nexus sweeps 0-5 and reports plateau "after 3 to 5" [S14]. A study that stops at 4
cannot observe pass 6. The number is real as a description of what those experiments saw; it
is not evidence about what a sixth pass by a different process would find.

Meanwhile the closest published analogue to our topology — a nine-round, fresh-agent audit of
a multi-agent prompt specification — reports per-round defect counts of
**15, 8, 12, 2, 8, 1, 4, 1, 0** and names the pattern *"non-monotonic convergence"* [S15].
Round 3 out-yielded round 2. Round 5 out-yielded rounds 4 *and* 3-adjacent. A counter set to
"stop after the yield first drops" would have stopped at round 4 and missed 14 more defects.
That is an independent, external reproduction of the shape the operator observed on PR #233.

This does **not** establish that convergence-based stopping is correct. §5 collects a serious
case against it, including one result (adaptive bias, [S10]) that says naive "no new findings
lately" rules **systematically under-estimate** remaining risk, and one human-subject result
([S12]) where adding review passes did *not* raise defect detection at all.

---

## 1. Primer

### 1.1 Three different things are all called "the plateau"

The word "plateau" is doing three incompatible jobs in this literature, and conflating them is
the whole failure mode of the extrapolation this paper was commissioned to check.

| # | Claim | What it is about | What would falsify it |
|---|---|---|---|
| **P1** | **Marginal quality gain** decays across refinement iterations | A *score* on the artifact (accuracy, preference, F1) | A later iteration raising the score as much as an early one |
| **P2** | **The defect pool saturates** — passes stop finding *new* things | A *set* of findings and its growth rate | A later pass returning a finding absent from every prior pass |
| **P3** | **The loop reaches a fixpoint** — the operator maps its input to itself | A *deterministic transformation* and its stability | The same input producing different output on re-run |

Self-Refine measures **P1** [S1]. Our system cares about **P2** (a credential leak found on
pass 2 is new work regardless of any score) and can only mechanize **P3** (an unchanged tree
reviewed again). P1 evidence does not transfer to P2: a pass can add zero to a quality score
while adding a Critical finding, and a pass can raise a score by rewording without finding
anything. *(Confidence: derived — from the definitions in [S1], [S15], [S6].)*

### 1.2 The substrate distinction that the literature mostly does not make

Every foundational self-correction result assumes **one actor, one context**: the generator,
the critic, and the reviser are the same model in the same conversation with the same
accumulated state. That is stated plainly by the field's own critical survey, which excludes
the alternative *by construction*:

> "Cross-model correction uses different models for initial response generation and
> self-correction, so it is unsuitable for evaluating whether LLMs can improve their own
> initial responses [RQ1, RQ2]." — Kamoi et al., TACL 2024 [S3]

That sentence is the crux of this paper. The survey's headline negative results are scoped, by
the authors' own framing, to the same-actor case. **Our pipeline is the excluded case**:
`revision-draft` and `revision-refine` are separate `claude` processes with disjoint contexts,
and `review-pr` is a third with different instructions and — the operator's word — different
*stakes* (it may not author, only judge). *(Confidence: definitive on the quote; derived on
the mapping to our topology, from `revision.sh` lines 28-38.)*

### 1.3 What "convergence" means formally, and why the LLM case does not inherit it

In program analysis, "iterate until it stops changing" is a *proof* of termination only under
specific conditions: the abstract domain must satisfy the ascending chain condition or have
finite height, or the iteration must be forced to terminate with a widening operator
[S16], [S17]. The reason is that a fixpoint iteration over an infinite-height lattice can
climb forever without ever repeating.

A pass's finding-set has **neither property**. There is no finite lattice of findings, no
monotonicity guarantee (pass N+1 can retract pass N's finding), and the operator is
stochastic. So "two passes produced the same set" is **a sample, not a fixpoint**. This is not
a pedantic distinction — §2.2.4 gives the empirical version: the same model reviewing the same
artifact five times produces largely *disjoint* finding sets [S6].

*(Confidence: **directional** on the ACC / finite-height / widening termination conditions
[S16], [S17] — the primary texts did not extract in this environment and the claim rests on
search-corroborated summaries, which is the same sourcing posture that put [S25], [S26] and
[S34] at directional. It is uncontested textbook material and I have no reason to doubt it,
but a claim whose primary was never fetched does not meet §3's bar for **definitive**, and
marking it so would be exactly the inflation this paper faults elsewhere. **Derived** on the
non-inheritance argument. Nothing load-bearing rests on this paragraph — it supplies the
vocabulary for §5.3, whose argument is carried by [S10], which was fetched.)*

---

## 2. The specific options — what the evidence actually establishes

### 2.1 Where the plateau claims come from, audited one by one

**2.1.1 Self-Refine (Madaan et al., NeurIPS 2023) — the usual citation, and it does not say this.**

Verbatim from the paper's own text:

> "The feedback-refine iterations continue until the desired output quality or task-specific
> criterion is reached, **up to a maximum of 4 iterations**." [S1]

> "Figure 4 highlights the **diminishing returns** in the improvement as the number of
> iterations increases." [S1]

> "The stopping condition stop(fb_t,t) either stops at a specified timestep t, or **extracts a
> stopping indicator (e.g. a scalar stop score) from the feedback**." [S1]

Three findings follow, all **definitive**:

1. **The experiment is truncated at 4.** A plateau "at 3-5" cannot be read off a sweep whose
   maximum is 4. The paper reports diminishing *marginal* gain (P1) inside that window — e.g.
   Code Optimization 22.0 → 28.8 over three iterations, with the y₂→y₃ delta at 0.9 points
   against a y₀→y₁ delta of ~5 [S1].
2. **The word "plateau" does not appear** in the paper's discussion of iteration counts; the
   term used is "diminishing returns." Plateau (yield → 0) and diminishing returns (yield → a
   smaller positive number) are different claims, and the second does not imply the first.
3. **Self-Refine's own stopping rule is already convergence-flavoured, not a counter.** The
   iteration cap is a *backstop* behind a feedback-derived stopping indicator. The canonical
   citation for "use a fixed count" in fact implements judge-declared stopping with a count as
   the guard rail.

*Sourcing note: quotes taken from the ar5iv LaTeX-derived HTML of arXiv:2303.17651; the arXiv
PDF did not extract. Metadata (authors, versions, abstract) verified independently against the
arXiv API. Marked definitive but quoted conservatively — only spans visible in the fetch.*

**2.1.2 Nexus (Huang et al., 2025) — the one real "3 to 5", from a different setup.**

> "Performance continues to climb with additional steps, generally beginning to plateau after
> **3 to 5 iterations**." [S14]

Same structural caveat: §5.3 of that paper varies refinement loops **from 0 to 5** and adopts
5 as its default. The plateau is reported at the boundary of the swept range, and the authors'
own response to it was to *keep* five steps, not to cut to one. The task is execution-grounded
test-oracle synthesis by a multi-agent framework — closer to our shape than Self-Refine, but
still one artifact under one framework's control loop, not separate dispatches against a PR.
*(Confidence: definitive on the quote — fetched from the arXiv LaTeX-derived HTML; directional
on transfer.)*

**2.1.3 Huang et al., "LLMs Cannot Self-Correct Reasoning Yet" (ICLR 2024) — and the
stopping-criterion leak.**

> "After self-correction, the model's performance **drops on all benchmarks**." [S2]

> "Among the remaining instances, the model is **more likely to modify a correct answer to an
> incorrect one** than to revise an incorrect answer to a correct one." [S2]

And, critically for *this* paper's question, the authors flag that the field's stopping rule
was cheating:

> "we follow previous works in **using the correct label to determine when to stop the
> self-correction loop**." [S2] … "In a realistic setting … the correct answer is unknown to
> us." [S2]

**This is the single most important methodological finding in the corpus for our purposes.**
A large share of published self-refinement gains were measured under a stopping rule that had
oracle access to the answer. The Kamoi survey independently names the same defect in specific
systems: RCI prompting "uses ground-truth answers and does not apply self-correction when the
initial responses are correct"; Reflexion "generates feedback by using an exact match between
the generated and ground-truth answers, which cannot be accessed in real-world applications"
[S3]. Consequence: **the literature's iteration-count guidance was tuned under an oracle
stopping rule and does not transfer to a deployment that has no oracle.** *(Confidence:
definitive on all four quotes; derived on the consequence.)*

**2.1.4 The Kamoi TACL survey — the scoping that voids the extrapolation.**

> "no prior work demonstrates successful self-correction with feedback from prompted LLMs,
> except for studies in tasks that are exceptionally suited for self-correction" [S3, abstract
> via arXiv API]

Paired with the cross-model exclusion quoted in §1.2, the survey's position is: *same-model
prompted self-critique mostly does not work*, and *different-model correction is a different
question we are not answering here*. Neither statement supports a pass cap for a
different-process pipeline. **A negative result about same-actor self-critique is not a
diminishing-returns curve for cross-actor review.** *(Confidence: definitive on the quotes;
derived on the conclusion.)*

**2.1.5 Self-Correction Bench (Tsui, 2025) — the mechanism behind the split.**

> LLMs "cannot correct errors in their own outputs while successfully correcting identical
> errors from external sources," at a measured **64.5% average blind-spot rate across 14
> models** [S4, abstract via arXiv API].

This is the causal story for why a process boundary matters: the *same error text* is
correctable when it arrives from outside and not when it is the model's own. Corroborated in
kind by the accuracy-correction paradox result, where "intrinsic self-correction … remains
largely ineffective" and weaker models showed *higher* intrinsic correction rates than stronger
ones [S5]. *(Confidence: definitive on what each paper claims; [S5] is a single-author
preprint — treat its numbers as directional.)*

**2.1.6 Multi-agent debate — where a genuine 2-3 round convergence does appear.**

Du et al. run multiple model instances that "debate their individual responses and reasoning
processes over multiple rounds to arrive at a common final answer" [S7]. Secondary syntheses
report consensus typically within 2-3 rounds with accuracy plateauing there
*(uncorroborated commentary — flagged, not relied on)*. The rigorous counterweight is Huang et
al.'s direct comparison:

> "multi-agent debate **significantly underperforms simple self-consistency using majority
> voting**." [S2]

Debate is the closest published thing to "several actors with separate contexts iterate," and
its convergence at 2-3 rounds is the strongest published support for a low cap. But note what
converges: debate converges on **agreement**, which is a consensus signal, not a
defect-exhaustion signal. Agreement can be reached while the defect pool is untouched —
indeed [S2] finds debate barely beats majority vote, which finds nothing new at all.
*(Confidence: definitive on the quotes; derived on the agreement-vs-exhaustion distinction.)*

### 2.2 Does any of it hold when reviser ≠ reviewer? The direct evidence

**2.2.1 Context separation itself is the active ingredient (Cross-Context Review, 2026).**

A controlled experiment injecting exactly 5 errors into each of 30 artifacts (150 ground-truth
errors), all reviews by Claude Opus 4.6, 3 runs, 360 reviews total, four conditions [S8]:

| Condition | What the reviewer sees | F1 | Precision | Recall |
|---|---|---|---|---|
| **CCR** — fresh session, artifact only | artifact only | **28.6%** | 31.5% | 27.1% |
| **SR** — self-review, same session | full history | 24.6% | 25.8% | 24.2% |
| **SA** — subagent, fresh + prompt | prompt + artifact | 23.8% | 27.4% | 21.8% |
| **SR2** — self-review twice, same session | full + 1st review | **21.7%** | 21.0% | 22.7% |

Reported significance for the headline comparison: "an F1 of 28.6%, outperforming SR (24.6%,
p=0.008, d=0.52)" [S8, abstract via arXiv API]. The paper's own framing of the control:
"Reviewing twice in the same session does not help — it actually hurts precision," with the
SR-vs-SR2 contrast itself not significant (reported p = 0.11) [S8, HTML].

Two things this establishes and two it does not.

- **Reports (definitive that the paper reports it; directional as a result):** a second pass
  *in the same context* is the worst of the four conditions, and *removing production history*
  beats keeping it. The benefit is attributed to context separation, not model capability.
- **Reports (same tier):** **absolute per-pass recall is ~22-27%.** One review pass, in the
  best condition, finds about a quarter of the known-present errors.
- **Does not establish:** anything about a *second fresh* session. The design has no
  CCR×2 arm. The repetition control was run only on the same-session condition.
- **Limitations, per the paper:** single model, injected rather than natural errors, moderate
  absolute F1, no human baseline, a language confound (Korean artifacts / English reviews),
  narrow domain [S8]. It is a single-author 2026 preprint. **Directional, not definitive.**

**2.2.2 Repeated independent passes on the same artifact find largely disjoint sets
(SWR-Bench, 2025).**

On 1000 manually verified PRs [S6]:

> "for different LLMs only **36** successfully identified change-actions overlapped" [S6, HTML]

> "for the same LLM over **five independent runs**, only **27** successfully identified
> change-actions overlapped" [S6, HTML]

And the direct consequence the authors then exploit:

> "execute PR-Review (or another ACR tool) multiple times on the same code change to generate
> n independent review reports, which are then aggregated into a final review report using an
> additional LLM call" [S6, HTML] → "Gemini-2.5-Flash with Self-Agg (n=10) achieved an F1 of
> 21.91% (a **43.67% increase**)" [S6, HTML]

**This is the strongest published evidence against a low fixed cap for our topology.** Ten
independent passes over the *same unchanged input* still improved the finding set by 44%
relative. There is no plateau at 3-5 here; the authors chose n=10 and reported gains.
*(Confidence: definitive on the quotes — abstract cross-verified via arXiv API, quotes from
the arXiv HTML; the caveat is that these are **parallel independent** reviews aggregated, not
**sequential** passes reading a revised artifact. That distinction is real and unbridged.)*

**2.2.3 Coverage from repeated independent sampling grows log-linearly, over orders of
magnitude.**

"Large Language Monkeys" reports coverage — "the fraction of problems that are solved by any
generated sample" — scaling log-linearly with sample count, with SWE-bench Lite going from
15.9% at one sample to **56% at 250 samples** [S9]. Codex reported the same shape earlier:
28.8% at one sample, 70.2% with 100 [S18]. Both also report the *selection* problem: methods
for picking the right sample "plateau beyond several hundred samples" [S9].

The transfer is imperfect (solving a task ≠ finding a defect) but the structural lesson is
exact and **derived**: *when passes are independent, the union keeps growing long past the
point where any single pass's marginal quality gain has flattened, and the binding constraint
moves from generation to selection.* [S9], [S18], [S6].

**2.2.4 The closest published analogue to our loop, and it is non-monotonic.**

The Iterative Audit Convergence case study audits a seven-lane production multi-agent pipeline
— a 7152-line specification surface — "across nine rounds, surfacing 51 consistency defects
(per-round counts of **15, 8, 12, 2, 8, 1, 4, 1, 0**)," reporting "**non-monotonic convergence
consistent with cascading edits and audit-scope expansion**, and a locked audit protocol"
[S15, abstract via arXiv API]. Its cross-vendor replication: a panel of four frontier vendors
across 12 traces, where the "**multi-vendor union detects all five seeded defects**" [S15];
inter-rater reliability Cohen's κ = 0.80 on category, 0.46 on severity [S15].

Why this matters here, in order of load:

1. **The sequence is non-monotonic.** Any stopping rule of the form "stop when yield drops"
   fires at round 4 (yield 2, down from 12) and forfeits rounds 5-8's 14 defects.
2. **The terminating round is a zero-round.** The audit ran to an actual empty pass — the
   convergence criterion in its strongest form.
3. **It independently reproduces the operator's PR #233 observation** on a different system,
   different repo, different task shape. Two independent n=1s pointing the same way is not a
   result, but it does relocate the burden of proof.
4. **The multi-vendor union finding** matches SWR-Bench's overlap result: no single reviewer
   found everything; the union did.

**Limits, stated plainly.** Single-author 2026 preprint. Single-system case study, post hoc
taxonomy. **A gap I could not close: whether each audit round ran in a fresh context or a
separate process is not determined from the abstract**, and the paper's arXiv HTML render is
not available (`arxiv.org/html/2605.12280` and `.../v2` both returned 404; the PDF path does
not extract in this environment; the arXiv API supplies abstract-level metadata only). Treat
the round-structure detail as **unverified**. **Directional overall.**

**2.2.5 A separate critic beats the author — and hallucinates.**

OpenAI's CriticGPT work trains critic models that "help humans to more accurately evaluate
model-written code," with "model-written critiques … preferred over human critiques in 63% of
cases," while explicitly warning that LLM critics can "hallucinate bugs" that mislead human
reviewers [S13, abstract via arXiv API]. The mechanism-level reason a *different* evaluator is
needed at all is well documented: LLM evaluators show measurable **self-preference bias**
correlated with self-recognition ability [S19]; RLHF-trained assistants show **sycophancy**,
with preference models "sometimes favor[ing] convincing sycophantic responses over correct
ones" [S20]; and LLM reviewers "systematically inflate scores for LLM-authored papers" while
"persistently underrat[ing] human-authored papers with critical statements" [S21].
*(Confidence: definitive on all four abstracts, fetched via arXiv API.)*

**2.2.6 DERIVED: the arithmetic of low per-pass recall.**

Taking CCR's best-condition recall of 27.1% [S8] and *assuming* passes were independent,
cumulative coverage after n passes is 1 − (1 − 0.271)ⁿ: **27% after one pass, 47% after two,
61% after three, 78% after five.** Under those assumptions the third pass adds ~14 percentage
points of coverage — not a plateau.

**This is derived and the assumption is almost certainly false.** Passes are positively
correlated (some defects are easy for every reviewer, some are invisible to all), which flattens
the curve; SWR-Bench's small-overlap result [S6] suggests correlation is *lower* than intuition
expects, but "lower than expected" is not "zero." The honest reading is: **a plateau claim
requires per-pass recall near 100%, and the only measured per-pass recall in this corpus is
near 25%.** Derived from [S8] recall figures and [S6] overlap figures; contradicted by nothing
located, but not directly tested by anything either.

### 2.3 What is actually computable from two successive pass outputs

Five mechanism classes, ordered by how much structure they require from the handoff.

| Class | Signal | Input required | Status in the corpus |
|---|---|---|---|
| **A. Set fixpoint** | pass N+1's finding set ⊄ pass N's | **typed, comparable finding records** | Mechanically trivial; formally unsound here (§1.3, [S16]/[S17]) |
| **B. Semantic distance + patience** | cos-distance between successive draft embeddings below ε for k rounds | two text outputs + an embedding model | Directly measured [S11] |
| **C. Agreement / self-consistency** | code stability, semantic self-consistency, lexical confidence; majority agreement | multiple parallel outputs | [S22] (metrics), [S23] (majority vote) |
| **D. Dynamical regime** | contractive / oscillatory / exploratory classification | a trajectory of ≥3 iterations in embedding space | [S24] |
| **E. Residual-risk estimation** | capture-recapture from inter-pass overlap; discovery-probability upper bound | **two or more independent passes' finding sets, with overlap** | [S25]/[S26] (inspections), [S10] (fuzzing) |

**Class B is the only one measured end-to-end against a fixed cap.** Semantic Early-Stopping
halts "when consecutive draft embeddings stop changing in meaning (cosine distance with a
patience window) and the answer's measured quality stops improving" [S11]. On HotpotQA (60-
question test split, llama-3.1-8b-instruct for writer/critic/judge), the **judge-free** variant
"reduces operational tokens by **38%** relative to max_iterations at parity quality (Delta-IS =
−0.004, p = 0.81)" [S11]. The **judge-gated** variant is worse than useless: "full shp is
counter-productive" at "+129% tokens" [S11] — the per-round judging dominates the savings.

And the paper's own reframing, which is the most important sentence in §2.3:

> "An oracle that selects the best round attains **+0.115 Information Score over every
> practical policy** (p ~ 4e-11), reframing the problem from **'when to stop' (easy)** to
> **'which round is best' (open)**." [S11]

The authors also downgrade their own theory honestly — they "prove deterministic termination
and well-definedness" but treat "the convergence of the distance sequence as an empirically
tested conjecture rather than a (previously over-claimed) Banach contraction" [S11] — and note
that "the benchmark under-exercises iteration" because "HotpotQA answers are short and often
answerable from a single grounded draft" [S11]. **Single-author 2026 preprint, one benchmark,
an 8B model. Directional.**

**Class E is the one nobody in the LLM literature is using, and it is the one that answers the
actual question.** Capture-recapture estimates *remaining* defect content from the overlap
between independent reviewers' finding sets — first applied to software inspections by Eick et
al. in 1992, with model variants (Mt, Mh) for equal vs. varying per-defect detection
probability [S25], [S26]. Fuzzing's modern equivalent estimates the probability that the *next*
input finds something new [S10]. Both convert "two passes' outputs" into an *estimate of what is
still missing*, which is strictly more information than "did the second pass find something."
**Both also require the passes to be independent and the overlap to be identifiable** — which
in turn requires findings to be typed and matchable, not prose. *(Confidence: **definitive**
for [S10] — its abstract was fetched verbatim and states exactly what it estimates.
**Directional** for the capture-recapture line [S25], [S26]: neither primary extracted, so the
Eick-1992 origin and the Mt/Mh model split rest on corroborated search summaries. §5.3 covers
why [S10] is simultaneously the strongest argument against the naive version of Class A.)*

**What is NOT computable from two pass outputs — stated as a gap:**

- **Whether the findings still missing matter.** Every convergence signal above measures
  *discovery rate*, none measures *residual severity*. A loop can converge with a Critical
  unfound; nothing in the corpus detects that from the loop's own outputs.
- **Which round was best.** [S11]'s oracle gap is large and unclosed.
- **Whether a zero-finding pass means "clean" or "the reviewer failed."** The finding-set
  difference is identical in both cases. No source located distinguishes them from pass
  outputs alone.

---

## 3. Comparative landscape — the five stopping rules, fairly stated

First-party mechanisms exist for all five. AutoGen's termination-condition catalogue is the
most complete single enumeration and maps cleanly onto the taxonomy [S27].

| Rule | First-party mechanisms | What it gets right | Where it fails |
|---|---|---|---|
| **Fixed count** | OpenAI Agents SDK `max_turns` → `MaxTurnsExceeded` [S28]; LangGraph `recursion_limit` → `GraphRecursionError` [S29]; Claude Agent SDK `max_turns` [S30]; AutoGen `MaxMessageTermination` [S27]; Anthropic: "it's also common to include stopping conditions (such as a maximum number of iterations) to maintain control" [S31] | Guaranteed termination; trivially auditable; zero measurement cost; bounded blast radius | "syntactic kill-switch … blind to whether the answer is still improving, so it **over-spends tokens on easy inputs and truncates hard ones**" [S11]. The number must come from somewhere — and §2.1 shows the usual somewhere doesn't support it. |
| **Budget ceiling** | AutoGen `TokenUsageTermination`, `TimeoutTermination` [S27] | Bounds the thing that actually costs money; degrades gracefully; the natural outer guard | Says nothing about work quality. Uncorrelated with whether the task is done — a cheap pass that finds a Critical and an expensive one that finds nothing are treated identically. |
| **Convergence** | AutoGen `FunctionalTermination` — "Stop when a function expression is evaluated to `True` on the last delta sequence of messages" [S27] — is the only first-party *predicate* hook located; the semantic-distance rule of [S11]; the "one clean pass" rule of [S15] | Stops on an *observable state*, not a turn count; measured 38% token saving at parity in the one head-to-head [S11]; adapts per-task | Termination is not guaranteed (§5.1). Naive forms under-estimate residual risk (§5.3). Requires comparable outputs — prose diffs are not a finding-set difference. |
| **Judge-declared** | Self-Refine's feedback-extracted stop indicator [S1]; AutoGen `TextMentionTermination`, `StopMessageTermination` [S27]; our `VERDICT: MERGE` | Uses the richest available signal; already how `review-pr` terminates today | Inherits every judge pathology: self-preference [S19], sycophancy [S20], score inflation for machine-authored work [S21], hallucinated findings [S13]. And it costs a full LLM call per check — the failure mode measured at +129% tokens in [S11]. |
| **Human hold** | AutoGen `ExternalTermination` ("programmatic control of termination from outside the run") and `HandoffTermination` [S27]; Anthropic: "Agents can then pause for human feedback at checkpoints or when encountering blockers" [S31]; our `HOLD - needs-assistance` | The only rule that can stop on a *judgement* the loop cannot produce. Correct by construction for its case. | Not autonomous — it is the exit from autonomy, not a mode of it. Latency is unbounded. Does not scale to the "nobody presses the button" phase. |

**Two observations from the landscape, both derived:**

1. **Every production framework surveyed ships a count or a budget as the guaranteed backstop,
   and offers convergence/judge rules as the *primary* rule layered in front of it.** AutoGen's
   AND/OR composition [S27] and Self-Refine's own design [S1] are both this shape. Nothing
   located ships convergence *without* a backstop.
2. **"Fixed count vs. convergence" is a false binary in every real system.** The live question
   is which rule is *primary* and what the backstop's number is for — bounding cost and blast
   radius (defensible without a plateau claim) versus encoding a belief about when work stops
   being productive (which needs evidence this paper could not find).

---

## 4. What this provides — enumerated, citable properties

Properties a plan may rely on, each with its source and confidence.

**P1. The "3-5 passes" figure has no source describing separate-process review.** Self-Refine
truncates at 4 [S1]; Nexus sweeps 0-5 and defaults to 5 [S14]; both are single-loop,
single-artifact setups. *(definitive — negative finding; search method in §6.)*

**P2. The field's critical survey explicitly excludes the cross-actor case from its negative
results.** [S3]. *(definitive)*

**P3. A large share of published iteration-count guidance was measured under an oracle stopping
rule.** Huang et al. state they used the correct label to decide when to stop [S2]; the Kamoi
survey names the same defect in RCI and Reflexion [S3]. *(definitive)*

**P4. Same-context repetition is measurably the worst option.** Second review in the same
session scored lowest of four conditions (F1 21.7% vs. 28.6% for fresh-context) [S8].
*(directional — one preprint, one model, injected errors)*

**P5. Context separation, not model capability, carries the benefit.** [S8], mechanistically
supported by the 64.5% self-correction blind-spot rate [S4] and the accuracy-correction paradox
[S5]. *(directional)*

**P6. Single-pass review recall is low — ~22-27% in the only controlled measurement located.**
[S8]. *(directional; the single most load-bearing number for any plateau argument)*

**P7. Independent passes over the same artifact produce largely disjoint finding sets, and
aggregating ten of them improved F1 by 43.67%.** [S6]. *(definitive on the paper's claims;
parallel-not-sequential caveat stands)*

**P8. Per-round yield in a nine-round fresh-audit loop was non-monotonic (15, 8, 12, 2, 8, 1,
4, 1, 0).** [S15]. *(directional — single-author case study; round-structure detail
unverified)*

**P9. Convergence-based stopping has been measured against a fixed cap exactly once, and won on
cost at parity quality: −38% operational tokens, ΔIS = −0.004, p = 0.81.** [S11].
*(directional — 60 questions, one benchmark, 8B model)*

**P10. The judge-gated form of convergence detection cost +129% tokens** — measurement expense
can exceed the savings [S11]. *(directional)*

**P11. Convergence detection requires typed, comparable outputs.** Classes A and E are
unavailable against prose logs; Class B needs only text but measures P1-style semantic drift,
not P2-style defect discovery [S11], [S25], [S10]. *(derived, from the mechanism requirements
in the cited work — this is the concrete dependency on the handoff-contract work)*

**P12. Every surveyed production framework pairs its primary stopping rule with a hard count or
budget backstop.** [S27], [S28], [S29], [S31]. *(definitive)*

**P13. Statistical machinery for "how much is still unfound" exists and is unused in the LLM
loop literature** — capture-recapture from inter-pass overlap [S25], [S26]; discovery-probability
upper bounds [S10]. *(definitive that the methods exist; negative finding that no located LLM
review-loop paper applies them — see §6 search method)*

---

## 5. Honest boundary analysis — when convergence-based stopping is worse than a counter

This section is the case against this paper's own centre of gravity. It is not
counterbalancing garnish; three of these are strong enough to sink a naive convergence rule.

### 5.1 It does not guarantee termination, and non-termination is an empirically common failure

An Infinite Agentic Loop is defined as "an execution failure in which an agentic feedback path
repeatedly triggers costly or state-growing actions without an effective stopping bound"
[S32]. Such failures "can amplify a single request into long running model and tool execution,
causing **cost exhaustion, model denial of service, context growth, and repeated external side
effects**" [S32]. And on where they come from: "IALs are not ordinary programming loops; they
arise from the interaction between **agent logic, framework semantics, runtime observations,
and termination mechanisms**" [S32]. A static analyser over 6,549 repositories "reported 74
potential findings, with manual review confirming **68 IAL failures across 47 projects**,
achieving 91.9% precision" [S32].
These are shipped open-source projects. A counter cannot produce this failure; a convergence
predicate can. *(definitive on the paper's claims — abstract fetched via the arXiv API, body
quotes re-fetched verbatim from https://arxiv.org/html/2607.01641v1 after the critic pass
caught three non-verbatim quotations here. Note the fourth term in the source's causal list,
"runtime observations", which the earlier draft dropped: it strengthens §5.2's point rather
than weakening it — regime is a function of what the loop observes at runtime, not of prompt
design alone.)*

### 5.2 The oscillatory regime is a documented attractor, not an edge case

Iterative LLM systems modelled as discrete dynamical systems in semantic space exhibit three
regimes — "contractive (convergence to stable attractors), **oscillatory (cycling among
attractors)**, and exploratory (unbounded divergence)" — and "prompt design directly controls
the dynamical regime," so "the same model [exhibits] fundamentally different behaviors
depending on transformations applied" [S24]. A loop cycling between two finding sets never
satisfies a naive "no new findings" test and never terminates. **A convergence rule inherits a
dependency on prompt design that a counter does not have.** *(**Directional** — single-author
preprint, same tier as [S5], [S8], [S11], [S15]; the analysis is purely semantic and is not
coupled to task performance or to any execution substrate.)*

### 5.3 Adaptive bias: "nothing new lately" systematically under-estimates what is left

The strongest single argument against naive convergence stopping, and it is rigorous. From the
ESEC/FSE 2021 abstract, verbatim:

> "For any errorless fuzzing campaign, no matter how long, there is always some residual risk
> that a software error would be discovered if only the campaign was run for just a bit longer.
> … We find that estimators for blackbox fuzzing **systematically and substantially
> under-estimate the true risk**. An engineer—who stops the campaign when the estimators
> purport a risk below the maximum allowable risk—**is vastly misled**. She might need execute
> a campaign that is **orders of magnitude longer** to achieve the allowable risk. Hence, the
> key challenge we address in this paper is **adaptive bias: The probability to discover a
> specific error actually increases over time**." [S10]

Mapped to our case (**derived**): a review pass that finds nothing is weak evidence that
nothing is there, and the naive estimator is biased in the *dangerous* direction. The
non-monotonic series in [S15] is the same phenomenon observed directly — a round yielding 2
was followed by a round yielding 8. **A convergence rule that stops on the first quiet pass is
the exact failure mode [S10] formalises.** The paper's remedy — a principled
discovery-probability upper bound rather than a raw "nothing new" test — is available in
principle but has no LLM-loop instantiation located (§6).

### 5.4 The human analogue says more passes may buy nothing

The most rigorous non-LLM evidence available, and it cuts against the thesis. Porter, Siy,
Mockus & Votta, TOSEM 1998, on professional inspections of a Lucent 5ESS compiler project:

> "we determined how various changes in three structural elements of the software inspection
> process (**team size, and number and sequencing of session**), altered effectiveness and
> interval" … "our results showed that such changes **did not significantly influence the
> defect detection reate** [sic], but that certain combinations of changes **dramatically
> increased the inspection interval**." [S12]

> "we found that they [reviewers, authors, and code units] were responsible for **much more
> variation in defect detection than was process structure**." [S12]

**This is the honest counter to §2.2's optimism.** In the closest well-powered human study, the
number of review sessions was *not* the lever; who was reviewing and what was being reviewed
were. If that transfers, per-pass yield is dominated by task and reviewer variance, and any
stopping rule — count or convergence — is tuning a second-order term. It also names the real
cost: latency. *(definitive on the quotes, from the University of Maryland institutional-
repository record; the ACM DL page returned 403. Transfer to LLM reviewers is **unverified** —
nothing located tests it.)*

### 5.5 A pass that finds nothing is not free, and a noisy reviewer can prevent convergence

- **False positives dominate real static-analysis alarm streams and are expensive to
  dispose of.** The Tencent industrial study built its dataset from 433 alarms of which **328
  were false positives** [S33], and reports that false positives require manual inspection per
  alarm *(inspection-time figure appeared only in a search-result summary, not in the fetched
  abstract — treated as **unverified** and not relied on)*.
- **LLM critics hallucinate findings.** CriticGPT's own paper warns critics can "hallucinate
  bugs" that mislead human reviewers [S13].
- **Derived consequence:** under a "stop when a pass finds nothing" rule, a reviewer with a
  non-zero hallucination rate **never emits an empty pass**, so the loop runs to its backstop
  every time and the convergence rule contributes nothing but the cost of evaluating it. This
  is the mechanism behind [S11]'s +129% judge-gated result [S11], [S13], [S33].

### 5.6 Premature saturation is the documented failure of "no new X" rules elsewhere

Qualitative research has used "stop when no new codes emerge" for decades and has a literature
on its abuse: reliance on data saturation alone leads to premature closure, the criterion is
routinely used to justify undersized samples, and theoretical saturation typically requires
substantially more data than data saturation [S34]. *(Confidence: **unverified** — these are
search-result summaries across a rendered-page corpus, not fetched primary text. Included
because the failure-mode shape corroborates §5.3 from an unrelated field, not as an
independent load-bearing claim.)*

### 5.7 Where a counter is simply the better instrument

Stated positively, because a fair comparison owes this:

1. **When the artifact is unchanged between passes.** Our own PR #224 reached eight `review-pr`
   passes, and pass 8 reviewed the same tree as pass 7 with no commits between, re-issuing the
   same runway (`revision.sh` lines 311-315). Here a *count* and a *trivial fixpoint check* do
   the same job, and the fixpoint check is cheaper — but note §1.3 and [S6]: for a stochastic
   reviewer, even an unchanged tree is not guaranteed to yield an unchanged finding set.
2. **When cost predictability is the requirement.** A count gives an exact worst-case bill; a
   convergence rule gives a distribution.
3. **When there is no typed payload.** Class A and E convergence require matchable findings
   (P11). Against two prose logs, "did this pass find something new" is itself an LLM judgement
   — i.e. judge-declared stopping wearing a convergence costume, with all of §5.5's pathologies.
4. **When blast radius, not yield, is the binding constraint.** An autonomous loop with commit
   authority has a failure mode a counter bounds absolutely and a convergence rule does not.

---

## 6. Citations

### 6.1 Negative findings and their search method

Per §3's requirement that a negative finding state how it was searched.

**N1. No study was located that measures marginal yield per *sequential* pass where each pass
is a separate process with a fresh context reviewing the *revised* artifact.** This is the
exact shape of `revision.sh` and of the PR #233 observation. Searched via: arXiv API id-lookup
and title search; web search on "ablation number of review rounds agentic pipeline fresh
context each round new defects found sequential passes", "measuring marginal new findings per
additional independent LLM review pass same artifact saturation code review agents",
"'ensemble' multiple independent LLM reviewers overlap union of defects found each reviewer
unique findings study"; and forward-reading from [S3], [S6], [S8], [S11], [S15]. The nearest
hits are [S6] (parallel independent, unchanged artifact), [S8] (single fresh pass, no ×2 arm)
and [S15] (sequential rounds on a changing artifact, but round-context structure not
determinable from the available text). **The crux experiment does not appear to exist.**

**N2. No LLM review-loop paper located applies capture-recapture or discovery-probability
estimation to its own pass outputs.** Searched via: web search combining the estimator names
with LLM/agent review terms; citation-direction check from [S10], [S25], [S26]; and inspection
of the convergence-metric papers [S11], [S22], [S24], none of which reference residual-risk
estimation. Stated as a gap, not as proof of absence.

**N3. The round-context structure of [S15] (fresh session per round vs. continuing context) is
not determined.** `arxiv.org/html/2605.12280` and `.../v2` both returned HTTP 404; the PDF
route does not extract text in this environment; the arXiv API returns abstract-level metadata
only. The per-round counts and the "non-monotonic convergence" characterisation are quoted from
the API-fetched abstract and are reliable; the protocol detail is not.

**N4. Self-Refine does not use the word "plateau" in its iteration discussion, and states no
3-5 figure.** Verified against the ar5iv LaTeX-derived HTML of arXiv:2303.17651 with a targeted
extraction prompt; the arXiv PDF did not parse and was not used. The only located source
stating "3 to 5" is [S14].

### 6.2 Source list

**Self-correction and refinement — peer-reviewed (low volatility)**

- [S1] Madaan, A., Tandon, N., Gupta, P., Hallinan, S., Gao, L., Wiegreffe, S., Alon, U.,
  Dziri, N., Prabhumoye, S., Yang, Y., Gupta, S., Majumder, B. P., Hermann, K., Welleck, S.,
  Yazdanbakhsh, A., & Clark, P. (2023). *Self-Refine: Iterative Refinement with Self-Feedback.*
  NeurIPS 2023. arXiv:2303.17651. https://arxiv.org/abs/2303.17651 — quotes from
  https://ar5iv.labs.arxiv.org/html/2303.17651
- [S2] Huang, J., Chen, X., Mishra, S., Zheng, H. S., Yu, A. W., Song, X., & Zhou, D. (2023).
  *Large Language Models Cannot Self-Correct Reasoning Yet.* ICLR 2024. arXiv:2310.01798.
  https://arxiv.org/abs/2310.01798 — quotes from https://ar5iv.labs.arxiv.org/html/2310.01798
- [S3] Kamoi, R., Zhang, Y., Zhang, N., Han, J., & Zhang, R. (2024). *When Can LLMs Actually
  Correct Their Own Mistakes? A Critical Survey of Self-Correction of LLMs.* TACL 2024.
  arXiv:2406.01297. https://arxiv.org/abs/2406.01297 — quotes from
  https://arxiv.org/html/2406.01297v3
- [S4] Tsui, K. (2025). *Self-Correction Bench: Uncovering and Addressing the Self-Correction
  Blind Spot in Large Language Models.* arXiv:2507.02778. https://arxiv.org/abs/2507.02778
- [S5] Li, Y. (2025). *Decomposing LLM Self-Correction: The Accuracy-Correction Paradox and
  Error Depth Hypothesis.* arXiv:2601.00828. https://arxiv.org/abs/2601.00828 *(single-author
  preprint — directional)*
- [S7] Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2023). *Improving
  Factuality and Reasoning in Language Models through Multiagent Debate.* arXiv:2305.14325.
  https://arxiv.org/abs/2305.14325

**Cross-context / multi-pass review evidence (high volatility — 2025-2026 preprints)**

- [S6] Zeng, Z., Shi, R., Han, K., Li, Y., Sun, K., Wang, Y., Yu, Z., Xie, R., Ye, W., & Zhang,
  S. (2025). *SWR-Bench: Assessing LLM Performance in Real-World Code Review Comment
  Generation.* arXiv:2509.01494. https://arxiv.org/abs/2509.01494 — quotes from
  https://arxiv.org/html/2509.01494v2
- [S8] Song, T.-E. (2026). *Cross-Context Review: Improving LLM Output Quality by Separating
  Production and Review Sessions.* arXiv:2603.12123. https://arxiv.org/abs/2603.12123 —
  condition table from https://arxiv.org/html/2603.12123 *(single-author preprint —
  directional)*
- [S9] Brown, B., Juravsky, J., Ehrlich, R., Clark, R., Le, Q. V., Ré, C., & Mirhoseini, A.
  (2024). *Large Language Monkeys: Scaling Inference Compute with Repeated Sampling.*
  arXiv:2407.21787. https://arxiv.org/abs/2407.21787
- [S13] McAleese, N., Pokorny, R. M., Ceron Uribe, J. F., Nitishinskaya, E., Trebacz, M., &
  Leike, J. (2024). *LLM Critics Help Catch LLM Bugs.* arXiv:2407.00215.
  https://arxiv.org/abs/2407.00215 — first-party OpenAI write-up:
  https://openai.com/index/finding-gpt4s-mistakes-with-gpt-4/
- [S14] Huang, D., Du, M., Zhang, J. M., Lin, Z., Luo, M., Zhang, Q., & Ng, S.-K. (2025).
  *Nexus: Execution-Grounded Multi-Agent Test Oracle Synthesis.* arXiv:2510.26423.
  https://arxiv.org/abs/2510.26423 — quote from https://arxiv.org/html/2510.26423v1 §5.3
- [S15] Calboreanu, E. (2026). *Iterative Audit Convergence in LLM-Managed Multi-Agent Systems:
  A Case Study in Prompt-Engineering Quality Assurance.* arXiv:2605.12280.
  https://arxiv.org/abs/2605.12280 *(single-author case study — directional; HTML render
  unavailable, see N3)*
- [S18] Chen, M., et al. (2021). *Evaluating Large Language Models Trained on Code.*
  arXiv:2107.03374. https://arxiv.org/abs/2107.03374

**Judge reliability (medium volatility)**

- [S19] Panickssery, A., Bowman, S. R., & Feng, S. (2024). *LLM Evaluators Recognize and Favor
  Their Own Generations.* arXiv:2404.13076. https://arxiv.org/abs/2404.13076
- [S20] Sharma, M., Tong, M., Korbak, T., Duvenaud, D., Askell, A., Bowman, S. R., et al.
  (2023). *Towards Understanding Sycophancy in Language Models.* arXiv:2310.13548.
  https://arxiv.org/abs/2310.13548
- [S21] Li, R., Gu, J.-C., Kung, P.-N., Xia, H., Liu, J., Kong, X., Sui, Z., & Peng, N. (2025).
  *LLM-REVal: Can We Trust LLM Reviewers Yet?* arXiv:2510.12367.
  https://arxiv.org/abs/2510.12367

**Convergence detection mechanisms (high volatility)**

- [S11] Shrivastava, S. (2026). *Semantic Early-Stopping for Iterative LLM Agent Loops.*
  arXiv:2606.27009. https://arxiv.org/abs/2606.27009 — setup and quotes from
  https://arxiv.org/html/2606.27009v1 *(single-author preprint — directional)*
- [S22] Parfenova, A., Denzler, A., & Pfeffer, J. (2025). *Emergent Convergence in Multi-Agent
  LLM Annotation.* arXiv:2512.00047. https://arxiv.org/abs/2512.00047
- [S23] Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., & Zhou,
  D. (2022). *Self-Consistency Improves Chain of Thought Reasoning in Language Models.*
  arXiv:2203.11171. https://arxiv.org/abs/2203.11171
- [S24] Tacheny, N. (2025). *Geometric Dynamics of Agentic Loops in Large Language Models.*
  arXiv:2512.10350. https://arxiv.org/abs/2512.10350 *(single-author preprint — directional)*

**Stopping rules and residual risk outside the LLM literature (low volatility)**

- [S10] Böhme, M., Liyanage, D., & Wüstholz, V. (2021). *Estimating Residual Risk in Greybox
  Fuzzing.* ESEC/FSE 2021. https://doi.org/10.1145/3468264.3468570 — abstract quoted from
  https://research.monash.edu/en/publications/estimating-residual-risk-in-greybox-fuzzing
- [S12] Porter, A. A., Siy, H., Mockus, A., & Votta, L. G. (1998). *Understanding the Sources of
  Variation in Software Inspections.* ACM TOSEM 7(1). https://doi.org/10.1145/268411.268421 —
  abstract quoted from https://drum.lib.umd.edu/items/5e99e954-e625-46c1-9a07-d8ec9ac5b107
  *(ACM DL returned 403)*
- [S16] Cousot, P. (2023). *Abstract Interpretation: From 0, 1, To ∞.*
  https://cs.nyu.edu/~pmc309/publications.www/CSV-2023-cousot.pdf *(classical result, but PDF
  text did not extract — the ACC/widening claim rests on search-corroborated summaries of
  [S16] and [S17], not on fetched primary text. **Directional**, per the same rule applied to
  [S25], [S26], [S34].)*
- [S17] Cousot, P., & Cousot, R. (1992). *Comparing the Galois Connection and Widening/Narrowing
  Approaches to Abstract Interpretation.* PLILP'92, LNCS 631, 269-295.
  https://www.di.ens.fr/~cousot/COUSOTpapers/publications.www/CousotCousot-PLILP-92-LNCS-n631-p269--295-1992.pdf
- [S25] Eick, S. G., Loader, C. R., Long, M. D., Votta, L. G., & Vander Wiel, S. (1992).
  *Estimating software fault content before coding.* ICSE '92 — the first application of
  capture-recapture to software inspections. *(cited via [S26]; primary not fetched —
  **unverified** as to exact wording)*
- [S26] Petersson, H., Thelin, T., Runeson, P., & Wohlin, C. (2004). *Capture-recapture in
  software inspections after 10 years research — theory, evaluation and application.* Journal of
  Systems and Software 72(3). https://wohlin.eu/jss04-1.pdf *(PDF text did not extract; the
  model-Mt/Mh and Eick-1992-origin claims are from corroborated search summaries —
  **directional**)*
- [S33] Du, X., Feng, J., Zou, Y., Xu, W., Ma, J., Zhang, W., Liu, S., Peng, X., & Lou, Y.
  (2026). *Reducing False Positives in Static Bug Detection with LLMs: An Empirical Study in
  Industry.* ICSE-SEIP 2026. arXiv:2601.18844. https://arxiv.org/abs/2601.18844
- [S34] Assorted methodological literature on qualitative saturation (Saunders et al.;
  Aguinis et al., *Defining, assessing, and reporting saturation in qualitative research*,
  https://hermanaguinis.com/pdf/LQsaturation.pdf). **Unverified** — used only as a
  corroborating failure-mode analogy in §5.6; primary text not fetched.

**Framework and vendor documentation — first-party (high volatility)**

- [S27] Microsoft AutoGen, *Termination* (AgentChat user guide).
  https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/termination.html
  *(rendered page — quotes kept short and verbatim; the raw notebook path in the repo returned
  404)*
- [S28] OpenAI Agents SDK, *Running agents.*
  https://raw.githubusercontent.com/openai/openai-agents-python/main/docs/running_agents.md
  *(raw markdown)*
- [S29] LangChain / LangGraph, *GRAPH_RECURSION_LIMIT.*
  https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT.md *(raw
  markdown; the default value of 25 is widely reported in issue trackers but is **not** stated
  in the fetched doc — treated as unverified and not used)*
- [S30] Anthropic, *Claude Agent SDK for Python* README.
  https://raw.githubusercontent.com/anthropics/claude-agent-sdk-python/main/README.md *(raw
  markdown; `max_turns` appears as a `ClaudeAgentOptions` field — semantics not documented
  there)*
- [S31] Anthropic, *Building Effective Agents* (engineering blog).
  https://www.anthropic.com/engineering/building-effective-agents *(rendered page — quotes kept
  short and verbatim)*
- [S32] Hou, X., Wang, S., Zhao, Y., & Wang, H. (2026). *When Agents Do Not Stop: Uncovering
  Infinite Agentic Loops in LLM Agents.* arXiv:2607.01641. https://arxiv.org/abs/2607.01641 —
  body quotes in §5.1 from https://arxiv.org/html/2607.01641v1 *(re-fetched and corrected
  after the critic pass; the first draft's §5.1 quotations were not verbatim)*

**Internal evidence (not a citation — recorded for traceability)**

- `docs/development/phases/burn-test-intake-2026-08-02.md` § "Recorded: the plateau correction"
  — PR #233, three productive passes, n=1.
- `scripts/workflows/revision.sh` lines 21-26, 309-325 — the shipped one-loop-back bound and
  its stated justification; and lines 311-315, the PR #224 pass-8 unchanged-tree observation.

*All arXiv metadata (id, authors, dates, abstracts) was verified through the arXiv Atom API
(`export.arxiv.org/api/query?id_list=…`) rather than through rendered abs pages. Body quotes
come from ar5iv or arXiv LaTeX-derived HTML where available. arXiv PDF fetches did not extract
text in this environment and were not used as a quote source — three attempts ([S1], [S6],
[S10]) returned unparsed binary and were re-sourced.*

---

## 7. Test plan — what research cannot settle

Research located the shape of the question and ruled out the extrapolation currently in the
code. It cannot supply the number, because **the experiment that would supply it does not exist
in the literature (N1)**. These are ordered by decision value.

**T1. Extend the n=1. Run the same PR through K sequential fresh-context review passes and
record per-pass new-verified-finding counts.**
*Because:* PR #233's three-productive-passes result and [S15]'s nine-round series are the only
two observations of this shape anywhere, and neither is ours-at-scale.
*Design:* K ≥ 6, ≥ 10 PRs, spanning at least three task shapes (security sweep, refactor,
docs/standards edit — the operator's own note that PR #233 was "security-sweep-shaped" is the
confound to break). Record per pass: findings raised, findings *verified* by a later pass or by
a human, findings retracted, tokens, wall time.
*Reads out:* the per-pass yield curve for our topology — the object neither [S1] nor [S14]
measured. *Fails if:* yield is dominated by task shape rather than pass index, which is what
[S12] predicts; that outcome is itself decisive and would argue for a count.

**T2. Measure per-pass recall against seeded defects on our own artifacts.**
*Because:* P6 is the load-bearing number for every plateau argument, and the only measurement
located ([S8], ~22-27%) used injected errors, one model, and a language confound.
*Design:* seed N known defects of graded severity into real PRs; run single passes; measure
recall and inter-pass overlap. *Reads out:* both the recall figure and — via [S25]-style
capture-recapture — an estimate of *unfound* defects, which is the only thing that can tell a
"clean" pass from a "failed" pass (the §2.3 gap).

**T3. Determine whether an unchanged tree yields an unchanged finding set.**
*Because:* this is the cheapest possible convergence signal (PR #224's pass 8) and §1.3 plus
[S6] predict it is **not** reliable — a stochastic reviewer may find something new on identical
input. *Design:* re-run `review-pr` M ≥ 5 times against a frozen commit; measure finding-set
variance. *Reads out:* whether "trivial fixpoint" is a sound stop or merely a cheap one.
*Directly falsifiable, cheap, and should probably run first.*

**T4. Measure the empty-pass rate.**
*Because:* §5.5's derived argument says a reviewer with a non-zero hallucination rate never
emits an empty pass, which would make a "stop on zero findings" rule a no-op that always falls
through to the backstop. *Design:* on already-merged, reviewed PRs, count how often a fresh
`review-pr` returns zero findings. *Reads out:* whether the convergence predicate can ever
fire in production.

**T5. Cost the detector.**
*Because:* [S11] measured the judge-gated variant at **+129% tokens** — the measurement
outspending the saving is a real and observed outcome, not a hypothetical.
*Design:* for whichever detector class is prototyped, instrument detector cost separately from
loop cost, as [S11] does ("operational tokens (charged to a policy)" vs "evaluation tokens (a
measurement instrument)"). *Reads out:* whether convergence stopping is cheaper than the
counter it replaces at our pass costs.

**T6. Establish whether findings can be typed well enough to diff.**
*Because:* P11 — Classes A and E are unavailable without matchable finding records, and this is
the concrete dependency on the inter-process handoff contract (burn-test intake Item 4).
*Design:* take two passes' outputs on the same PR and attempt automated matching; measure how
often two humans agree that finding X in pass 2 is or is not finding Y from pass 1. [S15]'s
inter-rater reliability (κ = 0.80 category, **0.46 severity**) is the prior: category matching
is tractable, severity matching is not. *Reads out:* whether "did this pass find something new"
is mechanically answerable or is itself an LLM judgement.

**T7. Test the oscillation case deliberately.**
*Because:* [S24]'s oscillatory regime and [S32]'s 68 confirmed non-termination failures are the
mechanisms by which a convergence rule fails open. *Design:* construct a PR where two passes
plausibly disagree (a style/architecture judgement with no ground truth) and observe whether the
loop cycles. *Reads out:* whether the backstop is load-bearing in practice or only in theory.

**Not settleable by any of the above, and worth recording as such:** whether the findings a
converged loop *did not* find are the ones that mattered. Every mechanism in §2.3 measures
discovery rate; none measures residual severity. The only instruments located for "what is
still missing" are statistical estimates from inter-pass overlap ([S25], [S10]), and they give a
distribution, never an assurance.
