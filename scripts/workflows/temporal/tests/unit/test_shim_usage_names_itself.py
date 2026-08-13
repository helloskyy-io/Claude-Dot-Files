"""A shim's usage block must invoke the shim it is in.

WHY THIS EXISTS. Three V2 entry scripts — `research.sh`, `build_minor.sh` and
`plan_sprint.sh` — carried usage blocks reading `./build.sh`, nine wrong lines
copied from the file they were cloned from and never renamed. The usage block is
the documented invocation an operator copy-pastes, so following `research.sh`'s
ran a DIFFERENT workflow with a different model key and turn budget.

IT SURVIVED BECAUSE NOTHING LOOKED. Every shim was individually plausible, the
error is invisible unless you read two files together, and no test compared a
comment to its own filename. This one is three lines of comparison and closes
the class.

TWO DISPATCH-ARGUMENT FAILURES IN ONE DAY came from invoking a workflow from
memory rather than from `--help`; a usage block that names the wrong script is
the same failure with the wrong answer written down where it looks official.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SHIMS = Path(__file__).resolve().parents[1].parent / "scripts"
_INVOCATION = re.compile(r"^#\s+\./([a-z_0-9]+\.sh)", re.M)


def _shims() -> list[Path]:
    return sorted(p for p in SHIMS.glob("*.sh"))


def test_there_are_shims_to_check() -> None:
    """Vacuity guard: a moved directory would make the check below pass on nothing."""
    found = _shims()
    assert len(found) >= 5, f"only {len(found)} shims found under {SHIMS} — the glob is not reading the fleet"


@pytest.mark.parametrize("shim", _shims(), ids=lambda p: p.name)
def test_every_usage_line_invokes_this_shim(shim: Path) -> None:
    named = set(_INVOCATION.findall(shim.read_text(encoding="utf-8")))
    assert named, (
        f"{shim.name} has no `#   ./<script>` usage line. Either it stopped "
        f"documenting its invocation — which is the thing an operator copies — "
        f"or the spelling changed and this gate must follow."
    )
    wrong = named - {shim.name}
    assert not wrong, (
        f"{shim.name}'s usage block tells an operator to run {sorted(wrong)}. "
        f"Copy-pasting it runs a different workflow, with a different model key "
        f"and turn budget, against the arguments of the one they meant to run."
    )
