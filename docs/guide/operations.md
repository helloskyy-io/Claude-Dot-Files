# Operations Guide

How to run the harness day to day. **Deployment is covered by [`deployment.md`](deployment.md)** — this document starts after everything is installed.

Two things to understand before the inventory: where the platform keeps its memory, and what a day looks like. Everything after that is reference.

---

## The memory model

Long-running work outlives any single session. Context windows do not. So the platform keeps **no state files and no bookmarks**: memory lives in durable records, and the record's own to-do bit is what marks work as current.

The surfaces that carry it are **PR threads** and the four **`tracked/` stores** — `issues/`, `operations/`, `candidates/` and `standards/`** — and they are not interchangeable. Which one a given outcome belongs to, what each holds and for how long, who reads and writes each field, and how a later dispatch addresses a record it needs are all answered in **one** document, and it is not this one.

> **[`memory-model.md`](memory-model.md) is the framework.** It states the durable record as a substrate-free interface, this fleet's binding of it, the selection rule, the per-field consumer lists, and the addressing convention. **Read it before changing anything a surface emits or parses** — and before restating any of it here. Exactly one description of this model exists by design; a second one is drift with a delay on it.

---

## The daily loop

```
morning  →  /standup  →  rule on what it surfaces  →  dispatch  →  (async)
                ↑                                                     │
                └──────────────  review-pr.sh  ←──  PR returns  ←─────┘
```

**1. Sign on and run `/standup`.** It reads `tracked/operations/` first — that is where you left off, and it reframes everything after it — then sweeps open PRs and their `pr_review:` verdicts, open issues, `direction.md`'s open rulings, and merges since the window. **It is a writer on three of the five surfaces**, and everything else it does is a read. The writes are what stop a finished item being re-reported every morning forever; which three, and the line in `standup.md` that declares each, are enumerated in [`memory-model.md` §2.3](memory-model.md) — **the one place that enumeration is maintained. If you find it restated elsewhere, that copy is drift: delete it and point here, rather than updating both.**

**2. Rule on what it surfaces.** This is the part that earns the command, and it is the part that rots if skipped:

- **Tracker lines** get a ruling **per line**, not per document: *acted on* (→ `RESOLVED` with a date) / *re-stated* with what changed / *explicitly carried* **with the reason it cannot move**. "Reviewed the tracker" is not a disposition.
- **Open issues** get one of four exits: *resolved now* / *scheduled into existing planning* / *planned as new work* / *closed as invalid*. **An issue must not survive a standup in the same state.**
- **`RESOLVED` tracker items older than 7 days** get pruned. The command flags them; you delete them.
- **`HOLD` PRs** arrive with their next-step already written by `review-pr`. Deliver it, don't re-derive it.

