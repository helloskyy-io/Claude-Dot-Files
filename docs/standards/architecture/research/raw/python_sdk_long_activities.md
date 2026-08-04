# Python SDK: Long Blocking Subprocess Activities

```
Topic:          Can a single 10–60 minute `claude -p` subprocess run as a Temporal activity under the Python SDK — heartbeating, timeouts, cancellation, worker slot occupancy — and how are multi-megabyte transcripts carried past payload limits?
Feeds:          Phase: Temporal Integration (docs/development/roadmap.md) -> the `claude_cli` activity domain; directly answers the unchecked milestone "Confirm the two known SDK constraints — heartbeating for long activities, payload limits for transcripts"
Last validated: 2026-08-03
Revalidate:     high — 4 weeks
Confidence:     Definitive on the SDK/server mechanics (every API, default and limit below is read from raw first-party source, version-anchored to temporalio 1.31.0 / temporal server main @ 2026-08-03). DERIVED on the recommended activity shape — the ingredients are documented, the composition is this paper's, and no first-party sample of a subprocess-wrapping activity exists. UNVERIFIED on child-process orphaning and on real heartbeat behaviour under a 60-minute run; both are in the test plan.
Critic:         PASS-WITH-FIXES (un-quoted a §3 inference-from-absence that was dressed as a quote from S18; re-marked S33 "Go only" as derived-from-repo-structure; retagged staff-forum claims from the out-of-contract "corroborated" to "unverified" and added the §0 vocabulary-gap note; cited S10b inline) — 2026-08-03
```

**Version anchor (binding on every SDK claim below).** All `temporalio` claims are read from `temporalio/sdk-python@main` on 2026-08-03. `pyproject.toml` on that tree declares `version = "1.31.0"` [S8], and 1.31.0 is the latest release, published 2026-07-29 [S9] — so `main` and 1.31.0 are the same API surface for everything cited. Server-side limits are read from `temporalio/temporal@main` on 2026-08-03. **An unversioned restatement of anything below is unusable; carry the anchor.**

**Scope discipline.** Event sourcing, deterministic replay and the case for durable execution are settled in [`durable_execution.md`](durable_execution.md); the Claude Code CLI surface (flags, exit codes, `stream-json`, session resumption, idempotency hazards) is settled in [`claude_code_integration_surface.md`](claude_code_integration_surface.md). Neither is re-derived here. This paper answers only: *what does the Python worker do to a blocking 10–60 minute child process, and where do the bytes go.*

**§0 Note on a confidence-vocabulary gap (surfaced for the reviewer, not a finding about Temporal).** Two claims in this paper come from **named Temporal staff answering on Temporal's own public forum** ([S26] Maxim, [S38] Chad Retz — both identifiable maintainers, both on `community.temporal.io`). Research Standard §3 offers exactly four classes, and reserves *definitive* for first-party documentation; forum commentary is not documentation, so these are tagged **`unverified`** throughout — the same tag an anonymous blog comment would receive. **What that tag loses:** a named maintainer answering on the vendor's official forum is materially stronger evidence than uncorroborated community commentary, and the contract has no vocabulary to say so. Nothing in this paper rides on the difference — both claims are sizing heuristics that §9's tests measure directly, and neither is load-bearing for a design decision. Recorded here so the reviewer can carry the vocabulary gap upstream rather than re-discovering it.

---

## §1 Primer — the four mechanics that decide this

A Temporal **activity** is a function the worker runs in response to an activity task pulled off a task queue. Four mechanics govern a long one.

**1. The slot.** "A Worker Task Slot represents the capacity of a Temporal Worker to execute a single concurrent Task" [S19, definitive]. An activity occupies its slot for its entire wall-clock duration. Nothing else about a long activity is special to Temporal; it is a slot held open.

**2. The heartbeat.** A heartbeat is a ping from worker to service that the activity is alive. Two things depend on it, and only these two:

- **Worker-death detection.** Without heartbeats, the service cannot learn a worker died until `start_to_close_timeout` elapses. The encyclopedia is explicit that the server "cannot independently detect" a worker crash mid-task and relies on the timeout [S17, definitive]. For a 60-minute `start_to_close`, that is up to 60 minutes of dead air.
- **Cancellation delivery.** "In order for a non-local activity to be notified of cancellation requests, it must be given a `heartbeat_timeout` at invocation time and invoke `temporalio.activity.heartbeat()` inside the activity" [S1, definitive]. No heartbeat, no cancellation — ever.

The SDK's own summary: "all long running, non-local activities should heartbeat so they can be cancelled" [S1, definitive].

**3. The timeouts.** Three, with distinct jobs [S13, S17, definitive]:

| Timeout | Governs | Our shape |
|---|---|---|
| `start_to_close_timeout` | "the maximum time allowed for a single Activity Task Execution" | Must exceed the longest expected `claude -p` run. Temporal staff guidance for a 3-hour activity: "StartToClose … should be 3 hours in your case" [S26, unverified] |
| `schedule_to_close_timeout` | "from when the first Activity Task is scheduled to when the last Activity Task reaches a Closed status" — spans retries | Bounds total spend across attempts |
| `schedule_to_start_timeout` | queue wait before a worker picks it up; non-retryable by design | Detects a saturated or absent worker fleet. Directly degraded by long activities holding slots [S19] |
| `heartbeat_timeout` | "the maximum time between Activity Heartbeats" | The *fast* failure detector. Staff guidance: "It is expected to be relatively small. Let's say one minute" [S26, unverified] |

An activity requires `start_to_close` **or** `schedule_to_close` [S13, definitive]. `heartbeat_timeout` is set **at invocation time by the caller**, not in the activity definition [S1, S13, definitive] — a fact that bites, because the activity author cannot make their own activity heartbeat-capable.

**4. Heartbeat throttling.** Calling `heartbeat()` in a tight loop is cheap: the worker throttles. The interval is the lesser of 80% of `heartbeat_timeout` and `max_heartbeat_throttle_interval` (default 60 s); when no heartbeat timeout is set, `default_heartbeat_throttle_interval` (default 30 s) is used [S3, S17, definitive]. The docstring is explicit: "Default interval for throttling activity heartbeats in case per-activity heartbeat timeout is unset. Otherwise, it's the per-activity heartbeat timeout * 0.8" [S3]. The worker "pauses sending heartbeats after one transmission, retaining the most recent heartbeat data" [S17]. **Consequence for us: heartbeating on every `stream-json` line costs essentially nothing.** [derived from S3 + S17]

