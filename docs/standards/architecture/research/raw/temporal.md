# Temporal as a vendor commitment

```
Topic:          What does committing to Temporal as a VENDOR cost and commit us to — the
                orchestration primitives the agent layer actually depends on, the operational
                burden of self-hosting versus Temporal Cloud, and the release/upgrade cadence
                and licence we inherit?
Feeds:          Phase: Temporal Integration — the self-hosted-vs-Cloud decision, the server
                upgrade cadence the fleet must keep, and the workflow-side primitive surface
                (child workflows, signals/queries/updates, continue-as-new, saga, pause) that
                workflow authoring rests on. Explicitly NOT the activity mechanics
                (python_sdk_long_activities.md) nor worker placement and routing
                (dedicated_edge_routing.md).
Last validated: 2026-08-05
Revalidate:     high — 6 weeks   (see the volatility ruling below)
Confidence:     DEFINITIVE on the licence (MIT), the workflow-execution limits, the
                orchestration primitive semantics, the Temporal Cloud billing model and the
                definition of a billable Action — all first-party and documented.
                DEFINITIVE-AS-A-NEGATIVE on the absence of any first-party Anthropic/Claude
                runtime integration, reached by enumerating `temporalio/contrib`. DEFINITIVE
                on the release WINDOW (which releases postdate 2026-07-04), established by a
                paginated walk plus tag-existence probes — NOT by any list total, which the
                API's retrieval layer truncates (§6.1). WORDING-UNCERTIFIED, but definitive
                as to substance, on every span drawn from a documentation source: these were
                extraction fetches, not byte-for-byte dumps, so nothing below is presented as
                a quotation — see §0, and note that this marker is about TRANSCRIPTION, never
                about whether the fact is first-party. REDUCED on Temporal Cloud pricing
                FIGURES (rendered pages, though now documentation-grade rather than marketing
                only). DERIVED on the cost verdict (§5), the primitive-to-failure-mode mapping
                (§2.2) and the self-host-vs-Cloud reading (§3).
Critic:         PASS-WITH-FIXES (two independent verification passes. Every cited source
                re-fetched and confirmed to exist; every count in the paper re-derived by
                independent enumeration; no fabrication and no false quotation survives, with
                the §0 no-quotation discipline checked mechanically both times. Pass 1 fixed:
                a release count that was a truncated-fetch artifact asserted under an
                "enumerated" heading, now carried by a paginated walk plus two 404 tag probes;
                two FALSE NEGATIVES — "no first-party Cloud pricing" and "no first-party
                definition of a billable Action" — which were repo-path absences written up as
                documentation absences, now replaced by the sourced billing model and the
                eleven billable Action categories; and a restructure claim built on a path the
                sibling paper never cited, restated as the two-locations finding it is. Pass 2
                re-verified all four at source and caught two defects INTRODUCED by those
                repairs: a marketing-page plan-count discrepancy that does not exist (a
                re-fetch returns all four tiers; the claim is deleted, not softened), and a
                stale §7 clause still calling the Cloud decision blocked after §3.2 had
                unblocked it. Plus marker, confidence-tag, citation-entry and quotation
                cleanups. NOT a clean pass — the repair rounds are the record) — 2026-08-05
```

> **Volatility ruling (Research Standard §3 mixed-volatility rule, §5 bounds).** The header takes
> **high** because the fastest-decaying material present is high-tier: Temporal Cloud pricing,
> the maturity labels on preview surfaces (Serverless Workers, Workflow Streams, Workflow Pause),
> and the AI-integration inventory.
>
> **The interval is 6 weeks — the TOP of §5's high band — because the subject barely moved on the
> axes this paper's conclusions rest on.** Measured over the 32 days since the last validation:
> the server shipped exactly two releases, both on the same day (v1.31.2 and v1.30.6, 2026-07-08),
> and **none in the four weeks since** [S2]; the licence is unchanged [S1]; the workflow-execution
> limits read today are identical to those a sibling paper read from server source two days ago
> [S17, and `python_sdk_long_activities.md` §4]; and retry, child-workflow, continue-as-new and
> determinism semantics are stable encyclopedia material. What *did* move is preview-tier surface
> this paper **tracks but does not rest on** (§6). §5's rule is that a topic that did not move
> takes its band's maximum.
>
> **On-announcement override triggers — revalidate immediately, do not wait for the interval, if
> any of these fire:** Temporal Cloud pricing or plan structure changes; a first-party
> Anthropic/Claude *runtime* integration appears in `temporalio/contrib` or the docs (§6.3); the
> licence changes from MIT; a server release introduces a breaking persistence or upgrade-path
> change; or Serverless Workers gains a self-hostable or bare-metal compute provider.
>
> **Refresh scope:** re-verify §3.2 (pricing), §6 (what moved) and the `contrib` enumeration in
> §6.3. §2 and §4 may be skipped unless a server minor release lands.

---

## §0 Fetch-fidelity note — read before quoting anything out of this paper

Research Standard §3 permits a span to be presented as a **quotation** only when its exact
character sequence was returned by a fetch. In this sweep, the GitHub **API** responses (release
metadata, directory listings) came back as structured data and are trustworthy as such. Every
**documentation `.mdx`** span, by contrast, came back through an *extraction* fetch — the fetching
layer was asked for verbatim spans and returned prose containing them, which does not certify
byte-identity.

**Consequence, applied throughout: this paper contains no quotation marks around any
documentation-derived span.** Quote marks appear in exactly three permitted classes, all
self-referential and none load-bearing on a vendor fact — (1) spans from the **pre-standard version
of this paper**, quoted so corrections are auditable and verified character-exact against
`git show fff8aec`; (2) spans from **earlier drafts of this refresh**, quoted in the correction
notes; (3) **rhetorical or hypothetical** phrasing that is the paper's own. Any quote mark outside
those three classes is a defect — the invariant is mechanically checkable and has been checked twice.
Everything from a documentation source is paraphrased and marked
`[S-n, doc, wording-uncertified]`. The *facts* are first-party and documented; the *wording* is not
certified. A downstream author who needs a literal quote must re-fetch the file and certify it
themselves. This costs the paper some rhetorical force and is the correct trade — a paraphrase
wearing quote marks is a fabrication regardless of how good the URL was.

**Two markers, deliberately distinguished — read this before downgrading anything.** An earlier
draft used `reduced` for both of the situations below, which let a section read in isolation
downgrade a fact the header calls definitive. They are now separate tokens:

| Marker | What is uncertain | What is NOT uncertain |
|---|---|---|
| `[S-n, doc, wording-uncertified]` | Only the **transcription** — the exact characters were not certified by the fetch | Nothing else. The source is first-party and documented, and the **fact is definitive**. |
| `[S-n, rendered, reduced]` | The **fact itself** carries lower confidence — a rendered/JS-heavy page, per §3's sourcing rules | — |

So: `wording-uncertified` is not a weaker class of evidence, it is a weaker class of *quotation*.
A consuming agent should treat a `wording-uncertified` fact as definitive and simply not reproduce
its phrasing as a quote.

## §0.1 Scope discipline — what this paper owns

The pool has four Temporal-adjacent papers and they were overlapping. This refresh re-cuts the
boundary explicitly:

| Paper | Owns |
|---|---|
| [`durable_execution.md`](durable_execution.md) | Vendor-INDEPENDENT concepts: event sourcing, deterministic replay, the engine landscape (Restate, Inngest, LangGraph, Cadence), when durability is not needed. **Not re-derived here.** |
| [`python_sdk_long_activities.md`](python_sdk_long_activities.md) | The ACTIVITY-side mechanics: heartbeats, the four timeouts, cancellation delivery, worker slots and tuning, payload/blob limits read from server source, External Storage. **Not re-derived here.** |
| [`dedicated_edge_routing.md`](dedicated_edge_routing.md) | Task queues, routing, worker placement, Worker Deployments/Versioning, sticky execution, capability discovery. **Not re-derived here.** |
| **This paper** | Temporal **as a vendor**: the licence and what is actually being adopted; the WORKFLOW-side orchestration primitives and their limits; the operational cost of self-hosting versus Cloud; the release and upgrade cadence the fleet inherits; and the standing maturity/integration inventory. |

