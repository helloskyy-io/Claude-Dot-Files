"""Pure compiler for the review-pr workflow — Layer 2.

BINDING: no I/O. No subprocess, no network, no filesystem read at call time, no
clock. Every function is a deterministic map from inputs to a value.

Input models live here rather than in a separate `review_pr_inputs.py`, per
temporal_standard.md §11.2: models live in the helper by default and extract
only when the helper grows unwieldy. Presence or absence is not a conformance
signal.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from .. import convergence, exit_record, routing


Verdict = routing.Verdict


# THE KIND 1 ADDRESS, DECLARED ONCE for this tree. `exit-protocol.md` §6 covers
# the record's schema AND its address, because the measured duplication was in
# the address: three incompatible declarations of this marker, two of them
# unanchored, writing a wrong durable `pass:` onto 2 of 8 archived PRs (issue
# #68). Fence-anchored so a comment that merely MENTIONS the key — a reflection,
# a summary, a brief quoting the wire format — is not counted as a record.
#
# Kept shape-identical to `scripts/helpers/measure/replay_pr_review_blocks.py`'s
# FENCE, which is the one declaration that was already correct; that module is a
# measurement tool outside the workflow tree and importing across that boundary
# would couple a helper to the fleet it measures.
PR_REVIEW_BLOCK = re.compile(r"```ya?ml\s*\n(pr_review:.*?)\n```", re.DOTALL)


class ReviewType(str, Enum):
    """What KIND of artifact is under review.

    Explicit, never inferred — same doctrine run-claude.sh enforces for
    --model: identity is an input, not something derived from context. Commit 2
    adds the type-specific criteria; commit 1 defines the axis and defaults to
    BUILD so behaviour is unchanged.
    """

    BUILD = "build"
    RESEARCH = "research"
    PLANNING = "planning"


@dataclass(frozen=True)
class ReviewInput:
    pr_number: str
    repo_target: str | None = None
    verbose: bool = False
    review_type: ReviewType = ReviewType.BUILD

    def __post_init__(self) -> None:
        # Fail loud at the boundary: a non-numeric PR number reaches `gh` as a
        # confusing error several layers down.
        if not str(self.pr_number).isdigit():
            raise ValueError(f"--pr must be a number, got {self.pr_number!r}")


@dataclass
class ReviewResult:
    pr_number: str
    verdict: Verdict
    this_pass: int
    parseable: bool = True
    notes: list[str] = field(default_factory=list)
    # The typed exit record this verdict was routed FROM. Optional because a
    # caller may still run the prose-only path; None means the typed channel was
    # not in play, never that it was in play and empty — that state is an
    # ExitRecord with routed_outcome UNDETERMINED.
    record: exit_record.ExitRecord | None = None
    # Phase 5's computed convergence signal. RECORDED, NEVER ROUTED ON — no
    # caller branches on it and `routing.MAX_LOOPS` remains the only stopping
    # authority. Optional for the same reason `record` is: None means the
    # predicate was not run at all, which is distinct from it running and
    # reaching the residual arm (a ConvergenceAssessment with state
    # INDETERMINATE — the predicate's spelling, deliberately NOT the exit
    # protocol's `undetermined`; `ConvergenceState` says why the two must not
    # collapse, and collapsing them here in prose is how that starts).
    convergence: convergence.ConvergenceAssessment | None = None

    @property
    def ready_to_merge(self) -> bool:
        return self.verdict is Verdict.MERGE


# The completion contract. `exit 0` means finished only if output matches this.
COMPLETION_PATTERN = r"^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$"

MODEL_KEY = "review-pr"

# THE ONE DECLARATION of the merge-deciding parser, re-exported rather than
# re-typed — §6, and the same line `build/build_helper.py` ships. Its owner is
# `routing.py`, which carries the fail-safe rationale and the LAST-match-wins
# rule; a body typed here would be a second copy that stays green in its own
# tests while diverging from the rule applied to its owner. Issue #34 named this
# file and `build_helper.py` and was closed with only the other one fixed.
#
# THIS IS THE SHADOW CHANNEL'S OWN ROUTE. The comparator this module builds
# exists to notice when two channels disagree; a private retype here would make
# the comparator the divergence it was built to detect.
#
# `test_parse_verdict_is_declared_exactly_once_in_the_whole_tree` fails if a
# THIRD declaration appears anywhere — the gate is on the class, not this
# instance.
parse_verdict = routing.parse_verdict


def pass_numbers(prior_pass_count: int) -> tuple[int, int]:
    """(this_pass, prior_pass) from the count of prior disposition comments.

    Pass numbering is 1-based; prior_pass is 0 on a fresh PR, which the prompt
    reads as "no prior pass to reconcile against."
    """
    if prior_pass_count < 0:
        raise ValueError(f"prior pass count cannot be negative: {prior_pass_count}")
    return prior_pass_count + 1, prior_pass_count


# `- id: <slug>` under `findings:`; two-space and four-space indents both occur
# in the archive. Shape-identical to `replay_pr_review_blocks.FINDING_ID` for the
# same reason `PR_REVIEW_BLOCK` is: that module measures the fleet from outside
# it, and coupling a workflow helper to a measurement tool would invert the
# dependency.
_FINDING_ID = re.compile(r"^\s*-\s*id:\s*([^\s#]+)", re.MULTILINE)

# The `disposition:` belonging to a finding, matched from that finding's `- id:`
# line up to the next one. `disposition.md`'s block puts four keys between them,
# so an unbounded search would attribute the NEXT finding's value to this one.
_FINDING_ITEM = re.compile(
    r"^[ \t]*-[ \t]*id:[ \t]*([^\s#]+)(.*?)(?=^[ \t]*-[ \t]*id:|\Z)",
    re.MULTILINE | re.DOTALL,
)
_DISPOSITION = re.compile(r"^[ \t]*disposition:[ \t]*([^\s#]+)", re.MULTILINE)

# The INCUMBENT convergence flag, model-asserted under the single-pass severity
# heuristic at `disposition.md` Stage 4. Read here so the computed signal can be
# SHADOWED against it — Phase 1 E7's ruling is that `converged` is a label the
# computation should reproduce, not a competitor to replace silently, and a
# shadow needs both values in one place to be countable.
#
# Shape-identical to `replay_pr_review_blocks.CONVERGED` and paired in
# `SHARED_KIND_ONE_PATTERNS`, for the reason every other pattern in this file
# is: the two readers attribute the same field, and a silent divergence would
# make the workflow's agreement count disagree with the archive replay's while
# both suites stayed green.
#
# DELIBERATELY NARROW: unquoted, lowercase, first match. Both emitters instruct
# exactly `converged: true|false` (`review-pr.sh:355`, `disposition.md:265`) and
# no archived block departs from it. Widening it to tolerate `True` or `"true"`
# would mean widening `replay_pr_review_blocks.CONVERGED` in step with it to keep
# the one-declaration gate green — moving a shared tool whose published figures
# must stay reproducible, to accept a form nothing produces. The failure
# direction if one ever appears is fail-safe: a non-matching form reads as
# `None`, i.e. "this block predates the flag", which SHRINKS the agreement
# denominator rather than adding a wrong entry to it.
CONVERGED_FLAG = re.compile(r"^\s*converged:\s*(true|false)", re.MULTILINE)


def _unquote(token: str) -> str:
    """Strip one matched pair of surrounding quotes, and nothing else.

    `- id: "a-slug"` is valid yaml for `a-slug`, and the raw capture keeps the
    quotes. Comparing that against the typed record's `a-slug` raises "the two
    copies disagree" on input that is semantically identical — a guard failing
    on correct input, which is the anti-pattern `finding_dispositions_in_block`
    avoids a YAML parser to escape in the first place.
    """
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    return token


# The `findings:` mapping value — from the key to the next key at the SAME
# indent, or the end of the block. `[ \t]` and not `\s` in the indent capture,
# because `\s` matches the newline and would let the group span into the body.
_FINDINGS_SECTION = re.compile(
    r"^([ \t]*)findings:[ \t]*$(.*?)(?=^\1[A-Za-z_][A-Za-z0-9_]*:|\Z)",
    re.MULTILINE | re.DOTALL,
)


def findings_section(block: str) -> str:
    """The block's `findings:` value, or `""` when it declares none.

    THE SCAN BELOW IS ANCHORED HERE BECAUSE `- id:` IS NOT UNIQUE TO A FINDING,
    AND THE PROMPT IS WHAT MAKES IT NOT UNIQUE. `disposition.md:292` gives the
    child a `dispatch_context: |` block scalar whose documented content is
    *"which findings to fix, what to change, what NOT to touch"*, and `:295` a
    `precheck: |` beside it. Both are free text inside the same `pr_review:`
    block, after `findings:`. A reviewer enumerating findings there the way the
    prompt asks — `- id: some-slug` — injects an entry the scan cannot tell from
    a real one, and the injected entry carries no `disposition:`, so it pairs
    with `""` and is OPEN by rule.

    Both consequences are severe and neither is loud:

    - `_assert_block_matches_record` raises AFTER the child's comment is posted
      and AFTER `append_parent_route` persisted the route, so a **correct**
      review is destroyed at the last step;
    - `convergence_history` runs this same parse over PRIOR blocks, where no
      invariant checks it at all. One phantom id in pass 1 is absent from every
      later pass, so C3 reports `PRIOR_FINDINGS_DROPPED` and the PR is
      INDETERMINATE for the rest of its life.

    Measured over the archive at 27 blocks / 14 PRs: **0 blocks carry a `- id:`
    outside `findings:`**, so anchoring moves no replayed figure. The regexes
    themselves are UNCHANGED — they stay byte-identical to
    `replay_pr_review_blocks`' pair, which `SHARED_KIND_ONE_PATTERNS` gates —
    and the fix is a narrowing of the INPUT in the consumer that holds the
    contract. That is the same ruling this phase made for the `pass:` ordering
    defect: the shared extractor feeds a published figure, so a consumer's
    contract is enforced in the consumer.
    """
    match = _FINDINGS_SECTION.search(block)
    return match.group(2) if match else ""


def finding_ids_in_block(block: str) -> frozenset[str]:
    """The finding ids the DURABLE record claims, for the render-record invariant.

    Regex rather than a YAML parser, deliberately: the archived blocks predate
    any schema and some are hand-edited, so a strict parser would reject exactly
    the malformed ones this check most wants to catch — and a check that throws
    on the input it exists to examine is not a check.
    """
    return frozenset(_unquote(t) for t in _FINDING_ID.findall(findings_section(block)))


def finding_dispositions_in_block(block: str) -> frozenset[tuple[str, str]]:
    """`(id, disposition)` pairs the durable block claims.

    THE PROMPT PROMISES BOTH HALVES AND THE INVARIANT MUST CHECK BOTH.
    `disposition.md` tells the child that every `findings[].id` AND
    `findings[].disposition` is identical in the block and the record, and that
    its caller fails the run loud on a mismatch. Comparing ids alone let a block
    saying `deferred` stand against a record saying `fixed` — and
    `findings[].disposition` is the field Phase 5's stopping predicate keys on,
    so the two copies would diverge in exactly the place a convergence rule
    reads. A finding with no parseable `disposition:` pairs with the empty
    string, which fails the comparison rather than silently dropping out.

    ANCHORED TO `findings:` — see `findings_section` for why `- id:` elsewhere in
    the block is a shape the shipped prompt actively invites.
    """
    return frozenset(
        (_unquote(fid), _unquote(m.group(1)) if (m := _DISPOSITION.search(body)) else "")
        for fid, body in _FINDING_ITEM.findall(findings_section(block))
    )


def asserted_converged_in_block(block: str) -> bool | None:
    """The block's own `converged:` claim, or None when it carries no such key.

    NONE IS A THIRD VALUE, NOT A DEFAULT. Absence dates a block to before the
    flag shipped, and folding it into `false` would make an agreement rate over
    the archive quietly count pre-flag blocks as disagreements with whatever the
    computation said. `replay_pr_review_blocks` draws the same distinction for
    the same reason.
    """
    match = CONVERGED_FLAG.search(block)
    return (match.group(1) == "true") if match else None


def _this_pass_index(window: Sequence[str]) -> int | None:
    """WHICH block in the thread's window is this pass's. THE ONE DECLARATION.

    ONE DECLARATION OF AN INFERENCE THAT WAS MADE IN FIVE PLACES. The
    render↔record invariant, the incumbent-flag shadow and the convergence
    history each need *"which of these is this pass's"*, and each was answering
    it with its own `window[-1]` or `window[:-1]` slice.
    `phase4_fleet_migration.md`'s run-nonce checkbox replaces this positional
    inference with an identity check, and it needs ONE site to replace.

    IT IS AN INDEX, NOT A BLOCK, BECAUSE THE COMPLEMENT MUST FOLLOW FROM THE
    SAME ANSWER. A first version of this collapse declared `this_pass_block`
    alone and left `prior_pass_blocks` as its own `window[:-1]` — the complement
    of the same inference, stated separately. That is not one declaration: when
    the nonce lands, `this_pass_block` becomes identity-based and a positional
    complement keeps selecting by position, so the two disagree about which
    block is this pass's. The failure is not an exception — the same pass then
    appears twice in the history, every id looks restated, and the result reads
    as a perfectly conforming, perfectly stalled loop, which is exactly what
    `convergence_history`'s own docstring warns about. Both public accessors
    below are derived from this function so the disagreement is unwritable.

    IT IS POSITIONAL AND THAT IS THE KNOWN WEAKNESS, not a hidden one. The block
    carries no `run_id`, so "this pass's" is inferred from ordering plus the
    posted-count delta `_assert_block_matches_record` checks. The remaining race
    — a third party posting a fenced `pr_review:` example between the child's
    comment and the parent's read — is what the nonce closes.
    """
    return len(window) - 1 if window else None


def this_pass_block(window: Sequence[str]) -> str | None:
    """The block THIS pass posted, out of the thread's window. None if empty."""
    index = _this_pass_index(window)
    return window[index] if index is not None else None


