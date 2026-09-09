"""Requirement 8 — a fleet module that reaches the store directly goes RED.

WHY A SWEEP AND NOT A PLACEMENT, which is Phase 1 r11's argument applied to this
store's two I/O boundaries. `content_activities` puts capture and resolve in the
activities layer, and that delivers tidiness rather than a guarantee: nothing
stops a later module importing `content_store.load_object` and reading an object
without re-hashing it, or composing `data/content-store/…` itself. r7(d) is the
rule those bypasses break — *all reads go through one resolver that re-hashes on
resolve and fails closed, and `verify` is that resolver run over everything* —
and a rule stated in a docstring is a rule the next module does not read.

⚠ THIS GUARD DELIVERS THE NEGATIVE HALF ONLY, AND SAYING SO IS PART OF ITS JOB.
It proves nobody reaches PAST the boundary. It never proves anybody reaches IT.
A fleet that captures nothing at all satisfies every assertion in this file, and
today that is exactly the fleet: no fleet-code path calls `capture_source`,
because r7(c)'s ruling leaves a research citation's read inside a `claude -p`
child where no fleet call site exists. The positive half — a sweep asserting
that every run which cites a source captured it — is not buildable until that
changes, and it is the phase's two open checklist items rather than a third one.

⚠ WHAT THIS DOES NOT LOOK AT, stated here AND in the failure message because an
enumerating test is only as good as its discovery predicate:

  * ANY DYNAMIC REACH. `importlib.import_module("…content_store")`, a `getattr`
    off the package, or a name assembled at runtime is invisible to a static
    walk. This closes the reach somebody writes by accident, not the one somebody
    writes deliberately — which is the correct ambition for a guard whose whole
    population is this repo's own modules.
  * ANYTHING OUTSIDE `scripts/workflows/temporal/{modules,scripts}/**.py`. A
    shell script that finds and cats an object, or a consumer in another repo,
    is outside the swept scope. Named in the failure text so a reader hitting
    this learns the boundary rather than assuming there is none.
  * THE TEST TREE, DELIBERATELY. `tests/unit/test_content_store.py` must import
    `content_store` — it is the module under test. A test is not a run and
    stores nothing a citation later resolves, so excluding it costs no coverage
    of the property; including it would make the guard un-writable.
  * WHETHER A CAPTURED SOURCE WAS CAPTURED AT READ TIME. That is the `capture`
    field's job, per row, and `verify` reports it. A `harvest` row crossing this
    boundary correctly is still the weaker guarantee.
  * A PACKAGE BINDING PASSED THROUGH AN INTERMEDIATE VARIABLE. The attribute
    walk resolves a chain rooted at a name an IMPORT bound, so
    `j.content_store.load_object(…)` is caught and `p = j; p.load_object(…)` is
    not. Closing that needs local dataflow, which is the point where a static
    guard starts approximating the interpreter; the shape above is the one
    somebody writes by accident, and this one is not.
  * WHETHER THE BOUNDARY'S OWN FUNCTIONS ARE CORRECT. `test_content_activities`
    and `test_verify_citations` own that; this file only asks who calls them.

SEVEN SHAPES REACH THE STORE WITHOUT A DOTTED PATH THAT NAMES IT, in two
families, and each family was shipped blind to in turn. `modules/journal/`'s
`__init__.py` re-exports the raw store functions and the package is a package,
so all seven work and none contains the string `modules.journal.content_store`.

FAMILY 1 — THE IMPORT STATEMENT ITSELF BINDS A STORE NAME. Checking the imported
NAMES rather than only the dotted module path is what closes these:

    from modules.journal import load_object      # the re-exported FUNCTION
    from modules.journal import content_store    # the SUBMODULE, bound as a name
    from modules.journal import *                # both, and everything else

FAMILY 2 — THE IMPORT BINDS THE PACKAGE AND THE REACH IS AN ATTRIBUTE ACCESS.
Nothing in the import statement names a store module or a store function at all,
so a detector reading imports alone is blind to every one of them:

    import modules.journal          →  modules.journal.content_store.load_object(…)
    import modules.journal as j     →  j.load_object(…)
    from modules import journal     →  journal.load_object(…)
    from .. import journal          →  journal.content_store.load_object(…)

⚠ EACH FAMILY CONTAINS THE FLEET'S OWN IDIOM, WHICH IS WHY NEITHER IS EXOTIC.
Eighteen fleet modules import a journal submodule as a name — every entrypoint
takes `journal_activities as journal`, and `verify_citations.py` and
`validate_bag.py` take `verify` and `validate`. `from .. import journal` is the
dominant relative-import spelling across the workflow tree (`from .. import
routing`, `from .. import plan_activities as act`, `from . import
tracked_items as ti`). So both are what a real bypass looks like: a line copied
from the one above it.

⚠ THE FIX FOR FAMILY 2 BINDS BY SEMANTICS, NEVER BY THE SPELLING `journal`, AND
TWO SEPARATE MECHANISMS HOLD THAT — which is worth stating because a review
attributed the whole job to one of them and MEASUREMENT SAID OTHERWISE:

  * MATCHING `alias.name` AND NEVER THE ASNAME. `from modules import
    journal_activities as journal` binds the identifier `journal` to a module
    that reaches no store; only the ORIGINAL name says which module that is.
  * `BOUNDARY_PARENT`, which rejects a name genuinely spelled `journal`
    imported from somewhere that is not the package's parent —
    `from modules.assistant import journal`, a sibling exporting a colliding
    name.

The eighteen entrypoints are excluded REDUNDANTLY, by both at once, which is
why neither mechanism can be controlled through them: each shape above isolates
exactly one, and the control below uses those rather than the idiom.

⚠ AND NEITHER COSTS THE EIGHTEEN FALSE POSITIVES THEY WERE PREDICTED TO COST.
Deleting the parent check outright leaves every test in this file green and
flags no fleet module: those eighteen only ever reach `journal.open_run_bag`,
which is in neither `STORE_MODULES` nor `STORE_IO_NAMES`, so a reach-based
matcher never looks at them. The trap is structurally unreachable rather than
narrowly avoided — and the guard against it is therefore UNTESTABLE THROUGH THE
SWEEP, because the tree contains no module the mistake would break. That is why
`test_the_FLEET_IDIOM_binding_journal_to_the_activities_module_is_NOT_flagged`
asserts on `_package_bindings` DIRECTLY: a sweep-routed control would begin
discriminating only once some module writes `journal.load_object` off the
activities alias — the moment the guard matters most, and the worst possible
moment to learn its control never worked.

Controls for all seven live below, one per shape. The `_package_bindings` walk
is the direct application of `test_every_subprocess_the_fleet_launches_is_bounded`'s
`visit_Import`, which closed this identical hole for `import subprocess as sp`.
"""

