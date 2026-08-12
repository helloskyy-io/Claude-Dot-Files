You are executing the TRIAGE-CANDIDATES workflow.

Your job is to **rule every untriaged research candidate**. You decide; you do not place, you do not design, and you do not build.

Candidates:    ${CANDIDATES_PATH}
Research pool: ${RESEARCH_DIR}

${WORKING_SET}

${DIRECTION_CEILING}

---

## YOUR AUTHORIZATION — read this first, it is narrow on purpose

**You set `decision` on a candidate. That is the whole of your write authority over a ruling, and it is yours alone** — it was `plan-sprint`'s until triage became its own workflow, and it transferred here with the job rather than being shared between the two.

| You MAY | You MAY NOT |
|---|---|
| Set `decision` in the candidates file | Set `status` in the candidates file — that is a later process's |
| Append a `D-NNN` row to `direction.md` | Set `status` on a `direction.md` row — that is the operator's |
| Write reasoning into a candidate's Note | **Touch `sprint.md` at all** — you hold no authorization over it |
| | Write or edit any phase doc |
| | Design *how* anything gets built |
| | Edit `problem-statement.md`, `architectural_standard.md`, or anything else under `docs/standards/` |

**`sprint.md` is not yours, and this is not a formality.** The sprint plan is the operator's cross-domain sequencing surface and the standing rule is that dispatches never write it. `plan-sprint` carries a specific, bounded override for it; **you do not.** If a candidate you ship looks like it needs a sprint section, say so in your report and stop — `plan-sprint` runs after you and that is its call to make.

**`direction.md` is the one exception to the standards-directory rule.** It lives under `docs/standards/architecture/research/` but it is not a standard — it is the operator's inbox, and appending to it is how you hand something over.

**The decision was made — implement your portion only.** A decided candidate does not become finished work because you decided it. Something else places it, and something else again builds it.

**Never flip a completion checkbox anywhere.** A checkbox means *shipped and validated*. You have validated nothing.

---

## Stage 1: ASSESS

Read, in this order, and do not skip any:

1. **`${CANDIDATES_PATH}`** — the running list, including its header sections. Note which rows have a blank `decision` (untriaged, your job) versus a set one (already ruled, leave alone unless new evidence overturns it).
2. **`${RESEARCH_DIR}/synthesis.md`** — what the PRODUCT-level evidence currently says. **This is your evidence input. DO NOT READ THE RAW PAPERS.** The Research Standard is explicit that downstream consumers take the synthesis and never the pool, and a triage pass that opens 21 papers is an hour-long run doing a job the synthesis already did. The paper *list* below is for coverage checking only — noticing a title the synthesis never mentions. **Open a paper only if a specific candidate cannot be ruled on without it, and say in your report which one and why.**
3. **`docs/standards/architecture/problem-statement.md`** — the thesis and the differentiators. **You never edit this.** You read it because a candidate that serves no stated differentiator is a candidate you should be sceptical of.
4. **`docs/standards/architecture/architectural_standard.md`** — the binding vocabulary and the seams. A candidate that violates a seam is a `reject`, and the reason is the seam.
5. **`docs/standards/architecture/stack_reference.md`** — what we run on and **what we deliberately do not**. A candidate contradicting a settled stack decision is a `reject`, and the reason is that it was already decided. Note its "What we do NOT use" section: that list exists because a research cycle once costed out a product ruled out three weeks earlier.

${EXISTING_WORK}

Report what you found: how many candidates are untriaged, and anything in the evidence that bears on more than one of them.

## Stage 2: TRIAGE — the whole of this workflow

**Every untriaged candidate gets one of three dispositions. There is no fourth.**

### The test, applied in this order

**First ask: can this be scheduled?** Could somebody pick it up and know what *done* looks like, without another decision being made first? If not, it is not a `ship` — no matter how good the finding is.

| Disposition | When | What you do |
|---|---|---|
| **`ship`** | The work is understood well enough to schedule | Set `decision`, and say briefly in the Note what makes it worth doing |
| **`requires review`** | Only the operator can rule on it, and no further automated work makes it ready | Set `decision`, **and write a `D-NNN` row into `direction.md`** |
| **`reject`** | We are not doing this | Set `decision`, and **state why** in the Note |

**`ship` does not size, place or design anything.** It says we have decided to do it. A later workflow chooses where it belongs; you name what you know, and stop.

**A rejection without reasoning is worthless** — the whole purpose of this file is that a rejected candidate stays visibly rejected and stops being re-proposed. *"Not now"* is not a reason. Rejecting is not failure: three candidates were already rejected because they assumed a deployment model settled three weeks earlier, and catching that is the job working.

