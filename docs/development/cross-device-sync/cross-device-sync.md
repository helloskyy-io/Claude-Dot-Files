# Phase: Cross-Device Sync

**Status:** ✅ COMPLETE
**Roadmap entry:** [`../sprint.md`](../sprint.md#sprint-cross-device-sync--complete)
**Depends on:** [`explore-claude-directory.md`](../explore-claude-directory/explore-claude-directory.md) — the portable/machine-local split is this phase's input

## Goal

Get the repo deploying to every machine, so that everything built in later phases propagates automatically rather than being hand-copied.

This is infrastructure for the phases after it. Its real success criterion is not "the symlinks exist" but **"a new agent written on the laptop is live on the VM after a `git pull`, with no further steps."**

## Completion criteria

- [x] One command installs on a clean machine
- [x] The installer is **idempotent** — safe to re-run, which is what makes automation possible
- [x] Verified on all three machine classes: laptop, workstation, VM
- [x] Non-interactive path exists for automation
- [x] Nothing machine-local is ever touched

## Work

- [x] **Finalize repo structure** — `config/` holds the synced items: `settings.json`, `CLAUDE.md`, `agents/`, `commands/`, `hooks/`, `rules/`, `skills/`
- [x] **Write `install.sh`** — checks prerequisites, backs up existing targets, creates the symlinks, verifies every one. `--non-interactive` / `-n` skips prompts, fails fast on missing prerequisites, skips the auth check entirely
- [x] **Create starter `settings.json`** — minimal, expanded in later phases
- [x] **Create global `CLAUDE.md`** — applies to all projects
- [x] **Test on laptop** — clean run, all 7 symlinks verified
- [x] **Deploy to workstation** — clone, install, verify
- [x] **Ansible integration** — `install.sh --non-interactive` on desktops and laptops; Ansible clones the repo and installs prerequisites first
- [x] **Deploy to VMs** — verified at `/opt/skyy-net/claude-dot-files`

## Decisions

**Targeted symlinks, not tree-mirroring.** Seven explicit links rather than managing `~/.claude/` wholesale. GNU Stow and similar mirror a tree, which here would mean adopting `projects/`, `cache/` and `.credentials.json` — the exact set the previous phase found must stay local. Selective linking within a directory we do not own is the correct shape, and it is why this is a bash script rather than a stow invocation.

**Idempotency is the feature, not a nicety.** Ansible re-runs `install.sh` on every playbook execution. That is only safe because a correct symlink is a no-op and a conflicting file is backed up before replacement. Without that property the installer could not be automated at all, and the whole "propagates automatically" goal fails.

**Auth is deliberately not automated.** `claude login` needs a browser OAuth flow, so it stays a manual per-machine step. `--non-interactive` skips the auth *check* rather than attempting the login — a non-interactive installer that blocks on a browser is worse than one that installs and tells you what remains.

## Notes

**Workstations and laptops** run the installer via Ansible on every playbook run.

**VMs** are installed manually with the interactive path. Auth is per-machine.

**The `.claude/` gitignore step is easy to miss and bites later.** Worktrees created by autonomous workflows live under `.claude/` inside whatever repo they run in; without a global gitignore entry they surface as untracked changes in unrelated repos. It belongs in the install instructions rather than in troubleshooting, because the symptom appears far from the cause.

## Where this landed

- [`../../guide/deployment.md`](../../guide/deployment.md) — the operator-facing instructions
- `install.sh` — the implementation
