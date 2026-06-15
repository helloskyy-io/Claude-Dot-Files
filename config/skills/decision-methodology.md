---
name: decision-methodology
description: Five-whys cascade for decision-making — reframe the question before answering it, check whether the decision itself is a symptom of an upstream issue, apply best practices to the reframed question. Use when facing a decision with low or mid confidence, when multiple plausible options exist with no clear winner, when about to ask the user "which way should I go?", or when you've been weighing options without converging.
---

## Principles

The failure mode that wastes the most time in decision-making is **accepting the framing as given.** When confidence on a decision is low or mid, the question itself is often wrong — and answering a wrong question well still produces the wrong answer.

Three core ideas:
- **Low/mid confidence is a SIGNAL, not the decision** — it's the cue to step back, not to push harder on the local frame
- **Indecision is often a symptom of an upstream bad choice** — find the upstream issue and the local decision often dissolves
- **Most "hard decisions" are easy once reframed** — they're hard because they're framed wrong, not because the underlying problem is hard

## Process

### 1. Recognize the trigger
You should invoke this methodology when ANY of these are true:
- You'd assess your own confidence on the decision as "low" or "mid" if asked
- You can list 2+ options but can't articulate why one is clearly better
- You're about to ask the user "which approach should I take?" (forcing the user to do the reframing)
- You've been weighing options for several iterations without converging
- The phrase "I'll just go with X" feels arbitrary

If you're at "high confidence, just decide" — skip this methodology and decide.

### 2. The five whys cascade
Apply in order. Don't skip whys to get to the answer faster — the skipped why is usually where the real reframe lives.

**Why 1 — Why is this a decision at all?**
What is the underlying need this decision is supposed to satisfy? Not "which option should I pick?" but "what am I actually trying to accomplish?"

**Why 2 — Why does the system constrain us this way?**
What constraint is forcing this fork? Understand it — sometimes the constraint is real, sometimes it's assumed.

**Why 3 — Why is this functionality actually required?**
Is the requirement real, or inherited from a context that no longer applies? "We've always done it this way" is not a reason.

**Why 4 — Is this decision appropriate for this platform/scope?**
Does this decision-point belong HERE in this layer/component/codebase? Sometimes the right answer is "this decision belongs somewhere else entirely."

**Why 5 — Why are we stuck?**
What earlier choice put us at this fork? Is there an upstream fix that would dissolve this decision rather than answer it? **This is the most important why** — many low-confidence decisions exist because an earlier bad choice routed work to this dead end.

**Why 5 may iterate.** If the upstream answer reveals ANOTHER bad choice further upstream, chase it. Cap at 2 additional iterations (total whys ≤ 7). Beyond that, you've hit a genuinely systemic issue — escalate to the user with the upstream chain documented.

### 2.5 Cascade guardrails
The cascade can over-iterate. **Stop when ANY of these are true:**
- A why produces a clear reframe (decision dissolves, BP applies, or genuine trade-off emerges)
- A why returns "I don't know" — that's the boundary of available knowledge; surface it as the escalation point, don't fabricate
- Two consecutive whys return the same answer — you've bottomed out
- Total whys reach 7 — hard cap to prevent infinite cascading

The point of cascading is to find a reframe. If new whys aren't producing new framings, stop and escalate honestly.

### 3. Apply best practices to the reframed question
After the cascade, you'll have one of three outcomes:

- **The question dissolved** — the cascade revealed the decision was unnecessary, or belongs elsewhere, or has an obvious answer when reframed. Take the dissolved-question path.
- **The question is real, and industry best practice answers it** — apply `/best-practices` to the REFRAMED question (not the original). High confidence now exists because the question changed. **This is the path most reframed questions take** — best practices solve most decisions once the framing is right.
- **The question is real AND genuinely ambiguous** — now you can present the trade-off honestly to the user, WITH the reframing context. The user gets a clean choice between two real options, not a confused choice between five framings.

### 4. Decide or escalate honestly
If the methodology produced clarity → decide.
If the question is genuinely ambiguous → escalate to the user with structured framing:

```
Original decision: [as initially framed]

Reframing (after the cascade):
- Why am I really asking: [underlying need]
- Upstream check: [no upstream issue / upstream issue found and noted]
- Best-practices check: [BP says X / BP is silent here]

Genuine trade-off:
- Option A: [pro] / [con] — best when [context]
- Option B: [pro] / [con] — best when [context]

My recommendation: [if I have one, with reasoning] / [I genuinely don't have a preference because the trade-off depends on a factor only you can judge — which is: ...]
```

This is the "explicit escalation > confused punt" discipline. The user gets a clean question, not a fog.

