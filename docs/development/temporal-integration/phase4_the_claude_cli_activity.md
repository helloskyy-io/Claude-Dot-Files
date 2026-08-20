# Phase 4 — The `claude_cli` activity domain

**Status: ⬜ NOT STARTED.** Fourth in [rollout order](roadmap.md).

**This is the one part of the port that is not a port.** Every activity in the vendored standards runs for seconds to minutes and returns a structured result. Ours runs for 10–60 minutes and returns prose. Nothing upstream reaches that shape, which is why [§A1 of the addendum](../../standards/temporal/claude-dot-files-addendum.md) has carried it as OPEN since the addendum was written, and why it is a phase of its own rather than a paragraph inside [Phase 5](phase5_the_first_dispatch.md).

**And it is not a temporary state to wait out.** There is no first-party Claude ↔ Temporal runtime integration and none is coming: the product pool established this by enumerating `temporalio/contrib` — eleven entries, no `anthropic/`, no `claude/` — while OpenAI, Google ADK, LangGraph and Strands all have one. Temporal's Anthropic surface is *developer tooling*, not runtime. **A hand-rolled `claude_cli` activity is the permanent answer, and this phase should be scoped as such rather than as a stopgap.**

---

## Requirements for completion

1. **The activity heartbeats at a stated cadence**, and what counts as *progress* is defined rather than assumed — a heartbeat that fires on a timer while the run is stalled is worse than none, because it converts a detectable failure into an invisible one.
2. **The transcript is a file and the result carries a reference.** Event history carries references, never payloads. This is simultaneously a correctness constraint and a security control: event history persists in the central Postgres, and repo content does not belong there.
3. **Retry semantics for a non-deterministic producer are ruled**, and the ruling is folded into [Phase 2](phase2_durable_dispatch_identity.md)'s contract rather than written twice.
4. **[§A1](../../standards/temporal/claude-dot-files-addendum.md) is closed in the addendum** — all three of its open bullets, heartbeating, payload limits and retry semantics.
5. **A long run is demonstrated completing under a real worker**, and a worker restart mid-run behaves the way requirement 3's ruling says it should.
6. **Whether a headless invocation is behaviourally indistinguishable from an operator at a terminal is settled, and how that was demonstrated is recorded.** **This requirement stays unchecked** — see § *What this phase does not settle*, which explains why and what it blocks.

---

## Dependencies

**Inside this component:** [Phase 1](phase1_the_starter_control_plane.md) — heartbeating cannot be demonstrated without a server to heartbeat to, and requirement 5 needs a real worker. [Phase 2](phase2_durable_dispatch_identity.md), because requirement 3's ruling lands in that contract and a retried `claude -p` run is exactly the case the identity work exists for.

**Outside this component:** none.

**What this phase unblocks:** [Phase 5](phase5_the_first_dispatch.md). Every parent in the fleet ultimately calls `claude -p`, so the first dispatch cannot run end to end until this activity exists.

---

## What this phase rests on

**Mostly upstream product research, not this component's pool** — stated plainly because it is unusual for a phase here.

| Source | What it supplies |
|---|---|
| `python_sdk_long_activities.md` (product pool) — `Last validated 2026-08-03`, Critic `PASS-WITH-FIXES` | **Closes the heartbeating and payload-limit halves in full.** Definitive, first-party sourced, and its own `Feeds:` line names this exact milestone. Nothing in the 2026-08-19 component cycle adds to it |
| [`raw/durable_dispatch_identity.md`](research/raw/durable_dispatch_identity.md) §4.2, §5.4 | The dispatch row of the recovery table — conversation transcript, machine-local, 30-day default retention, **conditionally** replayable — and the three-legged liveness taxonomy as a *design input* rather than a work item |
| [`../../standards/temporal/claude-dot-files-addendum.md`](../../standards/temporal/claude-dot-files-addendum.md) §A1, §A2 | The three open bullets this phase closes, and the producer-that-can-be-confidently-wrong constraint that shapes requirement 3 |
| First-party Temporal documentation | Heartbeat semantics and blob-size limits, read at plan time — see § *Runtime Verification* |

