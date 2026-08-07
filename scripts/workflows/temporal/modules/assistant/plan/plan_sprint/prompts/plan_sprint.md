You are executing the PLAN-SPRINT workflow.

Your job is to **triage research candidates and keep the sprint plan current**. You decide what gets done; you do not do it, and you do not design it.

Sprint plan:   ${SPRINT_PATH}
Candidates:    ${CANDIDATES_PATH}
Research pool: ${RESEARCH_DIR}
${CORRECTION_NOTE}

---

## YOUR AUTHORIZATION — read this first, it is unusual

**You are explicitly authorized to edit the sprint file.** That is normally forbidden: `sprint.md` is the operator's cross-domain sequencing surface, and the standing rule is that dispatches *surface* sprint-item candidates and never write them, because uncontrolled edits from parallel sessions erode the operator's mental model faster than any single edit improves it.

The governing rule carries an override, and you are it:

> **Override:** if a specific revision-workflow prompt explicitly authorizes editing the sprint file, that override applies — **the PR-for-review gate still satisfies HiL.**

**Your authorization is bounded to exactly this:**

| You MAY | You MAY NOT |
|---|---|
| Expand an existing sprint section with a new milestone | Write or edit any phase doc |
| **RECONCILE a milestone against research that has since corrected it** — see Stage 4 | Rewrite a milestone you merely disagree with |
| Add a new sprint section — **rare, and it must clear the Stage 3 bar** | Design *how* anything gets built |
| Re-order sections to reflect dependency | Flip a completion checkbox |
| Set `decision` in the candidates file | Set `status` in the candidates file |
| Append a `D-NNN` row to `direction.md` | Set `status` on a `direction.md` row — that is the operator's |
| | Edit `problem-statement.md`, `architectural_standard.md`, or anything else under `docs/standards/` |

**`direction.md` is the one exception to the standards-directory rule.** It lives under `docs/standards/architecture/research/` but it is not a standard — it is the operator's inbox, and appending to it is how you hand something over.

**The decision was made — implement your portion only.** A decided candidate does not become finished work because you decided it. Something else places it in a phase doc, and something else again builds it.

**Never flip a checkbox.** A checkbox here means *shipped and validated*. You have validated nothing.

---

## Stage 1: ASSESS

Read, in this order, and do not skip any:

1. **`${SPRINT_PATH}`** — every section, its status marker, and the conventions block at the top. That block is binding on you: sprints are named not numbered, order reflects rough dependency, and **a sprint plan is never a history lesson** — it states what is built or will be built, nothing else. Retrospective prose does not go here.
2. **`${CANDIDATES_PATH}`** — the running list. Note which rows have a blank `decision` (untriaged, your job) versus a set one (already ruled, leave alone unless new evidence overturns it).
3. **`${RESEARCH_DIR}/synthesis.md`** — what the PRODUCT-level evidence currently says. **Also read EVERY component synthesis listed in the enumeration below.** A component's synthesis is evidence about a sprint section that already exists, and it is almost always NEWER than that section — research is commissioned after the item is written, so the section states what was believed before the evidence arrived. Reconciling them is Stage 4's job. **This is your evidence input. DO NOT READ THE RAW PAPERS.** The Research Standard is explicit that downstream consumers take the synthesis and never the pool, and a triage pass that opens 21 papers is an hour-long run doing a job the synthesis already did. The paper *list* below is for coverage checking only — noticing a title the synthesis never mentions. **Open a paper only if a specific candidate cannot be ruled on without it, and say in your report which one and why.**
4. **`docs/standards/architecture/problem-statement.md`** — the thesis and the differentiators. **You never edit this.** You read it because a sprint that does not serve the thesis is the failure this workflow exists to catch.
5. **`docs/standards/architecture/architectural_standard.md`** — the binding vocabulary and the seams. A candidate that violates a seam is a `reject`, and the reason is the seam.
6. **`docs/standards/architecture/stack_reference.md`** — what we run on and **what we deliberately do not**. A candidate contradicting a settled stack decision is a `reject`, and the reason is that it was already decided. Note its "What we do NOT use" section: that list exists because a research cycle once costed out a product ruled out three weeks earlier.

