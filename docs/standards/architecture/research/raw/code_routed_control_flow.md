# Code-Routed Control Flow Over Typed Agent Results

```
Topic:          Should the decision of WHAT RUNS NEXT be made by code reading a typed value,
                rather than by a model reading prose? Is that premise sound, and is it
                DISTINGUISHING — or is it what every deterministic orchestrator already does?
Feeds:          `docs/standards/architecture/problem-statement.md` elements 3 and 4 (typed
                results a next step reads in code, "with no model in the loop"; and a driver
                doing if/then/else over the results of entire workflows); AND
                `docs/standards/architecture/system-overview.md` § *What is not built*
                ("a parent still routes on a parsed token rather than a structured result").
Last validated: 2026-08-03
Revalidate:     high — 6 weeks
Confidence:     DEFINITIVE on what each cited framework documents as its own routing model —
                every claim in §2 rests on a fetched first-party doc. Raw-markdown provenance
                (the strongest tier) covers Google ADK ×2, OpenAI Agents SDK, Tekton tasks +
                TEP-0074, Airflow, Argo, GitHub Docs reusables and 12-Factor Agents; Microsoft
                Agent Framework, AWS Step Functions and Airflow's rendered siblings were
                retrieved as full document text and read directly rather than through a
                summariser, which is the second tier. DEFINITIVE on the OpenAI Structured
                Outputs guarantee and on its stated limits. DEFINITIVE on what each cited study
                measured. DEFINITIVE on the central NEGATIVE finding (N1): no head-to-head
                measurement of code-routing versus model-routing of CONTROL FLOW exists in the
                located literature.
                RENDERED-PAGE CARVE-OUT (applied consistently): a SHORT VERBATIM SPAN quoted
                from a rendered page is marked definitive ON THE QUOTE where the span was
                re-verified; any inference, figure or paraphrase drawn from a rendered page
                stays directional. This covers [S2], [S23], [S9], [S10], [S11] and [S28].
                DIRECTIONAL on the four 2026 preprints (2604.27891 — five authors;
                2607.17044 — one named author plus a team; 2605.14102 and 2607.18476 —
                single-author) and on the vendor-interested rebuttal [S28].
                UNVERIFIED on the GitHub Actions 1 MB / 50 MB output caps — the figure did not
                appear in the fetched primary (N4) — and on the Tekton termination-message
                causal story. DERIVED, and flagged inline, on §0's verdict, §2.4.2, §4.4,
                §5 P2/P7/P9/P11 and §6.6.
Critic:         PASS-WITH-FIXES (CrewAI removed from the six and N6 re-scoped, with ADK's graph
                routing example added; [S24] false-switch rate corrected 0.03%→3% and §6.4
                re-argued; three quotations restored or unquoted; [S11] unrelated-input case
                re-grouped; rendered-page and raw-provenance labels made consistent; preprint
                authorship descriptor corrected) — 2026-08-03
```

> **Mixed volatility (§3).** The **high-volatility** material is §2.1–2.3 and §3.2 (agent-framework
> routing APIs move with SDK releases — Google ADK already marks its template workflows
> superseded) and the 2026 preprints in §3. The **low-volatility** material is §2.4 (CI/CD
> result-passing caps and the Tekton deprecation, stable for years), §4.1–4.2 (constrained
> decoding), and §1's taxonomy. The header takes the highest tier present.

---

## 0. Headline: the premise is sound, the binary is false, and as stated the premise is ORDINARY

Three findings, in order of how much they should change the problem statement.

**1. The two-way framing does not describe the field.** Five production frameworks whose
routing documentation was fetched for this paper — LangGraph, Microsoft Agent Framework,
Google ADK, Temporal, Restate — converge on the *same* middle pattern: **a model
emits a value from a closed vocabulary, and ordinary code branches on that value.** This is not
a compromise between the two poles; it is the canonical example in each vendor's own docs
(§2.2). The thesis's "no model in the loop" is true of the **branch** and false of the
**decision**: the model still decided, it just decided in a typed field instead of a paragraph.
*(CrewAI Flows was checked and is deliberately NOT in this five — its one `@router()` example
branches on a value no model produced. That exception is the subject of finding 3(b).)*

