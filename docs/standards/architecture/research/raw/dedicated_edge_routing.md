# dedicated_edge_routing

```
Topic:          Dedicated, non-fungible edges versus the industry's central-queue role-advertisement
                model — does the claim hold up, and what does building it on Temporal actually
                require?
Feeds:          problem-statement.md § "Where we actually differ" claim #2 ("Edges are dedicated and
                non-fungible") — the claim's wording, its evidence marking, and the theory-of-a-worker
                argument underneath it. And roadmap.md § "Phase: Temporal Integration" — worker
                placement, the "machine-axis queue naming" and "topology profiles" addendum items,
                and the migration-order checkbox.
Last validated: 2026-08-04
Revalidate:     high — 6 weeks
Confidence:     DEFINITIVE on every Temporal semantic this paper's conclusions rest on — task-queue
                creation and routing, the ∞ Schedule-To-Start default and its non-retryable
                behaviour, sticky-execution scope, Worker Sessions being Go-only, Worker Deployment
                Version rollout gating, poller-liveness surfaces, and the first-party
                Worker-Specific Task Queues design pattern including its Python code and its own
                stated trade-offs. All were read as byte-for-byte file dumps from
                raw.githubusercontent.com. DEFINITIVE on bernstein's cluster and task protobuf
                surface and on its MESH claim-journal section (both byte-for-byte). DEFINITIVE on
                the Kubernetes, GitHub Actions and GitLab routing semantics quoted — with the
                caveat that the Kubernetes spans are verbatim-EQUIVALENT after Hugo-shortcode and
                emphasis normalization rather than byte-identical to the raw file (transcription
                note in §3.2). REDUCED — summarizing fetches of raw files, quoted conservatively:
                Temporal workers.mdx (Worker Identity), worker-performance.mdx (poller
                autoscaling), Kubernetes statefulset.md, Paperclip agents-runtime.md. REDUCED —
                rendered page: Slurm sbatch. **TWO OF THOSE REDUCED SOURCES ARE LOAD-BEARING and
                §6.4 says so:** Slurm is one of FOUR direct sources for the §3.4/§7
                physical-capability ruling, and Paperclip is the sole external corroboration for
                the §6.5 credential reframing. DERIVED, and the paper's own contribution:
                the narrowed verdict (§7), the capability-discovery relocation argument (§4.4), the
                credential-locality reframing (§6.5), the queue-axis conflict with the vendored
                Worker Deployment Standard (§4.1), and every cost figure in §8.
Negative:       Five findings of absence, each with its search method — no first-party Temporal
                upper bound or cost curve for task-queue count (§4.1); no wake-on-task mechanism for
                non-serverless compute (§4.2); no Worker Sessions outside the Go SDK (§4.5); no
                first-party capability-declaration surface at the Worker level (§4.4); and no
                published account of a Temporal fleet running stable one-queue-per-physical-machine
                topology with operational numbers (§6.6).
Critic:         PASS-WITH-FIXES (removed an unsupported StatefulSet quote; repointed the
                vendored-standard pre-flight citation from §8.3 to §8.2/§8.5; narrowed the
                physical-capability ruling from five families to three direct; corrected the
                load-bearing self-assessment for S20/S29) — 2026-08-04
```

> **Volatility ruling (Research Standard §3, mixed-volatility rule).** The load-bearing Temporal
> semantics in §4.1–§4.3 and §4.5 are stable encyclopedia material and would sit in the medium band
> on their own. Three parts are not: **Worker Versioning / Worker Deployments** (§4.3) is an actively
> moving surface whose CLI carries "Note: This is an experimental feature and may change in the
> future" on several subcommands [S9]; **Serverless Workers** (§4.2) is explicitly labelled Public
> Preview for AWS Lambda and Pre-release for GCP Cloud Run, with "APIs may change in
> backwards-incompatible ways" [S8]; and the two agent-orchestration comparators in §3 are live
> repositories that both pushed on the day of this sweep [S17][S18]. §3's rule is to take the
> **highest tier present**, so the header takes **high**. The interval is **6 weeks** — the top of
> §5's high band — because the claims this paper's verdict rests on come from the stable pages, not
> the moving ones.
>
> **Refresh scope:** re-verify §3 (competitor repos), §4.2 (serverless / compute providers) and §4.3
> (worker versioning) only. §4.1, §4.4, §4.5, §5 and §6 may be skipped unless Temporal ships a new
> routing primitive. **Explicit override trigger:** revalidate immediately if the Temporal Python
> SDK gains Worker Sessions, if a non-cloud compute provider appears for Serverless Workers, or if a
> second edge kind is scheduled.

---

## 0. The short answer, for a consumer who reads no further

| # | Question the dispatch asked | Answer |
|---|---|---|
| **Q1** | What does building it require? | **Less than expected on the mechanism, more than expected on the policy.** Temporal ships a first-party, named, Python-documented design pattern for exactly this — *Worker-Specific Task Queues* [S14]. There is no new primitive to build. What must be built is everything the pattern deliberately leaves to the application: the no-poller policy, the capability declaration, the fleet-liveness surface, and a decision about which Worker Deployment topology the fleet uses. §8 enumerates nine items with costs. |
| **Q2** | Is the claim true of the field? | **Nuanced, exactly as the dispatch predicted.** In *agent orchestration* the claim is confirmed, and more sharply than the problem statement states it — the nearest neighbour's protobuf has a literal `role` field, a literal `ClaimTask` RPC, a literal `StealTasks` RPC with donor/receiver nodes, and a leaderless claim journal that resolves contention by lowest content hash [S15][S16][S17]. In *infrastructure* the claim is not novel at all: dedicated, hardware-bound, non-fungible workers are the norm, in five independent families. |
| **Q3** | What does the pool model buy that we give up? | **One thing that matters and four that do not.** Load balancing, elasticity, utilisation and horizontal scaling are all irrelevant to a fixed fleet of credentialed machines. **Cross-machine failover is not irrelevant**, and the design currently gives it up for *all* work rather than only for repo-local work. That is the real cost, and it is the reason the verdict is "narrowed" rather than "holds". |

**Verdict (developed in §7): the claim holds in narrowed form.** The narrowing is in two places — the
*theory* ("role-pull assumes fungible workers distinguished by a label") is the weakest part and the
field refutes it; the *scope* ("no edge can claim another's") is too absolute for work that has no
locality requirement. **The strongest version of the claim is not about hardware at all — it is about
credentials**, and that version survives every counter-case in this paper. §6.5.

**One correction the planner needs before anything else.** The vendored Worker Deployment Standard
already fixes the queue axis at `<domain>-<env>` and makes worker→queue mapping 1:1 (§2.1, §2.2), and
§1.1 forbids a worker that registers multiple domains. **A machine axis has no slot in that scheme**,
and the three ways to add one are not equivalent. This is a live standards conflict, not a naming
preference, and it blocks the queue-naming work the roadmap already lists. §4.1.

---

## 1. Primer — what the two models actually are, and what would falsify the claim

Two ways to get work from a scheduler to a machine:

**Pull-from-pool (claim-and-contend).** Work is placed on a shared queue, described by attributes.
Workers advertise what they are and pull what they can handle. Contention between workers claiming
the same item is a real condition and needs an arbiter — a lock, a lease, a compare-and-swap, or a
consensus rule. Idle capacity migrates to where the work is; work does not have to know where it will
run.

**Push-to-address (dedicated routing).** Work is addressed to a destination at enqueue time. The
destination polls only its own address. There is no contention because there is nothing to contend
for, and no advertisement at claim time because the claim is not a decision.

The problem statement asserts the second, absolutely: *"each edge is dedicated, sees only its own
work, and no edge can claim another's."*

**What would falsify it, stated up front so §3 and §6 can be judged against it:**

1. If claim-and-contend is *not* the common model in the comparable systems, the "we invert it" framing is wrong.
2. If dedicated routing is ubiquitous elsewhere, the claim is true but not differentiating.
3. If removing role-pull does not actually remove capability advertisement — only relocates it — the theory underneath the claim is wrong even where the mechanism is right.
4. If the durable substrate cannot express dedicated routing without a fallback path, the absolute form is unbuildable as stated.

**All four are tested below. Two of them fire.** (2) fires in infrastructure and not in agent
orchestration; (3) fires outright and is this paper's central finding. (1) does not fire — the
characterisation is accurate. (4) half-fires: the substrate expresses it natively, but its own
documented pattern retains a shared queue alongside the dedicated ones.

Adjacent pool papers: [`durable_execution.md`](durable_execution.md) establishes the substrate's
guarantees; [`backbone_edge_generality.md`](backbone_edge_generality.md) covers the edge-kind axis
this paper's machine axis is orthogonal to; [`python_sdk_long_activities.md`](python_sdk_long_activities.md)
covers the long-activity constraint on the same workers.

---

