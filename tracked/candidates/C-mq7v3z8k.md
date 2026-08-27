---
id: C-mq7v3z8k
title: The managed/user configuration tier is named only in the prose of a phase that will close, so the successor Phase 5 defers to has no surface that outlives it
status: open
count: 1
filed: 2026-08-27
filed_by: plan-feature
component: workflow-decomposition
size:
decision:
---

**PROPOSAL — a capability that does not exist, deliberately deferred, and currently tracked nowhere that survives the deferral.**

**What was deferred, and correctly.** [Phase 5](../../docs/development/workflow-decomposition/phase5_configuration_a_run_absorbed.md) carries a roadmap checkbox with two halves — *"the fleet's set becomes managed; the user keeps a tier they own and can extend"* and the record of what a dispatch absorbed. The phase builds the record and **explicitly declines to build the tier**, because the precedence direction is a policy choice the digest is meant to supply evidence for. That reasoning is sound and this candidate does not reopen it.

**The defect in the placement, not in the decision.** The phase doc then states: *"The tier mechanism is a SUCCESSOR, gated on the evidence this phase produces and on an operator ruling about precedence direction — so it is named here as what comes next and is **not** a completion criterion of this phase."* **A successor named in the prose of a phase that closes is a successor with no surface.** When Phase 5's boxes are ticked, the only record that this work was consciously deferred rather than finished lives in a document whose header says COMPLETE, and the component's roadmap says *"when these phases close, decomposition is done."*

**Why this is a candidate and not an issue.** It is capability that does not exist and would be added — [`finding-routing.md`](../../docs/standards/finding-routing.md) §4 routes that to `candidates/` whatever its done-state looks like. Nothing behaves wrongly today.

**Why it is filed now rather than when Phase 5 ships.** The four stores did not exist when Phase 5 was planned on 2026-08-18; they landed 2026-08-26. At planning time there was no store a deferral could be placed in and prose was the only option available. There is one now, so the placement is available and the deferral becomes durable.

**Proposed action.** Rule the managed/user configuration tier as its own unit of work once Phase 5's digest and reader have produced evidence:

1. **Which direction precedence runs.** The field runs both ways — vendor-package systems (git, npm, systemd) let the *local* tier win; org-policy systems, including Claude Code's own Managed tier, let the managed tier win **unconditionally, with no user override**. Phase 5's checkbox promises the first shape; reaching for Claude Code's Managed tier because the word matches would silently adopt the second and remove the tier the checkbox promises the user.
2. **What the user tier may override**, stated as a list rather than as a principle.
3. **Whether the mechanism is Claude Code's Managed tier at all** — gated on Phase 5 requirement 5's measurement (does that tier survive `--setting-sources` and `--safe-mode`), which is unmeasured today and which nothing may be designed on until it is run.

**Where it lands if adopted** is `docs/development/workflow-decomposition/` — the operator ruled on 2026-08-19 that managed configuration belongs to this component in full, and that ruling is not in question here. Whether it becomes a sixth phase or a follow-on sprint item is the triage call, not this candidate's claim.

**Not a duplicate of [[C-idwrru3n]] or [[C-7ymfdw28]]**, and the distinction matters because all three touch `~/.claude/`. Those two are about the **install mechanism** — per-file symlink granularity, and pointing the symlinks at a pinned worktree so `git pull` is the deploy step. Both change *how the configuration gets onto a machine*. This is about **whose tier wins once it is there**, which is a policy question that stands whatever the install mechanism is, and which neither of them answers. They are constrained together as an architecture surface; this is not on that surface.

**Source:** `plan-feature` follow-up design pass over `docs/development/workflow-decomposition`, 2026-08-27, reading [`phase5_configuration_a_run_absorbed.md`](../../docs/development/workflow-decomposition/phase5_configuration_a_run_absorbed.md) § *Requirement 1's checkbox has two halves* against [Tracked Items Standard §1.1](../../docs/standards/documentation/tracked_items_standard.md).
