# The Blocked-Work Notification Channel and the Operator Inbox Behind It

```
Topic:          Which channel carries a blocked-work notification for a one-operator,
                multi-machine agent fleet; what delivery semantics that channel actually
                guarantees; how dedupe, grouping and a severity ladder should work when
                there is no rota; and whether the inbox behind the notification is
                git-native or a separate surface.
Feeds:          `docs/development/sprint.md` line 183 — Sprint: Fleet Reliability,
                "A blocked-work notifier — and an inbox the operator reads, in place of a
                dashboard". Destination is the fleet-reliability phase doc, NOT YET WRITTEN;
                this paper is the validating evidence that phase doc will cite. Also
                constrains sprint line 182 (the three-legged liveness predicate), which
                supplies two of this notifier's three detectors.
Last validated: 2026-08-07
Revalidate:     high — 6 weeks
Confidence:     DEFINITIVE on the documented retention, priority and escalation surfaces of
                ntfy, Gotify, Pushover, Alertmanager, FCM and GitHub notifications/issues —
                all from first-party raw `.md`/`.rst` sources or the GitHub contents API,
                except the four rendered-only sources named below. DEFINITIVE on the
                current-state facts about this repo (config.yaml, gh-monitor, notify-done.sh,
                settings.json), each read directly from the file. REDUCED CONFIDENCE on
                [S8] Pushover, [S12] PagerDuty, [S13] Google SRE Book and [S16] Firebase —
                rendered HTML only, quoted conservatively. DERIVED — and marked at each
                site — for the blocked/failed/stalled vocabulary (§1.2), the
                artifact-positive/artifact-negative asymmetry (§1.3), the channel ruling
                (§4.1), the no-guarantee-therefore-idempotent conclusion (§3.3), the
                one-operator severity ladder (§3.5), and the inbox ruling (§4.3).
                NEGATIVE FINDINGS with stated search method in §5.6: no channel surveyed
                publishes an ordering guarantee; APNs offline-storage behaviour could not be
                fetched; Gotify documents no retention; SMS is unanchored and therefore
                excluded from the ranking.
Critic:         not-yet-verified — 2026-08-07
```

> **Quoting discipline, stated once and binding on every quotation below.** No source in
> this paper was read as raw page images. Every quoted span was returned by a fetch layer
> that summarizes; even where the underlying file is raw first-party markdown, that layer
> cannot *establish* character-for-character exactness. All quoted spans are therefore
> labelled **[quoted-via-fetch]** and should be treated as accurate in substance and
> unproven in punctuation. Spans from rendered HTML — [S8] Pushover, [S12] PagerDuty,
> [S13] Google SRE Book, [S16] Firebase, [S23] arXiv abstract page — carry a further
> reduction and are kept deliberately short. A critic re-fetching these should expect the
> substance to hold and should not treat a comma as a finding.

> **Mixed volatility (Research Standard §3).** The high-volatility material is §3.1–§3.2
> (product feature and retention inventories for ntfy, Gotify, Pushover, FCM, GitHub) and
> §4.3's reliance on GitHub's issue-dependency and sub-issue surfaces, which shipped
> recently and are still gaining fields. The low-volatility material is §1.2 (task-state
> vocabulary), §3.4 (the Alertmanager grouping model, unchanged for years), §3.5
> (PagerDuty escalation semantics) and §6 (the SRE alert-fatigue literature) — a refresh
> may skip those. The header takes the highest tier present.

> **Revalidate justification (§5).** Tier is **high** because product feature inventories
> and API surfaces are high-tier by the standard's own table, and this paper is largely
> such an inventory. Interval is set at the band's **maximum, 6 weeks**, not its minimum,
> because the specific high-tier facts here are stable by observation: ntfy's 12-hour
> default cache duration and Pushover's 10,000-message free allowance are long-standing
> published defaults, and Alertmanager's defaults have been stable across major versions.
> The one genuinely moving surface is GitHub's issue-relationship feature set (§4.3), which
> is where a refresh should look first.

---

## 0. Headline

**The upstream negative is given, not re-litigated.** `standards/architecture/research/raw/operator_interface.md`
§0 and §6 ruled: do not build a dashboard; build the blocked-work notifier (1–2 days) and
give the inbox a home (0.5 days). Rolled up as candidate 22 in that pool's `synthesis.md`,
which additionally directs that Hermes' stranded-work severity ladder (`hermes_assessment.md`
§5.2 — threshold, then error at 2×, critical at 6×) be sequenced into this same item. This
paper takes all of that as settled and answers only what upstream left open.

Four findings decide the build:

1. **"Blocked" is artifact-POSITIVE; the other three failure legs are artifact-NEGATIVE, and
   they need different detectors.** Blocked work announces itself by writing a durable git
   artifact (an open PR carrying `verdict: HOLD` with `next_steps` that need a human).
   Stalled, looping and stranded work is *defined by the absence* of an artifact. A notifier
   built on git polling covers exactly one of the four, and shipping it alone will make the
   operator believe silence means health. **The notifier must be sequenced with sprint line
   182 (the three-legged liveness predicate), not before it** (§1.3, §5.2).

2. **No candidate channel publishes a delivery guarantee.** Not one of ntfy, Gotify,
   Pushover, FCM, Matrix or GitHub states an at-least-once or ordering guarantee in the
   documentation fetched. What they publish is *retention*: ntfy 12 hours by default and
   in-memory-only unless a cache file is configured [S3]; Pushover until verified delivered,
   21 days if unverified [S8]; FCM four weeks [S16]; GitHub's notification inbox five months
   [S19]. **The correct response is not to hunt for a channel with a guarantee — it is to make
   the notification disposable.** The durable state is the inbox; the notification is a lossy
   pointer that can be re-derived and re-fired from state. That dissolves the milestone's
   founding failure mode ("an alert dropped while the laptop is closed") without needing any
   channel to be reliable (§3.3).

3. **The channel should be GitHub first, with one self-hosted push channel behind a
   configured URL.** GitHub is the only candidate that is simultaneously the notification
   path, the inbox, and the surface the Research Standard §7 already binds every
   action-driving outcome to — and it now ships a first-class `blocked by` issue relation
   [S22] and sub-issues [S21], both driveable from `gh`. Its weakness is real and named:
   it is a third-party single point of failure for the surface that exists to catch failures
   (§5.1). ntfy is the recommended second leg — Apache-2.0, self-hostable, and the only
   surveyed push option that documents *avoiding* Google's push infrastructure for
   self-hosted servers [S4] (§4.1).

4. **Most alerting machinery does not transfer, and saying which parts do not is the
   finding.** With one operator there is no rota, so PagerDuty-style escalation cannot
   escalate to *anyone* — it can only change channel and priority [S12] (§3.5). Alertmanager's
   `group_by`/`group_wait` batching solves a volume problem this fleet does not have [S10].
   What *does* transfer is `repeat_interval` — and it transfers as the load-bearing mechanism,
   because repeating from state is what makes a dropped notification eventually arrive (§3.4).

**Current-state finding that changes the cost estimate.** Upstream anchored the notifier's
1–2 day estimate on `gh-monitor` "already existing as a systemd-timed poller". It exists but
is **disabled and stale**: `config.yaml` sets `gh-monitor.enabled: false` with the comment
"DECISION POINT: if still unused by ~2026-08-19, delete the service rather than carry dead
code", and `gh-monitor.sh` routes to `revision.sh` / `revision-minor.sh`, which are not among
the nine scripts in `scripts/workflows/`. See §5.3 — this is an Escalation item, not a
component-altitude one.

---

## 1. Primer

### 1.1 Two artifacts, routinely conflated

The milestone names two things and they are not the same thing:

| | The notification | The inbox |
|---|---|---|
| What it is | An **interrupt** — a one-shot push at a human who is not looking | A **durable list** — what is waiting, and what the next action on each item is |
| Lifetime | Seconds. It is consumed or lost | Until drained |
| Failure if absent | The operator learns late | The operator learns, then forgets, then re-derives |
| Failure if bad | Alert fatigue → the operator stops reading (§6) | The queue fills faster than it drains |
| Can it be lossy? | **Yes, and it must be assumed lossy** (§3.3) | No |

This split is the paper's organising idea, and it is what makes the "which channel" question
tractable: **the channel only has to be good enough to point at the inbox**, not good enough
to be the record of what is waiting.

### 1.2 What "blocked" means, precisely — and the vocabulary that already exists

The dispatch asks for the standard vocabulary. Two independent bodies of first-party
documentation supply it, and they agree.

**Task-state vocabulary (workflow engines).** Apache Airflow enumerates task-instance states
and distinguishes, as separate states with separate meanings [S15, all spans quoted-via-fetch]:

- `failed` — *"The task had an error during execution and failed to run"*
- `up_for_retry` — *"The task failed, but has retry attempts left and will be rescheduled"*
- `deferred` — *"The task has been deferred to a trigger"*
- `awaiting_input` — *"Task awaiting human response in Human-in-the-loop workflows"*
- `queued` — *"The task has been assigned to an Executor and is awaiting a worker"*

and, separately from all of these, a *stuck* condition: *"TaskInstances may get stuck in a
running state despite their associated jobs being inactive...Airflow will find these
periodically, clean them up, and mark the TaskInstance as failed or retry it."* [S15].

`awaiting_input` is the concept this milestone is about, and it is worth noting that a
mature, decade-old orchestrator needed a **distinct state name** for it rather than
overloading `deferred`. Waiting on a trigger and waiting on a person are different states
because they have different resolutions: one resolves itself, one does not.

**Routing vocabulary (alerting practice).** The Google SRE Book classifies alerts by where
they are delivered rather than by what caused them: *"Alert: A notification intended to be
read by a human and that is pushed to a system such as a bug or ticket queue, an email alias,
or a pager. Respectively, these alerts are classified as tickets, email alerts, and pages."*
[S13, rendered, quoted-via-fetch]. Its routing rule is a single test: *"Every page response
should require intelligence. If a page merely merits a robotic response, it shouldn't be a
page."* [S13]. Prometheus' own alerting-practices page states the same discipline as a design
goal: *"Keep alerting simple, alert on symptoms, have good consoles to allow pinpointing
causes, and avoid having pages where there is nothing to do."* [S11, quoted-via-fetch].

**DERIVED — the vocabulary applied here.** Inputs: [S15], [S13], [S11], plus
`synthesis.md` candidate 10 (the three-legged liveness taxonomy: *stalled* = no output,
*looping* = identical output, *stranded* = never claimed) and `config/commands/standup.md`'s
existing `verdict: HOLD` classification into `redispatch` vs `needs-assistance`.

| Class | Definition for this fleet | Robotic response available? | Route |
|---|---|---|---|
| **BLOCKED** | The run terminated cleanly and wrote a durable artifact recording a decision it cannot make. Concretely: an open PR whose latest `pr_review:` block is `verdict: HOLD` with `next_steps` of the `needs-assistance` shape, or an open issue filed as a no-change outcome | **No** — by construction, it needs judgement | **Page.** This is the notifier's trigger |
| **FAILED** | The run terminated with a non-zero outcome, or a `HOLD` whose `next_steps` is a `redispatch` with the command already written | **Yes** — the disposition engine already wrote it | **Ticket.** Inbox row, no interrupt |
| **STALLED / LOOPING / STRANDED** | The run did not terminate, produced identical output, or was never claimed. Sprint line 182's taxonomy | Unknown at detection time | **Neither, at first.** Detection event → inbox row → severity ladder promotes it to a page over time (§3.5) |

**The routing implication of the vocabulary is a one-line rule:** *page on the class for which
no robotic response exists, and only that class.* BLOCKED is the only class that satisfies it
at time zero. Everything else earns a page by aging, not by occurring.

### 1.3 The asymmetry that decides the build order

**DERIVED. Inputs: the table above; `operator_interface.md` §3.4 (git has no representation
for *in flight*, and a hung dispatch produces no PR, no issue, no comment); `synthesis.md`
candidate 10.**

BLOCKED is **artifact-positive**: the work stopped *and told git it stopped*. Detecting it is
a query over surfaces that already exist, which is why upstream priced it at 1–2 days.

STALLED, LOOPING and STRANDED are **artifact-negative**: they are defined by the absence of a
record. No amount of polling GitHub will ever find them, because there is nothing there to
find. They require a heartbeat or a dispatch registry — which is sprint line 182's item, and
partly sprint line 181's durable dispatch id.

Two consequences the phase doc must carry:

1. **The notifier has two detector families, not one.** A git poller for the artifact-positive
   class, and a state-file/heartbeat reader for the artifact-negative class. They share a
   channel, a dedupe key scheme and a severity ladder — and nothing else.
2. **Shipping only the git poller is worse than it looks.** It converts "I don't know what's
   happening" into "I have been told nothing, therefore nothing is wrong" — which is false for
   three of the four classes. This is the paper's strongest sequencing finding and is
   restated as an honest boundary in §5.2.

---

## 2. The specific options — the channel candidates

Seven architectural answers, and they are not variants of one another.

| # | Channel | Concrete instance | Who hosts it | What reaches the phone |
|---|---|---|---|---|
| **A** | **The forge itself** | GitHub notification inbox + email + GitHub Mobile [S19] | GitHub | GitHub Mobile via APNs/FCM, and/or email |
| **B** | **Self-hosted push server** | ntfy [S1]–[S4]; Gotify [S5]–[S7] | You | ntfy Android *instant delivery* holds its own connection; Gotify's Android app holds a WebSocket [S6][S7] |
| **C** | **Third-party push service** | Pushover [S8] | Vendor | Vendor app via APNs/FCM |
| **D** | **Email** | SMTP to an existing mailbox | Your provider | Mail client, however it is configured |
| **E** | **Chat** | Slack, Discord, Matrix [S17] | Vendor, or you for Matrix | Client app — and for Matrix the spec is explicit that it terminates at APNs/GCM via a push gateway [S17] |
| **F** | **Desktop notification** | `notify-send` over D-Bus — **already implemented in this repo** at `config/hooks/notify-done.sh`, wired at `Stop` in `config/settings.json` | The local machine | Nothing. It is on-machine only |
| **G** | **A local file the operator reads** | A tracked markdown file | The local machine | Nothing. It is an inbox, not a channel |

**A note on abstraction.** Apprise is a single library that fronts a large set of these:
*"Apprise allows you to send a notification to almost all of the most popular notification
services available to us today such as: Telegram, Discord, Slack, Amazon SNS, Gotify, etc."*
[S14, quoted-via-fetch]. Its own README does not state a total count, and this paper does not
assert one (§5.6.4). The relevant fact for planning is qualitative and it is important: **the
channel choice is cheap to change later** if the notifier emits through a URL-shaped
abstraction. That downgrades the stakes of §4.1's ruling considerably, and the ruling should
be read in that light.

---

## 3. Comparative landscape

### 3.1 The channel comparison, on the six axes the dispatch names

