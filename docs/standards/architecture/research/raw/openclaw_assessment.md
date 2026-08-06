# OpenClaw — Not an Orchestrator, and That Is the Point

```
Topic:          What is OpenClaw, and — separately — (a) is its architecture right for this edge, and
                (b) what features, interfaces and lessons are worth taking regardless of the answer to (a)?
                Assessed on six axes: durability, domain generality, dispatch/worker model, credential
                locality, deployment shape, trust model.
Feeds:          docs/development/roadmap.md § "Tools to Evaluate" (OpenClaw is ABSENT from the comparator
                set — §7 says what the entry should say); and problem-statement.md § "The nearest neighbor"
                (§3.5 rules on whether that designation still holds) plus § "Where we actually differ" #4
                (§3.2 narrows it again) and its unresolved pinning ruling (§4.1 supplies a shipped answer)
Last validated: 2026-08-06
Revalidate:     high — 3 weeks
Confidence:     DEFINITIVE at the first-party-documentation level for every axis: the load-bearing findings
                (§3.6 trust model, §3.4 credential locality, §3.1 durability, §4.2 maturity taxonomy) come
                from raw first-party markdown under the project's own editorial control, returned as quoted
                spans by the fetch layer. DEFINITIVE for repository metadata and the licence (GitHub JSON
                API; LICENSE returned as a reproduced code block — the only unsummarized whole-file fetch in
                this paper). DERIVED for the architecture verdict (§3.7), for the domain-generality reading
                (§3.2), for the "durability starts at admission" finding (§3.1), for the fourth-coordination-
                shape finding (§3.3) and for every cost estimate (§4, §6) — each names its inputs. UNVERIFIED
                at the behavioural level: no code was read, nothing was installed, nothing was executed. The
                rename history (§1.2) rests on ONE rendered third-party page and is marked unverified except
                for its first datum, which is corroborated first-party. NO COUNT of any directory, tool,
                doc or capability is asserted anywhere in this paper — every enumeration is stated as a
                floor ("at least N named") because contents-API listings are a measured under-enumeration
                surface in this pool (§5(c)). The two numbers that DO appear (repo metadata; "50 surfaces -
                281 capability areas") are quoted from a source, not counted by me.
Critic:         not-yet-verified — 2026-08-06
```

> ## Headline — the comparator set is missing its largest member, and the verdict is MINE HEAVILY, ADOPT NOTHING
>
> **`roadmap.md` § *Tools to Evaluate* does not mention OpenClaw at all.** It lists Paperclip (assessed) and
> the Claude Agent SDK.[^roadmap] Meanwhile OpenClaw carries **385,334 stars** — roughly **five times** the
> 75,610-star project this pool already calls "the largest system in this research pool by two orders of
> magnitude."[^gh-api-openclaw][^paperclip-paper] *(Both figures are quoted JSON fields, not counts I took; the
> ratio is my arithmetic on them — `derived`.)*
> **The comparator set has a hole in it the size of the category's biggest project.** §7 supplies the entry
> text.
>
> **Architecture: reject — but for a reason no prior rejection in this pool has used.** OpenClaw is not a
> rival orchestrator that we judge and decline. **It explicitly refuses to be an orchestrator**, listing among
> its own non-goals *"Agent-hierarchy frameworks (manager-of-managers / nested planner trees) as a default
> architecture"* and *"Heavy orchestration layers that duplicate existing agent and tool
> infrastructure."*[^vision] Its topology is one Gateway per host owning everything, with companion devices as
> *"peripherals, not gateways"*;[^nodes] its durability is SQLite plus boot-time reconciliation, with no
> durable-execution engine documented anywhere in the ~30 first-party docs fetched (§3.1, negative finding
> with method); and its security model is stated as *"one trusted operator boundary per Gateway, not hostile
> multi-tenant isolation inside one shared Gateway."*[^multitenant] **None of that is a backbone for a
> federation of trust domains.** §3 states it and moves on.
>
> **But it is the strongest validating evidence in the pool for two of our positions, and the strongest
> counter-evidence against a third.**
>
> - **Credentials at the edge: shipped, at 385k stars, more literally than we state it.** *"Model calls are
>   proxied back through the Gateway, so provider credentials never leave your machine"*, with *"No standing
>   model, forge, or cloud credentials on the box"*;[^cloudworkers] and to use Claude at all, *"Claude Code
>   itself must be logged in on the same host."*[^clibackends] The paperclip paper already removed
>   *credentials-at-the-edge* from our differentiator list;[^paperclip-paper] **this is the second independent
>   confirmation, and it is more emphatic.**
> - **Trust: the disclaimer is nearly word-for-word the one we already quote from the nearest neighbour.**
>   *"Session ownership, visibility in the sidebar, and presence indicators are usability features, not
>   security boundaries."*[^multiuser] *"Operator scopes … are a control-plane guardrail inside one trusted
>   Gateway operator domain, not hostile multi-tenant isolation."*[^scopes] **Two unrelated projects, both
>   near the top of the category, both stating the same limit in their own docs.** Differentiator #1 is not
>   just intact — it now has a second, larger data point.
> - **Domain generality (differentiator #4) takes its second narrowing, and its replacement is sharper.**
>   OpenClaw is not "sold for code" in any sense — it is *"a personal assistant that is easy to use, supports
>   a wide range of platforms."*[^vision] **But its default result contract is prose:** native sub-agents
>   *"return plain assistant text",*[^subagents] and typed results appear only in an *"experimental"* Swarm /
>   Code Mode path and an optional plugin.[^swarm][^llmtask] **The nearest neighbour generalised its boundary
>   without generalising its product; OpenClaw generalised its product without generalising its boundary.**
>   *(derived — §3.2.)* What survives, and is stronger than what it replaces: **domain-general AND typed at
>   the boundary by default. Nothing in this pool has both.**
>
> **Ten mineable items in §4**, of which **#1 supplies a shipped answer to an open ruling `problem-statement.md`
> admits it has not made** (whether to pin *all* work to a credential-holding machine, or only work with a
> genuine locality requirement — OpenClaw pins the credential and proxies the calls), and **#3 is a
> zero-dependency fix for a gap in this repo's own worktree handling that nothing currently covers.**

---

## 1. Primer — identifying the subject, then grounding it

### 1.1 Disambiguation — two products share this name, and only one is the subject

The dispatch flagged identification as the largest failure risk on this paper, correctly. **A GitHub search API
query for `openclaw`, sorted by stars, returned an items array that I enumerated in full**; two entries carry
the exact name `OpenClaw`, and they are unrelated products.[^gh-search]

| Candidate | What it is | Evidence |
|---|---|---|
| **`openclaw/openclaw`** ← **the subject** | *"Your own personal AI assistant. Any OS. Any Platform. The lobster way. 🦞"*, TypeScript, default branch `main`, homepage `https://openclaw.ai`, created 2025-11-24, pushed 2026-08-06 (the day of this sweep) | first-party GitHub JSON[^gh-api-openclaw] |
| `pjasicek/OpenClaw` | *"Reimplementation of Captain Claw (1997) platformer"*, C++, GPL-3.0, default branch `master`, created 2017-03-08, last pushed 2022-10-24 | first-party GitHub JSON[^gh-api-game] |

**Why `openclaw/openclaw` is the one the dispatch means:** this pool's comparators are agent-orchestration and
AI-assistant systems,[^problem-statement] and `openclaw/openclaw` is an AI assistant. The 1997-platformer
reimplementation shares only the string. It is named here so a reader can see the choice was made, not
skipped. *(Note the default-branch trap this pool has already been burned by: the two repos have **different**
default branches — `main` and `master` respectively. Every raw fetch in this paper used `main`, confirmed from
the JSON before fetching.)*[^gh-api-openclaw][^paperclip-paper]

Adjacent name-collisions found in the same enumeration and explicitly **not** assessed here:
`VoltAgent/awesome-openclaw-skills`, `hesamsheikh/awesome-openclaw-usecases` (community lists *about* the
subject, not alternative products) and `zeroclaw-labs/zeroclaw` (*"Fast, small, and fully autonomous AI
personal assistant infrastructure, any OS"*, Rust — a **different project with a similar name and an
overlapping pitch**, worth its own topic and out of scope here).[^gh-search]

### 1.2 The rename history — recorded, and honestly marked

The project has been renamed repeatedly. **This is the weakest-sourced material in the paper** and is
segregated here so nothing downstream rests on it. A single rendered third-party encyclopedia page lists the
sequence as *"Warelay (original, Nov 24, 2025)"*, *"CLAWDIS (Dec 3, 2025)"*, *"Clawdbot (Jan 2, 2026)"*,
*"Moltbot (Jan 27, 2026)"*, *"OpenClaw (Jan 30, 2026)"*, and attributes it to *"Austrian programmer turned
vibe coder Peter Steinberger"*.[^wikipedia]

- **The first datum is corroborated first-party and definitive:** the repo's `created_at` is
  `"2025-11-24T10:16:47Z"`,[^gh-api-openclaw] which matches *"Nov 24, 2025"* exactly — two structurally
  different sources agreeing.
- **The intermediate names are `unverified`.** *Search method for the negative:* I looked for a first-party
  rename record in the repository root listing (no `HISTORY.md`, no rename doc among the entries enumerated),
  in `docs/announcements/` (which enumerated a single unrelated file, `bluebubbles-imessage.md`), and by
  probing `api.github.com/repos/steipete/clawdbot`, which returned **HTTP 404** — a probe of a *guessed* owner
  path, so it establishes nothing about the rename, only that this particular guess is not a live
  redirect.[^root-contents][^announcements][^404-probe] **No first-party artifact confirming the intermediate
  names was located.** Web-search result summaries naming Forbes, DEV and other outlets were used only to
  *find* candidate sources and are not cited: a search summary is never a source.
- **Nothing in this paper's findings depends on the rename.** It is recorded because the dispatch requires it
  and because a reader encountering "Moltbot" or "Clawdbot" in older material needs the pointer.

### 1.3 Grounding — what it is, and what it is not

**First-party self-description.** *"OpenClaw is the AI that actually does things."* / *"an assistant that can
run real tasks on a real computer."* / *"a personal assistant that is easy to use, supports a wide range of
platforms."*[^vision] The README frames the shape: *"a personal AI assistant that runs on your devices and
meets you in the channels you already use"*, with the Gateway as *"the local control plane for sessions,
tools, events, and channel connections"*, reachable from *"WhatsApp, Telegram, Slack, Discord, Google Chat,
Signal, iMessage, and other messaging services."*[^readme]

**Licence and stewardship.** `LICENSE` is the MIT License, `Copyright (c) 2026 OpenClaw Foundation`, with a
trailing note that *"Third-party notices for incorporated or adapted code are recorded in
THIRD_PARTY_NOTICES.md."*[^license] *(The GitHub API reports `license.spdx_id: "NOASSERTION"` — a detection
artefact of that trailing paragraph, not a licence ambiguity; the file itself is unmodified MIT.
`derived` — inputs: the LICENSE text and the API field.)*[^gh-api-openclaw] The README describes the project
as developed openly by a non-profit foundation; **that characterisation came back as fetch-layer prose rather
than a quoted span and is marked `directional`, not definitive.**[^readme]

