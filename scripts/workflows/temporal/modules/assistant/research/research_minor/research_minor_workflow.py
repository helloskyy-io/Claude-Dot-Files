"""The research-minor parent.

    write-minor  ->  verify  ->  review-pr  ->  [one loop-back]  ->  done

THE SAME SEQUENCE AS `research`, with a lighter first child. Same loop-back
bound, same disposition handling, same completion contract. A parent calls no
model; every branch is a pure decision, every side effect is a child or an
activity.

WHY IT IS A SIBLING RATHER THAN A FLAG ON `research`. A portfolio-direction
question cost ~3.5 hours, five papers and a synthesis — "mass overkill", in the
operator's words. The sizing rubric was not the cause: Research Standard §2
already sizes Small at 1-2 topics, and a correctly-sized Small run STILL emits
`topics.md`, a fan-out, a synthesis and a verify pass over all of it. What was
missing is a shape with no pool in it at all, and that is a different
composition of the same children — not a mode.

WHAT CHANGES AND WHAT DOES NOT, stated because the ratio is the whole design:

  * CHANGED — exactly one thing: the first child. `research_write_minor`
    replaces `research_write`.
  * UNCHANGED — `research_verify` (reused, see below) and `research-critic`
    (untouched). The critic is the anti-hallucination gate: it fetches every
    cited source and has repeatedly caught fabrications. Dropping to a bare
    deep-research call was considered and the critic is precisely the reason
    not to. A cheaper cycle that skipped verification would be cheaper at the
    only thing worth paying for.

HOW `research_verify` IS REUSED WITHOUT A BEHAVIOURAL FLAG. It already
discovers artifacts from `RESEARCH_DIR` on the filesystem — nothing in its code
reads `synthesis.md` — so a missing synthesis needs no signalling for the
mechanics to work. Its PROMPT is the problem: it asserts "you did not write
this synthesis", which presupposes one exists, and a run reading that against a
directory with none will stall or invent one. Inventing is the exact failure
that child guards against.

So the parent injects a rendered-or-empty block stating the cycle's SHAPE as a
fact — modelled on the `${CORRECTION_NOTE}` this family already renders the
same way. It is a statement about what the parent produced, not a switch that
changes what the child does, and the distinction is load-bearing: a flag that
alters which artifacts a workflow emits is a behavioural branch living inside a
prompt, and prompt branches are where drift lives.
"""

from __future__ import annotations

from pathlib import Path

from .. import research_activities as act
from ..research_write_minor import research_write_minor_workflow as write_minor
from ..research_verify import research_verify_workflow as verify
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType, Verdict
from ...assistant_activities import ci_verdict, repo_slug, wait_for_ci
from ... import routing


MAX_LOOPS = 1


def run_research_minor(*, research_dir: Path, repo_root: Path, worktree_name: str,
                       context: str = "", pr_number: str | None = None,
                       verbose: bool = False) -> dict:
    """Produce one paper, verify, disposition. Returns a typed result."""
    notes: list[str] = []

    # Isolation once, at the parent. Children receive the path.
    ref = act.base_ref(pr_number, repo_root)
    worktree = act.worktree_add(repo_root, worktree_name, ref)

    # Read BEFORE the child, so a `gh` failure costs a dispatch that has
    # produced nothing rather than one that has already written a paper.
    slug = repo_slug(repo_root)

    pr_url = write_minor.run_write_minor(
        research_dir=research_dir, repo_root=repo_root, worktree=worktree,
        context=context, pr_number=pr_number, verbose=verbose,
    )
    # THROUGH THE OWNER, not a string split. `rstrip("/").rsplit("/", 1)[-1]`
    # is the PR-URL parse with NO validation whatsoever — it returns the last
    # path segment of whatever it is handed, so a child that printed a bare
    # sentence yields a word and it reaches `gh` as a PR number.
    pr = routing.pr_number_from_url(pr_url, expected_repo=slug)

    loops = 0
    verdict = _verify_then_dispose(research_dir, pr, repo_root, worktree,
                                   notes, verbose, correction=False)

    # ONE loop-back, the same bound the full cycle uses. Self-correction
    # plateaus at 3-5 passes; past it the model justifies rather than corrects.
    # Counting across the pipeline:
    # verify=1 . review-pr=2 . [loop] verify=3 . review-pr=4.
    while verdict is Verdict.HOLD_REDISPATCH and loops < MAX_LOOPS:
        loops += 1
        notes.append("HOLD (redispatch): looping back ONCE — the last automated pass.")
        verdict = _verify_then_dispose(research_dir, pr, repo_root, worktree,
                                       notes, verbose, correction=True)

    if verdict is Verdict.HOLD_NEEDS_ASSISTANCE:
        # THE LOOP DECISION AND NOTHING ELSE. Wiring the CI gate above gave this
        # parent a SECOND path to this verdict, and the gate writes its own cause
        # ending "review-pr was NOT dispatched" — so the old sentence here,
        # "review-pr found an item only a human can rule on", now lands directly
        # beneath a note saying review-pr never ran. That exact contradiction was
        # measured on PR #124 in the build family, and it cost a log sweep to tell
        # UNREVIEWED from reviewed-and-held. The layer that DETECTS a condition
        # reports it; this layer detects neither.
        notes.append("No loop-back was attempted: more passes cannot produce a "
                     "human decision. The cause is in the note above.")
    elif verdict is Verdict.HOLD_REDISPATCH:
        notes.append("The automated loop is SPENT — one loop-back is the cap.")

    return {"pr_number": pr, "pr_url": pr_url, "verdict": verdict,
            "loops_used": loops, "notes": notes}


