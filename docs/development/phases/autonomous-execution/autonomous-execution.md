# Phase: Autonomous Execution

**Status:** ✅ COMPLETE — the fleet exists and is in daily use. Its *shape* is now being reworked under [Workflow Decomposition](../../roadmap.md).
**Roadmap entry:** [`../roadmap.md`](../../roadmap.md)
**Depends on:** [`planning-and-agents.md`](../planning-and-agents/planning-and-agents.md) — a workflow is an orchestration of agents; the agents came first

## Goal

Build the plan → execute → PR pipeline: scripts that run Claude headless in an isolated worktree, review their own output, and deliver a pull request without a human in the loop.

## Completion criteria

- [x] A task can be dispatched and walked away from
- [x] Work is isolated — a bad run damages nothing outside its worktree
- [x] Output arrives as a **PR**, never a push to `main`
- [x] Every run leaves a machine-readable record of what it did
- [x] Verified on real tasks in real repos, not fixtures

## Work

### Foundation validation

- [x] **Headless mode** — `claude -p` works, including slash commands
- [x] **`gh` CLI installed and authed** on workstation and laptop
- [x] **Worktree mode** — `-w` auto-prefixes the branch with `worktree-`
- [x] **Full pipeline in one command** — headless → worktree → edit → commit → push → PR
- [x] **Dual permission model** — interactive uses allow/deny lists; autonomous uses `--dangerously-skip-permissions` behind worktree isolation and the hook
- [x] **`/cleanup-merged-worktrees`** — scans worktrees, checks PR state, removes the merged ones

### Standards, written before the fleet grew

- [x] `agents.md`, `hook-scripts.md`, `skills.md`, `slash-commands.md`
- [x] All four referenced from `CLAUDE.md` so a session finds them before starting

### The workflows

- [x] **`revision.sh`** — 5 stages, single session, light corrections
- [x] **`revision-major.sh`** — 9 stages with a review panel *(since split into `revision.sh` parent + children)*
- [x] **`build-phase.sh`** — plan-driven: takes a **document path**, not free text, and extracts scope and success criteria from it
- [x] **`plan-new.sh`** — 14 stages, greenfield project definition
- [x] **`plan-revision.sh`** — 7 stages, revising existing planning docs
- [x] **`init-project.sh`** — pure bash scaffolding, zero AI tokens

### Shared infrastructure

- [x] **`run_claude` extracted** to a shared lib, sourced by every workflow
- [x] **Stream formatter** for live `--verbose` output
- [x] **Shared prompt blocks** — stage text and rules factored into variables, removing ~80 lines of duplication per script

### PR comment automation

- [x] **`gh-monitor.sh`** — bash poller routing `@claude <route>:` comments to workflows
- [x] **Reaction-based deduplication** — 👀 processing, 🎉 done, 👎 failed, 😕 needs clarification
- [x] **systemd** oneshot + 5-minute timer, `Persistent=true`
- [x] **`install.sh --with-services`** — opt-in deployment

### Skills library (built from experience, not planned)

- [x] Testing methodology · testing scaffolding
- [x] Documentation structure — the four-bucket convention
- [x] Planning methodology · architecture decisions · project definition
- [x] Refactoring methodology · standards enforcement

## Decisions

**Bash, not a framework — and the reasoning has held.** The original argument was that bash is portable forward, debuggable, and has zero learning curve. A second argument arrived later and is stronger: **composition never needed a framework.** A parent needs a child's exit code plus one stable identifier on its final line. See [`claude_code_orchestration.md`](../../../guide/claude_code_orchestration.md).

**Plan-driven input for `build-phase.sh`.** It takes a document path rather than a prose task, so the plan is the contract and the run can be graded against something written down beforehand.

**PR, never a direct push.** Every workflow ends at a pull request. This is what makes `--dangerously-skip-permissions` acceptable: the blast radius is a branch, and a human still gates the merge.

**GitHub Actions abandoned for a local poller.** The original approach (PR #10, closed) ran the automation in Actions. Rejected: it needed API credentials in CI, could not reach the machine that holds the repo, and put the trigger somewhere the operator could not observe. A local `gh` poller keeps execution on the machine with the code — the same **repo-locality** constraint that later drives Temporal worker placement.

## What this phase discovered that changed everything after it

**Subagents do not auto-load skills.** Found when trimmed agents behaved worse than fat ones: the methodology had been extracted to skills, and the agents were not loading them. Fixed by adding `skills:` frontmatter to every agent. Without this, the entire lean-agent architecture silently does not work.

**Agents should be lean roles, not methodology dumps.** `planner` went 212 → 45 lines and `architect` 212 → 50, with the depth moved into skills. A fat agent re-states methodology that then drifts from the skill; a lean one is a role plus a pointer. This is the pattern the whole skills library exists to serve.

**A run's own log is evidence.** Analyzing one JSONL log found **~35% redundant reads** — the same files re-read across stages. That single observation is the seed of the entire CPI loop: the system's own logs are a measurable, honest record, and reading them systematically became `review-runs.sh`.

## Superseded

The phase originally carried an orchestration-options survey with graduation triggers — *move to the Agent SDK if error handling gets painful, to Managed Agents for multi-project state, wait for Agent Teams for parallelism*. **That question is answered and the triggers were the wrong ones.** The gap that mattered was never error handling or parallelism; it was **durability and resumability**, which none of those options supply. See [Temporal Integration](../../roadmap.md) and [`../skyy-net-seed-handoff.md`](../../skyy-net-seed-handoff.md).

Its April-era warnings *did* hold and are now enforced structurally rather than remembered: explicit exit criteria over loop counts, sequential over nested, precision in the initial prompt over iteration. All three are in [`../../standards/workflow-scripts.md`](../../../standards/workflow-scripts.md).

## Where this landed

- [`../../guide/workflows.md`](../../../guide/workflows.md) — the architecture
- [`../../standards/workflow-scripts.md`](../../../standards/workflow-scripts.md) — the standard
- `scripts/workflows/` — the fleet
