"""A handler that names SOME of a call's failures and not the decode one.

WHY THIS FILE EXISTS, AS THE MEASUREMENT RATHER THAN AS A PRINCIPLE.
`Path.read_text(encoding="utf-8")` fails two ways that share no base class: the
file cannot be opened, which is an `OSError`, and its bytes cannot be decoded,
which is a `UnicodeDecodeError` — a `ValueError`. `except OSError` around one of
these calls therefore catches the failure everybody thinks of and lets the other
through, and it does so while LOOKING handled, which is why it survives review.

This package acquired the shape four times, in four files, and each was found
separately:

  * `installer_targets` — one non-UTF-8 byte in `install.sh` escaped
    `_config_digest_value`'s handler and out of `open_run_bag`, making every
    dispatch on the machine impossible for a condition whose design says it is
    one unknown fact and never a reason a run may not proceed.
  * `compare_run_config._read_digest` — caught `OSError` around `read_tag_file`,
    which also raises `BagError` and `ValueError`. Both left `main()` unhandled,
    and CPython exits **1** on an unhandled exception: the code that tool's own
    contract assigns to DIFFERENT. A corrupt bag was indistinguishable from a
    real divergence.
  * `load_journal_config` — a non-UTF-8 `config.yaml` escaped a docstring whose
    stated rule is that *every call on the resolution path raises
    `JournalRootError` or nothing*, so the operator got a traceback instead of
    the named diagnostic.
  * `validate.validate_bag` — three tag-file reads inside one `except OSError`,
    in a function whose whole contract is that it RETURNS a report rather than
    raising. Found by this sweep, in the file nobody had reason to open.

The first three were each fixed as they were reported, one file at a time, over
two review passes. Fixing instances did not converge — the fourth was still
there, and nothing would have gone red. What converges is a check that keys on
the CLASS, so the fifth site fails at the moment it is written.

⚠ THE PREDICATE IS "PARTIALLY HANDLED", NOT "HANDLED", AND THAT IS THE WHOLE
DESIGN. A `read_text` with NO enclosing `try` is out of scope and passes: it
propagates, its caller owns the contract, and there is nothing misleading about
it. The defect is specifically a handler that exists and is incomplete — it tells
the next reader the failure mode was considered. Three sites in this package have
no enclosing `try` (`bag.py` twice, `citations.py` once) and are correctly silent
here.

⚠ WHAT THIS DOES NOT COVER, because a sweep is only as good as its predicate:

  * IT SWEEPS `modules/journal/*.py` AND NOTHING ELSE, the same scope as the
    regex-anchor, containment and tag-line sweeps. The scope is named in the
    failure message so a reader hitting it learns the boundary rather than
    assuming there is none.
  * IT SEES `…read_text(encoding=…)` AS AN ATTRIBUTE CALL. `open(p).read()`,
    `json.loads(p.read_bytes())` and a decode performed through a helper are
    invisible. The class is broader than the predicate; this is the member of it
    that has actually shipped four times.
  * IT IS A CHECK ON THE HANDLER'S CLASS LIST, NOT ON WHAT THE HANDLER DOES. A
    clause that names `UnicodeDecodeError` and then swallows it silently passes
    here and is a different defect, caught by the tests that drive those paths.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
PACKAGE = REPO_ROOT / "scripts" / "workflows" / "temporal" / "modules" / "journal"

#: Naming any of these in an enclosing handler discharges the site.
#: `UnicodeDecodeError` is the precise class; `ValueError` is its base and is
#: what a caller writes when it means "and anything else this parse can raise";
#: a bare `except` catches it too. Nothing else does — and in particular
#: `OSError` does not, which is the entire finding.
#: `"*"` is what `_handler_names` reports for a bare `except:`, which catches
#: this too. It is not an endorsement of bare excepts — `engineering-quality.md`
#: has its own view on those — only an accurate statement that such a clause is
#: not the partial-handler defect this file is about.
_DISCHARGING = frozenset({"UnicodeDecodeError", "ValueError", "Exception",
                          "BaseException", "*"})

#: Sites that legitimately guard a decode with a handler that does not name it,
#: each with the reason. Empty, and an entry added here is a claim a reader can
#: check — which is the point of declaring rather than skipping. The honest
#: state is an empty escape hatch, not a missing one.
_DECLARED: dict[str, str] = {}


def _parents(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    return {child: node
            for node in ast.walk(tree)
            for child in ast.iter_child_nodes(node)}


def _handler_names(handler: ast.ExceptHandler) -> set[str]:
    """Every exception name this clause catches, or `{"*"}` for a bare except."""
    if handler.type is None:
        return {"*"}
    nodes = (handler.type.elts if isinstance(handler.type, ast.Tuple)
             else [handler.type])
    names = set()
    for node in nodes:
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def guarded_decoding_reads(tree: ast.Module) -> list[tuple[int, set[str]]]:
    """`(lineno, caught)` for each `read_text(encoding=…)` inside a `try`.

    `caught` is the UNION over every enclosing `try`, not just the innermost.
    `validate_bag` nests a `BagError`-only clause inside an `OSError` clause, and
    an innermost-only reading would have called that site unguarded while the
    outer clause is the one that actually holds the contract — a predicate that
    reports a site correctly for the wrong reason is one edit from reporting the
    next one wrongly.

    TAKES A PARSED TREE RATHER THAN A PATH so the recogniser can be exercised
    against literal snippets. A recogniser whose only evidence is that it worked
    against the tree on the day it was written is the failure
    `test_a_census_guard_proves_its_own_predicate.py` exists to refuse — and a
    literal test that re-implements the walk instead of calling it proves the
    copy, not the code.
    """
    parents = _parents(tree)
    found: list[tuple[int, set[str]]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "read_text"
                and any(kw.arg == "encoding" for kw in node.keywords)):
            continue
        caught: set[str] = set()
        enclosed = False
        walker: ast.AST | None = parents.get(node)
        while walker is not None:
            if isinstance(walker, ast.Try):
                enclosed = True
                for handler in walker.handlers:
                    caught |= _handler_names(handler)
            walker = parents.get(walker)
        if enclosed:
            found.append((node.lineno, caught))
    return found


def decoding_reads(path: pathlib.Path) -> list[tuple[int, set[str]]]:
    """`guarded_decoding_reads` over one module's source on disk."""
    return guarded_decoding_reads(ast.parse(path.read_text(encoding="utf-8")))