**2. There is no measured evidence that code-routing beats model-routing on control flow.**
Not weak evidence — **none located** (N1). What exists is (a) vendors *asserting* the benefit
("Improve the predictability of your agents by relying on structured node definitions rather
than prompts alone" — Google ADK [S5]), (b) a measured *accuracy ceiling* on model routing
(90–92% classification accuracy, <3% false switch on a curated enterprise benchmark [S24]),
(c) measured *instability* of repeated model decisions (τ-bench `pass^8 <25%` in retail [S20]),
and (d) two 2026 preprints measuring orchestration as a **net loss** against letting the model
self-orchestrate (§6.1, §6.2). The preference is asserted, and the strongest measured results
in the corpus point the *other* way.

**3. Verdict on the premise, stated plainly as the dispatch requires — DERIVED.** As worded
("routing decisions are made by code over typed state"), the premise is **ordinary**: it is
what an AWS Step Functions `Choice` state does [S8], what every CI/CD system does with job outputs
(§2.4), and what this repo already does today with `grep -oE '^VERDICT: (MERGE|HOLD - ...)$'`
plus a `case` statement [I1]. Elevating it to a novelty element is not supportable. **Two
narrower readings are not ordinary**, and the problem statement should be re-cut to one of
them if it wants a defensible claim:

- **(a) Altitude.** Every framework conditional edge located routes *within one graph, one
  process, one run*. Elements 3–4 route **across whole workflow runs that are separate OS
  processes with disjoint contexts, resumed from persisted state**. The only prior art located
  at that altitude is CI/CD (§2.4) — non-agentic — and it arrived there by hitting hard caps
  and one full deprecation (§2.4.2), which is exactly the evidence a design at that altitude
  should be reading.
- **(b) Literal "no model in the loop."** A predicate over a value **the model did not choose**
  — an exit code, an empty diff, a test result, a finding-set difference — is a strictly
  stronger and genuinely different claim, and it is the one the pool's own
  `convergence_stopping.md` P11 depends on. **The pattern is not absent from the docs, but the
  one located instance is a toy.** CrewAI's sole `@router()` example branches on
  `random.choice([True, False])` stored in Pydantic state [S7] — a non-model value, and
  therefore a genuine counter-example to any unqualified claim that the field never routes this
  way, but a synthetic illustration of the decorator rather than a result produced by a
  completed unit of work. Re-scoped honestly (N6): **no located agent-framework doc presents a
  non-model value *carrying the outcome of real work* as its canonical branching example.**
  That narrower gap is real and is the strongest available reading of element 3.

Everything below is the evidence for those three.

---

## 1. Primer: "routing" is three questions, not one

The literature collapses three independent questions into the word "routing." Separating them
is what makes the middle position visible.

| # | Question | Answers in the wild |
|---|---|---|
| **Q1. Who *decides*?** | A model, or code | model / code |
| **Q2. What is the decision *carried in*?** | Prose, a parsed token, a typed field, a non-model observable | prose / token / typed / observable |
| **Q3. Who *executes* the branch?** | A model choosing a next tool, or code evaluating a predicate | model / code |

The problem statement's element 3 conflates Q1 and Q3. The field's convergent answer is
**Q1 = model, Q2 = typed field from a closed vocabulary, Q3 = code** (§2.2). The pure
"agent" pole is model/prose/model; the pure "workflow" pole is code/typed/code.

The canonical vocabulary comes from Anthropic's engineering post, which is the reference both
LangChain and the 12-factor essay cite:

> "Workflows are systems where LLMs and tools are orchestrated through predefined code paths."
> — [S2]

> "Agents, on the other hand, are systems where LLMs dynamically direct their own processes and
> tool usage, maintaining control over how they accomplish tasks." — [S2]

> "Routing classifies an input and directs it to a specialized followup task." — [S2]

And the post's own guidance on *when* routing is appropriate names the load-bearing
precondition, which the rest of this paper is largely about:

> routing "works well for complex tasks where there are distinct categories that are better
> handled separately, and where classification can be handled accurately, either by an LLM or a
> more traditional classification model/algorithm." — [S2]

*(Confidence: **definitive on the quotes**, per the header's rendered-page carve-out — short
verbatim spans only, and no figure or inference is drawn from this page. LangChain's own docs
restate the same distinction — "Workflows
have predetermined code paths and are designed to operate in a certain order" / "Agents are
dynamic and define their own processes and tool usage" [S1] — from a `.md` fetch.)*

---

## 2. What production systems actually do

### 2.1 The model-routed pole is real, first-party, and defended on the merits

**OpenAI Agents SDK — handoffs are tool calls.** The routing decision is exposed to the model
as a callable:

> "Handoffs are represented as tools to the LLM. So if there's a handoff to an agent named
> `Refund Agent`, the tool would be called `transfer_to_refund_agent`." — [S3, raw markdown]

The same doc's guidance for multi-destination routing is to "register one handoff per
destination and let the model choose among them" [S3]. Q1, Q2 and Q3 are all the model.

**Anthropic's own multi-agent research system** is orchestrator-worker with a model at the top,
and the post states the design rationale as a rejection of code-routing for that task shape:

> "When a user submits a query, the lead agent analyzes it, develops a strategy, and spawns
> subagents to explore different aspects simultaneously." — [S23]

> "You can't hardcode a fixed path for exploring complex topics, as the process is inherently
> dynamic and path-dependent." — [S23]

*(Confidence: **definitive on the quotes**, per the header's rendered-page carve-out — short
verbatim spans only. This is the single strongest first-party statement against the thesis's
premise and is treated as such in §6.)*

**The published hierarchical architectures route by model.** The pool's own
`raw/hierarchical_agents.md` establishes this across AgentOrchestra, HALO, AiScientist and
CORPGEN — each puts an LLM planner at the top. That paper is cited here rather than repeated.

### 2.2 The convergent middle: a model emits a closed-vocabulary verdict, code branches on it

This is the finding that dissolves the dispatch's binary. **Five** independent first-party
sources document the *same* pattern as their canonical example. Provenance, since it is this
paper's reliability warrant: **two raw markdown** (Google ADK ×2, `raw.githubusercontent.com`),
**one docs-`.md`** (LangChain), **one full document text read directly rather than through a
summariser** (Microsoft Agent Framework), and **two rendered vendor pages** quoted in short
verbatim spans only (Temporal, Restate). A sixth framework, CrewAI, was checked and **does
not** document this pattern — §2.2.4 states what it documents instead, because a survey that
silently drops its disconfirming case is not a survey.

The same convergence is reported from outside the vendors by the 12-Factor Agents essay —
"most of the products out there billing themselves as \"AI Agents\" are not all that agentic. A
lot of them are mostly deterministic code, with LLM steps sprinkled in at just the right points"
[S32] — which is uncorroborated single-author commentary and is used here only as corroboration
of a pattern already established by the five first-party sources below.

**2.2.1 LangGraph.** The Routing workflow in LangChain's own docs is a structured-output call
constrained to a `Literal`, followed by a plain `if/elif` over the stored decision:

```python
class Route(BaseModel):
    step: Literal["poem", "story", "joke"] = Field(
        None, description="The next step in the routing process"
    )

router = llm.with_structured_output(Route)
...
def route_decision(state: State):
    if state["decision"] == "story":
        return "llm_call_1"
    elif state["decision"] == "joke":
        return "llm_call_2"
    elif state["decision"] == "poem":
        return "llm_call_3"
```
— [S1], reproduced from the docs `.md`. Note there is **no `else`**: an unanticipated value
falls off the end of the function.

**2.2.2 Microsoft Agent Framework** documents the same shape with more machinery, and — more
valuably — documents its **failure handling inline**, which §5 mines for the cost side. The
detector agent is pinned to a Pydantic model via `response_format`, and the edge predicate
parses that model:

```python
class DetectionResult(BaseModel):
    """Represents the result of spam detection."""
    # is_spam drives the routing decision taken by edge conditions
    is_spam: bool
```
```python
    def condition(message: Any) -> bool:
        # Defensive guard. If a non AgentExecutorResponse appears, let the edge pass to avoid dead ends.
        if not isinstance(message, AgentExecutorResponse):
            return True
        try:
            detection = DetectionResult.model_validate_json(message.agent_response.text)
            return detection.is_spam == expected_result
        except Exception:
            # Fail closed on parse errors so we do not accidentally route to the wrong path.
            # Returning False prevents this edge from activating.
            return False
```
— [S6]. And the receiving executor re-checks the invariant the predicate was supposed to
guarantee, with the comment naming the failure mode:

```python
    else:
        # This indicates the routing predicate and executor contract are out of sync.
        raise RuntimeError("This executor should only handle spam messages.")
```
— [S6].

The switch-case variant is the one that matters most for this paper, because it is the
**closed-vocabulary-with-residual** pattern the dispatch asked whether the field had converged
on:

```python
    spam_decision: Literal["NotSpam", "Spam", "Uncertain"]
```
with `handle_uncertain` yielding the original content for human review [S6]. The doc's own
summary of why switch-case beats chained conditionals is the branch-management argument:

> "**Guaranteed Routing**: The default case ensures messages never get stuck" — [S6]

> "The switch-case pattern scales much better as the number of routing decisions grows, and the
> default case provides a safety net for unexpected values." — [S6]

*(Confidence: definitive. This content was read directly from the fetched document text, not
from a summarizer's paraphrase.)*

**2.2.3 Google ADK.** Template workflow agents are the explicitly-non-model tier:

> "Template workflow agents operate based on predefined logic. They determine the execution
> sequence according to their type, such as sequential, parallel, or loop, without consulting an
> AI model for assistance with the orchestration. This approach results in deterministic and
> predictable execution patterns." — [S4, raw markdown]

The same raw file carries a forward-looking note that matters for revalidation:

> "Starting in ADK 2.0 for Python and Go, template workflows have been superseded
> by more flexible workflow structures, including
> [graph-based workflows](/graphs/) and
> [dynamic workflows](/graphs/dynamic/)." — [S4, raw markdown]

The graph docs then make the typed-handoff claim explicitly — "The framework automatically
passes each node's typed return value to the next node via `event.Output`" — and offer two
selling points that are exactly the thesis's, **asserted without measurement**:

> "Run chains of functions without AI: Call agent tools and your own code without invoking a
> generative AI model" — [S5]

> "Enhance reliability: Improve the predictability of your agents by relying on structured node
> definitions rather than prompts alone" — [S5]

And the graph docs' own routing sample is the pattern in its purest form — a model classifies
into a closed vocabulary, a plain function normalises the string, and a **dict** dispatches:

```python
    process_message = Agent(
        name="process_message",
        model="gemini-flash-latest",
        instruction="""Classify user message into either "BUG", "CUSTOMER_SUPPORT",
          or "LOGISTICS". If you think a message applies to more than one category,
          reply with a comma separated list of categories.
       """,
        output_schema=str,
    )

    def router(node_input: str):
        routes = node_input.split(",")
        routes = [route.strip() for route in routes]
        return Event(route=routes)
...
           ( router,
               {
                   "BUG": response_1_bug,
                   "CUSTOMER_SUPPORT": response_2_support,
                   "LOGISTICS": response_3_logistics,
               }
           )
```
— [S5, raw markdown]. **Note what is missing:** `output_schema=str`. The closed vocabulary is
enforced by the *prompt*, not by a schema or a decoder, and the instruction explicitly invites
a multi-value answer. Any category the model invents simply fails to match a dict key. This is
the §4.1 guarantee **not** being used, in the docs of a vendor that markets the pattern on
predictability. *(Confidence: definitive on the code and on the absence of an enum; **derived**
on the consequence.)*

**2.2.4 CrewAI Flows — the checked case that does NOT fit, and why it matters.** The mechanism
is the same shape: `@router()` returns a label, `@listen("label")` methods subscribe to it, and
state is a Pydantic `BaseModel` parameterised onto the Flow class ("**Type Safety**: Leveraging
Pydantic ensures that state attributes adhere to the specified types, reducing runtime errors."
[S7]). **But the docs' only `@router()` example routes on a value no model produced:**

```python
    @start()
    def start_method(self):
        print("Starting the structured flow")
        random_boolean = random.choice([True, False])
        self.state.success_flag = random_boolean

    @router(start_method)
    def second_method(self):
        if self.state.success_flag:
            return "success"
        else:
            return "failed"
```
— [S7]. This is a synthetic illustration of the decorator, not a claim about where routing
values come from. It is recorded prominently for one reason: **it is the documented
counter-example to N6's earlier unqualified form**, and it is the reason N6 and P2 are now
scoped to values *carrying the outcome of real work* rather than to non-model values in
general. *(Confidence: definitive on the code; the re-scoping is this paper's own judgement and
is marked derived at P2.)*

**2.2.5 Temporal — the durable-execution vendor's answer to "where does the model sit."**
Temporal's position is that the model's decision is an *activity result* and the workflow
dispatches on it:

> "While Temporal requires that your Workflow code is deterministic, your AI Agent can
> absolutely make decisions based on non-deterministic LLM outcomes." — [S9]

> "next_action.tool could be ANY of your activities" … "It's determined at runtime by the LLM,
> not hardcoded" — [S9]

The accompanying loop calls `llm_decide_next_action` as an activity and passes
`next_action.tool` straight into `workflow.execute_activity(...)` [S9]. *(Confidence:
**definitive on the quotes**, per the header's rendered-page carve-out — the three short spans
above appeared identically across two independent fetches of the page. The code block appeared
in one fetch only and is described rather than relied upon.)*

**2.2.6 Restate** documents the same division for its durable-agent pattern: the developer
writes the loop explicitly, the code checks the model's finish reason (final answer vs. tool
calls) and dispatches, and "Every LLM call, tool execution, and routing decision is durably
persisted" [S10]. *(Rendered docs page — directional.)*

**2.2.7 This repo already implements the middle position.** `revision.sh` extracts a closed
verdict vocabulary from a child's stdout and `case`s on it, with a fail-closed default:

```bash
VERDICT_LINE=$(grep -oE '^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$' "$log" | tail -1)
if [[ -z "$VERDICT_LINE" ]]; then
    ...
    VERDICT_LINE="VERDICT: HOLD - needs-assistance"
fi
```
— [I1]. The comment above it states the intent in exactly the problem statement's terms: "The
terminal VERDICT line IS the interface — review-pr aggregates the per-finding hold_kind values
into one routing token so the caller never re-derives a judgement the reviewer already made"
[I1]. **The delta between what is shipped and what element 3
describes is Q2 only — regex-over-stdout versus a typed value.** That is a robustness upgrade
inside an already-code-routed system, not a new control-flow model.

### 2.3 The pure code-routed pole: AWS Step Functions

The oldest and most rigorous instance, and the one whose documented edges are most useful.

> "A `Choice` state (`"Type": "Choice"`) adds conditional logic to a state machine." — [S8]

> "When a `Choice` state is run, Step Functions evaluates each **Choice Rule** to true or false.
> Based on the result, Step Functions transitions to the next state in the workflow." — [S8]

Two documented properties are directly load-bearing for §5:

> "If no **Choices** evaluate to true when the workflow runs, and no **Default** is provided,
> the state machine will throw an **error** due to a *failure to transition out of the state*."
> — [S8]

> "Step Functions doesn't attempt to match a numeric field to a string value." — [S8]

The JSONPath dialect exposes explicit type predicates (`IsBoolean`, `IsNull`, `IsNumeric`,
`IsPresent`, `IsString`, `IsTimestamp`) alongside the comparators [S8] — i.e. a 10-year-old
production system's answer to "the producer might emit something the schema did not anticipate"
is *make the type test a first-class routing primitive and require a default*. *(Confidence:
definitive — full documentation text fetched.)*

### 2.4 CI/CD: the only prior art at element 3's altitude, and its hard-won limits

CI/CD systems route across **separate processes** on typed step results. This is the closest
structural analogue to a parent branching on a child workflow's conclusion, and its documented
caps are the field's accumulated scar tissue.

**2.4.1 Every one of them caps the payload, and says so.**

| System | Documented limit on inter-step results | Source |
|---|---|---|
| Tekton | "This feature allows users to store up to 4 KB per result by default." (sidecar-logs feature; the base mechanism is smaller) | [S13, raw md] |
| Argo Workflows | "Argo stores workflows as Kubernetes resources (i.e. within EtcD). This creates a limit to their size as resources must be under 1MB." | [S15, raw md] |
| Airflow XCom | XComs "are only designed for small amounts of data; do not use them to pass around large values, like dataframes." | [S14, raw rst] |
| GitHub Actions | Fetched primary documents redaction and matrix collision, **not** a size cap — see N4 | [S16] |

Argo's remediation list is itself the design lesson: compress the node status, offload it to
SQL, or **restructure the workflow** — "Use [workflows of workflows](workflow-of-workflows.md)
to factor a large workflow into a workflow of smaller workflows" [S15]. Argo also offloads
container arguments over 128 KB to a ConfigMap and replaces individual >128 KB arguments with
`@/tmp/argo_arg_N.txt`, with the explicit warning that "**Downstream programs must support the
`@filename` syntax**" [S15] — i.e. the typed channel leaks its own transport into the contract
between independently-evolving steps.

Two documented non-size hazards, both first-party:

> "Outputs containing secrets are redacted on the runner and not sent to {% data
> variables.product.prodname_actions %}" — [S16, raw md, liquid template as in source]

> "ensure that the output name is unique, otherwise the last matrix job that runs will override
> the output value." — [S16, raw md]

The first is a *silent* value change on the routing channel; the second is a *silent*
last-writer-wins on fan-in. Neither is a schema violation. Both would make a code-router branch
on a well-formed wrong value.

**2.4.2 The deprecation is the most valuable single artifact here.** Tekton had a richer typed
inter-step abstraction — `PipelineResources` — and **removed it**. TEP-0074's stated reasons:

> "Using a PipelineResource in a Task couples the Task to this PipelineResource," — [S17, raw md]

> "It was very hard to describe concretely what the purpose of PipelineResources is (a strong
> hint that the abstraction is not right)." — [S17, raw md]