## 2. The specific model: what Temporal actually offers for this

### 2.1 Task queues are free to create, and routing to a specific process is a documented use

Every load-bearing sentence here was read as a byte-for-byte file dump.

> "Task Queues are lightweight components that don't require explicit registration.
> They're created on demand when a Workflow Execution, Activity, or Nexus Operation is invoked,
> and/or when a Worker Process subscribes to start polling." [S1]

> "A Temporal Application can use, and the Temporal Service can maintain, an unlimited number of Task
> Queues." [S1]

> "Task Queues enable [Task Routing](/task-routing), which is the routing of specific Tasks to
> specific Worker Processes or even a specific process." [S1]

And the per-process case is called out by name:

> "Some Activities load large datasets and cache them in the process.
> The Activities that rely on those datasets should be routed to the same process.
>
> In this case, a unique Task Queue would exist for each Worker Process involved." [S2]

> "In some use cases, such as file processing or machine learning model training, an Activity Task
> must be routed to a specific Worker Process or Worker Entity." [S2]

*(Confidence: **definitive**. [S1] and [S2] were both returned as complete file dumps.)*

### 2.2 There is a first-party design pattern for it, with Python code

`docs/design-patterns/worker-specific-taskqueue.mdx` [S14] is the single most decision-relevant source
in this paper. Its own description line:

> "Routes Activities to specific Workers using unique Task Queues for Worker affinity and
> host-specific processing." [S14]

Its solution, stated in full because the shape matters:

> "You use a two-tier Task Queue architecture: a default shared Task Queue for initial Activities,
> and dynamically-named host-specific Task Queues for Activities that must run on the same Worker.
> The first Activity returns its host-specific Task Queue name, and subsequent Activities use that
> queue." [S14]

The Python worker setup, verbatim from the same file, settles a question the design would otherwise
have to test — **one process can host multiple Workers on multiple queues:**

```python
    default_worker = Worker(
        client,
        task_queue=default_task_queue,
        workflows=[FileProcessingWorkflow],
        activities=[download, process, upload],
    )
    host_worker = Worker(
        client,
        task_queue=host_task_queue,
        activities=[download, process, upload],
    )

    await asyncio.gather(default_worker.run(), host_worker.run())
```

*(Confidence: **definitive** — byte-for-byte from [S14]. This removes a cost item: N queues per
machine do not require N OS processes.)*

**Two details in this pattern cut against a naive port, and both are load-bearing.**

First, **the queue name in the sample is ephemeral, not stable:**

```python
    host_task_queue = f"FileProcessing-{socket.gethostname()}-{uuid.uuid4()}"
```

and the best-practice line is "Use unique queue names. Use hostname, IP, or UUID to ensure unique Task
Queue names." [S14] That is correct for *session* affinity, where the queue must die with the process.
It is **wrong for this design**, where the queue means "this machine's work" and must survive a
restart. A UUID in the queue name means every worker restart orphans whatever was queued. *(DERIVED
from [S14] + [S1]'s persistence semantics; see §4.1 item 7.)*

Second, **the pattern keeps the shared queue.** It is explicitly two-tier: unpinned work goes to a
default queue that any worker may take; only the affinity-requiring legs are pinned. Temporal's own
answer to "route to a specific host" is *not* "eliminate the pool."

### 2.3 Sticky Execution is not this, and must not be mistaken for it

Sticky Execution looks like pinning and is not. From the complete file:

> "Sticky Execution is the default behavior of the Temporal Platform and only applies to Workflow
> Tasks.
> Since Event History is associated with a Workflow, the concept of Sticky Execution is not relevant
> to Activity Tasks." [S5]

> "If the Worker fails to start a Workflow Task in the Sticky Queue shortly after it's scheduled
> (within five seconds by default), the Temporal Service disables stickiness for that Workflow
> Execution.
> When stickiness is disabled, the Temporal Service reschedules the Workflow Task in the original
> queue, allowing any Worker to pick it up and continue the Workflow Execution." [S5]

*(Confidence: **definitive**.)* It is an in-memory workflow-state cache whose *stickiness* is
abandoned if the worker does not start the task within five seconds — the five seconds is the sticky
schedule-to-start window, not the cache's lifetime — and it **falls back to the shared queue by
design**. It is the opposite of a non-fungibility mechanism. Any plan that cites sticky queues as
evidence Temporal supports dedicated edges is citing the wrong thing.

### 2.4 Worker Sessions are the right shape and are unavailable to us

> ":::tip
>
> This feature is currently available only in the Go SDK.
>
> :::" [S11]

*(Confidence: **definitive** — byte-for-byte from the Go Sessions page. Corroborated structurally: a
contents-API listing of `docs/develop/python/workers` returns four entries and `docs/develop/java/workers`
three, neither including a sessions page; `docs/develop/go/workers` includes `sessions.mdx` [S28].)*

The roadmap has decided Python and recorded that decision as closed. **Sessions are therefore off the
table, and that is fine** — §2.2's explicit-queue pattern is documented in Python and is what this
design wants anyway, since sessions bind to *whichever worker took the first activity*, not to a
named machine.

---

## 3. The comparative landscape — is claim-and-contend really the norm?

### 3.1 Agent orchestration: the claim is confirmed, and understated

The nearest neighbour is `bernstein` (Apache-2.0, 788 stars, pushed 2026-08-04) [S17]. Its wire
contract is a raw protobuf file, so this is as first-party as evidence gets.

From `proto/bernstein/v1/tasks.proto` [S15], byte-for-byte:

```proto
service TaskService {
  rpc CreateTask(CreateTaskRequest) returns (TaskResponse);
  rpc ClaimTask(ClaimTaskRequest) returns (TaskResponse);
```

```proto
enum TaskStatus {
  TASK_STATUS_UNSPECIFIED = 0;
  TASK_STATUS_OPEN = 1;
  TASK_STATUS_CLAIMED = 2;
```

```proto
message Task {
  string id = 1;
  string goal = 2;
  string role = 3;
  TaskStatus status = 4;
  string assigned_agent = 5;
  string assigned_node = 6;
```

From `proto/bernstein/v1/cluster.proto` [S16], byte-for-byte — note the file's own comment:

```proto
// Cluster-internal node management and task stealing.
// Replaces HTTP heartbeats and node registration with low-latency gRPC.
service ClusterService {
  rpc RegisterNode(RegisterNodeRequest) returns (RegisterNodeResponse);
```

```proto
  rpc StealTasks(StealTasksRequest) returns (StealTasksResponse);
```

```proto
message StealAction {
  string donor_node_id = 1;
  string receiver_node_id = 2;
  repeated string task_ids = 3;
}
```

```proto
message NodeCapacity {
  int32 max_agents = 1;
  int32 available_slots = 2;
  int32 active_agents = 3;
  bool gpu_available = 4;
  repeated string supported_models = 5;
}
```

And the leaderless topology's arbitration rule, byte-for-byte from the MESH section [S19]:

> "The arbiter is a **signed, append-only, Merkle-chained claim journal**."

> "1. A node appends a signed `claim` receipt for `(tracker, ticket_id, role)`.
> 2. It reconciles: any key with more than one live claim gets a `supersede`
> receipt naming the winner.
> 3. The winner is the claim with the **lexicographically lowest `entry_hash`**."

> "**Leases.** A hold whose `claim_lease_ttl_s` has elapsed can be retired by
> *any* node observing it - there is no central sweep."

*(Confidence: **definitive** on all of the above — protobuf files and the MESH section were returned
as complete dumps.)*

**Reading.** The problem statement's characterisation is not a caricature; it is close to a
transcription. `role` is a field on the task. Claiming is an RPC. Contention has a documented
tie-break rule. Cross-node work-stealing is an RPC with named donor and receiver. And a lease that
lapses can be retired by *any* observer — which is the force-claim condition the problem statement
names, in the neighbour's own words.

**The honest counterweight, and it matters.** bernstein *also* carries `Task.assigned_node`,
`ListTasksRequest.node_filter`, `StreamTasksRequest.node_filter`, `NodeInfo.labels`, `cell_ids`, and
`CordonNode` / `DrainNode` [S15][S16]. **bernstein can pin work to a node.** The difference between
the two systems is not capability; it is *which mode is the default and which is the exception*.
Stating the difference as "not a smaller version of the same design" overstates it at the mechanism
level. It is defensible at the *default* level, and that is a smaller but still real claim.

Paperclip (MIT, ~75,600 stars as fetched 2026-08-04 — a live counter that moves hourly; a critic
re-fetch the same day read 75,612, and nothing here depends on the exact figure, only the order of
magnitude — pushed 2026-08-04) [S18] is the volume comparator. Its agent-runtime
doc concedes the same locality that drives this design, from the other direction:

> "For local CLI adapters (`claude_local`, `codex_local`, `opencode_local`, `hermes_local`,
> `droid_local`), Paperclip assumes the CLI is already installed and authenticated on the host
> machine." [S20]

