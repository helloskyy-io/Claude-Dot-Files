# OpenClaw — Architecture Rejected on Altitude, Six Things Worth Taking, and the Auth Question Answered

```
Topic:          OpenClaw is the largest project in this category by adoption and the one named in the
                February 2026 OAuth-enforcement coverage. What is its architecture, what does it say about
                Anthropic auth today, and what is worth taking regardless of whether the architecture suits us?
Feeds:          docs/development/roadmap.md § "Tools to Evaluate" — NO OpenClaw item exists there today;
                whether one should is answered in §7. And docs/standards/architecture/problem-statement.md
                § "Where we actually differ" #4 (domain generality) and § "The edges". Secondarily
                docs/standards/architecture/research/raw/anthropic_tos_and_enterprise.md §3.3, whose
                third-party press claim this paper was commissioned to run down (§4.1).
Last validated: 2026-08-06
Revalidate:     high — 3 weeks
Confidence:     DEFINITIVE for the auth findings (§4.1) and the Anthropic policy state — those rest on
                fenced VERBATIM reproductions of raw first-party markdown (docs/providers/anthropic.md,
                docs/auth-credential-semantics.md, docs/providers/claude-max-api-proxy.md) plus a full
                verbatim fetch of Anthropic's own legal-and-compliance page. DEFINITIVE for repository
                metadata (raw GitHub API JSON) and for the license text. REDUCED-CONFIDENCE FIRST-PARTY for
                everything sourced through a SUMMARIZING fetch of a raw .md — the trust-boundary quotes
                (§2.5), the durability quotes (§2.2), the cloud-worker quotes (§2.4) — these are raw-source
                first-party but were returned as quoted spans inside prose, not as reproduced blocks, and
                §5(b) records one measured case on this very repo where a summarizing fetch produced two
                spans a later verbatim fetch of the same page did NOT contain. DIRECTIONAL for VISION.md's
                roadmap and non-goals. UNVERIFIED for the April 2026 enforcement date — third-party rendered
                press only, internally inconsistent, and absent from every Anthropic first-party surface
                fetched (§4.1(d), a gap finding with its search method). DERIVED for the whole of §3, all
                cost estimates in §4/§6, and the two-tests verdict. NOTHING WAS EXECUTED; no TypeScript was
                read. COUNTS are stated as floors from single enumerations and are load-bearing nowhere.
Critic:         not-yet-verified — 2026-08-06
```

> ## Headline — three answers, and one of them changes what we thought we knew
>
> **Test (a) — architecture: NO, and the reason is altitude, not quality.** OpenClaw is a **single-operator,
> single-host personal assistant**. Its own security policy calls it *"local-first agent infrastructure for
> trusted operators"* and states it is not *"a shared multi-tenant boundary between adversarial users on one
> gateway"*;[^security] its multi-tenant guide's answer to two untrusted tenants is *"running a separate
> complete OpenClaw instance for each tenant"*, and *"one Gateway remains one trusted operator
> domain"*.[^multitenant] Durability is hand-rolled on SQLite.[^restart] It is one process that owns
> everything. That is a coherent design for the product it is; it is the opposite of a federated fabric of
> distinct operators on a Temporal backbone (§3).
>
> **Test (b) — mine: YES, six items, and one of them is the single most useful artifact in this
> pool for `Phase: Temporal Integration`.** OpenClaw's crash-recovery design is a complete, documented,
> production-hardened answer to *what do you do when a long agent turn dies mid-flight* — durable dispatch
> identifier, a **charged** three-attempt budget that survives restarts, a two-hour finalize horizon, and
> **tombstoning** rather than looping (§4.2). We are about to design exactly this on top of Temporal, and
> Temporal supplies the mechanism but none of the policy.
>
> **The auth lead is answered, and the answer is a WIN.** OpenClaw's current first-party docs describe **no
> consumer-OAuth-token-extraction path for Anthropic at all.** The two documented routes are an API key and
> *"Claude CLI — reuse an existing Claude Code login on the same host"*, which works by running the installed
> Claude Code binary in `claude -p` mode.[^anthropic] The credential-semantics doc is explicit that external
> CLI credentials are **discovered, not copied**,[^authsem] and OpenClaw's own docs assert *"Anthropic has
> confirmed that Claude CLI reuse (including `claude -p`) is a sanctioned integration pattern unless it
> publishes a new policy."*[^usagecosts] **The largest project in the category converged on our exact
> pattern** — invoke the real CLI on the host that holds the login. And Anthropic's own support article, last
> updated 2026-06-16, states: *"We're pausing the changes to Claude Agent SDK usage described below. For now,
> nothing has changed: Claude Agent SDK, `claude -p`, and third-party app usage still draw from your
> subscription's usage limits."*[^anthropic-sdk-plan]
>
> **What this paper does NOT do is upgrade the press claim.** No Anthropic first-party surface fetched here
> documents an April 2026 third-party enforcement event, and the one third-party article fetched is
> internally inconsistent about its own date. That absence is stated as a gap with its search method in
> §4.1(d), not resolved.
>
> **And one genuine win for them, stated as a win.** OpenClaw's cloud-worker design solves *run the work
> somewhere else without moving the credential* by **proxying inference back through the credential
> holder**[^cloudworkers] — the exact inverse of our topology, shipped, and a real option we had not
> considered (§4.5).

---

## 1. Primer — what OpenClaw is, and how this paper was built

**OpenClaw** (`openclaw/openclaw`) is TypeScript. From the GitHub REST API, fetched 2026-08-06:
`default_branch: "main"`, `language: "TypeScript"`, `license.spdx_id: "NOASSERTION"`,
`stargazers_count: 385333`, `forks_count: 81008`, `open_issues_count: 5503`, `subscribers_count: 1759`,
`created_at: "2025-11-24T10:16:47Z"`, `pushed_at: "2026-08-06T12:24:59Z"`,
`homepage: "https://openclaw.ai"`, `description: "Your own personal AI assistant. Any OS. Any Platform. The
lobster way. 🦞"`.[^gh-api] **It is roughly five times the size of Paperclip by stars and is the largest
system this pool has assessed by a wide margin.** *(These are counts a source STATES, quoted from an API
JSON response — not counts this paper measured; see §5(c).)*

**A license discrepancy, stated rather than resolved.** The API reports `license.spdx_id: "NOASSERTION"`,
but the repository's `LICENSE` file begins *"MIT License"* / *"Copyright (c) 2026 OpenClaw
Foundation"*.[^license] GitHub's classifier declining to match a file that self-identifies as MIT usually
means added text, but **I did not read the whole file and do not assert why.** Anyone depending on the
license terms must read `LICENSE` directly.

**Its own framing.** `VISION.md`: *"OpenClaw is the AI that actually does things. It runs on your devices, in
your channels, with your rules."*[^vision] It is a personal assistant reachable through messaging channels —
WhatsApp, Telegram, Slack, Discord, Signal, iMessage, WebChat — with a local daemon in the
middle.[^architecture]

**Why it is in this pool at all.** Two independent signals, both already recorded here: Paperclip ships an
`openclaw_gateway` built-in adapter,[^paperclip] and OpenClaw is the tool named in the February 2026
OAuth-enforcement coverage recorded in `anthropic_tos_and_enterprise.md` §3.3.[^anthropic-tos] Being adapted
by a competitor is evidence of a shipped interface; being named in an enforcement story about *our* auth
model makes it load-bearing.

**Search method for this paper.** GitHub REST *git trees* API for every directory enumeration (root,
`docs`, `docs/providers`, `docs/gateway`, `docs/concepts`, `docs/nodes`, `docs/tools`, `docs/automation`,
`docs/announcements`, `deploy`); GitHub REST repo API for metadata; and `raw.githubusercontent.com` for
every document. **Twenty-two raw first-party OpenClaw files** were fetched. Four of them
(`docs/providers/anthropic.md` §§ *Usage and cost tracking* / *Getting started*,
`docs/providers/claude-max-api-proxy.md` §§ *Why use this* / *How it works* / *Notes*,
`docs/auth-credential-semantics.md` §§ *External CLI credential discovery* / *Agent copy portability*,
`docs/reference/api-usage-costs.md`) were retrieved as **fenced verbatim reproductions**, which is the
strongest source class available without cloning; the rest came back as quoted spans inside a summarizing
response and are marked at reduced confidence throughout. Two Anthropic first-party pages were fetched
(`legal-and-compliance` came back as complete verbatim markdown). One rendered third-party news page was
fetched and is used only where flagged. **Nothing was executed and no TypeScript was read** — §5(a) states
what that costs.