---

## §2 The specific options — how a Python activity heartbeats while a subprocess blocks

The Python SDK offers exactly three activity execution models [S1, S14, definitive]:

| Model | Definition | Worker requirement | Cancellation delivery |
|---|---|---|---|
| **Asynchronous** | `async def` | none | `asyncio.CancelledError` into the activity task [S1] |
| **Sync multithreaded** | `def` + `ThreadPoolExecutor` | `activity_executor=ThreadPoolExecutor(...)` | `temporalio.exceptions.CancelledError` injected into the thread [S1, S4] |
| **Sync multiprocess/other** | `def` + non-thread `Executor` | `activity_executor=` + `shared_state_manager=` | **no exception is raised**; a shared event is set, and the activity must poll it [S1, S4] |

`activity_executor` is "required if any activities are non-async" and "`max_workers` on the executor should at least be `max_concurrent_activities` or a warning is issued" [S3, definitive]. For non-thread executors, "all of these activity functions must be 'picklable'" [S1, definitive].

### 2.1 The trap: a `def` activity blocked in `subprocess.run()` cannot heartbeat itself

There is no facility for the SDK to interrupt a blocking call to give the activity a chance to heartbeat. `activity.heartbeat(*details)` [S2] must be called by *some* thread. If the only thread is inside `subprocess.wait()`, nothing calls it.

Worse, **cancellation cannot reach it either**. The threaded-cancellation mechanism is exact and now fully sourced:

- `_activity.py` raises cancellation via `_ThreadExceptionRaiser` → `temporalio.bridge.runtime.Runtime._raise_in_thread` [S4, definitive].
- That bridge function is four lines of Rust: `unsafe { pyo3::ffi::PyThreadState_SetAsyncExc(thread_id, exc.as_ptr()) == 1 }` [S31, definitive].
- CPython documents `PyThreadState_SetAsyncExc` with the caveat that matters: **"This function does not necessarily interrupt system calls such as `time.sleep()`"** [S30, definitive].

**[derived, from S4 + S31 + S30]** A synchronous threaded activity blocked in `subprocess.wait()` / `os.waitpid()` will **not** observe an injected `CancelledError` until that call returns — i.e. until the `claude` process exits on its own. A 60-minute run cancelled at minute 2 keeps burning for 58 more. This is the single most important finding in the paper for anyone tempted by the "just call `subprocess.run()` in a `def` activity" shape.

### 2.2 The four shapes that actually work

**Shape A — async activity + `asyncio.create_subprocess_exec` (RECOMMENDED).** [derived composition of definitive parts]

Every ingredient is first-party:
- `async def` activities need no worker executor and cancellation arrives as ordinary `asyncio.CancelledError` [S1].
- The docs' own warning against blocking applies only to blocking *calls*; awaiting a subprocess does not block the loop [S14].
- CPython: "Standard asyncio event loop supports running subprocesses from different threads by default" [S29, definitive] — the pre-3.8 child-watcher hazard does not apply.
- Reading `stream-json` lines from `proc.stdout` gives a natural heartbeat point per line, and the throttle makes per-line heartbeats free (§1.4).
- On `CancelledError`, the coroutine holds a live `proc` handle and can `proc.terminate()` → the CLI's documented SIGTERM path (abort turn, kill Bash process tree, run `SessionEnd` hooks, exit 143) per [`claude_code_integration_surface.md`](claude_code_integration_surface.md) §5.

The one gap this shape must close itself: `claude` can go quiet for minutes (a long Bash tool call, extended thinking) while still healthy, so per-line heartbeating alone will trip `heartbeat_timeout`. Pair it with a watchdog task on the `auto_heartbeater` pattern — the first-party sample computes its interval as `heartbeat_timeout.total_seconds() / 2` ("Heartbeat twice as often as the timeout") using `asyncio.create_task` [S25, definitive]. **Note the sample is async-only**: its TypeVar is `bound=Callable[..., Awaitable[Any]]`, so it does not apply to `def` activities [S25].

**Shape B — sync threaded activity + a heartbeat thread.** [derived; the enabling constraint is definitive]

Legal, and explicitly anticipated by the SDK: "new threads starting inside of activities must `copy_context()` and then `.run()` manually to ensure `temporalio.activity` calls like `heartbeat` still function in the new threads" [S1, definitive; restated in `activity.py` as "Activities that make calls that do not automatically propagate the context, such as calls in another thread, should not use the calls herein unless the context is explicitly propagated" S2]. So a helper thread *can* heartbeat while the main activity thread blocks — **but §2.1 still holds**: cancellation injected into the blocked main thread will not land. Shape B fixes liveness and does not fix cancellation. Use `subprocess.Popen` + `poll()` in a loop rather than `run()` if you take this path, so the main thread returns to bytecode regularly.

**Shape C — sync multiprocess.** Requires `shared_state_manager` "created by passing a `multiprocessing.managers.SyncManager` to `temporalio.worker.SharedStateManager.create_from_multiprocessing()`" [S1, definitive]; heartbeats route through a `multiprocessing.managers.Queue` drained by a background `_heartbeat_processor` thread [S4, definitive]. Cancellation sets `cancelled_event.thread_event`, which the activity must poll — no exception crosses the process boundary [S4, definitive]. **This buys nothing for our shape**: we already have a child process (the CLI); adding a second layer of process isolation adds pickling constraints and a queue for no gain.

**Shape D — async activity completion (decouple the subprocess from the slot).** `activity.raise_complete_async()` lets "the Activity Function … return without the Activity Execution completing" [S16, definitive]. The activity captures `activity.info().task_token`, launches the run, and returns; an external process later calls `client.get_async_activity_handle(...)` and `complete()` / `heartbeat()` / `fail()` / `report_cancellation()` [S16, definitive]. This frees the worker slot for the whole 60 minutes. The cost: you own process supervision, and you have moved the reliability problem outside Temporal. Discussed in §5.

### 2.3 Escape hatches when cancellation must be shaped

