# Architecture Standard

Binding vocabulary and the cross-cutting rules everything else references. **Deliberately narrow in scope** — it defines terms and boundaries and defers detail to the individual standards, so a rule lives in exactly one place.

The WHY is [`problem-statement.md`](problem-statement.md). The tech stack is [`stack_reference.md`](stack_reference.md). What is planned is [`../../development/sprint.md`](../../development/sprint.md). This file is neither the argument nor the plan.

## 1. Common terms

| Term | Meaning |
|---|---|
| **Edge** | A machine with a capability and a credential, running a worker that speaks the backbone's protocol. Not a plugin |
| **Jarvis** | The assistant edge — this repo. Coding is its first function, not its definition |
| **Backbone** | The domain-agnostic orchestration layer. It does not change when an edge is added |
| **Parent** | A workflow that calls no model. It decides *if*, *when* and *what* to call, and holds no process code |
| **Child** | A complete workflow that another workflow starts. Child-ness is a **call-graph property, not a location** |
| **Activity** | External I/O, workflow-agnostic and idempotent. A parent may not inline any of it |
| **Completion contract** | A pattern a run's final output must contain, so `exit 0` provably means *finished* |

## 2. Composition (binding)

**A parent calls no model.** It decides what runs and in what order; every side effect is an activity or a child.

```
build.sh
  ├─ build-draft     writes the change, opens an UNREVIEWED PR
  ├─ build-refine    FRESH context: fidelity, review, corrections
  └─ review-pr       decide-only: MERGE | HOLD + a runway
        └─ HOLD(redispatch) → one bounded loop-back, then stop
```

**The completion contract is the interface.** A parent needs a child's exit code plus one stable identifier on its final line. That is why composition here needs no framework.

**Isolation is an invariant, not a parameter.** Every run executes in a worktree, established once by the parent and passed down. A child that creates its own isolation cannot know whether a sibling already did.

## 3. The seams (binding)

Deliberate boundaries. Each has a reason, and each was paid for:

| Seam | Why |
|---|---|
| **author ≠ judge** | the author of a change defends it; no wording fixes that |
| **parent ≠ child** | every boundary is a retry/resume point |
| **activity ≠ workflow** | a workflow doing network I/O cannot replay |
| **decide ≠ act** | `review-pr` rules; a human or a parent fires |
| **surface ≠ ratify** | agents propose standards; humans write them |
| **derive ≠ declare** | a constant restated in two places diverges silently; read it from its source |
| **observe ≠ assert** | never report an outcome you did not read. A confident wrong answer gets acted on; a crash does not |

## 4. Memory (binding)

**No state files, no bookmarks. Open is the to-do bit.**

| Surface | Holds | Lifecycle |
|---|---|---|
| PR threads | change-outcomes, decision logs, disposition rulings | closes at merge |
| [`tracked/issues/`](../../../tracked/issues/) | **defects** — something already built or already decided behaves wrongly, in code, docs or the planning corpus. **Never a proposal.** | filed → ruled → `resolved` / `rejected`, then pruned |
| [`tracked/operations/`](../../../tracked/operations/) | continuity — operating state, next moves. **Human-in-the-loop ONLY; no autonomous run writes here** | never closes; pruned |
| [`tracked/candidates/`](../../../tracked/candidates/) | **proposals** — anything an actor wants ADDED, and the ruling queue: a finding only the operator can decide carries `decision: requires review` | filed → ruled → `adopted` / `rejected` |
| [`tracked/standards/`](../../../tracked/standards/) | **amendments to a NAMED standard**, with an anchor precise enough to act on. Filing is surfacing, not editing | filed → `ratified` / `amended` / `rejected` |

> **REBOUND 2026-08-26, and this table was the last binding surface still naming the old ones.** GitHub Issues are retired for tracked work, the standup tracker and the candidates table moved into `tracked/`, and `direction.md` was deleted. **The `standards/` row is new** — before it, an autonomous run was permitted to *surface* a standards amendment and had nowhere to put it, so correctly-classified amendments died in PR bodies. See [Tracked Items Standard](../documentation/tracked_items_standard.md), which owns the four stores.
>
> **A decide-only reviewer still cannot commit, and does not need to.** It files a `tracked-intake` GitHub issue — the same API call it always made — which a named harvest moves into the store and closes. §5.0 there makes that exemption conditional on the harvest existing.

**The full routing procedure lives in [`finding-routing.md`](../finding-routing.md), which owns it.** This section states the surface set and the one rule that decides between the two queues; the gates, the mechanism requirement and the disposition vocabulary are there, not restated here — this standard is *deliberately narrow in scope*, and a procedure that lives in two places diverges silently.

### Defect or proposal — ask this BEFORE choosing a surface (binding)

**`tracked/issues/` holds a DEFECT: something already built or already decided behaves wrongly, or a decision the existing research and planning do not supply is now blocking.** Issues are the human-in-the-loop queue and are reserved for the hardest of those.

**A PROPOSAL — capability that does not exist yet and would be added — goes to `tracked/candidates/` and is NEVER an issue**, however clean its done-state looks.

**This question comes first because the surface test alone routes proposals wrongly.** A proposal answers *"nothing changed"* and *"it has a done-state"* — *"add a link checker"* has a perfectly clean one — so any rule keyed on those two properties files it as an Issue. Measured across two repos in one cycle: roughly a third of everything filed was a proposal, and clearing the queue cost two working days against zero days of development.

**Bias toward `tracked/candidates/` when a finding reads either way.** The costs are asymmetric: a proposal misfiled as a candidate costs a triage pass; a proposal misfiled as an issue costs an operator's day. **No actor is expected to know where a proposal belongs in the plan** — only that it is one. Deciding whether it becomes a sprint, a phase or nothing is separate triage with its own criteria.

**Breaking it looks like:** an issue item proposing capability that does not exist; a second item describing the same mechanism as an existing one in different words instead of incrementing its `count`; several issues from one pass against one file or one function; a proposal parked on the standup tracker, whose own rules forbid it.

Every reviewing actor verifies claims **against the artifact rather than the account of it**, and verifies a pointer by fetching it.

## 5. The improvement loop (binding)

Two machine-produced evidence sources, no human gathering data: **run logs** (every dispatch writes JSONL) and **self-disclosure** (every workflow posts a decision log and tooling suggestions to its PR).

Findings reach an explicit ship / defer / reject in an append-only log, **ruled by a human**. The system observes itself and proposes; **it does not modify itself.**

## 6. Safety (binding)

Autonomous runs pass `--dangerously-skip-permissions`, so the `PreToolUse` hook is **the only control operating during a run** — worktree isolation bounds blast radius, PR review is after the fact. `block-dangerous.sh` is therefore load-bearing rather than defence-in-depth, and **it fails closed**. Nothing reaches `main` except through a PR.

## 7. What this standard does not contain

Completion state, plans and history. A standard states **the rule, never the status** — what is built and what is queued belong in [`../../development/sprint.md`](../../development/sprint.md), and why a decision was made belongs in the phase doc that made it.

## Related

- [`problem-statement.md`](problem-statement.md) — the problem and the thesis
- [`stack_reference.md`](stack_reference.md) — what we run on
- [`research/`](research/) — the evidence, non-binding
- [`../workflow-scripts.md`](../workflow-scripts.md) — the binding rules for workflow layout and authoring
