# Synthesis — fleet-reliability (DRAFT)

**Cycle:** 2026-08-07 (cycle 1 — the pool was empty before this run) · **Pool:** 5 papers · **Tier:** Medium · **This cycle: 5 papers added, 0 retired, 0 revalidated**

> ## ⚠️ DRAFT — NOT YET VERIFIED
>
> **Every paper in this pool carries `Critic: not-yet-verified — 2026-08-07`.** No critic round was run: this workflow writes papers, and a **separate fresh-context run verifies them** — an actor that writes a paper and then certifies it has verified its own work.
>
> Treat every claim below as unverified evidence. The papers make heavy use of first-party raw-source fetches and several report fetch-layer defects they caught themselves (one analyst discarded two fetches outright, one as an *"outright fabrication"* contradicted by our own logs). That is the exact class the verification gate exists to catch, and it has not run yet.

Read this instead of the pool. Nothing here is binding — research is evidence, and a finding becomes a rule only by being codified into a standard through human review.

---

## Inputs

All five papers were written on 2026-08-07 against the `Fleet Reliability` sprint section (`docs/development/sprint.md` lines 172–184), whose phase doc does not yet exist. The currency table computed at dispatch reported **0 of 0 papers past window** — the pool was empty.

| Paper | Feeds (sprint milestone) | Last validated | Revalidate | Critic verdict |
|---|---|---|---|---|
| `raw/durable_dispatch_identity.md` | "A restart-recovery contract" (line 181) | 2026-08-07 | high — 4 weeks | **not-yet-verified** |
| `raw/liveness_signal_measurement.md` | "The three-legged liveness predicate" (line 182) | 2026-08-07 | high — 3 weeks (mixed-volatility; §3, §5.1, §6 marked LOW) | **not-yet-verified** |
| `raw/credential_expiry_detection.md` | "Three cheap guards" — credential expiry (line 180) | 2026-08-07 | high — 3 weeks | **not-yet-verified** |
| `raw/false_completion_detection.md` | "Three cheap guards" — false completion (line 180) | 2026-08-07 | high — 6 weeks (mixed-volatility) | **not-yet-verified** |
| `raw/blocked_work_notification.md` | "A blocked-work notifier" (line 183) | 2026-08-07 | high — 6 weeks | **not-yet-verified** |

**No papers are retired**, so no paper is excluded from this synthesis.

**Upstream product research is cited, never re-derived.** This pool takes as settled: the three-legged liveness taxonomy (`openclaw_assessment.md`, `paperclip_assessment.md`, `hermes_assessment.md` — product synthesis candidate 10); that the recovery contract must be designed before workers exist (candidate 9); that the answer is a notifier and an inbox, not a dashboard (`operator_interface.md` — candidate 22); that the three cheap guards are the right three (`fleet_failure_modes.md` — candidate 21); and that unattended re-authentication is unsolved industry-wide (`edge_identity_trust.md` §5). Each is cited in the paper that rests on it. Nothing was written to the product pool.

**Milestone 5 — per-credential quota headroom — was deliberately not researched this cycle.** Reasoning and the cycle-2 pointer are in `topics.md`.

---

## What this cycle found

### 1. The fleet already produces the signals all three guards need, and throws them away

This is the cycle's strongest result and no single paper contains it. Three analysts, working independently on three milestones, each found a first-party signal the fleet **already touches and then discards**:

- **`claude auth status` exists, is documented to exit `0` if logged in and `1` if not, and is not a `-p` model query — so (derived) it costs no turn.** The fleet instead preflights with `claude -p "ping" --max-turns 1`, which spends subscription quota on every single dispatch. (`credential_expiry_detection.md` §2.2)
- **The `claude -p` stream already carries a real periodic heartbeat.** `tool_progress` events with `"heartbeat": true` and a monotonic `elapsed_time_seconds`, on a **30-second cadence that restarts per tool call**, covering `Bash`, `TaskOutput` and `Agent`. Measured empirically: 125 occurrences across 6 of 57 logs in `.claude/logs/`. Nothing in the fleet parses them. This is precisely the signal that stops a naive no-output detector firing on a legitimate long tool call. (`liveness_signal_measurement.md` §2.3)
- **`run-claude.sh` already computes the completion-contract verdict and discards it.** (`durable_dispatch_identity.md` §6 item 8)

**What this means for us:** the sprint budgets these as three *cheap* guards at ~9 operator-hours (upstream `fleet_failure_modes.md` §7). The evidence says that estimate is if anything generous — the expensive part of a guard is usually acquiring the signal, and the signals are already on disk. **But the heartbeat is undocumented** (below), which converts a cost saving into a maintenance liability.

