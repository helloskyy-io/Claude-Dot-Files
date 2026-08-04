# backbone_edge_generality

```
Topic:          Does a domain-agnostic orchestration backbone with swappable domain edges hold up —
                and does each new edge really cost less to stand up than the last?
Feeds:          problem-statement.md § "Where this repo sits" (the "backbone does not change; only
                the edge does" claim and the named future edges), § "Why coding is the first edge,
                and not merely the earliest" (the economies-of-scope and compounding claims), and
                § "What this means for anything built here" → "Nothing may assume the coding edge"
                (the binding design constraint on work happening today). Also system-overview.md
                § "What is not built".
Last validated: 2026-08-03
Revalidate:     high — 6 weeks
Confidence:     DEFINITIVE on what each surveyed platform shipped, extracted, or refused, and on the
                numeric facts drawn from first-party raw sources (Kubernetes KEP + release blog,
                Home Assistant ADRs + analytics endpoint + developer docs, OPC Foundation nodeset
                repo, EtherCAT Technology Group, Temporal activity docs, ROS 2 design articles,
                nf-core site). DEFINITIVE on the wording of the counter-position principles (Fowler,
                Fowler/Beck, Glass, Brooks) as reproduced at the cited URLs. DERIVED — and the
                paper's core contribution — on the three-way split of what actually stays generic,
                on the "amortisation vs. declining marginal cost" distinction, and on the
                supervisory-not-control reframing of the server/edge seam. UNVERIFIED and stated as
                such at every point of use: the Home Assistant integration tally and the OPC UA
                nodeset directory total (both tool-side counts of long listings, neither
                independently recounted — order-of-magnitude only); the ISO 10218-1:2025 and EU
                Machinery Regulation Annex I content (first-party fetches returned 403 / truncated
                before the Annex, so NEITHER IS ASSERTED); and the nf-core Genome Biology figures
                (unreachable, so NOT USED — the first-party site count is used instead).
Negative:       Four findings of absence, each stated with its search method — no measured
                cost-per-integration-N study across unrelated domains (§3.4); no documented
                post-mortem of premature platform generalisation (§6.3); no benchmark of an
                assistant operating an orchestration substrate it helped author (§7.3); no platform
                that added a genuinely unrelated second domain on an unchanged core (§8.4).
Critic:         PASS-WITH-FIXES (round 3: §7.3 benchmark-set attribution corrected —
                PersonalHomeBench re-cited to arXiv 2604.16813 as search-surfaced and AI2-THOR
                re-cited or dropped, leaving [S36] credited only with the benchmarks it names)
                — 2026-08-03
```

