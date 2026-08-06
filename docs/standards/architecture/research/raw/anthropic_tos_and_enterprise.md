# Anthropic ToS, Claude Code Authentication Policy, and Claude for Enterprise — Source Synthesis for §7.2

```
Topic:          Is subscription-tier authentication at the edge viable under Anthropic's terms?
Feeds:          Phase: Managed Configuration + edge-worker topology — whether edge auth is viable
Last validated: 2026-08-06
Revalidate:     high — 2 weeks   (tightened: the subject changed three times in four months)
Confidence:     Definitive where it quotes published policy; directional on enterprise-tier interpretation. **§1–§8 MISSED three policy events that predate their own validation date — read §9 FIRST.** Policy is the most volatile input in the pool.
Critic:         PASS — 2026-07-24 · HAND-CORRECTED 2026-08-06 (§9 appended, NOT critic-verified)
```

**Prepared:** 2026-07-24
**Purpose:** Ground the paper's §7.2 claim ("subscription-tier authentication at the edge sidesteps ToS gray areas by design") in Anthropic's own published policy documents.

---

## Executive Summary

Anthropic's own Claude Code documentation now explicitly codifies the exact architectural distinction the paper argues for. As of February 19, 2026, `code.claude.com/docs/en/legal-and-compliance` states plainly that consumer-tier OAuth (Free, Pro, Max, Team, Enterprise) is *"intended exclusively for purchasers…to support ordinary use of Claude Code and other native Anthropic applications,"* while *"developers building products or services that interact with Claude's capabilities, including those using the Agent SDK, should use API key authentication."* Anthropic *"does not permit third-party developers to…route requests through Free, Pro, or Max plan credentials on behalf of their users."* A federation architecture in which each participant runs Claude Code (a native Anthropic application) locally under their own subscription and never proxies credentials satisfies the permitted pattern by construction. Claude for Enterprise provides shared identity, billing, RBAC, and audit surfaces but no orchestration or workflow layer — confirming the paper's "shared access, not shared orchestration" positioning. The paper's §7.2 claim holds up; it can be strengthened from principle-argument to citation-grounded argument using the quotes catalogued below.

---

## §1 Subscription-Tier ToS Findings (per-tier)

Anthropic's legal stack for Claude Code decomposes into three surfaces, with the tier determining which applies (source: `code.claude.com/docs/en/legal-and-compliance`, "License" section):

- **Consumer Terms of Service** — Free, Pro, Max
- **Commercial Terms of Service** — Team, Enterprise, Claude API, Claude Agent SDK
- **Anthropic Usage Policy (AUP)** — universal

### 1.1 Consumer Terms (Free / Pro / Max)

*URL:* https://www.anthropic.com/legal/consumer-terms — Effective October 8, 2025.

**Products covered** (introductory paragraph):
> "These Terms…govern your use of Claude.ai, Claude Pro, and other products and services that we may offer for individuals, along with any associated apps, software, and websites."

**§2 — Account creation and access:**
> "You may not share your Account login information, Anthropic API key, or Account credentials with anyone else. You also may not make your Account available to anyone else."

**§3 — Use of our Services** (automation prohibition with two carve-outs):
> "Except when you are accessing our Services via an Anthropic API Key **or where we otherwise explicitly permit it**, [you may not] access the Services through automated or non-human means, whether through a bot, script, or otherwise." (emphasis added)

**Rate limits:** not specified in the Consumer Terms document itself; deferred to product-page disclosures and to the Claude Code compliance page, which states that *"advertised usage limits for Pro and Max plans assume ordinary, individual usage of Claude Code and the Agent SDK"* (code.claude.com/docs/en/legal-and-compliance).

### 1.2 Commercial Terms (Team / Enterprise / API / Agent SDK)

*URL:* https://www.anthropic.com/legal/commercial-terms.

**Products covered:** the Commercial Terms apply to *"Anthropic API keys and any other Anthropic offerings that reference these Terms."* The Claude Code compliance page explicitly maps them onto Team, Enterprise, and API users; the Agent SDK overview page adds:
> "Use of the Claude Agent SDK is governed by Anthropic's Commercial Terms of Service, including when you use it to power products and services that you make available to your own customers and end users." (code.claude.com/docs/en/agent-sdk/overview, "License and terms")

