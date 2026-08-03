# workflow_reuse_boundary

```
Topic:          Where does the boundary between parameterizing one shared workflow and forking a
                second one fall — and does a parameterized shared workflow library hold up in
                practice, or do teams fork anyway?
Feeds:          synthesis.md action candidate #4 ("treat the shared workflow library as the
                first-class artifact, not any individual workflow"); and downstream of it, the
                gating fork-vs-parameterize ruling in roadmap.md § Phase: Workflow Decomposition
Last validated: 2026-08-03
Revalidate:     high — 6 weeks
Confidence:     Definitive on what each surveyed system ships and what it deprecated (first-party
                docs, fetched raw) and on the peer-reviewed empirical numbers. Definitive on the
                survey finding that copy-and-adapt out-competes first-class reuse in practice.
                DERIVED on this paper's central claim — that the field's operative discriminator is
                expected future co-evolution, not textual overlap. UNVERIFIED (stated as a negative
                finding with search method) that any documented numeric threshold exists for "too
                many parameters → fork"; it is folklore. Directional on vendor intent.
Critic:         PASS-WITH-FIXES (re-sourced the ClusterTask → `cluster` resolver replacement to
                Tekton's v1beta1→v1 migration guide [S24], which states it — [S10] alone did not;
                restored the dropped word in the [S9] PipelineResources quote; split a §5.1 [S21]
                quote that had been synthesized from two separate passages) — 2026-08-03
```

> **Volatility note (per Research Standard §3, mixed-volatility rule).** The paper's load-bearing
> evidence is peer-reviewed clone-evolution and configuration-complexity research from 2005–2015 —
> **low volatility, safe to skip on refresh**: §5, §6, §7 and the numbers attributed to [S17]–[S22].
> The header takes the *highest* tier present, which comes from a small minority of the content:
> the vendor limits and deprecation states in §3 and §4 ([S1]–[S4], [S7]–[S14]) are product
> API-surface facts and decay fast. **A refresh should re-verify §3–§4 and leave §5–§7 alone.**

---

## 1. Primer — what the question actually is

Two artifacts do nearly the same thing. You have exactly two structural options, and every
orchestration system that has shipped at scale ships both:

- **Parameterize** — one definition, called with different inputs. Variation is expressed as data.
- **Fork** — two definitions, edited independently. Variation is expressed as code.

The naive framing is DRY: measure the textual overlap, and if it is high, deduplicate. This repo's
own workflow standard already rejects that framing for a neighbouring decision — *"The test is not
lines of code and it is not DRY"* (`docs/standards/workflow-scripts.md` § Composition). This paper
asks whether the field agrees, and if so what test it uses instead.

The vocabulary is not consistent across communities, which is a research hazard worth naming up
front. CI/CD systems say *reusable workflow* / *composite action* / *template* / *component*. The
Kubernetes configuration-management literature says *parameterization* vs *overlay* vs *fork*. The
software-maintenance literature says *clone*, and — critically for this topic — partitions clones by
the **author's intent about future evolution**, not by how much text they share [S17]. Those three
literatures are answering the same question in three dialects, and the maintenance literature is the
only one with controlled empirical measurement behind it.

**A note on what is *not* asked here.** This paper does not rule on any specific script in this
repo. It establishes the premise underneath such a ruling: whether a parameterized shared library is
the right shape for a workflow shelf at all, and what the field's experience establishes about where
parameterization stops paying.

---

## 2. The specific options, as the field actually ships them

### 2.1 Two-tier reuse is the near-universal shape *(definitive)*

Every surveyed system offers **a small-grained reusable unit** and **a large-grained reusable unit**,
with different capabilities:

| System | Small-grained unit | Large-grained unit | Reference mechanism |
|---|---|---|---|
| GitHub Actions | Composite action — *"collect a series of workflow job steps into a single action which you can then run as a single job step in multiple workflows"* [S2] | Reusable workflow — invoked via `on: workflow_call` at job level [S1] | `uses:` by repo/ref |
| Argo Workflows | `templateRef` to a template inside a `WorkflowTemplate` [S7] | `workflowTemplateRef` — run an entire `WorkflowTemplate` as a `Workflow` [S7] | Kubernetes resource name |
| Tekton | `Task` (steps) | `Pipeline` (tasks) | name + remote resolvers |
| GitLab CI/CD | Component — *"a reusable single pipeline configuration unit"* [S13] | Component composing a full pipeline; same primitive [S13] | `include: component:` with version |
| Jenkins | Shared-library step/function | Shared-library global var / whole pipeline template | `@Library('name@version')` [S11] |
| Airflow | Shared Python helper imported by DAG files | DAG factory generating many DAGs from config [S12] | Python import |

The consistent design is: **a named, versioned reference plus a typed input list.** Nobody ships
"one giant workflow with a mode flag" as the recommended shape, and nobody ships "copy the file" as
the recommended shape either.

### 2.2 The parameter channels are explicitly bounded *(definitive, high volatility)*

- **GitHub Actions.** *"You can connect a maximum of ten levels of workflows — that is, the top-level
  caller workflow and up to nine levels of reusable workflows."* On GitHub Enterprise Server the
  same doc states **four** levels. *"Loops in the workflow tree are not permitted."* Secrets do not
  transit implicitly: *"Secrets are only passed to directly called workflow, so in the workflow chain
  A > B > C, workflow C will only receive secrets from A if they have been passed from A to B, and
  then from B to C."* Permissions *"can only be maintained or reduced—not elevated—throughout the
  chain."* [S1]
- **GitLab.** *"A pipeline can take up to 20 inputs."* *"A string containing an input must be less
  than 1 MB."* *"A string inside an input must be less than 1 KB."* [S14] The component catalog caps
  components per project (documented as 30, raised in a later release) [S13].