> "The line between the functionality provided by PipelineResources and Tasks is not clear," — [S17, raw md]

The replacement is **plain results plus ordinary tasks**. *(Confidence: definitive on the
quotes. **Derived** consequence, and the one this repo should read: the field's one serious
attempt at a rich typed handoff object between independently-authored steps was withdrawn for
coupling and conceptual opacity, and the surviving design is a small, dumb, size-capped
key/value result. A typed-handoff design at this altitude is arguing against a documented
retreat and owes an explanation of why it will not repeat it.)*

---

## 3. Is the preference measured or asserted? — the central discrimination

### 3.1 The scoreboard

| Claim | Status | Evidence |
|---|---|---|
| Code-routing improves **reliability** vs model-routing | **Asserted, not measured** (N1, N2) | Google ADK "Enhance reliability … rather than prompts alone" [S5]; MS "the default case provides a safety net" [S6]; Temporal, Restate positioning [S9], [S10]. No experiment located. |
| Code-routing improves **determinism** | **Definitionally true; measured only for model-selection routing** | ORCH reports "The deterministic routing and merge pipeline improves stability across runs" — but its routing selects *which model answers*, not *which step runs* [S22]. |
| Code-routing improves **cost** | **Not measured for control flow** (N2) | The nearest measured cost result is in the pool: judge-gated convergence detection at **+129% tokens** — the detector outspending the saving (`convergence_stopping.md` P10). |
| Code-routing improves **debuggability** | **Not measured** (N2) | Asserted by every vendor; located only in uncorroborated commentary otherwise. |
| Model routing is **inaccurate enough to matter** | **Measured** | 90–92% routing classification accuracy, up to **3%** false switch, ~350 ms latency, on curated enterprise scenarios [S24]. |
| Repeated model decisions are **unstable** | **Measured** | τ-bench: "even state-of-the-art function calling agents (like gpt-4o) succeed on <50% of the tasks, and are quite inconsistent (pass^8 <25% in retail)" [S20]. |
| Multi-agent coordination fails in characteristic ways | **Measured** | MAST: 1600+ annotated traces, 7 frameworks, 14 failure modes in 3 categories including "inter-agent misalignment", κ=0.88 [S21]. |
| Orchestration **helps** | **Contradicted twice in 2026 (both directional)** | §6.1 [S18]; §6.2 [S19]. |

