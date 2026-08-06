# Decide-Only Disposition: Does Removing the Judge's Authoring Authority Reduce Defects?

```
Topic:          Does a judging stage with NO authoring authority actually reduce defects,
                compared with (a) a reviewer that can also fix what it finds, or (b) no
                separate judge at all?
Feeds:          docs/standards/architecture/problem-statement.md element 2 ("distinct actors
                at distinct layers — one that authors, one that judges with no stake in the
                work, one that dispositions"); validates docs/standards/workflow-scripts.md
                § Composition and the shipped decide-only `review-pr` child recorded in
                docs/standards/architecture/system-overview.md § Composition and
                § Where the seams are (`author ≠ judge`, `decide ≠ act`).
Last validated: 2026-08-06
Revalidate:     high — 6 weeks
Confidence:     DEFINITIVE on every arXiv abstract quoted (all fetched through the arXiv Atom
                API, which returned verbatim text — evidenced by preserved source typos and
                LaTeX macros) and on the GitHub Copilot code-review behaviour (raw markdown
                from the first-party github/docs repo, Liquid template tokens intact).
                DEFINITIVE-but-REDUCED-CONFIDENCE (rendered page and/or summarizing fetch —
                wording not established verbatim) on the four Cognition posts, the Anthropic
                evaluator-optimizer description, the OpenAI Agents SDK guardrail text, the
                three NASA SWEHB pages and the SEC Regulation S-X text; these are marked at
                point of use and quoted only in short spans.
                DIRECTIONAL on every transfer of a code-review or planning-benchmark result to
                this repo's topology, and on all first-party *informal* vendor blog statements
                however senior the speaker (§3 authority-vs-formality rule).
                DERIVED, marked at point of use, on: the three-configuration taxonomy (§1.2),
                the ruling on the Cognition contradiction (§5), the reading of Fagan/IV&V/audit
                as antecedents of decide-only (§4), and the headline verdict (§0).
                SEVEN negative findings with stated search method (§9.1) — N1 is the paper's
                headline result.
Critic:         not-yet-verified — 2026-08-06
```

> **Mixed volatility (§3).** §4 (human-process antecedents: Fagan-style inspection, IV&V,
> audit independence) and §2.1–2.2 (the self-critique corpus, 2022–2024) are
> **low-volatility** — a refresh may skip re-verifying them. §6 (what shipping agent systems
> do) is a **vendor product inventory** and is the fastest-decaying material here; three of
> its four Cognition data points were published inside the last seven months, and the
> product it describes ships new review/autofix behaviour on a monthly cadence. §3 and
> §2.3 (2025–2026 preprints) are **medium** — replication, not withdrawal, is the expected
> change. Per §3 the header takes the highest tier present, which is why a paper whose
> centre of gravity is academic carries a 6-week interval rather than the `medium — 3 months`
> that `topics.md` proposed. The fast-moving material is well under a third of the paper, so
> §3's split-the-paper remedy does not apply.

---

## 0. Headline: the shipped design is UNEVIDENCED at exactly the joint it claims

**Verdict: UNEVIDENCED — not unsupported, and not supported.**

The literature establishes, repeatedly and from several directions, that **an author critiquing
its own work in its own context is the worst available configuration**. It establishes that a
*separate* evaluator beats a same-context self-review. It does **not** establish anything about
the specific seam this repo shipped: whether a separate reviewer that may **also fix** what it
finds performs worse than a separate judge that may **only rule**, with the fix routed back to
the author.

**N1 (§9.1): no controlled comparison of those two configurations was located.** Not in the
LLM-agent literature, not in the automated-code-review literature, and not in the fifty-year
human software-inspection literature, where the "find defects, do not design fixes" rule has
been *doctrine* since Fagan 1976 but appears never to have been isolated as an experimental
variable. The search method is stated in full.

That is the finding, and it is worth having. It says precisely this: **problem-statement
element 2's sharpest testable claim is currently carried by the easier half of the
comparison.** Every located result that appears to support "the layering is what makes the
improvement real" is a result about *context separation* (author-in-its-own-session vs. a fresh
separate reviewer). None is a result about *authority removal*. This repo's own strongest
internal evidence — `workflow-scripts.md § Composition`'s account of a fresh-context pass
catching in minutes what engineer self-review, four in-context review agents and manual
verification all missed — is likewise a context-separation observation, not an
authority-removal one.

Three things soften "unevidenced" without converting it to "supported", and they are why the
recommendation in §11 is *keep the design, retire the research topic*:

1. **The decide-only shape is what the field is converging on when it ships.** SWE-Review's
   reviewer agent "decides whether the PR should be accepted, and provides structured feedback
   for revision" [S12]; OpenAI's Agents SDK output guardrails halt a run and do not rewrite it
   [S30]; GitHub Copilot code review leaves a `Comment` review and never an `Approve` or
   `Request changes`, with the human applying suggestions [S31]; Cognition ships reviewing and
   autofixing as *separate* products wired together [S27][S28]. Convergence is not evidence of
   effect, but it is evidence the shape is not exotic.
2. **Cognition — the source of this pool's live contradiction — has publicly moved to a
   position that endorses precisely this shape** (§5). Its refined principle is that
   multi-agent systems work when "writes stay single-threaded and the additional agents
   contribute intelligence rather than actions" [S26]. A judge that rules and cannot edit is
   the canonical instance of an agent contributing intelligence rather than actions.
3. **The classical antecedents assign the fix to the author by construction** — Fagan-style
   inspection separates the defect-finding phase from a rework phase performed by the author
   [S21]; NASA IV&V is defined by technical, managerial and financial independence from the
   developer [S23]; and US securities regulation treats "auditing his or her own work" as a
   per-se impairment of independence [S24]. But all three are *requirements*, not measured
   effects, and NASA's own peer-review guidance cuts partly the other way by expecting
   participants to help identify solutions [S22].

**What would flip the verdict to "supported" is an experiment, not more reading.** §10
specifies it.

---

## 1. Primer

### 1.1 What is actually being claimed

`problem-statement.md` element 2:

> *"Not one agent critiquing itself, but distinct actors at distinct layers — one that authors,
> one that judges with no stake in the work, one that dispositions — each reading and writing
> artifacts the others can see. The layering is what makes the improvement real rather than an
> agent agreeing with itself."*

`system-overview.md § Where the seams are` names two seams this paper validates: `author ≠
judge` ("the author of a change defends it; no wording fixes that") and `decide ≠ act`
("`review-pr` rules; a human or parent fires"). The shipped artifact is
`children/review-pr.sh`, documented as "decide-only: MERGE | HOLD + a runway".

Those two seams are **different claims**, and conflating them is the failure mode this paper
exists to prevent:

- **`author ≠ judge`** is a claim about **who** evaluates and **what context they carry**. It
  is well evidenced (§2.1, §2.2).
- **`decide ≠ act`** is a claim about **what authority the evaluator holds**. It is the claim
  under test here, and §3 finds no direct evidence either way.

### 1.2 The three configurations (DERIVED — this taxonomy is the paper's own)

*(Derived from the problem statement's element 2 and the shipped composition in
`system-overview.md`, set against the configurations the located literature actually
instantiates. No cited source uses this taxonomy.)*

| # | Configuration | Who evaluates | Who changes the artifact | Canonical instances located |
|---|---|---|---|---|
| **(i)** | **Self-critique** | the author, in its own context | the author | Self-Refine, Reflexion, CRITIC (see `raw/reflection_literature.md`); Stechly [S6]; Valmeekam [S7]; Olausson self-repair [S8] |
| **(ii)** | **Reviewer that may fix** | a separate actor | the same separate actor | CodeAgent's revision-suggesting agents [S10]; Getafix-style detect-and-patch [S20]; any "review agent with write access" |
| **(iii)** | **Decide-only judge** | a separate actor | the **author** or a human, on the judge's verdict | `review-pr`; SWE-Review [S12]; Copilot code review [S31]; OpenAI output guardrails [S30]; Fagan inspection rework [S21]; IV&V [S23] |

A fourth exists and matters for §6: **(0) no separate judge at all** — the artifact ships on
the author's own say-so. This is the baseline Monperrus argues we should return to for human
reviewers [S17].

**The evidence problem in one line.** The corpus is rich on (i) vs {(ii),(iii)} and empty on
(ii) vs (iii).

### 1.3 Sourcing posture (read this before trusting any quotation below)

Per the Research Standard's verbatim rule, a span is presented as a quotation here **only**
where the fetch returned raw text. Two classes exist in this paper and are marked distinctly:

- **Verbatim-capable fetches.** All arXiv abstracts were pulled through the arXiv Atom API
  (`export.arxiv.org/api/query?id_list=…`). That these returned raw text rather than a
  paraphrase is *checkable*: the returned LLMs-as-Judges abstract preserves the source's own
  typo ("we aim aims to provide"), the CodeAgent abstract preserves an unrendered LaTeX macro
  (`\tool{}`), and the SWE-Review abstract preserves `\textbf{…}` markup. The GitHub Copilot
  documentation was fetched from `raw.githubusercontent.com` and returned unexpanded Liquid
  tokens (`{% data variables.product.prodname_copilot %}`). Quotations from these are
  **definitive**.
