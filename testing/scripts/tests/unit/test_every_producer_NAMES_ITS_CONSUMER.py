"""Every producer names its consumer, across every surface ruled in — and every
directory in the repo is RULED, in or out, by name.

WORKFLOW DECOMPOSITION PHASE 6. A surface written by one part of the system and
read by no other part is not neutral: it costs the run that produces it, it looks
like coverage to a reader, and nothing goes red when it stops being correct —
because nothing was ever checking. Measured twice here. Three parent-written
observables shipped with no reader at all; and the directory that governs the
measurement tools stated its own *"a `Read by` column with nothing in it is a
finding"* rule **in prose**, one level up from the tools it governs — nothing
enforced it, and a tool shipped unread anyway.

THE DEFINITION (requirement 1), stated once, here, because this is where the
check is built from it:

    A PRODUCER is a surface one part of the system writes for another part to
    read. It is CONFORMANT when its consumer is NAMED; and, when the surface
    ACCUMULATES items awaiting disposition, when that consumer is additionally
    invoked on a NAMED CADENCE by a NAMED RUNNER.

    The keying is on *something is meant to read this*, never on *this writes a
    file*. A check keyed on the second catches every temp file in the tree and
    gets disabled within a month.

    DELIBERATELY EXCLUDED, and each exclusion is asserted BY NAME below because
    an exclusion that is not named is a hole:

      * A DECLARATION MODULE — code defining a surface's shape, loaded by the
        tools rather than run beside them. `measure/run_log.py` is the one.
      * A SURFACE WHOSE ONLY LEGITIMATE CONSUMER IS A HUMAN — `tracked/
        operations/`, and `config/commands/`. No check can assert that a
        person read something, and a proxy like file mtime is routed around
        within a month.
      * A SURFACE THE HARNESS LOADS WHOLESALE — `config/rules/`, `config/
        skills/`, `.github/`. Every member is read every time by construction;
        there is no per-member consumer to name and none can go unread.
      * TESTS — any `tests/` directory, and the harness under `testing/`. Read
        by the runner, not by the system.
      * CODE CONSUMED BY IMPORT — `modules/`. The import graph, the suite and
        `code-reviewer`'s structure lens hold it; a gate keyed on names would
        re-implement dead-code detection badly. The THREE FLAT LIBRARIES beside
        the entrypoints (`preflight.py`, `dispatch_identity.py`,
        `dispatch_context.py`) are NOT this class: `scripts/` is no package,
        each is loaded by a `sys.path` insert and a bare stem import, and that
        is one shape an AST predicate can see — so they are ruled IN below.
      * A SURFACE HELD BY ANOTHER GATE — the shared prompt pool, the repo map.
        Named here with the gate that holds it, so a reader can go and check
        that claim rather than take it.
      * A TRANSIENT ARTIFACT — a temp file, a log, a build output written for
        the writer's own use. `_is_transient` is the rule; unlike the classes
        above it is NOT asserted against the tree, because a transient
        artifact's absence is the normal case.

TWO WAYS A CONSUMER IS NAMED, and the difference is where the claim lives.

  * A TABLE surface (`measure/`, `scripts/helpers/`, `tracked/`) carries a
    README whose rows name each member's consumer. The gate holds the
    population — a member with no row fails — and a person holds the cell.
  * A DERIVED surface (`config/hooks/`, `config/agents/`, the bash libraries,
    `scripts/services/`, `testing/suites/`, the three bash workflows, and the
    four populations of `scripts/workflows/temporal/scripts/`) has no table,
    and cannot: `config/agents/` and `config/hooks/` are symlinked
    WHOLESALE into `~/.claude/`, so a README there would be loaded as an agent
    named `README`. Its consumer is FOUND on disk by a predicate written for
    that surface's own invocation shape — `settings.json` for a hook, a
    `source` line for a bash library, a `$SERVICES_DIR/` reference for a
    service — and the gate is the surface's declaration. A member the
    predicate finds nothing for fails unless it is baselined in `unread`.

  The derived shape is the STRONGER claim: the consumer was opened and read,
  which for a table surface is only done on `scripts/helpers/`. Its cost is
  that the predicate can be wrong in either direction, which is why every one
  of them has a self-contained control below.

AND EVERY DIRECTORY IN THE REPO IS RULED. `test_every_DIRECTORY_in_the_repo_is_
RULED` walks `git ls-files` and demands each directory be a ruled-in surface, a
`RULED_OUT` entry with its reason, a `CONTAINER` whose own DIRECT files are
each named with a reader — asserted against `git ls-files`, not read as prose —
or a `tests/` directory. A new directory fails until somebody rules it, and a
new file dropped straight into a container fails until somebody names its reader.
That is the phase's *"enumerate the remaining candidate producer surfaces
across the fleet and rule each in or out"* step, made a check rather than a
list: the list was wrong three times in a fortnight.

(This file superseded `test_measure_readme_names_a_consumer.py`, and moved
from `scripts/helpers/tests/unit/` to here when its population stopped being
one directory's. The repo-wide gates no code unit owns live in this directory.)

WHY THE CADENCE CLAUSE IS CONDITIONAL (requirement 2, RULED 2026-09-10). The
three properties were borrowed from `Tracked Items Standard` §0, which governs
STORES — surfaces that accumulate items awaiting a decision — and whose exit
clause is about items reaching a terminal state. This phase generalises them to
PRODUCERS, a wider class containing members nothing accumulates in.
`scripts/workflows/temporal/scripts/compare_run_config.py` is the worked test
case: a named machine reader, invoked on demand, over bags that are never edited
after sealing. Requiring a cadence of it would mean inventing a schedule to
satisfy a check, which is how a gate gets routed around. So an ON-DEMAND READER
IS A CONFORMANT CONSUMER, and the cadence clause binds accumulating surfaces
only. `tracked/` is the accumulating surface here and carries the stronger check.

*(§0 governs stores and says nothing about generalising. The generalisation is
this phase's claim to defend — do not cite §0 as though it already ruled the
fleet.)*

WHAT THIS GATE DOES NOT LOOK AT. Stated here so nobody over-reads a green suite:

  * It does not check that a consumer is any GOOD. Naming a reader is a much
    weaker claim than the reader being correct, and only the weaker one is made.
  * It does not check that a named invoker's ARGUMENTS are right, that the code
    path is ever taken at runtime, or that anyone reads the output once produced.
  * A derived predicate finds a MENTION in the shape an invocation takes. It
    cannot tell a `source` line inside a dead branch from a live one, or a
    rule that names an agent to explain it from one that dispatches it. The
    gap between *mentions* and *invokes* is recorded in
    `scripts/helpers/README.md` and is not closed here either.
  * It does not reach INSIDE a ruled-out directory, and no directory is any
    longer ruled out for being unruled. `scripts/workflows/temporal/scripts/`
    was — #181 said so in its own `RULED_OUT` reason — and is now FOUR
    surfaces on one root, one per consumer shape the directory holds: a shim
    is named in an operator document (the bash workflows' claim), a runner
    is exec'd by a shim beside it, a library is imported by stem from a fleet
    module, a tool is named in an operator document. The four member
    predicates partition the directory, and that partition is asserted, so a
    file of a fifth shape fails rather than falling between them. What the
    four DO NOT see: a shim's usage line naming itself and a runner existing
    beside every shim (both HELD BY `test_shim_usage_names_itself.py`, the
    shim→runner direction — the runner surface here is the reverse, which
    nothing held before); and Phase 4's dispatch-context ECHO
    (`RunContext.echo`, shipped 2026-09-01), a producer ruled by NAME rather
    than by surface, whose consumer is the operator reading stderr — the
    human-only class — and whose presence at every entrypoint is HELD BY
    ANOTHER GATE (`HELD_BY`). #170 recorded the echo as un-landed; it had
    landed.
  * A RECORD A RUN WRITES FOR A LATER RUN — a journal bag's files and tags,
    the typed exit record, the run log's member events — is written under a
    configured root OUTSIDE any tracked tree, so the `git ls-files` walk
    cannot reach it, and the phase's own table calls this class *"probably
    in, and this is where the real value is"*. It IS ruled, by declaration
    rather than by walk (`RUNTIME_RECORDS`, ruled 2026-09-14): the population
    is every file-or-directory constant the journal package declares
    (`MANIFEST_FILE`, `PAYLOAD_DIR`, … — the suffix is `_RECORD_CONSTANT`)
    plus every run-log member type, each must name a reader, and a reader RESOLVES
    only when its module is on disk, its entry function is defined, it names
    the record's declared symbol as a code token, and every hop from the
    operator tool or parent branch down to it imports the next by stem. The
    run log's WRITE side stays with `HELD_BY`; this is its read side. What
    the ruling does NOT see: it never opens a bag, so a reader that names
    the right constant and reads the wrong file passes; a record declared by
    a name `_RECORD_CONSTANT` does not match is outside the derived
    population and must be registered by hand (the exit record and the
    config-digest tag are, with that said); and the unread ratchet keys on
    the record's read ACCESSOR, so a
    reader that re-types the filename and parses lines itself is invisible
    to it. One record was found unread when the class was ruled — the bag's
    event stream, `events.jsonl`, decoded by tests only until Persistent
    Memory Protocol Phase 4's replay lands — and is frozen in
    `UNREAD_RUNTIME_RECORDS` rather than given a reader to make a check green.
  * A "HELD BY ANOTHER GATE" claim is a cross-file coverage claim, and one
    whose holder was renamed covers nothing while reading as if it did. So
    every holder is registered in `HELD_BY` and asserted to resolve to a test
    function that exists, and a holder named in a ruling's prose must be in
    that registry.
  * It does not DELETE an unread producer. Finding one is the output; ruling
    what happens to it is a separate decision with its own criteria. The four
    findings this sweep produced are baselined, not fixed, for that reason.
  * On a clone with no sibling planning repo the `tracked/` surface and the
    bash-workflow surface SKIP. That is a real coverage gap rather than a
    neutral fallback (`C-8z8v04wk`), and THE GITHUB RUNNER IS SUCH A CLONE —
    it checks out this repo alone, so those two surfaces assert nothing
    there. The runner with both repos side by side is the planned own-CI
    that candidate names, not the one that gates merges today.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]

# ONE IMPLEMENTATION OF "WHERE IS THE PLANNING REPO", NOT A SECOND ONE. The walk
# is the part that is easy to get wrong: under a worktree the repo root's parent
# is `.claude/worktrees/`, not the directory the two repos share, so a naive
# `_REPO.parent / "skyynet-master-planning"` resolves to nothing on exactly the
# checkouts every dispatch runs in.
sys.path.insert(0, str(_REPO / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import PLANNING_ROOT  # noqa: E402
from file_structure_map import LEAF as _MAP_LEAF, MAP as _MAP  # noqa: E402

_ENTRYPOINTS = _REPO / "scripts" / "workflows" / "temporal" / "scripts"


def _is_transient(p: Path) -> bool:
    """The docstring's transient-artifact class, in code rather than in prose.

    A transient artifact is written for its writer's own use and is gitignored;
    it has no consumer to name and no row to carry. It is NOT asserted against
    the tree the way a named exclusion is — its absence is the normal case, so
    a check that its subject still exists would fail on a clean checkout.

    THIS IS WHY THE GATE WAS GREEN LOCALLY AND RED ON CI. `__pycache__` appears
    under `scripts/helpers/` the moment anything imports a module from it, which
    `test_the_standards_index_is_ACTUALLY_CLEAN.py` does. The authoring shell had
    `PYTHONDONTWRITEBYTECODE=1` and the runner's did not, so the off-disk
    subdirectory read asserted something true only of the machine that wrote it.
    """
    return p.name == "__pycache__" or p.name.startswith(".")


def _text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _names(member: str, text: str) -> bool:
    """`text` names `member` as a whole token.

    A substring test says `build.sh` is named by a line reading `rebuild.sh`
    or `build.sh.bak`; this does not. A path separator, a quote or a backtick
    before the name is allowed — those are how a file is named — and a word
    character, a dot or a hyphen is not, because then the name is part of a
    longer one. `-` is in the excluded set on BOTH sides so that
    `quality-control` is not found inside `quality-control-methodology.md`.
    """
    return re.search(rf"(?<![\w.-]){re.escape(member)}(?![\w.-])", text) is not None


def _strip_trailing_comment(line: str) -> str:
    """`line` up to a `#` that starts a comment: preceded by whitespace and
    OUTSIDE quotes. `"PR #${pr}"` is not a comment and the invocation after it
    is live — `wait-for-ci.sh` carries exactly that shape, which the first
    version of this (a bare whitespace-then-`#`-to-end-of-line strip) cut the
    line at. `${VAR#pat}` is left alone by the whitespace requirement."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and i > 0 and line[i - 1].isspace():
            return line[:i]
    return line


def _code_lines(text: str) -> str:
    """A shell file with its comments removed — whole comment lines AND a
    trailing `# ...` on a code line — so a header that merely describes a
    sibling, or `noop  # replaces activities/x.sh`, does not count as
    consuming it."""
    return "\n".join(_strip_trailing_comment(l)
                     for l in text.splitlines() if not l.lstrip().startswith("#"))


def _rel(p: Path) -> str:
    return p.relative_to(_REPO).as_posix()


#: A map mentions every file in the repo, so accepting it as an invoker would
#: make every row pass trivially. Named, not inferred, so a reader can see the
#: hole was considered rather than missed.
NOT_AN_INVOKER = frozenset({"docs/file_structure.txt"})

#: The marker a baselined row must carry, so a reader of the table sees the same
#: fact the gate does rather than having to open this file.
UNREAD_MARKER = "NOBODY"


@dataclass(frozen=True)
class Surface:
    """One ruled-in producer population and how its consumers are named."""

    name: str
    root: Path
    #: How the population is read OFF DISK. Never a hand-kept list: a table
    #: checked against itself cannot see the member that was never added to it,
    #: which is the exact shape of the finding this phase is the remedy for.
    members: Callable[[Path], set]
    #: `True` when the surface accumulates items awaiting disposition, which is
    #: what makes the cadence-and-runner clause bind (requirement 2's ruling).
    accumulates: bool
    #: TABLE surface: the README whose three-column table names each member's
    #: consumer. `None` for a derived surface.
    readme: Path | None = None
    #: DERIVED surface: member name -> repo-relative paths of the files that
    #: consume it, found on disk by a predicate written for this surface's own
    #: invocation shape. `None` for a table surface. Exactly one of `readme`
    #: and `consumers` is set — asserted below.
    consumers: Callable[[str], list[str]] | None = None
    #: NOT A MEMBER AT ALL. name -> reason. Subtracted from the population, and
    #: a row for one is a FAILURE — the surface's own README says these are not
    #: rows, so permitting one would let the table contradict its own prose.
    exclusions: dict = field(default_factory=dict)
    #: A MEMBER, with a row, exempt from the CADENCE clause only. Distinct from
    #: the above and the distinction is load-bearing: `tracked/operations/` is a
    #: real store that must appear in its table — what cannot be checked is
    #: whether a person emptied it, not whether it exists.
    cadence_exempt: dict = field(default_factory=dict)
    #: Members with no consumer anywhere, FROZEN so the finding cannot grow
    #: silently. name -> reason. The ratchet runs BOTH ways: a new unread member
    #: fails, and a baselined member that gains a real consumer fails until its
    #: line is deleted here. Freezing rather than fixing is the phase's own
    #: boundary — inventing a consumer to make a check green is how a gate gets
    #: routed around. A table surface's README repeats the reason beside its
    #: row; a derived surface's reason lives here, because this IS its table.
    unread: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # THE TWO DICTS MEAN OPPOSITE THINGS and are merged in the exclusion
        # check, where a name in both would let one silently win. Nothing
        # populates both today; this is what keeps that true.
        both = set(self.exclusions) & set(self.cadence_exempt)
        assert not both, (
            f"{self.name}: {sorted(both)} is declared NOT A MEMBER and also a "
            f"member merely exempt from the cadence clause. Pick one."
        )
        assert (self.readme is None) != (self.consumers is None), (
            f"{self.name}: a surface names its consumers in a README table OR "
            f"finds them on disk — exactly one of `readme` / `consumers`."
        )


