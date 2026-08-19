"""The plan parent — Layer 1 orchestration for the planning family.

A parent calls no model. It decides IF, WHEN and WHAT to call, and holds no
process code. Every branch is a pure decision from `routing`; every side effect
is an activity or a child workflow.

    triage-candidates -> plan-candidates -> research(per NEW component) -> plan-feature -> plan-verify -> plan-sprint -> review-pr
                         [activity, no model]   write -> verify           [-------- per component -------]            [loop-back]

TRIAGE AT THE FRONT, SPRINT MAINTENANCE AT THE BACK. Until the split, one child
did both and nothing could be sequenced between them. Feature planning and
scaffolding belong in that gap, and while the two jobs shared a dispatch that was
structurally impossible rather than merely unbuilt.

`plan-candidates` IS AN ACTIVITY, NOT A CHILD, AND IT IS THE ONLY STEP HERE THAT
IS NOT. It calls no model because it needs no judgement: triage already decided
which candidates ship and the filer already named where each one goes, so the
whole job is creating the directory and seeding the first document from what the
row already says. Two rules carry that, and neither is §3.4 — this docstring
cited §3.4 until a standards pass read it, and §3.4 is *Composition — reuse
workflows as building blocks*, which says nothing about parents calling
activities. **§3.1/§3.3** is the layering rule: Layer 1 orchestrates and holds no
process code, Layer 3a holds the I/O — which is why the function lives in
`plan_project_activities.py` rather than inline here. **§3.4's actual sentence**
supplies the other half: *"manufacturing children for their own sake adds
dispatch overhead for no gain"*. Both support this; the sentence quoted before
did not.

IT FIXED AN ORDERING DEFECT ON ITS OWN. `plan-sprint` used to run FIRST, so the
sprint plan — hour totals included — was updated before anything estimated the
work those totals are of. Running it last means it reads what the middle of the
pipeline produced instead of predicting it.

`plan-feature` IS HERE NOW, AND IT RUNS INSIDE THE RESEARCH LOOP RATHER THAN
AFTER IT. It takes ONE component and writes that component's `roadmap.md` and its
numbered phase docs from that component's research, so it belongs immediately
after the `research-verify` that gated the evidence it plans from — a second loop
would separate each component's plan from its own evidence by every other
component's research cycle.

**It sizes nothing and writes no sprint entry.** Sizing is `plan-verify`'s, on
the same `author != judge` argument that split research into write/verify and
build into draft/refine — and that child now EXISTS and runs immediately after
it, per component, inside the same loop. The sprint entry stays the operator's,
and `plan-feature`'s report names the one each component needs.

`plan-verify` CLOSED THE FAMILY'S LAST `author != judge` GAP. It reads the
roadmap and the phase docs cold, sizes every phase in hours, and answers the
question `plan-feature`'s own report is required to ask and structurally cannot
answer about itself — *where is this plan weakest*. Its estimates go into
`<component>/roadmap.md` and nowhere else.

**AND `plan-sprint` DOES NOT READ THEM, which is worth knowing here because this
is where the ordering argument lives.** Running the sizer before the sprint
maintainer is necessary and is not yet sufficient: `plan-sprint`'s prompt states
it never opens a phase doc, its `EXISTING_WORK` block enumerates components,
syntheses, pool papers and issues but no roadmap, and no reader for an hour
figure exists in it. It still sizes against the 160-hour calibration. Closing
that is a change to `plan-sprint` and is deliberately not made from the PR that
built the sizer.

THE RESEARCH STEP CAN FIRE AGAIN, AND `plan-candidates` IS WHAT FIXED IT. Its
input was `new_sprint_sections` alone, read from the sprint diff, and with
plan-sprint sequenced behind it nothing ahead of it added a sprint section — so
the step was inert by construction. It was left wired rather than deleted or
given an invented interim signal, on the grounds that a signal invented for an
interim outlives the interim. `plan-candidates` supplies the real one: the
components it scaffolds ARE the new components, named by the filer and ruled by
triage, and no diff heuristic is involved. Both signals are read and unioned —
`new_sprint_sections` stays because it is still the correct answer to *"did this
run add a sprint section"*, and it will start returning rows again the moment
anything ahead of this step writes one.

WHAT "CAN FIRE AGAIN" MEANS AND WHAT IT DOES NOT. The wiring is live; the input
still depends on somebody naming a component. Today every row that names one
names a component whose directory already exists, so the next run scaffolds
nothing and takes the empty-working-set branch. That is correct behaviour rather
than a defect, but a reader taking this docstring as a statement about the
RUNNING pipeline would be wrong. The step becomes productive as filers name
components on the rows they file, which every filing prompt now instructs; the
pre-existing `ship`+`open` rows with a blank cell are the operator's to name, per
`candidates.md`.

THE FIGURES ARE NOT RESTATED HERE, AND THAT IS THE POINT. This paragraph read
"of 77 candidate rows exactly one names a `component`" and was false by the end
of the same commit that wrote it, which appended a row naming one — the second
restated tally this change falsified within a single pass, in a class the same
pass claimed to have closed by deleting a third. `candidate_counts` and
`candidate_components` derive both numbers from the file on demand; a sentence
that re-types them is a copy with no gate on it.

WHY THIS EXISTS AT ALL. `plan-sprint` shipped and ran twice with no parent, so
its output reached the operator UNJUDGED — and it is the only autonomous run
authorised to write `sprint.md`, the file the governing rule exists to protect.
Every other family has its judge: build is draft -> refine -> review-pr,
research is write -> verify -> review-pr. This one had nothing, which made it
the single place where `author != judge` was not being honoured.

Neither child could simply call `review-pr` itself: a parent calls no model and
both of them call one. Bolting the judge onto a child would have made it a
model-calling orchestrator, which is the exact shape decomposition removes.

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

`plan-phase` IS NOT COMING, AND THAT IS A RESOLUTION RATHER THAN A CANCELLATION.
This paragraph described it as a separate port slotting between `plan-sprint` and
`review-pr`, writing the phase doc for a new sprint section. `plan-feature` writes
the roadmap AND the phase docs, because the phase boundaries ARE both documents'
subject: splitting them puts a dispatch boundary in the middle of one decision,
and deciding it twice in two contexts is how the two layers come to disagree. Its
position is also earlier than that plan assumed — before `plan-sprint`, not after
— so the sprint plan is maintained against work that has already been decomposed.

`plan-verify` IS HERE NOW, and this paragraph used to say it was the one thing
missing. Two judges now see a planning PR and they are not redundant:
`plan-verify` reads the ARTIFACT cold — a roadmap and its phase docs, whether the
boundaries are right and what each costs — while `review-pr --type planning` at
step 4 judges the DIFF against the planning criteria and returns the verdict this
parent routes on. Neither substitutes for the other: a plan can be a clean diff
and a bad decomposition.
"""