- `with activity.shield_thread_cancel_exception():` — "Context manager for synchronous multithreaded activities to delay cancellation exceptions" [S2]. Implementation is a depth counter; the exception fires when depth reaches zero [S4]. The README adds the sharp edge: "once the last nested form of that block is finished, even if there is a return statement within, it will throw the cancellation if there was one" [S1]. Correct use for us: shield the *cleanup* (worktree removal, transcript upload), not the run.
- `@activity.defn(no_thread_cancel_exception=True)` — "If set to true, an exception will not be raised in synchronous, threaded activities upon cancellation" [S2, definitive]. Converts threaded cancellation into pure polling via `activity.is_cancelled()` / `activity.wait_for_cancelled_sync(timeout)` [S2].
- `activity.is_worker_shutdown()` / `wait_for_worker_shutdown_sync(timeout)` [S1, S2] — distinguishes "the operator is stopping this worker" from "the workflow cancelled me". Worth wiring: the two want different child-process treatment.

---

## §3 Cancellation, shutdown, and the orphan question

**Graceful shutdown default is ZERO.** `graceful_shutdown_timeout` defaults to `timedelta()` [S3, definitive] — "Amount of time after shutdown is called that activities are given to complete before their tasks are cancelled" [S3]. Left unset, a 55-minutes-in `claude` run is cancelled the instant the worker is told to stop. The docs' recommended pattern sets it explicitly (`graceful_shutdown_timeout=timedelta(seconds=30)`) and describes shutdown as: the worker "stops polling for new Tasks and waits for in-flight Tasks to finish, up to `graceful_shutdown_timeout`" [S20, definitive]. The encyclopedia adds: "Activities are allowed to complete during the graceful shutdown period"; after it, "the Activity context is canceled", and the guidance is to "Ensure Activities and Local Activities honor context cancellation or other shutdown signals" [S18, definitive].

**A worker that cannot cancel an activity cannot shut down.** `worker.run()` "will not return until shutdown is complete. This means that activities have all completed after being told to cancel after the graceful timeout period" [S3, definitive], and the README states the consequence outright: "The `shutdown()` invocation will wait on all activities to complete, so if a long-running activity does not at least respect cancellation, the shutdown may never complete" [S1, definitive]. **[derived]** Combined with §2.1, a `def` activity blocked in `subprocess.wait()` will hang `systemctl stop` on the worker unit for the remainder of the `claude` run. That is a deployment-visible defect, not a theoretical one.

**Does a killed worker orphan the `claude` process?**

- **[gap — not documented.]** Searched: `sdk-python` README and `temporalio/worker/_activity.py`, `_worker.py` (raw); the documentation repo's `docs/encyclopedia/workers/worker-shutdown.mdx`, `docs/develop/python/workers/run-process.mdx` (raw); and web search for Temporal worker child-process cleanup. The worker-shutdown page [S18] covers only graceful and non-graceful shutdown initiated by the worker itself; **read in full 2026-08-03, it has no section addressing kill-signal / hard-termination scenarios, and does not use the terms at all** — that is this paper's observation of an absence, not a disclaimer the page makes. Temporal documents nothing about child processes spawned by activities, in any SDK.
- **[derived, POSIX semantics]** Nothing in the SDK reaps a grandchild. On `SIGKILL` of the worker, the `claude` process is reparented and keeps running — burning tokens, holding the git worktree, and racing the retry attempt that Temporal will schedule after `heartbeat_timeout` expires.
- **[definitive, and it is our mitigation]** Bare systemd workers get cgroup cleanup for free: `KillMode` "Defaults to control-group", and in that mode "all remaining processes in the control group of this unit will be killed on unit stop" [S32]. Because the roadmap's topology is *bare systemd processes, never containerized*, the unit's cgroup is the correct kill boundary and systemd already enforces it on `systemctl stop`/restart. **This does not cover `kill -9` of the worker PID by hand, nor an OOM kill of the worker alone**, which leave the unit active and the child alive. Both belong in the test plan.

**Duplicate-execution risk is acknowledged by Temporal, not eliminated.** Temporal staff, on this exact question: "It is not really possible to provide hard guarantee that you don't end up with two activity attempts running at the same time … You can get pretty close by shutting down an activity on an exception thrown from the heartbeat call and setting an initial retry interval larger than the heartbeat interval" [S26, unverified]. **Note the Python asymmetry:** in Go, `RecordHeartbeat` cancels the context when the activity is cancelled or gone [S22], so "an exception thrown from the heartbeat call" is a real signal; in Python `activity.heartbeat()` returns `None` and raises only `RuntimeError` "When not in an activity" [S2, definitive]. **[derived]** The Python translation of Maxim's advice is: poll `activity.is_cancelled()` alongside heartbeating, and set `retry_policy.initial_interval` greater than the heartbeat interval.

---

## §4 Payload limits, precisely

*(Slower-decaying section — server-side constants have been stable across releases. A refresh may re-verify these last.)*

All values read from raw server source, `temporalio/temporal@main`, 2026-08-03 [S10, definitive]. These are `dynamicconfig` *declarations*; the history service reads them into its own config struct at startup, which is where the enforcement points live [S10b, definitive] — so a self-hosted override is a namespace-scoped dynamic-config change, not a code change:

| Dynamic config key | Default | Scope |
|---|---|---|
| `limit.blobSize.error` | `2*1024*1024` = **2 MiB** | "per event blob size limit" — one payload |
| `limit.blobSize.warn` | `512*1024` = **512 KiB** | warning threshold |
| `limit.historySize.error` | `50*1024*1024` = **50 MiB** | whole workflow execution history |
| `limit.historySize.warn` | `10*1024*1024` = 10 MiB | |
| `limit.historyCount.error` | `50*1024` = **51,200 events** | whole history |
| `limit.historyCount.warn` | `10*1024` = 10,240 events | |
| `limit.mutableStateSize.error` | `8*1024*1024` = 8 MiB | per-execution mutable state (global setting) |
| `limit.mutableStateActivityFailureSize.error` | `4*1024` = **4 KiB** | per **activity failure** |

Plus the transport ceiling: **4 MB max gRPC message**, applying to the full request including metadata [S21, S23, definitive]. Server source corroborates indirectly — `MaxHTTPAPIRequestBytes` is documented as "currently set to the max gRPC request size" = 4 MB [S11].

