"""Every `gh` this fleet launches must be anchored to the tree it is acting on.

THE OTHER HALF OF `test_no_gh_call_is_given_a_FILESYSTEM_PATH`, AND THE HALF
NOBODY CHECKED. That guard forbids the wrong way to address a repo — a `--repo`
in a `gh` argv, which fails loudly with a format error. Its own remedy sentence
is "Set the subprocess cwd from `repo_root` instead", and until this file
existed **nothing asserted the remedy had been applied.** A call that neither
passes `--repo` nor sets cwd satisfies that guard completely and still reads the
wrong repository — silently, which is the difference that matters.

MEASURED 2026-08-20 ON PR #124, one pass after the `--repo` removal that guard
records. Both CI-gate reads were left unanchored:

    result = gh_attempt(cmd, None)      # ci_verdict
    result = run_bounded(cmd)           # wait_for_ci — no cwd=

`gh_attempt(args, repo_root)` is `run_bounded(["gh", *args], cwd=repo_root)`, so
`None` means the process cwd — the directory the operator happened to be in.
**Nothing in this fleet chdirs**, and `preflight.resolve_repo_root` exists
precisely because cwd and the target tree are allowed to differ: its docstring is
"the repository ROOT, never the directory the operator happened to be in", and
`--repo` is the supported mode in which they do.

WHAT THE GAP COSTS, IN BOTH DIRECTIONS. These two reads are the ONLY inputs to
the merge gate that PR #124 wired into six parents across three families:

  * cwd repo has a PR of the same number and it is green -> the gate returns
    GREEN FOR A DIFFERENT REPOSITORY'S PR, no hold is raised, `review-pr` is
    dispatched and MERGE becomes reachable on a red tree. That is the exact hole
    the gate was built to close, reopened at the ADDRESS layer instead of the
    logic layer, where none of the gate's own 47 cases can see it.
  * cwd repo has no such PR -> every read fails for the full 600s deadline and a
    clean PR takes UNREADABLE_CHECKS and holds. That is the 2026-08-19 incident
    recorded in `ci_verdict`'s own comment block, recurring with a new cause.

WHY THE EXISTING SUITE WAS GREEN OVER IT. `test_ci_gate.py` monkeypatches
`subprocess.run` and discards the `cwd` kwarg entirely — `grep -n cwd
tests/unit/test_ci_gate.py` returned nothing. Every gate case passes with the
reads pointed at any repository at all, so no amount of behavioural testing of
the CASCADE could reach a defect in the ADDRESS. This is a structural check for
that reason, not a behavioural one.

THE CLASS, NOT THE INSTANCE. The two sites above are what was found; this test is
written against the property so the NEXT `gh` launch fails here rather than in
production. A guard listing `ci_verdict` and `wait_for_ci` would have been green
on the third.

WHAT THIS CHECKS: every `gh` dispatch under `modules/` names a tree.

  * `gh_attempt(args, tree)` — the second argument must not be a literal `None`.
  * `run_bounded(argv, ...)` / `subprocess.run(argv, ...)` where `argv` is a `gh`
    command list — must carry a `cwd=` that is not a literal `None`.

WHAT IT DOES NOT CHECK, stated because a check read as broader than it is does
more harm than a narrow one:

  * **Whether the tree passed is the RIGHT tree.** `cwd=some_unrelated_path`
    passes. This asks only that a caller made the address explicit rather than
    inheriting the operator's shell. Which tree is correct is argued at each
    call site; that it is chosen at all is what regressed.
  * **A `None` that arrives through a variable or a default.** The matcher wants
    a spelled literal, so `ci_verdict(pr)` reaching `gh_attempt(cmd, None)`
    through a defaulted parameter was — and still is — invisible here.

    THE SENTENCE THAT USED TO SIT HERE CALLED THAT PATH FAIL-SAFE AND WAS WRONG,
    which is why the defect survived a review pass reading this file. It claimed
    the verdict would be `NO_CHECKS`, "which the cascade treats as a HOLD and
    never as GREEN". `routing.ci_gate` does not treat `NO_CHECKS` as a HOLD: it
    appends a SKIPPED note and returns `hold=None`, which every parent reads as
    PROCEED. Driven on 2026-08-20: `ci_verdict("1", repo_root=None)` over
    `[{"name": "suite", "state": "FAILURE"}]` returned `NO_CHECKS` and the gate
    raised nothing. The direction that was called closed was the one that was
    open.

    WHAT IS TRUE NOW, AND WHAT HOLDS IT TRUE. `repo_root` is a REQUIRED
    parameter on both CI reads as of 2026-08-20, so the defaulted call does not
    exist to be reached: the path is closed BY THE SIGNATURE AND THE VERDICT, not
    by the cascade, which is unchanged in all six states. This guard still does
    not look at it, and nothing here should be read as claiming otherwise — the
    thing that looks is
    `test_ci_gate.py::test_a_NON_HOLDING_gate_is_unreachable_without_a_policy_READ`
    with `test_neither_CI_READ_can_be_called_without_a_tree` beside it.
  * **Anything outside `modules/`.** `scripts/helpers/measure/` launches `gh`
    from operator-invoked tools where a failure is visible to the person who
    typed the command. Out of the population on purpose, matching the scoping
    `test_every_subprocess_the_fleet_launches_is_bounded` states for itself.
"""
from __future__ import annotations

