# Carrying durable memory across nodes that come and go

```
Topic:          How do mature systems carry durable memory across nodes that come and go?
                Evaluated against the thesis: "Workers are ephemeral like containers; what
                matters is stashed on persistent storage; short-lived processes are stitched
                together by a common set of data passed on." Four facets: (1) identity across
                nodes, (2) what lives at the edge vs the centre, (3) binding-independence of
                the store, (4) reconciliation after a node returns.
Feeds:          A NOT-YET-TAKEN planning decision on whether cross-node memory persistence
                becomes its own component or a phase of the Memory Management Framework.
                Extends docs/guide/memory-model.md (single-machine Kind 1) to the multi-node
                layer. This paper is validating evidence for that decision; it does not take it.
Last validated: 2026-08-12
Revalidate:     high — 6 weeks   (mixed volatility; see the volatility note below)
Confidence:     DEFINITIVE (first-party documented, exact bytes retrieved by `curl` and quoted
                from the retrieved file): the CloudEvents `source`+`id` uniqueness contract; W3C
                Trace Context trace-id/parent-id format and uniqueness language; OpenTelemetry
                `service.namespace,service.name,service.instance.id` global-uniqueness triplet;
                Temporal's Workflow-Id/Run-Id split, Namespace scoping, Reuse and Conflict
                policies, and Event-History/sticky-cache placement; git's object-name definition
                and merge-conflict behaviour; Twelve-Factor Factor VI; Kubernetes node-unreachable
                eviction timing and StatefulSet at-most-one semantics; Home Assistant's Recorder
                defaults and its documented retained-message hazard; MQTT v5 [MQTT-3.3.1-5/-6];
                Kafka log-compaction semantics.
                DEFINITIVE (peer-reviewed): Dynamo's syntactic/semantic reconciliation split and
                vector-clock truncation cost; Shapiro et al.'s SEC definition; Imine et al.'s
                finding that existing String transformation functions are incorrect or
                over-specified; Kleppmann et al.'s statement of the one case CRDTs cannot resolve;
                Gilbert & Lynch on the safety/liveness trade-off.
                DEFINITIVE-LOCAL (read from this repo at HEAD, with file:line): `JOIN_KEY =
                "run_id"`, the bare `uuid.uuid4().hex` run id, and the local-filesystem log root.
                DERIVED (this paper's inference across cited sources, flagged inline): the
                two-layer identity finding (§4.1); the DERIVABILITY placement rule (§4.2); the
                store-adequacy test list (§4.3); the layered reconciliation reading (§4.4); and
                the central verdict that the thesis is correct about compute and wrong about
                memory (§0, §5.2).
                REDUCED (rendered page or self-stripped HTML rather than a raw text source):
                the MQTT v5 spec spans (OASIS HTML, tags stripped by this analyst — whitespace
                normalised, so presented as quotations of the retrieved bytes with that caveat)
                and the SQLite Library-of-Congress statement.
                DIRECTIONAL / UNVERIFIED: the 2026 agent-memory preprint cluster (§4.4.6) —
                arXiv preprints, not peer-reviewed, and cited as evidence that the question is
                being worked rather than as evidence of an answer.
                GAPS (stated with search method, §7): no peer-reviewed treatment found of
                reconciling conflicting REASONING (as opposed to conflicting values); Temporal's
                redelivery behaviour to a sleeping/disconnected worker (inherited, unclosed);
                no source found that decides the component-vs-phase question this paper feeds.
Critic:         not-yet-verified — 2026-08-12
```

> **Volatility note (per Research Standard §3, mixed-volatility rule).** The header takes the
> highest tier present. Most of this paper is LOW-volatility material — CAP, CRDTs, OT, Dynamo,
> git's object model, Twelve-Factor — and §4.4.1–§4.4.5, §3 and §4.2 can be skipped on a refresh
> unless a cited spec revs. The HIGH-volatility content is narrow and named: the agent-memory
> preprint cluster (§4.4.6), which is moving monthly, and the API surfaces of CloudEvents,
> OpenTelemetry and Temporal (§4.1), which rev on their own cadence. Six weeks is the top of the
> high band because the load-bearing claims are the stable ones.

---

## §0 Bottom line up front

**The thesis is right about compute and wrong about memory, and the discipline it borrows from
says so itself.**

Three findings, in order of how much they should change a later design.

1. **The property that makes edge state safe to discard is DERIVABILITY, not ephemerality.**
   Every system examined that discards worker-local state does so because that state can be
   reconstructed from the centre. Twelve-Factor permits the local filesystem as *"a brief,
   single-transaction cache"* [S9]. Temporal's worker cache exists to reduce *"the need to
   reconstruct the Workflow from its Event History"* and is dropped outright when its contents
   become suspect [S6]. In both cases the centre holds the original and the edge holds a
   derivative. **An agent's reasoning produced at an edge is not a derivative of anything — it is
   the original.** The ephemeral-worker analogy therefore licenses discarding precisely what
   `memory-model.md` §1 property 3 (*the outcome **and its reasoning***) says must never be lost
   [S24]. *(Derived from [S9][S6][S24].)*

2. **Kubernetes already draws the line the thesis needs, and draws it at identity.** For stateless
   work the control plane evicts an unreachable node's Pods after a default five-minute wait and
   reschedules them [S10] — duplication is tolerable because the work is reproducible. For a
   StatefulSet it refuses: *"StatefulSet ensures that, at any time, there is at most one Pod with
   a given identity running in a cluster"*, and a Pod on an unreachable node is **not** deleted
   automatically; the documented remedies require a human or the node's own return, because
   *"Having multiple members with the same identity can be disastrous"* [S11]. Memory has
   identity. Taken from its own home discipline, the container analogy classifies memory as the
   StatefulSet case, which is the case where the analogy stops auto-resolving and escalates.
   *(Derived from [S10][S11].)*

3. **"A common set of data passed on" presumes the data merges, and reasoning is always the one
   case that does not.** Kleppmann et al. state the limit exactly: *"The only type of change that
   a CRDT cannot automatically resolve is when multiple users concurrently update the same
   property of the same object; in this case, the CRDT keeps track of the conflicting values, and
   leaves it to be resolved by the application or the user"* [S18]. Two agents writing competing
   justifications for one decision **is** that case, by construction. Three independent
   literatures — CRDT [S18][S19], git [S8], Kubernetes [S11] — converge on the same escalation for
   it. *(Derived from [S18][S19][S8][S11].)*

**What this paper does NOT do:** it does not decide whether cross-node memory becomes its own
component or a phase of the Memory Management Framework. No source found speaks to that question,
and §5.1 says so at length rather than dressing a preference as a finding.

---

## §1 Primer — the problem this fleet actually has, stated precisely

`docs/guide/memory-model.md` [S24] defines a **Kind 1 durable record** as an *interface* with five
properties — durable, readable by humans and machines, carries outcome **and** reasoning, has a
to-do bit, retrievable by address — and documents that this fleet already ships **two bindings** of
it: three GitHub-object surfaces whose to-do bit is `open`, and two committed-markdown-table
surfaces (`direction.md`, `candidates.md`) whose to-do bit is a `status:` column (§2.4, §2.5). That
document is the frame this paper extends; its content is cited, not re-derived.

