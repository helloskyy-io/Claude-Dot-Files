# Operations Guide

How to run the harness day to day. **Deployment is covered by [`deployment.md`](deployment.md)** — this document starts after everything is installed.

Two things to understand before the inventory: where the platform keeps its memory, and what a day looks like. Everything after that is reference.

---

## The memory model

Long-running work outlives any single session. Context windows do not. So the platform keeps **no state files and no bookmarks**: memory lives in durable records, and the record's own to-do bit is what marks work as current.

Five surfaces carry it — **PR threads**, **GitHub Issues**, the **standup tracker**, **`direction.md`** and **`candidates.md`** — and they are not interchangeable. Which one a given outcome belongs to, what each holds and for how long, who reads and writes each field, and how a later dispatch addresses a record it needs are all answered in **one** document, and it is not this one.

> **[`memory-model.md`](memory-model.md) is the framework.** It states the durable record as a substrate-free interface, this fleet's binding of it, the selection rule, the per-field consumer lists, and the addressing convention. **Read it before changing anything a surface emits or parses** — and before restating any of it here. Exactly one description of this model exists by design; a second one is drift with a delay on it.

---

## The daily loop

```
morning  →  /standup  →  rule on what it surfaces  →  dispatch  →  (async)
                ↑                                                     │
                └──────────────  review-pr.sh  ←──  PR returns  ←─────┘
```

**1. Sign on and run `/standup`.** It reads the standup tracker first — that is where you left off, and it reframes everything after it — then sweeps open PRs and their `pr_review:` verdicts, open issues, `direction.md`'s open rulings, and merges since the window. **It is a writer on three of the five surfaces**, and everything else it does is a read. The writes are what stop a finished item being re-reported every morning forever; which three, and the line in `standup.md` that declares each, are enumerated in [`memory-model.md` §2.3](memory-model.md) — **the one place that enumeration is maintained. If you find it restated elsewhere, that copy is drift: delete it and point here, rather than updating both.**

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

**Naming is `<family>-<qualifier>`, and it is now uniform across the fleet.** The family is what the script *is*; the qualifier narrows it. `review-runs` and `review-sprint` are both reviews, of run logs and of a sprint. `build-draft` and `build-refine` are both build steps, authoring and correcting. `plan-new` and `plan-revision` are both planning.

Read backwards it is wrong — a PR is not a *type of thing that gets reviewed*, review is the family. Two scripts violated this (`pr-review`, `sprint-review`) and both were renamed; the value is that families now group in `ls`, and a new script's name is a decision you make once rather than a coin flip.

Bash scripts that run Claude headless in an isolated git worktree and deliver a PR. Every run writes a JSONL log to `.claude/logs/<workflow>-<timestamp>.jsonl`. All accept `--verbose` (stream output live), `--repo <path>` (explicit target, never derived from cwd), and `--task-file <path>` where a task is taken.

> **Any MEASURED number in a brief carries the commit it was measured at.** A dispatch cannot verify *"baseline on `main`: 5101 passed"* — it can only believe it or spend turns disproving it, and briefs go stale between writing and firing. Write `5101 passed at 417162f`; the run then checks in one command. **Measured: that exact figure was 5112 at the actual branch point**, and the run had to discover it. This is the same class as a drift check reading a stale clone — a comparison is only as good as the freshness of what it compares to, and a bare number names no baseline at all.

> **Flags FIRST, positional LAST.** Terminals line-wrap long commands; a trailing positional stays visible and editable when the front wraps. For anything multi-paragraph or containing quotes, write it to `/tmp/claude-<name>.md` and use `--task-file` — it bypasses command-line parsing entirely.