**This paper's topic was re-scoped at this refresh.** The prior question — *"Does Temporal supply
what a durable workflow layer needs, and at what cost in complexity?"* — is half-dead: the
supply half is settled (Temporal is chosen and the port is underway), and its stated `UNVERIFIED`
gap on heartbeat and payload limits was **closed by `python_sdk_long_activities.md` on
2026-08-03**, which says so in its own citation list. What survives is the *cost and commitment*
half, which no paper owned. See §7 for the full re-scoping argument.

---

## §1 Primer — what is actually being adopted

**Temporal is MIT-licensed.** The `LICENSE` file at `temporalio/temporal@main` is the MIT License,
carrying copyright lines for Temporal Technologies Inc. (2025) and Uber Technologies, Inc. (2020)
[S1, definitive — raw file]. This is the single most important fact in the vendor question and it
is the one the previous version of this paper never stated: **the self-hosted escape hatch is real
and permissive, not a source-available or BSL arrangement.** A Cloud price change is a commercial
event, not an existential one.

**What you run when you self-host.** The self-hosted deployment guide describes the core Temporal
Server plus a separate UI server, backed by a persistence store; the databases named are Apache
Cassandra, MySQL, or PostgreSQL, with SQLite appearing for the local/dev path, and Elasticsearch
appearing for advanced visibility [S9, doc, wording-uncertified]. The server README's local-start path is
`brew install temporal` then `temporal server start-dev` [S5, doc, wording-uncertified] — a single-binary dev
server, which is what makes the *evaluation* cost near zero and is frequently mistaken for the
*production* cost. §5 separates them.

**What Temporal itself tells self-hosters they are signing up for.** The production-readiness
checklist is unusually candid, and three of its statements are load-bearing for our decision
[S8, doc, wording-uncertified]:

- Shard capacity — and often overall service throughput — is set at build time and **cannot be
  adjusted later**. This is a one-way door taken before the first workflow runs.
- The operator must create and maintain the hosting infrastructure and the persistence data
  stores.
- Temporal recommends not falling behind on server versions, upgrading sequentially without
  skipping minor versions (patch versions may be skipped), and load/availability testing during
  upgrades.

The upgrade guide reinforces the sequencing: upgrade one minor version at a time, reaching the
latest patch of each before advancing, because backward compatibility is guaranteed only between
two successive minor versions — skipping versions risks older data formats becoming unreadable.
Schema migration is a distinct step run with `temporal-sql-tool` (Postgres/MySQL),
`temporal-cassandra-tool`, or `temporal-elasticsearch-tool`, and roughly ten minutes per version
should be allowed for the History Service to reload shards [S7, doc, wording-uncertified].

**[derived, from S7 + S8 + S2]** The upgrade obligation is the real recurring cost of self-hosting,
and it compounds with this repo's fleet shape. Sequential-minor upgrades plus a schema migration
step plus per-machine workers on independent uptime (`dedicated_edge_routing.md` §4.3) means a
server upgrade is a *scheduled fleet operation*, not a `docker pull`. Against that, §6.1's
measured release cadence is the mitigating fact: the pace is slow enough to absorb.

## §2 The specific model — the orchestration primitives the agent layer depends on

### 2.1 The failure-mode table, now sourced

**This table is the one genuinely useful artifact the pre-standard version of this paper carried,
and it is kept.** It has been rebuilt so every row names its source, and three rows gained
qualifications that materially change how a planner should read them. The right-hand column's
*mapping* — agent failure mode to Temporal primitive — is **the paper's own derived framing**;
what is sourced is that each named primitive exists and behaves as stated.

| Agentic failure mode | Temporal primitive | Source, and the qualification that matters |
|---|---|---|
| LLM call fails or is rate-limited mid-run | Activities with retry policies | Activities retry **by default**; workflows do **not** — a workflow execution is not associated with a default retry policy. Defaults: initial interval 1 second, backoff coefficient 2.0, maximum interval 100× the initial interval, maximum attempts unlimited [S11, doc, wording-uncertified]. **The unlimited default is a hazard for paid LLM calls and must be overridden.** |
| Run must survive hours/days and process restarts | Durable workflow execution | Concept settled in [`durable_execution.md`](durable_execution.md); not re-derived. |
| Multi-agent coordination (planner delegates to sub-agents) | Child workflows | **Heavily qualified.** A child workflow is spawned from within another workflow in the same namespace. Temporal advises a single parent should not spawn more than **1,000** children; children produce more event-history events than activities do; children do **not** carry over when the parent continues-as-new; and Temporal recommends starting with one workflow using activities until there is a clear need, stating there is no reason to use child workflows merely for code organisation [S12, doc, wording-uncertified]. |
| Agent must pause and wait for an external event | Signals, timers — **and Updates** | Signals are asynchronous write requests with no awaitable response or error. Queries are read requests that cannot block. **Updates are synchronous tracked write requests whose sender can await completion or failure** [S13, doc, wording-uncertified]. **The old table omitted Updates entirely** — for a human-approval gate that needs an acknowledgement, Update, not Signal, is the primitive. |
| Tool call is non-idempotent and could double-fire | Deterministic replay + activity idempotency | Determinism is a *constraint on the author*, not a free property — §2.3. Activity-level idempotency mechanics are owned by [`python_sdk_long_activities.md`](python_sdk_long_activities.md). |
| Undo partial work when a downstream step fails | Saga via compensating activities | First-party design pattern: each step is a local transaction with a corresponding compensation, executed in reverse order on failure. **Its own stated limits:** eventual consistency only, intermediate states remain visible, and some operations have no meaningful compensation [S19, doc, wording-uncertified]. |
| Inspect what the agent did after the fact | Event history + query API | Queries read live state but cannot block [S13]; history is bounded — §2.2. |
| **Stop a runaway agent without killing it** *(new — the old table had no row)* | **Workflow Pause** | Pause stops a workflow execution from making new progress until unpaused. Self-hosted requires **server v1.30.0+** with `frontend.WorkflowPauseEnabled`, CLI v1.6.0+, and self-hosted UI v2.47.2+; on Temporal Cloud, pre-release access is invite-only [S15, doc, wording-uncertified]. **Directional on maturity, definitive that a version floor exists.** |
| **Stream partial output to an operator surface** *(new)* | **Workflow Streams** | A durable event channel hosted inside a workflow; publishers append to topics, subscribers attach by workflow ID and consume by long-polling, with independent offsets and reconnect without loss. Sized for modest fan-out — tens of publishers/subscribers — not ultra-low latency [S14, doc, wording-uncertified]. Directly relevant to the pool's open operator-interface question. |

### 2.2 The limits a workflow author must design against

From the workflow-execution limits page [S17, doc, wording-uncertified], corroborated against server source read
independently by [`python_sdk_long_activities.md`](python_sdk_long_activities.md) §4 on 2026-08-03,
which agrees on every value:

| Limit | Value |
|---|---|
| Event history — maximum events | 51,200 |
| Event history — maximum size | 50 MB |
| Event history — warning thresholds | 10,240 events / 10 MB |
| Incomplete activities, child workflows, signals, or cancellation requests per execution | 2,000 each (default) |
| Incomplete Nexus operation requests per execution | 30 (default) |

The self-hosted defaults page adds that these four pending-command types fail when the concurrent
pending count exceeds 2,000, recommends staying under 500 for performance, and notes that as of
v1.21 the individual pending limits are overridable via dynamic configuration [S6, doc, wording-uncertified].

