# The activity retry boundary — what actually triggers a Temporal retry, and where `gh()`'s retry belongs

```
Topic:          How Temporal's Python-SDK activity retry mechanics (RetryPolicy,
                non_retryable_error_types, and specifically WHAT TRIGGERS a retry — a raised
                exception vs. a returned ActivityResult with status="failed") compose with this
                fleet's already-built in-process bounded retry for `gh` CLI calls, once those
                calls move inside a Temporal activity.
Feeds:          docs/development/sprint.md § Temporal Integration, the two unchecked items
                "Rule the retry boundary before wrapping anything" and "Reduce gh()'s own retry
                when wrapping" (lines 189–190) → the Temporal Integration phase doc's Stage-B
                activity-wrapping design.
Last validated: 2026-08-19
Revalidate:     medium — 3 months
Confidence:     DEFINITIVE on every SDK/server mechanic in §2 — each is read from raw first-party
                source pinned to a commit SHA, and every quoted span below was re-verified
                byte-exact with `curl … | grep -F` at write time (21 spans, all VERIFIED; method
                in §6). DEFINITIVE on the first-party doc statements in §2.6 and §3.
                DERIVED on §3's recommendation and on §2.5's claim that the sprint's proposed
                design cannot express `_RETRYABLE_HTTP`'s split as written — the inputs are
                definitive, the composition is this paper's. FINDING (negative, method stated):
                first-party Temporal documentation gives no guidance on composing a library's
                own in-process retry with the SDK's. UNVERIFIED: nothing asserted here has been
                run against a live Temporal server — see §7.
Critic:         not-yet-verified — 2026-08-19
```

## 1. Primer — two retry layers, and only one of them can see the classification

`gh()` in [`assistant_activities.py`](../../../../../scripts/workflows/temporal/modules/assistant/assistant_activities.py) already owns a bounded retry: `_RETRYABLE_HTTP = frozenset({429, 502, 503, 504})` plus a phrase-promoted 403, gated by `_gh_is_read_only` (mutations are never retried — issue #41 recorded duplicate comments) and by `_gh_timed_out_line` (a hang is terminal), with `_GH_RETRY_BACKOFF_SECONDS = (2.0, 6.0)` — three attempts. Its own comments argue that split; this paper does not re-derive it. Temporal adds a second, outer retry layer around the whole activity. The sprint's worry is the product: 3 × 3 = 9. The real question is narrower and mechanical — **what does Temporal actually observe of a `gh` failure, and what can it act on?**

## 2. The mechanics (definitive; raw source, SHA-pinned)

**2.1 A retry engages ONLY when the activity raises.** In the Python worker, the activity's return value is encoded and set as a *completed* result — `completion.result.completed.result.CopyFrom(payload)` — and the failure path is the enclosing `except BaseException as err:` [S4]. **Returning an `ActivityResult(status="failed")` is a successful Activity Task Execution**; the retry machinery is never consulted, because the server's decision function takes a `Failure` proto and there is none [S5]. This is the load-bearing fact for §3.

**2.2 Every raised exception becomes an `ApplicationError` whose `type` is the class name.** A non-`FailureError` exception is converted with `type=exception.__class__.__name__,` [S3] — bare class name, no module path. First-party docs corroborate: "*Any* other exceptions that are raised from your Python code in a Temporal Activity will be converted to an `ApplicationError` internally." [S7]

**2.3 `non_retryable_error_types` matches by EXACT STRING against `ApplicationFailureInfo.type`.** The SDK carries it as `non_retryable_error_types: Sequence[str] | None = None` / `"""List of error types that are not retryable."""` [S1]; the server decides inside `IsRetryableFailure` with a `slices.Contains(` call whose second argument is `failure.GetApplicationFailureInfo().GetType()` — the two spans sit on consecutive lines of one multi-line call, and are quoted here as the separate fragments they are, not recombined into a line that does not exist in the file [S5]. **No subclass awareness, no prefix or glob matching** — `slices.Contains` is equality over strings. Docs agree: "Errors are matched against the `type` field of the [Application Failure]" [S6].

**2.4 Three ways to signal, and their precedence.** The server checks `if failure.GetApplicationFailureInfo().GetNonRetryable() {` *before* consulting the list [S5], so: (i) **terminal, implementer decides** — `ApplicationError(..., non_retryable=True)` [S2], always wins; (ii) **terminal, caller decides** — the type string listed in the workflow's `RetryPolicy` [S6][S7]; (iii) **let the default apply** — raise anything at all. Note also that timeouts are matched by a *different* key: only `"TemporalTimeout:StartToClose"` / `":Heartbeat"` entries suppress a timeout retry [S5]. **Consequence: a worker crash (a start-to-close timeout) still retries even when every application error type is listed non-retryable** — infrastructure recovery is not forfeited by a terminal error vocabulary.

**2.5 The sprint's proposed design requires a typed raise, and today's `gh()` cannot supply one (DERIVED from 2.1–2.3 + repo source).** `gh()` raises `RuntimeError(f"gh {' '.join(args)} failed in {repo_root}: …")` — one bare type for *every* `gh` failure. Under 2.2 that lands as `type="RuntimeError"`, so `non_retryable_error_types` has exactly one string to work with and **cannot express the `_RETRYABLE_HTTP` split at all**: listing it makes a 503 terminal, omitting it makes a 404 retry forever under the unlimited default. Carrying the classification across therefore requires the activity to raise a **typed** error, e.g.:

```python
retryable = bool(_gh_transient_reason(r.stderr)) and _gh_is_read_only(args)
raise ApplicationError(f"gh {label} failed: {r.stderr.strip()}",
                       type="GITHUB_UNAVAILABLE" if retryable else "GITHUB_TERMINAL",
                       non_retryable=not retryable)
```

**2.6 Wrapping destroys the signal.** "When an Activity returns an error, the SDK checks the **outermost** error type to determine retryability" [S8] — so any `except … raise RuntimeError(...)` between that raise and the activity boundary silently reverts the classification to one opaque type. This is a live hazard here: `gh_json` and several callers re-wrap.

**2.7 Retry re-executes the whole activity.** "If an Activity performs multiple steps and the last step fails, the entire Activity is retried." … "If step 3 fails, all three steps execute again on retry." [S7] Hence the fleet's binding idempotency requirement applies to the *whole* wrapper, not the `gh` call — [Stateful Patterns §4](../../../../standards/temporal/stateful_patterns.md) ("invoking the activity twice with the same input arguments MUST leave the world in the same final state"), and [Temporal Standard §7.1](../../../../standards/temporal/temporal_standard.md). Cited, not re-derived.

## 3. Comparative landscape — three real compositions

**(a) Sprint's proposal: cut `gh()` to one attempt inside activities; Temporal owns all retrying.** *Requires* 2.5's typed raise and 2.6's no-rewrap discipline. **Gains:** one retry layer; backoff durable across worker restarts; every attempt visible in event history; `next_retry_delay` on `ApplicationError` [S2] can even carry `_GH_RETRY_BACKOFF_SECONDS`' shape upward. **Costs:** every `gh`-wrapping activity must become idempotent over its *entire* body (2.7) before this is safe; and Temporal's RetryPolicy has **no representation for `_gh_is_read_only`** — the policy retries whatever type it is given, so the read-vs-write guard must be folded into the raise or it is lost (the failure mode is issue #41's duplicate comments, at Temporal's attempt count rather than `gh()`'s).

