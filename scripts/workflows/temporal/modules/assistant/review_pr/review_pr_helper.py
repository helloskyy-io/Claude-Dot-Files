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
    # UNDETERMINED).
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


def finding_ids_in_block(block: str) -> frozenset[str]:
    """The finding ids the DURABLE record claims, for the render-record invariant.

    Regex rather than a YAML parser, deliberately: the archived blocks predate
    any schema and some are hand-edited, so a strict parser would reject exactly
    the malformed ones this check most wants to catch — and a check that throws
    on the input it exists to examine is not a check.
    """
    return frozenset(_unquote(t) for t in _FINDING_ID.findall(block))


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
    """
    return frozenset(
        (_unquote(fid), _unquote(m.group(1)) if (m := _DISPOSITION.search(body)) else "")
        for fid, body in _FINDING_ITEM.findall(block)
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


def convergence_history(prior_blocks: Sequence[str],
                        record: exit_record.ExitRecord,
                        ) -> tuple[tuple[tuple[str, str], ...], ...]:
    """This PR's passes oldest-first, as `(id, disposition)` pairs per pass.

    THE PREDICATE IS A HYBRID AND THIS FUNCTION IS WHERE THAT SHOWS. The pass
    under assessment comes from the TYPED record, which is authoritative; every
    prior pass comes from its durable `pr_review:` block, parsed as prose.
    That is not an oversight and it is not a hole in the typed channel — a Kind
    2 record's lifetime is one parent invocation (`exit-protocol.md` §1, and the
    to-do-bit ruling in Phase 3 step 6), so a prior pass's typed record does not
    exist to be read. Kind 1 is the only durable copy, which is exactly the job
    §1 gives it.

    THE TWO SOURCES ARE NOT ASSUMED TO AGREE — they are made to. The
    render↔record invariant (`review_pr_workflow._verify_block_matches_record`)
    raises unless this pass's posted block and this pass's record carry
    identical `(id, disposition)` pairs, so today's typed term becomes
    tomorrow's prose term without drift. Callers must pass the blocks with this
    pass's own block ALREADY REMOVED; passing it would put the same pass in the
    history twice and make every id look restated.
    """
    return tuple(
        [tuple(sorted(finding_dispositions_in_block(b))) for b in prior_blocks]
        + [tuple(sorted((f["id"], f["disposition"]) for f in record.findings))]
    )


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