**Continue-as-new is the sanctioned answer to all of it.** It checkpoints workflow state and starts
a fresh execution; state is passed as arguments to the new run, which keeps the same workflow ID but
gets a new run ID and **its own fresh event history** [S16, doc, wording-uncertified]. The page states
the following reasons it is needed — presented as the facts the page carries, without asserting the
page's own enumeration boundary, which two independent extractions grouped differently: a long or
large history bogs down performance; an execution may generate more events than the limits allow;
and a long-lived execution can hit workflow-versioning problems when it started on older code and
continues on newer code [S16, doc, wording-uncertified].

**[derived, from S12 + S16]** Two of those interact badly and a planner should see it before
designing the agent topology: **child workflows do not carry over continue-as-new** [S12], and
continue-as-new is the required mitigation for history growth [S16]. A long-lived parent that both
fans out to children and must bound its history has to reconcile those two facts explicitly. This
is a design constraint on the parent/child decomposition the roadmap already commits to, and it is
not visible from either page alone.

### 2.3 Determinism is a tax on the author, not a property of the runtime

The workflow-definition page is explicit that the burden sits with the developer: workflow code must
make the same Temporal API calls in the same sequence given the same input; the call classes that
produce commands — timers, activity scheduling, child workflows, signalling external workflows,
Nexus operations, ending executions, `patched()` calls, upserting search attributes and memos, side
effects — must not be reordered, added, or removed without proper versioning; a definition may not
branch on local time or a random number; and operations that do not purely mutate execution state
should go through an SDK API [S18, doc, wording-uncertified].

**[gap — not closed.]** I could not obtain, from `encyclopedia/workflow/patching.mdx`, a first-party
statement of *why* patching is required, of what a non-deterministic change causes in general, or an
enumerated list of what counts as a breaking change to workflow code. Search method: fetched
`docs/encyclopedia/workflow/patching.mdx` raw with a request for exactly those three items; the
extraction reported the page covers only `patched()` mechanics and replay behaviour and contains
none of the three. `workflow-definition.mdx` [S18] carries the command-list above, which is the
closest available substitute but is a list of *command-producing calls*, not a list of *breaking
changes*. **The versioning-discipline cost is therefore real but unpriced from first-party sources
in this sweep**; `durable_execution.md` §6 states it qualitatively.

## §3 Comparative landscape — the deployment choice, not the engine choice

The *engine* comparison (Restate, Inngest, LangGraph, Cadence, DBOS) is settled in
[`durable_execution.md`](durable_execution.md) §4 and
[`python_sdk_long_activities.md`](python_sdk_long_activities.md) §6.2 and is **not re-run here**.
The live comparison for a vendor-commitment paper is *self-host versus Cloud* — which is how Temporal
itself frames the deployment choice: its production-deployment index offers exactly a Cloud guide, a
self-hosted guide, and Worker Deployments [S33, doc, wording-uncertified].

### 3.1 Self-hosted

Cost is labour, not licence: MIT [S1], no fee, and the burden enumerated in §1 — infrastructure and
data stores you build and maintain, a shard-capacity decision that cannot be revisited, and a
sequential-minor upgrade treadmill with a schema-migration step [S7, S8]. The single-binary
`temporal server start-dev` path [S5] makes evaluation nearly free and is **not** the production
shape.

### 3.2 Temporal Cloud — the billing model, and where it is and is not documented

**A provenance correction, stated first because an earlier draft of this paper got it backwards.**
The pricing material is **absent from the documentation REPOSITORY but present on the documentation
SITE**. Those are different claims and only the first is true of the repo. Specifically:

- `docs/cloud` enumerates to **24 entries** with no `pricing.mdx`, and `docs/cloud/billing-and-usage`
  to **4** (`actions-usage.mdx`, `billing-api.mdx`, `billing.mdx`, `index.mdx`) [S30, definitive —
  enumerated].
- The raw path `docs/cloud/pricing.mdx` returns **HTTP 404**, and so does `docs/cloud/actions.mdx`.
- **But `docs.temporal.io/cloud/pricing` and `docs.temporal.io/cloud/actions` are live first-party
  DOCUMENTATION pages** carrying the full model [S34, S35].

**The lesson, recorded because it is the reusable part:** a 404 on a repo path establishes only that
the content is not at that path. An earlier draft turned that into "not in first-party
documentation" and then built a decision-blocking gap on it. Repo-absence is not documentation-absence.

**The billing model** [S34, rendered, reduced]. The monthly charge is a platform fee expressed as a
*floor against a percentage of usage* — a structure that a starting-at framing obscures:

| Plan | Monthly platform fee | Included |
|---|---|---|
| Essentials | **greater of $100/mo or 5% of Usage Spend** | 1M Actions, 1 GB active storage, 40 GB retained storage |
| Business | **greater of $500/mo or 10% of Usage Spend** | 2.5M Actions, 2.5 GB active storage, 100 GB retained storage |
| Enterprise | priced annually (contact Sales) | 10M Actions, 10 GB active storage, 400 GB retained storage |
| **Mission Critical** | priced annually (contact Sales) | 10M Actions, 10 GB active storage, 400 GB retained storage |

Action overage runs in declining per-million tiers — $50 for the first 5M, then $45, $40, $35, $30,
and $25 across the 5M–200M range, with over-200M routed to Sales. Storage is $0.042/GBh active and
$0.00105/GBh retained [S34, rendered, reduced; every figure independently matched against the
marketing page S26]. A $1,000 trial credit and a $6,000 startup-program credit for companies under
$30M funding are advertised on the marketing page [S26, rendered, reduced]. Self-hosting is
presented as the free option.

*(An earlier draft of this paper claimed the marketing page showed only three plans against the
documentation page's four, and told the reader to distrust [S26] on that basis. **That discrepancy
does not exist** — a re-fetch of [S26] with a prompt asking explicitly for every tier including
add-ons returned Mission Critical, both in the plan-comparison table and as an Enterprise support
add-on. The original omission was an artifact of a narrower extraction prompt, not a difference
between the vendor's pages. The claim is deleted rather than softened. **Standing caution: an
absence claim about a JS-heavy rendered page is sourcing-fragile under §3 regardless of how the
fetch comes back** — this paper makes no absence claims about [S26] or [S34].)*

**What a billable Action is — the gap an earlier draft wrongly declared open.** Three first-party
sources define it. The glossary, which is a **raw `.md`** at the root of `docs/` — one directory above
the `docs/cloud` listing enumerated above — defines an Action as the fundamental pricing unit in
Temporal Cloud and the building block of workflow executions, and links to `/cloud/pricing#action`
[S36, definitive — raw source; wording uncertified per §0, substance not]. The dedicated Actions page
describes them as the primary unit of consumption-based pricing, tracking billable operations such as
starting workflows, recording a heartbeat, or sending signals [S35, doc, wording-uncertified].

**The billable categories, enumerated from [S35]:** Workflow (starts, resets, search-attribute
updates, execution-option changes), Activity (scheduling, retries, **and heartbeat recording**, for
both standard and local activities), Timer (including implicit timeouts), Signal, Query, Update
(accepted **and rejected**), Schedule, Nexus, Export, Fairness (an hourly charge when enabled), and
Capacity (provisioned capacity). Counting that enumeration: **11 categories**
[S35, doc, wording-uncertified].

*(The narrower finding from `actions-usage.mdx` survives and is worth keeping: its tip-box lists
Query, Activity Heartbeats, rejected Updates, Export, Schedule and Replicated Actions as excluded
from **estimates** [S31]. That is a statement about the estimator's coverage, not about billability —
and [S35] shows several of those same items ARE billable. Do not read the estimator's exclusions as a
discount.)*

**[derived, from S34 + S35 + [`python_sdk_long_activities.md`](python_sdk_long_activities.md) §1.4
and §7.3 + the repo's own economics — and this REPLACES the earlier "do not decide"
recommendation.]** The blocking gap is closed, so the deferral it justified no longer stands on that
ground. What the corrected evidence supports:

1. **The model is now sizeable, not unknown — and the size is BOUNDED.** An agent workload's Action
   count is dominated by activity scheduling and retries, and — the detail that matters most for
   this repo — **activity heartbeat recording is a billable Action** [S35].
   [`python_sdk_long_activities.md`](python_sdk_long_activities.md) recommends heartbeating per
   `stream-json` line on a 10–60 minute activity, on the reasoning that the SDK's throttle makes
   per-line heartbeats free. **That reasoning is correct about SDK and network cost and does not
   transfer to Temporal Cloud billing.**
   **But the same throttle that makes heartbeats free locally also CAPS what they can cost.** That
   sibling reads the effective interval from raw SDK source as
   **min(0.8 × `heartbeat_timeout`, `max_heartbeat_throttle_interval`)**, where the latter defaults
   to **60 s** — so heartbeat Actions are emitted at most once per throttle interval regardless of
   how often the activity calls `heartbeat()`. **Worked ceiling:** at the 60 s default, a 60-minute
   activity emits at most ~60 heartbeat Actions; a 60 s `heartbeat_timeout` gives 48 s intervals and
   ~75. Per-line heartbeating does **not** mean per-line billing. The line item is real, is not zero,
   and is computable in advance — state it that way, because a planner told only "heartbeats are
   billable" will over-price it by orders of magnitude.
2. **The $100/mo is a FLOOR on a usage-scaled fee, not an entry price.** For a single-operator fleet
   whose usage spend is small, 5% of usage will sit far below $100, so **the floor binds and $100/mo
   is the real number** — which is the same order as the Claude Max subscription this repo's
   economics already assume (`subscription_economics.md` owns that thesis). The earlier draft reached
   a similar conclusion by reading $100 as an entry point; the conclusion survives, but it survives
   *because the floor binds*, and a reader must be able to see that rather than infer it.
3. **Revised recommendation:** self-host-vs-Cloud is **no longer research-blocked**. It is now a
   sizing question with a known model, and the remaining unknown is a measurement — how many Actions
   one representative agent run consumes — not a missing definition. T3 is accordingly re-framed in
   §8 from "close the blocker" to "calibrate against a known billing model." The one genuine
   caution that still argues for measuring before committing is (1): the heartbeat line item is
   easy to overlook precisely because the SDK treats heartbeats as free.

## §4 What this provides — enumerated, citable properties

Properties a plan may rely on, anchored at server v1.31.2 [S2] / Python SDK 1.31.0 [S3]:

1. **A permissive, forkable licence.** MIT [S1, definitive]. Self-hosting is a permanent option, not
   a vendor concession.
2. **A slow, predictable server release cadence.** Established in §6.1 by a paginated walk plus tag
   probes — no release in the four weeks to 2026-08-05 [S2, S37, definitive].
3. **A documented, sequential upgrade path** with per-database schema tooling and a stated
   compatibility window of two successive minor versions [S7, doc, wording-uncertified].
4. **Activity-level retry as a default**, with documented default backoff parameters
   [S11, doc, wording-uncertified] — and the matching fact that workflows do not retry by default.
5. **Three distinct message-passing shapes** with different guarantees: Signal (async write, no
   response), Query (non-blocking read), Update (synchronous tracked write with a response)
   [S13, doc, wording-uncertified].
6. **Child workflows with a stated fan-out ceiling** (~1,000 per parent) and explicit first-party
   advice to prefer activities until a clear need exists [S12, doc, wording-uncertified].
7. **Hard, knowable workflow-execution limits**: 51,200 events / 50 MB history, 2,000 pending
   operations per class, 30 pending Nexus operations [S17, doc, wording-uncertified], corroborated against server
   source by a sibling paper.
8. **A first-party history-bounding mechanism** — continue-as-new, with documented carry-over
   semantics [S16, doc, wording-uncertified].
9. **A first-party compensation pattern** with its limitations stated by the vendor
   [S19, doc, wording-uncertified].
10. **A pause/unpause control plane** for stopping a running execution without terminating it, with
    a stated self-hosted version floor of server v1.30.0+ [S15, doc, wording-uncertified].
11. **A durable streaming channel** for operator-facing partial output [S14, doc, wording-uncertified].
12. **A large, enumerable design-pattern catalogue** — `docs/design-patterns` contains **46 files**,
    reached by enumerating the GitHub contents listing and counting the enumeration [S21,
    definitive-as-a-count], including `saga-pattern`, `long-running-activity`, `resumable-activity`,
    `approval`, `polling`, `entity-workflow`, `priority-task-queues` and `worker-specific-taskqueue`.

## §5 Honest boundary analysis — where Temporal is the wrong answer, and what it costs

The prior version of this paper contained **no case against its own thesis**. Under §3 that made it
advocacy. The case against:

- **The dev-server single binary is not the production system, and conflating them is the standard
  costing error.** `temporal server start-dev` [S5] is one command; the production system is a
  multi-role server plus a persistence store plus, for advanced visibility, Elasticsearch [S9], with
  infrastructure the operator builds and maintains [S8].
- **Shard capacity is a one-way door.** Set at build time, not adjustable later [S8, doc, wording-uncertified].
  A self-hosted deployment stood up casually for a two-machine fleet encodes a throughput ceiling
  before anyone has measured what the fleet needs.
- **The upgrade treadmill is the recurring cost.** Sequential minors, no skipping, schema migrations,
  ~10 minutes per version for shard reload, and a recommendation to load-test during upgrades
  [S7, S8]. For a fleet of independently-uptimed machines this is a coordinated operation, and
  `dedicated_edge_routing.md` §4.3 shows the worker-versioning side of the same problem.
- **Determinism is a permanent tax on every workflow author** [S18], and the versioning-discipline
  cost could not be priced from first-party sources in this sweep (§2.3 gap).
- **Child workflows are not the free composition primitive the old table implied.** Temporal itself
  says to prefer activities until a clear need exists, caps practical fan-out around 1,000, notes
  higher event cost, and warns they do not survive continue-as-new [S12].
- **The default retry policy is wrong for paid work.** Unlimited maximum attempts [S11] against a
  metered LLM API is a cost incident waiting to happen; every activity in this repo's design must
  override it.
- **Cloud's cost scales with a unit our design emits heavily, and the headline number hides it.**
  The $100/mo Essentials figure is a *floor on a usage-scaled fee*, not a flat price [S34], and the
  billable-Action categories include **activity scheduling, retries and heartbeats** [S35]. An
  hour-long heartbeating activity per agent run — precisely the shape
  [`python_sdk_long_activities.md`](python_sdk_long_activities.md) recommends — is a workload whose
  Action count is driven by a mechanism the SDK correctly describes as free at the *transport* layer
  and which is *not* free at the *billing* layer. This is a sizing hazard, not a blocker: the model
  is fully documented and the count is measurable (T3).
- **The AI-facing surfaces we would most want are previews.** Workflow Pause is invite-only
  pre-release on Cloud and needs a specific self-hosted server floor [S15]; Serverless Workers is
  Public Preview on AWS Lambda and Pre-release on GCP Cloud Run [S25]; the LangGraph plugin declares
  itself experimental and cautions against production use [S23]. A plan that sequences work behind
  any of these is sequencing behind a preview.
- **There is still no first-party Anthropic/Claude runtime integration** (§6.3) — the paved road runs
  to OpenAI, Google and LangGraph, and this repo's substrate remains hand-rolled.
- **Where Temporal is simply not needed** — the short-task, human-present, cheap-rerun boundary is
  argued with sources in [`durable_execution.md`](durable_execution.md) §6 and is not re-derived.

## §6 What moved since 2026-07-04

### 6.1 Releases — established by a paginated walk, not by a list total

