"""The plan parent — Layer 1 orchestration for the planning family.

A parent calls no model. It decides IF, WHEN and WHAT to call, and holds no
process code. Every branch is a pure decision from `routing`; every side effect
is an activity or a child workflow.

    plan-sprint  ->  research(per NEW component)  ->  review-pr  ->  [one loop-back]
                       write -> verify

WHY THIS EXISTS AT ALL. `plan-sprint` shipped and ran twice with no parent, so
its output reached the operator UNJUDGED — and it is the only autonomous run
authorised to write `sprint.md`, the file the governing rule exists to protect.
Every other family has its judge: build is draft -> refine -> review-pr,
research is write -> verify -> review-pr. This one had nothing, which made it
the single place where `author != judge` was not being honoured.

`plan-sprint` could not simply call `review-pr` itself: a parent calls no model
and `plan-sprint` calls one. Bolting the judge onto the child would have made it
a model-calling orchestrator, which is the exact shape decomposition removes.

WHY review-pr AND NOT A DEDICATED REVIEWER. `review-pr` is a SHARED child — it
already takes `--type planning` with its own criteria, and it stays
independently dispatchable against any returned PR. Child-ness is a call-graph
property, not a location.

WHY THE RESEARCH CHILDREN AND NOT THE RESEARCH PARENT. `run_research` is itself
a parent: it establishes its own worktree and opens its own PR. Calling it here
would give one flow two worktrees and two PRs, and its verify loop would gate a
sprint triage that was already fine. Calling `research_write` and
`research_verify` directly keeps ONE worktree and ONE PR, and reuses the same
children the research parent uses. Same children, two callers.

WHAT IS NOT HERE YET. `plan-phase` — writing the phase doc for a new sprint
section — is being ported from `plan-revision.sh`. It slots between research and
review-pr and needs no change to the shape below.
"""

from __future__ import annotations

from pathlib import Path

from .. import plan_activities as act
from ... import routing
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType
from ...research.research_write import research_write_workflow as write
from ...research.research_verify import research_verify_workflow as verify
from ..plan_sprint import plan_sprint_workflow as sprint


