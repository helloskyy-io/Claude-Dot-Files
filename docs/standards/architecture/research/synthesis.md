# Synthesis — product-level research

**Cycle:** 2026-08-03 · **Pool:** 11 papers · **Tier:** Large / architecture-layer · **This cycle added 3**

Read this instead of the pool. It says what the evidence means for the product's direction and ends in reviewable candidates. Nothing here is binding — research is evidence, and a finding becomes a rule only by being codified into a standard through human review.

## Inputs

| Paper | Last validated | Revalidate | Critic verdict | Status |
|---|---|---|---|---|
| `raw/convergence_stopping.md` | 2026-08-03 | high — 6 weeks | **PASS** (2 correction rounds: 4 non-verbatim quotes incl. one invented phrase; 4 confidence downgrades) | current |
| `raw/workflow_reuse_boundary.md` | 2026-08-03 | high — 6 weeks | **PASS-WITH-FIXES** (re-sourced the ClusterTask→cluster-resolver claim to a source that states it; 2 quote-fidelity fixes) | current |
| `raw/python_sdk_long_activities.md` | 2026-08-03 | high — 4 weeks | **PASS-WITH-FIXES** (un-quoted an inference-from-absence dressed as a quote; 1 confidence re-mark; retagged an out-of-contract confidence class) | current |
| `raw/durable_execution.md` | 2026-07-27 | low — 6 months | PASS | current |
| `raw/hierarchical_agents.md` | 2026-07-25 | medium — 3 months | PASS | current |
| `raw/reflection_literature.md` | 2026-07-23 | medium — 3 months | PASS | current |
| `raw/production_cases.md` | 2026-07-23 | medium — 3 months | PASS | current |
| `raw/temporal.md` | 2026-07-04 | high — 4 weeks | PASS | ⚠️ **PAST WINDOW** |
| `raw/claude_code_integration_surface.md` | 2026-07-25 | high — 4 weeks | PASS | ⚠️ **PAST WINDOW** |
| `raw/anthropic_tos_and_enterprise.md` | 2026-07-24 | high — 4 weeks | PASS | ⚠️ **PAST WINDOW** |
| `raw/hook_sourcing_supplement.md` | 2026-07-25 | high — 4 weeks | PASS | ⚠️ **PAST WINDOW** |

**Currency warning (§5).** Four inputs are past their revalidation window as of today and are **flagged, not trusted** — a consumer treats their claims as unverified until `research-refresh.sh` runs. All four are the high-volatility vendor-surface papers, which is the tier behaving exactly as designed. Nothing in this synthesis's candidates rests on an unrefreshed claim from those four *alone*; where one is cited below, the candidate is marked.

**No papers were retired this cycle.** Every subject still has a live destination in `docs/development/roadmap.md`. See `topics.md` for the per-paper reasoning.

## What the pool now establishes

### 1. The stopping rule shipped in `revision.sh` rests on evidence that does not exist

This is the cycle's most consequential finding and it corrects something already in production.

`revision.sh` caps its correction loop at one loop-back and justifies it in a comment: *"self-correction plateaus at ~3–5 passes."* `convergence_stopping.md` audited that figure's provenance and found **no study describing a loop whose passes are separate processes with separate contexts**. The two studies producing a "3–5"-shaped number both run one actor in one context *and truncate their own sweep at the plateau they report* — Self-Refine caps at 4 iterations by construction, Nexus sweeps 0–5. A study that stops at 4 cannot observe pass 6. Worse, the field's own critical survey (Kamoi, TACL) explicitly excludes cross-actor correction from its negative results as *"unsuitable for evaluating whether LLMs can improve their own initial responses"*, and a large share of published iteration guidance was measured under an **oracle stopping rule** — Huang et al. state outright that they used the correct label to decide when to stop, which no deployment has.

The positive evidence points the other way. The closest published analogue to our topology — a nine-round fresh-agent audit — reports per-round yields of **15, 8, 12, 2, 8, 1, 4, 1, 0** and names the pattern *"non-monotonic convergence"*. A "stop when yield drops" rule fires at round 4 and forfeits 14 defects. Independently: single-pass review recall is measured at **~22–27%**, and aggregating ten independent passes improved F1 by **43.67%**. A plateau claim needs recall near 100%; ours is nowhere near it.

**This corroborates the operator's own correction** in `phases/burn-test-intake-2026-08-02.md`, which rejected the extrapolation from n=1 measured evidence (PR #233: three passes, new verified work each time). The literature now says the same thing from the other direction — not "three is the number," but "the number you have has no source."

