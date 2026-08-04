# Prior Art on the Four-Way Combination

```
Topic:          Has the four-way combination this product claims as novel already been built by someone else?
Feeds:          docs/standards/architecture/problem-statement.md § "What we are combining, and why it is novel" — the novelty claim itself
Last validated: 2026-08-03
Revalidate:     high — 4 weeks
Confidence:     Definitive (documentation-level) that a system exists satisfying E1, E3 and E4 — bernstein, from its own raw first-party docs plus package-registry and repo metadata. E2 is PARTIAL by bernstein's own documentation, not definitive. E5 is DERIVED from a documented division of labour, not first-party-stated — no bernstein doc says the coordinator runs no agent compute or where model credentials live. The element-by-element mapping onto the problem statement's prose is derived throughout. Directional on the second-tier near-misses (tutti, kodo), whose docs are thinner. Unverified on runtime behaviour — no system in this paper was executed.
Critic:         PASS-WITH-FIXES (autofix loop miscitation corrected and E2 re-argued; header Confidence de-inflated to match body; headline derived-marks restored for E2 role-mapping and E5; two README quotes restored to verbatim; llms.txt directory-count, Temporal and Coder citation titles, index entry count corrected) — 2026-08-03
```

> ## Headline finding — the novelty claim as written does not hold
>
> **A system exists that satisfies all four elements *and* the deployment shape** — three of them squarely, one partially, one by inference. It is [`bernstein`](https://github.com/sipyourdrink-ltd/bernstein) — Apache-2.0, Python, 777 stars, on PyPI at v3.13.0, created 2026-03-22, last pushed 2026-08-03 (the day of this search).[^gh-bernstein][^pypi-bernstein] Its own one-line description is *"Deterministic orchestrator for CLI coding agents (Claude Code, Codex, Gemini CLI, +40 more). No model in the coordination loop, so parallel runs in per-task git worktrees replay byte-identically."*[^gh-bernstein]
>
> - **E1 ✅** WAL-backed crash recovery.[^bern-state]
> - **E2 ⚠️** a janitor / gate-pipeline / cross-model-verifier stack in which the cross-model reviewer is *"a **different** model (a cheap one from a different provider)"*;[^bern-quality] reading that as *author / judge-with-no-stake / disposition* is **my mapping, not bernstein's framing** *(derived)*.
> - **E3 ✅** plain-Python scheduling over typed task values with explicitly no LLM in the coordination loop.[^bern-why]
> - **E4 ✅** a tick loop over a durable backlog, plan DAGs, and a "VP" cell above the worker cells.[^bern-state][^bern-multicell]
> - **E5 ⚠️** a STAR cluster in which a central server runs orchestrator, API and task store while N worker hosts *"register, heartbeat, and pull tasks"*.[^bern-cluster] That the coordinator runs **no agent compute** and that **model** credentials stay on the worker are **inferences from the documented division of labour** *(derived)* — the cluster docs discuss only cluster **auth tokens**, distributed *"out of band (scp, your secrets manager, etc.)"*, and say nothing about provider credentials.[^bern-cluster]
>
> **One element is genuinely short**, and bernstein's own docs say so: the *general* lesson-accumulation write path is unwired — *"nothing files lessons automatically yet."*[^bern-lessons] Two narrower loops **are** closed: an append-only SQLite outcome ledger feeding model-selection routing,[^bern-confidence] and a telemetry→autofix dispatch path with no human approval gate.[^bern-autofix] Neither routes through the judging layer — see §2 E2.
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

The single highest-yield artifact was a community index, `andyrewlee/awesome-agent-orchestrators`, which catalogues **~180 orchestrators as of 2026-08-03** across eight sections, and whose one-line descriptions are precise enough to shortlist against E1–E5 directly.[^awesome-orch] Two of its entries read as near-verbatim restatements of the problem statement's own elements: *"Keeps no model in the coordination loop, so orchestration costs zero tokens"* (bernstein) and *"Config-driven workflows passing typed artifacts between agents, each in its own worktree"* (tutti).[^awesome-orch] **The existence of a curated ~180-entry list in this exact category is itself a finding** — this is a crowded space, not an empty one.

**This paper does not re-cover** what durable execution provides (`raw/durable_execution.md`), who adopted it and what they hit (`raw/production_cases.md`), or the published hierarchical-agent architectures (`raw/hierarchical_agents.md`). It cites them and asks the question they do not: *does anything combine the four?*

## 2. The match: bernstein, element by element

All claims in this section are **definitive** at the documentation level (first-party repo docs fetched raw) and **unverified** at the behavioural level (nothing was executed). Quoted spans appeared inside quotation marks in the fetched text.

### E1 — Durable execution ✅

`docs/architecture/state-persistence.md` documents a write-ahead log at `.sdd/runtime/wal/*.wal.jsonl` with three invariants: append-only via `write() + flush() + fsync()`, a hash chain where each entry's `prev_hash` matches the prior digest, and a per-entry fsync guarantee that *"A process crash immediately after `append()` returns cannot lose the entry."* Restart recovery is a documented sequence: load the durable backlog, scan uncommitted WAL entries, replay through an idempotency filter, reset tasks stuck in `claimed`, resume the tick loop. The doc's summary claim: *"kill `bernstein run`, restart it in the same workdir, and your task graph comes back."*[^bern-state] Durable surfaces enumerated: backlog YAML, WAL, idempotency markers, metrics, a content-addressed artifact store (`.sdd/cas/`), and audit logs with Merkle seals.[^bern-state] `llms-full.txt` lists *"WAL-backed crash recovery"* as a shipped capability.[^bern-llmsfull]

**Boundary, stated by bernstein itself:** the in-process run actor is *"In-memory only. Persistence is out of scope; pair with the existing WAL if durability is required."*[^bern-runactor] So durability is a property of the backlog/WAL layer, not of every component — which is precisely the layering Temporal-style systems also have. This is a *narrower* durability guarantee than a replay-based engine (no deterministic workflow replay of arbitrary orchestration code), and it is hand-rolled rather than bought — exactly the "hand-rolled durability" pattern `raw/production_cases.md` §4 documents across the industry.[^prod-cases]

### E2 — Layered judging ✅ / self-improvement loop ⚠️ PARTIAL

`docs/architecture/quality-pipeline.md` documents three sequential verification layers: a **janitor** evaluating declarative completion signals (file existence, tests pass, regex match), a **gate pipeline** running build/lint/type/test/security against the actual diff, and an optional **cross-model verifier** that sends the diff to *"a *different* model (a cheap one from a different provider)"* for independent review.[^bern-quality] The README's four-stage arc is *Decompose → Spawn → Verify → Merge*, with disposition explicit: *"Failed tasks get retried or routed to a different model."*[^bern-readme]

Mapped onto E2: **author** = the spawned CLI agent in its worktree; **judge with no stake** = the cross-model verifier, a different provider's model reviewing another provider's output; **disposition** = the merge gate plus retry/reroute. The artifacts are shared and durable — worktrees, CAS blobs, the audit chain. *(derived — the role mapping is my inference from bernstein's docs, not their framing.)*

**Two closed loops exist.** Both write a durable artifact from one part of the system and read it **in code** from another to change future behaviour — E2's mechanism, at narrow scope:

- **Model-routing ledger.** `docs/quality/empirical-confidence.md` documents an append-only SQLite `agent_outcomes` ledger keyed `"role:<task.role>|model:<model_key>"`, queried after a minimum sample count (default 5), whose result is the first-ranked input to `recommend_models` ahead of a bandit fallback and a heuristic fallback.[^bern-confidence] This one is genuinely self-referential: the system reads its **own** past outcomes and changes its **own** future routing.
- **Telemetry-grounded autofix.** `docs/autofix/telemetry-grounded.md` documents a fully automatic path — *"Webhook arrives at `/webhooks/telemetry/<source>/`"* → *"Adapter parses the payload into a `TelemetryEvent`"* → *"Grounding retriever pulls a window of recent log lines around the event fingerprint"* → *"A grounded goal is built and handed to the existing autofix dispatch hook"* → *"The outcome is recorded in the audit log."*[^bern-autofix] **There is no human approval gate before dispatch.** Operator control is enablement-only (*"Operator-flagged off per source"*) plus a pre-dispatch spend check — *"Every event consults its source's `cost_cap_usd` **before** the dispatch hook fires"* — with post-hoc intervention when *"the dispatcher flips the outcome to `cost_capped` so the operator can intervene without losing the audit trailer."*[^bern-autofix]

**Where it falls short, per bernstein's own documentation.** Lessons live in `.sdd/memory/lessons.jsonl` with tags, confidence, memory type and a SHA-256 integrity chain; `spawner_core.py` reads them at task assignment via `gather_lessons_for_context()`. But the write path is not wired: *"nothing files lessons automatically yet"* — `file_lesson()` is *"fully implemented, tested, and safe to call"* yet *"no code path in the shipped orchestrator calls it,"* and *"nothing currently reads a task's outcome and writes a lesson on completion."*[^bern-lessons]

**The E2 verdict, re-argued on what is left.** An earlier draft of this paper claimed the autofix path was "operator-mediated rather than closed." **That was wrong** — the source says the opposite, and the correction removes one of the two supports the PARTIAL verdict rested on. The verdict survives, but on narrower and more precise grounds:

1. **The layered *judging* stack is real and unaffected** — janitor, gate pipeline, cross-model verifier, with retry/reroute as disposition.[^bern-quality][^bern-readme] E2's *layering* clause is satisfied.
2. **Neither closed loop routes through that judging layer.** The routing ledger consumes a binary pass/fail outcome, not a judge's verdict; the autofix loop is triggered by an **external** observability signal (Sentry, GitHub Actions) and produces an error remediation. It is a closed loop, but it is *error remediation, not lesson accumulation* — the system fixing the code it maintains, not improving how it works. *(derived from `telemetry-grounded.md` + `empirical-confidence.md` read together.)*
3. **The general lesson-accumulation path — the one that would join the judging layer to future behaviour — remains unwired by bernstein's own admission.**[^bern-lessons]

So: **layered judging ✅; two closed narrow behaviour loops ✅; a layered self-improvement loop, in which what a judge concluded durably changes how the system works next time, ❌.** That last conjunction is what E2 asks for and what bernstein does not have. The margin is thinner than the earlier draft implied, and a reader should know the correction moved it in bernstein's favour.

### E3 — Code-routed control flow over typed values ✅

This is the leg the problem statement treats as most distinctive, and it is bernstein's **headline marketing claim**, not a buried feature. `docs/architecture/WHY_DETERMINISTIC.md`: *"There are no LLM calls in this loop. No model decides which task to run next, which agent to assign it to, or whether the agent is making progress."*[^bern-why] The README: *"No LLM in the coordination loop."* / *"Scheduling is plain Python, so a run is reproducible end to end."* / *"Replay yesterday's plan and get yesterday's task graph."*[^bern-readme] One LLM call decomposes the goal into tasks carrying roles, owned files and completion signals; everything after is Python over those values.[^bern-readme]

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

Model credentials stay with the local CLI agent: bernstein drives 40+ CLI agent adapters (Claude Code, Codex, Gemini CLI, Aider, Cline, Continue, Cursor, Zed…), with *"file-based state, no SaaS hop, no third-party data plane,"* and mixes *"cheap local models"* with cloud subscriptions in the same run.[^bern-readme][^bern-substrate]

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
| **Orca** — indexed as *"Agentic development environment for running a fleet on your own subscription"* (the **index's** wording, not Orca's own README, which does not contain that phrase)[^awesome-orch] | ❌ | ❌ | ❌ | ⚠️ scriptable CLI | ⚠️ README shows *"Account switcher & usage tracking"* but does not state the credential/server split | [^orca][^awesome-orch] |
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

**Devin, GitHub Copilot coding agent / Copilot Workspace.** **Gap — not covered, and the negative is weak.** E1–E4 were **not found via**: the `awesome-agent-orchestrators` index (neither product is listed);[^awesome-orch] the two BYO-agent/fleet landscape sweeps run for §3.6;[^byo-search] and the durable-execution and agent-orchestration sweeps that surfaced every other system in this paper. **No first-party documentation site for either product was fetched** — that is the honest limit, and it is a budget limit rather than an evidenced absence. I am not willing to characterise either from secondary commentary. `raw/production_cases.md` cites a community Copilot-orchestrator project that persists *"full state and results in filesystem YAML"* with a Repair Agent retrying up to three times — a hand-rolled activity-retry policy — but that is a third-party project, not GitHub's product.[^prod-cases] **This is the largest named gap in this paper.**

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
4. **E2 is the leg where the field is thin — but narrowly, and less thin than an earlier draft of this paper claimed.** bernstein has two closed behaviour loops (a model-routing outcome ledger and a fully automatic telemetry→autofix dispatch with no approval gate),[^bern-confidence][^bern-autofix] and neither routes through its judging layer; its general lesson-writing path is unwired by its own admission.[^bern-lessons] Temporal's multi-agent guidance has no critic loop;[^temporal-multiagent] Claude Code's team lead judges by model judgement, not by rule.[^cc-teams] kodo shows the judging half is buildable.[^kodo-readme] **The precise thing not found anywhere is the conjunction: a judging layer whose verdict durably changes how the system works next time.** If a defensible contribution exists, it is that conjunction — not "E2" broadly. *(derived.)*
5. **A durable, layered improvement loop is not obtainable off the shelf.** Every system found either bought durability and skipped the loop, or built the loop on checkpoint-grade persistence. *(derived from §3.1–3.4.)*
6. **The competitive set is now known and enumerable**, which changes the framing available to downstream planning: the honest claim is *"a particular assembly of a crowded space,"* not *"a combination nobody has attempted."* *(derived.)*
7. **A concrete comparison target exists.** bernstein is installable (`pip`), documented at depth — **52 directories under `docs/`**, including `orchestration/`, `cluster/`, `memory/`, `quality/`, `eval/` and `lineage/`[^bern-docs-root] — and its doc index claims *"API Reference - 120+ REST endpoints"* and *"Benchmarks - SWE-Bench Lite performance data."*[^bern-llmstxt] Anything built here can be measured against something real rather than against a hypothetical.

## 5. Honest boundary analysis — the case against this paper's conclusion

**This paper's conclusion benefits nobody who commissioned it, which is a reason to scrutinise it harder, not less.** The strongest arguments against it:

**(a) I read documentation, I did not run anything.** Every bernstein claim is from bernstein's own docs. Repositories over-claim routinely; a doc directory named `cluster/` is not a working cluster, and `raw/production_cases.md`'s central lesson is that "checkpoints" are frequently marketed as durability and are not.[^prod-cases] **The whole headline could survive only until someone runs it.** This is the single largest weakness and the first item in the test plan.

**(b) WebFetch summarisation is a fabrication surface even on raw sources.** I fetched raw markdown per the standard's rule, but a summarising model still stood between me and the bytes. Quoted spans are ones that appeared in quotation marks in the fetch output; I did not read the repository's raw bytes directly. A critic should spot-check two or three quotes verbatim before treating them as citable.

**(c) The element mapping is mine, and I could be inflating matches.** The problem statement's four elements are prose, not a spec. "Layered self-improvement that exercises durable artifacts" could reasonably be read as *the system improving its own workflow modules over cycles* — a stricter reading under which **bernstein clearly fails**, its own docs say so, and the headline weakens from "built" to "three and a half of four." I chose the more literal reading (distinct authoring/judging/dispositioning actors over shared durable artifacts) because that is what the sentence enumerates. **A reviewer who prefers the stricter reading should downgrade the verdict accordingly** — and should note that under the stricter reading, *nothing found in this sweep passes E2*, which would restore a narrower novelty claim.

**(d) Element-by-element matching may be the wrong test entirely.** A system can satisfy five predicates and still be a different thing. bernstein is a single-goal coding orchestrator: decompose one goal, fan out to worktrees, verify, merge. The problem statement describes a *general backbone* whose coding edge is instance one, with home automation, robotics and bioinformatics edges to follow, and a shared workflow library as "the genuinely novel artifact."[^problem-statement] **Nothing found in this sweep is domain-general in that sense** — every candidate is a coding-agent orchestrator. If the actual contribution is the *reusable cross-domain module library*, this paper tested the wrong claim, and `raw/backbone_edge_generality.md` is where that gets settled. *(This is the most credible defence of the product, and it is a defence of a **different** claim than the one the § tested says.)*

**(e) The un-built case could be un-built because it is not worth building.** If nothing here had matched, the honest alternative explanation would have been that the combination is unattractive, not unattempted — the coordination cost exceeds the benefit, or the E2 loop plateaus (see `raw/convergence_stopping.md` and `raw/reflection_literature.md`). That explanation is now partly moot for E1/E3/E4/E5 but stands undiminished for **E2**: the fact that bernstein *implemented* `file_lesson()` and then *did not call it* is weak evidence that the general learning loop was tried and found not to pay.[^bern-lessons] **That is the most important adverse signal in this paper**, and it points at `raw/case_against.md` and the deferred decide-only-disposition topic. The signal survived this paper's own correction and arguably strengthened: bernstein demonstrably *does* wire closed loops when it wants them — a routing ledger and a no-approval-gate autofix dispatch[^bern-confidence][^bern-autofix] — so the unwired lesson path is less plausibly an oversight and more plausibly a judgement.

**(f) Internal and unpublished systems are unreachable by any search.** Every large lab and several large enterprises plausibly run internal agent fleets with durable orchestration; none would publish. `raw/production_cases.md` already notes its cases are *"self-reported and selection-biased toward teams who published."*[^prod-cases] A null result here would never have been strong; a positive result does not depend on it.

**(g) Named coverage gaps.**
- **Devin and GitHub Copilot coding agent** were not assessed from first-party sources; §3.3 states the search method and the limit.
- **Paperclip was not assessed at all.** `raw.githubusercontent.com/paperclipai/paperclip/main/README.md` returned **HTTP 404** (wrong default branch, a moved path, or a renamed repo — I did not diagnose which). The index describes it as *"Self-hosted platform where agents wake on heartbeats to claim tickets,"*[^awesome-orch] which reads as E4 + E5 and would have earned a full assessment. **This gap is load-bearing for this operator specifically**, who has Paperclip on file as an orchestration platform to evaluate after Phase 4 — the one candidate most likely to matter here is the one this sweep missed.
- **Microsoft Agent Framework, Google ADK, CrewAI, AutoGen, Dify and Flowise** were not individually assessed against E1–E5 — the Diagrid analysis cited in `raw/production_cases.md` argues the checkpoint-grade ones fail E1,[^prod-cases] but that is inherited, not re-verified.
- **Restate, Inngest, DBOS and Cloudflare Workflows** were assessed only via the pool's existing coverage.

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
[^bern-docs-root]: bernstein, `docs/` root listing via GitHub contents API — 52 directories (`_internal`, `adapters`, `api`, `architecture`, `assets`, `autofix`, `benchmarks`, `blog`, `ci`, `cloudflare`, `cluster`, `compliance`, `concepts`, `contributing`, `cost`, `decisions`, `demo`, `devops`, `diagrams`, `eval`, `events`, `examples`, `fleet`, `getting-started`, `git`, `gui`, `guides`, `installation`, `integrations`, `interop`, `lineage`, `maintainers`, `mcp`, `memory`, `observability`, `operations`, `orchestration`, `overrides`, `planning`, `playbooks`, `protocols`, `quality`, `reference`, `release-notes`, `sandbox`, `sdd`, `security`, `skills`, `substrate`, `testing`, `trackers`, `workflows`), counted 2026-08-03. https://api.github.com/repos/sipyourdrink-ltd/bernstein/contents/docs
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
[^temporal-multiagent]: Temporal, "Using the power of multi-agent architectures with Temporal" (2025-08-27; rendered vendor page — reduced confidence). https://temporal.io/blog/using-multi-agent-architectures-with-temporal
[^llm-as-code]: Qi, J., Fu, Z., Gao, J., Zhang, W., Yan, H., Wu, X., & Zhao, X. (2026). *LLM-as-Code: Agentic Programming for Agent Harness.* arXiv:2606.15874 (v1 2026-06-14, v2 2026-06-22). https://arxiv.org/abs/2606.15874
[^code-as-harness]: Ning, X., Tieu, K., Fu, D., et al. (2026). *Code as Agent Harness.* arXiv:2605.18747 (2026-05-18). https://arxiv.org/abs/2605.18747
[^byo-search]: Landscape orientation for the BYO-subscription category — search-result-level commentary and rendered vendor pages naming Orca, Paseo, Agent Orchestrator, Coder, Tembo (**unverified**; individual product claims not fetched from first-party sources). Representative: Coder, "Coder's AI Stack: Bring Your Own Agent or Run Coder Agents in Governed Environments." https://coder.com/blog/inside-the-stack-secure-and-scale-ai-coding-agents-with-coder ; getpaseo/paseo. https://github.com/getpaseo/paseo
[^prod-cases]: This repo, `docs/standards/architecture/research/raw/production_cases.md` (last validated 2026-07-23, Critic: PASS). Also `raw/durable_execution.md` and `raw/hierarchical_agents.md`, cited in-text.

**Located but not assessed** (named so a reader knows what was seen and skipped): `XMUDeepLIT/Awesome-Self-Evolving-Agents`; arXiv:2508.07407 *A Comprehensive Survey of Self-Evolving AI Agents*; arXiv:2602.14690 *Harness Engineering for Agentic AI Coding Tools*; arXiv:2606.17546 *SEAGym*. **`paperclipai/paperclip` is not filed here — it is a named gap in § 5(g)**, because the operator has prior interest in it and its index one-liner reads as E4 + E5.

## 7. Test plan — what research cannot settle

Ordered by how much each would change the verdict.

1. **Run bernstein.** `pip install bernstein`, drive a two-task goal against a local Claude Code, kill the process mid-run, restart in the same workdir. **Settles:** whether E1's *"your task graph comes back"* is real or aspirational. This is the single test that most changes the headline. Budget: under an hour.
2. **Stand up the STAR cluster with two hosts.** Confirm the coordinator spawns no agent process and holds no model credential, and that a worker executes under its own locally-installed CLI auth. **Settles:** whether E5 — the leg I marked *derived* — is first-party true. If it fails, the deployment shape becomes the differentiator.
3. **Verify three quotes byte-for-byte.** Read the raw bytes of `WHY_DETERMINISTIC.md`, `state-persistence.md` and `lesson-persistence.md` outside a summarising fetch. **Settles:** boundary (b). Cheap; do it first if the critic is budget-constrained.
4. **Assess Paperclip, then Devin and GitHub Copilot coding agent, against E1–E5 from first-party docs.** Paperclip first: resolve the 404 (check the repo's actual default branch via the contents API) — its index one-liner reads as E4 + E5, and it is already on the operator's evaluation list. **Settles:** the two named coverage gaps in § 5(g), one of which is the candidate most likely to matter to this operator.
5. **Determine empirically whether the E2 conjunction pays.** bernstein closed two behaviour loops but wrote `file_lesson()` and never called it — so it is not that the team lacked the appetite for closed loops, it is that *this* loop specifically did not get wired. That makes the question sharper, not weaker. Ask the maintainer, or search the repo's `docs/decisions/` and issues for the rationale. **Settles:** boundary (e) — whether the judge-verdict-changes-future-behaviour conjunction is thin because it is hard, because it does not pay, or merely because nobody got to it. This is the highest-value question in the paper, research cannot answer it, and it is the same question the deferred *decide-only disposition* topic asks.
6. **Test the domain-generality claim, not the element claim.** Boundary (d) says the real contribution may be the cross-domain module library. No system found is domain-general — but that is only interesting if a second edge actually gets stood up. Handoff to `raw/backbone_edge_generality.md`.
7. **Re-sweep in four weeks.** Specifically re-check bernstein's `lesson-persistence.md` for a wired write path, and re-scan `awesome-agent-orchestrators` (~180 entries as of this sweep) for new entries whose one-liners describe **a judging verdict that durably changes future behaviour** — the § 4.4 conjunction, not E2 broadly. That conjunction is the tripwire: the day one appears, the remaining novelty claim is gone.
