# Synthesis — workflow-decomposition research

**Cycle:** 2026-08-18 (cycle 2) · **Pool:** 2 papers · **Tier:** Small / single-concern component per paper

Read this instead of the pool. It says what the evidence means for Phase 2's and Phase 3's rulings
and ends in reviewable candidates. Nothing here is binding — research is evidence, and a finding
becomes a rule only by being codified into a standard through human review.

## Inputs

| Paper | Last validated | Revalidate | Critic verdict |
|---|---|---|---|
| [`raw/fork_vs_parameterize_drift_signal.md`](raw/fork_vs_parameterize_drift_signal.md) | 2026-08-17 | high — 6 weeks (due 2026-09-28) | **PASS-WITH-FIXES** — three critic rounds, zero blocking findings from round 2 on. Full history in the prior cycle-1 synthesis, preserved below. |
| [`raw/invocation_contract.md`](raw/invocation_contract.md) | 2026-08-18 | high — 4 weeks (due 2026-09-15; mixed-volatility, §4.3 fast-decaying, §2/§3 slow-decaying) | **not-yet-verified** — this paper has not yet been through a critic round. Treat every claim below sourced to it as unverified evidence until a `research-critic` pass runs. |

Both papers also lean on upstream, product-pool papers they cite rather than re-derive:
[`docs/standards/architecture/research/raw/workflow_reuse_boundary.md`](../../../standards/architecture/research/raw/workflow_reuse_boundary.md)
(`Last validated: 2026-08-03`, `high — 6 weeks`, due 2026-09-14, current, PASS-WITH-FIXES) and, new
this cycle,
[`claude_code_integration_surface.md`](../../../standards/architecture/research/raw/claude_code_integration_surface.md)
(`2026-07-25`, `high — 4 weeks`, due 2026-08-22 — **four days from its window at cycle time**;
`invocation_contract.md` §1.3 flags that its own P13/P12 corroboration to that paper should be treated
as unverified after that date) and
[`paperclip_assessment.md`](../../../standards/architecture/research/raw/paperclip_assessment.md)
(`2026-08-04`, `high — 4 weeks`, due 2026-09-01, current, PASS-WITH-FIXES). Treat any claim below
sourced to "upstream" as carrying that paper's own verdict, not this cycle's.

**One boundary carried forward from cycle 1, unchanged:** a critic pass over *this synthesis* checks
it against its inputs, not against either paper's external sources. The verdict column above is each
paper's own. `invocation_contract.md` additionally has no critic round at all yet — a consequential
call should read the paper itself, not this rollup.

---

## What this means for us — Phase 2 (unchanged from cycle 1)

Fork-vs-parameterize is a human judgement, reasoning written down, never an automated gate — the
κ=0.271 inter-rater ceiling and intent being a property of a person's awareness, not of a text, rule
out scoring it. When ruling on a drifted pair, check fit-to-referent and drift *pattern*, not
inter-copy similarity magnitude. Do not import the literature's default-to-intentional convention —
it was conservative for a research hypothesis, and our failure mode runs the opposite direction. Full
detail, findings 1–3 and action candidates 1–6, is unchanged from the prior cycle and not restated
here — read the paper's own §6.1–6.3 and §7 rather than a second summary of a summary.

## What this means for us — Phase 3, the invocation contract

**The paper's own framing correction matters more than any single finding: `plan-project` is already
built and running, and it already derives component scope from a positional path.** A planner who
reads Phase 3's checkbox wording cold and scopes "build target-derived scope" is scoping a project
that shipped. The real work is narrower — see below.

### 1. Facet 1 (dual-mode) is a shape that already exists, mostly — with one unresolved contradiction blocking how far it should be extended

