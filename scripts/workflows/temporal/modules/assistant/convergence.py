"""The COMPUTED convergence signal — Phase 5's stopping predicate.

THE ONE DECLARATION, like its siblings `routing.py` and `exit_record.py`.
`exit-protocol.md` §6 requires a record's schema and its address to be declared
once and loaded; this module is that declaration for the convergence
vocabulary — the open/closed partition over `disposition`, the state vocabulary,
and the ordered rules that produce one.

WHAT THIS ANSWERS, AND WHAT IT DOES NOT. It answers *"is there anything left for
another pass of THIS review loop to do?"*. It does NOT answer *"is this work
finished?"* and it does not authorise a merge — that stays with the child's
`outcome` and the parent's `routed_outcome` (`exit_record.py`). Conflating the
two is how a stopping rule turns into a merge rule nobody ruled on.

IT GATES NOTHING TODAY, DELIBERATELY. `routing.MAX_LOOPS` remains the only
stopping authority. This module computes, records and shadows the incumbent
model-asserted `converged` flag; whether it may ever replace the bound is a
measurement question and the archive currently contains **two** confirming
observations of the predicate firing (see `phase5_convergence_stopping.md`
§ Measurement). Two is enough to falsify "it never fires" and nowhere near
enough to be a rate.

THE READER AND THE WRITER ARE THE SAME ACTOR, AND THAT IS THE HAZARD THIS
MODULE IS BUILT AROUND. `review-pr` writes `findings[].disposition`; this
predicate reads it. If the reviewer were biased toward closing findings, the
predicate would silently agree — there is no check in code that separates a
truthfully-`fixed` finding from a falsely-`fixed` one, because such a check IS
a second review. Three things bound the damage and each is a rule below:
`prior_findings_dropped` (convergence by forgetting is detectable),
`oscillating_findings` (convergence by churn is detectable), and the fact that
nothing routes on the output. The residual — an honest-looking pass that closes
what is not closed — is UNMITIGATED and is recorded as such rather than
papered over.

DEPENDENCY-FREE ON PURPOSE. Stdlib only, no sibling imports, no I/O, no clock.
That is what lets the replay tool load it BY PATH and validate the shipped
predicate rather than a copy of it, and it is the same posture `routing.py`
holds for the same class of reason.

IDENTITY IS THE ID SLUG AND NOTHING ELSE. Phase 1 E7 measured that a persisting
finding reuses its slug verbatim (25 of 25 added ids adjudicated, and re-checked
at 0 of 12 pairs dropping an id) while its TITLE is not stable — PR #45 carries
one id across two passes with a completely rewritten title, because pass 2
restates it as fixed. So this compares ids and deliberately ignores titles,
bodies, categories, ordering, and the block's own `pass:` integer (measured
wrong on the most recently reviewed PR in the repo, issue #68). Sequence comes
from the order the passes are handed in, never from that integer.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "CLOSED_DISPOSITIONS", "OPEN_DISPOSITIONS", "ESCALATED",
    "ConvergenceState", "IndeterminateReason",
    "ConvergenceAssessment", "open_ids", "assess",
]


# `escalated` IS COUNTED CLOSED, AND THIS IS THE PHASE'S ONE UNFORCED RULING.
#
# Phase 1 E7 handed it here explicitly: it counted `escalated` as open, said the
# corpus did not constrain the choice (2 of 195 findings, none inside a measured
# pair, every figure identical either way), and required Phase 5 to rule rather
# than inherit. THE CORPUS THAT SETTLES IT NOW EXISTS — 13 of 300 findings, and
# they sit inside multi-pass blocks on two PRs.
#
# The measurement that decides it, PR #67: `standup-md-self-contradiction` and
# `sprint-mmf-entry-stale` are escalated at pass 1 and STILL escalated,
# unchanged, at pass 4. An escalated finding has been moved to another
# authority; this reviewer cannot close it on any future pass, by definition.
# Counting it open therefore makes the predicate STRUCTURALLY UNABLE TO FIRE on
# any PR that ever escalates anything — the exact never-fires failure mode E7's
# re-scoping to the open subset existed to escape, re-entering through a
# different door.
#
# It is the same rule `routing.should_loop_back` already applies one level up:
# a `needs-assistance` verdict never loops at any count, because more passes
# cannot produce a human ruling. An escalation is that sentence per-finding.
#
# WHAT IT COSTS, PAID IN THE OPEN: convergence can now be reported while work is
# genuinely outstanding somewhere else. That is why `escalated_open` is carried
# on every assessment — the ids are recorded, so a later gating decision reads
# the number rather than rediscovering the trade.
ESCALATED = "escalated"

CLOSED_DISPOSITIONS = frozenset({"fixed", "deferred", "rejected", "noted", ESCALATED})

# `hold` is the only disposition that leaves work for THIS loop. Spelled as its
# own frozenset rather than derived, so the completeness gate in
# `test_convergence.py` can assert the two partition `CHILD_SCHEMA`'s enum
# exactly — a seventh disposition added to the schema fails that gate until
# somebody classifies it, instead of silently landing in whichever half the code
# happens to default to.
OPEN_DISPOSITIONS = frozenset({"hold"})


class ConvergenceState(str, Enum):
    """What the PARENT computed about the loop. Never written by a child.

    INDETERMINATE is the computed *could-not-check* arm, reused in SHAPE from
    `exit_record.RoutedOutcome.UNDETERMINED` — same split, same fail-safe
    direction: the residual arm is a named state that gets recorded, never a
    silent fall-through.

    ITS SPELLING IS DELIBERATELY DIFFERENT FROM THAT ARM'S, and the difference
    was forced by the one-declaration gate rather than chosen for taste. Both
    values land in the SAME run log — `parent_route.routed_outcome` and
    `convergence.state`, joined on `run_id` — so one token meaning "the router
    could not evaluate this record" and "the predicate could not evaluate this
    loop" would put two different facts in one grep. That is the shared-bin
    measurement failure `UndeterminedReason.DENIALS_UNREADABLE` exists to
    prevent, one artifact over.
    """

    CONVERGED = "converged"
    NOT_CONVERGED = "not_converged"
    INDETERMINATE = "indeterminate"


class IndeterminateReason(str, Enum):
    """Why convergence could not be computed. Required iff INDETERMINATE.

    A SEPARATE ENUM FROM `exit_record.UndeterminedReason`, and the separation is
    forced rather than stylistic. That enum is the output vocabulary of
    `exit-protocol.md` §4's ordered rules, and a test parses §4's reason column
    out of the markdown and asserts it is EXACTLY that enum's members — so a
    member no §4 rule emits fails the protocol gate. These reasons are emitted
    by no §4 rule; they belong to a different contract with a different input.
    """

    # The pass itself is not trustworthy evidence — its typed record did not
    # route. A degraded, truncated or turn-capped pass emits an empty or partial
    # finding set that is indistinguishable from a clean one unless the
    # predicate first requires proof the pass completed.
    PASS_NOT_EVALUABLE = "pass_not_evaluable"
    # The prior passes could not be read at all (the thread read failed). Not a
    # statement about the loop; a statement about the reader.
    HISTORY_UNREADABLE = "history_unreadable"
    # Pass 1. There is no prior pass to compare against, and an absent
    # comparison routes to the residual arm — NEVER to converged.
    NO_PRIOR_PASS = "no_prior_pass"
    # This pass does not restate every id the prior pass carried.
    # `disposition.md` INVARIANT 1 requires it to, so a shrinking id set means
    # the pass is not conforming and its emptiness proves nothing. This is the
    # check that separates real convergence from CONVERGENCE BY FORGETTING.
    PRIOR_FINDINGS_DROPPED = "prior_findings_dropped"
    # Some finding in this PR's history was closed and later re-opened. A set
    # that has churned once may be churning now, and a pairwise comparison
    # cannot see it — this is the window check, and it is why the history is
    # passed in whole rather than as two passes.
    OSCILLATING_FINDINGS = "oscillating_findings"


@dataclass(frozen=True)
class ConvergenceAssessment:
    """One computed assessment — the state, its evidence, and its denominators.

    Everything a later gating decision would need is carried here rather than
    recomputed: `phase3_typed_exit_record.md` step 4's lesson is that a metric
    defined over a field nothing writes is a plan, not an instrument.
    """

    state: ConvergenceState
    reason: IndeterminateReason | None = None
    passes: int = 0
    open_ids: tuple[str, ...] = ()
    opened: tuple[str, ...] = ()
    closed: tuple[str, ...] = ()
    escalated_open: tuple[str, ...] = ()
    unknown_dispositions: tuple[str, ...] = ()
    # The all-ids delta. Emitted as TELEMETRY and as the window check's input,
    # never as the stopping condition: the `pr_review:` block is cumulative, so
    # this set cannot shrink and its delta was empty 0 of 12 archived pairs —
    # a property of the reporting shape, not of the fleet.
    added_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """`reason` is required IFF the state is INDETERMINATE.

        Enforced at construction in `exit_record.ExitRecord.__post_init__`'s
        shape, for its reason: the residual arm is a named state that is
        RECORDED, and an indeterminate assessment carrying no reason records
        nothing while looking like it does.
        """
        indeterminate = self.state is ConvergenceState.INDETERMINATE
        if indeterminate and self.reason is None:
            raise ValueError(
                "an indeterminate convergence assessment must name its reason: the "
                "residual arm is a named state that is RECORDED, never a silent "
                "fall-through"
            )
        if not indeterminate and self.reason is not None:
            raise ValueError(
                f"state={self.state.value} carries reason={self.reason.value}; a "
                f"reason belongs only to the computed could-not-check arm"
            )

    @property
    def stalled(self) -> bool:
        """Open, unchanged, and nothing closed — the #58 pass 2→3 shape.

        THE MEASURED REASON THE STOPPING CONDITION IS EMPTINESS AND NOT
        STABILITY. At PR #58 pass 2→3 the open set held at 2 with nothing added
        and nothing closed; a rule reading *"the open set stopped changing"*
        stops there and is WRONG. A stalled loop routes to the bound in
        `routing.MAX_LOOPS`, never to convergence — which is what this property
        is for: it names the state so an operator can see it, and it changes no
        route.
        """
        return (self.state is ConvergenceState.NOT_CONVERGED
                and not self.opened and not self.closed and bool(self.open_ids))


def _as_map(entries: Iterable[tuple[str, str]]) -> dict[str, str]:
    """One pass's `(id, disposition)` pairs as a mapping. Last spelling wins.

    A duplicate id within one block is malformed, not a modelled state; taking
    the last is the same last-wins rule `latest_pr_review_block` applies one
    level up, and it keeps the function total on input the archive can produce.
    """
    return {str(fid): str(disposition) for fid, disposition in entries}


def open_ids(entries: Iterable[tuple[str, str]]) -> frozenset[str]:
    """The ids still carrying work for THIS loop, from one pass.

    UNKNOWN COUNTS AS OPEN, and the asymmetry is deliberate. A disposition this
    vocabulary does not recognise is a finding whose state nobody established,
    and the two errors are not equal: treating it as closed can EMPTY the open
    set and report convergence never observed, while treating it as open can
    only spend a pass the bound already limits. Every archived finding carries a
    known disposition today (300 of 300), so this changes no current number — it
    bounds what a future re-run can silently conclude.
    """
    return frozenset(
        fid for fid, disposition in _as_map(entries).items()
        if disposition not in CLOSED_DISPOSITIONS
    )


def _ever_reopened(passes: Sequence[dict[str, str]]) -> frozenset[str]:
    """Ids closed in some pass and open again in a later one.

    THE WINDOW, AND THE REASON IT IS THE WHOLE HISTORY RATHER THAN A FIXED N.
    A two-pass comparison cannot see a cycle by construction, and any fixed
    window is a number nobody measured. The whole history is the only bound the
    corpus justifies, and it is cheap — the largest archived PR carries four
    blocks.
    """
    reopened: set[str] = set()
    for i, later in enumerate(passes):
        later_open = {fid for fid, d in later.items() if d not in CLOSED_DISPOSITIONS}
        for earlier in passes[:i]:
            earlier_closed = {
                fid for fid, d in earlier.items() if d in CLOSED_DISPOSITIONS
            }
            reopened |= earlier_closed & later_open
    return frozenset(reopened)


def assess(history: Sequence[Iterable[tuple[str, str]]], *,
           pass_evaluable: bool) -> ConvergenceAssessment:
    """The stopping predicate. Ordered rules, first match wins, C6 is the default.

    TOTAL. Every input reaches a named state, including inputs nobody
    anticipated — the shape borrowed from `exit_record.route`, which borrowed it
    from Kubernetes `podFailurePolicy`. Routing on values the model did not
    author is mature and boring outside the agent corpus; so is having an answer
    for the unmatched case.

    `history` is this PR's passes OLDEST FIRST, each an iterable of
    `(finding id, disposition)` pairs, with the pass under assessment LAST.
    Consecutiveness comes from this ordering and never from the block's `pass:`
    integer, which `memory-model.md` §6.4 measured wrong on the most recently
    reviewed PR in the repo.

    `pass_evaluable` is the caller's evidence that the pass under assessment
    actually completed — in the live path, that its typed exit record routed to
    something other than `undetermined`. It is a REQUIRED keyword with no
    default, so a new call site cannot acquire the degraded-pass hole by
    forgetting it.

    THE STOPPING CONDITION IS THE OPEN SET BEING EMPTY, NOT UNCHANGED. Both
    halves are measured over the archive (`phase5_convergence_stopping.md`
    § Measurement) and the difference is not academic: over 12 consecutive-pass
    pairs an "unchanged" rule fires 3 times and is wrong once, while an "empty"
    rule fires twice and is wrong never.
    """
    # C0 — the pass is not evidence. A degraded, truncated or turn-capped pass
    # emits nothing, and nothing looks exactly like a clean pass with no open
    # findings. The fleet's measured turn-cap rate is 0.9% (4/443): rare, real,
    # and silent, which is the combination that needs a rule rather than a note.
    if not pass_evaluable:
        return ConvergenceAssessment(
            ConvergenceState.INDETERMINATE,
            IndeterminateReason.PASS_NOT_EVALUABLE,
        )

    passes = [_as_map(entries) for entries in history]

    # C1 — nothing to read. Distinct from C2 on purpose: "the thread could not be
    # read" and "this is pass 1" are different diagnoses with different remedies,
    # and the computed arm's instrument is the state GROUPED BY reason.
    if not passes:
        return ConvergenceAssessment(
            ConvergenceState.INDETERMINATE,
            IndeterminateReason.HISTORY_UNREADABLE,
        )

    current = passes[-1]
    current_open = open_ids(current.items())
    unknown = tuple(sorted(
        d for d in set(current.values())
        if d not in CLOSED_DISPOSITIONS and d not in OPEN_DISPOSITIONS
    ))
    escalated = tuple(sorted(
        fid for fid, d in current.items() if d == ESCALATED
    ))

    # C2 — no comparable prior pass. Requirement 5 of the phase doc states this
    # as its own rule: absence of a prior pass routes to the residual arm and
    # NEVER to converged. A pass-1 review that closed everything it found has
    # demonstrated nothing about a loop it has not yet looped.
    if len(passes) < 2:
        return ConvergenceAssessment(
            ConvergenceState.INDETERMINATE,
            IndeterminateReason.NO_PRIOR_PASS,
            passes=len(passes), open_ids=tuple(sorted(current_open)),
            escalated_open=escalated, unknown_dispositions=unknown,
        )

    prior = passes[-2]
    added = tuple(sorted(set(current) - set(prior)))

    # C3 — CONVERGENCE BY FORGETTING. `disposition.md` INVARIANT 1 requires each
    # pass to carry every prior finding forward until it reaches an explicit
    # disposition, and the archive does exactly that: 0 of 12 pairs drop an id.
    # A pass that drops one is not conforming, so its open set is not comparable
    # to the prior one and its emptiness proves nothing. Measured never to have
    # happened — which is the point: this guards the failure that has no natural
    # alarm, not one already occurring.
    #
    # THE COMPARISON IS AGAINST EVERY PRIOR PASS, NOT THE ADJACENT ONE, and the
    # difference is the whole guard. A pairwise check catches a drop for exactly
    # ONE pass: `{a: hold, b: hold}` → `{a: fixed}` → `{a: fixed}` flags pass 2
    # and then reports pass 3 CONVERGED with `b` never dispositioned — so the
    # cheapest way to fake convergence, stop mentioning a finding and keep not
    # mentioning it, walks straight through. That is the same reason
    # `_ever_reopened` scans the whole history rather than a fixed window: any
    # window shorter than the history is a number nobody measured. Number-neutral
    # on the archive — an adjacent-superset chain implies an all-prior superset,
    # and 0 of 12 pairs drop an id, so no replayed figure moves.
    dropped = set().union(*(set(p) for p in passes[:-1])) - set(current)
    if dropped:
        return ConvergenceAssessment(
            ConvergenceState.INDETERMINATE,
            IndeterminateReason.PRIOR_FINDINGS_DROPPED,
            passes=len(passes), open_ids=tuple(sorted(current_open)),
            escalated_open=escalated, unknown_dispositions=unknown,
            added_ids=added,
        )

    prior_open = open_ids(prior.items())

    # C4 — still open. NOT converged, and `stalled` names the sub-case where
    # nothing moved in either direction. This rule sits BEFORE the oscillation
    # check because a non-empty open set is already a complete answer: churn
    # cannot make "there is outstanding work" wrong.
    if current_open:
        return ConvergenceAssessment(
            ConvergenceState.NOT_CONVERGED,
            passes=len(passes), open_ids=tuple(sorted(current_open)),
            opened=tuple(sorted(current_open - prior_open)),
            closed=tuple(sorted(prior_open - current_open)),
            escalated_open=escalated, unknown_dispositions=unknown,
            added_ids=added,
        )

    # C5 — the open set is empty, but this PR has churned before. A finding
    # closed in one pass and re-opened in a later one means at least one closure
    # on this thread did not hold, and nothing here can tell whether the current
    # closures are the durable kind. DELIBERATELY CONSERVATIVE — one reopening
    # anywhere in the history withholds convergence for the rest of the PR —
    # and affordable because the fail-safe direction costs at most the passes
    # `routing.MAX_LOOPS` already bounds. Measured at 0 occurrences across 12
    # archived pairs, so this rule has never fired on real data and is here
    # because the mode is documented, not because it is observed.
    reopened = _ever_reopened(passes)
    if reopened:
        return ConvergenceAssessment(
            ConvergenceState.INDETERMINATE,
            IndeterminateReason.OSCILLATING_FINDINGS,
            passes=len(passes), open_ids=(),
            closed=tuple(sorted(prior_open)),
            escalated_open=escalated, unknown_dispositions=unknown,
            added_ids=added,
        )

    # C6 — the default, and the only path to CONVERGED. Nothing is open, the
    # pass is evidence, it restated everything it inherited, and nothing on this
    # thread has ever been re-opened.
    return ConvergenceAssessment(
        ConvergenceState.CONVERGED,
        passes=len(passes), open_ids=(),
        closed=tuple(sorted(prior_open)),
        escalated_open=escalated, unknown_dispositions=unknown,
        added_ids=added,
    )
