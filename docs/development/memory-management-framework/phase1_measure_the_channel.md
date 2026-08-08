# Phase 1 — Measure the channel before designing it

**Component:** [Memory Management Framework](roadmap.md) · **Status: not started**

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
- **Cites but does not re-derive:** `docs/standards/architecture/research/raw/claude_code_integration_surface.md` §5 (no first-party exit-code table; the `system/api_retry` error enum) and §7 (the result-envelope field list). **Comes due 2026-08-22** — if this phase runs after that date, note the staleness in the ruling rather than silently relying on it.
- **Cites and does not re-derive:** `../fleet-reliability/research/raw/liveness_signal_measurement.md`, which already measured the `stream-json` event vocabulary and identified the progress signals. This phase does **not** re-run that measurement; see the close-out.

---

## §Runtime Verification

Required because this phase orchestrates an external runtime — the `claude` CLI, a vendor binary whose documented surface is the thing being measured.

**Date performed:** 2026-08-07 · **Host:** `puma-workstation-mint` · **Performed during:** the planning run that wrote this doc

```
$ claude --version
2.1.224 (Claude Code)

$ claude --help | grep -iE "json-schema|output-format"
  --json-schema <schema>                JSON Schema for structured output
  --output-format <format>              Output format (only works with --print):
```

**What this establishes.** `--json-schema` and `--output-format` are both present on the CLI actually installed here. The upstream paper documents `structured_output` as available from v2.1.205+; the installed version is **2.1.224**, so the transport this component's Key Decisions name as option (a) is not hypothetical. **What it does NOT establish** — and E1 is what settles it — is whether the flag delivers a validated `structured_output` under `--dangerously-skip-permissions`, inside a worktree, at a child's turn budget. Flag presence is not flag behaviour.

**The incumbent surfaces, verified by reading the shipped code** (not by citing a description of it):

| Fact | Where |
|---|---|
| The parent's shell propagates the child's non-zero exit through `tee` | `scripts/workflows/build.sh:60` (`set -euo pipefail`), `:266` |
| **Two** bash parents parse the routing token out of prose stdout | `scripts/workflows/build.sh:277` and `scripts/workflows/build-minor.sh:281` |
| Two bash parents extract the PR URL by anchored regex | `build.sh:198`, `build-minor.sh:202` |
| The runtime reads the envelope's `subtype` for turn-cap death | `scripts/workflows/activities/run-claude.sh:167` |
| The runtime reads `.result` against the declared completion pattern | `scripts/workflows/activities/run-claude.sh:201-204` |
| Measured turn-cap termination rate, already recorded by the fleet | `run-claude.sh:157-160` — **0.9% (4/443 runs)** |
| The routing vocabulary is declared once in the Python tree | `scripts/workflows/temporal/modules/assistant/routing.py:24-56`, re-exported at `review_pr/review_pr_helper.py:67` |
| Completion patterns are declared in **both** fleets | `grep -rnE "COMPLETION_PATTERN\s*=" scripts/` → **21** total: 11 bash, 10 Python |
| `review-pr` already emits a convergence flag and stable finding ids | `children/review-pr.sh:323` (the rule), `:355` (`converged: true\|false`), `:221` and `:357` (stable ids reused verbatim across passes) |
| Archived run logs available for replay | `.claude/logs/` at the repo root → 60 JSONL files as of 2026-08-07 |

**Two greps this phase must run with the right pattern.** `grep -rn "COMPLETION_PATTERN=" scripts/` finds only the 11 bash declarations — Python writes `COMPLETION_PATTERN = r"…"` with spaces and is invisible to it. Use `grep -rnE "COMPLETION_PATTERN\s*="`. The same applies to any enumeration this phase produces: **a bash-shaped grep measures one of the two fleets.**

**`is_error` and `permission_denials` appear nowhere in the fleet.** Verified 2026-08-07 — `grep -rn "is_error\|permission_denial" scripts/` returns nothing. Re-verify when the phase starts; a non-empty result changes E1's framing.

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

**Rate-limit exhaustion is UN-MEASURED, not inferred.** It cannot be forced on demand without deliberately burning the account's seven-day window, which is not a throwaway-prompt cost. Per this doc's own gotcha, no row is guessed for it. What *was* observed instead is a passive signal the research did not list: a top-level stream event

```json
{"type":"rate_limit_event","rate_limit_info":{"status":"allowed_warning","resetsAt":1786251600,
  "rateLimitType":"seven_day","utilization":0.83,"isUsingOverage":false,"surpassedThreshold":0.75}}
```

