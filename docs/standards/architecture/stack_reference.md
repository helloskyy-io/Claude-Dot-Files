# Stack Reference

What we run on, and what we deliberately do not.

> **⚠ SEEDED, NOT COMPLETE.** This file currently holds one settled decision, moved here from `system-overview.md` so it is not lost. **The full stack reference — its sections, its terminology, and what a good one contains — awaits a research pass**, after which a standard defines the shape and `plan-tech-stack` maintains the content.
>
> Do not treat an absence here as a decision. A component missing from this file has not been ruled out; it has not been written down yet.

## Orchestration

**Temporal, SELF-HOSTED. Temporal Cloud is not on the table.** Decided 2026-07-12.

| | |
|---|---|
| **Two servers, never combined** | one for infrastructure, one for the AI edge (Jarvis). An agent-facing control plane must not share a server with the one that runs the datacentre |
| **HA on k3s** | not serverless. AWS Lambda's hard 15-minute activity ceiling cannot host a `claude -p` run, which takes 10–60 minutes |
| **Workers** | systemd, on the machine holding the repo and the credential |
| **Owned by** | SkyyCommand. This repo is an edge: it consumes the decision, it does not make it |

**Why this is written down at all.** The decision lived only in conversation, and a research cycle then spent effort pricing Temporal Cloud and produced two action candidates against a deployment ruled out three weeks earlier. **A settled decision that is not written down gets re-derived wrongly by every tool that reads the docs.**

**Consequences that are not obvious**, and are the reason this belongs in a stack reference rather than a sentence somewhere:

- Cloud's **billable-Action pricing does not apply** — heartbeat frequency is a persistence-write question on our own cluster, not a cost one
- **Serverless worker patterns are unavailable**, so any design assuming them is out of scope
- **Shard capacity is a build-time one-way door we own**, fixed at cluster creation and not adjustable later, rather than a vendor default

The binding standard belongs upstream in `MDC-Master-Planning` alongside the other Temporal standards and vendors down like them. **This is the consuming edge's copy, not the authority.**

## What we do NOT use

*(To be filled by the research pass. This section exists because it is the one that stops a later run re-proposing something already rejected — the same failure the Cloud candidates demonstrate.)*

- **Temporal Cloud** — see above
- **Serverless workers (AWS Lambda)** — 15-minute activity ceiling against a 10–60 minute workload

## Related

- [`architectural_standard.md`](architectural_standard.md) — vocabulary and cross-cutting rules
- [`../temporal/`](../temporal/) — the vendored Temporal standards (MIRROR)
- [`../temporal/claude-dot-files-addendum.md`](../temporal/claude-dot-files-addendum.md) — what is genuinely ours
