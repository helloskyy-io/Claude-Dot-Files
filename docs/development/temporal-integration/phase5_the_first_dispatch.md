# Phase 5 — The first dispatch, end to end

**Status: ⬜ NOT STARTED.** Listed after [Phase 4](phase4_the_claude_cli_activity.md) in [rollout order](roadmap.md) — sixth in that order since [Phase 9](phase9_review_runs_in_the_python_tree.md) was inserted — and the first phase where a wrong answer in any earlier one becomes visible.

**One worker, one family, one pull request.** This is the strangler fig, and it is deliberately thin. The thing that breaks a port is never the second family — it is the first, and everything the first one teaches is cheaper to learn against a single dispatch than against twenty.

It also carries the audit that [Phase 3](phase3_the_retry_boundary.md) deliberately defers. Temporal retries the **whole activity body**, not the failed sub-call, so *"this activity is idempotent"* is a claim about a wrapper end to end and not about the `gh` call inside it. That claim has to be ruled against the actual population of wrappers, which does not exist until this phase creates it.

---

## Requirements for completion

1. **One worker runs as a bare systemd process** on the machine holding the repo, polling exactly one machine-axis task queue — the one [Phase 1](phase1_the_starter_control_plane.md) named.
2. **Every activity the chosen family needs is wrapped**, and each is ruled against [Phase 3](phase3_the_retry_boundary.md)'s two options — **the whole population, not a sample** — with the ruling and its reasoning recorded per activity.
3. **Every dispatch names its target task queue explicitly.** Inheriting the parent's queue is forbidden, and it is the failure mode that produces no error at all: the work sits on a queue where its type is not registered, indefinitely, silently.
4. **The completion contract still holds.** The run's final line still carries the stable identifier a parent reads, and the parent still branches on an exit code plus that identifier.
5. **One dispatch produces one PR end to end under Temporal**, and survives a worker restart mid-run.
6. **[Phase 2](phase2_durable_dispatch_identity.md)'s *parent sequencing* recovery row is satisfied, and this phase is what satisfies it.** That row records the fleet's largest recoverability gap — which child ran, what it concluded, how many loops have been spent, all of it living only in a live process's memory. **Writing the parent as a workflow is what makes that state durable**, because Temporal's event history *is* the record the row asks for. The requirement is therefore concrete and checkable: **demonstrate that a parent which dies between children resumes knowing the earlier ones succeeded**, and record what carries that knowledge against what the row says should carry it. Phase 2 fills the row; this phase is its first reader, and until something reads it the row is a schema nobody has tested.

---

## Dependencies

**Inside this component:** [Phases 1, 2, 3 and 4](roadmap.md) — named rather than counted, because [Phase 9](phase9_review_runs_in_the_python_tree.md) also precedes this one in rollout order and **is not a dependency of it.**

| Depends on | Why |
|---|---|
| [Phase 1](phase1_the_starter_control_plane.md) | the worker needs a frontend to poll, and a queue name that will not change under it |
| [Phase 2](phase2_durable_dispatch_identity.md) | requirement 1 of that phase must hold, or every retry mints a new identity |
| [Phase 3](phase3_the_retry_boundary.md) | requirement 2 of this phase is that phase's ruling applied |
| [Phase 4](phase4_the_claude_cli_activity.md) | every parent in the fleet ultimately calls `claude -p` |

**Outside this component, and it is TWO things rather than one:**

| Precondition | Why it blocks, and what it is not |
|---|---|
| [Workflow Decomposition](../workflow-decomposition/roadmap.md) | see below — a shape still being re-cut is ported twice |
| **Candidate [C-118](../../standards/architecture/research/candidates.md) triaged** | §A4 — prompt-as-input or prompt-as-resource — is unruled, and *"Write the parent as a workflow"* is the step where a replay first has to load a prompt from somewhere. **This is a stop condition, so it belongs here and not only in § *What this phase does not settle***, where a dispatcher scanning dependencies would never see it. **It is not a technical dependency and nothing in this component can clear it** — it is a ruling somebody has to make |

[Workflow Decomposition](../workflow-decomposition/roadmap.md) is where the component's stated gate actually bites — *porting a shape still being changed means porting it twice*, and this is the first phase that ports a shape. **Which of that component's phases must land before this one is an operator sequencing call, not a technical derivation**, and it is named in § *What this phase does not settle*.

**What this phase unblocks:** [Phase 6](phase6_the_rest_of_the_fleet.md).

---

## What this phase rests on

**No paper in this component's pool backs this phase directly**, and that is stated rather than left to be noticed. It applies rulings the earlier phases made:

- [Phase 3](phase3_the_retry_boundary.md)'s per-call-class ruling, and the whole-body-retry fact from [`raw/activity_retry_boundary.md`](research/raw/activity_retry_boundary.md) §2.7 that makes requirement 2 an audit rather than an assumption.
- [Phase 2](phase2_durable_dispatch_identity.md)'s identity contract, from [`raw/durable_dispatch_identity.md`](research/raw/durable_dispatch_identity.md).
- The vendored [Worker Deployment Standard](../../standards/temporal/worker_deployment_standard.md): **§1.1** one worker per domain and one queue per worker, **§1.4** the cross-worker dispatch invariant, **§7** worker entry points, **§8** fail-fast dispatch, **§3** the same-PR worker-inventory obligation.
- The [Temporal Standard](../../standards/temporal/temporal_standard.md)'s three-layer model, which is already what this fleet's directory layout means — the alignment was done deliberately so the port is a re-host rather than a redesign.
- [D11 of the seed handoff](../skyy-net-seed-handoff.md): milestone 1 stays thin. One dispatch workflow, one edge worker, one PR produced end to end, everything else added to a running platform afterwards.

---

## Choosing the family — the criteria, not the pick

**The pick is the build's, and it should be made against these criteria rather than by preference.** A family qualifies if it:

1. **Calls `claude -p`**, so [Phase 4](phase4_the_claude_cli_activity.md)'s activity is exercised rather than merely present;
2. **Touches the `gh` seam in both modes** — at least one read-only call and at least one mutation — so [Phase 3](phase3_the_retry_boundary.md)'s split is exercised on both sides rather than on the easy one;
3. **Produces a PR**, so requirement 4's completion contract is a real assertion;
4. **Is the smallest family satisfying the first three.**

**The leading candidate is the `build_minor` family** — the one-lens tier, whose draft/refine/review-pr shape is the composition contract already codified in [`workflow-scripts.md`](../../standards/workflow-scripts.md). It satisfies all four and its children are the shortest in the fleet. **The build may choose otherwise and should say why** — what must not happen is choosing the largest family because it is the most familiar.

**Do not choose a family whose children Workflow Decomposition is actively reshaping.** That is the gate this phase inherits, made concrete: a family being re-cut mid-port is ported twice.

---

## Implementation steps

- [ ] **Pick the family against the four criteria above**, and record the choice and the reasoning in this doc before writing anything.
- [ ] **Enumerate every activity that family reaches** — including the ones it reaches transitively through shared modules. **Read it off the tree, never off a table**; a hand-kept list is the shape that reads as complete and is not.
- [ ] **Rule each enumerated activity against [Phase 3](phase3_the_retry_boundary.md)'s two options.** For each: is the *whole wrapper body* idempotent, or does it do file/git work before its `gh` call? Record the verdict and the reasoning per activity, not as a summary.
- [ ] **Write the semantic wrappers.** `@activity.defn` over the plain functions Stage A already produced — the plain functions are untouched, which is the property that made the staging worth having.
- [ ] **Give each wrapper a unique activity name**, so the Temporal UI names a call site rather than a function. That superpower lives in the semantic wrappers, not in the helpers, and losing the distinction is how a port arrives with a UI nobody can read.
- [ ] **Build the worker entry point** per [§7 of the deployment standard](../../standards/temporal/worker_deployment_standard.md), registering only this family's workflows and activities.
- [ ] **Set this worker's activity slot count and executor width by [Phase 4](phase4_the_claude_cli_activity.md)'s requirement 8**, and record the number and the budget it came from in § *Runtime Verification*. **This is the fleet's first real worker, so it is where the precedent is set** — and left unset, `max_concurrent_activities` admits a hundred concurrent `claude` runs on the machine holding the repo.
- [ ] **Install it as a systemd unit** — a Python venv with `temporalio` plus the `claude` CLI, on the machine holding the repo. **Not a container**; see the gotchas.
- [ ] **Write the parent as a workflow**, holding no process code and calling no model. It decides *if*, *when* and *what*; every side effect is an activity or a child.
- [ ] **Restart the worker while the parent sits BETWEEN children, with no activity in flight** — requirement 6 — and show the next workflow task replaying the completed children out of event history. Record what the parent knows on resume against what [Phase 2](phase2_durable_dispatch_identity.md)'s *parent sequencing* row says should be durable. **`terminate` and `cancel` are the wrong levers and naming them is the point: a terminated workflow does not resume**, so reaching for one demonstrates the opposite of the property under test. **This is the same lever as the mid-activity restart above, timed differently, and the two fail differently; do both.**
- [ ] **Name the target task queue on every dispatch, including parent-to-child.** Add a test that fails on a dispatch with no explicit `task_queue`, because this failure mode produces silence rather than an error.
- [ ] **Fail fast on dispatch.** Per [§8](../../standards/temporal/worker_deployment_standard.md), a start against a queue nobody polls must be a loud failure, not a wait.
- [ ] **Confirm the completion contract survives.** The parent needs the child's exit code plus one stable identifier on its final line; that is the interface, and it is why composition here needs no framework.
- [ ] **Run one dispatch end to end and produce one PR.** Record the run in this doc.
- [ ] **Kill the worker mid-run and restart it.** Record what happened against what [Phase 2](phase2_durable_dispatch_identity.md)'s and [Phase 4](phase4_the_claude_cli_activity.md)'s rulings predicted, and treat a disagreement as the ruling being wrong.
- [ ] **Update the worker inventory in the same change** — the deployment standard's §3/§3.1 obligation is binding and is the one part of that vendored file an engineer may edit directly, because it is a factual registry whose source of truth is the code.
- [ ] **Re-run § *Runtime Verification*** and replace it with observations of the standing worker.

