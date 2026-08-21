# Problem Statement

## Where this sits: read this first

This repo is **not a product.** It is the **assistant edge** of a larger system, and almost every question about it is unanswerable without that frame.

```
SkyyNet                  federation and central control. Self-healing k8s;
  │                      places paid work across MDCs
  └─ SkyyCommand (MDC)   a Micro-Data-Center. Orchestrates hosts, VMs and k8s
       │                 clusters; owns local services and workloads
       ├─ Assistant edge     ← THIS REPO. Coding, and general assistance
       ├─ (future edge)      control of the self-healing k8s infrastructure
       └─ (future edge)      the physical world: building and industrial
                             automation, home automation, robotics
```

**What is actually deployed today**, so the diagram is not read as aspiration:

- **SkyyNet** is the logical layer where this repo's central server lives. Today it is Django, Temporal and Argo, and nothing more.
- **Two MDCs are deployed.** Status: partially capable of complex orchestration over Temporal durable execution.
- **Edges deploy adjacent to what they control**, and the assistant edge deploys **by default alongside any secondary edge.** That is a deployment rule, not an aspiration, and it is why the assistant is both the thing that builds the other edges and the thing present inside them.

Three earlier drafts of this document tried to describe the repo on its own in its current state, and all three fell apart. The problem was not the writing, it was the frame.

Described by itself in its current state, this is one more tool for coordinating AI coding agents. That is the most crowded category in the industry right now, and there is very little to say about it that a dozen other projects could not also say.

Described as **the primary edge that every future edge depends on, and as the self-learning central brain for federated control**, the questions that actually matter have answers: what this repo has to do, what it is allowed to assume, and what it can leave to another layer. The second frame is the accurate one, and the rest of this document uses it.

**Deliberately incomplete.** SkyyNet and SkyyCommand (MDC) have not had this exercise run against them, because their AI-powered edge does not exist yet. What follows about them is conceptual, not their specification, and is here so that work on this repo can orient against the real destination rather than against a smaller subset of it. **The platform is live; the edge for it is not.**

## The trade-off that should not exist

Organizations adopting agentic AI are forced to choose between two shapes, and neither one works.

**Per-user tools**, Claude Code, Codex and their peers, authenticate with an individual's subscription on that individual's machine. They are very economical, they reach private code, and they cannot be orchestrated: nothing coordinates them, nothing survives a crash, and nothing shared accumulates between people.

**Centralized platforms** solve orchestration by moving the work to a server, and pay for it twice: metered per-token billing, which Anthropic's own published multiplier puts at **3 to 10 times** the token cost of interactive use for agentic workloads, against a flat per-person fee, and credentials that must leave the machine they belong to in order to reach the work.

Neither side supplies all five of the things an organization actually needs: **shared, managed workflow logic**, **subscription-tier pricing**, **credentials that stay at the edge**, **durable orchestration**, and **user-level customization**.

## What is known, and what we intend to do with it

Four capabilities make an autonomous agent system durable and capable. **None of them is ours by design, none is novel, and the larger field of agentic AI is converging on all four.**

They become the recipe:

**1. Durable execution.** Retries, resumption, and a written record of how far a run got, so a crash resumes from the same step rather than restarts.

**2. Layered self-improvement over durable artifacts provided by a persistent memory protocol.** Not one agent critiquing itself, but distinct actors at distinct layers: one that authors, one that judges with no stake in the work, and one that dispositions, each reading and writing artifacts the others can see. The layering is what makes the improvement real rather than an agent agreeing with itself.

**3. Typed memory between steps.** The results a step leaves behind are read by the next step **in code**, with no model in the loop. This is what turns a sequence into a program: a parent branches on what a child concluded because the conclusion is a value, not prose. The persistent memory protocol allows each step to complete separately, which is what enables durable execution to take the form of building-block parent and child workflows that seamlessly mix code-based and AI-based steps.

**4. High-level loops over persisted state.** Above the parents, a driver that chooses what runs next, triggered by a schedule, an input, a chat message or an API call: if/then/else over the results of entire long-running workflows daisy-chained together, running unattended until an exit condition it can actually observe. The full stack is activities, then children, then parents, then the high-level loop above them.