### 2. The existing credential preflight cannot detect an expired credential — by construction, not by omission

`run-claude.sh`'s `check_rate_limit()` runs its probe as `2>&1 >/dev/null`, capturing **stderr only**. Anthropic documents that an in-run failure *"such as missing authentication"* is printed as the result on **stdout**. So the auth text is discarded before the grep runs, the rate-limit pattern cannot match, and control falls into the `return 0` *"don't block, let the real run surface it"* branch — on an unattended machine, nobody is watching that branch. (`credential_expiry_detection.md` §2.1)

This is not a gap in coverage; it is a defect in shipped code that the guard's design must correct rather than route around. **Mid-run expiry, by contrast, is cleanly detectable in the JSONL the fleet already writes** — `error: "authentication_failed"`, `api_error_status: 401`, and the exact string `Failed to authenticate: OAuth session expired and could not be refreshed` — needing only a `jq` pass shaped like the existing `error_max_turns` check. (§4.2, §4.4)

**One trap worth carrying forward.** The obvious community workaround — gate dispatch on `~/.claude/.credentials.json`'s `expiresAt` — would fire constantly: that field sits only ~3.4h out on a *healthy* session (one local sample, undocumented schema). `refreshTokenExpiresAt` is the horizon-relevant field, and a shipped release has been observed writing `expiresAt: 0`. The paper's ruling: the file is **advisory-only, never blocking**. (§3.3)

**The load-bearing gap (G2):** whether `auth status` exit `1` covers *"saved but expired"* or only *"no credential at all"* is undocumented. **The entire preflight hinges on it**, and it is a five-minute experiment, not a research question.

### 3. Three milestones need the same write at dispatch time — which is why "designed once" is correct, and sharper than the sprint states

The sprint asserts the recovery contract should be *"designed once and covering all three guards."* Three papers independently converge on **why**, and the reason is mechanical rather than conceptual:

| Milestone | What it needs recorded at DISPATCH time | Source |
|---|---|---|
| Restart-recovery contract | the dispatch record itself | `durable_dispatch_identity.md` §4.2 |
| **Stranded** detection | a claim record — "never claimed" is undistinguishable from "claimed and silent" without one | `liveness_signal_measurement.md` §4.3 |
| False-completion detection | the **pre-state** (head SHA) the post-run assertion diffs against | `false_completion_detection.md` §4.1 |

**One artifact serves all three.** Planning them separately produces three partial records — which is the concrete form of the failure upstream's candidate 9 warned about.

`durable_dispatch_identity.md` supplies the schema: a six-component model derived from a first-party survey of Temporal (workflow id + run id, plus its two *orthogonal* reuse/conflict policies), GitHub Actions (`run_id`/`run_attempt`), GitLab's ID-vs-IID scope split, systemd's `$INVOCATION_ID`, message-queue identity, and the IETF `Idempotency-Key` draft (**expired — there is no ratified standard**, corroborated against Stripe and AWS). **This fleet has none of the six.** Its identity today is a wall-clock filename minted *inside* the activity, in bash and — re-derived independently — in the Python port at `assistant_activities.py:252-253`.

**Why that specific fact is urgent:** under Temporal's default retry policy, an identity minted inside the activity becomes a **fresh identity on every retry**. Moving generation to an activity *input* costs one parameter and must precede Stage B of the Temporal port.

**Corroborating evidence that identity-by-filename has already failed here:** enumerating `.claude/logs/*.jsonl` returned 57 files (stated as a floor, since the population may be incomplete), of which **19 are named for `revision`/`revision-major` scripts that no longer exist**. V1 and V2 already use two different naming authorities.

### 4. The verdict must be separated from the action, and the false-positive economics differ per leg

Two papers reach this independently, and it is the finding most likely to be lost if the phase doc treats "detection" as one thing.

| Leg | False-positive cost | False-negative cost | Implied action |
|---|---|---|---|
| **Stalled** | worst — kills up to 60 min of unrecoverable paid work | mild — measured silent-death rate is 0.9% (4/443) | **record and alert; do NOT kill** |
| **Looping** | structurally rare — byte-identity is hard to hit by accident | unbounded — a loop burns quota indefinitely | **the one leg that earns automatic intervention** |
| **Stranded** | cheap | cheap | **most sensitive threshold; escalate, never retry-in-place** |

