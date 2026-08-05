# System Overview

What is built, and how the pieces fit. **The WHY is [`problem-statement.md`](problem-statement.md); the rules are `docs/standards/`; what is planned is [`../../development/roadmap.md`](../../development/roadmap.md).** This file is the map, not the argument.

## What this is

**Jarvis — the assistant edge**, and iteration one of the backbone described in the problem statement. Coding is its first function, not its definition; it sits under SkyyCommand, which sits under SkyyNet. A single operator, orchestration in bash, everything running on that operator's own machines under their own subscription.

No server, no daemon, no framework. Workflows are shell scripts that invoke `claude -p` in isolated git worktrees; agents, skills and rules are markdown; memory is GitHub.

## Layers

```
scripts/workflows/
  *.sh              PARENTS and monoliths — you dispatch these
  children/         CHILD WORKFLOWS — a parent invokes these; shared, not owned
  activities/       EXTERNAL I/O — workflow-agnostic, idempotent, never inlined in a parent
  common/           SHARED TYPES AND CONTENT — no I/O, nothing executes

config/
  agents/           subagents dispatched by workflows; one distinct lens each
  skills/           methodology, loaded on demand when context matches
  rules/            always-loaded global instructions
  hooks/            PreToolUse safety, Stop notification
```

The organizing axis is **who invokes it**. That single question places every file.

`config/` is symlinked into `~/.claude/` by `install.sh`, so authored config is identical on every machine while credentials, sessions and per-project state stay local.

## Composition

A parent calls no model. It decides *if*, *when* and *what* to call, and holds no process code.

```
revision.sh
  ├─ children/revision-draft.sh    writes the change, opens an UNREVIEWED PR
  ├─ children/revision-refine.sh   FRESH context: fidelity, review, corrections
  └─ children/review-pr.sh         decide-only: MERGE | HOLD + a runway
        └─ HOLD(redispatch) → one bounded loop-back, then stop
```

`revision-minor.sh` runs the identical sequence with lighter children. The handoff between runs is git plus the original task — nothing else crosses.

**The completion contract is the interface.** Each child declares a pattern its final output must contain, so `exit 0` provably means *finished*. A parent needs that plus one stable identifier on the final line, which is why composition here needs no framework.

## Memory

No state files, no bookmarks. **Open is the to-do bit.**

| Surface | Holds | Lifecycle |
|---|---|---|
| PR threads | change-outcomes, decision logs, disposition rulings | closes at merge |
| GitHub Issues | no-change outcomes — deferred work, planning STOPs | filed → ruled → closed |
| Standup tracker | continuity — operating state, next moves | never closes; pruned |

`/standup` reads all three into a morning brief. Every reviewing actor verifies claims against the artifact rather than the account of it, and verifies a pointer by fetching it.

## The improvement loop

Two machine-produced evidence sources, no human gathering data:

- **Run logs** — every dispatch writes JSONL; `review-runs.sh` analyses a window across repos.
- **Self-disclosure** — every workflow posts a decision log and tooling suggestions to its PR; `review-pr` mines them.

Findings reach an explicit ship / defer / reject in an append-only log, **ruled by a human**. The system observes itself and proposes; it does not modify itself.

## Safety

Autonomous runs pass `--dangerously-skip-permissions`, so the `PreToolUse` hook is **the only control operating during a run** — worktree isolation only bounds blast radius, PR review is after the fact. `block-dangerous.sh` fails closed. Nothing reaches `main` except through a PR.

## Where the seams are

Deliberate boundaries, each with a reason:

| Seam | Why |
|---|---|
| author ≠ judge | the author of a change defends it; no wording fixes that |
| parent ≠ child | every boundary is a retry/resume point |
| activity ≠ workflow | a workflow doing network I/O cannot replay |
| decide ≠ act | `review-pr` rules; a human or parent fires |
| surface ≠ ratify | agents propose standards; humans write them |

## What is not built

Durable execution, the server tier, additional edges, and typed handoff between runs — a parent still routes on a parsed token rather than a structured result. See the roadmap.

## Deployment target — settled, and stated here because tools read this file

**Temporal is SELF-HOSTED. Temporal Cloud is not on the table.** Decided 2026-07-12.

| | |
|---|---|
| **Two servers, never combined** | one for infrastructure, one for the AI edge (Jarvis). An agent-facing control plane must not share a server with the one that runs the datacentre |
| **HA on k3s** | not serverless. AWS Lambda's hard 15-minute activity ceiling cannot host a `claude -p` run, which takes 10–60 minutes |
| **Workers** | systemd on the machine holding the repo and the credential |
| **Owned by** | SkyyCommand. This repo is an edge and consumes the decision; it does not make it |

**Stated here for a specific reason.** This decision lived only in conversation, and a research cycle then spent effort pricing Temporal Cloud and produced two action candidates against a deployment ruled out three weeks earlier. **A settled decision that is not written down gets re-derived wrongly by every tool that reads the docs** — and consequences follow from it that are not obvious: Cloud's billable-Action pricing does not apply, serverless worker patterns are unavailable, and shard capacity becomes a build-time one-way door we own rather than a vendor default.

The binding standard belongs upstream in `MDC-Master-Planning` alongside the other Temporal standards, and vendors down like them. This paragraph is the consuming edge's copy, not the authority.

## Related

- [`problem-statement.md`](problem-statement.md) — the problem and the thesis
- [`research/`](research/) — the evidence, non-binding
- [`../workflow-scripts.md`](../workflow-scripts.md) — the binding rules for everything above
- [`../../guide/operations.md`](../../guide/operations.md) — how to run it
- [`../../guide/workflows.md`](../../guide/workflows.md) — workflow architecture in depth