---

## §Runtime Verification

**Date:** 2026-08-19 · **Host:** `puma-workstation-mint` · **Runtime verified:** the local worker prerequisites. **No worker and no Temporal server exist yet** — this block records the starting state and is replaced by requirement 5's observations.

```
$ python3 --version
Python 3.13.12

$ python3 -m pip show temporalio | head -2
Name: temporalio
Version: 1.27.2

$ claude --version
2.1.235 (Claude Code)

$ hostname
puma-workstation-mint
```

**One live obstacle carried forward from [Phase 1](phase1_the_starter_control_plane.md)'s verification, because it bites here too:** on this workstation, ports **7233 and 8080 are already held by a running VS Code process** (`ss -tlnp` → `pid=3528184 code`). A worker configured against `localhost:7233` on this machine will connect to an editor. Whatever the worker's frontend address turns out to be, **it must not be assumed to be the local default**, and a reachability check that only tests whether the port is open will pass for the wrong reason.

**What the build must add here:** `systemctl cat` for the worker unit showing its actual `ExecStart`, the worker's observed poller registration on its queue, and the frontend address it resolved.

---

## Notes, decisions and gotchas

- **The workers are bare systemd processes and this is not negotiable.** A worker spawns `claude` needing a real repo, a real toolchain and real credentials; containerizing buys worse fidelity at higher complexity. **MDC containerizes its workers because its activities call APIs, not local development environments — a different constraint with a different answer.** The k3s and immutable-image sections of the deployment standard govern the control plane, which is [Phase 1](phase1_the_starter_control_plane.md)'s, not this phase's.
- **`children/` dissolves and nothing is lost.** There is no such directory in the Temporal model, because a child workflow is not a kind of file in a place — it is a workflow another workflow starts. Child-ness is a call-graph property. Every workflow lands in `modules/` regardless of who calls it; the directory exists today only because a shell script has no call graph to read.
- **No helper or compiler tier is needed for this fleet's shape.** The standard exempts direct-dispatch orchestrations — parents naming the callable inline — from the step-dict execution-plan pattern. **That exemption stops applying** the moment git and `gh` operations move out of the model's turn and something has to compile their inputs. Notice when that happens rather than discovering it.
- **Watch for a UUID minted inside what is now workflow code.** [Phase 2](phase2_durable_dispatch_identity.md) names one such site and rules it; if a second appears during wrapping, it is the same defect class — a random value does not replay, and Temporal replays workflow functions.
- **A returned failure is not a failure.** An activity that *returns* a failed result has completed successfully as far as Temporal is concerned and will not be retried. Any wrapper written to report failure by return value silently opts out of the retry policy [Phase 3](phase3_the_retry_boundary.md) just designed.
- **The completion contract is the interface, and it predates Temporal.** A parent needs an exit code plus a stable identifier on the final line. Temporal is being adopted for **durability, resumability and cross-run observability — not to gain composition**, which already works. If a wrapping decision would break the completion contract to gain something Temporal-shaped, it is the wrong trade.

---

## What this phase does not settle

**Which [Workflow Decomposition](../workflow-decomposition/roadmap.md) phases must land before this one starts.** The gate is real — porting a shape still being changed means porting it twice — but *"is this family's shape settled?"* is a judgement about work another component owns, on a schedule this plan does not control. **It is an operator sequencing call**, and it belongs in [`sprint.md`](../sprint.md) rather than being guessed here.

**§A4 — whether a prompt is an INPUT or a RESOURCE — and this phase is where it stops being abstract.** [§A4 of the addendum](../../standards/temporal/claude-dot-files-addendum.md) is `📋 OPEN` and **no phase in this component rules it.** It becomes concrete here because this is where a parent first becomes a workflow: **a workflow function is replayed, and a replay has to get its prompt text from somewhere.** If the prompt is versioned with the code, a replay loads *today's* text rather than the text that ran; if it is an input, it rides the payload and meets the limits [Phase 4](phase4_the_claude_cli_activity.md) is built around. **This plan does not rule it** — the ruling is tracked as candidate **C-118** in [`candidates.md`](../../standards/architecture/research/candidates.md), untriaged, and it is named on the [roadmap](roadmap.md) § *What is deliberately not built*. **A build run reaching this step with C-118 still untriaged should stop and get the ruling, not pick one.**

**Requirement 2's ruling is per-activity and this plan does not pre-empt it.** The audit's *method* is specified above — read the population off the tree, rule each wrapper on whole-body idempotency, record the reasoning. Its *results* cannot be written before the wrappers exist, and a plan that guessed them would be supplying an answer the audit is supposed to produce.