**No total is asserted here, and that is deliberate.** An earlier draft of this paper reported that
the releases API "lists seven releases" under a heading claiming enumeration. That number was a
**truncated-fetch artifact**, and the truncation is demonstrable: `?per_page=100` and `?per_page=15`
both return the *same* 7 items, yet `?per_page=6&page=2` returns six *further* releases (v1.31.0, v1.29.6.1, v1.30.4,
v1.29.6, v1.28.4, v1.30.3) and `?per_page=6&page=3` six more (v1.29.5, v1.28.3.1, v1.29.4.1, v1.30.2,
v1.28.3, v1.29.4). A retrieval layer that caps at 7 regardless of `per_page` is not describing a
7-element population. **Per §3, a count from a retrieval layer is not evidence, so this paper reports
the window it walked instead of a total** [S2, definitive as to the walk].

**A second hazard, which is why the negative needs a method rather than a glance at the top of the
list: the GitHub releases endpoint sorts by `created_at`, not `published_at`, and this very list
demonstrates it** — v1.29.6.1 (`published_at` 2026-05-06, `created_at` 2026-04-24) sorts *below*
v1.31.0 (`published_at` 2026-04-29, `created_at` 2026-04-29) [S2, definitive]. So "nothing recent at
the top" would not have established "nothing published recently."

**What was actually established.** Walking pages 1–3 covers the 18 most recent releases by
`created_at`; across all 18, exactly **two** carry a `published_at` after 2026-07-04 — **v1.31.2 and
v1.30.6, both 2026-07-08** — and every other walked release has `published_at` on or before
2026-06-15 [S2]. The absence of anything newer is corroborated independently of the listing by two
tag-existence probes: `releases/tags/v1.31.3` and `releases/tags/v1.30.7` both return **HTTP 404**
[S37], and `releases/latest` returns v1.31.2 [S2]. **Together those establish the negative — no
server release in the four weeks to 2026-08-05 — without relying on any list total.**

v1.31.2's release body identifies it as a security patch addressing **CVE-2026-5724 (MEDIUM)**, with
a stated potential breaking change: deployments using authorization with replication should set the
`system.disableStreamingAuthorizer` dynamic config to `true` to opt out and avoid replication
connection errors [S2, definitive — release body returned as structured API data].

**[derived, from S2 + S37 — and it is the volatility finding.]** No server release in the four weeks
to 2026-08-05, and the newest patch in each active minor line is confirmed newest by tag probe. The
server is not a fast-moving surface, which is what justifies §5's 6-week interval.

**Python SDK** [S3, definitive]: the same no-total discipline applies — the returned page reaches back
to 1.23.0 (2026-02-18), and within that walked window exactly **one** release postdates 2026-07-04:
**1.31.0, published 2026-07-29**, corroborated as newest by `releases/latest` [S3]. No total is
asserted. Its notable changes include a
breaking move of payload size limits from `DataConverter` to `Client.connect` via
`PayloadLimitsConfig`, removal of the deprecated `PayloadSizeWarning`, and a breaking change
requiring custom workflow runners to pass `payload_converter_factory` rather than
`payload_converter_class` [S3, definitive]. **This is already fully covered by
[`python_sdk_long_activities.md`](python_sdk_long_activities.md), which is version-anchored to
1.31.0** — recorded here only so the vendor-cadence picture is complete.

**Temporal CLI** [S4, definitive]: latest is **v1.8.2, published 2026-07-31**, whose stated change is
a backport of GCP Cloud Run scaling options. Note this is **ahead of** the v1.7.x line referenced by
the server v1.31.2 admin-tools note [S2], and ahead of the v1.6.0+ floor Workflow Pause requires
[S15].

### 6.2 Serverless Workers documentation exists at TWO paths

**A correction to an earlier draft of this paper, stated plainly because it made a false claim about
a sibling.** That draft asserted `dedicated_edge_routing.md` cites Serverless Workers at
`docs/production-deployment/serverless-workers/index.mdx`, that the path now 404s, and that a
documentation restructure had therefore rotted the sibling's citation. **All three are wrong.** The
sibling's [S8], read directly from its citation list at line 1018, is
`docs/encyclopedia/workers/serverless-workers/index.mdx` — **a different path, which is live**. The
404 was on a path this paper constructed and never verified against the sibling.
**`dedicated_edge_routing.md` needs no correction on this point.**

**The real finding, verified at both locations: two copies of this content exist.**

| Path | Contents |
|---|---|
| `docs/encyclopedia/workers/serverless-workers/` — the sibling's citation [S38] | 3 entries: `aws-lambda.mdx`, `cloud-run.mdx`, `index.mdx` |
| `docs/production-deployment/worker-deployments/serverless-workers/` [S25] | 3 entries: `aws-lambda/`, `cloud-run/`, `index.mdx` |

Both counts reached by enumerating the contents listing and counting the enumeration [S25, S38,
definitive]. `docs/production-deployment` itself enumerates to six entries — `data-encryption.mdx`,
`index.mdx`, `multi-tenant-patterns.mdx`, `self-hosted-guide/`, `temporal-proxy/`,
`worker-deployments/` — with no top-level `serverless-workers` directory [S32, definitive].

**Maturity is identical at both paths**, checked independently at each: AWS Lambda support is Public
Preview; GCP Cloud Run support is Pre-release with APIs that may change in backwards-incompatible
ways. The two compute providers are AWS Lambda (Temporal assumes an IAM role to invoke the function)
and GCP Cloud Run (Temporal scales a Cloud Run Worker Pool via the admin API)
[S25, S38, doc, wording-uncertified]. **`dedicated_edge_routing.md`'s negative finding — no
bare-metal or wake-on-LAN provider — still holds**, unchanged and uncontradicted.

**One provider constraint worth carrying, and it disqualifies Lambda for our shape.** The
encyclopedia copy states that on AWS Lambda an activity must finish within the invocation limit, a
maximum of 15 minutes, whereas GCP Cloud Run instances are long-lived so no per-invocation limit
applies [S38, doc, wording-uncertified]. **[derived, from S38 +
[`python_sdk_long_activities.md`](python_sdk_long_activities.md)]** This repo's `claude_cli` activity
is specified at 10–60 minutes, so **Serverless Workers on AWS Lambda cannot host it** — more than
half the target range exceeds the ceiling. Only the Cloud Run path is even shape-compatible, and
neither is bare-metal.

**[gap — genuine, and now evidenced by enumeration rather than a search-result hedge.]** Whether
Serverless Workers functions against a self-hosted service or requires Temporal Cloud is **not stated
on either index page**, checked at both [S25, S38]. Search method: fetched both `index.mdx` files and
asked each directly whether Cloud is required — neither says. Additionally, **neither directory
contains a self-hosted-setup page**: both enumerate to exactly the three entries tabled above
[S25, S38]. An earlier draft hedged this gap on a `self-hosted-setup` page seen in search results; a
search result is not a source, and the enumeration shows no such page at either location. The gap
stands, on better evidence.

### 6.3 The Anthropic question — answered as a negative finding, by enumeration

The pool's standing observation (from `durable_execution.md`, 2026-07-27) was that first-party
Claude ↔ Temporal integration lagged OpenAI and Google. **That is still true, and it can now be
stated more strongly than "not found", because the population is enumerable.**

Enumerating `temporalio/sdk-python/temporalio/contrib` via the GitHub contents API returns **eleven
entries**, counted from the enumeration [S22, definitive]: `__init__.py`, `aws/`,
`google_adk_agents/`, `google_genai/`, `langgraph/`, `langsmith/`, `openai_agents/`,
`opentelemetry/`, `pydantic.py`, `strands/`, `workflow_streams/`.

**There is no `anthropic/` and no `claude/` package.** [S22, definitive-as-a-negative — the
population was enumerated, not searched.]

