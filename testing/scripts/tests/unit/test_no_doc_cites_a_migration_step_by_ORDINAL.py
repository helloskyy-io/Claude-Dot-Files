"""A citation keyed on an ordinal resolves to the WRONG step instead of failing.

`temporal-integration.md` carries a numbered migration path. Inserting a step
renumbers every step after it, and a citation written as *"step 3"* then points at
a different, real step — so it still resolves, it just resolves to the wrong thing.
Nothing goes red. The next reader follows the number to a step that is not the one
the author meant, and a required input to their work sits one line down with
nothing pointing at it.

THE COUNT ON ONE PR, WHICH IS WHY THIS IS A CHECK AND NOT A CONVENTION. PR #123
inserted dispatch-identity as step 2. `phase6_the_rest_of_the_fleet.md:46` cited
"step 3" for the file-layout ruling, which the insertion moved to 4. The sweep that
closed it found `temporal-integration.md` citing its own path by ordinal from six
more places. **Then the class reopened INSIDE the same PR**: a `candidates.md` row
authored after the sweep cited "migration step 2" twice, because the sweep's
verification grep had been scoped to one FILE. Eight instances, three correction
passes, one class.

THAT LAST FAILURE IS THE REASON THIS PREDICATE IS REPO-WIDE AND NOT PER-FILE. A
sweep verified against the file it was sweeping cannot see the site authored
minutes later somewhere else. The check has to key on the class — any document,
any ordinal — or it certifies exactly the subset that was already fixed.

THE FIRST VERSION OF THIS FILE DID EXACTLY THAT, AND `review-pr` PASS 8 MEASURED
IT: of the eight instances quoted above as this check's own justification, the
original predicate caught **two** — and both of those had already been fixed by
other means. All six inside `temporal-integration.md` were invisible, because the
predicate required the word "migration" IMMEDIATELY BEFORE "step", and **a
document citing its own migration path writes neither its own filename nor, four
times out of six, the word "migration" at all** — it writes *"begins once step 3
stands Temporal up"*. The root cause was not the regex. It was that the mutation
corpus was author-invented while git held the real one for free: the eight
historical lines were never replayed against the predicate. They are replayed
now, as fixtures, by `test_the_PREDICATE_catches_every_instance_that_HAPPENED`.
That test is what stops this predicate being narrowed back.

THE THREE BRANCHES, AND WHAT EACH ONE IS FOR:

  1. The line names the migration path AND carries an ordinal, in EITHER word
     order — *"migration path, step 3"* and *"step 2 of the migration path"* are
     the same citation. Also `migration step N` / `migration's step N`, which name
     it without the word "path".
  2. The line names `temporal-integration.md` AND carries an ordinal. This is an
     outside document citing the carrier by filename, which branch 3 cannot see.
  3. THE CARRIER DOCUMENT ITSELF. Any file with a `# ... migration path` heading
     carries a numbered path, and inside such a file a bare `step N` is a
     self-citation. This branch is keyed on the HEADING, not on a filename, so a
     second migration path written anywhere in the repo is covered on arrival
     rather than after the next incident. It is the branch that covers four of
     the six misses, and the one the original file had no equivalent of.

WHAT MAKES A FAILURE HERE CHEAP: the remedy is always the same and always local.
Replace the number with the step's content — *"the dispatch-identity step"*,
*"the Temporal file layout step"* — which is what the surviving citations already
do and what `temporal-integration.md`'s own blockquote instructs.

WHAT THIS DOES NOT COVER, STATED SO IT IS NOT MISTAKEN FOR WIDER COVER: ordinals
that name a *different* document's internal numbering (`cpi-cycle.md` § *Step 1*,
a phase doc's own numbered steps) are legitimate and are not matched. Branch 1
requires the phrase *"migration path"* rather than the bare word *"migration"*
for exactly this reason — measured across all tracked markdown, eleven lines
carry "migration" and an ordinal legitimately (the Memory-Management-Framework
phase docs, `exit-protocol.md`'s *"Phase 3 § step 3"*), and **not one of them
contains "migration path"**. A citation phrased *"the Temporal migration's
step 3"* without the word "path" is caught; one phrased with neither "path" nor
adjacency is not, and that is a known and deliberate edge, not an oversight.

THERE IS NO EXEMPTION FOR THE RULE'S OWN STATEMENT, DELIBERATELY. An earlier
version of this file carried one, keyed on the phrase "never by ordinal", so a
blockquote stating the rule could quote the anti-pattern it forbids. It rescued
nothing — checked against the tree, not assumed — and an exemption that fires on
no line is a hole with nobody watching it. So the constraint moved to the rule's
phrasing instead: state the rule WITHOUT embedding a matching ordinal. **The
first version of this docstring claimed the blockquote in `temporal-integration.md`
"already does" that. It did not** — it ended *"Cite the dispatch-identity step,
not step 2"*, embedding the ordinal it forbids, and the predicate was too narrow
to notice. Branch 3 sees it, and the blockquote was reworded rather than
exempted. If a future rewording trips this check, the rewording is what changes.

THE SIBLING HAZARD ONE LEVEL DOWN IS ANSWERED BY A GUARANTEE, NOT BY THIS CHECK.
Requirement numbers (`PMP Phase 9 r7`) are cited by ordinal across component
boundaries constantly, and content-keying them all would be a rewrite of two
components. `temporal-integration.md`'s blockquote instead pins the numbering —
requirements are append-only, a number names a requirement for life. That is a
guarantee about how documents are EDITED and no grep can enforce it; it is
recorded here so the next reader does not mistake this file's silence for
absence of the hazard.

THE HAZARD ONE LEVEL *UP* IS ALREADY RATIFIED, AND DELIBERATELY NOT CHECKED HERE.
`docs/standards/documentation/documentation_standard.md` § *Phase numbering* rule
4 (*"A phase is CITED BY NAME, never by number — everywhere a human reads"*,
binding 2026-08-20) is this same class applied to phase numbers, and it is the
upstream rule this check is a special case of. **It is not enforced here on
purpose:** that rule states its own migration is *"rolling, not a sweep"* across
31 components and roughly 8,000 phase references, of which the prose half cannot
be mechanically converted. A repo-wide phase-ordinal predicate added today would
go red on thirty components that are correctly mid-migration, so the merge gate
would be asserting a rule the corpus is not yet expected to satisfy. Scope here
stays on the migration path, whose corpus is small and fully converted.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]

# `migration step 2`, `migration's step 2`, `migration path step 2`.
_ADJACENT = re.compile(r"migration'?s?\s+(?:path'?s?\s+)?step\s+\d", re.I)

# The path named anywhere on the line, in either word order, plus an ordinal.
_MIGRATION_PATH = re.compile(r"migration\s+path", re.I)
_ORDINAL = re.compile(r"\bstep\s+\d", re.I)

# An outside document citing the carrier by filename. Branch 3 cannot see this
# one, because the carrier never writes its own name.
_BY_FILENAME = re.compile(r"temporal-integration\.md")

# A document that CARRIES a numbered migration path. Keyed on the heading rather
# than on a filename, so a second one anywhere in the repo is covered on arrival.
_CARRIER_HEADING = re.compile(r"^#+.*migration\s+path", re.I | re.M)


def _markdown() -> list[Path]:
    """Every TRACKED markdown file, enumerated by git rather than by walking.

    `rglob` is the obvious implementation and it is wrong here. Dispatch worktrees
    live at `.claude/worktrees/<name>/` — gitignored, but each one a complete
    nested checkout of this same repository. Measured from the main checkout:
    `rglob("*.md")` returns **31,039** files against **268** tracked, and the
    extra 30,770 are stale copies of these very documents belonging to other
    dispatches. Several still carry the pre-fix ordinals this check forbids, so
    a filesystem walk would fail the merge gate on work that is not in the tree,
    non-deterministically, depending on which dispatches happened to be running.

    `check=True` on purpose: if git cannot enumerate the tree, this check has no
    population and must say so rather than report clean over nothing.
    """
    listed = subprocess.run(
        ["git", "-C", str(_REPO), "ls-files", "-z", "--", "*.md"],
        capture_output=True, text=True, check=True)
    return sorted(_REPO / p for p in listed.stdout.split("\0") if p)


def _line_is_offence(line: str, *, in_carrier: bool) -> bool:
    """The predicate, factored out so the historical corpus can be replayed on it."""
    if _ADJACENT.search(line):
        return True
    if _MIGRATION_PATH.search(line) and _ORDINAL.search(line):
        return True
    if _BY_FILENAME.search(line) and _ORDINAL.search(line):
        return True
    return in_carrier and bool(_ORDINAL.search(line))


def _offences() -> list[str]:
    out = []
    for path in _markdown():
        text = path.read_text()
        in_carrier = bool(_CARRIER_HEADING.search(text))
        for n, line in enumerate(text.splitlines(), 1):
            if _line_is_offence(line, in_carrier=in_carrier):
                out.append(f"{path.relative_to(_REPO)}:{n}")
    return out


# The eight instances that ACTUALLY happened, quoted from the pre-fix blobs in
# git rather than invented. `carrier` records whether the line lived inside the
# document that carries the migration path, because four of them are bare
# ordinals that only branch 3 can see.
_HISTORICAL_CORPUS = [
    ("temporal-integration.md@bb4a3ae:11", True,
     "That is step 2 of the migration path below."),
    ("temporal-integration.md@bb4a3ae:54", True,
     "This comes before anything is wrapped — before Stage B, which begins "
     "once step 3 stands Temporal up — because under Temporal's default "
     "retry policy"),
    ("temporal-integration.md@bb4a3ae:54", True,
     "And the addendum is otherwise produced at **step 5**, which is after the "
     "deadline this step exists to meet"),
    ("temporal-integration.md@bb4a3ae:54", True,
     "so the identity entry is authored here, at step 2, and the rest of the "
     "addendum stays at step 5.**"),
    ("temporal-integration.md@bb4a3ae:77", True,
     "and the identity half of it is step 2 of the migration path above."),
    ("phase6_the_rest_of_the_fleet.md@2af48df:46", False,
     "- [`temporal-integration.md`](temporal-integration.md)'s migration path, "
     "step 3: the Temporal file layout, and why `children/` dissolves."),
    ("candidates.md@e844280^", False,
     "[`temporal-integration.md`](../../../development/temporal-integration/"
     "temporal-integration.md) migration step 2 names §A3 as the artifact"),
    ("candidates.md@e844280^", False,
     "**Evidence:** `claude-dot-files-addendum.md:33`; `temporal-integration.md` "
     "migration step 2, which already flags the mismatch in-line"),
]

# Lines that legitimately carry an ordinal and MUST stay green: another
# document's own numbered steps. Quoted from the live tree, not invented.
_LEGITIMATE_CORPUS = [
    ("exit-protocol.md:74", False,
     "**The parent's run-identity check** — [Phase 3 § step 3]"
     "(../development/memory-management-framework/phase3_typed_exit_record.md)."),
    ("phase6_read_what_it_writes.md:301", False,
     "[Phase 4](phase4_fleet_migration.md) step 2 may move "
     "`modules/assistant/convergence.py` into `review_pr/`."),
    ("cpi-cycle.md-shape", False,
     "Run the review, then follow step 1 of the cycle below."),
]


def test_the_scan_reaches_THE_WHOLE_TRACKED_TREE() -> None:
    """A vacuity floor AND a scope floor. The original check had only the first.

    The original asserted `> 100` files while scanning `docs/` alone (148). Once
    the scan is widened to the tracked tree (268), that floor is cleared by BOTH
    scopes — so it could no longer detect a silent regression back to docs-only,
    which is the narrowing this file's own history is about. The structural
    assertions below are the ones that bite; the count is only the vacuity net.
    """
    found = _markdown()
    assert len(found) > 200, (
        f"only {len(found)} tracked markdown files found under {_REPO} — this "
        f"predicate is reporting clean over a population that cannot be right. "
        f"Check the enumeration before trusting the result.")

    outside_docs = [p for p in found if not p.is_relative_to(_REPO / "docs")]
    assert outside_docs, (
        "the scan returned nothing outside docs/ — it has regressed to the "
        "docs-only scope the original version had, and the 120 tracked markdown "
        "files elsewhere in the repo are unchecked again.")

    # The nested-worktree hazard, asserted rather than trusted: a filesystem walk
    # from the main checkout pulls in ~30k stale copies out of `.claude/`.
    dotted = [p for p in found if any(part.startswith(".") for part in
                                      p.relative_to(_REPO).parts)]
    assert not dotted, (
        f"the enumeration returned paths inside dot-directories: "
        f"{[str(p.relative_to(_REPO)) for p in dotted[:5]]}. Tracked markdown "
        f"lives in the working tree; this means the scan is walking the "
        f"filesystem rather than asking git, and it will pick up other "
        f"dispatches' worktrees under .claude/.")


def test_the_PREDICATE_catches_every_instance_that_HAPPENED() -> None:
    """The regression corpus. `review-pr` pass 8 measured the original at 2 of 8.

    These lines are quoted from the pre-fix blobs in git — the real corpus, which
    was available for free and never replayed. Narrowing the predicate back to
    anything that misses one of them turns this red.
    """
    missed = [(where, line) for where, carrier, line in _HISTORICAL_CORPUS
              if not _line_is_offence(line, in_carrier=carrier)]
    assert not missed, (
        f"the predicate misses {len(missed)} of {len(_HISTORICAL_CORPUS)} "
        f"instances that actually happened: {[w for w, _ in missed]}. A guard "
        f"that certifies a class it does not cover is worse than no guard. The "
        f"six inside temporal-integration.md are the ones a narrow predicate "
        f"loses first — the carrier document writes neither its own filename "
        f"nor, usually, the word 'migration'.")


def test_the_predicate_leaves_ANOTHER_DOCUMENTS_OWN_STEPS_alone() -> None:
    """The other half of discrimination. A guard that fires on everything is noise.

    Eleven lines in the tracked tree carry 'migration' and an ordinal
    legitimately. None contains the phrase 'migration path', which is why
    branch 1 keys on the phrase and not on the word.
    """
    false_positives = [where for where, carrier, line in _LEGITIMATE_CORPUS
                       if _line_is_offence(line, in_carrier=carrier)]
    assert not false_positives, (
        f"the predicate fires on another document's own numbered steps: "
        f"{false_positives}. Those ordinals are legitimate — they name internal "
        f"numbering the reader is meant to follow, not a citation of the "
        f"Temporal migration path.")


def test_no_document_cites_a_MIGRATION_PATH_STEP_BY_NUMBER() -> None:
    """The requirement. A number points at a different step after the next insert."""
    offences = _offences()
    assert not offences, (
        f"these lines cite a migration-path step by ordinal: "
        f"{', '.join(offences)}. Inserting a step renumbers everything after it, "
        f"so the citation keeps resolving and starts naming the WRONG step — it "
        f"never fails loudly. Cite the step by CONTENT instead: 'the "
        f"dispatch-identity step', 'the Temporal file layout step'. The rule and "
        f"its reason are stated in the blockquote under the migration path's own "
        f"heading in docs/development/temporal-integration/temporal-integration.md.\n"
        f"IF THE OFFENDING LINE IS THE RULE'S OWN STATEMENT, reword the rule "
        f"rather than exempting it — see this file's docstring for why there is "
        f"no exemption.")