| | **A. GitHub** | **B1. ntfy (self-hosted)** | **B2. Gotify** | **C. Pushover** | **D. Email** | **E. Chat** | **F. Desktop** | **G. Local file** |
|---|---|---|---|---|---|---|---|---|
| **Reachability away from the machine** | **Yes** — inbox, email and GitHub Mobile [S19] | **Yes** — phone app; instant delivery works *"even when your phone is in doze mode"* [S4] | **Yes**, with a caveat: *"With enabled battery optimization, Gotify will be killed and you wont receive any notifications."* [S7] | **Yes** | **Yes** | **Yes** | **No** — requires `notify-send` and `DBUS_SESSION_BUS_ADDRESS`; the repo's own hook comment says it *"Silently skips on headless/VM environments where D-Bus is unavailable"* | **No** |
| **Documented retention when the device is off** | **5 months** — *"Notifications that are not marked as Saved are kept for 5 months."* [S19] | **12h default, in-memory unless configured** — *"By default, ntfy keeps messages in-memory for 12 hours, which means that cached messages do not survive an application restart."* [S3] | **Not documented** — §5.6.2 | **Until verified delivered; 21 days if not** [S8] | Provider-dependent; not anchored here (§5.6.5) | Server-side history, indefinite in practice; not anchored per-vendor here | n/a | n/a |
| **Self-hosted vs third-party** | Third-party | **Self-hosted** (Apache-2.0, 33,220★ [S1]) | **Self-hosted** (15,657★ [S5]) | Third-party | Third-party unless you run a mail server | Third-party (Slack/Discord); self-hostable (Matrix) | Local | Local |
| **Cost** | £0 on the existing plan | £0 + a VM you already run | £0 + a VM | Free tier: *"Each account is permitted to send 10,000 messages per month for free"* [S8]; per-platform licence cost not stated on the API page (§5.6.3) | £0 | £0 | £0 | £0 |
| **Setup burden** | **Zero** — already authenticated on every machine (`gh auth status` is already a precondition in `gh-monitor.sh`) | One container + one topic + a phone app | One container + a phone app | An app registration + a phone app | An SMTP credential (a secret to manage) | A webhook/bot registration | Already done | Trivial |
| **Context it can carry** | **Unbounded** — the issue/PR body, the verbatim `next_steps`, the diff, the thread | Title + body + *"up to three user actions"* via `X-Actions`, plus a click URL via `X-Click` [S2] | Title + body + priority | Title + body + a supplementary URL | Unbounded | Unbounded | One line | Unbounded |

**Two entries deserve elaboration because they are the ones a planner will get wrong.**

**F is already built and is exactly the wrong notifier.** `config/hooks/notify-done.sh` fires
`notify-send "Claude Code" "Task ${STOP_REASON}"` on the `Stop` hook — that is, on *every*
session completion, on the local machine only, silently doing nothing on VMs. It fails the
milestone on all three axes at once: wrong event (completion, not blockage), wrong
reachability (on-machine), and wrong failure mode (silent absence). It is also precisely the
behaviour `operator_interface.md` §5.2 rules out: *do not notify on run completion*. This is
not an argument to delete it — a desktop ping when you are at the desk is harmless — but it
must not be mistaken for partial coverage of this milestone.

**G cannot be either half of this milestone.** A local file is not a channel (zero
reachability) and it is not a multi-machine inbox either, because it lives on one of the
machines. Committing it to git fixes the second problem and converts it into a git-native
inbox — at which point it is a strictly worse version of §4.3's option, since it gains merge
conflicts and loses the notification path.

### 3.2 Where the push actually terminates — the fact that collapses three rows

**Every channel that reaches an iPhone or a stock Android device terminates at Apple's or
Google's push service, with one documented exception.**

- Matrix's own specification is explicit that this is the architecture: *"A push gateway is a
  server that receives HTTP event notifications from homeservers and passes them on to a
  different protocol such as APNS for iOS devices or GCM for Android devices."* [S17,
  quoted-via-fetch]. Self-hosting the homeserver does not self-host the push.
- ntfy is the exception, and it is explicit about it: *"The ntfy Android app uses Firebase only
  for the main host `ntfy.sh`, and only in the Google Play flavor of the app. It won't use
  Firebase for any self-hosted servers, and not at all in the F-Droid flavor."* [S4]. Its
  *instant delivery* mode exists precisely because of what the alternative costs: *"Without
  instant delivery, messages may arrive with a significant delay (sometimes many minutes, or
  even hours later)."* [S4].
- Gotify's Android client holds its own connection too — the app README's battery warning is
  the tell: *"By default Android kills long running apps as they drain the battery. With
  enabled battery optimization, Gotify will be killed and you wont receive any
  notifications."* [S7], and the server README describes the model as *"receive messages via
  WebSocket"* [S6].

**What FCM guarantees when the device is off** (the one leg of this chain that is documented,
rendered source, reduced confidence): *"If the device isn't connected to FCM, the message is
stored until a connection is established. When a connection is established, FCM delivers all
pending messages to the device."* [S16]. Default lifespan when no TTL is set: *"By default,
requests that don't contain this field, last for a maximum period of four weeks."*, with the
maximum *"a duration from 0 to 2,419,200 seconds (28 days)"* [S16]. And the collapse
behaviour, which is the closest thing to a dedupe primitive in the transport layer: *"If the
collapse_key is set, and there's an existing message with the same collapse key and
registration token waiting for delivery, the old message is discarded and then new message
takes its place. However, if the collapse key is not set, both the new and old messages are
stored."* [S16].

**APNs' equivalent behaviour is a gap in this paper** — see §5.6.1 for the search method.

### 3.3 Delivery semantics — and the conclusion that follows from their absence

| Channel | At-most-once / at-least-once, as documented | Retention if device off | Ordering, as documented |
|---|---|---|---|
| GitHub inbox | Not stated | 5 months; Saved kept indefinitely [S19] | Not stated |
| ntfy | Not stated | 12h default; **in-memory and lost on restart** unless `cache-file`/`database-url` set [S3] | Not stated |
| Gotify | Not stated | Not documented (§5.6.2) | Not stated |
| Pushover | Not stated | Until verified delivered; 21 days if unverified [S8] | Not stated |
| FCM (under B-via-Play, C, E) | Not stated | 4 weeks default, 28 days max [S16] | Not stated |
| Matrix | Not stated | Not fetched | Not stated |

**This is a negative finding, and it is the most consequential one in the paper.** *Search
method:* the retention/delivery sections of [S3], [S4], [S6], [S7], [S8], [S16], [S19] and
[S20] were each fetched with a prompt explicitly asking for statements about at-most-once /
at-least-once semantics, offline delivery and ordering. None returned such a statement. The
vocabulary these products publish is **retention**, not **guarantee** — how long a message is
kept, never whether it is certain to arrive or in what order.

Two things are documented that *partially* substitute:

- ntfy exposes **catch-up reads**: *"Subscribers can retrieve cached messaging using the
  `poll=1` parameter, as well as the `since=` parameter"* [S3]. That is a pull recovery path
  over a push channel, bounded by the cache duration.
- ntfy states the *purpose* of caching in exactly these terms: *"Caching messages for a short
  period of time is important to allow phones and other devices with brittle Internet
  connections to be able to retrieve notifications that they may have missed."* [S3]. Note
  the framing — the product's own documentation treats missed notifications as expected.

**DERIVED — the design conclusion. Inputs: the table above; [S3]; [S10]'s `repeat_interval`;
`operator_interface.md` §4.3 (the inbox already exists as HOLD PRs + issues + the standup
tracker).**

The milestone's founding fear — *"an alert dropped while the laptop is closed"* — cannot be
engineered away by channel selection, because no channel on the market sells the guarantee.
It can be engineered away by **making the notification derivable rather than delivered**:

> The inbox is the state. The notification is a stateless, idempotent function of that state,
> re-evaluated on a timer. A notification that is dropped is re-sent on the next evaluation,
> because the condition that produced it is still true.

Under that design, at-most-once transport is sufficient. A dropped ntfy message costs one
repeat interval, not one missed blocker. And this is exactly what Alertmanager's
`repeat_interval` does (§3.4) — Alertmanager is not a message queue and never promised to be
one; it is a state evaluator that re-notifies.

### 3.4 Dedupe and grouping, grounded in Alertmanager

