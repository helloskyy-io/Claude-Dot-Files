# bernstein_capability_mining

```
Topic:          What does `bernstein` — a shipping product, not a paper — ship that this repo does
                not, and what would each capability cost us to build?
Feeds:          docs/development/roadmap.md — new items across phases (named per capability in §5);
                docs/standards/architecture/problem-statement.md § "The nearest neighbor" (what the
                reference material actually contains), and § "Where we actually differ" #1 and #2
                (both re-checked against current docs — see §0, one of them moved).
Last validated: 2026-08-04
Revalidate:     high — 2 weeks
Confidence:     DEFINITIVE on repository-level scalars fetched from APIs (default_branch, stars,
                pushed_at, licence, PyPI upload timestamps, CRD field values) and on SMALL directory
                listings, which were verified exactly. NOT definitive — and withdrawn from this
                paper — on counts taken from LARGE directory listings: enumerating a long JSON array
                is the one operation §1.3 shows the fetch layer handling badly, and §1.4 states the
                withdrawal.
                DEFINITIVE-AT-DOCUMENTATION-LEVEL and UNVERIFIED-AT-BEHAVIOURAL-LEVEL on every
                capability: all of it comes from bernstein's own docs, nothing was executed, and
                bernstein itself documents that its docs lag its code (§7.2). DERIVED — and the
                paper's contribution — on the capability ranking, on every cost estimate (§5), and
                on the two-test split of architecture-fit vs. capability-worth. See §1.3 for a
                measured sourcing failure caught in this cycle's own evidence-gathering and what it
                costs the quote-level claims.
Negative:       Six findings of absence, each with its search method: no controller documented for
                the shipped CRDs (§4.9); no cross-organisation federation (§0.2); no non-coding use
                case in the user-facing use-case list despite five shipped modalities (§0.1); ADR
                002 absent from the decisions directory (§7.4); lesson filing still unwired
                (§4.11); no trace of anything resembling differentiator #3 (§0.3).
Critic:         PASS-WITH-FIXES (ADR-005 spawn-overhead unit corrected per-batch→per-spawn and the
                amortization argument rebuilt; summarizer-derived docs/ and repo-root listing counts
                withdrawn; §5 cost-S tally corrected nine→eight with rows enumerated; §1.3 and its
                echoes reworded from fabrication to summarizer truncation; §0.1 headline splice
                marked and both spans re-verified) — 2026-08-04
```

> **Read §0 first.** One of the two differentiators this paper was asked to re-check has moved. That
> is the headline, it is reported plainly per the dispatch, and it is good news under the stated
> strategy — but a planner who reads only §5 will miss it.

---

## 0. The two differentiator checks, answered first

The problem statement marks differentiator #1 *"confirmed absent from the nearest neighbor, three
independent ways"* and differentiator #2 *"confirmed different."* Both were re-checked against
bernstein's current documentation on 2026-08-04.

### 0.1 Differentiator #1 — "the backbone is domain-general; the edge is what changes" — **NARROWED, and this is the headline**

**The claim as written is no longer safe.** bernstein ships a typed activity boundary that admits
non-coding modalities as first-class citizens of the same scheduler.

`docs/operations/activity-boundary.md` states that "The typed activity boundary is the one contract a
non-coding modality -- research, browser/computer-use, data, ops -- participates through as a
replayable step" and that "every activity returns an artifact plus the hashes needed to replay it"
*(two spans from the source, joined here for readability — they are not one sentence)*. It names the
modality set as "research / browser / data / ops / coding," and requires that "every modality returns
an `ActivityResult`" carrying kind,
artifact, artifact_hash, evidence_set_hash, terminal_state and reason_code [S14].

Two of those modalities have their own shipped documentation, and both are verified by something
that is *not* "tests pass":

- **Research.** "The research modality produces a **sourced report** whose every claim is bound to
  the exact bytes it was derived from"; "A research report here is not prose with links; it is a
  citation-lineage artifact"; verification "re-hashes them to detect an altered source, and confirms
  the quoted span still occurs in them" [S12]. No git repository is required.
- **Browser.** "The browser modality runs **site checks and UI flows** as first-class activities: an
  operator schedules 'check the deployed page after this merge' or 'walk the signup flow' with the
  same scheduler, budgets, and audit guarantees a coding task gets"; verification "reattaches the DOM
  bytes by hash and **re-evaluates** the assertion" [S13].

*(Confidence: definitive at documentation level. Quoted spans are §1.3-class quoted spans from raw
first-party markdown.)*

**What survives, stated precisely, because the nuance is the actionable part.** bernstein's
*positioning* is still entirely code-framed while its *execution boundary* is already
modality-general:

| Surface | What it says | Source |
|---|---|---|
| GitHub repo description | "Deterministic orchestrator for CLI coding agents (Claude Code, Codex, Gemini CLI, +40 more)." | [S1] |
| `docs/index.md` front door | "Deterministic orchestrator for CLI coding agents. No model in the coordination loop, so parallel runs in per-task git worktrees replay byte-identically." | [S38] |
| `docs/use-cases.md` | Six use cases, all software-development: parallel test generation, CI failure repair, PR review follow-up, codebase modernization, ticket-to-run, API-change safety checks. **The fetch found no non-code use case**, noting only a passing mention of "teams whose pipeline also produces non-code deliverables (a report, a dataset, an ops result)". | [S11] |
| `docs/operations/activity-boundary.md` | five modalities, four of them non-coding, one typed result contract | [S14] |

**DERIVED, from [S1] + [S11] + [S12] + [S13] + [S14] + [S38]:** the honest restatement of
differentiator #1 is no longer *"comparable systems are built for code"* — it is **"comparable
systems are *sold* for code, and the nearest one has already generalised its execution boundary
without generalising its product."** That is a much weaker differentiator and a much better piece of
reference material: the design we were going to have to invent has a shipped, documented shape we
can read. §4.1 treats it as capability #1.

**Search method for the negative half** (no non-coding use case in the user-facing list): fetched
`docs/index.md` and `docs/use-cases.md` raw and asked for enumeration plus explicit statement if all
were code-centric; cross-checked against the repo description from the GitHub API and against the
full mkdocs `nav:` tree [S2], which files research/browser activities under "Architecture &
internals → Orchestration internals", not under "Guides" or "Use cases".

### 0.2 Differentiator #2 — "edges are dedicated and non-fungible" — **CONFIRMED STILL DIFFERENT**

bernstein remains a central-queue, role-advertising, claim-and-contend design, and its multi-instance
story stops well short of the federated destination.

- **Role-pull with force-claim.** Work is pulled: `GET /tasks/next/{role}`; tasks declare `"role":
  "backend"`; contention is resolved by an explicit `POST /tasks/{id}/force-claim` recorded on the
  audit chain with `release_path: force_claim`. The only claim-time restriction documented is a
  dependency rule — "The claim API never offers a task whose dependencies are not all in a
  terminal-success state (`done` or `closed`)" [S9].
- **Pools bound concurrency, not workers.** Named resource pools are "Lease-backed admission control
  - concurrency-limited pools, per-tag ceilings, adaptive rate limits, and priority queues"; the
  fetch found **no statement** binding a pool to particular workers or hosts [S10].
- **Fleet is a trusted-operator reader, not a federation.** "`bernstein fleet` is a supervisory
  dashboard that aggregates state from multiple Bernstein projects into a single view"; the
  aggregator "is purely a fan-out reader plus a dispatcher for bulk actions"; and the limit is stated
  outright: **"Fleet mode is multi-project, **not** multi-tenant in the security sense. Every task
  server it queries is assumed to be run by the same operator, on a network the operator trusts"**
  [S25].
- **"Federation" means multi-tracker, not multi-site.** "The federation layer lets one Bernstein
  orchestrator instance pull tickets from Linear, GitHub Projects, Jira, Notion, etc. in a single
  run"; the v1 limitation list explicitly includes **"Cross-tenant federation across organisations"**
  [S8].

*(Confidence: definitive at documentation level.)*

**DERIVED, from [S8] + [S9] + [S10] + [S25]:** differentiator #2 holds, and it holds for a *larger*
reason than the problem statement claims. Not only is the worker model fungible-by-role — the
cross-instance model is explicitly single-operator and single-trust-domain. **SkyyNet's destination
— many MDCs, distinct operators, distinct trust domains — is outside bernstein's shipped scope by
its own documentation.** This is the strongest position in the comparison and it should be stated in
the problem statement in these terms rather than as a scheduling-model difference.

### 0.3 Differentiator #3 — "the first edge builds the others, then operates inside them"

**Not checked as a claim, and no trace found.** Search method: full enumeration of the mkdocs `nav:`
tree [S2] (hundreds of page entries across the whole doc set) and of the `docs/` root listing [S3],
scanning for any self-construction, bootstrapping, or edge-authoring concept. The
nearest neighbours in the tree are `decisions/003-self-evolution.md` (policy self-tuning, §4.12) and
`concepts/scaffold.md` ("Prompt-to-repo scaffold", not fetched). Neither is the claim. **This is an
absence in the nav enumeration, not a verified absence in the product** — the nav is the strongest
enumeration available without cloning, and it is what this negative rests on.

---

## 1. Primer — what this paper is, and how to read a claim in it

### 1.1 The frame

The novelty question is closed. `problem-statement.md` states the intent as *"to execute it better
than anyone else, and to acquire the lessons rather than re-learn them"* and names bernstein as
reference material. **A finding that bernstein does something better is a win.** This paper is an
inventory and a price list, not a defence.

### 1.2 The two independent tests, applied to every capability

Every capability below is scored twice, and the scores are deliberately allowed to disagree:

- **(a) Is the architecture right for us?** Usually not. Our durability comes from Temporal; theirs
  comes from a local WAL and file-based state. We are not Kubernetes-native. This question is close
  to settled and is answered briefly.
- **(b) Is the capability, interface or lesson worth taking?** Independent, and frequently **yes**
  even when (a) is a hard no. Rejecting on (a) and skipping (b) is how a project re-learns
  expensively what someone already published.

### 1.3 What "quoted" means in this paper — a measured failure from this cycle

