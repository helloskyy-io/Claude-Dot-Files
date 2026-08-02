# Workflows Guide

## Quick Reference — All Scripts

### Helper Scripts (no AI, pure bash)

| Script | Purpose | Location |
|---|---|---|
| `init-project.sh` | Initialize a new project (git, GitHub, scaffolding) | `scripts/helpers/` |

### Workflow Scripts (AI-powered, autonomous)

| Script | Purpose | Agents Used | Max Turns |
|---|---|---|---|
| `revision.sh` | Significant code rework — **PARENT** over the three children below | none itself (pure bash) | n/a |
| `revision-minor.sh` | Small scoped fixes — **PARENT**, same shape, lighter middle child | none itself (pure bash) | n/a |
| `build-phase.sh` | Implement from a plan doc | code-reviewer, refactoring-evaluator, standards-auditor | 300 |
| `plan-new.sh` | Define new project from scratch | architect, planner, security-auditor | 500 |
| `plan-revision.sh` | Revise existing planning docs | architect, planner, security-auditor, standards-architect | 300 |
| `research.sh` | Create/extend a component's source-verified research pool + synthesis | research-analyst, research-critic | 250 |
| `research-refresh.sh` | Revalidate papers that have come due; rewrite the synthesis with a diff | research-currency, research-critic | 200 |
| `review-runs.sh` | CPI log analysis (see `cpi-cycle.md` for the full cycle) | workflow-analyst | 100 |
| `review-sprint.sh` | Comprehensive end-of-sprint review (security + refactoring + testing + synthesis) | security-auditor, refactoring-evaluator, test-writer | 600 |

### Children (`scripts/workflows/children/`) — invoked BY a parent, not dispatched by you

Children are **shared, not owned**: `review-pr` is the last child of every PR-producing parent. Run one by hand only to recover — a failed review half, or a PR from a workflow not yet decomposed.

| Child | Role | Agents Used | Max Turns |
|---|---|---|---|
| `revision-draft.sh` | Writes the change, opens an UNREVIEWED PR. Holds NO review authority | none | 250 |
| `revision-refine.sh` | FRESH context: fidelity → peer review → resolve → verify | code-reviewer, refactoring-evaluator, standards-auditor, quality-control | 250 |
| `revision-draft-minor.sh` | Same role, minor tier | none | 100 |
| `revision-refine-minor.sh` | Same role, minor tier — **ONE** lens, because at this scope the risk is a change that is *wrong*, not a design that will not scale | code-reviewer | 100 |
| `review-pr.sh` | Decide-only disposition → `MERGE` \| `HOLD - redispatch` \| `HOLD - needs-assistance` | none (it reads, it does not review code) | 120 |

### Layers (`scripts/workflows/`) — sourced, never dispatched

| Folder | Holds | Rule |
|---|---|---|
| `activities/` | `run-claude`, `wait-for-ci`, `require-environment` | External I/O, workflow-agnostic, idempotent. **A parent may not inline any of it** — a workflow doing network I/O cannot replay |
| `common/` | `format-stream`, `shared-prompts` | Shared types and content. No I/O, nothing executes |

### Services (background, systemd)

| Script | Purpose | Location |
|---|---|---|
| `gh-monitor.sh` | Poll GitHub for @claude PR comments | `scripts/services/` |

## The revision split — why authoring and judging are separate runs

`revision.sh` is a **parent workflow**: pure bash that runs two independent
`claude -p` children in sequence and calls no model itself.

```
revision.sh  (parent — no model, no turn budget)
  ├─ 1. children/revision-draft.sh    250 turns   writes the change, opens an UNREVIEWED PR
  ├─ 2. children/revision-refine.sh   250 turns   FRESH context: fidelity, review, corrections
  └─ 3. children/review-pr.sh         120 turns   decide-only: MERGE, or HOLD + a runway
        │
        ├─ MERGE                   → finish
        ├─ HOLD - needs-assistance → stop NOW; more passes cannot produce a human ruling
        └─ HOLD - redispatch       → loop back ONCE (refine --correction-pass → review-pr), then stop

revision-minor.sh runs the IDENTICAL sequence with the minor children — same
shape, same routing, same single loop-back. One mental model, two weights.
```