Alertmanager (Apache-2.0, 8,571★ [S9]) documents four mechanisms, and it is worth separating
them because they solve four different problems [S10, all quoted-via-fetch]:

| Mechanism | What the docs say | Default |
|---|---|---|
| `group_by` | *"The labels by which incoming alerts are grouped together. For example, multiple alerts coming in for cluster=A and alertname=LatencyHigh would be batched into a single group."* | — |
| `group_wait` | *"How long to wait before sending the first notification for a new group of alerts. Allows to wait for alerts to arrive from other rule groups or Prometheus servers, and for one or more inhibiting alerts to arrive and mute any target alerts before the first notification."* | `30s` |
| `group_interval` | *"How long to wait before sending subsequent notifications for an existing group of alerts after group_wait."* | `5m` |
| `repeat_interval` | *"How long to wait before repeating the last notification. Notifications are not repeated if any new alerts have fired or any firing alerts have resolved since the last group_interval."* | `4h` |
| `inhibit_rule` | *"An inhibition rule mutes an alert (target) matching a set of matchers when an alert (source) exists that matches another set of matchers. Both target and source alerts must have the same label values for the label names in the `equal` list."* | — |

And the routing model itself: *"A route block defines a node in a routing tree and its
children. Its optional configuration parameters are inherited from its parent node if not
set."* [S10].

**PagerDuty supplies the time-based escalation half** [S12, rendered, reduced confidence,
quoted-via-fetch]: *"Escalation policies are made up of rules that allow you to escalate
incidents if responders in the first rule do not respond within the escalation timeout."*;
*"The escalation timeout is the amount of time in which a user must acknowledge or resolve an
incident before it escalates to the next rule."*; *"If no one takes action before the timeout
elapses, the incident escalates to the next rule, and PagerDuty notifies the target(s)
there."* (The default timeout value and the maximum repeat count were described by the fetch
in its own words rather than quoted, and are therefore **not asserted here** — §5.6.6.)

**Pushover supplies a consumer-grade equivalent of the same loop**, and it is the only
first-party acknowledgement primitive found in this sweep [S8, rendered, quoted-via-fetch]:
*"Emergency-priority notifications are similar to high-priority notifications, but they are
repeated until the notification is acknowledged by the user."*, with `retry` that *"must have
a value of at least 30 seconds between retries"* and `expire` that *"must have a maximum value
of at most 10800 seconds (3 hours)"*. Note also that *"The `ttl` parameter is ignored for
messages with a `priority` value of 2"* [S8].

### 3.5 What transfers to ONE operator — and what does not

**DERIVED. Inputs: [S10], [S12], [S8], [S2] (ntfy priority levels 1–5: min/low/default/high/max),
`hermes_assessment.md` §5.2 (threshold → error at 2× → critical at 6×), and `gh-monitor.sh`'s
existing emoji-reaction dedupe.**

| Mechanism | Transfers? | Why |
|---|---|---|
| **Dedupe key** | **Yes — and it is free** | The natural key already exists: `repo + issue-or-PR number + the id of the comment carrying the verdict`. It is globally unique, stable, and *observable by anyone*. `gh-monitor.sh` already implements dedupe of exactly this shape — it writes an `eyes`/`hooray`/`-1`/`confused` reaction onto the comment and skips anything already reacted to. **State-on-the-surface dedupe beats a local LRU here**, because it survives the machine that fired it and it is visible to the operator |
| **`repeat_interval`** | **Yes — and it is the load-bearing one** | It is the mechanism that makes §3.3's conclusion work. Without it there is no recovery from a dropped notification. Alertmanager's `4h` default is a reasonable starting value for a fleet whose runs are 10–60 minutes |
| **`group_by` / `group_wait`** | **No, not in v1** | Their stated purpose is batching alerts arriving *"from other rule groups or Prometheus servers"* [S10] — a volume problem. This fleet's blocked-work rate is on the order of a handful per week (measurable before building — §7.1 item 1). Grouping a set of size one is machinery with no payload |
| **`inhibit_rule`** | **Not in v1, but note the one real case** | The genuine analogue: if an entire machine is unreachable, suppress the per-run *stranded* alerts it would generate. That requires a machine-level liveness signal that does not exist yet (sprint line 182). Record as a design note for when it does |
| **Escalation to the next responder** | **No — and this is the sharpest non-transfer** | PagerDuty's entire model is *"escalates to the next rule, and PagerDuty notifies the target(s) there"* [S12]. With one operator there is no next target. **Escalation here can only change channel and priority, never recipient.** Any design that copies a rota-shaped escalation policy is copying an empty structure |
| **Acknowledgement** | **Partially — and git already has it** | Pushover's ack loop [S8] is genuinely useful, but the acknowledgement this fleet needs is not "I saw it", it is "I acted on it" — which is a comment, a label change, or a merge. Those are already the natural acks on a git surface, and they are durable in a way a push-service ack is not |
| **Severity ladder** | **Yes — as time-in-state, which is what Hermes' is** | See below |

**The minimum viable ladder, stated concretely.** Hermes' shape — threshold, error at 2×,
critical at 6× (`hermes_assessment.md` §5.2) — transfers directly, because it is a
*time-in-state* ladder rather than an intrinsic-severity one, and time-in-state is the only
severity axis a single operator has. Mapped onto the channel primitives:

| Rung | Trigger | Action | Primitive it maps to |
|---|---|---|---|
| **info** | Item enters the blocked set | Inbox row only. No interrupt | A label / an issue in the tracker |
| **warn** | Still blocked at 1× threshold | One push, default priority | ntfy priority `3` [S2] |
| **error** | Still blocked at 2× | Push repeats at `repeat_interval`, raised priority | ntfy `4` / Alertmanager `repeat_interval` [S2][S10] |
| **critical** | Still blocked at 6× | Highest priority; second channel added | ntfy `5` (`max`/`urgent`) [S2], or Pushover priority 2's ack loop [S8] |

Note what the ladder does NOT do: it never changes recipient, and it never adds a person. Both
of those are the parts of the industry model that do not exist here.

**Threshold choice is a measurement, not a guess**, and the measurement is cheap — §7.1 item 2.

---

## 4. What this provides — the enumerated properties a plan can rely on

### 4.1 The channel ruling

**DERIVED. Inputs: §3.1, §3.2, §3.3; Research Standard §7's git-surface principle; the
repo-state facts in §0.**

**Primary: GitHub.** Five enumerated properties a plan can cite:

1. **It is already the mandated surface.** Research Standard §7 binds: *"every workflow outcome
   that must drive future action lands on a git surface — a PR comment when a PR exists, an
   issue when nothing changed"*. A blocked-work item is by definition an outcome that must
   drive future action. Choosing a non-git channel as the *record* would contradict a binding
   standard; choosing one as the *interrupt* would not.
2. **Zero setup and zero new secret.** Every machine already authenticates; `gh-monitor.sh`
   already fails fast on `gh auth status`. No SMTP credential, no push token, no new item in
   the secrets story.
3. **It is a notification path in its own right.** *"You can choose to view your notifications
   through the notifications inbox at https://github.com/notifications and in the GitHub Mobile
   app, through your email, or some combination of these options."* [S19] — and being
   `@mention`ed or assigned triggers one [S19].
4. **Longest documented retention of any candidate.** *"Notifications that are not marked as
   Saved are kept for 5 months. Notifications marked as Saved are kept indefinitely."* [S19].
5. **Filterable.** The inbox supports `repo:`, `is:`, `reason:`, `author:` and `org:`
   qualifiers [S20] — enough to build a saved view that isolates blocked-work items from CI
   noise.

**Secondary: one self-hosted push channel, and ntfy is the recommendation.** Three properties:

1. **It is the only surveyed channel that documents avoiding Google's push path** for
   self-hosted servers [S4], which matters for a fleet whose whole thesis is self-hosted
   edges — and materially, because the alternative is the delay ntfy itself describes as
   *"sometimes many minutes, or even hours later"* [S4].
