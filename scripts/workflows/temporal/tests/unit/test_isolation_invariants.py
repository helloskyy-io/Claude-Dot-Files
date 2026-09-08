"""Isolation is UNCONDITIONAL, and a negative outcome is OBSERVED, never asserted.

Two production failures are encoded here.

The first: `worktree_name=None if pr_number else worktree_name` put a `--pr` run
on the operator's live working tree with no discard path. Isolation is
established ONCE BY THE PARENT and passed down — two children creating the same
named worktree is `fatal: already exists`, which killed the draft->refine
handoff. The round-1 fix was right in principle and applied at the wrong
altitude, so both halves are asserted: children must NOT create one, parents
MUST.

The second: a failure banner claimed nothing was pushed when 9 files had landed
(+798/-111, on the PR branch). The operator read the banner, concluded the work
was lost, and dispatched a second full-budget run against work that was already
there. A false negative on the failure path is worse than a crash — a crash is
obviously wrong, while a confident wrong answer gets acted on.

These are structural (source-inspection) checks, so EVERY predicate below carries
a positive control per Testing Standard § Structural tests need a positive
control.

The limit of the technique, stated so nobody reads more into a green run than is
there: a source-grep catches DRIFT — a guard removed, a call reshaped, a ternary
reintroduced. It does NOT prove the module runs, and it does not prove
`observe_outcome` produces a CORRECT report; only that it still reads the two
things it must read.

AND THAT LIMIT WAS NOT ACADEMIC — IT CERTIFIED A LIVE DEFECT. `_refuses_to_guess`
asks whether the SOURCE contains "cannot determine" or "do not assume", and
`observe_outcome` contained both while its middle read discarded git's return
code and printed "Uncommitted changes: none" for a worktree it had never read.
The predicate cannot distinguish "every unreadable path says so" from "one of
three does", so it was green for two passes over exactly the false negative this
module exists to prevent.

THE STATED REASON FOR ACCEPTING THAT LIMIT EXPIRED, which is why there is now a
behavioural test below. This header used to say proving the behaviour "needs a
real git repo in `tmp_path`, which is integration-tier and does not exist yet".
That stopped being true when `observe_outcome` moved to `run_bounded`: every
launch now funnels through one `subprocess.run`, which a unit test monkeypatches
freely. `test_observe_outcome_does_not_report_a_negative_it_could_not_read`
takes the property the grep could only approximate. The REMAINING gap — a real
repo, git's own stderr, the already-exists collision — is still real and is
still tracked at issue #36, NOT in a PR body, because a PR body stops being
reachable the moment the PR merges.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import inspect
import subprocess
from typing import Callable

import pytest

from modules.assistant import assistant_activities as act
from modules.assistant.build.build import build_workflow as parent
from modules.assistant.build.build_draft import build_draft_workflow as draft
from modules.assistant.build.build_minor import build_minor_workflow as parent_minor
from modules.assistant.build.build_refine import build_refine_workflow as refine

# AUTO-DISCOVERED. The previous hand-maintained lists covered 3 of the 10
# modules that fit this file's own definition of a child and 2 of the 5 parents
# — a net whose coverage depended on someone remembering to add a line, which is
# not a net. Adding a workflow now adds it to the sweep, and a workflow that
# fits neither definition is reported rather than silently skipped.
_ASSISTANT = Path(__file__).resolve().parents[2] / "modules" / "assistant"


def _workflow_modules() -> list[tuple[str, str]]:
    """(import-path, source) for every *_workflow.py in the assistant tree."""
    found = []
    for f in sorted(_ASSISTANT.rglob("*_workflow.py")):
        if "__pycache__" in f.parts:
            continue
        rel = f.relative_to(_ASSISTANT.parent.parent)
        found.append((".".join(rel.with_suffix("").parts), f.read_text()))
    return found


# The two predicates the classification is built from, declared ABOVE it: `_classify`
# runs at import and calls them, so their definitions cannot sit below it.

def _creates_a_worktree(source: str) -> bool:
    """True when the source CALLS worktree_add — read from the AST, not the text.

    IT USED TO MATCH THE LITERAL `"act.worktree_add("`, AND THAT MADE A GREEN
    ASSERTION FALSE. `review_pr_workflow` calls `_shared.worktree_add(` — the
    same function through a different alias — so it was filed under CHILDREN,
    `test_child_does_not_create_its_own_worktree` passed while asserting
    something untrue, and the module never reached
    `test_parent_establishes_isolation`. The damage was the EXEMPTION, not the
    false pass: the one assertion that would fire if it stopped cutting its
    per-pass tree was never applied to it.

    THE AST ALSO SETTLES THE PROSE CASE THE LITERAL WAS GUARDING. The old
    predicate leaned on a trailing `(` to tell a call from a docstring mention;
    a comment reading `# calls act.worktree_add(repo, name)` would have defeated
    it. A comment is not a `Call` node, so the question stops being textual.

    A FRAGMENT THAT IS NOT A MODULE falls back to the substring: the controls
    below drive this on one-line samples, and a sample that cannot be parsed
    should still be answerable rather than crash the control that uses it.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "worktree_add(" in source
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name == "worktree_add":
            return True
    return False

