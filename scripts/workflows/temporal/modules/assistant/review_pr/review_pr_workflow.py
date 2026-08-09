"""The review-pr disposition engine — Layer 1 orchestration.

DECIDE-ONLY. It merges nothing, closes nothing, fixes nothing, dispatches
nothing. Its output is one disposition comment plus a terminal VERDICT line —
plus the single write authority it holds: filing GitHub Issues for qualifying
deferred work. That exception exists because it is the only actor with no scope
of its own to offload; everything else stays decide-only.

    gather → render → dispose → verdict

Every decision below comes from the helper; every side effect is an activity.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from .. import assistant_activities as _shared
from .. import exit_record
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


def run_review(task: ReviewInput, worktree: Path) -> ReviewResult:
    """Disposition one PR and return its typed verdict."""
    notes: list[str] = []

    pr = act.fetch_pr(task.pr_number, worktree)
    this_pass, prior_pass = helper.pass_numbers(
        act.count_prior_passes(task.pr_number, worktree)
    )

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
    log_file = _shared.claude_log_path(worktree, helper.MODEL_KEY)
    act.run_disposition(
        prompt, worktree, helper.MODEL_KEY, helper.COMPLETION_PATTERN,
        worktree=pr_tree, verbose=task.verbose,
        exit_record_schema=exit_record.schema_argument(), log_file=log_file,
    )

    # --- THE TYPED CHANNEL DECIDES --------------------------------------
    record = exit_record.route(_shared.result_event(log_file), expected_run_id=run_id)
    verdict = helper.verdict_from_record(record)

    # --- THE PROSE CHANNEL IS A SHADOW ----------------------------------
    # Still emitted, still parsed, and it decides nothing. Read from the
    # assistant text blocks rather than from the console or `.result`: declaring
    # a schema replaces `.result` with the serialised structured output, so a
    # shadow read from there would report a disagreement that is an artifact of
    # where it looked.
    shadow, parseable = helper.parse_verdict(_shared.assistant_text(log_file))
    if shadow is not verdict:
        # A LOUD FAILURE, deliberately, for the duration of this phase. A
        # comparison that cannot fail records a protection that does not exist,
        # and the whole point of running both channels on one pair is to find
        # out where they disagree before the fleet depends on one of them.
        raise RuntimeError(
            f"exit-record disagreement on PR #{task.pr_number}: the typed record routes "
            f"{verdict.value!r} (routed_outcome={record.routed_outcome.value}"
            + (f"/{record.undetermined_reason.value}" if record.undetermined_reason else "")
            + f") while the prose channel parsed {shadow.value!r} "
            f"(parseable={parseable}). Both channels are live during Phase 3 and "
            f"disagreement is a failure, not a preference. Log: {log_file}"
        )

    notes.append(
        f"Routed on the typed exit record: routed_outcome={record.routed_outcome.value}"
        + (f", reason={record.undetermined_reason.value}" if record.undetermined_reason else "")
        + f". Prose shadow agreed ({shadow.value})."
    )
    if record.routed_outcome is exit_record.RoutedOutcome.UNDETERMINED:
        notes.append(
            f"The typed record could not be evaluated ({record.undetermined_reason.value}) "
            f"on PR #{task.pr_number}. This is the COMPUTED abstention arm — a defect in "
            f"the machinery, not a question about the work. Inspect by hand: {log_file}"
        )
    if record.permission_denials:
        notes.append(
            f"{len(record.permission_denials)} permission denial(s) recorded: "
            + ", ".join(sorted({d['tool_name'] for d in record.permission_denials}))
            + ". Never auto-redispatched — a child that tripped the only in-run safety "
              "control is not retried against it."
        )

    return ReviewResult(
        pr_number=task.pr_number, verdict=verdict, this_pass=this_pass,
        parseable=parseable, notes=notes, record=record,
    )
