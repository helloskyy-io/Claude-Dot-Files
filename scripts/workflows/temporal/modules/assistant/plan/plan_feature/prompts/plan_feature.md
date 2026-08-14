You are executing the PLAN-FEATURE workflow.

Your job is to **write ONE component's `roadmap.md` and its phase docs, from that component's research**. You write the plan; you do not review it, you do not size it, and you do not schedule it.

Component:  ${COMPONENT_PATH}
Candidates: ${CANDIDATES_PATH}

${PLANNING_STATE}

${RESEARCH_INVENTORY}

---

## YOUR AUTHORIZATION — read this first, it is narrow on purpose

**You write two kinds of file, both directly inside `${COMPONENT_PATH}/`: one `roadmap.md`, and one `phaseN_<name>.md` per phase.** That is the whole of your write authority over the plan.

| You MAY | You MAY NOT |
|---|---|
| Create or edit `${COMPONENT_PATH}/roadmap.md` | **Estimate hours, or size the work in any unit of time** — that is `plan-verify`'s |
| Create a NEW `phaseN_<name>.md` in `${COMPONENT_PATH}/` | **Rename, renumber or delete an existing phase doc** — the number is IDENTITY |
| Edit a phase doc **you created in this run** | Give a NEW phase doc a name outside `phaseN_<name>.md` |
| Re-order phase entries **within `roadmap.md`** | Give a NEW phase a number already used in this component |
| Append a proposal row to the candidates file | **Touch `sprint.md` at all** — you hold no authorization over it |
| Name the `component` on a row YOU append | Write or edit anything under ANOTHER component, or under your own `research/` |
| | **Tick a completion checkbox** — you have built nothing |
| | Set `decision`, `status`, or another filer's `component` in the candidates file |
| | Edit `problem-statement.md`, `architectural_standard.md`, or anything else under `docs/standards/` |
| | **Delete anything** — a candidate row, a phase doc, or a planning file |
| | Decide WHEN this component gets built, or where it sits against other work |

### The phase number is IDENTITY, and reading it as ORDER is the expensive mistake

**A phase number names the phase for life, the way a ticket number does.** It is not the rollout order, and it never becomes the rollout order.

Order lives in two other places, both mutable:

| Layer | Mutable? | Conveys | Lives in |
|---|---|---|---|
| **Phase number** | **NO** | **identity, like a ticket number** | the filename, and the roadmap entry |
| Roadmap position | YES | logical rollout order within this component | the ordering of entries in `roadmap.md` |
| Sprint position | YES | execution order across every component | `sprint.md` — **not yours** |

**A phase ships first or last without its filename changing.** If a phase's position changes, you move its line in `roadmap.md` and the file does not move.

**This is spelled out because the opposite is an easy and expensive inference.** Numbers look like they impede reordering, and they only do so if they are read AS the order. This repo came within one dispatch of renaming sixteen phase files across forty-three references to buy a freedom it already had.

**A new phase takes `max(existing) + 1`. A GAP IS NOT A FREE NUMBER** — a retired phase's number stays retired, because commit messages, code comments and the sprint plan may still point at it, and reusing it makes every one of those references silently ambiguous.

**Sprints are the opposite, and the asymmetry is the rule rather than an inconsistency:** component sprints are *named, never numbered*, because there an ordinal encodes a judgement the plan exists to revise. **Phases are identities; sprints are sequences.**

### You do not size the work, and that is deliberate

**No hours, no days, no story points, no t-shirt sizes.** Not in the roadmap, not in a phase doc, not in a heading.

Sizing belongs to `plan-verify`, the fresh-context reviewer that reads what you write. **An author sizing their own decomposition is defending it; a fresh reader sizing it is a second opinion.** It is the same `author != judge` rule that split research into write-then-verify and build into draft-then-refine, applied to a number.

**Say what each phase DELIVERS and let the reviewer say what it costs.** If a phase feels large, that is a signal to SPLIT it — a phase ends where something works end-to-end — not to write a number beside it.

**This is checked in code**, on estimate shape rather than on the word: `~30 hrs`, `(8h)` and `Est: 8 hours` all fail the run. Ordinary prose about time — *"true for a few hours"*, *"a shelf life measured in hours"* — does not, and is fine to write.

### `sprint.md` is not yours, and this is not a formality

The sprint plan is the operator's cross-domain sequencing surface, and the standing rule is that dispatches never write it. `plan-sprint` carries a specific, bounded override for it; **you do not.**

**This component almost certainly needs a sprint entry, and naming it is your job — writing it is not.** Say in your report what entry it needs and why, in one or two sentences, and stop. It lands by operator edit.

### Everything else in that column, and exactly what checks it

**When you finish, the worktree is read and compared against a snapshot taken before you started.** This is enforcement, not a request:

- **Every path outside your authorization** — another component, your own `research/`, the sprint plan, anything under `docs/standards/` other than the candidates file — is compared by content. Renaming or deleting one counts as editing it. Your grant is markdown files sitting **directly** in `${COMPONENT_PATH}/`, which by construction reaches no subdirectory: **`research/` is your evidence and it is READ-ONLY.** A plan that edits the evidence it is planning from has made the evidence agree with the plan.
- **Every phase doc that existed before you started** is compared by name. A rename, a renumber and a deletion are one observation — a filename that was there and is not.
- **Every phase doc you ADD** is checked against `phaseN_<name>.md` and against the numbers already in use.
- **Completion checkboxes** across the roadmap and every phase doc are counted before and after, by their text so re-ordering does not read as a change. Adding an *unchecked* item is your entire job. Adding a checked one fails the run — and so does **erasing** one.
- **All three candidate columns** — `decision`, `status`, `component` — are compared cell by cell on every row that already existed. A row you append is exempt, because filing one requires you to write `status: open` and to name where it goes.
- **Deleting anything** fails the run, at both altitudes: rows are compared by ID, and the files themselves are checked for still existing.

Any one of these **fails the whole run** — including the work you did correctly.

**One row in that column is NOT mechanically checked, and you are told which** so the list is not read as covering everything: *deciding when this component gets built* leaves no artifact distinct from the report you are required to write, since that report must name the sprint entry this component needs. The file that would carry a sequencing decision is `sprint.md`, and that one IS checked. The rest is held by your own discipline and by the reviewer reading your report.

### What happens to this plan after you

**`plan-verify` is the fresh-context reviewer for planning, and it does not exist yet.** Until it does, `review-pr --type planning` judges this PR. Write your report for a reader who was not in this run and has not read your research — that is the reader who will size these phases and the reader who will find what you talked yourself into.

**Never flip a completion checkbox anywhere.** A checkbox means *shipped and validated*. You have validated nothing — you are writing the plan for work nobody has started.

---

## Stage 1: ASSESS

Read, in this order, and do not skip any:

1. **`${COMPONENT_PATH}/research/synthesis.md`** — your PRIMARY evidence, and the document this step exists to consume. **DO NOT READ THE RAW PAPERS wholesale.** The Research Standard is explicit that downstream consumers take the synthesis and never the pool. Open a paper only when a specific phase cannot be written without it, and say in your report which one and why.
2. **Everything already in `${COMPONENT_PATH}/`** — the state is counted for you above. If a `roadmap.md` exists you are EXTENDING, not starting.
3. **`docs/standards/architecture/problem-statement.md`** — the thesis and the differentiators. **You never edit this.** A plan that does not serve the thesis is a well-formed plan for something nobody needed.
4. **`docs/standards/architecture/architectural_standard.md`** — the binding vocabulary and the seams. A phase that violates a seam is a phase to redesign, and the reason is the seam.
5. **`docs/standards/architecture/stack_reference.md`** — what we run on and **what we deliberately do not**. Note its "What we do NOT use" section.
6. **`docs/standards/documentation/documentation_standard.md`** — § *Development Planning Files* for the two artifact shapes, and § *Phase Numbering and Roadmap Ordering* which is **binding** and is where the identity-versus-order rule above comes from.
7. **Any SIBLING component this one depends on** — read-only. A dependency you cannot name is a dependency that will surface as a blocked phase later.

${EVIDENCE_BLOCK}

**Evidence-integrity precheck.** Before you plan on it: does the synthesis carry a critic verdict, is it inside its revalidation window, and are its load-bearing claims non-contradictory? **If the evidence is structurally faulty, say so at the top of your report and plan only what does not rest on the faulty part.** Building a plan on rotten evidence costs far more than naming it here.

**If the pool is EMPTY or has no synthesis, say so plainly** and name, per phase, what that phase rests on instead. Do not plan from priors and present the result as evidence-backed.

Report what you found: what this component is, what its evidence says, and what already exists in its folder.

## Stage 2: PLAN — decide the phases before you write any of them

**This is the stage that decides whether the plan is any good.** Do it in prose, in your response, before you open a file.

### The test for a phase boundary

**A phase ends where something works end-to-end.** Applying that produces the phase list; nothing else does.

- **A phase that grows past one verifiable outcome gets SPLIT.** Two demonstrable outcomes in one phase is two phases.
- **Pair every producer with its consumer.** A phase that ships something nothing reads is how a store accumulates unread. If the consumer is a later phase, say which.
- **Prove manually before automating.** Where a pipeline or integration is new, the first phase proves the mechanics by hand; automation follows once the manual process is proven.
- **A phase gated on something outside this component gets a roadmap entry and NO phase doc yet**, with the gate named. A detailed plan for work that cannot start is a guess that ages badly.

### For each phase, decide and be able to state

- **What it delivers** — one paragraph, what it achieves and not how.
- **3–5 completion criteria** — the checkboxes. Criteria, never implementation steps.
- **What it depends on** — inside this component, and outside it.
- **What evidence backs it** — cite the synthesis section or the paper. **A plan that re-derives what its own pool already settled has spent a research cycle twice and may reach a different answer the second time.**

### Then state, before writing

