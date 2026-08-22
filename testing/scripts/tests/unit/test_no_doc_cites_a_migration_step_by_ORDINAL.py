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
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

from vendored_standards import EXPECTED as _VENDORED_EXPECTED
from vendored_standards import VENDOR_SCRIPT, vendored_paths

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


def _is_research_prose(path: Path) -> bool:
    """Is this file part of a RESEARCH POOL, at either altitude?

    Research papers quote fetched sources, and the Research Standard says a
    span *"may be labelled or presented as a quotation only if its exact
    character sequence was returned by a fetch ... a paraphrase presented as a
    quote is a fabrication."* Editing digits inside such a quote to satisfy this
    gate manufactures exactly that, so the remedy for these files differs.

    KEYED ON THE CLASS, NOT ON ONE PATH, and that is the correction rather than
    a preference. The first version of this partition matched the literal
    `docs/standards/architecture/research/raw` and nothing else — which is the
    SAME "one literal directory instead of the class" mistake this PR had
    already found and fixed one bucket over, in the vendored set that was
    modelled as four directory names. The repo has research pools at TWO
    altitudes (CLAUDE.md; Research Standard § *Two locations, by altitude*):
    `docs/standards/architecture/research/` for findings that change WHAT we
    build, and `docs/development/<component>/research/` for the ~98% that decide
    HOW. The second altitude holds 27 tracked files and every one of them was
    routed into the "reword it locally" bucket.

    `synthesis.md` is included and not just `raw/`: the standard extends the
    same verbatim burden to it, because a synthesis quotes the pool papers it
    cites.
    """
    return "research" in path.relative_to(_REPO).parts


def _offences() -> list[tuple[Path, int]]:
    out: list[tuple[Path, int]] = []
    for path in _markdown():
        text = path.read_text()
        in_carrier = bool(_CARRIER_HEADING.search(text))
        for n, line in enumerate(text.splitlines(), 1):
            if _line_is_offence(line, in_carrier=in_carrier):
                out.append((path, n))
    return out


# THE PROVENANCE OF A FIXTURE IS ITSELF A CHECKABLE CLAIM, AND IT IS CHECKED.
# Both corpora below used to carry their source as a free-text label — a bare
# filename, sometimes without a line. That is unresolvable by anything except a
# human, and `review-pr` pass 9 found the consequence: one `_LEGITIMATE_CORPUS`
# entry sitting under the comment *"Quoted from the live tree, not invented"*
# existed nowhere but this file. So each entry now carries the coordinates that
# let a machine go and look — a git rev (or `None` for the live tree), a
# repo-relative path, and the `carrier` flag — and
# `test_every_FIXTURE_IS_QUOTED_FROM_THE_SOURCE_IT_NAMES` resolves every one of
# them. An invented fixture now fails here rather than surviving to be found by
# the next review pass.
#
# `carrier` is checked too, not just the quote. It records whether the source
# document carries a `# ... migration path` heading, which is what branch 3 keys
# on — a fixture that claims the wrong side of that flag exercises a branch the
# real line never took, and the corpus would certify a predicate the tree does
# not run.

class _Fixture(NamedTuple):
    """One corpus line plus the coordinates that let a machine go and check it.

    `rev` is a git rev, or None meaning the LIVE tree. `carrier` records whether
    the source document carries a `# ... migration path` heading, which is what
    branch 3 keys on.
    """

    rev: str | None
    path: str
    carrier: bool
    line: str


# The eight instances that ACTUALLY happened, quoted from the pre-fix blobs in
# git. Four of them are bare ordinals that only branch 3 can see, which is why
# the carrier flag matters.
_TI = "docs/development/temporal-integration/temporal-integration.md"
_HISTORICAL_CORPUS = [
    _Fixture("bb4a3ae", _TI, True,
     "That is step 2 of the migration path below."),
    _Fixture("bb4a3ae", _TI, True,
     "once step 3 stands Temporal up"),
    _Fixture("bb4a3ae", _TI, True,
     "produced at **step 5**, which is after the deadline this step exists to meet"),
    _Fixture("bb4a3ae", _TI, True,
     "the identity entry is authored here, at step 2, and the rest of the "
     "addendum stays at step 5.**"),
    _Fixture("bb4a3ae", _TI, True,
     "and the identity half of it is step 2 of the migration path above."),
    _Fixture("2af48df", "docs/development/temporal-integration/phase6_the_rest_of_the_fleet.md", False,
     "[`temporal-integration.md`](temporal-integration.md)'s migration path, "
     "step 3: the Temporal file layout, and why `children/` dissolves."),
    _Fixture("e844280^", "docs/standards/architecture/research/candidates.md", False,
     "migration step 2 names §A3 as the artifact"),
    _Fixture("e844280^", "docs/standards/architecture/research/candidates.md", False,
     "migration step 2, which already flags the mismatch in-line"),
]

