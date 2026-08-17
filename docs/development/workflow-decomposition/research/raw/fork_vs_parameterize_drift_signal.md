# fork_vs_parameterize_drift_signal

```
Topic:          Two workflow children carry near-identical prompt blocks and the copies have
                already drifted. Holding only the two current texts — no authoring history, no
                author to ask — what signal or method lets a reviewer tell a DELIBERATE variant
                from a NEGLECTED copy?
Feeds:          docs/development/workflow-decomposition/roadmap.md § Phase 2, the unchecked item
                "Rule fork-vs-parameterize — the half a test cannot judge: a copy that has already
                drifted reads as intent, not accident"
Last validated: 2026-08-17
Revalidate:     high — 6 weeks
Confidence:     DEFINITIVE on what each cited study did, measured and reported (all quotes are
                exact character sequences returned by a raw fetch or a local read — see the
                sourcing note below). DEFINITIVE on the local counts in §5, each enumerated by a
                command whose output is quoted. DERIVED on this paper's central claim — that the
                retrospective signal the field actually uses is FIT-TO-REFERENT and CONTEXT, not
                inter-copy similarity — and on the four-signal ordering in §4.2; the inputs are
                definitive, the ordering is this paper's. NEGATIVE FINDINGS, with search method,
                on (a) the absence of any prompt/LLM-engineering literature on divergence between
                copies of a prompt and (b) the absence of any source using drift MAGNITUDE as an
                intent signal. UNVERIFIED: nothing in this paper rests on uncorroborated
                commentary; the one vendor article consulted is cited only for what it does NOT
                contain, and is not quoted.
Critic:         not-yet-verified — 2026-08-17
```

> **Volatility note (Research Standard §3, mixed-volatility rule).** The load-bearing evidence is
> peer-reviewed clone and documentation-clone research from 2005–2021 — **low volatility, safe to
> skip on refresh**: §2, §3.1–§3.4, §4, and every claim attributed to [R1]–[R5] and [R7]. The
> header takes the *highest* tier present, which comes from two smaller parts: **§3.5** (the
> prompt/LLM-engineering negative finding — a fast-moving literature where one new paper flips a
> stated gap) and **§5** (local repo measurements, pinned to commit `a92e53a` and true only of that
> commit). **A refresh should re-run §3.5's searches and §5's commands, and leave the rest alone.**

> **Sourcing note (read before quoting this paper).** Every span presented as a quotation below is
> an exact character sequence returned to this analyst — from `pdftotext -layout` over bytes
> fetched with `curl`, from a raw `raw.githubusercontent.com` file, or from a local file read. Two
> mechanical normalizations were applied to PDF-derived spans and to nothing else: **line breaks
> introduced by two-column extraction were joined, and end-of-line hyphenation introduced by the
> typesetter was closed** (`in-\ntentionally` → `intentionally`). **No word was changed, added or
> dropped.** Where a quote joins text the source did not have adjacent, it says so.

---

## 1. Primer — the narrow question, and what is already settled upstream

### 1.1 What is NOT re-derived here

The general fork-vs-parameterize question is answered by
[`docs/standards/architecture/research/raw/workflow_reuse_boundary.md`][U1] — 24 sources, `Last
validated: 2026-08-03`, `Critic: PASS-WITH-FIXES`, `Revalidate: high — 6 weeks`, therefore **inside
its window on 2026-08-17 and citable as current**. Its `Feeds:` line names this exact ruling. Four
of its conclusions are taken as given here and are not re-argued:

1. Every orchestration system at scale ships both a small-grained and a large-grained reuse unit
   [U1 §2.1]; copy-and-adapt out-competes first-class reuse in practice [U1 §4].
2. **The field's operative discriminator is expected future co-evolution, not textual overlap** —
   Kapser & Godfrey's Forking / Templating / Customization / Exact-match partition, made on "the
   high level motivation for the cloning pattern" [U1 §7.1].
3. A percentage-shared figure "**cannot decide the ruling in either direction**" [U1 §7.1].
4. A third option exists — record lineage, propagate mechanically (Copier) [U1 §7.3].

[U1] also declines the question this paper asks. Its own boundary section states: *"Nothing in the
corpus studies duplicated **prompt prose**. Our shared artifacts are substantially LLM prompt text,
whose failure modes (semantic drift, instruction interference, context budget) are not code-clone
failure modes and are not covered by any cited source. The CI analogy may hold for the bash and
break for the prompts."* [U1 §9.2]

### 1.2 The narrower question, and why it is a different question

[U1]'s discriminator is **forward-looking**: *will* a change to one require the same change in the
other. Its own test plan answers it by walking commit history [U1 §10, item 1]. The roadmap item
this paper feeds is different and harder. A reviewer sits in front of two drifted prompt texts. The
copies were made at different times by different runs. The "author" is a dispatch that no longer
exists and cannot be interviewed. And the drift is already *there* — which, as the repo's own
standard puts it, is the problem:

> *"Matching is verbatim, so a copy that has already drifted by one word is invisible — and a
> drifted copy is the more dangerous kind, because it reads as intent rather than as an accident."*
> — [L2] `docs/standards/workflow-scripts.md:715`

So: **is that reading a local bias, or is it the field's position?** It turns out to be the field's
position, written down, and that is where this paper starts.

---

## 2. The specific options — the four retrospective methods the field actually has

There are exactly four documented ways to classify an existing divergence as deliberate or
neglected. Three of them appear in the corpus; the fourth is the absence of one.

| # | Method | Needs the author? | Needs history? | Measured reliability |
|---|---|---|---|---|
| **M1** | **Ask the developers** | yes | no | treated as ground truth [R1] |
| **M2** | **Infer motivation from artifact + context**, manually | no | no | κ = 0.271, three judges [R3] |
| **M3** | **Fit-to-referent asymmetry**, computed | no | no | 79% precision on prose [R4] |
| **M4** | **Learn a classifier from features** | no | optional | does not transfer across projects [R5] |

### 2.1 M1 — ask the author, and default to DELIBERATE when you cannot *(definitive)*

Juergens et al.'s ICSE 2009 study is the field's most-cited empirical treatment of exactly this
distinction, and its method is unambiguous [R1]:

> *"The inconsistent clone groups were then presented to the developers of the respective systems
> in the tool CloneDetective mentioned in Section 4.4, which is able to display the commonalities
> and differences of the clone group in a clearly arranged way, as depicted in Figs. 1 and 7. The
> developers rated whether the clone groups were created intentionally or unintentionally."*

