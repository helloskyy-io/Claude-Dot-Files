"""plan-revision — revise EXISTING planning docs and open a reviewed PR.

A RE-HOST of `scripts/workflows/plan-revision.sh`, not a redesign. Same six
stages, same prompt text, same CLI contract. The prompts in `prompts/` were
GENERATED from the bash script rather than retyped, and
`test_plan_revision_v1_parity.py` re-extracts them on every run and asserts byte
equality — because the failure this port had to avoid is documented and
specific: an earlier port lifted the `PROMPT="..."` strings, missed the
heredoc-captured variables interpolated INTO them, and shipped ~935-byte prompts
that said "follow all 8 stages" with the stages absent. Every run exited 0.

Its scope is broader than its neighbours': roadmaps, requirements, ADRs and
epics, not only phase docs. That is why the name stays `plan_revision` — a
narrower one would describe less than it does.

Folder holds only this file (§10.1 rule 6); the family's shared I/O is promoted
to `plan_activities`.

THIS WORKFLOW CALLS A MODEL, SO IT IS A CHILD. It receives a worktree and never
creates one — two actors creating the same named worktree is a
`fatal: already exists` that has killed a handoff before. It calls no other
workflow. A parent will orchestrate it; wiring it into `plan_project` is
deliberately NOT part of this port.

NOT IDEMPOTENT (§7.1): it pushes commits and opens PRs. Under Temporal a retry
is a NEW ATTEMPT, not a replay.
"""

from __future__ import annotations

from ... import routing

import re
from pathlib import Path

from .. import plan_activities as act

_HERE = Path(__file__).resolve().parent
PROMPTS = _HERE / "prompts"

MODEL_KEY = "plan-revision"
WORKFLOW_KEY = "plan-revision"   # the run log's per-workflow bin; see run_log.py
MAX_TURNS_KEY = WORKFLOW_KEY

# `(pull|issues)`, verbatim from V1, and the `issues` half is load-bearing rather
# than defensive: Stage 1 can legitimately STOP (research required, or evidence
# structurally faulty) and file an issue, and on that path the ISSUE is the
# deliverable. Narrowing this to `pull` would turn a correct, cheap stop into a
# reported failure and invite someone to re-dispatch past the very gate that
# fired.
COMPLETION_PATTERN = routing.PR_OR_ISSUE_COMPLETION_ERE

_STOP_ISSUE = re.compile(r"https://github\.com/[^\s)]+/issues/[0-9]+")


def context_block(context: str, evidence: str = "") -> str:
    """V1's CONTEXT_BLOCK: delimited when there is context, EMPTY when there is not.

    Empty means empty, not an empty pair of delimiters. An
    `--- additional context ---` header with nothing beneath it reads to the
    model as context that was meant to be there and went missing, which is worse
    than no header at all.
    """
    blocks = []
    if context:
        blocks.append(f"--- additional context ---\n{context}\n--- end additional context ---")
    # The evidence pointer rides here rather than in a new placeholder: the
    # wrapper prompts are parity-locked, and "what this run may read" is what
    # this block is for. Rendered even with no operator context — a planning run
    # that was given no brief needs the pointer MORE, not less.
    if evidence:
        blocks.append(evidence)
    return "\n" + "\n\n".join(blocks) + "\n" if blocks else ""


def completion_url(output: str) -> str | None:
    """The run's completion signal: its PR URL, or a STOP's issue URL.

    WHICHEVER KIND APPEARS LAST WINS, because both prompt paths mandate the same
    thing and the position is therefore the signal, not the kind: Stage 6 says
    "as your FINAL line, print the PR URL", and the STOP path says "print the
    issue URL as your FINAL line — it is the STOP's completion signal".

    A rule that always preferred a PR would mis-report a genuine STOP that
    happened to quote any PR URL earlier — a planning run reads docs full of
    them — as a completed plan, sending the operator to an unrelated PR and
    inviting a re-dispatch straight past the gate that just fired. Position gets
    the mirror case right for free: a normal run's PR body cites `Closes <issue
    URL>` while it is being written, and the mandated PR line still comes after
    it.

    Ties go to the PR: `extract_pr_url` is the shared spelling every sibling
    uses for the ordinary path, and the ordinary path is the PR.
    """
    pr = act.extract_pr_url(output)
    issues = _STOP_ISSUE.findall(output)
    if not issues:
        return pr
    issue = issues[-1]
    if not pr:
        return issue
    # rfind, not the match objects: `extract_pr_url` is shared and returns a
    # string, so the position is recovered here rather than reaching around it.
    return pr if output.rfind(pr) >= output.rfind(issue) else issue


