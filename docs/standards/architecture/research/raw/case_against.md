# The Case Against the Thesis

```
Topic:          What are the strongest PUBLISHED arguments that this architecture is wrong,
                unnecessary, or premature? Written adversarially: the paper's job is the
                counter-position, not a balanced verdict.
Feeds:          docs/standards/architecture/problem-statement.md as a whole — every claim in
                it: the gap claim ("the industry made the artifacts durable, it did not make
                the loop durable"), the four-element combination, the affordability enabler,
                and the generality claim ("the backbone does not change; only the edge does").
                Read against docs/standards/architecture/system-overview.md for what is built.
Last validated: 2026-08-03
Revalidate:     high — 4 weeks
Confidence:     Four classes only, per §3 — definitive / directional / unverified / derived.
                "Rendered page — reduced confidence" is a MODIFIER on definitive, never a fifth
                class: it means the span was quoted verbatim from a fetched page that carries
                navigation and boilerplate, so it is usable as definitive but re-verify before
                building on it.
                DEFINITIVE on the vendor-shipped durable agent runtimes (§2.1). DEFINITIVE on
                the first-party Temporal non-determinism rule (§2.2), the Kubernetes level-based
                design principle (§2.5), the GitHub self-hosted-runner warning and the
                CVE-2025-30066 advisory (§2.6), the OpenAI Agent Builder deprecation (§5.2),
                and on the abstracts of the three arXiv results in §2.3 (fetched via arXiv API
                / arXiv HTML). DEFINITIVE (rendered page — reduced confidence) on the Anthropic,
                Cognition, Fowler, Metz, Chroma, DBOS and Glass quotations — all fetched, quoted
                conservatively, and marked at the point of use. DIRECTIONAL on Crash-Only
                Software and Daly (2006), whose primaries did not extract. DERIVED, and marked
                AT POINT OF USE as well as in the roll-up, on every transfer of a published
                result to this architecture — that transfer is the paper's own inference, never
                the source's. UNVERIFIED on the Cognition softening (§5.4), on the OpenAI
                AgentKit launch date (§5.2 — publisher page returned HTTP 403), and on the
                Dapr publication date and npm-worm material used only as corroboration.
                Eight negative findings in §6.1 with stated search method.
Critic:         PASS-WITH-FIXES (round 3: N6's dependent trace extended to durable_execution.md
                §3, where the same threshold appears unhedged; [S5]'s citation entry corrected to
                record the first-party GA verification; §2.1.2's element-count transfer marked
                derived at point of use) — 2026-08-03
```

> **Mixed volatility (§3).** The load-bearing section §2.1 is a **vendor product inventory**
> and is the fastest-decaying material in the pool — it moved three times between March and
> May 2026. The header takes that tier. §§2.4–2.6 (software-engineering fundamentals, CI/CD
> risk taxonomy, level-triggered control) are **low-volatility** and a refresh may skip them.
> §2.3's arXiv results are **medium** — replication, not withdrawal, is the expected change.

---

## 0. Headline: the gap claim was true when it was written and is not true now

The problem statement's load-bearing sentence is:

> "**The industry made the artifacts durable. It did not make the loop durable.**"

Between **2026-03-25 and 2026-05-28**, **three separate vendors** shipped products whose explicit,
first-party-documented job is making the agent *loop* durable — not the artifact — **and a fourth
ships the same pattern on a date this paper could not establish** (§2.1.4). One of the three is
Anthropic, in Claude Code, on the coding edge, **generally available**, and its announcement
describes **code-written orchestration scripts, saved progress that resumes an interrupted run,
adversarial cross-checking between agents, and convergence-based stopping** — four of the things
the problem statement enumerates as the combination nobody has put together (§2.1).

That is the single most damaging finding in this paper and everything else is smaller. It does
not say the architecture is worthless. It says the *sentence that motivates it* is a claim about
the state of the industry, that claims about the state of the industry decay, and that this one
decayed in under three months. **A thesis whose novelty rests on an industry gap needs a dated
gap and a revalidation schedule, and the problem statement carries neither.**

The rest of the paper ranks six further attacks by how much damage they do if true (§4).

---

## 1. Primer — what an adversarial paper is, and what it is not

### 1.1 Why this paper exists and what would make it dishonest

The Research Standard §3 requires every paper to carry a section arguing against its own thesis,
on the reasoning that a paper without one is advocacy. This pool satisfies that rule
paper-by-paper. It does not satisfy it *pool-wide*: eleven papers were commissioned by the party
who benefits from a favourable answer, and each one's honest-boundary section is scoped to its
own narrow question. Nobody had been asked to attack the frame.

Two failure modes are available to a paper with this brief, and both are worse than not writing
it:

1. **Manufacturing a counter-case.** Constructing plausible-sounding objections and dressing them
   as findings. Guarded against by the §3 **derived** marking: an argument this paper builds is
   marked derived and names the source claims it is built from. Nothing in §2 is presented as a
   citation unless a URL was fetched and the span was visible.
2. **Balancing.** Ending with "on balance the thesis holds." The synthesis balances, from this
   brief plus the other five papers. This paper's honest boundary (§5) is therefore *inverted*:
   it states where the counter-arguments fail, and it is written with the same rigour as §2.

### 1.2 The four claim classes under attack

| # | Problem-statement claim | Attack surface | Section |
|---|---|---|---|
| C1 | The industry made artifacts durable, not the loop | Falsifiable by product inventory; and by the argument that the loop *should not* be durable | §2.1, §2.5 |
| C2 | Durable execution is mature technology, borrowed not invented | Its costs are first-party documented and land on exactly the changes an LLM system makes constantly | §2.2 |
| C3 | Layering (author / judge / disposition) makes improvement real | Measured results where more actors did not help, and where judges are unreliable | §2.3 |
| C4 | "The backbone does not change; only the edge does" | Reuse-in-the-large is a documented mostly-unsolved problem; the rule of three; YAGNI | §2.4 |
| C5 | (implicit) A hand-built backbone is worth building | Provider-side runtimes are eating the layer | §2.1, §5.2 |
| C6 | "Nothing may assume a single operator" | Multi-participant edge topologies have documented, catalogued failure modes the design has not met yet | §2.6 |

### 1.3 What this paper does NOT re-derive

Per the dispatch's scope note, two pool papers already own material adjacent to §2.3 and are
**cited, not re-derived**:

- **`raw/convergence_stopping.md`** (Last validated 2026-08-03; Critic: PASS) — owns the
  plateau/stopping-rule literature, the judge-pathology corpus (CriticGPT, self-preference bias,
  sycophancy and LLM-REVal, in its §2.2.5), the "3–5 passes has no source" negative finding, and
  the measured per-pass recall figures. Where this paper needs a stopping or judge fact, it points
  there. *(Sibling papers are referenced by source name and section, never by their `[Sn]`
  numbers — those collide with this paper's own numbering and are a re-verification hazard.)*
- **`raw/reflection_literature.md`** (Last validated 2026-07-23; Critic: PASS) — owns the
  reflection corpus and its four named gaps.

What this paper brings that neither has: the **architectural** case against layering, and
**measured results where adding actors made outcomes worse under controlled compute** (§2.3).

---

## 2. The attacks, with the strongest published support located

### 2.1 C1 (a) — someone made the loop durable, and it was announced while this pool was being written

**This is the strongest attack in the paper, it is first-party, and three of its four data points
are dated.** Four independent implementations, listed oldest-announcement-first; the fourth
(§2.1.4) carries no establishable publication date and is treated as corroboration only.

**2.1.1 AWS — Bedrock AgentCore Runtime managed session storage, 2026-03-25.**

Verbatim from the AWS what's-new page: the feature is "managed session storage for persistent
agent filesystem state"; the persisted state includes "source files, installed packages, build
artifacts, and git history"; it survives stop and resume cycles; retention is "14 days of idle
time"; status "public preview" [S1]. AgentCore itself reached general availability on
**2025-10-13**, under the announcement title "Amazon Bedrock AgentCore is now generally
available" [S2].

*Confidence: **definitive** on the quoted spans (both first-party AWS announcement pages,
fetched). The persisted object here is a filesystem — closer to "durable artifact" than "durable
loop" — which is a limitation on this data point, not a strength.*

*(**DERIVED** — from [S1]'s enumeration of the persisted state ("source files, installed packages,
build artifacts, and git history") across stop/resume, set against the problem statement §*The gap
underneath it*: a persisted **working** filesystem across stop and resume is the resumption
primitive that section says the industry did not build. AWS makes no claim about the problem
statement; the equivalence is this paper's inference and is the weakest of the four in §2.1,
because a filesystem is not a loop.)*

**2.1.2 Cloudflare — Project Think, 2026-04-15.**

Verbatim: Project Think is "The next generation of the Agents SDK" introducing "a set of new
primitives for building long-running agents (durable execution, sub-agents, sandboxed code
execution, persistent sessions) and an opinionated base class that wires them all together"
[S3]. On the durability primitive: a fiber is "a durable function invocation: registered in
SQLite before execution begins, checkpointable at any point via `stash()`, and recoverable on
restart via `onFiberRecovered`" [S3]. The SDK's own README describes agents as "persistent,
stateful execution environments for agentic workloads, powered by Cloudflare Durable Objects,"
with state that "Syncs to all connected clients, survives restarts" [S4].

*Confidence: definitive on the quoted spans — [S3] is the first-party Cloudflare blog (rendered;
quotes kept to visible spans), [S4] is raw markdown from the first-party repo.*

**Note what that parenthesis contains: durable execution, sub-agents, persistent sessions —
bundled, in one vendor's base class.**

*(**DERIVED** — from [S3]'s primitive list quoted above, set against the problem statement §*What
we are combining, and why it is novel*: those three primitives correspond to **three of that
section's four enumerated elements**. Cloudflare enumerates primitives; it makes no claim about
the problem statement, and the element count is this paper's mapping, not the vendor's. The
correspondence is loosest on element 2 — "sub-agents" is a parallelism primitive, and the problem
statement's element 2 requires *distinct actors at distinct layers, one with no stake in the
work*, which [S3] does not claim.)*

**2.1.3 Anthropic — dynamic workflows in Claude Code, 2026-05-28.**

This is the one that lands closest. Verbatim from the first-party announcement:

> "Claude dynamically writes orchestration scripts that run tens to hundreds of parallel
> subagents in a single session, checking its work before anything reaches you." [S5]

> "Progress is saved as the run goes, so a job that's interrupted picks up where it left off
> instead of starting over." [S5]

> "Agents address the problem from independent angles, other agents try to refute what they
> found, and the run keeps iterating until the answers converge—which is how a workflow reaches
> results a single pass can't." [S5]

And on maturity, verbatim from the same page:

> "Dynamic workflows are now generally available" [S5]

> "…generally available in the Claude Code CLI, Desktop, and the VS code extension for Pro, Max,
> Team, and Enterprise plans, as well as on the Claude API, on Amazon Bedrock, Vertex AI, and
> Microsoft Foundry." [S5] *(leading ellipsis: the source sentence opens "Dynamic workflows are
> generally available in the Claude Code CLI…")*

Map the first three sentences onto the problem statement's own enumeration:

| Problem statement element | The 2026-05-28 announcement |
|---|---|
| 1. Durable execution — "a crash resumes rather than restarts" | "a job that's interrupted picks up where it left off instead of starting over" |
| 2. Layered self-improvement — "one that authors, one that judges" | "other agents try to refute what they found" |
| 3. Memory the *next step reads in code* | "Claude dynamically writes orchestration scripts" — the routing is a script |
| 4. High-level loops with an observable exit condition | "keeps iterating until the answers converge" |

*Confidence: **definitive (rendered page — reduced confidence)** that the announcement contains
those spans, all fetched from claude.com; the quotes are short and visible and no figure is
claimed. **The maturity label is first-party GA, quoted above.** An earlier draft of this paper
recorded it as "research preview per secondary reporting, not verified" — that was wrong, the
page states general availability outright, and the correction runs **in favour of** this finding:
a GA product is stronger evidence for D1 than a preview would be. **DERIVED** on the mapping
table: the equivalence is this paper's inference from [S5] and the
problem statement's own text, not Anthropic's claim. In particular "a single session" is a real
scope difference from a multi-day, multi-machine loop — see §5.3, which is where that difference
gets its full weight.*

**2.1.4 Dapr Agents — DurableAgent.**

First-party docs describe "Workflow-based execution using Dapr Workflows", "Persistent workflow
state management across sessions and failures", "Deterministic execution with checkpointing",
and state that "The conversation state and the execution are persisted and can resume across
failures or restarts" [S6]. **No publication date is establishable** — treated as corroboration of
the pattern's spread, not as a dated data point. *(The page foots with "Last modified August 3,
2026", which is a modification date on living documentation and says nothing about when the
DurableAgent capability shipped. **Unverified** as to date; the quoted capabilities are
definitive.)*

**2.1.5 What this collectively establishes, and what it does not.**

*Establishes (**definitive**, and this is the whole of what the sources say):* as of 2026-08-03,
at least three major platform vendors ship, under dated first-party documentation, a runtime in
which an interrupted agent run resumes rather than restarts. One of the three is generally
available. That is a fact about four fetched pages ([S1], [S3], [S5], and [S2] for the GA date)
and nothing more.

*(**DERIVED** — from [S1], [S3] and [S5] set against the problem statement § *The gap underneath
it*: **the distinction between "durable artifact" and "durable loop" no longer separates this
architecture from the market.** This is an inference about *this architecture's position*, not a
claim any of the three vendors makes, and it is the sentence in this paper most likely to be
lifted forward into the synthesis. It is qualified immediately below and again, more heavily, in
§5.3 — a consumer that carries this sentence without §5.3 has mis-carried it.)*

*Does not establish (stated so the finding is not over-read):* that any of them is durable in the
Temporal sense (event-sourced deterministic replay). Cloudflare's fibers are checkpoint-and-
recover; AgentCore persists a filesystem; Anthropic's wording ("picks up where it left off") does
not specify a mechanism. The pool's `durable_execution.md` §4 already records that checkpointing
is not durable execution, and Diagrid argues the same about LangGraph/CrewAI/ADK [S7] — a
distinction which, note, is drawn by a *vendor of the alternative*. **The honest form of this
attack is therefore not "durable loops are solved" but "the loop-vs-artifact framing no longer
marks a gap; the remaining gap is a much narrower engineering claim about replay semantics that
the problem statement does not make."**

### 2.2 C2 — the durable-execution cost case, from first-party sources

**2.2.1 The determinism tax is real, first-party, and lands on the changes an LLM system makes
most often.**

Temporal's own diagnostic rule TMPRL1100 states verbatim:

> "A non-determinism error occurs if, during workflow replay, the system determines a different
> set of commands was generated by the workflow code than is expected based on the events from
> the last code run." [S8]

and names the two causes: "there is non-deterministic code causing a different path to be
traversed, **or a code change happened that took a different path for past workflow code**"
[S8]. The remedies are "patching new code changes to preserve past execution paths",
"implementing worker versioning", or fixing the code and resetting workflows [S8]. Replay is
triggered "when a worker needs to resume a workflow that is no longer cached (e.g. on worker
crash or workflow cache eviction)" [S8].

**DERIVED consequence, from [S8] plus this repo's own change pattern.** The second cause — a code
change taking a different path for in-flight workflows — is the *normal operating mode* of an
agentic system under continuous improvement. The improvement loop this repo treats as its thesis
(`system-overview.md` § *The improvement loop*) produces exactly one kind of output: changes to
the logic that runs. If that logic lives in workflow code, every accepted improvement is a
versioning event for every in-flight run. Note precisely what is and is not claimed: an LLM call
placed in an activity is *not* a determinism hazard (its result is recorded), and Temporal says so
[S9]. The hazard is **branching on it in workflow code and then changing the branch** — which is
what element 3 ("a parent can branch on what a child concluded") proposes to do.

*Confidence: definitive on [S8]'s wording (raw markdown, first-party repo). Derived on the
consequence — no source located makes this argument about self-improving systems specifically
(see negative finding N1).*

**2.2.2 Temporal's own marketing confirms the objection is widespread.**

Temporal published a rebuttal post whose framing is the objection: developers say "We can't use
Temporal for our AI agent. LLMs are inherently non-deterministic and our agent doesn't follow a
predefined path... And since Temporal requires determinism we can't use it for our very clever
and dynamic agents" [S9]. Temporal's answer: "Temporal's determinism requirement doesn't limit
the behavior of your agent, it's actually what makes AI agents reliable in production" [S9].

*Confidence: definitive that Temporal published this characterisation of the objection; the
objection itself is presented by Temporal as paraphrase, not quoted from an original source, so
it is **unverified** as anyone's specific stated position. Its evidentiary value is narrow but
real: **the vendor considers the objection common enough to answer**.*

**2.2.3 The server tier is a real operational tier.**

Temporal's own architecture doc enumerates four internal services — "Frontend Service", "History
Service", "Matching Service", "Internal Workers Service" [S10]. The competing vendor DBOS builds
its entire positioning on the cost of that: "DBOS is a library you install, not a service you
run"; "Temporal requires extra infrastructure and a rearchitecture of your application"; "No
cluster to provision, no orchestration server"; "Unlike Temporal, which requires a separate
orchestration server and Cassandra data cluster to host, DBOS runs as a library inside your
existing application" [S11].

*Confidence: definitive on [S10] (raw first-party markdown) for the component list — note the
fetched section does **not** state database requirements, so the "Cassandra cluster" claim rests
on [S11] alone. [S11] is **definitive (rendered page — reduced confidence)** on its own wording
and is **vendor competitive marketing**, marked as such; it is used as
evidence that a published architectural argument against the server tier exists, not as a neutral
cost estimate. Third-party cost figures for self-hosting were located only on
commentary/affiliate sites and are **not cited** — see N6.*

**2.2.4 What was NOT found: a horizon threshold from a first party.** See N6.

### 2.3 C3 — the architectural case against layering, and measured results where more actors were worse

The pool already establishes that judges are biased and that same-context self-review is the
worst option (`convergence_stopping.md` §2.2.5, §2.2.1). This section brings what it does not
have.

**2.3.1 Under matched compute, single agents match or beat multi-agent systems. (The strongest
measured result located.)**

Tran & Kiela, 2026-04-02, verbatim from the abstract:

> "Recent work reports strong performance from multi-agent LLM systems (MAS), but these gains are
> often confounded by increased test-time computation. When computation is normalized,
> single-agent systems (SAS) can match or outperform MAS..." [S12]

> "We find that SAS consistently match or outperform MAS on multi-hop reasoning tasks when
> reasoning tokens are held constant." [S12]

> "...many reported advantages of multi-agent systems are better explained by unaccounted
> computation and context effects rather than inherent architectural benefits" [S12]