What Temporal *does* ship toward Anthropic is developer-side. `docs/with-ai.mdx` covers using AI
coding tools to build Temporal applications — Claude Code, Claude Desktop, Codex, Cursor, Cline —
plus packaged Skills (a Temporal Developer Skill and a Temporal Cloud Skill) and a **Temporal
Knowledge Base MCP Server** offering access to practices compiled from documentation, educational
material, forum responses and Slack channels, authenticated via MCP OAuth with a Google or GitHub
account [S27, doc, wording-uncertified].

**[derived, from S22 + S27 + `durable_execution.md`'s 2026-07-27 finding that first-party Claude ↔
Temporal integration lagged OpenAI and Google]** The asymmetry that paper identified is intact and
now has a sharper shape:
**Temporal's Anthropic surface is a tooling relationship, not a runtime one.** It helps a human write
Temporal code inside Claude Code; it does not make a Claude agent durable. Two consequences for this
repo: (a) the `claude_cli` activity domain remains hand-rolled, exactly as
`python_sdk_long_activities.md` assumes, and no first-party shortcut has appeared to change that
design; (b) the Knowledge Base MCP Server and the Temporal Developer Skill are **directly usable by
this repo today** as authoring aids, and nothing in the pool has noted them. That is an action
candidate for the synthesis, not a design change.

### 6.4 New and newly-noticed surfaces

- **`temporalio/contrib/langgraph`** — a first-party plugin running LangGraph nodes and tasks as
  Temporal activities to give LangGraph agent workflows durable execution, retries and timeouts. Its
  module docstring declares the package experimental and cautions against production use [S23,
  definitive — raw `.py` source]. **This is the finding that most damages the old paper's thesis
  (§7).**
- **`temporalio/contrib/strands`** and **`temporalio/contrib/google_genai`** appear in the
  enumeration [S22] and are not covered anywhere in the pool.
- **`temporalio/contrib/workflow_streams`** [S22] confirms Workflow Streams has landed in the SDK,
  alongside a full encyclopedia page [S14] — a maturity step up from the Public Preview
  announcement `durable_execution.md` recorded from Replay 2026.
- **Workflow Pause** [S15] — new to the pool entirely.
- **OpenAI Agents maturity, still contradictory.** `durable_execution.md` flagged that Temporal's
  Replay blog said GA while the bundle page said Public Preview. The `sdk-python` README read today
  describes the OpenAI Agents SDK integration as being in public preview [S24, doc, wording-uncertified].
  **That is a third first-party data point, and it sides with Public Preview.** The contradiction is
  narrowing but is not resolved; treat GA as unsupported.

**[minor contradiction, flagged, not load-bearing.]** The `sdk-python` README extraction reported a
minimum of Python 3.9+ [S24, doc, wording-uncertified], whereas `python_sdk_long_activities.md` read
`requires-python = ">=3.10"` directly from `pyproject.toml` on 2026-08-03. **Trust `pyproject.toml`**
— it is raw source and it is the file that actually gates installation. Recorded so a reader who
hits the README does not think the sibling is wrong.

## §7 Is this still the right topic? — the §0 inner-loop ruling

**Ruling: RE-SCOPE, do not retire.** The header's `Topic:` and `Feeds:` lines have been rewritten
accordingly. Reasoning:

**Why the old question is dead.** *"Does Temporal supply what a durable workflow layer needs, and at
what cost in complexity?"* had two halves and both failed, differently:

1. **The supply half is a decided question.** The roadmap has chosen Temporal and the repo is porting
   workflow scripts to Python against it. A paper that keeps asking whether the chosen substrate is
   adequate is decide-then-justify — it audits a taken direction, which Research Standard §0
   explicitly distinguishes from research's job.
2. **The evidence half was taken by siblings.** The header's own stated gap — heartbeat and payload
   limits for 10–60 minute activities — was closed on 2026-08-03 by
   `python_sdk_long_activities.md`, which anchors those limits to raw server source and names
   `temporal.md` in its citations as the paper whose gap it closes. Routing and worker placement went
   to `dedicated_edge_routing.md` on 2026-08-04. Concepts went to `durable_execution.md`. **By
   2026-08-04 this paper had been hollowed out by its own pool.**

**Why it is not retirement.** §6 retires a topic whose *subject* died. Temporal did not die — it is
the substrate of a live phase. What died was the *question*. And the sweep found a real, unowned
question sitting underneath it: **nobody in the pool owns the cost and commitment of the
vendor.** No paper stated the licence. No paper priced Cloud. No paper carried the upgrade
obligation, the shard-capacity one-way door, or the workflow-side limits. **That ownership gap is
the whole justification** — it does not depend on any particular question being unanswered today.

**A correction to an earlier draft of this section, because it is exactly the trap this ruling has
to avoid.** That draft justified keeping the topic partly on the ground that the self-host-vs-Cloud
decision was "unmade, and now has a named gap blocking it." **§3.2 no longer says that** — the gap
was a false negative, it is closed, and the decision is no longer research-blocked. Had that clause
survived, a synthesis reading only §7 would have inherited the very conclusion §3.2 reversed. The
topic survives because the *ownership* is missing, not because a *blocker* is present; a paper that
justifies its existence by an open question quietly acquires an interest in that question staying
open. A retirement here would delete the only home for the vendor-cost question — and that remains
true now that the question is answerable.

**One thesis correction, which §3's rules require be stated in the body and not only in the diff.**
The old paper's closing claim was that the LangGraph / CrewAI / OpenAI-Assistants layer "handles the
flow logic of an agent, but skips almost every one of the failure modes above" and is therefore
"Prototype-grade orchestration, not production-grade." **That framing is now contradicted by
first-party evidence.** Temporal ships `temporalio/contrib/langgraph`, whose stated purpose is to run
LangGraph nodes as Temporal activities so that LangGraph agent workflows get durable execution,
retries and timeouts [S23], alongside `openai_agents`, `google_adk_agents` and `strands` [S22]. The
relationship between the agent-framework layer and the durability layer is **composition, not
substitution** — the durability layer is now a plugin you attach to the framework layer, not a
replacement for it. The careful, sourced version of the *residual* critique (LangGraph's checkpointer
persists between nodes but not inside them, and does not enforce activity-level idempotency) lives in
[`durable_execution.md`](durable_execution.md) §4 and is not re-derived here.

## §8 Test plan — what research cannot settle

1. **T1 — Self-hosted stand-up cost, measured.** Stand up server + Postgres + UI on one machine from
   the self-hosted guide [S9] and record wall-clock time to first workflow. Settles whether the
   "single binary" impression survives contact with the production shape (§5).
2. **T2 — Shard-capacity sizing.** Before any production stand-up, determine the shard count the
   fleet needs and record the reasoning. §1's one-way door [S8] makes this a decision that must be
   made deliberately once, not discovered later.
3. **T3 — Action accounting: CALIBRATION against a known billing model, not a blocker-closer.**
   *(Re-framed after §3.2's gap was corrected — the billing model and the 11 billable Action
   categories are documented [S34, S35]; what is unmeasured is our workload's Action count, which is
   an empirical quantity no amount of reading settles.)* Run one representative agent workflow
   against a Temporal Cloud trial (the advertised $1,000 credit [S26] covers it) and read the billed
   Action count out of the billing API [S30, `billing-api.mdx`]. **Instrument the heartbeat
   contribution separately** — heartbeat recording is a billable Activity Action [S35] and the
   long-activity design heartbeats continuously, so this is the line item most likely to surprise.
   Compare against a self-hosted total-cost estimate from T1 and T4.
4. **T4 — Upgrade rehearsal.** Perform one sequential minor-version server upgrade including the
   schema-migration step on a staging instance and time it [S7]. The recurring cost of self-hosting
   is this number.
5. **T5 — Retry-policy default audit.** Assert in code review or test that no activity in the repo
   inherits the unlimited-max-attempts default [S11] against a paid API.