**3. Dispatch.** Pick the workflow by weight (see [Sizing](#sizing-which-workflow)), write the task, fire it, walk away. Runs are headless and isolated in their own worktrees; several can run at once on different PRs.

**4. When a PR comes back, run `review-pr.sh` on it.** It is **decide-only** — it never merges, fixes, or dispatches. It returns `MERGE` or `HOLD`, and a `HOLD` carries a runway: the ordered list of what must happen for the next pass to be a `MERGE`. You fire the redispatch; it never fires itself.

**5. Merge, or redispatch with the runway.** Then the tracker gets updated — by you and the session in conversation, or by `/standup`'s own reconciliation pass. **No autonomous dispatch writes to it**; that remains true and is a different claim from step 1's, since `/standup` runs in an operator session.

**The CPI loop runs on top of this**, not inside it: `review-runs.sh` analyzes the JSONL logs every run leaves in `.claude/logs/`, and findings land in `docs/development/cpi-decisions.md` as ship/defer/reject with explicit watch-criteria. See [cpi-cycle.md](cpi-cycle.md).

---

## How the scripts are organized

One question explains every folder under `scripts/`: **who invokes it?**

```
scripts/
├── helpers/    ← YOU run.     Pure bash, no AI, zero tokens (init-project.sh, lint-prompts.sh)
├── services/   ← SYSTEMD runs. Background pollers, also no AI
└── workflows/  ← YOU run.     Each one calls Claude headless
    ├── activities/ ← SOURCED.  External I/O, workflow-agnostic, idempotent (run_claude, wait_for_ci)
    ├── common/     ← SOURCED.  Shared types and content — no I/O (formatter, shared prompt text)
    └── children/  ← THE PARENT runs. Full workflows in their own right — own model, turn budget,
                     completion contract, worktree — but invoked BY a parent, not by you
```

Two distinctions do the work, and both are easy to miss:

- **`helpers/` vs `activities/`+`common/`** — a helper is a standalone executable you *run*; an activity is bash a workflow *sources*. Same file extension, opposite usage.
- **`activities/` vs `common/`** — the split is **does it touch the outside world?** `activities/` holds external I/O (invoking Claude, polling the GitHub API): workflow-agnostic, single-responsibility, idempotent, and **never inlined into a parent** — a workflow that does network I/O cannot replay, which is why Temporal enforces this boundary rather than merely recommending it. `common/` holds shared types and content that execute nothing. Keeping them apart stops `activities/` becoming the generic dumping ground.
- **`workflows/` vs `children/`** — the axis is *who invokes it*, and nothing else. Top level = **you dispatch it**. `children/` = **a parent invokes it**; you only run one by hand when something upstream went wrong (a failed review half, a PR from a workflow not yet decomposed). That is the whole rule.

  **Children are shared, not owned.** `children/review-pr.sh` will be called by every parent that produces a PR — `build.sh` today, `build-phase.sh` and the planning workflows as they get decomposed. A child belongs to no single parent, which is what makes it reusable; Temporal treats child workflows the same way. So `children/` is not namespaced per parent and should not become so.

As more long-running workflows get split into parent + children, `children/` is what keeps the top level meaning *"things you dispatch."*

## Workflows

**The roster lives in [`workflows.md`](workflows.md) and is not restated here.** It carries all eleven entrypoints, what each one composes, and which children it dispatches.

This section used to hold its own copy, and the copy rotted: it documented `children/review-pr.sh`, `build-phase.sh`, `plan-new.sh`, `review-runs.sh` and `review-sprint.sh` — names from the frozen tree — while eight live entrypoints appeared nowhere. A second list of the same population is a list that goes stale, and this one did.

What belongs here is the part `workflows.md` does not cover: how you run them.

### Check before you spend: `--dry-run`

**Seven of the eleven entrypoints take `--dry-run`.** It renders the prompt and exits: no model call, no comment, no spend. Use it when you are about to commit budget to a long run and want to see what it will actually be handed.

| Takes `--dry-run` | Does not |
|---|---|
| `plan_feature.sh` · `plan_sprint.sh` · `plan_verify.sh` · `research.sh` · `research_minor.sh` · `review_pr.sh` · `triage_candidates.sh` | `build.sh` · `build_minor.sh` · `plan_project.sh` · `plan_revision.sh` |

**The gap is on the expensive side, and it is worth knowing before you plan around it.** The build tier is the longest and costliest run in the fleet and cannot be previewed; `plan_project.sh` composes five children and cannot either. This sentence used to read *"every entrypoint"*, which was wrong and was caught by a `build.sh --dry-run` that errored out.

```bash
scripts/workflows/temporal/scripts/triage_candidates.sh --dry-run
scripts/workflows/temporal/scripts/plan_verify.sh docs/development/<component> --dry-run
```

It prints the rendered prompt size with placeholders resolved, the turn ceiling, the write grants the run will hold, and whatever counts that workflow reads off the tree.

**One thing it cannot tell you, and it says so in its own output.** A dry run cuts no worktree, so every count comes from **this checkout** — while a `--pr` run reads a worktree cut from `origin/<the PR's branch>`. On a correction pass those differ, and a plan that is fully written on the branch previews as `0`. The line `Counted in : this checkout (...)` is the run telling you which tree the numbers describe. Issue #134 records the ruling and what a stronger version would cost.

### Correcting work already on a PR

`--pr <n>` turns any entrypoint into a correction pass against an existing PR rather than opening a new one. The run cuts its worktree from that PR's branch.

### Long tasks

Use `--task-file /tmp/claude-<name>.md` rather than a positional argument for anything multi-paragraph — it bypasses shell parsing entirely, so quotes, newlines and backticks pass through literally. Flags first, positional last.

## Slash commands

Interactive-mode prompt templates. Type `/<name>` in a session.

| Command | What it does | Example |
|---|---|---|
| `/get-started` | Session primer — sets working roles, the dual-workflow model, and the operating pattern. Run at the start of a session. | `/get-started` |
| `/standup` | Reads `tracked/operations/`, drains the tracked-item intake, then sweeps PRs and issues into an attention brief. Writer on three of the five surfaces — the write set is in [`memory-model.md` §2.3](memory-model.md). | `/standup --since 48h` |
| `/review` | Runs `code-reviewer` on recent changes, reported by severity. | `/review` |
| `/best-practices` | Primes the session with the industry-standard approach to a topic before you build. | `/best-practices retry backoff in distributed queues` |
| `/decide` | Five-whys reframing cascade — reframes the question before answering, for low/mid-confidence calls. | `/decide should we pin model versions per workflow?` |
| `/troubleshoot` | Hypothesis-driven bisection with structured escalation, instead of guess-and-check. | `/troubleshoot the gh-monitor timer fires but nothing dispatches` |
| `/create-claude` | Generates CLAUDE.md files for a project root and its major directories. | `/create-claude` |
| `/update-claude` | Syncs every CLAUDE.md's standards references against `docs/standards/`. | `/update-claude` |
| `/update-file-structure` | Refreshes `docs/file_structure.txt` from the current tree. | `/update-file-structure` |
| `/cleanup-merged-worktrees` | Removes worktrees whose PRs have merged or closed. Run after a batch of dispatches lands. | `/cleanup-merged-worktrees` |

---

## Agents

Subagents invoked by workflows and by you. All are read-only unless noted. Model tier is pinned in each agent's own frontmatter — see the canon comment in `config.yaml`.

**Review lenses** — distinct questions, run in parallel during review stages:

| Agent | Asks | Model |
|---|---|---|
| `code-reviewer` | Is this code correct? Bugs, edge cases, real failure modes | sonnet |
| `refactoring-evaluator` | Could this be structured better? | sonnet |
| `standards-auditor` | Does this match our documented standards and exemplars? | sonnet |
| `security-auditor` | Are there vulnerabilities? *(web-enabled for CVE verification)* | opus |
| `quality-control` | Would a senior engineer at a top-tier org sign off? Runs **sequentially after** the others, with their findings | sonnet |

**Planning:**

| Agent | Asks | Model |
|---|---|---|
| `architect` | Is the design coherent and scalable? *(web-enabled for industry verification)* | opus |
| `planner` | Is this feasible and well-scoped? | opus |

**Research** — the family behind `research.sh` / `research-refresh.sh`, all web-enabled:

| Agent | Does | Model |
|---|---|---|
| `research-analyst` | Gathers 10–20 credible sources per topic, writes the paper, marks confidence per claim | opus |
| `research-critic` | **Fetches every citation** to confirm it exists and supports the claim. The anti-hallucination gate | sonnet |
| `research-currency` | Re-sweeps an existing paper, diffs it, and re-establishes its revalidation interval | opus |

**Corpus and meta:**

| Agent | Does | Model |
|---|---|---|
| `standards-architect` | Audits the standards docs *themselves* for drift, duplication, and gaps — not per-PR conformance | sonnet |
| `doc-manager` | Documentation systems engineer, four modes: AUTHOR / COORDINATE / AUDIT / MAINTAIN. Substance always human-in-the-loop | sonnet |
| `test-writer` | Generates tests for existing code *(can write)* | sonnet |
| `workflow-analyst` | Analyzes workflow logs for patterns and inefficiencies — the engine behind `review-runs.sh` | sonnet |

Invoke one directly when you want a specific lens: *"use the security-auditor agent on the new webhook handler."*

---

## Skills

Methodology documents Claude loads on demand when the context matches. You rarely invoke these directly — they shape *how* work gets done when it starts.

| Skill | Covers |
|---|---|
| `planning-methodology` | Feature and phase breakdowns, dependencies, sizing |
| `architecture-decisions` | When a decision needs recording as a standard, trade-off analysis, reversibility |
| `decision-methodology` | Five-whys reframing — behind `/decide` |
| `troubleshooting-methodology` | Bisection + hypothesis testing + structured escalation — behind `/troubleshoot` |
| `testing-methodology` | Principles, scoping, execution for writing and fixing tests |
| `testing-scaffolding` | Standing up a suite in a project that has none |
| `test-suite-architecture` | Test placement, suite wiring, master runners, scoped regression |
| `refactoring-methodology` | What to refactor vs leave alone, and how to do it safely |
| `standards-authoring` | Writing timeless, rule-focused standards docs |
| `standards-enforcement` | Verifying conformance against the CLAUDE.md chain and exemplars |
| `documentation-structure` | The four-bucket convention, formats, naming |
| `documentation-management` | The full doc lifecycle — behind `doc-manager` |
| `quality-control-methodology` | The six-dimension senior-engineer lens |
| `project-definition` | Defining a project from scratch — requirements, stack, roadmap |
| `project-organization` | Multi-repo vs single-repo, deployment-location conventions |
| `workflow-analysis` | Reading workflow logs for patterns — behind `review-runs.sh` |
| `workflow-dispatch` | Picking the right workflow and writing an effective task prompt |

---

## Rules

Always-loaded global instructions. Unlike skills, these are not on-demand — every session gets all of them, so they stay short and binding.

| Rule | Binds |
|---|---|
| `engineering-quality` | The quality bar: no bandaids, surface assumptions, finding disposition, surgical changes. The longest and most-cited rule |
| `safety` | Never commit secrets, never force push or run destructive commands without approval |
| `git` | Conventional commits, don't push or amend unless asked |
| `code-style` | Readability over cleverness, early returns, match local style |
| `communication` | Don't annotate code you didn't change; ask before exceeding scope |
| `dependencies` | Check what exists before adding; prefer stdlib for trivia |
| `terminal-output` | **No heredocs in commands given to the operator**; single-line, absolute paths, `--task-file` for payloads |
| `standards-governance` | Standards are human-in-the-loop; `sprint.md` is never edited by autonomous dispatch |
| `proactive-doc-management` | Doc updates are triggered by work, not requested |
| `personal-tooling` | Where the workflow scripts live |
| `claude-dot-files-governance` | Project sessions surface tooling improvements; they never edit this repo directly |

---

## What this repo puts on your machine

`install.sh` symlinks seven items into `~/.claude/` and that list is in
[`CLAUDE.md`](../../CLAUDE.md). **It is not the whole footprint**, and the rest is
here because state that nothing documents is state nobody knows to look at, back
up, or delete.

| Path | Who writes it | Removed by |
|---|---|---|
| `~/.claude/{settings.json,CLAUDE.md,agents,commands,hooks,rules,skills}` | `install.sh`, as symlinks into this repo | `install.sh` / deleting the link |
| `<repo>/.claude/logs/*.jsonl` | every dispatch, one file per run | nothing — there is no pruning code |
| `<repo>/.claude/worktrees/<name>/` | any workflow that cuts a worktree | `/cleanup-merged-worktrees` |
| `~/.local/state/claude-dot-files/journal/<run_id>/` | **every non-dry-run dispatch**, created on demand, mode `0700` | nothing yet — retention is [PMP Phase 5](../development/persistent-memory-protocol/phase5_snapshots_then_retention.md) |

**The journal root is the one outside any repository checkout**, which is
deliberate: it is state rather than source, so it survives a clone being deleted
and never lands in a commit. Its location is a config value —
[`config.yaml`](../../config.yaml) `journal.root:`, empty meaning the documented
default for `journal.deployment:` (`user` → the path above, following
`XDG_STATE_HOME`; `systemd` → `/var/lib/claude-dot-files/journal`; `container` →
no default, so it must be set). A root that cannot be resolved to a writable,
correctly-moded directory outside any git working tree **stops the run before it
starts**, with a message naming the resolved path and the failing property.

Inspect one with `python3 scripts/workflows/temporal/scripts/validate_bag.py`,
which takes a single bag, a whole root, or nothing (resolving the configured root
read-only). Today a bag is ~16 KiB; from PMP Phase 3, when runs start writing
into it, expect roughly 4.9 MB per run.

---

## Where things live

| Need | Go to |
|---|---|
| What this repo writes to disk outside the repo | [above](#what-this-repo-puts-on-your-machine) |
| Install / deploy / sync | [deployment.md](deployment.md) |
| Why the build split exists, model management, escalation ladder | [workflows.md](workflows.md) |
| Running the CPI cycle and reading the decisions log | [cpi-cycle.md](cpi-cycle.md) |
| Decision history — what shipped, what was deferred, and why | [`docs/development/cpi-decisions.md`](../development/cpi-decisions.md) |
| Writing a new workflow / agent / skill / rule | [`docs/standards/`](../standards/) |
| Platform background — what agents, skills, rules, headless mode *are* | `claude_code_*.md` in this folder |
| Annotated map of the whole repo | [`docs/file_structure.txt`](../file_structure.txt) |