def prior_pass_blocks(window: Sequence[str]) -> tuple[str, ...]:
    """Every block in the window EXCEPT this pass's. The typed record replaces it.

    The complement of `this_pass_block`, derived from the SAME index rather than
    from its own slice — see `_this_pass_index` for why that is the property and
    not a tidiness preference.
    """
    index = _this_pass_index(window)
    return tuple(window[:index]) if index is not None else ()


def convergence_history(window: Sequence[str],
                        record: exit_record.ExitRecord,
                        ) -> tuple[tuple[tuple[str, str], ...], ...]:
    """This PR's passes oldest-first, as `(id, disposition)` pairs per pass.

    TAKES THE WHOLE WINDOW AND DROPS THIS PASS'S BLOCK ITSELF. It used to require
    the caller to have removed it already, enforced by nothing but this
    docstring — and Phase 4 adds the call sites. The failure mode of getting it
    wrong is not an exception: the same pass appears twice, every id looks
    restated, and the result reads as a perfectly conforming, perfectly stalled
    loop. A precondition whose violation is silent and whose only enforcement is
    prose is not a precondition.

    THE PREDICATE IS A HYBRID AND THIS FUNCTION IS WHERE THAT SHOWS. The pass
    under assessment comes from the TYPED record, which is authoritative; every
    prior pass comes from its durable `pr_review:` block, parsed as prose.
    That is not an oversight and it is not a hole in the typed channel — a Kind
    2 record's lifetime is one parent invocation (`exit-protocol.md` §1, and the
    to-do-bit ruling in Phase 3 step 6), so a prior pass's typed record does not
    exist to be read. Kind 1 is the only durable copy, which is exactly the job
    §1 gives it.

    THE TWO SOURCES ARE NOT ASSUMED TO AGREE — they are made to. The
    render↔record invariant (`review_pr_workflow._assert_block_matches_record`)
    raises unless this pass's posted block and this pass's record carry
    identical `(id, disposition)` pairs, so today's typed term becomes
    tomorrow's prose term without drift.
    """
    return tuple(
        [tuple(sorted(finding_dispositions_in_block(b)))
         for b in prior_pass_blocks(window)]
        + [tuple(sorted((f["id"], f["disposition"]) for f in record.findings))]
    )