def _receives_a_worktree_path(source: str) -> bool:
    """True when a PUBLIC function in the module takes `worktree: Path`.

    PUBLIC, NOT ANYWHERE IN THE TEXT, and the distinction decides the taxonomy.
    A parent that CREATES isolation still passes it around internally — 
    `build_workflow._refine_then_dispose` takes `worktree: Path` — so a
    substring match reads four parents as also RECEIVING, which is the opposite
    of what they do. Only the module's own entry point can receive isolation
    from a caller; a private helper taking the same parameter is the parent
    handing down what it just cut.

    Falls back to the substring for a fragment that is not a module, so the
    one-line controls below stay answerable.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "worktree: Path" in source
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        args = node.args
        for a in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            ann = a.annotation
            if (a.arg == "worktree" and isinstance(ann, ast.Name)
                    and ann.id == "Path"):
                return True
    return False

def _classify() -> tuple[list, list, list]:
    """Split the tree by what each module DOES, read from its source.

    Classified on behaviour rather than on a name or a folder: child-ness is a
    call-graph property, and a module that creates its own worktree is a parent
    no matter where it sits.
    """
    children, parents, both, neither = [], [], [], []
    for dotted, src in _workflow_modules():
        short = dotted.rsplit(".", 1)[-1].removesuffix("_workflow")
        mod = importlib.import_module(dotted)
        creates = _creates_a_worktree(src)
        receives = _receives_a_worktree_path(src)
        param = pytest.param(mod, id=short)
        if creates and receives:
            both.append(param)
        elif creates:
            parents.append(param)
        elif receives:
            children.append(param)
        else:
            neither.append(short)
    return children, parents, both, neither


CHILDREN, PARENTS, BOTH, UNCLASSIFIED = _classify()

# A module that RECEIVES a tree and also CUTS one. `review-pr` is the case and it
# is legitimate: it is dispatched with its parent's worktree AND cuts a fresh
# per-pass tree of the PR under review, because a loop-back needs one per pass.
#
# THE IF/ELIF THAT PRECEDED THIS COULD NOT SAY THAT. First branch won, so a
# both-module was silently a PARENT and lost the two child invariants it
# genuinely satisfies — or, while the creation predicate was alias-blind, was
# silently a CHILD and lost the parent one. Naming the third state is what stops
# the next such module being absorbed into whichever bucket the ordering favours.
ESTABLISHES = PARENTS + BOTH          # asserted to CREATE isolation
RECEIVES = CHILDREN + BOTH            # asserted to RECEIVE it


def test_the_sweep_actually_found_workflows() -> None:
    """POSITIVE CONTROL on discovery itself.

    A glob that matched nothing would make every parametrised test below vacuous
    and the suite would report green over zero coverage — which is exactly the
    silent-hole this replaced.
    """
    assert CHILDREN, "no child workflows discovered — the sweep is inert"
    assert PARENTS, "no parent workflows discovered — the sweep is inert"


def test_every_workflow_is_classifiable() -> None:
    """A module that neither creates nor receives a worktree is UNCHECKED.

    It is not necessarily wrong — but it is invisible to every isolation
    assertion in this file, and invisible is how the previous net failed.
    """
    assert not UNCLASSIFIED, (
        f"these workflows neither create nor receive a worktree, so no isolation "
        f"invariant is checked against them: {UNCLASSIFIED}"
    )






def _conditionally_skips_isolation(source: str) -> bool:
    """The exact ternary that put a --pr run on the operator's live working tree."""
    return "None if pr_number" in source


