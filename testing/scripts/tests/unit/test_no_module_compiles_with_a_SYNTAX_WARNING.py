"""Every tracked Python module compiles clean — no `SyntaxWarning`, anywhere.

THE INSTANCE, AND WHY THE INSTANCE IS NOT THE POINT.
`scripts/workflows/temporal/tests/unit/test_plan_refine.py:459` held a docstring
quoting the regex `[^/]+\\.md$` without an `r` prefix, so `\\.` was an invalid
escape sequence. It printed a `SyntaxWarning` on every collection of the unit
tier, and under `python -W error::SyntaxWarning` it is already a hard
`SyntaxError` — at which point the module stops importing and the whole tier
fails to COLLECT rather than failing one test. Invalid escapes are on a published
path from `DeprecationWarning` to `SyntaxWarning` to `SyntaxError`; the promotion
is scheduled, not hypothetical.

It was flagged by hand on THREE separate passes over two PRs — the draft, its
refine, and `review-pr` — each time as an aside in a reflection, each time with no
home, and each time it survived. That is the signature of a finding that needs a
gate rather than another sighting: whoever happens to read the collection banner
is not a control.

THIS KEYS ON THE CLASS, NOT THE CHARACTER. The population is every `*.py` tracked
by git, and the predicate is "compiles without warning" rather than "has no `\\.`
in a docstring". So it also catches the neighbours the one-character fix would
have left standing:

  * any other invalid escape, in a docstring, a comment or a literal
  * `SyntaxWarning: "is" with a literal` — the identity-vs-equality confusion,
    which silently works until the interpreter stops interning the value
  * `assert (cond, "msg")` — the always-true tuple assert, the single most
    expensive vacuous-test shape there is, and one this repo's guards are full of
    the honest form of

WHAT THIS DOES NOT LOOK AT. Runtime warnings of any kind — this compiles, it never
imports or executes, so a module with an expensive or side-effecting import is not
run by it. Nor does it read files git does not track: an untracked scratch module
is invisible here exactly as it is to every other tree-derived gate in this repo.
"""

from __future__ import annotations

import subprocess
import warnings
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]


def _tracked_modules() -> list[Path]:
    """DERIVED FROM GIT, so a file added tomorrow is covered on the day it lands."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "*.py"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    return [REPO / p for p in out]


def _warnings_from_compiling(path: Path) -> list[str]:
    """Compile in isolation and collect what the COMPILER said about it.

    `compile()` and not `py_compile`/`import`: nothing here executes module-level
    code, so a module whose import is slow, networked or side-effecting is still
    covered. `simplefilter("always")` defeats the once-per-location dedup, which
    would otherwise hide a second occurrence in the same file.
    """
    source = path.read_text(encoding="utf-8", errors="strict")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        compile(source, str(path), "exec")
    return [f"{w.category.__name__}: {w.message}" for w in caught
            if issubclass(w.category, SyntaxWarning)]


def test_the_derivation_found_the_tree() -> None:
    """VACUITY FLOOR. A gate that scans nothing passes silently and forever."""
    found = _tracked_modules()
    assert len(found) > 100, (
        f"only {len(found)} tracked Python files found under {REPO} — the "
        f"`git ls-files` derivation is wrong, and every assertion below is "
        f"passing over an empty set."
    )


@pytest.mark.parametrize("path", _tracked_modules(),
                         ids=lambda p: str(p.relative_to(REPO)))
def test_a_tracked_module_compiles_without_a_syntax_warning(path: Path) -> None:
    """THE GATE."""
    issues = _warnings_from_compiling(path)
    assert not issues, (
        f"{path.relative_to(REPO)} compiles with a SyntaxWarning:\n\n  "
        + "\n  ".join(issues)
        + "\n\nThis is not cosmetic. `python -W error::SyntaxWarning` already "
          "treats it as a SyntaxError, and CPython is promoting these warnings "
          "to hard errors — at which point this module stops importing and its "
          "whole tier fails to COLLECT. For an invalid escape in prose that "
          "quotes a regex, prefix the string with `r` rather than escaping the "
          "backslash: the reader must see the regex as it appears in the code "
          "it describes."
    )


def test_the_gate_can_actually_FAIL() -> None:
    """A control whose failing path has never run is not a control.

    Once the tree is clean the parametrised gate above can only ever exercise its
    passing case, which is precisely when a broken predicate stops being visible.
    Each sample is a real member of the class this exists to catch, compiled from
    a synthetic string so nothing on disk is touched.
    """
    samples = {
        "invalid-escape": '"""a grant shaped [^/]+\\.md$ reaches no subdirectory"""',
        "is-with-a-literal": "def f(x):\n    return x is 1\n",
        "assert-on-a-tuple": 'def f():\n    assert (1 == 1, "never fires")\n',
    }
    for label, source in samples.items():
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            compile(source, f"<{label}>", "exec")
        assert any(issubclass(w.category, SyntaxWarning) for w in caught), (
            f"the {label} sample no longer raises a SyntaxWarning on this "
            f"interpreter ({source!r}). Either CPython changed what it warns "
            f"about — in which case replace the sample — or the collection above "
            f"is inert and the gate is asserting nothing."
        )

    clean = '"""a grant shaped r-quoted [^/]+ is fine"""\nx = 1 == 1\n'
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        compile(clean, "<clean>", "exec")
    assert not [w for w in caught if issubclass(w.category, SyntaxWarning)], (
        "the control's own clean sample warns, so the predicate flags innocent "
        "code and the gate above would red on a healthy tree."
    )