The reason no artifact-only method can be complete is stated by the same paper, in its definition
of what "intentional" even means [R1]:

> *"It can obviously be sensible to change a clone so that it becomes inconsistent to it
> counterparts because it has to conform to different requirements. However, the important
> difference is whether the developer is aware of the other clones, i.e. whether the inconsistency
> is intentional."*

**Intent is defined as an AWARENESS PROPERTY OF A PERSON.** It is not a property of the text, and no
amount of reading the text can recover it directly — only correlates of it. *(definitive: this is
the source's own definition, quoted.)*

And then the finding that makes the roadmap item's phrasing literal rather than rhetorical. When
the authors could not be reached, the study did not drop the case — it **defaulted it to
intentional**, twice stated [R1]:

> *"In cases where intentionality or faultiness could not be determined, e. g., because none of the
> original developers could be accessed for rating, the inconsistencies were treated as intentional
> and non-faulty."*

> *"Inconclusive candidates were ranked as intentional and non-faulty."*

**This is the single most directly on-point finding in the paper.** The roadmap's sentence — *"a
copy that has already drifted reads as intent, not accident"* [L3] — is not a local worry. It is the
documented conservative default of the field's benchmark study, applied precisely in the situation
this paper is about: the author is gone. *(definitive; the transfer of that default to our setting
is derived, and §6.3 argues the default's safety direction is INVERTED for us.)*

Juergens et al. also close off the forward-looking tooling escape, for exactly our case [R1]:

> *"Furthermore, for existing clones, there should be tool support that ensures that all changes
> that are made to a clone are made in the full knowledge of its duplicates. Tools such as
> CloneTracker [4] or CReN [10] provide promising approaches. However, both approaches are not
> applicable to existing software that already contains inconsistent clones."*

That is the gap this paper occupies, named by the source: lineage tooling ([U1 §7.3]'s third option)
prevents the problem going forward and **does not diagnose copies that have already drifted**.

### 2.2 M2 — infer motivation from the artifact, without history *(definitive)*

Kapser & Godfrey classified clones in Apache httpd 2.2.4 and Gnumeric 1.6.3 — systems they did not
write — with no authoring interviews and no commit history. Their method section is the corpus's
only fully-enumerated recipe for artifact-only retrospective classification [R2]:

> *"Classifying the clones into patterns was done manually, based on the descriptions we have
> documented in Section 3. The high level classification was one of the four clone pattern groups:
> Forking, Templating, Customization and Exact match. … **The primary mechanism for classification
> was to infer the motivation for the duplication.** This required an understanding of programmer
> intent for each code fragment individually and also the types of changes made to the cloned code.
> To determine the purpose of the source code fragments, we analyzed the code fragments in the
> context of the software system. Relevant documentation (either found within the source code or
> distributed with the source code), data structures, and data flow were referenced to gain as much
> information about the source code as possible."*

and, on how the *differences* enter the judgement [R2]:

> *"Next we analyzed the differences between the clones. These differences include not only the
> textual differences of the cloned code fragments, but also the differences in the programmer
> intent uncovered in our analysis of the purpose of the code. … We also analyzed the purpose of
> the file and subsystems containing the clones. Combining information about the intent of
> individual code fragments with an understanding of their differences, we could then assess
> individual attributes, such as forces that will affect evolution of the source code and
> difficulty to form a more general abstraction, in order to infer motivation for forming the code
> clone."*

**Enumerated evidence classes M2 uses** (read off the two passages above): documentation in or
shipped with the source; data structures; data flow (callers and callees); **the purpose of the
containing file and subsystem**; the textual differences; and a forecast of the forces that will
drive future evolution. *(definitive — this is an enumeration of the source's own list, not an
addition to it.)*

Its cost is stated too: *"This process was very time consuming in the beginning of the sample
analysis of each system, but as we analyzed more clones the process became easier as we could reuse
much of the knowledge about the system we gained over time."* [R2]

The pattern catalogue itself carries a per-pattern **`Structural manifestations`** field — *"How
this type of cloning pattern occurs in the system. This section describes the scope and type of
code copied, as well as the types of changes that are expected to be made."* [R2] That field is the
field's nearest thing to "what does a deliberate variant LOOK like," and two of its entries are
directly usable:

- *Experimental Variation* (a Forking pattern): *"The cloning pattern will appear as a cloned file,
  subsystem or class. **It may even be labeled as an experimental development effort**, as in the
  case of several Apache modules"* [R2] — **naming as an intent signal.**
- *Parameterized Code* (a Templating pattern): *"this solution can be modified to solve a new
  problem by **changing only a few identifiers or literals** in the code"*, with structural
  manifestation *"These clones most commonly involve entire functions that are within very close
  proximity of each other."* [R2] — **substitution-confined-to-identifiers as the templating
  signature, and proximity as a corroborating signal.**

### 2.3 M3 — fit-to-referent asymmetry *(definitive)*

This is the corpus's only implemented, precision-evaluated retrospective classifier that operates on
**prose**, and its mechanism is the most transferable thing in this paper. RepliComment analyses
Javadoc comment clones in 10 open-source Java projects. Its decision does **not** compare the two
copies to each other. It compares **each copy to the thing that copy is attached to** [R4]:

> *"In lines 10 and 11 of algorithm 1, the Clone analyzer computes the similarity scores between the
> cloned comment and each of the involved methods … **The method that achieves the highest
> similarity score is assumed to be the real owner of the comment, while the other is reported to be
> the victim of a mistaken copy-paste.** We set the diff-threshold value to 0.1, once again due to
> empirical evidence."*

The full decision procedure, verbatim from Algorithm 1 [R4]:

```
10:     m1Sim = compute-similarity(methodSignature1, clonedJavadoc)
11:     m2Sim = compute-similarity(methodSignature2, clonedJavadoc)
12:     if m1Sim < min-threshold and m2Sim < min-threshold then
13:          report(Please fix poor info comment)
14:          warn(mild_severity)
15:     if m1Sim > 0.50 and m2Sim > 0.50 then
16:          report(This looks like a false positive)
17:          warn(low_severity)
18:     if | m1Sim - m2Sim| > diff-threshold then
19:          report(Please fix method with lowest sim score)
20:          warn(high_severity)
```

Three regimes, and every one of them is a statement about intent: **both copies fit** → legitimate;
**neither fits** → both are generic and under-informative; **one fits and one does not** → the
misfitting one is the neglected copy. *(definitive as a description of the algorithm.)*

Its evaluation, from the abstract [R4]: *"Our evaluation of 10 well-known open source Java projects
identified over 11K instances of comment clones, and over 1,300 of them are potentially critical. …
Our manual inspection of 412 issues reported by RepliComment reveals that it achieves a precision of
79% in reporting critical comment clones. The manual inspection of 200 additional comment clones
that RepliComment filters out as being legitimate, could not evince any false negative."*

### 2.4 M4 — learn it from features, and the ablation that matters most here *(definitive)*

Wang et al. built a Bayesian-network predictor of whether a cloning operation is *harmful*, where
their definitions map cleanly onto [U1 §7.1]'s partition [R5]:

> *"resulting clone groups are never changed or always changed inconsistently. For this category of
> code clones, no maintenance of consistency is required, so that developers can perform
> copy-and-paste and benefit from the convenience for free. The second category of cloning
> operations, referred to as harmful cloning operations in this paper, includes cloning operations
> whose resulting clone groups need to be changed consistently."*

Harmless ≡ independent evolution ≡ Forking. Harmful ≡ must co-evolve ≡ Templating. *(derived, from
[R5] + [U1 §7.1]; both sources' definitions are quoted, the equation is this paper's.)*

Their 21 features split into three groups: **history**, **code**, and **destination** (the context of
the place the copy was pasted into). The ablation result is the reason this section exists [R5]:

> *"First, removing the history features has small impacts on the prediction in both scenarios.
> Second, removing the destination features results in significantly negative impacts on the
> effectiveness in both scenarios. Third, removing the code features results in a small impact in
> the conservative scenario but a significantly negative impact in the aggressive scenario. …
> These observations indicate that it may be feasible to use only the code features and the
> destination features to predict the harmfulness of intended cloning operations."*

And, for the specific case where the copies **have already been edited** [R5]:

> *"For customization clones, history features and code features sometimes may be misleading because
> the revisions in the cloned code affect the precision of these two features, while destination
> features may remain discriminative."*

The destination features are all *context and naming* comparisons: file-name similarity (two
variants), *"Method Name Similarity: The similarity between the name of the method containing the
copied piece of code and the name of the method containing the pasting destination"*, sum and
maximum parameter-name similarity, and *"Difference in Only Postfix Numbers: Whether the name of the
method containing the copied piece of code and the name of the method containing the pasting
destination differ in only their postfix numbers."* [R5]

The paper closes with the open problem that is this paper's own subject: *"Therefore, we may further
improve our approach by considering Kasper and Godfrey's clone categories, if we are able to
automatically identify the category of cloning operations."* [R5] *(the misspelling is the source's.)*

---

## 3. Comparative landscape — how well each method actually works

### 3.1 M2's measured reliability is FAIR, and that is the ceiling on any judgement rule *(definitive)*

Bettenburg et al. re-ran Kapser & Godfrey's eleven-category classification on Apache Mina and jEdit
with three independent raters, and — uniquely in the corpus — **measured the agreement** [R3]:

> *"In order to understand the dominant types of cloning patterns that we can observe from
> long-lived clone genealogies at release level, we performed a classification of the encountered
> clone genealogies into different categories of cloning [9]. For the three judges and eleven
> categories, we measured an inter-rater agreement of κ = 0.271 at p < 0.001. This result shows a
> statistically significant and fair level of agreement, considering the low number of judges and
> high number of categories [25]. While discussing our ratings, we found that most disagreements
> rooted in subtle semantics of the source code, which blurred the borders between categories."*

Kapser & Godfrey's own study did not measure agreement at all, and says so [R2]:

> *"First, the RGCs were judged by a single expert observer who is one of the authors of this
> paper. Without additional judges in this study there is no way to measure bias."*

**Derived (from [R2] + [R3]):** retrospective intent classification is *reproducible enough to be
worth doing and not reproducible enough to be a gate*. κ = 0.271 across three experts means two
competent reviewers looking at the same pair will often disagree. That is a strong argument for the
placement the repo's own standard already chose — *"That half is a judgement about which differences
are deliberate, and it belongs to the fork-vs-parameterize ruling, not to a test"* [L2] — and an
equally strong argument against ever promoting such a judgement into a merge-blocking check.

### 3.2 The load-bearing signal is CONTEXT, and history is nearly dispensable *(derived)*

**Derived (from [R5]'s ablation + [R5]'s customization caveat + [R2]'s evidence list):** a reviewer
holding two drifted texts and no authoring history is **far less handicapped than the framing
suggests**. The one study that measured the contribution of each feature group found history to be
the *least* load-bearing and destination context the *most*, and specifically found that once the
copies have been revised, the code features degrade while the **context features remain
discriminative**. [R2]'s independently-derived evidence list points the same way: four of its six
classes (documentation, data structures, data flow, purpose of the containing file and subsystem)
describe the *sites*, not the copied text.

This is the paper's central claim, and it inverts the intuitive one. **The instinct is to diff the
two texts harder. The evidence says to look at the two homes instead.** *(derived — the inputs are
definitive, the inference is this paper's; §6 states the case against it.)*

### 3.3 Drift PATTERN is a used signal; drift MAGNITUDE is not *(definitive + negative finding)*

RepliComment applies the standard Type I–IV clone taxonomy to comments and then **excludes one type
on intent grounds** [R4]:

> *"Type II comment clone: The comment of a code element is an exact copy of the comment of another
> code element except for identifier names."*

> *"RepliComment does not report Type II clones since comments differ in identifiers, and therefore
> likely document their corresponding piece of software correctly."*

Whereas the type it *does* target is defined by whole-section presence/absence [R4]:

> *"Type III comment clone: The comment of a code element is an exact copy of the comment of another
> code element except for some paragraphs."*

**This is a documented, implemented, evaluated instance of drift-pattern-as-intent-signal on prose,
and it points the way the dispatch question guessed:** divergence confined to named entities reads as
deliberate adaptation and is filtered out; divergence that is whole-block presence/absence is the
reportable class. It corroborates [R2]'s Parameterized-Code signature (*"changing only a few
identifiers or literals"*) and [R5]'s naming-pattern destination feature (*"Difference in Only
Postfix Numbers"*) from a third direction. *(definitive that each source states this; derived that
the three agree on a single signal.)*

RepliComment's other legitimacy heuristics are all **declared-relationship** tests rather than
text-similarity tests [R4]: *"the clone is found in methods with the same (overloaded) names"*, *"the
comment describes the same exception type"*, *"the clones affect parameters that have the same
name"*, *"Fields with same name in different classes are allowed to have the same comment."*

**Negative finding, with method: no source in this corpus uses the MAGNITUDE of inter-copy
divergence as a signal of intent.** Searched: the full extracted text of [R1]–[R5] and [R7] for
"similarity", "percent", "threshold", "distance", "magnitude"; every similarity computation found is
either (a) copy-to-referent [R4], (b) context-name-to-context-name [R5], or (c) a *detector*
parameter that decides what counts as a clone at all ([R1]'s *"max edit distance of 5"*). [R2] does
record a *scope* attribute — whether the clone covers the *"Full"* region or a *"Fragment"* — but
uses it descriptively, not as the discriminator; the discriminator is motivation. This corroborates
[U1 §7.1]'s conclusion that a percentage-shared figure cannot decide the ruling, and extends it: a
percentage is not merely insufficient, **it is not a signal anyone uses.**

### 3.4 Prose clones drift the same way — and are studied, but by content type, not intent *(definitive)*

Clone detection has been run on natural-language artifacts, and the phenomenon is described in terms
that match this repo's exactly [R7]:

> *"who tend to copy (and adapt) text if they need similar things at different parts of the document
> or different documents."*

*(This span is quoted from where it resumes after a page break. The sentence begins on the previous
page — "Specifications are written by people" — with a page number intervening in the extraction, so
the two halves are NOT presented as one contiguous quotation. The subject of "who" is
"Specifications … written by people".)*

> *"The copies of the text drift apart over time as some copies are adapted, for example to changes
> in the requirements of the customer, while others are forgotten. We now have conflicting
> requirements and the developers can introduce faults into the software."*

The scale is real: across 28 industrial requirements specifications, their Table 2 reports clone
coverage from 0.0% to 71.6% with an average of 13.6%, and column totals of **2,631 clone groups and
7,669 clones** [R7, Table 2]. *(definitive; the two totals are the source's own Σ row, read
directly from the extracted table, not computed by this paper.)*

But their manual coding answers a **different** question than ours [R7]:

> *"Afterwards, we manually coded a random sample of the clones to form categories of the type of
> information that was cloned. … To validate the more subjectively developed categories, we made an
> independent re-coding of a sample of the categorised clones and found a substantial agreement
> between the raters."*

**The contrast with §3.1 is the finding.** Categorising *what kind of content* was cloned reached
**substantial** agreement on prose [R7]; categorising *why it was cloned* reached only **fair**
agreement (κ = 0.271) on code [R3]. *(derived — two studies, two artifact types, two different
categorisation targets; the comparison is this paper's and is suggestive, not controlled. It is
consistent with the obvious reading: content type is in the text, intent is not.)*

### 3.5 The prompt / LLM-engineering literature does not have this concept *(negative finding, with method)*

**Searched:**

1. **[R6] "Promptware Engineering: Software Engineering for Prompt-Enabled Systems"** (arXiv
   2503.02400v2, 27 Jan 2026; ACM copyright block present) — a full-lifecycle survey of SE for
   prompt-based systems that enumerates open problems, including *"O24: Versioning and
   traceability"*. Fetched the PDF, extracted with `pdftotext -layout` (1,208 lines), and grepped
   the whole extraction for `clone|duplicat|redundan|DRY`. **Result: zero hits for `clone` and zero
   for `duplicat`.** The sole `redundan` hit is *"token compression eliminates redundancies"* —
   context-window economy, not artifact duplication. Prompt versioning appears as an **open
   problem**, not established practice: *"promptware engineering would benefit from specialized
   version control tools to track prompt iterations, document modifications, and ensure
   accountability"*, and *"Additionally, automated diff-checking mechanisms could highlight changes
   in prompts and their impact on LLM responses, improving reliability."* [R6] Both sentences are in
   the conditional — a gap the survey names, not a practice it reports.
2. **The term "prompt drift" is taken, and it means something else.** Web-searched for prompt drift
   as divergence between separately-maintained copies. A search-result summary asserted that a
   vendor article defined it that way; **fetching the article contradicted the summary** — [R8] is
   about an LLM's output behaviour changing over time for an unmodified prompt, and the fetch found
   no discussion of copy-to-copy divergence and nothing on telling a deliberate variant from a
   neglected one. *(This is recorded as a method note and a caution: the search summary was wrong
   and was never a source. [R8] is cited only for what it does not contain, is a rendered page read
   through a summarizing fetch, and is therefore not quoted anywhere in this paper.)*
3. **Web-searched** for `prompt clone detection` / `duplicate prompt detection` static-analysis
   tooling. Nothing prompt-specific returned; results were code-clone detection tools and
   LLMs-detecting-code-clones papers.
4. **What DOES exist first-party is the FORWARD mechanism only.** Google's Dotprompt file format
   ships **partials** — a shared-fragment primitive. Confirmed `default_branch` is `main` via the
   GitHub contents API before fetching, then enumerated the repo tree for paths matching `partial`
   (16 paths, including `spec/partials.yaml`, `examples/partials.prompt`,
   `java/.../PartialResolver.java`). The raw spec shows the inclusion syntax verbatim [R9]:
   ```
   - name: basic_partial
     template: |
       {{> greeting}} This is the main template.
     partials:
       greeting: "Hello from a partial!"
   ```
   That is the same mechanism this repo already implements as `modules/assistant/prompts/<name>.md`
   plus `act.shared_prompt("<name>")` [L2]. **It prevents duplication; it says nothing about
   diagnosing copies that already drifted** — the same limitation [R1] names for CloneTracker and
   CReN.

**Stated as a result:** as of 2026-08-17, **there is no prompt-engineering or LLM-engineering
literature on divergence between two separately-maintained copies of the same prompt text, and no
tooling for it.** The nearest usable prior art is the documentation-clone work in §2.3 and §3.4,
which studies prose but prose with a *formal* referent. *(negative finding; method enumerated above.
It is the claim in this paper most likely to be falsified by a refresh, which is why the header takes
the high volatility tier.)*

---

## 4. What this provides — enumerated, citable properties

### 4.1 Claims a ruling may rely on

1. **Intent is defined in the field as developer AWARENESS of the other copy** [R1], i.e. a property
   of a person, not of a text. Any artifact-only method estimates a correlate of it, never it.
   *(definitive)*
2. **The field's gold-standard method is to ask the author** [R1]; every other method in the corpus
   is an approximation of that interview. *(definitive)*
3. **When the author is unreachable, the benchmark study's documented default is INTENTIONAL** —
   *"Inconclusive candidates were ranked as intentional and non-faulty"* [R1]. The roadmap item's
   premise is the field's own default, not a local bias. *(definitive; see §6.3 for why the
   default's safety direction is inverted for us.)*
4. **Artifact-only retrospective classification IS documented and was performed at scale on systems
   the raters did not write**, with an enumerated evidence list: documentation in/with the source,
   data structures, data flow, the purpose of the containing file and subsystem, the textual
   differences, and a forecast of evolution forces [R2]. *(definitive)*
5. **Its measured inter-rater reliability is κ = 0.271 across three judges and eleven categories —
   "fair"** [R3]; the originating study was single-rater with, in its own words, *"no way to measure
   bias"* [R2]. A rule built on this is a judgement aid, never a gate. *(definitive)*
6. **History is the least load-bearing feature group; destination context is the most** — removing
   history had *"small impacts"*, removing destination features had *"significantly negative
   impacts"*, and code-plus-destination alone was reported feasible [R5]. *(definitive as a
   statement of [R5]'s ablation; the transfer to our setting is derived — see 4.2.)*
7. **Once copies have been revised, the copied-text features degrade and the context features
   survive** — *"the revisions in the cloned code affect the precision of these two features, while
   destination features may remain discriminative"* [R5]. This is exactly the already-drifted case.
   *(definitive)*
8. **A retrospective prose classifier exists, and its discriminator is fit-to-referent asymmetry, not
   copy-to-copy similarity** — *"The method that achieves the highest similarity score is assumed to
   be the real owner of the comment, while the other is reported to be the victim of a mistaken
   copy-paste"* [R4], evaluated at 79% precision over 412 manually-inspected issues, with no false
   negative evinced in 200 filtered-as-legitimate cases [R4]. *(definitive)*
9. **Drift confined to named entities is treated as deliberate; drift that is whole-block
   presence/absence is the reportable class** — [R4] excludes Type II comment clones by design,
   targets Type III; corroborated by [R2]'s Parameterized-Code signature and [R5]'s
   *"Difference in Only Postfix Numbers"* destination feature. *(definitive per source; the
   three-way agreement is derived.)*
10. **No source uses inter-copy drift MAGNITUDE as an intent signal.** *(negative finding; method in
    §3.3.)* This extends [U1 §7.1]'s "a percentage cannot decide the ruling" to "a percentage is not
    a signal anyone uses."
11. **Prose copies are documented to drift by exactly the mechanism this repo observed** — *"some
    copies are adapted … while others are forgotten"* [R7] — at industrial scale (28 specs, 2,631
    clone groups, 7,669 clones, mean clone coverage 13.6% [R7, Table 2]). *(definitive)*
12. **Forward lineage tooling does not solve this case, and the sources say so.** *"[B]oth approaches
    are not applicable to existing software that already contains inconsistent clones"* [R1]; the
    prompt-format equivalent (Dotprompt partials [R9]) is likewise a prevention mechanism.
    *(definitive)*
13. **The prompt/LLM literature is silent on copy divergence.** *(negative finding; method in §3.5.)*

### 4.2 The derived discriminator — four signals, ordered by evidential backing

**This ordering is DERIVED. It is this paper's inference across [R1]–[R5], it is undertested, and
§6 states the case against it.** It is offered as the input to a ruling, not as the ruling.

Given two drifted prompt texts and no authoring history, ask in this order:

| Rank | Signal | Question to ask | Backing |
|---|---|---|---|
| **1** | **Fit to referent** | Does each copy still fit *its own* child — its stage numbering, the artifacts it names, the job that child does? | [R4] — the only implemented, precision-evaluated instantiation, and it is on prose |
| **2** | **Context similarity of the two sites** | How alike are the two children's jobs, names, inputs and surroundings? Alike ⇒ co-evolution required ⇒ neglected copy. Unlike ⇒ independence legitimate ⇒ deliberate variant. | [R5] ablation (destination = most load-bearing, survives revision); [R2] (purpose of containing file/subsystem) |
| **3** | **Drift pattern (never magnitude)** | Are the differences confined to named entities and parameters, or are they whole blocks present in one copy and absent from the other? | [R4] Type II vs Type III; [R2] Parameterized-Code; [R5] postfix-number feature |
| **4** | **Stated rationale in the artifact** | Does either copy say why it differs? | [R2] — documentation in/with the source is an explicit evidence class; [R2] — a fork *"may even be labeled"* as one |

**Signal 4 is asymmetric and that asymmetry is the point.** A variant that states its rationale is
evidence *for* deliberation. Silence is **not** evidence for accident — it only removes the cheapest
signal and forces the reviewer down to 1–3. *(derived; [R2] establishes documentation as an evidence
class but nowhere claims its absence is evidence of anything.)*

---

## 5. Local grounding — measured in this repo, by this analyst

All commands run from the worktree root at commit **`a92e53a`** (`git rev-parse HEAD` →
`a92e53ae006700729881518e53f95e509a05a017`). Every count below was reached by **enumerating the
population and counting the enumeration**, per Research Standard §3.

**5.1 The verbatim ratchet holds 48 baseline entries, and passes.** `grep -cE '^\s*"[0-9a-f]{12}":'`
over [L1] prints `48`; `python3 -m pytest … -v` prints `2 passed in 0.04s` with both
`test_no_NEW_block_is_copied_between_children` and
`test_a_FIXED_duplication_is_removed_from_the_baseline` PASSED. *(definitive)*

**5.2 The child prompt corpus is 32 files; 7 filenames appear in more than one child.** Enumerated
with `find . -path '*/prompts/*.md' -not -path './prompts/*'` under `modules/assistant`, giving a
32-line list; grouping that list by basename and keeping groups spanning more than one child yields
exactly these seven, which are listed rather than counted: `altitude_component.md`, `from_plan.md`,
`new_branch.md`, `refine.md`, `stages_1_to_4_from_plan.md`, `stages_2_to_4.md`, `update_pr.md`.
*(definitive)*

**5.3 Two of those seven groups are byte-identical; five have drifted.** SHA-1 per copy:

| Group | Copies | Identical? |
|---|---|---|
| `from_plan.md` | `build_draft`, `build_draft_minor` — both `74a814bdb4ffab0bedfc32ae39bb5ee989659e08` | **yes** |
| `stages_1_to_4_from_plan.md` | `build_draft`, `build_draft_minor` — both `37e907af42b1…` | **yes** |
| `altitude_component.md` | `research_refresh` `a7a67777b622…` / `research_write` `49979cd62575…` | no |
| `new_branch.md` | `build_draft` `898726852bca…` / `build_draft_minor` `01d5f3b286a4…` / `plan_revision` `e8799d73fd26…` | no |
| `refine.md` | `build_refine` `c2b6777f2934…` / `build_refine_minor` `3f4d69dd81c9…` | no |
| `stages_2_to_4.md` | `build_refine` `5206ec6cdcba…` / `build_refine_minor` `6723203003d0…` | no |
| `update_pr.md` | `build_draft` `513d836a9d8e…` / `build_draft_minor` `1f2271142654…` / `plan_revision` `6b60d29da88e…` | no |

The `from_plan.md` pair's full SHA-1 is quoted from `sha1sum` output:
`74a814bdb4ffab0bedfc32ae39bb5ee989659e08  scripts/workflows/temporal/modules/assistant/build/build_draft/prompts/from_plan.md`.
*(definitive)*

**5.4 The drift here is dominated by whole-block presence/absence, not in-place rewording.**
Byte sizes from `wc -c` for two of the drifted groups: `update_pr.md` is **1,397 B** in `build_draft`
and **10,675 B** in `build_draft_minor`; `new_branch.md` is **1,451 B** in `build_draft` and
**7,419 B** in `build_draft_minor`. Grepping each file's bolded-lead and heading lines shows the
larger copies carry whole additional discipline sections (verification-of-asserted-facts,
worktree-CWD, read-before-edit) that the smaller copies do not contain at all. **This is [R4]'s
Type III shape, not its Type II shape** — the reportable class, not the filtered one. *(the sizes and
the structural observation are definitive; **the classification of this repo's corpus as Type III-shaped
is derived, and this paper does not rule on any specific pair** — see §6.5.)*

**5.5 GAP — the standard's near-duplicate figures are not reproducible as documented.** The three
similarity percentages appear in exactly two places, and I quote both in full:

> *"Three same-named prompts sit at 85.8%, 76.1% and 62.1% similarity to their siblings and NONE of
> them appears below."* — [L1], docstring line 35

> *"Three same-named prompts sit at 85.8%, 76.1% and 62.1% similarity to their siblings and none
> appears in the baseline."* — [L2], line 715

**Neither location names WHICH three prompts, and neither names the diffing method.** `grep -rn
"85\.8"` across the repo returns exactly those two lines. `grep -rln
"SequenceMatcher\|difflib\|similarity" --include=*.py scripts/ testing/` returns exactly one file —
[L1] — and it matches only on the word *similarity* in the prose above; **no similarity computation
exists anywhere in the repo.** The figures are therefore **unverifiable as stated**: a reader cannot
reproduce them, and cannot tell whether 85.8% was computed over characters, lines, tokens or blocks.
*(negative finding, with method. It is not a defect in the standard's argument — the argument does
not depend on the numbers — but the numbers are the thing a ruling will reach for first, and §3.3
says drift magnitude is not a signal anyone uses anyway.)*

**5.6 The promotion rule's extension to prompts is dated in git, not in the file.** [L2] states the
rule — *"This applies to prompt `.md` files exactly as it applies to modules"* and *"The rule was
stated for code, the paragraph below noted that we additionally ship prompts, and nobody extended it
across; the measured cost was 61 duplicated blocks carrying 25,270 bytes"* — and carries **no date**
for the extension. `git log --format='%ad %h %s' --date=short -- docs/standards/workflow-scripts.md`
shows `2026-08-17 0738899 standards(workflow-scripts): the promotion rule covers prompts, not just
modules`. **The extension landed today, 2026-08-17.** *(definitive — but note the correct source is
the git history; the assertion could not have been verified from the file's own text.)*

**5.7 The repo's documented failure mode is precisely the M1 default's blind spot.** [L1] and [L2]
both record it: *"`stages_1_to_4.md` and its `_from_plan` sibling forked, the plan variant never
received eleven testing rules, and every phase built from a plan ran without the instruction that
says how much rigour to apply … Nobody chose that. A copy simply stopped being updated, and no reader
could tell, because a copy and an original are the same file type."* [L2] Under [R1]'s default, that
divergence would have been classified **intentional**. *(definitive as to what [L2] records; the
application of [R1]'s default to it is derived.)*

---

## 6. Honest boundary analysis — the case against this paper

### 6.1 The ceiling is structural, and no amount of method removes it

[R1] defines the distinction as *"whether the developer is aware of the other clones."* Awareness is
not in the text. Every method in §2 except M1 estimates a correlate. **A reviewer working from two
texts is not recovering intent; they are forecasting co-evolution and calling the forecast intent.**
[U1 §9.2] already made the equivalent admission about its own claim: *"The co-evolution test is a
forecast, not a measurement."* This paper does not fix that; it moves the forecast from the future
to the past and inherits the same weakness.

### 6.2 κ = 0.271 is a small number and it bounds everything above it

Three experts, eleven categories, *"fair"* agreement [R3]. The four-signal ordering in §4.2 has no
measured reliability at all — it is an ordering over signals from studies that never combined them.
**A rule that produces confident-sounding rulings from these signals will produce confidently wrong
ones at a rate nobody here has measured**, and the only honest guard is that the ruling stays a human
judgement with its reasoning written down, which is where [L2] already put it.

### 6.3 The field's conservative default is SAFE FOR THEM AND UNSAFE FOR US *(derived — read this one carefully)*

[R1] defaulted inconclusive cases to *intentional and non-faulty* for a stated reason: it *"only
reduces the chances to positively answer the research question."* Their hypothesis was *inconsistent
clones cause faults*; defaulting toward "intentional" made their positive result harder to reach, so
it was conservative **for them**.

**Our decision has the opposite shape.** We are ruling on whether to merge copies. Defaulting to
"deliberate variant" preserves the copy, and preserving the copy is precisely the outcome [L2]
records as the documented harm — a rule that silently stopped applying to one branch of the fleet.
**Importing [R1]'s default without importing its rationale would be a methodological error**, and it
is a tempting one because it looks like deference to the literature. The default is not
direction-neutral; it is conservative with respect to a *research claim*, not with respect to a
*maintenance decision*. Stating this is not disagreement with [R1] — [R1] is explicit about why it
chose the direction it chose.

### 6.4 The transfer chain is now TWO hops, and the second one is weaker than the first

[U1 §9.2] already flagged its single largest validity threat: code clones in 300 kLOC–1 MLOC systems
versus a shelf of workflow scripts. This paper adds a hop: **code prose → prompt prose.** Only [R4]
and [R7] study prose at all, and:

- **[R4]'s mechanism may not be computable here.** Its referent is a Java method signature — a
  formal, machine-comparable object, which is what makes `compute-similarity(methodSignature,
  comment)` meaningful. A prompt block's referent is "the job this child does", which is itself
  prose. The fit-asymmetry signal may transfer as a *judgement* and not as a *computation*. Nothing
  in the corpus establishes that it transfers at all.
- **[R7] categorises content type, not intent** (§3.4). It corroborates that prose copies drift and
  are forgotten; it does not supply an intent discriminator.
- **[R5] does not transfer across projects.** Its own cross-project table reports recall as low as
  1.3% at threshold 0.1 in one direction [R5, Table 8]. The "train a classifier" path is closed at
  our scale — we have seven multi-child prompt groups (§5.2), not a training set.

### 6.5 Confirmation risk, named

The analyst writing this knew before starting that this repo's standard prefers sharing [L2], and
§5.4's observation — that local drift is whole-block presence/absence, [R4]'s reportable shape —
points the same way the standard already leans. **That is exactly the direction a biased reading
would produce.** Two guards were applied and neither is sufficient: §5.4's sizes and structure are
mechanically checkable by anyone re-running the commands, and **this paper rules on no specific
pair** — including the byte-identical `from_plan.md` pair of §5.3, which may be a legitimate
pending-fork, and which this paper deliberately does not adjudicate. The blind inter-rater trial in
§7.1 is the real guard, and it has not been run.

### 6.6 When this whole question does not need answering

- **When the copies are short-lived.** [U1 §9.1] carries the point from its own source [S19] (Kim et
  al., FSE 2005): refactoring short-lived clones may not be worthwhile, because they are likely to
  diverge very soon anyway. A prompt tree under active decomposition is that case. *(cited through
  [U1]; the Kim et al. paper was not independently fetched for this paper.)*
- **When the pair is byte-identical.** Then the existing verbatim ratchet [L1] already decides it and
  no judgement is needed; this paper's subject is only the drifted remainder.
- **When the two children genuinely do different jobs.** [L1]'s own docstring anticipates this — *"A
  child doing a genuinely different job may legitimately repeat a sentence."*
- **When the rationale is already written down.** Signal 4 short-circuits the other three.

### 6.7 Scope, held

Three findings surfaced that belong elsewhere and are named once and not pursued: whether the
current set of children is the right set is **Assistant Workflow Design**; whether a shared fragment
survives a resumed or retried run is **Temporal Integration**; and whether a given prompt block
makes a child better at its job is **Self Improvement**.

---

## 7. Test plan — what research cannot settle

Each item is a local experiment with what it decides. Items 1 and 2 are the ones that would move
this paper from derived to measured.

1. **Blind inter-rater trial.** Two reviewers independently classify each of the five drifted groups
   (§5.3) as deliberate-variant or neglected-copy from the texts alone, recording which of §4.2's
   four signals drove each call. Compute Cohen's κ. **Decides:** whether the §4.2 ordering is
   reproducible *here at all*, against [R3]'s κ = 0.271 as the field's benchmark. A κ near zero
   retires §4.2; a κ materially above 0.271 is the first evidence that the prompt case is *easier*
   than the code case, which no source predicts.
2. **Ground-truth validation — the check Kapser & Godfrey could not run.** After (1) is sealed,
   reveal the commit history for each pair and score the blind classifications against what actually
   happened. **Decides:** accuracy, not merely agreement. **This repo has an advantage the literature
   does not**: the history exists even though the ruling method must not consult it, so the artifact-only
   method can be validated rather than merely applied. No cited source performed this validation.
3. **Operationalise fit-to-referent.** Score each drifted block against the *role* of the child it
   sits in (e.g. an LLM judge given the child's entrypoint and stage list, asked how well the block
   fits), and check whether the asymmetry it reports matches the human ruling from (1). **Decides:**
   whether [R4]'s mechanism transfers to a referent that is prose rather than a method signature —
   the §6.4 threat, and the highest-value unknown in this paper.
4. **Classify the differing hunks.** For each drifted group, label every differing hunk as
   named-entity substitution, whole-block presence/absence, or in-place rewording, and test whether
   the label predicts the ruling from (1). **Decides:** whether §3.3's pattern signal holds locally.
   §5.4 suggests the population is dominated by one shape, which would make this a weak test until
   more variety exists — that itself is a result.
5. **Document the similarity method, or drop the figures.** Either publish the computation behind
   85.8% / 76.1% / 62.1% and name the three prompts, or remove the numbers from [L1] and [L2].
   **Decides:** whether the standard's near-duplicate claim is checkable by a reader. §3.3 says the
   magnitude is not a signal anyone uses, so *dropping* them costs the argument nothing.
6. **Manufacture signal 4 instead of inferring it.** Require any deliberate variant to carry a
   one-line `differs from <sibling> because <reason>`, and check after one quarter whether it was
   ever consulted in a ruling. **Decides:** whether the cheapest signal can be created rather than
   recovered. Same shape as [U1 §10, item 8]'s tracked-lineage probe and cheap enough to run
   alongside it.
7. **Cost the method.** Time one reviewer classifying one pair by §4.2. **Decides:** whether this is
   affordable per-pair at fleet scale, given [R2]'s own warning that the process was *"very time
   consuming in the beginning."* If it is not, the honest conclusion is that the ruling should be
   made once per *family* rather than once per *pair*.

---

## 8. Citations

**Source count: 13** — 9 external (7 peer-reviewed or archival, 1 first-party raw spec, 1 rendered
vendor page cited only for an absence), 1 upstream research paper, and 3 local first-party artifacts.
This sits at the small end of the Research Standard §2/§3 band **by design and is argued to be
sufficient**: the general question is already answered by [U1] at 24 sources and is not re-derived
here (§1.1); the residual question is single-concern; and §3.5 establishes by enumerated search that
one of the two literatures that could bear on it **does not exist yet**. Padding past this point
would mean citing commentary above first-party and peer-reviewed evidence, which §3 forbids. No
source was excluded for space.

### Peer-reviewed and archival research (PDFs fetched and text-extracted directly)

- **[R1]** E. Juergens, F. Deissenboeck, B. Hummel, S. Wagner — *Do Code Clones Matter?* ICSE 2009.
  https://teamscale.com/hubfs/Publications/2009-do-code-clones-matter.pdf — *fetched 2026-08-17;
  extracted with `pdftotext`. Read: §3 (RQ definitions), §5.2 (study description / developer rating
  procedure), §7.2 (internal validity), §8 (discussion). **Re-mined for the classification-method
  angle; [U1] cited this paper for its fault rates, which are not re-stated here.***
- **[R2]** C. J. Kapser, M. W. Godfrey — *"Cloning considered harmful" considered harmful: patterns
  of cloning in software.* Empirical Software Engineering 13(6), 2008.
  https://plg.uwaterloo.ca/~migod/papers/2008/emse08-ClonePatterns.pdf — *fetched 2026-08-17;
  extracted with `pdftotext -layout`. Read: §3 (pattern template, 3.1.3 Experimental Variation,
  3.2.4 Parameterized Code), §4.2 (classification criteria), §4.7 (threats to validity). **Re-mined
  for the retrospective-method angle; [U1] cited it for the four-group partition, which is not
  re-derived here.***
- **[R3]** N. Bettenburg, W. Shang, W. Ibrahim, B. Adams, Y. Zou, A. E. Hassan — *An Empirical Study
  on Inconsistent Changes to Code Clones at Release Level.* WCRE 2009.
  https://users.encs.concordia.ca/~shang/pubs/bettenburg-wcre09.pdf — *fetched 2026-08-17. Read:
  §III.D–E (manual inspection and classification method), §V Q3 (κ = 0.271). **Source of the only
  measured inter-rater reliability for retrospective clone-intent classification in this corpus.***
- **[R4]** A. Blasi, N. Stulova, A. Gorla, O. Nierstrasz — *RepliComment: Identifying Clones in Code
  Comments.* arXiv:2108.11205v1, 25 Aug 2021. https://arxiv.org/pdf/2108.11205 — *fetched
  2026-08-17. Read: abstract, §2 (comment-clone taxonomy), §3.2 (legitimacy heuristics), §3.3 +
  Algorithm 1 (severity computation). **The corpus's only implemented, precision-evaluated
  retrospective classifier operating on prose.***
- **[R5]** X. Wang, Y. Dang, L. Zhang, D. Zhang, E. Lan, H. Mei — *Can I Clone This Piece of Code
  Here?* ASE 2012.
  https://www.microsoft.com/en-us/research/wp-content/uploads/2016/07/caniclonethispieceofcodehere_ase2012.pdf
  — *fetched 2026-08-17. Read: §1 (harmful/harmless definitions), §3.2.1–3.2.3 (feature groups),
  §4 (ablation, Tables 5–6, cross-project Table 8), §5 (discussion of Kapser categories).*
- **[R6]** Z. Chen, C. Wang, W. Sun, X. Liu, J. M. Zhang, Y. Liu — *Promptware Engineering: Software
  Engineering for Prompt-Enabled Systems.* arXiv:2503.02400v2, 27 Jan 2026.
  https://arxiv.org/pdf/2503.02400 — *fetched 2026-08-17. Read: O24 (versioning and traceability).
  **Cited primarily as a NEGATIVE finding: full-text grep for `clone|duplicat` returns zero relevant
  hits — see §3.5.***
- **[R7]** S. Wagner, D. Méndez Fernández — *Analysing Text in Software Projects.*
  arXiv:1612.00164. https://arxiv.org/pdf/1612.00164 — *fetched 2026-08-17. Read: §4.4 (clone
  detection on non-code text), §5.2 (clone detection in 28 industrial requirements specifications,
  Tables 2–3). Book-chapter preprint; the underlying study is its reference [25], which was not
  independently fetched — **claims sourced here are attributed to this chapter's own text, not to
  the primary study.***

### First-party documentation (raw)

- **[R9]** Google Dotprompt — *partials specification.*
  `raw.githubusercontent.com/google/dotprompt/main/spec/partials.yaml` (fetched 2026-08-17;
  `default_branch` confirmed `main` via `api.github.com/repos/google/dotprompt` before fetching, and
  the 16 `partial`-matching repo paths enumerated via the git-tree API). *Cited as an existence
  proof of the shared-fragment primitive in a first-party prompt file format.*

### Consulted for an absence (not quoted, reduced confidence)

- **[R8]** Agenta — *Prompt Drift: What It Is and How to Detect It.*
  https://agenta.ai/blog/prompt-drift — *rendered vendor page read through a summarizing fetch,
  2026-08-17. **Cited ONLY for what it does not contain** (§3.5, item 2): it treats prompt drift as
  output-behaviour change over time and does not address divergence between separately-maintained
  copies. Not quoted anywhere in this paper, and no claim rests on it.*

### Upstream research paper (this repo)

- **[U1]** `docs/standards/architecture/research/raw/workflow_reuse_boundary.md` — *Where does the
  boundary between parameterizing one shared workflow and forking a second one fall…* `Last
  validated: 2026-08-03`; `Revalidate: high — 6 weeks`; `Critic: PASS-WITH-FIXES` (re-sourced the
  Tekton ClusterTask → `cluster` resolver replacement to the v1beta1→v1 migration guide; restored a
  dropped word in the PipelineResources quote; split a §5.1 quote synthesized from two passages).
  **Inside its revalidation window on 2026-08-17.** 24 sources.

### Local first-party artifacts (verified by command at commit `a92e53a`)

- **[L1]** `scripts/workflows/temporal/tests/unit/test_prompt_blocks_are_shared_not_copied.py` —
  the verbatim duplication ratchet and its docstring. Baseline enumerated at 48 entries; suite runs
  `2 passed`.
- **[L2]** `docs/standards/workflow-scripts.md` — § *A prompt block with two consumers is promoted,
  and a test enforces it* (line 705 ff.), and the promotion rule at line 38. Extension to prompts
  dated to commit `0738899` (2026-08-17) via `git log`, not from the file's own text.
- **[L3]** `docs/development/workflow-decomposition/roadmap.md` § Phase 2 — the unchecked item this
  paper feeds.
