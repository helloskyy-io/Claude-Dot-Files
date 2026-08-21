# Claude Dot Files

A self-improving Claude Code development environment. Custom agents, autonomous workflows, and a continuous process improvement loop — synced across all your machines.

Everything here is Python, markdown and git. There is no server, no daemon and no framework: workflows are parent/child modules that invoke `claude -p` in isolated worktrees, agents and skills are markdown, and the memory is GitHub.

**What makes this different from a basic dotfiles repo:**

- **Parent/child workflows** — the flagship pattern. A workflow that both writes code and rules on the review findings about it will defend its own work; no amount of prompt engineering fixes that. So the run that authors is no longer the run that judges. [How it works](#the-flagship-parentchild-workflows)
- **Verification over narrative** — every reviewing actor is bound to check claims against the artifact rather than the account of it. A PR body, a run's summary, a prior pass's prescription and an agent's finding are all *claims about* the code; none of them are the code
- **Git-native memory** — no state files, no bookmarks: the record's own to-do bit is what marks work as current. Five surfaces carry it — PR threads (change-outcomes), Issues (no-change outcomes), a standup tracker (continuity), and two committed markdown tables, `direction.md` (operator rulings) and `candidates.md` (research candidates). `/standup` reads all five into a morning brief and **writes on three of them**. [The memory model](docs/guide/memory-model.md)
- **Continuous process improvement** — `review-runs` analyses Claude's own workflow logs across repos; every finding lands in an append-only decisions log as ship / defer / reject with explicit watch-criteria. Nothing is deferred without a condition that would bring it back. *(It is the one workflow still living only in the frozen bash tree — porting it is a named phase of Temporal Integration, and it is the one of the four with a real run history.)*
- **12 agents · 17 skills · 11 workflows · 10 slash commands** — model-tiered per role, web-enabled only where ground truth lives outside the repo. [Full roster](docs/guide/operations.md)

## The flagship: parent/child workflows

The problem is not that models write bad code. It is that **the author of a change defends it.** A single run that implements something and then dispositions the review findings about it will dismiss findings rather than fix them — and this is not fixable by wording. Engineer self-review, four in-context review agents under an explicit disposition taxonomy, and manual verification all failed to catch defects that a fresh-context pass then found in minutes.

So the boundary is structural rather than textual:

```
build.sh  (parent — orchestration only, calls no model itself)
  ├─ 1. build_draft     writes the change, opens an UNREVIEWED PR
  ├─ 2. build_refine    FRESH context: did this deliver what was asked? then review, fix
  └─ 3. review_pr       decide-only: MERGE, or HOLD with a runway

build_minor.sh          the same shape, one review lens instead of five
```

Neither child inherits the other's context. The handoff is git — the PR, its diff, its comments — plus **the original task, which both children receive**, so the reviewer can ask *did this deliver what was asked?* and not merely *is this code good?*

Two properties fell out that were not the original goal. Each child boundary is a **retry/resume point**, which a monolith cannot have. And the completion contract that makes `exit 0` mean *finished* turns out to be the entire interface between runs — a parent needs a child's exit code plus one stable identifier on its final line, which is why composition here needs no framework.

[Full rationale and the escalation ladder →](docs/guide/workflows.md)

## Quick start

```bash
git clone https://github.com/helloskyy-io/Claude-Dot-Files.git ~/Repos/claude-dot-files
cd ~/Repos/claude-dot-files && ./install.sh
claude login && gh auth login
```

Then, in any repo:

```bash
claude                # interactive
/get-started          # session primer — roles, the dual-workflow model, operating pattern
/standup              # what needs attention this morning
```

Prerequisites, VM and Ansible paths, troubleshooting: **[Deployment guide →](docs/guide/deployment.md)**

## Two modes

**Interactive** is the default for most work — you and Claude, approving changes as they happen, with slash commands for the repeatable parts.

**Autonomous** is for planned work you can walk away from. A workflow runs headless in an isolated git worktree, reviews its own output through agent panels, and delivers a PR:

```bash
W=scripts/workflows/temporal/scripts
$W/build.sh "restructure the auth flow to use sessions"
$W/build.sh --phase docs/development/<component>/phase1_<name>.md --verbose
$W/review_pr.sh --pr 42 --type build
```

Eleven entrypoints in all — three build tiers, six planning, two research. `--pr <n>` turns any of them into a correction pass against work already on a PR.

Every run writes a JSONL log to `.claude/logs/` — which is what the CPI loop later reads.

**[Operations guide →](docs/guide/operations.md)** — the memory model, the daily loop, and a one-entry reference for every workflow, agent, command, skill and rule.

## Safety

Autonomous runs pass `--dangerously-skip-permissions`, so the `PreToolUse` hook is the **only control operating during a run** — worktree isolation only bounds blast radius, and PR review happens after the fact. `block-dangerous.sh` is therefore load-bearing rather than defence-in-depth, and it fails closed. Nothing reaches `main` except through a PR.

## Where things are

| | |
|---|---|
| **[Deployment](docs/guide/deployment.md)** | Install, sync, VMs, Ansible, troubleshooting |
| **[Operations](docs/guide/operations.md)** | Running it day to day; the full roster |
| **[Workflows](docs/guide/workflows.md)** | Architecture: the split, model management, escalation |
| **[CPI cycle](docs/guide/cpi-cycle.md)** | How the system improves itself |
| **[Sprint plan / roadmap](docs/development/sprint.md)** | Dual purpose: the project roadmap across components, and the tracker for work in flight |
| **[Decisions log](docs/development/cpi-decisions.md)** | Append-only record of every ship / defer / reject, with evidence |
| **[Standards](docs/standards/)** | Binding rules for contributing — workflows, agents, skills, hooks, services, docs |
| **[File structure](docs/file_structure.txt)** | Annotated map of the whole repo |

## Status and direction

Actively developed and in daily production use across several repos.

**[`docs/development/sprint.md`](docs/development/sprint.md) is the single source for what is planned and where it stands**, and it serves a dual purpose: a **project roadmap** across every component, and the **sprint tracker** for the work in flight. It is not restated here — a second copy is a copy that goes stale.

What it gives you at a glance:

- **A status marker per sprint, derived rather than typed** — 🔵 not scheduled · 🟠 planned · 🟡 in progress · ✅ complete. The state follows from the checkboxes below it, so a marker that disagrees with its own items is a defect.
- **Hours where a component has been cold-sized**, totalled and net of what is done — also derived, from each roadmap's own estimates. An absent figure honestly means *never sized*, which is actionable.
- **Two links per item** — the component's roadmap and the phase doc — so any line reaches its plan in one hop.

**Phases are cited by NAME, never by number.** The number is identity, like a ticket number, and it lives in the filename where the tooling reads it; the roadmap lists in *build* order, which is not numeric order. Temporal Integration builds 1, 2, 3, **9**, 4, 5, 6 — `review-runs` was split out late and took the next free number while sitting where it actually builds. An ordinal in a sprint line is a claim about sequence that the sequence does not honour.

The [decisions log](docs/development/cpi-decisions.md) is the other half of the honest record. It carries rejected items and withdrawn claims alongside shipped ones, including cases where a finding was retracted after its evidence did not hold.

## Contributing

Read `CLAUDE.md` first — it indexes the standards, and the applicable ones are meant to be read before work starts. Standards are human-in-the-loop: agents and workflows surface candidates, they never write them.

## License

[MIT](LICENSE)
