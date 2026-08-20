"""research-write-minor — ONE topic, ONE paper, plus the synthesis. Open the PR.

Folder holds only this file (§10.1 rule 6): the family's shared capability is
already promoted to `research_activities`, and this child reaches for exactly
the same helpers `research_write` does.

Completion contract: the PR URL on the final line — identical to its full-size
sibling, so `research_minor` reads the handoff the same way `research` does.

WHY A SEPARATE CHILD RATHER THAN A MODE ON `research_write`. A portfolio-
direction question cost ~3.5 hours, five papers and a synthesis, and the
operator called it "mass overkill for what we needed". The sizing rubric was
NOT the cause and tuning it would not have helped: Research Standard §2 already
puts Small at 1-2 topics, and even a correctly-sized Small run still produces
`topics.md`, a fan-out, a synthesis and a verify pass over all of it. The
missing shape is one with NO POOL IN IT AT ALL, and a pool-less pool-writer is
a different workflow, not a flag on this one.

WHAT IS DELIBERATELY ABSENT, and none of it is an oversight:

  * `topics.md` — it records which TIER was judged and what was left for a later
    cycle. A one-paper cycle judges nothing and defers nothing.
  * the sizing assessment — the operator picked the question; there is no list
    to size.
  * the fan-out — one analyst, dispatched once.

`synthesis.md` WAS ON THAT LIST AND IS NOT ANY MORE. PR #105 reversed it, and the
superseded argument is kept here rather than deleted, because an engineer who
finds only its absence reads the reversal as the defect and reverts a shipped
fix. The old reasoning: §4 makes the synthesis the roll-up of a POOL, so with one
paper the roll-up IS the paper and writing one anyway produces a second document
that can disagree with its only input. What it got wrong is reading one CYCLE as
one POOL. Papers ACCUMULATE and the synthesis is REPLACED (Research Standard §4),
so a second minor cycle against the same pool leaves two papers with nothing
rolling them up — and a planner told not to read raw papers wholesale reports "no
synthesis" and plans from priors while both papers sit unread. The contract is
`write_minor.md` line 13, the work happens in its Stage 3 SYNTHESIZE, and
`tests/unit/test_research_minor.py::test_the_minor_cycle_writes_a_SYNTHESIS` pins
it in the opposite direction from the bullet this replaced.

WHAT IS DELIBERATELY PRESENT. Every §3 obligation that makes a paper
trustworthy on its own: the currency header and its parseable revalidation
interval, per-claim confidence marking, the source floor and the count rule,
and the honest-boundary analysis. Those are per-PAPER rigor; they have nothing
to do with how many papers there are. The paper this produces is a §3 paper or
it is not shippable.

DEFERRED, AND NAMED RATHER THAN LEFT SILENT: `write_minor.md`'s RULES footer is
the FOURTH near-copy of one block across the research family (`write.md`,
`verify.md`, `refresh.md`). `temporal_standard.md` §10.1 rule 3 puts the
promotion threshold at more than one consumer, so that threshold was already
crossed before this file existed — but the remedy is a family-wide migration
that rewrites three prompts this workflow does not own, and the four copies have
already drifted, so unifying them changes what three live workflows receive.
Placed as `candidates.md` C-067 rather than done here or dropped.
"""

from __future__ import annotations

from ... import routing

from pathlib import Path

from .. import research_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

# ITS OWN KEY, NOT `research`. The full cycle's `research` key is opus because
# that run authors a synthesis over a pool it also orchestrated. This run
# authors nothing: it dispatches ONE research-analyst — which pins opus in its
# own frontmatter and is unaffected by this key — then commits and opens a PR.
# That is the same pure-orchestration shape `build-draft-minor` already runs at
# sonnet. Sharing `research` would tie the cheap shape's cost to the expensive
# one, which is the entire thing this workflow exists to avoid.
MODEL_KEY = "research-write-minor"
WORKFLOW_KEY = "research-write-minor"   # NOT MODEL_KEY — see run_claude's docstring.
                                       # Added on the merge with Phase 6, which made
                                       # `workflow_key` a required keyword: this child was
                                       # written before that gate existed, so the two landed
                                       # correct in isolation and broken together.

