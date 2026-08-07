# Phase 1 — Measure the channel before designing it

**Component:** [Memory Management Framework](roadmap.md) · **Status: not started**

Five experiments the research could not settle and the design depends on. Two of them can shrink [Phase 3](phase3_typed_exit_record.md). This phase produces **a measured record, not a design** — every experiment ends in a written ruling, and the rulings are the deliverable.

---

## Requirements for completion

This phase is done when all five experiments below have run against the pinned CLI and the archived logs, each has its observed data recorded **in this document**, and each carries an explicit ruling of one of three kinds:

- **Changes the design** — names what in [Phase 3](phase3_typed_exit_record.md) must be different, and that phase's checklist is amended before it starts.
- **Confirms the design** — the Key Decision it bears on stands as written in the [roadmap](roadmap.md), with this measurement now cited as its evidence rather than a derived claim.
- **No-op** — the work the measurement was gating is not warranted, stated with the number that shows it.

"We ran it and it looked fine" is not a ruling. A ruling names a downstream consequence.

**Also required:** the `§Runtime Verification` block below is re-run and its date refreshed if this doc is substantively revised, per [Documentation Standard § Live-Runtime Verification](../../standards/documentation/documentation_standard.md).

---

## Dependencies

- **None built.** This phase depends only on the pinned `claude` CLI and the archived run logs, both of which exist today.
- **Evidence:** [`research/synthesis.md`](research/synthesis.md); experiment designs are taken from `research/raw/non_model_observables.md` §7 (T1, T2, T3) and `research/raw/dual_channel_outcome_records.md` §8 (T2, T3, T5, T6). Where the two papers number differently, this doc uses the label in its own experiment heading and cites both sources.
- **Cites but does not re-derive:** `docs/standards/architecture/research/raw/claude_code_integration_surface.md` §5 (no first-party exit-code table; the `system/api_retry` error enum) and §7 (the result-envelope field list). **Comes due 2026-08-22** — if this phase runs after that date, note the staleness in the ruling rather than silently relying on it.

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

**The incumbent routing surface, verified by reading the shipped scripts** (not by citing a description of them):

| Fact | Where |
|---|---|
| The parent's shell propagates the child's non-zero exit through `tee` | `scripts/workflows/build.sh:60` (`set -euo pipefail`), `:266` |
| The parent parses the routing token out of the child's prose stdout | `scripts/workflows/build.sh:281` |
| The runtime reads the envelope's `subtype` for turn-cap death | `scripts/workflows/activities/run-claude.sh:167` |
| The runtime reads `.result` against the declared completion pattern | `scripts/workflows/activities/run-claude.sh:201-204` |
| The routing vocabulary is declared once for the Python tree | `scripts/workflows/temporal/modules/assistant/routing.py:24-56` |
| Ten workflows declare a PR-URL completion pattern | `grep -rn "COMPLETION_PATTERN=" scripts/` → 11 declarations, 10 PR-URL-shaped, 1 `^VERDICT:` |
| Archived run logs available for replay | `.claude/logs/` at the repo root → 60 JSONL files as of 2026-08-07 |

**`is_error` appears nowhere in the fleet.** Verify this is still true when the phase starts — `grep -rn "is_error" scripts/` — and record the result, because a non-empty result changes E1's framing.

---

## Implementation steps

Experiments are ordered by decision value: E1 and E5 come first because either can move the design, and running them last would mean designing on assumptions they can overturn.

### E1 — The exit-code ↔ `is_error` relationship on the pinned version

*Because:* there is no first-party exit-code table for `claude` (`claude_code_integration_surface.md` §5 records that codes for auth failure, rate-limit exhaustion and `--max-turns` exceeded are undocumented), and the whole "gate on `is_error`" milestone assumes the exit status and `is_error` can disagree. **If they never disagree, that milestone is a no-op and this phase says so with the data.**

- [ ] Force each failure mode in turn — auth failure, rate-limit exhaustion, `--max-turns` exceeded, `--max-budget-usd` exceeded, a usage-policy refusal, `SIGTERM` — using a trivial throwaway prompt, not a real dispatch
- [ ] For each, record the tuple: process exit code, `result.subtype`, `result.is_error`, whether `result.result` is non-empty
- [ ] Record the same tuple for a **successful** run, so the baseline is measured rather than assumed
- [ ] Run each mode inside a worktree under `--dangerously-skip-permissions`, matching the real child-invocation shape — a measurement taken in a different invocation shape measures a different thing
- [ ] Also record, for one run, whether `--output-format json --json-schema <schema>` produces a `structured_output` field that validates against the schema (this is the transport question the `§Runtime Verification` block above could not answer)
- [ ] **Ruling:** does `.is_error` carry information the shell's propagated exit status does not? Name the consequence for Phase 3's composition rule and Phase 4's envelope-reads step

### E5 — How often the current prose grep actually misses

*Because:* the case for replacing the prose channel is currently a robustness argument, not a demonstrated-defect argument, and the pool says a doc claiming the incumbent is broken would be overclaiming. **This experiment is the only thing that can convert that argument, in either direction.**