**Volatility note (§3 mixed-volatility rule).** The header takes `high — 3 weeks`, tighter than the
Paperclip paper's four, for one specific reason: the load-bearing external fact in §4.1 is in a
**paused** state by Anthropic's own words, and OpenClaw's own documentation warns *"Anthropic can change
Claude Code billing and rate-limit behavior without an OpenClaw release."*[^anthropic] The repository was
also pushed on the day of the sweep.[^gh-api] The **lessons** in §4.2 and §4.3 are design policy, not
features, and age far better; a refresh should re-verify §4.1 first and may treat §4.2–§4.4 as slow-moving.

## 2. The specific model — how OpenClaw actually works

Six mechanisms, each first-party.

**2.1 One long-lived Gateway process owns everything.** *"A single long-lived Gateway owns all messaging
surfaces (WhatsApp via Baileys, Telegram via grammY, Slack, Discord, Signal, iMessage, WebChat)"*, it
*"Maintains provider connections"*, *"Exposes a typed WS API (requests, responses, server-push events)"* and
*"Validates inbound frames against JSON Schema"*; *"Control-plane clients (macOS app, CLI, web UI,
automations) connect to the Gateway over WebSocket on the configured bind host"*; and the invariant is
stated flatly — *"One Gateway per host; it is the only place that opens a WhatsApp
session."*[^architecture] The WS endpoint *"defaults to `ws://127.0.0.1:18789`"* and *"Remote access is
typically an SSH tunnel or Tailscale VPN"*.[^network] *(reduced-confidence first-party — summarizing
fetch.)*

**2.2 Durability is bespoke, on SQLite, and unusually well specified.** `restart-recovery.md` tabulates what
survives: conversation history in a *"Per-agent SQLite database"*; the interrupted turn in a *"Per-agent
SQLite session row and transcript"*; subagent runs, background tasks, the outbound delivery queue, the cron
store and a *"restart sentinel"* each in SQLite.[^restart] Behaviourally: *"Work that was interrupted
mid-turn is detected and resumed automatically after the gateway comes back up"*; *"A few seconds after
startup, the gateway re-dispatches each marked session with a synthetic system message"*; *"Every retry
reuses one durable dispatch identifier, so an ambiguous connection failure cannot start the same recovery
twice"*.[^restart] And it is **bounded in three independent ways**: *"Each interrupted main-session cycle has
a durable budget of three charged automatic dispatch attempts, retained across gateway restarts"*; *"Runs
interrupted more than 2 hours ago are finalized instead of resumed"*; *"A session that repeatedly fails to
recover is tombstoned as wedged so recovery cannot loop forever"*.[^restart] *(reduced-confidence
first-party — summarizing fetch; §4.2 treats this as the paper's highest-value finding and test-plan item 1
is its direct verification.)*

**2.3 Above the turn sits a durable flow layer.** *"Task Flow is the orchestration layer above background
tasks."* *"A flow is a durable record of multi-step work with its own status, JSON state, revision counter,
and linked task records."* *"The controller advances the flow between `running`, `waiting`, and terminal
states, and stores arbitrary JSON step state on the flow record."* The controller is *"plugin code that
creates the flow through the plugin runtime Task Flow API… then drives it explicitly"*, and flow records
*"persist in the shared SQLite state database"*.[^taskflow] **This is a code-routed driver over persisted
state — element 4 of the recipe, hand-rolled.** *(reduced-confidence first-party.)*

**2.4 Work can move to a machine; the credential does not.** Cloud workers *"let a session run its agent loop
on a throwaway cloud machine while everything about the session stays where it always was"*: *"The Gateway
leases a box, installs a pinned copy of OpenClaw on it, syncs the session's workspace over, and hands the
turn loop to a restricted `openclaw worker` process."* Crucially — *"Model calls are proxied back through the
Gateway, so provider credentials never leave your machine"*, with *"No standing model, forge, or cloud
credentials on the box. Model auth stays on the Gateway (inference travels by `{provider, model}`
reference)."* Lifecycle: *"When the work is done (or the box dies), the machine is discarded. The durable
state — transcript, workspace commits, placement records — lives with the Gateway."*[^cloudworkers]
*(reduced-confidence first-party — and §4.5 argues this is the most architecturally interesting thing in the
project.)*

**2.5 The trust model is one operator, explicitly and repeatedly.** `SECURITY.md` describes the project as
*"local-first agent infrastructure for trusted operators"* and states it is not *"a shared multi-tenant
boundary between adversarial users on one gateway"*; *"Authenticated Gateway callers are treated as trusted
operators for that gateway instance"*; the exec sandbox is host-first — *"`agents.defaults.sandbox.mode`
defaults to `off`"*; and the operator instruction is *"Do **not** expose it to the public internet (no direct
bind to `0.0.0.0`, no public reverse proxy). It is not hardened for public exposure."*[^security] The
multi-tenant guide does not soften this: *"Hosting users or organizations that do not share a trust boundary
therefore means running a separate complete OpenClaw instance for each tenant"*; *"No rung in this ladder
changes the OpenClaw application trust model: one Gateway remains one trusted operator domain"*; *"The Fleet
operator and the host are trusted by every tenant. Resistance to a compromised host is a non-goal"*; *"Do not
co-locate mutually untrusted users in one OpenClaw process or one OS user."*[^multitenant]
*(reduced-confidence first-party — but the position is stated four separate ways across two documents, which
is itself corroboration.)*

**2.6 The model loop is pluggable, and one of the plugs is Claude Code.** *"An agent runtime owns one
prepared model loop: it receives the prompt, drives model output, handles native tool calls, and returns the
finished turn to OpenClaw."* One enumeration of that page named **at least five** runtimes — `openclaw`,
`claude-cli`, `codex`, `copilot`, `acp` — with the distinction that *"Embedded harnesses run inside
OpenClaw's prepared agent loop"* while *"CLI backends run a local CLI process while keeping the model ref
canonical."*[^runtimes] For the CLI backends specifically: *"The gateway service must have the CLI on its
`PATH`"*, *"Before OpenClaw can use `claude-cli`, Claude Code itself must be logged in on the same host"*,
and on restart *"OpenClaw resumes from the stored Claude session id"*. A stated limitation: *"OpenClaw does
not inject tool calls into the CLI backend protocol."*[^clibackends] *(reduced-confidence first-party;
runtime count stated as a floor per §5(c).)*

## 3. Test (a) — is the architecture right for us? No. Four reasons, then move on.

**The five axes the existing comparators were assessed on**, answered:

| Axis | OpenClaw | This repo's destination |
|---|---|---|
| **1. Durability** | Bespoke, on SQLite. Per-agent DB + shared state DB + delivery queue + cron store + restart sentinel; interrupted turns re-dispatched on boot with a durable dispatch identifier, a charged 3-attempt budget, a 2-hour finalize horizon and tombstoning[^restart] | Temporal, self-hosted[^system-overview] |
| **2. Domain generality** | **Fully general and always was** — a personal assistant over messaging channels, with browser, media, exec, search and device tools; coding is one runtime among several.[^toolstree][^runtimes] Result contract at the sub-agent boundary is **prose**: a completion carries the *"latest visible `assistant` reply text from the child"*.[^subagents] Typed structure exists on the **protocol** (TypeBox-generated schemas, `{type:"req"…}` / `{type:"res"…}` / `{type:"event"…}` frames, `minProtocol`/`maxProtocol` negotiation, *"current clients and servers run protocol v4"*)[^protocol] and on **Task Flow** (*"arbitrary JSON step state"*)[^taskflow] — but not between an agent and its child | Domain-general backbone; typed handoff between steps is element 3 and is **not built**[^system-overview] |
| **3. Dispatch / worker** | **Neither queue-claim nor addressed workers.** A Gateway routes inbound messages to an agent by *"bindings"* — channel/account/peer match — with no contention and no hierarchy: *"Run multiple _isolated_ agents in one Gateway process"*.[^multiagent] Remote execution exists only as leased throwaway cloud workers driven by the Gateway[^cloudworkers] | Dedicated edges addressed by identity |
| **4. Credential locality** | **At the edge, by construction, and hardened.** Claude auth is API key or reuse of the host's own Claude Code login; *"Claude CLI reuse expects the OpenClaw process to run on the same host as the Claude CLI login"*[^anthropic]; external-CLI credentials are discovered in scope rather than copied[^authsem]; `oauth` profiles are *"not portable by default"*[^authsem]; and cloud workers get **no** model credential at all[^cloudworkers] | Credential never leaves the edge |
| **5. Deployment** | A **daemon on one host**. *"The standard `openclaw onboard --install-daemon` path installs a systemd user unit"*[^vps]; Docker, `docker-compose.yml`, `fly.toml`, `render.yaml` and `deploy/fly.private.toml` are present at the repo root[^tree-root][^tree-deploy]. **No Kubernetes deployment documentation was found** — searched the `deploy` tree (one file), the repo root tree, and `docs/vps.md`, whose provider coverage names cloud hosts and systemd but no k8s[^vps][^tree-deploy][^tree-root] | k3s HA server tier + systemd workers[^system-overview] |

**3.1 It is one trusted operator domain, and we are three trust tiers.** §2.5's four statements are not
incidental phrasing; they are the product's stated boundary. `problem-statement.md` differentiator #1
requires edge / MDC / federated tiers held by *distinct operators*.[^problem-statement] **OpenClaw's own
documentation puts that outside its scope even harder than the nearest neighbour's did** — bernstein's fleet
is *"not multi-tenant in the security sense"*;[^problem-statement] OpenClaw's answer to two untrusted tenants
is a whole second installation.[^multitenant] *(derived — inputs: §2.5 and `problem-statement.md` #1.)*

**3.2 Durability is re-derived per feature, and the price list is visible.** Seven SQLite surfaces, a restart
sentinel, a startup reconciliation pass with exponential backoff, a charged retry budget persisted across
restarts, a wedged-session tombstone, and a two-hour finalize horizon — all so a process can resume its own
work.[^restart] Temporal gives the *mechanism* for every one of those.[^temporal-paper] **This is not a
criticism; it is a second independent price list beside Paperclip's 206 migrations**, and §4.2 spends it.
*(derived.)*

**3.3 One host owns everything, so there is nothing to federate.** One Gateway per host, one process holding
every channel connection, agents as personas inside it, remote work only as leased ephemeral boxes the
Gateway drives.[^architecture][^multiagent][^cloudworkers] There is no worker fleet to address, no queue to
route to, no second operator. Adopting this shape would mean deleting the destination. *(derived.)*

**3.4 It explicitly rejects the layering that element 2 depends on.** `VISION.md`'s *"What We Will Not Merge
(For Now)"* names *"Agent-hierarchy frameworks (manager-of-managers / nested planner trees) as a default
architecture"*.[^vision] Our parent→child→judge composition is precisely a nested planner tree, and
`problem-statement.md` element 2 makes the layering the thesis.[^problem-statement] **This is the one place
where we and the biggest project in the category have made opposite bets in the open** — and §5(f) argues
their bet is not obviously wrong. *(directional — `VISION.md` is a stated non-goal, not a shipped
constraint, and it carries its own "(For Now)".)*

**Verdict on (a): do not adopt the architecture.** Nothing in §4 depends on this verdict — that separation
is the point of the two-tests rule.

## 4. Test (b) — what to take. Six items, ranked, each with a cost and a landing surface.

Ranking is by *value to the federated destination × plannability*. **Costs are `derived` throughout and name
their inputs.**

### 4.1 — The auth answer, and what it does and does not settle `RANK 1 (evidence, not capability)`

This is the lead the dispatch required run down. It is answered in four parts.

**(a) What OpenClaw supports today, first-party and verbatim.** `docs/providers/anthropic.md` documents two
routes: *"**API key** — direct Anthropic API access with usage-based billing (`anthropic/*` models)"* and
*"**Claude CLI** — reuse an existing Claude Code login on the same host"*.[^anthropic] The CLI route is not a
token replay — it runs the real binary: *"OpenClaw's Claude CLI backend runs the installed Claude Code CLI in
non-interactive print mode (`claude -p`)."*[^anthropic] Onboarding is *"choose: Claude CLI"*, after which
*"OpenClaw detects and reuses the existing Claude CLI credentials."*[^anthropic] Locality is stated as a
requirement, not a recommendation: *"Claude CLI reuse expects the OpenClaw process to run on the same host as
the Claude CLI login."*[^anthropic] A third, Anthropic-sanctioned mechanism is offered for machines without a
login: *"Run `claude setup-token` on any machine with Claude Code installed. It prints a long-lived token
starting with `sk-ant-oat01-`."*[^anthropic] *(definitive — fenced verbatim reproduction of raw first-party
markdown.)*

**(b) The credential-handling design actively avoids copying tokens.** *"Runtime-only credentials owned by
external CLIs (Claude CLI for `claude-cli`, Codex CLI for `openai`, MiniMax CLI for `minimax-portal`) are
discovered only when the provider, runtime, or auth profile is in scope for the current operation, or when a
stored local profile for that external source already exists."* Copy flows are constrained: *"`oauth`
profiles are not portable by default because refresh tokens can be single-use or rotation-sensitive."*
Inheritance across agents is read-through — it *"resolves profiles from the default/main agent store at
runtime without copying secret material into its own credential store"*. And read-only paths *"use
file-backed external CLI credentials only and do not read or reuse macOS Keychain results."*[^authsem]
*(definitive — fenced verbatim reproduction.)*

**(c) OpenClaw asserts Anthropic's blessing; Anthropic's own documented page does not say it.** OpenClaw
states: *"Anthropic has confirmed that Claude CLI reuse (including `claude -p`) is a sanctioned integration
pattern unless it publishes a new policy."*[^usagecosts] **This is a first-party OpenClaw claim ABOUT a third
party, and it must not be laundered into an Anthropic statement.** What Anthropic's own
`legal-and-compliance` page actually says, fetched verbatim: OAuth *"is intended exclusively for purchasers
of Claude Free, Pro, Max, Team, and Enterprise subscription plans and is designed to support ordinary use of
Claude Code and other native Anthropic applications"*; *"Anthropic does not permit third-party developers to
offer Claude.ai login or to route requests through Free, Pro, or Max plan credentials on behalf of their
users"*; *"Advertised usage limits for Pro and Max plans assume ordinary, individual usage of Claude Code and
the Agent SDK"*; and *"Anthropic reserves the right to take measures to enforce these restrictions and may do
so without prior notice."*[^anthropic-legal] **The reconciliation is the finding, and it is ours as much as
theirs:** the prohibited act is a *third-party developer routing requests through consumer credentials on
behalf of their users*. A tool that spawns the user's own Claude Code, on the user's own host, under the
user's own login, is not doing that — but Anthropic's documented page **never names the CLI-reuse pattern as
permitted**, so "sanctioned" is OpenClaw's characterization, not a quotable Anthropic position. *(the
Anthropic quotes: definitive. The word "sanctioned": directional, first-party-to-OpenClaw only.)*

**(d) The billing status, and the gap.** OpenClaw's docs state: *"Anthropic's June 15, 2026 support update
paused the announced separate Agent SDK billing change: Claude Agent SDK, `claude -p`, and third-party app
usage still draw from a signed-in subscription's usage limits, and the previously announced monthly Agent SDK
credit is not available while Anthropic revises that plan."*[^anthropic] **That is corroborated at
first-party by Anthropic itself**, whose support article (last updated 2026-06-16) states *"We're pausing the
changes to Claude Agent SDK usage described below. For now, nothing has changed: Claude Agent SDK, `claude
-p`, and third-party app usage still draw from your subscription's usage limits."*[^anthropic-sdk-plan]
*(definitive on the pause — two first-party sources, one from each party.)*