from __future__ import annotations

from pathlib import Path

from .. import plan_activities as act
from . import plan_project_activities as own
from ... import assistant_activities as _shared
from ... import routing
from ...review_pr import review_pr_workflow as review_pr
from ...review_pr.review_pr_helper import ReviewInput, ReviewType
from ...research.research_write import research_write_workflow as write
from ...research.research_verify import research_verify_workflow as verify
from ..plan_feature import plan_feature_workflow as feature
from ..plan_sprint import plan_sprint_workflow as sprint
from ..plan_verify import plan_verify_workflow as plan_verify
from ..triage_candidates import triage_candidates_workflow as triage

# WHICH SIGNAL PUT A COMPONENT IN FRONT OF THE RESEARCH STEP. Interned constants
# rather than bare strings so the brief branch below compares by IDENTITY: the
# two briefs are not interchangeable — one of them is a false premise for the
# other's component — and a typo'd string literal would silently pick the wrong
# one rather than raising.
_SCAFFOLDED = "scaffolded"
_SPRINT_SECTION = "sprint-section"


def _plan_one(*, section: str, component_root: Path, repo_root: Path,
              worktree: Path, candidates_path: Path, pr: str | None,
              verbose: bool) -> None:
    """Dispatch `plan-feature` then `plan-verify` for ONE component, in that order.

    Raises what either child raises.

    CALLED INSIDE THE RESEARCH LOOP, NOT AFTER IT, and that is the whole
    placement argument. `plan-feature` takes ONE component and plans it from ITS
    research; the evidence it needs is what `research-verify` gated a line
    earlier. A second loop after the first would re-derive the same set from the
    same `origin` map and separate each component's plan from its own evidence by
    every other component's research cycle.

    `plan-verify` IS THE SECOND CALL AND NOT A SECOND LOOP, for the same reason.
    It reads ONE component's plan, so it belongs beside the run that wrote it —
    and it must run before `plan-sprint`, which is step 3 below. That ordering is
    not stylistic: `plan_sprint_workflow`'s own docstring records the defect it
    fixes, *"the sprint plan used to be updated BEFORE anything estimated the
    work, so its hour totals landed ahead of the estimates they depend on"*, and
    until this child landed there were no estimates for it to be ahead OF.

    THE FRESH CONTEXT IS THE POINT. It is a separate dispatch rather than a stage
    inside `plan-feature` because a judge sharing the producer's context is the
    one thing it exists not to be — the same argument that made `research-verify`
    and `build-refine` separate runs.

    BOTH CHILDREN ARE HANDED A REPO-ROOTED COMPONENT, and `component_root` is
    WORKTREE-rooted, so it is re-anchored here rather than passed as-is. That
    asymmetry is deliberate and is the one every child in this parent shares:
    `candidates_path` and `sprint_path` arrive repo-rooted from the runner and
    each child relativises against `repo_root` itself, while a directory the
    PARENT creates is created where the run can see it. Passing the worktree path
    would make the child's `relative_to(repo_root)` raise on a path that is
    perfectly valid — a failure naming the wrong cause. Resolved ONCE into a
    local so the two calls cannot be given different anchors.

    A FUNCTION RATHER THAN INLINE LINES because the caller wraps this and the two
    research children in one `try`, and the re-anchoring argument above belongs
    with the expression it explains rather than a screen away inside a handler.
    `section` is carried only so the loop reads the same either side.
    """
    repo_component = repo_root / component_root.relative_to(worktree)
    feature.run_plan_feature(
        repo_root=repo_root, worktree=worktree, component=repo_component,
        candidates_path=candidates_path, pr_number=pr, verbose=verbose,
    )
    plan_verify.run_plan_verify(
        repo_root=repo_root, worktree=worktree, component=repo_component,
        candidates_path=candidates_path, pr_number=pr, verbose=verbose,
    )