The fleet's shim → runner → core-function structure is already the field's converged answer
(Temporal's "two entrypoints, one core," `workflow-scripts.md`'s own parent/child rule that "a child
workflow is not a kind of file in a place, it is a workflow that another workflow starts"), with
`verbose` already threaded as an explicit parameter rather than detected. **The measured gap is nine
workflow modules — all children — with no standalone runner, not a wrong pattern.** Fixing that is a
mechanical nine-adapter job, cheap to scope and cheap to build.

**But it may not be the right nine to build**, and the paper cannot settle this — it is a ruling, not
a finding, and the synthesis surfaces it rather than resolving it: `workflow-scripts.md` already
states *"Running one by hand is recovery … never the interface."* Phase 3's checkbox — *"every child
runs standalone and under a parent, equally well"* — reads as the opposite rule. **A planner cannot
decompose this checkbox without an operator ruling on which of the two stands first.** If
standalone-is-recovery-only is the standing rule, nine children without shells is a deliberate
narrowing, not a defect, and the checkbox needs rewording before it is planned against.

The enumerated failure surface for whichever children *do* get adapters is concrete and citable:
verbosity inversion, exit-code semantics, interactive-prompt blocking, stream discipline,
working-directory assumptions (measured: six of seven V2 entrypoints once dropped repo-root
resolution and used `cwd` instead) — each backed by a first-party span, not asserted.

### 2. Facet 2's real work is three missing properties, not a missing mechanism

The field's convergent answer for a *safe* derived value is five properties: anchor on a marker
(a fact, not a similarity judgement), publish the algorithm, echo what was derived, provide an
explicit override, and state the derived value's scope of effect. Measured against what shipped:
**the marker-anchor and the override already exist** (`resolve_repo_root`'s git-root anchoring;
`--repo`). **The published algorithm, the echo, and the stated scope of effect do not.** That's the
actual Phase 3 item — three specific, small additions to code that already runs, not a new
derivation subsystem.

**The strongest counter-case is one this repo already decided correctly and should not re-litigate:**
repo identity is declared (`--repo`, explicitly "never derived from cwd"), component scope is
derived. Derivation is a per-value decision with a stated reason, not a blanket policy — a Phase 3
rule that says "prefer derivation" would contradict a decision already shipped and working.

**One structural honest-boundary point carries real weight:** a wrong derivation produces a
*plausible* wrong run — the workflow plans the wrong component competently — where a wrong flag fails
loudly at parse time. Against an LLM producer, that asymmetry is the argument for the echo (M3) being
non-optional, and it is also the reason M3 collides with facet 1's verbosity property (F1) — echoing
costs output, and the caller that most wants silence (a parent) is the caller that most needs the
echo suppressible. Nobody has measured the trade; it is argued convention, not evidence, across every
source found.

**A wording defect in the roadmap itself, surfaced and not corrected here (out of this run's write
boundary):** Phase 3's third checkbox says `research_refresh_parent` "has no entrypoint — a parent
nothing can invoke." Measured at `128091c`: it *is* invocable, via `run_research.py --refresh`. The
real, narrower defect is that it has no entrypoint **of its own** — no `research_refresh.sh`. A
planner decomposing the checkbox as currently worded will scope the wrong fix.

### 3. Facet 3's honest answer is: build one digest, and stop there until the evidence says otherwise

Five shipping systems were read for managed-plus-user config layering. The precedence direction is
**not universal** — it is a policy choice disguised as a technical one, and it runs two opposite ways
depending on who "managed" means: vendor-package systems (git, npm, systemd) let the *local* tier
win; org-policy systems (VS Code Policy, Claude Code's own Managed tier) let the *managed* tier win
unconditionally. **Phase 3's stated intent — "the user keeps a tier they own and can extend" — is the
first shape.** A design that reaches for Claude Code's own Managed tier because it is named "managed"
would silently adopt the second shape and remove the very tier the checkbox promises the user.

**One derived finding is flagged, not adopted, because it needs a measurement this cycle did not
run:** declaring the safety hook specifically in Claude Code's Managed tier would plausibly make it
immune to both `--setting-sources` and `--safe-mode` — a direct route out of the blocker recorded in
`test_no_runner_STRIPS_the_settings_file_the_safety_hook_lives_in`. This is an inference across three
sources, one of them a rendered page. **It must be measured (paper's T2) before any design relies on
it**, and the safety-layer invariant already demands exactly that kind of demonstration before
landing.

**The facet's own gate, already stated in the roadmap, is currently open and cheap to close:** *"if
the run bag records the config a run used, the divergence half shrinks to a reader."* Measured: the
run bag carries five `Journal-` tags today and none of them names the configuration used. Closing
that gate is one additional tag. **And once it is closed, most of the rest of what the field ships —
provenance commands, typed drift diffs, cross-machine agreement proofs — may never be justified**:
if the digest is in the bag, divergence detection falls out for free as a post-hoc reader over run
bags, without building a drift detector at all. The paper's own honest-boundary section goes further
still: this fleet currently has one operator, and the multi-machine case the checkbox describes may
not be live yet — the minimal, defensible Phase 3 increment for this facet is **one digest, one info
tag, one reader**, with everything else deferred until the evidence says it's needed.

---

## Action candidates

Reviewable items, sized for a standup. Nothing is ratified. Per §7 this run surfaces candidates here
and writes nothing outside `research/` — routing is the reviewer's and the operator's.

| # | Candidate | Type | Rests on |
|---|---|---|---|
| 1 | **Rule Phase 2's fork-vs-parameterize item as a human judgement, reasoning written down — never automated.** Unchanged from cycle 1. | adopt | `raw/fork_vs_parameterize_drift_signal.md` §2.2, §6.1–6.2 |
| 2 | **When ruling a specific drifted pair, check fit-to-referent and drift pattern, not inter-copy similarity magnitude.** Unchanged from cycle 1. | adopt | `raw/fork_vs_parameterize_drift_signal.md` §3.3, §4.2 |
| 3 | **Do not import the literature's default-to-intentional-when-unreachable convention.** Unchanged from cycle 1. | no change *(the finding IS the warning)* | `raw/fork_vs_parameterize_drift_signal.md` §6.3 |
| 4 | **Either publish the method behind the standard's 85.8%/76.1%/62.1% similarity figures, or drop them.** Unchanged from cycle 1. Home per §7: `workflow-decomposition/roadmap.md` § *Standards-amendment candidates* (create if absent) — a planning run writes it there after the operator's ratification pass, never a research run. | adopt | `raw/fork_vs_parameterize_drift_signal.md` §7 item 5, §5.5, §3.3 |
| 5 | **Run the blind-classify-then-reveal-history validation.** Unchanged from cycle 1. | adopt | `raw/fork_vs_parameterize_drift_signal.md` §7 items 1–2 |
| 6 | **No change to the `from_plan.md` byte-identical pair or any other specific pair.** Unchanged from cycle 1. | no change *(the restraint is the finding)* | `raw/fork_vs_parameterize_drift_signal.md` §5.3, §6.5 |
| 7 | **Before decomposing Phase 3's first checkbox, get an operator ruling on the standing contradiction: `workflow-scripts.md` says standalone invocation is "recovery … never the interface"; the checkbox says "every child runs standalone and under a parent, equally well."** A planner cannot resolve this — it is a design decision, not evidence. Whichever way it rules, the nine-missing-adapter gap (facet 1, measured) is the concrete unit of work either to build or to explicitly decline. | new concept *(a ruling to make, not a build to plan yet)* | `raw/invocation_contract.md` §6.1 |
| 8 | **Adopt the five-property safe-derivation checklist (anchor / published algorithm / echo / override / stated scope) and apply the two missing properties (echo, stated scope) plus the published-algorithm write-up to `plan-feature`'s already-shipped component-path derivation.** Marker-anchor and override are already satisfied; this is finishing three properties on code that runs today, not new derivation machinery. | adopt | `raw/invocation_contract.md` §2.2 (M1–M5), §4.2 (P6, P7), §5.2 |
| 9 | **Correct Phase 3's third checkbox wording before it is planned: `research_refresh_parent` IS invocable (via `run_research.py --refresh`); the real defect is that it has no entrypoint of its own.** Home per §7: the phase doc's own text once Phase 3 gets one, or the roadmap line directly — a **planning run** writes it, never this research run. | change direction | `raw/invocation_contract.md` §5.1 |
| 10 | **Ship the minimal facet-3 increment only: one config digest, added as a sixth `Journal-` tag in the run bag, read back by a reader — and defer provenance commands, typed drift diffs, and cross-machine agreement proofs until the digest shows they're needed.** This closes the roadmap's own stated gate ("if the run bag records the config a run used, the divergence half shrinks to a reader") at the cost the paper's own honest-boundary section argues is the only currently-justified one, given a single-operator fleet today. | adopt | `raw/invocation_contract.md` §2.3 (P17), §5.3 (P16), §6.3 |
| 11 | **Do NOT design toward Claude Code's own Managed settings tier as a load-bearing mechanism until T2 (declare the safety hook there; test against `--setting-sources` and `--safe-mode`) is actually run.** The immunity property is a three-source inference, one source rendered, explicitly flagged by the paper as unmeasured. | adopt *(as a "measure before building" constraint, not a design)* | `raw/invocation_contract.md` §4.3 (P14), §7 (T2) |
| 12 | **Do not read Claude Code's `--bare` flag as applicable to this fleet, despite the upstream integration paper recommending it for reproducibility.** `--bare` skips hooks (the safety-layer invariant's sole live control in headless runs) and refuses OAuth/keychain reads (the subscription credential this whole edge runs on). The upstream recommendation is correct for an API-keyed worker and does not transfer to a subscription-backed edge. | no change *(a citation this repo should not follow, named so it isn't adopted by association)* | `raw/invocation_contract.md` §4.3 (P13); `claude_code_integration_surface.md` §8 |
| 13 | **When building the nine missing dual-mode adapters (if candidate 7 rules to build them), add the shim-naming guard at the same time — do not let it lag.** `test_shim_usage_names_itself.py` exists because three prior V2 entry scripts shipped with wrong usage text copied from their clone source; adding nine new adapters without the corresponding guard risks the same defect at three times today's scale. | adopt | `raw/invocation_contract.md` §4.4 (P19) |

**Homeless findings this cycle: none.** Every candidate above has a home in §7's routing table.
Candidate 7 is a ruling for the operator, not a filing gap — §7's table does not need to name a home
for "the operator decides," since the operator is always reachable directly, and this synthesis is
where the reviewer routes it per the disposition doctrine.

## Gaps this cycle did not cover

- **`invocation_contract.md` carries `Critic: not-yet-verified`.** No claim in the Phase 3 section
  above should be treated as more certain than the paper itself states until a `research-critic`
  pass runs against it.
- **No source was found measuring the defect rate of derived-vs-declared configuration** — the
  entire industry position on facet 2 (derive when safe) is argued by convention across five sources,
  never evidenced by data. Stated as a gap in the paper (§6.2), carried here because it bears
  directly on how much weight candidate 8 should get.
- **Whether declaring the safety hook in the Managed tier actually confers immunity to
  `--setting-sources`/`--safe-mode` (P14) is untested** — flagged above as candidate 11's constraint,
  restated here as a gap because it blocks any facet-3 design beyond the minimal digest increment.
  Paper's test plan T2 is the way to close it.
- **Whether `managed-settings.d/` (a drop-in directory alongside Claude Code's single managed-settings
  file) exists and merges is unverified** — single rendered-page source, no verbatim span. Paper's
  test plan T8.
- **The paper's own negative finding on TTY-sniffing (no first-party source recommends detection
  without an explicit override) rests on two sources, not a survey** — the paper names this itself
  (§6.1) as thin for the weight a reader might put on it.
- Prompt/LLM-engineering literature coverage, tooling-search coverage, and the three adjacent
  out-of-scope lines of enquiry (child-set correctness, resumed-run fragment survival,
  prompt-quality-vs-child-performance) are unchanged from cycle 1 — see the paper's own §7/§8 for the
  Phase 2 gaps, unchanged and not restated here.