6. **T6 — Continue-as-new versus child workflows.** For the intended parent/child agent topology,
   measure event growth and confirm the interaction §2.2 identifies — children not surviving
   continue-as-new [S12, S16] — against the actual decomposition.
7. **T7 — Workflow Pause on the self-hosted floor.** Confirm the deployed server is v1.30.0+ and that
   `frontend.WorkflowPauseEnabled` can be set, then pause and unpause a live agent run [S15]. If it
   works, it is a materially better operator control than terminate-and-restart.
8. **T8 — Adopt the developer-side tooling.** Trial the Temporal Knowledge Base MCP Server and the
   Temporal Developer Skill [S27] in this repo's Claude Code configuration. Cheap, and it is the only
   Anthropic-facing thing Temporal actually ships (§6.3).

## §9 Gaps — findings, each with its search method

1. **Temporal Cloud pricing is not in the documentation REPOSITORY — but it IS on the documentation
   SITE.** *(Corrected: an earlier draft stated the second clause as "not in first-party
   documentation," which was false.)* Established: `docs/cloud` enumerates to 24 entries with no
   `pricing.mdx`, `docs/cloud/billing-and-usage` to 4 [S30], and both `docs/cloud/pricing.mdx` and
   `docs/cloud/actions.mdx` return HTTP 404. NOT a gap: `docs.temporal.io/cloud/pricing` is a live
   first-party documentation page carrying the full model [S34]. **Residual gap: none of it is
   available in raw form**, so every pricing figure is transcribed from a rendered page and
   re-verification before a budget decision is still warranted.
2. **~~No first-party definition or enumeration of a billable "Action".~~ CLOSED — this was a FALSE
   NEGATIVE.** Recorded rather than deleted, because the failure mode is the reusable part: the
   original search method (fetch `actions-usage.mdx` [S31], find no definition) executed correctly
   but was scoped to one file in one directory, and "not at the path I tried" was written up as
   "does not exist" — then used to block a live decision. The definition is in `docs/glossary.md`,
   **a raw `.md` one directory ABOVE the `docs/cloud` tree that was enumerated** [S36]; the 11
   billable categories are on `docs.temporal.io/cloud/actions` [S35]; and
   `billing-and-usage/index.mdx` — a file that WAS fetched — points at the Actions page. **Lesson:
   a negative finding must state the boundary of its search, and a one-directory search cannot
   support a documentation-wide negative.** §3.2 now carries the sourced model and every dependent
   recommendation has been re-derived.
3. **The integration inventory is not enumerable from source.** `docs/integrations.mdx` renders a
   dynamic `<IntegrationsGrid />` component; the raw file contains the component call, not the list
   [S28]. **No count of Temporal integrations is asserted anywhere in this paper.** The `contrib`
   enumeration [S22] is an SDK-side anchor and is not the same population.
4. **Patching/versioning cost is unpriced.** `docs/encyclopedia/workflow/patching.mdx` fetched raw;
   the extraction reported it covers only `patched()` mechanics and contains no why-required
   statement, no general non-determinism consequence, and no breaking-change list (§2.3).
5. **Serverless Workers on self-hosted: undetermined — but the search method is now an enumeration,
   not a hedge.** Neither of the two `index.mdx` copies states whether Temporal Cloud is required,
   checked at both [S25, S38]. **Neither directory contains a self-hosted-setup page**: both
   enumerate to exactly three entries [S25, S38]. *(An earlier draft hedged this on a
   `self-hosted-setup` page seen in a search result — not a source, and not present at either
   location.)* The gap is real; the evidence for it is now stronger.
6. **OpenAI Agents SDK maturity remains contradictory across three first-party surfaces** — Replay
   blog (GA), bundle page (Public Preview), `sdk-python` README (public preview) [S24 + prior pool
   evidence]. Treat GA as unsupported.
7. **Fetch fidelity.** No documentation `.mdx` in this sweep was returned as a certified byte-for-byte
   dump; all were extraction fetches (§0). Every doc-derived span is paraphrase.
8. **Two claims from the prior version of this paper were REMOVED as unsourceable, not re-sourced.**
   (a) The named-companies assertion that Sourcegraph's Cody, Databricks' agent operations, Fireflies
   and Vercel's AI SDK backends all converge on this pattern — no source was present in the original
   and none was located in this sweep; adoption evidence is `production_cases.md`'s subject, not this
   paper's. (b) The figure that teams avoiding Temporal end up "reinventing 60% of it in Redis +
   Postgres + wrappers" — an unsourced quantity. Both are gone from the body. Recorded here so the
   removal is auditable rather than silent.

## §10 Citations

**First-party — raw source files (highest confidence)**

- [S1] [temporalio/temporal `LICENSE`](https://raw.githubusercontent.com/temporalio/temporal/main/LICENSE) — MIT License; Temporal Technologies Inc. 2025, Uber Technologies Inc. 2020
- [S5] [temporalio/temporal `README.md`](https://raw.githubusercontent.com/temporalio/temporal/main/README.md) — `brew install temporal`, `temporal server start-dev`, MIT link
- [S23] [`temporalio/contrib/langgraph/__init__.py`](https://raw.githubusercontent.com/temporalio/sdk-python/main/temporalio/contrib/langgraph/__init__.py) — LangGraph nodes as activities; experimental, caution against production use
- [S24] [temporalio/sdk-python `README.md`](https://raw.githubusercontent.com/temporalio/sdk-python/main/README.md) — OpenAI Agents integration described as public preview; Python-version statement (contradicts `pyproject.toml`, §6.4)
- [S36] [`docs/glossary.md`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/glossary.md) — **the `Action` entry**: fundamental pricing unit in Temporal Cloud, building block of Workflow Executions; links to `/cloud/pricing#action`. **Raw `.md`; wording uncertified per §0, substance definitive.**

**First-party — GitHub API (structured data; enumerations and counts taken from these)**

- [S2] [temporalio/temporal releases](https://api.github.com/repos/temporalio/temporal/releases?per_page=15) and [latest](https://api.github.com/repos/temporalio/temporal/releases/latest) — v1.31.2 (2026-07-08), CVE-2026-5724, `system.disableStreamingAuthorizer`; full release enumeration
- [S3] [temporalio/sdk-python releases](https://api.github.com/repos/temporalio/sdk-python/releases?per_page=15) and [latest](https://api.github.com/repos/temporalio/sdk-python/releases/latest) — 1.31.0 published 2026-07-29 and its breaking changes; `latest` corroborates it as newest
- [S4] [temporalio/cli latest release](https://api.github.com/repos/temporalio/cli/releases/latest) — v1.8.2, 2026-07-31, GCP Cloud Run scaling backport
- [S10] [contents: `docs/production-deployment/self-hosted-guide`](https://api.github.com/repos/temporalio/documentation/contents/docs/production-deployment/self-hosted-guide) — 14-file enumeration. **Method citation:** used to locate §1's and §5's self-hosting sources (`checklist`, `upgrade-server`, `deployment`, `defaults`) and to establish that the directory holds no pricing or capacity-sizing page.
- [S37] [`releases/tags/v1.31.3`](https://api.github.com/repos/temporalio/temporal/releases/tags/v1.31.3) and [`releases/tags/v1.30.7`](https://api.github.com/repos/temporalio/temporal/releases/tags/v1.30.7) — **both HTTP 404.** The tag-existence probes that establish §6.1's negative independently of any list total.
- [S38] [contents: `docs/encyclopedia/workers/serverless-workers`](https://api.github.com/repos/temporalio/documentation/contents/docs/encyclopedia/workers/serverless-workers) — 3-entry enumeration — and [its `index.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/serverless-workers/index.mdx) — **the path `dedicated_edge_routing.md` actually cites**; Lambda Public Preview / Cloud Run Pre-release; the 15-minute Lambda invocation ceiling
- [S21] [contents: `docs/design-patterns`](https://api.github.com/repos/temporalio/documentation/contents/docs/design-patterns) — 46-file enumeration
- [S22] [contents: `temporalio/contrib`](https://api.github.com/repos/temporalio/sdk-python/contents/temporalio/contrib) — 11-entry enumeration; **no `anthropic`/`claude` package**
- [S29] [contents: `docs/encyclopedia`](https://api.github.com/repos/temporalio/documentation/contents/docs/encyclopedia) — 25-entry enumeration. **Method citation:** this is how §2's primitive sources (`retry-policies`, `child-workflows`, `workflow-message-passing`, `workflow`, `workflow-execution`) were located rather than guessed at, and how `workflow-streams` and `workflow-pause` were discovered.
- [S30] [contents: `docs/cloud`](https://api.github.com/repos/temporalio/documentation/contents/docs/cloud) and [`docs/cloud/billing-and-usage`](https://api.github.com/repos/temporalio/documentation/contents/docs/cloud/billing-and-usage) — 24- and 4-entry enumerations establishing the pricing gap
- [S32] [contents: `docs/production-deployment`](https://api.github.com/repos/temporalio/documentation/contents/docs/production-deployment) — 6-entry enumeration establishing the Serverless Workers path move

**First-party — documentation `.mdx` (extraction fetches; paraphrased, never quoted — see §0)**

- [S6] [`self-hosted-guide/defaults.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/self-hosted-guide/defaults.mdx) — pending-command limits, dynamic-config overrides since v1.21
- [S7] [`self-hosted-guide/upgrade-server.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/self-hosted-guide/upgrade-server.mdx) — sequential minor upgrades, two-version compatibility window, schema tooling, ~10 min/version
- [S8] [`self-hosted-guide/checklist.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/self-hosted-guide/checklist.mdx) — shard capacity fixed at build time; operator owns infrastructure; upgrade cadence guidance
- [S9] [`self-hosted-guide/deployment.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/self-hosted-guide/deployment.mdx) — server + UI server; Cassandra/MySQL/PostgreSQL/SQLite; Elasticsearch
- [S11] [`encyclopedia/retry-policies.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/retry-policies.mdx) — activities retry by default, workflows do not; default backoff parameters
- [S12] [`encyclopedia/child-workflows/child-workflows.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/child-workflows/child-workflows.mdx) — definition; ~1,000-child guidance; event-cost note; no carry-over across continue-as-new
- [S13] [`encyclopedia/workflow-message-passing/workflow-message-passing.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workflow-message-passing/workflow-message-passing.mdx) — Signal / Query / Update semantics
- [S14] [`encyclopedia/workflow-message-passing/workflow-streams.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workflow-message-passing/workflow-streams.mdx) — durable event channel; long-polling subscribers; modest fan-out
- [S15] [`encyclopedia/workflow/workflow-pause.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workflow/workflow-pause.mdx) — pause semantics; server v1.30.0+, CLI v1.6.0+, UI v2.47.2+; Cloud invite-only pre-release
- [S16] [`encyclopedia/workflow/workflow-execution/continue-as-new.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workflow/workflow-execution/continue-as-new.mdx) — definition; the reasons it is needed; new run ID and fresh history
- [S17] [`encyclopedia/workflow/workflow-execution/limits.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workflow/workflow-execution/limits.mdx) — 51,200 events / 50 MB; 2,000 pending per class; 30 pending Nexus
- [S18] [`encyclopedia/workflow/workflow-definition.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workflow/workflow-definition.mdx) — determinism constraints; command-producing call list
- [S19] [`design-patterns/saga-pattern.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/design-patterns/saga-pattern.mdx) — compensation in reverse order; eventual consistency; no-meaningful-compensation limit
- [S20] [`design-patterns/long-running-activity.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/design-patterns/long-running-activity.mdx) — heartbeat/checkpoint/cancellation pattern; **flagged for the sibling paper, see the note below**
- [S25] [`production-deployment/worker-deployments/serverless-workers/index.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/worker-deployments/serverless-workers/index.mdx) — AWS Lambda Public Preview, GCP Cloud Run Pre-release
- [S27] [`docs/with-ai.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/with-ai.mdx) — Claude Code / Cursor / Codex authoring tools, Temporal Skills, Knowledge Base MCP Server
- [S28] [`docs/integrations.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/integrations.mdx) — dynamic `<IntegrationsGrid />`; **inventory not enumerable from source**
- [S31] [`docs/cloud/billing-and-usage/actions-usage.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/cloud/billing-and-usage/actions-usage.mdx) — exclusions tip-box; **no Action definition returned**
- [S33] [`production-deployment/index.mdx`](https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/index.mdx) — sub-page structure: Cloud guide, self-hosted guide, Worker Deployments

**First-party — rendered pages (transcription uncertified per §0; the two `docs.temporal.io` pages are documentation-grade, the marketing page is not)**

- [S34] [Temporal Cloud pricing — docs.temporal.io](https://docs.temporal.io/cloud/pricing) — **the platform-fee STRUCTURE**: greater of $100/mo or 5% of Usage Spend (Essentials), greater of $500/mo or 10% (Business); four plans including Mission Critical; Action overage ladder $50→$25; storage $0.042/GBh active, $0.00105/GBh retained
- [S35] [Temporal Cloud Actions — docs.temporal.io](https://docs.temporal.io/cloud/actions) — Actions as the primary unit of consumption-based pricing; the 11 billable categories, **including Activity heartbeat recording**
- [S26] [Temporal pricing — temporal.io (marketing)](https://temporal.io/pricing) — plan tiers (Essentials, Business, Enterprise, Mission Critical), Action overage ladder, storage rates, $1,000 trial and $6,000 startup credits. **Every overlapping figure matched against [S34], with no divergence found.** Prefer [S34] for the fee structure, which this page states in starting-at form.

**Sibling pool papers (cross-referenced, not re-derived)**

- [`durable_execution.md`](durable_execution.md) — vendor-independent concepts; engine landscape; when durability is not needed
- [`python_sdk_long_activities.md`](python_sdk_long_activities.md) — activity mechanics, heartbeats, timeouts, payload limits; **closes this paper's former UNVERIFIED gap**
- [`dedicated_edge_routing.md`](dedicated_edge_routing.md) — task queues, worker placement, Worker Deployments/Versioning
- [`claude_code_integration_surface.md`](claude_code_integration_surface.md) — the CLI surface the activity domain wraps

> **Cross-paper note for the next refresh of `python_sdk_long_activities.md`.** That paper's §8 records
> a gap: no first-party sample or documented pattern for a long/subprocess-wrapping activity, with a
> search method covering `samples-python`, the `sdk-python` README, and `docs/develop/python/activities/`.
> **`docs/design-patterns/` was not in that search method**, and it contains `long-running-activity.mdx`
> [S20], `resumable-activity.mdx` and `polling.mdx` [S21]. [S20] covers heartbeat-as-checkpoint,
> resumption from heartbeat details, cancellation delivered only on heartbeat, and the rule that
> heartbeat timeout be shorter than start-to-close. **This does not close that paper's gap — none of it
> is subprocess-specific — but it narrows the search method's claim of absence, and the sibling's
> negative finding should be re-stated against this directory at its next touch.** Surfaced here rather
> than edited into that paper, which is outside this dispatch's write boundary.
>
> **A second, cheap flag — for `dedicated_edge_routing.md`'s next touch, not a finding.** The server
> v1.31.0 release body (2026-04-29 — outside this paper's §6 diff window, which is why it gets no §6
> entry) states the Worker **Deployment APIs** are fully GA, while the newer `CreateWorkerDeployment*`
> creation APIs remain pre-release. That sibling's line 51 characterises the **CLI command's**
> experimental note — a different object, so there is no contradiction to resolve. Worth a look when
> that paper next refreshes its §4.3.
