---
name: troubleshooting-methodology
description: Systematic debugging methodology using divide-and-conquer bisection + hypothesis-driven testing + structured escalation. Use when diagnosing complex bugs, investigating unexpected behavior, when initial fixes haven't resolved the problem, or when stuck on a problem with no obvious cause.
---

## Principles

Debugging is the scientific method applied to broken code. The failure mode that wastes the most time is **hypothesis lock-in** — picking a theory and trying cosmetic variations of it instead of questioning the theory itself.

Three core ideas:
- **Each test cuts the possibility space in half** — regardless of outcome
- **Each test is anchored to an explicit hypothesis** — if you can't state the hypothesis, you're guessing
- **Stuck has a definition** — a concrete iteration cap, not a subjective feeling

## Process

### 1. Observe
Establish ground truth before theorizing:
- What is the actual symptom? (Exact error message, exact unexpected behavior)
- What changed recently? (Last working commit, recent config edits, dependency bumps)
- What's known to work? (Adjacent code paths, previous version, other environments)

Don't move past observation until you can answer all three concretely. Skipping this is where wheels start spinning.

### 2. Map the possibility space
List candidate causes. Be exhaustive — write them down, don't hold them in your head:
- What could produce this symptom?
- Which candidates are testable, which require speculation?
- Order roughly by likelihood given the recent changes

### 3. Articulate the current hypothesis
**Before designing a test, state the hypothesis explicitly:**

> "Hypothesis: the auth middleware drops the session cookie when the request comes through the reverse proxy. If true, requests bypassing the proxy will succeed."

If you can't state the hypothesis in a sentence, you don't have one — you're about to guess. Stop and return to step 2.

### 4. Design a bisecting test
The test must eliminate **roughly half** the remaining candidates regardless of which way it comes out. A test that only confirms ONE specific theory (and tells you nothing if it fails) is not bisection — it's a guess wearing a lab coat.

Good bisecting tests:
- `curl directly to app port` — proves proxy is/isn't involved
- `git bisect` — narrows the commit range that introduced the regression
- `disable middleware X` — proves middleware is/isn't involved
- `run with verbose logging` — exposes which layer the failure crosses

### 5. Run the test, capture the measurement
Run the test. Record the result. Update the candidate list:
- **Eliminated candidates** — explicitly note what's now ruled out
- **Surviving candidates** — explicitly note what's still in play
- **New candidates** — did the test surface something unexpected?

**Capture negative results as carefully as positive ones.** "X didn't reproduce" is data — record it so you don't re-test the same theory later.

### 6. Decide the next move

- **Cause clear?** → Apply the fix. Verify the ORIGINAL symptom is gone (not just "the code runs again" — the original symptom is the success criterion).
- **Possibility space narrow but answer not obvious?** → **Web search prior art.** Someone has almost certainly hit this. Don't reinvent debugging that's already documented.
- **Possibility space still wide?** → Return to step 3 with a refined hypothesis.

### 7. Iteration cap — escalate before you spin

**After 3 cycles where the test result did NOT eliminate at least half the remaining candidates, escalate.** Three cycles without halving is the trigger between "diagnosing" and "wheel-spinning."

When escalating, hand the user structured state, not "I'm stuck":

```
Symptom:
- [exact observation]

Known facts (with evidence):
- [fact 1] — proved by [test/observation]
- [fact 2] — proved by [test/observation]

Ruled out (with evidence):
- [theory A] — disproved by [test result]
- [theory B] — disproved by [test result]

Current hypothesis:
- [explicit statement]

What would tell us next:
- [test C would distinguish between theories D and E]

Where I'm blocked:
- [specific gap — domain knowledge? access? a question only the user can answer?]
```

The user can intervene with one read instead of three rounds of follow-up questions.

## Criteria — am I doing it right?

After each cycle, check:
- Did I state the hypothesis BEFORE designing the test? (If no: lock-in risk)
- Did my test eliminate roughly half the candidates? (If no: guessing, not bisecting)
- Did I measure, or did I assume? (If assume: not real progress)
- Have I tried the same fix twice with cosmetic variation? (If yes: stop, escalate)
- Am I past 3 cycles without halving? (If yes: escalate now)

## Examples

### Good — bisecting test with explicit hypothesis

> Symptom: API returns 502 only for one specific user.
> Hypothesis: the user's session token contains a character that breaks the auth middleware's parser.
> Test: `curl` the API with that user's exact token vs a freshly-generated token for the same user.
> Outcome (either way) eliminates ~half: if both fail, it's not the token format; if only the original fails, it IS token-format-related.

### Bad — non-bisecting "test"

> Symptom: API returns 502 only for one specific user.
> "Let me add more logging to the auth middleware and see what shows up."
> No hypothesis. No success criterion. Result is noise.

### Good — web search at the right moment

> Cycle 4: I've narrowed the issue to a Kubernetes ingress timeout, but I can't see why the timeout fires before the configured threshold.
> Web search: "nginx ingress timeout fires before annotation value" → known issue with conflicting annotations on different ingress objects.

### Bad — web search at the wrong moment

> Cycle 1: "API is slow sometimes." Immediately search "why is my API slow."
> The space hasn't been narrowed. Search results are noise.

## Red flags

- **Trying fixes without articulating what would tell you it worked.** "Let me try this" with no success criterion is guessing.
- **Repeating the same approach with cosmetic variation.** Re-running with a different timeout, retry count, or log level is the same test, not a new one.
- **Treating "compiles / runs / no errors" as success.** The original symptom is the success criterion. Until it's gone, you haven't fixed it.
- **Web searching too early.** Before narrowing, search results are noise. Narrow first, then search.
- **Web searching too late.** After 5 cycles of guessing, you've already wasted what 30 seconds of search could have prevented.
- **Silent giving up.** Drifting onto other work because the bug is hard. Either keep going with method, or escalate with structured state.
- **Pivoting hypotheses without recording why.** If you abandon a theory, write down what disproved it. Otherwise you'll waste cycles re-testing it later.

## Checklist

Per cycle:
- [ ] Hypothesis stated explicitly (one sentence)
- [ ] Test designed to halve the possibility space regardless of outcome
- [ ] Test executed and result measured (not assumed)
- [ ] Candidates updated — both eliminated and surviving
- [ ] Next move chosen: fix / web search / refine hypothesis / escalate

When escalating:
- [ ] Symptom restated exactly
- [ ] Known facts listed with evidence
- [ ] Ruled-out theories listed with disproof
- [ ] Current hypothesis stated
- [ ] Next-test proposal stated
- [ ] Specific blocker named

## When to invoke this methodology

This is for **complex problems where initial fixes haven't worked.** For trivial bugs (typo, missing import, obvious null check), just fix them.

Cues to invoke:
- You've already tried 1-2 fixes and the symptom is unchanged
- The cause space is wide enough that you don't know where to start
- The problem crosses layers (network, auth, database, frontend, infra) and you don't know which layer
- The user has explicitly fired `/troubleshoot`
- You notice yourself trying cosmetic variations of the same approach