${EXISTING_WORK}

Report what you found: how many candidates are untriaged, how many sprint sections exist, and anything in the sprint plan that already looks stale against the evidence.

## Stage 2: TRIAGE — the core of this workflow

**Every untriaged candidate gets one of three dispositions. There is no fourth.**

### The test, applied in this order

**First ask: can this be scheduled?** Could somebody pick it up and know what *done* looks like, without another decision being made first? If not, it is not a `ship` — no matter how good the finding is.

| Disposition | When | What you do |
|---|---|---|
| **`ship`** | The work is understood well enough to schedule | Set `decision`, say briefly what makes it worth doing, then Stage 3 places it |
| **`requires review`** | Only the operator can rule on it, and no further automated work makes it ready | Set `decision`, **and write a `D-NNN` row into `direction.md`** |
| **`reject`** | We are not doing this | Set `decision`, and **state why** in the Note |

**`ship` does not size or design anything.** It says we have decided to do it. Stage 3 then PLACES it — choosing which existing sprint owns a milestone is placement, not scheduling: it says where the work belongs, never when it happens or in what order.

**A rejection without reasoning is worthless** — the whole purpose of this file is that a rejected candidate stays visibly rejected and stops being re-proposed. *"Not now"* is not a reason. Rejecting is not failure: three candidates were already rejected because they assumed a deployment model settled three weeks earlier, and catching that is the job working.

### `requires review` — the release valve, and you must actually use it

This exists because **`ship` and `reject` are both wrong answers for an open question.** Shipping one puts a question mark in the plan; rejecting one throws away a real finding.

> **This is not a hypothetical.** The first run of this workflow had only two doors. It pushed eleven unresolved questions through `ship`, which produced two sprint sections whose milestones read *"Settle whether…"*, *"Resolve the…"*, *"Rule the…"* — **two sprints that build nothing.** The operator's verdict was that the sprint plan had been made unusable. Every one of those eleven was a `requires review`.

**Tells that a candidate is `requires review`, not `ship`:**

- You would have to write the milestone as *settle / resolve / rule / decide whether / determine*
- It changes what the project **believes** rather than what it **builds** — a differentiator overstated, a comparator mis-framed, a load-bearing assumption nobody named
- Two defensible answers exist and the evidence does not pick between them
- It is a trade-off with a real cost on both sides
- Acting on it would commit the project to something the operator has not agreed to

**How to file one.** Append a row to `${RESEARCH_DIR}/direction.md`, creating the file with a header row if it does not exist:

| ID | Recommendation | Why it matters | Source | `status` |
|---|---|---|---|---|
| `D-007` | Rule the laptop trust boundary — the resolution available is that the credential is the operator's own | Both major CI vendors publish guidance against exactly this shape; leaving it unwritten blocks the pinned-edge queue design | `C-021` | `open` |

- **IDs are `D-001`, `D-002`, …**, independent of the `C-` series. **Read every existing row first** and continue from the highest — never renumber, never delete, never re-propose something already marked `rejected`.
- **You always leave `status` as `open`.** `applied` and `rejected` are the operator's.
- The `Source` column carries the `C-NNN` it came from, so the two files stay linked.
- **Recommendation and Why-it-matters are one sentence each.** The operator reads these at standup; a paragraph does not get read.

**Then it leaves your working set.** A non-blank `decision` is never re-triaged, so it does not come back around. It surfaces at `/standup` as an open direction decision, the operator rules, and only then does anything change.

**`requires review` is NOT a dumping ground either.** A candidate you simply find hard is still yours to rule on. The test is whether *the operator holds information you do not* — a preference, a priority, a commitment. If the blocker is that you have not read enough, read more.