- **Summarizing fetches.** The Cognition posts, the Anthropic engineering page, the NASA SWEHB
  pages, the eCFR API response and the OpenAI `guardrails.md` fetch all came back partly or
  wholly as prose *about* the page. Their content is reported and short spans are shown, but
  they are marked **reduced confidence — wording not verified verbatim** at point of use, and
  nothing load-bearing rests on their exact phrasing. Where a number was involved, the page was
  re-fetched with a differently-worded prompt and the two results compared (§5 does this for
  the only figures used).

---

## 2. The literature on separating generation from evaluation

*(§2.1 and §2.2 are LOW volatility — a refresh may skip them. §2.3 is MEDIUM.)*

### 2.1 Configuration (i) fails, and the field's own strongest results say so

The pool already owns the core of this — `raw/convergence_stopping.md` §§2.1.3–2.1.5 holds
Huang et al.'s "LLMs Cannot Self-Correct Reasoning Yet", the Kamoi TACL survey's scoping, and
the 64.5% self-correction blind-spot rate, and `raw/reflection_literature.md` holds the
Reflexion / Self-Refine / CRITIC / Self-RAG corpus and its four named gaps. **Cited, not
re-derived.** What this paper adds are three results that isolate the *verification* half of
self-critique specifically:

**2.1.1 The critique is not the active ingredient — the model's verification ability is, and
it is absent.** Stechly, Marquez & Kambhampati, on graph colouring, verbatim from the abstract:

> "(ii) they are no better at verifying a solution--and thus are not effective in iterative
> modes with LLMs critiquing LLM-generated solutions (iii) the correctness and content of the
> criticisms--whether by LLMs or external solvers--seems largely irrelevant to the performance
> of iterative prompting" [S6]

and, on the mechanism behind apparent gains:

> "We show that the observed increase in effectiveness is largely due to the correct solution
> being fortuitously present in the top-k completions of the prompt (and being recognized as
> such by an external verifier)." [S6]

*Confidence: definitive on the abstract (arXiv API). **Directional** as a result for this
repo — graph colouring is a formal-verifier domain, and a PR review is not.*

**2.1.2 Self-critique made planning worse, and the LLM verifier produced false positives.**
Valmeekam, Marquez & Kambhampati, verbatim:

> "our findings reveal that self-critiquing appears to diminish plan generation performance,
> especially when compared to systems with external, sound verifiers and the LLM verifiers in
> that system produce a notable number of false positives, compromising the system's
> reliability" [S7]

and:

> "the nature of feedback, whether binary or detailed, showed minimal impact on plan
> generation" [S7]

*Confidence: definitive on the abstract. **The second span is directly relevant to a
decide-only design and cuts against it**: if binary versus detailed feedback made minimal
difference in that setting, the "runway" a HOLD carries may be buying less than the design
assumes. Directional on transfer — planning, not code review.*

**2.1.3 Self-repair is bottlenecked by feedback quality, not by repair ability.** Olausson et
al., verbatim:

> "We find that when the cost of carrying out repair is taken into account, performance gains
> are often modest, vary a lot between subsets of the data, and are sometimes not present at
> all." [S8]

> "We hypothesize that this is because self-repair is bottlenecked by the model's ability to
> provide feedback on its own code; using a stronger model to artificially boost the quality of
> the feedback, we observe substantially larger performance gains." [S8]

> "a small-scale study in which we provide GPT-4 with feedback from human participants suggests
> that even for the strongest models, self-repair still lags far behind what can be achieved
> with human-level debugging" [S8]

**This is the single most decision-relevant result in §2 (DERIVED consequence).** Olausson et
al. decompose the loop into *feedback production* and *repair execution*, hold the repairer
fixed, and vary only the feedback source. The gain tracks the feedback source. *Derived from
[S8]: if the marginal value of the loop sits in feedback quality rather than in who executes
the patch, then moving the patch back to the author (configuration iii) costs little, and the
design question becomes "is the judge good?" rather than "may the judge write?".* Olausson et
al. make no claim about authoring authority; the transfer is this paper's.

### 2.2 A separate evaluator beats a same-context one — and the gap has a name

**2.2.1 The generator–discriminator–critique framing.** Saunders et al. (OpenAI, 2022)
introduced the vocabulary this whole question needs, verbatim:

> "Finally, we motivate and introduce a framework for comparing critiquing ability to
> generation and discrimination ability." [S5]

> "Our measurements suggest that even large models may still have relevant knowledge they
> cannot or do not articulate as critiques." [S5]

> "critiques written by our models help humans find flaws in summaries that they would have
> otherwise missed" [S5]

*Confidence: definitive on the abstract. Note the shape of the deployment they describe: the
model writes critiques, **humans find and act on the flaws** — configuration (iii) with a human
author.*

**2.2.2 The pool's on-domain results.** `raw/convergence_stopping.md` §2.2.1 (Cross-Context
Review: fresh-session review F1 28.6% vs same-session self-review 24.6%, p=0.008, d=0.52, with
review-twice-in-session the worst of four conditions) and §2.2.5 (CriticGPT; self-preference
bias; sycophancy; LLM-REVal score inflation) are **cited, not re-derived**. Both are
directional per that paper's own marking. Note what they measure: **context separation**, with
authoring authority held constant.

**2.2.3 The repo's own internal evidence is also a context-separation observation.**
`workflow-scripts.md § Composition` states the rationale in first-party form: *"A run that both
authors work and rules on the review findings about it will defend its own work. This is not a
prompt-quality problem and cannot be fixed by wording: engineer self-review, four in-context
review agents under an explicit disposition taxonomy, and manual verification all failed to
catch defects that a fresh-context pass then found in minutes."* **This is evidence for
`author ≠ judge`. It is not evidence for `decide ≠ act`** — the fresh-context pass that found
the defects was not tested with and without write authority. *(Derived, from the standard's own
text.)*

### 2.3 The judge is itself unreliable, and the failures are structured

**2.3.1 The canonical bias taxonomy.** Zheng et al., verbatim:

> "We examine the usage and limitations of LLM-as-a-judge, including position, verbosity, and
> self-enhancement biases, as well as limited reasoning ability, and propose solutions to
> mitigate some of them." [S1]

> "Our results reveal that strong LLM judges like GPT-4 can match both controlled and
> crowdsourced human preferences well, achieving over 80% agreement, the same level of
> agreement between humans." [S1]

*Confidence: definitive on the abstract. Both spans matter: the biases are real **and** the
agreement with humans is high. A paper citing only the first half is cherry-picking.*

**2.3.2 Self-preference is causal, not coincidental.** Panickssery, Bowman & Feng, verbatim:

> "One such bias is self-preference, where an LLM evaluator scores its own outputs higher than
> others' while human annotators consider them of equal quality." [S2]

> "By fine-tuning LLMs, we discover a linear correlation between self-recognition capability
> and the strength of self-preference bias; using controlled experiments, we show that the
> causal explanation resists straightforward confounders." [S2]

*Confidence: definitive on the abstract. **This is the strongest published mechanism for
`author ≠ judge`** — and note it is a *who*-claim, not an *authority*-claim.*

**2.3.3 A production judge caught roughly one defect in five.** Zhang, Wang & Lei, verbatim:

> "Across three batches the judge surfaces well under a quarter of human-confirmed systematic
> problems -- 2 of 9 patterns (22%) in one batch, and its operational gate flagged zero of 100
> rounds in a batch where humans confirmed 23 distinct defects and 7 new cross-cutting
> patterns." [S4]

> "The failure is routing, not perception: 113 of 114 rounds whose raw judge note describes a
> confirm-gate or cart-state defect are scored "brand voice", and none reach an operational
> failure -- the gate is wired to hangs and hard assertions, not the rubric" [S4]

> "For production multi-turn agents, automated judging is a regression floor, not a substitute
> for human review." [S4]

**DERIVED, and it is a warning aimed squarely at this repo's design.** [S4]'s diagnosis is that
the judge *noticed* the defects and the **verdict vocabulary had no slot for them**, so they
never reached the gate. `review-pr`'s vocabulary is `MERGE | HOLD` plus a runway — a
closed vocabulary, per `workflow-scripts.md § Routing contracts`. *Derived from [S4] plus that
standard: a decide-only judge's value is bounded above by the expressiveness of the verdict
vocabulary it is allowed to emit, and a judge that cannot fix ALSO cannot route a finding the
vocabulary has no category for.* [S4] studies a transaction agent, not a code reviewer; the
transfer is this paper's.

**2.3.4 Ten independent reviewers can be unanimously wrong.** Agarwal, verbatim:

> "The most instructive failure: ten dedicated reviewers unanimously endorsed a non-existent
> Bleichenbacher padding oracle in OpenSSL's CMS module; it was killed only by a single
> empirical test, motivating the mandatory empirical gate." [S16]

> "No vulnerability was discovered autonomously; the contribution is external structure that
> filters LLM agents' persistent false positives." [S16]