from __future__ import annotations

import ast
from pathlib import Path

# Derived locally rather than imported from `journal_entrypoint_facts`, which is
# the dominant idiom in this suite: that helper exists to share the ENTRYPOINT
# POPULATION between the guards that assert against it, and this file asserts
# nothing about entrypoints. A `parents[5]` root cannot drift the way a
# discovered population can, so sharing it would buy a coupling and no safety.
REPO_ROOT = Path(__file__).resolve().parents[5]
FLEET_ROOT = REPO_ROOT / "scripts" / "workflows" / "temporal"

# The package whose modules ARE the boundary. Everything under it is exempt by
# construction: `content_activities` is capture and resolve, `verify` is r7(d)'s
# bulk run of the resolver, and `citations` reaches only for an error type and a
# digest-shape check. Exempting the package rather than listing four filenames
# keeps this from failing the day a fifth module is added inside it.
BOUNDARY_DIR = FLEET_ROOT / "modules" / "journal"

# Its name alone, for the star-import case: `from modules.journal import *` names
# no store module and no store function, and binds both. It is also the name a
# package binding is recognised BY, in `_package_bindings`.
BOUNDARY_PACKAGE = BOUNDARY_DIR.name

# The package's PARENT directory name. `from modules import journal` is the one
# package-binding shape whose `node.module` names something other than the
# journal, so the parent has to be nameable to tell it from
# `from modules.journal import journal_activities as journal` — which names the
# journal and binds a different module entirely. Derived from the same Path as
# BOUNDARY_PACKAGE so the two cannot drift apart.
BOUNDARY_PARENT = BOUNDARY_DIR.parent.name

# Directories swept. `tests/` is excluded — see the docstring's scope list.
SWEPT_DIRS = ("modules", "scripts")