What it explicitly does not have is any answer for a second machine. This paper verified the shape
of that gap directly in the code rather than accepting it as a premise:

- **The join key is a run id, and it is declared once.** `scripts/helpers/measure/run_log.py:64`
  reads `JOIN_KEY = "run_id"` [S27] — the three run-log member event types
  (`parent_route`, `run_resources`, `convergence`) join on it.
- **The run id is a bare random UUID with no source component.**
  `scripts/workflows/temporal/scripts/run_review_pr.py:81` and
  `modules/assistant/review_pr/review_pr_workflow.py:110` both read `uuid.uuid4().hex` [S28].
- **The log root is a local filesystem path.** `run_log.py` derives its log directory from
  `__file__`, resolving to `<root>/.claude/logs` [S27].

So "which run produced this?" is answerable today because all three writers are processes on one
filesystem writing one directory. *(Definitive-local: read at HEAD, file:line given.)*

**One local fact deserves emphasis because it is the cheapest available evidence that facet 1 is
load-bearing.** `run_log.py`'s own comment at `:59-63` records that the join key's *value* was out
of conformance — `run_resources` wrote `log_file.stem` (`{model_key}-{stamp}-{nonce}`) while the
other two wrote a bare `uuid4().hex`, so, in the file's own words, *"the surface's own join key
joined nothing"* [S27]. **An identity-agreement failure has already happened here, on one machine,
between three cooperating writers in one repository.** Facet 1 is not a hypothetical import from
distributed systems; it is the failure this fleet has already paid for once, and adding a second
machine adds writers that cannot see each other's code.

---

## §2 What upstream already covers, and where this paper is a different question

Two papers in the product-level pool (`docs/standards/architecture/research/raw/`) touch adjacent
ground. Stating the boundary plainly, because the overlap is easy to overstate:

| Upstream paper | What it settles | Why this paper is not that |
|---|---|---|
| [`edge_identity_trust.md`](../../../../standards/architecture/research/raw/edge_identity_trust.md) [S25] | **Credential and trust topology** for dispatching WORK to an edge: SPIFFE trust domains and one-way federation as the closest published analogue; SPIRE node attestation; the self-hosted-Temporal finding that a Namespace is the only offered credential boundary; the pull-based Worker/Task-Queue polling model | That paper asks *how is work authorised when the worker is somebody else's machine*. This one asks *how does a fact written on one machine become the same fact on another*. Authorisation and identity-of-record are different problems: a perfectly attested edge still has no way to name what it wrote so a second node agrees |
| [`temporal.md`](../../../../standards/architecture/research/raw/temporal.md) [S26] | Temporal as a **vendor commitment** — licence, limits, orchestration primitives, self-host vs Cloud, and continue-as-new's new-run-id/fresh-history mechanics | This paper uses Temporal only as one of four **identity schemes** to compare (§4.1) and one instance of the **placement rule** (§4.2). It takes no position on the vendor decision |

**Explicitly inherited, not re-researched:** the pull-based worker model (workers poll; the trunk
dispatches work it need not itself perform) [S25], and Temporal's Namespace-as-credential-boundary
finding [S25]. **Explicitly inherited as an OPEN gap:** `edge_identity_trust.md` §9 item 11 records
that Temporal's redelivery behaviour for a Task already dispatched to a worker that then sleeps or
disconnects was *not researched and not assumed* [S25]. That gap sits directly under this paper's
facet 2 ("what happens to work in flight when the centre is unreachable") and **this paper did not
close it either** — see §7.

---

## §3 The comparative landscape, in one frame

Before the facets, the shape of the option space. Every system surveyed answers "how do nodes that
come and go share durable state?" by choosing a position on three axes, and the axes are not
independent:

| Axis | One end | Other end | Who is where |
|---|---|---|---|
| **Where uniqueness is guaranteed** | a central authority enforces it | probability / mathematics, no authority | Temporal (central, enforced) [S4] ←→ W3C trace-id and OTel instance-id (random) [S2][S3]; git (content hash) [S7] |
| **What the edge is allowed to hold** | nothing durable — pure cache | a full independent replica | Twelve-Factor / Temporal worker [S9][S6] ←→ git clone, local-first devices [S7][S18] |
| **Who resolves a conflict** | the store, mechanically | the application or a human | LWW [S17] ←→ CRDT partial + human tail [S18][S19]; git merge [S8]; k8s StatefulSet [S11] |

**The dependency that matters:** a system may only move rightward on axis 2 (a richer edge) if it
has moved rightward on axis 3 (a real conflict story). Twelve-Factor gets to say "processes are
stateless" *because* it never has to merge anything — the backing service is the single writer of
record. **A design that keeps the ephemeral-worker framing but lets the edge hold originals has
taken axis 2's right end and axis 3's left end, which is the one combination none of the surveyed
systems occupies.** *(Derived from [S9][S17][S18][S11].)*

---

## §4 The four facets

### 4.1 · Identity across nodes — how a fact gets a name two nodes agree on

This facet is load-bearing: every other facet presupposes an answer. Four schemes, first-party
sources, exact bytes retrieved.

#### 4.1.1 CloudEvents — `source` + `id`, uniqueness delegated to the producer

CloudEvents v1.0.2 makes the contract explicit in both attribute definitions. On `id`:

> *"Identifies the event. Producers MUST ensure that `source` + `id` is unique for each distinct
> event. If a duplicate event is re-sent (e.g. due to a network error) it MAY have the same `id`.
> Consumers MAY assume that Events with identical `source` and `id` are duplicates."* [S1]

Constraints: `id` is REQUIRED, MUST be a non-empty string, and *"MUST be unique within the scope of
the producer"*; `source` is REQUIRED, MUST be a non-empty URI-reference, and *"An absolute URI is
RECOMMENDED"* [S1]. The spec also anticipates the multi-writer case directly: *"A source MAY include
more than one producer. In that case the producers MUST collaborate to ensure that `source` + `id`
is unique for each distinct event."* [S1] *(Definitive. Verified identical in released tag v1.0.2
and on `main` at v1.0.3-wip, so the clause is version-stable across the 1.0.x line.)*

**Buys:** a duplicate-detection contract that costs nothing to evaluate — equality on two strings —
and a natural place to record *which node wrote this*. **Costs:** nothing validates it. The spec
says producers MUST collaborate; it supplies no mechanism, so the guarantee is exactly as good as
the operational discipline assigning `source` values. **Consequence for this fleet:** the fleet's
`run_id` [S28] is a CloudEvents `id` with no `source`. Two nodes running the same workflow produce
two UUIDs that will not collide but also cannot be attributed — nothing in the record says which
machine wrote it.

#### 4.1.2 W3C Trace Context / OpenTelemetry — probabilistic uniqueness, no authority

`trace-id` is *"the ID of the whole trace forest… represented as a 16-byte array"*; *"The value of
`trace-id` SHOULD be globally unique"*, and the recommended method to achieve that *"to a
satisfactory degree of certainty is to randomly (or pseudo-randomly) generate the `trace-id`"*
[S2]. `parent-id` is the 8-byte span identifier, *"the ID of this request as known by the caller"*
[S2]. Both have an explicit invalid value (all zeros) that vendors MUST reject [S2].