> "Local CLI adapters run unsandboxed on the host machine." [S20]

*(Confidence: **reduced** — this came from a summarizing fetch of a raw `.md`; the spans are short and
specific but were not certified byte-for-byte. **Nothing in this section's comparison rests on them —
but they ARE load-bearing in §6.5**, where [S20] is the sole external corroboration for the
credential-locality reframing that §7 recommends. An earlier draft claimed nothing in the paper's
verdict rested on them; corrected at critic round 1, see §6.4.)*

### 3.2 Infrastructure: dedicated, hardware-bound workers are completely ordinary

Five independent families, all first-party, four of them raw.

**Kubernetes — three separate mechanisms, escalating in strength.**

> "You can constrain a Pod so that it is _restricted_ to run on particular node(s)." [S21]

> "`nodeSelector` is the simplest way to constrain Pods to nodes with specific labels." [S21]

> "`nodeName` is a more direct form of node selection than affinity or `nodeSelector`."
> "If the `nodeName` field is not empty, the scheduler ignores the Pod and the kubelet on the named
> node tries to place the Pod on that node." [S21]

> "_Taints_ are the opposite -- they allow a node to repel a set of pods." [S22]

> "If you want to dedicate a set of nodes for exclusive use by a particular set of users, you can add
> a taint to those nodes (say, `kubectl taint nodes nodename dedicated=groupName:NoSchedule`)" [S22]

> "A _DaemonSet_ ensures that all (or some) Nodes run a copy of a Pod." [S23]

*(Confidence: **definitive** on all Kubernetes quotations except the StatefulSet one below.
**Transcription note, added at critic round 1 — read this before diffing raw bytes.** The Kubernetes
docs source is Hugo markdown containing shortcodes and emphasis markers that the fetch resolved. The
first [S21] span appears in the source as `You can constrain a {{< glossary_tooltip text="Pod"
term_id="pod" >}} so that it is _restricted_ to run on particular {{< glossary_tooltip text="node(s)"
term_id="node" >}}`, and the two [S22] spans drop bold markers present in the source. These spans are
therefore **verbatim-equivalent after shortcode normalization, not byte-identical to the raw file**.
Meaning is unaffected and every span was confirmed present; the distinction is flagged so a
re-verifier's byte diff does not read as fabrication.)*

A DaemonSet is structurally *identical* to this design's shape: exactly one worker per node,
addressed by node, never load-balanced. And StatefulSet exists to model workloads whose instances
carry identity — the docs describe "a sticky identity for each of those Pods" [S24]. *(Confidence:
**reduced** — [S24] came from a summarizing fetch; the sticky-identity span was independently
confirmed exact, and it is the only span from this source used. **Correction, critic round 1:** an
earlier draft also attributed the phrase "not interchangeable" to [S24]. That word does not occur in
the document — two independent fetches, one an explicit word search over the full text, confirm its
absence. It is deleted rather than re-sourced, since the verified span carries the point unaided.)*

**GitHub Actions — labels route, and the no-match behaviour is the interesting part.**

> "If {% data variables.product.prodname_dotcom %} doesn't find an online and idle runner that
> matches the job's `runs-on` labels and groups, then the job will remain queued until a runner comes
> online." [S25]

> "If a job is labeled for a certain type of runner, but none matching that type are available, the
> job does not immediately fail at the time of queueing." [S25]

and the bound:

> "A job can be in the queue for 24 hours before it is automatically cancelled." [S26]

**GitLab — same shape, same failure mode, named "stuck".**

> "For a runner to be selected to run a job, it must have all of the tags defined in the job script
> block." [S27]

> "The runner is configured to run only tagged jobs and has the `docker` tag. A job that has a
> `hello` tag is executed and stuck." [S27]

**Slurm — HPC has done this for decades.**

> "-w, --nodelist=<node_name_list> … Request a specific list of nodes. The job will contain as many of
> these nodes as possible based on the resource requirements, delaying execution as needed to wait
> for resources to become available." [S29]

> "-C, --constraint=<list> … Nodes can have features assigned to them by the Slurm administrator.
> Users can specify which of these features are required by their job using the constraint option."
> [S29]

*(Confidence: **reduced** — rendered page, quoted conservatively.)*

**Temporal itself** — §2.1 and §2.2 above, plus a design pattern named for it [S14] and a sibling
guide it references for "dedicated GPU, high-memory, and CPU Worker pools by resource requirement"
[S14].

### 3.3 The derived finding: the differentiator is real but it is not the mechanism

**DERIVED, from [S14][S15][S16][S19][S21][S22][S23][S25][S27][S29].**

| Domain | Is dedicated hardware-bound routing normal? | Evidence |
|---|---|---|
| Container orchestration | **Yes — three built-in mechanisms** | nodeSelector, nodeName, taints; DaemonSet is one-per-node by construction [S21][S22][S23] |
| CI / build | **Yes — it is the entire runner model** | `runs-on` labels [S25]; GitLab tags [S27] |
| HPC batch | **Yes, for thirty years** | `--nodelist`, `--constraint` [S29] |
| Durable execution | **Yes — a named first-party pattern** | Worker-Specific Task Queues [S14] |
| **Agent orchestration** | **No — the default is claim-from-pool with stealing** | `role`, `ClaimTask`, `StealTasks`, claim journal [S15][S16][S19] |

**So the claim narrows and survives:** *dedicated, non-fungible, machine-bound workers are ordinary
in infrastructure scheduling and unusual in agent orchestration, where the shipping systems default
to a shared pool with roles, claims, contention arbitration and cross-node stealing.* That sentence
is true, checkable, and considerably more useful than the broad version — because it tells a reader
where to look for prior art (Kubernetes and Slurm, not the agent field) and it stops a reviewer with
an infrastructure background from dismissing the whole claim in one sentence.

### 3.4 The part of the theory the field refutes

The problem statement's argument is: *"Role-pull assumes fungible workers distinguished by a label.
An edge is a machine with a physical capability and its own credential; a robotics edge cannot take a
bioinformatics task because it* is *a different thing, not a differently-labeled one."*

**DERIVED, and this is the sharpest counter-finding in the paper.** The field does not draw that
distinction. **The evidence is graded, not uniform** — this ruling goes against this repo's own
stated position, so it is worth being exact about which sources carry it and which merely rhyme with
it.

**Carried directly — the fetched span names physical hardware (four sources, three families plus the
substrate):**

- A Kubernetes node with a GPU is addressed by a **label** (`nodeSelector`) and defended by a **taint** — and Kubernetes' own example for tainting is "a cluster where a small subset of nodes have specialized hardware (for example GPUs)" [S22]. The label is not a substitute for the physical capability; it is the *addressing scheme for* it.
- A Slurm node's physical features are exposed as **features** matched by `--constraint`: "Nodes can have features assigned to them by the Slurm administrator." [S29]
- bernstein's `NodeCapacity` carries `gpu_available` and `supported_models` [S16] — physical capability, advertised, in a claim-based system.
- Temporal's own routing page: "Some Workers might exist on GPU boxes versus non-GPU boxes. In this case, each type of box would have its own Task Queue and a Workflow can pick one to send Activity Tasks." [S2] — physical capability, addressed by queue name, which is a label.

**Carried by routing-mechanism analogy only — the fetched spans establish label/tag *selection*, not
hardware (two families):**

- GitHub Actions matches a job to a runner on `runs-on` labels and groups [S25]. The span establishes selection semantics; it does **not** name hardware, and no hardware-specific first-party span was located for it in this sweep.
- GitLab requires a runner to have "all of the tags defined in the job script block" [S27]. Same limitation.

**The ruling stands on the four direct sources.** A label is how Kubernetes, Slurm, bernstein and
Temporal itself name a physical capability; "distinguished by a label" is not the opposite of "is a
different thing," it is the standard *implementation* of "is a different thing." The two analogy
sources broaden the pattern's reach but are not load-bearing, and **the ruling does not need them** —
a reviewer who checks GitLab and finds only generic tag matching has found a weak corroborator, not a
hole in the finding. The sentence that carries the theory is the weakest sentence in claim #2, and a
reviewer with Kubernetes or HPC experience will find it first. §6.5 proposes what to say instead.

*(Correction, critic round 1: an earlier draft called this evidence "uniform" across five families
and bundled all five citations behind one sentence. Three of the five did not carry hardware. The
split above is the honest version; the verdict in §7 is unchanged.)*

---

## 4. What building it actually requires — the enumerated findings

Each finding: what it is, why it matters for the federated destination, the evidence, and the cost.

### 4.1 Per-edge task queues: cheap on the substrate, blocked on our own standard

**What it is.** One stable task queue per machine, named from configuration, polled by that machine's
worker only.

**The substrate cost is near zero.** Queues are created on demand and need no registration; the
service maintains "an unlimited number" of them [S1]. One OS process can host several Workers on
several queues via `asyncio.gather` [S14]. Poller counts autoscale — "Temporal SDKs implement support
for *Poller Autoscaling*, which dynamically adjusts the number of pollers in use to maximize
throughput for a given number of workers and the size of the task backlog" [S12] *(reduced — a
summarizing fetch)* — so a mostly-idle per-machine queue is not an expensive standing cost.