**Automation:** the Commercial Terms have no equivalent of the Consumer §3 automation prohibition. API/SDK access *is* the automated path.

**Delegation / assignment (§M.4):**
> "Neither party may assign its rights or delegate its obligations under these Terms without the other party's prior written consent…"

### 1.3 Anthropic Usage Policy (AUP) — universal

*URL:* https://www.anthropic.com/legal/aup. Fourteen top-level prohibited categories; two are load-bearing for agentic architectures:

- *"Agentic use cases must still comply with the Usage Policy."*
- Prohibited: *"Utilization of inputs and outputs to train an AI model (e.g., 'model scraping' or 'model distillation') without prior authorization."*

### 1.4 Claude Code "Authentication and Credential Use" Policy — THE key finding

*URL:* https://code.claude.com/docs/en/legal-and-compliance. Formalized February 19, 2026; server-side enforcement rolled out January 9, 2026 (winbuzzer.com, alternativeto.net, aihackers.net corroborating).

Verbatim policy text (this is the exception that permits Claude Code CLI use under Consumer §3):
> "**OAuth authentication** is intended exclusively for purchasers of Claude Free, Pro, Max, Team, and Enterprise subscription plans and is designed to support ordinary use of Claude Code and other native Anthropic applications."
>
> "**Developers** building products or services that interact with Claude's capabilities, including those using the Agent SDK, should use API key authentication through Claude Console or a supported cloud provider. Anthropic does not permit third-party developers to offer Claude.ai login or to route requests through Free, Pro, or Max plan credentials on behalf of their users."
>
> "Anthropic reserves the right to take measures to enforce these restrictions and may do so without prior notice."

The Agent SDK "Get Started" documentation reiterates:
> "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK. Please use the API key authentication methods described in this document instead." (code.claude.com/docs/en/agent-sdk/overview)

### 1.5 Headless / CLI invocation of Claude Code — explicitly supported

The `code.claude.com/docs/en/headless` page documents `claude -p` (or `--print`) as an officially supported non-interactive mode with subagent orchestration, JSON output, streaming, CI examples, and `claude setup-token` for issuing long-lived OAuth tokens (one-year expiry) specifically for *"CI pipelines and scripts where browser login isn't available"* (code.claude.com/docs/en/iam, "Generate a long-lived token"). This token *"authenticates with your Claude subscription and requires a Pro, Max, Team, or Enterprise plan."*

Bottom line for §7.2: Claude Code itself — running locally on a user's machine and authenticating with that user's subscription — is precisely the intended, sanctioned use of subscription OAuth, including in headless mode. The prohibition targets *third-party* servers that would proxy subscription credentials on users' behalf.

### 1.6 Distinction chart

| Path | Auth | Governing terms | Permitted? |
|---|---|---|---|
| Claude.ai web | OAuth | Consumer | Yes — intended use |
| Claude Code CLI local (interactive or `-p`) on personal Pro/Max | OAuth | Consumer + Claude Code compliance | **Yes — native Anthropic app, ordinary individual use** |
| Claude Code CLI on Team/Enterprise seat | OAuth | Commercial + Claude Code compliance | Yes — added SSO/RBAC controls |
| Third-party tool authenticating with a user's Pro/Max OAuth token | OAuth (extracted) | Consumer + Claude Code compliance | **No — explicitly prohibited** |
| Agent SDK in a hosted product | API key | Commercial | Yes |
| Agent SDK in a hosted product using consumer OAuth | OAuth | violates Consumer + compliance | **No** |

---

## §2 Claude for Enterprise — Current State

*Sources:* claude.com/pricing/enterprise, claude.com/pricing, code.claude.com/docs/en/authentication ("Set up team authentication").

Feature inventory (all quoted from the Enterprise page unless noted):