The paper also reports identifying "significant artifacts in API-based budget control
(particularly in Gemini 2.5) and in standard benchmarks, both of which can inflate apparent gains
from MAS" [S12]. Three model families (Qwen3, DeepSeek-R1-Distill-Llama, Gemini 2.5) [S12].

*Confidence: definitive on the abstract (fetched via the arXiv Atom API). **Directional** as a
result — the tasks are multi-hop reasoning, not review or defect-finding, and §5.5 states why
that limit matters.*

**2.3.2 More calls can make a compound system worse — measured, and explained.**

Chen et al., verbatim from the abstract:

> "We find, surprisingly, that across multiple language tasks, the performance of both Vote and
> Filter-Vote can first increase but then decrease as a function of the number of LM calls." [S13]

The explanation offered is query-difficulty heterogeneity: more calls help easy queries and hurt
hard ones, and a task containing both produces the non-monotone curve [S13].

*Confidence: definitive on the abstract (fetched from the arXiv LaTeX-derived HTML). This is a
result about **aggregation-by-voting**, not about author/judge separation — transfer is not
claimed.*

**2.3.3 Multi-agent systems fail for reasons that are structural, not tuning.**

Cemri et al., verbatim from the abstract: "Despite enthusiasm for Multi-Agent LLM Systems (MAS),
their performance gains on popular benchmarks are often minimal" [S14]. The taxonomy is built
from "1600+ annotated traces collected across 7 popular MAS frameworks" and "150 traces, guided
closely by expert human annotators and validated by high inter-annotator agreement (kappa =
0.88)", yielding "14 unique modes, clustered into 3 categories: (i) system design issues, (ii)
inter-agent misalignment, and (iii) task verification" [S14].

**The architectural point is the taxonomy's shape.** Two of the three categories — inter-agent
misalignment and task verification — are failures that *do not exist* in a single-agent system.
They are created by the decision to layer. *(Confidence: definitive on the abstract, fetched via
arXiv API; **derived** on the "created by layering" reading — the authors do not frame it that
way.)*

**2.3.4 The best-known practitioner argument against layering is about context, not cost.**

Cognition's position paper states two principles: "Share context, and share full agent traces,
not just individual messages" and "Actions carry implicit decisions, and conflicting decisions
carry bad results" [S15]. Its diagnosis: "the decision-making ends up being too dispersed and
context isn't able to be shared thoroughly enough between the agents" [S15]; parallel subagents
"cannot see what the other was doing and so their work ends up being inconsistent with each
other" [S15].

**DERIVED — and the extrapolation here is larger than it looks, so it is stated in full.** [S15]
is about **parallel coding subagents making conflicting implementation decisions**: agents that
*act*, concurrently, on the same artifact. The problem statement's element 2 is a different
shape — a **judge that only reads and rules**, sequentially, with no authoring authority. This
paper's inference, built from [S15]'s "dispersed" decision-making and its "cannot see what the
other was doing" finding plus the problem statement's "one that judges with no stake in the work",
is that the same mechanism should reach the judging case: *a judge with no stake in the work is
also a judge with none of the author's context, and the seam that removes bias also removes
information.* **Cognition does not say this.** The transfer from concurrent actors to a sequential
reader is unestablished, and it is the reason this finding is ranked last (D7) rather than higher.

*Confidence: **definitive (rendered page — reduced confidence)** on the four quoted spans, all
fetched from the first-party Cognition blog; **derived**, as marked above, on everything after
them. Note the derived reading cuts directly against the pool's own `convergence_stopping.md`
§2.2.1 finding that removing production history **improves** review F1; the two are in genuine
tension and §5.5 does not resolve it in the thesis's favour by fiat.*
**Cognition has since softened this position — see §5.4, which is the honest boundary.**

**2.3.5 The vendor most invested in multi-agent publishes the cost multiplier and the anti-pattern.**

Anthropic's own guidance states "In our testing, multi-agent implementations typically use 3-10x
more tokens than single-agent approaches for equivalent tasks"; that in the anti-pattern case
"improved prompting
on a single agent achieved equivalent results"; and "Outside these situations, the coordination
costs typically exceed the benefits" [S16]. Its general engineering guidance is to "find the
simplest solution possible, and only increasing complexity when needed", to have developers
"start by using LLM APIs directly: many patterns can be implemented in a few lines of code", and
notes "Agentic systems often trade latency and cost for better task performance" [S17].

*Confidence: **definitive (rendered page — reduced confidence)** — first-party pages, fetched,
short verbatim spans.
Note the 3-10x figure in [S16] and the widely-repeated 15x figure from Anthropic's 2025
multi-agent-research post are different numbers from different pages; only [S16] was fetched, so
only 3-10x is cited here.*

**2.3.6 Judge unreliability is quantified, not anecdotal.**

Ye et al., verbatim: "we identify 12 key potential biases and propose a new automated bias
quantification framework-CALM"; "the results indicate that while advanced models have achieved
commendable overall performance, significant biases persist in certain specific tasks";
"there remains room for improvement in the reliability of LLM-as-a-Judge" [S18].

*Confidence: definitive on the abstract (arXiv abs page, fetched). Complements — does not
duplicate — `convergence_stopping.md` §2.2.5, which covers self-preference, sycophancy and
review-score inflation.*

**2.3.7 The affordability argument makes this worse, not better (DERIVED).**

The problem statement argues flat-rate subscription billing makes wasteful loops free, so
"being wrong costs nothing but time." Set against [S12]: if multi-agent gains are "better
explained by unaccounted computation" [S12], then a billing model that hides computation from
the operator **removes the signal that would have revealed the layering was buying nothing**. A
metered operator sees a 3-10x bill [S16] and asks whether the layers earn it; a flat-rate operator
does not. *(Derived from [S12], [S16] and the problem statement's own § Affordability. No source
located makes this argument — see N5.)*

### 2.4 C4 — the generality claim, which has the least evidence and the oldest counter-evidence

The claim under attack: *"The backbone does not change; only the edge does,"* with the shared
workflow library named as "the genuinely novel artifact." One edge exists. Zero others.

**2.4.1 The exact artifact class is a documented mostly-unsolved problem.**

Robert Glass, *Facts and Fallacies of Software Engineering*, verbatim from the publisher's
authorized chapter excerpt:

> **Fact 16:** "Reuse-in-the-large (components) remains a mostly unsolved problem, even though
> everyone agrees it is important and desirable." [S19]

> **Fact 18:** "There are two 'rules of three' in reuse: (a) It is three times as difficult to
> build reusable components as single use components, and (b) a reusable component should be
> tried out in three different applications before it will be sufficiently general to accept
> into a reuse library." [S19]

> **Fact 15:** "Reuse-in-the-small (libraries of subroutines) began nearly 50 years ago and is a
> well-solved problem." [S19]

> **Fact 17:** "Reuse-in-the-large works best in families of related systems and thus is
> domain-dependent. This narrows the potential applicability of reuse-in-the-large." [S19]

**Fact 17 is the one aimed squarely at "only the edge does."** The roadmap's edge list is coding,
home automation, industrial automation, robotics and bioinformatics. **That is not a family of
related systems** — it is a deliberately maximal spread across unrelated domains, chosen to
demonstrate generality. Glass's finding is that the spread is exactly what makes
reuse-in-the-large fail, and that the successful cases are the narrow ones. **The generality
claim's breadth, which is presented as the evidence for the backbone's value, is on Glass's
account the strongest predictor that it will not hold.** *(**DERIVED** on the reading — Glass
does not discuss agent backbones; the inputs are Fact 17 [S19] and the roadmap's own edge list in
problem-statement.md § *Where this repo sits*.)*

**Read Fact 18(b) against the roadmap.** The generality claim asserts a backbone stable across
coding, home automation, industrial automation, robotics and bioinformatics, on the evidence of
**one** application. Glass's threshold for calling a component general enough to *enter a library*
is three. **The problem statement is one-third of the way to the evidence bar for the artifact it
names as its contribution.**

Read Fact 15 against Fact 16, and the claim's shape gets worse: the well-solved case is
*reuse-in-the-small*, subroutine libraries. `system-overview.md`'s `activities/` and `common/`
layers are reuse-in-the-small and are on the solved side. The *composable workflow modules one
person writes and another uses without rewriting* — the named novel artifact — is
reuse-in-the-large, the unsolved side.

*Confidence: **definitive (rendered page — reduced confidence)** on all four quoted Facts (15, 16,
17, 18), each fetched from InformIT, the publisher's own excerpt of the book text — a rendered
page, but an authorized reproduction of a primary text, and the Fact numbers were checked against
it. **DERIVED** on every transfer: Glass (2002) is about compiled software components, not
markdown workflow modules invoked by shell scripts, and §5.6 states why that transfer is
contestable.*

**2.4.2 Speculative generality has a named cost model.**

Fowler's Yagni entry gives four costs of building a presumptive capability — build, delay, carry,
repair — of which the one that binds here is **cost of carry**: "The code for the presumptive
feature adds some complexity to the software, this complexity makes it harder to modify and
debug" [S20]. And on the case where the capability *is* eventually needed but differently: "You
often realize that a feature coded six months ago wasn't done the way you now realize it should
be done" [S20].

