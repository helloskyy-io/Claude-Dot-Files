---
id: C-zhdm5gh1
title: **Temporal addendum §A3 is scoped to machine-axis queue naming only, while two planning docs nominate it as where the RUN-IDENTITY ruling lands — so resolving §A3 as written settles queue names and leaves identity unruled, and identity gates the Temporal port's Stage B**
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: temporal-integration
---

**The consequence: a gate that reads as satisfied while the thing it gates is untouched.** [`claude-dot-files-addendum.md:33`](../../temporal/claude-dot-files-addendum.md) reads `## §A3 Machine-axis queue naming — 📋 OPEN`, and its body is entirely about task-queue naming for machine-segmented workers. But [`temporal-integration.md`](../../../development/temporal-integration/temporal-integration.md)'s migration path, at the **dispatch-identity step**, names §A3 as the artifact that rules *what the run id IS* — whether the port's workflow id can **be** the run id or has to be joined to a second name — and [PMP Phase 9](../../../development/persistent-memory-protocol/phase9_one_run_one_identity.md) refers its own open questions to the same section from the other side. **Whoever closes §A3 will close it against its title.** The port's Stage B is the deadline: after Stage B, moving where a name is minted means changing wrapped activities rather than plain functions, so an identity question still open at that point is a migration rather than a parameter. **Evidence:** `claude-dot-files-addendum.md:33`; `temporal-integration.md`'s migration path at the dispatch-identity step, which already flags the mismatch in-line and correctly declines to fix it (*"a human-in-the-loop edit to a standards file, not this step's to write"*). **The remedy is a human ruling and this row queues it, nothing more**: widen §A3's title and scope to carry the identity ruling alongside queue naming, or split identity into its own §A-section and re-point both planning docs at it. **The addendum itself is deliberately untouched** — it is a standards surface, and [`standards-governance.md`](../../../../config/rules/standards-governance.md) makes widening it the operator's. **Precedent for a standards-amendment proposal living in this queue: C-97zzv697**, which likewise records a standards-relevant fact whose natural home is human-in-the-loop and names the interim carrier. **Done-state today: yes** — it is a scope ruling on an existing OPEN section, not work waiting on a trigger.

**Source:** PR #123 (`review-pr` pass 2)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