For naming a *node* rather than a *trace*, OpenTelemetry's semantic conventions are the on-point
artifact. `service.instance.id` (marked Stable) *"MUST be unique for each instance of the same
`service.namespace,service.name` pair (in other words `service.namespace,service.name,
service.instance.id` triplet MUST be globally unique)"*, with SDKs *"recommended to generate a
random Version 1 or Version 4 … UUID"*, or a UUID Version 5 derived from an inherent unique ID
*"if stability is desirable"* [S3]. The conventions also warn against inferring instance identity
from ambient facts: a Collector should not set the field *"if it can't unambiguously determine the
service instance that is generating that telemetry"* [S3]. *(Definitive.)*

**Buys:** global uniqueness with zero coordination and zero central component — the only scheme
here that works with the centre unreachable. The UUIDv5-from-a-stable-source option additionally
buys *stability across restarts*, which random UUIDs do not. **Costs:** the identifier is opaque
and carries no meaning, so it must be *propagated* on every hop; a dropped propagation silently
orphans the record, and nothing detects it. **Consequence for this fleet:** this is the closest
match to what the fleet already does (`uuid4().hex`), and the gap it exposes is the same one §4.1.1
names — the fleet has the instance half of OTel's triplet and neither of the scoping halves.

#### 4.1.3 Temporal — a two-part identity with central enforcement

Temporal splits identity across a user-chosen name and a system-generated instance:

- **Workflow Id** — *"a customizable, application-level identifier for a Workflow Execution that is
  unique to an Open Workflow Execution within a Namespace"*, and *"meant to be a business-process
  identifier, such as customer identifier or order identifier"* [S4].
- **Run Id** — *"a globally unique, platform-level identifier for a Workflow Execution"*, which
  *"uniquely identifies a Workflow Execution even if it shares a Workflow Id with other Workflow
  Executions"* [S4].
- The composite address is stated outright: *"A Workflow Execution can be uniquely identified
  across all Namespaces by its Namespace, Workflow Id, and Run Id."* [S4]

Uniqueness is **enforced by the service**: *"Temporal guarantees that there can be at most one
Workflow Execution with a given ID running at any point in time"*, and *"This uniqueness constraint
is enforced within the active Namespace"* [S4]. Reuse across closed executions is governed by a
Workflow Id Reuse Policy whose default is **Allow Duplicate** [S4]. *(All definitive.)*

**Two costs the docs state themselves, and both matter here.** First, the uniqueness check has a
*horizon*: the policies *"apply to Closed Workflow Executions that are retained within the
Namespace"*, so *"given a default Retention Period, the Temporal Service can only check the Workflow
Id … against the Closed Workflow Executions for the last 30 days"* [S4]. Uniqueness is not eternal;
it is as long as retention. Second, the Run Id is explicitly **not** a stable handle: *"The current
Run Id is mutable and can change during a Workflow Retry. You shouldn't rely on storing the current
Run Id, or using it for any logical choices"*, and the docs repeat the caution [S4]. Temporal also
warns that these identifiers are stored in plain text and visible in UI, CLI, Event History and
logs, so they must not carry sensitive data [S4].

**Consequence for this fleet:** this is the scheme whose *shape* fits a durable record best — a
stable business-meaningful name plus an immutable per-attempt id — and whose *mechanism* fits an
intermittently-connected edge worst, because the guarantee requires a reachable central service at
start time.

#### 4.1.4 Content-addressing — identity derived, not assigned

Git's glossary states the model in two sentences: an object is *"The unit of storage in Git. It is
uniquely identified by the SHA-1 of its contents. Consequently, an object cannot be changed."* An
object name is *"The unique identifier of an object … usually represented by a 40 character
hexadecimal string."* [S7] *(Definitive.)*

**Buys the one property none of the other three has: convergence.** Two nodes that independently
record byte-identical content produce byte-identical names, with no coordination, no authority and
no propagation. Duplicate detection is free and exact rather than contractual (CloudEvents) or
probabilistic (OTel). **Costs:** the name is a function of the content, so *the name changes when
the record is amended*. A content hash cannot name "the same evolving record" — which is exactly
what `memory-model.md` property 5 requires of an address across revisions [S24].

Git resolves this with a second layer: mutable **refs** pointing at immutable objects — a
repository is *"A collection of refs together with an object database containing all objects which
are reachable from the refs"* [S7].

#### 4.1.5 The comparison, and the finding that falls out of it

| Scheme | Stable/scope half | Instance half | Uniqueness guaranteed by | Works with centre unreachable? | Convergent? |
|---|---|---|---|---|---|
| **CloudEvents** [S1] | `source` (URI-ref) | `id` (producer-scoped) | producer discipline; spec mandates collaboration, supplies no mechanism | Yes (if `source` pre-assigned) | No |
| **W3C Trace Context** [S2] | *(none — trace-id is flat)* | `trace-id` / `parent-id` | randomness | Yes | No |
| **OTel resource** [S3] | `service.namespace` + `service.name` | `service.instance.id` | randomness (UUIDv4), or stable-source UUIDv5 | Yes | No |
| **Temporal** [S4] | Namespace + Workflow Id | Run Id | a central service, enforced, bounded by retention | **No** — start requires the service | No |
| **Git objects + refs** [S7] | ref (mutable) | object name (content hash) | mathematics | Yes | **Yes** |

**Derived finding — all four schemes are two-layer, and the fleet has only one of the layers.**
*(Derived from [S1][S2][S3][S4][S7]; the enumeration is the four schemes named in the dispatch plus
git, and the count is over that enumerated population of five rows, not over any claimed universe of
identity schemes.)* Every scheme examined splits identity into **a stable scope-name plus a
per-instance identifier**. They differ on two things only: who guarantees the stable half is unique,
and whether the instance half is *assigned* or *derived from content*. Only content-derivation
converges — and it pays for that by being unable to name a mutable record, which is why git needs
refs and why Temporal, arriving independently, landed on the same stable-name-plus-immutable-instance
shape.

**Consequence for this fleet, stated so a later design can start from it:** the fleet has an
instance half (`uuid4().hex`) and no scope half [S27][S28]. That is sufficient on one filesystem —
where the directory *is* the scope — and insufficient the moment a second writer exists, because a
bare instance id can be compared for equality but cannot be attributed, ordered against another
node's ids, or grouped. Nothing in this section says which scope half to adopt; it says a design
that adopts none is the one option the prior art does not offer.

---

### 4.2 · What lives at the edge and what lives at the centre

#### 4.2.1 The placement rule the container analogy actually carries

Twelve-Factor Factor VI is the canonical statement, and it is more permissive than the thesis'
paraphrase:

> *"Twelve-factor processes are stateless and share-nothing. Any data that needs to persist must be
> stored in a stateful backing service, typically a database."* [S9]

But immediately after:

> *"The memory space or filesystem of the process can be used as a brief, single-transaction cache.
> For example, downloading a large file, operating on it, and storing the results of the operation
> in the database. The twelve-factor app never assumes that anything cached in memory or on disk
> will be available on a future request or job."* [S9]

And the prohibition is specific rather than general: sticky sessions *"are a violation of
twelve-factor and should never be used or relied upon"*, with the remedy being a datastore offering
time-expiration [S9]. *(Definitive.)*

