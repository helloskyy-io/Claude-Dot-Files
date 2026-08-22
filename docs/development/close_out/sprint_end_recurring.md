# Sprint-End Recurring Items

This repo's instance of the list [Documentation Standard § Sprint Close-Out](../../standards/documentation/documentation_standard.md) requires. The standard requires that a list EXIST; it does not say which checks are on it. This is ours.

**Close-out is a verification gate, not a work phase.** One checkbox, two conditions: these checks were run for the sprint, and every finding they produced was dispositioned — fixed, rejected with reasoning, or placed. *Run* and *dispositioned* are different claims and only the second closes a sprint.

## What earns a place on this list (binding)

**Only a check for something that ARRIVES ON ITS OWN SCHEDULE and has no other trigger.** Upstream publishes a standards amendment when it publishes one; a research paper falls due on the date written into it. No pull request of ours causes either, and nothing else is watching.

**Everything a pull request can trigger belongs to the pull request.** Dead code, stale prose, a map entry that drifted, a guard whose population narrowed — `review-pr` and the merge-path suite see those on the diff that introduced them, while the author still has context. A periodic sweep for that class is re-finding what should already have been placed, and **if a sweep does find one, the finding is not the drift — it is that the per-PR gate missed it.** Fix the gate, not the calendar.

**Consequence, and it is the whole point:** this list stays short and close-out stays about an hour. A recurring list that accepts anything becomes the ledger it exists not to be.

**Identifier convention:** items are `R1`, `R2`, `R3`… (`R` for recurring), never sprint-prefixed. Adding an R-item needs no Documentation Standard amendment; changing the close-out *shape* does.

---

## R1. Re-vendor the standards, and read the diff

`bash scripts/helpers/vendor-standards.sh --check`

**Why it qualifies:** MDC-Master-Planning amends a standard when it amends one. Nothing in this repo triggers it and no PR here can surface it. **Measured 2026-08-20:** the vendored Documentation Standard was six days behind and missing a *binding* rule ratified that morning — phases are cited by name, never by number — while `--check` reported green, because it compares against the pinned SHA rather than upstream's HEAD. The check passing is not the same as the copy being current.

**Disposition, not just execution:** an upstream amendment can invalidate something built here. Read the diff and rule on each change — conformant already, needs work here, or needs pushing back upstream. Re-vendoring without reading the diff satisfies *run* and fails *dispositioned*.

## R2. Re-validate research papers that have fallen due

Papers carry a revalidation interval and a validated-on date. A three-week paper validated on the 7th is due on the 28th whether or not anyone opens it.

**Why it qualifies:** the due date arrives on the calendar's schedule. **A paper past its date is not wrong — it is unverified**, and the failure mode is that it keeps being cited as current evidence. The remedy is a `research-refresh` run, not a note.

**Disposition:** for each paper past due — refreshed, re-dated with reasoning, or retired. A due paper left due is not a disposition.

## R3. Read what Claude Code shipped, and rule on each capability

Anthropic ships Claude Code releases and feature announcements on its own cadence. Read what landed since the last close-out, and rule on each item that touches this fleet.

**Why it qualifies:** nothing here triggers a Claude Code release and no pull request of ours surfaces one. This whole repo is built *on* that product, so a capability shipping upstream silently changes what is worth building here, and nothing is watching.

**The failure is bidirectional, which is what makes it worth a standing check.** Build something the platform already provides and the work is wasted and has to be maintained forever. Miss something that would simplify the fleet and the design drifts further from the platform every cycle, so adopting it later costs more than adopting it now. **Neither failure announces itself** — both look like ordinary progress.

**Also in scope: what the platform changes about our own arguments.** [`problem-statement.md`](../../standards/architecture/problem-statement.md) § *Affordability is the enabler* rests on a pricing position that Anthropic has moved three times in a year. That section states the assumption and dates it; this check is what keeps the date honest. **Measured 2026-08-22:** the pause it depends on was two months old and unverified when the document was sent to two readers outside this project.

**Disposition, per capability:** adopt (and name where), reject with the reason, or defer with the condition that would bring it back. **A release read and not ruled on is not a disposition** — the point is deciding what it changes here, not knowing it happened.

---

**Not on this list, deliberately.** Dependabot: this repo has no dependency manifest and no alerts configured, so there is nothing arriving on that schedule. If that changes, it earns an R-item; it does not get one in advance.