def _reads_git_subcommand(source: str, subcommand: str) -> bool:
    """The QUOTED argv token, not the bare word.

    `"log"` is how the subcommand reaches `subprocess`; the bare word `log`
    appears in prose, in `log_file`, and in `logging` — matching it unquoted
    would keep passing after the call itself was deleted.
    """
    return f'"{subcommand}"' in source


def _refuses_to_guess(source: str) -> bool:
    return "cannot determine" in source or "do not assume" in source


def _reports_observed_state(source: str) -> bool:
    return "observed git state" in source


# --- children: isolation is received, never created and never skipped ---------

@pytest.mark.parametrize("module", CHILDREN)
def test_child_does_not_create_its_own_worktree(module) -> None:
    assert not _creates_a_worktree(inspect.getsource(module)), (
        f"{module.__name__} calls worktree_add. Isolation is established once by "
        "the parent and passed down; a second child creating the same named "
        "worktree is `fatal: already exists`, which killed the draft->refine handoff."
    )


@pytest.mark.parametrize("module", RECEIVES)
def test_child_receives_a_worktree_path(module) -> None:
    assert _receives_a_worktree_path(inspect.getsource(module)), (
        f"{module.__name__} no longer takes a `worktree: Path` parameter — if it "
        "does not receive isolation it will either run unisolated or create its own."
    )


@pytest.mark.parametrize("module", RECEIVES)
def test_child_does_not_conditionally_skip_isolation(module) -> None:
    assert not _conditionally_skips_isolation(inspect.getsource(module)), (
        f"{module.__name__} reintroduced the `None if pr_number` ternary. That put "
        "a --pr run directly on the operator's live working tree, where a run "
        "dying mid-write leaves a dirty tree on a foreign branch with no discard path."
    )


# --- parents: isolation is established exactly here ---------------------------

@pytest.mark.parametrize("module", ESTABLISHES)
def test_parent_establishes_isolation(module) -> None:
    assert _creates_a_worktree(inspect.getsource(module)), (
        f"{module.__name__} no longer calls worktree_add. If the parent stops "
        "establishing isolation, every child below it runs on whatever tree it was given."
    )