So the rule is neither "everything central" nor "everything local". **The rule is a scope bound: the
edge may hold state whose lifetime is one transaction, and may never hold state a later actor
depends on finding there.**

Temporal is the same rule at a different scale. The Event History is *"a complete and durable log of
everything that has happened in the lifecycle of a Workflow Execution"*, and recovery works because
*"if the Worker crashes, the Worker uses the Event History to replay the code and recreate the state
of the Workflow Execution to what it was immediately before the crash"* [S5]. The worker's local
state is a cache with a stated purpose — it *"improves performance by reducing the need to
reconstruct the Workflow from its Event History for every Task"* [S6] — and a stated disposal rule:
*"If a Workflow Task fails, the Worker removes that Workflow Execution from its cache (as it's now
in an unknown state)"*, and stickiness is disabled if the worker does not pick up the task within
five seconds by default [S6]. *(Definitive.)*

**Derived: the placement rule is DERIVABILITY, not location.** *(Derived from [S9][S5][S6].)*
State may live at the edge exactly when it can be reconstructed from what the centre holds — by
replay (Temporal), or by re-doing one transaction (Twelve-Factor). Both systems can be cavalier
about edge state because in both, the centre holds the original. That is the load-bearing property,
and "the worker is ephemeral" is a *consequence* of it rather than a cause.

**Consequence for this fleet — the sharpest one in this paper.** A `pr_review:` disposition block
and its authored reasoning are produced at the edge and exist nowhere else. `memory-model.md` §7.2
already enumerates fourteen authored-prose items, three of which (⚠ rows 3, 4, 11 — the per-finding
disposition reasoning, the verdict rationale, the Post-Run Reflection) have **no field anywhere**,
so a render-from-record *"drops them silently rather than degrading visibly"* [S24]. Those items
fail the derivability test outright: nothing at any centre can reconstruct them. **Applying the
ephemeral-worker rule to this fleet's records without qualification would authorise discarding
exactly the content §1 property 3 exists to protect.**

#### 4.2.2 What happens to work in flight when the centre is unreachable

The honest theoretical frame first. Gilbert & Lynch situate CAP inside *"the impossibility of
guaranteeing both safety and liveness in an unreliable distributed system"*, and note the sharper
consequence that a node cannot tell partition from delay: *"if the message delay from p1 to p2 is
sufficiently large that p2 believes the system to be partitioned, then it may return an incorrect
response, despite the lack of partitions. Thus it is even impossible to guarantee consistency when
there are no partitions, and return a bad (inconsistent) answer only when partitions occur."* [S21]
*(Definitive, peer-reviewed.)* **No amount of design removes this**; it only decides who absorbs it.

Kubernetes absorbs it by acting on a timer and accepting duplication — but only for work without
identity:

- The node controller checks each node's state every 5 seconds by default; on unreachability it
  sets the `Ready` condition to `Unknown`, and *"By default, the node controller waits 5 minutes
  between marking the node as `Unknown` and submitting the first eviction request"* [S10].
- Eviction is rate-limited (default 0.1/second), reduced or stopped when a large fraction of a zone
  is unhealthy, and — the telling case — *"when all zones are completely unhealthy … the node
  controller assumes that there is some problem with connectivity between the control plane and the
  nodes, and doesn't perform any evictions"* [S10]. The control plane distrusts its own reading when
  the reading is implausible.
- For stateful identity it declines entirely: *"A Pod is not deleted automatically when a node is
  unreachable"*, and the three listed removal paths are node-object deletion, the kubelet returning,
  or explicit force-deletion by a user — with the recommendation being the first two, and force
  deletion warned against because it *"has the potential to violate the at most one semantics"*
  [S11]. *(All definitive.)*

**Derived: mature systems answer "centre unreachable" by choosing which of duplication or loss they
prefer, and they choose per-workload by whether the work has identity.** *(Derived from
[S10][S11][S21].)* Reproducible work tolerates duplication; identity-bearing work escalates to a
human rather than guessing. **Consequence for this fleet:** a memory record is identity-bearing.
The prior art's own recommendation for that class is not an automatic resolution policy.

**Inherited open gap, not closed here.** Temporal's redelivery behaviour for a Task already
dispatched to a worker that then sleeps or disconnects is recorded as un-researched by
`edge_identity_trust.md` §9 item 11 [S25]. It is the exact question this sub-facet asks of the
substrate the fleet is committing to, and this paper did not research it either — see §7 item 2.

---

### 4.3 · Binding-independence — what a store must be, stated so a non-git binding is checkable

The purpose of this facet is a **test list**, not an argument. `memory-model.md` §1 supplies five
properties [S24]; the prior art surveyed here adds three conditions that only appear once there are
two nodes. Combined, a store is a candidate Kind 1 binding at the multi-node layer if it satisfies:

**Inherited from `memory-model.md` §1 [S24] — unchanged by multi-node:**
1. Durable beyond the process and the machine.
2. Readable by humans *and* by later automated runs.
3. Carries the outcome **and its reasoning**.
4. Has a to-do bit on the record.
5. Retrievable by address, not by replay.

**Added by the multi-node layer, each traceable to a source in this paper:**
6. **Names do not collide across writers without coordination.** Because the coordinating authority
   may be unreachable (§4.1.2, §4.1.4) [S2][S3][S7].
7. **Concurrent writes are distinguishable from sequential ones.** A store that cannot tell "B
   followed A" from "B and A were concurrent" cannot route to a resolution policy at all — this is
   what vector clocks buy Dynamo [S17].
8. **A losing write is not silently destroyed.** Required by property 3: reasoning that is
   overwritten without trace fails "carries the reasoning" at the merge boundary, the same way
   `memory-model.md` §3.2 enforces it at the deletion boundary [S24][S17].

#### 4.3.1 The concrete edge case — Home Assistant, where git may be absent

Running the test list against the three stores the dispatch names. Home Assistant's own docs are the
source for what is actually available.

**SQLite (Home Assistant's default).** *"The default, and recommended, database engine is SQLite
which does not require any configuration. The database is stored in your Home Assistant
configuration directory ('/config/') and is named `home-assistant_v2.db`"* [S12]. Longevity is
well-attested: SQLite is *"a Recommended Storage Format for datasets according to the US Library of
Congress"*, and the same page notes that as of its writing *"the only other recommended storage
formats for datasets are XML, JSON, and CSV"* [S16, rendered page — reduced confidence on wording,
substance corroborated by the LoC URLs the page cites].

| Property | Verdict for SQLite-on-device |
|---|---|
| 1 durable | Yes as a format — **but the default configuration is lossy**: HA's Recorder runs `auto_purge` nightly and `purge_keep_days` describes *"the number of history days to keep in recorder database after a purge"* [S12]. HA's docs also record that on unrecoverable disk corruption *"it will move the database aside and create a new database to keep the system online"* [S12] |
| 2 human + machine readable | **The real cost.** Machine-readable natively; human access requires a tool. `memory-model.md` property 2 wants *one* artifact for both audiences [S24] |
| 3 outcome + reasoning | No structural obstacle — a TEXT column holds prose |
| 4 to-do bit | A column. Directly analogous to the `status:` column the fleet's file binding already uses [S24] |
| 5 addressable | A primary key |
| 6 no-collision | **Not provided** — the store supplies no cross-node naming; must come from §4.1 |
| 7 concurrency visible | **Not provided** — a row update overwrites |
| 8 loser preserved | **Not provided by default** — must be built as an explicit revision table |

