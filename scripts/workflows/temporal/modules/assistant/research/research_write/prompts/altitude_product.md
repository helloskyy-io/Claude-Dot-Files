## Stage 4b: APPEND TO `candidates.md` — BINDING

`${RESEARCH_DIR}/candidates.md` is the **durable** home for action candidates. `synthesis.md` is rewritten every cycle; that file is not, and a candidate that lives only in the synthesis loses its disposition the moment the next cycle runs. That has happened: candidates already ruled on were re-proposed, and seven ended up parked on a tracker whose own rules forbid it.

**The division of labour is absolute:**

> **Research creates and appends. Planning dispositions.**

**You set:** `ID` · `Candidate` · `component` · `Source`
**You NEVER set or alter:** `decision` · `status` — those are `triage-candidates`'s and a later process's. Leave `decision` as `—` and `status` as `` `open` `` on every row you add.

**Name the `component` this candidate belongs to when you file it** — an existing `docs/development/<name>/` if it extends one, a new name if it does not. **A blank means nothing is scaffolded for it.** You are the one who knows: you have just written the proposal, and anything downstream would be guessing from a one-line summary. A blank is an unanswered question rather than an error, so leave it blank rather than inventing a name you are not sure of.

${CANDIDATE_CEILING}

### If the file already exists — read it BEFORE you write

1. **Read every existing row.** Note the highest `C-NNN` in use.
2. **For each candidate in your synthesis, decide: is this NEW, or a RESTATEMENT of one already there?**
   - **A restatement REUSES the original ID.** Do not mint a new one. If your wording is better, update the `Candidate` cell in place and leave the ID, `decision` and `status` untouched. A carried-forward candidate is the *same* candidate.
   - **Only genuinely new candidates get new IDs**, continuing from the highest in use. **IDs are never reused and never renumbered**, even if a row is rejected.
3. **A candidate already marked `reject` must NOT be re-proposed.** Read the reasoning; if new evidence genuinely overturns it, say so explicitly in the Note and in your PR body rather than quietly adding it again. That file exists so a rejection sticks.
4. **Never delete a row.** Not a rejected one, not a stale one.

### If the file does not exist

Create it with the header explaining the two flags, who sets which, and the never-delete / never-renumber rules — then add your candidates starting at `C-001`.

### In your PR body

State plainly: how many candidates you **added**, how many you **restated under an existing ID**, and how many existing rows you **left alone**. A cycle that adds nothing new is a legitimate outcome — say so rather than manufacturing candidates to look productive.

## Stage 4c: APPEND TO `direction.md` — BINDING

Some findings are not design work. They are **recommendations about what the project believes** — that a differentiator is overstated, that a comparator is mis-framed, that a claim rests on an assumption nobody named. Those belong to the operator, not to a planner and not to you.

`${RESEARCH_DIR}/direction.md` is where they go.

> **`candidates.md` is the machine's document. `direction.md` is the human's.**

**You NEVER edit `problem-statement.md`.** It is the thesis every other document derives from, and the judgement in it is not delegable. You recommend; the operator rules; the operator writes.

### What belongs here rather than in `candidates.md`

| Goes in `direction.md` | Goes in `candidates.md` |
|---|---|
| A differentiator is overstated, refuted, or should be restated | Build this, adopt that, decide a ruling |
| The problem statement claims something the evidence no longer supports | A standards amendment, a phase item, a guard to ship |
| A comparator is mis-framed or missing an axis | Anything with an implementation |
| A stated assumption is load-bearing and unnamed | |

**If you cannot tell, ask: does acting on this change what we BELIEVE, or what we BUILD?** Belief goes here.

### Row shape

| ID | Recommendation | Why it matters | Source | `status` |

**You set:** `ID` · `Recommendation` · `Why it matters` · `Source`.
**You NEVER set `status`** — that is the operator's, and it is one of `open` · `applied` · `rejected`. Leave it `` `open` ``.

### If the file already exists

Same discipline as `candidates.md`: **read every row first**, reuse the original ID for anything you are restating, never renumber, never delete, and **do not re-propose something already marked `rejected`** unless new evidence overturns it — in which case say so explicitly.

IDs are `D-001`, `D-002`, … and are independent of the `C-` series.

**You are not the only writer.** `triage-candidates` also appends here — it is where a candidate it triages as `requires review` gets handed to the operator, carrying its `C-NNN` in the Source column. So **read every row and continue from the highest ID**; never assume the file holds only your own cycles' rows.

### In your PR body

**List the `direction.md` items separately from the candidates, as their own table.** They are the reason a research PR carries `HOLD - needs-assistance` rather than merging unattended: a human must rule on them, and no number of additional passes can produce that ruling.