### 3.2 The one paper that decomposes where reliability comes from

`Where Does Agent Reliability Come From?` [S25] evaluates a production enterprise agent across
SpreadsheetBench Verified, BullshitBench v2 and GAIA validation. The gains are reported
per-benchmark, not as a range — verbatim:

> "The full system improves over its frontier base model by +11.0 percentage points on
> SpreadsheetBench (91.25% vs 80.25%, n=400, p<0.001), +7 to +10 percentage points on
> BullshitBench (98% vs 91%, n=100), and roughly +15 points on GAIA validation (75.2% pass@1,
> n=165; 83.0% best-of-k)." — [S25]

And the attribution, also verbatim:

> "most of it comes from scaffolding, routing, and specialist models rather than from the
> verification step itself, whose isolated contribution is small (+1.5 points) but concentrated
> at the top of the score distribution, where it converts otherwise-failing tasks." — [S25]

*(An earlier draft compressed the three figures into a quoted "+7 to +15 percentage points
across benchmarks" and quoted "only +1.5 points". Neither string is in the source. The
synthesis was defensible; presenting it inside quotation marks was not.)*

**Read carefully, because it is the most cite-able number on the pro-scaffolding side and it
does not say what one would want it to say.** It attributes gain to scaffolding-and-routing *as
a bundle* against a bare base model. It does **not** compare a code router to a model router.
*(Confidence: directional — single-organisation 2026 preprint; the fetched abstract came back
partly paraphrased, so only the parenthesised fragments are treated as quotation.)*

### 3.3 Adjacent, and frequently mis-cited into this debate

`The Routing Plateau` [S26] studies 21 routing methods across five benchmarks and reports "a
consistent phenomenon that we call the routing plateau: many methods, including kNN, achieve
very similar accuracy and converge to a narrow performance range that remains far below the
oracle router" [S26]. **This is model-*selection* routing (which LLM answers a query), not
control-flow routing.** It is recorded here because the vocabulary collides and a future reader
will otherwise pull it in as evidence it is not. *(Confidence: definitive on what it measured;
explicitly out of scope for Q3.)*

---

## 4. The producer is an LLM: what a typed verdict does and does not buy

This is the section the dispatch is most right to insist on. A typed value emitted by a model
can be schema-valid, confidently stated, and false.

### 4.1 What constrained decoding *does* guarantee — and it is not nothing

OpenAI's first-party guarantee, verbatim:

> "ensures the model will always generate responses that adhere to your supplied JSON Schema"
> — [S11]

> "you don't need to worry about the model omitting a required key, or hallucinating an invalid
> enum value" — [S11]

**The enum clause is the load-bearing one for this design.** A closed verdict vocabulary
(`MERGE | HOLD-redispatch | HOLD-needs-assistance`) expressed as an enum under Structured
Outputs is *guaranteed* to come back inside the vocabulary. That is exactly the class of
brittleness the dispatch hypothesised — "the producer emits something the schema did not
anticipate" — and for enum-shaped verdicts it is **eliminated at the decoder**, not managed in
application code. *(Confidence: definitive on the vendor's claim. Note the scope: this is a
guarantee about the token stream, and it is a guarantee OpenAI makes about its own API; nothing
here establishes it for a `claude -p` process whose output is stdout.)*

### 4.2 What it explicitly does not guarantee

> "Structured Outputs can still contain mistakes." — [S11]

Two distinct residual classes, and OpenAI documents them separately. **Class one — no
conforming answer is produced at all:** model refusals for safety reasons, and token-limit
truncation [S11]. **Class two — a conforming answer is produced and it is fabricated**, which
is first-party support for this section's whole thesis and is the sharper of the two:

> "The model will always try to adhere to the provided schema, which can result in
> **hallucinations if the input is completely unrelated to the schema.**" — [S11]

The doc's own remedy is to push the problem back into the prompt: "If your application is using
user-generated input, make sure your prompt includes **instructions on how to handle situations
where the input cannot result in a valid response.**" [S11] — i.e. the vendor's answer to
"schema-valid but wrong" is *ask the model to abstain*, which is precisely the mechanism §4.4
argues is under-incentivised. So the guarantee is: **the shape is safe; the content is not; and
the pressure to fill a required field is itself a documented hallucination source.**

### 4.3 Does forcing the shape damage the judgement? The literature is genuinely split

- **Against.** Tam et al. (EMNLP 2024 Industry Track): "Surprisingly, we observe a significant
  decline in LLMs reasoning abilities under format restrictions. Furthermore, we find that
  stricter format constraints generally lead to greater performance degradation in reasoning
  tasks." [S27]
- **For.** The `.txt`/Outlines rebuttal reports the opposite on re-run, reporting GSM8K
  0.77→0.78, Last Letter 0.73→0.77, Shuffle Object 0.41→0.44 (unstructured→structured) and
  concluding "Consistent with all of our past findings, structured generation _outperforms_
  unstructured generation," while charging that the original "*uses different prompts for
  structured generation and unstructured generation*" [S28]. *(Vendor blog, rendered page,
  and the vendor sells a structured-generation library — **directional at best**, included
  because omitting the rebuttal would misrepresent the state of the question.)*
- **Orthogonal and measured.** JSONSchemaBench evaluates six constrained-decoding frameworks
  across 10K real-world schemas on "efficiency … coverage … and quality," and its framing
  concedes the gap this paper cares about: most uses guarantee "constraint compliance given a
  schema," while "there is poor understanding of the effectiveness of the methods in practice"
  [S29].
