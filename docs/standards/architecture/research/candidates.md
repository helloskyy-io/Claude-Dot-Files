# Action candidates — the running list

**This file is the durable home for research action candidates. `synthesis.md` is rewritten every cycle; this is not.**

## Why it exists

A candidate surfaced in `synthesis.md` disappeared on the next research cycle, so its disposition — and the reasoning behind a rejection — went with it. Two consequences, both observed: candidates already ruled on were re-proposed in later cycles, and seven of them were parked on the standup tracker because no other surface would hold them, which the tracker's own rules forbid.

## The rule

> **Research creates and appends. Planning dispositions.**

- **Research** adds new candidates with a **stable ID**, never reused, and never renumbers an existing one.
- **Planning** sets `decision`; a later process sets `status`. Both carry reasoning in the Note.
- **A carried-forward candidate REUSES its original ID.** When a later cycle restates a live candidate, it is the same candidate — do not mint a new ID. (Cycle 4 restated C-007 and this file briefly carried it twice before the duplicate was removed.)
- **Nobody deletes a row.** A rejected candidate stays visible so it is not re-proposed — that is the whole point.

## Two flags, orthogonal — do not collapse them

| Flag | Values | Who sets it |
|---|---|---|
| **`decision`** | `ship` · `requires review` · `reject` · **blank = not yet triaged** | **`plan-sprint`, and only `plan-sprint`.** This is its triage output |
| **`status`** | `open` · `closed` | **A later process.** `plan-feature` when the item lands in a phase doc; the build that completes it |

## The three dispositions

Every candidate ends at exactly one of these. There is no fourth, and **leaving a row blank is not a disposition** — it means triage has not happened yet.

### `ship` — we have decided to do this

The work is **understood well enough to schedule.** Somebody could pick it up and know what "done" looks like without another decision being made first.

**`ship` does NOT mean done.** A shipped candidate stays `open` until something actually implements it, and neither `plan-sprint` nor `plan-tech-stack` does detailed phase design, so neither can close one on its own.

### `requires review` — only the operator can rule on this

The candidate is **not ready to be scheduled, and no amount of further automated work makes it ready.** An open question, an unresolved trade-off, a ruling that changes what the project believes. Shipping it would put a question mark in the plan; rejecting it would throw away a real finding.

**Where it goes:** `plan-sprint` writes a `D-NNN` row into [`direction.md`](direction.md) — the operator's file — and sets `decision` here to `requires review`. The row stays in this file as the pointer, and **`status` stays `open`** because the decision is outstanding, just outstanding with a human.

**It then leaves the automation's working set entirely.** A non-blank decision is not re-triaged, so it never comes back around. It surfaces at `/standup` as an open direction decision, the operator rules, and only then does the disposition change to `ship` or `reject`.

> **This is the release valve.** Without it, `ship` and `reject` are the only doors out, and an open question that deserves neither gets forced through one of them. That is exactly what happened on the first `plan-sprint` run: eleven unresolved questions were shipped into the sprint plan as milestones, which produced two sprints that build nothing.

### `reject` — we are not doing this

State why in the Note. **The reasoning is the point** — a rejection without it gets re-proposed on the next cycle by a run that cannot see why it was refused.

## Where a shipped decision lands depends on its size

A candidate large enough to need its own sprint section gets one, added by `plan-sprint` — that is the **entire** extent of `plan-sprint`'s implementation. **Most shipped candidates are not that size.** They belong inside an *existing* sprint or phase doc, placed by `plan-feature`, and `plan-sprint` does nothing with them beyond setting `decision`.

**A blank decision is not the same as `open`.** Blank means nobody has triaged it; `open` means the work is outstanding. Collapsing the two is what turns this file into a to-do list nobody agreed to — the failure that put seven untriaged candidates on the standup tracker.

**Every workflow that touches this file states its own portion in its prompt:** *the decision was made — implement your portion only.*

