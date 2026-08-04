# Problem Statement

## Where this sits — read this first

This repo is **not a product.** It is the **assistant edge** of a larger system, and almost every question about it is unanswerable without that frame.

```
SkyyNet          federation and central planning — places paid work across MDCs
  └─ SkyyCommand    per-MDC local control — owns local services and workloads
       ├─ Jarvis         the assistant edge  ← THIS REPO
       └─ (future edges) building & industrial automation, and others
```

A previous attempt to describe this repo on its own terms failed three times, and the reason was altitude: judged as a standalone product it is one more coding-agent orchestrator in the most crowded category in the industry. Judged as **one edge of a federated fabric**, it is a component with a specific job. The second framing is the true one.

**(stub — deliberately incomplete.)** SkyyNet and SkyyCommand have not had this exercise run against them yet. What follows about them is sketch, not specification, and is here so that work on this repo can orient against the real destination rather than against a subset of it.

## The trade-off that should not exist

Organizations adopting agentic AI are forced to choose between two shapes, and neither one works.

**Per-user tools** — Claude Code and its peers — authenticate with an individual's subscription on that individual's machine. They are economical, they reach private code, and they cannot be orchestrated: nothing coordinates them, nothing survives a crash, and nothing shared accumulates between people.

**Centralized platforms** solve orchestration by moving the work to a server, and pay for it twice: metered per-token billing instead of a flat per-person fee, and credentials that must leave the machine they belong to in order to reach the work.

Neither side supplies all four of the things an organization actually needs — **shared workflow logic**, **subscription-tier economics**, **credentials that stay at the edge**, and **durable orchestration**.

## What is known, and what we intend to do with it

Four capabilities make an autonomous agent system durable and capable. **None of them is ours, none is novel, and the field is converging on all four.** They are the recipe:

**1. Durable execution.** Retries, resumption, and a written record of how far a run got — so a crash resumes rather than restarts.

**2. Layered self-improvement over durable artifacts.** Not one agent critiquing itself, but distinct actors at distinct layers — one that authors, one that judges with no stake in the work, one that dispositions — each reading and writing artifacts the others can see. The layering is what makes the improvement real rather than an agent agreeing with itself.

**3. Typed memory between steps.** Results a step leaves behind that the *next* step reads **in code**, with no model in the loop. This is what turns a sequence into a program: a parent branches on what a child concluded because the conclusion is a value, not prose.

**4. High-level loops over persisted state.** Above the parents, a driver that chooses what runs next — if/then/else over the results of entire workflows, running unattended until an exit condition it can actually observe.

**The intent is not to invent this recipe. It is to execute it better than anyone else, and to acquire the lessons rather than re-learn them.** Competing projects have paid for hard-won knowledge in production; where their work is open, that knowledge is free to us. Mining it deliberately is the strategy, not an admission.

## Where we actually differ

Three differences survive first-party inspection of the nearest comparable systems. They are stated with their evidence status, because a differentiator nobody has verified is a hope.

**1. The backbone is domain-general; the edge is what changes.** Comparable systems are built for code — their verification vocabulary is *tests pass, lint clean, types correct*. Here, code is one edge among several, and machinery that only makes sense for git and PRs belongs at the edge rather than the backbone. *Evidence: confirmed absent from the nearest neighbor, three independent ways.*

**2. Edges are dedicated and non-fungible.** The common model is a central queue where workers advertise a *role* and claim from a shared pool, with contention and force-claim as real conditions. Ours inverts it: **each edge is dedicated, sees only its own work, and no edge can claim another's.** This is not a smaller version of the same design — it follows from a different theory of what a worker is. Role-pull assumes fungible workers distinguished by a label. An edge is a machine with a physical capability and its own credential; a robotics edge cannot take a bioinformatics task because it *is* a different thing, not a differently-labeled one. *Evidence: confirmed different. Ours is designed, not yet built.*

**3. The first edge builds the others, then operates inside them.** See below. *Evidence: no trace of anything comparable.*

**Not differentiators, stated plainly so nobody re-litigates them:** durable execution, checkpoint/resume, completion contracts, typed refusal, and Kubernetes-native deployment all exist in shipping competitors today. Several are ahead of us. Claiming them would be false and would discredit the claims that are true.