*Confidence: definitive on the abstract. **This is the sharpest available counter to
"add more judges"** — and note the remedy the author reached for was not another judge but an
**empirical gate**, i.e. an actor that acts on the world rather than one that rules on text.*

**2.3.5 Judge surveys.** Li et al.'s survey covers "Functionality, Methodology, Applications,
Meta-evaluation, and Limitations" of the LLMs-as-judges paradigm [S3]. *Confidence: definitive
on the abstract; used here only to establish that the paradigm and its limitation literature
are consolidated, not for any specific claim.*

---

## 3. The sharp question: does removing the judge's AUTHORING authority change the outcome?

*(MEDIUM volatility — most sources are 2025–2026 preprints.)*

### 3.1 N1 — the headline negative finding

**No study was located that holds the evaluator, the artifact and the task constant and varies
only whether the evaluator may edit the artifact.** Full search method in §9.1 N1.

This is not a claim that no such study exists. It is a claim that a targeted sweep across the
arXiv API, four web searches with deliberately different phrasings, forward-reading from the
five closest located papers, and inspection of a purpose-built code-review-agent benchmark's
task definition, did not surface one — and that the closest papers do not contain the arm.
Notably, the c-CRAB benchmark [S15] evaluates whether "a code review agent produces a review"
and scores the *review*; it does not have an arm in which the agent applies its own finding.

### 3.2 Systems that instantiate (iii), and what they measured instead

**3.2.1 SWE-Review — the closest thing to an evaluation of the (iii) shape.** Verbatim:

> "Given an issue and an AI-generated PR, a reviewer agent explores the repository, decides
> whether the PR should be accepted, and provides structured feedback for revision." [S12]

> "Experiments show that agentic review continuously improves PRs through a generate-review-
> revise loop, outperforms single-turn fixed-context review in both decision accuracy and
> resolve rate after revision, transfers beyond review to improve issue-resolution models, and
> enables effective and efficient test-time scaling." [S12]

**What it establishes and what it does not.** *Establishes (definitive on the abstract's
claims):* a decide-and-feed-back reviewer, with revision performed elsewhere, measurably
improves PRs, and a *repository-exploring* reviewer beats a fixed-context one on both decision
accuracy and post-revision resolve rate. *Does not establish:* anything about (ii) — the
comparison arm is single-turn fixed-context review, not a reviewer with write access. **The
whole framework is configuration (iii); nothing in it is configuration (ii).**

*(DERIVED, and it cuts against a naive reading of this repo's `author ≠ judge` seam: [S12]'s
winning arm is the reviewer that **explores the repository**, i.e. the one with MORE context,
not less. `case_against.md` D7 raises the same tension from a different source. §8.4 states it
fully.)*

**3.2.2 Adversarial kill-gates.** Refute-or-Promote is a pure decide-only pipeline: adversarial
agents "attempt to disprove candidates at each promotion gate", with "cold-start reviewers …
intended to reduce anchoring cascades" and a "Cross-Model Critic (CMC)" [S16]. Verbatim on
yield:

> "Over a 31-day campaign across 7 targets (security libraries, the ISO C++ standard, major
> compilers), the pipeline killed roughly 79% of 171 candidates before advancing to disclosure
> (retrospective aggregate); on a consolidated-protocol subset (lcms2, wolfSSL; n=30), the
> prospective kill rate was 83%." [S16]

Outcomes were "evaluated by external acceptance, not benchmarks" [S16] — 4 CVEs, an accepted
C++ working-paper item, merged compiler and security fixes. *Confidence: definitive on the
abstract; single-author campaign report, no control arm, so **directional** as a result. It has
no (ii) arm either.*

**3.2.3 Courtroom topologies.** VulTrial uses "four role-specific agents, which are security
researcher, code author, moderator, and review board" and "almost doubles the efficacy of prior
best-performing baselines" [S9]. The review board rules; it does not patch. *Definitive on the
abstract; directional as a result (GPT-4o, vulnerability detection). Again: no (ii) arm.*

**3.2.4 Evaluator/judge frameworks generally.** Agent-as-a-Judge "dramatically outperforms
LLM-as-a-Judge and is as reliable as our human evaluation baseline" on DevAI [S11] — an
evaluation instrument with no authoring role by construction. *Definitive on the abstract.*

### 3.3 Systems that instantiate (ii)

**3.3.1 Detect-and-patch as an industrial norm.** Getafix's premise, verbatim:

> "Static analyzers help find bugs early by warning about recurring bug categories. While
> fixing these bugs still remains a mostly manual task in practice, we observe that fixes for a
> specific bug category often are repetitive." [S20]

> "The approach predicts exactly the human-written fix as the top-most suggestion between 12%
> and 91% of the time, depending on the bug category." [S20]

*Confidence: definitive on the abstract. This is the best available statement of the case FOR
the finder producing the fix: at Facebook scale, findings that arrive without fixes stay
manual. Note carefully that Getafix **suggests**; the abstract does not claim autonomous
application, so even this is closer to (iii) than to a true (ii).*

**3.3.2 Multi-agent review that also revises.** CodeAgent's task list includes "suggest code
revision", and it "incorporates a supervisory agent, QA-Checker, to ensure that all the agents'
contributions address the initial review question" [S10]. *Definitive on the abstract. The
QA-Checker is itself a decide-only supervisory layer over the reviewing agents — a
configuration-(iii) actor inside a configuration-(ii) system.*

### 3.4 What indirectly bears on (ii) vs (iii)

Three located results bear on it obliquely. None is a substitute for N1's missing experiment,
and each is marked for what it actually measured.

**3.4.1 Reviewer-authored fixes are adopted less and inflate the artifact.** Zhong, Noei, Zou &
Adams, on 278,790 code-review conversations across 300 GitHub projects, verbatim:

> "Moreover, code suggestions made by AI agents are adopted into the codebase at a
> significantly lower rate than suggestions proposed by human reviewers. Over half of unadopted
> suggestions from AI agents are either incorrect or addressed through alternative fixes by
> developers. When adopted, suggestions provided by AI agents produce significantly larger
> increases in code complexity and code size than suggestions provided by human reviewers."
> [S13]

*Confidence: definitive on the abstract (arXiv API). **Specific adoption percentages circulated
in a search-result summary and are deliberately NOT cited** — the abstract states the direction,
not the numbers, and a search summary is never a source (§9.1 N6).*

**DERIVED, and this is the closest thing to (ii)-vs-(iii) evidence located.** *Derived from
[S13]: if an AI reviewer's proposed fixes are, more than half the time when unadopted, either
wrong or superseded by the developer's own alternative, then the marginal value of letting the
reviewer produce the fix is low and its marginal cost (complexity and size inflation on the
ones that are adopted) is measurable.* Two limits, stated: [S13] measures **suggestions on a
human-owned PR**, not a reviewer with commit authority, and the adoption decision is a human's
— so it measures the *acceptability* of reviewer-authored fixes, not the *defect-detection*
effect of granting write authority. It cannot settle N1.

**3.4.2 The feedback/repair decomposition.** [S8] §2.1.3 above: the gain tracks feedback
quality, not repairer identity.

**3.4.3 Human inspection assigns rework to the author by construction.** §4.1.

### 3.5 The verdict on the shipped design, stated precisely

- **`author ≠ judge` — SUPPORTED.** [S2] gives the causal mechanism (self-preference tracks
  self-recognition); [S6][S7] show same-actor critique failing or backfiring; the pool's
  Cross-Context Review result is on-domain; the repo's own § Composition narrative is a
  consistent n=1. Confidence: **directional-to-definitive**, definitive on the mechanism papers
  and directional on the transfer to this topology.
- **`decide ≠ act` — UNEVIDENCED.** N1. No located source compares it against the alternative.
  The shape is widely shipped (§6) and matches three human-process antecedents (§4), and that
  is all that can honestly be said.
- **The stronger reading of element 2 — "the layering is what makes the improvement real" — is
  supported only in its `author ≠ judge` half.** A consumer that carries element 2 forward as
  validated in full has mis-carried it.

---

## 4. Human-process antecedents, treated as evidence

*(LOW VOLATILITY — a refresh may skip this section. All four sub-sections rest on standards and
regulations that change on multi-year cycles.)*

### 4.1 Fagan-style inspection: detection and correction are separate phases

NASA's Software Engineering Handbook documents the inspection phase structure. Per the fetched
page, the inspection-meeting phase's purpose is to *find, classify and record defects*; a
separate **rework** phase exists whose purpose is to *remove known defects*; the **author** is
the role that "Performs rework, correcting defects identified"; and exit from the process
requires resolution of all major defects found during the meeting **by the author** [S21]. Roles
are separated: moderator (oversees), reader (presents the product), inspectors (review),
recorder [S21][S22].

*Confidence: **reduced confidence — the SWEHB pages are rendered and the fetch summarized them**,
so the exact wording above is NOT established verbatim and is reported rather than quoted. The
substance — that inspection has a distinct rework phase and that the author performs it — was
returned consistently by two separate page fetches.*