**The reason for the boundary:** the author of a change defends it. When one
context both writes the code and dispositions the review findings about it,
findings get dismissed rather than fixed — commitment bias, and it is measured
repeatedly on this fleet. Defects have survived engineer self-review, four
in-context review agents, and manual verification, then fallen to a fresh-eyes
pass costing a few dollars. Splitting the run puts a process boundary exactly
where judgement happens.

**What crosses the boundary:** nothing but git and the task. Refine inherits
none of draft's context. Its inputs are the PR, its diff, **its comments** —
the draft's reflection is posted as a comment, so refine's Stage 1 fetch
includes `comments` explicitly; a fetch of `body,commits` alone returns a PR
that appears to have no reflection at all — and **the original task**, which
the parent passes to BOTH children. That last part is load-bearing: without the task, refine can
only ask "is this code good?", never "did this deliver what was asked?" —
and the second question is the one that catches missing scope and scope creep.

**The parent waits for CI between the children.** Refine is the only actor that
can read the delivered CI gate — pushing is draft's terminal act, so CI has not
finished when it exits. That gap is a real verification window (a run has
already caught a gate that was RED on a clean runner while green locally), so
the parent polls check runs for the draft's head SHA before starting refine.
The wait lives in the parent precisely because the parent has no turn budget:
polling costs wall-clock only, where the same loop inside refine would burn the
reliability budget the split exists to protect. On timeout it **proceeds rather
than fails** — killing a run because Actions is slow trades a large loss for a
small one — and passes `--ci-unsettled`, which makes refine state that the gate
is unknown rather than emit a clean summary that was never gate-checked.

**Turn budgets are per child**, not shared: draft gets 250 to analyse and code,
refine gets its own 250 to review and correct.

**A cap is a RUNAWAY GUARD, not a budget.** An unused turn costs nothing — spend is driven by turns actually consumed, so raising a ceiling from 200 to 250 costs zero on every run that never reaches it, and only changes when the guard fires.

This corrects an earlier framing that called caps "reliability controls." That conflated two separate things. A cap **cannot buy reliability** — it can only truncate. Reliability comes from scope discipline: the workflow-fit checks, the routing decision, the size of the task you hand a child. All a low ceiling does to a mis-scoped run is kill it partway and strand the work.

The routing signal survives, but it now reads off **consumption, not termination**: a child that routinely *uses* most of its budget was probably mis-sized and wants the next workflow up. Watch the number it spends, not whether it hit the wall.

The 200s these replaced were set when the split was unproven and a runaway was
the live worry. Two burn-test cycles later the shape holds — the highest draft
observed used 143 — so the ceilings were raised to sit clear of real work rather
than near it. Each child carries its own
`MODEL_KEY` (`revision-draft`, `revision-refine`) and its own completion
contract; the parent's contract is the children's exit codes plus a PR URL.
If draft fails, refine never runs. If refine fails, the parent says so loudly:
the PR exists and is **unreviewed**, and must not be merged as-is.

**Dispatch the parent, not the children.** `children/*.sh` are runnable alone for
recovery (re-running just the review pass on an existing PR is genuinely
useful) but they are not the interface.

This is also the shape a durable-execution engine wants — deterministic control
flow outside, non-deterministic work inside independent activities. Composition
already works in bash; Temporal would add durability, not composition.

## The research family — evidence before decisions

`research.sh` and `research-refresh.sh` exist because a decision resting on recalled training data is a decision resting on nothing checkable. They produce **source-verified evidence pools** in the consuming repo, per its Research Standard.

The pairing is the point. `research-analyst` gathers 10–20 credible sources per topic and writes the paper, marking confidence per claim and stating gaps as findings rather than hiding them. Then `research-critic` **fetches every citation** to confirm it exists and that the claim attributed to it matches its content. That second pass is an anti-hallucination gate, not a proofread — a fabricated source is exactly the failure a research artifact cannot survive, and it is invisible to the actor that wrote it.

`research-refresh.sh` handles decay. Papers carry a revalidation interval; the workflow gates in **bash** on what is actually due, so a run with nothing due exits clean without spending a model call. For each due paper `research-currency` re-sweeps the topic and diffs: what changed, what is now wrong, what is missing — and re-asks whether the topic is still the right question, which is the part a pure refresh would miss.

