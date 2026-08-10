# Phase 4 — Migrate the fleet

**Component:** [Memory Management Framework](roadmap.md) · **Status: not started** · **Scope: the V2 Python tree only (re-cut 2026-08-10)**

Takes the record [Phase 3](phase3_typed_exit_record.md) proved on one pair and rolls it across every child **in the V2 Python tree**, retires prose parsing as a routing input **there**, and lands the envelope observables the sprint milestone named.

**This phase includes prompt text.** An earlier draft of this plan claimed it changed no prompt content at all; that was verified false and is corrected below. The verdict and the findings are model-authored, so the instruction to emit the typed record is prompt-borne — and the `pr_review:` wire format already lives inside the prompt strings.

---

## The scope ruling that re-cut this phase, and the blocker it dissolved

**RULED BY THE OPERATOR, 2026-08-10: the V1 bash fleet is not a migration target and never was.** In substance: *V1 things get left in place and eventually retired when no longer needed; when they stop being used they are deleted. Stop placing so much emphasis on converting them one-for-one — that works for some and fails miserably for others, because what we are doing is fundamentally different.*

This phase previously spanned two fleets. It now spans one, and three things follow.

**1 · Requirement 1's *"in either fleet"* is VOID.** It is restated against the V2 tree below. `build.sh:277` and `build-minor.sh:281` keep greping prose for as long as those scripts are used, and that is the ruling rather than a gap — [`exit-protocol.md` §7](../../standards/exit-protocol.md) already said *"no parent branches on prose is **false for the bash fleet on purpose**, and any conformance claim is scoped to the V2 tree."* The ruling makes the phase agree with the protocol instead of contradicting it.

**2 · The Dependencies blocker is VOID — stated here rather than deleted, because a reader who remembers it needs to find out why it went away.** The blocker read: *"Do not schedule this phase until [Temporal Integration's open question] — what happens to the bash fleet after Stage A, retired or kept as an edge fallback — is answered."* It existed **only while bash was in scope**: its whole argument was *if bash is retiring, its half of this migration is throwaway; if it is staying, skipping it makes requirement 1 false*. With bash out of scope there is no bash half to be throwaway, and requirement 1 no longer makes a claim about it. **The question itself is now answered** — left in place, retired when no longer needed — and is recorded as such in [`temporal-integration.md`](../temporal-integration/temporal-integration.md) § Open questions. **Nothing gates this phase's scheduling.**

**3 · What the ruling does NOT dissolve, and the artifact is not the one you would guess.** A bash artifact IS load-bearing for V2 today, and it is **[`scripts/workflows/activities/run-claude.sh`](../../../scripts/workflows/activities/run-claude.sh)** — the shared runner. `assistant_activities.run_claude` executes `bash -c 'source "<activities/run-claude.sh>"; run_claude "$1"'` (`:508`, `:565`) and also requires `common/format-stream.sh` (`:509`). That script owns the **completion gate**, including the `.result`-versus-last-assistant-text branch that a declared `EXIT_RECORD_SCHEMA` flips — the write-time gate Phase 1 E5 measured and that open direction row `D-007` turns on. Deleting it stops V2 from running. It is in scope for this phase as **V2 infrastructure**, not as V1 residue, and requirement 9 states that.

> **A claim that reached this plan and is false: that `scripts/workflows/children/*.sh` are what the Python fleet invokes at runtime.** Verified 2026-08-10: nothing under `scripts/workflows/temporal/` invokes a script in `children/`. Every V2 workflow carries its own prompts (`review_pr/prompts/*.md`, `build/*/prompts/`, …) and declares its own `COMPLETION_PATTERN` in its `*_workflow.py`; [`temporal-integration.md`](../temporal-integration/temporal-integration.md) already records that **`children/` dissolves** under the Temporal layout. So the five bash children leave scope alongside the six bash parents, and the runner stays. **The confusion is worth recording rather than silently corrected:** conflating *the children* with *the runner they and V2 both source* is what made `temporal-integration.md:35`'s *"the bash does not die"* look like it contradicted a fleet retirement. It does not — that sentence is about **a bash script surviving as an executable an activity calls**, which is exactly and only `run-claude.sh`.
>
> Command that re-checks it, because this plan asks for the command wherever it asks for a claim:
> ```
> grep -rn "children/" scripts/workflows/temporal/ --include=*.py | grep -v tests/
> ```
> Hits today are docstrings and comments only. A hit that is a `subprocess`, a `Path` or an import falsifies this paragraph.

