---
id: C-ni21k1bd
title: Check what a PR's merge will ACTUALLY close, across all three channels that bind a closing keyword — `closingIssuesReferences` reports the body and title and is blind to commit messages
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: continuous-process-improvement
---

**Two carriers found in one PR, by two different readers, and the second is reported by nothing.** A `review-pr` pass found that PR #94's body still bound `Closes` to #68 in three places — one in bare prose — after a build pass had deleted the `Closes #68` line and verified the deletion by grep. `gh pr view --json closingIssuesReferences` returned `[57,65,68]`: the PROPERTY, where the grep was a string standing in for it. **This correction pass then found a third carrier that `closingIssuesReferences` does not report at all** — commit `ea5c862`'s message body contains the literal `` `Closes #68` `` while explaining that the line was removed, and GitHub closes an issue from a closing keyword in any commit message that lands on the default branch. `origin/main`'s last 12 commits are all single-parent, so this repo lands branch commits individually and the message ships verbatim. **Backticks do not exempt a closing keyword in any of the three channels**, and prose written to explain that an issue is deliberately NOT being closed is the exact shape that closes it. The capability that does not exist is the reading: one command answers two channels, nothing answers the third, and the remedy for the third (rewriting a pushed message) needs an authority a dispatch does not have — so it has to be caught before the commit, not before the merge. Adjacent to but distinct from C-hurryucg: that one asks *is this issue still real?* before a brief is written; this asks *will merging shut the right issues?* before a branch is pushed  **RENUMBERED from C-emxcrzti on 2026-08-16**: `origin/main` had already landed a different C-emxcrzti while this branch was open — the sixth such collision — so this row keeps its content and takes the next free id.

**Source:** PR #94 `build-refine` (correction pass on `review-pr` F1)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
