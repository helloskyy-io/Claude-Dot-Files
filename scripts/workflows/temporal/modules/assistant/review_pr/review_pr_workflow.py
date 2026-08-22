"""The review-pr disposition engine — Layer 1 orchestration.

DECIDE-ONLY. It merges nothing, closes nothing, fixes nothing, dispatches
nothing. Its output is one disposition comment plus a terminal VERDICT line —
plus the single write authority it holds: filing GitHub Issues for qualifying
deferred work. That exception exists because it is the only actor with no scope
of its own to offload; everything else stays decide-only.

    gather → render → dispose → verdict

Every decision below comes from the helper; every side effect is an activity.

STATED DEVIATION, so the sentence above is not read as either aspirational
or as a bug. FIVE pure `ExitRecord`/assessment-to-string functions remain in
this layer: three from Phase 3 and `_convergence_notes` / `_convergence_event`
from Phase 5. They were left here deliberately — with ONE parent the
misplacement costs only that a few otherwise-pure tests run through a
monkeypatch harness — and `phase4_fleet_migration.md` step 2 is the trigger
that extracts them, on the moment a SECOND parent routes on a record. It names
the count so that extracting three and leaving two is not available.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from .. import assistant_activities as _shared
from .. import convergence
from . import exit_record
from .. import routing
from . import review_pr_activities as act
from . import review_pr_helper as helper
from .review_pr_helper import ReviewInput, ReviewResult, ReviewType

_HERE = Path(__file__).resolve().parent
_BASH_FLEET = _HERE.parents[3]

# Single-consumer prompt: stays in this workflow's folder per §10.1 rule 3.
PROMPTS = _HERE / "prompts"
PROMPT_PATH = PROMPTS / "disposition.md"

# The prompt is ASSEMBLED, not branched. Core + universal addenda + exactly one
# type-criteria file. This is what the port bought: a mode is a different file,
# not an `if` inside a 43KB string. Adding a fourth type means adding one file.
CORE_ADDENDA = ["core_corpus_rule.md"]

# Shared fragment: several workflows use it, so it promotes to a parent level
# once the second consumer ports. Read from the bash original until then.
SHARED_PROMPTS = _BASH_FLEET / "common" / "shared-prompts.sh"


def assemble_prompt(review_type: ReviewType) -> str:
    """Core + universal addenda + exactly ONE type-criteria file.

    Both the real path and --dry-run call this. An earlier version rendered only
    the core in the dry run, so every type produced an identical byte count and
    the dry run could not have detected a broken assembly — the same shape as the
    bug where a render-only check missed a path resolved at invocation time.
    """
    criteria = PROMPTS / f"criteria_{review_type.value}.md"
    if not criteria.exists():
        raise FileNotFoundError(
            f"no criteria file for --type {review_type.value}: {criteria}. "
            f"A review type without criteria would silently apply another type's."
        )
    return "\n\n".join(
        [act.load_prompt(PROMPT_PATH)]
        + [act.load_prompt(PROMPTS / a) for a in CORE_ADDENDA]
        + [act.load_prompt(criteria)]
    )


def _append_shadow_pair(log_file, *, run_id: str, pr: str, expected_ref) -> None:
    """Write the `parent_route` row comparing the typed channel against the prose one.

    CALLED ON BOTH PATHS, AND THE FAILURE PATH IS THE POINT (`C-45bhs5cm`).

    THE DEFECT THIS CLOSES. `run-claude.sh` returns non-zero when the model's
    final result does not match `COMPLETION_PATTERN` — a PR URL, which the PROSE
    channel prints. `run_claude` turns that into a `RuntimeError` before
    returning, so this parent's recording code never ran, and `channels_agree`
    could only ever be written on runs where the prose channel ALREADY
    SUCCEEDED. The metric was conditioned on the very channel it exists to
    retire, so every run where the typed record OUTPERFORMED prose was
    structurally invisible and the number could only ever look like agreement.
    More runs do not fix a biased instrument.

    MEASURED: Phase 3's run set was nine live dispatches and the instrument
    recorded eight. The ninth emitted a valid typed record and no prose
    `VERDICT:` line — the single most informative run in the set, and the one
    that went unrecorded.

    THE PRECEDENT IS TEN LINES AWAY IN `assistant_activities.run_claude`, which
    calls `append_run_resources` BEFORE its failure branch and says why: "A run
    that died is the one whose resource numbers are most worth having, and an
    early `raise` would throw them away at exactly the moment they became
    evidence." One member event of the run log learned that; this one had not.

    THE EVIDENCE WAS ALREADY ON DISK. Both channels read from `log_file`, which
    the activity writes DURING the run — so this was a missing code path, never
    missing instrumentation.

    BEST EFFORT, AND IT NEVER MASKS THE ORIGINAL FAILURE. On the failure path
    the log may be truncated or hold no result event at all. Recording is worth
    attempting and is never worth converting a run's real error into a
    different one, so anything raised in here is swallowed — the caller's
    `raise` is what the operator must see.
    """
    try:
        record = exit_record.route(
            _shared.result_event(log_file), expected_run_id=run_id,
            expected_ref=expected_ref,
        )
        verdict = helper.verdict_from_record(record)
        shadow, parseable = helper.parse_verdict(_shared.assistant_text(log_file))
        _shared.append_parent_route(log_file, {
            "run_id": run_id,
            "pr": pr,
            "routed_outcome": record.routed_outcome.value,
            "undetermined_reason": (
                record.undetermined_reason.value if record.undetermined_reason else None
            ),
            "hold_kind": record.hold_kind.value if record.hold_kind else None,
            "shadow_verdict": shadow.value,
            "shadow_parseable": parseable,
            "channels_agree": shadow is verdict,
        })
    except Exception:
        # The pair is evidence, not a gate. A log too damaged to read one from
        # is a missing row, never a second failure stacked on the first.
        pass


def run_review(task: ReviewInput, worktree: Path) -> ReviewResult:
    """Disposition one PR and return its typed verdict."""
    notes: list[str] = []

    pr = act.fetch_pr(task.pr_number, worktree)
    this_pass, prior_pass = helper.pass_numbers(
        act.count_prior_passes(task.pr_number, worktree)
    )

    # R5b'S RIGHT-HAND SIDE IS BUILT HERE, BEFORE THE CHILD RUNS, AND THE
    # ORDERING IS THE POINT. `repo_slug` is a `gh` round trip, on the path whose
    # named failure mode is rate limiting (`thread_snapshot`'s docstring). Built
    # here, a `gh` failure costs a dispatch that has produced nothing. Built
    # after the child — where the first version of this put it — an unretried
    # network call sits between a completed ~40-minute review and the
    # `parent_route` event that records it, so a transient 5xx destroys the
    # review, the durable event and the parent's loop. That is precisely the
    # loss `_thread_unreadable_note` was written to prevent, and nothing in
    # `expected_ref` depends on anything the child produces.
    expected_ref = helper.expected_completion_ref(
        task.pr_number, _shared.repo_slug(worktree))

    # CAP (binding): exactly two things vary by type — the scope boundary and
    # the blocking-defect checklist — and both live in the criteria file. Type
    # MUST NOT be consulted anywhere else in this workflow. Without that cap the
    # fourth type gets added by copy-pasting a branch, which reproduces the
    # 398-diverged-lines problem inside one file where it is harder to see.
    assembled = assemble_prompt(task.review_type)
    notes.append(f"Reviewed as --type {task.review_type.value}.")

    # RUN IDENTITY IS ISSUED BY THE PARENT, not derived from anything the child
    # can see. It goes into the prompt and must come back in the typed record;
    # rule R5 compares them. Freshness by path allocation (below) and identity
    # in the payload are two independent checks, and the second is the one that
    # catches a record arriving on a CORRECT path from a DIFFERENT invocation.
    run_id = uuid.uuid4().hex

    prompt = helper.render_prompt(
        assembled,
        pr_number=task.pr_number,
        pr_branch=pr["headRefName"],
        this_pass=this_pass,
        prior_pass=prior_pass,
        headless_guard=act.load_shared_block("HEADLESS_EXECUTION_GUARD", SHARED_PROMPTS),
        run_id=run_id,
    )

    # The reviewer must read the PR's branch, not the repo's checkout.
    pr_tree = _shared.worktree_add(
        worktree, f"review-pr-{task.pr_number}-{int(time.time())}",
        f"origin/{pr['headRefName']}",
    )
    # THE NONCE BINDS THE LOG'S NAME, not just the record inside it — this
    # workflow is the concurrent-dispatch case `claude_log_path`'s docstring
    # describes, so passing the run_id is what makes the name unique here and
    # makes the filename greppable against the record it carries.
    log_file = _shared.claude_log_path(worktree, helper.MODEL_KEY, run_id=run_id)
    # WRAPPED SO THE PAIR IS RECORDED ON BOTH OUTCOMES (`C-45bhs5cm`). The
    # completion gate fires on the PROSE channel's PR URL, so a prose failure
    # killed this parent before it could record that the TYPED channel had
    # succeeded. The gate itself is unchanged and still fails the run — exit 0
    # must mean done, and buying a datapoint by weakening that would trade a
    # real guarantee for a number.
    try:
        act.run_disposition(
            prompt, worktree, helper.MODEL_KEY, helper.COMPLETION_PATTERN,
            worktree=pr_tree, verbose=task.verbose,
            exit_record_schema=exit_record.schema_argument(), log_file=log_file,
            # The SAME nonce that named the log and that the child echoes into
            # the record, so all three of the run log's member events agree on
            # it. `run_claude` refuses a log_file with no run_id for that reason.
            run_id=run_id,
        )
    except Exception:
        _append_shadow_pair(log_file, run_id=run_id, pr=task.pr_number,
                            expected_ref=expected_ref)
        raise

    # --- THE TYPED CHANNEL DECIDES --------------------------------------
    # TWO IDENTITIES ARE CHECKED, NOT ONE. `run_id` says the record came from
    # the invocation this parent issued (R5); `expected_ref` (built above,
    # before the child ran) says the record is ABOUT the PR this parent
    # dispatched against (R5b). `routing.PR_URL` owns the threat argument for
    # the second; it is not restated here.
    #
    # THE BRANCH HALF IS CLOSED BY CONSTRUCTION HERE AND IS NOT RE-CHECKED. The
    # review worktree above is created from `origin/{pr['headRefName']}`, where
    # `pr` came from `act.fetch_pr(task.pr_number, …)` BEFORE the child ran — so
    # the child reviews the head branch of the PR this parent named and has no
    # way to choose another. Re-asserting it after the fact would compare the
    # parent's own value against itself.
    record = exit_record.route(
        _shared.result_event(log_file), expected_run_id=run_id,
        expected_ref=expected_ref,
    )
    verdict = helper.verdict_from_record(record)

    # --- THE PROSE CHANNEL IS A SHADOW ----------------------------------
    # Still emitted, still parsed, and it decides nothing. Read from the
    # assistant text blocks rather than from the console or `.result`: declaring
    # a schema replaces `.result` with the serialised structured output, so a
    # shadow read from there would report a disagreement that is an artifact of
    # where it looked.
    #
    # PARSED BEFORE THE STRATUM IS WRITTEN so the stratum can carry it. The
    # COMPARISON still happens after; only the parse moved.
    shadow, parseable = helper.parse_verdict(_shared.assistant_text(log_file))

    # Persist the parent stratum BEFORE the shadow COMPARISON, because a
    # disagreement raises and a machinery failure that leaves no trace is the
    # one Phase 4 most needs counted. Step 4's computed-arm predicate reads
    # `routed_outcome`/`undetermined_reason`; nothing else writes them durably.
    #
    # THE SHADOW'S OWN RESULT IS PART OF THE STRATUM, and leaving it out made
    # requirement 6 unmeasurable. That requirement is *"both paths asserted to
    # agree across a run set"* — a per-run PAIR. Recording only the typed half
    # leaves a corpus of N events that ALL describe agreements, because the
    # disagreements raise and never reach a log; the pair could then only be
    # reconstructed by a second offline reader of the prose channel, which is
    # the duplicated-parser defect this whole component exists to remove.
    #
    # `shadow_parseable` is recorded separately from `shadow_verdict` because
    # `parse_verdict` fails safe: an unparseable channel and one that genuinely
    # said `HOLD - needs-assistance` yield the same token, and
    # `verdict_from_record` collapses all seven `UndeterminedReason` values onto
    # that same token from the other side. Without the flag, those two defaults
    # colliding is indistinguishable from a real agreement — and the E2(c) cell
    # (record absent on an otherwise-clean run, prose saying needs-assistance)
    # is the single case this phase most needs counted as a DISAGREEMENT.
    # RE-READS THE LOG RATHER THAN TAKING THE VALUES ABOVE, DELIBERATELY. The
    # failure path has no `record` to hand — that is the whole point of the
    # wrap — so the helper must derive its own. Passing pre-parsed values here
    # and re-parsing there would give the two paths different code, and the
    # path that runs rarely is the one that would drift. Identical code on both
    # is worth one extra read of a local file that is already in page cache.
    _append_shadow_pair(log_file, run_id=run_id, pr=task.pr_number,
                        expected_ref=expected_ref)

    # BUILT BEFORE THE RAISE, NOT AFTER IT, AND THAT ORDERING IS A FIX RATHER
    # THAN A STYLE. R5b routes to `undetermined`, which collapses to
    # `HOLD - needs-assistance`; the case R5b exists for is a child that
    # attached its review to a foreign record AND printed `VERDICT: MERGE`, and
    # on that case the shadow disagrees and this function raises. Building the
    # note only in the notes block below made it unreachable in exactly the
    # scenario it was written for — the operator got the generic
    # "could not be evaluated" line and never the two references. So the note is
    # built once here and consumed by BOTH arms.
    ref_note = helper.completion_ref_mismatch_note(record, expected_ref)

    if shadow is not verdict:
        # A LOUD NOTE FOR A BENIGN DIVERGENCE; STILL A RAISE WHEN THERE IS NO
        # SECOND OPINION AT ALL. Ruled by the operator 2026-08-11 and NARROWED
        # here, deliberately, because the ruling's evidence does not reach the
        # whole path.
        #
        # WHAT WAS MEASURED: 2 firings in 8 runs, BOTH `permission_denied`, and
        # in both the two channels agreed about the review. Those destroyed a
        # completed review that had already produced a correct verdict — a 25%
        # false-termination rate on a check whose evidence (`channels_agree`) is
        # durable in the log BEFORE it fires. Conflating *make it visible* with
        # *stop everything* let a monitor destroy the thing it monitors. Prior
        # art is GitHub's `Scientist`: run both, return the control's result,
        # publish the mismatch, never throw.
        #
        # WHAT WAS NOT MEASURED, AND MUST STILL STOP: `record_absent`,
        # `record_stale`, `record_unparseable`, `envelope_unreadable` and
        # `schema_version_unknown` all route to UNDETERMINED too — and in those
        # the typed channel produced NO OPINION. That is a MISSING CHANNEL, not
        # a disagreement: there is nothing to diverge from, so continuing would
        # accept a confident prose MERGE on a single unverified channel. A
        # blanket demotion would have silently converted the dangerous shape
        # into a warning, which is the opposite of what the ruling was for.
        BENIGN_DIVERGENCE = {
            exit_record.UndeterminedReason.PERMISSION_DENIED,
            exit_record.UndeterminedReason.DENIALS_UNREADABLE,
        }
        no_second_opinion = (
            record.routed_outcome is exit_record.RoutedOutcome.UNDETERMINED
            and record.undetermined_reason not in BENIGN_DIVERGENCE
        )
        detail = (
            f"the typed record routes {verdict.value!r} "
            f"(routed_outcome={record.routed_outcome.value}"
            + (f"/{record.undetermined_reason.value}" if record.undetermined_reason else "")
            + f") while the prose channel parsed {shadow.value!r} (parseable={parseable})"
        )

        if no_second_opinion:
            raise RuntimeError(
                f"exit-record UNUSABLE on PR #{task.pr_number}: {detail}. "
                f"The typed channel produced no opinion, so this is a MISSING "
                f"CHANNEL rather than a divergence — continuing would accept the "
                f"prose verdict with nothing to check it against. Log: {log_file}"
                + (f"\n\n{ref_note}" if ref_note else "")
            )

        print(
            f"\n{'!' * 72}\n"
            f"!! CHANNEL DIVERGENCE on PR #{task.pr_number} — RECORDED, NOT FATAL\n"
            f"!! {detail}\n"
            f"!! The TYPED record DECIDES and the run continues on it — `verdict_from_record`\n"
            f"!! at :155 is what this function returns. The prose parse is the SHADOW.\n"
            f"!! channels_agree=false is in the run log. Log: {log_file}\n"
            + (f"!! {ref_note}\n" if ref_note else "")
            + f"{'!' * 72}\n",
            flush=True,
        )

    # "Agreed" is claimed only when the shadow actually produced a verdict.
    # `parse_verdict` fails safe to the same token the typed channel falls back
    # to, so an unparseable prose channel reaching here is two defaults matching,
    # not two channels agreeing — and an operator reading "agreed" would count it
    # as evidence for the very property this phase exists to measure.
    notes.append(
        f"Routed on the typed exit record: routed_outcome={record.routed_outcome.value}"
        + (f", reason={record.undetermined_reason.value}" if record.undetermined_reason else "")
        + (f". Prose shadow agreed ({shadow.value})." if parseable else
           f". Prose shadow produced NO parseable verdict; its fail-safe default "
           f"({shadow.value}) coincides with the typed route, which is not agreement.")
    )
    if record.routed_outcome is exit_record.RoutedOutcome.UNDETERMINED:
        notes.append(
            f"The typed record could not be evaluated ({record.undetermined_reason.value}) "
            f"on PR #{task.pr_number}. This is the COMPUTED abstention arm — a defect in "
            f"the machinery, not a question about the work. Inspect by hand: {log_file}"
        )
        # R5b's reason is the one an operator cannot act on from the generic line
        # above — see `helper.completion_ref_mismatch_note`. `extend` on a list
        # that is empty when the rule did not fire, for the same reason
        # `_convergence_notes` returns one: no conditional in this function may
        # read a routing signal it does not own. Same `ref_note` object the
        # raise above interpolates, so the two arms cannot describe the same
        # rule differently.
        notes.extend(n for n in [ref_note] if n is not None)
    if record.permission_denials:
        notes.append(
            f"{len(record.permission_denials)} permission denial(s) recorded: "
            + ", ".join(sorted({d['tool_name'] for d in record.permission_denials}))
            + ". Never auto-redispatched — a child that tripped the only in-run safety "
              "control is not retried against it."
        )

    # --- ONE THREAD READ, TWO CONSUMERS ----------------------------------
    # The render↔record invariant needs this pass's block and the block count;
    # Phase 5's convergence predicate needs the whole window. Reading them
    # together keeps them ONE OBSERVATION — the skew a split read invites is the
    # same one `_read_thread_for_invariant` retries as a unit to avoid.
    #
    # Both are skipped on an UNDETERMINED route, and for the same reason: there
    # are no ids to compare and no pass to assess. Convergence still gets an
    # assessment — the residual arm, named `pass_not_evaluable` — because the
    # predicate is total and a pass that did not route is not evidence.
    evaluable = record.routed_outcome is not exit_record.RoutedOutcome.UNDETERMINED
    blocks: list[str] | None = None
    if evaluable:
        try:
            posted, blocks = _read_thread_for_invariant(task.pr_number, worktree)
        except RuntimeError as exc:
            # COULD-NOT-CHECK IS NOT DISAGREEMENT, and reporting it as one sends
            # the operator to the wrong place. `gh` failing here (rate limit,
            # transient 5xx, no network) says nothing about the two copies.
            notes.append(_thread_unreadable_note(task.pr_number, record, log_file, exc))
        else:
            # Co-authoring persists for the three prose regions that have no
            # field (`memory-model.md` §7.2 rows 3, 4 and 11), so the durable
            # block and the typed record are written in one act by one author —
            # the arrangement none of the surveyed instances permits WITHOUT a
            # write-time gate. This is that gate. THE TYPED REGION WINS; the
            # block is its rendering.
            _assert_block_matches_record(
                task.pr_number, record, prior_pass, posted, blocks, run_id
            )
            # THE DEGRADATION IS REPORTED, because a selection that fell back to
            # position looks exactly like one that matched on the nonce. The
            # `parent_route` payload is FROZEN while this phase's run set is
            # being read (`append_parent_route`'s own docstring), and a new
            # durable event type here would be a producer with no consumer —
            # the admission failure Phase 6 exists to stop. So this reaches the
            # operator and nothing else, and that limit is stated rather than
            # discovered. Built in the helper and `extend`ed unconditionally,
            # like its two siblings — this function does not branch on a signal
            # it does not own, and an inline `if` here would be a sixth pure
            # record-to-string site the docstring's count does not name.
            notes.extend(
                n for n in
                [helper.positional_fallback_note(task.pr_number, blocks, run_id)]
                if n is not None
            )

    # --- THE COMPUTED CONVERGENCE SIGNAL — RECORDED, NOT ROUTED ON --------
    # `routing.MAX_LOOPS` remains the only stopping authority. This phase emits
    # the signal, shadows it against the incumbent model-asserted `converged`
    # flag, and gates nothing: the archive contains two confirming observations
    # of the predicate firing, which falsifies "it never fires" and is nowhere
    # near a rate. Replacing the bound is a measurement decision and the
    # measurement does not support it yet.
    #
    # THE PASS'S OWN BLOCK IS DROPPED FROM THE HISTORY. It is this pass, already
    # supplied by the typed record, and `_assert_block_matches_record` has just
    # proven the two carry identical `(id, disposition)` pairs. Leaving it in
    # would put one pass in twice and make every id look restated.
    #
    # THE TWO FAILURE REASONS ARE NOT FOLDED TOGETHER. A pass that did not route
    # is `pass_not_evaluable`; a pass that routed while the thread read was
    # exhausted is `history_unreadable`. Collapsing them would report a `gh`
    # rate limit as a degraded review, and the computed arm's whole instrument
    # is the state GROUPED BY its reason — the same defect this component
    # recorded at R2 and again at R1a.
    this_block = helper.this_pass_block(blocks, run_id) if blocks is not None else None
    assessment = convergence.assess(
        helper.convergence_history(blocks, record, run_id) if blocks is not None else (),
        pass_evaluable=evaluable,
    )
    asserted = (helper.asserted_converged_in_block(this_block)
                if this_block is not None else None)
    agrees = helper.shadow_agreement(assessment, asserted)
    _shared.append_convergence(log_file, _convergence_event(
        run_id=run_id, pr_number=task.pr_number, assessment=assessment,
        asserted=asserted, agrees=agrees,
    ))
    # `extend`, not an `if`: the routing function must contain NO conditional
    # that reads the convergence signal, and `test_nothing_in_the_tree_routes_on
    # _the_convergence_signal` enforces exactly that on `run_review`. The
    # rationing decision belongs to the note builder, which cannot route.
    notes.extend(_convergence_notes(assessment, asserted, agrees))

    return ReviewResult(
        pr_number=task.pr_number, verdict=verdict, this_pass=this_pass,
        parseable=parseable, notes=notes, record=record, convergence=assessment,
    )


# The run-log convergence event's keys that are NOT derived from the assessment.
# `run_id` and `pr` are the join keys `append_convergence`'s docstring names as
# the reason this is a separate event type at all; the other two carry the
# incumbent's claim and the shadow verdict.
CONVERGENCE_ENVELOPE_KEYS = frozenset(
    {"run_id", "pr", "asserted_converged", "agrees"}
)


def _convergence_event(*, run_id: str, pr_number: str,
                       assessment: convergence.ConvergenceAssessment,
                       asserted: bool | None, agrees: bool | None) -> dict:
    """The `{"type": "convergence"}` payload — envelope keys plus the assessment.

    THE MERGE IS GUARDED BECAUSE THE DERIVATION THAT MAKES IT SAFE IS ALSO WHAT
    MAKES IT COLLIDE. `as_event()` is derived from `dataclasses.fields`
    specifically so that adding a field to `ConvergenceAssessment` for a later
    gating decision lands durably with no call-site edit — and that is exactly
    what lets a future field named `run_id` or `pr` reach this splat with nobody
    in the loop. The two failure directions are both silent and both destroy the
    corpus this phase exists to accumulate:

    - a field named `run_id` or `pr` OVERWRITES the join key, so the event can no
      longer be joined to its `parent_route` row;
    - a field named `asserted_converged` or `agrees` is silently DROPPED by the
      two literal keys below it, so the shadow the phase is measured on records
      the wrong value.

    Neither is reachable while the assertion holds, and the assertion names the
    collision rather than letting the dict resolve it. This is the same property
    `_append_run_event` now enforces for `type`, one layer up: a payload that can
    set an envelope key can make itself unreadable.
    """
    payload = assessment.as_event()
    collisions = CONVERGENCE_ENVELOPE_KEYS & set(payload)
    if collisions:
        raise ValueError(
            f"ConvergenceAssessment now carries {sorted(collisions)}, which the "
            f"convergence run-log event already uses for its envelope. One of the "
            f"two would be silently lost — the join key or the shadow. Rename the "
            f"new field, or rule on which meaning the key carries and update "
            f"CONVERGENCE_ENVELOPE_KEYS with the reason."
        )
    return {
        "run_id": run_id,
        "pr": pr_number,
        # DERIVED from the assessment, never retyped here — a field added to
        # `ConvergenceAssessment` for a later gating decision must not be able to
        # land in the return value and in nothing durable.
        **payload,
        # The INCUMBENT's claim, carried verbatim beside the computed one in the
        # `outcome`/`routed_outcome` shape — the raw observation is never
        # overwritten. `None` means the block carried no `converged:` key, which
        # is distinct from `false` and must stay distinct or an agreement rate
        # counts pre-flag blocks as disagreements.
        "asserted_converged": asserted,
        "agrees": agrees,
    }


def _convergence_notes(assessment: convergence.ConvergenceAssessment,
                       asserted: bool | None, agrees: bool | None) -> list[str]:
    """The operator-facing line, or NO line when this assessment says nothing.

    Returns a list rather than an optional string so the caller can `extend`
    unconditionally — `run_review` routes, and the restraint guard holds it to
    containing no conditional that reads this signal at all.

    An operator seeing `converged` in a run's notes will reasonably assume
    something acted on it. Nothing does, so the note says so in its own words
    rather than leaving the reader to infer it from the absence of an effect.

    EMITTED ONLY WHEN THERE IS SOMETHING TO READ, and the RUN-LOG EVENT is
    unconditional regardless — the denominator lives there, not here. Every
    dispatch used to print this line, and the archive's most common shape by far
    is pass 1 (12 of 25 blocks), whose line reads *"indeterminate
    (no_prior_pass) over 1 pass(es); 0 open"* and carries no information. Burying
    the four cases that DO carry information — a fire, a stall, a converged
    assessment with escalations outstanding elsewhere, and a divergence from the
    incumbent flag — in a line that prints every time is how the first real one
    gets skimmed past. This phase's headline is *0 divergences*; the mechanism
    that would report the first one has to be readable.
    """
    informative = (assessment.state is convergence.ConvergenceState.CONVERGED
                   or assessment.stalled or assessment.escalated_open
                   or assessment.unknown_dispositions or agrees is False)
    if not informative:
        return []

    line = f"Computed convergence: {assessment.state.value}"
    if assessment.reason is not None:
        line += f" ({assessment.reason.value})"
    line += f" over {assessment.passes} pass(es); {len(assessment.open_ids)} open"
    if assessment.stalled:
        line += " — STALLED: nothing opened and nothing closed since the prior pass"
    if assessment.escalated_open:
        line += (f"; {len(assessment.escalated_open)} escalated finding(s) counted "
                 f"CLOSED for this loop and outstanding elsewhere: "
                 + ", ".join(assessment.escalated_open))
    if assessment.unknown_dispositions:
        line += ("; unrecognised disposition(s) counted OPEN: "
                 + ", ".join(assessment.unknown_dispositions))
    if agrees is False:
        # NOT called a disagreement, because the two rules answer different
        # questions and a difference is a definitional one at least as often as
        # it is a defect. `helper.shadow_agreement` carries the argument; the
        # word here has to match it or an operator goes looking for a bug.
        line += (f". It DIFFERS from the incumbent flag: the block asserts "
                 f"converged={str(asserted).lower()}. The two answer different "
                 f"questions — the flag is a single-pass severity heuristic "
                 f"(are this pass's findings all preventive?), the computation "
                 f"is set emptiness across passes (is anything still open?) — so "
                 f"record this, do not act on it")
    line += (". THIS SIGNAL ROUTES NOTHING — the loop-back bound "
             f"(MAX_LOOPS={routing.MAX_LOOPS}) is still the only stopping authority.")
    return [line]


# A BOUNDED RETRY, not a poll and not a policy. The read below is `gh pr view
# --json comments` — READ-ONLY and idempotent — so re-issuing it is not a
# routing decision and changes neither the success path nor the terminal
# behaviour on a persistent failure. Two attempts of backoff cover the shape
# that actually occurs here (a 5xx, a secondary rate limit, a dropped
# connection) without turning a genuinely-down API into a long stall.
_THREAD_READ_BACKOFF_SECONDS = (2.0, 8.0)


def _read_thread_for_invariant(pr_number: str, repo_root: Path) -> tuple[int, list[str]]:
    """The thread observation the invariant and the predicate share, retried once.

    IT RETURNS THE WHOLE BLOCK WINDOW, not just the latest one, because two
    consumers read this observation: the invariant compares the LAST block
    against the typed record, and Phase 5's convergence predicate needs every
    prior pass — a pairwise comparison cannot see an oscillating finding set by
    construction.

    ONE `gh` READ, NOT A RETRY AROUND TWO. This used to call
    `count_prior_passes` and `pr_review_blocks` in sequence, and retrying the
    pair together covers a FAILURE while doing nothing about SKEW: a count read
    taken before this pass's comment lands, paired with a window read taken
    after it, is exactly the mismatch the `posted > prior_pass` delta exists to
    detect, and it would kill a completed review that did nothing wrong.
    `act.thread_snapshot` derives both from a single reply, which is the only
    thing that closes it — and it drops a round trip from the path whose named
    failure mode is rate limiting.

    `RuntimeError` IS THE WHOLE FAILURE SURFACE, and that is a property of
    `assistant_activities.gh_json` rather than an assumption made here. For one
    pass it was an assumption and it was wrong: the readers below parsed `gh`
    stdout themselves, so a zero-exit reply with a truncated or non-JSON body
    raised `json.JSONDecodeError` — a `ValueError`, caught by nothing on this
    path — and skipped this retry entirely, at zero attempts, to crash the parent
    build loop. Catching `ValueError` here would have closed one caller and left
    the next `gh` reader to re-acquire the gap, so the normalisation lives at the
    call that knows what it can emit. Widen THAT if a third failure shape appears.
    """
    for pause in _THREAD_READ_BACKOFF_SECONDS:
        try:
            return act.thread_snapshot(pr_number, repo_root)
        except RuntimeError:
            time.sleep(pause)
    # The last attempt is deliberately OUTSIDE the loop and NOT caught, so a
    # persistent failure raises the real `gh` error with its real message rather
    # than a swallowed one.
    return act.thread_snapshot(pr_number, repo_root)


def _thread_unreadable_note(pr_number: str, record: exit_record.ExitRecord,
                            log_file: Path, exc: Exception) -> str:
    """The could-not-check note, when the thread read is exhausted.

    A VERIFICATION THAT COULD NOT RUN MUST NOT DESTROY A DECISION THAT ALREADY
    DID. This point is reached AFTER the child posted its disposition comment
    and AFTER `append_parent_route` persisted the route, so for one pass a 5xx,
    a rate limit or a dropped connection on a READ discarded a ~40-minute review
    at real budget and killed the parent's build loop with it — for a reason
    with nothing to do with the review. The reads are retried; on exhaustion the
    check is REPORTED as unperformed and the run completes, because the route is
    already durable and the evidence survives either way.

    REPORTED, NOT RECORDED, AND THE DIFFERENCE IS DELIBERATE HERE. The note goes
    into `ReviewResult.notes` — printed by `run_review_pr` and folded into the
    parent's notes by `build_workflow` — which reaches an operator watching the
    run and NOTHING ELSE. Every other computed-arm signal (`routed_outcome`,
    `undetermined_reason`, `channels_agree`) is written to the run log by
    `append_parent_route` and is therefore countable offline; this one is not, so
    no replay can say how often the invariant degraded. That is a real gap and it
    is named rather than papered over: making it durable means a new stratum in
    `exit-protocol.md` §2, and WHAT a parent should do about a verification it
    could not perform — annotate, record, or downgrade — is one unruled question,
    carried as candidate **C-rrm2t4sj**.

    IT IS A SEPARATE FUNCTION FROM THE INVARIANT ITSELF, and that split is what
    let the invariant be renamed honestly. It used to be one `_verify_` function
    with three outcomes — raise, note, nothing — where an `_assert_` prefix would
    have promised only two and invited a later call site to drop the note. With
    the read hoisted to the caller (Phase 5 needs the same observation), the
    third outcome moved out with it and the invariant has exactly the two its
    new name claims. Phase 4 adds the call sites; the name has to be right
    before they arrive.

    The note is deliberately loud for the reader it does reach: an invariant that
    silently did not run is indistinguishable from one that held, and the whole
    reason this is enforced rather than documented is that both copies diverging
    is silent. THE ROUTING POLICY IS UNTOUCHED.
    """
    return (
        f"PR #{pr_number}: the render↔record invariant was NOT CHECKED — "
        f"reading the thread failed after "
        f"{len(_THREAD_READ_BACKOFF_SECONDS) + 1} attempts: {exc}. This is not "
        f"a disagreement between the two copies; it is the check itself not "
        f"running, and it says NOTHING about whether they agree. The typed "
        f"record routed {record.routed_outcome.value}, is intact in the run "
        f"log and was persisted before this check ran, so the verdict stands "
        f"on the record rather than on this. VERIFY THE POSTED BLOCK BY HAND "
        f"against the record's findings before acting on it. Convergence is "
        f"INDETERMINATE for the same reason — no history was read. Log: {log_file}"
    )


def _assert_block_matches_record(pr_number: str,
                                 record: exit_record.ExitRecord,
                                 prior_pass: int, posted: int,
                                 blocks: list[str], run_id: str) -> None:
    """Fail loud when the durable render and the typed record disagree on findings.

    RAISES OR RETURNS. The could-not-check third outcome lives in
    `_thread_unreadable_note` above, at the caller, which is why this is
    `_assert_` and its predecessor was `_verify_`.

    ONE AUTHOR, TWO DERIVED COPIES — and the copies are checked rather than
    trusted. A finding in the record but not in the block is a finding the
    operator never sees; a finding in the block but not in the record is one
    Phase 5's stopping predicate will never count. Both are silent today, which
    is why this is enforced rather than documented.

    THE BLOCK MUST BE *THIS PASS'S*, AND THAT CHECK IS THE FIRST ONE. Reading
    "the latest block on the thread" is not the same as reading the block this
    run posted: `disposition.md`'s INVARIANT 1 requires a pass to carry every
    prior finding forward, so identical id sets across passes is the NORM. A
    pass ≥2 that produced a record and then failed to post its comment would
    therefore be compared against pass 1's block, match, and report the
    invariant satisfied — silently passing in exactly the case it exists to
    catch. The block count is re-read here (fence-anchored, one declaration) and
    must have risen by one. Sequence comes from that count, never from the
    block's own `pass:` counter, which `memory-model.md` §6.4 measured wrong.

    AND PHASE 5 NOW DEPENDS ON THAT GUARANTEE RATHER THAN MERELY BENEFITING
    FROM IT. `helper.convergence_history` builds the convergence predicate's
    most recent term from the TYPED record and every earlier term from the
    durable blocks; the two sources are only interchangeable because this
    invariant makes this pass's block and this pass's record carry identical
    `(id, disposition)` pairs. A weakening here would not fail a convergence
    test — it would silently make yesterday's prose term disagree with what
    today's typed term was compared against.
    """
    # THROUGH THE ACCESSOR, NOT AN INLINE SLICE. `phase4_fleet_migration.md`'s
    # run-nonce checkbox names `helper.this_pass_block` as THE single site where
    # "which block is this pass's" is inferred. This function re-derived it
    # inline, so that checkbox would have hardened the shadow and the history and
    # left the render↔record invariant — the check `convergence_history`'s hybrid
    # design depends on — still selecting by position, silently disagreeing with
    # its two siblings. Since Phase 4 that accessor matches on the RUN NONCE
    # where the thread carries it, so this check and the convergence history are
    # both addressed by identity or both by position — never one of each.
    block = helper.this_pass_block(blocks, run_id)
    if posted <= prior_pass:
        raise RuntimeError(
            f"PR #{pr_number}: the run produced a typed exit record but posted no new "
            f"`pr_review:` block — the thread still carries {posted} block(s), the "
            f"same count as before this pass. The durable half of the record is "
            f"missing, so the operator has the outcome with none of its reasoning — "
            f"which is the one thing arrangement A must not lose. The latest block on "
            f"the thread belongs to an earlier pass and is NOT this run's rendering."
        )
    if block is None:
        raise RuntimeError(
            f"PR #{pr_number}: the run produced a typed exit record but no "
            f"`pr_review:` block was found on the thread. The durable half of the "
            f"record is missing, so the operator has the outcome with none of its "
            f"reasoning — which is the one thing arrangement A must not lose."
        )
    # Ids AND dispositions, because that is what the prompt promises the child.
    # `findings[].disposition` is what Phase 5's stopping predicate keys on, so
    # an id-only comparison lets the two copies diverge in the one field a
    # convergence rule reads.
    rendered = helper.finding_dispositions_in_block(block)
    typed = {(f["id"], f["disposition"]) for f in record.findings}
    if rendered != typed:
        raise RuntimeError(
            f"PR #{pr_number}: the posted `pr_review:` block and the typed exit "
            f"record disagree on findings (id, disposition). Only in the block: "
            f"{sorted(rendered - typed) or 'none'}. Only in the record: "
            f"{sorted(typed - rendered) or 'none'}. The typed region is "
            f"authoritative; the block is its rendering, and a rendering that "
            f"drops, invents or re-dispositions a finding is not one."
        )
