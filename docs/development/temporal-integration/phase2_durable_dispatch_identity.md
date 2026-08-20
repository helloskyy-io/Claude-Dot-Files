# Phase 2 — Durable dispatch identity, and the recovery contract

**Status: ⬜ NOT STARTED.** Second in [rollout order](roadmap.md), and a hard prerequisite for wrapping anything.

An identity minted inside the thing that retries becomes a new identity on every attempt. Temporal's default activity retry policy has effectively unlimited attempts, so the failure mode is not one duplicate — it is an unbounded fan of them, each with its own log file and its own name for the same work.

**This lands before workers, not after them.** Retrofitting an identity contract onto running workers is a rewrite, which is why the sprint item says it *"lands with them rather than after"*.

---

## Requirements for completion

1. **No code path invents a dispatch identity inside an activity.** The logical id is computed by the **caller** from the work, is stable across every retry, resume and reconciliation, and is passed in.
2. **The six identity components exist as record fields**, each with an owner: logical id (caller), attempt id (system), uniqueness scope (design-time), request fingerprint (store), retention horizon (store), and the two conflict rulings (design-time).
3. **The per-subsystem recovery table is filled for every subsystem this fleet has**, on all six columns, including the rows whose values another component supplies.
4. **Re-dispatching the same logical id is demonstrated to reuse one identity** — same record, same bag — and a duplicate launch while one is live **fails loudly** rather than starting a second run against the same worktree. **This depends on [PMP Phase 9](../persistent-memory-protocol/phase9_one_run_one_identity.md) r7** — atomic create-if-not-exists on the bag is the mechanism a loud failure detects against, and it is not built here.
5. **Nothing Temporal replaces is built.** No claim/lease/TTL, no boot reconciler, no retry bookkeeping, no hand-rolled liveness probe. The negative is a deliverable: it is written down, with the reason.

---

## Dependencies

**Inside this component:** none. This phase needs no Temporal runtime and can proceed while [Phase 1](phase1_the_starter_control_plane.md) is blocked on a machine. It is independent of [Phase 3](phase3_the_retry_boundary.md) and the two could swap.

**Outside this component:** [PMP Phase 1](../persistent-memory-protocol/phase1_the_run_bag.md) — **satisfied.** The run bag is already keyed by `run_id`, and the identity record extends a store that exists rather than creating one.

**What this phase unblocks:** [Phase 4](phase4_the_claude_cli_activity.md)'s retry ruling folds into this contract, and [Phase 5](phase5_the_first_dispatch.md) cannot wrap anything until requirement 1 holds.

---

## What this phase rests on

[`raw/durable_dispatch_identity.md`](research/raw/durable_dispatch_identity.md) — `Last validated 2026-08-07`, Critic `PASS-WITH-FIXES`, and its content is unchanged by the 2026-08-19 cycle (only its `Feeds:` line was corrected, from a dissolved sprint section to this one). The specific sections: **§2.7** for the six components, **§4.1–§4.2** for the recovery table's columns and rows, **§5.2** for the trap, **§5.3** for the migration-safe shape, and **§5.4** for what gets thrown away.

**One thing in that paper is stale, and a build run planning from it alone will over-scope this phase.** See the next section — this is not a criticism of the paper, which was written 2026-08-07 against the tree as it then stood. **A second item over-scopes this phase the same way and is superseded rather than stale:** its §3.6 / §5.3 / §6 item 6 tier-1 store on `refs/dispatch/*`, costed there at *1–2 days* to build, is answered by the PMP run bag — see [`roadmap.md`](roadmap.md) § *What is deliberately not built*, which records the supersession and names what this phase still owes because of it. **§5.3 is in the reading list above and its tier-1 row reads `zero`, which is a port-time rewrite cost and not a build cost** — that column is the most persuasive argument for building the thing this ruling supersedes.

---

## §Runtime Verification

**Date:** 2026-08-19 · **Host:** `puma-workstation-mint` · **Runtime verified:** the Claude Code CLI's caller-supplied-identity surface, and the shipped state of the code this phase changes.

### The CLI accepts a caller-supplied session identity, and it must be a UUID