def _files(root: Path) -> set[str]:
    return {p.name for p in root.iterdir() if p.is_file() and not _is_transient(p)}


def _py(root: Path) -> set[str]:
    return {p.name for p in root.glob("*.py") if not _is_transient(p)}


def _md_stems(root: Path) -> set[str]:
    return {p.stem for p in root.glob("*.md") if not _is_transient(p)}


def _dirs(root: Path) -> set[str]:
    return {p.name for p in root.iterdir() if p.is_dir() and not _is_transient(p)}


# THE FOUR POPULATIONS OF `scripts/workflows/temporal/scripts/`, one per consumer
# shape, and they PARTITION the directory (asserted by `test_the_ENTRYPOINT_
# populations_PARTITION_the_directory`). Two are by name and two by a shebang:
# a `run_*.py` is a runner whatever its first line says, and among the rest a
# file that declares itself executable is a TOOL an operator runs, while one
# that does not is a LIBRARY something imports. Both directions of the split
# fail loudly — a tool that drops its shebang is judged as a library and must
# be imported; a library that gains one must be documented for the operator.

def _entrypoint_shims(root: Path) -> set[str]:
    return {p.name for p in root.glob("*.sh") if not _is_transient(p)}


def _entrypoint_runners(root: Path) -> set[str]:
    return {p.name for p in root.glob("run_*.py") if not _is_transient(p)}


def _has_shebang(p: Path) -> bool:
    with p.open("rb") as fh:
        return fh.read(2) == b"#!"


def _entrypoint_libraries(root: Path) -> set[str]:
    return {n for n in _py(root) - _entrypoint_runners(root)
            if not _has_shebang(root / n)}


def _entrypoint_tools(root: Path) -> set[str]:
    return {n for n in _py(root) - _entrypoint_runners(root)
            if _has_shebang(root / n)}


# --- derived-consumer predicates, one per invocation shape --------------------
#
# FOUR corpus functions below are `lru_cache`d and read the module-level
# `_REPO`. A control that repoints `_REPO` at a fixture must clear ALL of them,
# before and after — clearing only the one it happens to call leaves a fixture-
# derived result cached for the rest of the process the day a later edit adds a
# second call. The `repo_at` fixture is the one way a control repoints the module.
# (`_imported_stems` is keyed on an absolute path, so a fixture cannot collide
# with the tree; it is cleared with the rest so nothing has to reason about that.)

def _clear_corpus_caches() -> None:
    for fn in (_dispatch_corpus, _bash_corpus, _operator_docs, _fleet_python,
               _imported_stems, _module_ast):
        fn.cache_clear()


@pytest.fixture
def repo_at(monkeypatch):
    """Point the module at a fixture tree for one test. `monkeypatch` undoes
    the attribute on teardown but cannot undo a cache fill, so the caches are
    cleared here on entry AND on exit."""
    def _set(root: Path) -> None:
        _clear_corpus_caches()
        monkeypatch.setattr(sys.modules[__name__], "_REPO", root)
    yield _set
    _clear_corpus_caches()
#
# Each takes a member name and returns the repo-relative files that consume it.
# Each has a self-contained control below, because a predicate that is wrong
# in the permissive direction passes every member silently.

def _found_in(corpus: list[Path], member: str, *, text_of=_text) -> list[str]:
    return sorted(_rel(p) for p in corpus if _names(member, text_of(p)))


@lru_cache(maxsize=None)
def _dispatch_corpus() -> tuple[Path, ...]:
    """Every live surface that can dispatch an agent: command files, skills,
    rules, and the workflow tree (prompts, runners, the three bash workflows).
    NOT `config/agents/` itself — an agent naming another to say what it
    absorbed is a note, not a dispatch — and not any `tests/` directory."""
    roots = [_REPO / "config" / "commands", _REPO / "config" / "skills",
             _REPO / "config" / "rules", _REPO / "scripts" / "workflows"]
    return tuple(sorted(
        p for r in roots for p in r.rglob("*")
        if p.is_file() and p.suffix in {".md", ".sh", ".py"}
        and "tests" not in p.relative_to(_REPO).parts
        and not any(_is_transient(q) for q in p.relative_to(_REPO).parents)
    ))


def _dispatched_by(agent: str) -> list[str]:
    return _found_in(list(_dispatch_corpus()), agent)


def _declared_in_settings(hook: str) -> list[str]:
    """A hook is consumed by `settings.json` naming it in a hook command. The
    reverse direction — every configured command resolves to a file — is
    `testing/config-hooks/`'s; this is the direction that catches a hook
    written and never wired."""
    return _found_in([_REPO / "config" / "settings.json"], hook)


@lru_cache(maxsize=None)
def _bash_corpus() -> tuple[Path, ...]:
    w = _REPO / "scripts" / "workflows"
    return tuple(sorted(
        p for p in [*w.glob("*.sh"), *(w / "activities").glob("*.sh"),
                    *(w / "common").glob("*.sh")]
        if not _is_transient(p)
    ))


def _sourced_or_run_by(lib: str) -> list[str]:
    """A bash library is consumed by a workflow or a sibling library naming it
    on a NON-COMMENT line — `source "${SCRIPT_DIR}/activities/x.sh"` or
    `"${SCRIPT_DIR}/common/x.sh" key` both count; a header comment that
    describes it does not. The file itself is not its own consumer."""
    corpus = [p for p in _bash_corpus() if p.name != lib]
    return _found_in(corpus, lib, text_of=lambda p: _code_lines(_text(p)))


def _reads_from_services_dir(text: str, unit: str) -> bool:
    """`text` opens `unit` under `$SERVICES_DIR` — `$SERVICES_DIR/x`,
    `${SERVICES_DIR}/x` or the quote-closed `"$SERVICES_DIR"/x`. The last is
    not in `install.sh` today; it is the idiom a quoting edit would produce,
    and without it every service would flip to unread on that edit."""
    pat = rf"\$\{{?SERVICES_DIR\}}?\"?/{re.escape(unit)}(?![\w.-])"
    return re.search(pat, text) is not None


def _installed_from_repo(unit: str) -> list[str]:
    """A service file is consumed by `install.sh` reading it FROM THE REPO —
    a `$SERVICES_DIR/<name>` reference. A bare mention is not enough, and the
    difference is the finding this predicate exists for: `install.sh` names
    `gh-monitor.service` as the file it GENERATES under `$SYSTEMD_DIR`, and
    never opens the repo's copy of it."""
    text = _text(_REPO / "install.sh")
    return ["install.sh"] if _reads_from_services_dir(text, unit) else []


def _frameworks_in_run_all(text: str) -> set[str]:
    found = re.search(r"^FRAMEWORKS=\(([^)]*)\)", text, re.M)
    return set(found.group(1).split()) if found else set()


def _listed_as_framework(suite: str) -> list[str]:
    """A suite runner is consumed by `run-all.sh` listing its stem in
    `FRAMEWORKS=(...)` — the runner builds `$SUITES_DIR/$framework.sh` from
    that array, so the filename never appears literally and a name match
    would find nothing."""
    text = _text(_REPO / "testing" / "run-all.sh")
    stem = suite[:-3] if suite.endswith(".sh") else suite
    return ["testing/run-all.sh"] if stem in _frameworks_in_run_all(text) else []


@lru_cache(maxsize=None)
def _operator_docs() -> tuple[Path, ...]:
    """Where an operator learns a workflow exists: the rules, commands and
    skills the harness loads, and the planning repo's guide."""
    local = [p for r in ("commands", "skills", "rules")
             for p in (_REPO / "config" / r).glob("*.md")]
    guide = sorted((PLANNING_ROOT / "guide").glob("*.md"))
    return tuple(sorted(local) + guide)


def _documented_for_the_operator(script: str) -> list[str]:
    """A bash workflow's consumer is the OPERATOR, and the claim a check can
    make is that a document the operator reads names it. `merge-pr.py` was
    baselined for lacking exactly this."""
    docs = list(_operator_docs())
    out = []
    for p in docs:
        if _names(script, _text(p)):
            out.append(_rel(p) if p.is_relative_to(_REPO)
                       else p.relative_to(PLANNING_ROOT.parent).as_posix())
    return sorted(out)


def _execd_by_a_shim(runner: str) -> list[str]:
    """A runner is consumed by a shim beside it naming it on a NON-COMMENT
    line — `exec python3 "${SCRIPT_DIR}/run_build.py" "$@"`. The other
    direction, every shim has a runner beside it and a usage line naming
    itself, is `test_shim_usage_names_itself.py`'s; this is the reverse,
    which nothing held: a `run_*.py` that no shim execs."""
    root = _REPO / "scripts" / "workflows" / "temporal" / "scripts"
    shims = sorted(p for p in root.glob("*.sh") if not _is_transient(p))
    return _found_in(shims, runner, text_of=lambda p: _code_lines(_text(p)))


@lru_cache(maxsize=None)
def _fleet_python() -> tuple[Path, ...]:
    """Every non-test `.py` under `scripts/` — everywhere a stem import of a
    library beside the entrypoints could come from."""
    return tuple(sorted(
        p for p in (_REPO / "scripts").rglob("*.py")
        if "tests" not in p.relative_to(_REPO).parts
        and not _is_transient(p)
        and not any(_is_transient(q) for q in p.relative_to(_REPO).parents)
    ))


@lru_cache(maxsize=None)
def _imported_stems(p: Path) -> frozenset[str]:
    """The module names `p` imports, read off its AST: `import x` and
    `from x import y`, absolute only. A stem in a comment, a docstring or a
    string literal is not here — which is the mentions/invokes line, drawn
    structurally rather than by a regex that has to know what a comment is."""
    out: set[str] = set()
    for node in ast.walk(ast.parse(_text(p), filename=str(p))):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module)
    return frozenset(out)


def _imported_by_stem(lib: str) -> list[str]:
    """A library beside the entrypoints is consumed by another fleet module
    IMPORTING it by stem. `common/journal/config_digest.py` names
    `compare_run_config` twice, both in bug-history comments; under this
    predicate that is not a consumer, and it must not be."""
    stem = lib[:-3] if lib.endswith(".py") else lib
    return sorted(_rel(p) for p in _fleet_python()
                  if p.name != lib and stem in _imported_stems(p))


SURFACES = [
    Surface(
        name="scripts/helpers/measure/",
        root=_REPO / "scripts" / "helpers" / "measure",
        readme=_REPO / "scripts" / "helpers" / "measure" / "README.md",
        members=_py,
        accumulates=False,
        exclusions={
            "run_log.py": "declaration module — the one declaration of what the "
                          "run-log surface holds, loaded BY the tools rather "
                          "than run beside them",
        },
    ),
    Surface(
        name="scripts/helpers/",
        root=_REPO / "scripts" / "helpers",
        readme=_REPO / "scripts" / "helpers" / "README.md",
        members=_files,
        accumulates=False,
        exclusions={
            "README.md": "the table itself — the surface's declaration, not a "
                         "member of it. A check whose population includes the "
                         "text making the claim can be satisfied by its own "
                         "row, which is not a claim about anything",
        },
        # Reasons are in `scripts/helpers/README.md` § *The two tools nothing
        # invokes*, beside the rows that carry the marker.
        unread={
            "merge-pr.py": "only mention outside its own docstring is a "
                           "workflow-tree diagram in the planning repo's "
                           "`puma-temp-workflows.md`",
            "sibling_checkouts.py": "landed 2026-09-08 and was never wired to "
                                    "anything",
        },
    ),
    Surface(
        name="tracked/",
        root=PLANNING_ROOT / "tracked",
        readme=PLANNING_ROOT / "tracked" / "README.md",
        members=_dirs,
        accumulates=True,
        cadence_exempt={
            "operations": "human-in-the-loop only (Tracked Items §1.2) — its "
                          "consumer is a person and no check can assert that a "
                          "person read something",
        },
    ),
    # --- derived surfaces: the consumer is FOUND, and the gate is the table ---
    Surface(
        name="config/hooks/",
        root=_REPO / "config" / "hooks",
        members=_files,
        accumulates=False,
        consumers=_declared_in_settings,
    ),
    Surface(
        name="config/agents/",
        root=_REPO / "config" / "agents",
        members=_md_stems,
        accumulates=False,
        consumers=_dispatched_by,
    ),
    Surface(
        name="scripts/workflows/activities/",
        root=_REPO / "scripts" / "workflows" / "activities",
        members=_files,
        accumulates=False,
        consumers=_sourced_or_run_by,
        # THREE OF FOUR, found by this sweep on 2026-09-10. Each is a complete,
        # documented activity whose header says `source activities/<name>` and
        # which no surviving bash workflow sources. `run-claude.sh` is the one
        # all three workflows use. Frozen, not deleted: whether the three are
        # dead or are the library the next port needs is a ruling with its own
        # criteria, and this gate's job was to make the question visible.
        unread={
            "paper-currency.sh": "computes which research papers are past "
                                 "revalidation; the Python research family "
                                 "computes its own due set and nothing sources "
                                 "this",
            "require-environment.sh": "establishes the execution environment; "
                                      "the three bash workflows each do it "
                                      "inline and none sources this",
            "wait-for-ci.sh": "blocks until a PR's checks settle; nothing "
                              "sources it, and the Python fleet's CI wait lives "
                              "in its own activities",
        },
    ),
    Surface(
        name="scripts/workflows/common/",
        root=_REPO / "scripts" / "workflows" / "common",
        members=_files,
        accumulates=False,
        consumers=_sourced_or_run_by,
    ),
    Surface(
        name="scripts/services/",
        root=_REPO / "scripts" / "services",
        members=_files,
        accumulates=False,
        consumers=_installed_from_repo,
        # Found by this sweep on 2026-09-10. `install.sh` writes its own unit
        # file under `$SYSTEMD_DIR` with the path for THIS machine, and never
        # opens the repo's copy — which carries a hardcoded workstation path.
        # A second carrier of one fact, read by nobody. Frozen here; the remedy
        # (delete it, or have install.sh template from it) is a separate ruling.
        unread={
            "gh-monitor.service": "install.sh generates its own unit under "
                                  "$SYSTEMD_DIR and never reads this copy",
            # Baselined 2026-09-17, the day it landed. This service is installed
            # PER PLANNING REPOSITORY — its hook symlinked into that clone, its
            # section written into that repo's config — which is `sync-project`'s
            # job (SkyyNet's Project Scaffold and Sync), not install.sh's. On
            # disk today its runners are the merge hook beside it and the CI step
            # init-project.sh scaffolds; neither is the consumer this surface's
            # predicate names. The ratchet forces this line out the day
            # sync-project reads it from $SERVICES_DIR.
            "planning-ui.sh": "installed per planning repo by sync-project, "
                              "which does not exist yet; install.sh never reads it",
        },
    ),
    Surface(
        name="testing/suites/",
        root=_REPO / "testing" / "suites",
        members=_files,
        accumulates=False,
        consumers=_listed_as_framework,
    ),
    Surface(
        name="scripts/workflows/ (the bash workflows)",
        root=_REPO / "scripts" / "workflows",
        members=_files,
        accumulates=False,
        consumers=_documented_for_the_operator,
    ),
    # --- scripts/workflows/temporal/scripts/: FOUR surfaces on ONE root ---------
    # The directory holds four consumer shapes, and one predicate for all of
    # them would be their union — which passes a library nobody imports the
    # day a guide page mentions it. #181 ruled the directory OUT *"for being
    # unruled rather than for a property of its own"*; this is the ruling.
    # The four member predicates partition the directory, asserted by
    # `test_the_ENTRYPOINT_populations_PARTITION_the_directory`. Two claims
    # about the directory are held elsewhere and registered in `HELD_BY`: the
    # shim→runner pairing (`test_shim_usage_names_itself.py`) and the
    # dispatch-context echo every runner emits (`test_dispatch_context.py`).
    # The shims and the tools make the bash workflows' claim — an operator
    # document names them — and so, like that surface, SKIP on a clone with
    # no planning repo beside it; the runners and the libraries assert
    # everywhere.
    Surface(
        name="scripts/workflows/temporal/scripts/ (the shims)",
        root=_ENTRYPOINTS,
        members=_entrypoint_shims,
        accumulates=False,
        consumers=_documented_for_the_operator,
    ),
    Surface(
        name="scripts/workflows/temporal/scripts/ (the runners)",
        root=_ENTRYPOINTS,
        members=_entrypoint_runners,
        accumulates=False,
        consumers=_execd_by_a_shim,
    ),
    Surface(
        name="scripts/workflows/temporal/scripts/ (the libraries)",
        root=_ENTRYPOINTS,
        members=_entrypoint_libraries,
        accumulates=False,
        consumers=_imported_by_stem,
    ),
    Surface(
        name="scripts/workflows/temporal/scripts/ (the tools)",
        root=_ENTRYPOINTS,
        members=_entrypoint_tools,
        accumulates=False,
        consumers=_documented_for_the_operator,
        # TWO OF FOUR, found when this directory was ruled in on 2026-09-13.
        # Each is a working, tested reader of the journal that a human is
        # meant to run — and no document a human reads says so. Frozen, not
        # fixed: naming them in the guide is a planning-repo edit with its
        # own review, and this gate's job was to make the gap visible. The
        # ratchet opens the guide (`_consumer_file`), so the line leaves the
        # day the page names them.
        # EMPTY AS OF 2026-09-14, AND THAT IS THE RATCHET CLOSING. Two readers sat
        # here frozen — `compare_run_config.py` and `reconcile_harvest.py` — with
        # the note that "the line leaves the day the page names them". The
        # planning repo's `guide/operations.md` named both on 2026-09-13
        # (ed5f119), the gate went red for exactly the reason it was built to,
        # and the entries left. The dict stays so the next frozen reader has a
        # place to land.
        # EMPTY AGAIN AS OF 2026-09-16. `rebuild.py`, PMP Phase 4's operator
        # tool, sat here from 2026-09-15 with the same note the two before it
        # carried — "the line leaves the day the page names it". The planning
        # repo's `guide/operations.md` named it the next day, the gate went red
        # on main for exactly the reason it was built to, and the entry left.
        unread={},
    ),
]

