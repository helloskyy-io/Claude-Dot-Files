# Non-Model Observables as Routing Inputs

```
Topic:          Which parts of an orchestrator's routing decision can be taken from values the
                model did NOT author — a process exit status, an `is_error` flag, an empty diff,
                a failing test, a finding-set delta, a liveness/progress probe — rather than
                from a verdict the model asserted about its own work? What prior art exists for
                routing on such observables ACROSS PROCESS BOUNDARIES, what taxonomy does it
                support, and where does the approach fail?
Feeds:          `docs/development/memory-management-framework/memory-management-framework.md` (the phase doc, not yet written) — specifically its **"Design it"** milestone (the closed-vocabulary verdict, the payload the bare token cannot carry, and the fail-safe contract) and its **"Read the result envelope; gate on `is_error`"** milestone, which is exactly one such observable.
Last validated: 2026-08-06
Revalidate:     high — 6 weeks
Confidence:     DEFINITIVE on what each cited system documents as its own branching inputs.
                The strongest provenance tier — raw source whose exact characters were returned
                by the fetch, markup intact — covers GitHub Actions expressions + contexts (raw
                `.md`, Liquid `{% raw %}` tags preserved), Tekton `when` (raw `.md`), Argo
                `variables.md` / `conditionals.md` / `exit-handlers.md` (raw `.md`), Airflow
                trigger rules + ShortCircuitOperator (raw `.rst`), Kubernetes probes / Job
                podFailurePolicy / Deployment conditions (raw `.md`, Hugo shortcodes intact),
                systemd `WatchdogSec=` (raw XML), Erlang/OTP supervisor principles (raw `.md`),
                Temporal activity-failure detection (raw `.mdx`), dbt data-tests + build (raw
                `.md`), Great Expectations checkpoint actions (raw `.md`), coverage.py
                `fail_under` (raw `.rst`), Stryker `thresholds` (raw `.md`), pytest exit codes
                (raw `.rst`), `git diff --exit-code` (raw `.adoc`), the Bash manual (plain
                text), and the GitLab CI JSON schema (spec JSON).
                REDUCED CONFIDENCE, quoted in short spans only: the Monitoring Plugins
                guidelines (rendered HTML) — §1.3's four-value table.
                DIRECTIONAL on all arXiv material: the abstracts were retrieved through the
                arXiv Atom API and through `arxiv.org/abs` pages read by a summarising layer;
                short spans are used, and no figure is carried as a quotation unless it came
                back in an unabridged API `<summary>` (this holds for [S30] only).
                DERIVED, and flagged inline: §0's three findings, §1.4's taxonomy boundaries,
                §4's P4/P7/P9/P12/P13/P14, and the whole of §5.2 and §5.5.
                UNVERIFIED: nothing is carried at this tier; two candidate claims were dropped
                rather than asserted (see N3, N5).
Critic:         not-yet-verified — 2026-08-06
```

> **Mixed volatility (§3 of the Research Standard).** The **low/medium-volatility** material —
> and it is most of the paper — is §1–§3's CI/CD, workflow-orchestration, Kubernetes, systemd
> and OTP semantics, which have been stable for years and change by deprecation notice.
> The **high-volatility** material is §2.4 (the agent-side execution-verification literature,
> all 2022–2026 preprints) and §3.4 / §5.4 (this fleet's `claude -p` result envelope, which
> moves with CLI releases — the pool's `claude_code_integration_surface.md` carries
> `Revalidate: high` for that reason). The header takes the highest tier present, per §3.
> **A refresh may skip re-verifying §1.1–§1.3, §2.1–§2.3 and §3.1–§3.3** unless a deprecation
> is announced; re-verify §2.4, §3.4, §4's P12–P14 and §5.4 every cycle. The fast-moving
> material is under a third of the paper, so §3's "prefer a split" guidance does not trigger.
> 6 weeks is the **top** of the high band, chosen because the paper's decision-bearing content
> is the slow half; the agent-side half is directional everywhere it appears, so a lapse
> degrades confidence rather than inverting a conclusion.

---

## 0. Headline: the pattern is ordinary outside agents, the operator's premise is half right, and the transferable artifact is the abstention member

Three findings, in the order they should change the phase doc.