- **Products bundled:** Claude Chat, Claude Code, Claude Cowork, Claude Security; connectors for Gmail, Google Drive, Slack, Microsoft 365, Chrome.
- **Identity & access:** "Single sign-on (SSO/SAML) and domain capture"; "SCIM provisioning"; "Role-based access control (RBAC)".
- **Observability & governance:** "Usage analytics and reporting"; "Spend controls"; "Audit logs and OpenTelemetry monitoring"; Compliance API; "Data retention controls" (Enterprise only).
- **Compliance:** "SOC 2, ISO 27001, GDPR, and CCPA compliance"; "HIPAA-ready offering" (BAA extends to Claude Code with Zero Data Retention enabled — code.claude.com/docs/en/legal-and-compliance, "Healthcare compliance").
- **Data:** "Your prompts, data, and results are not used to train our models by default."
- **Pricing:** $20/seat plus usage at API rates (per claude.com/pricing summary).
- **Claude Code specifics:** Enterprise adds *"managed policy settings for organization-wide Claude Code configurations,"* plus `forceLoginMethod` / `forceLoginOrgUUID` device-managed pins that restrict developer sessions to a specific Anthropic organization (code.claude.com/docs/en/iam).

**What Claude for Enterprise does NOT include** (verified by absence from every Anthropic surface consulted):

- No mention of Temporal, Airflow, Prefect, or any workflow orchestration engine.
- No cross-user shared-agent primitive. Each seat is an individual Claude Code / Claude.ai identity; sessions do not span users.
- No federation layer, no A2A/MCP registry hosted at the enterprise tier.
- No published "team workflow" runtime — the closest surface, "Routines" (code.claude.com/docs/en/routines), is per-user scheduled invocation of a single user's Claude Code, not a multi-user workflow substrate.

The paper's positioning — "Claude for Enterprise provides shared *access* but not shared *orchestration*" — is confirmed by the feature inventory. The Enterprise product is a fleet-management + compliance envelope wrapped around individual Claude Code sessions.

---

## §3 Anthropic Public Statements on Team / Multi-User Patterns and Roadmap

### 3.1 Definitive (published product surfaces)

- **Sub-agents and dynamic workflows** — `code.claude.com/docs/en/sub-agents`; blog *"A harness for every task: dynamic workflows in Claude Code"* by Thariq Shihipar and Sid Bidasaria, June 2, 2026 (claude.com/blog). Establishes eight compositional patterns (classify-and-act, fan-out-and-synthesize, adversarial verification, generate-and-filter, tournament, loop-until-done, …) — **all within a single user's Claude Code process**, not across users.
- **Agent SDK** — Python and TypeScript packages; explicitly commercial-terms-governed; API-key-authenticated for developer-built products.
- **Claude Code Plugins Marketplace** — launched October 9, 2025; official directory published May 22, 2026 (55+ curated plugins + community catalog with automated safety screening; "Anthropic Verified" badge for stricter-reviewed entries). Directory is a git-hosted `.claude-plugin/marketplace.json` manifest; anything on GitHub, GitLab, Bitbucket, or self-hosted git can serve as a marketplace. Sources: techtimes.com/articles/317139, github.com/anthropics/claude-plugins-official.
- **Skills** — `.claude/skills/*/SKILL.md` layer, packaged and shareable inside plugins.
- **Third-party integrations** — Amazon Bedrock, Google Cloud Agent Platform, Microsoft Foundry, plus a self-hostable "Claude apps gateway" for organizations that want to route inference through their own IdP and cloud provider (code.claude.com/docs/en/claude-apps-gateway).

### 3.2 Directional signals (Anthropic personnel statements)

- **Boris Cherny (Head of Claude Code), "Steps of AI Adoption," July 16, 2026** — Five maturity levels: 0 Gated → 1 Assisted (1 agent) → 2 Parallel (~10 agents/engineer) → 3 Supervised Autonomy (~100 agents) → 4 AI-native (1,000+ agents). Cherny cites Anthropic itself operating at Step 3 org-wide with his personal workflow at Step 4. Notably, the framework is a *per-engineer* multi-agent progression — the "1,000 agents" are spawned by one human, not federated across humans. (explainx.ai/blog, and secondary summaries.)
- **Cat Wu (Head of Product, Claude Code + Cowork), TechCrunch May 13, 2026** — "The next big step for AI is proactivity" (AI anticipating user needs). No public commitment to a multi-user orchestration primitive.

### 3.3 Reverse-engineered / community observations