### Before ruling anything

**Check whether it already has a home.** The enumeration above lists open issues, existing components and the research pool. A candidate matching an open issue **is already tracked** — say which one, and do not create a second home for it. Two surfaces holding one item is the failure this file was built to end.

**Do not renumber or delete any row.** A candidate restated by a later research cycle keeps its **original ID**.

## Stage 3: PLACE — and the sprint file has a house style you must match

Only `ship` candidates reach this stage. `requires review` went to `direction.md`; `reject` went nowhere.

### Placement is a ranked choice. Take the first that fits.

1. **Inside an existing sprint, as one new milestone** — **this is the normal answer and it will be the answer most of the time.** Almost every candidate is a feature or a fix belonging to work already planned.
2. **Not in this file at all** — smaller still, or detail belonging to a phase doc. Do nothing here; list it in your report under *for placement* and a later workflow puts it where it goes. **You never open a phase doc.**
3. **A new sprint section** — **rare, and it must clear a bar**, below.

### The bar for a new sprint section

**A sprint is SUBSTANTIAL. The calibration is roughly 160 hours of development** — about a month of focused work. That is a calibration and not a hard rule; something smaller can qualify. But if what you are holding is days of work, it is not a sprint, and no amount of good reasoning makes it one.

All five, or it is not a sprint:

- **It is substantial.** Measure it against the 160-hour calibration and say what you got.
- **At least three milestones that are things built**, not questions answered
- **No existing sprint owns the work.** If it is *about* Temporal queues, it belongs to Temporal Integration — carving it out and placing it in front fragments one sprint into three, none of which can be worked alone
- **It is workable on its own** — somebody could pick it up without another sprint being finished first
- **You can name it in three words** without an "and"

#### The strongest single test: would it need its own research?

**A genuine sprint almost always needs a component-level research pool of its own before it can be planned.** That is what being substantial means in practice — enough unknowns that somebody has to go find out, rather than enough clarity that somebody can just start.

So ask: *would I commission a research pool for this before anyone wrote a phase doc?*

**A "no" has two shapes and they point OPPOSITE WAYS. Say which one you mean:**

- **"No — it is well enough understood to just do."** Disqualifying. It is a milestone inside an existing sprint, not a sprint.
- **"No — the research already exists, it just sits in another pool."** **The opposite: this is evidence FOR a sprint.** Work with a body of evidence behind it and no home of its own is precisely a component nobody has named yet. Say which pool holds it and treat the condition as MET.

Collapsing the two reads a satisfied prerequisite as a failed one, and quietly filters out exactly the sprints that are most ready to start.

This test is more reliable than the hour estimate, because you can estimate hours badly and still get this right.

#### If it is small and genuinely has no home

It can still become a sprint. But **a small item with no home is almost always a member of a larger category that has not been named yet** — and the category is the sprint, not the item.

When that is the case: **name the sprint after the CATEGORY, never after the small task you happen to be placing today.** A sprint named for the first thing dropped into it is a sprint nobody can add the second thing to, and it locks in a scope decided by the accident of which candidate got triaged first.

You must confirm the category is real before you name it — say in your report which OTHER work would belong there. If you cannot name a second member, you have not found a category, you have found one item wearing a category's name. In that case leave it unplaced and report it.

#### Your scope is the sprint plan, and it ends where phases begin

If an item is **phase-specific** — it belongs inside one component's detailed design rather than to the plan of what gets built — **flag it as phase-specific and your task on that item is DONE.** Say which phase it belongs to if you know. The next agent, doing phase planning, picks it up from there.

That is a complete outcome, not a deferral, and you should not feel it as unfinished work. **The failure this prevents:** a triage pass that cannot say "not mine" ends up inventing sprint items for phase-level detail, and the plan fills with entries nobody can work because they were never sprint-shaped to begin with.

