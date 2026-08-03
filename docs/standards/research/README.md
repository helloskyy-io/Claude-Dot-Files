# Research Standard — vendored, and where research lives here

`research_standard.md` is a **verbatim MIRROR** from `helloskyy-io/MDC-Master-Planning`. Do not edit it; amendments go upstream, then `scripts/helpers/vendor-standards.sh`.

## Where research lives in this repo

§1 is the rule — *co-location with the consumer beats taxonomy purity* — and it names two altitudes: stack-level research under `standards/architecture/research/`, component-level under `development/<component>/research/`.

§1 names **two altitudes**, and both exist here:

| Altitude | Location | Backs |
|---|---|---|
| **Product** — the holistic layer | [`docs/architecture/research/`](../../architecture/research/) | The whole approach. Findings that could change *what* we build |
| **Phase** — ~98% of research | `docs/development/phases/<phase>/research/` | That phase's planning. Findings that decide *how* to build something already committed to |

The test between them: **would this finding invalidate a phase, or inform one?** Invalidating is product-level; informing is phase-level.

At the phase altitude, a phase is a folder, so research lives *inside* it:

```
docs/development/phases/<phase>/
├── <phase>.md              the phase doc
└── research/
    ├── raw/<topic>.md      the pool — one mini-paper per topic (§3 contract)
    └── synthesis.md        the deliverable — what the pool means for this phase (§4)
```

This is co-location taken as far as it goes: the evidence sits beside the plan that cites it, in the same directory, so neither can be read without the other being one level away. There is no central research corpus to hunt through and no question about which phase a pool belongs to.

**Research is EVIDENCE, not rules.** Nothing under `research/` is binding. A finding becomes binding only by being codified into a standard through the normal human-ratified path — the same governance that keeps agents from writing standards.

## Running it

```bash
./scripts/workflows/research.sh docs/development/phases/<phase>/research "<the question>"
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

- [`../../development/phases/`](../../development/phases/) — the phases, each carrying its own pools
- [`../documentation/`](../documentation/) — research is a distinct non-binding file type there