**1. The upstream pool's open question is answered, and the answer is "mature, boring, and
canonical."** `code_routed_control_flow.md` §0 finding 3(b) records that routing on *"a value
the model did not choose — an exit code, an empty diff, a test result, a finding-set
difference"* is "a strictly stronger and genuinely different claim," and its N6 found only a toy
instance (CrewAI's `random.choice`) inside the agent-framework corpus it surveyed. Outside that
corpus the pattern is not merely present — **it is the canonical documented branching example in
every general-purpose orchestrator surveyed here.** Argo Workflows' exit-handler walkthrough
routes on `when: "{{workflow.status}} == Succeeded"` [S5]. GitHub Actions applies `success()` as
the **default** predicate on every `if:` [S1]. Airflow's entire `trigger_rule` vocabulary — 13
named rules — branches on nothing but upstream *task state* [S7]. Tekton guards a `Task` on a
`when` expression evaluated before it runs [S4]. Kubernetes routes Job outcomes on container
**exit codes** with an ordered rule list [S10]. N6 said the gap was in the field's
*documentation*, not in the field's practice, and explicitly declined to claim the pattern was
unused. That caution was correct. *(**derived** — the enumeration below is definitive per
source; the generalisation is this paper's.)*

**2. The operator's stated premise — "every orchestration system we know of assumes a
deterministic producer" — is half right, and the correction is the more useful half.** The CI
world has the well-formed-plausible-wrong-result problem in a different costume, it is measured,
and it is severe:

- **A passing test is weak evidence.** An empirical study of 22,352 PyPI projects reports that
  "A 95% confidence that a passing test case is not flaky on average would require 170 reruns"
  [S23]. Green means "this run was green," not "the property holds."
- **A test suite that passes can be incapable of failing.** SWE-Bench+ manually screened
  SWE-Agent+GPT-4's successful patches and reports "31.08% of the passed patches are suspicious
  patches due to weak test cases, i.e., the tests were not adequate to verify the correctness of
  a patch" [S30]. A computed observable over produced artifacts certified a wrong artifact in
  roughly one case in three.
- **The runtime will lie about the outcome if you ask it to, as a first-class feature.** GitHub
  Actions ships `continue-on-error`, and documents the resulting divergence in its own contexts
  reference: "When a `continue-on-error` step fails, the `outcome` is `failure`, but the final
  `conclusion` is `success`." [S2] A green build over a step that failed is not a bug there; it
  is a keyword.
- **The whole mutation-testing and coverage-threshold industry exists because "the tests pass"
  under-certifies.** coverage.py's `fail_under` exits with status 2 below a target [S17]; Stryker
  fails the build when "`mutation score < break`" [S18]. Both are gates *on the adequacy of the
  gate*.

What genuinely differs with an LLM producer is not the *existence* of well-formed wrong output —
it is that a CI step's malformedness is a **defect with a fix**, whereas an LLM's is a
**stationary rate with a distribution**. That difference changes the *fail-safe contract* (it
must be total, and it must assume the bad case recurs), not the *taxonomy*. **The phase doc
should stop justifying the design by "our producer is special" and start justifying it by
"our error rate is stationary, so the residual arm is load-bearing rather than decorative."**
*(**derived**, from [S2] + [S17] + [S18] + [S23] + [S30].)*

**3. Every mature non-model observable vocabulary carries an explicit "could not determine"
member, distinct from failure — and that is the single most transferable artifact here.**
Kubernetes probe results are `Success` / `Failure` / **`Unknown`**, and `Unknown` is documented
as *"The diagnostic failed (no action should be taken, and the kubelet will make further
checks)."* [S9] Argo's `{{workflow.status}}` is "One of: `Succeeded`, `Failed`, `Error`" [S6] —
failed and errored are separate. Monitoring Plugins' four-value convention has `Unknown` at 3,
reserved for the plugin's own inability to answer [S20]. pytest distinguishes ":Exit code 5: No
tests were collected" from ":Exit code 0: All tests were collected and passed successfully"
[S15]. GitHub Actions step results include `skipped` alongside `success` / `failure` /
`cancelled` [S2].

This corroborates — from an entirely different direction — the upstream paper's §4.4 prediction
that a model's abstention arm will be **under-used**. In every system above, the abstention
member is emitted by a *runtime that has no incentive to guess*, which is exactly why it is
reliable there and exactly why it is fragile when the emitter is a model [`code_routed_control_flow.md`
§4.4, N5]. **A closed verdict vocabulary should therefore take its abstention member from a
computed observable wherever one exists, and treat the model-asserted abstention as the
residual of last resort.** *(**derived**, from [S2] + [S6] + [S9] + [S15] + [S20] +
`code_routed_control_flow.md` §4.4.)*

---

## 1. Primer: three classes of routing input, and where the boundaries actually are

### 1.1 Class (i) — observables the RUNTIME produces about the run

Facts the execution substrate knows without inspecting the work product: did the process end,
how, when, and how many times.

| Observable | Documented instance | Source |
|---|---|---|
| Process exit status | `git diff --exit-code`; pytest `ExitCode`; coverage.py exit 2 | [S16], [S15], [S17] |
| Step/task terminal state | GitHub Actions `success` / `failure` / `cancelled` / `skipped` | [S1], [S2] |
| Container exit code as a routing key | Kubernetes Job `.spec.podFailurePolicy` `onExitCodes` | [S10] |
| Workflow-level status | Argo `{{workflow.status}}` ∈ {`Succeeded`, `Failed`, `Error`} | [S6] |
| Per-step exit code across steps | Argo `{{steps.<STEPNAME>.exitCode}}` | [S6] |
| Timeout / missed-heartbeat | Temporal Heartbeat Timeout, Start-To-Close Timeout | [S13] |
| Watchdog silence | systemd `WatchdogSec=` | [S11] |
| Retry exhaustion | Erlang/OTP `intensity` / `period`; Kubernetes `backoffLimit` | [S12], [S10] |
| Signal-derived status | Bash: `128+N`-style statuses; systemd terminating with `SIGABRT` | [S19], [S11] |

**What class (i) can decide.** Whether to retry, whether to escalate, whether the producer is
alive, whether it is *making progress*, and whether a budget is spent. Nothing else.

**What class (i) cannot decide.** Whether the work is correct, complete, or in scope. `exit 0`
means the process ended cleanly. The field already knows this and encodes the knowledge: pytest
reserves a **separate** code for "No tests were collected" [S15] precisely because "nothing ran"
and "everything passed" are indistinguishable at the level of a single success bit.

**A polarity trap worth naming.** `git diff --exit-code` documents: *"Make the program exit with
codes similar to `diff`(1). That is, it exits with 1 if there were differences and 0 means no
differences."* [S16] The empty-diff observable — the most obvious "did the agent actually do
anything" probe — has the **opposite** polarity to the success convention. A predicate written
from success-convention muscle memory reads backwards, and it reads backwards *silently*.

### 1.2 Class (ii) — observables computed over the run's ARTIFACTS by a separate deterministic process

A second process, which did not produce the work, evaluates a predicate over the work product.

| Observable | Documented instance | Source |
|---|---|---|
| Assertion over produced data | dbt data tests: *"If the data test returns zero failing rows, it passes, and your assertion has been validated."* | [S8] |
| Gate that halts the pipeline on that assertion | dbt build: *"Tests on upstream resources will block downstream resources from running, and a test failure will cause those downstream resources to skip entirely."* | [S14] |
| Validation result driving graded actions | Great Expectations Checkpoint Actions with `notify_on` ∈ {`all`, `success`, `failure`, `critical`, `warning`, `info`} | [S21] |
| Coverage threshold | coverage.py `fail_under` → exit status 2 | [S17] |
| Mutation-score threshold | Stryker `thresholds.break` → exit code 1 | [S18] |
| Test outcome over generated code | CodeT dual execution agreement; Self-Debugging on execution results | [S25], [S28] |
| Agreement across sampled outputs | Self-consistency: sample diverse paths, marginalise, take the most consistent answer | [S24] |
| Finding-set delta between two passes | `convergence_stopping.md` Classes A / E | pool |

**What class (ii) can decide.** Whether a *stated, checkable* property of the artifact holds.
It is strictly more informative than class (i) about the work, and strictly less informative
than a full judgement — and its power is bounded entirely by the quality of the predicate, which
is the SWE-Bench+ result in one sentence [S30].

**Does any surveyed system route on class (ii)?** Yes, unambiguously, and at pipeline altitude:
dbt `build` **skips** downstream nodes when an upstream test fails [S14]; Great Expectations
executes a different Action list depending on the graded validation result [S21]; Stryker and
coverage.py convert a computed threshold into a process exit status that a CI `if:` then routes
on [S17], [S18]. This is the concrete answer to the upstream N6's open question at class (ii):
**routing on a computed predicate over produced artifacts is documented, first-party, and
canonical in the data-engineering and test-tooling worlds.**

### 1.3 Class (iii) — values the MODEL asserted

A verdict token, a confidence field, a severity label, a self-report of completion. The upstream
paper `code_routed_control_flow.md` covers this class in full (its §2.2 convergent middle, §4.1
constrained decoding, §4.2 the residual risk, P8/P9). **It is cited here, not re-derived.** The
one property this paper adds: class (iii) is the only class that can answer a question with no
computable predicate — which is §5.1's subject.

The four-value monitoring convention is the cleanest statement of why the classes need separate
names. Monitoring Plugins' guidelines table gives `0` OK, `1` Warning, `2` Critical, `3` Unknown,
with Unknown described as covering *"low-level failures internal to the plugin"* — i.e. **the
checker failing is a different event from the checked thing failing** [S20]. *(Rendered HTML
page — reduced confidence, short spans only.)*

### 1.4 Where the boundaries actually sit — DERIVED, and two of them are not where they look

- **Class (i) vs class (ii) is not "runtime vs. user code."** It is *what the observable is
  about*. coverage.py's `fail_under` surfaces as an **exit status** — a class (i) shape — but
  the fact it carries is a computed property of the artifact, so it is class (ii) wearing a
  class (i) envelope [S17]. Stryker's `break` is identical [S18]. **Do not classify by
  transport.** The practical consequence for the phase doc: an exit code is not automatically
  class (i), and a class (ii) fact does not become runtime-authoritative by being encoded as one.
- **Class (ii) vs class (iii) is "who chose the value," not "is a model involved."** A
  finding-set delta computed over two model-authored finding sets is class (ii): the *records*
  are model-authored, the *delta* is not, and the delta is what the predicate reads. Likewise
  self-consistency [S24] and CodeT [S25] are class (ii) computations over class (iii) inputs.
  This third category is real and is the one most often mislabelled.
- **The boundary that is genuinely sharp** is between "the model asserted a fact about its own
  work" (iii) and everything else. Only (iii) can be wrong in the specific way a fluent
  generator is wrong — confidently, plausibly, and in the required schema
  [`code_routed_control_flow.md` §4.2, P9].

---

## 2. The specific models: what each surveyed system routes on

### 2.1 CI/CD — conditional execution on step OUTCOME, not step OUTPUT

**GitHub Actions.** The status-check functions are the routing primitive, and the default is
implicit:

> "You can use the following status check functions as expressions in `if` conditionals. A
> default status check of `success()` is applied unless you include one of these functions."
> — [S1, raw md]

> "Returns `true` when all previous steps have succeeded." (`success`) — [S1]

> "Returns `true` when any previous step of a job fails. If you have a chain of dependent jobs,
> `failure()` returns `true` if any ancestor job fails." (`failure`) — [S1]

> "Causes the step to always execute, and returns `true`, even when canceled." (`always`) — [S1]

And the doc warns against the most obvious use of `always()` in exactly the terms a fail-safe
contract cares about:

> "Avoid using `always` for any task that could suffer from a critical failure, for example:
> getting sources, otherwise the workflow may hang until it times out. If you want to run a job
> or step regardless of its success or failure, use the recommended alternative:
> `if: ${{ !cancelled() }}`" — [S1, `{% raw %}` tags elided from the span for readability;
> the fetched source carries them]

The **`outcome` / `conclusion` split is the most useful single artifact in this section** and is
reproduced verbatim in §3.3.

**GitLab CI.** The `when` keyword's own JSON schema enumerates its closed vocabulary:
`on_success`, `on_failure`, `always`, `never`, `manual`, `delayed`, with the schema description
"Describes the conditions for when to run the job. Defaults to 'on_success'." [S3, spec JSON].
Note the same implicit default as GitHub Actions: **success is the assumed predicate; every
other route is opt-in.**

**Tekton.** `when` expressions are guards evaluated before the Task runs, over `Parameters` and
prior-Task `Results`:

> "The declared `when` expressions are evaluated before the `Task` is run. If all the `when`
> expressions evaluate to `True`, the `Task` is run. If any of the `when` expressions evaluate to
> `False`, the `Task` is not run and the `Task` is listed in the `Skipped Tasks` section of the
> `PipelineRunStatus`." — [S4, raw md]

Two design properties worth carrying: the operator vocabulary is **closed to `in` / `notin`**,
and *"Using `Results` in a `when` expression in a guarded `Task` introduces a resource dependency
on the previous `Task` that produced the `Result`"* [S4] — the predicate is not free; it creates
graph structure.

**Argo Workflows.** Argo is the sharpest instance because it documents *both* halves. Its
`conditionals.md` walkthrough branches on a **script's stdout** —
`when: "{{steps.flip-coin.outputs.result}} == heads"` over a Python `random.randint` [S22] —
which is structurally the same toy the upstream N6 found in CrewAI. But its `exit-handlers.md`
walkthrough branches on the **runtime's own verdict about a completed unit of work**, and the
comment in the source says so:

```yaml
  # Exit handler templates
  # After the completion of the entrypoint template, the status of the
  # workflow is made available in the global variable {{workflow.status}}.
  # {{workflow.status}} will be one of: Succeeded, Failed, Error
  - name: exit-handler
    steps:
    - - name: notify
        template: send-email
      - name: celebrate
        template: celebrate
        when: "{{workflow.status}} == Succeeded"
      - name: cry
        template: cry
        when: "{{workflow.status}} != Succeeded"
```
— [S5, raw md]. **This is the counter-example the upstream N6 was missing**: a non-model value
carrying the outcome of a completed unit of work, presented as the canonical branching example
in first-party docs. Argo's variable reference makes the class (i) surface explicit:
`` `steps.<STEPNAME>.status` `` "Phase status of any previous step", `` `steps.<STEPNAME>.exitCode` ``
"Exit code of any previous script or container step", `` `workflow.status` `` "Workflow status.
One of: `Succeeded`, `Failed`, `Error`", and `` `workflow.failures` `` "A list of JSON objects
containing information about nodes that failed or errored during execution. Available fields:
`displayName`, `message`, `templateName`, `phase`, `podName`, and `finishedAt`." [S6, raw md].

That last one matters for the phase doc's *"payload the bare token cannot carry"* milestone:
**Argo's answer is a structured failure list alongside the scalar status, not a richer scalar.**

### 2.2 Airflow — a whole vocabulary for branching on upstream TASK STATE

Airflow is the densest prior art for the "route on what happened, not on what was said" problem,
because its `trigger_rule` argument is nothing else. Verbatim from the raw reStructuredText:

```
* ``all_success`` (default): All upstream tasks have succeeded
* ``all_failed``: All upstream tasks are in a ``failed`` or ``upstream_failed`` state
* ``all_done``: All upstream tasks are done with their execution
* ``all_done_setup_success``: Like ``all_done``, but if the task has upstream setup tasks, at least one of them must have succeeded. This is the default trigger rule for teardown tasks.
* ``all_done_min_one_success``: All non-skipped upstream tasks are done with their execution and at least one upstream task has succeeded
* ``all_skipped``: All upstream tasks are in a ``skipped`` state
* ``one_failed``: At least one upstream task has failed (does not wait for all upstream tasks to be done)
* ``one_success``: At least one upstream task has succeeded (does not wait for all upstream tasks to be done)
* ``one_done``: At least one upstream task succeeded or failed
* ``none_failed``: All upstream tasks have not ``failed`` or ``upstream_failed`` - that is, all upstream tasks have succeeded or been skipped
* ``none_failed_min_one_success``: All upstream tasks have not ``failed`` or ``upstream_failed``, and at least one upstream task has succeeded.
* ``none_skipped``: No upstream task is in a ``skipped`` state - that is, all upstream tasks are in a ``success``, ``failed``, ``upstream_failed``, or ``removed`` state
* ``always``: No dependencies at all, run this task at any time
```
— [S7, raw rst]. Enumerated and counted from that list: **13 rules**, over a task-state alphabet
of `success`, `failed`, `upstream_failed`, `skipped`, `removed`. Three design lessons:

1. **`upstream_failed` is a distinct state from `failed`.** A task that never ran because its
   parent broke is a different event from a task that ran and broke. This fleet currently
   collapses both into "the child script exited non-zero."
2. **Several rules do not wait** (`one_failed`, `one_success`) — the predicate fires on partial
   information. That is a deliberate latency/completeness trade, made explicit in the vocabulary.
3. **`always` exists and is named**, so "run regardless" is a stated choice rather than an
   omitted guard.

`ShortCircuitOperator` is the class-(ii)-adjacent complement — a predicate that *skips* rather
than *fails*, with documented interaction against the trigger rules:

> "If ``ignore_downstream_trigger_rules`` is set to True, the default configuration, all
> downstream tasks are skipped without considering the ``trigger_rule`` defined for tasks.  If
> this parameter is set to False, the direct downstream tasks are skipped but the specified
> ``trigger_rule`` for other subsequent downstream tasks are respected." — [S26, raw rst]

**That is a documented precedence rule between two non-model routing mechanisms** — see §3.3.

### 2.3 Liveness, progress and supervision — the observables that answer "is it stuck?"

**Kubernetes separates three questions the word "healthy" collapses.** Verbatim from the raw
markdown:

```
Startup probes verify whether the application within a container is started.
...
Liveness probes determine when to restart a container.
For example, liveness probes could catch a deadlock, where an application is
running, but unable to make progress. Restarting a container in such a state
can help to make the application more available despite bugs.

Readiness probes determine when a container is ready to accept traffic.
```
— [S9, raw md]. And the outcome alphabet, verbatim:

```
`Success`
: The container passed the diagnostic.

`Failure`
: The container failed the diagnostic. For liveness and startup probes, the
  kubelet kills the container, and the container is subjected to its
  [restart policy](/docs/concepts/workloads/pods/pod-lifecycle/#restart-policy).
  For readiness probes, the kubelet marks the container as not ready, and the
  Pod stops receiving traffic from matching Services.

`Unknown`
: The diagnostic failed (no action should be taken, and the kubelet will make
  further checks).
```
— [S9, raw md]. Note that **the same observable value drives different actions depending on which
question was asked** — `Failure` on a liveness probe kills, `Failure` on a readiness probe
merely de-routes traffic. The routing decision is (observable, question) → action, not
observable → action.

**Kubernetes also separates "progressing" from "available" at the controller level.** A
Deployment is marked *progressing* when it "creates a new ReplicaSet", is "scaling up its newest
ReplicaSet", is "scaling down its older ReplicaSet(s)", or "New Pods become ready or available"
[S25k, raw md], recorded as a `.status.conditions` entry with `type: Progressing`. Stall is
detected by a **deadline**, not by a failure: `.spec.progressDeadlineSeconds` "denotes the number
of seconds the Deployment controller waits before indicating (in the Deployment status) that the
Deployment progress has stalled" [S25k]. **A hang produces no error; it produces a timer
expiry.** The documented causes of a stuck Deployment are worth reading directly for a fleet
whose children can also stall: "Insufficient quota", "Readiness probe failures", "Image pull
errors", "Insufficient permissions", "Limit ranges", "Application runtime misconfiguration"
[S25k].

**systemd's watchdog is the same mechanism as a wall-clock progress probe across a process
boundary.** Verbatim from the raw XML man page source:

> "The service must call sd_notify 3 regularly with `WATCHDOG=1` (i.e. the "keep-alive ping").
> If the time between two such calls is larger than the configured time, then the service is
> placed in a failed state and it will be terminated with `SIGABRT` (or the signal specified by
> `WatchdogSignal=`)." — [S11, raw XML, element markup elided]

**Temporal states the limit of the whole approach explicitly**, and it is the sentence a
distributed-orchestration design should be able to quote from memory:

> "The Temporal Server doesn't detect failures when a Worker loses communication with the Server
> or crashes.
> Therefore, the Temporal Server relies on the Start-To-Close Timeout to force Activity
> retries." — [S13, raw mdx]

And on what heartbeating is actually *for*:

> "Heartbeating is best thought about not in terms of time, but in terms of "How do you know you
> are making progress?"" — [S13]

> "Your underlying task must be able to report definite progress." — [S13]

That precondition is the one this fleet's children currently fail: a `claude -p` child emits a
stream of events, but nothing in that stream is a *definite progress* signal distinguishable
from productive churn.

