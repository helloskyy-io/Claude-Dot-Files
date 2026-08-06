# Local AI Offloading

**Notes predating planning.** Collected April 2026 and moved here out of the sprint plan. Model management has since gone a different direction — per-workflow explicit `--model` resolved from `config.yaml` — so **the integration points below predate the current design and need re-reading before any of it is built.**

## The idea

Preserve Claude Max rate limits by offloading mechanical work — file summarization, classification, boilerplate — to local GPU hardware. Estimated saving at the time: ~10–15% of Opus turns per workflow with no quality loss on the offloaded tasks.

**Why it was raised (2026-04-12):** real usage showed two concurrent engineers plus a PM session exhausting rate limits in half a metered period. Whether that still holds under the current dispatch pattern has not been re-measured.

Ollama installation and GPU provisioning are handled by SkyyCommand, not this repo.

## Hardware available

```
RTX 4080 (16GB VRAM):
├── Qwen 2.5 Coder 7B (Q4_K_M)  — ~5GB   — candidate for summarization
├── Timpi Node                   — ~1.6GB — passive income (colocated)
└── Free                         — ~9GB

A6000 (48GB VRAM):
├── Qwen 2.5 Coder 14B (Q4_K_M) — ~10GB  — candidate for summarization
└── Free                         — ~38GB
```

## What would get offloaded, and what would not

| Task | Offload? | Why |
|---|---|---|
| File reading for context | **Yes** — summarize for Opus | Simple comprehension |
| Filtering files by relevance | **Yes** — local model scans, tells Opus which to read | Classification task |
| Writing/editing code | **No** | Quality matters |
| Code review | **No** | Nuance matters, and it is already Sonnet |
| Architecture decisions | **No** | Deep reasoning needed |
| Boilerplate generation | **Maybe** — test quality first | Simple patterns |

## Open questions

- **7B or 14B for summarization?** Unanswerable without benchmarking both on real project files for accuracy, completeness and missed detail.
- **Does the current `--model` design leave a seam for this at all?** The April plan assumed an MCP server and delegation rules in the global `CLAUDE.md`. Per-workflow explicit model resolution may make that the wrong shape.
- **Does the Timpi node coexist** with the chosen model without VRAM contention?
