> **Provenance:** carried over from the CSCI-6905.604 research project (`research_project/research_direction.md`, v3), 2026-08-03.
> Placed here as the prior-run synthesis so the next `research.sh` reassesses against real prior work rather than a cold start.

---

# CSCI-6905.604 Research Project — Direction Document (v3)

**Author:** Eric Rue
**Course:** CSCI-6905.604 Applied Agentic AI
**Due:** July 26, 2026 (Sunday) — 11:59 PM
**Status:** Direction committed 2026-07-23; refined with background research; **v3 pivot 2026-07-24 morning** — reframed as systems architecture contribution after Author's pushback on prior novelty framing.

**v3 changes** — see §13 "What changed in v3" at the end for the diff summary.

---

## 1. Committed Direction

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

## 2. Why This Topic — The Fit

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

## 3. Novelty Landscape

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

## 4. The Design Axioms — Bigger Picture Contributions

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

## 5. Proposed Paper Structure (12-18 pages)

Target ~14-15 pages excluding title, TOC, bibliography.

### §1 Introduction (~1.5 pages)
- Opening hook: organizations increasingly need agentic AI at team scale, and the current market forces a false trade-off
- Concrete example: Replit's reinvent-then-adopt arc (launched September 2024 on custom orchestration; migrated to Temporal by November 2024; 99.9999% trailing 30-day uptime)
- The specific Anthropic-integration gap
- Research question stated
- Contributions listed (5 bullets, mapped to §3.3 novelty claim's four elements + the module standards contribution)
- Paper roadmap

### §2 Background & Related Work (~2 pages — compressed)
- **§2.1 Reflective self-improvement lineage** — Self-Refine → Reflexion → CRITIC → Self-RAG → PRMs → 2026 convergence work. Note the shared in-memory assumption.
- **§2.2 The verifiability constraint and verification hierarchy** — Weng (2026), Ambroise et al. (2026). Position the paper's substrate at the execution-grounded level.
- **§2.3 Hierarchical agent architectures** — AgentOrchestra (TEA Protocol), HALO (planner/role-designer/executor), AiScientist (File-as-Bus, empirical anchor). Brief.
- **§2.4 Durable execution and industry convergence** — Temporal Replay 2026 primitives, OpenAI/Google integrations, the Anthropic gap, LangGraph teardown as hostile witness. Compressed.
- **§2.5 Production case studies** — Replit (reinvent-then-adopt), Vercel/DBOS (rebuilt-because-couldn't-adopt), AiScientist ablation as empirical anchor. Brief.

### §3 The Proposed Architecture (~3 pages)
- **§3.1 Framing** — "a deterministic sequence of non-deterministic things" (Google ADK, 2026)
- **§3.2 Two-tier topology**
  - **Server tier:** Temporal server + Postgres + object storage + shared workflow library host
  - **Edge tier:** Temporal worker + one or more capability endpoints (Claude Code, OpenAI/Anthropic API client, Ollama, HTTP service adapter, non-AI operation)
- **§3.3 Federation protocol** — server dispatches activities to task queues; edges pull activities they're registered for; results flow back via activity return; payload discipline (§5.5) governs what lives in event history vs artifact storage
- **§3.4 Deployment topologies** — three brief examples showing the reference architecture's generality:
  - Developer team workflows (edges = developer laptops with Claude Code)
  - Infrastructure operations (edges = bastion VMs with Ansible/Terraform capabilities)
  - Home / edge automation (edges = local VMs running Home Assistant integrations)
- **§3.5 Formal properties provided** — enumerated: durability, verifiability via event history, extended horizon, first-class human-in-the-loop, rate-limit-aware coordination, idempotent tool execution, compensable multi-step operations, observability

### §4 Design Axioms (~1.5-2 pages)
- **§4.1 Edge autonomy** ("edge owns what edge is better suited for") with corollary (server never impersonates edge → ToS elegance)
- **§4.2 Deterministic-sequence framing** (verbatim Google ADK)
- **§4.3 Verifiability via execution record** (Ambroise hierarchy position)
- **§4.4 Rate-limit-aware coordination** as first-class concern
- **§4.5 Composition over reimplementation** (generic → semantic wrapper → workflow → parent workflow)

### §5 Module Design Standards (~3 pages)
Presented as a set of ten binding rules that make workflow modules composable, reusable, and CPI-ready. Attributed to the author's production implementation of these principles (the `mdc-master-planning` standards repository), which validates the standards at scale in a real infrastructure automation context.

- **§5.1 Three-layer discipline** — Workflow (orchestration, deterministic) / Helper (pure compiler) / Activity (side effects). Universal separation of concerns.
- **§5.2 Semantic wrapping** — Generic reusable executors + workflow-scoped semantic wrappers with intent-first names. Same building block, different named intents. Solves the "identical generic names in the UI" observability problem.
- **§5.3 Typed input contracts** — One input dataclass per semantic activity, named after the activity. Dict-serialized on the wire; wrapper reconstructs at the top. No positional args across layer boundaries.
- **§5.4 Activity registry pattern** — String keys from the helper's execution plan resolve to registered activity callables via a per-module map. Central registration; no dynamic dispatch magic.
- **§5.5 Structured result contract** — Every activity returns a structured payload: status (`ok` / `changed` / `skipped` / `failed`) + details + artifacts + metrics + error_code. Machine-readable outcome, not free-form text. This is the observability contract that makes CPI-style reflective loops possible without bespoke instrumentation.
- **§5.6 Idempotency by construction** — Every activity is idempotent. Check-then-act, compare-and-swap, no side-effect duplication on retry.
- **§5.7 Controlled error vocabularies** — Per-external-system UPPER_SNAKE_CASE codes with defined retry semantics (transient vs terminal). Bare HTTP status codes cannot distinguish terminal from transient; controlled vocabularies can.
- **§5.8 Composition over reimplementation** — Child workflows for reuse; parents compose full child behavior with minimal new design. Situational (compose where it benefits), not mandate-to-decompose.
- **§5.9 Standardized file layout** — Workflow modules organized as `modules/{domain}/{purpose}/{name}_{workflow,helper,activities}.py`; generic executors as `activities/{domain}/` — reflects the three-layer separation at the filesystem.
- **§5.10 Semantic boundaries in the observability surface** — The orchestration UI shows meaningful activity types per intent, not repeated generic names. Debug-time observability is a first-class design concern.

### §6 Case Studies (~1.5 pages)
- **§6.1 Replit as the industry flagship** — the cleanest documented reinvent-then-adopt arc; Michele Catasta quote; 99.9999% trailing 30-day uptime post-migration
- **§6.2 AiScientist File-as-Bus ablation as empirical anchor** — 6.41 pt PaperBench drop, 31.82 pt MLE-Bench Lite drop when File-as-Bus is removed; the strongest single data point that hierarchical orchestration + durable state are one mechanism
- **§6.3 The author's production standards as informal validation** — abstracted reference to the `mdc-master-planning` standards corpus (662 lines for the Temporal standard alone with cross-references to 20+ peer standards) as evidence that the §5 module design standards work at scale in a real infrastructure automation context; formal empirical evaluation is deferred to future work

### §7 Discussion (~1.5 pages)
- **§7.1 Limitations** — durable substrate is necessary but not sufficient (version-drift, product-layer gaps, ~30-minute-task threshold below which durability is pure cost); the ~30-minute threshold is a rough heuristic, not a bright line
- **§7.2 Terms-of-service considerations for subscription-tier edges** — the edge-autonomy axiom is what makes subscription-tier authentication ToS-clean; if the axiom is violated (e.g., central-proxy compute), the ToS story changes materially; this is a design constraint, not a workaround
- **§7.3 Timing risk** — Anthropic could ship a first-party solution; historical precedent (Netflix Chaos Monkey documented as a pattern before AWS shipped Chaos Engineering) suggests reference architectures remain valuable even when vendor products emerge
- **§7.4 Ethical considerations** — audit trails are dual-use (accountability vs surveillance); the paper's architecture makes both easier; brief but explicit engagement
- **§7.5 Failure modes** — self-confirming loops, model collapse, diversity collapse (Ambroise et al.); durable substrate does not prevent these but makes them detectable via replay

### §8 Future Work + Conclusion (~1 page)
- Formal empirical evaluation (benchmark vs LangGraph/CrewAI/plain-Python-loop on convergence rate + wall-clock + cost)
- First-party Claude Agent SDK + Temporal integration
- Package management for workflow modules (currently no npm-equivalent exists for Temporal)
- Extension to non-software domains (research agents, ops agents, edge automation)
- Rate-limit-aware learning schedules as a research variable
- **Conclusion:** restate the four-element composition + module standards contribution; reiterate that the competitive edge has shifted from model capability to orchestration quality (Zylos 2026); federated architecture is the deployment model; standardized modules are the ecosystem the field currently lacks

### Reproducibility Appendix
- Reference to the `mdc-master-planning` standards repository as production evidence
- Design sketches for the reference architecture's server + edge topology
- Sample module skeleton illustrating the three-layer discipline
- Environment setup notes (Temporal server via docker-compose or k3s, Claude Agent SDK, Python)

---

## 6. Three-Day Execution Plan (updated — research is DONE, framing is LOCKED)

**Given:** Today is Friday 2026-07-24 morning. Due Sunday 2026-07-26 at 23:59. Research base is complete + framing pivoted to systems architecture contribution.

### Friday (7-9 hours — heaviest writing day)
- Morning: read the 4 research summaries (if not done), read `mdc-master-planning` Temporal standard for §5 grounding, read this doc v3 + `annotated_bibliography.md` v2 + `paper_outline.md` v2 (when ready)
- Draft §1 Introduction (in your voice, using the sketch in `paper_outline.md`)
- Draft §2 Background (compressed — literature synthesis, following outline)
- Draft §3 Reference Architecture (your voice — this is a core contribution section)

### Saturday (7-9 hours)
- Draft §4 Design Axioms (your voice — the axioms are your framing)
- Draft §5 Module Design Standards (draws heavily from `mdc-master-planning` corpus — abstract the principles, cite the repo for provenance, keep insider jargon out)
- Draft §6 Case Studies (Replit + AiScientist + your production standards abstracted)
- Draft §7 Discussion + §8 Future Work + Conclusion
- Draft Reproducibility Appendix
- First full read-through, revise for flow

### Sunday (4-6 hours — polish + submission)
- Second read-through, revise for precision + jargon-scrub
- Record 8-10 minute presentation (narrate the paper's argument from §1 → §3 → §5 → §8)
- Assemble submission bundle: paper PDF, annotated bibliography PDF, presentation video, source code reference (link to `claude-dot-files` as informal case study; link to `mdc-master-planning` as production standards evidence)
- Submit before evening — do not push to the 23:59 deadline

**Total effort estimate:** 18-24 focused hours across 3 days. Aggressive but doable — research and standards material are both banked.

---

## 7. What NOT To Do

Explicit anti-scope for this paper:

- **Do not build a Temporal PoC before submission.** The methodology (novel architecture with theoretical justification, grounded in production evidence from existing standards) does not require new implementation. `mdc-master-planning` provides production evidence for §5 standards; `claude-dot-files` provides informal evidence for §6.3; Replit + AiScientist provide external validation.
- **Do not use insider jargon.** The paper's audience is grad-level reviewers with no context on the author's specific business platform. Reference the `mdc-master-planning` repo for provenance, but abstract every principle to universal terms. Do not name internal workflows, custom infrastructure services, or domain-specific components as if they were common knowledge.
- **Do not overreach on novelty claims.** The specific novelty is the four-element composition as reference architecture + the module design standards as ecosystem contribution. Overclaiming ("solving AGI orchestration," "novel LLM training regime") weakens the paper.
- **Do not skip the ethical / limitations discussion.** Grad-level paper requires it. Not optional.
- **Do not exceed 18 pages.** Page limit is real; tight writing is a virtue.
- **Do not present `claude-dot-files` as the flagship case study.** Replit is the industry flagship; the author's production standards corpus is the module-design flagship. `claude-dot-files` is corroborating informal evidence.

---

## 8. Annotated Bibliography

**See separate deliverable: `annotated_bibliography.md`.**

Curated to 10-12 primary sources spanning reflection foundations, 2026 field framing, hierarchical architecture, durable execution, industry convergence, and production case studies. Full 71-source pool available in `research/raw/*.md` for inline paper citations beyond the annotated bibliography.

Bibliography retains v2 curation — no changes needed for the v3 framing pivot because all cited sources support the systems-architecture framing as well as they supported the analysis framing.

---

## 9. Open Questions — Now Resolved

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

## 10. Research Files Reference

All raw research syntheses live in `research/raw/`:

- **`reflection_literature.md`** (~2,200 words, 14 sources) — §2.1, §2.2, motivation, verification hierarchy engagement
- **`durable_execution.md`** (~1,800 words, 24 sources) — §2.4, §3, §4.2, Anthropic gap evidence
- **`hierarchical_agents.md`** (~1,750 words, 14 sources) — §2.3, §3.4 composition mechanism, §4.5 composition axiom
- **`production_cases.md`** (~1,690 words, 19 sources) — §2.5, §6.1 Replit, §6.2 AiScientist, hostile witness citation

Production standards reference (for §5 grounding):
- **`/home/puma/Repos/mdc-master-planning/standards/development/temporal/`** — Temporal standard (662 lines) + Worker Deployment standard + Stateful Patterns standard
- **`/home/puma/Repos/mdc-master-planning/CLAUDE.md`** — corpus-level index; useful to understand the scale of the standards ecosystem but not directly cited in the paper

Total curated research: ~7,440 words + 71 external sources + a production standards corpus of hundreds of pages.

---

## 11. Grade Weight Reference

From assignment doc (`research_assignments.md`):

| Category | Weight | Where this paper wins |
|---|---|---|
| Research Depth | 30% | 10-source annotated bib, 71 sources in reserve, verification-hierarchy framing engagement, production standards corpus as fifth evidence category |
| Technical Rigor | 10% | Systems architecture methodology; formal design axioms in §4; formal design standards in §5 with production validation |
| Insight & Originality | 20% | The four-element composition as reference architecture; the Anthropic-gap observation as forward-looking positioning; the edge-autonomy axiom as ToS elegance |
| Communication | 10% | Structure planned; jargon-scrub pass on Sunday; author voice preserved by NOT drafting §3-§5 substance for the author |
| Presentation | 30% | 8-10 min recording — narrate the paper's argument from §1 → §3 → §5 → §8 |

**Highest-leverage areas:** Research Depth (30%) and Presentation (30%). Plan 2-3 hours on Sunday for the presentation recording — it's a third of the grade.

---

## 12. Session Handoff Notes (For Author's Return)

When you come back to this document:

1. **First read (30-45 min):** the 4 raw research summaries in `research/raw/` if not done. Recommended order: `production_cases.md` → `durable_execution.md` → `reflection_literature.md` → `hierarchical_agents.md`
2. **Second read (10 min):** this doc — confirm the framing still resonates; §3.2 novelty claim and §5.10 standards enumeration are the two places to gut-check
3. **Third read (10 min):** `annotated_bibliography.md` — verify sources
4. **Fourth read (10 min):** `paper_outline.md` — confirm structure
5. **Fifth read (as needed during §5 drafting):** `/home/puma/Repos/mdc-master-planning/standards/development/temporal/temporal_standard.md` — the source material for §5's ten design standards; abstract each principle to universal terms during writing
6. **When ready to draft:** ping the session with "let's draft §1" or "let's flesh out §3." I'll write to your voice, you'll edit.

**If any framing feels off:** name it before drafting. The topic is committed; the framing is now locked at v3 unless you surface a concrete objection.

**Timeline reminder:** 18-24 hours of focused work across the next 3 days. Front-load the reading Friday morning; the writing is the easy part once the argument is clear.

---

## 13. What Changed in v3

For reference on the diff between v2 (evening 2026-07-23) and v3 (Friday morning 2026-07-24):

- **Framing pivoted from analytical claim to systems architecture contribution.** V2 argued "durable execution is the substrate for reflective loops." V3 argues "the proposed reference architecture composes four elements — durable orchestration + heterogeneous edge compute + subscription-tier edge auth + composable module standards — to solve an organizational deployment problem."
- **Research question restated.** V2: "Can durable execution serve as the substrate for verifiable multi-day reflective self-improvement loops in production software engineering agents?" V3: "How can an organization deploy self-improving agentic AI workflows at team scale without forcing a trade-off between per-user tools without orchestration and centralized platforms with prohibitive per-token cost?"
- **Title updated.** V2: "Beyond In-Memory Reflection: Durable Execution as the Substrate for Long-Horizon Self-Improving Agent Systems in Software Engineering." V3: "Federated Agentic Orchestration: A Reference Architecture for Team-Scale Self-Improving Workflows on Heterogeneous Edge Compute."
- **Design axioms surfaced as first-class content.** V4 has a dedicated §4 for the five design axioms (edge autonomy, deterministic sequence, verifiability via execution record, rate-limit-aware coordination, composition over reimplementation). V2 had these implicit throughout §3-§4.
- **Module Design Standards section added.** New §5 draws from the author's production standards corpus (`mdc-master-planning`), enumerating ten binding rules that make workflow modules composable, reusable, and CPI-ready. Attributed to production origin; principles abstracted to universal terms.
- **Case study restructure.** V2 had Replit + AiScientist + `claude-dot-files`. V3 promotes the author's production standards corpus to fourth evidence category alongside `claude-dot-files` (both attributed to author's production practice, at different levels of formality).
- **Anthropic gap sharpened as forward-looking positioning.** V2 framed it as a fact. V3 explicitly positions the paper as filling the integration gap OpenAI and Google have already filled for their frameworks but Anthropic has not.
- **Working name adopted.** V2 had "SkyyNet" or generic. V3 uses "the proposed architecture" as running descriptor throughout, per author's decision.
- **Anti-scope expanded.** New rule: no insider jargon; production standards referenced for provenance but principles abstracted to universal terms.
- **Timeline unchanged.** Still ~18-24 hours across 3 days; research and standards material are both banked.

---

*Document created 2026-07-23. Updated to v3 2026-07-24 morning after framing pivot to systems architecture contribution.*