> **Volatility note (Research Standard §3, mixed-volatility rule) — ruling applied 2026-08-03.**
> Most of this paper is low-volatility: every load-bearing claim in §2–§6 rests on 1975–2026
> fundamentals, mature standards bodies, and *completed* migrations — ROS 1 → ROS 2, Kubernetes
> in-tree → out-of-tree, OPC UA companion specs, the software-product-line economics literature, the
> YAGNI/rule-of-three/second-system corpus. **§7 is not.** It cites agent benchmarks, which §5
> classes as high-volatility AI/agent tooling.
>
> The first draft proposed `low — 5 months` on the argument that §7 is a purely negative finding and
> therefore decays in one direction. **That argument was put to the critic and rejected, and the
> rejection is correct on the merits:** §7.1 and §7.2 assert positive quantitative facts from
> high-volatility sources ([S31]–[S36]), and this paper concedes the point itself where it notes
> that [S34]'s figure "moves across versions." §3's one-third threshold governs whether to *split*
> the paper, not what interval the header takes — the rule is to take the highest tier present,
> always. §3's tiebreak settles the rest: "the failure mode is over-refresh, never staleness."
>
> **The header therefore takes `high — 6 weeks`** — the top of §5's high band, justified because
> §7's sources are published papers rather than a live API surface.
>
> **Refresh scope (per §3's provision for marking slower-decaying sections):** re-verify **§7 only**.
> §2–§6 and §8–§9 may be skipped; their sources are stable and their claims are not
> version-sensitive. **Explicit trigger, overriding the interval:** revalidate immediately if a
> second edge is scheduled, or if a first-party result on cross-domain agent operation appears.

---

## 0. The short answer, for a consumer who reads no further

The problem statement makes four separable claims. They do not stand or fall together, and the
evidence separates them cleanly.

| # | Claim (problem statement's words) | Verdict from this paper |
|---|---|---|
| **C1** | "The backbone does not change; only the edge does" | **Supported as a shape, with one correction.** Every mature platform of this form works — and every one of them had to put a *domain ontology* somewhere. None kept a truly domain-free core. |
| **C2** | "each new edge costs less to stand up than the one before it" | **Unsupported in the strong form; supported in a weaker one.** The measured evidence for declining marginal cost comes from product lines *within one domain*. The nearest cross-domain measurement found says the opposite: cost per integration rose linearly. |
| **C3** | "An edge is … a machine with a capability and a credential, running a worker that speaks the same protocol" | **Holds for supervisory work; fails for control.** A durable-execution backbone whose activity contract is at-least-once cannot own an irreversible or hard-real-time action. The server/edge seam helps here more than it hurts — but only if the edge worker is understood as a *supervisor*, not a controller. |
| **C4** | "every new edge arrives with an assistant already fluent in the backbone that runs it" | **Least testable claim in the set, and the evidence that exists is unflattering.** Two independent smart-home benchmarks find that the category agents fail worst at is *automation/workflow scheduling* — which is precisely the backbone's job. |

**The binding constraint under test — "Nothing may assume the coding edge… would this still make
sense if the edge were a robot?" — survives, but for a reason different from the one stated.** It is
defensible as a *modifiability discipline* (Fowler explicitly exempts that from YAGNI), not as a
licence to build edge machinery now. §6 develops this.

---

## 1. Primer — what the question actually is, and what would falsify it

"Domain-agnostic backbone, swappable domain edges" is not a novel idea; it is one of the oldest
shapes in systems engineering, and it has a well-attested failure mode on each side.

- **Fail left:** the core hard-codes its first domain's assumptions and cannot be extended later.
- **Fail right:** the core is generalised ahead of evidence, pays carry cost forever, and the second
  domain never arrives — or arrives in a shape the generalisation did not anticipate.

Both failures are documented in the field (§2.3, §2.4 for the first; §6 for the second). The
interesting question is therefore not "does this pattern exist" — it plainly does — but **what,
empirically, is the set of things that stayed generic across a domain boundary, and what did every
platform end up dragging back into the core?** That is the question §2 answers, because it is the
only version of the question whose answer constrains a design decision made today.

A note on scope. This paper does not rule on any specific file in this repo. Its neighbours in the
pool cover adjacent ground: [`durable_execution.md`](durable_execution.md) establishes what the
durable substrate provides (and is the input to §5's constraint analysis);
[`hierarchical_agents.md`](hierarchical_agents.md) covers parent/child composition;
[`workflow_reuse_boundary.md`](workflow_reuse_boundary.md) covers parameterise-vs-fork *within* one
domain — this paper is the cross-domain case, and reaches a compatible but distinct conclusion.

---

## 2. The comparative landscape — five platforms that actually did it

### 2.1 OPC UA — the purest instance of the intended shape

OPC UA is the closest existing thing to "one backbone, many domain edges." The architecture is
literally a domain-neutral base information model plus **companion specifications**, which the OPC
Foundation describes as being developed to "publish specific information models (e.g., for specific
industries, specific devices, specific use cases)" and to "specify how to use OPC UA in specific
environments" [S1]. *(Confidence: definitive; rendered first-party page, quoted conservatively.)*

The scale is checkable from a raw source. The OPC Foundation's `UA-Nodeset` repository — the
machine-readable form of the companion models — carries **~80 root directories**, including
`Robotics`, `MachineTool`, `Mining`, `Glass`, `PlasticsRubber`, `Woodworking`,
`CommercialKitchenEquipment`, `LADS` (laboratory devices), `IEC61850`, `ISA-95`, `PackML`,
`Powertrain`, `Scales`, `UnattendedRetail`, `Safety`, and `UAFX` [S2].

*(Confidence: **definitive** on the presence of every directory named above; **unverified /
approximate** on the total. Two independent enumerations of the same contents-API endpoint on the
same day returned 82 and 79 — both are tool-side tallies of a long listing, neither independently
recounted, so the honest figure is "~80". This is the same evidence class marked unverified for the
Home Assistant tally in §2.2, and it is marked the same way here deliberately. Not every directory
is a companion specification: `AnsiC`, `DotNet`, `Schema`, `TestModel`, `DemoModel`, `OpenApi`,
`XML` and `.github` are visibly tooling rather than domain models, putting the domain-model count at
**~70** — an approximation, not a counted figure.)*

**What stayed generic:** the address space, node classes, services, security model, and the
transport. **What did not:** `Safety` and `UAFX` are in that list. Functional safety and
TSN-scheduled deterministic communication were not expressible as ordinary companion models — they
became *additional core-adjacent specifications*. That is the pattern's first tell: the domain
ontology went to the edge, but the **timing and safety envelope came back toward the core.**

### 2.2 Home Assistant — ~1,000+ integrations on one core, and a core that is not domain-free

Home Assistant is the strongest available evidence that a very large edge count on a shared core is
achievable by a small team. Its own first-party analytics endpoint reports **661,738 active
installations** and integrations reported across **~1,000+ distinct integration identifiers** [S3].
*(Confidence: **definitive** on `active_installations: 661738`, an exact scalar field verified
independently twice; **unverified / order-of-magnitude** on the integration tally — independent
tool-side counts of the same large JSON document returned ~1,115 and ~1,500+, and neither was an
independent recount. The order of magnitude is what the argument uses; nothing here depends on the
exact figure.)*

The architecture is exactly the claimed shape: "An entity abstracts away the internal workings of
Home Assistant" [S4], and integration authors subclass entity base classes rather than touching the
state machine.

**But the core is not domain-agnostic, and the evidence is in Home Assistant's own repository.**

1. **A device ontology lives in core.** Entity integrations — `light`, `switch`, `climate`, `fan`,
   `sensor`, `binary_sensor`, `button`, `number`, `image` and others [S5] — are *core* concepts.
   Each new class of physical device that did not fit an existing abstraction produced a new
   first-class domain inside the core, not a plugin.
2. **A connectivity taxonomy lives in the manifest.** Every integration must declare an `iot_class`
   from a fixed core vocabulary: `local_push` ("Offers direct communication with device. Home
   Assistant will be notified as soon as a new state is available"), `local_polling`, `cloud_push`,
   `cloud_polling`, `assumed_state` ("We are unable to get the state of the device. Best we can do
   is to assume the state based on our last command"), and `calculated` [S6]. That vocabulary is a
   *domain* judgement — it encodes what kinds of latency and staleness a home-automation edge can
   have — and it is in the core manifest schema.
3. **The core rules on integration technique.** ADR-0004: "We no longer accept any new integration
   that relies on webscraping," because such integrations are "very fragile, break often" [S7].
   ADR-0011: "Integrations that are discoverable must provide a unique id (via
   `async_set_unique_id`) to allow the user to ignore the discovered config entry" [S8].
4. **The bar for an edge rises over time.** ADR-0022 established a four-tier quality scale, and the
   developer docs state the rule plainly: "To reach a tier, the integration must fulfill all rules
   of that tier and the tiers below" [S9][S10]. This matters for §3 — it is a documented mechanism
   by which the cost of integration *N+1* goes **up**, not down.

*(Confidence: definitive — all four points from raw GitHub markdown or the raw developer-docs
source.)*

### 2.3 Kubernetes — the same pattern, run backwards, with a price tag on it

Kubernetes is the most quantified case available, and it is the cautionary one. Cloud-provider
integrations were originally *in* the core tree. KEP-2395's goal is stated flatly: "Remove all cloud
provider specific code from the `k8s.io/kubernetes` repository with minimal disruption to end users
and developers" [S11]. The project's completion announcement puts numbers on what the core had
absorbed: the migration removed "roughly 1.5 million lines of code" and reduced "the binary sizes of
core components by approximately 40%", driven by "the growing complexity of maintaining native
support for every cloud provider across millions of lines of Go code, and the desire to establish
Kubernetes as a truly vendor-neutral platform" [S12].

The **duration** needs stating precisely, because §8.3 sizes a risk with it. [S12] says the goal was
pursued "Since as early as Kubernetes v1.7" and that success came "After many releases," having
"required several releases to bring each subsystem to GA-level maturity"; it gives no release count
and — published 2024-05-20 — names no end version. KEP-2395 states: "GA is targeted for v1.31. One
release after GA, the in-tree cloud providers can be safely removed," and cautions that "the removal
of the code will depend on when we can remove the in-tree storage plugins, so the actual removal may
end up in a later release" [S11]. **DERIVED:** v1.7 → v1.31 is 24 minor releases, and the KEP puts
full removal at v1.32 or later — so the span is roughly *two dozen* releases.

*(Confidence: definitive on the [S11] and [S12] quotations, both fetched raw / first-party; DERIVED
on the release arithmetic. **Correction, 2026-08-03, after critic review:** an earlier draft
asserted "permanent removal in v1.31 [S12]" and "a dozen releases." [S12] contains no occurrence of
"1.31", and [S11] points to v1.32-or-later. The error understated the span by about half, in the
direction that weakened this paper's own §8.3 conclusion.)*

Read carefully, this case cuts **both** ways and should not be enlisted for one side:

- It is evidence that a core *will* accrete domain-specific accommodation if you let it — 1.5M lines
  and 40% of the binary is not a rounding error.
- It is also evidence that the extraction is survivable. Kubernetes did not die; it shipped the
  refactor across roughly two dozen releases while remaining the dominant platform in its category.

### 2.4 ROS and ROS 2 — the fail-left case, stated by the project itself

The single clearest documented instance of "hard-coded the first domain, could not extend later" is
ROS. The ROS 2 design rationale states that ROS "began life as the development environment for the
Willow Garage PR2 robot," guided by characteristics including "a single robot; workstation-class
computational resources on board; no real-time requirements…; excellent network connectivity…;
applications in research, mostly academia" [S13].

Each new use case broke one of those assumptions — "Teams of multiple robots… are all somewhat of a
hack on top of the single-master structure of ROS"; "Small embedded platforms"; "Real-time systems:
we want to support real-time control directly in ROS, including inter-process and inter-machine
communication"; "Non-ideal networks" [S13]. And the project's own verdict on retrofitting rather
than rewriting: "Given the intrusive nature of the changes that would be required to achieve the
benefits that we are seeking, there is too much risk associated with changing the current ROS system
that is relied upon by so many people" [S13]. *(Confidence: definitive — design.ros2.org is
first-party and static.)*

**The sharper detail is what happened when robotics tried to add a genuinely different edge to its
*own* generic backbone.** Microcontrollers did not become a ROS 2 plugin. They got a different
middleware: micro-ROS runs a "client-server architecture, where low resource devices, called XRCE
Clients, are connected to a server, called XRCE Agent," at "less than 75 KB of Flash memory and
around 3 KB of RAM" for a publisher/subscriber application [S14]. *(Confidence: definitive.)* The
protocol had to change to reach the constrained edge. "Speaks the same protocol" was not achievable.

### 2.5 Bioinformatics — a named future edge that declined the generic engine

This is the most direct evidence about one of the problem statement's four named edges, and it is
not encouraging for the generic-backbone thesis.

Bioinformatics is a domain saturated with long-running, retryable, dependency-heavy batch work — on
paper, the ideal customer for a general workflow engine. It did not buy one. The field built and
standardised on **domain-specific** workflow managers (Nextflow, Snakemake, Galaxy, Cromwell/WDL)
plus a domain-specific curation layer. nf-core's own site states: "Browse the 155 pipelines that are
currently available as part of nf-core" [S15]. *(Confidence: definitive on the count and the
existence of the ecosystem; the underlying peer-reviewed account is [S16], which I could **not**
fetch — see §8 negative findings.)*

The derived point, which is the one that matters: **an edge is not a blank slate.** Three of the
four named future edges (industrial, robotics, bioinformatics) already have entrenched, standardised
orchestration of their own. The backbone would not be arriving into a vacuum; it would be arriving
as a competitor to, or a layer above, something the domain already trusts.

### 2.6 Robotics again — the control structure is not a workflow

Robotics converged on **behavior trees**, not on workflow DAGs or state machines: "BTs are a very
efficient way of creating complex systems that are both modular and reactive. These properties are
crucial in many applications, which has led to the spread of BT from computer game programming to
many branches of AI and Robotics" [S17]. *(Confidence: definitive on the quotation.)* Reactivity —
re-evaluating the whole tree on every tick — is a structurally different control model from a
durable workflow that persists a decision and resumes from it.

### 2.7 The derived finding — what actually stayed generic

**DERIVED, from [S1]–[S17] taken together.** Across five independent platforms in four unrelated
domains, the split falls in the same place every time:

| Layer | Stayed generic? | Evidence |
|---|---|---|
| Transport, addressing, identity, discovery, security | **Yes** | OPC UA services/address space [S1]; ROS 2 DDS layer [S13]; K8s API machinery [S11] |
| Lifecycle, retry, and the execution record | **Yes** | K8s controllers [S11]; Temporal event history ([`durable_execution.md`](durable_execution.md)) |
| **Domain ontology** — what a thing *is* and what it can be asked to do | **No** | HA entity domains in core [S5]; OPC UA ~70 companion models [S2]; nf-core's 155 curated pipelines [S15] |
| **Timing / safety envelope** | **No — and it migrates toward the core** | OPC UA `Safety` + `UAFX` nodesets [S2]; ROS 2's entire rewrite rationale [S13]; micro-ROS's separate middleware [S14] |
| **Vendor/instance specifics** | **Started in core, had to be evicted** | K8s: 1.5M LOC, ~40% binary [S12] |

**So: C1 is supported as a shape, with one correction that is load-bearing.** The backbone genuinely
does not change for transport, lifecycle, and record-keeping. It *does* change for the domain
ontology and the timing envelope — and the strongest platforms in the survey are the ones that
recognised this early enough to put the ontology in a **named, versioned, out-of-core artifact**
(OPC UA companion specs, CSI/CRI/CNI) rather than in the core (Home Assistant's entity domains,
Kubernetes' first decade).

---

## 3. Does the marginal-cost-per-edge claim have support?

This is the sharpest testable version of the thesis, so it gets the most careful handling.

### 3.1 The evidence in favour is real — and it is all same-domain

The software/systems product line literature is where this claim lives. The canonical economics
paper is Böckle, Clements, McGregor, Muthig and Schmid, "Calculating ROI for software product
lines," *IEEE Software* 21(3), 2004 [S18]. The strongest empirical claim is in the *title* of a
later paper by the same school: Gregg, Scharadin and Clements, "The more you do, the more you save:
the superlinear cost avoidance effect of systems product line engineering," SPLC 2015 [S19]. The
associated case — Lockheed Martin's Aegis Weapon System — is recorded by the SPLC Product Line Hall
of Fame: "The Aegis Weapon System realized more than $166 million in cost avoidance over the last
three years" [S20]. *(Confidence: definitive on the existence, authorship and titles [S18][S19] —
retrieved via the Semantic Scholar graph API, whose response elided both abstracts. **Definitive on
the Hall of Fame quotation**, which was fetched. **I have not read either paper's method**, so no
claim here rests on their internal argument.)*

**The disqualifying detail:** Aegis variants are *the same product for different ships*. Product line
engineering's economies of scope are measured across **members of one family in one domain**. That
is not the claim under test. The problem statement's claim is that a home-automation edge makes a
robotics edge cheaper — a transfer across domains with no shared ontology, no shared regulator, and
no shared timing envelope. **The SPL literature is evidence for a different proposition than the one
it is being asked to support.** *(DERIVED from [S18]–[S20].)*

### 3.2 The nearest cross-domain measurement says the opposite

Segment (now Twilio) ran a platform whose entire job was integrating unrelated third-party
destinations — structurally the closest published analogue to "N edges on one backbone." Their
engineering account states: "With our microservice architecture, our operational overhead increased
linearly with each added destination"; "we added over 50 new destinations, and that meant 50 new
repos"; and on the shared-library problem, "Eventually, all of them were using different versions of
these shared libraries" [S21]. *(Confidence: definitive on the quotations — but note this is a
rendered vendor engineering blog, and the cause they diagnose is per-destination **deployment
topology**, not generality as such. It is evidence that per-edge cost did not fall; it is weaker
evidence about *why*.)*

