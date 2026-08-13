You are executing the PLAN-CANDIDATES workflow.

Your job is to **give every ruled `ship` candidate somewhere to be built** — and, for most of them, to establish that somewhere already exists. You create structure; you do not plan work.

Candidates:    ${CANDIDATES_PATH}
Research pool: ${RESEARCH_DIR}

${WORKING_SET}

---

## YOUR AUTHORIZATION — read this first, it is narrow on purpose

**You create a component's CHARTER. That is the whole of your write authority**, and the file it lives in is `docs/development/<slug>/roadmap.md`.

| You MAY | You MAY NOT |
|---|---|
| Create `docs/development/<slug>/roadmap.md` for a component that has none | **Touch `sprint.md` at all** — you hold no authorization over it |
| Write the CHARTER into it — see the next section for exactly what that is | Write or edit any phase doc — `plan-feature` writes those |
| Append a new `C-NNN` proposal row to the candidates file with `decision` **blank** | **Edit a `roadmap.md` that already exists** — you create one, you never revise one |
| | Write phases, epics, milestones or hour estimates into anything |
| | Leave a component directory with no `roadmap.md` in it |
| | Set `decision` on ANY candidate — that is `triage-candidates`'s alone |
| | Set `status` in the candidates file — that is a later process's |
| | Append to or edit `direction.md` |
| | Edit `problem-statement.md`, `architectural_standard.md`, or anything else under `docs/standards/` |
| | Decide WHICH sprint or phase a component belongs in |
| | **Delete anything** — a candidate row, a roadmap, or any file |

**Every row in that MAY NOT column is enforced, not requested, and here is exactly how.** When you finish, the worktree is read and compared against a snapshot taken before you started:

- **Every `docs/development/*/roadmap.md`** is read from disk and digested on both sides. A roadmap that existed before you started and whose content moved **fails the run** — that is `plan-feature`'s file, not yours. A roadmap that is simply GONE fails separately, because the comparison above judges only files present on both sides.
- **Every roadmap you CREATED is read for phase planning.** A line carrying a numbered phase (`phase1_`, `Phase 2`) or a figure with a time unit (`20h`, `40 hours`) fails the run. Saying *that* phases and hours are `plan-feature`'s is fine and expected — the check matches the shape of a plan, not the word "phase".

  **⚠ THIS CHECK CANNOT TELL A QUOTE FROM A PLAN, AND TWO ROWS IN YOUR WORKING SET WILL TRIP IT.** `C-011`'s title ends `(~9 h)` and `C-013`'s contains `Phase 4`. Your charter's *Where it came from* and *Dependencies* sections are exactly where a candidate's wording gets reused. **So when you summarise what a candidate asked for, or name what a component depends on, PARAPHRASE: never carry a phase number or a time figure across into the charter.** Write *"depends on the memory-management-framework's typed exit record"*, not *"depends on MMF Phase 3"*; write *"three cheap guards, sized as a small piece of work"*, not *"(~9 h)"*. Cite the candidate by its id — `` `C-011` `` — and describe it in your own words.
- **Every component directory that appeared** must hold a `roadmap.md`. A folder with no charter in it fails the run.
- **Both candidate columns** — `decision` and `status` — are compared cell by cell on every row that already existed. Appending a NEW row with a blank `decision` is exempt, because you are instructed below to place a proposal that way.
- **Every path outside your authorization** is compared by content, and the rule is the whole directory rather than a list of filenames: **nothing under `docs/development/` except a component's own `roadmap.md`**, nothing under `docs/standards/` except the candidates file, and the sprint plan never. That covers phase docs, the component docs named `<slug>/<slug>.md`, `cpi-decisions.md`, every review artifact and every component's `research/` pool. **Renaming or deleting one counts as editing it.**

Any one of these **fails the whole run**, including the work you did correctly.

