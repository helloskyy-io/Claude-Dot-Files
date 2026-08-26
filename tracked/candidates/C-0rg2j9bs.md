---
id: C-0rg2j9bs
title: Gate `vendor-standards.sh --check` on the merge path so a local edit to a vendored MIRROR standard cannot merge green
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

Nothing is broken — the check works and is correct; this ADDS a gate. Split ruled: the committed-checksum half (local-edit detection) needs no upstream and is shippable; the upstream-divergence half is blocked on a read-only credential for a private repo, and the Testing Standard's freshness clause forbids gating a check that cannot establish its own baseline

**Source:** issue #55

**Routing note, for `triage-candidates`.** This reads as a proposed amendment to the TEXT of a named standard, which [§1](../../docs/standards/documentation/tracked_items_standard.md) routes to `tracked/standards/` rather than here. **It was not moved during the migration**: an id is immutable (§2), a prefix change is an id change, and this id may be cited elsewhere in the planning corpus. Rule on it — if it moves, mint a fresh `S-` id, carry the reasoning, and leave a pointer here.

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
