# Phase 5 — What configuration a run absorbed

**Component:** [Workflow Decomposition](roadmap.md) · **Status:** not started · **Gate:** none live — the run bag this phase writes into shipped with [PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md)

## What this phase does

A dispatch reads its agents, its skills, its rules and its hooks from `~/.claude/` on the machine it runs on. Those files are symlinks into a repository, which is what makes them syncable — and it is also what makes them **editable mid-flight**. Someone adjusts a rule in an interactive session at 14:00, and every dispatch on that machine after 14:00 behaves differently from every dispatch before it. Nothing records the change, and no two machines can be *shown* to be running the same thing; they can only be assumed to be.

The roadmap's own gate for this problem already names the cheap half of the answer: *if the run bag records the config a run used, the divergence half shrinks to a reader.* **That gate is open.** The run bag exists and carries five `Journal-` tags today — the workflow key, the origin repo, its remote, its commit, and the worktree — and **none of them names the configuration the run absorbed.**

So this phase builds three things and deliberately stops: **one digest, one tag, one reader.** Record what configuration a run ran under; put it in that run's own bag beside the five facts already there; write the reader that answers *did these two runs use the same configuration*. Divergence detection then falls out as a question you ask of records that already exist, instead of a drift detector nobody has justified building.

**Terms used here.** A **bag** is one run's folder in the journal, never edited after the run ends. A **`Journal-` tag** is one line of that bag's metadata. A **digest** is a short value computed from the configuration's bytes, so two runs that absorbed the same configuration produce the same value and any difference changes it. The **managed tier** is a settings scope an operator controls and a session cannot override; the **user tier** is the one the person on that machine owns.

---

## Requirements for completion

1. **A run's bag records a digest of the configuration that run absorbed** — a sixth `Journal-` tag beside the five that exist. Written at the same point in the run the other five are, before the first side effect.
2. **What the digest covers is stated explicitly**, and what it deliberately excludes is stated by name. A digest whose inputs are unnamed cannot be reasoned about when two runs disagree, and cannot be recomputed by anyone checking it.
3. **A reader answers "did these two runs use the same configuration"** from bags alone — no network, no live filesystem read, no drift detector.
4. **The tag survives the bag's own rules.** A value is written once and never edited afterwards; a field with nothing to say records that it had nothing to say rather than being omitted. Verify against the bag's existing contract rather than inventing a convention for this one tag.
5. **Whether Claude Code's own Managed settings tier survives `--setting-sources` and `--safe-mode` is MEASURED** — declared, then tested against both flags, with the observed output recorded. **This requirement stays unchecked until the measurement exists, and nothing in this phase or any later one may be designed on the assumption that it passes.**

**Requirement 5 is an input to a decision this phase does not make.** The immunity property is an inference across three sources, one of them a rendered page, flagged by its own paper as unmeasured. It matters because the fleet's safety hook lives in user-scope settings, and a dispatch that narrows its setting sources strips the file the hook is declared in — the one control still operating during a headless run. Measuring it is cheap. Building on it unmeasured is not.

---

## Dependencies

- **[PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md)** — the run bag and its `Journal-` tags. **Complete**, so the roadmap's stated gate for this phase is already open.
- **[PMP Phase 3](../persistent-memory-protocol/phase3_the_emit_rule.md)** — not a gate, but read it before choosing where the digest is written: it owns the rule about what a failed journal write may and may not do silently.
- **No sibling component.** Managed configuration is **this** component's, in full — see below.

### Requirement 1's checkbox has two halves, and only one of them is built here

The pre-existing roadmap checkbox this phase carries promises two different things: *the fleet's set becomes managed; the user keeps a tier they own and can extend*, and the record that makes divergence visible. **They are not the same work.** Deciding which tier wins, and what a user's tier may override, is a policy design; recording what one dispatch absorbed is a fact.

**This was planned on 2026-08-18 as an open question — whether the tier design belonged to a sibling — and the operator ruled on 2026-08-19 that it does not.** Managed configuration belongs here, under decomposition, for the reason the sprint edit that placed it gave: `run-claude` already refuses to dispatch on an *inherited* model, and agents, skills, rules and hooks are the ambient inputs still outstanding. This is decomposition's own derive-not-inherit seam, finished. **There is no seam with another component to negotiate, and no scoping question left open.**

**What that ruling does NOT change is this phase's increment.** It builds the record and stops:

> **The tier half of requirement 1 stays UNCHECKED, and stays in this phase.** Not because it belongs elsewhere — it belongs here — but because **the precedence direction is a policy choice and the digest is what supplies the evidence for it.** Building the tier mechanism before the record exists is designing the thing this phase was created to inform, on the one question (§ *The precedence direction is a policy choice wearing technical clothes*) where the field itself runs two opposite ways. The record comes first; the tier is what the record is for.

The checkbox is carried verbatim because a planning run does not reword a completion criterion.

---

## What this phase decides

### Why one digest and not the rest

Seven systems ship a managed-plus-user configuration model, and the field's fuller answer includes provenance commands, typed drift diffs, and cross-machine agreement proofs. **None of those is justified yet, and the reason is not fleet size.**

**Say the reasoning precisely, because the obvious version of it is one this project has ruled out.** The problem statement is explicit that *nothing may assume a single operator* — a shortcut that works because one person runs everything is a shortcut that has to be removed later. So "there is one operator today, therefore defer" is **not** the argument, and a design here that reads that way is wrong.

The actual argument is about **which mechanism is load-bearing**: the digest is the primitive every one of those richer features would have to be built on, and none of them can be specified well before the digest shows what actually diverges in practice. Building the reader over recorded digests is the cheapest path to *knowing* rather than *guessing* — and it is the path that stays correct when the second machine arrives, because the record was there before it did.

