# Phase 3 — The retry boundary, and a `gh` failure that carries its own verdict

**Status: ⬜ NOT STARTED.** Third in [rollout order](roadmap.md), and — with [Phase 2](phase2_durable_dispatch_identity.md) — a hard prerequisite for wrapping anything.

Temporal retries an **activity**. `gh()` retries a **call**. Nested without a ruling, that is three attempts times three attempts, and a brief GitHub outage becomes a long stall. Temporal's default policy also retries almost everything it is given, including a `404`, forever.

The sprint item names the fix — cut `gh()` to one attempt inside activities and carry the transient/terminal classification across — and the research found that **the fix has a prerequisite the item never named.** Today's `gh()` raises one bare `RuntimeError` for every failure class, and Temporal matches non-retryable errors by **exact string on the error type's bare class name, with no subclass awareness and no glob**. One string cannot express a two-way split: list it and a `503` becomes terminal; omit it and a `404` retries forever.

---

## Requirements for completion

1. **`gh()` raises a typed error** whose type carries both the transient/terminal split *and* the read-only-versus-mutating guard. Never a bare `RuntimeError`.
2. **Nothing between that raise and the activity boundary erases the classification.** Every re-wrapping site is audited and either fixed or explicitly ruled, with a test that fails if a new one appears.
3. **The boundary is ruled per call class, not once**, and the ruling is written down with its reasoning: read-only and already-idempotent goes one way; mutating, and anything doing file or git work before the `gh` call, goes the other.
4. **`preflight` is demonstrably outside.** It runs before any workflow exists, so no retry policy can reach it. It keeps its own retry unchanged.
5. **Three cases are demonstrated, not asserted**: a transient failure on a read retries at exactly one layer; a terminal failure does not retry at all; a mutating call is bounded at its stated total.

---

## Dependencies

**Inside this component:** none. This phase needs no Temporal runtime — every requirement above is testable against the installed SDK and the shipped code. It is independent of [Phase 2](phase2_durable_dispatch_identity.md) and the two could swap.

**Outside this component:** none.

**What this phase unblocks:** [Phase 5](phase5_the_first_dispatch.md), which cannot wrap a `gh`-calling activity until requirement 1 holds, and which carries the idempotency audit this phase deliberately defers.

---

## What this phase rests on

[`raw/activity_retry_boundary.md`](research/raw/activity_retry_boundary.md) — `Last validated 2026-08-19`, Critic `PASS-WITH-FIXES` from a fresh-context pass that fetched eight external sources at pinned SHAs and re-checked every quoted span byte-exact. The sections: **§2.1–§2.4** for the SDK mechanics, **§2.5** for the typed-raise shape, **§2.6** for the outermost-error-type rule, **§2.7** for whole-body retry, and **§3** for the three real compositions and the split recommendation.

**One honest limit, from the paper's own boundary analysis:** every claim in its §2 is **source-read against pinned commits, and none of it was run against a live worker.** Its §7 names seven test items, none executed. Requirement 5 exists to convert the most load-bearing of them from *read* to *observed*.

**And one negative finding worth carrying, because it changes what to cite:** first-party Temporal documentation gives **no guidance anywhere** on composing a client library's own in-process retry with the SDK's retry policy. The method is in the paper — five enumerated first-party pages fetched raw at a pinned docs SHA, grepped for nine phrasings, zero matches. **So when the ruling in requirement 3 keeps `gh()`'s retry for mutating calls, cite our own [Temporal Standard §6.4](../../standards/temporal/temporal_standard.md), not Temporal.** That section already carves out exactly this shape — an error code whose retryable-looking `*_UNAVAILABLE` suffix is overridden to terminal, in the standard's own words, because it expresses a verdict *"that the activity already bounded-retried in-process"*. It is our precedent, not published Temporal advice, and presenting it as the latter would be false.

---

## §Runtime Verification

**Date:** 2026-08-19 · **Host:** `puma-workstation-mint` · **Runtime verified:** the installed Temporal Python SDK's retry surface, and the shipped state of the `gh` seam this phase changes.

### The SDK surface the design depends on, on the version actually installed

```
$ python3 -m pip show temporalio | head -2
Name: temporalio
Version: 1.27.2

$ python3 -c "import dataclasses; from temporalio.common import RetryPolicy; \
    print([f.name for f in dataclasses.fields(RetryPolicy)])"
['initial_interval', 'backoff_coefficient', 'maximum_interval',
 'maximum_attempts', 'non_retryable_error_types']
```

`non_retryable_error_types` is present on the installed version, which is the field the whole design hangs on. The paper establishes from source that it is matched by **exact string equality** against the failure's type, which is the raised exception's **bare class name** — no module path, no subclass awareness, no prefix matching.

### The shipped `gh` seam