**Erlang/OTP supplies the retry-exhaustion half.** Restart strategies are `one_for_one` ("If a
child process terminates, only that process is restarted"), `one_for_all`, and `rest_for_one`
[S12, raw md]. The bound:

> "If more than `MaxR` number of restarts occur in the last `MaxT` seconds, the supervisor
> terminates all the child processes and then itself." — [S12]

> "The intention of the restart mechanism is to prevent a situation where a process repeatedly
> dies for the same reason, only to be restarted again." — [S12]

The tuning guidance contains a warning that transfers directly to a redispatch loop: "if the top
level allows 10 restarts, and the next level also allows 10, a crashing child below that level
will be restarted 100 times, which is probably excessive" [S12] — **nested retry budgets
multiply.** This fleet nests: `run_claude` retries a rate-limit probe up to 3 times, Claude Code
itself retries transients up to 10 times [`claude_code_integration_surface.md` §5], and
`build.sh` adds one loop-back.

**Kubernetes Job `podFailurePolicy` is the fullest documented example of routing on an exit
code**, with a graded action vocabulary — verbatim from the raw markdown:

```
  - `FailJob`: use to indicate that the Pod's job should be marked as Failed and
     all running Pods should be terminated.
  - `Ignore`: use to indicate that the counter towards the `.spec.backoffLimit`
     should not be incremented and a replacement Pod should be created.
  - `Count`: use to indicate that the Pod should be handled in the default way.
     The counter towards the `.spec.backoffLimit` should be incremented.
  - `FailIndex`: use this action along with [backoff limit per index](#backoff-limit-per-index)
     to avoid unnecessary retries within the index of a failed pod.
```
— [S10, raw md]. And the evaluation semantics, which are the fail-safe contract in three lines:

> "the Pod failure policy rules you specify under `spec.podFailurePolicy.rules` are evaluated in
> order. Once a rule matches a Pod failure, the remaining rules are ignored. When no rule matches
> the Pod failure, the default handling applies." — [S10]

**Ordered rules, first match wins, total by construction via a documented default.** That is
directly reusable as the phase doc's fail-safe contract shape.

### 2.4 The agent-side third category: observables COMPUTED OVER model output

This is the class (ii)-over-(iii) category §1.4 separates out, and the literature on it is the
strongest evidence in the whole paper *for* preferring computed observables to asserted ones.

- **Intrinsic self-assessment does not work; external feedback does.** *Large Language Models
  Cannot Self-Correct Reasoning Yet*: "our research indicates that LLMs struggle to self-correct
  their responses without external feedback, and at times, their performance even degrades after
  self-correction" [S27]. Its definition of the thing that fails is exactly a class (iii) routing
  input — "intrinsic self-correction, whereby an LLM attempts to correct its initial responses
  based solely on its inherent capabilities, without the crutch of external feedback" [S27].
  *(directional — 2026-era preprint/conference paper retrieved via a summarising fetch of the
  arXiv abs page.)*
- **Execution results are the external feedback that does work.** Self-Debugging reports the
  model "is able to identify its mistakes by investigating the execution results," and improves
  baseline accuracy "by up to 12%" on TransCoder and MBPP "where unit tests are available"
  [S28]. Reflexion's whole premise is reinforcement from "task feedback signals," reporting "a
  91% pass@1 accuracy on the HumanEval coding benchmark" [S29]. CodeT selects among samples by
  actually running them: "CodeT then executes the code samples using the generated test cases,
  and performs a dual execution agreement" [S25]. *(all directional.)*
- **Agreement across samples is a computed observable that needs no external oracle.**
  Self-consistency "first samples a diverse set of reasoning paths instead of only taking the
  greedy one, and then selects the most consistent answer by marginalizing out the sampled
  reasoning paths," reporting GSM8K +17.9%, SVAMP +11.0%, AQuA +12.2%, StrategyQA +6.4%,
  ARC-challenge +3.9% [S24]. *(directional. Note the task shape: single-answer reasoning
  benchmarks, not multi-hour multi-file agent runs; the transfer is untested.)*
- **And the ceiling on all of it.** SWE-bench established test-passing as the field's standard
  execution-based verdict for agentic repair [S31]; SWE-Bench+ then measured how much that
  verdict certifies, and the answer was "less than it looks" — see §0 finding 2 [S30].

**A finding-set delta between two passes is a class (ii) observable and belongs in the
taxonomy** — but *when to stop on it* is settled elsewhere and is not re-researched here. See
`convergence_stopping.md` P11 (convergence detection requires typed comparable finding records)
and its §5.1–5.7 (the case against a naive "stop when a pass finds nothing" rule).

---

## 3. Comparative landscape

### 3.1 The alternatives, fairly stated

| Approach | What it buys | What it costs | Best documented instance |
|---|---|---|---|
| **Route on class (i) only** | Cheapest, most reliable, needs no cooperation from the producer | Answers only "did it run" — silent on correctness; blind to a no-op | Airflow trigger rules [S7]; Argo exit handlers [S5] |
| **Route on class (ii)** | Answers a real property of the artifact; independent of the producer's opinion | Only as good as the predicate; expensive to author; SWE-Bench+ bounds the trust [S30] | dbt build gating [S14]; Stryker/coverage thresholds [S17], [S18] |
| **Route on class (iii)** | The only class that can answer an open-ended question | Confidently wrong in the required schema; abstention arm under-used | `code_routed_control_flow.md` §2.2, §4.2 |
| **Route on class (iii) validated by class (ii)** | Catches the specific failure of a fluent producer | Doubles the machinery; measurement can outspend the saving | Self-consistency [S24]; CodeT [S25]; `convergence_stopping.md` P10 (+129% tokens) |
| **No routing — let the model self-orchestrate** | Zero machinery; degrades gracefully on the unforeseen case | Measured *worse* in two 2026 comparisons | `code_routed_control_flow.md` §6.1, §6.2 |

### 3.2 What each system does when the observable is missing or the predicate does not match

Every surveyed system has an answer, and **none of them is "fall through."**

- Kubernetes Job: ordered rules, first match wins, *"When no rule matches the Pod failure, the
  default handling applies."* [S10]
- Tekton: a `False` guard skips the Task and **records it** in the `Skipped Tasks` section of the
  PipelineRunStatus [S4] — the non-execution is itself an observable.
- GitHub Actions / GitLab CI: an implicit `success()` / `on_success` default on every conditional
  [S1], [S3].
- Airflow: `all_success` is the default trigger rule [S7]; the ShortCircuitOperator's skip
  propagation is configurable and documented [S26].
- Kubernetes probes: `Unknown` is a named outcome with a named action ("no action should be
  taken, and the kubelet will make further checks") [S9].

This corroborates the upstream P5 ("a code-routed branch needs a total function") from five
additional first-party sources — and adds the sharper form: **the total function's residual arm
should be a named state that gets recorded, not a silent default.**

### 3.3 When an asserted result and a computed one disagree — what precedence is documented

This is deliverable (c), and the honest answer has three parts.

**(1) No surveyed system defines precedence between a *producer's assertion* and a *computed
observable*, because no surveyed system has an asserting producer.** In CI/CD, Airflow, Argo,
Tekton and Kubernetes, the producer emits an exit status and the runtime owns the verdict; there
is no second, self-reported opinion to reconcile. **Stated as a gap — N1.**

**(2) What IS documented is precedence between an observed outcome and a DECLARED POLICY, and
the pattern is: keep both, name them differently, and let the policy govern routing.** GitHub
Actions is the exemplar, verbatim from the raw contexts reference:

```
| `steps.<step_id>.conclusion` | `string` | The result of a completed step after [`continue-on-error`](/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstepscontinue-on-error) is applied. Possible values are `success`, `failure`, `cancelled`, or `skipped`. When a `continue-on-error` step fails, the `outcome` is `failure`, but the final `conclusion` is `success`. |
| `steps.<step_id>.outcome` | `string` | The result of a completed step before [`continue-on-error`](/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstepscontinue-on-error) is applied. Possible values are `success`, `failure`, `cancelled`, or `skipped`. When a `continue-on-error` step fails, the `outcome` is `failure`, but the final `conclusion` is `success`. |
```
— [S2, raw md]. **Two fields, two names, both retained, both queryable.** The raw observation is
never overwritten; the policy-adjusted value is what downstream `if:` conditions see by default,
and a workflow that wants the truth asks for `outcome` explicitly. *(**derived** on the
"exemplar" framing; definitive on the field semantics.)*

**(3) Where two computed signals disagree, the documented answers are ordered rules or an
explicit precedence statement.** Kubernetes: ordered rules, first match wins, default otherwise
[S10]. Airflow: `ignore_downstream_trigger_rules` decides whether a short-circuit skip overrides
downstream trigger rules [S26]. Great Expectations states a precedence rule outright for its
graded severities: *"If a Validation Result includes a mix of warning and info failures, only
Actions configured to notify on `warning`, `failure`, or `all` will be triggered. Any Actions
configured to run on `info` will not be triggered."* [S21, raw md] — highest severity wins,
stated in the docs rather than left to the reader.

**The transferable design, derived:** when this fleet's `is_error` and its `VERDICT:` token
disagree, do not pick one — **record both under distinct names, route on a documented composition
rule, and make the composition rule's residual arm a named state.** The GitHub Actions
`outcome`/`conclusion` split is the shape; the Kubernetes ordered-rules-with-default is the
evaluation semantics. *(**derived**, from [S2] + [S10] + [S21] + [S26].)*

### 3.4 What this fleet already routes on — corrected against the source

The dispatch's framing needed two corrections, and stating them is more useful than repeating it.

**Correction 1 — the parent DOES gate on the child's process exit status.** `build.sh` sets
`set -euo pipefail` (line 60) and invokes children under `if ! "$PR_REVIEW" … 2>&1 | tee "$log"`
(line 266) [I1]. With `pipefail`, per the Bash manual — *"If 'pipefail' is enabled, the
pipeline's return status is the value of the last (rightmost) command to exit with a non-zero
status, or zero if all commands exit successfully."* [S19, plain text] — the child's non-zero
status is **not** masked by `tee`. So class (i) routing at the coarsest grain is already
implemented and is correct.

**Correction 2 — `run-claude.sh` already reads two envelope observables, not zero.** It greps the
result-envelope `subtype` field (`grep -q '"subtype":"error_max_turns"'`, line 167) and it
`jq`-reads `.result` against `COMPLETION_PATTERN` (lines 201–204) [I2]. The first is a class (i)
runtime observable read from the envelope; the second is a class (ii) predicate over the run's
own output text.

**What is genuinely absent, and the dispatch is right about this:** **`.is_error` is never
read.** Neither is `permission_denials[]`, `num_turns` against the cap, `duration_ms`, or
`system/api_retry`'s `error` enum — all of which the pool's
`claude_code_integration_surface.md` §7 enumerates as available in the result envelope and
`system/init` (that paper is the citation for the field list; it is not re-established here).
Its §5 also records that **there is no first-party exit-code table** for `claude`, and that
"Codes for auth failure, rate limit exhaustion, `--max-turns` exceeded, and `--max-budget-usd`
exceeded are **not documented**." That is directly load-bearing: **class (i) routing in this
fleet is currently resting on an undocumented mapping.** A child that ends with `is_error: true`
and exit 0 would pass every gate the parent has, and nothing first-party says whether that
combination can occur. **Stated as a gap — N2**, and it is T1 in §7.

---

## 4. What this provides — enumerated, citable properties

**P1. Routing on non-model observables across process boundaries is mature, first-party and
canonical outside agent frameworks.** Argo exit handlers on `{{workflow.status}}` [S5]; GitHub
Actions' implicit `success()` default [S1]; GitLab's `when` enum [S3]; Airflow's 13 trigger rules
[S7]; Tekton `when` guards [S4]; Kubernetes `podFailurePolicy` on exit codes [S10].
*(definitive per source.)*

**P2. The upstream N6 gap is a documentation gap in the AGENT corpus specifically, and this paper
closes it from outside.** Argo's `exit-handlers.md` is a first-party doc presenting a non-model
value *carrying the outcome of a completed unit of work* as its canonical branching example
[S5]. *(definitive on the artifact; the "closes N6" framing is **derived**.)*

**P3. Class (ii) routing — a computed predicate over produced artifacts halting a pipeline — is
documented and canonical in data engineering and test tooling.** dbt build: "a test failure will
cause those downstream resources to skip entirely" [S14]; Great Expectations graded Actions
[S21]; coverage.py `fail_under` → exit 2 [S17]; Stryker `break` → exit 1 [S18].
*(definitive.)*

**P4. Classify observables by WHAT THEY ARE ABOUT, not by their transport.** A computed
threshold surfaced as an exit status is class (ii) in a class (i) envelope [S17], [S18].
*(**derived**, from the two cited mechanisms.)*

**P5. Every mature observable vocabulary contains an explicit "could not determine" member,
distinct from failure.** Kubernetes `Unknown` [S9]; Argo `Error` vs `Failed` [S6]; Monitoring
Plugins `Unknown`=3 [S20]; pytest exit 5 [S15]; GitHub Actions `skipped` [S2].
*(definitive per source; the generalisation is **derived**.)*

**P6. "The process exited cleanly" and "the work happened" are different facts, and the field
encodes the difference.** pytest reserves ":Exit code 5: No tests were collected" separately from
":Exit code 0: All tests were collected and passed successfully" [S15]. *(definitive.)*

**P7. The empty-diff observable has INVERTED polarity relative to the success convention.**
`git diff --exit-code` "exits with 1 if there were differences and 0 means no differences" [S16].
A predicate written from success-convention habit is silently backwards. *(definitive on the
quote; the trap is **derived**.)*

**P8. Hang detection is a timer, not an error — and it is a separate mechanism from failure
detection in every system that has it.** Kubernetes `.spec.progressDeadlineSeconds` [S25k];
systemd `WatchdogSec=` with `SIGABRT` [S11]; Temporal Heartbeat Timeout and Start-To-Close
Timeout [S13]. *(definitive.)*

**P9. A liveness/progress probe requires the producer to emit a definite-progress signal, and
Temporal states this as a precondition.** "Your underlying task must be able to report definite
progress." [S13] This fleet's children do not currently emit one. *(definitive on the quote;
the fleet-side observation is **derived** from [I1], [I2].)*

**P10. Nested retry budgets multiply, and OTP documents the arithmetic.** "if the top level
allows 10 restarts, and the next level also allows 10, a crashing child below that level will be
restarted 100 times" [S12]. *(definitive.)*

**P11. The documented fail-safe shape is: ordered rules, first match wins, an explicit default,
and the residual recorded as a named state.** Kubernetes `podFailurePolicy` [S10]; Tekton's
`Skipped Tasks` section [S4]; Kubernetes `Unknown` [S9]. *(definitive per source; the composite
shape is **derived**.)*

**P12. Where an observed result and a declared policy disagree, the documented pattern is to
keep BOTH under distinct names and route on the policy-adjusted one by default.** GitHub Actions
`outcome` vs `conclusion` [S2]. *(definitive on the field semantics; the transfer to a
verdict-vs-`is_error` disagreement is **derived**.)*

**P13. The "our producer is non-deterministic, theirs isn't" premise does not survive contact
with the CI literature — but a narrower version does.** Flaky-test measurement [S23], weak test
cases [S30], and `continue-on-error` [S2] all show well-formed-wrong outcomes in deterministic
pipelines. The surviving difference is *stationary rate vs. fixable defect*.
*(**derived**, from [S2] + [S23] + [S30].)*

**P14. Computed observables over model output beat model self-assessment, and the evidence is
one-directional.** Self-correction without external feedback "at times… degrades" performance
[S27], while execution-grounded methods report gains [S24], [S25], [S28], [S29]. *(**derived**
across five directional sources; no single source states the comparison this way, and every
input is a preprint or conference paper read through a summarising fetch.)*

---

## 5. Honest boundary analysis

### 5.1 The routing decisions in THIS fleet that CANNOT be moved off the model's assertion

This is the most useful thing the phase doc can be handed, so it is stated as a list rather than
an argument. For each, the reason no computable predicate exists.

| Decision | Can it move to (i) or (ii)? | Why not |
|---|---|---|
| **"Is this PR mergeable?"** | **No.** | Mergeability is a judgement about scope, correctness and taste. Class (i) says the child ran; class (ii) says the tests pass and CI is green — and SWE-Bench+ measures how little "the tests pass" certifies [S30]. Nothing computable distinguishes "correct" from "compiles and doesn't break anything visible." |
| **"Is this finding blocking or a nit?"** | **No.** | Severity is the assertion. Great Expectations *has* graded severities [S21] — but they are declared by the author of the Expectation, i.e. asserted, just by a human instead of a model. |
| **"Does this need a HUMAN ruling?"** (`HOLD - needs-assistance`) | **No, by construction.** | The criterion is "no ground truth exists that an automated pass could reach." A predicate that could detect it would be the ground truth. This is the abstention arm, and §0 finding 3 says it is exactly the member a model under-emits. |
| **"Was the review itself adequate?"** | **No.** | Coverage of the *review*, not of the code. The nearest analogue in the corpus is mutation testing — a gate on the gate [S18] — and no such instrument exists for a prose review. |
| **"Did the child process finish, and how?"** | **Yes — class (i).** | Exit status, `is_error`, `subtype`, timeout, signal. Partially implemented [I1], [I2]; `.is_error` is the named gap (N2). |
| **"Did it produce work at all?"** | **Yes — class (ii).** | Empty diff [S16], PR URL present, git SHA changed. `build.sh` already checks the PR URL (line 198) [I1]. |
| **"Did it break the build?"** | **Yes — class (i)/(ii).** | CI conclusion; `wait_for_ci` is already an activity [I1]. |
| **"Did it stall?"** | **Yes in principle — class (i), not implemented.** | `error_max_turns` is caught [I2]; a wall-clock or no-progress probe is not, and P9's precondition (a definite-progress signal) is unmet. |
| **"Has the finding set stopped changing?"** | **Yes — class (ii).** | Requires typed comparable finding records; see `convergence_stopping.md` P11 and its §5.1–5.7 for when NOT to stop on it. |

**The boundary in one sentence, derived:** non-model observables can establish that a run
*happened, terminated, produced an artifact, and did not break anything checkable* — they cannot
establish that the artifact is *right*, and every routing decision that turns on rightness stays
class (iii).

### 5.2 The case against moving routing onto observables at all — DERIVED

- **Every observable answers a narrower question, and the narrowing is silent.** `exit 0` means
  the process ended cleanly. An agent that does nothing exits 0. `run-claude.sh`'s own comment
  documents having been bitten by exactly this: *"A headless (`claude -p`) run ends on ANY
  text-only turn, including a premature "waiting on dispatched agents…" message: the harness
  reports exit 0 with nothing produced."* [I2] — the COMPLETION_PATTERN check exists **because**
  class (i) was insufficient and a class (ii) predicate had to be added on top.
- **Adding an observable adds a failure mode.** GitHub Actions warns that `always()` on a task
  that can fail critically means "the workflow may hang until it times out" [S1]. Kubernetes
  warns that "The readiness and liveness probes do not depend on each other to succeed" [S32] —
  two probes, two independent verdicts, and the interaction is the operator's problem.
- **A predicate creates graph coupling.** Tekton: using a Result in a `when` expression
  "introduces a resource dependency on the previous `Task` that produced the `Result`" [S4]. The
  upstream paper's TEP-0074 finding is the extreme version of this cost
  [`code_routed_control_flow.md` §2.4.2].
- **The measurement can outspend the saving.** `convergence_stopping.md` P10 measured judge-gated
  convergence detection at **+129% tokens**.
- **And the strongest counter is upstream and measured:** two 2026 comparisons found
  orchestration a net *loss* against letting the model self-orchestrate
  [`code_routed_control_flow.md` §6.1, §6.2]. Moving routing onto observables makes the
  orchestrator *more* rigid, not less, so it moves in the direction those results disfavour.

### 5.3 Where the prior art is a POOR analogue, said plainly

- **CI/CD steps are idempotent and re-runnable; a `claude -p` child is neither.** Every
  retry-and-restart taxonomy in §2.3 assumes restarting is cheap and semantically clean. OTP's
  restart strategies assume a supervised process can be restarted into a known state [S12]. A
  redispatched agent re-enters a worktree it has already modified.
- **Kubernetes probes assume a long-lived service; a workflow child is a batch job with a
  terminal state.** The liveness/readiness/startup distinction [S9] maps only loosely: "ready to
  accept traffic" has no analogue here, and the useful half is only the liveness/progress axis.
- **Airflow trigger rules operate over a static DAG known before the run.** This fleet's routing
  is dynamic — a loop-back is decided after a child returns. The *vocabulary* transfers; the
  *evaluation model* does not.
- **The agent-side execution-verification literature is benchmark-shaped.** Self-consistency
  [S24], CodeT [S25] and Self-Debugging [S28] all evaluate on short single-answer or
  single-function tasks with an available oracle. Nothing located measures them on multi-hour
  multi-file repository work under a real review gate. SWE-bench is the nearest [S31], and
  SWE-Bench+ is the measurement of how far even that oracle is trusted [S30].
- **Great Expectations' and dbt's producers are deterministic SQL.** Their gating pattern
  transfers; their assumption that a failing test means "the data is wrong" (rather than "the
  test is wrong") does not, per §0 finding 2.

### 5.4 Where this paper's own evidence is weakest

- **The agent-side section (§2.4) is directional throughout.** Every source is a preprint or
  conference paper whose abstract was read through a fetch layer that summarises. Only [S30]'s
  figures came back as an unabridged API `<summary>`; the others are short spans.
- **[S20] (Monitoring Plugins) is a rendered HTML page** and is used only for the four-value
  table, in short spans, corroborating a point already made by three raw sources.
- **No source located measures the RATE at which any of these observables is wrong in an agent
  context.** The flaky-test figure [S23] and the weak-test figure [S30] are the nearest
  quantifications, and neither is about an orchestrator's routing channel. **N3.**
- **The GitLab evidence is a schema, not prose.** [S3] establishes the closed `when` vocabulary
  and its default; it does not establish the runtime semantics of each value. The prose
  documentation was sought and not obtained in a verbatim-quotable form — **N4**.

### 5.5 The counter-case to §0 finding 3 — DERIVED

The claim that the abstention member is "cheap when the emitter is a runtime" has a limit: it is
cheap because the runtime's abstention is about *the checker*, not about *the work*. Kubernetes'
`Unknown` means the probe could not be evaluated [S9]; Monitoring Plugins' `Unknown` covers
"low-level failures internal to the plugin" [S20]. **Neither is "the work is ambiguous."** So
the transferable lesson is narrower than it first looks: **a computed observable can supply a
reliable "I could not check," but it cannot supply "this needs a human to decide."** The second
of those is what `HOLD - needs-assistance` means in this fleet, and it stays class (iii). This
weakens §0 finding 3's recommendation from "take the abstention member from an observable" to
"**split the abstention member in two** — a computed *could-not-check* arm and an asserted
*needs-a-ruling* arm — because they have different reliability and different remedies."
*(**derived**, from [S9] + [S20] + `code_routed_control_flow.md` §4.4. Recorded here rather than
folded into §0 because a boundary section that only strengthens the thesis is not one.)*

---

## 6. Citations

### 6.1 Negative findings and their search method

**N1. No surveyed system defines precedence between a producer's SELF-ASSERTED result and a
computed observable about the same unit of work.** Checked by reading, for a precedence
statement, the first-party routing/branching documentation of: GitHub Actions expressions [S1]
and contexts [S2], GitLab CI's schema [S3], Tekton `when` [S4], Argo conditionals [S22] / exit
handlers [S5] / variables [S6], Airflow trigger rules [S7] and ShortCircuitOperator [S26],
Kubernetes probes [S9] / Job podFailurePolicy [S10] / Deployment conditions [S25k], Temporal
activity-failure detection [S13], systemd `WatchdogSec=` [S11], OTP supervisor principles [S12],
dbt data tests [S8] / build [S14], and Great Expectations checkpoint actions [S21]. **What was
found instead** is precedence between an observed outcome and a *declared policy* [S2], between
two computed signals [S21], [S26], and ordered-rule evaluation over observables [S10] — all
recorded in §3.3. **The reason is structural, not an oversight: none of these systems has a
producer that files an opinion about its own output.** This is the genuinely uncovered part of
the phase doc's question.

**N2. It is not documented whether a `claude -p` process can exit 0 while its result envelope
carries `is_error: true`.** Search method: the pool's `claude_code_integration_surface.md` §5
(header `Last validated: 2026-07-25`, `Critic: PASS`) is the enumeration of the documented
failure surface, and it records that there is "**no first-party exit-code table**" and that codes
for auth failure, rate-limit exhaustion, `--max-turns` exceeded and `--max-budget-usd` exceeded
are "not documented." No first-party source establishing the exit-code↔`is_error` relationship
was located, and this paper did not re-run that survey — it cites it. **This is an experiment
(T1), not a literature question.**

**N3. No source located measures the error rate of any non-model observable used as an
orchestrator's routing channel.** Searched via the CI/CD, workflow-orchestration and
agent-verification corpora above, plus targeted retrieval of the flaky-test and benchmark-quality
literature ([S23], [S30]). The nearest quantifications are about *tests* (170 reruns for 95%
confidence [S23]; 31.08% suspicious passed patches [S30]), not about a routing decision. A
candidate claim of the form "observables are more reliable than verdicts by X" was available in
uncorroborated commentary and is **not asserted here**.

**N4. GitLab CI's prose documentation of `when` values was not obtained in a verbatim-quotable
form.** Method: `gitlab.com/gitlab-org/gitlab/-/raw/master/doc/ci/yaml/_index.md` returned
truncated content with the `when` section absent; `doc/ci/jobs/job_control.md` and
`doc/ci/jobs/job_rules.md` were fetched and neither contains the enumerated definition. `master`
was confirmed as the correct ref by the successful `ci.json` fetch on the same path prefix.
**What IS carried** is the CI JSON schema [S3], which is a stronger source for the closed
vocabulary and its default and a weaker one for per-value semantics.

**N5. No source located states an exit-status convention that a wrapper around a
non-deterministic producer should adopt.** Searched via the exit-code conventions in [S15],
[S16], [S17], [S18], [S20] and the Bash manual [S19]. Every located convention assumes a
deterministic producer. The four-value monitoring convention [S20] is the closest fit and was
designed for *checkers*, not *producers*. **Stated as a gap; the phase doc is designing into
uncovered territory here, which is a reason for care, not a reason to stop.**

**N6. No located source measures how often a class (ii) predicate over agent output is itself
wrong in a production orchestration setting.** Searched via the agent-verification corpus
([S24], [S25], [S27], [S28], [S29], [S31]) and [S30]. [S30] measures oracle inadequacy on a
*benchmark*, which is the nearest available proxy and is used as such.

### 6.2 Source list

**CI/CD and workflow orchestration — first-party (low/medium volatility)**

- [S1] GitHub Docs, *Evaluate expressions in workflows and actions* — "Status check functions."
  https://raw.githubusercontent.com/github/docs/main/content/actions/reference/workflows-and-actions/expressions.md
  *(raw md; Liquid `{% raw %}` markup returned intact, which is the verbatim warrant)*
- [S2] GitHub Docs, *Contexts reference* — `steps.<step_id>.outcome` / `.conclusion`.
  https://raw.githubusercontent.com/github/docs/main/content/actions/reference/workflows-and-actions/contexts.md
  *(raw md; the two table rows in §3.3 were re-fetched with a verbatim-only prompt and returned
  character-identical to the first fetch)*
- [S3] GitLab, *CI/CD JSON schema* — the `when` keyword's `enum` and description.
  https://gitlab.com/gitlab-org/gitlab/-/raw/master/app/assets/javascripts/editor/schema/ci.json
  *(spec JSON. Enumerated values, counted from the enumeration: `on_success`, `on_failure`,
  `always`, `never`, `manual`, `delayed` — six.)*
- [S4] Tekton, *Pipelines* — "Guard `Task` execution using `when` expressions."
  https://raw.githubusercontent.com/tektoncd/pipeline/main/docs/pipelines.md *(raw md)*
- [S5] Argo Workflows, *Exit handlers.*
  https://raw.githubusercontent.com/argoproj/argo-workflows/main/docs/walk-through/exit-handlers.md
  *(raw md. A first fetch of this file returned a prose summary and was discarded; the YAML in
  §2.1 comes from a second fetch that returned the file's raw markdown.)*
- [S6] Argo Workflows, *Workflow variables.*
  https://raw.githubusercontent.com/argoproj/argo-workflows/main/docs/variables.md *(raw md)*
- [S7] Apache Airflow, *DAGs* — Trigger Rules.
  https://raw.githubusercontent.com/apache/airflow/main/airflow-core/docs/core-concepts/dags.rst
  *(raw rst. Thirteen rules, counted from the reproduced list in §2.2.)*
- [S22] Argo Workflows, *Conditionals.*
  https://raw.githubusercontent.com/argoproj/argo-workflows/main/docs/walk-through/conditionals.md
  *(raw md)*
- [S26] Apache Airflow, *Python operators* — ShortCircuitOperator.
  https://raw.githubusercontent.com/apache/airflow/main/providers/standard/docs/operators/python.rst
  *(raw rst)*

**Liveness, supervision and failure policy — first-party (low volatility)**

- [S9] Kubernetes, *Liveness, Readiness, and Startup Probes.*
  https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/pods/probes.md
  *(raw md)*
- [S10] Kubernetes, *Jobs* — "Pod failure policy."
  https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/controllers/job.md
  *(raw md; Hugo shortcodes returned intact)*
- [S25k] Kubernetes, *Deployments* — "Deployment status."
  https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/controllers/deployment.md
  *(raw md. Labelled `S25k` to avoid collision with [S25].)*
- [S32] Kubernetes, *Configure Liveness, Readiness and Startup Probes.*
  https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes.md
  *(raw md; the caution block in §5.2 was the only caution the fetch returned, and it is quoted
  in full there)*
- [S11] systemd, `systemd.service(5)` — `WatchdogSec=`.
  https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.service.xml *(raw XML)*
- [S12] Erlang/OTP, *Supervisor Behaviour* — Restart Strategy, Maximum Restart Intensity.
  https://raw.githubusercontent.com/erlang/otp/master/system/doc/design_principles/sup_princ.md
  *(raw md; `master` confirmed as `default_branch` via the GitHub repos API before fetching)*
- [S13] Temporal, *Detecting Activity failures.*
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/detecting-activity-failures.mdx
  *(raw mdx; `main` confirmed as `default_branch` via the GitHub repos API)*
- [S20] Monitoring Plugins, *Development Guidelines* — plugin return codes.
  https://www.monitoring-plugins.org/doc/guidelines.html *(**rendered HTML — reduced
  confidence**, short spans only)*

**Computed predicates over artifacts — first-party (low/medium volatility)**

- [S8] dbt Labs, *Add data tests to your DAG.*
  https://raw.githubusercontent.com/dbt-labs/docs.getdbt.com/current/website/docs/docs/build/data-tests.md
  *(raw md; `current` confirmed as `default_branch` via the GitHub repos API)*
- [S14] dbt Labs, *`dbt build` command reference.*
  https://raw.githubusercontent.com/dbt-labs/docs.getdbt.com/current/website/docs/reference/commands/build.md
  *(raw md. A first fetch returned a prose summary; the sentence quoted in §1.2 and P3 comes from
  a second, verbatim-only fetch.)*
- [S21] Great Expectations, *Create a Checkpoint with Actions.*
  https://raw.githubusercontent.com/great-expectations/great_expectations/develop/docs/docusaurus/docs/core/trigger_actions_based_on_results/create_a_checkpoint_with_actions.md
  *(raw md)*
- [S15] pytest, *Exit codes.*
  https://raw.githubusercontent.com/pytest-dev/pytest/main/doc/en/reference/exit-codes.rst
  *(raw rst. A first fetch returned a prose list; the `:Exit code N:` lines quoted in §1.1 and P6
  come from a second, verbatim-only fetch. Seven codes, counted from the reproduced list.)*
- [S16] Git, *diff-options* — `--exit-code`, `--quiet`.
  https://raw.githubusercontent.com/git/git/master/Documentation/diff-options.adoc *(raw adoc)*
- [S17] coverage.py, *Configuration reference* — `[report] fail_under`.
  https://raw.githubusercontent.com/nedbat/coveragepy/master/doc/config.rst *(raw rst)*
- [S18] Stryker Mutator (StrykerJS), *Configuration* — `thresholds`.
  https://raw.githubusercontent.com/stryker-mutator/stryker-js/master/docs/configuration.md
  *(raw md)*
- [S19] GNU Bash, *Reference Manual* — Pipelines / `pipefail`.
  https://www.gnu.org/software/bash/manual/bash.txt *(plain text; two earlier attempts returned
  HTTP 429 and the third succeeded)*

**Agent-side execution verification (high volatility — 2022–2026)**

- [S23] Gruber, M., Lukasczyk, S., Kroiß, F., & Fraser, G. (2021). *An Empirical Study of Flaky
  Tests in Python.* arXiv:2101.09077. https://arxiv.org/abs/2101.09077 *(abstract via the arXiv
  Atom API — directional)*