# Lines that legitimately carry an ordinal and MUST stay green: another
# document's own numbered steps. `rev=None` means the LIVE tree.
#
# The third entry replaces one that was invented. It is deliberately keyed on
# `Step 3` — the same ordinal as the phase6 offence above — so the pair
# discriminates on the citation's SUBJECT rather than on which digit it uses.
_LEGITIMATE_CORPUS = [
    _Fixture(None, "docs/standards/exit-protocol.md", False,
     "**The parent's run-identity check** — [Phase 3 § step 3]"
     "(../development/memory-management-framework/phase3_typed_exit_record.md)."),
    _Fixture(None, "docs/development/memory-management-framework/phase6_read_what_it_writes.md", False,
     "[Phase 4](phase4_fleet_migration.md) step 2 may move "
     "`modules/assistant/convergence.py` into `review_pr/`."),
    _Fixture(None, "docs/guide/cpi-cycle.md", False,
     "### Step 3 — Read the report together"),
]


@lru_cache(maxsize=None)
def _source_text(rev: str | None, path: str) -> str:
    """The fixture's source, read from git history or from the live tree.

    `check=True`: a fixture whose source cannot be read is a fixture whose
    provenance is unverified, and that is the whole failure this corpus exists
    to make impossible. It must raise rather than resolve to an empty string,
    which would make every `in` test below fail with a misleading message.
    """
    if rev is None:
        return (_REPO / path).read_text(encoding="utf-8")
    return subprocess.run(
        ["git", "-C", str(_REPO), "show", f"{rev}:{path}"],
        capture_output=True, text=True, check=True).stdout


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
    missed = [(f"{f.rev}:{f.path}", f.line) for f in _HISTORICAL_CORPUS
              if not _line_is_offence(f.line, in_carrier=f.carrier)]
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
    false_positives = [f.path for f in _LEGITIMATE_CORPUS
                       if _line_is_offence(f.line, in_carrier=f.carrier)]
    assert not false_positives, (
        f"the predicate fires on another document's own numbered steps: "
        f"{false_positives}. Those ordinals are legitimate — they name internal "
        f"numbering the reader is meant to follow, not a citation of the "
        f"Temporal migration path.")


def test_every_FIXTURE_IS_QUOTED_FROM_THE_SOURCE_IT_NAMES() -> None:
    """The corpora's own provenance claim, enforced instead of asserted in prose.

    `review-pr` pass 9 found a `_LEGITIMATE_CORPUS` entry that existed nowhere
    but this file, sitting under the comment *"Quoted from the live tree, not
    invented"* — in the one module whose entire stated root cause is *"the
    mutation corpus was author-invented while git held the real one for free"*.
    Two `git grep`s found it. Nothing in the suite would have.

    This is the class-check rather than the instance fix: it resolves EVERY
    fixture in BOTH corpora against the source it names, so the next invented
    one goes red here instead of surviving to the next review pass. Sweeping the
    two corpora when this was written found 8 of 8 historical entries genuine
    and 2 of 3 legitimate entries genuine — the predicate below would have
    caught the third on the commit that introduced it.

    The `carrier` flag is checked against the same source, because it is the
    second claim each fixture makes: it decides whether branch 3 is exercised,
    so a wrong flag replays the line down a path the real document never took.
    """
    wrong_quote: list[str] = []
    wrong_carrier: list[str] = []
    for fixture in _HISTORICAL_CORPUS + _LEGITIMATE_CORPUS:
        where = (f"{fixture.rev}:{fixture.path}" if fixture.rev
                 else f"(live tree) {fixture.path}")
        text = _source_text(fixture.rev, fixture.path)

        # Matched against PHYSICAL LINES, not the file blob. `_line_is_offence`
        # is fed one line at a time by `_offences`, so a fixture that only
        # exists as a substring spanning a line break would be replayed through
        # the predicate in a form the scan can never actually hand it.
        if not any(fixture.line in physical for physical in text.splitlines()):
            wrong_quote.append(f"{where} :: {fixture.line[:60]!r}")
            continue
        actual = bool(_CARRIER_HEADING.search(text))
        if actual != fixture.carrier:
            wrong_carrier.append(
                f"{where} claims carrier={fixture.carrier}, is {actual}")

    assert not wrong_quote, (
        f"{len(wrong_quote)} fixture(s) are not present as a SINGLE LINE of "
        f"the source they name: "
        + "; ".join(wrong_quote) + ". A fixture that quotes nothing real "
        "certifies nothing real. Quote an actual line — git holds every "
        "pre-fix blob, and the live tree holds the legitimate ones — or delete "
        "the entry. Do NOT resolve this by relaxing the check.")

    assert not wrong_carrier, (
        "a fixture's carrier flag disagrees with its source document: "
        + "; ".join(wrong_carrier) + ". The flag decides whether branch 3 is "
        "exercised, so a wrong one replays the line down a branch the real "
        "document never took.")