Every span in quotation marks below was returned **inside quotation marks by a fetch of a raw
first-party source** (`raw.githubusercontent.com`, `api.github.com`, `pypi.org/pypi/.../json`). The
fetching layer summarises surrounding structure even when the underlying bytes are raw markdown, so
the Research Standard's strict verbatim bar is **not** claimed for these spans. They are marked
**quoted-span (raw source)** — strong evidence, one notch below verbatim.

That distinction is not theoretical. **In this cycle, a summarising fetch of
`https://pypi.org/pypi/bernstein/json` returned a partial release list that read as a complete
history and was wrong as one** — a tidy run of releases dated across early-to-mid May 2026,
presented as the package's latest state. Narrow re-fetches of the per-version endpoints returned
`bernstein-3.13.0-py3-none-any.whl` at `2026-08-01T16:45:04.125536Z`, `3.12.0` at
`2026-08-01T01:50:29.983811Z`, and `3.0.0` at `2026-07-06T20:08:52.892817Z` [S43][S44][S45]. **The mechanism is most likely truncation rather than invention:** a re-fetch of the
same endpoint returned a much longer, plausible history whose 1.10.x line does cluster in that May
window, so the summariser appears to have surfaced a genuine subset of a long array and presented it
as the whole. That is a milder failure than fabrication and it is stated as the milder one — but it
is *indistinguishable from fabrication at the point of use*, which is the whole reason the rule
below exists. Every numeric claim in this paper that mattered was re-fetched through the narrowest
endpoint that could carry it.

### 1.4 Coverage — stated as a limit, not smoothed over

The prior cycle read 12 files. This cycle read **~35 additional first-party files** — 13 `docs/`
subdirectories were touched, plus 4 root-level doc files, the Helm chart, the CRDs and six
contents-API listings. **No denominator is stated for that coverage, deliberately.** An earlier draft
gave one ("13 of 58 directories", "88 entries"); those figures came from a *summarizing* fetch
counting a long JSON array, which is the single operation §1.3 shows this fetch layer handling badly,
and a re-fetch of the identical endpoint returned a materially different tally. **The counts are
therefore withdrawn rather than corrected** — the git trees API is the reliable enumeration method
and this cycle did not use it. What is safe to say is qualitative and sufficient: the mkdocs `nav:`
[S2] enumerates hundreds of pages, **the large majority of bernstein's documentation remains
unread**, and this paper is a broad sweep, not an exhaustive audit. Directories with zero coverage
across both cycles include `gui/`, `mcp/`, `compliance/`, `trackers/`, `integrations/`, `protocols/`,
`sandbox/`, `skills/`, `testing/`, `memory/`, `lineage/`, `api/`, `interop/`, `benchmarks/`, `blog/`,
`events/` and `planning/` — that list is read off the nav tree, not off a count.
`docs/CHANGELOG.md` was **not** read; `release-notes/unreleased.md` and `release-notes/v3.13.0.md`
were read instead as the highest-density recent-defect seam.

**Direction of the error, stated because it matters to a consumer:** the withdrawn denominator
*understated* this paper's own coverage. No claim in §4 or §5 is inflated by it; only the honesty
bound was mis-sized.

---

## 2. What the subject is, verified

| Fact | Value | Source |
|---|---|---|
| `default_branch` | `main` | [S1] |
| Licence | `Apache-2.0` | [S1][S42] |
| Stars | 788 | [S1] |
| Created / last push | `2026-03-22T14:52:26Z` / `2026-08-04T19:26:33Z` | [S1] |
| Forks / open issues / watchers | 93 / 76 / 9 — the last is `subscribers_count`, which is what GitHub's UI labels "Watching"; the API's `watchers_count` field is a duplicate of the star count | [S1] |
| Language, PyPI version, Python floor | Python, `3.13.0`, `>=3.12` | [S1][S42] |
| Release cadence, **measured** | `3.0.0` 2026-07-06 → `3.13.0` 2026-08-01: **13 minor releases in 26 days**, two of them (`3.12.0`, `3.13.0`) on the same calendar day | [S43][S44][S45] |

*(Confidence: definitive — all scalars from JSON API endpoints, the version timestamps re-fetched
per §1.3.)*

**The cadence figure sets this paper's revalidation interval.** §5 of the Research Standard puts
product feature inventories in the high tier at 2–6 weeks; a subject shipping a minor release every
other day takes the **floor of the band: 2 weeks**. The specific decay risk is §0.1 — one release
that reframes the product around its own activity boundary would change this paper's headline.

**Single-maintainer concentration is a standing risk, and it is now partly corroborated by the
project's own release notes:** `v3.13.0` describes a distribution pipeline in which "The npm wrapper
had been failing inside a green job since 2.3.0" and the RPM channel "had shipped nothing since
1.4.11" [S17]. A project with more independent operators would likely have caught either. *(derived
from [S17]; the "one maintainer" figure itself was supplied by the dispatch and is **not**
independently verified here — commit-author analysis was not run.)*

---

## 3. Comparative landscape — where else each capability could come from

A capability worth having is not automatically worth building. For every item in §4 the honest
alternatives are: **take bernstein's design**, **buy it from the substrate**, **adopt a standard**,
or **do without**. The table below is the buy-side that §5's costs are netted against.

| Capability class | Bought from the substrate we have already chosen | Available as a published standard | Verdict |
|---|---|---|---|
| Retries, backoff, timers, heartbeats, at-least-once activities | **Temporal** — established in `raw/durable_execution.md` and `raw/temporal.md` | — | **Buy.** Do not port bernstein's WAL. |
| Crash-resume of orchestration state | **Temporal** event history | — | **Buy.** |
| Metrics / traces | — | **OpenTelemetry.** (Note: GenAI semantic conventions have relocated — the OTel semconv repo's `docs/gen-ai/README.md` now says only "GenAI semantic conventions have moved to the OpenTelemetry GenAI semantic conventions repository" [S47], so the agent-span vocabulary is a moving target and should be tracked, not forked.) | **Adopt.** bernstein's own stack is exactly this: Prometheus at `/metrics`, OTLP/gRPC canonical, presets for "Jaeger, Grafana Tempo, Datadog, Zipkin, and console" [S37]. |
| Workload identity for an edge | — | **SPIFFE** — "A SPIFFE Identity (or SPIFFE ID) is defined as an RFC 3986 compliant URI comprising a 'trust domain name' and an associated path" [S46] | **Adopt-when-needed.** bernstein treats SPIRE the same way: "This is an optional integration profile. The self-contained Ed25519 path stays the default" [S26]. |
| Typed completion / typed refusal at a worker boundary | Temporal gives you a typed *result*; it does not give you a **closed refusal taxonomy** | — | **Build, from bernstein's design.** §4.2. |
| A closed machine-readable failure vocabulary | Temporal gives failure *types*, not domain reason codes | — | **Build, from bernstein's design.** §4.3. |
| Tamper-evident audit chain over decisions | Temporal history is durable but not adversarially tamper-evident | in-toto / DSSE (bernstein ships an envelope for this per the nav [S2]; not fetched) | **Defer, with a priced design.** §4.5. |
| Worker lifecycle policy (how long an agent lives) | Nothing supplies this | — | **Take the lesson free.** §4.4. |

**The single most important line in that table:** the four capabilities we would otherwise be tempted
to build — durable retry, resume, event history, backoff — are the ones we are already buying. Every
capability in §4 that survives is one Temporal does *not* provide. That is what makes the mining
exercise worth its cost. *(DERIVED from the table's own rows plus `raw/durable_execution.md` and
`raw/temporal.md`.)*

---

## 4. What bernstein ships that we do not — ranked, with costs

**Cost units** (derived; the basis is stated per item, and the shared basis is that this repo is bash
workflow scripts, markdown agents/skills, and GitHub as memory, with no server and no daemon
[system-overview.md]):

- **S** — one dispatch, hours. A schema plus a validator plus a handful of call sites in files that
  already exist.
- **M** — two to four dispatches. A new shared module under `scripts/workflows/common/` or
  `activities/`, changes across every workflow, plus docs and standards updates.
- **L** — a roadmap phase. Requires the Temporal substrate, a new service, or a persistent store that
  does not exist today.

Ranking is by *value per unit cost against the federated destination*, not by how impressive the
capability is.

---

### TIER 1 — take these; they are cheap and they survive the "would this make sense if the edge were a building controller?" test

---

#### 4.1 The typed activity boundary — one result contract, many modalities `[Tier 1 · cost M]`

**What it is.** One typed boundary through which every modality — coding, research, browser, data,
ops — returns the same shape. "every modality returns an `ActivityResult`" with kind, artifact,
artifact_hash, evidence_set_hash, terminal_state, reason_code; new modalities must satisfy "Schema
validation" and "Evidence pinning"; and the audit chain mirrors "only hashes, the kind, the terminal
state, and the reason code -- never the artifact body or the fetched evidence" [S14].

**One rule inside it is worth the whole section:** "the scheduler refuses to add a stage whose
`evidence_set_hash` equals a prior stage's" [S14]. That is a **no-new-evidence stop condition**,
enforced structurally rather than by a model's judgement — a loop that has learned nothing cannot
proceed. It is the sharpest mechanism found anywhere in this sweep, and it directly answers a
question `raw/convergence_stopping.md` left open.

**Why it matters for the federated destination.** This *is* differentiator #1, built. A backbone that
carries `ActivityResult` rather than `PullRequestResult` is a backbone a building-controller edge can
join without changing. Our workflows currently route on a parsed completion token — a string — which
is a coding-shaped contract wearing a general name.

**Evidence.** [S14], corroborated by two shipped non-coding modalities [S12][S13]. *(definitive at
documentation level; unverified behaviourally.)*

**(a) Architecture right for us?** Partly. Their boundary is enforced by their scheduler; ours would
be enforced by a Temporal activity signature. The *shape* transfers; the enforcement point differs.
**(b) Worth taking?** **Yes — highest-value item in this paper.**

**Cost: M.** Derived from: a Python dataclass or TypedDict plus a validator (S), plus retrofitting
every workflow's final-output contract to emit it (the expensive half — `workflow-scripts.md`'s
completion-contract rule touches every parent and child script). **Depends on** the Phase: Temporal
Integration language decision (Python, decided 2026-08-03), and is cheapest if done *as* that port
rather than before it. **Roadmap home:** `Phase: Temporal Integration`, plus a
standards-amendment candidate against `workflow-scripts.md § Composition`.