(`liveness_signal_measurement.md` §5.2–§5.4)

`false_completion_detection.md` §5.3 reaches the same shape from the other side: fail-open on transport errors, let one assertion warn while the others fail closed.

**Supporting prior art, fairly stated:** Kubernetes' startup probe exists precisely because one threshold cannot serve both startup and steady state ⇒ thresholds must be phase-scoped. systemd's ≥2×-cadence rule ⇒ a 60-second floor here, given the observed 30-second heartbeat. And CircleCI's 10-minute idle kill versus GitHub Actions' wall-clock-only timeout proves the no-output threshold is **a policy choice, not a best practice** — there is no number to copy.

### 5. The false-completion guard's real yield is three classes, and the argument for artifact assertion is cost-to-fake

The shipped guard — `COMPLETION_PATTERN` plus `exit_code == 0 AND a PR URL appears in stdout` — catches exactly **one** of six false-completion classes (F1, silent early stop), which is also the only class the fleet has actually observed. It misses: **F2** fabricated/unresolvable pointer, **F3** real pointer with no delta, **F4** partial contract (the PR exists; the required Decision Log comment does not), and **F5/F6** hollow or criterion-gaming work.

**The whole marginal yield lies in F2–F4, and all three are decided by one act:** capture the pre-state at dispatch, then after the run resolve the pointer with `gh pr view --json` and require that it (a) resolves, (b) has a head SHA differing from the pre-state, (c) carries the contract's side-artifacts. ~2 subprocess calls.

**Why artifact assertion beats output matching is not thoroughness — it is cost-to-fake.** The completion pattern is a criterion the run is *told* to satisfy; the prompt instructs it to print the PR URL as its final line. A criterion an agent knows and can satisfy with one token is the exact shape reward hacking takes. Making a head SHA change requires doing the work.

**And "just add a verifier agent" is measurably worse for this class, not merely more expensive.** LLM *text* judges detect false success at AUROC ≤0.65/0.54, keying on confident closing language rather than verified state change. (Counterbalanced fairly in the paper against Agent-as-a-Judge and the CUA Universal Verifier, which are agentic state-*readers*, not text judges.)

**The honest limit, stated sharply:** these assertions certify that a declared artifact exists and changed. **They certify nothing about content.** A run that opens a real PR full of hollow work passes every one. F5 cannot be delegated to `review-pr`, because that stage audits the same self-report (upstream `decide_only_disposition.md` §5.7).

**A Temporal port hazard is named now, cheaply:** the pre-state must be captured **once at workflow start**. `run_child` is documented non-idempotent, so a retry would re-baseline the pre-SHA and turn the guard into one that always passes.

### 6. No notification channel publishes a delivery guarantee — and the correct response is to stop looking for one

Surveying ntfy, Gotify, Pushover, FCM, Matrix and GitHub: **not one publishes at-least-once delivery or ordering.** What they publish is *retention* — ntfy 12 hours and in-memory-only unless a cache file is configured; Pushover 21 days if unverified; FCM four weeks; GitHub's inbox five months.

**So make the notification disposable.** The durable state is the **inbox**; the notification is a lossy pointer, re-derivable and re-fired from state on a `repeat_interval`. **This dissolves the milestone's founding fear — "an alert dropped while the laptop is closed" — without needing any channel to be reliable.** (`blocked_work_notification.md` §3.3)

**The channel ruling:** GitHub as record, one self-hosted push channel (ntfy) as interrupt. GitHub is simultaneously the notification path, the inbox, and the surface the Research Standard §7 already binds every action-driving outcome to; it now ships first-class `blocked by` issue relations and sub-issues, both `gh`-driveable. **The counter is stated at full strength:** a git-native inbox is a third-party single point of failure for the surface that exists to catch failures, and it cannot detect its own detector's failure.

**Most alerting machinery does not transfer, and saying which parts do not is the finding.** With one operator there is no rota, so PagerDuty-style escalation cannot escalate to *anyone* — only change channel and priority. Alertmanager's `group_by`/`group_wait` solve a volume problem this fleet does not have. What transfers is `repeat_interval`, and it transfers as the load-bearing mechanism.

**Current notification config in this repo: none.** `config.yaml` and `scripts/services/` carry nothing; only `config/hooks/notify-done.sh` fires `notify-send` on the `Stop` hook — the wrong event, on-machine only, silently absent on VMs.

### 7. The sequencing the sprint implies is wrong in one place, and the reason is a correctness argument

