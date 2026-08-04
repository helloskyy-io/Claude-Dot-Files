# Problem Statement

## The trade-off that should not exist

Organizations adopting agentic AI are forced to choose between two shapes, and neither one works.

**Per-user tools** — Claude Code and its peers — authenticate with an individual's subscription on that individual's machine. They are economical, they reach private code, and they cannot be orchestrated: nothing coordinates them, nothing survives a crash, and nothing shared accumulates between people.

**Centralized platforms** solve orchestration by moving the work to a server, and pay for it twice: metered per-token billing instead of a flat per-person fee, and credentials that must leave the machine they belong to in order to reach the work.

Neither side supplies all four of the things an organization actually needs — **shared workflow logic**, **subscription-tier economics**, **credentials that stay at the edge**, and **durable orchestration**.

## The gap underneath it

Self-improvement in an agent is a **loop**: produce something, evaluate it, revise. Every implementation that survives past a single session writes something down where the next run can find it.

**The industry made the artifacts durable. It did not make the loop durable.** The output survives; the reflection cycle that produced it does not. A run that learns something and then dies has learned nothing.

## What we are combining, and why it is novel

Four things exist independently today. Each is well understood on its own. **Nobody has put them together**, and the combination is the contribution:

**1. Durable execution for long-running processes.** Retries, resumption, and a written record of how far a run got — so a crash resumes rather than restarts. Mature technology, borrowed rather than invented.

**2. Layered self-improvement that exercises durable artifacts.** Not one agent critiquing itself, but distinct actors at distinct layers — one that authors, one that judges with no stake in the work, one that dispositions — each reading and writing artifacts the others can see. The layering is what makes the improvement real rather than an agent agreeing with itself.

**3. Memory management for persistent communication between steps.** Typed results a step leaves behind that the *next* step reads **in code**, with no model in the loop. This is the piece that turns a sequence into a program: a parent can branch on what a child concluded because the conclusion is a value, not prose.

**4. High-level loops that orchestrate many parent workflows.** Above the parents, a driver that chooses what runs next from persisted state — if/then/else over the results of entire workflows, running unattended until an exit condition it can actually observe.

Each is ordinary. **Together they make autonomous long-running processes something you can build and experiment with** — because the loop survives failure, the layers keep it honest, the memory makes branching possible, and the driver strings it all together.

## Affordability is not a footnote — it is the enabler

The fourth element is what makes the other three reachable: **the work runs at the edge, on each participant's own subscription.**

Metered per-token billing makes experimentation expensive in proportion to curiosity. An autonomous loop that runs for hours, retries, branches, and occasionally goes nowhere is precisely the thing you cannot afford to explore when every turn has a price — so exploring it is restricted to organizations who can absorb the bill. **The interesting experiments are the wasteful ones**, and metered billing prices those out first.

A flat per-person subscription inverts that. A long-running loop costs the same as a short one. Being wrong costs nothing but time. **This makes experimenting with loop logic and autonomous long-running processes trivial rather than a privilege of the well-funded** — and that access is the point, not a cost optimization.

## What is being built

A two-tier system, shaped by the above:

- **Server tier** — durable orchestration plus a shared library of reusable workflow modules. Decides what runs next, records how far each run got, resumes rather than restarts. **Runs no agent compute.**
- **Edge tier** — a worker on each participant's own machine, authenticated with that person's own subscription. **Credentials never leave the edge.** Multi-tenancy comes from everyone authenticating locally, not from a central service holding everyone's keys.

The genuinely novel artifact is neither tier: it is **the shared workflow library** — composable modules one person writes and another can use without rewriting.

## Where this repo sits

**This repo is iteration one, and coding is the first edge.**

Everything here — the agents, the workflows, the memory model, the improvement loop — is that architecture built for a single participant, with orchestration still in bash. It is not a coding tool that might generalize later; **it is the backbone, exercised against the edge that was closest to hand.**

| | |
|---|---|
| **Now** | The backbone as a single-operator harness: workflows decomposed into composable parents and children, memory that outlives a context window, an improvement loop that reads the system's own execution record |
| **Next** | Durable execution — the server tier on a remote host, this machine as an edge running a local worker |
| **Then** | Additional edges: home automation, industrial automation, robotics, bioinformatics. **The backbone does not change; only the edge does** |

An edge is not a plugin. It is a machine with a capability and a credential, running a worker that speaks the same protocol. Coding is one because it happened to be first.

## What this means for anything built here

Three consequences, and they explain decisions that look over-engineered for a personal config repo:

- **Nothing may assume a single operator.** A shortcut that works because one person runs everything is a shortcut that has to be removed later.
- **Nothing may assume the coding edge.** Machinery that only makes sense for git and PRs belongs at the edge, not the backbone. The test: *would this still make sense if the edge were a robot?*
- **The improvement loop is a feature, not tooling.** It is the thing under study. Treating it as scaffolding is treating the thesis as scaffolding.

## Status and evidence

**Not ratified as a standard.** This states the problem and the intent. Binding decisions live in `docs/standards/`; what is actually built and planned lives in [`../../development/roadmap.md`](../../development/roadmap.md).

The supporting evidence — the reference architecture, the design principles, the production cases, and the convergent adoption record — is in the research pool beside this file: [`research/synthesis.md`](research/synthesis.md) for the rolled-up version, [`research/raw/`](research/raw/) for the papers. Originally developed as a CSCI-6905.604 research project (2026-07).