# KEYED BY WORKFLOW, NOT BY MODEL — the same discipline `research_write`
# documents at length. The value is an ESTIMATE and is labelled as one in
# config.yaml; nothing has measured this workflow yet.
MAX_TURNS = act.max_turns(WORKFLOW_KEY)

COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE


def run_write_minor(*, research_dir: Path, repo_root: Path, worktree: Path,
                    context: str = "", pr_number: str | None = None,
                    verbose: bool = False) -> str:
    """Research one TOPIC, write one paper and the synthesis, submit. Returns the PR URL."""
    pool = act.in_worktree(research_dir, repo_root, worktree)
    currency, _due = act.paper_currency(pool)

    # `upstream_block` is kept and the ALTITUDE fragments are not, and the two
    # decisions are not in tension. The fragments decide whether a run also
    # MAINTAINS `candidates.md` and `direction.md` — the product pool's triage
    # queues, which `plan-sprint` consumes. Wiring the scaled-down shape into
    # the surface that steers the whole product is precisely the coupling this
    # workflow should not have. `upstream_block` is the opposite: a read-only
    # POINTER at what the product pool already settled, which stops this run
    # re-deriving a settled answer. It returns "" at product altitude by itself.
    #
    # ITS TWO DIRECTIVES ARE SUPPLIED, NOT DEFAULTED, because the defaults name
    # `research_write`'s stages — "before you SIZE", "your sizing in Stage 2" —
    # and this cycle HAS no sizing stage. Left defaulted, the injected pointer
    # ordered a sizing assessment two paragraphs after this workflow's own prompt
    # forbids writing one, and a contradiction inside one prompt is resolved by
    # the model rather than by us. Reachable today: this repo's product pool has
    # a synthesis, so any component-altitude minor run renders this block.
    blocks = [b for b in (
        context,
        act.upstream_block(
            pool, worktree,
            read_directive="READ THIS IN STAGE 1, BEFORE YOU RESEARCH",
            coverage_directive=(
                "Your paper must state which part of its question upstream "
                "already covers, and cite the upstream paper rather than "
                "re-deriving it."),
        ),
        # Returns "" at component altitude, which is where this cycle almost
        # always runs — wired anyway so a PRODUCT-altitude minor run is not the
        # one arm that silently loses the feature pools.
        act.component_pools_block(pool, worktree),
        currency,
    ) if b]

    values = {
        # The path the MODEL is given must be the one it can actually write to.
        # `pool` is `research_dir` re-anchored to this run's worktree; handing over
        # the un-anchored `research_dir` pointed two consecutive runs (#84, #86) at
        # the MAIN CHECKOUT, and both were caught only by a pre-commit `git status`.
        "RESEARCH_DIR": str(pool),
        "CONTEXT_BLOCK": "\n\n".join(blocks),
        "SUBMIT_PROMPT": act.submit_prompt(pr_number, f"research-minor: {research_dir}"),
        "RESEARCH_STAGE_1_VERIFY_AND_DISCOVER": act.shared_prompt("research_stage_1_verify_and_discover"),
        "STAGE_ORDER_SKIPPED_MARKER": act.shared_prompt("stage_order_skipped_marker"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }
    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / "write_minor.md"), values,
                   opaque=frozenset({"CONTEXT_BLOCK"})),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY, completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree, max_turns=MAX_TURNS, verbose=verbose,
    )
    from ...assistant_activities import extract_pr_url
    url = extract_pr_url(output)
    if not url:
        raise RuntimeError(
            "research-write-minor produced no PR URL — cannot hand off to verify. "
            "The run must open (or update) a PR and print its URL as its final line."
        )
    return url