## Provenance note — read before trusting cycle-4 rows

Cycle-3 rows come from `synthesis.md` on `main` and are settled. **Cycle-4 rows come from PR #33, which is `HOLD - redispatch` and unmerged.** Its held item concerns a currency-tier marker that C-024's costing rests on, so cycle-4 entries are **provisional** and this file gets revised if that assessment finds the evidence thin.

---

## Cycle 3 — 2026-08-04

| ID | Candidate | Source | `decision` | `status` | Note |
|---|---|---|---|---|---|
| C-001 | Heartbeat clause on `python_sdk_long_activities.md` — heartbeats free at the SDK layer, billable on Cloud | `temporal.md` | `reject` | `closed` | billing is moot on self-hosted. The *ceiling* survives for a different reason: every heartbeat is a persistence write on our own cluster |
| C-002 | Schedule the self-host-vs-Cloud decision | `temporal.md` | `reject` | `closed` | decided 2026-07-12, self-hosted. Recorded in `system-overview.md` § Deployment target |
| C-003 | Decide shard capacity before the first self-hosted workflow runs | `temporal.md` | `ship` | `open` | build-time one-way door, and now *more* relevant since we self-host. **Ship:** a parameter of the server stand-up, not a question — Temporal Integration phase-doc detail |
| C-004 | Override the default retry policy on every activity wrapping a paid API — Temporal defaults to unlimited attempts | `temporal.md` | `ship` | `open` | **Ship:** a concrete rule for every activity wrapper; Temporal Integration Stage B phase-doc detail |
| C-005 | Amend the Serverless Workers reading — Lambda caps an activity at 15 min | `dedicated_edge_routing.md` | `reject` | `closed` | k3s pods, not serverless |
| C-006 | Record that no first-party Claude ↔ Temporal runtime integration exists | `temporal.md` | `ship` | `open` | **Ship:** scopes the hand-rolled `claude_cli` integration as permanent rather than temporary. Natural home is `stack_reference.md`, which is human-in-the-loop — Temporal Integration phase doc meanwhile |
| C-007 | Correct differentiator #1 in `problem-statement.md` | `bernstein_capability_mining.md` §0.1 | `ship` | `closed` | `b9710d5` |
| C-008 | Replace differentiator #2 with the credential version | `dedicated_edge_routing.md` §7 | `ship` | `closed` | `b9710d5` |
| C-009 | Add the trust-domain claim — stronger than any scheduling-model difference | `bernstein_capability_mining.md` §0.2 | `ship` | `closed` | `b9710d5`, promoted to differentiator #1 |
| C-010 | Resolve the queue-axis conflict before Temporal Integration is planned | `dedicated_edge_routing.md` §4.1 | `requires review` | `open` | gates that sprint; addendum §A3. **`D-001`** — the resolution is a commitment against a vendored standard, and C-022's spike is the evidence it needs first |
| C-011 | Ship three cheap guards: credential expiry, false completion, safety-hook wiring test (~9 h) | `fleet_failure_modes.md` §7 | `ship` | `open` | **Ship:** three things built with a stated cost. Placed as a *Fleet Reliability* milestone |
| C-012 | Do NOT build an operator dashboard; build the blocked-work notifier | `operator_interface.md` §0, §6 | `ship` | `open` | the negative *is* the finding. **Ship:** both halves are concrete. Placed as a *Fleet Reliability* milestone |
| C-013 | Close the "evaluate Paperclip after Phase 4" gate and rewrite the item | `paperclip_assessment.md` §7 | `ship` | `closed` | `b9710d5` |
| C-014 | Adopt the eight cost-S, dependency-free interface/doctrine items | `bernstein_capability_mining.md` §5 | `ship` | `open` | case-by-case, not a bundle. **Ship:** §5 already names a home for each of the eight (rows 2/4/6/8/9/10/11/12) across five existing sprints plus one problem-statement amendment — phase-doc detail, not a sprint change |
| C-015 | Fix the missed-window assumption in the sprint plan — backwards, verified against the code | `fleet_failure_modes.md` §5.2 | `ship` | `closed` | `b9710d5` |
| C-016 | Design the stalled predicate as a three-way conjunction before workers are written | `paperclip_assessment.md` §4.4 | `reject` | `open` | claims the failure mode is live here today; **unverified**. **Reject:** folded into C-029 — the three-legged taxonomy supersedes the two-way framing, and one design does not need two homes |
| C-017 | Decide dedupe granularity as a ruling, not a build | `paperclip_assessment.md` §4.3, §6 | `requires review` | `open` | explicitly not a pair to build both of. **ALREADY TRACKED at issue #41**, whose *Proposed next action* is this exact ruling — worktree scan vs comment recency vs a real lock, decided once for both the bash and Python paths. No `D-` row: one item, one home |
| C-018 | Drop any uniqueness framing on subscription-auth-at-the-edge | `paperclip_assessment.md` §4.6 | `ship` | `closed` | `b9710d5` |
| C-019 | Reconsider giving up cross-machine failover for *all* work | `dedicated_edge_routing.md` §5, §7 | `ship` | `closed` | **RULED via `D-002` 2026-08-07** — pin to the initiating edge; the reconsideration is closed |

