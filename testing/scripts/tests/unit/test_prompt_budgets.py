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
    "review_pr/prompts/disposition.md": 75_872,
    "plan/plan_revision/prompts/stages_1_to_5.md": 22_506,
    # RAISED 19 BYTES on 2026-08-16, deliberately, for C-089's remedy — "ask what
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
    "build/build_refine/prompts/stages_2_to_4.md": 15_345,
    "plan/plan_sprint/prompts/plan_sprint.md": 21_619,
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
    "plan/plan_feature/prompts/plan_feature.md": 18_051,
    "research/research_verify/prompts/verify.md": 15_510,
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
    "plan/plan_verify/prompts/plan_verify.md": 13_142,
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
    "build/build_refine_minor/prompts/stages_2_to_4.md": 7_988,
    "plan/triage_candidates/prompts/triage_candidates.md": 13_670,
    "research/research_write_minor/prompts/write_minor.md": 12_313,
    "research/research_write/prompts/write.md": 11_669,
    "build/build_draft_minor/prompts/update_pr.md": 10_675,
    # SHARED FRAGMENTS ARE THE EXPENSIVE ONES — every workflow that includes one
    # pays for it, so a byte here costs more than a byte in any single prompt.
    # RAISED 9_605 -> 9_810 for the one-line rigour-tier declaration. The tier rule
    # existed in the prompt and the standard and NOTHING checked it was applied, so
    # the operator was the enforcement mechanism and asked four times in three days.
    # Paid for by a raise rather than a cut: the fragment carries no duplicated
    # sentences, so funding it meant deleting substance to hit a number.
    "prompts/decision_log_and_reflection.md": 9_810,
    # 8,106 not 8,057 — the first draft of this budget counted CHARACTERS and
    # this file is full of em-dashes. The test caught it on its first run,
    # which is the cheapest possible demonstration that byte counts are not
    # eyeballable.
    "prompts/rules.md": 7_491,
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
