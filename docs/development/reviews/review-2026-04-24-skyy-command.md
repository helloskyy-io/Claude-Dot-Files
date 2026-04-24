# Workflow Run Review — 2026-04-24

## Runs Analyzed

- **Count:** 20 logs (18 completed + 2 in-flight/incomplete at time of review)
- **Date range:** 2026-04-17 through 2026-04-24
- **Workflow types:** `revision-major` (14), `build-phase` (6)
- **Repo:** `/opt/skyy-net/skyy-command`
- **Prior reviews in `docs/development/reviews/`:** none (this is the first)

### Aggregate metrics (completed runs)

| metric | value |
|---|---|
| avg turns / run | 133.3 |
| avg cost / run | $16.53 |
| avg wall-clock / run | 25.5 min |
| total cost across 18 runs | $297.50 |
| prompt-cache read ratio (per-run) | 0.93 – 0.99 (excellent) |
| max observed context in a single turn | 369,244 tokens (`revision-major-20260419-052204`) |
| failing-tool-result events total | 78 (across 18 runs) |
| sub-agent invocation pattern | consistently: `code-reviewer` + `refactoring-evaluator` + `standards-auditor` (+ optional `Explore` up-front) |

The two incomplete logs (`build-phase-20260424-134603`, `revision-major-20260424-133312`) have no terminal `result` event and appear to be either still in flight or interrupted before completion. They are excluded from the metrics table but included in pattern counts where evidence is clear.

---

## High-Confidence Findings

### HC-1 — Systematic InputValidationErrors from wrong parameter names (12 events, 7 runs)

**Evidence (grepped from `is_error: true` tool-results):**

- `Grep(file_path=...)` instead of `Grep(path=...)` — `build-phase-20260417-001014` (×1), `revision-major-20260417-020926` (×2), `revision-major-20260417-004805` (×1), `build-phase-20260423-000327` (×1). Error text: `InputValidationError: Grep failed due to the following issue: An unexpected parameter 'file_path' was provided`.
- `Read(command=...)` — `build-phase-20260419-013501` (×3), `build-phase-20260417-001014` (×3). The model appears to confuse `Read` with `Bash`.
- `Glob(head_limit=...)` — `revision-major-20260417-190208` (×1). `Glob` has no `head_limit` parameter (that is a `Grep` option).
- `TodoWrite(todos="<string>")` instead of array — `build-phase-20260421-192228` (×1).

**Recommendation:** Add a lint/repair pass in the workflow post-processing, or a single-sentence guard to the system prompt ("Grep takes `path=`, not `file_path`. Read does not take `command`. Glob does not take `head_limit`."). All four are zero-ambiguity mechanical errors.

**Impact:** Every InputValidationError costs a round-trip (1–2k tokens + 1 turn of latency). 12 events × ~1500 tokens ≈ 18k tokens wasted; minor direct cost but noisy signal in logs.

---

### HC-2 — Redundant unbounded reads of hot workflow files (all 20 runs)

**Evidence (max reads of a single file per run, files generally 500–1500+ lines):**

| run | file | reads |
|---|---|---|
| `revision-major-20260419-052204` | `cluster_provision_helper.py` | 17 |
| `revision-major-20260421-212809` | `test_helm_charts.py` | 14 |
| `build-phase-20260423-000327` | `cluster_provision_helper.py` | 13 |
| `build-phase-20260419-040037` | `cluster_provision_helper.py` | 13 |
| `revision-major-20260417-012858` | `bootstrap.sh` | 13 |
| `revision-major-20260423-195002` | `read_recipe.py` | 12 |
| `build-phase-20260417-001014` | `das_vm_helper.py` | 11 |
| `revision-major-20260424-014301` | `test_das_vm_stage_plans.py` | 10 |

Inspection of the read sequence (e.g., `revision-major-20260419-052204` @ events 6, 32, 419, 551) shows 3–4 **full** (unbounded) reads of `cluster_provision_helper.py` interleaved with offset/limit reads. The narrow offset/limit reads are legitimate re-verification after Edits (good). The unbounded re-reads of the same 1000+ line file are the waste.

**Recommendation:** Add to the agent preamble / workflow kickoff: "After the first full read of a file, subsequent reads of the same file must use `offset`+`limit` or Grep to target a specific region — do not re-read the whole file." Also consider surfacing a small in-context "files already read" inventory in the kickoff prompt.

**Impact:** A single 1500-line Python file is ~15k tokens. 3× unbounded re-reads = ~45k tokens of pure redundancy per run. Across 18 runs, this is the single largest preventable token sink.

---

### HC-3 — "File has not been read yet" Edit/Write-before-Read errors (17 events, 10 runs)

**Evidence:** `<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>`

