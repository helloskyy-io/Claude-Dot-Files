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

WHAT MAKES A FAILURE HERE CHEAP: the remedy is always the same and always local.
Replace the number with the step's content — *"the dispatch-identity step"*,
*"the Temporal file layout step"* — which is what the surviving citations already
do and what `temporal-integration.md`'s own blockquote instructs.

WHAT THIS DOES NOT COVER, STATED SO IT IS NOT MISTAKEN FOR WIDER COVER: ordinals
that name a *different* document's internal numbering (`cpi-cycle.md` § *Step 1*,
a phase doc's own numbered steps) are legitimate and are not matched. This
predicate is about citations of a MIGRATION PATH.

THERE IS NO EXEMPTION FOR THE RULE'S OWN STATEMENT, DELIBERATELY. An earlier
version of this file carried one, keyed on the phrase "never by ordinal", so a
blockquote stating the rule could quote the anti-pattern it forbids. It rescued
nothing — checked against the tree, not assumed — and an exemption that fires on
no line is a hole with nobody watching it. So the constraint moved to the rule's
phrasing instead: state the rule WITHOUT embedding a matching ordinal, which the
blockquote in `temporal-integration.md` already does. If a future rewording trips
this check, the rewording is what changes.

THE SIBLING HAZARD ONE LEVEL DOWN IS ANSWERED BY A GUARANTEE, NOT BY THIS CHECK.
Requirement numbers (`PMP Phase 9 r7`) are cited by ordinal across component
boundaries constantly, and content-keying them all would be a rewrite of two
components. `temporal-integration.md`'s blockquote instead pins the numbering —
requirements are append-only, a number names a requirement for life. That is a
guarantee about how documents are EDITED and no grep can enforce it; it is
recorded here so the next reader does not mistake this file's silence for
absence of the hazard.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
_DOCS = _REPO / "docs"

# `migration step 3`, `migration path step 3`, `migration path's step 3`.
_ORDINAL_CITATION = re.compile(r"migration\s+(?:path'?s?\s+)?step\s+\d", re.I)

# A line that cites `temporal-integration.md` AND an ordinal step is the same
# citation written the other way round, and the per-file sweep missed exactly
# this shape.
_BY_FILENAME = re.compile(r"temporal-integration\.md")
_BARE_ORDINAL = re.compile(r"\bstep\s+\d", re.I)


def _markdown() -> list[Path]:
    return sorted(_DOCS.rglob("*.md"))


def _offences() -> list[str]:
    out = []
    for path in _markdown():
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if _ORDINAL_CITATION.search(line) or (
                    _BY_FILENAME.search(line) and _BARE_ORDINAL.search(line)):
                out.append(f"{path.relative_to(_REPO)}:{n}")
    return out


def test_the_sweep_examined_something() -> None:
    """A vacuity floor. A glob that found nothing satisfies every assertion below.

    This is the failure the count above records: the original sweep reported clean
    over a range that did not contain the offending site.
    """
    assert len(_markdown()) > 100, (
        f"only {len(_markdown())} markdown files found under {_DOCS} — this "
        f"predicate is reporting clean over a population that cannot be right. "
        f"Check the glob before trusting the result.")


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