Kubernetes points the same way over a longer window: 1.5M lines of per-vendor accommodation
accumulated *in the core* before anyone extracted it [S12]. Home Assistant points the same way by a
third mechanism: the quality scale ratchets the bar for each new integration upward over time
[S9][S10].

### 3.3 The move that actually makes N+1 cheaper — and it is not the one claimed

**DERIVED from [S2], [S11], [S12], [S15].** In every case where per-edge cost to the *platform*
demonstrably fell, the mechanism was the same, and it was not amortisation:

> The platform defined a stable interface and **externalised the marginal cost to the edge author.**

Kubernetes did not make storage integration cheaper; it made storage integration *someone else's
repository* (CSI). The OPC Foundation does not write ~70 domain models; industry consortia do. Home
Assistant's integrations are contributed, with "one or more active code owners" required at Silver
[S9]. nf-core's 155 pipelines are community-authored [S15].

This is a genuinely valuable property and the architecture should claim it. **But it is a different
claim.** "The platform's marginal cost per edge falls because edge authors absorb it" is true and
supportable. "Each new edge costs less to stand up than the one before it" — the total cost, borne
by whoever bears it — has no support I could find in either direction across unrelated domains.

### 3.4 Negative finding, with search method

**No measured or documented study of cost-per-integration-N across unrelated domains was located.**
Search method: WebSearch for (a) software product line ROI / break-even / number of products, with
and without the Clements/Böckle/McGregor author set; (b) "superlinear cost avoidance" product line;
(c) the Segment/microservices integration-cost retrospective; (d) Kubernetes in-tree→out-of-tree
extraction KEPs and release notes; (e) Home Assistant architecture ADRs (full ADR index enumerated
via the GitHub contents API, 22 files, none on integration cost economics). Attempted first-party
retrieval of [S18] and [S19] full texts; both abstracts were elided by the publisher in the
Semantic Scholar response and neither PDF was reachable. **This is a gap, not a null result** — the
measurement may exist behind IEEE/ACM paywalls I could not reach.