## Cycle 4 — 2026-08-06 · PROVISIONAL (PR #33 unmerged)

| ID | Candidate | Source | `decision` | `status` | Note |
|---|---|---|---|---|---|
| C-020 | Restate differentiator #1 on the credential, not the topology — state both halves together | cycle-4 pool | `ship` | `open` | **Ship — already applied** at `f2b80a6`; `problem-statement.md` §1 states both halves together |
| C-021 | Cost differentiator #1 with the self-hosted-CI-runner warning; rule on the laptop trust boundary | cycle-4 pool | `requires review` | `open` | **`D-003`** — the costing is a `problem-statement.md` edit and the boundary is a ruling; neither is automation's |
| C-022 | Settle whether a Temporal worker can be prevented from polling a queue it should not serve — **before** the pinned-edge design | cycle-4 pool | `ship` | `open` | bears directly on C-010. **Ship:** an empirical spike with an artifact, not a preference — run it before `D-001` is ruled. Temporal Integration phase-doc detail |
| C-023 | Record that self-hosted Temporal ships `noopAuthorizer` by default; the namespace is the only credential boundary offered | cycle-4 pool | `ship` | `open` | security-relevant to the two-server split. **Ship:** natural home is `stack_reference.md` § *What we do NOT use*, which is human-in-the-loop — Temporal Integration phase doc meanwhile |
| C-024 | Split the sprint plan's *Tools to Evaluate* into backbone comparators and edge runtimes | cycle-4 pool | `ship` | `open` | the row whose evidence the held item concerns. **Ship — already applied**; the sprint plan carries both categories |
| C-025 | Give "nearest neighbour" an axis: bernstein by architecture, OpenClaw by thesis | cycle-4 pool | `ship` | `open` | **Ship — already applied** at `f2b80a6`; `problem-statement.md` § *The nearest neighbor* carries the axis table |
| C-026 | Add OpenClaw as ASSESSED-and-closed, not as an evaluation gate | cycle-4 pool | `ship` | `open` | **Ship — already applied**; listed under *Edge runtimes*, ASSESSED with no evaluation gate |
| C-027 | Add Hermes under a new edge-runtimes heading | cycle-4 pool | `ship` | `open` | an addition, not a rewrite. **Ship — already applied**; listed under *Edge runtimes* |
| C-028 | Plan the three pre-worker recovery items as ONE design session | cycle-4 pool | `ship` | `open` | **Ship:** one session producing one restart-recovery contract. Placed as a *Fleet Reliability* milestone |
| C-029 | Adopt the three-legged liveness taxonomy: stalled / looping / stranded | cycle-4 pool | `ship` | `open` | supersedes C-016's two-way framing. **Ship:** placed as a *Fleet Reliability* milestone |
| C-030 | Unblock quota-headroom — derivable from observed cap-errors, no provider telemetry needed | cycle-4 pool | `ship` | `open` | **Ship:** the telemetry transfers, the rotation does not — we hold one subscription. Placed as a *Fleet Reliability* milestone |
| C-031 | No fallback queue: an unresolvable assignee PARKs with a typed event, never silently falls back | cycle-4 pool | `ship` | `open` | a negative design decision. **Ship:** it is queue topology, so Temporal Integration owns it — phase-doc detail |
| C-032 | Amend `workflow-scripts.md` § Composition — it justifies two mechanisms with an argument supporting only the first | cycle-4 pool | `requires review` | `open` | **`D-004`** — a standards amendment against two binding documents, and `architectural_standard.md` §3's `author ≠ judge` seam restates the same over-claim. Agents surface, humans write |
| C-033 | Withdraw or downgrade `case_against.md`'s D7 — contradicted by its own primary source | cycle-4 pool | `ship` | `open` | **Ship:** a bounded correction to one paper with a named source. Needs a `research-refresh` dispatch against `case_against.md`, not a sprint item |
| C-034 | Switch `review-pr` to a cross-family judge — self-preference bias is causally linked to self-recognition | cycle-4 pool | `requires review` | `open` | **`D-005`** — every genuinely cross-family option needs a second provider credential, which is a thesis-level commitment, not a one-line change |
| C-035 | Run E1b first — classify 30 PRs' disposition items to read out the judge's marginal yield | cycle-4 pool | `ship` | `open` | cheap, and it sizes C-034. **Ship:** reads existing logs and PR threads, no new dispatches. Added as a Continuous Process Improvement milestone |
| C-037 | Cross-machine failover — **a third option**: pin the credential, not the work | amends C-019 | `ship` | `closed` | **RULED via `D-002` 2026-08-07** — the proxy option excludes `claude-cli` by name, so it does not apply here |

