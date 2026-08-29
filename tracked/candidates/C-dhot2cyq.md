---
id: C-dhot2cyq
title: Route a parent's loop-back by WHAT THE RUNWAY NAMES, so passes are not spent firing a child that cannot reach the correction close it
status: open
count: 3
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**`plan-project`'s loop-back can only reach `plan-sprint`, and the comment justifying that reasons entirely about TRIAGE** — *"every candidate already carries a decision, so re-triaging would re-litigate rulings"* — because when it was written the research step was inert by construction and no research artifact could appear in a plan-project PR. **`plan-candidates` is what changed that**, which is why this is filed from this PR rather than earlier. **The consequence:** a `review-pr` runway naming a component's `synthesis.md` (a thin citation, an unverified span — exactly what `research-verify` and `research-critic` exist to catch) is dispatched `MAX_LOOPS` times at `plan-sprint`, which cannot edit a research pool, and the run then reports *"The automated loop is SPENT"* over a defect nobody addressed. The operator pays three opus dispatches and reads notes pointing at the sprint plan. **Done-state today: yes** — `research_workflow._verify_then_dispose` already routes a research runway to `research_verify` with `correction_pass=True`, so the shape exists and the work is choosing the child by runway content. **NOT a defect in what this PR built:** every documented behaviour of `plan-candidates` is correct and tested; this is a routing capability the parent has never had. **Not an expansion of C-hii1c5ox:** that is about a filer choosing a component name. This is about which child a correction pass reaches. Disjoint remedies, different files. **Not filed as an issue** — capability that would be ADDED, per [`finding-routing.md` § 4](../../docs/standards/finding-routing.md).

**Source:** PR for `plan-candidates` (build-refine pass 2, 2026-08-14)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*

---

**2026-08-29 — recurrence 2 and 3, and the item's SUBJECT MOVED.** `plan-project` was narrowed
to `triage-candidates → plan-candidates → review-pr` on 2026-08-29, which leaves it ONE producing
child and dissolves this item *for that parent*. **The class did not dissolve — it relocated to
`plan`, which has three producers and a loop that ignores the routing hint the reviewer already
writes.** An earlier reading of this item as "dissolved by the narrowing" was wrong about the
class and is corrected here.

Two independent observations, both 2026-08-29:

- **CDF PR #145.** `review-pr` emits a `dispatch_tool` per runway entry and **nothing in the tree
  reads it** — every reference is a test. `plan_workflow.py` fires `plan-draft` unconditionally.
  Passes 4, 5 and 6 issued the SAME runway naming `plan_revision.sh`; three full
  draft→verify→sprint triples ran instead, each touching **zero** runway items. Six of seven
  redispatch items were structurally unreachable by that child.
- **MDC PR #173** (PM3). *"The review workflow prescribes dispatch tools by TYPE and by SIZE, but
  never by WRITE SCOPE, and the type-matched tool was structurally incapable of making the
  most-repeated correction."* Four passes; the close-out had to split into two dispatches purely
  on grant boundaries.

**PARTIALLY MITIGATED 2026-08-29, and the operator ruled the remainder deliberately deferred.**
The cheap half shipped: the dispatch-sizing table now carries a **write scope** column with a line
telling the reviewer to check reachability before naming a tool, and `plan-draft`'s prompt was
told about the `docs/file_structure.txt` grant it already held in code. That covers the measured
cases without changing how any parent routes.

**What is still open is the routing itself** — a parent reading `dispatch_tool` and dispatching
what it names. **WATCH CRITERIA: ship it on the next occurrence where a runway names a tool the
loop cannot fire AND the write-scope column did not prevent the wasted pass.** The column is the
cheaper control and it is now in place; if a pass is still spent on an unreachable correction, the
column is insufficient and the routing is the remedy.
