# Phase 1 — Measure the channel before designing it

**Component:** [Memory Management Framework](roadmap.md) · **Status: complete — measured 2026-08-08, all six experiments run, thirteen rulings recorded; three of them re-taken the same day (E7, E6's field list, E5's denominator) and marked inline**

Six experiments the research could not settle and the design depends on. Three of them can shrink or cancel work downstream. This phase produces **a measured record, not a design** — every experiment ends in a written ruling, and the rulings are the deliverable.

---

## Requirements for completion

This phase is done when all six experiments below have run against the pinned CLI and the archived artifacts, each has its observed data recorded **in this document**, and each carries an explicit ruling of one of three kinds:

- **Changes the design** — names what in [Phase 3](phase3_typed_exit_record.md), [Phase 4](phase4_fleet_migration.md) or [Phase 5](phase5_convergence_stopping.md) must be different, and that phase's checklist is amended before it starts.
- **Confirms the design** — the Key Decision it bears on stands as written in the [roadmap](roadmap.md), with this measurement now cited as its evidence rather than a derived claim.
- **No-op** — the work the measurement was gating is not warranted, stated with the number that shows it.

"We ran it and it looked fine" is not a ruling. A ruling names a downstream consequence.

**Also required:** the `§Runtime Verification` block below is re-run and its date refreshed if this doc is substantively revised. That block is adopted from the vendored Documentation Standard's practice; the [applicability note](../../standards/documentation/README.md) excludes that section from binding here, and this phase follows it because a component that reads a vendor CLI's output surface is exactly what it was written for.

---

## Dependencies

- **None built.** This phase depends only on the pinned `claude` CLI and the archived run logs and PR comments, all of which exist today.
- **Evidence:** [`research/synthesis.md`](research/synthesis.md); experiment designs are adapted from `research/raw/non_model_observables.md` §7 and `research/raw/dual_channel_outcome_records.md` §8. **Those papers number their tests T1–T6 with two different meanings for `T3`.** This doc uses its own E-labels and cites the source tests inline, so a reader is never resolving a `T` against the wrong paper. The [roadmap](roadmap.md) refers to these experiments by E-label only.
- **There is no E4, deliberately.** The label space is stable so a citation to `E6` means the same thing across drafts. E4 was the liveness/progress-signal question, and it is **closed by citation rather than by measurement** — `liveness_signal_measurement.md` already measured it, and re-deriving it here would produce an ad-hoc phase-doc measurement competing for authority with a critic-gated paper. See the close-out.
- **Cites but does not re-derive:** `docs/standards/architecture/research/raw/claude_code_integration_surface.md` §5 (no first-party exit-code table; the `system/api_retry` error enum) and §7 (the result-envelope field list). **Comes due 2026-08-22** — if this phase runs after that date, note the staleness in the ruling rather than silently relying on it.
- **Cites and does not re-derive:** `../temporal-integration/research/raw/liveness_signal_measurement.md`, which already measured the `stream-json` event vocabulary and identified the progress signals. This phase does **not** re-run that measurement; see the close-out.

---

## §Runtime Verification

Required because this phase orchestrates an external runtime — the `claude` CLI, a vendor binary whose documented surface is the thing being measured.

**Date performed: 2026-08-08** (re-run for the execution of this phase; the block below replaces the 2026-08-07 planning-run version) · **Host:** `puma-workstation-mint` · **Performed during:** the build-draft run that executed E1–E7, and **re-run unchanged during the same day's build-refine pass** — same version, same three results

```
$ claude --version
2.1.224 (Claude Code)

$ claude --help | grep -iE "json-schema|output-format"
  --json-schema <schema>                JSON Schema for structured output
  --output-format <format>              Output format (only works with --print):

$ claude --help | grep -c -- "--max-turns"
0
```

**What this establishes.** `--json-schema` and `--output-format` are present on the CLI actually installed here; the version is unchanged from the planning run at **2.1.224**, so the E1–E7 measurements and the planning assumptions were taken against the same binary. The upstream paper documents `structured_output` as available from v2.1.205+, so the transport this component's Key Decisions name as option (a) is not hypothetical.

**What the 2026-08-07 version of this block did NOT check, and should have.** `--max-turns` — the flag **every dispatch in the fleet passes** (`run-claude.sh:139`) — **does not appear in `claude --help` on 2.1.224 at all.** E1 measured it: it still parses and still works (`error_max_turns` fired correctly with the cap honoured). But a block that verifies two flags the design *might* use while omitting the one the fleet *already depends on* is verifying the wrong surface. **Any future re-run of this block includes `--max-turns` and `--dangerously-skip-permissions`.**

**Flag presence is not flag behaviour, and E1 settled the behaviour.** Under `--dangerously-skip-permissions`, inside a worktree, at a child's turn budget: `--json-schema` delivers a `structured_output` object that validates — and **`--json-schema` takes an inline JSON string, not a file path** (a path fails with `--json-schema is not valid JSON: JSON Parse error: Unrecognized token '/'`). See E1 for the full tuple table.

**The incumbent surfaces, verified by reading the shipped code** (not by citing a description of it):

| Fact | Where |
|---|---|
| The parent's shell propagates the child's non-zero exit through `tee` | `scripts/workflows/build.sh:60` (`set -euo pipefail`), `:266` |
| **Two** bash parents parse the routing token out of prose stdout | `scripts/workflows/build.sh:277` and `scripts/workflows/build-minor.sh:281` |
| Two bash parents extract the PR URL by anchored regex | `build.sh:198`, `build-minor.sh:202` |
| The runtime reads the envelope's `subtype` for turn-cap death | `scripts/workflows/activities/run-claude.sh:167` |
| The runtime reads `.result` against the declared completion pattern | `scripts/workflows/activities/run-claude.sh:201-204` |
| Measured turn-cap termination rate, already recorded by the fleet | `run-claude.sh:157-160` — **0.9% (4/443 runs)**. Cite verified 2026-08-08 (the figure is at `:159`). **E5 cross-checked it and the only re-measurable sample runs 3–4× higher** — 2 `error_max_turns` in 72 completed archived logs (2.8%), both from August. Different populations, so not a claim the rate rose; see E5 |
| The routing vocabulary is declared once in the Python tree | `scripts/workflows/temporal/modules/assistant/routing.py:24-56`, re-exported at `review_pr/review_pr_helper.py:67` |
| Completion patterns are declared in **both** fleets | `grep -rnE "COMPLETION_PATTERN\s*=" scripts/` → **21** total: 11 bash, 10 Python |
| `review-pr` already emits a convergence flag and stable finding ids | `children/review-pr.sh:323` (the rule), `:355` (`converged: true\|false`), `:221` and `:357` (stable ids reused verbatim across passes) |
| Archived run logs available for replay | `.claude/logs/` at the repo root → ~~60 JSONL files as of 2026-08-07~~ → **73 as of 2026-08-08**. The fleet ran 13 more times in one day; every count taken over this corpus dates fast |
| Archived PRs available for `pr_review:` replay | `gh pr list --state all` → **38** PRs as of 2026-08-08 (32 merged, 6 closed, **0 open**), of which **7** carry a `pr_review:` block and **5** carry more than one |

**Two greps this phase must run with the right pattern.** `grep -rn "COMPLETION_PATTERN=" scripts/` finds only the 11 bash declarations — Python writes `COMPLETION_PATTERN = r"…"` with spaces and is invisible to it. Use `grep -rnE "COMPLETION_PATTERN\s*="`. Both counts **re-verified 2026-08-08: 11 and 21, unchanged.** The same applies to any enumeration this phase produces: **a bash-shaped grep measures one of the two fleets** — and E6 records the site that would have been lost to one (`plan_revision_workflow.py:86-95`, the issue-URL completion path).

**`is_error` and `permission_denials` appear nowhere in the fleet. Re-verified 2026-08-08** — `grep -rn "is_error\|permission_denial" scripts/` still returns nothing, so E1's framing stands as written. `grep -rn "structured_output\|rate_limit_event" scripts/` likewise returns nothing: **neither the transport this phase selects nor the rate-limit signal E1 discovered has any reader today.**

**The one dated dependency, checked rather than assumed.** `claude_code_integration_surface.md` carries `Last validated: 2026-07-25` and `Revalidate: high — 4 weeks`, so it **comes due 2026-08-22**. Today is 2026-08-08; it is **current**, and this phase relies on it as such. Two facts about it are worth carrying forward anyway: its **version anchor is 2.1.220** while the installed CLI is **2.1.224**, and E1 found **ten result-envelope fields its §7 does not list**. When it is revalidated, that §7 list is the section that has drifted.

---

## Implementation steps

Experiments are ordered by decision value: E1, E5 and E7 come first because each can cancel work downstream, and running them last would mean designing on assumptions they can overturn.

### E1 — The envelope observables on the pinned version

*(Source: `non_model_observables.md` T1.)* *Because:* there is no first-party exit-code table for `claude` — `claude_code_integration_surface.md` §5 records that codes for auth failure, rate-limit exhaustion and `--max-turns` exceeded are undocumented — and the whole "read the rest of the envelope" milestone assumes these values carry information the exit status does not.