2. **It carries actionable context.** Up to three action buttons via `X-Actions` and a click
   URL via `X-Click` [S2] — enough to make the notification a one-tap jump to the PR rather
   than a prompt to go find it.
3. **It has a catch-up read** (`poll=1`, `since=`) [S3], which is the pull half of §3.3's
   design and which Gotify does not document.

**The ntfy caveat that must be configured, not assumed:** the default cache is in-memory and
*"cached messages do not survive an application restart"* [S3]. A self-hosted ntfy for this
purpose must set `cache-file` or `database-url`. Recording this because it is exactly the kind
of default that turns a "reliable" channel into a silently lossy one.

**Not recommended, with reasons:**

| Channel | Verdict | Reason |
|---|---|---|
| Pushover | **No, but it is the fallback** | Best documented escalation semantics in the sweep [S8] and a real free tier — but it is a third-party dependency bought to solve a problem (repeat-until-ack) that `repeat_interval` over a self-hosted channel solves for free (§3.3) |
| Gotify | **No** | Functionally similar to ntfy but documents no retention (§5.6.2) and no catch-up read; its Android client's stated failure mode is silent death under battery optimisation [S7] |
| Email | **No** | It is not *worse* — its retention is likely the best of all — but it is the one channel this paper could not anchor first-party (§5.6.5), and it adds an SMTP credential to a repo whose stated posture is `${env:VAR}` references and no hardcoded secrets |
| Slack / Discord | **No** | Third-party hosting for a single-user channel, and mobile delivery still terminates at APNs/FCM [S17, for the Matrix case; asserted for Slack/Discord only as the general pattern, not as a first-party claim] |
| Matrix | **No** | Self-hostable, but the spec makes clear you self-host the homeserver and still depend on a push gateway relaying to APNs/GCM [S17]. Maximum setup burden for no gain over ntfy |
| SMS | **Excluded, not rejected** | Not anchored first-party in this sweep (§5.6.7). It should not be ranked on unsourced reasoning |
| Desktop (`notify-send`) | **Keep, do not count** | Already built; fails all three milestone axes (§3.1) |

### 4.2 What the notifier must emit — four enumerated requirements