**What that rules out for this phase, by name:** a provenance command, a typed drift diff, a cross-machine agreement proof, and any repair or reconciliation action. What it rules *in* later is all four — the deferral is until the digest supplies evidence, not indefinitely.

### The precedence direction is a policy choice wearing technical clothes

Of the shipping systems surveyed, the direction of precedence **runs both ways**. Vendor-package systems let the *local* tier win. Org-policy systems — including Claude Code's own Managed tier — let the *managed* tier win unconditionally, with no user override at all.

**Phase 5's stated intent is the first shape:** *the user keeps a tier they own and can extend.* A design that reaches for Claude Code's Managed tier because the word "managed" matches would silently adopt the second shape and **remove the very tier the checkbox promises the user.**

This is recorded here as a trap rather than as a decision, because the decision is the operator call above. What this phase must not do is make it by accident through a mechanism choice.

### The digest's inputs are the hard part, and they are not "hash the directory"

`~/.claude/` holds machine-local state — credentials, sessions, caches, per-project data — alongside the synced configuration. A digest over the whole tree changes on every run and answers nothing. A digest over the synced set answers the question, and **the synced set is already enumerated**: it is what the installer links, and there are seven of those targets. Requirement 2 exists so that whichever set is chosen is written down beside the tag, rather than being recoverable only by reading the function that computed it — which is the same property [Phase 4](phase4_nothing_invisible.md) is establishing for every other derived value in the fleet.

---

## Implementation steps

- [ ] Read the run bag's contract for how a tag is written, what a field with nothing to say records, and what may never be edited after a run ends. Do not invent a convention for this tag.
- [ ] Decide and write down the digest's inputs and exclusions, against the installer's synced set rather than the whole of `~/.claude/`.
- [ ] Compute the digest and write the sixth `Journal-` tag, at the same point in the run the existing five are written — before the first side effect.
- [ ] Verify a run with no readable configuration still produces a bag, and records *that* rather than omitting the tag.
- [ ] Write the reader that compares the digests of two bags and reports same-or-different, with no network and no live filesystem read.
- [ ] Name the reader as the digest's consumer wherever [Phase 4](phase4_nothing_invisible.md)'s gate expects it — this phase pairs its producer with its consumer deliberately, and that pairing should be visible rather than incidental.
- [ ] Verify the reader against two real bags produced by two runs with a deliberate configuration change between them, and record what it reported.
- [ ] **Requirement 5, and it is independent of everything above:** declare the safety hook in Claude Code's Managed settings tier and test it against `--setting-sources` and `--safe-mode` separately. Record both outputs verbatim in the § Runtime Verification section below. **Do not build on the result in this phase** — the measurement is the deliverable.
- [ ] Re-read § Runtime Verification against the installed CLI version at build time and refresh it if the version moved.
- [ ] Run the full suite.

---

## Runtime Verification

**Date:** 2026-08-18 · **Host:** `puma-workstation-mint` · **Runtime verified:** the Claude Code CLI, which is the external runtime whose settings behaviour requirement 5 turns on.

```
$ claude --version
2.1.235 (Claude Code)

$ claude --help | grep -A2 -- "--setting-sources"
  --setting-sources <sources>           Comma-separated list of setting sources
                                        to load (user, project, local).

$ claude --help | grep -A5 -- "--safe-mode"
  --safe-mode                           Start with all customizations
                                        (CLAUDE.md, skills, plugins, hooks, MCP
                                        servers, custom commands and agents,
                                        output styles, workflows, custom themes,
                                        keybindings, and more) disabled — useful
                                        for troubleshooting a broken
```

**Three things observed, and the third is the one that matters:**

1. **`--setting-sources` names exactly three selectable sources: `user`, `project`, `local`.** A managed source is **not** in that list on this version.
2. **`--safe-mode` disables hooks by name**, among the rest of the customization surface.
3. **Observation 1 does not settle requirement 5 in either direction, and must not be read as if it did.** A managed tier absent from the selectable list is equally consistent with *it is always loaded and therefore immune* and with *it is not a source this version has*. That ambiguity is precisely why requirement 5 is a measurement — declare the hook there and observe — rather than a documentation read.

**Why this section exists at all:** the fleet's safety hook is declared at user scope, and a dispatch narrowing its sources to `project,local` would strip the file the hook lives in. That is the only control still operating during a headless run, and a guard already exists asserting no runner does it — see `test_no_runner_STRIPS_the_settings_file_the_safety_hook_lives_in` under `testing/config-hooks/`. Requirement 5 asks whether a different tier would make that guard unnecessary; until it is measured, the guard is what holds.

**Re-verify before the build dispatch fires.** The CLI moves faster than this document, and both flags above are exactly the kind of surface that gains or loses a value between releases.

---

## Notes and gotchas

- **The digest answers "were these the same", never "which one was right".** Two runs disagreeing is a fact; which configuration should have been in force is a policy question this phase does not own.
- **Do not reach for Claude Code's Managed tier because the name matches.** Its precedence model is unconditional-managed-wins, which is the opposite of what this phase's own checkbox promises the user.
- **The bag is append-only by design.** A digest recorded at the start of a run describes what the run absorbed at that moment; if configuration changed mid-run, that is a separate finding and not a reason to rewrite the tag.
- **This phase is the strongest argument for [Phase 4](phase4_nothing_invisible.md), and it also dodges it** — it ships its consumer in the same phase as its producer. That is the correct shape and it is exactly why the gate is needed for the pairings that are not planned together.
