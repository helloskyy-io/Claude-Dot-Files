# Hermes Agent — Identified, Architecture Rejected, Twelve Things Worth Taking

```
Topic:          "Hermes" appears twice in this pool as a Paperclip adapter (hermes_local, hermes_gateway)
                and nowhere else. Which Hermes is it, what is its architecture, and what is worth taking
                from it regardless of whether that architecture suits us?
Feeds:          docs/development/roadmap.md § "Tools to Evaluate" (adds a resolved entry — §7); and
                docs/standards/architecture/problem-statement.md § "The edges" → the provider-shaped-edge
                stub ("the helpers available differ by which subscription backs the edge"). §3.2 and §4.1
                report what a non-Claude edge actually exposes, as input to that stub's own exercise.
                Secondary: Phase: Temporal Integration — §4.3 and §4.4 are design constraints on the
                claude_cli activity's heartbeat payload and failure metadata.
Last validated: 2026-08-06
Revalidate:     high — 3 weeks   (fast end of the 2-6 week band. Justification: the repo's pushed_at was
                the day of this sweep; the API-server doc carries a July-2026 breaking change and a
                June-2026 security hardening, both recent enough to still be moving; the Paperclip adapter
                package publishes a canary channel dated 2026.806; and the feature-doc directory holds at
                least 49 documents, a surface that decays faster than the 4 weeks used for Paperclip.)
Confidence:     DEFINITIVE for §2, §3 and §4 at the documentation level — eleven Hermes Agent docs and two
                Paperclip docs were fetched as raw .md from raw.githubusercontent.com and returned as
                apparently-complete reproductions (headings, tables, admonitions and fenced code blocks
                intact); every quoted span below appeared inside that returned text. DEFINITIVE for the
                identification in §1 — it rests on JSON API responses (npm registry, GitHub repo metadata,
                HuggingFace model API) plus a raw first-party README that names the upstream project and
                its URL. DERIVED for the architecture verdict (§3.7, §7), for every cost-to-adopt estimate
                (§4), and for each "why it matters here" reading — every derived claim names its inputs.
                REDUCED for anything sourced to the hermes-agent root README.md, whose fetch summarized;
                nothing load-bearing rests on it and it is not quoted. UNVERIFIED at the behavioural
                level: no Python source was read, nothing was installed, nothing was executed. GAPS are
                stated as gaps in §6 — HERMES_TENANT semantics, host systemd integration, and any
                Kubernetes deployment path are not documented in what was fetched, and are reported as
                negative findings with their search method rather than guessed. COUNTS are floors; the
                one retrieval-layer total this paper explicitly refuses to cite is the npm version count
                (see §6c).
Critic:         not-yet-verified — 2026-08-06
```

> ## Headline — the identification succeeded, and the answer reframes the topic
>
> **The Hermes in this pool is [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent)**
> — *Hermes Agent*, a Python, MIT-licensed personal-assistant agent runtime by Nous Research. It is **not**
> the Nous Research Hermes *LLM* family (a same-org, different-product collision that is the trap here) and
> not Facebook's Hermes JavaScript engine. The chain is first-party and unbroken: Paperclip's adapter
> package is described on the npm registry as *"Paperclip adapters for Hermes Agent local CLI and Hermes
> Gateway HTTP/SSE runs"*,[^npm] and its in-repo README links the upstream project by
> URL.[^pc-hermes-readme] §1 states the method and the ruled-out candidates.
>
> **The topic list under-described it.** `hermes_local` reads, from the Paperclip adapter table alone, like
> one more CLI coding agent. It is not. Hermes Agent carries **226,385 stars** and **44,120 forks** — three
> times Paperclip's adoption and the largest system in this research pool by a wide
> margin[^gh-hermes][^prior-art] — and it is **an assistant, not a coding tool**: messaging gateways across
> twenty-plus platforms, persistent memory, a skills system, a cron scheduler, an OpenAI-compatible API
> server, and a kanban board with worker lanes.[^sessions][^api-server][^kanban-lanes] **That is the same
> product category as Jarvis.** It is the closest thing in this pool to *what this repo says it is*, and
> the nearest neighbour on positioning even though `bernstein` remains the nearest neighbour on
> architecture.[^problem-statement]
>
> **Test (a) — is its architecture right for us? NO, on five grounds (§3.7).** Durability is bespoke on
> per-profile SQLite and the project **says so itself**: *"Background completion durability is not durable
> execution"*, and *"A Hermes process restart does **not** resume a running child. Its attempt becomes
> `unknown` because Hermes cannot prove which side effects happened."*[^delegation] The unit of
> orchestration is a *session*, not a replayable workflow. The recommended deployment is **one container
> hosting all profiles** under s6-overlay as PID 1,[^docker] and the image's own entrypoint documents that
> under a foreign PID-1 init — *"Fly.io Machines, `docker run --init`, some Nomad/Kubernetes setups"* —
> *"supervised services (dashboard, per-profile gateways) are unavailable."*[^docker] That collides
> head-on with the settled k3s-HA target.[^system-overview]
>
> **Test (b) — is anything worth taking? YES — this is the richest mining target in the pool.** Twelve
> items in §4, ranked. The top three fill gaps that are currently *homeless* here: a machine-readable
> **capability endpoint** at the edge (`GET /v1/capabilities`), which is the capability-advertisement
> primitive the Paperclip paper said differentiator #2 has no equivalent for;[^api-server][^paperclip] a
> **five-field completion contract** plus deterministic **quality gates** that must exit 0 before an LLM
> judge is even called;[^goals] and **structured terminal metadata on every failure class**, with named
> fields that are `null` on non-timeout errors.[^delegation]
>
> **One correction and one confirmation for positions this repo holds.** *Confirmed:* the `_gateway` form
> moves the **control** boundary, not the **credential** boundary — the provider credential stays in
> `~/.hermes/auth.json` on the Hermes host and only the API-server bearer crosses (§3.4). That is the
> federated-trunk shape the trust-tier table describes, shipped. *Corrected again:* subscription-auth at
> the edge is not merely un-unusual, it is **tooled** — `hermes auth add anthropic --type oauth` and
> auto-discovery of `~/.claude/.credentials.json` into a rotation pool.[^cred-pools]

---

## 1. Identification — which Hermes, and how the others were ruled out

This section exists because the dispatch named name-disambiguation as the first task. The identification
**succeeded**; what follows is the method, so a reader can check it rather than trust it.

### 1.1 The chain, forward from the pool

The pool's two anchors say Hermes is (i) a locally-installed, already-authenticated CLI agent and (ii)
something that also has a gateway form. `paperclip_assessment.md` enumerates `hermes_local` and
`hermes_gateway` as two of at least eleven built-in adapters;[^paperclip] `dedicated_edge_routing.md`
quotes Paperclip grouping `hermes_local` with the local CLI adapters for which *"Paperclip assumes the CLI
is already installed and authenticated on the host machine."*[^edge-routing]

Fetching Paperclip's own adapter overview as raw markdown resolves both rows:

> "| Hermes | `hermes_local` | Runs the local Hermes CLI through `@paperclipai/hermes-paperclip-adapter` |"
> "| Hermes Gateway | `hermes_gateway` | Calls an already-running Hermes API server through `@paperclipai/hermes-paperclip-adapter/gateway` |"[^pc-adapters]

That names a package. The **npm registry JSON** for it — a raw API response, not a rendered page — carries:

> `"description": "Paperclip adapters for Hermes Agent local CLI and Hermes Gateway HTTP/SSE runs"`
> `"keywords": ["paperclip","hermes","hermes-agent","ai-agent","adapter","orchestration"]`[^npm]

And the package's in-repo README, fetched raw, states the upstream directly:

> "A [Paperclip](https://paperclip.ing) adapter package that lets you run [Hermes Agent](https://github.com/NousResearch/hermes-agent) as a managed employee in a Paperclip company."
> "Hermes Agent is a full-featured AI agent by [Nous Research](https://nousresearch.com) with 30+ native tools, persistent memory, session persistence, 80+ skills, MCP support, and multi-provider model access."[^pc-hermes-readme]

Its prerequisites line closes the loop on *what kind of thing* it is: *"[Hermes Agent](https://github.com/NousResearch/hermes-agent) installed (`pip install hermes-agent`)"* and *"Python 3.10+"*.[^pc-hermes-readme]

**Confirmed at the destination.** `api.github.com/repos/NousResearch/hermes-agent` returns
`default_branch: main`, `language: Python`, `license.spdx_id: MIT`, `stargazers_count: 226385`,
`forks_count: 44120`, `open_issues_count: 28829`, `created_at: 2025-07-22T22:22:28Z`,
`pushed_at: 2026-08-06T12:06:41Z`, `archived: false`, homepage `https://hermes-agent.nousresearch.com`,
description *"The agent that grows with you"*.[^gh-hermes] **The default branch was confirmed via the API
before any raw fetch**, per the branch-404 lesson recorded in the prior-art paper.[^prior-art]

*(Confidence: **definitive**. Every link in the chain is a first-party JSON API response or a raw
first-party markdown file.)*

### 1.2 The candidates ruled out, and how