_BY_NAME = {s.name: s for s in SURFACES}
#: The ruled-in roots the fleet walk must reach: the surfaces of THIS repo.
#: Keyed on "not under the planning repo" rather than on "under this repo",
#: because with no sibling checkout `PLANNING_ROOT` falls back to a path INSIDE
#: this tree — `tests/__no_planning_repo__/` — and the first form then demanded
#: the walk reach a directory that exists on no runner. That was red on the
#: GitHub runner and green on every machine with both repos, on the draft.
_ROOTS = {_rel(s.root) for s in SURFACES if not s.root.is_relative_to(PLANNING_ROOT)}


# --- the fleet: every directory is ruled ---------------------------------------

#: Directories ruled OUT of the gate, by repo-relative path, with the reason.
#: A ruling covers the directory's subtree unless a ruled-in surface sits below
#: it. Every key is asserted to exist on disk, so a ruling cannot outlive its
#: subject and silently start covering nothing.
RULED_OUT = {
    ".github": "read by GitHub Actions — an external system that loads the "
               "directory wholesale; no member can go unread and no check "
               "here can see the reader",
    "config/commands": "slash commands, invoked by a PERSON typing `/name`. The "
                       "human-only exclusion, for the reason `tracked/"
                       "operations/` is: no check can assert a person did "
                       "something",
    "config/managed-settings.d": "the managed floor (WD Phase 7) — placed "
        "ROOT-OWNED under /etc/claude-code/ by install.sh (`MANAGED_FLOOR`, "
        "copied, never symlinked) and read by the harness above every other "
        "tier. Not a symlink target, so `config`'s container reason does not "
        "reach it. HELD BY ANOTHER GATE: `test_the_managed_floor_is_wired.py` "
        "asserts its hook is declared, resolves to a placed executable, and "
        "sets no key that silences or halts",
    "config/rules": "loaded WHOLESALE by the harness into every session; there "
                    "is no per-member consumer to name and none can go unread",
    "config/skills": "loaded wholesale by the harness — every skill is listed "
                     "with its description in every session and invoked by "
                     "relevance, not by a named caller",
    "docs": "the repo map, one file, whose consumer is `scripts/helpers/"
            "file_structure_check.py` — HELD BY ANOTHER GATE: "
            "`test_file_structure_map_covers_the_tree.py`",
    "scripts/services/planning_ui": "code consumed by IMPORT — the `planning-ui` "
        "service's Python package, held by the import graph and its own suite "
        "(`scripts/services/planning_ui/tests`, listed in pytest.ini). Its "
        "`renderers/vendor/` is third-party JavaScript, declared by package, "
        "version and integrity in `renderers/vendor/manifest.json` and HELD BY "
        "ANOTHER GATE: `test_vendor_manifest.py` asserts every file is declared "
        "and every declaration's bytes match",
    "scripts/workflows/temporal/modules": "code consumed by IMPORT — the import "
        "graph, the suite and `code-reviewer`'s structure lens hold it. The "
        "prompt corpus under it is HELD BY ANOTHER GATE: "
        "`test_every_POOL_fragment_is_render_checked_by_some_consumer` and "
        "`test_prompt_completeness.py` require every shared fragment to be "
        "loaded by a consumer or excluded with a reason",
    "scripts/workflows/temporal/common": "code consumed by IMPORT — the shared "
        "library package beside `modules/` (the journal), held by the import "
        "graph, the suite and `code-reviewer`'s structure lens",
    "scripts/helpers/managed-tier-probe": "a HOST-RUN verification harness, "
        "invoked by a PERSON: `probe.sh` spends the operator's tokens against a "
        "container to observe the OS-level managed tier and is off every merge "
        "path — the human-only exclusion, for the reason `config/commands` is. "
        "`Dockerfile` and `marker-hook.sh` are read only by `probe.sh`; its "
        "README carries the measured result. Excluded from `scripts/helpers/`'s "
        "own table by name, beside `measure/` and `tests/`",
    "testing/config-hooks": "tests for `config/hooks/`, read by the runner — "
                            "placed here rather than beside the hooks for the "
                            "reason its README records",
    "testing/installer": "tests for `install.sh`, read by the runner — placed "
                         "here rather than at the repo root for the reason its "
                         "README records",
    "testing/scripts": "the mutation harness and the repo-wide guards no code "
                       "unit owns, this file among them — read by the runner "
                       "and the operator",
}

@dataclass(frozen=True)
class Container:
    """A directory that is a grouping, not a surface: why, and its OWN files."""

    reason: str
    #: The files sitting DIRECTLY in the container, name -> who reads it. DATA,
    #: not prose, because the walk below rules directories only and a file
    #: dropped straight into a container is invisible to it. Measured: `testing/
    #: check-policy.yaml` — a live producer by this gate's own definition, read
    #: by the build parent between refine and review-pr — was absent from
    #: `testing`'s prose account and nothing went red. `test_every_CONTAINER_
    #: accounts_for_its_own_DIRECT_files` holds this dict against `git ls-files`
    #: in both directions.
    files: dict = field(default_factory=dict)


#: Directories that are a grouping, not a surface: their own files are named
#: here with who reads them, and their SUBDIRECTORIES must each be ruled on
#: their own. A container does NOT cover its subtree — that is the difference
#: from `RULED_OUT`, and it is what keeps a new directory under `config/` from
#: inheriting a ruling nobody made about it. A ruled-in surface root is the
#: same: `scripts/helpers/` rules its files, and `measure/` and `tests/` under
#: it are ruled on their own.
CONTAINERS = {
    ".": Container(
        "the repo root — each file an entrypoint read by the harness, the "
        "operator, the installer, pytest or git, not a surface something else "
        "produces",
        {
            ".gitignore": "git",
            "CLAUDE.md": "the harness, at the start of every session",
            "LICENSE": "humans and GitHub — not a produced surface",
            "README.md": "the operator and GitHub",
            "config.template.yaml": "`install.sh`, which writes the gitignored "
                                    "`config.yaml` from it once; `config.yaml` is "
                                    "then read by `config-value.sh` and the fleet",
            "conftest.py": "pytest — the RLIMIT_AS guardrail",
            "install.sh": "the operator, on every machine that syncs",
            "pytest.ini": "pytest — pins rootdir so the guardrail loads",
        }),
    "config": Container(
        "the synced Claude Code configuration — symlinked into ~/.claude/ by "
        "install.sh and read by the harness every session",
        {
            "CLAUDE.md": "the harness, via the ~/.claude/CLAUDE.md symlink",
            "settings.json": "the harness, via the ~/.claude/settings.json "
                             "symlink",
        }),
    "scripts": Container("no files of its own"),
    "scripts/workflows/temporal": Container("no files of its own"),
    "testing": Container(
        "Tier 1 of the Testing Standard — the entry point the operator and CI "
        "run",
        {
            "README.md": "the operator — which half of the vendored standard "
                         "binds here and what the merge-path gate covers",
            "check-policy.yaml": "the build parent, between refine and "
                                 "review-pr — `scripts/workflows/temporal/"
                                 "modules/assistant/routing.py` `POLICY_PATH`",
            "run-all.sh": "the operator and CI — `.github/workflows/tests.yml`",
        }),
}

#: A directory by this NAME, anywhere, is tests: read by the runner, not by the
#: system. The Testing Standard's `<component>/tests/<category>/` convention is
#: what makes a name-keyed class rule safe here.
TESTS_DIR = "tests"

#: Surfaces this gate does NOT hold itself, with the test that DOES: claim ->
#: (test module, repo-relative; test function name). Every ruling above that
#: says "HELD BY ANOTHER GATE" is a cross-file coverage claim, and a holder that
#: was renamed or deleted leaves the claim covering nothing while it still
#: reads as if it did — the highest-severity shape a load-bearing sentence can
#: take, because it stops the next reader from checking. So each holder is
#: asserted to resolve, by file AND by function name, and a `test_*` name in a
#: ruling's prose must appear here (`test_every_HOLDER_named_in_a_ruling_is_
#: REGISTERED`). Registering a holder claims only that the named test EXISTS
#: and holds THAT surface — not that it is any good, which is the same weaker
#: claim this whole gate makes.
HELD_BY: dict[str, tuple[str, str]] = {
    "planning-ui's vendored JavaScript — every file declared, every declaration's bytes match": (
        "scripts/services/planning_ui/tests/unit/test_vendor_manifest.py",
        "test_the_committed_set_matches_its_manifest_and_is_under_budget"),
    "the managed floor's hook is declared, resolves to a placed executable, and the floor sets no silencing key": (
        "testing/config-hooks/tests/unit/test_the_managed_floor_is_wired.py",
        "test_every_floor_hook_RESOLVES_to_a_shipped_executable_under_the_managed_dir"),
    "the repo map, docs/file_structure.txt — population off git ls-files": (
        "testing/scripts/tests/unit/test_file_structure_map_covers_the_tree.py",
        "test_a_directory_the_map_ENUMERATES_is_enumerated_COMPLETELY"),
    "the shared prompt pool — every fragment render-checked by a consumer": (
        "scripts/workflows/temporal/tests/unit/"
        "test_promoted_fragments_render_for_every_consumer.py",
        "test_every_POOL_fragment_is_render_checked_by_some_consumer"),
    "the prompt corpus — every placeholder has a supplier": (
        "scripts/workflows/temporal/tests/unit/test_prompt_completeness.py",
        "test_every_placeholder_has_a_supplier"),
    "the shim<->runner pairs under temporal/scripts/": (
        "scripts/workflows/temporal/tests/unit/test_shim_usage_names_itself.py",
        "test_every_usage_line_invokes_this_shim"),
    # TWO claims, TWO holders. The entry above holds that a shim's usage line
    # names itself; the `assert runner.is_file()` that holds "a runner exists
    # beside every shim" lives in a DIFFERENT function of the same module, and
    # registering only the first left the second resolving to a test that
    # never asserted it — a rename of the real holder would have passed here.
    "a runner beside every shim under temporal/scripts/": (
        "scripts/workflows/temporal/tests/unit/test_shim_usage_names_itself.py",
        "test_every_usage_FLAG_is_one_the_runner_ACCEPTS"),
    "Phase 4's dispatch-context echo, at every entrypoint": (
        "scripts/workflows/temporal/tests/unit/test_dispatch_context.py",
        "test_every_entrypoint_BUILDS_a_context_and_SAYS_IT"),
    "the run log's WRITERS equal its declaration (its readers are measure/)": (
        "scripts/helpers/tests/unit/test_run_log.py",
        "test_the_declared_member_set_is_EXACTLY_what_the_fleet_writes"),
}


def _unresolved_holders(held_by: dict, *, repo: Path) -> list[str]:
    """Registry entries whose module is missing or whose function is not
    defined in it. The failure a renamed holder produces, made loud."""
    out = []
    for claim, (module, func) in held_by.items():
        path = repo / module
        if not path.is_file():
            out.append(f"{claim}: {module} is not on disk")
        elif not _defines_function(path, func):
            out.append(f"{claim}: {module} defines no `{func}`")
    return out


_TEST_NAME_IN_PROSE = re.compile(r"`(test_[A-Za-z0-9_]+(?:\.py)?)`")


def _unregistered_holders(prose: list[str], held_by: dict) -> list[str]:
    """Backticked `test_*` names in ruling prose that the registry does not
    carry, by module basename or by function name. A holder named only in
    a sentence is the unasserted claim the registry exists to replace."""
    known = set()
    for module, func in held_by.values():
        known.add(Path(module).name)
        known.add(func)
    return sorted({name for text in prose for name in _TEST_NAME_IN_PROSE.findall(text)
                   if name not in known})


def test_every_HOLDER_of_a_surface_this_gate_defers_to_RESOLVES() -> None:
    """A "held by another gate" ruling whose holder is gone covers nothing."""
    assert HELD_BY, "the registry is empty — every deferral above is unbacked"
    assert _unresolved_holders(HELD_BY, repo=_REPO) == []


def test_every_HOLDER_named_in_a_ruling_is_REGISTERED() -> None:
    """The RULINGS, not the module docstring: the docstring cites a deleted
    module as history (`test_prose_NAMES_a_symbol_that_RESOLVES.py` holds
    that citation by site), and a ruling is where a holder is load-bearing."""
    prose = [*RULED_OUT.values(),
             *(c.reason for c in CONTAINERS.values()),
             *(r for c in CONTAINERS.values() for r in c.files.values())]
    assert _unregistered_holders(prose, HELD_BY) == [], (
        "a ruling names a holder by prose alone — add it to HELD_BY so the "
        "claim is asserted rather than read"
    )