def run_plan_master(*, repo_root: Path, worktree_name: str, sprint_path: Path,
                    candidates_path: Path, research_dir: Path,
                    pr_number: str | None = None, repo_target: str | None = None,
                    verbose: bool = False) -> tuple[str, routing.Verdict, int, list[str]]:
    """Triage, judge, and route on the verdict.

    Returns (pr_url, verdict, loops_used, notes). A HOLD is a RESULT, not a
    failure — the caller branches on the verdict, which is the entire point of
    returning a typed value rather than an exit code.
    """
    notes: list[str] = []

    # ISOLATION IS ESTABLISHED ONCE, HERE. The child receives the path and never
    # creates one — two actors creating the same named worktree is a
    # `fatal: already exists` that has killed a handoff before.
    ref = f"origin/{act.pr_branch(pr_number, repo_root)}" if pr_number else "HEAD"
    worktree = act.worktree_add(repo_root, worktree_name, ref)

    # --- Step 1: TRIAGE ----------------------------------------------------
    # The PR URL is both the handoff and the child's completion contract; the
    # child raises if it produced none AND if it left any candidate untriaged,
    # so `exit 0` cannot mean unfinished.
    pr_url = sprint.run_plan_sprint(
        repo_root=repo_root, worktree=worktree, sprint_path=sprint_path,
        candidates_path=candidates_path, research_dir=research_dir,
        pr_number=pr_number, verbose=verbose,
    )
    pr = routing.pr_number_from_url(pr_url)

    # --- Step 2: RESEARCH each NEW component -------------------------------
    # Read from the diff, never asked of the triage child: the parent must not
    # trust an account when the artifact is right there. An edited section shows
    # no added heading, so a component is researched only when it is genuinely
    # new — researching one because its prose moved spends a full cycle on
    # nothing.
    #
    # The research CHILDREN are called, not the research PARENT. That parent
    # would establish a second worktree and open a second PR, and its verify
    # loop would then gate a sprint triage that was already fine. Same children,
    # two callers — which is the whole point of child-ness being a call-graph
    # property rather than a location.
    for section in act.new_sprint_sections(worktree, str(sprint_path.relative_to(repo_root))):
        notes.append(f"New component `{section}` — researching before it is planned.")
        # NOT `research_dir` — that parameter is the PRODUCT pool plan-sprint
        # triages, and rebinding it here would hand the loop-back below the
        # wrong pool. A shadowed parameter is a silent wrong-argument bug.
        component_pool = act.component_dir(worktree, section) / "research"
        component_pool.mkdir(parents=True, exist_ok=True)

        # The sprint section IS the brief. It states the milestones, and the
        # research child's Stage 1 already reads the destination's planning docs
        # to drive its topics — so a hand-written task file would be restating
        # what it is about to read.
        context = (
            f"A new sprint section `{section}` was just added to "
            f"{sprint_path.relative_to(repo_root)} and has no phase doc yet. "
            f"Research it BEFORE it is planned. Read that section first — it is "
            f"your brief, and its milestones are what this pool must inform."
        )
        write.run_write(research_dir=component_pool, repo_root=repo_root,
                        worktree=worktree, context=context, pr_number=pr,
                        verbose=verbose)
        verify.run_verify(research_dir=component_pool, pr_number=pr,
                          repo_root=repo_root, worktree=worktree, verbose=verbose)

    # --- Step 3: DISPOSITION, with one bounded loop-back -------------------
    loops = 0
    verdict = _dispose(pr, repo_root, repo_target, notes, verbose)

    while routing.should_loop_back(verdict, loops):
        loops += 1
        notes.append("HOLD (redispatch): the runway closes with a scoped fix. "
                     "Looping back ONCE — this is the last automated pass.")
        # A correction pass, not a fresh triage: every candidate already carries
        # a decision, and re-triaging them would re-litigate rulings the first
        # pass made rather than closing the runway the reviewer wrote.
        sprint.run_plan_sprint(
            repo_root=repo_root, worktree=worktree, sprint_path=sprint_path,
            candidates_path=candidates_path, research_dir=research_dir,
            pr_number=pr, correction_pass=True, verbose=verbose,
        )
        verdict = _dispose(pr, repo_root, repo_target, notes, verbose)

    if verdict is routing.Verdict.HOLD_NEEDS_ASSISTANCE:
        notes.append("review-pr found at least one item only a human can rule on. No "
                     "loop-back was attempted: more passes cannot produce a human decision.")
    elif verdict is routing.Verdict.HOLD_REDISPATCH:
        notes.append("The automated loop is SPENT — one loop-back is the cap, because "
                     "passes beyond it produce justification rather than correction.")

    # A planning PR ALWAYS needs the operator, even at MERGE. `direction.md`
    # rows are by construction rulings no automated pass can make, and the
    # sprint plan is the operator's own surface. MERGE here means "the judge
    # found nothing to correct", never "merge it unattended".
    if verdict is routing.Verdict.MERGE:
        notes.append("MERGE means the judge found nothing to correct. It does NOT mean "
                     "merge unattended: any direction.md rows are rulings only the "
                     "operator can make, and the sprint plan is the operator's surface.")

    return pr_url, verdict, loops, notes


def _dispose(pr: str, repo_root: Path, repo_target: str | None,
             notes: list[str], verbose: bool) -> routing.Verdict:
    """One disposition pass, judged against the PLANNING criteria.

    No CI wait: this family changes markdown only, so there is no build to
    settle. Adding one would spend a timeout per pass to observe nothing.
    """
    result = review_pr.run_review(
        ReviewInput(pr_number=pr, repo_target=repo_target,
                    review_type=ReviewType.PLANNING, verbose=verbose),
        repo_root,
    )
    notes.extend(result.notes)
    return result.verdict