### 3.5 Verdict on C2

**Unsupported in the strong form.** The one measured cross-domain analogue reports linear growth in
per-edge overhead [S21]; the platform that let its core absorb domain specifics paid 1.5M lines to
get them out [S12]; the platform with the largest edge count actively *raises* the per-edge bar over
time [S9]. The supporting literature measures a different phenomenon [S18]–[S20].

**Supported in the weaker, more useful form:** a stable edge interface externalises marginal cost,
and *that* is what makes large edge counts survivable. The problem statement's second mechanism —
"it builds them… that is code, written by the edge that already exists" — is a real cost reduction
of the same kind (it moves work to a cheaper producer), and is not addressed by any of this
evidence. It is untested, and §7 is where its weakest link lives.

---

## 4. What each named future edge demands that a coding edge does not

Concretely, per edge, with the constraint that actually binds the architecture named first.

| Edge | The binding constraint the coding edge does not have | Evidence |
|---|---|---|
| **Industrial automation** | **Cycle determinism.** EtherCAT's stated design targets are "short cycle times (≤ 100 µs)" with "low jitter for accurate synchronization (≤ 1 µs)", across "Up to 65,535 devices … in one EtherCAT segment" [S22] | first-party ETG |
| **Robotics** | **Hard/firm real-time and no-allocation code paths.** "A hard real-time system treats a missed deadline as a system failure"; real-time paths must "Avoid pagefaults" and "Avoid nondeterministic heap allocation algorithms" [S23] | first-party ROS 2 design |
| **Robotics (embedded)** | **A resource envelope that excludes a general-purpose worker.** 75 KB flash / 3 KB RAM [S14] | first-party micro-ROS |
| **Home automation** | **Staleness and locality are first-class, not incidental** — the `iot_class` vocabulary exists because "an update might be noticed later" is a real and declared property of an edge [S6] | first-party HA docs |
| **Bioinformatics** | **An incumbent, standardised, community-curated orchestration layer already occupies the slot** [S15] | first-party nf-core |
| **Robotics / industrial (regulatory)** | Certification regimes with third-party assessment — **claim NOT verified, see §8** | — |

### 4.1 The irreversibility problem, stated precisely

This is the load-bearing question the dispatch asks, and it has a clean answer from first-party
sources on both sides of the seam.

**What the backbone guarantees.** Temporal's own documentation: "For an Activity with a Retry Policy
that allows retries, Temporal guarantees that the Activity will be observed as completed exactly
once. However, the Activity may be executed multiple times" [S24]. *(Confidence: definitive.)* The
exactly-once property is about the **workflow's view of the record**, not about the world. The world
gets at-least-once.

**What the world permits.** Microsoft's Azure Architecture Center, on compensating transactions:
"Define clear *points of no return* and irreversible steps. In complex workflows, you can't safely
or meaningfully undo some operations, such as external side effects or legally binding actions."
And: "It's not easy to generalize compensation logic. A compensating transaction is application
specific" [S25]. *(Confidence: definitive on the quotations; the source is a first-party vendor
architecture guide, which is prescriptive rather than empirical.)* The intellectual lineage is
Garcia-Molina and Salem's *Sagas* (SIGMOD 1987) [S26], whose bibliographic record I confirmed but
whose text I could not retrieve (§8).

**DERIVED, from [S24] + [S25] + [S23]:** the durable-execution contract and the physical-actuation
contract are incompatible at two separate points, and they need separating because the fixes differ:

1. **At-least-once vs. irreversible.** A retried "extend the arm" is not a retried API call. The
   mitigation exists and is well understood — an idempotency key plus a read-back of physical state
   before acting — but it is *per-activity engineering at the edge*, and [S25] states the general
   form does not exist ("not easy to generalize compensation logic"). **This does not break the
   architecture. It breaks the assumption that an edge is cheap.**
2. **Late-is-wrong vs. resumable.** This one is not fixable by engineering at the edge. A
   durable-execution activity's unit of scheduling is orders of magnitude coarser than a 100 µs
   cycle [S22] and the substrate is explicitly a persisted, replayable, allocating one, which [S23]
   rules out of a real-time path. **A hard-real-time control loop cannot be a backbone activity at
   any level of effort.**

### 4.2 The seam — does "server runs no agent compute, worker lives at the edge" help or hurt?

The problem statement's split is: **server tier** — "durable orchestration plus a shared library of
reusable workflow modules… Runs no agent compute"; **edge tier** — "a worker on each participant's
own machine… Credentials never leave the edge."

**DERIVED assessment, from [S13], [S14], [S22]–[S25] and the surveyed platforms' own layering:**

**Where the seam helps — materially, and more than expected:**

- **It is the layering every surveyed platform already converged on.** OPC UA sits above the fieldbus
  [S1][S22]; ROS 2 sits above the real-time control layer [S23]; Home Assistant sits above the radio
  [S6]. A supervisory tier that schedules, records, and coordinates while something below it owns
  the microsecond is not an awkward compromise — **it is the canonical shape of every successful
  domain-agnostic backbone in this survey.**
- **Keeping agent compute off the server is exactly right for irreversibility.** The compensation
  and read-back logic that [S25] says cannot be generalised is *domain* logic; it belongs where the
  domain knowledge and the physical state are — at the edge. A server that ran agent compute would
  be the natural place to put a generic compensation framework, and building one would be the
  mistake.
- **Credential locality is domain-independent.** Nothing in the industrial, robotics, or lab
  literature surveyed argues against it, and the certification direction (§8) argues for it.

**Where it hurts, or is simply irrelevant:**

- **It buys nothing for real-time.** The seam is in the wrong place to help; the real-time loop is
  *below* the worker, not inside it. This is not a flaw so much as a scope boundary that the problem
  statement does not currently draw.
- **The worker may not fit.** "A machine with a capability and a credential, running a worker that
  speaks the same protocol" assumes the edge machine can host the worker. micro-ROS is the
  documented counterexample: the constrained edge needed a *different protocol and an agent proxy*
  [S14]. The generalisation that survives contact with this evidence is: **the worker runs on a
  machine adjacent to the capability, not necessarily on the machine with the capability.**
- **Certification, if it applies, cuts against remote scheduling.** Unverified — see §8 — but the
  direction is clear enough to name as a risk: a safety function whose timing depends on a remote
  scheduler is a difficult thing to certify.

**The single most useful reframing this paper can offer:** state, in the problem statement, that the
backbone is a **supervisory** tier — it schedules, records, coordinates and diagnoses; it does not
close control loops. That reframing costs nothing today, is consistent with every platform in §2,
and converts C3 from a claim that is false as written into one that is true and defensible.

---

## 5. What this provides — the enumerated, citable properties

A plan may rely on these:

1. **The shape is proven at scale in four unrelated domains.** OPC UA (~70 domain models on one base
   model — approximate, see §2.1) [S1][S2], Home Assistant (~1,000+ integrations on one core —
   *unverified, order-of-magnitude*, see §2.2) [S3], Kubernetes (all cloud
   vendors on one API machinery, post-extraction) [S11][S12], ROS 2 (many robots on one middleware)
   [S13].
2. **What stays generic is specifically: transport, identity, discovery, lifecycle, retry, and the
   execution record.** [S1][S11][S13] + [`durable_execution.md`](durable_execution.md). This is a
   usable design test — a candidate backbone feature that is not in this list is suspect.
3. **The domain ontology will not stay generic, and the platforms that put it out-of-core did
   better.** OPC UA companion specs [S2] and Kubernetes CSI/CCM [S11][S12] versus Home Assistant's
   in-core entity domains [S5]. *(DERIVED.)*
4. **A stable edge interface externalises marginal cost to edge authors — this is the real
   economies-of-scope mechanism, and it is worth designing for.** [S2][S11][S15][S9]. *(DERIVED.)*
5. **The durable substrate's contract is at-least-once execution with an exactly-once record.**
   [S24]. Any edge design must state, per activity, what happens on a duplicate.
6. **Compensation does not generalise; it is per-domain, per-activity work.** [S25]. Budget for it
   per edge; do not plan a generic compensation framework in the backbone.
7. **Hard real time is out of scope for a durable-execution backbone, definitionally, not
   incidentally.** [S22][S23]. The backbone supervises the controller; it is not the controller.
8. **The named future edges have incumbents.** Bioinformatics has Nextflow/nf-core [S15]; industrial
   has OPC UA [S1]; robotics has ROS 2 + behavior trees [S13][S17]. A new edge is an integration
   with an existing ecosystem, not a greenfield.

---

## 6. The counter-position, sought deliberately

### 6.1 The case against building for the second use case

**YAGNI.** Fowler defines a presumptive feature as "Any code that supports a feature that isn't yet
being made available for use," and names four costs — build, delay, carry, repair [S27]. Cost of
carry is the one that applies to a design constraint rather than a feature: an extension point with
one implementation complicates every subsequent change.

**Speculative generality** (Fowler & Beck, *Refactoring* 2nd ed.): "You get it when people say, 'Oh,
I think we'll need the ability to do this kind of thing someday' and thus add all sorts of hooks and
special cases to handle things that aren't required" [S28]. *(Confidence: the quotation is from a
publisher's excerpt of the book, not from the book directly — corroborated secondary.)*

**The rule of three, in its reuse form** — the most directly damaging of the four. Glass, *Facts and
Fallacies of Software Engineering*, Fact 18: "There are two 'rules of three' in [software] reuse: It
is three times as difficult to build reusable components as single use components, and a reusable
component should be tried out in three different applications before it will be sufficiently general
to accept into a reuse library" [S29]. *(Confidence: quotation verified verbatim at the cited URL,
which reproduces the book passage; **the widely-repeated attribution to Ted Biggerstaff was NOT
confirmed** — the fetched source attributes it to Glass alone. Stated as a limit on the citation,
not smoothed over.)*

Applied here: **this repo has one edge.** Fact 18's second rule says three are needed before a
component is "sufficiently general," and its first says the generalising itself costs 3×.

**The second-system effect.** Brooks: "This second is the most dangerous system a man ever designs.
When he does his third and later ones, his prior experiences will confirm each other as to the
general characteristics of such systems, and their differences will identify those parts of his
experience that are particular and not generalizable" [S30]. *(Confidence: quotation as reproduced
on a sourced-quotation site citing the 1995 Anniversary Edition p. 55; I did not fetch the book.)*

**DERIVED, and uncomfortable:** the problem statement calls this repo "iteration one." Brooks's
warning targets exactly the transition being planned — from a working first system built under
restraint, to a second one designed with confidence and all the deferred generality applied at once.
The second half of Brooks's sentence is also the strongest single argument *for* getting to a second
edge quickly: only the third system tells you which parts of your experience were "particular and
not generalizable."

### 6.2 The counter-counter-case: hard-coding the first domain is also documented, and also expensive

ROS 1 [S13] and Kubernetes [S11][S12] are the two cleanest instances, and both are first-party
accounts. ROS 1 could not be retrofitted — the project judged the risk "too much" and rewrote [S13].
Kubernetes could be retrofitted, and it cost 1.5M lines [S12] across roughly two dozen releases
(v1.7 → v1.31 GA target, full removal v1.32 or later — DERIVED from [S11][S12], §2.3).

### 6.3 Negative finding: no post-mortem of premature *generalisation* was located

Search method: WebSearch for engineering retrospectives / post-mortems describing a platform
generalised ahead of its second use case ("generalized too early", "built for a second use case that
never came", platform retrospective phrasings). Results returned only generic articles *about*
conducting post-mortems. The Segment case [S21] is frequently cited as one, but its own account
diagnoses per-destination deployment topology, not premature generality. **Result: the
speculative-generality side of this argument is supported by principle and aphorism, not by a
documented case with numbers — while the hard-code-your-first-domain side has two first-party cases
with numbers ([S12], [S13]).** That asymmetry may be publication bias (successful restraint produces
no artifact to write about), and should not be read as settling the question.

### 6.4 The resolution that the evidence does support

**DERIVED, from [S27] + [S12] + [S13].** Fowler's own carve-out is the hinge, and it is quoted here
in full because it decides the matter: **"Yagni only applies to capabilities built into the software
to support a presumptive feature, it does not apply to effort to make the software easier to
modify"** [S27].

"Nothing may assume the coding edge… would this still make sense if the edge were a robot?" is a
*modifiability* discipline. It is a question asked at design review; it produces no extension points,
no plugin registry, no abstract base class with one implementation. Under Fowler's own definition it
**is not a YAGNI violation at all.**

The line falls precisely there, and it is the actionable output of this section:

| Permitted by the evidence | Prohibited by the evidence |
|---|---|
| Asking "would this make sense for a robot?" as a review question | Building a robot-shaped abstraction now |
| Keeping git/PR machinery out of the backbone and at the edge | Designing a generic "edge SDK" before edge two |
| Naming the domain ontology as an out-of-core artifact | Populating that artifact for an unbuilt domain |
| Writing down which activities are irreversible | Building a generic compensation framework [S25] |

---

## 7. The compounding claim — the thinnest evidence in the set

The claim: "every new edge arrives with an assistant already fluent in the backbone that runs it."

### 7.1 What transfers, per the evidence

Code in pre-training measurably improves *non-code* performance: "compared to text-only
pre-training, the addition of code results in up to relative increase of 8.2% in natural language
(NL) reasoning, 4.2% in world knowledge, 6.6% improvement in generative win-rates, and a 12x boost
in code performance" [S31]. *(Confidence: definitive on the quotation; 470M–2.8B parameter models,
so extrapolation to frontier scale is unwarranted.)* This is evidence that code training transfers —
but it is about *training data composition*, not about an assistant operating an unfamiliar
operational platform. It is the weakest kind of support for C4.

### 7.2 What the direct evidence says, and it is unflattering