def test_the_HOLDER_checks_fire_on_a_missing_module_a_missing_function_and_prose(tmp_path: Path) -> None:
    """Self-contained control: one real holder, one module that is not there,
    one module that is there without the function, and one name in prose the
    registry does not carry."""
    (tmp_path / "t_ok.py").write_text("def test_ok() -> None:\n    pass\n")
    (tmp_path / "t_nofn.py").write_text("def test_other() -> None:\n    pass\n")
    reg = {"ok": ("t_ok.py", "test_ok"),
           "gone": ("t_gone.py", "test_ok"),
           "nofn": ("t_nofn.py", "test_ok")}
    bad = _unresolved_holders(reg, repo=tmp_path)
    assert [b.split(":")[0] for b in bad] == ["gone", "nofn"], bad
    assert _unregistered_holders(["held by `test_ok`, see `t_ok.py`"], reg) == []
    assert _unregistered_holders(["held by `test_ok` and `test_vanished`"], reg) == ["test_vanished"], \
        "a holder named in prose and absent from the registry was not reported"


# --- THE RUNTIME-RECORD CLASS -------------------------------------------------
#
# A record a run writes for a LATER run: a journal bag's files and tags, the
# typed exit record, the run log's member events. Written under the configured
# journal root or the untracked log directory, so the `git ls-files` walk that
# rules every other surface structurally cannot reach them — a population that
# has to be found somewhere other than the tree. It is found in the DECLARATIONS:
# every on-disk record the journal package writes is named once by a top-level
# constant `_RECORD_CONSTANT` matches, and every run-log member is a string in
# `MEMBER_EVENT_TYPES`. Those two populations are read off the modules, not
# listed here (`_journal_record_symbols`, `_run_log_members`), and each member
# must be a `RUNTIME_RECORDS` entry or an `UNREAD_RUNTIME_RECORDS` line. Two
# members are of neither family and are registered by hand with that said:
# the exit record (one schema in one module) and the config-digest tag (a
# label INSIDE `bag-info.txt`, read across two bags — the file is derived,
# the tag is not).
#
# THE READ SIDE ONLY. The run log's write side is `HELD_BY` (its writers equal
# its declaration) and is not re-asserted here.
#
# WHAT "RESOLVES" MEANS FOR A READER, because "the reader exists" is the weakest
# claim on offer: the module is on disk, the entry function is defined in it,
# and the module names the record's declared symbol AS A CODE TOKEN — a Name, an
# attribute, or a string passed as a value — never in a comment or docstring
# (`_code_tokens`). Then every `via` hop — from the operator-facing tool, the
# parent branch, or the fleet module that opens the record next — imports the
# next by stem, so the name a person is told to run actually reaches the
# function that opens the record. That the FIRST hop is itself alive is the
# import graph's to hold, as the module docstring rules for every module.


@dataclass(frozen=True)
class RuntimeRecord:
    """One off-tree record and the reader that opens it."""

    #: The module that declares the record's on-disk name (or its schema),
    #: repo-relative, and the symbol it is asserted to declare: a top-level
    #: constant, a string member of one, or a function name.
    declared_in: str
    symbol: str
    #: The module that OPENS the record and the function in it that does. The
    #: module must name `symbol` as a code token.
    reader: str
    entry: str
    #: How the reader is REACHED: the operator tool or parent branch first,
    #: each hop importing the next by stem, the last importing `reader`.
    #: Empty when the reader is itself the operator-facing tool.
    via: tuple[str, ...] = ()


_JOURNAL = "scripts/workflows/temporal/common/journal"
_TOOLS = "scripts/workflows/temporal/scripts"
_RUN_LOG = "scripts/helpers/measure/run_log.py"

RUNTIME_RECORDS: dict[str, RuntimeRecord] = {
    # --- a sealed bag, as `validate_bag.py` reads it -------------------------
    "a bag's payload directory — every file hashed": RuntimeRecord(
        f"{_JOURNAL}/bag.py", "PAYLOAD_DIR",
        f"{_JOURNAL}/validate.py", "validate_bag",
        via=(f"{_TOOLS}/validate_bag.py",)),
    "a bag's manifest — bytes match their hashes": RuntimeRecord(
        f"{_JOURNAL}/bag.py", "MANIFEST_FILE",
        f"{_JOURNAL}/validate.py", "validate_bag",
        via=(f"{_TOOLS}/validate_bag.py",)),
    "a bag's bagit.txt — the RFC 8493 declaration": RuntimeRecord(
        f"{_JOURNAL}/bag.py", "BAGIT_FILE",
        f"{_JOURNAL}/validate.py", "validate_bag",
        via=(f"{_TOOLS}/validate_bag.py",)),
    "a bag's tags — schema version and lifecycle": RuntimeRecord(
        f"{_JOURNAL}/bag.py", "BAG_INFO_FILE",
        f"{_JOURNAL}/validate.py", "validate_bag",
        via=(f"{_TOOLS}/validate_bag.py",)),
    # --- one tag, read across TWO bags by its own tool ----------------------
    "the config digest tag, compared across two bags": RuntimeRecord(
        f"{_JOURNAL}/config_digest.py", "LABEL_CONFIG_DIGEST",
        f"{_TOOLS}/compare_run_config.py", "_read_digest"),
    # --- citations and the bytes they were made from, as `verify_citations.py`
    #     reads them: the tool imports `verify`, which imports both readers ---
    "citations recorded in a bag": RuntimeRecord(
        f"{_JOURNAL}/citations.py", "CITATIONS_FILE",
        f"{_JOURNAL}/citations.py", "read_citations",
        via=(f"{_TOOLS}/verify_citations.py", f"{_JOURNAL}/verify.py")),
    "the content store a citation's bytes are kept in": RuntimeRecord(
        f"{_JOURNAL}/content_store.py", "CONTENT_STORE_DIR",
        f"{_JOURNAL}/content_store.py", "load_object",
        via=(f"{_TOOLS}/verify_citations.py", f"{_JOURNAL}/verify.py")),
    # --- the harvest index, as `reconcile_harvest.py` reads it --------------
    "a harvest's index — which comment landed on which event": RuntimeRecord(
        f"{_JOURNAL}/harvest.py", "HARVEST_INDEX_FILE",
        f"{_JOURNAL}/harvest.py", "read_harvest_indexes",
        via=(f"{_TOOLS}/reconcile_harvest.py",)),
    # --- a bag's event stream, as PMP Phase 4's replay reads it ------------
    #     Every writer's `events.jsonl` under the payload, decoded and deduped
    #     on identity, then applied from the starting snapshot forward. Reached
    #     by the operator through `rebuild.py check` and by the suite on both
    #     arms of requirement 4. The file name and the walk that finds every
    #     writer's copy are `bag.py`'s, shared with the Self Improvement
    #     reader so the two cannot read different streams.
    "a bag's event stream, events.jsonl": RuntimeRecord(
        f"{_JOURNAL}/bag.py", "EVENTS_FILE",
        f"{_JOURNAL}/bag.py", "events_files",
        via=(f"{_TOOLS}/rebuild.py",
             "scripts/workflows/temporal/modules/assistant/tracked/rebuild.py")),
    # --- the starting snapshot, as the same replay starts from it ----------
    "the starting snapshot at the journal root": RuntimeRecord(
        f"{_JOURNAL}/snapshot.py", "SNAPSHOT_NAME_RE",
        f"{_JOURNAL}/snapshot.py", "latest_snapshot",
        via=(f"{_TOOLS}/rebuild.py",
             "scripts/workflows/temporal/modules/assistant/tracked/rebuild.py")),
    # --- the machine's persisted identity, read by every LATER bag open -----
    "the edge-id file under the journal root": RuntimeRecord(
        f"{_JOURNAL}/edge_id.py", "EDGE_ID_FILE",
        f"{_JOURNAL}/edge_id.py", "resolve_edge_id",
        via=(f"{_JOURNAL}/emit.py",)),
    # --- the typed exit record: the child's stratum, routed by the parent ---
    "the typed exit record — the parent branch routes on it": RuntimeRecord(
        "scripts/workflows/temporal/modules/assistant/review_pr/exit_record.py",
        "CHILD_SCHEMA",
        "scripts/workflows/temporal/modules/assistant/review_pr/exit_record.py",
        "route",
        via=("scripts/workflows/temporal/modules/assistant/review_pr/"
             "review_pr_workflow.py",)),
    # --- the run log's three members, one replay tool each ------------------
    "the run log's parent_route events": RuntimeRecord(
        _RUN_LOG, "parent_route",
        "scripts/helpers/measure/replay_parent_route.py", "rows"),
    "the run log's run_resources events": RuntimeRecord(
        _RUN_LOG, "run_resources",
        "scripts/helpers/measure/replay_run_resources.py", "main"),
    "the run log's convergence events": RuntimeRecord(
        _RUN_LOG, "convergence",
        "scripts/helpers/measure/replay_convergence_events.py", "rows"),
}


@dataclass(frozen=True)
class UnreadRecord:
    """A declared record NO committed reader opens — frozen, with the ratchet."""

    declared_in: str
    symbol: str
    #: The function the declaring module publishes for READING the record. The
    #: ratchet: a fleet module outside `declared_in` naming it as a code token
    #: is a reader, and this line must then move to `RUNTIME_RECORDS`.
    accessor: str
    reason: str


UNREAD_RUNTIME_RECORDS: dict[str, UnreadRecord] = {
    # EMPTY AS OF 2026-09-15, AND THAT IS THE RATCHET CLOSING. One record sat
    # here frozen from the day the class was ruled (2026-09-14): a bag's event
    # stream, `events.jsonl`, decoded by tests only. The note said its reader
    # was SCHEDULED — PMP Phase 4's replay — and that the line would leave the
    # day that replay landed as a FLEET module. It landed as
    # `modules/assistant/tracked/rebuild.py` (`read_bags`, reached from
    # `scripts/rebuild.py`), the gate went red for exactly the reason it was
    # built to, and the record moved to `RUNTIME_RECORDS`. The dict stays so
    # the next unread record has a place to land.
}


@lru_cache(maxsize=None)
def _module_ast(p: Path) -> ast.Module:
    """Cached like `_imported_stems`, and for the same reason: the unread
    ratchet tokenises EVERY fleet module per baselined record."""
    return ast.parse(_text(p), filename=str(p))


def _all_targets(node: ast.stmt) -> list[str]:
    """The plain names a top-level statement assigns, in every spelling the
    fleet uses for a constant: `X = `, `X: T = ` and `X += `. The journal
    package declares five constants annotated today, so a helper that reads
    only the bare form is one refactor from missing a record."""
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        targets = [node.target]
    else:
        return []
    return [t.id for t in targets if isinstance(t, ast.Name)]


def _declared_tokens(p: Path) -> frozenset[str]:
    """What a module DECLARES at top level: the names it assigns, the string
    members of what it assigns them (so `"parent_route"` inside
    `MEMBER_EVENT_TYPES = frozenset({...})` is declared), and the functions
    and classes it defines. Nothing nested, nothing imported."""
    out: set[str] = set()
    for node in _module_ast(p).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            out.update(_all_targets(node))
            if node.value is not None:
                out.update(n.value for n in ast.walk(node.value)
                           if isinstance(n, ast.Constant) and isinstance(n.value, str))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
    return frozenset(out)


def _code_tokens(p: Path) -> frozenset[str]:
    """The symbols a module USES: every `Name` and attribute it LOADS, and
    every string constant that is a VALUE — an argument, an operand, a key —
    rather than a bare statement (a docstring is a bare `Expr` holding a
    string). Comments are not in the AST at all. A `Store` is a definition,
    not a use: five entries declare a record in the very module that reads it,
    and the declaration's own target would otherwise satisfy "names it in
    code" for every one of them whatever the entry function does. An import
    alias is NOT here, and nor is a string inside `__all__` (assigned,
    annotated or augmented — `_all_targets`): a module that re-exports a
    reader has not read anything, and `journal/__init__.py` re-exports every
    accessor in the package both ways — the first run of the unread ratchet
    named it as the event stream's reader on the strength of its `__all__`."""
    tree = _module_ast(p)
    not_a_use: set[int] = set()
    for node in tree.body:
        if "__all__" in _all_targets(node) and node.value is not None:
            not_a_use.update(id(n) for n in ast.walk(node.value))
    out: set[str] = set()
    # `ast.walk` is breadth-first, so a docstring's `Expr` is seen before the
    # `Constant` it holds — which is what lets the skip be recorded in place.
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            out.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            out.add(node.attr)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            not_a_use.add(id(node.value))
        elif (isinstance(node, ast.Constant) and isinstance(node.value, str)
              and id(node) not in not_a_use):
            out.add(node.value)
    return frozenset(out)