**DERIVED.** *From [S21]'s phase structure plus §1.2's taxonomy: the fifty-year-old default
process for software defect detection is configuration (iii). The evaluator identifies and
records; the author changes the artifact.* Fagan (1976) is the origin — [S17] itself dates the
practice: "Code review has been the primary quality gate in software development since Fagan
formalised code inspection in 1976" [S17].

**And the counter-evidence, from the same body of guidance.** NASA's SWE-087 guidance, per the
fetched page, describes inspections as producing "specific suggestions for product improvements"
and describes methodically evaluating each defect "to identify solutions and track the
incorporation of these solutions" [S22]. **NASA's own peer-review guidance therefore expects
participants to help produce solutions** — which is a lean toward (ii), inside the same standard
whose phase model is (iii). *(Reduced confidence on wording, as above. This is real tension, it
is reported rather than resolved, and it is the reason §8.2 exists.)*

**What the human literature does NOT give us (N2).** No experiment isolating the "find defects,
do not design solutions" rule as a variable was located. The nearest well-powered study is
Porter, Siy, Mockus & Votta (TOSEM 1998), held in `raw/convergence_stopping.md` §5.4, which
varied team size and the number and sequencing of sessions and found these "did not
significantly influence the defect detection reate [sic]", with reviewer, author and code unit
accounting for "much more variation in defect detection than was process structure". **If that
transfers, the (ii)-vs-(iii) difference this paper was commissioned to find may be a
second-order term.** *(Cited to the sibling paper by source name per pool convention; not
re-fetched here.)*

### 4.2 IV&V: independence is a requirement, and its parameters are named

NASA's handbook defines IV&V as "an objective examination of safety and mission-critical
software processes and products", states that "The key parameters for independence are technical
independence, managerial independence, and financial independence", and records that it is NASA
policy to use the NASA IV&V Facility "as the sole provider of IV&V services" for software
selected for IV&V [S23]. The page also states that IV&V across the lifecycle "increases the
likelihood of uncovering high-risk errors early in the life cycle" [S23].

*Confidence: **reduced confidence — rendered page, summarizing fetch.** The three independence
parameters are the load-bearing content and were returned as an explicit enumeration.*

**Two things this establishes and one it does not.** It establishes that a domain where being
wrong destroys spacecraft has (a) codified evaluator independence as a *requirement*, and (b)
specified independence along three axes, of which **managerial independence is the closest
analogue to `decide ≠ act`** — the verifier does not report to, and cannot be directed by, the
party whose work is verified. It does **not** establish an effect size: the fetched page makes
no comparison between IV&V and developer-performed V&V, and the ROI literature this paper went
looking for did not resolve to a fetchable primary (§9.1 N3).

### 4.3 Audit: "auditing his or her own work" is a per-se impairment

US securities regulation, 17 CFR 210.2-01 (Regulation S-X Rule 2-01), enumerates the conditions
under which the SEC examines an accountant's independence, including a relationship that
"places the accountant in the position of auditing his or her own work" [S24]. The general
standard in paragraph (b) turns on whether the accountant is "capable of exercising objective
and impartial judgment" [S24].

*Confidence: **reduced confidence** — the eCFR versioner API was used (a structured source), but
the fetch returned prose about the section alongside the quoted spans, so verbatim status is not
established. The short phrase "auditing his or her own work" is the only span anything rests on.*

**DERIVED.** *From [S24] plus §1.2: the `author ≠ judge` seam is codified in binding federal
regulation for financial reporting, and the mechanism named is exactly the one [S2] measured in
LLMs — an evaluator's judgement of its own work is not trusted, regardless of the evaluator's
competence or good faith.* **The limit is important and is stated rather than buried: this is a
*normative* rule about appearance and incentive, not a measured defect-detection result.** No
citation here should be read as evidence that separation *finds more defects*; it is evidence
that a field with strong incentives to get this right chose separation as a requirement.

### 4.4 What the antecedents collectively support

*(DERIVED, from [S21][S22][S23][S24].)* Three independent, high-stakes domains — software
inspection, aerospace assurance, financial audit — converged on evaluator independence, and two
of the three additionally separate the *judgement* from the *change* (inspection routes rework
to the author; audit issues an opinion and is prohibited from keeping the books). **That is
strong support for the shape and no support at all for the magnitude.** None of the three ran
the arm where the evaluator was allowed to fix.

---

## 5. The live contradiction: Cognition vs. `convergence_stopping.md` — ruled

`case_against.md` §2.3.4 and D7 surface a sourced tension:

- **Cognition's position** (2025-06-12, "Don't Build Multi-Agents"): two principles — "Share
  context, and share full agent traces, not just individual messages" and "Actions carry
  implicit decisions, and conflicting decisions carry bad results" — with parallel subagents
  producing work that "ends up being inconsistent with each other" because their actions "were
  based on conflicting assumptions not prescribed upfront" [S25]. `case_against.md` extrapolates
  from this that a judge with no stake also has none of the author's context, and that "the seam
  that removes bias also removes information", marking the extrapolation **derived** and ranking
  it last (D7) for exactly that reason.
- **`convergence_stopping.md` §2.2.1** reports the opposite on-domain: removing production
  history **improved** review F1 (fresh-context 28.6% vs same-session self-review 24.6%,
  p=0.008, d=0.52), with same-session repetition the worst of four conditions.

### 5.1 The ruling: it is a SCOPE difference, and the source has since closed it

**First, on the original post's own terms.** A fresh fetch of [S25] with a targeted prompt
returned an explicit negative: **the post does not distinguish agents that take actions from
agents that only read or critique.** The distinction is absent from the text. So the
extrapolation in `case_against.md` §2.3.4 is not contradicted by [S25] — it is *unsupported* by
it, which is what that paper already said. The two principles are about **concurrent writers**;
the Flappy Bird example the post uses is two subagents producing incompatible *artifacts*
[S25]. A sequential reader that emits a verdict produces no artifact to conflict with.

**Second, and this closes `case_against.md` §5.4's UNVERIFIED item.** Cognition published a
follow-up, "Multi-Agents: What's Actually Working", dated **04.22.26** — established by
enumerating the posts on `cognition.com/blog` and reading the listing, not by a search summary.
Its refined principle, as returned by the fetch:

> "multi-agent systems work best today when writes stay single-threaded and the additional
> agents contribute intelligence rather than actions" [S26]

and:

> "one writer, augmented by other agents contributing intelligence around it" [S26]

The post names a **Code-Review-Loop** among the patterns that work, and reports:

> "Devin Review catches an average of 2 bugs per PR, of which roughly 58% are severe (logic
> errors, missing edge cases, security vulnerabilities)." [S26]