| Setting | Result | Source |
|---|---|---|
| Generating PLC (IEC 61131-3) code | "State-of-the-art LLMs such as GPT-4 and LLaMa2 fail to produce valid programs for Industrial Control Systems"; a pipeline with grammar checkers, compilers and SMV verifiers "improved the generation success rate from 47% to 72%" | [S32] |
| Domain-rule-following agents (retail/airline) | "even state-of-the-art function calling agents (like gpt-4o) succeed on <50% of the tasks, and are quite inconsistent (pass^8 <25% in retail)" | [S33] |
| Simulated workplace, multi-tool | "the most competitive agent can complete 30% of tasks autonomously" | [S34] |
| Smart home, Matter-grounded simulator, 18 agents | "workflow scheduling is the hardest category, with failures persisting across alternative agent frameworks and fine-tuning" | [S35] |
| Smart home, 1,100 tasks, up to 135 devices | frontier LLMs "still exhibit significant weaknesses in automation task scheduling, ambiguity handling and personalized reasoning, especially as home complexity increases" | [S36] |

*(Confidence: definitive on every quotation — all fetched from arXiv abstract pages. Note [S34]'s
figure is from the v3 abstract, revised 2025-09-10; the number moves across versions and is a
high-volatility fact.)*

### 7.3 The derived reading

**DERIVED from [S31]–[S36].** Two things, and they point in opposite directions:

1. **The claim is stated in a form that cannot be tested.** "Fluent in the backbone" is not a
   measured construct. No benchmark evaluates an assistant's competence at operating an
   orchestration substrate it helped author, in a domain it has not seen. This is the least
   falsifiable of the four claims — worth saying plainly rather than padding.

   **Search method for that absence** (required by §3 — an unmethodized "does not exist" is
   indistinguishable from "didn't look"). The benchmark set surveyed, with each name's provenance
   stated so the method is reproducible:

   - **Read directly:** [S33] τ-bench (tool-agent-user, retail/airline), [S34] TheAgentCompany
     (simulated workplace, multi-tool), [S35] SimuHome (Matter-grounded smart home, 18 agents),
     [S36] SMH-Bench (1,100 tasks, up to 135 devices), and [S38] PersonalHomeBench (personalized
     smart home) — the last surfaced by the same search rather than by any other paper's citation.
   - **Named by [S36]'s related-work section**, verified verbatim in its HTML rendering:
     "HomeBench Li et al. (2025), SmartHome-Bench Zhao et al. (2025) and SmartBench Zou et al.
     (2026) study anomaly and safety-related scenarios, and SimuHome Seo et al. (2026) introduces
     executable temporal simulation," alongside "CASAS Cook et al. (2013) and ARAS Alemdar et al.
     (2013) focus on activity recognition, while VirtualHome Puig et al. (2018), ALFRED Shridhar et
     al. (2020), TEACh Padmakumar et al. (2022), BEHAVIOR Srivastava et al. (2022), and ReALFRED
     Kim et al. (2024) emphasize navigation and physical manipulation in household environments."

   Queries run: LLM-agent benchmarks for smart-home control and evaluation accuracy; LLM agents
   operating unfamiliar domain platforms; coding-model transfer to non-coding operational systems;
   LLMs for IEC 61131-3 / PLC programming; code-in-pretraining transfer to non-code tasks.

   **Every benchmark located evaluates an agent against a platform it did not author.** The
   authored-substrate variable is not manipulated anywhere in the set — which is why §9 item 5
   proposes measuring it here rather than waiting for the literature.

   *(Correction, 2026-08-03, round 3: an earlier draft attributed PersonalHomeBench and AI2-THOR to
   [S36]'s related-work section. Neither string occurs in it — re-verified by direct fetch of
   [S36]'s HTML, which enumerates the eleven names quoted above and no others. PersonalHomeBench is
   real and is now cited to its own record [S38]; AI2-THOR is dropped rather than re-cited, since
   nothing in the argument rests on it. Both were real benchmarks mis-attributed, not invented — but
   a search method is only worth what it is reproducible to, and five-of-seven names is not
   reproducible. **Conservative statement of the negative:** the two names' absence from [S36] is
   established for the HTML rendering fetched; a fetch reported partial content, so it is strong
   rather than exhaustive.)*
2. **The measurable adjacent evidence identifies the failure mode as the backbone's own job.** Both
   smart-home benchmarks independently name *automation/workflow scheduling* as the weakest category
   [S35][S36]. If an assistant's differentiating asset on a new edge is supposed to be backbone
   fluency, the two closest measurements say scheduling is where agents are worst. That is not
   disproof — those agents did not author the backbone, which is the whole point of the claim — but
   it is the opposite of confirmation, and it is the sharpest available signal.

**The restatement the evidence supports:** the assistant arrives fluent in the *backbone* (which it
wrote, and whose source, standards, and execution record it can read) and **illiterate in the
domain**. That is a real asset, and a smaller one. It also predicts the correct operating posture,
which the problem statement already has: human in the loop. Home Assistant's own LLM API is
consistent with that posture — it exposes intents to a model, with the stated constraint "No
administrative tasks can be performed" [S37].

---

## 8. Honest boundary analysis

### 8.1 The case that this question does not matter yet — argued properly

There is one edge. No second edge is scheduled. Under the roadmap, the next milestone is durable
execution with this machine as the first edge, not a second domain.

The argument for deferring, stated at full strength:

1. **The generality claim is untestable with N=1.** Glass's second rule of three says a component is
   not known to be general until it has been tried in three applications [S29]. Nothing this paper
   found contradicts that. A generality claim validated against zero additional domains is not
   validated.
2. **The costs of premature answer are the four Fowler names** [S27], and *cost of carry* is the one
   that bites a design constraint: every design review that asks "would this make sense for a
   robot?" spends real judgement on a hypothetical, and occasionally produces an abstraction that
   the actual second edge will not fit.
3. **Brooks's warning is precisely aimed at this transition** [S30] — the second system, designed
   with confidence and with all the deferred generality applied at once, is the dangerous one.
4. **The evidence in §2 says the guess will be wrong in a specific way anyway.** Every platform
   surveyed found that the domain ontology and the timing envelope did *not* stay generic. Since
   those are exactly the parts you cannot design without the second domain in hand, the portion of
   the work that could be done now is the portion that was never at risk.
5. **§6.3's asymmetry is not evidence of safety.** The absence of documented premature-generalisation
   post-mortems is at least as likely to be publication bias as to be evidence that it rarely
   happens.

### 8.2 Whether I agree

**Partly. I agree the question should not be *answered* now; I disagree that it should be *dropped*
now — and the distinction is not a hedge, it changes what gets written this week.**

Fowler's carve-out does the work [S27]: a review question is not a presumptive feature. The current
formulation — "Nothing may assume the coding edge… would this still make sense if the edge were a
robot?" — costs nothing to carry, produces no code, and is a modifiability discipline, which YAGNI
explicitly exempts. Keeping it is cheap and correct.

What the evidence *does* say should change now, and it is small:

- **Correct C2 in the problem statement.** "Each new edge costs less to stand up than the one before
  it" is not supported (§3). "A stable edge interface externalises the marginal cost to the edge
  author, and the coding edge is the cheapest available author" is supported, and is the claim
  actually being relied on. This is a one-paragraph edit that removes a falsifiable overclaim.
- **Add the word *supervisory*** (§4.2). It converts C3 from false-as-written to true, costs nothing,
  and pre-empts the sharpest objection any reviewer with a robotics background will raise.
- **Downgrade C4 or mark it explicitly as a hypothesis** (§7). It is currently stated as the source
  of the compounding, which makes it load-bearing; the evidence cannot carry that weight.

None of these is a build. All three are edits to a document that already exists, made while the
evidence is loaded — which is cheaper now than after a context rebuild.

### 8.3 What it costs to be wrong, in each direction

