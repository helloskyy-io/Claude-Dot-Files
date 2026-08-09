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
from dataclasses import dataclass, field
from enum import Enum

from .. import exit_record, routing


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

    @property
    def ready_to_merge(self) -> bool:
        return self.verdict is Verdict.MERGE


# Anchored and exhaustive: an unanchored match would find the token inside prose
# discussing it. MULTILINE because the line sits in a stream of output.
_VERDICT = routing._VERDICT   # ONE parser (§10.1); see routing.py and issue #34

# The completion contract. `exit 0` means finished only if output matches this.
COMPLETION_PATTERN = r"^VERDICT: (MERGE|HOLD - (redispatch|needs-assistance))$"

MODEL_KEY = "review-pr"


def parse_verdict(output: str) -> tuple[Verdict, bool]:
    """Return (verdict, was_parseable).

    FAILS SAFE TO THE HUMAN BRANCH. An unparseable verdict becomes
    HOLD_NEEDS_ASSISTANCE — never MERGE, never a redispatch. The routing
    contract's rule: ambiguity routes to the branch requiring a person, because
    wrongly merging costs an unbounded amount and wrongly asking costs one
    message.
    """
    matches = _VERDICT.findall(output)
    if not matches:
        return Verdict.HOLD_NEEDS_ASSISTANCE, False
    return Verdict(matches[-1]), True


def pass_numbers(prior_pass_count: int) -> tuple[int, int]:
    """(this_pass, prior_pass) from the count of prior disposition comments.

    Pass numbering is 1-based; prior_pass is 0 on a fresh PR, which the prompt
    reads as "no prior pass to reconcile against."
    """
    if prior_pass_count < 0:
        raise ValueError(f"prior pass count cannot be negative: {prior_pass_count}")
    return prior_pass_count + 1, prior_pass_count


def verdict_from_record(record: exit_record.ExitRecord) -> Verdict:
    """The incumbent routing token this typed record produces.

    THE TYPED REGION WINS. This is the only translation between the two
    vocabularies, and it runs one way: the record decides, and the prose is
    compared against it (never the reverse). Both computed and asserted
    abstention collapse to `HOLD - needs-assistance` here because the prose
    vocabulary HAS only one abstention member — which is the whole reason the
    typed one splits it, and why this function is not a general mapping layer.
    """
    return Verdict(exit_record.as_prose_verdict(record).removeprefix("VERDICT: "))


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