## Criteria — am I doing it right?

After the cascade, check:
- Did I question the FRAMING, or just weigh options within it? (If just weighed: framing escape didn't happen)
- Did I check upstream for a dissolving fix, or skip to the local question? (If skipped: most-important-why missed)
- Did the cascade actually change my confidence, or did I rationalize my original lean? (If rationalized: not honest reframing)
- Did I apply /best-practices to the REFRAMED question, or to the original? (Original = wasted reframe)
- Am I escalating to the user with structured framing, or punting with "what do you want?" (If punting: methodology incomplete)

## Examples

### Good — cascade dissolves the decision

> Original: Should we use Redis or Postgres for the rate-limiter cache?
> Why 1: Why a cache at all? — to avoid hitting the DB on every request
> Why 2: Why does that matter? — DB load under traffic spikes
> Why 3: Why is that a real concern HERE? — actually, this endpoint sees < 10 RPS
> Result: Decision dissolves. No cache needed; the framing assumed a load profile that doesn't exist.

### Good — cascade finds upstream issue

> Original: Should auth tokens live in the session table or a dedicated tokens table?
> Why 1: Why split them? — they have different lifecycles
> Why 2: Why do they share a parent? — the session model includes token metadata
> Why 5 (upstream): Why is token metadata on the session model? — because the original auth implementation conflated session-state and token-state.
> Result: The real fix is upstream (separate session from token). The local decision dissolves once the upstream split happens.

### Good — cascade leaves a real question that /best-practices answers

> Original: Should the new service use REST or gRPC?
> Why 1-4: confirms the underlying need (internal service-to-service comm, low-latency, polyglot clients)
> Why 5: no upstream issue — the service legitimately needs to exist
> Apply /best-practices to the REFRAMED question: "internal high-throughput polyglot RPC"
> BP answer: gRPC is the industry-standard fit for this profile. Decide gRPC with high confidence.

### Bad — weighing within the wrong frame

> Original: Should we use Lambda or ECS for the image-processing service?
> "Lambda is serverless but has cold starts. ECS has lower latency but more ops overhead. Let me make a pros/cons table..."
> Missing: WHY image processing as its own service at all? Is the underlying need actually "process images" or "deliver thumbnails to the frontend"? If the latter, the answer might be a CDN-side resize, not either Lambda or ECS.

### Bad — punt to user without reframing

> "Should I use a hash map or a sorted set for the leaderboard? I see arguments for both. Which do you prefer?"
> The user now has to do the reframing work that should have happened first: what's the actual access pattern, what scale, what update frequency, etc.

## Red flags

- **"I've been thinking about this for a while, I should just decide."** — Sunk cost. The right move when stuck is to step back, not to push harder.
- **Pros/cons tables for options where the framing hasn't been verified.** — Polishing the wrong question.
- **"Both are reasonable, I'll go with X."** — If both are reasonable, the question is likely wrong. Reframe.
- **Asking the user "which approach?" without the cascade context.** — Punting the reframing work.
- **Treating "best practices" as a tiebreaker AFTER weighing options.** — BP should inform the REFRAMED question, not break ties in a wrongly-framed comparison.
- **Skipping Why 5 (upstream check).** — This is where the most valuable reframes live. Most-skipped why.
- **Confident decisions made fast without the cascade.** — If your confidence is genuinely high, you don't need the cascade. But verify it's confidence, not bias.
- **Iterating Why 5 beyond the cap.** — If you're past Why 7 still chasing upstream, you've hit a systemic issue. Escalate, don't keep cascading.

## Checklist

When stuck on a decision:
- [ ] Confirmed: this is low/mid confidence, not "I just need to decide"
- [ ] Why 1 — underlying need articulated (not "which option?")
- [ ] Why 2 — constraint forcing the fork understood
- [ ] Why 3 — requirement validated as real (not inherited assumption)
- [ ] Why 4 — appropriate scope/platform confirmed
- [ ] Why 5 — upstream check completed (most important — don't skip)
- [ ] Cascade stop condition recognized (reframe found / IDK / repetition / cap hit)
- [ ] Best practices applied to REFRAMED question (not original)
- [ ] Outcome: dissolved / BP answers it / genuine trade-off (one of three)
- [ ] If genuine trade-off, structured escalation prepared (not "what do you want?")

## When NOT to invoke

- High confidence on the decision — just decide
- Decisions that are reversible and cheap (use early returns or use late returns? — just pick one)
- Time-critical decisions where 5-whys cost exceeds the value of the reframe
- Decisions already structured by the project standard (per-standard binding decisions — follow the standard, don't re-derive it)