**MQTT retained topic.** The MQTT v5 spec is normative and blunt: *"If the RETAIN flag is set to 1
in a PUBLISH packet sent by a Client to a Server, the Server MUST replace any existing retained
message for this topic and store the Application Message [MQTT-3.3.1-5], so that it can be delivered
to future subscribers whose subscriptions match its Topic Name."* A zero-byte payload deletes:
*"any retained message with the same topic name MUST be removed and any future subscribers for the
topic will not receive a retained message [MQTT-3.3.1-6]"* [S15, OASIS HTML with tags stripped by
this analyst and whitespace normalised — reduced confidence on exact whitespace, not on substance].

**A retained topic is a register, not a log. It holds one value per topic and the broker is
contractually required to destroy the previous one.** That fails test 8 by specification and test 3
in consequence — there is no place for a reasoning trail and no trace of the overwritten write.
Home Assistant additionally documents the operational hazard first-hand: *"A disadvantage of using
retained messages is that these messages retain at the broker, even when the device or service stops
working. They are retained even after the system or broker has been restarted. Retained messages can
create ghost entities that keep coming back."* [S13] *(Definitive.)* A stale write from a returning
node resurrects, which is precisely the reconciliation failure §4.4 is about.

**Append-only log on the device.** A log passes tests 3, 7 and 8 naturally — it keeps the trail, and
ordering is intrinsic. Its weakness is test 5: an offset is a location, and finding *the right
record* means scanning, which is `memory-model.md` §6.1's distinction between an address and a
location [S24]. The instructive caveat is what happens when a log is bounded for space: Kafka's log
compaction *"ensures that Kafka will always retain at least the last known value for each message
key within the log of data for a single topic partition"* [S14] *(definitive)* — which converts the
log back into exactly the MQTT register, per key. **Compaction is LWW applied to storage.** Any
device-local log with a retention policy reintroduces the failure it was chosen to avoid, unless the
compaction key is chosen so that competing reasonings are not siblings under it.

#### 4.3.2 Is a per-edge git repo one memory with five writers, or five isolated memories?

**Neither, until a sync path is specified — and that is the finding.** *(Derived from [S7][S8].)*

Git supplies one thing no other candidate store does: **namespace-compatible identity without
coordination.** Because an object *"is uniquely identified by the SHA-1 of its contents"* [S7], five
repositories independently recording identical content already agree on the name of that content.
That satisfies test 6 for free and is a genuine, non-obvious advantage over SQLite, MQTT and a plain
log, all of which need §4.1 identity bolted on.

But identity compatibility is not integration. Git's own definition of merge makes the requirement
explicit: bringing in another branch *"from a different repository … is done by first fetching the
remote branch and then merging the result into the current branch"* [S7]. A repository is refs plus a
reachable object database [S7]; nothing in the model causes two repositories to observe each other.

So the answer is conditional and the condition is the whole question:

- **With a fetch/merge path** — five repos are one memory with five writers, and the content-address
  makes the join cheap and exact.
- **Without one** — five repos are five isolated memories that happen to use compatible names, which
  is strictly worse than five obviously-separate stores because the compatibility *looks* like
  integration.

**Facet 3 therefore does not settle independently of facet 4**, and that is a real result rather
than a hedge: a store's adequacy as a durable record is a function of the reconciliation policy
layered on it, because tests 7 and 8 are properties of the merge, not of the medium. Git is also the
only candidate here whose merge behaviour is specified rather than left to the application (§4.4.5).

---

### 4.4 · Reconciliation — what wins when a node returns

#### 4.4.1 Last-write-wins

Dynamo states plainly what LWW is *for*: it is what a store picks when it cannot understand the
data. *"If conflict resolution is done by the data store, its choices are rather limited. In such
cases, the data store can only use simple policies, such as 'last write wins' [22], to resolve
conflicting updates. On the other hand, since the application is aware of the data schema it can
decide on the conflict resolution method that is best suited for its client's experience."* [S17]
*(Definitive, peer-reviewed.)*

**Cost:** convergence is trivially guaranteed and the losing write is destroyed without trace.
Against the test list, LWW fails test 8 by definition. **Fit for reasoning-bearing writes: wrong by
construction** — it discards a justification and leaves nothing saying a justification was
discarded. It also depends on clock comparison across nodes, which is the classic edge failure.

#### 4.4.2 Vector clocks

*"Dynamo uses vector clocks in order to capture causality between different versions of the same
object. A vector clock is effectively a list of (node, counter) pairs. One vector clock is
associated with every version of every object."* Comparison yields ancestry or conflict: *"If the
counters on the first object's clock are less-than-or-equal to all of the nodes in the second clock,
then the first is an ancestor of the second and can be forgotten. Otherwise, the two changes are
considered to be in conflict and require reconciliation."* [S17] *(Definitive, peer-reviewed.)*

**Vector clocks DETECT; they do not RESOLVE.** That is not a criticism — detection is test 7, and
nothing else on this list supplies it as cleanly. The documented cost is metadata growth, and
Dynamo's own mitigation is instructive: when pairs reach a threshold *"(say 10), the oldest pair is
removed from the clock"*, and the paper concedes *"this truncation scheme can lead to inefficiencies
in reconciliation as the descendant relationships cannot be derived accurately"* [S17]. **The
detector degrades silently under exactly the conditions that produce conflicts** — many writers,
partitions — which is a caution worth carrying: a truncated clock reports "conflict" for things that
were ordered, and the reader cannot tell.

#### 4.4.3 CRDTs

Shapiro et al. define the guarantee precisely. Under **Strong Eventual Consistency**, adding to
eventual consistency a **Strong Convergence** clause — *"Correct replicas that have delivered the
same updates have equivalent state"* [S19] — a CRDT is a type meeting sufficient conditions such
that *"Replicas of any CRDT are guaranteed to converge in a self-stabilising manner, despite any
number of failures"* [S19]. The motivation is explicitly to avoid the rollback path: several EC
systems *"execute an update immediately, only to discover later that it conflicts with another, and
to roll back to resolve this conflict… in general requires a consensus to ensure that all replicas
arbitrate conflicts in the same way. To avoid this, we require a stronger condition"* [S19].
*(Definitive, peer-reviewed.)*

**The limit, stated by the local-first literature rather than inferred:** *"The only type of change
that a CRDT cannot automatically resolve is when multiple users concurrently update the same
property of the same object; in this case, the CRDT keeps track of the conflicting values, and
leaves it to be resolved by the application or the user."* [S18] *(Definitive, peer-reviewed.)*

**Costs:** the data must be modelled as a semilattice, which is a design constraint on every record
type, not a library choice. And convergence is not correctness — the merged state is *a* consistent
state, not necessarily the right one.

#### 4.4.4 Operational transformation