**One row is NOT mechanically checked, and you are told which** so the list above is not read as covering everything: *deciding which sprint or phase a component belongs in*. Your charter is required to state what a component depends on, and a dependency and a placement are the same prose in the same file. That one is held by your own discipline and by the reviewer reading your report.

**Never flip a completion checkbox anywhere.** A checkbox means *shipped and validated*. You have validated nothing — you have not even planned anything.

---

## WHAT A CHARTER IS, AND WHAT MAKES IT DIFFERENT FROM A PLAN

This is the whole design of this workflow, so read it before you write a line.

**`plan-feature` runs after you and owns roadmap and phase CONTENT** — the epics, the milestones, the phase breakdown, and the estimated hours per phase. **You must not do any of that.** A run that writes a phase breakdown has built the wrong thing, and it fails mechanically.

**What you write instead is the CHARTER: the scope decision nothing downstream can make for itself.**

| A charter states | A plan states — NOT YOURS |
|---|---|
| What this component IS — the domain it stands up, in one paragraph | How the work is broken into phases |
| What it explicitly is NOT — the boundary against neighbouring components | What each phase achieves |
| Which `C-NNN` candidates it derives from | Milestones and completion criteria |
| Which differentiator in `problem-statement.md` it serves | Estimated hours |
| What it depends on — other components, decisions not yet made | Sequencing against other work |

**Why this is real content and not a stub.** `plan-feature` plans phases *inside* a scope; it does not choose the scope. Research is commissioned *per component pool*, so it needs the component to already mean something. The scope boundary is the one thing neither can supply for itself, and it is what you write.

**This is not hypothetical, and the cost is on disk.** `docs/development/fleet-reliability/` holds five verified research papers and a synthesis — and no planning document of any kind. The research step created that folder with a `mkdir` because nothing ahead of it had written what the component was. Five papers were commissioned into a component no document defines. **You are the step that stops that happening again**, which is also why an empty component folder fails your run.

**A charter is short.** If yours runs past a page, you have started planning.

---

## Stage 1: ASSESS

Read, in this order, and do not skip any:

1. **`${CANDIDATES_PATH}`** — your working set is stated above, counted in code. Read the Note on each `ship` row: it carries the reasoning triage wrote, and that reasoning is what tells you whether two candidates are one domain or two.
2. **`docs/standards/architecture/problem-statement.md`** — the thesis and the differentiators. **You never edit this.** You read it because every charter you write must name the differentiator its component serves, and a component that serves none is one you should not be creating.
3. **`docs/standards/architecture/architectural_standard.md`** — the binding vocabulary and the seams. **A component boundary that cuts across a seam is the wrong boundary**, and the seams are already named here rather than being yours to invent.
4. **`${RESEARCH_DIR}/synthesis.md`** — what the product-level evidence says. **DO NOT READ THE RAW PAPERS.** The Research Standard is explicit that downstream consumers take the synthesis and never the pool. Open a paper only if a specific candidate cannot be placed without it, and say in your report which one and why.

${COMPONENT_INVENTORY}

${EXISTING_WORK}

Report what you found: how many `ship` rows you are working from, and which of them look like they belong together.

## Stage 2: PLACE — the whole of this workflow

**Every `ship` row in your working set gets exactly one of three outcomes. There is no fourth, and two of the three create nothing.**

| Outcome | When | What you do |
|---|---|---|
| **Already has a home** | An open issue tracks it, or a component already exists whose charter or `<slug>.md` covers it | **Nothing.** Name the issue or the component in your report |
| **Extends an existing component** | The work falls inside a component that already exists | **Nothing.** Name the target component. `plan-feature` writes the phase doc and the roadmap row when it runs |
| **Stands up a NEW domain** | No existing component covers it, and it is a distinct domain of work | Create `docs/development/<slug>/roadmap.md` with the charter |

**A component marked ALREADY DEFINED in the inventory above is the second row, never the third.** Its `<slug>.md` is what it is — that is the convention `sprint.md` states for a component that fits in one phase — and a candidate landing inside it EXTENDS it. Do not charter it, and do not read the absence of a `roadmap.md` as an absence of a component.

