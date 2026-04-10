# Phase 4d: PR Comment Automation (Local Poller)

## Status
Not started (redesigned from GitHub Actions approach)

## Overview
Enable Claude to respond to PR comments automatically. A local systemd timer polls GitHub every 5 minutes for new `@claude` mentions on open PRs. When found, the poller launches the appropriate workflow script locally — using the Max subscription, not API billing.

## Why NOT GitHub Actions
The original design used GitHub Actions to trigger Claude from PR comments. This was abandoned because:
1. **Billing mismatch** — Actions runners require Claude API tokens (per-token billing), not the $100/mo Max subscription
2. **Security exposure** — Would require opening the workstation to external triggers or running on GitHub's cloud, neither of which is acceptable for a hardened dev workstation on Tailscale
3. **Unnecessary complexity** — Spinning up VMs to install Claude Code for each comment is heavyweight for what's essentially "read a comment, run a script"

## Goal
PR comments become an iteration mechanism using local infrastructure:
- Comment `@claude fix the null check` → poller detects it → runs `revision.sh --pr N` locally
- Comment `@claude revision-major: restructure the auth flow` → runs `revision-major.sh --pr N` locally  
- Comment `@claude help` → posts a comment listing available commands
- All runs use Max subscription ($0 additional cost)
- Workstation stays closed to external traffic

## Architecture

```
┌────────────────────────────────────────┐
│  systemd timer (every 5 min)           │
│  Runs: scripts/services/pr-watcher.sh  │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  pr-watcher.sh (bash + gh CLI)         │
│  - Lists open PRs with recent comments │
│  - Filters for @claude mentions        │
│  - Skips already-processed (reacted)   │
│  - Parses route and description        │
│  - No Claude invoked, no tokens burned │
│  - Fast: ~2 seconds when nothing found │
└────────────────────────────────────────┘
         │ found work?
         ▼
┌────────────────────────────────────────┐
│  Launch appropriate workflow            │
│  - @claude fix X → revision.sh --pr N  │
│  - @claude major: Y → revision-major   │
│  - @claude help → gh pr comment        │
│  - React 👀 on comment (processing)    │
│  - React ✅ on comment (done)          │
│  - React ❌ on comment (failed)        │
└────────────────────────────────────────┘
```

## Requirements

### Functional
- Systemd timer runs `pr-watcher.sh` every 5 minutes
- Poller uses `gh` CLI to list open PRs and their comments
- Filters for comments containing `@claude` that haven't been reacted to yet
- Routes to correct workflow based on comment content:
  - Default: `revision.sh "task description" --pr <number>`
  - Explicit: `@claude revision-major: description` → `revision-major.sh "description" --pr <number>`
  - Help: `@claude help` → post a help comment listing commands
- Reacts to comments to track processing state:
  - 👀 (eyes) — processing started
  - ✅ (check) — completed successfully  
  - ❌ (cross) — failed
- Posts error comment on PR if workflow fails
- JSONL logs captured per normal workflow standard

### Non-functional
- Polling must be lightweight (no Claude invocation for checking)
- Must not process the same comment twice (reaction-based deduplication)
- Must handle multiple pending comments in order (oldest first)
- Must work on any repo where `gh` is authed (not just this one)
- Must survive machine reboots (systemd ensures this)
- Must not block if a workflow is already running for the same PR (concurrency)

### Constraints
- `gh` CLI must be installed and authenticated
- Workflows (revision.sh, revision-major.sh) must exist in the repo
- Only runs on machines with the systemd timer installed
- Only monitors repos the `gh` CLI has access to

## Tasks

### Poller Script
- [ ] **Create `scripts/services/pr-watcher.sh`** — The polling script. Uses `gh api` to list comments on open PRs, filters for `@claude` mentions without reaction markers, parses route and description, launches the correct workflow.
- [ ] **Reaction-based deduplication** — React with 👀 before starting, ✅ or ❌ when done. Skip comments that already have any of these reactions.
- [ ] **Comment routing** — Parse `@claude help`, `@claude revision-major: <desc>`, and default `@claude <desc>`.
- [ ] **Error handling** — If the workflow fails, react with ❌ and post a comment with the error. Don't crash the poller.
- [ ] **Concurrency guard** — If a workflow is already running for a PR, skip that comment and process it next cycle.
- [ ] **Multi-repo support** — Accept a configurable list of repos to monitor, or default to the current repo.

### Systemd Integration
- [ ] **Create `scripts/services/pr-watcher.service`** — Systemd service unit file
- [ ] **Create `scripts/services/pr-watcher.timer`** — Systemd timer unit (every 5 minutes)
- [ ] **Install instructions** — How to symlink units to `~/.config/systemd/user/`, enable, and start
- [ ] **Add to install.sh** — Optional systemd setup during deployment (with flag to opt in)

### Help Command
- [ ] **Implement `@claude help` response** — Post a PR comment listing available commands, syntax, and examples using `gh pr comment`

## Dependencies
- `gh` CLI installed and authenticated (already done on workstation and laptop)
- Workflow scripts exist in the repo (already built)
- Systemd user service support (standard on Linux Mint/Ubuntu)

## Success Criteria
- [ ] Polling script runs every 5 minutes via systemd timer
- [ ] `@claude fix X` on a PR triggers revision.sh and pushes a fix
- [ ] `@claude revision-major: Y` triggers revision-major.sh
- [ ] `@claude help` posts a helpful comment
- [ ] Same comment is never processed twice (reaction deduplication)
- [ ] Failed runs post error comments and react with ❌
- [ ] Zero Claude tokens burned on polling (only on actual work)
- [ ] Survives machine reboot

## Risks & Mitigations
- **Risk:** Workstation is off or asleep when comment is posted
  - **Mitigation:** Poller picks it up next time the machine is on. Comments don't expire. Acceptable latency tradeoff for zero-cost operation.
- **Risk:** Multiple workflows triggered simultaneously for the same PR
  - **Mitigation:** Concurrency guard — skip if a workflow is already running for that PR.
- **Risk:** Comment parsing edge cases (markdown, code blocks containing @claude)
  - **Mitigation:** Only match `@claude` at the start of a comment or after a newline. Ignore code blocks.
- **Risk:** `gh` CLI auth expires
  - **Mitigation:** `gh auth status` check at poller startup. Log warning if not authed.

## Standards
- Follow all applicable standards in docs/standards/
- Poller script follows the same bash conventions as workflow scripts (set -euo pipefail, env checks, etc.) but does NOT use the workflow-scripts standard (it's a service, not a workflow)
- JSONL logging for the workflows it triggers (already built into the workflow scripts)

## Notes
- This replaces the original GitHub Actions approach (PR #10, closed)
- The poller is "old school" bash + systemd — intentionally NOT AI-powered for the polling logic
- Claude is only invoked when real work exists, using Max subscription
- This could later be extended to monitor for other GitHub events (new issues, review requests, etc.)
- Tailscale-only network means no external exposure — the poller reaches OUT to GitHub, nothing reaches IN
