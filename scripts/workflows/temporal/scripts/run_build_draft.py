"""Kickoff entrypoint for build-draft — and the FAMILY RULING for all six.

Lives in scripts/ because it is a launch concern, not a workflow concern. When
the Temporal path exists this is replaced by a client that starts the workflow
on a task queue; the workflow module itself does not change.

════════════════════════════════════════════════════════════════════════════════
THE FAMILY RULING — ONE ruling, made before the first adapter was written
════════════════════════════════════════════════════════════════════════════════

Workflow Decomposition Phase 3 adds SIX runner/shim pairs in one sitting, from
one template, by one run. That is the exact population `Family alignment`'s blind
trial scored at **κ = 0.000** when ruled pair-by-pair AFTERWARDS, which is why
that phase moved ruling to per-FAMILY granularity and why this ruling exists
here, once, rather than six times in six diffs. No guard in this repo can see
duplication in a Python runner — the prompt-duplication ratchet's population is
`ASSISTANT.rglob("prompts/*.md")` and `FAMILY_RULINGS` is keyed on prompt-fragment
stems — so this is prose a reviewer applies, and a green suite is NOT coverage
for it.

INVARIANT ACROSS ALL SIX. A deviation in any of these is a defect, not a variant:

  1. The RUNNER owns the CLI contract and the SHIM is thin. The shim resolves
     the interpreter and passes every argument through untouched. A shim that
     validates, defaults or reorders arguments creates a second definition of
     the contract, and two definitions diverge silently.
  2. IDENTITY ARRIVES FROM OUTSIDE. `add_identity_arguments(parser)` declares
     `--run-id`/`--writer`; `resolve_identity(argv)` reads them, inline, AFTER
     any `--dry-run` early return. No entrypoint names `mint_run_id`.
  3. THE REPO ROOT IS RESOLVED, NEVER ASSUMED. `preflight(--repo)` — never
     `Path.cwd()`. Six of seven V2 entrypoints once dropped this and scattered
     worktrees and logs into whatever subdirectory the operator was standing in.
  4. THE BOUNDARY IS ONE SHAPE: `RunContext.build(...)` -> `ctx.echo()` ->
     `journal.open_run_bag(...)`, all inside a `try` whose `except RuntimeError`
     is `return refuse(exc)`. The echo precedes the bag; the bag precedes the
     first side effect.
  5. THE RUNNER ESTABLISHES ISOLATION, because the parent is not there to.
     `act.base_ref(pr, repo_root)` then `act.worktree_add(repo_root,
     ctx.worktree_name, ref)`, and the resulting `Path` is handed to the core
     function. This is the ONE structural difference between the standalone path
     and the parent-driven path, and it is unavoidable: a parent establishes
     isolation once for a whole chain (`build_workflow.run_build`), so a child
     invoked alone has to do for itself what the parent would have done for it.
     The NAME still comes from the context — nothing assembles it here.
  6. EXIT-CODE TRANSLATION, NOT RESULT REPLACEMENT. The runner turns the core
     function's returned object into `$?`; it does not replace the object. A
     child that starts returning a string because "the shell only needs a
     message" has broken its parent. `0` means the completion contract was met;
     `1` means a layer raised, and its message is printed unchanged.
  7. STREAMS ARE SPLIT BY AUDIENCE. stdout carries the RESULT somebody may pipe
     — for these six, the PR URL and nothing else. stderr carries narration: the
     banner, the context echo, the minted-run-id line, every refusal.
  8. NOTHING BLOCKS ON A HUMAN. No `input()`, no prompt, no confirmation. Under a
     parent a waiting child looks like a stall rather than a question.
  9. `--dry-run` ON EVERY ONE, and it rehearses by printing
     `RunContext.for_dry_run(...).render()` — the same object and the same
     rendering the live path echoes. Nothing minted, no bag, no worktree, no
     model. It is also how requirement 5's demonstration is run cheaply for
     children whose real work costs an hour of model time.
 10. THE SHIM'S USAGE BLOCK NAMES ITSELF. Three earlier shims shipped usage text
     naming the script they were cloned from; `test_shim_usage_names_itself.py`
     holds it for all seventeen.

LEGITIMATELY PER-CHILD, each carrying its own `differs from <sibling> because
<reason>` line in ITS module docstring — and nowhere else:

  * `run_build_refine` / `run_build_refine_minor` / `run_research_refine` make
    `--pr` REQUIRED. Their core functions take `pr_number: str`, not optional: a
    refine pass corrects an existing PR and has nothing to open.
  * THIS file passes `prefer_repo`; `run_build_draft_minor` does not, because
    only the major tier's core function accepts it.
  * The research pair declares its pool through `RepoPathParser.add_repo_path`;
    the build four use plain `add_argument`. A research pool is an in-repo path
    and must be contained; a build task source is deliberately read from wherever
    the operator wrote it, routinely /tmp.

WHAT THE RULING DELIBERATELY DOES NOT DO — THE FIVE DIVERGENCE SURFACES, ruled
once here rather than inherited six times from whichever sibling was cloned:

  * VERBOSITY: `--verbose` stays an EXPLICIT parameter. No TTY detection, no
    implicit mode switch of any kind. The run-context echo is unconditional and
    is printed by the process that CONSTRUCTED the context — a standalone child
    constructs its own, so it echoes; there is no suppression flag, and adding
    one is the shape Phase 4's ruling rejected.
  * EXIT CODES: see invariant 6. A child whose failure is a returned object and
    whose runner exits `0` looks fine to every caller that is not a parent.
  * INTERACTIVE PROMPTS: see invariant 8.
  * STREAM DISCIPLINE: see invariant 7. Mixing them is unusable in a shell and
    merely noisy under a parent, which is why the defect survives.
  * WORKING DIRECTORY: see invariant 3.

THIS RULING IS SURFACED, NOT FILED. `finding-routing.md` §7 gives a producing run
the surfacing and `review-pr` the filing; the two amendments it proposes —
against `workflow-scripts.md` § *Composition* (the five divergences) and
§ *Required Features* (the invariants) — are in this PR's body, as two separate
items with two anchors. Nothing here edits a standard.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight import preflight, refuse  # noqa: E402
from dispatch_identity import add_identity_arguments, resolve_identity  # noqa: E402
from dispatch_context import RunContext  # noqa: E402

from modules.journal import journal_activities as journal  # noqa: E402
from modules.assistant import assistant_activities as act  # noqa: E402
from modules.assistant.build.build_activities import path_for_the_model, task_text  # noqa: E402
from modules.assistant.build.build_inputs import BuildInput  # noqa: E402
from modules.assistant.build.build_draft.build_draft_workflow import run_draft  # noqa: E402

BANNER = "=" * 64

#: The `models:` and turn-cap key, and the stem `worktree_name` is built from.
#: It matches `build_draft_workflow.WORKFLOW_KEY`; a rename moves both plus the
#: two `config.yaml` keys, or the workflow becomes silently unlaunchable.
WORKFLOW_KEY = "build-draft"


def parse_args(argv: list[str] | None = None) -> tuple[BuildInput, bool]:
    parser = argparse.ArgumentParser(
        prog="build-draft",
        description="Write the change and open an UNREVIEWED PR. No review pass "
                    "runs — this is build's first child, invoked alone.")
    parser.add_argument("description", nargs="?", help="what to build")
    parser.add_argument("--task-file", help="read the task from a file (bypasses shell parsing)")
    parser.add_argument("--phase", dest="plan_path",
                        help="path to a plan doc — extract success criteria and verify against them")
    parser.add_argument("--pr", dest="pr_number", help="update an existing PR instead of opening one")
    parser.add_argument("--repo", dest="repo_target", help="target repo (never derived from cwd)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="state what this run derived; no model, no worktree, no spend")
    add_identity_arguments(parser)
    args = parser.parse_args(argv)

    # `BuildInput` validates the TWO task-source rules and raises with a readable
    # message; routing it through argparse's error path keeps the CLI contract in
    # one place. The rule itself is stated once, in `BuildInput.__post_init__`.
    try:
        task = BuildInput(
            description=args.description,
            task_file=args.task_file,
            plan_path=args.plan_path,
            pr_number=args.pr_number,
            repo_target=args.repo_target,
            verbose=args.verbose,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return task, args.dry_run


def main(argv: list[str] | None = None) -> int:
    task, dry_run = parse_args(argv)

    try:
        repo_root = preflight(task.repo_target)
    except RuntimeError as exc:
        # Nothing has been created yet — that is the point of preflight.
        return refuse(exc)

    if dry_run:
        # BEFORE `resolve_identity`, deliberately: a rehearsal states "nothing
        # invoked, nothing posted", and minting a name and announcing it would
        # make that false. Same exemption that keeps a dry run from opening a bag.
        print(f"{BANNER}\n  DRY RUN — nothing invoked, nothing posted\n{BANNER}")
        # `target=None`: a build is pointed at a task, not at a component.
        print(RunContext.for_dry_run(repo_root=repo_root, workflow_key=WORKFLOW_KEY,
                                     pr_number=task.pr_number, target=None).render())
        return 0

    try:
        # Invariant 4 — the boundary, in one shape, before anything is created.
        ctx = RunContext.build(identity=resolve_identity(argv), repo_root=repo_root,
                               workflow_key=WORKFLOW_KEY, pr_number=task.pr_number)
        ctx.echo()
        journal.open_run_bag(run_id=ctx.run_id, writer=ctx.writer,
                             repo_root=ctx.repo_root,
                             workflow_key=ctx.workflow_key,
                             worktree_name=ctx.worktree_name,
                             journal_root=ctx.journal_root)

        # Invariant 5 — isolation, which the parent would otherwise have
        # established for this child. The NAME is the context's field.
        ref = act.base_ref(task.pr_number, repo_root)
        worktree = act.worktree_add(repo_root, ctx.worktree_name, ref)

        # Read BEFORE the child runs, as the parent does: a `gh` failure then
        # costs a dispatch that has produced nothing, rather than sitting between
        # a completed multi-hour child and the PR it opened.
        slug = act.repo_slug(repo_root)

        pr_url = run_draft(
            description=task_text(task, repo_root), repo_root=repo_root,
            worktree=worktree, prefer_repo=slug, pr_number=task.pr_number,
            # ANCHORED FOR THE MODEL, never the raw operator string — the model
            # reads it standing inside the worktree.
            plan_path=path_for_the_model(repo_root, task.plan_path),
            verbose=task.verbose,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        # These carry operator-facing recovery instructions from the layer that
        # knew what failed. `refuse` prints them unchanged.
        return refuse(exc)

    # Invariant 7 — the banner is narration and goes to stderr; the PR URL is the
    # result and is the only thing on stdout, so `$(./build_draft.sh …)` is a URL.
    print(f"\n{BANNER}\n  BUILD-DRAFT COMPLETE — the PR is UNREVIEWED\n{BANNER}",
          file=sys.stderr)
    print("  refine it with:  ./build_refine.sh --pr <n> <the same task>\n"
          "  clean up with :  /cleanup-merged-worktrees", file=sys.stderr)
    print(pr_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