## Evicted from the sprint plan — 2026-08-06

Nine ideas that lived in the sprint plan under *Future Ideas (Not Yet Committed)*, some since April. **None was ever committed to and none had been triaged** — a candidates list wearing a plan's clothes, which is exactly the shape this file exists to hold. Moved verbatim in substance; the plan file is not the place to park an idea.

| ID | Candidate | Source | `decision` | `status` | Note |
|---|---|---|---|---|---|
| C-038 | Cross-project intelligence — aggregate CPI analysis across repos so a pattern in one informs another | sprint plan, Future Idea A | `reject` | `open` | needs centralized log collection or report aggregation. **Reject: delivered.** Continuous Process Improvement's *Cross-repo reporting* milestone centralises with source-repo metadata, so patterns spanning repos are already visible |
| C-039 | Workflow composition / chaining — an orchestrator running a pipeline of workflows end to end | sprint plan, Future Idea B | `reject` | `open` | **largely overtaken** — parent/child composition ships today. **Reject:** two live sprints cover it — Workflow Decomposition ships the composition and its standard, and a driver above parents is Autonomous Operation |
| C-040 | Project templates for `plan-new` — stack preferences and boilerplate decisions pre-made per project type | sprint plan, Future Idea C | `reject` | `open` | **Reject:** presupposes a settled stack reference, and `stack_reference.md` is explicitly seeded-not-complete pending a research pass. Re-propose once it lands and two projects want the same boilerplate |
| C-041 | Team scaling — per-user config overrides, aggregated CPI, role-based workflow access, onboarding | sprint plan, Future Idea D | `requires review` | `open` | bears on the SkyyNet multi-participant question. **`D-006`** — the four items cannot be sized until the repo/SkyyNet boundary is ruled |
| C-042 | Metrics dashboard over the JSONL logs — cost trends, efficiency, failure types, agent utilization | sprint plan, Future Idea E | `reject` | `open` | **tension**: cycle-4 evidence argues a blocked-work notifier over a dashboard. **Reject:** the tension resolves against it — `operator_interface.md` argues explicitly for the notifier, which C-012 carries |
| C-043 | `/rollback-cpi` — revert the last CPI PR and mark that pattern tried-and-failed | sprint plan, Future Idea F | `reject` | `open` | grows in value as CPI automation increases. **Reject:** CPI changes are human-ruled and already reversible by `git revert` plus an append to `cpi-decisions.md`, and the operation has never been performed once. Re-propose the first time a CPI change is reverted and the log fails to record why |
| C-044 | SkyyCommand AI decision engine — the lean-agent + rich-skill pattern applied to VM placement | sprint plan, Future Idea G | `reject` | `open` | out of this repo's scope; belongs to SkyyCommand. **Reject:** out of scope by the problem statement's own frame — this repo is the Jarvis edge, and VM placement is SkyyCommand's |
| C-045 | Prompt pattern library — capture phrasings that measurably produce better output | sprint plan, Future Idea H | `reject` | `open` | **Reject:** *measurably* is the blocker — nothing here can read out a phrasing's marginal yield, and `cpi-decisions.md` already records shipped prompt changes with their reasoning. Re-propose once C-035 shows the fleet can measure a prompt change at all |
| C-046 | `plan-new` greenfield — handle `git init`, initial commit and remote setup rather than requiring a repo | sprint plan, Future Idea I | `reject` | `open` | found during the 1Password vault manager test, 2026-04-11. **Reject: delivered.** `scripts/helpers/init-project.sh` runs `git init --initial-branch=main`, makes the initial commit and creates the GitHub remote; `plan-new` correctly requires an existing repo |