**This matters more than it looks.** GitLab's 20-input cap is the only hard, first-party numeric
ceiling found anywhere on the parameterize side. It is framed as a platform limit, not as design
guidance — but it is the field's single existence proof that somebody decided the parameter list
needs a wall.

---

## 3. Comparative landscape — what each system learned, and what it deprecated

The most informative signal is not what these systems ship; it is what they **withdrew**.

### 3.1 Tekton removed its general parameterization layer *(definitive)*

`PipelineResources` were Tekton's abstraction for typed, parameterized inputs/outputs. The
first-party doc states plainly: *"PipelineResources are now deprecated."* The reasons given are a
near-complete enumeration of how a general parameterization layer fails [S9]:

1. Opaque behaviour — implemented as *"a mixture of injected Task Steps, volume configuration and
   type-specific code"*, making errors hard to trace.
2. Undebuggable — *"Several PipelineResources inject their own Steps before a `Task's` Steps. It's
   extremely difficult to manually insert Steps before them to inspect the state."*
3. Insufficient coverage — *"The six types of existing PipelineResources only cover a tiny subset of
   the possible systems."*
4. It **reduced** Task reusability, by coupling Tasks to specific resource types.
5. Conceptual ambiguity — the CRD's purpose was unclear.

The replacement is not "fewer parameters." It is **explicit composition**: ordinary Tasks with
`params`, `workspaces` and `results`. Tekton also deprecated `ClusterTask` — the cluster-scoped
*shared copy* — in favour of remote resolution of a referenced definition: the deprecations table
records `[ClusterTask is deprecated]` at v0.41.0 [S10], and Tekton's own v1beta1→v1 migration guide
names the replacement directly — *"`ClusterTask` is deprecated. Please use the `cluster` resolver
instead."* [S24]. Both moves run the same direction: **from implicit shared machinery toward
explicit, typed, named references.**

### 3.2 Argo deprecated the construct that let a definition also be an instantiator *(definitive)*

The Argo 3.4 documentation carries an unusually clear diagnosis [S7]:

> *"You should **never** reference another template directly on a `template` object (outside of a
> `steps` or `dag` template). This includes both using `template` and `templateRef`. This behavior is
> deprecated, no longer supported, and will be removed in a future version."*
>
> *"The reasoning for deprecating this behavior is that a `template` is a 'definition': it defines
> inputs and things to be done once instantiated. With this deprecated behavior, the same template
> object is allowed to be an 'instantiator': to pass in 'live' arguments and reference other
> templates (those other templates may be 'definitions' or 'instantiators')."*
>
> *"This behavior has been problematic and dangerous. It causes confusion and has design
> inconsistencies."*

The passage is **absent from the current `main`-branch copy of the same file** (checked raw,
2026-08-03) [S8], consistent with the removal having completed. *(Derived, from [S7] + [S8]: the
absence is a reasonable inference of completed removal, not a documented statement of it.)*

The transferable lesson is the definition/instantiator separation itself: **the thing that holds
parameters and the thing that supplies them must not be the same object.** This is the same boundary
this repo's standard already draws between a parent (decides) and a child (does).

### 3.3 GitLab replaced templates with versioned, input-typed components *(definitive/directional)*

GitLab's CI/CD components are *"a reusable single pipeline configuration unit"* that *"can be listed
in the CI/CD Catalog"*, *"can be released and used with a specific version"*, and support
`spec:inputs` [S13]. GitLab has stopped accepting new CI/CD *templates* in favour of components
*(directional — sourced from GitLab's development guide and blog framing rather than a single
verbatim first-party deprecation line)*.

The delta between the old and new mechanism is instructive: templates were unversioned includes;
components are **versioned artifacts with a declared input schema and a discovery surface.** The fix
GitLab chose for "shared config is hard to maintain" was *versioning and typing the shared artifact*,
not *reducing sharing*.

### 3.4 Jenkins: the shared library works, and its cost is trust and version skew *(definitive)*

Jenkins states the motivation exactly as this repo's action candidate #4 does: *"As Pipeline is
adopted for more and more projects in an organization, common patterns are likely to emerge.
Oftentimes it is useful to share parts of Pipelines between various projects to reduce redundancies
and keep code 'DRY'."* [S11]

Its documented cost is not parameter proliferation. It is **blast radius and authority**: *"Beware
that **anyone able to push commits to this SCM repository could obtain unlimited access to
Jenkins**."* [S11] The mitigation Jenkins ships is per-pipeline version pinning — a default version,
optionally overridable per-pipeline by `@Library('name@version')`, and versions that *"could be
computed rather than a constant"* [S11]. That is: **the shared library is real, and the escape hatch
is per-consumer version choice rather than per-consumer copies.**

### 3.5 Airflow: parameterization is endorsed, with a stated operational ceiling *(definitive)*

Airflow explicitly endorses the factory shape — *"Sometimes writing Dags manually isn't practical.
Maybe you have a lot of Dags that do similar things with just a parameter changing between them."*
[S12] — and then names the wall: *"Make smaller number of Dags per file"*, because *"one file can
only be parsed by one FileProcessor"* [S12]. The limit is a **runtime scaling** property of the
factory, not a maintainability judgement about it. Airflow is the one surveyed system whose stated
boundary is mechanical rather than cognitive.

### 3.6 Kubernetes: the one first-party document that argues *against* parameterization *(definitive)*

The Kubernetes "Declarative Application Management" design proposal is the strongest counter-case in
the corpus, and it is a primary design document rather than commentary [S15]:

