# Paperclip — Architecture Rejected, Features Mined

```
Topic:          Paperclip is the largest player in this category. Its architecture is wrong for us — what
                are its features, interfaces and durability lessons worth taking anyway?
Feeds:          docs/development/roadmap.md § "Tools to Evaluate" → the open "Paperclip — UI overlay for
                Claude Code … Evaluate after Phase 4" item (answered in §7); and Phase: Temporal Integration
                (§4.3, §4.4, §4.6 are design constraints on the claude_cli activity and the worker contract)
Last validated: 2026-08-04
Revalidate:     high — 4 weeks
Confidence:     DEFINITIVE at the schema/SQL/commit-message level — the load-bearing findings (§4.2 the
                review-path scar, §4.3 the recovery-idempotency indexes, §4.4 the process-liveness columns)
                come from raw SQL migration files, raw Drizzle schema files, and a raw commit message
                returned as reproduced blocks, which is the strongest source class available without
                cloning. DEFINITIVE at the documentation level for the operator surface (§4.1), the adapter
                contract (§4.5) and the credential story (§4.6) — raw first-party markdown. DERIVED for
                every cost estimate (§4, §6), for the architecture verdict (§3), and for the coordination
                reading (§4.7) — each names its inputs. UNVERIFIED at the behavioural level: nothing was
                executed, no TypeScript was read. One third-party page (rywalker) is cited only for
                governance/adoption context and is marked reduced-confidence. COUNTS are stated only where
                corroborated by a second structurally different signal (the 206 migrations); every other
                count is a floor ("at least eleven") or has been dropped — see §5(c), where four fetches of
                one directory returned four different totals, all claiming completeness.
Critic:         PASS-WITH-FIXES (r1: §4.4 "stalled" restored to all three conditions; §4.3 four→five partial
                unique indexes, 0069's elided leaf_uq added; commit-10675 file count 36→47; six non-verbatim
                spans de-quoted or ellipsed; adapter count restated as a floor; ui/src/pages count dropped —
                four fetches, four totals; §5(b) reframed garbling→elision. r2: §2.4 "agent runtime"
                un-inserted; the coarse/fine pairing claim restricted to 0069, where 0084's fine index is
                subsumed; §6 item 4 given the stalled conjunction) — 2026-08-04
```

> ## Headline — the roadmap item describes a product that does not exist, and the verdict is MINE AND DISCARD
>
> `roadmap.md` § *Tools to Evaluate* records Paperclip as *"UI overlay for Claude Code. Offers visual
> workflow design, agent management, parallel project tracking, and PR review."*[^roadmap] **Three of those
> four are denied by Paperclip's own README**, which lists under *What Paperclip is not*: *"Not a workflow
> builder. No drag-and-drop pipelines."*, *"Not a code review tool. Paperclip orchestrates work, not pull
> requests."*, and *"Not an agent framework. We don't tell you how to build agents."*[^readme] The item as
> written cannot be evaluated because it describes something else. **Rewriting it is itself a roadmap
> action** (§7).
>
> **Architecture: rejected, and the rejection is cheap to state.** The ontology is a company of employees
> under a CEO in a strict reporting tree;[^core-concepts][^product] durability is hand-rolled on Postgres
> across 206 migrations rather than bought from an execution engine;[^tree-migrations][^database] and the
> server injects secrets and invokes adapters.[^readme] None of that survives contact with *edges are
> machines with capabilities and credentials* on a Temporal backbone. §3 states it with evidence in one
> page and moves on.
>
> **Features and lessons: seven worth taking, ranked in §4, and the top one fills a gap that is currently
> homeless.** This repo has no operator surface beyond a CLI and a text standup and no roadmap phase holds
> one. Paperclip has a working answer — an attention queue where every row resolves to `blocking` or
> `review` and carries inline actions[^decision-sheet][^ui-spec] — and, better than the answer, it has the
> **scar that produced it**: work that entered `in_review` and lost its reviewer *"become[s] invisible
> zombies. Nobody knows a decision is owed, so the work stalls forever."*[^commit-10675] That failure mode
> is live in this repo today, on GitHub Issues and PR threads, and nothing here detects it.
>
> **One correction to a position this repo holds.** Subscription-auth-at-the-edge is **not unusual**. The
> 75,610-star player supports it by default for local Claude Code runs and treats *which credential home is
> authoritative* as an adapter-level decision.[^claude-local][^adapters-overview][^agents-runtime] Our
> position has precedent at scale — which de-risks it and removes it from any list of differentiators.

---

## 1. Primer — what Paperclip is, and why an assessment of it kept going wrong

**Paperclip** (`paperclipai/paperclip`) is MIT-licensed TypeScript: 75,610 stars, 14,081 forks, 5,060 open
issues, created 2026-03-02, last pushed 2026-08-04 — the day of this sweep. Its default branch is
**`master`**. Its one-line description is *"The open-source app everyone uses to manage agents at work"* and
its homepage is `paperclip.ing`.[^gh-api] By adoption it is the largest system in this research pool by two
orders of magnitude.[^prior-art]

Its own framing: *"Paperclip is a Node.js server and React UI that orchestrates a team of AI agents to run a
business."* and *"If OpenClaw is an _employee_, Paperclip is the _company_."*[^readme]

**Two prior assessments in this pool got Paperclip wrong, and the reasons are methodological, not
incidental.**

- The first recorded it as unreachable. The raw fetch had guessed branch `main`; the default is `master`,
  and a guessed-branch 404 is indistinguishable from a dead project.[^prior-art]
- The second assessed it from the README alone and left E3 (code-routed control flow) undocumented, marking
  it *"the single most decision-relevant fact still open in this paper."*[^prior-art] §4.7 settles it.

**A third measurement error happened inside *this* paper and is reported in §5(c).** The GitHub *contents*
API listing of the migrations directory came back summarized as 95 entries ending at `0094_…`; the *git
trees* API on the identical path returned 207 objects, `truncated: false`, ending at
`0206_review_path_recovery_idempotency_index.sql`.[^tree-migrations] The trees answer is corroborated three
ways and the contents answer is wrong. **A directory listing passed through a summarizing fetch is not a
count.**

**Search method for this paper.** GitHub REST *contents* API for structure, GitHub REST *git trees* API for
counts, GitHub REST *commits* API for provenance and rationale, and `raw.githubusercontent.com` for every
file. Twenty-three first-party documents, five raw SQL migrations, four raw Drizzle schema files, three
skill definitions and four commit records were fetched. Every quoted span below appeared inside quotation
marks or a reproduced code block in a fetch response. One rendered third-party page was fetched for
governance context only and is marked at reduced confidence throughout. **No TypeScript source was read and
nothing was executed** — §5(a) and §5(h) state what that costs.

**Volatility note (§3 mixed-volatility rule).** The header takes `high — 4 weeks` because the **feature
inventory** decays fast: 206 migrations in five months is roughly 1.4 schema changes per day, and the single
most load-bearing artifact in this paper landed on the day of the sweep.[^commit-10675][^tree-migrations]
The **lessons** in §4.2–§4.4 are scars, not features, and are far more durable — a refresh may treat §4.2,
§4.3 and §4.4 as slow-moving and re-verify §4.1 and §4.5 first.

## 2. The specific model — how Paperclip actually works

Six mechanisms, each first-party.

**2.1 The object model is an org chart over an issue tracker.** *"A company is the top-level unit of
organization"* with *"A goal — the reason it exists"* and *"monthly spend limits in cents."* *"Every employee
is an AI agent"* with *"Adapter type + config — how the agent runs"*, arranged in *"a strict tree
hierarchy."* *"Issues are the unit of work"*, each with *"A parent issue (creating a traceable hierarchy back
to the company goal)"*.[^core-concepts] The product doc states the target directly: *"Paperclip is the
control plane for autonomous AI companies."*[^product]

**2.2 Execution is heartbeat-shaped, not session-shaped.** *"Agents don't run continuously. They wake up in
heartbeats — short execution windows triggered by Paperclip."*[^core-concepts] The five documented triggers
are Schedule, Assignment, Comment, Manual and Approval resolution — presented in the source as five separate
bullets with descriptions, not as a single string, so this list is a paraphrase.[^core-concepts] The README
lists *"Heartbeat Execution — DB-backed wakeup queue with coalescing, budget checks, workspace resolution,
secret injection, skill loading, and adapter invocation."*[^readme] The `agent_wakeup_requests` table carries
`source`, `status` (default `"queued"`), `coalescedCount`, `idempotencyKey`, `runId`, `requestedAt`,
`claimedAt`, `finishedAt`.[^schema-wakeup]