import ast
from pathlib import Path

MODULES = Path(__file__).resolve().parents[2] / "modules"

# The census below found FIVE dispatch points. The floor is deliberately lower
# than that: it exists to catch a WALK THAT STOPPED MATCHING, not to pin the
# number, and a legitimate refactor that folds two call sites into one must not
# have to edit this line to stay honest. A walk returning nothing is the failure
# this number is here for — a guard that reads no files passes silently.
_MINIMUM_DISPATCHES = 4


def _terminal_name(func: ast.AST) -> str:
    """`gh_attempt` from a bare call and from `shared.gh_attempt` alike."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _is_literal_none(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _gh_argv_names(tree: ast.AST) -> set[str]:
    """Names assigned a `gh` argv — `cmd = ["gh", "pr", "checks", ...]`.

    The shape that shipped built the argv into a variable and launched the
    variable one screen later, so a matcher that only reads inline list literals
    at the call site sees nothing at all.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target, value = node.targets[0], node.value
        if not isinstance(target, ast.Name) or not isinstance(value, ast.List):
            continue
        if value.elts and isinstance(value.elts[0], ast.Constant) \
                and value.elts[0].value == "gh":
            names.add(target.id)
    return names


def _is_gh_argv(arg: ast.AST, gh_names: set[str]) -> bool:
    if isinstance(arg, ast.Name):
        return arg.id in gh_names
    if isinstance(arg, ast.List) and arg.elts:
        first = arg.elts[0]
        return isinstance(first, ast.Constant) and first.value == "gh"
    return False


def _unanchored(source: str) -> list[str]:
    """Every `gh` dispatch in `source` that names no tree. Also the detector."""
    tree = ast.parse(source)
    gh_names = _gh_argv_names(tree)
    offenders: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _terminal_name(node.func)

        if name == "gh_attempt":
            # def gh_attempt(args, repo_root) — second positional, or by keyword.
            tree_arg: ast.AST | None = None
            if len(node.args) > 1:
                tree_arg = node.args[1]
            for kw in node.keywords:
                if kw.arg == "repo_root":
                    tree_arg = kw.value
            if tree_arg is None or _is_literal_none(tree_arg):
                offenders.append(f"line {node.lineno}: gh_attempt(..., None)")
            continue

        if name in {"run_bounded", "run"} and node.args \
                and _is_gh_argv(node.args[0], gh_names):
            cwd = next((kw.value for kw in node.keywords if kw.arg == "cwd"), None)
            if cwd is None or _is_literal_none(cwd):
                offenders.append(f"line {node.lineno}: {name}(gh argv) with no cwd")

    return offenders


def _module_files() -> list[Path]:
    found = sorted(MODULES.rglob("*.py"))
    assert len(found) > 20, (
        f"only {len(found)} modules found under {MODULES} — the walk is wrong, "
        f"and a guard that reads nothing passes silently"
    )
    return found


