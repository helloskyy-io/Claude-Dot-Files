# Hook Sourcing Supplement

```
Topic:          Where do hooks load from, and what survives a change to setting sources?
Feeds:          Phase: Managed Configuration — setting-source loading, and the hook that survives it
Last validated: 2026-07-25
Revalidate:     high — 4 weeks
Confidence:     Definitive on documented loading order; UNVERIFIED on whether a narrowed --setting-sources drops the PreToolUse hook in practice — untested.
Critic:         PASS — 2026-07-25
```

Targeted gap-filling pass against `production_cases.md`. Scope: strengthen the opening hook's weakest citation (Replit's uptime figure, vendor-sourced) and test whether the "reinvent-then-adopt" claim is a pattern or an anecdote.

## Bottom line

**Yes — the hook can be materially strengthened, and one claim in the existing sweep is now wrong.** Cursor published a first-party engineering post (June 2, 2026) describing the exact reinvent-then-adopt arc: they built a work-stealing orchestrator, ran their cloud-agent beta at "one 9 of reliability," realized they were "on the verge of rebuilding a lot of the durable execution primitives that Temporal already solves," and migrated. This is a *better* citation than Replit — it is first-party, self-critical, and includes both a before number and an after number. The existing sweep states Cursor has "no public claim of workflow-level durable execution"; that entry is stale and must be corrected. Second, the OpenAI Codex citation upgrades from "vendor asserts" to a **named OpenAI engineer on the record**. Third, a genuine counter-case surfaced (Harvey) that the paper should absorb rather than ignore. Priorities 3 and 4 largely came up empty: the "teams lose N hours/week" number **does not exist**, and there is **no independent (non-vendor-funded) analysis** of durable execution for agents worth citing.

---

## §1 Additional reinvent-then-adopt cases

### Cursor — FIRST-PARTY, definitive. The strongest case in the corpus.

"What we've learned building cloud agents," Josh Ma, Cursor, June 2, 2026.

The full arc, in their own words:

- **What they built:** "We started building cloud agents with a work-stealing architecture, where worker nodes could pick up agents and loop them to completion."
- **What failed:** "It transplanted what works locally to a server and it was a fragile setup—our early beta of cloud agents often operated at one 9 of reliability." Exposure cited: "inference provider outages, pods needing to be replaced, and EC2 nodes going down."
- **The realization (the money quote for this paper):** "As cloud agents matured, we found ourselves on the verge of rebuilding a lot of the durable execution primitives that Temporal already solves (e.g., retry mechanisms, scheduling work across machines, durability across node failures), so instead we migrated there."
- **After:** "past two 9s of reliability"; Temporal "handles more than 50 million actions per day across more than 7 million unique workflows"; agent runs now survive "pod hibernation and resumption, and runs that stretch across days or weeks." Also: "more than 40% of our PRs come from cloud agents."

Why this beats Replit for the hook: the failure number (one 9) is *self-reported by the company that failed*, not by the vendor that sold them the fix. Note the honesty asymmetry — Cursor claims two 9s, an order of magnitude more modest than the 99.9999% in Temporal's Replit case study. That contrast is itself an argument for citing Cursor first.

**Corrects the existing sweep.** `production_cases.md` §2 currently reads: "There is no public claim of workflow-level durable execution; the durability is at the VM/repo-clone layer." That is now false and should be rewritten.

### Harvey — FIRST-PARTY. A documented *counter*-case; the paper is stronger for engaging it.

"Why we Built our own Cloud Agent Infrastructure," Gabe Pereyra, Harvey, June 1, 2026.

Harvey built their own cloud-agent runtime rather than adopting a managed one, and their stated reason is a real constraint, not ignorance: **"Automatic state persistence and zero retention are mutually exclusive; you cannot have both."** Every law-firm and enterprise contract they sign "requires zero data retention," and "the frontier labs' managed runtimes don't offer ZDR." Their runtime scopes state to sessions and purges it after execution; agents keep "working memory, intermediate files, tool results, and the checkpoints it uses to recover from interruptions," but that state is lifecycle-bound by design.

This is the most useful thing found after Cursor. It identifies the boundary condition on the paper's thesis: durable execution's core mechanism — journaling every step — is in direct tension with data-retention compliance. A paper that names this constraint is harder to attack than one that doesn't. Harvey's separate "Resilient AI Infrastructure" post (April 22, 2025) discusses only load balancing, fallbacks, and retries; no durable execution, no checkpointing, no workflow engine. Confirms the build-your-own posture.

### Searched, nothing found

