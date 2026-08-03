# Research — continuous-process-improvement

Evidence backing this phase's planning. Governed by [`research_standard.md`](../../../../standards/research/research_standard.md).

```
research/
├── raw/<topic>.md    one mini-paper per topic — sources, per-claim confidence, gaps stated as findings
└── synthesis.md      the curated deliverable: what the pool means for THIS phase's direction
```

**`raw/` is the pool.** One paper per topic, each carrying 10–20 credible sources, confidence marked per claim, and an honest-boundary section. `research-critic` fetches every citation before a pool merges — a fabricated source is invisible to the actor that wrote it.

**`synthesis.md` is the deliverable.** Continuously rewritten, never appended. It is what you read to check the build direction against the evidence, and it is the only file in here the phase doc should need to cite.

**Nothing here is binding.** Research is evidence; a finding becomes a rule only by being codified into a standard through human review. This phase doc may *cite* a pool — it may not treat one as a decision already made.

Create a pool by asking a question:

```bash
./scripts/workflows/research.sh docs/development/phases/continuous-process-improvement/research "<the question>"
```
