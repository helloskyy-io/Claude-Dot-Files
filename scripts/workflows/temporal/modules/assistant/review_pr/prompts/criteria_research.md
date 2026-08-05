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

### Axis 2 — the blocking-defect checklist (exactly six; nothing else blocks)

1. **Every citation resolves and the claim matches the source.**
2. **Internal links resolve.**
3. **Header block present and machine-parseable** — `Revalidate:` interval, `Critic:` line.
4. **Honest-boundary section present.**
5. **No statement about our platform that is factually false.**
6. **Source-count floor met for the paper's size.**

That is the whole review. These artifacts already passed `research-critic` **inside** the run; this is a **fresh-context integrity pass**, not a second opinion on the research itself.

Worth knowing why it is kept rather than skipped: one pass found **18 broken links** in a document whose entire purpose is traversable evidence, plus a false statement about shipped state. `research-critic` verifies that sources exist and claims match them — it does **not** check internal link integrity or platform accuracy. That gap is real, and fresh-context review is what closes it.

### The volume expectation — state it to yourself before you begin

**A clean research PR returns `MERGE` with ZERO findings. That is the expected outcome, not a failure of diligence.**

A reviewer instructed to enumerate *will* find things. Resist it. If the six checks pass, say so and merge — a manufactured finding costs the operator real attention and teaches them to distrust the next one.
