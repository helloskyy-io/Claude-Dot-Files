---
id: C-j7pagwn3
title: A dependency manifest for the repo
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
---

**Re-verified at placement:** no `requirements.txt`, `pyproject.toml`, `setup.py` or `Pipfile` exists anywhere in the tree, and `temporalio`, `pytest` and `jsonschema` all import on this workstation while being declared nowhere. **Proposal, not defect: nothing is currently broken** — `exit_record.py` is stdlib-only *because its author checked*, which is the point. The failure mode is the next module that does not check: it works here and strands a worktree on the VM. Related to C-xd4mc9cr only in that both are "a check that does not exist"; the mechanism is different (undeclared runtime dependency vs untested function) so they are **not** one entry

**Source:** PR #71

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