**The honest boundary is real and cuts against acting hastily.** Böhme (FSE'21) shows naive "nothing new lately" estimators *"systematically and substantially under-estimate the true risk"*; Porter et al. (TOSEM 1998) — the best-powered human analogue — found team size and session count *did not significantly influence* defect detection rate. And a derived finding with teeth: a reviewer with a non-zero hallucination rate never emits an empty pass, so "stop on zero findings" would fall through to its backstop every time. **Every surveyed production framework pairs its primary stopping rule with a hard count or budget backstop.** Convergence stopping has been measured against a fixed cap exactly once — it won on cost at parity quality (−38% tokens), but its *judge-gated* variant cost **+129%**.

### 2. Where the workflow shelf's "library" premise holds, and where it is folklore

`workflow_reuse_boundary.md` tests candidate #4 from the prior cycle — that the shared workflow library, not any individual workflow, is the first-class artifact.

The premise survives, but not in the form DRY suggests. **Copy-and-adapt is the dominant creation mechanism even where a first-class reuse mechanism exists**: 62.5% of practitioners at least frequently copy parts of their own workflows, and 28.2% never use their own reusable workflows. The stated reasons are **control (43.0%) and convenience (40.3%)**, not ignorance (unawareness 20.0%, lack of trust 4.3%). A library that loses on control and convenience gets bypassed by informed engineers — that is the design constraint, and it is measured, not asserted.

What every surveyed system deprecated is instructive: **general-purpose parameterization layers**. Tekton removed `PipelineResources` for opacity, undebuggability, covering only a "tiny subset", and *reducing* reusability; Argo deprecated template-level `templateRef` for letting a definition also be an instantiator — *"problematic and dangerous"*. What replaced them is **explicit, typed, versioned reference**. Kubernetes' own design proposal is the corpus's genuine dissent, arguing *against* parameterizing everything and *for* fork-plus-overlay with fork *management tooling*.

**Two findings change how the pending ruling should be made.** First, **no numeric threshold for "too many parameters" is documented anywhere** — it is folklore, stated as a negative finding with search method. Any threshold this repo adopts must be labelled a local invention; it cannot cite the field. Second, and sharper: **the field's discriminator is expected future co-evolution, not textual overlap.** Kapser & Godfrey partition clones by intent about future evolution — Forking, Templating, and *Customization* (a requirements difference, so a behaviour decision that must be settled *before* the structural one). Copied-from-ness is presupposed by all four categories and therefore cannot discriminate. This means the measured 82%/9% overlap figures in the burn-test intake are **not sufficient input** to the ruling in either direction; the test is "when one changed, did the other need the same change?", and that evidence lives in commit history, not in a diff. A third structural option also exists and the two-way framing hides it: **tracked lineage with mechanical propagation** (Copier's answers-file + three-way update).

Divergence has a measured cost — ~52% of clone groups go inconsistent, ~28% of those unintentionally, and roughly every second-to-third unintentional inconsistency is a fault. **Caveat stated by the paper and carried here: no study measures this for CI/workflow definitions specifically, and nothing in the corpus studies duplicated prompt prose**, which is much of what our near-copies actually are.

### 3. The Temporal port's two known unknowns are now knowns — and the answer is not the obvious one

`python_sdk_long_activities.md` closes the roadmap's unchecked milestone *"Confirm the two known SDK constraints."* Version-anchored to `temporalio` 1.31.0 / server `main` @ 2026-08-03.

**A 10–60 minute activity is an ordinary, supported shape** — no documented ceiling on `start_to_close_timeout` was found, and heartbeating is effectively free (throttled to min(0.8 × `heartbeat_timeout`, 60 s)). Payload numbers are hard and knowable: 2 MiB/payload, 4 MB/gRPC message, 50 MiB and 51,200 events/history, 4 KiB/activity failure. The paper's recommendation on transcripts is **not** to reach for External Storage: GitHub plus repo-local files is already our claim check, so the result carries pointers, not copies.

**The non-obvious finding is that the naive shape cannot work.** A synchronous `def` activity blocked in `subprocess.wait()` can neither heartbeat itself nor receive cancellation. The chain is sourced link by link: the SDK delivers threaded cancellation via `Runtime._raise_in_thread` → the Rust bridge calls `PyThreadState_SetAsyncExc` → CPython's own docs state this *"does not necessarily interrupt system calls."* The recommended shape is an **async** activity over `asyncio.create_subprocess_exec`, heartbeating per `stream-json` line. Two operational teeth: `graceful_shutdown_timeout` **defaults to zero**, and the SDK README warns shutdown *"may never complete"* if an activity ignores cancellation — so a blocked sync activity hangs `systemctl stop` for the rest of the run.