- [x] Force each failure mode in turn — auth failure, rate-limit exhaustion, `--max-turns` exceeded, `--max-budget-usd` exceeded, a usage-policy refusal, `SIGTERM` — using a trivial throwaway prompt, not a real dispatch
- [x] For each, record the **full** tuple: process exit code, `result.subtype`, `result.is_error`, `result.num_turns` against the configured cap, `result.permission_denials[]` (length and contents), whether any `system/api_retry` `error` value appeared, and whether `result.result` is non-empty
- [x] Record the same tuple for a **successful** run, so the baseline is measured rather than assumed
- [x] Force at least one run that trips `block-dangerous.sh`, so `permission_denials[]` is observed non-empty at least once. **This is the fleet's only scheduled opportunity to see the sole in-run safety control leave a trace** — under `--dangerously-skip-permissions` a denial does not fail the run, and the array is all there is
- [x] Run each mode inside a worktree under `--dangerously-skip-permissions`, matching the real child-invocation shape — a measurement taken in a different invocation shape measures a different thing
- [x] Record, for one run, whether `--output-format json --json-schema <schema>` produces a `structured_output` field that validates against the schema
- [x] **Ruling, one per observable, not one for the experiment.** For `is_error` and `num_turns`-against-cap: does each carry information the propagated exit status does not? For the transport: which of the two options does the evidence support, judged on **isolation and Temporal replay cost as well as availability** — a file the child writes outside its worktree is a new write channel across the isolation boundary and a second I/O boundary under Temporal; `structured_output` is neither. `permission_denials[]` gets no redundancy ruling — it is recorded regardless

#### E1 — Observed

**Method.** Nine `claude -p` invocations on **2.1.224**, each `--model haiku --output-format stream-json --verbose --dangerously-skip-permissions -w <name>` — the real child shape from `run-claude.sh:134-142` minus the model, which was downgraded to haiku because the envelope is model-independent and the failure modes cost real calls. Denominator for every row below is **1 forced run per mode**; this is an existence measurement of the tuple, not a rate.

| Mode | exit | `subtype` | `is_error` | `terminal_reason` | `stop_reason` | `num_turns` / cap | `permission_denials[]` | `system/api_retry` | `.result` | `errors[]` |
|---|---|---|---|---|---|---|---|---|---|---|
| success | 0 | `success` | `false` | `completed` | `end_turn` | 1 / 3 | `[]` (0) | none | `"OK"` | **key absent** |
| `--max-turns` exceeded | 1 | `error_max_turns` | `true` | `max_turns` | `tool_use` | **2 / 1** | `[]` (0) | none | **key absent** | `["Reached maximum number of turns (1)"]` |
| `--max-budget-usd` exceeded | 1 | `error_max_budget_usd` | `true` | `budget_exhausted` | `tool_use` | 1 / 20 | `[]` (0) | none | **key absent** | `["Reached maximum budget ($0.005)"]` |
| permission denial (`sudo ls`) | **0** | `success` | **`false`** | `completed` | `end_turn` | 2 / 4 | **1 entry** | none | denial prose, 136 ch | **key absent** |
| model decline (copyright) | 0 | `success` | `false` | `completed` | `end_turn` | 1 / 2 | `[]` (0) | none | decline prose, 500 ch | **key absent** |
| `SIGTERM` mid-run | 143 | `error_during_execution` | `true` | `aborted_streaming` | `null` | 2 / 10 | `[]` (0) | none | **key absent** | `["[ede_diagnostic] result_type=user last_content_type=n/a stop_reason=null"]` |
| auth failure (bad `ANTHROPIC_API_KEY`) | **124** (our `timeout`, not the CLI's) | `error_during_execution` | `true` | `aborted_streaming` | `null` | 2 / 1 | `[]` (0) | **9×**, `error_status:401`, `error:"authentication_failed"`, `max_retries:10` | **key absent** | `["[ede_diagnostic] …"]` |
| auth failure (unreachable `ANTHROPIC_BASE_URL`) | **124** (our `timeout`) | `error_during_execution` | `true` | `aborted_streaming` | `null` | 2 / 1 | `[]` (0) | 9× | **key absent** | `["[ede_diagnostic] …"]` |
| rate-limit exhaustion | — | — | — | — | — | — | — | — | — | — |

**Rate-limit exhaustion is UN-MEASURED, not inferred.** It cannot be forced on demand without deliberately burning the account's seven-day window, which is not a throwaway-prompt cost. Per this doc's own gotcha, no row is guessed for it. What *was* observed instead is a passive signal: a top-level stream event

```json
{"type":"rate_limit_event","rate_limit_info":{"status":"allowed_warning","resetsAt":1786251600,
  "rateLimitType":"seven_day","utilization":0.83,"isUsingOverage":false,"surpassedThreshold":0.75}}
```

appeared unprompted in the `SIGTERM` run's stream. **This is NOT a new discovery and this doc does not claim it as one** — `liveness_signal_measurement.md` Finding C already records `rate_limit_event` as a typed first-party message (`class RateLimitEvent` in the Python SDK's `types.py`), and the `claude_code_integration_surface.md` §7 list this phase cites is an *envelope* field list, which is a different surface. What is incremental here is the **variant**: that paper observed `rateLimitType: "five_hour"` with `status: "allowed"`; this run observed `"seven_day"` with **`status: "allowed_warning"`, `utilization: 0.83` and `surpassedThreshold: 0.75`.** Exhaustion is therefore **predictable before it happens**, which is a stronger observable than the post-hoc exit code this experiment went looking for. `grep -rn "rate_limit_event" scripts/` → **0 hits**: nothing in either fleet reads it, in either fleet's language.

**`permission_denials[]` non-empty, observed once (1 of 9 runs, forced).** Full entry:

```json
{"tool_name":"Bash","tool_use_id":"toolu_01CsEb…","tool_input":{"command":"sudo ls /root .","description":"Run sudo ls /root ."}}
```

with a matching `{"type":"system","subtype":"permission_denied","tool_name":"Bash","decision_reason_type":"subcommandResults","message":"Permission to use Bash with command sudo ls /root . has been denied."}` stream event. The run **exited 0 with `is_error:false` and `subtype:"success"`.**

**`structured_output` — works, and validates.** `--output-format json --json-schema '<inline JSON>'` produced, alongside a `.result` carrying the same object as a string:

```json
"structured_output": {"verdict":"MERGE","reason":"all clear","findings":0}
```

**Three of this doc's own premises were wrong or stale, corrected here:**

1. **`--json-schema` takes an inline JSON string, not a file path.** Passing a path fails hard: `Error: --json-schema is not valid JSON: JSON Parse error: Unrecognized token '/'`. Both of this phase's first two attempts failed on it. Phase 3 must pass the schema inline (or via a `"$(cat …)"` expansion), and a shell-quoting-sensitive multi-KB argument is a real cost to weigh that the "availability" framing missed.
2. **`--max-turns` is no longer in `claude --help` on 2.1.224.** It still parses and still works — `error_max_turns` fired correctly — but the flag every dispatch in the fleet passes (`run-claude.sh:139`) is now undocumented on the installed binary. The `§Runtime Verification` block above verified `--json-schema` and `--output-format`; it did not verify `--max-turns`, and that is the one that matters most.
3. **The result envelope carries ten fields `claude_code_integration_surface.md` §7 does not list**: `stop_reason`, `terminal_reason`, `api_error_status`, `errors[]`, `fast_mode_state`, `fast_mode_disabled_reason`, `modelUsage`, `ttft_ms`, `ttft_stream_ms`, `uuid`. The paper is anchored at **2.1.220** and is current until 2026-08-22 (`Last validated: 2026-07-25`, `Revalidate: high — 4 weeks` — checked, not assumed); the installed CLI is **2.1.224**. Four patch versions produced ten new envelope fields. That drift rate is itself the finding.

#### E1 — Rulings (one per observable)

**(a) `is_error` — NO-OP.** Across all 8 measured rows, `is_error == (exit != 0)` with no exception. It carries **zero** information the shell's propagated exit status does not, and `build.sh:60`'s `set -euo pipefail` already propagates that. **Consequence:** `is_error` does **not** enter Phase 3's envelope as a routing field, and Phase 4's "read the rest of the envelope" milestone loses its `is_error` component. *(Denominator honesty: 8 rows, one per forced mode. This is an existence test — one disagreeing row would overturn it, and rate-limit exhaustion is un-measured.)*

**(b) `num_turns` against the cap — NO-OP as a routing signal, and actively unsafe as one.** The turn-cap run reported **`num_turns: 2` against a cap of 1**. A parent testing `num_turns >= MAX_TURNS` would be correct here by accident; a parent testing `num_turns == MAX_TURNS` would be wrong. `subtype: "error_max_turns"` states the same fact exactly, and `run-claude.sh:167` already reads it. **Consequence:** `num_turns` enters Phase 3's envelope, if at all, as **telemetry only** (it is already consumed that way by the cost rollup at `run-claude.sh:115`), never as the input to a branch. Phase 3's schema marks it non-routing.

**(c) `subtype` — CONFIRMS the design, and it is the only envelope field that earns its place.** `error_max_turns` and `error_max_budget_usd` **both exit 1**. The exit status cannot tell them apart; `subtype` can, and `terminal_reason` duplicates it 1:1 across all 8 rows (`success`/`completed`, `error_max_turns`/`max_turns`, `error_max_budget_usd`/`budget_exhausted`, `error_during_execution`/`aborted_streaming`). **Consequence:** the roadmap's "read the rest of the envelope" decision stands, but **narrowed to `subtype`** — this measurement replaces the derived claim as its evidence. Phase 4 reads `subtype`, not the envelope generally. `terminal_reason` is redundant with it and does not enter the envelope.

**(d) `.result` is ABSENT — not empty — on every error subtype. CHANGES THE DESIGN.** On all four error rows the `result` **key does not exist**, replaced by `errors[]`. The fleet's completion check (`run-claude.sh:201-204`) reads `.result // ""` and so degrades correctly to a loud failure — that is luck of a well-chosen `//` default, not a contract. **Consequence for Phase 3:** any transport that rides inside `.result` (including today's prose `VERDICT:` line) is structurally incapable of carrying a record out of a turn-cap, budget, `SIGTERM` or auth death. This is the strongest single argument for the typed record so far, and it is a *measured* one rather than the robustness argument E5 was expected to have to carry alone.

