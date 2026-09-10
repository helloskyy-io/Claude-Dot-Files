"""A code identifier named in prose must exist — swept over the Python tree.

WHY THIS FILE EXISTS, AS THE MEASUREMENT RATHER THAN AS A PRINCIPLE. On
2026-09-03 a review pass found `test_journal_regex_anchors.py` justifying the
removal of a declared row with *"`_MUTATION_RE` counts mutations of the array in
any spelling"*. `_MUTATION_RE` had never existed in the tree: it was the SECOND
of three attempts at that guard and was abandoned before it shipped, because
keying on mutation-shape was itself a spelling. The note therefore handed the
next reader the design that had already lost, under a name that resolves to
nothing — inside the file whose own docstring calls a published-and-false
closure worse than an open one.

**Fixing that one sentence was the runway. Sweeping the class found EIGHT MORE
in eight prose sites, and they were nothing like each other:** a helper renamed
and its prose not; a validator that never existed, so the sentence sent a reader
looking for a second gate that was never there; a leading underscore put on a
PUBLIC name, twice, which reads as "module-private, look inside" and is not; and
one function named in THREE files that does not exist, under a parent that no
longer does the job the sentence describes — including in an argument that a
maintainer would refactor away a live call, to a call site nobody could find.
The commit message carries the eight; this docstring deliberately does not, because
a permanent list of dead names in a guard file is the thing the guard exists to
prevent.

Every one of them had survived review, because a name in backticks reads as
already-checked. That is the property this gates: **a false statement in the
block a reader is trained to trust stops them checking**, which is the shape
three sibling modules in this tree already exist to catch on other axes —
`test_no_prose_claims_a_shipped_workflow_is_UNBUILT` for a workflow asserted
absent, `test_docstrings_do_not_promise_a_raise` for a contract table promising
a raise, `test_no_live_surface_advertises_a_superseded_contract` for a retired
contract. This one closes the symbol-resolution axis.

WHAT IT KEYS ON. A backticked span in a COMMENT or a DOCSTRING whose content is
a module-private identifier (_<name>) or a qualified one (mod._<name>), matched
against every name BOUND anywhere in the tracked Python and shell. Private,
deliberately: a leading underscore is what makes a backticked token unambiguously
a reference to code rather than an English word, a CLI flag or a file name. The
resolution set is derived from the tree, so a rename retires every claim about
the old name the day it lands, with no list to maintain.

WHY THIS ONE IS REPO-WIDE WHILE THREE OF ITS FOUR SIBLINGS ARE PACKAGE-SCOPED.
`test_no_prose_claims_a_shipped_workflow_is_UNBUILT`, `test_docstrings_do_not_
promise_a_raise` and `test_a_census_guard_proves_its_own_predicate` each check a
contract that only the temporal package HAS, so their scope is the package. A
symbol either exists in this repository or it does not — the question has no
package boundary, and narrowing the RESOLUTION set to one package would report
every cross-package reference as a ghost. So it lives beside the fourth sibling,
`test_no_live_surface_advertises_a_superseded_contract`, in the repo-wide suite.

⚠ IT SEES UNCOMMITTED FILES, AND KEYING ON `git ls-files` ALONE WAS A DEFECT IN
THIS FILE'S FIRST DRAFT. The corpus is `--cached --others --exclude-standard`,
so a file being written right now is both swept and resolvable. With the bare
`--cached` form this module was green against its OWN docstring, which at that
moment named nine symbols that do not exist — a guard blind to exactly the edit
that is being made is green when it matters and red only afterwards.

⚠ THE `_DECLARED` LIST BELOW IS NOT AN ALLOWLIST FOR STALENESS, and two checks
hold it to that. A row must still be UNRESOLVED — the day somebody defines a
real `_MUTATION_RE`, the row describing it as never-shipped becomes false and
goes red. And no row may be ORPHANED: when the prose that needed it goes, so
does the row. Each row carries the reason a reader can check, which is the same
bar `test_journal_regex_anchors` sets for its own exemptions.

⚠ WHAT THIS DOES NOT COVER, because a sweep is only as good as its predicate:

  * IT SWEEPS `scripts/` AND `testing/scripts/` AND NOTHING ELSE — the temporal
    fleet, the helper scripts beside it, and the repo-wide guard suite. `testing/config-hooks/` is
    OUT, and not because it is clean: one comment there names a variable from
    the 193-line scratch-delete elision that `block-dangerous.sh` deleted on
    2026-08-15. That is a live instance of this exact class, and correcting it
    is not a rename — the sentence's whole premise is a mechanism that no longer
    exists, so it needs a read of what that sweep is still for. It is SURFACED
    on the PR that added this file rather than laundered into a row below.
    Widening the scope is what closes it.
  * IT RESOLVES AGAINST THIS TREE'S BINDINGS AND NOTHING ELSE, so a prose
    reference to a name the RUNTIME provides — `_replace`, `_field_defaults` on
    a `NamedTuple` — needs a row below. That is two rows across the whole tree,
    and it is the price of the resolver counting only what is BOUND: an earlier
    draft also counted every LOAD, which meant a ghost resolved against any
    unrelated local sharing its spelling. A resolver looser than its own
    docstring is this module's own defect class, so the rows are the honest arm.
  * IT ONLY SEES PRIVATE NAMES. A public function named in prose after being
    deleted is invisible. Public names collide with prose words often enough
    that the false-positive rate would decide the gate's fate, and a gate
    answered by suppression is worse than no gate.
  * IT RESOLVES A NAME, NOT A CLAIM. *"`_NAME_RE` matches an empty string"*
    passes here and is false. Quotation fidelity is the adjacent axis and is
    proposed separately at `C-gbclnzsq`.
"""