- [ ] Replay every archived `.claude/logs/*.jsonl` through the exact predicate `build.sh` uses today (`grep -oE '^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$'`), taking the last match
- [ ] Count the runs where the predicate found nothing **but a real verdict is present in the log** — these are the fail-closed misses, and the count is the headline number
- [ ] Separately count runs where the predicate matched a verdict quoted from a *previous* pass rather than the run's own — the anchored, last-match-wins design is meant to prevent this, and the count tests that it does
- [ ] State the sample size alongside the count. A zero over 60 logs is a different claim from a zero over 600, and the doc must not let the reader mistake one for the other
- [ ] **Ruling:** if the miss count is zero, the transport upgrade buys nothing *measurable at this scale*, the roadmap's "lead with the measurement argument" decision becomes load-bearing rather than stylistic, and Phase 3's justification is rewritten accordingly. If it is non-zero, record each miss's cause

### E2 — Does a turn-cap death leave a partial typed record?

*Because:* a run killed at its cap leaves no comment and possibly no final result. A **partial** typed record would be worse than none — absence has a declared meaning under the fail-safe contract, and a truncated record could satisfy a parser while carrying a wrong value.

- [ ] Force a low `--max-turns` on a task that cannot finish inside it, using each candidate transport (file-at-declared-path, and `structured_output` if E1 showed it works)
- [ ] Observe whether any typed artifact exists at the declared path, and if so whether it parses
- [ ] Repeat for `SIGTERM` mid-run and for a run killed while the record is being written
- [ ] **Ruling:** is absence the only absence path, or must Phase 3's contract also defend against a partial record? If the latter, name the mechanism (atomic write, terminal sentinel field, or a length/complete flag) as a Phase 3 requirement

### E3 — The disagreement four-cell table, measured before any policy is built

*Because:* no surveyed system defines precedence between an asserted result and a computed one, since none has an asserting producer. There is no prior art to borrow, so the fleet must pick — and it should pick knowing which cells actually occur.

- [ ] Instrument, **without changing routing behaviour**, the cross-tab of (`is_error` clean / dirty) × (`VERDICT:` MERGE / HOLD) over N ≥ 30 completed runs
- [ ] Record which cells are populated and with what frequency; name the empty cells explicitly as empty rather than omitting them
- [ ] While the instrumentation is in place, also count the disagreements between each PR's `pr_review:` verdict and that PR's open/closed state — this is the input to the **who owns the to-do bit** ruling that Phase 3 must make and that nothing upstream decides
- [ ] **Ruling:** if the off-diagonal cells are empty, Phase 3 adopts the record-both-under-distinct-names shape anyway (it costs nothing and preserves the option) but **builds no composition machinery** for a case that has never occurred — and the doc says that is why

### E6 — The smallest envelope that routes every parent

*Because:* the proposed envelope is roughly five fields derived from one caller, and every field a parent branches on becomes API surface the moment it does. The union must be enumerated, not guessed.

- [ ] Enumerate every branch point in `build.sh`, `build-minor.sh`, `build-phase.sh` and each Python parent under `scripts/workflows/temporal/modules/assistant/`, recording the value each one reads
- [ ] Add the values the planned parents need: Phase 5's convergence comparison, and Autonomous Operation's "dispatch from persisted state" driver
- [ ] Take the union, and for each field state which consumer requires it. **A field with no named consumer does not enter the envelope**
- [ ] Verify the enumeration is complete by grepping for prose parsing across the fleet (`grep -rnE "grep -oE|re\.search|re\.compile" scripts/workflows/`) and checking every hit is either in the list or explicitly out of scope
- [ ] **Ruling:** the concrete field list Phase 3 writes down as its contract, with each field's consumer named beside it

### Close-out

- [ ] Every experiment above has its observed data recorded in this document — numbers and tuples, not summaries
- [ ] Every experiment has one of the three ruling types, and each ruling names a downstream consequence in a specific phase
- [ ] Any experiment that could not be run is recorded here with the reason and what it blocks; it is **not** dropped and it is **not** replaced with a guess
- [ ] Findings that belong to another component — notably whether a definite-progress predicate is derivable from the `stream-json` event stream — are written up here and surfaced for [Fleet Reliability](../fleet-reliability/), which owns the liveness axis. This phase does not build it

---

## Notes and gotchas

- **The instrumentation in E3 must not change routing.** A measurement that alters the thing being measured produces a table describing the instrumented fleet, not the fleet.
- **E1's failure modes cost real API calls.** Use a trivial prompt; the measurement is of the envelope, not of the work.
- **`--max-budget-usd` and rate-limit exhaustion may not be forceable on demand.** If a mode cannot be induced, record it as un-measured rather than inferring the tuple from the others — the whole point of E1 is that the mapping is undocumented, and an inferred row would reintroduce exactly the assumption being tested.
- **Sample-size honesty is a requirement, not a courtesy.** Every count in this doc carries its denominator. The pool's own critic pass caught three wrong counts across two papers; the same discipline applies to measurements taken here.