**Three honest limits, all load-bearing.** (a) **No first-party sample of a Temporal Python activity wrapping a subprocess exists** — the recommended shape is the paper's composition of documented parts and must be treated as a design hypothesis until tested. (b) **Child-process orphaning on worker death is undocumented across every Temporal SDK**; systemd's cgroup kill covers `systemctl stop` but not `kill -9` or a worker-only OOM. (c) **The retry economics are bad and no heartbeat fixes them** — an activity is the unit of retry, so a failure at minute 55 re-executes the whole run, re-entering a repo a previous attempt already mutated. If expected failure rate × 60-minute re-run cost exceeds the cost of decomposition, the single-activity shape is wrong however well it heartbeats. Whether an agentic `claude -p` run decomposes into resumable per-turn legs is **not a Temporal question** and is not settled anywhere in this pool.

### 4. Carried forward from the prior cycle, unchanged

Durable execution remains the argued substrate for durability and resumability — *not* for composition, which already works in bash. Edge-held subscription authentication remains viable by construction under Anthropic's published policy ⚠️(rests on a past-window paper). The separation of the run that authors from the run that judges remains supported by the hierarchical-agent and reflection literature — and is now additionally load-bearing, since §1 above shows the *cost* of that separation (extra passes) is not bounded by the plateau argument that was used to bound it. The `--setting-sources` safety blocker remains untested ⚠️(past-window paper), and it is the one item where the roadmap and the pool agree the next step is an experiment, not more reading.

## A stale destination, worth naming

`docs/standards/architecture/system-overview.md` was **excluded from this cycle's sizing as substantively stale**, and that exclusion is itself a finding. It still describes orchestration as "bash-over-Python" monoliths and contains no mention of parent/child workflows, the activities layer, the disposition engine, or the Python decision. It was moved under `standards/architecture/` on 2026-08-03 without its content being revisited. A stale architecture overview at this altitude is worse than an absent one: it reads as authority. Flagged here because sizing product-level research against it would have measured a system that no longer exists — a future cycle will hit the same trap.

## Action candidates

Reviewable items, sized for a standup. Nothing is ratified. Per §7, this run surfaces candidates and writes nothing outside `research/` — routing is the reviewer's and the operator's.

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Remove the "plateaus at 3–5 passes" justification from `revision.sh`.** The claim has no source describing our topology. This is a *provenance* correction, not a request to change the loop bound — the bound may still be right for cost reasons, but it must be justified by budget, not by a citation that does not exist | change direction | `convergence_stopping.md` |
| 2 | **Do not adopt a bare "stop when a pass finds nothing" rule.** Three independent findings kill it: non-monotonic yield (a quiet round is followed by productive ones), Böhme's adaptive-bias result, and the derived point that a hallucinating reviewer never emits an empty pass. Any convergence rule needs a hard count or budget backstop — which every surveyed production framework has | no change | `convergence_stopping.md` |
| 3 | **Treat the 82%/9% overlap figures as insufficient input to the fork-vs-parameterize ruling.** The field's test is expected future co-evolution — "when one changed, did the other need the same change?" — answerable from commit history, not from a diff. Also put a third option on the table the current framing hides: tracked lineage with mechanical propagation | change direction | `workflow_reuse_boundary.md` |
| 4 | **Any parameter-count threshold we adopt must be labelled a local invention.** No numeric threshold is documented anywhere in the surveyed corpus. Adopting one is fine; citing the field for it is not | adopt | `workflow_reuse_boundary.md` |
| 5 | **Design the `claude_cli` activity as async-over-`asyncio.create_subprocess_exec`, not as a sync `def`.** The sync shape cannot heartbeat or be cancelled while blocked, and `graceful_shutdown_timeout` defaulting to zero makes that an operational hazard, not a theoretical one | adopt | `python_sdk_long_activities.md` |
| 6 | **Carry transcripts as pointers into GitHub, not as payloads.** Do not reach for External Storage; the claim-check tier already exists | adopt | `python_sdk_long_activities.md` |
| 7 | **Open the question of whether a `claude -p` run decomposes into resumable per-turn legs.** It is the fork between the single-activity and child-workflow shapes, it is not a Temporal question, and no paper in the pool covers it. Named as a topic candidate for the next cycle in `topics.md` | new concept | `python_sdk_long_activities.md` §8 |
| 8 | **Rewrite `temporal.md` at its next refresh rather than diffing it.** It is pre-standard prose carrying a `Critic: PASS` its content does not support, it is past window, and its one stated gap (heartbeat + payload limits against our shape) is now closed by `python_sdk_long_activities.md`. This is a *quality* judgement, not a retirement — the subject is alive | change direction | `temporal.md`, `python_sdk_long_activities.md` |
| 9 | **Refresh the four past-window papers before the next planning run consumes them.** `temporal.md`, `claude_code_integration_surface.md`, `anthropic_tos_and_enterprise.md`, `hook_sourcing_supplement.md`. §5's planning-stage fail-fast will otherwise stop that run | no change | the four papers' headers |
| 10 | **Revisit `system-overview.md`, or mark it stale in place.** It describes a system that no longer exists and reads as authority | change direction | this synthesis, § *A stale destination* |