# Positive controls for both predicate families — isolation above, observation
# below. Without them a rename (`act.worktree_add` -> `wt.add`) silently turns
# every assertion that uses the predicate into a permanent pass: the checks stay
# green with the invariant gone.
#
# Enumerated at COLLECTION time, one case per (predicate, sample) pair. Bundled
# into one test body, the first failing assert aborts the function and every
# later predicate's control never runs — so a second predicate that also went
# blind stays hidden until the first is fixed. A control that can mask a
# regression is the exact failure controls exist to prevent, and
# test_prompt_completeness.py enumerates its pairs for the same reason.
PREDICATE_CONTROLS = [
    ("creates_a_worktree/call", _creates_a_worktree,
     "wt = act.worktree_add(repo_root, name, ref)", True),
    # The trailing `(` IS the discriminator: a CALL, not a mention in prose. A
    # child's docstring may legitimately explain that its parent calls
    # worktree_add, and that must not read as the child calling it.
    ("creates_a_worktree/prose-mention", _creates_a_worktree,
     "# the parent calls act.worktree_add for us", False),
    ("creates_a_worktree/absent", _creates_a_worktree,
     "wt = passed_in_worktree", False),

    # THE ALIAS THE PREDICATE WAS BLIND TO, and the controls were blind to it
    # too — none of the three above is an aliased call, so the control set
    # shared the predicate's hole and could not have caught it. This is the
    # exact shape in `review_pr_workflow`.
    ("creates_a_worktree/aliased-receiver", _creates_a_worktree,
     "pr_tree = _shared.worktree_add(repo_root, name, ref)", True),
    # A comment that CONTAINS a call. The old predicate leaned on a trailing
    # `(` to tell a call from prose, which this defeats; the AST does not care.
    ("creates_a_worktree/prose-with-parens", _creates_a_worktree,
     "# the parent calls act.worktree_add(repo_root, name, ref) for us", False),
    ("receives_a_worktree_path/annotated", _receives_a_worktree_path,
     "def run(*, worktree: Path) -> str:\n    return ''", True),
    # A PRIVATE helper taking the parameter is a parent handing down what it
    # just cut, not a module receiving isolation. Reading this as "receives"
    # classified four parents as also-children.
    ("receives_a_worktree_path/private-helper", _receives_a_worktree_path,
     "def _refine(task, *, worktree: Path) -> str:\n    return ''", False),
    ("receives_a_worktree_path/unannotated", _receives_a_worktree_path,
     "def run(*, worktree) -> str:\n    return ''", False),

    ("conditionally_skips_isolation/ternary", _conditionally_skips_isolation,
     "name = None if pr_number else name", True),
    ("conditionally_skips_isolation/unconditional", _conditionally_skips_isolation,
     "name = worktree_name", False),

    ("reads_git_subcommand/log-argv", lambda s: _reads_git_subcommand(s, "log"),
     'run(["git", "log", "--oneline"])', True),
    # The bare word appears in `log_file`, in `logging`, and in prose. If the
    # quoted argv token stopped being the discriminator, this check would keep
    # passing after the `git log` call itself was deleted.
    ("reads_git_subcommand/log-bare-word", lambda s: _reads_git_subcommand(s, "log"),
     "log_file = repo_root / 'run.log'", False),
    ("reads_git_subcommand/status-argv", lambda s: _reads_git_subcommand(s, "status"),
     'run(["git", "status", "-s"])', True),
    ("reads_git_subcommand/status-absent", lambda s: _reads_git_subcommand(s, "status"),
     'run(["git", "log"])', False),

    ("refuses_to_guess/cannot-determine", _refuses_to_guess,
     "notes.append('cannot determine push state')", True),
    ("refuses_to_guess/do-not-assume", _refuses_to_guess,
     "notes.append('do not assume work was lost')", True),
    ("refuses_to_guess/asserts-a-negative", _refuses_to_guess,
     "notes.append('nothing was pushed')", False),

    ("reports_observed_state/observed", _reports_observed_state,
     "banner += f'observed git state: {obs}'", True),
    ("reports_observed_state/asserted", _reports_observed_state,
     "banner += 'the run failed'", False),
]


@pytest.mark.parametrize(
    ("predicate", "sample", "expected"),
    [pytest.param(p, s, e, id=label) for label, p, s, e in PREDICATE_CONTROLS],
)
def test_predicate_positive_control(
    predicate: Callable[[str], bool], sample: str, expected: bool
) -> None:
    assert predicate(sample) is expected, (
        f"the predicate no longer distinguishes this sample — it returned "
        f"{not expected} for {sample!r}. Every assertion that relies on it has "
        f"become a permanent pass while the invariant it names goes unchecked."
    )


# --- a negative outcome must be OBSERVED, never asserted ----------------------

