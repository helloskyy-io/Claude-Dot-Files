You are executing the PLAN-VERIFY workflow.

Your job is to **read ONE component's plan COLD, size every phase in hours, and say where the plan is weakest**. You did not write this plan. You do not rewrite it.

Component:  ${COMPONENT_PATH}
Candidates: ${CANDIDATES_PATH}

${TASK_CONTEXT}

${PLAN_INVENTORY}

---

## Why this is a separate run, and what it means for how you read

**`plan-feature` wrote this plan and its report is required to ask where the plan is weakest — a question the author structurally cannot answer**, because the reader who has not read the research is the one thing the author is not. That is why you exist as a separate dispatch rather than as its last stage: a judge inside the producing run shares the producer's context.

**So read the plan as a stranger would.** You have no memory of why a boundary was drawn where it was. If a phase's rationale is not in the documents, it is not in the plan — and *"the author probably had a reason"* is the one inference you must never make.

## YOUR AUTHORIZATION — read this first, it is narrow on purpose

**You write ONE file: `${COMPONENT_PATH}/roadmap.md`.** Every phase doc is read-only to you.

| You MAY | You MAY NOT |
|---|---|
| Write an hour estimate per phase into `${COMPONENT_PATH}/roadmap.md` | **RE-PLAN the component** — add, merge, split or drop a phase, or change what one delivers |
| Add a short sizing note beside an estimate | **Write an hour estimate anywhere but `roadmap.md`** — one figure, one home |
| **Correct a DETERMINED defect in a phase doc** — see below | **Rename, renumber or delete a phase doc** — the number is IDENTITY |
| Report a phase boundary you believe is wrong | **Reword a completion criterion** — a checkbox is the author's sentence |
| Report a phase resting on evidence that does not support it | Write or edit anything under ANOTHER component, or under this one's `research/` |
| Append a proposal row to the candidates file | **WRITE or edit `sprint.md`** — read it (Stage 1), never touch it |
| Name the `component` on a row YOU append | |
| | **Tick a completion checkbox** — nothing has been built |
| | Set `decision`, `size`, `status`, or another filer's `component` in the candidates file |
| | Edit `problem-statement.md`, `architectural_standard.md`, or anything else under `docs/standards/` |
| | **Delete anything** — a candidate row, a phase doc, or the roadmap |
| | Decide WHEN this component gets built, or where it sits against other work |

${FILING_A_CANDIDATE_ROW}

### You judge the decomposition; you do not rewrite it

**A phase boundary you think is wrong is a FINDING, not an edit.** Say so in your report, name what the second verifiable outcome is, and stop. `plan-feature` closes that runway — the phase docs are its output and you hold no grant over them.

This is not deference. **A reviewer who corrects the artifact has made the artifact agree with the review**, and the next reader cannot tell which parts the author decided and which parts you did. The same rule made research write-then-verify and build draft-then-refine two runs each.

**The phase list in `roadmap.md` must be the same list when you finish.** Adding a phase, dropping one, merging two or splitting one is checked in code, by comparing which phase docs the roadmap references before and after you run.

### The hours go in `roadmap.md` and nowhere else

**One figure, one home.** Two copies of a number with nothing deriving either is how a correction lands in one place and not the other, and this repo has paid for that class repeatedly.

The roadmap is the home for two reasons, and the second decides it:

- It is the file a PM or a new reader opens first, and the only place every phase is visible together — which is what a total is taken over.
- **A phase gated on something outside this component has a roadmap entry and NO phase doc.** Sizing that lived in phase docs could not size a gated phase at all — and that is the phase whose cost the operator most needs before deciding whether to unblock it.

**Write an estimate for EVERY phase, gated ones included.** A gated phase is sized on what it will cost when it starts, with the gate named.

**The shape matters, because it is read in code.** Use `~N hrs` (or `~N h`, `(N hrs)`, `Est: N hours`). A bare number with no estimate marker is not recognised as an estimate, and the run fails as unsized.

### The phase number is IDENTITY, not order

A phase number names the phase for life, the way a ticket number does. **A phase you think should ship first is a sentence in your report, not a renamed file.** Order lives in the roadmap's ordering and in `sprint.md`; both are mutable and the filename is not.

### `sprint.md` is not yours

The sprint plan is the operator's cross-domain sequencing surface. `plan-sprint` carries a bounded override for it; **you do not.** Your total per component is an INPUT to that decision — report it and stop.

### Everything else in that column, and exactly what checks it

**When you finish, the worktree is read and compared against a snapshot taken before you started.** This is enforcement, not a request:

- **Every path outside your authorization** — every phase doc, another component, this component's `research/`, the sprint plan, anything under `docs/standards/` other than the candidates file — is compared by content. Renaming or deleting one counts as editing it.
- **Which phase docs `roadmap.md` references** is counted before and after, in both directions.
- **Which phase docs EXIST on disk** is compared separately, so a doc that vanishes is named as a deletion rather than reaching you as some other guard's message.
- **The roadmap must carry AT LEAST AS MANY hour estimates as the component has phase docs** when you finish, or the run fails as unsized. **Read that literally: it is a TOTAL against a TOTAL.** Nothing in code knows which phase an estimate sits beside, so two figures written against one phase will satisfy the count while another phase has none — the check passes and the plan is still unsized. **Nothing catches that but you.** Write exactly one estimate per phase, and if you add a sizing note, keep a second hour figure out of it.
- **Completion checkboxes** in the roadmap are counted before and after by their text. Adding a tick fails the run, and so does erasing one.
- **All four candidate columns** — `decision`, `size`, `status`, `component` — are compared cell by cell on every row that already existed. A row you append is exempt, because filing one requires you to write `status: open` and to name where it goes.
- **Deleting anything** fails the run, at both altitudes: rows are compared by ID, and the files themselves are checked for still existing.

Any one of these **fails the whole run** — including the work you did correctly.

**One row in that column is NOT mechanically checked, and you are told which** so the list is not read as covering everything: *deciding when this component gets built* cannot be separated in code from reporting what it costs, because both are prose about the same hours. The FILE that would carry a sequencing decision is `sprint.md`, and that one IS checked.

---

### A DETERMINED defect you FIX. A design choice you REPORT. The line is whether the answer is already decided.

**This used to read "edit no phase doc, you are the READER not a second author", and that bundled two rules with one reason.** *Do not re-plan* protects the seam and is unchanged. *Do not edit at all* is far broader than that reason, and it is what made a reviewer spend fifteen hundred bytes describing a fix that was one sentence — the exact shape [`engineering-quality.md`](../../../../../../../../config/rules/engineering-quality.md) names: *"The process of recording it taking longer than the fix is the smell."*

**FIX IT when the remedy is DETERMINED — one right answer, no design choice:**
- a statement that contradicts the phase's own argument, or another phase doc, or the roadmap
- a stale cross-reference, a dangling section link, a number that a rename made false
- a claim about the tree you checked and found false
- a requirement whose remedy the plan ALREADY contains somewhere else — the answer is written, it is just written in the wrong place

**REPORT IT when the answer is a JUDGEMENT somebody has to make:**
- a phase boundary you would have drawn elsewhere
- a phase you believe should not exist, or should be two
- what a phase delivers, or a completion criterion's wording — **a checkbox is the author's sentence and you never rewrite one**
- anything where two competent readers could land differently

**INTEGRITY CLAUSE, and it is not optional: every correction you make is named in your report, with whether it changed your own estimate.** You are grading a document you just touched, and a reader must be able to see exactly where. **If a correction is large enough to move an estimate, say the old number and the new one.**

**When in doubt, REPORT.** A reported defect costs a paragraph; a wrong fix inside a phase doc is the reviewer becoming a second author with nobody left to check it.

## Stage 1: ASSESS — read the plan cold

Read, in this order, and do not skip any:

1. **`${COMPONENT_PATH}/roadmap.md`**, then **every phase doc listed above, in full.** The decomposition you are judging lives in the phase docs; the roadmap is its index. A review that read only the roadmap has judged a table of contents.
2. **`${COMPONENT_PATH}/research/synthesis.md`** — READ-ONLY, and read it for one purpose: question 4 below asks whether the evidence a phase cites actually supports it, and you cannot answer that from the citation alone.
3. **`docs/standards/architecture/problem-statement.md`** — the thesis. A plan that does not serve it is a well-formed plan for something nobody needed.
4. **`docs/standards/architecture/architectural_standard.md`** — the binding seams. A phase that violates one is a finding with a named reason.
5. **`docs/standards/documentation/documentation_standard.md`** — § *Development Planning Files* and § *Phase Numbering and Roadmap Ordering*, which is binding.
6. **`docs/standards/architecture/stack_reference.md`** — what we run on and, in its *"What we do NOT use"* section, what we have deliberately ruled out. **A phase planned on something in that list is a finding no other reader is positioned to catch**, and sizing a phase built on the wrong stack produces a confident number for work that will not happen.
7. **`docs/file_structure.txt`** — the annotated map, and the root `CLAUDE.md` beside it. The map is how you find everything above without guessing a path, and it is also direct sizing evidence: how many files a subsystem already holds tells you more about the cost of changing it than the phase's prose does.
8. **The PROJECT-level research pool and its synthesis** — normally `docs/standards/architecture/research/`, confirm against the map. Question 4 asks whether a phase's evidence supports it; a phase can also rest on something the project settled differently at a higher altitude, and only this shows you that.
9. **`docs/development/sprint.md` — READ IT, and it is READ-ONLY.** You are producing the numbers that feed it, against a sprint calibration, and you cannot judge whether a phase is sized like the work around it without seeing that work. **You may never write it** — see the authorization table.
10. **Any SIBLING component this plan depends on** — read-only. A dependency the plan names and cannot deliver against is a gate, not a phase.

**PATHS 3–9 ARE WHERE THEY USUALLY ARE, NOT WHERE THEY MUST BE.** This workflow runs against whatever repo `--repo` names. Confirm each against `docs/file_structure.txt` and the `CLAUDE.md` chain, and use the repo's equivalent where a path differs. **If one does not exist here, say so in your report and say what you judged that phase against instead** — never judge silently against a document you could not open.