```
$ claude --version
2.1.235 (Claude Code)

$ claude --help | grep -A2 -- '--session-id'
  --session-id <uuid>                   Use a specific session ID for the
                                        conversation (must be a valid UUID)

$ claude --help | grep -E -- '--resume|--fork-session'
  --fork-session                        When resuming, create a new session ID
                                        with --resume or --continue)
  -r, --resume [value]                  Resume a conversation by session ID, or
```

**This is the fact the attempt-id design turns on.** `--session-id` takes a UUID the caller chooses, so the attempt id and the Claude Code session handle can be the same value and there is no need for a second identifier. `--fork-session` exists and does the opposite on purpose; nothing in this phase should reach for it.

### The paper's headline trap is HALF FIXED already — read this before scoping

`durable_dispatch_identity.md` §5.2(d) quotes `run_claude` as minting its identity inside the activity:

```python
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"{model_key}-{stamp}.jsonl"
```

**That is not what the tree says today.** Verified 2026-08-19 in `scripts/workflows/temporal/modules/assistant/assistant_activities.py`:

```
$ sed -n '466,470p' scripts/workflows/temporal/modules/assistant/assistant_activities.py
    log_dir = repo_root / ".claude" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = log_dir / f"{model_key}-{stamp}-{run_id}.jsonl"
    try:

$ sed -n '745,755p' scripts/workflows/temporal/modules/assistant/assistant_activities.py
    if log_file is not None and run_id is None:
        raise ValueError(
            f"run_claude was given a log_file ({log_file.name}) with no run_id. "
            ...
    if log_file is None:
        run_id = run_id or uuid.uuid4().hex
        log_file = claude_log_path(repo_root, model_key, run_id=run_id)
```

**`run_claude` already accepts a caller-supplied `run_id`, and the name is reserved atomically with `O_CREAT|O_EXCL`.** The half-supplied case raises rather than falling back. So the shipped code is considerably further along than the paper's quotation suggests, and **scoping this phase as "move identity generation out of the activity" from scratch would be re-doing work that landed.**

**Four things are still true, and they are this phase's actual scope:**