# THE MAP LINE IS THE PARENT'S, because the child's write boundary makes it
# unreachable. `write_minor.md` confines the analyst to `raw/` -- correct in
# spirit, the researcher researches -- but that makes `docs/file_structure.txt`,
# which CLAUDE.md calls authoritative, structurally unwritable by the ONLY run
# that knows a new component directory now exists. Every other folder in that
# map arrived via a build or plan run. The parent already commits the paper; it
# adds the map line the same way rather than widening the child.
#
# ⟨NOT IMPLEMENTED -- surfaced by PR #84 and recorded here so the next change to
# this parent has it in view. Doing it needs the map's annotation convention,
# which is a format decision, not a mechanical insert.⟩


def _verify_then_dispose(research_dir: Path, pr: str, repo_root: Path,
                         worktree: Path, notes: list[str], verbose: bool,
                         *, correction: bool) -> Verdict:
    # NO CYCLE-SHAPE SIGNAL IS PASSED, and the pair that used to be here was
    # deleted rather than corrected. Both arms rested on *a minor cycle writes no
    # synthesis*, which stopped being true when `research_write_minor` gained
    # Stage 3 on 2026-08-17: `synthesis.md` now always exists by the time verify
    # runs, so one arm was unreachable and the other told every run the synthesis
    # came from an earlier cycle and did not cover this one. Issue #107.
    #
    # `research_verify` discovers artifacts from the filesystem and reads no flag,
    # so there is nothing left to signal — which is why deleting beat repairing.
    verify.run_verify(
        research_dir=research_dir, pr_number=pr, repo_root=repo_root,
        worktree=worktree, correction_pass=correction, verbose=verbose,
    )
    # --- THE GATE: the parent reads the verdict, so MERGE is unreachable on red
    # THE SAME CASCADE THE BUILD PARENTS RUN — `routing.ci_gate`, pure, six
    # consumers. It was absent from this family because it lived under `build/`
    # and reaching it from here would have been a layering inversion, so this
    # parent dispatched `review-pr` with the CI verdict never read and could
    # return MERGE on a red tree.
    #
    # A MARKDOWN-ONLY PR IS NOT AN UNGATED ONE. This repo's `tests.yml` carries
    # no `paths:` filter by deliberate choice, and the suite greps prompts and
    # docs, so a research edit can and does turn the tree red.
    #
    # `repo_root=repo_root` ON BOTH, and the parameter is REQUIRED rather than
    # merely conventional: omitting it used to make every read degrade to "this
    # repo declares no gate", so the gate was present and forgave everything.
    # That omission was live in `build_minor` until PR #124; the default was
    # dropped on 2026-08-20 so the degrade path no longer exists.
    wait_for_ci(pr, repo_root=repo_root)
    verdict_state, extra = ci_verdict(pr, repo_root=repo_root)
    hold, gate_notes = routing.ci_gate(verdict_state, extra, pr=pr, repo_target=None)
    notes.extend(gate_notes)
    if hold is not None:
        return hold

    # --type research: candidates are CARGO, not findings. A clean research PR
    # returns MERGE with zero findings, and that is the expected outcome.
    result = review_pr.run_review(
        ReviewInput(pr_number=pr, verbose=verbose, review_type=ReviewType.RESEARCH),
        repo_root,
    )
    notes.extend(result.notes)
    return result.verdict
