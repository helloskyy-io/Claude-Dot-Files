# Synthesis — product-level research

**Cycle:** 2026-07-27 · **Pool:** 8 papers · **Tier:** Large / architecture-layer

> **Provenance.** This pool and synthesis were produced by the CSCI-6905.604 research project (2026-07-04 → 07-27),
> working this methodology by hand — `research.sh` was modelled on that process, not the reverse. Carried into this
> repo as a completed prior cycle. Class-administrative sections (paper structure, submission plan, grading) were
> dropped on transfer; the research content is unchanged.

## Inputs

| Paper | Last validated | Revalidate | Critic |
|---|---|---|---|
| `raw/durable_execution.md` | 2026-07-27 | low — 6 months | PASS |
| `raw/temporal.md` | 2026-07-04 | high — 4 weeks | PASS |
| `raw/claude_code_integration_surface.md` | 2026-07-25 | high — 4 weeks | PASS |
| `raw/anthropic_tos_and_enterprise.md` | 2026-07-24 | high — 4 weeks | PASS |
| `raw/hook_sourcing_supplement.md` | 2026-07-25 | high — 4 weeks | PASS |
| `raw/hierarchical_agents.md` | 2026-07-25 | medium — 3 months | PASS |
| `raw/reflection_literature.md` | 2026-07-23 | medium — 3 months | PASS |
| `raw/production_cases.md` | 2026-07-23 | medium — 3 months | PASS |

**Currency note:** `temporal.md` is the oldest input and carries the shortest interval. Vendor specifics age fastest; the durable-execution *concepts* paper is deliberately long-interval because only the vendor layer moves.

## What the pool establishes

**Author:** Eric Rue
**Course:** CSCI-6905.604 Applied Agentic AI
**Due:** July 26, 2026 (Sunday) — 11:59 PM
**Status:** Direction committed 2026-07-23; refined with background research; **v3 pivot 2026-07-24 morning** — reframed as systems architecture contribution after Author's pushback on prior novelty framing.

**v3 changes** — see §13 "What changed in v3" at the end for the diff summary.

---

### Committed direction

**Topic (from approved list):** Self-Improving Agents with Reflective Loops
**Secondary compositional mechanism:** Long-Horizon Planning with Hierarchical Agent Stacks (invoked in §3 as the natural composition target)

**Proposed research question:**

> **How can an organization deploy self-improving agentic AI workflows at team scale without forcing a trade-off between per-user tools without orchestration and centralized platforms with prohibitive per-token cost?**

**Working paper title (draft):**

> **"Federated Agentic Orchestration: A Reference Architecture for Team-Scale Self-Improving Workflows on Heterogeneous Edge Compute"**

**Methodology (from the four permitted):**

> **Propose a novel architecture or algorithm with theoretical justification**

