# claude-dot-files Repo Governance

The `claude-dot-files` repo is the global tooling layer for Claude Code workflows — workflow scripts, agents, skills, rules, and configuration that every Claude session and every project depends on. It is architecture, not a project artifact. All changes flow through a dedicated architecture session under the user's direct control.

## When working in any project repo

If you identify an improvement to claude-dot-files — a workflow prompt change, a new rule, a skill addition, an agent tweak, or any other configuration update — DO NOT edit the claude-dot-files repo directly, even if you can see it on the filesystem (commonly at `~/Repos/claude-dot-files/` on workstations or `/opt/skyy-net/claude-dot-files/` on VMs).

Instead, surface the suggestion to the user with explicit framing:

> "This is a claude-dot-files-level change worth bringing to the architecture session: <description and reasoning>"

The user maintains a dedicated claude-dot-files session where changes are evaluated with architectural context — cross-project consistency, alignment with existing patterns, evidence thresholds, and the engineering-quality discipline that governs claude-dot-files changes.

## Why this rule exists

- **Project-level PMs see one project's needs.** claude-dot-files changes affect every project. A fix that solves one project's problem may not generalize, may conflict with another project's pattern, or may violate architectural discipline (e.g., shipping a single-occurrence finding without sufficient evidence).
- **The architecture session has context project sessions lack.** It tracks `docs/development/cpi-decisions.md`, knows what was recently shipped or deferred, understands cross-cutting workflow patterns, and applies the engineering-quality discipline consistently across cycles.
- **Direct edits bypass human-in-the-loop control.** The user has explicitly chosen architectural review as the gate for global tooling changes. Every claude-dot-files change flows through that review, including small ones.

## What to do instead

1. **In Post-Run Reflection comments** (every PR-producing workflow creates one), use the existing "Tooling-level suggestions (claude-dot-files)" section. That is the canonical surface — the user reads reflections and brings actionable items to the architecture session.
2. **In interactive sessions** (PM working alongside the user), raise it directly: "I notice a pattern that would benefit from a claude-dot-files change. Flagging for the architecture session — not editing directly."
3. **Continue with the project work.** The suggested claude-dot-files change is the user's to act on at their discretion. Don't block on it.

## What this does NOT prevent

- **VM clones existing.** The VM still has a `claude-dot-files` clone for syncing config via `install.sh`. The rule is about EDITING, not presence.
- **Reading claude-dot-files content.** You may freely Read workflow scripts, rules, skills, etc. to understand how they work. The restriction is on writes.
- **Discussion of claude-dot-files in PR bodies / comments.** Surfacing suggestions IS the goal; that's not bypassing the rule, it's following it.

## Exception

If the user EXPLICITLY directs you to edit claude-dot-files in the current session ("update the workflow prompt to X", "add a rule about Y"), that overrides this rule. The rule prevents UNINSTRUCTED initiative; it doesn't override explicit user direction. When in doubt, ask: "Should I make this change in claude-dot-files now, or surface it for the architecture session?"

## Critical Rules

- **Never edit `~/Repos/claude-dot-files/` or `/opt/skyy-net/claude-dot-files/` from a project session without explicit user direction.**
- **Surface improvements through Post-Run Reflection or interactive flagging, never through direct edits.**
- **The rule applies to all forms of editing: Edit, Write, Bash with redirect (`>`, `>>`), `git commit` to claude-dot-files, etc.**
- **When uncertain, ask the user before touching claude-dot-files.**