**Read `python_sdk_long_activities.md` before writing the heartbeat cadence.** It is the paper that already answers requirements 1 and 2, and re-deriving them here would spend a research cycle twice and might reach a different answer the second time.

---

## §Runtime Verification

**Date:** 2026-08-19 · **Host:** `puma-workstation-mint` · **Runtime verified:** the installed Claude Code CLI and Temporal SDK, and the first-party Temporal limits this phase's design turns on. **No Temporal server exists yet** — requirement 5's observations replace this block once [Phase 1](phase1_the_starter_control_plane.md) has landed.

```
$ claude --version
2.1.235 (Claude Code)

$ python3 -m pip show temporalio | head -2
Name: temporalio
Version: 1.27.2

$ python3 --version
Python 3.13.12
```

### The two Temporal limits this phase is built around

| Fact | Source, fetched 2026-08-19 |
|---|---|
| **gRPC** — *"gRPC has a limit of 4 MB for each message received."* | [docs.temporal.io/self-hosted-guide/defaults](https://docs.temporal.io/self-hosted-guide/defaults) |
| **Blob warn** — *"Temporal warns at 256 KB: `Blob size exceeds limit.`"* | same |
| **Blob error** — *"Temporal errors at 2 MB: `ErrBlobSizeExceedsLimit: Blob data size exceeds limit.`"* Applies to workflow context, workflow arguments, activity arguments and their return values | same |
| **Heartbeat Timeout** — *"the maximum time between Activity Heartbeats."* *"If this timeout is reached, the Activity Task fails and a retry occurs if a Retry Policy dictates it."* | [docs.temporal.io/encyclopedia/detecting-activity-failures](https://docs.temporal.io/encyclopedia/detecting-activity-failures) |
| **Heartbeat guidance** — for extended operations, *"a relatively short Heartbeat Timeout and a frequent Heartbeat. That way if a Worker fails it can be handled in a timely manner."* | same |
| **Heartbeat throttling** — the worker throttles automatically: the interval is the smaller of `heartbeatTimeout * 0.8` (when a timeout is set) and the configured throttle bounds. *"Throttling does not apply to the final Heartbeat message in the case of Activity Failure."* | same |

**Two consequences worth stating before anyone writes a cadence.** First, **the SDK already throttles**, so a naive tight loop does not cost what it looks like it costs — the design question is what a heartbeat *means*, not how often to call it. Second, **256 KB is the warning and 2 MB is the hard error**, and a full transcript of a 60-minute run clears both without difficulty. That is not a tuning problem; it is why requirement 2 is a reference and not a payload.

**Re-verify before the build dispatch fires**, and re-run this block against the standing worker for requirement 5.

---

## Implementation steps

- [ ] **Read `python_sdk_long_activities.md` first.** It closes requirements 1 and 2 and is the reason this phase is smaller than it looks.
- [ ] **Re-run § *Runtime Verification* against the installed CLI and SDK**, and refresh it.
- [ ] **Define what a heartbeat MEANS for a `claude -p` run**, before choosing a cadence. A run is emitting `stream-json`; a heartbeat tied to *new output* says something a wall-clock heartbeat does not. Write down which one is being sent and what a reader may conclude from it.
- [ ] **Set the heartbeat timeout deliberately and record the reasoning.** First-party guidance is short timeout, frequent heartbeat; the throttle then does the rest.
- [ ] **Write the transcript to a file and put a reference on the result.** Reuse the run bag rather than inventing a second store — [PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md) already gives every run a folder keyed by `run_id`, and [Phase 2](phase2_durable_dispatch_identity.md) makes that key stable across attempts.
- [ ] **Assert the result payload stays under the blob limits**, with a test rather than a comment. A result that grows past 2 MB fails at the server, late, in a way that reads as an infrastructure fault.
- [ ] **Rule the retry semantics** — an LLM run is not deterministic, so a retry is a *new attempt*, not a replay of the same work. Whether that is safe depends entirely on whether the activity is idempotent, and for anything that pushes commits or opens PRs it is not.
- [ ] **Fold that ruling into [Phase 2](phase2_durable_dispatch_identity.md)'s recovery table** rather than writing a second contract. The dispatch row already exists; this supplies its retry column.
- [ ] **Record the three-legged liveness predicates as fields, and build nothing.** Stalled, looping and stranded are three different states and a driver that keeps going needs to know which one it is in — but the detection layer is [Autonomous Operation](../autonomous-operation/autonomous-operation.md)'s, and building it here builds the thing the port deletes.
- [ ] **Close [§A1](../../standards/temporal/claude-dot-files-addendum.md)** — all three bullets, with the reasoning. The addendum is the one file in that folder that may be edited locally; the rest are vendored MIRROR.
- [ ] **Demonstrate a long run completing under a real worker**, and record the observed heartbeat behaviour in § *Runtime Verification*.
- [ ] **Demonstrate a worker restart mid-run** and record what happened against what requirement 3's ruling predicted. **If they disagree, the ruling is wrong, not the observation.**
- [ ] **Leave requirement 6 unchecked**, with the prose below beside it.

---

## Notes, decisions and gotchas

- **A retry of this activity is a new attempt, not a replay, and that is the whole difficulty.** Temporal's model assumes an activity re-run does the same thing. Ours re-runs a non-deterministic producer against a working tree the first attempt may already have modified. The identity work in [Phase 2](phase2_durable_dispatch_identity.md) makes the *naming* stable; it does not make the *work* idempotent, and nothing can.
- **[§A2](../../standards/temporal/claude-dot-files-addendum.md) applies to every result this activity returns.** Ours is a producer that can be **confidently wrong** — a fabricated citation, an attested-but-unverified pointer, a verdict that does not match its own findings. No upstream pattern defends against this because no upstream producer has the failure mode. The rules that do are already recorded: routing contracts fail safe to the branch requiring a human, verification is by fetch rather than by plausibility, and a run's own summary is a claim *about* its work rather than the work.
- **The payload rule is a security control as much as a correctness one.** Event history persists in the central Postgres. Transcripts, secrets and repo content never go in it — and on a starter node whose secrets are treated as compromised by construction at [Phase 8](roadmap.md), that matters more than usual.
- **Do not reach for a resumption hint in `heartbeat_details` without deciding what it means here.** It is a real Temporal pattern — a retried attempt skips completed prefix work — and it is covered in depth by `python_sdk_long_activities.md`. It also assumes the prefix work was deterministic, which for a `claude -p` run it was not.
- **`--fork-session` is the wrong tool** for the same reason it is in [Phase 2](phase2_durable_dispatch_identity.md): it exists to mint a *new* session id on resume.

---

## What this phase does not settle

**Requirement 6 — whether a headless invocation is behaviourally indistinguishable from an operator at a terminal — has no evidence behind it, and the milestone is open on exactly the half that is the milestone.**

The sprint line disclaims the reading the evidence answers, in its own text: *"Not a permission question; a design one."* The **permission** half is settled and settled well — `anthropic_tos_and_enterprise.md` §1.5 establishes that headless `claude -p` invocation is explicitly sanctioned, an operator's own worker running their own CLI for their own use. **The design half is untouched by that paper and by the 2026-08-19 research cycle.** Nothing in this component's pool or the product pool addresses what makes an invocation behaviourally indistinguishable, or how that would be demonstrated.

**An earlier draft of the component synthesis called the milestone "substantially answered." It corrected itself, and the correction is the useful part** — the permission answer reads like an answer to the design question and is not one.

**What this blocks.** The sprint says this milestone *"gates everything below it"* and *"decides whether the port is viable on a subscription model at all."* Read strictly, that gates this whole component. **This plan does not treat it that way, and says so rather than leaving the divergence silent:** the milestone is placed here, at the phase that first runs `claude -p` from a worker rather than from a shell, because that is where the question becomes concrete and answerable. Every phase before this one is a control plane, an identity contract and an exception hierarchy — none of them depends on the answer.

**It is a research question, not deferred work, and it needs a research cycle rather than a build step.** Naming it here is the placement; the requirement stays unchecked until evidence exists. **Built is not proven**, and a requirement whose evidence cannot exist yet is not checked.
