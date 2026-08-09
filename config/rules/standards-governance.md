# Standards Governance

## Architectural decisions: standards, not ADRs

Architectural decisions are captured as standards documents in `docs/standards/<topic>.md`, not as separate numbered ADR files in `docs/standards/architecture/`. Standards documents serve the same role ADRs do — they document binding decisions about how things should be done, with rationale and alternatives considered.

Do NOT propose creating `docs/standards/architecture/adr-NNN.md` files when adding a `docs/standards/<topic>.md` file accomplishes the same goal. The architecture-decisions skill's methodology still applies (trade-off analysis, rationale, alternatives considered, consequences) — but the artifact is a standards doc, not a numbered ADR. The `docs/standards/architecture/` directory is reserved for high-level system-architecture descriptions and tech-stack overviews, not per-decision artifacts.

## Standards governance — human-in-the-loop

Standards documents (`docs/standards/`, `docs/standards/architecture/`) are a curated product with human-in-the-loop control. Autonomous workflows and agents may SURFACE standards implications (gaps, drift, deviations, ADR candidates) but must NOT auto-create, auto-modify, or auto-stub standards artifacts. All standards changes flow through the interactive session for human review before merge.

### `docs/standards/architecture/research/` is a WORKING SURFACE, not a standards artifact (binding)

**Everything under that directory is exempt from the paragraph above.** `candidates.md`, `direction.md`, `synthesis.md`, `topics.md` and `raw/` are **queues and evidence**, not curated binding product: they are appended to continuously, they carry no rules anyone conforms to, and their whole purpose is to accumulate what has *not* yet been ratified.

**Autonomous runs MAY write there, by the routing in [`finding-routing.md`](../../docs/standards/finding-routing.md) § 7** — a research run appends papers and candidates, a producing run places a proposal it surfaced, `plan-sprint` appends a `direction.md` row. **What stays human-only is the `status` flag on a `direction.md` row and the `decision` flag on a candidate**: those are rulings, and a ruling is the thing this rule exists to protect.

**Why this is a carve-out and not a loophole.** The rule above protects documents that *state how things must be done*. Nothing under `research/` does — it states what has been found and what is being proposed. Applying a curated-product rule to an inbox is what produced the failure it was written to prevent: a proposal with no permitted writer stops existing.

**This was already being violated, invisibly, and that is the evidence.** The research family has appended to `docs/standards/architecture/research/` every cycle for weeks. Both rules were binding and they contradicted each other silently, because a research run's output is a PR and a PR-for-review satisfies human review by a *different* rule. It surfaced only when a `review-pr` run hit the same wall from the other side and had three correctly-classified proposals it was not permitted to place.

**What counts as "human review before merge" — this sentence exists because two passes of one pipeline read it oppositely, one pass apart.** A dispatch **opening a PR** against the standards repo, and merging nothing, **SATISFIES this rule**: the PR-for-review gate IS the human-in-the-loop, and nothing reached a default branch unreviewed. What the rule forbids is a standards change that LANDS without a human — a direct commit to the default branch, or a self-merge. **So when a build brief explicitly names a standards file as an in-scope edit, the brief wins and the mechanism is a PR** — including a PR in a different repository. Declining the edit outright is the *wrong* reading and costs an operator ruling to unstick. *(Observed 2026-08-08: a draft pass declined a standards edit citing this rule; the refine pass made it as a PR in the upstream repo. The refine pass was right.)*

**Planning artifacts (phase docs, `roadmap.md`, sprint.md, epic breakdowns) are explicitly NOT covered by this rule** — they are dispatch-scope and engineers MAY edit them autonomously. When a phase doc and a standard contradict, the engineer SHOULD update the phase doc to remove the contradiction in the dispatch's PR (since the standard is binding) AND surface the standards-side amendment as a candidate for human review. This avoids the "next sprint reads the phase doc, doesn't notice the tension, flips a coin" failure mode.

### Sprint plans are the exception — human-in-the-loop only (binding)

`sprint.md` / `sprints.md` (or equivalent sprint execution plan) MUST NOT be edited by autonomous dispatches or non-operator-reviewed sessions. It is the **exception** to the planning-artifacts carve-out above: phase docs, `roadmap.md` and epic breakdowns remain dispatch-scope — but the sprint plan is the operator's cross-domain sequencing surface, and every edit (new item, re-sequencing, checkbox flip, hour re-total) happens under human review.

**How autonomous work interacts with sprints:** dispatches and non-operator-reviewed sessions **surface** sprint-item candidates — they never write the sprint file themselves. A candidate discovered mid-dispatch (a new item, a re-order, a done checkbox) is raised in the PR body or a handoff for human-reviewed editing; it is **not** committed to the sprint file by the dispatch.

**Why:** the sprint plan is the operator's mental model of what's being built when. Uncontrolled edits from parallel sessions and engineer runs erode that model faster than any single edit improves it — the cost is the operator losing the thread, not one wrong line. Documented failure modes that drove this rule: engineer runs placing items in the wrong sprint or unrelated ones, appending history-lesson prose to sprint items ("used to be here but that didn't work"), and continued flag/repair cycles that eroded trust.

**Override:** if a specific revision-workflow prompt explicitly authorizes editing the sprint file (e.g., an early-draft iteration the operator knows will be reviewed), that override applies — the PR-for-review gate still satisfies HiL. The default remains: no autonomous edits.

**Breaking it looks like:** an engineer dispatch or non-human-reviewed session committing a new or edited sprint-file line; a checkbox flipped in the sprint file by an autonomous run without human sign-off; a new sprint item created by a dispatch instead of surfaced for human-reviewed insertion.

## CPI Decisions Log

Persistent record of every CPI decision (ship / defer / reject) lives at `~/Repos/claude-dot-files/docs/development/cpi-decisions.md` (or `/opt/skyy-net/claude-dot-files/docs/development/cpi-decisions.md` on the VM). The log preserves context across sessions so deferred findings don't slip away between cycles.

**When CPI cycles produce findings:**
1. Discuss in the interactive session, decide ship/defer/reject for each finding
2. SHIPPED items get implemented + committed
3. DEFERRED items get appended to `cpi-decisions.md` with explicit watch-criteria (e.g., "ship on second occurrence")
4. REJECTED items get appended with reasoning so future reviewers don't re-litigate

**Before a new CPI cycle:** scan the DEFERRED sections. New findings that match prior watch-criteria become Tier-1 ship candidates with confirmed evidence. New findings unrelated to prior deferrals are evaluated fresh.

**Append-only:** entries don't get deleted. When a previously-deferred item finally ships, the original deferral entry gets amended with "→ SHIPPED at <commit>" rather than removed. This preserves the calibration history (how often did we correctly defer noise vs incorrectly defer real patterns).

The `review-runs.sh` and `review-sprint.sh` workflows automatically cross-reference the log when generating new reports — findings that match prior deferrals are flagged as recurrences with the original context.

For the full CPI cycle methodology, see `docs/guide/cpi-cycle.md`.