**If I am wrong to keep the constraint** (the second edge never comes, or comes in an unanticipated
shape): the cost is Fowler's cost of carry [S27], paid as review-time friction and the occasional
over-general abstraction. Bounded, visible, and reversible — an unused abstraction with one
implementation is a cheap deletion. **Estimated exposure: low.**

**If I am wrong to relax it** (the constraint is dropped and a second edge does arrive): the cost is
ROS 1's and Kubernetes' [S12][S13]. ROS 1's was unrecoverable — the project rewrote rather than
retrofit. Kubernetes' was recoverable at 1.5M lines [S12] and **roughly two dozen releases** — a span
this paper initially understated by about half (§2.3), which is worth flagging because the
correction moves in the direction that *strengthens* this branch of the asymmetry. Both
organisations were far better resourced than this one. **Estimated exposure: high, and the failure
is not visible until the second edge is already being attempted.**

**The asymmetry is the finding.** Not because the constraint is likely to pay off — §3 says its
central economic premise is unsupported — but because the two error costs are of different orders
and only one of them is reversible. That is an argument for keeping a *cheap* form of the constraint
(a review question) and refusing an *expensive* one (a built abstraction), which is exactly where
§6.4's table draws the line.

### 8.4 Where this paper is weak

- **Two regulatory claims are unverified and are NOT asserted.** ISO 10218-1:2025 (robot safety) and
  EU Machinery Regulation 2023/1230 Annex I Part A (which reportedly requires third-party conformity
  assessment for machinery with self-evolving/ML behaviour). Search method: iso.org standard page
  returned HTTP 403; the ISO OBP viewer is JS-rendered; the open-access ScienceDirect comparative
  analysis returned 403; the TÜV SÜD notified-body page returned 403; EUR-Lex CELEX 32023R1230 was
  fetched but the response truncated at Article 16, before the Annexes. **Only search-engine
  summaries and secondary commentary support these claims, so this paper does not rely on them.** If
  a robotics or industrial edge is ever seriously scoped, this is the first thing to research
  properly — it is plausibly the single largest cost item on such an edge and it is currently a
  blank.
- **[S18], [S19] and [S26] are cited bibliographically, not read.** Their abstracts were elided by
  the publisher in the Semantic Scholar response; the PDFs were unreachable (one returned raw binary
  the fetcher could not parse). No argument here rests on their internal content.
- **The nf-core peer-reviewed account [S16] could not be fetched** (BMC 301 → Springer 303 → IdP
  auth; bioRxiv and PMC returned 403/CAPTCHA). Figures circulating in search summaries (124
  pipelines as of Feb 2025; >2,600 contributors) are **not** used. The first-party site count of 155
  [S15] is used instead.
- **Home Assistant's integration tally is a tool-side count** of a large JSON document [S3], not an
  independent recount. Same for the OPC UA directory total (§2.1).
- **Survivorship bias runs through §2.** Every platform surveyed succeeded. Backbones that
  generalised and died leave no first-party design documents to fetch.
- **The single most important comparison is missing entirely:** a platform that started in one
  domain and *successfully* added a genuinely unrelated second domain on an unchanged core. I did
  not find one. Every case in §2 either stayed within a domain family (OPC UA: all industrial; Home
  Assistant: all home devices) or changed the core to accommodate (Kubernetes, ROS). **That absence
  is arguably this paper's most significant finding, and it is a gap rather than a refutation.**

  **Search method for that absence.** Platform survey scope — the candidates examined for §2, and
  what disqualified each: industrial/IoT integration layers (**OPC UA** — ~70 companion models, all
  industrial; **EtherCAT/ETG** — single-domain fieldbus); robotics middleware (**ROS 1 → ROS 2** —
  core rewritten; **micro-ROS** — protocol changed for the constrained edge); home-automation
  platforms with large integration counts (**Home Assistant** — ~1,000+ integrations, all home
  devices, with the device ontology *in* core); lab/scientific and bioinformatics automation
  (**Nextflow / nf-core**, **Snakemake**, **Galaxy**, **Cromwell/WDL** — domain-specific engines
  chosen over general ones); general workflow engines used across unrelated domains (**Temporal**,
  **Airflow**, **Camunda/Zeebe** — surveyed; each is domain-general at the *orchestration* layer and
  carries no domain ontology at all, which is why none of them is a counterexample: they do not have
  edges in the sense under test); and container/cloud platforms (**Kubernetes** — core changed, 1.5M
  lines extracted). Queries run: domain-agnostic core with domain-specific plugins as pattern vs.
  anti-pattern; what platform cores absorbed per domain; integration-layer architecture across
  industrial, robotics, lab and home automation; general-purpose workflow engines adopted across
  unrelated domains and their limits. **The disqualifying pattern is consistent enough to be a
  finding in itself: every platform that kept its core unchanged did so by staying inside one
  domain family.** What I cannot exclude is a case that exists but is not written up in first-party
  form — which is exactly the survivorship point above.

---

## 9. Test plan — what research cannot settle

Research got as far as it can on C1 and C2. The rest is experiment.

1. **Build the second edge small and early, and instrument the cost.** The only way to test C2 is to
   record hours-to-first-working-activity for edge 2 against the same measure for edge 1. Pick the
   cheapest possible non-coding edge (a home-automation edge against an existing Home Assistant
   instance is the obvious candidate — it has a first-party LLM API [S37], no safety regime, and no
   real-time constraint). **The experiment is worthless unless edge 1's number is recorded first.**
2. **Enumerate what the backbone had to change for edge 2, and classify each change** against §2.7's
   table (transport/lifecycle/record vs. ontology vs. timing envelope). If the changes land where
   §2.7 predicts, the model is validated cheaply. If they land in transport or lifecycle, C1 is in
   trouble.
3. **Write the irreversibility register for one real edge activity.** For a single physical action,
   document: the idempotency key, the read-back that detects a duplicate, and the compensation (or
   the explicit statement that there is none, per [S25]). Measure how long it takes. That number,
   times the number of activities, is the real per-edge cost that §3 could not find in the
   literature.
4. **Test the supervisory boundary explicitly.** Take one activity with a real deadline and measure
   end-to-end backbone latency (dispatch → worker → completion recorded). Compare against the
   domain's budget. This turns §4.2's argument into a number and settles where the boundary sits for
   *this* implementation rather than in general.
5. **Test C4 directly, and cheaply.** Give the assistant an unfamiliar domain platform plus this
   backbone, and measure task completion against the same assistant given the unfamiliar platform
   alone. That difference *is* "fluency in the backbone," operationalised. No published benchmark
   measures it [S33]–[S36]; this repo can measure it in an afternoon and would be the only source.
6. **Research handoff, not experiment:** the certification question (§8.4) needs a proper pass with
   paywalled-standard access before any industrial or robotics edge is scoped. Flag as a topic-list
   candidate, not as work for this cycle.

---

## 10. Citations