> *"Parameterization solutions are easy to implement and to use at small scale, but parameterized
> templates tend to become complex and difficult to maintain. Syntax-oblivious macro substitution
> (e.g., sed, jinja, envsubst) can be fragile, and parameter substitution sites generally have to be
> identified manually, which is tedious and error-prone, especially for the most common use cases,
> such as resource name prefixing.*
>
> *Additionally, performing all customization via template parameters erodes template encapsulation.
> Some prior configuration-language design efforts made encapsulation a non-goal due to the
> widespread desire of users to override arbitrary parts of configurations. **If used by enough
> people, someone will want to override each value in a template.** Parameterizing every value in a
> template creates an alternative API schema that contains an out-of-date subset of the full API, and
> when every value is a parameter, a template combined with its parameters is considerably less
> readable than the expanded result, and less friendly to data-manipulation scripts and tools."*

Its assessment of forking is not dismissive: *"Fork: simple to understand; supports arbitrary changes
and updates via rebasing, but hard to automate in a repeatable fashion to maintain multiple
variants"* and *"Fork provides one-time customization, which is the most common case."* [S15] The
document proposes tooling to make forking *manageable* — *"Build fork/branch management tooling for
common workflows, such as branch creation, cherrypicking … rebasing, etc."* [S15] — rather than
proposing to eliminate it.

This is the intellectual ancestor of Kustomize's overlay model, and it is a genuine dissent from
"parameterize the shared artifact."

---

## 4. Does the shared library hold up in practice? — the survey evidence

This is the topic's empirical core, and there is a directly on-point 2026 peer-reviewed survey of
419 practitioners [S5].

**The headline: copy-and-adapt beats first-class reuse, decisively.** *(definitive — first-party
survey data)*

- Adapting **one's own existing workflow** is the dominant creation mechanism: 50.8% *frequently* +
  26.3% *(nearly) always* [S5, Fig. 3].
- On the reuse side, *"a clear preference to **copy own workflow** as opposed to **copy other's
  workflow** or **copy another source**"* [S5]. **62.5% of all respondents at least *frequently* copy
  parts from one of their own workflows** [S5].
- Against that: *"28.2% of respondents reported that they never use their **own reusable workflows**,
  while 38.4% never use **others' reusable workflows**."* And *"only 36% of respondents reported
  using their own reusable workflows at least frequently. Reliance on others' reusable workflows was
  even less common, with merely 22.7% doing so at least frequently."* [S5]
- The *small*-grained mechanism does far better than the *large*-grained one: *"Reusing someone
  **other's Action** is the most frequent, with 77.4% respondents reporting it at least frequently."*
  [S5]
- **Reusability is the least-valued maintenance property surveyed.** Of seven non-functional
  characteristics, reliability was rated at least moderately important by 97.1% and reusability by
  53.7% — last place. The authors' own reading: *"Workflow maintainers seem to underexploit GitHub
  Actions's reusability mechanisms."* [S5]

**And the stated reasons are not just ignorance.** For respondents who copy a whole job instead of
calling a reusable workflow [S5]:

| Reason | Share |
|---|---|
| control and flexibility | 43.0% |
| convenience | 40.3% |
| unfamiliarity with the mechanism | 29.8% |
| perceived complexity of adopting it | 28.5% |
| undiscoverability of a suitable one | 21.3% |
| unawareness that it exists | 20.0% |
| lack of trust | 4.3% |

The paper summarises: *"They believe that duplicating a job definition is simpler and quicker than
setting up and calling a reusable workflow"*, and *"managing inputs, outputs, and the overall call
structure can seem more involved than simply copying the job definition"* [S5]. Across all
respondents and all three mechanisms, *"43.7% of all respondents reported that adopting a reuse
mechanism would introduce additional complexity"* [S5].

Practitioner quotes from the same study state the boundary in engineers' own words [S5]:

> *"If an Action is actually really simple, it's better to copy it, rather than depend on an external
> Action"*
>
> *"Indirection makes it harder to reason about."*
>
> *"Most steps are less than 5 lines of bash. I don't want complexity spread across multiple
> locations, unless it's an official Action (feels like a standard library), unless it's actually not
> worth maintaining the complexity myself (similar to the decision to include dependencies in
> software itself), and even then I'd prefer to use something well established."*
>
> *"A reusable workflow has to be an entire job; it cannot just be a step. This limits its usefulness.
> But even then, I should probably use it more often."*

A companion 2026 large-scale study of 49K+ repositories, 267K+ workflow change histories and 3.4M+
file versions adds the maintenance profile: *"repositories contain a median of three workflow files,
and 7.3% of all workflow files are being changed every week … about three-quarters containing only a
single change"*, with changes concentrated in *"task configuration and task specification in workflow
jobs"* [S6]. *(Definitive.)*

**Derived reading of [S5] + [S6], and the honest version of the answer to the topic question:** teams
*do* fork anyway — but the finding is more specific than "the library failed." Small-grained,
well-typed, externally-published units (Actions, 77.4% frequent use) hold up **very well**.
Large-grained whole-pipeline reuse (reusable workflows, 22–36%) largely does not. The differentiator
across the reasons given is **interface cost relative to artifact size**: the mechanisms people adopt
are the ones where the call is cheaper than the copy. That is a ratio, not a line count.

---

## 5. The parameterize-side failure mode — and whether a threshold is documented

### 5.1 The failure mode is measured, and the direction is one-way *(definitive)*

Xu et al.'s ESEC/FSE 2015 study of four mature systems (Storage-A, Apache httpd, MySQL, Hadoop) is
the field's quantitative account of configuration proliferation [S21]:

- Growth is severe: Hadoop MapReduce went from 17 parameters at first release (Apr 2006) to 173 (Oct
  2013), *"an increase of more than nine times."* MySQL 5.6 has 461 configuration parameters; Apache
  HTTP 2.4 *"has more than 550 parameters across all the modules."*
- Growth is **not reversible in practice**: *"The parameter removal rate is almost 7x slower than the
  rate of addition."*
- Most parameters are dead weight: *"only a small percentage (6.1%~16.7%) of configuration parameters
  are set by the majority (50+%) of users in the studied systems, while a significant percentage (up
  to 54.1%) of parameters are seldom set."*
