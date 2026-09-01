"""What a run WORKED OUT for itself, computed once, said out loud.

WHY THIS EXISTS. A wrong flag fails loudly at parse time. A wrong DERIVATION
produces a plausible wrong run — the workflow competently plans the wrong
component, opens a real pull request, and nothing anywhere goes red. Workflow
Decomposition Phase 4 closes that class, and it does it by making the question
smaller rather than by auditing it: a run has ONE place its derived values come
from, that place is built once at the dispatch boundary, and the run states what
it built before it does anything that costs money.

  `derivation`   — the four things every field on this object must say (in
                   `dispatch_identity`, beside `RunIdentity`, whose fields are
                   the first three a run carries)
  `RunContext`   — the frozen object itself; extends `RunIdentity`
  `.build`       — the boundary constructor, for a run that will actually run
  `.for_dry_run` — the same object for a rehearsal, which mints nothing,
                   resolves no journal root and creates nothing
  `.render`      — the ONE rendering, read by the echo and by every `--dry-run`

THE OBJECT IS THE ENUMERATION, WHICH IS THE WHOLE POINT. The requirement this
replaces asked for a published table of every derived value in the fleet, held
honest by a check that read its population off the tree. That check ran cold and
found there IS no enumerable population of derivations: four marker conventions
returned zero hits across 225 files. A frozen dataclass's fields ARE an
enumerable population — `dataclasses.fields()` returns them by construction — so
a field cannot drift from the enumeration, because it IS the enumeration.

  ⚠ A FIELD EXISTING IS NOT A FIELD BEING DOCUMENTED, and that is why every
  field carries `derivation(...)` metadata and why
  `test_every_context_FIELD_STATES_ITSELF.py` reads it back. Two of the five
  safe-derivation properties — the published algorithm and the stated scope of
  effect — ARE the documentation, so nothing checking it would let this object
  ship nine fields with none.

THE WORKTREE NAME IS THE VALUE THIS WAS BUILT FOR. It reached ELEVEN sites in
THREE spellings — `f"<key>-{int(time.time())}"` at eight, an
`int(__import__('time').time())` variant at two, and an inline argument at one —
and `run_build_minor` had already DRIFTED: `workflow_key="build-minor"` with a
worktree named `build-…`. The fleet has performed exactly this consolidation
once before, on `base_ref`, at the same call sites, and that helper's docstring
records what a hand sweep of eleven sites produces: a fix applied to ten.

WHAT DOES NOT BELONG HERE, because the object becoming a grab-bag is the
failure mode on the other side. The test for a field is *run-scoped and derived
once at the boundary*. A value computed inside the work, from an argument the
work was handed, is not a context field however convenient it would be to
reach — `paper_currency` and `due_papers` are per-pool, and the sub-worktree one
review PASS cuts is per-pass, so neither is here.

AND "PREFER DERIVATION" IS NOT THE RULE THIS OBJECT IMPLIES. Repo identity is
DECLARED (`--repo`, explicitly never derived from the working directory) while
component scope is derived from the path the run was pointed at. Derivation is a
per-value decision with a stated reason. This object changes where a derived
value is computed and recorded, not which values are derived — `workflow_key`
sits here and is declared, and its `derivation` metadata says so.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field, fields
from pathlib import Path

from dispatch_identity import RunIdentity, derivation, resolve_identity
from modules.journal.journal_activities import load_journal_config
from modules.journal.root import resolve_journal_root

__all__ = ["RunContext", "DRY_RUN_RUN_ID"]

# The run id a rehearsal carries. A dry run states "nothing invoked, nothing
# posted", and minting a name would make that false — `resolve_identity`'s own
# docstring carries the same exemption for the same reason. It is deliberately
# not a valid run id: nothing may open a bag with it.
DRY_RUN_RUN_ID = "(dry run — no name minted, no bag opened)"


@dataclass(frozen=True)
class RunContext(RunIdentity):
    """Everything one run DERIVED rather than was told, frozen at the boundary.

    EXTENDS `RunIdentity` RATHER THAN SITTING BESIDE IT. Identity is the first
    thing a run derives — the run id when nothing supplied one — so a second
    object holding "the rest" would be two answers to one question and would put
    `dataclasses.fields()` over half the population.

    NOTHING DOWNSTREAM RE-DERIVES A FIELD THIS CARRIES. An object handed down is
    not the same as an object in scope: if a callee still computes its own
    worktree name because it can, the context has been ADDED without removing
    the thing it replaces, and the fleet now has two answers where it had one.
    `test_a_worktree_NAME_comes_from_the_RUN_CONTEXT.py` holds that for the one
    value that was measurably scattered, and says in terms that it holds one
    value at one call-site shape.
    """

    repo_root: Path = field(metadata=derivation(
        marker="the `.git` that `git rev-parse --show-toplevel` reads — a fact "
               "on disk, never a similarity judgement.",
        algorithm="`preflight` runs `git rev-parse --show-toplevel` inside "
                  "`--repo` when it was given and inside the process's working "
                  "directory otherwise, and refuses anything that is not a "
                  "repository.",
        override="`--repo <path>` — a FILESYSTEM PATH, never a gh OWNER/NAME slug.",
        scope="`.claude/worktrees/` and `.claude/logs/` both hang off it, so a "
              "root resolved at a SUBDIRECTORY scatters worktrees and logs "
              "where `/cleanup-merged-worktrees` never looks — and a later "
              "cleanup deletes the logs along with the workspace, after which "
              "cost accounting for those runs is unrecoverable. Six of seven V2 "
              "entrypoints once dropped this resolution and used the working "
              "directory. Under this fleet the answer is normally a WORKTREE "
              "root, which is correct for a dispatch and wrong for a tool that "
              "expects the main checkout."))

    journal_root: Path | None = field(metadata=derivation(
        marker="`config.yaml`'s `journal.root:`, or the deployment shape's "
               "documented default — XDG_STATE_HOME for `user`, /var/lib for "
               "`systemd`. The `container` shape has no derivable default and "
               "is refused rather than guessed.",
        algorithm="`resolve_journal_root` takes the configured path or the "
                  "shape's documented default, refuses a relative path, a "
                  "symlink, a path inside a git working tree, a wrong owner or "
                  "a mode that is not 0700, and creates it at 0700 when absent. "
                  "`None` on a rehearsal, which resolves nothing and creates "
                  "nothing.",
        override="`journal.root:` in config.yaml.",
        scope="wrong ⇒ every verbatim transcript and every cost record this run "
              "writes lands somewhere nobody reads, or inside a repo where it "
              "gets committed and pushed. Resolved HERE rather than inside "
              "`open_run_bag` so an unusable root stops the run one step "
              "earlier and so the echo can name it before the run spends "
              "anything."))

    workflow_key: str = field(metadata=derivation(
        marker="none — this field is DECLARED by the entrypoint, not derived, "
               "and it is here because a declared value still has to travel "
               "with the derived ones it feeds.",
        algorithm="the literal each entrypoint passes to `RunContext.build`. It "
                  "is the key `config.yaml` looks a model up under, the key the "
                  "bag files the run as, and the stem `worktree_name` is built "
                  "from.",
        override="none — a run cannot be told it is a different workflow.",
        scope="wrong ⇒ the bag files this run as another workflow AND the "
              "worktree derived from it is named for one. `run_build_minor` "
              "carried exactly that: `workflow_key=\"build-minor\"` beside a "
              "worktree named `build-…`, which is the drift this field's "
              "consolidation fixes."))

    worktree_name: str = field(metadata=derivation(
        marker="`workflow_key` and the wall clock, read once at this boundary.",
        algorithm="`f\"{workflow_key}-{int(time.time())}\"`, computed once here "
                  "and passed to every caller of `worktree_add`. No entrypoint "
                  "and no workflow module assembles it.",
        override="none.",
        scope="wrong ⇒ two runs collide on one directory under "
              "`.claude/worktrees/`, or a run's tree is named for a workflow "
              "that is not the one running and `/cleanup-merged-worktrees` "
              "cannot pair the tree with its PR. Eleven sites derived this in "
              "three spellings before it moved here, and one had already "
              "drifted from the key it was supposed to follow."))

    pr_number: str | None = field(metadata=derivation(
        marker="the `--pr` flag, and nothing else.",
        algorithm="taken verbatim from `--pr`; `None` means this run opens a PR "
                  "of its own rather than continuing one. It is NOT parsed back "
                  "out of a URL here — `routing.pr_number_from_url` does that "
                  "mid-run for a PR the run has just opened, which is not a "
                  "boundary value.",
        override="`--pr <n>` is itself the only input.",
        scope="wrong ⇒ the run comments on, corrects or disposes somebody "
              "else's pull request. It also decides the base a worktree is cut "
              "from (`base_ref`), so a wrong number branches this run's work off "
              "unrelated commits — the shape that put another PR's commits into "
              "three of eight open PRs on 2026-08-20."))

    target: str | None = field(metadata=derivation(
        marker="the positional path the operator pointed the run at, already "
               "resolved against `repo_root` and refused if it escapes.",
        algorithm="the entrypoint's resolved operator path, stated "
                  "repo-relative. `None` for the runs that take no target — "
                  "`build`, `build-minor`, `plan-project` and `review-pr`.",
        override="the positional argument is itself the only input.",
        scope="THE ONE A WRONG ANSWER IS SILENT ABOUT, and the reason this "
              "object echoes at all. A wrong target plans, researches or "
              "triages the WRONG component competently: it reads real files, "
              "opens a real pull request, and nothing goes red. Every other "
              "field here fails loudly somewhere; this one does not, which is "
              "why the echo happens before the first side effect rather than "
              "somewhere in the transcript."))

    @classmethod
    def build(cls, *, identity: RunIdentity, repo_root: Path, workflow_key: str,
              pr_number: str | None = None, target: str | None = None,
              config_path: Path | None = None,
              env=None, clock=time.time) -> "RunContext":
        """The dispatch boundary. Everything derived, once, before anything runs.

        RESOLVES THE JOURNAL ROOT HERE RATHER THAN LEAVING IT TO `open_run_bag`,
        and the choice was not obvious. Resolving at the boundary means an
        unusable root stops the run one step earlier, and it means the echo can
        NAME the root before the run spends anything — a run that says where its
        record is going is the point of the echo. What it costs is that
        `open_run_bag` stops owning a decision it has always owned; it keeps its
        own resolution for every caller that has no context (the validator, the
        tests) and takes this answer when one is passed, so there is one
        resolution per run rather than two.

        `clock` IS INJECTED FOR THE TESTS AND FOR NOTHING ELSE. The worktree name
        is the value this object exists to consolidate, so a test has to be able
        to pin it without pinning the module's clock globally.
        """
        journal_root = resolve_journal_root(
            config=load_journal_config(config_path), env=env)
        return cls(
            run_id=identity.run_id, writer=identity.writer, minted=identity.minted,
            repo_root=repo_root, journal_root=journal_root,
            workflow_key=workflow_key,
            worktree_name=f"{workflow_key}-{int(clock())}",
            pr_number=pr_number, target=target,
        )

    @classmethod
    def for_dry_run(cls, *, repo_root: Path, workflow_key: str,
                    pr_number: str | None = None, target: str | None = None,
                    clock=time.time) -> "RunContext":
        """The same object for a rehearsal — nothing minted, nothing created.

        ⚠ THE BOUNDARY IS NARROWER THAN "THE ENTRYPOINT", which is why this
        exists rather than a flag on `build`. `resolve_identity` is called AFTER
        the `--dry-run` early return on purpose: a dry run states "nothing
        invoked, nothing posted", and minting a name would make that false. So
        would creating a journal root at 0700. A context built for a dry run
        must be buildable without either, and both fields say so in their
        values rather than being quietly absent.

        THE POINT IS THAT THERE IS ONE ASSEMBLY. `--dry-run` previewing values it
        assembled itself is how a rehearsal shows something that is not what
        runs, and this family has shipped that bug once already. Both paths
        construct a `RunContext` and both print `render()`.
        """
        return cls(
            run_id=DRY_RUN_RUN_ID, writer=None, minted=False,
            repo_root=repo_root, journal_root=None, workflow_key=workflow_key,
            worktree_name=f"{workflow_key}-{int(clock())}",
            pr_number=pr_number, target=target,
        )

    def render(self) -> str:
        """What this run derived, as the ONE block both paths print.

        Read by `echo` on the live path and by every entrypoint's `--dry-run`
        block. A second rendering would be a second assembly, which is the
        defect requirement 4 names.
        """
        rows = [
            ("run", self.run_id if self.is_the_run
                    else f"{self.run_id} (writer {self.writer})"),
            ("workflow", self.workflow_key),
            ("repo root", str(self.repo_root)),
            ("journal", str(self.journal_root) if self.journal_root
                        else "(not resolved — rehearsal opens no bag)"),
            ("worktree", self.worktree_name),
            ("target", self.target or "(this workflow takes none)"),
            ("pr", f"#{self.pr_number}" if self.pr_number
                   else "(a new one will be opened)"),
        ]
        width = max(len(label) for label, _ in rows)
        head = "run context — derived here, before anything is created:"
        return "\n".join([head] + [f"  {label:<{width}} : {value}"
                                   for label, value in rows])

    def echo(self, stream=None) -> None:
        """State the context on stderr, once, before the first side effect.

        UNCONDITIONAL, AND NOT GATED ON `verbose`. `verbose` governs a
        workflow's own chatter; this is the run saying what it is about to spend
        money on. The precedent is one function away — `resolve_identity`
        announces a minted run id on stderr unconditionally, for the same class
        of value, because a name nobody was told is a bag nobody can retry into.

        GATED ON *IS THIS INVOCATION THE RUN*, WHICH IS THE "CONSTRUCTED HERE OR
        RECEIVED" DISCRIMINATOR. A parent that builds a context and hands it to
        nine children should say it once; a child that was handed one should not
        reprint what its parent already said, and `--writer` is the only thing
        that distinguishes the two from inside the process.

        ⚠ IT IS DELIBERATELY *NOT* GATED ON `minted`, and that is a correction
        rather than a simplification. `minted` is False for an operator retrying
        with `--run-id X` — a parent, constructing its own context, and exactly
        the caller who most needs to see what the retry derived. `minted`
        answers "did I make the NAME"; the echo asks "did I make the CONTEXT",
        and `writer` is the field that answers it.

        stderr rather than stdout because several entrypoints' stdout is a
        rendered report an operator or a tool reads.
        """
        if not self.is_the_run:
            return
        print(self.render(), file=stream or sys.stderr, flush=True)


def context_field_documentation() -> dict[str, dict[str, str]]:
    """Every field's four-part statement, read off the object itself.

    THE POPULATION IS `dataclasses.fields()`, WHICH IS THE ENTIRE ARGUMENT FOR
    DOING IT THIS WAY. It is a language primitive: no marker convention, no tree
    sweep, no hand-kept list, and a field added a year from now is in it the
    moment it is declared. That is the property the deleted tree-wide enumeration
    could not have — a table checked against itself cannot see what was never
    added to it.
    """
    return {f.name: dict(f.metadata) for f in fields(RunContext)}