from __future__ import annotations

import ast
import io
import os
import re
import subprocess
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]

# The Python fleet and the repo-wide guard suite. See the docstring for why
# `testing/config-hooks/` is outside it and what is known to be sitting there.
SWEPT_PREFIXES = ("scripts/", "testing/scripts/")

# A backticked module-private identifier, optionally qualified by a module. The
# trailing `[A-Za-z0-9]` refuses a name ending in `_`, which is how this tree
# writes a PREFIX fragment (`_verify_`, `_assert_`) rather than a name.
_REFERENCE = re.compile(r"`(?:[A-Za-z_][A-Za-z0-9_]*\.)?(_[A-Za-z0-9_]*[A-Za-z0-9])`")

# A shell function or variable binding — `name() {`, `function name`, `name=`.
_SHELL_BINDING = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(\)|=)")

# Names that appear in prose, resolve to nothing, and are NOT defects. Each row
# is a claim a reader can check, and `test_no_DECLARED_row_has_gone_stale` fails
# the day one stops being true.
_DECLARED: dict[str, str] = {
    "_APPEND_RE":
        "a DELETED pattern, narrated as history. Three sibling comments explain "
        "why the config digest stopped keying on `SYMLINK_TARGETS+=(`; naming "
        "the pattern that lost IS the explanation, and blanking it would leave "
        "the reasoning without a subject.",
    "_read_task_file":
        "a DELETED function, narrated as history at two sites — same shape as "
        "`_APPEND_RE` above. It was `run_plan_revision.py`'s task-source reader "
        "until `main` deleted that runner on 2026-09-05. "
        "`test_a_task_SOURCE_path_is_anchored_to_the_repo.py` records it as one "
        "of the nine read sites a past sweep FOUND, and "
        "`test_journal_prose_figures_are_DERIVED.py` names it as the unrelated "
        "handler that made a deriver read 9 against a correct prose figure of "
        "10. Both sentences are about what was true then, and naming the site "
        "IS the explanation. The one site that made a LIVE claim — "
        "`anchor_task_source`'s docstring, which justified its own existence by "
        "this consumer — was corrected rather than declared.",
    "_MUTATION_RE":
        "a pattern that NEVER SHIPPED — the second failed attempt at the same "
        "guard. Named in `test_journal_regex_anchors.py` precisely so a reader "
        "does not re-derive it; that file's row is the correction this module "
        "was written alongside.",
    "_SOME_NAME":
        "an illustrative placeholder inside a regex-shape description in "
        "`test_a_prose_COUNT_of_a_collection_is_DERIVED.py`, not a reference.",
    "_field_defaults":
        "a `typing.NamedTuple` API member — REAL, but provided by the runtime "
        "rather than bound in this tree. `test_plan_candidates.py` reads it off "
        "`Scaffolded` at line 894.",
    "_replace":
        "a `typing.NamedTuple` API member, same as `_field_defaults` above.",
    "_event":
        "a DICT KEY, in `replay_run_resources.py`, from a removed earlier "
        "version of the row builder. Never an identifier.",
    "_from_plan":
        "a PROMPT-FILE suffix (`stages_1_to_4_from_plan.md`), not an identifier.",
    "_minor":
        "a WORKFLOW-VARIANT suffix (`build_minor.sh`, `build_draft_minor`), not "
        "an identifier.",
    "_v2":
        "a FILENAME suffix, discussed in `test_plan_draft.py` as the thing the "
        "phase-doc filename regex does and does not forbid.",
    "_workflow":
        "a MODULE-NAME suffix every child workflow module carries; "
        "`_child_workflow_imports` keys on it.",
}


