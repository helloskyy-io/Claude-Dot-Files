"""build-draft-minor — the light tier's draft: one scoped change, one PR.

Folder holds only this file (§10.1 rule 6): the family's trio is promoted to the
purpose level. Its wrappers carry their own stage text — unlike the major tier
they pull in neither RULES nor the headless guard, which is why they are larger.
They are not fragment-free: the evidence-discipline pair and the two blocks
promoted with them are shared, and which fragments a wrapper is DENIED is a
ruling in `tests/unit/fork_vs_parameterize.py`, not an accident of history.
"""

from __future__ import annotations

from ... import routing

from pathlib import Path

from ... import assistant_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "build-draft-minor"
WORKFLOW_KEY = "build-draft-minor"   # the run log's per-workflow bin; see run_log.py
MAX_TURNS_KEY = WORKFLOW_KEY          # constants DERIVED, never re-declared
COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE


def run_draft_minor(*, description: str, repo_root: Path, worktree: Path,
                    pr_number: str | None = None, plan_path: str | None = None,
                    context: str = "", verbose: bool = False) -> str:
    """Draft a scoped change. Returns the PR URL — the handoff to refine."""
    # Same single axis as the major tier. Scope is what makes this the minor
    # tier — a 100-turn cap — not the information source. A small fix scoped to
    # a phase still benefits from that phase's success criteria to verify against.
    # BOTH plan-driven prompts are SHARED with build_draft — see that workflow.
    # The non-plan wrappers are NOT: they are self-contained at this tier.
    if plan_path:
        template = act.shared_prompt("build_from_plan")
        stages_body = act.shared_prompt("stages_1_to_4_from_plan")
    else:
        wrapper = "update_pr.md" if pr_number else "new_branch.md"
        template = act.load_prompt(PROMPTS / wrapper)
        stages_body = None
    values = {
        "DESCRIPTION": description,
        # Tier identity, derived from `WORKFLOW_KEY` — see the sibling tier.
        "WORKFLOW_LABEL": WORKFLOW_KEY.upper(),
        "TIER_PREFIX": f"{WORKFLOW_KEY}:",
        "VERIFICATION_IS_BY_FETCH": act.shared_prompt("verification_is_by_fetch"),
        "VERIFY_THE_TASKS_ASSERTED_FACTS": act.shared_prompt("verify_the_tasks_asserted_facts"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        # BOTH OF THESE MOVED UP TO THE BASE DICT, because both are now
        # referenced on every path of this tier rather than on one arm of it.
        # `characterize_by_execution` was wrapper-only and the shared plan body
        # never carried it; `gitignore_collision_check` was plan-only and NEITHER
        # wrapper carried it, so a light-tier run on a fresh branch could ship a
        # PR its own new files were invisible in. Both are TIER_INVARIANT under
        # `tests/unit/fork_vs_parameterize.py` — `evidence-discipline` and
        # `operational-safety`, the second of which reads "a cheaper run is not a
        # run permitted to be less careful".
        "CHARACTERIZE_BY_EXECUTION": act.shared_prompt("characterize_by_execution"),
        "GITIGNORE_COLLISION_CHECK": act.shared_prompt("gitignore_collision_check"),
    }
    if stages_body:
        values |= {
            "STAGES_1_TO_4": stages_body,
            "RULES": act.shared_prompt("rules"),
            "MUTATION_DISCIPLINE": act.shared_prompt("mutation_discipline"),
            # The plan-driven body carries this as a PLACEHOLDER rather than as
            # text: it was a byte-exact copy of a pool fragment sitting INSIDE a
            # pool fragment, where no duplication guard looks — `_duplicated()`
            # skips the pool by construction. Plan-path only, because the
            # wrappers open with their own condensed ordering paragraph.
            "STAGE_ORDER_IS_MANDATORY": act.shared_prompt("stage_order_is_mandatory"),
            "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
            "PLAN_PATH": plan_path, "CONTEXT_BLOCK": context,
        }
    else:
        # WRAPPER-BRANCH, AND THE REASON IS THE PLAN BODY'S OTHER CONSUMER.
        # This block was prose in `update_pr.md` and absent from `new_branch.md`,
        # so a light-tier run started on a fresh branch was never told to prove
        # its gate can go red — one of the two disciplines that stand in for the
        # review agents this tier does not dispatch. Promoted by §10.1 once the
        # second consumer existed.
        #
        # It stays here rather than moving to the base dict because the shared
        # plan template does not reference it and `build_draft` renders that same
        # template without supplying it: a base-dict entry would be built and
        # thrown away on the plan path, which is the same defect one path over,
        # and `test_every_pool_fragment_a_dispatch_LOADS_also_RENDERS` fails on
        # it. Its sibling `characterize_by_execution` moved UP for the mirror
        # reason — the plan body now DOES reference that one.
        values |= {
            "CAN_IT_FAIL_LIGHT_TIER": act.shared_prompt("can_it_fail_light_tier"),
        }
    if pr_number:
        values |= {"PR_NUMBER": pr_number, "PR_BRANCH": act.pr_branch(pr_number, repo_root)}

    output = act.run_claude(
        act.render(template, values,
                   opaque=frozenset({"DESCRIPTION"})),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=act.max_turns(MAX_TURNS_KEY),
        verbose=verbose,
    )
    url = act.extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "build-draft-minor produced no PR URL — cannot hand off to refine. "
            "The draft step must open (or update) a PR and print its URL as its final line."
        )
    return url