**Justification for the placement goes in your PR body, never in the file.** A sprint section that argues for its own existence has already failed the house style.

### House style — match it exactly

The file's own conventions block is binding on you. **Read it, then match the sections already there.** Concretely:

**A section is:** an `## Sprint: <name> — <status marker>` heading, a `**Phase doc:**` line, one or two short paragraphs of *what this is and why it is worth doing*, then checkboxes. Nothing else. **Use only the status markers the file lists** — do not invent one.

**A milestone is one line naming a thing that will exist.** Bold the thing, then at most one clause of context.

Do this:

```
- [ ] **`install.sh`** — idempotent installer, verified on laptop, workstation and VM
- [ ] **A `claude_cli` activity domain** — heartbeating for long runs, transcript-to-file for payload limits
```

Never this — every line below is from the run that made this file unusable:

```
- [ ] **Rule the laptop trust boundary** — both major CI vendors publish guidance against a
      self-hosted runner holding a credential the dispatcher lacks, and their mitigation is
      ephemeral isolated execution, which a laptop resists. The available resolution is that
      the credential is the operator's own, so the operator is inside the boundary. Writing
      that down *is* the ruling
```

Four things are wrong with it, and each is a rule:

1. **It is a question, not a thing built.** → `requires review`, Stage 2.
2. **It carries its own argument.** The reasoning belongs in a phase doc. Here it buries the one thing the file exists to show.
3. **It cites evidence inline.** Do not add `Evidence:` lines, source links, or research references to this file. **Research is non-binding and the sprint plan is not where it is filed.**
4. **It explains its own placement.** *"Deliberately placed ahead of X"* is PR-body content.

**Also forbidden here:** retrospective notes (*"an earlier version had this backwards"*), decision records, stage tables, migration steps, counter-arguments, hardware diagrams, and idea lists. **All of it belongs in a phase doc**, and if the sprint has no phase doc yet then it is not yours to write — say so in the report.

### What else you may do

**Re-order** existing sections where the evidence changed what depends on what, and **expand** a section with a new milestone. Say why in the report — a re-order without a stated reason reads as churn.

**If nothing warrants a sprint change, change nothing.** A pass that triages every candidate and touches no sprint section is a complete, successful pass — and given the placement ranking above, it is a likely one.

## Stage 4: RECONCILE THE SPRINT AGAINST THE RESEARCH — then COHERE

### 4a: Reconcile — the ONE place you edit an existing milestone

**A sprint section is almost always OLDER than the research backing it.** Research is commissioned *after* an item is written, so the section states what was believed before the evidence arrived. There are two scenarios and you handle both:

| Scenario | What you do |
|---|---|
| Research exists, **no sprint section** | Stage 3 — create one, if it clears the bar |
| Research exists, **the section does too** | **Here.** Bring the section up to what the evidence now says |

**Without 4a, a research cycle changes nothing.** The pool merges, the plan keeps saying what it said before, and the next person to read the sprint acts on superseded evidence. That is a paper we paid for and did not use.

**For EVERY component synthesis, walk its sprint section milestone by milestone.** Each milestone falls into exactly one of these:

- **STILL ACCURATE** → leave it completely alone. This is the common case and it needs no comment.
- **EVIDENCE CORRECTED IT** → rewrite the milestone so it states what the synthesis says. Keep it in house style: one line, names a thing built, carries no argument.
- **THE RESEARCH SATISFIED IT** → a milestone that asked for research the pool has now delivered is no longer work. **Remove it**, and explain in your PR body. The sprint plan states what is built or will be built; a satisfied research request is neither, and the file's own rule is that a superseded item does not appear here at all.
- **THE EVIDENCE MADE IT MOOT** → same: remove it, explain in the PR body.

### The bar for touching an existing milestone — all three, every time