---

#### 4.2 Typed completion **and typed refusal** with a closed taxonomy `[Tier 1 · cost S]`

**What it is.** "The completion contract defines the two closed terminal shapes a worker may submit at
the completion API boundary: a **completion** or a typed **refusal**." Completion carries
`contract: worker-completion/v1`, a required `summary` (non-empty, max 2000 chars), optional
`files_changed`, optional `verification` (command + exit code), optional `receipt_ref`. Refusal is
the interesting half: "A worker that cannot proceed submits a typed refusal instead. The `kind` is a
**closed** taxonomy - there is deliberately no catch-all" — four kinds, each with a required field:
`awaiting_operator` (question), `underspecified` (question), `scope_exceeded` (proposed_split, non-empty
list), `blocked_on_dependency` (blocking_dep). And the enforcement: "A payload that fails validation
auto-fails the task with `terminal_reason='contract_violation'`, releasing the worker slot
atomically" [S30].

**Why it matters for the federated destination.** We already have completion contracts — that is the
one place this repo is genuinely level. **We do not have typed refusal.** Today a workflow that
cannot proceed either invents prose or fails, and a parent cannot branch on *why*. In a fabric where
a parent may be on a different machine from the edge that refused, "I need an operator" and "this is
bigger than one task, here is the split" must be different values, not different sentences. Every one
of the four kinds is domain-general — none mentions code.

**The design lesson inside it is "no catch-all."** A refusal taxonomy with an `other` bucket collapses
into `other`.

**Evidence.** [S30]. *(definitive at documentation level.)*

**(a) Architecture right for us?** Yes, unusually — this is an API-boundary contract, substrate-neutral.
**(b) Worth taking?** **Yes, and it is the cheapest high-value item here.**

**Cost: S.** Derived from: our completion contracts are already pattern-matched strings emitted by
child workflows; adding four refusal shapes is a documented enum plus a parser plus a parent-side
branch. **Depends on** nothing. **Roadmap home:** `Phase: Workflow Decomposition` (the parent/child
contract), with a standards-amendment candidate against `workflow-scripts.md`.

---

#### 4.3 A closed-set machine-readable failure taxonomy `[Tier 1 · cost S]`

**What it is.** Failures are posted as a YAML block tagged `bernstein-failure-v1` with fields
`reason_code` ("Closed-set machine code"), `category` ("Broader bucket from `FailureCategory`"),
`transient` ("True when retry is likely to recover"), `next_action` ("Short imperative hint (`retry`,
`escalate`, `page_oncall`, ...)") and `evidence_path` ("Relative path to a log or trace file, or
`""`"). Fourteen reason codes are enumerated, including `timeout`, `rate_limit`, `network_error`,
`sandbox_violation`, `flaky_test`, `scope_violation`, `merge_conflict`, `context_miss` and `unknown`.
Consumers must "treat unrecognised codes as `unknown` and fall back to the default escalation policy"
[S6].

**Why it matters for the federated destination.** `transient` and `next_action` are the two fields
that let a *parent* — or a central planner — act without reading prose. Across many edges, a human
cannot read every failure; the vocabulary has to be closed and versioned. Roughly half the codes are
coding-specific (`merge_conflict`, `compile_error`), which is exactly the right split: the *envelope*
is domain-general, the *code set* is per-edge. That is a worked example of §2.7 of
`raw/backbone_edge_generality.md` — ontology at the edge, envelope in the core.

**Evidence.** [S6]. *(definitive at documentation level.)*

**(a) Architecture right for us?** Yes. **(b) Worth taking?** **Yes.**

**Cost: S.** Derived from: a versioned schema plus an emitter in the workflow error paths plus a
consumer in `review-pr`. The forward-compatibility rule (unknown codes → `unknown`) is one line and
prevents the version-skew failure the taxonomy would otherwise cause. **Depends on** 4.2 (share the
enum discipline; do them in one dispatch). **Roadmap home:** `Phase: Continuous Process Improvement`
(the run-log analysis consumes it) and `Phase: Workflow Decomposition`.

---

#### 4.4 The short-lived-worker lifecycle — the measured lesson `[Tier 1 · cost S for the policy, free for the lesson]`

**This is the most valuable *lesson* in the sweep**, because it is a design bernstein **changed after
measuring the failure**.

**What failed.** ADR-005 records a pilot of 12 agents over multiple days on a persistent-session
model, and three failure modes:

- **Agents stopped taking work.** "Anti-sleep instructions in the system prompt ("NEVER sleep, NEVER
  stop") did not reliably prevent this."
- **Signalling ate the budget.** "The worst-case agent produced 283 bulletin messages, the vast
  majority being idle status reports. Zero code commits. ~50,000 tokens consumed on signaling rather
  than work."
- **Context confusion.** "After hours of operation, agents confused their own work with others' (one
  agent claimed credit for the manager agent's commits), accumulated stale context, and degraded in
  output quality."

Only 3 of 12 agents proved reliable [S20].

**What replaced it.** "Agents are short-lived. They spawn with a batch of 1–3 tasks, execute them
sequentially, and exit cleanly." Pure single-task spawning was rejected because the ADR prices
context loading **per spawn**, not per unit of work — "With many tasks and ~3–5K tokens per spawn for
context loading, pure pull accumulates significant spawn overhead" — so batching 2–3 related tasks
"amortizes spawn cost and preserves useful context." **The batch cap exists because the two costs
pull in opposite directions:** per-spawn context loading rewards larger batches, and context staleness
punishes them. Two hard safeguards: "Agents are killed after a configurable wall-clock
limit (default: 30 minutes) regardless of claimed progress," and a batch cap of "1–3 tasks. Above 3,
context accumulates enough stale information that the agent's performance degrades measurably"
[S20].

**Corroborated independently inside the same repo.** `architecture/orchestration-approaches.md`
describes the LLM-manager failure as one where "the LLM manager stalls and every queue drains behind
it, workers spin on idle 'hunger' signals instead of committing code, and phantom agents spawned
without identity flood the bus with noise," and states the replacement as "Agents are born with work
and die when done. There is no idle state, no hunger state, no polling loop" [S24].

**Why it matters for the federated destination.** Nothing in this lesson is about code. It is about
what a worker *is*: a bounded unit of work with a wall-clock kill, not a resident process with a
mailbox. The problem statement's edge — "a machine with a capability and a credential, running a
worker that speaks the backbone's protocol" — is silent on lifetime, and the temptation when standing
up a Temporal worker is exactly the long-lived-agent design that failed here. **This paper's single
most transferable finding is that the resident-agent design was tried, measured, and abandoned by the
nearest neighbour.**

**Evidence.** [S20], corroborated by [S24]. *(definitive at documentation level for the ADR's
contents; the pilot's numbers are **bernstein's self-reported measurements**, not independently
reproduced — treat as first-party-reported, not as a published result.)*

**(a) Architecture right for us?** Yes, and it happens to match what we already do: workflow scripts
spawn `claude -p` and exit. **We are accidentally correct here, and should make it deliberate.**
**(b) Worth taking?** **Yes — as an explicit, written policy plus a wall-clock kill.**

**Cost: S.** Derived from: the lesson is free; the enforceable part is a wall-clock timeout on every
dispatch and a documented statement that workers do not idle. We already have per-run isolation and
no daemon, so this is a guard, not an architecture. **Depends on** nothing. **Roadmap home:** a
standards-amendment candidate against `workflow-scripts.md`, and an explicit constraint recorded in
`Phase: Temporal Integration` before workers are designed.

---

#### 4.5 Hash-chained audit with a **priced** overhead and an offline verifier `[Tier 1 for the price, Tier 2 for the build · cost M]`

**What it is.** A hash-chained append-only audit log, benchmarked, with the decision to keep it opt-in
recorded as an ADR. The measurements: "The chain adds roughly 50 us on top of a plain log write";
"The chain adds a fixed **+157 B/entry**"; verification runs at "~72-75k events/s, flat across total
events and segment count." The conclusion: "Append overhead is sub-millisecond and byte overhead is a
constant 157 B/entry." The decision: "Keep the chain opt-in in this release. Adopt on-by-default as
the target once the migration steps below are in place," because "the reason not to flip the default
inside a measurement change is scope and operational rollout (key generation on existing installs),
not performance" [S21].

**Why it matters for the federated destination.** Across MDCs with distinct operators, "what did that
edge actually do" needs to be answerable by someone who does not trust the edge. Temporal's history
is durable but is not an adversarial tamper-evidence story.

**The lesson is the ADR shape, not the chain.** bernstein measured the cost *before* deciding, then
declined to flip the default for an operational reason, and wrote down which reason it was. That is
the discipline our own standards-governance path is supposed to produce.