`blocked_work_notification.md` §1.3: **"blocked" is artifact-positive; stalled, looping and stranded are artifact-negative.** A poller over git surfaces finds exactly one of four failure classes. **Ship the notifier alone and the operator learns that silence means health** — which is the same lesson the dashboard-nobody-opens taught, one step later, and it is the failure this whole sprint section exists to prevent.

Combined with §3 above, the evidence supports: **milestone 2 (the dispatch record) first → milestones 1 and 3 (the guards and the liveness legs, which write to it) → milestone 4 (the notifier, which reads from it).** The sprint lists them 1, 2, 3, 4.

### 8. Two dependencies with dates on them

- **The heartbeat the liveness design leans on is undocumented.** `tool_progress`, `heartbeat`, `thinking_tokens`, `rate_limit_event`, `vcs_state_changed` and `code_change_published` appear in **no first-party page fetched**, and Anthropic's own closed issue #24596 is titled *"[DOCS] CLI `--output-format stream-json` lacks event type reference."* The surface demonstrably moves: the `result` event's field order changed between this repo's April and August 2026 logs, and the heartbeat did not exist four months ago. **Design consequence:** log mtime is the schema-independent primary signal; the heartbeat is refinement, never the reverse.
- **`--bare` is stated by Anthropic to be *"the recommended mode for scripted and SDK calls"* and that it *"will become the default for `-p` in a future release"* — and bare mode *"never reads OAuth credentials or the system keychain."* The eventual default flips this fleet off its subscription login whether or not anyone rules on it. Escalated below.

---

## Escalations — findings above this component's altitude

Per the write boundary, these are surfaced and **not filed anywhere**. Only the first is a belief-level finding; I am listing the other two separately rather than inflating the escalation count, because they are operator rulings this component needs, not challenges to what the project believes.

**Belief-level — one:**

- **`--bare` becoming the `-p` default forces a credential-model decision the project has not made.** Anthropic's own unattended product (GitHub Actions) does not carry a `/login` session at all; its documented automation advice is `ANTHROPIC_API_KEY` or `claude setup-token`. Adopting `--bare` *forces* moving off the subscription login, and the roadmap statement means the default may arrive without anyone choosing it. **Bears on:** the product pool's `subscription_economics.md`, `anthropic_tos_and_enterprise.md` and `edge_identity_trust.md` — the credential-at-the-edge thesis. **What I think it means:** the credential-expiry guard should be built anyway (it is cheap and correct under either model), but a product-pool cycle should cost the `setup-token` path before this fleet invests further in subscription-session tooling. (`credential_expiry_detection.md` §8)

**Operator rulings needed before the phase doc is written — two:**

- **`sprint.md`'s "all three guards" (line 181) is ambiguous between two triples in its own section** — line 180's three cheap guards, and line 182's three liveness legs (a third triple exists upstream in `hermes_assessment.md`). `durable_dispatch_identity.md` §4.4 reads it as line 180's and states the contract serves all three regardless, but the phase doc will otherwise inherit the ambiguity and scope the recovery contract to the wrong triple. **Remedy:** one line in the phase doc stating the reading; the operator confirms. A research run does not edit planning artifacts.
- **Upstream's 1–2 day notifier estimate rests on a decayed anchor.** `operator_interface.md` §6.1 priced it *"anchored on `gh-monitor` (shipped)"*. Read from the repo on 2026-08-07: `config.yaml` sets `gh-monitor.enabled: false` with the comment *"DECISION POINT: if still unused by ~2026-08-19, delete the service rather than carry dead code"*, and `gh-monitor.sh` routes to `revision.sh`/`revision-minor.sh`, which are not among the nine scripts in `scripts/workflows/`. Its config route-enable keys are also inert (`enable-build*` vs. the script's `enable-revision*`). **Remedy:** rule on the 2026-08-19 decision point *before* the phase doc is written, and if the ruling is "delete", harvest the poller skeleton — the loop, lock file, rate-limit backoff and repo discovery — into the notifier rather than losing it and rebuilding it.

---

## Action candidates