- The excess is removable: for Storage-A, applying the paper's guidelines *"can remove 51.9% of its
  parameters and simplify 19.7% of the remaining ones"* — *"with little impact on existing users."*
- And the excess is harmful: of 620 real-world configuration errors, *"a significant percentage
  (17.5%~53.3%) of the configuration errors were caused by users' incorrectly staying with the
  default values, rather than setting wrong values."* A separate passage of the same paper explains
  why a default can be the wrong value at all — correct settings have to be chosen *"according to the
  runtime environments, workloads, resources, cross-component correlations."* *(Two quotes from two
  separate passages; joining them is this paper's reading, not the source's sentence.)*

The paper quotes Rob Pike for the practitioner sentiment: *"There is too much configuration. There
are too many options. There are too many dot files. Stuff should just work."* [S21]

The mechanism by which the knobs accrete is best stated by Sandi Metz, and it is exactly the
"one workflow with fourteen booleans" shape [S22] *(commentary — influential practitioner essay, not
peer-reviewed; corroborated in substance by [S15] and [S21])*:

> 5. A new requirement appears for which the current abstraction is *almost* perfect.
> 6. Programmer B gets tasked to implement this requirement. They alter the code to take a parameter,
>    and then add logic to conditionally do the right thing based on the parameter value.
> 7. Another new requirement arrives. Another additional parameter. Another new conditional. Loop
>    until code becomes incomprehensible.

— and the conclusion *"duplication is far cheaper than the wrong abstraction"* [S22]. The Kubernetes
design proposal makes the same prediction from the other end: *"If used by enough people, someone
will want to override each value in a template."* [S15]

**Derived (from [S15] + [S21] + [S22]):** parameter count has **no stable equilibrium**. Additions
are locally justified and individually cheap; removals are globally beneficial and individually
expensive, so they run ~7× slower [S21]. A shared workflow with a parameter list and no explicit
removal discipline is therefore predicted to ratchet, not to converge. *This is the strongest
transferable claim on the parameterize side, and it is a prediction about direction, not magnitude.*

### 5.2 Is there a documented threshold? — **No. It is folklore.** *(negative finding, with method)*

**Searched:** GitHub Actions `content/actions/how-tos/reuse-automations/reuse-workflows.md`,
`content/actions/reference/limits.md`, `content/actions/reference/workflows-and-actions/
workflow-syntax.md`, `content/actions/tutorials/create-actions/create-a-composite-action.md` (all raw
from `github/docs@main`); GitLab `doc/ci/components/_index.md` and `doc/ci/inputs/_index.md` (raw);
Argo `docs/workflow-templates.md` (raw, both `main` and `release-3.4`); Tekton `docs/resources.md`
and `docs/deprecations.md` (raw); Jenkins `shared-libraries.adoc` (raw); Airflow
`airflow-core/docs/best-practices.rst` (raw); plus targeted web search for documented "when to split
a template / too many inputs" guidance.

**Result:**

- **No surveyed system publishes design guidance of the form "at N inputs, stop parameterizing."**
- The only numeric caps found are **platform limits, not design advice**: GitLab's *"A pipeline can
  take up to 20 inputs"* [S14]; GitHub's ten-level (four on GHES) workflow nesting depth [S1].
  GitHub's `limits.md` and `workflow-syntax.md` state **no** maximum input count for `workflow_call`
  [S3][S4]. Community claims of a 10-input cap on `workflow_call` were **not corroborated in
  first-party docs** and should not be relied on. *(unverified)*
- The only widely-cited numeric heuristic in the whole space is the **Rule of Three** — "the third
  time you do something similar, you refactor" — popularised by Fowler's *Refactoring* and
  attributed by him to Don Roberts [S23]. It is an anecdote-sourced rule of thumb about *when to
  start* abstracting, not about *when to stop* parameterizing, and no empirical derivation of the
  number was found. *(unverified as an empirical threshold; definitive only as to its attribution.)*

**Therefore: any threshold rule this repo adopts is a local invention, and must be labelled as one.**
It cannot cite the field, because the field does not have one. What the field *does* supply is a
direction of drift ([S21]'s 7× asymmetry) and a set of qualitative tells ([S9]'s five reasons,
[S15]'s encapsulation-erosion argument, [S5]'s "indirection makes it harder to reason about").

---

## 6. The fork-side failure mode — N-way propagation, measured

The propagation failure is real, quantified, and comes from the software-maintenance literature
rather than from CI research.

**Juergens et al., ICSE 2009** — five industrial/open-source systems (three commercial C#, one Cobol,
one open-source Java), ~1800 manual clone-group assessments, developers of the systems consulted to
classify intent, 107 confirmed faults [S18] *(definitive)*:

| Measure | Result |
|---|---|
| Clone groups containing inconsistencies | *"About half of the clones (52%) contain inconsistencies."* |
| Of those, introduced **unintentionally** | *"over a quarter (28%) have been introduced unintentionally"* |
| Inconsistent clone groups that presented a fault | *"at least 3-23% … Ignoring [the Cobol outlier], the total ratio of faulty inconsistent clone groups adds up to 18%"* |
| Unintentionally-inconsistent groups that presented a fault | mean 0.50 — *"about every second to third unintentional change to a clone leads to a fault"* |
| Fault density in the inconsistencies | 3.4–91.4 faults per kLOC, mean 48.1 — against a 0.1–50/kLOC typical range |

**Barbour et al., ICSM 2011** quantifies the specific *delayed*-propagation pattern — one clone
changes, the pair goes inconsistent, and they are re-synchronised only in a later revision. *"late
propagation genealogies accounts for between 8-21% of all clone genealogies that experience at least
one change"*, and the two riskiest cases are *"(1) when a clone experiences inconsistent changes and
then a re-synchronizing change without modification to the other clone in a clone pair; and (2) when
two clones undergo an inconsistent modification followed by a consistent change that modifies both
the clones in a clone pair."* [S20] *(definitive)*

