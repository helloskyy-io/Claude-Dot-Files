# Personal Tooling

Autonomous workflow scripts live at `~/Repos/claude-dot-files/scripts/workflows/temporal/scripts/`.

Run `/get-started` at session start for the workflow inventory, role definitions, and dispatch guidance. Full reference at `~/Repos/claude-dot-files/docs/guide/workflows.md`.

## The Python fleet is the fleet. Its scripts use UNDERSCORES.

Every workflow you dispatch is `scripts/workflows/temporal/scripts/*.sh` — a thin shim over `run_*.py`, which owns the CLI contract. Names use underscores: `plan_revision.sh`, `build_minor.sh`, `review_pr.sh`.

**`build.sh` and `research.sh` are the two names that also existed in the old fleet.** Always give a full path rather than a bare script name.

**`build-phase.sh` no longer exists as a script.** Implementing from a plan doc is `build.sh --phase <plan>` — the build parent extracts the plan's success criteria and verifies against them.

## Three bash workflows survive, and they are SUPPORTED, not frozen

The V1 bash fleet was deleted on 2026-09-04 once every one of its members had a working Python runner. **Three had none and remain in `scripts/workflows/`:**

- `plan-new.sh` — greenfield project definition (thirteen stages; nothing in the Python fleet covers it)
- `review-runs.sh` — CPI log analysis
- `review-sprint.sh` — whole-repo end-of-sprint review

**Binding:**

- **These three are the correct thing to dispatch for their capability.** They are not deprecated and not a fallback; there is no alternative yet.
- **Maintain them like any live script.** Fix defects in them. They share `scripts/workflows/common/` and `scripts/workflows/activities/`, which exist for them and are equally live.
- **The Python fleet still must not depend on them** — no reading their source for a value, no invoking them.
- **Porting them is real work, not tidying.** Deleting one without a successor removes a capability, so it needs an operator ruling rather than a cleanup pass.

**Why this rule reversed.** It previously read *"the bash fleet is FROZEN REFERENCE, it is not a topic, never modify them, never raise them as a consideration."* That was correct while the whole fleet was a backup awaiting deletion. It stopped being correct the moment eleven were deleted and three were not: a blanket "not a topic" turned three live, dispatchable workflows into scripts nobody was allowed to fix. **`review-sprint.sh` was dispatching `refactoring-evaluator` and `standards-auditor`, agents consolidated away on 2026-08-18** — a defect that sat in a supported workflow precisely because the rule forbade noticing it.

**The frozen framing also had a cost outside this repo.** `/get-started` advertised the old fleet for weeks after the Python fleet worked, so engineers in other repos dispatched V1 by following the tooling's own front door — one spent a 196-turn run against `build-phase.sh`'s retired agent roster, work that `build.sh --phase` would have reviewed correctly. A fleet nobody may discuss is also a fleet nobody notices is still being recommended.