# The two modules that own the store's I/O. Importing either from outside the
# package is a reach, whatever it is imported for.
STORE_MODULES = frozenset({"content_store", "source_fetch"})

# The names that TOUCH the store or the network, re-exported at package level
# and therefore reachable without naming a module above. Pure helpers are
# deliberately absent: `digest_of_bytes` and `validated_digest` hash and validate
# without opening anything, and flagging them would fail modules that compute a
# digest to hand TO the boundary — the conforming shape.
STORE_IO_NAMES = frozenset({
    "store_bytes", "load_object", "has_object", "stored_digests",
    "object_path", "object_relpath", "store_dir", "fetch_source",
})

# The on-disk segment a module would compose to reach an object by path. Only
# this one: `sha256` is the other segment and it is not discriminating — the
# string appears wherever anything hashes — so guarding it would produce
# failures that teach a reader to add exemptions rather than to stop reaching.
STORE_PATH_SEGMENT = "content-store"


def _swept_modules(root: Path) -> list[Path]:
    """Every fleet module under `root`, excluding the boundary package.

    `tmp_path` trees in the controls below have no `modules/journal/`, so the
    same predicate serves the real sweep and the synthetic ones — which is what
    makes a control's red mean the real sweep would have gone red too.
    """
    found: list[Path] = []
    for name in SWEPT_DIRS:
        directory = root / name
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.py")):
            if BOUNDARY_DIR in path.parents:
                continue
            found.append(path)
    return found


def _docstring_ids(tree: ast.AST) -> set[int]:
    """`id()` of every constant that is a docstring rather than a value.

    A module explaining the store in prose is not reaching into it, and the
    first version of this file flagged `content_activities`' own docstring —
    which is the false positive that teaches a reader the guard is noisy and
    should be silenced.
    """
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                and isinstance(first.value.value, str):
            ids.add(id(first.value))
    return ids