Top offenders: `revision-major-20260419-052204` (×3), `build-phase-20260419-040037` (×3), `revision-major-20260417-190208` (×3), `build-phase-20260419-013501` (×2), `revision-major-20260422-210631` (×2). Also a variant: `<tool_use_error>File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.</tool_use_error>` appears in `revision-major-20260419-052204` and `revision-major-20260417-020926`.

**Recommendation:** Two mechanical fixes:

1. When creating a file via Write, the Read-before-Write check should be automatically satisfied (it is for new files, but Write-then-Edit sometimes trips this when the formatter rewrites the file). The fix is for the agent to Read again after any tool that might rewrite the file (autoformatter, codemod, `git checkout`).
2. The "File has been modified since read" variant suggests a linter/formatter is re-touching the file between Read and Edit — if `ruff format` / `black` runs on save via a hook, either disable it during the revision-major turn or have the agent always Read immediately before Edit.

**Impact:** ~17 events × 1 wasted Edit + 1 forced Read = ~34 wasted turns. At 133 avg turns/run this is ~2% of turn budget.

---

## Medium-Confidence Findings

### MC-1 — Low parallel-tool-call usage (all 20 runs)

**Evidence (multi-tool assistant turns grouped by `message.id`):**

- Median: ~13% of assistant turns issue 2+ tools in parallel
- Range: 3% (`revision-major-20260417-020926`, `revision-major-20260417-012858`) to 24% (`revision-major-20260422-210631`, `build-phase-20260419-040037`)
- 3+ parallel tools: typically 0–10 turns per run

**Recommendation:** The system prompt already covers parallelism ("make all independent tool calls in parallel"). Consider a stronger, more actionable phrasing in the workflow-specific prefix: "When gathering context for review/evaluation, batch independent Reads/Greps into a single turn. Aim for 3+ tool calls per turn during the gather phase." The runs with higher parallelism (24%) were not obviously more error-prone or less thorough than the low-parallelism runs — suggesting this is a pure efficiency win, not a quality risk.

**Needs:** 2–3 more runs with an explicit parallelism nudge to confirm the hypothesis.

**Impact:** Each sequential Read is ~1 turn of latency. Pushing median from 13% to 30% would likely shave 10–20 turns off a typical 133-turn run.

---

### MC-2 — Reading files that exceed the 25k-token cap (4 events, 3 runs)

**Evidence:** `File content (27302 tokens) exceeds maximum allowed tokens (25000).`

- `build-phase-20260419-040037` (×2)
- `build-phase-20260419-013501` (×1)
- `revision-major-20260421-212809` (×1)

These are most likely attempted unbounded Reads of large standards/planning docs (e.g., `architectural_standard.md`, `cluster_provision_workflow.py` as it grew).

**Recommendation:** CLAUDE.md already documents "For known-large files (roadmap.md, standards docs, .jsonl logs), use limit:200 on first read or run wc -l to check size first." This rule is working for some runs but not all. Consider adding a curated "known-large" allowlist to the workflow kickoff that explicitly names the top offenders in this repo (`architectural_standard.md`, `cluster_provision_helper.py`, `cluster_provision_workflow.py`, `genesis_helper.py`, `template_standard.md`) with a recommended initial read budget.