*Confidence: **reduced confidence — rendered page, summarizing fetch.** The numeric sentence was
obtained by a **second, differently-worded fetch** that asked the page to reproduce every
sentence containing a numeral; the two fetches agreed on the content. That same enumeration also
returned one item that is plainly a fetch artifact rather than page prose (a description of an
image's pixel dimensions), which is stated here as direct evidence that this fetch layer
synthesizes — and is why nothing in this paper rests on Cognition's exact wording.*

### 5.2 What follows (DERIVED)

*Derived from [S25], [S26] and `convergence_stopping.md` §2.2.1:*

1. **The contradiction is a scope difference, not a genuine disagreement.** Cognition's evidence
   is about concurrently *acting* agents; `convergence_stopping.md`'s is about a sequentially
   *reading and ruling* agent. Both can be true simultaneously, and the refined Cognition
   principle says so explicitly by dividing agents into those that contribute actions and those
   that contribute intelligence.
2. **The direction of the update favours this repo's shipped design.** "Additional agents
   contribute intelligence rather than actions" [S26] is a first-party practitioner statement of
   configuration (iii). Under §3's authority-vs-formality rule this is a **blog post, therefore
   directional at most**, however senior the speaker and however large the deployment behind it.
3. **It does not resolve N1.** Cognition reports that its code-review loop works; it reports no
   comparison against a review agent permitted to write. The 2-bugs-per-PR figure is a yield,
   not a contrast.
4. **`case_against.md` D7 should be down-weighted, not withdrawn.** Its underlying worry — a
   judge with no author context may miss things — survives, and is independently raised by
   [S12], whose winning arm is the *repository-exploring* reviewer. See §8.4. The specific
   Cognition-based support for D7 does not survive [S26].

**Recommended dependent trace (for the synthesis, not written by this run):**
`case_against.md` §2.3.4, §5.4 and D7 all carry the unverified-softening caveat; `topics.md`'s
entry for this paper cites the contradiction as open. All three are downstream of this section.

---

## 6. Comparative landscape: what shipping agent systems actually do

*(HIGH VOLATILITY — this is the section that decays. Everything here is a product-behaviour
claim about a system under active development.)*

| System | Separate judge? | May the judge change the artifact? | Config | Published effect? | Source |
|---|---|---|---|---|---|
| **this repo — `review-pr`** | yes, fresh context | documented as decide-only (`MERGE \| HOLD` + runway); a human or parent fires | (iii) | no | `system-overview.md`, `workflow-scripts.md § Composition` |
| **Cognition / Devin Review** | yes | flags for humans — "You can copy/paste or dismiss the AI flags" [S28]; a **separate** autofix run applies them: "Devin can now be configured to **autofix** incoming review comments from Devin Review and other review bots" [S27] | (iii), with an automated author | yield only: 2 bugs/PR, ~58% severe [S26] | [S26][S27][S28] |
| **GitHub Copilot code review** | yes | no — "always leaves a 'Comment' review, not an 'Approve' review or a 'Request changes' review"; suggestions are applied by the developer, and in VS Code "Any changes you apply will not be automatically committed" | (iii), advisory (no verdict at all) | none located | [S31] |
| **OpenAI Agents SDK guardrails** | yes, out-of-band | agent-level **output** guardrails halt and do not rewrite; **tool** guardrails may replace a tool output | (iii) at the agent boundary | none located | [S30] |
| **Anthropic — evaluator-optimizer** | yes | no — "one LLM call generates a response while another provides evaluation and feedback in a loop" | (iii) | none published | [S29] |
| **SWE-Review (research)** | yes | no — decides acceptance, emits structured feedback for a revision step | (iii) | yes, vs single-turn fixed-context review | [S12] |
| **Refute-or-Promote (research)** | yes, cross-model | no — adversarial kill/promote gates only | (iii) | yes, external-acceptance outcomes | [S16] |
| **VulTrial (research)** | yes | no — review board rules | (iii) | yes, ~2x prior baselines | [S9] |
| **CodeAgent (research)** | yes, plus a QA-Checker over the reviewers | yes — "suggest code revision" is one of its tasks | (ii) with an (iii) supervisor | yes, SOTA claim | [S10] |
| **bernstein** | yes — janitor, gate pipeline, cross-model verifier | no for the verifier; disposition is retry/reroute/escalate and a fix **task** | (iii) | none published | `raw/bernstein_capability_mining.md` §2 E2 |
| **kodo** | yes — "Independent architect + tester agents review work before accepting" with rejection authority; work routes back to workers | no | (iii) | none published | `raw/combination_prior_art.md` §3.1 |
| **paperclip** (75,535 stars) | judging is **human governance** — approval workflows, sign-off | n/a | human (iii) | not documented | `raw/combination_prior_art.md` §3.1, `raw/paperclip_assessment.md` |
| **tutti** | yes — a `type = "review"` step separates `agent` from `reviewer` | not documented | (iii), thin | none published | `raw/combination_prior_art.md` §3.1 |
| **Claude Code agent teams** | reviewer roles exist, but "The lead makes approval decisions autonomously" | n/a | model-directed | none published | `raw/combination_prior_art.md` §3.3 |

**Three observations, all DERIVED from the table.**

1. **Configuration (iii) is the overwhelming default among shipping systems, and nobody
   published why.** Eleven of the thirteen rows are (iii) or human-(iii). Not one of them
   publishes a comparison against (ii). *(Derived from the enumerated rows; the "nobody
   published why" half is N1 restated at product level.)*
2. **The one clear (ii) instance puts an (iii) supervisor on top of it.** CodeAgent's QA-Checker
   [S10] is a decide-only actor governing agents that may revise — which is the same seam one
   layer up, and is structurally what `review-pr` is to `build-draft`/`build-refine`.
3. **Cognition ships the two halves as separate products and wires them together** [S27][S28].
   That is the single most direct product-level endorsement of (iii) located, and it is
   *directional* — a vendor blog, per §3.

**Rationale worth recording, and correctly graded.** Cognition's autofix post states the
author≠judge case in plain terms: "Why couldn't the code just be correct the first time? Even
the best engineers might not catch everything on their first pass - you're focused on solving
the problem, not stress-testing the solution. A review agent spends dedicated reasoning on the
diff after it's written, and can go deep into specific issues not obvious just from the original
plan." [S27] *Confidence: **directional** — first-party but informal (a product blog post),
reduced-confidence on wording (summarizing fetch). It is a rationale, not a measurement.*

---

## 7. What this provides — enumerated, citable properties

Each with its source and confidence. A plan may rely on these; it may not rely on anything
stronger.

**P1. Same-actor self-critique is the worst configuration, and the mechanism is documented.**
Self-critique diminished planning performance and produced false positives [S7]; models were "no
better at verifying a solution" than solving in the graph-colouring study [S6]; the pool holds
the reasoning-benchmark and blind-spot results. *(definitive on the abstracts; directional on
transfer to code review.)*

**P2. An evaluator's preference for its own output is causal, not incidental.** Self-preference
correlates linearly with self-recognition ability under fine-tuning, with confounders controlled
[S2]. *(definitive on the abstract.)* **This is the load-bearing citation for `author ≠ judge`.**

**P3. The marginal value of a review loop tracks FEEDBACK quality, not who executes the fix.**
Holding the repairer fixed and improving the feedback source produced "substantially larger
performance gains" [S8]. *(definitive on the abstract; **derived** on the consequence for
authoring authority.)*

**P4. A decide-and-feed-back reviewer measurably improves PRs, and a repository-exploring
reviewer beats a fixed-context one.** [S12]. *(definitive on the abstract's claims;
directional as a result — one framework, one benchmark.)*

**P5. Configuration (iii) is what shipping systems ship.** Eleven of thirteen enumerated
systems (§6). *(derived from the enumeration; each row individually sourced.)*

**P6. Three high-stakes human domains codify evaluator independence, and two also separate
judgement from change.** Inspection rework is the author's [S21]; IV&V independence has three
named parameters [S23]; "auditing his or her own work" is a per-se impairment [S24].
*(reduced-confidence on wording; **derived** on the mapping to configurations.)*

**P7. Cognition's refined public position endorses read-only augmenting agents.** "writes stay
single-threaded and the additional agents contribute intelligence rather than actions" [S26].
*(directional — informal first-party; reduced confidence on wording.)*

**P8. A judge's practical yield can be bounded by its verdict vocabulary rather than by its
perception.** 113 of 114 rounds whose judge note described the defect were scored under a
category that never reached the gate [S4]. *(definitive on the abstract; **derived** on the
transfer to `MERGE | HOLD`.)*

**P9. Reviewer-authored fixes are adopted less than human-authored ones and inflate complexity
and size when adopted.** [S13]. *(definitive on the abstract; **derived** on the reading as
(ii)-vs-(iii) evidence; it measures suggestion acceptability, not detection.)*

**P10. Unanimity among many independent judges is not evidence of correctness.** Ten reviewers
unanimously endorsed a non-existent vulnerability; an empirical test killed it [S16].
*(definitive on the abstract.)*

**P11. NEGATIVE — no controlled (ii)-vs-(iii) comparison exists in the located literature.**
N1, method in §9.1. *(definitive as a negative finding about this sweep.)*

**P12. NEGATIVE — the "find defects, don't design fixes" inspection rule has not been isolated
experimentally.** N2. And the closest well-powered inspection study — Porter, Siy, Mockus &
Votta (TOSEM 1998), held in `convergence_stopping.md` §5.4 — found process structure was not the
lever. *(definitive as a negative finding about this sweep; the Porter result is cited to the
sibling paper by source name, never by an `[Sn]` number, because those collide with this paper's
own numbering.)*

**P13. NEGATIVE — whether `review-pr`'s decide-only property is enforced structurally or by
prompt instruction was NOT verified in this run.** N7. *(definitive as a statement about this
run's access; see §9.1 for method.)* **This matters: a prompt-level constraint and a
tool-permission-level constraint are different claims, and only the second is a seam.**

---

## 8. Honest boundary — the case against decide-only

This section is written against the paper's own feed. Four of the seven items are strong enough
to change a design decision.

### 8.1 The round-trip cost is real and nobody has priced it

A HOLD that must be re-dispatched costs a full extra child dispatch, a full extra context, and
the wall-clock of a second run — to fix, in the limit, a one-character typo the judge could have
corrected in a token. `revision.sh`'s one-loop-back bound (documented in
`convergence_stopping.md`) exists precisely because that loop is expensive. **No published
measurement of this trade-off was located (N4).** The honest position is that the cost side of
the decide-only decision is entirely unquantified, in this repo and in the literature, and that
a design defended on an unmeasured benefit against an unmeasured cost is defended on priors.

### 8.2 A standards body that thought about this asks reviewers to propose solutions

NASA's own peer-review guidance expects participants to identify solutions and to track their
incorporation [S22], inside the same handbook whose phase model assigns rework to the author
[S21]. *(Reduced confidence on wording.)* **The inspection tradition is not as cleanly
decide-only as the "find, don't fix" folk rule suggests** — the separation is of *phases*, not
of *permission to think about the fix*. Applied here: a decide-only judge that emits a runway is
already doing what NASA asks; a decide-only judge forbidden from proposing a remedy would be
doing less than the human antecedent does.

### 8.3 The whole review layer may be the wrong gate

Monperrus argues the strong form, verbatim:

> "We argue that coding agents have crossed a threshold of capability at which traditional human
> code review is no longer a necessary component of a software quality pipeline. Our argument
> rests on two claims: every stated goal of code review can be served by agents at lower cost
> and higher throughput; the naive integration in which agents write code and humans remain the
> mandatory reviewers is a dead end because it neither provides meaningful assurance nor scales
> with AI-assisted throughput." [S17]

*Confidence: definitive on the abstract (arXiv API). It is a **position paper**, single-author,
with no measurement — directional at most as a result, and it argues against **human** review
rather than against a decide-only agent judge. But its second claim lands on this repo's actual
operating model, in which a human rules on the disposition.*

### 8.4 Separation removes information, and the best-performing reviewer in the corpus had MORE context

[S12]'s winning arm is a reviewer that "explores the repository" and beats "single-turn
fixed-context review" on both decision accuracy and post-revision resolve rate. `case_against.md`
D7 raises the same worry from Cognition's context-sharing principle. **DERIVED:** *the seam that
removes the author's bias also removes the author's context, and [S12] is a located result in
which more reviewer context won.* Note this is an argument about **context**, not about
**authority** — a decide-only judge can be given full repository access without being given
write access, and `review-pr` per `workflow-scripts.md § Composition` already receives the
original task precisely so it can ask "did this deliver what was asked?". The two are separable,
and conflating them would be a design error.

### 8.5 The judge may simply be too weak for the seam to matter

If the judge catches "well under a quarter" of real defects [S4], if code-review agents together
solve "only around 40% of the c-CRAB tasks" [S15], and if CRA-only PRs "achieve a 45.20% merge
rate, 23.17 percentage points lower than human-only PRs (68.37%)" with "60.2% of closed CRA-only
PRs" in the 0–30% signal range [S14], then the marginal effect of the judge's *authority* is a
second-order term on top of a first-order reliability problem. *(Definitive on all three
abstracts. [S14] is observational and confounded — reviewer composition is not randomly assigned
— so **directional** as a causal claim, and the paper's own conclusion is that CRAs "should
augment rather than replace human reviewers" [S14], which is what this repo does.)*

### 8.6 The strongest argument FOR a fixing reviewer has no source

The dispatch names it: a reviewer that must produce the fix bears the cost of being wrong and
may therefore review more carefully. **No source supporting this was located (N3).** The nearest
adjacent evidence points the other way — [S13] finds reviewer-authored fixes adopted less and
inflating complexity when adopted. **Stated plainly: this counter-argument is as unevidenced as
the thesis it attacks**, and neither side of §3's question currently has a measurement.

### 8.7 Matched-compute results say extra actors may buy nothing

`case_against.md` §2.3.1 holds Tran & Kiela's matched-compute result (single-agent systems match
or outperform multi-agent systems when reasoning tokens are held constant) and §2.3.5 holds
Anthropic's own 3–10x token multiplier for multi-agent implementations. **Cited, not re-derived.**
Both are off-domain for review work — `case_against.md` §5.5 says so itself — but they are the
reason a decide-only layer must justify its cost, not merely its plausibility.

---

## 9. Citations

### 9.1 Negative findings and their search method

**N1 (headline). No study was located that holds evaluator, artifact and task constant and
varies ONLY whether the evaluator may modify the artifact.** Searched via: arXiv Atom API
id-lookups for eleven candidate papers; web searches on `ablation "reviewer agent" allowed to
edit code versus feedback only author fixes multi-agent LLM defect detection comparison`,
`"code review" agent "read-only" reviewer versus reviewer that applies fixes empirical study
which detects more defects`, and `arxiv LLM agent ablation judge with write access versus
verdict only merge decision defect detection difference`; forward-reading the five nearest
located papers ([S12] SWE-Review, [S13] Human-AI Synergy, [S15] c-CRAB, [S16] Refute-or-Promote,
[S10] CodeAgent) for such an arm; and inspection of [S15]'s task definition, which scores a
produced review and has no apply-your-own-finding arm. Two of the three searches' own result
summaries stated that no such direct comparison appeared. **The crux experiment does not appear
to exist.**

**N2. No experiment isolating the inspection "find defects, do not design fixes" rule as a
variable was located.** Searched via: web search on `software inspection experiment "find
defects" versus "discuss solutions" meeting rule effectiveness empirical evaluation Votta
Porter`; web search on `Fagan 1976 "Design and code inspections" IBM Systems Journal inspection
meeting "find errors" not fix rework author moderator roles`; fetches of three NASA SWEHB pages
[S21][S22][S23]. The SEI teaching-materials PDF
(`sei.cmu.edu/documents/1561/1993_011_001_16127.pdf`) returned unparsed PDF binary and was not
used. The ACM DL record for Fagan (1976) was not fetched. The located experimental inspection
literature varies *detection method* (ad hoc / checklist / defect-based reading), *team size* and
*session count* — not fix authority.

**N3. No source was located supporting the claim that a reviewer who must produce the fix
reviews more carefully.** Searched incidentally across the code-review sweep (the three N1
searches plus the two N2 searches) and not found in any fetched abstract. The accountability-
psychology literature that would be its natural home was not reached: no fetchable primary was
identified within this run's budget. **Stated as an unevidenced counter-argument in §8.6, not
as a finding.**

**N4. No published measurement of the round-trip cost of a HOLD-and-redispatch versus an
in-place fix was located.** Searched incidentally across the same sweep. This is the cost side
of §3's question and it is unquantified on both the literature side and (per N7) this repo's
side.

**N5. `cacm.acm.org/research/lessons-from-building-static-analysis-tools-at-google/` returned
HTTP 403 and was NOT fetched.** The widely-repeated claim that attaching suggested fixes
increases the rate at which static-analysis findings are acted on — which would be the strongest
argument for a fixing reviewer — is therefore **not made in this paper**. [S20] Getafix is cited
instead, for the weaker and verifiable claim that fixing static-analysis findings "remains a
mostly manual task in practice" [S20].

**N6. Specific adoption-rate percentages for AI-agent versus human code-review suggestions
(circulated as "16.6% vs 56.5%") appeared ONLY in a search-engine result summary and are NOT
cited.** [S13]'s abstract, which was fetched, states the direction ("a significantly lower
rate") without the figures. A search summary is never a source.

**N7. Whether `review-pr`'s decide-only property is enforced by tool permissions or by prompt
instruction was NOT established in this run.** Method: the shipped script was sought in this
worktree via Glob (`**/review-pr*`, `scripts/**/*review*`) and Grep (`VERDICT: (MERGE|HOLD)`);
the search tooling returned `ENOENT: … posix_spawn 'rg'` on every attempt after the first two
calls, and `docs/file_structure.txt` does not exist in this worktree, which indicates a
docs-scoped checkout. The decide-only property is therefore taken from first-party documented
sources inside the repo (`system-overview.md § Composition`, `§ Where the seams are`, and
`workflow-scripts.md § Composition`) and is **definitive as a documented design intent and
unverified as an enforced mechanism.**

### 9.2 Source list

**Judge reliability and evaluation bias (MEDIUM volatility)**

- [S1] Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z.,
  Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). *Judging LLM-as-a-Judge
  with MT-Bench and Chatbot Arena.* arXiv:2306.05685. https://arxiv.org/abs/2306.05685
  *(abstract via arXiv Atom API)*