def test_THE_VENDORED_SET_the_remedy_names_is_READ_OFF_the_script() -> None:
    """The remedy below routes vendored files upstream; this holds that set.

    The failure message partitions offences into files this repo may fix in
    place and files it may not. That partition is only as good as the set, and
    a hand-kept list would be exactly the stale declaration this repo's gates
    exist to catch — so `vendored_standards.vendored_paths` derives it from
    `vendor-standards.sh`, and this is the vacuity guard FOR THIS GATE: a parse
    that silently stopped matching would return an empty set, and the remedy
    would go back to prescribing a forbidden local edit on all six mirrors.

    IT IS SIX FILES, NOT FOUR DIRECTORIES, and the distinction is load-bearing
    here. The four `README.md` applicability notes and `temporal/claude-dot-
    files-addendum.md` sit in those same directories and ARE local and editable.
    `review-pr` pass 9 wrote this finding as *"four vendored MIRROR standard
    sets"*. Telling a contributor their local fix must go upstream stalls it
    against a source that has no counterpart for it.
    """
    vendored = vendored_paths()
    assert sorted(p.name for p in vendored) == sorted(_VENDORED_EXPECTED), (
        f"the vendored set derived from {VENDOR_SCRIPT.name} is "
        f"{sorted(p.name for p in vendored)}. Either the set genuinely changed "
        f"— update `vendored_standards.EXPECTED` and the remedy paragraph in "
        f"this module's docstring — or the parse broke, in which case the "
        f"remedy below is silently telling contributors to edit mirrors they "
        f"may not edit.")

    missing = [p for p in vendored if not p.is_file()]
    assert not missing, (
        f"the script declares vendored files that are not in the tree: "
        f"{[str(p.relative_to(_REPO)) for p in missing]}. The remedy partition "
        f"below matches on these paths, so a wrong path means a vendored "
        f"offence is routed as a local fix.")


def test_THE_RESEARCH_BUCKET_reaches_BOTH_ALTITUDES() -> None:
    """The bucket predicate, held against the tree rather than against itself.

    `_is_research_prose` replaced a literal `docs/standards/architecture/
    research/raw` match that missed the component-altitude pools entirely. This
    asserts both altitudes are actually reached and non-empty, so the predicate
    cannot silently narrow back to one of them — which is the regression that
    produced the finding, one bucket over, on this same PR.
    """
    pools = [p for p in _markdown() if _is_research_prose(p)]
    architecture = [p for p in pools
                    if p.is_relative_to(_REPO / "docs/standards/architecture/research")]
    component = [p for p in pools
                 if p.is_relative_to(_REPO / "docs/development")]

    assert architecture, (
        "no architecture-altitude research file is in the research bucket — "
        "`docs/standards/architecture/research/` holds the pool whose papers "
        "quote fetched sources, and its offences would now be routed as local "
        "rewords.")
    assert component, (
        "no component-altitude research file is in the research bucket. The "
        "repo has research pools at TWO altitudes and this predicate has "
        "narrowed back to one, which is exactly the finding it was written to "
        "close: `docs/development/<component>/research/` papers carry the same "
        "verbatim-quote burden.")

    # The bucket must not swallow the whole tree; it is a carve-out, not a mode.
    assert len(pools) < len(_markdown()) // 2, (
        f"{len(pools)} of {len(_markdown())} tracked markdown files landed in "
        f"the research bucket. `_is_research_prose` matches any path with a "
        f"'research' component; if that is now most of the tree, the remedy "
        f"text is telling nearly every contributor not to edit their own prose.")