- **February 2026 OAuth crackdown coverage** — winbuzzer.com (Feb 19, 2026), alternativeto.net (Feb 2026), aihackers.net all report that server-side enforcement blocked previously-working third-party tools (OpenClaw, OpenCode, Roo Code, Goose) that had extracted consumer OAuth tokens. Anthropic's `code.claude.com` policy was published contemporaneously to codify the enforcement.
- **June 15, 2026 Agent SDK credit-pool change — paused.** Anthropic announced (May 14, 2026) that Agent SDK / `claude -p` / GitHub Actions / third-party ACP callers would exit the subscription usage pool and draw from a separate monthly USD credit ($20 Pro / $100 Max-5x / $200 Max-20x). Interactive Claude Code TUI, Claude Cowork, and Claude.ai were explicitly unaffected. Per digitalapplied.com (June 15, 2026): *"Anthropic has paused the June 15 Agent SDK billing change — it is not taking effect."* As of this synthesis, subscription pools continue to cover headless Claude Code CLI usage. (Confidence: high on the pause; the operational status could shift, so any citation should be dated.)

### 3.4 What Anthropic has *not* said publicly

- No stated roadmap item for cross-user shared agent state.
- No public commitment to a hosted A2A registry / federated-agent marketplace.
- No public analog of the paper's "federation layer" architecture at the enterprise tier.

---

## §4 Implications for the Paper's §7.2 Argument

**The claim holds up — and can be sharpened from principle to citation.**

### 4.1 The federation architecture the paper describes matches Anthropic's own permitted pattern

The paper's §7.2 says: each participant runs Claude Code on their own machine under their own subscription; nothing is proxied; the federation layer sees only agent-to-agent messages (MCP / A2A), never credentials. Anthropic's Authentication and Credential Use policy defines the same shape as the *permitted* case:

- Claude Code is a *"native Anthropic application"* whose OAuth use is *"designed to support ordinary use…for purchasers of Claude Free, Pro, Max, Team, and Enterprise subscription plans."*
- The Consumer §3 automation prohibition contains the carve-out *"or where we otherwise explicitly permit it"* — Claude Code CLI (including `-p`) is that explicit permission, documented across `code.claude.com/docs/en/headless`, `iam`, and `legal-and-compliance`.
- The prohibition Anthropic emphasizes is *"third-party developers…rout[ing] requests through Free, Pro, or Max plan credentials on behalf of their users"* — precisely the shared-server-tier pattern the paper's architecture avoids.

### 4.2 Recommended §7.2 rewrite framing

The paper can now state (with citation) that its architecture is *aligned with* Anthropic's stated policy rather than merely *not prohibited by* it. Suggested load-bearing citations:

1. Anthropic, *Consumer Terms of Service*, §3, "Use of our Services" — the automation prohibition and the *"otherwise explicitly permit it"* carve-out. anthropic.com/legal/consumer-terms.
2. Anthropic, *Claude Code — Legal and compliance*, "Authentication and credential use." code.claude.com/docs/en/legal-and-compliance — the primary quote for §7.2.
3. Anthropic, *Claude Code — Run programmatically* (`claude -p`, `--bare`). code.claude.com/docs/en/headless.
4. Anthropic, *Claude Code — Authentication*, "Generate a long-lived token" (`claude setup-token`). code.claude.com/docs/en/iam.

### 4.3 Boundaries the paper should acknowledge explicitly

To be defensible under scrutiny, §7.2 should note:

- **Enforcement scope is credential handling, not architecture.** Anthropic reserves the right to enforce *"without prior notice"* (code.claude.com/docs/en/legal-and-compliance). A federation implementation MUST NOT: (a) proxy user OAuth tokens through the federation layer, (b) offer Claude.ai login as an authentication method for the federation product itself, (c) route requests to Claude on behalf of federation participants using pooled credentials. If a future implementation crosses these lines it would violate the same policy that currently blesses the architecture.
- **The Agent SDK path is different.** Agent-SDK-based components in the federation must use API keys (Commercial Terms), not consumer OAuth. This is stated twice — in the Legal & Compliance page and in the Agent SDK "Get Started" note. The paper should distinguish "Claude Code as edge substrate" (subscription OAuth OK) from "Agent SDK in a federation runtime" (API key required).
- **Rate-limit assumptions are individual.** *"Advertised usage limits…assume ordinary, individual usage of Claude Code and the Agent SDK"* (compliance page). A federation that fans a single human's intent into many concurrent Claude Code sessions is per-user, but a federation that fans one user's intent across other users' Claude Code sessions would arguably violate the individual-use assumption. §7.2 should specify that federation participants are peers acting on their own tasks, not slave-workers for another participant.
- **The June 15, 2026 billing change was paused, not withdrawn.** Anthropic disclosed an intent to move headless usage to a separate credit pool; that change is not currently in effect but signals the direction of pricing. §7.2 should date its citations and note that headless economics may shift.