> **The gap, with its search method.** `anthropic_tos_and_enterprise.md` line ~140 records February 2026
> press reporting server-side enforcement against tools that had *"extracted consumer OAuth
> tokens"*.[^anthropic-tos] **I could not corroborate that from any first-party source, and I am not
> upgrading it.** Specifically: (i) **no OpenClaw first-party document states that a consumer-OAuth
> extraction path ever existed or was removed** — searched `docs/providers/anthropic.md`,
> `docs/concepts/oauth.md`, `docs/gateway/authentication.md`, `docs/auth-credential-semantics.md`,
> `docs/providers/claude-max-api-proxy.md`, `docs/reference/api-usage-costs.md`, the `docs/announcements`
> tree (**one file, unrelated**), and a `CHANGELOG.md` probe for the terms *Anthropic / OAuth / subscription
> / Claude CLI / setup-token*, which returned only unrelated maintenance entries. (ii) **No Anthropic
> first-party surface fetched documents an April 2026 third-party enforcement** — checked
> `code.claude.com/docs/en/legal-and-compliance` (verbatim, no dates at all) and
> `support.claude.com/…/11145838-use-claude-code-with-your-pro-or-max-plan` (last updated 2026-06-11), which
> **does not mention third-party tools, OAuth, or April 2026**.[^anthropic-legal][^anthropic-promax]
> (iii) The one rendered third-party article fetched is **internally inconsistent**: published 2026-04-06 by
> Thomas Claburn, it carries both *"As of April 4, 2026, Anthropic went from policy warnings to
> billing-based enforcement"* and *"Starting tomorrow at 12pm PT, Claude subscriptions will no longer cover
> usage on third-party tools like OpenClaw."*[^register] Those cannot both describe the same event on the
> same page. **Status: an enforcement event in early 2026 is plausible and widely reported; its date,
> scope and current force are UNVERIFIED, and the only first-party statement about the current state says
> the changes are paused.** *(unverified — rendered third-party page, self-contradictory, uncorroborated
> first-party.)*

**What this is worth to us.** `problem-statement.md`'s affordability thesis depends on subscription auth at
the edge remaining viable.[^problem-statement] Two things now support it that did not before: an
**explicitly current first-party Anthropic statement** that `claude -p` still draws from subscription
limits,[^anthropic-sdk-plan] and the observation that the **385k-star** project in this category ships
host-local CLI reuse as a first-class route with a documented no-copy credential design.[^gh-api][^authsem]
Paperclip already removed *unusual* from this claim;[^paperclip] OpenClaw removes *fragile*.

**Cost: zero.** This is evidence, not a backlog item. It does, however, imply a **correction candidate** for
`anthropic_tos_and_enterprise.md` §3.3 (§6).

### 4.2 — Crash-recovery POLICY: the charged budget, the horizon, and the tombstone `RANK 2`

**This is the highest-value transferable design in the paper**, because it is the part Temporal does not give
us and we are weeks from having to invent it.

**What it is.** Four policies layered on top of resume-the-interrupted-turn:[^restart]

1. **A durable, charged attempt budget.** *"Each interrupted main-session cycle has a durable budget of three
   charged automatic dispatch attempts, retained across gateway restarts"*. The word doing the work is
   **charged** — an attempt is spent whether or not it succeeded, and the count survives the crash that
   caused it.
2. **Idempotent recovery dispatch.** *"Every retry reuses one durable dispatch identifier, so an ambiguous
   connection failure cannot start the same recovery twice"*.
3. **A staleness horizon.** *"Runs interrupted more than 2 hours ago are finalized instead of resumed"* —
   past some age, resuming is worse than closing out, because the world moved.
4. **A terminal state for unrecoverable work.** *"After the durable budget is exhausted, the session is
   tombstoned instead of looping forever"*; *"A session that repeatedly fails to recover is tombstoned as
   wedged so recovery cannot loop forever"*.

And a **do-not-resume list** that is as instructive as the resume path: sessions with another owner
(*"subagent recovery"*, the cron scheduler, ACP-managed), sessions *"whose transcript tail cannot be safely
continued"* which get a resend notice instead of a silent re-run, and *"Work that was never admitted:
messages arriving during the drain window are rejected with an explicit restart error"*.[^restart]

**Why it matters for the federated destination.** Temporal gives us retry policies, workflow-ID reuse and
deterministic replay — the *mechanism*.[^temporal-paper] It does not tell us **how many times to charge a
`claude -p` run that keeps dying, when a resumed run is too stale to be worth resuming, or what state a
permanently-wedged run should end in so a human can find it.** Those are exactly the three questions
`Phase: Temporal Integration` has to answer for the `claude_cli` activity, and OpenClaw has shipped answers
for a workload of the same shape (long, expensive, non-idempotent model turns). **The two-hour horizon is the
subtlest and most valuable of the three** — a resumed agent turn whose world has moved on is not a recovered
run, it is a new run with a stale premise. Nothing in our current design has that idea in it.

**And it lands on a live gap in this repo.** `system-overview.md` records `HOLD(redispatch) → one bounded
loop-back, then stop`.[^system-overview] That is a budget of one, not durable, with no terminal state and no
staleness rule. **OpenClaw's tombstone is the same shape as Paperclip's "invisible zombie" scar** —
independently arrived at, by a different project, in a different language, on a different substrate. *(derived
— inputs: §2.2, `system-overview.md` § Composition, `raw/paperclip_assessment.md` §4.2.)* **Two independent
projects converging on "unrecoverable work needs a name and a terminal state" is the strongest
transferable signal in this paper.**

**Cost to build here. S (~1 day of design), and it MUST land before workers are written.** *(derived — inputs:
the four policies above; `raw/python_sdk_long_activities.md`'s account of activity retry/heartbeat; the
observation that all four are policy constants and one state, not machinery.)* Concretely: a charged-attempt
counter in workflow state (not activity retries — activity retries do not survive the way a charged budget
must), a `max_age` guard before re-dispatch, and a `wedged` terminal status that the standup surfaces.
**Lands on:** `Phase: Temporal Integration`, `claude_cli` activity + the workflow that wraps it.

### 4.3 — Credential discovery over credential copying, as a stated rule `RANK 3`

**What it is.** Three rules from `auth-credential-semantics.md`, all verbatim in §4.1(b): external CLI
credentials are **discovered in scope**, never copied; `oauth` profiles are **not portable by default**
because refresh tokens *"can be single-use or rotation-sensitive"*; and cross-agent inheritance is
**read-through** — resolve at runtime *"without copying secret material into its own credential
store"*.[^authsem] Reinforced by the secrets layer, where *"SecretRefs stop credentials from being persisted
in config and generated model files"* and *"OpenClaw intentionally does not write rollback backups containing
historical plaintext secret values"*.[^secrets] *(the auth-semantics rules: definitive, verbatim. The secrets
spans: reduced-confidence first-party.)*

**Why it matters for the federated destination.** `problem-statement.md` differentiator #1 says the edge
*"holds its own credential, which never leaves it"*.[^problem-statement] That is a topology statement. **It
is not yet a rule about what the software may do with a credential it can see**, and `raw/multi_edge_identity_trust.md`
is this cycle's paper on exactly that question. OpenClaw supplies a ready-made three-line rule set, and
critically, **the single-use-refresh-token rationale is a real operational hazard we would otherwise
discover the hard way**: a copied OAuth refresh token that is spent by the copy invalidates the original.
An edge that "helpfully" propagated a credential to a peer edge would break the peer's login, not share it.

**Cost to adopt: S (hours) — it is a standards-amendment candidate, not code.** *(derived — inputs: the three
rules; the fact that this repo has no worker-side credential rule today.)* **Lands on:** a candidate for the
worker/edge standard, routed per Research Standard §7 (a research run surfaces; a planning run writes).