**But read the first row of the Juergens table honestly.** 52% of clone groups changed
inconsistently, and **~72% of those inconsistencies were intentional** [S18]. The dominant outcome of
copying is *deliberate divergence*, not accidental drift. The harm concentrates in the ~28% minority
that nobody meant to create.

**Negative finding, with method:** *no study was found that measures inconsistent-update faults
across copies of CI/workflow definitions specifically.* Searched arXiv and general web for empirical
work on GitHub Actions workflow duplication/cloning; the two best-matching 2026 papers study reuse
*practice* [S5] and workflow *evolution* [S6], and neither measures propagation failure across
copied workflow files. **All quantified propagation evidence in this paper is from source-code clone
research and its transfer to workflow definitions is an assumption, not a finding.**

---

## 7. Is "lineage" a recognised discriminator? — nearly, but the field's discriminator is sharper

This is the question the local measured case turns on, and it has a precise answer.

### 7.1 The recognised discriminator is *expected future co-evolution*, not *copied-from* *(definitive)*

Kapser & Godfrey's EMSE 2008 study of Apache httpd and Gnumeric partitions eleven cloning patterns
into four groups, and states the partitioning criterion explicitly [S17]:

> *"We have divided the eleven patterns into four related groups: Forking, Templating, Customization
> and Exact match. **This partitioning is done based on the high level motivation for the cloning
> pattern.** Forking is cloning used to bootstrap development of similar solutions, **with the
> expectation that evolution of the code will occur somewhat independently**, at least in the short
> term. A major motivation for forking is to protect system stability, by allowing for
> experimentation to occur away from the core system. In these types of clones, the original code is
> copied to a new source file and then independently developed. Templating is used as a method to
> directly copy behavior of existing code when appropriate abstraction mechanisms, such as
> inheritance or generics, are unavailable. Templating is used when there is a common set of
> requirements shared by the clones, such as behavior requirements or the use of a particular
> library. **When these requirements change, all clones must be maintained together.** Customization
> occurs when currently existing code does not adequately meet a new set of requirements. The
> existing code is cloned and tailored to solve this new problem. Exact match duplication is
> typically used to replicate simple solutions or repetitive concerns within the source code."*

And the headline result: *"In this study, we found that as many as **71% of the clones could be
considered to have a positive impact on the maintainability** of the software system."* [S17]

**This is the answer to the lineage question, and it is a refinement rather than a confirmation.**
Copied-from-ness is *presupposed* by every one of these patterns — all four groups are clones, all
four were copied. Lineage therefore cannot be the discriminator, because it does not vary across the
categories. What varies, and what the field partitions on, is **whether the artifacts are expected to
share requirements going forward**:

| Field's category [S17] | Expectation about future change | Structural answer |
|---|---|---|
| **Templating** | shared requirements; *"all clones must be maintained together"* | **parameterize** — this is exactly the case parameterization exists for |
| **Forking** | *"evolution … will occur somewhat independently"* | **fork, deliberately** — and the independence is the *point*, not a defect |
| **Customization** | existing code *"does not adequately meet a new set of requirements"* | **neither** — it is a requirements decision that must be settled before the structural one |
| **Exact match** | trivial repeated snippets | usually not worth either mechanism |