### 4.4 Where the paper's argument becomes stronger

The paper can now cite an Anthropic-owned URL that names the exact architectural distinction it makes — "native Anthropic applications" (edge Claude Code) vs. "third-party developers…on behalf of their users" (shared-server proxying). This is a rare case where an infrastructure argument in a research paper can be pinned to a vendor's own compliance page rather than to industry-observer interpretation.

---

## §5 Citation List (URLs, dates, roles)

**Anthropic primary policy documents:**

1. Anthropic. *Consumer Terms of Service*. Effective 2025-10-08. https://www.anthropic.com/legal/consumer-terms
2. Anthropic. *Commercial Terms of Service*. https://www.anthropic.com/legal/commercial-terms
3. Anthropic. *Usage Policy*. https://www.anthropic.com/legal/aup

**Anthropic Claude Code documentation (product surface):**

4. Anthropic. *Claude Code — Legal and compliance* ("Authentication and credential use"). https://code.claude.com/docs/en/legal-and-compliance (canonical source for the OAuth-vs-API-key policy; codified 2026-02-19).
5. Anthropic. *Claude Code — Authentication*. https://code.claude.com/docs/en/iam
6. Anthropic. *Claude Code — Run programmatically (headless)*. https://code.claude.com/docs/en/headless
7. Anthropic. *Claude Agent SDK — Overview* ("License and terms" note). https://code.claude.com/docs/en/agent-sdk/overview
8. Anthropic. *Claude Code — Overview*. https://code.claude.com/docs/en/overview

**Anthropic product / pricing pages:**

9. Anthropic. *Pricing*. https://claude.com/pricing
10. Anthropic. *Claude for Enterprise*. https://claude.com/pricing/enterprise

**Anthropic personnel / blog:**