### 4.4 — The stalled-and-wedged vocabulary, and a loop guard on `(tool, args, result)` `RANK 4`

**What it is.** Two small, independent mechanisms:

- **Loop detection.** *"OpenClaw has two cooperating guardrails against repetitive tool-call patterns"*,
  watching *"the rolling tool-call history for repeated patterns and unknown-tool retries"* and specifically
  the same *"`(tool, args, result)` triple"*, then it *"logs a loop event and either warns or blocks the next
  tool-cycle depending on severity"*. **The documented `enabled` field defaults to `false`.**[^loopdetect]
- **Sub-agent bounds.** *"Maximum nesting depth is 5 (`maxSpawnDepth` range: 1-5)"*, and at most
  *"`maxChildrenPerAgent` (default `5`) active children at a time"*.[^subagents]

*(reduced-confidence first-party — summarizing fetches; no numeric loop thresholds were documented on the
page, which is itself a gap finding.)*

**Why it matters.** `raw/convergence_stopping.md` covers the stopping question and
`raw/fleet_failure_modes.md` covers what goes wrong at scale; this is a **cheap, concrete detector** that
neither had: the repeated `(tool, args, result)` triple is a signature a code path can compute with no model
in the loop. **The default-off flag is the honest half of the finding** — the maintainers shipped it
unenabled, which is weak evidence it is noisy or immature (test-plan item 4).

**Cost: S (hours) for the depth/breadth bounds, which we should simply adopt; the loop detector is M (~2–3
days) and should wait.** *(derived — inputs: the two mechanisms; our parent/child composition already has an
implicit depth of 2–3.)* **Lands on:** `Phase: Workflow Decomposition` for the bounds; the loop detector is
not currently sequenceable and is listed in §6 as deferred.

### 4.5 — Inference-proxying: the inverse topology, and a real option we had not considered `RANK 5`

**This is the win, and it is written as a win.** Our design says: *work runs where the subscription lives,
because that is the only place it can.*[^problem-statement] OpenClaw ships a shape where **that is not the
only place it can**. A cloud worker gets the workspace and the agent loop; the Gateway keeps the credential
and **proxies the model calls back**: *"Model calls are proxied back through the Gateway, so provider
credentials never leave your machine, and prompt caching keeps working because the provider sees one
continuous stream"*; *"No standing model, forge, or cloud credentials on the box"*; and the box is
disposable — *"When the work is done (or the box dies), the machine is discarded."*[^cloudworkers]

**Why this matters, honestly, in both directions.**

- **For us:** `problem-statement.md` carries an explicitly *"unresolved"* cost — pinning *all* work to the
  credential-holding machine gives up failover even for work that needs no credential and no local
  repo.[^problem-statement] **Inference-proxying is a third answer to that trade-off that neither the pinned
  model nor the shared-queue model offers:** the compute is fungible, the credential is not, and the
  boundary between them is a proxy rather than a placement rule.
- **Against us adopting it:** it puts a **network hop with the credential on it** between the work and the
  model, which is precisely the property `problem-statement.md` objects to in centralized platforms — with
  the mitigating difference that the proxy is the *user's own* Gateway rather than a vendor's. And it is
  unverified whether Anthropic's *"ordinary, individual usage"* language[^anthropic-legal] survives a
  proxied CLI session originating from a leased cloud box; **OpenClaw's docs do not address that, and I am
  not guessing.** *(gap, method: searched `docs/gateway/cloud-workers.md`, `docs/providers/anthropic.md`,
  `docs/reference/api-usage-costs.md` — none discusses provider terms for proxied cloud-worker inference.)*

**Cost: L, and it is a design question before it is a build.** *(derived — inputs: the cloud-worker doc; the
fact that we have no proxy tier and `system-overview.md` lists the server tier as not built.)* **Lands on:**
not a build item. It is an input to the open ruling recorded in `problem-statement.md` § *One honest cost of
claim #2*, and belongs in `raw/dedicated_edge_routing.md`'s next refresh.

### 4.6 — A generated, versioned control-plane protocol `RANK 6`

**What it is.** The Gateway's WS API is schema-first: *"Schemas and models are generated from TypeBox
definitions"*, frames are *"Request: `{type:"req", id, method, params, traceparent?}`; Response: `{type:"res",
id, ok, payload|error}`; Event: `{type:"event", event, payload, seq?, stateVersion?}`"*, the Gateway
*"Validates inbound frames against JSON Schema"*, and versions are negotiated — *"Clients send `minProtocol`
+ `maxProtocol`… current clients and servers run protocol v4"*.[^protocol][^architecture] Every client — the
macOS app, CLI, web UI, automations — is generated from the same definitions. *(reduced-confidence
first-party — summarizing fetch; the schema export names and frame shapes were returned as quoted spans.)*

**Why it matters.** `system-overview.md` records that *"a parent still routes on a parsed token rather than a
structured result"* and lists typed handoff as **not built**.[^system-overview] OpenClaw's answer is not a
message format — it is **one source of truth that generates the types, plus a negotiated protocol version so
a stale client fails loudly instead of silently misparsing**. When our edges are on separate machines running
separately-updated code, the version-negotiation half becomes the load-bearing half. **We are currently
designing the payload and not the compatibility story.**

**Cost: M (~2–4 days) for a versioned typed result contract; it is an interface decision, not a feature.**
*(derived — inputs: the protocol doc; `system-overview.md` § What is not built; Temporal's data-converter
seam as the natural home.)* **Lands on:** `Phase: Temporal Integration` — the workflow/activity result types,
and the `Phase: Workflow Decomposition` parent→child contract.

### Not taken, and why — stated so a reader knows they were considered

- **Self-learning.** *"Self-learning turns corrections and successful work into reusable skills"*, *"The
  default mode is `auto`"*, and *"Every autonomous capture is authored by a model reviewing real
  evidence"*.[^selflearn] **This is a system that modifies itself without a human ruling.**
  `system-overview.md` states the opposite position as a design commitment: *"The system observes itself and
  proposes; it does not modify itself."*[^system-overview] **Rejected on principle, not on cost** — and it is
  a genuinely interesting counter-position that §5(f) revisits.
- **Standing orders.** *"Standing orders grant your agent **permanent operating authority** for defined
  programs"*, loaded from workspace bootstrap files each session.[^standing] This is prompt-level policy,
  which we already have as `config/rules/`. No delta.
- **The channel/binding layer.** Real engineering, and irrelevant to a backbone that has no messaging
  surface.

## 5. Honest boundary analysis — the case against this paper

**(a) Documentation only. Nothing was executed and no TypeScript was read.** Every behavioural claim in §2 is
inferred from prose. A documented three-attempt budget is not an observed one; a documented tombstone is not
a row anyone saw. **This is the single largest weakness**, and test-plan items 1 and 4 are its direct tests.
Specifically unverified: whether the charged budget is actually charged on failure-to-start, whether the
two-hour horizon is the shipped default, and whether loop detection is usable when enabled.

**(b) A measured hallucination on this repo's own documents, and it is the reason §4.1 is quoted the way it
is.** A first, summarizing fetch of `docs/providers/claude-max-api-proxy.md` returned two spans as
quotations: *"Anthropic has blocked some subscription usage outside Claude Code in the past"* and
*"Technical compatibility only, not an officially sanctioned path"*. **Both were extremely convenient for
this paper's thesis.** A second fetch of the same page requesting fenced verbatim reproduction of its
*"Why use this"*, *"How it works"* and *"Notes"* sections returned neither span; what those sections actually
contain is *"It is not an unlimited flat-rate path — it inherits Claude Code's usage limits"* and
*"Inherits Claude Code's `claude -p` billing, usage-credit, and rate-limit behavior."*[^proxy] **The two
spans are therefore treated as UNVERIFIED and are used nowhere in this paper's argument.** They may exist
elsewhere on the page; I did not reproduce the whole file and do not claim they are fabricated. What I claim
is narrower and sufficient: **a summarizing fetch of a raw first-party file produced quotation-marked text
that a verbatim fetch of the named sections of that same file did not contain.** Raw-over-rendered does not
protect against this; only asking for reproduction does. Every load-bearing quote in §4.1 came from a fenced
reproduction for exactly this reason, and every span elsewhere in the paper that did not is marked
reduced-confidence in-place.