1. **`uuid.uuid4().hex` is a fallback *inside* the activity.** Under a Temporal retry with no caller-supplied id, every attempt mints a fresh one. The fix is not to move the line — it is to make the caller's supply mandatory at the activity boundary, so the fallback becomes unreachable rather than merely discouraged.
2. **`uuid4` is neither the logical id nor a good attempt id.** It is random, so it is not derived from the work (component #1 requires that) and it is not time-ordered (RFC 9562 recommends UUIDv7 *"instead of UUIDv1 and UUIDv6"*, and time-ordering is the one property today's wall-clock filenames actually buy).
3. **The log path still varies per attempt even under a stable `run_id`,** because `stamp` is re-taken on each call. A retry one second later produces a different filename for the same identity — components #1 and #2 conflated in a single string.
4. **A workflow function mints a UUID.** `scripts/workflows/temporal/modules/assistant/review_pr/review_pr_workflow.py:171` calls `uuid.uuid4().hex`. That is harmless today, because it is a plain Python function. **It is a determinism violation the moment it becomes workflow code** — Temporal replays workflow functions and a random value will not replay the same. It is listed in the checklist below rather than left for [Phase 5](phase5_the_first_dispatch.md) to discover.

**Re-verify before the build dispatch fires.** These are live source lines and line numbers drift; the *shapes* are what matter, and the build should re-read them rather than trusting the numbers above.

---

## The six components — what each is, and where it stands here

| # | Component | Owned by | State in this fleet |
|---|---|---|---|
| 1 | **Logical id** — deterministic from the work, stable across every retry | the **caller** | partially present — a `run_id` can be supplied, but it is random rather than derived, and supplying it is optional |
| 2 | **Attempt id** — unique per execution, never used for logic | the **system** | absent — the wall-clock stamp is doing both this job and #1's |
| 3 | **Uniqueness scope**, named | design-time | implicit: one repo's log directory on one machine |
| 4 | **Request fingerprint** — same key, different payload ⇒ **error** | the **store** | absent, and Temporal does not supply it |
| 5 | **Retention horizon**, bounded and stated | the **store** | unbounded in intent, unreliable in fact |
| 6 | **Two conflict rulings** — one for *closed*, one for *running* | design-time | absent |

**#6 is free and it is the one Temporal asks for by name on day one.** It is a written ruling, not code. The paper's recommended default, and the one this phase should adopt unless a build finds a reason not to: a **completed** dispatch is never silently re-run under the same id, and a duplicate launch while one is live **fails loudly**. The reasoning is that a PR is not replayable — a second `gh pr create` makes a second PR — and a worktree is a single-writer resource.

**#5 is the component that reaches across a phase boundary.** The horizon must be at least as long as the Claude Code transcript's 30-day default, or the record outlives the artifact it points at. [Phase 1](phase1_the_starter_control_plane.md) sets the namespace retention period and its **CLI default is 3 days** — so a namespace created without thinking about this phase silently breaks this phase's contract. That coupling is named in both docs on purpose.

---

## Implementation steps

- [ ] **Re-read § *Runtime Verification* against the tree** and refresh the line numbers before changing anything. Four of this phase's five requirements turn on what that section found.
- [ ] **Define the identity function** — the rule that computes the logical id from the task. It is the piece that carries forward unchanged: at the port it *becomes the Workflow Id verbatim*.
- [ ] **Make the caller's supply mandatory at the activity boundary**, so `uuid.uuid4().hex` is unreachable rather than discouraged. The existing half-supplied `ValueError` is the right shape and the right reasoning — extend it, do not replace it.
- [ ] **Separate #1 from #2 in the log path.** The stamp is currently doing both jobs; a stable identity must produce a stable path across attempts.
- [ ] **Mint the attempt id as a UUIDv7 and pass it to `claude --session-id`.** One value, two jobs: it sorts chronologically the way the current filenames do, and it satisfies the CLI's must-be-a-valid-UUID requirement without a second identifier.
- [ ] **Write down the uniqueness scope** as a record field — `(machine-id, repo)` today, becoming `(Namespace, Task Queue)` after the port. A field moves; nothing is rewritten.
- [ ] **Add the request fingerprint** — a hash over the task inputs, stored in the record, erroring when the same key arrives with a different payload. **Temporal does not supply this and never will**, so it is built once and carried across the port unchanged. **The mismatch error names the key and the two digests, never the two payloads.** A fingerprint is a digest and carries nothing, but the error raised on mismatch is exactly where a task input gets attached for diagnosability — and [Phase 4](phase4_the_claude_cli_activity.md) requirement 2 already rules that failure detail is one of the three payloads that must not reach event history. One rule, one writer: that one.
- [ ] **Rule how an atomic bag create tells a RETRY from a DUPLICATE LAUNCH, and write down which component decides.** `open_bag` already creates by winning or losing an `os.mkdir`, so the atomicity the superseded `refs/dispatch/*` store would have supplied is present — what is absent is the signal that distinguishes the two callers, because it adopts an open bag either way and refuses a sealed one. Requirement 4 needs one to adopt and the other to fail loudly, so the ruling turns on #2 and #4 rather than on the store. **This is what [`roadmap.md`](roadmap.md) § *What is deliberately not built* records as still owed after the tier-1 store was superseded.** Do not amend PMP's shipped `open_bag` from this phase — if the ruling needs a change there, surface it.
- [ ] **State the retention horizon in the record schema**, at least 30 days, and cross-check it against whatever [Phase 1](phase1_the_starter_control_plane.md) set on the namespace. If the two disagree, the *record* is not the thing to change.
- [ ] **Write the two conflict rulings**, one line each, with the reasoning. This is a document deliverable, not code.
- [ ] **Fill the per-subsystem recovery table** — see the next section for what belongs in it.
- [ ] **Fix `review_pr_workflow.py:171`** — a UUID minted in what becomes workflow code will not replay. Either it moves to the caller or it becomes a workflow-safe derivation; the ruling belongs here rather than in [Phase 5](phase5_the_first_dispatch.md), where it would be found by a failing replay.
- [ ] **Demonstrate requirement 4.** Re-dispatch the same logical id and show one record and one bag; launch a duplicate while one is live **concurrently rather than sequentially** — two launches racing for one logical id — and show one succeeding and one failing loudly. **A sequential second launch demonstrates the ruling and not the mechanism, and passes either way**, which is precisely the check `git update-ref` used to perform for free. Both go in the checklist as demonstrations, not as assertions in a summary.
- [ ] **Write the negative down.** Requirement 5 is satisfied by a paragraph naming what was deliberately not built and why — not by silence.
- [ ] **Test that a second attempt against the same logical id resolves to the same record**, and that a mismatched fingerprint raises rather than overwrites.

---

## The recovery table — the shape, and the three rows this phase does not fill

The table has six columns. Three come from the upstream pattern; three more are needed because this fleet's failure modes differ from a resident gateway's.

| Column | Why it is here |
|---|---|
| **Subsystem** | — |
| **What state exists** | — |
| **Where it is stored** | — |
| **Tier** — record or bulk | decides whether it crosses a machine. Absent, every row silently defaults to *machine-local*, which is today's bug |
| **Is the side effect replayable?** | this fleet's side effects include `git push` and `gh pr create`, and one of those is not |
| **What the operator sees** | the blocked-work notifier is this column's consumer; without it, the notifier re-derives per-subsystem semantics |

**Three rows read "nowhere yet," and they are exactly the three cheap guards** — credential expiry, false completion, safety-hook wiring. **This phase does not build them.** It gives each a row, so that whoever builds one is supplying a *value* to a schema that exists rather than designing a schema of its own. That is the concrete meaning of *designed once, not three times*.

**Where those guards live is an open operator ruling and it is not this phase's to make.** Their milestone was dropped when the Fleet Reliability sprint dissolved; the ratified `ship` decision behind them is tracked at [issue #125](https://github.com/helloskyy-io/Claude-Dot-Files/issues/125). The two papers that are their evidence sit in this component's pool and feed nothing here. **Nothing in this phase blocks on that ruling** — a row with an empty value is still a schema.

**One row is easy to miss and is the largest recoverability gap the current fleet has: *parent sequencing*.** Which child ran, what it concluded, how many loops have been spent — all of it exists only in a live process's memory. A parent that dies between children loses the knowledge that the earlier ones succeeded, and the only durable trace is log files named after a wall-clock time. This is a bigger hole than the turn cap, and it is the row most likely to be skipped because nothing is visibly broken today.

**That row has a named reader, and it is [Phase 5](phase5_the_first_dispatch.md) requirement 6.** Writing the parent as a workflow is what makes the state durable — Temporal's event history *is* the record this row asks for — so Phase 5 demonstrates a parent resuming between children and checks what it knows against what this row says should survive. **Stated here rather than left implicit**, because a recovery row with no reader is a schema nobody has tested, and this is the row where that would cost the most.

---

## Notes, decisions and gotchas

- **The migration cost of every one of these decisions is zero or near-zero, and that is the argument for doing them now.** The logical id becomes the Workflow Id verbatim; the fingerprint is unchanged because Temporal declines the job; the two rulings become constructor arguments; the scope is a field that moves. Nothing here is throwaway work that the port then replaces.
- **Do not build the thing the port deletes.** Anything that *schedules, leases, times, reclaims or reconciles* is Temporal's — claim tables and their TTLs, extension-on-live-PID, reclamation-on-dead-PID, boot-time orphan scans, retry bookkeeping, backoff, attempt counters, timers, cron, and any hand-rolled "is this worker alive" probe. The three-legged liveness taxonomy — stalled, looping, stranded — is worth *recording as a design input* to the `claude_cli` activity in [Phase 4](phase4_the_claude_cli_activity.md); it is not worth implementing.
- **`--fork-session` is the wrong tool and its name will tempt someone.** It exists to create a *new* session id when resuming. This phase's entire premise is that a retry keeps the same identity.
- **The attempt id must never be keyed on for logic.** That is not a style preference — it is the same warning Temporal gives about its own Run Id, and the reason component #2 exists as a separate row rather than being folded into #1.
- **`ALLOW_DUPLICATE_FAILED_ONLY` + a fail-loud conflict policy is a default, not a law.** The paper's own note: `USE_EXISTING` is attractive for an idempotent re-dispatch and should be revisited *once a parent can attach to a running dispatch*, which it cannot today. Record the ruling with that revisit condition attached, so the next reader knows what would change it.