---

## Re-homed from GitHub Issues — 2026-08-09

Five open issues that were **proposals, not defects**, re-homed under [Architecture Standard § 4 Memory](../architectural_standard.md) — *"a PROPOSAL — capability that does not exist yet and would be added — goes to `candidates.md` and is NEVER an Issue, however clean its done-state looks."*

**Why they were filed as issues:** the selection rule in force when they were filed routed on *"did something change?"* and *"does it have a done-state?"* — and a proposal answers **no** and **yes**. `candidates.md` was explicitly excluded as a destination, so a proposal had nowhere else to go. That paragraph was corrected the same day this section was written.

**`decision` is deliberately blank on every row: these have been re-homed, not triaged.** Blank means triage has not happened, and `decision` is `plan-sprint`'s output alone. **Two of the five were filed by the operator's own session**, so this is not a dispatch-behaviour problem.

| ID | Candidate | Source | `decision` | `status` | Note |
|---|---|---|---|---|---|
| C-047 | Gate `vendor-standards.sh --check` on the merge path so a local edit to a vendored MIRROR standard cannot merge green | issue #55 | | `open` | Nothing is broken — the check works and is correct; this ADDS a gate. Split ruled: the committed-checksum half (local-edit detection) needs no upstream and is shippable; the upstream-divergence half is blocked on a read-only credential for a private repo, and the Testing Standard's freshness clause forbids gating a check that cannot establish its own baseline |
| C-048 | Per-file granularity in `install.sh`'s symlink targets, so a `tests/` dir beside a hook does not land in the live `~/.claude/hooks/` | issue #63 | | `open` | Nothing is broken — PR #58 placed the tests successfully elsewhere and documented the divergence. Changes the documented 7-target strategy on every machine, so it is an architecture decision. Constrained by C-049; rule them together |
| C-049 | Point `~/.claude/*` at a worktree pinned to a ref instead of at the git working tree, making `git pull` the deploy step | issue #64 | | `open` | Today the working tree IS production: whatever branch is checked out is live, and an edit takes effect before commit. **The value is not mainly safety** — it is that when CDF grows to server + multiple edges, adding rings becomes a config change rather than a re-architecture. Costs instant prompt iteration. Same architecture surface as C-048 |
| C-050 | Derive declared roster and inventory counts rather than restating them in prose | issue #70 | | `open` | **The live instance is already fixed** (`README.md` said 10 workflows, there are 9 — corrected 2026-08-09); what remains is the check, which is capability. `architectural_standard.md:46` already states the principle — *"a constant restated in two places diverges silently"* — and nothing enforces it |
| C-051 | A marketing workflow — outward positioning, with inward feedback into the problem statement and roadmap | issue #28 | | `open` | Filed 2026-08-05 and parked ever since. Wholly unbuilt capability; it was never a defect on any reading |