**DERIVED, and this is the sharpest form of the attack on C4.** The problem statement makes
cost-of-carry *binding policy*: "Nothing may assume a single operator" and "Nothing may assume
the coding edge" are standing constraints on every design decision made today, justified by edges
that do not exist. Yagni's cost-of-carry is normally a property of code; here it has been promoted
to a rule that constrains all future code. **If the second edge arrives in a shape the abstraction
did not anticipate — Fowler's "wasn't done the way you now realize it should be done" — the
carrying cost was paid on every decision in between, and the repair cost is still owed.**
*(Derived from [S20] and the problem statement § What this means for anything built here.)*

**2.4.3 The wrong abstraction is more expensive than the duplication it replaced.**

Metz's essay states the claim this paper needs verbatim: "duplication is far cheaper than the
wrong abstraction" [S21], and prescribes "When dealing with the wrong abstraction, the fastest way
forward is back" [S21] — inline the abstraction, re-introduce duplication, delete what each caller
does not need. The described failure sequence is an abstraction extracted from one case, then
parameterised repeatedly by later callers until it is incomprehensible [S21].

*Confidence: **definitive (rendered page — reduced confidence)** on the two quoted spans, fetched.
**DERIVED** on the mapping: a backbone/edge split extracted from a single edge is exactly the "extracted from
one case" starting condition [S21] describes. Note the pool's own
`raw/workflow_reuse_boundary.md` covers the parameterise-vs-fork ruling — this paper does not
re-open it and takes no position on it.*

**2.4.4 What could not be found.** No documented post-mortem of a domain-general agent or
workflow platform that failed to generalise across domains was located — see **N2**. This is the
attack line the brief expected to be sharpest, and **the sharpest available material for it is
2002-vintage software-engineering fact and 2016-vintage refactoring essay, not a modern case
study.** That is itself a finding: C4 is under-evidenced on *both* sides.

### 2.5 C1 (b) — the loop does not need to be durable, because re-derivation beats resumption

This is the weaker half of the C1 attack, and the paper says so up front: the published record
supporting *restart-over-resume for agents specifically* is thin (**N1**). What exists is a
strong general-systems argument by analogy.

**2.5.1 The largest deployed control system in the industry is built on the opposite principle.**

Kubernetes' architectural design principles, verbatim:

> "Functionality must be *level-based*, meaning the system must operate correctly given the
> desired state and the current/observed state, regardless of how many intermediate state updates
> may have been missed. **Edge-triggered behavior must be just an optimization.**" [S22]

> "Components should be self-healing. For example, if you must keep some state (e.g., cache) the
> content needs to be periodically refreshed, so that if an item does get erroneously stored or a
> deletion event is missed etc, it will be soon fixed, ideally on timescales that are shorter
> than what will attract attention from humans." [S22]

> "Don't assume a component's decisions will not be overridden or rejected... Retry, but back off
> and/or make alternative decisions." [S22]

Kubernetes' own concept documentation frames the controller as a "control loop": "In robotics and
automation, a _control loop_ is a non-terminating loop that regulates the state of a system"
[S23].

**DERIVED, from [S22] and [S23].** A level-based system does not resume; it re-observes and
re-derives. It needs no event history because the world *is* the history. Applied here: a
workflow that can re-read the repo, the PR thread and the issue list can re-derive where it is
without a durable execution log — and `system-overview.md` already says memory works this way
("No state files, no bookmarks. **Open is the to-do bit.**"). **The system as built is
level-triggered; the roadmap's next phase is to make it edge-triggered and durable. [S22] says
the arrow should point the other way, and calls the edge-triggered form "just an optimization."**
*(This is the paper's own inference. No source located applies level-triggered design to LLM
agent loops — N1.)*

**2.5.2 Restart-as-recovery has a named tradition; its primary did not extract.**

Candea & Fox's *Crash-Only Software* (HotOS IX, 2003) argues for systems whose only stop is a
crash and whose only start is recovery, on the reasoning that separate shutdown/recovery paths are
rarely exercised and therefore unreliable [S24]. **The primary text could not be quoted**: three
hosted PDFs returned unparsed binary and the USENIX HTML returned HTTP 403 (N4). The
characterisation above rests on search-corroborated summaries. **Directional; no verbatim quote is
offered and none should be inferred.**

**2.5.3 Checkpointing pays only above a failure-rate threshold; the primary did not extract.**

The Young/Daly result gives an optimum checkpoint interval as a function of checkpoint write cost
and mean time between failures — i.e. **checkpointing is a cost-benefit calculation against a
failure rate, not an unconditional good** [S25]. The primary PDF did not extract (N4); the
formula quoted in search results is not reproduced here because it could not be verified from the
paper. **Directional. Its use here is limited to the shape of the argument: durability has an
optimum, and below the relevant failure rate the optimum is "don't."**

**2.5.4 A fresh context can beat a resumed one — and this is already in the pool.**

`convergence_stopping.md` §2.2.1 reports a controlled experiment in which a fresh-context review
outscored same-session self-review (F1 28.6% vs 24.6%, p=0.008, d=0.52) and in which reviewing
twice in the same session was the **worst** of four conditions. Independently, Chroma's context-rot
study of "18 LLMs, including the state-of-the-art GPT-4.1, Claude 4, Gemini 2.5, and Qwen3 models"
reports that "models do not use their context uniformly; instead, their performance grows
increasingly unreliable as input length grows" [S26].

**DERIVED, from `convergence_stopping.md` §2.2.1 and [S26].** Resumption restores accumulated
context. Both results say accumulated context is a liability for evaluation work. **For the
specific workload this repo runs — review, critique, disposition — "resume with everything you
had" may be strictly worse than "restart clean against the artifact," which is what the system
already does.** §5.7 states where this argument stops.

*Confidence on [S26]: **definitive (rendered page — reduced confidence)** — first-party research
page, fetched, short verbatim spans.*

### 2.6 C6 — the multi-tenant edge topology has a catalogued failure model it has not met

The problem statement forbids assuming a single operator. Everything built assumes one. The
question is whether the second participant introduces failure modes the single-operator design
cannot anticipate. **The published answer is yes, and it is a standard risk taxonomy.**

**2.6.1 The exact topology — a worker on a participant's own machine, running shared workflow
modules — is the one GitHub tells you not to build across trust boundaries.**

GitHub's documentation reusable, verbatim in full:

> "We recommend that you only use self-hosted runners with private repositories. This is because
> forks of your public repository can potentially run dangerous code on your self-hosted runner
> machine by creating a pull request that executes the code in a workflow." [S27]

*Confidence: definitive — raw markdown from the first-party github/docs repo.*

**DERIVED.** An edge worker executing workflow modules authored elsewhere is structurally the
self-hosted-runner-plus-untrusted-workflow pattern. The credential that "never leaves the edge" is
present on the machine executing another participant's module. **Credentials staying at the edge
bounds where the secret is stored; it does not bound what runs next to it.**

**2.6.2 The risk has a catalogue entry and it names the credential problem.**

OWASP's CI/CD risk taxonomy, verbatim: "The PPE vector abuses permissions against an SCM
repository, in a way that causes a CI pipeline to execute malicious commands" [S28]; impact
includes "Access to any secret available to the CI job, such as secrets injected as environment
variables or additional secrets stored in the CI" [S28]; and "Being responsible for building code
and deploying artifacts, CI/CD systems typically contain dozens of high-value credentials and
tokens" [S28].

*Confidence: definitive — raw markdown from the first-party OWASP project repo.*

**2.6.3 The shared-library blast radius is not hypothetical; it has a CVE and a count.**

GitHub's own advisory for CVE-2025-30066, verbatim: "A supply chain attack compromised the
tj-actions/changed-files GitHub Action, impacting over 23,000 repositories. Attackers
retroactively modified multiple version tags to reference a malicious commit, exposing CI/CD
secrets in workflow logs." Severity High (CVSS 8.6); affected versions ≤ 45.0.7; published
2025-03-15 [S29]. CISA issued an alert on 2025-03-18 [S30]. A separate 2025 incident, the
self-replicating "Shai-Hulud" npm worm, propagated through maintainer credentials across hundreds
of packages [S31].

*Confidence: definitive on [S29] (GitHub Advisory Database — first-party for the advisory text,
rendered page, short verbatim span). [S30] is cited by URL only: the CISA page returned HTTP 403
and its content was **not** fetched — the alert's existence and date come from search results and
are **unverified**. [S31] is corroborated industry reporting, counts vary by source and are not
quoted; used only to establish that credential-propagating worms in shared package ecosystems are
a realised, not theoretical, class.*

**DERIVED, and this is the load-bearing inference of §2.6.** The problem statement names the
shared workflow library as "the genuinely novel artifact." [S28] and [S29] say that a shared,
versioned, cross-organisation library of executable pipeline modules is **a named attack vector
with a realised 23,000-repository incident**. **The artifact identified as the contribution is the
same artifact identified by the risk taxonomy as the blast-radius amplifier**, and the
single-operator system has no governance surface for it — `system-overview.md` lists no module
signing, no pinning discipline, no provenance, and no per-edge trust model, because with one
participant none is needed.

