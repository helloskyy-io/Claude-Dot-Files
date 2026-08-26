"""plan-project's own I/O — one consumer each, so §10.1 rule 3 puts them here.

Every function here serves the PARENT's decisions: which components are new,
where their research pool belongs, and — since `plan-candidates` — creating that
pool for a candidate triage has agreed to. Nothing else in the family calls any
of them, and [`workflow-scripts.md` § Location](../../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and mechanical — *"consumer count decides,
never taste"*. Rule 6 gives a one-file workflow folder its place to grow the
helper it has earned.

THEY SAT ON THE FAMILY'S SHARED SURFACE UNTIL THE SPLIT AUDIT WAS FINISHED
PROPERLY. `plan_activities`'s docstring listed five functions it had checked
against rule 3 and moved two of them out; these two were single-consumer the
whole time and were simply not in the list, so a file whose stated invariant is
*"shared by definition"* held two functions that were not. Counted this time
rather than eyeballed.

`scaffold_candidate_components` LANDED HERE FOR THE SAME REASON AND NOT BECAUSE
IT IS CONVENIENT. Its only consumer is `plan_project`, and it is a second CALL
SITE of `component_dir` — which is still one workflow, so rule 3 moves nothing.
**The count rule 3 arbitrates is per WORKFLOW, not per call site**, and this
sentence said "second consumer" until a review pointed out that the file which
teaches the rule was demonstrating the wrong arithmetic on itself: a reader
copying it promotes a single-workflow helper to the shared surface and breaks the
"anything at a parent level is shared by definition" invariant the rule buys.
That it needed no migration is a consequence of the rule, not a reason to skip
checking it.

AND THE SENTENCE ABOVE WAS FALSE WHEN IT WAS WRITTEN — the scaffolder built
`docs/development/<slug>/research` by hand, ninety lines below the helper whose
whole job is constructing that path, so `component_dir` had exactly ONE call
site and the `source` parameter added for the second was passed by nobody. A
worked example of rule 3 that miscounts its own call sites is worse than none,
because the next reader copies the arithmetic rather than the rule. The
scaffolder routes through `component_dir` now, which is what makes the claim
true and the parameter live.

IDEMPOTENT (§7.1) BY CHECK-THEN-ACT, which is the pattern §7.1's own
`create_folder` example uses and `stateful_patterns.md` §4.1 names. The
exists-check IS the guard: a replay against an unchanged tree creates nothing,
and a replay landing after `plan-feature` has filled a component in leaves it
alone. This docstring called it "CONVERGENT rather than idempotent" against a
definition ("safe to replay against a CHANGED tree") that appears nowhere in
§7.1, which reads as a conformance deviation on code that is the standard's
worked example — and licenses the reverse reading, that a genuinely
non-idempotent activity can be waved through under a softer word.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from .. import plan_activities as act

# Strips the leading marker so a section name is just its name.
_SECTION_NAME = re.compile(r"^## Sprint:\s*")

# In the seeded synthesis, and removed by the first real research pass.
#
# THE RESUME SIGNAL, AND IT IS A COMMENT RATHER THAN PROSE ON PURPOSE. A run can
# die between the seed being committed and its research finishing — a
# `research-verify` failure on the documented `--pr` recovery path is enough —
# and the exists-check would then skip the component forever, because "already
# exists" cannot distinguish a live component from one this pipeline abandoned
# half-built. Matching a machine-readable marker rather than a sentence keeps a
# research paper that happens to QUOTE the seed's prose from reading as unseeded.
_UNRESEARCHED = "<!-- plan-candidates: seeded, no research yet -->"


def new_sprint_sections(worktree: Path, sprint_rel: str, *, base_ref: str) -> list[str]:
    """Sprint sections THIS DISPATCH added — read from the diff, in code.

    A NON-MODEL OBSERVABLE. The parent must know which components are new so it
    can research and plan only those, and asking the triage child to report them
    would make the parent trust an account rather than read the artifact. `git`
    already knows, and a diff is not something a model can be wrong about.

    `base_ref` IS REQUIRED AND HAS NO DEFAULT, deliberately. It defaulted to
    `origin/main`, which answers a different question — *what has this BRANCH
    accumulated* rather than *what has THIS RUN added* — and the two diverge on
    exactly the path the entrypoints document: a `--pr` redispatch cuts its
    worktree from a branch that already carries a `## Sprint:` heading an
    earlier pass added and researched, so the section reads as new again and
    buys a second full research cycle for it. `plan_activities.py`'s snapshot
    comparators state the same rule for the same reason — *snapshot around the
    run, never diff against the base* — and a caller cannot inherit the wrong
    base by saying nothing.

    Matched on the added-heading form specifically: a section merely EDITED
    shows as a changed body with no added `## Sprint:` line, and researching an
    existing component because its prose moved would spend a full cycle on
    nothing.
    """
    out = act.git_output(
        worktree, ["git", "diff", f"{base_ref}...HEAD", "--", sprint_rel],
        "The parent cannot tell which components are new, and guessing would "
        "research the wrong ones.",
    )
    return [
        _SECTION_NAME.sub("", line[1:]).split("—")[0].strip()
        for line in out.splitlines()
        if line.startswith("+## Sprint:")
    ]


def component_slug(name: str) -> str:
    """`Fleet Reliability` -> `fleet-reliability`. Empty string when nothing survives.

    RETURNS RATHER THAN RAISES, because its two callers disagree about what an
    unusable name MEANS. A sprint heading that slugs to nothing is a bug in the
    sprint file and `component_dir` still raises on it; a candidate's `component`
    cell that slugs to nothing is a filer typo, and `candidates.md` § `component`
    says of a blank that *"Nothing is scaffolded for a blank row and nothing fails
    because of one"*, extending that to a cell "not blank but yields no folder
    name". Sharing one raising helper made the second case abort the whole parent
    run after the triage dispatch had already been paid for.

    Not path-traversable: every run of non-alphanumerics collapses to a single
    `-`, so `../../etc` becomes `etc` rather than escaping the tree. Idempotent,
    so re-slugging an already-slugged name is safe.
    """
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def component_dir(tree: Path, name: str, *, source: str) -> Path:
    """`Fleet Reliability` -> `docs/development/fleet-reliability`.

    The convention the whole tree already follows, applied in code rather than
    asked of a model — a component whose folder name does not match its sprint
    section is invisible to every reconciliation that walks one against the other.

    `tree`, not `repo_root`: the only caller passes its WORKTREE, because the
    research pool this returns is written on the branch. The parameter was named
    `repo_root` and the call was correct anyway, which is the combination that
    survives review and breaks on the second caller.

    `source` NAMES THE SURFACE THE NAME CAME FROM, and it is in the exception for
    the operator's benefit. This function now serves two of them, and a message
    reading "sprint section '--' yields no folder name" over a cell that came from
    `candidates.md` sends whoever is debugging it to the wrong file — a diagnostic
    that points away from the cause is worse than a bare traceback.

    IT IS REQUIRED AND HAS NO DEFAULT, for the reason `new_sprint_sections`'
    `base_ref` states one file over: a default is the wrong answer that a new
    caller inherits by saying nothing. It defaulted to `"sprint section"` — which
    was the only surface when it was written and has not been since — and both
    production call sites had already been given an explicit value, so the default
    was reachable only by a caller that had not thought about it. That is the one
    caller it would have been wrong for.
    """
    slug = component_slug(name)
    if not slug:
        raise ValueError(f"{source} {name!r} yields no folder name")
    return tree / "docs" / "development" / slug


class Scaffolded(NamedTuple):
    """What step 1b did, per candidate — and every row it DECLINED, with the reason.

    IT RETURNED A BARE LIST OF CREATED SLUGS, AND THAT IS WHAT MADE THREE
    SEPARATE FAILURES SILENT. "Created nothing" was indistinguishable from
    "every eligible row already has a live component", from "one row named a
    component off by a character and forked it", and from "an earlier pass
    created this and died before its research finished". The parent printed the
    same empty-working-set note over all four, and that note reads as health.

    `to_research` is `created + resumed`: both are components whose research pool
    exists and holds nothing but the seed.

    THE TWO HALVES ARE NOT THE SAME KIND OF LIST, AND CONFLATING THEM IS WHAT
    PRODUCED A DEFECT IN EACH OF THE LAST TWO PASSES. `created` and `resumed`
    name COMPONENTS and feed the research fan-out, so a slug may appear in them
    at most once across BOTH — the parent turns each entry into an operator note
    and a research dispatch, and a repeat is a claim that two components need
    work when one does. `extends` and `unnamed` name ROWS and feed nothing, so
    repeats there are correct: two rows extending one component are two facts
    about the file, each carrying its own `C-NNN`.

    Stated here because it is the invariant the loop below enforces and the one
    `test_to_research_NEVER_NAMES_A_COMPONENT_TWICE` holds — as a property over
    every path into the two lists, rather than one example per path.
    """

    created: list[str]
    resumed: list[str]
    extends: list[tuple[str, str]]
    unnamed: list[tuple[str, str]]
    # TWO DECLINE REASONS ADDED 2026-08-19 WITH THE `size` COLUMN, and they are
    # separate because the operator does something different about each.
    #   `not_a_feature` — sized `phase` or `checkboxes`. Correctly not scaffolded;
    #     it is work INSIDE a component rather than a component of its own, and
    #     the run that plans that component is where it lands. Nothing is wrong.
    #     WHETHER THAT COMPONENT EXISTS IS NOT CHECKED, and the note the parent
    #     prints says so. It read "belongs inside a component that already
    #     exists" until 2026-08-20, which is a positive claim about a directory
    #     nothing on this branch looks at — `pool.parent.exists()` is below the
    #     `continue`, on the `feature` path only. A `phase` naming a component
    #     nobody has planned is triage's ruling to have made and this activity's
    #     job to REPORT; asserting it away is the one thing that would hide it.
    #   `unsized`       — ruled `ship` and never sized. Nothing can route it, and
    #     the remedy is a triage pass rather than anything here. Reported so the
    #     backlog is VISIBLE instead of silently skipped.
    #
    # REQUIRED, WITH NO DEFAULT, AND THAT IS DELIBERATE. They shipped as
    # `= []`, which on a NamedTuple is ONE list built once at class-creation and
    # handed to every instance that omits the field — so `s.not_a_feature.append(
    # ...)` on a default-constructed value writes into the class, and the next
    # default-constructed `Scaffolded` in the same process starts life holding
    # the previous one's rows. The parent turns each entry into an operator note,
    # so the visible failure is one run reporting another run's declines.
    #
    # A DEFAULT WOULD ALSO BE WRONG EVEN IF IT WERE IMMUTABLE, which is the
    # stronger reason and the one that decided against `= ()`. Every list here
    # answers "what happened to the rows I did not scaffold?", and the whole
    # argument of this class is that "nothing happened" must never be reachable
    # by omission — an absent field is exactly the silence the four original
    # buckets were introduced to remove. Requiring them makes a caller that has
    # not thought about the two decline reasons fail at construction rather than
    # report an empty one.
    not_a_feature: list[tuple[str, str]]
    unsized: list[tuple[str, str]]

    @property
    def to_research(self) -> list[str]:
        return self.created + self.resumed


def scaffold_candidate_components(worktree: Path, candidates_path: Path) -> Scaffolded:
    """Create the folder and seed the synthesis for every shipped candidate that has neither.

    THIS IS AN ACTIVITY, NOT A CHILD, AND THE DISTINCTION IS THE WHOLE DESIGN.
    There is no prompt, no entry script and no model call. The job is to move
    what triage already decided to where the next step reads from — the operator's
    words are *"it just needs to move the info over to the correct place so the
    next step can happen"*. Nothing in that needs judgement, so nothing in it
    should cost a dispatch: this runs for free, deterministically, and is
    unit-testable without a model.

    An earlier attempt built it as a model child — 1,605 lines and a 173-line
    prompt for this — and every hold the review raised was a consequence of it
    being a dispatch at all. It was closed rather than repaired.

    FIVE CONDITIONS, AND EACH SKIP IS A DECISION SOMEBODY ELSE ALREADY MADE. The
    count moved from four when `size` landed on 2026-08-19, and it is written out
    rather than derived because this list is the only place each condition's
    reasoning is recorded — there is no collection here to count:

      * `decision` is not `ship` — triage has not agreed to do it, or has refused.
      * `status` is not `open` — it is already handled.
      * `component` is blank — nobody has said where it goes. **That is an
        unanswered question, not an error**, and answering it is not this code's
        job: the filer knows and this does not. A blank scaffolds nothing and
        fails nothing. A cell that is not blank but slugs to nothing — an EN dash,
        `--`, anything punctuation-only — is the same answer for the same reason:
        it is a filer typo, and the contract says an unnamed component fails
        nothing. It is REPORTED rather than raised, since the alternative aborted
        the parent after triage's dispatch was already spent.

        ASKED OF EVERY ELIGIBLE ROW, WHATEVER ITS SIZE, and it was not when the
        `size` skip first landed. That branch sat AHEAD of this one, so
        `component_slug` was reached only for a `feature` — and a `phase`-sized
        row whose cell reads `--` was filed as `not_a_feature` under a note that
        then read *"belongs inside a component that already exists"* — a positive
        claim about a cell that names nothing. The typo went unreported and the
        note that stood in for the report asserted the opposite of it. A cell
        yielding no folder name is a filer typo at every size: a `phase` still
        has to say WHICH component it is a phase of. (That wording is gone; the
        note now refers to *"the component its `component` cell names"* and says
        outright that whether it is planned is not asked here.)
      * `size` is not `feature` — triage ruled how big this is, and only a
        feature is a component. `phase` and `checkboxes` are work INSIDE one; a
        blank is UNSIZED rather than small. Both are reported, in their own
        buckets, and neither is an error. Nothing here checks that the component
        a `phase` names is planned — that is triage's ruling to have made, and
        this activity's job is to report the row, not to enforce it.
      * `docs/development/<slug>/` ALREADY EXISTS — the candidate EXTENDS
        something already planned, so there is nothing to scaffold. The operator's
        scope is exact about this: *"If the component directory already exists, do
        nothing for that row."* The condition is the DIRECTORY, not its contents,
        and this said "exists AND holds research" until a review measured the
        tree: MOST components under `docs/development/` hold no `synthesis.md` —
        some hold a `research/` with `raw/` and nothing rolled up, some hold no
        `research/` at all — so the stronger sentence was false for the majority
        of them and the run note built on it told the operator a pool held
        research that did not exist.

        THE TALLY THAT USED TO BE IN THAT SENTENCE IS GONE ON PURPOSE, and its
        removal is the same correction one altitude up. It read *"of 17
        components, 3 … 9 … 5"*: internally consistent, and wrong against the
        tree, because it counted `docs/development/reviews/` — which
        `plan_activities.existing_work` excludes BY NAME as not a component, four
        lines from where the count was taken. A restated figure over mutable
        state is a copy with no gate on it, and this one was written by the very
        pass that was correcting a different false claim in the same sentence.
        The property is what this argument needs; the denominator was decoration.

    THE EXISTS-CHECK ALONE WAS NOT ENOUGH, AND THE GAP WAS THE RECOVERY PATH.
    "The directory exists" conflated a live component with one THIS PIPELINE
    seeded and then abandoned: a run dying between the seed being committed and
    its research finishing leaves a real directory holding nothing but the stub,
    and the documented `--pr` redispatch would skip it forever while the parent
    printed "an empty working set, not a skipped step" over a stranded candidate.
    A seeded-but-unresearched pool is therefore RESUMED rather than skipped,
    detected by the `_UNRESEARCHED` marker the first real research pass removes.

    WHICH HALF OF THAT GAP THIS ACTUALLY CLOSES, because the sentence above once
    claimed both. `research_write` REWRITES `synthesis.md` and commits before
    `research_verify` runs — its completion contract is a PR URL — so a component
    whose write succeeded and whose VERIFY then failed carries no marker and is
    read here as `extends`, not `resumed`. What is recovered is every component
    the run had not reached yet, whose seed a sibling's commit sweep carried onto
    the branch intact. The unrecovered half is not new and is not this activity's:
    a sprint-section component whose verify failed was equally unreachable on a
    redispatch before `plan-candidates` existed, because `new_sprint_sections`
    diffs from the redispatch's own base. Closing it means `research-verify`
    recording its own success, which is a change to a child two parents share.

    WHAT IT DOES NOT DO: no `roadmap.md`, no phase docs. `sprint.md` says every
    component gets both, and `plan-feature` writes them. This creates a folder
    and a seeded synthesis and stops.

    IDEMPOTENT (§7.1) by check-then-act — see the module docstring. A second run
    over an unchanged tree creates nothing; it re-reports the same resume and
    skip rows, which is a read rather than a write.

    Returns a `Scaffolded`, in file order. Every eligible ROW lands in exactly one
    of its buckets, so "nothing happened" can always be told from "nothing was
    eligible". The number of buckets is deliberately NOT stated here: it read
    "four" from the day this was written until `size` added two more, and the
    sentence's claim is the PROPERTY — one row, one bucket — which needs no
    denominator. `test_EVERY_field_of_Scaffolded_REACHES_THE_OPERATOR_as_its_own_
    note` is what holds the property, over whatever `_fields` currently is.
    """
    result = Scaffolded(created=[], resumed=[], extends=[], unnamed=[],
                        not_a_feature=[], unsized=[])
    rows = act.candidate_rows(candidates_path, missing_hint=(
        "Without it there is nothing to scaffold from, and the research step "
        "that reads what this creates has no input."))

    for row in rows:
        if row.decision != "ship" or row.status != "open" or not row.component:
            continue
        # THE NAME IS CHECKED BEFORE THE SIZE, and the first version of the size
        # branch had it the other way round. A cell that is not blank but slugs
        # to nothing is a filer typo whatever triage sized the row, and
        # `not_a_feature`'s note speaks of "the component its `component` cell
        # names" — a reference to a cell that, in this case, names nothing.
        # Reporting the typo first is the only
        # ordering under which every bucket's note is TRUE of the row in it.
        # `unnamed`'s note holds at every size: it says the cell needs a real
        # name or a blank and promises no scaffolding, which is exactly the
        # situation for a `phase`.
        slug = component_slug(row.component)
        if not slug:
            result.unnamed.append((row.id, row.component))
            continue
        # SIZE DECIDES WHETHER THIS SCAFFOLDS AT ALL, and before 2026-08-19 there
        # was no size — this activity inferred one from a proxy: if the named
        # component's directory did not exist, the candidate must be a new
        # component. Right for a `feature` and wrong for the other two. A
        # `phase`-sized candidate naming a component that happens to be new got a
        # whole component scaffolded around one phase of work, and a
        # `checkboxes`-sized one had no expressible form at all.
        #
        # BLANK IS SKIPPED RATHER THAN GUESSED AT, which is what makes the
        # backfill self-healing: the 29 rows ruled `ship` before this column
        # existed carry no size, and each heals when triage next reaches it. A
        # guess here would scaffold components for rows nobody has sized.
        if row.size != "feature":
            (result.unsized if not row.size else result.not_a_feature).append(
                (row.id, row.size or "unsized"))
            continue
        pool = component_dir(worktree, row.component,
                             source="`component` cell in candidates.md") / "research"
        # A COMPONENT ALREADY CLAIMED BY AN EARLIER ROW IS `extends` FOR EVERY
        # LATER ONE, and the exists-check alone gets that wrong. The second row's
        # directory does exist — but its `synthesis.md` still carries the marker
        # this loop wrote a moment ago, so `_is_unresearched` says yes and the
        # slug landed in `resumed` as well as `created`. The parent then printed
        # both notes for one component — "scaffolded from a shipped candidate"
        # and "seeded by an earlier pass and never researched" — of which the
        # second is false, and `to_research` carried the slug twice. Checked
        # BEFORE the marker, because the marker cannot tell this run's seed from
        # a previous run's.
        #
        # KEYED ON `to_research`, NOT ON `created`, AND THAT IS THE FIX RATHER
        # THAN A SECOND PATCH. It read `slug in result.created`, which closed the
        # created+created pair and left the structurally identical resumed+resumed
        # pair open: two rows naming a component a PREVIOUS run seeded and never
        # researched both passed the exists-check, both saw the marker, and both
        # appended — `resumed=['shared', 'shared']`, reproduced before this line
        # changed. `to_research` is the union the parent actually consumes, so
        # asking it is the question that has to be true for every bucket that
        # feeds research, including one added later. A bucket that does NOT feed
        # research (`extends`, `unnamed`) is per-ROW by design and must keep its
        # duplicates: two rows extending one component are two facts about the
        # file, and each is a separate note naming its own `C-NNN`.
        if slug in result.to_research:
            result.extends.append((row.id, slug))
            continue
        if pool.parent.exists():
            if _is_unresearched(pool):
                result.resumed.append(slug)
            else:
                result.extends.append((row.id, slug))
            continue
        pool.mkdir(parents=True)
        # `encoding` explicitly: the seed carries em dashes, and this is the one
        # place in the family that WRITES rather than reads. A read that fails on
        # a narrow locale fails before anything exists; a write that fails leaves
        # the directory `mkdir` just made, half-built and indistinguishable from
        # a component somebody is working on.
        (pool / "synthesis.md").write_text(_seed(row, slug), encoding="utf-8")
        result.created.append(slug)

    return result


def _is_unresearched(pool: Path) -> bool:
    """Does this pool still hold nothing but what `plan-candidates` seeded?

    Anything other than a synthesis still carrying the marker counts as
    researched — including a pool with no synthesis at all, which is a component
    somebody laid out by hand and which this activity has no business touching.

    `errors="replace"` IS THE POINT OF THIS READ, NOT A DETAIL OF IT. This is the
    only place the loop above reads a file it did NOT write, and it reads it
    while holding partially-created state: earlier rows have already `mkdir`'d
    and seeded, and step 1's model dispatch has already been paid for. A strict
    decode against a pre-existing `synthesis.md` that is not valid UTF-8 — any of
    the component pools predate this activity and none of them are its output —
    raises `UnicodeDecodeError` out of the loop and aborts the whole parent,
    which is exactly the cost the blank-`component` and punctuation-only-
    `component` cases were changed to avoid: *"it is REPORTED rather than raised,
    since the alternative aborted the parent after triage's dispatch was already
    spent"*. A row is not responsible for the encoding of somebody else's file.

    AND IT IS NOT A SWALLOWED ERROR, WHICH IS THE DISTINCTION THAT MAKES IT
    ALLOWED. `_UNRESEARCHED` is pure ASCII and this activity writes the marker
    itself in UTF-8, so a byte sequence that fails to decode cannot be part of
    it: replacing an undecodable byte can only ever turn a file that does not
    carry the marker into another file that does not carry it. The answer is
    therefore exact for every pool this activity seeded, and `False` — "not ours,
    leave it alone" — for one it did not, which is the correct classification
    rather than a degraded one.

    A genuine `OSError` (the pool is unreadable, the disk is gone) still
    propagates, deliberately: that is an environment fault the operator has to
    see, not a filer artifact this row can be blamed for.
    """
    seeded = pool / "synthesis.md"
    return (seeded.is_file()
            and _UNRESEARCHED in seeded.read_text(encoding="utf-8", errors="replace"))


def _seed(row: act.CandidateRow, slug: str) -> str:
    """The first document in a new component's pool — provenance, then the summary.

    Deliberately thin. It is a HANDOFF, not a research paper: it says where this
    came from and what was proposed, so the research child that runs next has a
    brief instead of an empty directory. `research_write` rewrites this file with
    real findings; anything more elaborate here would be written to be discarded.

    The `C-NNN` id is the load-bearing part. It is the only link back from the
    component to the row that authorised it, and without it a reader finding this
    folder cannot tell scaffolding from abandoned work.

    AND THE NEXT STEP OVERWRITES THIS FILE, so the id has to be handed ON rather
    than merely written down. `research_write`'s prompt says *"write (or fully
    rewrite) synthesis.md"* and its synthesis contract has no provenance field —
    so the id would live for exactly one pipeline step and be gone before any
    reviewer saw the PR. The seed asks for it explicitly, and the parent's brief
    for a scaffolded component asks again.

    `_UNRESEARCHED` is the marker that makes an abandoned seed recoverable; a
    rewrite removes it, which is precisely the signal wanted.
    """
    return (
        f"# {slug} — synthesis\n"
        f"\n"
        f"{_UNRESEARCHED}\n"
        f"\n"
        f"**This component arrived from project-wide planning as a candidate for "
        f"inclusion — [`{row.id}`]"
        f"(../../../tracked/candidates/{row.id}.md).** It was ruled "
        f"`ship` by `triage-candidates` and scaffolded by `plan-candidates`, which "
        f"creates the folder and this file and nothing else. **No research has been "
        f"done yet**, and the `roadmap.md` and phase docs that `plan-feature` writes "
        f"do not exist.\n"
        f"\n"
        f"> **Whoever rewrites this file: carry the `{row.id}` line above into what "
        f"you write.** It is the only link back to the row that authorised this "
        f"component, and a folder with no link back is indistinguishable from "
        f"abandoned work.\n"
        f"\n"
        f"## The candidate as filed\n"
        f"\n"
        f"{row.title}\n"
        f"\n"
        f"> That summary is a PROPOSAL, not a finding — it is what was written when "
        f"the candidate was filed, carried across verbatim. The next research pass "
        f"replaces this file.\n"
    )
