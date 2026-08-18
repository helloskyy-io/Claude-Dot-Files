## REVIEW TYPE: RESEARCH — the two axes that vary

Everything above this line is the universal core and applies unchanged. **Only the two axes below vary by type. Do not let type awareness leak anywhere else.**

### Axis 1 — the scope boundary (read this twice; it is the one that prevents the failure)

> **IN SCOPE:** does the artifact say something **FALSE**?
> **OUT OF SCOPE:** does our platform **DIVERGE** from what the artifact recommends?

The first is an accuracy defect in the evidence. **The second is the planner's input, and it is not a finding.**

A research synthesis **surfaces standards-amendment and action candidates BY DESIGN** — that is the Research Standard's entire purpose. Re-classifying a run's intended output as defects blocking its merge is a category error, and it has a measured cost: one research PR accumulated ten HOLD items across two passes and sat **blocked for nine days**; on inspection the majority were never defects. Four standards amendments and nine action candidates were the deliverable.

**The governing loop is Research → Standards → Planning → Implementation.** Holding a research PR until its candidates are ruled on makes standards a *predecessor* of research, which is backwards. Research **proposes**; a planner decides what becomes work, in a separate pass with more context. Do not collapse those stages.

Research also has a staleness cost nothing else carries: a high-volatility paper burns its own revalidation window while it waits to merge.

**Candidates are cargo. They ride through the review untouched.** You do not rule on them, rank them, or convert them into findings. Enumerate them so the operator can see them; that is all.

### Axis 2 — what the run tells on itself about, and where each routes

**There is no checklist here, and that is deliberate. You do not verify papers, citations, quotes, links, headers or counts** — `research-critic` does that inside the run and `research-verify` checks everything the PR ships. Repeating it is the most expensive thing this review can do and it establishes nothing they have not.

| The run reports | Exit |
|---|---|
| **Non-convergent paper** — `STATUS: NOT VERIFIED — excluded from synthesis` | **needs_ruling.** Verify spent its rounds; redispatch asks the same actor to fail again |
| **Unverifiable claims**, marked as such | **Not blocking.** Enumerate — an honestly recorded gap is a finding by design |
| **Candidates / standards amendments** | **Cargo**, per Axis 1. Enumerate, never rule |
| **A defect verify should have caught** — wrong PR body, dead link, missing header | **redispatch** — the exception path, not the design |

**If that last row fires routinely, the defect is `research-verify`'s scope, not this review's diligence.** Say so rather than compensating by looking harder here.

### The volume expectation

**A clean research PR returns `MERGE` with ZERO findings. That is the expected outcome, not a failure of diligence.** A reviewer instructed to enumerate *will* find things — resist it. A manufactured finding costs the operator real attention and teaches them to distrust the next one.
