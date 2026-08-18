# Temporal Integration

The port of the workflow fleet onto durable execution.

**Status: Stage A is substantially built.** The Python tree exists under `scripts/workflows/temporal/`, the parity suite runs against the bash fleet, and the planning family — `plan-sprint`, and `triage-candidates` split out of it in PR #85 — has no bash ancestor at all and was authored directly in the Python tree. Temporal itself is not stood up and nothing is orchestrated.

## Why Temporal, and what it is not for

Temporal is being adopted for **durability, resumability and cross-run observability** — **not to gain composition**, which already works in bash. A parent needs a child's exit code plus one stable identifier on its final line, and the completion contract already supplies both.

**Gated on Workflow Decomposition and the Memory Management Framework.** Not by preference, by dependency: porting before the decomposition and the typed handoff are settled would mean porting a shape we are still changing.

**Counter-argument, stated fairly.** Bash has zero runtime dependencies, the current fleet works, and every activity ultimately shells out to `claude -p` regardless. A rewrite buys nothing on its own — it only pays off as part of this port, and Stage A is what makes it pay off early rather than at the end.

## What is already true and should not be re-derived

- **Our layers already map.** `children/` are child workflows, not activities — an activity must be idempotent per §7.1, and a child that pushes commits is not. `activities/` are the generic executors. Parents are parent workflows. That alignment was done deliberately so the port is a re-host rather than a redesign.
- **No helper/compiler tier is needed** for our shape — the standard exempts direct-dispatch orchestrations (parents naming the callable inline) from the step-dict execution-plan pattern. That exemption stops applying when git/gh operations move out of the model's turn and something has to compile their inputs.
- **Topology, from the seed handoff:** server (Temporal + Postgres) on a backed-up VM so event history is a backed-up asset; workers as **bare systemd processes, never containerized**, on every machine that holds repos. Claude Code must run on the machine holding the repo, and that repo-locality constraint drives the whole worker placement.

Decision record: [`../skyy-net-seed-handoff.md`](../skyy-net-seed-handoff.md). Binding standard: [`../../standards/temporal/`](../../standards/temporal/) — the three-tier model (generic activities → composable child workflows → parent workflows), `ActivityResult`, `ACTIVITY_MAP`.

## Implementation language — DECIDED 2026-08-03: Python

**Bash is not an option, and that is not a preference.** Temporal has no bash SDK. A worker is a long-running process that implements the task-queue protocol and, for workflow code, guarantees deterministic replay. Bash cannot do either. The SDKs are Go, Java, Python, TypeScript, .NET, PHP and Ruby — pick one or do not port.

The inputs were never open questions:

- The framework being ported **is Python** — `lib/temporal/` in Skyy-Command, 123 non-test modules.
- The **Worker Deployment Standard is written in Python** — `python:3.11-slim` base image, `CMD ["python", "<worker>_worker.py"]`. Conforming to a binding standard while choosing a different language means diverging from it on day one.
- The seed handoff already specifies the worker as a Python venv with `temporalio` plus the `claude` CLI.

Choosing anything else is not evaluating options, it is proposing to diverge from a standard we have already agreed to conform to. **Do not re-open this.**

**The bash does not die.** Skyy-Command's activities already shell out via `subprocess` in several domains, and every activity we would write ultimately invokes `claude -p` anyway. A bash script survives as *an executable an activity calls*. The open question is only whether that indirection earns its keep once the caller is already a real program.

**The narrow thing that does deserve checking** is whether any Python-SDK constraint bites our specific shape — 10–60 minute activities need heartbeating, and large transcripts hit payload limits. Both are flagged as known work in the seed handoff, which is evidence the constraint is understood rather than unexplored.

## Convert → test → orchestrate

The port does not need a big bang, and the standard's own architecture is what allows this. Generic executors under `activities/` are **plain functions** — verified in Skyy-Command: no `@activity.defn`, no `temporalio` import, just `subprocess` and a returned `ActivityResult`. Decoration happens one layer up, in the semantic wrappers. So the port splits into stages that are each independently valuable:

| Stage | What exists at the end | Temporal needed? |
|---|---|---|
| **A — Convert** | The fleet as plain Python functions plus a CLI entrypoint. Same invocation UX as today, now unit-testable, and the prompts-are-code escaping class disappears with real string literals | **No** |
| **B — Wrap** | Semantic wrappers add `@activity.defn`; the plain functions from A are untouched | Yes, but nothing orchestrates yet |
| **C — Orchestrate** | Workflows and parents compose the wrappers; schedules replace timers | Yes |

**Stage A is a valid resting place.** If Temporal slips, we still have a tested Python fleet that runs exactly like the bash one and has shed an entire class of outage. That is the property that makes this safe to start before everything else is settled.

## The migration path, end to end

1. **Convert the existing fleet to Python, in place.** Everything in `activities/`, `common/`, `children/` and the top-level parents becomes Python with a CLI entrypoint. Same invocation UX, same behaviour, no Temporal. This is Stage A, and it stands on its own.
2. **Stand up Temporal.**
3. **Refactor into the Temporal file layout** — the `{name}_workflow.py` / `{name}_helper.py` / `{name}_activities.py` trio beside each other in a module purpose folder, generic executors under `activities/`, per Temporal Standard §3 and §10. `activities/` and `common/` map straight across. **`children/` dissolves** — there is no such directory in the Temporal model, because a child workflow is not a kind of file in a place, it is a workflow another workflow starts; every workflow lands in `modules/` regardless of who calls it. The directory exists today only because bash has no call graph to read.
4. **Bring the Temporal standards over** — adopted rather than re-derived, with an addendum only for what is genuinely ours: long-activity discipline for 10–60 minute `claude -p` runs, machine-axis queue naming, topology profiles.