Cognition/Devin, Factory, Sourcegraph Amp, Reflection AI, Magic, Poolside, Augment Code, All Hands/OpenHands, Warp, Zed, Perplexity, Sierra, Decagon, Parahelp, Lindy, Gumloop, Relay, Wordware: **no public architecture post describing a durability migration.** Cohere appears in an Inngest testimonial and Yutori in a DBOS one, but neither describes a failed custom system — they are vendor testimonials, not arcs. Do not cite.

## §2 First-party sources for existing citations

**OpenAI Codex — upgraded, but not to first-party.** A named OpenAI engineer is on the record: **Will Wang, software engineer on Codex at OpenAI** — "Temporal is a critical part of the infrastructure powering Codex, responsible for executing our core control flows." Separately, **Venkat Venkataramani, VP of App Infrastructure at OpenAI** — "Durable execution is a core requirement for modern AI systems, and Temporal offers a compelling platform to help build it in from the start." Both are hosted on Temporal's site, so still vendor-published, but named-attribution to identified OpenAI staff is a meaningfully stronger citation class than "Temporal's materials name OpenAI."

**OpenAI's own posts never name Temporal.** "Unlocking the Codex harness: how we built the App Server" and "An open-source spec for Codex orchestration: Symphony" both discuss durability at the *harness* layer — threads as "the durable container for an ongoing Codex session," a rollout system persisting events as JSONL indexed in SQLite, replay-on-resume to reconstruct model state, and in Symphony's case an Elixir/OTP supervision tree where "if an agent crashes or stalls beyond a configurable `stall_timeout_ms`, Symphony terminates and restarts it." OpenAI publishes extensively about durability and never mentions its durable-execution vendor. Note both openai.com URLs return 403 to automated fetching; content above is from search indexing and third-party coverage, so quote them only after manual browser verification.

**Lovable — confirmed absent.** No first-party engineering post, conference talk, or podcast transcript on orchestration or Temporal. Available material (TechAhead, OTF, System Design Space) is third-party reconstruction. The one substantive claim in circulation — that Lovable "tried complex multi-agent orchestration and abandoned it" — traces to secondary write-ups, not to Lovable. **Recommend dropping Lovable from the hook** and keeping it, if at all, in the body with an explicit secondary-source marker.

## §3 Quantified failure cost — mostly absent

**The number you wanted does not exist.** No survey, postmortem corpus, or study measures hours or dollars lost to agent runs dying on infrastructure failure. Closest available:

- **"Measuring Agents in Production,"** arXiv 2512.04123 (Pan et al., incl. Stoica, Zaharia, Gonzalez, Song, Sen; Dec 2, 2025, rev. June 4, 2026). 306 practitioners, 20 interview case studies, 26 domains. **Reliability is the top development challenge**, and **68% of production agents execute at most 10 steps before human intervention.** This is the best number in the supplement: it shows practitioners *truncating agent horizons* to stay inside what their infrastructure survives. That is the paper's thesis measured from the demand side, in a non-vendor academic source.
- **METR time horizons** (metr.org, March 2025, updated through 2026): 50%-success task length doubling every ~7 months, accelerating to ~4 months in 2024–25. Useful for the "horizons are lengthening" half of the argument. Caveat: METR measures *model capability*, not infrastructure failure — do not present it as evidence of durability problems.

Pairing these two is the honest version of a scale claim: horizons are growing (METR) while practitioners cap agents at ≤10 steps because reliability won't hold (MAP). No fabricated hours-lost figure needed.

## §4 Independent analysis — effectively absent

- **VentureBeat, "AI agents are entering their rebuild era"** looks like the ideal independent source and **is not.** Temporal sponsored VentureBeat's AI Impact Series where this reporting originated, and the featured expert is Temporal's own SVP of Engineering. **Do not cite as independent.**
- **InfoQ** (Craig Risi, Sept 18, 2025) covers the Temporal/OpenAI integration but is vendor-announcement reporting with no independent verification.
- **"Measuring Agents in Production"** (§3) is the only genuinely independent, academically-vetted source found — but it studies production agents generally and does not treat durable execution as a named category.
- A large volume of SEO content (Zylos Research, Quellix Labs, AppScale, Spheron, noqta, IntuitionLabs) discusses this topic. It is low-provenance and frequently unattributed. **Do not cite any of it.**

**Finding worth stating in the paper:** the near-total absence of non-vendor analysis is itself evidence for the paper's contribution. The category has no independent literature yet. That is a gap a research paper is entitled to claim.

## §5 Recommendation

**Change the hook. Lead with Cursor, support with Replit.**

