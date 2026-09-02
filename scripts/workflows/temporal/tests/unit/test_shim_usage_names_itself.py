"""A shim's usage block must invoke the shim it is in, with flags that exist.

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

⚠ THE SECOND HALF — A USAGE LINE MAY ONLY NAME FLAGS THE RUNNER DECLARES — WAS
ADDED 2026-09-02, AND IT FOUND A LIVE DEFECT ON ARRIVAL. `research.sh` documented
`./research.sh <pool> --refresh` months after `--refresh` was deleted: revalidation
stopped being a mode of that parent when the write child began computing the due
set itself (`6ec37a5`), and `run_research.py` has carried no such flag since. An
operator copying that line got an argparse error from a block that reads
official. The name half of this guard was green throughout — the script named
itself correctly and told the truth about nothing else.

The extension is what makes `Dual-mode children`'s requirement 3 mean something.
The population half of that requirement needed no code: `_shims()` is a glob, so
six new shims joined the swept set the moment they landed. What a glob cannot
notice is a usage line that documents an argument nobody accepts — and the six
new pairs took the corpus from eleven copy-pasteable blocks to seventeen, on one
template, which is when a wrong flag stops being one operator's afternoon.

WHAT IT CANNOT SEE, stated because a sweep is only as good as its predicate:

  * It reads the flags a runner DECLARES, never whether the VALUES beside them
    are usable. `./research.sh /abs/path/into/another/repo` was equally wrong and
    equally documented — the pool is resolved against the repo root, so an
    absolute path elsewhere is refused as escaping — and nothing here could have
    caught it. That one was found by reading, and fixed in the same pass.
  * It reads the runner's SOURCE, not a live `--help`. A flag added dynamically,
    or one whose name is computed, is invisible. Nothing does that today; the
    limit is named so a reader does not assume the sweep is exhaustive.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1].parent / "scripts"
_INVOCATION = re.compile(r"^#\s+\./([a-z_0-9]+\.sh)", re.M)

#: A long option as it appears in a usage line. Deliberately not matching short
#: options: `-v` collides with too much ordinary prose, and every short option in
#: this fleet has a long twin that this sweep does see.
_USAGE_FLAG = re.compile(r"(?<![\w-])(--[a-z][a-z0-9-]*)")

#: Where the identity flags are declared for every runner at once. Read from the
#: source that declares them rather than retyped, for the reason
#: `add_identity_arguments` exists at all: one statement, many readers.
_IDENTITY = SCRIPTS / "dispatch_identity.py"


def _shims() -> list[Path]:
    return sorted(p for p in SCRIPTS.glob("*.sh"))


def _declared_flags(module: Path) -> set[str]:
    """THE WALK. Every long option one runner declares, read off disk.

    SPLIT FROM THE PREDICATE BELOW SO `test_a_census_guard_proves_its_own_
    predicate` CAN SEE THIS GUARD AT ALL. That meta-guard recognises a
    tree-walking check by the literal shape `ast.parse(<x>.read_text(...))`, and
    requires each one to exercise its predicate against a snippet. Written as one
    function taking a `str`, this check walked the production tree and sat
    OUTSIDE the census — a new guard invisible to the guard-over-guards, which is
    precisely the class that meta-guard exists for.
    """
    return _declared_flags_in(ast.parse(module.read_text(encoding="utf-8")))


def _declared_flags_in(tree: ast.Module) -> set[str]:
    """THE PREDICATE. Every long option in an already-parsed module.

    READ BY AST RATHER THAN BY GREP, because this file's own docstring quotes
    `--refresh` — the flag whose absence it exists to catch. A textual scan would
    read the documentation of the defect as a declaration of the fix, which is
    the failure `_missing_bag_open` records one file over and which would make
    this guard permanently unable to see the very instance it was written for.
    """
    flags: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", None) not in ("add_argument", "add_repo_path"):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                    and arg.value.startswith("--"):
                flags.add(arg.value)
    return flags


def _runner_flags(runner: Path) -> set[str]:
    """What the runner declares, plus the two `add_identity_arguments` supplies."""
    flags = _declared_flags(runner)
    if "add_identity_arguments" in runner.read_text(encoding="utf-8"):
        flags |= _declared_flags(_IDENTITY)
    return flags


def _runner_for(shim: Path) -> Path:
    return shim.parent / f"run_{shim.stem}.py"


def test_there_are_shims_to_check() -> None:
    """Vacuity guard: a moved directory would make the check below pass on nothing.

    The floor is the population before `Dual-mode children` added six, so a
    regression that deleted this phase's shims still fails here rather than
    quietly shrinking the swept set back to what it was.
    """
    found = _shims()
    assert len(found) >= 11, (
        f"only {len(found)} shims found under {SCRIPTS} — the glob is not "
        f"reading the fleet: {[p.name for p in found]}")


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


@pytest.mark.parametrize("shim", _shims(), ids=lambda p: p.name)
def test_every_usage_FLAG_is_one_the_runner_ACCEPTS(shim: Path) -> None:
    """THE REQUIREMENT. A documented flag the runner refuses is a wrong answer
    written down where it looks official."""
    runner = _runner_for(shim)
    assert runner.is_file(), (
        f"{shim.name} has no {runner.name} beside it. A shim is thin by design — "
        f"it resolves the interpreter and execs its runner — so a shim without "
        f"one documents a CLI that has no definition.")

    documented = {flag for line in shim.read_text(encoding="utf-8").splitlines()
                  if _INVOCATION.match(line)
                  for flag in _USAGE_FLAG.findall(line)}
    unknown = documented - _runner_flags(runner)
    assert not unknown, (
        f"{shim.name}'s usage block documents {sorted(unknown)}, which "
        f"{runner.name} does not declare. An operator copying that line gets an "
        f"argparse error from text that reads official — which is how "
        f"`--refresh` outlived its own deletion in `research.sh`.")


def test_the_FLAG_SWEEP_read_something(shim: Path = None) -> None:
    """VACUITY FLOOR FOR THE FLAG CHECK, and it is a different floor from the
    shim count above.

    Seventeen shims each documenting zero flags would satisfy the assertion
    above on every one of them, because an empty set has no unknown members.
    A guard that scans a corpus can pass by examining nothing, so the count of
    things examined is asserted rather than assumed.
    """
    documented = sum(
        len({flag for line in shim.read_text(encoding="utf-8").splitlines()
             if _INVOCATION.match(line)
             for flag in _USAGE_FLAG.findall(line)})
        for shim in _shims())
    assert documented >= 20, (
        f"the usage blocks across {len(_shims())} shims name only {documented} "
        f"distinct flags between them; there were 34 when this floor was set. "
        f"A predicate that has stopped matching passes vacuously.")


def test_THE_FLAG_SWEEP_CATCHES_THE_LINE_THAT_SHIPPED() -> None:
    """NEGATIVE CONTROL, on the defect this half of the guard was written for.

    ⚠ THE FIXTURE IS SELF-CONTAINED — TWO LITERAL SNIPPETS, NO FILES. A control
    sharing a fixture with the code it perturbs over-fires: the verdict stops
    being attributable to the mutation. Written as literals, the only difference
    between the passing and failing arm is the one line under test, and
    `test_a_census_guard_proves_its_own_predicate` can see that this guard's
    PREDICATE is exercised rather than only its walk.

    The failing case is `research.sh` as it ACTUALLY SHIPPED — `--refresh`
    documented against a runner that deleted the flag in `6ec37a5`.
    """
    runner = (
        "import argparse\n"
        "def main(argv=None):\n"
        "    p = argparse.ArgumentParser()\n"
        "    p.add_argument('research_dir')\n"
        "    p.add_argument('--task-file', dest='task_file')\n"
        "    p.add_argument('--verbose', '-v', action='store_true')\n")
    declared = _declared_flags_in(ast.parse(runner))
    assert declared == {"--task-file", "--verbose"}, (
        f"the predicate did not read the runner's declarations: {declared}")

    def unknown_flags(usage_line: str) -> set[str]:
        shim = f"#!/usr/bin/env bash\n# Usage:\n{usage_line}\n"
        documented = {flag for line in shim.splitlines()
                      if _INVOCATION.match(line)
                      for flag in _USAGE_FLAG.findall(line)}
        return documented - declared

    shipped = "#   ./probe.sh docs/development/x/research --refresh"
    assert unknown_flags(shipped) == {"--refresh"}, (
        "the sweep must flag the line that actually shipped in research.sh")

    conforming = "#   ./probe.sh docs/development/x/research --task-file /tmp/x.md --verbose"
    assert unknown_flags(conforming) == set(), (
        "a usage line naming only declared flags must not be flagged — a guard "
        "that fires on everything is a guard that gets deleted")

    # A usage line is `#   ./<script>.sh …`. A flag in ordinary prose elsewhere in
    # the shim is documentation, not an invocation, and must not be read as one.
    assert unknown_flags("# see --refresh in the parent's docs") == set()

    # AND THE IDENTITY FLAGS ARE NOT MAGIC. A runner that does NOT call
    # `add_identity_arguments` must not be credited with `--run-id`: the union in
    # `_runner_flags` is conditional, and a control that never exercises the
    # negative arm would let it become unconditional silently.
    assert unknown_flags("#   ./probe.sh x --run-id abc") == {"--run-id"}


def test_THE_IDENTITY_FLAGS_REACH_A_RUNNER_THAT_DECLARES_THEM() -> None:
    """The positive arm of the conditional above, on the real tree.

    Every runner in this fleet calls `add_identity_arguments`, so `--run-id` and
    `--writer` are accepted everywhere and a usage block is entitled to document
    them. If that stops being true the union in `_runner_flags` starts crediting
    a runner with flags it does not have, which is a FALSE NEGATIVE — the
    direction a guard cannot report on itself.
    """
    identity = _declared_flags_in(ast.parse(_IDENTITY.read_text(encoding="utf-8")))
    assert {"--run-id", "--writer"} <= identity, (
        f"`add_identity_arguments` no longer declares both identity flags: "
        f"{sorted(identity)}")

    missing = [shim.name for shim in _shims()
               if "add_identity_arguments" not in _runner_for(shim).read_text(encoding="utf-8")]
    assert not missing, (
        f"these runners do not route through `add_identity_arguments`: {missing}. "
        f"`test_the_run_id_ARRIVES_from_outside` owns that property; it is "
        f"restated here because this sweep's flag union DEPENDS on it.")
