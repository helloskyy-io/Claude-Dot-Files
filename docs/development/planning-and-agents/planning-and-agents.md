# Phase: Planning & Agents

**Status:** ✅ COMPLETE — one item deliberately abandoned, see below
**Roadmap entry:** [`../sprint.md`](../../sprint.md)
**Depends on:** [`cross-device-sync.md`](../cross-device-sync/cross-device-sync.md) — agents are only useful if they are on every machine

## Goal

Build the specialists a workflow can dispatch. Autonomous runs need to plan, review and verify without a human in the loop, and that requires actors with **narrow, distinct lenses** rather than one general-purpose helper asked to be thorough.

## Completion criteria

- [x] Each agent answers **one question** no other agent answers
- [x] Agents are read-only unless writing is their job
- [x] They do not fire on routine work — depth is opt-in
- [x] Invocable interactively, not only from workflows

## Work

- [x] **`architect`** — system design, trade-offs, scalability. Read-only, opus
- [x] **`planner`** — feature decomposition, phased plans, risk. Read-only, opus
- [x] **`code-reviewer`** — bugs, performance, security, style, reported by severity. Read-only, sonnet
- [x] **`test-writer`** — generates tests to project convention and runs them. Full access, sonnet
- [x] **`security-auditor`** — OWASP-focused, with exploitation scenarios, and **reports clean areas to prove coverage**
- [x] **Two-tier agent strategy** — built-ins handle routine work automatically; custom agents are on-demand only
- [x] **`/review`** and **`/best-practices`** slash commands
- [ ] **~~Port Cursor workflows to slash commands~~** — **ABANDONED.** See below

## Decisions

**Two tiers, and the second is opt-in on purpose.** Built-in agents fire automatically on routine work. Custom agents do not fire at all unless asked. An agent that triggers proactively competes for attention with the work in front of it, and a specialist that interrupts constantly stops being consulted — so depth is something you reach for, not something that happens to you.

**Read-only by default, and the exception is narrow.** Only `test-writer` writes, because generating a test it cannot run is useless. Every other agent returns findings for the main loop to act on. This is what makes it safe to dispatch four of them at once against the same tree.

**Report clean areas, not just findings.** `security-auditor` states what it checked and found sound. An audit that returns nothing is ambiguous — thorough, or did it not look? — and an unfalsifiable clean bill is worth nothing.

**Subagents cannot spawn subagents.** A platform constraint, and it is the reason orchestration lives in bash rather than inside a "coordinator agent." Multi-step work chains from the main conversation. That constraint shaped everything downstream, including the parent/child workflow model.

## What was abandoned, and why

**Porting Cursor workflows to slash commands never happened, and should not.** It was a migration task written while still thinking in the old tool's terms — a list of saved prompts to carry across.

What actually replaced them is better and arrived from a different direction: **methodology became skills**, loaded on demand when context matches, with commands as thin invokers for when you want to force the lens. A saved prompt is a snippet that rots; a skill is methodology with one home and two entry points. The rule that fell out — *write it as a skill once it has been explained twice, and never speculatively* — is now in [`../../standards/skills.md`](../../../standards/skills.md).

Leaving the box unchecked would imply pending work. It is not pending; it was answered by a better design.

## What this phase set up that was not obvious at the time

The **distinct-lens** principle is what later made a review *panel* work. Four agents against one tree only produce four useful results if each is answering a different question — otherwise you get the same finding four times and a false sense of coverage. That principle is now binding in [`../../standards/agents.md`](../../../standards/agents.md), along with two things this phase did not yet know:

- **Model tier is an evidence question**, not a default. Mechanical verification runs as well on a cheaper tier; authoring a synthesis does not.
- **Web access is a capability decision with a reason to withhold it.** A conformance checker with web access grades your code against someone else's conventions, and will not tell you it did.

## Where this landed

- [`../../standards/agents.md`](../../../standards/agents.md) — the standard
- [`../../guide/operations.md`](../../../guide/operations.md) — the current roster, now 14 agents
- `config/agents/` — the implementations
