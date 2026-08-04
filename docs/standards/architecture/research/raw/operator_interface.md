# The Operator Interface: Is a Control Surface a Requirement for a Fabric of Unattended Edges, and What Must It Show?

```
Topic:          Is an operator control surface a genuine requirement for a fabric of
                unattended agent edges — and if so, what must it show, in what order,
                and at what build cost?
Feeds:          `docs/development/roadmap.md` — NO PHASE HOLDS THIS TODAY. This is the
                named gap. A positive finding becomes a new roadmap phase; a negative
                finding closes the gap and saves the build. Also touches
                `Phase: Temporal Integration` (what the Temporal Web UI supplies free)
                and `Phase: Autonomous Operation` (observable exit criteria).
Last validated: 2026-08-04
Revalidate:     high — 4 weeks
Confidence:     DEFINITIVE on the shipped feature inventory of ten comparable systems
                (all from first-party raw `.md`/`.mdx`/`.rst`/`.yaml` sources and the
                GitHub contents API, all fetched). DEFINITIVE on the negative findings in
                §5.6, each carrying its search method. VERBATIM (read directly as page
                images, not via a summarizing fetch) only for Bainbridge 1983 [S31].
                DIRECTIONAL on every quoted span from every other source — see the
                quoting-discipline box below — and on the single-author preprint [S32],
                whose central result is explicitly a modelling result its own author says
                "motivate[s] a human study". REDUCED CONFIDENCE on [S30] (Google SRE Book,
                rendered HTML only). DERIVED — and marked as such at each site — for the
                convergence verdict (§3.3), the git-as-control-plane ruling (§3.4), the
                Temporal-covers-most argument (§4.1), the cost estimates (§4, §6), and the
                sequenced minimum (§6). UNVERIFIED and therefore UNUSED: the widely
                repeated "75% of Nextflow users" statistic (§5.6.5).
Critic:         not-yet-verified — 2026-08-04
```

> **Quoting discipline, stated once and binding on every quote below.** Only [S31]
> (Bainbridge 1983) was read as raw page images by this analyst, so only its quoted spans
> are labelled **[verbatim]**. Every other quotation was returned by a fetch layer that
> summarizes; even when the underlying file is raw first-party markdown and the fetch was
> asked for character-for-character exactness, that layer cannot *establish* exactness.
> All such spans are labelled **[quoted-via-fetch]** and should be treated as accurate in
> substance and unproven in punctuation. A critic re-fetching them should expect the
> substance to hold and should not treat a comma as a finding. Quotes from rendered HTML
> ([S30]) carry a further reduction and are kept deliberately short.

> **Mixed volatility (§3 of the Research Standard).** The high-volatility material is
> §§2–3 (shipped product feature inventories for `bernstein`, Paperclip,
> `cli-agent-orchestrator`, Temporal — all four pushed commits on the validation date) and
> §4.1 (the Temporal Web UI surface). The low-volatility material is §5.1–5.3 (the
> human-factors and SRE literature: Bainbridge 1983, the SRE Book, the alert-fatigue
> survey) and may be skipped on refresh. The header takes the highest tier present.

---

## 0. Headline

**A control surface is a requirement. The field is unanimous — ten of ten comparable systems
verified first-party ship one, including the two that most nearly match this repo's shape
and including one built on tmux by AWS Labs. There is no located counter-example of a fleet
deliberately run without one.**

**But the requirement is already ~70% met here, and almost none of the remainder is a
dashboard.** The two findings that matter for the roadmap:

1. **The blocked-work inbox — the single element the field converges on hardest — already
   exists in this repo** as PR-thread `HOLD` verdicts plus GitHub Issues plus `/standup`,
   and it is *better designed* than the shipped alternatives on two axes the literature
   says decide whether an inbox works (a staleness detector, and a filer-calibration
   feedback loop). `/standup` has both; Paperclip's approvals surface documents neither
   (§5.6.2). Git-as-control-plane is **legitimate, not a stopgap** — Atlantis has run that
   exact model in production for years, and its one bespoke UI screen exists for precisely
   the state a VCS cannot represent (§3.4).
2. **The genuine gap is not decisions — it is liveness.** Git has no representation for
   *in flight*. A dispatch that hangs at minute forty produces no PR, no issue, no comment,
   and no artifact of any kind until it dies. That is the one axis where the current answer
   is nothing at all — and it is also **the axis the Temporal port supplies for free**
   (§4.1). Building a run-state view before the port would be building the thing the port
   deletes.

**Therefore the recommended answer is mostly negative, and the negative is the useful part:
do not build a dashboard. Build two small things the substrate will never supply (§6), and
let the Temporal port deliver the rest.** Total recommended pre-port build: **order 3–5
engineer-days**, against a dashboard's order 20–40.

The one thing that would falsify this: if the Temporal port slips past roughly one quarter,
the liveness gap has to be closed some other way, and §6.3 prices that stopgap.

---

## 1. Primer

### 1.1 Two axes, routinely conflated

The literature and the products both blur a distinction that decides this question:

| Axis | The question it answers | Failure if absent |
|---|---|---|
| **Observability** | *What happened, and what is happening?* | You cannot diagnose. You learn about failures from their consequences. |
| **Control** | *What happens next, and can I change it?* | You can watch a run destroy something and be unable to stop it. |

The Google SRE Book's alerting chapter is a control-axis document dressed as an
observability one: its central rule is about what should *interrupt a human*, not about
what should be displayed [S30]. Argo Workflows' `suspend` node is pure control — the
workflow stops and schedules nothing new until `argo resume` is issued [S21]. Temporal's
Web UI is both, and separates them explicitly: its configuration file carries independent
switches for the write actions (`disableWriteActions`, `workflowCancelDisabled`,
`workflowResetDisabled`, `workflowSignalDisabled`, `workflowTerminateDisabled`) distinct
from the read surface [S4].

**Why this matters here.** This repo's existing surfaces sit almost entirely on the
observability axis. `/standup` is explicitly and repeatedly read-only — *"You are a
read-only reporter — take NO actions"* — and its rule section restates the prohibition
against editing even the tracker it just enumerated (`config/commands/standup.md`). The
JSONL run logs are pure history. The one control affordance the system has is the
operator's shell: `Ctrl-C`.

### 1.2 What "unattended" changes

An attended system can put its control surface in the operator's terminal, because the
operator is at the terminal. An unattended fabric cannot, by definition. This is the whole
of the argument for a surface, and it is worth stating precisely rather than as a slogan:

- The operator is **absent at the moment work stops**, so a surface that requires the
  operator to be present in order to reveal that work stopped has a latency equal to the
  gap between operator sessions.
- The operator is **absent from the machine**, so state that lives on the machine that ran
  the dispatch (this repo's JSONL logs live at `<repo>/.claude/logs/` on the machine that
  dispatched — confirmed by reading `scripts/workflows/*.sh`, every one of which sets
  `LOG_DIR="${REPO_ROOT}/.claude/logs"`) is not reachable without knowing which machine to
  go to.
- With **many edges across many MDCs**, "which machine" stops being a question the operator
  can answer from memory.

### 1.3 The classical result that frames the whole question

Bainbridge's *Ironies of Automation* (1983) is the canonical statement of what happens to
an operator of a highly-automated system, and it is directly on point for an unattended
agent fabric. Read from the paper's own pages:

> "It may seem that the operator is expected solely to monitor that the automatics are
> acting correctly, and to call the supervisor if they are not, has a relatively simple
> task which does not raise the above complexities." *(p. 776, §1.1.3)* **[verbatim]**

