"""research-verify — FRESH context: verify the papers, fix, trace, verify the synthesis.

Folder holds only this file (§10.1 rule 6).

Three jobs the monolith never separated:
  1. verify each paper (this existed, as stage 4)
  2. trace every correction through to the synthesis (§4 binding rule, never executed)
  3. verify the SYNTHESIS itself (never existed at all)

Job 3 is why this child exists. The synthesis carries a paper's full sourcing
burden per §4 and is the only artifact the standup consumes — and nothing
checked it. A wrong count in one cycle's synthesis propagated into the next
cycle's dispatch prompts and mis-instructed two analysts.
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
               minor_cycle: bool = False,
               synthesis_present: bool = False, verbose: bool = False) -> str:
    """Verify, correct, trace, and re-verify. Returns the PR URL.

    `minor_cycle` AND `synthesis_present` STATE WHAT IS ON DISK, together. Neither
    is a switch over this child's behaviour, and that difference is load-bearing
    rather than semantic.

    THEY WERE ONE PARAMETER AND IT SAID THE WRONG THING. `minor_cycle` alone was
    documented as *stating what the parent produced*, and the parent hard-coded
    it `True` — so a minor cycle running against a pool an earlier FULL cycle had
    populated told this child "no synthesis exists" while one sat right there,
    and stages 2 and 3 skipped the only artifact the standup consumes. The parent
    now derives both from the worktree it reads:

      * `minor_cycle`       -> one paper was written and NO synthesis is present
      * `synthesis_present` -> a synthesis IS present, from an earlier cycle;
                               verify it as always and report that this cycle's
                               new paper is not yet in it

    They are mutually exclusive by construction and both may be false, which is
    the full cycle.

    The mechanics never needed a signal: this child discovers artifacts from
    `RESEARCH_DIR` on the filesystem and NOTHING here reads `synthesis.md`, so a
    directory without one already works. The PROMPT is what breaks — it opens by
    asserting *"you did not write this synthesis"*, which presupposes one exists.
    A run reading that against a directory with no synthesis will stall or invent
    one, and inventing is the exact failure this child guards against.

    So the parent renders a block of FACT — the cycle produced one paper and no
    synthesis — exactly as it already renders `correction_pass`. What it must
    NOT become is a flag that alters which artifacts this workflow emits: that
    is a behavioural branch living inside a prompt, and prompt branches are
    where drift lives. Every arm of the verification itself is unchanged, and
    Stage 1 verifies the paper exactly as always.

    WHAT IS ACTUALLY PROVEN, STATED NARROWLY, because the paragraph above is
    easy to read as a stronger claim than the tests support.
    `test_the_flag_reaches_no_if_statement` proves the MECHANICS are
    unconditional: this parameter reaches no `if`, and nothing here reads
    `synthesis.md`, so no Python path forks on it. It does NOT prove the
    rendered prompt is behaviourally inert — the block plainly tells the model
    to emit `SKIPPED` for stages 2 and 3, and those stages are work that
    otherwise happens.

    That residue is ACCEPTED, not overlooked, and the reason is narrow: stages 2
    and 3 operate on a synthesis, the skip is asserted only when no synthesis
    exists, and the alternative — a run inventing one so it has something to
    verify — is the failure this child exists to prevent. The honest reading is
    that the parameter states a fact and the model draws the only consequence
    that fact has. What the design forbids is the NEXT block being added this
    way with a consequence that does not follow from a fact about the
    filesystem, and an AST walk over Python cannot tell those two apart.
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
        "CYCLE_SHAPE_NOTE": (
            "**MINOR CYCLE — one paper, no synthesis. The paper IS the deliverable.** "
            "Stage 1 verifies it exactly as always. **Stages 2 and 3 emit "
            "`SKIPPED — minor cycle, no synthesis exists`.** Do not create one, and "
            "do not treat its absence as a defect."
            if minor_cycle else
            "**MINOR CYCLE OVER AN EXISTING SYNTHESIS.** This cycle wrote ONE paper and "
            "no synthesis, but `synthesis.md` is present from an earlier full cycle. "
            "**Verify it exactly as always** — it is still the artifact the standup "
            "consumes. It does NOT cover this cycle's new paper; say so in your report "
            "rather than tracing a correction into a section that cannot exist."
            if synthesis_present else ""
        ),
        "SUBMIT_PROMPT": act.submit_prompt(pr_number, f"research-verify: {research_dir}"),
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