| Candidate | What it actually is | Ruled out because |
|---|---|---|
| **Nous Research Hermes LLM family** (e.g. `NousResearch/Hermes-4-70B`) | HuggingFace model API returns `pipeline_tag: text-generation`, `library_name: transformers`, tags including `Llama-3.1`, `base_model:meta-llama/Llama-3.1-70B`[^hf-hermes4] | A model, not a runtime. It has no CLI, no API server, no adapter. **This is the dangerous one** — same organisation, same word, and the models are what Nous is best known for. Both exist; they are different products. Hermes Agent's *own* subscription proxy serves Hermes-4 models as inference[^sub-proxy] — i.e. the agent *consumes* the LLM family, which is exactly how a careless read fuses them. |
| **`facebook/hermes`** — the JS engine | GitHub API: *"A JavaScript engine optimized for running React Native."*, `default_branch: static_h`, `language: JavaScript`, `stargazers_count: 11236`, `created_at: 2018-10-22`[^gh-fbhermes] | Not an agent, not a CLI, no relationship to Paperclip. |
| **"Hermes" as a generic gateway/messaging name** | — | Not pursued past the point the positive identification closed. Stated so the reader knows the search stopped deliberately. |

**Search method for the disambiguation** (stated per the negative-finding rule): forward chain from the
pool anchors → Paperclip `docs/adapters/overview.md` (raw) → npm registry JSON for the named package →
package README (raw) → GitHub repo metadata API. Confirmatory: one web search for `"Hermes Agent" CLI`
used **only to locate candidate URLs**, never cited as a source. Negative checks: GitHub metadata API for
`facebook/hermes`, HuggingFace model API for `NousResearch/Hermes-4-70B`.

### 1.3 One relationship that is NOT established — stated as a gap

Hermes Agent's repo `topics` include `clawdbot`, `moltbot` and `openclaw`,[^gh-hermes] and it ships a
migration guide whose frontmatter reads *"Complete guide to migrating your OpenClaw / Clawdbot/Moldbot
setup to Hermes Agent"* with the body stating *"`hermes claw migrate` imports your OpenClaw (or legacy
Clawdbot/Moldbot) setup into Hermes"* and *"Reads from `~/.openclaw/` by default."*[^migrate-openclaw]
Paperclip separately ships an `openclaw_gateway` adapter as a distinct built-in.[^pc-adapters]

**Whether Hermes Agent is a rename/fork of OpenClaw, or an unrelated project that courts its users, is
NOT established by anything fetched.** A migration importer and SEO topics are consistent with either.
Searched: the repo's `website/docs/guides` listing (34 entries), the migration guide's first 40 lines, the
repo description and topics. **Not found via those.** Do not infer a lineage from this paper.

*(Confidence: **definitive** that the migration tool and topics exist; the lineage itself is an explicit
**gap**.)*

### 1.4 One directional-only link, flagged

The Paperclip↔Hermes relationship is evidenced **only from Paperclip's side** — its adapter table, its
package, its package README. Nothing fetched from Nous Research acknowledges Paperclip. Searched: the
hermes-agent `website/docs` tree (8 top-level entries), `website/docs/user-guide` (24), `.../features`
(50), `.../reference` (13), `.../guides` (34) — **no Paperclip integration document appears in any of
those listings**. The integration is real (the package ships and Paperclip registers it as a built-in) but
it is a **one-party** relationship on the evidence available.

## 2. The specific model — how Hermes Agent actually works

Six mechanisms, each first-party and each raw.

**2.1 The unit of state is a session in one SQLite file.** *"Every conversation — whether from the CLI,
Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Teams, or any other messaging platform — is stored as
a session with full message history."* Storage is *"**SQLite database** (`~/.hermes/state.db`) — structured
session metadata with FTS5 full-text search, plus full message history"*, holding session id, source
platform, model, system-prompt snapshot, full message history, token counts, timestamps, and *"Parent
session ID (for compression-triggered session splitting)"*. *"The SQLite database uses WAL mode for
concurrent readers and a single writer."*[^sessions] Key tables named: `sessions`, `messages`,
`messages_fts`, plus a `gateway_routing` table mapping session keys to active session ids.[^sessions]

**2.2 Control state hangs off session rows, not off a workflow history.** Persistent goals live in
*"`SessionDB.state_meta` keyed by `goal:<session_id>`"*;[^goals] session heartbeats in
*"`SessionDB.state_meta` keyed by `heartbeat:<session_id>`"*;[^heartbeat] completion contracts, subgoals
and quality gates all *"persist in `SessionDB.state_meta` alongside the goal"*.[^goals] Sessions can be
forked: `POST /api/sessions/{id}/fork` *"Branch the session via `SessionDB` lineage (matches CLI `/branch`
semantics)"*.[^api-server]

**2.3 Fan-out is `delegate_task`, and children are context-isolated by design.** *"The `delegate_task` tool
spawns child AIAgent instances with isolated context, inherited tool access, and their own terminal
sessions. Each child gets a fresh conversation and works independently — only its final summary enters the
parent's context."* The docs state the constraint bluntly: *"Subagents start with a **completely fresh
conversation**. They have zero knowledge of the parent's conversation history."* Default concurrency is 3
(*"configurable via `delegation.max_concurrent_children`"*), depth is flat by default
(`max_spawn_depth: 1`) and nested orchestration is opt-in via `role="orchestrator"`. Leaf children are
denied `delegate_task`, `clarify`, `memory`, `send_message`, `cronjob`.[^delegation]

**2.4 Multi-task work goes on a kanban board with typed worker lanes.** *"A **worker lane** is a class of
process that the kanban dispatcher can route tasks to. Each lane has an identity (the assignee string), a
spawn mechanism, and a contract for what it must do with the task once spawned."* Lifecycle truth is the
kernel's: *"Hermes Kanban owns lifecycle truth — `ready` → `running` → `blocked` / `done` / `archived`.
Worker lanes execute work but never own that truth."* The default lane runs
`hermes -p <assignee> chat -q <prompt>` with a documented env contract (`HERMES_KANBAN_TASK`,
`HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`, `HERMES_KANBAN_WORKSPACE`, `HERMES_KANBAN_RUN_ID`,
`HERMES_KANBAN_CLAIM_LOCK`, `HERMES_PROFILE`, `HERMES_TENANT`).[^kanban-lanes]

**2.5 Two loops sit above turns, and they are explicitly different things.** `/goal` is single-session:
*"After every turn a lightweight judge model checks whether the goal is satisfied… If not, Hermes
automatically feeds a continuation prompt back into the same session."* The boundary against kanban is
stated, not implied: *"`/goal` is single-session… Setting a goal never creates a kanban card, never
assigns work to another profile, and never fans out."*[^goals] `/heartbeat` is the third: one recurring
instruction per session, *"injected only between turns (never mid-run), as a plain user-role
message"*.[^heartbeat] Durable scheduled work is a fourth surface — `hermes cron` — which the heartbeat doc
contrasts as *"Yes — fully durable scheduler"* against heartbeat's session-scoped persistence.[^heartbeat]

**2.6 The remote surface is an OpenAI-compatible API server plus a Hermes-native runs API.** Bearer auth
via `API_SERVER_KEY`, default bind `127.0.0.1`, default port 8642.[^api-server] Beyond
`/v1/chat/completions` and `/v1/responses` it exposes `POST /v1/runs`, `GET /v1/runs/{run_id}`,
`GET /v1/runs/{run_id}/events` (SSE), `POST /v1/runs/{run_id}/stop`, `POST /v1/runs/{run_id}/approval`, a
jobs CRUD under `/api/jobs`, a sessions CRUD under `/api/sessions`, `GET /v1/skills`, `GET /v1/toolsets`,
and `GET /v1/capabilities`.[^api-server]

## 3. The six axes

### 3.1 Durability — bespoke, session-scoped, and disclaimed by its own docs

**The disclaimer is first-party and unambiguous.** Under a warning admonition titled *"Background
completion durability is not durable execution"*:

> "A Hermes process restart does **not** resume a running child. Its attempt becomes `unknown` because Hermes cannot prove which side effects happened."
> "A child that completed before restart but whose result was not delivered is restored and routed back through the owning session's normal checks."[^delegation]

What **is** durable is the *delivery* of a completed result, and the mechanism is worth reading:

> "When a background delegation finishes, Hermes stores its completion event in the active profile's `state.db` before publishing it to the normal fresh-turn queue. If Hermes restarts after completion but before delivery, the pending event is restored and routed through the same ownership checks. Competing consumers use a durable claim, so only the consumer that successfully accepts the synthetic turn acknowledges delivery; failed attempts release the claim for retry."[^delegation]

That is a hand-rolled at-least-once outbox on SQLite. It is competent, and it is precisely the layer
Temporal supplies.

