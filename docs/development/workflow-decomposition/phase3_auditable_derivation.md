# Phase 3 — A derived value you can audit

**Component:** [Workflow Decomposition](roadmap.md) · **Status:** not started · **Gate:** none — the mechanism it finishes is already running

## What this phase does

A workflow in this fleet does not learn everything from flags. It reads the repository root off git, reads the component it is planning from a path it was handed, and builds several more values from those two. Those are **derived** values, and they are the right design — a constant restated in two places diverges silently, which is why the [Architecture Standard](../../standards/architecture/architectural_standard.md) carries `derive ≠ declare` as a seam.

Derivation has one failure mode that a flag does not, and it is the reason this phase exists:

> **A wrong flag fails loudly at parse time. A wrong derivation produces a *plausible* wrong run** — the workflow competently plans the wrong component, opens a real pull request, and nothing anywhere goes red.

The field's answer to that is five properties a safe derived value has: it is anchored on a **marker** (a fact, not a resemblance), its **algorithm is published**, the run **echoes** what it derived, an explicit **override** exists, and the value **states its scope of effect**. Measured against what shipped here: **the marker and the override already exist.** The other three do not.

So this phase is smaller than its checkbox suggests. It is not building a derivation subsystem. It is finishing three properties on code that runs today, and then proving the important one by pointing a run at the wrong thing and watching it say so out loud.

**Terms used here.** A **derived value** is anything a run computes rather than being told — the repo root, the component under plan, a path built from another path. A **marker** is a fact the derivation anchors on, like the presence of a `.git` directory, as opposed to a similarity judgement. An **echo** is the run stating, in its own output, what it derived and from what. **Scope of effect** is the answer to *what else is wrong if this value is wrong*.

---

## Requirements for completion

1. **Every derived value in the fleet is enumerated** with its marker, its algorithm in one sentence, its override if it has one, and its scope of effect. Published where a reader looks — not recoverable only by reading the call chain.
2. **A live run echoes what it derived.** Not a rehearsal: `plan-feature` already prints its component, its phase-doc count and its grants **under `--dry-run` only**, and prints none of it on the run that actually dispatches. The echo has to be on the path that does the work.
3. **A parent can silence the echo without destroying the record.** `verbose` is already threaded through this fleet as an explicit parameter rather than sniffed from the terminal, and the caller that most wants quiet output — a parent running nine children — is exactly the caller that most needs the derivation recorded. Silencing the console must not silence the record.
4. **Each derived value states its scope of effect** at the place it is derived, in a form a reader hits before the value is used.
5. **A wrong derivation is DEMONSTRATED to be visible.** Point a run at the wrong component, capture the echo, and show that the output names what it derived before the run costs anything. This is the phase's end-to-end proof and requirements 1–4 are not complete without it.

**Requirement 3 carries an unresolved trade, and it stays unchecked until somebody rules it.** Echoing costs output; the parent that wants silence is the one that needs the echo most. Nobody has measured the cost, and the evidence is explicit that this is argued convention across every source found, not data. **Rule it in this phase, in one sentence, and record the ruling** — do not let it be decided implicitly by whichever stream the first implementation happens to write to.

---

## Dependencies

- **[Phase 1](roadmap.md)** — complete. The activities layer this derivation lives in came out of it.
- **Nothing outside this component.** No sibling component and no external system gates this.
- **Not gated on [Phase 5](roadmap.md).** Dual-mode invocation and scope derivation are the two halves of the invocation contract and they are independent: the echo is worth having whether or not any child gains a standalone runner.

---

## What this phase decides

### The five properties, and which two are already satisfied

| Property | State today | What this phase does |
|---|---|---|
| **Anchored on a marker** | ✅ satisfied — `resolve_repo_root` runs `git rev-parse --show-toplevel`, which reads `.git` and never guesses | nothing; record it as satisfied so it is not rebuilt |
| **Explicit override** | ✅ satisfied — `--repo` exists and is documented as *a FILESYSTEM PATH, never a gh slug* | nothing |
| **Published algorithm** | ❌ absent | requirement 1 |
| **Echo of what was derived** | ⚠️ partial — exists under `--dry-run`, absent on the live path | requirements 2 and 3 |
| **Stated scope of effect** | ❌ absent | requirement 4 |

Source: [`research/synthesis.md`](research/synthesis.md) § *Facet 2's real work is three missing properties*, resting on [`raw/invocation_contract.md`](research/raw/invocation_contract.md) §2.2 (M1–M5), §4.2 and §5.2.

### "Prefer derivation" is NOT the rule, and writing it would contradict a shipped decision