**Derived (this paper's central claim, from [S17] + [S18] + [S19] + [S5]):** *textual overlap is a
symptom; the operative test is whether a change to one artifact is expected to be required in the
other.* Two 95%-identical artifacts that are expected to diverge are correctly forked. Two
40%-identical artifacts whose shared 40% must always change together are correctly parameterized —
and the shared part, not the whole artifact, is what gets shared. A percentage-shared figure alone
therefore **cannot decide the ruling in either direction**; it can only tell you how much is at stake
once the co-evolution question is answered.

### 7.2 Kim et al.: the abstraction is often *discovered* through the copies *(definitive)*

Kim, Sazawal, Notkin & Murphy's FSE 2005 clone-genealogy study is the strongest evidence that the
co-evolution question is frequently unanswerable at authoring time [S19]:

> *"Our study contradicts some conventional wisdom about clones. In particular, refactoring may not
> always improve software with respect to clones for two reasons. First, many code clones exist in
> the system for only a short time; extensive refactoring of such short-lived clones may not be
> worthwhile if they are likely diverge from one another very soon. Second, many clones, especially
> long-lived clones that have changed consistently with other elements in the same group, are not
> easily refactorable due to programming language limitations."*

And, on how developers actually arrive at the shared abstraction [S19]:

> *"our subjects often appeared to discover a shared abstraction of similar code through the process
> of copying, pasting, and modifying code; they kept and maintained clones for some period of time
> before they realized how to abstract the common part of the clones."*

**Derived:** copy-then-abstract-later is a documented, effective *process*, not a failure of
discipline. It also implies the correct time to answer the fork-vs-parameterize question is **after**
the copies have been changed a few times independently — because that is the observation that reveals
whether the requirements are actually shared. A ruling made at copy time is a forecast.

### 7.3 Lineage *is* tracked mechanically — by scaffolding tools, for propagation *(definitive)*

Copier is the clearest instance of lineage-as-a-first-class-record. It writes a `.copier-answers.yml`
recording the template, its Git version and the answers given, so that a later update can *"regenerate
a fresh project from the current template version"*, *"compare both version to get the diff from
'fresh project' to 'current project'"*, apply the template changes, then *"re-applies the previously
obtained diff"* [S16]. Its stated failure mode is exactly the divergence problem: when the smart
update breaks, the fallback `copier recopy` *"will discard all the smart update algorithm"* and
behaves *"like if you were applying the template for the first time"* [S16].

**Derived:** the field's answer to "we forked and now the copies drift" is **not always "collapse
them."** A third option exists and is shipped: *keep the copies, record the lineage, and propagate
mechanically.* That is a genuine middle path between parameterize and fork, and it is the option most
often missing from a two-way framing of this decision.

---

## 8. What this provides — enumerated, citable properties

Claims a plan may rely on, each with its confidence class:

1. **Two-tier reuse (small unit + large unit) is the universal shape**, and small-grained reuse
   succeeds far more than large-grained reuse in practice: 77.4% frequent use of others' Actions vs
   22.7% for others' reusable workflows [S5]. *(definitive)*
2. **Copy-and-adapt is the dominant creation mechanism even where a first-class reuse mechanism
   exists**: 62.5% of practitioners at least frequently copy parts of their own workflows; 28.2%
   never use their own reusable workflows [S5]. *(definitive)*
3. **The stated reasons for copying are dominated by control/flexibility (43.0%) and convenience
   (40.3%), not ignorance** (unawareness 20.0%, lack of trust 4.3%) [S5]. A library that loses on
   control and convenience will be bypassed by informed engineers. *(definitive)*
4. **Parameter counts ratchet.** Removal runs ~7× slower than addition; 6.1–16.7% of parameters are
   used by a majority of users while up to 54.1% are seldom set [S21]. *(definitive)*
5. **General-purpose parameterization layers are what get deprecated**, for opacity, undebuggability,
   partial coverage and reduced reusability [S9]; and for conflating *definition* with *instantiator*
   [S7]. *(definitive)*
6. **What replaced them is explicit, typed, versioned reference** — Tekton params/workspaces/results
   [S9], the `cluster` resolver over `ClusterTask` (deprecated at v0.41.0 [S10]; *"Please use the
   `cluster` resolver instead"* [S24]), GitLab versioned components with `spec:inputs` [S13],
   Jenkins per-pipeline `@Library` version pinning [S11]. *(definitive)*
7. **A first-party design document argues that parameterizing everything is the wrong answer**, and
   that fork-plus-overlay with fork *management tooling* is a legitimate alternative [S15].
   *(definitive)*
8. **Divergence between copies causes measurable faults**: ~52% of clone groups go inconsistent, ~28%
   of those unintentionally, and roughly every second-to-third unintentional inconsistency is a fault
   [S18]; late propagation accounts for 8–21% of changing genealogies [S20]. *(definitive, but see
   the transfer caveat in §6.)*
9. **Most divergence is deliberate** — ~72% of inconsistent changes were intentional [S18] — and up
   to 71% of clones were assessed as *positive* for maintainability [S17]. *(definitive)*
10. **The field's discriminator is expected future co-evolution, not textual overlap** [S17], and
    developers frequently discover the right abstraction only *after* maintaining copies for a while
    [S19]. *(derived from [S17] + [S19]; the inference is this paper's.)*
11. **A third structural option exists: tracked lineage with mechanical propagation** (Copier's
    answers-file + three-way update) [S16]. *(definitive)*
12. **No numeric threshold for "too many parameters" is documented anywhere in the surveyed corpus.**
    The only hard numbers are platform limits (GitLab: 20 inputs [S14]; GitHub: 10/4 nesting levels
    [S1]). *(negative finding; search method in §5.2.)*

### 8.1 What the discriminator *asks* of a phase-level ruling — questions, not answers

Scope discipline: this paper does not rule on any script in this repo. It does establish that a
percentage-shared measurement is **not sufficient input** to the ruling, and that whoever makes it
must additionally answer:

- For each near-copy pair: **when one changed, did the other need the same change?** (§7.1 — this,
  not the overlap figure, is the field's test.) The evidence for it is in commit history, not in a
  diff.
- Where a pair's difference is a **requirements** difference rather than a **values** difference, the
  field classifies it as *Customization* [S17] — a behaviour decision that must be settled *before*
  the structural one, not resolved by it.
- If the answer is "parameterize," what is the **removal discipline** that prevents the [S21] ratchet?
- If the answer is "fork," is the **lineage recorded** so propagation can be mechanical rather than
  remembered [S16]?

---

## 9. Honest boundary analysis — where a shared library is the wrong answer

### 9.1 The case against action candidate #4, stated at full strength

**A shared library is the wrong answer when the interface costs more than the artifact.** This is the
practitioner consensus in [S5], stated bluntly: *"Most steps are less than 5 lines of bash. I don't
want complexity spread across multiple locations"*; *"If an Action is actually really simple, it's
better to copy it"*; *"Indirection makes it harder to reason about."* 43.7% of all respondents said
adopting a reuse mechanism would add complexity [S5]. **The library is not free; it is a trade of
duplication cost for indirection cost, and below some artifact size the trade is bad.**

**It is the wrong answer when the abstraction would be worse than the duplication.** Kapser & Godfrey:
*"aggressive refactoring can sometimes create abstractions that are complex, overly subtle, and
unintuitive; in this case, near duplicates may be easier to understand and modify than a solution
that employs abstraction"* [S17]. Metz's essay is the same claim from practice [S22].

**It is the wrong answer for short-lived artifacts.** *"[M]any code clones exist in the system for
only a short time; extensive refactoring of such short-lived clones may not be worthwhile if they are
likely diverge from one another very soon"* [S19]. A workflow shelf under active redesign is exactly
this case.

**It is the wrong answer when independence is the requirement.** Forking's stated motivation is *"to
protect system stability, by allowing for experimentation to occur away from the core system"* [S17].
A shared child means a change to satisfy one caller is a change shipped to *every* caller — the
blast-radius property Jenkins warns about in its own terms (*"anyone able to push commits to this SCM
repository could obtain unlimited access to Jenkins"* [S11]) and that GitHub's reuse chain mitigates
with explicit non-inheritance of secrets and non-elevating permissions [S1]. **Copies fail one
consumer; shared definitions fail all of them.** No source in this corpus measures that trade
directly — it is stated as a structural property, not a measured one. *(derived)*

**And the whole premise has a documented dissent.** [S15] argues parameterization *"tend[s] to become
complex and difficult to maintain"* and that *"Fork provides one-time customization, which is the
most common case"*, proposing that the correct investment is fork-*management* tooling. Kustomize
exists because that argument won inside Kubernetes. Treating the shared library as the first-class
artifact is a defensible position, but it is **not the field's consensus** — it is one side of a live
disagreement between the CI/CD systems (which parameterize) and the Kubernetes config lineage (which
overlays and forks).

### 9.2 Where this paper's own central claim is weak

- **The co-evolution test is a forecast, not a measurement.** [S19] is direct evidence that developers
  often cannot answer it at authoring time. A rule built on it *looks* rigorous while resting on a
  prediction, and will be applied confidently and wrongly. The mitigation — decide after observing a
  few independent changes — costs time and is not always available before a third copy is created.
- **The transfer from source-code clones to workflow scripts is assumed.** [S17]–[S20] study C, C#,
  Java and Cobol at function/file granularity in systems orders of magnitude larger than a workflow
  shelf. Nothing establishes that a shelf of ~10 bash scripts behaves like a clone group in a 1M-LOC
  system. *(This is the single largest validity threat in the paper.)*
- **Nothing in the corpus studies duplicated *prompt prose*.** Our shared artifacts are substantially
  LLM prompt text, whose failure modes (semantic drift, instruction interference, context budget) are
  not code-clone failure modes and are not covered by any cited source. The CI analogy may hold for
  the bash and break for the prompts.
- **N=419 survey respondents are self-selected**, and [S5]'s reuse-mechanism analysis restricts to
  respondents who reported copy-pasting (74.9–79.7% subpopulations) — the percentages in §4 are
  within-subpopulation, not population-wide, wherever the paper says so.
- **The 2005–2015 empirical core predates modern tooling.** Automated refactoring, IDE clone
  detection, and LLM-assisted editing all change the cost of both options. [S6] explicitly looked for
  and *"did not find any conclusive evidence of the effect of LLM coding tools"* on workflow
  maintenance frequency [S6] — which is a null result on adoption timing, not evidence that costs are
  unchanged.
- **One relevant first-party source could not be verified.** HashiCorp's Terraform module-authoring
  guidance (widely reported to advise against thin-wrapper modules) was **not obtained from a raw
  first-party source** — the expected paths in `hashicorp/terraform` 404'd and only secondary
  summaries were available. It is therefore **excluded** from this paper's evidence rather than cited
  at low confidence. *(negative finding: searched `raw.githubusercontent.com/hashicorp/terraform`
  website paths + web search.)*

---

## 10. Test plan — what research cannot settle

Each item is a local experiment, with what it would decide.

1. **Measure actual co-evolution, not overlap.** For every near-copy pair on the shelf, walk the
   commit history: how many commits touched one member, and of those, how many required the same
   change in the other within N commits? **Decides:** whether the pair is Templating (co-evolving →
   parameterize) or Forking (independent → keep forked), per §7.1. This is the single measurement
   that converts the field's discriminator into a local answer, and no cited source can supply it.
2. **Count local late propagations.** In the same history, count changes applied to one member and
   mirrored only in a later commit — Barbour's pattern [S20]. **Decides:** whether the divergence
   risk is real here or hypothetical. A count of zero across the shelf's life is strong evidence
   against urgency.
3. **A/B the parameterized child against a dedicated child on real dispatches.** Same task, one
   invocation through a shared child taking a lens/sizing input, one through a purpose-built child.
   **Decides:** whether parameterization costs *run quality* (not just author convenience) when the
   parameterized artifact is an LLM prompt. Nothing in the literature covers this.
4. **Localise the differing lines.** For each pair, classify differing lines as control flow, config,
   or prompt prose. **Decides:** whether the CI/clone analogy transfers at all — if the divergence is
   overwhelmingly prompt prose, §6's fault-rate evidence does not apply and the honest answer is
   "unstudied."
5. **Instrument the parameter ratchet.** After any parameterization lands, track inputs added vs
   removed per quarter. **Decides:** whether [S21]'s 7× asymmetry reproduces at this scale. This is
   the falsifiable prediction of §5.1, and the trigger for a removal pass.
6. **Measure blast radius empirically.** When a shared child changes, how many callers required
   re-testing, and how many broke? **Decides:** the counterweight to propagation risk, which §9.1
   asserts structurally and no source measures.
7. **Cost the interface.** Time-to-first-successful-dispatch and time-to-debug for a shared child vs
   a copy. **Decides:** whether the [S5] practitioner objection (*"indirection makes it harder to
   reason about"*) holds for this shelf, where the caller and callee are authored by the same person.
8. **Prototype tracked lineage before choosing between the two-way options.** Record a
   `copied-from: <path>@<commit>` provenance line on any deliberate copy and check, after one
   quarter, whether it was ever used. **Decides:** whether §7.3's third option is viable here or is
   ceremony. Cheap to run and rules out an option that the two-way framing never surfaces.

---

## 11. Citations

**First-party documentation (fetched raw per Research Standard §4):**

- **[S1]** GitHub Docs — *Reusing workflows*. `raw.githubusercontent.com/github/docs/main/content/actions/how-tos/reuse-automations/reuse-workflows.md` (fetched 2026-08-03)
- **[S2]** GitHub Docs — *Creating a composite action*. `raw.githubusercontent.com/github/docs/main/content/actions/tutorials/create-actions/create-a-composite-action.md` (fetched 2026-08-03)
- **[S3]** GitHub Docs — *Actions limits*. `raw.githubusercontent.com/github/docs/main/content/actions/reference/limits.md` (fetched 2026-08-03) — *negative check: no `workflow_call` input cap stated*
- **[S4]** GitHub Docs — *Workflow syntax reference*. `raw.githubusercontent.com/github/docs/main/content/actions/reference/workflows-and-actions/workflow-syntax.md` (fetched 2026-08-03) — *negative check*
- **[S7]** Argo Workflows — *Workflow Templates*, release-3.4. `raw.githubusercontent.com/argoproj/argo-workflows/release-3.4/docs/workflow-templates.md` (fetched 2026-08-03)
- **[S8]** Argo Workflows — *Workflow Templates*, main. `raw.githubusercontent.com/argoproj/argo-workflows/main/docs/workflow-templates.md` (fetched 2026-08-03) — *negative check: deprecation passage absent*
- **[S9]** Tekton Pipelines — *PipelineResources*. `raw.githubusercontent.com/tektoncd/pipeline/main/docs/resources.md` (fetched 2026-08-03)
- **[S10]** Tekton Pipelines — *Deprecations*. `raw.githubusercontent.com/tektoncd/pipeline/main/docs/deprecations.md` (fetched 2026-08-03) — *lists `ClusterTask` deprecation and the resolver-framework deprecation as two independent rows; it does NOT state a causal replacement. See [S24] for that.*
- **[S24]** Tekton Pipelines — *Migrating from v1beta1 to v1*. `raw.githubusercontent.com/tektoncd/pipeline/main/docs/migrating-v1beta1-to-v1.md` (fetched 2026-08-03) — *source of the `ClusterTask` → `cluster` resolver replacement statement*
- **[S11]** Jenkins — *Extending with Shared Libraries*. `raw.githubusercontent.com/jenkins-infra/jenkins.io/master/content/doc/book/pipeline/shared-libraries.adoc` (fetched 2026-08-03)
- **[S12]** Apache Airflow — *Best Practices*. `raw.githubusercontent.com/apache/airflow/main/airflow-core/docs/best-practices.rst` (fetched 2026-08-03)
- **[S13]** GitLab — *CI/CD components*. `raw.githubusercontent.com/gitlabhq/gitlabhq/master/doc/ci/components/_index.md` (fetched 2026-08-03)
- **[S14]** GitLab — *CI/CD inputs*. `raw.githubusercontent.com/gitlabhq/gitlabhq/master/doc/ci/inputs/_index.md` (fetched 2026-08-03)
- **[S15]** B. Grant et al. — *Declarative Application Management in Kubernetes* (design proposal). `raw.githubusercontent.com/kubernetes/design-proposals-archive/main/architecture/declarative-application-management.md` (fetched 2026-08-03)
- **[S16]** Copier — *Updating a project*. `raw.githubusercontent.com/copier-org/copier/master/docs/updating.md` (fetched 2026-08-03)

**Peer-reviewed research (primary PDFs read directly):**

- **[S5]** H. Onsori Delicheh, G. Cardoen, A. Decan, T. Mens — *Automation and Reuse Practices in GitHub Actions Workflows: A Practitioner's Perspective*. ACM TOSEM, 2026. arXiv:2601.11299. https://arxiv.org/abs/2601.11299 (PDF read: §4.2, §4.3, §5.1, §5.2)
- **[S6]** P. Rostami Mazrae, A. Decan, T. Mens, M. Wessel — *An Empirical Study of the Evolution of GitHub Actions Workflows*. Journal of Systems and Software 236, 2026. arXiv:2602.14572. https://arxiv.org/abs/2602.14572 (abstract)
- **[S17]** C. J. Kapser, M. W. Godfrey — *"Cloning considered harmful" considered harmful: patterns of cloning in software*. Empirical Software Engineering 13(6), 2008. https://plg.uwaterloo.ca/~migod/papers/2008/emse08-ClonePatterns.pdf (PDF read: abstract, §2, §3)
- **[S18]** E. Juergens, F. Deissenboeck, B. Hummel, S. Wagner — *Do Code Clones Matter?* ICSE 2009. https://teamscale.com/hubfs/Publications/2009-do-code-clones-matter.pdf (PDF read: abstract, §5, §6, Table 2)
- **[S19]** M. Kim, V. Sazawal, D. Notkin, G. C. Murphy — *An Empirical Study of Code Clone Genealogies*. ESEC/FSE 2005. https://web.cs.ucla.edu/~miryung/Publications/esecfse05-clonegenealogy.pdf (PDF read: abstract, §1)
- **[S20]** L. Barbour, F. Khomh, Y. Zou — *Late Propagation in Software Clones*. ICSM 2011. https://seal-queensu.github.io/publications/pdf/ICSME-Liliane-2011.pdf (PDF read: abstract, §1)
- **[S21]** T. Xu, L. Jin, X. Fan, Y. Zhou, S. Pasupathy, R. Talwadker — *Hey, You Have Given Me Too Many Knobs! Understanding and Dealing with Over-Designed Configuration in System Software*. ESEC/FSE 2015. https://dl.acm.org/doi/10.1145/2786805.2786852 (PDF read: abstract, §1.1, §1.2, §2)

**Commentary and folklore (labelled as such):**

- **[S22]** S. Metz — *The Wrong Abstraction*, 2016. https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction — *rendered page; quoted conservatively. Influential practitioner essay, not peer-reviewed.*
- **[S23]** *Rule of three (computer programming)* — the "three strikes and you refactor" heuristic, popularised in Fowler's *Refactoring* (1999) and attributed there to Don Roberts. https://en.wikipedia.org/wiki/Rule_of_three_(computer_programming) — *secondary source; cited only to establish that the field's one numeric heuristic is anecdote-attributed. The primary book text was not verified.*

**Consulted and deliberately excluded:**

- HashiCorp Terraform module-authoring / module-composition guidance — could not be obtained from a raw first-party source (expected `hashicorp/terraform` website paths returned 404); only secondary summaries were available. Excluded rather than cited at reduced confidence. See §9.2.