def test_observe_outcome_reads_git_log() -> None:
    assert _reads_git_subcommand(inspect.getsource(act.observe_outcome), "log"), (
        "observe_outcome no longer reads `git log` — it cannot report what landed "
        "without reading HEAD, and the banner it feeds would go back to guessing."
    )


def test_observe_outcome_reads_git_status() -> None:
    assert _reads_git_subcommand(inspect.getsource(act.observe_outcome), "status"), (
        "observe_outcome no longer reads `git status` — uncommitted work would be "
        "invisible in the failure report."
    )


def test_observe_outcome_refuses_to_guess_when_it_cannot_read() -> None:
    """If it cannot determine the state it must SAY SO. It never reports a
    negative it did not verify.
    """
    assert _refuses_to_guess(inspect.getsource(act.observe_outcome)), (
        "observe_outcome lost its I-cannot-tell branch. A function that always "
        "produces a confident answer will produce a confident WRONG answer the "
        "first time git is unreadable — which is the failure that cost a duplicate run."
    )


@pytest.mark.parametrize("failure", [
    pytest.param(lambda cmd, **kw: (_ for _ in ()).throw(
        subprocess.TimeoutExpired(cmd, kw.get("timeout", 120))), id="git-status-hangs"),
    pytest.param(lambda cmd, **kw: subprocess.CompletedProcess(
        cmd, 128, stdout="", stderr="fatal: not a git repository"), id="git-status-fails"),
])
def test_observe_outcome_does_not_report_a_negative_it_could_not_read(
        monkeypatch, tmp_path, failure) -> None:
    """THE PROPERTY THE SOURCE-GREP ABOVE COULD ONLY APPROXIMATE.

    An unread `git status` must never render as a clean worktree. Both failure
    shapes are covered because they arrive differently and converge on the same
    lie: a hang becomes `returncode=124, stdout=""` via `run_bounded`, and an
    ordinary git failure is already `returncode!=0, stdout=""`. Empty stdout is
    what a CLEAN tree also produces, which is the whole conflation.

    ASSERTED AS AN ABSENCE, deliberately. Matching the new wording would pass
    just as well against a function that emitted both sentences, so what is
    checked is that the confident negative is GONE — and, separately, that the
    fact the function DID read survives, because degrading the whole report
    would trade a wrong answer for no answer.
    """
    def fake_run(cmd, **kw):
        if cmd[:2] == ["git", "status"]:
            return failure(cmd, **kw)
        return subprocess.CompletedProcess(
            cmd, 0, stdout="abc1234 real work committed\n", stderr="")

    monkeypatch.setattr(act.subprocess, "run", fake_run)
    report = act.observe_outcome(tmp_path)

    assert "Uncommitted changes: none" not in report, (
        "observe_outcome reported a clean worktree from a `git status` that "
        "never answered. This is the false negative the module's docstring "
        "records as having cost a duplicate full-budget dispatch — and the "
        "source-grep guard above is green on it, which is why this test exists."
    )
    assert "COULD NOT BE READ" in report, (
        "the unreadable state must be NAMED, not merely omitted — an operator "
        "who sees no line about uncommitted work will assume there is none."
    )
    assert "abc1234 real work committed" in report, (
        "the HEAD this function DID successfully read was discarded along with "
        "the failed one. Reporting what it CAN determine is the entire point; "
        "aborting the whole observation trades a wrong answer for no answer."
    )


def test_failure_path_reports_observed_state() -> None:
    assert _reports_observed_state(inspect.getsource(act.run_claude)), (
        "run_claude's failure path no longer reports observed git state. A "
        "turn-cap exit may have committed and pushed real work; asserting "
        "otherwise costs a duplicate full-budget run."
    )


# --- worktree_add: a failed fetch is fatal for a REMOTE ref -------------------
#
# Behavioural, not structural, and it is the one behaviour of worktree_add that
# is unit-testable without a real repo: the decision to raise is made from the
# fetch's return code and the ref's shape, both of which a fake can supply.
# (Its remaining behaviours — the already-exists collision, git's stderr on a
# genuine failure — need a real repo in tmp_path and are tracked at issue #36
# item 6.)

