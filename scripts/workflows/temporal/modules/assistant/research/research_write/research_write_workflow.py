"""research-write — produce the pool and a DRAFT synthesis, open the PR.

Folder holds only this file (§10.1 rule 6): the family's shared capability is
promoted to `research_activities`.

Completion contract: the PR URL on the final line.

The synthesis it writes is explicitly a DRAFT. A separate fresh-context run
verifies the papers, applies corrections and traces each one through to it —
because the run that wrote an artifact defends it.
"""

from __future__ import annotations

from ... import routing

from pathlib import Path

from .. import research_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "research"

# ITS OWN KEY, NOT `research`. This workflow's MODEL_KEY is "research" and it
# shares that model with `research_verify` — but the three have separately
# measured turn budgets, so the cap is keyed by WORKFLOW. Keying it off the
# model would silently revert this 150 to the parent's 250, which is a mistake
# a previous version of this file made and carried a paragraph warning about.
# Reasoning and measurement live with the value, in config.yaml.
WORKFLOW_KEY = "research-write"   # NOT MODEL_KEY -- see run_claude's docstring
MAX_TURNS = act.max_turns(WORKFLOW_KEY)

COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE


def run_write(*, research_dir: Path, repo_root: Path, worktree: Path,
              context: str = "", pr_number: str | None = None,
              verbose: bool = False) -> str:
    """Discover, size, research, draft the synthesis, submit. Returns the PR URL."""
    pool = act.in_worktree(research_dir, repo_root, worktree)
    currency, _due = act.paper_currency(pool)

    # Altitude is DERIVED from the pool path (Research Standard §1 names two
    # locations, one each). It decides which stages exist at all: candidates.md
    # and direction.md are product-pool surfaces, and a component pool that
    # grows its own forks the operator's inbox.
    level = act.altitude(pool, worktree)
    # BOTH altitude blocks are SHARED, and the product one has been since #91: it
    # is one authorization contract about what a run may write to the operator's
    # inbox, and both entry points must be permitted exactly the same things.
    #
    # The component block was ONCE described here as genuinely differing between
    # write and refresh. It does not: the two files opened with 32 byte-identical
    # lines out of 43 here and 35 in refresh, and only the closing section
    # differs — this one sizes a new pool, refresh's says it may not resize an
    # existing one. So the shared lane rules are
    # `shared_prompt("altitude_component")` and the local file is the tail, named
    # `altitude_component_tail.md` so that searching for the lane rules finds the
    # one file that carries them rather than three files with the same name.
    if level == "PRODUCT":
        altitude = act.shared_prompt("altitude_product")
    else:
        altitude = act.load_prompt(PROMPTS / "altitude_component_tail.md")

    blocks = [b for b in (context, act.upstream_block(pool, worktree),
                          act.component_pools_block(pool, worktree), currency) if b]

    values = {
        # The path the MODEL is given must be the one it can actually write to.
        # `pool` is `research_dir` re-anchored to this run's worktree; handing over
        # the un-anchored `research_dir` pointed two consecutive runs (#84, #86) at
        # the MAIN CHECKOUT, and both were caught only by a pre-commit `git status`.
        "RESEARCH_DIR": str(pool),
        "CONTEXT_BLOCK": "\n\n".join(blocks),
        "SUBMIT_PROMPT": act.submit_prompt(pr_number, f"research: {research_dir}"),
        "ALTITUDE_BLOCK": altitude,
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }
    # Only the product fragment carries ${CANDIDATE_CEILING}; supplying it at
    # component altitude would be supplying a next-ID for a file that must not
    # exist there. render() substitutes to a fixed point, so the fragment's own
    # placeholder is resolved in the same pass.
    if level == "PRODUCT":
        values["CANDIDATE_CEILING"] = act.candidate_ceiling(research_dir)
    else:
        # Only the component fragment is loaded at component altitude, for the
        # mirror-image reason: supplying it at product altitude would inject
        # lane rules for a pool this run is not in. render() resolves to a fixed
        # point, so the fragment's own ${RESEARCH_DIR} is filled in the same pass.
        values["ALTITUDE_COMPONENT"] = act.shared_prompt("altitude_component")
    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "write.md"), values,
                   opaque=frozenset({"CONTEXT_BLOCK"})),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree, max_turns=MAX_TURNS, verbose=verbose,
    )
    from ...assistant_activities import extract_pr_url
    url = extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "research-write produced no PR URL — cannot hand off to verify. "
            "The run must open (or update) a PR and print its URL as its final line."
        )
    return url