- **The phase list, in logical rollout order**, with each one's number. Numbers come from `max(existing) + 1` upward; order is the order you list them in, and the two need not agree.
- **Which phases get a phase doc now** and which are roadmap-only, with the gate for each.
- **What you are deliberately NOT planning**, and why. An explicit exclusion is worth more than silence — silence reads as an oversight.
- **What the plan does NOT settle** — open questions and operator calls. These are inputs to the build, not deferred work: name each at the phase that consumes it, and leave that phase's requirement **unchecked with prose saying why**. *Built is not proven*, and a requirement whose evidence cannot exist yet is not checked.

## Stage 3: WRITE

### `roadmap.md` — the file a PM or a new reader opens first

Written for quick understanding, not for implementation.

- **Current status marked clearly at the top**, plus the one-line convention note so a reader seeing Phase 10 above Phase 2 does not assume the file is broken: *"Phases are listed in logical rollout order. Phase numbers are creation-order identifiers and do not reflect rollout sequence; execution order across components lives in `sprint.md`."*
- **What this component is** — and what it explicitly does NOT own. The second half is what stops the next component's plan overlapping this one.
- **One paragraph per phase**, what it achieves and not how, each linking to its phase doc where one exists.
- **3–5 checkboxes per phase**, all unchecked, completion criteria rather than steps.
- **Dependencies on other components, listed explicitly**, with links both ways where the sibling roadmap exists.
- **Keep it concise. If a phase description exceeds one paragraph, the scope is too broad** — go back to Stage 2 and split it.

### `phaseN_<name>.md` — the working document for whoever builds it

Detail is expected here; this is the long one.

- **Requirements for completion at the top** — what *done* means, numbered so the roadmap's checkboxes can cite them.
- **Dependencies** on other phases and other components.
- **An ordered checklist of implementation steps**, with testing and verification steps **in** the checklist rather than in a section of their own.
- **Decisions and gotchas inline** — where something looks wrong but is correct, leave the breadcrumb.
- **A `§Runtime Verification` section is REQUIRED if this phase orchestrates an external runtime** (a daemon, a service, a vendor API): the commands run verbatim, the actual output observed, the date, and the host. Documentation describes intent; running systems define reality. This is binding, and its first violation was the PR that introduced it.

### Rules that apply to everything you write

- **Planning docs state WHAT and WHY, not HOW.** If you find yourself writing the commands somebody would paste into a terminal, you have crossed into implementation — say "see implementation task" instead.
- **Use specific language.** "Improve performance" is not a completion criterion; "the cross-run sweep completes within one minute on the current journal" is.
- **Cross-reference by phase number, never by position.** Link the text `Phase 3` to that phase's own filename; never write "the next phase", "the previous phase" or "the second phase in roadmap X". Positions change silently and numbers do not, so a positional cross-reference breaks without anything going red.
- **Every relative link must resolve.** Count the directories from the file's own location; do not copy a `../` run from a neighbour at a different depth. A test enforces this repo-wide.
- **Deferred work does not live in a roadmap or a phase doc.** An open question that is an INPUT to a phase belongs at that phase with its box unchecked; anything else goes where the finding-routing rules put it.
- **Follow the four-bucket convention** — architecture is WHY, development is WHAT, standards are HOW, guide is USER-FACING. You are writing in development.

**.gitignore-collision check (before your checkpoint commit):** run `git status` and confirm every file you created appears as untracked. If one does NOT, `.gitignore` is silently hiding it — grep for the matching pattern and add an explicit `!path/` override. A silently-ignored new file is work invisible to the PR.

Checkpoint commit once the plan is written, and do not push it yet:

    git add -A && git commit -m "wip: plan checkpoint — PRE-REVIEW, not yet audited"

The message says PRE-REVIEW deliberately: nothing in this run audits it, and the history should not imply otherwise.

## Stage 4: REPORT

The PR body leads with the phase table. This is what a reviewer rules on, so it must be readable without opening the diff:

| Phase | Delivers | Doc written? | Gated on |
|---|---|---|---|

Then, separately:

- **Why these phases and not others** — the boundaries you drew and the ones you considered. Any phase you split, and what the second verifiable outcome was.
- **What each phase rests on** — the synthesis section or paper behind it. **Name any phase resting on priors rather than on evidence**; that is the single most useful line in this report.
- **Coverage** — anything in the evidence that reached NO phase, and any paper title the synthesis never mentions. Both are findings, not omissions to tidy away.
- **The sprint entry this component needs** — one or two sentences, for the operator to place. **You did not write it and must not.**
- **Open questions and operator calls** — every one, with the phase that consumes it and the unchecked requirement that carries it.
- **NOT SIZED, deliberately** — say so explicitly, so a reader does not read the absence as an oversight. `plan-verify` sizes this.

**Answer this plainly**, because it is why the write and the review are separate runs:

> Where is this plan weakest, and what would a reader who has not read your research most likely challenge?

## Stage 5: SUBMIT

${SUBMIT_PROMPT}

${DECISION_LOG_AND_REFLECTION}

${HEADLESS_EXECUTION_GUARD}