# A backticked TEST MODULE FILENAME, optionally path-qualified. The `.py` is the
# discriminator and it is why this half is decidable while bare test-FUNCTION
# names are not: a citation carrying the suffix is unambiguously a file, whereas
# a bare one is also a parametrize id, a prompt-variant stem and a section
# heading. (An illustrative example cannot be written here, because this gate
# reads its own comments and would report the example as a ghost — which it did,
# to this paragraph's first draft.) Measured
# over the swept tree: 32 bare-name citations do not resolve and almost all are
# false positives, against 11 filename citations of which every one was a real
# question. Keying on the half that discriminates is the whole lesson of the
# `_ROOTS` recogniser two files over.
_TEST_MODULE = re.compile(r"`([A-Za-z0-9_/]*\btest_[A-Za-z0-9_]+\.py)`")

# Test modules named in prose that are NOT in the tree and are NOT defects.
#
# ⚠ KEYED BY (FILE, NAME) AND NOT BY NAME, AND THE FIRST DRAFT WAS KEYED BY NAME.
# That draft's negative control PASSED when the deleted citation was put back at
# the exact site a reviewer had just found it — because one row exempting the
# name covered every site in the tree, including sites that did not exist when
# the row was written. A deleted test module is cited in HISTORY at a handful of
# known places and in ERROR anywhere; an exemption that cannot tell those apart
# retires the gate for the one name it most needs to watch. The three historical
# mentions below are three ROWS, and a fourth site naming any of them is a
# finding.
_DECLARED_TEST_MODULES: dict[tuple[str, str], str] = {
    ("testing/scripts/tests/unit/gfm_table_scan.py",
     "test_candidates_prose_matches_the_table.py"):
        "DELETED in `91925af` with the `candidates.md` corpus it gated. Narrated "
        "as history: these scanning helpers were private to it until a repo-wide "
        "gate needed the same boundary, and naming the file IS that explanation.",
    ("testing/scripts/tests/unit/test_markdown_tables_render_whole.py",
     "test_candidates_prose_matches_the_table.py"):
        "same deletion, narrated as history at ONE remaining site — the first "
        "draft of this gate path-loaded it, which is the PR #96 coupling "
        "`test_test_tree_hygiene.py` was widened for. The other three mentions "
        "in this file made LIVE claims (a \"sibling\" comparison, a COMPANION "
        "instruction to delete it in one commit) and were corrected, not "
        "declared.",
    ("testing/scripts/tests/unit/test_test_tree_hygiene.py",
     "test_candidates_prose_matches_the_table.py"):
        "same deletion. This is the MEASUREMENT that produced this file's "
        "dynamic-load gate — a correction pass reached four private helpers out "
        "of it by `spec_from_file_location`. The measurement is about that file "
        "and cannot be restated without it.",
    ("scripts/workflows/temporal/modules/journal/verify.py",
     "test_verify_is_offline.py"):
        "a file that NEVER EXISTED. `verify.py` names it in the act of saying so "
        "— the sentence IS the correction, and blanking the name leaves it "
        "without a subject.",
    ("testing/scripts/tests/unit/test_mutate.py",
     "test_subject.py"):
        "a fixture WRITTEN AT RUN TIME into a `tmp_path` sandbox by this file, "
        "never a tracked one. A real module that exists only while the test that "
        "creates it is running.",
}