- [S24] Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., & Zhou, D.
  (2022). *Self-Consistency Improves Chain of Thought Reasoning in Language Models.*
  arXiv:2203.11171. https://arxiv.org/abs/2203.11171 *(directional)*
- [S25] Chen, B., Zhang, F., Nguyen, A., Zan, D., Lin, Z., Lou, J.-G., & Chen, W. (2022).
  *CodeT: Code Generation with Generated Tests.* arXiv:2207.10397.
  https://arxiv.org/abs/2207.10397 *(directional)*
- [S27] Huang, J., Chen, X., Mishra, S., Zheng, H. S., Yu, A. W., Song, X., & Zhou, D. (2023).
  *Large Language Models Cannot Self-Correct Reasoning Yet.* arXiv:2310.01798.
  https://arxiv.org/abs/2310.01798 *(directional)*
- [S28] Chen, X., Lin, M., Schärli, N., & Zhou, D. (2023). *Teaching Large Language Models to
  Self-Debug.* arXiv:2304.05128. https://arxiv.org/abs/2304.05128 *(abstract via the arXiv Atom
  API — directional)*
- [S29] Shinn, N., Cassano, F., Berman, E., Gopinath, A., Narasimhan, K., & Yao, S. (2023).
  *Reflexion: Language Agents with Verbal Reinforcement Learning.* arXiv:2303.11366.
  https://arxiv.org/abs/2303.11366 *(abstract via the arXiv Atom API — directional)*