**Adoption metadata**, quoted from the repository JSON at 2026-08-06: `stargazers_count: 385334`,
`forks_count: 81008`, `open_issues_count: 5504`, `subscribers_count: 1759`, `language: "TypeScript"`,
`default_branch: "main"`, `pushed_at: "2026-08-06T12:30:34Z"`.[^gh-api-openclaw] Latest release:
`tag_name: "v2026.7.1-2"`, `published_at: "2026-08-04T00:41:26Z"`, `prerelease: false`.[^release] **These are
values I quoted from a JSON object, not enumerations I performed** — the distinction §5(c) turns on.

**Search method for this paper.** GitHub REST *repos* API for metadata, GitHub REST *search/repositories* API
for disambiguation, GitHub REST *contents* API for structure and navigation **only** (never for a count), and
`raw.githubusercontent.com` for every document. At least twenty-five first-party documents were fetched across
`docs/`, `docs/gateway/`, `docs/concepts/`, `docs/tools/`, `docs/automation/`, `docs/nodes/`,
`docs/maturity/`, plus root `LICENSE`, `VISION.md` and `SECURITY.md`. One rendered third-party page was
fetched, for rename history only, and is marked reduced-confidence throughout.

**Quoting discipline, stated because it constrains what this paper may assert.** `LICENSE` was the **only**
file the fetch layer returned as an unsummarized reproduced block. Every other document came back as
fetch-layer prose containing **quoted spans in quotation marks**; every quotation below is one of those spans,
and nothing is quoted that was not returned inside quotation marks. Two separate attempts to obtain
`README.md` as a raw block — including one explicitly demanding a fenced code block, character for character —
both returned summarized prose. **README-sourced claims are therefore held to quoted spans only and are the
lowest-confidence first-party material here.**

**Volatility note (§3 mixed-volatility rule).** The header takes `high — 3 weeks`, one step tighter than the
sibling Paperclip paper's four, for a specific reason: this repo was **pushed on the day of the sweep** and cut
a non-prerelease **two days before it**,[^gh-api-openclaw][^release] so the feature inventory (§2, §4.5–§4.7)
decays fast. The **policy** material — the trust-model disclaimers (§3.6), the security posture (§5), the
maturity taxonomy (§4.2) — is editorial position rather than feature surface and moves far more slowly; a
refresh may re-verify §2 and §4.5–§4.7 first and treat §3.6, §4.2 and §5 as slow-moving.

## 2. The specific model — how OpenClaw actually works

Seven mechanisms, each first-party.

**2.1 One Gateway per host owns everything.** *"A single long-lived **Gateway** owns all messaging surfaces
(WhatsApp via Baileys, Telegram via grammY, Slack, Discord, Signal, iMessage, WebChat)."* /
*"One Gateway per host; it is the only place that opens a WhatsApp session."* Clients connect inward:
*"Control-plane clients (macOS app, CLI, web UI, automations) connect to the Gateway over **WebSocket**"*, and
*"**Nodes** (macOS/iOS/Android/headless) also connect over **WebSocket**, but declare `role: node`."*
Operationally: *"Start: `openclaw gateway` (foreground, logs to stdout)."* / *"Supervision: launchd/systemd for
auto-restart."*[^architecture] Running more than one is possible but discouraged: *"Most setups need one
Gateway - a single Gateway handles multiple messaging connections and agents. Run separate Gateways with
isolated profiles/ports only when you need stronger isolation or redundancy (e.g., a rescue
bot)."*[^multigateway]

**2.2 Agents are personas inside that process, addressed by deterministic binding.** *"Run multiple _isolated_
agents in one Gateway process, each with its own workspace, state directory (`agentDir`), and SQLite-backed
session history, plus multiple channel accounts"*; *"A **binding** maps a channel account (a Slack workspace, a
WhatsApp number, etc.) to one of those agents"*; *"Bindings are deterministic and most-specific
wins."*[^multiagent] The isolation is scoped honestly: *"Direct chats collapse to the agent's main session key
by default, so true isolation requires one agent per person."*[^multiagent]

**2.3 The turn loop is pluggable, and one of the plugs is Claude Code.** *"An **agent runtime** owns one
prepared model loop: it receives the prompt, drives model output, handles native tool calls, and returns the
finished turn to OpenClaw."* At least five are named: `claude-cli`, `codex`, `copilot`, `openclaw`,
`acp`.[^runtimes] Selection is layered — model-scoped policy, then provider-scoped policy, then `auto`, with
fallback to the built-in `openclaw` runtime — and explicit pins **fail closed**: *"Explicit provider/model
plugin runtimes fail closed: `agentRuntime.id: \"codex\"` on a provider or model means Codex, or a clear
selection/runtime error - it is never silently routed back to OpenClaw."*[^runtimes] `claude-cli` is a *CLI
backend* rather than an embedded harness — *"`claude-cli` is not an embedded harness id and must not be passed
to AgentHarness selection"* — and its documented role is narrow: *"OpenClaw can run a local AI CLI as a
text-only fallback when API providers are down, rate-limited, or misbehaving."*[^runtimes][^clibackends]

**2.4 Inbound work is serialized in-process; delivery is persisted.** *"OpenClaw serializes inbound auto-reply
runs (all channels) through a tiny in-process queue"*, which *"enqueues by **session key**"*, drained by
*"A lane-aware FIFO queue … with a configurable concurrency cap"*, with an explicit non-dependency:
*"No external dependencies or background worker threads; pure TypeScript + promises."* Bursts coalesce:
*"Coalesce queued messages into a **single** followup turn after the quiet window."*[^queue] Outbound is a
different story — see §3.1.

**2.5 State is SQLite, per agent and shared.** Credentials go to *"its own credential store
(`agents/<agentId>/agent/openclaw-agent.sqlite`)"*;[^authsem] flow records *"persist in the shared SQLite state
database (~/.openclaw/state/openclaw.sqlite, flow_runs table)"*;[^taskflow] session change events append to
*"the shared state database (`session_state_events`)"* where *"A session's **state version** is simply the
highest sequence number in its log, tracked in a durable per-session head that survives pruning."*[^sessionstate]
Exec approvals *"live in the shared SQLite state database on the execution host."*[^execapprovals]

**2.6 Above single turns sit three loop constructs.** A **goal** is *"one durable objective attached to the
current OpenClaw session"* that *"move[s] with the session key, survive[s] process restarts"* — but it is
deliberately not a driver: *"A goal is not a task queue"*, and *"Only one goal can exist on a session at a
time."*[^goal] **Task Flow** is *"the orchestration layer above background tasks"*, where *"A flow is a durable
record of multi-step work with its own status, JSON state, revision counter, and linked task records"*, with
optimistic concurrency — *"Each write bumps the flow's revision; concurrent writers that pass a stale expected
revision get a conflict and must re-read."*[^taskflow] *(`ClawFlow` is the former name: *"ClawFlow was renamed
to Task Flow"*.)*[^clawflow] **Heartbeat** *"runs **periodic agent turns** in the main session so the model can
surface anything that needs attention without spamming you"*, and is explicitly *not* a task record:
*"Heartbeat is a scheduled main-session turn - it does **not** create background task records."*[^heartbeat]

**2.7 Fan-out exists, and it is where typed results live.** Sub-agents are *"background agent runs spawned from
an existing agent run"*, started with *"the `sessions_spawn` tool"*, bounded by *"Maximum nesting depth is 5
(`maxSpawnDepth` range: 1-5)"* and *"`maxChildrenPerAgent` caps active children per session (default `5`, range
`1-20`)"* — and they report back as prose: *"Native sub-agents do not get the message tool. They return plain
assistant text."*[^subagents] **Swarm** is the typed path, and it is experimental: *"Swarm is an experimental,
opt-in way to orchestrate many sub-agents from a Code Mode script"*, using *"normal JavaScript or TypeScript
control flow such as `Promise.all`, `while`, and `if` to fan out work, collect results, and make decisions"*,
where — the load-bearing sentence — *"Without `schema`, `agents.run()` resolves to the child's final text. With
a JSON Schema, it resolves to the value submitted through the child's `structured_output`
tool."*[^swarm] Code Mode itself is *"an experimental OpenClaw agent-runtime feature"* whose *"`exec` tool
takes a JSON `{ code, language }` payload, executed in a QuickJS-WASI worker."*[^codemode]

## 3. The six axes, the comparative landscape, and Test (a)

### 3.1 Durability — bespoke, SQLite-backed, and it starts at *admission*

**What survives is documented per-subsystem, and the document is unusually good.** `restart-recovery.md`
states the headline — *"Restarting the gateway does not lose agent state."* / *"work that was interrupted
mid-turn is detected and resumed automatically after the gateway comes back up."* — and then enumerates, row by
row, what each subsystem stores and what happens to it on boot: *"Conversation history… Per-agent SQLite
database… Untouched; sessions continue from the stored transcript"*; *"Interrupted main-session turn… Per-agent
SQLite session row and transcript… Automatically resumed or reconciled"*; *"Subagent runs… SQLite (shared state
database)… Registry restored on boot; interrupted runs resumed"*; *"Background tasks… SQLite (shared state
database)… Reconciled on boot; orphaned runs recovered"*; *"Queued outbound deliveries… SQLite delivery queue…
Drained after restart; undelivered replies are retried"*; *"Scheduled (cron) jobs… SQLite cron store… Schedules
persist; the scheduler re-arms on boot."*[^restartrecovery]

**Recovery carries real idempotency discipline**, stated as a rule rather than an implementation note:
*"Every retry reuses one durable dispatch identifier, so an ambiguous connection failure cannot start the same
recovery twice."* Resumption is bounded and honest about what it will not do: *"Recovery never replays a hook
interrupted mid-call."* / *"Recovery completes a delivered receipt without rerunning tools."* / *"the gateway
re-dispatches each marked session with a synthetic system message."* And the failure cases are named:
*"Sessions whose transcript tail cannot be safely continued; these get the resend notice"*; *"Only work that
cannot finish inside the drain budget (or any run interrupted by a forced restart or a crash) is
aborted."*[^restartrecovery]