**⚠ First-party contradiction, flagged.** The self-hosted defaults doc lists the blob-size *warning* threshold as **256 KB** [S23]; the server source says `512*1024` [S10]. The error threshold (2 MiB) agrees in both. **Trust the source; the doc is stale on the warn value.** Immaterial to design (it is a log line, not a rejection) but it is a live example of why §4 of the Research Standard prefers raw sources.

**Where each limit bites our shape** [derived from S10, S21]:

- **Activity input and activity result are each single payloads → 2 MiB.** A multi-megabyte transcript returned from the activity fails with `Complete result exceeds size limit` / `[TMPRL1103] Attempted to upload payloads with size that exceeded the error limit` [S21].
- **Heartbeat details are payloads too.** Do not stuff progress text into `heartbeat(...)`.
- **Activity failures are capped at 4 KiB.** Raising an exception whose message carries `claude` stderr will be truncated at the server. Classification enums belong in the error; log dumps do not.
- **History is cumulative.** 50 MiB / 51,200 events across the whole workflow. A parent driving many `claude` legs accumulates; `continue-as-new` is the standard answer.

**The documented remedies, first-party vs community:**

1. **External Storage — first-party, Public Preview since 2026-05-14, Go + Python SDKs** [S28, rendered page — lower confidence on the date/SDK list]. The Python implementation is real and readable: `temporalio/converter/_extstore.py` provides `StorageDriver` (ABC with `store()`/`retrieve()`), `ExternalStorage`, `StorageDriverClaim`, and a default `payload_size_threshold: int = 256 * 1024` [S6, definitive]. **Every public API in that module carries "This API is experimental."** [S6, definitive]. The first-party sample confirms operational shape: S3-compatible backend, "default 256 KiB threshold; payloads still above it are stored in S3", and the binding caveat — "Both the worker and the starter must use the **same** `DataConverter` configuration (codec **and** storage) so each side can read what the other wrote" [S27, definitive].
2. **Payload codec (compression) — first-party but explicitly a stopgap.** The troubleshooting page lists compression via custom Payload Codec as a "temporary measure", and `data-encryption.mdx` steers oversized payloads to External Storage rather than codec compression [S21, S24, definitive]. Codecs run client- and worker-side; a Codec Server is "an HTTP server that uses your custom Codec logic to decode your data remotely" for the Web UI / CLI [S24].
3. **DataDog `temporal-large-payload-codec` — community, and it disqualifies itself.** "please do not use in production. We make no guarantees about backwards compatibility of codecs, the HTTP interface, or storage drivers." Default 128 KB threshold [S33, definitive-as-to-its-own-status]. **Go only** — [derived from repo structure]: the README documents only Go SDK integration and the repo carries no Python surface; the README never states a language restriction outright.

**SDK-side limits moved in 1.31.0 — a breaking change to note.** "Payload size limits have moved from `DataConverter` to `Client.connect`. Pass `payload_limits=PayloadLimitsConfig(...)` (now exported from `temporalio.client`) instead of setting `payload_limits` on `DataConverter`. Config fields were renamed to `payloads_warn_size` and `memo_warn_size`, and the deprecated `PayloadSizeWarning` was removed." [S7, definitive]. **Any code sample found online predating 2026-07-29 will use the old shape.**

**[derived — the recommendation for our shape.]** We should **not** adopt External Storage for transcripts. The roadmap already names GitHub as the durable memory tier and the repos are on the worker host by hard constraint; the transcript's natural home is a file on the repo-local disk plus a commit/artifact reference. That makes our claim check a *pointer we already have* (repo, branch, SHA, path, `session_id`) rather than a second object store to operate, and it keeps the activity result well under 2 MiB by construction. External Storage remains the right answer if a payload must round-trip through the workflow — which, for a transcript, it must not.

---

## §5 Worker slot occupancy and tuning

*(Slower-decaying section, except that `WorkerTuner` is comparatively new API surface.)*

- **Default is 100 activity slots.** With no tuner and no `max_*` arguments, the worker builds a fixed tuner: "Defaults to fixed-size 100 slots for each slot kind if unset and none of the `max_*` arguments are provided" [S3, definitive].
- **`max_concurrent_activities`** — "Maximum number of activity tasks that will ever be given to the activity worker concurrently. Mutually exclusive with `tuner`" [S3, definitive].
- **`WorkerTuner`** supersedes it: "Worker tuners supersede the existing `maxConcurrentXXXTask` style Worker options" [S19, definitive]. Factories: `create_fixed()` ("Any unspecified slot numbers will default to 100"), `create_resource_based()` (targets memory/CPU), `create_composite()` [S5, definitive]. Resource-based defaults: minimum slots 1 for activities (5 for workflows), maximum 500, ramp throttle 50 ms for activities [S5, definitive].
- **Temporal's own recommendation for workloads like ours:** "For most workloads, Temporal recommends fixed-size slot suppliers." Resource-based suits "Fluctuating workloads with low per-Task consumption" such as I/O-waiting HTTP calls, and carries the caveat "You cannot guarantee that the targets for resource-based suppliers won't ever be exceeded" [S19, definitive].
- **The observability hook:** `worker_task_slots_available`, per worker type, is the documented metric for slot depletion, and `schedule_to_start` latency is the symptom [S19, definitive].
- **`max_activities_per_second`** "Limits the number of activities per second that this worker will process" [S3] — a rate limit, orthogonal to slots.

**[derived — what a 60-minute activity actually costs us.]** The slot is the cheap part; a slot is a counter. The expensive part is what the slot *holds*: one `claude` CLI process (Node runtime, MCP stdio children, a git worktree) plus, in the sync-threaded model, one OS thread pinned in the executor for the full hour. The binding number is therefore **how many concurrent `claude` runs the host can afford**, not 100. Concretely: leaving `max_concurrent_activities` at its default 100 on a repo-holding workstation means the worker will cheerfully accept 100 simultaneous `claude` runs. Set a fixed activity slot count equal to the host's real concurrency budget, and set `ThreadPoolExecutor(max_workers=...)` to at least that number to avoid the documented warning [S3]. Resource-based tuning is a poor fit here — a `claude` run's resource profile is spiky and mostly *waiting on a network API*, which reads as idle to a CPU-target supplier and would over-admit.

