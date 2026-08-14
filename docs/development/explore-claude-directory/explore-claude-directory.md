# Phase: Explore ~/.claude

**Status:** ✅ COMPLETE
**Roadmap entry:** [`../sprint.md`](../sprint.md#phase-explore-claude--complete)

## Goal

Understand what Claude Code actually stores in `~/.claude/` before deciding what to sync. Every later phase depends on this answer — a sync strategy built on a wrong model of the directory would have been expensive to unwind.

## Completion criteria

- [x] Every directory under `~/.claude/` identified, with what writes to it
- [x] Each one classified: **portable** (belongs in git) or **machine-local** (must not be)
- [x] The classification justified per item, not assumed

## What was found

A fresh install creates the tree eagerly — every folder exists, most are empty. Population is lazy, so an early look shows structure without content.

| Path | Written by | Verdict |
|---|---|---|
| `settings.json` | operator | **portable** |
| `CLAUDE.md` | operator | **portable** |
| `agents/` `commands/` `hooks/` `rules/` `skills/` | operator | **portable** — this is the authored surface |
| `.credentials.json` | `claude login` | machine-local — secret |
| `projects/` | Claude Code | machine-local — **path-keyed** |
| `history.jsonl` `sessions/` `shell-snapshots/` | Claude Code | machine-local — session state |
| `cache/` `file-history/` `telemetry/` `backups/` | Claude Code | machine-local — derived |
| `ide/` `plugins/` `plans/` `session-env/` | Claude Code / IDE | machine-local |

## The decision this phase produced

**`projects/` is path-keyed, and that single fact set the sync strategy.**

Claude Code stores per-project state under a directory named for the project's absolute path — `-home-puma-Repos-foo`. A workstation at `~/Repos/foo` and a VM at `/opt/skyy-net/foo` are, to that scheme, different projects. Syncing the directory would not merge their histories; it would carry a growing set of entries that are inert on every machine but the one that made them.

So the strategy is **targeted symlinks over the authored subset**, not whole-directory sync — the finding that made stow-style tree-mirroring wrong for this. Everything Claude Code writes for itself stays where it lands.

**Corollary, learned later and worth recording here:** the directory also holds `.credentials.json`. Whole-directory sync would have put credentials in git. The path-keying argument arrived first, but this one is the more expensive mistake avoided.

## Where this landed

- [`../../guide/deployment.md`](../../guide/deployment.md) — the sync model and the full synced/not-synced split
- `install.sh` — the seven symlinks that implement it
