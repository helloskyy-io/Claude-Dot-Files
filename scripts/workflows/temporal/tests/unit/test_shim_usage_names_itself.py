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

  * ⚠ IT USED TO READ ONLY THE FLAGS A RUNNER DECLARES, NEVER WHETHER THE VALUES
    BESIDE THEM ARE USABLE — and this bullet used to end *"nothing here could
    have caught it."* THE THIRD HALF BELOW IS THAT GAP CLOSED, added 2026-09-02,
    and it found ten sites on arrival. `./research.sh /abs/path/into/another/repo`
    was the shape: a repo path is resolved against the repo root, so an absolute
    one elsewhere is refused as escaping. That instance was found by reading and
    fixed by hand; a review then found nine more of it in the plan family, which
    is what a class looks like when only its instances are ever fixed.
    What the value half STILL cannot see is a refusal that is not about the path
    at all — `plan_refine` refuses a component with no `roadmap.md`, and a usage
    line naming such a component parses, resolves, exists, and fails anyway. The
    only instrument for that is running the line, which is how it was found.
  * It reads the runner's SOURCE, not a live `--help`. A flag added dynamically,
    or one whose name is computed, is invisible. Nothing does that today; the
    limit is named so a reader does not assume the sweep is exhaustive.
"""

from __future__ import annotations

import ast
import re
import shlex
from dataclasses import dataclass, field
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


def _declaring_calls(tree: ast.Module) -> list[ast.Call]:
    """Every `add_argument` / `add_repo_path` call in a parsed module, IN SOURCE
    ORDER.

    ONE EXTRACTION, TWO PREDICATES. `_declared_flags_in` wants a set of flag
    names and `_declared_arguments_in` wants dests, positionals and repo paths;
    both were re-deriving *which calls declare an argument* from scratch, so a
    third declaring spelling would have to be added in two places and the flag
    sweep and the value sweep would disagree about the corpus in between.

    SORTED BY SOURCE POSITION, WHICH IS NOT WHAT `ast.walk` GIVES YOU. Positional
    order is the whole meaning of a positional: `run_plan.py` declares
    `component` first, and a breadth-first walk can hand it back after `--sprint`
    depending on nesting. That would bind the wrong token to the repo path and
    the value sweep would be checking a value nobody typed there.
    """
    calls = [node for node in ast.walk(tree)
             if isinstance(node, ast.Call)
             and getattr(node.func, "attr", None) in ("add_argument", "add_repo_path")]
    return sorted(calls, key=lambda node: (node.lineno, node.col_offset))


def _declared_flags_in(tree: ast.Module) -> set[str]:
    """THE PREDICATE. Every long option in an already-parsed module.

    READ BY AST RATHER THAN BY GREP, because this file's own docstring quotes
    `--refresh` — the flag whose absence it exists to catch. A textual scan would
    read the documentation of the defect as a declaration of the fix, which is
    the failure `_missing_bag_open` records one file over and which would make
    this guard permanently unable to see the very instance it was written for.
    """
    flags: set[str] = set()
    for node in _declaring_calls(tree):
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

    The floor is the population AFTER `Dual-mode children` added six, so a
    regression that deleted this phase's shims fails here rather than quietly
    shrinking the swept set back to what it was.

    ⚠ IT WAS SET AT ELEVEN — the PRE-phase population — while the docstring
    claimed exactly the property above. Deleting this phase's six shims left
    eleven and passed, so the guard advertised protection for the population the
    phase added and provided none. The floor has to be the measured count for the
    sentence to be true, which is how the sibling floor in `test_preflight.py`
    (`>= 17`, "there were 17 when this floor was set") is written.
    """
    found = _shims()
    assert len(found) >= 17, (
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


def test_the_FLAG_SWEEP_read_something() -> None:
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
    # THE BASIS, stated because every sibling floor in this file states one: 34
    # distinct flags were documented across the seventeen shims when this was
    # written. The floor sits below the measurement rather than on it — unlike
    # the shim COUNT above, which is a population and moves only when the fleet
    # does, a flag total moves whenever any one shim's usage block is reworded,
    # and a floor pinned to 34 would fail on an ordinary edit. Twenty is the
    # point below which the reader must have stopped matching rather than the
    # prose merely having changed.
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


# ─────────────────────────────────────────────────────────────────────────────
# THE THIRD HALF — THE VALUES, not just the flags.
#
# A usage line is a documented invocation an operator copies. The name half
# proves it names its own script; the flag half proves every `--flag` in it
# exists. Neither looks at what sits BESIDE a flag, and that is where the defect
# had moved: ten documented invocations across `plan.sh` (3), `plan_refine.sh`
# (3), `plan_draft.sh` (3) and `triage_candidates.sh` (1) were refused on
# arrival — seven naming an absolute path into another checkout with no `--repo`
# (`✗ component … resolves outside the repo`), three naming a repo-relative tree
# that exists in no repo the line points at (`✗ component not found`).
#
# THE CLASS IS NOT "SEVEN ABSOLUTE PATHS". It is *a documented invocation the
# runner refuses*, and the previous pass fixed one member of it by hand in
# `research.sh` and declared it closed after sweeping `add_repo_path` HELP
# STRINGS — a different surface from the one the defect was found on. That is
# why this is a predicate over the whole corpus rather than ten more edits.
# ─────────────────────────────────────────────────────────────────────────────

#: This repository's root, which is the root a `--repo`-less invocation resolves
#: against — `preflight.resolve_repo_root` falls back to the operator's cwd, and
#: the operator copying a line out of a shim in this tree is standing in it.
_REPO_ROOT = SCRIPTS.parents[3]

#: A usage line, with its `#   ./shim.sh` prefix stripped. Separate from
#: `_INVOCATION` above, which captures the script NAME; this one captures the
#: ARGUMENTS, and one regex trying to do both reads worse than two doing one.
_INVOCATION_ARGS = re.compile(r"^#\s+\./[a-z_0-9]+\.sh(.*)$")

#: A token an operator must substitute before the line can run: `<component>`,
#: `<N>`, or the `/path/to/…` spelling three shims use for the same idea. A line
#: carrying one is a TEMPLATE, so "does this path exist" is not a question that
#: has an answer for it — the existence check below skips such lines and says so.
_PLACEHOLDER = re.compile(r"<[a-z][a-z0-9_-]*>|/path/to/", re.I)

#: argparse actions that consume no following token. Anything else does — which
#: is what lets the binder below know that `42` in `--pr 42` is the flag's value
#: and not a positional. Getting this wrong shifts every positional after it.
_ACTIONS_WITHOUT_A_VALUE = frozenset(
    {"store_true", "store_false", "store_const", "count", "help", "version"})


@dataclass
class ArgSpec:
    """What one runner's parser accepts, read off its source.

    `repo_dests` is the subset declared with `add_repo_path` — the ones
    `preflight.resolve_operator_paths` resolves against the repo root and
    refuses when they escape it. `--task-file` and `--phase` are deliberately
    NOT in it: `test_a_task_SOURCE_path_is_anchored_to_the_repo` records the
    ruling that a task source may legitimately live outside the tree, so an
    absolute one in a usage line is correct and must not be flagged here.
    """

    value_flags: dict[str, str] = field(default_factory=dict)
    positionals: list[tuple[str, bool]] = field(default_factory=list)
    repo_dests: set[str] = field(default_factory=set)


def _declared_arguments(module: Path, spec: ArgSpec | None = None) -> ArgSpec:
    """THE WALK. One runner's declared arguments, read off disk.

    Split from the predicate for the same reason `_declared_flags` is: the
    meta-guard recognises a tree-walking check by the literal shape
    `ast.parse(<x>.read_text(...))` and requires the predicate to be exercised
    against a literal snippet. A single function taking a `Path` would put this
    sweep outside the census that exists to catch exactly that.
    """
    return _declared_arguments_in(
        ast.parse(module.read_text(encoding="utf-8")), spec)


def _declared_arguments_in(tree: ast.Module, spec: ArgSpec | None = None) -> ArgSpec:
    """THE PREDICATE. Declared arguments from an already-parsed module.

    Shares `_declaring_calls` with the flag sweep, which is also where the
    source-order sort lives — see there for why order is load-bearing here.
    """
    spec = spec if spec is not None else ArgSpec()
    for node in _declaring_calls(tree):
        names = [a.value for a in node.args
                 if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if not names:
            continue
        keywords = {k.arg: k.value for k in node.keywords}

        def literal(key: str):
            node_ = keywords.get(key)
            return node_.value if isinstance(node_, ast.Constant) else None

        dest = literal("dest")
        if names[0].startswith("-"):
            resolved = dest or names[0].lstrip("-").replace("-", "_")
            if literal("action") not in _ACTIONS_WITHOUT_A_VALUE:
                for name in names:
                    spec.value_flags[name] = resolved
        else:
            resolved = dest or names[0]
            spec.positionals.append((resolved, literal("nargs") not in ("?", "*")))
        if getattr(node.func, "attr", None) == "add_repo_path":
            spec.repo_dests.add(resolved)
    return spec


def _arg_spec_for(runner: Path) -> ArgSpec:
    """The runner's own declarations, plus the two `add_identity_arguments` adds.

    Conditional for the same reason `_runner_flags` is conditional, and the
    control below exercises the negative arm: crediting a runner with
    `--run-id` when it does not route through the helper would make the binder
    swallow the following token as that flag's value.
    """
    spec = _declared_arguments(runner)
    if "add_identity_arguments" in runner.read_text(encoding="utf-8"):
        _declared_arguments(_IDENTITY, spec)
    return spec


def _bind(tokens: list[str], spec: ArgSpec) -> tuple[list[tuple[str, str]], int]:
    """Bind a usage line's tokens to the dests the runner would put them in.

    Returns `(bindings, positionals_supplied)`. An UNRECOGNISED flag is skipped
    without consuming a value, which is the safe direction: the flag half of
    this guard already fails on any flag the runner does not declare, so an
    unknown one here means that assertion is about to fire anyway.
    """
    bindings: list[tuple[str, str]] = []
    supplied = index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("-") and token != "-":
            # `--repo=/path` IS `--repo /path`. argparse accepts both and a
            # reader writing the first would otherwise bind nothing at all — not
            # a value, not a positional — so all three arms would pass over that
            # line while still counting it. No shim spells it this way today;
            # handled rather than disclosed, because the failure is silent.
            flag, _, attached = token.partition("=")
            if flag in spec.value_flags:
                if attached:
                    bindings.append((spec.value_flags[flag], attached))
                    index += 1
                    continue
                if index + 1 < len(tokens):
                    bindings.append((spec.value_flags[flag], tokens[index + 1]))
                    index += 2
                    continue
            index += 1
            continue
        if supplied < len(spec.positionals):
            bindings.append((spec.positionals[supplied][0], token))
        supplied += 1
        index += 1
    return bindings, supplied


def _invocations(shim: Path) -> list[list[str]]:
    """Every documented invocation in one shim, tokenised as a shell would.

    The trailing `# no model, no spend` comments four shims carry are stripped
    before tokenising — `shlex` would otherwise hand back `no`, `model,` and
    `spend` as three positionals and the required-positional count below would
    pass on prose.
    """
    lines = []
    for line in shim.read_text(encoding="utf-8").splitlines():
        matched = _INVOCATION_ARGS.match(line)
        if matched:
            lines.append(shlex.split(matched.group(1).split("#")[0].strip()))
    return lines


def _repo_path_values(shim: Path) -> list[tuple[list[str], str, str]]:
    """`(tokens, dest, value)` for every repo-anchored path in every usage line."""
    spec = _arg_spec_for(_runner_for(shim))
    found = []
    for tokens in _invocations(shim):
        bindings, _ = _bind(tokens, spec)
        found += [(tokens, dest, value) for dest, value in bindings
                  if dest in spec.repo_dests]
    return found


def _checkable_paths(tokens: list[str], spec: ArgSpec,
                     default_root: Path) -> list[tuple[str, str, Path]]:
    """THE PREDICATE FOR THE EXISTENCE ARM: `(dest, value, root)` per checkable path.

    A path is checkable when its OWN value has nothing left to substitute. THE
    SKIP IS PER-VALUE AND IT WAS PER-LINE FOR ONE REVISION, which is why this is
    a function rather than three lines inside the test: keyed on the line, a
    `--task-file /tmp/claude-<name>.md` elsewhere in the invocation exempted a
    concrete `component` beside it. A CONTROL CANNOT SEE WHICH ARGUMENT A TEST
    PASSES TO A REGEX — measured, on the first attempt at this fix: reverting the
    skip to the whole line left the control green while the arm went blind again.
    Extracted so the control drives THIS code and the mutation is visible.

    The root a value resolves against is the invocation's own `--repo` when it
    names one, and otherwise the repo the operator is standing in.
    """
    bindings = dict(_bind(tokens, spec)[0])
    repo_dest = spec.value_flags.get("--repo")
    root = Path(bindings[repo_dest]) if repo_dest in bindings else default_root
    return [(dest, value, root) for dest, value in _bind(tokens, spec)[0]
            if dest in spec.repo_dests and not _PLACEHOLDER.search(value)]


@pytest.mark.parametrize("shim", _shims(), ids=lambda p: p.name)
def test_every_usage_REPO_PATH_is_REPO_RELATIVE(shim: Path) -> None:
    """THE REQUIREMENT, first arm. A repo path documented as an absolute path is
    refused for every operator who does not additionally pass a `--repo` naming
    an ancestor of it — which none of the seven that shipped did.

    Repo-relative is the invariant rather than "absolute unless `--repo`
    matches", because the second is a coincidence between two strings in one
    line and reads as correct right up until somebody moves a checkout.
    """
    offenders = [(dest, value) for _, dest, value in _repo_path_values(shim)
                 if value.startswith("/")]
    assert not offenders, (
        f"{shim.name}'s usage block documents an ABSOLUTE path for "
        f"{sorted({d for d, _ in offenders})}, which `resolve_operator_paths` "
        f"refuses as escaping unless `--repo` names an ancestor: {offenders}. "
        f"Write the path relative to the repo and name the checkout with "
        f"`--repo`, which is the form every conforming line in this fleet uses.")


@pytest.mark.parametrize("shim", _shims(), ids=lambda p: p.name)
def test_every_LITERAL_usage_line_names_a_path_that_EXISTS(shim: Path) -> None:
    """THE REQUIREMENT, second arm. A line with nothing left to substitute is one
    an operator copies verbatim, so its paths have to be there verbatim.

    `docs/development/fleet-reliability` and `docs/development/managed-
    configuration` shipped in `plan_draft.sh` naming a tree layout that exists in
    neither this repo nor the planning one, and `triage_candidates.sh` documented
    `tracked/candidates` with no `--repo`, which resolves into THIS repo where
    there is no `tracked/`. All three parse, carry a declared flag, and fail.

    SKIPPED FOR A TEMPLATE VALUE ON PURPOSE. `development/<component>/research`
    has no truth value until the operator substitutes, and demanding a concrete
    example everywhere would trade a real check for a worse-documented corpus.

    ⚠ THE SKIP IS PER-VALUE, AND IT WAS PER-LINE FOR ONE REVISION. Keyed on the
    whole line, `./plan.sh development/edge-assistant/mcp-servers --repo <planning>
    --task-file /tmp/claude-<name>.md` was skipped entirely — its `component` is
    concrete and checkable, and the `<name>` belonged to an unrelated flag. A
    typo'd component on any line that happens to carry a template argument
    elsewhere would have passed, which is precisely the shape this arm exists to
    catch.

    SKIPPED ALSO WHEN THE NAMED CHECKOUT IS ABSENT, so the sweep degrades to the
    first arm on a machine holding only this repo rather than failing there.
    """
    spec = _arg_spec_for(_runner_for(shim))
    missing = [(dest, value, str(root))
               for tokens in _invocations(shim)
               for dest, value, root in _checkable_paths(tokens, spec, _REPO_ROOT)
               if root.is_dir() and not (root / value).exists()]
    assert not missing, (
        f"{shim.name} documents a copy-pasteable invocation naming a path that "
        f"is not there: {missing}. An operator following it gets "
        f"`✗ <arg> not found` from text that reads official.")


@pytest.mark.parametrize("shim", _shims(), ids=lambda p: p.name)
def test_every_usage_line_supplies_the_REQUIRED_POSITIONALS(shim: Path) -> None:
    """THE REQUIREMENT, third arm, and it closes this guard's other stated hole.

    `plan_sprint.sh` shipped a usage block that omitted the required `component`
    positional entirely, so EVERY documented invocation would have failed. The
    previous pass fixed it by reading and wrote *"it does not check that required
    positionals are documented"* into this file's limits. It does now.
    """
    spec = _arg_spec_for(_runner_for(shim))
    required = sum(1 for _, is_required in spec.positionals if is_required)
    short = [(tokens, supplied) for tokens in _invocations(shim)
             if (supplied := _bind(tokens, spec)[1]) < required]
    assert not short, (
        f"{shim.name} documents {len(short)} invocation(s) supplying fewer than "
        f"the {required} required positional(s) "
        f"{[name for name, req in spec.positionals if req]}: {short}. "
        f"argparse refuses the line before the workflow starts.")


def test_the_VALUE_SWEEP_read_something() -> None:
    """VACUITY FLOOR FOR THE VALUE HALF, and it is a third distinct floor.

    Every assertion above is over a list that is empty when the binder stops
    binding — a shape change in `add_repo_path`, a `dest` moved into `**kwargs`,
    a usage-comment prefix reworded — and three green sweeps over nothing look
    exactly like three green sweeps over the fleet.
    """
    examined = sum(len(_repo_path_values(shim)) for shim in _shims())
    # THE BASIS: 27 repo-anchored path values were documented across the
    # seventeen shims when this floor was set. It sits below the measurement for
    # the reason the flag floor states — a total that moves whenever any usage
    # block is reworded cannot be pinned to its own measurement — and 15 is the
    # point below which the binder must have stopped binding.
    assert examined >= 15, (
        f"the usage blocks across {len(_shims())} shims bind only {examined} "
        f"repo-anchored path values between them; there were 27 when this floor "
        f"was set. A binder that has stopped binding passes vacuously.")


def test_THE_VALUE_SWEEP_CATCHES_THE_LINES_THAT_SHIPPED() -> None:
    """NEGATIVE CONTROL, on all three arms, against the lines that actually shipped.

    THE FIXTURE IS SELF-CONTAINED — a literal runner and literal usage lines, no
    files — for the reason the sibling control states: a control sharing a
    fixture with the code it perturbs over-fires, and the census guard needs to
    see this guard's PREDICATE exercised against `ast.parse` of a string.
    """
    runner = (
        "import argparse\n"
        "def main(argv=None):\n"
        "    p = RepoPathParser(prog='plan')\n"
        "    p.add_repo_path('component', kind='dir')\n"
        "    p.add_repo_path('--sprint', default='development/sprints.md')\n"
        "    p.add_argument('--repo', dest='repo_target')\n"
        "    p.add_argument('--pr', dest='pr_number')\n"
        "    p.add_argument('--task-file', dest='task_file')\n"
        "    p.add_argument('--verbose', '-v', action='store_true')\n")
    spec = _declared_arguments_in(ast.parse(runner))

    assert spec.repo_dests == {"component", "sprint"}, (
        f"the predicate did not read the repo paths: {spec.repo_dests}")
    assert spec.positionals == [("component", True)], (
        f"the predicate did not read the positionals in order: {spec.positionals}")
    assert "--verbose" not in spec.value_flags, (
        "a store_true flag must not be credited with consuming the next token — "
        "that shifts every positional after it and the sweep checks the wrong "
        "value while still reporting a count")

    def repo_values(line: str) -> list[tuple[str, str]]:
        bindings, _ = _bind(shlex.split(line), spec)
        return [(d, v) for d, v in bindings if d in spec.repo_dests]

    # ARM 1 — `plan.sh` as it shipped: an absolute component, no `--repo`.
    shipped = "/opt/skyy-net/skyynet-master-planning/development/x --pr 145 --verbose"
    assert [v for _, v in repo_values(shipped) if v.startswith("/")] == [
        "/opt/skyy-net/skyynet-master-planning/development/x"], (
        "the sweep must bind the absolute component that actually shipped")

    # …and the corrected form must NOT fire. A guard that flags the fix too is
    # a guard whose only available remedy is deleting the documentation.
    corrected = "development/x --repo /opt/skyy-net/skyynet-master-planning --pr 145"
    assert [v for _, v in repo_values(corrected) if v.startswith("/")] == [], (
        "a repo-relative path beside an absolute `--repo` is the CORRECT form; "
        "flagging it would leave no conforming way to document an invocation")

    # `--pr 145` must not be read as the component. This is the binder's whole
    # reason for reading actions: get it wrong and arm 1 checks `145`.
    assert repo_values("development/x --pr 145") == [("component", "development/x")]

    # ARM 2 — `plan_draft.sh` as it shipped: concrete, relative, and nowhere.
    tokens = shlex.split("docs/development/fleet-reliability")
    bindings, supplied = _bind(tokens, spec)
    assert dict(bindings)["component"] == "docs/development/fleet-reliability"
    assert not _PLACEHOLDER.search(" ".join(tokens)), (
        "the shipped line had nothing to substitute — that is why it was "
        "copy-pasteable and why its absence mattered")
    assert not (_REPO_ROOT / "docs/development/fleet-reliability").exists(), (
        "the existence arm is asserted against a path this repo really lacks; "
        "if that tree ever appears the control is testing nothing")
    # …and a template line is exempt, which is the arm that keeps the check honest.
    assert _PLACEHOLDER.search("development/<component>/research")

    # ARM 3 — `plan_sprint.sh` as it shipped: no `component` at all.
    assert _bind(shlex.split("--verbose"), spec)[1] == 0, (
        "the sweep must see zero positionals in the usage block that shipped")
    assert _bind(shlex.split("development/x --verbose"), spec)[1] == 1

    # AND THE IDENTITY FLAGS ARE NOT MAGIC, same negative arm the flag half
    # carries: a runner not routing through the helper must not be credited with
    # `--writer`, or the binder eats the token after it.
    assert "--writer" not in spec.value_flags

    # `--flag=value` IS THE SAME ARGUMENT. Bound to the same dest, and the token
    # after it is still the positional it was — the failure this arm rules out is
    # the quiet one, where an `=`-spelled line binds NOTHING and all three
    # assertions pass over it while the vacuity floor still counts the line.
    attached = _bind(shlex.split("--repo=/opt/planning development/x"), spec)[0]
    assert dict(attached)["repo_target"] == "/opt/planning"
    assert dict(attached)["component"] == "development/x"
    assert _bind(shlex.split("--repo=/opt/planning development/x"), spec)[1] == 1

    # A PLACEHOLDER BELONGS TO ITS OWN VALUE, and this arm drives
    # `_checkable_paths` rather than `_PLACEHOLDER` so that reverting the skip to
    # the whole line is VISIBLE here. It was not, on the first attempt.
    here = Path("/nowhere")
    line = shlex.split("development/x --repo /opt/planning --task-file /tmp/claude-<name>.md")
    assert _checkable_paths(line, spec, here) == [
        ("component", "development/x", Path("/opt/planning"))], (
        "a concrete component beside a template `--task-file` must stay "
        "checkable, and must resolve against the `--repo` the line names")

    # …while a value that IS a template is exempt, and takes nothing with it.
    template = shlex.split("development/<component> --sprint development/sprints.md")
    assert [dest for dest, _v, _r in _checkable_paths(template, spec, here)] == ["sprint"], (
        "the template component is exempt and the concrete `--sprint` beside it "
        "is not — per-VALUE in both directions")

    # And with no `--repo`, a path resolves against the repo the operator is in.
    assert _checkable_paths(shlex.split("development/x"), spec, here) == [
        ("component", "development/x", here)]