**2.6.4 The credential-permission question is answered elsewhere in the pool and is not re-derived
here.** Whether subscription auth at the edge is *permitted* is `raw/anthropic_tos_and_enterprise.md`
(Last validated 2026-07-24; Critic: PASS; **in window** — a 4-week interval puts it due 2026-08-21,
so §5's staleness gate does not fire and it is consumable as current evidence). This paper's point
is orthogonal: permission is not governance.

---

## 3. Comparative landscape — how strong each counter-position actually is

Stated fairly, including where the counter-position is weak. Ordered as in §2.

| Counter-position | Best available support | Evidential strength | Where it is weakest |
|---|---|---|---|
| **The gap claim is factually stale** | Four first-party vendor announcements, three dated Mar–May 2026 [S1][S3][S5][S6] | **Strongest in the paper.** First-party, dated, multiple independent vendors | None of the four is multi-participant or credential-at-edge; Anthropic's is scoped to "a single session" [S5] |
| **The loop should not be durable** | Kubernetes level-based principle [S22]; crash-only tradition [S24]; context-rot [S26] + pool §2.2.1 | **Weak as published evidence, strong as architecture.** No source applies it to agent loops (N1) | The most-cited practitioner manifesto asks for the opposite (§5.1) |
| **Durable execution's costs bite here specifically** | TMPRL1100 [S8]; Temporal's own rebuttal post [S9]; DBOS positioning [S11] | **Moderate.** The mechanism is first-party; the transfer is derived | Temporal's answer (put nondeterminism in activities) is real and largely works; the residue is narrower than the attack implies (§5.2) |
| **Layering does not pay** | Matched-budget SAS≥MAS [S12]; non-monotone call scaling [S13]; MAST [S14]; Cognition [S15]; Anthropic's own 3-10x [S16] | **Moderate-to-strong on cost; weak on transfer** | Every measured result is on reasoning/QA benchmarks; the pool's own review-topology results point the other way (§5.5) |
| **The generality claim is premature** | Glass Facts 15/16/**17**/18 [S19] — **Fact 17 (reuse-in-the-large is domain-dependent and works best in families of related systems) is the one aimed squarely at "only the edge does"**; Yagni [S20]; wrong abstraction [S21] | **Strong in principle, thin in evidence.** No modern post-mortem located (N2) | All three sources predate LLM-authored code, which changes the cost of building the second implementation (§5.6) |
| **Multi-tenant edges fail in ways this cannot anticipate** | GitHub first-party warning [S27]; OWASP PPE [S28]; CVE-2025-30066 [S29] | **Strong on the mechanism.** Realised incidents, first-party sources | All evidence is from *open, untrusted-contributor* ecosystems; a closed trusted org is a different threat model (§5.8) |
| **The platforms will eat this** | [S1][S3][S5]; AgentCore GA [S2] | **Moderate.** The trend is real and dated | OpenAI announced Agent Builder's deprecation on 2026-06-03, roughly eight months after its DevDay launch [S32] — platform durability is itself unreliable (§5.2). *[S32] documents only the deprecation; the launch date is unverified — see §5.2.* |

**Two observations from the landscape, both derived.**

1. **The counter-case is strongest exactly where the problem statement is most specific and
   time-indexed** (the industry-gap claim), and weakest exactly where the problem statement is
   most abstract (whether a loop *ought* to be durable). A thesis is normally attacked in the
   reverse order. This asymmetry means the durable revision to the problem statement is not "drop
   the gap claim" but "date it and cite it."
2. **No published source located attacks the specific combination.** Every counter-argument in
   this paper attacks one element in isolation. That is a real gap in the adversarial literature
   and it is stated as N3, not converted into a point in the thesis's favour — absence of a
   published attack on a combination almost nobody has attempted is not evidence the combination
   works.

---

## 4. What this provides — the ranked damage list

Enumerated, each with source, confidence, and **what breaks in the problem statement if it is
true**. Ranked by damage, most damaging first.

**D1. The gap claim is falsified as a present-tense statement about the industry.** **Three
vendors, on dated first-party announcements between 2026-03-25 and 2026-05-28**, ship runtimes in
which an interrupted agent run resumes rather than restarts [S1][S3][S5]; a fourth ships the same
pattern undated [S6]. Anthropic's 2026-05-28 announcement — **generally available**, not a preview
— covers four of the problem statement's enumerated elements at once, on the coding edge [S5].
*Confidence: definitive on the announcements and on the GA label; **derived** on the mapping of
those announcements onto the problem statement's four elements (§2.1.3) and on the market
conclusion (§2.1.5).*
**Breaks:** the § *The gap underneath it* section entire, and the framing of § *What we are
combining, and why it is novel* as a present-tense novelty claim.
**Remedy:** date the claim ("as of <date>"), cite it, and put it on the highest revalidation tier
— the sentence is a market observation wearing a thesis's clothes.

**D2. The named novel artifact is the artifact class the field calls mostly unsolved, and it has
one-third of the evidence its own discipline's rule of three requires.** Glass Facts 16 and 18
[S19].
*Confidence: definitive on the quotes; derived on the transfer.*
**Breaks:** "The backbone does not change; only the edge does," and the claim that the shared
workflow library is a reachable contribution rather than an aspiration.
**Remedy:** treat the generality claim as a hypothesis with a stated falsification test (§7 T3),
not as a standing constraint on today's decisions.

**D3. Multi-agent gains may be an artifact of unmetered compute, and flat-rate billing hides
exactly the signal that would reveal it.** [S12] with [S16]; derived joint.
*Confidence: definitive on [S12]'s abstract; derived on the affordability interaction.*
**Breaks:** element 2's claim that layering "is what makes the improvement real," and the §
*Affordability* claim that being wrong costs nothing but time.
**Remedy:** instrument token cost per layer even though it is not billed (§7 T2). Free is not the
same as costless when the cost is the evidence.

**D4. The determinism/versioning tax lands on the change the improvement loop produces most
often.** [S8]; derived consequence.
*Confidence: definitive on TMPRL1100; derived on the transfer to a self-improving system.*
**Breaks:** "Mature technology, borrowed rather than invented" as a statement that the cost is
already paid. It is mature; the cost is not zero and is concentrated where this system moves.
**Remedy:** decide before the port whether branch logic lives in workflow code (versioned, replay-
hazardous) or in activities/data (cheap to change). This is a fork, not a detail.

**D5. The shared workflow library is a catalogued blast-radius amplifier, and no governance
surface exists for it.** [S27][S28][S29].
*Confidence: definitive on all three sources; derived on the mapping to edge workers.*
**Breaks:** "Multi-tenancy comes from everyone authenticating locally" as a sufficient security
story. It answers *where the secret lives*, not *what executes beside it*.
**Remedy:** module provenance/pinning is a design requirement of the library, not a hardening pass
after it exists.

**D6. The system as built is level-triggered, and the roadmap's next step makes it
edge-triggered — which the most widely deployed statement of this design principle calls "just an
optimization."** [S22][S23]; derived.
*Confidence: definitive on the quotes; **derived and unsupported by any agent-specific source** on
the transfer (N1).*
**Breaks:** the ordering of the roadmap, not the thesis. Durable execution may be the right
second step rather than the right first one.
**Remedy:** run T1 (§7) — measure what a crash actually costs today before buying durability.

**D7 (DERIVED, weakest of the seven). A separate judge may lose the author's context, because
dispersed decision-making is a named failure mode for concurrent agents.** [S15]; [S14]'s
taxonomy shape. The transfer from concurrent acting subagents to a sequential judge is this
paper's inference and is unestablished (§2.3.4).
*Confidence: definitive (rendered page — reduced confidence) on [S15]'s quoted spans; definitive
on [S14]'s abstract; **derived** on the architectural reading and on the transfer from concurrent
acting subagents to a sequential judge (§2.3.4).*
**Breaks:** nothing outright — it is in direct tension with the pool's own contrary finding
(§5.5), and is listed last because that tension is unresolved.
**Remedy:** the decide-only disposition experiment already queued as next cycle's first topic in
`topics.md` is the right instrument; this finding raises its priority, it does not pre-empt it.

---

## 5. Honest boundary — where the counter-case fails (inverted, per the brief)

This section is written against this paper. Six of the eight items materially weaken something in
§2, and two of them weaken the paper's second-strongest attack.

### 5.1 The strongest practitioner voice for "own your control flow" asks for durable resume

The 12-factor-agents manifesto — the most-cited practitioner statement of the position §2.5
depends on — includes "Factor 8: Own your control flow" and "Factor 12: Make your agent a
stateless reducer" [S33]. But Factor 8's own text says, verbatim:

> "The number one feature request I have for every AI framework out there is we need to be able to
> interrupt a working agent and resume later, ESPECIALLY between the moment of tool selection and
> the moment of tool invocation." [S34]

and characterises the alternatives as pausing in-memory with sleep loops, restricting agents to
low-stakes tasks, or giving the agent real authority and hoping [S34].

**This substantially damages §2.5.** The manifesto that argues hardest for hand-rolled control
flow names durable interrupt-and-resume as its single largest missing capability. The
restart-over-resume case does not have this source on its side; it has it on the other side.
*(Confidence: definitive — raw markdown from the first-party repo. Note also that Factor 12,
which the paper's title-level reading would have made load-bearing, has **no substantive body
text** — the file is a heading, two images and navigation links, and the author labels it "mostly
just for fun" [S35]. It is cited for its title only and carries no argumentative weight.)*

### 5.2 Platform durability is itself unreliable — the "platforms will eat this" case has a
counter-example from this year

OpenAI's first-party deprecations page states: "On June 3, 2026, we notified developers using
Agent Builder that the product is being deprecated," with shutdown scheduled 2026-11-30; the same
notice covers the Evals platform and reusable prompt objects, and the migration guidance for
prompts is "move reusable prompt content into your application code" [S32].

**This damages D1's forward-looking half.** Agent Builder was announced at OpenAI DevDay in
October 2025 and deprecated in June 2026 — roughly eight months. *(**The launch date is
UNVERIFIED**: `openai.com/index/introducing-agentkit/` returned HTTP 403 and was not fetched.
[S32] establishes only the deprecation dates, which are what the argument actually needs — a
product deprecated within a year of any plausible launch date makes the point regardless of the
exact interval.)* A hand-built backbone that outlives a vendor's orchestration product is
not obviously the wrong bet, and "the platforms will eat this" is an argument that requires the
platform to still be there. It does **not** damage D1's backward-looking half: the gap claim was
still stale on 2026-05-28 regardless of what happens to any one product.

*Confidence: definitive — first-party OpenAI deprecations page, fetched.*

### 5.3 The vendor durable loops do not do what the architecture is for

Read carefully, each of the four §2.1 implementations is scoped in a way the architecture is not:

- Anthropic's is "in a single session" [S5] — one machine, one operator, one Claude Code session.
- AgentCore's session storage retains for "14 days of idle time" and is AWS-hosted [S1]; the
  compute is AWS's, which is the metered-billing side of the trade-off the problem statement
  refuses.
- Cloudflare's fibers live in Durable Objects on Cloudflare [S3][S4] — same objection.
- Dapr's DurableAgent requires a Dapr runtime [S6].

**None of them is "durable orchestration on a server that runs no agent compute, with credentials
staying on each participant's own machine."** The four-way combination as *scoped* survives §2.1;
what does not survive is the sentence "the industry did not make the loop durable," which is a
broader claim than the architecture needs. *(Derived, from [S1][S3][S4][S5][S6] and the problem
statement § What is being built.)*

### 5.4 Cognition softened its own position

Search results indicate Walden Yan has since stated that a year on, the "don't build multi-agents"
advice has been superseded by setups Cognition now runs in production, with the refined principle
that multi-agent works when writes stay single-threaded and extra agents contribute intelligence
rather than actions.

**Marked UNVERIFIED and stated as such.** The follow-up post was **not** fetched; the original
[S15] was. This is exactly the failure mode the brief warns about — inflating a summary into a
result — and the honest report is: **§2.3.4's source has publicly moved, in a direction that
weakens §2.3.4, and this paper has not verified how far.** Verifying it is a §7 item, not a claim.

### 5.5 Every multi-agent underperformance result is off-domain, and the pool has on-domain results
pointing the other way

[S12] measures multi-hop reasoning; [S13] measures vote aggregation; [S14] measures general
MAS task completion. **None measures review, critique or defect-finding**, which is what this
system's layering does. Against that, `convergence_stopping.md` reports on-domain results in the
opposite direction: repeated independent review passes produce largely disjoint finding sets and
aggregating ten of them improved F1 by 43.67% (SWR-Bench, in that paper's §2.2.2), and a fresh
separate reviewer beat same-session self-review (Cross-Context Review, in that paper's §2.2.1).
The pool also records OpenAI's CriticGPT result that a separate critic beats the author (that
paper's §2.2.5). *(Named by source rather than by the sibling paper's `[Sn]` numbers, which
collide with this paper's own numbering.)*

**This is the single largest limitation on §2.3.** The transfer from reasoning benchmarks to
review topology is unestablished in both directions, and the on-domain evidence such as it is
favours separation. *(Derived, from [S12][S13][S14] and `convergence_stopping.md` §§2.2.1–2.2.5.)*

### 5.6 The reuse evidence is pre-LLM, and LLM authorship attacks its cost model directly

Glass's Fact 18(a) — reusable components are three times as hard to build [S19] — is a **labour
cost** claim from 2002. The problem statement's own economics argue that the marginal cost of the
implementation labour is approaching a subscription fee, and § *Why coding is the first edge*
argues each new edge is *built by* the existing edge. If building the second and third
implementations is cheap, Fact 18(b)'s "try it in three applications" stops being a barrier and
becomes a plan. **Glass's rule of three may be an argument for building three edges quickly rather
than an argument against generalising.** *(Derived, from [S19] and the problem statement §
Why coding is the first edge. No source located tests whether LLM authorship changes reuse
economics — N7.)*

### 5.7 The level-triggered argument requires a declarative desired state, and a revision loop has
none

[S22] specifies systems that "operate correctly given the desired state and the current/observed
state." A Kubernetes controller can re-derive because the desired state is a written spec.
**A code-review or revision loop has no such spec** — "the PR is good" is not a declarative
target a worker can diff against the world. Where the desired state is not observable, level-based
re-derivation degrades to "run the whole thing again," which is restart, not reconciliation — and
restart is exactly what durable execution exists to avoid for expensive work. §2.5.1 is therefore
an analogy, not a transfer, and this paper marked it derived for that reason.

### 5.8 The CI/CD evidence is from open, untrusted-contributor ecosystems

[S27] is scoped to "forks of your public repository"; [S28]'s PPE vector assumes an attacker with
SCM write access they should not have; [S29]'s 23,000 repositories consumed an action from a
public marketplace. A shared workflow library among a handful of colleagues inside one
organisation is a materially different threat model, and none of the cited sources says otherwise.
**§2.6's force is proportional to how open the participant set becomes** — which is unknown, and
the problem statement does not say.

---

## 6. Citations

### 6.1 Negative findings and their search method

Per §3: a negative finding states how it was searched.

**N1. No published argument was located that agent loops specifically should NOT be durable, or
that restart-over-resume is preferable for LLM agent work.** Searched via: web search on
`critique "durable execution" wrong abstraction for AI agents "agents are not workflows"
LangChain LangGraph position 2026`; `"durable execution" criticism "over-engineering" agents
"you probably don't need" simpler queue database checkpoint`; and inspection of
`microsoft/agent-framework` Discussion #1092 ("Thoughts on supporting Durable execution"), which
was fetched and contains **no** argument against durability — the thread compares checkpointing to
durable execution and treats the approaches as complementary. **The published disagreement in this
space is entirely about *which* durability implementation is adequate (checkpoints vs. journals —
[S7]), never about whether the loop should be durable at all.** [S7] was fetched and is the
sharpest available instance: it contrasts "Checkpointing says: 'I saved your state. You take it
from here.'" with durable execution's "Your agent workflows will run to completion. Period. I
handle everything," and concludes that "for production workloads where agent workflows process
orders, manage infrastructure, handle customer requests...you need durable execution" [S7].
**Note the direction: the one source located that most sharply criticises how the field implements
durable loops argues that loops should be *more* durable, not less.** §2.5 is therefore this
paper's own architectural argument from adjacent fields, marked derived throughout. *This is the
finding that most favours the thesis and it is reported first.*

**N2. No documented post-mortem was located of a domain-general agent, workflow or automation
platform that failed to generalise across domains.** Searched via: `Gregor Hohpe platform trap
"build it and they will come" internal platform failure premature generalization postmortem` (three
successive query reformulations); `Robert Glass "Facts and Fallacies of Software Engineering" fact
reuse-in-the-large`; and attempted retrieval of Roberts & Johnson's *Evolving Frameworks* pattern
language. Nothing returned a case study with a named platform, a stated generalisation goal and a
documented failure. The C4 attack therefore rests on principle ([S19][S20][S21]), not on precedent.

**N3. Could not verify the "Three Examples" pattern from Roberts & Johnson's *Evolving
Frameworks*.** `laputan.org/drc/drc.html` was fetched and does not contain a pattern by that name
(it does contain "an abstraction is usually discovered by generalizing from a number of concrete
examples," which is not the same claim and is not cited); the Auckland PDF
(`cs.auckland.ac.nz/~john-g/papers/EFPL.pdf`) returned unparsed binary. **The "three examples
before a framework" claim is NOT made in this paper.** Glass Fact 18(b) [S19], which was verified
verbatim, carries that argument instead.

**N4. Two primaries in §2.5 did not extract and are cited without quotation.** *Crash-Only
Software*: `dslab.epfl.ch/pubs/crashonly.pdf` and
`research.cs.wisc.edu/.../Candea-CrashOnlySoftware.pdf` both returned unparsed PDF binary;
`usenix.org/legacy/events/hotos03/...` returned HTTP 403. Daly (2006):
`graal.ens-lyon.fr/~abenoit/CR02/papers/daly.pdf` and `ittc.ku.edu/~sun/publications/ic322.pdf`
both returned unparsed binary. Both are marked directional and neither is quoted.

**N5. No source was located making the argument in §2.3.7** (that flat-rate billing suppresses the
signal that would reveal layering is not paying). Searched incidentally across the multi-agent-cost
sweep ([S12][S16] and the Anthropic multi-agent-research material). It is this paper's own
inference and is marked derived.

**N6. No first-party guidance was located from any durable-execution vendor stating a horizon or
failure-rate threshold below which durable execution is not worth adopting.** Searched via: the
Temporal rules repo (TMPRL1100 fetched), the Temporal server architecture doc (fetched), the
Temporal AI-agents blog post (fetched), the DBOS comparison page (fetched), and web search on
`"durable execution" criticism "over-engineering" agents "you probably don't need"`. **Vendors do
not publish the boundary of their own product's usefulness** — an unsurprising gap, but one that
means the boundary has to be measured (§7 T1), not looked up.

> **N6 carries a correction into a sibling paper, so its dependent trace is stated in full.** The
> "~30-minute task-duration threshold" appears in `durable_execution.md` at **TWO sites**, both
> attributed to the same `claudelab.net` community-authored production guide, and **no vendor
> states it** at either. The correction is to the *authority* a consumer might read into the
> figure — not to the number, and not to the sibling paper's sourcing, which names its source
> correctly in both places.
>
> | Site | Wording | Unearned-authority risk |
> |---|---|---|
> | **§3**, Claude Agent SDK bullet | "…observe an approximate thirty-minute task-duration threshold **below which the discipline is net cost**" | **HIGHEST — fix this one first.** Stated flatly, with no hedge, inside the 2026 convergence timeline, where the surrounding material is first-party vendor announcements. A reader scanning §3 will take the threshold for vendor guidance by adjacency. |
> | **§6**, bullet 1 ("Short, in-process tasks") | notes "the ~30-minute threshold as **a rough heuristic**" | Lower — already hedged, and sits in the honest-boundary section where a reader expects judgement calls. |
>
> **An earlier draft of this note asserted that §3 "contains no such claim." That was wrong** —
> §3 line 45 carries it, unhedged — and the error was the worse kind for a propagating finding,
> because a downstream pass following the trace would have corrected the hedged site and left the
> unhedged one standing. **Full dependent list:** `durable_execution.md` §3 (Claude Agent SDK
> bullet) and §6 (bullet 1); any planning artifact that cites a horizon threshold as vendor
> guidance; and §7 T1 of this paper, which exists precisely because the threshold has no
> first-party source. *(This paper's separate pointer to `durable_execution.md` §4 for
> "checkpointing is not durable execution" was checked and is correct.)*

**N7. No source was located testing whether LLM-authored implementations change reuse economics**
(§5.6). Searched incidentally during the Glass/Fowler/Metz sweep. The argument in §5.6 is derived
and is offered *against* this paper's own §2.4.

**N8. Third-party self-hosting cost figures for Temporal were located only on commentary and
affiliate-style sites and are deliberately NOT cited.** §2.2.3 states the operational-tier
argument from first-party component enumeration [S10] and a named vendor competitor [S11] only.

### 6.2 Source list

**Vendor-shipped durable agent runtimes — first-party (HIGH volatility; this is the section that
decays)**

- [S1] Amazon Web Services (2026-03-25). *Amazon Bedrock AgentCore Runtime now supports managed
  session storage for persistent agent filesystem state (preview).*
  https://aws.amazon.com/about-aws/whats-new/2026/03/bedrock-agentcore-runtime-session-storage
  *(first-party announcement page, fetched)*
- [S2] Amazon Web Services (posted **2025-10-13**). *Amazon Bedrock AgentCore is now generally
  available.*
  https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/
  *(**fetched** — first-party announcement page; title and posted date verified)*
- [S3] Cloudflare (2026-04-15). *Project Think: building the next generation of AI agents on
  Cloudflare.* https://blog.cloudflare.com/project-think/ *(rendered first-party blog — short
  verbatim spans only)*
- [S4] Cloudflare. *agents* README.
  https://raw.githubusercontent.com/cloudflare/agents/main/README.md *(raw markdown, first-party)*
- [S5] Anthropic (2026-05-28). *Introducing dynamic workflows in Claude Code.*
  https://claude.com/blog/introducing-dynamic-workflows-in-claude-code *(rendered first-party
  blog — short verbatim spans only; **maturity label verified first-party: "Dynamic workflows are
  now generally available"**. Neither "research preview" nor "preview" appears on the page.)*
- [S6] Dapr. *Dapr Agents core concepts.*
  https://docs.dapr.io/developing-ai/dapr-agents/dapr-agents-core-concepts/ *(rendered
  first-party docs; undated in the fetched page)*
- [S7] Diagrid. *Why Checkpoints Aren't Durable Execution: LangGraph, CrewAI, Google ADK and
  others.*
  https://www.diagrid.io/blog/checkpoints-are-not-durable-execution-why-langgraph-crewai-google-adk-and-others-fall-short-for-production-agent-workflows
  *(**fetched** — vendor competitive content, so **definitive (rendered page — reduced
  confidence)** on its own wording and not neutral analysis. Independently corroborated on the
  checkpoint-vs-durable distinction by `durable_execution.md` §4.)*

**Durable-execution cost case — first-party and vendor (MEDIUM–HIGH volatility)**

- [S8] Temporal. *TMPRL1100 — Non-determinism error.*
  https://raw.githubusercontent.com/temporalio/rules/main/rules/TMPRL1100.md *(raw markdown,
  first-party)*
- [S9] Temporal. *Of course you can build dynamic AI agents with Temporal.*
  https://temporal.io/blog/of-course-you-can-build-dynamic-ai-agents-with-temporal *(rendered
  first-party blog; the "objection" text is Temporal's own paraphrase, not a sourced quotation)*
- [S10] Temporal. *Temporal server architecture README.*
  https://raw.githubusercontent.com/temporalio/temporal/main/docs/architecture/README.md *(raw
  markdown, first-party; note the fetched section states no database requirements)*
- [S11] DBOS. *DBOS vs. Temporal.* https://www.dbos.dev/compare/dbos-vs-temporal *(rendered
  **vendor competitive marketing** — cited as a published architectural argument, not as neutral
  analysis)*