**The intent is not to invent this recipe. It is to derive it through research, keep progressing it, and execute it better than anyone else, acquiring the lessons rather than re-learning them.** Competing projects have paid for hard-won knowledge in production, and where their work is open, that knowledge is free to us. Mining it deliberately is the strategy, not an admission, and assembling what is mined in new and creative ways is what continuous process improvement is for.

## Where we actually differ

Four things about this project look genuinely different from the closest systems we could find. We checked each one against those systems directly, reading their own documentation and code rather than anyone's summary of them. **They are listed strongest first.**

Each one also says how well it has been checked, because **a difference nobody has verified is a hope, not a difference.** We commissioned research whose job was to knock these claims down, and it worked: two of the four came back weaker than we had written them, and were rewritten or replaced.

**1. The credential cannot be handed out, so the shape of the system is forced rather than chosen. The shape itself is not new.** Both halves have to be stated together, or the claim collapses in one direction or the other.

A Claude subscription credential is minted by Anthropic, for one person. Nothing inside this system can issue one, shrink one down to a limited version, or hand a copy to a server to use on someone's behalf, and the terms forbid sharing it in any case. That is what **unmintable** means: we are not the authority that issues this credential, so we can never hand it out.

Everything else follows. If the backbone cannot hold a participant's credential, it cannot run their model work. So the work has to run where the credential already lives, on that person's own machine. **The backbone sends the job, never the key.**

