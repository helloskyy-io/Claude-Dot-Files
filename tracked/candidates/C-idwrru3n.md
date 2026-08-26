---
id: C-idwrru3n
title: Per-file granularity in `install.sh`'s symlink targets, so a `tests/` dir beside a hook does not land in the live `~/.claude/hooks/
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

Nothing is broken — PR #58 placed the tests successfully elsewhere and documented the divergence. Changes the documented 7-target strategy on every machine, so it is an architecture decision. Constrained by C-7ymfdw28; rule them together

**Source:** issue #63

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