**(b) Keep `gh()`'s bounded retry; make the resulting `GITHUB_*` code terminal to Temporal.** This is the fleet's own documented shape: [Temporal Standard §6.4](../../../../standards/temporal/temporal_standard.md) already carves out `CLUSTER_RECONCILE_CONTROL_PLANE_UNAVAILABLE` and `SEED_CLUSTER_ACCESS_UNAVAILABLE` as terminal *because the activity already bounded-retried in-process*, requiring only that the module name the exception it falls under. **Gains:** the three guards stay where they were measured; composition is 3 × 1, which meets the sprint's stated goal as well as (a) does; per 2.4 a worker crash still retries. **Costs:** `gh`'s pauses are invisible to Temporal (no event-history record); `time.sleep(pause)` is a *blocking* sleep, so inside an `async def` activity it must be reached through a thread executor; and a GitHub outage longer than ~8s is not survived, where Temporal's exponential backoff would have survived it.

**(c) Patterns Temporal itself documents.** Split the activity so only the failing step retries — "You might split this into three separate Activities so only the failed step retries, but balance this against having a larger Event History" [S7]; carry a resumption hint in `heartbeat_details` so a retried attempt skips completed prefix work (covered in depth by [`python_sdk_long_activities.md`](../../../../standards/architecture/research/raw/python_sdk_long_activities.md), *Last validated 2026-08-03, Critic PASS-WITH-FIXES*); and the standing advice "In most cases, let the Retry Policy handle retry limits … Reserve `non_retryable` for cases where retrying is guaranteed to be futile." [S8]

**Recommendation (DERIVED).** For **read-only** `gh` activities that are already idempotent, (a) is the better end state and should be adopted with 2.5's typed raise. For **mutating** `gh` activities and for any wrapper doing file/git work before the `gh` call, (b) is right *today* — it is this repo's own ratified pattern for exactly this situation, it does not forfeit crash recovery, and it does not make correctness depend on an idempotency audit that has not been done. The blocking prerequisite is the same in both: **`gh()` must stop raising a bare `RuntimeError`**, because until it does, neither `non_retryable_error_types` nor a terminal `GITHUB_*` verdict can be expressed.