```
$ grep -n '_RETRYABLE_HTTP = \|_GH_RETRY_BACKOFF_SECONDS = ' \
    scripts/workflows/temporal/modules/assistant/assistant_activities.py
896:_RETRYABLE_HTTP = frozenset({429, 502, 503, 504})
938:_GH_RETRY_BACKOFF_SECONDS = (2.0, 6.0)

$ sed -n '1186,1188p' scripts/workflows/temporal/modules/assistant/assistant_activities.py
    r = gh_attempt(args, repo_root)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed in {repo_root}: {r.stderr.strip()}")

$ grep -rln 'gh(\|gh_json(' scripts/workflows/temporal/modules/ --include=*.py
scripts/workflows/temporal/modules/assistant/assistant_activities.py
scripts/workflows/temporal/modules/assistant/build/build_activities.py
scripts/workflows/temporal/modules/assistant/review_pr/review_pr_activities.py

$ grep -rn 'except RuntimeError' scripts/workflows/temporal/modules/ --include=*.py
.../plan/plan_project/plan_project_workflow.py:480:  except (RuntimeError, FileNotFoundError, ValueError) as exc:
.../review_pr/review_pr_workflow.py:393:        except RuntimeError as exc:
.../review_pr/review_pr_workflow.py:627:        except RuntimeError:
```

**The bounded retry is three attempts** — `len(_GH_RETRY_BACKOFF_SECONDS) + 1`, confirmed at `assistant_activities.py:1091`. Composed with Temporal's three that is nine, which is the number the sprint item objects to.

**Re-verify before the build dispatch fires.** These are live source lines; the line numbers will drift and the shapes are what matter.

---

## The hard part, and it is not the typed raise

**Requirement 2 collides head-on with a deliberate, documented, tested design decision in the shipped code, and a build run that treats it as a mechanical audit will break something.**

`gh_json` re-wraps on purpose. Its docstring says why at length: `gh()` raises `RuntimeError` on a non-zero exit and validates nothing about stdout, so every caller that then ran `json.loads` had a **second, unrelated** way to fail — `json.JSONDecodeError`, which is a `ValueError` and shares no base class with the first. That gap was not hypothetical. The retry in `review_pr_workflow._read_thread_for_invariant` exists precisely so a flaky `gh` read cannot discard a completed review; it catches `RuntimeError`; and a zero-exit reply with a truncated body therefore **skipped the retry entirely and crashed the parent build loop.** Normalising both failures onto one exception *type* is what fixed it, and the composed behaviour is pinned by `test_a_decode_failure_IS_retried_by_the_one_caller_that_retries_the_TYPE`.

So the fleet has two requirements that look contradictory:

- **Callers need one type**, because a caller cannot be expected to know which exception families a function's implementation can emit.
- **Temporal needs several types**, because the type name *is* the classification and it does exact string matching.

**They are only contradictory if "type" means the same thing in both sentences, and it does not.** A caller guards with `except`, which **is** subclass-aware. Temporal matches the **bare class name**, which is **not**. That asymmetry is the resolution, and it is the shape this phase should adopt unless the build finds a reason not to: a small hierarchy under a common base, where every existing `except RuntimeError` keeps catching everything it caught before, while the concrete class name each failure carries is what Temporal reads and splits on.

**Two consequences that fall straight out of that shape**, and both must be checked rather than assumed:

- **Listing a base class name in `non_retryable_error_types` does nothing** — no subclass awareness means the base name never matches a subclass's failure. The concrete names are what go in the list.
- **`gh_json`'s decode failure needs a name of its own.** Its docstring is explicit that a zero-exit unparseable body is *not* retryable at that layer and that "retry until it parses" is the loop that turns a deterministic wrong answer into a slow one. Under this phase that judgement stops being a comment and becomes a type Temporal can act on. The one caller that currently retries it does so bounded and deliberately; **that behaviour is pinned by a named test and must be preserved or explicitly re-ruled, not silently changed.**

---

## The ruling, and why it is a split rather than a winner

The paper's recommendation is **two answers, and the split is the finding.**

**(a) Read-only `gh` calls that are already idempotent: cut `gh()` to one attempt and let Temporal own the retry.** Gains: one retry layer, backoff durable across a worker restart, every attempt visible in event history, and the SDK's per-failure `next_retry_delay` can even carry the existing backoff shape upward. **Cost, and it is the blocking one:** Temporal retries the **whole activity body**, not the failed sub-call — so this is only safe once every `gh`-wrapping activity is confirmed idempotent end to end, which is an audit nobody has done.

**(b) Mutating `gh` calls, and any wrapper doing file or git work before the `gh` call: keep the bounded retry and mark the resulting code terminal to Temporal.** This is **not a new pattern.** It is [Temporal Standard §6.4](../../standards/temporal/temporal_standard.md)'s own carve-out, already ratified for exactly this situation. Gains: the composition is three-times-one, which meets the sprint's stated goal as well as (a) does; the guards stay where they were measured; and a worker crash still retries, because a start-to-close timeout is matched by a *different* key and is not suppressed by an application-error vocabulary. **Costs, stated fairly:** `gh`'s pauses are invisible in event history, so an operator sees one long attempt rather than three; the blocking sleep must be reached through a thread executor inside an async activity; and an outage longer than the bounded window is not survived where Temporal's backoff would have survived it.

