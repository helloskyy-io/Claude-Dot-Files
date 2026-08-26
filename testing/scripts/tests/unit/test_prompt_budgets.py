"""Every prompt carries a byte budget, and adding to one is a TRADE.

WHY THIS EXISTS. A prompt is not read once — it is re-sent on every turn of
every run, forever. Measured 2026-08-14: prompts in this tree grew 224 KB ->
317 KB in seven days, every byte of it a correct lesson, while a run's starting
context went 34k -> 57k tokens and cost per run went $1.90 -> $13.17. Tokens per
turn — which is model-independent, so not the model change — went up 4x.

WHY A BUDGET AND NOT REVIEW DISCIPLINE. All of that growth happened under
review, by people who were right about each individual addition. Adding is
visible work; removing is nobody's job. A ratchet does not need anyone to be
careless. A budget makes each addition compete with what it displaces, which is
the only question that was never being asked.

WHAT THIS IS NOT. It is not a cap on rigour and it is not a claim that any
current prompt is too long. Budgets below are set at each file's CURRENT size,
so this test passes on the day it lands and constrains only what happens next.

RAISING A BUDGET IS A NORMAL DECISION. Change the number, say why in the commit.
What this prevents is raising it SILENTLY, as a side effect of adding text.

See `docs/standards/workflow-scripts.md` § Prompt economy for what earns a place
in a prompt at all.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PROMPTS = REPO_ROOT / "scripts" / "workflows" / "temporal" / "modules" / "assistant"

# path relative to PROMPTS  ->  budget in bytes.
# Set at the file's size on 2026-08-14 unless a note says otherwise.
BUDGETS: dict[str, int] = {
    # THE OUTLIER, AND THE ONE WORTH SHRINKING. 4x the next-largest, loaded on
    # every review, and 56% of the kernel's 131,072-byte argv ceiling on its own.
    # A line-by-line classification on 2026-08-14 found only 34% of it is
    # imperative; 19% is evidence that belongs in commits. Budget is set at
    # today's size rather than at a target: this test's job is to stop the
    # ratchet, and shrinking it is separate work with its own reasoning.
    # RAISED 372 BYTES on 2026-08-16 for two rules, and the accounting is stated
    # because this is the file that most needs shrinking rather than growing.
    # Added: an ESCALATED ownership condition (a PR that BUILT the fixing
    # mechanism owns the defect, however far it predates the branch — without it
    # a PR can ship a safety control, apply it partially, and escalate the rest
    # past its own review), and a COMPARATIVE convergence floor ("would this have
    # blocked on pass 1's own bar?", answerable against the prior pass's durable
    # yaml rather than judged alone). 315 bytes were funded by cutting three
    # evidence anecdotes; 372 is the residue. The shrink pass this file needs is
    # still owed and is tracked separately — this is not it.
    # RAISED 4 BYTES on 2026-08-16, and the trade is the smallest this gate has
    # been asked to rule on: NOT new content, but one term corrected in place.
    # The line cites `exit-protocol.md` §2.1 for "the Kind 2 record"; the memory
    # taxonomy is now cut on lifecycle and that document no longer carries the
    # label anywhere, so the citation named a term its target had stopped using.
    # (§2.1 itself never carried it — the label lived in §1, §2's requirement
    # table and §6 — so the citation was pointing past the term as well as at a
    # retired one.) "typed exit record" is 4 bytes longer than "Kind 2 record"
    # and nothing was added around it.
    # Stated rather than absorbed, because a 4-byte raise on the file that most
    # needs shrinking is exactly the kind that gets waved through silently.
    # RAISED 75_872 -> 76_004 for the pass-1-only sweep scope. The arithmetic is
    # not close: 132 bytes re-sent per turn against a loop-back measured at ~145,000
    # output tokens (a refine at ~92k plus a review at ~53k). This clause exists to
    # remove loop-backs. Partly funded by deleting a second current-tree anecdote —
    # one example already carried that rule.
    # 76_004 -> 76_507: the pass-scope clause shipped too broad. It banned ALL
    # re-searching, including the sweep-from-a-different-angle that closed a
    # credential-leak class on PR #233. Now it bans repeating a prior search and
    # permits a new angle, stated. Fixing the defect costs more bytes than the
    # defect did — that is the trade, and it still removes loop-backs.
    # 76_507 -> 77_115 for the asymmetric-presence sweep. It cleared the two-PR
    # bar the hard way: #96 and #100 each produced their HEADLINE finding from it,
    # and neither was reachable by the deleted-artifact sweep beside it, because
    # nothing had been deleted — something was added to one side of a pair only.
    # 77_115 -> 77643: the reviewer picks the dispatch tool and was never told
    # `-minor` is a LESS CAPABLE MODEL. Its whole sizing axis was scope and turn
    # caps, so a scoped-and-known fix needing judgement routed to the weak tier.
    # 77643 -> 78068 -> 78_926: this body is SHARED by all three ReviewType
    # values, and its `dispatch_tool` enum named build and planning tools only.
    # `criteria_research.md` routes "a defect verify should have caught" to
    # REDISPATCH and the universal core forbids FILING a defect that is the run's
    # own scope — so a research reviewer reached that exit with no legal value to
    # emit. The residue is two sizing rows read from the modules, the two shim
    # names, and one type-matching line; ~1.5 KB of rationale for them was cut
    # before this number moved, which is the mechanism working.
    # +120 ON 2026-08-24, and it buys a WIDER POPULATION rather than more prose.
    # The asymmetric-presence sweep said "run it on every artifact this PR
    # TOUCHED that has a sibling". Measured across three passes on PR #138:
    # all three hits were on artifacts the PR never opened, one of them in a
    # different component. The sibling that matters is usually the one nobody
    # edited — which is exactly why it went stale — so a population keyed on
    # the diff cannot reach it. Now keyed on "makes a claim about what this PR
    # changed, touched or not". Changes what the model DOES, which is the test
    # `workflow-scripts.md` § Prompt economy sets for an addition.
    # RAISED 79_046 -> 81734 on 2026-08-26 (+2688): GitHub Issues retired as a
    # store, so the filing authority changed MECHANISM and gained a fourth route.
    # Against § Prompt economy's four questions — it changes what the model DOES
    # (it emits an intake body with a store field where it used to open a plain
    # issue); a capable reasoner would NOT infer it, because the label, the
    # frontmatter keys and the three permitted stores are conventions, not
    # deductions; the harness enforces only the REFUSALS (a bad store, an
    # operator-only field), which fire after the model has already written the
    # thing, so the format has to be stated up front; and the evidence — the 21
    # unenumerable amendments, the id-collision history — is in the commit
    # message, not here. A first draft ran +3,432; the trim removed
    # measurements and one justification a reader infers from the rule above it.
    # RAISED 81734 -> 82627 on 2026-08-26 (+893) for the RECURRENCE CHECK, which
    # is the half of §3.1 that was missing: the standard says increment rather
    # than open a second item, and said nothing about how a filer KNOWS. Against
    # § Prompt economy — it changes what the model DOES (a read of the store now
    # precedes every filing, and "already there" became a terminal disposition);
    # a capable reasoner would NOT infer it, because the instinct is to file and
    # the asymmetry that says otherwise is counter-intuitive; the harness cannot
    # enforce it, since deciding two findings are one finding is exactly the
    # judgement `recurrence.py` refuses to automate; and the measurement behind
    # it — four nominated for merging, one surviving — is in the commit, not here.
    "review_pr/prompts/disposition.md": 82627,
    "plan/plan_revision/prompts/stages_1_to_5.md": 22_506,
    # RAISED 19 BYTES on 2026-08-16, deliberately, for C-f0lfdhmm's remedy — "ask what
    # each guard does NOT look at". Paid for by removing a 280-byte anecdote; the
    # residue is 19 bytes. Worth stating because this is the mechanism working
    # rather than failing: the addition competed, most of it was funded by a cut,
    # and the remainder is a number changed on purpose with a reason attached.
    # RATCHETED DOWN 21_899 -> 17_358: twelve blocks it shared verbatim with
    # build_refine_minor moved to six shared fragments under prompts/. CONTENT
    # DID NOT SHRINK, IT MOVED — the same 4,541 bytes are still sent on every
    # refine run, they are just sent from one place instead of two. The budget
    # follows the bytes so the vacated 4.5 KB cannot quietly refill.
    # Then 17_358 -> 17_370, and the twelve bytes NEVER REACH THE MODEL: the
    # correction pass renamed the fragment `resolve_fix_by_default` ->
    # `resolve_fix_by_default_and_summary`, so `${RESOLVE_FIX_BY_DEFAULT}` grew
    # by twelve characters that `render()` substitutes away before dispatch.
    # Raised rather than absorbed because this table measures the FILE, which is
    # the right proxy almost always and is a slight over-count exactly here —
    # and a budget quietly wrong by twelve bytes is worse than one raised on
    # purpose with the reason attached.
    # RATCHETED DOWN 17_370 -> 15_345: two more blocks moved out, to
    # prompts/resolve_rejections_must_be_executed.md and
    # prompts/resolve_disposition_definitions.md. THE ACCOUNTING IS DIFFERENT
    # FROM THE MOVE ABOVE and worth stating: these two were NOT verbatim copies
    # when the pass began — each tier carried one sentence the other lacked, so
    # the second correction pass unioned them first. So this file GAINED 97
    # bytes of substance (the minor tier's measured-evidence sentence, which
    # every refine run now reads) and then LOST 2,122 to the promotion. The net
    # is a ratchet down; the substance change is a raise, and both are here so
    # neither hides inside the other.
    # RATCHETED DOWN 15_345 -> 11_057: six more blocks moved out, to
    # prompts/fidelity_read_and_compare.md, fidelity_evidence_discipline.md and
    # fidelity_mutate_what_you_added.md. SAME ACCOUNTING AS THE MOVE ABOVE and
    # the two movements run opposite ways, so both are stated rather than netted:
    # this file GAINED 1,431 bytes of substance — five `Measured:` evidence
    # sentences the minor tier alone carried, which every major refine run now
    # reads. It then LOST the whole 4,383-byte span to three placeholder lines
    # costing 95: 15,345 - 4,383 + 95 = 11,057, which is the number below.
    # ALL SIX PAIRS WERE ONE-SIDED ADDITIVE, which is why a union could only add:
    # verified by rendering both tiers before and after and diffing, opcode kinds
    # `equal`/`insert` ONLY, so nothing was replaced, deleted or invented.
    # THE COMPONENT FIGURES ARE BYTES, NOT CHARACTERS, and the first draft of
    # this comment had them in characters — off by 90 on this file — which is the
    # exact error the `plan_verify` note below warns about. Em-dashes are three
    # bytes each and this prompt is full of them.
    "build/build_refine/prompts/stages_2_to_4.md": 10294,
    # 21_619 -> 8_466 in the 2026-08-19 rebuild. It SHRANK BY 61% while gaining
    # the job it was missing. What left: the five-condition bar for "does this
    # warrant a sprint section", and the ranked placement choice over ruled
    # candidate rows. Both answered a question the chain above already answers by
    # BUILDING the thing — a component arriving with a roadmap, phase docs and an
    # estimate per phase has been ruled. What arrived is smaller: place a
    # computed total, reconcile one component's bullets against its roadmap.
    # (This paragraph was here TWICE, the two copies disagreeing on whether the
    # number was 8466 or 8_466 and neither reaching the value on the line below.
    # A duplicated entry in the one file whose job is to make prompt growth
    # legible is the thing this file exists to prevent, one level up.)
    # 8_466 -> 8_830: the no-precedent-yet case, from the first run.
    # 8_830 -> 9_230 on 2026-08-19 with the `size` column. The prompt tells the
    # run to COPY the neighbouring sections' form; two runs read that and still
    # inferred a shape, so the section and the phase-bullet shapes are now stated
    # outright — 400 bytes buying the removal of a re-dispatch. Nothing was cut to
    # fund it: this file is a fifth the size of the outlier above and the ratchet
    # it guards against is growth without a reason, not growth.
    # +610 ON 2026-08-25, and it REPLACES a restatement that had gone false.
    # The House-style section stated the shapes — `## Sprint: <name> — <marker>`
    # heading, a `**Planning:**` line, a one-line bullet — and all three were
    # wrong within a fortnight of the 2026-08-19 format change: the marker moved
    # to its own line and gained derived hours, the `Planning:` line was deleted
    # outright, and bullets gained a component prefix and two links. The prompt
    # would have told this workflow to write a format the file no longer uses.
    #
    # What replaces it is SHORTER per shape and does not rot: copy the
    # neighbours, plus the four rules a neighbour cannot show you — marker
    # derived not chosen, hours derived, phases cited by name not number, and
    # every sprint ends with a close-out. Changes what the model DOES, which is
    # the test `workflow-scripts.md` § Prompt economy sets.
    # RAISED 9840 -> 9904 on 2026-08-25 (+64): the UNSIZED sentence had to stop
    # saying a COMPLETE phase carries no estimate by design. It now does carry
    # one, so an unsized phase has no benign case and the reader must treat every
    # member of that list as a defect. Changes what the model DOES with the list.
    # +10 on 2026-08-26: the MAY-NOT row named `candidates.md`, a file that is
    # no longer the store. "anything under `tracked/`" is the true prohibition
    # and it is WIDER — it now also covers the three stores plan-sprint never
    # had a reason to touch, `operations/` included, which §1.2 reserves to
    # humans. A prohibition naming a retired surface reads as permission for
    # what replaced it.
    "plan/plan_sprint/prompts/plan_sprint.md": 9914,
    # RATCHETED DOWN 16_060 -> 9_919: the mutation discipline moved to the shared
    # prompts/mutation_discipline.md, budgeted below. Content did not shrink, it
    # MOVED — so both lines exist and neither absorbs growth silently.
    "build/build_draft/prompts/stages_1_to_4.md": 9_919,
    # SET AT ITS SIZE ON THE DAY IT LANDED, not on 2026-08-14: this prompt was
    # in flight on `build/plan-feature` when the budget test was written on
    # `main`, so it is the first file to meet this gate rather than be measured
    # into it. Same rule, one commit later — the number is today's size and its
    # job is to make the NEXT addition a trade.
    # RAISED 17,821 -> 18,051 (+230) on 2026-08-15, and the raise IS the trade
    # this gate exists to force. The prompt told the model *"`plan-verify` … does
    # not exist yet"*, which the same PR that built `plan-verify` made false. The
    # correction is longer than the sentence it replaces because it has to say
    # what the reader now DOES — reads the roadmap cold, writes the hours this
    # prompt forbids, answers the question this run cannot ask of itself — and
    # that changes what the model writes, which is this table's own bar for a
    # raise. Measured with `wc -c`, in BYTES.
    # 18_051 -> 20820: the six inputs this child was never handed. It already got
    # the synthesis (PRIMARY) and the raw pool to backtrack into. It did NOT get
    # docs/file_structure.txt, the CLAUDE.md chain, the PROJECT-level research
    # pool, or sprint.md — the last one named five times as a prohibition and
    # never as a read, while Stage 4 requires it to propose the sprint entry this
    # component needs. A proposal into a sequence nobody has seen is a guess.
    # Also: WebSearch/WebFetch were granted by --dangerously-skip-permissions and
    # never mentioned, so a run designing against a real API planned from memory;
    # and four standards paths were hardcoded in a workflow that takes --repo.
    # The correction path is what makes these load-bearing rather than nice: a
    # plan-project loop-back goes to plan-sprint, so a defect in THIS child's
    # output may not be fixable downstream at all.
    # 20_820 -> 21_828: the MERGE rule. This prompt said SPLIT in five places and
    # said combine in none, so a plan could only ratchet toward more phases. The
    # first run produced six for a component with small remaining work, said in
    # its own report that two should probably be one, named which two, and shipped
    # six anyway — the verb did not exist.
    # 21_845 -> 23422: an INITIAL plan numbers 1,2,3 in rollout order, and a
    # RELOCATED phase leaves no tombstone. The first run produced 1,2,5,3,6 with
    # a "Phase 4 — RETIRED" heading and was following the standard as written:
    # the immutability rule reads unconditionally, so it applied to a plan
    # nothing had cited yet. Operator ruling — the rule protects PUBLISHED
    # addresses, and before publication a tidy plan is strictly better.
    # +8 on 2026-08-19: `size` joined `decision` and `status` in the MAY NOT
    # column. The word is 8 bytes and nothing was added around it. Recorded even
    # so — the same reason the 4-byte raise at the top of this file is recorded:
    # an 8-byte raise is precisely the size that gets waved through, and the
    # habit is what the gate is, not the number.
    # +7 on 2026-08-20, and the trade is a CORRECTION rather than new content.
    # The enforcement list beneath the MAY NOT table read "All three candidate
    # columns — `decision`, `status`, `component`" after `size` became the
    # fourth one actually compared. It now names four. "three" -> "four" is -1
    # and "`size`, " is +8. The prompt's list closes by promising exactly one row
    # is NOT mechanically checked and naming which, so an omitted column made
    # that promise false in the expensive direction: the model learns the column
    # is on the honour system and the guard then fails the whole run.
    # +362 on 2026-08-20, and it buys ONE bullet plus a numeral this list no
    # longer has to hand-maintain. The list heads itself "exactly what checks
    # it" and closes by promising exactly ONE row is not mechanically checked --
    # yet the table's FIRST MAY NOT row, "Estimate hours, or size the work in
    # any unit of time", appeared nowhere beneath it, while `own.hour_hits`
    # checks it on every run. A reader had to leave the list to learn that,
    # which is what a completeness promise exists to make unnecessary. The
    # bullet is +367; "All four candidate columns" -> "Every candidate column"
    # is -4 and the agreement fix "are" -> "is" is -1. The count now derives
    # from the enumeration beside it instead of being remembered, which is the
    # class this repo paid four correction passes for on PR #101.
    # +656 on 2026-08-20, and NEITHER SIDE OF THE REBASE HAD THE RIGHT NUMBER.
    # This branch pinned 24211 against a base that has since moved and main
    # pinned 23826 without this branch's bullet; the figure below is the file
    # MEASURED after the rebase, not either remembered value. It buys the
    # `git ls-files` half of the ignore check — `git status` showing a file as
    # untracked proves it is unstaged, not that it is unignored, and the two
    # answers diverge exactly when a `.gitignore` rule matches something the
    # run just created.
    #   -1045 on 2026-08-22, MEASURED DOWNWARD RATHER THAN LEFT STALE. Both
    #   halves of that check are now the shared `gitignore_collision_check`
    #   fragment and this file renders the placeholder, so the text left the
    #   prompt without leaving the run. A budget that keeps the old ceiling
    #   after a promotion silently re-grants the space the promotion freed,
    #   which is how a prompt gets back to its old size with nobody deciding it.
    "plan/plan_feature/prompts/plan_feature.md": 23_437,
    # 15_510 -> 13_204: the `research-analyst` re-dispatch is gone. The verify
    # child holds Write/Edit and applies the critic's findings itself, so the
    # rules that existed only to coordinate a second writing agent went with it
    # — the resume contract, "do not transcribe", and the critic-authors /
    # analyst-signs split. Stages 2 and 3 also folded into the one critic pass.
    # 13_204 -> 15_081: a WRITE BOUNDARY, because PR #105 widened this child's
    # scope to everything the PR ships and did not widen its lane with it. On the
    # first run under that scope it edited a roadmap and two workflow docstrings —
    # all three edits CORRECT, none of them its to make, and one against a runway's
    # explicit DO-NOT-TOUCH. The block carries its own exit: report it, do not fix
    # it, because a boundary with no route turns a real finding into a silent drop.
    "research/research_verify/prompts/verify.md": 15_084,
    # SET AT ITS SIZE ON THE DAY IT LANDED, like `plan_feature.md` above and for
    # the same reason: this prompt is new, so it MEETS this gate rather than
    # being measured into it. Measured in BYTES with `wc -c`, never eyeballed —
    # the first draft of this table counted characters and was wrong by 49 on a
    # file full of em-dashes.
    #
    # RAISED 12_557 -> 13_142 by the review pass, and the +585 bought ONE thing:
    # the enforcement list used to tell the model *"the roadmap must carry at
    # least one hour estimate per phase doc"*, which is not what the code checks.
    # The code compares a TOTAL against a TOTAL and cannot see which phase an
    # estimate sits beside, so two figures against one phase satisfy it while
    # another phase has none. That gap is not closable in code — every candidate
    # association fails a correct run (see the guard's own comment) — so the
    # model is the only thing that can close it, and it could not while the
    # prompt told it the machine was already checking. This clears the gate's
    # own bar: it changes what the model DOES, and the harness cannot enforce it.
    # 13_142 -> 15577: the reviewer was reading FIVE documents where the planner it
    # judges reads ten. Three of the five it lacked bear directly on its own job:
    # stack_reference's "what we do NOT use" (a phase planned on ruled-out tech is
    # the finding no other reader is positioned to catch), sprint.md (it produces
    # the numbers that feed the sprint, against a sprint calibration, having never
    # seen one), and the web (sizing "build X against vendor Y's API" is answerable
    # by reading Y's docs, and the grant was live but unmentioned). Plus
    # ${TASK_CONTEXT}, so a --pr pass can be told why it is re-running.
    # + the DETERMINED-vs-JUDGEMENT split. The old prohibition bundled two rules
    # under one reason: "do not re-plan" (right, and unchanged) and "edit no
    # phase doc" (far broader than the reason given). The second is what made a
    # reviewer spend 1,500 bytes describing a one-sentence fix — the exact smell
    # engineering-quality.md names. Fixing a determined defect is now in scope;
    # re-planning is not, and the observers that always enforced that half do it.
    # +8 on 2026-08-19, the same `size` in the same MAY NOT column as
    # `plan_feature.md` above, for the same 8 bytes.
    # +7 on 2026-08-20, the same corrected sentence as `plan_feature.md` above
    # and for the same reason, byte for byte.
    # RATCHETED DOWN 18142 -> 18137 on 2026-08-20: -4 for the same dropped
    # numeral as `plan_feature.md` above ("All four candidate columns" ->
    # "Every candidate column") and -1 for the same agreement fix. Ratcheted
    # rather than left slack, because a budget five bytes loose is exactly the
    # room the next unrecorded addition slips into.
    # RAISED 18137 -> 18334 on 2026-08-25 (+197). The COMPLETE-phase exception
    # added on 2026-08-19 was DELETED: every phase is sized on every run.
    # Against § Prompt economy's four questions — it changes what the model DOES
    # (the rule inverted); a capable reasoner would NOT do it anyway, because the
    # prompt previously said the opposite and the floor's arithmetic is invisible
    # from here; the harness does NOT already enforce it, it enforces the
    # CONTRARY and fails the run at its last guard, destroying the work; and the
    # evidence — the run it failed, the PR that introduced it — is in the commit
    # message, not in these bytes. A first draft ran +527; the trim to +197 took
    # out the history and the third bullet a reasoner infers from the first.
    "plan/plan_verify/prompts/plan_verify.md": 18334,
    # RATCHETED DOWN 14_437 -> 9_896, the other side of the same move. It stays
    # above the FLOOR, so it keeps its line rather than dropping off the table.
    # Then 9_896 -> 9_908, the same twelve substituted-away bytes as above.
    # RATCHETED DOWN 9_908 -> 7_988, the other side of that second move: +202
    # for the major tier's RULING-REQUIRED clause, then -2,122 to the same two
    # fragments — the identical removal, which is what "they were copies" means
    # once the union has run. It has
    # now fallen BELOW the 8,000-byte FLOOR and keeps its line anyway: dropping
    # it would let the file regrow to 8,000 unbudgeted, which is the ratchet
    # running backwards. The floor decides what must ACQUIRE a budget, never
    # what may lose one.
    # RATCHETED DOWN 7_988 -> 2_693, the other side of that third move: +424 for
    # the major tier's `gh pr view` truncation warning — the one pair of the six
    # where the MAJOR tier was the superset — then its 5,390-byte span went to
    # the same three placeholder lines costing 95: 7,988 - 5,390 + 95 = 2,693.
    # The two spans differ (4,383 vs 5,390) because each tier's copy was its own
    # size before the union; the FRAGMENTS they both now read total 5,814.
    # It sits far below the FLOOR now and still keeps its line, for
    # the reason already stated above: the floor decides what must ACQUIRE a
    # budget, never what may lose one, and dropping the line would let 5 KB of
    # vacated space refill unwatched.
    "build/build_refine_minor/prompts/stages_2_to_4.md": 2989,
    # 13_670 -> 19_668 on 2026-08-19, and this is the largest single raise the
    # gate has been asked to rule on. It buys TWO rulings the workflow was not
    # making, and the accounting is stated at this length because a 44% raise on
    # one prompt is exactly the shape that should have to argue for itself.
    #   ~2_400  THE WORTHINESS TEST. Triage's whole bar was "can this be
    #           scheduled?" — a READINESS question that says nothing about
    #           whether the work is worth doing, so a perfectly schedulable
    #           candidate serving nothing this platform is building passed it
    #           cleanly. The prompt now asks the hard question FIRST and names
    #           where the trajectory is written, because "does it serve the
    #           thesis" is unanswerable without an address to check it against.
    #   ~3_600  THE `size` RULING — the vocabulary, the five-question feature
    #           test, and the two OPPOSITE meanings of "it needs no research of
    #           its own". This one replaces code, and that is the trade: the
    #           inference it removes lived in `plan_candidates` as a proxy — no
    #           directory, therefore a new component — which was right for one of
    #           three cases and silently wrong for the other two.
    # NOT FUNDED BY A CUT, and the honest reason is that there was nothing in
    # this prompt to cut: it is a fifth the size of the outlier at the top of
    # this file, and every byte of the removed inference was in Python, not here.
    # +385 on 2026-08-20 — ONE BULLET, and it is a disclosure this prompt
    # already promised. Line 32 says "Every row in that MAY NOT column is
    # enforced, not requested, and here is exactly how", and the list that
    # follows accounted for `status`, `component`, paths and deletion while
    # `size` appeared in it zero times — under a closing guarantee that names the
    # single unchecked row. The `size` prohibition IS wired
    # (`own.sized_without_shipping`), so the list under-claimed: two rows read as
    # unaccounted while the prompt swore there was one, and it named the wrong
    # one as the exception. NOT FUNDED BY A CUT for the reason the entry above
    # gives — the alternative was deleting a correct disclosure to buy a correct
    # disclosure. The bullet says what the pairing check reads and why it needs
    # no before-snapshot, which is the part a model cannot infer from the row.
    # +10 ON 2026-08-21, AND IT BUYS NOTHING THE MODEL READS. Candidate ids went
    # from `C-NNN` to `C-` plus eight base36 characters, because the sequential
    # scheme allocated "the next free id" from a stale snapshot and collided six
    # times. This prompt cites two ids by name; five bytes each is the entire
    # increase. Funded by nothing, deliberately: the alternative is deleting a
    # sentence to pay for a rename, and no cut here would have been made on its
    # own merits.
    "plan/triage_candidates/prompts/triage_candidates.md": 20_063,
    # 12_313 -> 13_941: a MINOR cycle now writes a synthesis. The earlier prompt
    # forbade it on the argument that with one paper the roll-up IS the paper —
    # true on run 1, false on run 2, since papers accumulate and the synthesis is
    # replaced. Without it a planner reports "no synthesis" and plans from priors
    # while the paper sits unread, which wastes the whole cycle.
    # 13_941 -> 15_131: the CONTRACT was wrong, and the prompt is where it was
    # wrong. This workflow takes a TOPIC and produces the basis a planner plans
    # from; the prompt said "one question" and told a run to STOP if handed
    # several concerns. A run followed it, narrowed a four-concern brief to one
    # question, and produced 1,055 lines covering a quarter of the ground at the
    # same cost. Also gained: the inputs it is expected to read (feature docs,
    # project synthesis, the project research pool it must not re-derive),
    # write-time quote verification by byte-exact GET, and the topic-has-moved
    # case that was previously undefined. ~2,300 bytes of measurement narration
    # were cut to pay for it, per `workflow-scripts.md` § Prompt economy — the
    # figures belong in a commit, not on every turn of every run.
    # 15_131 -> 16_212: SIZE IS A RATE. The flat 20-source ceiling made the
    # OPERATOR carry the sizing decision — remember that a five-phase feature needs
    # the bigger instrument. Now 5 sources and ~60 body lines per FACET, which is
    # the unit Research Standard §3 already uses, so it scales with the feature.
    "research/research_write_minor/prompts/write_minor.md": 16_236,
    "research/research_write/prompts/write.md": 11_669,
    "build/build_draft_minor/prompts/update_pr.md": 10_675,
    # SHARED FRAGMENTS ARE THE EXPENSIVE ONES — every workflow that includes one
    # pays for it, so a byte here costs more than a byte in any single prompt.
    # RAISED 9_605 -> 9_810 for the one-line rigour-tier declaration. The tier rule
    # existed in the prompt and the standard and NOTHING checked it was applied, so
    # the operator was the enforcement mechanism and asked four times in three days.
    # Paid for by a raise rather than a cut: the fragment carries no duplicated
    # sentences, so funding it meant deleting substance to hit a number.
    # +5 on 2026-08-26: the PROPOSAL route names `tracked/candidates/` and one
    # file per item, where it named `candidates.md` and "append a row with the
    # next free C-NNN". Both halves of that were wrong after the flip — there is
    # no row to append and ids are not sequential.
    "prompts/decision_log_and_reflection.md": 9_815,
    # 8,106 not 8,057 — the first draft of this budget counted CHARACTERS and
    # this file is full of em-dashes. The test caught it on its first run,
    # which is the cheapest possible demonstration that byte counts are not
    # eyeballable.
    # +67 on 2026-08-20, and it buys a CORRECTNESS fix rather than prose. The
    # re-read rule illustrated its point with `/tmp/claude-pr-body.md`, and an
    # example in a prompt is a prescription in practice: the logs show that exact
    # path copied VERBATIM 133 times across 45 runs. A fixed name in a shared
    # directory is overwritten by any sibling dispatch, and the visible outcome is
    # a PR published with another PR's body. The name now carries the branch.
    "prompts/rules.md": 7_558,
    # RATCHETED DOWN 6_584 -> 6_164 on 2026-08-17: a five-line `<!-- SHARED … -->`
    # editor header was deleted. It was addressed to whoever edits the file and
    # reached the MODEL instead — `load_prompt()` is a bare `read_text()` and
    # `render()` substitutes `${…}` without stripping anything — so 420 bytes of
    # provenance shipped ahead of the first instruction on every plan-driven
    # draft dispatch. It fails § Prompt economy on three of the four questions in
    # this file's own failure message, and its `Measured on PR #99` is the
    # evidence-in-a-prompt case that section names by example. The provenance now
    # lives only in git history and in both draft workflows' Python comments,
    # which is where an editor is looking. Enforced by
    # `test_no_prompt_ships_EDITOR_COMMENTARY_to_the_model` below.
    "prompts/mutation_discipline.md": 6_164,
}

# A prompt below this is not worth a budget line; the total of all of them is
# smaller than the noise in the two biggest files.
FLOOR = 8_000


def _all_prompts() -> list[Path]:
    found = [p for p in PROMPTS.rglob("*.md") if "prompts" in p.parts or p.name == "rules.md"]
    assert len(found) > 20, (
        f"only {len(found)} prompt files found under {PROMPTS} — the glob is wrong, "
        f"and a budget test that measures nothing passes silently"
    )
    return sorted(found)


@pytest.mark.parametrize("rel", sorted(BUDGETS), ids=lambda r: r.split("/")[-1])
def test_a_prompt_stays_within_its_budget(rel: str) -> None:
    path = PROMPTS / rel
    assert path.is_file(), (
        f"{rel} is budgeted but does not exist. If it moved, move its budget line; "
        f"if it was deleted, delete the line — do not leave a budget pointing at nothing."
    )
    size = path.stat().st_size
    budget = BUDGETS[rel]
    assert size <= budget, (
        f"{rel} is {size:,} bytes against a budget of {budget:,} "
        f"(+{size - budget:,}).\n\n"
        f"A prompt is re-sent on EVERY TURN of every run. Before raising this number, "
        f"check the addition against `workflow-scripts.md` § Prompt economy:\n"
        f"  · does it change what the model DOES, or only what it knows?\n"
        f"  · would a capable reasoner do it anyway?\n"
        f"  · does the harness already enforce it?\n"
        f"  · is it evidence — a date, a run id, a count of occurrences? That belongs "
        f"in the commit message, not here.\n\n"
        f"Raising the budget is a normal decision. Raising it silently is what this "
        f"test exists to prevent."
    )


def test_every_prompt_over_the_floor_HAS_a_budget() -> None:
    """A new large prompt must arrive with a number, not slip in unbudgeted."""
    unbudgeted = []
    for p in _all_prompts():
        rel = str(p.relative_to(PROMPTS))
        if rel in BUDGETS:
            continue
        if p.stat().st_size > FLOOR:
            unbudgeted.append((rel, p.stat().st_size))
    assert not unbudgeted, (
        "these prompts are over the "
        f"{FLOOR:,}-byte floor and carry no budget:\n"
        + "\n".join(f"  {r}  ({s:,} bytes)" for r, s in sorted(unbudgeted, key=lambda x: -x[1]))
        + "\n\nAdd a line to BUDGETS at the file's current size. The budget is not a "
        "judgement that the file is too big — it is what makes the NEXT addition a trade."
    )


def test_no_prompt_ships_EDITOR_COMMENTARY_to_the_model() -> None:
    """An HTML comment in a prompt is addressed to an editor and read by a model.

    THE WHOLE CLASS, NOT THE THREE INSTANCES THAT WERE FOUND. Markdown hides an
    `<!-- … -->` from a human previewing the file, which is exactly why it reads
    as free: it looks like a code comment and behaves like prose. It is not free.
    `load_prompt()` is a bare `read_text()` and `render()` only substitutes
    `${…}`, so every byte between the markers is sent on every turn of every run
    that loads the file.

    MEASURED, and the count went the wrong way twice before it went right. One
    such header existed when PR #100 was cut; the draft pass ADDED two more by
    promoting two whole files with their headers attached, putting the literal
    first line a plan-driven build reads ahead of its own first instruction; the
    first correction pass deleted its own two and left the original, returning
    the class to a baseline of one rather than to zero. Three review passes each
    re-derived the same measurement by hand from `grep -rl '<!--'`. This is that
    grep, kept.

    NO FROZEN BASELINE, deliberately, and it is the one guard here that has
    none. A baseline is what you build when the population is too large to fix in
    one change — 48 duplicated blocks were. This population was ONE file and five
    lines, so freezing it would have recorded a decision to keep paying rather
    than made the next addition a trade, which is the permanent-excuse-list shape
    the duplication baseline's own docstring warns against.

    WHAT IT DOES NOT LOOK AT: only `<!-- -->`. Commentary written as ordinary
    prose — a paragraph explaining to an editor why a fragment lives where it
    does — is indistinguishable from instruction to any check, and belongs to
    § Prompt economy's four questions and a human reading them.
    """
    offenders = [
        (str(p.relative_to(PROMPTS)), p.read_text().count("<!--"))
        for p in _all_prompts()
        if "<!--" in p.read_text()
    ]
    assert not offenders, (
        "these prompt files carry HTML comments, which are invisible in a "
        "markdown preview and fully visible to the model:\n"
        + "\n".join(f"  {r}  ({n} comment{'s' if n > 1 else ''})" for r, n in offenders)
        + "\n\nMove the note to the commit message, or to a Python comment beside "
        "the `shared_prompt(...)` call that loads the fragment — both are where an "
        "editor is actually looking, and neither is re-sent on every turn."
    )


def test_the_fleets_TOTAL_prompt_weight_is_reported() -> None:
    """Not a limit — a number that must stay visible.

    The 42%-in-seven-days growth was invisible because nobody was looking at the
    total. Per-file budgets cannot see it either: thirteen files each gaining
    300 bytes breaks no budget and adds 4 KB to every run.
    """
    total = sum(p.stat().st_size for p in _all_prompts())
    budgeted = sum(BUDGETS.values())
    print(
        f"\n  fleet prompt weight: {total:,} bytes across {len(_all_prompts())} files"
        f"  ({budgeted:,} of it budgeted, {budgeted / total * 100:.0f}%)"
    )
    assert budgeted / total > 0.5, (
        f"only {budgeted / total * 100:.0f}% of prompt bytes are under a budget, so the "
        f"total can grow freely in the unbudgeted remainder. Lower FLOOR or add lines."
    )