- **New, and specifically about verdicts.** *Structured Output Collapses Answer Diversity
  Across 44 Language Models* re-runs 31 wide-answer-space prompts across 44 models and reports
  that merely *requesting* JSON deepens convergence: "the modal answer rises from 41% to 64% of
  the pool and distinct answers fall from 52 to 36; mean answer-choice surprisal drops from 1.80
  to 1.58 bits" [S30]. Two details matter here: the effect is "specific to the answer-delivery
  formats models are trained to speak (JSON -0.22 bits, p=.0002; XML -0.19, p=.002)", and
  "Enforcing the schema at the decoder (response_format) compresses no further than the request
  (-0.03 bits): the collapse lives in the model's response to the register, not the decoder"
  [S30]. *(Single-author 2026 preprint — **directional**. Its task is open-vocabulary choice,
  not a 3-way verdict, and the transfer is untested.)*

### 4.4 The failure mode a closed vocabulary does not fix — DERIVED

Kalai et al. (OpenAI) argue hallucination is structurally incentivised: models "sometimes guess
when uncertain, producing plausible yet incorrect statements instead of admitting uncertainty,"
because "the training and evaluation procedures reward guessing over acknowledging
uncertainty" [S31].

**Derived, from [S31] + [S11] + [S6]:** an enum guarantees the verdict is *inside* the
vocabulary; nothing guarantees the verdict is *the right member of it*, and the pressure
described in [S31] runs specifically against emitting the abstention member. A three-way
`Spam | NotSpam | Uncertain` vocabulary [S6] is the correct shape, and the literature predicts
its `Uncertain` arm will be **under-used** relative to the actual uncertainty unless something
rewards it. This is the single most important unmeasured risk in the design, and it is what
T3 in §8 exists to measure. *(No source located measures abstention-arm usage rates in an
agent routing verdict — N5.)*

### 4.5 Where the wrongness shows up in whole systems

MAST is the corpus-level evidence: 1600+ annotated traces across 7 MAS frameworks, a taxonomy
of "14 unique modes, clustered into 3 categories: (i) system design issues, (ii) inter-agent
misalignment, and (iii) task verification," validated at κ=0.88 [S21]. The middle category is
the one code-routing claims to attack, and MAST establishes it as a real and dominant class —
without establishing that typed routing reduces it.

---

## 5. What this provides — enumerated, citable properties

**P1. The field has converged on the middle, not on either pole.** Model emits a
closed-vocabulary typed value; code branches on it. Documented as the canonical routing example
by LangGraph [S1], Microsoft Agent Framework [S6], Google ADK [S5], Temporal [S9] and Restate
[S10] — five sources. **CrewAI [S7] was checked and is excluded**: it has the same primitives
but its only `@router()` example branches on `random.choice([True, False])` (§2.2.4).
*(definitive)*

**P2. "No model in the loop" is false of the decision in every located instance that routes on
the outcome of real work.** Of six frameworks surveyed, five have a model producing the value
the predicate reads; the sixth (CrewAI) routes on a synthetic random value in a decorator
demonstration (N6). *(**derived** — the per-source enumeration is definitive, but the
generalisation now depends on this paper's own judgement that a `random.choice` illustration
does not count as a routing value "carrying the outcome of real work". That judgement is
defensible and it is a judgement, so P2 does **not** carry a definitive mark. A consumer who
rejects the distinction should read P2 as falsified by one of its own six sources.)*

**P3. Code-routing over typed step results across process boundaries is ~decade-old, boring
technology outside agents.** Step Functions Choice states [S8], Argo, Tekton, Airflow, GitHub
Actions (§2.4). *(definitive)*

**P4. Every system that does it caps the payload, and says so in its docs.** Tekton 4 KB
default [S13]; Argo's 1 MB etcd ceiling with SQL offload [S15]; Airflow "small amounts of data
… do not use them to pass around large values" [S14]. *(definitive)*

**P5. A code-routed branch needs a total function, and the vendors say so in two different
ways.** Step Functions **errors out** if no rule matches and no `Default` exists [S8]; Microsoft
recommends switch-case specifically because "the default case provides a safety net for
unexpected values" [S6]. *(definitive)*

**P6. The documented failure modes of code-routing are parse failure, dead-end, and
predicate/executor contract drift — not schema surprise.** All three appear as inline
handling in Microsoft's own sample, including the comment "This indicates the routing predicate
and executor contract are out of sync" [S6]. *(definitive)*