- [S2] Panickssery, A., Bowman, S. R., & Feng, S. (2024). *LLM Evaluators Recognize and Favor
  Their Own Generations.* arXiv:2404.13076. https://arxiv.org/abs/2404.13076 *(abstract via
  arXiv Atom API)*
- [S3] Li, H., Dong, Q., Chen, J., Su, H., Zhou, Y., Ai, Q., Ye, Z., & Liu, Y. (2024).
  *LLMs-as-Judges: A Comprehensive Survey on LLM-based Evaluation Methods.* arXiv:2412.05579.
  https://arxiv.org/abs/2412.05579 *(abstract via arXiv Atom API)*
- [S4] Zhang, S., Wang, A., & Lei, S. (2026). *Catching One in Five: LLM-as-Judge Blind Spots in
  Production Multi-Turn Transaction Agents.* arXiv:2606.10315. https://arxiv.org/abs/2606.10315
  *(abstract via arXiv Atom API; single-team production study — directional as a result)*

**Self-critique, verification and repair (LOW volatility)**

- [S5] Saunders, W., Yeh, C., Wu, J., Bills, S., Ouyang, L., Ward, J., & Leike, J. (2022).
  *Self-critiquing models for assisting human evaluators.* arXiv:2206.05802.
  https://arxiv.org/abs/2206.05802 *(abstract via arXiv Atom API)*
- [S6] Stechly, K., Marquez, M., & Kambhampati, S. (2023). *GPT-4 Doesn't Know It's Wrong: An
  Analysis of Iterative Prompting for Reasoning Problems.* arXiv:2310.12397.
  https://arxiv.org/abs/2310.12397 *(abstract via arXiv Atom API)*
