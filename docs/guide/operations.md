# Operations Guide

How to run the harness day to day. **Deployment is covered by the [README](../../README.md)** — this document starts after everything is installed.

Two things to understand before the inventory: where the platform keeps its memory, and what a day looks like. Everything after that is reference.

---

## The memory model

Long-running work outlives any single session. Context windows do not. So the platform keeps **no state files and no bookmarks** — memory lives entirely in Git surfaces, and **"open" IS the to-do bit**. An open PR or issue is current by definition; nothing has to mark it as such.

Three surfaces, three different jobs. They are not interchangeable, and collapsing any two of them is a recurring failure:

| Surface | Holds | Lifecycle | Read by |
|---|---|---|---|
| **PR threads** | change-outcomes — what got built, the run's own decision log and reflection, and the `pr_review:` disposition ruling on it | closes at merge | `/standup`, `review-pr.sh` |
| **Issues** | no-change outcomes — deferred work `review-pr` filed, and planning STOPs | filed → ruled → **closed** | `/standup`, both `revision` children |
| **Standup tracker** | continuity — operating state, next moves, work in flight | **never closes**; items are **pruned** | `/standup` |

**Why three.** The first two cover *transactions*: something changed, or something was consciously not changed. Neither covers **continuity** — a multi-day vendor migration or a live incident is not development (so not a sprint item) and has no single done-state (so not an issue). Before the tracker existed, that work lived in session context and died at a session boundary.

**The tracker is a GitHub issue only because of the substrate.** Several sessions edit it daily; one API call beats a branch and a merge conflict on the artifact least able to afford being stale. Its semantics are its own: it never closes, items flow through it, and **a tracker that grows month over month is failing**.

**What makes this work is that every surface is written by the actor that knows something, and read by an actor that needs it.** A workflow run posts its decision log because a later reviewer will mine it. `review-pr` files an issue because nobody else will. `/standup` reads all three because you were not watching live. Nothing is written "for the record."

**The corresponding discipline:** an account is not the artifact. A PR body, a run summary, a prior pass's prescription and an agent's finding are all *claims about* the code. Every reviewing actor in this harness is bound to verify against the artifact — and to verify a pointer by **fetching** it, never by plausibility.

---

## The daily loop

```
morning  →  /standup  →  rule on what it surfaces  →  dispatch  →  (async)
                ↑                                                     │
                └──────────────  review-pr.sh  ←──  PR returns  ←─────┘
```

**1. Sign on and run `/standup`.** It reads the standup tracker first — that is where you left off, and it reframes everything after it — then sweeps open PRs and their `pr_review:` verdicts, open issues, and merges since the window. It is strictly read-only, including the tracker.

**2. Rule on what it surfaces.** This is the part that earns the command, and it is the part that rots if skipped:

- **Tracker lines** get a ruling **per line**, not per document: *acted on* (→ `RESOLVED` with a date) / *re-stated* with what changed / *explicitly carried* **with the reason it cannot move**. "Reviewed the tracker" is not a disposition.
- **Open issues** get one of four exits: *resolved now* / *scheduled into existing planning* / *planned as new work* / *closed as invalid*. **An issue must not survive a standup in the same state.**
- **`RESOLVED` tracker items older than 7 days** get pruned. The command flags them; you delete them.
- **`HOLD` PRs** arrive with their next-step already written by `review-pr`. Deliver it, don't re-derive it.