**P7. The two defensive defaults in that sample are opposite, and their composition has a
hole.** Unexpected *type* fails **open** ("let the edge pass to avoid dead ends"); unparseable
*content* fails **closed** ("Fail closed on parse errors so we do not accidentally route to the
wrong path") [S6]. If every outgoing edge fails closed on the same unparseable payload, the
message reaches no executor. *(**derived** from the two code paths in [S6]; the doc does not
state this consequence, and the sample also sets `response_format`, which makes the case rare
rather than impossible.)*

**P8. Enum-valued verdicts are protected at the decoder, on OpenAI's API.** "you don't need to
worry about the model omitting a required key, or hallucinating an invalid enum value" [S11].
*(definitive on the vendor claim; scope is that vendor's API)*

**P9. Schema validity does not transfer to semantic validity, and the vendor says so.**
"Structured Outputs can still contain mistakes." [S11] Corroborated in kind by the split
literature in §4.3 and by [S31]. *(definitive on the quote; **derived** on the consequence that
a code-router is a *faithful executor of a possibly-wrong judgement*, which is a different risk
profile from a model-router, not a smaller one)*

**P10. Model routing's measured accuracy on a curated enterprise benchmark is 90–92%, with a
false-switch rate up to 3%.** The paper's prose states "more than 90% routing classification
accuracy" and "less than 3% false agent switching rate"; its Table 7 prints the same figures as
**proportions** — 0.92/0.00, 0.92/0.00 and 0.90/**0.03** for Mortgage first layer, Mortgage
second layer and Travel routing — i.e. the worst domain misroutes 3 conversations in 100, not
3 in 10,000. "Average latency of routing classification is about 350 ms" [S24]. *(definitive on
what the paper reports; handcrafted scenarios from three enterprise domains, so read as an
upper bound on in-the-wild accuracy)*

**P11. Typed state is a *precondition* for the mechanisms this pool already wants, independent
of the routing question.** `convergence_stopping.md` P11 establishes that Class A (set fixpoint)
and Class E (capture-recapture residual risk) convergence detection require typed, comparable
finding records. *(**derived**, from that paper's P11 + this paper's §2.4 — the case for typed
results is stronger as a *measurement* argument than as a *routing* argument, because the
measurement argument has a mechanism that provably cannot run on prose, and the routing
argument has a working prose-adjacent incumbent [I1].)*

**P12. Schema evolution across independently-versioned steps is a documented hard problem in
the durable-execution substrate this repo is heading for.** Temporal: "The Workflow Definition
can change in very limited ways once there is a Workflow Execution depending on it," and
mismatched commands against event history produce "a nondeterminism error" [S12]. Tekton's
version of the same lesson is the whole of TEP-0074 [S17]. *(definitive)*

**P13. Redaction and fan-in collision can silently change a routing value without violating its
schema.** GitHub Actions redacts secret-containing outputs, and matrix jobs last-writer-wins on
name collision [S16]. *(definitive)*

---

## 6. Honest boundary analysis — the case for model-routing, and the ordinariness verdict

### 6.1 A 2026 controlled comparison finds orchestration *loses* to letting the model self-orchestrate

This is the strongest single result against the thesis and it is measured, not asserted:

> "Agent orchestration frameworks -- LangGraph, CrewAI, Google ADK, OpenAI Agents SDK, and
> others -- place an external orchestrator above the LLM, tracking state and injecting routing
> instructions at every turn. We present a controlled comparison showing that for procedural
> tasks, this architecture is dominated by a simpler alternative: putting the entire procedure
> in the system prompt and letting the model self-orchestrate." … "The in-context approach
> scores 4.53--5.00 on a 5-point scale while a LangGraph orchestrator using the same model
> scores 4.17--4.84. The orchestrated system fails on 24% of travel, 9% of Zoom, and 17% of
> insurance conversations, compared to 11.5%, 0.5%, and 5% for the in-context baseline." … "While
> external orchestration may have been necessary for earlier models, advances in frontier model
> capabilities have made it unnecessary for multi-turn conversations following a defined
> procedure." — [S18]

**Limits, stated fairly:** LLM-as-judge scoring on five criteria (and the pool already carries
evidence that LLM judges are biased — `convergence_stopping.md` §2.2.5); multi-turn
*conversational* procedures, not multi-hour multi-process autonomous runs; 2026 preprint. But
the shape of the claim — *orchestration was a workaround for weaker models* — is precisely the
claim a design betting on code-routed control flow must answer, and it is now a measured claim
rather than a rhetorical one. *(directional)*

### 6.2 A second 2026 result reports more orchestration making things worse

ChromaFlow's own summary: "A frozen full Level-1 baseline achieved 29/53 correct answers, or
54.72%. A later recovery configuration with expanded orchestration achieved 27/53 correct
answers, or 50.94%, while increasing tracebacks, timeout events, tool-failure mentions,
token-log calls, and campaign-log cost estimates. … The central result is therefore a negative
ablation: more aggressive orchestration did not improve full-set performance and increased
operational noise." [S19] *(single-author 2026 preprint, GAIA Level-1, n=53 — **directional**,
and its own author frames it as negative-result reporting)*

### 6.3 Anthropic's position on task shape

"You can't hardcode a fixed path for exploring complex topics, as the process is inherently
dynamic and path-dependent." [S23] For open-ended exploration this is a first-party statement
from the vendor whose model this repo runs, and it is not obviously wrong for the *research*
workflows in this fleet, as opposed to the *revision* ones.

### 6.4 Model routing may be accurate enough at this scale — but this argument is weaker than it first looked

**Correction, stated in place because the correction is the finding.** An earlier draft of this
section read [S24]'s false-switch rate as 0.03% and concluded that model routing was plainly
good enough. Table 7 prints **proportions**: 0.03 is **3%**, which is what the paper's own prose
says ("less than 3% false agent switching rate") [S24]. The counter-argument survives, but at
one hundred times the error rate, and it must be re-made on the honest number.

What survives: **the cost of a wrong route here is a wasted run, not a wrong production
transaction.** A single-operator fleet dispatching a handful of workflows a day, with a human
reviewing every PR, absorbs a misroute cheaply — the blast radius is one worktree, and this repo
already bounds it (worktree isolation, nothing reaches `main` except through a PR). A design
should not pay a structural price for a failure mode that costs an hour and is caught by an
already-existing gate.

What does not survive: the claim that the rate is negligible. 90–92% per-decision accuracy is
**8–10 decisions in 100 misclassified**, with up to 3 in 100 actively dispatched to the wrong
destination [S24]. *(**Derived**, and the assumption is almost certainly false: if k routing
decisions in a chain were independent at 92%, a five-step chain would route end-to-end
correctly 0.92⁵ ≈ 66% of the time. Routing errors are surely positively correlated — the hard
inputs are hard for every decision — which flattens the curve, and no source located measures
the correlation. The arithmetic is offered to show the direction the number moves under
composition, not as an estimate. Element 4's driver is explicitly a *chain* of such decisions,
which is where this matters.)*

**Net:** §6.4 is still a real counter-argument, and it is now a narrower one — it defends model
routing on *blast radius*, not on *accuracy*. Recorded this way because the honest-boundary
section getting weaker on re-verification is exactly the kind of movement a consuming agent
must be able to see.

### 6.5 Code-routing forfeits the unforeseen case by construction

Both poles have a documented answer to the unanticipated input, and they are not equivalent.
Model-routing degrades — it picks *something*, plausibly. Code-routing either errors (Step
Functions with no `Default` [S8]), silently drops (P7), or falls to a default arm someone had
to anticipate. **The engineering content of code-routing is entirely in the quality of the
default arm**, and no located source measures how often that arm is hit in practice (N5).

### 6.6 Distinguishing, or ordinary? — DERIVED, and the answer is "ordinary as stated"

Applying this pool's own altitude test (`research/README.md`: *would this finding invalidate a
phase, or inform one?*):

- **As worded in element 3 — ordinary.** "Typed results a step leaves behind that the next step
  reads in code" is Step Functions [S8], Argo, Tekton, Airflow, GitHub Actions, LangGraph,
  Microsoft Agent Framework, CrewAI and ADK. It is also, in weaker form, already shipped here
  [I1]. Presenting it as one of four novelty elements will not survive contact with a reviewer
  who has used any orchestrator.
- **As worded in element 4 — ordinary in mechanism, unusual in scope.** "if/then/else over the
  results of entire workflows" is `workflows of workflows` in Argo [S15] and nested state
  machines in Step Functions. What is unusual is doing it over *agent* runs whose results are
  model-authored judgements rather than exit statuses — and that unusualness is precisely where
  §4's risk lives, not where a benefit has been demonstrated.
- **The defensible re-cut.** The novelty, if any, is **(a)** code-routing across whole
  agent-workflow runs that are separate processes with disjoint contexts, resumed from persisted
  state — no located agent framework does this, and CI/CD does it only for non-agent steps; and
  **(b)** routing on values the model did not author. Both are narrower than the current wording
  and both are actually uncovered by the literature.
- **The stronger argument for typed results is not routing at all.** It is P11: the convergence
  and residual-risk mechanisms this pool has already committed to *cannot run* on prose. That
  argument has no working incumbent to beat, whereas the routing argument does [I1].

*(Derived from: [S1]–[S17] on ubiquity; [I1] on the shipped incumbent; `convergence_stopping.md`
P11 on the measurement dependency; `research/README.md` on the altitude test.)*

---

## 7. Citations

### 7.1 Negative findings and their search method

Per §3's requirement that a negative finding state how it was searched.

**N1. No study was located that measures code-routed control flow against model-routed control
flow, head to head.** Searched via: web queries `empirical comparison deterministic orchestration
versus LLM router agent reliability measured ablation 2026`; `"rule-based routing" versus "LLM
routing" head-to-head evaluation accuracy cost agent workflow measured`; `structured output
constrained decoding guarantees schema valid but semantically wrong benchmark 2025`; and
forward-reading from [S18], [S19], [S22], [S24], [S25], [S26]. Nearest hits: [S18] (orchestrator
vs. *no* orchestrator — the orchestrator is model-mediated in both arms), [S22] (deterministic
routing, but of *model selection*), [S24] (model-routing accuracy alone, no code-routed arm).
**The crux experiment does not appear to exist.**

**N2. No measurement located of a cost, latency or debuggability delta attributable to
code-routing versus model-routing of control flow.** Same searches, plus first-party vendor
docs [S5], [S6], [S8], [S9], [S10] — all of which assert reliability/predictability benefits
without citing a measurement. The only quantified debuggability-adjacent claim located
(rule-based routing "adds under 1 ms" vs. LLM latency) appeared in uncorroborated vendor
commentary and is **not** relied on.

**N3. No primary source located documents combinatorial branch explosion as a measured cost of
code-routed agent or workflow systems.** Searched via `workflow orchestration "combinatorial
explosion" branches maintenance cost state machine agents documented`; results were
uncorroborated blog commentary. The nearest first-party statement is Microsoft's own advice that
switch-case "scales much better as the number of routing decisions grows" [S6], which is design
guidance, not evidence of a cost. **Stated as a gap: the branch-explosion objection to
code-routing is plausible and undocumented.**

**N4. The widely-cited GitHub Actions output caps (1 MB per output, 50 MB per run) were NOT
found in the fetched primary.** The reusable content file that GitHub's workflow-syntax
reference transcludes [S16] documents secret redaction and matrix-collision behaviour but no
size figure; the `passing-information-between-jobs` page returned no size statement either. The
figure appears only in search-result summaries. **Treated as unverified and not used as
evidence.**

**N5. No source located measures (a) how often a code-routed default/residual arm is taken in
production, or (b) how often a model under-uses an explicit abstention value in a closed
verdict vocabulary.** Searched via the N1/N2 queries plus the structured-output corpus [S27]–
[S31]; [S30] measures distributional collapse on open answer spaces, not abstention-arm usage.
Both are §8 experiments, not literature questions.

**N6. No agent-framework documentation located presents a NON-model-produced value as its
canonical branching example.** Checked: LangChain/LangGraph workflows-and-agents [S1], OpenAI
Agents SDK handoffs [S3], Google ADK template + graph workflows [S4], [S5], Microsoft Agent
Framework edges [S6], CrewAI Flows [S7], Temporal's AI-agent blog [S9], Restate durable-agent
patterns [S10]. In every case the canonical routing predicate reads a field a model produced.
Non-model routing signals (activity failure, retry exhaustion, exit status) exist in these
runtimes but are documented as *error handling*, not as *routing*. **Stated as a gap in the
field's documentation, not as proof the pattern is unused.**

### 7.2 Source list

**Agent frameworks — first-party (high volatility)**

- [S1] LangChain / LangGraph, *Workflows and agents.*
  https://docs.langchain.com/oss/python/langgraph/workflows-agents.md *(docs `.md` form)*
- [S2] Anthropic, *Building Effective Agents* (engineering).
  https://www.anthropic.com/engineering/building-effective-agents *(rendered page — short
  verbatim spans only)*
- [S3] OpenAI Agents SDK, *Handoffs.*
  https://raw.githubusercontent.com/openai/openai-agents-python/main/docs/handoffs.md *(raw md)*
- [S4] Google ADK, *Template agent workflows.*
  https://raw.githubusercontent.com/google/adk-docs/main/docs/agents/workflow-agents/index.md
  *(raw md; rendered form at https://adk.dev/agents/workflow-agents/)*
- [S5] Google ADK, *Graph-based workflows.*
  https://raw.githubusercontent.com/google/adk-docs/main/docs/graphs/index.md *(raw md)*
- [S6] Microsoft Agent Framework, *Workflows — Edges.*
  https://learn.microsoft.com/en-us/agent-framework/workflows/edges *(full document text
  retrieved and read directly; sample code at
  https://github.com/microsoft/agent-framework/blob/main/python/samples/03-workflows/control-flow/edge_condition.py)*
- [S7] CrewAI, *Flows.* https://docs.crewai.com/en/concepts/flows.md *(docs `.md` form; fetch
  returned mixed quotation and summary — no long quote taken)*
- [S23] Anthropic, *How we built our multi-agent research system.*
  https://www.anthropic.com/engineering/multi-agent-research-system *(rendered page — short
  verbatim spans only)*

**Durable execution — first-party (high volatility)**

- [S8] AWS, *Choice workflow state* (Step Functions Developer Guide).
  https://docs.aws.amazon.com/step-functions/latest/dg/state-choice.html
- [S9] Temporal, *Of course you can build dynamic AI agents with Temporal.*
  https://temporal.io/blog/of-course-you-can-build-dynamic-ai-agents-with-temporal *(rendered
  vendor blog — the three short quotes used appeared identically across two independent
  fetches; the code block in one)*
- [S10] Restate, *Durable Agents.* https://docs.restate.dev/ai/patterns/durable-agents
  *(rendered docs page — directional)*
- [S12] Temporal, *Workflow Definition.* https://docs.temporal.io/workflow-definition

**Structured output — first-party (high volatility)**

- [S11] OpenAI, *Structured Outputs* (API guide).
  https://developers.openai.com/api/docs/guides/structured-outputs *(rendered docs; short
  verbatim spans only)*

**CI/CD result-passing — first-party (low volatility)**

- [S13] Tekton, *Tasks* — `Larger Results using sidecar logs`.
  https://raw.githubusercontent.com/tektoncd/pipeline/main/docs/tasks.md *(raw md; the
  Kubernetes-termination-message causal story is **unverified** — search-corroborated only)*
- [S14] Apache Airflow, *XComs.*
  https://raw.githubusercontent.com/apache/airflow/main/airflow-core/docs/core-concepts/xcoms.rst
  *(raw rst)*
- [S15] Argo Workflows, *Offloading Large Workflows.*
  https://raw.githubusercontent.com/argoproj/argo-workflows/main/docs/offloading-large-workflows.md
  *(raw md)*
- [S16] GitHub Docs, *Defining outputs for jobs* (reusable content transcluded by the
  workflow-syntax reference).
  https://raw.githubusercontent.com/github/docs/main/data/reusables/actions/jobs/section-defining-outputs-for-jobs.md
  *(raw md — see N4)*
- [S17] Tekton Community, *TEP-0074: Deprecate PipelineResources.*
  https://raw.githubusercontent.com/tektoncd/community/main/teps/0074-deprecate-pipelineresources.md
  *(raw md)*

**Empirical work (high volatility — 2024-2026)**

- [S18] Dennis, S., Diamond, M., Patil, R., Shabahang, K., & Guo, H. (2026). *In-Context
  Prompting Obsoletes Agent Orchestration for Procedural Tasks.* arXiv:2604.27891.
  https://arxiv.org/abs/2604.27891 *(2026 preprint — directional)*
- [S19] Mittal, T. (2026). *ChromaFlow: A Negative Ablation Study of Orchestration Overhead in
  Tool-Augmented Agent Evaluation.* arXiv:2605.14102. https://arxiv.org/abs/2605.14102
  *(single-author 2026 preprint — directional)*
- [S20] Yao, S., Shinn, N., Razavi, P., & Narasimhan, K. (2024). *τ-bench: A Benchmark for
  Tool-Agent-User Interaction in Real-World Domains.* arXiv:2406.12045.
  https://arxiv.org/abs/2406.12045
- [S21] Cemri, M., Pan, M. Z., Yang, S., Agrawal, L. A., Chopra, B., Tiwari, R., Keutzer, K.,
  Parameswaran, A., Klein, D., Ramchandran, K., Zaharia, M., Gonzalez, J. E., & Stoica, I.
  (2025). *Why Do Multi-Agent LLM Systems Fail?* arXiv:2503.13657.
  https://arxiv.org/abs/2503.13657
- [S22] Zhou, H., & Chan, H. Y. (2026). *ORCH: many analyses, one merge—a deterministic
  multi-agent orchestrator for discrete-choice reasoning with EMA-guided routing.* Frontiers in
  Artificial Intelligence, 2026-02-02.
  https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2026.1748735/full
  *(peer-reviewed; routing = model selection, NOT control flow)*
- [S24] Shu, R., Das, N., Yuan, M., Sunkara, M., & Zhang, Y. (2024). *Towards Effective GenAI
  Multi-Agent Collaboration: Design and Evaluation for Enterprise Applications.*
  arXiv:2412.05449. https://arxiv.org/abs/2412.05449 — routing numbers quoted from
  https://arxiv.org/html/2412.05449v1
- [S25] Dastidar, A., & the Leni Team (2026). *Where Does Agent Reliability Come From? A
  Cross-Benchmark Decomposition of Verification Loops, Specialist Models, and Scaffolding in a
  Production Enterprise Agent.* arXiv:2607.17044. https://arxiv.org/abs/2607.17044
  *(2026 preprint — directional; abstract returned partly paraphrased, only quoted fragments
  treated as quotation)*
- [S26] Lu, Y., Zhang, Q., Zhang, S., Yu, Z., Wang, Z., Chen, H., & Xing, J. (2026). *The Routing
  Plateau: Understanding and Breaking the Accuracy Limits of LLM Routers.* arXiv:2606.07587.
  https://arxiv.org/abs/2606.07587 *(model-selection routing — recorded to prevent
  mis-citation)*

**Structured-output reliability (mixed volatility)**

- [S27] Tam, Z. R., Wu, C.-K., Tsai, Y.-L., Lin, C.-Y., Lee, H., & Chen, Y.-N. (2024). *Let Me
  Speak Freely? A Study on the Impact of Format Restrictions on Performance of Large Language
  Models.* EMNLP 2024 Industry Track. arXiv:2408.02442. https://arxiv.org/abs/2408.02442
- [S28] Kurt, W. (2024). *Say What You Mean: A Response to 'Let Me Speak Freely'.* dottxt blog.
  https://blog.dottxt.ai/say-what-you-mean.html *(vendor blog with a commercial interest in the
  conclusion, rendered page — **directional at best**)*
- [S29] Geng, S., Cooper, H., Moskal, M., Jenkins, S., Berman, J., Ranchin, N., West, R.,
  Horvitz, E., & Nori, H. (2025). *JSONSchemaBench: A Rigorous Benchmark of Structured Outputs
  for Language Models.* arXiv:2501.10868. https://arxiv.org/abs/2501.10868
- [S30] Parikh, T. (2026). *Structured Output Collapses Answer Diversity Across 44 Language
  Models.* arXiv:2607.18476. https://arxiv.org/abs/2607.18476 *(single-author 2026 preprint —
  directional)*
- [S31] Kalai, A. T., Nachum, O., Vempala, S. S., & Zhang, E. (2025). *Why Language Models
  Hallucinate.* arXiv:2509.04664. https://arxiv.org/abs/2509.04664

**Engineering commentary — first-party, widely adopted (medium volatility)**

- [S32] HumanLayer, *12-Factor Agents.*
  https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/README.md *(raw md.
  Verbatim: "I've been surprised to find that most of the products out there billing themselves
  as \"AI Agents\" are not all that agentic. A lot of them are mostly deterministic code, with
  LLM steps sprinkled in at just the right points to make the experience truly magical." and
  "Agents, at least the good ones, don't follow the [\"here's your prompt, here's a bag of
  tools, loop until you hit the goal\"](…) pattern. Rather, they are comprised of mostly just
  software." Factor 8 is titled "Own your control flow". **Uncorroborated single-author
  commentary — used only as corroboration of the §2.2 pattern, never as load-bearing
  evidence.**)*

**Pool cross-references (not re-cited)**

- `raw/hierarchical_agents.md` — published hierarchical architectures route by LLM planner.
- `raw/durable_execution.md` — durable-execution primitives and their boundary conditions.
- `raw/convergence_stopping.md` — P11 (convergence detection requires typed, comparable
  outputs); P10 (judge-gated detection at +129% tokens); §2.2.5 (LLM-judge pathologies).

**Internal evidence (not a citation — recorded for traceability)**

- [I1] `scripts/workflows/revision.sh` lines 274-283 and 329-336 — the shipped
  `grep -oE '^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$'` extraction, its
  fail-closed default, and the `case` that routes on it.
- `docs/standards/architecture/system-overview.md` line 86 — "a parent still routes on a parsed
  token rather than a structured result."

*arXiv metadata and abstracts were retrieved from `arxiv.org/abs/…` pages (the Atom API returned
HTTP 429 during this run and was not usable); body-level numbers for [S24] came from the arXiv
HTML render. Where a raw markdown form of a doc existed it was fetched in preference to the
rendered site, per §4's sourcing rule; the rendered-page sources are flagged individually above.*

---

## 8. Test plan — what research cannot settle

Research established that the premise is sound-but-ordinary and that the head-to-head
measurement does not exist (N1). It cannot supply the numbers below. Ordered by decision value.

**T1. Measure the verdict-fidelity of a code-routed handoff on this fleet's own workflows.**
*Because:* P10's 90–92% is someone else's benchmark, and §6.4 argues the whole design may be
unnecessary if the incumbent's error rate is already low. *Design:* over N ≥ 30 completed
`revision.sh` runs, have a human classify the correct verdict independently of `review-pr`, and
measure how often the emitted `VERDICT:` token matches. *Reads out:* the actual defect rate of
the routing channel this design proposes to harden — and whether the defect is in the *value*
(a model problem, which typing does not fix) or in the *transport* (a regex problem, which
typing does fix). **Run this first; it is cheap and it can moot T2.**

**T2. Measure the transport failure rate separately from the judgement failure rate.**
*Because:* the entire delta between shipped [I1] and element 3 is Q2 — regex-over-stdout versus
a typed value. *Design:* instrument how often the `VERDICT_LINE` extraction falls through to its
fail-closed `needs-assistance` default, and inspect each case to determine whether the child
emitted a malformed line, no line, or a correct line the regex missed. *Reads out:* whether
typed handoff would have prevented an observed failure or a hypothetical one. *Fails if:* the
fall-through count is zero across the sample, which would mean the upgrade buys nothing
measurable at this scale.

**T3. Measure abstention-arm usage — the §4.4 risk.**
*Because:* [S31] predicts a model under-emits the "I don't know" member of a closed vocabulary,
and this fleet's `HOLD - needs-assistance` **is** that member. No literature answers it (N5).
*Design:* seed PRs that are genuinely ambiguous (a design judgement with no ground truth,
per `convergence_stopping.md` T7) and measure how often `needs-assistance` is chosen versus a
confident `MERGE`/`redispatch`. *Reads out:* whether the residual arm is real machinery or
decoration — which determines whether the "model proposes, code vetoes" middle actually has a
veto.

**T4. Determine whether `claude -p` can be held to an enum at all.**
*Because:* P8's decoder-level guarantee is an OpenAI API property [S11]. This fleet's producer
is a CLI process emitting stdout, and nothing located establishes an equivalent guarantee for
it. *Design:* over N runs, measure the rate at which a child asked for a strict verdict token
emits (a) the token exactly, (b) a near-miss, (c) nothing parseable — with and without a
structured-output mechanism if one is available. *Reads out:* whether "typed" is enforceable
here or merely requested. **This is a prerequisite for element 3 as written and is currently
unanswered.**

**T5. Cost the branch surface as it grows.**
*Because:* N3 — the combinatorial-explosion objection is plausible and completely undocumented.
*Design:* as the driver in element 4 accumulates workflows, track the number of distinct
routing predicates and how often a change to one child's verdict vocabulary forces an edit to a
parent. *Reads out:* the real maintenance coupling, which is the cost TEP-0074 [S17] retired an
entire abstraction over.

**T6. Test the element-4 altitude directly, once.**
*Because:* §6.6(a) says cross-run, cross-process code-routing over persisted state is the part
with no prior art. *Design:* build the smallest possible driver that runs two whole workflows
and branches on the first one's persisted verdict, with a deliberate crash between them.
*Reads out:* whether the durable-resume path preserves the routing value intact — the property
that distinguishes this from a CI pipeline, and the one [S12]'s versioning constraints threaten.

**Not settleable by any of the above, and worth recording as such:** whether a *correct* code
route on a *wrong* model verdict is better or worse than a model route that would have
degraded gracefully. §6.5 frames it; nothing in the located corpus measures it; and it is the
question on which the whole premise ultimately turns.