Both take `--pr <N>` to extend an existing research PR rather than opening a new one.

## Review-agent count rationale

Review-stage workflows dispatch a parallel **trio** (3 agents) by default. `plan-revision.sh` dispatches **four** — adding `standards-architect` alongside `architect`, `planner`, and `security-auditor`.

**Why the extra agent on `plan-revision`:** `standards-architect` surfaces corpus-level implications (cross-document drift, gap detection, ADR candidates, bloat patterns) that the other three agents — focused on the immediate revision — don't catch. CPI cycles validated this across multiple separate runs where `standards-architect` findings were unique to its lens.

Code-revision workflows (`revision-refine`, `build-phase`) keep the 3-agent trio because the review surface is narrower (specific files in a worktree, not corpus-wide), so the broader-lens agent isn't typically the binding constraint. `review-sprint.sh` uses a different 3-agent trio (`security-auditor` + `refactoring-evaluator` + `test-writer`) because it's whole-repo end-of-sprint review, where security and test-coverage lenses dominate.

All review-trios are dispatched in a single assistant message containing N `Agent` tool calls — multiple `Agent` calls in one message run concurrently, while splitting them across messages forces sequential execution and roughly doubles or triples wall time on the review stage.

## Starting a New Project

```bash
# Option 1: Full automation (init-project handles scaffolding, plan-new handles AI planning)
~/Repos/claude-dot-files/scripts/helpers/init-project.sh "my-project" --org helloskyy-io
~/Repos/claude-dot-files/scripts/workflows/plan-new.sh "my-project" "description of the project" --verbose

# Option 2: plan-new.sh auto-detects and calls init-project if needed (future)
```

## Naming Conventions

Names are **`<family>-<qualifier>`**, uniform across the fleet. The family is what the script *is*; the qualifier narrows it. Read backwards it is wrong — a PR is not a *type of thing that gets reviewed*; review is the family. Two names violated this (`pr-review`, `sprint-review`) and both were renamed.

- **`revision*`** — fix existing code. `revision.sh` is the reviewed default, `revision-minor.sh` the lighter tier. **Both are parents**; the difference is the weight of the middle child (4 review lenses vs 1)
- **`build-*`** — implement from plans
- **`plan-*`** — create or revise planning docs
- **`review-*`** — analyze and decide (`review-runs` on logs, `review-sprint` on a sprint, `review-pr` on a PR)

Directories answer *who invokes it?* — top level = you dispatch it; `children/` = a parent invokes it; `activities/` and `common/` = sourced, never run.

---

## The Dual Workflow Model

## Core Insight

Claude Code already orchestrates agents internally. When you run a regular `claude` command, Claude spawns Explore agents for research, uses the Task tool for delegation, manages context across tool calls, and coordinates its own multi-agent flows behind the scenes.

**Building elaborate custom orchestration on top of this duplicates work Claude already does.** It creates diminishing returns, burns tokens, and adds complexity without proportional value.

Custom orchestration is only valuable when you need something Claude's internal handling can't provide:

- **Named specialists at specific stages** — "use MY planner, MY architect, MY security-auditor" in a specific order with fresh context per stage
- **Walk-away workflows** — autonomous runs that complete while you do other things
- **Explicit context reset between phases** — each stage gets a fresh context window
- **Parallel execution of independent work** — multiple features built simultaneously in isolated worktrees

Everything else, Claude handles natively. This principle drives our entire development model.

## The Two Workflows

We use Claude Code through exactly two workflows. Every task falls into one of them.

### Workflow 1: Interactive Development

**When:** Daily work, small changes, learning, exploration, anything where you want to stay in the loop.

**How:** Start a continuous chat session.

```bash
claude
```

**Characteristics:**
- Direct feedback on each step
- Approval-based (popup on unlisted commands)
- Educational — you see how Claude thinks and works
- Best for: bug fixes, small features, refactoring, exploration, debugging, learning

**Permission model:**
- Conservative allow list in `settings.json`
- Popup approval on anything not allowed
- Deny list for destructive operations

