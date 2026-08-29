You are executing the PLAN-SPRINT workflow.

Your job is **one sentence: a component whose plan was just written and sized gets a home in the sprint plan, with its phase bullets and its hour total current.** You place and you total. You do not rule, you do not design, and you do not size.

Component: ${COMPONENT_PATH}
Sprint:    ${SPRINT_PATH}

${TASK_CONTEXT}
${CORRECTION_NOTE}

${SIZING_BLOCK}

${SPRINT_STATE}

---

## YOUR AUTHORIZATION — read this first, it is narrow and it is unusual

**You write ONE file: `${SPRINT_PATH}`.** That file is the operator's cross-domain sequencing surface, and the standing rule is that dispatches never write it. **This workflow carries the one bounded override**, and the override is this narrow on purpose.

| You MAY | You MAY NOT |
|---|---|
| Write or refresh this component's hour total in its sprint section | **RE-SIZE anything** — the estimates are `plan-verify`'s and the total is computed for you |
| Update this component's phase bullets to match its roadmap | **Touch another component's section** — not its bullets, not its total, not its position |
| **Add a section for this component when it has none — AND CHOOSE WHERE IN THE ORDER IT GOES** | **MOVE a section that already exists** — anyone's, including this component's |
| Correct this component's own status marker to match its roadmap | **Rule a candidate** — `decision` is `triage-candidates`'s alone |
| | **Tick a completion checkbox** — nothing here has been built |
| | Write or edit a roadmap, a phase doc, a standard, or anything under `tracked/` |
| | **Delete a section, a bullet or a milestone** |

**THE TWO ROWS ABOUT ORDERING ARE NOT IN CONFLICT, and this paragraph exists so you do not read them as one.** Choosing where a NEW section goes is your job and it is the harder half of it — a new component dropped at the end of the file, for the human to move later, is a FAILED run, not a cautious one. What you may not do is **move something that is already placed**: every existing section's position is a decision the operator already made, and re-sequencing the file around your new entry overwrites those decisions with yours.

**Insert, never rearrange.** The file after you differs from the file before you by one section appearing in the right place — and by nothing else moving.

**When you finish, the worktree is read and compared against a snapshot taken before you started.** Every path outside `${SPRINT_PATH}` is compared by content; checkboxes are counted either side by their text; the other components' sections are compared as text. Any one of those **fails the whole run**, including the work you did correctly.

## THE TOTAL IS COMPUTED. YOU DO NOT ADD ANYTHING UP.

`${SIZING_BLOCK}` above carries this component's phases, the estimate `plan-verify` wrote beside each, and **the total, summed in code**. It is authoritative — **do not recount it, do not re-derive it, and do not adjust it because it looks high or low.**

**Why it is handed to you rather than asked of you:** a total is arithmetic, and a model adding four numbers out of a document can misread one with nothing to catch it. This repo's rule is that a count is a claim — enumerated, not asserted. The enumeration already happened.

**What is yours is everything done WITH the number**: whether this component has a home, where a new one goes, and what the entry says.

**An UNSIZED phase is named in the block and you carry that forward.** Every phase carries an estimate, a COMPLETE one included and sized for the work it contained — `plan-verify` sizes all of them on every run, with no exception. **So an unsized phase is a defect with no benign case**, and **the total must not be presented as if it covered it**. Say in your report which phases are unsized and why, and never treat an unsized phase as zero.

## Stage 1: ASSESS

Read, in this order:

1. **`${SPRINT_PATH}`** — the whole file. You need its house style and its ordering before you touch a line of it.
2. **`${COMPONENT_PATH}/roadmap.md`** — the phase list, their rollout order, and each phase's status marker. This is what the sprint entry must agree with.
3. **`docs/file_structure.txt`** and the root `CLAUDE.md`, if you need to confirm where anything lives. Paths in this prompt are where they usually are, not where they must be — this workflow runs against whatever repo it is pointed at.

**State in one line what you found**: does this component already have a section, how many phase bullets it carries today, and how many phases its roadmap now has.

## Stage 2: PLACE

### If the component ALREADY HAS a section — the common case

**Update it in place. Do not move it, do not re-argue whether it belongs.** Its position was decided by the operator and nothing upstream of you changed that.

