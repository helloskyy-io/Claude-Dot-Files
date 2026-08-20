"""research-verify — FRESH context: verify everything the PR ships, and fix it.

Folder holds only this file (§10.1 rule 6).

Three jobs the monolith never separated, all still done, now in ONE critic loop
rather than three stages:
  1. verify each paper (this existed, as stage 4)
  2. trace every correction through to the synthesis (§4 binding rule, never executed)
  3. verify the SYNTHESIS itself (never existed at all)

Job 3 is why this child exists. The synthesis carries a paper's full sourcing
burden per §4 and is the only artifact the standup consumes — and nothing
checked it. A wrong count in one cycle's synthesis propagated into the next
cycle's dispatch prompts and mis-instructed two analysts.

WHY THEY COLLAPSED INTO ONE PASS. They were separate stages because a separate
`research-analyst` did the writing, so each artifact needed its own hand-off.
The child now holds Write/Edit and applies the critic's findings itself, which
makes tracing a correction into the synthesis simply part of fixing it.

AND THE SCOPE WIDENED WITH IT: the papers, the synthesis, the PR body, internal
links, the header block, and every claim the paper makes about OUR platform —
which the authoring run could not check, having been on the web while this child
holds the repo. Measured: three of four items on one cycle's first review pass
came from outside the paper, so a verifier scoped to "the papers" leaves the
common defect for a downstream reviewer that cannot fix it.
"""

from __future__ import annotations

from ... import routing

from pathlib import Path

from .. import research_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "research"
# Its own key, not `research` — see research_write for why the cap is keyed by
# workflow rather than by model. Measurement lives with the value in config.yaml.
WORKFLOW_KEY = "research-verify"   # NOT MODEL_KEY -- see run_claude's docstring
MAX_TURNS = act.max_turns(WORKFLOW_KEY)

COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE


def run_verify(*, research_dir: Path, pr_number: str, repo_root: Path,
               worktree: Path, correction_pass: bool = False,
               verbose: bool = False) -> str:
    """Verify everything the PR ships, correct it, and re-verify. Returns the PR URL.

    THE `minor_cycle` / `synthesis_present` PAIR WAS DELETED HERE, and the reason
    is that both had become false. They rendered a `CYCLE_SHAPE_NOTE` built on one
    premise — *a minor cycle writes no synthesis* — which stopped being true when
    `research_write_minor` gained Stage 3 SYNTHESIZE on 2026-08-17. After that,
    `synthesis.md` always exists when this child runs, so `minor_cycle` was
    unreachable and its sibling arm fired on every minor run telling it the
    synthesis was **from an earlier full cycle** and **does not cover this cycle's
    paper**. Both false, on every run, for the artifact the standup consumes.

    Filed as issue #107 by `review-pr` on PR #106 and closed by this deletion. The
    prompt needs no replacement: it opens with *"you did not write these papers and
    you did not write this synthesis"*, which is true — the write child wrote both.
    """
    pool = act.in_worktree(research_dir, repo_root, worktree)
    currency, _due = act.paper_currency(pool)
    values = {
        # The path the MODEL is given must be the one it can actually write to.
        # `pool` is `research_dir` re-anchored to this run's worktree; handing over
        # the un-anchored `research_dir` pointed two consecutive runs (#84, #86) at
        # the MAIN CHECKOUT, and both were caught only by a pre-commit `git status`.
        "RESEARCH_DIR": str(pool),
        "PR_NUMBER": pr_number,
        "PR_BRANCH": act.branch_of(pr_number, repo_root),
        "CURRENCY_BLOCK": currency,
        "CORRECTION_NOTE": (
            "This is a CORRECTION PASS. A prior disposition returned HOLD with a "
            "scoped runway; close it. This is the last automated pass."
            if correction_pass else ""
        ),
        "SUBMIT_PROMPT": act.submit_prompt(pr_number, f"research-verify: {research_dir}"),
        "RESOLVE_APPLY_THE_REMEDY_YOU_WROTE": act.shared_prompt("resolve_apply_the_remedy_you_wrote"),
        "RESOLVE_REJECTING_IS_LEGITIMATE": act.shared_prompt("resolve_rejecting_is_legitimate"),
        "RESOLVE_YOUR_OWN_DISPOSITIONS_TOO": act.shared_prompt("resolve_your_own_dispositions_too"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
    }
    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "verify.md"), values),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree, max_turns=MAX_TURNS, verbose=verbose,
    )
    from ...assistant_activities import extract_pr_url
    url = extract_pr_url(output)
    if not url:
        raise RuntimeError(
            f"research-verify produced no PR URL on PR #{pr_number}. The pool and "
            f"synthesis are UNVERIFIED — the PR must not be merged as-is."
        )
    return url