1. **Open on Cursor, not Replit.** First-party, self-critical, both-ends quantified, and the "on the verge of rebuilding a lot of the durable execution primitives that Temporal already solves" line states the paper's thesis in a practitioner's own voice. Best sentence available for the opening.
2. **Keep Replit as the second case** — it supplies the user-facing failure narrative Cursor lacks (Catasta's "you lose everything"). **Attribute the 99.9999% figure in-text to Temporal's case study** rather than asserting it. Better: cite Cursor's "two 9s" as the load-bearing number and let Replit's six 9s be the vendor's claim, explicitly labeled. Two independent companies, same arc, same year, is a pattern.
3. **Add the OpenAI Codex named quote** (Will Wang) as a third data point, marked vendor-hosted-but-named. **Drop Lovable from the hook.**
4. **Add scale via MAP, not via a fabricated cost figure.** "68% of production agents execute at most 10 steps before human intervention" + METR's lengthening horizons opens with measured scale honestly.
5. **Engage Harvey in the body.** Naming the state-persistence/zero-retention conflict pre-empts the strongest objection and demonstrates the thesis was tested, not assumed.
6. **State the independent-literature gap explicitly** as motivation.

If time forces one change only: **swap Cursor in as the lead case and label Replit's uptime figure as vendor-reported.** That single edit removes the weakest-citation problem and converts the anecdote into a pattern.

## Citations

| # | Source | Class |
|---|---|---|
| 1 | Josh Ma, "What we've learned building cloud agents," Cursor, June 2, 2026. https://cursor.com/blog/cloud-agent-lessons | **First-party — definitive** |
| 2 | Gabe Pereyra, "Why we Built our own Cloud Agent Infrastructure," Harvey, June 1, 2026. https://www.harvey.ai/blog/why-we-built-our-own-cloud-agent-infrastructure | **First-party — definitive** |
| 3 | "Resilient AI Infrastructure," Harvey, April 22, 2025. https://www.harvey.ai/blog/resilient-ai-infrastructure | **First-party — definitive** |
| 4 | Will Wang (SWE, Codex, OpenAI), quoted in "Improving our Java SDK with Codex by OpenAI," Temporal, May 17, 2025. https://temporal.io/blog/improving-java-sdk-codex-openai | Vendor-hosted, **named first-party attribution** |
| 5 | Venkat Venkataramani (VP App Infrastructure, OpenAI), testimonial on https://temporal.io/ | Vendor-hosted, **named first-party attribution** |
| 6 | "Unlocking the Codex harness: how we built the App Server," OpenAI. https://openai.com/index/unlocking-the-codex-harness/ | First-party — *verify manually, 403 to fetch* |
| 7 | "An open-source spec for Codex orchestration: Symphony," OpenAI. https://openai.com/index/open-source-codex-orchestration-symphony/ | First-party — *verify manually, 403 to fetch* |
| 8 | Pan et al., "Measuring Agents in Production," arXiv:2512.04123, Dec 2, 2025 (rev. June 4, 2026). https://arxiv.org/abs/2512.04123 | **Independent academic — strongest non-vendor source** |
| 9 | "Measuring AI Ability to Complete Long Tasks," METR, March 19, 2025. https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/ | Independent research org |
| 10 | Craig Risi, "Temporal and OpenAI Launch AI Agent Durability," InfoQ, Sept 18, 2025. https://www.infoq.com/news/2025/09/temporal-aiagent/ | Secondary — vendor-announcement reporting |
| 11 | "AI agents are entering their rebuild era," VentureBeat. https://venturebeat.com/orchestration/ai-agents-are-entering-their-rebuild-era-as-enterprises-confront-the-reliability-problem | Secondary — **Temporal-sponsored, not independent** |
| 12 | Temporal/OpenAI integration press release, BusinessWire, July 30, 2025. https://www.businesswire.com/news/home/20250730783559/en/ | Vendor press release — Temporal quotes only, no OpenAI attribution |

**Explicitly not found (do not invent):** any survey quantifying hours or dollars lost to failed agent runs; any Lovable first-party engineering source; any non-vendor-funded analyst or trade-press analysis of durable execution for agents; any reinvent-then-adopt post from Cognition, Factory, All Hands, Warp, Sierra, Decagon, Perplexity, or the other startups checked.

**Verification note:** the Will Wang quote appeared in search summaries before I confirmed it against Temporal's post; it is now verified there. It does *not* appear in the BusinessWire release, contrary to what one search summary implied. Citations 6 and 7 rest on search-index and third-party rendering of pages that block automated fetching — read them in a browser before quoting.