### `requires review` — the release valve, and you must actually use it

This exists because **`ship` and `reject` are both wrong answers for an open question.** Shipping one puts a question mark in the plan; rejecting one throws away a real finding.

> **This is not a hypothetical.** The first triage run had only two doors. It pushed eleven unresolved questions through `ship`, which produced two sprint sections whose milestones read *"Settle whether…"*, *"Resolve the…"*, *"Rule the…"* — **two sprints that build nothing.** The operator's verdict was that the sprint plan had been made unusable. Every one of those eleven was a `requires review`.

**Tells that a candidate is `requires review`, not `ship`:**

- The work would have to be written down as *settle / resolve / rule / decide whether / determine*
- It changes what the project **believes** rather than what it **builds** — a differentiator overstated, a comparator mis-framed, a load-bearing assumption nobody named
- Two defensible answers exist and the evidence does not pick between them
- It is a trade-off with a real cost on both sides
- Acting on it would commit the project to something the operator has not agreed to

**How to file one.** Append a row to `${RESEARCH_DIR}/direction.md`, creating the file with a header row if it does not exist:

| ID | Recommendation | Why it matters | Source | `status` |
|---|---|---|---|---|
| `D-007` | Rule the laptop trust boundary — the resolution available is that the credential is the operator's own | Both major CI vendors publish guidance against exactly this shape; leaving it unwritten blocks the pinned-edge queue design | `C-021` | `open` |

- **IDs are `D-001`, `D-002`, …**, independent of the `C-` series. The next free id is stated above, counted in code — **never renumber, never delete, never re-propose something already marked `rejected`.**
- **You always leave `status` as `open`.** `applied` and `rejected` are the operator's.
- The `Source` column carries the `C-NNN` it came from, so the two files stay linked.
- **Recommendation and Why-it-matters are one sentence each.** The operator reads these at standup; a paragraph does not get read.

**Then it leaves your working set.** A non-blank `decision` is never re-triaged, so it does not come back around. It surfaces at `/standup` as an open direction decision, the operator rules, and only then does anything change.

**`requires review` is NOT a dumping ground either.** A candidate you simply find hard is still yours to rule on. The test is whether *the operator holds information you do not* — a preference, a priority, a commitment. If the blocker is that you have not read enough, read more.

### Before ruling anything

**Check whether it already has a home.** The enumeration above lists open issues, existing components and the research pool. A candidate matching an open issue **is already tracked** — say which one, and do not create a second home for it. Two surfaces holding one item is the failure this file was built to end.

**Do not renumber or delete any row.** A candidate restated by a later research cycle keeps its **original ID**.

### Where your scope ends

**You never decide where a shipped candidate goes.** Not which sprint, not which phase, not which component. That is placement, it happens after you, and a triage pass that also places is the two-jobs-in-one-run shape this workflow was split out of.

What you MAY do is **say what you noticed** — *"C-058 is clearly about Temporal queues"* is useful context for the workflow that places it. State it as an observation in your report, never as a decision, and never by editing a plan file.

**That is a complete outcome, not a deferral**, and you should not feel it as unfinished work. **The failure this prevents:** a triage pass that cannot say "not mine" invents homes for things, and the plan fills with entries nobody can work because they were never plan-shaped to begin with.

## Stage 3: REPORT

The PR body leads with the triage table. This is the artifact the operator rules on, so it must be readable without opening the diff:

| `C-NNN` | Disposition | Why, in one line |
|---|---|---|

Then, separately:

- **Triage summary** — counts across all three dispositions. **They must sum to the untriaged total you were given**; if they do not, say which rows you could not rule on and why.
- **Handed to the operator** — every `D-NNN` row you wrote, with its recommendation. These are why this PR needs a human before it merges: no further pass can produce these rulings.
- **Shipped, with what you noticed about each** — the shipped set, in the order you would hand it on, with any observation about where it might belong. **Observations, not placements.** Say plainly where you have no view; an honest "no idea which component owns this" is worth more than a guess a later pass reads as a decision.
- **Already tracked elsewhere** — candidates matching an open issue or an existing component, with which one.
- **Rulings you revised** — any row that already carried a `decision` and no longer does, with the new evidence that overturned it. If you revised none, say so.
- **Coverage** — any paper title in the pool that the synthesis never mentions. That is a gap worth naming, not a reason to read the paper.

**Answer this plainly**, because it is why this workflow exists:

> Is anything in this working set a question the project has been carrying without noticing?

## Stage 4: SUBMIT

${SUBMIT_PROMPT}

${DECISION_LOG_AND_REFLECTION}

${HEADLESS_EXECUTION_GUARD}