**Use slash commands to accelerate common tasks:**
- `/review` — code review on recent changes
- `/best-practices <topic>` — industry-standard approach primer
- `/update-file-structure` — refresh file_structure.txt
- `/cleanup-merged-worktrees` — clean up old autonomous run artifacts

**This is the default mode.** Probably 90% of development work happens here.

### Workflow 2: Autonomous Development

**When:** Large, well-scoped features or phases where you want to walk away and come back to a PR ready for review. Two specific high-value scenarios:

1. **Initial planning of complex features** — getting multiple expert perspectives upfront (architect, planner, security auditor) saves significant time later
2. **Initial implementation of a planned phase** — executing a pre-thought-out plan while you do other work

**How:** Headless mode with `claude -p` in an isolated worktree, escalating to GitHub PR comments for refinement.

**Permission model:**
- `--dangerously-skip-permissions` flag
- Safety comes from the `block-dangerous.sh` hook (hardened against ~40 destructive patterns)
- Blast radius limited by worktree isolation
- PR review gates merge to main

## Workflow 2 — The Four Stages

Workflow 2 is not a single step. It's a staged flow with clear escalation paths.

### Stage A: Initial Autonomous Run

The primary autonomous path. You kick off a single command and get a PR ready for review.

```bash
./scripts/workflows/build-phase.sh "add user authentication with JWT"
```

Or for a smaller change:

```bash
./scripts/workflows/revision-minor.sh "fix the null check in login()"
```

Workflow scripts handle the worktree creation, claude invocation, logging, and PR creation internally — you just provide the task description.

What happens:
1. Planning pipeline runs (planner → architect → security-auditor → consolidation)
2. Implementation pipeline runs (implement → test → commit → push)
3. PR created via `gh pr create`
4. Stop hook fires desktop notification
5. You come back to a PR ready for review

**Scope:** Entire feature or phase, initial build

### Stage B: PR Review

Standard human review of the PR in GitHub's browser UI.

```
You review the PR
  ↓
Decision:
  ├── Perfect → merge
  ├── Minor issues → leave PR comments (go to Stage C)
  └── Major issues → full re-run needed (go to Stage D)
```

**Scope:** Human judgment on autonomous output

### Stage C: Minor Fix Path (PR Comments)

For small corrections, use GitHub's PR comment system. This is the most elegant iteration mechanism.

```
You leave PR comments: "fix the error handling in login()", "add test for null case"
  ↓
GitHub Actions detects @claude mention
  ↓
Claude reads comments, makes fixes
  ↓
Claude pushes to the same branch
  ↓
PR auto-updates
  ↓
You review again (back to Stage B)
```

**Why this is smart:**
- **GitHub IS the orchestration layer** — no bash state management needed
- **Comments are naturally iterative** — each comment is a correction
- **State persists in the PR** — no `/tmp/workflow/` files
- **Matches existing review workflow** — same as human code review
- **Async-friendly** — works for distributed teams
- **No custom code needed** — GitHub Actions handles the plumbing

**Scope:** Small to medium corrections that fit naturally in review comments

### Stage D: Major Fix Path (Full Re-run)

When corrections are too extensive for PR comments — architectural changes, substantial refactoring, large scope changes — escalate to a full autonomous re-run.

```bash
claude -p "/fix-pr 42 with major changes: the auth flow needs to use sessions instead of JWT" \
  --max-turns 100 \
  --dangerously-skip-permissions \
  -w fix-pr-42
```

What happens:
1. Claude checks out the existing PR branch in a new worktree
2. Applies the requested changes
3. Pushes updates to the same branch
4. PR updates with new commits
5. You review again (back to Stage B)

**Scope:** Substantial rework that would overwhelm PR comments

## Why This Model Works

### 1. It Matches Existing Workflow Patterns

PR review is already how you iterate on code. Extending that natural flow to include Claude means there's nothing new to learn — Claude just becomes another collaborator who responds to PR comments.

### 2. It Uses GitHub as the Orchestration Layer

For iteration, we don't need to build complex bash state management. GitHub PRs remember state, track comments, maintain branch history. Using GitHub as the orchestration layer means **less custom code to maintain**.