- [S7] Valmeekam, K., Marquez, M., & Kambhampati, S. (2023). *Can Large Language Models Really
  Improve by Self-critiquing Their Own Plans?* arXiv:2310.08118. https://arxiv.org/abs/2310.08118
  *(abstract via arXiv Atom API)*
- [S8] Olausson, T. X., Inala, J. P., Wang, C., Gao, J., & Solar-Lezama, A. (2023). *Is
  Self-Repair a Silver Bullet for Code Generation?* arXiv:2306.09896.
  https://arxiv.org/abs/2306.09896 *(abstract via arXiv Atom API)*

**Agentic review and code-review agents (MEDIUM–HIGH volatility; 2024–2026)**

- [S9] Widyasari, R., Weyssow, M., Irsan, I. C., Ang, H. W., Liauw, F., Ouh, E. L., Shar, L. K.,
  Kang, H. J., & Lo, D. (2025). *Let the Trial Begin: A Mock-Court Approach to Vulnerability
  Detection using LLM-Based Agents.* arXiv:2505.10961. https://arxiv.org/abs/2505.10961
  *(abstract via arXiv Atom API)*
- [S10] Tang, X., Kim, K., Song, Y., Lothritz, C., Li, B., Ezzini, S., Tian, H., Klein, J., &
  Bissyandé, T. F. (2024). *CodeAgent: Autonomous Communicative Agents for Code Review.*
  arXiv:2402.02172. https://arxiv.org/abs/2402.02172 *(abstract via arXiv Atom API)*
- [S11] Zhuge, M., Zhao, C., Ashley, D., Wang, W., Khizbullin, D., Xiong, Y., Liu, Z., Chang,
  E., Krishnamoorthi, R., Tian, Y., Shi, Y., Chandra, V., & Schmidhuber, J. (2024).
  *Agent-as-a-Judge: Evaluate Agents with Agents.* arXiv:2410.10934.
  https://arxiv.org/abs/2410.10934 *(abstract via arXiv Atom API)*
- [S12] Wang, R., Chen, J., Wang, S., Tao, C., Yang, S., Jiang, Y., Yap, K.-H., Shang, L., Li,
  X., & Bai, H. (2026). *SWE-Review: Closing the Loop on Issue Resolution with Agentic Code
  Review.* arXiv:2607.06065. https://arxiv.org/abs/2607.06065 *(abstract via arXiv Atom API;
  2026 preprint — directional)*
- [S13] Zhong, S., Noei, S., Zou, Y., & Adams, B. (2026). *Human-AI Synergy in Agentic Code
  Review.* arXiv:2603.15911. https://arxiv.org/abs/2603.15911 *(abstract via arXiv Atom API;
  278,790 review conversations across 300 projects — observational)*
- [S14] Chowdhury, K., Banik, D., Ferdous, K. M., & Shamim, S. I. (2026). *From Industry Claims
  to Empirical Reality: An Empirical Study of Code Review Agents in Pull Requests.*
  arXiv:2604.03196. https://arxiv.org/abs/2604.03196 *(abstract via arXiv Atom API;
  observational, confounded — directional as a causal claim)*
- [S15] Zhang, Y., Pan, Z., Yusuf, I. N. B., Ruan, H., Shariffdeen, R., & Roychoudhury, A.
  (2026). *Code Review Agent Benchmark.* arXiv:2603.23448. https://arxiv.org/abs/2603.23448
  *(abstract via arXiv Atom API)*
- [S16] Agarwal, A. (2026). *Refute-or-Promote: An Adversarial Stage-Gated Multi-Agent Review
  Methodology for High-Precision LLM-Assisted Defect Discovery.* arXiv:2604.19049.
  https://arxiv.org/abs/2604.19049 *(abstract via arXiv Atom API; single-author campaign report,
  no control arm — directional)*
- [S17] Monperrus, M. (2026). *The End of Code Review: Coding Agents Supersede Human Inspection.*
  arXiv:2606.13175. https://arxiv.org/abs/2606.13175 *(abstract via arXiv Atom API; position
  paper — directional)*
- [S18] Lu, J., Jiang, L., Li, X., Fang, J., Zhang, F., Yang, L., & Zuo, C. (2025). *Towards
  Practical Defect-Focused Automated Code Review.* arXiv:2505.17928.
  https://arxiv.org/abs/2505.17928 *(abstract via arXiv Atom API; cited for the industrial
  multi-role framing and the KBI/FAR framing only)*
- [S19] Aðalsteinsson, F. S., Magnússon, B. B., Milicevic, M., Davidsson, A. N., & Cheng, C.-H.
  (2025). *Rethinking Code Review Workflows with LLM Assistance: An Empirical Study.*
  arXiv:2505.16339. https://arxiv.org/abs/2505.16339 *(abstract via arXiv Atom API; field
  experiment at one company — directional)*
- [S20] Bader, J., Scott, A., Pradel, M., & Chandra, S. (2019). *Getafix: Learning to Fix Bugs
  Automatically.* arXiv:1902.06111. https://arxiv.org/abs/1902.06111 *(abstract via arXiv Atom
  API)*

**Human-process antecedents — standards and regulation (LOW volatility)**

- [S21] NASA. *7.10 — Peer Review and Inspections Including Checklists.* NASA Software
  Engineering Handbook Ver D.
  https://swehb.nasa.gov/spaces/SWEHBVD/pages/102695640/7.10+-+Peer+Review+and+Inspections+Including+Checklists
  *(rendered page; the fetch summarized — wording NOT verified verbatim, substance reported)*
- [S22] NASA. *SWE-087 — Software Peer Reviews and Inspections for Requirements, Plans, Design,
  Code, and Test Procedures.* NASA Software Engineering Handbook Ver D.
  https://swehb.nasa.gov/spaces/SWEHBVD/pages/102695472/SWE-087+-+Software+Peer+Reviews+and+Inspections+for+Requirements+Plans+Design+Code+and+Test+Procedures
  *(rendered page; the fetch summarized — wording NOT verified verbatim)*
- [S23] NASA. *SWE-141 — Software Independent Verification and Validation.* NASA Software
  Engineering Handbook Ver C.
  https://swehb.nasa.gov/display/SWEHBVC/SWE-141+-+Software+Independent+Verification+and+Validation
  *(rendered page; the fetch summarized — wording NOT verified verbatim)*
- [S24] U.S. Securities and Exchange Commission. *17 CFR § 210.2-01 — Qualifications of
  accountants* (Regulation S-X Rule 2-01), Preliminary Note and paragraph (b). Retrieved through
  the eCFR versioner API:
  `https://www.ecfr.gov/api/versioner/v1/full/2026-01-01/title-17.xml?part=210&section=210.2-01`
  *(structured API source, but the fetch returned prose alongside the spans — wording NOT
  established verbatim beyond the short phrase quoted)*

**Vendor and product documentation — first-party (HIGH volatility; this is what decays)**

- [S25] Cognition (2025-06-12). *Don't Build Multi-Agents.*
  https://cognition.com/blog/dont-build-multi-agents *(rendered first-party blog; note
  `cognition.ai` now 301-redirects to `cognition.com`. Fetch returned an explicit negative on the
  act-vs-critique distinction. Informal first-party — directional per §3.)*
- [S26] Cognition (2026-04-22). *Multi-Agents: What's Actually Working.*
  https://cognition.com/blog/multi-agents-working *(rendered first-party blog; date established
  by enumerating `cognition.com/blog` and reading the listing. Two independent fetches with
  different prompts agreed on the principle sentence and the 2-bugs/PR figure. Informal
  first-party — directional.)*
- [S27] Cognition (2026-02-10). *Closing the Agent Loop: Devin Autofixes Review Comments.*
  https://cognition.com/blog/closing-the-agent-loop-devin-autofixes-review-comments *(rendered
  first-party blog; the post does NOT state whether the fixing agent is the same session as the
  reviewing agent — stated as a gap at point of use.)*
- [S28] Cognition (2026-01-21). *Devin Review: AI to Stop Slop.*
  https://cognition.com/blog/devin-review *(rendered first-party blog; the fetch returned an
  explicit negative on measured figures — none present.)*
- [S29] Anthropic. *Building Effective Agents.*
  https://www.anthropic.com/engineering/building-effective-agents *(rendered first-party
  engineering page; short spans only.)*
- [S30] OpenAI. *Guardrails*, OpenAI Agents SDK for Python.
  https://raw.githubusercontent.com/openai/openai-agents-python/main/docs/guardrails.md *(raw
  markdown; the fetch nonetheless summarized much of the file, so wording beyond the short
  tripwire span is reported rather than quoted.)*
- [S31] GitHub. *Using GitHub Copilot code review.*
  https://raw.githubusercontent.com/github/docs/main/content/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review.md
  *(raw markdown from the first-party github/docs repo; returned unexpanded Liquid template
  tokens, which is the evidence that the fetch was raw. **Definitive.**)*

**Pool papers relied on and NOT re-derived (per §3 and pool convention, referenced by source
name and section rather than by their own `[Sn]` numbers)**

