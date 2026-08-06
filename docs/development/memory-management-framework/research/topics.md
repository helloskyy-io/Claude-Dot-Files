# Topic assessment — memory-management-framework

**Last assessed:** 2026-08-06
**Complexity tier:** **Small** (§2 band: single-concern component, bounded integration — 1–2 topics)
**Topic count this cycle:** **2**
**Cycle:** 1 (first pool for this component)

---

## Why Small, and why two

The destination is one not-yet-written phase doc — `docs/development/memory-management-framework/memory-management-framework.md` — behind the sprint item `## Sprint: Memory Management Framework`, which names five milestones. **Three of the five are already decided by verified evidence in the product pool**, so they need citations, not papers:

| Sprint milestone | Already answered upstream by | Verdict |
|---|---|---|
| **Read the result envelope; gate on `is_error`** | `claude_code_integration_surface.md` §5, §7, §8 — the `result` message's field list (`is_error`, `subtype`, `num_turns`, `permission_denials[]`), the `system/api_retry` `error` enum, and a five-class failure taxonomy with dispositions | **Answered.** The phase doc can specify this from the existing paper. No new topic. |
| **Research the payload contract** | `code_routed_control_flow.md` §2.4.1 (Tekton 4 KB, Argo 1 MB + `@filename` offload, Airflow "small amounts of data"), P4, and §2.4.2 (TEP-0074 withdrew a rich typed handoff object for coupling and conceptual opacity) | **Answered, and more sharply than the sprint item states it.** The references-not-payloads lesson is verified first-party. No new topic. |
| **Convergence-based stopping** | `convergence_stopping.md` — P11 (Class A/E detection *requires* typed comparable finding records), §5.1–5.7 (the case against a naive "no new findings" rule: infinite-loop risk, oscillatory attractors, adaptive bias, hallucinating reviewers never emitting an empty pass) | **Answered.** Depends on the typed channel existing; the stopping rule itself is settled evidence. No new topic. |

What upstream does **not** answer is the pair of questions the sprint item's remaining two milestones actually turn on, and each gets one topic.

---

## Topic table

| Topic | Feeds | Paper |
|---|---|---|
| **`dual_channel_outcome_records`** — when one unit of work must leave both a durable human-readable record and a typed machine-readable record, how do production systems relate the two? Derived, dual-authored, or one-source-two-renderings — and what drifts | The phase doc's Kind 1 ↔ Kind 2 relationship decision, and the **"Document Kind 1 as a framework"** milestone (what Kind 1 must expose for Kind 2 to reference it) | `raw/dual_channel_outcome_records.md` |
| **`non_model_observables`** — which parts of a parent's routing decision can be taken from values the model did **not** author (process exit status, `is_error`, an empty diff, a finding-set delta, a liveness probe), and what prior art exists for routing on them across process boundaries | The phase doc's **"Design it"** milestone — specifically the fail-safe contract and the split between what the verdict asserts and what the run demonstrates; also gates **"gate on `is_error`"** (which is exactly one such observable) | `raw/non_model_observables.md` |

Both topics were selected because `code_routed_control_flow.md` **names them as the two things it did not settle**, not because they are interesting:

- Its §0 finding 3(a)/(b) reduces the defensible novelty to two narrower readings — cross-process altitude, and *"routing on values the model did not author"* — and N6 records that no located agent-framework doc presents a non-model value carrying real work product as its canonical branching example. That is topic 2's whole warrant.
- Its §2.4 worked CI/CD as *routing* prior art (caps, deprecation, total functions). It did **not** ask how those systems keep a human-durable record and a typed channel over the same work from diverging. That is topic 1's whole warrant.

---

## Deliberately NOT commissioned this cycle

Each of these was considered and rejected with a reason, so a later cycle does not re-derive the decision.

- **"Is code-routing over typed results the right pattern, and is it novel?"** — settled upstream. `code_routed_control_flow.md` (last validated 2026-08-03, `PASS-WITH-FIXES` round 3): the pattern is the field's convergent middle (P1, five first-party sources), is ~decade-old outside agents (P3), and **is ordinary as the problem statement words it** (§6.6). Re-running it would produce a second answer that can drift from the first.
- **"What does a typed channel buy when the producer is an LLM?"** — settled upstream, and the operator's stated belief is *partly* confirmed and *partly* corrected there. §4.1 (enum values are protected at the decoder), §4.2 (*"Structured Outputs can still contain mistakes"*), §4.4 (the abstention arm is predicted to be **under-used**, unmeasured — N5), P9. The residual open question is not "does typing help" but "what can we route on that the model did not assert" — which is topic 2.
- **"Can `claude -p` emit a validated typed value at all?"** — documented upstream: `claude_code_integration_surface.md` §1 records `--json-schema` with `--output-format json` producing a validated `structured_output` field (v2.1.205+). Topic 2 may cite it; it does not re-establish it. **Note for the next cycle:** that paper's own header carries `Last validated: 2026-07-25 · Revalidate: high — 4 weeks`, so it comes due around 2026-08-22 and it is a **product-pool** paper — a component run may not refresh it.
- **Payload sizing and wire-format caps** — settled upstream (P4, §2.4.1). The design consequence (*carry references into git, not copies*) is a citation, not a research question.
- **Schema evolution across independently-versioned producers and consumers** — upstream P12 (Temporal's nondeterminism error on changed definitions) and §2.4.2 (TEP-0074) establish it as a documented hard problem with a documented retreat. **Deferred as a topic**, not answered: our specific version-skew question — a parent on `main` reading a child's envelope written by a worktree on an older revision — is a *design* question the phase doc must rule on, and it has enough upstream evidence to rule with. Revisit only if the phase doc cannot decide it.
- **A separate topic on documenting Kind 1** — Kind 1 is built and in use; writing it down is an authoring task, not a research question. What research owes it is the *interface* Kind 2 needs from it, which topic 1 covers.
- **Verdict-vocabulary design (the closed enum itself)** — the product synthesis's §4 de-confliction table already identifies OpenClaw's `structured_output` + schema-per-call and Hermes' `done`/`continue`/`wait` as **one vocabulary decision**, and names this component as one of its two destinations. Evidence exists; the ruling is the phase doc's.

## Per-cycle capacity

§2 caps a cycle at ~5 topics. This cycle uses 2 and leaves headroom deliberately — not because more work is queued, but because the pool's job here is to close the two open questions rather than to reach a band. **If the phase doc can be written after this cycle, no cycle 2 is warranted**, and the correct outcome is no further research.