**(c) Counts.** Directory enumerations here each come from **one** git-trees fetch and are **corroborated by
nothing**, so they are stated as floors and nothing rests on them: at least 68 provider pages, at least 51
gateway docs, at least 67 tool docs, at least 57 concept docs, at least five agent runtimes. The repository
metadata figures (385,333 stars and the rest) are **counts a source STATES**, quoted from the GitHub API
JSON — they inherit the API's reliability, not an enumeration's. The one number this paper leans on
argumentatively is the star count, and it leans lightly: it establishes *scale of adoption*, which is a
popularity signal and not a production-validation signal (see (e)).

**(d) The strongest case against §4.2 is that Temporal may already dictate the answer.** I asserted the
charged budget must live in workflow state rather than in an activity retry policy — that is **derived from
the shape of the requirement, not from Temporal documentation read for this paper.** `raw/temporal.md` is
past its revalidation window and was not re-read here.[^temporal-paper] If Temporal's retry policy already
persists attempt counts across worker restarts in the way required, §4.2's cost line is wrong in our favour
and the item shrinks to two policy constants. **Test-plan item 3 settles it, and it is cheap.**

**(e) 385,333 stars is adoption, not validation — and the governance context is genuinely unusual.** The
project was created 2025-11-24 and has 5,503 open issues.[^gh-api] `VISION.md` states the current focus is
*"Security and safe defaults"*, *"Bug fixes and stability"* and *"Setup reliability and first-run
UX"*[^vision] — a stability-first posture, which is a positive signal, but also one a project adopts *after*
growing faster than it hardened. **Consequence for this paper: the lessons mined are the ones expressed as
policy constants and stated rules (§4.2, §4.3) rather than feature bullets.** I did not investigate
maintainership, funding or the project's history under prior names; a widely-reported founder departure
surfaced in search results and is **deliberately excluded** because no first-party source was fetched for it.

**(f) The case against my own §3.4, and it is a real one.** I recorded OpenClaw's refusal to merge
*"manager-of-managers / nested planner trees"*[^vision] as a place where we bet differently. **A reader is
entitled to ask which of us is right.** The largest project in the category looked at agent hierarchies and
declined them as a default; we have made layered composition the thesis.[^problem-statement] The honest
statement is that this is **an open empirical question that `raw/decide_only_disposition.md` — commissioned
in this same cycle — exists to test**, and OpenClaw's position is a data point against us that I am
recording rather than explaining away. The same applies to §4.6's "not taken" ruling on self-learning: a
385k-star project ships model-authored self-modification **on by default**, and our rule against it is a
principle we have not tested.

**(g) Named coverage gaps** *(with method, per §3)*. Located via git-trees enumeration and **deliberately not
fetched** for budget: `docs/specs/`, `docs/plan/`, `docs/refactor/`, `docs/maturity/`, `docs/reference/`
beyond `api-usage-costs.md`, `docs/plugins/`, `docs/clawhub/`, `docs/channels/`, `docs/install/`,
`docs/security/`, `docs/gateway/security/`, `docs/gateway/pairing.md`, `docs/gateway/operator-scopes.md`,
`docs/gateway/sandboxing.md`, `docs/gateway/multiple-gateways.md`, `docs/concepts/memory-architecture.md`,
`docs/concepts/queue.md`, `docs/concepts/retry.md`, `docs/concepts/session-state.md`, `AGENTS.md`,
`REPORT.md`, `THIRD_PARTY_NOTICES.md`, and the `apps/`, `packages/`, `src/`, `extensions/`, `skills/`,
`security/` and `qa/` trees. **Any claim of absence in this paper is scoped to the ~22 OpenClaw documents
actually fetched** and must not be read as a claim about the repository. The one absence claim that matters —
no documented consumer-OAuth extraction path — is scoped in §4.1(d) to a named list of six documents plus two
tree listings plus a changelog probe.

**(h) The Kubernetes absence is a scoped negative, not a claim.** I searched the `deploy` tree (one file:
`fly.private.toml`), the repository root tree, and `docs/vps.md`. **I did not fetch `docs/install/`**, which
plausibly contains container and orchestration guidance. The correct statement is *"no Kubernetes deployment
documentation was found in the three surfaces searched"*, and nothing in this paper depends on it.

**(i) Recency risk is asymmetric and one external dependency is explicitly unstable.** The repo was pushed
the day of the sweep.[^gh-api] §4.1's billing finding rests on a state Anthropic itself calls a **pause**,
and OpenClaw's own docs warn *"Anthropic can change Claude Code billing and rate-limit behavior without an
OpenClaw release."*[^anthropic][^anthropic-sdk-plan] **§4.1 could be false three weeks from now; §4.2 and
§4.3 will still be true in a year.**

## 6. What this provides — the enumerated, plannable list

For the master-planning pass. Each row is sequenceable; costs are `derived` and their inputs are named in §4.

| # | Item | Where it lands | Cost | Hard dependency |
|---|---|---|---|---|
| 1 | **Recovery policy for `claude_cli`** — a durable **charged** attempt budget in workflow state, a **staleness horizon** past which an interrupted run is finalized not resumed, and a **`wedged` terminal state** that is surfaced rather than retried | `Phase: Temporal Integration`, **before** workers are written | **S** — ~1 day design | `claude_cli` activity design; verify against Temporal retry semantics (test-plan 3) |
| 2 | **Do-not-resume list** — work owned by another recovery path, work whose tail cannot be safely continued (gets an explicit notice, never a silent re-run), and work never admitted during drain | same as #1 | **S** — hours, part of #1 | sequence with #1 |
| 3 | **Credential rule: discover, never copy** — an edge resolves a credential in scope at runtime; OAuth refresh material is never propagated between edges (single-use/rotation hazard); read-only paths use file-backed credentials only | Standards-amendment **candidate** for the worker/edge standard — routed per Research Standard §7 by a planning run, never from here | **S** — hours | none |
| 4 | **Sub-agent depth and breadth bounds** — an explicit max nesting depth and max concurrent children, as constants rather than emergent behaviour | `Phase: Workflow Decomposition` | **S** — hours | none |
| 5 | **Versioned typed result contract** — one source of truth generating the types, plus `minProtocol`/`maxProtocol`-style negotiation so a stale edge fails loudly | `Phase: Temporal Integration` result types; `Phase: Workflow Decomposition` parent→child | **M** — 2–4 days | worker contract |
| 6 | **Loop detector on the `(tool, args, result)` triple** | **Deferred** — the source ships it default-off; revisit after test-plan 4 | **M** — 2–3 days | evidence it is not noisy |
| 7 | **Inference-proxying as a third answer to the pinning trade-off** — compute fungible, credential not, proxy in between | **Not a build item.** Input to the open ruling in `problem-statement.md` § *One honest cost of claim #2*; feed `raw/dedicated_edge_routing.md` | **L** if ever built | server tier (**not built**) |
| — | *Evidence, no cost:* subscription-auth-at-the-edge is **load-bearing for a 385k-star project** and Anthropic's current first-party position is that `claude -p` still draws from subscription limits | Strengthens `problem-statement.md` § *Affordability* | 0 | — |
| — | *Correction candidate:* `anthropic_tos_and_enterprise.md` §3.3's February-2026 OAuth-crackdown line should be re-scoped — no first-party corroboration was found, the one fetched article is self-contradictory, and Anthropic's own June-2026 article says the change is **paused** | `raw/anthropic_tos_and_enterprise.md` (its own next refresh; **this paper does not edit it**) | 0 | — |
| — | *Claim refinement:* differentiator #4 (domain generality) is **weaker still.** Paperclip generalised its execution boundary; OpenClaw was never code-shaped at all. What survives is not generality but **generality plus durable multi-operator orchestration** | `problem-statement.md` #4, human-ratified path | 0 | — |