---

## Requirements for completion

Done when all of the following hold. **Every requirement below is scoped to the V2 Python tree plus `activities/run-claude.sh`**; none makes a claim about `scripts/workflows/*.sh` or `scripts/workflows/children/*.sh`.

1. **No parent in the V2 tree branches on a value parsed out of prose.** Every routing input is a field in the typed record. **Partly satisfied on arrival — see § What already landed** — so this requirement's remaining work is two named surfaces, not a sweep.
2. **The record's schema is declared per [Phase 3](phase3_typed_exit_record.md)'s ownership ruling**, with a test that catches a second declaration **within the V2 tree**. *(The original clause read "including one introduced across the bash/Python boundary". **That half is VOID by the same ruling**, and it was already superseded: Phase 3 step 6 ruled the declaration **scoped to the V2 tree** with the cross-tree conformance test deliberately not built, because the frozen bash fleet emits prose and has no envelope to diverge — [roadmap Key Decisions](roadmap.md#key-decisions). The phase must not rebuild a test a prior phase ruled against.)*
3. **Every V2 prompt whose return-contract section changes is enumerated and edited**, and a check verifies each prompt's emit instruction still corresponds to the field the parent reads.
4. **`is_error` and `num_turns`-against-cap are resolved** — routed per Phase 3's composition rule, **or** closed as a no-op against **their own** measurement in [Phase 1](phase1_measure_the_channel.md) E1. Each closes on its own evidence; neither closes on the other's.
5. **`permission_denials[]` is recorded and surfaced on every run** regardless of any routing ruling. It is safety observability, not a routing option, and it **cannot** be closed as a no-op — see the [roadmap's Key Decision](roadmap.md#key-decisions). *(Phase 3 already made this the fleet's first consumer, twice in nine live dispatches; this phase widens it, it does not introduce it.)*
6. **The anchored PR-URL validation survives the migration** as a validator on the field, not as a regex deleted along with the extraction.
7. **Kind 1's readers see no change**, verified against [Phase 2](phase2_kind1_framework.md)'s consumer list **for every V2 emitter**. Where that list names a V1 reader, the V1 half is out of scope and is recorded as out of scope rather than verified — `review-pr.sh:142`'s over-match is the known instance and stays on **issue #68**.
8. **A `§Capability Parity` audit is recorded.** This phase replaces a working mechanism; the parity discipline is adopted here for that reason.
9. **`activities/run-claude.sh` is treated as V2 infrastructure and its completion gate is preserved or consciously changed.** It is the only bash this phase owns. **The typed record does not replace the completion contract** — one proves the run finished, the other says what it decided — and the gate's *surface* already depends on whether the caller declares a schema. Any change to it is a parity line item under requirement 8, not a side effect of the migration.

---

## What already landed, so this phase does not plan work that is done

**Re-derive each of these before acting on it. They are stated with the command that produces them for exactly that reason** — a plan that asks for finished work costs a dispatch to discover it, and a plan that assumes work is finished when it is not costs more.

| Claim | Re-derive with | State on 2026-08-10 |
|---|---|---|
| **`review_pr_workflow` already routes on the typed record**, with `parse_verdict` retained as a **shadow** | `grep -n "exit_record.route\|parse_verdict" scripts/workflows/temporal/modules/assistant/review_pr/review_pr_workflow.py` | `:126` routes; `:138` shadows. Requirement 1's routing half holds for this parent |
| **No other V2 parent parses a verdict from prose.** `build`, `build_minor` and `plan_project` consume a typed `Verdict` returned by the review sub-workflow | `grep -rn "parse_verdict" scripts/workflows/temporal/modules/ \| grep -v tests` | two hits: the declaration in `routing.py:57` and the re-export at `review_pr_helper.py:122` |
| **`v1_constant()` is gone** (`ed6e2ea`). The Python fleet no longer recovers turn caps by regexing the V1 bash scripts at runtime; `config.yaml`'s `max_turns:` map is the single authority and **both fleets read it, neither reads the other** | `grep -rn "v1_constant" scripts/` | comments and a regression test (`test_v1_parity.py:218`) only. **This is why the ruling above is cheap to execute:** the dependency that would have made deleting V1 break V2 was removed before the ruling landed |

**Consequence for requirement 1, stated as scope rather than as reassurance.** What remains is **two surfaces, not a fleet**:

- **the shadow verdict parse** at `review_pr_workflow.py:138` — already non-routing, so removing it is a *data* decision (the shadow-agreement run count) rather than a migration; and
- **the PR-URL extraction path**, which is still a prose parse of a value that routes: the extracted number flows into `gh pr view`, `gh pr checks` and `--pr` on downstream children.

A plan sized for "migrate every parent" would spend its budget looking for parents that are already migrated.

---

## §Runtime Verification

Adopted practice — see the [roadmap's note on doc shape](roadmap.md).

- [ ] Re-run [Phase 1](phase1_measure_the_channel.md#runtime-verification)'s block and record version, date and host here. This phase touches every V2 child, so CLI drift between Phase 3 and this phase lands tree-wide
- [ ] Re-run every enumeration below against the live tree rather than trusting the counts. **Each row carries the command that produces it; run the command, do not adjust the number**

---

## The migration surface, re-derived V2-only on 2026-08-10

**Re-derived rather than adjusted.** The previous table's totals were taken on 2026-08-07 across both fleets; subtracting the bash rows from a stale total would have produced a number that was wrong in a new way. Every row below was re-run.

| Surface | Count | Command that produces it | What changes |
|---|---|---|---|
| **V2 workflows declaring a `COMPLETION_PATTERN`** | **10** (9 PR-URL-shaped, 1 `^VERDICT:`) | `grep -rnE "COMPLETION_PATTERN\s*=" scripts/workflows/temporal/` | The completion contract gains the typed record; the final line stays as the human-facing signal |
| V2 parents parsing a verdict from prose | **1, and it is already a shadow** | `grep -rn "parse_verdict" scripts/workflows/temporal/modules/ \| grep -v tests` | `review_pr_workflow.py:138`. Removed on the agreement data, not on the design |
| **V2 PR-URL extraction — TWO declarations plus a re-export** | **2 + 1** | `grep -rn "PR_URL\|extract_pr_url" scripts/workflows/temporal/modules/ \| grep -v tests` | `assistant_activities.py:29`/`:242` and `build/build_helper.py:24`/`:30`, re-exported at `plan/plan_activities.py:30`. **One implementation behind one name — and keep the anchored pattern as a validator on the field** |
| V2 routing vocabulary | one declaration, three consumers | `grep -rn "^from\|^import\|routing\." scripts/workflows/temporal/modules/assistant/*/*.py` | `assistant/routing.py`, re-exported at `review_pr/review_pr_helper.py:122`. Extended in place, never duplicated |
| **V2 prompt text carrying the return contract** | **non-zero** | `grep -rln "VERDICT:\|pr_review:\|FINAL line" scripts/workflows/temporal/modules/assistant/*/prompts/ scripts/workflows/temporal/modules/assistant/prompts/` | The `pr_review:` wire format is specified inside `review_pr/prompts/disposition.md`. Enumerate and edit |
| **The shared runner** | 1 file | `grep -rn "run-claude.sh\|format-stream.sh" scripts/workflows/temporal/modules/assistant/assistant_activities.py` | `activities/run-claude.sh` (`:508`) and `common/format-stream.sh` (`:509`). Requirement 9's surface |

**Out of scope, enumerated so the exclusion is deliberate rather than an oversight:** 11 bash `COMPLETION_PATTERN` declarations (6 parent entrypoints + 5 files under `children/`), 2 bash prose verdict parsers (`build.sh:277`, `build-minor.sh:281`), 2 bash PR-URL regexes (`build.sh:198`, `build-minor.sh:202`). These stay as they are until the operator deletes the scripts. **`activities/run-claude.sh` and `common/format-stream.sh` are NOT in this list** — they are requirement 9.

**Use language-agnostic patterns anyway.** `grep -rnE "COMPLETION_PATTERN\s*="` finds all 21 across both trees; `grep -rn "COMPLETION_PATTERN="` finds 11 and silently reports the bash fleet as the whole fleet. **The first draft of this plan made exactly that mistake and undercounted the surface by half.** The note survives the re-scope because the failure it describes is about the pattern, not about the fleet: a V2-only sweep written as `COMPLETION_PATTERN=` finds **zero**, which reads as "nothing to do."

---

## Implementation steps

### 1. Migrate the emitters, including their prompts

- [ ] Enumerate every V2 prompt section that states a return contract, before editing any of them. This is the surface the plan previously sized at zero
- [ ] Edit each so the child is instructed to emit the typed record per [Phase 3](phase3_typed_exit_record.md)'s authorship ruling, and so the `pr_review:` wire format stated in-prompt matches the schema
- [ ] Add a check that the prompt's emit instruction corresponds to the field the parent reads — a prompt edit that drops a field is invisible to a schema test, because the schema is still fine and the producer simply stopped filling it
- [ ] Every V2 child writes the typed record at exit on the channel Phase 3 specified, with its freshness, run-identity and outside-the-worktree properties intact
- [ ] The schema is declared per Phase 3's ruling, **scoped to the V2 tree**, with the test that catches a second declaration. This repo has already paid for a duplicated routing enum once, where the copy deciding whether a PR merges had zero tests while its twin had twenty. **Do not build the cross-tree conformance test** — Phase 3 ruled against it and the frozen fleet has no envelope to diverge
- [ ] Each V2 workflow's `COMPLETION_PATTERN` continues to guard against the headless early-stop failure it exists for, and `activities/run-claude.sh`'s gate is unchanged or its change is a parity line item (requirement 9)

### 2. Migrate the consumers

- [ ] **BEFORE the second parent copies the shape: extract the pure half of `review_pr_workflow.run_review` into `review_pr_helper`.** [Phase 3](phase3_typed_exit_record.md) added roughly forty lines of `ExitRecord`-to-string logic — the shadow-disagreement comparison and its message, the three record-derived notes, and the finding-set comparison and its two messages — directly into the workflow layer, against that file's own binding docstring (*"Every decision below comes from the helper; every side effect is an activity"*). It was left in place deliberately: with **one** parent the misplacement costs only that five otherwise-pure tests run through a monkeypatch harness, and refactoring the file this phase is about to rework would have been churn. **This checkbox is the trigger.** The moment a second parent routes on a record, the choice is re-typing that prose or reaching into a workflow module for it — which is the duplicated-vocabulary defect the whole component exists to remove. **FIVE** pure functions, each returning the operator-facing message or `None`; the existing tests assert message text via `pytest.raises(match=…)`, so the strings move byte-identical. *(Three at Phase 3; [Phase 5](phase5_convergence_stopping.md) added `_convergence_notes` and `_thread_unreadable_note` to the same layer for the same reason and left them there under the same trigger. Extracting three and leaving two is the half-fix this count exists to prevent.)* **Unaffected by the V2-only re-scope** — both parents were always V2
- [ ] **If this phase migrates NO second consumer of a single-consumer parent-level module, move it to `review_pr/`. There are TWO: `modules/assistant/exit_record.py` and `modules/assistant/convergence.py`, one ruling covering both.** [Phase 3](phase3_typed_exit_record.md) placed the first at the `assistant/` parent level with **one** consumer, which is a stated deviation from §10.1 rule 3 (a module promotes on consumer count, never on taste) and not a claim of conformance; [Phase 5](phase5_convergence_stopping.md) placed the second in the same position for the same reasons — dependency-free like `routing.py`, and loaded **by path** by `replay_convergence_predicate.py`, an out-of-tree consumer rule 3's *workflow* count cannot see. **This checkbox is where both deviations expire.** Rule them either way here; do not leave either unruled
  > **And the membership of that set is now a TEST, not this sentence.** The first version of this checkbox named `exit_record.py` alone while a second module already qualified, and nothing could tell — which is the failure the paragraph below describes, reproduced in the checkbox that describes it. `test_every_parent_level_module_is_shared_or_a_DECLARED_deviation` computes each parent-level module's consumer count from the import graph and asserts it equals the declared set, so a **third** single-consumer module fails there rather than waiting for a reader, and a declared deviation that acquires its **second** consumer also fails, because it has expired on its own. Both directions were mutated and both go red. Prose in a completed phase is not a trigger anybody re-reads — so the deviation would have survived by default rather than by decision, and an honest deviation becomes an unmarked violation the moment nobody is left who remembers it was one.
- [ ] **Select this pass's `pr_review:` block by the run nonce rather than by position.** The parent already issues a `run_id` and rule R5 compares it, but the block carries no `run_id` field, so the inference is still positional: ordering plus a posted-count delta. **The change site is `review_pr_helper._this_pass_index`**, which [Phase 5](phase5_convergence_stopping.md) added precisely so there is ONE site: it returns *which* block is this pass's, and `this_pass_block` and `prior_pass_blocks` are both derived from it, so the complement cannot keep selecting by position after the selection becomes an identity check. `latest_pr_review_block` (which this checkbox used to name) is a projection over the same accessor rather than the place the inference lives. *(The first collapse declared `this_pass_block` alone and left three sites — `_assert_block_matches_record`'s inline `blocks[-1]` and `prior_pass_blocks`' own `window[:-1]`, the complement being the one hardest to count. `test_selecting_from_the_END_of_a_sequence_happens_only_where_it_is_owned` now gates the SHAPE across the whole `review_pr/` package, so a fourth site fails rather than being found by a later pass; both re-derivations were mutated back in and both turn it red, while the behavioural test stays green on one of them.)* Phase 3 closed the reachable half of that (a comment quoting the block it supersedes returned the superseded one; fixed with `finditer`), and what remains is a genuine race: a third party posting a fenced `pr_review:` example between the child's comment and the parent's read. **This belongs here and not in Phase 3 because the remedy is not small** — a schema field, a prompt change in `disposition.md`, a parser and a gate — and this is the phase that already owns the tree-wide addressing sweep. It turns an inference into an identity check, which is what `review_pr_workflow`'s invariant docstring is actually trying to assert
- [ ] **The PR URL becomes a field, and the anchored pattern is retained as a validator on that field.** **Collapse the two declarations first** (`assistant_activities.py:29`/`:242` and `build/build_helper.py:24`/`:30`) — migrating a value that is extracted two ways migrates the divergence with it. The current regex (`https://github\.com/[^\s)]+/pull/(\d+)`) is not merely an extraction: it pins the host and guarantees the derived PR number is digits, and that value flows into `gh pr view`, `gh pr checks` and `--pr` on downstream children. `gh` accepts a URL wherever it accepts a number, so an unvalidated `pr_url` field naming a different repository makes the parent act on a PR the child chose. This needs no adversarial child — children are instructed to read prior PR comments, which routinely contain other PRs' URLs. A field failing the pattern routes to the human arm
- [ ] Remove the shadow prose parse only after it has agreed across a **stated run count with its denominator, and with the denominator's own limit named**. **Removing it on the strength of the design rather than the data is the failure this phase is structured to avoid** — and the data has a stated blindness this phase inherits rather than fixes: `channels_agree` can only be written on runs where the incumbent prose channel already succeeded, so the agreement figure is conditioned on the very thing it measures. Carried as **C-060**, and widening the denominator does not remove the blindness
- [ ] Verify no remaining prose parsing of routing values exists in the V2 tree: `grep -rnE "re\.search|re\.compile|re\.findall" scripts/workflows/temporal/modules/ | grep -v tests` and **account for every hit**, including the ones that are legitimately not routing values (`research_activities.py`'s revalidation dates, `plan_activities.py`'s `C-NNN`/`D-NNN` row readers, `resource_telemetry.py`'s `Task` counter). *The sweep is over the V2 tree only; `scripts/workflows/*.sh` is out of scope by the ruling above and a hit there is not a finding.*

### 3. Resolve the envelope observables — separately

- [ ] **`is_error`:** route through Phase 3's ordered-rules contract, or close as a no-op citing E1's measurement of `is_error` specifically
- [ ] **`num_turns`-against-cap:** same, against E1's measurement of `num_turns` specifically. **State whether the cap being compared against binds a unit or an aggregate** — `config.yaml`'s `max_turns:` map is per-workflow-invocation and nothing sums it across concurrent dispatches
- [ ] **`permission_denials[]`:** record and surface on every run. **No no-op path exists for this one.** Under `--dangerously-skip-permissions` the safety hook is the only control operating inside a headless run, a denial does not fail the run, and the array is the only trace it left. Per Phase 3's contract, a non-empty list routes to the human arm and never to automatic redispatch. **Phase 3 made this the first consumer** — two of nine live dispatches tripped it — so this step widens an observed control rather than lighting up a theoretical one
- [ ] Record what the `system/api_retry` error enum is used for, or state explicitly that it is read by nothing and why that is acceptable
- [ ] Whichever outcomes: state that class-(i) routing in this fleet rests on an **undocumented exit-code mapping**, and record the mapping Phase 1 measured as this fleet's own table with its measurement date. A measured table with a date is honest; an assumed one is the thing being fixed

### 4. Verify Kind 1 tree-wide

The rendering and archive design lands in [Phase 3](phase3_typed_exit_record.md) on the single proven pair. This phase's obligation is that it still holds once every V2 child is migrated.

- [ ] Verify against [Phase 2](phase2_kind1_framework.md)'s consumer list that every reader of every Kind 1 surface still reads what it needs, for every migrated V2 child
- [ ] **Where the consumer list names a V1 reader, record it as out of scope rather than verifying or fixing it.** The known instance is `review-pr.sh:142`'s unanchored `pr_review:` match, which over-counted passes on two archived PRs and is tracked on issue **#68**. [`memory-model.md` §6.4](../../guide/memory-model.md) already rules that Phase 4 does **not** inherit the prompt-file half of the one-declaration sweep; the V1-reader half is excluded on the same footing
- [ ] Verify the publish classification holds tree-wide — no migrated child publishes a field Phase 3 classified `internal`
- [ ] Verify the retrievability convention survives the migration, so a correction pass can still address a prior pass's record

### 5. Capability parity

- [ ] Enumerate every behaviour of the prose-channel arrangement being replaced **in the V2 tree** — not just the headline. Fail-closed on absence; last-match-wins so a run quoting a previous verdict does not route on its own history; the anchored pattern so prose mentioning a token cannot match; the anchored PR-URL validation; loud failure on a missing completion signal; the human-readable final line an operator reads in a terminal
- [ ] Map each to **ported** (cite where) or **consciously dropped** (named, with operator sign-off and a one-line rationale). A behaviour that is neither is a parity gap that blocks completion
- [ ] Include the prompt-to-field correspondence from step 1 as a parity line item — a model-authored field is a behaviour of the prompt, and the audit must cover it or it covers only the plumbing
- [ ] **Include `activities/run-claude.sh`'s completion gate as a parity line item** (requirement 9), including its schema-dependent surface: without a declared schema it reads `.result`; with one it reads the last assistant text block, because `--json-schema` replaces `.result` with the serialised structured output
- [ ] **State each parity claim with BOTH bounds where a bound is meaningful.** A verification that asserts only a floor passes while measuring the wrong thing — measured on this fleet on 2026-08-10, where a one-sided assertion in the telemetry's own test went green while reporting three different children at an identical figure because it was reading the caller's cgroup. *"The migrated path still fails closed"* is a floor; *"and it does not fail closed on inputs the incumbent accepted"* is the ceiling, and a parity audit needs both or it certifies a regression as a pass
- [ ] Record the audit as a `§Capability Parity` table in this doc and post it alongside the QC dispositions

### Close-out

- [ ] Every requirement above met, with evidence in this doc
- [ ] The shadow-agreement run count is recorded **with its denominator and C-060's stated blindness**, and the shadow's removal is justified by it
- [ ] The standards-amendment candidate on `§ Composition` is now supported by a proven replacement — surface it for ratification in the [roadmap](roadmap.md#standards-amendment-candidates); **do not write it**. Note that item 1 is the standards-side half of open direction row `D-007` and must not be ruled independently of it
- [ ] Confirm [Temporal Integration](../temporal-integration/temporal-integration.md) can proceed: the handoff shape is fixed, and say so here so the gate is checkable rather than inferred

---

## Notes and gotchas

- **The phase got smaller and the enumeration did not get easier.** Dropping V1 removes roughly half the declared surface, but what would break this phase was never breadth — it is a call site nobody enumerated, or a grep whose pattern only matches one shape. A V2-only sweep written with the bash spelling (`COMPLETION_PATTERN=`) returns **zero hits**, which reads as "nothing to do" rather than as a broken pattern. Every enumeration in this doc carries the command that produces it for that reason.
- **Do not re-derive a count from a previous count.** Three times in two days a figure in this repo was right with a wrong derivation, or computed from an earlier copy of itself. Where this plan states a number, run the command beside it.
- **The two-declaration failure is the one this repo has already had**, and it is still live in this phase's surface: `extract_pr_url` exists twice. The cross-language version of the problem is closed by the scope ruling; the intra-tree version is not.
- **Do not let a refactor move aggregation into the parent.** The child derives its verdict from its own findings and states it; a parent re-deriving one is a caller with no stake making a judgement about the child's judgement. This is correct in the shipped code today and the migration must keep it correct.
- **Splitting this phase by consumer is now a smaller question than it was.** Requirement 1 is satisfied by `review_pr` alone plus the PR-URL path. The other nine V2 `COMPLETION_PATTERN` children have no parent that branches on their prose today; their final line is read by `run-claude.sh`'s completion check and by a human. Migrating them anyway buys uniformity and forward compatibility at the cost of bundling speculative work into the phase that unblocks Temporal Integration. Both are defensible; **the choice should be made deliberately rather than inherited from the phase's title.**
- **This phase writes a `parent_route` event on every routed run and reads none of them.** So does [Phase 5](phase5_convergence_stopping.md) with `convergence`, and so does the resource telemetry with `run_resources`. [Phase 6](phase6_read_what_it_writes.md) owns that, and it owns it *after* this phase widens the emission — which is the right order, because a reader built before the fleet-wide denominator exists measures one parent.