- [S30] Aleithan, R., Xue, H., Mohajer, M. M., Nnorom, E., Uddin, G., & Wang, S. (2024).
  *SWE-Bench+: Enhanced Coding Benchmark for LLMs.* arXiv:2410.06992.
  https://arxiv.org/abs/2410.06992 *(directional. The figures in §0 and §2.4 come from an
  unabridged `<summary>` returned by `export.arxiv.org/api/query?id_list=2410.06992&max_results=1`
  after a first, ellipsis-containing fetch was discarded.)*
- [S31] Jimenez, C. E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O., & Narasimhan, K.
  (2023). *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* arXiv:2310.06770.
  https://arxiv.org/abs/2310.06770 *(abstract via the arXiv Atom API — directional)*

**Pool cross-references (cited, NOT re-derived, and this paper writes nothing to them)**

- `docs/standards/architecture/research/raw/code_routed_control_flow.md` — header records
  `Last validated: 2026-08-03`, `Critic: PASS-WITH-FIXES` (round 3). Cited for: §0 finding 3(b)
  and N6 (the open questions this paper extends); §2.2 (the convergent middle); §4.1–4.2
  (constrained decoding guarantees and their limits); §4.4 + N5 (the under-used abstention arm);
  P5 (total functions), P8, P9; §2.4.2 (TEP-0074); §6.1–6.2 (the measured case against
  orchestration).
