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
| GitHub Issues | no-change outcomes — deferred work, planning STOPs | filed → ruled → closed |
| Standup tracker | continuity — operating state, next moves | never closes; pruned |
| `candidates.md` | research candidates and their dispositions | appended, never rewritten |

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
