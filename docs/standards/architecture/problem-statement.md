# Problem Statement

**What this repo is for, and what it is the first iteration of.**

## The problem

Organizations adopting agentic AI face a trade-off that should not exist.

**Per-user tools** — Claude Code and its peers — authenticate with an individual's subscription on that individual's machine. They are economical, they reach private code, and they cannot be orchestrated: nothing coordinates them, nothing survives a crash, and nothing shared accumulates between people.

**Centralized platforms** solve orchestration by moving the work to a server, and pay for it twice: metered per-token billing instead of a flat per-person fee, and credentials that must leave the machine they belong to in order to reach the code.

Neither side supplies all four of the things an organization actually needs — **shared workflow logic**, **subscription-tier economics**, **credentials that stay at the edge**, and **durable orchestration**.

## The narrower gap this repo exists to close

Self-improvement in an agent is a **loop**: produce something, evaluate it, revise. Every implementation that survives past a single session writes something down where the next run can find it.

**The research made the artifacts durable. It did not make the loop durable.** The output survives; the reflection cycle that produced it does not. A run that learns something and dies has learned nothing.

That is the gap. Not "agents should be better" — *the improvement loop itself needs to be a first-class, durable, resumable thing.*

## What is being built

A two-tier system:

- **Server tier** — durable orchestration plus a shared library of reusable workflow modules. Decides what runs next, keeps a written record of how far each run got, and resumes rather than restarts.
- **Edge tier** — a worker on each participant's own machine, authenticated with that person's own subscription. **Credentials never leave the edge.** Multi-tenancy comes from each person authenticating locally, not from a central service holding everyone's keys.

The genuinely novel part is neither tier. It is **the shared workflow library as a first-class artifact** — composable modules that one person writes and another can use without rewriting.

## Where this repo sits

**This repo is iteration one, and coding is the first edge.**

Everything here — the agents, the workflows, the memory model, the improvement loop — is that architecture built for a single participant on their own machines, with the orchestration layer still in bash. It is not a coding tool that might generalize later; **it is the backbone, exercised against the edge that was closest to hand.**

The sequencing follows from that:

| | |
|---|---|
| **Now** | The backbone as a single-operator harness. Workflows decomposed into composable parents and children; memory that outlives a context window; an improvement loop that reads the system's own execution record |
| **Next** | Durable execution — the server tier on a remote host, this machine as an edge running a local worker |
| **Then** | Additional edges. Home automation, industrial automation, robotics, bioinformatics. **The backbone does not change; only the edge does** |

An edge is not a plugin. It is a machine with a capability and a credential, running a worker that speaks the same protocol. Coding is one because it happened to be first.

## What this means for anything built here

Three consequences, and they explain decisions that look over-engineered for a personal config repo:

- **Nothing may assume a single operator.** A shortcut that works because one person runs everything is a shortcut that has to be removed later.
- **Nothing may assume the coding edge.** Machinery that only makes sense for git and PRs belongs at the edge, not the backbone. The test: *would this still make sense if the edge were a robot?*
- **The improvement loop is a feature, not tooling.** It is the thing under study. Treating it as scaffolding is treating the thesis as scaffolding.

## Source

The full statement, the reference architecture, the five design principles, and the evidence are in the research pool this document summarizes:

- [`research/synthesis.md`](research/synthesis.md) — the decision deliverable, rewritten each cycle
- [`research/raw/`](research/raw/) — the pool, one paper per topic
- [`research/topics.md`](research/topics.md) — what has been researched, and what has not

Originally developed as a CSCI-6905.604 research project (2026-07). **That paper is the problem statement; this is its repo-scoped restatement.** Where they disagree, the paper is the source and this file is stale.

## Status

**Not ratified as a standard.** This states the problem and the intent. Binding decisions live in `docs/standards/`; what is actually built and planned lives in [`../../development/roadmap.md`](../../development/roadmap.md).