> "We know from many 'vigilance' studies (Mackworth, 1950) that it is impossible for even
> a highly motivated human being to maintain effective visual attention towards a source of
> information on which very little happens, for more than about half an hour. This means
> that it is humanly impossible to carry out the basic function of monitoring for unlikely
> abnormalities, which therefore has to be done by an automatic alarm system connected to
> sound signals." *(p. 776, §1.1.3)* **[verbatim]** [S31]

> "In any situation where a low probability event must be noticed quickly then the operator
> must be given artificial assistance, if necessary even alarms on alarms." *(p. 776, §2.1)*
> **[verbatim]** [S31]

And immediately after, the counterweight that makes the paper research rather than
advocacy for dashboards:

> "Unfortunately a proliferation of flashing red lights will confuse rather than help."
> *(p. 776, §2.1)* **[verbatim]** [S31]

> "Perhaps the final irony is that it is the most successful automated systems, with rare
> need for manual intervention, which may need the greatest investment in operator
> training." *(p. 777)* **[verbatim]** [S31]

**Derived, from [S31].** Three consequences for this repo, and they set the design
constraints for everything below:

1. **A pull-only surface cannot satisfy the requirement on its own.** Bainbridge's vigilance
   result is that a human cannot be the detector for a rare event over a long window.
   `/standup` is a pull surface: it detects nothing until the operator invokes it. It is a
   *briefing*, not an alarm.
2. **A push surface must be filtered or it degrades to noise.** "Alarms on alarms" and
   "flashing red lights will confuse rather than help" are the same author, one paragraph
   apart. This is the constraint §6.1's design must satisfy.
3. **The rarer intervention becomes, the more context the surface must carry.** Bainbridge's
   final irony says the successful automated system is the one whose operator is least
   prepared to intervene. The implication is not "notify more"; it is that when a
   notification fires, it must arrive with enough context to reconstruct the situation. This
   repo already does that — `review-pr` writes a `next_steps` block and `/standup` is
   instructed to deliver it *"VERBATIM"* rather than re-derive it (`config/commands/standup.md`)
   — and that is a property to preserve, not to invent.

---

## 2. The specific model — what an "operator control surface" can actually be

There are six distinct architectural answers in the field, and they are not variants of one
another. They differ in what they cost, what they can represent, and who can use them.

| # | Model | Concrete instance | What it costs to have | What it cannot do |
|---|---|---|---|---|
| **A** | **Bespoke web application** | Paperclip (React UI) [S14]; `bernstein` web GUI [S7] | A service to build, host, secure, and keep current with the domain | Nothing structurally — but it is the most expensive answer, and both instances are products with paying users amortising it |
| **B** | **Substrate-provided UI** | Temporal Web UI [S1]; Inngest Dev Server [S27]; Restate UI/CLI [S26]; Argo Server [S20]; Airflow webserver [S19] | Zero build if the substrate is already adopted; deployment only | Only shows what the substrate knows. It has no vocabulary for domain concepts the substrate never sees |
| **C** | **Metrics/tracing stack** | `bernstein`'s OTLP export, Grafana dashboards, trace store [S13 dir listing: `docs/observability/`] | A Prometheus/Grafana/OTel deployment; dashboards as config, not code | It is an observability answer, not a control one. You cannot approve a thing from a Grafana panel |
| **D** | **Version control as the control plane** | Atlantis (PR comments + VCS approval) [S23][S24]; this repo today | Zero — the substrate is already deployed, already multi-user, already audited | Cannot represent *in flight*. Git has commits and comments; it has no tick |
| **E** | **Push / ChatOps** | `bernstein` notification drivers — Slack, Telegram, Discord, Email, webhook, PagerDuty, Jira, shell [S12] | Small: one poller and one outbound HTTP call | Carries an event, not a state. You cannot browse a notification stream for "what is true now" |
| **F** | **Terminal UI / CLI** | `bernstein fleet` TUI [S10]; `cli-agent-orchestrator` tmux sessions [S28]; this repo's dispatch CLI | Near-zero | Requires the operator to be at a terminal, on the right machine — the exact assumption "unattended" removes |

**The decision is not "UI or no UI." It is which of A–F, in which combination.** Every
system surveyed in §3 uses at least two of them. `bernstein` uses A, C, E and F
simultaneously. Atlantis uses D plus a single screen of A.

---

## 3. Comparative landscape — what ten systems actually shipped

### 3.1 Durable-execution and workflow substrates

| System | Surface | Run state & history | Blocked / approval view | Failure triage | Fleet / worker view | Intervention affordances | Cost |
|---|---|---|---|---|---|---|---|
| **Temporal** [S1][S4][S5] | Web UI (MIT-licensed, separate repo `temporalio/ui`), bundled with every CLI release and with Cloud | Workflows table filterable by status, ID, type, start/end time and search attributes; History in Timeline / All / Compact / JSON; downloadable event history JSON | **None native** — see §5.6.1 | **Yes, a first-class one:** a pre-defined "Task Failures" Saved View; a workflow is auto-flagged after five consecutive task failures or timeouts | Workers tab shows workers polling the task queue with a count, and errors if none are polling. Namespace switcher. **One `temporalGrpcAddress` per UI instance** [S4] | Cancel, Signal, Update, Reset, Terminate from the UI; each individually disableable by config | None |
| **Airflow** [S19] | Web UI | Dag List, Grid, Graph, Dag Run, Task Instance, Logs, XCom, Events, Rendered Templates | None (no HITL concept in the core UI) | Task instance state + logs; Events tab | **Home Page** with health indicators for MetaDatabase, Scheduler, Triggerer and Dag Processor — *"It is the default landing page in Airflow 3"* [quoted-via-fetch] | Trigger, backfill, clear/retry, mark success/failed, pause Dag | None |
| **Argo Workflows** [S20][S21] | Argo Server — *"The Argo Server is a server that exposes an API and UI for workflows."* [quoted-via-fetch] | Workflow DAG/steps view | **Suspend node** — *"Once suspended, a Workflow will not schedule any new steps until it is resumed."* [quoted-via-fetch]; resumed by `argo resume WORKFLOW` or automatically after a `duration` | Node status | Cluster-scoped via k8s | Suspend / resume / terminate | None |
| **Restate** [S26] | *"Restate includes a UI and CLI to inspect the state of your application across services and invocations."* [quoted-via-fetch] | Invocations + service state | Not documented in README | OTel traces auto-generated | — | — | None |
| **Inngest** [S27] | Dev Server dashboard at `localhost:8288`; *"The UI to manage apps, functions and view function run history"* [quoted-via-fetch] | Function run history | — | — | Apps/functions | — | None |
| **Prefect** [S34] / **Dagster** [S35] | Both ship UIs; **not verified first-party in this sweep** — see §5.6.4 | | | | | | |

### 3.2 Agent-fleet systems — the nearest neighbours