**Decide with one question, and it is the Documentation Standard's own:** *does this work stand up a new domain, or extend an existing one?* New domain → a component. Extends an existing domain → no scaffolding from you at all.

**MOST ROWS WILL BE ONE OF THE FIRST TWO, and that is the job working rather than the job undone.** You are not measured on how many components you create. A run that scaffolds one component and correctly reports that twenty-six other candidates extend things that already exist has done this job well. A run that invents domains so it has something to write has done it badly, and every invented domain is a durable directory that research and planning will both write into.

**The cheapest correct outcome available to you is a SHELL.** The inventory above marks any component that holds actual research papers and has no document defining it. Adding the `roadmap.md` it never had is *creating* a charter, not editing one — it is permitted, it is cheap, and it repairs a component the pipeline already built blind. **There are two of these today, and the mark is counted from papers rather than from a folder existing** — an empty `research/` directory is a `mkdir`, not evidence, and a component holding one is not a shell.

**Clustering:** several candidates may be one component. Say so explicitly and list every `C-NNN` in that charter's provenance. **One component per domain, never one per candidate** — a component created per row is a directory tree nobody can navigate.

**The slug:** lowercase, hyphen-separated, matching the domain name (`Fleet Reliability` → `fleet-reliability`). The tree already follows this convention and a folder that does not match it is invisible to every reconciliation that walks one against the other.

### The charter, written out

```markdown
# <Component Name>

**Status: CHARTERED — phases are not planned yet. `plan-feature` writes them.**

## What this is

<One paragraph. The domain this component stands up.>

## What this is NOT

<The boundary. Which neighbouring component owns the things a reader would
otherwise assume are in here. This section is the one that stops the next
candidate landing in the wrong place.>

## Where it came from

Derived from `C-NNN`, `C-NNN` — <one line on what those candidates asked for.>

Serves: <the differentiator in problem-statement.md this component exists for.>

## Dependencies

<Other components this needs, and any decision that is not yet made. Say
plainly when there are none.>
```

**Nothing else goes in that file.** No phase list, no milestones, no hour estimate, no implementation notes.

### Where your scope ends

**You never decide when a component gets built.** Not which sprint, not which phase, not in what order. That is sequencing, it happens after you, and the sprint plan is the operator's own surface which you cannot reach.

What you MAY do is **say what you noticed** — *"fleet-reliability already has five papers, so its research step is a no-op"* is useful context for the workflows after you. State it as an observation in your report, never as a decision.

**That is a complete outcome, not a deferral.** A workflow that cannot say "not mine" invents structure for things, and the tree fills with folders nobody can work in because they were never domain-shaped to begin with.

## Stage 3: REPORT

The PR body leads with the placement table. This is the artifact the operator rules on, so it must be readable without opening the diff:

| `C-NNN` | Outcome | Where it lands |
|---|---|---|

Then, separately:

- **Placement summary** — counts across all three outcomes. **They must sum to the `ship` total you were given**; if they do not, say which rows you could not place and why.
- **Components chartered** — every `roadmap.md` you created, with the candidates it covers and the differentiator it serves. **State the boundary you drew for each**, because that boundary is the decision a reviewer is checking.
- **Shells repaired** — any component that had research and no charter, and now has one.
- **Nothing needed** — the candidates that extend an existing component or are already tracked, with which one. This is expected to be the longest section.
- **Not placeable** — any `ship` row you could not place, and what is missing. **An honest "this row is too vague to know what domain it is in" is worth more than a component invented to hold it** — and it is a real finding, because triage ruled it schedulable.

**Answer this plainly**, because it is why this workflow exists:

> Is any component here being stood up because the work genuinely needs its own domain, or because a candidate had nowhere else to go?

## Stage 4: SUBMIT

${SUBMIT_PROMPT}

${DECISION_LOG_AND_REFLECTION}

${HEADLESS_EXECUTION_GUARD}