### 3. It Scales by Task Complexity

| Task Size | Workflow | Stage |
|-----------|----------|-------|
| One-line fix | Interactive | N/A |
| Bug investigation | Interactive | N/A |
| Small feature | Interactive | N/A |
| Medium feature | Either | Stage A, maybe C |
| Large phase | Autonomous | Stage A → C or D as needed |
| Entire subsystem | Autonomous | Multiple Stage A runs |

The model doesn't force you to pick one mode — it lets the task size drive the choice.

### 4. It Respects Claude's Internal Orchestration

We're not fighting what Claude already does. Custom agents and workflows only appear at specific high-value entry points (initial planning, initial build). Everything in between is Claude's native handling.

### 5. It's Portable

None of this locks us into bash scripts, Paperclip, or a specific SDK. Workflow 2 is mostly GitHub-native with a thin layer of commands on top. If Claude Code's Agent Teams goes GA, we can swap out the bash layer without changing the overall model.

## The Escalation Ladder

Think of the workflows as a ladder. You climb only as high as the task requires.

```
                                    ┌──────────────────────┐
                                    │  Stage D             │
                                    │  Full re-run         │
                                    │  (major changes)     │
                                    └──────────────────────┘
                                              ▲
                                              │ escalate
                                              │
                                    ┌──────────────────────┐
                                    │  Stage C             │
                                    │  PR comments         │
                                    │  (minor fixes)       │
                                    └──────────────────────┘
                                              ▲
                                              │ iterate
                                              │
                                    ┌──────────────────────┐
                                    │  Stage B             │
                                    │  PR review           │
                                    └──────────────────────┘
                                              ▲
                                              │ output
                                              │
                                    ┌──────────────────────┐
                                    │  Stage A             │
                                    │  Initial autonomous  │
                                    │  run                 │
                                    └──────────────────────┘
                                              ▲
                                              │
┌──────────────────────┐                      │
│  Workflow 1          │──────── for ────────►│
│  Interactive         │        everything    │
│  (default for 90%    │        else          │
│  of work)            │                      │
└──────────────────────┘
```

## What We Build

Given this model, the scope of what we actually build is narrower than it might appear.

### Essential Components

**For Workflow 1 (already built):**
- Custom agents (architect, planner, code-reviewer, test-writer, security-auditor)
- Slash commands (review, best-practices, update-file-structure, etc.)
- Safety hooks (block-dangerous.sh, notify-done.sh)

**For Stage A (Initial Autonomous Run):**
- Workflow scripts in `scripts/workflows/`:
  - `revision-minor.sh` — minor corrections, three-child parent (built)
  - `revision.sh` — significant rework, three-child parent (built)
  - `build-phase.sh` — architect & build a phase (planned)
  - `plan-new.sh` — research & planning (built)

**For Stage C (PR Comments):**
- GitHub Actions workflow file (`.github/workflows/claude-pr-handler.yml`)
- Claude GitHub App installed on repos (`claude /install-github-app`)
- Guidelines for how to write PR comments that Claude can act on

**For Stage D (Major Fix):**
- `/fix-pr <PR#>` command that checks out existing PR branch and applies corrections
- Essentially a variant of Stage A with different inputs

### What We Do NOT Build

These were considered and rejected based on research and the dual-flow principle:

- ❌ **Complex iterative refinement loops** — Use PR comments instead (Stage C)
- ❌ **Multi-stage review cycles** — Single pass with human review gate
- ❌ **Parallel multi-feature orchestration** — Wait for Agent Teams GA
- ❌ **Wrapper scripts for every combination** — Only build what's needed
- ❌ **Custom state management** — Let GitHub PRs hold state

## PR Disposition (children/review-pr.sh)

**It is a child now, and every PR-producing parent calls it as its last step.** You invoke it by hand only to recover — a PR from a workflow not yet decomposed, or a human-authored one. It lives in `children/` because a parent invokes it, and it is **shared, not owned**: no single parent has claim to it.

