# Synthesis — Memory Management Framework

**Cycle:** 1 (2026-08-06) · **Pool:** 2 papers · **Tier:** Small (§2: 1–2 topics) · **Status: verified — both pool papers are through the critic gate, and so is this document.**

> ### What verification actually happened, stated exactly
>
> Both input papers were read by an **independent read-only critic** in a fresh context, which re-fetched every citation and checked every quoted span against its source. The findings were applied by each paper's analyst, and **each repaired span was re-verified against its source before the finding was reported closed** (Research Standard §3: a repaired span is a new claim). Both papers now carry `Critic: PASS-WITH-FIXES — 2026-08-06` in their own headers, with the fixes enumerated there — see the Inputs table below.
>
> **This synthesis went through the same gate** and was corrected in the same pass. Five defects were found here and fixed: **one span presented as a quotation that was not character-exact** (the A2A phrase in §11); **one table row recording a disagreement that does not exist** (§11 — a first look was credited with a claim it never made); **one conflation of two distinct Argo mechanisms** (§11, traced into `topics.md` as well); **one false section locator** (Escalations); and **one wrong pool count** ("0 of 0", now enumerated). One further span was hardened rather than corrected: §7's SWE-Bench+ figure was a bolded near-verbatim paraphrase sitting next to the word "reports" — not a quotation, so not a §3 breach, but close enough to be lifted as one downstream, and it is now the character-exact sentence. Every replacement was re-verified against its source: the unabridged arXiv Atom API for the two abstracts, and a direct read for each local document.
>
> **What this does NOT mean.** Verification checked that sources exist and that claims match them. It did not re-run the research, and it does not upgrade any claim's confidence tier: the *derived* and *directional* marks in the source papers still bound what may be relied on.

Read this instead of the pool. It answers three questions the sprint item asked — *how do we get both memory layers cleanly, what do other organisations actually use, and what does our LLM-producer constraint change* — and ends in candidates a standup can rule on. **Nothing here is binding.** Research is evidence; a finding becomes a rule only by being codified into a standard through human review.

---

## Inputs

**This pool.** Both written this cycle, both verified this cycle. Verdicts and "what was fixed" are transcribed from each paper's own `Critic:` header line — the authoritative record for them.

| Paper | Last validated | Revalidate | Critic verdict — and what was fixed |
|---|---|---|---|
| [`raw/dual_channel_outcome_records.md`](raw/dual_channel_outcome_records.md) | 2026-08-06 | medium — 3 months | **PASS-WITH-FIXES**. Every source re-fetched and every quoted span checked at byte level — 26 external sources, 3 sibling-paper citations, 4 local-script citations — with **no fabricated source, no miscitation, no confidence inflation**. Two **counts** were wrong and were corrected: the §7.1 gap count (read "six", enumerates to **seven**), and N7's Argo occurrence count and characterisation (read "four … all table rows", enumerates to **five**, of which three are table rows) |
| [`raw/non_model_observables.md`](raw/non_model_observables.md) | 2026-08-06 | high — 6 weeks (mixed-volatility; the slow §§ are marked skippable in the paper) | **PASS-WITH-FIXES**. Every URL resolved, every quoted span matched on re-fetch, every count re-enumerated and stood. Five fixes: **(1) N4 was a fabricated gap and is withdrawn** — GitLab's per-value `when` prose does exist first-party, and §2.1 now carries the semantics as a reduced-confidence paraphrase; (2) the `system/api_retry` `error` enum was miscited to `claude_code_integration_surface.md` §7 — it is enumerated in that paper's **§5** and applied in its **§8**; (3) the header's arXiv-quotation warrant was widened from [S30] alone to all seven quoted preprints, which the body was already relying on; (4) a Tekton quote had silently dropped the source's markdown link markup — restored; (5) the stated preprint range "2022–2026" was wrong — enumerating each paper's `<published>` field gives **2021–2024** |