Reviewable items, sized for a standup. **Nothing is ratified, and every candidate rests on an unverified paper.** Per §7 this run surfaces candidates here and writes nothing outside `research/` — routing is the reviewer's and the operator's. The natural home for candidates 1–12 is the fleet-reliability phase doc, which does not yet exist; writing it is the planning step this pool feeds.

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Sequence the milestones 2 → (1,3) → 4, not 1 → 2 → 3 → 4.** The dispatch record is what the guards and the liveness legs write to, and the notifier reads. Shipping the notifier before the liveness legs teaches the operator that silence means health — the artifact-positive/artifact-negative asymmetry makes this a correctness argument, not a convenience one. Cost 0; it is a re-ordering | change direction | `blocked_work_notification.md` §1.3; `durable_dispatch_identity.md` §4.2; `liveness_signal_measurement.md` §4.3 |
| 2 | **Fix `check_rate_limit()`'s stream capture before designing the credential guard.** `2>&1 >/dev/null` keeps stderr and discards stdout, where auth failures are printed — so the existing preflight cannot detect an expired credential by construction. This is a defect in shipped code, not a missing feature. Minutes | adopt | `credential_expiry_detection.md` §2.1 |
| 3 | **Replace the turn-spending `claude -p "ping"` preflight with `claude auth status`** — documented to exit `0`/`1`, not a model query, and (derived) zero-turn. It does not replace the rate-limit probe, only precede it: quota headroom is not observable before a session's first API response. Hours | adopt | `credential_expiry_detection.md` §2.2, §4.6 |
| 4 | **Settle G2 first: does `auth status` exit 1 cover "saved but expired", or only "no credential"?** The whole preflight hinges on it and it is undocumented. A five-minute experiment, not a research topic. **Do this before sizing the guard** | adopt | `credential_expiry_detection.md` §6.3 |
| 5 | **Move dispatch-identity generation out of the activity, in both the bash and Python paths.** Today it is a wall-clock filename minted inside `run-claude.sh` and, independently, `assistant_activities.py:252-253`. Under Temporal's default retry that yields a fresh identity per attempt. One parameter; **must precede Stage B of the Temporal port** | adopt | `durable_dispatch_identity.md` §2.6, §5.2, §6 item 1 |
| 6 | **Adopt the six-component identity schema and the per-subsystem table (six columns, nine rows) as the recovery contract.** Three rows are the three cheap guards and are currently "nowhere yet" — that is the concrete meaning of "designed once, not three times." Hours of design; constrains the build | adopt | `durable_dispatch_identity.md` §2.7, §4.2, §6 items 3–4 |
| 7 | **Two-tier state store: the small dispatch record git-native on `refs/dispatch/*` with `git update-ref`'s compare-and-swap; bulk transcripts stay local and referenced by `(machine-id, path)`.** `.gitignore` line 2 is `.claude/`, so nothing there crosses a machine today, and SQLite's own docs rule out direct multi-machine access as a corruption risk. 1–2 days | adopt | `durable_dispatch_identity.md` §3.3, §3.6, §6 items 6–7 |
| 8 | **Explicitly do NOT build claim/lease/TTL, a boot reconciler, retry bookkeeping or timers.** Temporal replaces exactly that layer. Name the liveness predicates as record *fields* so the guards have somewhere to write, and stop there. **Negative cost — it removes work** | no change *(the negative is the finding)* | `durable_dispatch_identity.md` §4.5, §5.4 |
| 9 | **Separate the liveness verdict from the action, per leg: stalled records-and-alerts, looping is the only leg that may intervene automatically, stranded escalates and never retries in place.** The false-positive economics are opposite on the first two, and one uniform policy gets one of them badly wrong | new concept | `liveness_signal_measurement.md` §5.2–§5.4 |
| 10 | **Build the stalled detector on log mtime as primary, with the undocumented `tool_progress`/`heartbeat` (30 s, per-tool-call) as refinement — never the reverse.** Thresholds phase-scoped (the startup-probe lesson), with a ≥60 s floor from systemd's 2×-cadence rule. There is no industry number to copy: CircleCI kills at 10 min idle, GitHub Actions has no idle timeout at all | adopt | `liveness_signal_measurement.md` §2.3, §3.1, §4.1 |
| 11 | **Strengthen the false-completion guard to pre-state + pointer resolution: capture the head SHA at dispatch, then `gh pr view --json` and require the pointer resolves, its head SHA changed, and the contract's side-artifacts exist.** Kills F2–F4; ~2 subprocess calls. **Capture the pre-state once at workflow start** — `run_child` is non-idempotent and a retry would re-baseline it into an always-passing guard | adopt | `false_completion_detection.md` §0, §4.1 |
| 12 | **Do NOT add a verifier agent for false completion.** LLM text judges detect false success at AUROC ≤0.65/0.54, keying on confident closing language rather than verified state change — more expensive *and* measurably worse for this class. Record the limit honestly alongside it: artifact assertion certifies a declared artifact exists and changed, and certifies nothing about content | no change *(the negative is the finding)* | `false_completion_detection.md` §3.3, §5.1 |
| 13 | **Make the notification disposable and the inbox durable: GitHub as record, ntfy as the interrupt, re-fired from state on a `repeat_interval`.** No surveyed channel publishes a delivery guarantee — only retention — so this is what dissolves the "dropped while the laptop was closed" failure mode without needing a reliable channel. Drop the rota-shaped machinery (`group_by`, escalation chains) that has nowhere to escalate to with one operator | adopt | `blocked_work_notification.md` §3.3, §4.1, §4.3, §3.5 |
| 14 | **Verify `gh pr view --json`'s field list before writing candidate 11's guard.** The analyst could not obtain the enumerable field list (`PullRequestFields` is not in `api/queries_pr.go`), so the field names in `false_completion_detection.md` §4 are marked unverified. Minutes, and it blocks the implementation | adopt | `false_completion_detection.md` §6.1 (N3) |
| 15 | **Run the two zero-dispatch log measurements before sizing anything.** (a) A histogram of legitimate quiet periods from existing `.claude/logs/*.jsonl` — it blocks every threshold in candidate 10; (b) a grep of the same corpus for auth failures — the base rate for candidate 3 is currently unmeasured. Both read files already on disk and cost no dispatches. **This is the cheapest high-value item in the pool** | adopt | `liveness_signal_measurement.md` §8 T1; `credential_expiry_detection.md` §7 T7 |
| 16 | **Plan the false-completion guard and the safety-hook wiring test together.** `topics.md` excluded the hook test as "needs a test written, not evidence gathered"; `false_completion_detection.md` §5.2 independently concluded the false-completion guard needs its own wiring test of the identical shape, with the identical `--setting-sources`/`--bare` hook-availability dependency. Two milestones, one test harness. **This is a sprint-item implication and the operator writes it** | change direction | `false_completion_detection.md` §5.2, §7 T6 |