The one first-party number that constrains the shape: "Task Queues can be scaled by adding
partitions. By default each Task Queue has 4 partitions." and "Task Queues with a single partition
are almost always first-in, first-out, with rare edge case exceptions. However, using a single
partition limits you to low- and medium-throughput use cases." [S1] A per-machine queue is
low-throughput by construction, so **single-partition per-machine queues are the correct
configuration** and buy strict FIFO for free. *(DERIVED from [S1].)*

**Why it matters for the federated destination.** SkyyNet placing paid work across MDCs needs the
destination to be an addressable name. A queue name is that name, and it is the cheapest possible
one.

**⚠️ The blocking finding — the axis conflict.** The vendored Worker Deployment Standard already fixes
the queue axis, and it is the *domain* axis:

- §2.1: task queue names follow `<domain>-<env>`.
- §2.2: "A worker polls exactly one queue. A queue is polled by exactly one *kind* of worker (though there may be multiple replicas of that worker)."
- §1.1: "one worker per domain, one task queue per worker", with the anti-pattern named as "a single 'god worker' that registers every workflow across every domain".

There is no machine slot, and the three ways to add one differ materially:

| Option | Queue count (M machines, D domains) | Conflict with the vendored standard | Consequence |
|---|---|---|---|
| **(a) `<domain>-<machine>-<env>`** | D×M | Extends §2.1's pattern; §1.1 and §2.2 hold unchanged | Cleanest. D Worker objects per machine in one process [S14]. Fleet inventory (§3 of that standard) grows D×M rows. |
| **(b) `<machine>-<env>`** | M | **Breaks §1.1** — one worker per machine registers every domain, which is the named god-worker anti-pattern | Fewest queues, wrong shape. Rejected. |
| **(c) `<domain>-<env>` shared + `<domain>-<machine>-<env>` pinned** | D + D×M | Extends §2.1; matches Temporal's own two-tier pattern [S14] | Most faithful to first-party guidance, and the only option that preserves cross-machine failover for non-local work (§5). |

**Recommendation: (c), with (a) as the fallback if the shared tier is judged unnecessary.** (c) is
what Temporal documents, and §5 shows the shared tier is not decoration — it is where the failover
this design otherwise gives up comes back.

**Cost.** *DERIVED.* The decision itself: one planning session. The addendum text: hours — the file
`docs/standards/temporal/claude-dot-files-addendum.md` already exists and the roadmap already lists
"machine-axis queue naming" as its content. The propagation cost is the real one: §3's Worker
Inventory table in the vendored standard is per-queue, so D×M rows instead of D. **Order of
magnitude: a day of planning, no build.** Dependency: §4.6's workflow classification must land first,
because it decides D and which workflows are eligible for the shared tier.

