# Standards Governance

## Architectural decisions: standards, not ADRs

Architectural decisions are captured as standards documents in `docs/standards/<topic>.md`, not as separate numbered ADR files in `docs/architecture/`. Standards documents serve the same role ADRs do — they document binding decisions about how things should be done, with rationale and alternatives considered.

Do NOT propose creating `docs/architecture/adr-NNN.md` files when adding a `docs/standards/<topic>.md` file accomplishes the same goal. The architecture-decisions skill's methodology still applies (trade-off analysis, rationale, alternatives considered, consequences) — but the artifact is a standards doc, not a numbered ADR. The `docs/architecture/` directory is reserved for high-level system-architecture descriptions and tech-stack overviews, not per-decision artifacts.

## Standards governance — human-in-the-loop

Standards documents (`docs/standards/`, `docs/architecture/`) are a curated product with human-in-the-loop control. Autonomous workflows and agents may SURFACE standards implications (gaps, drift, deviations, ADR candidates) but must NOT auto-create, auto-modify, or auto-stub standards artifacts. All standards changes flow through the interactive session for human review before merge.

**Planning artifacts (phase docs, roadmap.md, loose-ends entries, sprint docs, epic breakdowns) are explicitly NOT covered by this rule** — they are dispatch-scope and engineers MAY edit them autonomously. When a phase doc and a standard contradict, the engineer SHOULD update the phase doc to remove the contradiction in the dispatch's PR (since the standard is binding) AND surface the standards-side amendment as a candidate for human review. This avoids the "next sprint reads the phase doc, doesn't notice the tension, flips a coin" failure mode.

## CPI Decisions Log

Persistent record of every CPI decision (ship / defer / reject) lives at `~/Repos/claude-dot-files/docs/development/cpi-decisions.md` (or `/opt/skyy-net/claude-dot-files/docs/development/cpi-decisions.md` on the VM). The log preserves context across sessions so deferred findings don't slip away between cycles.

**When CPI cycles produce findings:**
1. Discuss in the interactive session, decide ship/defer/reject for each finding
2. SHIPPED items get implemented + committed
3. DEFERRED items get appended to `cpi-decisions.md` with explicit watch-criteria (e.g., "ship on second occurrence")
4. REJECTED items get appended with reasoning so future reviewers don't re-litigate

**Before a new CPI cycle:** scan the DEFERRED sections. New findings that match prior watch-criteria become Tier-1 ship candidates with confirmed evidence. New findings unrelated to prior deferrals are evaluated fresh.

**Append-only:** entries don't get deleted. When a previously-deferred item finally ships, the original deferral entry gets amended with "→ SHIPPED at <commit>" rather than removed. This preserves the calibration history (how often did we correctly defer noise vs incorrectly defer real patterns).

The `review-runs.sh` and `sprint-review.sh` workflows automatically cross-reference the log when generating new reports — findings that match prior deferrals are flagged as recurrences with the original context.

For the full CPI cycle methodology, see `docs/guide/cpi-cycle.md`.
