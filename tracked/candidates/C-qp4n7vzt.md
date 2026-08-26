---
id: C-qp4n7vzt
title: The run log's admission rule accepts an observable whose rate DECIDES NOTHING, so the next telemetry field will pass the gate the same way `run_resources` failed it
status: open
count: 1
filed: 2026-08-26
filed_by: plan-verify
component: persistent-memory-protocol
size:
decision:
---

**PROPOSAL — a clause that does not exist, not a defect in one that does.** Phase 6 built exactly what it specified and every artifact it names is real. What is missing is capability: the admission clause it wrote stops one failure mode and not the one its own Kind-3 ruling identifies.

**The rule as written.** [Phase 6 § 4 Clause B](../../docs/development/memory-management-framework/phase6_read_what_it_writes.md) admits a new run-log observable on **"a reader in the same change or a placed candidate with a named trigger."** It exists because `run_resources` shipped with neither, which is the finding the phase was created against.

**Why a reader is one level short.** The same phase's Kind-3 ruling turns on a single property, and states it as the thing that separates Kind 3 from the other two: *"for Kind 1 and Kind 2 alike the unit of meaning is the RECORD; for this one it is the POPULATION"* — the row in its own table reads **"decides nothing alone; a rate decides."** So for a Kind 3 member the thing that makes it memory rather than exhaust is that the **rate feeds a decision**. The admission rule checks for a reader, and a reader that emits a correct figure nobody rules on satisfies it completely.

**Measured against the three members that exist, which is what makes this a real gap rather than a tidy one:**

- `parent_route` → `replay_parent_route.py` → the rate feeds **shadow removal**, a named decision. Phase 6 closed that box. **Decides something.**
- `convergence` → `replay_convergence_events.py` → the rate feeds the **operator's ruling to enable the predicate**, with conditions 1 and 2 printed and a trigger. **Decides something.**
- `run_resources` → `replay_run_resources.py` → four figures, each with its denominator and its cutover. **Decides nothing, and the same phase is why.** Its requirement 4 rules that no ceiling is introduced and records the operator's acceptance of the uncapped aggregate; the 2026-08-10 outage cause "remains UNIDENTIFIED"; and figure 4 — the one the phase calls *"the only one of the four that speaks to the failure that produced the instrument"* — has no decision with a trigger waiting on it. The `resource_limits:` comment in `config.yaml` is a **placement for a future cap author**, not a consumer.

**Consequence if this is not closed.** The next observable added to the run log ships a correct reader, passes Clause B, produces a figure with a denominator, and feeds nothing — which is `run_resources`'s original failure one level up, arriving through the gate built to stop it. The failure is *quieter* than the one Phase 6 caught, because a reader exists and the surface looks complete.

**Proposed action.** Extend Clause B's admission test from *a reader* to *a reader plus the decision its rate feeds, or a named trigger for that decision*, and state the third arm the current rule already implies but does not offer: an observable whose rate will decide nothing is **not admitted** — the deletion arm requirement 3 already uses. The clause is drafted but unratified today: it lives as [roadmap candidate 10's `memory-model.md` §2.7 payload](../../docs/development/memory-management-framework/roadmap.md), which is where the amendment would land, so the cost is a clause in a block an operator has not yet merged rather than an edit to a shipped standard.

**Not an expansion of [[C-73bf2gvm]].** That asks for the record types, their stores and their wire formats to be **researched and designed as a set**, and names OpenTelemetry's metrics model as the unopened prior art. This is one specific, checkable clause in the growth rule that already shipped, with a counter-example among the three members that exist. Merging it into a whole-protocol research request buries a defect that can be fixed in a sentence under work that has not been commissioned — and C-73bf2gvm's own design would still have to answer it.

**Not [[C-skkjo6jn]].** That asks why the instrument cannot say *when* a spike happened — a retention question about the payload. This asks what any of the figures **decide**, and it would still stand if the series were added tomorrow.

**Source:** `plan-verify` cold read of `docs/development/memory-management-framework`, 2026-08-26. Component named as `persistent-memory-protocol` because MMF is retired and PMP absorbed the framework and the surfaces with it.