def _package_bindings(tree: ast.AST) -> dict[str, int]:
    """Dotted prefix -> lineno, for every name an import binds to the PACKAGE.

    BOUND BY SEMANTICS, NEVER BY THE SPELLING `journal`, and that distinction is
    the whole difficulty. Eighteen fleet modules write
    `from modules.journal import journal_activities as journal`, which binds the
    ACTIVITIES module to the name `journal` and reaches nothing — so a matcher
    reading the identifier text fails the unmodified tree eighteen times over.
    What is collected here is the prefix through which the package's attributes
    become reachable:

        import modules.journal        -> "modules.journal"   (binds `modules`)
        import modules.journal as j   -> "j"
        from modules import journal   -> "journal"
        from .. import journal        -> "journal"

    Two independent checks keep a non-package binding out, and the eighteen
    `journal_activities as journal` entrypoints happen to trip both — so neither
    can be observed through them. `alias.name` (never the asname) rejects
    `from modules import journal_activities as journal`; `node.module` rejects
    `from modules.assistant import journal`. Each shape isolates one check, and
    both are asserted directly on this function rather than through the sweep —
    see that control's docstring for why the sweep cannot see either.
    """
    bindings: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # `import a.b.journal` binds `a`, and reaches through the full
                # dotted path; `as j` collapses that to the one name.
                if alias.name.split(".")[-1] == BOUNDARY_PACKAGE:
                    bindings.setdefault(alias.asname or alias.name, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            named = (node.module or "").split(".")[-1]
            if node.module is not None and named != BOUNDARY_PARENT:
                continue
            for alias in node.names:
                if alias.name == BOUNDARY_PACKAGE:
                    bindings.setdefault(alias.asname or alias.name, node.lineno)
    return bindings


def _dotted(node: ast.Attribute) -> list[str] | None:
    """`a.b.c` -> `["a", "b", "c"]`; None when the chain is not rooted in a name.

    A subscript, a call or a literal at the root means the expression is not a
    static path and this guard does not follow it — see the docstring's scope
    list, which says the same about dynamic reaches generally.
    """
    parts: list[str] = []
    cursor: ast.expr = node
    while isinstance(cursor, ast.Attribute):
        parts.append(cursor.attr)
        cursor = cursor.value
    if not isinstance(cursor, ast.Name):
        return None
    parts.append(cursor.id)
    return list(reversed(parts))


def _reaches(path: Path, root: Path) -> list[str]:
    """Every direct reach into the store in one file, as `relpath:line: why`."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    skip = _docstring_ids(tree)
    where = path.relative_to(root)
    found: list[str] = []

    # PASS 1. Which local names, if any, is the journal PACKAGE reachable
    # through in this file? Empty for almost every module, which is what makes
    # pass 2 cost nothing on the fleet.
    bindings = _package_bindings(tree)
    # `j.content_store.load_object` is two nested Attribute nodes on one line
    # and both match; the reach is one reach, so it is reported once.
    seen: set[tuple[int, str]] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if set(alias.name.split(".")) & STORE_MODULES:
                    found.append(f"{where}:{node.lineno}: imports {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            parts = set((node.module or "").split("."))
            if parts & STORE_MODULES:
                found.append(f"{where}:{node.lineno}: imports from {node.module}")
            for alias in node.names:
                if alias.name in STORE_MODULES:
                    found.append(
                        f"{where}:{node.lineno}: imports the store module "
                        f"{alias.name} as a name")
                elif alias.name in STORE_IO_NAMES:
                    found.append(
                        f"{where}:{node.lineno}: imports the store I/O name "
                        f"{alias.name}")
                elif alias.name == "*" and BOUNDARY_PACKAGE in parts:
                    found.append(
                        f"{where}:{node.lineno}: star-imports {node.module}, "
                        f"binding every name its __all__ re-exports")
        elif isinstance(node, ast.Attribute) and bindings:
            # PASS 2. The reach that no import statement names: the package is
            # bound, and the store is one or two attributes off that binding.
            parts = _dotted(node)
            if parts is None:
                continue
            for prefix, _ in bindings.items():
                head = prefix.split(".")
                if parts[:len(head)] != head:
                    continue
                rest = parts[len(head):]
                if not rest or rest[0] not in (STORE_MODULES | STORE_IO_NAMES):
                    continue
                key = (node.lineno, rest[0])
                if key in seen:
                    continue
                seen.add(key)
                kind = ("the store module" if rest[0] in STORE_MODULES
                        else "the store I/O name")
                found.append(
                    f"{where}:{node.lineno}: reaches {kind} {rest[0]} through "
                    f"{prefix}, which is bound to the {BOUNDARY_PACKAGE} package")
                break
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in skip:
                continue
            if STORE_PATH_SEGMENT in node.value:
                found.append(
                    f"{where}:{node.lineno}: composes the store path segment "
                    f"{STORE_PATH_SEGMENT!r}")
    return found


def _sweep(root: Path) -> list[str]:
    """Every reach across every swept module under `root`, sorted."""
    return sorted(reach for path in _swept_modules(root)
                  for reach in _reaches(path, root))


# --- the requirement -------------------------------------------------------------


def test_no_fleet_module_reaches_the_content_store_directly() -> None:
    """THE REQUIREMENT. A module added that bypasses capture/resolve goes red."""
    offenders = _sweep(FLEET_ROOT)
    assert not offenders, (
        f"these fleet modules reach the content store without crossing its "
        f"boundary:\n  " + "\n  ".join(offenders) + "\n"
        f"Capture and resolve are ACTIVITIES (Persistent Memory Protocol Phase 2 "
        f"r8), and every read re-hashes and fails closed (r7(d)). Call "
        f"`content_activities.capture_source` / `capture_fetched_source` / "
        f"`capture_code_citation` to store, `resolve_citation` to read one, and "
        f"`verify.verify_bag` to read them all. Reaching `content_store` or "
        f"`source_fetch` directly — or composing "
        f"`data/{STORE_PATH_SEGMENT}/…` yourself — skips the re-hash, so a "
        f"corrupted object is read as a good one.\n"
        f"SCOPE OF THIS SWEEP: {'/'.join(SWEPT_DIRS)}/**.py under "
        f"{FLEET_ROOT.relative_to(REPO_ROOT)}, excluding the journal package "
        f"itself and the test tree. A dynamic import, a shell script, or a "
        f"consumer in another repo is INVISIBLE here.")


def test_the_sweep_is_not_vacuous() -> None:
    """A sweep that examined nothing satisfies the assertion above exactly.

    THE FLOOR IS PER DIRECTORY, AND A SINGLE AGGREGATE FLOOR IS WHAT THIS FILE
    SHIPPED FIRST. `modules/` alone holds 59 of the 80, so a total-only floor of
    fifty stayed green with `scripts/` — all 21 fleet entrypoints — dropped from
    the population entirely. That is the failure this control exists to catch,
    passing the control: a guard whose SCOPE has halved reports the same green
    as one that swept everything. Measured by mutation, not reasoned about.

    Floors rather than exact counts: pinning would fail this file for the wrong
    reason the next time a module is added, while a bare `assert swept` cannot
    tell one file from the whole fleet.
    """
    for name, floor in (("modules", 40), ("scripts", 15)):
        found = [p for p in _swept_modules(FLEET_ROOT)
                 if (FLEET_ROOT / name) in p.parents]
        assert len(found) >= floor, (
            f"only {len(found)} modules discovered under {FLEET_ROOT / name}; "
            f"this fleet has 59 under modules/ (outside the journal package) "
            f"and 21 under scripts/. The predicate has drifted from the tree "
            f"and the absence above proves nothing about this half of it.")


def test_the_journal_package_ITSELF_is_excluded_and_that_is_why_it_passes() -> None:
    """The exemption is load-bearing, so it is asserted rather than assumed.

    If `BOUNDARY_DIR` ever stopped matching the package's real location the
    sweep would go red on the four modules that are SUPPOSED to reach the store,
    and the obvious repair — widening the exemption — would quietly widen it for
    everyone. Naming the four here means that failure arrives as this test
    rather than as a puzzle.
    """
    swept = {path.name for path in _swept_modules(FLEET_ROOT)}
    assert not swept & {"content_store.py", "content_activities.py",
                        "source_fetch.py", "verify.py", "citations.py"}, (
        f"the boundary package is being swept as if it were a caller — "
        f"{BOUNDARY_DIR} no longer matches where those modules live")


# --- controls: the detector must SEE a reach, and see only the reaching file ------


def test_the_detector_SEES_the_reach_in_the_BOUNDARY_MODULE_itself() -> None:
    """POSITIVE CONTROL, on real code rather than a fixture.

    The assertion above is an ABSENCE, and an absence is evidence only if a
    presence is visible. `content_activities` is the one module in the tree that
    legitimately reaches the store, so pointing the detector at it is a control
    that cannot pass by breaking something the assertion would have caught by
    accident — it is a SEPARATE starting point, not a mutation of the sweep.
    """
    reaches = _reaches(BOUNDARY_DIR / "content_activities.py", FLEET_ROOT)
    assert any("content_store" in reach for reach in reaches), reaches
    assert any("source_fetch" in reach for reach in reaches), reaches


def test_the_sweep_FAILS_on_a_deliberately_non_conforming_module(tmp_path) -> None:
    """DEMONSTRATED, NOT ASSERTED. A guard that cannot go red manufactures confidence.

    THE FIXTURE IS SELF-CONTAINED AND NOT THIS REPO'S TREE. A control sharing a
    fixture with the code under mutation over-fires, and the failure then reads
    like a stronger guard rather than as a defect in the control. Three modules
    here, two conforming and one not, so the assertion has to DISCRIMINATE — a
    detector that flagged everything would pass a red/green control while being
    useless.
    """
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "good_capture.py").write_text(
        "from modules.journal.content_activities import capture_fetched_source\n"
        "def run(bag, data):\n"
        "    return capture_fetched_source(bag=bag, stage='draft', claim_id='c',\n"
        "                                  quote='q', source_ref='https://x/', data=data)\n",
        encoding="utf-8")
    (modules / "good_resolve.py").write_text(
        "from modules.journal import verify_bag\n"
        "def run(path):\n"
        "    return verify_bag(path)\n",
        encoding="utf-8")
    (modules / "bad_direct.py").write_text(
        "from modules.journal.content_store import store_bytes\n"
        "def run(bag, data):\n"
        "    return store_bytes(bag.path, data)\n",
        encoding="utf-8")

    assert len(_swept_modules(tmp_path)) == 3, "the fixture itself must be discovered"
    flagged = {reach.split(":")[0] for reach in _sweep(tmp_path)}
    assert flagged == {"modules/bad_direct.py"}, (
        f"the sweep must name exactly the non-conforming module; it named "
        f"{flagged}")


def test_the_PACKAGE_RE_EXPORT_bypass_is_caught(tmp_path) -> None:
    """The shortest bypass in the tree, and the one a module-path check misses.

    `modules/journal/__init__.py` re-exports `load_object`, so a caller reaches
    the store while naming only the package. This is the reason the detector
    matches imported NAMES and not just module paths, and it is asserted here so
    that reason cannot be refactored away silently.
    """
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "sneaky.py").write_text(
        "from modules.journal import load_object\n"
        "def run(bag, digest):\n"
        "    return load_object(bag.path, digest)\n",
        encoding="utf-8")

    flagged = _sweep(tmp_path)
    assert len(flagged) == 1 and "load_object" in flagged[0], flagged


def test_the_SUBMODULE_AS_A_NAME_bypass_is_caught(tmp_path) -> None:
    """THE SHAPE THIS FILE SHIPPED BLIND TO, kept as a control so it cannot return.

    `from modules.journal import content_store` names the package, not the
    module, and binds the module anyway — so neither a dotted-path check nor a
    re-exported-function-name check sees it. It is also how eighteen fleet
    modules already import a journal submodule, which is what makes it the
    likeliest bypass rather than an exotic one.
    """
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "idiomatic.py").write_text(
        "from modules.journal import content_store\n"
        "def run(bag, data):\n"
        "    return content_store.store_bytes(bag.path, data)\n",
        encoding="utf-8")

    flagged = _sweep(tmp_path)
    assert len(flagged) == 1 and "as a name" in flagged[0], flagged


def test_a_STAR_IMPORT_of_the_journal_package_is_caught(tmp_path) -> None:
    """`import *` binds every name `__all__` re-exports, naming none of them.

    Flagged on the package rather than on a resolved name list, because a star
    import's bindings are not knowable statically without importing — and a
    module that star-imports the journal package has reached the store whether
    or not it goes on to call `load_object`.
    """
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "star.py").write_text(
        "from modules.journal import *\n"
        "def run(bag, digest):\n"
        "    return load_object(bag.path, digest)\n",
        encoding="utf-8")

    flagged = _sweep(tmp_path)
    assert len(flagged) == 1 and "star-imports" in flagged[0], flagged


# --- controls: family 2, the four shapes that bind the PACKAGE ------------------
#
# Each fixture carries a CONFORMING sibling that binds the package the same way
# and reaches a NON-store attribute. That is what makes these discriminators
# rather than merely red: a matcher keyed on the binding alone — "this file can
# see the journal package, so flag it" — passes a red/green control and would
# fail every entrypoint in the fleet. The assertion is on the attribute reached,
# so the conformer has to survive it.


def test_the_DOTTED_PACKAGE_binding_bypass_is_caught(tmp_path) -> None:
    """`import modules.journal` -> `modules.journal.content_store.load_object(…)`.

    The import names the package and binds `modules`; nothing in the statement
    names a store module or a store function, so every import-only check reads
    it as clean. The reach is three attributes off the dotted prefix.
    """
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "dotted_bad.py").write_text(
        "import modules.journal\n"
        "def run(bag, digest):\n"
        "    return modules.journal.content_store.load_object(bag, digest)\n",
        encoding="utf-8")
    (modules / "dotted_good.py").write_text(
        "import modules.journal\n"
        "def run(run_id, writer):\n"
        "    return modules.journal.journal_activities.open_run_bag(run_id, writer)\n",
        encoding="utf-8")

    assert len(_swept_modules(tmp_path)) == 2, "the fixture itself must be discovered"
    flagged = {reach.split(":")[0] for reach in _sweep(tmp_path)}
    assert flagged == {"modules/dotted_bad.py"}, (
        f"the sweep must name exactly the non-conforming module; it named {flagged}")


def test_the_ALIASED_PACKAGE_binding_bypass_is_caught(tmp_path) -> None:
    """`import modules.journal as j` -> `j.load_object(…)`.

    THIS IS THE SHAPE THE SIBLING SWEEP ALREADY FIXED ONCE, for `import
    subprocess as sp` — see `test_every_subprocess_the_fleet_launches_is_bounded`'s
    `visit_Import`, which documents at length why an alias is a separate hole
    one import statement away from the one you closed. The alias collapses the
    dotted prefix to a single name, and the re-exported function is then one hop.
    """
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "aliased_bad.py").write_text(
        "import modules.journal as j\n"
        "def run(bag, digest):\n"
        "    return j.load_object(bag, digest)\n",
        encoding="utf-8")
    (modules / "aliased_good.py").write_text(
        "import modules.journal as j\n"
        "def run(path):\n"
        "    return j.validate.validate_bag(path)\n",
        encoding="utf-8")

    assert len(_swept_modules(tmp_path)) == 2, "the fixture itself must be discovered"
    flagged = {reach.split(":")[0] for reach in _sweep(tmp_path)}
    assert flagged == {"modules/aliased_bad.py"}, (
        f"the sweep must name exactly the non-conforming module; it named {flagged}")


def test_the_FROM_PARENT_package_binding_bypass_is_caught(tmp_path) -> None:
    """`from modules import journal` -> `journal.load_object(…)`.

    The statement names the package's PARENT, so `node.module` is `modules` and
    matches no store module — while the bound name is the package itself. This
    is the shape that forces `BOUNDARY_PARENT` to exist: without it there is no
    way to tell this line from `from modules.journal import journal_activities
    as journal`, which binds the same identifier to something harmless.
    """
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "from_parent_bad.py").write_text(
        "from modules import journal\n"
        "def run(bag, digest):\n"
        "    return journal.load_object(bag, digest)\n",
        encoding="utf-8")
    (modules / "from_parent_good.py").write_text(
        "from modules import journal\n"
        "def run(run_id, writer):\n"
        "    return journal.journal_activities.open_run_bag(run_id, writer)\n",
        encoding="utf-8")

    assert len(_swept_modules(tmp_path)) == 2, "the fixture itself must be discovered"
    flagged = {reach.split(":")[0] for reach in _sweep(tmp_path)}
    assert flagged == {"modules/from_parent_bad.py"}, (
        f"the sweep must name exactly the non-conforming module; it named {flagged}")


def test_the_RELATIVE_package_binding_bypass_is_caught(tmp_path) -> None:
    """`from .. import journal` -> `journal.content_store.load_object(…)`.

    THE LIKELIEST BYPASS IN THE TREE, because it is the fleet's dominant
    relative-import spelling: `from .. import routing`, `from .. import
    plan_activities as act`, `from . import tracked_items as ti` and twenty more.
    A module under `modules/assistant/` that needs a stored object writes this
    line without thinking about it. `node.module` is None, so the parent check
    cannot apply and the binding is recognised by the imported name alone.

    Two hops on purpose: this fixture is the one that reaches THROUGH the
    package to the submodule, which is what pins the `<bound>.content_store.…`
    resolution rather than only the one-hop re-export.
    """
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "relative_bad.py").write_text(
        "from .. import journal\n"
        "def run(bag, digest):\n"
        "    return journal.content_store.load_object(bag, digest)\n",
        encoding="utf-8")
    (modules / "relative_good.py").write_text(
        "from .. import journal\n"
        "def run(run_id, writer):\n"
        "    return journal.journal_activities.open_run_bag(run_id, writer)\n",
        encoding="utf-8")

    assert len(_swept_modules(tmp_path)) == 2, "the fixture itself must be discovered"
    flagged = {reach.split(":")[0] for reach in _sweep(tmp_path)}
    assert flagged == {"modules/relative_bad.py"}, (
        f"the sweep must name exactly the non-conforming module; it named {flagged}")


def test_the_FLEET_IDIOM_binding_journal_to_the_activities_module_is_NOT_flagged(
        tmp_path) -> None:
    """THE FALSE-POSITIVE TRAP THE FAMILY-2 FIX HAD TO AVOID — ASSERTED ON THE
    FUNCTION THAT MAKES THE CLAIM, BECAUSE THE SWEEP CANNOT SEE IT.

    `from modules.journal import journal_activities as journal` binds the name
    `journal` to the ACTIVITIES module, which reaches no store; `from modules
    import journal` and `from .. import journal` bind the PACKAGE, which does.
    All three spell the bound name `journal`, so only `node.module` tells them
    apart once the asname has been ruled out — and ruling the asname out is a
    separate mechanism, which is the distinction the docstring below draws.

    ⚠ WHY THIS DOES NOT GO THROUGH `_sweep`, WHICH IS WHERE IT WAS FIRST
    WRITTEN. Deleting the parent check was expected to fail this file loudly and
    to flag eighteen fleet modules. MEASURED, IT DOES NEITHER: every test stayed
    green and the real-tree sweep named nothing, because those eighteen modules
    only reach `journal.open_run_bag`, which is in neither name set. A control
    routed through the sweep is therefore VACUOUS for this property today. It
    would begin discriminating only once some module writes `journal.load_object`
    off the activities alias — the moment the guard matters most, and the worst
    possible moment to learn its control never worked. So the assertion is moved
    onto `_package_bindings`, where the semantic claim actually lives.
    """
    idiom = ast.parse(
        "from modules.journal import journal_activities as journal\n"
        "def run(run_id, writer):\n"
        "    return journal.open_run_bag(run_id=run_id, writer=writer)\n")
    assert _package_bindings(idiom) == {}, (
        "`journal_activities as journal` binds the ACTIVITIES module, not the "
        "package; treating it as a package binding is the identifier-text bug")

    for binds_the_package in ("from modules import journal\n",
                              "from .. import journal\n",
                              "import modules.journal as journal\n"):
        assert _package_bindings(ast.parse(binds_the_package)), (
            f"{binds_the_package.strip()!r} binds the package and must be "
            f"collected; a check that rejects it also rejects the bypass")

    # AND THE ONE THE PARENT CHECK ALONE HOLDS. A sibling package exporting a
    # colliding name binds the identifier `journal` to something that is not
    # this package; treating it as one would flag `journal.load_object` in a
    # module that never touched the journal at all. No such export exists today,
    # which is exactly why it is asserted here and cannot be asserted anywhere
    # else — the sweep has nothing to sweep.
    collision = ast.parse("from modules.assistant import journal\n")
    assert _package_bindings(collision) == {}, (
        "`journal` imported from a sibling package is not THIS package; "
        "collecting it makes every `journal.<store name>` in that module a "
        "false positive")

    # AND THE ONE `alias.name` ALONE HOLDS. This clears the parent check —
    # `modules` IS the package's parent — so only matching the original name
    # rather than the asname keeps it out. It is the isolated form of the
    # eighteen entrypoints, which trip both checks at once and therefore
    # demonstrate neither.
    aliased_sibling = ast.parse(
        "from modules import journal_activities as journal\n")
    assert _package_bindings(aliased_sibling) == {}, (
        "the ASNAME is not what says which module was imported; matching it "
        "binds `journal_activities` as if it were the package")

    # And the end-to-end half, which is real but — per the docstring above —
    # cannot discriminate on its own.
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "entrypoint_shaped.py").write_text(
        "from modules.journal import journal_activities as journal\n"
        "def run(run_id, writer):\n"
        "    return journal.open_run_bag(run_id=run_id, writer=writer)\n",
        encoding="utf-8")

    assert len(_swept_modules(tmp_path)) == 1, "the fixture itself must be discovered"
    assert _sweep(tmp_path) == []


def test_a_module_COMPOSING_the_store_path_itself_is_caught(tmp_path) -> None:
    """The reach that names no module at all — the one an import check is blind to.

    Reading an object off a path it built itself is the purest r7(d) bypass:
    no re-hash happens, so a tampered object is returned as a good one and
    nothing anywhere reports a `tampered` outcome.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "peeks.py").write_text(
        "from pathlib import Path\n"
        "def run(bag, digest):\n"
        "    return Path(f'{bag}/data/content-store/sha256/{digest[:2]}/{digest[2:]}')"
        ".read_bytes()\n",
        encoding="utf-8")

    flagged = _sweep(tmp_path)
    assert len(flagged) == 1 and "composes the store path" in flagged[0], flagged


def test_a_module_that_only_TALKS_about_the_store_is_not_flagged(tmp_path) -> None:
    """The false positive that would teach a reader to silence this guard.

    Every module in this package explains the store in prose, and the phase's
    own docs quote the layout. A detector that could not tell a docstring from a
    path join would fire on the documentation and be exempted within a week.
    """
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "talks.py").write_text(
        '"""Notes on data/content-store/sha256/ab/cdef… and why we keep bytes."""\n'
        "def run():\n"
        '    """Reads nothing from data/content-store/ — see content_store.py."""\n'
        "    return 1\n",
        encoding="utf-8")

    assert _sweep(tmp_path) == []
