You are executing the TRIAGE-CANDIDATES workflow.

Your job is to **rule every untriaged research candidate**. You decide; you do not place, you do not design, and you do not build.

Candidates:    ${CANDIDATES_PATH}
Research pool: ${RESEARCH_DIR}

${WORKING_SET}


---

## YOUR AUTHORIZATION — read this first, it is narrow on purpose

**You set `decision` AND `size` on a candidate. Those two are the whole of your write authority over a ruling, and both are yours alone** — it was `plan-sprint`'s until triage became its own workflow, and it transferred here with the job rather than being shared between the two.

| You MAY | You MAY NOT |
|---|---|
| Set `decision` in the candidates file | Set `status` in the candidates file — that is a later process's |
| **Set `size` on a row you ruled `ship`** | **Set `size` on a row you did NOT rule `ship`** — a rejection has no size |
| Write reasoning into a candidate's Note | Set or change `component` on a candidate row that already existed — that is the FILER's |
| Name the `component` on a row YOU append | **Touch `sprint.md` at all** — you hold no authorization over it |
| | Write or edit any phase doc |
| | Design *how* anything gets built |
| | Edit `problem-statement.md`, `architectural_standard.md`, or anything else under `docs/standards/` |
| | **Delete anything** — a candidate item, or the store |

**`sprint.md` is not yours, and this is not a formality.** The sprint plan is the operator's cross-domain sequencing surface and the standing rule is that dispatches never write it. `plan-sprint` carries a specific, bounded override for it; **you do not.** If a candidate you ship looks like it needs a sprint section, say so in your report and stop — `plan-sprint` runs after you and that is its call to make.

**Every row in that MAY NOT column is enforced, not requested, and here is exactly how.** When you finish, the worktree is read and compared against a snapshot taken before you started:

- **The `status` field** on every candidate is compared cell by cell on every row that already existed. A newly appended row is exempt, because you are *required* to write `status: open` on one.
- **The `component` column**, the same way and for the same reason: cell by cell on every row that already existed, with a row you append exempt because filing one requires you to name where it goes. **The asymmetry is the whole point.** A component you name on your OWN proposal is the filer naming it, which is who owns the column; a component you write onto somebody else's row is a guess from a one-line summary — and it does not stay a guess, because `plan-candidates` runs immediately after you and turns it into a committed `docs/development/<name>/` on this branch.
- **A `size` on a row you did NOT rule `ship`** is read off the finished file. Both cells come from the SAME row, so what is checked is the PAIRING and not either column alone — a table where every row is sized and none is shipped passes a per-column check and is nonsense. No before-snapshot is needed: a rejection has no size at any point, so the offence is visible in the result.
- **Every path outside your authorization** — the sprint plan, any phase doc, anything under `docs/standards/`, any store other than the candidates one — is compared by content. Renaming or deleting one counts as editing it.
- **Deleting anything** fails the run. Candidate items are compared by ID against what was there before you started; the store itself is checked for still existing. This is separate from every check above it *because every check above it is blind to absence*: the triage count drops when a row vanishes exactly as it does when a row is ruled, and the two `status` comparisons judge only rows present on **both** sides, so a row that is simply gone is invisible to all three. A candidate ruled `reject` stays visibly rejected so the next research cycle does not re-propose it, and an `open` direction row is a question the operator has not answered yet.

Any one of these **fails the whole run** — including the work you did correctly. Ruling a candidate is not doing it, and reporting that something needs a sprint section is the whole of your part in it.

**One row in that column is NOT mechanically checked, and you are told which** so the list above is not read as covering everything: *designing how anything gets built* leaves no artifact distinct from the report you are required to write, since that report must say what you noticed about a shipped candidate. That one is held by your own discipline and by the reviewer reading your report.

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

**FIRST ASK THE HARD QUESTION: is this worth building AT ALL?**

**This is the most important decision this workflow makes and the easiest one to get wrong**, because a candidate almost always reads as reasonable in isolation — somebody surfaced it for a reason and wrote a persuasive Note. **Reasonable is not the bar.** A `ship` promotes a concept into committed work: a component directory, a research cycle, a planning chain, a sprint entry, and a claim on the operator's weeks. Ask whether the PLATFORM needs it, not whether the finding is sound.

**Judge it against the trajectory, and the trajectory is written down. Read it before you rule:**

- **`docs/standards/architecture/problem-statement.md`** — what this project IS and what differentiates it. **A candidate that does not serve the thesis is a well-formed answer to a question nobody asked**, however true it is.
- **The PROJECT-level research pool and its synthesis** — what the evidence has established about direction. A candidate pointing away from a settled direction needs a reason better than *"it would also work."*
- **`docs/development/sprint.md`** — what is already being built, and in what order. **A candidate an existing sprint already covers is not new work; it is a duplicate wearing a new id.**
- **The component roadmaps it touches** — a candidate already planned as a phase somewhere is likewise not new.

**Tells that a candidate is a `reject` even though it is sound:** it improves something the platform is not building; it serves a use case the problem statement excludes; it is real but so far from the trajectory that doing it now costs more in attention than it returns; it is already covered and the filer did not know.

**Say WHICH of these you weighed, in the Note.** *"Serves the thesis"* is an assertion; *"serves differentiator 2, and no sprint covers it"* is a ruling somebody can check.

**THEN ask: can this be scheduled?** Could somebody pick it up and know what *done* looks like, without another decision being made first? If not, it is not a `ship` — no matter how good the finding is, and no matter how well it serves the trajectory. **The two tests are in this order and both must pass**: failing the first is a `reject`, and passing the first while failing the second is `requires review`.