| System | Surface | What it shows |
|---|---|---|
| **`bernstein`** (Apache-2.0, 788★, pushed 2026-08-04) [S7]–[S13] | Web GUI, described as *"Operator dashboard for Bernstein orchestration runs. Replaces the Textual TUI for browser-based supervision."* [quoted-via-fetch] | Seven screens: **Tasks** (`/ui/tasks`, default route — list, filters, status, detail drawer); **Agents** (cards, session details, metrics, live log streaming); **Approvals** (`/ui/approvals` — a queue of tool approvals with risk assessment, diffs, and allow/deny buttons); **Audit** (log with cryptographic chain verification, filters, export); **Costs** (KPIs, hourly spend trend, adapter breakdown, top-10 task costs); **Fleet**; **Settings** |
| — its fleet view [S10] | `bernstein fleet` — *"a supervisory dashboard that aggregates state from multiple Bernstein projects into a single view."* [quoted-via-fetch] | Per project: **Project · State** (INITIALIZING / ONLINE / DEGRADED / OFFLINE / PAUSED) **· Run** (plain-language phase) **· Agents** (live count + roles) **· Approvals** (count pending) **· Last SHA · Cost (7d) · Sparkline · Chain** (audit chain ok/BROKEN). Bulk commands: `bulk-stop`, `bulk-pause`, `bulk-resume`, `bulk-cost-report` |
| — its notification layer [S12] | *"Outbound, fire-and-forget notification drivers - Slack, Telegram, Discord, Email, generic webhook, PagerDuty (via webhook), Jira (via webhook), and shell command."* [quoted-via-fetch] | Six lifecycle events (`pre_task`, `post_task`, `pre_merge`, `post_merge`, `pre_spawn`, `post_spawn`) + a `synthetic` test event; LRU dedup on `event_id` with a configurable 6-hour window; per-sink `events` and `severities` filters; exponential-backoff retry |
| — its blocked-work primitive [S11] | *"A hold is a lightweight, heartbeat-renewed lease: acquire it before a gap in task submission, renew it periodically while you still need it, release it when you're done."* [quoted-via-fetch] | Free-text `reason` (documented example: `"waiting on human approval for phase 2"`); listed via `GET /orchestrator/holds`; cleared by `DELETE /orchestrator/holds/{hold_id}` or by TTL expiry |
| — its mobile story [S9] | *"Install the Bernstein dashboard as a phone home-screen PWA via a Cloudflare / ngrok / bore / Tailscale tunnel with QR onboarding."* [quoted-via-fetch] | The operator surface is explicitly designed to be reachable when the operator is away from the machine |
| **Paperclip** (MIT, 75,610★, default branch `master`, pushed 2026-08-04) [S14]–[S18] | Node.js server + React UI | **Dashboard** — *"The dashboard gives you a real-time overview of your autonomous company's health."* [quoted-via-fetch]: agent status counts (active / idle / running / error); task breakdown by status (todo / in progress / **blocked** / done); **stale tasks** (in progress without recent updates); cost summary vs budget with burn rate; recent activity. **Approvals page** — *"Paperclip includes approval gates that keep the human board operator in control of key decisions."* [quoted-via-fetch]; each approval shows requester, rationale, linked issues; actions approve / reject / *"Request revision — ask the agent to modify and resubmit."* [quoted-via-fetch]. **Overrides:** pause/resume agents, terminate agents, reassign tasks, override budgets. **Execution policy** [S17]: a three-layer gate — comment required (always on), review stage, approval stage — where a completed task transitions to `in_review` rather than `done` |
| **`cli-agent-orchestrator`** (AWS Labs, 989★, pushed 2026-08-04) [S28][S29] | Explicit *"Control-plane selection"*: Web UI, shell CLI, operations MCP server, or plugins; Web UI at `localhost:9889`, described together with MCP Apps as *"browser and host-rendered fleet interfaces"* [quoted-via-fetch] | *"Manage sessions, spawn agents, create scheduled flows, configure agent directories, and interact with live terminals — all from the browser."* [quoted-via-fetch]; live status badges, an **inbox** (for agent-to-agent messaging), output viewer. Also tmux attach for direct session access |

### 3.3 The convergence verdict

**DERIVED, from [S1][S7][S14][S19][S20][S23][S26][S27][S28] and the repo metadata in
[S5][S13][S18][S34][S35].**

**Ten of ten systems verified first-party ship an operator surface** — Temporal, Airflow,
Argo Workflows, Restate, Inngest, `bernstein`, Paperclip, `cli-agent-orchestrator`, Atlantis
and AWX. (Prefect and Dagster are excluded from the count; see §5.6.4.) The sweep found no
counter-example — no comparable system that runs work unattended, deliberately shipped no
operator surface, and documented what that cost. Search method for that negative is stated
in §5.6.3.

Four things are worth more than the headcount:

1. **The convergence is not on "a dashboard." It is on "a control plane," and the word is
   used literally.** AWS Labs' tmux-based orchestrator — the system in this survey with the
   strongest claim to being terminal-native — names its own configuration section
   *"Control-plane selection"* and ships a browser UI anyway [S28]. `bernstein`'s GUI doc
   opens by saying it *"Replaces the Textual TUI"* [S7]. The direction of travel in this
   category is TUI → browser, and it happened inside a few months in an actively-developed
   Apache-2.0 project.
2. **The evolution lesson from the decade-old engines is the same in both directions.**
   Airflow's health-overview Home Page — MetaDatabase / Scheduler / Triggerer / Dag
   Processor health, plus Dag counts by status — is *new in Airflow 3* [S19]. Ten years of
   per-Dag views came first; the fleet-health landing page came after. Temporal's "Task
   Failures" Saved View, with its five-consecutive-failures auto-flag, is the same shape:
   a *pre-computed answer to the question operators kept asking manually* [S1]. Both are
   evidence that **the surface people converge on last is the aggregate one**, and both
   arrived only once the per-run views existed.