## 7. The roadmap item's answer

**Verdict: CREATE the item, and create it already-answered — `MINE AND DISCARD`.**

`roadmap.md` § *Tools to Evaluate* currently holds two entries: the Paperclip line (already resolved to
ASSESSED) and Claude Agent SDK.[^roadmap] **There is no OpenClaw item.** There should be one, and the reason
is not completeness — it is that **a future reader who encounters the 385k-star project in this category and
finds no trace of it in our planning will reasonably conclude we never looked.** The Paperclip entry's
current form is the model: a struck-through gate, a verdict, a pointer to the assessment, and no open
evaluation.

**The item should say, in substance:** *OpenClaw — ASSESSED 2026-08-06, architecture rejected on altitude.
Single-operator, single-host personal assistant; one Gateway per host; durability hand-rolled on SQLite;
its own security policy states it is not a multi-tenant boundary. Not a competitor to the backbone and not
adoptable as one. **Its crash-recovery POLICY is the most directly reusable artifact this pool has found for
`Phase: Temporal Integration`** — see the assessment. Its Anthropic auth story independently validates
host-local `claude -p` reuse. No further evaluation gate.*

**Writing that line is a PLANNING action, not a research one.** Per Research Standard §7 this run surfaces
the candidate and writes nothing outside `research/`; the synthesis carries it, the reviewer triages, and a
planning run applies it.[^research-standard]

**One thing the item must NOT say.** It must not describe OpenClaw as an orchestrator or a competitor to
this repo. It is a personal assistant that happens to be able to drive Claude Code. **The category
resemblance is superficial and the altitude difference is total** — and mis-stating that is exactly the
failure the Paperclip item made in its first form.

## 8. Citations

**First-party — OpenClaw repository metadata and structure (GitHub REST API)**

[^gh-api]: GitHub REST API, repo metadata for `openclaw/openclaw` (JSON): `default_branch: "main"`,
  `language: "TypeScript"`, `license.spdx_id: "NOASSERTION"`, `stargazers_count: 385333`,
  `forks_count: 81008`, `open_issues_count: 5503`, `subscribers_count: 1759`,
  `created_at: "2025-11-24T10:16:47Z"`, `pushed_at: "2026-08-06T12:24:59Z"`,
  `homepage: "https://openclaw.ai"`, `archived: false`, `fork: false`. Fetched 2026-08-06.
  https://api.github.com/repos/openclaw/openclaw
[^tree-root]: GitHub REST *git trees* API, `main` (repository root) — enumerated; includes `Dockerfile`,
  `docker-compose.yml`, `fly.toml`, `render.yaml`, `LICENSE`, `VISION.md`, `SECURITY.md`, `CHANGELOG.md`,
  `appcast.xml`, and the `apps`, `packages`, `src`, `extensions`, `skills`, `security`, `qa`, `deploy`,
  `docs` trees. Fetched 2026-08-06.
  https://api.github.com/repos/openclaw/openclaw/git/trees/main
[^tree-deploy]: GitHub REST *git trees* API, `main:deploy` — **one entry, `fly.private.toml`**. Fetched
  2026-08-06. https://api.github.com/repos/openclaw/openclaw/git/trees/main:deploy
[^toolstree]: GitHub REST *git trees* API, `main:docs/tools` — enumerated; **at least 67 blobs** including
  `browser.md`, `exec.md`, `code-execution.md`, `media-overview.md`, `image-generation.md`,
  `video-generation.md`, `music-generation.md`, `screen.md`, `pdf.md`, `mcp.md`, `skills.md`,
  `subagents.md`, `swarm.md`, `self-learning.md`, `loop-detection.md`, `clawhub.md`. Count stated as a
  floor (§5(c)). Fetched 2026-08-06.
  https://api.github.com/repos/openclaw/openclaw/git/trees/main:docs/tools

*(Additional trees enumerated and used only for structure and the §5(g) scoping list: `main:docs`,
`main:docs/providers` — at least 68 blobs; `main:docs/gateway` — at least 51; `main:docs/concepts` — at least
57; `main:docs/nodes` — at least 12; `main:docs/automation` — at least 13; `main:docs/announcements` — one
blob, `bluebubbles-imessage.md`. All floors, all single fetches, none load-bearing.)*

**First-party — OpenClaw raw documents retrieved as FENCED VERBATIM reproductions (strongest class here)**

[^anthropic]: `docs/providers/anthropic.md` (raw, `main`) — §§ *Usage and cost tracking* and *Getting started*
  reproduced verbatim, including the `<Warning>` block carrying the June 15 2026 pause language, the
  *"same host as the Claude CLI login"* requirement, the `claude setup-token` / `sk-ant-oat01-` instruction,
  and the *"Billing and `claude -p`"* bullets. Also the *"Claude sessions across computers"* section
  (`agent.cli.claude.run.v1`, node continuation v1). Fetched 2026-08-06.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/providers/anthropic.md
[^authsem]: `docs/auth-credential-semantics.md` (raw) — §§ *External CLI credential discovery* and *Agent copy
  portability* reproduced verbatim.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/auth-credential-semantics.md
[^usagecosts]: `docs/reference/api-usage-costs.md` (raw) — the *"Anthropic has confirmed that Claude CLI reuse
  (including `claude -p`) is a sanctioned integration pattern unless it publishes a new policy"* passage
  reproduced verbatim. **A first-party OpenClaw claim about Anthropic, not an Anthropic statement.**
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/reference/api-usage-costs.md
[^proxy]: `docs/providers/claude-max-api-proxy.md` (raw) — §§ *Why use this*, *How it works*, *Notes*
  reproduced verbatim. **See §5(b): an earlier summarizing fetch of this page returned two quotation-marked
  spans that the verbatim reproduction of these three sections did not contain; those spans are treated as
  unverified and are used nowhere.**
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/providers/claude-max-api-proxy.md
[^license]: `LICENSE` (raw) — first lines *"MIT License"* / *"Copyright (c) 2026 OpenClaw Foundation"*.
  Note the discrepancy against the API's `NOASSERTION`; unresolved (§1).
  https://raw.githubusercontent.com/openclaw/openclaw/main/LICENSE

**First-party — OpenClaw raw documents retrieved through a SUMMARIZING fetch (reduced confidence; quoted
spans only, never reconstructed)**

[^architecture]: `docs/concepts/architecture.md` (raw).
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/architecture.md
[^restart]: `docs/gateway/restart-recovery.md` (raw) — the survives-a-restart table, automatic resume,
  charged budget, 2-hour finalize horizon, tombstoning, and the *"What is not resumed"* list.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/restart-recovery.md
[^cloudworkers]: `docs/gateway/cloud-workers.md` (raw).
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/cloud-workers.md
[^multitenant]: `docs/gateway/multi-tenant-hosting.md` (raw).
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/multi-tenant-hosting.md
[^security]: `SECURITY.md` (raw, repo root) — *"Operator Trust Model"*, *"One-User Trust Model"*,
  *"Deployment Assumptions"* sections.
  https://raw.githubusercontent.com/openclaw/openclaw/main/SECURITY.md
[^vision]: `VISION.md` (raw, repo root) — purpose, next priorities, and *"What We Will Not Merge (For Now)"*.
  *(directional — a stated non-goal, not a shipped constraint.)*
  https://raw.githubusercontent.com/openclaw/openclaw/main/VISION.md