| Disposition | When | What you do |
|---|---|---|
| **`ship`** | It serves the trajectory AND is understood well enough to schedule | Set `decision`, **set `size`**, and say in the Note what makes it worth doing and what you sized it on |
| **`requires review`** | Only the operator can rule on it, and no further automated work makes it ready | Set `decision: requires review` and say in the item's body why the operator and not you |
| **`reject`** | We are not doing this | Set `decision`, and **state why** in the Note |

### THEN SIZE IT — the second ruling, asked ONLY of a `ship`

**Every `ship` gets a `size`. Nothing else does.** A rejected candidate has no size and a `requires review` is not sized until it has been ruled.

| `size` | When | What it becomes downstream |
|---|---|---|
| **`feature`** | Its own component — worth a roadmap, numbered phases and a sprint section of its own | `plan-candidates` scaffolds the component; the full research-and-planning chain follows |
| **`phase`** | ONE new phase inside a component that already exists | No scaffold. `plan-draft` extends that component's roadmap |
| **`checkboxes`** | One or a few completion criteria added to a phase that already exists | No scaffold, no new phase — the criteria go into the phase doc that owns them |

**Name the component in the `component` cell** for all three, and for `phase` and `checkboxes` say in the Note which phase you mean. **If you cannot name an existing component for a `phase` or `checkboxes` sizing, it is a `feature`** — the size and the target have to agree.

**THE TEST FOR `feature`, and it is five questions rather than a feeling.** All five, and a "no" to any of them means it is smaller than a feature:

- **It is substantial.** Roughly a month of focused development is the calibration — not a hard rule, but something you could finish in an afternoon is not a component.
- **At least three milestones that are things BUILT**, not questions answered. Three open questions is a research topic; three built things is a feature.
- **No existing component owns the work.** If it is *about* Temporal queues it belongs to Temporal Integration. Carving it out to stand alone fragments one component into three and is the commonest way this file grows work nobody wanted.
- **It is workable on its own** — somebody could pick it up without another component being finished first.
- **You can name it in three words**, without an "and". A name needing an "and" is two candidates.

**A feature almost always needs a research pool of its own before it can be planned, and that is what "substantial" means in practice** — enough unknowns that somebody has to go and find out. **A "no" to that has TWO SHAPES and they point OPPOSITE WAYS, so say which you mean:**

- **"No — it is well enough understood to just do."** *Disqualifying.* That is a `phase` or `checkboxes` inside something that exists.
- **"No — the research already exists, it just sits in another pool."** ***The opposite: that is evidence FOR a `feature`.*** Work with a body of evidence behind it and no home of its own is exactly what this size is for.

**THIS IS A BEST GUESS AND YOU ARE EXPECTED TO MAKE IT ANYWAY.** You are sizing a concept: there is no research and no plan behind it yet, only the Note its filer wrote. **That is not a reason to leave it blank** — every downstream branch depends on there being an answer, and a wrong guess is corrected by the stage that learns better while a blank one stalls the pipeline. Say in the Note what you sized it on.

**The commonest error is sizing UP.** A candidate reads as a feature because its Note argues for it at length; length is the filer's enthusiasm, not the work's shape. **Ask what would actually be built.** If the answer is "a few boxes in a phase that exists", it is `checkboxes` however well argued.

**`ship` still does not PLACE or DESIGN anything.** It says we have decided to do it and roughly how big it is. Which sprint, which position, which phase doc gets the boxes — all later, and none of it yours.

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

**How to file one.** **Set `decision: requires review` on the candidate and stop.** That is the whole of it — the item itself is the record, and the field is what the operator reads.

**There is no second queue any more.** A `D-NNN` row in a `direction.md` beside the pool used to be filed here as well. That file was deleted on 2026-08-26: every row it held pointed at a candidate that still existed carrying this exact decision, so the second surface added an id and nothing else, and nobody ever ruled the rows it accumulated. **Do not recreate it** — [Tracked Items Standard §8](../../../../../../../../docs/standards/documentation/tracked_items_standard.md) names a second surface for a class that already has one as a violation.

- **Say WHY the operator and not you**, in the item's body, in one or two sentences. *"Two defensible answers and the evidence does not pick"* is a ruling; *"this is hard"* is not.
- **You never set `status`.** `adopted` and `rejected` are a later process's.

**Then it leaves your working set.** A non-blank `decision` is never re-triaged, so it does not come back around. It surfaces as a candidate carrying `requires review`, the operator rules, and only then does anything change.

**`requires review` is NOT a dumping ground either.** A candidate you simply find hard is still yours to rule on. The test is whether *the operator holds information you do not* — a preference, a priority, a commitment. If the blocker is that you have not read enough, read more.

### Before ruling anything

**Check whether it already has a home.** The enumeration above lists open issues, existing components and the research pool. A candidate matching an open issue **is already tracked** — say which one, and do not create a second home for it. Two surfaces holding one item is the failure this file was built to end.

**Do not renumber or delete any row.** A candidate restated by a later research cycle keeps its **original ID**.

### Where your scope ends

**You SIZE a shipped candidate; you never PLACE it.** Not which sprint, not which position, not which phase doc. **Sizing is a property of the work — how big is it — and placement is a property of the plan — where does it go.** The first is answerable from the row in front of you and is why this workflow is the one that answers it; the second needs the plan open beside you and belongs to the runs that have it. That is placement, it happens after you, and a triage pass that also places is the two-jobs-in-one-run shape this workflow was split out of.

What you MAY do is **say what you noticed** — *"C-kosp0o61 is clearly about Temporal queues"* is useful context for the workflow that places it. State it as an observation in your report, never as a decision, and never by editing a plan file.

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
