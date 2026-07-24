# Workflow Review — desired-state-sturdy-wheat-pelican — 2026-07-24

**Source repo:** `/opt/skyy-net/desired-state-sturdy-wheat-pelican`
**Source machine:** `skyy-net`
**Analysis date:** 2026-07-24
**Logs analyzed:** 1 log, 2026-07-10 (single `revision-major` run)

> **Important caveat on repo attribution:** the single log in this repo's `.claude/logs/` records a run whose *task target was `mdc-ansible-collections`*, not this repo. The dispatch harness placed the worktree in `desired-state-sturdy-wheat-pelican` by mistake (see MC-1); the engineer detected the mismatch, created a correct worktree in the target repo, and did all work there. The log lives here only because the dispatch started here. Findings below therefore describe workflow/harness behavior, not desired-state repo content.

---

## Runs Analyzed

| Log | Workflow | Date | Outcome |
|---|---|---|---|
| `revision-major-20260710-170724.jsonl` | revision-major | 2026-07-10 | Success — PR #17 on `helloskyy-io/mdc-ansible-collections` (etcd-freshness guard in `k3s_server_init`) |

Sample size: **1 run.** Per the confidence scoring system, no finding in this report can exceed Medium confidence (High requires a pattern across 3+ runs). This is also the **first review of this repo** — no prior `review-desired-state-sturdy-wheat-pelican-*.md` exists.

---

## High-Confidence Findings

None possible at N=1. See Medium below for the strongest single observations.

---

## Medium-Confidence Findings

### MC-1 — Dispatch harness placed the worktree in the wrong repo (strong single observation, severe class)

**Evidence:** Init event: `cwd = /opt/skyy-net/desired-state-sturdy-wheat-pelican/.claude/worktrees/revision-major-20260710-170724`, while the task prompt's every path targets `mdc-ansible-collections`. Engineer narration (turns 2–5): *"I'm in a worktree for `desired-state-sturdy-wheat-pelican`, but the task targets `mdc-ansible-collections`… This is a harness/dispatch misconfiguration — the worktree was created in the wrong repo."* Final report flag #1 confirms recovery: engineer created `/opt/skyy-net/mdc-ansible-collections/.claude/worktrees/revision-major-etcd-freshness-guard` and did all work there; nothing was written to the desired-state worktree.

**Impact:**
- ~4–5 turns of investigation + manual worktree recovery (engineer time recovered cleanly, but only because it noticed).
- **Log/telemetry mis-attribution:** the run's log landed in this repo's `.claude/logs/`, which is why *this very review* was dispatched against desired-state to analyze mdc-ansible-collections work. CPI targeting is skewed until the mismatch class is fixed.
- Latent asymmetric risk: a less careful run could have edited the wrong repo. The engineer's detect-and-recover behavior is not a guarantee.

**Recommendation (claude-dot-files-level — surface to the architecture session, do not edit directly):** workflow dispatch scripts should validate that the task's target repo matches the repo the worktree is created in — either a pre-flight check ("task paths reference repo X, cwd repo is Y → abort with message") or an explicit `--repo <name>` dispatch flag. Note the adjacency to the deferred **"No `--base-branch` flag"** entry (cpi-decisions.md, 2026-05-09 ad-hoc): both are dispatch-parameterization gaps where the operator has no way to declare the target and the harness infers it from the invocation directory. Two members of the same gap family may together justify a single dispatch-targeting fix.

**Root-cause note:** cannot be determined from the log alone whether the operator dispatched from the wrong directory or the script mis-resolved the repo. The diagnostic is operator-side: check the dispatch invocation for this run.

### MC-2 — Task brief contained a fabricated standards citation (strong single observation)

**Evidence:** The stage-5a standards-auditor dispatch prompt (and the change itself, per the task brief) cited a *"Lifecycle Management Standard §state-aware convergence"* section that does not exist. standards-auditor flagged it (its only Warning); the engineer independently verified before correcting — *"I must not replace one wrong citation with another"* — and re-anchored the in-code citation to Desired State Standard §4 + Container Clustering Standard §5.1, both verified against source. Final report flag #2.