appeared unprompted in the `SIGTERM` run's stream. Exhaustion is therefore **predictable before it happens**, which is a stronger observable than the post-hoc exit code this experiment went looking for. `grep -rn "rate_limit_event" scripts/` → **0 hits**: nothing in either fleet reads it.

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

**Scoping correction — 22 of the 73 are anachronistic and are excluded, with the exclusion stated rather than hidden in a denominator.** Applying today's predicate to a log from a workflow that did not declare one measures a rule that was not in force. `revision` (6) and `revision-major` (13) are **retired** — no such script exists in `scripts/workflows/` today. `review-runs` (3) exists but declares no `COMPLETION_PATTERN` at all. All 22 are from 2026-04. **In-scope corpus: 51 logs** across the 10 workflows that declare a pattern today.

| | denominator | strict matched | strict found nothing | loose matched | strict ≠ loose |
|---|---|---|---|---|---|
| **`VERDICT` predicate** (`review-pr`) | **14** | **14** | **0** | 14 | **0** |
| **PR-URL predicate** (9 workflows) | **37** | **34** | **3** | 34 | **0** |
| in-scope total | **51** | 48 | 3 | 48 | **0** |
| *(excluded: retired / no pattern)* | *22* | *17* | *5* | *17* | *0* |

**The three in-scope strict-negatives, adjudicated individually — all three are CORRECT REJECTIONS, none is a miss:**

| Log | Envelope | Adjudication |
|---|---|---|
| `build-draft-minor-20260806-173722` | `subtype: error_max_turns`, `num_turns: 101/100`, **`result` key absent**, `errors: ["Reached maximum number of turns (100)"]` | No PR URL anywhere in the file. The run genuinely produced nothing. Correct rejection. |
| `build-draft-minor-20260808-122206` | `subtype: error_max_turns`, `num_turns: 101/100`, **`result` key absent** | **A `github.com/…/pull/N` URL IS present in the file** — the run opened a PR and then died at its cap. The predicate correctly reports no completion (nothing was in `.result` because there was no `.result`), and `run-claude.sh:167` fires first regardless. Correct rejection — but see the ruling. |
| `build-draft-20260808-145403` | **no `result` event at all** — the JSONL ends without one | Truncated log. `jq -r '… .result // ""'` yields `""` and the check fails loud. Correct rejection. |

**Adjudicated miss count: 0 of 51.** Zero of 14 for the `VERDICT` predicate specifically.

**Quoted-prior-pass matches: 0 of 14.** No `review-pr` log contained more than one strict `^VERDICT:` match anywhere in its assistant-text stream, so the anchored last-match-wins design was never even put under load. One log had two strict matches (`revision-major-20260410-115958`, two PR URLs) — out of scope, retired workflow, and PR-URL not `VERDICT`.

**A surface difference between the two parsers, found while reconstructing the predicate and worth recording because it is not what the design assumes.** `run-claude.sh:204` applies the pattern to `jq -r '.result'` — the final result only. `build.sh:277` and `build-minor.sh:281` apply it to `"$log"`, the **tee'd console output of the whole child process**, which carries every streamed assistant message. The parent's surface is strictly wider than the child's. Replayed over the reconstructed assistant-text stream, the two surfaces agreed on **51 of 51** logs — but that is agreement by luck of the corpus, not by construction: a model that writes a well-formed `VERDICT:` line mid-run and then a different one at the end would route the parent one way and pass the child's gate another.

**Turn-cap rate, cross-checked against this doc's own cited figure.** `run-claude.sh:159` records **0.9% (4/443 runs, 3 of them from April)**. The archived corpus shows **2 `error_max_turns` in 73 logs (2.7%)**, or **2 in 51 in-scope (3.9%)** — and *both are from August* (2026-08-06, 2026-08-08), where the cited figure had only one non-April occurrence. The two denominators are not the same population (443 runs vs 73 archived logs), so this is **not** a claim that the rate rose. It is a flag: the cited comment's own reopen condition is "if the rate climbs", and the only sample that can be checked today runs 3–4× the recorded figure. Surfaced for the operator; not fixed here.

#### E5 — Ruling

**NO-OP for the defect argument, and it CHANGES what Phase 3's justification is allowed to say.**

The adjudicated miss count is **zero over 51 in-scope logs, zero over the 14 that carry the `VERDICT` predicate**. The strict and loose match sets are identical — there is not a single log where a real verdict was present in a shape the anchored predicate could not see. The prose grep has never, in the archived history, produced a wrong route or a missed one.

**Consequences, named:**