**Repo-locality is a solved pattern, not a constraint to invent.** The first-party `worker_specific_task_queues` sample exists for exactly our case: each worker process runs two workers — one on a shared distribution queue and one on "a uniquely generated Task Queue" — for "tasks where interaction with a filesystem is required, such as data processing", where in production the per-worker folders "would typically be independent machines in a worker cluster" [S15, definitive]. This is also the mechanism required by session resumption's directory scoping, per [`claude_code_integration_surface.md`](claude_code_integration_surface.md) §8.

---

## §6 Comparative landscape

### 6.1 Other Temporal SDKs — is Python the constrained choice?

**Go — materially better ergonomics for this specific shape.** Activities receive a `context.Context`. `RecordHeartbeat`: "If the activity is either canceled or the workflow/activity doesn't exist, then we would cancel the context with error [context.Canceled]" [S22, definitive] — heartbeating *is* the cancellation channel, and the cancelled context propagates. `GetWorkerStopChannel` "Returns a read-only channel. The closure of this channel indicates the activity worker is stopping" [S22, definitive]. **[derived]** Because Go's `os/exec` accepts a context that kills the child when cancelled, a Go activity gets subprocess-lifetime binding essentially for free — the orphan question of §3 largely disappears.

**TypeScript — the same advantage, differently spelled.** `Context.current().cancellationSignal` is "An `AbortSignal` that can be used to react to Activity cancellation", and the SDK's own docs mention passing it "to abort a child process" [S34, definitive]. The heartbeat requirement is identical and stated bluntly: "Activities must heartbeat in order to receive Cancellation" [S34].

**Python — the outlier, but a mild one.** Python has no context object and no `AbortSignal` to hand to `subprocess`. It has an *event* you must observe: `is_cancelled()`, `wait_for_cancelled_sync(timeout)` — "essentially a wrapper around `threading.Event.wait()`" [S2, definitive] — or, in async activities, ordinary `asyncio.CancelledError`. **[derived]** Shape A (§2.2) recovers most of the Go/TS ergonomics, because `asyncio` cancellation lands in a coroutine that still holds the `Process` handle. So: Python is *not* the constrained choice for the shape we should be writing; it is the constrained choice only for the naive `def` + `subprocess.run()` shape, which is wrong in every SDK. **This does not reopen the language decision** — the roadmap's Python decision rests on the framework and standard being Python, and the delta measured here is a code pattern, not a capability gap.

### 6.2 Other engines

| Engine | Long blocking local subprocess | Payload ceiling | Verdict for our shape |
|---|---|---|---|
| **Restate** | Journal-based durable execution; handlers are RPC-shaped. Enforces "strict size limits on journal entries"; exceeding the configured `message-size-limit` fails the invocation with **RT0003 (`MessageSizeLimit`)**, default **32 MiB** [S35, definitive] — a far more generous per-entry budget than Temporal's 2 MiB | 32 MiB/entry (config) | Larger payload headroom, but no worker-slot/task-queue affinity story for repo-locality, and the AWS-Lambda deployment path it optimises for is irrelevant to bare systemd workers on repo-holding machines |
| **Inngest** | Steps are HTTP-invoked by the platform. "Up to 2 hours" step timeout, "dependent on hosting provider's timeout"; step output 4 MiB; 1000 steps/function [S36, rendered page — directional] | 4 MiB/step output | **Wrong shape.** The engine invokes your endpoint; a 60-minute local subprocess on the machine that holds the git repo is not what an HTTP-step model is for |
| **DBOS Transact (Python)** | Steps are ordinary in-process Python functions on Postgres; "If your program ever fails, when it restarts all your workflows will automatically resume from the last completed step" [S37, definitive] | **[gap]** No step-duration or payload limit documented. Searched: `dbos-transact-py` README (raw) and web search for DBOS step duration/payload limits — neither states one | Genuinely attractive on payload freedom (no 2 MiB wall). But no documented heartbeat/liveness model, no documented cancellation delivery into a blocked step, and no worker-slot/task-queue affinity primitive. Would be a direction change, not a tweak — out of scope against a settled roadmap decision |
| **Cadence / LangGraph / others** | Settled in [`durable_execution.md`](durable_execution.md) §4 | | Not re-derived |

**[derived]** Nothing in this landscape makes a 10–60 minute local subprocess *easy*. Every engine surveyed treats "long blocking work pinned to a specific machine" as an edge case handled by heartbeat-plus-affinity, and every one of them lands the operator with the same two duties: keep something alive that says "still running", and keep the big bytes out of the log. Temporal's version of those duties is the best-documented of the four.

---

## §7 What this provides — enumerated, citable properties

Properties a plan may rely on, at `temporalio` 1.31.0 / temporal server main @ 2026-08-03:

1. **A 10–60 minute activity is a supported, ordinary shape.** No documented ceiling on `start_to_close_timeout` was found (searched: `docs/develop/python/activities/timeouts.mdx`, `docs/encyclopedia/detecting-activity-failures.mdx`, `docs/production-deployment/self-hosted-guide/defaults.mdx`, all raw — none states a maximum). Temporal staff sized a 3-hour activity without qualification [S26]. **[definitive that no limit is documented; the absence of a limit is derived from that.]**
2. **Sub-minute worker-death detection**, independent of run length, via `heartbeat_timeout` [S17].
3. **Free heartbeating.** Throttled to min(0.8 × `heartbeat_timeout`, 60 s) [S3, S17] — heartbeat per `stream-json` line costs nothing.
4. **Resumption hints across retries.** `activity.heartbeat(123, 456)` → `activity.info().heartbeat_details` on the next attempt [S1, definitive]. For us: carry the `session_id` and turn count so a retry can choose `--resume` vs restart. Keep it small — heartbeat details are payloads (§4).
5. **Cancellation that can reach a child process**, in the async shape: `asyncio.CancelledError` into a coroutine holding a live `Process` handle [S1 + S29, derived composition].
6. **Explicit shutdown grace.** `graceful_shutdown_timeout` [S3, S20], plus `is_worker_shutdown()` / `wait_for_worker_shutdown_sync()` to distinguish operator-stop from workflow-cancel [S1, S2].
7. **Cancellation shielding for cleanup.** `shield_thread_cancel_exception()` [S2, S4] and `no_thread_cancel_exception=True` [S2].
8. **Bounded concurrency with a real tuning surface.** Fixed or resource-based slot suppliers [S5, S19], `max_activities_per_second` [S3], and `worker_task_slots_available` to observe it [S19].
9. **Machine affinity as a first-class, sampled pattern** — per-worker unique task queues for filesystem-local work [S15].
10. **Hard, knowable payload numbers**: 2 MiB/payload, 4 MB/gRPC message, 50 MiB & 51,200 events/history, 4 KiB/activity failure [S10, S21, S23].
11. **A first-party claim-check escape**, `temporalio.converter.ExternalStorage` with a 256 KiB default threshold — experimental, Public Preview [S6, S27, S28].
12. **Slot decoupling if we ever need it** — async activity completion via task token [S16].