**The sharp finding is where the durability boundary sits, and it is a design choice we should copy the
*shape* of.** Restart recovery states that *"Work that was never admitted… are rejected with an explicit
restart error"*,[^restartrecovery] and the inbound run queue is described as *"a tiny in-process queue"* with
*"No external dependencies or background worker threads."*[^queue] **Durability therefore begins at admission,
not at arrival: pre-admission inbound work is lost by design, post-admission work is reconciled from SQLite.**
That is not sloppiness — it is a deliberate, cheap, defensible line, and it is exactly the line Temporal draws
between *a signal that was never received* and *a workflow that started*. *(derived — inputs: the two quoted
sources above; no code was read and the boundary was not tested. §8 test-plan item 1.)*

**No durable-execution engine is used. Stated as a negative finding with method.** Across the first-party
documents fetched for this paper — including `agent-runtime-architecture.md` (asked directly about
determinism, replay and durable execution: *"Not stated"*), `concepts/session-state.md`, `gateway/restart-recovery.md`,
`automation/taskflow.md`, `automation/clawflow.md` and `concepts/commitments.md` — **no reference to Temporal,
Cadence, Restate, DBOS, or any durable-execution engine was returned.** The documented mechanism is SQLite plus
boot-time reconciliation plus a durable dispatch identifier.[^runtimearch][^restartrecovery][^taskflow]
This is not a criticism; it is a **price list**, the same way §3.2 of the Paperclip paper is.[^paperclip-paper]
It is also a floor claim, not a proof of absence: the source tree was not read.

**One retired experiment is worth noting for what it says about ambition.** `commitments.md` records
*"The inferred commitments experiment is retired. OpenClaw no longer extracts new conversation follow-ups or
delivers them through heartbeat"*, with *"Previously stored commitments remain in the shared SQLite state
database."*[^commitments] **A shipped project retiring its own follow-up-inference feature is a data point
about how hard "the agent remembers what it owed you" turns out to be in production.**

### 3.2 Domain generality — the mirror image of the nearest neighbour, and it re-narrows differentiator #4

**Positioning: fully general, with no coding front door.** *"OpenClaw is the AI that actually does things"* /
*"a personal assistant that is easy to use, supports a wide range of platforms."*[^vision] The channel surface
is messaging, not a repository;[^readme] the capability surface spans browser control, media understanding and
generation, voice, presence, camera and location.[^tools-listing][^nodes-listing] **Whatever else is true,
"comparable systems are *sold* for code" is false of this one.**

**The result contract at the boundary: prose by default.** Native sub-agents *"return plain assistant
text."*[^subagents] Typing exists but is confined to opt-in, explicitly experimental or optional paths: Swarm's
*"With a JSON Schema, it resolves to the value submitted through the child's `structured_output` tool"* inside
a feature described as *"experimental, opt-in"*;[^swarm] Code Mode, *"an experimental OpenClaw agent-runtime
feature"*, where *"a declared output contract lets the model call and transform a tool result in one
`exec`"*;[^codemode] and `llm-task`, *"a bundled **optional plugin tool** that runs a single JSON-only LLM call
and returns structured output"* with *"Optional JSON Schema the parsed output must validate against."*[^llmtask]
Even the CLI-backend seam is untyped: *"Structured outputs depend on the CLI's own JSON
format."*[^clibackends]