1. **Phase 3's justification is rewritten to lead with the measurement, and the measurement is this zero.** The roadmap's "lead with the measurement argument" decision becomes **load-bearing rather than stylistic**: a Phase 3 doc that opens by calling the incumbent broken would be contradicted by its own phase's evidence.
2. **The transport upgrade's case does not rest here — it rests on E1(d).** E5 found no defect in the predicate *given a `.result` to read*. E1 found that on every error subtype **there is no `.result` to read at all**, and this replay reproduced that in the wild: 2 of 51 archived runs (3.9%) had the `result` key absent, one of them after having already opened a PR. **The prose channel's failure mode is not misparsing; it is non-existence.** Phase 3 argues from the channel's absence under failure, not from the grep's accuracy. That is a stronger and a *measured* argument, and it is the one E5 was supposed to be able to supply in either direction.
3. **The `zero` is small and must be reported as small.** 14 logs for the `VERDICT` predicate is a thin base. This ruling states a zero over 14, not a zero over the fleet's history.

**What this feeds — `D-007`, and this is written to be usable as that row's evidence directly.** Open direction row `D-007` (`docs/standards/architecture/research/direction.md:67`) asks whether the VERDICT-token-on-stdout completion contract *stands unchanged*, *gains a write-time gate*, or *is replaced*. Its stated tension is that every located comparable system pairs machine-parsing-a-human-artifact with authoring-time enforcement while ours has none, against no evidence the incumbent ever mis-routed. **This experiment supplies the missing half of that: the miss count is 0/14 for the token specifically and 0/51 across both patterns, with the loose set identical to the strict set.** Two further inputs `D-007` did not have: (a) a write-time gate **already exists** on the child side — `run-claude.sh:201-204` fails the run loud when the pattern is absent from `.result`, which is authoring-time enforcement by any reasonable reading, so the "ours has none" premise is *false as stated*; and (b) the parent's parse surface (`build.sh:277`, the whole console) is wider than the gate's (`.result`), so the gate does not cover everything the parent reads. **`D-007` is the operator's to rule and this phase does not rule it** — but the ruling it needs to make is now the narrower one of whether that surface mismatch is worth closing, not whether the token has been missing routes.


### E7 — Does the convergence delta ever fire?

*Because:* [Phase 5](phase5_convergence_stopping.md) builds a computed convergence signal, and if the delta between consecutive passes is never empty over the fleet's real history, that signal is decorative and Phases 3 and 4 would have been built partly to serve it. **This measurement was originally scheduled inside Phase 5 itself, which is exactly the "gate the same run walks past" failure this phase exists to prevent.** Its corpus exists today: archived PRs carry `pr_review:` blocks with `pass:`, stable finding ids and `converged`.

- [ ] Enumerate archived PRs carrying more than one `pr_review:` block and extract each block's `pass`, finding `id` set, and `converged` value
- [ ] Compute the finding-id delta between consecutive passes and count how often it was empty
- [ ] Count how often the shipped `converged: true` was asserted, and cross-tab it against the computed delta — the two disagreeing is the most informative cell, because it is the difference between the class-(iii) heuristic and the class-(ii) computation
- [ ] Count how often the same finding recurred across passes under the same id, versus recurring under a new id — this measures whether the stable-id convention actually holds in practice, which [Phase 5](phase5_convergence_stopping.md) depends on outright
- [ ] Report every count with its denominator
- [ ] **Ruling:** if the delta is never empty, Phase 5's predicate never fires and the phase says so before it is built. If the stable-id convention does not hold, Phase 5's step 1 becomes the phase's hard part rather than its premise

### E2 — Does a turn-cap death leave a partial typed record?