11. Shihipar, T., and Bidasaria, S. (Anthropic). *A harness for every task: dynamic workflows in Claude Code.* 2026-06-02. https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code
12. Cherny, B. (Anthropic, Head of Claude Code). *Steps of AI Adoption.* 2026-07-16. (Secondary summary: https://explainx.ai/blog/boris-cherny-steps-ai-adoption-claude-code-july-2026)
13. TechCrunch — Cat Wu (Anthropic Head of Product, Claude Code/Cowork), interview. 2026-05-13. https://techcrunch.com/2026/05/13/anthropics-cat-wu-says-that-in-the-future-ai-will-anticipate-your-needs-before-you-know-what-they-are/

**Third-party corroborating coverage (secondary sources; use only for enforcement-history claims):**

14. Winbuzzer. *Anthropic Bans Claude Subscription OAuth in Third-Party Apps.* 2026-02-19. https://winbuzzer.com/2026/02/19/anthropic-bans-claude-subscription-oauth-in-third-party-apps-xcxwbn/
15. AlternativeTo. *Anthropic officially bans using subscription authentication for third-party Claude use.* 2026-02. https://alternativeto.net/news/2026/2/anthropic-officially-bans-using-subscription-authentication-for-third-party-claude-use
16. AI Hackers. *Anthropic OAuth Policy Feb 2026: What Changed.* https://aihackers.net/posts/anthropic-claude-code-oauth-policy-feb-2026/
17. Autonomee. *Is This Allowed? Claude Code Terms of Service Explained.* https://autonomee.ai/blog/claude-code-terms-of-service-explained/
18. Digital Applied. *Claude Credit Overhaul 2026: Anthropic Pauses the June 15 Change.* 2026-06-15. https://www.digitalapplied.com/blog/anthropic-claude-credit-overhaul-june-15-2026
19. TechTimes. *Claude Code Plugins Get Official Directory: Anthropic Flags Unverified MCP Risks.* 2026-05-25. https://www.techtimes.com/articles/317139/20260525/claude-code-plugins-get-official-directory-anthropic-flags-unverified-mcp-risks.htm

**Confidence ratings for §7.2 use:**

- Direct Anthropic-published policy language (items 1–8, 11): definitive.
- Anthropic personnel statements (items 12–13): directional signal.
- Third-party enforcement history (items 14–19): use for historical / calibration context only; do not use as primary policy support.


---

# §9 — HAND CORRECTION, 2026-08-06

**This section was written by hand from news sources, not by a research pass, and has NOT been through `research-critic`. Treat it as directional and re-verify before citing it as definitive.**

## Why this correction exists

**§1–§8 were validated 2026-07-24 and miss three policy events that all occurred before that date.** This is not staleness — it is a coverage gap in a paper whose own header claims to be *"definitive where it quotes published policy"*, sitting under the affordability thesis, on the most volatile subject the pool tracks.

## What actually happened

**1 · 2026-04-04 — third-party agent access BLOCKED.** Anthropic stopped Claude Pro and Max subscribers using flat-rate plans with third-party agent frameworks including OpenClaw and OpenCode. Boris Cherny, head of Claude Code, attributed it to **capacity constraints** — subscriptions were not built for third-party usage patterns. Reported cost increases up to **50×** for affected users. *(TNW; heise online; techbuzz.ai)*

**2 · 2026-05-14 — announced: programmatic use exits the subscription pool.** Claude Agent SDK **and `claude -p` (headless)** would leave Pro/Max/Team/Enterprise pools on 2026-06-15, moving to a **separate monthly dollar credit billed at standard API rates, with no rollover.** Proposed: **$20** Pro · **$100** Max 5× · **$200** Max 20× · **$200** Enterprise Premium. Third-party agents were simultaneously **reinstated** under this mechanism. *(VentureBeat; digitalapplied; claudefa.st)*

**3 · 2026-06-15 — PAUSED.** Anthropic deferred the separate credit pool. **As of this correction, programmatic usage — Agent SDK, `claude -p`, and third-party apps — still draws from subscription usage limits.** Terminal and IDE use is unchanged. *(koromo; Tygart Media)*

## Current state

**`claude -p` draws from the subscription.** Confirmed operationally: this fleet's own run logs return `rate_limit_info` with `"rateLimitType": "five_hour"` and no credit balance — a time-windowed subscription limit, not a metered pool.

## The consequence §7.2 does not carry

**§7.2's claim — that subscription-tier authentication at the edge "sidesteps ToS gray areas by design" — is currently true and rests on a deferred policy change, not on a structural property.**

The affordability thesis states that a long-running loop costs the same as a short one. Under the paused mechanism it would not: at **$200/month for Max 20×, billed at API rates**, this fleet's own measured usage — **$78 for one research cycle, $108 for another** — exhausts the allocation in roughly two cycles before any build or review work.

**And the usage pattern Anthropic named as the problem is ours**: multi-hour autonomous runs with heavy sub-agent fan-out.

## The unanswered question this correction cannot settle

**Does `claude -p` invoked by an operator's own local script fall under the sanctioned "Claude Code on your own machine" path, or under "programmatic Agent SDK use"?** The May announcement named `claude -p` explicitly alongside the SDK, which suggests the latter — but the pause means the distinction is currently untested, and no first-party source states how a personal automation is classified versus a distributed product driving users' installs.

**That distinction is load-bearing for the affordability differentiator and for any future multi-participant deployment.** It is the single most important open question in this paper and should be a topic in its own right.

## Sources

- Anthropic removes OpenClaw from Claude subscriptions — heise online
- Anthropic blocks OpenClaw from Claude subscriptions in cost crackdown — TNW
- Anthropic reinstates OpenClaw and third-party agent usage on Claude subscriptions — with a catch — VentureBeat
- Claude Credit Overhaul 2026: Anthropic Pauses the June 15 Change — digitalapplied
- The Complete Guide to Claude Agent SDK Credits: How `claude -p` and GitHub Actions Billing Changes on June 15, 2026 — koromo
- Claude Code Billing in 2026: Subscription Usage vs the Agent Credit Pool — Tygart Media

**Honest boundary:** every source above is secondary reporting. **No first-party Anthropic policy page was fetched for this correction**, which is exactly the standard §3 requires and exactly what a hand-correction cannot supply. A proper research pass must re-verify all of it against Anthropic's own published terms and support pages.