**Evidence.** [S21]. *(definitive at documentation level for the decision and the quoted figures;
the benchmark itself was not reproduced — **the numbers are bernstein's, on bernstein's hardware, for
bernstein's entry sizes**, and should be treated as an order-of-magnitude anchor, not as our number.)*

**(a) Architecture right for us?** Not directly — theirs chains a local JSONL WAL that we are not
building. **(b) Worth taking?** **The price and the decision shape: yes, now, free. The chain
itself: later.** The +157 B/entry figure is what makes "should we hash-chain the decision log?"
answerable without an experiment.

**Cost: M** if built (a canonicalisation rule, a key story, a verifier, and a migration path — the
ADR names key generation on existing installs as the blocker, and that is precisely the part that is
not free). **Cost: 0** to take the number and the decision shape today. **Depends on** a persistent
decision log existing, which today is GitHub PR threads. **Roadmap home:** `Phase: Memory Management
Framework`.

---

#### 4.6 Evidence-hash verification — proving a claim still matches its source `[Tier 1 · cost S–M]`

**What it is.** In the research modality, every claim carries a citation record with `claim_id`,
`quote`, `source_ref` and `page_content_hash`; `bernstein activity verify <run>` "resolves every
citation from the content store alone", "re-hashes them to detect an altered source, and confirms the
quoted span still occurs in them", with exit codes distinguishing verified / missing / tampered; and
"A report with an **uncited** claim never reaches the journal" [S12]. The browser modality does the
same for DOM bytes: verification "reattaches the DOM bytes by hash and **re-evaluates** the
assertion", and "The check touches only the content store, so it holds with the network disabled"
[S13].

**Why it matters for the federated destination — and immediately, here.** This repo runs a
research-critic that re-fetches citations by hand. bernstein has mechanised the same idea: store the
bytes, hash them, re-check the quoted span offline. It is domain-general (any edge that makes a claim
about the world can pin the bytes it claimed from), and it is the direct mechanical answer to §1.3's
truncation failure.

**Evidence.** [S12][S13]. *(definitive at documentation level.)*

**(a) Architecture right for us?** Yes — content-addressed storage plus a verify command is
substrate-neutral. **(b) Worth taking?** **Yes.**

**Cost: S–M.** Derived from: S for the narrow version — a fetch-cache that stores raw bytes plus
sha256 per URL, and a verifier that re-checks each quoted span against the stored bytes. M for the
full lineage artifact. **Depends on** somewhere to put the bytes (a cache dir is enough for S).
**Roadmap home:** the research workflow tooling (`research-critic`), and `Phase: Continuous Process
Improvement`. **This is the item with the shortest path from "read about it" to "we are using it."**

---

### TIER 2 — real capabilities, right for the destination, but they need a substrate or a surface we do not have yet

---

#### 4.7 Intent capsules — binding what a worker *did* to what an operator *approved* `[Tier 2 · cost M]`

**What it is.** "An intent capsule compiles the approved goal into a canonical, signed chain entry and
binds the running worker's action stream to it, so scope drift is caught at the first divergence
rather than during a post-hoc journal review." It carries task/plan identifiers, a digest of the
approved goal, permitted capability surfaces, file-write scopes, adapter allowlists, egress
permissions, cost references, and an expiry. "The capsule is written to the HMAC audit chain as an
`intent.capsule` event, and its hash is bound into the run journal (`intent.capsule_bound`), so every
subsequent journal step is attributable to one approved capsule" [S32].

**The problem statement it opens with is the finding:** "Nothing bound the running worker's action
stream to the goal the operator actually approved. Post-hoc journal review does not scale to fleets,
and 'the run finished green' says nothing about whether the actions taken were the actions
authorized" [S32].

**Why it matters for the federated destination.** Our autonomous runs pass
`--dangerously-skip-permissions`, and `system-overview.md § Safety` states plainly that the
`PreToolUse` hook is the only control operating during a run — worktree isolation bounds blast
radius and PR review is after the fact. **That is precisely the gap the capsule closes, and bernstein
wrote our problem statement better than we did.** At fabric scale, with an operator per MDC, post-hoc
review does not scale, exactly as quoted.

**Evidence.** [S32]. *(definitive at documentation level.)* Note the same feature appears in the
unreleased notes as a **reversal**: intent-conformance verification "took the run to verify from the
unsigned on-disk capsule record" and was changed to read from the signed audit entry [S18]. Reading
your own authorisation record from an unsigned local file is a real bug class and the correction is
worth having for free.

**(a) Architecture right for us?** Partly — signing and chaining assume the audit chain of §4.5.
**(b) Worth taking?** **Yes, and the *scope digest* half is takeable without any crypto:** record
the approved task text's hash and the declared write-scope with the dispatch, and have the reviewing
stage compare what changed against what was authorised.

**Cost: M** for the full capsule; **S** for the scope-digest subset. Derived from: dispatch scripts
already receive a task file and already open a PR — writing the task digest and declared scope into
the PR body is cheap; enforcing it during the run is not. **Depends on** §4.5 for the signed version.
**Roadmap home:** `Phase: Safety & Guardrails` (complete, so this is a new roadmap item) or
`Phase: Autonomous Operation`.

---

#### 4.8 Delegation narrowing — child ⊆ parent, verified from receipts `[Tier 2 · cost M–L]`

**What it is.** "A hop now records the **effective scope** it granted (or a content-addressed
reference to it) plus the **parent hop it descends from**, so the child ⊆ parent relation is
recomputed per hop from the receipts alone." A receipt records "`issuer`, `subject`, `audience`, and
`act`, HMAC-chained hop to hop." `bernstein delegation verify <run>` "reconstructs a run's per-hop
delegation receipts offline", and "Every hop is evaluated and nothing short-circuits, so a widening
late in the chain is still found when an earlier hop is unproven" [S31].

**The trap, stated first-party, is the reason to read this before designing our own:** "Scope axes
follow the capability-token convention that `None` is the *widest* value, so a child that drops a
bound its parent imposed widens on that axis" [S31]. A missing field silently means *unlimited*. That
is a live footgun in any parent→child delegation we build.

**Related and equally load-bearing, from `v3.13.0`'s breaking changes:** "A delegation chain with no
recorded scope is now unproven rather than valid (#3306)", with `bernstein delegation verify` exiting
code 3 (unproven) instead of 0 [S17]. **Absence of evidence is graded as *unproven*, not as *pass*.**
That is a two-valued-to-three-valued correction with immediate application to our own review agents,
which today return PASS/HOLD and have no way to say "I could not verify this."

**Why it matters for the federated destination.** Parent→child workflow composition is our
architecture. Once children run on other machines under other credentials, "what was this child
allowed to do, and who says so" needs an answer that does not require trusting the child.

**Evidence.** [S31][S17]. *(definitive at documentation level.)*

**(a) Architecture right for us?** The receipts assume the audit chain. **(b) Worth taking?** **The
two lessons — `None` means widest, and unproven ≠ valid — are worth taking today, for free.** The
mechanism is Tier 2.

**Cost: M–L** for the mechanism; **S** for the unproven/valid/invalid tri-state in our review agents.
Derived from: our reviewers are markdown agent definitions with a verdict vocabulary — adding a third
verdict is a prompt-contract change plus the parent's branch. **Depends on** §4.2 (same enum
discipline). **Roadmap home:** the tri-state goes to `Phase: Continuous Process Improvement`; the
mechanism to `Phase: Temporal Integration` once workers are remote.

---

#### 4.9 Kubernetes CRDs — verified present; **the controller is not documented** `[Tier 3 for us · cost L · not recommended]`

**What is verified.** `deploy/helm/bernstein/crds/` contains `bernsteinplan.yaml` (4,945 B) and
`bernsteinrun.yaml` (5,850 B) [S39]. The run CRD is `apiVersion: apiextensions.k8s.io/v1`,
`metadata.name: bernsteinruns.bernstein.io`, group `bernstein.io`, kind `BernsteinRun`, plural
`bernsteinruns`, shortName `brun`, scope `Namespaced`, version `v1`, with spec properties `planRef,
maxRetries, timeout, serverUrl, image, nodeSelector, resources` and status properties `phase,
startTime, completionTime, totalSteps, completedSteps, failedSteps, activeJobs, currentStage, stages,
conditions` [S40]. The chart's `templates/` directory contains `deployment-operator.yaml` and
`rbac-operator.yaml` [S41], and the operator deployment runs container `operator` with command
`["python", "-m", "bernstein.core.operator"]` and env `POD_NAMESPACE`, `BERNSTEIN_SERVER_URL`,
`BERNSTEIN_AGENT_IMAGE`, `BERNSTEIN_AUTH_SECRET`, `BERNSTEIN_PROVIDER_KEYS_SECRET` [S48].

**The negative finding.** **Neither `docs/operations/HELM_DEPLOYMENT.md` nor the chart's own
`deploy/helm/bernstein/README.md` mentions an operator, a controller, or the CRDs.** Search method:
fetched both raw and asked explicitly to state the absence if present; independently enumerated the
mkdocs `nav:` [S2] and `docs/cluster/` [S4] — the nav has entries for "Helm chart", "Cluster mode",
"Cluster mTLS", "Cluster patterns" and "Cluster e2e harness", and no operator entry; `docs/cluster/`
contains exactly two files [S4]. [S34] describes the chart as deploying a task server Deployment,
worker StatefulSet, Service and PVCs, with optional Prometheus/PostgreSQL/Redis, and no CRDs
[S34][S35].

**DERIVED:** the operator is **shipped in the chart and absent from the prose** — a documentation
gap, not a missing feature. bernstein's own `KNOWN_LIMITATIONS` predicts exactly this: "Bernstein
evolves quickly; some docs may lag short-term behind newly shipped features" [S5]. **The
methodological point matters more than the finding: had this paper stopped at the two docs pages, it
would have recorded "no operator" as a result, and been wrong.** The manifests are the source of
truth; the prose is not.