## 4. What this provides (enumerated, citable)

1. A returned `ActivityResult(status="failed")` produces **zero** Temporal retries [S4][S5]. 2. Any raise becomes `ApplicationError` typed by bare class name [S3][S7]. 3. `non_retryable_error_types` is exact string equality on that type [S1][S5][S6]. 4. `non_retryable=True` outranks the policy list [S5][S2]. 5. Start-to-close timeouts are retried unless `"TemporalTimeout:StartToClose"` is listed [S5]. 6. Re-wrapping an error erases its retryability [S8]. 7. Retry re-runs the whole activity body [S7]. 8. `next_retry_delay` lets an activity set the next backoff per failure [S2].

## 5. Honest boundary analysis

- **Where the recommendation fails:** if the fleet later runs `gh` mutations that GitHub *does* make idempotent (an idempotency key, a conditional update per [Stateful Patterns §4.1](../../../../standards/temporal/stateful_patterns.md)), (b)'s read-only conservatism becomes pure cost and (a) is strictly better. Re-read this section then.
- **(b) is a genuine trade, not a free win.** It hides retry state from Temporal: an operator reading event history sees one long attempt, not three. If observability of transient GitHub failure becomes a requirement, (b) is the wrong answer regardless of its other merits.
- **This whole boundary is moot for `preflight`.** The sprint says so twice and it is mechanically true — no RetryPolicy reaches code that runs before a workflow exists.
- **Nothing here is measured.** Every claim is source-read, none is run. In particular the `time.sleep`-in-async concern (§3b) is inferred from the shipped code's shape, not observed under a worker.
- **A count I cannot make:** §6.4's `GITHUB_*` row points at a GitHub Automation Standard that **is not vendored into this repo** (verified: `ls docs/standards/` — no `github-automation/` directory). The existing `GITHUB_*` vocabulary is therefore **not enumerable from here**, so a `non_retryable_error_types` list cannot be derived from it in this repo; new codes must be minted with the activity under §6.4's engineer-editable carve-out.
- **Negative finding, with method:** first-party Temporal documentation gives **no** guidance on composing a client library's own in-process retry with the SDK's retry policy. Method: `grep -iE "internal retry|own retry|nested retry|retry inside|in-process retry|retry loop|client library retr|sdk retr"` across five enumerated first-party pages fetched raw at docs SHA `acdf6cb` — `best-practices/error-handling.mdx`, `design-patterns/non-retryable-errors.mdx`, `design-patterns/error-handling-patterns.mdx`, `encyclopedia/failures-and-error-handling.mdx`, `encyclopedia/application-failures.mdx`. Zero matches in all five. The pattern in (b) is this fleet's, ratified in its own standard; it is not Temporal's published advice.
- **Related, not re-derived:** an identity minted inside an activity becomes a fresh identity on every retry — see [`durable_dispatch_identity.md`](./durable_dispatch_identity.md) (*Last validated 2026-08-07, Critic PASS-WITH-FIXES*). The unlimited-`maximum_attempts` default and its hazard are established in [`temporal.md`](../../../../standards/architecture/research/raw/temporal.md) (*Last validated 2026-08-05, Critic PASS-WITH-FIXES*) and are not re-verified here.

## 6. Citations

**Verbatim method (binding under Research Standard §3):** every quoted span above was re-verified at write time by `curl -s <pinned raw URL> | grep -cF '<span>'` against the SHA in its citation (repo-internal spans checked against the working tree). **21 spans checked, 21 returned ≥1 match** (count reached by enumerating the checks in one script that numbered and printed each one, then reading the 21 numbered result lines — not by asking any layer for a total). Line-wrapped prose spans were matched against a newline-flattened copy of the source, which is stated here because unwrapping is itself a transformation.

