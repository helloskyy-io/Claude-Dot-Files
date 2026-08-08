# Standards Governance

## Architectural decisions: standards, not ADRs

Architectural decisions are captured as standards documents in `docs/standards/<topic>.md`, not as separate numbered ADR files in `docs/standards/architecture/`. Standards documents serve the same role ADRs do — they document binding decisions about how things should be done, with rationale and alternatives considered.

Do NOT propose creating `docs/standards/architecture/adr-NNN.md` files when adding a `docs/standards/<topic>.md` file accomplishes the same goal. The architecture-decisions skill's methodology still applies (trade-off analysis, rationale, alternatives considered, consequences) — but the artifact is a standards doc, not a numbered ADR. The `docs/standards/architecture/` directory is reserved for high-level system-architecture descriptions and tech-stack overviews, not per-decision artifacts.

## Standards governance — human-in-the-loop

Standards documents (`docs/standards/`, `docs/standards/architecture/`) are a curated product with human-in-the-loop control. Autonomous workflows and agents may SURFACE standards implications (gaps, drift, deviations, ADR candidates) but must NOT auto-create, auto-modify, or auto-stub standards artifacts. All standards changes flow through the interactive session for human review before merge.

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
