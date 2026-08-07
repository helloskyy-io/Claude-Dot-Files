# Phase 4 — Migrate the fleet, and archive the record as a by-product

**Component:** [Memory Management Framework](roadmap.md) · **Status: not started**

Takes the record [Phase 3](phase3_typed_exit_record.md) proved on one pair and rolls it across every child, retires prose parsing as a routing input, lands the envelope observables the sprint milestone named, and makes the durable `pr_review:` block a **copy** of the exit-channel record rather than an independently composed second write.

**This phase is smaller than the call-site count suggests, and the plan should say so.** The change is a signature change at the boundaries plus one declaration point per language tree. **It changes no prompt content at all** — what a child is *told to do* is unaffected by what it *returns*, and the workflow scripts' 428 KB is overwhelmingly prompt text this phase does not open.

---

## Requirements for completion

Done when all of the following hold:

1. **No parent branches on a value parsed out of prose.** Every routing input is a field in the typed record.
2. **The record's schema is declared in exactly one place per language tree**, and a test asserts no second declaration exists.
3. **The envelope observables are resolved** — `is_error`, `permission_denials[]` and `num_turns`-against-cap are read and routed per Phase 3's composition rule, **or** this doc records that [Phase 1](phase1_measure_the_channel.md) E1 proved them redundant and closes the milestone as a no-op with the measurement attached. Both are acceptable outcomes; leaving it unstated is not.
4. **The durable `pr_review:` block is produced from the typed record**, and either the human disposition table is rendered from it or a write-time invariant reconciles the two before the comment posts.
5. **Kind 1's readers see no change.** `/standup` and `review-pr` are verified against the migrated block, against the consumer list [Phase 2](phase2_kind1_framework.md) produced.
6. **A capability-parity audit is recorded** — this phase replaces a working mechanism, and [Documentation Standard § Capability-Parity Gate](../../standards/documentation/documentation_standard.md) binds it.

---

## Dependencies

- **[Phase 3](phase3_typed_exit_record.md) — hard.** The schema, the fail-safe contract and the shadow-agreement data all come from it. Migrating before the design is proven is migrating a guess.
- **[Phase 2](phase2_kind1_framework.md) — hard.** The consumer list is what "Kind 1's readers see no change" is verified against. Without it, verification degrades to "standup still seemed to work."
- **[Phase 1](phase1_measure_the_channel.md) E1** decides whether step 3 is work or a documented no-op.
- **Unblocks:** [Temporal Integration](../temporal-integration/temporal-integration.md) — the handoff shape stops moving here. Its `claude_cli` activity domain and its `review-runs` port both consume this shape.

---

## §Runtime Verification