**One choice sits upstream of all of this.** An Anthropic API key *would* be mintable, delegatable and scopable, exactly like every system named below, and this entire constraint would disappear. What disappears with it is the pricing, which is argued in [Affordability is the enabler](#affordability-is-the-enabler). So the full chain is that affordability forces the credential, and the credential forces the topology. Only the second link is a differentiator; the first is a decision, and it is defended rather than assumed.

**The topology is not an invention.** Three administratively isolated trust domains exchanging only public key material (so a foreign domain can *validate* identities it cannot *issue*) is **SPIFFE Federation with different nouns**. Presenting it as new would not survive first contact with a reviewer who knows SPIFFE, and the dispatcher-without-target-credential property ships at mass scale in CI→cloud OIDC.

**What no surveyed model has is our constraint.** SPIFFE, OIDC federation, Vault, Kubernetes and every cloud workload-identity product all assume the edge credential is **mintable by an authority inside one of the tiers**. That assumption *is* their mechanism. Ours is a per-person consumer subscription minted by a fourth party: the edge cannot attenuate it, cannot delegate it, cannot present proof-of-possession for it on the backbone's behalf, and is contractually forbidden from sharing it.

**So the three-tier split is not a design preference we could trade away. It is the only shape that credential permits**, and a competitor cannot adopt it without acquiring the same constraint.

The tiers:

| Tier | What it is | What it may do |
|---|---|---|
| **Edge** | wherever the work actually executes | holds its own credential, which never leaves it |
| **MDC** | the local trusted network | runs local services and workloads: secure, but one operator's domain |
| **Federated** | SkyyNet, across MDCs and operators | deliberately limited: sends work over the trunk, holds no edge credential |

**An edge is a role, not a location.** It is wherever the work is actually being done, and that can be a personal laptop, a machine on a local trusted network, a private cloud, or a worker sitting inside the federated tier itself. What makes something an edge is that it holds its own credential and executes with it, not where it happens to be racked.

**This is why centrally managed agentic AI is still possible here.** The control plane sends instructions; a worker at the edge executes them. Nothing in that requires the centre to hold anyone else's credential, which is the term this design has to satisfy. What is centralized is the workflow logic, the scheduling and the record of what happened, and all three are ours to manage.

Distinct operators in distinct trust domains is not a harder version of what exists: **it is outside the closest system's shipped scope, by its own documentation.** *Evidence: first-party, current.*

**2. Work is bound to a machine by identity, and no scheduling label can move it.**

In an ordinary orchestration system you choose which machine runs a job by labelling machines and asking for a label: send this one to a box tagged `gpu`. Any box carrying that tag will do, because the boxes are interchangeable.

An earlier version of this claim said that was our difference: everyone else treats workers as interchangeable, we bind work to specific hardware. **Research knocked that down.** Routing work to particular physical machines by label is ordinary infrastructure. Kubernetes does it, Slurm does it, and Temporal's own documentation describes giving GPU boxes and non-GPU boxes separate queues. The nearest comparable system advertises `gpu_available` the same way. Hardware-bound workers are unusual only inside *agent orchestration*, which is a much smaller claim than the one we were making.

What survived is narrower and it holds. **A label can say what a machine has. No label can let one machine log in as a different subscriber.** Two machines carrying identical labels are still not interchangeable here, because each one can only authenticate as itself. That is an identity fact, not a scheduling preference, and nothing in the scheduler can override it.

So this is the affordability argument again in another form: **work runs where the subscription lives, because that is the only place that can pay for it.** *Evidence: confirmed. Designed, but not yet built.*

**3. The first edge builds the others, then operates inside them.** See below. *Evidence: no trace of anything comparable.*

**4. The backbone is built for any kind of work, while comparable systems are sold for writing code.** This is the weakest of the four, and direct inspection narrowed it.

*Domain-general* means the orchestration machinery does not care what the work is. The same machinery that runs a coding job should run a building-control job, an infrastructure job or a research job, because nothing inside it assumes software.

We expected the comparable systems to be coding-only underneath. **They are not.** The nearest one already handles five kinds of work: research, browsing, data, operations and coding. Each kind hands back its result in one fixed shape, so the layer above does not need to know which kind it asked for.

The telling part is how the non-coding work gets checked. A coding system verifies by running the tests, which is a trick that only works on code. That system checks a research result by hashing the source again and confirming the quoted passage is still there, and a browsing result by keeping the page bytes and matching them by hash. **Those are real verification methods for work that is not code**, and having them is what makes the generalisation genuine rather than a label.

So *"built only for code"* is false where it counts, at the point where work is handed off and results come back.

**What is left of our claim.** Their website, their marketing and every example they publish are about writing software. So they built an engine that can run anything, and they still sell a coding tool. That is the whole of the difference now: not what the machinery is capable of, but what the product is aimed at.

*How this was checked: we read their own materials directly. The claim is weaker than earlier versions of this document stated.*

**That narrowing is worth more as reference material than as a differentiator**: the domain-general result contract we expected to invent has a shipped, documented shape we can read.

**Not differentiators, stated plainly so nobody argues them again.** Durable execution, checkpoint and resume, completion contracts, typed refusal, Kubernetes-native deployment, and **authenticating at the edge on a personal subscription** all exist in products shipping today. The last of those has precedent in projects far larger than this one, the biggest at roughly 385,000 stars, where credentials at the edge ship more literally than we state it. Several of them are further along than ours. Claiming any of them would be false, and it would discredit the claims that are true.

**What is ours is the assembly, and what the assembly is for.** Every ingredient above can be had somewhere, so we commissioned research to find out whether the recipe itself had already been built. The nearest system matched the four elements one by one. **The honest reading of that result is the one the paper itself gives: matching element by element may be the wrong test.** A system can satisfy every predicate on a list and still be a different thing. Take any recipe, generalise its ingredients far enough, and you will find it somewhere else.

**And the same paper names what it could not find: every candidate it turned up is a coding orchestrator.** That is the distance that matters. This is not a harness for writing software. It is the assistant edge of a federated control system whose other edges run infrastructure and, eventually, physical plant. The nearest comparable system decomposes one coding goal across worktrees and merges the result. Nothing in that sweep is aimed at what this is aimed at, and no amount of predicate-matching closes that gap.

So both things hold, and the order of them matters. **The generalised stack is not unique and we do not claim it. The assembly is ours, the constraint it runs under is ours, and the system being built out of it is not competing with anything named in this section.**

*How this was checked: [`research/raw/combination_prior_art.md`](research/raw/combination_prior_art.md), commissioned to break the claim. It found the four elements built elsewhere and says in its own honest-boundary analysis that the element test may not be the right one. Documentation-level confidence; nothing was executed.*

**If the combination were not the point, there would be no reason to build this at all.** The ingredients are free to anyone who reads. Assembling them under a constraint nobody else carries, and improving the assembly continuously, is the work.

**Where claim #2 places the work, and the two usages it has to cover.** The 2026-08-07 ruling settled this. It is stated here in the two forms the system is intended to be used in, because only the first of them exists today.

**1. An edge initiates its own work and runs it itself.** This is what is built. A dispatch runs against the initiating machine's working tree, its credential and its logs. No other machine holds that state, so no other machine can take responsibility for the work. The parent workflow is a process on that same machine, holding the loop counter, the worktree path and the routing, so handing a child elsewhere would mean distributing the parent, which is a different architecture nobody has proposed.

**The cost is real and accepted:** if the initiating machine is off, its work does not run. That is the definition of an edge, not a defect in the routing.

**2. Central command initiates work that runs on other edges.** This is intended, and not built. A control plane sends one workflow to a named edge, or the same workflow to every edge carrying a given tag. **The credential still never moves.** Each target authenticates as itself, executes against its own working tree, and writes its own logs. What the control plane sends is a name and an instruction, never state and never a key, so nothing about this weakens claim #1. Central command is itself an edge as well as a control plane, so it also runs work locally like any other participant.

**Fan-out is where this needs layered safety, and that is a precondition rather than a detail.** One instruction reaching many machines at once has a different blast radius from one machine acting on its own, and the safety layers have to exist before the capability does.

**Stated precisely enough to cover both usages:** work runs on a machine that holds the credential and the state that work needs. Today that is always the machine that initiated it, because there is no control plane yet to say otherwise.

**The one alternative worth recording, so it is not re-proposed:** keep the credential still and proxy the model call back to it, letting work run anywhere. A shipping product does exactly this, and **excludes CLI runtimes by name**, `claude-cli` among them, which is precisely our runtime. The pattern generalises to API-keyed work and not to `claude -p` on a subscription.

Revisit only if a concrete case appears that this rule serves badly. None exists today.

## The nearest neighbours

**Two systems hold the title, on different axes, and naming only one of them distorts the comparison.** A problem statement that does not know what it is closest to is not a problem statement.

| | Nearest by | Why |
|---|---|---|
| **`bernstein`** | **architecture** | deterministic orchestration, worktree isolation, typed contracts, and it explicitly *refuses* the orchestrator role we are building, listing "agent-hierarchy frameworks" and "heavy orchestration layers" among its published non-goals |
| **`OpenClaw`** | **thesis, and adoption** | credential at the edge, domain-general assistant, your own machines, a supervised long-lived process. 385,334 stars |

**[`bernstein`](https://github.com/sipyourdrink-ltd/bernstein)** (Apache-2.0) is a deterministic orchestrator for CLI coding agents: no model in the coordination loop, per-task git worktrees, checkpoint and resume, a Kubernetes operator with CRDs, mTLS between workers, and typed completion contracts. It is a real, actively released product, and on everything except the differences named above it is ahead of this repo. Its designs, CRD-modeled runs, typed refusal and checkpointed retries, are reference material we intend to learn from and adapt onto our own durability substrate rather than copy wholesale, because our durability comes from Temporal and its does not.

**`OpenClaw`** runs on your own machines, holds the credential at the edge, and is deliberately not limited to software. It is not a durable orchestrator, which is where we part company, but it is the system that shows the thesis is not exotic. 385,334 stars is a large number of people who wanted exactly this arrangement.

**A reader who only knows `bernstein` will over-rate differentiators #1 and #4.** OpenClaw is the harder comparison for the *idea*; bernstein is the harder comparison for the *build*.

## Affordability is the enabler

The work runs at the edge, on each participant's own subscription.

Metered per-token billing makes experimentation expensive in proportion to curiosity. An autonomous loop that runs for hours, retries, branches, and occasionally goes nowhere is precisely the thing you cannot afford to explore when every turn has a price, so exploring it is restricted to organizations who can absorb the bill. **The interesting experiments are the wasteful ones**, and metered billing prices those out first.

A flat per-person subscription inverts that. A long-running loop costs the same as a short one; being wrong costs nothing but time. **That access is the point, not a cost optimization.**

### This differentiator depends on a pricing position, and states so

**It is true today.** `claude -p` draws from the subscription, and this fleet's own run logs confirm it operationally: `rate_limit_info` returns a five-hour window with no credit balance.

**It rests on a change that was announced and deferred, not abandoned.** On 2026-05-14 Anthropic announced that Agent SDK **and `claude -p`** usage would leave subscription pools on 2026-06-15, moving to a monthly dollar credit at standard API rates with no rollover, **$200/month at Max 20×**. That change was **paused** on 2026-06-15. Third-party agents had been blocked outright on 2026-04-04 and reinstated in May under the same mechanism. Evidence: [`research/raw/anthropic_tos_and_enterprise.md`](research/raw/anthropic_tos_and_enterprise.md) §9.

**What resuming would cost us, in measured numbers.** One research cycle cost **$78** in API-equivalent; another **$108**. A $200 monthly allocation covers roughly **two cycles** before any build or review work. And the usage pattern Anthropic named as its reason, multi-hour autonomous runs with heavy sub-agent fan-out, is exactly ours.

**One question decides it, and no first-party source answers it:** does `claude -p`, invoked by an operator's own script on their own machine, count as the sanctioned *Claude Code on your machine* path, or as *programmatic Agent SDK use*? The May announcement named `claude -p` explicitly alongside the SDK.

**Stated plainly because a thesis that hides its load-bearing assumption is weaker than one that names it.** What would break is this *argument*, that wasteful experiments are free. What would not: credentials still stay at the edge, the credential is still unmintable, and the topology is still forced. **And the design is itself the hedge:** because every participant authenticates locally, a pricing change lands identically on each of them rather than centrally on an operator holding everyone's keys.

## Managed configuration is what makes the fifth need answerable

**Deliberately incomplete, and written here so the gap is visible rather than forgotten.** This is the fifth item in the list above, **user-level customization**, and it is the only one of the five without an argument behind it yet.

The shape of the answer, in one line: **configuration is resolved by tier, and a workflow resolves its own.** A participant customizing their agents, skills, rules or hooks changes what *their* interactive sessions do. It does not change what a dispatched workflow does, because the workflow derives its configuration rather than inheriting whatever the machine happened to have. That is what lets shared logic and per-person customization exist on the same machine without one silently altering the other.

**This is intentional, not a side effect**, and it is already decided rather than aspirational:

- **Operator ruling, 2026-08-19:** managed configuration, both halves, belongs to Workflow Decomposition. Which tier wins, what a user's own tier may override, and the record of what a dispatch actually absorbed.
- **[Phase 5, "what configuration a run absorbed"](../../development/workflow-decomposition/phase5_configuration_a_run_absorbed.md)** builds the *record* first and states why the tier policy waits on it.
- The seam already exists in one place: `run-claude` refuses to dispatch on an *inherited* model. Agents, skills, rules and hooks are the ambient inputs still outstanding.

**What still needs writing here:** why this is a NEED rather than a nicety, and whether it is a differentiator or simply table stakes that neither incumbent shape delivers. The comparison to make is against per-user tools, where customization is total but nothing is shared, and against centralized platforms, where logic is shared but the participant gets whatever the server decides.

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

**Not ratified as a standard.** This states the problem and the intent. Binding decisions live in `docs/standards/`; what is built and planned lives in [`../../development/sprint.md`](../../development/sprint.md).

Supporting evidence is in the research pool beside this file: [`research/synthesis.md`](research/synthesis.md) rolled up, [`research/raw/`](research/raw/) for the papers. **[`research/raw/combination_prior_art.md`](research/raw/combination_prior_art.md) and [`research/raw/case_against.md`](research/raw/case_against.md) are the two that forced this document's rewrite** — both argue against the position this repo held, and both were commissioned to do exactly that. Originally developed as a CSCI-6905.604 research project (2026-07).