- `docs/standards/architecture/research/raw/convergence_stopping.md` — header records
  `Last validated: 2026-08-03`, `Critic: PASS`. Cited for: P11 (convergence detection requires
  typed comparable finding records); P10 (+129% tokens); §5.1–5.7 (the case against a naive
  "stop when a pass finds nothing" rule). **Not re-researched here.**
- `docs/standards/architecture/research/raw/claude_code_integration_surface.md` — header records
  `Last validated: 2026-07-25`, `Critic: PASS`. Cited for: §7's result-envelope field list and
  `system/init` inventory; §5's statement that there is no first-party exit-code table and that
  several codes are undocumented. **The envelope field list is not re-established here.**

*(Currency: this component's research pool was empty before this paper, so no revalidation
verdict is asserted for any upstream paper beyond what its own header states, quoted above.)*

**Internal evidence (not citations — recorded for traceability)**

- [I1] `scripts/workflows/build.sh` — line 60 `set -euo pipefail`; line 198 the PR-URL
  extraction; line 227 `source .../activities/wait-for-ci.sh`; line 266 the child invocation
  under `if ! … | tee`; lines 277–283 the `VERDICT_LINE` grep and its fail-closed default; lines
  329–343 the `case` that routes on it.
- [I2] `scripts/workflows/activities/run-claude.sh` — line 167
  `grep -q '"subtype":"error_max_turns"' "$LOG_FILE"`; lines 194–222 the `COMPLETION_PATTERN`
  contract, including the comment quoted in §5.2 and the `jq -r 'select(.type == "result") |
  .result // ""'` read. **`.is_error` appears nowhere in this file.**