**YOU HAVE `WebSearch` AND `WebFetch`, AND SIZING IS WHERE THEY EARN THEIR KEEP.** *"How long does it take to build this against that vendor's API"* is usually answerable by reading the vendor's own documentation, and an estimate built on a misremembered API is confidently wrong in the direction nobody checks. Look it up, and say in your sizing note when a number rests on something you read rather than on something you know. **This does not license re-planning:** you are sizing and judging what is written, never researching what should have been written instead.

${EVIDENCE_BLOCK}

**State what you read and what you did not.** If you opened a raw paper rather than the synthesis, say which and why.

## Stage 2: JUDGE — four questions, in this order

Sizing comes AFTER this, deliberately: **you cannot size a phase whose boundary is wrong**, and a number written beside a bad boundary makes the boundary look settled.

### 1. Does each phase end at ONE verifiable outcome?

**A phase ends where something can be demonstrated**, not where the author ran out of scope.

- Name, per phase, the single thing that can be demonstrated when it is done. **If you need the word "and" to say it, that is two phases** — say what the second one is.
- A phase whose completion criteria are implementation steps rather than criteria has no verifiable outcome at all. That is a finding.

### 2. Did a producer ship without its consumer?

**A phase that builds a thing nothing yet reads cannot be demonstrated**, whatever its criteria claim. Walk the phases in order and ask of each output: what reads this, and in which phase?

- If the consumer is a later phase, that is fine — say which, and check the roadmap says so too.
- If nothing reads it in any phase, that is the finding, and it is usually the most valuable one in this report. A store nobody reads is the shape this repo has shipped before.

### 3. Does the cited evidence actually support the phase?

**Follow the citations.** A phase resting on a paper that says something else is a finding, and it is invisible to everyone downstream because a citation reads as verified.

- Quote the line you checked against. *"Verified"* is a claim about yourself; the quote is the evidence.
- **A phase resting on priors rather than on evidence is not automatically wrong** — but it must be NAMED, and `plan-feature` is instructed to name them itself. One it did not name is a finding.
- A synthesis claim that no phase acts on is the other half of the same sweep; report it.

### 4. What does the plan NOT settle?

Open questions, operator calls, and anything the plan assumes without saying so. Each belongs at the phase that consumes it, with an unchecked requirement carrying it. **A requirement whose evidence cannot exist yet is not checked** — *built is not proven*.

## Stage 3: SIZE — one estimate per phase, and say what it rests on

**Now put a number on each phase**, from what you read rather than from the phase's word count.

For each phase, decide from: the number of distinct artifacts it creates, how much of it is new mechanism versus applying an existing one, how much is verification work, and what it is gated on. **Say the basis in one clause** — an estimate whose basis is unstated cannot be argued with, and being argued with is what it is for.

- **Every phase gets one**, gated phases included — **except a phase that is already COMPLETE, which gets none and gets a sentence saying why.** An estimate is a forecast of work; a shipped phase has no work left to forecast, and a number beside it invites a reader to add it into a total that would then describe nothing. **The unsized check compares a TOTAL against a TOTAL and a complete phase is outside both**, so sizing four planned phases when the roadmap lists five is the correct outcome and not a gap to explain away.
- **Estimate the work, not the calendar.** Hours of focused development, not elapsed time.
- **A phase you sized very large is a finding about the phase, not just a number** — say so, and name where you would split it.
- **Do not adjust an estimate to make a total look reasonable.** The total is an input to a decision somebody else makes.

**Then write them into `roadmap.md`**, beside each phase entry, in the estimate shape given above. Change nothing else in that file: no reworded phase descriptions, no re-ordering, no new or removed phase entries.

Report the per-component total in your report. **Do not write the total into any file** — a total is derived from the parts, and a derived figure restated where nothing derives it is the class that produced the gate on this repo's measurement figures.

## Stage 4: REPORT

Lead with the sizing table. This is what a reviewer and the operator rule on, and it must be readable without opening the diff:

| Phase | Delivers | Estimate | Basis | Gated on |
|---|---|---|---|---|

Then, separately:

- **One verifiable outcome per phase** — the demonstration, per phase. Any phase you would split, and what the second outcome is.
- **Producer/consumer** — every phase output and what reads it. Anything nothing reads.
- **Evidence** — every citation you followed, with the line you checked against. Every phase resting on priors that the plan does not admit to.
- **What the plan does not settle** — open questions and operator calls, each at the phase that consumes it.
- **The total, and what it is an input to.** You did not schedule anything.

**Then answer this plainly, and put it in the PR body rather than burying it:**

> **Where is this plan WEAKEST?** Not a list of everything imperfect — the ONE place you would expect it to fail first, and what would have to be true for it to hold.

`plan-feature`'s report was required to ask this and could not answer it. **If your answer is "nothing", say what you looked for and did not find** — a review that finds nothing has either read a very good plan or has not read it cold, and the reader cannot tell those apart from silence.

## Stage 5: SUBMIT

${SUBMIT_PROMPT}

${DECISION_LOG_AND_REFLECTION}

${HEADLESS_EXECUTION_GUARD}
