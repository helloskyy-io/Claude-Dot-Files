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

AND THE UNIVERSE OF WORKFLOWS IS DISCOVERED, NOT LISTED. `workflows_declaring`
sweeps `modules/` for any workflow that declares a registry, for exactly the
reason `_functions_with_boundary_calls` sweeps the whole tree rather than the
planning family: the obligation belongs to the MECHANISM. Both consumers
originally hardcoded `[triage, sprint]`, which reopened the failure this whole
apparatus was built to close, one altitude up — a third workflow growing an
authorization table would have been silently exempt, and `plan_activities.py`'s
own docstring already names `plan_tech_stack` as the next one coming. A missing
row fails loudly here; a missing WORKFLOW failed silently there.
"""

from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path

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


# The component root — the directory holding `modules/` — reached from
# `tests/unit/`. `conftest.py` puts this same directory on `sys.path`, which is
# what makes the dotted import below resolve the way the runtime resolves it.
COMPONENT_ROOT = Path(__file__).resolve().parents[2]
MODULES_ROOT = COMPONENT_ROOT / "modules"


def _declares(path: Path, registry: str) -> bool:
    """Whether this file assigns `registry` at MODULE level, by AST.

    Module level specifically: a local variable of the same name inside some
    helper is not a declaration, and a substring grep would count it as one.
    """
    for node in ast.parse(path.read_text()).body:
        targets = (node.targets if isinstance(node, ast.Assign)
                   else [node.target] if isinstance(node, ast.AnnAssign) else [])
        if any(isinstance(t, ast.Name) and t.id == registry for t in targets):
            return True
    return False


def workflows_declaring(registry: str) -> list[tuple[object, str, str]]:
    """Every workflow module in `modules/` that declares `registry`.

    Returns `(module, prompt_filename, test_id)`, sorted, so both consumers
    parametrise over a DISCOVERED universe rather than a hand-written pair.

    ONLY MATCHING MODULES ARE IMPORTED. The sweep decides membership by AST and
    imports nothing else, so adding this discovery does not drag every build-
    and research-family workflow into the unit suite's import graph — a change
    in what gets imported at collection is the kind of coupling `test_test_tree_
    hygiene.py` exists to keep out.

    The prompt filename is DERIVED from the module filename
    (`triage_candidates_workflow.py` -> `triage_candidates.md`) rather than
    passed in beside it. A derived name that is wrong fails at the `read_text()`
    with the path in the message; a hand-written one that is wrong reads a
    DIFFERENT workflow's prompt and checks the wrong table against the right
    registry — green, and asserting about somebody else's file.
    """
    out: list[tuple[object, str, str]] = []
    for path in sorted(MODULES_ROOT.rglob("*_workflow.py")):
        if not _declares(path, registry):
            continue
        dotted = ".".join(path.relative_to(COMPONENT_ROOT).with_suffix("").parts)
        stem = path.name.removesuffix("_workflow.py")
        out.append((importlib.import_module(dotted), f"{stem}.md",
                    stem.replace("_", "-")))
    return out