**Multi-agent and judge evidence — peer-reviewed and preprint (MEDIUM volatility)**

- [S12] Tran, D., & Kiela, D. (2026-04-02). *Single-Agent LLMs Outperform Multi-Agent Systems on
  Multi-Hop Reasoning Under Equal Thinking Token Budgets.* arXiv:2604.02460.
  https://arxiv.org/abs/2604.02460 *(abstract fetched via the arXiv Atom API)*
- [S13] Chen, L., Davis, J. Q., Hanin, B., Bailis, P., Stoica, I., Zaharia, M., & Zou, J. (2024).
  *Are More LM Calls All You Need? Towards the Scaling Properties of Compound AI Systems.*
  arXiv:2403.02419. https://arxiv.org/abs/2403.02419 — abstract quoted from
  https://arxiv.org/html/2403.02419
- [S14] Cemri, M., Pan, M. Z., Yang, S., Agrawal, L. A., Chopra, B., Tiwari, R., Keutzer, K.,
  Parameswaran, A., Klein, D., Ramchandran, K., Zaharia, M., Gonzalez, J. E., & Stoica, I.
  (2025-03-17, updated 2025-10-26). *Why Do Multi-Agent LLM Systems Fail?* arXiv:2503.13657.
  https://arxiv.org/abs/2503.13657 *(abstract fetched via the arXiv Atom API)*
