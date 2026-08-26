## Stage 4b: STAY IN YOUR LANE — BINDING

**You are running at COMPONENT altitude.** The pool you are building serves ONE component's planning, and the Research Standard §1 is explicit about what that means: a component research folder holds **`raw/` and `synthesis.md`**, and nothing else. Do not create `candidates.md` and do not create `direction.md` — those exist only at the product pool, which is a different altitude with a different consumer.

Your action candidates live in `synthesis.md`, as §4 requires. That is their home here. They are read by whoever writes this component's phase doc.

### What "your lane" means, concretely

**The question you are answering is: how do we build this thing we have already committed to building.** Not whether to build it, not whether the approach is right, not whether it serves the thesis. Those were settled before this component became a component, and re-opening them is not thoroughness — it is a different piece of work, at a different altitude, with a different reviewer.

The Standard's own test: **would this finding INVALIDATE a phase, or INFORM one?** Informing is yours. Invalidating is not.

### Upstream evidence — cite it, never re-derive it

The product-level research pool is supplied to you below as read-only context. It is the accumulated evidence about *what* this project is and what it has already settled.

**Use it. Do not repeat it.** A topic already covered upstream does not need a second paper here — cite the upstream paper and move on. Re-researching a settled question burns a cycle and produces a second answer that can drift from the first, which is worse than no answer.

**You may not write to the product pool.** Not a paper, not a row, not a correction. Your write boundary is `${RESEARCH_DIR}` and only that.

### If you find something above your altitude — ESCALATE, do not act

You may turn up a finding that bears on what the project believes rather than how this component is built: a differentiator that no longer holds, a settled stack decision the evidence now contradicts, an assumption the whole approach rests on that nobody named.

**That is a real finding and you must not bury it.** It is also not yours to file.

1. **State it in `synthesis.md`** under a clearly-marked heading: `## Escalations — findings above this component's altitude`. One entry each: what you found, what it bears on, and what you think it means.
2. **Repeat it in your PR body as its own table**, separate from the component's action candidates. The operator reads escalations differently from candidates — an escalation may stop other work.
3. **Do NOT write it into the product pool's `tracked/candidates/`.** Those files are the product pool's, and a component run appending to them means the operator's inbox is being written by runs that were never scoped to it. Surface it; the operator files it.

**An escalation is rare.** If you produce more than one or two, that is a signal you have drifted upward rather than a signal the project is in trouble — say so plainly rather than presenting drift as findings.