def _imports_stem(p: Path, stem: str) -> bool:
    """`p` imports a module whose last segment is `stem`, absolute or relative:
    `import a.b.stem`, `from a.b import stem`, `from .stem import x`,
    `from . import stem`. Wider than `_imported_stems` on purpose — the readers
    are package-internal and reach each other by relative import."""
    for node in ast.walk(_module_ast(p)):
        if isinstance(node, ast.Import):
            if any(a.name.rsplit(".", 1)[-1] == stem for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.rsplit(".", 1)[-1] == stem:
                return True
            if any(a.name == stem for a in node.names):
                return True
    return False


def _defines_function(p: Path, name: str) -> bool:
    return re.search(rf"^def {re.escape(name)}\(", _text(p), re.M) is not None


def _unresolved_records(records: dict, *, repo: Path) -> list[str]:
    """Every way a `RuntimeRecord` can fail to resolve, as `claim: defect`.
    Three parts — declaration, reader, reach — and an entry stops at the
    first part that fails, so a mis-typed symbol reports once at its
    declaration rather than again at every reader that also lacks it."""
    out = []
    for claim, r in records.items():
        declared = repo / r.declared_in
        reader = repo / r.reader
        if not declared.is_file():
            out.append(f"{claim}: {r.declared_in} is not on disk")
            continue
        if r.symbol not in _declared_tokens(declared):
            out.append(f"{claim}: {r.declared_in} declares no `{r.symbol}`")
            continue
        if not reader.is_file():
            out.append(f"{claim}: reader {r.reader} is not on disk")
            continue
        if not _defines_function(reader, r.entry):
            out.append(f"{claim}: reader {r.reader} defines no `{r.entry}`")
            continue
        if r.symbol not in _code_tokens(reader):
            out.append(f"{claim}: reader {r.reader} never names `{r.symbol}` in code")
            continue
        chain = [*r.via, r.reader]
        for hop, nxt in zip(chain, chain[1:]):
            if not (repo / hop).is_file():
                out.append(f"{claim}: via {hop} is not on disk")
                break
            if not _imports_stem(repo / hop, Path(nxt).stem):
                out.append(f"{claim}: via {hop} does not import `{Path(nxt).stem}`")
                break
    return out


def _regained_records(unread: dict, *, repo: Path, fleet: list[Path]) -> list[str]:
    """An `UnreadRecord` whose declaration is gone, or whose accessor a fleet
    module outside the declaring one now names in code — the ratchet."""
    out = []
    for claim, u in unread.items():
        declared = repo / u.declared_in
        if not declared.is_file():
            out.append(f"{claim}: {u.declared_in} is not on disk")
            continue
        missing = {u.symbol, u.accessor} - _declared_tokens(declared)
        if missing:
            out.append(f"{claim}: {u.declared_in} declares no {sorted(missing)}")
            continue
        readers = sorted(p.relative_to(repo).as_posix() for p in fleet
                         if p != declared and u.accessor in _code_tokens(p))
        if readers:
            out.append(f"{claim}: `{u.accessor}` is now named by {readers} — "
                       f"register the reader and delete this line")
    return out


_RECORD_CONSTANT = re.compile(r"_(FILE|DIR)$")


def _journal_record_symbols(journal: Path, *, repo: Path) -> set[tuple[str, str]]:
    """The journal package's on-disk records, read off its declarations: every
    top-level constant `_RECORD_CONSTANT` matches, in every module, in either
    spelling (`_all_targets`). Keyed (repo-relative module, symbol) — the
    same key a `RuntimeRecord.declared_in` carries, so a hand-registered
    entry that names a same-basename module elsewhere cannot stand in for
    the journal's; `_ruled_records` keys the same way."""
    out = set()
    for p in sorted(journal.glob("*.py")):
        if _is_transient(p):
            continue
        rel = p.relative_to(repo).as_posix()
        for node in _module_ast(p).body:
            out.update((rel, name) for name in _all_targets(node)
                       if _RECORD_CONSTANT.search(name))
    return out


def _run_log_members(run_log: Path) -> set[str]:
    """`MEMBER_EVENT_TYPES`, loaded the way the replay tools load it — by path,
    no package. Reading the declaration rather than re-typing it is what makes
    a fourth member fail HERE until it has a reader."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_run_log_for_the_gate", run_log)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.MEMBER_EVENT_TYPES)


def _ruled_records(records: dict, unread: dict) -> set[tuple[str, str]]:
    return ({(r.declared_in, r.symbol) for r in records.values()}
            | {(u.declared_in, u.symbol) for u in unread.values()})


def test_every_RUNTIME_RECORD_names_a_reader_that_RESOLVES_and_READS_it() -> None:
    """The read obligation for the class: each entry's declaration, reader and
    reach all resolve on disk. A renamed reader, a renamed constant, or a tool
    that stopped importing the reader it fronts is reported by name."""
    assert RUNTIME_RECORDS, "the registry is empty — the class is unruled"
    assert _unresolved_records(RUNTIME_RECORDS, repo=_REPO) == []


def test_every_DECLARED_runtime_record_is_RULED_read_or_unread() -> None:
    """The population, off the declarations: every journal file-or-directory
    constant and every run-log member is registered or baselined. A record the
    fleet starts writing fails here until somebody names who reads it."""
    journal = _journal_record_symbols(_REPO / _JOURNAL, repo=_REPO)
    members = {(_RUN_LOG, m) for m in _run_log_members(_REPO / _RUN_LOG)}
    assert len(journal) >= 5 and len(members) >= 3, (journal, members)
    ruled = _ruled_records(RUNTIME_RECORDS, UNREAD_RUNTIME_RECORDS)
    assert (journal | members) - ruled == set(), (
        "a declared record has no reader named and no unread line — rule it"
    )


# `test_an_UNREAD_runtime_record_is_still_declared_and_still_UNREAD` stood here
# until 2026-09-15 and left on its own instruction ("nothing is baselined —
# delete this test") when the one baselined record gained its reader. Its
# predicate, `_regained_records`, stays — its control below still exercises it —
# so the next baselined record re-adds the two-line test rather than the helper.


# The repo map's annotation of this gate NARRATES its two unread figures, and a
# number in prose is held by nothing: the map said "Eight" for the fortnight
# after two of them closed on main, and the pass that ruled the runtime-record
# class found it. So the sentence is keyed on by SHAPE and its digits compared
# with the registries — the next drift goes red here instead of waiting for a
# review pass to notice. Digits, not number-words, so the shape has one spelling.
_MAP_UNREAD_RE = re.compile(r"\b(\d+) unread producers and (\d+) unread runtime records?\b")


def _map_annotation(map_text: str, leaf: str) -> str:
    """The map's leaf line naming `leaf` plus its continuation lines — every
    line up to the next leaf — joined. Empty when the map has no such entry."""
    lines = map_text.splitlines()
    for i, line in enumerate(lines):
        m = _MAP_LEAF.match(line)
        if not m or m.group(2) != leaf:
            continue
        block = [line]
        for nxt in lines[i + 1:]:
            if _MAP_LEAF.match(nxt):
                break
            block.append(nxt)
        return "\n".join(block)
    return ""


def _map_unread_counts(annotation: str) -> tuple[int, int] | None:
    """The (producers, runtime records) figures an annotation states, or None
    when it states none in the one spelling `_MAP_UNREAD_RE` reads."""
    m = _MAP_UNREAD_RE.search(annotation)
    return (int(m.group(1)), int(m.group(2))) if m else None


def test_the_REPO_MAP_states_the_UNREAD_figures_this_gate_holds() -> None:
    """`docs/file_structure.txt`'s sentence about this gate's baselines must
    equal the registries. Stating none is also a failure: the annotation is
    where a reader learns the ratchet exists, and a number that quietly
    vanished is the same silence as one that quietly went stale."""
    annotation = _map_annotation(_MAP.read_text(), Path(__file__).name)
    assert annotation, f"{_MAP.name} has no entry for {Path(__file__).name}"
    stated = _map_unread_counts(annotation)
    assert stated is not None, (
        "the map's annotation no longer states the unread figures in the "
        f"shape {_MAP_UNREAD_RE.pattern!r} — restate them, or delete this test")
    held = (sum(len(s.unread) for s in SURFACES), len(UNREAD_RUNTIME_RECORDS))
    assert stated == held, (
        f"{_MAP.name} says {stated} (producers, runtime records); the gate "
        f"holds {held} — correct the annotation")


def test_the_MAP_FIGURE_check_reads_the_sentence_and_only_that_sentence() -> None:
    """Self-contained control: the entry's own continuation lines are read,
    the next entry's are not, a missing entry is empty, and an annotation
    without the sentence — or with it in number-words — states nothing."""
    text = (
        "├── x.py                  # rules things. Cadence clause binds only\n"
        "│                         #   accumulating surfaces. 6 unread producers and 1 unread runtime record\n"
        "│                         #   are baselined.\n"
        "├── y.py                  # says Six unread producers and one unread runtime record\n"
        "└── z.py                  # 9 unread producers and 2 unread runtime records\n")
    assert _map_unread_counts(_map_annotation(text, "x.py")) == (6, 1)
    assert _map_unread_counts(_map_annotation(text, "y.py")) is None
    assert _map_unread_counts(_map_annotation(text, "z.py")) == (9, 2)
    assert "z.py" not in _map_annotation(text, "y.py")
    assert _map_annotation(text, "w.py") == ""


def _runtime_fixture(root: Path) -> None:
    """A declaring module, a reader that names its symbol in CODE, a tool that
    imports the reader — the shape every real entry has, in miniature. The
    declaring module reads ONE of its own records (`open_it` loads `THE_FILE`)
    and only stores the other (`MEMBERS`), which is the self-referential
    shape five live entries take."""
    (root / "decl.py").write_text(
        'THE_FILE = "the.txt"\nMEMBERS = frozenset({"alpha"})\n'
        "def open_it(p):\n    return p / THE_FILE\n")
    (root / "reader.py").write_text(
        '"""Mentions MEMBERS in the docstring only."""\n'
        "from decl import THE_FILE, MEMBERS  # and alpha, in a comment\n"
        "def read(p):\n    return (p / THE_FILE).read_text()\n"
        "def asks(log):\n    return events(log, 'alpha')\n")
    (root / "tool.py").write_text("import reader\n")
    (root / "mentions_only.py").write_text(
        '"""`open_it` is only mentioned here."""\nfrom decl import open_it\n'
        '__all__ = ["open_it"]\n')
    # The other two spellings of a re-export, which the first cut of
    # `_code_tokens` did not exclude: annotated, and augmented.
    (root / "reexports.py").write_text(
        'from decl import open_it\n__all__: list[str] = []\n__all__ += ["open_it"]\n')
    (root / "calls_it.py").write_text("import decl\ndecl.open_it(None)\n")


def test_the_RUNTIME_RECORD_check_fires_ONCE_on_each_of_its_SEVEN_defects(tmp_path: Path) -> None:
    """Self-contained control. One entry per way to be wrong, each reported
    once by its claim — including an entry wrong in two ways at once, which
    reports the first — and the three good entries are not: a constant read
    across files, a string member read by a call argument, and a module that
    declares AND loads its own record."""
    _runtime_fixture(tmp_path)
    reg = {
        "ok": RuntimeRecord("decl.py", "THE_FILE", "reader.py", "read", via=("tool.py",)),
        "ok-string": RuntimeRecord("decl.py", "alpha", "reader.py", "asks"),
        "ok-self": RuntimeRecord("decl.py", "THE_FILE", "decl.py", "open_it"),
        "decl-gone": RuntimeRecord("gone.py", "THE_FILE", "reader.py", "read"),
        "symbol-gone": RuntimeRecord("decl.py", "OTHER_FILE", "reader.py", "read"),
        "reader-gone": RuntimeRecord("decl.py", "THE_FILE", "gone.py", "read"),
        "entry-gone": RuntimeRecord("decl.py", "THE_FILE", "reader.py", "write"),
        # THE DISCRIMINATOR: on disk, entry defined, symbol in a docstring and
        # an import alias — and that is not reading it.
        "prose-only": RuntimeRecord("decl.py", "MEMBERS", "reader.py", "read"),
        # The self-referential discriminator: the module DECLARES the symbol,
        # so its own `Store` is in the AST, and nothing in it loads it.
        "self-store-only": RuntimeRecord("decl.py", "MEMBERS", "decl.py", "open_it"),
        # Wrong twice — no entry AND no symbol — reported once, at the entry.
        "entry-and-symbol-gone": RuntimeRecord("decl.py", "MEMBERS", "reader.py", "write"),
        "via-gone": RuntimeRecord("decl.py", "THE_FILE", "reader.py", "read", via=("nope.py",)),
        "via-unlinked": RuntimeRecord("decl.py", "THE_FILE", "reader.py", "read", via=("decl.py",)),
    }
    bad = _unresolved_records(reg, repo=tmp_path)
    assert [b.split(":")[0] for b in bad] == [
        "decl-gone", "symbol-gone", "reader-gone", "entry-gone", "prose-only",
        "self-store-only", "entry-and-symbol-gone", "via-gone", "via-unlinked"], bad
    assert "never names `MEMBERS` in code" in next(b for b in bad if b.startswith("prose-only"))
    assert "never names `MEMBERS` in code" in next(b for b in bad if b.startswith("self-store-only"))
    assert "defines no `write`" in next(b for b in bad if b.startswith("entry-and-symbol-gone"))


def test_the_UNREAD_RATCHET_fires_on_a_CALL_and_not_on_a_MENTION(tmp_path: Path) -> None:
    """A fleet module that re-exports (in any of the three spellings of
    `__all__`) or documents the accessor is not a reader; one that calls it
    is, and the line must then leave."""
    _runtime_fixture(tmp_path)
    unread = {"still": UnreadRecord("decl.py", "THE_FILE", "open_it", "why"),
              "gone": UnreadRecord("nope.py", "THE_FILE", "open_it", "why"),
              "undeclared": UnreadRecord("decl.py", "THE_FILE", "read_it", "why")}
    quiet = [tmp_path / "decl.py", tmp_path / "mentions_only.py", tmp_path / "reexports.py"]
    assert _regained_records(unread, repo=tmp_path, fleet=quiet) == [
        "gone: nope.py is not on disk",
        "undeclared: decl.py declares no ['read_it']"]
    loud = _regained_records(unread, repo=tmp_path, fleet=[*quiet, tmp_path / "calls_it.py"])
    assert any(b.startswith("still:") and "calls_it.py" in b for b in loud), loud


def test_the_POPULATION_reads_the_declarations_and_reports_an_UNRULED_one(tmp_path: Path) -> None:
    """`_journal_record_symbols` finds a file constant and a directory
    constant — bare or annotated — and nothing else, keyed by the module's
    path under the repo; `_run_log_members` reads the frozenset; a member of
    either with no entry is the set difference the population test asserts
    empty."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text(
        'A_FILE = "a"\nA_DIR: str = "d"\nNOT_ONE = "x"\nFILE_NAME = "n"\n')
    (tmp_path / "run_log.py").write_text('MEMBER_EVENT_TYPES = frozenset({"one", "two"})\n')
    assert _journal_record_symbols(tmp_path / "pkg", repo=tmp_path) == {
        ("pkg/a.py", "A_FILE"), ("pkg/a.py", "A_DIR")}
    assert _run_log_members(tmp_path / "run_log.py") == {"one", "two"}
    ruled = _ruled_records(
        {"x": RuntimeRecord("pkg/a.py", "A_FILE", "r.py", "f")},
        {"y": UnreadRecord("pkg/a.py", "A_DIR", "g", "why")})
    assert ruled == {("pkg/a.py", "A_FILE"), ("pkg/a.py", "A_DIR")}
    assert {("pkg/a.py", "A_FILE"), ("pkg/a.py", "A_DIR"), ("run_log.py", "one")} - ruled == {("run_log.py", "one")}
    # A same-basename module elsewhere is NOT the journal's: the key is the path.
    assert _ruled_records({"z": RuntimeRecord("other/a.py", "A_FILE", "r.py", "f")}, {}) \
        != {("pkg/a.py", "A_FILE")}


def _tracked_files() -> set[str]:
    """Every tracked or untracked-unignored file, repo-relative. Read from git
    rather than the disk so that ignored trees — `testing/logs/`, bytecode
    caches, `.claude/worktrees/` — are not members, on a workstation or on
    the sibling-less CI runner alike."""
    out = subprocess.run(
        ["git", "-C", str(_REPO), "ls-files", "-co", "--exclude-standard", "-z"],
        check=True, capture_output=True, text=True,
    ).stdout
    return {f for f in out.split("\0") if f}


def _tracked_dirs() -> set[str]:
    """Every directory holding a tracked or untracked-unignored file, plus its
    ancestors — the same population `_tracked_files` reads, folded to dirs."""
    dirs = {"."}
    for f in _tracked_files():
        parts = Path(f).parts[:-1]
        for i in range(1, len(parts) + 1):
            dirs.add("/".join(parts[:i]))
    return dirs


def _ruling_for(rel: str, *, roots: set, out: dict, containers: dict) -> str | None:
    """How `rel` is ruled, or `None` if nothing rules it.

    Order matters and is deliberate: a ruled-in surface wins over an ancestor's
    OUT ruling, so `testing/suites/` is a surface although `testing/` is a
    container — and a `tests/` directory anywhere is out by class.
    """
    if rel in roots:
        return "in"
    if rel in containers:
        return "container"
    parts = rel.split("/")
    if TESTS_DIR in parts:
        return "tests"
    for i in range(len(parts), 0, -1):
        if "/".join(parts[:i]) in out:
            return "out"
    return None


def test_every_DIRECTORY_in_the_repo_is_RULED() -> None:
    """The fleet-wide enumeration, read off `git ls-files` rather than off a list.

    The phase's own count of one directory was wrong three times in a fortnight
    — a hand-kept population has been wrong on every re-count so far, and each
    time the only reason it was caught is that somebody counted again. This is
    the counting, on every CI run.
    """
    dirs = _tracked_dirs()
    assert len(dirs) > 20, f"only {len(dirs)} directories read — this walk read nothing"
    missing_roots = _ROOTS - dirs
    assert not missing_roots, (
        f"ruled-in surfaces the walk did not reach: {sorted(missing_roots)} — "
        f"either the surface moved or the walk is scoped wrong"
    )
    unruled = sorted(d for d in dirs
                     if _ruling_for(d, roots=_ROOTS, out=RULED_OUT,
                                    containers=CONTAINERS) is None)
    assert not unruled, (
        f"directories that are neither a ruled-in producer surface, ruled out "
        f"by name, nor a container: {unruled}. Rule each one in or out and "
        f"record the reason — an unexplained exclusion is the hole this phase "
        f"exists to close."
    )