**2.3 The stack.** *"React UI (Vite) — Dashboard, org management, tasks"*, *"Express.js REST API (Node.js) —
Routes, services, auth, adapters"*, *"PostgreSQL (Drizzle ORM) — Schema, migrations, embedded
mode"*.[^architecture] *"Paperclip uses PostgreSQL via Drizzle ORM"*; *"If you don't set DATABASE_URL, the
server automatically starts an embedded PostgreSQL instance and manages a local data
directory"*.[^database]

**2.4 The execution flow puts the agent on the client side of a REST API.** *"Trigger"* → *"Adapter
invocation — Server calls the configured adapter's execute() function"* → *"Agent process — Adapter spawns
the agent (e.g. Claude Code CLI) with Paperclip env vars and a prompt"* → *"Agent work — The agent calls
Paperclip's REST API to check assignments, checkout tasks, do work, and update status"* → *"Result
capture"* → *"Run record"*.[^architecture] **This is the single most consequential structural fact in the
paper**: Paperclip does not drive the agent step by step; it wakes the agent and the agent calls back. The
tail of the third step — *"with Paperclip env vars and a prompt"* — is the seam §4.5's env-contract argument
runs through, and a round-1 repair to this sentence dropped it while inserting a word (*"runtime"*) the
source does not contain. **A repair to a quote is a new quote and needs the same verification the original
did**; recorded in §5(b).

**2.5 Work is directed, then locked.** *"Before doing any work on a task, checkout is required"*; *"This is
an atomic operation. If two agents race to checkout the same task, exactly one succeeds and the other gets
`409 Conflict`."*; *"Never retry a 409 — pick a different task."*[^task-workflow] Assignment itself is made
by a model: the CEO agent *"Assigns tasks to the right agent based on role and capabilities"* and *"The CEO
assigns tasks directly"*.[^delegation]

**2.6 Deployment is single-server with pluggable execution targets.** Three modes: `local_trusted`
(*"Single-operator local machine workflow"*), `authenticated + private` (*"Private-network access (for
example Tailscale/VPN/LAN)"*), `authenticated + public` (*"Internet-facing/cloud
deployment"*).[^deployment-modes] Adapters run *"on the Paperclip host, SSH targets, or managed sandbox
targets"*.[^adapters-overview] *"Local CLI adapters run unsandboxed on the host machine"*, with *"no adapter
timeout on local/SSH, a 4-hour backstop on sandbox targets."*[^agents-runtime]

## 3. Test (a) — is its architecture right for us? No. Four reasons, then move on.

This section is deliberately short; the dispatch is correct that it is near-settled.

**3.1 The ontology models workers as role-holders under a manager; ours models them as machines.** A
Paperclip agent is a row with a title, a reporting line, a budget and an adapter config, arranged in a
strict tree.[^core-concepts] The physical machine is a *separate* axis — execution workspaces, SSH targets
and sandboxes are bound independently.[^adapters-overview][^exec-workspaces] The problem statement's edge is
the opposite: *"a machine with a capability and a credential, running a worker that speaks the backbone's
protocol"*, and *"a robotics edge cannot take a bioinformatics task because it is a different thing, not a
differently-labeled one."*[^problem-statement] **Paperclip's agent is exactly a differently-labeled one.**
*(derived — inputs are §2.1, §2.6 and the problem statement's differentiator #2.)*

**3.2 Durability is re-derived per feature, not provided by a substrate.** There is no execution engine.
Every guarantee is a bespoke table, a partial unique index or a watchdog: 206 SQL migrations, of which
`0064_issue_thread_interaction_idempotency`, `0069_liveness_recovery_dedupe`, `0084_issue_recovery_actions`,
`0192_task_watchdog_stop_snapshots` and `0206_review_path_recovery_idempotency_index` each buy back one
property a durable engine gives for free.[^tree-migrations] Our substrate is Temporal.[^temporal-paper]
**This is not a criticism of Paperclip — it is a price list**, and §4.3 uses it as one.

**3.3 The server holds and injects secrets.** Heartbeat execution includes *"budget checks, workspace
resolution, secret injection, skill loading, and adapter invocation"*, and secrets are server-side:
*"Secrets & Storage — Instance and company secrets, encrypted local storage."*[^readme][^database] A central
tier that stores credentials is the shape the problem statement rejects.[^problem-statement] *(Note the
partial counter-evidence in §4.6 — the credential story is more mixed than this sentence alone suggests, and
that nuance is a finding in our favour, not against it.)*

**3.4 It assumes a coding-adjacent product surface even while denying it.** It denies being a code review
tool[^readme] and ships HTTP/webhook adapters[^adapters-overview] — but its shipped operator vocabulary is
issues, projects, PR-shaped review and workspaces with git worktrees.[^exec-workspaces][^component-inventory]
Adopting it would import a product ontology, not a backbone. *(derived.)*

**Verdict: do not adopt the architecture.** Nothing below depends on this verdict, which is the point of
separating the two tests.

## 4. Test (b) — what to take. Seven capabilities, ranked, each with a cost.

Ranking is by *value to the federated destination × plannability*. Every entry carries what it is, why it
matters, the evidence, and an order-of-magnitude cost with its dependencies. **Cost figures are `derived`
throughout and name their inputs.**

### 4.1 — The attention queue: an inbox of work blocked on a human `RANK 1`

**What it is.** A dedicated operator surface whose only job is *what needs you*. Concretely, in Paperclip:

- **`/inbox` is the operator's primary action centre**, aggregating *"everything that needs human attention,
  with approvals as the highest-priority category"*, in the order **approvals** → **alerts** (*"Agent errors
  (failed heartbeats, error status) and budget alerts"*) → **stale work** (*"Tasks in `in_progress` or `todo`
  with no activity…beyond a configurable threshold"*), with a sidebar badge: *"The sidebar badge count
  reflects total unread/unresolved inbox items."*[^ui-spec]
- **Every row is typed.** *"Every row now resolves to `blocking` (failed run, agent error, blocked
  dependency, recovery, budget) or `review`"*.[^decision-sheet]
- **Every stalled row carries its actions inline** — *"one-click Approve, Request changes, and Send back to
  work"*, rendered both on the issue page and on the `/decisions` feed's `AttentionQueueRow`.[^commit-10675]
- **The row states who owes the decision.** A `reviewAttention` field *"describes what is under review (bound
  target with links), who decides, since when, and whether the review is stalled."*[^commit-10675]
- **Backing surfaces exist as shipped pages**: `Inbox.tsx`, `DecisionQueuePage.tsx`, `Approvals.tsx`,
  `ApprovalDetail.tsx`, `MyIssues.tsx`, `Dashboard.tsx`, `DashboardLive.tsx`, `Activity.tsx`, all present in
  `ui/src/pages/`.[^ui-pages] **No file count is asserted for that directory — four fetches returned four
  different totals, all claiming completeness; see §5(c).** The eight names above were independently
  corroborated in critic round 1; the size of the directory was not, and nothing in this paper rests on it. The dashboard shows *"Agent status"*, *"Task
  breakdown"*, *"Stale tasks"*, *"Cost summary"*, *"Recent activity"*, and marks blocked tasks — *"these need
  your attention."*[^dashboard]
- **Approvals are a distinct, structured row-type.** Approvals surface on a dedicated page — *"From the
  Approvals page, you can see all pending approvals."* — where each shows *"Who requested it and why; Linked
  issues (context for the request); The full
  payload"*; and the operator can *"Approve — the action proceeds; Reject — the action is denied; Request
  revision — ask the agent to modify and resubmit"*.[^approvals] Note the third verb: **a queue whose only
  outcomes are yes/no is under-specified**; *request revision* is the one that keeps work moving.