- [S15] Cognition. *Don't Build Multi-Agents.* https://cognition.com/blog/dont-build-multi-agents
  *(rendered page — short verbatim spans only; **position since softened, see §5.4**)*
- [S16] Anthropic. *When to use multi-agent systems (and when not to).*
  https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them *(rendered
  first-party page — short verbatim spans only)*
- [S17] Anthropic. *Building Effective Agents.*
  https://www.anthropic.com/engineering/building-effective-agents *(rendered first-party page —
  short verbatim spans only; the same page is also cited in `convergence_stopping.md`)*
- [S18] Ye, J., Wang, Y., Huang, Y., Chen, D., Zhang, Q., Moniz, N., Gao, T., Geyer, W., Huang,
  C., Chen, P.-Y., Chawla, N. V., & Zhang, X. (2024-10-03). *Justice or Prejudice? Quantifying
  Biases in LLM-as-a-Judge.* arXiv:2410.02736. https://arxiv.org/abs/2410.02736 *(abstract fetched
  from the arXiv abs page)*

**Generalisation and reuse — software-engineering fundamentals (LOW volatility)**

- [S19] Glass, R. L. (2002). *Facts and Fallacies of Software Engineering*, Reuse chapter, Facts
  **15, 16, 17 and 18**. Publisher's authorized excerpt:
  https://www.informit.com/articles/article.aspx?p=30091&seqNum=5 *(**fetched twice** — rendered
  page reproducing primary book text; **definitive (rendered page — reduced confidence)**. Fact
  numbers verified against the page. Fact 17 was added on the second fetch after an earlier draft
  wrongly recorded it as unfetched and declined to use it.)*
- [S20] Fowler, M. *Yagni.* https://martinfowler.com/bliki/Yagni.html *(rendered page — short
  verbatim spans only)*
- [S21] Metz, S. (2016-01-20). *The Wrong Abstraction.*
  https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction *(rendered page — two short verbatim
  spans only)*

**Level-triggered control and restart-as-recovery (LOW volatility)**

- [S22] Kubernetes. *Design Principles.*
  https://raw.githubusercontent.com/kubernetes/design-proposals-archive/main/architecture/principles.md
  *(raw markdown, first-party)*
- [S23] Kubernetes. *Controllers.*
  https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/architecture/controller.md
  *(raw markdown, first-party)*
- [S24] Candea, G., & Fox, A. (2003). *Crash-Only Software.* HotOS IX.
  https://www.usenix.org/conference/hotos-ix/crash-only-software *(**primary did not extract —
  see N4. Directional; not quoted.**)*
- [S25] Daly, J. T. (2006). *A higher order estimate of the optimum checkpoint interval for
  restart dumps.* Future Generation Computer Systems 22(3), 303-312.
  https://www.sciencedirect.com/science/article/abs/pii/S0167739X04002213 *(**primary did not
  extract — see N4. Directional; formula not reproduced.**)*
- [S26] Chroma (2025). *Context Rot: How Increasing Input Tokens Impacts LLM Performance.*
  https://www.trychroma.com/research/context-rot *(rendered first-party research page — short
  verbatim spans only)*

**Multi-tenant / shared-library risk (LOW volatility for the taxonomy, HIGH for incidents)**

- [S27] GitHub Docs. *self-hosted-runner-security* reusable.
  https://raw.githubusercontent.com/github/docs/main/data/reusables/actions/self-hosted-runner-security.md
  *(raw markdown, first-party — quoted in full)*
