# Prior Art on the Four-Way Combination

```
Topic:          Has the four-way combination this product claims as novel already been built by someone else?
Feeds:          docs/standards/architecture/problem-statement.md § "What we are combining, and why it is novel" — the novelty claim itself
Last validated: 2026-08-03
Revalidate:     high — 4 weeks
Confidence:     Definitive that a system exists combining all four elements plus the deployment shape (bernstein, first-party docs + package registry + repo metadata). Derived on the element-by-element mapping (my inference against the problem statement's wording). Directional on the second-tier near-misses (tutti, kodo), whose docs are thinner. Unverified on runtime behaviour — no system in this paper was executed; every claim is documentation-level.
Critic:         not-yet-verified — 2026-08-03
```

> ## Headline finding — the novelty claim as written does not hold
>
> **A system exists that combines all four elements *and* the deployment shape.** It is [`bernstein`](https://github.com/sipyourdrink-ltd/bernstein) — Apache-2.0, Python, 777 stars, on PyPI at v3.13.0, created 2026-03-22, last pushed 2026-08-03 (the day of this search).[^gh-bernstein][^pypi-bernstein] Its own one-line description is *"Deterministic orchestrator for CLI coding agents (Claude Code, Codex, Gemini CLI, +40 more). No model in the coordination loop, so parallel runs in per-task git worktrees replay byte-identically."*[^gh-bernstein]
>
> It has WAL-backed crash recovery (E1), a janitor/gate/cross-model-verifier judging stack with a reviewer that has no stake (E2), plain-Python scheduling over typed task values with explicitly no LLM in the coordination loop (E3), a tick loop over a durable backlog with a "VP" cell above the worker cells (E4), and a STAR cluster topology where a central coordinator distributes to worker hosts that run the local CLI agents under their own installed auth (E5).
>
> **One element is genuinely short**, and bernstein's own docs say so: the *general* self-improvement write path is unwired — *"nothing files lessons automatically yet."*[^bern-lessons] The learning loop that IS closed is narrow: an append-only SQLite outcome ledger that feeds model-selection routing.[^bern-confidence]
>
> **The honest verdict:** the combination is not un-built. What survives as potentially distinctive is much narrower than "nobody has put these together" — see §5.

---

## 1. Primer: what was being tested, and how

The problem statement asserts four things "exist independently today… **Nobody has put them together**, and the combination is the contribution."[^problem-statement] Restating them as testable predicates, plus the deployment shape it names as the enabler:

| | Element | The predicate a candidate must satisfy |
|---|---|---|
| **E1** | Durable execution | A crashed or killed run **resumes** rather than restarts, from a persisted record of how far it got |
| **E2** | Layered self-improvement over durable artifacts | **Distinct actors at distinct layers** — one authors, one judges *with no stake*, one dispositions — reading and writing artifacts the others can see |
| **E3** | Memory as typed inter-step communication | A step leaves a **typed result** the next step reads **in code, no model in the loop**; a parent branches on a child's conclusion because it is a value, not prose |
| **E4** | High-level loops over many parent workflows | A **driver above the parents** choosing what runs next from persisted state, unattended until an **observable** exit condition |
| **E5** | Edge deployment shape | Work runs on **each participant's own subscription** at the edge; the server tier runs **no agent compute** and holds **no model credentials** |

**Search method** (stated so a negative finding would be credible, per Research Standard §3): web sweeps across durable-execution vendors' agent offerings, agent-orchestration frameworks, 2025–2026 arXiv on self-evolving/self-improving agents and agent harnesses, AI-DevOps and "agent fleet" products, and self-hosted/BYO-subscription runners; then depth-first on candidates via **raw** sources — `raw.githubusercontent.com` markdown, the GitHub REST API's JSON repo metadata, PyPI's JSON API, and arXiv `/abs` pages. Rendered marketing pages were used only for landscape orientation and are marked at reduced confidence throughout, per the standard's fabrication-surface rule.

The single highest-yield artifact was a community index, `andyrewlee/awesome-agent-orchestrators`, which catalogues ~150 orchestrators by category and whose one-line descriptions are precise enough to shortlist against E1–E5 directly.[^awesome-orch] Two of its entries read as near-verbatim restatements of the problem statement's own elements: *"Keeps no model in the coordination loop, so orchestration costs zero tokens"* (bernstein) and *"Config-driven workflows passing typed artifacts between agents"* (tutti).[^awesome-orch] **The existence of a curated 150-entry list in this exact category is itself a finding** — this is a crowded space, not an empty one.

**This paper does not re-cover** what durable execution provides (`raw/durable_execution.md`), who adopted it and what they hit (`raw/production_cases.md`), or the published hierarchical-agent architectures (`raw/hierarchical_agents.md`). It cites them and asks the question they do not: *does anything combine the four?*

## 2. The match: bernstein, element by element

All claims in this section are **definitive** at the documentation level (first-party repo docs fetched raw) and **unverified** at the behavioural level (nothing was executed). Quoted spans appeared inside quotation marks in the fetched text.

### E1 — Durable execution ✅

`docs/architecture/state-persistence.md` documents a write-ahead log at `.sdd/runtime/wal/*.wal.jsonl` with three invariants: append-only via `write() + flush() + fsync()`, a hash chain where each entry's `prev_hash` matches the prior digest, and a per-entry fsync guarantee that *"A process crash immediately after `append()` returns cannot lose the entry."* Restart recovery is a documented sequence: load the durable backlog, scan uncommitted WAL entries, replay through an idempotency filter, reset tasks stuck in `claimed`, resume the tick loop. The doc's summary claim: *"kill `bernstein run`, restart it in the same workdir, and your task graph comes back."*[^bern-state] Durable surfaces enumerated: backlog YAML, WAL, idempotency markers, metrics, a content-addressed artifact store (`.sdd/cas/`), and audit logs with Merkle seals.[^bern-state] `llms-full.txt` lists *"WAL-backed crash recovery"* as a shipped capability.[^bern-llmsfull]

**Boundary, stated by bernstein itself:** the in-process run actor is *"In-memory only. Persistence is out of scope; pair with the existing WAL if durability is required."*[^bern-runactor] So durability is a property of the backlog/WAL layer, not of every component — which is precisely the layering Temporal-style systems also have. This is a *narrower* durability guarantee than a replay-based engine (no deterministic workflow replay of arbitrary orchestration code), and it is hand-rolled rather than bought — exactly the "hand-rolled durability" pattern `raw/production_cases.md` §4 documents across the industry.[^prod-cases]

### E2 — Layered judging ✅ / self-improvement loop ⚠️ PARTIAL

`docs/architecture/quality-pipeline.md` documents three sequential verification layers: a **janitor** evaluating declarative completion signals (file existence, tests pass, regex match), a **gate pipeline** running build/lint/type/test/security against the actual diff, and an optional **cross-model verifier** that sends the diff to *"a *different* model (a cheap one from a different provider)"* for independent review.[^bern-quality] The README's four-stage arc is *Decompose → Spawn → Verify → Merge*, with disposition explicit: *"Failed tasks get retried or routed to a different model."*[^bern-readme]

Mapped onto E2: **author** = the spawned CLI agent in its worktree; **judge with no stake** = the cross-model verifier, a different provider's model reviewing another provider's output; **disposition** = the merge gate plus retry/reroute. The artifacts are shared and durable — worktrees, CAS blobs, the audit chain. *(derived — the role mapping is my inference from bernstein's docs, not their framing.)*

**Where it falls short, per bernstein's own documentation.** Lessons live in `.sdd/memory/lessons.jsonl` with tags, confidence, memory type and a SHA-256 integrity chain; `spawner_core.py` reads them at task assignment via `gather_lessons_for_context()`. But the write path is not wired: *"nothing files lessons automatically yet"* — `file_lesson()` is *"fully implemented, tested, and safe to call"* yet *"no code path in the shipped orchestrator calls it,"* and *"nothing currently reads a task's outcome and writes a lesson on completion."*[^bern-lessons] The autofix telemetry path is likewise operator-mediated rather than closed.[^bern-autofix]

**The loop that IS closed** is narrow but real: `docs/quality/empirical-confidence.md` documents an append-only SQLite `agent_outcomes` ledger keyed `"role:<task.role>|model:<model_key>"`, queried after a minimum sample count (default 5), whose result is the first-ranked input to `recommend_models` ahead of a bandit fallback and a heuristic fallback.[^bern-confidence] That is a durable artifact written by one part of the system and read **in code** by another to change future behaviour — E2's mechanism, applied to model routing only.

### E3 — Code-routed control flow over typed values ✅

This is the leg the problem statement treats as most distinctive, and it is bernstein's **headline marketing claim**, not a buried feature. `docs/architecture/WHY_DETERMINISTIC.md`: *"There are no LLM calls in this loop. No model decides which task to run next, which agent to assign it to, or whether the agent is making progress."*[^bern-why] The README: *"No LLM in the coordination loop. Scheduling is plain Python, ensuring reproducible end-to-end runs. Replaying yesterday's plan yields yesterday's task graph."*[^bern-readme] One LLM call decomposes the goal into tasks carrying roles, owned files and completion signals; everything after is Python over those values.[^bern-readme]

Bernstein's stated rationale is close to identical to the problem statement's. It documents a *motivating failure*: a predecessor orchestrator ("PAPA") that delegated scheduling to an LLM managing 12 workers, where only ~3 completed meaningful work, the coordinator went unresponsive and starved downstream workers, and *"Sleep is not a prompt engineering problem - it is a fundamental property of long-lived LLM sessions."*[^bern-why] It claims four consequences: no hallucinating/sleeping single point of failure; *"The deterministic orchestrator spends zero tokens on scheduling decisions"*; reproducible unit tests instead of probabilistic outcomes; and O(tasks)-per-tick scheduler cost instead of quadratic context growth.[^bern-why] It also states the trade-off honestly — clearer task specs up front, no mid-execution replanning by the orchestrator.[^bern-why]

Typed inter-step state is documented across `docs/concepts/` and `docs/architecture/`: `feature-contract.md`, `artifact-lineage.md`, `jsonl-memory-log.md`, `schema-validation-retry.md`, `schema-registry.md`, `cas-store.md`.[^bern-docs-concepts][^bern-docs-arch] Cross-worker dependency gating is a **typed** predicate evaluated in code: a task declares `{"needs": ["<producer-task-id>"]}` and *"The claim API never offers a task whose dependencies are not all in a terminal-success state"* — enforced at three endpoints, with `409 Conflict` on a blocked claim.[^bern-workers]

### E4 — A driver above the parents ✅

Three mechanisms, all documented:

- **The tick loop over the durable backlog.** Recovery ends by "resume the tick loop"; the scheduler is O(tasks) per tick; work is pulled by role from persisted open tasks.[^bern-state][^bern-why]
- **Multi-cell with a VP layer.** Cells are independent units *"each with its own manager and worker pool"*; above them sits *"a VP cell above them that only handles cross-cell concerns"* which scans status, posts to a bulletin board and makes rebalancing recommendations without executing work. Cell membership is a typed field: tasks carry `cell_id` and are fetched via `GET /tasks?status=open&cell_id=<id>`.[^bern-multicell]
- **Declarative multi-stage plans.** `bernstein run plan.yaml` executes YAML DAGs of agent / command / loop nodes.[^bern-readme]

**Boundary:** multi-cell *"runs cells in one process against one task server. It is not the same mechanism as multi-host fan-out,"* and the VP makes *recommendations* rather than issuing control-flow decisions.[^bern-multicell] So E4 is satisfied by the tick-loop-over-backlog and the plan DAG more strongly than by the VP layer. *(derived.)*

### E5 — Edge deployment shape ✅ (with one caveat)

`docs/cluster/deployment-patterns.md` documents a STAR topology: one **central server** running orchestrator, API, task store, node registry and task assignment; **N worker hosts** on separate machines that *"register, heartbeat, and pull tasks"* and advertise the roles they can execute.[^bern-cluster] Coordination state is a journaled HTTP-accessible store with HMAC-chained JSONL, such that *"rebuilding the store from the same JSONL journal reproduces the identical eligibility projection."*[^bern-workers] mTLS setup is documented separately.[^bern-docs-cluster]

Model credentials stay with the local CLI agent: bernstein drives 40+ CLI agent adapters (Claude Code, Codex, Gemini CLI, Aider, Cline, Continue, Cursor, Zed…), with *"file-based state, no SaaS dependency, and no third-party data plane,"* and mixes *"cheap local models"* with cloud subscriptions in the same run.[^bern-readme][^bern-substrate]

**Caveat, and it matters:** the cluster docs' credential discussion covers **cluster auth tokens** (`BERNSTEIN_AUTH_TOKEN` / `BERNSTEIN_CLUSTER_AUTH_SECRET`, distributed *"out of band (scp, your secrets manager, etc.)"*), not model credentials.[^bern-cluster] The claim "the central server runs no agent compute" is **derived** from the documented division of labour (coordinator assigns; workers claim and execute), not from an explicit first-party sentence saying so. A critic should treat E5 as *strongly indicated, not first-party-stated*.

### Bernstein scorecard

| | E1 durable | E2 layered self-improvement | E3 code-routed typed | E4 driver loop | E5 edge shape |
|---|---|---|---|---|---|
| bernstein | ✅ WAL + resume | ⚠️ layered judging ✅ / general learning loop unwired | ✅ headline claim | ✅ tick loop + plan DAG + VP | ✅ *(E5 partly derived)* |

## 3. Comparative landscape

### 3.1 Second tier — 3-of-4, and their gaps are *complementary*

**`tutti`** (nutthouse, Rust, MIT, 109 stars, created 2026-03-12).[^gh-tutti] Config-driven multi-agent CLI. **E3 ✅**: prompt steps capture artifacts via `artifact_glob`/`artifact_name`, downstream steps consume them via `inject_files = ["{{output.artifact_name.path}}"]`, and sequencing is declared in `tutti.toml` with `depends_on = [<step-number>, ...]` — routing is decided by the config, not a model. **E1 ⚠️**: *"Run checkpoints persisted at .tutti/state/workflow-checkpoints/<run_id>.json + tt run --resume <run_id>"* plus a *"Resume intent log + compensator preflight for safe workflow replay"* — checkpoint-and-resume, which `raw/production_cases.md` and Diagrid argue is weaker than durable execution.[^prod-cases] **E2 ✅ (thin)**: a `type = "review"` step separates `agent` from `reviewer`. **E4 ⚠️**: cron `schedule` plus `workflow_complete hooks for deterministic chaining` — chaining, not a state-driven driver. **E5 ✅**: *"No API keys required for CLI-agent mode. Existing Claude Code, Codex, Aider, or OpenClaw authentication keeps working."*[^tutti-readme] *(directional — single README as source.)*

**`kodo`** (ikamensh).[^kodo-readme] **E2 ✅ — the strongest instance of E2 found anywhere**: *"Independent architect + tester agents review work before accepting. Catches bugs the implementing agent is blind to,"* with the architect holding rejection authority and the orchestrator routing work back to workers. **E4 ✅**: *"Cycle — one unit of orchestrated work"*; *"Run — multiple cycles until done, with summaries bridging context between cycles"* — a driver above parent workflows. **E1 ⚠️**: *"ctrl-C'd or crashed? `kodo --resume` picks up where it left off, with agents resuming their prior conversations"* — session resume, not workflow replay. **E3 ❌**: the orchestrator is *"an LLM that delegates to a team of agents via tool calls"* — exactly the variant the problem statement rejects. **E5 ✅ (split)**: workers use Claude Code Max (user subscription), orchestrator uses separate API credentials. *(directional.)*

**The pattern is the finding.** bernstein has E3 and is weak on E2's learning loop; kodo has E2 and lacks E3 entirely; tutti has both thinly and is weak on E1/E4. **The four elements are being assembled in public, by multiple independent parties, right now** — which is a stronger refutation of "nobody has put them together" than any single match would be. *(derived from the three scorecards.)*

### 3.2 Third tier — one or two elements

| System | E1 | E2 | E3 | E4 | E5 | Evidence |
|---|---|---|---|---|---|---|
| **LionClaw** — local control plane for coding agents | ✅ durable sessions/transcript | ❌ | ❌ model does the work; *"LionClaw owns the boundary around it"* | ⚠️ scheduled jobs in *"fresh isolated sessions"* | ✅ *"Runtime auth stays runtime-specific… stages only the runtime-local auth files"* | [^lionclaw] |
| **automata** — Matrix-native assistant | ✅ *"it uses Temporal, a workflow system that saves progress step by step"* | ❌ undocumented | ❌ undocumented | ❌ undocumented | ❌ undocumented | [^automata] |
| **Orca** — *"fleet on your own subscription"* | ❌ | ❌ | ❌ | ⚠️ scriptable CLI | ✅ marketed shape; *"Account switcher & usage tracking"* | [^orca][^awesome-orch] |
| **gh-aw** — GitHub's official agentic workflows | ❌ undocumented | ❌ | ⚠️ markdown compiled to Actions YAML | ❌ | ❌ — runs *"inside GitHub Actions"*, credentials are repo secrets (`ANTHROPIC_API_KEY`) | [^ghaw] |
| **OpenHands** — self-hostable control center | ❌ undocumented | ❌ | ❌ undocumented | ⚠️ schedule/webhook automations | ✅ *"locally on your machine by default"*, or Docker/VM/company infra | [^openhands] |

*(directional throughout — single-README sourcing; "❌ undocumented" means the predicate is not addressed in the fetched first-party text, which is a gap finding, not a claim of absence.)*

### 3.3 The closest ecosystem neighbours

**Claude Code — subagents.** First-party docs: a subagent *"does that work in its own context and returns only the summary"* and *"works independently and returns results."*[^cc-subagents] Return is **prose**, not a typed value → **E3 ❌**. Subagents *"work within a single session"* → **E1 ❌**, **E4 ❌**. A `security-reviewer` subagent gives a judging role → **E2 ⚠️** (roles exist; the dispatch decision is the model's).

**Claude Code — agent teams** (experimental, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, documented as of v2.1.178).[^cc-teams] Closest native competitor, and it fails on all four for documented reasons:
- **E1 ❌** — *"No session resumption with in-process teammates: `/resume` and `/rewind` do not restore in-process teammates."*
- **E2 ⚠️** — parallel reviewers with distinct lenses are a documented use case, but *"The lead makes approval decisions autonomously"*; the judge is directed by a model, not by code.
- **E3 ❌** — coordination is a mailbox of messages (`~/.claude/teams/{team-name}/inboxes/{agent-name}.json`) plus a shared task list; teammates *"communicate directly with each other"* in prose. The one code-routed piece is dependency gating: *"when a teammate completes a task that other tasks depend on, it unblocks the dependent tasks without any action from you."*
- **E4 ❌** — *"One team per session"*, *"No nested teams: teammates cannot spawn their own teammates"*, *"Lead is fixed."*
- **E5 ✅** — runs locally on the operator's subscription by construction.

Anthropic's own guidance runs *against* unattended operation: *"Letting a team run unattended for too long increases the risk of wasted effort."*[^cc-teams]

**Cursor background agents, Sourcegraph Amp, Claude Code as a harness** — already surveyed in `raw/production_cases.md` §2: Cursor's durability is at the VM/repo-clone layer with coordination via filesystem + git and no workflow-level durable execution; Sourcegraph positions itself as a context layer, not an orchestrator, and documents no session persistence or retry mechanism; Claude Code's public materials describe no durable-execution layer or cross-process checkpoint format.[^prod-cases] **Not re-derived here.**

**Devin, GitHub Copilot coding agent / Copilot Workspace.** **Gap — not covered.** I did not locate first-party documentation addressing E1–E4 for these two within this cycle's budget, and I am not willing to characterise them from secondary commentary. `raw/production_cases.md` cites a community Copilot-orchestrator project that persists *"full state and results in filesystem YAML"* with a Repair Agent retrying up to three times — a hand-rolled activity-retry policy — but that is a third-party project, not GitHub's product.[^prod-cases] **This is the largest named gap in this paper.**

### 3.4 Durable-execution vendors: E1 and E3/E4 yes, E2 no

Temporal's own multi-agent guidance documents agent-routing and task-delegation patterns in which routing is handled **in workflow code** using conditional logic, signals, queries and wait conditions — not by a model — and describes human approval gates and confidence thresholds but **no self-improvement or critic loop**.[^temporal-multiagent] *(directional — rendered vendor page; quoted spans limited to what appeared in the fetch.)* This matches the pool's existing coverage: `raw/durable_execution.md` establishes what the substrate provides, and `raw/production_cases.md` establishes the convergent adoption record across Temporal, Restate, Inngest, DBOS, Cloudflare Workflows, AWS Step Functions and Azure Durable Functions.[^prod-cases]

**The vendor-side finding for this topic specifically:** durable-execution platforms give E1 and make E3/E4 natural (workflow code branching on typed activity results *is* code-routed control flow), and **none of them ship E2**. Combining a durable engine with a layered improvement loop remains the assembler's job — which is what bernstein, kodo and tutti each did independently, none of them on a bought engine.

### 3.5 Academic prior art on E3/E4

The problem statement's sharpest leg has a 2026 literature.

- **LLM-as-Code: Agentic Programming for Agent Harness** (Qi et al., submitted 2026-06-14, revised 2026-06-22) argues that *"token explosion, control-flow hallucination, and unreliable completion are not implementation bugs but architectural consequences"* of assigning deterministic work to a probabilistic system, and inverts the design so the program controls execution flow with the LLM invoked only for reasoning or generation. Its technical consequence — *"Each call's context length is then determined by its call depth rather than by accumulation over steps"* — is the same context argument `raw/hierarchical_agents.md` makes for hierarchy, reached from the control-flow side.[^llm-as-code]
- **Code as Agent Harness** (Ning et al., submitted 2026-05-18), a large survey, frames code as *"an operational substrate for agent reasoning, acting, environment modeling, and execution-based verification"* and covers scaling from single- to multi-agent settings.[^code-as-harness]

**This means the E3 premise is a named, published research position as of mid-2026, not an unexamined idea.** It is also the direct counter-position to every system in `raw/hierarchical_agents.md`, all of which put an LLM planner at the top — a tension that paper notes but does not resolve. *(derived.)*

### 3.6 The BYO-subscription deployment shape is a recognised category

E5 is not distinctive either. `awesome-agent-orchestrators` lists dozens of local/self-hosted runners, and industry commentary describes "bring your own agent" as an emerging standard architecture, naming Orca (*"running a fleet on your own subscription"*), Paseo (local daemon, agents on your machine), Agent Orchestrator (execution and code stay on your machine), Coder, Tembo and others.[^awesome-orch][^byo-search] *(unverified — this is search-result-level commentary and rendered vendor pages; treat the category claim as directional and the individual product claims as unverified.)*

## 4. What this provides — enumerated, citable properties

For the consumer (`problem-statement.md` § *What we are combining*):

1. **The blanket claim "Nobody has put them together" is falsified** by a single, currently-maintained, packaged, Apache-2.0 system.[^gh-bernstein][^pypi-bernstein][^bern-readme] *(definitive at documentation level.)*
2. **E3 is the least novel leg, not the most.** It is bernstein's headline marketing claim,[^bern-why] tutti's design premise,[^tutti-readme] and the thesis of at least one 2026 arXiv paper.[^llm-as-code] Any claim of novelty resting primarily on "routing in code over typed values" should be withdrawn. *(derived.)*
3. **E5 is a recognised product category** with multiple named entrants, not a differentiator.[^awesome-orch][^byo-search] *(directional.)*
4. **E2 is the leg where the field is actually thin.** bernstein's general lesson-writing path is unwired by its own admission;[^bern-lessons] its closed loop covers model routing only;[^bern-confidence] Temporal's multi-agent guidance has no critic loop;[^temporal-multiagent] Claude Code's team lead judges by model judgement, not by rule.[^cc-teams] kodo is the counter-example that shows it is buildable.[^kodo-readme] **If a defensible contribution exists, it is here.** *(derived.)*
5. **A durable, layered improvement loop is not obtainable off the shelf.** Every system found either bought durability and skipped the loop, or built the loop on checkpoint-grade persistence. *(derived from §3.1–3.4.)*
6. **The competitive set is now known and enumerable**, which changes the framing available to downstream planning: the honest claim is *"a particular assembly of a crowded space,"* not *"a combination nobody has attempted."* *(derived.)*
7. **A concrete comparison target exists.** bernstein is installable (`pip`), documented at depth (50+ doc directories including `orchestration/`, `cluster/`, `memory/`, `quality/`, `eval/`, `lineage/`), and claims a 120+ endpoint REST API and SWE-Bench Lite benchmarks.[^bern-llmstxt] Anything built here can be measured against something real rather than against a hypothetical.

## 5. Honest boundary analysis — the case against this paper's conclusion

**This paper's conclusion benefits nobody who commissioned it, which is a reason to scrutinise it harder, not less.** The strongest arguments against it:

**(a) I read documentation, I did not run anything.** Every bernstein claim is from bernstein's own docs. Repositories over-claim routinely; a doc directory named `cluster/` is not a working cluster, and `raw/production_cases.md`'s central lesson is that "checkpoints" are frequently marketed as durability and are not.[^prod-cases] **The whole headline could survive only until someone runs it.** This is the single largest weakness and the first item in the test plan.

**(b) WebFetch summarisation is a fabrication surface even on raw sources.** I fetched raw markdown per the standard's rule, but a summarising model still stood between me and the bytes. Quoted spans are ones that appeared in quotation marks in the fetch output; I did not read the repository's raw bytes directly. A critic should spot-check two or three quotes verbatim before treating them as citable.

**(c) The element mapping is mine, and I could be inflating matches.** The problem statement's four elements are prose, not a spec. "Layered self-improvement that exercises durable artifacts" could reasonably be read as *the system improving its own workflow modules over cycles* — a stricter reading under which **bernstein clearly fails**, its own docs say so, and the headline weakens from "built" to "three and a half of four." I chose the more literal reading (distinct authoring/judging/dispositioning actors over shared durable artifacts) because that is what the sentence enumerates. **A reviewer who prefers the stricter reading should downgrade the verdict accordingly** — and should note that under the stricter reading, *nothing found in this sweep passes E2*, which would restore a narrower novelty claim.

**(d) Element-by-element matching may be the wrong test entirely.** A system can satisfy five predicates and still be a different thing. bernstein is a single-goal coding orchestrator: decompose one goal, fan out to worktrees, verify, merge. The problem statement describes a *general backbone* whose coding edge is instance one, with home automation, robotics and bioinformatics edges to follow, and a shared workflow library as "the genuinely novel artifact."[^problem-statement] **Nothing found in this sweep is domain-general in that sense** — every candidate is a coding-agent orchestrator. If the actual contribution is the *reusable cross-domain module library*, this paper tested the wrong claim, and `raw/backbone_edge_generality.md` is where that gets settled. *(This is the most credible defence of the product, and it is a defence of a **different** claim than the one the § tested says.)*

**(e) The un-built case could be un-built because it is not worth building.** If nothing here had matched, the honest alternative explanation would have been that the combination is unattractive, not unattempted — the coordination cost exceeds the benefit, or the E2 loop plateaus (see `raw/convergence_stopping.md` and `raw/reflection_literature.md`). That explanation is now partly moot for E1/E3/E4/E5 but stands undiminished for **E2**: the fact that bernstein *implemented* `file_lesson()` and then *did not call it* is weak evidence that the general learning loop was tried and found not to pay.[^bern-lessons] **That is the most important adverse signal in this paper**, and it points at `raw/case_against.md` and the deferred decide-only-disposition topic.

**(f) Internal and unpublished systems are unreachable by any search.** Every large lab and several large enterprises plausibly run internal agent fleets with durable orchestration; none would publish. `raw/production_cases.md` already notes its cases are *"self-reported and selection-biased toward teams who published."*[^prod-cases] A null result here would never have been strong; a positive result does not depend on it.

**(g) Named coverage gaps.** Devin and GitHub Copilot coding agent were not assessed from first-party sources (§3.3). Microsoft Agent Framework, Google ADK, CrewAI, AutoGen, Dify and Flowise were not individually assessed against E1–E5 — the Diagrid analysis cited in `raw/production_cases.md` argues the checkpoint-grade ones fail E1,[^prod-cases] but that is inherited, not re-verified. Restate, Inngest, DBOS and Cloudflare Workflows were assessed only via the pool's existing coverage.

**(h) Recency risk is severe.** bernstein was pushed the day of this search; tutti and bernstein were both created in March 2026. This category is turning over on a scale of weeks. A four-week revalidation is the right tier and may still be too slow.

## 6. Citations

[^problem-statement]: This repo, `docs/standards/architecture/problem-statement.md` § *What we are combining, and why it is novel*.
[^gh-bernstein]: GitHub REST API, repo metadata for `sipyourdrink-ltd/bernstein` (JSON). https://api.github.com/repos/sipyourdrink-ltd/bernstein
[^pypi-bernstein]: PyPI JSON API, package `bernstein`, v3.13.0. https://pypi.org/pypi/bernstein/json
[^bern-readme]: bernstein, `README.md` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/README.md
[^bern-why]: bernstein, `docs/architecture/WHY_DETERMINISTIC.md` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/architecture/WHY_DETERMINISTIC.md
[^bern-state]: bernstein, `docs/architecture/state-persistence.md` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/architecture/state-persistence.md
[^bern-quality]: bernstein, `docs/architecture/quality-pipeline.md` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/architecture/quality-pipeline.md
[^bern-lessons]: bernstein, `docs/concepts/lesson-persistence.md` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/concepts/lesson-persistence.md
[^bern-confidence]: bernstein, `docs/quality/empirical-confidence.md` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/quality/empirical-confidence.md
[^bern-autofix]: bernstein, `docs/autofix/telemetry-grounded.md` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/autofix/telemetry-grounded.md
[^bern-runactor]: bernstein, `docs/orchestration/run-actor.md` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/orchestration/run-actor.md
[^bern-multicell]: bernstein, `docs/orchestration/multi-cell.md` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/orchestration/multi-cell.md
[^bern-workers]: bernstein, `docs/orchestration/worker-coordination.md` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/orchestration/worker-coordination.md
[^bern-cluster]: bernstein, `docs/cluster/deployment-patterns.md` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/cluster/deployment-patterns.md
[^bern-llmstxt]: bernstein, `docs/llms.txt` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/llms.txt
[^bern-llmsfull]: bernstein, `docs/llms-full.txt` (raw). https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/llms-full.txt
[^bern-docs-concepts]: bernstein, `docs/concepts/` directory listing via GitHub contents API. https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/docs/concepts
[^bern-docs-arch]: bernstein, `docs/architecture/` directory listing via GitHub contents API. https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/docs/architecture
[^bern-docs-cluster]: bernstein, `docs/cluster/` directory listing via GitHub contents API. https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/docs/cluster
[^bern-substrate]: bernstein, `docs/substrate/` directory listing (per-agent adapter docs: aider, claude-code, claude-desktop, cline, continue, cursor, zed). https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/docs/substrate
[^awesome-orch]: andyrewlee/awesome-agent-orchestrators, `README.md` (raw). https://raw.githubusercontent.com/andyrewlee/awesome-agent-orchestrators/main/README.md
[^gh-tutti]: GitHub REST API, repo metadata for `nutthouse/tutti` (JSON). https://api.github.com/repos/nutthouse/tutti
[^tutti-readme]: nutthouse/tutti, `README.md` (raw). https://raw.githubusercontent.com/nutthouse/tutti/main/README.md
[^kodo-readme]: ikamensh/kodo, `README.md` (raw). https://raw.githubusercontent.com/ikamensh/kodo/main/README.md
[^lionclaw]: moshthepitt/lionclaw, `README.md` (raw). https://raw.githubusercontent.com/moshthepitt/lionclaw/main/README.md
[^automata]: sentientwave/automata, `README.md` (raw). https://raw.githubusercontent.com/sentientwave/automata/main/README.md
[^orca]: stablyai/orca, `README.md` (raw). https://raw.githubusercontent.com/stablyai/orca/main/README.md
[^ghaw]: github/gh-aw, `README.md` (raw). https://raw.githubusercontent.com/github/gh-aw/main/README.md
[^openhands]: OpenHands/OpenHands, `README.md` (raw). https://raw.githubusercontent.com/OpenHands/OpenHands/main/README.md
[^cc-subagents]: Anthropic, Claude Code docs, "Create custom subagents." https://code.claude.com/docs/en/sub-agents
[^cc-teams]: Anthropic, Claude Code docs, "Orchestrate teams of Claude Code sessions" (agent teams; experimental, documented as of v2.1.178). https://code.claude.com/docs/en/agent-teams
[^temporal-multiagent]: Temporal, "Durable multi-agentic AI architecture with Temporal" (rendered vendor page — reduced confidence). https://temporal.io/blog/using-multi-agent-architectures-with-temporal
[^llm-as-code]: Qi, J., Fu, Z., Gao, J., Zhang, W., Yan, H., Wu, X., & Zhao, X. (2026). *LLM-as-Code: Agentic Programming for Agent Harness.* arXiv:2606.15874 (v1 2026-06-14, v2 2026-06-22). https://arxiv.org/abs/2606.15874
[^code-as-harness]: Ning, X., Tieu, K., Fu, D., et al. (2026). *Code as Agent Harness.* arXiv:2605.18747 (2026-05-18). https://arxiv.org/abs/2605.18747
[^byo-search]: Landscape orientation for the BYO-subscription category — search-result-level commentary and rendered vendor pages naming Orca, Paseo, Agent Orchestrator, Coder, Tembo (**unverified**; individual product claims not fetched from first-party sources). Representative: Coder, "Inside the Stack: Secure and Scale AI Coding Agents with Coder." https://coder.com/blog/inside-the-stack-secure-and-scale-ai-coding-agents-with-coder ; getpaseo/paseo. https://github.com/getpaseo/paseo
[^prod-cases]: This repo, `docs/standards/architecture/research/raw/production_cases.md` (last validated 2026-07-23, Critic: PASS). Also `raw/durable_execution.md` and `raw/hierarchical_agents.md`, cited in-text.

**Located but not assessed** (named so a reader knows what was seen and skipped): `XMUDeepLIT/Awesome-Self-Evolving-Agents`; arXiv:2508.07407 *A Comprehensive Survey of Self-Evolving AI Agents*; arXiv:2602.14690 *Harness Engineering for Agentic AI Coding Tools*; arXiv:2606.17546 *SEAGym*; `paperclipai/paperclip` (README fetch returned HTTP 404 on `main`; **not assessed**, despite the operator's prior interest in Paperclip as an orchestration platform).

## 7. Test plan — what research cannot settle

Ordered by how much each would change the verdict.

1. **Run bernstein.** `pip install bernstein`, drive a two-task goal against a local Claude Code, kill the process mid-run, restart in the same workdir. **Settles:** whether E1's *"your task graph comes back"* is real or aspirational. This is the single test that most changes the headline. Budget: under an hour.
2. **Stand up the STAR cluster with two hosts.** Confirm the coordinator spawns no agent process and holds no model credential, and that a worker executes under its own locally-installed CLI auth. **Settles:** whether E5 — the leg I marked *derived* — is first-party true. If it fails, the deployment shape becomes the differentiator.
3. **Verify three quotes byte-for-byte.** Read the raw bytes of `WHY_DETERMINISTIC.md`, `state-persistence.md` and `lesson-persistence.md` outside a summarising fetch. **Settles:** boundary (b). Cheap; do it first if the critic is budget-constrained.
4. **Assess Devin and GitHub Copilot coding agent against E1–E5 from first-party docs.** **Settles:** the largest named coverage gap (§3.3).
5. **Determine empirically whether the E2 general loop pays.** bernstein wrote `file_lesson()` and never called it. Ask the maintainer, or search the repo's issues/decisions log for the rationale. **Settles:** boundary (e) — whether the thinnest leg is thin because it is hard or because it does not work. This is the highest-value question in the paper and research cannot answer it; it is the same question the deferred *decide-only disposition* topic asks.
6. **Test the domain-generality claim, not the element claim.** Boundary (d) says the real contribution may be the cross-domain module library. No system found is domain-general — but that is only interesting if a second edge actually gets stood up. Handoff to `raw/backbone_edge_generality.md`.
7. **Re-sweep in four weeks.** Specifically re-check bernstein's `lesson-persistence.md` for a wired write path, and re-scan `awesome-agent-orchestrators` for new entries whose one-liners hit E2 + E3 together. That conjunction is the tripwire: the day one appears, the remaining novelty claim is gone.