def shadow_agreement(assessment: convergence.ConvergenceAssessment,
                     asserted: bool | None) -> bool | None:
    """Does the computation reproduce the incumbent flag? None when incomparable.

    ONE DECLARATION, because the rule was written twice in opposite polarity two
    lines apart — once for the run-log event and once for the operator note. The
    comparability rule is the thing most likely to move, and a durable record
    saying `agrees: false` while the human-facing note stays silent is two
    accounts of one shadow disagreeing, which is the defect class this component
    exists to remove.

    TWO WAYS TO BE INCOMPARABLE, both returning None. `asserted is None` means
    the block predates the flag — distinct from `false`, or an agreement rate
    scores every pre-flag block as a disagreement. An INDETERMINATE assessment
    made no decision, so it agrees with nothing; folding it into `not converged`
    would invent a verdict the predicate declined to reach, and that case is not
    rare — it is pass 1, the archive's single most common block.

    AND WHAT "AGREEMENT" DOES NOT MEAN, because the name overpromises: the two
    rules answer different questions. The incumbent is a single-pass severity
    heuristic (*are this pass's findings all preventive?*); this is a set
    emptiness test across passes (*is anything still open?*). A `False` here is a
    definitional difference at least as often as it is a defect in either
    channel, which is why nothing raises on one.
    """
    if asserted is None or assessment.state is convergence.ConvergenceState.INDETERMINATE:
        return None
    return asserted == (assessment.state is convergence.ConvergenceState.CONVERGED)