### `build.sh` — significant code rework (PARENT)
The flagship, and the assembly template. **draft → refine → review-pr**, with one bounded correction loop. Pure bash — it calls no model itself; every stage is a child run. Full rationale in [workflows.md](workflows.md#the-build-split--why-authoring-and-judging-are-separate-runs).

On `review-pr`'s verdict the parent routes itself:

| Verdict | Parent does |
|---|---|
| `MERGE` | finishes — ready to merge |
| `HOLD - redispatch` | loops back **once** (refine → review-pr), then stops regardless |
| `HOLD - needs-assistance` | stops **immediately** — more passes cannot produce a human ruling |

**Exactly one loop-back, and it is not configurable.** Self-correction plateaus at roughly 3–5 passes; past it the same model justifies rather than corrects. Counting across the pipeline — refine 1, review-pr 2, loop refine 3, review-pr 4 — one loop-back lands inside the band and two would clear it. The number comes from the research, so there is no knob to tune past it.
```bash
./scripts/workflows/build.sh "restructure the auth flow to use sessions"
./scripts/workflows/build.sh --repo /opt/skyy-net/skyy-command --pr 42 --task-file /tmp/claude-task.md
```

### `children/review-pr.sh` — the disposition engine (120 turns, DECIDE-ONLY)
Called automatically by every parent that produces a PR. Mines the place a run told on itself — decision log, deferred work, reflection — forces every surfaced item to a terminal ruling, and ends in `MERGE` or `HOLD` with a runway. Takes no actions except filing GitHub issues for qualifying deferred work. Run it by hand only for a PR whose producer is not yet a parent, or a human-authored PR.
```bash
./scripts/workflows/children/review-pr.sh --pr 42
```

### `children/build-draft-minor.sh` · `children/build-refine-minor.sh` — children of `build-minor.sh`
Same roles as the pair below, one tier lighter. `build-refine-minor` reviews with `code-reviewer` alone: at this scope the dominant risk is a change that is simply **wrong** (inverted condition, off-by-one, a missed case), not a design that will not scale — and correctness is the lens that catches that class.

### `children/build-draft.sh` · `children/build-refine.sh` — children of `build.sh`
**Not dispatched directly** in normal use. `build-refine.sh --pr <N> "<the same task>"` is the recovery path when the review half fails and the draft PR is sitting unreviewed — pass the *same* task, or refine loses its fidelity check.
```bash
./scripts/workflows/children/build-refine.sh --pr 42 "the original task text"
```

### `build-minor.sh` — small scoped fixes (PARENT)
The light tier, and **deliberately the same three-child shape as `build.sh`** so there is one mental model rather than two: draft → refine → review-pr, with the same single bounded loop-back. The difference is entirely in the middle child — `build-refine-minor` runs **one** review lens (`code-reviewer`) instead of four, on a cheaper model with half the turn budget. Roughly **$7 against $25–50**.

The draft child's Stage 1 still stops and escalates to `build.sh` if the task turns out bigger than it looked. And if the review keeps surfacing *structural or standards* problems rather than correctness ones, that is a routing signal — the task was mis-sized for this tier.
```bash
./scripts/workflows/build-minor.sh "fix the null check in login()"
./scripts/workflows/build-minor.sh --pr 42 "add error handling to the webhook handler"
```

### `build-phase.sh` — implement from a written plan doc (300 turns)
The heavy engineer. Takes a phase document as its input rather than a prose task, so the plan is the contract. Reach for this when `build.sh` would run out of turns.
```bash
./scripts/workflows/build-phase.sh docs/development/phase-1.md "follow all standards" --verbose
```

### `plan-new.sh` — define a new project from scratch (500 turns)
14-stage planning pipeline (architect + planner + security-auditor). Produces the docs a `build-phase.sh` run later consumes. Pair with `scripts/helpers/init-project.sh` for the non-AI scaffolding.
```bash
~/Repos/claude-dot-files/scripts/helpers/init-project.sh "my-project" --org helloskyy-io
~/Repos/claude-dot-files/scripts/workflows/plan-new.sh "my-project" "description of the project" --verbose
```

### `plan-revision.sh` — revise existing planning docs (300 turns)
Roadmaps, phase docs, requirements, epics. Four review agents including `standards-architect` for corpus-level implications. **Not for code** — the agents are wrong for it, and a bulk rename dispatched here once burned 301 turns and $37.
```bash
./scripts/workflows/plan-revision.sh "add a detailed phase doc for the Harbor integration" --verbose
```

### `research.sh` — build a source-verified evidence pool (250 turns)
`research-analyst` gathers sources and writes mini-papers; `research-critic` fetches every citation to confirm it exists and says what it is claimed to say. Use before a decision that rests on external ground truth.
```bash
./scripts/workflows/research.sh "durable execution engines for multi-language workers" --verbose
```

### `research-refresh.sh` — revalidate papers that have come due (200 turns)
Bash-side gate: exits cleanly with no model call when nothing is due. `research-currency` diffs a fresh sweep against each paper — what changed, what is now wrong, what is missing — and re-establishes the interval.
```bash
./scripts/workflows/research-refresh.sh
./scripts/workflows/research-refresh.sh --pr 18   # gate on one PR's pool
```

### `review-runs.sh` — the CPI analysis pass (100 turns)
Reads `.claude/logs/` **from inside the repo whose runs you want analyzed** and produces an improvement report. Cross-references `cpi-decisions.md` so findings matching a prior watch-criterion are flagged as recurrences.
```bash
cd /opt/skyy-net/skyy-command && ~/Repos/claude-dot-files/scripts/workflows/review-runs.sh --days 21
```

### `review-sprint.sh` — end-of-sprint whole-repo review (600 turns)
A different trio (`security-auditor` + `refactoring-evaluator` + `test-writer`) because the lens is whole-repo rather than per-PR: security and test coverage dominate.
```bash
./scripts/workflows/review-sprint.sh --sprint "Sprint 1" --verbose
```

### Sizing: which workflow?

| The work | Use | Why |
|---|---|---|
| Known fix to known lines | `build-minor.sh` | A review cycle would cost more than it finds |
| Multi-file, new seam, architecture touched, or "review it before I see it" | `build.sh` | Two independent runs; the second has no stake in the first's choices |
| Won't fit in `build.sh` | write a phase doc → `build-phase.sh` | Turn-cap pressure is a **routing** signal, not a budget one |
| Planning docs | `plan-revision.sh` (existing) / `plan-new.sh` (from scratch) | Different agents entirely |
| A returned PR | `review-pr.sh` | Always, before merging |

**A cap is a RUNAWAY GUARD, not a budget.** An unused turn costs nothing — spend is driven by turns actually consumed, so raising a ceiling from 200 to 250 costs zero on every run that never reaches it, and only changes when the guard fires.

This corrects an earlier framing that called caps "reliability controls." That conflated two separate things. A cap **cannot buy reliability** — it can only truncate. Reliability comes from scope discipline: the workflow-fit checks, the routing decision, the size of the task you hand a child. All a low ceiling does to a mis-scoped run is kill it partway and strand the work.

The routing signal survives, but it now reads off **consumption, not termination**: a child that routinely *uses* most of its budget was probably mis-sized and wants the next workflow up. Watch the number it spends, not whether it hit the wall.

---

## Slash commands

Interactive-mode prompt templates. Type `/<name>` in a session.

| Command | What it does | Example |
|---|---|---|
| `/get-started` | Session primer — sets working roles, the dual-workflow model, and the operating pattern. Run at the start of a session. | `/get-started` |
| `/standup` | Reads the standup tracker, then sweeps PRs, issues, `direction.md` and merges into an attention brief. Writer on three of the five surfaces — the write set is in [`memory-model.md` §2.3](memory-model.md). | `/standup --since 48h` |
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
