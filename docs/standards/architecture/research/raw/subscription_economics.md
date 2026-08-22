# Subscription Economics as Enabler — does flat-rate edge billing actually make wasteful loops affordable?

```
Topic:          Does flat-rate, edge-held subscription billing actually make long-running autonomous agent loops economically accessible — and what erodes that?
Feeds:          docs/standards/architecture/problem-statement.md § "Affordability is the enabler"
Last validated: 2026-08-03
Revalidate:     high — 2 weeks
Confidence:     Definitive on published per-token prices, plan reset-window mechanics, and the documented existence of session/weekly caps (all from first-party raw-markdown docs). Directional on the status of the paused Agent SDK billing split. Unverified on absolute per-plan allowance quantities — Anthropic does not publish them. Derived on every cost-band and subsidy-ratio estimate, on the cross-element inference in §5.1(a) that underwrites this paper's proposed correction to problem-statement.md, and on the policy-change base rate in §4.11 — each marked at the point of use.
Critic:         PASS-WITH-FIXES (round 3: the 2026-07-10 go-live attribution withdrawn — the cited page is a pre-pause prospective explainer and makes no such claim; the paused-not-withdrawn posture re-based on its independent first-party grounds) — 2026-08-03
```

---

## §0 Bottom line, before the arc

**The topic is the right question, and the claim under test does not survive in its stated form.**

> "A long-running loop costs the same as a short one. Being wrong costs nothing but time."
> — `problem-statement.md` § *Affordability is not a footnote*

Three findings, each first-party, each load-bearing:

1. **A usage cap is a second metering surface, and Anthropic's own docs say it binds on exactly this workload.** Claude Code's error reference states, verbatim: *"A single burst of heavy activity, such as a large workflow fanout, can exhaust the weekly allowance before the session window resets."* ([errors](https://code.claude.com/docs/en/errors.md), fetched 2026-08-03, raw markdown — **definitive**). The dollar cost of the extra turn is zero; the allowance cost is not. The correct restatement is *below the plan ceiling the marginal dollar cost of a turn is zero*, which is a materially weaker and materially different claim.

2. **The overage path is metered billing at list prices.** Usage credits are *"billed at standard API rates"* ([support: extra usage](https://support.claude.com/en/articles/12429409-extra-usage-for-paid-claude-plans), rendered page — **definitive but quote-conservative**). The subscription is therefore a prepaid block on the metered curve, not an escape from it. Past the block: wait (time) or pay (dollars).

3. **The specific invocation this architecture depends on — `claude -p` — has already been formally announced as moving off the subscription pool onto a dollar-denominated credit at API list rates, and that change is currently *paused*, not withdrawn.** Anthropic's support article carries a banner reading *"Update June 15: We're pausing the changes to Claude Agent SDK usage described below. For now, nothing has changed: Claude Agent SDK, `claude -p`, and third-party app usage still draw from your subscription's usage limits."* ([support: Agent SDK with your plan](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan), fetched 2026-08-03 — **definitive as of fetch**). The body of the same page describes the change in future tense: Pro $20 / Max 5x $100 / Max 20x $200 per month of Agent-SDK credit. If it un-pauses, the edge tier's economics invert overnight.

The affordability argument does not collapse — it narrows. What it defensibly buys is *removal of the per-decision cost question below a ceiling*, not *free waste*. §5 argues the case against it as strongly as the evidence permits, and answers it.

**Dependency note (do not re-litigate here):** whether edge-held subscription auth is *permitted* is settled by [`anthropic_tos_and_enterprise.md`](anthropic_tos_and_enterprise.md) — `Last validated: 2026-07-24`, `Revalidate: high — 4 weeks`, `Critic: PASS`. Under §5's mechanical gate it is **due 2026-08-21 and therefore current**, so claims borrowed from it below carry its own confidence marks rather than a staleness discount. (`temporal.md` is the pool's only past-window paper this cycle.) This paper's question is economic. The two touch at exactly one point, noted in §4.6.

---

## §1 Primer — the two billing shapes, and the third one nobody names

**Metered per-token billing.** You pay per million input and output tokens, per model, with modifiers for caching, batching, data residency, and speed. Cost is linear in work done, with no ceiling and no floor. ([Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing.md), raw markdown — **definitive**.)

**Flat-rate subscription.** A fixed monthly fee. Cost is constant in work done — *up to a limit*. Every consumer AI subscription in this survey has a limit; none of them is unlimited.

**The third shape, which is what actually exists: a prepaid block with a wall and an optional metered spillover.** Anthropic's plans reset on *"a rolling five-hour window and a weekly window"* ([costs](https://code.claude.com/docs/en/costs.md), raw markdown — **definitive**). When you hit either, Claude Code emits one of:

```
You've hit your session limit · resets 3:45pm
You've hit your weekly limit · resets Mon 12:00am
You've hit your Opus limit · resets 3:45pm
```

and *"blocks further requests until the reset time shown in the message. The session and weekly limits are shared across all models, so switching models doesn't restore access."* ([errors](https://code.claude.com/docs/en/errors.md) — **definitive**.)

This third shape is the one the problem statement's claim has to be evaluated against. Its cost curve is **flat, then a wall, then linear** — not flat. The interesting question is where the wall sits relative to an unattended loop's appetite.

---

## §2 The specific model — what Anthropic's plans actually state

### 2.1 Prices (first-party, raw markdown — definitive)

Subscription (from [claude.com/pricing](https://claude.com/pricing) and [support: what is the Max plan](https://support.claude.com/en/articles/11049741-what-is-the-max-plan), both **rendered pages — reduced confidence**; the two fetches agreed on Pro and Max 5x and *disagreed* on Max 20x, so the Max 20x figure is taken from the support article only):

Confidence class per the four permitted values; *provenance* (raw vs rendered fetch, one source vs two) is annotated separately, per §4's raw-source rule.

| Plan | Price | Confidence | Provenance |
|---|---|---|---|
| Free | $0 | definitive | rendered, single source |
| Pro | $20/mo ($17 annual) | definitive | rendered, two sources agree |
| Max 5x | $100/mo | definitive | rendered, two sources agree |
| Max 20x | $200/mo | definitive | rendered, **single** source — the `claude.com/pricing` fetch rendered Max 20x as "From $100/month", which the support article contradicts at $200. First-party documentation exists (hence definitive), but corroboration does not. **Stated as a fetch defect, not smoothed over**; re-check on next touch. Independently consistent with the Agent SDK credit tiers in §2.4, which list Max 20x at $200 |
| Team | $20–25/seat standard; $100–125/seat premium | definitive | rendered, single source |
| Enterprise | $20/seat + usage at API rates | definitive | rendered, two sources agree |

Metered, per million tokens ([pricing.md](https://platform.claude.com/docs/en/about-claude/pricing.md), raw markdown — **definitive**), abridged to what a coding loop would plausibly use:

| Model | Input | 1h cache write | Cache read | Output |
|---|---|---|---|---|
| Claude Opus 5 | $5 | $10 | $0.50 | $25 |
| Claude Sonnet 5 (through 2026-08-31) | $2 | $4 | $0.20 | $10 |
| Claude Sonnet 5 (from 2026-09-01) | $3 | $6 | $0.30 | $15 |
| Claude Haiku 4.5 | $1 | $2 | $0.10 | $5 |
| Claude Opus 4.1 (deprecated) | $15 | $30 | $1.50 | $75 |

Batch API: *"a 50% discount on both input and output tokens."* Prompt caching: 5-minute write 1.25x, 1-hour write 2x, cache read 0.1x. ([pricing.md](https://platform.claude.com/docs/en/about-claude/pricing.md) — **definitive**.)

### 2.2 The limits, in their own words — and the shape of the gap

What Anthropic **does** publish (all **definitive**):

- Reset windows: *"a rolling five-hour window and a weekly window"* ([costs](https://code.claude.com/docs/en/costs.md)); *"Weekly limits reset at a fixed time each week that is assigned to your account"* ([support: Max plan](https://support.claude.com/en/articles/11049741-what-is-the-max-plan), rendered).
- Relative multipliers: *"Max 5x provides 5 times more usage per session than the Pro plan"*; *"Max 20x provides 20 times more usage per session"* (same source, rendered).
- Two weekly limits on Max: *"one that applies across all models and another for Sonnet models only"* (same source, rendered).
- Shared pool across surfaces: *"all activity in both tools counts against the same usage limits"* ([support: Claude Code with Pro or Max](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan), rendered).
- A reservation of further discretion: *"To manage capacity and ensure fair access to all users, we may limit your usage in other ways, such as weekly and monthly caps or model and feature usage."* ([support: Max plan](https://support.claude.com/en/articles/11049741-what-is-the-max-plan), rendered.)

**What Anthropic does not publish: any absolute quantity.** No token count, no message count, no hour figure, on any current first-party surface.

**Search method for that negative finding** (§3 requires it): fetched `code.claude.com/docs/en/costs.md`, `errors.md`, `feature-availability.md`, `routines.md`, `scheduled-tasks.md`, `github-actions.md`, `agent-sdk/cost-tracking.md` (all raw markdown, complete pages); `platform.claude.com/docs/en/about-claude/pricing.md` (raw markdown); `claude.com/pricing`; support articles 11049741 (Max), 11145838 (Claude Code on Pro/Max), 9797557 (usage-limit best practices), 12429409 (usage credits), 14782391 (Enterprise consumption guide), 15036540 (Agent SDK credit); and `anthropic.com/news/higher-limits-spacex`. Two targeted web searches for a published hour or token figure. The only absolute figures located anywhere trace to a **July 2025 press statement**, not a current doc.

Those 2025 figures, for calibration only (**unverified — secondary, one year stale, and superseded by an announced doubling**): Pro *"40 to 80 hours of Sonnet 4"* weekly; Max $100 *"140 to 280 hours of Sonnet 4 and 15 to 35 hours of Opus 4"*; Max $200 *"240 to 480 hours of Sonnet 4 and 24 to 40 hours of Opus 4"* ([TechCrunch, 2025-07-28](https://techcrunch.com/2025/07/28/anthropic-unveils-new-rate-limits-to-curb-claude-code-power-users/)). Anthropic later announced *"Doubling Claude Code's five-hour rate limits"* for Pro, Max, Team and seat-based Enterprise, effective 2026-05-06 ([Anthropic news](https://www.anthropic.com/news/higher-limits-spacex), rendered — **directional**), which changes the session limit but says nothing about the weekly one.

**The un-publishability of the ceiling is itself the finding.** You cannot compute in advance whether a given unattended loop fits inside a given plan. The only way to know is to run it and watch. That is the single strongest argument for the burn test in §7.

> **Currency lead for the next touch — not researched here, not a defect in this paper.** Secondary sources claim a temporary 50% weekly-limit boost for Pro/Max/Team running through **2026-08-19**. Unverified and deliberately not chased. It matters for one reason: **if a burn test (T1/T2) is run before that date, it may measure a boosted ceiling and record it as the baseline.** Verify the boost's status first-party before treating any T1/T2 number as the steady-state ceiling.

### 2.3 What Anthropic documents about *why* long sessions consume more

This is the most directly on-point first-party material in the whole survey, and every item is a property of unattended loops rather than of interactive use ([costs](https://code.claude.com/docs/en/costs.md), § *Why usage climbs in a long session*, raw markdown — **definitive**):

- **Long context**: *"Claude Code sends your full conversation with every request, and each time Claude uses tools it sends another request carrying that batch of tool results… so a one-line question in a session that has been open all day still draws usage for the whole conversation."*
- **Cache misses**: *"your first message after a break longer than the cache lifetime misses the cache and reprocesses your full context. The lifetime is an hour on a subscription and drops to five minutes once you're drawing on usage credits; on an API key or cloud provider, it's five minutes by default."*
- **Scheduled tasks**: *"a scheduled task fires on its interval even while the session is idle, sending your full context each time."*
- **Agent teammates**: *"each active teammate keeps consuming tokens until it exits."*
- **Compaction**: *"compacting a large context is itself a large request."*

And the multiplier, stated flatly: *"Agent teams use approximately 7x more tokens than standard sessions when teammates run in plan mode."* Anthropic's engineering blog gives the general shape: *"agents typically use about 4× more tokens than chat interactions"* and *"multi-agent systems use about 15× more tokens than chats"*, with the conclusion *"For economic viability, multi-agent systems require tasks where the value of the task is high enough to pay for the increased performance."* ([Anthropic engineering](https://www.anthropic.com/engineering/multi-agent-research-system), rendered — **definitive on the multipliers, which are stated as bare numbers; the surrounding analysis is directional**.)

**Derived** (from the five bullets above plus the 7x/15x multipliers): the workload the problem statement describes — hours-long, branching, retrying, fanned out — sits at the intersection of *every single documented allowance amplifier at once*. It is not an average consumer of the plan; it is the worst case the plan's mechanics were designed around.

### 2.4 The paused split — the highest-consequence live fact in this paper

Announced 2026-05-14, effective 2026-06-15, **paused 2026-06-15**. The first-party page as fetched 2026-08-03 carries the pause banner verbatim (quoted in §0) and describes the change itself in future tense ([support 15036540](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) — **definitive as of fetch**):

- Scope, quoted as the page states it — a lead-in plus a list, not a sentence:
  > *"The Agent SDK monthly credit applies to:"*
  > - *"Claude Agent SDK usage in your own projects (Python or TypeScript)"*
  > - *"The `claude -p` command in Claude Code (non-interactive mode)"*
  > - *"The Claude Code GitHub Actions integration"*
  > - *"Third-party apps that authenticate with your Claude subscription through the Agent SDK"*
- Effect: *"Starting June 15, 2026, Claude Agent SDK and `claude -p` usage no longer counts toward your Claude plan's usage limits."*
- Amounts: Pro $20 / Max 5x $100 / Max 20x $200 / Team Standard $20 / Team Premium $100 / Enterprise usage-based $20 / Enterprise Premium $200, per month.
- Spillover: *"When your monthly credit runs out, additional Agent SDK usage flows to usage credits at standard API rates—but only if you've enabled usage credits."*
- Carve-out: *"Using Claude Code in the terminal or your IDE continues to use your subscription usage limits exactly as before."*

**Relayed** — not independently corroborated — by Zed, a vendor materially affected. The leading clause matters and is restored here, because it establishes that Zed is repeating Anthropic rather than observing the state itself: *"**Update (June 16, 2026):** Anthropic has told subscribers that the billing change described below is not taking effect yet. For now, ACP usage, `claude -p`, the Claude Agent SDK, and third-party apps built on the Agent SDK continue to work with Claude subscriptions exactly as they did before."* ([Zed blog](https://zed.dev/blog/anthropic-subscription-changes), rendered — **definitive that Zed published this relay; it carries no independent evidentiary weight on the pause itself**.)

**So the real count for "paused" is one first-party source plus one relay of that same source** — not two sources.

**No contradicting source exists. A correction, recorded because the movement is instructive.** An earlier draft of this paper asserted that a secondary source claimed the change went live on 2026-07-10, and named [help.apiyi.com](https://help.apiyi.com/en/anthropic-claude-subscription-agent-sdk-billing-split-june-2026-en.html) as that source. **That characterisation did not survive re-fetching and is withdrawn.** The page is dated 2026-05-16 and discusses the change *prospectively* — *"On May 14, 2026, Anthropic officially announced a major restructuring of its Claude subscription billing, effective June 15"* — and contains no July date, no go-live assertion, and no mention of a pause. It is a **pre-pause explainer**, not a contradicting report.

The go-live date came from a **search-engine summary synthesised across results**, not from any page this paper fetched. That is the precise failure mode, and it is worth naming for the next analyst: *a search tool's synthesised answer is not a source, and a date appearing only in one is not evidence.* Confirming sweeps found no source asserting a July go-live; the secondary coverage that exists reports the change as paused or cancelled.

**The posture is unchanged, because it never depended on the contradiction.** Treat "paused" as **true-as-of-fetch, not as settled**, and re-verify on every touch. The independent grounds are sufficient on their own: the change was **formally announced once, with a published effective date, and is paused rather than withdrawn** — the page still describes it in future tense. That, plus the 2026-09-01 Sonnet 5 price increase, is what sets the `Revalidate:` interval at the fast end of the high band and what T4 exists to settle in five minutes of measurement rather than another research sweep.

**Why it matters here, precisely.** `raw/claude_code_integration_surface.md` (`Last validated: 2026-07-25`, `Critic: PASS`) establishes that `claude -p` is the invocation surface a programmatic edge worker uses. That is exactly and only the surface this change targets; the interactive TUI is explicitly carved out. **The architecture's edge tier is the one thing the announced change would meter.** If it lands, an edge worker on Max 20x has a $200/month API-priced budget for automation — which, per §3.3, is roughly what *one* human-paced Claude Code developer already consumes in token value.

---

## §3 Comparative landscape

### 3.1 What the market actually charges for agentic work

| Offering | Flat component | Metered component | Does a long agent run cost more than a short one? |
|---|---|---|---|
| **Claude Pro/Max** | $20–$200/mo | Usage credits at *"standard API rates"* past the cap | **In dollars: no, until the wall. In allowance: yes, proportionally.** |
| **GitHub Copilot Pro / Pro+** | $10 / $39 mo, 300 / 1,500 premium requests | $0.04 per extra premium request | **No** — *"only the prompts you send count as premium requests; actions Copilot takes autonomously to complete your task, such as tool calls, do not."* |
| **OpenAI Codex on ChatGPT Plus/Pro** | $20 / $100 / $200 mo | Credits; or *"extra local chats using an API key, with usage charged at standard API rates"* | Same shape as Claude — *"a five-hour window. Additional weekly limits may apply."* |
| **Gemini CLI, personal Google account** | $0 | none at the free tier | Capped by request count: *"60 requests/min and 1,000 requests/day with personal Google account."* |
| **Cursor Pro (post-June 2025)** | $20/mo | *"$20 of frontier model usage per month at API pricing"*, then at-cost | **Yes** — the flat tier is a dollar budget, not a usage budget |
| **Claude API / Console** | none | full per-token | **Yes**, linearly |

Sources: [GitHub docs — Copilot requests](https://docs.github.com/en/copilot/concepts/billing/copilot-requests) for the 300/1,500 allowances, the $0.04 overage and the autonomous-actions rule (rendered, **definitive on the quoted rule**); [GitHub docs — Copilot plans](https://docs.github.com/en/copilot/get-started/plans) for the *"$10 USD per month"* / *"$39 USD per month"* prices, which are **not** on the requests page (rendered, **definitive**); [Codex/ChatGPT pricing](https://learn.chatgpt.com/docs/pricing) (rendered, **definitive on the quoted window language**); [gemini-cli README, raw](https://raw.githubusercontent.com/google-gemini/gemini-cli/main/README.md) (**definitive**); [Cursor blog, June 2025 pricing](https://cursor.com/blog/june-2025-pricing) (first-party, **definitive**).

> **Currency lead for the next touch — not a defect in this paper.** The `plans` page states *"Each plan comes with an allowance of GitHub AI Credits"* while the cited `copilot-requests` page still denominates allowances in premium requests (300/1,500). GitHub appears to be mid-migration from "premium requests" to "GitHub AI Credits". Since the Copilot row is this section's most important comparator, re-verify the unit before citing it again.

**The most important row is Copilot's.** GitHub meters *human prompts*, not model turns — an autonomous run of any length inside one prompt is one premium request. **That is the exact property the problem statement claims for subscriptions, and it exists in the market — at GitHub, not at Anthropic.** The property is achievable and vendors sometimes choose it; Anthropic currently does not. (**Derived**, from the Copilot rule plus Anthropic's session/weekly mechanics.)

### 3.2 What a wasteful long-running loop costs under metering — the order-of-magnitude answer

Published measurements, weakest-to-strongest provenance:

| Measurement | Figure | Source & confidence |
|---|---|---|
| HAL benchmark sweep | *"21,730 agent rollouts across 9 models and 9 benchmarks… with a total cost of about $40,000"* → **~$1.84 per rollout, mean** (arithmetic mine) | [arXiv 2510.11977](https://arxiv.org/abs/2510.11977) abstract — **definitive on the two inputs, derived on the quotient** |
| HAL leaderboard, whole-run costs on SWE-bench Verified Mini | *"SWE-Agent Claude Sonnet 4.5 High (September 2025) 72.0% $463.90"*; *"SWE-Agent Claude Sonnet 4.5 (September 2025) 68.0% $505.92"*; *"SWE-Agent Claude Opus 4.1 (August 2025) 68.0% $1351.35"* — and the authors' own framing, *"Agents can be 100x more expensive while only being 1% better"* | [hal.cs.princeton.edu](https://hal.cs.princeton.edu/), first-party from the HAL authors, rendered — **definitive**. *(Replaces a per-task spread figure carried in the first draft on a secondary review's authority; that figure is withdrawn as untraceable, and these whole-run costs are cited in its place.)* |
| FARS autonomous research deployment | *"ran for 417 hours"*, *"consumed 21.6 billion model tokens"*, 166 papers, *"a total cost of approximately $186,000"*; amortized *"2.51 deployment hours, approximately 130 million model tokens, and about $1,120 per paper"* | [arXiv 2606.31651](https://arxiv.org/html/2606.31651v2) — **definitive** |
| METR expenditure-horizon evaluation | *"up to $10,000 on a single evaluation run"* spanning 5 days; expenditure horizons of *"$0–$3K"* across six models | [METR](https://metr.org/blog/2026-07-21-expenditure-horizon/) — **definitive** |
| Anthropic enterprise Claude Code deployments | *"the average cost is around $13 per developer per active day and $150-250 per developer per month, with costs remaining below $30 per active day for 90% of users"* | [costs.md](https://code.claude.com/docs/en/costs.md), raw markdown — **definitive** |
| Anthropic Enterprise budgeting guide, Code seats | Power (top 10%) **$500**/mo, Typical (mean) **$215**/mo, Light (median) **$40**/mo — page states *"These figures are rough planning estimates"* | [support 14782391](https://support.claude.com/en/articles/14782391-claude-enterprise-consumption-guide), rendered — **definitive on the figures, which the page itself hedges** |
| This repo's own research cycle | *"~$58 / 44 min"* for a 5-topic research cycle — one bounded, largely-autonomous multi-agent run | [`docs/standards/research/research_standard.md`](../../../research/research_standard.md) §2 — **unverified**: the source does not state whether the figure is metered spend or a client-side `total_cost_usd` estimate, and §4.7 shows those differ |

**Derived band** (from the definitive rows above; the inference is this paper's):

| Unit of work | Metered cost, order of magnitude |
|---|---|
| One agentic task/rollout | $10⁰ (HAL mean $1.84; spread across models is wide but was not verifiable first-party — see the withdrawn row above) |
| One agent evaluated across one benchmark suite | $10² — $10³ ($464 – $1,351 on SWE-bench Verified Mini) |
| One human-paced day of agentic coding | $10¹ ($13 typical, <$30 for 90%) |
| One month, one heavy developer | $10² ($215 typical, $500 power) |
| One **unattended** multi-hour autonomous loop that branches and retries | $10¹ — $10³ |
| A multi-day unattended research/optimization campaign | $10³ — $10⁵ (METR $10k/run; FARS $186k/deployment) |

The problem statement's workload — *"runs for hours, retries, branches, and occasionally goes nowhere"* — lands in the $10¹–$10³ band per run. Against a $200/month subscription that is the difference between "run it and see" and "justify it first." **The order of magnitude supports the claim's spirit even where its letter fails.** The evidence does *not* support a tighter estimate than one order of magnitude, and I decline to manufacture one.

### 3.3 The subsidy ratio — how much is the flat rate actually worth?

**Derived, from Anthropic's own two figures**: a typical Claude Code seat consumes ~$215/month of token value and a power seat ~$500/month ([support 14782391](https://support.claude.com/en/articles/14782391-claude-enterprise-consumption-guide)); Max 20x costs $200/month. So for **human-paced interactive** use the arbitrage is roughly **1x to 2.5x** — real, but not the order-of-magnitude subsidy the "trivial rather than a privilege of the well-funded" framing implies.

For **unattended** use the ratio would be far larger, because an unattended loop consumes far more wall-clock-hour-for-hour than a human typing. **And that is exactly what the session and weekly caps exist to prevent.** The caps are not incidental friction; per Anthropic's own July-2025 framing they were introduced in response to subscribers *"running Claude Code continuously in the background, 24/7"* ([TechCrunch](https://techcrunch.com/2025/07/28/anthropic-unveils-new-rate-limits-to-curb-claude-code-power-users/), secondary — **unverified on the quote, corroborated in substance by the existence of the weekly limit in current first-party docs**).

**This is the sharpest derived finding in the paper:** the cap is the mechanism by which the vendor bounds precisely the arbitrage the thesis relies on. The thesis and the cap are not independent facts that happen to coexist — the cap is a response to the behaviour the thesis proposes to institutionalise.

### 3.4 Metered-side cost levers, and the one that is structurally unavailable

- **Prompt caching** is real and already applied: Claude Code *"automatically optimizes costs through prompt caching"*, and *"Claude subscription users already receive 1-hour TTL automatically"* ([costs.md](https://code.claude.com/docs/en/costs.md), [cost-tracking.md](https://code.claude.com/docs/en/agent-sdk/cost-tracking.md) — **definitive**). Cache read is 0.1x base input.
- **Small models** are 5x cheaper at the same tier position: Haiku 4.5 at $1/$5 vs Opus 5 at $5/$25.
- **Batch is a 50% discount on both directions** — and is **structurally unavailable to this workload**. Anthropic's own pricing page states, for Managed Agents sessions, that the Batch discount does not apply because *"Sessions are stateful and interactive. There is no batch mode."* ([pricing.md](https://platform.claude.com/docs/en/about-claude/pricing.md) — **definitive**). **Derived:** the largest single published metered discount cannot be applied to agentic loops by construction, so the counter-argument "batch pricing attacks per-token cost" does not reach this workload.
- **Adverse lever, easy to miss:** on the subscription the cache TTL is one hour, but *"drops to five minutes once you're drawing on usage credits"* ([costs.md](https://code.claude.com/docs/en/costs.md) — **definitive**). **Derived:** the metered fallback is worse for a long-running loop than list prices alone suggest, because the loop's re-read pattern loses the hour-long cache exactly when it starts paying per token.

---

## §4 What this provides — enumerated, citable properties a plan can rely on

Each item is something downstream planning can cite. Confidence marked per item.

**4.1 Below the ceiling, the marginal dollar cost of an additional turn is zero.** No per-turn charge exists on a subscription; the `/usage` session cost figure is explicitly *"intended for API users"* and *"isn't relevant for billing purposes"* for subscribers ([costs.md](https://code.claude.com/docs/en/costs.md)). — **definitive.**

**4.2 The ceiling is two-dimensional and both dimensions bind: a rolling five-hour session window and a weekly window, shared across all models and all Anthropic surfaces.** Switching models does not restore access to either. ([errors.md](https://code.claude.com/docs/en/errors.md), [costs.md](https://code.claude.com/docs/en/costs.md).) — **definitive.**

**4.3 Fanout is the documented failure mode.** *"A single burst of heavy activity, such as a large workflow fanout, can exhaust the weekly allowance before the session window resets."* A design that fans out parents into children — which this architecture does — is the named case. ([errors.md](https://code.claude.com/docs/en/errors.md).) — **definitive.**

**4.4 The plan ceiling is not published in absolute terms and therefore cannot be planned against analytically.** See §2.2 for the search method. — **definitive negative finding.**

**4.5 Anthropic ships a first-party unattended-loop product that draws on subscription usage, which bounds how hostile the vendor is to the workload shape.** Routines *"execute on Anthropic-managed cloud infrastructure"*, *"run autonomously as full Claude Code cloud sessions: there is no permission-mode picker and no approval prompts during a run"*, and are *"available on Pro, Max, Team, and Enterprise plans"*. Critically: *"Routines draw down subscription usage the same way interactive sessions do. In addition to the standard subscription limits, routines have a daily cap on how many runs can start per account."* Minimum schedule interval is one hour; the feature is *"in research preview"*. ([routines.md](https://code.claude.com/docs/en/routines.md), raw markdown — **definitive**.) **Derived:** unattended autonomous execution funded by a subscription is a *sanctioned, shipped* pattern — but Anthropic gates it with a third cap (daily runs) on top of the two windows, and runs it on their infrastructure rather than the edge.

**4.6 Anthropic's own edge/CI automation surface is metered, not subscription-funded — the one place where the economic and contractual questions touch.** The Claude Code GitHub Action documents only `ANTHROPIC_API_KEY` (or Bedrock/Vertex credentials) for authentication; no OAuth/subscription path appears anywhere on the page. Its cost section is headed **"CI costs"**, within which *"API costs:"* is one of two bolded items, the other being *"GitHub Actions costs:"* ([github-actions.md](https://code.claude.com/docs/en/github-actions.md), raw markdown — **definitive on what the page documents; the absence of an OAuth option is a documented absence, not a proven prohibition**). This is the point where [`anthropic_tos_and_enterprise.md`](anthropic_tos_and_enterprise.md) governs — that paper (**current, `Critic: PASS`, due 2026-08-21**) establishes the permitted boundary. Economically the observation stands on its own: *the vendor's own answer to "run this unattended in CI" is an API key.*

**4.7 Cost instrumentation exists at the edge and is adequate for a burn test — with a documented caveat.** `claude -p --output-format json` returns `total_cost_usd` and a per-model breakdown ([`claude_code_integration_surface.md`](claude_code_integration_surface.md), `Critic: PASS`, 2026-07-25). But: *"The `total_cost_usd` and `costUSD` fields are client-side estimates, not authoritative billing data… Do not bill end users or trigger financial decisions from these fields."* ([cost-tracking.md](https://code.claude.com/docs/en/agent-sdk/cost-tracking.md), raw markdown — **definitive**). For subagent-spawning runs, `total_cost_usd` and `model_usage` include subagent tokens but the `usage` field *"undercounts as soon as nesting occurs"* — a trap for anyone instrumenting a hierarchical loop. Allowance consumption, separately, is observable via `/usage` bars and the `rate_limits` status-line fields ([errors.md](https://code.claude.com/docs/en/errors.md)).

**4.8 Per-unit-of-capability inference prices have fallen fast; per-unit-of-frontier-work they have not, and can rise.** Epoch AI, fitting log-linear regressions on cheapest-model-above-threshold across six benchmarks, reports *"prices declining between 9x per year and 900x per year, with a median of 50x per year"*, with their own caveat: *"The fastest price drops in that range have occurred in the past year, so it's less clear that those will persist"* ([Epoch AI](https://epoch.ai/data-insights/llm-inference-price-trends), rendered — **definitive on the quoted figures**). Against that, three first-party counter-observations from a single fetch of Anthropic's price table (**definitive**):
   - **Supporting the trend:** Opus 4.1 at $15/$75 → Opus 4.5 and every later Opus at $5/$25 — a 3x drop at the flagship tier.
   - **Against it:** Sonnet 5 is at *introductory* $2/$10 *"through August 31, 2026, after which the standard pricing of $3/$15 per million input/output tokens will take effect"* — a scheduled 50% increase landing four weeks after this paper's validation date.
   - **Hidden against it:** *"Claude 4.7 and later models and Claude Mythos Preview use a newer tokenizer… This tokenizer produces approximately 30% more tokens for the same text."* **Derived:** that is an effective ~30% price increase per unit of *text* on newer models, invisible in the per-token headline. A price-trend argument built on headline $/MTok is systematically biased optimistic for exactly the models an agentic loop would use.

**4.9 Falling unit prices are being consumed by rising unit counts.** **Derived**, from 4.8 plus §2.3's multipliers (agents 4x chat, multi-agent 15x chat, agent teams 7x standard sessions) plus the industry move to long-horizon agentic scaffolds. Cursor's own explanation of abandoning flat request quotas says the same thing from the vendor side: *"New models can spend more tokens per request on longer-horizon tasks… the hardest requests cost an order of magnitude more than simple ones."* ([Cursor](https://cursor.com/blog/june-2025-pricing) — **definitive**.) The affordability argument's shelf life therefore depends on a race between two exponentials, not on one trend.

**4.10 Edge-held subscription execution is a recognised, vendor-named pattern — with a name.** Zed's documentation has a page titled *Use an Existing Subscription*, whose stated fit is *"You already pay for ChatGPT, Claude, Copilot, or another subscription"* ([llm-providers.md, raw](https://raw.githubusercontent.com/zed-industries/zed/main/docs/src/ai/llm-providers.md) — **definitive**). It covers ChatGPT Plus/Pro (*"Sign in with OpenAI in Zed; no separate OpenAI API key is required"* — that sentence is in [use-an-existing-subscription.md, raw](https://raw.githubusercontent.com/zed-industries/zed/main/docs/src/ai/use-an-existing-subscription.md), not the page cited immediately above), GitHub Copilot as a chat model provider, and Claude Pro/Max.

The Claude row is the interesting one, and it is quoted here as two separate artifacts rather than merged — the table row and the prose sentence say different things ([use-an-existing-subscription.md, raw](https://raw.githubusercontent.com/zed-industries/zed/main/docs/src/ai/use-an-existing-subscription.md) — **definitive**):

> | Subscription | Zed AI features | External Agent via ACP | Terminal Thread | Notes |
> |---|---|---|---|---|
> | Claude Pro / Max | No direct Zed LLM provider path | Claude Agent | Claude Code | Separate from Anthropic API keys |

> *"Use Claude Agent or Claude Code where supported if you want subscription-backed Claude behavior."*

**Derived:** the pattern is common enough to have first-party documentation at a third-party vendor, and the Claude row's routing — no direct provider path, subscription-backed behaviour only via Claude Agent or Claude Code — mirrors exactly the boundary the ToS paper documents. **What I found no evidence of, anywhere in the sweep, is the *multi-participant orchestrated* version** — work coordinated centrally but executed on many individuals' own subscriptions. Search method: the "bring your own subscription"/BYOK sweep returned only single-user tooling and API-key-based BYOK platforms; no orchestration product, paper, or vendor doc describing federated edge-subscription execution surfaced. **That absence is consistent with the problem statement's novelty claim, and is the economic half of what [`combination_prior_art.md`](combination_prior_art.md) tests directly.**

**4.11 Flat-rate terms change, and the base rate is not low.** Four documented adverse-to-flat-rate changes in ~13 months, all first-party or vendor-confirmed: Anthropic weekly limits (announced 2025-07-28, effective 2025-08-28); Cursor request-quota → API-priced credits (June 2025, with a public apology — *"Our recent pricing changes for individual plans were not communicated clearly, and we take full responsibility"* — and refunds); Anthropic OAuth enforcement against third-party subscription routing (policy codified 2026-02-19 — first-party; the earlier "server-side enforcement Jan 2026" sub-date rests on three secondary outlets, per [`anthropic_tos_and_enterprise.md`](anthropic_tos_and_enterprise.md) §3.3 — **that paper is current, `Critic: PASS`, due 2026-08-21, and rates the Anthropic-published policy language definitive**); Anthropic Agent SDK credit split (announced 2026-05-14, paused 2026-06-15). **Derived:** roughly one materially adverse flat-rate term change per vendor per year across 2025–2026 — a base rate resting on four inputs, each of which is **first-party or vendor-confirmed as to the change itself**; only the OAuth item's enforcement *start date*, which the base rate does not depend on, is secondary. A business built on someone else's flat rate carries a policy risk a metered one does not, and the observed frequency is annual, not decadal.

---

## §5 Honest boundary analysis

### 5.1 The required case: affordability is a cost optimisation the problem statement promoted to a principle

Argued as strongly as the evidence allows, before any answer.

**(a) Of the four numbered elements, only element 2 spends tokens at scale. — DERIVED.** The four quoted element descriptions below each verify verbatim against `problem-statement.md` (**definitive**); the cross-element inference drawn from them is this paper's own (**derived**), and it must not be read as a documented result — it is the input to the §5.2(a) candidate correction, which is the one finding here proposing an edit to the framing document.

By the problem statement's own definitions: element 1 (durable execution) is *"Mature technology, borrowed rather than invented"* whose cost is engineering time; element 3 (typed memory) is explicitly something the next step *"reads in code, with no model in the loop"* — zero token cost by construction; element 4 (high-level loops) is *"if/then/else over the results of entire workflows"* — also code. Only element 2, layered self-improvement, spends tokens at scale.

**Derived conclusion: affordability enables element 2 alone, not "the other three."** (Elements 1, 3 and 4 are the cheap ones; element 2 — layered self-improvement — is the expensive one. A planner applying the §5.2(a) correction needs that set named, not counted.) This is the strongest single objection in this section, and it is an inference, not a citation.

**(b) Loop *logic* is cheap to debug even under metering.** A parent that fails to parse a child's typed result fails on turn one. Haiku 4.5 at $1/$5 per MTok, or a local model on the hardware this repo already documents (A6000 + 4080, per `CLAUDE.md`), serves loop-logic iteration at near-zero marginal cost. What costs frontier-model money is loop *outcomes* — and outcomes are the part you would want to evaluate carefully and sparingly anyway.

**(c) The measured subsidy is 1x–2.5x, not 10x.** §3.3: Anthropic's own budgeting figures put a typical Code seat at $215/mo and a power seat at $500/mo against a $200/mo Max 20x. "Trivial rather than a privilege of the well-funded" overstates a 2.5x discount.

**(d) Flat-rate is obtainable without any vendor's permission.** A $2,000 GPU amortised over three years is ~$55/month of genuinely unmetered inference with no cap, no ToS, and no policy risk. What a subscription buys is not flat-rate — it is *frontier capability* at flat rate. That is a narrower and more contingent claim than the one the problem statement makes.

**(e) The field says cost is not the binding constraint.** LangChain's State of Agent Engineering (n=1,340, fielded 2025-11-18 to 2025-12-02) ranks quality first (*"one third of respondents cited quality as their primary blocker"*), latency second (20%), security among larger enterprises — and reports cost *"is less frequently cited as a concern than in previous years"*, attributing it to *"Falling model prices and improved efficiency"* ([LangChain](https://www.langchain.com/state-of-agent-engineering), rendered — **definitive on the quoted findings**). HAL's entire thesis is that the missing infrastructure is *evaluation*, not budget ([arXiv 2510.11977](https://arxiv.org/abs/2510.11977)). A 2026 CISO survey puts trust first (press release — **unverified**; [GlobeNewswire](https://www.globenewswire.com/news-release/2026/05/07/3290087/0/en/Mind-the-Trust-Gap-Strike48-CISO-Survey-Finds-Lack-of-Trust-in-AI-Agents-Is-the-Main-Barrier-to-Adoption.html)).

**(f) The caps make the claim self-limiting.** If the loop is cheap enough not to hit the cap, it was cheap enough to meter. If it is expensive enough to hit the cap, the subscription did not make it accessible — it made it *blocked*, which is worse than expensive because you cannot pay to unblock it without leaving the flat rate.

### 5.2 The answer

**(a) is conceded, and should change the problem statement's wording.** "The enabler of the other three" is not supported; "the enabler of element 2" is. This is a **candidate correction to `problem-statement.md`**, surfaced here per §7 of the Research Standard and routed through the synthesis — not edited by this run.

**(b) is partly conceded and is directly testable** — see the test plan's item 6. If most of a loop's turns are logic turns, the affordability argument's scope shrinks to the evaluation turns.

**(c) is conceded for human-paced use and rejected for the workload actually claimed.** Those figures measure developers typing. An unattended loop's per-wall-clock-hour consumption is unbounded above by human typing speed. The reason the ratio does not run away is the cap — which is the finding, not a rebuttal.

**(d) is a real alternative and is under-explored in this repo's planning.** It does not defeat the claim, because the claim is about *frontier* loops; it does narrow it, and it belongs in the boundary rather than being ignored.

**(e) is the strongest counter-evidence in the paper and it does not quite land.** Every survey located measures **organisations deploying agents into production**. The problem statement's claim is about **individuals exploring loop design**, where the decision unit is "should I run this speculative thing" rather than "should we ship this". **No survey of the individual-experimenter population was located.** *Search method: targeted searches for agent-adoption blocker surveys, developer-survey cost findings, and LangChain/Stanford-style instrument reports; every instrument found samples enterprises or production teams.* **The claim is therefore unfalsified rather than verified — and it is unfalsified because nobody has measured the population it is about.** That is a gap, and it is the most consequential one in this paper.

**(f) is answered by the shape of the cost function, and this is where the claim genuinely survives.** Metered cost is *linear and unbounded*; subscription cost is *flat then a wall*. The literature on wasteful search says the difference matters: repeated sampling scales coverage *"over four orders of magnitude"*, and on SWE-bench Lite raises the solved fraction *"from 15.9% with one sample to 56% with 250 samples"* ([Large Language Monkeys, arXiv 2407.21787](https://arxiv.org/abs/2407.21787) — **definitive**). That is the canonical case of *the interesting experiment being the wasteful one*, and under metering its price is linear in the waste — 250x. Under a subscription its price is bounded by a cap that does not care how many of the 250 were duds. **The problem statement's intuition about *which experiments get priced out first* is supported by published inference-scaling results; only its claim about *what a subscription costs* is wrong.**

### 5.3 Where this paper's own thesis fails

- **If the Agent SDK split un-pauses, the paper's §4.1 property evaporates for `claude -p`** and the edge tier becomes metered at list prices with a $200/month ceiling — worse than a plain API account with no ceiling. This is a single vendor decision away, has already been made once, and is the reason for a 2-week revalidation.
- **If the loop is small, none of this matters.** A run that fits comfortably inside a five-hour window is affordable under either model; the whole analysis only bites for loops that approach the cap.
- **If the work is worth real money, metering is the right answer.** Anthropic's own framing: *"multi-agent systems require tasks where the value of the task is high enough to pay for the increased performance."* An organisation that would pay $500/developer/month is not blocked by anything discussed here.
- **The absolute ceiling is unknown (§4.4), so this paper cannot tell you whether your loop fits.** It can only tell you that the question is empirical and give you the instrumentation to answer it.

---

## §6 Citations

**First-party, raw markdown (highest confidence in this pool):**

1. Anthropic. *Claude Code — Manage costs effectively.* https://code.claude.com/docs/en/costs.md (fetched 2026-08-03)
2. Anthropic. *Claude Code — Troubleshoot errors* (§ *You've hit your session limit*). https://code.claude.com/docs/en/errors.md (fetched 2026-08-03)
3. Anthropic. *Pricing.* https://platform.claude.com/docs/en/about-claude/pricing.md (fetched 2026-08-03)
4. Anthropic. *Claude Code — Automate work with routines.* https://code.claude.com/docs/en/routines.md (fetched 2026-08-03)
5. Anthropic. *Claude Code — Run prompts on a schedule.* https://code.claude.com/docs/en/scheduled-tasks.md (fetched 2026-08-03)
6. Anthropic. *Claude Code — Feature availability.* https://code.claude.com/docs/en/feature-availability.md (fetched 2026-08-03)
7. Anthropic. *Claude Code — GitHub Actions.* https://code.claude.com/docs/en/github-actions.md (fetched 2026-08-03)
8. Anthropic. *Claude Agent SDK — Track cost and usage.* https://code.claude.com/docs/en/agent-sdk/cost-tracking.md (fetched 2026-08-03)
9. Google. *gemini-cli README* (raw). https://raw.githubusercontent.com/google-gemini/gemini-cli/main/README.md (fetched 2026-08-03)
10. Zed Industries. *Use an Existing Subscription* (raw). https://raw.githubusercontent.com/zed-industries/zed/main/docs/src/ai/use-an-existing-subscription.md (fetched 2026-08-03)
11. Zed Industries. *LLM Providers* (raw). https://raw.githubusercontent.com/zed-industries/zed/main/docs/src/ai/llm-providers.md (fetched 2026-08-03)

**First-party, rendered pages (reduced confidence; quoted conservatively):**

12. Anthropic Support. *Use the Claude Agent SDK with your Claude plan.* https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan (fetched 2026-08-03 — pause banner present)
13. Anthropic Support. *Extra usage for paid Claude plans.* https://support.claude.com/en/articles/12429409-extra-usage-for-paid-claude-plans (fetched 2026-08-03)
14. Anthropic Support. *What is the Max plan?* https://support.claude.com/en/articles/11049741-what-is-the-max-plan (fetched 2026-08-03)
15. Anthropic Support. *Claude Enterprise consumption guide.* https://support.claude.com/en/articles/14782391-claude-enterprise-consumption-guide (fetched 2026-08-03)
16. Anthropic Support. *Usage limit best practices.* https://support.claude.com/en/articles/9797557-usage-limit-best-practices (fetched 2026-08-03)
17. Anthropic Support. *Use Claude Code with your Pro or Max plan.* https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan (fetched 2026-08-03)
18. Anthropic. *Plans & Pricing.* https://claude.com/pricing (fetched 2026-08-03 — Max 20x figure ambiguous in fetch; see §2.1)
19. Anthropic. *Higher usage limits for Claude and a compute deal with SpaceX.* 2026-05-06. https://www.anthropic.com/news/higher-limits-spacex (fetched 2026-08-03)
20. Anthropic. *How we built our multi-agent research system.* https://www.anthropic.com/engineering/multi-agent-research-system (fetched 2026-08-03)
21. GitHub. *Requests in GitHub Copilot.* https://docs.github.com/en/copilot/concepts/billing/copilot-requests (fetched 2026-08-03 — allowances, overage rate, autonomous-actions rule; **not** the source for Pro/Pro+ prices — see 37)
22. OpenAI. *Codex / ChatGPT pricing.* https://learn.chatgpt.com/docs/pricing (fetched 2026-08-03)
23. Cursor. *Clarifying our pricing.* June 2025. https://cursor.com/blog/june-2025-pricing (fetched 2026-08-03)
24. Zed Industries. *What Anthropic's New Claude Billing Means for Zed Users.* https://zed.dev/blog/anthropic-subscription-changes (fetched 2026-08-03)

**Peer-reviewed / preprint:**

25. Stroebl, B., et al. *Holistic Agent Leaderboard: The Missing Infrastructure for AI Agent Evaluation.* arXiv:2510.11977 (ICLR 2026). https://arxiv.org/abs/2510.11977
26. *FARS: A Fully Automated Research System Deployed at Scale.* arXiv:2606.31651. https://arxiv.org/html/2606.31651v2
27. Brown, B., et al. *Large Language Monkeys: Scaling Inference Compute with Repeated Sampling.* arXiv:2407.21787. https://arxiv.org/abs/2407.21787

**Research organisations / industry data:**

28. METR. *Expenditure Horizon: Measuring Optimization Ability, with an Application to NanoGPT.* 2026-07-21. https://metr.org/blog/2026-07-21-expenditure-horizon/
29. Epoch AI. *LLM inference prices have fallen rapidly but unequally across tasks.* https://epoch.ai/data-insights/llm-inference-price-trends
30. LangChain. *State of Agent Engineering* (n=1,340, fielded 2025-11-18 – 2025-12-02). https://www.langchain.com/state-of-agent-engineering

**Secondary (use only where marked unverified):**

31. TechCrunch. *Anthropic unveils new rate limits to curb Claude Code power users.* 2025-07-28. https://techcrunch.com/2025/07/28/anthropic-unveils-new-rate-limits-to-curb-claude-code-power-users/
32. GlobeNewswire. *Strike48 CISO Survey: Lack of Trust in AI Agents Is the Main Barrier to Adoption.* 2026-05-07. https://www.globenewswire.com/news-release/2026/05/07/3290087/0/en/Mind-the-Trust-Gap-Strike48-CISO-Survey-Finds-Lack-of-Trust-in-AI-Agents-Is-the-Main-Barrier-to-Adoption.html

**Pool-internal (cited, not duplicated):**

33. `docs/standards/architecture/research/raw/anthropic_tos_and_enterprise.md` — permissibility of edge-held subscription auth; cited in §0, §4.6, §4.11 and T7. `Last validated: 2026-07-24`, `Critic: PASS`, `Revalidate: high — 4 weeks` → **due 2026-08-21; current and PASS at this paper's validation date.**
34. `docs/standards/architecture/research/raw/claude_code_integration_surface.md` — `claude -p` invocation surface, `--output-format json`, `total_cost_usd`; cited in §2.4 and §4.7. `Last validated: 2026-07-25`, `Critic: PASS`.
35. `docs/standards/architecture/research/raw/combination_prior_art.md` — the novelty claim; §4.10's negative finding on multi-participant edge-subscription orchestration is the economic half of what that paper tests directly. *(Same cycle as this paper; consult its own header for validation state.)*
36. `docs/standards/research/research_standard.md` §2 — records a 5-topic research cycle at *"~$58 / 44 min"*; used as an in-house datapoint in §3.2's cost table. **Unverified**: the source does not state whether the figure is metered spend or a client-side estimate.

**Added at critic revision (2026-08-03):**

37. GitHub. *Plans for GitHub Copilot.* https://docs.github.com/en/copilot/get-started/plans (fetched 2026-08-03 — Pro/Pro+ monthly prices, which are absent from citation 21; also the source of §3.1's "GitHub AI Credits" currency lead)
38. Princeton PLI. *Holistic Agent Leaderboard.* https://hal.cs.princeton.edu/ (fetched 2026-08-03 — whole-run benchmark costs in §3.2, replacing a withdrawn per-task figure)
39. Apiyi (vendor blog). *Anthropic June 15 Agent SDK billing split.* https://help.apiyi.com/en/anthropic-claude-subscription-agent-sdk-billing-split-june-2026-en.html — dated 2026-05-16; re-fetched 2026-08-03 and confirmed to be a **pre-pause prospective explainer** carrying no go-live or pause claim. Listed only to document §2.4's withdrawn attribution so a later reader is not left wondering what the citation pointed at. **Not evidence for anything in this paper.**

**Withdrawn at round-3 revision:** the claim that citation 39 asserted a 2026-07-10 go-live for the Agent SDK billing split. Re-fetching showed the page makes no such claim; the date originated in a search-engine summary rather than a source. See §2.4 — the paper's "paused, not withdrawn" posture is unaffected, being first-party grounded.

**Withdrawn at round-2 revision:** a HAL per-task cost spread ($0.08–$32.00) and a Sakana AI Scientist per-paper figure (~$15), both carried in the first draft on secondary-review authority with no URL. Neither fed the derived band's endpoints. `production_cases.md` was listed in the first draft but never cited in the body; the entry is removed rather than retro-fitted to a use that did not occur.

---

## §7 Test plan — what research cannot settle

Research established the *mechanics*. It could not establish the *quantities*, because Anthropic does not publish them (§4.4). Every item below is a measurement, ordered by how much it changes a decision.

**T1 — The burn test: run one deliberately wasteful loop to exhaustion.**
The obvious experiment, and the one §4.4 forces. It must record **two currencies simultaneously**, because the paper's whole finding is that they differ:
- *Dollars-equivalent*: `total_cost_usd` and `model_usage` from `claude -p --output-format json`, per run and per subagent — using `model_usage` not `usage`, since `usage` *"undercounts as soon as nesting occurs"* (§4.7).
- *Allowance*: percent-of-session-window and percent-of-weekly-window consumed, from `/usage` or the `rate_limits` status-line fields, sampled before and after each leg.
- *Token classes*: input / output / cache-read / cache-write separately — cache behaviour is the dominant lever (§3.4).
- *Wall clock and turn count*, to normalise.
Run it on a workload with the architecture's actual shape (parent fans out to children, children retry, some branches produce nothing) and **run it past the wall at least once**, so the wall's location is observed rather than inferred. Deliverable: *"on plan P, an unattended run of workflow W consumes X% of the weekly window per hour, and Y hours exhausts it."*

**T2 — Establish the ceiling empirically, per plan.** T1 gives one point; T2 turns it into a planning number. Repeat across the plan tiers actually in use. Without this, no phase doc can state how many unattended loop-hours per week the architecture has to work with. **Precondition:** check §2.2's currency lead first — a temporary weekly-limit boost is reported to run through 2026-08-19, and a measurement taken inside that window would record a boosted ceiling as the baseline.

**T3 — Measure the cost of *waste* specifically.** Compare allowance consumed by a run that succeeds against one that produces nothing (dead branch, failed retry loop, abandoned exploration). The problem statement's claim is about the *wasteful* run's cost, and nothing published measures it separately. If a dead branch costs the same allowance as a successful one — which §2.3's context mechanics suggest it does — then "being wrong costs nothing but time" is false in allowance terms too, and the claim needs a third revision.

**T4 — Determine which pool `claude -p` currently draws from.** Research cannot settle this — not because sources conflict (§2.4: they do not), but because the only published statement is a **pause banner on an announced change**, and a pause has no expiry date. Documentation states intent; only the meter states fact. Run one `claude -p` invocation and observe whether the session-window bar moves or an Agent-SDK credit balance decrements. **This is a five-minute experiment that resolves the paper's highest-consequence open question**, and it should be re-run on every revalidation rather than re-researched.

**T5 — Measure the cache-hit ratio of a long unattended loop.** `costs.md` names cache misses as a top-flagged allowance consumer, and the TTL drops from one hour to five minutes the moment you fall through to usage credits (§3.4). If a loop's natural inter-leg gap exceeds five minutes, its metered fallback is far worse than list prices imply. Measure the gap distribution and the resulting hit ratio.

**T6 — Test the local-model floor (tests boundary argument 5.1(b)).** Classify a real run's turns into *loop-logic* turns (routing, parsing, dispatch, retry decisions) and *substantive* turns. Measure what fraction of tokens each consumes. If loop-logic dominates, the affordability argument's scope shrinks sharply and a local model on existing hardware covers most of it — which would be a direction-changing finding for the edge tier's design.

**T7 — Multi-participant scaling.** Does N edge workers on N individual subscriptions actually yield N× the weekly allowance in practice, or do concurrency behaviours, shared-surface accounting, or per-account effects interfere? This is the economic half of the multi-tenancy claim; the contractual half is already settled and current in [`anthropic_tos_and_enterprise.md`](anthropic_tos_and_enterprise.md) (`Critic: PASS`, due 2026-08-21), so **T7 has no research precondition and can be run whenever the second edge exists.** Note that paper's §4.3 boundary when designing it: participants must be peers acting on their own tasks, not workers for another participant.

**T8 — Not settleable by measurement, flagged as such.** Whether zero marginal dollar cost actually changes an individual experimenter's *willingness to run speculative loops* is a behavioural question about a population nobody has surveyed (§5.2(e)). It could be answered by instrumenting this operator's own run log — comparing speculative-run frequency across periods with and without a live metered account — but that is an observational study with n=1 and confounds, and should be labelled as such rather than presented as evidence.