- [S28] OWASP. *CICD-SEC-04: Poisoned Pipeline Execution.*
  https://raw.githubusercontent.com/OWASP/www-project-top-10-ci-cd-security-risks/main/CICD-SEC-04-Poisoned-Pipeline-Execution.md
  *(raw markdown, first-party project repo)*
- [S29] GitHub Advisory Database. *GHSA-mrrh-fwg8-r2c3 / CVE-2025-30066* (published 2025-03-15).
  https://github.com/advisories/ghsa-mrrh-fwg8-r2c3 *(rendered first-party advisory — short
  verbatim span)*
- [S30] CISA (2025-03-18). *Supply Chain Compromise of Third-Party tj-actions/changed-files
  (CVE-2025-30066) and reviewdog/action-setup@v1 (CVE-2025-30154).*
  https://www.cisa.gov/news-events/alerts/2025/03/18/supply-chain-compromise-third-party-tj-actionschanged-files-cve-2025-30066-and-reviewdogaction
  *(**HTTP 403 — not fetched. Existence and date from search results; unverified.**)*
- [S31] Palo Alto Unit 42 (2025, updated 2025-11-26). *"Shai-Hulud" Worm Compromises npm Ecosystem
  in Supply Chain Attack.* https://unit42.paloaltonetworks.com/npm-supply-chain-attack/ *(not
  fetched; corroborated industry reporting, counts vary across sources and are not quoted —
  **unverified**)*

**Counter-evidence against this paper (§5)**

- [S32] OpenAI. *Deprecations.* https://developers.openai.com/api/docs/deprecations *(fetched —
  first-party; Agent Builder, Evals and reusable prompts, announced 2026-06-03, shutdown
  2026-11-30)*
- [S33] HumanLayer. *12-factor-agents* README.
  https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/README.md *(raw markdown)*
- [S34] HumanLayer. *Factor 8: Own your control flow.*
  https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/content/factor-08-own-your-control-flow.md
  *(raw markdown)*
- [S35] HumanLayer. *Factor 12: Make your agent a stateless reducer.*
  https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/content/factor-12-stateless-reducer.md
  *(raw markdown — **contains no substantive body text**; cited for its title only)*

**Pool papers cited, not re-derived (per the dispatch scope note)**

- `docs/standards/architecture/research/raw/convergence_stopping.md` — Last validated 2026-08-03;
  **Critic: PASS**. Owns the plateau/stopping literature, judge pathologies, per-pass recall.
- `docs/standards/architecture/research/raw/reflection_literature.md` — Last validated 2026-07-23;
  **Critic: PASS**. Owns the reflection corpus and its four gaps.
- `docs/standards/architecture/research/raw/durable_execution.md` — Last validated 2026-07-27;
  **Critic: PASS**. Owns the durable-execution primer, the vendor landscape, the
  checkpointing-is-not-durable-execution distinction (**§4**), and the ~30-minute threshold
  (**§6**, bullet 1 — *not* §3) whose provenance N6 corrects.
- `docs/standards/architecture/research/raw/anthropic_tos_and_enterprise.md` — Last validated
  2026-07-24; Critic: PASS; **in window — due 2026-08-21**, consumable as current evidence.
- `docs/standards/architecture/research/raw/workflow_reuse_boundary.md` — owns the
  parameterise-vs-fork ruling; §2.4.3 does not re-open it.

*Sourcing posture, counted after the critic pass: 35 external sources. **31 were fetched** — [S2]
and [S7] were upgraded from unfetched after the critic pass located both, and [S5] and [S19] were
re-fetched to correct a maturity label and to add Glass Fact 17. Of the 31, **17 came from raw
markdown, the arXiv API/HTML, or a first-party announcement page** ([S1], [S2], [S4], [S8], [S10],
[S12], [S13], [S14], [S18], [S22], [S23], [S27], [S28], [S32], [S33], [S34], [S35]) and **14 from
rendered pages** ([S3], [S5], [S6], [S7], [S9], [S11], [S15], [S16], [S17], [S19], [S20], [S21],
[S26], [S29]) — each carrying the "rendered page — reduced confidence" modifier at the point of
use and quoted only in spans visible in the fetch. **4 were NOT successfully fetched** ([S24]
Candea & Fox and [S25] Daly, whose PDFs returned unparsed binary; [S30] CISA, HTTP 403; [S31] Unit
42) and are marked directional or unverified in place; **nothing load-bearing rests on any of the
four** — [S24] and [S25] are quoted nowhere, [S30] duplicates [S29], and [S31] is corroboration
only. Every §4 finding D1–D7 rests on at least one raw/API/first-party-fetched source.*

---

## 7. Test plan — what research cannot settle

Ordered by decision value. Each names what it would change.

**T1. Measure what a crash actually costs today, before buying durability.**
*Because:* D6 and N6 together say the durability decision is a cost-benefit calculation against a
realised failure rate that nobody has published a threshold for, and that this system is currently
level-triggered [S22].
*Design:* over a window of dispatches, count runs that died mid-flight; for each, record wall-time
and token spend lost, and whether a plain re-dispatch recovered it. Instrument this in the existing
run-log JSONL — no new tooling.
*Reads out:* the empirical numerator of the checkpoint-interval trade-off [S25]. *Decides:* whether
durable execution is the right next phase or a later one. **If crashes are rare and re-dispatch is
cheap, D6 stands and the roadmap should re-order.**

**T2. Instrument per-layer token cost even though it is not billed.**
*Because:* D3 — [S12] says multi-agent gains are often explained by unaccounted compute, and
flat-rate billing is precisely a mechanism for not accounting for compute.
*Design:* record tokens per child workflow and per agent lens; compute cost-per-verified-finding
for the author lane, the judge lane and the disposition lane separately.
*Reads out:* whether the layering earns its 3-10x [S16] on this workload. *Fails informatively:*
if the judge lane's cost-per-verified-finding is worse than a second author pass, D3 lands.

**T3. Give the generality claim a falsification test with a date.**
*Because:* D2 — Glass Fact 18(b) [S19] wants three applications and there is one; §5.6 says LLM
authorship may make three cheap. Both cannot be assessed without a second edge.
*Design:* pick the smallest plausible non-coding edge, timebox it, and record what in `scripts/`,
`config/` and the workflow contracts had to change. The claim under test is literal: *the backbone
does not change.*
*Reads out:* the backbone's actual change-rate per new edge. *Decides:* whether "nothing may assume
the coding edge" is a validated constraint or a carrying cost [S20].

**T4. Decide where branch logic lives, before the Temporal port and not during it.**
*Because:* D4 — [S8] says a workflow-code change that alters a past execution path is a
non-determinism error, and the improvement loop's entire output is changes to that logic.
*Design:* take three real routing decisions from `revision.sh` and write each twice: once as
workflow-code branching, once as data an activity returns. Change each, and count the versioning
work.
*Reads out:* the real cost of element 3 ("a parent can branch on what a child concluded") under
replay. Research cannot settle this because it depends on this repo's change rate.

**T5. Test whether a judge with no author context loses findings.**
*Because:* D7 and §5.5 — [S15] says separation disperses decision-making and loses context;
`convergence_stopping.md` says separation *improves* review F1. **The pool now contains two
sourced claims pointing opposite ways and no experiment — but they are NOT peers and should not
be queued as though they were.** [S15] is a practitioner blog (rendered page, reduced confidence),
about *concurrent acting* subagents rather than a sequential judge, and its author has publicly
softened the position (§5.4, unverified). The `convergence_stopping.md` result is a controlled
experiment, but a directional one — single model, injected errors, single-author preprint, and no
fresh-context-twice arm. **The asymmetry favours the separation side**; what makes this worth an
experiment is not that the two are evenly matched, it is that neither measures the topology this
system actually runs.
*Design:* the decide-only-disposition experiment already queued first in `topics.md`, extended with
a context-rich judge arm: same PR, judged (a) with only the artifact, (b) with the artifact plus
the author's full trace. Measure findings raised, verified and retracted.
*Reads out:* which side of the §5.5 tension holds on this workload. **This is the highest-value
experiment in the plan and it is the only one that adjudicates a live contradiction inside the
pool.**

**T6. Verify the Cognition follow-up.**
*Because:* §5.4 is marked unverified and it weakens §2.3.4, which is a §4 finding.
*Design:* fetch the follow-up post; determine whether the refined principle ("writes stay
single-threaded, extra agents contribute intelligence rather than actions") contradicts or refines
[S15]. Cheap; should run first. *Reads out:* whether D7 survives at its stated strength.

**T7. Define the participant set before designing the shared library's governance.**
*Because:* D5's force is proportional to how open the participant set is (§5.8), and that is a
product decision, not a research finding. [S27][S28][S29] describe open ecosystems.
*Design:* not an experiment — a written decision. Who may publish a module; who may run one; what
signing/pinning/provenance is required at each trust level. *Reads out:* whether §2.6 is a design
requirement or an out-of-scope threat model.

**Not settleable by any of the above, and recorded as such:** whether the four-element combination
is worth building *given* that three vendors ship scoped versions of it (§5.3). That is a judgement
about whether the scope difference — multi-participant, credentials-at-edge, server-runs-no-agent-
compute — is worth a hand-built backbone, and no experiment inside this repo can answer it. It is
the question the synthesis has to answer, and this paper's contribution to it is only that the
question is now *whether the scoping is valuable*, not *whether the gap exists*.
