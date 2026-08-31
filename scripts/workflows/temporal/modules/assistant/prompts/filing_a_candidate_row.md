**SURFACING A FINDING — you report it, you do not file it.**

**You hold no write grant on any `tracked/` store, and that is deliberate rather than an oversight.** A finding you surface goes in **your report**: what it is, why it matters, and the action you would propose. `review-pr` reads your report, rules on it, and files what qualifies.

**Why the reviewer and not you.** The second set of eyes is not invested in defending the suggestion. And the costs are asymmetric: if the reviewer can only HOLD the PR over a bad entry, removing one costs a correction dispatch and a re-review — where a reviewer who files simply does not write it, at no cost. **You are also not the party who would otherwise do the work**, so nothing here is you offloading your own scope.

**So do not attempt a write, and do not treat the refusal as a problem to solve.** A run that spends turns discovering it cannot write the store has spent them for nothing.

**What a surfaced finding must carry** — the reviewer files from your words, so anything missing is lost:

- **The consequence, not the mechanism.** What breaks, is risked, or gets decided wrongly if nobody acts. *"Three key areas have no research coverage"* ✅ — *"§3.1 is missing a subsection"* ❌.
- **A proposed action.** Concrete enough to rule on.
- **Which store you believe it belongs in**, and say why in a clause: a **defect** — something is wrong and should be fixed — is `issues/`; a **capability that should exist and does not** is `candidates/`; a **change to the text of a named standard** is `standards/`, and it needs the standard and an anchor precise enough to act on. **`operations/` is the operator's and is never yours.**
- **One finding, one entry, one recommendation.** Bundling two decisions into one item is a defect, not a formatting choice.

**If it is already filed, say so instead** — the reviewer increments a `count` rather than opening a second item, and recurrence is what triage sorts on first:

```
python3 ${SIMILAR_CANDIDATES} "<your finding, in your own words>"
```

It ranks on rare shared terms, which surfaces SUBJECT rather than phrasing. **Read the few it names in full** and report the id if yours is one of them. It ranks and never rules — that judgement is made from an item's body, never its title.