def _ruling_defects(*, out: dict, containers: dict, roots: set,
                    is_dir: Callable[[str], bool]) -> list[str]:
    """The three ways the ruling tables can be wrong about themselves: a
    ruling whose directory is gone (covers nothing after a rename), a
    directory in two tables (one ruling silently wins), and the repo root
    ruled OUT (one line covers everything — the vacuous pass)."""
    defects = [f"{rel}: ruled by name but not a directory on disk — renamed or "
               f"removed; update the ruling or it covers nothing"
               for rel in [*out, *containers] if not is_dir(rel)]
    twice = (set(out) & set(containers)) | (set(out) & roots) | (set(containers) & roots)
    defects += [f"{rel}: ruled more than once" for rel in sorted(twice)]
    if "." in out:
        defects.append(".: the repo root ruled OUT covers every directory with "
                       "one line, which is the vacuous pass this refuses")
    return defects


def test_every_RULING_still_has_a_subject_and_rules_ONE_thing() -> None:
    """A ruling outliving its directory is how a gate stops covering a rename;
    a directory in two lists is how one ruling silently wins."""
    assert _ruling_defects(out=RULED_OUT, containers=CONTAINERS, roots=_ROOTS,
                           is_dir=lambda rel: (_REPO / rel).is_dir()) == []


def test_the_RULING_INTEGRITY_check_fires_on_each_of_its_three_defects() -> None:
    """Self-contained control: a conformant pair of tables reports nothing;
    a stale subject, a double ruling and a root OUT ruling each report once."""
    ok = _ruling_defects(out={"a": "r"}, containers={"c": "r"}, roots={"s"},
                         is_dir=lambda rel: True)
    assert ok == []
    bad = _ruling_defects(out={"a": "r", "gone": "r", ".": "r"},
                          containers={"c": "r", "a": "r"}, roots={"c"},
                          is_dir=lambda rel: rel != "gone")
    assert [d.split(":")[0] for d in bad] == ["gone", "a", "c", "."], bad


def test_the_RULING_LOOKUP_fires_on_an_unruled_directory_and_honours_precedence() -> None:
    """Self-contained control for `_ruling_for`, on a fixture built here.

    The fixture is NOT symmetric under the defect: `x/in` sits under an OUT
    ruling and must still read as `in`; `x/tests/deep` sits under nothing and
    must read as `tests`; `c/child` sits under a CONTAINER and must read as
    UNRULED, because a container does not cover its subtree.
    """
    kw = dict(roots={"x/in", "s"}, out={"x": "r"}, containers={".": "r", "c": "r"})
    assert _ruling_for("x/in", **kw) == "in", "a surface under an OUT ruling was lost"
    assert _ruling_for("x/other/deep", **kw) == "out", "an OUT ruling does not cover its subtree"
    assert _ruling_for("x/tests/deep", **kw) == "tests"
    assert _ruling_for("c", **kw) == "container"
    assert _ruling_for("c/child", **kw) is None, \
        "a container COVERED its subtree — a new directory under it would inherit a ruling nobody made"
    assert _ruling_for("zzz", **kw) is None, "an unruled directory read as ruled"


def _direct_files(rel: str, files: set[str]) -> set[str]:
    """The files sitting DIRECTLY in `rel` — not its subtree, which the walk
    rules directory by directory."""
    prefix = "" if rel == "." else rel + "/"
    return {f[len(prefix):] for f in files
            if f.startswith(prefix) and "/" not in f[len(prefix):]}


def _container_defects(containers: dict, files: set[str]) -> list[str]:
    """The three ways a container's account of its own files can be wrong: a
    file on disk the account does not name (the producer the walk cannot see),
    a file the account names that is gone (a ruling outliving its subject),
    and a file named with nobody reading it (prose reduced to data and still
    saying nothing)."""
    defects = []
    for rel, c in containers.items():
        on_disk = _direct_files(rel, files)
        for name in sorted(on_disk - set(c.files)):
            defects.append(f"{Path(rel) / name}: on disk and not in the "
                           f"container's account — name who reads it, or it is "
                           f"a producer the directory walk cannot see")
        for name in sorted(set(c.files) - on_disk):
            defects.append(f"{Path(rel) / name}: accounted for but not on disk "
                           f"— renamed or removed; update the account or it "
                           f"covers nothing")
        for name, reader in sorted(c.files.items()):
            if not reader.strip():
                defects.append(f"{Path(rel) / name}: accounted for with no "
                               f"reader named")
    return defects


def test_every_CONTAINER_accounts_for_its_own_DIRECT_files() -> None:
    """The walk rules directories; this rules the files sitting directly in a
    container, which the walk cannot see. Read off the same `git ls-files`
    population as the walk, so a stray ignored file cannot make it red."""
    assert _container_defects(CONTAINERS, _tracked_files()) == []


def test_the_CONTAINER_FILES_check_fires_on_each_of_its_three_defects() -> None:
    """Self-contained control: a complete account reports nothing — and
    `c/deep/z` is NOT reported although nothing accounts for it, because a
    container's account is of its direct files only; a file on disk the
    account omits, a file the account names that is gone, and a file with an
    empty reader each report once."""
    fixture = {"a", "c/x", "c/y", "c/deep/z"}
    ok = _container_defects({".": Container("r", {"a": "reader"}),
                             "c": Container("r", {"x": "reader", "y": "reader"})},
                            fixture)
    assert ok == []
    bad = _container_defects({".": Container("r"),
                              "c": Container("r", {"x": "", "y": "reader",
                                                   "gone": "reader"})},
                             fixture)
    assert [d.split(":")[0] for d in bad] == ["a", "c/gone", "c/x"], bad


# --- reading a surface -----------------------------------------------------------

def _rows(surface: Surface) -> list[list[str]]:
    """The three-column table's body rows, cells stripped.

    One parser for every table surface, because three copies of a markdown-table
    reader is three places for the column index to drift.
    """
    rows = []
    for line in _text(surface.readme).splitlines():
        if not line.startswith("| `") and not line.startswith("| ["):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3:
            rows.append(cells)
    return rows


def _member_of(cell: str) -> str | None:
    """The first backticked token in the subject cell, `/` stripped."""
    found = re.search(r"`([^`]+)`", cell)
    return found.group(1).rstrip("/") if found else None


def _population(surface: Surface) -> set[str]:
    return set(surface.members(surface.root)) - set(surface.exclusions)


def _listed(surface: Surface) -> dict[str, str]:
    """member -> consumer cell.

    A TABLE surface's cells are read out of its README. A DERIVED surface's are
    built here from what the predicate found, in the same shape — backticked
    repo-relative paths, and the `NOBODY` marker on a baselined member — so
    that every check below reads both kinds the same way.
    """
    if surface.consumers is None:
        out = {}
        for row in _rows(surface):
            member = _member_of(row[0])
            if member:
                out[member] = row[2]
        return out
    out = {}
    for member in sorted(_population(surface)):
        cell = ", ".join(f"`{p}`" for p in surface.consumers(member))
        if member in surface.unread:
            cell = f"**{UNREAD_MARKER} — baselined in the gate.** {cell}".rstrip()
        out[member] = cell
    return out


def _skip_if_absent(surface: Surface) -> None:
    if not surface.root.is_dir():
        pytest.skip(
            f"{surface.name} is not on this checkout (looked for "
            f"{surface.root}); with no population there is nothing to assert"
        )
    if surface.consumers is _documented_for_the_operator and not (PLANNING_ROOT / "guide").is_dir():
        pytest.skip(
            f"{surface.name} names its consumer in the planning repo's guide, "
            f"which is not beside this checkout (looked for {PLANNING_ROOT / 'guide'})"
        )


def _paths_in(cell: str) -> list[str]:
    """Backticked tokens in a consumer cell that are repo-relative paths.

    A token with a separator is a path. A bare token is one only if it resolves
    from the repo root — `install.sh` is a consumer, `harvest-intake.py` in a
    sentence is a tool being talked about. Without the second clause the
    ratchet is blind to every consumer that lives at the root.
    """
    return [t for t in re.findall(r"`([^`]+)`", cell)
            if re.search(r"\.(py|sh|md|ya?ml|txt|json)$", t)
            and ("/" in t or (_REPO / t).is_file())]


def test_the_ABSENT_SURFACE_SKIP_fires_ONLY_when_the_root_is_missing() -> None:
    """The one failing path in this file that no control covered, and it is the
    one that turns a whole surface green-by-absence.

    Every other failing path here got a self-contained control because a path
    nobody has seen run is a path nobody has seen work. This one was missed:
    the sibling planning repo is present on every machine this suite is known to
    run on, so `tracked/` has never actually skipped, and a typo in the skip
    reason or a wrong `PLANNING_ROOT` fallback would go unnoticed until the day
    coverage silently dropped by a whole surface.
    """
    def _probe(root: Path) -> Surface:
        return Surface(name="probe", root=root, readme=root / "README.md",
                       members=_files, accumulates=False)

    _skip_if_absent(_probe(_REPO))  # a real directory must NOT skip

    with pytest.raises(pytest.skip.Exception) as raised:
        _skip_if_absent(_probe(_REPO / "__no_such_surface__"))
    assert "__no_such_surface__" in str(raised.value), (
        "the skip reason must name the path it looked for, or a reader cannot "
        "tell a missing sibling repo from a renamed directory"
    )


@pytest.fixture(params=[s.name for s in SURFACES])
def surface(request) -> Surface:
    s = _BY_NAME[request.param]
    _skip_if_absent(s)
    return s


# --- the two properties every ruled-in surface carries --------------------------

#: Cells that name nobody while looking like they name something.
_NAMES_NOBODY = frozenset({"", "-", "—", "n/a", "TBD"})


def _unlisted(on_disk: set, listed: set) -> set:
    """Members on disk with no row. The failure; a blank cell is its symptom."""
    return on_disk - listed


def _phantom(on_disk: set, listed: set) -> set:
    """Rows for something that is not a member.

    STRICTLY `listed - on_disk`, with no slack for the excluded names. An
    excluded name is one the surface's README says is NOT a row — `run_log.py`
    is a declaration module, `README.md` is the table itself — so forgiving a
    row for one would let the table contradict the prose the exclusion rests on,
    and silently permitting a stray row is the drift this phase exists to catch.
    A store that IS a member and merely cannot be cadence-checked is
    `cadence_exempt`, not this.
    """
    return listed - on_disk


def _unnamed(listed: dict) -> list:
    return [m for m, cell in listed.items() if cell.strip() in _NAMES_NOBODY]


def test_every_member_on_disk_has_a_ROW(surface: Surface) -> None:
    """Read off disk rather than out of the table.

    A table checked against itself cannot see the member that was never added to
    it, which is the exact shape of the finding this phase is the remedy for.
    (A derived surface lists every member by construction; the check it needs
    is the next one.)
    """
    on_disk = _population(surface)
    assert on_disk, f"no members found under {surface.root} — this gate read nothing"
    listed = set(_listed(surface))
    assert not _unlisted(on_disk, listed), (
        f"{surface.name} holds members with no row in {surface.readme.name}: "
        f"{sorted(_unlisted(on_disk, listed))}. A surface nobody reads is what "
        f"this gate exists to stop producing; one nobody LISTS is how one gets "
        f"there."
    )
    assert not _phantom(on_disk, listed), (
        f"{surface.readme.name} has rows for things that are not members of "
        f"{surface.name}: {sorted(_phantom(on_disk, listed))}"
    )


def test_every_row_NAMES_A_CONSUMER(surface: Surface) -> None:
    """The weaker claim, made of every surface: somebody is named.

    On a derived surface this is the check that fires for a member the
    predicate found nothing for — a hook not in `settings.json`, an agent no
    live surface dispatches, an activity nothing sources.
    """
    empty = _unnamed(_listed(surface))
    where = (f"{surface.readme.name}" if surface.readme
             else f"`{surface.consumers.__name__}` — nothing on disk consumes them")
    assert not empty, (
        f"{surface.name} members with no named consumer ({where}): {empty}. "
        f"Name what reads this, or the member does not belong in a surface "
        f"whose population claims every entry answers a standing question. "
        f"If it is a real finding rather than a fix, baseline it in `unread` "
        f"with the reason — the ratchet forces the line out when it is wired."
    )


def test_the_TWO_BASE_checks_fire_on_the_two_ways_to_be_wrong() -> None:
    """Live controls for requirement 5's two shapes, on self-contained samples.

    Both were also demonstrated by real mutation at authoring time — a tool
    added to `scripts/helpers/` with no row, and a row whose cell was `—`; each
    turned the suite red in exactly the predicted test. Those mutations ran once,
    by hand, in a session nobody can re-open. These run on every CI run, so the
    failing path stays exercised rather than remembered.

    The samples are BUILT HERE rather than borrowed from a live surface: a
    control sharing a fixture with the code under mutation over-fires and proves
    nothing about the check.
    """
    assert _unlisted({"a.py"}, {"a.py"}) == set(), "fires on a listed member"
    assert _unlisted({"a.py", "orphan.py"}, {"a.py"}), \
        "a member with NO ROW AT ALL is invisible — requirement 5, shape one"
    assert _phantom({"a.py"}, {"a.py", "ghost.py"}), \
        "a row for something not on disk is invisible"
    assert _unnamed({"a.py": "`config/commands/standup.md`"}) == [], \
        "fires on a row that names a consumer"
    for nobody in ("", "  ", "-", "—", "n/a", "TBD"):
        assert _unnamed({"a.py": nobody}), (
            f"an EMPTY consumer cell {nobody!r} is invisible — requirement 5, "
            f"shape two"
        )


def test_PATHS_IN_sees_a_root_level_consumer_and_not_a_tool_being_discussed() -> None:
    """Control for the second clause: the ratchet on `scripts/services/` reads
    `install.sh` out of a cell, and a bare tool name in prose is not a path."""
    assert _paths_in("`install.sh`") == ["install.sh"]
    assert _paths_in("`config/settings.json`, `install.sh`") == ["config/settings.json", "install.sh"]
    assert _paths_in("wraps `harvest-intake.py` for the operator") == []
    assert _paths_in("**NOBODY — baselined in the gate.**") == []


def test_a_DERIVED_surface_lists_an_unconsumed_member_with_an_EMPTY_cell(tmp_path: Path) -> None:
    """The derived-surface half of requirement 5, on a self-contained sample:
    a member the predicate finds nothing for reaches `_unnamed` as an empty
    cell, a consumed member reaches it as a path, and a baselined member
    carries the marker whether or not anything consumes it."""
    (tmp_path / "wired.sh").write_text("")
    (tmp_path / "orphan.sh").write_text("")
    (tmp_path / "frozen.sh").write_text("")
    probe = Surface(
        name="probe", root=tmp_path, members=_files, accumulates=False,
        consumers=lambda m: ["x/uses.sh"] if m == "wired.sh" else [],
        unread={"frozen.sh": "r"},
    )
    listed = _listed(probe)
    assert _unnamed(listed) == ["orphan.sh"], listed
    assert listed["wired.sh"] == "`x/uses.sh`"
    assert UNREAD_MARKER in listed["frozen.sh"]