[^network]: `docs/network.md` (raw) — the *"Core model"* section into which
  `docs/gateway/network-model.md` redirects (that page's entire content is the redirect notice).
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/network.md
[^protocol]: `docs/gateway/protocol.md` (raw) — TypeBox-generated schemas, frame shapes, protocol v4
  negotiation.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/protocol.md
[^secrets]: `docs/gateway/secrets.md` (raw) — SecretRef contract, sentinel-until-egress, no plaintext
  rollback backups.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/secrets.md
[^clibackends]: `docs/gateway/cli-backends.md` (raw) — `claude-cli` and `google-gemini-cli`, PATH
  requirement, same-host login requirement, session resume, the no-tool-injection limitation.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/cli-backends.md
[^runtimes]: `docs/concepts/agent-runtimes.md` (raw) — runtime definition, selection, embedded vs CLI-backed.
  Runtime count stated as a floor (§5(c)).
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/agent-runtimes.md
[^multiagent]: `docs/concepts/multi-agent.md` (raw) — isolated agents in one Gateway process; bindings.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/multi-agent.md
[^taskflow]: `docs/automation/taskflow.md` (raw) — durable flow records, JSON step state, revision counter,
  plugin-code controller. `docs/automation/clawflow.md` is a redirect to it.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/automation/taskflow.md
[^subagents]: `docs/tools/subagents.md` (raw) — `sessions_spawn`, isolated-by-default context, prose
  completion payload, depth 5 / children 5 bounds.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/subagents.md
[^loopdetect]: `docs/tools/loop-detection.md` (raw) — `(tool, args, result)` triple, warn-or-block,
  `enabled` default `false`, **no numeric thresholds documented**.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/loop-detection.md
[^selflearn]: `docs/tools/self-learning.md` (raw) — auto mode default, skills as the durable unit,
  security scan at apply.
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/tools/self-learning.md
[^standing]: `docs/automation/standing-orders.md` (raw).
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/automation/standing-orders.md
[^vps]: `docs/vps.md` (raw) — `openclaw onboard --install-daemon` / systemd user unit; cloud host coverage;
  no Kubernetes on this page (§5(h) scopes the negative).
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/vps.md
[^ocoauth]: `docs/concepts/oauth.md` (raw) — OAuth "subscription auth" support named for OpenAI Codex
  (ChatGPT OAuth) and Anthropic Claude CLI reuse; token storage under
  `~/.openclaw/agents/<agentId>/agent/openclaw-agent.sqlite`; external CLI credentials re-read rather than
  spending a copied refresh token. *(Consulted for §4.1(d)'s search method.)*
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/concepts/oauth.md
[^ocauthdoc]: `docs/gateway/authentication.md` (raw) — provider-credential authentication routes; points to
  `/gateway/configuration` for gateway-connection auth. *(Consulted for §4.1(d)'s search method.)*
  https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/authentication.md
[^changelog]: `CHANGELOG.md` (raw) — probed for the terms *Anthropic / OAuth / subscription / Claude CLI /
  setup-token*; the returned portion's most recent entry is headed **Unreleased** and the matching lines are
  routine maintenance (OAuth callback loopback binding, Claude CLI context budgets, warm sessions). **No
  entry describing removal of a consumer-OAuth path was returned.** A single probe of a large file is a weak
  negative and is reported as such in §4.1(d).
  https://raw.githubusercontent.com/openclaw/openclaw/main/CHANGELOG.md

**First-party — Anthropic**

[^anthropic-legal]: Anthropic, *Claude Code — Legal and compliance*, § *Usage policy* → *Acceptable use* and
  *Authentication and credential use*. Returned as complete verbatim markdown. Fetched 2026-08-06.
  **Contains no dates and no mention of third-party enforcement events.**
  https://code.claude.com/docs/en/legal-and-compliance
[^anthropic-sdk-plan]: Anthropic Support, *"Use the Claude Agent SDK with your Claude plan"* — **last updated
  June 16, 2026**; carries the pause notice. Fetched 2026-08-06. *(Retrieved through a summarizing fetch;
  the pause sentence was returned as a quotation and is corroborated by OpenClaw's independent restatement
  of the same update.[^anthropic])*
  https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
[^anthropic-promax]: Anthropic Support, *"Use Claude Code with your Pro or Max plan"* — last updated
  June 11, 2026. Fetched 2026-08-06 and reported as containing **no mention of third-party tools, OAuth, or
  April 2026**; cited only as a negative-search surface for §4.1(d).
  https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan

**Third-party (reduced confidence — rendered page, and internally inconsistent)**

[^register]: Thomas Claburn, *"Anthropic closes door on subscription use of OpenClaw"*, The Register,
  published 2026-04-06. Cited **only** in §4.1(d), and only to record that the reporting exists and
  contradicts itself on its own date. https://www.theregister.com/2026/04/06/anthropic_closes_door_on_subscription/

**This repo**

[^roadmap]: `docs/development/roadmap.md` § *Tools to Evaluate* — two entries, neither OpenClaw.
[^problem-statement]: `docs/standards/architecture/problem-statement.md`.
[^system-overview]: `docs/standards/architecture/system-overview.md`.
[^research-standard]: `docs/standards/research/research_standard.md` §3 (paper contract, sourcing rules) and
  §7 (consumption — a research run surfaces candidates and writes nothing outside `research/`).
[^paperclip]: `docs/standards/architecture/research/raw/paperclip_assessment.md` (last validated 2026-08-04,
  Critic: PASS-WITH-FIXES) — §4.5 records `openclaw_gateway` among Paperclip's built-in adapters; §4.6 is
  the prior subscription-at-the-edge correction this paper extends.
[^anthropic-tos]: `docs/standards/architecture/research/raw/anthropic_tos_and_enterprise.md` (last validated
  2026-07-24) — §3.3, the February 2026 OAuth-crackdown line this paper was commissioned to run down, and
  the June 15 2026 pause note this paper corroborates at first-party.
[^temporal-paper]: `docs/standards/architecture/research/raw/temporal.md` (last validated 2026-08-05) and
  `raw/python_sdk_long_activities.md` (2026-08-03). **Neither was re-read for this paper** — see §5(d).

## 9. Test plan — what research cannot settle

Ordered by how much each would change a decision.

1. **Run OpenClaw locally with the `claude-cli` runtime and NO `ANTHROPIC_API_KEY`, then kill the gateway
   mid-turn.** Confirm the interrupted session is re-dispatched on boot, count how many attempts are
   actually charged, and check whether a session that keeps failing reaches a visible `wedged`/tombstoned
   state. **Settles §4.2** — the paper's highest-value finding, currently sourced from prose alone. Budget:
   ~2 hours.
2. **Verify the subscription path end to end.** With a Claude Code login present and no API key, drive one
   OpenClaw turn and confirm it consumed subscription usage rather than failing or billing API rates.
   **Settles §4.1(a) behaviourally** and is the single most decision-relevant experiment in the paper,
   because `problem-statement.md`'s economic premise rests on it. Budget: ~1 hour.
3. **Read Temporal's Python SDK retry/attempt semantics for the specific question §5(d) raises:** does an
   activity's attempt count survive a *worker process restart*, or only an in-worker failure? If it
   survives, §6 item 1 shrinks to two constants and a state. **Cheapest item here; do it first if the
   critic or the planner is budget-constrained.**
4. **Enable OpenClaw's loop detection and run a deliberately looping task.** Does it fire, and how often does
   it fire wrongly? **Settles whether §6 item 6 should stay deferred** — the source shipping it default-off
   is the only evidence we have about its quality.
5. **Fetch the §5(g) documents that bear on absence claims, `docs/install/` and `docs/gateway/pairing.md`
   first.** **Settles §5(h)** (the Kubernetes negative) and would strengthen or falsify §3's dispatch-model
   reading. The prior papers in this pool have twice had absence claims falsified by cited-but-unread
   sources.
6. **Establish, from a first-party Anthropic surface, whether an April 2026 third-party enforcement event
   occurred and what its current force is.** Candidate surfaces not yet tried: Anthropic's support-article
   index, the Claude Code changelog, and the consumer-terms revision history. **Settles §4.1(d)**, which is
   the one place this paper leaves a load-bearing question open. **Research may be able to settle this — it
   is listed here because I did not, not because it is unsettleable.**
7. **Re-sweep in three weeks.** Tripwires: any change to Anthropic's Agent-SDK pause (§4.1(d) inverts); any
   OpenClaw release that adds a distributed or multi-operator mode (§3.1 and §3.3 go stale); and any change
   to `docs/gateway/restart-recovery.md`'s bounds, which are the constants §6 item 1 copies.