`review-pr.sh --pr <N>` mechanizes the PM ritual on a returned PR. **It is not a code reviewer** — the code is already the most-reviewed thing in the pipeline. Its job is to mine the place where the run *told on itself* (the decision log, deferred-work, and reflection comments): the run surfaces far more than it fixes, and the buried remainder is what this digs out. It forces every surfaced item to a terminal disposition — **FIXED** (verified against the code) / **REJECTED** (with real reasoning) / **DEFERRED** (only when the work is *already* scheduled in an existing sprint item or *already* in motion in a live PR, pointer verified present) — and ends in a binary **VERDICT: MERGE | HOLD**.

**HOLD is the catch-all runway:** anything still needing something to be right → HOLD, with an explicit "what happens next so the next pass is a MERGE" list. Each next-step is one of two shapes: **redispatch** (the correction is obvious — carries a scoped `dispatch_context` a human/parent fires) or **needs-assistance** (human-in-the-loop — the reviewer presents a `/decide` + `/best-practices`-reasoned recommendation for the operator to rule on). Not all HOLD is a dispatch: surfacing a gap bigger than the PR — an architecture or planning hole — is a first-class needs-assistance HOLD, and one of the most valuable things the workflow catches.

**The anti-rug-sweep doctrine (baked in as binding):** "recommend we move on", "low value", and "acceptable as-is" are forbidden. **"Pre-existing / existing condition" is abolished as an excuse** — a pre-existing issue is dispositioned like any other. **"Out of scope" is an input, not a disposition.** **Cost-of-dispatch is never a rationale** — a disproportionate-fix belief is a `HOLD(scope)` for the operator to rule on, never a self-granted waiver. **DEFERRED never creates a parking spot** — it only points at work that already has a home (review-pr can't write trackers, so a valid target must already exist); the reviewed PR is never a valid pointer, because *merging it is the burial*. A real but un-homed non-blocking follow-up becomes a HOLD next-step (redispatch if its home is an obvious doc edit, needs-assistance if where it belongs is a judgment call) — never buried by the merge. This doctrine exists because the first meal reasoned work away exactly as the producing run had; the fix was to state the value function explicitly (get issues corrected, don't help the PR pass) rather than patch each dodge.

**Why it works — and the premise was re-founded once already.** It used to read *"the producing run is commitment-biased."* That went false the moment `revision.sh` split authoring from judging, and every other PR-producing workflow is headed the same way. The durable premise is **every account is an account**: the PR body, a run summary, a prior pass's prescription and an agent's finding are all *claims about* the code, none of them are the code — so verify against the artifact, never the narrative, regardless of who produced the PR or whether they had a stake. That version survives any topology, and it explains what the bias framing could not: pointer-verification caught a bad disposition shape in the *reviewer's* output, against an actor with nothing to defend. **Bias does not vanish when work is split; it relocates to whoever wrote the account you are reading.**

**Decide-only (additive-automation).** It takes NO actions: never merges, closes, fixes, dispatches, or edits standards/sprints. When a fix is genuinely needed it writes a scoped, ready-to-fire `dispatch_context` into the PR comment (a `fix-needed` HOLD).

**Fix-dispatch authority has now been partly earned — and review-pr still does not hold it.** As of 2026-08-02 `revision.sh` calls review-pr as its third child and *acts on the verdict*: one bounded loop-back on `HOLD - redispatch`, immediate escalation on `HOLD - needs-assistance`. The actor that decides is still not the actor that fires; the **parent** fires, from a token review-pr wrote to a durable artifact. That separation is the point, and it is the Temporal child-workflow shape exactly: return a decision, let the parent act on it.

**The routing token is a decision, not a derived value.** `hold_kind` lives per-finding, so a HOLD mixing five `redispatch` items with one `needs-assistance` has no single answer written anywhere. Rather than have the caller aggregate — a caller with no stake making a judgement about the review — review-pr aggregates it itself onto its terminal line (`VERDICT: HOLD - needs-assistance` when ANY item needs a human). Merge authority remains entirely un-earned: nothing merges without you.

**Output = one PR comment**: a human disposition table + a machine-readable `pr_review:` yaml block (stable finding slugs + fixed category enum → the future Temporal activity-result contract; recurrence mines on the slugs). "Pass 2" is simply a later re-run on the updated PR — it detects the prior comment, increments `pass`, and reuses stable ids. Distinct from `review-runs.sh` (that mines run LOGS for process CPI; this reviews PR CONTENT for disposition).