def unresolved_test_modules(source: str, filenames: set[str]) -> list[tuple[int, str]]:
    """`(lineno, name)` for every backticked test-module filename that is not a file."""
    found: list[tuple[int, str]] = []
    for lineno, text in prose_of(source):
        for match in _TEST_MODULE.finditer(text):
            if match.group(1).split("/")[-1] not in filenames:
                found.append((lineno, match.group(1).split("/")[-1]))
    return found


def _tracked(pattern: str) -> list[Path]:
    """Tracked files AND untracked-but-not-ignored ones. See the docstring.

    `--others --exclude-standard` is what makes this module see a file being
    written right now, including itself. Without it a new guard is green against
    its own prose until the moment it is committed, which is after review.
    """
    out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others",
                          "--exclude-standard", pattern], cwd=ROOT,
                         capture_output=True, text=True, check=True)
    # `-z` and NUL, not `.split()`: a tracked path may contain a space, and
    # whitespace-splitting would shred it into two paths that do not exist.
    return sorted({ROOT / line for line in out.stdout.split("\0") if line})


def bound_names(python_files: list[Path], shell_files: list[Path]) -> set[str]:
    """Every name BOUND by the tree — never one that only appears in prose.

    Derived from the AST rather than from the text, which is the whole point: a
    name that exists only inside the comment claiming it exists must not resolve
    itself. `ast.Name`/`ast.Attribute`/`ast.arg`/`ast.alias` are included so a
    local, an attribute and an import alias all count as existing.
    """
    names: set[str] = set()
    for path in python_files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue        # `test_no_module_compiles_with_a_SYNTAX_WARNING` owns this
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, (ast.Name, ast.Attribute)):
                # STORE/DEL ONLY. A LOAD is a name being USED, and counting uses
                # would let a ghost resolve against any unrelated local that
                # happens to share its spelling — the guard would then be looser
                # than its own docstring, which is this module's own defect class.
                if isinstance(node.ctx, (ast.Store, ast.Del)):
                    names.add(node.id if isinstance(node, ast.Name) else node.attr)
            elif isinstance(node, ast.arg):
                names.add(node.arg)
            elif isinstance(node, ast.alias):
                names.add((node.asname or node.name).split(".")[0])
    for path in shell_files:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = _SHELL_BINDING.match(line)
            if match:
                names.add(match.group(1))
    return names


def prose_of(source: str) -> list[tuple[int, str]]:
    """`(lineno, text)` for every comment and docstring in `source`.

    Comments come from `tokenize` and docstrings from the AST, so a string
    LITERAL that is not a docstring — a test fixture holding source code, an
    error message — is not scanned. Prose is what makes a claim; a fixture does
    not.
    """
    prose: list[tuple[int, str]] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            prose.append((token.start[0], token.string))
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            text = ast.get_docstring(node, clean=False)
            if text:
                prose.append((getattr(node, "lineno", 1), text))
    return prose


def unresolved_in(source: str, names: set[str]) -> list[tuple[int, str]]:
    """`(lineno, name)` for every prose reference in `source` that resolves to nothing."""
    found: list[tuple[int, str]] = []
    for lineno, text in prose_of(source):
        for match in _REFERENCE.finditer(text):
            if match.group(1) not in names:
                found.append((lineno, match.group(1)))
    return found


def _swept() -> list[Path]:
    return [p for p in _tracked("*.py")
            if str(p.relative_to(ROOT)).startswith(SWEPT_PREFIXES)]


@pytest.fixture(scope="module")
def names() -> set[str]:
    return bound_names(_tracked("*.py"), _tracked("*.sh"))


def test_the_sweep_reads_a_real_corpus() -> None:
    """A floor on the WALK. A predicate over nothing is green forever."""
    files = _swept()
    assert len(files) > 150, f"only {len(files)} Python files in scope — the walk broke"


