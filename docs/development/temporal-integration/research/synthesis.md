# Synthesis — Temporal Integration

**Cycle:** 2026-08-19 (minor cycle — one paper added to a pool inherited from the dissolved
`Fleet Reliability` sprint) · **Pool: 6 papers** (enumerated below) · **This cycle: 1 paper added
(`activity_retry_boundary.md`), 0 retired, 1 `Feeds:` line corrected**

Read this instead of the pool. Nothing here is binding — research is evidence, and a finding
becomes a rule only by being codified into a standard through human review.

---

## Pool inventory and currency

**Two papers serve THIS destination** (`docs/development/sprint.md` § Temporal Integration):

| Paper | Feeds (Temporal Integration milestone) | Last validated | Critic verdict |
|---|---|---|---|
| `raw/durable_dispatch_identity.md` | "A restart-recovery contract" (sprint.md:188) | 2026-08-07 | PASS-WITH-FIXES (2026-08-07) — extended three truncated quotations to their source sentence ends; withdrew a Candea & Fox "unretrievable" negative finding after re-fetching the PDF and rewrote five sections around the now-cited source; corrected a version enumeration from 8 to 11 point releases; one critic finding disputed with evidence |
| `raw/activity_retry_boundary.md` | "Rule the retry boundary" + "Reduce gh()'s own retry" (sprint.md:189–190) | 2026-08-19 | PASS-WITH-FIXES (2026-08-19) — fresh-context pass: 8 external sources fetched at pinned SHAs, every quoted span re-checked byte-exact, zero fabricated and zero miscited; every repo claim re-checked against the working tree. Fixed: a log formatter named as the timeout gate, and a span count the artifact does not let a reader re-derive |

**Four papers are physically in this pool but do NOT feed Temporal Integration** — see
*Housekeeping* below, which draws on their substance, so they are cited here under §4's input rule
rather than merely named:

| Paper | Actually feeds | Last validated | Critic verdict |
|---|---|---|---|
| `raw/liveness_signal_measurement.md` | Autonomous Operation (sprint.md:243) | 2026-08-07 | PASS-WITH-FIXES, three rounds — withdrew an "undocumented heartbeat" headline that rested on a silently-truncated fetch, and re-enumerated the log corpus |
| `raw/blocked_work_notification.md` | Autonomous Operation (sprint.md:244) | 2026-08-07 | PASS-WITH-FIXES — 24 sources all fetchable; retention and delivery claims re-verified |
| `raw/credential_expiry_detection.md` | "Three cheap guards" — **milestone no longer exists** | 2026-08-07 | PASS-WITH-FIXES, 3 rounds — corrected which release introduces the `claude auth` subcommands, retracted a false "absent from the changelog" finding, and in r3 retracted the r2 repair itself after five further changelog entries turned up |
| `raw/false_completion_detection.md` | "Three cheap guards" — **milestone no longer exists** | 2026-08-07 | PASS-WITH-FIXES, rounds 1–3 all applied, verified over three passes |

Per the computed currency table this cycle was given: none of the five inherited papers are past
their revalidation window as of 2026-08-19. That clears them of *staleness*; it says nothing about
whether they still feed the destination they claim to (see Housekeeping).

**Upstream product research cited, not re-derived** (dates and verdicts given because §4's input
rule applies to these too): `python_sdk_long_activities.md` (*Last validated 2026-08-03, Critic
PASS-WITH-FIXES — un-quoted an inference dressed as a quote, re-marked a "Go only" claim as
derived, retagged staff-forum claims to unverified*) already closes the "claude_cli activity
domain" milestone (heartbeating, payload limits) in full — definitive, first-party sourced, its
own `Feeds:` line names that exact milestone. Nothing in this cycle adds to it. `temporal.md`
(*Last validated 2026-08-05, Critic PASS-WITH-FIXES over two independent passes — every source
re-fetched, every count re-derived by enumeration*) already establishes Temporal's default
`RetryPolicy` (unlimited max attempts, 1s initial interval, 2.0 backoff, 100× max interval) as a
hazard requiring override.
`anthropic_tos_and_enterprise.md` §1.5 (*Last validated 2026-08-06, Critic PASS 2026-07-24*)
establishes that headless `claude -p` invocation is explicitly ToS-sanctioned. **That answers the
PERMISSION half of "Prove an invocation is indistinguishable from an operator at a terminal"
(sprint.md:183) and no more** — and the sprint line itself says the permission half is not the
question: *"Not a permission question; a design one."* The design half — whether an invocation is
technically indistinguishable in behaviour from an operator's — is untouched by that paper and by
this cycle; see Gaps. A separate billing-classification question also remains open, in that paper's
§9, which its own header marks appended and **NOT critic-verified**.

---

## What this cycle found