def test_an_EXCLUSION_still_has_its_subject_and_its_reason(surface: Surface) -> None:
    """An exclusion outliving its subject is how a gate stops covering it.

    Two halves, and the second is the one prose can lose: the name must still be
    on disk, AND the README must still explain why it has no row — otherwise its
    absence from the table reads as an omission to the next person. A derived
    surface has no README; its reason is the dict entry, which IS its table.
    """
    named = {**surface.exclusions, **surface.cadence_exempt}
    if not named:
        pytest.skip(f"{surface.name} excludes nothing by name")
    text = _text(surface.readme) if surface.readme else None
    for name, reason in named.items():
        target = surface.root / name
        assert target.exists(), (
            f"{name} is excluded from {surface.name} ({reason}) but is not "
            f"there. Either the exclusion is stale or its subject moved."
        )
        if text is not None:
            assert name.rstrip("/") in text, (
                f"{surface.readme} no longer explains why {name} has no row, so "
                f"its absence from the table reads as an omission"
            )


# --- the derived predicates, each made to fire ---------------------------------

def test_NAMES_matches_a_whole_token_and_not_a_longer_one() -> None:
    """Control for the token match every derived predicate rests on.

    Derived from the claim the function makes about itself: a name inside a
    longer name is NOT a mention. The substring test it replaces — `tool in
    text`, still what `scripts/helpers/` used at first — passes all four of
    the negatives.
    """
    assert _names("build.sh", 'source "./build.sh --phase x"')
    assert _names("build.sh", "run `build.sh` from the root")
    assert _names("code-reviewer", "dispatch code-reviewer, then")
    assert _names("notify-done.sh", '"$HOME/.claude/hooks/notify-done.sh"')
    assert not _names("build.sh", "rebuild.sh"), "a suffix of a longer name"
    assert not _names("build.sh", "build.sh.bak"), "a prefix of a longer name"
    assert not _names("build.sh", "build.shim"), "a prefix by extension"
    assert not _names("quality-control", "quality-control-methodology.md"), \
        "an agent name inside a skill's filename"


def test_a_HOOK_not_in_settings_is_found_by_nothing() -> None:
    """`_declared_in_settings` reads the real file, so the control is the
    negative: a name that is not there yields nothing, and the three that are
    each yield the one file."""
    assert _declared_in_settings("__no_such_hook__.sh") == []
    for hook in _files(_REPO / "config" / "hooks"):
        assert _declared_in_settings(hook) == ["config/settings.json"], hook


def test_a_SOURCE_line_counts_and_a_HEADER_COMMENT_does_not(tmp_path: Path, repo_at) -> None:
    """Control for the bash-library predicate, on a corpus built here.

    The fixture varies the SHAPE: one file sources the library, one runs it as
    a command, one only describes it in a comment, one names it in a TRAILING
    comment on a live line (the shape review found the first `_code_lines`
    blind to), one invokes it after a `#` that is a parameter expansion
    rather than a comment, one invokes it after a `#` INSIDE A QUOTED STRING
    (the `"PR #${pr}"` shape `wait-for-ci.sh:36` carries, which a quote-blind
    strip cuts the line at), and the library names itself in its own header.
    Four are consumers: the source, the command, the expansion line and the
    quoted-`#` line.
    """
    w = tmp_path / "scripts" / "workflows"
    (w / "activities").mkdir(parents=True)
    (w / "common").mkdir()
    (w / "a.sh").write_text('source "${SCRIPT_DIR}/activities/lib.sh"\n')
    (w / "b.sh").write_text('X="$("${SCRIPT_DIR}/common/lib.sh" key)"\n')
    (w / "c.sh").write_text("# helper: see activities/lib.sh for details\n")
    (w / "d.sh").write_text("noop  # replaces activities/lib.sh, see c.sh\n")
    # A `#` that is a parameter expansion, BEFORE a real invocation on the same
    # line: if the trailing-comment strip fired on it, the invocation would
    # vanish and e.sh would wrongly drop out of the consumers.
    (w / "e.sh").write_text('X="${Y#pre}" "${SCRIPT_DIR}/common/lib.sh"\n')
    (w / "f.sh").write_text('echo "PR #${pr} gone"; source "${SCRIPT_DIR}/activities/lib.sh"\n')
    (w / "activities" / "lib.sh").write_text("# lib.sh — usage: source activities/lib.sh\n")
    repo_at(tmp_path)
    assert _sourced_or_run_by("lib.sh") == ["scripts/workflows/a.sh",
                                            "scripts/workflows/b.sh",
                                            "scripts/workflows/e.sh",
                                            "scripts/workflows/f.sh"]


def test_every_DERIVED_consumer_path_is_one_the_RATCHET_can_see(surface: Surface) -> None:
    """`_paths_in` carries an extension whitelist, and only the ratchet routes
    through it — so a baselined member that gained a consumer of an extension
    not on the list would never force its line out, and the gate would report
    it as still unread with a straight face. This ties the whitelist to what
    the predicates actually return, on the live surfaces, so a new surface
    whose consumers end in `.toml` fails HERE with the reason rather than
    later as a ratchet that never fires."""
    if surface.consumers is None:
        pytest.skip(f"{surface.name} is a table surface; its cells are prose a person wrote")
    for member in _population(surface):
        found = surface.consumers(member)
        seen = _paths_in(", ".join(f"`{p}`" for p in found))
        assert set(found) <= set(seen), (
            f"{surface.name}: {member}'s consumers {found} include a path "
            f"`_paths_in` does not recognise — widen its extension list, or the "
            f"ratchet is blind to this surface"
        )
        # AND EACH ONE OPENS. `_paths_in` is a shape test; the ratchet then
        # opens the path, and a path the predicate reports in a form the
        # ratchet cannot resolve — a planning-repo page, before
        # `_consumer_file` — passes the shape test and never forces a line out.
        unopenable = [p for p in found if _consumer_file(p) is None]
        assert not unopenable, (
            f"{surface.name}: {member}'s consumers {unopenable} do not resolve "
            f"to a file from this repo or the planning repo's parent — the "
            f"ratchet cannot open them"
        )


def test_a_SERVICE_counts_only_when_install_sh_reads_it_FROM_THE_REPO() -> None:
    """Control for the finding this predicate exists for: a `$SYSTEMD_DIR/`
    mention is the file install.sh WRITES, not one it reads."""
    text = _text(_REPO / "install.sh")
    assert "gh-monitor.service" in text, \
        "the fixture assumption — install.sh names the unit it generates — no longer holds"
    assert _installed_from_repo("gh-monitor.service") == [], \
        "a $SYSTEMD_DIR mention counted as reading the repo's copy"
    assert _installed_from_repo("gh-monitor.sh") == ["install.sh"]
    assert _installed_from_repo("gh-monitor.timer") == ["install.sh"]
    # The three spellings of "open it from the repo", and the two that are not.
    for live in ('ln -sf "$SERVICES_DIR/x.timer" "$T"',
                 'ln -sf "${SERVICES_DIR}/x.timer" "$T"',
                 'ln -sf "$SERVICES_DIR"/x.timer "$T"'):
        assert _reads_from_services_dir(live, "x.timer"), live
    assert not _reads_from_services_dir('cat > "$SYSTEMD_DIR/x.timer"', "x.timer"), \
        "the file install.sh WRITES counted as one it reads"
    assert not _reads_from_services_dir('"$SERVICES_DIR/x.timer.bak"', "x.timer"), \
        "a longer name counted"


def test_a_SUITE_counts_only_when_its_stem_is_in_FRAMEWORKS() -> None:
    """`run-all.sh` never names `python.sh`; it builds the path from the
    array. A name match would find nothing and a control that only checked
    the live file could not tell a parser that reads the array from one that
    matched a comment."""
    assert _frameworks_in_run_all("FRAMEWORKS=(python bats)\n") == {"python", "bats"}
    assert _frameworks_in_run_all("# FRAMEWORKS=(python)\nX=1\n") == set(), \
        "a commented-out array counted"
    assert _listed_as_framework("python.sh") == ["testing/run-all.sh"]
    assert _listed_as_framework("__no_such__.sh") == []
    # A stem that IS in run-all.sh — `ALL_CATEGORIES=(unit ...)` — and is NOT a
    # framework. Without this line a predicate matching the stem anywhere in
    # the file passes the two assertions above; found while predicting the
    # mutation count, before the mutation ran.
    assert "unit" in _text(_REPO / "testing" / "run-all.sh")
    assert _listed_as_framework("unit.sh") == [], \
        "a stem present in run-all.sh outside FRAMEWORKS counted as a suite"


def test_the_AGENT_corpus_is_the_dispatching_surfaces_and_not_the_agents() -> None:
    """Vacuity floor and scope for `_dispatched_by`: the corpus must be
    non-trivial, must not include `config/agents/` (an agent naming another to
    say what it absorbed is a note, not a dispatch), and must not include any
    `tests/` directory."""
    corpus = [_rel(p) for p in _dispatch_corpus()]
    assert len(corpus) > 30, f"only {len(corpus)} dispatching files read"
    assert not [p for p in corpus if p.startswith("config/agents/")]
    assert not [p for p in corpus if "/tests/" in p]
    assert any(p.startswith("config/rules/") for p in corpus)
    assert any("/prompts/" in p for p in corpus), "the workflow prompts are where dispatch happens"
    assert _dispatched_by("__no_such_agent__") == []


def test_the_OPERATOR_DOCS_corpus_reaches_both_repos() -> None:
    if not (PLANNING_ROOT / "guide").is_dir():
        pytest.skip(f"no planning guide beside this checkout ({PLANNING_ROOT})")
    docs = list(_operator_docs())
    assert any(p.is_relative_to(_REPO) for p in docs)
    assert any(p.is_relative_to(PLANNING_ROOT) for p in docs)
    assert _documented_for_the_operator("__no_such_workflow__.sh") == []


# --- scripts/workflows/temporal/scripts/: the partition and its two predicates ---

def test_the_ENTRYPOINT_populations_PARTITION_the_directory() -> None:
    """Four surfaces share one root, so the gap BETWEEN them is where a file
    of a fifth shape would sit, ruled by nobody while the directory reads as
    ruled. Every file in the directory is in exactly one population, and no
    population is empty — a predicate that read nothing would partition
    trivially."""
    on_disk = _files(_ENTRYPOINTS)
    parts = {s.name: _population(s) for s in SURFACES if s.root == _ENTRYPOINTS}
    assert len(parts) == 4, sorted(parts)
    for name, members in parts.items():
        assert members, f"{name} is empty — its member predicate read nothing"
    union = set().union(*parts.values())
    assert union == on_disk, (
        f"files in scripts/workflows/temporal/scripts/ that no surface claims: "
        f"{sorted(on_disk - union)} — a fifth shape needs a fifth ruling"
    )
    assert sum(len(m) for m in parts.values()) == len(union), (
        f"a file is in two populations: "
        f"{sorted(n for n in union if sum(n in m for m in parts.values()) > 1)}"
    )
    # The measured shape on the day of the ruling, as a floor rather than an
    # equality — a runner or a tool may be added, but the split itself
    # reading as 16/16/0/0 would mean the shebang test broke.
    assert len(parts["scripts/workflows/temporal/scripts/ (the libraries)"]) >= 3
    assert len(parts["scripts/workflows/temporal/scripts/ (the tools)"]) >= 4


def test_the_SHEBANG_splits_a_tool_from_a_library_and_the_NAME_makes_a_runner(tmp_path: Path) -> None:
    """Self-contained control for the four member predicates. The fixture
    varies the SHAPE: a shebang under a `run_` name is still a runner, and a
    `.sh` never reaches either `.py` population."""
    (tmp_path / "tool.py").write_text("#!/usr/bin/env python3\n")
    (tmp_path / "lib.py").write_text('"""a library"""\n')
    (tmp_path / "run_x.py").write_text("#!/usr/bin/env python3\n")
    (tmp_path / "run_y.py").write_text('"""a runner without a shebang"""\n')
    (tmp_path / "x.sh").write_text("#!/usr/bin/env bash\n")
    assert _entrypoint_shims(tmp_path) == {"x.sh"}
    assert _entrypoint_runners(tmp_path) == {"run_x.py", "run_y.py"}
    assert _entrypoint_libraries(tmp_path) == {"lib.py"}
    assert _entrypoint_tools(tmp_path) == {"tool.py"}


def test_an_EXEC_line_counts_and_a_SHIM_COMMENT_does_not(tmp_path: Path, repo_at) -> None:
    """Control for the runner predicate, on a corpus built here. `b.sh`
    names `run_b.py` ONLY in its header comment and execs `run_a.py` — the
    shape a shim cloned from a sibling and half-renamed would have — so
    `run_a.py` has two consumers, `run_b.py` none, and `run_c.py`, with no
    shim at all, none."""
    d = tmp_path / "scripts" / "workflows" / "temporal" / "scripts"
    d.mkdir(parents=True)
    (d / "a.sh").write_text('exec python3 "${SCRIPT_DIR}/run_a.py" "$@"\n')
    (d / "b.sh").write_text('# b — thin shim over run_b.py\n'
                            'exec python3 "${SCRIPT_DIR}/run_a.py" "$@"\n')
    for n in ("run_a.py", "run_b.py", "run_c.py"):
        (d / n).write_text("")
    repo_at(tmp_path)
    assert _execd_by_a_shim("run_a.py") == ["scripts/workflows/temporal/scripts/a.sh",
                                            "scripts/workflows/temporal/scripts/b.sh"]
    assert _execd_by_a_shim("run_b.py") == [], "a comment mention counted as an exec"
    assert _execd_by_a_shim("run_c.py") == [], "a runner no shim execs was found a consumer"


def test_an_IMPORT_counts_and_a_MENTION_does_not(tmp_path: Path, repo_at) -> None:
    """Control for the library predicate, on a corpus built here, derived
    from the claim the predicate makes: a stem in a comment, a docstring or
    a string is NOT an import. The fixture varies the shape — `from lib
    import`, `import lib`, an import from `modules/` rather than a sibling,
    and three mentions that are not imports: a comment, a string literal,
    and `import lib_extra`, whose stem CONTAINS the member's. A test file
    importing it is outside the corpus and does not count."""
    d = tmp_path / "scripts" / "workflows" / "temporal" / "scripts"
    d.mkdir(parents=True)
    (d / "lib.py").write_text('"""lib — imported by run_a.py, says this docstring"""\n')
    (d / "lib_extra.py").write_text("")
    (d / "run_a.py").write_text("from lib import thing\n")
    (d / "run_b.py").write_text("import lib\n")
    (d / "run_c.py").write_text("# see lib for the shape\nimport lib_extra\nX = 'lib'\n")
    m = tmp_path / "scripts" / "workflows" / "temporal" / "modules"
    m.mkdir()
    (m / "m.py").write_text("from lib import other\n")
    t = tmp_path / "scripts" / "tests"
    t.mkdir()
    (t / "test_lib.py").write_text("import lib\n")
    repo_at(tmp_path)
    assert _imported_by_stem("lib.py") == [
        "scripts/workflows/temporal/modules/m.py",
        "scripts/workflows/temporal/scripts/run_a.py",
        "scripts/workflows/temporal/scripts/run_b.py",
    ]
    assert _imported_by_stem("lib_extra.py") == ["scripts/workflows/temporal/scripts/run_c.py"]
    assert _imported_by_stem("__no_such__.py") == []