def test_the_corpus_INCLUDES_A_FILE_THAT_IS_NOT_COMMITTED_YET() -> None:
    """The guard must see the edit UNDER REVIEW, not only the last one merged.

    Measured on this module: with a bare `git ls-files` corpus it was green
    against its own docstring, which at that moment named nine symbols that do
    not exist. A guard blind to uncommitted files is green exactly when it
    matters and red only after the PR has merged.

    The probe is written into the swept tree because that is the only place the
    property is decidable — `git ls-files` answers about the repository, not
    about a `tmp_path`. It is named so pytest will not collect it and removed in
    a `finally`.
    """
    probe = Path(__file__).parent / f"_corpus_probe_{os.getpid()}.py"
    probe.write_text("# probe\n", encoding="utf-8")
    try:
        assert probe in _swept(), (
            "an uncommitted file in the swept tree is invisible to this guard — "
            "the corpus has lost `--others --exclude-standard`")
    finally:
        probe.unlink()


def test_the_extractor_FINDS_references_at_all(names: set[str]) -> None:
    """A floor on the EXTRACTOR, which the walk floor above does not give.

    `prose_of` could return nothing — a tokenize change, a docstring shape — and
    every assertion below would pass over an empty stream. So: the tree's prose
    must contain a large number of private references that DO resolve.
    """
    resolving = 0
    for path in _swept():
        source = path.read_text(encoding="utf-8", errors="replace")
        for _, text in prose_of(source):
            resolving += sum(1 for m in _REFERENCE.finditer(text)
                             if m.group(1) in names)
    assert resolving > 100, (
        f"only {resolving} resolving private references found in the tree's prose "
        f"— the extractor is not reading what it claims to read")


def test_the_resolver_DISCRIMINATES(names: set[str]) -> None:
    """A floor on the RESOLVER. If it answered "yes" to everything, nothing fails.

    Both directions, because one alone is a half-check: a real module-private
    name resolves, and a name shaped exactly like one does not.
    """
    assert "_SEGMENT_RE" in names, "a real module-private name did not resolve"
    assert "_a_name_no_module_in_this_tree_binds" not in names


def test_EVERY_PRIVATE_NAME_PROSE_CITES_RESOLVES_OR_IS_DECLARED(names: set[str]) -> None:
    """THE RULE: a backticked _<name> in a comment or docstring must exist."""
    findings: list[str] = []
    for path in _swept():
        source = path.read_text(encoding="utf-8", errors="replace")
        for lineno, name in unresolved_in(source, names):
            if name in _DECLARED:
                continue
            findings.append(f"{path.relative_to(ROOT)}:{lineno}: `{name}`")
    assert not findings, (
        "prose names a module-private symbol that does not exist anywhere in the "
        "tree. A name in backticks reads as already-checked, so a wrong one stops "
        "the next reader checking. Correct it to the name that shipped, or — if "
        "it is deliberately historical — add a row to `_DECLARED` with the reason:"
        "\n  " + "\n  ".join(findings) +
        f"\n\nSCOPE: {SWEPT_PREFIXES}. A name outside it is invisible here.")


# ---------------------------------------------------------------------------
# THE SECOND AXIS: a TEST MODULE named in prose must exist.
#
# Added after a review pass found `test_a_census_guard_proves_its_own_predicate`
# — the file whose thesis is that a coverage claim must be derived or must not be
# written — enumerating "four corpora" and naming a gate deleted in `91925af`.
# Sweeping the class found the SAME deleted filename at SEVEN sites in five
# files, four of them making live claims, plus two other prose-only test modules
# that do not exist. That is why this is a predicate and not seven corrections:
# the previous pass corrected the two dead citations it found by script, and this
# one was in the file class that sweep excluded.
#
# A test module named in prose is the strongest possible form of the thing
# `_REFERENCE` gates: it does not merely read as already-checked, it reads as
# ALREADY-ENFORCED. A reader auditing what is covered stops at the name.