**(e) Auth failure and `SIGTERM` are INDISTINGUISHABLE in the envelope. CHANGES THE DESIGN (Phase 4).** Both produce `subtype: error_during_execution`, `terminal_reason: aborted_streaming`, `stop_reason: null`, and the same opaque `[ede_diagnostic]` string in `errors[]`. The **only** discriminator is the `system/api_retry` stream events (`error_status: 401`, `error: "authentication_failed"`), which live outside the result envelope entirely. **Worse: neither exited on its own.** Both auth runs returned **124 — our `timeout(1)` wrapper**, after 9 retries against `max_retries: 10`. Nothing in `run-claude.sh` wraps the CLI in a timeout. **Consequence:** Phase 4 cannot route auth failure from the result envelope; it must either read the `system/api_retry` stream events (which the fleet already captures — every dispatch writes `stream-json` to `$LOG_FILE`) or accept that auth failure is an unbounded hang. This is a live gap in the incumbent, not just in the design; surfaced to the operator in the PR body rather than fixed here, because this phase measures.

**(f) `permission_denials[]` — CHANGES THE DESIGN (Phase 3). Recorded regardless of redundancy, per this experiment's terms, and the measurement says it is not redundant with anything.** The denial run exited **0**, with `is_error: false` and `subtype: "success"`. The sole in-run safety control fired, and **every signal the fleet currently reads said the run was clean.** `permission_denials[]` and the `system/permission_denied` stream event are the entire trace. **Consequence:** Phase 3's envelope carries `permission_denials` (count, and enough of each entry to name the tool and command) as a **required** field, and its consumer is named: an operator reviewing whether a dispatch tried something the hook stopped. Without it, the answer to "did any run this month get blocked?" is unanswerable from anything the fleet stores in a structured form.

**(g) Transport — `structured_output`, CONFIRMS option (a), with one cost the framing missed.** On availability: it works on 2.1.224 and validates (measured above). On **isolation**: it rides in the CLI's own stdout, so no write crosses the worktree boundary — a file transport would require the child to write outside its own isolation unit, which is the boundary the worktree exists to draw. On **Temporal replay cost**: it is already inside the activity's return value, so it adds no second I/O boundary; a file transport adds one, and a file is not part of an activity result, so replay would need it re-read or side-channelled into the workflow's history. All three point the same way. **Consequence:** Phase 3 specifies `structured_output` as the transport, and adds one requirement the availability framing did not surface — **the schema is passed inline as a shell argument, so it must stay small enough to quote safely**. E2 measures whether it survives the error paths where `.result` does not; if it does not, this ruling is not overturned (the file transport has the same or worse partial-record class) but Phase 3's fail-safe contract carries the whole load.


### E5 — How often the current prose grep actually misses

*(Source: `dual_channel_outcome_records.md` T5.)* *Because:* the case for replacing the prose channel is currently a robustness argument, not a demonstrated-defect argument, and a doc claiming the incumbent is broken would be overclaiming. **This experiment is the only thing that can convert that argument, in either direction — so its method has to be stated, or a zero is unreadable.**

- [x] Replay every archived `.claude/logs/*.jsonl` through the exact predicate the parents use today (`grep -oE '^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$'`, last match wins)
- [x] **State the adjudication procedure before counting.** "A real verdict is present" is established by a deliberately looser unanchored search over the final assistant message, producing a candidate set; the difference between the loose and strict match sets is adjudicated by hand. Report the raw strict count, the raw loose count, and the adjudicated miss count separately
- [x] Count the runs where the strict predicate found nothing but adjudication says a verdict was present — this is the headline number
- [x] Separately count runs where the predicate matched a verdict quoted from a *previous* pass rather than the run's own. The anchored, last-match-wins design is meant to prevent this, and the count tests that it does
- [x] State the sample size alongside every count. A zero over 60 logs is a different claim from a zero over 600
- [x] **Ruling:** if the adjudicated miss count is zero, the transport upgrade buys nothing *measurable at this scale*, the roadmap's "lead with the measurement argument" decision becomes load-bearing rather than stylistic, and Phase 3's justification is rewritten accordingly. If it is non-zero, record each miss's cause

#### E5 — Observed

**Corpus: 73 archived JSONL**, not the 60 this doc recorded on 2026-08-07 — the fleet ran 13 more times on 2026-08-08 alone. Replay tool kept at [`scripts/helpers/measure/replay_completion_predicate.py`](../../../scripts/helpers/measure/replay_completion_predicate.py); its module docstring states why it is kept rather than deleted as a one-shot (the denominator grows, and `D-007` re-reads this number).

**Adjudication procedure, stated before the counts, exactly as required.**
- **Strict** = the predicate verbatim from `review-pr.sh:186` / `routing.py:43` (`^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$`, multiline, last match wins), and verbatim from the six PR-URL declarations, applied to `.result` as `run-claude.sh:201-204` applies it.
- **Loose** = deliberately weaker: unanchored, case-insensitive, tolerant of markdown emphasis and leading whitespace (`VERDICT:?\s*\**\s*(MERGE|HOLD)`). This is the candidate set.
- A log is a **miss** only where strict found nothing *and* hand adjudication of the envelope says a real terminal outcome was present. Every strict/loose difference and every strict-negative was opened by hand; the adjudications are recorded below individually.

**Scoping correction — 22 of the 73 are anachronistic and are excluded, with the exclusion stated rather than hidden in a denominator.** Applying today's predicate to a log from a workflow that did not declare one measures a rule that was not in force. `revision` (6) and `revision-major` (13) are **retired** — no such script exists in `scripts/workflows/` today. `review-runs` (3) exists but declares no `COMPLETION_PATTERN` at all. All 22 are from 2026-04. **In-scope corpus: 51 logs** across the 10 workflows that declare a pattern today — **50 once the in-flight self-log is removed** (see the correction under the adjudication table), which is the denominator every count below should be read against.

| | denominator | strict matched | strict found nothing | loose matched | strict ≠ loose |
|---|---|---|---|---|---|
| **`VERDICT` predicate** (`review-pr`) | **14** | **14** | **0** | 14 | **0** |
| **PR-URL predicate** (9 workflows) | **37** | **34** | **3** | 34 | **0** |
| in-scope total | **51** | 48 | 3 | 48 | **0** |
| *(excluded: retired / no pattern)* | *22* | *17* | *5* | *17* | *0* |
| **corrected** — in-flight self-log removed | **50** | 48 | **2** | 48 | **0** |