- [ ] Re-run [Phase 1](phase1_measure_the_channel.md#runtime-verification)'s block and record version, date and host here. This phase touches every child, so a CLI drift between Phase 3 and this phase would land fleet-wide
- [ ] Re-confirm the enumeration of migration targets against the live tree at the time this phase starts, rather than trusting the counts below. They were taken on 2026-08-07 and the fleet changes

---

## The migration surface, enumerated as of 2026-08-07

| Surface | Count | What changes |
|---|---|---|
| Workflows declaring a PR-URL `COMPLETION_PATTERN` | 10 | The completion contract gains the typed record; the URL stays as the human-facing final line |
| Workflows declaring the `^VERDICT:` pattern | 1 (`children/review-pr.sh`) | Already migrated by [Phase 3](phase3_typed_exit_record.md) |
| Bash call sites extracting a PR URL by regex | 2 (`build.sh:198`, `build-minor.sh:202`) | Read the field instead |
| Bash call sites parsing the verdict from prose | 1 (`build.sh:281`) | Already migrated by [Phase 3](phase3_typed_exit_record.md) |
| Python extraction helpers | `assistant_activities.py:233`, `build/build_helper.py:30`, re-exported at `plan/plan_activities.py:30` | One implementation behind one name |
| Python routing vocabulary | `assistant/routing.py` — **one declaration, three consumers** | Extended in place, not duplicated |
| Prompt content | **0 bytes** | A child's instructions do not mention what it returns to its caller |

**Verify these counts before acting on them** — `grep -rn "COMPLETION_PATTERN=" scripts/`, `grep -rn "grep -oE 'https://github" scripts/`, `grep -rn "extract_pr_url" scripts/`. A migration planned against a stale enumeration silently skips whatever was added since.

---

## Implementation steps

### 1. Migrate the emitters

- [ ] Every child writes the typed record at exit on the channel Phase 3 established, alongside its existing final-line output
- [ ] The record's schema is declared once per language tree and imported everywhere else. Add a test that fails if a second declaration appears — this repo has already paid for a duplicated routing enum once, where the copy deciding whether a PR merges had zero tests while its twin had twenty
- [ ] Each child's `COMPLETION_PATTERN` continues to guard against the headless early-stop failure it exists for. **The typed record does not replace the completion contract** — one proves the run finished, the other says what it decided, and collapsing them loses the first

### 2. Migrate the consumers

- [ ] Each parent reads its routing values from the record. The prose parse is retained as a shadow, exactly as in Phase 3, until this phase's agreement data supports removing it
- [ ] The PR URL becomes a field rather than a regex extraction at each of the enumerated call sites
- [ ] Remove the prose parse only after the shadow has agreed across a stated run count, and record that count here. **Removing it on the strength of the design rather than the data is the failure this phase is structured to avoid**
- [ ] Verify no remaining prose parsing of routing values exists anywhere: `grep -rnE "grep -oE|re\.search|re\.compile" scripts/workflows/` and account for every hit

### 3. Land the envelope observables

- [ ] Read `is_error`, `permission_denials[]` and `num_turns`-against-cap from the result envelope, and route them through Phase 3's ordered-rules contract — **or** record Phase 1 E1's finding that they add nothing the propagated exit status does not, and close the milestone as a no-op with the tuple table cited
- [ ] Whichever outcome: state that class-(i) routing in this fleet rests on an **undocumented exit-code mapping**, and record the mapping Phase 1 measured as this fleet's own table with its measurement date. A measured table with a date is honest; an assumed one is the thing being fixed
- [ ] Record what the `system/api_retry` error enum is used for, or state explicitly that it is read by nothing and why that is acceptable

### 4. Archive as a by-product, not a second write

- [ ] The `pr_review:` block posted to the PR becomes a copy of the exit-channel record, not an independent composition. One author, two copies, two lifetimes
- [ ] Either render the human disposition table from the typed record (preferred — one source), or, if co-authoring persists, add the write-time invariant: every table row has a matching finding id in the record and vice versa, checked **before** the comment posts. Today they are two prose regions written in one act with no declared precedence, which is the one thing none of the surveyed instances of that arrangement permit
- [ ] Whichever is chosen, **declare that the typed region wins** — no source lets the prose region carry semantics
- [ ] Verify against [Phase 2](phase2_kind1_framework.md)'s consumer list that every reader of the block still reads what it needs. `/standup` in particular parses this block and must be checked, not assumed

### 5. Capability parity

- [ ] Enumerate every behaviour of the prose-channel arrangement being replaced — not just the headline. Fail-closed on absence; last-match-wins so a run quoting a previous verdict does not route on its own history; the anchored pattern so prose mentioning a token cannot match; loud failure on a missing completion signal; the human-readable final line an operator reads in a terminal
- [ ] Map each to **ported** (cite where) or **consciously dropped** (named, with operator sign-off and a one-line rationale). A behaviour that is neither is a parity gap that blocks completion
- [ ] Record the audit as a `§Capability Parity` table in this doc and post it alongside the QC dispositions, per the binding gate

### Close-out

- [ ] Every requirement above met, with evidence in this doc
- [ ] The shadow-agreement run count is recorded, and the prose parse's removal is justified by it
- [ ] The standards-amendment candidate on `§ Composition` is now supported by a proven replacement — surface it for ratification in the [roadmap](roadmap.md#standards-amendment-candidates); **do not write it**
- [ ] Confirm [Temporal Integration](../temporal-integration/temporal-integration.md) can proceed: the handoff shape is fixed, and say so in this doc so the gate is checkable rather than inferred

---

## Notes and gotchas

- **The two-declaration failure is the one this repo has already had.** The Python routing module exists because the vocabulary was typed twice, byte-identical, and the untested copy was the one deciding merges. A fleet-wide migration is exactly the situation that reintroduces it — hence the test in step 1, not just the intention.
- **Do not let a refactor move aggregation into the parent.** The child derives its verdict from its own findings and states it; a parent re-deriving one is a caller with no stake making a judgement about the child's judgement. This is correct in the shipped code today and the migration must keep it correct.
- **Migration breadth is not migration risk, but the enumeration is.** The mechanical change is small and repetitive; what would actually break this phase is a call site nobody enumerated. Re-run the greps rather than trusting the table above.