- **Two agents tend the queue itself.** `garden-inbox`: *"Scan a Paperclip user's Mine inbox, classify
  reversible archive candidates, request checkbox confirmation, and archive only accepted
  selections."*[^skill-garden] And `diagnose-why-work-stopped`: *"Diagnose stalled, looping, or
  over-recovered Paperclip issue trees and propose a no-code product-rule plan"*, built around three stated
  invariants — *"Productive work continues"*, *"Only real blockers stop work"*, *"No infinite
  loops"*.[^skill-diagnose] **Those three invariants are a better statement of the design goal than anything
  in the product docs**, and they transfer verbatim to a fabric of unattended edges. *(derived.)*

**Why it matters for the federated destination.** In a fabric of many edges across many MDCs running
unattended, the operator cannot watch runs; they can only be *interrupted correctly*. The scarce resource is
human decisions, and the queue of them is the control surface. Paperclip's ordering — approvals first,
errors second, silence third — is a shipped answer to *what interrupts a human first*, arrived at over five
months of production. This repo currently has **no such surface**: `/standup` reads PR threads, Issues and
the standup tracker into a morning brief,[^system-overview] which is a *digest*, not a queue — it has no
notion of a row that is blocking, no responsible party, and no next action per row.

**Cost to build here.** *(derived — inputs: Paperclip's component inventory of 24 shared primitives / 206
feature components / 73 pages;[^component-inventory] this repo's existing three memory surfaces and
`/standup`;[^system-overview] and the observation that in our case aggregation, not rendering, is the work.)*
Two shapes, and they should not be conflated:

| Shape | Scope | Order of magnitude | Dependencies |
|---|---|---|---|
| **(a) Text queue in `/standup`** | An explicit *Blocked — needs you* section: one row per open PR awaiting a ruling, open STOP/`research-candidate` issue, `HOLD`-ed run, and failed dispatch. Each row carries `blocking \| review`, who owes the decision, since when, and the one command that resolves it. | **hours to ~2 days** | None new. All three source surfaces already exist. |
| **(b) Web control surface** | Read-only single page over the GitHub API plus run JSONL; live status; per-row actions. | **1–3 weeks** for one person to first usable state | A server tier or a static generator — `system-overview.md` lists the server tier as **not built**.[^system-overview] |

**Recommendation: sequence (a) now, hold (b) until edge count > 1.** (a) captures most of the value at ~1% of
the cost, and §5(d) argues honestly that (b) is currently a build for a hypothetical.

### 4.2 — The maintained-path invariant, and the "invisible zombie" scar `RANK 2`

**This is the highest-value single artifact in the paper**, because it is a production failure narrated by
the people who hit it, and the same failure is live here.

**The scar, verbatim from the commit that fixed it** (`678728f`, 2026-08-04, PR #10675, **47 changed files**,
+3,420 / −60):[^commit-10675]

> *"Agents move issues to `in_review` and rely on a 'review path' (an interaction, an approval, a monitor, or
> a named reviewer) to tell them who decides next."*
> *"That review path can silently disappear. A user comment supersedes the pending interaction, a monitor is
> exhausted, or a run ends without restoring a path."*
> *"Such issues become invisible zombies. Nobody knows a decision is owed, so the work stalls forever."*

**The fix has four parts**, and the shape matters more than the code: (1) *"Maintain the review path as a
server invariant"* — the server derives and persists a path whenever an issue enters or sits in `in_review`,
and *"recovers a stale path with one bounded wake instead of leaving the issue pathless"*; (2) a
`reviewAttention` field exposing what/who/since-when/stalled; (3) inline decision routes; (4) a UI panel
that *"never renders empty"* — an amber *"nobody is reviewing this"* notice when no path exists.[^commit-10675]

**The alternatives they rejected are as instructive as what they built.** *"A pure background auto-recovery
sweep. This stays opt-in and is not enough on its own, because it is invisible to the human. A bare status
banner. This is rejected, because it gives no action to resolve the stall."*[^commit-10675] **Auto-recovery
without visibility, and visibility without an action, were both judged insufficient.**

**Why it matters for the federated destination.** Our entire memory model is *"Open is the to-do
bit"*[^system-overview] — an open PR, an open issue. That model has exactly this failure: an open PR whose
reviewer never ruled, an issue filed by a workflow with no named responsible party, a `HOLD(redispatch)` that
looped back once and stopped. **Each is an invisible zombie by Paperclip's definition, and nothing in this
repo detects one.** Multiply by many edges and many MDCs and the failure becomes the dominant one.