---

## §8 Honest boundary analysis — when this is the WRONG use of an activity

**The retry economics are bad, and no heartbeat fixes them.** An activity is the unit of retry. A failure at minute 55 of a 60-minute run re-executes the *entire* run: heartbeat details carry a hint, not a checkpoint [S1]. Combined with the non-idempotency of a `claude` invocation ([`claude_code_integration_surface.md`](claude_code_integration_surface.md) §8), a retried attempt re-enters a repo that a previous attempt already mutated. **[derived]** If a workload's expected failure rate times its 60-minute re-run cost exceeds the cost of decomposition, the single-activity shape is wrong regardless of how well it heartbeats.

**Where the alternatives beat it:**

- **Child workflow driving many short activities.** One activity per `claude` turn (`--resume <session-id>`), 1–5 minutes each. Buys: real checkpoints, cheap retries, per-turn observability, small payloads. Costs: history growth against the 51,200-event / 50 MiB ceilings [S10] (mitigable with `continue-as-new`), a per-turn `--resume` that pins every leg to the same host *and directory* (so §5's per-worker queue becomes mandatory, not optional), and the loss of a single continuous CLI process — which may itself change model behaviour. **Genuinely the better shape if the work decomposes.** Whether an agentic run decomposes cleanly into resumable turns is not a Temporal question and is not settled here.
- **Async activity completion (Shape D).** The right answer if the concern is slot/host occupancy rather than durability: the `claude` run becomes a supervised process whose completion is reported by task token [S16]. Costs: you re-own supervision, orphan cleanup, and liveness — precisely the things Temporal was adopted to stop hand-rolling.
- **Standalone activities.** Activities "that run independently, without being orchestrated by a Workflow", executed straight from client code; requires Python SDK ≥ v1.23.0 and Temporal CLI ≥ v1.7.0, and listing APIs "return only Standalone Activity Executions" [S12, definitive]. Attractive for a one-off `claude` run needing retry + observability but no orchestration. **Not** a substitute for the parent/child structure the roadmap already commits to.
- **No Temporal at all.** For a run that a human is watching, that reruns cheaply on failure, and that no other work depends on, the whole apparatus is cost — the boundary already argued in [`durable_execution.md`](durable_execution.md) §6.

**Where our own recommendation is weakest — stated plainly:**

- **[gap]** There is **no first-party sample of a Temporal Python activity wrapping a subprocess.** Searched: the `samples-python` README index (raw, full sample list), the `sdk-python` README (raw), every file under `docs/develop/python/activities/` in the documentation repo (raw), and web search for "temporal python subprocess heartbeat". The nearest neighbours are `custom_decorator` (async-only auto-heartbeat) [S25], `polling` (periodic external resource), and `hello_activity_threaded` / `hello_activity_multiprocess` [S15, samples index]. **Shape A is this paper's composition of documented parts, not a documented pattern.** It should be treated as a design hypothesis until §9's tests pass.
- **[unverified]** The §2.1 claim that `PyThreadState_SetAsyncExc` will not interrupt `subprocess.wait()` rests on the CPython caveat "does not necessarily interrupt system calls" [S30] applied to our case. The inputs are definitive; the application is inference. Test T2 settles it.
- **[unverified]** Real heartbeat behaviour over a 60-minute run — the one community report found on this exact topic was an SDK bug ("Error when recording heartbeat: Status { code: Cancelled … }") fixed in 1.7.1 [S38], which is evidence the path is exercised and also evidence it has broken before.
- **[gap]** Child-process orphaning on worker death is undocumented across all Temporal SDKs (§3). systemd's cgroup kill covers the managed cases [S32]; it does not cover a hand-`kill -9` or a worker-only OOM.
- **[directional at best]** External Storage's SDK version support and backend list come from a rendered changelog page [S28]; the `_extstore.py` module itself is the trustworthy artifact and it says "This API is experimental" [S6].

---

## §9 Test plan — what research cannot settle

Run on a real worker, on a repo-holding machine, against the pinned `temporalio` version and the pinned `claude` CLI version. Every item is a decision gate for the `claude_cli` activity domain.

**Heartbeat and liveness**

1. **Shape A end-to-end.** `async def` activity, `asyncio.create_subprocess_exec("claude", "-p", …, --output-format stream-json)`, heartbeat per line + watchdog task at `heartbeat_timeout/2`. Run 60+ minutes. Confirm: zero heartbeat-timeout failures, no event-loop starvation, `worker_task_slots_available` behaves.
2. **Blocking-thread cancellation (the §2.1 claim).** Sync `def` activity calling `subprocess.run()` on a 10-minute sleep; cancel the workflow at t=30 s. Record whether `CancelledError` lands before the child exits. **Expected: it does not.** If it does, §2.1 and half of §3 need rewriting.
3. **Heartbeat silence budget.** Drive a `claude` run into its longest natural quiet gap (long Bash tool call, extended thinking) and measure the maximum inter-line interval across ≥20 real runs. This number sets `heartbeat_timeout`; guessing it is how we get spurious retries.
4. **Throttle verification.** Heartbeat every line and confirm from server-side heartbeat records that the effective rate is ~0.8 × `heartbeat_timeout`, not per-line [S3, S17].

**Cancellation, shutdown, orphans**

5. **`systemctl stop` mid-run.** With `graceful_shutdown_timeout` set and unset. Confirm: SIGTERM reaches `claude`, exit 143 observed, `SessionEnd` hooks ran, worktree released, unit actually stops. Confirm the zero-default does what §3 predicts.
6. **`kill -9` the worker PID.** Does `claude` survive? Does the systemd unit restart and does the cgroup sweep the orphan [S32]? Then: does Temporal's retry attempt collide with the still-running orphan?
7. **Worker OOM.** Same as (6) under kernel OOM-kill of the worker only.
8. **Shutdown deadlock reproduction.** Sync `def` + `subprocess.run()` + `systemctl stop` — confirm (or refute) that shutdown hangs for the remainder of the run [S1, S3].
9. **Cleanup shielding.** Verify `shield_thread_cancel_exception()` / the async `finally` path reliably runs `git worktree remove` and transcript archival under cancellation, and that the trailing-throw semantics [S1] don't lose the cleanup result.

**Payloads**

10. **Result-envelope sizing.** Measure the real size of the intended `ActivityResult` (session_id, cost, turns, git SHA, pointers, classification) across 50 runs; confirm p99 ≪ 2 MiB with the 512 KiB warn threshold [S10] as the alarm line.
11. **Failure-payload truncation.** Raise an activity failure carrying 100 KB of `claude` stderr; confirm the 4 KiB `limit.mutableStateActivityFailureSize.error` behaviour is truncation-with-usable-classification and not a workflow-task failure [S10].
12. **Heartbeat-details sizing.** Confirm the resumption hint (session_id + turn count) stays trivially small and that `heartbeat_details` round-trips on retry [S1].
13. **History growth for the decomposed alternative.** Simulate a parent driving N short `claude` legs; find the N at which history approaches 10 MiB / 10,240 events (the warn thresholds) and fix the `continue-as-new` cadence from the measurement, not a guess.

**Slots and hosts**

14. **Real host concurrency budget.** Ramp concurrent `claude` activities on one worker host; find the point where RSS, file descriptors, or API rate limits break first. That number — not 100 — is the fixed activity slot count [S5, S19].
15. **Per-worker task-queue affinity.** Implement the `worker_specific_task_queues` pattern [S15] and confirm a `--resume` leg routes back to the same host *and* directory, including after a worker restart.
16. **`schedule_to_start` under saturation.** With all slots held by 60-minute runs, confirm the queued work's `schedule_to_start_timeout` fires as intended rather than silently queueing forever [S17, S19].

**Version hygiene**

17. **Pin and re-verify.** Confirm the deployed `temporalio` version, and re-run (2), (5) and (6) on any minor upgrade — the cancellation path has regressed before [S38].

---

## §10 Citations

**First-party — Temporal Python SDK (raw source, `sdk-python@main`, read 2026-08-03)**

- [S1] [README.md](https://raw.githubusercontent.com/temporalio/sdk-python/main/README.md) — sync vs async activities, `activity_executor`, `shared_state_manager`, heartbeat/cancellation contract, contextvars-in-threads requirement, shutdown-never-completes warning
- [S2] [temporalio/activity.py](https://raw.githubusercontent.com/temporalio/sdk-python/main/temporalio/activity.py) — `heartbeat`, `is_cancelled`, `wait_for_cancelled_sync`, `wait_for_worker_shutdown_sync`, `raise_complete_async`, `shield_thread_cancel_exception`, `no_thread_cancel_exception`
- [S3] [temporalio/worker/_worker.py](https://raw.githubusercontent.com/temporalio/sdk-python/main/temporalio/worker/_worker.py) — `activity_executor`, `max_concurrent_activities`, `max_activities_per_second`, `graceful_shutdown_timeout` (default `timedelta()`), `max_heartbeat_throttle_interval` (60 s), `default_heartbeat_throttle_interval` (30 s), default 100 slots, `run()` shutdown semantics
- [S4] [temporalio/worker/_activity.py](https://raw.githubusercontent.com/temporalio/sdk-python/main/temporalio/worker/_activity.py) — `_ThreadExceptionRaiser`, shield depth counter, multiprocess `cancelled_event`, `SharedStateManager` heartbeat queue, `notify_shutdown()`
- [S5] [temporalio/worker/_tuning.py](https://raw.githubusercontent.com/temporalio/sdk-python/main/temporalio/worker/_tuning.py) — `WorkerTuner`, `create_fixed` / `create_resource_based` / `create_composite`, `FixedSizeSlotSupplier`, `ResourceBasedSlotSupplier` defaults
- [S6] [temporalio/converter/_extstore.py](https://raw.githubusercontent.com/temporalio/sdk-python/main/temporalio/converter/_extstore.py) — `ExternalStorage`, `StorageDriver`, `StorageDriverClaim`, `payload_size_threshold: int = 256 * 1024`, "This API is experimental."
- [S7] [CHANGELOG.md](https://raw.githubusercontent.com/temporalio/sdk-python/main/CHANGELOG.md) — 1.31.0 breaking change: payload limits moved to `Client.connect(payload_limits=PayloadLimitsConfig(...))`
- [S8] [pyproject.toml](https://raw.githubusercontent.com/temporalio/sdk-python/main/pyproject.toml) — `version = "1.31.0"`, `requires-python = ">=3.10"`
- [S9] [GitHub Releases API — latest](https://api.github.com/repos/temporalio/sdk-python/releases/latest) — tag `1.31.0`, published 2026-07-29
- [S31] [temporalio/bridge/src/runtime.rs](https://raw.githubusercontent.com/temporalio/sdk-python/main/temporalio/bridge/src/runtime.rs) — `raise_in_thread` calls `pyo3::ffi::PyThreadState_SetAsyncExc`

**First-party — Temporal server (raw source, `temporal@main`, read 2026-08-03)**

- [S10] [common/dynamicconfig/constants.go](https://raw.githubusercontent.com/temporalio/temporal/main/common/dynamicconfig/constants.go) — all blob/history/mutable-state size and count limit defaults
- [S11] [common/rpc/grpc.go](https://raw.githubusercontent.com/temporalio/temporal/main/common/rpc/grpc.go) — `MaxHTTPAPIRequestBytes` "currently set to the max gRPC request size" (4 MB), `maxInternodeRecvPayloadSize` (128 MB)
- [S10b] [service/history/configs/config.go](https://raw.githubusercontent.com/temporalio/temporal/main/service/history/configs/config.go) — the history-service config struct that consumes those keys

**First-party — Temporal documentation (raw `.mdx` from `temporalio/documentation@main`)**

- [S12] [docs/develop/python/activities/standalone-activities.mdx](https://raw.githubusercontent.com/temporalio/documentation/main/docs/develop/python/activities/standalone-activities.mdx)
- [S13] [docs/develop/python/activities/timeouts.mdx](https://raw.githubusercontent.com/temporalio/documentation/main/docs/develop/python/activities/timeouts.mdx)
- [S14] [docs/develop/python/activities/basics.mdx](https://raw.githubusercontent.com/temporalio/documentation/main/docs/develop/python/activities/basics.mdx)
- [S16] [docs/develop/python/activities/asynchronous-activity.mdx](https://raw.githubusercontent.com/temporalio/documentation/main/docs/develop/python/activities/asynchronous-activity.mdx)
- [S17] [docs/encyclopedia/detecting-activity-failures.mdx](https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/detecting-activity-failures.mdx) — heartbeat throttling formula, all four timeouts, worker-crash detection
- [S18] [docs/encyclopedia/workers/worker-shutdown.mdx](https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workers/worker-shutdown.mdx)
- [S19] [docs/develop/worker-performance.mdx](https://raw.githubusercontent.com/temporalio/documentation/main/docs/develop/worker-performance.mdx) — task slots, tuners supersede `maxConcurrentXXX`, `worker_task_slots_available`
- [S20] [docs/develop/python/workers/run-process.mdx](https://raw.githubusercontent.com/temporalio/documentation/main/docs/develop/python/workers/run-process.mdx)
- [S21] [docs/troubleshooting/blob-size-limit-error.mdx](https://raw.githubusercontent.com/temporalio/documentation/main/docs/troubleshooting/blob-size-limit-error.mdx) — 2 MB payload / 4 MB gRPC, error strings, claim-check remedies
- [S23] [docs/production-deployment/self-hosted-guide/defaults.mdx](https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/self-hosted-guide/defaults.mdx) — **contradicts [S10] on the blob-size warn threshold (256 KB vs 512 KiB)**
- [S24] [docs/production-deployment/data-encryption.mdx](https://raw.githubusercontent.com/temporalio/documentation/main/docs/production-deployment/data-encryption.mdx) — payload codec, codec server, steer-to-External-Storage for oversized payloads

**First-party — Temporal samples (raw, `samples-python@main`)**

- [S15] [worker_specific_task_queues/README.md](https://raw.githubusercontent.com/temporalio/samples-python/main/worker_specific_task_queues/README.md) + [samples README index](https://raw.githubusercontent.com/temporalio/samples-python/main/README.md)
- [S25] [custom_decorator/activity_utils.py](https://raw.githubusercontent.com/temporalio/samples-python/main/custom_decorator/activity_utils.py) — `auto_heartbeater`, interval = `heartbeat_timeout/2`, async-only
- [S27] [external_storage/README.md](https://raw.githubusercontent.com/temporalio/samples-python/main/external_storage/README.md) — 256 KiB threshold, same-DataConverter-both-sides requirement

**First-party — other Temporal SDKs (raw source, for comparison)**

- [S22] [sdk-go activity/activity.go](https://raw.githubusercontent.com/temporalio/sdk-go/master/activity/activity.go) — `RecordHeartbeat` cancels the context, `GetWorkerStopChannel`
- [S34] [sdk-typescript packages/activity/src/index.ts](https://raw.githubusercontent.com/temporalio/sdk-typescript/main/packages/activity/src/index.ts) — `cancellationSignal` as `AbortSignal`, child-process abort, "Activities must heartbeat in order to receive Cancellation"

**First-party — rendered page (lower confidence per Research Standard §4)**

- [S28] [External Storage is now in Public Preview — temporal.io changelog](https://temporal.io/changelog/external-storage-public-preview) — announced 2026-05-14, Go + Python SDKs. Version/backend specifics NOT confirmed from raw source.

**Community — Temporal staff answers on the official forum (all claims sourced here are marked `unverified`; see §0 note)**

- [S26] [Best practices for long-running activities](https://community.temporal.io/t/best-practices-for-long-running-activities/934) — Maxim (Temporal): heartbeat timeout "relatively small … one minute", `StartToClose` = full expected duration, no hard guarantee against overlapping attempts
- [S38] [Long running activity with auto_heartbeater failing](https://community.temporal.io/t/long-running-activity-with-auto-heartbeater-failing/13586) — Chad Retz (Temporal): heartbeat-cancellation regression fixed in 1.7.1

**First-party — non-Temporal**

- [S29] [CPython Doc/library/asyncio-subprocess.rst](https://raw.githubusercontent.com/python/cpython/main/Doc/library/asyncio-subprocess.rst) — "Standard asyncio event loop supports running subprocesses from different threads by default"
- [S30] [CPython Doc/c-api/threads.rst](https://raw.githubusercontent.com/python/cpython/main/Doc/c-api/threads.rst) — `PyThreadState_SetAsyncExc` "does not necessarily interrupt system calls such as `time.sleep()`"
- [S32] [systemd man/systemd.kill.xml](https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.kill.xml) — `KillMode` "Defaults to control-group"; all remaining cgroup processes killed on unit stop

**Comparative engines**

- [S35] [restatedev/restate release-notes/v1.6.0.md](https://raw.githubusercontent.com/restatedev/restate/main/release-notes/v1.6.0.md) — RT0003 `MessageSizeLimit`, default 32 MiB journal-entry limit
- [S36] [Inngest usage limits](https://www.inngest.com/docs/usage-limits/inngest) — 2-hour step timeout, 4 MiB step output, 1000 steps/function *(rendered page — directional)*
- [S37] [dbos-inc/dbos-transact-py README.md](https://raw.githubusercontent.com/dbos-inc/dbos-transact-py/main/README.md) — step model, resume-from-last-completed-step
- [S33] [DataDog/temporal-large-payload-codec README.md](https://raw.githubusercontent.com/DataDog/temporal-large-payload-codec/main/README.md) — claim-check codec, Go-only, "please do not use in production"

**Sibling pool papers (not re-derived here)**

- [`durable_execution.md`](durable_execution.md) — durable-execution concepts, engine landscape, when durability is not needed
- [`claude_code_integration_surface.md`](claude_code_integration_surface.md) — CLI flags, exit codes, SIGTERM behaviour, session resumption scoping, idempotency hazards
- [`temporal.md`](temporal.md) — general Temporal capability paper; this paper closes its stated UNVERIFIED gap on heartbeat and payload limits