### The retry boundary needs a prerequisite the sprint item doesn't name, and the fleet already has the pattern for half of it

`gh()`'s in-process bounded retry (`_RETRYABLE_HTTP`, three attempts) and Temporal's own
activity-level retry would compose to 3×3=9 attempts if simply nested — the sprint item
(sprint.md:189–190) already names this and asks to cut `gh()` to one attempt, carrying
`_RETRYABLE_HTTP`'s classification into `non_retryable_error_types`.

**`activity_retry_boundary.md` verified the SDK mechanics that design depends on and found a
blocker:** a Temporal retry engages **only** when the activity raises — a returned
`ActivityResult(status="failed")` is a *successful* Activity Task Execution and produces zero
retries [S4, S5 in that paper, definitive]. `gh()` today raises one bare `RuntimeError` for every
failure class, which under the SDK's exact-string `non_retryable_error_types` matching [S1, S5, S6]
collapses to a single opaque type. **The sprint's design cannot be implemented until `gh()` raises
a typed exception carrying `_RETRYABLE_HTTP`'s split** — the paper gives the concrete shape (§2.5).

**Two live hazards found beyond the prerequisite:**
- Moving retry ownership to Temporal has **no representation for `_gh_is_read_only`** — the
  mutation guard that issue #41's duplicate-comment incident motivated. Folding it into the raise
  is required or it is silently lost, at Temporal's attempt count rather than `gh()`'s.
- Any `except … raise RuntimeError(...)` between the typed raise and the activity boundary erases
  the classification — first-party documented as the *outermost*-error-type rule — and `gh_json`
  and several callers currently re-wrap this way.

**The paper's recommendation is split, not a single winner, and the split maps onto work this
fleet already ratified once:** for read-only, already-idempotent `gh` activities, cut to one
attempt and let Temporal own retry (needs the typed raise above). For mutating activities and any
wrapper doing file/git work before the `gh` call, **keep `gh()`'s bounded retry and mark the
resulting code terminal to Temporal** — this is not a new pattern; `temporal_standard.md` §6.4
already carves out exactly this shape for `CLUSTER_RECONCILE_CONTROL_PLANE_UNAVAILABLE` and
`SEED_CLUSTER_ACCESS_UNAVAILABLE` — a code whose retryable-looking `*_UNAVAILABLE` suffix is
overridden to terminal, in the standard's own words, because it expresses a verdict *"that the
activity already bounded-retried in-process"*. (Only the inner span is quoted; the ⇒-shorthand an
earlier draft of this line put in quotation marks appears nowhere in the standard.)
The reasoning: Temporal retries the **whole activity body**, not the failed sub-call [S7 in that
paper, definitive], so option (a) is only safe once every `gh`-wrapping activity is confirmed
idempotent end-to-end — an audit that has not been done — while option (b) gets the same 3×1
attempt bound the sprint wants without waiting on that audit.

**A negative finding worth carrying forward:** first-party Temporal documentation gives no
guidance anywhere on composing a library's own in-process retry with the SDK's retry policy
(searched, method stated in the paper). Option (b) is this fleet's own precedent, not published
Temporal advice — cite the internal standard, not Temporal, when applying it.

### The restart-recovery contract's prior findings still apply unchanged

`durable_dispatch_identity.md`'s content is untouched this cycle — only its `Feeds:` line was
corrected (it pointed at the dissolved "Fleet Reliability" section; the milestone it answers moved
into Temporal Integration unchanged). Its load-bearing findings, not re-derived here:

- **Dispatch-identity generation must move out of the activity, in both the bash and Python
  paths.** Today it is minted inside the activity (a wall-clock filename); under Temporal's
  default retry that produces a fresh identity on every attempt. **Must precede Stage B.**
- **The six-component identity schema and per-subsystem recovery table are ready to adopt** as
  the recovery contract — three of its rows are the (now-orphaned, see Housekeeping) "three cheap
  guards," currently "nowhere yet."
- **Do not build claim/lease/TTL, a boot reconciler, or retry bookkeeping** — Temporal replaces
  that layer outright. Name the liveness predicates as record fields; stop there.

---

## Housekeeping — a defect this cycle found and did not fix

**Four papers in this pool's `raw/` do not feed Temporal Integration, and this run is not the
right actor to re-home them:**

- `liveness_signal_measurement.md` and `blocked_work_notification.md` feed milestones that moved
  to **Autonomous Operation** (`sprint.md:243`, `:244`), not Temporal Integration.
- `credential_expiry_detection.md` and `false_completion_detection.md` feed "Three cheap guards" —
  a milestone that **no longer exists anywhere in `sprint.md`**. It was not merged into another
  section; it was dropped when Fleet Reliability dissolved.