def run_plan_project(*, repo_root: Path, worktree_name: str, sprint_path: Path,
                    candidates_path: Path, research_dir: Path,
                    pr_number: str | None = None, repo_target: str | None = None,
                    verbose: bool = False) -> tuple[str, routing.Verdict, int, list[str]]:
    """Triage, plan, judge, and route on the verdict.

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

    # THE COMMIT THIS DISPATCH STARTED FROM, pinned before any child can write.
    # Step 2's sweep asks "which sections did THIS RUN add", and only a base
    # taken here answers it: on a `--pr` redispatch the branch already carries
    # sections an earlier pass added and researched, so a diff against
    # `origin/main` would re-research every one of them. Same rule the snapshot
    # comparators state — snapshot around the run, never diff against the base.
    base_sha = act.git_output(
        worktree, ["git", "rev-parse", "HEAD"],
        "The parent cannot pin the commit this dispatch started from, so it "
        "cannot tell the sections IT added from ones an earlier pass added.",
    ).strip()

    # Read BEFORE the triage child, so a `gh` failure costs a dispatch that has
    # produced nothing rather than one that has already triaged a sprint.
    slug = _shared.repo_slug(repo_root)

    # --- Step 1: TRIAGE ----------------------------------------------------
    # FIRST, and this is the ordering the split bought. The PR URL is both the
    # handoff and the child's completion contract; the child raises if it
    # produced none AND if it left any candidate untriaged, so `exit 0` cannot
    # mean unfinished.
    pr_url = triage.run_triage_candidates(
        repo_root=repo_root, worktree=worktree,
        candidates_path=candidates_path, research_dir=research_dir,
        pr_number=pr_number, verbose=verbose,
    )
    pr = routing.pr_number_from_url(pr_url, expected_repo=slug)

    # --- Step 1b: SCAFFOLD each shipped candidate that has no home yet ------
    # AN ACTIVITY, NOT A CHILD. No worktree of its own, no PR of its own, no
    # model: it runs inline on the branch step 1 just opened, and its output
    # lands in the same commit range under the same review.
    #
    # IT RUNS AFTER TRIAGE FOR THE OBVIOUS REASON — it acts on `ship` rulings,
    # and before triage there are none. On a `--pr` redispatch the rulings are
    # already there from an earlier pass, and the exists-check is what keeps that
    # from re-scaffolding them.
    scaffolded = own.scaffold_candidate_components(
        worktree, worktree / candidates_path.relative_to(repo_root))

    # EVERY OUTCOME GETS A NOTE, NOT ONLY THE PRODUCTIVE ONE. A step that reports
    # only what it created cannot be told apart from a step that saw nothing, and
    # the three quiet outcomes are the ones worth reading: a candidate extending a
    # live component is the design working, a resumed pool is a previous run that
    # died half-way, and an unusable name is a filer typo nobody else will notice.
    #
    # NOT `slug` for the loop variable — that name is already bound to the
    # REPOSITORY slug above and is what step 1's PR-number lookup was given.
    for component in scaffolded.created:
        notes.append(f"Scaffolded `docs/development/{component}/research/` "
                     f"from a shipped candidate — researching it next.")
    for component in scaffolded.resumed:
        notes.append(f"`docs/development/{component}/research/` was seeded by an "
                     f"earlier pass and never researched — resuming it.")
    # NOT "which already holds research" — that was a claim about the pool's
    # CONTENTS over a check of the directory's EXISTENCE, and it is false for most
    # of the tree: most components hold either a `research/` with nothing rolled
    # up or no `research/` at all. An operator acting on the old sentence believed
    # research existed that did not. The note now says what was actually checked.
    #
    # The tally this comment used to carry ("9 of 17 … and 5") is gone for the
    # reason `scaffold_candidate_components`' docstring states at length: it was
    # wrong against the tree — it counted `docs/development/reviews/`, which is
    # not a component — and a figure restated where nothing derives it is a copy
    # with no gate on it. The claim the note rests on is the PROPERTY, and the
    # property needs no denominator.
    for cid, component in scaffolded.extends:
        notes.append(f"`{cid}` names `docs/development/{component}/`, which already "
                     f"exists — the candidate extends something already planned, so "
                     f"nothing was scaffolded. Whether that component has research "
                     f"is a separate question this step does not ask.")
    for cid, raw in scaffolded.unnamed:
        notes.append(f"`{cid}`'s `component` cell reads {raw!r}, which yields no "
                     f"folder name. Nothing scaffolded; the cell needs a real name "
                     f"or a blank.")

    # --- Step 2: RESEARCH each NEW component -------------------------------
    # TWO SIGNALS, UNIONED, AND NEITHER IS ASKED OF A CHILD. The parent must not
    # trust an account when the artifact is right there.
    #
    #   * what step 1b just scaffolded — a `ship` candidate whose component the
    #     FILER named and whose directory did not exist. This is the live signal.
    #   * a `## Sprint:` heading THIS RUN added — read from the diff. An edited
    #     section shows no added heading, so a component is researched only when
    #     it is genuinely new; researching one because its prose moved spends a
    #     full cycle on nothing.
    #
    # THE SECOND WAS THE ONLY SIGNAL AND THAT MADE THIS STEP INERT. With
    # plan-sprint sequenced behind it, nothing ahead of it adds a sprint section,
    # so the sweep could not return anything. It is kept rather than replaced
    # because it is still the correct answer to the question it asks, and it
    # starts returning rows the moment anything ahead of this step writes one.
    #
    # Order matters only for reading the notes: scaffolded components first,
    # because that is the path a candidate actually travels today.
    #
    # The research CHILDREN are called, not the research PARENT. That parent
    # would establish a second worktree and open a second PR, and its verify
    # loop would then gate a triage pass that was already fine. Same children,
    # two callers — which is the whole point of child-ness being a call-graph
    # property rather than a location.
    new_sections = own.new_sprint_sections(
        worktree, str(sprint_path.relative_to(repo_root)), base_ref=base_sha)

    # DE-DUPLICATED ON THE RESOLVED SLUG, NOT ON THE RAW STRING, AND THAT IS THE
    # WHOLE CORRECTNESS OF THIS LINE. The two signals speak different alphabets:
    # `scaffold_candidate_components` returns SLUGS (`fleet-reliability`) because
    # it named the directory it made, while `new_sprint_sections` returns the RAW
    # HEADING (`Fleet Reliability`) because it read it out of a diff. `component_dir`
    # maps both onto the same directory, so a string-keyed union kept both — two
    # `research-write` plus two `research-verify` dispatches into one pool, and the
    # SECOND one handed the sprint-section brief for a component that has no sprint
    # section, which is the false premise the branch below exists to avoid.
    #
    # Latent rather than firing today, because nothing ahead of this step adds a
    # sprint section — which is exactly why it had to be fixed rather than watched:
    # it becomes live on the day `plan-feature` lands, in a run nobody is reading.
    #
    # An ORIGIN MAP rather than a bare list, so the brief below reads off a
    # recorded fact instead of re-deriving it with a membership test that has the
    # same alphabet problem. `setdefault` makes first-signal-wins explicit, and
    # scaffolding is listed first because a scaffolded component genuinely has no
    # sprint section to read.
    # The value keeps THE NAME AS ITS SIGNAL SPELLED IT alongside the signal, and
    # that is deliberately weaker than "the raw name", which is what this said and
    # was false for one of its two arms. `new_sprint_sections` yields the heading
    # as the operator wrote it, and the sprint brief below quotes it — a slug is
    # not that. `scaffolded.to_research` yields SLUGS, because the scaffolder names
    # the directory it made, so the scaffolded arm's value is already resolved.
    # Nothing downstream is wrong about that — `component_slug` is idempotent, and
    # the scaffolded brief never quotes the name — but a reader taking the old
    # sentence at face value would believe a filer's original spelling survives to
    # here, and it does not.
    origin: dict[str, tuple[str, str]] = {}
    for name in scaffolded.to_research:
        origin.setdefault(own.component_slug(name), (_SCAFFOLDED, name))
    for name in new_sections:
        origin.setdefault(own.component_slug(name), (_SPRINT_SECTION, name))
    if not origin:
        notes.append(
            "No component research ran: no shipped candidate named a component "
            "that needed scaffolding, and this run added no sprint section. That "
            "is an empty working set, not a skipped step. Any candidate that WAS "
            "seen and declined is named in its own note above."
        )
    for section, (signal, raw) in origin.items():
        notes.append(f"New component `{section}` — researching before it is planned.")
        # NOT `research_dir` — that parameter is the PRODUCT pool the triage and
        # sprint children work from, and rebinding it here would hand the
        # loop-back below the wrong pool. A shadowed parameter is a silent
        # wrong-argument bug.
        #
        # THE RAW NAME, NOT THE SLUG, and the `source` with it. `component_dir`
        # takes a `source` precisely so its one raise names the surface to go and
        # look at; handing it the slugged key produced "sprint section '' yields no
        # folder name" — a message with nothing in it anybody can search for.
        # `component_slug` is idempotent, so passing the raw name changes only the
        # diagnostic.
        #
        # RESOLVED ONCE INTO A LOCAL, because step 2b needs the same directory
        # and a second `component_dir` call would be a second chance to pass a
        # different `raw` or a different `source`. This is the read-once rule the
        # sibling workflows state for their column readers, applied to a path.
        component_root = own.component_dir(
            worktree, raw,
            source=("`component` cell in candidates.md" if signal is _SCAFFOLDED
                    else "sprint section"))
        component_pool = component_root / "research"
        component_pool.mkdir(parents=True, exist_ok=True)

        # THE BRIEF DEPENDS ON WHICH SIGNAL BROUGHT THE COMPONENT HERE, and
        # getting that wrong hands the model a FALSE PREMISE. A scaffolded
        # component has no sprint section — `sprint.md` is the operator's file
        # and nothing in this pipeline writes it — so telling the child to "read
        # that section first" would send it to look for something that does not
        # exist and cannot be created. It gets pointed at the seeded synthesis
        # instead, which is where its actual brief was just written.
        #
        # Read off `origin` rather than re-derived by membership: the two signals
        # spell a component differently, so `section in scaffolded` answered the
        # wrong question for the one case where the answer mattered.
        #
        # In both cases the child's Stage 1 already reads the destination's
        # planning docs to drive its topics, so a hand-written task file would
        # be restating what it is about to read.
        if signal is _SCAFFOLDED:
            context = (
                f"A new component `{section}` was just scaffolded from a shipped "
                f"research candidate and has no research and no phase doc yet. "
                f"Read `{component_pool.relative_to(worktree)}/synthesis.md` first "
                f"— it names the candidate this came from and carries the summary "
                f"as filed, and it is your brief. It has NO sprint section: "
                f"planning follows this research, not the other way round. "
                f"CARRY THE `C-NNN` PROVENANCE LINE at the top of that synthesis "
                f"into the one you write — it is the only link back to the row "
                f"that authorised this component, and you are about to overwrite "
                f"the only copy of it."
            )
        elif signal is _SPRINT_SECTION:
            context = (
                f"A new sprint section `{raw}` was just added to "
                f"{sprint_path.relative_to(repo_root)} and has no phase doc yet. "
                f"Research it BEFORE it is planned. Read that section first — it is "
                f"your brief, and its milestones are what this pool must inform."
            )
        else:
            # THE ARM THAT MAKES THE INTERNING ABOVE MEAN WHAT IT CLAIMS. That
            # comment says a typo'd literal "would silently pick the wrong one
            # rather than raising" — and with a bare `else` it did the opposite:
            # any value that is not `_SCAFFOLDED` fell through to the SPRINT
            # brief, which is the false premise this branch exists to prevent,
            # handed to a model. A third signal added later would have inherited
            # it silently. Now the guarantee is the code's rather than the
            # comment's.
            raise ValueError(
                f"`{section}` reached the research step under an unknown signal "
                f"{signal!r}. Every signal needs its own brief: the two that exist "
                f"are not interchangeable, since a scaffolded component has no "
                f"sprint section to read and a sprint-section component has no "
                f"seeded synthesis. Add the arm rather than letting it default.")
        # A FAILURE HERE ORPHANS THIS COMPONENT FROM AUTOMATIC REDISPATCH, so it
        # is caught to SAY SO and then re-raised. Nothing is swallowed and the
        # exit code does not change; what is added is the two things the operator
        # cannot reconstruct from the raised message alone.
        #
        # THE ORPHANING IS REAL AND IS NOT THIS LOOP'S DOING. `scaffold_candidate_
        # components` decides "does this component still need work?" from the
        # `_UNRESEARCHED` marker in its `synthesis.md`, and `research-write`
        # strips that marker as its first act. So a component whose research
        # SUCCEEDED and whose planning then failed reads as `extends` on every
        # later `--pr` redispatch: it never re-enters `to_research`, never
        # re-enters `origin`, and no later pass in this pipeline looks for a
        # missing `roadmap.md` at all. Absent this message the operator's only
        # signal is one child's error text, from which the fact that the parent
        # will never retry is not derivable.
        #
        # AND THE NOTES DIE WITH IT OTHERWISE. `notes` is local and returned only
        # on the success path, so the accounting this function's own docstring
        # calls the part worth reading — which candidate was declined and why,
        # which component was scaffolded — is guaranteed absent at exactly the
        # moment it is being read for a diagnosis.
        try:
            write.run_write(research_dir=component_pool, repo_root=repo_root,
                            worktree=worktree, context=context, pr_number=pr,
                            verbose=verbose)
            verify.run_verify(research_dir=component_pool, pr_number=pr,
                              repo_root=repo_root, worktree=worktree, verbose=verbose)
            _plan_one(section=section, component_root=component_root,
                      repo_root=repo_root, worktree=worktree,
                      candidates_path=candidates_path, pr=pr, verbose=verbose)
        except (RuntimeError, FileNotFoundError, ValueError) as exc:
            raise RuntimeError(
                f"{exc}\n\n"
                f"— plan-project stopped on component `{section}`, and the "
                f"{len(origin)} component(s) in this run's working set are NOT all "
                f"done. This component will not be picked up automatically: "
                f"`scaffold_candidate_components` keys resume off the "
                f"`<!-- plan-candidates: seeded, no research yet -->` marker, "
                f"`research-write` removes that marker before either step above "
                f"ran, and nothing anywhere checks for a missing `roadmap.md`. A "
                f"`--pr` redispatch will read `{section}` as already handled.\n"
                f"  To finish it by hand, IN THIS ORDER — the second reads what "
                f"the first writes, and `plan_verify.sh` refuses a component with "
                f"no `roadmap.md` rather than dispatching against nothing:\n"
                f"    scripts/workflows/temporal/scripts/plan_feature.sh "
                f"docs/development/{section}"
                + (f" --pr {pr}" if pr else "")
                + "\n"
                f"    scripts/workflows/temporal/scripts/plan_verify.sh "
                f"docs/development/{section}"
                + (f" --pr {pr}" if pr else "")
                + "\n  Skip the first if the plan is already written; the second "
                f"is what puts an hour estimate on each phase.\n"
                + "\n\nWhat this run had done before it stopped:\n"
                + "\n".join(f"  - {n}" for n in notes)
            ) from exc
        notes.append(f"`{section}` planned and SIZED — `plan-feature` wrote "
                     f"`roadmap.md` and its phase docs from the component's "
                     f"research, and `plan-verify` then read them cold, put an "
                     f"hour estimate on every phase in `roadmap.md`, and reported "
                     f"where the plan is weakest. `plan-sprint` does not read "
                     f"those estimates; it still sizes against its 160-hour "
                     f"calibration.")

    # --- Step 3: MAINTAIN THE SPRINT PLAN ----------------------------------
    # LAST of the producing children, which is the second thing the split
    # bought. It reads what steps 1 and 2 put in the tree — the rulings and any
    # component evidence — rather than being written before either existed. Its
    # own guard fails the run if it wrote the `decision` column, which is now
    # `triage-candidates`'s alone.
    #
    # `pr_number=pr`: the PR is already open. Step 1 opened it, and both children
    # land their work on the one branch, in the one worktree, under the one
    # review.
    # ONE DISPATCH PER PLANNED COMPONENT since 2026-08-19, where it used to be one
    # dispatch for all of them. `plan-sprint` was rebuilt around a single planned
    # component — read its roadmap, sum its phases, make its sprint entry current
    # — because a sprint entry is per-component and a total is per-component, and
    # the old candidate-walking shape had no component input at all.
    #
    # THE COST IS N DISPATCHES AND IT IS ACCEPTED. Each is narrow: one file
    # granted, one section touched, and a total already summed in code. The
    # alternative — handing one run every component at once — is what made the
    # old prompt 21KB and gave it a five-condition bar for a decision the chain
    # above it had already made.
    for section in origin:
        sprint.run_plan_sprint(
            repo_root=repo_root, worktree=worktree, sprint_path=sprint_path,
            component=repo_root / "docs" / "development" / section,
            pr_number=pr, verbose=verbose,
        )

    # --- Step 4: DISPOSITION, with one bounded loop-back -------------------
    loops = 0
    verdict = _dispose(pr, repo_root, repo_target, notes, verbose)

    while routing.should_loop_back(verdict, loops):
        loops += 1
        # COUNTED, not asserted. This said "Looping back ONCE — this is the last
        # automated pass" while `routing.MAX_LOOPS` is 3, so it was false on two
        # passes out of three and told the operator the runway had closed when it
        # had not. The whole class is now counted — the four build-family sites
        # too, two of which were telling a MODEL it was the last pass — and
        # `test_loop_cap_prose_is_counted.py` fails any new hard-coded claim. The
        # research family keeps its own `MAX_LOOPS = 1`, so its identical wording
        # is TRUE and is left alone.
        notes.append(f"HOLD (redispatch): the runway closes with a scoped fix. "
                     f"Loop-back {loops} of {routing.MAX_LOOPS}."
                     + (" This is the last automated pass."
                        if loops == routing.MAX_LOOPS else ""))
        # THE LOOP-BACK GOES TO plan-sprint, NOT TO TRIAGE, and it is a
        # correction pass. Every candidate already carries a decision, so
        # re-triaging would re-litigate rulings rather than close the runway the
        # reviewer wrote — the reason this was a correction pass before the
        # split, and it did not change. plan-sprint is also the LAST producer and
        # sees the whole PR, so a runway naming either child's work is
        # addressable from here; sending each loop through both children would
        # double the cost of every pass to reach a set of rulings that are, by
        # construction, already made.
        #
        # AND THAT ARGUMENT IS NOW INCOMPLETE, which is worth stating rather than
        # leaving for the next reader to notice. It reasons entirely about TRIAGE,
        # because when it was written the research step was inert by construction
        # and no research artifact could appear in a plan-project PR. Step 1b is
        # what changed that. A runway naming a component's SYNTHESIS — a thin
        # citation, an unverified span — is not something `plan-sprint` can close
        # either, so the loop spends its full budget on the one child that is
        # reachable and reports SPENT. Routing the loop-back by what the runway
        # names is real work and is out of a `plan-candidates` PR; it is placed as
        # a candidate rather than left as a comment nobody acts on.
        for section in origin:
            sprint.run_plan_sprint(
                repo_root=repo_root, worktree=worktree, sprint_path=sprint_path,
                component=repo_root / "docs" / "development" / section,
                pr_number=pr, correction_pass=True, verbose=verbose,
            )
        verdict = _dispose(pr, repo_root, repo_target, notes, verbose)

    if verdict is routing.Verdict.HOLD_NEEDS_ASSISTANCE:
        notes.append("review-pr found at least one item only a human can rule on. No "
                     "loop-back was attempted: more passes cannot produce a human decision.")
    elif verdict is routing.Verdict.HOLD_REDISPATCH:
        # COUNTED from the same source the loop reads. This said "one loop-back
        # is the cap" twenty-two lines below the fix above it, so a spent runway
        # emitted "Loop-back 3 of 3" and then "one loop-back is the cap" in one
        # run's notes — and the false one understates the automated budget the
        # operator is deciding against by 3x.
        notes.append(f"The automated loop is SPENT — {routing.MAX_LOOPS} loop-back(s) "
                     f"is the cap, because passes beyond it produce justification "
                     f"rather than correction.")

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