*(Source: both papers' T2.)* *Because:* a run killed at its cap leaves no comment and possibly no final result. A **partial** typed record would be worse than none — absence has a declared meaning under the fail-safe contract, and a truncated record could satisfy a parser while carrying a wrong value. The fleet already measures the rate this matters at: **0.9%, 4 of 443 runs** (`run-claude.sh:157-160`), so this is rare but not hypothetical.

- [ ] Force a low `--max-turns` on a task that cannot finish inside it, using each candidate transport still live after E1's ruling
- [ ] Observe whether any typed artifact exists at the declared path, and if so whether it parses
- [ ] Repeat for `SIGTERM` mid-run and for a run killed while the record is being written
- [ ] Note that this experiment is **only meaningful for the file transport** — `structured_output` rides in the CLI's own result envelope and has no partial-record class. If E1 selects that transport, record that as the reason E2 is closed rather than run
- [ ] **Ruling:** is absence the only absence path, or must Phase 3's contract also defend against a partial record? If the latter, name the mechanism — a consumer-side completeness check the parent enforces, with atomic write as an additional producer-side measure — as a Phase 3 requirement

### E3 — The disagreement four-cell table

*(Source: `non_model_observables.md` T3.)* *Because:* no surveyed system defines precedence between an asserted result and a computed one, since none has an asserting producer. There is no prior art to borrow, so the fleet must pick — and it should pick knowing which cells actually occur.

- [ ] **Determine the data source first, and state it.** The result envelope carries `is_error` whether or not any script reads it, so the archived JSONL very likely already contain the tuple. Check. If they do, this experiment is retrospective over the archived corpus, N is the archived count, and no instrumentation ships
- [ ] Only if the archived logs do not carry it: instrument, **without changing routing behaviour**, and state the expected elapsed time to reach N ≥ 30. Phase 3's disagreement-policy and to-do-bit requirements are the only two that block on this, and the doc must say so rather than letting the whole of Phase 3 inherit an unbounded wait
- [ ] Record the cross-tab of (`is_error` clean / dirty) × (`VERDICT:` MERGE / HOLD); name empty cells explicitly as empty rather than omitting them
- [ ] Count the disagreements between each PR's `pr_review:` verdict and that PR's open/closed state — the input to the **who owns the to-do bit** ruling that Phase 3 must make and that nothing upstream decides
- [ ] **Ruling:** if the off-diagonal cells are empty, Phase 3 adopts the record-both-under-distinct-names shape anyway (it costs one field and preserves the option) but **builds no composition machinery** for a case that has never occurred — and the doc says that is why

### E6 — The smallest envelope that routes every parent

*(Source: `dual_channel_outcome_records.md` T6.)* *Because:* the proposed envelope is roughly five fields derived from one caller, and every field a parent branches on becomes API surface the moment it does. The union must be enumerated, not guessed.

- [ ] Enumerate every branch point in the bash parents (`build.sh`, `build-minor.sh`, `build-phase.sh`) **and** the Python parents under `scripts/workflows/temporal/modules/assistant/`, recording the value each one reads. Use language-agnostic patterns; a bash-shaped grep sees half the fleet
- [ ] Add the values [Phase 5](phase5_convergence_stopping.md)'s convergence comparison needs — that consumer is specified
- [ ] **Add nothing on behalf of [Autonomous Operation](../autonomous-operation/autonomous-operation.md).** Its own doc says it is not designed and not to be built toward; a field invented for it would become permanent API surface on a guess. Unanticipated consumers are served by Phase 3's additive `schema_version` extension rule
- [ ] Take the union, and for each field state which consumer requires it. **A field with no named consumer does not enter the envelope**
- [ ] Verify the enumeration is complete by grepping for prose parsing across both fleets (`grep -rnE "grep -oE|re\.search|re\.compile" scripts/workflows/`) and checking every hit is either in the list or explicitly out of scope
- [ ] **Ruling:** the concrete field list Phase 3 writes down as its contract, with each field's consumer named beside it

### Close-out

- [ ] Every experiment above has its observed data recorded in this document — numbers and tuples, not summaries
- [ ] Every experiment has one of the three ruling types, and each ruling names a downstream consequence in a specific phase. E1's observables get one ruling each, not one for the group
- [ ] Any experiment that could not be run is recorded here with the reason and what it blocks; it is **not** dropped and it is **not** replaced with a guess
- [ ] **The liveness question is closed by citation, not by measurement.** `../fleet-reliability/research/raw/liveness_signal_measurement.md` already measured the `stream-json` event vocabulary and identified the progress signals. This phase's only obligation is to confirm nothing E1 or E2 observed contradicts that paper's findings, and to say so in one line. Re-deriving it here would produce an ad-hoc phase-doc measurement competing for authority with a critic-gated paper

---

## Notes and gotchas

- **Any instrumentation must not change routing.** A measurement that alters the thing being measured produces a table describing the instrumented fleet, not the fleet.
- **E1's failure modes cost real API calls.** Use a trivial prompt; the measurement is of the envelope, not of the work.
- **`--max-budget-usd` and rate-limit exhaustion may not be forceable on demand.** If a mode cannot be induced, record it as un-measured rather than inferring the tuple from the others — the whole point of E1 is that the mapping is undocumented, and an inferred row would reintroduce exactly the assumption being tested.
- **Sample-size honesty is a requirement, not a courtesy.** Every count in this doc carries its denominator. The research pool's own critic pass caught three wrong counts across two papers, and this plan's first draft asserted a completion-pattern count that was half the true number because the grep was bash-shaped. The same discipline applies to every measurement taken here.