- [S1] temporalio/sdk-python `temporalio/common.py` @ `f1579fc` — [raw](https://raw.githubusercontent.com/temporalio/sdk-python/f1579fc90f46a9365635ff8782e6bce39612518b/temporalio/common.py) — `RetryPolicy` fields. *definitive*
- [S2] temporalio/sdk-python `temporalio/exceptions.py` @ `f1579fc` — [raw](https://raw.githubusercontent.com/temporalio/sdk-python/f1579fc90f46a9365635ff8782e6bce39612518b/temporalio/exceptions.py) — `ApplicationError(type=, non_retryable=, next_retry_delay=)`. *definitive*
- [S3] temporalio/sdk-python `temporalio/converter/_failure_converter.py` @ `f1579fc` — [raw](https://raw.githubusercontent.com/temporalio/sdk-python/f1579fc90f46a9365635ff8782e6bce39612518b/temporalio/converter/_failure_converter.py) — exception → `ApplicationError(type=class name)`. *definitive*
- [S4] temporalio/sdk-python `temporalio/worker/_activity.py` @ `f1579fc` — [raw](https://raw.githubusercontent.com/temporalio/sdk-python/f1579fc90f46a9365635ff8782e6bce39612518b/temporalio/worker/_activity.py) — return → `completed`, raise → `failed`. *definitive*
- [S5] temporalio/temporal `common/retrypolicy/retry_policy.go` @ `5e43259` — [raw](https://raw.githubusercontent.com/temporalio/temporal/5e43259a3624a98048cb3bc277006fb4a73bb75f/common/retrypolicy/retry_policy.go) — `IsRetryableFailure`, exact-string containment, timeout-type prefix. *definitive*
- [S6] Temporal docs `docs/encyclopedia/retry-policies.mdx` @ `acdf6cb` — [raw](https://raw.githubusercontent.com/temporalio/documentation/acdf6cb4d74d8f18a35a44ba0da9a9f1e3ea2967/docs/encyclopedia/retry-policies.mdx) — non-retryable errors matched on `type`. *definitive*
- [S7] Temporal docs `docs/develop/python/best-practices/error-handling.mdx` @ `acdf6cb` — [raw](https://raw.githubusercontent.com/temporalio/documentation/acdf6cb4d74d8f18a35a44ba0da9a9f1e3ea2967/docs/develop/python/best-practices/error-handling.mdx) — raise-from-activities, whole-activity retry, `non_retryable_error_types` check. *definitive*
- [S8] Temporal docs `docs/best-practices/error-handling.mdx` @ `acdf6cb` — [raw](https://raw.githubusercontent.com/temporalio/documentation/acdf6cb4d74d8f18a35a44ba0da9a9f1e3ea2967/docs/best-practices/error-handling.mdx) — outermost-error-type rule; use `non_retryable` sparingly. *definitive*
- [S9] Repo artifact — [`scripts/workflows/temporal/modules/assistant/assistant_activities.py`](../../../../../scripts/workflows/temporal/modules/assistant/assistant_activities.py), `_RETRYABLE_HTTP` / `_gh_transient_reason` / `_gh_is_read_only` / `_gh_timed_out_line` / `gh_attempt` / `gh`. *definitive (read directly)*
- [S10] Binding standard — [`docs/standards/temporal/temporal_standard.md`](../../../../standards/temporal/temporal_standard.md) §6.2–§6.4, §7.1, §7.4. *definitive, binding — cited, never validated here*
- [S11] Binding standard — [`docs/standards/temporal/stateful_patterns.md`](../../../../standards/temporal/stateful_patterns.md) §4. *definitive, binding*
- [S12] Repo artifact — [`docs/development/sprint.md`](../../../../development/sprint.md) lines 189–190. *definitive (read in place)*
- [S13] Sibling research — [`durable_dispatch_identity.md`](./durable_dispatch_identity.md), [`temporal.md`](../../../../standards/architecture/research/raw/temporal.md), [`python_sdk_long_activities.md`](../../../../standards/architecture/research/raw/python_sdk_long_activities.md). *evidence, not binding; validation dates and critic verdicts given inline above*

## 7. Test plan — what research cannot settle

1. **Confirm 2.1 empirically:** an activity returning `ActivityResult(status="failed")` under a `RetryPolicy(maximum_attempts=5)` records exactly one `ActivityTaskCompleted` and no retries.
2. **Confirm 2.3's exactness:** raise a subclass of a listed exception type and observe whether it retries (source says yes — it should retry, because the subclass's own name is what is matched).
3. **Confirm 2.4's timeout independence:** kill a worker mid-activity with every application type listed non-retryable; confirm the start-to-close timeout still produces a second attempt.
4. **Confirm 2.6:** wrap an `ApplicationError(non_retryable=True)` in a `RuntimeError` and verify the retry resumes (i.e. the flag is genuinely lost).
5. **Measure the blocking-sleep concern (§3b):** run today's `gh()` unchanged inside an `async def` activity and observe whether heartbeats stall during `time.sleep`.
6. **Idempotency audit (gates option (a)):** enumerate every planned `gh`-wrapping activity and classify each as naturally idempotent / needs a key / mutating — the list, not a sample. Option (a) is only safe for the first class.
7. **Cost of `next_retry_delay`:** verify an activity can reproduce `_GH_RETRY_BACKOFF_SECONDS`' shape via `next_retry_delay` rather than an internal loop, and that the delays appear in event history.