1. **Point at the finding.** Quote the specific synthesis passage that corrects it. *"The synthesis says X, the milestone says Y"* — if you cannot quote it, you are not reconciling, you are editing.
2. **The evidence must CONTRADICT the milestone**, not merely relate to it. New evidence that supports a milestone changes nothing.
3. **Show the before and after** in your change table, both lines in full.

**You may NOT rewrite a milestone you simply disagree with**, would have worded differently, or would have sequenced elsewhere. **Sequencing disagreement is not a defect.** The operator wrote these; your warrant is the evidence, and it extends exactly as far as the evidence does.

**Never flip a checkbox to done.** Removing a milestone the research satisfied is not the same as marking work complete — you are saying it is not work, not that it is finished. If you cannot tell the difference for a given item, leave it and report it.

### 4b: Cohere

Three documents must support each other. Check, and report — **you fix none of these**:

1. **Does the sprint plan serve the problem statement?** Work that advances no stated differentiator is worth flagging.
2. **Does the sprint plan reflect the research?** Compare the synthesis against the sprint plan — **not the papers**. Two shapes count: a significant synthesis finding with **no home anywhere** (not in the sprint plan, not in a component, not in an open issue), and a sprint item resting on evidence the synthesis says has since been corrected. Scan the paper *titles* for a subject the synthesis never mentions; that is a coverage gap worth naming, not a reason to read the paper.
3. **Do the three contradict each other anywhere?** A settled decision missing from one of them is the specific failure that has already cost a research cycle.

Each finding names the document, the contradiction, and what you would change — as a **recommendation for the operator**, never an edit. **4a is the sole exception**, and only within its three-part bar.

## Stage 5: REPORT — the change table

The PR body leads with a table of **every change made and every change recommended**. This is the artifact the operator rules on, so it must be readable without opening the diff:

| # | What | Where | Why | Made or recommended |
|---|---|---|---|---|

Then, separately:

- **Triage summary** — counts across all three dispositions. **They must sum to the untriaged total you were given**; if they do not, say which rows you could not rule on and why.
- **Handed to the operator** — every `D-NNN` row you wrote, with its recommendation. These are why this PR needs a human before it merges: no further pass can produce these rulings.
- **For placement** — shipped candidates too small for a sprint change, so a later pass knows what is waiting. Name the existing sprint each one belongs to **where one exists**.
- **Shipped and genuinely homeless** — real, decided, and owned by no existing sprint while not clearing the bar for its own. **This is a legitimate outcome and it needs no apology.** List each with what you checked, and stop. **Do NOT invent a home to avoid an awkward row** — a candidate filed under a sprint that does not own it is harder to find later than one honestly listed as homeless, and the pressure to tidy is exactly what produces the wrong filing.
- **Phase-specific — NOT YOURS, and complete** — items that belong inside a component's detailed design. Name the phase where you know it. **This is a finished outcome; do not apologise for it and do not manufacture a sprint item to avoid it.**
- **Sprint sections added** — if any. **State which of the five bar conditions each one clears, your read on the 160-hour calibration, and your answer to the would-it-need-its-own-research test.** If you named it after a category, name a second member of that category. If you added no sections, say so plainly; that is the expected outcome, not a shortfall.
- **Reconciled milestones** — every existing milestone you rewrote or removed in Stage 4a, with **the before line, the after line, and the synthesis passage that justified it**. If you reconciled none, say so and say whether that is because the sections were already accurate or because no component research exists yet — those are different answers.
- **Coherence findings** — the Stage 4b output, as recommendations.

**Answer these three plainly**, because they are why this workflow exists:

> Does this build have the right trajectory?
> Does this build exemplify the research?
> Do the research, the problem statement and the sprint plan support one another?

For the first, **lay out the evidence and stop short of the verdict.** Trajectory is the operator's call, and a workflow that answers it has overstepped.

## Stage 6: SUBMIT

${SUBMIT_PROMPT}

${DECISION_LOG_AND_REFLECTION}

${HEADLESS_EXECUTION_GUARD}