- **[S1]** OPC Foundation — *UA Companion Specifications*. https://opcfoundation.org/about/opc-technologies/opc-ua/ua-companion-specifications/ *(rendered first-party; quoted conservatively)*
- **[S2]** OPC Foundation — `UA-Nodeset` repository root listing (GitHub contents API, raw JSON). https://api.github.com/repos/OPCFoundation/UA-Nodeset/contents/
- **[S3]** Home Assistant — analytics data endpoint (raw JSON). https://analytics.home-assistant.io/data.json
- **[S4]** Home Assistant Developer Docs — *Devices and Services* (raw markdown). https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/architecture/devices-and-services.md
- **[S5]** Home Assistant Developer Docs — *Entity* (raw markdown). https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/core/entity.md
- **[S6]** Home Assistant Developer Docs — *Integration Manifest* / `iot_class` (raw markdown). https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/creating_integration_manifest.md
- **[S7]** Home Assistant — ADR-0004, *Webscraping* (raw markdown). https://raw.githubusercontent.com/home-assistant/architecture/master/adr/0004-webscraping.md
- **[S8]** Home Assistant — ADR-0011, *Discovery requires unique ID* (raw markdown). https://raw.githubusercontent.com/home-assistant/architecture/master/adr/0011-discovery-requires-unique-id.md
- **[S9]** Home Assistant — ADR-0022, *Integration Quality Scale* (raw markdown). https://raw.githubusercontent.com/home-assistant/architecture/master/adr/0022-integration-quality-scale.md
- **[S10]** Home Assistant Developer Docs — *Integration quality scale* (raw markdown). https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/core/integration-quality-scale/index.md
- **[S11]** Kubernetes — KEP-2395, *Removing In-Tree Cloud Providers* (raw markdown). https://raw.githubusercontent.com/kubernetes/enhancements/master/keps/sig-cloud-provider/2395-removing-in-tree-cloud-providers/README.md
- **[S12]** Kubernetes Blog — *Completing the largest migration in Kubernetes history* (2024-05-20). https://kubernetes.io/blog/2024/05/20/completing-cloud-provider-migration/
- **[S13]** ROS 2 Design — *Why ROS 2?* https://design.ros2.org/articles/why_ros2.html
- **[S14]** micro-ROS — *Micro XRCE-DDS* (raw markdown). https://raw.githubusercontent.com/micro-ROS/micro-ros.github.io/master/_docs/concepts/middleware/Micro_XRCE-DDS/index.md
- **[S15]** nf-core — *Pipelines*. https://nf-co.re/pipelines
- **[S16]** *Empowering bioinformatics communities with Nextflow and nf-core*, Genome Biology (2025), DOI 10.1186/s13059-025-03673-9. **Cited bibliographically only — full text unreachable (§8.4).**
- **[S17]** Colledanchise & Ögren — *Behavior Trees in Robotics and AI: An Introduction*, arXiv:1709.00084. https://arxiv.org/abs/1709.00084
- **[S18]** Böckle, Clements, McGregor, Muthig & Schmid — *Calculating ROI for software product lines*, IEEE Software 21(3), 2004. DOI 10.1109/MS.2004.1293069. Record retrieved via https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/MS.2004.1293069 — **abstract elided by publisher; not read.**
- **[S19]** Gregg, Scharadin & Clements — *The more you do, the more you save: the superlinear cost avoidance effect of systems product line engineering*, SPLC 2015. DOI 10.1145/2791060.2791065. Record retrieved via https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/2791060.2791065 — **abstract elided by publisher; not read.**
- **[S20]** SPLC — *Product Line Hall of Fame: Lockheed Martin*. http://splc.net/fame/lockheed-martin/
- **[S21]** Noonan, A. (Segment / Twilio) — *Goodbye Microservices: From 100s of problem children to 1 superstar*. https://www.twilio.com/en-us/blog/developers/best-practices/goodbye-microservices/ *(rendered vendor engineering blog)*
- **[S22]** EtherCAT Technology Group — *Technology*. https://www.ethercat.org/en/technology.html
- **[S23]** ROS 2 Design — *Proposal for Implementation of Real-time Systems in ROS 2*. https://design.ros2.org/articles/realtime_proposal.html
- **[S24]** Temporal — *Activity Definition* (idempotency, retries, execution semantics). https://docs.temporal.io/activity-definition
- **[S25]** Microsoft Azure Architecture Center — *Compensating Transaction pattern*. https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction
- **[S26]** Garcia-Molina, H. & Salem, K. — *Sagas*, ACM SIGMOD 1987. DOI 10.1145/38714.38742. Record retrieved via https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/38714.38742 — **abstract elided; PDF unparseable; cited bibliographically only.**
- **[S27]** Fowler, M. — *Yagni* (bliki). https://martinfowler.com/bliki/Yagni.html
- **[S28]** Fowler, M. & Beck, K. — *Refactoring* 2nd ed., "Speculative Generality", as excerpted at InformIT. https://www.informit.com/articles/article.aspx?p=2952392&seqNum=15 *(publisher excerpt — corroborated secondary)*
- **[S29]** Glass, R. — *Facts and Fallacies of Software Engineering*, Fact 18, as quoted verbatim at Coding Horror, *The Rule of Three*. https://blog.codinghorror.com/rule-of-three/ *(secondary reproducing a book passage)*
- **[S30]** Brooks, F. — *The Mythical Man-Month* (Anniversary Ed., 1995), p. 55, as reproduced at Wikiquote. https://en.wikiquote.org/wiki/Fred_Brooks *(sourced-quotation site; book not fetched)*
- **[S31]** Aryabumi et al. — *To Code, or Not To Code? Exploring Impact of Code in Pre-training*, arXiv:2408.10914. https://arxiv.org/abs/2408.10914
- **[S32]** Fakih, Dharmaji, Moghaddas, Quiros Araya, Ogundare & Al Faruque — *LLM4PLC: Harnessing Large Language Models for Verifiable Programming of PLCs in Industrial Control Systems*, arXiv:2401.05443. https://arxiv.org/abs/2401.05443
- **[S33]** Yao, Shinn, Razavi & Narasimhan — *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains*, arXiv:2406.12045. https://arxiv.org/abs/2406.12045
- **[S34]** Xu et al. — *TheAgentCompany: Benchmarking LLM Agents on Consequential Real World Tasks*, arXiv:2412.14161 (v3, 2025-09-10). https://arxiv.org/abs/2412.14161
- **[S35]** Seo, Yang, Pyo, Kim, Lee & Jo — *SimuHome: A Temporal- and Environment-Aware Benchmark for Smart Home LLM Agents*, arXiv:2509.24282. https://arxiv.org/abs/2509.24282
- **[S36]** Li et al. — *SMH-Bench: Benchmarking LLM Agents for Environment-Grounded Reasoning and Action in Smart Homes*, arXiv:2606.01912. https://arxiv.org/abs/2606.01912
- **[S37]** Home Assistant Developer Docs — *LLM API* (raw markdown). https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/core/llm/index.md
- **[S38]** Bharadwaj, Liu, Yang, Kim, Verma, Kim, Ferreira & Kim — *PersonalHomeBench: Evaluating Agents in Personalized Smart Homes*, arXiv:2604.16813. https://arxiv.org/abs/2604.16813 *(cited only in §7.3's search method, as a search-surfaced benchmark; no claim in this paper rests on its results)*

**Source count: 38 cited; 34 fetched and verified, 4 ([S16], [S18], [S19], [S26]) cited
bibliographically with their unreachability stated at the point of use.**

**Adjacent pool papers referenced (not counted above):**
[`durable_execution.md`](durable_execution.md) (last validated 2026-07-27, Critic: PASS) —
the substrate whose contract §4 tests against physical actuation;
[`hierarchical_agents.md`](hierarchical_agents.md) (2026-07-25, PASS);
[`workflow_reuse_boundary.md`](workflow_reuse_boundary.md) (2026-08-03, PASS-WITH-FIXES) — the
within-domain counterpart to this paper's cross-domain question.