def run_plan_revision(*, description: str, repo_root: Path, worktree: Path,
                      context: str = "", pr_number: str | None = None,
                      verbose: bool = False) -> str:
    """Revise the planning docs. Returns the completion URL (PR, or STOP issue)."""
    # Two prompts, two paths: updating an existing PR is a different task from
    # opening one, and the bash original branched the same way.
    wrapper = "update_pr.md" if pr_number else "new_branch.md"

    values = {
        "DESCRIPTION": description,
        # THE WORKTREE, not the repo, and this was `repo_root` until the same
        # defect was caught one caller over. `evidence_block` enumerates the pools
        # and COUNTS their papers; anchored at the repo it describes the main
        # checkout while the run reads and writes somewhere else, so a pool this
        # branch added is invisible and every count is the wrong branch's. Not a
        # refactor of this workflow — the identical one-argument fix its sibling
        # took, applied where the function's own parameter is now named `tree`.
        "CONTEXT_BLOCK": context_block(context, act.evidence_block(worktree)),
        # The two bodies V1 interpolates from heredocs. They are the ~23kB that a
        # prior port dropped; they are loaded here, and their arrival intact is
        # asserted by the parity suite rather than assumed.
        "STAGES_1_TO_5": act.load_prompt(PROMPTS / "stages_1_to_5.md"),
        # LOCAL, not the promoted `prompts/rules.md`. The shared file carries the
        # BUILD rules; this workflow's are planning rules ("do not modify code,
        # scripts, or configuration files"). Same placeholder name in V1, and
        # different text — reaching for the shared one would silently hand a
        # planning run the code-change ruleset.
        "RULES": act.load_prompt(PROMPTS / "rules.md"),
        "AGENTS_HAVE_NO_SHELL": act.shared_prompt("agents_have_no_shell"),
        "GITIGNORE_COLLISION_CHECK": act.shared_prompt("gitignore_collision_check"),
        "ORCHESTRATOR_EXECUTES_AGENTS_READ": act.shared_prompt("orchestrator_executes_agents_read"),
        "STAGE_ORDER_IS_MANDATORY": act.shared_prompt("stage_order_is_mandatory"),
        "TELL_EACH_AGENT_WHAT_IT_CAN_RUN": act.shared_prompt("tell_each_agent_what_it_can_run"),
        "VERIFICATION_IS_BY_FETCH": act.shared_prompt("verification_is_by_fetch"),
        "VERIFY_THE_TASKS_ASSERTED_FACTS": act.shared_prompt("verify_the_tasks_asserted_facts"),
        "DECISION_LOG_AND_REFLECTION": act.shared_prompt("decision_log_and_reflection"),
        "HEADLESS_EXECUTION_GUARD": act.shared_prompt("headless_execution_guard"),
    }
    if pr_number:
        values |= {"PR_NUMBER": pr_number, "PR_BRANCH": act.pr_branch(pr_number, repo_root)}

    output = act.run_claude(
        act.render(act.load_prompt(PROMPTS / wrapper), values,
                   opaque=frozenset({"CONTEXT_BLOCK", "DESCRIPTION"})),
        model_key=MODEL_KEY, workflow_key=WORKFLOW_KEY,
        completion_pattern=COMPLETION_PATTERN,
        repo_root=repo_root, worktree=worktree,
        max_turns=act.max_turns(MAX_TURNS_KEY),
        verbose=verbose,
    )

    url = completion_url(output)
    if not url:
        raise RuntimeError(
            "plan-revision produced neither a PR URL nor a STOP issue URL. The run "
            "did not finish, whatever its exit code says — the planning docs in the "
            "worktree are UNSUBMITTED and unreviewed. Inspect the worktree before "
            "re-dispatching; the work may be there."
        )
    return url