class _FakeRun:
    """Records the git argv it was handed and fails whatever it is told to fail."""

    def __init__(self, fail_on: str | None) -> None:
        self.fail_on = fail_on
        self.calls: list[list[str]] = []

    def __call__(self, argv, **_kwargs):
        self.calls.append(argv)
        failed = self.fail_on is not None and self.fail_on in argv
        return subprocess.CompletedProcess(
            argv, 1 if failed else 0, stdout="", stderr="fatal: could not read from remote",
        )


def test_a_failed_fetch_of_a_remote_ref_refuses_to_cut_a_worktree(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    """THE SILENT CASE IS THE DANGEROUS ONE.

    When the fetch fails but a stale `origin/<branch>` already exists locally
    from an earlier run, `git worktree add` SUCCEEDS — against content that has
    since moved — and the run plans on top of a base that is no longer real.
    Nothing downstream can tell that apart from a good run. V1 had this for free
    under `set -euo pipefail`; here it has to be explicit.
    """
    fake = _FakeRun(fail_on="fetch")
    monkeypatch.setattr(act.subprocess, "run", fake)

    with pytest.raises(RuntimeError, match="git fetch origin plan/x failed"):
        act.worktree_add(tmp_path, "wt", "origin/plan/x")

    assert not any("worktree" in a for a in fake.calls), (
        "worktree add ran anyway after the fetch failed — the raise is not "
        "preventing the stale checkout, only reporting it afterwards"
    )


def test_a_failed_fetch_of_a_local_ref_is_not_fatal(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    """Scoped to `origin/` refs on purpose, and this pins the scope.

    The new-branch path cuts from `HEAD`, which resolves with no network at
    all — V1's new-branch path did no fetch whatsoever. Raising there would turn
    every offline run into a failure over a fetch whose result is never used.
    """
    fake = _FakeRun(fail_on="fetch")
    monkeypatch.setattr(act.subprocess, "run", fake)

    assert act.worktree_add(tmp_path, "wt", "HEAD") == tmp_path / ".claude" / "worktrees" / "wt"


@pytest.mark.parametrize(
    ("ref", "expected_branch"),
    [
        pytest.param("origin/plan/x", "plan/x", id="plain"),
        pytest.param("origin/sync-origin/main", "sync-origin/main", id="prefix-repeats-in-name"),
        pytest.param("origin/team/origin/legacy", "team/origin/legacy", id="prefix-repeats-mid-path"),
    ],
)
def test_only_the_leading_origin_is_stripped_from_the_fetch_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path, ref: str, expected_branch: str,
) -> None:
    """ONE "origin/" COMES OFF, NOT EVERY ONE.

    `ref.replace("origin/", "")` was the original spelling, and the sibling test
    above could never have caught it: `origin/plan/x` has exactly one occurrence,
    so replace and removeprefix agree on it. A branch that legitimately contains
    "origin/" further along — `sync-origin/main` is an ordinary mirror-sync name
    — got every occurrence stripped, and the fetch went after a ref that does not
    exist. Paired with the fatal-fetch raise directly above, that is not a silent
    near-miss: the run dies naming a branch nobody has.

    Asserts the ARGV git actually received, because the bug was invisible in the
    return value — worktree_add still returned the right path.
    """
    fake = _FakeRun(fail_on=None)
    monkeypatch.setattr(act.subprocess, "run", fake)

    act.worktree_add(tmp_path, "wt", ref)

    fetch = next(a for a in fake.calls if "fetch" in a)
    assert fetch[-1] == expected_branch, (
        f"fetched {fetch[-1]!r} for ref {ref!r} — expected {expected_branch!r}. "
        "Every 'origin/' was stripped instead of just the leading one."
    )
    assert any("worktree" in a for a in fake.calls), "the worktree was never cut"
