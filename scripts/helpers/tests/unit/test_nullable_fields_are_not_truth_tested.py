"""A nullable field may never be tested for truth. `is None` or nothing.

WHY THIS EXISTS. PR #82 shipped SEVEN instances of one defect: a NULL emission
folded into a zero by a falsy test. The seventh sat two lines below two filters
that guarded `is not None` correctly, and it was the headline evidence sentence
of the figure whose entire purpose is reporting that exact confusion — the tool
attributed an absence to a broken emitter on a run that was simply never
measured.

THE EXISTING GUARDS WERE STRUCTURALLY BLIND TO IT. They check that
`NULLABLE_FIELDS` matches the EMITTER's own declaration, which is the right
check for the declaration and says nothing about how CONSUMERS read it. A
declaration gate cannot see a usage defect. This one reads the usage.

`not x` and `if x` are indistinguishable from `x == 0` when `x` may be `None`,
and every figure in this directory divides by a population — so one folded NULL
moves a numerator, a median, and a headline claim at once.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

HELPERS = Path(__file__).resolve().parents[2] / "measure"
import sys
sys.path.insert(0, str(HELPERS.parent))
from measure import run_log  # noqa: E402

# NUMERIC nullables only, and the narrowing is the point. For a string field
# `if r["reason"]` means *filter to the ones that have a reason*, which is
# correct and idiomatic — flagging it would make this gate fire on right code,
# and a gate that fires on right code gets deleted rather than fixed. For a
# NUMBER, falsy spans `None` and `0`, and those are the two facts every figure
# in this directory must keep apart: an unmeasured record and a measured zero.
_NUMERIC_NULLABLE = frozenset({
    "peak_anon", "peak_total", "mean_total", "pids_peak", "high_events",
    "oom_kills", "tool_result_bytes", "subagents_spawned",
})
_ALL_NULLABLE = {f for fields in run_log.NULLABLE_FIELDS.values() for f in fields}
_NULLABLE = _NUMERIC_NULLABLE & _ALL_NULLABLE


def _readers() -> list[Path]:
    return sorted(p for p in HELPERS.glob("*.py") if p.name != "__init__.py")


def test_there_are_nullable_fields_and_readers_to_check() -> None:
    """Vacuity guard on both halves — either one empty makes the sweep inert."""
    assert len(_NULLABLE) >= 6, (
        f"only {len(_NULLABLE)} numeric nullable fields resolved — either the "
        f"emitter's declaration moved or the numeric list drifted from it. "
        f"Declared nullable: {sorted(_ALL_NULLABLE)}"
    )
    assert len(_readers()) >= 2, f"only {len(_readers())} readers found under {HELPERS}"


def _truth_tested_nullables(tree: ast.AST) -> list[tuple[int, str]]:
    """Subscripts of a nullable field used in a BOOLEAN position."""
    found: list[tuple[int, str]] = []

    def key_of(node: ast.AST) -> str | None:
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            value = node.slice.value
            if isinstance(value, str) and value in _NULLABLE:
                return value
        return None

    for node in ast.walk(tree):
        # `not r["field"]`
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            if (k := key_of(node.operand)):
                found.append((node.lineno, f'not …["{k}"]'))
        # `if r["field"]` / `... if r["field"]` in a comprehension
        tests: list[ast.AST] = []
        if isinstance(node, (ast.If, ast.IfExp)):
            tests.append(node.test)
        if isinstance(node, ast.comprehension):
            tests.extend(node.ifs)
        for t in tests:
            if (k := key_of(t)):
                found.append((getattr(t, "lineno", 0), f'if …["{k}"]'))
    return found


@pytest.mark.parametrize("reader", _readers(), ids=lambda p: p.name)
def test_no_reader_truth_tests_a_nullable_field(reader: Path) -> None:
    offenders = _truth_tested_nullables(ast.parse(reader.read_text(encoding="utf-8")))
    assert not offenders, (
        f"{reader.name} tests a NULLABLE field for truth, which folds an absent "
        f"measurement into a zero and inflates every figure computed from it. "
        f"Use `is None` / `is not None`, or compare explicitly to 0: {offenders}"
    )


def test_the_detector_fires_on_both_shapes() -> None:
    """Positive control. The seventh instance survived six reviews; a detector
    for it that has never been shown to fire is the same bet again."""
    field = sorted(_NULLABLE)[0]
    for source, why in (
        (f'x = [r for r in fleet if not r["{field}"]]', "not …[nullable]"),
        (f'if r["{field}"]:\n    pass', "if …[nullable]"),
    ):
        assert _truth_tested_nullables(ast.parse(source)), f"detector blind to {why}"

    clean = f'x = [r for r in fleet if r["{field}"] is not None]'
    assert not _truth_tested_nullables(ast.parse(clean)), "false positive on a correct guard"