@pytest.fixture(scope="module")
def filenames() -> set[str]:
    """Every file basename in the tree — uncommitted ones included, per `_tracked`."""
    return {path.name for path in _tracked("*")}


def test_the_test_module_extractor_FINDS_references_at_all(
        filenames: set[str]) -> None:
    """A floor on the second extractor, which the first one's floor does not give."""
    resolving = 0
    for path in _swept():
        source = path.read_text(encoding="utf-8", errors="replace")
        for _, text in prose_of(source):
            resolving += sum(1 for m in _TEST_MODULE.finditer(text)
                             if m.group(1).split("/")[-1] in filenames)
    assert resolving > 50, (
        f"only {resolving} resolving test-module citations found in the tree's "
        f"prose — the extractor is not reading what it claims to read")


def test_EVERY_TEST_MODULE_PROSE_CITES_EXISTS(filenames: set[str]) -> None:
    """THE RULE: a backticked `test_*.py` in a comment or docstring must be a file."""
    findings: list[str] = []
    for path in _swept():
        source = path.read_text(encoding="utf-8", errors="replace")
        relpath = str(path.relative_to(ROOT))
        for lineno, name in unresolved_test_modules(source, filenames):
            if (relpath, name) in _DECLARED_TEST_MODULES:
                continue
            findings.append(f"{relpath}:{lineno}: `{name}`")
    assert not findings, (
        "prose names a test module that is not in the tree. A named test reads "
        "as already-ENFORCED, so a deleted one stops the next reader checking "
        "whether the property is covered at all. Correct it to the gate that "
        "ships, or — if the mention is deliberately historical — add a row to "
        "`_DECLARED_TEST_MODULES` for THIS FILE with the reason (rows are keyed "
        "by site, so declaring a name elsewhere does not cover this one):"
        "\n  " + "\n  ".join(findings) +
        f"\n\nSCOPE: {SWEPT_PREFIXES}. A file outside it is invisible here.")


def test_no_DECLARED_TEST_MODULE_row_has_gone_stale(filenames: set[str]) -> None:
    """A row claims the module does not exist. Re-creating it expires the row."""
    live = sorted(name for _, name in _DECLARED_TEST_MODULES if name in filenames)
    assert not live, (
        f"these `_DECLARED_TEST_MODULES` rows name files that NOW EXIST: {live}. "
        f"The row's reason is no longer true — delete it, and check the prose it "
        f"was exempting still says the right thing about the file that now exists.")


def test_every_DECLARED_TEST_MODULE_row_is_still_REACHED(
        filenames: set[str]) -> None:
    """A row for a module nobody cites is dead weight that reads as coverage."""
    cited: set[tuple[str, str]] = set()
    for path in _swept():
        source = path.read_text(encoding="utf-8", errors="replace")
        relpath = str(path.relative_to(ROOT))
        cited.update((relpath, name)
                     for _, name in unresolved_test_modules(source, filenames))
    orphaned = sorted(set(_DECLARED_TEST_MODULES) - cited)
    assert not orphaned, (
        f"`_DECLARED_TEST_MODULES` rows nothing cites any more: {orphaned}. The "
        f"prose that needed the exemption is gone; delete the row with it.")


_GHOST_TEST_MODULE = '''
# Held by `test_a_gate_that_was_deleted.py`, which does not exist.
X = 1
'''

_REAL_TEST_MODULE = '''
# Held by `test_prose_NAMES_a_symbol_that_RESOLVES.py`.
X = 1
'''

_TEST_FUNCTION_NOT_A_MODULE = '''
# The property is held by `test_the_thing_is_held`, a function and not a file.
X = 1
'''


def test_the_test_module_predicate_CATCHES_a_deleted_gate() -> None:
    found = unresolved_test_modules(_GHOST_TEST_MODULE, {"anything.py"})
    assert [name for _, name in found] == ["test_a_gate_that_was_deleted.py"]


def test_the_test_module_predicate_PASSES_a_gate_that_exists() -> None:
    assert unresolved_test_modules(
        _REAL_TEST_MODULE,
        {"test_prose_NAMES_a_symbol_that_RESOLVES.py"}) == []


