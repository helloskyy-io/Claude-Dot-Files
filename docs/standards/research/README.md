# Research Standard — vendored, and where research lives here

`research_standard.md` is a **verbatim MIRROR** from `helloskyy-io/MDC-Master-Planning`. Do not edit it; amendments go upstream, then `scripts/helpers/vendor-standards.sh`.

## Where research lives in this repo

§1 is the rule — *co-location with the consumer beats taxonomy purity* — and it names two altitudes: stack-level research under `standards/architecture/research/`, component-level under `development/<component>/research/`.

**Our consumer is a phase**, so the mapping is:

```
docs/development/research/<topic>/
├── raw/<paper>.md      one mini-paper per topic (§3 contract)
└── synthesis.md        the curated decision deliverable (§4)
```

It sits in `docs/development/` beside `roadmap.md` and `phases/`, because those are what cite it. A phase that needs evidence gets a research pool next to it, not in a separate corpus.

**Research is EVIDENCE, not rules.** Nothing under `research/` is binding. A finding becomes binding only by being codified into a standard through the normal human-ratified path — the same governance that keeps agents from writing standards.

## Running it

```bash
./scripts/workflows/research.sh docs/development/research/<topic> "<the question>"
./scripts/workflows/research-refresh.sh          # revalidates papers that have come due
```

`research.sh` takes the pool directory as its first argument and reads this standard to know the artifact contract. `research-refresh.sh` gates in bash on what is actually due, so a run with nothing due exits clean without spending a model call.

The pairing is the point: `research-analyst` gathers sources and writes the paper; `research-critic` **fetches every citation** to confirm it exists and supports the claim. A fabricated source is invisible to the actor that wrote it, which is why the second pass is a gate rather than a proofread.

## What this unblocks

Three queued phases need evidence before they can be planned, and all three are currently reasoning from a single interactive session's worth of searching:

- **Memory Management Framework** — the inter-process handoff contract. Prior art was surveyed once, informally, and explicitly flagged as *suggestive only, needs real research*
- **Managed Configuration** — the managed/user boundary, and whether `--agents` is workable at our prompt sizes
- **Temporal Integration** — the two known SDK constraints: heartbeating for 10–60 minute activities, payload limits for transcripts

## Related

- [`../../development/research/`](../../development/research/) — the pools
- [`../documentation/`](../documentation/) — research is a distinct non-binding file type there
