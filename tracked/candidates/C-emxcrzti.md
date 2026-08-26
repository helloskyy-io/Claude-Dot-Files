---
id: C-emxcrzti
title: Make the research family say whether a pool it was pointed at is meant to EXIST, so a typo'd pool path costs a message instead of a full dispatch that researches into a new directory
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**`run_research.py` and `run_research_minor.py` accept a pool path that does not exist and proceed, and nothing downstream can tell a new pool from a misspelled one.** Measured on this branch: `run_research.py docs/development/no-such-pool-yet --dry-run` exits 0 and prints `Due papers: 0` — the same output a correct empty pool produces. **The consequence is a whole dispatch spent wrong**: the run cuts a worktree, researches, and opens a PR that adds an entire pool one directory letter away from the real one, and the operator finds out at review rather than at the second the command was typed. That is the orphaned-worktree class (#48/#49) reached through an argument `preflight` did not previously see. **Why it is NOT fixed in this PR, and this is the substantive half:** this PR brings both runners inside the containment mechanism, and containment is a different question from existence. Nothing in the research family `mkdir`s its pool — `plan-candidates` scaffolds them — so requiring existence today would refuse the one legitimate case the flag has, a genuinely new pool. The behaviour is therefore preserved exactly, with `must_exist=False` on the declaration and the reason stated at the call site. **Deciding which case the flag means is a change to the research family's CLI contract, whose tests are not in this diff.** **Done-state today: yes, and it is a choice not a build** — either require existence and give `plan-candidates` the sole right to create a pool, or keep the permission and make it explicit (`--new-pool`), so that the silent third state stops existing. **NOT a defect in what this PR built:** every documented behaviour is preserved and the escape it does close is proven by execution on both runners. **Not an expansion of C-oapy6vg8** (deriving the hand-maintained control sets): that is about test-side bookkeeping, this is an operator-facing CLI contract. **Not an expansion of C-0e9oeexi**, which resumes a component whose planning step failed — that is about recovering from a run that went wrong, this is about refusing to start one. *(Id taken by re-reading this file at HEAD immediately after resolving the `origin/main` merge, which itself carried a duplicate C-2asq6d9x minted on the other branch; highest was C-hurryucg.)*

**Source:** PR #93 `plan-verify` (build-draft, 2026-08-16)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