### Trace: what candidate #1 touches

Per §4, a corrected fact enumerates **every** dependent, not the most visible one. The "3–5 passes" claim reaches:

1. `scripts/workflows/revision.sh` — the comment block at lines 21–26, and the loop-bound rationale at 309–325. **The claim's origin.**
2. `docs/development/phases/burn-test-intake-2026-08-02.md` § *Recorded: the plateau correction* — already correct; this cycle adds external corroboration, so it needs no change, only the citation.
3. `docs/development/roadmap.md` § *Phase: Memory Management Framework* — the **Convergence-based stopping** milestone, whose framing ("stop when a pass produces no new confirmed findings") is precisely the bare rule candidate #2 says not to adopt unbacked.
4. `docs/development/roadmap.md` § *Phase: Autonomous Operation* — *"'stop' has to be a state something can observe, not a turn count"*, which this evidence supports in direction while denying it the cheap implementation.
5. Any other workflow that inherited a loop bound by copying `revision.sh`'s rationale. **This is unenumerated and I did not verify it** — the reviewer should check, because the copy-and-adapt finding in §2 makes silent propagation the expected case rather than the unlikely one.

## Homeless findings

Named here rather than parked elsewhere, per §7 — a homeless finding means the surface is missing, and the reviewer disposes of it.

- **A defined shape for production feedback.** Carried from the prior cycle and still homeless. Operator and burn-test findings have driven more workflow fixes than log analysis has. One instance now exists as a dated intake record (`phases/burn-test-intake-2026-08-02.md`), which is better than nothing, but a dated one-off is not a channel: nothing says where the *next* one goes, and `review-runs.sh` sweeps logs while the reflection channel is read opportunistically. The CPI phase names the sibling gap for reflections; neither has a surface that owns operator findings.

- **Research Standard §3 has no confidence class for an authoritative speaker in an informal artifact.** The four classes (definitive / directional / unverified / derived) conflate two independent axes — how authoritative the speaker is, and how formal the artifact is. A named Temporal maintainer answering on Temporal's own forum currently gets the same tag as an anonymous blog comment. `python_sdk_long_activities.md` hit this, invented a fifth tag (`corroborated`), and was correctly made to retract it. This is homeless *for us specifically*: the Research Standard is **vendored MIRROR** from `MDC-Master-Planning`, so it cannot be amended here — the amendment goes upstream and is then re-vendored, and this repo has no surface that holds "an upstream standards amendment we owe." Nothing in that paper rides on the difference, so this is a process gap, not an evidence gap.

## Gaps this cycle did not cover

- **Inter-process handoff contracts — redirected, not deferred.** The prior cycle named this a product-level gap. That was an altitude error: this folder's own `README.md` uses this exact question as its worked example of a *phase-level* one. It belongs in `docs/development/phases/memory-management-framework/research/`, which does not exist because the phase doc is unwritten. It remains the highest-value open research on the queue — the burn-test intake says so and flags its own prior art as an unverified lead. **`convergence_stopping.md` deepens the dependency:** its finding P11 establishes that the mechanizable convergence classes require typed, comparable outputs. Without the handoff contract, convergence detection collapses to semantic distance over prose, which measures drift rather than discovery — the wrong quantity.
- **Decide-only disposition — does a judging stage with no authoring authority actually reduce defects?** Per-cycle cap; first in line next cycle. It validates the central claim of `workflow-scripts.md § Composition`.
- **Whether an agentic `claude -p` run decomposes into resumable per-turn legs.** Surfaced by this cycle (candidate #7); no paper covers it.
- **Duplicated prompt *prose*.** Every quantified source in `workflow_reuse_boundary.md` concerns code or config. If our near-copies differ mainly in prompt text, none of the clone-fault evidence transfers. There appears to be no literature; that is itself a finding worth a topic.
- **Reflection-channel mining** and **bash → Python Stage A conversion** — both phase-level; see `topics.md`.