OT is the older answer for concurrent editing, and its documented problem is correctness. Imine et
al. verified state-of-the-art String transformation functions with an automated theorem prover and
report: *"Even on a simple String object, all existing transformation functions are incorrect or
over-specified."* They locate the cause in proof complexity — *"On a simple String object, each time
a function definition changes, you have to explore 123 different cases carefully"* — and note that
if the functions are not correct *"then these algorithms cannot ensure the consistency of shared
data."* [S20] *(Definitive as to the finding, peer-reviewed, ECSCW 2003.)*

**Fit here: poor, and for a reason beyond the correctness record.** OT is built for fine-grained
concurrent editing of a shared sequence with low latency. Cross-node agent memory is coarse-grained,
high-latency, and conflicts at the level of *records and rulings* rather than *character positions*.
OT would be paying a famously hard correctness bill for a shape of concurrency this problem does not
have. It is included here because the dispatch asked for it to be compared fairly; the fair
comparison is that it is the wrong tool, not that it is a bad idea.

#### 4.4.5 Manual merge with conflict surfacing

Git states the policy directly: non-overlapping changes are incorporated verbatim, and *"When both
sides made changes to the same area, however, Git cannot randomly pick one side over the other, and
asks you to resolve it by leaving what both sides did to that area."* [S8] *(Definitive.)*

**Cost:** latency and a human. **What it buys:** it is the only option on this list that never
produces a wrong answer silently. Note how much company it has — for the *same* case, from three
unrelated lineages:

- CRDTs leave it *"to be resolved by the application or the user"* [S18].
- Kubernetes refuses to auto-remove an identity-bearing Pod on an unreachable node, listing human
  force-deletion as the last resort and warning against it [S11].
- Dynamo pushes the case up to the application, which *"is aware of the data schema"* [S17].

#### 4.4.6 The case where the writes carry REASONING

**Derived finding.** *(Derived from [S17][S18][S19][S8][S11][S24].)* Conflicting justifications for
one decision are, in CRDT terms, *always* "multiple writers concurrently updating the same property
of the same object" [S18] — the contested property being the ruling itself. There is no
value-domain merge for "A rejected this because X" versus "B accepted this because Y": the
semilattice join that would be required is an *argument*, and no cited source claims to supply one.
Therefore no single mechanism on this list is the answer, and the prior art's shape is layered:

| Layer | Job | Mechanism the sources support | Why |
|---|---|---|---|
| Container | never lose a record | add-wins set / union semantics | Dynamo: with semantic reconciliation *"an 'add to cart' operation is never lost"* [S17]; CRDTs converge cleanly for concurrent additions to different objects [S18] |
| Detector | say which records are contested | vector clocks or a causal marker | Detection is a separate job from resolution [S17] |
| Resolver | rule on contested content | surface to a human | The convergent answer of [S18][S8][S11][S17] for exactly this case |

**Two consequences specific to this fleet, and the second is the more useful one.**

**(a) The known cost of add-wins is already this fleet's known failure.** Dynamo names it: with
merge-biased reconciliation *"deleted items can resurface"* [S17]. HA reports the same shape
operationally as retained-message *"ghost entities that keep coming back"* [S13].

**(b) This fleet's two existing file surfaces have OPPOSITE reconciliation requirements, so one
merge policy cannot serve both.** *(Derived from [S24][S17].)* Per `memory-model.md` §3.2:
`candidates.md` has **no pruning rule, by design** — *"a row is never deleted, because a rejected
candidate that disappears gets re-proposed"* [S24]. `direction.md` **rotates**: a ruled row ≥90 days
old whose reasoning is recorded in the source candidate is deleted [S24]. Under an add-wins union
merge, `candidates.md` behaves perfectly — resurfacing a row is the desired behaviour there, and
the surface's stated purpose is precisely that rejections stay visible. Under the *same* policy,
`direction.md` is corrupted: every rotated row a returning node still holds is resurrected, and
rotation stops being expressible. **A cross-node design cannot pick one merge policy for "the file
binding"** — the two members of that binding differ, and `memory-model.md` §2.5 already emphasises
that they share the five properties *and not their lifecycles* [S24]. That per-surface split is a
concrete requirement a later design can be checked against.

**The 2026 preprint cluster — flagged as directional, and as evidence the question is live.** A
targeted search (§7) surfaced recent arXiv work aimed at exactly this problem. Two are on-point and
were verified to exist and read via the arXiv API rather than a search summary:

- **StateFuse** (arXiv 2607.05844, published 2026-07-07) proposes *"a conflict-aware replicated
  memory contract built on standard OpSet/CRDT merge"* with *"immutable history, explicit conflict
  objects"* and *"projection-time resolution that cannot rewrite replicated state"*; its evaluation
  reports that *"the compared methods tie on answer accuracy, but conflict-preserving surfaces keep
  contradictions visible while collapsed surfaces do not"*, and its authors state the claim is
  *"narrow… not as a universal accuracy gain"* [S22].
- **Rashomon Memory** (arXiv 2604.03588, published 2026-04-04) targets agents that *"must often
  maintain conflicting interpretations of the same events"*, resolving at query time via Dung's
  argumentation semantics, where *"the resulting attack graph is itself an explanation: it records
  which interpretation was selected, which alternatives were considered, and on what grounds they
  were rejected"* [S23].

**Both are unreviewed preprints and neither is corroborated by a documented, versioned artifact, so
both are DIRECTIONAL at most and neither is evidence that the approach works.** What they *do*
establish, and it is worth recording: two independent 2026 groups converged on **preserve the
conflict and surface it rather than collapse it** — the same conclusion §4.4.6's derived table
reaches from the classical literature. Agreement between an unreviewed preprint and a peer-reviewed
lineage raises confidence in the *direction*, not in either preprint.

---

## §5 Honest boundary analysis

### 5.1 · The evidence does NOT decide the question this paper feeds, and saying otherwise would be the most damaging thing this paper could do

The operator has explicitly not decided whether cross-node memory persistence becomes its own
component or a phase of the Memory Management Framework. **Nothing in §4 bears on that.** Every
source here is about mechanism — how a name is assigned, where state sits, what merges. **No source
found speaks to how a team should partition work into components**, and it is not the kind of
question a spec or a distributed-systems paper answers.

The temptation this paper must actively resist: §4 produces a long list of mechanisms, and a long
list *feels* like an argument for a dedicated component. It is not. The same list is equally
consistent with a phase that adopts three of the mechanisms and defers the rest. **A paper that let
volume of findings stand in for a scoping argument would be laundering its own page count into a
recommendation.** The decision rests on facts this paper did not investigate — how much of the
Memory Management Framework's remaining phase would be displaced, whether a second machine is
actually coming and when, and the operator's own sequencing preference, which §7 of the local model
would classify as a *ruling* rather than work [S24].

### 5.2 · Where the ephemeral-worker analogy breaks, specifically

Four named breaks, each with the source that produces it:

1. **It imports an availability assumption it does not state.** "Stashed on persistent storage"
   presumes the storage is reachable. Twelve-Factor was written for datacenter processes next to
   their backing service [S9]. An edge is partition-prone by construction, and Gilbert & Lynch show
   a node cannot even distinguish partition from delay [S21]. The thesis does not say *which*
   storage or *what happens when it is gone*, and those are the questions.

