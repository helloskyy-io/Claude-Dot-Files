# Research — product level

Evidence that backs **the whole approach**, not any single phase. This is the holistic altitude from [Research Standard §1](../../research/research_standard.md): research that validates the implemented and planned design, drives direction changes, and introduces new concepts.

```
research/
├── topics.md         the SIZE memory — tier, topic list with destinations, named gaps
├── raw/<topic>.md    the pool — one mini-paper per topic
└── synthesis.md      the deliverable — what the pool means for the product's direction
```

**`topics.md` persists what `research.sh` Stage 2 decides.** Stage 2 assesses complexity, produces a topic list, and Stage 3 dispatches on it — but the list has never been written anywhere, so only the papers survive and the *reasoning* is lost between runs. Re-assessed on every touch per §2, never appended: a later run rewrites it with its own assessment.

## Which altitude does a question belong to?

**Here** if the answer could change *what we are building* — the shape of the system, whether an approach is sound, a concept we do not yet use.

**In a phase** (`docs/development/phases/<phase>/research/`) if the answer decides *how to build a thing already committed to*. That is roughly 98% of research: a phase asks a narrow question, gets an answer, and builds.

The test: **would this finding invalidate a phase, or inform one?** Invalidating is product-level. Informing is phase-level.

Examples from this repo's actual queue — *should a parent hand off through a typed file or a parsed log* informs the Memory Management phase and belongs there. *Does splitting authoring from judging actually reduce defects* questions the premise the whole fleet is built on, and belongs here.

## What lands here

- **Findings from the Agentic AI coursework** — the six design principles and the literature behind them. Several already have concrete instances in this platform, arrived at by burn-testing rather than by design; that convergence is itself worth recording, and so are the places we diverge.
- **Anything that reframes the roadmap** rather than advancing one phase of it.

## The same rules apply

**Nothing here is binding.** Research is evidence. A finding becomes a rule only by being codified into a standard through human review — the same path that keeps agents from writing standards. **This is doubly true at this altitude**, because product-level findings are the most tempting to treat as settled: a paper is not a decision, and a principle that matches something we already do is a coincidence worth checking rather than a validation.

**`synthesis.md` is rewritten, never appended.** It is what you read to check the product's direction against the evidence.

```bash
./scripts/workflows/research.sh docs/standards/architecture/research "<the question>"
```