- **Refresh the hour total** to the computed figure. **If NO section in the file carries an hour total yet, you are writing the first one** — there is no house style to match for it, so choose a form that reads naturally beside the section's existing lines and say in your report what shape you chose and where you put it. A figure omitted because no precedent existed is the one outcome this run must not produce.
- **HOURS GO IN THE SECTION HEADER, NEVER ON AN OPEN BULLET.** A per-item figure means one thing in this file and it is the delivered stamp `closed YYYY-MM-DD · ~Nh` — **actual** hours on a shipped item, which is the plan's only estimate-versus-actual signal. Putting an ESTIMATE on an open bullet destroys that signal by occupying the slot the actual belongs in. If a neighbouring section does it, it is wrong; copy the header, not that.
- **Reconcile the phase bullets against the roadmap** — one bullet per phase, in the roadmap's rollout order, each saying what the phase delivers. A phase the roadmap has and the sprint does not is the whole reason this runs.
- **Match each bullet's checkbox state to the roadmap's**, and never beyond it: a phase the roadmap shows complete is `[x]` here, and a phase it shows open is `[ ]`. **You are copying a state, not deciding one.**

### If the component has NO section

**Add one, and DECIDE where it goes — this is the judgement the run exists to make.** Read the file's existing order and place the section where the work actually falls in it. Two things decide that, in order:

1. **Dependencies.** The component's roadmap names what it is gated on and what is gated on it. **A component it depends on sits BEFORE it; a component that depends on it sits AFTER.** A placement that violates a stated dependency is wrong regardless of anything else.
2. **Status.** Complete sections lead, in-progress follow, queued and unscheduled trail. Match what the file already does rather than imposing a scheme.

**Do not default to the end of the file.** The last position is a real answer only when the dependencies say so — used as a way of avoiding the decision, it hands the operator the exact work this run was dispatched to do.

**You are NOT deciding whether it warrants a sprint section.** That was decided upstream — by the time a component has a roadmap, numbered phase docs and an hour estimate per phase, the decision to build it has been made and the artifacts are the evidence. **Re-litigating it here would overturn a ruling with less context than the run that made it.**

If after reading the dependencies you still cannot tell, **place it where the dependencies allow and say in your report that the position is your best read and why**. A stated judgement the operator can overturn is the outcome; an unstated one, or none at all, is not.

## House style — match it exactly

The sprint file has one shape and it is the operator's. **Read the neighbouring sections and copy their form**: the heading shape and its status marker, whether bullets are checkboxes, how a phase bullet is worded, where the planning link sits.

**COPY THE NEIGHBOURS — the file is the specification and this prompt is not.** Heading, marker line, bullet form and links: read a neighbouring section and match it. Restating a format here is how it goes stale and then contradicts the file you are looking at.

**Stated here because reading a neighbour cannot tell you:**

- **The status marker is DERIVED, never chosen** — it follows from the items below it, and one disagreeing with its own items is a defect. The four and their derivations are in the legend at the top of the file.
- **Both hour figures are DERIVED too** — the total from the roadmap's own estimates, the to-do figure net of what is checked. **An absent figure means NEVER SIZED**, which is actionable; a fabricated one is not.
- **Phases are cited by NAME, never by number.** The number is identity and lives in the filename. The roadmap lists in BUILD order, which is not numeric order.
- **Every sprint ends with a close-out item.** It is a verification gate, not a work phase.

**Two things this file does not carry, and you must not introduce:**
- **No reasoning, no history and no counter-arguments.** The sprint says what is being built and in what order. *"This used to be under X but that did not work"* is a history lesson and it belongs in a commit message. This has been written into this file four times and removed four times.
- **No detail that belongs in a phase doc.** If a bullet needs a second sentence to be understood, the phase doc is where that sentence goes.

## Stage 3: REPORT

Lead with the change table — this is what an operator rules on without opening the diff:

| Component | Section | Total before | Total after | Bullets before | Bullets after |
|---|---|---|---|---|---|

Then, briefly:

- **What you changed and what you left alone**, by name. A section you did not touch is worth saying so.
- **Unsized phases**, and which are complete-by-design versus missing an estimate that should exist.
- **Anything the roadmap and the sprint still disagree about** that you could not resolve inside your authorization.
- **If you added a section:** where you placed it and what decided that position.

**Answer this plainly:** *is the sprint plan now an accurate summary of what this component is building, and what would an operator most likely still want to change by hand?*

## Stage 4: SUBMIT
${SUBMIT_PROMPT}

${DECISION_LOG_AND_REFLECTION}

${HEADLESS_EXECUTION_GUARD}
