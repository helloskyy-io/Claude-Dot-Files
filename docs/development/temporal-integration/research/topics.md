# Topics — temporal-integration

**Last assessed:** 2026-08-07 (cycle 1 — the pool was empty before this run)

## Tier and count

**Tier: Medium — 5 topics.** Per Research Standard §2, Medium is *"multi-concern component, real alternatives exist"* at 3–5 topics, and a cycle runs at most ~5 regardless of band.

Justification tied to what the destination actually contains. **Written for the `Fleet Reliability` sprint section, which dissolved on 2026-08-19 — this pool moved to Temporal Integration and the milestones it names moved with it.** That section carried **five milestones**, and no phase doc existed for it; the same is true of Temporal Integration today, so the planning step this pool feeds is unchanged and the reasoning below still holds. Four of the five milestones name a mechanism that does not exist in the fleet today and for which real alternatives exist (state store shape, detection signal, notification channel, threshold policy). That is the Medium band's definition, not the Large band's — this component has **one destination** (the fleet-reliability phase doc), which per §2 is the test for whether it is one component.

**It is NOT Large.** The Large band is the stack-level, direction-setting altitude. Whether to build a reliability layer, and what the five milestones should be, was settled by the product pool before this became a sprint section. This cycle answers only *how to build them*.

**The topic list does not exceed the per-cycle cap**, so no split across cycles is needed for the topics chosen. One milestone is deliberately deferred to a second cycle against this same directory (below).

## Topics

| # | Topic | Feeds | Paper |
|---|---|---|---|
| 1 | Where durable dispatch state lives, what a dispatch id must contain, and how per-subsystem restart recovery survives the bash → Python → Temporal port | Sprint milestone **"A restart-recovery contract"** → the temporal-integration phase doc's recovery design | `raw/durable_dispatch_identity.md` |
| 2 | How *stalled*, *looping* and *stranded* are each measured against a live `claude -p` process — available signals, thresholds, and the cost of a false positive on each leg | Sprint milestone **"The three-legged liveness predicate"** → the phase doc's detection design | `raw/liveness_signal_measurement.md` |
| 3 | How a headless dispatch detects an expired or invalid Claude Code subscription session — before dispatch and mid-run | Sprint milestone **"Three cheap guards"**, credential-expiry guard | `raw/credential_expiry_detection.md` |
| 4 | How a run's self-reported success is verified against observable artifacts, given `exit_code == 0` is already known to be necessary-but-not-sufficient | Sprint milestone **"Three cheap guards"**, false-completion guard | `raw/false_completion_detection.md` |
| 5 | The blocked-work notification channel and the operator inbox behind it — delivery semantics, dedupe, escalation, and git-native vs. push surfaces | Sprint milestone **"A blocked-work notifier"** → the phase doc's operator-surface design | `raw/blocked_work_notification.md` |

Sequenced most-decision-blocking first: topic 1 constrains topics 2–4, because the sprint states the recovery contract is *"designed once and covering all three guards."*

## Already settled upstream — cited, not re-researched

The product pool (`docs/standards/architecture/research/`, 25 papers, synthesis dated 2026-08-06) already establishes **what** each milestone is and **why** it exists. This cycle does not re-derive any of it:

- **The three-legged liveness taxonomy itself** (stalled / looping / stranded) — product synthesis candidate 10, from `paperclip_assessment.md` §4.4, `openclaw_assessment.md` §4.7, `hermes_assessment.md` §5.2. Topic 2 takes the taxonomy as given and researches only its measurement.
- **That the recovery contract must be designed before workers exist** — candidate 9, from `openclaw_assessment.md` §6 items 3–4 and `hermes_assessment.md` §7 item 4. Topic 1 takes the sequencing as given.
- **That the answer is a notifier and an inbox, not a dashboard** — candidate 22, from `operator_interface.md` §0, §6. Topic 5 takes the negative as given and researches only the channel and inbox shape.
- **That the three cheap guards are the right three, at ~9 operator-hours** — candidate 21, from `fleet_failure_modes.md` §7.
- **That credential/session expiry at an unattended edge is unsolved industry-wide** — `edge_identity_trust.md` §5, and the product synthesis' *"Re-authentication of an expired subscription session at an unattended edge"* gap. Topic 3 does **not** re-open the industry survey; it asks the narrower, first-party-answerable question of what Claude Code itself emits on an expired session.
- **That quota headroom is derivable from observed cap-errors without provider telemetry** — candidate 11, from `hermes_assessment.md` §5.1. This is the reason topic 6 is deferred rather than run.

## Gaps named but NOT covered this cycle

- **Per-credential quota headroom — the mechanism for our single subscription.** Destination: sprint milestone *"Per-credential quota headroom"* → the phase doc. **Why deferred:** the per-cycle cap is ~5 topics (§2) and this is the least decision-blocking of the six — it is the last milestone, it constrains nothing else, and its blocking unknown was already discharged upstream (`hermes_assessment.md` §5.1 shows headroom is derivable from cap-errors; product candidate 11 sizes it at ~1 day + hours and explicitly rules out the rotation half). What remains is a component-level provider-error taxonomy for Claude Code specifically. **Run it as cycle 2 against this same directory.**
- **The safety-hook wiring test** (third of the three cheap guards). Destination: same milestone as topics 3–4. **Why not a topic:** it needs a test written, not evidence gathered — the mechanism is already named in the `Managed Configuration` sprint section's blocker note (`sprint.md:168`), which records that `block-dangerous.sh` lives in user-level `settings.json` and is the only live control under `--dangerously-skip-permissions`. Researching it would produce a paper restating a known fact.
- **What happens to a Temporal Task already handed to a worker that then sleeps.** Destination: the Temporal Integration phase doc, not this one. **Why deferred:** it belongs to a different component (product synthesis lists it as an uncovered product-pool gap, `edge_identity_trust.md` §9 item 11). Named here because topic 1's recovery contract must survive the Temporal port and will brush against it — if topic 1 finds it load-bearing for *this* component, that is an escalation, not a topic this pool absorbs.

## Retired topics

None — this is cycle 1 and no paper predates it.