**Homeless findings: none this cycle.** Candidates 1–15 land in the fleet-reliability phase doc (written by a planning run); 16 is a sprint-item implication, which §7's table routes to the operator; the three escalations above are the operator's to file. Every candidate has a surface that already exists.

---

## Gaps this cycle did not cover

- **Per-credential quota headroom** (sprint milestone line 184) — deferred to cycle 2 against this same directory; reasoning in `topics.md`. Upstream already discharged its blocking unknown (`hermes_assessment.md` §5.1: headroom is derivable from observed cap-errors), so what remains is a Claude-Code-specific provider-error taxonomy.
- **No on-harness false-completion rate exists**, so candidate 11 must not be sized against the cited benchmark rates (75.8% on AppWorld self-assessing trajectories; 97/154 DeployBench failures as agent self-stops). Test T1/T2 produce our own number for zero dispatch cost.
- **No false-positive rate exists anywhere for an artifact-assertion guard**, and no study ablates artifact assertion against output matching — candidate 11's superiority argument is *derived* from cost-to-fake, not measured.
- **`--session-id` collision behaviour is undocumented**, and there is no documented cross-machine Claude Code session portability — both bear on candidate 7's two-tier store.
- **No prior art was found anywhere for a client-side-only idempotency-key store** — every surveyed model assumes a server enforces uniqueness.
- **No complete first-party reference for the `stream-json` event vocabulary exists** (Anthropic issue #24596). Whether the fleet should maintain a pinned, tested schema snapshot is an architecture-layer question, noted in the escalation section's belief-level neighbourhood but not itself a belief item.
- **Gotify's retention is undocumented**; an APNs body fetch failed; an Apprise channel total and a GitHub sub-issue limit were both unassertable (the latter because the raw source carries an unexpanded Liquid variable) — all stated as gaps rather than estimated.
- **Candea & Fox, *Crash-Only Software*, could not be retrieved as text across five hosts** and is therefore cited nowhere in `durable_dispatch_identity.md`, despite being the canonical reference for its §4.3 rules.
- **The 0.9% (4/443) silent-death denominator is not reconstructible** from what is on disk — the log enumeration returned 57 files and is stated as a floor. The rate is quoted from `run-claude.sh`'s own comment and inherits its provenance.
- **Milestone 3's stalled leg may not be worth shipping yet.** `run-claude.sh` argues detection machinery is not worth building at 0.9% *under attended operation*; the sprint schedules it because unattended operation is coming. Both are correct under their own assumptions, and which one holds is an operator call rather than a research finding.
