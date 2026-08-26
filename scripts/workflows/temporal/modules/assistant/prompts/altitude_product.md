## Stage 4b: FILE INTO `tracked/candidates/` — BINDING

`tracked/candidates/` is the **durable** home for action candidates, one file per item. `synthesis.md` is rewritten every cycle; that file is not, and a candidate that lives only in the synthesis loses its disposition the moment the next cycle runs. That has happened: candidates already ruled on were re-proposed, and seven ended up parked on a tracker whose own rules forbid it.

**The division of labour is absolute:**

> **Research creates and appends. Planning dispositions.**

**You set:** `ID` · `Candidate` · `component` · `Source`
**You NEVER set or alter:** `decision` · `status` — those are `triage-candidates`'s and a later process's. Leave `decision` as `—` and `status` as `` `open` `` on every row you add.

**Name the `component` this candidate belongs to when you file it** — an existing `docs/development/<name>/` if it extends one, a new name if it does not. **A blank means nothing is scaffolded for it.** You are the one who knows: you have just written the proposal, and anything downstream would be guessing from a one-line summary. A blank is an unanswered question rather than an error, so leave it blank rather than inventing a name you are not sure of.

${CANDIDATE_CEILING}

### If the store already holds items — read them BEFORE you write

1. **Read every existing item.** You are not choosing ids: `${CANDIDATE_CEILING}` above offered you a batch, minted at random, and **there is no highest-in-use to continue from.**
2. **For each candidate in your synthesis, decide: is this NEW, or a RESTATEMENT of one already there?**
   - **A restatement REUSES the original ID.** Do not mint a new one — increment that item's `count` and append a dated line under `## Recurrences`. If your wording is better, update its `title` in place and leave the `id`, `decision` and `status` untouched. A carried-forward candidate is the *same* candidate.
   - **Only genuinely new candidates get new IDs**, taken from the batch you were offered. **IDs are never reused**, even after a terminal state, and unused ones are simply discarded.
3. **A candidate already marked `reject` must NOT be re-proposed.** They are kept for six months precisely so the reasoning is findable. Read it; if new evidence genuinely overturns it, say so explicitly in the Note and in your PR body rather than quietly adding it again. That file exists so a rejection sticks.
4. **Never delete an item.** Not a rejected one, not a stale one — pruning runs on the Tracked Items Standard §4.2 clock, never on yours.

### If the file does not exist

Create it with the header explaining the two flags, who sets which, and the never-delete / never-renumber rules — then add your candidates starting at `C-d1uhacwn`.

### In your PR body

State plainly: how many candidates you **added**, how many you **restated under an existing ID**, and how many existing rows you **left alone**. A cycle that adds nothing new is a legitimate outcome — say so rather than manufacturing candidates to look productive.

## Stage 4c: A RECOMMENDATION ABOUT WHAT THE PROJECT BELIEVES — BINDING

Some findings are not design work. They are **recommendations about what the project believes** — that a differentiator is overstated, that a comparator is mis-framed, that the problem statement claims something the evidence no longer supports.

**They go in `tracked/candidates/` like everything else, carrying `decision: requires review`.** That field is what says *only the operator can rule on this, and no further automated work makes it ready.*

> **THERE USED TO BE A SECOND FILE FOR THESE and it was deleted on 2026-08-26.** `direction.md` held them as `D-NNN` rows beside the pool. Every row pointed at a candidate that already carried this exact decision, so it added an id and nothing else — and in three weeks nobody ruled a single row on it. **Do not recreate it.** [Tracked Items Standard §8](../../../../../../docs/standards/documentation/tracked_items_standard.md) names a second surface for a class that already has one as a violation.

**You NEVER edit `problem-statement.md`.** It is the thesis every other document derives from, and the judgement in it is not delegable. You recommend; the operator rules.