**Item 7, cheap and easy to get wrong.** The queue name must come from **explicit configuration, not
from `socket.gethostname()` and never with a UUID** — [S14]'s sample uses
`f"FileProcessing-{socket.gethostname()}-{uuid.uuid4()}"`, correct for session affinity and wrong
here. A hostname change or a worker restart would silently orphan a queue that has work in it. This
is the same class the vendored standard already calls out at §2.3 ("identities are explicit, never
derived"), and Temporal states the consequence of a name mismatch directly:

> "Since Task Queues are created dynamically when they are first used, a mismatch
> between these two values does not result in an error. Instead, it will result
> in the creation of two different Task Queues. Consequently, the Worker will
> not receive any tasks from the Temporal Service and the Workflow Execution
> will not progress." [S3]

*(Confidence: **definitive**.)* A queue name is not validated by anything — a typo, a renamed host or
a regenerated UUID produces a second, empty queue and silence. **Cost: hours.**

**Negative finding.** *No first-party upper bound or cost curve for task-queue count exists.* Search
method: `docs/encyclopedia/workers/task-queues.mdx` read in full — it says "unlimited" and gives no
figure [S1]; `docs/production-deployment/self-hosted-guide` enumerated via the contents API (14
files, none about queue counts) [S28]; `docs/develop/worker-performance.mdx` searched for "number of
Task Queues" and "multiple Task Queues" — no matching sentence returned [S12]. **"Unlimited" is the
only first-party statement, and it is a statement about correctness, not about cost.** At fleet sizes
of single-digit machines this does not bind; it would need re-checking before a multi-MDC federation.

### 4.2 The offline edge: the answer is definitive, and the default is the worst option

**What it is.** A task addressed to a machine that is off, asleep, or has no running worker.

**What Temporal does, in three verbatim facts:**

> "Workflow and Activity Tasks persist in a Task Queue.
> When a Worker Process goes down, the messages remain until the Worker recovers and can process the
> Tasks." [S1]

> "**The default Schedule-To-Start Timeout is ∞ (infinity).**" [S4]

> "This timeout is non-retryable by design. It **does not** trigger any retries regardless of the
> Retry Policy, as a retry would place the Activity Task back into the same Task Queue." [S4]

*(Confidence: **definitive** — all three from complete file dumps.)*

**So: the task waits forever, by default, and the timeout that stops it does not reroute anything.**
That is the design's stated behaviour arriving as the substrate's default — which is convenient, and
also means the failure mode is silent.

**Temporal's own recommendation contradicts the absolute form of the claim, and this must be stated
plainly:**

> "If this timeout is used, we recommend setting this timeout to the maximum time a Workflow
> Execution is willing to wait for an Activity Execution in the presence of all possible Worker
> outages, and have a concrete plan in place to reroute Activity Tasks to a different Task Queue."
> [S4]

and from the design pattern:

> "**Retry the entire sequence.** Wrap the sequence in retry logic to restart on a different host if
> needed." [S14]

> "**Missing ScheduleToStartTimeout on host-specific queues.** Without this timeout, if the target
> Worker is down, the Activity waits indefinitely. Always set `ScheduleToStartTimeout` so the
> Workflow can detect unavailability and retry on a different host." [S14]

*(Confidence: **definitive**.)* First-party guidance for host-pinned queues is: set the timeout, and
have a reroute. **"No edge can claim another's" is a decision to decline that guidance.** It can be
the right decision — for repo-local work there *is* no other host — but it has to be owned as a
policy per workflow class, not inherited as a default.

**Why it matters for the federated destination.** SkyyNet places *paid* work. A silently-parked task
on a laptop that is closed is an availability failure with a customer on the other end. The federation
tier needs to know, at placement time, whether the destination is live — which is §4.4.

**How the field answers it** — three data points, all different, none of them "wait forever": GitHub
Actions cancels at 24 hours [S26]; GitLab surfaces the job as "stuck" [S27]; Kubernetes `nodeName`
against a missing node means "the Pod will not run, and in some cases may be automatically deleted"
[S21].

**We already have the machinery, and it is already binding.** The vendored Worker Deployment Standard
names this the silent dead-queue failure at §10.4, requires a live poller on a new queue before a
routing PR merges, and sanctions a `describe_task_queue` pre-flight for high-risk dispatches — the
mechanism is the verification-options table row in **§8.2** (`client.workflow_service.describe_task_queue(...)`
pre-flight, for "High-risk dispatches where a 3s post-wait is unacceptable") together with **§8.5**
("Pre-flight queue registration check (optional hardening)"). *(§8.3 is that standard's failure-mode
taxonomy and contains no mechanism; an earlier draft of this paper pointed here, corrected at critic
round 1.)*
That is not new work; it is work that must be *extended to a new axis*.

**Negative finding — no wake-on-task for our compute.** Temporal ships exactly the mechanism this
design wants: "If no Worker is available (sync match fails), the Matching Service pushes a signal to
the WCI, and the WCI triggers the configured compute provider to start a Worker." [S8] But: "Temporal
supports two compute providers" — AWS Lambda and GCP Cloud Run [S8] — with AWS Lambda in Public
Preview and Cloud Run in Pre-release [S8], and the CLI exposing only those two provider flag families
[S9]. **There is no bare-metal or Wake-on-LAN provider.** Search method: `serverless-workers/index.mdx`
read in full [S8]; `docs/cli/command-reference/worker.mdx` read in full and its
`create-version` / `update-version-compute-config` flag tables enumerated — only `--aws-lambda-*` and
`--gcp-cloud-run-*` appear [S9]. **This is a gap with a named shape**, which is more useful than a
blank: the pattern is validated by the vendor, and an equivalent for personal hardware is ours to
build or to decline.

**Cost.** *DERIVED.* Deciding the per-workflow-class policy (wait ∞ / timeout-and-alert /
timeout-and-reroute-to-shared): **one planning session**, gated on §4.6's classification. Wiring the
`describe_task_queue` pre-flight into dispatch: **~1 day**, reusing the mechanism already sanctioned
by the vendored standard's §8.2 table row and §8.5.
Building wake-on-task for personal machines: **~1 week and out of scope** — recommend explicitly
declining it and running workers always-on where the machine is always-on.

### 4.3 Worker versioning: the cost that only appears with a fleet of sometimes-offline machines

**What it is.** Rolling new worker code across M machines that do not share a release cadence.

**The relevant semantics, verbatim:**

> "Each Deployment Version consists of Workers that share the same code build and environment.
> When a Worker starts polling for Workflow and Activity Tasks, it reports its Deployment Version to
> the Temporal Server." [S6]

> "A **Pinned** Workflow is guaranteed to complete on a single Worker Deployment Version." [S6]

And the sharp one, from the CLI reference for `worker deployment set-current-version`:

> "If not all the expected Task Queues are being polled by Workers in the
> new Version the request will fail. To override this protection use
> `--ignore-missing-task-queues`. Note that this would ignore task queues
> in a deployment that are not yet discovered, leading to inconsistent task
> queue configuration." [S9]

with a second override:

> "`--allow-no-pollers` … Override protection and set version as current even if it has no pollers."
> [S9]

*(Confidence: **definitive** — both CLI reference files read as complete dumps.)*

**DERIVED — the consequence, and it is the least obvious finding in the paper.** If the fleet is
**one** Worker Deployment spanning M machines, then promoting a new build requires *every* machine's
queues to have a live poller on the new version. A travel laptop that is closed blocks the rollout,
or forces `--ignore-missing-task-queues`, which the docs themselves say leaves inconsistent
configuration. **Non-fungible edges with independent uptime and one shared Deployment is a bad
combination, and it is the combination a naive port lands in.**

**The fix follows from the theory.** *One Worker Deployment per machine.* Then each machine has its
own Current Version, rolls forward independently, and drains independently — which is exactly what
"an edge is a different thing, not a differently-labeled one" implies operationally. It also makes
`temporal worker deployment list` a fleet inventory for free [S9]. Cost: M deployment names to manage
instead of one, and M current-version pointers.

**Why it matters for the federated destination.** Under SkyyNet, edges will be operated by different
people on different schedules. A rollout model that requires fleet-wide simultaneity is a rollout
model that will be overridden, and `--ignore-missing-task-queues` will become routine. Per-machine
deployments make the fleet's version skew *visible* instead of overridden.

**Cost.** *DERIVED.* The decision: **hours**. Wiring per-machine deployment names into the worker
entrypoint and the systemd unit: **~2 days**, and it is the same edit that carries §4.1's queue name.
Note the ordering dependency: this decision must be made *before* the first worker ships, because
migrating an existing deployment's version history is not a config change.

### 4.4 Capability discovery — the sharpest unexamined consequence, and it does not disappear

**What it is.** How the backbone (and eventually SkyyNet) learns that an edge exists, is alive, and
can do a particular thing.

**Temporal answers two of those three, natively.**

*Existence and identity.* Worker Identity defaults to `${process.pid}@${os.hostname()}` and "is
visible in various contexts, such as Event History and the list of pollers on a Task Queue" [S7]
*(reduced — summarizing fetch)*. Deployment Version is reported on poll [S6] *(definitive)*.

*Liveness.* From the CLI reference, verbatim:

> "Display a list of active Workers that have recently polled a Task Queue. The
> Temporal Server records each poll request time. A `LastAccessTime` over one
> minute may indicate the Worker is at capacity or has shut down. Temporal
> Workers are removed if 5 minutes have passed since the last poll request." [S10]

plus a fleet-level query surface:

> "Get a list of workers to the specified namespace.
>
> ```
> temporal worker list --namespace YourNamespace --query 'TaskQueue="YourTaskQueue"'
> ```" [S9]

and per-queue backlog statistics — `ApproximateBacklogCount`, `ApproximateBacklogAge`,
`TasksAddRate`, `TasksDispatchRate`, `BacklogIncreaseRate` [S10]. *(Confidence: **definitive**.)*

**Temporal answers the third — capability — not at all.** And it says so structurally:

> "Worker Processes do not need to advertise themselves through DNS or any other network discovery
> mechanism." [S1]

*(Confidence: **definitive**.)* Workers pull. Nothing in the Worker API carries "what I can do"
beyond the implicit statement made by *which queue I poll*.

**Negative finding.** *No first-party Worker-level capability-declaration surface exists in Temporal.*
Search method: `encyclopedia/workers/` enumerated via the contents API (8 files + 1 dir) and
`task-queues.mdx`, `task-routing-worker-sessions.mdx`, `sticky-execution.mdx`, `worker-versioning.mdx`
read in full [S28][S1][S2][S5][S6]; the `worker` and `task-queue` CLI references read in full for any
capability or attribute flag [S9][S10]. The nearest thing is **Worker Deployment Version metadata** —
`temporal worker deployment update-version-metadata --metadata bar=1 --metadata foo=true`, retrievable
via `describe-version` [S9] — which is an arbitrary key/value bag attached to a *deployment version*,
not to a worker. Under §4.3's one-deployment-per-machine recommendation, that bag becomes a
per-machine bag, which makes it a viable home.

**DERIVED — the central argument of this paper.** Removing role-pull removes *claim-time* capability
matching. It does not remove capability advertisement; it **relocates it to placement time and moves
the reader from the worker to the planner.** Every dedicated-routing system in §3.2 has an
advertisement channel:

| System | Where capability is declared | Who reads it |
|---|---|---|
| Kubernetes | node labels; taints | the scheduler, at placement |
| GitHub Actions | runner labels | the job router, at placement |
| Slurm | node features | the scheduler, at placement |
| bernstein | `NodeCapacity{gpu_available, supported_models}` on both `RegisterNodeRequest` and `HeartbeatRequest`; `labels` on `RegisterNodeRequest` only [S16] | the assigner, at claim or steal |
| **This design** | **undecided** | **whoever enqueues — eventually SkyyNet** |

The problem statement's own consequence — *"Nothing may assume a single operator"* — is what makes
this binding. One operator with three machines can hold the topology in their head. A federation
placing paid work cannot, and **it must know before it enqueues, because after it enqueues there is
no fallback** (§4.2).

**Three options, with costs.** *DERIVED.*

| Option | What it is | Cost | Failure mode |
|---|---|---|---|
| **(a) Static topology profile** | a versioned file mapping machine → capabilities; the roadmap already names "topology profiles" | **hours** | drifts from reality silently; no liveness |
| **(b) Deployment Version metadata** | capabilities as KV on each machine's Worker Deployment Version [S9] | **~1 day** | requires §4.3's per-machine deployments; experimental surface; still operator-maintained |
| **(c) Registration workflow** | each edge runs a long-lived workflow reporting its own capabilities into queryable state | **~1 week** | self-correcting and accurate — **and it is a re-implementation of `RegisterNode`/`NodeCapacity` [S16]** |

**Recommend (a) now, (b) alongside §4.3, (c) deferred until a second MDC exists.** State (c)'s nature
honestly in the roadmap: when the federation grows, this design will re-acquire capability
advertisement. That is not a defeat — advertisement at placement time with no claim contention is a
genuinely different and better-behaved thing than claim-time contention — but a plan that assumes
advertisement was *eliminated* will be surprised.

### 4.5 Do Temporal's existing primitives match, or is the design reaching?

**They match, and this is the largest cost reduction in the paper.**

| Primitive | Matches this design? | Evidence |
|---|---|---|
| Explicit per-queue routing | **Yes — it is the mechanism** | "a unique Task Queue would exist for each Worker Process involved" [S2] |
| Worker-Specific Task Queues pattern | **Yes — named, documented, Python code** | [S14] |
| Multiple Workers in one process | **Yes** | `asyncio.gather(default_worker.run(), host_worker.run())` [S14] |
| Sticky Execution | **No — wrong mechanism** | workflow-tasks only; falls back to the shared queue after 5s [S5] |
| Worker Sessions | **Shape yes, availability no** | "currently available only in the Go SDK" [S11] |
| Automatic fallback on no-poller | **No — application's job** | "have a concrete plan in place to reroute" [S4] |
| Capability declaration | **No** | §4.4 negative finding |
| Wake a sleeping edge | **Only for AWS Lambda / GCP Cloud Run** | [S8][S9] |

**The finding the dispatch asked to be reported if true, and it is true:** *Temporal already supports
this natively, through its plainest primitive.* The mechanism is a string. There is no scheduler to
write, no plugin, no fork. **What is left to build is policy and observability, not routing.**

### 4.6 The prerequisite nobody has written down: which work is actually machine-bound?

**What it is.** A classification of every workflow into repo-local (must run where the repo and the
credential are) versus machine-independent (could run anywhere with a credential).

**Why it is a finding and not an implementation detail.** §4.1's queue axis, §4.2's no-poller policy
and §5's failover analysis all consume this table, and none of them can be decided without it. The
roadmap's own framing — "Claude Code must run on the machine holding the repo — that repo-locality
constraint drives the whole worker placement" — establishes the constraint but not its *extent*. Some
of the current fleet is plainly repo-local (a revision run in a worktree). Some plainly is not (a
`review-pr` decide-only pass, a research sweep, a CPI window analysis) — those need a credential and
a network, not a specific disk.

**Cost.** *DERIVED.* One table, **~2 hours**, produced by reading `scripts/workflows/`. It is the
cheapest item on this list and it gates three of the others.

---

## 5. What the pool model buys, and which of it this system needs

Stated fairly first, then judged. Temporal's own list of what a pool gives you: "In effect, Task
Queues enable load balancing across many Worker Processes" [S1], plus flow control and throttling
[S2]. The design-pattern page states the trade-off of pinning in the vendor's own words:

> "It is not a good fit for stateless Activities that can run anywhere, Activities that use shared
> storage (S3, databases), high-availability requirements (host failure blocks the Workflow), or
> Workflows without local state dependencies." [S14]

and its comparison table rates Worker-Specific Queues as **Availability: Lower** against shared
storage's **Higher** [S14]. *(Confidence: **definitive**.)*

| Property the pool buys | Do we need it? | Reasoning |
|---|---|---|
| **Load balancing** | **No** | For repo-local work there is no second machine that *could* run it — the repo and the credential are singular. Temporal's file-processing example is the identical argument [S14]. |
| **Elasticity / autoscaling** | **No** | Fixed hardware. The scarce resource is a subscription rate limit, not CPU. |
| **Utilisation** | **No** | Idle machines cost nothing under a flat per-person subscription — which the problem statement identifies as the enabler. |
| **Horizontal scaling** | **No** | The growth axis in the roadmap is edge *kinds*, not replicas of one edge. |
| **Simple capacity planning** | **Partially lost, cheaply recovered** | M queues means M backlogs. But `describe` already exposes `ApproximateBacklogCount`, `ApproximateBacklogAge` and `BacklogIncreaseRate` per queue [S10] — the data exists; only the dashboard is missing. **~1 day.** |
| **Failover** | **⚠️ Genuinely needed, and currently given up too broadly** | Two cases, and they differ. |

**The failover case, split properly — this is the paper's most consequential §5 finding.**

*Within a machine*, dedicated queues lose nothing: "When a Worker Process goes down, the messages
remain until the Worker recovers and can process the Tasks" [S1]. A crashed worker restarts and
resumes. Crash resilience is intact.

*Across machines*, dedicated queues lose real availability — **but only for work that did not need
locality in the first place.** A `review-pr` pass pinned to a laptop that is closed is an outage the
design inflicted on itself for no benefit. Under the roadmap's own **Autonomous Operation** phase — a
driver running unattended, choosing the next dispatch from persisted state — that outage is precisely
the condition nobody is awake to notice.

**DERIVED conclusion, from [S1] + [S4] + [S14] + §4.6.** The correct scope is not "all edges
dedicated" but **"the machine axis binds work that is machine-bound; everything else stays on a
shared queue."** That is what Temporal's two-tier pattern does [S14], it is §4.1 option (c), and it
recovers the one property in this table that is worth having. It also narrows claim #2 — see §7.

---

## 6. Honest boundary analysis

### 6.1 The case that the claim is not a differentiator at all, argued at full strength

1. **The mechanism is thirty years old.** Slurm `--nodelist` [S29], Kubernetes DaemonSet [S23], GitHub Actions labels [S25]. Nothing about routing work to a named machine is new.
2. **Temporal has a named design pattern for it**, with inline code in Python, Go, Java and TypeScript and links to a working sample repo for each of those four languages [S14]. A differentiator the vendor documents as a pattern is not a differentiator; it is a configuration.
3. **The nearest neighbour already supports it.** `Task.assigned_node`, `node_filter`, `NodeInfo.labels`, `CordonNode`, `DrainNode` [S15][S16]. The difference is a default, not a capability.
4. **The theory is refuted by the field** (§3.4, on three direct comparator families plus the substrate). Labels *are* how physical capability is expressed.
5. **The vendor rates the trade-off against us.** "Availability: Lower" [S14], and "not a good fit for … high-availability requirements (host failure blocks the Workflow)" [S14].

### 6.2 Where that case is wrong

Points 1–3 establish that the *mechanism* is ordinary. They do not touch the claim, which is about
**which mode is the only mode**. bernstein *can* pin; its default is a claim journal with contention
arbitration and cross-node stealing [S16][S19]. Paperclip *runs on the host machine* and assumes the
CLI is authenticated there [S20], yet its assignment model is central. **No surveyed agent-orchestration
system makes machine-dedication the sole routing mode.** That is a real difference, it is small, and
it is defensible — which is more than the broad version of the claim can say.

Point 5 is correct and is why §5 and §7 narrow the scope rather than defend it.

### 6.3 When this is NOT needed

**If the fleet were one always-on machine, per-edge queues buy nothing** over a single queue, and cost
a naming scheme, an inventory table, M deployments and a dashboard. The value of the design is
proportional to (a) how heterogeneous the machines are and (b) how often they are off. At the current
fleet — an Ubuntu workstation, a travel laptop, remote VMs — (a) is high and (b) is high for exactly
one of them. That is enough to justify the axis and not enough to justify building capability
discovery yet (§4.4's recommendation).

### 6.4 Where this paper is weak

- **[S7], [S12], [S24] came from summarizing fetches** of raw sources rather than byte-for-byte dumps. Their quoted spans are short and specific, they are marked reduced at every point of use, and **no conclusion in §7 or §8 rests on any of them.** [S24]'s only surviving span was independently confirmed exact; an unsupported second span was deleted at critic round 1 (§3.2).
- **⚠️ Two reduced-confidence sources ARE load-bearing, and an earlier draft said otherwise.** *(Correction, critic round 1 — this is the one place in the paper where under-reporting is worse than over-reporting, so it is stated at full strength.)*
  - **[S29] (Slurm) is a rendered page, and it is one of the four direct sources — three comparator families plus the substrate — carrying §3.4/§7's physical-capability ruling.** An earlier draft called it "a fifth corroborating family… removing it changes nothing." That was wrong: removing it drops the ruling to two comparator families plus the substrate. The ruling still stands on Kubernetes, bernstein and Temporal, but the margin is thinner than the draft implied. **The one action this warrants: if §3.4 is ever challenged, re-source Slurm's `--constraint`/features from the man-page source rather than the rendered page.**
  - **[S20] (Paperclip, summarizing fetch) is the sole external corroboration in §6.5**, which §7's proposed replacement wording draws on. An earlier draft said "nothing in this paper's verdict rests on them." That is true of the §3.1 comparison it appears in and **false of §6.5**. The credential-locality argument is primarily ours and stands on the problem statement's own economics; [S20] is what shows a 75,000-star comparator hitting the same constraint from the other side. **If the credential reframing is adopted, re-verify [S20] byte-for-byte first** — it is the only outside evidence for the paper's most consequential recommendation.
- **Every cost figure in §8 is derived, not measured.** They name their inputs (queue counts from §4.1, the existing §8.2/§8.5/§10.4 machinery from the vendored standard, file counts from the current fleet) but no comparable build has been timed here. Treat them as ordering information, not as estimates.
- **Survivorship bias in §3.2.** Every surveyed system that pins to hosts is a system that survived. Systems that pinned and were abandoned leave no docs to fetch.
- **The federation tier is a stub.** SkyyNet and SkyyCommand have not had this exercise run against them, per the problem statement's own note. §4.4's federation argument is therefore an argument about a sketch, and should be re-run when the sketch becomes a specification.

### 6.5 The reframing this paper recommends — and it is the most valuable thing here

**DERIVED, from [S20] + [S14] + [S22] + [S25] + [S29] + the problem statement's own economics section.**

The claim currently leads with **physical capability** ("a robotics edge cannot take a bioinformatics
task because it *is* a different thing"). That is the argument the field refutes (§3.4), because
labels are how the field expresses physical capability.

The claim *also* contains the argument that survives, in a subordinate clause: **"and its own
credential."**

A Claude Max subscription is bound to a person and authenticated on their machines. Another edge
cannot take that work — not because it lacks a GPU, not because it is labelled differently, but
because **it cannot authenticate as that subscriber.** No label grants it. No node affinity relaxes
it. No work-stealing RPC can move it. And Paperclip, the ~75,600-star comparator, concedes exactly this
constraint from the other side: local CLI adapters "assume the CLI is already installed and
authenticated on the host machine" [S20].

**Credential locality is a hard non-fungibility that the label model genuinely cannot express**, and
it is upstream of the problem statement's own affordability thesis — the flat-subscription economics
*require* the work to run where the subscription lives. Leading with it makes claim #2 unattackable
by the Kubernetes objection, and it ties the differentiator to the economics rather than to a hardware
analogy.

**Proposed replacement wording for claim #2 is in §7.**

### 6.6 Negative finding: nobody has published this at fleet scale

*No account of a Temporal deployment running stable, long-lived, one-queue-per-physical-machine
topology with operational numbers was located.* Search method: `docs/design-patterns` enumerated via
the contents API (57 files at the time of the sweep; a critic re-count the same day returned 61 files
and 0 directories — the directory is growing fast, which weakens nothing here since the on-topic file
is present in both) and the one directly on-topic file read in full [S14][S28];
`docs/best-practices` enumerated (10 files) [S28]; `docs/encyclopedia/workers/` enumerated and its
routing, queue, sticky and versioning pages read in full [S1][S2][S5][S6][S28];
`docs/production-deployment/worker-deployments` enumerated (6 files + 1 dir) and its index read in
full [S13][S28]. **Every first-party treatment of host-specific queues is the *ephemeral session*
case** — a queue created per process for the duration of a file-processing workflow, named with a
UUID [S14] — **not the durable per-machine case this design needs.** That is a genuine gap and it is
what §9's test plan exists to close. It is a gap, not a refutation: the semantics carry over
unchanged; what is unpublished is the operational experience.

---

## 7. Verdict on the claim, and the wording that survives

**HOLDS IN NARROWED FORM.** Three parts, ruled separately, because they do not stand or fall together.

| Part of claim #2 | Ruling |
|---|---|
| "The common model is a central queue where workers advertise a *role* and claim from a shared pool, with contention and force-claim as real conditions" | **Holds, and is understated.** `Task.role`, `rpc ClaimTask`, `TASK_STATUS_CLAIMED`, `rpc StealTasks` with donor/receiver, a claim journal resolving contention by lowest `entry_hash`, and leases retirable by any observer [S15][S16][S19]. |
| "each edge is dedicated, sees only its own work, and no edge can claim another's" | **Holds as a default; too absolute as a rule.** Temporal's own pattern is two-tier and retains a shared queue [S14]; first-party guidance for pinned queues is to have a reroute plan [S4]; and the design currently gives up cross-machine failover for work that has no locality requirement (§5). |
| "This is not a smaller version of the same design — it follows from a different theory of what a worker is. Role-pull assumes fungible workers distinguished by a label." | **Does not hold as stated** — on **three direct comparator families plus the substrate itself (four sources)**, with two more families by analogy only. Labels are how Kubernetes [S22], Slurm [S29] and Temporal itself [S2] address *physical hardware*, and bernstein advertises `gpu_available` and `supported_models` inside a claim-based system [S16]. GitHub Actions [S25] and GitLab [S27] corroborate the routing mechanism but their fetched spans establish label/tag *selection*, not hardware — see §3.4's graded split. The mechanism is ordinary. **The difference that survives is credential locality (§6.5), not physical capability.** |

**Proposed replacement wording for the problem statement's claim #2** — offered as a candidate for the
ratification pass, not written into the standard by this run, per Research Standard §7:

> **2. Edges are dedicated, and the binding non-fungibility is the credential.** The common model in
> agent orchestration is a central queue where workers advertise a role and claim from a shared pool
> — contention arbitration and cross-node work-stealing are first-class features of the nearest
> comparable system. Ours addresses work to a named edge instead: an edge polls its own queue, and
> work that is bound to a machine is never eligible to be claimed elsewhere. **The binding constraint
> is not hardware — hardware-bound routing is ordinary in Kubernetes, CI and HPC — it is the
> credential.** The work runs on a subscription that is authenticated on one person's machines, so no
> other edge can take it at any price. Work that carries no such binding stays on a shared queue and
> keeps its failover. *Evidence: the claim-and-contend model confirmed first-party in the nearest
> neighbour; the routing mechanism confirmed native to our substrate; the credential argument is
> ours and is untested at more than one operator.*

**What that wording costs and gains.** It gives up the strong "different theory of a worker" framing,
which the evidence cannot carry. It gains a differentiator no comparator can copy without giving up
metered billing, ties claim #2 to the affordability thesis the problem statement already argues, and
survives the Kubernetes objection a technical reader will raise first.

---

## 8. What `Phase: Temporal Integration` must add — the planner's list

Ordered by dependency. Every cost is **derived**; inputs named. Items 1–4 are blocking; 5–7 are
sequenced after; 8–9 are decisions to *decline* work.

| # | Item | Why it matters | Cost (derived) | Depends on |
|---|---|---|---|---|
| **1** | **Classify every workflow as repo-local or machine-independent.** A table in the phase doc. | Gates items 2, 3 and 5. Nothing about placement can be decided without it. Inputs: `scripts/workflows/` contents. | **~2 h** | — |
| **2** | **Decide the queue axis and write it into `claude-dot-files-addendum.md`.** Recommend §4.1 option (c): `<domain>-<env>` shared + `<domain>-<machine>-<env>` pinned. **Surface the conflict with the vendored Worker Deployment Standard §1.1/§2.1/§2.2 as a standards-amendment candidate** — do not edit the vendored file. | The vendored standard has no machine slot; option (b) trips its named god-worker anti-pattern. Roadmap already lists this as addendum content. | **~1 day planning, no build** | 1 |
| **3** | **Set a per-workflow-class no-poller policy.** For each class: wait ∞ / schedule-to-start timeout + alert / timeout + reroute to the shared tier. Then wire the sanctioned `describe_task_queue` pre-flight into dispatch. | Default is ∞ and the timeout does not reroute [S4]. Vendored §10.4 already names this the silent dead-queue failure and gates it; this extends the gate to the machine axis. | **~1 day** (policy) **+ ~1 day** (pre-flight, reusing the §8.2 table row / §8.5 mechanism) | 1 |
| **4** | **Decide the Worker Deployment topology: one per machine, not one for the fleet.** | With one shared Deployment, an offline laptop blocks every rollout or forces `--ignore-missing-task-queues`, which the docs say leaves inconsistent configuration [S9]. Must be decided before the first worker ships — version history does not migrate. | **~2 h decide, ~2 days wire** (same edit as item 5) | — |
| **5** | **Derive queue names and deployment names from explicit config, never from `gethostname()`, never with a UUID.** | [S14]'s sample uses `hostname-uuid`, correct for sessions and wrong here: a restart orphans a queue with work in it. Same class as vendored §2.3 "identities are explicit, never derived". | **~4 h** | 2, 4 |
| **6** | **Pick a capability-declaration surface.** Recommend (a) static topology profile now, (b) Deployment Version metadata alongside item 4, (c) registration workflow deferred. **Record in the roadmap that (c) is a re-acquisition of capability advertisement**, not a new invention. | Temporal answers existence and liveness natively and capability not at all (§4.4). SkyyNet must know before it enqueues, because after it enqueues there is no fallback. Roadmap already names "topology profiles". | **(a) ~4 h · (b) ~1 day · (c) ~1 week, deferred** | 4 |
| **7** | **Build the fleet-liveness surface into `/standup`.** Wrap `temporal task-queue describe` and `temporal worker list` [S9][S10]. | Recovers the "one number" capacity view that M queues cost (§5). Per-queue backlog stats already exist; only the aggregation is missing. | **~1 day** | 2 |
| **8** | **Decline wake-on-task.** Record the decision: workers run always-on where the machine is always-on; work addressed to a sometimes-off machine waits per item 3's policy. | Temporal ships the mechanism but only for AWS Lambda and GCP Cloud Run [S8][S9]. Building an equivalent is ~1 week for a fleet of three. | **~0 (a recorded decision)** | 3 |
| **9** | **Record what is NOT needed, so it is not re-derived:** Worker Sessions (Go-only [S11]), Sticky Execution as a pinning mechanism (wrong primitive [S5]), any custom scheduler or matching-service change. | Prevents three plausible-looking dead ends. The routing mechanism is a string. | **~0** | — |

**Aggregate: roughly one week of planning and wiring, no new primitive, no fork of anything.** The
expensive items on this list are all *decisions*, which is the correct shape for a phase that is
gated on decisions the roadmap already flags as open.

---

## 9. Test plan — what research cannot settle

1. **Measure the no-poller path end to end, once.** Stop a machine's worker, enqueue a workflow addressed to its queue, and record: what `temporal task-queue describe` shows at T+1min and T+6min (the docs say pollers are removed after 5 minutes [S10]); whether a `schedule_to_start_timeout` fires cleanly; what the workflow sees. **This is the single highest-value experiment** because item 3's policy is being written against documented behaviour that has not been observed here.
2. **Measure the standing cost of an idle per-machine queue.** Run M=3 machines with D queues each for a week against the real Postgres, and record connection count, matching-service load and DB growth. §4.1's negative finding is that no first-party cost curve exists; this produces ours. Single-partition versus the default 4 is the one variable worth sweeping.
3. **Test the version-skew scenario deliberately.** With one Deployment spanning machines, take one offline and attempt `set-current-version`. Confirm the documented failure [S9], then repeat with per-machine deployments and confirm independence. This converts item 4 from a derived argument into an observed one, in under an hour.
4. **Time item 1's classification, and count the result.** If it turns out that ≥80% of workflows are repo-local, the shared tier in §4.1 option (c) is near-empty and option (a) is the better answer. If it is closer to half, option (c) is load-bearing and §5's failover argument is the paper's most important finding. **Research cannot predict this ratio; reading `scripts/workflows/` settles it in two hours.**
5. **Test whether one process comfortably hosts D Workers under real `claude -p` load.** [S14] establishes the pattern is supported; it does not establish that a laptop running four Workers plus a 40-minute Claude Code activity behaves. Pairs with [`python_sdk_long_activities.md`](python_sdk_long_activities.md)'s heartbeat work.
6. **Research handoff, not experiment:** re-run §4.4 when SkyyNet's specification exists. This paper's federation argument is reasoning about a stub, and the capability-discovery decision (item 6) should be re-opened — not merely refreshed — once the federation tier is specified.

---

## 10. Citations

**Temporal first-party — all fetched from `raw.githubusercontent.com`, default branch `main` confirmed via the repository API [S28].**

- **[S1]** Temporal Documentation — *Task Queues* (raw, complete file dump). https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/task-queues.mdx
- **[S2]** Temporal Documentation — *Task Routing and Worker sessions* (raw, complete file dump). https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/task-routing-worker-sessions.mdx
- **[S3]** Temporal Documentation — *Task Queue Names* (raw). https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/task-queue-naming.mdx
- **[S4]** Temporal Documentation — *Detecting Activity failures* (raw, complete file dump; source of the ∞ Schedule-To-Start default). https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/detecting-activity-failures.mdx
- **[S5]** Temporal Documentation — *Sticky Execution* (raw, complete file dump). https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/sticky-execution.mdx
- **[S6]** Temporal Documentation — *Worker Versioning* (raw, complete file dump). https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/worker-versioning.mdx
- **[S7]** Temporal Documentation — *Workers* (raw file, **summarizing fetch — reduced confidence**; Worker Identity). https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/workers.mdx
- **[S8]** Temporal Documentation — *Serverless Workers* (raw, complete file dump). https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/serverless-workers/index.mdx
- **[S9]** Temporal Documentation — *Temporal CLI `worker` command reference* (raw, complete file dump; auto-generated from CLI definitions). https://raw.githubusercontent.com/temporalio/documentation/main/docs/cli/command-reference/worker.mdx
- **[S10]** Temporal Documentation — *Temporal CLI `task-queue` command reference* (raw, complete file dump). https://raw.githubusercontent.com/temporalio/documentation/main/docs/cli/command-reference/task-queue.mdx
- **[S11]** Temporal Documentation — *Worker Sessions — Go SDK* (raw; "currently available only in the Go SDK"). https://raw.githubusercontent.com/temporalio/documentation/main/docs/develop/go/workers/sessions.mdx
- **[S12]** Temporal Documentation — *Worker performance* (raw file, **summarizing fetch — reduced confidence**; poller autoscaling). https://raw.githubusercontent.com/temporalio/documentation/main/docs/develop/worker-performance.mdx
- **[S13]** Temporal Documentation — *Temporal Worker deployments* (raw, complete file dump). https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/worker-deployments/index.mdx
- **[S14]** Temporal Documentation — *Worker-Specific Task Queues Pattern* (raw, complete file dump; the single most decision-relevant source in this paper). https://raw.githubusercontent.com/temporalio/documentation/main/docs/design-patterns/worker-specific-taskqueue.mdx
- **[S28]** GitHub contents/repository API — directory enumerations and `default_branch` confirmations used for the negative findings' search methods (`temporalio/documentation` → `main`; `paperclipai/paperclip` → `master`; `sipyourdrink-ltd/bernstein` → `main`; `hashicorp/nomad` → `main`). https://api.github.com/repos/temporalio/documentation

**Agent-orchestration comparators**

- **[S15]** bernstein — `proto/bernstein/v1/tasks.proto` (raw, complete file dump). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/proto/bernstein/v1/tasks.proto
- **[S16]** bernstein — `proto/bernstein/v1/cluster.proto` (raw, complete file dump). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/proto/bernstein/v1/cluster.proto
- **[S17]** bernstein — repository metadata (GitHub API JSON): Apache-2.0, `default_branch: main`, 788 stars, `pushed_at: 2026-08-04`. https://api.github.com/repos/sipyourdrink-ltd/bernstein
- **[S18]** Paperclip — repository metadata (GitHub API JSON): MIT, `default_branch: master`, `stargazers_count: 75610` **as fetched 2026-08-04** (live counter; a same-day re-fetch read 75,612), `pushed_at: 2026-08-04`, `archived: false`. https://api.github.com/repos/paperclipai/paperclip
- **[S19]** bernstein — *Cluster deployment patterns*, MESH section (raw, section dumped byte-for-byte). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/cluster/deployment-patterns.md
- **[S20]** Paperclip — *Agents runtime* (raw file, **summarizing fetch — reduced confidence**). https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/agents-runtime.md

**Infrastructure scheduling comparators**

- **[S21]** Kubernetes — *Assigning Pods to Nodes* (raw). https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/scheduling-eviction/assign-pod-node.md
- **[S22]** Kubernetes — *Taints and Tolerations* (raw). https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/scheduling-eviction/taint-and-toleration.md
- **[S23]** Kubernetes — *DaemonSet* (raw). https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/controllers/daemonset.md
- **[S24]** Kubernetes — *StatefulSets* (raw file, **summarizing fetch — reduced confidence**; used only as corroboration). https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/controllers/statefulset.md
- **[S25]** GitHub Docs — *Self-hosted runners reference* (raw source markdown; routing precedence). https://raw.githubusercontent.com/github/docs/main/content/actions/reference/runners/self-hosted-runners.md
- **[S26]** GitHub Docs — *Actions limits* (raw source markdown; 24-hour self-hosted queue cancellation). https://raw.githubusercontent.com/github/docs/main/content/actions/reference/limits.md
- **[S27]** GitLab Docs — *Configure runners* (raw source markdown; tags and the "stuck" condition). https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/ci/runners/configure_runners.md
- **[S29]** SchedMD — *sbatch* man page (**rendered page — reduced confidence**; `--nodelist`, `--constraint`). https://slurm.schedmd.com/sbatch.html

**Source count: 29 cited.** Fetch-method accounting, restated at critic round 1 so it survives a byte
diff:

- **19 fetched as complete or sectional byte-for-byte dumps** — [S1], [S2], [S3], [S4], [S5], [S6], [S8], [S9], [S10], [S11], [S13], [S14], [S15], [S16], [S19], [S21]\*, [S22]\*, [S23]\*, [S26]. ([S3] returned raw file text with its code blocks intact.)
- **\*3 of those are Kubernetes Hugo sources** ([S21], [S22], [S23]) whose spans are **verbatim-equivalent after shortcode/emphasis normalization**, not byte-identical to the raw file — see the transcription note in §3.2.
- **2 fetched raw with targeted phrase extraction** rather than a full dump — [S25], [S27]. Spans confirmed present; not certified as complete-file reproductions.
- **4 fetched from raw sources whose response summarized**, marked reduced at every point of use — [S7], [S12], [S20], [S24]. Note §6.4: **[S20] is load-bearing in §6.5** despite being in this class.
- **1 rendered page** — [S29]. Note §6.4: **also load-bearing**, as one of four direct sources for §3.4.
- **1 API-metadata aggregate** — [S28].

**No search-engine result summary is cited as a source anywhere in this paper.**

**Repo artifacts referenced (not counted above):**
`docs/standards/temporal/worker_deployment_standard.md` (vendored, MIRROR) §1.1, §1.4, §2.1, §2.2,
§2.3, §3, §8.2, §8.5, §10.4 — the queue-axis conflict in §4.1 and the existing dead-queue machinery in
§4.2 are stated against this file. `docs/development/roadmap.md` § *Phase: Temporal Integration* —
the addendum items this paper feeds. `docs/standards/architecture/problem-statement.md` § *Where we
actually differ* — the claim under test.

**Adjacent pool papers referenced (not counted above):**
[`durable_execution.md`](durable_execution.md), [`backbone_edge_generality.md`](backbone_edge_generality.md),
[`python_sdk_long_activities.md`](python_sdk_long_activities.md).