Grounded in an existing production implementation of the module design standards (the author's `mdc-master-planning` standards repository, described in §5), which serves as informal validation that the standards work at scale in a real infrastructure automation context.

**Framing anchors (locked):**

- **The Anthropic-integration gap** — OpenAI Agents SDK is GA on Temporal (Replay 2026), Google ADK has native Temporal integration (April 2026), but Claude Agent SDK has no first-party Temporal integration. A November 2025 community forum request remains unanswered. The paper's reference architecture addresses this specific unpaved integration path without depending on any single vendor.
- **The subscription-vs-token economic asymmetry** — flat-rate subscription-tier authentication at the edge (each user's own subscription on their own machine) sidesteps the per-token cost profile of centralized platforms. Combined with distributed orchestration, this dissolves the current organizational deployment trade-off.
- **The edge-autonomy design axiom** — "edge owns what edge is better suited for." Auth, compute, and local state stay at the edge; only orchestration and shared workflow definitions live at the server. This is the elegance that sidesteps ToS gray areas and enables generalization across deployment domains.
- **Google ADK framing borrowed** — "a deterministic sequence of non-deterministic things." Used verbatim in §3 as the paper's architectural framing sentence.

---

### Why this direction fits

### 2.1 Personal alignment

- Author has deep prior Temporal experience (production workflow orchestration on the MDC platform)
- Author has developed production-grade module design standards for Temporal workflows over multi-year operation — the `mdc-master-planning` standards repository is the concrete artifact
- Author has also developed an informal reflective-loop framework (CPI methodology) for software engineering workflows — currently bash-based, hits the substrate ceilings this paper argues against
- The paper is the formalization and generalization of what the author has been building in narrower domains

### 2.2 Academic gap (unchanged from v2, restated)

The reflective-loop literature (Reflexion 2023, Self-Refine 2023, CRITIC 2023, Self-RAG 2024, PRMs 2025) assumes in-memory, in-session execution. Even the 2026 convergence papers operate at the semantic-embedding layer and do not tie convergence to a persistent execution record. Weng's 2026 "verifiability constraint" essay names the substrate need but frames durable state as an engineering recommendation, not a research architecture. Ambroise et al.'s 2026 verification-hierarchy formalization identifies execution-grounded verification as a level of the hierarchy but does not architecturally instantiate it.

**No published academic work addresses the organizational deployment question this paper answers.** Industry has partial answers (Replit reinvented Temporal; Vercel and Databricks built their own durable layers) but no reference architecture has been documented that combines durable orchestration + heterogeneous edge compute + subscription-tier authentication + composable module design standards.

### 2.3 Real-world convergence — very fresh, asymmetric across vendors

- **Temporal Replay 2026** shipped four AI-relevant primitives: Serverless Workers on AWS Lambda, Workflow Streams, External Payload Storage (S3-backed, keeps histories bounded despite tokenized traffic), Standalone Activities
- **OpenAI Agents SDK**: GA on Temporal
- **Google ADK**: public preview with native Temporal integration (April 20, 2026)
- **Anthropic Claude Agent SDK: no first-party Temporal integration**
- **Vercel and Databricks built their own durable execution layers** (Workflow DevKit + WorkflowAgent, DBOS Postgres-backed checkpointing) — reinventing Temporal-shaped primitives because their target developers won't stand up a Temporal cluster

**This asymmetry is load-bearing for the paper.** The obvious substrate for a Claude Code-based self-improvement loop is not yet paved road. The paper's reference architecture applies to any authenticated edge compute — Claude Code, OpenAI API, Ollama, non-AI orchestration — and specifically fills the integration gap that exists today for organizations using subscription-tier Anthropic tooling at team scale.

---

### Novelty landscape

### 3.1 What exists

| Layer | Prior work | Status |
|---|---|---|
| Reflective loops (in-memory) | Reflexion, Self-Refine, CRITIC, Self-RAG, PRMs | Mature academic literature |
| Hierarchical agents | AgentOrchestra (2026, TEA Protocol), HALO (2025, planner/role-designer/executor + MCTS), AiScientist (2026, File-as-Bus + ablation) | Emerging 2025-2026 |
| Reflection convergence formalism | 2512.10350 (attractor dynamics), 2512.00047 (code stability, semantic self-consistency, lexical confidence) | Semantic-layer only; not tied to execution record |
| Verification hierarchy | Ambroise et al. (2026) formalization | 2026 survey, framing the field |
| Verifiability constraint terminology | Weng (2026) essay | Names the problem, doesn't solve substrate |
| Durable workflow engines | Temporal, Cadence, Restate, Inngest | Mature production tech |
| Durable AI orchestration frameworks | Temporal AI Bundle (2026), Google ADK + Temporal (April 2026), Vercel Workflow DevKit (2026), DBOS-on-Databricks | Announced 2026, asymmetric across vendors |
| Production case studies | Replit (reinvent-then-adopt), OpenAI Codex web, Lovable, Vercel, Databricks | Documented industry pattern |
| Independent teardown of naive alternatives | Diagrid (LangGraph checkpoints), Vadim's blog, Oblique News | Multiple corroborating sources |
| **Reference architecture for federated agentic orchestration on heterogeneous edge compute** | **GAP** | **Not yet published** |
| **Composable workflow module design standards for agentic workloads** | **GAP** | **Not yet published; author has a production instance** |

### 3.2 The specific gap this paper addresses

**No published reference architecture combines the following four elements as a coherent design:**

1. **Durable orchestration** at the server tier (Temporal or equivalent event-sourced workflow engine)
2. **Heterogeneous edge compute** where any authenticated capability endpoint (Claude Code, OpenAI API client, Ollama, HTTP service, non-AI operation) can execute dispatched activities
3. **Subscription-tier authentication elegance** where user credentials stay at the edge, eliminating central-proxy ToS gray areas
4. **Composable module design standards** for authoring workflows/helpers/activities as reusable LEGO-block libraries with binding conventions on layer separation, semantic naming, typed contracts, and idempotent execution

The four elements exist independently. Industry has partially combined subsets (Replit, Vercel, Databricks). No academic or industry publication has documented the four-element composition as a REFERENCE ARCHITECTURE with articulated design principles and validated module standards.

### 3.3 Novelty claim (defensible)

> This paper proposes the first documented reference architecture for team-scale federated agentic orchestration on heterogeneous edge compute, combining (a) durable server-tier workflow orchestration, (b) subscription-tier edge authentication that sidesteps central-proxy ToS concerns, (c) heterogeneous edge capabilities including subscription-based AI reasoning agents alongside API services and non-AI operations, and (d) composable module design standards derived from a multi-year production implementation. The architecture fills the deployment gap that currently forces organizations to choose between per-user tools without orchestration and centralized platforms with prohibitive per-token cost, and specifically addresses the unpaved integration path for the Claude Agent SDK (which lacks the first-party Temporal integration OpenAI Agents SDK and Google ADK have).

Reviewers will read this as: "author is documenting a systems architecture that composes existing primitives (Temporal, Claude Code, MCP, subscription auth) in a novel way to solve a real organizational deployment problem, with production evidence for the module design standards."

Systems papers get published on exactly this kind of contribution. Netflix chaos engineering, Twitter Manhattan, LinkedIn Kafka origin paper — all describe compositions of existing primitives in novel ways with articulated design principles.

### 3.4 The "Anthropic gap" as forward-looking positioning

The paper explicitly frames its architecture as applicable to the integration gap OpenAI and Google have already filled for their agent frameworks but Anthropic has not. This positions the paper as forward-looking without being speculative — the integration will happen (or should happen); this paper defines what its properties should provide when it does. If Anthropic ships a first-party solution during peer review, the paper's contribution shifts from "here's how to do it" to "here's the design space Anthropic's solution should be evaluated against" — still defensible.

---

### The design axioms

Five axioms the paper's architecture rests on. Each has an anchor citation for defense.

### 4.1 Edge autonomy — "edge owns what edge is better suited for"

The central design principle. The edge tier owns anything the edge is inherently better positioned to own:
- **User authentication** — user's account on user's machine; no shared central credentials
- **Local compute** — LLM invocation, tool execution, file I/O; wherever the work actually happens
- **Ephemeral state** — session data, git worktrees, local files; state that has no cross-user meaning

The server tier owns only what it is inherently better positioned to own:
- **Workflow definitions** — the shared library of reusable modules
- **Orchestration state** — which workflows are running, what's blocked on what, retry counters
- **Coordination signals** — cross-edge visibility, human-in-the-loop pauses, scheduling
- **Cross-run artifacts** — persistent outputs that need cross-user or cross-time queryability

Corollary: **the server never impersonates the edge.** No shared credentials at the server means no central-proxy ToS gray area. Multi-tenancy = user auth on user machine, not shared compute.

### 4.2 "A deterministic sequence of non-deterministic things"

Borrowed verbatim from the Google ADK + Temporal integration blog (April 2026). Every LLM call, every tool invocation, every external API request is a non-deterministic side effect wrapped in a deterministic workflow. The workflow describes intent; activities produce effect. This maps cleanly onto Temporal's fundamental workflow/activity separation and onto the module design standards' three-layer discipline (§5).

### 4.3 Verifiability via execution record

Positions the paper's substrate in Ambroise et al.'s verification hierarchy at the **execution-grounded** level (formal verifier > execution-grounded > retrieval-grounded > LLM-judge > intrinsic self-critique). The Temporal event history + activity result payloads + externally-stored artifacts provide a queryable execution record that supports post-hoc audit, replay-based debugging, and cross-run reasoning by CPI-style reflective loops. This is one level above what in-memory reflection can access.

### 4.4 Rate-limit-aware coordination as a first-class concern

Rate limits are not an implementation detail; they are a real production constraint that shapes agent architecture. Temporal's activity-level retry policies (exponential backoff, jitter, controlled error-code vocabularies) and workflow-level scheduling give the substrate an honest answer to rate-limit constraints across subscription-tier and API-tier edges alike. The paper's architecture treats this as a design property, not an ops workaround.

### 4.5 Composition over reimplementation

Generic activities compose into semantic wrappers, which compose into workflows, which compose into parent workflows. Parent workflows gain the full behavior of children with minimal new design. This is how a modest module library produces exponentially many higher-level workflows without exponentially many new components. The DRY discipline applies at the workflow layer, not just the code layer.

---

### What not to do

Explicit anti-scope for this paper:

- **Do not build a Temporal PoC before submission.** The methodology (novel architecture with theoretical justification, grounded in production evidence from existing standards) does not require new implementation. `mdc-master-planning` provides production evidence for §5 standards; `claude-dot-files` provides informal evidence for §6.3; Replit + AiScientist provide external validation.
- **Do not use insider jargon.** The paper's audience is grad-level reviewers with no context on the author's specific business platform. Reference the `mdc-master-planning` repo for provenance, but abstract every principle to universal terms. Do not name internal workflows, custom infrastructure services, or domain-specific components as if they were common knowledge.
- **Do not overreach on novelty claims.** The specific novelty is the four-element composition as reference architecture + the module design standards as ecosystem contribution. Overclaiming ("solving AGI orchestration," "novel LLM training regime") weakens the paper.
- **Do not skip the ethical / limitations discussion.** Grad-level paper requires it. Not optional.
- **Do not exceed 18 pages.** Page limit is real; tight writing is a virtue.
- **Do not present `claude-dot-files` as the flagship case study.** Replit is the industry flagship; the author's production standards corpus is the module-design flagship. `claude-dot-files` is corroborating informal evidence.

---

### Bibliography

**See separate deliverable: `annotated_bibliography.md`.**

Curated to 10-12 primary sources spanning reflection foundations, 2026 field framing, hierarchical architecture, durable execution, industry convergence, and production case studies. Full 71-source pool available in `research/raw/*.md` for inline paper citations beyond the annotated bibliography.

Bibliography retains v2 curation — no changes needed for the v3 framing pivot because all cited sources support the systems-architecture framing as well as they supported the analysis framing.

---

### Open questions, resolved this cycle

Locked from prior sessions:

| Q | Decision |
|---|---|
| Reflection vs orchestration framing | Reflection as anchor topic; orchestration architecture as core contribution |
| Case study weight | Replit flagship + AiScientist empirical + production standards corpus (author's) + `claude-dot-files` corroboration |
| Google ADK scope | Brief mention in §2.4; framing sentence borrowed in §3.1 and §4.2 |
| Ethical section depth | 0.5 page in §7.4; dual-use framing |
| Verifiability constraint engagement | Motivation reference in §1; cited in §2.2 (Weng, Ambroise); revisited in §4.3 as design axiom placement |
| Bibliography quality | Verified via research syntheses; 10-12 curated sources; production standards corpus adds provenance for §5 |
| Naming | "The proposed architecture" as running descriptor; no product name yet; author retains flexibility for future branding |
| Attribution of production standards | Reference `mdc-master-planning` repo by name for provenance; abstract principles to universal terms; no insider jargon |
| Framing pivot from v2 | Confirmed 2026-07-24 morning; v3 recasts as systems architecture contribution rather than analytical claim |

---

---

## Action candidates

Reviewable items, sized for a standup. Nothing here is ratified — a candidate becomes binding only by being codified into a standard through human review.

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Adopt durable execution for the workflow layer**, for durability and resumability — *not* to gain composition, which already works in bash | adopt | `durable_execution.md`, `temporal.md` |
| 2 | **Keep authentication at the edge.** Subscription-tier auth on the machine holding the repo, credentials never crossing to the server tier | adopt | `anthropic_tos_and_enterprise.md` |
| 3 | **Separate the run that authors from the run that judges** — the composition boundary is a review boundary and a retry point | adopt | `hierarchical_agents.md`, `reflection_literature.md` |
| 4 | **Treat the shared workflow library as the first-class artifact**, not any individual workflow | new concept | `production_cases.md`, `hierarchical_agents.md` |
| 5 | **Do not build agent-as-durable-unit.** Canonical for a metered API integration; wrong shape for a subscription CLI overlay | change direction | `anthropic_tos_and_enterprise.md`, `claude_code_integration_surface.md` |
| 6 | **Verify the hook survives a narrowed `--setting-sources` before touching it** | no change, pending test | `hook_sourcing_supplement.md` |

### Homeless candidates

- **A defined shape for production feedback.** Operator and burn-test findings have driven more workflow fixes than log analysis has, and arrive as ad-hoc markdown handoffs. No surface owns this. *Named as homeless per §4 — not parked elsewhere.*

## Gaps this cycle did not cover

- **Inter-process handoff contracts** — the highest-value remaining gap; the Memory Management phase currently reasons from one informal survey
- **Convergence-based stopping conditions** — depends on the above
