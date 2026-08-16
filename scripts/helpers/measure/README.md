# `scripts/helpers/measure/`

Replay tools that read the fleet's own archived artifacts and produce a number.

**Why these are here and not deleted as one-shots.** Each answers a question whose
answer is a *rate over a growing denominator*, and re-deriving the method costs more
than re-running the tool. A measurement taken once over 51 logs is not the same claim
as the same measurement over 500, and the open decisions these feed say so explicitly.

Nothing here is on any merge path, nothing here writes, and nothing here reads
anything but `.claude/logs/` and `gh` output. They are read-only over local artifacts.

| Tool | Answers | Read by |
|---|---|---|
| `replay_completion_predicate.py` | How often does the fleet's completion grep miss a real terminal outcome? | Open direction row `D-007` (`docs/standards/architecture/research/direction.md`); Memory Management Framework [Phase 1](../../../docs/development/memory-management-framework/phase1_measure_the_channel.md) E5 |
| `replay_pr_review_blocks.py` | How often is the finding-set delta between consecutive `review-pr` passes empty, and does the stable-id convention hold? | Memory Management Framework [Phase 1](../../../docs/development/memory-management-framework/phase1_measure_the_channel.md) E7; [Phase 5](../../../docs/development/memory-management-framework/phase5_convergence_stopping.md) |
| `replay_convergence_predicate.py` | Over the whole archive, how often would the shipped convergence predicate have fired, how often *early*, and does it reproduce the model-asserted `converged` flag? | Memory Management Framework [Phase 5](../../../docs/development/memory-management-framework/phase5_convergence_stopping.md) § Measurement and § What would let this gate |
| `replay_run_resources.py` | What fraction of runs could not be measured and why; how `peak_anon` distributes by workflow; whether footprint tracks subagent COUNT or content VOLUME; and what concurrent runs sum to | Memory Management Framework [Phase 6](../../../docs/development/memory-management-framework/phase6_read_what_it_writes.md) requirement 3, and requirement 4's retraction re-check |
| `replay_convergence_events.py` | What the LIVE predicate actually said — including the `pass_not_evaluable` and `history_unreadable` rates the GitHub archive structurally cannot produce — and **Phase 5's gate conditions 1 and 2 with their denominators** | Candidate **C-059**; [Phase 5](../../../docs/development/memory-management-framework/phase5_convergence_stopping.md) § What would let this gate; [Phase 6](../../../docs/development/memory-management-framework/phase6_read_what_it_writes.md) § Phase 5's un-owned activation |
| `judge_marginal_yield.py` | Whether the separate review pass finds anything the producing run had not already disclosed — each disposition finding classified ECHOED or NEW against the run's own reflection bullets, with the denominator and the lexical-matching bias stated | [`sprint.md`](../../../docs/development/sprint.md) § *Continuous Process Improvement*, *measure the judge's marginal yield*; the 2026-08-14 deferral asking whether four review layers earn their cost |
| `replay_parent_route.py` | How often the parent ABSTAINS and for which reason, and how often the prose shadow agrees with the typed record — with the denominator's own conditioning stated | [Phase 3](../../../docs/development/memory-management-framework/phase3_typed_exit_record.md) step 4's computed arm; [Phase 4](../../../docs/development/memory-management-framework/phase4_fleet_migration.md)'s shadow-removal box; candidate **C-060** |

**The last three read the RUN LOG, which is a surface with a name as of Phase 6.**
`run_log.py` beside them is not a replay tool — it is the one declaration of what
that surface holds (`MEMBER_EVENT_TYPES`), what joins it (`JOIN_KEY`), what may be
published from it, and where each figure's denominator starts (`CUTOVERS`). A
fourth parent-written event type is added there, and a test fails if the declared
set and the `_append_run_event` call sites disagree in either direction. The prose
home is the `memory-model.md` amendment drafted as candidate 10 of the framework
roadmap, which is the operator's to ratify.

**A `Read by` column with nothing in it is this directory's own finding, one level
up.** A tool nobody reads is the thing Phase 6 exists to stop; a tool whose row
cannot name a consumer is the same defect wearing a table.

**Two of these treat the rule they replay in OPPOSITE ways, and the difference is a
rule rather than an inconsistency.** `replay_completion_predicate.py` **pins a copy** of
the predicate it measures, because it reports the historical miss rate of an
**incumbent** gate and a live import would silently re-measure a changed rule against
the same archived logs. `replay_convergence_predicate.py` **imports the shipped
predicate**, because it validates a **candidate** before anything is allowed to gate on
it and a pinned copy would certify a rule nobody runs. **The discriminator: pin when
the number must stay reproducible, import when the rule must be the one that ships.**

**Sample-size discipline is not optional here.** Every count these emit carries its
denominator, and every excluded artifact is named as excluded rather than quietly
dropped from a denominator. The exclusions are the part a reader cannot reconstruct.

**PUBLISH CLASSIFICATION — binding on every tool here that reads the run log.**
Two of the run log's three event types share a file with the CLI's own transcript,
so this surface is co-resident with prompt text, tool inputs and tool results, and
these tools route their output into committed docs and PR comments. **Readers emit
derived figures, `run_id`s and log file names — never a value whose text
originates in the CLI transcript, model output or tool input.** The live hazard is
`convergence`, whose payload carries lists of model-authored finding slugs that
read exactly like identifiers; readers emit their LENGTHS.
`run_log.assert_publishable` enforces it on the row about to be printed, by
comparing emitted VALUES against what arrived in a non-publishable payload field —
a key-name allowlist would just be an inventory of each reader's own output. The
control one surface over is `exit_record._redact()`, which drops `tool_input` for
the same reason.

**And a denominator that grows is one that goes stale.** Phase 1 E7's headline figure —
*"the open set reaches zero exactly once … the only `MERGE` and the only
`converged: true` in the archive"* — was **false one day after it was measured**: there
are now two of each. Re-run before quoting; do not carry a number forward.