**(a) Architecture right for us?** **No.** We are not Kubernetes-native, we have no server tier, and
`Phase: Temporal Integration` puts durability in Temporal with systemd workers. **(b) Worth taking?**
**The CRD's *status* field list, and nothing else.** `phase, totalSteps, completedSteps, failedSteps,
activeJobs, currentStage, stages, conditions` [S40] is a well-shaped, hard-won answer to "what does an
external observer need to know about a running orchestration?" — and that question is live for the
operator-interface topic being researched in parallel this cycle. Take it as a **field list**, free.

**Cost: L**, and not recommended. Derived from: an operator implies a cluster, a control loop, and a
reconciliation model we have deliberately not chosen.

---

#### 4.10 Credentials at the edge — two independent mechanisms `[Tier 2 · cost S then M]`

**Mechanism 1 — filtered env at the spawn boundary.** "Bernstein spawns each leaf-agent subprocess
with a **filtered** credential view: only the env vars the policy permits for that agent or role are
forwarded"; rules are per-agent ("Exact id, or glob pattern such as "backend-*"") with a per-role
fallback; "The filtered env is what the subprocess inherits - the orchestrator's other secrets never
cross the spawn boundary"; and cloud storage keys "are stripped from every spawned env regardless of
the per-agent policy" so "a compromised agent therefore cannot exfiltrate the orchestrator's
long-lived cloud keys" [S22].

**Mechanism 2 — a short-lived-token broker.** "A short-lived-token broker that replaces
dotfile-in-workspace and process-env credential patterns for agent spawns." "Each task asks the
broker to mint a token for a named secret with a TTL. The broker reads the raw value from the backend,
generates a new opaque token, and registers the mapping in-process." "The raw backing value never
appears in an agent environment or a persisted artifact", and "The redactor scrubs both the raw
backing value and the minted token value from any persisted transcript" [S23].

**Why it matters for the federated destination.** "Credentials that stay at the edge" is one of the
four things the problem statement says neither side of the market supplies. bernstein does not solve
the *cross-MDC* version of the problem (§0.2), but it solves the *spawn-boundary* version twice, and
the second solution — mint a scoped token with a TTL, never hand over the backing secret — is what
the cross-MDC version will be built from.

**Evidence.** [S22][S23]. *(definitive at documentation level. Note [S22]'s fetch reported that
issuance and expiry are **not** described in that document — the TTL story lives in [S23], and the two
were not stated to be integrated.)*

**(a) Architecture right for us?** Mechanism 1: yes, immediately — we spawn subprocesses with
inherited env today. Mechanism 2: yes in shape, but it needs a broker process we do not have.
**(b) Worth taking?** **Yes to both; sequence them.**

**Cost: S** for mechanism 1 (an allow-list applied where dispatch scripts build the child
environment, plus the unconditional strip-list for anything cloud-shaped). **M** for mechanism 2 (a
broker, a backend adapter, a redactor, and a TTL story). **Depends on** nothing for the first.
**Roadmap home:** `Phase: Managed Configuration` for the filter; a new item under
`Phase: Temporal Integration` for the broker, since remote workers are what make it necessary.

---

#### 4.11 The self-improvement loop, and the honest state of it `[Tier 2 · lesson free]`

**The capability.** Lessons are "A tag-indexed, decaying store of short lessons filed on task
completion", stored in `.sdd/memory/lessons.jsonl` with tags, content, confidence (0.0–1.0), memory
type, timestamps and a SHA-256 integrity chain, and "matched against a new task's tags and injected
into the spawn prompt of the agent picking up related work" [S27].

**The gap, re-verified today.** "nothing files lessons automatically yet"; the retrieval and injection
path runs at every agent spawn but "no code path in the shipped orchestrator calls it"; the documented
trigger "describes the intended trigger, not current wiring"; in practice the file "only gains entries
if something outside the base orchestrator (a plugin, a custom hook, direct use of the Python API)
calls `file_lesson()`" [S27]. *(Re-verified 2026-08-04; the prior cycle recorded the same state, so
this has persisted across at least the interval between cycles.)*

**Why this is a finding rather than a footnote.** bernstein built the *read* half of its improvement
loop — retrieval, decay, tag-matching, prompt injection, integrity chaining — and left the *write*
half unwired. The read half is the interesting engineering; the write half is the one that makes the
loop exist. **DERIVED: build the write path first. A loop with no producer is decoration, however
sophisticated the consumer.** Our own loop is the mirror image and is better off for it: run logs and
PR self-disclosure are *written* automatically, and the consumption is a human-ruled review. The
asymmetry is worth stating in `problem-statement.md` element 2, where the layered-improvement claim
lives.

**ADR-003 is consistent with this reading.** It defines a risk-tiered self-evolution model — low-risk
changes such as "Adjust provider switching thresholds" and "Modify batch sizes" auto-apply,
high-risk ones such as "Update system prompts" require approval, with "Only apply changes with >80%
confidence", "Maximum 2 concurrent upgrades", and automatic rollback if metrics degrade [S19]. The
fetch reports the ADR carries **no measured results** and is dated 2026-03-22 — the day the
repository was created [S1]. *(negative finding; search method: single-document fetch asking
explicitly for measured results or case studies. It is a proposal, not a report.)*

**(a)/(b):** the risk-tier idea (auto-apply cheap policy changes, gate prompt changes on a human) is
worth taking as a **framing** for our CPI disposition log. **Cost: 0** — it is a way of sorting
findings we already produce.

---

### TIER 3 — capabilities whose architecture we reject, whose *lessons* we still take

---

#### 4.12 Agent suspend/resume and checkpointed retry `[architecture: no · lesson: yes · cost S for the lesson]`

**What it is.** At suspend, "A suspend row is appended to the task's event journal" containing "the
adapter-native session id, a workspace hash over the worktree, the journal head, and the envelope
balance at park time"; the task enters `SUSPENDED` "so the park survives orchestrator restarts and
daemon crashes"; the process is terminated, "the sandbox is torn down, the parallelism seat is
returned." Resume "is a deterministic projection" such that "two hosts with the same suspend row and
adapter capability derive the byte-identical decision," proven by a "suspend and resume receipt pair."
Limits are stated: "no cost is recorded while the task is parked", and "A park settles **once**. If a
`task.resume_receipt` already hangs off the suspend receipt, a second resume is refused" [S29].
Separately, retries checkpoint "the adapter's native session id and a workspace hash" at every
checkpoint and can resume "**warm**", "**fork**", or "**cold**" with "default `warm`"; "Prompt
content, gate output, and provider session state are never mirrored into the chain -- only
identifiers, hashes, the mode, and the downgrade reason"; and "the warm retry prompt is a fraction of
the cold re-prompt's input tokens" [S36].

**(a) Architecture right for us? No.** Our durability is Temporal; we will not build a journal, a
park state or a receipt pair.

**(b) Worth taking? Yes — the *contents of the checkpoint* is the transferable part.** The
non-obvious answer to "what must be captured to park a running agent session and resume it
elsewhere" is: **the provider-native session id, a hash of the workspace, the budget balance, and
nothing of the prompt**. That is exactly the open question in `Phase: Temporal Integration`'s
single-activity-vs-child-workflow fork, and `raw/python_sdk_long_activities.md` §8 leaves it open.
bernstein's answer is a free input to it.

**Two lessons priced at zero:** (1) warm resume of a provider session costs a fraction of a cold
re-prompt in input tokens [S36] — directly relevant to our subscription-economics thesis, where the
constraint is rate limits rather than dollars; (2) **a park settles once** [S29] — idempotency on the
resume edge, which is the kind of thing normally learned by a double-resume in production.

**Cost: S** to record these as constraints in the Temporal phase doc. **Roadmap home:**
`Phase: Temporal Integration`.

**The substrate underneath it is the part to leave behind, and ADR-004 says why it was chosen.** "All
persistent Bernstein state lives in `.sdd/` - plain text files (YAML, Markdown, JSONL, JSON) on the
local filesystem. No embedded database. No hidden in-memory state." SQLite was rejected as "Not
inspectable without tooling" with "Git diffs on `.db` files are meaningless"; Redis/external DB was
rejected because "Bernstein's core value proposition is `pip install bernstein && bernstein run` -
zero external dependencies for a solo developer"; and pure in-memory was rejected because the initial
prototype was "Lost on crash." The stated limits are "Not suitable for high-frequency writes" and "No
atomic multi-task transactions" across network filesystems [S51].

**DERIVED, from [S51] + our own position:** bernstein's file-based state is a direct consequence of a
constraint we do not share — zero external dependencies for a solo `pip install`. We have already
accepted a server dependency (Temporal on a backed-up VM). **The rejected alternative in their ADR is
the choice we made**, so their durability machinery is not evidence against ours; it is evidence that
the two products optimise different first constraints. Worth stating explicitly so a future reader
does not mistake bernstein's WAL for a recommendation.

---

#### 4.13 Loop, stall and crash detection with real thresholds `[Tier 2 · cost S]`

**What it is.** "An agent is 'looping' when it edits the same file more than a few times in a short
window" — detected by polling whether "a file's mtime has advanced since the last poll", counting
edits per `(agent_id, file_path)` pair, with more than 3 edits in a 300-second sliding window
triggering the response, which "kills the offending agent, propagates the abort to any child agents,
clears its lock-wait state, and releases its file locks" [S28]. The honest limitation is stated by
bernstein itself: detection is mtime-based with no intent signal, so "a legitimate agent that touches
the same file many times in quick succession...can trip the same threshold as a genuine fix-verify-fail
cycle" [S28].

**Corroborating tuning data from the unreleased notes:** the stall threshold was "Raised 90s→170s"
alongside an adjacent 180s idle-log reaper, and a heartbeat escalation cap was added because a
"Chattering runner log no longer defers stalled agents forever" — capped at 900s [S18].

**Why it matters.** Our `revision.sh` bounds loop-backs by *count*; it has no detector for an agent
spinning *inside* a run. Every mechanism here is domain-general (file mtime is the coding-edge
instantiation; the pattern is "same effector, repeatedly, no progress").

**(a) Architecture right for us?** The mechanism is polling-based and assumes a supervisor process.
Under Temporal a heartbeat-with-progress-token is the idiomatic equivalent. **(b) Worth taking?**
**Yes — the thresholds and the failure mode.** The numbers (>3 edits / 300 s; 90→170 s stall; 900 s
escalation cap) are hard-won calibration that would otherwise cost us weeks of tuning, and they are
free to adopt as *starting points*.

**Cost: S** as a documented starting calibration; **M** to build a detector. **Roadmap home:**
`Phase: Autonomous Operation` (exit criteria and failure behaviour).

---

#### 4.14 `pass^k` as an observable exit criterion `[Tier 2 · cost S–M]`

**What it is.** "pass^k" is the "fraction of tasks where **all** `k` attempts passed" and is used as
"the floor — the headline number." The rationale: "A task that succeeds once in eight attempts and a
task that succeeds every time both read as 'passed' under single-run or best-of-N scoring. They are
worlds apart operationally." The estimator: "with per-attempt success probability `p` and `n` recorded
attempts of which `c` passed, the unbiased estimator of the all-of-k probability `p^k` is `C(c, k) /
C(n, k)`." And the caveat, stated first-party: "The floor is a **point estimate, not a confidence
bound**: with small `k`, a flaky task can still show a clean floor by luck" [S33]. In the unreleased
notes it becomes a first-class CLI spelling: "`bernstein eval --reliability K is now a first-class
spelling`" [S18].

**Provenance note:** `pass^k` is not bernstein's invention — it is the metric introduced by τ-bench,
already cited elsewhere in this pool as `backbone_edge_generality.md`'s **[S33]**, a *different*
paper's label for arXiv 2406.12045 and not this paper's [S33] (`docs/eval/reliability.md`). **What
bernstein contributes is operationalising it as a shipped gate**, which is the part we would
otherwise have to figure out. *(derived.)*

**Why it matters.** `Phase: Autonomous Operation` needs "an exit condition it can actually observe"
(problem statement element 4), and `raw/convergence_stopping.md` is the pool paper on it. A repeated-
run floor is an observable, and a cheap one.

**(a)/(b):** architecture-neutral; **worth taking.** **Cost: S** to adopt the metric in the run-log
analysis (`review-runs.sh` already reads a window of JSONL across repos); **M** to build a repeated-
attempt harness. **Roadmap home:** `Phase: Continuous Process Improvement`, then
`Phase: Autonomous Operation`.

---

#### 4.15 An admission contract for what may be an edge `[Tier 2 · lesson free · cost S]`

**What it is.** A documented, public list of integrations bernstein **declined**, with the reason for
each. SAP Joule: "There is no `joule` binary, no `sap-joule exec`, no documented headless
invocation." Tessl: "it is a spec installer / agent harness wrapper" creating a wrapper-of-wrapper
problem. Phind / Pieces / Sweep: "All three are IDE-only or web-only." Vercel v0 / Lovable /
Bolt.new: "These are web-only build-an-app surfaces aimed at UI generation, not general coding
agents." Tabby: "There is no agentic CLI - no short-lived process to spawn, no stdout to harvest."
Suna: "a service-manager surface, not a short-lived task process." DeepSeek CLI: "no canonical
first-party `deepseek` binary" [S7].

**DERIVED, from [S7] + [S20]:** the declines all reduce to one admission criterion — **a candidate
must be a short-lived process that can be spawned, whose output can be harvested, and whose exit maps
to task success or failure.** That is the same short-lived-agent doctrine as §4.4, applied as an
*intake filter*. It is the closest thing in the sweep to an answer to "what makes something an edge?",
which the problem statement asserts ("a machine with a capability and a credential, running a worker
that speaks the backbone's protocol") without a test.

**Why it matters for the federated destination.** With many edge types proposed over time, a written
admission test is what stops the backbone accreting one-off accommodation — which is precisely the
failure `raw/backbone_edge_generality.md` §2.3 prices at 1.5M lines in the Kubernetes case.

**(a)/(b):** **take the practice.** **Cost: S** — write the criterion and a `declined/` note when an
edge candidate is rejected. **Roadmap home:** `problem-statement.md § The edges` as a
standards-amendment candidate.

---

#### 4.16 Observability — the cheapest capability in the paper `[Tier 2 · cost S–M]`

**What it is.** "Metrics - Prometheus-format counters, gauges, and histograms exposed at `/metrics`.
Native Datadog APM and OpenTelemetry/OTLP export are also available out of the box"; "Traces - task
and agent execution spans via OpenTelemetry, with built-in presets for Jaeger, Grafana Tempo,
Datadog, Zipkin, and console"; the OTel projection "is written to the local
`.sdd/runs/<run_id>/projection.otel.json` store even when no OTLP endpoint is set
(`BERNSTEIN_OTEL_ENDPOINT` stays opt-in)"; canonical protocol "OTLP/gRPC"; and the honest limit
"Logs are not piped directly - use the Datadog Agent's log file collection on `.sdd/runtime/*.log` if
you need log correlation" [S37]. The repo ships `deploy/grafana`, `deploy/prometheus` and
`deploy/otel-collector` [S49].

**The design worth copying is the local projection.** Writing the OTel projection to disk *whether or
not* an endpoint is configured means the telemetry exists before the infrastructure does. For an edge
that may be offline, behind a tunnel, or in an MDC with no collector yet, that ordering is the right
one.

**(a) Architecture right for us?** Yes, once there is anything long-running to observe. **(b) Worth
taking?** **Yes**, and it is nearly free relative to its value: our run logs are already JSONL.

**Cost: S** to emit OTel-shaped spans into the existing JSONL; **M** for a collector and dashboards.
**Depends on** `Phase: Temporal Integration` for there to be anything worth a dashboard. **Roadmap
home:** `Future Ideas → E. Metrics Dashboard` is where this currently lives; this finding argues it
should become a phase item, not an idea.

---

### 4.17 The v3.13.0 lesson that has nothing to do with orchestration `[free · read this one]`

`v3.13.0` is a reliability release about the project's own release pipeline, and it contains the
single most transferable failure story in the sweep for a repo whose thesis is a self-improving loop:

- "The npm wrapper had been failing inside a green job since 2.3.0" — masked by warning-only
  reporting.
- The RPM channel "had shipped nothing since 1.4.11".
- **"The drift detector that was supposed to catch any of that closed its own tickets"** — due to
  unread registry failures.
- The corrections make failure loud: "A failed npm wrapper publish now fails its job (#3322)";
  "`reconcile-release` fails when it could not read a channel (#3345)", which previously "excluded
  unreadable channels from verdict" [S17].
- And from the unreleased notes, the same shape once more: "CI gate required check could be satisfied
  by the synthetic stub on a diff that carries code" [S18].

**DERIVED, from [S17] + [S18]:** four independent instances of one failure mode — **a check that
cannot read its subject reports success.** Warning-only reporting, excluding unreadable channels from
the verdict, a stub satisfying a required check, and a detector closing its own tickets are the same
bug wearing four costumes. The correction in every case is the same and is the one this repo should
adopt verbatim: **unreadable is a failure, not an exclusion; and no checker may close its own
finding.**

This bears directly on our architecture. `system-overview.md § The improvement loop` states that the
system "observes itself and proposes; it does not modify itself," and `§ Where the seams are` lists
"author ≠ judge" and "decide ≠ act". **bernstein's drift detector violated exactly that seam, in
production, and the release notes are the receipt.** Our seam is already drawn correctly — this is
corroborating evidence for a design we hold, which is the rarest and most useful kind of finding in a
mining pass.

**Cost: S.** Derived from: an audit of our own gates for the "cannot read → pass" pattern, plus a
rule that no agent closes a finding it raised. **Roadmap home:** `Phase: Continuous Process
Improvement`; standards-amendment candidate against `engineering-quality.md § Finding disposition`.

---

### 4.18 Transport security and disaster recovery — verified shipped, low value to us `[Tier 3 · lesson S]`

Both were named in the dispatch's known-shipped list and both verify. Neither is worth building here;
three of their stated limits are worth keeping.

**mTLS.** "mTLS authenticates the *channel*. The existing JWT bearer token still authorises the
*action* - both layers compose." Any PKI works ("step-ca, cert-manager, HashiCorp Vault, your
corporate CA"), with a self-signed bootstrap for internal clusters. Two limits are stated plainly:
"This is an opt-in: existing plain-HTTP deployments keep working", and **"Rotation is manual"**, with
the recommendation to "automate it via a sidecar that writes the files and SIGHUP/restarts the
server" [S53].

**Disaster recovery.** The WAL appends "every orchestrator decision (claim, spawn, complete, fail,
merge)" to "a hash-chained JSONL file with `fsync()` *before* the action runs", alongside "periodic
atomic snapshots of full orchestrator state (task graph + agent sessions + cost accumulator + WAL
sequence position)". RPO is "= backup cadence"; RTO is "< 15 min for the dr-restore step itself, plus
your provisioning". What is lost is named: committed state survives, but "the *bound but un-fsynced
runtime telemetry* (heartbeats, log tails, metrics counts)" does not. Provider API keys are
deliberately excluded from the backup [S54].

**(a) Architecture right for us? No** on both counts — Temporal owns crash recovery, and there is no
cluster to put mTLS across today.

**(b) Worth taking? Three things, all free:**

1. **"Rotation is manual" is the confession most mTLS write-ups omit** [S53]. It is the real cost of
   mTLS and the reason SPIFFE/SPIRE exists (§3). Any future edge-to-backbone security design must be
   priced with rotation included from the first sentence.
2. **The channel/action split** — authenticate the channel, authorise the action, compose both [S53]
   — is the correct two-layer statement for edges under SkyyCommand and costs nothing to adopt.
3. **"A backup you have not restored is not a backup"** [S54], with a periodic restore drill. Our
   memory lives in GitHub, which makes this feel solved; it is not, and the discipline transfers.

**Cost: S** for the three lessons as written constraints; **L**, and not recommended, for the
machinery. **Roadmap home:** the deferred "Multi-edge identity, trust and credential distribution"
topic, as priced inputs.

---

## 5. Summary — the ranked take list a planner can sequence

| # | Capability | Take? | Arch fit (a) | Cost | Depends on | Roadmap home |
|---|---|---|---|---|---|---|
| 1 | Typed activity boundary / `ActivityResult` + no-repeat-evidence stop rule (§4.1) | **Yes** | partial | **M** | Temporal port | Temporal Integration |
| 2 | Typed refusal, closed taxonomy, no catch-all (§4.2) | **Yes** | yes | **S** | — | Workflow Decomposition |
| 3 | Closed failure vocabulary: `reason_code` / `transient` / `next_action` (§4.3) | **Yes** | yes | **S** | do with #2 | CPI + Workflow Decomposition |
| 4 | Short-lived worker doctrine + wall-clock kill (§4.4) | **Yes** | yes | **S** | — | standards + Temporal Integration |
| 5 | Evidence-hash verification of claims (§4.6) | **Yes** | yes | **S–M** | a byte cache | research tooling / CPI |
| 6 | "Unreadable is a failure"; no checker closes its own finding (§4.17) | **Yes** | yes | **S** | — | CPI + standards |
| 7 | Unproven ≠ valid (tri-state review verdict) (§4.8) | **Yes** | yes | **S** | do with #2 | CPI |
| 8 | Filtered credential env at the spawn boundary (§4.10) | **Yes** | yes | **S** | — | Managed Configuration |
| 9 | Intent capsule — scope-digest subset (§4.7) | **Yes** | partial | **S** | — | Autonomous Operation |
| 10 | Checkpoint contents: session id + workspace hash + budget (§4.12) | **Yes (as constraint)** | no | **S** | — | Temporal Integration |
| 11 | Loop/stall thresholds as starting calibration (§4.13) | **Yes** | partial | **S** | — | Autonomous Operation |
| 12 | Edge admission criterion + a declined list (§4.15) | **Yes** | yes | **S** | — | problem-statement amendment |
| 13 | `pass^k` reliability floor as exit criterion (§4.14) | **Yes** | yes | **S–M** | run-log window | CPI → Autonomous Operation |
| 14 | OTel projection written locally regardless of endpoint (§4.16) | **Yes** | yes | **S–M** | — | promote from Future Ideas |
| 15 | Short-lived secrets broker with TTL (§4.10) | **Later** | yes | **M** | remote workers | Temporal Integration |
| 16 | Hash-chained audit + offline verifier (§4.5) | **Later** (take the +157 B/entry price now) | partial | **M** | a persistent decision log | Memory Management Framework |
| 17 | Delegation-narrowing receipts (§4.8) | **Later** | partial | **M–L** | #16 | Temporal Integration |
| 18 | Kubernetes operator + CRDs (§4.9) | **No** — take the status field list only | **no** | **L** | a cluster | — |
| 19 | WAL / file-based state / journal (§4.12, ADR-004 [S51]) | **No** | **no** | — | — | superseded by Temporal |
| 20 | mTLS machinery + DR runbook (§4.18) | **No** — take three constraints only | **no** | **L** | a cluster | deferred identity topic |

**Eight of the fourteen unconditional "yes" items (rows 2, 4, 6, 8, 9, 10, 11, 12) are cost S and
depend on nothing; a ninth (row 14, the local OTel projection) depends on nothing but is costed
S–M.** *(DERIVED from the column values above.)* That is the actionable summary: the majority of the value in the nearest neighbour is
in *interfaces and doctrine*, not in machinery — which is the expected result when the machinery
question has already been answered by choosing Temporal.

---

## 6. What this provides — enumerated, citable properties a plan can rely on

1. **A shipped, documented typed boundary for non-coding work exists in a competitor**, with five
   named modalities and one result contract [S14], and two of them documented independently
   [S12][S13]. *(definitive at doc level.)*
2. **A worked closed refusal taxonomy** — four kinds, required field per kind, contract_violation
   auto-fail [S30]. *(definitive at doc level.)*
3. **A worked closed failure vocabulary** — 14 reason codes plus `transient` and `next_action`, with a
   forward-compatibility rule [S6]. *(definitive at doc level.)*
4. **Measured evidence that resident agents fail** — 12-agent pilot, 3 reliable, 283 idle messages,
   ~50k tokens on signalling, and the replacement policy with its two caps [S20], corroborated [S24].
   *(first-party self-reported measurement.)*
5. **A price for tamper-evident audit** — +157 B/entry, ~50 µs/append, 72–75k events/s verify [S21].
   *(first-party benchmark, not reproduced.)*
6. **A mechanised answer to "is this citation still true?"** — content hash plus offline re-check of
   the quoted span [S12][S13]. *(definitive at doc level.)*
7. **Four independent instances of "a check that cannot read its subject reports success"**, with the
   corrections [S17][S18]. *(definitive at doc level; DERIVED that they are one failure mode.)*
8. **A capability-token footgun stated first-party** — `None` is the widest value, so a dropped bound
   widens [S31]. *(definitive at doc level.)*
9. **Calibration numbers for agent-liveness detection** — >3 edits / 300 s; stall 90→170 s; 900 s
   escalation cap [S28][S18]. *(definitive at doc level.)*
10. **Two independent confirmations that cross-organisation federation is outside the nearest
    neighbour's scope** — fleet's trusted-operator assumption [S25] and federation v1's explicit
    limitation [S8]. *(definitive at doc level.)*
11. **A checkpoint content list for parking an agent session** — provider-native session id,
    workspace hash, budget balance, journal head; prompt content deliberately excluded [S29][S36].
    *(definitive at doc level.)*
12. **An admission criterion for what may be integrated**, derivable from seven public declines [S7].
    *(DERIVED.)*

---

## 7. Honest boundary analysis — the case against this paper

### 7.1 The strongest argument: this is documentation, not behaviour

**Nothing was executed.** Every capability claim rests on bernstein's own prose about bernstein.
`raw/production_cases.md`'s central lesson — that "checkpoints" are routinely marketed as durability
and are not — applies here with full force. A doc called `activity-boundary.md` is not a running
activity boundary, and §0.1's headline is a claim about a *document*.

**The counter, and it is partial:** four of this paper's load-bearing findings do not depend on
bernstein's prose about its features. §4.9's CRDs were read from the manifest YAML and the operator
from the Helm template [S39][S40][S41][S48]; §4.4's and §4.5's numbers are stated as measurements
with methods; §4.17's failures are the project's own bug reports, and **a project does not overstate
its own broken release channels.** The release notes are the most trustworthy genre in the corpus
precisely because they are unflattering.

### 7.2 bernstein says its own docs drift, and it is right

"Bernstein evolves quickly; some docs may lag short-term behind newly shipped features" [S5]. §4.9 is
a demonstrated instance in the *other* direction: the code shipped ahead of the prose. **So the doc
set both over- and under-states the product**, and neither direction is predictable per-page.

### 7.3 The case against mining at all

Stated at full strength, because a mining paper that cannot argue against mining is advocacy:

1. **Copying a competitor's interfaces imports their assumptions.** `ActivityResult`'s
   `evidence_set_hash` presumes content-addressed storage; the refusal taxonomy presumes a completion
   API; the failure codes presume a tracker. Take the field and you may have taken the substrate.
2. **Their solutions are shaped by problems we do not have.** Nine of the fourteen recommended items
   are cheap partly *because* they are small — but small items accumulate carry cost, and
   `raw/backbone_edge_generality.md` §6 (Fowler's four costs, Glass's rule of three) applies to
   imported interfaces exactly as it does to invented ones. **An interface with one implementation is
   speculative generality regardless of who designed it.**
3. **The lessons may not transfer across the model generation.** ADR-005's pilot ran on whatever
   models were current in March 2026. "Agents confuse their own work with others' after hours of
   operation" is a statement about a context window and a model, not a law. Adopting the wall-clock
   kill because *they* measured it is cargo-culting unless we re-measure.
4. **Reading 35 files across 13 directories and ranking capabilities produces a plausible ranking, not
   a correct one.** The ranking in §5 is this paper's inference. A different reader with the same
   corpus could reasonably promote §4.5 over §4.6.
5. **Opportunity cost is real.** Fourteen "yes" items is roughly a phase of work. The roadmap's next
   milestone is durable execution. A capability shopping list is exactly the kind of artifact that
   turns into scope.

**Where I come down:** items 2, 3, 4, 6, 7 and 12 in §5 are *doctrine and vocabulary* — they cost
words, not code, and objections 1 and 2 do not reach them. Items 1, 5, 14 and 15 are builds and
should be sequenced against the Temporal port rather than before it. Objection 3 is answered by
adopting bernstein's numbers as **starting calibration explicitly labelled as theirs**, which is what
§4.13 says. Objection 5 is real and is why §5 is ranked rather than listed.

### 7.4 Where this paper is weak, specifically

- **Coverage is a small minority of the doc set, and is stated without a denominator** (§1.4 — the
  earlier numeric denominator was withdrawn as summarizer-derived). Whole areas — `gui/`, `mcp/`,
  `compliance/`, `trackers/`, `memory/`, `lineage/` — are unread. `docs/CHANGELOG.md` was not read at
  all, and it is the richest remaining seam for design reversals.
- **The commit history was not analysed.** The dispatch's "~3,397 commits by one maintainer" is
  **not** verified here; no commit-author query was run. §2's single-maintainer risk is therefore
  supported only indirectly, by [S17].
- **ADR 002 is absent.** The decisions directory contains 001 and 003–010 [S16]. *(negative finding;
  search method: contents-API listing of `docs/decisions`, which returns exactly nine files.)*
  Whether 002 was withdrawn, renumbered or never written is **unknown**, and a withdrawn ADR would
  have been the highest-value document in the directory.
- **`FEATURE_MATRIX.md` was fetched and is not cited for any specific claim** [S50] — the fetch
  returned a structural summary rather than the matrix rows, and nothing in this paper rests on it.
  Recording the fetch rather than silently dropping it, per §1.3.
- **Every "quoted" span is §1.3-class, not strict-verbatim.** A critic re-fetching these URLs should
  expect the substance to match and should treat any character-level mismatch as a fetch-layer
  artefact to be reported, not as fabrication — but the possibility that a span was reworded by the
  fetch layer cannot be excluded, and §1.3 shows the fetch layer presenting partial content as
  complete under other conditions.
- **No independent corroboration of bernstein's self-reported measurements.** The pilot figures
  [S20] and the audit-chain benchmark [S21] are unreplicated first-party numbers.

---

## 8. Test plan — what research cannot settle

1. **Install it and run it.** `pip install bernstein` (Apache-2.0, `>=3.12` [S42]) against a throwaway
   repo, and execute the four claims this paper leans on hardest: a typed refusal round-trip
   (§4.2), an `ActivityResult` from a non-coding modality (§4.1), `bernstein activity verify` on a
   tampered source file (§4.6), and a suspend/resume pair (§4.12). **Everything in §5 above is
   documentation-grade until this is done**, and the run costs an afternoon.
2. **Re-measure the wall-clock and batch caps on our own stack.** ADR-005's 30-minute kill and 1–3
   task batch are theirs. Run our own dispatches to degradation and record where output quality falls
   off. Objection 7.3(3) is only answered by our own number.
3. **Price the audit chain on our data.** +157 B/entry [S21] is their entry size. Take one month of
   our run-log JSONL, compute the delta, and decide §4.5 with a real figure rather than an imported
   one.
4. **Test the no-repeat-evidence stop rule against our loop-back bound.** §4.1's rule ("the scheduler
   refuses to add a stage whose `evidence_set_hash` equals a prior stage's") and `revision.sh`'s
   count-based bound are two answers to one question. Run the revision workflow on a task that cannot
   converge and check whether an evidence hash would have stopped it earlier than the count did. This
   is the sharpest cheap experiment available and it feeds `raw/convergence_stopping.md` directly.
5. **Audit our own gates for the §4.17 pattern.** Enumerate every check in our workflows and hooks and
   answer, per check: *what does it do when it cannot read its subject?* Any answer other than "fails"
   is the bug bernstein shipped for months. This is an audit, not an experiment, and it should happen
   before the next autonomous phase.
6. **Read `docs/CHANGELOG.md` and the remaining decisions directory.** Explicit handoff to the next
   cycle. The reversal seam is where the remaining hard-won lessons are, and 002's absence is worth
   resolving.
7. **Research handoff, not experiment — the cross-MDC identity question.** §0.2 establishes that the
   nearest neighbour does not solve it; §4.10 and §4.8 are the pieces it would be built from. The
   topic list already names "Multi-edge identity, trust and credential distribution" as deferred; this
   paper is evidence that it cannot be answered by mining and needs its own pass.

---

## 9. Citations

All bernstein sources are first-party and were fetched raw (`raw.githubusercontent.com`) or via the
GitHub contents/repo API. `default_branch` was confirmed as `main` via [S1] **before** any raw fetch.

**Repository, package and structure**

- **[S1]** GitHub REST API — repo metadata, `sipyourdrink-ltd/bernstein` (JSON). https://api.github.com/repos/sipyourdrink-ltd/bernstein
- **[S2]** bernstein — `mkdocs.yml`, full `nav:` tree (raw YAML). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/mkdocs.yml
- **[S3]** GitHub contents API — `docs/` listing. **Cited for the *presence* of the named directories only; no count from this endpoint is used (§1.4).** https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/docs
- **[S4]** GitHub contents API — `docs/cluster/` listing (2 files). https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/docs/cluster
- **[S16]** GitHub contents API — `docs/decisions/` listing (9 files; 001, 003–010). https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/docs/decisions
- **[S39]** GitHub contents API — `deploy/helm/bernstein/crds/` listing. https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/deploy/helm/bernstein/crds
- **[S41]** GitHub contents API — `deploy/helm/bernstein/templates/` listing (16 files). https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/deploy/helm/bernstein/templates
- **[S49]** GitHub contents API — `deploy/` listing (`github-app`, `grafana`, `helm`, `otel-collector`, `prometheus`; small listing, verified exactly) and the repo-root listing. **The root listing is cited for the *presence* of `deploy/`, `src/`, `schemas/` and `proto/` only; no count from it is used (§1.4).** https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/deploy · https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/
- **[S42]** PyPI JSON API — package `bernstein` (version, licence, `requires_python`). https://pypi.org/pypi/bernstein/json — **see §1.3: this endpoint's summarised fetch returned a partial release list presented as a complete history; only the scalar fields are used, and every date comes from [S43]–[S45].**
- **[S43]** PyPI JSON API — `bernstein` 3.13.0 upload timestamps. https://pypi.org/pypi/bernstein/3.13.0/json
- **[S44]** PyPI JSON API — `bernstein` 3.12.0 upload timestamps. https://pypi.org/pypi/bernstein/3.12.0/json
- **[S45]** PyPI JSON API — `bernstein` 3.0.0 upload timestamps. https://pypi.org/pypi/bernstein/3.0.0/json

**Architecture, decisions and orchestration**

- **[S5]** `docs/reference/KNOWN_LIMITATIONS.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/reference/KNOWN_LIMITATIONS.md
- **[S6]** `docs/orchestration/failure-taxonomy.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/orchestration/failure-taxonomy.md
- **[S7]** `docs/adapter-deferred.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/adapter-deferred.md
- **[S8]** `docs/orchestration/federation.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/orchestration/federation.md
- **[S9]** `docs/orchestration/worker-coordination.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/orchestration/worker-coordination.md
- **[S10]** `docs/operations/named-resource-pools.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/named-resource-pools.md
- **[S11]** `docs/use-cases.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/use-cases.md
- **[S12]** `docs/orchestration/research-activity.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/orchestration/research-activity.md
- **[S13]** `docs/orchestration/browser-activity.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/orchestration/browser-activity.md
- **[S14]** `docs/operations/activity-boundary.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/activity-boundary.md
- **[S19]** `docs/decisions/003-self-evolution.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/decisions/003-self-evolution.md
- **[S20]** `docs/decisions/005-short-lived-agents.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/decisions/005-short-lived-agents.md
- **[S21]** `docs/decisions/010-audit-chain-default-cost.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/decisions/010-audit-chain-default-cost.md
- **[S24]** `docs/architecture/orchestration-approaches.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/architecture/orchestration-approaches.md
- **[S51]** `docs/decisions/004-file-based-state.md` (the rejected-alternatives record for SQLite / Redis / in-memory). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/decisions/004-file-based-state.md

**Operations, reliability and security**

- **[S17]** `docs/release-notes/v3.13.0.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/release-notes/v3.13.0.md
- **[S18]** `docs/release-notes/unreleased.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/release-notes/unreleased.md
- **[S22]** `docs/security/credential-scoping.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/security/credential-scoping.md
- **[S23]** `docs/security/secrets-broker.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/security/secrets-broker.md
- **[S25]** `docs/operations/fleet.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/fleet.md
- **[S26]** `docs/reference/spiffe-workload-identity.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/reference/spiffe-workload-identity.md
- **[S27]** `docs/concepts/lesson-persistence.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/concepts/lesson-persistence.md
- **[S28]** `docs/operations/agent-loop-detection.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/agent-loop-detection.md
- **[S29]** `docs/operations/durable-suspend-resume.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/durable-suspend-resume.md
- **[S30]** `docs/operations/worker-contracts.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/worker-contracts.md
- **[S31]** `docs/security/delegation-narrowing.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/security/delegation-narrowing.md
- **[S32]** `docs/operations/intent-capsules.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/intent-capsules.md
- **[S33]** `docs/eval/reliability.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/eval/reliability.md
- **[S34]** `docs/operations/HELM_DEPLOYMENT.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/HELM_DEPLOYMENT.md
- **[S35]** `deploy/helm/bernstein/README.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/deploy/helm/bernstein/README.md
- **[S36]** `docs/operations/checkpointed-retries.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/checkpointed-retries.md
- **[S37]** `docs/operations/observability-overview.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/observability-overview.md
- **[S38]** `docs/index.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/index.md
- **[S40]** `deploy/helm/bernstein/crds/bernsteinrun.yaml`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/deploy/helm/bernstein/crds/bernsteinrun.yaml
- **[S48]** `deploy/helm/bernstein/templates/deployment-operator.yaml`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/deploy/helm/bernstein/templates/deployment-operator.yaml
- **[S52]** `docs/operations/HOLDS.md` (heartbeat-renewed lease that suppresses quiescence self-stop; read for §0.2's scheduling model, not cited for a §4 capability). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/HOLDS.md
- **[S53]** `docs/cluster/mtls-setup.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/cluster/mtls-setup.md
- **[S54]** `docs/operations/disaster-recovery.md`. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/disaster-recovery.md
- **[S50]** `docs/reference/FEATURE_MATRIX.md` — **fetched, not relied on** (§7.4). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/reference/FEATURE_MATRIX.md
- **[S55]** `docs/whats-new.md` — superseded by per-tag release notes; recorded because it was fetched and yielded no current facts. https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/whats-new.md

**Non-bernstein sources (the buy-side of §3)**

- **[S46]** SPIFFE — `standards/SPIFFE-ID.md` (raw markdown; `default_branch` = `main` confirmed via https://api.github.com/repos/spiffe/spiffe). https://raw.githubusercontent.com/spiffe/spiffe/main/standards/SPIFFE-ID.md
- **[S47]** OpenTelemetry — `semantic-conventions`, `docs/gen-ai/README.md` (raw; `default_branch` = `main` confirmed via https://api.github.com/repos/open-telemetry/semantic-conventions). Returns only a relocation notice: "GenAI semantic conventions have moved to the OpenTelemetry GenAI semantic conventions repository." https://raw.githubusercontent.com/open-telemetry/semantic-conventions/main/docs/gen-ai/README.md

**Source count: 54 citation labels covering 57 distinct URLs, every one of them fetched in this
cycle.** (Labels run S1–S14 and S16–S55; **S15 is unused** — the numbering gap is recorded rather
than silently closed. [S49] carries two URLs; [S46] and [S47] each carry an additional
`api.github.com` repo endpoint used solely to confirm `default_branch` before the raw fetch.) Of
these, 52 labels are first-party bernstein repository or package endpoints and 2 are non-bernstein
standards sources. **Two fetched sources ([S50], [S55]) are recorded as yielding nothing this paper
relies on**, and **one ([S42]) is recorded as having returned a partial list presented as
complete**, with the
correction path stated (§1.3). Nothing in this paper is sourced from a search-engine result summary;
no web search was used at any point — the entire evidence base is direct fetches of raw first-party
endpoints.

**Adjacent pool papers referenced (not counted above):**
[`combination_prior_art.md`](combination_prior_art.md) (last validated 2026-08-03, Critic:
PASS-WITH-FIXES) — the prior cycle's bernstein coverage, whose 12 read files this paper extends;
[`backbone_edge_generality.md`](backbone_edge_generality.md) (2026-08-03, PASS-WITH-FIXES) — §2.7's
ontology-at-the-edge split, which §4.3 instantiates, and §6's YAGNI analysis, which §7.3 applies;
[`durable_execution.md`](durable_execution.md) (2026-07-27, PASS) and
[`temporal.md`](temporal.md) (2026-07-04, **PAST WINDOW — treated as unverified**) — the buy-side of
§3; [`convergence_stopping.md`](convergence_stopping.md) (2026-08-03) — the consumer of §4.1's
no-repeat-evidence rule and §4.14; [`production_cases.md`](production_cases.md) (2026-07-23) — the
source of §7.1's doc-vs-behaviour caution;
[`python_sdk_long_activities.md`](python_sdk_long_activities.md) (2026-08-03) — the open fork that
§4.12 feeds.
