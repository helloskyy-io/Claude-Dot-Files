# Burn-test intake — 2026-08-02

**Status:** intake record. Nothing started, nothing planned.
**Source:** PM3 burn-test handoff (`/tmp/claude-cdf-handoff-three-items-20260802.md`) + one CDF-originated item

## What this document is

The raw items surfaced from live operation of the newly-decomposed workflow fleet, with their evidence, confidence levels and dependencies. **It is an intake record, not a plan** — each item still needs its own pass through the process before it becomes work, and the planning artifacts will be separate documents.

The items feed **three** roadmap sections, which is only clear once they are split apart:

| Item below | Roadmap section |
|---|---|
| 1 — Result envelope + `is_error` gating | **Memory Management Framework** (kind 2, the transport layer) |
| 2 — Fork vs parameterize → `build-phase` | **Workflow Decomposition** |
| 3 — Server-side agent definitions | **Autonomous Operation** |
| 4 — Handoff contract → convergence stopping | **Memory Management Framework** (kind 2, the payload layer) |
| `lint-docs.sh` | **Workflow Decomposition** |

Items 1 and 4 read as separate concerns here because that is how they arrived. They are **the same problem at two layers** — how a parent learns what a child concluded — which is why they belong to one framework rather than two queue entries.

## The process every item goes through

```
research  →  standards  →  planning  →  building  →  reflection/testing  →  validation
```

**We had been skipping the first two.** The last two months produced parent/child composition, a three-layer split, completion contracts and routing tokens — all built first and documented after, with nothing binding written down. None of this starts until the standards catch-up is done, because two of these items produce rulings that need somewhere binding to live.

**The one exception:** if an item genuinely does not warrant the full pass, we talk it through and build it together. Item 1 is the likely candidate. Taking the exception is a decision made explicitly, not a default.

**Standards are human-in-the-loop.** Drafts are prepared in the interactive session and approved by the operator before merge. No autonomous dispatch writes a standard.

---

## Item 1 — Read the result envelope; gate on `is_error`

**Problem.** Parents recover routing tokens by grepping a child's whole log — 307 lines scraped for one token on a measured run. `tail -1` is a heuristic: a run mentioning another PR URL after creating its own silently hands the parent the wrong one, and unlike the verdict channel, the URL channel has **no fail-safe**.

**Worse, and the reason this is a correctness item rather than an efficiency one:** the last line of a `stream-json` log is already a structured result envelope carrying `is_error`, `subtype`, `terminal_reason`. **The parent gates on none of them.** A child can return `is_error: true` and the parent greps on regardless.

**Known.** The envelope exists and `tail -1 | jq -r .result` replaces the scrape.
**Unverified.** Field availability was not confirmed against a real log — no JSONL on the CDF box. **Check this where runs actually happen before designing anything.**

**Confidence:** high. **Likely the exception case** — small, self-contained, no new concepts.
**Blocks:** nothing. **Blocked by:** nothing.

---

## Item 2 — Fork vs parameterize, then `build-phase` decomposition

**This is the highest-leverage ruling in the queue and it gates Item 4's sibling work.** If `build-phase` gets its own `build-draft` + `build-refine` by copy-and-edit, we go from two near-copy families to three and the shelf stops being a library.

**PM3 reported ~398 differing lines for both pairs. Measured, they are not alike:**

| pair | differing | of | shared |
|---|---|---|---|
| `revision-draft` vs `-minor` | 398 | 438 | ~9% |
| `revision-refine` vs `-minor` | 90 | 507 | ~82% |

**The difference is lineage, and it splits the ruling in two:**

- **Refines — the parameterize case.** `revision-refine-minor` was copied from `revision-refine` and scaled down. The diff is agent list, turn budget, names — all already-externalized patterns (`MODEL_KEY` → `config.yaml`). One child with a lens/sizing input is the obvious shape.
- **Drafts — not forks of each other.** `revision-draft-minor` is the old monolithic `revision-minor.sh`: different stages, no checkpoint commit, no gitignore-collision check. Collapsing them is a **behaviour decision** (should the minor tier gain checkpoint commits?), not a deduplication.

PM3's stale-usage-text find (`revision-draft-minor.sh:19` still reads `./revision-minor.sh "description..."`) is real, but it is evidence of an incomplete `git mv`, not of N-way propagation failure.

**Then, gated on that ruling:** does `revision`'s draft/refine shape actually fit `build`, or does it only look like it? `build` implements from a plan document, so it carries a **plan-conformance obligation** revision does not — *"did we build what the doc said, and where we deviated, is the deviation defensible?"* That may be a distinct child, a stage inside refine, or nothing. **It needs `build-phase.sh`'s stages read against the two refines before anyone commits.** A live option the investigation must be allowed to reach: `build` as a third *caller* of existing children rather than a new family.

**Free regardless:** `review-pr` takes `--pr` and `--repo` and contains nothing revision-specific. `build-phase` gains the whole disposition ritual and the `VERDICT` routing contract by becoming a parent, with no new child written.

**Confidence:** high that the ruling is needed. **Full process** — the fit investigation is research.
**Blocks:** any `build-phase` decomposition. **Blocked by:** standards catch-up.

---

## Item 3 — Server-side agent definitions

**Problem, on the existing rule's own terms.** `activities/run-claude.sh` fails loud rather than dispatch on an inherited model, and states why: *"model identity must be an explicit input, never derived."* By that same rule, **the agent roster a dispatch can reach is ambient and underived** — a headless run loads whatever `user` settings the edge machine happens to have, and nothing detects divergence between two machines.

