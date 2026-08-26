---
id: C-kosp0o61
title: A durable store for Kind 2 records, so a typed record can outlive its invocation
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**Phase 5 is the first consumer that needs one, and it works around the absence rather than solving it.** Its predicate compares this pass's findings against every prior pass's; the current pass comes from the TYPED exit record, but a prior pass's typed record no longer exists — a Kind 2 record's lifetime is one parent invocation ([`exit-protocol.md` §1](../../exit-protocol.md), and Phase 3's to-do-bit ruling). So prior terms are parsed out of the durable `pr_review:` block as prose, inside the component built to stop routing on parsed prose. **Re-verified as a PROPOSAL:** the workaround is SOUND, not broken — the render↔record invariant makes this pass's block and this pass's record carry identical `(id, disposition)` pairs, so the prose term is a faithful copy of what the typed term was. Nothing is wrong today. **Consequence of leaving it:** every future cross-pass consumer re-implements the same prose parse, and each one re-decides which fields survive the round trip. Phase 5 needed two of the eleven envelope fields; the third consumer may need one the block does not carry, and will discover that after building. **Not an expansion of C-w41xgeei or C-rrm2t4sj:** those are about a record that arrives wrong or a check that could not run; this is about a record that arrived correctly and then ceased to exist. **No done-state today, deliberately:** a durable Kind 2 store is a component-sized decision — where it lives, how it is keyed, how long it is kept, whether Temporal's event history already is one — and [Temporal Integration](../../../development/temporal-integration/temporal-integration.md) is gated on this component rather than the reverse, so it cannot be settled here. It is a candidate precisely because nobody should build it from inside a phase **Lens verdicts (`finding-routing.md` §5 gate 4).** `/decide`: DEFER-TO-TEMPORAL — the five-whys bottoms out at *no component owns durable Kind 2 storage*, and Temporal Integration's event history may already be one; deciding this from inside a phase whose own component gates that integration would be choosing a store before knowing whether one exists. `/best-practices`: durable execution engines persist activity results as event history precisely so a later step can read an earlier one's output, so the industry answer is *do not build a second store beside the workflow engine*. Both say: do not build now, re-ask when Temporal Integration is planned — which is the trigger this row is waiting on.

**Source:** PR #75

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