def test_the_test_module_predicate_IGNORES_a_bare_FUNCTION_name() -> None:
    """The `.py` is the discriminator. Bare `test_*` spans are also parametrize
    ids, prompt-variant stems and section headings — 32 of them do not resolve in
    this tree and almost none is a defect, so matching them would make this gate
    answered by suppression, which is worse than no gate."""
    assert unresolved_test_modules(_TEST_FUNCTION_NOT_A_MODULE, set()) == []


def test_no_DECLARED_row_has_gone_stale(names: set[str]) -> None:
    """A declared row claims a name resolves to NOTHING. That expires.

    The day somebody defines a real `_MUTATION_RE`, the row calling it
    never-shipped is false and the exemption is silently hiding a live reference
    to a real thing. A row here may only describe a name the tree does not bind.
    """
    live = sorted(name for name in _DECLARED if name in names)
    assert not live, (
        f"these `_DECLARED` rows name symbols that NOW EXIST: {live}. The row's "
        f"reason is no longer true — delete the row, and check the prose it was "
        f"exempting still says the right thing about the symbol that now exists.")


def test_every_DECLARED_row_is_still_REACHED(names: set[str]) -> None:
    """A row for a name nobody cites any more is dead weight that reads as coverage."""
    cited = set()
    for path in _swept():
        source = path.read_text(encoding="utf-8", errors="replace")
        cited.update(name for _, name in unresolved_in(source, names))
    orphaned = sorted(set(_DECLARED) - cited)
    assert not orphaned, (
        f"`_DECLARED` rows nothing cites any more: {orphaned}. The prose that "
        f"needed the exemption is gone; delete the row with it.")


# ---------------------------------------------------------------------------
# Predicate controls, against literal snippets rather than against the tree.
# `test_a_census_guard_proves_its_own_predicate` requires this of any module
# that walks the tree, and the reason is measured: a walk that still finds
# sites keeps every floor green while the predicate stops discriminating.

_GHOST_IN_A_COMMENT = '''
# The population is established by `_GHOST_RE`, which does not exist.
X = 1
'''

_GHOST_IN_A_DOCSTRING = '''
def f():
    """Delegates to `helper._GHOST_RE`, which does not exist."""
    return 1
'''

_GHOST_IN_A_FIXTURE = '''
SNIPPET = """a fixture mentioning `_GHOST_RE`, which is not prose"""
'''

_REAL_REFERENCE = '''
# The population is established by `_REAL_RE`.
_REAL_RE = 1
'''

_PREFIX_FRAGMENT = '''
# Every helper in this module carries a `_verify_` prefix.
X = 1
'''


@pytest.mark.parametrize("snippet", [_GHOST_IN_A_COMMENT, _GHOST_IN_A_DOCSTRING],
                         ids=["comment", "docstring"])
def test_the_predicate_CATCHES_a_ghost_in_prose(snippet: str) -> None:
    found = unresolved_in(snippet, {"helper", "f", "X"})
    assert [name for _, name in found] == ["_GHOST_RE"]
    # The line number is checked against the snippet, not against the function
    # under test — deriving the expectation from the result proves nothing.
    assert found[0][0] == next(i for i, line in enumerate(snippet.splitlines(), 1)
                               if "_GHOST_RE" in line) - (0 if "#" in snippet.splitlines()[
                                   found[0][0] - 1] else 1)


def test_the_predicate_IGNORES_a_string_that_is_not_prose() -> None:
    """A fixture holding source text is not a claim, and scanning it would make
    every guard that quotes a snippet answer for the snippet's contents."""
    assert unresolved_in(_GHOST_IN_A_FIXTURE, {"SNIPPET"}) == []


def test_the_predicate_PASSES_a_reference_that_resolves() -> None:
    assert unresolved_in(_REAL_REFERENCE, {"_REAL_RE"}) == []


def test_the_predicate_IGNORES_a_PREFIX_fragment() -> None:
    """`_verify_` is how this tree writes "every name starting with"; the
    trailing underscore is the discriminator and it is in the pattern."""
    assert unresolved_in(_PREFIX_FRAGMENT, {"X"}) == []