def test_no_gh_dispatch_in_the_fleet_runs_in_the_process_cwd() -> None:
    offenders: list[str] = []
    dispatches = 0

    for path in _module_files():
        source = path.read_text()
        tree = ast.parse(source)
        gh_names = _gh_argv_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _terminal_name(node.func)
            if name == "gh_attempt" or (
                    name in {"run_bounded", "run"} and node.args
                    and _is_gh_argv(node.args[0], gh_names)):
                dispatches += 1
        for hit in _unanchored(source):
            offenders.append(f"{path.relative_to(MODULES)} {hit}")

    assert dispatches >= _MINIMUM_DISPATCHES, (
        f"the census found only {dispatches} `gh` dispatches under {MODULES}, "
        f"below the floor of {_MINIMUM_DISPATCHES}. The walk has stopped matching "
        f"— fix the matcher rather than the floor, because a guard whose "
        f"population has collapsed to nothing reports GREEN forever."
    )

    assert not offenders, (
        "these `gh` dispatches name no tree, so `gh` resolves the repository "
        "from the PROCESS CWD — the directory the operator happened to be in, "
        "which `--repo` exists to differ from and which nothing in this fleet "
        "chdirs to:\n\n  " + "\n  ".join(offenders) + "\n\n"
        "For the CI gate this is not cosmetic in either direction: a same-numbered "
        "green PR in the cwd repo returns GREEN FOR THE WRONG REPOSITORY and puts "
        "MERGE within reach on a red tree, and a cwd repo with no such PR burns the "
        "full 600s deadline and holds a clean one.\n\n"
        "Pass the tree: `gh_attempt(cmd, repo_root)`, or `cwd=repo_root` on the "
        "`run_bounded`. Both parameters already exist and both are None-safe."
    )


def test_the_detector_would_SEE_the_two_shapes_that_shipped() -> None:
    """The #124 regression, both spellings, so the failing path runs every time.

    A census guard that has never been shown red is a guard whose predicate is
    unproven — this is the control `test_a_census_guard_proves_its_own_predicate`
    asks every population check in this tree to carry.
    """
    shipped = (
        'def ci_verdict(pr, *, repo_root=None):\n'
        '    cmd = ["pr", "checks", pr, "--json", "name,state"]\n'
        '    result = gh_attempt(cmd, None)\n'
        'def wait_for_ci(pr, *, repo_root=None):\n'
        '    cmd = ["gh", "pr", "checks", pr, "--json", "name,state"]\n'
        '    result = run_bounded(cmd)\n'
    )
    found = _unanchored(shipped)
    assert len(found) == 2, (
        f"the detector saw {len(found)} of the 2 shapes that actually shipped: {found}"
    )
    assert any("gh_attempt" in f for f in found), "the literal-None arg is invisible"
    assert any("no cwd" in f for f in found), "the missing cwd= kwarg is invisible"


def test_the_detector_ACCEPTS_the_anchored_forms() -> None:
    """The other direction: the fix must actually clear the guard.

    Without this, a detector that flagged EVERYTHING would pass the test above
    and the population test would simply be permanently red — which is a
    different way of telling nobody anything.
    """
    fixed = (
        'def ci_verdict(pr, *, repo_root=None):\n'
        '    cmd = ["pr", "checks", pr, "--json", "name,state"]\n'
        '    result = gh_attempt(cmd, repo_root)\n'
        'def wait_for_ci(pr, *, repo_root=None):\n'
        '    cmd = ["gh", "pr", "checks", pr, "--json", "name,state"]\n'
        '    result = run_bounded(cmd, cwd=repo_root)\n'
        'def gh(args, repo_root):\n'
        '    return run_bounded(["gh", *args], cwd=repo_root)\n'
        'def issues(tree):\n'
        '    return shared.gh_attempt(["issue", "list"], tree)\n'
    )
    assert _unanchored(fixed) == [], (
        f"the detector rejects correctly-anchored calls: {_unanchored(fixed)}"
    )