**Known.** Both CLI flags exist and were verified: `--agents <json>` injects definitions at invocation (no path lookup, the agent need not exist on the box); `--setting-sources <sources>` controls which setting tiers load. `run-claude.sh` passes neither today.

**Unverified.** `--agents` takes inline JSON and our agent prompts are large. Whether that is comfortable at our sizes, or wants a generated-file pattern, **must be tested before the design assumes it.**

**Explicitly out of scope — operator ruling, and it is correct.** Agent-as-independent-durable-unit (Tier 3) is the canonical answer for a *metered API* integration, not for a subscription-based CLI overlay. It would require the CLI baked into worker images and a credential per pod. **Do not build it.** The accepted trade: agents stay inside Claude Code's process model, so they are not independently retryable, and the parallel-narrow-then-sequential-integration pattern stays enforced by prompt discipline rather than structure. Known limit, not an oversight.

**Confidence:** high that the gap is real; untested on prompt size. **Full process, small build.**
**Blocks:** nothing. **Blocked by:** standards catch-up.

---

## Item 4 — The inter-process handoff contract

**The item that most needs real research, and PM3 says so explicitly.** Confident about the problem; only suggestive about the answer.

**Problem.** The routing signal carries no payload. `HOLD - redispatch` tells the parent *to* loop but not *with what*, so the loop re-runs refine on the original task and trusts it to re-read the PR comment. **The parent routes blind** — while `review-pr` already writes a rich `pr_review:` YAML block (findings, per-item `hold_kind`, a ready-to-fire `dispatch_context`) that `/standup` parses and the parent does not. The structured channel exists and is half-wired.

**First-look prior art (one interactive session, NOT a `research.sh` run, NOT through `research-critic`, NOT against the Research Standard's source floor — treat as a lead):** GitHub Actions **deprecated** stdout-based output passing (`set-output` → `$GITHUB_OUTPUT`), citing parsing the output stream as a security risk. Argo Workflows uses `valueFrom: {path:}` and documents the distinction directly — keep useful logs while exporting only specific JSON. Tekton uses the same write-to-declared-path shape and is instructive for its **4096-byte cap**: someone tried to make this channel carry everything and hit a wall, and their guidance is to pass a *reference*, not a payload. A2A's task-state enum validates that a closed state vocabulary is right for routing, but its transport is JSON-RPC over HTTP for networked cross-vendor agents — **right idea about state, wrong layer** for a parent shelling out to a child on the same box.

**Convergent sentence:** the producer writes structured output to a path the caller declares; the caller reads the file; the log stays a log.

**Two design properties worth carrying into the research:** an absent or malformed result must fail safe to `needs-assistance` — this matters more for us than for any surveyed CI system, because **our producer is an LLM that can emit a plausible-looking but wrong result**, an assumption none of them defend against. And GitHub stays the durable memory tier; the result file carries **pointers into it, not copies** (Tekton's lesson).

**Downstream of this:** a **convergence-based** stopping condition — "stop when a pass produces no new confirmed findings" — becomes mechanizable, because "did this pass find something not in the previous pass's result?" is answerable against two typed payloads and not against two prose logs. See the plateau correction below.

**Confidence:** high on the problem, **suggestive only on the answer**.
**Full process, research first.** **Blocked by:** standards catch-up.

---

## Also queued (small)

**`lint-docs.sh`** — a companion gate: fail when a script exists that no doc names, or when a doc states a turn count its script disagrees with. Two stale-doc classes shipped this week (the research family absent from `workflows.md`, a two-child diagram after the third child landed) and both were caught by eye rather than by gate. Same class as the `MODEL_KEY` check in `lint-prompts.sh`. Exception-case candidate.

---

## Recorded: the plateau correction

Round 3 justified the one-loop-back bound with "self-correction plateaus at 3–5 passes." **That was a bad extrapolation and the operator caught it.** The finding describes a single long-running process where the writer is also the reviewer and also the corrector — one actor, one context, one set of blind spots. Our pipeline has separate processes, separate contexts, and critically **separate stakes**.

Measured against PR #233: pass 1 dispositioned 31 items (its sweep capped by an unverified absence claim); **pass 2 found two NEW live credential leaks** pass 1 could not have reached; pass 3 closed the class from the opposite direction and returned MERGE. **No plateau within three cycles** — every cycle produced new, verified work. A cap at 1 would have left two live credential exits in `main`.

**What is claimed:** on this system, up to three cycles remained productive. **What is not claimed:** that three is the number. n=1, one PR, one repo, a security-sweep-shaped task. It becomes a hypothesis worth encoding **only if production use repeats it.**

**The design implication we do hold:** the stopping condition should be **convergence-based, not count-based**. A counter set to 1 stops early; a counter set to 5 burns two passes elsewhere. That depends on Item 4.

**Load-bearing prompt behaviour, do not trim:** pass 3 did not repeat pass 2's search — *"I re-swept from the opposite direction… rather than repeating the message-shape grep that found the first five."* That is what closes a class rather than a finding.

---

## Suggested order (across all three roadmap sections)

| | Item | Why here |
|---|---|---|
| 0 | **Standards catch-up** | Two items below produce rulings needing a binding home |
| 1 | Result envelope + `is_error` gating | Correctness gap, smallest, likely the exception |
| 2 | Fork-vs-parameterize ruling → build-phase fit | Unblocks the next decomposition; prevents a third copy family |
| 3 | Server-side agent definitions | Real gap, small build, needs a prompt-size test first |
| 4 | Handoff contract (research) → convergence stopping | Largest; the convergence work depends on it |
| — | `lint-docs.sh` | Whenever |