## The nearest neighbor

**[`bernstein`](https://github.com/sipyourdrink-ltd/bernstein)** (Apache-2.0) is the closest comparable system: a deterministic orchestrator for CLI coding agents, with no model in the coordination loop, per-task git worktrees, checkpoint/resume, a Kubernetes operator with CRDs, mTLS between workers, and typed completion contracts. It is a real, actively-released product and it is ahead of this repo on every axis except the three above.

We name it deliberately. A problem statement that does not know its nearest neighbor is not a problem statement. Its designs — CRD-modeled runs, typed refusal, checkpointed retries — are reference material we intend to learn from and adapt onto our own durability substrate rather than copy wholesale, because our durability comes from Temporal and its does not.

## Affordability is the enabler

The work runs at the edge, on each participant's own subscription.

Metered per-token billing makes experimentation expensive in proportion to curiosity. An autonomous loop that runs for hours, retries, branches, and occasionally goes nowhere is precisely the thing you cannot afford to explore when every turn has a price — so exploring it is restricted to organizations who can absorb the bill. **The interesting experiments are the wasteful ones**, and metered billing prices those out first.

A flat per-person subscription inverts that. A long-running loop costs the same as a short one; being wrong costs nothing but time. **That access is the point, not a cost optimization.**

## The edges

An edge is not a plugin. **It is a machine with a capability and a credential, running a worker that speaks the backbone's protocol.**

### Jarvis — the assistant edge (this repo)

**Jarvis is an assistant.** Coding is its current claim to fame because coding is what builds SkyyCommand — but the coding capability is the *first* function, not the definition.

**(stub.)** Later functions are expected to be provider-shaped: the helpers available differ by which subscription backs the edge — Claude Code and Codex expose different capabilities, different session models, and different limits. The backbone should not care which; the edge should.

**Why this edge is first, and permanent.** It is the edge that builds the others, and then works inside them.

- **It builds them.** Every new edge needs a worker, activities, and workflow modules. That is code, written by the edge that already exists — so each new edge costs less to stand up than the one before it.
- **It works inside them, with a human in the loop.** Once an edge exists, the operator running it is not left alone with it. The assistant is present *in* that edge — reading its state, diagnosing failures, proposing changes — the same way it is present in a repository today.

That second role is easy to miss and it is where the compounding comes from. A conventional platform gets harder to operate as it grows, because each new domain is one more thing an operator must learn to run unaided. Here, **every new edge arrives with an assistant already fluent in the backbone that runs it.**

### Building & industrial automation — the next edge

**(stub.)** The name is provisional and deliberately not "automation," which to a technical audience means CI rather than physical plant. This edge covers real-world control: buildings, HVAC, access, industrial equipment.

It is the natural second edge because **SkyyCommand already runs Home Assistant on the MDC** — the domain is present, the hardware exists, and the edge is not hypothetical. Jarvis dogfoods it twice over: as the assistant that helps *code* it, and as the operator interface *to* it.

Beyond it: robotics, bioinformatics, and whatever else has a machine, a credential, and a job. **The backbone does not change; only the edge does.**

## What this means for anything built here

Three consequences, and they explain decisions that look over-engineered for a personal config repo:

- **Nothing may assume a single operator.** A shortcut that works because one person runs everything is a shortcut that has to be removed later.
- **Nothing may assume the coding edge.** The test: *would this still make sense if the edge were a building controller?*
- **The improvement loop is a feature, not tooling.** It is the thing under study. Treating it as scaffolding is treating the thesis as scaffolding.

## Status and evidence

**Not ratified as a standard.** This states the problem and the intent. Binding decisions live in `docs/standards/`; what is built and planned lives in [`../../development/roadmap.md`](../../development/roadmap.md).

Supporting evidence is in the research pool beside this file: [`research/synthesis.md`](research/synthesis.md) rolled up, [`research/raw/`](research/raw/) for the papers. **[`research/raw/combination_prior_art.md`](research/raw/combination_prior_art.md) and [`research/raw/case_against.md`](research/raw/case_against.md) are the two that forced this document's rewrite** — both argue against the position this repo held, and both were commissioned to do exactly that. Originally developed as a CSCI-6905.604 research project (2026-07).