3. **The clearest CLI-first → control-plane transition in the survey is Ansible's, and it
   happened for exactly the reason this repo faces.** Ansible's core is a CLI with no daemon
   and no server — the closest structural analogue to this repo's bash fleet. AWX is what
   the ecosystem built on top of it: *"AWX provides a web-based user interface, REST API,
   and task engine built on top of Ansible."* [quoted-via-fetch] [S22]. Note what the
   sentence bundles: the UI arrives together with an API and a task engine, because
   unattended, scheduled, multi-user operation needs all three and the CLI supplies none of
   them. **The lesson is not "you will want a UI"; it is that the UI is the visible part of
   a control plane whose other two thirds are the actual work.** For this repo, the port
   supplies the task engine (Temporal) and the API (Temporal's gRPC/HTTP surface), which is
   a further reason the remaining UI-shaped delta is small.
4. **The approval/blocked-work view is the element that separates agent systems from
   workflow engines.** Airflow's core UI has no approval concept. Temporal's has none
   natively (§5.6.1). Argo has suspend/resume but no queue view. Both agent-fleet products
   built one as a top-level screen — `bernstein` has `/ui/approvals` *and* a pending-approval
   count in its fleet columns [S8][S10]; Paperclip has a dedicated Approvals page *and*
   `blocked` as a first-class task state on the dashboard [S15][S16]. **This is the field
   telling us which view is load-bearing when the work is agentic:** it is the one the
   general-purpose orchestrators did not need and the agent orchestrators built first.

### 3.4 Is git a legitimate control plane, or a stopgap?

**Legitimate — with one precisely-bounded exception, and Atlantis is the evidence for both
halves.**

Atlantis is a self-hosted server that *"listens for Terraform pull request events via
webhooks"* and *"Runs `terraform plan`, `import`, `apply` remotely and comments back on the
pull request with the output."* [quoted-via-fetch] [S23]. Its approval gate is not a bespoke
queue — it is the VCS's own review: *"The `approved` requirement will prevent applies unless
the pull request is approved by at least one person other than the author."*
[quoted-via-fetch] [S24]. Its three requirement types are `approved`, `mergeable` and
`undiverged` — all three are properties of the pull request, computed by the forge [S24].

This is a production system operating real infrastructure changes, whose entire control
plane is PR comments plus VCS review state. **The model works.** It is not a compromise
made by people who could not afford a UI.

And then the exception, which is the more valuable half of the finding. Atlantis *does*
have a web UI — exactly one screen, for locks: *"To view locks, go to the URL that Atlantis
is hosted at"*, with unlock available by commenting `atlantis unlock` on the PR or clicking
through from the lock detail view [quoted-via-fetch] [S25].

**DERIVED, from [S23][S24][S25].** The rule Atlantis follows, stated as a design rule:

> **Build bespoke surface only for state the version-control substrate cannot represent.**

A lock is a mutex held across pull requests. No PR owns it; no comment expresses it; it
exists between PRs and outside of any of them. That is why it needed a screen, and it is
the only thing that did.

**Applied here.** What can git represent, and what can it not?

| State | Git's representation | Adequate? |
|---|---|---|
| Work stopped, needs a human decision | An open PR carrying `verdict: HOLD` + `next_steps`; an open Issue | **Yes.** Durable, auditable, multi-user, no service to run, and the disposition is recorded where reviewers read |
| The outcome and reasoning of a completed run | PR thread, reflection comment, decisions log | **Yes** |
| Continuity across sessions | The `standup-tracker` issue, with `BLOCKED → READY → IN FLIGHT → RESOLVED` states | **Yes**, with the caveat that `IN FLIGHT` there is hand-maintained prose, not observed state |
| **A run that is executing right now** | **Nothing** | **No.** This is our lock. |
| **A run that hung** | **Nothing, ever** — a hung dispatch produces no PR, no issue, no comment | **No** |
| Which machine/edge is alive, behind, or saturated | Nothing | **No** |
| Rate-limit / quota headroom on an edge's subscription | Nothing | **No** |

**The four "No" rows are one thing wearing four hats: git has no tick.** It records
transitions, not duration. That is the boundary of model D, and it is where — and only
where — something else is needed.

---

## 4. What this provides — the enumerated recommendations

Every entry below carries the four properties a planner needs: **what it is**, **why it
matters for the federated destination**, **the evidence**, and **the cost**.

**Cost unit and its inputs, stated once so the numbers can be challenged.** "Engineer-day"
here means one autonomous dispatch cycle plus operator review — the unit this repo actually
bills in. Estimates are **derived** from: (a) the existence of `gh-monitor` as a
systemd-timed GitHub poller already shipped (`roadmap.md`, Phase: Autonomous Execution);
(b) `run-claude.sh` already writing per-run JSONL and already computing monthly cost totals
via `print_cycle_totals`; (c) `/standup` already implementing cross-repo enumeration with
disposition semantics (`config/commands/standup.md`); (d) the Temporal port's stage
boundaries in `roadmap.md` § *Phase: Temporal Integration*. Where an estimate has no such
anchor it is marked *(unanchored)* and should be treated as an order of magnitude only.

### 4.1 What the Temporal port supplies for free — and this is the largest single input

**DERIVED, from [S1][S4][S5][S6][S38] against `roadmap.md` § Phase: Temporal Integration.**

The Temporal Web UI is a separate MIT-licensed repository [S5] that ships with every
Temporal CLI release and with Cloud [S1]. Temporal names Observability among its feature
areas and describes it as *"List business processes, view their state, and set up dashboards
with metrics."* [quoted-via-fetch] [S6] — note that the promise is a *list-and-view* surface
plus metrics hooks, not an approval or intervention queue, which is consistent with the gap
found in §5.6.1.

The planned topology is **one Temporal server on a backed-up VM with workers as bare systemd
processes on every machine holding repos** (`roadmap.md`). The UI takes exactly one
`temporalGrpcAddress` [S4], and the shipped `ui-server` development config contains no
`clusters`/`multiCluster` section — a single service endpoint per UI instance [S38].
Against the planned single-server topology, that means **one UI instance covers the whole
fabric** — every edge's workers poll the same service, and the namespace switcher plus the
Workers tab give a fleet view without a line of code. Against a one-Temporal-per-MDC
topology it would mean one UI per MDC, which is the sensitivity flagged in §7.3.

| Surface element | Supplied by Temporal Web UI? | Detail |
|---|---|---|
| **Run state — what is running now** | **Yes, fully** | Workflows table filterable by status; the running set is a filter, not a feature to build [S1] |
| **Run history — what it did, where it got to** | **Yes, fully** | Event history in Timeline / All / Compact / JSON, downloadable as JSON [S1] |
| **Failure triage** | **Yes, and better than we would have built** | Pre-defined "Task Failures" Saved View; auto-flag at five consecutive task failures or timeouts [S1] |
| **Cross-edge liveness** | **Yes, partially** | Workers tab shows workers polling a task queue with a count and errors when none are polling [S1]. This *is* "which edges are alive," expressed per task queue — and the dedicated-non-fungible-edge design (`problem-statement.md` §*Where we actually differ* #2) makes task queue ≈ edge, so the mapping is clean |
| **Intervention affordances** | **Yes, fully** | Cancel, Signal, Update, Reset, Terminate, all from the UI, each independently disableable [S1][S4] |
| **Scheduled work** | **Yes** | Schedules page listing frequency, start/end times, recent and upcoming runs [S1] |
| **Blocked-work inbox** | **No — constructible, not supplied** | See §5.6.1. A custom Search Attribute plus a query builds it; Saved Views are capped at 20 and *"stored locally in your browser"* [quoted-via-fetch] [S1], so they are per-operator bookmarks, not a shared control plane |
| **Cost / quota** | **No** | Temporal has no concept of it |
| **Push notification** | **No** | Temporal has no outbound notification layer |

**This is the decision-relevant fact in the entire paper.** Five of the seven candidate
surface elements named in the dispatch arrive with a port that is already committed to.
Building any of them now is building something the port deletes.

### 4.2 The two elements the substrate will never supply

**Element 1 — Push notification of blocked work.**

*What it is.* A poller that watches, across the configured repo set, for (a) an open PR
whose latest `pr_review:` block carries `verdict: HOLD` **and whose `next_steps` are not a
redispatch** — i.e. it needs a human, not a re-run — and (b) a newly-opened Issue. On a
match it posts one message to one outbound channel, with the pre-written `next_steps`
attached verbatim. Dedup by item ID over a window.

*Why it matters for the federated destination.* The operator of an unattended fabric is by
construction not watching. Bainbridge's vigilance result says a human cannot be the detector
for a rare event over a long window [S31]; `/standup` is a pull surface and detects nothing
until invoked. As the edge count grows, the time between an edge stopping and an operator
noticing scales with the operator's session cadence, not with the fabric's size — which is
the wrong direction.

*Evidence.* `bernstein` ships exactly this and ships it as a first-class subsystem: eight
outbound drivers, six lifecycle trigger events, LRU dedup on `event_id` with a 6-hour
window, per-sink `events` and `severities` filters, exponential-backoff retry [S12]. Its
GUI is additionally packaged as an installable PWA behind a tunnel so the operator can be
reached off-machine [S9]. Paperclip, by contrast, documents *no* notification and *no*
timeout on its approvals surface (§5.6.2) — a gap this paper records as a finding rather
than a model.

*Cost.* **1–2 engineer-days.** Anchored: `gh-monitor` already exists as a systemd-timed
poller over the repo set and already routes on PR comment content; the `pr_review:` /
`plan_stop:` block parsing is already specified and implemented in `/standup`'s Stage 1.
The delta is a filter predicate and one outbound HTTP call. **No dependency on the Temporal
port.**

*The filter is the design, not a detail.* The SRE Book's rule is the one to apply: *"Every
page response should require intelligence"* and *"If a page merely merits a robotic
response, it shouldn't be a page."* [S30, rendered source, reduced confidence]. This repo's
`HOLD` verdicts already split cleanly into `redispatch` (robotic — the disposition engine
already wrote the command) and `needs-assistance` (requires judgement). **Notify only on
the second.** That predicate is available today, in the data, at no additional design cost —
and it is the difference between a notification channel and a noise channel.

**Element 2 — Rate-limit / quota headroom per edge.**

*What it is.* Not a cost dashboard. A per-edge view of *how much subscription capacity
remains* — which edges are near their limit, which are idle, and whether a dispatch was
throttled rather than failed.

*Why it matters for the federated destination.* **The cost surface every surveyed system
built does not transfer to us, and the reason is architectural.** `bernstein`'s Costs screen
(hourly spend, adapter breakdown, top-10 task costs [S8]) and Paperclip's cost-vs-budget
with burn rate [S15] are both shaped by metered per-token billing. This repo's stated
economic premise is the opposite: *"A long-running loop costs the same as a short one; being
wrong costs nothing but time"* (`problem-statement.md` § *Affordability is the enabler*).
Under a flat subscription, dollars are not the scarce resource — **rate-limit headroom is**,
and it is scarce *per edge*, because each edge authenticates with its own subscription
(`problem-statement.md` § *The edges*). A fabric that saturates one edge's limit while three
sit idle is misallocating the only resource that is actually finite. Note that this repo has
already recorded hitting exactly this: `roadmap.md` § *Local AI Offloading* records
*"2 concurrent engineers + PM session can exhaust rate limits in half a metered period."*

*Evidence.* **This is a gap finding, not a mined design.** No surveyed system exposes a
quota-headroom view; all six that expose cost expose *spend*. Search method: `bernstein`'s
`docs/observability/` and `docs/operations/` directory listings were enumerated via the
GitHub contents API and contain `rate-limits.md`, `cost-envelopes.md`,
`cost-anomaly-detection.md` and `cost-aware-scheduling.md` — the vocabulary is spend and
scheduling, and `rate-limits.md` was not read in this sweep, so **whether `bernstein`'s
`rate-limits.md` is the analogue of this element is UNRESOLVED and is the highest-value
single follow-up fetch in this paper's test plan (§7.2).** Paperclip's board-operator guide
has `costs-and-budgets.md` and no quota equivalent [S18 dir listing].

*Cost.* **2–3 engineer-days** *(partly unanchored)*. Anchored on: `run-claude.sh` already
computes per-run and monthly totals from JSONL. Unanchored on: whether the Claude Code CLI
exposes remaining-quota telemetry at all in its result envelope — **that is an open
question, listed in §7.1.** If it does not, this element degrades to inferred headroom
(dispatches-per-window per edge), which is weaker but still actionable, and cheaper.

### 4.3 The element that already exists and should be recognised rather than rebuilt

**The blocked-work inbox.**

*What it is, today.* Open PR with `verdict: HOLD` + verbatim `next_steps` → open Issue
carrying a `plan_stop:` block or deferred work with a pinned SHA and a proposed action →
the `standup-tracker` issue's `BLOCKED / READY / IN FLIGHT / RESOLVED` sections →
`/standup` aggregating all three across the configured repo set
(`config/commands/standup.md`; `system-overview.md` § *Memory*).

*Why it matters.* It is the element the field converges on hardest for agentic work (§3.3
point 4), and the one the substrate will not supply (§4.1).

*Evidence that the existing implementation is not merely adequate but ahead on two axes the
literature says decide whether an inbox works:*

- **A staleness detector.** `/standup` flags any open issue whose `updatedAt` predates the
  window as *aging*, and the command's own text names the reason: *"That is the exact
  failure mode this convention exists to prevent, and it means one of two things: the item
  is blocked ... or it never qualified in the first place."* This is a **drain-rate
  detector** — the direct observable for the failure mode §5.2 says is the one that kills
  approval queues. Neither `bernstein`'s holds [S11] nor Paperclip's approvals [S16]
  document one; `bernstein` holds expire silently by TTL, which removes the item without
  surfacing that it was never drained.
- **A filer-calibration loop.** `/standup` surfaces issues closed as invalid *"as a
  `review-pr` calibration signal, not as cleanup"* and instructs that a pattern of them
  *"is acted on as a tooling defect."* The oversight literature's named remedy for queue
  overload is precisely **more precise trigger logic** rather than more reviewer capacity
  [S32]. This repo has the feedback loop that produces that precision. No surveyed system
  documents an equivalent.

*What it is missing.* Three things, all small: it is **pull-only** (→ §4.2 Element 1); it
costs a Claude session's tokens per invocation, so its use is rationed by cost in a way a
static page is not; and its `IN FLIGHT` state is hand-maintained prose rather than observed
run state (→ §4.1, supplied by Temporal).

*Cost to "build."* **~0 engineer-days of code. 0.5 engineer-days of planning** — the work is
to give it a home in `roadmap.md` so that a surface the architecture depends on stops being
undocumented and unowned. It is currently described in `system-overview.md` § *Memory* as a
memory model, not as a control surface, and no phase holds it.

### 4.4 What is NOT recommended, and why

| Candidate | Verdict | Reason |
|---|---|---|
| **A bespoke web dashboard** | **No** | Five of seven elements arrive free with a committed port (§4.1); the sixth already exists (§4.3). Both instances of model A in the survey are commercial products amortising the build across users [S14][S18 — 75,610★; S13 — 788★] |
| **A metrics/Grafana stack (model C)** | **Not yet** | It is the right answer for saturation and trend questions, and `bernstein` demonstrates it works [S13 `docs/observability/`]. But it answers observability questions, not control ones, and with one operator and one edge there is no trend to watch. Revisit at edge #3 |
| **A run-state view built now** | **No** | It is the single largest thing the Temporal port supplies free (§4.1). Building it pre-port is building the thing the port deletes. **Unless** the port slips — priced in §6.3 |
| **A cost/spend dashboard** | **No** | Under a flat subscription, spend is not the scarce resource (§4.2 Element 2). The surface every competitor built does not transfer |
| **A TUI (model F)** | **No** | It assumes the operator is at a terminal on the right machine, which is the assumption "unattended" removes. `bernstein` moved *away* from its Textual TUI to a browser GUI [S7] |

---

## 5. Honest boundary analysis — the case against this paper's own conclusion

### 5.1 The case that no surface is warranted at all

The strongest version, stated fairly:

- **One operator, one edge.** Every convergence data point in §3 comes from a system with
  either multiple users (Paperclip, Airflow, Argo, Atlantis, AWX) or multiple projects
  (`bernstein fleet` exists precisely to aggregate *"multiple Bernstein projects"* [S10]).
  This repo has one operator and one edge. **The convergence evidence is evidence about
  systems that have crossed a threshold this repo has not crossed.** That is a real
  weakness in the argument, and it is not resolved by counting ten systems.
- **`/standup` may be enough.** If the operator's session cadence is daily, a pull-only
  inbox has at most a one-day detection latency, and nothing in this repo's work is
  latency-critical. The push notification in §6.1 buys hours, not correctness.
- **`gh pr list` exists.** An operator who can invoke `/standup` can invoke `gh`. The
  surface is a convenience layer over a CLI that already answers the question.

**Where this argument breaks:** at the second edge, not the second operator. The moment a
dispatch runs on a machine the operator is not sitting at, "which machine" becomes a
question, and the JSONL logs — machine-local and repo-local by design — stop being
reachable. `problem-statement.md` states the destination is *"many edges across many
MDCs"*. The honest form of the finding is therefore: **the surface is not needed today and
is needed at edge #2, so the correct time to build the cheap parts is now and the correct
time to build the expensive parts is never, because the port covers them.**

### 5.2 The case against the inbox specifically — and it is the strongest counter-argument in this paper

**An inbox that fills faster than a human drains it is worse than no inbox**, and there is a
2026 result that makes this precise rather than rhetorical.

*Oversight Has a Capacity* [S32] models the reviewer as endogenous — fatiguing as escalation
load grows — and reports [quoted-via-fetch from the arXiv abstract]:

> "when the reviewer is modeled as endogenous (fatiguing as escalation load grows), realized
> safety becomes an inverted-U in the escalation rate: more human oversight can make a
> system less safe, and the safety-optimal guard escalates below full escalation"

and, on the same construction:

> "a load-aware policy also uses to resist a flooding attack that slips a malicious action
> past a fatigued reviewer"

**Confidence: DIRECTIONAL, and deliberately so.** This is a single-author preprint. Its own
abstract says the inverted-U and the flooding attack *"are modeling results that motivate a
human study"*, and it explicitly disclaims novelty of the mechanisms. Its empirical component
is 125 hand-labelled actions with Fleiss' κ = 0.52 across reviewers — which is itself the
paper's other useful finding: **reviewers only moderately agree on what is risky**, so there
is no ground-truth label a filter can be tuned against.

Corroborating, from a different field and a peer-reviewed venue: the SOC alert-fatigue
survey [S33] synthesizes 119 records / 87 core studies from 2015–2026 into a four-stage
screening taxonomy (filtering, triage, correlation, generative augmentation) and reports
*"persistent gaps in operational validation, adversarial robustness, cross-environment
generalization, and evaluation practice"* [quoted-via-fetch]. **Note what that abstract does
NOT contain:** any of the widely-circulated "62% of alerts are ignored" figures. Those
appeared only in a search-engine summary during this sweep and are **not used** (§5.6.5).

And the same result, thirty years earlier and from the operator's side: the SRE Book's *"When
pages occur too frequently, employees second-guess, skim, or even ignore incoming alerts,
sometimes even ignoring a 'real' page that's masked by the noise."* [S30, rendered source,
reduced confidence].

**What this does to §6.1.** It does not kill the recommendation; it constrains its design and
supplies its exit criterion:

- Notify only on `HOLD` verdicts whose next step is **not** an auto-redispatch — the SRE
  robotic-response test, applied to data this repo already produces.
- Keep the `/standup` aging flag as the **drain-rate observable**. If the aging count trends
  up after the notifier ships, escalation is above the operator's capacity and the filter is
  wrong. **That is a falsifiable exit criterion, available at zero extra cost, and it is the
  most important line in §6.**
- Do **not** notify on run completion, run start, or any of the six lifecycle events
  `bernstein` offers [S12]. Those are the flashing red lights.

### 5.3 Bainbridge's irony cuts against a surface too

The final irony — *"it is the most successful automated systems, with rare need for manual
intervention, which may need the greatest investment in operator training"* [verbatim, S31]
— says that a surface which only *alerts* makes things worse: it summons an operator whose
situational awareness has decayed precisely because the system worked. The mitigation is not
more alerting; it is that the handoff must carry context. This repo happens to satisfy that
already (`next_steps` delivered verbatim), but **any new surface that alerts without
carrying the pre-written action is a regression against this evidence**, not a feature.

### 5.4 The Temporal-covers-it argument could be wrong

**Where §4.1 is weakest:**

- The Workers tab shows *pollers on a task queue* [S1]. Whether that is an adequate proxy
  for "this edge is healthy" is **untested** — a worker can poll while the `claude -p`
  process behind it is wedged. This is a real hole in the "fleet view comes free" claim and
  is listed in §7.1.
- `raw/temporal.md` in this pool is **past its revalidation window** (`Last validated:
  2026-07-04`, `high — 4 weeks`) and is therefore consumed as unverified per §5 of the
  Research Standard. This paper does not depend on it — every Temporal claim here is sourced
  directly to first-party docs fetched on 2026-08-04 — but a reader should not treat the two
  papers as jointly verified.
- The port is gated on two other phases (`roadmap.md` § Phase: Temporal Integration:
  *"Gated on the two phases above"*). "Free with the port" is only free when the port lands.
  §6.3 prices the slip.

### 5.5 Where the mined evidence does not transfer

- **Paperclip's org-chart metaphor.** Its approvals are *hire requests* and *CEO strategy
  approval* [S16] — a fictional-company framing. The *screen* transfers; the *semantics* do
  not. This paper cites the surface shape and ignores the metaphor.
- **Both agent products are metered-billing shaped.** Their cost surfaces are their most
  prominent screens and their least transferable (§4.2 Element 2).
- **`bernstein`'s holds are a scheduler primitive, not an inbox.** A hold is *"a lightweight,
  heartbeat-renewed lease"* acquired *"before a gap in task submission"* [S11] — it stops the
  orchestrator from concluding it is idle. It happens to carry a free-text reason whose
  documented example is human approval, but it is not a queue and has no drain semantics.
  Reading it as a blocked-work inbox would be over-reading.
- **Atlantis is not an agent system.** Its producer is `terraform`, which is deterministic
  and whose plan output a human can read. Ours is an LLM that can emit a plausible-looking
  but wrong result — a distinction `roadmap.md` already names under Memory Management. The
  git-as-control-plane conclusion transfers; the assumption that a reviewer can trust what
  the PR says does not.

### 5.6 Gaps and negative findings — each with its search method

**5.6.1 — Temporal documents no way to find workflows awaiting human approval.**
Its Approval design pattern defines the problem as *"you need Workflows that wait for human
approval before proceeding"* and covers `Workflow.await()` and Signal payloads
[quoted-via-fetch] [S3], but **does not address operator discovery** — no search attribute
guidance, no UI mechanism, no way to list all workflows currently blocked on a decision.
*Search method:* raw `.mdx` fetches of `docs/design-patterns/approval.mdx` [S3],
`docs/web-ui.mdx` [S1] (twice, with different targeted prompts),
`docs/encyclopedia/visibility/search-attributes.mdx` [S2],
`docs/references/web-ui-configuration.mdx` [S4], plus the contents-API listing of
`docs/design-patterns/` (46 files) and `docs/encyclopedia/visibility/` (4 files). **The
inbox is constructible** — a custom Keyword Search Attribute plus a List Filter query — but
constructible is not supplied, and Saved Views are *"stored locally in your browser"* with a
cap of 20 [quoted-via-fetch] [S1], which makes them per-operator bookmarks rather than a
shared control plane. Per-namespace custom-attribute limits on SQL visibility stores are 10
Keyword and 3 each of Bool/Datetime/Double/Int/KeywordList/Text [S2] — small, but ample for
one `BlockedOn` attribute.

**5.6.2 — Paperclip's approvals surface documents no notification and no timeout.**
*Search method:* raw fetches of `docs/guides/board-operator/approvals.md` [S16],
`docs/guides/board-operator/dashboard.md` [S15] and `docs/guides/execution-policy.md` [S17]
against `master` (default branch confirmed via the repo API before fetching — it is
`master`, not `main` [S18]), plus contents-API listings of `docs/`, `docs/guides/`,
`docs/guides/board-operator/` (13 files) and `docs/specs/`. An approval sits in the queue
until someone opens the page. **This is a gap in the largest product in the category
(75,610★), and it is the exact failure mode §5.2 predicts.** Recorded as a finding, not
copied as a design.

**5.6.3 — No located system deliberately ran an unattended fleet with no operator surface
and documented the cost.** *Search method:* the ten systems in §3, each checked
first-party; plus a targeted web search for CLI-only / no-dashboard agent orchestrators,
which surfaced `awslabs/cli-agent-orchestrator` as the leading candidate — and whose README,
fetched raw, **disproved the search summary's claim** by documenting a Web UI at
`localhost:9889` under a section named *"Control-plane selection"* [S28]. Atlantis is the
closest thing to a counter-example and it still built one screen [S25]. **The absence of a
documented CLI-only holdout is itself the finding**, and it is why §0 states the requirement
as established rather than open.

**5.6.4 — Prefect and Dagster UIs were not verified first-party.** *Search method:* repo
metadata retrieved via the GitHub API (Prefect: `main`, 23,551★; Dagster: `master`,
15,930★) [S34][S35]; two candidate raw docs paths under `dagster-io/dagster` (`docs/docs/
guides/operate/ui/index.md` and `.../operate/webserver/index.md`) both returned HTTP 404
against the confirmed default branch `master`. Their taglines mention *"observation"* and
*"observability"* respectively, but **this paper makes no claim about their UI contents.**
Both are widely known to ship UIs; that knowledge is not sourced here and is therefore not
used. Excluded from the 10/10 count in §3.3.

**5.6.5 — A widely-repeated statistic did not survive its primary source, and is not used.**
A search-engine summary attributed to Seqera the claim that *75% of Nextflow users view a
graphical monitoring interface as important or very important*. The primary source — the
Seqera blog post "Introducing Nextflow Tower", published 2019-10-08 — was fetched and
**contains no such statistic** [S36]. It is recorded here so a future reader does not
re-import it, and as a live demonstration of the standard's rule that a search-engine
summary is never a source.

**5.6.6 — `bernstein`'s `rate-limits.md` was not read.** It exists in the
`docs/observability/` contents-API listing [S13] and is the one document in the survey that
might be the analogue of §4.2 Element 2. Not fetched due to sweep budget. **This is the
single highest-value follow-up fetch in the paper** (§7.2).

---

## 6. The sequenced minimum

**If a planner builds exactly one thing, build #1. If two, add #2. #3 is conditional and
should not be built unless its trigger fires.**

### 6.1 First — the blocked-work notifier, with a drain-rate exit criterion

*Build:* a filter predicate on the existing `gh-monitor` poller plus one outbound message.
Fires on: an open PR whose latest `pr_review:` block carries `verdict: HOLD` **and** whose
`next_steps` are `needs-assistance` rather than `redispatch`; and on a newly-opened Issue.
Payload: the pre-written `next_steps`, verbatim. Dedup by item ID.

*Buys:* it converts the one surface the field says is irreplaceable from **pull to push**,
which is the only change that makes it work when the operator is by definition absent. It is
the only recommendation here that is strictly impossible for the Temporal port to supply,
because Temporal has no notion of a GitHub PR verdict.

*Cost:* **1–2 engineer-days.** Anchored on `gh-monitor` (shipped) and `/standup`'s existing
block-parsing spec. **No dependency on the Temporal port.**

*Exit criterion, and it is not optional:* track the `/standup` aging-issue count before and
after. **If aging trends up, escalation exceeds the operator's capacity and the filter is
wrong** — the inverted-U from [S32], made observable with a counter this repo already
computes. Ship the counter with the notifier or the notifier is unfalsifiable.

### 6.2 Second — give the inbox a home in the roadmap

*Build:* no code. A roadmap phase (or a named section of an existing one) that says: the
blocked-work inbox is `HOLD` PRs + Issues + the standup tracker, aggregated by `/standup`,
pushed by #1, with the aging flag as its health metric.

*Buys:* it converts an accidental architecture into an owned one. Right now the inbox is
documented in `system-overview.md` as *memory* and nowhere as a *control surface*, and no
phase holds it — which is exactly how the surface most likely to be quietly eroded gets
quietly eroded. **This is the cheapest item in the paper and the one most likely to be
skipped for that reason.**

*Cost:* **~0.5 engineer-days**, planning only.

### 6.3 Third — CONDITIONAL: a liveness heartbeat, only if the Temporal port slips past ~one quarter

*Trigger:* Temporal Integration not in progress by roughly 2026-11.

*Build:* each dispatch writes a small status record (run ID, workflow, repo, machine, PID,
start time, last-heartbeat) to a known path, and `/standup` reads them. A record whose
heartbeat is stale is a hung run.

*Buys:* the only "No" row in §3.4 that is genuinely urgent — a hung dispatch currently
produces **no artifact of any kind**.

*Cost:* **2–3 engineer-days**, and **it is throwaway.** The Temporal Workflows table plus the
Workers tab replaces it entirely [S1]. Build it only if the port genuinely slips; the whole
point of pricing it is so the slip does not force an improvised decision.

### 6.4 Not sequenced — the quota-headroom view

§4.2 Element 2 is real and genuinely ours, but it is **blocked on an unanswered question**
(does the Claude Code result envelope expose remaining quota at all? — §7.1) and on one
unread document (§5.6.6). It is not sequenceable until both are resolved. Naming it here
rather than ranking it is deliberate: **a recommendation with an unresolved input should not
be given a rank it cannot support.**

---

## 7. Test plan — what research cannot settle

### 7.1 Questions requiring an experiment

1. **Does the Claude Code CLI's result envelope expose remaining rate-limit / quota
   headroom?** Decides whether §4.2 Element 2 is a real view or an inferred one. *Test:* run
   a dispatch, inspect the final `stream-json` line for quota fields. One dispatch, minutes.
   **This is the cheapest high-value test in the list.**
2. **Is "a worker is polling the task queue" an adequate liveness proxy for an edge?**
   §4.1 and §5.4 both hinge on it. *Test:* after the port, `SIGSTOP` the `claude -p` child of
   a worker and observe whether the Workers tab still reports the worker as polling. If it
   does, the fleet view is not free after all and a heartbeat is required regardless.
3. **Does the notifier's filter predicate hold at real volume?** *Test:* the §6.1 exit
   criterion — aging-issue count before/after, over four weeks. This is the falsification
   test for the entire §6.1 recommendation and it costs nothing beyond running the counter.
4. **What is the actual detection latency of the pull-only inbox today?** *Test:* for the
   next N `HOLD` PRs, record `HOLD`-comment timestamp vs. first operator action. If the
   median is already under a few hours, §6.1's value drops sharply and the honest answer is
   to defer it. **This test can invalidate recommendation #1 and should be run first.**
5. **Do Temporal Saved Views survive as a shared surface in practice?** They are
   browser-local and capped at 20 [S1]. *Test:* once the port lands, whether a `BlockedOn`
   search attribute + a shared URL is usable as a two-operator inbox, or whether the
   browser-local storage makes it a per-person bookmark in practice.

### 7.2 Research follow-ups (cheap, and one is high value)

- **Fetch `bernstein`'s `docs/observability/rate-limits.md`.** [S13] The single highest-value
  unread document in this sweep; may collapse §4.2 Element 2 from "gap finding" to "mined
  design" (§5.6.6).
- Fetch `bernstein`'s `docs/operations/gate-adjudication.md`, `review-board.md` and
  `abandonments.md` — the approval-semantics and give-up semantics this sweep did not reach.
- Verify Prefect's and Dagster's UI contents first-party (§5.6.4).
- Re-run the CLI-only-holdout search with different terms; the negative in §5.6.3 is
  load-bearing for §0 and rests on one search plus ten first-party checks.

### 7.3 Questions this paper deliberately does not answer

- **Multi-edge identity and credential distribution** — already a named gap in
  `topics.md`. If the notifier or a future surface reaches across MDCs, it inherits that
  question whole.
- **Whether a single Temporal service or one-per-MDC is right.** `roadmap.md` specifies a
  single backed-up VM; that choice is what makes §4.1's one-UI-covers-the-fabric claim hold.
  If it changes, §4.1's fleet-view conclusion changes with it — one `temporalGrpcAddress` per
  UI instance [S4] means N MDCs would mean N UIs.

---

## 8. Citations

**First-party — Temporal**

- **[S1]** Temporal Web UI documentation (raw `.mdx`) — https://raw.githubusercontent.com/temporalio/documentation/main/docs/web-ui.mdx
- **[S2]** Temporal Search Attributes (raw `.mdx`) — https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/visibility/search-attributes.mdx
- **[S3]** Temporal Approval design pattern (raw `.mdx`) — https://raw.githubusercontent.com/temporalio/documentation/main/docs/design-patterns/approval.mdx
- **[S4]** Temporal Web UI configuration reference (raw `.mdx`) — https://raw.githubusercontent.com/temporalio/documentation/main/docs/references/web-ui-configuration.mdx
- **[S5]** `temporalio/ui` repository metadata (GitHub API; `default_branch: main`, MIT, 424★) — https://api.github.com/repos/temporalio/ui
- **[S6]** Temporal development/production features index (raw `.mdx`) — https://raw.githubusercontent.com/temporalio/documentation/main/docs/evaluate/development-production-features/index.mdx
- **[S38]** `temporalio/ui-server` development config (raw YAML) — https://raw.githubusercontent.com/temporalio/ui-server/main/config/development.yaml

**First-party — `bernstein` (Apache-2.0; `default_branch: main` confirmed before fetching)**

- **[S7]** GUI overview — https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/gui/index.md
- **[S8]** GUI screens — https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/gui/screens.md
- **[S9]** GUI mobile / PWA — https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/gui/mobile.md
- **[S10]** Fleet dashboard — https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/fleet.md
- **[S11]** Holds — https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/HOLDS.md
- **[S12]** Notifications — https://raw.githubusercontent.com/sipyourdrink-ltd/bernstein/main/docs/operations/notifications.md
- **[S13]** Repository metadata + `docs/`, `docs/gui/`, `docs/observability/`, `docs/operations/` contents listings (GitHub API; 788★, pushed 2026-08-04) — https://api.github.com/repos/sipyourdrink-ltd/bernstein

**First-party — Paperclip (MIT; `default_branch: master` confirmed before fetching)**

- **[S14]** README — https://raw.githubusercontent.com/paperclipai/paperclip/master/README.md
- **[S15]** Board-operator dashboard guide — https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/guides/board-operator/dashboard.md
- **[S16]** Board-operator approvals guide — https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/guides/board-operator/approvals.md
- **[S17]** Execution policy guide — https://raw.githubusercontent.com/paperclipai/paperclip/master/docs/guides/execution-policy.md
- **[S18]** Repository metadata + `docs/`, `docs/guides/`, `docs/guides/board-operator/`, `docs/specs/` contents listings (GitHub API; 75,610★, pushed 2026-08-04) — https://api.github.com/repos/paperclipai/paperclip

**First-party — workflow engines and control planes**

- **[S19]** Apache Airflow UI documentation (raw `.rst`) — https://raw.githubusercontent.com/apache/airflow/main/airflow-core/docs/ui.rst
- **[S20]** Argo Workflows — Argo Server (raw `.md`) — https://raw.githubusercontent.com/argoproj/argo-workflows/main/docs/argo-server.md
- **[S21]** Argo Workflows — suspending (raw `.md`) — https://raw.githubusercontent.com/argoproj/argo-workflows/main/docs/walk-through/suspending.md
- **[S22]** AWX README (raw `.md`) — https://raw.githubusercontent.com/ansible/awx/devel/README.md
- **[S23]** Atlantis README (raw `.md`) — https://raw.githubusercontent.com/runatlantis/atlantis/main/README.md
- **[S24]** Atlantis command requirements (raw `.md`) — https://raw.githubusercontent.com/runatlantis/atlantis/main/runatlantis.io/docs/command-requirements.md
- **[S25]** Atlantis locking (raw `.md`) — https://raw.githubusercontent.com/runatlantis/atlantis/main/runatlantis.io/docs/locking.md
- **[S26]** Restate README (raw `.md`) — https://raw.githubusercontent.com/restatedev/restate/main/README.md
- **[S27]** Inngest README (raw `.md`) — https://raw.githubusercontent.com/inngest/inngest/main/README.md
- **[S28]** `awslabs/cli-agent-orchestrator` README (raw `.md`) + repo metadata (989★, pushed 2026-08-04, not archived) — https://raw.githubusercontent.com/awslabs/cli-agent-orchestrator/main/README.md
- **[S29]** `awslabs/cli-agent-orchestrator` Web UI doc (raw `.md`) — https://raw.githubusercontent.com/awslabs/cli-agent-orchestrator/main/docs/web-ui.md
- **[S34]** Prefect repository metadata (GitHub API; `main`, 23,551★) — https://api.github.com/repos/PrefectHQ/prefect
- **[S35]** Dagster repository metadata (GitHub API; `master`, 15,930★) — https://api.github.com/repos/dagster-io/dagster

**Literature and practice**

- **[S30]** Google SRE Book, Ch. 6 *Monitoring Distributed Systems* — https://sre.google/sre-book/monitoring-distributed-systems/ *(rendered HTML only; reduced confidence, quoted conservatively)*
- **[S31]** Bainbridge, L. (1983). *Ironies of Automation.* Automatica **19**(6), 775–779. DOI 10.1016/0005-1098(83)90046-8. PDF read directly as page images — https://static1.squarespace.com/static/644321e78cd2dd37613af33e/t/6694873f71612132a84371c7/1721009983702/Ironies+of+Automation_Bainbridge_1983.pdf *(the only [verbatim] source in this paper)*
- **[S32]** Turan, E. (2026-06-08). *Oversight Has a Capacity: Calibrating Agent Guards to a Subjective, Fatiguing Human.* arXiv:2606.08919 — https://arxiv.org/abs/2606.08919 *(single-author preprint; DIRECTIONAL)*
- **[S33]** Ndichu, S., Ban, T., Ozawa, S., Takahashi, T., Inoue, D. (2026-05-08, rev. 2026-05-18). *AI-Driven Security Alert Screening and Alert Fatigue Mitigation in Security Operations Centers: A Survey.* arXiv:2605.08316 — https://arxiv.org/abs/2605.08316
- **[S36]** Seqera, *Introducing Nextflow Tower* (2019-10-08) — https://seqera.io/blog/introducing-nextflow-tower/ *(cited only for the negative finding in §5.6.5)*

**This repo (not external evidence; cited for the current-state description)**

- `config/commands/standup.md` · `scripts/workflows/*.sh` (`LOG_DIR` assignments) ·
  `docs/standards/architecture/problem-statement.md` ·
  `docs/standards/architecture/system-overview.md` · `docs/development/roadmap.md`
