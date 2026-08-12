"""One definition of "does this registry entry name code that exists?".

TWO REGISTRIES NOW ASK THE SAME QUESTION. `MAY_NOT_OBSERVERS` answers *what
observes this prohibition?* and `DISAPPEARANCE_OBSERVERS` answers *what watches
this snapshot for absence?* Both are free-text values, and both are wide open to
the same attestation failure: writing `act.some_guard` beside an entry costs one
line and reads exactly like coverage.

SHARED RATHER THAN COPIED, for the reason this component has already paid for
once. `plan_activities.normalise_cell` exists because two hand-written
normalisations of one cell drifted, and the row read as ruled to one reader and
blank to the other. A second copy of this resolver would drift the same way, and
the drift would be invisible: the weaker copy would simply stop catching things.

`MODULE_SYMBOL` is a deliberate explicit list rather than a general pattern.
Mechanism prose is written for a human and is full of capitalised words — BOTH,
SAME, ABSENT, CREATES — so a generic "looks like a constant" matcher would flag
sentences instead of symbols. The list is self-correcting rather than silent:
`names_code` requires every non-JUDGEMENT entry to match SOMETHING, so an entry
naming only an unlisted module symbol fails loudly and the fix is to add it here.
"""

from __future__ import annotations

import re

NS_REF = re.compile(r"\b(act|own)\.([a-z_][a-z_0-9]*)\b")

MODULE_SYMBOL = re.compile(r"\b(FORBIDDEN_PATHS|PERMITTED_PATHS|permitted_paths|"
                           r"_rulings_this_run_had_no_right_to)\b")


def names_code(mechanism: str) -> bool:
    """Whether the entry points at anything at all, rather than merely asserting."""
    return bool(NS_REF.search(mechanism) or MODULE_SYMBOL.search(mechanism))


def unresolved(mod, mechanism: str) -> list[str]:
    """Every symbol this entry names that does not exist on the module it claims.

    `act.` and `own.` are resolved through the aliases the workflow module
    actually imports, so an entry cannot name a helper that lives in neither.
    """
    missing: list[str] = []
    for ns, attr in NS_REF.findall(mechanism):
        target = getattr(mod, ns, None)
        if target is None or not hasattr(target, attr):
            missing.append(f"{ns}.{attr}")
    for symbol in sorted(set(MODULE_SYMBOL.findall(mechanism))):
        if not hasattr(mod, symbol):
            missing.append(symbol)
    return missing