**The transferable rule** *(derived — inputs: the commit above plus `system-overview.md`'s memory table)*:
*every artifact that enters a "waiting on a decision" state must carry a durable pointer to who decides and
what the next action is; the absence of that pointer is itself a first-class, surfaced state.*

**Cost to build here.** *(derived — inputs: PR #10675's 47-file / 3,480-line footprint, discounted because we
have no in-app UI and no server invariant to maintain; our equivalent is a rule plus a detector.)* **A day or
less for the rule**, expressed as a Research/Workflow standard amendment ("a no-change outcome files an issue
naming a responsible party and a next action") plus a detector in the `/standup` aggregator from §4.1(a).
Dependencies: none — and it is the natural first row-type for §4.1(a), so sequence them together.

### 4.3 — Recovery as a first-class entity with database-enforced idempotency `RANK 3`

**What it is.** Paperclip does not treat recovery as a retry; it treats it as a **record**. Migration `0084`
creates `issue_recovery_actions` with `kind`, `status`, `owner_type`, `cause`, `fingerprint`, `evidence`
(jsonb), `next_action`, `wake_policy`, `monitor_policy`, `attempt_count`, `max_attempts`, `timeout_at`,
`last_attempt_at`, `outcome`, `resolution_note`, `resolved_at`.[^mig-0084]

**And the uniqueness is enforced in Postgres, not in application code** — five partial unique indexes across
three migrations:[^mig-0084][^mig-0069][^mig-0206]

```sql
-- 0084: at most one active recovery per source issue, and per (source, cause, fingerprint)
CREATE UNIQUE INDEX IF NOT EXISTS "issue_recovery_actions_active_source_uq" ON "issue_recovery_actions"
  USING btree ("company_id","source_issue_id")
  WHERE "issue_recovery_actions"."status" in ('active', 'escalated');
CREATE UNIQUE INDEX IF NOT EXISTS "issue_recovery_actions_active_fingerprint_uq" ON "issue_recovery_actions"
  USING btree ("company_id","source_issue_id","cause","fingerprint")
  WHERE "issue_recovery_actions"."status" in ('active', 'escalated');

-- 0069: at most one open liveness-escalation issue per incident, and per leaf fingerprint
CREATE UNIQUE INDEX IF NOT EXISTS "issues_active_liveness_recovery_incident_uq" ON "issues"
  USING btree ("company_id","origin_kind","origin_id")
  WHERE "origin_kind" = 'harness_liveness_escalation' AND "origin_id" IS NOT NULL
    AND "hidden_at" IS NULL AND "status" NOT IN ('done', 'cancelled');
CREATE UNIQUE INDEX IF NOT EXISTS "issues_active_liveness_recovery_leaf_uq" ON "issues"
  USING btree ("company_id","origin_kind","origin_fingerprint")
  WHERE "origin_kind" = 'harness_liveness_escalation' AND "origin_fingerprint" <> 'default'
    AND "hidden_at" IS NULL AND "status" NOT IN ('done', 'cancelled');

-- 0206: at most one un-skipped review-path-lost recovery wake per company+key
CREATE UNIQUE INDEX "agent_wakeup_requests_review_path_recovery_idempotency_uq" ON "agent_wakeup_requests"
  USING btree ("company_id","idempotency_key")
  WHERE "agent_wakeup_requests"."idempotency_key" LIKE 'issue_review_path_lost:%'
    AND "agent_wakeup_requests"."status" <> 'skipped';
```

**What the two migrations actually encode is a GRANULARITY CHOICE, and the two files resolve it differently.**
Both ship two indexes, but they are not the same construction and an earlier draft of this section claimed
they were:

- **0069's pair is genuinely complementary.** `..._incident_uq` keys on `(company_id, origin_kind, origin_id)`
  under `origin_id IS NOT NULL`; `..._leaf_uq` keys on `(company_id, origin_kind, origin_fingerprint)` under
  `origin_fingerprint <> 'default'`. **Different third column, different extra predicate — neither key is a
  superset of the other and neither predicate implies the other**, so both constraints do independent work.
- **0084's pair is not.** `..._active_source_uq` keys on `(company_id, source_issue_id)` and
  `..._active_fingerprint_uq` on `(company_id, source_issue_id, cause, fingerprint)` — **under the identical
  partial predicate** `status in ('active','escalated')`. The second key is a strict superset of the first,
  and **uniqueness on a subset implies uniqueness on any superset**, so the coarse index already enforces the
  fine one. The fine index is *subsumed*: defensive, or positioned for a later relaxation of the coarse
  guard. **A single index would do here.**

**The transferable insight is the choice, not a mandatory pair.** A **coarse** guard (one open recovery per
work item, whatever the cause) forbids two different failures on the same item from being recovered
concurrently — safest, and it is what 0084 actually enforces. A **fine** guard alone (one open recovery per
distinct cause) permits that concurrency. **Which one you want is a design decision with a real trade-off,
and shipping both under identical predicates does not buy the second property — it buys nothing.**

*(derived — inputs: the five statements above and their `WHERE` clauses. **An earlier draft asserted "a single
index cannot do both, which is why there are two"; that is false for 0084 and is withdrawn.** The error is
instructive: it was produced by reading the two files as instances of one pattern rather than comparing their
key columns and predicates, and it is falsifiable in thirty seconds against the SQL block above — which is
exactly the check that was not run.)*

The same discipline appears on plan decomposition, which the execution-semantics doc calls *"an exact-once
control-plane primitive"* keyed on *"`(sourceIssueId, acceptedPlanRevisionId)`"*[^exec-semantics] and which
the schema enforces as `issue_plan_decompositions_source_revision_uq`.[^schema-decomp] And on user-facing
thread interactions, migration `0064` adding an `idempotency_key` column plus
`issue_thread_interactions_company_issue_idempotency_uq`.[^mig-0064]

**Recovery is also bounded, in prose that reads like a hard-won rule.** *"Paperclip queues at most one
continuation for the same recovery fingerprint"*; *"if that recovery wake also finishes and the issue is
still stranded, Paperclip moves the issue to `blocked`"*; *"after N attempts (N = 2–3) on the same fingerprint
lineage…the platform stops re-firing"*; *"after three consecutive continuation wakes are cancelled…recovery
converts a real dependency wait."*[^exec-semantics]

**Why it matters for the federated destination.** *The process that would deduplicate a recovery attempt is
the process that died.* That is why the dedupe lives in a unique index rather than in a service. This is a
**validating** finding, not an additive one: it prices what *not* choosing a durable engine costs. Paperclip
spent at least five dedicated migrations, a watchdog subsystem, a stop-fingerprint mechanism and a bounded
continuation state machine to re-derive properties Temporal provides as workflow-ID reuse policy, activity
retry policy and deterministic replay.[^temporal-paper]

**Cost to build here.** *(derived — inputs: the five migrations above; `raw/temporal.md`'s account of what
the engine provides.)* **Near zero incremental if the Temporal port lands**; the cost is *avoided*, and this
paper's role is to quantify the avoidance. **The one thing that does NOT come free** is the *taxonomy* —
`cause`, `fingerprint`, `evidence`, `next_action`, `max_attempts`, `outcome` are a design, not a runtime
feature, and Temporal supplies none of it. **Adopt the taxonomy, not the machinery: ~a day of schema/type
design inside `Phase: Temporal Integration`.**

### 4.4 — Process-loss detection by output silence, not by liveness ping `RANK 4`

**What it is.** `heartbeat_runs` carries, alongside the usual run fields, a dedicated liveness cluster:
`processPid`, `processGroupId`, `processStartedAt`, `lastOutputAt`, `lastOutputSeq`, `lastOutputStream`,
`lastOutputBytes`, `processLossRetryCount`, `retryOfRunId`, `scheduledRetryAt`, `scheduledRetryAttempt`,
`scheduledRetryReason`, `livenessState`, `livenessReason`, `continuationAttempt`, `lastUsefulActionAt`,
`nextAction`, `contextSnapshot` — with indexes
`heartbeat_runs_company_status_last_output_idx (companyId, status, lastOutputAt)` and
`heartbeat_runs_company_status_process_started_idx (companyId, status, processStartedAt)`.[^schema-runs]
Watchdog verdicts get their own table, `heartbeat_run_watchdog_decisions`, with `decision`, `snoozedUntil`,
`reason` and provenance columns.[^schema-watchdog]

A **second** watchdog operates one level up, over an issue subtree rather than a process: it fires *"When
every leaf in that subtree comes to rest — done, cancelled, blocked, in review, or waiting on an
interaction"*, treats the subtree as live if *"any included issue has a live run (`queued`, `running`,
`scheduled_retry`), a queued wake
request, or a scheduled retry"*, and then either leaves genuinely-complete leaves alone *"with a short note on
what was checked"* or, if a leaf is not genuinely complete, acts to *"restore a live path: reopen the issue,
reassign, comment actionable instructions…"*[^watchdog-doc] It dedupes against a
`lastReviewedFingerprint`,[^watchdog-doc] persisted as `last_observed_stop_snapshot` /
`last_reviewed_stop_snapshot` on `issue_watchdogs` by migration `0192`.[^mig-0192] **Two watchdogs at
two altitudes — one asking "is this process producing anything?", one asking "did this tree of work actually
finish?" — is the shape worth copying, not either one alone.** *(derived.)*

The rule the process-level columns implement: *"Paperclip treats prolonged output silence as a watchdog
signal"*, with *"a 30-minute default re-arm window before the watchdog evaluates the still-silent run
again."*[^exec-semantics]
And the framing that makes it work: *"an issue is healthy when the product can answer 'what moves this
forward next?'"*; *"An issue is stalled when it is non-terminal but has no live execution path, no explicit
waiting path, and no recovery path."*[^exec-semantics] **All three negatives are load-bearing and an earlier
draft of this paper quoted only the first.** A detector that fires on "no live execution path" alone raises an
alarm on every legitimately-waiting item — it manufactures exactly the false-alarm noise §4.1 and §5(d) warn
against. *The correct predicate is the conjunction: not running, not waiting, and not already being
recovered.* Coalescing prevents duplicate work: *"If an agent is already running, new wakeups
are merged (coalesced) instead of launching duplicate runs."*[^agents-runtime]

**Why it matters for the federated destination.** For a long agentic CLI run, *"is the process alive"* is the
wrong question — a wedged agent has a live PID. The right questions are **has it emitted output recently**
and **has it taken a useful action** (`lastOutputAt`, `lastUsefulActionAt`). Our `Phase: Temporal Integration`
must decide what a `claude_cli` activity heartbeat *carries*; `raw/python_sdk_long_activities.md` treats the
heartbeat mechanism, and this is the payload-design answer from production. **A heartbeat that only proves
liveness cannot distinguish a working agent from a wedged one.**

**Cost to build here.** *(derived — inputs: the schema above; `raw/python_sdk_long_activities.md`'s account
of Temporal activity heartbeating.)* **Small — hours of design, but it must land BEFORE workers are
written**, because it constrains the activity's heartbeat payload and its cancellation semantics. Dependency:
the `claude_cli` activity design in `Phase: Temporal Integration`. **This is a sequencing constraint, not a
work item.**

### 4.5 — The adapter contract, `testEnvironment` preflight, and the skills-injection rule `RANK 5`

**What it is.** Paperclip's edge boundary is an explicit three-consumer contract. Root metadata exports
`type` (*"snake_case, globally unique"*), `label`, `models`, `agentConfigurationDoc`. The **server** layer
provides `execute(ctx: AdapterExecutionContext): Promise<AdapterExecutionResult>`,
`testEnvironment(ctx): Promise<AdapterEnvironmentTestResult>`, and a `sessionCodec`. The **UI** layer provides
`parseStdoutLine(line, ts): TranscriptEntry[]` and `buildAdapterConfig(values)`. The **CLI** layer provides
`formatStdoutEvent(line, debug)`.[^skill-adapter][^creating-adapter] Registration is
`registerServerAdapter(adapter)` / `requireServerAdapter(type)` and `registerUIAdapter` /
`findUIAdapter`.[^adapter-plugin] **At least eleven** built-in adapters ship — Claude Code (`claude_local`),
Codex (`codex_local`), Gemini CLI (`gemini_local`), OpenCode (`opencode_local`), Cursor (`cursor`), Pi
(`pi_local`), Hermes (`hermes_local`), Hermes Gateway (`hermes_gateway`), OpenClaw Gateway
(`openclaw_gateway`), Process (`process`), HTTP (`http`) — with **a twelfth, Droid (`droid_local`), reported
by an independent re-fetch that my own two fetches of the same page did not return.**[^adapters-overview]
*"At least"* is deliberate: the listing disagreed across fetches, so the count is stated as a floor rather
than a total (§5(c)).

The server injects a fixed env contract: `PAPERCLIP_AGENT_ID`, `PAPERCLIP_COMPANY_ID`, `PAPERCLIP_API_URL`,
`PAPERCLIP_RUN_ID`, `PAPERCLIP_TASK_ID`, `PAPERCLIP_WAKE_REASON`, `PAPERCLIP_WAKE_COMMENT_ID`,
`PAPERCLIP_APPROVAL_ID`, `PAPERCLIP_APPROVAL_STATUS`, `PAPERCLIP_LINKED_ISSUE_IDS`,
`PAPERCLIP_API_KEY`.[^skill-adapter]

**Three items inside this are individually worth taking:**

1. **`testEnvironment` as a first-class preflight.** A per-adapter probe answering *can this runtime actually
   do the job here* — Claude's is `claude --print - --output-format stream-json --verbose`.[^claude-local]
   **This is the capability-advertisement primitive a dedicated-edge model needs**, and differentiator #2's
   design currently has no equivalent. An edge that cannot prove its capability before claiming work is an
   edge that fails at the worst moment. *(derived — inputs: the adapter contract; `problem-statement.md`
   differentiator #2.)*
2. **The skills-injection rule, actionable today.** *"Never copy or symlink skills into the agent's `cwd`.
   The cwd is the user's project checkout."*[^skill-adapter] Instead: *"The adapter creates a temporary
   directory with symlinks to Paperclip skills and passes it via `--add-dir`."* / *"This makes skills
   discoverable without polluting the agent's working directory."*[^claude-local] This repo symlinks
   `config/` into `~/.claude/` globally,[^system-overview] which works for one operator on one machine; when
   edges run against arbitrary checkouts on machines we do not own, the `--add-dir` temp-symlink-farm is the
   ready-made answer.
3. **Untrusted-output discipline.** *"Treat agent output as untrusted…Parse defensively: Never `eval()` or
   dynamically execute anything from output."*[^skill-adapter] Reinforced by the `low_trust_review` preset,
   whose stated reason is that *"a contained run reads untrusted input, so a free-prose comment into the
   higher-trust parent thread is a prompt-injection promotion path."*[^low-trust]

**Cost to build here.** *(derived — inputs: the contract above; our worker/activity split in
`system-overview.md`.)* The **skills-injection change is hours**. The **`testEnvironment` analogue is
small-to-medium (~2–4 days)** but is an *interface* decision that must be taken alongside the Temporal worker
registration contract, not after it. Dependency: `Phase: Temporal Integration`, worker startup.

### 4.6 — Credentials at the edge: precedent exists, and it corrects a claim `RANK 6`

**What it is.** Claude Code auth in Paperclip is *"Either `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` in
adapter or environment env (or host env)"* **or** *"a Claude Code subscription login available to the
execution target"*.[^claude-local] The precedence is stated explicitly: *"If `ANTHROPIC_API_KEY` is set in adapter env
or host environment, Claude uses API-key auth instead of subscription login."*[^agents-runtime] — i.e.
**subscription login is what happens when no key is present.** Credential home is an adapter-level decision:
*"The adapter decides which credential home is authoritative before the CLI starts."*[^adapters-overview] For
managed remote runs, *"credentials baked into the sandbox image win for managed remote Claude runs"* and
*"The sandbox snapshot owns the credential for the run"*, with Paperclip uploading *"only the sanitized
config seed."*[^claude-local]

**Why it matters, and what it corrects.** The problem statement frames centralized platforms as paying for
orchestration with *"credentials that must leave the machine they belong to…"*[^problem-statement] **The
largest player in the category does not require that for local Claude Code runs.** Our credentials-stay-at-
the-edge position therefore has **precedent at scale**, which cuts both ways honestly: it de-risks the
position (someone with 75k stars ships it) and it removes any claim that the position is unusual. The
distinction that survives is narrower and still real — Paperclip *also* stores company secrets server-side
and injects them into runs,[^readme][^database] so *provider* credentials at the edge coexists with a central
secret store for everything else.

**Cost to build here.** **Zero — this is a correction, not a capability.** It changes a claim, not a
backlog. It also validates `raw/anthropic_tos_and_enterprise.md`'s question with a large real-world data
point.[^anthropic-tos]

### 4.7 — Coordination: a third shape, and it refines differentiator #2 `RANK 7`

**What it is, and it settles a prior open question.** The prior paper marked Paperclip's E3 (code-routed
control flow) undocumented and called it *"the single most decision-relevant fact still open."*[^prior-art]
The answer is **hybrid, and the split is clean**:

- **The lifecycle state machine is code.** Wake dispatch, coalescing, checkout locking, review-path
  maintenance, watchdog evaluation, bounded continuation, recovery fingerprinting — all server-side code over
  typed DB rows.[^exec-semantics][^commit-10675][^schema-runs]
- **What work exists and who does it is model-decided.** The CEO agent decomposes the goal and *"assigns
  tasks directly"*;[^delegation] plan decomposition is a model output that the server then treats as an
  exact-once primitive.[^exec-semantics][^schema-decomp]

On the claim-and-contend axis, Paperclip is **neither** central-queue role-pull **nor** dedicated edges:

| Model | Who decides the assignee | Contention |
|---|---|---|
| Central queue + role advertisement (bernstein) | the queue, by role match | real; claim-and-contend[^prior-art] |
| **Paperclip** | **a manager agent, to a named employee** | **residual — atomic checkout, `409 Conflict`, "pick a different task"**[^task-workflow] |
| This repo (designed) | the edge's identity — it sees only its own work | none by construction[^problem-statement] |

**Why it matters.** Differentiator #2 asserts *"The common model is a central queue where workers advertise a
role and claim from a shared pool…"*[^problem-statement] **The largest player is a partial counter-example**:
it directs work to a named agent. But it is not our model either — its "worker" is a logical employee that
can share a host with other employees, so the machine-identity binding that makes our edges non-fungible is
absent. **The honest revision: "common" overstates it; the field has at least three shapes, and ours is
distinguished by binding worker identity to a machine and a credential rather than to a label or a job
title.** *(derived — inputs: §2.5, §2.6, delegation.md, task-workflow.md, and the prior paper's bernstein
cluster findings.)*

**Cost to build here.** **Zero — this is a claim refinement.** It should change one sentence in
`problem-statement.md` § *Where we actually differ* #2 through the normal human-ratified path, not through
this paper.

## 5. Honest boundary analysis — the case against this paper

**(a) Documentation, schema and commit messages. Nothing was executed.** Every behavioural claim is inferred
from structure. A `heartbeat_run_watchdog_decisions` table is not a working watchdog; a unique index proves a
constraint exists, not that the code path that would violate it is ever reached. **The single largest
weakness**, and test-plan items 1 and 2 are its direct tests.

**(b) The observed corruption mode is ELISION, not garbling — measured, and the correction is the useful
part.** An earlier draft of this section predicted that a summarizing model reproducing a long block would
garble clauses *inside* it, and named the long SQL/commit blocks as the byte-verification priority for that
reason. **Independent re-fetching falsified the prediction**: every long reproduced block in §4.2 and §4.3
was byte-accurate, character for character. What actually went wrong was the opposite shape, and it is more
dangerous because it leaves no visible seam:

- **A whole statement dropped from a block presented as reproduced.** §4.3's 0069 block originally showed one
  of the file's *two* partial unique indexes; `issues_active_liveness_recovery_leaf_uq` was simply absent, and
  the surviving text was well-formed SQL. The paper's own prose said *"per incident, and per leaf
  fingerprint"* — **the inline description contradicted the block above it, and that contradiction was the
  only available tell.**
- **Sentence tails truncated and closed with a period rather than an ellipsis**, which converts a partial
  quote into an apparently-complete one. The worst instance was §4.4's *"stalled"* definition, where dropping
  two of three conditions **inverts the rule the section teaches** (now restored, with the failure recorded
  in-place).

**The lesson generalises past this paper: a fetched long block is trustworthy character-by-character and
untrustworthy statement-by-statement.** Verify *completeness* against the source's structure — statement
count, bullet count, list length — not *fidelity* of the text you were given. Internal contradiction between
a block and the prose describing it is the cheapest available detector.

**A third mode appeared in round 2, and it is the one to watch: the REPAIR introduced the defect.** Fixing
§2.4's truncated quote restored the missing parenthetical, **inserted a word the source does not contain
(*"runtime"*), and dropped a different clause** — converting a truncation defect into a fabrication defect
while appearing to resolve it. Round 1's version had no inserted word. **A repair to a quote is a new quote
and carries the same verification duty as the original**, but it is systematically less likely to get one,
because attention is on the item being closed rather than on the text being written. **Re-verify repaired
spans against the source, not against the correction notice.**

**(c) A measured enumeration failure inside this paper.** The GitHub *contents* API listing of
`packages/db/src/migrations` was summarized as **95 entries** ending at `0094_…`. The *git trees* API on the
identical path returned **207 objects, 206 `.sql`, `truncated: false`**, ending at `0206_…`.[^tree-migrations]
The trees answer is corroborated three ways: the highest filename is `0206`; PR #10675's Risks section says it
*"adds migration `0200` (next after master `0199`, no renumber)"*[^commit-10675] — and a *later* renumber to
0206 is consistent with the repo's documented practice, PR #4244 recording *"renumbered branch migrations to
`0063` and `0064`"*[^commit-4244]; and the dispatch's own prior "200+" figure matches. **The contents-API
count was wrong by 2×.** This is a *new* failure mode beside the known wrong-branch-404: a summarizing fetch
can silently under-enumerate a listing.

**The rule that draft produced was too weak, and this paper then violated it.** The draft rule was *"use the
git trees API, never a summarized contents listing."* Two things falsified it. First, the paper asserted a
file count for `ui/src/pages` **sourced from the contents API** — the very method it had just ruled out.
Second, when that count was re-sourced, **the trees API did not agree with itself**: **four** fetches of the
same directory returned **four** totals — **147** (contents), then **169**, **181** and **183** (trees) —
**every one of them reporting `truncated: false`**. A same-hour push cannot plausibly account for the spread,
and `truncated: false` is precisely the field that is supposed to certify completeness. The adapter list
behaved the same way: two of my fetches enumerated eleven built-in adapters, an independent fetch of the
identical page enumerated twelve.

**The corrected rule, and it is stricter:**

1. **A count is a finding only when it is corroborated by a second, structurally different signal.** The
   206-migration figure survives because it is cross-checked by monotonic filename numbering *and* by two
   commit messages naming migration numbers — not because the trees API said so.
2. **An uncorroborated count is stated as a floor ("at least N") or not stated at all.** The `ui/src/pages`
   count is now **dropped** from §4.1; the adapter count is now **"at least eleven."** Neither carried any
   argument, which is why dropping them costs nothing — *and that is the test to apply before quoting any
   count: if the number is load-bearing, corroborate it; if it is decoration, delete it.*
3. **The `.agents/skills` count of 20 is retained** because §5(g)'s "17 of 20" scoping depends on it and it
   was independently confirmed via trees.[^agents-skills]
4. **The rule governs counts the paper MEASURES, not counts a source STATES.** §4.1's cost inputs cite 24
   shared primitives / 206 feature components / 73 pages — those are **assertions inside
   `COMPONENT-INVENTORY.md`**, quoted like any other first-party claim and verified exact against it, not
   totals I obtained by enumerating a directory. A stated count inherits the reliability of its document; a
   measured count inherits the reliability of the enumeration, which is what failed here. **Conflating the
   two would either over-trust my arithmetic or gratuitously discard a source's own figures.** The tell is
   simple: *did I count, or did I quote?*

**(d) The strongest case against §4.1 is that we have one operator.** An attention inbox is a solution to
*many things demand a scarce human*. Today: one operator, a handful of dispatches, and `/standup` already
reads all three memory surfaces.[^system-overview] The federated fabric that justifies a control surface **does
not exist yet** — the SkyyNet/SkyyCommand frame is explicitly a stub.[^problem-statement] Building shape (b)
now would be building for a hypothetical, and this paper deliberately recommends shape (a) instead. **A
reviewer who thinks even (a) is premature has a defensible position**; the counter is that §4.2's zombie
failure mode is *already occurring* at one operator, which is an argument about correctness rather than scale.

**(e) 75,610 stars is a popularity signal, not a production-validation signal.** An independent analysis
records the project as *"Pseudonymous, unfunded, single-maintainer-heavy"* with high bus-factor risk, notes
the issue backlog outpacing maintainers, and states plainly that *"Star counts still overstate verified
production usage."*[^rywalker] *(rendered third-party page — reduced confidence per the raw-over-rendered
rule; the governance facts it asserts are corroborated by the repo's own 5,060 open issues.[^gh-api])*
**Consequence for this paper: lessons mined from Paperclip's SCARS (commit rationale, migrations, partial
unique indexes) are load-bearing; lessons mined from its CLAIMS (README feature bullets) are not.** §4.2–§4.4
are scars. §4.1 is a mix — the surface is shipped code[^ui-pages] but its effectiveness is unmeasured.

**(f) The case against my own §3 verdict: the ontology may be more general than I allowed.** Paperclip
explicitly denies being a code tool[^readme] and ships HTTP/webhook adapters.[^adapters-overview] Strip the
*metaphor* (CEO, employees, board) and the *structure* that remains — a work item with a single assignee,
atomic checkout, goal ancestry, a maintained decision path, and a bounded recovery record — is domain-general
and would describe a building-controller edge as readily as a coding one. **If the objection is to the naming
rather than the model, §3 rejects more than it should.** I hold the verdict because differentiator #2's
machine-bound, non-fungible worker is genuinely absent, not merely differently named — but a reviewer is
entitled to push back here and §4.7 already concedes ground on the adjacent claim.

**(g) Named coverage gaps** *(stated with method, per §3)*. Located via the contents API and **deliberately
not fetched** for budget: `doc/SPEC.md`, `doc/SPEC-implementation.md`, `doc/AGENT-ARTIFACTS.md`,
`doc/AGENTCOMPANIES_SPEC_INVENTORY.md`, `doc/TASKS.md`, `doc/MCP-ACCESS-GOVERNANCE.md`, `doc/CLIPHUB.md`,
`docs/plans/`, `docs/pipelines-tutorial.md`, `docs/built-in-agents.md`, `evals/promptfoo`,[^evals] and 17 of
the 20 `.agents/skills/` definitions.[^agents-skills] **Any claim of absence about Paperclip in this paper is
scoped to the ~30 documents actually fetched** and must not be read as a claim about the repository.

**(h) No TypeScript was read.** Schema and SQL show structure; commit messages show intent; neither shows
behaviour. Specifically unverified: whether the wake dispatcher honours the coalescing it documents, whether
the 30-minute silence window is the shipped default, and whether `testEnvironment` is called on any path other
than the config UI.

**(i) Recency risk is severe and asymmetric.** The repo was pushed the day of this sweep and the §4.2 artifact
merged that same day.[^gh-api][^commit-10675] The **feature** claims in §4.1 and §4.5 could be stale within
weeks. The **scar** claims in §4.2–§4.4 age far better — a lesson about invisible zombies does not expire when
the UI is refactored.

## 6. What this provides — the enumerated, plannable list

For the master-planning pass. Each row is sequenceable; costs are `derived` and their inputs are named in §4.

| # | Capability | Where it lands | Cost (order of magnitude) | Hard dependency |
|---|---|---|---|---|
| 1 | **Blocked-work queue in `/standup`** — typed rows (`blocking`/`review`), responsible party, since-when, one resolving command | New roadmap item; currently **homeless** | hours – 2 days | none |
| 2 | **Maintained-decision-path rule** — no artifact may sit in a waiting state without a named decider and next action; absence is a surfaced state | Standards-amendment candidate + row-type for #1 | ≤ 1 day | sequence with #1 |
| 3 | **Recovery taxonomy** — `cause`, `fingerprint`, `evidence`, `next_action`, `max_attempts`, `outcome` as typed fields on retried work. **Plus one explicit ruling: dedupe granularity.** Coarse (one open recovery per work item, whatever the cause) or fine (one per distinct cause, permitting concurrent recovery of different failures)? They are alternatives with a real trade-off — **not a pair to build both of**; see §4.3 | `Phase: Temporal Integration` | ~1 day design | Temporal port |
| 4 | **Liveness payload design** — activity heartbeat carries `lastOutputAt` + `lastUsefulActionAt`, not just aliveness; silence threshold with re-arm. **The stalled predicate is a three-way conjunction: not running AND not waiting AND not already being recovered** — a detector on "not running" alone alarms on every legitimately-waiting item (§4.4) | `Phase: Temporal Integration`, **before** workers are written | hours (design), constrains build | `claude_cli` activity design |
| 5 | **Skills injection via `--add-dir` temp symlink farm** — never pollute the checkout | `Phase: Temporal Integration` / edge worker | hours | none |
| 6 | **`testEnvironment`-style capability preflight at worker registration** | `Phase: Temporal Integration`, worker startup | 2–4 days | worker contract |
| 7 | **Web control surface** | Deferred — hold until edge count > 1 | 1–3 weeks | server tier (**not built**) |
| — | *Claim correction:* subscription-at-the-edge has precedent; drop any uniqueness framing | `problem-statement.md` (human-ratified path) | 0 | — |
| — | *Claim correction:* "the common model is central-queue role-pull" overstates; three shapes exist | `problem-statement.md` #2 (human-ratified path) | 0 | — |
| — | *Cost avoided, quantified:* five migrations + watchdog subsystem + stop-fingerprint mechanism is what hand-rolled durability costs at Paperclip's scale | Evidence for `Phase: Temporal Integration` | 0 | — |

## 7. The roadmap item's answer

**Verdict: MINE AND DISCARD, and rewrite the item.**

**Do not adopt.** Adoption means taking a Node/Postgres server as the backbone, replacing Temporal with
hand-rolled durability, and accepting a company-of-employees ontology. All three contradict committed
direction (§3).

**Do not ignore.** Seven transferable items (§4), of which #1 and #2 fill a gap the roadmap does not
currently hold and #3–#6 are design constraints on a phase that is already committed.

**The item's own text is wrong and should be replaced.** It describes *"visual workflow design"* and *"PR
review"*, both explicitly disclaimed by the product.[^roadmap][^readme] It also asks whether Paperclip
*"may overlap with native headless mode + triggers."* **It does not overlap.** Native headless mode is a way
to *invoke* an agent; Paperclip is a control plane that *decides when to invoke*, *records what happened*,
*detects that nothing is happening*, and *shows a human what is blocked*. Those are complements, and
Paperclip's own adapter layer invokes headless Claude Code (`claude --print … --resume`) as its
substrate.[^claude-local] **The question "does it overlap?" has been the wrong question since the item was
written.**

**And the "evaluate after Phase 4" gate should close.** The evaluation is done, ahead of the gate, because
the pool's own prior cycle flagged Paperclip as twice-misjudged. Nothing is gained by re-running it after
Phase 4.

## 8. Citations

**First-party — repository metadata and structure**

[^gh-api]: GitHub REST API, repo metadata for `paperclipai/paperclip` (JSON): `default_branch: "master"`,
  `language: "TypeScript"`, `license.spdx_id: "MIT"`, `stargazers_count: 75610`, `forks_count: 14081`,
  `open_issues_count: 5060`, `created_at: "2026-03-02T15:01:51Z"`, `pushed_at: "2026-08-04T19:12:57Z"`,
  `subscribers_count: 374`, `homepage: "https://paperclip.ing"`. Fetched 2026-08-04.
  https://api.github.com/repos/paperclipai/paperclip
[^tree-migrations]: GitHub REST *git trees* API for `master:packages/db/src/migrations` — **207 objects, 206
  with a `.sql` extension, `truncated: false`**; highest-numbered
  `0206_review_path_recovery_idempotency_index.sql`. Fetched 2026-08-04.
  https://api.github.com/repos/paperclipai/paperclip/git/trees/master:packages%2Fdb%2Fsrc%2Fmigrations
[^ui-pages]: GitHub contents API, `ui/src/pages` — **no file count is cited from this source; four fetches
  returned four totals (147 / 169 / 181 / 183), all reporting `truncated: false`. See §5(c).** The eight
  named files — `Inbox.tsx`, `DecisionQueuePage.tsx`, `Approvals.tsx`, `ApprovalDetail.tsx`, `MyIssues.tsx`,
  `Dashboard.tsx`, `DashboardLive.tsx`, `Activity.tsx` — were **independently corroborated present in critic
  round 1** via a trees fetch answering per-name. Only the directory size is unresolved.
  https://api.github.com/repos/paperclipai/paperclip/contents/ui/src/pages?ref=master
[^agents-skills]: GitHub contents API, `.agents/skills` — 20 skill directories including `create-agent-adapter`,
  `diagnose-why-work-stopped`, `garden-inbox`, `check-pr`, `pr-gardening`, `prcheckloop`. **The count of 20 is
  the one directory count this paper retains**, because §5(g)'s "17 of 20" scoping depends on it and it was
  independently corroborated via the git trees API in critic round 1.
  https://api.github.com/repos/paperclipai/paperclip/contents/.agents/skills?ref=master
[^evals]: GitHub contents API, `evals` — `README.md`, `promptfoo/`.
  https://api.github.com/repos/paperclipai/paperclip/contents/evals?ref=master

**First-party — raw SQL migrations and Drizzle schema (strongest source class in this paper)**

[^mig-0064]: `packages/db/src/migrations/0064_issue_thread_interaction_idempotency.sql` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/migrations/0064_issue_thread_interaction_idempotency.sql
[^mig-0069]: `packages/db/src/migrations/0069_liveness_recovery_dedupe.sql` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/migrations/0069_liveness_recovery_dedupe.sql
[^mig-0084]: `packages/db/src/migrations/0084_issue_recovery_actions.sql` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/migrations/0084_issue_recovery_actions.sql
[^mig-0192]: `packages/db/src/migrations/0192_task_watchdog_stop_snapshots.sql` (raw) — adds
  `last_observed_stop_snapshot` and `last_reviewed_stop_snapshot` (jsonb) to `issue_watchdogs`.
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/migrations/0192_task_watchdog_stop_snapshots.sql
[^mig-0206]: `packages/db/src/migrations/0206_review_path_recovery_idempotency_index.sql` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/migrations/0206_review_path_recovery_idempotency_index.sql
[^schema-runs]: `packages/db/src/schema/heartbeat_runs.ts` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/schema/heartbeat_runs.ts
[^schema-wakeup]: `packages/db/src/schema/agent_wakeup_requests.ts` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/schema/agent_wakeup_requests.ts
[^schema-watchdog]: `packages/db/src/schema/heartbeat_run_watchdog_decisions.ts` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/schema/heartbeat_run_watchdog_decisions.ts
[^schema-decomp]: `packages/db/src/schema/issue_plan_decompositions.ts` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/packages/db/src/schema/issue_plan_decompositions.ts

**First-party — commit provenance**

[^commit-10675]: Commit `678728f650bf2a03f325922db32efb038dbb6ac9`, 2026-08-04T18:54:40Z — *"feat: maintained
  in_review review-path contract + stalled-review actions (#10675)"*; `changed_files: 47` per
  `pulls/10675` (the commit's own `files` array carries 49 entries), `additions: 3420`, `deletions: 60`.
  Full message retrieved via the commits API.
  https://api.github.com/repos/paperclipai/paperclip/commits/678728f650bf2a03f325922db32efb038dbb6ac9
[^commit-4244]: Commit `a95739442027bdec8d291030a91e351dc434f635`, 2026-04-22T01:15:11Z — *"[codex] Add
  structured issue-thread interactions (#4244)"*, the commit introducing migration `0064`; contains the
  migration-renumbering practice.
  https://api.github.com/repos/paperclipai/paperclip/commits?path=packages/db/src/migrations/0064_issue_thread_interaction_idempotency.sql&sha=master

**First-party — raw documentation**

[^readme]: `README.md` (raw, **`master`**).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md
[^roadmap-paperclip]: `ROADMAP.md` (raw) — *"Self-healing runs & automatic recovery"*, *"Cloud / Sandbox
  agents"*, *"queue-style work streams"*.
  https://raw.githubusercontent.com/paperclipai/paperclip/master/ROADMAP.md
[^exec-semantics]: `doc/execution-semantics.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/execution-semantics.md
[^watchdog-doc]: `doc/TASK-WATCHDOG.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/TASK-WATCHDOG.md
[^database]: `doc/DATABASE.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/DATABASE.md
[^product]: `doc/PRODUCT.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/PRODUCT.md
[^deployment-modes]: `doc/DEPLOYMENT-MODES.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/DEPLOYMENT-MODES.md
[^low-trust]: `doc/LOW-TRUST-PRESETS.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/LOW-TRUST-PRESETS.md
[^ui-spec]: `doc/spec/ui.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/spec/ui.md
[^decision-sheet]: `doc/design/DECISION-SHEET.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/design/DECISION-SHEET.md
[^component-inventory]: `doc/design/COMPONENT-INVENTORY.md` (raw) — 24 shared primitives, 206 feature
  components, 73 pages.
  https://raw.githubusercontent.com/paperclipai/paperclip/master/doc/design/COMPONENT-INVENTORY.md
[^architecture]: `docs/start/architecture.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/start/architecture.md
[^core-concepts]: `docs/start/core-concepts.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/start/core-concepts.md
[^adapters-overview]: `docs/adapters/overview.md` (raw). **Built-in adapter count is cited as a floor** — two
  fetches of this page enumerated eleven, an independent fetch enumerated twelve (adding Droid /
  `droid_local`); see §5(c).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/adapters/overview.md
[^claude-local]: `docs/adapters/claude-local.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/adapters/claude-local.md
[^creating-adapter]: `docs/adapters/creating-an-adapter.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/adapters/creating-an-adapter.md
[^adapter-plugin]: `adapter-plugin.md` (raw, repo root).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/adapter-plugin.md
[^agents-runtime]: `docs/agents-runtime.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/agents-runtime.md
[^dashboard]: `docs/guides/board-operator/dashboard.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/guides/board-operator/dashboard.md
[^approvals]: `docs/guides/board-operator/approvals.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/guides/board-operator/approvals.md
[^delegation]: `docs/guides/board-operator/delegation.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/guides/board-operator/delegation.md
[^exec-workspaces]: `docs/guides/board-operator/execution-workspaces-and-runtime-services.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/guides/board-operator/execution-workspaces-and-runtime-services.md
[^task-workflow]: `docs/guides/agent-developer/task-workflow.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/guides/agent-developer/task-workflow.md
[^skill-adapter]: `.agents/skills/create-agent-adapter/SKILL.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/.agents/skills/create-agent-adapter/SKILL.md
[^skill-garden]: `.agents/skills/garden-inbox/SKILL.md` (raw).
  https://raw.githubusercontent.com/paperclipai/paperclip/master/.agents/skills/garden-inbox/SKILL.md
[^skill-diagnose]: `.agents/skills/diagnose-why-work-stopped/SKILL.md` (raw) — *"Diagnose stalled, looping, or
  over-recovered Paperclip issue trees and propose a no-code product-rule plan."*
  https://raw.githubusercontent.com/paperclipai/paperclip/master/.agents/skills/diagnose-why-work-stopped/SKILL.md

**Third-party (reduced confidence — rendered page)**

[^rywalker]: Ry Walker, *"Paperclip: Open-Source Orchestration for Zero-Human Companies"* (published
  2026-04-14, updated 2026-06-11). Cited only for governance/adoption context. https://rywalker.com/research/paperclip

**This repo**

[^roadmap]: `docs/development/roadmap.md` § *Tools to Evaluate*.
[^problem-statement]: `docs/standards/architecture/problem-statement.md`.
[^system-overview]: `docs/standards/architecture/system-overview.md`.
[^prior-art]: `docs/standards/architecture/research/raw/combination_prior_art.md` (last validated 2026-08-03,
  Critic: PASS-WITH-FIXES) — §3.1 Paperclip entry, §5(g) the branch-404 correction, test-plan item 8.
[^temporal-paper]: `docs/standards/architecture/research/raw/temporal.md` (last validated 2026-07-04 —
  **past its revalidation window; treated as unverified**) and
  `raw/python_sdk_long_activities.md` (2026-08-03).
[^anthropic-tos]: `docs/standards/architecture/research/raw/anthropic_tos_and_enterprise.md` (2026-07-24).

**Located and deliberately not fetched** (named per §5(g)): `doc/SPEC.md`, `doc/SPEC-implementation.md`,
`doc/AGENT-ARTIFACTS.md`, `doc/AGENTCOMPANIES_SPEC_INVENTORY.md`, `doc/TASKS.md`,
`doc/MCP-ACCESS-GOVERNANCE.md`, `doc/CLIPHUB.md`, `docs/plans/`, `docs/pipelines-tutorial.md`,
`docs/built-in-agents.md`, `evals/promptfoo`, and 17 of 20 `.agents/skills/` definitions.

## 9. Test plan — what research cannot settle

Ordered by how much each would change a decision.

1. **Run Paperclip locally with NO `ANTHROPIC_API_KEY` set** and a Claude Code subscription login present;
   wire the `claude_local` adapter and drive one heartbeat. **Settles §4.6** — whether subscription-at-the-
   edge is genuinely the default path or a documented-but-untravelled one. This is the single most decision-
   relevant claim in the paper because it bears on the problem statement's central economic premise. Budget:
   ~1 hour.
2. **Kill an agent process mid-run and watch what happens.** Confirm output-silence detection fires, observe
   the re-arm interval, and check whether exactly one recovery row appears in `issue_recovery_actions`.
   **Settles §4.3 and §4.4** — whether the recovery machinery is real or structural. Budget: ~1 hour after
   item 1.
3. **Verify the long reproduced blocks for COMPLETENESS, not fidelity** — §4.2's three commit sentences and
   §4.3's **five** index definitions across 0084 / 0069 / 0206. Clone or `curl` the raw bytes and **count
   statements against the source file** rather than reading for wording; round 1 established that the
   character sequences are accurate and that a whole statement had gone missing. **Settles §5(b).** Cheapest
   item here; do it first if the critic is budget-constrained.
4. **Prototype §4.1(a) against real repos for two weeks and measure.** Does the *Blocked — needs you* section
   surface anything `/standup` does not? How many rows per day, and how many are false alarms? **Settles
   §5(d)** — whether an attention queue is a real need at one operator or premature federation-shaped
   engineering. **Research cannot answer this; only running it can.**
5. **Read the TypeScript for the wake dispatcher and the review-path invariant.** Specifically: is coalescing
   honoured, is 30 minutes the shipped silence default, and is `testEnvironment` invoked outside the config
   UI. **Settles §5(h).**
6. **Determine whether `testEnvironment` has a Temporal analogue worth adopting at worker registration.**
   Does the Python SDK expose a worker-startup hook that can refuse registration on a failed capability
   probe, or must the check live above the worker? **Settles the cost line on §6 item 6**, which is currently
   the least-anchored estimate in the table.
7. **Fetch the eleven named-but-unfetched documents in §5(g), `doc/SPEC.md` first.** **Settles** whether any
   §5(g)-scoped absence claim is wrong. The prior paper's two blocking defects were both absence claims
   falsified by cited-but-unread sources; this paper's absence claims are scoped rather than global, but the
   same failure shape is available.
8. **Re-sweep in four weeks.** Tripwires: a Paperclip remote-worker/distributed-execution release (its roadmap
   names *"Cloud / Sandbox agents (e2b, Cloudflare, Daytona, Modal, Novita, self-hosted
   Kubernetes)"*[^roadmap-paperclip]), which would make §4.7's coordination reading stale; and any change to
   the `claude_local` credential precedence, which would invalidate §4.6.
