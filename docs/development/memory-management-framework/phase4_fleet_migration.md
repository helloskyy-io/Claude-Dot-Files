# Phase 4 — Migrate the fleet

**Component:** [Memory Management Framework](roadmap.md) · **Status: not started**

Takes the record [Phase 3](phase3_typed_exit_record.md) proved on one pair and rolls it across every child, retires prose parsing as a routing input, and lands the envelope observables the sprint milestone named.

**This phase spans two fleets and includes prompt text.** An earlier draft of this plan claimed it changed no prompt content at all; that was verified false and is corrected below. The verdict and the findings are model-authored, so the instruction to emit the typed record is prompt-borne — and the `pr_review:` wire format already lives inside the prompt strings.

---

## Requirements for completion

Done when all of the following hold:

1. **No parent branches on a value parsed out of prose, in either fleet.** Every routing input is a field in the typed record.
2. **The record's schema is declared per [Phase 3](phase3_typed_exit_record.md)'s cross-language ownership ruling**, with a test that catches a second declaration — including one introduced across the bash/Python boundary.
3. **Every prompt whose return-contract section changes is enumerated and edited**, and a check verifies each prompt's emit instruction still corresponds to the field the parent reads.
4. **`is_error` and `num_turns`-against-cap are resolved** — routed per Phase 3's composition rule, **or** closed as a no-op against **their own** measurement in [Phase 1](phase1_measure_the_channel.md) E1. Each closes on its own evidence; neither closes on the other's.
5. **`permission_denials[]` is recorded and surfaced on every run** regardless of any routing ruling. It is safety observability, not a routing option, and it **cannot** be closed as a no-op — see the [roadmap's Key Decision](roadmap.md#key-decisions).
6. **The anchored PR-URL validation survives the migration** as a validator on the field, not as a regex deleted along with the extraction.
7. **Kind 1's readers see no change**, verified fleet-wide against [Phase 2](phase2_kind1_framework.md)'s consumer list.
8. **A `§Capability Parity` audit is recorded.** This phase replaces a working mechanism; the parity discipline is adopted here for that reason.

---

## Dependencies

- **[Phase 3](phase3_typed_exit_record.md) — hard.** The schema, the channel properties, the fail-safe contract and the shadow-agreement data all come from it. Migrating before the design is proven is migrating a guess. Phase 3 also already lands the single-child rendering and archive work, so this phase's Kind 1 obligation is *fleet-wide verification*, not a second rendering design.
- **[Phase 2](phase2_kind1_framework.md) — hard.** The consumer list is what requirement 7 is verified against. Without it, verification degrades to "standup still seemed to work."
- **[Phase 1](phase1_measure_the_channel.md) E1** decides whether requirement 4 is work or a documented no-op.
- **A ruling this phase cannot make alone — settle it before sequencing.** [Temporal Integration](../temporal-integration/temporal-integration.md) carries *"what happens to the bash fleet after Stage A — retired, or kept as an edge fallback"* as an open question while being gated on this phase. If bash is retiring, its half of this migration is throwaway; if it is staying, skipping it makes requirement 1 false for the fleet in daily use and the gate unopenable. **Do not schedule this phase until that is answered.**
- **Unblocks:** [Temporal Integration](../temporal-integration/temporal-integration.md) — the handoff shape stops moving here.

---

## §Runtime Verification

Adopted practice — see the [roadmap's note on doc shape](roadmap.md).

- [ ] Re-run [Phase 1](phase1_measure_the_channel.md#runtime-verification)'s block and record version, date and host here. This phase touches every child, so CLI drift between Phase 3 and this phase lands fleet-wide
- [ ] Re-run every enumeration below against the live tree rather than trusting the counts. They were taken on 2026-08-07 and the fleet changes

---

## The migration surface, enumerated as of 2026-08-07

| Surface | Count | What changes |
|---|---|---|
| Bash workflows declaring a `COMPLETION_PATTERN` | 11 (10 PR-URL-shaped, 1 `^VERDICT:`) | The completion contract gains the typed record; the final line stays as the human-facing signal |
| **Python workflows declaring a `COMPLETION_PATTERN`** | **10** | Same. Written `COMPLETION_PATTERN = r"…"` **with spaces** — invisible to a `COMPLETION_PATTERN=` grep |
| Bash parents parsing the verdict from prose | **2** (`build.sh:277`, `build-minor.sh:281`) | `build.sh` is migrated in [Phase 3](phase3_typed_exit_record.md); `build-minor.sh` is this phase's |
| Bash call sites extracting a PR URL by anchored regex | 2 (`build.sh:198`, `build-minor.sh:202`) | Read the field — **and keep the regex as a validator on it** |
| Python extraction helpers | `assistant_activities.py:233`, `build/build_helper.py:30`, re-exported at `plan/plan_activities.py:30` | One implementation behind one name |
| Python routing vocabulary | `assistant/routing.py:24-56`, re-exported at `review_pr/review_pr_helper.py:67` | Extended in place, not duplicated |
| **Prompt text carrying the return contract** | **Non-zero, in both trees** | `children/review-pr.sh:427` is a stage titled *"PRINT THE VERDICT"*; `children/build-draft.sh:374` instructs *"As your FINAL line, print the PR URL"*; the `pr_review:` wire format is specified inside `review-pr.sh` and again in the Python tree's `disposition.md`. Enumerate and edit |

**Use language-agnostic patterns.** `grep -rnE "COMPLETION_PATTERN\s*="` finds all 21; `grep -rn "COMPLETION_PATTERN="` finds 11 and silently reports the bash fleet as the whole fleet. The same applies to `extract_pr_url` and to any prose-parse sweep. **The first draft of this plan made exactly this mistake and undercounted the surface by half** — the note is here because the failure is easy and quiet.

---

## Implementation steps

### 1. Migrate the emitters, including their prompts

- [ ] Enumerate every prompt section that states a return contract, across both trees, before editing any of them. This is the surface the plan previously sized at zero
- [ ] Edit each so the child is instructed to emit the typed record per [Phase 3](phase3_typed_exit_record.md)'s authorship ruling, and so the `pr_review:` wire format stated in-prompt matches the schema
- [ ] Add a check that the prompt's emit instruction corresponds to the field the parent reads — a prompt edit that drops a field is invisible to a schema test, because the schema is still fine and the producer simply stopped filling it
- [ ] Every child writes the typed record at exit on the channel Phase 3 specified, with its freshness, run-identity and outside-the-worktree properties intact
- [ ] The schema is declared per the cross-language ownership ruling, with the test that catches a second declaration. This repo has already paid for a duplicated routing enum once, where the copy deciding whether a PR merges had zero tests while its twin had twenty — and an intra-tree test would not have caught a bash/Python divergence
- [ ] Each child's `COMPLETION_PATTERN` continues to guard against the headless early-stop failure it exists for. **The typed record does not replace the completion contract** — one proves the run finished, the other says what it decided, and collapsing them loses the first

### 2. Migrate the consumers

- [ ] Each parent in both fleets reads its routing values from the record. The prose parse is retained as a shadow, exactly as in Phase 3, until this phase's agreement data supports removing it
- [ ] **BEFORE the second parent copies the shape: extract the pure half of `review_pr_workflow.run_review` into `review_pr_helper`.** [Phase 3](phase3_typed_exit_record.md) added roughly forty lines of `ExitRecord`-to-string logic — the shadow-disagreement comparison and its message, the three record-derived notes, and the finding-set comparison and its two messages — directly into the workflow layer, against that file's own binding docstring (*"Every decision below comes from the helper; every side effect is an activity"*). It was left in place deliberately: with **one** parent the misplacement costs only that five otherwise-pure tests run through a monkeypatch harness, and refactoring the file this phase is about to rework would have been churn. **This checkbox is the trigger.** The moment a second parent routes on a record, the choice is re-typing that prose or reaching into a workflow module for it — which is the duplicated-vocabulary defect the whole component exists to remove. **FIVE** pure functions, each returning the operator-facing message or `None`; the existing tests assert message text via `pytest.raises(match=…)`, so the strings move byte-identical. *(Three at Phase 3; [Phase 5](phase5_convergence_stopping.md) added `_convergence_notes` and `_thread_unreadable_note` to the same layer for the same reason and left them there under the same trigger. Extracting three and leaving two is the half-fix this count exists to prevent.)*
- [ ] **If this phase migrates NO second consumer of `modules/assistant/exit_record.py`, move it to `review_pr/`.** [Phase 3](phase3_typed_exit_record.md) placed it at the `assistant/` parent level with **one** consumer, which is a stated deviation from §10.1 rule 3 (a module promotes on consumer count, never on taste) and not a claim of conformance. **This checkbox is where that deviation expires.** Its expiry condition was written into Phase 3's prose, and prose in a completed phase is not a trigger anybody re-reads — so the deviation would have survived by default rather than by decision, and an honest deviation becomes an unmarked violation the moment nobody is left who remembers it was one. Rule it either way here; do not leave it unruled
- [ ] **Select this pass's `pr_review:` block by the run nonce rather than by position.** The parent already issues a `run_id` and rule R5 compares it, but the block carries no `run_id` field, so the inference is still positional: ordering plus a posted-count delta. **The change site is `review_pr_helper._this_pass_index`**, which [Phase 5](phase5_convergence_stopping.md) added precisely so there is ONE site: it returns *which* block is this pass's, and `this_pass_block` and `prior_pass_blocks` are both derived from it, so the complement cannot keep selecting by position after the selection becomes an identity check. `latest_pr_review_block` (which this checkbox used to name) is a projection over the same accessor rather than the place the inference lives. *(The first collapse declared `this_pass_block` alone and left three sites — `_assert_block_matches_record`'s inline `blocks[-1]` and `prior_pass_blocks`' own `window[:-1]`, the complement being the one hardest to count. `test_selecting_from_the_END_of_a_sequence_happens_only_where_it_is_owned` now gates the SHAPE across the whole `review_pr/` package, so a fourth site fails rather than being found by a later pass; both re-derivations were mutated back in and both turn it red, while the behavioural test stays green on one of them.)* Phase 3 closed the reachable half of that (a comment quoting the block it supersedes returned the superseded one; fixed with `finditer`), and what remains is a genuine race: a third party posting a fenced `pr_review:` example between the child's comment and the parent's read. **This belongs here and not in Phase 3 because the remedy is not small** — a schema field, a prompt change in `disposition.md`, a parser and a gate — and this is the phase that already owns the fleet-wide addressing sweep. It turns an inference into an identity check, which is what `review_pr_workflow`'s invariant docstring is actually trying to assert
- [ ] `build-minor.sh` is migrated here — it is the lighter and more frequently used of the two build parents, and requirement 1 is false while it still greps prose
- [ ] The PR URL becomes a field — **and the anchored pattern is retained as a validator on that field.** The current regex (`https://github\.com/[^ )]+/pull/[0-9]+`) is not merely an extraction: it pins the host and guarantees the derived PR number is digits, and that value flows into `gh pr view`, `gh pr checks` and `--pr` on downstream children. `gh` accepts a URL wherever it accepts a number, so an unvalidated `pr_url` field naming a different repository makes the parent act on a PR the child chose. This needs no adversarial child — children are instructed to read prior PR comments, which routinely contain other PRs' URLs. A field failing the pattern routes to the human arm
- [ ] Remove the prose parse only after the shadow has agreed across a stated run count, and record that count here. **Removing it on the strength of the design rather than the data is the failure this phase is structured to avoid**
- [ ] Verify no remaining prose parsing of routing values exists in either tree: `grep -rnE "grep -oE|re\.search|re\.compile" scripts/workflows/` and account for every hit

### 3. Resolve the envelope observables — separately

- [ ] **`is_error`:** route through Phase 3's ordered-rules contract, or close as a no-op citing E1's measurement of `is_error` specifically
- [ ] **`num_turns`-against-cap:** same, against E1's measurement of `num_turns` specifically
- [ ] **`permission_denials[]`:** record and surface on every run. **No no-op path exists for this one.** Under `--dangerously-skip-permissions` the safety hook is the only control operating inside a headless run, a denial does not fail the run, and the array is the only trace it left. `grep -rn "permission_denial" scripts/` returns nothing today. Per Phase 3's contract, a non-empty list routes to the human arm and never to automatic redispatch
- [ ] Record what the `system/api_retry` error enum is used for, or state explicitly that it is read by nothing and why that is acceptable
- [ ] Whichever outcomes: state that class-(i) routing in this fleet rests on an **undocumented exit-code mapping**, and record the mapping Phase 1 measured as this fleet's own table with its measurement date. A measured table with a date is honest; an assumed one is the thing being fixed

### 4. Verify Kind 1 fleet-wide

The rendering and archive design lands in [Phase 3](phase3_typed_exit_record.md) on the single proven pair. This phase's obligation is that it still holds once every child is migrated.

- [ ] Verify against [Phase 2](phase2_kind1_framework.md)'s consumer list that every reader of every Kind 1 surface still reads what it needs, for every migrated child
- [ ] Verify the publish classification holds fleet-wide — no migrated child publishes a field Phase 3 classified `internal`
- [ ] Verify the retrievability convention survives the migration, so a correction pass can still address a prior pass's record

### 5. Capability parity

- [ ] Enumerate every behaviour of the prose-channel arrangement being replaced — not just the headline. Fail-closed on absence; last-match-wins so a run quoting a previous verdict does not route on its own history; the anchored pattern so prose mentioning a token cannot match; the anchored PR-URL validation; loud failure on a missing completion signal; the human-readable final line an operator reads in a terminal
- [ ] Map each to **ported** (cite where) or **consciously dropped** (named, with operator sign-off and a one-line rationale). A behaviour that is neither is a parity gap that blocks completion
- [ ] Include the prompt-to-field correspondence from step 1 as a parity line item — a model-authored field is a behaviour of the prompt, and the audit must cover it or it covers only the plumbing
- [ ] Record the audit as a `§Capability Parity` table in this doc and post it alongside the QC dispositions

### Close-out

- [ ] Every requirement above met, with evidence in this doc
- [ ] The shadow-agreement run count is recorded, and the prose parse's removal is justified by it
- [ ] The standards-amendment candidate on `§ Composition` is now supported by a proven replacement — surface it for ratification in the [roadmap](roadmap.md#standards-amendment-candidates); **do not write it**
- [ ] Confirm [Temporal Integration](../temporal-integration/temporal-integration.md) can proceed: the handoff shape is fixed, and say so here so the gate is checkable rather than inferred

---

## Notes and gotchas

- **Consider splitting this phase by consumer if the bash-fleet ruling allows it.** Requirement 1 — no parent branches on prose — is satisfied by `build.sh`, `build-minor.sh` and `review-pr` alone. The other PR-URL children have no code parent today; their final line is read by `run-claude.sh`'s completion check and by a human. Migrating them anyway buys uniformity and forward compatibility at the cost of bundling speculative work into the phase that gates Temporal Integration. Both are defensible; **the choice should be made deliberately rather than inherited from the phase's title.**
- **The two-declaration failure is the one this repo has already had**, and the fleet-wide migration is exactly the situation that reintroduces it — hence the test in step 1, and hence the cross-language ruling in Phase 3 rather than a per-tree rule that cannot see the other tree.
- **Do not let a refactor move aggregation into the parent.** The child derives its verdict from its own findings and states it; a parent re-deriving one is a caller with no stake making a judgement about the child's judgement. This is correct in the shipped code today and the migration must keep it correct.
- **Migration breadth is not migration risk, but the enumeration is.** The mechanical change is repetitive; what would actually break this phase is a call site nobody enumerated — or a grep whose pattern only matches one of the two fleets.