2. **It holds for compute and breaks at identity.** Kubernetes applies the analogy to Deployments
   and explicitly withholds it from StatefulSets, because *"Having multiple members with the same
   identity can be disastrous"* [S11]. Memory is identity-bearing.

3. **It presumes the "common set of data" merges.** It does for values; it does not for competing
   justifications, which are the CRDT literature's one named unresolvable case [S18].

4. **It licenses discarding originals, because it mistakes ephemerality for derivability.** §4.2.1.
   This is the break with the largest blast radius for this fleet, because `memory-model.md` §7.2
   already enumerates three authored items with no field anywhere [S24].

**What survives, and it is not nothing.** The thesis is *correct* about the fleet's workers as
compute: they are already disposable, already reconstruct their context from durable records, and
already hold nothing a later actor depends on finding. The analogy is a good description of the
execution layer and a bad description of the memory layer, and the paper's value is locating that
seam rather than picking a side.

### 5.3 · Where the four facets do NOT settle cleanly

- **Facet 3 depends on facet 4** (§4.3.2). Tests 7 and 8 are properties of the merge policy, not the
  medium, so "is SQLite an adequate binding?" has no medium-only answer.
- **Facet 1 depends on whether writes are ever concurrent.** If exactly one node ever writes a given
  record — a plausible topology — LWW is adequate, facet 4 is unpaid complexity, and facet 1 reduces
  to adding a `source` field to an existing UUID. **The cost of everything in §4.4 is conditional on
  a concurrency that has not been shown to exist here.**
- **Facet 2's placement rule presumes a centre exists.** In a genuinely peer topology there is no
  centre and "derivable from the centre" is vacuous. Every source in §4.2 assumes a hub; the
  local-first literature [S18] is the one that does not, and it pays for it with the full CRDT
  apparatus.
- **The identity comparison is over five enumerated schemes, not a survey of the field.** §4.1.5's
  two-layer finding is a property of those five rows. It is offered as a pattern worth checking a
  design against, not as a law.

### 5.4 · When this whole topic is NOT needed

Mirroring the sequencing argument `edge_identity_trust.md` §7 makes about the three-tier model
[S25]: **if the second machine never writes, none of this is needed.** A topology where an edge
only *reads* memory and routes all writes through one node needs no reconciliation model, no
per-edge store evaluation, and no merge policy. Facet 1 would still want a `source` half so records
are attributable — that is cheap and independently justified by the join-key incident in §1 — and
facets 2, 3 and 4 would be unpaid complexity.

**Nothing observed in this repo today requires them.** The fleet runs on one filesystem with one
run-log directory [S27]. That is an argument about *sequencing*, and it belongs to planning.

### 5.5 · Weaknesses in this paper's own evidence

- **The classical literature is about values.** Dynamo's shopping cart, CRDT counters and sets,
  OT's character positions. Every one of them is a domain where the merged result is checkable. The
  extension to *reasoning* is this paper's inference (§4.4.6), marked derived, and it rests on a
  categorisation — that a justification is "the same property of the same object" — that no cited
  source makes in those words.
- **The only sources that address the actual question are unreviewed.** The 2026 preprints [S22][S23]
  are the closest thing to on-point prior art, and they are preprints. That is a genuine weakness of
  the evidence base, not a presentational one.
- **Two facets lean on a single vendor.** Facets 1 and 2 draw heavily on Temporal because it is the
  substrate under consideration; a reader should discount for the risk that Temporal's answers look
  more canonical here than they are in the field.
- **One source is HTML-derived.** The MQTT spans [S15] were extracted by stripping tags from
  retrieved bytes, so whitespace was normalised. The substance is normative spec text with
  requirement labels; the exact character sequence including whitespace is not certified.

---

## §6 Citations

**Sourcing method.** Every raw source below was retrieved with `curl` and read from the retrieved
file, so quoted spans are the exact characters returned (the two exceptions are marked). Default
branches were confirmed via the GitHub repository API before any raw fetch — this mattered:
`git/git` defaults to `master` and `apache/kafka-site` to `markdown`, so a guessed `main` would have
produced a 404 indistinguishable from an absent document. GitHub tree listings were enumerated as
JSON arrays and counted locally, never taken from a reported total. arXiv identifiers surfaced by
search were verified through the arXiv API before citation; search-result summaries were used only
to locate candidates and are cited nowhere.

**Source count: 28 entries — 23 external, 5 local.** Research Standard §3 sets a 10–20 floor for
medium+ topics. This paper sits above it because the dispatch bound four load-bearing facets into
one artifact; each facet drew 4–6 primary sources, and cutting to the floor would have meant leaving
one facet on one vendor's documentation. Facet 4 in particular required the peer-reviewed lineage
(Dynamo, CRDT, OT, local-first) rather than any single survey.

### Raw specifications and first-party documentation (LOW volatility unless noted)

- **[S1]** CloudEvents Specification v1.0.2, `id` and `source` attribute definitions (raw).
  https://raw.githubusercontent.com/cloudevents/spec/v1.0.2/cloudevents/spec.md — clause verified
  identical on `main` (v1.0.3-wip): https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md
- **[S2]** W3C Trace Context, HTTP request header format — `trace-id`, `parent-id` (raw).
  https://raw.githubusercontent.com/w3c/trace-context/main/spec/20-http_request_header_format.md
- **[S3]** OpenTelemetry Semantic Conventions, service attribute registry — `service.instance.id`,
  `service.name`, `service.namespace` (raw). *(MEDIUM volatility — conventions rev.)*
  https://raw.githubusercontent.com/open-telemetry/semantic-conventions/main/docs/registry/attributes/service.md
- **[S4]** Temporal documentation, *Workflow Id and Run Id* (raw). *(MEDIUM volatility.)*
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workflow/workflow-execution/workflowid-runid.mdx
- **[S5]** Temporal documentation, *Event History* (raw).
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/event-history/event-history.mdx
- **[S6]** Temporal documentation, *Sticky Execution* (raw).
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/sticky-execution.mdx
- **[S7]** Git glossary — `object`, `object name`, `repository`, `merge` (raw; default branch
  `master` confirmed via API).
  https://raw.githubusercontent.com/git/git/master/Documentation/glossary-content.adoc
- **[S8]** `git-merge` documentation, *HOW CONFLICTS ARE PRESENTED* (raw).
  https://raw.githubusercontent.com/git/git/master/Documentation/git-merge.adoc
- **[S9]** The Twelve-Factor App, Factor VI — Processes (raw).
  https://raw.githubusercontent.com/heroku/12factor/main/content/en/processes.md
- **[S10]** Kubernetes documentation, *Nodes* — node controller, unreachability, eviction rates (raw).
  https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/architecture/nodes.md
- **[S11]** Kubernetes documentation, *Force Delete StatefulSet Pods* — at-most-one semantics (raw).
  https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/tasks/run-application/force-delete-stateful-set-pod.md
- **[S12]** Home Assistant documentation, *Recorder* integration — SQLite default, `purge_keep_days`,
  `auto_purge`, corruption recovery (raw). *(MEDIUM volatility.)*
  https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/recorder.markdown