**Kanban durability is a second, stronger, separate implementation.** The dispatcher handles: stale claims
(*"reclaimed after `DEFAULT_CLAIM_TTL_SECONDS` (15 min default) — but only if the worker process has
actually died. A live worker… gets the claim *extended* instead of killed; only a dead PID is
reclaimed."*); crashed workers via `detect_crashed_workers`; a consecutive-failure breaker; per-task
`max_runtime_seconds` as the deadlock backstop; and run fencing (*"the worker can use the
`expected_run_id` parameter on terminating tools to fail fast if its own run was already
superseded"*).[^kanban-lanes] The audit trail is table-shaped: `task_runs` rows carrying `log_path`, exit
code, summary and metadata, and `task_events` rows carrying *"every state transition (`promoted`,
`claimed`, `heartbeat`, `completed`, `blocked`, `gave_up`, `crashed`, `timed_out`, `reclaimed`,
`claim_extended`)"*.[^kanban-lanes]

**The ceiling is the storage engine.** State is per-profile SQLite in WAL mode — *"concurrent readers and
a single writer"*[^sessions] — and the Docker guide warns: *"Never run two Hermes **gateway** containers
against the same data directory simultaneously — session files and memory stores are not designed for
concurrent write access."*[^docker] A durability substrate that cannot have two writers cannot be a
multi-host backbone.

*(Confidence: **definitive** on every quoted mechanism; **derived** on the "cannot be a multi-host
backbone" reading — inputs: the single-writer statement, the two-container warning, and
`system-overview.md`'s two-server HA target.[^system-overview])*

### 3.2 Domain generality — general at the boundary, *typed only on the failure path*

Hermes is domain-general by construction: toolsets are *"`terminal`, `file`, `web`, `browser`,
`code_execution`, `vision`, `mcp`, `creative`, `productivity`"*,[^pc-hermes-readme] and session sources
enumerate twenty-plus origins including `homeassistant`, `email`, `sms`, `cron` and
`batch`.[^sessions] Coding is one use among many; the messaging gateways are the front door. **This is a
materially more general boundary than either `bernstein` or Paperclip**, both of which are sold for
code.[^problem-statement]

**But the result contract is asymmetric, and this is the finding that matters.** The *success* payload is
weakly typed: `GET /v1/runs/{run_id}` returns `"output": "Done."` — a string;[^api-server]
`kanban_complete(summary=..., metadata=...)` takes a human summary plus free-form metadata, and the docs
route structure into comments instead: *"`kanban_block` only carries the human-readable `reason`. Comments
are the durable annotation channel — every audit-relevant field (changed_files, tests_run, diff_path or PR
url, decisions) belongs there."*[^kanban-lanes]

The *failure* payload, by contrast, **is** typed, with named fields and explicit null semantics:

> "`timeout_seconds` (the configured cap), `timed_out_after_seconds` (actual wall clock), and `timeout_phase` (`before_first_llm_call` when the child never reached its first request, `after_llm_calls` otherwise). All three are `null` on non-timeout errors."[^delegation]

> "The `stalled` event carries structured metadata mirroring the sync-path timeout fields: `stalled_after_quiet_seconds`, `stall_threshold_seconds`, `stall_phase` (`idle` / `in_tool`), and `stall_grace_seconds`."[^delegation]

**Reading.** Hermes solved *typed refusal* and left *typed result* as prose. Our recipe element 3 — "a
parent branches on what a child concluded because the conclusion is a value, not prose"[^problem-statement]
— is therefore only **half**-answered by this system. Take the failure half; the success half is still
ours to design. *(derived — inputs: the runs-API response shape, the `kanban_complete` signature, the two
metadata blocks above, and the problem statement's element 3.)*

**What a non-Claude edge exposes — the answer the `The edges` stub asked for.** Hermes' answer to
"different subscriptions expose different capabilities" is **enumerate them over REST, and do not ask the
model**: *"`GET /v1/skills` and `GET /v1/toolsets` let external clients enumerate the agent's capabilities
deterministically over REST instead of asking the model. Both are read-only and gated by
`API_SERVER_KEY`."*[^api-server] Per-request routing is a deterministic four-step precedence — session
`/model` override, then a `model_routes` alias, then direct request `model`/`provider`, then gateway
defaults — and conflicts **fail** rather than degrade: *"If a request sends a `provider` that conflicts
with a configured `model_routes` alias, Hermes rejects the request with `400` instead of silently remixing
route credentials with another provider."*[^api-server] Eight inference providers ship (*"Anthropic,
OpenRouter, OpenAI, Nous, OpenAI Codex, ZAI, Kimi Coding, MiniMax"*).[^pc-hermes-readme]

### 3.3 Dispatch / worker model — addressed lanes, claimed locally, with no cross-host contention

**Routing is by address, not by contention.** *"The dispatcher matches `task.assignee` against either a
Hermes profile name (the default lane shape) or a registered non-spawnable identifier."* The
unresolvable-address behaviour is the sentence worth having: *"Tasks whose assignee doesn't resolve are
left on `ready` with a `skipped_nonspawnable` event so a board operator can fix them; **they are not
silently dropped or executed by an arbitrary fallback**."*[^kanban-lanes]

**But the claim is host-local, not distributed.** The claim lock string is `<host>:<pid>:<uuid>`, crash
detection is *"a worker whose host-local PID has vanished"*, and the board is a single SQLite file
(`HERMES_KANBAN_DB` is *"absolute path to the per-board SQLite file"*).[^kanban-lanes] There is no
cross-node work-stealing RPC and no distributed lease — because there is no cluster. Compared against the
two comparators already in the pool: `bernstein` contends on a central queue with documented tie-break and
donor/receiver work-stealing;[^edge-routing] Hermes does not contend at all, because every board lives on
one host.

**Hermes is therefore closer to our dedicated-addressed-worker design than either comparator** — and it
gets there by not being distributed, which is not a solution we can copy. What *is* copyable is the
**failure vocabulary around addressing**: `skipped_nonspawnable`, plus stranded-task detection —
*"a ready task whose assignee never produces a claim within `kanban.stranded_threshold_seconds` (default
30 min) shows up in `hermes kanban diagnostics` as a `stranded_in_ready` warning. Severity escalates to
error at 2x the threshold and critical at 6x. Catches typo'd assignees, deleted profiles, and down
external worker pools in one signal — identity-agnostic, no per-board allowlist to
curate."*[^kanban-lanes] That last clause is the design answer to the open risk in
`dedicated_edge_routing.md`: **what happens when work is addressed to an edge that never comes up.**

*(Confidence: **definitive** on the mechanisms; **derived** on the comparison — inputs: the quoted
kanban mechanisms and `dedicated_edge_routing.md` §3.1's bernstein protobuf findings.[^edge-routing])*

### 3.4 Credential locality — the sharpest axis, and the `_local`/`_gateway` split resolves cleanly

**What crosses in the `_gateway` form.** Paperclip's `hermes_gateway` config is documented as
`apiBaseUrl`, `apiKey` (*"`<same-value-as-API_SERVER_KEY>`"*), `paperclipApiUrl`, `sessionKeyStrategy`,
`timeoutSec`, and the mode *"does not start Hermes. It creates runs with `POST /v1/runs`, streams Hermes
events with SSE, polls run status as a fallback, and stops timed-out runs with `POST
/v1/runs/{run_id}/stop`."*[^pc-hermes-readme] On the Hermes side, the *provider* credential lives in
`~/.hermes/auth.json` on the Hermes host — the credential-pool storage schema is documented there, and
`hermes portal` *"stores the refresh token in `~/.hermes/auth.json` — the same place all Hermes provider
logins live."*[^cred-pools][^sub-proxy]

> **Therefore: the gateway form relocates the CONTROL boundary and leaves the CREDENTIAL boundary where it
> was.** What leaves the orchestrator is an API-server bearer plus prompt text over HTTP/SSE. The
> subscription credential does not move. *(derived — inputs: the Paperclip gateway config block, the
> `auth.json` storage schema, and the `hermes portal` storage statement. No single source states this
> conclusion; it is this paper's inference across three.)*

**That is exactly the federated-trunk shape the trust-tier table describes** — *"Federated … sends work
over the trunk, holds no edge credential."*[^problem-statement] A shipped system does it, which de-risks
the design and removes any claim of novelty for it.

**Subscription-auth at the edge is not merely present here, it is tooled.** `hermes auth add anthropic
--type oauth` is documented with the parenthetical *"(requires Claude Max plan + extra usage credits)"*,
and auto-discovery seeds pools from *"Claude Code credentials | `~/.claude/.credentials.json` | Yes
(Anthropic)"*.[^cred-pools] **The "extra usage credits" qualifier is a live constraint and should be
carried into `anthropic_tos_and_enterprise.md`'s next refresh** — it is a first-party statement that a Max
subscription alone is documented as insufficient for this path in Hermes.

**Borrowed secrets are reference-only at the storage boundary** — a genuinely good design:

> "Borrowed runtime secrets (for example env vars, Bitwarden/Vault/keyring/systemd references, and custom config values) are reference-only at the `auth.json` boundary. Hermes can use the resolved value in memory for the current run, but it persists only metadata such as the source ref, label, status, request counters, and a non-reversible fingerprint."[^cred-pools]

**Where the boundary is honestly weak, by the docs' own admission.** The API server *"gives full access to
hermes-agent's toolset, **including terminal commands**"* and `API_SERVER_KEY` is *"**required for every
deployment**, including the default loopback bind on `127.0.0.1`."*[^api-server] The write-guard note is
equally candid: *"Write guards apply to `write_file` and `patch` only. The `terminal` tool runs as the same
OS user and can still `cat` or overwrite denied paths via shell commands… it does not sandbox a hostile or
compromised agent."*[^security] And the subscription proxy carries *"⚠ **Be aware:** anyone on your
network can now use your Portal subscription. The proxy has no auth of its own — it accepts any
bearer."*[^sub-proxy]

### 3.5 Deployment shape — Docker + s6, one container many profiles, and Kubernetes is a documented degradation

The documented production shape is a container. Image `nousresearch/hermes-agent`, *"based on
`debian:13.4`"*, with *"**[`s6-overlay`](https://github.com/just-containers/s6-overlay) v3** as PID 1
(replaces the older `tini`) — supervises the dashboard and per-profile gateways with auto-restart on
crash, reaps zombie subprocesses, and forwards signals."*[^docker] Data is one bind mount: *"The
`/opt/data` volume is the single source of truth for all Hermes state."*[^docker] Multi-tenancy inside the
box is by profile: *"**Inside the official Docker image, the s6 supervision tree treats each profile as a
first-class supervised service**, so the recommended deployment is **one container hosting all
profiles**."* Each profile gets *"A dedicated s6 service slot at `/run/service/gateway-<name>/`"*, s6
auto-restart, per-profile rotated logs, and a boot reconciler that *"reads `gateway_state.json` from each
profile directory and brings the slot back up only for profiles whose last recorded state was
`running`."*[^docker]

**The Kubernetes statement is explicit and it is a degradation, not a path:**

> "When a platform wraps the image entrypoint under its own PID-1 init (Fly.io Machines, `docker run --init`, some Nomad/Kubernetes setups), `/init` would abort with `s6-overlay-suexec: fatal: can only run as pid 1` — so the dispatcher instead runs the stage2 bootstrap directly and exec's the main wrapper without s6. On that fallback path the requested command still runs, but supervised services (dashboard, per-profile gateways) are unavailable."[^docker]

**Gap, stated with method: no Kubernetes deployment document and no host-systemd unit document were
found.** Searched: the `website/docs` top-level listing (8 entries), `website/docs/user-guide` (24
entries), `website/docs/user-guide/features` (50 entries), `website/docs/reference` (13 entries), and
`website/docs/guides` (34 entries) — no entry names Kubernetes, Helm, k8s, or systemd. Two oblique
references exist (the subscription proxy suggests *"`tmux`, `nohup`, or a systemd unit if you want it to
survive logout"*;[^sub-proxy] the approval table blocks *"`gateway run` with `&`/`disown`/`nohup`/`setsid`
— Prevents starting gateway outside service manager"*[^security]), which together imply host service-manager
integration exists but **do not document it**. Not asserted here.

### 3.6 Self-improvement over durable artifacts — present, layered, and human-gated

Two mechanisms worth naming because they instantiate recipe element 2.[^problem-statement]

**The `/goal` judge is a distinct actor at a distinct layer.** *"After every turn, Hermes calls an
auxiliary model with: The standing goal text… The agent's most recent final response (last ~4 KB of
text)… A system prompt telling the judge to reply with strict one-line JSON:
`{"verdict": "done" | "continue" | "wait", "reason": "<one-sentence rationale>"}`."*[^goals] The judge is
routable to a different, cheaper model.[^goals] It **fails open**: *"If the judge errors… Hermes treats the
verdict as `continue` — a broken judge never wedges progress. The **turn budget** is the real
backstop."*[^goals]

**`hermes approvals suggest` is a ratification loop over a durable artifact.** It *"scans the session
database (`~/.hermes/state.db`) for dangerous-classified commands that actually executed… aggregates them
into patterns… and ranks them by approval frequency"*, with safety rules that are structurally what our
CPI log does by hand: *"**Nothing is ever applied automatically** — the default run is read-only; only an
explicit `--apply N[,M...]` writes to `config.yaml`"* and *"**Destructive classes are never proposed**, no
matter how often they were approved… `rm -rf build/` approved 100 times still never yields an `rm`
entry."*[^security]

### 3.7 The architecture verdict — five grounds, stated once

1. **Durability is bespoke and self-disclaimed.** §3.1. Adopting it means adopting a SQLite outbox we
   would then run *underneath* Temporal, or instead of it. Neither is coherent.
2. **The unit is a session, not a workflow.** §2.2. There is no deterministic replay, no event history, no
   separation of workflow code from activity I/O. Our seam *"activity ≠ workflow — a workflow doing
   network I/O cannot replay"*[^system-overview] has no counterpart here.
3. **It is a competing everything-layer, not a backbone.** At least 49 feature documents in one directory
   (§6b), 30+ native tools, its own memory, skills, dashboard, cron, and twenty-plus messaging
   gateways.[^pc-hermes-readme][^sessions] Taking Hermes as substrate means taking a second opinionated
   assistant into a repo whose job is to *be* the assistant.
4. **The deployment model fights the settled target.** §3.5. Recommended shape is one Docker container
   under s6 as PID 1; the documented Kubernetes interaction loses supervised services. `system-overview.md`
   fixes HA on k3s with systemd workers.[^system-overview]
5. **Single-operator-shaped, with a genuinely good exception.** Profiles isolate config, memory, skills and
   credentials, and per-profile API auth **fails closed** (§4.9) — better than the nearest neighbour's
   documented posture.[^problem-statement] But the recommended topology is many profiles on one host under
   one operator, and `HERMES_TENANT` — the one env var that hints at more — is **undocumented** (§6d).

*(Confidence: **derived** for the verdict; inputs are the cited sections above plus `system-overview.md`
§ Deployment target and `problem-statement.md` § Where this sits.)*

## 4. What is worth mining regardless — twelve items, ranked

Ranking is by *how much a decision here changes if we take it*. Cost is S (hours–1 day) / M (2–5 days) /
L (>1 week). Every cost is **derived** — inputs are the cited mechanism plus the named landing surface.

### 4.1 `GET /v1/capabilities` — a machine-readable capability document at the edge `RANK 1` `cost: S`

**What it is.** *"Returns a machine-readable description of the API server's stable surface for external
UIs, orchestrators, and plugin bridges"*, with a payload whose shape is given in full: `object`,
`platform`, `model`, `auth: {"type": "bearer", "required": true}`, and a `features` map with
`chat_completions`, `responses_api`, `run_submission`, `run_status`, `run_events_sse`, `run_stop`. The
stated purpose is the load-bearing part: *"Use this endpoint when integrating dashboards, browser UIs, or
control planes so they can discover whether the running Hermes version supports runs, streaming,
cancellation, and session continuity **without depending on private Python internals**."*[^api-server]
Individual features are advertised as flags — the approval endpoint *"is advertised in `/v1/capabilities`
as the `run_approval` feature so external UIs can detect support before surfacing an approval
prompt"*, and the sessions surface via *"`session_*` feature flags and `endpoints.session_*` entries so
external UIs can detect support and fall back safely."*[^api-server]

**Why it matters here.** The Paperclip paper flagged `testEnvironment` as *"the capability-advertisement
primitive a dedicated-edge model needs"* and noted differentiator #2's design *"currently has no
equivalent."*[^paperclip] **This is a better version of that primitive**: a *runtime, versioned,
negotiable* capability document rather than a one-shot preflight probe, and it is exactly what the
provider-shaped-edge stub needs — *"The backbone should not care which; the edge should"*[^problem-statement]
only works if the edge can *say* what it is. Combined with `/v1/skills` and `/v1/toolsets` (§3.2), the
pattern is: **the edge publishes a typed capability manifest; the backbone reads it; nobody asks a model.**

**Lands on.** The Temporal worker registration contract in `Phase: Temporal Integration`, and
`problem-statement.md` § *The edges* when that stub is exercised. **Sequencing constraint:** this is an
interface decision and must land alongside worker registration, not after it.

### 4.2 The five-field completion contract + deterministic quality gates `RANK 2` `cost: S–M`

**What it is.** A `/goal` may carry a structured contract with five optional fields — *"`outcome` — The
single end state that must be true when done"*, *"`verification` — The specific test / command / artifact
that *proves* the outcome"*, *"`constraints` — What must not change or regress"*, *"`boundaries` — Which
files, dirs, tools, or systems are in scope"*, *"`stop_when` — The condition under which Hermes should
stop and ask for input."* When set, *"the **judge prompt** decides `done` *only when the verification
criterion is met with concrete evidence* (a command result, file excerpt, test output) — not a loose
'looks done' claim."*[^goals]

**Above the judge sits something deterministic.** *"A **quality gate** is stronger: a deterministic shell
command that must exit 0 before the goal can complete at all."* The ordering is the point: *"**Gates run
before the judge.** If any gate fails, the judge is *not called* — a red gate is deterministic evidence the
goal isn't done. The gate's exit code and output tail (last ~3 KB) become the continuation prompt, so the
agent iterates against the actual failure instead of a vibe."* And the memoization is a detail worth
stealing outright: *"**Unchanged workspace → no re-run.** If a gate failed and nothing changed in the
workspace since (tracked via a git fingerprint of HEAD + working-tree status), the gate is not re-run — the
recorded failure is replayed and the attempt count advances. A stuck agent can't burn wall-clock re-running
an identical red suite."* Bounded: *"Each gate defaults to 3 retries and a 5-minute timeout."*[^goals]

**Why it matters here.** Our completion contract today is *"Each child declares a pattern its final output
must contain, so `exit 0` provably means *finished*."*[^system-overview] That is one field where Hermes has
five plus a deterministic pre-judge gate. **The gate-before-judge ordering is the transferable insight**,
and it is compatible with our `parent calls no model` seam in a way the judge itself is not (§5c).

**Lands on.** `docs/standards/workflow-scripts.md` § completion contract; and the *"typed handoff between
runs"* item in `system-overview.md` § What is not built.

### 4.3 Structured terminal metadata on every failure class `RANK 3` `cost: S`

**What it is.** Both quoted in full in §3.2: the timeout triple (`timeout_seconds`,
`timed_out_after_seconds`, `timeout_phase` ∈ {`before_first_llm_call`, `after_llm_calls`}, *"All three are
`null` on non-timeout errors"*) and the stall quadruple (`stalled_after_quiet_seconds`,
`stall_threshold_seconds`, `stall_phase` ∈ {`idle`, `in_tool`}, `stall_grace_seconds`).[^delegation] Their
purpose is stated: *"so parents and hooks can distinguish a stopwatch kill from other failures **without
parsing text**."*[^delegation]

**Why it matters here.** A `claude -p` activity under Temporal fails in several distinguishable ways and
the retry policy should differ per way. `timeout_phase: before_first_llm_call` means *provider unreachable
or auth broken* — retry is right. `after_llm_calls` means *the work was too big* — retry is wrong. This is
the smallest, highest-leverage item in the paper. **Also note the diagnostic-on-zero-call rule**: when a
child times out having made zero API calls, Hermes writes a structured dump containing *"the subagent's
config snapshot, credential-resolution trace, any early error messages, and stack traces for **all** live
threads (not just the child's own) — a child parked waiting on a nested helper thread is indistinguishable
from a slow provider without the full picture."*[^delegation]

**Lands on.** The `claude_cli` activity's exception taxonomy and Temporal retry policy, `Phase: Temporal
Integration`. **Must land before workers are written.**

### 4.4 Progress-based stall detection, and the scar that produced it `RANK 4` `cost: S design`

**What it is, and it is a reversal.** *"By default there is **no wall-clock timeout** on subagents.
Children fail only from what they're actually doing — API errors, tool errors, or hitting their iteration
budget — never from a delegation-level stopwatch. Earlier releases shipped a hard cap (300s, later 600s),
which kept killing legitimately busy children mid-task: deep code reviews, large research fan-outs, and
slow reasoning models routinely need more than 10 minutes while making steady progress the whole
time."*[^delegation]

The replacement samples progress, and the definition of progress is the payload design we need:
last-activity *"ticks on **every streamed token**, tool transition, and API-call boundary, so a child
mid-stream on a long response always counts as alive"*; and *"An in-flight model wait still counts as
progress — subagents refresh the activity clock while waiting on the provider, so a slow local / long-prefill
completion is not treated as stalled."*[^delegation] Thresholds: *"450s idle, 1200s while inside a tool —
legitimately slow terminal commands and web fetches get the higher ceiling"*, then a *"120s grace
window"*, then *"force-finalized with a terminal `stalled` completion event, so the owning session hears an
outcome instead of going silent, and the async slot frees for new work."*[^delegation] The
kanban dispatcher implements the same principle at a different altitude: a live-but-slow worker gets its
claim *extended*; only a dead PID is reclaimed.[^kanban-lanes]

**Why it matters here.** This is the second independent production confirmation — after Paperclip's
`lastOutputAt` / `lastUsefulActionAt` columns[^paperclip] — that **a heartbeat proving liveness cannot
distinguish a working agent from a wedged one**, and it adds what Paperclip's did not: a *two-ceiling*
model (idle vs in-tool) and an explicit ruling that *waiting on the provider is progress*. Our
`claude -p` runs take 10–60 minutes;[^system-overview] a naive Temporal `heartbeat_timeout` would kill
them exactly the way Hermes' 600s cap did.

**Lands on.** The `claude_cli` activity heartbeat payload and the `heartbeat_timeout` /
`start_to_close_timeout` choice. Reinforces, and is corroborated by, `raw/python_sdk_long_activities.md`.

### 4.5 Addressing failure semantics: `skipped_nonspawnable` and stranded-task escalation `RANK 5` `cost: S`

**What it is.** Both quoted in §3.3. An unresolvable assignee leaves the task on `ready` with a named
event, *"not silently dropped or executed by an arbitrary fallback"*; a task nobody claims within 30
minutes surfaces as `stranded_in_ready`, escalating warning → error → critical at 1x / 2x / 6x the
threshold, and the design note explains why it generalises: *"identity-agnostic, no per-board allowlist to
curate."*[^kanban-lanes]

**Why it matters here.** `dedicated_edge_routing.md` argues for addressed workers over a contended queue.
The failure mode addressed workers introduce and contended queues do not is **work addressed to an edge
that never comes up** — a laptop that is closed, an edge whose credential expired, a typo'd task-queue
name. Hermes has the detector, and crucially has it *without* maintaining a registry of valid addresses.
Our Temporal equivalent is a schedule that queries for workflows pending on a task queue with no poller.

**Lands on.** `dedicated_edge_routing.md`'s open risk list, and the routing design in
`Phase: Temporal Integration`.

### 4.6 Credential locality — precedent, tooling, and one live constraint `RANK 6` `cost: 0 (correction) / M (pools)`

**What it is.** §3.4 in full. Three separable takeaways: (i) the `_gateway` split relocates control not
credentials — a validated topology for the federated trunk, cost **zero**, it is a correction to how we
describe our own design; (ii) subscription-auth at the edge is *tooled*, with `~/.claude/.credentials.json`
auto-discovered into an Anthropic pool[^cred-pools] — cost **zero**, it is the second large-scale
precedent after Paperclip and it further deflates any novelty claim; (iii) **credential pools** as a
capability — same-provider rotation with strategies (`fill_first`, `round_robin`, `least_used`, `random`),
per-error-class cooldowns (429 → 1h after a second consecutive hit, 402 → immediate rotate + 1h, 401 →
refresh first, 5m), and pool inheritance into children with *"Per-task credential leasing… so children
don't conflict with each other when rotating keys concurrently"*[^cred-pools] — cost **M**, and only if we
ever run more than one credential per edge.

**One live constraint to carry forward.** The Anthropic OAuth path is documented as *"(requires Claude Max
plan + extra usage credits)"*.[^cred-pools] **This belongs in `anthropic_tos_and_enterprise.md`'s next
refresh** as a first-party data point about what a Max subscription alone does and does not enable outside
Anthropic's own clients.

**One honest cost the pool docs surface that our design will also pay.** *"When the pool rotates to a
different key mid-session, the new key has no cached prefix for your conversation — the next request
re-reads the full history at undiscounted input price."*[^cred-pools] Any failover across credentials — ours
included — pays a full-price context re-read.

### 4.7 The worker-lane contract as a shape `RANK 7` `cost: M`

**What it is.** Three obligations and exactly three terminators. *"To be a kanban worker lane, an
integration must provide three things"* — an assignee string, a spawn mechanism, and a lifecycle
terminator — and *"Every claim must end in exactly one of: `kanban_complete(summary=..., metadata=...)`…
`kanban_block(reason=...)`… The worker process exits without a tool call. The kernel reaps it and emits
`crashed` (PID died) or `gave_up` (consecutive-failure breaker tripped) or `timed_out` (max_runtime
exceeded)."* The enforcement clause is the one to copy: *"The kanban kernel enforces that exactly one of
these terminates each run. **A worker that calls neither and exits normally is treated as
crashed.**"*[^kanban-lanes]

The review convention layered on top is a second, separable idea: block-instead-of-complete with *"`reason`
prefixed `review-required: `"*, structured evidence dropped into a comment first because
*"`kanban_block` only carries the human-readable `reason`"*, and *"**Reviewer either approves and
unblocks**, which respawns the worker with the comment thread for follow-ups."*[^kanban-lanes] That is our
`review-pr` HOLD-with-runway loop, with a durable annotation channel our version lacks.

**Why it matters here.** Our composition contract is *"Each child declares a pattern its final output must
contain."*[^system-overview] The Hermes contract adds **exhaustiveness** (exactly one of three, absence is
a failure) and **a distinct waiting terminator** (`blocked` is not `done` and not `failed`). The three-way
`complete` / `block` / `reaped` split maps directly onto Temporal's completed / signal-wait / timed-out.

**Lands on.** `docs/standards/workflow-scripts.md` § composition; the child-workflow completion contract.

### 4.8 Artifacts ride the completion event `RANK 8` `cost: S`

**What it is.** `kanban_complete(summary=..., artifacts=["/tmp/q3-revenue.png", "/tmp/q3-report.pdf"])`,
and the notifier uploads each artifact natively when it delivers the completion message. One line of
defensive design: *"Files that don't exist on disk when the notifier runs are silently
skipped."*[^deliverable] The gateway's path-extraction rule is a second, smaller idea with a stated
rationale: *"Paths inside code blocks and inline code are ignored so code samples are never
mutilated"*, and *"`.py`, `.log`, and other source-file extensions are intentionally excluded so the agent
doesn't auto-ship arbitrary source files."*[^deliverable]

**Why it matters here.** Our completion contract carries *"one stable identifier on the final
line"*.[^system-overview] An `artifacts` list is the natural extension when a workflow's output is a file
rather than a PR number — a research paper, a diff, a report. **Small, and it is the concrete first step of
the typed-result work §3.2 says is still ours to do.**

### 4.9 Per-profile auth that fails closed, and the scar that produced it `RANK 9` `cost: 0 to learn, S to apply`

**What it is.** With multi-profile routing enabled, *"authentication is bound to the routed profile"*:
*"Requests to `/p/<profile>/v1/...` must present that profile's own `API_SERVER_KEY`… The default
listener's key is rejected on named-profile prefixes"*, and *"A named profile with no `API_SERVER_KEY` of
its own **fails closed** — its prefix is unreachable until you set one."* Under a warning admonition
titled *"Breaking change (July 2026)"*: *"Before this fix, a valid default-profile key was accepted on any
`/p/<profile>/` prefix."*[^api-server]

**A second, larger scar, stated as cause.** Under *"Why `--insecure` was removed"*: *"An unauthenticated
public dashboard was the entry point for the June 2026 MCP-config persistence campaign: internet scanners
reached exposed dashboards (and OpenAI API servers) and drove the agent into planting an SSH-key backdoor.
The auth gate is now mandatory on every non-loopback bind."* The escape hatch was not merely deprecated but
neutered: *"`HERMES_DASHBOARD_INSECURE=1` is now a deprecated no-op (it logs a warning and is
ignored)."*[^docker]

**Why it matters here.** Both are the *"Nothing may assume a single operator"* consequence[^problem-statement]
learned the expensive way by a system with 226k stars. The pattern to carry: **a tenant boundary that
accepts a sibling's credential is not a tenant boundary**, and **an unauthenticated bind on a non-loopback
address is an agent-takeover vector, not a convenience.** Any future operator surface here inherits both.

### 4.10 Secret redaction at every boundary the data crosses `RANK 10` `cost: S`

**What it is.** On subagent lifecycle events: *"free-text fields pass forced secret redaction before
leaving the process."*[^api-server] On session exports: `--redact` *"scrubs secrets (API keys, tokens,
credentials) from exported content on any format"*, and for the trace format the default inverts —
*"Trace exports are secret-redacted by default (they're meant to leave the machine); `--no-redact` opts
out after manual review."*[^sessions] On MCP tool errors, named patterns are replaced with `[REDACTED]`:
GitHub PATs, `sk-` keys, bearer tokens, and `token=` / `key=` / `API_KEY=` / `password=` / `secret=`
parameters.[^security]

**Why it matters here.** Every workflow run posts a decision log and tooling suggestions to a PR
thread,[^system-overview] and every dispatch writes JSONL run logs — two boundaries where agent-produced
free text leaves the machine. **The design rule to take is the inverted default**: redact-by-default on
the surface that is *meant* to leave, opt-out with review.

### 4.11 `hermes approvals suggest` — a shipped, human-gated improvement loop `RANK 11` `cost: S–M`

**What it is.** §3.6 in full: mine the session DB for dangerous-classified commands that actually
executed, aggregate into patterns, rank by approval frequency, propose, never auto-apply, and hard-exclude
destructive classes regardless of frequency.[^security]

**Why it matters here.** It is our CPI loop's shape — observe, propose, human rules — implemented as a
product feature over a durable artifact, and it independently arrives at our governance rule that agents
*"propose standards; humans write them."*[^system-overview] The transferable increment is the
**never-propose list**: a frequency-driven proposer needs a category that frequency cannot unlock.

**Lands on.** `config/hooks/block-dangerous.sh` (a mined-allowlist proposer over run logs), and the CPI
decisions-log methodology.

### 4.12 The judge's `wait` verdict — parking a loop on an external signal `RANK 12` `cost: M`

**What it is.** A third verdict alongside done/continue. *"Every turn, the judge is shown the agent's live
background processes… When the agent's progress is genuinely gated on one of them, the judge returns a
**`wait`** verdict instead of `continue`, and the loop **parks**: the next turns are skipped (no judge
call, no continuation, no turn consumed) until the wait is satisfied."* Three release conditions:
`wait_on_session <id>` (*"releases when the process's *own trigger* fires: it exits, **or** (if it was
started with `watch_patterns`) its pattern matches"*), `wait_on_pid <pid>`, `wait_for_seconds <n>`. The
staleness guard is stated: *"If the PID is already dead when the barrier is set (or dies while parked), or
the time deadline passes, the barrier clears on the next check — a stale barrier can never wedge the
loop."*[^goals]

**Why it matters here.** *"High-level loops over persisted state… running unattended until an exit
condition it can actually observe"*[^problem-statement] must handle *waiting on something outside the
loop* — CI, a review, a human. Under Temporal this is a signal or a timer rather than a judge verdict, so
the mechanism does not transfer; **the taxonomy does**: a driver needs three outcomes, not two, and the
third must be able to expire.

## 5. Honest boundary analysis — the case against this paper's own findings

**(a) The thing this paper mostly did not check: whether any of it works.** No Python was read. Nothing was
installed, configured or run. Every claim in §2–§4 is a claim about **documentation**, and Hermes'
documentation is unusually detailed *and* unusually promotional — the adapter README's capability table
scores Claude Code and Codex at *"~5"* native tools against Hermes' *"30+"* with ❌ in every other
row.[^pc-hermes-readme] That table is marketing published by the adapter author, not a measurement, and
**nothing in this paper rests on it**. But the same voice writes the feature docs. Treat §4's costs as
estimates against described behaviour.

**(b) The scale is a hazard, not only an asset.** 226,385 stars and **28,829 open issues**.[^gh-hermes] A
system this large has features that exist because someone asked, not because they are right. Mining it
invites cargo-culting: several §4 items (claim TTL, PID reclaim, run fencing, at-least-once delivery) are
things **Temporal already provides**, and copying Hermes' implementations would mean building durable
execution on top of durable execution. The correct read of §4.7 and §4.5 is *take the vocabulary and the
failure taxonomy; do not take the machinery.*

**(c) The single highest-value item conflicts with a documented seam.** `/goal`'s judge is **an LLM in the
coordination loop**. `system-overview.md` states *"A parent calls no model"* and the seam *"decide ≠
act"*.[^system-overview] The quality gates transfer cleanly (they are shell commands with exit codes); the
judge does not. **Anyone reading §4.2 as "adopt `/goal`" has misread it** — the item is the five-field
contract and the gate-before-judge ordering, not the judge.

**(d) The domain-generality finding cuts against a differentiator, again.** Differentiator #4 was already
narrowed to *"its positioning, front door and every published use case are software
development"*.[^problem-statement] Hermes breaks even that residue: it is positioned as an assistant, its
front door is a messaging gateway, and Home Assistant is a first-class session source[^sessions] — the
exact domain named as our *next* edge.[^problem-statement] **On generality Hermes is ahead of us, in our
own stated direction.** Per the settled frame that is a WIN — the lessons are free — but it should be
recorded plainly rather than discovered later.

**(e) The strongest case FOR Hermes' architecture, stated fairly.** Its kanban dispatcher does more of what
this repo needs *today* than this repo's bash workflows do, and it runs: addressed lanes, per-task
workspaces, a claim/reclaim discipline, an audit trail of typed events, a review-required convention, and a
dashboard. If Temporal integration slips, **"run a Hermes board with our workflows as lanes" is a credible
interim** — with one blocking caveat below.

**(f) The caveat that closes (e), and it is first-party.** Wrapping our `claude -p` workflows as a Hermes
lane is **not a supported path**: *"Wiring a non-Hermes CLI tool (Codex CLI, Claude Code CLI, OpenCode CLI,
a local coding-model runner, etc.) as a kanban worker lane is *not yet a paved path*."* The dispatcher's
`spawn_fn` is pluggable, but *"the surrounding integration work — wrapping the CLI's exit code into
`kanban_complete` / `kanban_block` calls, mapping the CLI's workspace/sandbox conventions onto the
dispatcher's `HERMES_KANBAN_WORKSPACE` env, handling auth and per-CLI policy — is still per-integration
design work."* The history is named: issue #19931 and *"the closed-not-merged Codex-specific PR #19924 —
those describe the original architecture proposal but didn't land a runner."*[^kanban-lanes] **So the one
integration that would make (e) cheap is the one Hermes has tried and not shipped.**

**(g) Where the paper's own confidence is weakest.** The `_local`/`_gateway` conclusion in §3.4 is
**derived across three sources, none of which states it**. It is the paper's inference, and it is the claim
most worth a critic's attention. The falsifier is concrete: if the `hermes_gateway` adapter or the Hermes
API server transmits provider credentials in any documented path, the conclusion inverts. Nothing fetched
shows that, but the Python was not read.

**(h) When none of this is needed.** If Jarvis stays single-operator, single-machine, with one credential
and no remote edges, **most of §4 is over-engineering**: the capability endpoint (§4.1) describes something
already known, stranded-task detection (§4.5) detects a condition that cannot occur, per-profile auth
(§4.9) has no second profile, and credential pools (§4.6) have one credential. The items that survive that
world are §4.2 (contracts and gates), §4.3 (failure metadata), §4.4 (stall vs liveness), §4.8 (artifacts)
and §4.10 (redaction) — five of twelve. **The other seven are bets on the federated destination being
real.**

## 6. Methodology notes — what was fetched, what was counted, what was not

**(a) Source discipline.** Every Hermes Agent document was fetched as raw markdown from
`raw.githubusercontent.com/NousResearch/hermes-agent/main/...`; every Paperclip document from
`raw.githubusercontent.com/paperclipai/paperclip/master/...`. **Both default branches were confirmed via
the GitHub repo-metadata API before any raw fetch** (`main` and `master` respectively).[^gh-hermes][^prior-art]
Structure came from the GitHub *contents* API; package facts from the npm registry JSON; disambiguation from
the GitHub and HuggingFace metadata APIs. **No rendered HTML page is cited anywhere in this paper.** One
web search was run and was used only to locate candidate URLs.

**(b) Counts are floors, and they were reached by enumeration.** Directory listings were requested as
*enumerations*, never as totals, and counted from the returned list: `website/docs` — 8 entries;
`website/docs/user-guide` — 24; `website/docs/user-guide/features` — 50 entries, of which one is
`_category_.json`, hence **at least 49 feature documents**; `website/docs/reference` — 13;
`website/docs/guides` — 34; `packages/adapters` (Paperclip) — 12 entries, one file and **at least 11
adapter directories**. All are stated as floors because the enumerations passed through a summarizing
retrieval layer and a dropped entry would be invisible.

**(c) One count is explicitly REFUSED.** The npm registry response for
`@paperclipai/hermes-paperclip-adapter` returned a version list ending at `2026.702.0-canary.1` while
`dist-tags.latest` reads `2026.722.0` — **the list is demonstrably incomplete and self-contradicting**.[^npm]
No version count, release cadence, or "first released" date is asserted from it. The only facts taken from
that response are the `description`, `keywords`, `repository.directory`, `license`, and the two `dist-tags`
values.

**(d) Gaps, each with its search method.**
1. **`HERMES_TENANT` semantics — undocumented.** It appears in the kanban lane env table as *"tenant
   namespace, if the task has one"*[^kanban-lanes] and nowhere else in anything fetched. Searched: the five
   directory listings in (b) and the eleven fetched documents. **Not found via those.** Whether Hermes has a
   real tenancy model beyond profiles is therefore **open**, and §3.7 ground 5 is stated conservatively
   because of it.
2. **Kubernetes and host-systemd deployment — no document found.** Method in §3.5.
3. **The OpenClaw lineage — not established.** Method in §1.3.
4. **Any Nous-side acknowledgement of Paperclip — not found.** Method in §1.4.
5. **Behaviour — entirely unverified.** Nothing executed. §8 is the handoff.

**(e) A corroboration for a neighbouring paper, noted not pursued.** Paperclip's `packages/adapters`
listing contains `grok-local` and `cursor-cloud` directories that do **not** appear as rows in
`docs/adapters/overview.md`'s built-in table, alongside `hermes` and a separate `hermes-gateway`
directory — the latter matching the overview's note that *"The older `@paperclipai/adapter-hermes-gateway`
package remains only as a deprecated compatibility shim."*[^pc-adapters] This corroborates
`paperclip_assessment.md`'s decision to state its adapter count as a floor rather than a
total.[^paperclip] **Flagged for that paper's refresh; not pursued here.**

**(f) The residual risk this paper cannot eliminate.** Every raw fetch was requested with an explicit
instruction to reproduce verbatim, and the returns preserved frontmatter, tables, admonitions, code fences
and typographic detail — the signature of a reproduction rather than a summary. **That is strong evidence,
not proof.** A silent elision inside a long returned document would be invisible to the analyst, and the
prior cycle recorded exactly that defect on a first-party source.[^paperclip] A critic re-fetching any
quoted span should expect exact character equality and should treat any divergence as a defect in this
paper, not in the source.

## 7. Verdict

**Test (a) — architecture: REJECTED.** Five grounds, §3.7. Bespoke session-scoped durability that its own
docs decline to call durable execution; a session rather than a workflow as the unit of state; a competing
everything-layer rather than a backbone; a Docker/s6 deployment model whose Kubernetes interaction is a
documented degradation; and a single-host, single-writer storage engine.

**Test (b) — features, interfaces and lessons: TAKE TWELVE.** §4, ranked. Three change design decisions
that are open right now — the capability endpoint (§4.1) is the missing half of the dedicated-edge model;
the five-field contract plus gate-before-judge ordering (§4.2) upgrades a one-field completion contract;
structured failure metadata (§4.3) and progress-vs-liveness (§4.4) are both **sequencing constraints on
`Phase: Temporal Integration`** that must land before workers are written, not after.

**Roadmap action.** `roadmap.md` § *Tools to Evaluate* has no Hermes entry — the name entered this pool
only as a cell in a Paperclip adapter table. **One should be added, and it should be an
already-answered entry**, in the shape the Paperclip item now takes: *architecture rejected on five
grounds, twelve capabilities mined, revalidate in 3 weeks*. Per §7 of the Research Standard this paper does
not write it; a planning run does, after triage.

**One position confirmed, one deflated.** *Confirmed:* the trust-tier table's federated row — *"sends work
over the trunk, holds no edge credential"* — has a shipped implementation in `hermes_gateway`, where the
control boundary moves and the credential boundary does not (§3.4). *Deflated:* subscription-auth at the
edge, already known to be un-unusual after Paperclip, is here **tooled** — a rotation pool that
auto-discovers `~/.claude/.credentials.json`.[^cred-pools] It is infrastructure, not a differentiator, and
this is the second independent confirmation.

## 8. Test plan — what research cannot settle

Each item names the question, the experiment, and what a result would change.

1. **Does `GET /v1/capabilities` actually enumerate what §4.1 needs, or is it a thin flag map?** Install
   Hermes, enable the API server, `curl /v1/capabilities`, `/v1/skills`, `/v1/toolsets`, and diff the real
   payloads against the documented shapes. *Changes:* the fidelity of the capability-manifest design in the
   worker registration contract. **Highest-value experiment in this list** — it is cheap and it feeds a
   decision that must be taken before workers exist.
2. **What actually crosses the wire in `hermes_gateway`?** Run Hermes with the API server on, drive it via
   `POST /v1/runs` from another host, and packet-capture / proxy-log the full request set. *Changes:* §3.4
   and §4.6 invert if any provider credential appears. **This is the falsifier for the paper's weakest
   load-bearing claim** (§5g) and should be run even if nothing else is.
3. **Does the progress-based stall monitor keep a 45-minute `claude -p` run alive?** Configure a Hermes
   lane or delegation wrapping a long agent invocation; observe whether it survives, and what
   `stall_phase` reports when it does not. *Changes:* the `heartbeat_timeout` value and payload for the
   `claude_cli` activity.
4. **Are the timeout/stall metadata fields actually emitted with the documented names and null semantics?**
   Force a `before_first_llm_call` timeout (bad auth) and an `after_llm_calls` timeout (tiny cap on real
   work); capture both payloads. *Changes:* the activity exception taxonomy in §4.3 — if the fields are
   inconsistent, we design ours from scratch rather than mirroring.
5. **Does the kanban dispatcher survive a hard kill mid-claim, and how quickly?** SIGKILL a worker; measure
   time to `crashed`, whether `expected_run_id` fencing rejects the zombie's late terminator, and whether
   the task re-dispatches. *Changes:* whether §4.7's three-terminator contract is worth copying at the
   fidelity described, or only at the vocabulary level.
6. **What is the real cost of the quality-gate memoization?** Run a `/goal` with a failing gate across a
   workspace that does and does not change; verify the git-fingerprint replay actually suppresses the
   re-run. *Changes:* whether §4.2's memoization is a detail or a load-bearing part of the gate design.
7. **Can our bash workflows be wrapped as a kanban lane at all?** Prototype a `spawn_fn` plugin against one
   `build-minor.sh` invocation. *Changes:* whether §5(e)'s interim is real. Expect friction — §5(f) says
   Hermes tried this shape and did not land it.
8. **Does `HERMES_TENANT` do anything?** Set it on a kanban task and inspect the DB and event rows. *Changes:*
   §3.7 ground 5 and the "single-operator-shaped" reading — the one gap that could move the architecture
   verdict rather than merely refine it.
9. **Does Hermes run under k3s at all, and what is lost?** Deploy the image to the target cluster and
   record which supervised services are unavailable. *Changes:* nothing about our own deployment (settled),
   but it is the cheap way to confirm §3.5's degradation is as total as the entrypoint note implies —
   relevant only if §5(e)'s interim is ever pursued.
10. **Does `hermes auth add anthropic --type oauth` work on a Max subscription without extra credits?**
    *Changes:* `anthropic_tos_and_enterprise.md`. The documented parenthetical says it does not; a direct
    test is the only way to know whether that is a current constraint or stale doc text.

---

## Citations

**Hermes Agent — first-party, raw `.md` from `raw.githubusercontent.com/NousResearch/hermes-agent/main/`
(default branch `main` confirmed via the repo metadata API before fetching):**

[^gh-hermes]: GitHub REST API, repo metadata for `NousResearch/hermes-agent` (JSON): `default_branch: "main"`,
  `language: "Python"`, `license.spdx_id: "MIT"`, `stargazers_count: 226385`, `forks_count: 44120`,
  `open_issues_count: 28829`, `created_at: "2025-07-22T22:22:28Z"`, `pushed_at: "2026-08-06T12:06:41Z"`,
  `archived: false`, `homepage: "https://hermes-agent.nousresearch.com"`, description *"The agent that grows
  with you"*, `topics` including `ai-agent`, `claude-code`, `clawdbot`, `hermes-agent`, `moltbot`,
  `nous-research`, `openclaw`. Fetched 2026-08-06.
  https://api.github.com/repos/NousResearch/hermes-agent

[^api-server]: `website/docs/user-guide/features/api-server.md` (raw). Endpoints, `/v1/capabilities` payload,
  runs API, jobs API, sessions API, per-request model selection precedence, `X-Hermes-Session-Key`,
  multi-profile `/p/<profile>/` auth binding and the July-2026 breaking change, concurrent-run cap,
  security warning.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/api-server.md

[^security]: `website/docs/user-guide/security.md` (raw). Eight-layer model, approval modes, hardline
  blocklist, `approvals.deny`, terminal-backend comparison table, env-var passthrough, MCP credential
  filtering and redaction, SSRF protection, `hermes approvals suggest`, write-guard threat-model note.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/security.md

[^cred-pools]: `website/docs/user-guide/features/credential-pools.md` (raw). Rotation strategies, per-error
  cooldowns, auto-discovery table (`~/.claude/.credentials.json`), `hermes auth add anthropic --type oauth`
  with the *"requires Claude Max plan + extra usage credits"* parenthetical, reference-only borrowed
  secrets, `auth.json` storage schema, subagent pool sharing and per-task leasing, prompt-cache warning.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/credential-pools.md

[^kanban-lanes]: `website/docs/user-guide/features/kanban-worker-lanes.md` (raw). Lane contract, assignee
  matching and `skipped_nonspawnable`, env-var table incl. `HERMES_TENANT`, three lifecycle terminators,
  review-required convention, `task_runs` / `task_events`, dispatcher failure modes (claim TTL, PID
  reclaim, `expected_run_id`, `max_runtime_seconds`, `stranded_in_ready`), and the "not yet a paved path"
  statement for external CLI lanes with issue #19931 / PR #19924.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/kanban-worker-lanes.md

[^delegation]: `website/docs/user-guide/features/delegation.md` (raw). `delegate_task` semantics, subagent
  context isolation, durable background completions, the removed wall-clock cap and its rationale,
  timeout metadata triple, stall monitor thresholds and `stalled` metadata quadruple, zero-call diagnostic
  dump, depth limits, blocked-tool list, and the *"Background completion durability is not durable
  execution"* admonition.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/delegation.md

[^goals]: `website/docs/user-guide/features/goals.md` (raw). `/goal` loop, the Goals-vs-Kanban boundary,
  five-field completion contract, `/subgoal`, quality gates incl. gate-before-judge ordering and the
  git-fingerprint memoization, `wait` verdict and its three release conditions, judge JSON schema,
  fail-open semantics, turn budget, `SessionDB.state_meta` persistence, Ralph-loop attribution.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/goals.md

[^sessions]: `website/docs/user-guide/sessions.md` (raw). `state.db` as canonical store, WAL single-writer
  note, schema tables, session-source table, `session_search` over FTS5, gateway session-key formats,
  group isolation defaults, export formats and `--redact` semantics, storage-location table.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/sessions.md

[^heartbeat]: `website/docs/user-guide/features/heartbeat.md` (raw). `/heartbeat` semantics, the
  heartbeat-vs-cron table (*"Yes — fully durable scheduler"*), idle-only injection, tick coalescing,
  `SessionDB.state_meta` persistence.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/heartbeat.md

[^sub-proxy]: `website/docs/user-guide/features/subscription-proxy.md` (raw). API-server-vs-proxy
  comparison table, `hermes portal` storing the refresh token in `~/.hermes/auth.json`, allowed-path
  allowlist, LAN-exposure warning (*"The proxy has no auth of its own"*), pass-through architecture.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/subscription-proxy.md

[^deliverable]: `website/docs/user-guide/features/deliverable-mode.md` (raw). Path-extraction rules,
  extension table, `kanban_complete(..., artifacts=[...])`, the silent-skip rule for missing files, and the
  *"OAuth tokens stay on the user's machine in `auth.json` / `.env`"* comparison note.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/deliverable-mode.md

[^docker]: `website/docs/user-guide/docker.md` (raw). `/opt/data` single-source-of-truth, s6-overlay v3 as
  PID 1, one-container-many-profiles recommendation and its comparison table, per-profile s6 slots and the
  `gateway_state.json` boot reconciler, dashboard auth gate and the *"Why `--insecure` was removed"*
  admonition, the entrypoint dispatcher's non-PID-1 fallback naming Nomad/Kubernetes, the two-container
  data-directory warning, base image and bundled tooling.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/docker.md

[^migrate-openclaw]: `website/docs/guides/migrate-from-openclaw.md` (raw, **first 40 lines only**).
  Frontmatter title/description, `hermes claw migrate`, `~/.openclaw/` / `~/.clawdbot/` / `~/.moltbot/`
  detection, and the pointer to `hermes import-agent` for Claude Code / Codex CLI users. **Cited only for
  the existence of the migration tool; no lineage claim is drawn from it (§1.3).**
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/guides/migrate-from-openclaw.md

**Hermes Agent — directory enumerations (GitHub REST *contents* API, `ref=main`). Requested as
enumerations, counted from the returned lists, cited as floors (§6b):**
`website/docs` (8) · `website/docs/user-guide` (24) · `website/docs/user-guide/features` (50) ·
`website/docs/reference` (13) · `website/docs/guides` (34).
`https://api.github.com/repos/NousResearch/hermes-agent/contents/<path>?ref=main`

**Hermes Agent — root README, REDUCED confidence, not quoted:**
`https://raw.githubusercontent.com/NousResearch/hermes-agent/main/README.md` — the fetch returned a
summarized rendering rather than a reproduction. Nothing in this paper is sourced to it.

**Paperclip — first-party, raw, `master` branch:**

[^pc-adapters]: `docs/adapters/overview.md` (raw). Built-in adapter table incl. both Hermes rows, the
  *"Hermes local vs gateway"* section, the deprecated `@paperclipai/adapter-hermes-gateway` shim note, the
  credential-ownership-for-sandbox-targets table, and the external-plugin table (Droid).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/adapters/overview.md

[^pc-hermes-readme]: `packages/adapters/hermes/README.md` (raw). Names `NousResearch/hermes-agent` by URL;
  `hermes_local` vs `hermes_gateway` selection guidance; prerequisites (`pip install hermes-agent`, Python
  3.10+); eight inference providers; toolset list; gateway startup command and adapter config block; the
  gateway run/stream/stop protocol; the `paperclip-task-bridge` reverse-direction skill and its
  `scope.kind = "task_bridge"` key guidance; the Claude/Codex/Hermes capability table (**marketing —
  §5a; nothing rests on it**).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/adapters/hermes/README.md

[^npm]: npm registry JSON for `@paperclipai/hermes-paperclip-adapter`. Cited for `description`, `keywords`,
  `repository.directory` (`packages/adapters/hermes`), `license` (MIT), `homepage`, and `dist-tags`
  (`latest: 2026.722.0`, `canary: 2026.806.0-canary.7`). **The returned version list is incomplete and no
  count or cadence is asserted from it — §6c.**
  https://registry.npmjs.org/@paperclipai%2Fhermes-paperclip-adapter

**Paperclip — directory enumerations (GitHub REST *contents* API, `ref=master`):**
`docs/adapters` (9) · `packages` (10) · `packages/adapters` (12 entries; **at least 11 adapter
directories**, incl. `hermes`, `hermes-gateway`, `grok-local`, `cursor-cloud` — §6e).

**Disambiguation — negative checks:**

[^gh-fbhermes]: GitHub REST API, repo metadata for `facebook/hermes` (JSON): description *"A JavaScript
  engine optimized for running React Native."*, `default_branch: "static_h"`, `language: "JavaScript"`,
  `license.spdx_id: "MIT"`, `stargazers_count: 11236`, `created_at: "2018-10-22T19:13:00Z"`, `topics: []`.
  https://api.github.com/repos/facebook/hermes

[^hf-hermes4]: HuggingFace model API for `NousResearch/Hermes-4-70B` (JSON): `pipeline_tag:
  "text-generation"`, `library_name: "transformers"`, tags incl. `Llama-3.1`, `function calling`,
  `base_model:meta-llama/Llama-3.1-70B`, `createdAt: "2025-08-18T15:39:17.000Z"`.
  https://huggingface.co/api/models/NousResearch/Hermes-4-70B

**Internal — this repo (non-binding research and architecture docs):**

[^problem-statement]: `docs/standards/architecture/problem-statement.md` — the altitude frame, the
  four-element recipe, the trust-tier table, differentiators #2 and #4, § *The edges* provider-shaped-edge
  stub, and the nearest-neighbour section.
[^system-overview]: `docs/standards/architecture/system-overview.md` — layers, composition and the
  completion contract, the seams table, § *What is not built*, § *Deployment target* (self-hosted Temporal,
  k3s HA, systemd workers, the 10–60 minute `claude -p` figure).
[^paperclip]: `docs/standards/architecture/research/raw/paperclip_assessment.md` (last validated
  2026-08-04, Critic: PASS-WITH-FIXES) — §4.4 process-liveness columns, §4.5 the adapter contract and the
  `testEnvironment` gap, §4.6 credentials at the edge, §5(c) the four-fetch count instability, and the
  adapter floor that named Hermes.
[^edge-routing]: `docs/standards/architecture/research/raw/dedicated_edge_routing.md` — §3.1 bernstein's
  claim/contend protobuf surface and lease semantics, and the [S20] quotations grouping `hermes_local`
  with Paperclip's unsandboxed local CLI adapters.
[^prior-art]: `docs/standards/architecture/research/raw/combination_prior_art.md` — the branch-404
  correction that motivates §6a's default-branch-first discipline, and the adoption comparison baseline.