**Impact:** a wrong citation baked into an operator-authored task brief propagates into code comments unless a reviewer catches it. Here the multi-agent review worked exactly as designed — this is a fresh confirming instance of the *"standards-auditor catches what the other lenses miss"* pattern (shipped as documentation at N=3, 2026-05-09; this would be N=4).

**Recommendation (project-side):** task-brief authoring discipline — verify standards citations against source before embedding them in dispatch prompts. Relates to the 2026-05-27 CPI disposition of "engineer task brief template" (Item 2, redirected project-side): if a task-brief template lands in mdc-master-planning, "citations verified against source" belongs on its checklist.

**Needs:** a second occurrence of a task-supplied factual error before any claude-dot-files-level action.

---

## Low-Confidence Findings

### LC-1 — One Edit-before-Read event (Pattern B residual)

Line 199: `Edit` on the worktree's `TESTING.md` rejected with *"File has not been read yet."* Single event, immediately self-corrected. This is the residual tail of CPI **Pattern B** (Read-before-Edit hardening, shipped 2026-05-03), which last cycle had already dropped to ~12% of its prior rate in skyy-command. 1 event / 1 run here is consistent with that residual rate, not a regression. **Watch-for:** rate climbing back above ~2 events/run in future cycles.

### LC-2 — Review subagents probe paths by guessing (5 errors across the 4 review agents)

Five of the run's seven tool errors came from review-stage subagents, not the main thread: `Read` on a directory (×2, lines 321/408 — one was the worktree root itself), `Grep` against a nonexistent path (line 510), and `Read` of `TESTING.md`/`README.md` at the role directory when the file lives at repo root (lines 667/712). All self-recovered within a turn. Pattern: reviewer agents take paths from their prompt literally or guess file locations instead of running `Glob` first. Cost is a handful of wasted tool calls per run — real but small. **Watch-for:** if future cycles show >5 subagent path-probe errors per multi-agent run, consider adding a one-line "Glob before first Read; prompt paths may be directories" note to the review-agent dispatch template — but that is a claude-dot-files change, so it would go through the architecture session.

### LC-3 — Benign multi-probe Bash exit-1

Line 82: a chained discovery command (`ls` + `wc` + molecule-scenario sweep + lint-tool probe) exited 1 because one grep in the chain matched nothing; all useful output was produced. Not a defect — noted only for error-count bookkeeping (headline "7 errors" overstates: 1 was this benign exit code).

---

## Patterns Resolved Since Last Review

No prior review of this repo exists — this is the first `review-desired-state-sturdy-wheat-pelican-*.md`. No same-repo resolution comparison is possible. Cross-repo shipped patterns validated by this run are listed under Recurrences below as validation signals.

---

## Recurrences from CPI Decisions Log

Checked every DEFERRED watch-criteria in `/opt/skyy-net/claude-dot-files/docs/development/cpi-decisions.md` against this run:

- **Sequential review-agent dispatch (DEFERRED 2026-05-09 review-runs cycle)** — **counter-evidence this cycle.** This run dispatched code-reviewer + refactoring-evaluator + standards-auditor as three `Agent` calls in a **single assistant message**, with quality-control run sequentially after — exactly the documented pattern. 1/1 compliant (vs 0% parallel in the worst prior runs). N=1, so not yet grounds to close the deferral, but the trend is in the right direction; the diagnostic-diff trigger ("continued sequential dispatch") did **not** fire in this window.
- **Pattern B — Read-before-Edit (SHIPPED 2026-05-03)** — 1 residual event (LC-1). Holding at low residual rate; no watch-criteria breach.
- **Pattern A — 25K-token Read overflow (DEFERRED, recurring prior cycles)** — **zero events this run.** No recurrence in this window.
- **Pattern C — `find | xargs` whitespace (DEFERRED, ship-on-second-occurrence)** — zero occurrences. Continue to defer.
- **L1 — ScheduleWakeup in non-loop workflows (DEFERRED at N=3 windows, 2026-05-09)** — **zero ScheduleWakeup calls this run.** Prior watch-criteria said a zero-event next cycle supports downgrading to REJECTED (intermittent). This window contributes a zero, but at 1 run it's weak evidence on its own — combine with the same-day skyy-command review before downgrading.
- **(a) .gitignore-collision check (SHIPPED 2026-05-12)** — **followed.** Engineer narration explicitly ran the check before checkpoint commit ("New files are untracked (not gitignore-hidden)"). Shipped rule validated under real load.
- **(d)/WI-1 — canonical-runner cross-check of test/lint claims (SHIPPED for sprint-review 2026-05-12)** — **discipline generalized unprompted.** Engineer hit a direct-`ansible-lint` vs master-runner discrepancy and *investigated to root cause before reporting* (runner lints the role tree but not the `molecule/` subtree), rather than carrying an unreconciled claim into the PR. The shipped rule targets sprint-review.sh; this run shows the same discipline in revision-major without an explicit instruction — a positive calibration signal.
- **"No `--base-branch` flag" (DEFERRED 2026-05-09 ad-hoc)** — MC-1 is an adjacent member of the same dispatch-parameterization gap family (harness infers target from invocation context with no operator-declared target). Not a strict recurrence of the base-branch shape, but worth evaluating together at the architecture session.

---

## Successes Worth Preserving

- **Detect-and-recover on the repo mismatch:** the engineer noticed the cwd/task contradiction on turn 2, verified the correct target before acting, created a proper worktree in the right repo, and surfaced the misconfiguration in the PR body + reflection instead of silently proceeding or silently working around it. Model behavior for unexpected-state handling.
- **Lint-baseline discipline:** before judging a `command-instead-of-module` violation, the engineer established that `main` was already red for the pre-existing instance — correctly classifying it as prior lint-debt and not fixing out-of-scope code.
- **Citation verification before correction:** the auditor's claim about the nonexistent standard was itself verified against source before the fix was applied.
- **Finding disposition discipline:** every stage-5 finding reached an explicit disposition (all 3 Warnings + Info items fixed; the `k3s_server_join` ambiguity explicitly deferred as out-of-scope with a pointer) — no silent dismissals.
- **Clean main-thread execution:** only 2 main-thread tool errors in 62 turns, one of them a benign exit code.

---

## Metrics

| Metric | Value |
|---|---|
| Runs | 1 (revision-major) |
| Outcome | Success — PR #17, 8 files, +317/−1 |
| Turns | 62 |
| Wall time | 21.8 min (1,305 s) |
| Cost | $8.57 |
| Output tokens | 63,061 |
| Cache reads / creation | 5.77 M / 138 k |
| Tool calls | 166 (Read 73, Grep 27, Bash 26, Glob 18, Edit 11, Write 7, Agent 4) |
| Tool errors | 7 total → 2 main-thread (1 benign), 5 subagent path-probes |
| Parallel dispatch | 3 narrow-lens reviewers in 1 message + sequential QC (compliant) |
| ScheduleWakeup misuse | 0 |
| Trend | N/A — first review of this repo, single run |

---

## Summary

A healthy run: revision-major delivered PR #17 in ~22 minutes at $8.57 with near-zero main-thread friction, compliant parallel review dispatch, and several previously-shipped CPI disciplines (gitignore-collision check, canonical-runner cross-check, finding disposition) visibly holding. The top-priority item is **MC-1**: the dispatch harness created the worktree in the wrong repo entirely — recovered gracefully this time, but it mis-attributes logs (this review's own targeting is a downstream symptom) and carries wrong-repo-edit risk; it belongs at the architecture session alongside the deferred `--base-branch` dispatch-parameterization entry. Trend cannot be assessed at N=1; the mis-filed log means future desired-state review cycles should confirm which repo their logs actually belong to before analysis.