## Model Management

Every workflow dispatch runs with an **explicit `--model`**, resolved at dispatch time from the `models:` map in `config.yaml` (repo root) by `activities/run-claude.sh`. This exists because headless runs otherwise inherit ambient defaults — a PM session's model leaks into the workflows it dispatches. Model identity is an explicit input, never derived.

**Changing a workflow's model:** edit the one line in `config.yaml`, commit. The next dispatch picks it up — no restarts, no Claude refresh.

**Alias vs pin:** map values are aliases by default (`sonnet`, `opus`, `fable` — float to the latest of that tier, zero-maintenance upgrades). Pin a row to a full model ID only on evidence: a critical push needing mid-sprint stability, or a generation jump that caused a measured regression (watch-criteria in `docs/development/cpi-decisions.md`). Either way the JSONL logs record the *resolved* model ID per run, so CPI analysis can always attribute behavior shifts to model changes.

**Per-dispatch A/B override** (bypasses the map for one run, no config change):

```bash
MODEL_OVERRIDE=fable ./scripts/workflows/build-phase.sh docs/development/phases/phase-2.md --verbose
```

**Missing key = hard failure.** If a workflow's `MODEL_KEY` has no entry in the map, the dispatch aborts loudly rather than running on an inherited default. New workflow scripts MUST add their key to `config.yaml models:` and set `MODEL_KEY` before sourcing `run-claude.sh`.

**Parent workflows have no model.** `revision.sh` is pure bash orchestration — it never calls a model, so it has no `MODEL_KEY` and does not source `run-claude.sh`. Its children do: `revision-draft` and `revision-refine` are separate rows in the map, which means the two halves of one logical revision can be tiered independently (e.g. a cheaper drafter with an expensive reviewer) by editing two lines.

**Agent models are separate:** agents pin their own model in `config/agents/*.md` frontmatter (static markdown — cannot reference config.yaml). The canonical agent-tier map is documented as a comment block in the config.yaml `models:` section; agent files must conform (checked at CPI time).

## When to Use What

Quick decision guide:

**"I just want to fix this bug"** → Workflow 1 (Interactive)
**"I'm learning a new codebase"** → Workflow 1 (Interactive)
**"Small refactor"** → Workflow 1 (Interactive)
**"I want a second opinion on my design"** → Workflow 1 + `/review` or manually invoke code-reviewer agent
**"I have a well-planned feature, build it"** → Workflow 2, Stage A
**"I'm starting a major new subsystem"** → Workflow 2, Stage A with detailed plan
**"Small scoped code fix"** → `revision-minor.sh` (reviewed by one lens, then dispositioned)
**"Significant rework — I want it reviewed before I see it"** → `revision.sh` (drafts, then judges with fresh eyes)
**"The PR is 90% right, just fix a few things"** → Workflow 2, Stage C (PR comments)
**"The PR needs major rework"** → Workflow 2, Stage D (full re-run)
**"I'm not sure where to start"** → Workflow 1, ask Claude to help you plan

## Principles

Rules we follow across both workflows:

1. **Let Claude do Claude things** — Don't reimplement what the internal orchestration already handles well
2. **Custom orchestration only at high-value entry points** — Planning and initial build, not iteration
3. **GitHub as state** — Use PR/commit history as orchestration state whenever possible
4. **Scope every investigation narrowly** — Unscoped exploration kills token budgets
5. **Verify everything** — PR review is non-negotiable
6. **Stay portable** — Don't lock into any orchestration platform that we can't easily leave
7. **Kill instead of recover** — If autonomous runs fail, restart cleanly instead of trying to rescue them

## Graduation Triggers

This model is right for now. It may not be right forever. Consider graduating when:

- You're running many concurrent autonomous workflows (3+ per day) → Consider Agent Teams when GA
- You need multi-project governance → Consider Anthropic Managed Agents or Paperclip
- You have a team using these workflows → Consider Managed Agents for consistency
- Bash scripts hit real limitations → Consider Claude Agent SDK for production-grade error handling

Until then, the dual workflow model is the right fit.