def test_the_sweep_examines_a_NON_EMPTY_population() -> None:
    """A sweep whose population silently emptied is green and asserts nothing.

    A rename of the package, or of `read_text` to a helper, would take every case
    below out without turning one red.
    """
    sites = {f"{p.name}:{lineno}"
             for p in sorted(PACKAGE.glob("*.py"))
             for lineno, _ in decoding_reads(p)}
    assert len(sites) >= 3, (
        f"only {len(sites)} guarded decoding read(s) found under {PACKAGE} — "
        f"either the package moved or the predicate went blind: {sorted(sites)}")


@pytest.mark.parametrize("module_path", sorted(PACKAGE.glob("*.py")),
                         ids=lambda p: p.name)
def test_a_guarded_decode_NAMES_the_decode_failure(
        module_path: pathlib.Path) -> None:
    partial = []
    for lineno, caught in decoding_reads(module_path):
        site = f"{module_path.name}:{lineno}"
        if site in _DECLARED or caught & _DISCHARGING:
            continue
        partial.append((site, sorted(caught)))
    assert not partial, (
        f"a `read_text(encoding=…)` is wrapped in a handler that does not name "
        f"its decode failure: {partial}.\n"
        f"`UnicodeDecodeError` is a `ValueError`, so `except OSError` catches "
        f"the failure everybody thinks of and lets this one through while "
        f"LOOKING handled. Either name it, or add the site to `_DECLARED` in "
        f"{pathlib.Path(__file__).name} with the reason it is safe.\n"
        f"Scope: {PACKAGE} only — this sweep does not see other packages.")


def test_the_predicate_answers_correctly_on_a_LITERAL() -> None:
    """The recogniser, on snippets the package does not contain.

    Both directions, because a predicate that answers "discharged"
    unconditionally passes every case above it.
    """
    def sites(src: str) -> list[tuple[int, set[str]]]:
        return guarded_decoding_reads(ast.parse(src))

    # The live shape: guarded, and the guard does not name the decode failure.
    bad = "try:\n    t = p.read_text(encoding='utf-8')\nexcept OSError:\n    pass\n"
    assert sites(bad) and not (sites(bad)[0][1] & _DISCHARGING)

    # Discharged three ways.
    for src in (
        "try:\n    p.read_text(encoding='utf-8')\nexcept UnicodeDecodeError:\n    pass\n",
        "try:\n    p.read_text(encoding='utf-8')\nexcept (OSError, ValueError):\n    pass\n",
        "try:\n    p.read_text(encoding='utf-8')\nexcept:\n    pass\n",
    ):
        assert sites(src)[0][1] & _DISCHARGING, src

    # The NESTED case, which an innermost-only reading gets wrong: the outer
    # clause is what holds the contract.
    nested = ("try:\n"
              "    try:\n"
              "        p.read_text(encoding='utf-8')\n"
              "    except BagError:\n"
              "        pass\n"
              "except ValueError:\n"
              "    pass\n")
    assert sites(nested)[0][1] & _DISCHARGING

    # Out of scope, and silent rather than falsely clean: no enclosing `try`,
    # and a `read_text` with no encoding argument.
    assert sites("t = p.read_text(encoding='utf-8')\n") == []
    assert sites("try:\n    p.read_text()\nexcept OSError:\n    pass\n") == []


def test_the_escape_hatch_is_EMPTY_or_every_entry_names_a_real_site() -> None:
    """A `_DECLARED` key pointing at nothing is an exemption nobody can check."""
    live = {f"{p.name}:{lineno}"
            for p in sorted(PACKAGE.glob("*.py"))
            for lineno, _ in decoding_reads(p)}
    stale = sorted(set(_DECLARED) - live)
    assert not stale, (
        f"`_DECLARED` exempts sites that no longer exist: {stale}. A line "
        f"number moves with the file, so a stale entry silently exempts "
        f"whatever ends up on that line next.")
