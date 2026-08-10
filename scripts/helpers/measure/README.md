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

**And a denominator that grows is one that goes stale.** Phase 1 E7's headline figure —
*"the open set reaches zero exactly once … the only `MERGE` and the only
`converged: true` in the archive"* — was **false one day after it was measured**: there
are now two of each. Re-run before quoting; do not carry a number forward.