def test_no_document_cites_a_MIGRATION_PATH_STEP_BY_NUMBER() -> None:
    """The requirement. A number points at a different step after the next insert.

    THE REMEDY IS NOT THE SAME EVERYWHERE, WHICH IS WHY THIS MESSAGE PARTITIONS.
    The scan is `git ls-files -- '*.md'` — the whole tracked tree — and a third
    of it is prose this repo is NOT free to reword. The single remedy this
    message used to give (*"cite the step by content"*) is forbidden on two of
    those groups, and following it there breaks a different gate:

      * A VENDORED MIRROR — the six files `vendor-standards.sh` copies. `CLAUDE.md`:
        *"Vendored standards are verbatim copies and MUST NOT be edited here."*
        Rewording one is local drift and `vendor-standards.sh --check` fails on
        it; reverting the re-vendor instead leaves the standard stale. Both
        gates then block each other with the only exit in another repository.
        The fix goes UPSTREAM, then re-vendor. NOT by excluding the trees from
        this scan — that would drop 58 files (6 vendored, 25 architecture-
        altitude research, 27 component-altitude research) from a check whose
        own history is about a predicate certifying the subset already fixed.
      * A RESEARCH POOL PAPER, at EITHER altitude — `docs/standards/architecture/
        research/` and `docs/development/<component>/research/` — whose papers
        quote fetched sources. The Research Standard: *"A span may be labelled
        or presented as a quotation only if its exact character sequence was
        returned by a fetch ... a paraphrase presented as a quote is a
        fabrication."* Editing the digits inside the quote to satisfy this gate
        manufactures exactly that. Fix the SURROUNDING prose instead — the quote
        stays, and the citation around it names the step by content.

    Not live when this was written: the three tracked lines carrying *"migration
    path"* under `docs/standards/` carry no ordinal, so the population is green.
    A re-vendor is a routine scripted operation and a new research paper is a
    weekly one, so the message says this now rather than after the deadlock.
    """
    offences = _offences()
    if not offences:
        return

    vendored = vendored_paths()
    mirror, quoted, local = [], [], []
    for p, n in offences:
        where = f"{p.relative_to(_REPO)}:{n}"
        if p.resolve() in vendored:
            mirror.append(where)
        elif _is_research_prose(p):
            quoted.append(where)
        else:
            local.append(where)

    parts = [
        "these lines cite a migration-path step by ordinal. Inserting a step "
        "renumbers everything after it, so the citation keeps resolving and "
        "starts naming the WRONG step — it never fails loudly."]
    if local:
        parts.append(
            "FIX IN PLACE — cite the step by CONTENT: 'the dispatch-identity "
            "step', 'the Temporal file layout step'. The rule and its reason "
            "are in the blockquote under the migration path's own heading in "
            "docs/development/temporal-integration/temporal-integration.md. IF "
            "THE OFFENDING LINE IS THE RULE'S OWN STATEMENT, reword the rule "
            "rather than exempting it — see this module's docstring for why "
            "there is no exemption: " + ", ".join(local))
    if mirror:
        parts.append(
            "VENDORED MIRROR — DO NOT reword locally and DO NOT exclude it "
            "from the scan. `vendor-standards.sh --check` fails on local "
            "drift. Fix it upstream in MDC-Master-Planning, then re-vendor "
            "with scripts/helpers/vendor-standards.sh: " + ", ".join(mirror))
    if quoted:
        parts.append(
            "RESEARCH POOL PAPER (either altitude) — if the ordinal sits "
            "inside a VERBATIM quotation, do not edit the quote; the Research "
            "Standard makes a reworded quote a fabrication. Cite the step by "
            "content in the surrounding prose and leave the quoted characters "
            "alone. If it is the paper's own prose rather than a quote, fix it "
            "in place: "
            + ", ".join(quoted))

    raise AssertionError("\n\n".join(parts))
