**EVERY PHASE ENTRY CARRIES A `**Depends on:**` LINE** — Documentation Standard § Development Planning Files rule 9. It sits beneath the entry, under `**Implementation:**` where that exists.

```
### The first dispatch 🟠 PLANNED

**Implementation:** [`phase5_the_first_dispatch.md`](phase5_the_first_dispatch.md)
**Depends on:** [persistent-memory-protocol · The journal root and the run bag](../persistent-memory-protocol/phase1_the_run_bag.md) · [Tracked Items Standard](../../standards/documentation/tracked_items_standard.md) — §0 only
```

Each dependency is a markdown link, ` · ` separated. Prose around them is welcome — a reader keys on the words and the parser reads only the links, so conditionality survives both.

- **A phase with nothing gating it writes `**Depends on:** NONE`.** A MISSING line is a defect, not a declaration: a blank cannot tell a reader whether somebody assessed this phase or whether the line was lost, and a mechanical pass has already damaged one in this ecosystem.
- **`NONE` is UNQUALIFIED** — the word, then the end of the clause. *"NONE internal"* and *"NONE inside this component"* are SCOPED claims meaning *and something outside it*, so writing one silently deletes a real dependency.
- **Declare FORWARD only.** What is gated on THIS component is derived by reading the corpus. Writing it here as well is one fact in two files, and two carriers disagree eventually.
- **Never write whether a dependency is SATISFIED.** That derives from the target's own status marker. A state written by hand is correct the day it is written and silently wrong afterwards.
- **A dependency is on an ARTIFACT.** An operator ruling not yet made, or a question not yet researched, is a REQUIREMENT of the phase — it belongs in the phase doc, or in this entry's prose where no phase doc exists yet. A graph node with no target cannot be resolved, sequenced or satisfied.
- **Declare what your research supports, and `NONE` where it supports nothing.** A dependency stated confidently and wrongly renders as an authoritative edge that work is sequenced from.
- **NEVER DELETE ONE YOU DID NOT AUTHOR.** If you are editing a roadmap and a `**Depends on:**` line is already there, it stays unless you are deliberately correcting it and say so. Dropping it converts a real dependency into a conformant "depends on nothing".

**`roadmap.md` is the SINGLE carrier.** A phase doc does not restate its dependencies; where it needs to discuss one it cites the roadmap entry.