---

### Added 2026-08-09 — re-homed from issue #36

| ID | Candidate | Source | `decision` | `status` | Note |
|---|---|---|---|---|---|
| C-052 | Close the V2 port's ranked coverage gaps — eight named functions, ranked by risk, produced by PR #31 as its *"state the untested surface, do not build it"* deliverable | issue #36 | | `open` | **A proposal, not a defect: "we have no test for X" is not a defect in X** — nothing claims any of these eight is wrong. **It had already decayed unnoticed**, which is why it left the issue queue: item 2 (`render()`) is now covered by `test_shared_render_catches_a_digit_bearing_placeholder`, landed via unrelated work; item 8 (`pr_number_from_url`) has a happy-path test but still none for its deliberate raise; the issue's own caveat *"without closing #30 none of it runs on the merge path"* is moot — **#30 is closed and the gate ships**. Still at zero: **item 1 `paper_currency`** and **item 4 `pass_numbers`**. Items 5-7 remain blocked on an integration tier that does not exist; building the one `tmp_path` git-repo fixture unblocks all three at once. **TRIAGE NOTE — item 1 is separable and stronger than the rest, and should probably be ruled `ship` on its own merits:** `paper_currency` computes staleness verdicts a prompt instructs the model to obey without recomputing, and its own docstring records why it exists — *"A model once marked four of eight papers past window when one was… Correct arithmetic, wrong anchor, and the error was invisible because the reasoning looked sound."* Documented past failure, authoritative output, zero tests, and nothing is likely to touch `research_activities.py` soon — which is precisely the case where a targeted one-off beats opportunistic coverage. The other seven are better taken at the point of change |

---

## Where things stand

**Nothing is untriaged.** All 45 rows carry a decision as of the 2026-08-06 `plan-sprint` pass: **25 `ship`**, **8 `requires review`**, **12 `reject`**.

**The `requires review` rows are the live queue.** Seven are filed as `D-001`–`D-006` in [`direction.md`](direction.md); **C-017** is not, because issue #41 already tracks that ruling and one item does not get two homes. Nothing here moves until the operator rules.

**Six `ship` rows were already applied before triage** — C-020, C-024, C-025, C-026 and C-027 landed in `f2b80a6` and the sprint-plan comparator split, and C-007/C-008/C-009/C-013/C-015/C-018 in `b9710d5`. A candidate can be delivered before anyone gets round to ruling it; recording that is cheaper than re-deriving it.

**12 rejected, and the reasoning is the point.** Three assumed **Temporal Cloud**, settled 2026-07-12 and unwritten at the time, so a research cycle costed out a product ruled out three weeks earlier — now recorded in `stack_reference.md`. Four more were **already delivered** by shipped work. The rest name what would have to change for them to be re-proposed.

**Known gap in this file's own model:** `status` is set by "a later process" — `plan-feature` on landing, or the build that completes it. A `reject` never lands in a phase doc and no build completes it, so nothing will ever close one. The 2026-08-06 rejects therefore sit at `status: open`, which reads as outstanding work when it is not.