**Needs:** confirmation that the offending Reads were in fact against standards docs (logs show the error but not the target filename cleanly; one run's error lists the file as `.../components/temporal/modules/common/provision/cluster_provision_workflow.py`).

---

### MC-3 — `cat`/`head`/`tail` via Bash instead of Read (48 events across 1,016 Bash calls = ~5%)

**Evidence:** Mostly benign — most of these are composite one-liners (`head -80 config.yaml && echo "---" && ls dir/`) that batch multiple discovery operations into a single turn, which is actually a form of parallelism. A meaningful minority (~10–15 events) are single-file reads that would have been better as `Read` (which honors the cache).

Top single-file offenders:
- `build-phase-20260419-013501` — 14 `cat`/`head`/`tail`-as-Bash calls, the highest count

**Recommendation:** Low priority. The composite-batch pattern is actually useful. Only worth addressing if the rule "prefer `Read` over `Bash cat` for single-file inspection" is easy to enforce in the preamble without suppressing useful batched Bash.

---

## Low-Confidence Findings

### LC-1 — Directory-read EISDIR errors (2 events, 2 runs)

`build-phase-20260424-134603` and `build-phase-20260419-013501` each tried `Read` on a path that was actually a directory (`EISDIR: illegal operation on a directory`). Watch for whether this correlates with a specific code path (e.g., an `__init__.py` confusion) — not enough evidence yet.

### LC-2 — Permission-prompt interruption on destructive Bash

Exactly one event: `revision-major-20260422-221652` hit `Permission to use Bash with command rm -rf components/temporal/modules/common/desired_state_sync && rm -f ...`. The workflow's `bypassPermissions` mode is in effect (per the `system/init` event) so this was a soft block, not a hard stop. Still worth watching — if the model is increasingly issuing multi-file `rm -rf` in a single turn, splitting it into individual `git rm`s would be safer.

### LC-3 — High-cost runs correlate with task complexity, not inefficiency

`revision-major-20260419-052204` hit 228 turns / $34.27 — the outlier. Inspection shows it moved cluster specs from `config.yaml` to desired-state infra templates (a cross-cutting refactor touching many files) and spawned 8 `is_error` events, 3 `File has not been read yet` errors, and 17 reads of one file. The high cost is primarily a function of scope (many files × careful edits) rather than wasted work — but it is the worst concentration of HC-2 and HC-3 symptoms, so it's the single best case study for the two top recommendations.

---

## Patterns Resolved Since Last Review

N/A — this is the first `review-runs` output in `docs/development/reviews/`.

---

## Metrics — detailed breakdown

### Failure-type frequency (across 20 runs, 78 total `is_error` tool-results)

| pattern | count | runs affected |
|---|---|---|
| `Exit code 1/2` from Bash (grep, ls, find, cd, pytest import) | ~30 | 12 |
| `File has not been read yet` (Write/Edit before Read) | 17 | 10 |
| `InputValidationError` (wrong parameter names) | 12 | 7 |
| `File does not exist` / `Directory does not exist` | 7 | 5 |
| `File has been modified since read` (linter race) | 3 | 2 |
| `exceeds maximum allowed tokens` (>25k-token Read) | 4 | 3 |
| `String to replace not found in file` (stale Edit context) | 2 | 2 |
| `EISDIR: illegal operation on a directory` | 2 | 2 |
| Permission prompt (Bash destructive) | 1 | 1 |

### Per-run summary (completed runs only)

| log | turns | $ | err | max-ctx |
|---|---|---|---|---|
| `revision-major-20260424-014301` | 113 | $13.77 | 0 | 231k |
| `revision-major-20260423-195002` | 86 | $9.32 | 1 | 183k |
| `build-phase-20260423-000327` | 165 | $24.71 | 4 | 314k |
| `revision-major-20260422-221652` | 144 | $21.14 | 2 | 274k |
| `revision-major-20260422-210631` | 112 | $9.61 | 3 | 155k |
| `revision-major-20260421-214013` | 101 | $13.81 | 2 | 248k |
| `revision-major-20260421-212809` | 177 | $19.03 | 14 | 243k |
| `build-phase-20260421-192228` | 211 | $26.00 | 7 | 298k |
| `revision-major-20260419-154858` | 83 | $8.38 | 1 | 181k |
| `revision-major-20260419-114939` | 96 | $14.78 | 0 | 256k |
| `revision-major-20260419-052204` | 228 | $34.27 | 8 | 369k |
| `build-phase-20260419-040037` | 136 | $19.62 | 7 | 291k |
| `build-phase-20260419-013501` | 156 | $23.77 | 9 | 310k |
| `revision-major-20260417-190208` | 129 | $9.70 | 5 | 155k |
| `revision-major-20260417-020926` | 86 | $6.41 | 4 | 128k |
| `revision-major-20260417-012858` | 111 | $9.14 | 0 | 158k |
| `revision-major-20260417-004805` | 119 | $8.29 | 2 | 146k |
| `build-phase-20260417-001014` | 146 | $25.77 | 7 | 352k |

### Trends

- Cost per run is stable (median ~$15, mean $16.53). No upward creep week-over-week.
- Turn counts cluster around 100–160 with one outlier at 228.
- `build-phase` runs consistently cost ~50% more than `revision-major` runs (more file creation, more implementation work — expected).
- Error counts are concentrated in a handful of runs (`revision-major-20260421-212809` with 14, `revision-major-20260419-052204` with 8, `build-phase-20260419-013501` with 9). These three runs account for ~40% of all errors.

---

## Summary

The workflow harness is healthy overall: cache-hit ratios are excellent (93–99%), the three-reviewer sub-agent pattern is consistently applied, all 18 completed runs terminated with `result: success`, and no manual user corrections were needed in any run (the apparent "user text" turns are just workflow-injected sub-agent prompts). The **top priority** is HC-2: unbounded re-reads of hot 1,000+ line files (17× in the worst case) is the single largest preventable token sink and the root cause behind HC-3 (Edit-after-stale-Read) cascading. Fixing the read discipline — "after the first full read, use offset/limit or Grep" — would probably also reduce HC-3 frequency and shorten the longest runs (228 turns, $34) by 10–20%. The trend across three weeks of runs is flat, not degrading.
