# Hermes — Identified, Architecture Rejected as a Backbone, Eight Things Mined

```
Topic:          "Hermes" is an overloaded name. WHICH Hermes is the comparator a product-research
                dispatch means, and once identified: what is its durability approach, domain
                generality, dispatch/worker model, credential locality, deployment shape and trust
                model — and what is worth taking regardless of whether its architecture fits?
Feeds:          docs/development/roadmap.md § "Tools to Evaluate" — the comparator set (answered in
                §8, including a recommendation to SPLIT that list); and
                problem-statement.md § "The nearest neighbor" — whether that designation still holds
                (it does; §3 says why, and why Hermes was never a candidate for it)
Last validated: 2026-08-06
Revalidate:     high — 3 weeks   (tighter than the pool's other comparator papers: the single fact
                that would most change this paper's recommendations — whether an external CLI worker
                lane lands — is an OPEN issue in the subject's own tracker (§5.3, §10 item 8), and
                the repo was pushed on the day of this sweep)
Confidence:     DEFINITIVE at the documentation level for every axis: the subject's docs are raw
                first-party markdown in its own repo (`website/docs/**`) fetched from
                raw.githubusercontent.com, plus GitHub/HuggingFace JSON APIs for identification.
                DEFINITIVE for the IDENTIFICATION chain (§1.1) — four candidates enumerated, three
                excluded against first-party metadata, and the surviving one independently
                corroborated by a THIRD party's adapter registry.
                REDUCED for everything sourced from `features/kanban.md`: two fetches of that one
                file returned a prose-summarized version and a re-wrapped version, so its spans are
                quoted only where both fetches agreed and are marked in place. Three later
                independent fetches (2026-08-06) could NOT reproduce the summarization — so this
                marking is now scoped to VERBATIM/PROVENANCE status; the substance of those spans
                is corroborated by three later clean fetches. Ruling and reasoning in §6(b′).
                DERIVED for the architecture verdict (§4), the category split (§3), every cost
                estimate (§5, §7), and the claim refinements in §8 — each names its inputs.
                UNVERIFIED at the behavioural level: nothing was executed, no Python was read.
                COUNTS: no document count is asserted for the docs tree (the enumerating fetch was
                truncated mid-list — §6(c)); the HuggingFace model list is stated as a FLOOR; the
                third-party adapter list is stated as a FLOOR; repository counters are quoted as
                values the API STATES, not values this paper measured.
                A MEASURED NEW SOURCING HAZARD is reported in §6(b): the fetch layer declared a
                125-character quote ceiling and REFUSED one full-document reproduction while
                granting others in the same session. No long block in this paper is presented as
                byte-exact, and every quoted span is kept short and distinctive as a result.
Critic:         PASS-WITH-FIXES — 2026-08-06. Four verification rounds. Rounds 1-2 verified the body
                and are its evidence; rounds 3-4 did no new checking of the body's research claims.
                Round 3 corrected bookkeeping in this header block AND one enumeration in §6(h);
                round 4 corrected this line only.
                ROUND 1 (PASS): an independent read-only pass re-fetched the 23 EXTERNAL sources
                cited in §9 — 17 Hermes raw-markdown fetches (16 distinct files; `features/kanban.md`
                is fetched twice, once per URL form), 4 GitHub REST calls (3 repository-metadata
                JSON, 1 git-trees listing), the HuggingFace models API, and the third-party adapter
                doc — and found none fabricated and none miscited. The other 6 of §9's 29 entries
                are documents in THIS repository; no external-re-fetch claim is made for them. All
                29 inline footnote tags reconcile 1:1 with the §9 list, no orphan on either side.
                Every high-risk quoted span was re-fetched and matched character-for-character —
                the single-host and PID-locality clauses in §4.1, the managed-scope and
                tenancy-boundary spans in §2.5, the credentials auto-seed, and the judge contract
                and liveness guards in §5 — each confirmed DOCUMENTED rather than inferred. The
                §1.1 identification chain was re-derived from direct API calls. Confidence marks
                were judged correctly calibrated, with the RANK-1 quota-headroom item correctly
                held as DERIVED rather than as a shipped Hermes capability. §6(h)'s
                unfetched-document list was spot-checked against a live git-trees listing (real
                paths), and §6(c)'s truncation reproduced. One non-blocking observation on
                `features/kanban.md` was raised; it is ruled on in §6(b′), and the REDUCED marking
                is retained deliberately.
                ROUND 2: a narrow re-verification of the then-new §6(b′) plus the footnote
                reconciliation. §6(b′) was judged sound — correctly attributed, accurately scoped,
                not overclaimed — and the 29-tag reconciliation was independently re-enumerated and
                held. That pass also ran its own fetch of the plain `main` kanban URL, which came
                back clean; it is recorded as the fourth observation in §6(b′).
                ROUND 3: four edits in three places — this line, the Confidence block above, and the
                body at §6(h). (1) THIS line's source-type breakdown did not survive enumeration: the
                raw-markdown bucket was overstated by one, and the buckets silently omitted the
                git-trees call and the six this-repo citations while sitting beside the total 29.
                Re-enumerated from §9 and now reconciling: 17 + 4 + 1 + 1 = 23 external, plus 6
                this-repo = 29. (2) The kanban ruling was pointed at §6(b) when the ruling is in
                §6(b′); both references to that ruling — the Confidence block's and this line's
                ROUND 1 entry — now resolve to §6(b′). (3) The Confidence block's kanban paragraph was
                brought to the post-round-2 state: THREE later clean fetches, not two. (4) §6(h)
                replaced an approximate "~18" with an enumerated 16 distinct documents / 17
                raw-markdown fetches; the absence claims there are unchanged in substance, and that
                edit carries its own in-place annotation in §6(h). Round 3 did NOT re-verify the
                body's research claims — rounds 1 and 2 remain their evidence — but it DID edit the
                body at (4). Those are different claims and an earlier version of this line conflated
                them.
                ROUND 4 (nothing in the body changed): a read-only pass re-enumerated §9 and
                confirmed the round-3 figures (17 raw-markdown over 16 distinct files, 4 GitHub REST
                including the git-trees call, 1 HuggingFace, 1 adapter doc, 6 this-repo, 29 total),
                re-resolved the §6(b′) pointer, re-counted §6(b′)'s four observations against its
                header, and endorsed the §6(h) correction on the merits. Its one finding was against
                the ROUND 3 entry itself: that entry described its own scope as confined to this line
                and named two of the four edits, so a reader could not have reconstructed round 3
                from it — which is the entry's only job. Rewritten above.
                NOT VERIFIED: no version history was available to the pass that rewrote the ROUND 3
                entry, so the edit list is reconstructed from in-place evidence (§6(h)'s own
                annotation; both pointers now reading §6(b′); the Confidence block's fetch counts
                matching §6(b′)'s post-round-2 observation set) plus the round-4 pass's report. Items
                (1) and (4) are self-evidencing in the text; the exact round in which (2) and (3)
                landed is attested, not diffed.
```

> ## Headline — the subject is **Hermes Agent** (`NousResearch/hermes-agent`), and the useful finding is a CATEGORY ERROR in the comparator set
>
> **Identification first, because it is the largest failure risk on this topic.** Four distinct things
> carry the name. The one a comparator dispatch means is **Hermes Agent**, an MIT-licensed Python
> personal-AI-agent runtime by Nous Research.[^gh-api] It is **not** the Hermes LLM *model family* from
> the same organisation,[^hf-api] and not Meta's Hermes JavaScript engine.[^fb-hermes] The chain that
> settles it is in §1.1 and ends outside the subject's own marketing: a third party's adapter registry
> ships `hermes_local` — *"Runs the local Hermes CLI"* — beside `claude_local` and `codex_local`.[^pc-adapters]
>
> **Test (a) — architecture as a BACKBONE: rejected, on one decisive ground plus three.** Its
> orchestration layer states its own limit: *"Kanban is deliberately single-host."*[^kanban][^kanban-raw]
> The task board is a local SQLite file, the dispatcher spawns workers on the same machine, and
> crash detection is by host-local PID.[^kanban-raw][^lanes] A federated destination cannot be built on a
> substrate whose crash detector cannot see the other machine. §4 states the other three.
>
> **But the rejection is scoped, and the scoping is the interesting part.** Hermes is not a rival
> backbone that loses to ours — **it is shaped like an EDGE**, and a third party already treats it as
> one.[^pc-adapters] *(derived — §3.)*
>
> **Test (b) — eight things worth taking, and RANK 1 unblocks a gap this pool has carried for two
> cycles.** `topics.md` records *"the quota-headroom view — per-edge rate-limit capacity as the scarce
> resource"* as not-yet-sequenceable.[^topics] Hermes ships the answer: **credential pools** with a
> per-error-class rotation policy, per-credential status and request counters, and cooldowns — plus a
> first-party warning that rotation costs one full-price pass over the context.[^cred-pools] §5.1.
>
> **Three claim refinements for `problem-statement.md`, all costing zero to adopt.** (1) A second
> independent product reads `~/.claude/.credentials.json` for subscription auth[^cred-pools] — the
> Paperclip correction now has two data points, not one.[^paperclip] (2) *"Per-user tools… cannot be
> orchestrated: nothing coordinates them, nothing survives a crash"*[^problem-statement] is **too
> strong** — Hermes is a per-user tool with a durable board, a crash-reaping dispatcher, a scheduler and
> a judged completion loop. The axis that actually survives is *cross-host* and *cross-trust-domain*,
> not orchestration as such. (3) Differentiator #1 **strengthens**: a third independent system documents
> its multi-tenancy as namespacing rather than a security boundary.[^kanban-raw][^managed-scope]

---

## 1. Primer

### 1.1 Identification — four candidates, one subject, and the chain that settles it

**This section is evidence, not scaffolding.** The dispatch is correct that "Hermes" is heavily
overloaded, and a mis-identified comparator would be worse than no paper.

**Search method.** GitHub REST repository API for candidate repositories; HuggingFace models API for
the model family; one web search used **only to locate** candidates (never cited as a source, per the
Research Standard's sourcing rules); `raw.githubusercontent.com` for every document; the GitHub git
trees API for structure; and the pool's own prior papers for ecosystem context. Where a candidate was
excluded, it was excluded against **first-party repository metadata**, not against recollection.

| # | Candidate | What it is, from first-party metadata | In scope? |
|---|---|---|---|
| 1 | **Hermes Agent** — `NousResearch/hermes-agent` | Python, MIT, description *"The agent that grows with you"*, homepage `hermes-agent.nousresearch.com`, default branch `main`, created 2025-07-22, pushed 2026-08-06[^gh-api] | **YES — assessed in full** |
| 2 | **Hermes / Nous-Hermes LLM family** — Nous Research | A model family. The HuggingFace models API returns `Hermes-4-405B`, `Hermes-4-70B`, `Hermes-4-14B`, `Hermes-4.3-36B`, `Hermes-3-Llama-3.1-70B`, `Nous-Hermes-2-SOLAR-10.7B`, `Redmond-Hermes-Coder` and others, every one `pipeline_tag: text-generation`[^hf-api] | **NO** — a set of model weights is not an orchestration comparator. Same organisation as #1, which is precisely why the confusion is easy |
| 3 | **Hermes (JavaScript engine)** — `facebook/hermes` | *"A JavaScript engine optimized for running React Native."*, JavaScript, MIT, created 2018-10-22[^fb-hermes] | **NO** — unrelated domain |
| 4 | **`hermes_local` / `hermes_gateway`** — adapter identifiers inside Paperclip | Not a product. Two entries in another product's built-in adapter registry[^pc-adapters] | **NO as a subject — decisive as EVIDENCE.** See below |

**Why #1 is the subject, stated as a chain rather than an assertion:**

1. The dispatch places Hermes beside OpenClaw in a comparator set whose existing members are
   agent-orchestration systems.[^topics] That rules out #2 and #3 on category.
2. Candidate #1 self-describes as an agent runtime — *"The self-improving AI agent built by Nous
   Research"*, with a terminal UI, a messaging gateway and 40+ tools.[^readme]
3. **The corroboration that matters is external.** Paperclip's built-in adapter registry lists
   **Hermes (`hermes_local`)** and **Hermes Gateway (`hermes_gateway`)** beside Claude Code
   (`claude_local`), Codex (`codex_local`), Gemini CLI (`gemini_local`), OpenCode (`opencode_local`),
   Cursor (`cursor`), Pi (`pi_local`), OpenClaw Gateway (`openclaw_gateway`), Process and HTTP —
   **at least eleven** built-ins.[^pc-adapters] It describes `hermes_local` as running *"the local
   Hermes CLI"* and `hermes_gateway` as calling *"an already-running Hermes API server"*.[^pc-adapters]
   A different vendor, shipping an integration, naming the same CLI, is identification that does not
   depend on the subject's own words. *(Count stated as a floor: this pool has previously measured
   this exact listing returning eleven entries to two fetches and twelve to a third.[^paperclip])*
4. Candidate #1 exposes an API server started by `hermes gateway`,[^api-server] which is what
   `hermes_gateway` would call. The two adapter identifiers map onto the subject's two documented
   entry points.

**A near-miss worth recording, because a later reader will hit it.** Candidate #1's GitHub topic list
includes `clawdbot`, `moltbot` and `openclaw`,[^gh-api] and its README documents `hermes claw migrate`
for importing an OpenClaw installation.[^readme] **These do not make Hermes and OpenClaw the same
project.** `openclaw/openclaw` is a separate live repository with its own metadata — different
creation date, different licence field (`NOASSERTION`), different homepage — pushed the same day as
Hermes.[^openclaw-api] They are **distinct subjects and the sibling paper on OpenClaw is not
duplicative**; the relationship is migration-source-and-destination, which is itself a competitive
signal. *(derived — inputs: both repositories' API metadata and the README's migration section.)*

### 1.2 What Hermes Agent is

An **assistant**, not a coding tool — and it says so in its shape rather than its slogans. One process
family gives you a terminal TUI (`hermes`), a messaging gateway spanning Telegram, Discord, Slack,
WhatsApp, Signal, Email and more, an OpenAI-compatible API server, ACP/IDE integration and batch
processing, all served by a single synchronous orchestration engine.[^readme][^architecture]

The repository API reports Python, MIT, default branch `main`, created 2025-07-22, and — as counters
that move continuously and are quoted as *values the API states*, not values this paper measured —
226,385 stars, 44,122 forks, 28,833 open issues and 862 watchers.[^gh-api] Its own architecture doc
states *"70+ registered tools across ~28 toolsets"* and *"25+ platform adapters"* — **the source's own
assertions, quoted as such, not directory enumerations performed here.**[^architecture]

The README's own framing of the differentiator is a learning loop: it *"creates skills from
experience, improves them during use"*, and *"It's not tied to your laptop"*.[^readme]

**Volatility note (Research Standard §3 mixed-volatility rule).** The header takes `high — 3 weeks`
because the **feature inventory** decays fast. The **architectural boundaries** — single-host kanban,
filesystem-permission enforcement of managed scope, credential-home locality — are far more durable; a
refresh may re-verify §5 and §2 first and treat §4 as slow-moving.

## 2. The specific model — how Hermes actually works

Seven mechanisms, each first-party.

**2.1 One long-lived gateway process is the whole server tier.** `hermes gateway` hosts the messaging
adapters, the cron scheduler, the kanban dispatcher and the optional API server; `hermes gateway
install` (or `sudo hermes gateway install --system`) registers it as a systemd/launchd
service.[^cron][^kanban][^api-server] There is no database server and no cluster: session state is
SQLite via `hermes_state.py` *"with FTS5 full-text search"*, with *"lineage tracking (parent/child
across compressions)"* and *"atomic writes with contention handling"*.[^architecture]

**2.2 Identity is a PROFILE, and a profile is a home directory.** A profile is *"a separate Hermes home
directory"* under `~/.hermes/profiles/<name>/`, carrying its own `config.yaml`, `SOUL.md`, `.env` (API
keys and bot tokens), session and memory databases, skills, cron jobs and gateway process.[^profiles]
Each profile can run its own gateway with its own bot token, installable as a separate service.[^profiles]
`hermes -p <name>` selects one.

**2.3 The durable work surface is a SQLite kanban board.** Tasks carry title, body, assignee, status
(`triage → todo → ready → running → blocked → done → archived`), an optional tenant namespace and an
optional idempotency key; links are parent→child dependency edges that auto-promote `todo→ready`;
workspaces are `scratch`, `dir:<path>` or `worktree`; a dispatcher loop (default 60 s) reclaims stale
claims, promotes ready tasks and spawns workers. *(This paragraph is sourced from a **summarizing**
fetch of `features/kanban.md` and is a paraphrase, not a quotation — §6(b).)*[^kanban] The lifecycle
ownership is stated crisply in the verbatim-grade companion document: *"Hermes Kanban owns lifecycle
truth"*, and *"Worker lanes execute work but never own that truth"*.[^lanes]

**2.4 Dispatch is address-by-name, not claim-and-contend.** *"A **worker lane** is a class of process
that the kanban dispatcher can route tasks to."*[^lanes] The dispatcher matches `task.assignee` against
a profile name and runs `hermes -p <assignee> chat -q <prompt>` inside the task's pinned workspace,
with a fixed environment contract: `HERMES_KANBAN_TASK`, `HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`,
`HERMES_KANBAN_WORKSPACES_ROOT`, `HERMES_KANBAN_WORKSPACE`, `HERMES_KANBAN_RUN_ID`,
`HERMES_KANBAN_CLAIM_LOCK` (`<host>:<pid>:<uuid>`), `HERMES_PROFILE`, `HERMES_TENANT`.[^lanes] Every
claim must end in exactly one of `kanban_complete`, `kanban_block`, or a failure reaped by the kernel
as `crashed` / `gave_up` / `timed_out`.[^lanes] Isolation of concurrent workers is **git worktrees** —
the same primitive this repo already uses — either as a task's `worktree` workspace kind[^kanban] or via
`hermes -w`, with each process on its own branch and its own checkpoint store hash.[^worktrees]

**2.5 Durability is bespoke and layered, with no execution engine anywhere.** From the lane
contract:[^lanes] a stale claim is reclaimed after `DEFAULT_CLAIM_TTL_SECONDS` (15 min default) — but
*"only a dead PID is reclaimed"*, and a live-but-slow worker gets its claim **extended**;
`detect_crashed_workers` reaps vanished PIDs and increments `consecutive_failures` until a breaker
auto-blocks; `task.max_runtime_seconds` hard-caps wall clock *regardless* of PID liveness; a retried
worker can pass `expected_run_id` to fail fast if its run was superseded; and a `ready` task whose
assignee never claims it surfaces as `stranded_in_ready` after `kanban.stranded_threshold_seconds`
(30 min default), escalating to error at 2× and critical at 6×. Audit is two tables: `task_runs`
(log path, exit code, summary, metadata) and `task_events` (`promoted`, `claimed`, `heartbeat`,
`completed`, `blocked`, `gave_up`, `crashed`, `timed_out`, `reclaimed`, `claim_extended`).[^lanes]

**2.6 Credentials live in the home directory, and multiply.** Provider credentials are pooled per
provider in `~/.hermes/auth.json`, auto-seeded from environment variables, OAuth tokens, **Claude Code
credentials at `~/.claude/.credentials.json`**, Hermes PKCE OAuth, and custom endpoint config.[^cred-pools]
Borrowed runtime secrets (env, Bitwarden, Vault, keyring, systemd refs) are *"reference-only at the
`auth.json` boundary"* — only source ref, label, status, counters and a non-reversible fingerprint are
persisted.[^cred-pools] The artifact-delivery doc states the posture directly: *"OAuth tokens stay on
the user's machine in `auth.json` / `.env`. No hosted token storage."*[^deliverable]

**2.6a … and the documented way to SHARE a credential is to lend it over HTTP.** `hermes proxy start`
runs a local OpenAI-compatible server that attaches the operator's real subscription credential to
requests from any client — *"a credential-attaching pass-through"*, in the doc's words. It binds
`127.0.0.1` by default, and `--host 0.0.0.0` is documented with a warning: *"The proxy has no auth of
its own — it accepts any bearer."*[^subscription-proxy] **This is the sharpest single contrast in the
paper.** Hermes' answer to *how does another machine use my subscription* is **move the credential's
reach off the machine**; the problem statement's answer is **move the work to the credential**.[^problem-statement]
Neither is wrong — they are answers to different questions — but the Hermes shape carries exactly the
property `dedicated_edge_routing.md` argues our topology exists to avoid.[^dedicated-edge] *(derived —
inputs: the proxy doc, `problem-statement.md` § *Affordability is the enabler*, and
`dedicated_edge_routing.md` §6.5's credential-locality reframing.)*

**2.7 There are two loop constructs above the turn.** **Cron** — jobs in `~/.hermes/cron/jobs.json`,
ticked every 60 s by the gateway, with a `.tick.lock` against double-firing.[^cron] **Goals** —
`/goal` sets a completion contract; after every turn a lightweight judge model returns one of
`done` / `continue` / `wait`; shell-command *quality gates* can be attached with `/goal gate add`;
the default budget is *"20 continuation turns"*, after which Hermes auto-pauses and says how to
proceed; goal state lives in `SessionDB.state_meta` and survives `/resume` and context
compression; semantics are explicitly **fail-open**.[^goals]

**2.8 The trust model is single-operator, and the documentation says so in four separate places.** This
is the axis where first-party wording matters most, so it is quoted rather than characterised.
**Where the boundary is admitted to be soft:** managed scope — the mechanism for an administrator to pin
policy across users — is enforced by file ownership alone (*"That filesystem permission is the
enforcement mechanism"*), ships a **world-readable** managed `.env` at mode `0644`, and is described by
its own authors as *"a management-convenience boundary against a normal user, not an un-escapable
sandbox"*, with signed/integrity-checked files, MDM delivery and group-scoped secret permissions all
listed **out of scope for v1**.[^managed-scope] Kanban's `--tenant` flag namespaces memory writes and
scopes data by filesystem path, but *"only the data is scoped"* — the board, the dispatcher and the
profile definitions are shared.[^kanban-raw] The subscription proxy accepts any bearer.[^subscription-proxy]
The kanban dashboard's plugin API skips HTTP auth on localhost by design.[^kanban] **Where the boundary
is genuinely hard:** the messaging gateway's user authorization, which resolves in a fixed order ending
*"Default: deny"*, backed by the DM-pairing enrolment protocol specified against OWASP and NIST SP
800-63-4.[^security] **The shape that emerges: Hermes has a real answer to *who may talk to my agent*
and no answer to *which principal owns this work*.** That is the same conclusion `bernstein_capability_mining`
reached about the nearest neighbour by a different route — *"multi-project, not multi-tenant in the
security sense"*[^problem-statement] — reached here against a **third** independent system. **Differentiator
#1 strengthens.** *(derived — inputs: the four documents cited in this paragraph plus
`problem-statement.md` #1. The sibling `edge_identity_trust.md` owns the full treatment; see the unranked
note at the end of §5.)*

## 3. Comparative landscape — and the category error this paper found

Placing Hermes beside the pool's existing comparators exposes that **"Tools to Evaluate" is holding two
different kinds of thing under one heading.** *(derived — inputs: this paper's §2 and §4;
`paperclip_assessment.md` §2 and §4.7; `dedicated_edge_routing.md` §3.1; `problem-statement.md`
§ *The nearest neighbor*.)*

| | bernstein | Paperclip | **Hermes Agent** | This repo (destination) |
|---|---|---|---|---|
| **What it is** | deterministic orchestrator for CLI coding agents[^problem-statement] | Node/React control plane over an org-chart ontology[^paperclip] | **a full agent runtime** — tools, memory, models, chat surfaces[^readme][^architecture] | a backbone (Temporal) plus edges |
| **Coordination unit** | task in a central queue, role-matched | issue assigned by a manager agent, atomic checkout[^paperclip] | **task addressed to a named profile on THIS host**[^lanes] | task queue per edge identity |
| **Durability** | checkpoint/resume, K8s CRDs[^problem-statement] | bespoke on Postgres, 206 migrations[^paperclip] | **bespoke on SQLite + PID liveness**[^lanes][^kanban-raw] | Temporal |
| **Cross-host** | yes — K8s operator, mTLS[^problem-statement] | yes — SSH and sandbox targets[^paperclip] | **NO — explicitly out of scope**[^kanban-raw] | the entire point |
| **Category** | backbone | backbone | **edge** | backbone + edges |

**The consequence, and it is actionable.** bernstein and Paperclip are *backbone* comparators — they
compete with the thing this repo is building. Hermes (and, on the same reasoning, OpenClaw) is an
*edge* comparator — it competes with **Claude Code**, the thing this repo's edge already runs. Judging
Hermes against the backbone axes produces a rejection that is technically correct and analytically
useless; judging it as an edge produces §5. **Recommendation: `roadmap.md` § *Tools to Evaluate*
should split into "backbone comparators" and "edge runtimes"** (§8).

**Does *"the nearest neighbor"* designation still hold? Yes, and Hermes never threatened it.** bernstein
remains the nearest comparable *system* because it competes on the backbone axes — distributed
workers, typed completion contracts, cross-host durability.[^problem-statement] Hermes matches on none
of the three. *(derived.)*

## 4. Test (a) — is its architecture right for us? No, as a backbone. Four grounds.

**4.1 It is single-host by design, and says so.** *"Kanban is deliberately single-host."*[^kanban][^kanban-raw]
The board is a local SQLite file, the dispatcher spawns workers on the same machine, and — the detail
that makes this structural rather than a missing feature — *"the crash-detection path assumes PIDs are
host-local"*.[^kanban-raw] *(That last span is sourced from the re-wrapped fetch only; the shorter
"deliberately single-host" appeared in both fetches of the file — §6(b).)* The whole liveness model in
§2.5 is built on `<host>:<pid>:<uuid>` claim locks.[^lanes] Our destination is many machines in many
trust domains; a substrate whose failure detector cannot see the other machine cannot be the backbone.

**4.2 Durability is re-derived per feature, exactly as Paperclip's is.** Claim TTLs, PID reaping,
consecutive-failure breakers, run-supersession tokens, stranded-task ladders, tick locks and idempotency
keys are each a hand-built purchase of one property a durable-execution engine supplies once.[^lanes][^cron]
Our substrate is Temporal.[^system-overview] **As with Paperclip, this is a price list rather than a
criticism** — and §5 spends it.

**4.3 There is no execution-state resume; the resumable unit is the TASK.** Three separate mechanisms
each stop short of replay. Checkpoints are *"opt-in"* filesystem snapshots into a shadow git store —
*"your real project `.git` is never touched"* — and `/rollback` restores files and *"Undoes the last
conversation turn"*.[^checkpoints] That is undo, not resume. Cron is blunter: a job mid-run at restart
is marked `unknown` and *"is not automatically retried"*.[^cron] Kanban comes closest — a crashed
worker's task is respawned with prior run handoffs available as context[^lanes] — but that is
**restart-with-memory**, not resumption from a step. *(derived — inputs: the three documents named.)*

**4.4 Adopting it means adopting an AGENT, not a backbone.** Hermes brings its own tool registry, its
own model routing and credential pools, its own memory system, its own personality layer and its own
25+ chat surfaces.[^architecture][^cred-pools] This repo's edge already has an agent. What it lacks is
the backbone. Taking Hermes as infrastructure would import a second agent runtime to sit under the one
we run. *(derived.)*

**Verdict: do not adopt as a backbone. Nothing in §5 depends on this verdict** — which is the entire
point of running the two tests separately.

**And the scoping caveat is load-bearing, so it is stated here rather than buried in §6.** §4.1's
limit is a documented statement about **kanban**, not about Hermes. The API server exposes a Runs API
over HTTP with bearer auth,[^api-server] profiles are process-isolated,[^profiles] and a third party
already drives Hermes remotely as a worker.[^pc-adapters] **"Rejected as a backbone" must not be read
as "no place here."**

## 5. Test (b) — what to take. Eight items, ranked, each with a cost.

Ranked by *value to the federated destination × plannability*. **Cost figures are `derived` and name
their inputs.**

### 5.1 — Credential pools: the quota-headroom primitive, and the gap it unblocks `RANK 1`

**What it is.** Multiple credentials registered per provider, with automatic rotation on failure. The
policy is per **error class**, not a blanket retry:[^cred-pools]

| Signal | Behaviour | Cooldown |
|---|---|---|
| Plan/usage-limit 429 (e.g. a subscription cap) | *"Rotate to next pool key immediately (no retry — the cap won't clear on retry)"* | — |
| Generic/transient 429 | retry the same key once; a second 429 rotates | 1 hour |
| 402 billing/quota | rotate immediately | 1 hour |
| 401 auth expired | attempt OAuth refresh first; rotate only if refresh fails | 5 minutes |
| All keys exhausted | fall through to a *different* provider (`fallback_model`) | — |

Provider-supplied `reset_at` timestamps override the defaults.[^cred-pools] Selection strategies are
`fill_first` (default), `round_robin`, `least_used`, `random`.[^cred-pools] Per-credential state
persisted in `auth.json` includes `last_status` and `request_count`.[^cred-pools] Subagents inherit the
parent's pool, and *"Per-task credential leasing ensures children don't conflict"* when rotating
concurrently.[^cred-pools] And the honest cost is documented rather than hidden: rotating mid-session
abandons the provider-side prompt cache, so *"each rotation costs one full-price pass over the
context"* — the doc's own framing.[^cred-pools]

**Why it matters for the federated destination.** `topics.md` carries *"the quota-headroom view — per-edge
rate-limit capacity as the scarce resource"* as a named gap, *"not deferred on priority — not
sequenceable yet"*, blocked on whether quota is observable at all.[^topics] Under flat-rate subscription
economics, dollars are not the scarce resource and **rate-limit headroom is** — that reasoning is the
pool's own.[^topics] Hermes is a shipped system that treats exactly that resource as first-class, and
its **error taxonomy is the sequenceable part**: the distinction between *a cap that will not clear on
retry* and *a transient blip* is the whole design, and it is invariant to whether we ever hold two
subscriptions.

**Cost to build here.** *(derived — inputs: the table above; `system-overview.md`'s single-operator,
single-subscription present state; `topics.md`'s statement of the gap.)* **~1 day for the taxonomy**
(classify a provider error into cap / transient / billing / auth-expired and attach a policy per class)
and **hours for the telemetry** (`last_status` + `request_count` + cooldown-until per credential,
surfaced in `/standup`). The *rotation mechanism* is worth **zero today** — one operator, one
subscription, a pool of one — and §6(e) argues that against this ranking. **The unblocking insight is
that the gap's blocker was mis-stated:** it was recorded as blocked on whether the Claude Code envelope
exposes remaining quota,[^topics] but a usable headroom signal can be *derived from observed cap
errors* without any provider telemetry at all.

### 5.2 — The stranded-work detector, on a severity ladder, with no allowlist `RANK 2`

**What it is.** A `ready` task whose assignee never produces a claim within
`kanban.stranded_threshold_seconds` (30 min default) surfaces in `hermes kanban diagnostics` as
`stranded_in_ready`, escalating to **error at 2× the threshold and critical at 6×**. The design note is
the takeaway: it *"Catches typo'd assignees, deleted profiles, and down external worker pools in one
signal — identity-agnostic, no per-board allowlist to curate."*[^lanes]

**Why it matters.** This is the *dispatch-side half* of the failure Paperclip narrated from the
*review-side*: `paperclip_assessment.md` §4.2 records work that enters review and loses its reviewer
becoming an invisible zombie.[^paperclip] Hermes catches the mirror case — work that never starts
because the thing it was addressed to is gone. **In a dedicated-edge fabric that is the dominant
failure**, because work is addressed to a specific machine that can simply be off. And the
*identity-agnostic* property is the design lesson: a detector that needs a registry of valid edges
fails exactly when the registry is wrong, which is the case it exists to catch. *(derived — inputs:
the lane doc; `paperclip_assessment.md` §4.1–§4.2; `problem-statement.md` § *The edges*.)*

**Cost to build here.** *(derived — inputs: the ladder above; the `/standup` blocked-work queue already
proposed as `paperclip_assessment.md` §6 item 1.)* **≤ 1 day**, as one more row-type in that queue plus
a threshold constant. **Sequence it with that item, not separately.**

### 5.3 — An unresolvable assignee PARKS; it never falls back `RANK 3`

**What it is.** *"Tasks whose assignee doesn't resolve are left on `ready` with a `skipped_nonspawnable`
event so a board operator can fix them; they are not silently dropped or executed by an arbitrary
fallback."*[^lanes]

**Why it matters, and it is the single most directly applicable rule in this paper.** Our design pins
work to an edge *because that edge holds the credential and the repository*.[^problem-statement] A
catch-all fallback queue would therefore be worse than a stall: it would run the work under the wrong
subscription, on a machine without the checkout, and **report success**. Hermes states the invariant as
a product behaviour, with a typed event so the stall is visible rather than silent. **For
`Phase: Temporal Integration` this is a negative design constraint — do not add a shared fallback
queue beside the per-edge queues** — and it is the counter-weight to the open ruling
`problem-statement.md` records about pinning costing failover.[^problem-statement]

**Cost.** **Zero to decide, and it saves work** — it removes a component rather than adding one. It is
a phase-doc constraint, not a build item.

### 5.4 — Live-PID extension vs dead-PID reclaim vs an absolute runtime cap `RANK 4`

**What it is.** Three separate guards that a naive design collapses into one timeout:[^lanes]

1. Claim TTL (15 min default) — but a claim is reclaimed **only if the worker process actually died**;
   a live worker *"(slow model spending 20+ min in one tool-free LLM call)"* gets the claim **extended**.
2. `detect_crashed_workers` reaps vanished PIDs, incrementing `consecutive_failures` toward a breaker.
3. `task.max_runtime_seconds` hard-caps wall clock *"regardless of PID liveness. Catches genuinely-
   deadlocked workers that the live-PID extension would otherwise keep running."*

**Why it matters.** `paperclip_assessment.md` §4.4 opened the question of what a `claude_cli` activity
heartbeat must *carry*, and answered it from Paperclip's side with **output-silence** detection.[^paperclip]
Hermes answers the same question differently — **process liveness with escalating override**. Read
together the two produce the design rule neither states alone: *liveness, progress and
permission-to-continue are three different predicates and a single timeout conflates them.* A run of
`claude -p` that takes 10–60 minutes[^system-overview] will trip any timeout tuned for the common case;
the extension-on-liveness plus absolute-cap pair is how you tolerate the long tail without tolerating a
deadlock. *(derived — inputs: the lane doc; `paperclip_assessment.md` §4.4; `system-overview.md`
§ *Deployment target*.)*

**Cost to build here.** **Hours of design, but it must land BEFORE workers are written** — it constrains
the activity's heartbeat payload, its `start_to_close` vs `heartbeat` timeout split, and its
cancellation semantics. Dependency: the `claude_cli` activity design in `Phase: Temporal Integration`.
**A sequencing constraint, not a work item.**

### 5.5 — Completion contracts judged per turn, with a budget and fail-open semantics `RANK 5`

**What it is.** `/goal` attaches a **completion contract** to a session. After each turn a lightweight
judge model — separately routable via `auxiliary.goal_judge.provider` / `.model` — returns one of three
verdicts: `done`, `continue`, `wait`.[^goals] Shell-command **quality gates** attach with
`/goal gate add <command>`. The default budget is *"20 continuation turns"* (`goals.max_turns`), after
which the loop auto-pauses and states how to proceed; user messages always preempt; semantics are
**fail-open**; state lives in `SessionDB.state_meta` and survives `/resume` and context
compression.[^goals]

**Why it matters.** This is `problem-statement.md` element 4 — *"high-level loops over persisted state…
running unattended until an exit condition it can actually observe"*[^problem-statement] — shipped, at
the *session* altitude rather than the workflow altitude. Three specifics transfer directly to
`convergence_stopping.md`'s territory and to `revision.sh`'s loop-back bound: **(i)** a **three**-verdict
vocabulary, because `wait` (blocked on something external) is a genuinely different state from
`continue` and collapsing them produces either busy-looping or premature exit; **(ii)** a **turn budget
that ends in an instruction**, not a silent stop; **(iii)** **fail-open** — a judge that errors must not
be able to declare the work done. *(derived — inputs: the goals doc; `problem-statement.md` element 4;
`system-overview.md` § *Composition*, where our completion contract is a regex on final output.)*

**Cost to build here.** *(derived — inputs: our existing completion-contract mechanism, which already
proves *finished* but carries no *verdict*.)* **~1 day** to widen the parent-visible outcome from
`exit 0` + pattern to a three-value verdict; the judge itself already exists here as `review-pr`'s
decide-only stage.[^system-overview] The mineable part is **the vocabulary and the budget-exhaustion
behaviour**, not the machinery.

### 5.6 — The curator: a reversible, telemetry-driven lifecycle over agent-created artifacts `RANK 6`

**What it is.** *"a background maintenance pass for agent-created skills"*[^curator] that runs when
**both** an interval (`interval_hours`, default 168) and an idle window (`min_idle_hours`, default 2)
are satisfied. It moves skills `active → stale → archived` on `stale_after_days` (30) and
`archive_after_days` (90); tracks view/use/patch counts in `~/.hermes/skills/.usage.json`; writes a
timestamped `run.json` plus a human-readable `REPORT.md` per run; takes a `skills.tar.gz` backup before
any mutation (`backup.keep: 5`); and exposes `hermes curator rollback --id <ts>`, `pin`, `adopt`,
`list-unmanaged`, `restore`, `list-archived`, `prune`.[^curator] **The split that matters: mechanical
pruning runs with no model in the loop; LLM-driven consolidation is a separate switch,
`consolidate: false` by default.**[^curator]

**Why it matters.** This repo's improvement loop produces artifacts — skills, rules, agents, the
CPI decisions log — and has **no lifecycle over them**: nothing measures whether a skill is ever
loaded, nothing ages an unused one out, and nothing can roll back a CPI change as a unit.[^system-overview]
Hermes ships all three, and the `prune`/`consolidate` split is the governance-relevant piece: the
irreversible-looking part is deterministic, and the model-driven part is opt-in and backed up. That maps
onto this repo's standing rule that agents propose and humans ratify.[^system-overview] *(derived.)*

**Cost to build here.** *(derived — inputs: the curator config surface; this repo's `config/skills/`
and its lack of usage telemetry.)* **Usage telemetry: hours** (a counter written when a skill is loaded).
**Backup-before-mutate + rollback-by-id for CPI changes: ~1 day.** **The full lifecycle: 2–4 days**, and
§6(f) argues it is premature.

### 5.7 — Mining approval history into policy, with never-promote classes `RANK 7`

**What it is.** `hermes approvals suggest` scans the session database for dangerous-classified commands
that *actually executed* — i.e. ones the operator approved — aggregates them into patterns, ranks by
frequency, and proposes allowlist additions. **Nothing is ever applied automatically**; only an explicit
`--apply N[,M...]` writes. And a fixed set of classes is **never proposed no matter how often they were
approved**: recursive deletes, `sudo`, disk/device writes, credential and system-config edits,
pipe-to-shell, SQL `DROP`/`TRUNCATE`, process kills, and every hardline class.[^security] The doc's own
example of the rule: `rm -rf build/` approved 100 times still never yields an `rm` entry.[^security]

**Why it matters.** This repo runs autonomous dispatches under `--dangerously-skip-permissions`, where
*"the `PreToolUse` hook is the only control operating during a run"*.[^system-overview] We have the
block half and none of the *learning* half: no path from repeated operator approval to policy, and — more
importantly — **no codified list of patterns that must never be promoted regardless of evidence.** The
second is the real prize, because an automated CPI loop that mines its own history is exactly the thing
that would otherwise promote `sudo` because it was approved often.

**Cost to build here.** *(derived — inputs: the command's stated safety rules; this repo's
`block-dangerous.sh` and JSONL run logs.)* **The never-promote list: hours, and it is a
standards-amendment candidate** for `docs/standards/hook-scripts.md`. **The suggester itself: 1–2 days**,
and only worth it once dispatch volume makes the prompt fatigue real.

### 5.8 — Protected-path denylist, and the honesty note attached to it `RANK 8`

**What it is.** Before `write_file` or `patch` touches disk, the target is checked against an
always-blocked list — OS credential stores (`~/.ssh/`, `~/.aws/`, `~/.kube/`, `/etc/sudoers`,
`~/.netrc`), Hermes credential stores (`auth.json`, `.env`, `.anthropic_oauth.json`, `mcp-tokens/`,
`pairing/`), and project secret files (`.env`, `.env.local`, `.env.production`, `.envrc`) **anywhere on
disk** — with no approval prompt and no chat-side override. An optional `HERMES_WRITE_SAFE_ROOT` narrows
writes further, and *"Sensitive paths inside the safe root are still blocked"*.[^security]

**And the note that makes it worth citing:** *"Write guards apply to `write_file` and `patch` only."* —
the terminal tool runs as the same OS user and can still overwrite denied paths via the
shell.[^security] The doc classifies the whole layer as defense-in-depth, not a boundary.

**Why it matters.** Our `PreToolUse` hook has **the identical property and does not say so**.[^system-overview]
A guard documented as a boundary gets trusted as one. Adopting the *denylist* is cheap; adopting the
*disclaimer* is free and prevents a category of misplaced confidence in every downstream design that
cites the hook. A separate transferable rule sits beside it: the same document scopes user-defined deny
globs as *"a guardrail against an honest-but-wrong agent"*, explicitly not a sandbox against an
adversarial one.[^security]

**Cost to build here.** **Hours** for the denylist patterns; **zero** for the disclaimer, which is a
documentation edit to `hook-scripts.md` through the human-ratified path.

### Also noted, not ranked — for the sibling `edge_identity_trust.md` paper

Hermes' **DM pairing** system is the most developed identity machinery in the product and is stated
against named external guidance (OWASP + NIST SP 800-63-4): an 8-character code from a 32-character
unambiguous alphabet (no `0/O/1/I`), generated with `secrets.choice()`, 1-hour TTL, one request per user
per 10 minutes, at most 3 pending codes per platform, 5 failed approval attempts → 1-hour lockout,
`chmod 0600` on all pairing files, and *"Codes are never logged to stdout"*.[^security] The authorization
check order ends *"Default: deny"*.[^security] **That sibling should mine this directly** — it is a
shipped, specified enrolment protocol for admitting a new principal, which is structurally the same
problem as admitting a new edge. This paper does not treat it further.

## 6. Honest boundary analysis — the case against this paper

**(a) Documentation only. Nothing was executed and no Python was read.** Every behavioural claim is
inferred from prose written by the people who built it. `detect_crashed_workers` being documented is not
evidence that it fires. **The single largest weakness**, and test-plan items 1–3 are its direct tests.

**(b) A NEW measured sourcing hazard: the fetch layer declared a 125-character quote ceiling, and
enforced it inconsistently.** Asked to reproduce `features/goals.md` verbatim, the layer **refused
outright**, replying that verbatim reproduction and a *"125-character limit for quotes"* were
contradictory instructions. Asked the same of other documents in the same session, it returned long
apparently-complete reproductions. A second fetch of `features/kanban.md` returned the requested spans
**re-wrapped to a different line width** than any plausible source. Three consequences, all applied:

1. **No long block in this paper is presented as byte-exact**, and no long block is fenced as a
   reproduction. Every quoted span is short and lexically distinctive.
2. **`features/kanban.md` is quoted only where two independent fetches agreed** (*"deliberately
   single-host"*), and single-fetch spans from it are marked in place (§4.1).
3. This is a **different** failure surface from the two this pool has already measured — the
   under-enumerating listing[^paperclip] and the silent statement-level elision[^paperclip]. Those
   corrupt content while looking complete; **this one corrupts the *provenance guarantee* while the
   content may be perfectly accurate.** The tell is different too: it is visible only when the layer
   *refuses*, which happened once in roughly a dozen fetches. **A single refusal invalidates the
   verbatim status of every long block in the same session, not just the refused one.**

**(b′) The `kanban.md` summarization did NOT reproduce in two later sessions — and the REDUCED marking
is kept anyway.** *(Added 2026-08-06 at the verification gate; observers named.)* The plain `main` URL
that returned summarized prose to the analyst returned accurate, unsummarized content to **three later
independent fetches on the same day** — one by the read-only verification pass and one by the pass that
recorded the critic verdict, both of which retrieved the `"crash-detection path assumes PIDs are
host-local"` clause inside its full surrounding sentence, plus one by the round-2 verification pass,
which reported clean unsummarized content without making a span-level claim.[^kanban] That third
observer added a caveat worth carrying: its own fetch layer summarizes by construction, so it
corroborates *content* and certifies no bytes — which is equally true of the other two clean fetches,
and is precisely why ground (i) below is the ruling. **Ruling: the analyst's observation
stands as written and the REDUCED marking is retained**, on three grounds. (i) A later session's clean
fetch corroborates the *content*; it cannot retroactively certify the *fetch* that actually produced
this paper's spans, and §6(b)(3) above already states that this hazard class leaves content accurate
while destroying the provenance guarantee — so a content-level corroboration is not the thing in doubt.
(ii) Four fetches across four sessions of one unchanged URL yielding two different response
characters — **one summarized, three clean** — is **evidence of fetch-layer non-determinism**, which
makes the reduced marking *more* warranted, not less: a hazard that appears intermittently cannot be
cleared by a passing sample. The 1-in-4 rate is stated plainly because it cuts both ways: it is a low
enough rate that a reviewer may reasonably read the original summarization as an outlier, and a high
enough one that no single clean fetch settles anything.
(iii) Removing the marking would delete a measured observation about the tooling, which this pool has
been tracking as a distinct failure class. **What DOES change:** the reduced confidence on
`features/kanban.md` should now be read as scoped to **verbatim/provenance status only** — the
*substance* of the spans this paper draws from that file is corroborated by three later clean fetches
in three separate sessions and is not in question. Anyone re-testing this should expect the failure to be intermittent and should
not treat one successful fetch as a clearance.

**(c) No document count is asserted for the docs tree.** The git-trees fetch of `main:website/docs`
(`recursive=1`) was **truncated by the fetch layer mid-listing** and did not return a usable
`truncated` field. The enumeration was used to *locate* documents, never to count them. The HuggingFace
model list is stated as a **floor** because the query was capped at `limit=20`. The third-party adapter
list is stated as a **floor** for a reason this pool independently measured.[^paperclip]

**(d) The strongest case against §4's verdict is that it answers a question nobody should have asked.**
Hermes never proposed itself as a backbone. Rejecting it as one is close to unfalsifiable and risks
reading as due diligence rather than analysis. **The counter, and why §4 is kept:** the topic list
placed Hermes in a comparator set alongside two genuine backbone comparators,[^topics] so the rejection
does real work — it *removes* it from that set and produces §3's split. A reviewer who thinks §4 should
be one paragraph instead of four has a defensible position.

**(e) The case against RANK 1 is that its mechanism solves a problem we do not yet have.** Credential
pools presume **multiple credentials**. This repo has one operator on one subscription;[^system-overview]
a pool of one rotates nowhere. The federated fabric that would make pooling meaningful is explicitly a
stub.[^problem-statement] §5.1 is therefore ranked on its **taxonomy and telemetry**, which are useful
at n=1, not on its rotation machinery, which is not. **If a reviewer disagrees with that split, RANK 1
should drop below §5.2 and §5.3, both of which are useful today.** Stated so the ranking can be
challenged rather than inherited.

**(f) §5.6 is the item most likely to be premature.** A skill-lifecycle curator presumes enough
agent-created artifacts that ageing them out is real work. This repo's skills are human-authored and
few.[^system-overview] The genuinely load-bearing sub-item is **backup-before-mutate plus
rollback-by-id**, which is valuable at any scale; the lifecycle state machine is not.

**(g) Adoption signals are not production-validation signals, and this subject's are noisy.** The API
reports 226,385 stars and **28,833 open issues**,[^gh-api] and the repository's own topic list contains
three competitors' names (`clawdbot`, `moltbot`, `openclaw`)[^gh-api] — discovery optimisation, not
engineering evidence. **Nothing in §5 is ranked on popularity.** As with Paperclip, lessons mined from
*mechanism* (the lane contract's failure-mode list, the credential-pool error table) are load-bearing;
lessons mined from *claims* (README feature bullets) are not.

**(h) Named coverage gaps** *(stated with method).* Located in the docs tree via the git trees API and
**deliberately not fetched** for budget: `developer-guide/agent-loop.md`, `developer-guide/gateway-internals.md`,
`developer-guide/subagent-lifecycle-api.md`, `developer-guide/session-storage.md`,
`developer-guide/trajectory-format.md`, `developer-guide/cron-internals.md`,
`user-guide/features/delegation.md`, `user-guide/features/hooks.md`, `user-guide/features/memory.md`,
`user-guide/features/skills.md`, `user-guide/features/mixture-of-agents.md`,
`user-guide/features/batch-processing.md`, `user-guide/docker.md`, `user-guide/multi-profile-gateways.md`,
`user-guide/secrets/*`, `user-guide/features/kanban-tutorial.md`, and
`guides/migrate-from-openclaw.md`.[^tree-docs] **Any claim of absence about Hermes in this paper is
scoped to the 16 distinct Hermes documents cited in §9** (17 raw-markdown fetches — `features/kanban.md`
appears twice, once per URL form; enumerated at the round-3 gate, replacing an earlier approximation of
"~18") and must not be read as a claim about the product.

**(i) Overlap risk with the sibling OpenClaw paper is real and un-deconflicted.** Both subjects are
personal-AI-assistant runtimes with messaging gateways, and Hermes ships a migration path *from*
OpenClaw.[^readme] §1.1 establishes they are distinct repositories,[^gh-api][^openclaw-api] but this
paper made **no attempt** to determine how much of Hermes' feature surface is convergent with, derived
from, or ahead of OpenClaw's. The synthesis step should compare the two papers' §5 lists for
double-counting before any item is sequenced.

**(j) Recency risk.** The repository was pushed on the day of this sweep.[^gh-api] The §5 items sourced
from *feature* docs (5.1, 5.6, 5.7) could be stale within weeks; those sourced from *contracts and
scope statements* (5.2, 5.3, 5.4, §4.1) age far better.

## 7. What this provides — the enumerated, plannable list

For the master-planning pass. Costs are `derived`; inputs named in §5.

| # | Capability | Where it lands | Cost (order of magnitude) | Hard dependency |
|---|---|---|---|---|
| 1 | **Provider-error taxonomy + per-credential headroom telemetry** — classify cap / transient / billing / auth-expired, each with its own policy; persist `last_status`, `request_count`, cooldown-until | Unblocks the **quota-headroom gap** in `topics.md`; surface in the `/standup` queue | ~1 day taxonomy + hours telemetry | none (rotation mechanism deferred until >1 subscription) |
| 2 | **Stranded-work detector on a severity ladder** — threshold, then error at 2×, critical at 6×; identity-agnostic, no allowlist | Row-type in the `/standup` blocked-work queue (`paperclip_assessment.md` §6 item 1) | ≤ 1 day | sequence with that item |
| 3 | **No fallback queue: unresolvable assignee parks with a typed event** | `Phase: Temporal Integration` — a **negative** design constraint on queue topology | 0 (removes work) | — |
| 4 | **Three-guard liveness: extend-on-live-PID, reclaim-on-dead-PID, absolute runtime cap** | `Phase: Temporal Integration`, **before** workers are written | hours (design); constrains build | `claude_cli` activity design |
| 5 | **Three-verdict completion contract (`done`/`continue`/`wait`) + budget that ends in an instruction + fail-open judge** | `Phase: Autonomous Operation` exit criteria; `revision.sh` loop-back bound | ~1 day | none |
| 6 | **Backup-before-mutate + rollback-by-id for self-improvement changes**; usage telemetry on skills. *(Full lifecycle state machine deferred — §6(f))* | `Phase: Continuous Process Improvement` | hours (telemetry) + ~1 day (rollback) | none |
| 7 | **Never-promote class list for any approval-mining path** | Standards-amendment candidate: `docs/standards/hook-scripts.md` | hours | human ratification |
| 8 | **Protected-path denylist + the "this is not a boundary" disclaimer on the PreToolUse hook** | `docs/standards/hook-scripts.md`; `block-dangerous.sh` | hours | human ratification |
| — | *Claim correction:* subscription-auth-at-the-edge now has a **second** independent precedent | `problem-statement.md` (human-ratified path) | 0 | — |
| — | *Claim correction:* *"per-user tools… cannot be orchestrated"* is too strong; the surviving axis is **cross-host and cross-trust-domain** | `problem-statement.md` § *The trade-off that should not exist* | 0 | — |
| — | *Claim strengthening:* differentiator #1 holds against a **third** system that documents its multi-tenancy as namespacing, not a security boundary | `problem-statement.md` #1 | 0 | — |
| — | *Structural:* split § *Tools to Evaluate* into **backbone comparators** and **edge runtimes** | `roadmap.md` | 0 | — |

## 8. The roadmap's and the problem statement's answers

**Verdict: MINE AND RECLASSIFY.**

**Do not adopt as a backbone** (§4). **Do not ignore** — eight transferable items (§5), one of which
unblocks a gap the pool has carried across two cycles (§5.1) and two of which are design constraints on
a committed phase (§5.3, §5.4).

**The comparator set is holding two categories under one heading, and should split** (§3). `roadmap.md`
§ *Tools to Evaluate* currently lists only Paperclip (now closed) and the Claude Agent SDK, so **Hermes
has no entry to correct** — this is an addition under a new sub-heading, not a rewrite.[^roadmap] bernstein and
Paperclip compete with the *backbone*; Hermes and OpenClaw compete with *Claude Code* — the runtime our
edge already contains. Judged against backbone axes Hermes fails trivially and teaches nothing; judged as
an edge runtime it is the most feature-complete open comparator to the thing sitting inside our edge.

**A live option the split makes visible, and this paper deliberately does not recommend it.** Because
Hermes is edge-shaped, exposes a bearer-authenticated Runs API,[^api-server] and is *already* driven as a
worker by a third party,[^pc-adapters] **"Hermes as a non-Claude edge"** is a coherent future option for
the provider-shaped-edges gap `topics.md` defers.[^topics] It is named here as an option with its
evidence, not sequenced — the destination it would serve is a documented stub.[^problem-statement]

**`problem-statement.md` § *The nearest neighbor* is unchanged.** bernstein keeps the designation; Hermes
was never a candidate for it (§3).

## 9. Citations

**First-party — Hermes Agent (raw markdown from the project's own repository, unless noted)**

[^gh-api]: GitHub REST API, repository metadata for `NousResearch/hermes-agent` (JSON):
  `default_branch: "main"`, `language: "Python"`, `license.spdx_id: "MIT"`, `stargazers_count: 226385`,
  `forks_count: 44122`, `open_issues_count: 28833`, `subscribers_count: 862`,
  `created_at: "2025-07-22T22:22:28Z"`, `pushed_at: "2026-08-06T12:06:41Z"`,
  `homepage: "https://hermes-agent.nousresearch.com"`, `description: "The agent that grows with you"`,
  `archived: false`, `fork: false`; `topics` include `clawdbot`, `moltbot`, `openclaw`, `claude-code`,
  `codex`, `nous-research`. Fetched 2026-08-06. https://api.github.com/repos/NousResearch/hermes-agent
[^readme]: `README.md` (raw, `main`). https://raw.githubusercontent.com/NousResearch/hermes-agent/main/README.md
[^lanes]: `website/docs/user-guide/features/kanban-worker-lanes.md` (raw). **The highest-grade source in
  this paper** — the lane contract, the env contract, the lifecycle terminators, and the dispatcher's
  handled failure modes.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/kanban-worker-lanes.md
[^kanban]: `website/docs/user-guide/features/kanban.md` (raw) — **returned SUMMARIZED by the fetch layer;
  cited as paraphrase, reduced confidence (§6(b))**.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/kanban.md
[^kanban-raw]: The same file re-fetched via the `refs/heads/main` path for section-level extraction —
  **returned re-wrapped; only short spans corroborated across both fetches are quoted as such (§6(b))**.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/refs/heads/main/website/docs/user-guide/features/kanban.md
[^cred-pools]: `website/docs/user-guide/features/credential-pools.md` (raw) — rotation strategies, the
  per-error-class table, auto-discovery sources including `~/.claude/.credentials.json`, the
  prompt-cache warning, subagent pool sharing, and the reference-only secret boundary.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/credential-pools.md
[^security]: `website/docs/user-guide/security.md` (raw) — the eight-layer model, hardline blocklist,
  `approvals.deny`, `hermes approvals suggest`, write-safety denylist, gateway authorization order, DM
  pairing properties, container hardening, SSRF policy.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/security.md
[^managed-scope]: `website/docs/user-guide/managed-scope.md` (raw) — `/etc/hermes` precedence,
  filesystem-permission enforcement, and the v1 out-of-scope list.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/managed-scope.md
[^checkpoints]: `website/docs/user-guide/checkpoints-and-rollback.md` (raw) — opt-in shadow-git
  checkpoints, `/rollback` semantics, store layout, safety guards.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/checkpoints-and-rollback.md
[^goals]: `website/docs/user-guide/features/goals.md` (raw) — **the layer REFUSED full reproduction of
  this file (§6(b));** structure, headings, commands, config keys and short quoted spans were extracted
  instead. Completion contracts, the judge's three verdicts, quality gates, `goals.max_turns`,
  fail-open semantics, `SessionDB.state_meta` persistence.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/goals.md
[^cron]: `website/docs/user-guide/features/cron.md` (raw) — `~/.hermes/cron/jobs.json`, the 60-second
  gateway tick, `.tick.lock`, and the `unknown`-not-retried restart behaviour.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/cron.md
[^curator]: `website/docs/user-guide/features/curator.md` (raw) — lifecycle states, idle-gated schedule,
  `run.json`/`REPORT.md`, `.usage.json`, backups and `curator rollback`.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/curator.md
[^profiles]: `website/docs/user-guide/profiles.md` (raw) — profile = separate home directory; isolation
  of config, credentials, memory, skills, cron and gateway; per-profile services.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/profiles.md
[^architecture]: `website/docs/developer-guide/architecture.md` (raw) — `AIAgent` in `run_agent.py`,
  directory layout, SQLite session storage with FTS5, and the source's own stated tool/toolset and
  platform-adapter figures (quoted as the document's assertions, not measured here).
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/developer-guide/architecture.md
[^api-server]: `website/docs/user-guide/features/api-server.md` (raw) — `API_SERVER_ENABLED`,
  `API_SERVER_KEY` required for every deployment, default bind `127.0.0.1:8642`, the Runs/Sessions/Jobs
  APIs, and the per-profile multi-user pattern.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/api-server.md
[^deliverable]: `website/docs/user-guide/features/deliverable-mode.md` (raw) — the artifact channel on
  `kanban_complete`, and the stated credential posture (*no hosted token storage*, *no remote tenant*).
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/deliverable-mode.md
[^subscription-proxy]: `website/docs/user-guide/features/subscription-proxy.md` (raw) — local
  credential-attaching pass-through, no auth of its own, the LAN-exposure warning.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/subscription-proxy.md
[^worktrees]: `website/docs/user-guide/git-worktrees.md` (raw) — `hermes -w` automatic worktree mode and
  parallel-agent isolation.
  https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/git-worktrees.md
[^tree-docs]: GitHub REST *git trees* API, `main:website/docs` with `recursive=1`, used to LOCATE
  documents. **The response was truncated by the fetch layer mid-listing; no count is asserted from it
  (§6(c)).**
  https://api.github.com/repos/NousResearch/hermes-agent/git/trees/main:website%2Fdocs?recursive=1

**First-party — the excluded candidates (identification evidence, §1.1)**

[^hf-api]: HuggingFace models API, `author=NousResearch&search=Hermes&limit=20` (JSON) — **at least 20**
  model repositories, every one `pipeline_tag: text-generation`, including `Hermes-4-405B`,
  `Hermes-4-70B`, `Hermes-4.3-36B`, `Hermes-3-Llama-3.1-70B`, `Nous-Hermes-2-SOLAR-10.7B`,
  `Redmond-Hermes-Coder`. **Stated as a floor — the query was capped at `limit=20`.**
  https://huggingface.co/api/models?author=NousResearch&search=Hermes&limit=20
[^fb-hermes]: GitHub REST API, `facebook/hermes` — `description: "A JavaScript engine optimized for
  running React Native."`, `language: "JavaScript"`, `license.spdx_id: "MIT"`,
  `created_at: "2018-10-22T19:13:00Z"`. https://api.github.com/repos/facebook/hermes
[^openclaw-api]: GitHub REST API, `openclaw/openclaw` — `default_branch: "main"`,
  `license.spdx_id: "NOASSERTION"`, `created_at: "2025-11-24T10:16:47Z"`,
  `pushed_at: "2026-08-06T12:30:34Z"`, `homepage: "https://openclaw.ai"`, `archived: false`. Cited only
  to establish that Hermes and OpenClaw are **distinct live repositories** (§1.1).
  https://api.github.com/repos/openclaw/openclaw

**Third-party (first-party to ITS own product — the external identification anchor)**

[^pc-adapters]: Paperclip, `docs/adapters/overview.md` (raw, `master`) — built-in adapter registry
  enumerating **at least eleven** adapters including Hermes (`hermes_local`) and Hermes Gateway
  (`hermes_gateway`). Count stated as a floor for the reason recorded in `paperclip_assessment.md` §5(c).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/adapters/overview.md

**This repo**

[^problem-statement]: `docs/standards/architecture/problem-statement.md`.
[^system-overview]: `docs/standards/architecture/system-overview.md` — including § *Deployment target*
  (Temporal self-hosted; Cloud not on the table) and the 10–60 minute `claude -p` run duration.
[^roadmap]: `docs/development/roadmap.md` § *Tools to Evaluate*.
[^topics]: `docs/standards/architecture/research/topics.md` — the cycle frame, the two-tests rule, and
  the *quota-headroom* and *provider-shaped edges* gap entries.
[^paperclip]: `docs/standards/architecture/research/raw/paperclip_assessment.md` (last validated
  2026-08-04, Critic: PASS-WITH-FIXES) — §4.1/§4.2 the attention queue and the invisible-zombie scar,
  §4.4 output-silence liveness, §4.6 the subscription-auth correction, §5(b) the elision failure mode,
  §5(c) the enumeration failure mode and the adapter-count instability.
[^dedicated-edge]: `docs/standards/architecture/research/raw/dedicated_edge_routing.md` (last validated
  2026-08-04) — §3.1's treatment of local CLI adapters and credential locality.

## 10. Test plan — what research cannot settle

Ordered by how much each would change a decision.

1. **Stand up a two-profile kanban board and kill a worker mid-task.** Confirm that a dead PID is
   reclaimed, that a *live* slow worker gets `claim_extended` rather than reaped, and that
   `max_runtime_seconds` overrides both. **Settles §5.4**, the item that most constrains
   `Phase: Temporal Integration`, and it is the highest-value experiment here because our heartbeat
   payload design is downstream of it. Budget: ~1–2 hours.
2. **Address a task to a profile that does not exist.** Confirm it parks on `ready` with
   `skipped_nonspawnable` and is never executed by another lane, then let it sit and confirm the
   `stranded_in_ready` ladder escalates at 2× and 6×. **Settles §5.2 and §5.3.** Budget: ~1 hour
   (mostly waiting).
3. **Register two Anthropic credentials and force a plan-limit 429.** Observe whether rotation is
   immediate and retry-free as documented, and measure the prompt-cache cost the doc warns about.
   **Settles §5.1's taxonomy** — specifically whether *"the cap won't clear on retry"* is the shipped
   behaviour or an aspiration. Budget: ~1 hour, and it needs two credentials we may not have, which is
   itself the finding in §6(e).
4. **Re-verify every short quoted span in this paper against a byte-exact copy.** `git clone --depth 1`
   and `grep -F` each span. **Settles §6(b)** — the 125-character-ceiling hazard is unprecedented in
   this pool and no prior verification recipe covers it. **Cheapest item here; do it first if the
   critic is budget-constrained.**
5. **Drive a Hermes run through its Runs API from a Temporal activity, bearer-authenticated.** Does the
   `POST /v1/runs` → SSE-events → `stop` surface behave like a long activity with heartbeats? **Settles
   whether "Hermes as a non-Claude edge" (§8) is a cheap option or a project.** Budget: half a day; do
   not sequence it until the provider-shaped-edges destination stops being a stub.
6. **Measure whether a completion `wait` verdict is separable in our workflows.** Take one month of
   `revision.sh` loop-backs and classify each terminal state as `done` / `continue` / `wait`. If `wait`
   is empty, §5.5's three-verdict argument does not transfer and the item drops. **Research cannot
   answer this; only our own run logs can.**
7. **Fetch the seventeen named-but-unfetched documents in §6(h)**, `developer-guide/gateway-internals.md`
   and `user-guide/features/delegation.md` first. **Settles** whether any §6(h)-scoped absence claim is
   wrong. The pool's precedent is that absence claims falsified by cited-but-unread sources are the
   most common blocking defect class.
8. **Re-sweep in three weeks. Tripwires, in priority order:** (i) issue **#19931** / PR **#19924** — an
   external CLI worker lane landing would make Hermes a *direct* precedent for our dispatch design and
   would rewrite §5.3 and §8; (ii) any multi-host kanban work, which would invalidate §4.1 and the whole
   category split in §3; (iii) changes to the credential-pool error table, which §5.1 rests on entirely.
