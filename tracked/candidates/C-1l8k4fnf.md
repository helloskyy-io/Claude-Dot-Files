---
id: C-1l8k4fnf
title: A research paper's claims ABOUT its sources have no verifier, so a vision paper was weighed as a systematic survey through three critic rounds
status: open
count: 1
filed: 2026-08-17
filed_by: review-pr
component: research-workflow
---

**Found during `review-pr` disposition pass 1 on PR #102.** Pinned to `origin/main` at `15c91a3` and to PR #102's head at `1c428b1e`.

## The consequence

A research paper makes two kinds of claim about a source: **what the source SAYS** (a span), and **what the source IS and where the span came from** (its genre and its fetch path). `research-critic` verifies the first and has no step that reaches the second. So a claim about a source's own nature can be false through every round of verification, and the false claim is often the one carrying the argument's weight.

Two live instances in a single cycle (PR #102), **both of which passed full span-matching by construction**:

1. **[R6] (arXiv 2503.02400) was described as *"a full-lifecycle survey"*** from the first draft through two critic rounds. It is a vision/roadmap paper — it says so itself (*"As a vision paper, this work primarily focuses on articulating the conceptual framework…"*). The paper's §3.5 negative finding (*no prompt-engineering literature on divergence between copies of a prompt*) draws its weight from that source's silence, and **a systematic survey's silence and a vision paper's silence are not the same evidence.** The genre claim was inflating the paper's single strongest negative.

2. **A quoted span was routed to the PDF by the paper's own sourcing note** when it exists only in the arXiv Atom API — `TOSEM` occurs 0 times in the PDF. The sourcing note's declared fetch path was false for that span.

Neither is catchable by the current gate. `grep -F` against a checkout answers *"do these exact characters exist in that file?"* — both spans pass it. The genre defect was ultimately caught not by a critic but by the analyst being asked to *write down the argument* for the claim; the fetch-path defect was caught in round 2 only as a side effect of repairing something else.

## Why the existing remedies do not reach this

- **#37** (quotes that exist in no source) and **#39** (verification agents have no shell) produced the clone-and-grep rule and the `Bash` grant in `config/agents/research-critic.md:76-90`. Both make **span content** verification stronger. Neither can see a claim *about* a span.
- `research-critic.md` was read in full (102 lines): the Verification process (lines 41-47) is enumerate → fetch → match claims → audit confidence → check contract. Step 4 audits confidence by **speaker authority** (first-party vs. community), never by **artifact kind**. Zero occurrences of `genre`, `artifact type`, `fetch path`, `retrieval path` or `provenance` anywhere in the file.
- Research Standard §3 *Sourcing rules* (`docs/standards/research/research_standard.md:103-108`) sets the bar at *"Verbatim means the exact characters were returned"*. Both defects clear that bar.

## Proposed next action

Require each citation entry to state **(a) what kind of artifact the source is** — systematic survey / vision or roadmap paper / empirical study / first-party spec / rendered vendor page — and **(b) which fetch path each of its spans came from** (PDF extraction, raw file, API response, local read). Then give `research-critic` a step that checks both against the fetched source. The analyst on PR #102 independently proposed the same guard, which is worth noting: two actors converged on it from opposite ends of the same cycle.

**The routing is part of the ruling, and it spans two repos:**

- The **per-citation field** is a change to paper *shape* — the artifact contract, which Research Standard §8 assigns to **MDC-Master-Planning**. `docs/standards/research/` here is vendored MIRROR and must not be edited locally.
- The **check** is the HOW, which §8 assigns to this repo: `config/agents/research-critic.md`.

Whether to do both, or only the local check with the field left as agent-side convention, is the decision to make.

## Verification performed

- `config/agents/research-critic.md` read in full; two independent checks for the absence (keyword grep over genre/provenance/fetch-path terms → 0 hits; full read of the Verification process, Rules and Output format sections → no step reaches genre or fetch path).
- Issue queue searched by mechanism, not keyword, across open and closed: #37, #39, #103, #38, #97, #26, #91 — none covers a claim-about-a-source with no verifier. #37/#39 are the nearest and are the ones whose remedy both defects pass.
- `pdfinfo` on a fresh fetch of arXiv 2503.02400 → `Pages: 22`, and the paper's corrected §3.5 now names the genre correctly and records its own prior error.



---

*Migrated from `Claude-Dot-Files#104` on 2026-08-26. Re-triaged from Issue to Candidate: the remedy is capability that does not exist, which §1.1 routes to a proposal.*