- `raw/convergence_stopping.md` (Last validated 2026-08-03; **Critic: PASS**) — owns the
  self-correction corpus (Huang et al., Kamoi TACL, Self-Correction Bench), the judge-pathology
  roll-up (CriticGPT, self-preference, sycophancy, LLM-REVal), the Cross-Context Review
  condition table, SWR-Bench's disjoint-finding-set result, and Porter et al. (1998).
- `raw/case_against.md` (Last validated 2026-08-03; **Critic: PASS-WITH-FIXES**) — owns the
  matched-compute SAS≥MAS result, the MAST taxonomy, Anthropic's 3–10x multiplier, and D7, the
  finding this paper was queued to adjudicate.
- `raw/reflection_literature.md` (Last validated 2026-07-23; **Critic: PASS**) — owns the
  Reflexion / Self-Refine / CRITIC / Self-RAG corpus and the four substrate gaps.
- `raw/hierarchical_agents.md` (Last validated 2026-07-25; **Critic: PASS**) — owns the
  planner/executor/verifier decomposition literature and the File-as-Bus ablation.
- `raw/combination_prior_art.md`, `raw/bernstein_capability_mining.md`,
  `raw/paperclip_assessment.md` — own the comparator scorecards used in §6.

*(Two of these papers are past a strict reading of their own revalidation windows as of
2026-08-06 — `reflection_literature.md` (medium — 3 months, due 2026-10-23: in window) and
`hierarchical_agents.md` (medium — 3 months, due 2026-10-25: in window) are fine;
`convergence_stopping.md` (high — 6 weeks, due 2026-09-14) and `case_against.md` (high — 4
weeks, due **2026-08-31**) are both in window. No stale-past-window paper is consumed as
authority here.)*

**Internal evidence (not citations — recorded for traceability)**

- `docs/standards/architecture/problem-statement.md` element 2 — the claim under test.
- `docs/standards/architecture/system-overview.md` § Composition, § Where the seams are — the
  shipped decide-only child and the two seams.
- `docs/standards/workflow-scripts.md` § Composition — the first-party rationale, the
  fresh-context n=1, and the routing-contract rules that bound the verdict vocabulary.

---

## 10. Test plan — what research cannot settle

Research located the shape of the question, resolved the pool's live contradiction, and
established that **the crux experiment does not exist in the literature (N1)**. It cannot supply
the answer. These are ordered by decision value; T1 is the paper's actual deliverable.

**T1. The A/B that N1 says nobody has run: same judge, same PRs, write authority as the only
variable.**
*Because:* this is the entire content of `decide ≠ act`, and no located source varies it.
*Design:* take K ≥ 20 merged PRs spanning at least three task shapes (security sweep, refactor,
docs/standards edit — the confound `convergence_stopping.md` T1 already names). Seed each with N
known defects of graded severity, as in that paper's T2. Run three arms against each PR, all
with identical prompts, identical model, identical repository access, and **only the tool
permission set varied**:
 - **Arm A (i):** the authoring run reviews its own work in its own context.
 - **Arm B (ii):** a fresh-context reviewer with write access; it fixes what it finds and reports.
 - **Arm C (iii):** a fresh-context judge with read-only tools; it emits `MERGE | HOLD` + runway,
   and a **separate** author run applies the runway.
*Measure, per arm:* seeded-defect recall; unseeded (natural) findings verified by a human;
false-positive rate; total tokens; wall-clock to a merged state; and — the variable [S13] says
matters — diff size and complexity delta of the resulting change.
*Reads out:* whether removing authoring authority changes **detection** (recall), **disposition
quality** (false positives, verified findings) or only **cost**.
*Falsifies the premise if:* Arm B's recall and verified-finding count meet or beat Arm C's at
equal or lower total cost. That result would say the `decide ≠ act` seam is buying nothing and
should be relaxed — element 2 would need rewriting to claim only `author ≠ judge`.
*Confirms it if:* Arm C's verified-finding count and false-positive rate beat Arm B's, or Arm B
shows the complexity/size inflation [S13] measured for reviewer-authored fixes.
*Note the arm that must NOT be omitted:* Arm A is the control that everything published already
covers; without it the experiment cannot be calibrated against the literature.

**T2. Price the round trip (N4).**
*Because:* §8.1 — the cost side of the decision is unmeasured in the literature and in this repo.
*Design:* instrument every `HOLD` in the existing run-log JSONL with: the finding class that
caused it, the tokens and wall-clock of the re-dispatch, and whether the fix that landed was
≤ 5 lines. *Reads out:* the fraction of HOLDs that were trivia, which is exactly the population
a fixing reviewer would have absorbed. **If most HOLDs are trivia, the decide-only rule is
expensive for a benefit T1 has to prove; if most are structural, the rule is cheap.** This is the
cheapest item here and should run first.

**T3. Establish whether the seam is structural or textual (N7).**
*Because:* P13 — a prompt-level "do not edit" and a tool-permission-level read-only are
different claims, and `system-overview.md` presents `decide ≠ act` as a seam. A seam that a
model can talk itself past is a convention.
*Design:* read `scripts/workflows/children/review-pr.sh` for its allowed-tool configuration;
then adversarially dispatch it against a PR with an instruction embedded in the diff that invites
it to fix something. *Reads out:* whether the constraint holds under pressure.
*This is a one-hour check and it gates how strongly §7 P5 may be cited.*

**T4. Test the verdict-vocabulary bound (P8).**
*Because:* [S4] found a production judge whose defects were perceived and then discarded by a
rubric with no slot for them, and `review-pr`'s vocabulary is closed by design.
*Design:* on a sample of `review-pr` runs, have a human read the judge's full prose output and
count findings that were *stated* in the body but did not survive into the `MERGE | HOLD` +
runway. *Reads out:* this repo's own routing-loss rate — the [S4] failure mode, measured locally.
*Fails the design if:* the loss rate is material, in which case the remedy is a richer verdict
payload (`workflow-scripts.md § Routing contracts`: "The signal should carry its payload"), not a
different judge.

**T5. Test whether context, not authority, is the active variable (§8.4).**
*Because:* [S12]'s winning arm was the repository-exploring reviewer, and `case_against.md` D7 and
T5 both ask for this. It is separable from T1 and cheaper.
*Design:* hold write authority fixed at read-only and vary context: (a) diff only, (b) diff +
original task, (c) diff + original task + full repository exploration. *Reads out:* whether the
`author ≠ judge` benefit the pool has measured is a context effect that a decide-only judge can
recover by being given more to read.

**Not settleable by any of the above, and recorded as such:** whether a decide-only judge's
*disposition* — the ruling itself, as opposed to the findings — is better than a fixing
reviewer's. Every instrument above measures defects found and cost incurred. Nothing measures
whether `MERGE` was the right call, because that requires ground truth about a change's future
consequences, which arrives months later if at all. This is the same residual-severity gap
`convergence_stopping.md` §7 records, and it does not close.

---

## 11. Retire-or-keep: this topic has earned its answer and should now stop consuming research slots

**Recommendation: RETIRE the research topic; KEEP the shipped design; PROMOTE the question to
the experiment queue.**

Stated plainly, because the topic was displaced three consecutive cycles and deserves a ruling
rather than a fourth deferral:

1. **The question was worth asking and is now answered as far as reading can answer it.** The
   sweep was broad — 31 external sources, four deliberately-varied search phrasings, three
   research literatures (LLM judging, automated code review, human inspection/assurance), and a
   product-level census of thirteen systems. It produced a clean, decision-relevant result:
   `author ≠ judge` is supported, `decide ≠ act` is unevidenced, and the missing evidence is
   missing everywhere, not just in the places this run looked.
2. **More reading will not close it.** N1's gap is not a gap in *coverage*; it is a gap in what
   anyone has bothered to measure. The field ships configuration (iii) and does not ablate it.
   A revalidation sweep in six weeks will find newer preprints doing the same thing.
3. **The topic's residual value is in §10, not in §2–§6.** T2 and T3 are hours of work against
   this repo's own logs and scripts and would each move the design more than another literature
   cycle.
4. **One thing WOULD justify a refresh rather than a retirement**, and it is narrow: if a
   published (ii)-vs-(iii) ablation appears. The trigger to watch is the code-review-agent
   benchmark line ([S15] c-CRAB, [S12] SWE-Review) — a benchmark that already scores reviews is
   one arm away from scoring reviewers-who-fix. **Set this as an on-trigger revalidation rather
   than a scheduled one**, and let the scheduled 6-week interval lapse into a retirement if the
   trigger has not fired.
5. **The one live carry-forward for the synthesis, not for this topic:** §5's resolution of the
   Cognition contradiction is a *correction to three sibling sites* (`case_against.md` §2.3.4,
   §5.4 and D7, plus `topics.md`'s entry) and should be traced there per §4's
   corrected-fact rule. That is a synthesis action, not a reason to keep this topic open.

**And the sentence a consumer must carry forward if it carries nothing else:** *the shipped
decide-only design is defensible, conventional, and matched to three human-process antecedents —
and the specific claim that it reduces defects **relative to a reviewer that may also fix** has
never been tested by anyone, including us.*