def verdict_from_record(record: exit_record.ExitRecord) -> Verdict:
    """The incumbent routing token this typed record produces.

    THE TYPED REGION WINS. This is the only translation between the two
    vocabularies, and it runs one way: the record decides, and the prose is
    compared against it (never the reverse). Both computed and asserted
    abstention collapse to `HOLD - needs-assistance` here because the prose
    vocabulary HAS only one abstention member — which is the whole reason the
    typed one splits it, and why this function is not a general mapping layer.
    """
    if record.routed_outcome is exit_record.RoutedOutcome.MERGE:
        return Verdict.MERGE
    if exit_record.routes_to_redispatch(record):
        return Verdict.HOLD_REDISPATCH
    return Verdict.HOLD_NEEDS_ASSISTANCE


def render_prompt(template: str, *, pr_number: str, pr_branch: str,
                  this_pass: int, prior_pass: int, headless_guard: str,
                  run_id: str) -> str:
    """Substitute the prompt's six placeholders.

    Deliberately NOT str.format() or an f-string: the prompt is 283 lines of
    markdown containing JSON examples, yaml blocks and shell snippets, all full
    of literal braces. Brace-based templating would either raise or silently
    interpolate them. Explicit replacement of `${NAME}` has no such surface —
    the same reasoning that moved the prompt out of a shell string.
    """
    values = {
        "PR_NUMBER": str(pr_number),
        "PR_BRANCH": pr_branch,
        "THIS_PASS": str(this_pass),
        "PRIOR_PASS": str(prior_pass),
        "HEADLESS_EXECUTION_GUARD": headless_guard,
        # The run-identity nonce. It goes IN so it can come back out in the
        # typed record and be compared against what this invocation issued —
        # rule R5. A record that echoes a different nonce is well-formed and
        # belongs to a different invocation.
        "RUN_ID": run_id,
    }
    rendered = template
    for name, value in values.items():
        rendered = rendered.replace("${" + name + "}", value)

    # An unsubstituted placeholder is a silent defect — it reaches the model as
    # literal `${FOO}` and reads as an instruction about a variable. Fail loud.
    #
    # [A-Z_0-9] — DIGITS MATTER. An earlier [A-Z_]+ silently missed
    # ${STAGES_1_TO_4}, so a prompt shipped with its entire stage body replaced
    # by a literal placeholder and this check raised nothing. The guard was
    # blind to the one thing it existed to catch. review-pr's own placeholders
    # are digit-free today, which makes the same bug latent here rather than
    # live — a guard that only holds for the current inputs is not a guard.
    # Kept character-identical to assistant_activities.render() deliberately:
    # two spellings of one rule is how the twin drifted in the first place.
    leftover = re.findall(r"\$\{[A-Z_][A-Z_0-9]*\}", rendered)
    if leftover:
        raise ValueError(f"unsubstituted prompt placeholders: {sorted(set(leftover))}")
    return rendered