def test_the_FLEET_PYTHON_corpus_is_the_fleet_and_not_the_tests() -> None:
    """Vacuity floor and scope for `_imported_by_stem`: the corpus reaches
    both the entrypoints and `modules/`, holds no test file, and is not
    trivially small."""
    corpus = [_rel(p) for p in _fleet_python()]
    assert len(corpus) > 50, f"only {len(corpus)} fleet modules read"
    assert not [p for p in corpus if "/tests/" in p]
    assert any(p.startswith("scripts/workflows/temporal/scripts/run_") for p in corpus)
    assert any(p.startswith("scripts/workflows/temporal/modules/") for p in corpus)
    # The finding this predicate was written around: two comment mentions
    # in `config_digest.py`, and no import anywhere.
    assert "compare_run_config" in _text(
        _REPO / "scripts" / "workflows" / "temporal" / "common" / "journal" / "config_digest.py"
    ), "the fixture assumption — config_digest.py mentions the tool in a comment — no longer holds"
    assert _imported_by_stem("compare_run_config.py") == [], \
        "a comment mention in config_digest.py counted as an import"


# --- the cadence clause, which binds ACCUMULATING surfaces only -----------------

def _cadence_gaps(listed: dict, excluded) -> list[tuple[str, str]]:
    """Rows that name a cadence or a runner but not both. Excluded rows skipped."""
    return [(m, cell) for m, cell in listed.items()
            if m not in excluded
            and not (cell.partition("·")[0].strip() and cell.partition("·")[2].strip())]


def test_an_ACCUMULATING_surface_names_a_cadence_AND_a_runner(surface: Surface) -> None:
    """Requirement 2's ruling, in code: a store must say who empties it, when.

    A surface with a reader nobody runs is the failure the borrowed §0 property
    sees and the older `does a reader exist` question does not. It binds stores
    because a store accumulates items awaiting disposition; it does not bind an
    on-demand reader, which never builds a backlog to drain.
    """
    if not surface.accumulates:
        pytest.skip(
            f"{surface.name} does not accumulate items awaiting disposition, so "
            f"the cadence clause does not bind it (requirement 2, ruled "
            f"2026-09-10: an on-demand reader is a conformant consumer)"
        )
    gaps = _cadence_gaps(_listed(surface), surface.cadence_exempt)
    assert not gaps, (
        f"{surface.name} rows that do not name a cadence AND a runner separated "
        f"by `·`: {gaps}. A store whose triage has no named runner is out of "
        f"conformance with Tracked Items §0."
    )


def test_the_CADENCE_check_fires_on_a_half_filled_cell() -> None:
    """Live control for the check above, on a SELF-CONTAINED sample.

    The real accumulating surface is `tracked/` in the SIBLING PLANNING REPO,
    which this repo must not edit — so the mutation that would prove this check
    discriminates cannot be performed on its own population. The sample below is
    built here rather than borrowed from that surface, because a control sharing
    a fixture with the code under mutation over-fires and proves nothing.

    THE PROPERTY UNDER TEST IS *BOTH HALVES*, not `the cell is non-empty` —
    `test_every_row_NAMES_A_CONSUMER` already makes the weaker claim, and a
    control that only distinguished empty from non-empty would be testing that
    one instead.
    """
    both = {"issues": "sprint close-out · the sprint's owner"}
    assert _cadence_gaps(both, set()) == [], "the check fires on a conformant row"
    assert _cadence_gaps({"issues": "sprint close-out"}, set()), \
        "a cadence with NO NAMED RUNNER is invisible to this check"
    assert _cadence_gaps({"issues": "· the sprint's owner"}, set()), \
        "a runner with NO CADENCE is invisible to this check"
    assert _cadence_gaps({"operations": ""}, {"operations"}) == [], \
        "the human-only exclusion is not honoured — requirement 4"


# --- the stronger claim, on `scripts/helpers/`: the named invoker OPENS ---------

# WHY ONLY `scripts/helpers/` CARRIES THE STRONGER CLAIM AMONG THE TABLE
# SURFACES, and it is a property of the cells rather than an oversight. That
# table's consumer cell names a PATH IN THIS REPO, which is a claim a check can
# open. `measure/`'s `Read by` names phases, candidates and open decisions in the
# planning corpus — prose addressed to a human — and `tracked/`'s names a
# cadence and a runner, one of which is a person. Opening those would mean
# asserting a proxy for "somebody read it", which is the shape § *The one
# exclusion the stores force* rules out. (A DERIVED surface makes this claim by
# construction: its cell was built from files that were opened.)
def test_a_named_invoker_RESOLVES_and_MENTIONS_the_tool() -> None:
    """The cell names a path, and the path is opened.

    `harvest-intake.py` is why this is stronger than name-only. It is a stated
    CONDITION of an exemption, invoked by one line of prose in
    `config/commands/standup.md`; if that line is dropped the intake keeps
    accepting, nothing empties it, and under a name-only check no suite goes red.
    """
    surface = _BY_NAME["scripts/helpers/"]
    verified: set[str] = set()
    for tool, cell in _listed(surface).items():
        if tool in surface.unread:
            continue
        paths = _paths_in(cell)
        assert paths, (
            f"{tool}'s `Invoked by` cell names no backticked path ending in "
            f"one of .py/.sh/.md/.yml/.yaml/.txt/.json — widen `_paths_in` if "
            f"the invoker is a real file of another kind: {cell!r}"
        )
        rejected = [p for p in paths if p in NOT_AN_INVOKER]
        assert not rejected, (
            f"{tool} names {rejected} as its invoker, which is excluded by "
            f"name: a map mentions every file in the repo, so accepting it "
            f"would make every row pass trivially."
        )
        for rel in paths:
            target = _REPO / rel
            assert target.is_file(), (
                f"{tool}'s named invoker {rel} does not exist. Either the "
                f"invoker moved or the tool is no longer invoked."
            )
            assert _names(tool, _text(target)), (
                f"{rel} is named as {tool}'s invoker and does not mention it. "
                f"This is the failure the cell exists to catch: the invocation "
                f"was dropped and the table still claims it."
            )
        verified.add(tool)
    # MEASURED AGAINST DISK, NOT AGAINST THE TABLE, AND BY TOOL, NOT BY PATH.
    # Comparing against `_listed()` — the dict the loop just walked — cannot
    # fail. Counting PATHS opened cannot fail the right way either: a tool with
    # three invokers covers for two rows that dropped out of the parse. So the
    # set of tools verified must equal the population on disk less the
    # baselined ones — a README whose table half-parses shows up as the
    # missing names, not as a count that still clears a floor.
    expected = _population(surface) - set(surface.unread)
    assert verified == expected, (
        f"tools on disk whose invoker was never opened: "
        f"{sorted(expected - verified)} — this check scoped itself past them "
        f"and would have passed vacuously"
    )


# --- the ratchet, both ways -----------------------------------------------------

def test_a_BASELINED_member_is_still_on_disk_and_still_declares_itself(surface: Surface) -> None:
    """Half one: the frozen list cannot outlive its subjects or go unsaid.

    A baselined row must carry the marker in its own cell, so a reader of the
    table learns the member is unconsumed without opening this file.
    """
    if not surface.unread:
        pytest.skip(f"{surface.name} baselines nothing")
    listed = _listed(surface)
    for member, reason in surface.unread.items():
        assert member in _population(surface), (
            f"{member} is baselined as unread on {surface.name} ({reason}) but "
            f"is not on disk. Delete the baseline entry."
        )
        assert UNREAD_MARKER in listed.get(member, ""), (
            f"{member} is baselined as unread, and its row does not say so. "
            f"Its consumer cell must carry {UNREAD_MARKER!r}."
        )


def test_the_NOT_AN_INVOKER_exclusions_still_exist_on_disk() -> None:
    """A named exclusion cannot outlive its subject silently.

    `NOT_AN_INVOKER` rejects a cell that names the repo map as an invoker — the
    map mentions every file, so accepting it would pass every row trivially. The
    entry is a path LITERAL: rename the map and the literal matches nothing, the
    rejection fires on no one, and a cell naming the new map path resolves,
    mentions the tool, and passes trivially — reopening the hole. Asserting the
    path exists makes the rename fail HERE, loudly, so the exclusion is updated
    rather than silently defeated.
    """
    for rel in NOT_AN_INVOKER:
        assert (_REPO / rel).is_file(), (
            f"{rel} is excluded by name as a non-invoker but is not on disk — "
            f"renamed or removed. Update NOT_AN_INVOKER to the new path, or the "
            f"exclusion rejects nothing and the map becomes an accepted invoker."
        )


def _consumer_file(rel: str) -> Path | None:
    """The file a consumer cell's path names, or `None`. A path is relative to
    this repo — or, for a document in the planning repo, which
    `_documented_for_the_operator` reports relative to the directory the two
    repos share, to that parent. WITHOUT THE SECOND CLAUSE THE RATCHET COULD
    NOT OPEN A GUIDE PAGE: a tool baselined for lacking a guide entry would
    stay baselined after gaining one, and the ratchet would only ever shrink
    on a consumer inside this repo. Found while ruling `temporal/scripts/`
    in, whose two unread tools have the guide as their likeliest fix."""
    for base in (_REPO, PLANNING_ROOT.parent):
        if (base / rel).is_file():
            return base / rel
    return None


def _regained(listed: dict, unread: dict) -> list[tuple[str, list[str]]]:
    """Baselined members whose cell now names a consumer that resolves and
    mentions them. On a derived surface the cell was built from files that
    were opened, so any path in it is live by construction; on a table
    surface the path is opened here."""
    out = []
    for member, cell in listed.items():
        if member not in unread:
            continue
        live = []
        for p in _paths_in(cell):
            target = None if p in NOT_AN_INVOKER else _consumer_file(p)
            if target is not None and _names(member, _text(target)):
                live.append(p)
        if live:
            out.append((member, live))
    return out


def test_the_RATCHET_fires_when_a_baselined_member_is_wired_up() -> None:
    """Live control: the shrink path runs on every CI run, not once by hand.

    A ratchet whose failing path has never run is a ratchet nobody has seen
    work, and this one's failing path CANNOT occur in the live table — a
    baselined row's cell says NOBODY by construction, so the check above is
    vacuous against real data forever. The sample is self-contained.

    IT ALSO PINS THE `docs/file_structure.txt` REJECTION, which is the hole that
    would make the whole ratchet meaningless: the map names every file in the
    repo, so if it counted as an invoker every baselined tool would read as
    wired-up the moment it was added to the map.
    """
    unread = _BY_NAME["scripts/helpers/"].unread
    tool = next(iter(unread))
    assert _regained({tool: "**NOBODY — baselined below.**"}, unread) == [], \
        "the ratchet fires on a correctly-baselined row"
    assert _regained({tool: "`config/commands/standup.md`"}, unread) == [], \
        "a named invoker that does NOT mention the tool must not clear it"
    assert _regained({tool: "`docs/file_structure.txt`"}, unread) == [], \
        "the repo map cleared a baselined tool — it is named as NOT an invoker"
    assert _regained({tool: f"`scripts/helpers/{tool}`"}, unread), \
        "a real, resolving, tool-mentioning invoker did not force the line out"


def test_the_RATCHET_fires_on_a_DERIVED_surface_too(tmp_path: Path, repo_at) -> None:
    """The derived cell is built by the gate, so the control must go through
    `_listed` rather than hand a cell in: a baselined member whose predicate
    now finds a real, resolving, member-mentioning consumer must be reported
    as regained, and one whose predicate finds nothing must not.

    SELF-CONTAINED, including the consumer file: the first draft of this
    control named the real `install.sh` as the consumer and predicted 1
    regained, observed 0 — `_regained` also opens the consumer and checks it
    mentions the member, which `install.sh` does not. The fixture was wrong,
    not the ratchet, and the fix is a consumer built here.
    """
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "frozen.sh").write_text("")
    (lib / "still.sh").write_text("")
    (tmp_path / "uses.sh").write_text("source lib/frozen.sh\n")
    repo_at(tmp_path)
    probe = Surface(
        name="probe", root=lib, members=_files, accumulates=False,
        consumers=lambda m: ["uses.sh"] if m == "frozen.sh" else [],
        unread={"frozen.sh": "r", "still.sh": "r"},
    )
    regained = _regained(_listed(probe), probe.unread)
    assert [m for m, _ in regained] == ["frozen.sh"], regained


def test_the_RATCHET_can_open_a_consumer_in_the_PLANNING_repo(tmp_path: Path, monkeypatch, repo_at) -> None:
    """The tools surface's likeliest fix is a guide page, which the predicate
    reports as `skyynet-master-planning/guide/<page>.md` — relative to the
    directory the two repos share, not to this repo. Before `_consumer_file`
    the ratchet resolved every path against `_REPO`, so that cell could never
    force a line out: predicted 0 regained under the old resolver, 1 under
    this one. Self-contained: both repos are built here."""
    repo = tmp_path / "repo"
    planning = tmp_path / "skyynet-master-planning"
    (repo / "lib").mkdir(parents=True)
    (planning / "guide").mkdir(parents=True)
    (repo / "lib" / "frozen.py").write_text("#!/usr/bin/env python3\n")
    (planning / "guide" / "ops.md").write_text("after a run, `frozen.py` reads it\n")
    repo_at(repo)
    monkeypatch.setattr(sys.modules[__name__], "PLANNING_ROOT", planning)
    probe = Surface(
        name="probe", root=repo / "lib", members=_files, accumulates=False,
        consumers=lambda m: ["skyynet-master-planning/guide/ops.md"],
        unread={"frozen.py": "r"},
    )
    assert [m for m, _ in _regained(_listed(probe), probe.unread)] == ["frozen.py"], \
        "a consumer in the planning repo did not force the baselined line out"
    assert _consumer_file("skyynet-master-planning/guide/gone.md") is None


def test_a_baselined_member_that_GAINS_a_consumer_forces_its_line_out(surface: Surface) -> None:
    """Half two — what makes the list shrink instead of becoming an excuse list.

    Wiring a baselined member up is the fix path, and the fix path fails until
    the entry is deleted. Without this the baseline is permanent by construction.
    """
    if not surface.unread:
        pytest.skip(f"{surface.name} baselines nothing")
    regained = _regained(_listed(surface), surface.unread)
    assert not regained, (
        f"these members of {surface.name} are baselined as unread and now have "
        f"a real consumer: {regained}. Delete their lines from `unread`"
        f"{' and from the README baseline section' if surface.readme else ''}"
        f" — the ratchet only shrinks."
    )


def test_a_TRANSIENT_ARTIFACT_is_not_a_member_of_any_population() -> None:
    """Live control for the exclusion class that made this gate host-coupled.

    The failure it pins is a REGRESSION THIS FILE SHIPPED: `__pycache__` under
    `scripts/helpers/` turned the surface-list check red on CI while it stayed
    green on a shell exporting `PYTHONDONTWRITEBYTECODE=1`. It cannot be
    demonstrated by creating the directory here — a test that writes into the
    tree it is grading is the coupling one level up — so the predicate is driven
    directly, which is what every population read below calls.
    """
    assert _is_transient(_REPO / "scripts" / "helpers" / "__pycache__"), \
        "bytecode caches are a member of the population — the CI-red shape"
    assert _is_transient(_REPO / ".git"), "dot-directories are tool state"
    assert not _is_transient(_REPO / "scripts" / "helpers" / "measure"), \
        "a real surface was filtered out as transient, which hides it entirely"
    assert not _is_transient(_REPO / "scripts" / "helpers" / "merge-pr.py"), \
        "a real tool was filtered out as transient, which hides it entirely"