**The derived finding, and it is the most decision-relevant sentence in this paper.**
*(derived — inputs: `vision.md`'s positioning, `subagents.md`'s return contract, `swarm.md`'s and
`code-mode.md`'s experimental markers, `llm-task.md`'s optional-plugin status, and `problem-statement.md`
differentiator #4 with the nearest-neighbour narrowing already recorded there.)*

> The nearest neighbour **generalised its execution boundary without generalising its product**. OpenClaw
> **generalised its product without generalising its execution boundary.** The two largest data points in the
> pool have each solved one half, in opposite directions, and neither ships the pair.

**Consequence for differentiator #4:** the current wording — *"comparable systems are *sold* for code"* — takes
a second hit and should be retired outright, because the largest project in the category is not sold for code
at all. **The replacement is narrower and better evidenced:** *domain-general AND typed at the boundary by
default*. That formulation survives both counter-examples and is checkable. This is a claim-refinement
candidate for the human-ratified path (§6), not something this paper may write.

### 3.3 Dispatch / worker model — a fourth shape

**Within one host: no contention, because there is one owner.** Runs serialize per session key through the
in-process queue with a global parallelism cap: *"OpenClaw already serializes runs per session and caps global
parallelism through the command queue."*[^lanes] Specialist lanes route rather than compete —
*"Parallel specialist lanes let one Gateway route different chats or rooms to different agents while keeping
the user experience fast"* — with a sequencing warning that reads like a scar: *"Do not start here. A
coordinator without lane contracts just coordinates chaos."*[^lanes]

**Across machines, two distinct mechanisms exist, and both are *pinned*, not claimed.**

- **Nodes are capability-declaring, individually addressable peripherals.** *"A node is a companion device
  (macOS/iOS/watchOS/Android/headless) that connects to the Gateway with `role: \"node\"`"*; it advertises what
  it can do — *"The node must declare the command in its authenticated connect metadata
  (`connect.commands`)"* — and work is addressed to one by identity: **"Pin exec to a specific node (id or
  name). Omit to allow any node."** The limit is explicit: *"Nodes are peripherals, not gateways: they don't
  run the gateway service, and channel messages (Telegram, WhatsApp, etc.) land on the gateway, not on
  nodes."*[^nodes]
- **Cloud workers are leased, fenced, throwaway compute.** *"Cloud workers let a session run its agent loop on
  a throwaway cloud machine while everything about the session stays where it always was: visible in the
  sidebar, streaming live, with the transcript owned by the Gateway."* / *"The Gateway leases a box, installs a
  pinned copy of OpenClaw on it, syncs the session's workspace over, and hands the turn loop to a restricted
  `openclaw worker` process."* Ownership is fenced rather than queued: *"Credential rotation and owner-epoch
  fencing guarantee at most one live owner per session — a stale worker that reconnects is fenced, never
  merged"*, and *"While a fenced result is still reconciling, a new turn waits up to 15 seconds for the prior
  claim to release."* Limits are stated: *"Cloud targets are not offered for external CLI session catalogs"*
  and *"Sessions configured for an external CLI runtime such as `claude-cli` cannot dispatch."*[^cloudworkers]

**The comparative table, extended.** The Paperclip paper established that the field has at least three
coordination shapes and that "the common model is central-queue role-pull" overstates it.[^paperclip-paper]
**OpenClaw is a fourth.** *(derived — inputs: §2.1, §2.4, `nodes/index.md`, `cloud-workers.md`, and the prior
paper's table.)*

| Model | Who decides the assignee | Contention | Where the credential is |
|---|---|---|---|
| Central queue + role advertisement (bernstein) | the queue, by role match | real; claim-and-contend[^paperclip-paper] | not established by this paper |
| Manager-agent assignment (Paperclip) | a manager agent, to a named employee | residual — atomic checkout, `409 Conflict`[^paperclip-paper] | adapter-level; may be at the edge[^paperclip-paper] |
| **Single-owner Gateway + pinned peripherals / leased workers (OpenClaw)** | **the Gateway, by node id/name or by leasing a box** | **none by construction — one owner, epoch-fenced**[^cloudworkers][^nodes] | **stays on the Gateway host; calls are proxied**[^cloudworkers] |
| This repo (designed) | the edge's identity — it sees only its own work | none by construction[^problem-statement] | at the edge, by construction[^problem-statement] |

**Why the fourth shape matters to us, and it is not flattering to a position we hold.** OpenClaw achieves
"no contention" the same way we do — by construction rather than by locking — but it gets there with a *central
owner* rather than *distributed identity*. That is a genuinely different route to the same property, and it
costs it the thing we want (many peers in many trust domains) while buying it the thing we have not solved
(a single place that knows the whole picture). **Neither is strictly better; they are duals.**

### 3.4 Credential locality — shipped, emphatic, and the second independent confirmation

- **For CLI backends, the credential must already be on the host.** *"Before OpenClaw can use `claude-cli`,
  Claude Code itself must be logged in on the same host"*, requiring `claude auth login`, and
  *"The gateway service must have the CLI on its `PATH`."*[^clibackends] **This is subscription-auth at the
  edge as a hard prerequisite, not an option.** *(The doc did not state, in the spans returned, whether that
  login is a subscription or an API key — `not stated`, recorded as a gap. For Gemini it does state an API-key
  profile is required.)*[^clibackends]
- **For remote execution, credentials do not travel — the calls do.** *"Model calls are proxied back through
  the Gateway, so provider credentials never leave your machine"*, and *"No standing model, forge, or cloud
  credentials on the box."*[^cloudworkers]
- **Stored credentials are per-agent and local.** *"stored into its own credential store
  (`agents/<agentId>/agent/openclaw-agent.sqlite`)"*, where *"stored credentials are only `api_key`, `token`,
  or `oauth`"*; portability is a flag — *"`api_key` and `token` profiles are portable unless
  `copyToAgents: false`"* — and precedence is stated: *"The stored override wins over `auth.order`
  config."*[^authsem]
- **The secret-handling doc is admirably honest about what it does not buy.** *"For model-provider credentials
  backed by SecretRefs, OpenClaw mints an opaque, process-local sentinel during model-auth resolution"*, and
  then, twice: *"SecretRefs stop credentials from being persisted in config and generated model files, but
  they are not a process-isolation boundary."* / *"Sentinels reduce plaintext exposure across the model-call
  chain, but they are not process isolation."*[^secrets]

**Consequence for our claims.** The Paperclip paper already ruled that subscription-auth-at-the-edge *"is
**not** unusual"* and removed it from the differentiator list.[^paperclip-paper] **This is the second, larger,
and more literal confirmation** — OpenClaw does not merely permit edge credentials, it *requires* them for the
CLI path and *architects around never moving them* for the remote path. Any residual framing of credential
locality as distinctive should be dropped wherever it survives. **This is a win, not a loss:** the affordability
thesis now rests on two independent shipping precedents rather than on a design intention.

### 3.5 Deployment shape — and it is closer to ours than anything else in the pool

**What must be stood up: one long-lived process, supervised, on a host that holds the state.**
*"Start: `openclaw gateway`"*, *"Supervision: launchd/systemd for auto-restart"*, *"One Gateway per
host."*[^architecture] On a server: *"The Gateway runs on the VPS and owns state + workspace"*, with
*"Treat the VPS as the source of truth and back up the state + workspace regularly"* and a governance warning
— *"Before you install OpenClaw on a public VPS, decide how you want to administer the box itself."*[^vps]
Install paths are per-OS installers or npm on Node 22.22.3+.[^readme]

**Container and cluster support exist but are not the recommended path.** The maturity scorecard records
*"Docker and Podman hosting"* at **Beta** and *"Kubernetes hosting"* at **Alpha**, against a taxonomy in which
Beta means *"Public path exists and the main workflow is usable with bounded caveats"* and Alpha means
*"Real users can try it, but breaking changes and incomplete UX are expected."*[^scorecard][^taxonomy]

**The structural echo of our own deployment decision.** `system-overview.md` § *Deployment target* settles on
**systemd workers on the machine holding the repo and the credential**, with Kubernetes reserved for the server
tier.[^system-overview] **OpenClaw independently converged on the same primitive** — a supervised long-lived
process on the credential-holding host, with k8s as the immature edge of the story rather than the centre.
*(derived — inputs: `architecture.md`, `vps.md`, the scorecard rows above, and `system-overview.md`.)* This is
corroboration of a settled decision, not a reason to revisit it.

### 3.6 Trust model — one operator per Gateway, stated repeatedly and without hedging

**This is the axis where OpenClaw's documentation is strongest, and it lands squarely on differentiator #1.**

`SECURITY.md` enumerates the trusted computing base explicitly: *"OpenClaw is local-first agent infrastructure
for trusted operators; it is not designed as a shared multi-tenant boundary between adversarial users on one
gateway."* / *"Authenticated Gateway callers are treated as trusted operators for that gateway instance."* /
*"The host where OpenClaw runs is within a trusted OS/admin boundary."* / *"Anyone who can modify `~/.openclaw`
state/config (including `openclaw.json`) is effectively a trusted operator."* / *"Plugins/extensions are part
of OpenClaw's trusted computing base for a gateway."* And one line that should be read twice, because it is a
principle rather than a limitation: ***"The model/agent is **not** a trusted principal."***[^security]

Multi-user mode is a *usability* feature by its own account: *"Multi-user mode lets several trusted people
operate the same OpenClaw agent"*; *"Everyone who can operate an agent can make it do anything that agent can
do"*; *"Session ownership, visibility in the sidebar, and presence indicators are usability features, not
security boundaries"*; *"If people must not access each other's sessions, tools, credentials, or files, give
them separate agents or separate gateway/host trust boundaries."*[^multiuser] Operator scopes — at least eight
named (`operator.read`, `operator.write`, `operator.admin`, `operator.pairing`, `operator.approvals`,
`operator.questions`, `operator.talk`, `operator.talk.secrets`) — are enforced per RPC (*"Each Gateway RPC has
a least-privilege method scope that decides whether a request reaches its handler"*) and are disclaimed in the
same breath: *"They are a control-plane guardrail inside one trusted Gateway operator domain, not hostile
multi-tenant isolation"* and *"`operator.read` is not a per-user or hostile multi-tenant privacy
boundary."*[^scopes]

**Multi-tenancy, where it exists, is achieved by replication rather than by isolation.** *"OpenClaw's default
security model is one trusted operator boundary per Gateway, not hostile multi-tenant isolation inside one
shared Gateway."* / *"Hosting users or organizations that do not share a trust boundary therefore means running
a separate complete OpenClaw instance for each tenant."* / *"Use one cell per tenant so each trust domain has a
separate Gateway process, container, persistent state tree, and Gateway credential."* / *"No rung in this
ladder changes the OpenClaw application trust model: one Gateway remains one trusted operator domain."* The
residual trust is named rather than hidden: *"The Fleet operator and the host are trusted by every tenant.
Resistance to a compromised host is a non-goal."*[^multitenant]

**Consequence for differentiator #1 — it strengthens.** `problem-statement.md` currently rests this claim on
one first-party quotation from the nearest neighbour.[^problem-statement] **A second project, far larger by
adoption and in a different product category, states the same limit in its own docs, across four separate
files** (`SECURITY.md`, `multi-user.md`, `operator-scopes.md`, `multi-tenant-hosting.md`).
Cross-operator, cross-trust-domain federation is outside the shipped scope
of *both* of the pool's largest comparators, by their own documentation. That is no longer one project's
choice; it is a pattern.

**For the sibling identity/trust paper this cycle, three things here are worth mining and are deliberately
not developed further in this paper:** (i) node pairing uses a signed device identity verified **out of band** —
*"A node presents a signed device identity during connect; the Gateway creates a device pairing request"*, and
approval *"connects back to the pairing host (`BatchMode`, `StrictHostKeyChecking=yes`), runs `openclaw node
identity --json` there, and approves only when the remote device id and public key match the pending request
exactly"*; (ii) revocation is specified, not implied — *"`node.pair.remove` … revokes the device's `node` role
in the paired-device store, drops the approved node surface with it, and invalidates/disconnects that device's
node-role sessions"*; (iii) the honest residual — *"Node pairing approval records the trusted capability
surface. It does **not** pin the live node command surface per node"*, and *"Commands queued before pairing
approval are dropped, not deferred."*[^pairing]

### 3.7 Test (a) — is its architecture right for us? **No, and it agrees.**

Four reasons, stated briefly because the answer is not close.

**(a1) It declines the job.** `VISION.md` lists among explicit non-goals *"Agent-hierarchy frameworks
(manager-of-managers / nested planner trees) as a default architecture"* and *"Heavy orchestration layers that
duplicate existing agent and tool infrastructure."*[^vision] **Adopting OpenClaw as a backbone would mean
building, on top of it, the exact layer its stewards have committed not to build.** Every such layer would be
downstream of a project that will not maintain the seam it needs. *(derived — inputs: `VISION.md` non-goals;
`system-overview.md`'s composition model.)*

**(a2) The topology is centre-and-peripherals; ours is peers.** *"One Gateway per host"*, and nodes are
*"peripherals, not gateways"* that *"don't run the gateway service."*[^architecture][^nodes] The problem
statement's edge is *"a machine with a capability and a credential, running a worker that speaks the backbone's
protocol"*[^problem-statement] — a peer, not a peripheral. A node cannot host an edge's workflows; by
definition it hosts commands the Gateway sends it.

**(a3) Durability is bespoke and stops at admission.** §3.1. Ours comes from Temporal, self-hosted, with
determinism and replay.[^system-overview] Layering Temporal *under* a Gateway that already owns reconciliation
would produce two recovery authorities disagreeing about the same run.

**(a4) The trust unit is one operator per Gateway, and scaling it means N whole instances.** §3.6. The
federated destination is three trust tiers with distinct operators; *"one cell per tenant"* is a valid answer
to a different question.[^multitenant][^problem-statement]

> **Verdict on (a): do not adopt, and do not build on. Nothing in §4 depends on this verdict** — which is the
> entire reason the two tests are separated.

### 3.8 Does "the nearest neighbour" designation still hold? **Yes — but the word "nearest" now needs an axis.**

*(derived — inputs: `problem-statement.md` § *The nearest neighbor*; §3.1–§3.7 above; the Paperclip
paper.)*[^problem-statement][^paperclip-paper]

| Sense of "nearest" | Which project | Why |
|---|---|---|
| **By architecture** (deterministic orchestrator, no model in the coordination loop, per-task worktrees, typed completion contracts, checkpoint/resume) | **bernstein** — designation **holds** | OpenClaw explicitly refuses this role (§3.7 a1); Paperclip's ontology is an org chart[^paperclip-paper] |
| **By thesis** (credential at the edge, domain-general assistant, your own machines, supervised long-lived process) | **OpenClaw** | §3.4, §3.2, §3.5 — it is closer to *what we are arguing for* than to *what we are building* |
| **By adoption** | **OpenClaw**, by a wide margin over the previously-largest datum | 385,334 vs 75,610 quoted stars[^gh-api-openclaw][^paperclip-paper] |

**Recommendation (claim-refinement candidate, §6):** `problem-statement.md` should keep bernstein as the
architectural nearest neighbour and **name OpenClaw as the thesis-nearest neighbour**, because two of that
document's four differentiators are now most sharply tested by OpenClaw rather than by bernstein. A reader who
only knows bernstein will over-rate differentiators #1 and #4.

## 4. Test (b) — what to take. Ten items, ranked, each with a cost.

Ranking is by *value to the federated destination × plannability*. **Cost figures are `derived` throughout and
name their inputs.**

### 4.1 — The credential-proxy alternative to pinning `RANK 1`

**What it is.** Instead of moving work to the machine that holds the credential, OpenClaw keeps the credential
still and moves the *model call*: *"Model calls are proxied back through the Gateway, so provider credentials
never leave your machine"*, with *"No standing model, forge, or cloud credentials on the box"*, while the agent
loop itself runs on *"a throwaway cloud machine"* whose workspace was synced in.[^cloudworkers] Ownership is
kept single by *"owner-epoch fencing"* rather than by a lock.[^cloudworkers]

**Why it matters — it answers an open ruling we have written down and not made.**
`problem-statement.md` records, under *One honest cost of claim #2, unresolved*: the design *"currently gives up
cross-machine failover for *all* work, not only work with a genuine locality requirement"*, and calls pinning a
credential-free workflow *"overshoot, not principle"* with *"the ruling … open."*[^problem-statement]
**OpenClaw ships the third option that ruling is missing.** The taxonomy becomes:

| Work has… | Placement | Failover |
|---|---|---|
| a local repo AND a credential requirement | pinned edge (today's design) | none — accepted |
| a credential requirement only | **any worker + credential proxy back to the credential holder** | **retained** |
| neither | shared queue (Temporal's own two-tier pattern) | retained |

**The caveat is honest and must travel with the item:** proxying is not free — it puts the credential holder in
the latency path of every model call, and OpenClaw itself excludes the CLI runtimes from this mode
(*"Sessions configured for an external CLI runtime such as `claude-cli` cannot dispatch"*),[^cloudworkers]
**which is exactly the runtime this repo uses.** So the pattern generalises to API-keyed work and *not* to
`claude -p` runs on a subscription. That narrowing is itself the finding: it explains *why* the pinned design
is right for our current workload and bounds where it stops being right.

**Cost.** *(derived — inputs: `cloud-workers.md`; `problem-statement.md`'s open ruling; `system-overview.md`'s
deployment target.)* **Zero to state the ruling; the ruling is the deliverable.** Implementing a proxy tier is
out of scope until a second edge exists and would require the not-built server tier.[^system-overview]

### 4.2 — The maturity scorecard and its promotion criteria `RANK 2`

**What it is.** A published, six-level readiness taxonomy with explicit promotion gates, applied across the
whole product surface. The levels, verbatim: **M0 - Planned:** *"Direction is known, but no supported user path
exists."* **M1 - Experimental:** *"Implemented behind caveats, flags, source builds, or maintainer-only
flows."* **M2 - Alpha:** *"Real users can try it, but breaking changes and incomplete UX are expected."*
**M3 - Beta:** *"Public path exists and the main workflow is usable with bounded caveats."* **M4 - Stable:**
*"Recommended path for normal users. Failures are treated as regressions."* **M5 - Clawesome:** *"Polished,
delightful, well-instrumented, and competitive with the best comparable workflow."*[^taxonomy]

The **gates** are the mineable part, because they are evidence requirements rather than opinions:
**M0→M1** *"Design issue, owner, and target surface exist."*; **M1→M2** *"Maintainer can run the scenario from
current main."*; **M2→M3** *"Documented setup, basic tests, known caveats, and at least one real-environment
proof."*; **M3→M4** *"Install/update docs, regression tests, support runbook, and successful scenario proof
across the expected environment."*; **M4→M5** *"Stable plus user scorecard pass across representative
users."*[^taxonomy]

And the governing rule, which is the single best sentence in OpenClaw's documentation for our purposes:
***"Coverage is deliberately evidence-led: an area does not become 'ready' just because the implementation
exists."***[^scorecard] The scorecard describes its own scope as *"release readiness scores for product areas,
integrations, and supported workflows"* covering *"50 surfaces - 281 capability areas - deterministic coverage
plus human-reviewed quality and completeness."* *(That figure is **quoted from the document**, not counted by
me — the §5(c) distinction.)*[^scorecard]

**Why it matters here.** This repo's roadmap marks phases complete with checkboxes and prose; there is no
readiness bar, no promotion gate, and no distinction between *"the code exists"* and *"an operator other than
the author can run this."* In a fabric of edges built by the first edge,[^problem-statement] **"is this edge
ready for someone else to run?" is the question that decides whether edge #2 costs less than edge #1** — and
nothing currently asks it. Note also that OpenClaw's own scorecard rates *"Security, auth, pairing, and
secrets"* at Beta and *"Kubernetes hosting"* at Alpha:[^scorecard] **a project willing to publish that about
itself is producing a more useful artifact than one that publishes only successes.**

**Cost.** *(derived — inputs: `taxonomy.md`'s six definitions and five gates; this repo's roadmap and phase-doc
conventions.)* **~1 day to adopt the taxonomy** as a standards amendment plus a per-phase readiness line;
**recurring hours per phase** thereafter. Dependencies: none. **The gates transfer nearly verbatim** — only M5's
"representative users" needs restating for a single-operator system.

### 4.3 — The lossless worktree-reaping rule `RANK 3`

**What it is.** OpenClaw gives agent tasks git worktrees and specifies exactly when it may destroy one:
*"Managed worktrees give an agent task its own git branch and checkout without placing temporary directories
inside the source repository"*; *"OpenClaw creates them under its state directory, records them in the shared
state database, and snapshots their tracked and non-ignored untracked contents before removal"*; and the guard
itself — ***"At run end, it removes a worktree only when `git status --porcelain` is empty and
`git log HEAD --not --remotes --oneline` finds no unpushed commits."*** Idle cleanup is separate and explicitly
more aggressive: *"Hourly cleanup snapshots and removes unlocked Workboard- and session-owned worktrees idle
for more than 7 days, even when dirty."* Deletion of the owning session is likewise conditional:
*"Deleting the session removes the worktree only when doing so is lossless."*[^worktrees]

**Why it matters here — this is the one item with a live gap and no dependencies.** Every autonomous dispatch
in this repo runs in an isolated git worktree,[^system-overview] and the two-condition guard above
(**clean tree AND no unpushed commits**, plus *snapshot before removal*) is precisely the rule that prevents an
autonomous run's uncommitted or unpushed work from being silently destroyed by cleanup. **The second condition
is the non-obvious one:** a worktree can be perfectly clean and still hold the only copy of a commit. A
cleanup that checks only `git status` deletes it.

**Cost.** *(derived — inputs: `managed-worktrees.md`; this repo's worktree-per-dispatch model.)* **Hours.**
Two shell conditions plus a snapshot step in whatever reaps worktrees, and a one-line rule in the workflow
standard. **No dependency on the Temporal port.** The `> 7 days idle, even when dirty` escape hatch should be
adopted with it — without a time-boxed override, the safety condition becomes a disk leak.

### 4.4 — The per-subsystem restart-recovery contract, as a documentation shape `RANK 4`

**What it is.** Not a feature — an artifact. `restart-recovery.md` answers, for each subsystem, three columns:
*what state exists*, *where it is stored*, and *what happens to it on boot*. Rows quoted in §3.1 cover
conversation history, interrupted main-session turns, subagent runs, background tasks, queued outbound
deliveries and cron schedules.[^restartrecovery] Alongside it sit three rules worth taking as rules:
*"Every retry reuses one durable dispatch identifier, so an ambiguous connection failure cannot start the same
recovery twice"*; *"Recovery never replays a hook interrupted mid-call"*; *"Recovery completes a delivered
receipt without rerunning tools."*[^restartrecovery]

**Why it matters here.** `Phase: Temporal Integration` will produce exactly this set of questions and has no
place to answer them. **A worker/activity design that cannot fill in this table is not finished**, and the
table is cheap to fill *before* the code exists and expensive to reconstruct after. The first rule
(one durable dispatch identifier per retry) is Temporal's workflow-ID-reuse policy stated in product terms;
the second and third are the *"is this side effect replayable?"* audit that the activity/workflow seam in
`system-overview.md` already assumes but does not enumerate.[^system-overview]

**Cost.** *(derived — inputs: `restart-recovery.md`'s structure; `system-overview.md`'s seam table.)*
**Hours of writing, high leverage, and it must land before workers are written** — it is a design artifact,
not a build item. Dependency: `Phase: Temporal Integration`.

### 4.5 — Typed child results: `structured_output` + JSON Schema `RANK 5`

**What it is.** The recipe's element #3 — *typed memory between steps*[^problem-statement] — shipped, and with
the untyped default sitting right beside it for contrast: *"Without `schema`, `agents.run()` resolves to the
child's final text. With a JSON Schema, it resolves to the value submitted through the child's
`structured_output` tool."*[^swarm] The parent then branches **in code, with no model in the loop**:
*"Use normal JavaScript or TypeScript control flow such as `Promise.all`, `while`, and `if` to fan out work,
collect results, and make decisions."*[^swarm] The same pattern appears in the optional `llm-task` plugin:
*"Optional JSON Schema the parsed output must validate against."*[^llmtask]

**Why it matters here.** `system-overview.md` § *What is not built* names *"typed handoff between runs — a
parent still routes on a parsed token rather than a structured result."*[^system-overview] **This is a shipped
reference implementation of the fix**, including the two design choices we will have to make: (i) schema is
*per-call*, not per-agent — the caller declares the contract, not the callee; (ii) the untyped path remains
available, so typing is opt-in rather than mandatory. **Both are worth arguing about before we copy them** —
a backbone that only sometimes returns typed results reproduces the parsed-token problem for the other half.

**Cost.** *(derived — inputs: `swarm.md`; `llm-task.md`; `system-overview.md`'s not-built list.)*
**Zero as reference; ~1 day as a design input** to the activity result-type decision in
`Phase: Temporal Integration`. **Caveat that must travel with it:** Swarm is *"experimental, opt-in"* and
*"Swarm v1 runs one-shot collector children"*[^swarm] — mine the contract, not the maturity.

### 4.6 — Capability declaration plus explicit pinning, with its honest residual `RANK 6`

**What it is.** A node declares what it can do at connect time — *"The node must declare the command in its
authenticated connect metadata (`connect.commands`)"* — and the caller may pin or not:
*"Pin exec to a specific node (id or name). Omit to allow any node."*[^nodes] Approval of the declared surface
is a separate gate: *"Node capability approval (`node.pair.*`) gates which declared capabilities/commands a
connected node may expose."*[^pairing]

**Why it matters here.** The Paperclip paper identified `testEnvironment` as *the capability-advertisement
primitive a dedicated-edge model needs*.[^paperclip-paper] **OpenClaw supplies the other half of that
primitive**: not "can this runtime do the job" (a preflight probe) but "what does this machine claim it can do,
and has an operator approved that claim" (a declared, approved, revocable surface). An edge model needs
**both** — a claim, an approval, and a probe that the claim is currently true. And OpenClaw names the gap in
its own design, which is the most valuable part: *"Node pairing approval records the trusted capability
surface. It does **not** pin the live node command surface per node."*[^pairing] **The approved set and the
live set can drift, and they know it.** Any capability registry we build inherits that problem on day one.

**Cost.** *(derived — inputs: `nodes/index.md`, `pairing.md`, and the Paperclip paper's `testEnvironment`
finding.)* **Small design, ~1–2 days**, and it is an *interface* decision that must be taken alongside the
Temporal worker registration contract. Dependency: `Phase: Temporal Integration`, worker startup.

### 4.7 — Loop detection for unattended runs `RANK 7`

**What it is.** A guard against agents that are alive, busy, and going nowhere. It sets out to
*"Detect repetitive sequences that make no progress"*, *"Detect high-frequency no-result loops (same tool, same
inputs, repeated errors)"*, and *"Break context-overflow -> compaction -> same-loop cycles instead of letting
them run indefinitely."* Escalation is graduated: *"Warnings come first. Blocking follows once a pattern
persists past the warning threshold"*; *"the first critical loop blocks the whole tool batch before any tool in
that batch runs"*, after which the model *"can answer, ask a question, or continue with a different tool or
different arguments"*, and *"Another critical loop in the same run blocks its whole batch and ends the run."*
The discriminator is byte-equality, stated as a deliberate conservatism: ***"The guard never aborts while
results are changing; only byte-identical results across the window trigger it."***[^loopdetect]

**Why it matters here.** The Paperclip paper's §4.4 supplies the *stalled* predicate (not running AND not
waiting AND not being recovered).[^paperclip-paper] **This is its complement: the *looping* predicate**, which
fires on work that is emphatically running and producing output. A liveness heartbeat cannot see it; a stalled
detector cannot see it. Our `HOLD(redispatch)` guard bounds loop-backs at the *parent* level once, and nothing
observes repetition *within* a run.[^system-overview] **The byte-identical rule is the transferable insight:**
it makes the detector conservative by construction, which is what keeps a false-positive from killing a
legitimately slow run.

**Cost.** *(derived — inputs: `loop-detection.md`; this repo's parent/child composition model.)*
**Small-to-medium, ~2–3 days** for a result-hash window in the activity layer; the *rule* is hours.
Dependency: best landed with the `claude_cli` activity design. **Note the gap:** exact thresholds were
`not stated` in the spans returned — the mechanism transfers, the tuning does not.[^loopdetect]

### 4.8 — The tenant "cell": trust separation by replication `RANK 8`

**What it is.** A documented ladder for hosting mutually-untrusting tenants on one machine *without* claiming
in-process isolation: *"Use one cell per tenant so each trust domain has a separate Gateway process, container,
persistent state tree, and Gateway credential"*; *"Each cell runs the official `ghcr.io/openclaw/openclaw`
image on its own user-defined bridge network"*; *"The runtime publishes it only to
`127.0.0.1:<allocated-port>` on the host"*; *"Fleet drops all Linux capabilities, enables `no-new-privileges`,
applies PID, memory, CPU, and optional writable-layer disk limits."* And the non-goals are named:
*"Fleet does not provide a shared channel account or inbound message router"*; *"Fleet does not proxy tenant
messages and does not add a shared application-level data path between cells"*; *"The Fleet operator and the
host are trusted by every tenant. Resistance to a compromised host is a non-goal."*[^multitenant]

**Why it matters here.** SkyyCommand will eventually face the same question — several trust domains, one MDC —
and this is a shipped, costed answer that does **not** require the application to become multi-tenant. **The
transferable rule** *(derived — inputs: `multi-tenant-hosting.md`, `problem-statement.md`'s three tiers)*:
*when the application's trust unit is smaller than the deployment's, replicate the application rather than
subdivide it, and state in writing what the shared host still implies.* The last clause is the discipline —
their ladder explicitly refuses to claim a property it does not have.

**Cost.** **Zero here; this is reference material for SkyyCommand**, which owns the deployment decision.[^system-overview]
Recorded so the edge does not invent a worse answer.

### 4.9 — A threat model that names its trusted computing base and its non-vulnerabilities `RANK 9`

**What it is.** `SECURITY.md` enumerates who is trusted (§3.6) and, unusually, what will be *rejected* as a
report: *"Prompt-injection-only attacks (without a policy/auth/sandbox boundary bypass)"* and
*"Reports whose only claim is use of an explicit trusted-operator control surface … without demonstrating an
auth, policy, allowlist, approval, or sandbox bypass."* The governing formulation:
*"Security boundaries come from host/config trust, auth, tool policy, sandboxing, and exec approvals"*, so
*"Prompt injection by itself is not a vulnerability report unless it crosses one of those boundaries"* — while
still instructing *"Assume prompt/content injection can manipulate behavior."*[^security] The sandbox doc
carries the same honesty: *"Sandboxing is off by default"*, and *"This is not a perfect security boundary, but
it materially limits filesystem and process access when the model does something dumb."*[^sandboxing]

**Why it matters here.** This repo runs autonomous dispatches with `--dangerously-skip-permissions`, where
*"the `PreToolUse` hook is **the only control operating during a run**."*[^system-overview] **We have a
control; we do not have a written statement of what it is and is not a boundary against.** OpenClaw's shape —
*enumerate the TCB, name the boundaries, declare what is not a vulnerability* — is directly transferable and
would make `block-dangerous.sh`'s scope arguable instead of assumed.

**Cost.** *(derived — inputs: `SECURITY.md`, `sandboxing.md`, `system-overview.md` § Safety.)*
**~1 day** for a threat-model section in the architecture docs. Dependency: none. **Governance note:** this
would be a *standards* artifact and therefore a human-ratified candidate, not something a research or build run
may author.[^research-standard]

### 4.10 — `VISION.md` as a governance artifact: a published non-goals list `RANK 10`

**What it is.** A first-party document whose most useful content is what the project **will not** do:
*"New core skills when they can live on ClawHub"*; *"Commercial service integrations that do not clearly fit
the model-provider category"*; *"Wrapper channels around already supported channels without a clear
capability"*; *"Agent-hierarchy frameworks (manager-of-managers / nested planner trees) as a default
architecture"*; *"Heavy orchestration layers that duplicate existing agent and tool
infrastructure."*[^vision]

**Why it matters here.** §3.7(a1) shows the practical value: **a competitor's non-goals list settled our
adoption question in one sentence, faster than any feature comparison could.** Our own `problem-statement.md`
does the positive half well and has no published negative half; adding one would let a downstream planner rule
out a direction without escalating. **This is the cheapest item on the list and the easiest to skip.**

**Cost.** **Hours**, as a section in `problem-statement.md` through the human-ratified path. Dependency: none.

## 5. Honest boundary analysis — the case against this paper

**(a) Documentation only. No code was read, nothing was installed, nothing was executed.** Every behavioural
claim in §3.1 (recovery), §3.3 (fencing), §3.4 (credentials never leaving the machine) and §4.7 (loop
detection) is a claim the project makes about itself. A documented fencing guarantee is not a tested one, and
*"provider credentials never leave your machine"* is precisely the kind of statement that deserves a packet
capture rather than a citation. **This is the single largest weakness**; §8 items 1–4 are its direct tests.

**(b) The fetch layer summarized nearly everything, and the strongest source class in this pool was
unavailable.** The Paperclip paper's load-bearing findings came from raw SQL and schema files returned as
reproduced blocks.[^paperclip-paper] **Here, exactly one file — `LICENSE` — came back as a reproduced block.**
Everything else arrived as fetch-layer prose containing quoted spans. Two explicit attempts to obtain
`README.md` verbatim, one demanding a fenced code block character-for-character, both returned summaries.
Consequences, stated plainly:

1. **Every quotation in this paper is a span the fetch layer placed inside quotation marks.** That satisfies the
   Research Standard's verbatim rule as this pool has applied it,[^research-standard][^paperclip-paper] but it
   is a weaker guarantee than a reproduced block, because the *selection* of what to quote passed through a
   summarizing model.
2. **The known elision failure mode applies with full force.** The Paperclip paper measured that summarizing
   fetches drop whole statements while leaving well-formed text behind.[^paperclip-paper] A dropped clause in,
   say, the `restart-recovery` row for background tasks would be undetectable here — **there is no second
   structural signal to check it against**, because I have no schema files or migrations for this project.
3. **README-sourced claims are the weakest** and are used only for the product framing in §1.3.

**(c) No count of anything is asserted, and that is deliberate.** Contents-API listings were used for
navigation only. This pool has measured the under-enumeration failure three times across two codebases —
seven fetches, seven totals, `truncated: false` every time.[^paperclip-paper] Accordingly: the runtime list
(§2.3) is *"at least five named"*; the operator-scope list (§3.6) is *"at least eight named"*; the channel list
is a floor; and **no directory in this repository is given a size.** The two numbers that do appear —
repository metadata (§1.3) and *"50 surfaces - 281 capability areas"* (§4.2) — are **values quoted from a
source**, not enumerations I performed. *The tell, per the prior paper: did I count, or did I quote?* I quoted.

**(d) One document did not say what its filename implied, and that is a warning about the rest.**
`concepts/delegate-architecture.md` was fetched expecting parent→child dispatch semantics; the spans returned
concern *organizational* delegation (agents acting on behalf of humans, tiered approval rules), and the fetch
answered *"not stated"* to every dispatch question asked of it.[^delegate] **So this paper's account of
fan-out rests on `subagents.md` and `swarm.md` alone**, and any claim of absence about OpenClaw's dispatch
model is scoped to those two files plus `nodes/index.md`, `cloud-workers.md`, `queue.md` and
`parallel-specialist-lanes.md`. It is not a claim about the codebase.

**(e) 385,334 stars is a popularity signal, not a production-validation signal — and the asymmetry is worse
here than for Paperclip.** OpenClaw is a *consumer-facing personal assistant* reached through mainstream
messaging apps;[^readme] its star count therefore reflects attention from a far broader population than an
orchestration platform's does, and says correspondingly less about production use in our category.
**The project's own scorecard is the better evidence, and it is more modest than the star count**:
*"Agent Runtime"* at Beta, *"Security, auth, pairing, and secrets"* at Beta, *"Kubernetes hosting"* at Alpha,
against a scale where Beta means *"bounded caveats"* and Alpha means *"breaking changes and incomplete UX are
expected."*[^scorecard][^taxonomy] **Consequence for this paper: lessons mined from its stated DESIGN RULES
(§4.2, §4.3, §4.4, §4.7, §4.9) are load-bearing; lessons mined from its FEATURE CLAIMS (§4.1, §4.5, §4.6) are
weaker, because the features are Beta or explicitly experimental.**

**(f) A measurement caveat inside §4.2 that I could not resolve.** The scorecard fetch returned per-area
levels, but its **grouping was internally inconsistent** — several rows appeared under a *"Beta (M3)"* heading
while carrying the value *"Stable"*. I therefore cite **individual area→level pairs** (*"Kubernetes hosting"* -
Alpha; *"Security, auth, pairing, and secrets"* - Beta; *"Agent Runtime"* - Beta; *"Docker and Podman
hosting"* - Beta) and **assert no distribution, no per-level count, and no claim about the scorecard's overall
shape.** A reader wanting the full picture must fetch the file.[^scorecard]

**(g) The case against my own §3.7 verdict.** Two objections are available and I do not think either wins,
but they are real. **First:** OpenClaw's *node* concept is closer to our *edge* than anything else in the pool
— capability-declaring, individually addressable, cryptographically paired, revocable.[^nodes][^pairing] A
reviewer could argue we should adopt the node protocol and treat the Gateway as one edge among many rather than
as the centre. The counter is (a2): nodes *"don't run the gateway service"*, so a node cannot host workflows —
adopting the protocol without the peer property gets the vocabulary and not the topology. **Second:** the
per-tenant *cell* pattern (§4.8) is arguably a legitimate route to federation — N gateways, one per trust
domain, coordinated above. The counter is that OpenClaw explicitly declines to build that coordination layer
(*"Fleet does not proxy tenant messages and does not add a shared application-level data path between
cells"*),[^multitenant] so we would be building the interesting part ourselves on someone else's non-goal.
**A reviewer is entitled to push back on both.**

**(h) Rename volatility is a live risk to this paper's own identifiers.** A project that changed names at least
twice in four days (§1.2, unverified) may do so again, and every raw URL in §9 is name-bound. **A refresh that
finds 404s on `raw.githubusercontent.com/openclaw/openclaw/main/...` must check for a rename before recording a
gap** — this pool has already lost two rounds to a branch-guess 404 misread as a dead project.[^paperclip-paper]

**(i) Out of scope by dispatch, stated so the omission is not read as an oversight.** No pricing, ToS or
commercial-terms analysis. No treatment of ClawHub's distribution/supply-chain model beyond noting it exists as
a non-goal boundary in §4.10. No full identity/trust treatment — §3.6 is a solid paragraph and a pointer, and
the sibling paper this cycle owns the depth.

## 6. What this provides — the enumerated, plannable list

For the master-planning pass. Each row is sequenceable; costs are `derived` and their inputs are named in §4.

| # | Capability / lesson | Where it lands | Cost (order of magnitude) | Hard dependency |
|---|---|---|---|---|
| 1 | **Worktree reaping guard** — remove only when `git status --porcelain` is empty **and** no unpushed commits; snapshot before removal; time-boxed dirty-idle escape | Workflow standard + whatever reaps worktrees | **hours** | none |
| 2 | **Maturity taxonomy (M0–M5) + evidence-led promotion gates**, applied per phase | Standards-amendment candidate; per-phase readiness line | ~1 day, then hours/phase | none |
| 3 | **Restart-recovery contract table** — per-subsystem: what state, where stored, what happens on boot; plus one durable dispatch id per retry, and the no-replay-of-interrupted-hooks rule | `Phase: Temporal Integration`, **before** workers are written | hours (design), constrains build | Temporal port |
| 4 | **Durability boundary ruling** — decide explicitly where our durability *begins* (arrival vs admission). OpenClaw's line is admission; pre-admission work is lost by design | `Phase: Temporal Integration` | hours (a ruling) | Temporal port |
| 5 | **Typed child-result contract** — schema-per-call, `structured_output`-shaped; **decide whether the untyped path stays available** | `Phase: Temporal Integration`, activity result types | ~1 day design | Temporal port |
| 6 | **Capability declaration + approval + drift caveat** — a worker declares, an operator approves, a probe verifies; approved set ≠ live set | `Phase: Temporal Integration`, worker startup | 1–2 days | worker contract |
| 7 | **Looping predicate** — byte-identical-result window, warn-then-block, end-run on repeat; complement to the stalled predicate already recorded | `Phase: Temporal Integration`, `claude_cli` activity | 2–3 days (rule: hours) | activity design |
| 8 | **Threat-model section** — enumerate the TCB, name the boundaries, declare what is not a vulnerability | Standards-amendment candidate (human-ratified) | ~1 day | none |
| 9 | **Published non-goals list** | `problem-statement.md` (human-ratified path) | hours | none |
| — | ***Ruling supplied, not a build item:*** the open pinning question has a third option — pin the credential and proxy the model call — **which does not apply to `claude-cli` runtimes**, and that exclusion is itself the argument for today's pinned design | `problem-statement.md` § claim #2 open ruling | 0 | — |
| — | ***Claim refinement:*** differentiator #4's *"sold for code"* framing fails against OpenClaw; replace with **domain-general AND typed at the boundary by default** | `problem-statement.md` #4 (human-ratified path) | 0 | — |
| — | ***Claim strengthened:*** differentiator #1 gains a second, larger, independent first-party confirmation (§3.6) | `problem-statement.md` #1 | 0 | — |
| — | ***Claim retired:*** any residual framing of credential-locality as unusual (§3.4) | `problem-statement.md` | 0 | — |
| — | ***Designation refined:*** "nearest neighbour" needs an axis — bernstein by architecture, **OpenClaw by thesis** (§3.8) | `problem-statement.md` § *The nearest neighbor* | 0 | — |
| — | ***Reference only:*** the per-tenant cell pattern for trust separation by replication (§4.8) | SkyyCommand (owns the decision) | 0 | — |

## 7. The roadmap item that does not exist yet

**`roadmap.md` § *Tools to Evaluate* currently holds two entries — Paperclip (assessed 2026-08-04) and the
Claude Agent SDK. OpenClaw is absent.**[^roadmap] Given that it carries roughly five times the stars of the
previously-largest datum in this pool (§1.3), **its absence is the finding**, and the correct action is an
entry that records the assessment rather than an evaluation gate.

**Proposed entry text** *(for a planning run to apply — a research run writes nothing outside `research/`)*:[^research-standard]

> **OpenClaw** (`openclaw/openclaw`, MIT, OpenClaw Foundation) — **ASSESSED 2026-08-06, architecture rejected,
> mined heavily.** See `research/raw/openclaw_assessment.md`. It is not an orchestrator and its own `VISION.md`
> lists orchestration layers and agent hierarchies as non-goals; it is a single-Gateway personal-assistant
> control plane with SQLite-backed recovery, companion devices as peripherals, and an explicit
> one-trusted-operator-per-Gateway security model. **Not adoptable as a backbone and not buildable on.**
> It is nonetheless the pool's strongest evidence for two of our positions — credentials at the edge, and the
> limit of shipped multi-tenancy — and the sharpest counter-example to the "sold for code" framing.
> Ten transferable items are recorded in the assessment. **No further evaluation gate.**

**Two things the entry should NOT say.** It should not describe OpenClaw as a competitor to this repo's
workflow layer — the categories barely intersect. And it should not defer: the evaluation is complete to the
limit of what documentation can settle, and everything remaining is behavioural (§8).

## 8. Test plan — what research cannot settle

Each item names what would have to be run, installed or measured, and which section it closes.

1. **Crash the gateway mid-turn and observe.** Install OpenClaw on a spare box; start a long turn that has
   already executed one side-effecting tool; `kill -9` the gateway; restart. **Measures:** does the interrupted
   turn resume? Is the already-executed tool re-executed? Does an inbound message sent during the outage arrive
   or get *"rejected with an explicit restart error"*? **Closes §3.1** — specifically the derived
   *durability-starts-at-admission* finding, which is currently an inference from two documents. **Effort:**
   half a day.
2. **Packet-capture the credential claim.** Configure the `claude-cli` runtime with a logged-in Claude Code on
   the host; run a turn through a transparent proxy or `tcpdump`; confirm no credential material egresses.
   Repeat for a cloud-worker session with an API-keyed provider and confirm the proxy path. **Closes §3.4 and
   §4.1** — and, more importantly, **produces a reusable test we can run against our own edge design**, where
   the identical claim is load-bearing and equally untested. **Effort:** 1 day. **Highest value per hour on
   this list.**
3. **Exercise the typed child-result path.** Write a Swarm script that spawns two children with a JSON Schema
   and branches in code on the returned values. **Measures:** does the parent receive a typed value with no
   model in the loop? What happens when a child's output fails schema validation — the one question
   `llm-task.md` returned *"not stated"* for? **Closes §4.5 and the §3.2 boundary reading.** **Effort:** half a
   day.
4. **Verify the worktree guard empirically before copying it.** Create a managed worktree; leave (a) a dirty
   file, then (b) a clean tree with an unpushed commit; end the run. **Measures:** does removal actually block
   in both cases, and does the pre-removal snapshot contain what it claims? **Closes §4.3** — and since §4.3 is
   the item recommended for immediate adoption at zero dependency, **the guard should be validated before it is
   trusted with our own dispatch output.** **Effort:** 2 hours.
5. **Read the source for the two mechanisms documentation cannot settle.** (i) The inbound queue: is admission
   truly in-memory, and where exactly is the durable boundary? (ii) Loop detection: what are the numeric
   thresholds and window sizes, which `loop-detection.md` did not state? **Closes §3.1 and §4.7's tuning gap.**
   **Effort:** 1 day. **No install required** — this is a `git clone` and a read, and it also retires the
   §5(a)/§5(b) weakness for the sections it touches.
6. **Re-verify the rename chain first-party, or record it as permanently unverifiable.** Check whether the
   `openclaw` GitHub organisation or `openclaw.ai` publishes a rename record; if nothing first-party exists,
   §1.2's intermediate names stay `unverified` **permanently** and should be marked as such rather than
   re-litigated each refresh. **Closes §1.2.** **Effort:** 1 hour.
7. **Fetch the scorecard as a raw block, not through a summarizer.** §5(f) is unresolved because the fetch
   layer's grouping was inconsistent. `curl` the file and read it directly. **Closes §5(f)**, and would let
   §4.2 cite the distribution rather than four hand-picked rows. **Effort:** minutes, but requires a tool this
   dispatch did not have.

**One meta-item, and it is the most important row in this table.** Items 1–4 all test claims that **our own
design also makes** — durable resumption, credentials that never move, typed handoff, safe worktree reaping.
**Testing them against a shipping system is cheaper than testing them against our unbuilt one, and a negative
result on OpenClaw's implementation is a warning about ours.** That is the mining strategy executed at the
behavioural level rather than the documentary one.

## 9. Citations

**First-party — repository metadata and structure (GitHub REST API, JSON)**

[^gh-api-openclaw]: GitHub REST API, repo metadata for `openclaw/openclaw` (JSON): `full_name:
  "openclaw/openclaw"`, `description: "Your own personal AI assistant. Any OS. Any Platform. The lobster way.
  🦞"`, `homepage: "https://openclaw.ai"`, `stargazers_count: 385334`, `forks_count: 81008`,
  `open_issues_count: 5504`, `subscribers_count: 1759`, `language: "TypeScript"`, `default_branch: "main"`,
  `created_at: "2025-11-24T10:16:47Z"`, `pushed_at: "2026-08-06T12:30:34Z"`, `license.spdx_id: "NOASSERTION"`,
  `archived: false`, `fork: false`, `topics: ["ai","assistant","crustacean","molty","openclaw","own-your-data",
  "personal"]`. Fetched 2026-08-06. https://api.github.com/repos/openclaw/openclaw
[^gh-api-game]: GitHub REST API, repo metadata for `pjasicek/OpenClaw` (JSON) — the **disambiguation
  candidate**: `description: "Reimplementation of Captain Claw (1997) platformer"`, `language: "C++"`,
  `default_branch: "master"`, `license.spdx_id: "GPL-3.0"`, `created_at: "2017-03-08T12:05:03Z"`,
  `pushed_at: "2022-10-24T22:56:34Z"`. Fetched 2026-08-06. https://api.github.com/repos/pjasicek/OpenClaw
[^gh-search]: GitHub REST *search/repositories* API, `q=openclaw&sort=stars&order=desc&per_page=20` — the
  `items` array was **enumerated entry by entry**; no total is cited from it and none is used. Named here:
  `openclaw/openclaw`, `pjasicek/OpenClaw` (via the separate repos call above),
  `VoltAgent/awesome-openclaw-skills`, `hesamsheikh/awesome-openclaw-usecases`, `zeroclaw-labs/zeroclaw`.
  Fetched 2026-08-06.
  https://api.github.com/search/repositories?q=openclaw&sort=stars&order=desc&per_page=20
[^release]: GitHub REST API, latest release: `tag_name: "v2026.7.1-2"`, `name: "openclaw 2026.7.1-2"`,
  `published_at: "2026-08-04T00:41:26Z"`, `prerelease: false`, `draft: false`. Fetched 2026-08-06.
  https://api.github.com/repos/openclaw/openclaw/releases/latest
[^root-contents]: GitHub contents API, repository root — enumerated for navigation only; **no count asserted**.
  Entries relied on here: `LICENSE`, `README.md`, `VISION.md`, `SECURITY.md`, `CHANGELOG.md`, `Dockerfile`,
  `docker-compose.yml`, `fly.toml`, `render.yaml`, `deploy/`, `docs/`, `skills/`, `packages/`, `src/`.
  **No rename-history file (`HISTORY.md` or equivalent) appears in the enumeration** — the negative finding in
  §1.2. https://api.github.com/repos/openclaw/openclaw/contents/
[^announcements]: GitHub contents API, `docs/announcements` — the enumeration returned a single entry,
  `bluebubbles-imessage.md`; **no rename announcement**, part of §1.2's negative finding.
  https://api.github.com/repos/openclaw/openclaw/contents/docs/announcements
[^404-probe]: `api.github.com/repos/steipete/clawdbot` returned **HTTP 404 Not Found**, 2026-08-06. This was a
  **guessed owner/name probe**, not a documented path; per this pool's confirm-before-recording-a-404 rule it
  establishes only that this guess is not a live redirect, and is **not** evidence about the rename.
  https://api.github.com/repos/steipete/clawdbot
[^tools-listing]: GitHub contents API, `docs/tools` — enumerated for navigation only; **no count asserted**.
  Names relied on for the domain-generality reading: `browser.md`, `image-generation.md`,
  `music-generation.md`, `video-generation.md`, `media-overview.md`, `pdf.md`, `screen.md`, `tts.md`,
  `code-execution.md`, `mcp.md`. https://api.github.com/repos/openclaw/openclaw/contents/docs/tools
[^nodes-listing]: GitHub contents API, `docs/nodes` — enumerated for navigation only; **no count asserted**.
  Names relied on: `audio.md`, `camera.md`, `computer-use.md`, `location-command.md`, `media-playback.md`,
  `presence.md`, `talk.md`, `voicewake.md`. https://api.github.com/repos/openclaw/openclaw/contents/docs/nodes

**First-party — raw repository root files**

[^license]: `LICENSE` (raw, `main`) — **the only file in this paper returned as an unsummarized reproduced
  block**: `MIT License`, `Copyright (c) 2026 OpenClaw Foundation`, plus the trailing note *"Third-party
  notices for incorporated or adapted code are recorded in THIRD_PARTY_NOTICES.md."*
  https://raw.githubusercontent.com/openclaw/openclaw/main/LICENSE
[^readme]: `README.md` (raw, `main`) — **two fetches, both returned summarized prose despite an explicit
  request for a character-for-character fenced block; quoted spans only, reduced confidence (§5(b)).**
  https://raw.githubusercontent.com/openclaw/openclaw/main/README.md
[^vision]: `VISION.md` (raw, `main`) — positioning and the non-goals list.
  https://raw.githubusercontent.com/openclaw/openclaw/main/VISION.md
[^security]: `SECURITY.md` (raw, `main`) — trusted-computing-base enumeration, out-of-scope report classes,
  prompt-injection posture. https://raw.githubusercontent.com/openclaw/openclaw/main/SECURITY.md

**First-party — raw documentation, `docs/gateway/`**

[^restartrecovery]: `docs/gateway/restart-recovery.md` (raw).
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/restart-recovery.md
[^multitenant]: `docs/gateway/multi-tenant-hosting.md` (raw) — the Fleet / per-tenant-cell model.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/multi-tenant-hosting.md
[^cloudworkers]: `docs/gateway/cloud-workers.md` (raw) — leasing, owner-epoch fencing, credential proxying.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/cloud-workers.md
[^scopes]: `docs/gateway/operator-scopes.md` (raw) — at least eight named scopes; enforcement and disclaimers.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/operator-scopes.md
[^clibackends]: `docs/gateway/cli-backends.md` (raw) — `claude-cli` and `google-gemini-cli`; the
  logged-in-on-the-same-host requirement. **Whether that login is a subscription or an API key was `not
  stated` in the spans returned — recorded as a gap.**
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/cli-backends.md
[^secrets]: `docs/gateway/secrets.md` (raw) — SecretRefs, process-local sentinels, and the twice-stated
  "not a process-isolation boundary" caveat.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/secrets.md
[^multigateway]: `docs/gateway/multiple-gateways.md` (raw).
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/multiple-gateways.md
[^heartbeat]: `docs/gateway/heartbeat.md` (raw) — periodic main-session turns; **explicitly not a stalled-work
  detector: the questions "does it detect stalled or dead work" and "what does it do on detection" both
  returned `not stated`.**
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/heartbeat.md
[^pairing]: `docs/gateway/pairing.md` (raw) — signed device identity, out-of-band SSH verification, revocation,
  and the approved-set-vs-live-set caveat.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/pairing.md
[^sandboxing]: `docs/gateway/sandboxing.md` (raw) — off by default; "not a perfect security boundary".
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/sandboxing.md

**First-party — raw documentation, `docs/concepts/` and `docs/`**

[^architecture]: `docs/concepts/architecture.md` (raw) — Gateway ownership, WebSocket clients, node role,
  launchd/systemd supervision.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/architecture.md
[^multiuser]: `docs/concepts/multi-user.md` (raw) — "usability features, not security boundaries".
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/multi-user.md
[^multiagent]: `docs/concepts/multi-agent.md` (raw) — isolated agents in one process; deterministic bindings.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/multi-agent.md
[^runtimes]: `docs/concepts/agent-runtimes.md` (raw) — at least five named runtimes (`claude-cli`, `codex`,
  `copilot`, `openclaw`, `acp`); selection order; fail-closed pins. **Stated as a floor, not a total (§5(c)).**
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/agent-runtimes.md
[^queue]: `docs/concepts/queue.md` (raw) — in-process serialization by session key; lane-aware FIFO; coalescing.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/queue.md
[^sessionstate]: `docs/concepts/session-state.md` (raw) — `session_state_events`, durable per-session head,
  30-day / 50,000-row bound, single-owner assumption.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/session-state.md
[^lanes]: `docs/concepts/parallel-specialist-lanes.md` (raw) — routing not contention; "a coordinator without
  lane contracts just coordinates chaos".
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/parallel-specialist-lanes.md
[^worktrees]: `docs/concepts/managed-worktrees.md` (raw) — the two-condition removal guard, snapshot-before-
  removal, 7-day idle sweep.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/managed-worktrees.md
[^commitments]: `docs/concepts/commitments.md` (raw) — the retired inferred-commitments experiment.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/commitments.md
[^delegate]: `docs/concepts/delegate-architecture.md` (raw) — **fetched expecting parent→child dispatch
  semantics; it concerns organizational delegation and returned `not stated` to every dispatch question
  asked of it. Cited for the negative finding in §5(d), not for any positive claim.**
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/delegate-architecture.md
[^authsem]: `docs/auth-credential-semantics.md` (raw) — per-agent credential store, allowed credential kinds,
  portability flag, precedence.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/auth-credential-semantics.md
[^runtimearch]: `docs/agent-runtime-architecture.md` (raw) — module layout. **Asked directly about determinism,
  replay and durable execution: `not stated`. Part of §3.1's negative finding.**
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/agent-runtime-architecture.md
[^vps]: `docs/vps.md` (raw) — Gateway owns state and workspace on the server; back-up guidance.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/vps.md

**First-party — raw documentation, `docs/tools/`, `docs/automation/`, `docs/nodes/`, `docs/maturity/`**

[^subagents]: `docs/tools/subagents.md` (raw) — `sessions_spawn`, nesting/child caps, "return plain assistant
  text", restart pruning.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/subagents.md
[^swarm]: `docs/tools/swarm.md` (raw) — experimental; `agents.run()` with and without a JSON Schema;
  `structured_output`; local-only children.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/swarm.md
[^codemode]: `docs/tools/code-mode.md` (raw) — experimental; QuickJS-WASI `exec`; declared output contract.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/code-mode.md
[^llmtask]: `docs/tools/llm-task.md` (raw) — optional plugin; optional JSON Schema. **What happens on schema
  mismatch was `not stated` — a gap, and test-plan item 3.**
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/llm-task.md
[^goal]: `docs/tools/goal.md` (raw) — one durable objective per session; "a goal is not a task queue".
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/goal.md
[^loopdetect]: `docs/tools/loop-detection.md` (raw) — byte-identical window, warn-then-block escalation.
  **Numeric thresholds were `not stated` — a gap, and test-plan item 5.**
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/loop-detection.md
[^execapprovals]: `docs/tools/exec-approvals.md` (raw) — approvals persisted in SQLite on the execution host;
  "not a per-user auth boundary".
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/exec-approvals.md
[^taskflow]: `docs/automation/taskflow.md` (raw) — `flow_runs` table, revision-based optimistic concurrency,
  survives restarts. https://raw.githubusercontent.com/openclaw/openclaw/main/docs/automation/taskflow.md
[^clawflow]: `docs/automation/clawflow.md` (raw) — rename stub: "ClawFlow was renamed to Task Flow".
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/automation/clawflow.md
[^nodes]: `docs/nodes/index.md` (raw) — node definition, `connect.commands`, "Pin exec to a specific node",
  "peripherals, not gateways".
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/nodes/index.md
[^scorecard]: `docs/maturity/scorecard.md` (raw) — evidence-led coverage rule; individual area→level pairs
  cited in §3.5 and §4.2. **§5(f) records that the fetch's level-grouping was internally inconsistent; no
  distribution or per-level count is asserted from this source.**
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/maturity/scorecard.md
[^taxonomy]: `docs/maturity/taxonomy.md` (raw) — the six M0–M5 definitions and the five promotion gates.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/maturity/taxonomy.md

**Third-party — rendered page, reduced confidence (§3 raw-over-rendered rule)**

[^wikipedia]: Wikipedia, *OpenClaw*, page last edited 4 August 2026 — **sole source for the rename chain
  (§1.2) and the attribution to Peter Steinberger. Rendered third-party page; every datum from it is marked
  `unverified` EXCEPT the first ("Warelay, Nov 24, 2025"), which is corroborated by the repository's
  first-party `created_at`.**[^gh-api-openclaw] https://en.wikipedia.org/wiki/OpenClaw

**This repo — the documents this paper feeds and cites**

[^problem-statement]: `docs/standards/architecture/problem-statement.md` — the federated frame, the four
  differentiators, the nearest-neighbour designation, and the unresolved pinning ruling.
[^system-overview]: `docs/standards/architecture/system-overview.md` — layers, memory surfaces, safety model,
  *What is not built*, and § *Deployment target* (Temporal self-hosted; systemd workers; k8s for the server
  tier).
[^roadmap]: `docs/development/roadmap.md` § *Tools to Evaluate* — two entries as of this sweep (Paperclip,
  assessed 2026-08-04; Claude Agent SDK). **OpenClaw is absent** — §7.
[^paperclip-paper]: `docs/standards/architecture/research/raw/paperclip_assessment.md` (Last validated
  2026-08-04; Critic: PASS-WITH-FIXES) — the pool's exemplar comparator paper. Cited here for: the 75,610-star
  figure and "largest in this pool" framing; the credential-at-the-edge correction; the three-shape coordination
  table; the stalled predicate; the `testEnvironment` capability-preflight finding; the branch-guess-404 lesson;
  and the seven-fetches-seven-totals enumeration failure that §5(c) applies.
[^research-standard]: `docs/standards/research/research_standard.md` (vendored, MIRROR) — §3 the mini-paper
  contract and sourcing rules; §5 volatility tiers; §7 consumption (a research run writes nothing outside
  `research/`).