The tempting generalisation from this phase is *derive where you can*. **Do not write it.** This repo already made the opposite call in one specific place and made it correctly: **repo identity is declared** — `--repo`, explicitly never derived from the working directory — **while component scope is derived** from the path the run was pointed at.

Derivation is a **per-value decision with a stated reason**, not a policy. A rule saying otherwise would quietly reopen a question that is settled and working.

### The scope of effect is not decoration — it is what makes the echo readable

`resolve_repo_root`'s own comments already record what a wrong answer costs: `.claude/worktrees/` and `.claude/logs/` both hang off it, so a run rooted at a subdirectory scatters worktrees and logs where `/cleanup-merged-worktrees` never looks, and a later cleanup deletes the logs along with the workspace — after which cost accounting for those runs is unrecoverable. **Six of seven V2 entrypoints once dropped repo-root resolution and used the working directory instead.**

That paragraph is the model for requirement 4. An echo that prints a path tells a reader *what* was derived; the scope of effect is what tells them whether to care.

### What this phase does not do

- **It does not touch dual-mode invocation.** That is [Phase 5](roadmap.md) and it is gated on a ruling.
- **It does not add a new derived value.** Every value in scope already exists; this phase makes the existing ones legible.
- **It does not build a config digest.** What a run absorbed from `~/.claude/` is a different question with a different mechanism — [Phase 6](phase6_configuration_a_run_absorbed.md).

---

## Implementation steps

- [ ] Enumerate the derived values across the fleet's entrypoints and activities. The known set to start from, each verified against the tree rather than this list: the repository root; the component under plan; paths built from an already-contained path; the per-run worktree name; the pull-request number parsed back out of a URL; the set of papers a refresh run considers due.
- [ ] For each, record marker / algorithm / override / scope of effect. Where a value has no override, say so and say why — an absence stated is a decision, an absence unstated is an oversight.
- [ ] Rule requirement 3's trade in one sentence and write the ruling down: what the echo costs, which stream carries it, and what a parent may suppress.
- [ ] Move the echo onto the live path so the run that dispatches prints what it derived. Keep the `--dry-run` preview building its values through the same assembly the live run uses — a rehearsal that constructs its own copy previews something that is not what runs, and this family has shipped that bug once already.
- [ ] Publish the enumeration where a reader looks for it, and cross-reference it from the code that derives each value so the two cannot drift apart unnoticed.
- [ ] Add a test that a run's output names the component it derived. The echo is a producer; something must read it, or [Phase 4](phase4_producer_names_its_consumer.md)'s gate is the next thing to catch it.
- [ ] **Demonstrate requirement 5:** run against a deliberately wrong component path, capture the output verbatim, and confirm the derived value is named before any side effect. Record the transcript in this doc.
- [ ] Run the full suite and confirm nothing that depended on the quiet path broke.

---

## Runtime Verification

**Date:** 2026-08-18 · **Host:** `puma-workstation-mint` · **Runtime verified:** `git`, which is the marker every derivation in this phase anchors on.

The claim being verified is the one requirement 1 rests on: that `git rev-parse --show-toplevel` returns the repository root rather than the invocation directory, so the anchor is a fact and not a guess.

```
$ git --version
git version 2.43.0

$ cd scripts/workflows/temporal && pwd
/home/puma/Repos/claude-dot-files/.claude/worktrees/plan-feature-1787093087/scripts/workflows/temporal

$ git rev-parse --show-toplevel
/home/puma/Repos/claude-dot-files/.claude/worktrees/plan-feature-1787093087
```

**Observed:** invoked three directories down, git returned the worktree root, not the working directory. The marker property holds on this host at this version.

**Re-verify when this doc is substantially revised** — and note the second-order fact this output demonstrates: the root returned here is a **worktree** root, which is the correct answer for a dispatch and would be the wrong answer for a tool expecting the main checkout. That distinction belongs in requirement 4's scope-of-effect entry for this value.

---

## Notes and gotchas

- **The echo is not logging.** Logging is for the person diagnosing a failure; the echo is for the person about to spend an hour of model time on the wrong component. It goes where they will see it before the run commits to anything, which is why requirement 5 checks *before any side effect* rather than *somewhere in the transcript*.
- **`--dry-run` already does most of this well, and that is the trap.** Reading the dry-run block makes the echo look built. It is built in the one mode where nothing is at stake.
- **Do not use this phase to add validation.** Containment of operator-supplied paths is already handled one layer up, by a parser where declaring a repo path and checking it are the same act. This phase is about visibility, not safety; conflating them will produce a change that touches the security-relevant path for a legibility reason.