**`_gh_is_read_only` has no representation in a Temporal RetryPolicy, and this is the sentence to reread if anything here is skipped.** The policy retries whatever type it is handed. The read-versus-write guard exists because a `502` on a mutation may mean the mutation *landed* and only the reply was lost — and issue #41's duplicate-comment incident is what motivated it. **If that guard is not folded into the raise, it is not weakened, it is silently deleted** — and the failure recurs at Temporal's attempt count rather than `gh()`'s.

---

## Implementation steps

- [ ] **Re-read § *Runtime Verification* and § *The hard part* before touching code.** The second one is where this phase's real design work is.
- [ ] **Define the exception hierarchy** — a common base that every existing `except RuntimeError` still catches, with concrete classes whose bare names carry the classification. Write down which name means what.
- [ ] **Fold `_RETRYABLE_HTTP`'s split into the raise.** The classification already exists and is already tested; carry it across rather than re-deriving it.
- [ ] **Fold `_gh_is_read_only`'s guard into the raise.** A transient status on a mutation is not transient for our purposes.
- [ ] **Give `gh_json`'s decode failure its own name**, preserving the one caller that bounds-retries the type today. Re-run `test_a_decode_failure_IS_retried_by_the_one_caller_that_retries_the_TYPE` and confirm it still passes, or re-rule it explicitly with reasoning.
- [ ] **Audit every re-wrapping site across every file that calls `gh` or `gh_json` — read the population off the tree, never off this doc.** The block above recorded three files on 2026-08-19 and that population is already two: PR #133 removed the last `gh` call from `build/build_activities.py` the following day. A count restated in prose is the *derive ≠ declare* seam, and [Phase 5](phase5_the_first_dispatch.md) and [Phase 6](phase6_the_rest_of_the_fleet.md) already state the remedy for their own enumerations. The rule is first-party documented: the SDK checks the **outermost** error type, so one `except … raise RuntimeError(...)` anywhere between the raise and the activity boundary reverts everything to one opaque string.
- [ ] **Ship a test that fails when a new re-wrap appears.** An audit finds today's; only a test stops tomorrow's, and this is exactly the shape that regresses silently because nothing goes red.
- [ ] **Write the per-call-class ruling down**, with the reasoning and with the citation pointing at our own §6.4 rather than at Temporal.
- [ ] **Enumerate the error-code vocabulary this phase mints**, and say why it is minted rather than derived — see the gotcha below.
- [ ] **Leave `preflight` alone**, and add a test asserting it is unreachable from any retry policy. The sprint item says this twice and it is mechanically true; a test is what keeps it true.
- [ ] **Demonstrate requirement 5 against a real worker if [Phase 1](phase1_the_starter_control_plane.md) has landed, or against the SDK's test environment if it has not.** The paper's §2 is entirely source-read; this is the step that observes it.
- [ ] **Record the observed attempt counts** in this doc, not in a summary elsewhere.

---

## Notes, decisions and gotchas

- **A returned failure is not a failure, as far as Temporal is concerned.** An activity that *returns* `ActivityResult(status="failed")` has completed **successfully** — the retry machinery is never consulted, because there is no failure proto for the server to inspect. **A retry engages only when the activity raises.** This is the single most surprising fact in the paper and it inverts the natural reading of a result object whose whole job is to report failure.
- **`non_retryable=True` on the error outranks the policy's list.** The server checks it first. That gives three ways to signal, with a precedence: terminal-because-the-implementer-said-so, terminal-because-the-caller-listed-it, or let the default apply.
- **Listing every application error type as non-retryable does not forfeit crash recovery.** A worker crash surfaces as a start-to-close timeout, which is matched by a separate key entirely. Infrastructure recovery survives a fully terminal error vocabulary.
- **The `GITHUB_*` code vocabulary cannot be derived from anything in this repo.** [§6.4](../../standards/temporal/temporal_standard.md) points it at a GitHub Automation Standard that is **not vendored here** — verified, there is no `docs/standards/github-automation/` directory. So new codes are **minted with the activity** under that section's engineer-editable carve-out, not looked up. Say so in the PR rather than leaving a reader to wonder which existing list they failed to find.
- **This phase deliberately does NOT do the idempotency audit.** Option (a) is limited to read-only calls precisely so that correctness does not depend on an audit that has not happened. The audit belongs to [Phase 5](phase5_the_first_dispatch.md), where the actual population of wrapped activities exists to audit — and until it is done, extending option (a) beyond read-only calls is not permitted.
- **Two open candidates in [`candidates.md`](../../standards/architecture/research/candidates.md) have this phase's surface as their subject** — C-106, on stating a retry policy for external CLI calls in the workflow-script standard, and C-107, on splitting `assistant_activities.py` at the `gh` seam. Both are untriaged. **This phase does not rule either**, and neither is a prerequisite; they are named so the build knows it is working in contested territory and does not re-file the same observations.
- **Where this ruling stops being right, stated so it is noticed rather than rediscovered:** if the fleet later runs `gh` mutations that GitHub itself makes idempotent — an idempotency key, a conditional update — then (b)'s read-only conservatism becomes pure cost and (a) is strictly better everywhere. **Re-read the ruling then.** Equally, if observability of transient GitHub failure ever becomes a requirement, (b) is the wrong answer regardless of its other merits, because it hides retry state from event history by construction.