All four are `current` per this cycle's revalidation table and their substantive findings (the
discarded-signal argument, the `check_rate_limit()` stdout-discard defect, the artifact-assertion
guard design, the disposable-notification/durable-inbox design) are unaffected — they are simply
shelved under the wrong component's research directory with stale `Feeds:` pointers. **This is an
operator-ruling gap, not a research gap:** whether they move to a new Autonomous Operation pool,
whether "three cheap guards" gets re-created as a milestone somewhere, and where its own restart
contract dependency (it needs milestone 8's schema, which now lives here) gets tracked, are
sequencing decisions above this run's altitude. Flagged in Post-Run Reflection.

---

## Action candidates

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Before wrapping any `gh`-calling activity: make `gh()` raise a typed exception carrying `_RETRYABLE_HTTP`'s split**, not a bare `RuntimeError`. Blocking prerequisite for either retry-boundary design below — neither `non_retryable_error_types` nor a terminal verdict can be expressed until this ships. Hours | adopt | `activity_retry_boundary.md` §2.5, §3 |
| 2 | **Read-only, already-idempotent `gh` activities: cut `gh()` to one attempt, let Temporal own retry via `non_retryable_error_types`.** Fold `_gh_is_read_only`'s guard into the raise or it is silently lost. Requires candidate 1 | adopt | `activity_retry_boundary.md` §3(a) |
| 3 | **Mutating `gh` activities, and any activity doing file/git work before the `gh` call: keep `gh()`'s bounded retry, mark the resulting code terminal to Temporal** — the fleet's own §6.4 `CLUSTER_RECONCILE`/`SEED` pattern, not a new one. Avoids depending on an idempotency audit that has not been done | adopt | `activity_retry_boundary.md` §3(b), §5 |
| 4 | **Audit every planned `gh`-wrapping activity for whole-body idempotency before extending candidate 2 beyond read-only calls.** Temporal retries the entire activity, not the failed sub-call — the population, not a sample | adopt (blocking, before scope expansion) | `activity_retry_boundary.md` §2.7, §3(a), §7 item 6 |
| 5 | **Move dispatch-identity generation out of the activity, in both the bash and Python paths, before Stage B.** Carried forward unchanged | adopt | `durable_dispatch_identity.md` §5.2d, §6 item 1 |
| 6 | **Adopt the six-component identity schema as the recovery contract.** Carried forward unchanged | adopt | `durable_dispatch_identity.md` §2.7, §4.1–§4.2 |
| 7 | **Do not build claim/lease/TTL, a boot reconciler, or retry bookkeeping — Temporal replaces this layer.** Carried forward unchanged | no change *(the negative is the finding)* | `durable_dispatch_identity.md` §4.5, §5.4 |
| 8 | **Rule where the four misplaced papers and the orphaned "three cheap guards" work belong.** Not this run's decision — see Housekeeping | operator ruling | this synthesis, Housekeeping |

**Homeless findings: none this cycle** — candidates 1–7 land in the Temporal Integration phase doc
(not yet written); candidate 8 is an operator ruling, surfaced in Post-Run Reflection.

---

## Gaps this cycle did not cover

- **No empirical confirmation of any §2 SDK claim in `activity_retry_boundary.md`** — every claim
  is source-read against pinned commits, none is run against a live worker. Its own §7 test plan
  names seven items, none executed.
- **`activity_retry_boundary.md`'s §6 span count is not reproducible from the artifact.** The
  verification pass re-checked its spans independently and found none that failed, but the paper
  does not print the enumeration behind its "21 spans" figure, so the pass rate is verified and the
  total is not. Recorded in the paper's §6; a re-check must re-enumerate rather than trust it.
- **The `GITHUB_*` error-code vocabulary is not enumerable from this repo** — `temporal_standard.md`
  §6.4 points it at a GitHub Automation Standard that is not vendored here (verified: no
  `docs/standards/github-automation/` directory). New codes must be minted with the activity under
  §6.4's engineer-editable carve-out rather than derived from an existing list.
- **Milestone 3 ("Prove an invocation is indistinguishable from an operator at a terminal") is
  OPEN on the half that is actually the milestone.** The sprint line disclaims the permission
  reading in its own text — *"Not a permission question; a design one"* — and the permission
  reading is the only one the upstream evidence answers. Nothing in this pool or the upstream
  papers addresses the DESIGN question: what makes a headless invocation behaviourally
  indistinguishable from an operator at a terminal, and how that would be demonstrated. An earlier
  draft of this synthesis called the milestone "substantially answered," which overstated the
  cited evidence; it is not.
- **A second, separate question is also open** — whether a personal automation script classifies
  as sanctioned "Claude Code on your own machine" use or as "programmatic Agent SDK use" under the
  paused June-2026 billing change. It sits in `anthropic_tos_and_enterprise.md` §9, a hand-appended
  section that paper's header marks NOT critic-verified. Not researched this cycle; a product-pool
  question, not a component one.