**3. Dispatch.** Pick the workflow by weight (see [Sizing](#sizing-which-workflow)), write the task, fire it, walk away. Runs are headless and isolated in their own worktrees; several can run at once on different PRs.

**4. When a PR comes back, run `review-pr.sh` on it.** It is **decide-only** — it never merges, fixes, or dispatches. It returns `MERGE` or `HOLD`, and a `HOLD` carries a runway: the ordered list of what must happen for the next pass to be a `MERGE`. You fire the redispatch; it never fires itself.

**5. Merge, or redispatch with the runway.** Then the tracker gets updated — in conversation, by you and the session. No autonomous dispatch writes to it.

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

  **Children are shared, not owned.** `children/review-pr.sh` will be called by every parent that produces a PR — `revision.sh` today, `build-phase.sh` and the planning workflows as they get decomposed. A child belongs to no single parent, which is what makes it reusable; Temporal treats child workflows the same way. So `children/` is not namespaced per parent and should not become so.

As more long-running workflows get split into parent + children, `children/` is what keeps the top level meaning *"things you dispatch."*

## Workflows

Bash scripts that run Claude headless in an isolated git worktree and deliver a PR. Every run writes a JSONL log to `.claude/logs/<workflow>-<timestamp>.jsonl`. All accept `--verbose` (stream output live), `--repo <path>` (explicit target, never derived from cwd), and `--task-file <path>` where a task is taken.

> **Flags FIRST, positional LAST.** Terminals line-wrap long commands; a trailing positional stays visible and editable when the front wraps. For anything multi-paragraph or containing quotes, write it to `/tmp/claude-<name>.md` and use `--task-file` — it bypasses command-line parsing entirely.

### `revision.sh` — significant code rework (PARENT)
The flagship, and the assembly template. **draft → refine → review-pr**, with one bounded correction loop. Pure bash — it calls no model itself; every stage is a child run. Full rationale in [workflows.md](workflows.md#the-revision-split--why-authoring-and-judging-are-separate-runs).

On `review-pr`'s verdict the parent routes itself:

| Verdict | Parent does |
|---|---|
| `MERGE` | finishes — ready to merge |
| `HOLD - redispatch` | loops back **once** (refine → review-pr), then stops regardless |
| `HOLD - needs-assistance` | stops **immediately** — more passes cannot produce a human ruling |

**Exactly one loop-back, and it is not configurable.** Self-correction plateaus at roughly 3–5 passes; past it the same model justifies rather than corrects. Counting across the pipeline — refine 1, review-pr 2, loop refine 3, review-pr 4 — one loop-back lands inside the band and two would clear it. The number comes from the research, so there is no knob to tune past it.
```bash
./scripts/workflows/revision.sh "restructure the auth flow to use sessions"
./scripts/workflows/revision.sh --repo /opt/skyy-net/skyy-command --pr 42 --task-file /tmp/claude-task.md
```

### `children/review-pr.sh` — the disposition engine (120 turns, DECIDE-ONLY)
Called automatically by every parent that produces a PR. Mines the place a run told on itself — decision log, deferred work, reflection — forces every surfaced item to a terminal ruling, and ends in `MERGE` or `HOLD` with a runway. Takes no actions except filing GitHub issues for qualifying deferred work. Run it by hand only for a PR whose producer is not yet a parent, or a human-authored PR.
```bash
./scripts/workflows/children/review-pr.sh --pr 42
```

### `children/revision-draft-minor.sh` · `children/revision-refine-minor.sh` — children of `revision-minor.sh`
Same roles as the pair below, one tier lighter. `revision-refine-minor` reviews with `code-reviewer` alone: at this scope the dominant risk is a change that is simply **wrong** (inverted condition, off-by-one, a missed case), not a design that will not scale — and correctness is the lens that catches that class.

### `children/revision-draft.sh` · `children/revision-refine.sh` — children of `revision.sh`
**Not dispatched directly** in normal use. `revision-refine.sh --pr <N> "<the same task>"` is the recovery path when the review half fails and the draft PR is sitting unreviewed — pass the *same* task, or refine loses its fidelity check.
```bash
./scripts/workflows/children/revision-refine.sh --pr 42 "the original task text"
```

### `revision-minor.sh` — small scoped fixes (PARENT)
The light tier, and **deliberately the same three-child shape as `revision.sh`** so there is one mental model rather than two: draft → refine → review-pr, with the same single bounded loop-back. The difference is entirely in the middle child — `revision-refine-minor` runs **one** review lens (`code-reviewer`) instead of four, on a cheaper model with half the turn budget. Roughly **$7 against $25–50**.

The draft child's Stage 1 still stops and escalates to `revision.sh` if the task turns out bigger than it looked. And if the review keeps surfacing *structural or standards* problems rather than correctness ones, that is a routing signal — the task was mis-sized for this tier.
```bash
./scripts/workflows/revision-minor.sh "fix the null check in login()"
./scripts/workflows/revision-minor.sh --pr 42 "add error handling to the webhook handler"
```

### `build-phase.sh` — implement from a written plan doc (300 turns)
The heavy engineer. Takes a phase document as its input rather than a prose task, so the plan is the contract. Reach for this when `revision.sh` would run out of turns.
```bash
./scripts/workflows/build-phase.sh docs/development/phases/phase-1.md "follow all standards" --verbose
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

### `sprint-review.sh` — end-of-sprint whole-repo review (600 turns)
A different trio (`security-auditor` + `refactoring-evaluator` + `test-writer`) because the lens is whole-repo rather than per-PR: security and test coverage dominate.
```bash
./scripts/workflows/sprint-review.sh --sprint "Sprint 1" --verbose
```

### Sizing: which workflow?

| The work | Use | Why |
|---|---|---|
| Known fix to known lines | `revision-minor.sh` | A review cycle would cost more than it finds |
| Multi-file, new seam, architecture touched, or "review it before I see it" | `revision.sh` | Two independent runs; the second has no stake in the first's choices |
| Won't fit in `revision.sh` | write a phase doc → `build-phase.sh` | Turn-cap pressure is a **routing** signal, not a budget one |
| Planning docs | `plan-revision.sh` (existing) / `plan-new.sh` (from scratch) | Different agents entirely |
| A returned PR | `review-pr.sh` | Always, before merging |

**Do not raise a turn cap to make a task fit.** The caps are reliability controls — per-context reliability decays as in-context memory grows, which is why the parent's children get 200 each rather than one run getting 400.

---

## Slash commands

Interactive-mode prompt templates. Type `/<name>` in a session.

| Command | What it does | Example |
|---|---|---|
| `/get-started` | Session primer — sets working roles, the dual-workflow model, and the operating pattern. Run at the start of a session. | `/get-started` |
| `/standup` | Reads the standup tracker, then sweeps PRs, issues, and merges into an attention brief. Read-only. | `/standup --since 48h` |
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
| `architecture-decisions` | When a decision needs an ADR, trade-off analysis, reversibility |
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

## Where things live

| Need | Go to |
|---|---|
| Install / deploy / sync | [README](../../README.md) |
| Why the revision split exists, model management, escalation ladder | [workflows.md](workflows.md) |
| Running the CPI cycle and reading the decisions log | [cpi-cycle.md](cpi-cycle.md) |
| Decision history — what shipped, what was deferred, and why | [`docs/development/cpi-decisions.md`](../development/cpi-decisions.md) |
| Writing a new workflow / agent / skill / rule | [`docs/standards/`](../standards/) |
| Platform background — what agents, skills, rules, headless mode *are* | `claude_code_*.md` in this folder |
| Annotated map of the whole repo | [`docs/file_structure.txt`](../file_structure.txt) |