1. **The pre-written next action, verbatim.** `/standup` already carries this rule for the same
   payload (*attach `next_steps` VERBATIM — "the disposition engine already wrote the action —
   you deliver it, you do not re-derive it"*, `config/commands/standup.md`). The SRE
   requirement is the same one from the other direction: a page must merit intelligence
   [S13], and a page that arrives without the context to exercise it produces a second lookup
   rather than an action.
2. **A deep link.** ntfy's `X-Click` [S2]; GitHub's notification is already one.
3. **A stable dedupe key**, emitted as a field, not derived by the reader (§3.5).
4. **A severity rung**, mapped to the channel's priority scale (§3.5).

### 4.3 The inbox ruling

**DERIVED. Inputs: [S19]–[S22]; Research Standard §7; `documentation_standard.md`'s
standup-tracker definition; `operator_interface.md` §4.3; `config/commands/standup.md`.**

**The inbox is the set of open GitHub issues and PRs carrying a blocked marker — plus the
existing `standup-tracker` issue as its frame. It is not a new artifact.**

Four properties that make this more than a default-by-inertia choice:

1. **GitHub now ships the exact relation this milestone is about.** *"Issue dependencies let you
   define issues that are blocked by, or blocking, other work."* [S22, quoted-via-fetch], with
   `blocked by` meaning *"your issue depends on another issue being completed"*. It is
   driveable from the CLI — `gh issue edit ISSUE-NUMBER --add-blocked-by ...` [S22] — which
   means an autonomous dispatch can set it without a browser.
2. **It ships the checklist shape too, as a first-class object.** Sub-issues *"break down larger
   pieces of work into tasks"*, can be created with `gh issue create --title "TITLE" --parent
   PARENT-ISSUE-NUMBER`, and support *"up to eight levels of nested sub-issues"* [S21]. (The
   per-parent count limit is present in the raw source only as an unexpanded template variable
   and is therefore **not stated here** — §5.6.8.)
3. **The aggregation layer already exists and already has a drain-rate detector.** `/standup`
   enumerates the repo set, reads each open PR's latest `pr_review:` block, classifies `HOLD`
   as a blocker, and flags aging issues explicitly. `operator_interface.md` §4.3 argues this is
   ahead of the shipped alternatives on precisely this axis; nothing in this sweep contradicts
   that.
4. **Standard-conformance is free.** §7's table already routes a homeless outcome to *"A GitHub
   issue labeled `research-candidate`"*. A `blocked` label is the same primitive with a
   different word in it — no new convention to ratify.

**The case against a git-native inbox, stated at full strength.** Five items, and the first is
serious enough that the phase doc must answer it:

1. **The inbox and its detector share a single point of failure — and it is the failure the
   sprint is about.** If GitHub is unreachable or the token has expired, the inbox is gone
   *and* the git poller reports nothing, which is indistinguishable from "nothing is blocked."
   Credential expiry is literally one of the three cheap guards in the same sprint (line 180).
   **A git-native inbox cannot detect its own detector's failure.** The mitigation is an
   inverse alert — a periodic "the notifier is alive and found N items" heartbeat, where
   *silence* is the alarm — and this paper found no first-party documentation of that pattern
   in the sources fetched (§5.6.9), so it is offered as derived design, not as a cited one.
2. **API-call budget.** `gh-monitor.sh` already backs off when the core rate limit drops below
   50 remaining. A per-tick sweep of open PRs plus their comments across the repo set is
   several calls per repo; at a 5-minute tick (`gh-monitor.timer`: `OnUnitActiveSec=5min`) that
   is a real budget, and it competes with the workflows themselves.
3. **Dilution.** GitHub's notification inbox already carries every subscribed thread. A blocked
   item competes with CI and review noise. `reason:` and `repo:` filters exist [S20] but are a
   thing the operator must set up and maintain — a filter nobody maintains is the dashboard
   nobody opens, one layer down.
4. **Issues are not a queue.** No lease, no claim, no ordering, no drain metric beyond
   `/standup`'s aging flag. The upstream paper treats the aging flag as sufficient; that is a
   defensible position but it is a *proxy* for drain rate, not a measurement of it.
5. **Latency floor.** Any polled git surface has a detection latency equal to the poll
   interval. At the existing 5-minute timer that is fine; it is worth stating so nobody
   later mistakes the notifier for event-driven. (Webhooks would remove this, at the cost of
   a publicly reachable endpoint — out of scope here, noted in §7.2.)

**What would change the ruling:** a second operator. Every weakness above is a
single-operator-tolerable one; item 4 in particular becomes a real defect the moment two
people can pick up the same blocked item.

---

## 5. Honest boundary analysis

### 5.1 The strongest case against this paper's channel ruling

**The ruling makes GitHub load-bearing for three roles simultaneously** — the record, the
detector's data source, and a notification path — in a milestone whose stated purpose is to
notice when things break. That is a genuine concentration of risk, and the honest form of the
counter-argument is: *a reliability feature should not depend on the least controllable
component in the system.*

The counter-counter is that the alternative is worse, not better: routing the record off
GitHub contradicts a binding standard (§7) and splits the operator's attention across two
surfaces, which is the alert-fatigue failure in structural form. The defensible middle is the
one §4.1 recommends — GitHub for the record, a self-hosted channel for the interrupt, so that
the *interrupt* path does not share GitHub's fate even though the *record* does.

But note what that does and does not buy: if GitHub is down, the self-hosted channel is still
up and still has nothing to say, because the detector's input is gone. **Channel diversity does
not buy detector diversity.** Only the inverse-alert heartbeat does.

### 5.2 The strongest case against building the notifier now

**Three of the four failure classes have no detector yet** (§1.3). A notifier shipped against
only the artifact-positive class will be correct about everything it reports and silent about
the majority of ways the fleet actually fails — and *silence from a notifier reads as health*.
That is a net loss in operator model accuracy, not a gain, and it is the specific mechanism by
which a well-built feature makes a system less observable.

**The remedy is sequencing, not cancellation:** sprint line 182 (the three-legged liveness
predicate) supplies the missing detectors, and candidate 22 already directs that Hermes'
stranded ladder be sequenced into this item. The phase doc should treat 182 and 183 as one
design with two build steps, and if only one ships, the notifier's scope statement must say
in words what it does *not* watch.

### 5.3 The cost anchor upstream used has decayed — ESCALATION

*This subsection is above COMPONENT altitude. It is recorded, not acted on.*

`operator_interface.md` §6.1 priced the notifier at 1–2 engineer-days "anchored on `gh-monitor`
(shipped)". Two facts, each read directly from the repo on 2026-08-07:

- **It is disabled.** `config.yaml` sets `gh-monitor.enabled: false` with the comment: *"DISABLED
  2026-07-29 — @claude PR-comment dispatch is not in use... DECISION POINT: if still unused by
  ~2026-08-19, delete the service rather than carry dead code."*
- **It is stale.** `gh-monitor.sh` routes to `revision.sh`, `revision-minor.sh`,
  `plan-revision.sh` and `build-phase.sh`. Enumerating `scripts/workflows/*.sh` returns nine
  files — `build-minor.sh`, `build-phase.sh`, `build.sh`, `plan-new.sh`, `plan-revision.sh`,
  `research-refresh.sh`, `research.sh`, `review-runs.sh`, `review-sprint.sh` — which I counted
  from that listing. `revision.sh` and `revision-minor.sh` are not among them. Separately, the
  route-enable keys in `config.yaml` (`enable-build`, `enable-build-minor`) are not the keys
  the script reads (`enable-revision`, `enable-revision-minor`), so those config keys are inert.

**Consequence:** the 1–2 day estimate assumes a working poller to hang a predicate on. If
gh-monitor is deleted on the 2026-08-19 decision point, the notifier inherits building the
poller loop, the lock file, the rate-limit backoff and the repo discovery from scratch —
material the current script already contains and which is worth *harvesting* even if the
`@claude` routes are dropped.

**Remedy (for the operator, not for this paper to act on):** rule on the gh-monitor decision
point *before* the fleet-reliability phase doc is written, and if the ruling is "delete",
extract the poller skeleton into the notifier rather than losing it. This is a sprint-item
sequencing implication, which per §7 is surfaced for the operator and written by nobody else.

### 5.4 Where the mined evidence does not transfer

- **Alertmanager is a state evaluator over a metrics pipeline that does not exist here.** Its
  grouping model is cited for its *semantics*, not as an adoption recommendation. Running
  Prometheus + Alertmanager to notify one person about a handful of weekly events would be the
  dashboard mistake in a different costume.
- **PagerDuty's model is built around a rota.** Cited for the escalation-timeout *concept*; the
  product is not a candidate (§3.5).
- **Airflow's `awaiting_input` is a state in a scheduler that owns the task.** This fleet's
  blocked state is recorded in a PR comment by a separate review pass. The *vocabulary*
  transfers; the enforcement does not — nothing here can refuse to proceed the way a scheduler
  can.
- **The SOC alert-fatigue survey [S23] is about machine-generated security alerts at industrial
  volume.** Its taxonomy is cited for the phenomenon, not for its methods; four-stage AI
  screening is not a proportionate response to five notifications a week.

### 5.5 When a notifier is the wrong answer entirely

1. **If detection latency is already low.** `operator_interface.md` §7.1 item 4 already frames
   this test and says it can invalidate the recommendation. If the operator's median time from
   `HOLD` comment to first action is already a couple of hours, the notifier buys hours and
   costs a permanent maintenance surface. **This test should be run before the build, not
   after.**
2. **If the blocked-work rate is near zero.** A notifier that fires once a month will be
   forgotten, its channel muted, and its correctness never observed. Below some rate, the
   right answer is `/standup` and nothing else.
3. **If the failure is wrongness rather than stoppage.** A run that reports success it did not
   achieve (sprint line 180's false-completion guard) produces no blocked item and no absence.
   The notifier is structurally blind to it.
4. **If the operator is genuinely unavailable.** With no rota, a notification during a
   two-week absence changes nothing except the size of the backlog on return. The escalation
   ladder has nowhere to escalate to (§3.5), so its top rung is decorative in that scenario.

### 5.6 Gaps and negative findings — each with its search method

**5.6.1 — APNs' offline-storage behaviour is not established by this paper.** Apple's
*Sending notification requests to APNs* page was fetched; the fetch returned only the page
title and no body, which is the documented failure mode of JS-rendered documentation. *Search
method:* one direct fetch of `developer.apple.com/documentation/usernotifications/sending-notification-requests-to-apns`;
no raw/plain-text equivalent of Apple's documentation is known to exist. **Consequence:** the
iOS half of §3.2's chain is asserted only as far as Matrix's spec states it [S17]; the
"how many notifications APNs stores and for how long" question is open and would matter if
iOS becomes the primary target device.

**5.6.2 — Gotify documents no message retention and no catch-up read.** *Search method:* raw
fetches of `gotify/server` README (default branch confirmed `master` via the repo API before
fetching — it is **not** `main` [S5]) and `gotify/android` README, both with prompts explicitly
asking for persistence/storage/retention and for missed-message behaviour. The server README
returned no retention statement; the Android README returned no reconnection or
missed-message statement. Gotify's separate documentation site was not swept. **This is
"not found in the two first-party READMEs", not "does not exist"** — but it is enough to
prefer ntfy, which states its retention explicitly.

**5.6.3 — Pushover's paid licence cost is not stated on its API page.** *Search method:* one
fetch of `pushover.net/api` with an explicit prompt for costs and limits; it returned the free
monthly allowance (*"Each account is permitted to send 10,000 messages per month for free"*
[S8]) and nothing about per-platform purchase price. The pricing page was not fetched. The
cost row in §3.1 is therefore incomplete for Pushover and is marked as such.

**5.6.4 — Apprise's supported-service total is not asserted.** *Search method:* raw fetch of
the `caronc/apprise` README with an explicit request to enumerate. The fetch reported that the
README *"does not provide a single enumerated total"* and returned a category-level listing.
Per Research Standard §3, a count reached through a summarizing layer over a partial
enumeration is not citable, so **no number is given** — only the qualitative point that the
set is large and the abstraction is real.

**5.6.5 — Email's delivery semantics are not anchored first-party here.** *Search method:* two
attempts at RFC 5321 §4.5.4.1 ("Sending Strategy") — `rfc-editor.org/rfc/rfc5321.txt` and
`datatracker.ietf.org/doc/html/rfc5321#section-4.5.4.1` — both of which returned content
truncated before that section. **No SMTP retry, give-up-time or store-and-forward claim is
made in this paper.** Email is therefore ranked on its non-semantic properties only
(reachability, setup burden, the added secret).

**5.6.6 — PagerDuty's default escalation timeout and maximum repeat count are not asserted.**
*Search method:* one fetch of `support.pagerduty.com/main/docs/escalation-policies`. The
values (a 30-minute default; repeat up to nine times) appeared in the fetch's own prose rather
than in a quoted span, and a rendered-page fetch that paraphrases cannot establish them. The
*concepts* are quoted and used; the *numbers* are not.

**5.6.7 — SMS was not researched first-party and is excluded from the ranking.** *Search
method:* none — no SMS gateway documentation was fetched in this sweep. Stating this rather
than reasoning about SMS from priors, because an unanchored channel ranked alongside anchored
ones would give the ranking false uniformity. If SMS matters (it is the only channel that
works with no data connection), it is a one-fetch follow-up (§7.2).

**5.6.8 — GitHub's per-parent sub-issue limit is not obtainable from the raw source.** The raw
markdown contains the limit only as an unexpanded template variable:
`"You can add up to {% data variables.projects.sub-issue_limit %} sub-issues per parent issue"`
[S21]. The nesting depth *is* stated in prose (*"create up to eight levels of nested
sub-issues"*) and is used. *Search method:* raw fetch of the file after enumerating
`content/issues/tracking-your-work-with-issues/using-issues/` via the contents API (15 entries,
listed and counted by this analyst). Resolving the variable requires the rendered docs site or
the repo's data files, neither of which was fetched.

**5.6.9 — No first-party documentation of the dead-man's-switch / inverse-alert pattern was
located.** *Search method:* the Alertmanager `configuration.md` fetch was prompted for the
grouping, inhibition and repeat model and returned no watchdog or heartbeat construct; the
Prometheus alerting-practices page fetch returned none either. The pattern is widely used in
practice; that practice is not sourced here, so §4.3's mitigation is offered as **derived
design with no citation**, and a planner should treat it as an unvalidated idea rather than an
industry-standard one.

**5.6.10 — GitHub's notification *delivery* semantics are undocumented in the pages fetched.**
Retention is stated precisely [S19]; whether a notification can be lost, duplicated or
reordered is not addressed. *Search method:* raw fetches of
`subscriptions-and-notifications/concepts/about-notifications.md` and
`reference/inbox-filters.md`, both explicitly prompted for delivery and retention statements,
after enumerating `content/subscriptions-and-notifications/` (6 entries), its `concepts/`
(3 entries) and its `reference/` (4 entries) via the contents API — each listed and counted by
this analyst. This is the same gap as every other channel (§3.3) and is why the paper's design
conclusion does not depend on any channel's semantics.

**5.6.11 — There is no notification configuration in this repo today beyond one desktop
hook.** *Search method:* full read of `config.yaml` (115 lines; sections `gh-monitor` and
`models` only — no notification section); enumeration of `scripts/services/` (three files:
`gh-monitor.service`, `gh-monitor.sh`, `gh-monitor.timer`); and a repo-wide case-insensitive
grep for `ntfy|pushover|gotify|matrix.org|apprise|smtp|sendmail|notify-send|osascript`, which
matched three files: `docs/file_structure.txt`,
`docs/development/safety-and-guardrails/safety-and-guardrails.md`, and
`config/hooks/notify-done.sh`. **The finding is: one channel exists, it is `notify-send` on the
`Stop` hook, and it is the wrong event on the wrong reachability axis (§3.1).**

---

## 6. Alert fatigue — the failure that kills notifiers

The sprint's framing is *"in place of a dashboard nobody opens"*. The symmetric failure is a
notifier nobody reads, and the literature is specific about how it happens.

**What the SRE literature establishes** [S13, rendered, reduced confidence, quoted-via-fetch]:

- The actionability test: *"Every page response should require intelligence. If a page merely
  merits a robotic response, it shouldn't be a page."*
- The capacity claim, stated in the first person by a practitioner in the text: *"I can only
  react with a sense of urgency a few times a day before I become fatigued."*
- The mechanism of failure: *"When pages occur too frequently, employees second-guess, skim, or
  even ignore incoming alerts, sometimes even ignoring a 'real' page that's masked by the
  noise."*

**What Prometheus' first-party practices page adds** [S11, quoted-via-fetch]: *"Aim to have as
few alerts as possible, by alerting on symptoms that are associated with end-user pain rather
than trying to catch every possible way that pain could be caused."*; *"Alerts should link to
relevant consoles and make it easy to figure out which component is at fault."*; and, for the
batch-job case which is the closest analogue to a dispatch, *"If you cannot withstand a single
run failing, run the job more frequently, as a single failure should not require human
intervention."*

**What the recent survey literature establishes, and what it does not** [S23]: the 2026 SOC
survey *"synthesize[s] 119 records, including 87 core studies, into a four-stage workflow
taxonomy covering filtering, triage, correlation, and generative augmentation"* and finds
*"persistent gaps in operational validation, adversarial robustness, cross-environment
generalization, and evaluation practice"*. **Note what the abstract does not contain: any
"N% of alerts are ignored" statistic.** The widely-circulated figures of that shape are not
used in this paper, and their absence from the primary source is recorded so a future reader
does not re-import them.

**DERIVED — what this means for the design here. Inputs: [S13], [S11], [S23], §1.2's routing
rule, and `config/commands/standup.md`'s existing aging flag.**

Four rules, each falsifiable:

1. **Fire only on the class with no robotic response.** BLOCKED at time zero; everything else
   only via the time ladder. This is the SRE test applied to data this repo already produces —
   `HOLD` verdicts already split into `redispatch` (robotic) and `needs-assistance`
   (judgement).
2. **Never fire on completion.** The repo's one existing notification does exactly this
   (§3.1) and it is the single behaviour both the literature and the upstream paper rule out.
3. **The volume defence is structural, not clever.** This fleet's blocked-work rate is small by
   construction. Filtering sophistication is not what keeps this notifier readable — *the rate
   is*. Which means the rate must be measured before the build, because if it is high, the
   filter is wrong and no amount of grouping will fix it (§7.1 item 1).
4. **Ship two counters with the notifier or it is unfalsifiable.** (a) `/standup`'s aging count,
   as upstream requires; and (b) **the already-known fraction** — of notifications fired, how
   many told the operator something they did not already know. (b) is the direct dilution
   measure and it is the one the literature's failure mode ("skim, or even ignore") shows up in
   first. Neither counter requires new infrastructure.

---

## 7. Test plan — what research cannot settle

### 7.1 Measurements to take BEFORE the build

1. **What is the actual blocked-work rate?** Count `pr_review:` blocks with
   `verdict: HOLD` + `needs-assistance` over the last 8 weeks across the repo set. *Decides:*
   whether a notifier is warranted at all (§5.5 item 2), and whether §3.5's decision to skip
   grouping holds. *Cost:* one `gh` sweep, minutes. **Run this first.**
2. **What threshold should the severity ladder's 1× be?** Measure the distribution of
   `HOLD`-comment timestamp → first operator action, over the same window. The 1× rung should
   sit near the current median, not at a round number. *Decides:* the ladder's only free
   parameter. *Cost:* the same sweep.
3. **What is today's detection latency?** The same measurement answers `operator_interface.md`
   §7.1 item 4, which upstream flags as able to invalidate the whole recommendation. If the
   median is already low, defer.

### 7.2 Experiments the build must run

4. **Does a self-hosted ntfy with `cache-file` configured actually deliver to a phone that was
   off for 12+ hours?** *Test:* publish, power the device off past the cache duration, power on,
   observe. *Why:* §3.3 concludes no channel guarantees delivery; this measures how bad the
   real behaviour is, and validates that `repeat_interval` is doing the work rather than the
   channel.
5. **Does the repeat-from-state design actually recover a dropped notification?** *Test:* kill
   the ntfy server, let a blocked item appear, restart, confirm the next evaluation re-fires.
   *Why:* this is the falsification test for the paper's central design claim.
6. **Does the GitHub API budget survive a 5-minute tick across the full repo set?** *Test:*
   instrument one hour of polling and compare against `gh api rate_limit`. *Why:* §4.3
   objection 2.
7. **Does the inverse-alert heartbeat catch a credential expiry?** *Test:* revoke the token on
   one machine and confirm the silence-is-the-alarm path fires. *Why:* §4.3 objection 1 and
   §5.6.9 — the mitigation is uncited derived design and must be validated empirically.

### 7.3 Research follow-ups (cheap)

- **Fetch Apple's APNs storage semantics** from a non-JS source if one exists (§5.6.1). Matters
  only if iOS is the target device.
- **Fetch Gotify's documentation site** (not just the READMEs) for retention (§5.6.2) — closes
  the one place this paper preferred ntfy on an absence rather than a comparison.
- **Fetch RFC 5321 §4.5.4.1** by a method that reaches the section (§5.6.5), if email is
  reconsidered.
- **Fetch one SMS gateway's delivery documentation** (§5.6.7) to make the exclusion a
  comparison.
- **Resolve GitHub's per-parent sub-issue limit** (§5.6.8) if the inbox design uses sub-issues
  as its primary structure rather than labels.

### 7.4 Questions this paper deliberately does not answer

- **Whether webhooks should replace polling.** It would remove the latency floor (§4.3 objection
  5) at the cost of a publicly reachable endpoint on a fleet of laptops and VMs — a network and
  security question above this paper's altitude.
- **Whether the notifier survives the Temporal port.** `operator_interface.md` §4.1 establishes
  that Temporal supplies run-state, history and failure triage but **not** a blocked-work inbox
  and **not** any outbound notification. That makes this item port-independent, which is why
  upstream sequenced it first — but the *detectors* for the artifact-negative classes (§1.3)
  may well be replaced by Temporal's Workers tab, and that trade belongs to sprint line 182's
  planning, not this one's.
- **The gh-monitor delete-or-keep decision** (§5.3) — Escalation, operator's call.

---

## 8. Citations

**First-party — self-hosted push**

- **[S1]** `binwiederhier/ntfy` repository metadata (GitHub API; `default_branch: main`, Apache-2.0, 33,220★, pushed 2026-08-04, not archived) — https://api.github.com/repos/binwiederhier/ntfy
- **[S2]** ntfy publishing documentation (raw `.md`) — https://raw.githubusercontent.com/binwiederhier/ntfy/main/docs/publish.md
- **[S3]** ntfy server configuration, "Message cache" (raw `.md`) — https://raw.githubusercontent.com/binwiederhier/ntfy/main/docs/config.md
- **[S4]** ntfy phone subscription / instant delivery (raw `.md`) — https://raw.githubusercontent.com/binwiederhier/ntfy/main/docs/subscribe/phone.md
- **[S5]** `gotify/server` repository metadata (GitHub API; `default_branch: master` — **not** `main` — 15,657★, pushed 2026-08-06, not archived) — https://api.github.com/repos/gotify/server
- **[S6]** Gotify server README (raw `.md`) — https://raw.githubusercontent.com/gotify/server/master/README.md
- **[S7]** Gotify Android client README (raw `.md`) — https://raw.githubusercontent.com/gotify/android/master/README.md

**First-party — third-party push and escalation**

- **[S8]** Pushover API documentation — https://pushover.net/api *(rendered HTML only; reduced confidence, quoted conservatively)*
- **[S12]** PagerDuty, *Escalation Policies* — https://support.pagerduty.com/main/docs/escalation-policies *(rendered HTML only; reduced confidence — numeric defaults NOT asserted, see §5.6.6)*
- **[S16]** Firebase Cloud Messaging, *Set the lifespan of a message* — https://firebase.google.com/docs/cloud-messaging/customize-messages/setting-message-lifespan *(rendered HTML only; reduced confidence)*

**First-party — alerting systems**

- **[S9]** `prometheus/alertmanager` repository metadata (GitHub API; `default_branch: main`, Apache-2.0, 8,571★, pushed 2026-08-04, not archived) — https://api.github.com/repos/prometheus/alertmanager
- **[S10]** Alertmanager configuration reference — grouping, inhibition, repeat (raw `.md`) — https://raw.githubusercontent.com/prometheus/alertmanager/main/docs/configuration.md
- **[S11]** Prometheus, *Alerting* best practices (raw `.md`) — https://raw.githubusercontent.com/prometheus/docs/main/docs/practices/alerting.md
- **[S14]** Apprise README (raw `.md`) — https://raw.githubusercontent.com/caronc/apprise/master/README.md
- **[S15]** Apache Airflow, *Tasks* — task-instance states (raw `.rst`) — https://raw.githubusercontent.com/apache/airflow/main/airflow-core/docs/core-concepts/tasks.rst
- **[S24]** Apache Airflow `airflow-core/docs/core-concepts/` contents listing (GitHub API; 22 entries enumerated and counted by this analyst — used to establish that no `hitl.rst` exists at that path) — https://api.github.com/repos/apache/airflow/contents/airflow-core/docs/core-concepts

**First-party — GitHub as channel and inbox**

- **[S18]** `github/docs` repository metadata + contents listings for `content/` (38 entries), `content/subscriptions-and-notifications/` (6), `.../concepts/` (3), `.../reference/` (4), and `content/issues/tracking-your-work-with-issues/using-issues/` (15) — each enumerated and counted by this analyst (GitHub API; `default_branch: main`, CC-BY-4.0, 20,626★, pushed 2026-08-06) — https://api.github.com/repos/github/docs
- **[S19]** GitHub Docs, *About notifications* (raw `.md`) — https://raw.githubusercontent.com/github/docs/main/content/subscriptions-and-notifications/concepts/about-notifications.md
- **[S20]** GitHub Docs, *Inbox filters* (raw `.md`) — https://raw.githubusercontent.com/github/docs/main/content/subscriptions-and-notifications/reference/inbox-filters.md
- **[S21]** GitHub Docs, *Adding sub-issues* (raw `.md`) — https://raw.githubusercontent.com/github/docs/main/content/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues.md
- **[S22]** GitHub Docs, *Creating issue dependencies* (raw `.md`) — https://raw.githubusercontent.com/github/docs/main/content/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies.md

**First-party — chat**

- **[S17]** Matrix Client-Server API, *Push Notifications* module (raw `.md`) — https://raw.githubusercontent.com/matrix-org/matrix-spec/main/content/client-server-api/modules/push.md

**Literature and practice**

- **[S13]** Google SRE Book, Ch. 6 *Monitoring Distributed Systems* — https://sre.google/sre-book/monitoring-distributed-systems/ *(rendered HTML only; reduced confidence, quoted conservatively)*
- **[S23]** Ndichu, S., Ban, T., Ozawa, S., Takahashi, T., Inoue, D. (2026-05-08, rev. 2026-05-18). *AI-Driven Security Alert Screening and Alert Fatigue Mitigation in Security Operations Centers: A Survey.* arXiv:2605.08316 — https://arxiv.org/abs/2605.08316 *(abstract page, rendered)*

**Upstream research consumed as given (evidence, not binding — Research Standard §1)**

- `docs/standards/architecture/research/raw/operator_interface.md` — `Last validated: 2026-08-04`, `Critic: PASS-WITH-FIXES` (Bainbridge verbatim span de-drifted; attribution correction; Prefect/Dagster claim corrected; three precision nits). §0, §3.4, §4.1, §4.3, §5.2, §6, §7.1 consumed.
- `docs/standards/architecture/research/raw/hermes_assessment.md` §5.2 — the stranded-work severity ladder (threshold → error at 2× → critical at 6×).
- `docs/standards/architecture/research/synthesis.md` — candidate 22 (the settled negative + this item's sizing) and candidate 10 (the three-legged liveness taxonomy).

**This repo (current-state description, not external evidence)**

- `docs/development/sprint.md` line 183 · `docs/standards/research/research_standard.md` §7 ·
  `docs/standards/documentation/documentation_standard.md` (standup-tracker definition) ·
  `config.yaml` · `config/settings.json` · `config/hooks/notify-done.sh` ·
  `config/commands/standup.md` · `scripts/services/gh-monitor.sh` ·
  `scripts/services/gh-monitor.timer` · `scripts/workflows/*.sh` (9 files, enumerated)
