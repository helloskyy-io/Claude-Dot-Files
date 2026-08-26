---
id: C-abieu0fg
title: A per-leg count of tests that actually EXECUTED, so a leg cannot report green having run nothing
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**`mutate.sh` accepts pytest's exit 0 as GREEN on all three legs, and an all-skipped run exits 0 having executed no test.** On leg 2 that is harmless — both readings land on "THE GUARD DID NOT FIRE", a refusal to certify. On legs 1 and 3 it is not. Leg 1 exists to establish *the guard is green before it is meaningful* and leg 3 to prove *green again, so the tree restored*; an all-skipped leg establishes neither and is accepted anyway. **Measured on this PR, not reasoned**: a subject whose tests skip while it is pristine and run once mutated yields leg 1 = nothing ran, leg 2 = RED, leg 3 = nothing ran, and the harness prints `✓ MUTATION DEMONSTRATED` over two legs that executed no test at all. **Proposal, not defect** — the behaviour is unchanged from `main` and predates the exit-2 work entirely; what PR #74 added was an exit-code table asserting this ambiguity was already closed, and that sentence is corrected in the same PR. What does not exist is the mechanism: **no pytest exit code carries an executed-test count**, so closing it means leaving the exit-code channel for a structured one (`--junitxml`'s `tests`/`skipped` attributes are the obvious candidate) and changing `run_leg`, which the PR #74 disposition placed explicitly out of scope. **Not filed as an issue** — it is capability that does not exist and would be added, and per [`finding-routing.md`](../../finding-routing.md) § 4 that makes it a candidate whatever its done-state looks like. **Not an expansion of an existing row**: no row covers `mutate.sh`, and the nearest neighbour — the `cpi-decisions.md:1125` entry on `mutate.sh` being pytest-only — is about which *frameworks* a leg can drive, not about whether a leg that ran can be told from one that did not. **Cost of leaving it:** the harness's own headline verdict rests on two legs it does not verify ran, in the one tool whose entire premise is refusing to certify what did not run.  *(Renumbered from C-45bhs5cm on 2026-08-11 — that ID was taken by an unrelated proposal on `main` while this branch was open.)*

**Source:** PR #74

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