**No paper in this pool is retired**, so none is excluded here. **0 of 2 papers are past a revalidation window** — the pool directory enumerates to exactly two papers (the two rows above), both carrying `Last validated: 2026-08-06` against windows of 3 months and 6 weeks respectively, so both are inside. *(A "0 of 0" reading produced by the dispatch-time currency check was a tooling artifact — it scanned the main-repo path, where this branch's files do not exist yet. The count above is from enumerating the directory.)*

**Upstream product-pool papers cited, never re-derived.** Dates and verdicts are taken from each paper's own header block — the most authoritative source for them.

| Upstream paper | Last validated | Critic verdict | What this synthesis takes from it |
|---|---|---|---|
| `standards/architecture/research/raw/code_routed_control_flow.md` | 2026-08-03 | PASS-WITH-FIXES (round 3) | §2.4 CI/CD payload caps + the TEP-0074 retreat; P4/P5/P12/P13; §4 on what a typed value buys with an LLM producer; §6.6's "ordinary as stated" verdict; N6 |
| `standards/architecture/research/raw/convergence_stopping.md` | 2026-08-03 | PASS | P11 — convergence detection *requires* typed comparable finding records; §5.1–5.7 — the case against a naive "stop when nothing new" rule |
| `standards/architecture/research/raw/claude_code_integration_surface.md` | 2026-07-25 | PASS | §1 `--json-schema` → validated `structured_output`; §7 ("Observability") the `result` envelope field list; §5 ("Failure and error surfaces") the absence of a first-party exit-code table **and the `system/api_retry` `error` enum**, which its §8 then applies in a failure-classification table |

⚠️ **`claude_code_integration_surface.md` carries `high — 4 weeks` and comes due around 2026-08-22.** Three candidates below depend on it. It is a **product-pool** paper — a component run may not refresh it, and this note is the handoff.

---

## What the pool found

### 1. Three of the sprint item's five milestones did not need research at all

Stated first because it is the cheapest finding here. `topics.md` records the reasoning; the short version: **the result envelope, the payload contract, and convergence-based stopping are already answered by verified upstream papers.** The phase doc can specify all three from citations. This cycle bought two papers, not five, for that reason.

### 2. There is a documented answer to "how do the two layers relate," and we are currently in the one arrangement nobody ships

Across 26 external sources, `dual_channel_outcome_records.md` finds **four arrangements** and, more usefully, finds that they are not equally represented:

| Arrangement | Direction | Instances | Failure mode |
|---|---|---|---|
| **A** — typed record is the artifact, human view is *rendered* from it | machine → human | SARIF → code-scanning alerts; Prow `finished.json` → crier → GitHub check; Open Test Reporting | The consumer implements a **subset** and silently drops the rest; payload caps |
| **B** — human artifact authored, machine value *parsed out* of it | human → machine | git trailers, kernel `Fixes:`, Gerrit `Change-Id`, Conventional Commits — **and this repo's `grep -oE '^VERDICT:'`** | Extraction is heuristic; human formatting rules get bent to protect the parser; the remedy for a wrong value is to rewrite the human artifact |
| **C** — one record, two regions (typed field + prose field) | co-authored in one act | SARIF `result.level` + `result.message`; CloudEvents; OTel attributes + body — **and this repo's `pr_review:` yaml beside its disposition table** | The prose region may carry semantics a consumer depends on. OTel forbids this outright |
| **D** — two artifacts, independently authored, bound by a shared key | neither | Kubernetes conditions vs. Events; SLSA attestation vs. release notes | Divergence unpoliced by construction |

Two generalisations do the work, and the paper marks both **derived over an enumerated set, not proven**:

- **Arrangement B never ships without a write-time gate.** Gerrit rejects the push on a missing `Change-Id`; Kubernetes auto-applies `do-not-merge/release-note-label-needed`; the Linux kernel *exempts tags from its own 75-column wrap rule "in order to simplify parsing scripts"*; git identifies a trailer block by a **25%-density heuristic**. Every located instance pairs the parse with enforcement at authoring time.
- **Arrangement B is always metadata *about* a human artifact — never the routing of a *process outcome*.** Where a process outcome routes a subsequent process, the arrangement is A or D, every time.

**`build.sh` today is B, for a process outcome, with no gate.** That is the finding, and it is narrower than "the current design is broken" — see §6 below, where the paper argues against its own thesis.

### 3. Two of the analogies in the brief are weaker than they look, and one is inverted

Worth stating because the phase doc would otherwise cite them:

- **SARIF is not "one outcome, two renderings."** `level` and `message` are sibling fields on one `result` object — arrangement **C**, not A. What looks like A is GitHub's *consumer* side. The transferable lesson is the **subset contract** (*"will only use the following supported properties … the rest of the supported fields are ignored"*) and the 10 MB cap, not a two-channel split.
- **Kubernetes conditions vs. Events is inverted relative to our constraint.** There the **human narrative channel is the expiring one** (`--event-ttl` default `1h0m0s`) while the typed channel persists on the object. We have the opposite: a durable human record and a machine value needed seconds after the child exits. **No located source addresses our configuration** (N1) — so the resolution in §5 of that paper is an extrapolation and is marked derived throughout.
- **Conventional Commits presupposes a mutable pre-merge artifact** (its documented remedy for a wrong value is `git rebase -i`). A posted PR comment is not rebaseable. It is excellent evidence for B's failure mode and poor evidence for adopting B.

### 4. The lifecycle mismatch is a storage problem, not a content problem

The phase doc's hardest-looking constraint — durable human record, transient machine read — **dissolves under arrangement A**: write the typed record once at exit to a channel the parent owns, render the human record from it, and archive that same typed record into the durable surface as a **by-product** rather than a second authoring act. One author, two copies, two lifetimes. This is what Prow does, and it is what this repo *almost* does already: the `pr_review:` block is already on the PR; the missing half is that **nothing typed reaches the parent at exit**.

### 5. Routing on values the model did not author is mature, boring, and canonical — outside the agent corpus

`non_model_observables.md` closes an explicitly-open upstream question. `code_routed_control_flow.md` §0(b) called routing on non-model values *"a strictly stronger and genuinely different claim"* and its **N6** recorded that no surveyed agent-framework doc presents such a value carrying real work product as its canonical branching example — while explicitly declining to claim the pattern was unused. That caution was right:

- Argo Workflows' exit-handler walkthrough branches on `when: "{{workflow.status}} == Succeeded"`.
- GitHub Actions applies `success()` as the **implicit default** on every `if:`.
- Airflow has **13 named trigger rules** over upstream task state alone.
- Kubernetes routes Job outcomes on **container exit codes** with an ordered rule list and a documented default.
- Tekton guards a Task on a `when` expression, and **records the skip** in `Skipped Tasks` — the non-execution is itself an observable.
- GitLab CI's `when` keyword closes over six values with `on_success` as the documented default (definitive, from the CI JSON schema), and its first-party prose defines `on_success` / `on_failure` against **upstream-stage outcome** (reduced confidence — the prose renders inconsistently, so the paper paraphrases it rather than quoting it; see N4 there).

**That last one is a correction landed by the critic pass, and it strengthens the finding rather than qualifying it.** GitLab's `on_success`/`on_failure` is a **third independent first-party vocabulary** routing on upstream-stage outcome, alongside Airflow's `all_success`/`one_failed` and GitHub Actions' `success()`/`failure()` — three vocabularies converging on the same two members.

**Consequence for the phase doc: stop treating "route on an observable" as a design novelty.** Borrow the shape. Kubernetes `podFailurePolicy`'s *ordered rules, first match wins, documented default* is a ready-made fail-safe contract.

### 6. The taxonomy the phase doc should adopt — and the boundary it must respect

Three classes, and the boundaries are **not where they look**:

- **(i) What the runtime knows about the run** — exit status, `is_error`, `subtype`, timeout, signal, retry exhaustion.
- **(ii) What a separate deterministic process computes over the artifacts** — empty diff, tests pass, coverage delta, **a finding-set delta between two passes**.
- **(iii) What the model asserted about its own work** — a verdict token, a severity, a confidence field.

Two corrections to the obvious reading: **class (i) vs (ii) is not "runtime vs. user code"** — coverage.py's `fail_under` surfaces as an exit status but carries a computed property of the artifact, so it is (ii) wearing an (i) envelope; **do not classify by transport**. And **class (ii) vs (iii) is "who chose the value"** — a finding-set delta over two model-authored finding sets is (ii), because the *records* are model-authored but the *delta* is not, and the delta is what the predicate reads.

**The boundary that is genuinely sharp** is between (iii) and everything else: only (iii) can be wrong in the specific way a fluent generator is wrong — confidently, plausibly, and in the required schema.

**What CANNOT move off the model's assertion in this fleet** — the most directly usable table in the pool:

| Decision | Movable? |
|---|---|
| "Is this PR mergeable?" | **No** — mergeability is a judgement about scope, correctness and taste |
| "Is this finding blocking or a nit?" | **No** — severity *is* the assertion |
| "Does this need a human ruling?" (`HOLD - needs-assistance`) | **No, by construction** — a predicate that could detect it would be the ground truth |
| "Was the review itself adequate?" | **No** — no mutation-testing analogue exists for a prose review |
| "Did the child finish, and how?" | **Yes** — class (i). Partially implemented; `.is_error` is the named gap |
| "Did it produce work at all?" | **Yes** — class (ii). Empty diff, PR URL, SHA changed |
| "Did it break the build?" | **Yes** — class (i)/(ii); `wait_for_ci` already exists |
| "Did it stall?" | **Yes in principle** — not implemented, and its precondition (a definite-progress signal) is unmet |
| "Has the finding set stopped changing?" | **Yes** — class (ii), and `convergence_stopping.md` §5.1–5.7 says when *not* to stop on it |

**In one sentence:** observables can establish that a run *happened, terminated, produced an artifact, and did not break anything checkable*. They cannot establish that the artifact is **right**, and every decision that turns on rightness stays class (iii).

### 7. The LLM-producer belief is HALF RIGHT, and the correction is the more useful half

The dispatch asked this to be tested rather than adopted. It does not survive intact.

**CI has the well-formed-plausible-wrong-result problem in a different costume, and it is measured:**

- *"A 95% confidence that a passing test case is not flaky on average would require 170 reruns"* — from an empirical study of flaky tests in Python that *"sampled 22352 open source projects from the popular PyPI package index, and analyzed their 876186 test cases for flakiness"* (arXiv:2101.09077). Green means "this run was green."
- SWE-Bench+ manually screened SWE-Agent+GPT-4's *successful* patches and reports that *"31.08% of the passed patches are suspicious patches due to weak test cases, i.e., the tests were not adequate to verify the correctness of a patch"* (arXiv:2410.06992). A computed observable certified a wrong artifact in roughly one case in three.
- GitHub Actions ships `continue-on-error` and documents the divergence itself: *"When a `continue-on-error` step fails, the `outcome` is `failure`, but the final `conclusion` is `success`."* A green build over a failed step is a **keyword**, not a bug.
- Mutation testing and coverage thresholds exist precisely because "the tests pass" under-certifies — both are gates *on the adequacy of the gate*.

**What genuinely differs is not the existence of well-formed wrong output. It is that a CI step's malformedness is a defect with a fix, whereas an LLM's is a stationary rate with a distribution.** That changes the **fail-safe contract** — it must be total, and it must assume the bad case recurs — not the taxonomy.

**The consequence for the phase doc's own prose:** stop justifying the design with *"our producer is special"* and justify it with *"our error rate is stationary, so the residual arm is load-bearing rather than decorative."* The first claim is contestable and a reviewer who knows CI will contest it. The second is the one the evidence supports.

### 8. Every mature observable vocabulary has an abstention member — but it means something narrower than ours does

Kubernetes probe results are `Success` / `Failure` / **`Unknown`** (*"The diagnostic failed (no action should be taken, and the kubelet will make further checks)"*). Argo separates `Failed` from `Error`. Monitoring Plugins reserve `Unknown`=3 for the plugin's own inability to answer. pytest distinguishes exit 5 (*"No tests were collected"*) from exit 0. Actions has `skipped`.

This corroborates upstream §4.4's prediction that a *model's* abstention arm will be under-used — those runtime abstentions are reliable **because the emitter has no incentive to guess**.

**But the paper argues against its own finding here, and the narrowing is the actionable part.** A runtime's `Unknown` means *the checker could not evaluate*. It never means *the work is ambiguous*. `HOLD - needs-assistance` means the second. So the recommendation is not "take the abstention member from an observable" — it is **split the abstention member in two**: a computed *could-not-check* arm and an asserted *needs-a-ruling* arm, with different reliability and different remedies.

### 9. Two corrections to the sprint item's own framing, verified against the shipped code

Both surfaced independently by the analyst reading the scripts, and both matter because milestone 1 is worded as a correctness gap:

- **The parent DOES gate on the child's process exit status.** `build.sh` sets `set -euo pipefail` (line 60) and runs children under `if ! "$PR_REVIEW" … | tee "$log"`, so `tee` does not mask a non-zero child. Coarse-grained class (i) routing already works.
- **`run-claude.sh` already reads two envelope observables, not zero** — it greps `"subtype":"error_max_turns"` (line 167) and `jq`-reads `.result` against `COMPLETION_PATTERN` (lines 201–204).

**What is genuinely absent, and the sprint item is right about this:** `.is_error` is never read. Neither are `permission_denials[]`, `num_turns` against the cap, nor `system/api_retry`'s `error` enum. And the sharper version of the gap: `claude_code_integration_surface.md` §5 records **there is no first-party exit-code table** for `claude`, and that codes for auth failure, rate-limit exhaustion and `--max-turns` exceeded are undocumented. **Class (i) routing in this fleet is resting on an undocumented mapping**, and whether a child can exit 0 with `is_error: true` is unknown.

### 10. The strongest case for Kind 2 is not routing — and the pool says so against its own interest

Recorded prominently because a phase doc could easily overclaim here. `dual_channel_outcome_records.md` §7.0.1 states it plainly: `build.sh`'s prose grep is fail-closed, the vocabulary is three closed tokens, `review-pr.sh` fails loud on absence, and **no evidence in this pool shows that arrangement producing a wrong route.** A phase doc that claims the current arrangement is broken is overclaiming.

What the evidence *does* support is narrower and still sufficient: it is the one arrangement the corpus never ships without a gate, and its failure mode is **silent** — a prose format change moves the token, and the fail-closed default converts that into a spurious `needs-assistance` rather than a loud error.

**And the strongest justification is upstream and independent of routing entirely:** `convergence_stopping.md` P11 establishes that convergence detection *requires* typed, comparable finding records. That argument has no working incumbent to beat. **Lead the phase doc with it.**

### 11. How the burn-test intake's first look held up — it survives intact

`burn-test-intake-2026-08-02.md` § *Item 4* marks itself a lead — one interactive session, never a `research.sh` run, never through `research-critic`. Per the dispatch, where it and a verified paper disagree the paper wins and the discrepancy is noted rather than averaged. **Checked claim by claim against Item 4's actual text, there is no such disagreement to note** — every claim it makes is either corroborated or untouched:

| Item 4's first look | The verified paper |
|---|---|
| Cites GitHub Actions' deprecation of stdout output-passing (`set-output` → `$GITHUB_OUTPUT`) as security-motivated | Not covered either way — **not contradicted, and not corroborated** |
| Tekton's **4096-byte cap** teaches "references, not payloads" | **Corroborated and strengthened** — Tekton 4 KB, Airflow "small amounts of data", Argo's 1 MB etcd resource ceiling, plus TEP-0074's withdrawal of a rich typed handoff object for coupling and conceptual opacity |
| A2A's task-state enum validates a closed vocabulary, but is *"right idea about state, wrong layer"* for a parent shelling out to a child on the same box | Consistent with both new papers |

**Net:** Item 4's *convergent sentence* — the producer writes structured output to a path the caller declares, the caller reads the file, the log stays a log — is exactly arrangement A and survives. So does its only cap figure, Tekton's 4096 bytes.

**A caution that is NOT about Item 4, and was previously misattributed to it here.** The widely-cited GitHub Actions **1 MB / 50 MB** output caps were **not found in the fetched primary** (`code_routed_control_flow.md` N4 — what GitHub *does* document there is secret redaction and matrix last-writer-wins collision). Those figures appear nowhere in the burn-test intake; the phase doc simply must not cite them from anywhere.

---

## Escalations — findings above this component's altitude

**One.** This workflow's own component-altitude guidance says an escalation is rare, and that producing more than one or two signals the analyst has drifted upward rather than that the project is in trouble. *(That guidance sits in an unnumbered subsection of the run's altitude brief — no section number is cited here, because the one previously given pointed at an unrelated rule.)*