**Two of the nine PR-URL workflows declare a wider pattern than this table replayed.** `plan-revision` and `plan-new` gate on `/(pull|issues)/` — a STOP **issue** URL is a lawful completion for them (`plan-revision.sh:220`, `plan-new.sh:245`, `plan_revision_workflow.py:49`; E6's P6 row is the same path seen from the parent). The replay originally applied the pull-only pattern to all nine. **Both archived `plan-revision` logs completed via `pull/` URLs, so no count above changes** — verified by re-running with the corrected pattern. The tool now carries `PR_OR_ISSUE_URL` for those two workflows, because the next issue-URL completion would otherwise be scored as a miss and inflate exactly the number this experiment exists to report honestly.

**The three in-scope strict-negatives, adjudicated individually — all three are CORRECT REJECTIONS, none is a miss:**

| Log | Envelope | Adjudication |
|---|---|---|
| `build-draft-minor-20260806-173722` | `subtype: error_max_turns`, `num_turns: 101/100`, **`result` key absent**, `errors: ["Reached maximum number of turns (100)"]` | No PR URL anywhere in the file. The run genuinely produced nothing. Correct rejection. |
| `build-draft-minor-20260808-122206` | `subtype: error_max_turns`, `num_turns: 101/100`, **`result` key absent** | **A `github.com/…/pull/N` URL IS present in the file** — the run opened a PR and then died at its cap. The predicate correctly reports no completion (nothing was in `.result` because there was no `.result`), and `run-claude.sh:167` fires first regardless. Correct rejection — but see the ruling. |
| `build-draft-20260808-145403` | **no `result` event at all** — the JSONL ends without one | ~~Truncated log. `jq -r '… .result // ""'` yields `""` and the check fails loud. Correct rejection.~~ **NOT A FLEET OBSERVATION — see the correction below.** |

> **CORRECTION (build-refine, 2026-08-08). The third strict-negative was this measurement observing its own in-flight run, and it should not have been in the corpus.** `build-draft-20260808-145403.jsonl` is the log of the build-draft run that *wrote this table*. It had no `result` event because it had not finished yet — not because anything failed. It has since completed, and replaying it now yields a **strict match** (`.result` carries the PR #66 URL). Corrected figures at the time of measurement: **72 completed logs, 50 in-scope, 2 strict-negatives** — both `error_max_turns`, both genuine — not 73 / 51 / 3. **The adjudicated miss count of 0 is unchanged in either accounting**, since a completed self-log is a match rather than a miss, so no ruling moves. What moves is the denominator and one adjudication row that described a measurement artifact as a fleet property, in a doc whose closing line is *"sample-size honesty is a requirement, not a courtesy."*
>
> **This recurs on every re-run unless it is handled**, because the tool is kept to be re-run and any run invoking it has its own open log in the directory. `replay_completion_predicate.py` now lists every envelope-less log separately, under a header saying they are in-flight-or-truncated and must be adjudicated before being counted as misses.

**Adjudicated miss count: 0 of 50 completed in-scope logs** (0 of 51 counting the in-flight self-log, which is a match now that it has finished — the zero does not depend on which accounting is used). **Zero of 14** for the `VERDICT` predicate specifically.

**Quoted-prior-pass matches: 0 of 14.** No `review-pr` log contained more than one strict `^VERDICT:` match anywhere in its assistant-text stream, so the anchored last-match-wins design was never even put under load. One log had two strict matches (`revision-major-20260410-115958`, two PR URLs) — out of scope, retired workflow, and PR-URL not `VERDICT`.

**A surface difference between the two parsers, found while reconstructing the predicate and worth recording because it is not what the design assumes.** `run-claude.sh:204` applies the pattern to `jq -r '.result'` — the final result only. `build.sh:277` and `build-minor.sh:281` apply it to `"$log"`, the **tee'd console output of the whole child process**, which carries every streamed assistant message. The parent's surface is strictly wider than the child's. Replayed over the reconstructed assistant-text stream, the two surfaces agreed on **50 of 50** completed in-scope logs — but that is agreement by luck of the corpus, not by construction: a model that writes a well-formed `VERDICT:` line mid-run and then a different one at the end would route the parent one way and pass the child's gate another.

**Turn-cap rate, cross-checked against this doc's own cited figure.** `run-claude.sh:159` records **0.9% (4/443 runs, 3 of them from April)**. The archived corpus shows **2 `error_max_turns` in 72 completed logs (2.8%)**, or **2 in 50 completed in-scope (4.0%)** — and *both are from August* (2026-08-06, 2026-08-08), where the cited figure had only one non-April occurrence. The two denominators are not the same population (443 runs vs 73 archived logs), so this is **not** a claim that the rate rose. It is a flag: the cited comment's own reopen condition is "if the rate climbs", and the only sample that can be checked today runs 3–4× the recorded figure. Surfaced for the operator; not fixed here.

#### E5 — Ruling

**NO-OP for the defect argument, and it CHANGES what Phase 3's justification is allowed to say.**

The adjudicated miss count is **zero over 50 completed in-scope logs, zero over the 14 that carry the `VERDICT` predicate**. The strict and loose match sets are identical — there is not a single log where a real verdict was present in a shape the anchored predicate could not see. The prose grep has never, in the archived history, produced a wrong route or a missed one.

**Consequences, named:**

1. **Phase 3's justification is rewritten to lead with the measurement, and the measurement is this zero.** The roadmap's "lead with the measurement argument" decision becomes **load-bearing rather than stylistic**: a Phase 3 doc that opens by calling the incumbent broken would be contradicted by its own phase's evidence.
2. **The transport upgrade's case does not rest here — it rests on E1(d).** E5 found no defect in the predicate *given a `.result` to read*. E1 found that on every error subtype **there is no `.result` to read at all**, and this replay reproduced that in the wild: 2 of 50 completed in-scope runs (4.0%) had the `result` key absent, one of them after having already opened a PR. **The prose channel's failure mode is not misparsing; it is non-existence.** Phase 3 argues from the channel's absence under failure, not from the grep's accuracy. That is a stronger and a *measured* argument, and it is the one E5 was supposed to be able to supply in either direction.
3. **The `zero` is small and must be reported as small.** 14 logs for the `VERDICT` predicate is a thin base. This ruling states a zero over 14, not a zero over the fleet's history.

**What this feeds — `D-007`, and this is written to be usable as that row's evidence directly.** Open direction row `D-007` (`docs/standards/architecture/research/direction.md:67`) asks whether the VERDICT-token-on-stdout completion contract *stands unchanged*, *gains a write-time gate*, or *is replaced*. Its stated tension is that every located comparable system pairs machine-parsing-a-human-artifact with authoring-time enforcement while ours has none, against no evidence the incumbent ever mis-routed. **This experiment supplies the missing half of that: the miss count is 0/14 for the token specifically and 0/50 completed in-scope logs across all three patterns, with the loose set identical to the strict set.** Two further inputs `D-007` did not have: (a) a write-time gate **already exists** on the child side — `run-claude.sh:201-204` fails the run loud when the pattern is absent from `.result`, which is authoring-time enforcement by any reasonable reading, so the "ours has none" premise is *false as stated*; and (b) the parent's parse surface (`build.sh:277`, the whole console) is wider than the gate's (`.result`), so the gate does not cover everything the parent reads. **`D-007` is the operator's to rule and this phase does not rule it** — but the ruling it needs to make is now the narrower one of whether that surface mismatch is worth closing, not whether the token has been missing routes.


### E7 — Does the convergence delta ever fire?

*Because:* [Phase 5](phase5_convergence_stopping.md) builds a computed convergence signal, and if the delta between consecutive passes is never empty over the fleet's real history, that signal is decorative and Phases 3 and 4 would have been built partly to serve it. **This measurement was originally scheduled inside Phase 5 itself, which is exactly the "gate the same run walks past" failure this phase exists to prevent.** Its corpus exists today: archived PRs carry `pr_review:` blocks with `pass:`, stable finding ids and `converged`.

- [x] Enumerate archived PRs carrying more than one `pr_review:` block and extract each block's `pass`, finding `id` set, and `converged` value
- [x] Compute the finding-id delta between consecutive passes and count how often it was empty
- [x] Count how often the shipped `converged: true` was asserted, and cross-tab it against the computed delta — the two disagreeing is the most informative cell, because it is the difference between the class-(iii) heuristic and the class-(ii) computation
- [x] Count how often the same finding recurred across passes under the same id, versus recurring under a new id — this measures whether the stable-id convention actually holds in practice, which [Phase 5](phase5_convergence_stopping.md) depends on outright
- [x] Report every count with its denominator
- [x] **Ruling:** if the delta is never empty, Phase 5's predicate never fires and the phase says so before it is built. If the stable-id convention does not hold, Phase 5's step 1 becomes the phase's hard part rather than its premise

#### E7 — Observed

**Corpus: all 38 PRs** in `helloskyy-io/Claude-Dot-Files` (6 closed, 32 merged, 0 open). Extraction tool kept at [`scripts/helpers/measure/replay_pr_review_blocks.py`](../../../scripts/helpers/measure/replay_pr_review_blocks.py).

- PRs carrying **≥1** `pr_review:` block: **7 of 38** (18%)
- PRs carrying **>1**: **5 of 38** (13%) — #31, #33, #42, #45, #58
- `pr_review:` blocks total: **14**
- Consecutive-block pairs available for a delta: **7**

**The finding-id delta between consecutive passes, all 7 pairs:**

| PR | passes | ids **added** | ids **dropped** | findings before → after |
|---|---|---|---|---|
| #31 | 1 → 2 | **2** | 0 | 18 → 20 |
| #31 | 2 → 4 | **4** | 0 | 20 → 24 |
| #33 | 1 → 2 | **5** | 0 | 11 → 16 |
| #42 | 1 → 2 | **3** | 0 | 6 → 9 |
| #45 | 1 → 2 | **5** | 0 | 15 → 20 |
| #58 | 1 → 2 | **5** | 0 | 10 → 15 |
| #58 | 2 → 3 | **1** | 0 | 15 → 16 |

**Pairs with an empty delta: 0 of 7.** **Pairs where any id was dropped: 0 of 7.** The finding-id set is **strictly monotonically growing** in every observed pass sequence — no pass ever carried fewer ids than the one before it, and the smallest delta observed was 1.

> **CORRECTION (build-refine, 2026-08-08). Both of those numbers are guaranteed by the reporting schema, and the table above measures the wrong set.** The `pr_review:` block is **cumulative**: `review-pr.sh:221` instructs each pass to reuse every prior finding's id slug verbatim, and the archive does exactly that — **pass N restates every id pass N-1 carried and updates that finding's `disposition` in place** (`hold` → `fixed` / `deferred` / `rejected`). Verified directly against PR #58: all 10 of pass 1's ids reappear in pass 2, seven of them flipped to `disposition: fixed`. So an id *cannot* be dropped and the full set *cannot* shrink, at any N, for any fleet behaviour. "0 dropped of 25" is a tautology of the block's shape, not a measurement of the stable-id convention, and "the convention holds in both directions" claimed more than the corpus can show. The **added** column is unaffected and remains a genuine empirical result. The set that carries meaning is measured below.

**The OPEN-subset delta — the set that can actually go empty.** Recomputed over the findings still carrying outstanding work in each block (`disposition` not in `{fixed, deferred, rejected, noted}`) — **and the `escalated` half of that partition is a DEFINITIONAL choice this corpus does not constrain.** `escalated` appears on 2 of 195 archived findings and on none inside the 7 measured pairs, so **every figure in the table below is identical whether `escalated` counts as open or closed**; the numbers are correct either way and none of them is evidence for the choice. It is counted as open because an escalation moves work to another authority rather than completing it — a reading of the taxonomy, not a measurement. **Phase 5 must rule it explicitly rather than inheriting it from here**, and what would settle it is a corpus containing an escalated finding inside a multi-pass block. Same 7 pairs, same corpus:

| PR | passes | all ids | open ids | open **added** | open **closed** |
|---|---|---|---|---|---|
| #31 | 1 → 2 | 18 → 20 | 6 → 2 | 1 | **5** |
| #31 | 2 → 4 | 20 → 24 | 2 → 2 | 2 | 2 |
| #33 | 1 → 2 | 11 → 16 | 5 → 1 | 1 | **5** |
| #42 | 1 → 2 | 6 → 9 | **2 → 0** | **0** | 2 |
| #45 | 1 → 2 | 15 → 20 | 2 → 1 | 1 | 2 |
| #58 | 1 → 2 | 10 → 15 | 7 → 2 | 2 | **7** |
| #58 | 2 → 3 | 15 → 16 | 2 → 2 | **0** | 0 |

**Pairs whose OPEN delta is empty: 2 of 7** (#42 1→2, #58 2→3) — against **0 of 7** for the all-ids delta. Ids leave the open set constantly (5, 2, 5, 2, 2, 7, 0 closed per pair); the all-ids view erased every one of those transitions, which is the entire convergence motion the archive contains.

**The open set reaches zero exactly once in 14 blocks — PR #42 pass 2**, which is also the only `MERGE` verdict and the only `converged: true` in the archive.

**Per-finding vocabulary actually shipped, counted across all 195 archived findings.** `disposition` — `fixed` 74, `deferred` 58, `hold` 37, `rejected` 21, `noted` 3, `escalated` 2. `category` — `correctness` 67, `doc-drift` 30, `standards-implication` 29, `test-gap` 28, `scope` 16, `deferral` 14, `friction` 10, `security` 1. **A `severity` field appears on 0 of the 195.** Every finding carries a `disposition`; none carries a severity.

**`converged` cross-tab — 14 blocks, every one carrying the key:**

| | computed delta empty | computed delta non-empty | no prior block |
|---|---|---|---|
| `converged: true` | **0** | **1** | 0 |
| `converged: false` | **0** | 6 | 7 |

**`converged: true` was asserted exactly once in 14 blocks** — PR #42 pass 2, the only `MERGE` verdict in the corpus. Its computed delta was **3 newly-added ids** (`escalation-locator-miscited`, `nmo-source-count-33`, `analyst-fetch-asymmetry-remedy-unlisted`).

> **CORRECTION (build-refine, 2026-08-08). The one cell with data is AGREEMENT, not disagreement — the original reading was an artifact of computing the delta over the cumulative set.** PR #42 pass 2 has **0 open findings**: all nine of its ids are `fixed`, `deferred` or `rejected`. So the class-(iii) heuristic (`review-pr.sh:323` — "this pass's only findings are preventive") and the class-(ii) computation over the **open** subset both say converged. **They agree, 1 of 1.** The three "newly-added" ids are new findings that were *disposed within the same pass*, which is exactly what the heuristic's "only preventive findings" wording describes. The previous claim — *"they are measuring different things and the archive contains no case where they agree"* — was wrong, and it was the load-bearing premise for replacing the computed signal rather than re-scoping it.

**Corrected cross-tab, over the OPEN subset — 14 blocks, every one carrying the key:**

| | open delta empty | open delta non-empty | no prior block |
|---|---|---|---|
| `converged: true` | **1** | **0** | 0 |
| `converged: false` | **1** | 5 | 7 |

The one `converged: false` with an empty open delta is #58 pass 2→3 — two open findings carried forward unchanged, none closed, none added. A stopping rule reading *"the open set stopped changing"* would have fired there and been **wrong**; a rule reading *"the open set is empty"* would not have. That distinction is a Phase 5 design input, and it is now measured rather than assumed.

**Stable-id convention — it holds.** 25 ids were added across the 7 pairs. Each was adjudicated against the prior pass's id set by slug and title; the two closest candidates had their finding bodies read in full:

- `quality-control-findings-have-no-slot-in-the-shipped-artifact` (#45 pass 2) vs `security-lens-findings-have-no-slot-in-the-shipped-pr-body-template` (#45 pass 1) — near-identical phrasing, but the bodies show a **different reviewer, different lines, different fix**; the pass-1 finding was already fixed by pass 2. **Distinct.**
- `merge-drops-the-model-key-guard` (#31 pass 4) vs `merge-drops-executability-guard` (#31 pass 1) — same defect *shape*, two different guards. **Distinct.**

**0 of 25 added ids are a restatement of an existing finding under a new slug.** That is a genuine adjudication over the added column and it stands.

> **CORRECTION (build-refine, 2026-08-08).** The companion claim — *"0 of 25 prior ids were dropped or renamed; the convention holds in both directions"* — **is not a measurement.** The block is cumulative, so no id can be dropped regardless of what the reviewer does (see the correction above). What the corpus supports is the **added** direction only: when a finding persists it keeps its slug, adjudicated 25 of 25. Phase 5 may rely on that. It may **not** treat "ids never disappear" as evidence about reviewer behaviour, because the reporting shape guarantees it either way.

**Two structural facts Phase 5 needs and the archive does not advertise:**

1. **Pass numbers are not dense.** PR #31's blocks are `pass: 1`, `pass: 2`, `pass: 4` — there is no pass 3 block. "Consecutive passes" therefore **cannot** be derived from the `pass` integer; it must come from the ordering of the blocks that exist.

   > **CORRECTION (Phase 2, 2026-08-08). The instruction stands; the CAUSE stated here is wrong, and the difference matters because one is permanent and the other is fixable.** Non-density is not a property of the archive. **The pass counter over-matches:** `review-pr.sh:142` and `review_pr_activities.py:51` count any comment merely *mentioning* the string `pr_review:`, while only `replay_pr_review_blocks.py:45` is fence-anchored — 18 matches against 15 over all 39 PRs, **3 false positives**. *(Denominator note, since this section's own E7 header states **38**: both figures are as-measured on their own dates and neither is corrected here. Phase 5 must not mix them in a rate.)* #31's missing pass 3 is a `build-refine` comment that was counted, and **#66's single block is labelled `pass: 3` when it is pass 1**. So `pass:` is not merely sparse — it is **wrong**, durably, on the most recently reviewed PR in the repo, and it is a two-file fix. Phase 5 should still derive consecutiveness from block ordering; that is now a defence against a producer-written counter being wrong, which is the general rule stated at [`memory-model.md` §6.1](../../guide/memory-model.md), rather than an accommodation of a gap. Measured and documented at [`memory-model.md` §6.4](../../guide/memory-model.md).
2. **An id is stable; its `title` is not.** #45's `security-lens-findings-have-no-slot-in-the-shipped-pr-body-template` appears in both passes under the same id with a *completely rewritten* title and consequence — pass 1 states the defect, pass 2 states the fix ("the security lens now reaches the durable artifact on both Stage 6 paths"). A convergence computation that compared titles, or hashed the finding body, would see change on every pass regardless.

#### E7 — Ruling

> **THIS RULING WAS RE-TAKEN (build-refine, 2026-08-08) AND ITS CONSEQUENCE REVERSED.** The draft measured the delta over the *cumulative* id set, which cannot go empty by construction, and concluded from 0-of-7 that set-difference is the wrong mechanism. Re-measured over the **open** subset — the only one the schema lets change — the delta goes empty **2 of 7**, and the set empties completely on exactly the one PR that converged. The mechanism is right; the *set* was wrong. **The original ruling would have cancelled a working predicate and redirected Phase 5 onto a `severity` field that does not exist in a single one of the 195 archived findings.** Both the superseded text and the corrected ruling are kept below, because the failure mode — measuring a monotone-by-construction set and reading its monotonicity as a fleet property — is the reusable lesson.

**CHANGES THE DESIGN — but the change is to the predicate's INPUT SET, not to its mechanism.**

Over the entire archived history — **7 consecutive-pass pairs across 5 PRs, the only 5 that have ever had more than one review pass** — the delta over **all** finding ids was empty **zero** times, because the `pr_review:` block restates every prior id and the set therefore cannot shrink. Over the **open** subset (`disposition` still outstanding) the same 7 pairs give an empty delta **2 times**, and the open set reaches **zero once — PR #42 pass 2, the only `MERGE` and the only `converged: true` in the archive.**

**Consequences, named:**

1. **[Phase 5](phase5_convergence_stopping.md)'s predicate is re-scoped, not replaced.** It computes the set difference over the **open** findings — those whose `disposition` is not one of `fixed` / `deferred` / `rejected` / `noted` — and its stopping condition is **the open set being EMPTY**, not merely unchanged. Both halves are measured: empty fired 1 of 14 blocks, precisely on the converged one; *unchanged-but-non-empty* fired at #58 pass 2→3, where stopping would have been **wrong**. A predicate reading "nothing changed" would have produced one correct stop and one incorrect one; "nothing is open" produced one correct stop and no incorrect ones.
2. **Phase 5 must NOT build on a `severity` field.** The draft ruling named one. **`severity` appears on 0 of the 195 archived findings** — the shipped per-finding vocabulary is `disposition` (6 values) and `category` (8). A predicate specified against `severity` would require inventing a field, backfilling it, and validating it, in place of one the fleet has emitted on every finding it has ever recorded.
3. **The shipped `converged` flag and the computed signal AGREE where both have a value — 1 of 1.** Phase 5 may therefore treat `converged` as a label the computation should reproduce, and has one archived positive case to check it against. This reverses the draft's consequence 2 outright.
4. **Phase 5's step 2 is NOT the phase's hard part — but for a narrower reason than the draft gave.** The stable-id convention is measured to hold on the **added** direction, 25 of 25 adjudicated. The "0 dropped" half is a property of the cumulative block, not evidence. Phase 5 may rely on ids; it may **not** rely on titles, on `pass` numbers being dense, or on id-disappearance meaning anything.
5. **This cancels nothing in Phases 3 and 4.** E1(d) and E1(f) give Phase 3 consumers independent of convergence, and Phase 4's `subtype` routing is independent of Phase 5 entirely.
6. **Denominator honesty, stated plainly.** 7 pairs, 5 PRs, 14 blocks, 195 findings, out of 39 PRs. **The open-set-empty predicate has exactly ONE positive observation.** One case is enough to falsify "it never fires"; it is nowhere near enough to establish a firing *rate*, and Phase 5 must not quote 1-of-14 as one. The honest statement is: the mechanism is viable and the archive contains a single confirming instance.

<details><summary><b>Superseded draft ruling (2026-08-08, kept for the lesson)</b></summary>

> **CHANGES THE DESIGN — Phase 5's predicate, as specified, never fires.**
>
> 1. An empty-delta predicate is decorative. The computed signal Phase 5 should build is a **severity/category-based** one over the typed findings, not a set-difference one.
> 2. The one cross-tab cell that has data is a **disagreement**, so Phase 5 cannot treat the shipped `converged` flag as a label to reproduce. 1 of 1.
> 3. The stable-id convention holds at 25/25 added and **0/25 dropped or renamed**.
> 5. A bigger corpus could contain an empty delta. It could not contain a *shrinking* id set without contradicting 7 of 7 observations.
>
> **Why it was wrong, in one line:** the id set is monotone *by construction*, so "7 of 7 observations of monotonicity" observed the schema, not the fleet — and every conclusion drawn from the monotonicity inherited that error.

</details>


### E2 — Does a turn-cap death leave a partial typed record?

*(Source: both papers' T2.)* *Because:* a run killed at its cap leaves no comment and possibly no final result. A **partial** typed record would be worse than none — absence has a declared meaning under the fail-safe contract, and a truncated record could satisfy a parser while carrying a wrong value. The fleet already measures the rate this matters at: **0.9%, 4 of 443 runs** (`run-claude.sh:157-160`), so this is rare but not hypothetical.

- [x] Force a low `--max-turns` on a task that cannot finish inside it, using each candidate transport still live after E1's ruling
- [x] Observe whether any typed artifact exists at the declared path, and if so whether it parses
- [x] Repeat for `SIGTERM` mid-run and for a run killed while the record is being written
- [x] Note that this experiment is **only meaningful for the file transport** — `structured_output` rides in the CLI's own result envelope and has no partial-record class. If E1 selects that transport, record that as the reason E2 is closed rather than run
- [x] **Ruling:** is absence the only absence path, or must Phase 3's contract also defend against a partial record? If the latter, name the mechanism — a consumer-side completeness check the parent enforces, with atomic write as an additional producer-side measure — as a Phase 3 requirement

#### E2 — Observed

**This experiment was RUN, not closed by E1's transport ruling — and running it was the right call.** The checklist offered to close E2 on the reasoning that *"`structured_output` … has no partial-record class."* That is an assertion about a vendor binary's behaviour, of exactly the kind this phase exists to stop taking on trust, and it costs four haiku calls to check. It was checked. **The assertion is correct, and checking it found a second absence path the design did not anticipate.**

Four runs, all with `--json-schema` declared, real child shape (`-w`, `--dangerously-skip-permissions`), 2.1.224:

| Forced condition | exit | `subtype` | `is_error` | `result` key | **`structured_output` key** | verdict |
|---|---|---|---|---|---|---|
| `--max-turns 1`, task needs more | 1 | `error_max_turns` | `true` | **absent** | **absent** | no artifact |
| `--max-budget-usd 0.005` | 1 | `error_max_budget_usd` | `true` | **absent** | **absent** | no artifact |
| `SIGTERM` at ~22s | 143 | `error_during_execution` | `true` | **absent** | **absent** | no artifact |
| **model cannot satisfy the schema** | **0** | **`success`** | **`false`** | **present** (prose) | **absent** | **no artifact, on a clean run** |

**No partial record was produced in any of the four.** In every case the key is **absent entirely** — never present-and-truncated, never present-and-invalid. There is no state between "a validated object" and "no key".

**The mechanism, observed rather than assumed.** `--json-schema` is implemented as a **`StructuredOutput` tool the model must call**. The schema-violation run's own assistant turn says so verbatim: *"the tool's schema constrains the `verdict` parameter to an enum that only accepts `MERGE` or `HOLD` … I can't call the tool with `BANANA`."* The model declined to call the tool and asked a clarifying question instead. The run **completed successfully** — exit 0, `subtype: success`, `is_error: false`, `.result` carrying 200 characters of polite prose — and emitted **no `structured_output` at all**.

**That is a second absence path, and it is the dangerous one.** The three error rows are loud: every signal the fleet reads already says the run died. The fourth row is **silent** — every signal says clean, and the typed record is simply not there.

#### E2 — Ruling

**Absence IS the only absence path — CONFIRMS Phase 3's contract shape. But the population of that arm is larger than the design assumed, which CHANGES one Phase 3 requirement.**

**(a) No partial-record defence is needed. CONFIRMS.** 0 of 4 forced deaths produced a partial or unparseable record. Phase 3 therefore does **not** need the consumer-side completeness check or the producer-side atomic write the checklist named as the contingency. **Consequence: that requirement is dropped from Phase 3, and this is the measurement that drops it** — one fewer mechanism to build, test and document. This is the transport's real advantage over a file, and it is now measured rather than argued: a file transport would have all four of these rows *plus* a genuine partial-write class.

**(b) A `success` run with no typed record is a REAL, REACHABLE state. CHANGES THE DESIGN (Phase 3).** The fail-safe contract cannot be written as "absent record ⟹ the run died", because the fourth row is a run that did not die. Phase 3's residual arm must be reachable from `subtype: success`, and the parent must not infer failure from absence — it must record *absence* as its own named state, which is exactly what the `podFailurePolicy`-derived shape Phase 3 already borrows is for. **Consequence:** Phase 3's fail-safe contract gains an explicit ordered rule for `subtype == success && structured_output absent`, distinct from its rule for the error subtypes, and the residual arm's documented population includes "the model declined to call the `StructuredOutput` tool." Phase 3's checklist is amended below.

**(c) One design constraint falls out of the mechanism, and it is not a fail-safe question.** Because the schema is a *tool the model chooses to call*, the record's presence is **model-dependent**, not transport-dependent. A schema the model finds unsatisfiable — an over-constrained enum, a required field the run has no value for — produces silence rather than an error. **Consequence for Phase 3's schema design:** every required field must be one the child can always fill, and the abstention vocabulary Phase 3 already specifies (a computed *could-not-check* arm and an asserted *needs-a-ruling* arm) is what makes that possible. This measurement is the reason that vocabulary is load-bearing rather than decorative — without an in-schema way to say "I don't know," the model's only remaining option is to not call the tool at all.


### E3 — The disagreement four-cell table

*(Source: `non_model_observables.md` T3.)* *Because:* no surveyed system defines precedence between an asserted result and a computed one, since none has an asserting producer. There is no prior art to borrow, so the fleet must pick — and it should pick knowing which cells actually occur.

- [x] **Determine the data source first, and state it.** The result envelope carries `is_error` whether or not any script reads it, so the archived JSONL very likely already contain the tuple. Check. If they do, this experiment is retrospective over the archived corpus, N is the archived count, and no instrumentation ships
- [x] Only if the archived logs do not carry it: instrument, **without changing routing behaviour**, and state the expected elapsed time to reach N ≥ 30. Phase 3's disagreement-policy and to-do-bit requirements are the only two that block on this, and the doc must say so rather than letting the whole of Phase 3 inherit an unbounded wait
- [x] Record the cross-tab of (`is_error` clean / dirty) × (`VERDICT:` MERGE / HOLD); name empty cells explicitly as empty rather than omitting them
- [x] Count the disagreements between each PR's `pr_review:` verdict and that PR's open/closed state — the input to the **who owns the to-do bit** ruling that Phase 3 must make and that nothing upstream decides
- [x] **Ruling:** if the off-diagonal cells are empty, Phase 3 adopts the record-both-under-distinct-names shape anyway (it costs one field and preserves the option) but **builds no composition machinery** for a case that has never occurred — and the doc says that is why

#### E3 — Observed

**Data source, determined and stated first as required: the archived JSONL DO carry the tuple.** All **14 of 14** `review-pr` result envelopes carry `is_error`, and all 14 carry a `.result` from which the `VERDICT:` token parses. **This experiment is retrospective; N is the archived count; no instrumentation ships and none is needed.** The second checkbox's instrumentation branch is therefore closed unbuilt, which is the outcome it was written to make possible — Phase 3's disagreement-policy and to-do-bit requirements inherit no wait at all.

**Cross-tab — (`is_error`) × (`VERDICT:`), N = 14 (every archived `review-pr` log):**

| | `VERDICT: MERGE` | `VERDICT: HOLD` | no VERDICT parsed |
|---|---|---|---|
| **`is_error: false` (clean)** | **1** | **13** | **0 — empty** |
| **`is_error: true` (dirty)** | **0 — empty** | **0 — empty** | **0 — empty** |

**The entire `dirty` row is empty, and so is the clean/no-VERDICT cell. Named as empty, per the requirement.** Subtype was `success` on all 14; `is_error` was `false` on all 14.

**The empty cells are empty BY CONSTRUCTION, not by small N — and that is the whole finding.** E1(d) measured that on every error subtype the `result` key is **absent from the envelope entirely**. A dirty run therefore has no `.result`, so there is no `VERDICT:` token to disagree with. E2 measured the same for `structured_output`, the transport Phase 3 will use. **The two rows cannot both be populated for the same run, at any N, under either transport.** Waiting for a bigger corpus would not fill a single off-diagonal cell.

**To-do-bit disagreement — last typed `pr_review:` verdict × PR terminal state. Denominator: 7 PRs carrying ≥1 block, of 38 total:**

| PR | terminal state | last block's `verdict` | last block's `converged` | blocks |
|---|---|---|---|---|
| #31 | MERGED | **HOLD** | false | 3 |
| #33 | MERGED | **HOLD** | false | 2 |
| #42 | MERGED | MERGE | true | 2 |
| #45 | MERGED | **HOLD** | false | 2 |
| #51 | MERGED | **HOLD** | false | 1 |
| #56 | MERGED | **HOLD** | false | 1 |
| #58 | MERGED | **HOLD** | false | 3 |

**6 of 7 PRs merged while their last durable typed verdict said HOLD.** The one agreement (#42) is the only `MERGE` verdict in the archive.

**Two honest caveats on that 6.** (i) A `HOLD` is a *runway*, not a rejection — a redispatch that cleared the runway need not have posted a further block, so "merged despite HOLD" does not by itself mean the operator overrode the reviewer. (ii) 0 of 38 PRs are open today, so the "open" state is unobserved in this corpus. **What the number does establish, and it is enough:** the last typed verdict in the durable record does **not** track the PR's disposition, in 6 of the 7 cases where both exist.

**And the larger denominator matters more than the 6.** **31 of 38 PRs (82%) carry no `pr_review:` block at all** — 25 merged, 6 closed. For those, open/closed is not merely the primary to-do bit; it is **the only one that exists**.

#### E3 — Ruling (two rulings — the checklist bundles two decisions and they resolve differently)

**(a) Disagreement policy — NO-OP, and stronger than "the cells are empty".** Phase 3 adopts the record-both-under-distinct-names shape (it costs one field and preserves the option) and **builds no composition machinery**. **The reason stated in Phase 3 is not "0 of 14 observed" but "structurally unreachable":** the asserted verdict lives in the same envelope key that E1(d) measured as *absent* on every run where `is_error` is true. A composition rule for "the model said MERGE but the runtime says the run failed" would be code for a state the transport cannot represent. **Consequence:** Phase 3 step 6's first checkbox is settled — two names, no policy engine — and the justification cites this structural fact rather than a count that a future reader would reasonably want to re-take at a larger N.

**(b) Who owns the to-do bit — CHANGES THE DESIGN (Phase 3). Kind 1 owns it; the typed verdict does not, and Phase 3 must say what the typed verdict is *for* instead.** The measurement is unambiguous: the typed verdict disagreed with the PR's disposition in **6 of 7** cases where both existed, and **did not exist at all in 31 of 38** PRs. A design that made the typed `verdict` the to-do bit would be making the rarer, less reliable signal authoritative over the one the fleet actually uses. **Consequences, named:**
1. **`open` remains the to-do bit** — the [Phase 2](phase2_kind1_framework.md) framing (*"open IS the to-do bit"*) is confirmed by measurement, not merely asserted.
2. **Phase 3 must state what the loser is for**, which its own checklist demands. The typed `verdict` is a **routing input for the immediate next dispatch decision, with a lifetime of one parent invocation** — it is not a durable record of whether work remains. That distinction is what makes 6 of 7 unsurprising rather than alarming: the two answer different questions over different lifetimes.
3. **Phase 3 must NOT add machinery to reconcile them.** Reconciling a one-invocation routing token against a durable human to-do bit is the composition engine ruling (a) just declined to build, in a second guise.


### E6 — The smallest envelope that routes every parent

*(Source: `dual_channel_outcome_records.md` T6.)* *Because:* the proposed envelope is roughly five fields derived from one caller, and every field a parent branches on becomes API surface the moment it does. The union must be enumerated, not guessed.

- [x] Enumerate every branch point in the bash parents (`build.sh`, `build-minor.sh`, `build-phase.sh`) **and** the Python parents under `scripts/workflows/temporal/modules/assistant/`, recording the value each one reads. Use language-agnostic patterns; a bash-shaped grep sees half the fleet
- [x] Add the values [Phase 5](phase5_convergence_stopping.md)'s convergence comparison needs — that consumer is specified
- [x] **Add nothing on behalf of [Autonomous Operation](../autonomous-operation/autonomous-operation.md).** Its own doc says it is not designed and not to be built toward; a field invented for it would become permanent API surface on a guess. Unanticipated consumers are served by Phase 3's additive `schema_version` extension rule
- [x] Take the union, and for each field state which consumer requires it. **A field with no named consumer does not enter the envelope**
- [x] Verify the enumeration is complete by grepping for prose parsing across both fleets (`grep -rnE "grep -oE|re\.search|re\.compile" scripts/workflows/`) and checking every hit is either in the list or explicitly out of scope
- [x] **Ruling:** the concrete field list Phase 3 writes down as its contract, with each field's consumer named beside it

#### E6 — Observed

**`build-phase.sh` is not a parent.** It was named in the checklist as one of three bash parents; it calls `run_claude` directly at `:502` and `:537` and invokes **no child**, so it has zero branch points on a child's output. Correcting that leaves **two** bash parents, not three.

**Every branch point on a child's output, both fleets. 15 sites.**

| # | Site | Value read | Read from |
|---|---|---|---|
| **B1** | `build.sh:198`, `build-minor.sh:202` | PR URL, **last match wins** | child's tee'd console |
| **B2** | `build.sh:199-203`, `build-minor.sh:203-207` | PR URL **absent** → hard `exit 1` | same |
| **B3** | `build.sh:205`, `build-minor.sh:209` | PR **number**, by `${PR_URL##*/}` string surgery | derived from B1 |
| **B4** | `build.sh:277`, `build-minor.sh:281` | VERDICT token, **last match wins** | child's tee'd console |
| **B5** | `build.sh:278-282`, `build-minor.sh:282-286` | VERDICT **absent** → synthesises `HOLD - needs-assistance` | same |
| **B6** | `build.sh:329-343`, `build-minor.sh:333-347` | **3-way** on the *full string*: `MERGE` / `HOLD - needs-assistance` / (fallthrough =) `HOLD - redispatch` | `VERDICT_LINE` |
| **B7** | `build.sh:359`, `build-minor.sh:363` | post-loop `== "VERDICT: MERGE"` | `VERDICT_LINE` |
| **B8** | `build.sh:236,266,304,327` (`\|\| exit 1`, `if ! …`) | child **process exit status** | process |
| **B9** | `run-claude.sh:167` | `.subtype == "error_max_turns"` | CLI result envelope |
| **B10** | `run-claude.sh:201-204` | `.result` matches `COMPLETION_PATTERN` | CLI result envelope |
| **P1** | `routing.py:72`, `review_pr_helper.py:84` | VERDICT token, last match wins | child stdout |
| **P2** | `routing.py:74-76` | VERDICT absent → `(HOLD_NEEDS_ASSISTANCE, was_parseable=False)` — **returns a second bit the bash fleet has no equivalent for** | same |
| **P3** | `routing.py:81`, used at `build_workflow.py:67`, `build_minor_workflow.py:57` | `verdict is HOLD_REDISPATCH and loops_used < MAX_LOOPS` | `Verdict` enum |
| **P4** | `routing.py:94`, `build_helper.py:24` | PR **number**, by regex; **raises** on absence rather than returning a sentinel | child stdout |
| **P5** | `build_workflow.py:74,77`, `build_minor_workflow.py:63,66` | 3-way on the `Verdict` enum | `Verdict` |
| **P6** | `plan_revision_workflow.py:86-95` | **an ISSUE URL as an alternative completion token**, plus a positional `rfind` tie-break when both a PR and an issue URL appear | child stdout |

**P6 is the site the bash-shaped grep would have missed, and it is the one that changes the envelope.** `plan-revision` may legitimately complete by opening a **STOP issue** instead of a PR. Because both rides are prose URLs in one text blob, the parent disambiguates by **which appears later in the output** (`output.rfind(pr) >= output.rfind(issue)`). That tie-break exists *only* because the channel is untyped; a typed field with a `kind` discriminator deletes it outright.

**Out of scope, checked and named rather than dropped.** The completeness grep (`grep -rnE "grep -oE|grep -qE|re\.search|re\.compile|re\.match|\.findall|\.search\("` over `scripts/workflows/`) returned **34 hits**. Every one is accounted for:

| Hits | Where | Why out of scope |
|---|---|---|
| 15 | the table above | in scope |
| 9 | `research-refresh.sh:159,161`, `paper-currency.sh:43,45,46`, `research_activities.py:32,33,34,52,55` | parse **research paper front-matter** (`Last validated:`, `Revalidate:`) — a document, not a child's output |
| 5 | `plan_activities.py:35,38,43,58,79`, `research_activities.py:91` | parse **planning tables** (`C-NNN`, `D-NNN` rows, sprint headings) — documents |
| 3 | `assistant_activities.py:68,210`, `review_pr_helper.py:133`, `review_pr_activities.py:65` | parse the **bash scripts' own source** for the V1↔V2 parity harness — not a runtime channel |
| 1 | `wait-for-ci.sh:61` | parses **`gh`'s** check states, not a child's |
| 1 | `build_workflow.py:90`, `build_minor_workflow.py:77` (`ci_settled`) | an **activity return value** from `wait_for_ci`, already typed; not a child's exit record |

**What Phase 5 needs, added because that consumer is specified.** Per E7's re-taken ruling: per-finding **`id`** (identity — measured to hold on the added direction, 25/25) and per-finding **`disposition`** (the field that decides whether a finding is still open, and therefore the input to the open-subset predicate). **Not** `pass`, which E7 measured as non-dense; **not** finding `title`, which E7 measured as unstable under a stable id; and **not `severity`**, which E7's correction measured as appearing on **0 of 195** archived findings.

**Nothing added on behalf of Autonomous Operation.** Checked and honoured: no field below exists for it.

**Three already-shipped `pr_review:` keys have ZERO programmatic readers**, verified by grep across both fleets excluding prompt strings and this phase's own measurement tools: **`converged`**, **`attempt`**, **`hold_kind`**. `hold_kind` is *aggregated by the model* into the VERDICT token (`routing.py:30` says so explicitly) and the token is what every parent reads. They are human-facing today.

#### E6 — Ruling: the field list Phase 3 writes down as its contract

**Nine fields. Each row names the consumer that requires it; a field with no named consumer is not here.**

| Field | Type | Required by |
|---|---|---|
| `schema_version` | string | The parent's version-skew rule — a child in a worktree on an older revision writing to a parent on `main` (Phase 3 step 1) |
| `outcome` | enum `merge` \| `hold` | **B6, B7, P3, P5** |
| `hold_kind` | enum `redispatch` \| `needs_assistance`, present iff `outcome == hold` | **B6, P3, P5** — every parent branches on the *sub-kind*, so "HOLD" alone does not route. Promotes an existing key with no code reader into one with four |
| `completion_ref.kind` | enum `pull` \| `issue` | **P6** — the sole reason `plan_revision_workflow.py`'s `rfind` tie-break exists. This field deletes that code |
| `completion_ref.number` | integer | **B3, P4** — both fleets currently recover it by string surgery on a URL |
| `completion_ref.url` | string | **B1, B2, P4**, and the human-facing banners at `build.sh:210,292` |
| `permission_denials` | count + per-entry `{tool_name, tool_use_id}`, **`tool_input` redacted** | **E1(f)** — an operator reviewing whether a dispatch tried something the hook stopped. Measured: the run exits **0** with `is_error: false` and `subtype: success`, so nothing else can answer it. Redaction per Phase 3 step 1 and `code_routed_control_flow.md` P13. *(This row proposed `matched_rule`, which this phase's own measured entry above does not contain — Phase 3 withdrew it for `tool_use_id`; see `exit-protocol.md` §2.2.)* |
| `findings[].id` | string slug | **Phase 5** identity, and Phase 3 step 8's render↔record invariant |
| `findings[].disposition` | enum — measured vocabulary `hold` \| `fixed` \| `deferred` \| `rejected` \| `noted` \| `escalated` | **Phase 5**'s stopping predicate. This is the field that partitions a block's findings into open and closed, and the open subset is the only set whose delta can go empty (E7's correction). Present on **195 of 195** archived findings, so promoting it costs no backfill |

**Explicitly NOT in the envelope, each with the reason — this half of the ruling is the one that keeps it small:**

| Excluded | Why |
|---|---|
| `is_error` | E1(a): `== (exit != 0)` on 8 of 8 measured modes |
| `num_turns` | E1(b): telemetry only; reported **2 against a cap of 1** |
| `subtype`, `terminal_reason` | **Runtime-produced, not child-authored.** `subtype` routes at `run-claude.sh:167` and stays exactly where it is — the CLI's own envelope, which E1(c) confirmed is the right place. `terminal_reason` duplicates it 1:1 |
| **`was_parseable` / any "the record is present" flag** | **A record cannot report its own absence.** P2 returns this bit today because prose parsing can half-succeed; under a typed transport it is the parent's residual arm (Phase 3 step 5), never a field |
| `converged` | Zero code readers today, and E7 measured it disagreeing with the computed signal 1 of 1. Phase 5 rules on the key; Phase 3 does not ship it as routing surface |
| `attempt` | Zero code readers. Human-facing continuity, and Kind 1's surface ([Phase 2](phase2_kind1_framework.md)) |
| `findings[].title`, `pass` | E7: title is unstable under a stable id; `pass` is not dense (#31 runs 1, 2, 4) |
| `findings[].severity` | **Does not exist.** 0 of 195 archived findings carry one. E7's draft ruling named it as Phase 5's predicate input; the correction replaced it with `disposition`, which every finding already carries. A field with no producer is worse than a field with no consumer |
| `findings[].category` | Real (8 measured values) and human-useful, but **no named consumer**: E7's corrected predicate reads `disposition`, not `category`. Held out under this ruling's own bar; it enters later by the additive `schema_version` rule if a consumer appears |
| `ci_settled` | Already a typed activity return from `wait_for_ci`; not a child's exit record |
| anything for Autonomous Operation | Its own doc says it is not designed. Served by the additive `schema_version` rule |

**This CHANGES the design in one place worth naming.** The envelope the roadmap sized at *"roughly five fields derived from one caller"* is **nine**, and the four beyond the guess are `hold_kind` (four consumers, currently a human-facing key nothing reads), the `completion_ref` triple (which absorbs `plan-revision`'s issue-URL path — a second caller the five-field guess did not include), and `permission_denials`. **The union was enumerated, not guessed, and it was 80% larger than the guess.**


### Close-out

- [x] Every experiment above has its observed data recorded in this document — numbers and tuples, not summaries
- [x] Every experiment has one of the three ruling types, and each ruling names a downstream consequence in a specific phase. E1's observables get one ruling each, not one for the group
- [x] Any experiment that could not be run is recorded here with the reason and what it blocks; it is **not** dropped and it is **not** replaced with a guess
- [x] **The liveness question is closed by citation, not by measurement.** `../temporal-integration/research/raw/liveness_signal_measurement.md` already measured the `stream-json` event vocabulary and identified the progress signals. This phase's only obligation is to confirm nothing E1 or E2 observed contradicts that paper's findings, and to say so in one line. Re-deriving it here would produce an ad-hoc phase-doc measurement competing for authority with a critic-gated paper

**The one line, as required: nothing E1 or E2 observed contradicts `liveness_signal_measurement.md`.** Every stream event these thirteen runs produced — `system`/`init`, `system`/`thinking_tokens`, `rate_limit_event`, `assistant`, `user`, `result` — is in that paper's §2.3 observed vocabulary; its Finding C's `rate_limit_event` shape held (with the `seven_day`/`allowed_warning` variant noted in E1 rather than re-derived); and it is **current** (`Last validated: 2026-08-07`, `Revalidate: high — 3 weeks` → due 2026-08-28). Two `system` subtypes these runs produced are **not** in its §2.3 list — `api_retry` and `permission_denied` — which is an *addition* to that paper's enumeration, not a contradiction of it. Both are recorded in E1 with their full shapes; **surfacing them to that paper's next revalidation sweep is the right home, and this phase does not edit it.**

---

## Phase summary — the six rulings and what each one moved

| Exp. | Ruling type | Downstream consequence |
|---|---|---|
| **E1(a)** `is_error` | **no-op** | Removed from Phase 3's envelope; Phase 4's "read the rest of the envelope" loses its `is_error` component |
| **E1(b)** `num_turns` vs cap | **no-op** | Telemetry only in Phase 3, never a branch input |
| **E1(c)** `subtype` | **confirms** | Phase 4's envelope read narrows to `subtype` alone, now on measured evidence |
| **E1(d)** `.result` absent on error | **changes the design** | Phase 3 argues from the channel's *absence under failure*, not from grep accuracy |
| **E1(e)** auth ≡ `SIGTERM` in the envelope | **changes the design** | Phase 4 cannot route auth failure from the envelope; a live unbounded-hang gap surfaced to the operator |
| **E1(f)** `permission_denials[]` | **changes the design** | Required field in Phase 3's envelope, with a named consumer |
| **E1(g)** transport | **confirms** | `structured_output`, plus a new constraint: the schema is an inline shell argument |
| **E5** prose-grep miss rate | **no-op** for the defect argument | 0 misses / 50 completed in-scope; Phase 3's justification rewritten; `D-007` given its missing evidence and one false premise corrected |
| **E7** convergence delta | **changes the design** | **Phase 5's predicate is RE-SCOPED to the open subset, not replaced.** Over all ids the delta is empty 0/7 — but that set is cumulative and cannot shrink; over the **open** subset it is empty **2/7** and empties completely on the one converged PR. `disposition`, not `severity`, is its input |
| **E2** partial records | **confirms** + **changes** | Completeness check and atomic write DROPPED from Phase 3; a silent `success`-path absence added to its fail-safe contract |
| **E3(a)** disagreement policy | **no-op** | Two names, no composition engine — for a *structural* reason, not a small-N one |
| **E3(b)** to-do bit | **changes the design** | `open` owns it (6/7 disagreements, 31/38 PRs have no typed verdict); Phase 3 states what the typed verdict is for instead |
| **E6** envelope union | **changes the design** | Nine fields, not the roadmap's "roughly five"; `plan-revision`'s issue-URL path is a second caller the guess omitted |

**Amendments made to downstream phase docs, per this phase's own mandate:** [Phase 3](phase3_typed_exit_record.md) step 1 (E1, E2), step 5 (E2 — one requirement dropped, one added), step 6 (E3, two rows); [Phase 5](phase5_convergence_stopping.md) step 2 (E7 — premise confirmed, and one half of it withdrawn), step 3 (E7 — **predicate re-scoped to the open subset**), step 4 (E7 — one mode re-answered). Phase 4 is **not** amended: E1(c) and E1(e) change what it reads, but its checklist is written at a level that already accommodates both, and amending it to restate a Phase 1 ruling would duplicate rather than direct.

**Three rulings were re-taken during the build-refine pass (2026-08-08), all marked inline where they occur.** E7's, whose consequence **reversed** — it would have cancelled a working predicate and pointed Phase 5 at a field that has never shipped; E6's field list, which inherited that error via `findings[].severity`; and E5's denominator, which counted the measuring run's own in-flight log as a fleet observation. **No E1, E2 or E3 ruling moved**, and every measured figure in those experiments reproduced exactly on re-run. **The lesson generalises past this doc:** each of the three came from measuring an artifact the measurement itself was inside of, or whose shape guaranteed the answer — a cumulative ledger read as if it could shrink, and a log directory read while the reader was writing to it. *Ask what the reporting shape makes impossible before reading a zero as evidence.*

---

## Notes and gotchas

- **Any instrumentation must not change routing.** A measurement that alters the thing being measured produces a table describing the instrumented fleet, not the fleet.
- **E1's failure modes cost real API calls.** Use a trivial prompt; the measurement is of the envelope, not of the work.
- **`--max-budget-usd` and rate-limit exhaustion may not be forceable on demand.** If a mode cannot be induced, record it as un-measured rather than inferring the tuple from the others — the whole point of E1 is that the mapping is undocumented, and an inferred row would reintroduce exactly the assumption being tested.
- **Sample-size honesty is a requirement, not a courtesy.** Every count in this doc carries its denominator. The research pool's own critic pass caught three wrong counts across two papers, and this plan's first draft asserted a completion-pattern count that was half the true number because the grep was bash-shaped. The same discipline applies to every measurement taken here.