- **[S13]** Home Assistant documentation, *MQTT* integration — retained-message disadvantages,
  ghost entities, message expiry interval (raw). *(MEDIUM volatility.)*
  https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_integrations/mqtt.markdown
- **[S14]** Apache Kafka documentation (4.3), *Design* — Log Compaction (raw; default branch
  `markdown` confirmed via API).
  https://raw.githubusercontent.com/apache/kafka-site/markdown/content/en/43/design/design.md
- **[S15]** OASIS, *MQTT Version 5.0* OASIS Standard — RETAIN semantics [MQTT-3.3.1-5],
  [MQTT-3.3.1-6], [MQTT-3.3.1-7], Retain Handling [MQTT-3.3.1-9]–[MQTT-3.3.1-11].
  **REDUCED CONFIDENCE ON WORDING** — retrieved as HTML and tag-stripped by this analyst; whitespace
  normalised. https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html
- **[S16]** SQLite, *LoC Recommended Storage Format*. **REDUCED CONFIDENCE** — rendered page.
  https://www.sqlite.org/locrsf.html

### Peer-reviewed and archival research

- **[S17]** DeCandia, Hastorun, Jampani, Kakulapati, Lakshman, Pilchin, Sivasubramanian, Vosshall,
  Vogels. *Dynamo: Amazon's Highly Available Key-value Store.* SOSP 2007.
  https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf
- **[S18]** Kleppmann, Wiggins, van Hardenberg, McGranaghan. *Local-first software: You own your
  data, in spite of the cloud.* Onward! 2019. https://martin.kleppmann.com/papers/local-first.pdf
- **[S19]** Shapiro, Preguiça, Baquero, Zawirski. *Conflict-free Replicated Data Types.* SSS 2011.
  https://www.lip6.fr/Marc.Shapiro/papers/2011/CRDTs_SSS-2011.pdf
- **[S20]** Imine, Molli, Oster, Rusinowitch. *Proving Correctness of Transformation Functions in
  Real-Time Groupware.* ECSCW 2003. https://www.lri.fr/~mbl/ENS/CSCW/2013/papers/Imine-ECSCW03.pdf
- **[S21]** Gilbert, Lynch. *Perspectives on the CAP Theorem.* 2012.
  https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer2.pdf

### Preprints — DIRECTIONAL, not peer-reviewed (HIGH volatility)

- **[S22]** *StateFuse: Deterministic Conflict-Preserving Memory for Multi-Agent Systems.*
  arXiv:2607.05844, published 2026-07-07. Existence, title and date verified via the arXiv API;
  abstract quoted from the API response. https://arxiv.org/abs/2607.05844
- **[S23]** *Rashomon Memory: Towards Argumentation-Driven Retrieval for Multi-Perspective Agent
  Memory.* arXiv:2604.03588, published 2026-04-04. Verified as above.
  https://arxiv.org/abs/2604.03588

### Local — this repo and its upstream pool (read at HEAD)

- **[S24]** `docs/guide/memory-model.md` — the single-machine Kind 1 model this paper extends.
  451 lines at `origin/main` (counted via `git show origin/main:… | wc -l`).
- **[S25]** `docs/standards/architecture/research/raw/edge_identity_trust.md` — upstream, read-only.
  Edge credential/trust topology; SPIFFE Federation; pull-based worker model; §9 item 11's
  un-researched Temporal redelivery gap.
- **[S26]** `docs/standards/architecture/research/raw/temporal.md` — upstream, read-only. Temporal
  as a vendor commitment; continue-as-new run-id/history mechanics.
- **[S27]** `scripts/helpers/measure/run_log.py` — `JOIN_KEY = "run_id"` (`:64`); the member event
  set (`:58`); the join-key non-conformance note (`:59-63`); local-filesystem log root (`:211-218`).
- **[S28]** `scripts/workflows/temporal/scripts/run_review_pr.py:81` and
  `scripts/workflows/temporal/modules/assistant/review_pr/review_pr_workflow.py:110` —
  `run_id = uuid.uuid4().hex`.

---

## §7 Test plan — what research cannot settle

Research established the option space. These are the questions that need an experiment, an operator
ruling, or a source that does not appear to exist. Ordered by how much they block a later design.

1. **Does a second writer actually exist, and when?** *(Operator ruling, not research.)* Everything
   in §4.4 is conditional on concurrent writes to the same record. Settles: whether facets 3 and 4
   are load-bearing or unpaid complexity (§5.3, §5.4). **This is the cheapest question here and it
   gates the most.**

2. **What does Temporal do with a Task already dispatched to a worker that then sleeps or
   disconnects?** *(Inherited unclosed from `edge_identity_trust.md` §9 item 11 [S25]; not closed
   here.)* Method: a two-worker experiment on a self-hosted namespace — dispatch, suspend the
   worker, observe redelivery timing and whether the original resumes on return. Settles facet 2's
   "work in flight when the centre is unreachable" for the substrate actually being adopted.

3. **Is there any peer-reviewed treatment of reconciling conflicting REASONING rather than
   conflicting values?** *(Negative finding, stated with method.)* Not found via: (a) targeted
   search for CRDT/provenance/justification merge and for multi-agent memory conflict; (b) forward
   reading from the CRDT and local-first literature [S18][S19], neither of which addresses it beyond
   deferring the case to the user; (c) the Dynamo semantic-reconciliation lineage [S17], which
   locates the resolution in application code without characterising it. **What the search did
   return is a 2026 preprint cluster [S22][S23] — unreviewed.** Settles whether §4.4.6's derived
   layering has any published foundation or is this paper's construction. *Treat §4.4.6 as
   unfounded-but-corroborated until this closes.*

4. **What does the fleet's own archive say about concurrency rates?** Method: replay the run-log
   corpus and the `pr_review:` archive, counting records that would have been concurrent under a
   two-node split of the same workload. Settles whether conflicts would be rare-and-escalatable or
   common-and-needing-automation — which decides whether a human-in-the-loop resolver (§4.4.5) is
   viable or a bottleneck.

5. **Do the two file surfaces really need different merge policies, or does one generalise?**
   §4.4.6(b) derives that `candidates.md` (never delete) and `direction.md` (rotate at 90 days)
   invert under add-wins [S24]. Method: construct the concurrent-write cases by hand against both
   files' stated rules and check whether any single policy satisfies both. Settles a concrete
   requirement, and it is checkable today on one machine.

6. **What is the human cost of conflict surfacing at this fleet's volume?** Every source converges
   on escalation (§4.4.5), and none of them prices it. Method: from item 4's count, estimate
   escalations per week. Settles whether the convergent recommendation of the prior art is
   affordable here — an escalation policy that generates daily interrupts is a different proposal
   from one that generates a monthly one.

7. **Does a per-edge git binding survive contact with an actual edge?** Method: install a repo on a
   Home Assistant host and measure — storage cost against SD-card wear (which HA's own docs flag as
   a live concern [S12]), whether a fetch/merge path can run unattended, and what happens when the
   device is reimaged. Settles §4.3.2's conditional, which research left open by construction.

8. **Component or phase?** *(Explicitly NOT a research question — §5.1.)* Recorded here so the
   handoff is complete: this is a ruling, and by the local model's own selection rule an outcome
   whose resolution is a preference rather than work is the operator's [S24].