- **`non_model_observables.md` materially closes upstream negative finding N6, and closing it weakens the last defensible reading of problem-statement element 3.** `code_routed_control_flow.md` §6.6 already ruled element 3 "ordinary as stated" and offered two narrower re-cuts, of which **(b) — routing on values the model did not author — was called *"the strongest available reading of element 3."*** This cycle finds that pattern documented as the **canonical branching example** in Argo, GitHub Actions, Airflow, Tekton and Kubernetes. N6's gap was in the agent corpus's documentation, not in the field's practice, and the upstream paper said so; this pool supplies the instances. **What it bears on:** `docs/standards/architecture/problem-statement.md` element 3, and any differentiator resting on it. **What I think it means:** re-cut (b) should be retired as a novelty claim, leaving re-cut (a) — cross-process, cross-run, disjoint-context, resumed-from-persisted-state — as the only reading still uncovered by the located literature. **This is not mine to file.** The product pool is read-only to this run; the operator disposes.

---

## Action candidates

Reviewable items, sized for a standup. Nothing is ratified. Per §7 this run surfaces candidates here and **writes nothing outside `research/`** — routing is the reviewer's and the operator's. **Every candidate rests on a paper that is through the critic gate** (both carry `PASS-WITH-FIXES — 2026-08-06`; see Inputs). Verification does not flatten confidence: **the per-claim marks in the source papers still govern** — several candidates below rest on claims marked *derived* or *directional*, and those are labelled where they occur.

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Adopt arrangement A: the child writes a small typed record at exit to a channel the parent owns, and the human record is rendered from it.** This is the pool's central recommendation and it dissolves the lifecycle mismatch rather than solving it. Two viable transports: a JSON file at a caller-declared path, or `--output-format json --json-schema` and the parent reads `structured_output`. **Prefer the file variant if the schema surface proves unavailable** — it carries the same properties with no dependency on a high-volatility CLI feature | adopt | `dual_channel_outcome_records.md` R1, §5, P2 |
| 2 | **Keep what the parent READS tiny and versioned — roughly `{schema_version, verdict, hold_kind, pass, pr}` — and write that subset down as its own contract.** The rich findings array stays a payload the parent never branches on. SLSA's verifier reads four things; Tekton retreated from a rich handoff object; GitHub's SARIF consumer implements a documented subset and ignores the rest. **Every field the parent does not read is explicitly not load-bearing, and saying so is the point** | adopt | `dual_channel_outcome_records.md` R2, P3, P5 |
| 3 | **Split the abstention member in two: a computed `could-not-check` arm and an asserted `needs-a-ruling` arm.** They have different reliability and different remedies, and every mature vocabulary surveyed has only the first. This is the concrete change to the closed-vocabulary design and it is *not* in the sprint item today | new concept | `non_model_observables.md` §0 finding 3, §5.5, P5 |
| 4 | **When `is_error` and the model's verdict disagree, record BOTH under distinct names and route on a documented composition rule with a named residual — do not pick one.** GitHub Actions' `outcome` / `conclusion` split is the shape (raw observation never overwritten, policy-adjusted value is what conditions see by default); Kubernetes' ordered-rules-with-default is the evaluation semantics. **No surveyed system documents precedence between an asserted and a computed result** (N1), because none has an asserting producer — so this is derived, and T3 is written to settle it empirically | new concept | `non_model_observables.md` §3.3, P11, P12, N1 |
| 5 | **Correct milestone 1's framing before the phase doc inherits it — the parent DOES gate on exit status and `run-claude.sh` DOES read two envelope observables.** `set -euo pipefail` + `tee` propagates the child's status; `subtype` and `.result` are already read. The real gap is `.is_error`, `permission_denials[]`, `num_turns`-vs-cap, and the `api_retry` error enum — **plus the sharper one: there is no first-party exit-code table, so class (i) routing rests on an undocumented mapping.** `sprint.md` is operator-only; this is surfaced, not written | change direction | `non_model_observables.md` §3.4, N2; `claude_code_integration_surface.md` §5 |
| 6 | **Rewrite the design's justification: not "our producer is special" but "our error rate is stationary."** CI's producers emit well-formed wrong results too, and it is measured (170 reruns for 95% confidence a pass isn't flaky; 31.08% of SWE-Bench+ passed patches suspicious; `continue-on-error` as a shipped keyword). The difference is defect-with-a-fix vs. stationary-rate-with-a-distribution, which changes the **fail-safe contract**, not the taxonomy. Cost 0 — it is a paragraph — and it removes a claim a CI-literate reviewer will break | change direction | `non_model_observables.md` §0 finding 2, P13 |
| 7 | **Lead the phase doc with the MEASUREMENT argument, not the routing argument.** `convergence_stopping.md` P11 (typed comparable records are a precondition for convergence detection) has no working incumbent to beat; the routing argument does, and this pool found no evidence the incumbent produces a wrong route. **A phase doc claiming the current arrangement is broken is overclaiming** | change direction | `dual_channel_outcome_records.md` §7.0.1, §7.0.2 |
| 8 | **Render the `review-pr` disposition table from the typed record — or, if co-authoring persists, add a write-time invariant (every table row has a matching finding `id` in the yaml, and vice versa) checked before the comment is posted.** Today they are two prose regions written in one act with no declared precedence — the one thing none of the surveyed arrangement-C instances permit. **Whichever is chosen, declare that the typed region wins**, because no source lets the prose region carry semantics | adopt | `dual_channel_outcome_records.md` R4, P8, P12 |
| 9 | **Archive the typed record into the PR as a by-product of rendering, not as a second write — Kind 1 is unchanged by this.** `/standup` keeps parsing the same `pr_review:` block; the block simply becomes a copy of the exit-channel record rather than an independent composition | adopt | `dual_channel_outcome_records.md` R5, §5 |
| 10 | **Do NOT put the machine channel in git notes or commit trailers.** That family is arrangement-B metadata *about* a durable artifact and is never used to route a process outcome; notes additionally have an unresolved transfer-semantics question (N4) — a reason to avoid, not a reason to assume | no change *(the negative is the finding)* | `dual_channel_outcome_records.md` R7, N4 |
| 11 | **Do not cite SARIF or Conventional Commits as precedent in the phase doc.** SARIF is arrangement C, not A — the transferable lesson is the subset contract and the cap. Conventional Commits presupposes a rebaseable pre-merge artifact, which a posted PR comment is not. Both are good evidence for a *failure mode* and bad evidence for an adoption | change direction | `dual_channel_outcome_records.md` §7.0.6, §7.0.7 |
| 12 | **Run T1 and T5 before the design is fixed — both are cheap and either can move it.** T1: does `claude -p` ever exit 0 with `is_error: true` on the pinned version, and what are the exit codes for turn-cap and auth failure (N2 says undocumented). T5: replay archived `stream-json` logs through the current `grep -oE '^VERDICT:'` predicate and **count the misses** — if the fall-through count is zero across the sample, the transport upgrade buys nothing measurable at this scale and candidate 7's ordering becomes load-bearing | adopt | `non_model_observables.md` T1; `dual_channel_outcome_records.md` T5 |
| 13 | **A capability the sprint item does not name: a definite-progress signal, and the stall/liveness axis on top of it.** "Did it stall?" is answerable in principle from class (i), but its precondition is unmet — nothing in the fleet emits a progress signal a probe could read. This composes with the product pool's already-surfaced three-legged liveness taxonomy (**stalled** / **looping** / **stranded**), which names this component as one of its destinations. **Scope call for the operator: in this component, or deferred to Autonomous Operation?** | new concept | `non_model_observables.md` P8, P9, §5.1 |
| 14 | **Standards-amendment candidate — `docs/standards/workflow-scripts.md § Composition` codifies the VERDICT-over-stdout contract, which the evidence identifies as the one arrangement the corpus never ships without a write-time gate.** Not urgent and not a defect claim (see candidate 7), but the standard currently states a mechanism the pool's comparative evidence recommends against. Human-ratified path only; a **planning run** writes it, never this one — **and see the homeless finding below, because the surface §7 routes it to does not exist for this component** | change direction | `dual_channel_outcome_records.md` §3, P7 |
| 15 | **Keep the widely-cited GitHub Actions 1 MB / 50 MB output caps out of the phase doc** — N4 records they were not found in the fetched primary, so they are unverified wherever they are met. **No correction to `burn-test-intake-2026-08-02.md` is warranted**: an earlier draft of this synthesis attributed those figures to its § Item 4, and Item 4 does not state them — its only cap figure is Tekton's 4096 bytes, which is corroborated. Nothing to file; recorded so the retracted correction is not re-proposed | no change *(the retraction is the finding)* | `code_routed_control_flow.md` N4; `burn-test-intake-2026-08-02.md` § Item 4, read directly |

---

## Homeless findings

Named here rather than parked elsewhere, per §7 — a homeless finding means the surface is missing.

- **Candidate 14 has no surface to be routed to.** §7's consumption table sends a standards-amendment candidate to *"the consuming component's **roadmap** 'Standards-amendment candidates' section (create it if absent)."* This component has **no roadmap and correctly should not have one** — `sprint.md` states that a component fitting in one phase gets `<name>/<name>.md` and that a roadmap should not be created "to be tidy." So the standard's routing table assumes an artifact the repo's own convention forbids here. Either the phase doc gains such a section, or the table needs a single-phase-component row. **The reviewer disposes; this run only names it.**

- **"Which channel owns the to-do bit" has no ruling anywhere.** Kind 1 uses **open/closed** as the to-do bit — that is its defining property. A typed record carrying a `verdict` field is a second state machine over the same work, and the pool found that Kubernetes' answer is *neither closes the loop* (a condition is current state, an Event is history). **Nothing upstream tells us which one wins here**, and the phase doc will have to rule on it without precedent (T3 in `dual_channel_outcome_records.md`). Flagged as homeless rather than as a gap because it is a **decision with no owner**, not a fact nobody has looked up.

---

## Gaps this cycle did not cover

- **The lifecycle mismatch itself has no precedent** (N1). Every located analogue is inverted — Kubernetes' human channel expires while the typed one persists; SLSA's typed channel is durable while release notes are unbound. §5's resolution is an extrapolation, marked derived throughout, and its falsifiers are in the paper's test plan.
- **No source measures the error rate of any non-model observable used as a routing channel** (N3/N6 in `non_model_observables.md`). The flaky-test and weak-test figures are the nearest quantifications and neither is about an orchestrator's routing channel. This is an experiment, not a literature question.
- **Whether `claude -p` can exit 0 with `is_error: true` is undocumented** (N2) — and there is no first-party exit-code table at all. T1.
- **Schema evolution across independently-versioned producers and consumers** — deliberately deferred in `topics.md`. Upstream P12 and TEP-0074 establish it as a documented hard problem with a documented retreat; our specific version-skew question (a parent on `main` reading an envelope written by an older worktree) is a *design* ruling the phase doc has enough evidence to make. Revisit only if it cannot.
- **OpenTelemetry's general "attributes vs. body" placement rubric was NOT FOUND** in the two documents where it was expected (N2 in `dual_channel_outcome_records.md`); only the narrower body-is-display-only rule was located.
- **GitHub Checks API `conclusion` semantics** could not be obtained from a raw first-party source (N6 there), so nothing in the pool depends on them.
- **The Argo "keep useful logs, export only specific JSON" distinction named in the dispatch brief was not corroborated** at the paths checked (N7). Argo's size caps are cited to the upstream paper instead. **The brief's claim should not be repeated without a source.**
- **GitLab CI's prose `when` semantics are carried, but no span of them may be quoted** (N4 there, restated after the critic pass withdrew an earlier, wrong version of this finding). The semantics *are* first-party and *are* in the paper's §2.1 — as an explicitly-labelled reduced-confidence paraphrase, because four retrievals across two hosts returned three mutually inconsistent wordings, so the content is certain and the exact characters are not. The closed vocabulary and the `on_success` default remain definitive from the CI JSON schema. **The residual limit is quotability, not knowledge** — a consumer needing to quote GitLab's wording must re-retrieve it.