---

## 7. Test plan — what research cannot settle

Research established the taxonomy, the prior art and the boundary. It cannot supply the
following, all of which are cheap and all of which the phase doc's "Design it" milestone depends
on. Ordered by decision value.

**T1. Determine the exit-code ↔ `is_error` relationship for `claude -p` on the pinned version.**
*Because:* N2 — there is no first-party exit-code table
[`claude_code_integration_surface.md` §5], and the entire "gate on `is_error`" milestone assumes
the two can disagree. *Design:* force each of — auth failure, rate-limit exhaustion, `--max-turns`
exceeded, `--max-budget-usd` exceeded, a usage-policy refusal, SIGTERM — and record the tuple
(process exit code, `result.subtype`, `result.is_error`, `result.result` non-empty). *Reads out:*
whether `.is_error` adds information the shell's `pipefail`-propagated exit status does not
[S19], [I1]. **If it never disagrees, the milestone is a no-op and should say so.**

**T2. Measure how often a completed child produces an empty diff.** *Because:* P6 and P7 —
"exited cleanly" and "did work" are different facts, and the empty-diff probe has inverted
polarity so it must be written and tested deliberately [S15], [S16]. *Design:* over N ≥ 30
completed `build-draft` runs, record `git diff --quiet` against the branch point and cross-tab
against the run's outcome. *Reads out:* whether the no-op case is real at this scale, and
therefore whether the class (ii) "did work happen" gate earns its place.

**T3. Decide the disagreement policy empirically, not by design.** *Because:* N1 — no surveyed
system defines precedence between an asserted and a computed result, so this fleet has to pick
one and there is no prior art to borrow. *Design:* instrument, without changing behaviour, the
four-cell table (`is_error` clean/dirty) × (`VERDICT:` MERGE/HOLD) over N ≥ 30 runs.
*Reads out:* which cells actually occur. **If the off-diagonal cells are empty, adopt the GitHub
Actions shape anyway — record both under distinct names [S2] — but do not build composition
machinery for a case that never happens.**

**T4. Establish whether a definite-progress signal can be derived from the `stream-json`
event stream.** *Because:* P9 — Temporal states the precondition ("Your underlying task must be
able to report definite progress" [S13]), and a stall probe is worthless without one.
*Design:* over recorded logs, test candidate progress predicates (a new `tool_use` with a
file-write effect; a monotonically increasing turn count with a changing worktree SHA) against
runs known to have stalled versus runs known to have been productive. *Reads out:* whether the
liveness half of §2.3's prior art is reachable here at all, or whether the only available probe
is a wall clock. *Fails if:* no predicate separates the two populations — in which case say so
and use `progressDeadlineSeconds`-style timing alone [S25k].

**T5. Cost the nested retry budget.** *Because:* P10 — OTP documents that nested restart
intensities multiply [S12], and this fleet nests at least three levels (Claude Code's ≤10
internal retries per `claude_code_integration_surface.md` §5; `run-claude.sh`'s 3-attempt
rate-limit probe [I2]; `build.sh`'s single loop-back [I1]). *Design:* compute the worst-case
product and compare it against observed maxima in the existing JSONL logs. *Reads out:* whether
the effective retry ceiling is the one anybody intended.

**T6. Measure the split abstention arms separately.** *Because:* §5.5 argues
`HOLD - needs-assistance` is doing two jobs — "I could not check" (computable, reliable) and
"a human must rule" (not computable, and the arm the literature predicts is under-emitted
[`code_routed_control_flow.md` §4.4, N5]). *Design:* extend `code_routed_control_flow.md`'s T3
by classifying each `needs-assistance` occurrence into the two kinds. *Reads out:* whether
splitting the vocabulary member into two would move any routing decision — and if it would, the
computed arm can be taken off the model entirely.

**Not settleable by any of the above, and worth recording as such:** whether a routing decision
made correctly on a narrow observable is better or worse than one made plausibly on a broad
assertion. §5.1 draws the boundary; §0 finding 2 shows the CI world has not solved it either;
nothing in the located corpus measures it.
