"""An intake the reviewer files while EMBEDDED in a parent reaches that parent's harvest.

THE DEFECT, MEASURED ON DISK (2026-09-14). A `build` run reviewed its own
PR #192; the reviewer filed `skyynet-master-planning#32` and the banner said
*"Filed 1 intake(s), handed to the harvest (0 on the printed FILED-INTAKE line,
1 in the posted block's filed_intakes)"*. The run's bag holds five events, all
PR #192, and no event whose destination is issue #32 — and no gap. r1 false,
r5 silent. The intake body was nowhere in the journal.

WHERE IT DIED, and why every guard was green. `run_review` returned the URL
on `ReviewResult.issue_urls` (#187); `run_review_pr.py` hands that field to
the harvest. But this review ran INSIDE `build_workflow._refine_then_dispose`,
which did `notes.extend(result.notes)` — carrying the "handed to the harvest"
sentence up to the banner — and `return Verdict(result.verdict.value)`,
dropping the URLs with the local. `BuildResult` had no field for them and
`run_build.py` harvested `(ctx.pr_number, result.pr_url)`. The same shape sat
in FIVE parents. The unit tests drove `run_review` and asserted on ITS result;
the sweep declared `run_review_pr.py` the one trailing-ref entrypoint; the
harvest tests proved a handed ref lands or gaps. Nothing asked whether a parent
that embeds the reviewer hands over what the reviewer returned — the seam was
covered from both sides and never across, the shape
`test_a_PARENT_forwards_what_its_CHILD_reads` names.

FOUR LEVELS, BECAUSE THE MISS HAD THREE LAYERS AND THE FIX HAD A FOURTH:

  1. THE INNER BOUNDARY, all five parents — the dispose function each loop
     calls, with the reviewer faked to return intakes: the caller's
     accumulator holds them afterwards, across passes, and untouched on the
     CI-hold path where no reviewer ran.
  1b. THE OUTER RETURN, all five parents — the whole parent run with the
     reviewer faked at the same boundary: the URLs are ON THE RETURNED SHAPE,
     read strictly (the dataclass field, the tuple's last slot, the dict key
     by subscript). Added after review-pr measured that level 1 and level 2
     together left this line unpinned for four of five parents: deleting
     `issue_urls=issue_urls` from `build_minor`'s `BuildResult(...)` or the
     `"issue_urls"` key from `research`'s dict left all of `tests/unit/`
     green, because the read side of both defaults to empty — the original
     silence, one seam further out.
  2. THE REAL NESTING, `build` — the REAL `run_review` reading the REAL
     `disposition.md`-shaped block (intake in the block ONLY, cross-repo,
     exactly the live shape) inside the REAL `run_build`: `BuildResult`
     carries the URL out.
  3. THE ENTRYPOINT, LIVE — `run_build.main()` against a real repository, an
     isolated journal and a fake `gh`: the issue's body lands in the bag with
     the issue URL as its destination; and when `gh` cannot read that issue,
     a typed gap names it and the bag is `incomplete`. NEVER NEITHER.

The static half — every reviewer-running entrypoint splices the trailing ref —
is `test_every_parent_HARVESTS_its_github_surfaces.py`, whose population is
now derived rather than declared. This file is the dynamic half.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import run_build
from modules.assistant import routing
from modules.assistant.build.build import build_workflow as build
from modules.assistant.build.build_inputs import BuildInput, BuildResult
from modules.assistant.build.build_inputs import Verdict as BuildVerdict
from modules.assistant.build.build_minor import build_minor_workflow as build_minor
from modules.assistant.plan.plan import plan_workflow as plan
from modules.assistant.plan.plan_project import plan_project_workflow as plan_project
from modules.assistant.research.research import research_workflow as research
from modules.assistant.review_pr.review_pr_helper import ReviewInput, ReviewResult, Verdict
from modules.journal import harvest_activities
from modules.journal.bag import LABEL_INCOMPLETE, read_tag_file
from modules.journal.events import EVENTS_FILE, EventKind, GapClass, decode_event
from review_run_fakes import REPO_SLUG, _FakeWorkflow, _record

# CROSS-REPO BY CONSTRUCTION: the dispatch's repo is `REPO_SLUG` (owner/repo),
# the intake is in a planning repo — the documented live case.
INTAKE = "https://github.com/other-org/planning/issues/32"
SECOND = "https://github.com/other-org/planning/issues/33"
PR_URL = f"https://github.com/{REPO_SLUG}/pull/67"
INTAKE_BODY = "---\nstore: candidates\n---\nThe body the reviewer authored.\n"


def _reviewer_filing(monkeypatch: pytest.MonkeyPatch, module, *per_pass: tuple[str, ...]):
    """Fake `review_pr.run_review` at its boundary: pass N returns `per_pass[N]`."""
    passes: list[ReviewInput] = []

    def fake(task: ReviewInput, worktree: Path, *, worktree_name: str) -> ReviewResult:
        urls = per_pass[min(len(passes), len(per_pass) - 1)]
        passes.append(task)
        return ReviewResult(pr_number=task.pr_number, verdict=Verdict.MERGE,
                            this_pass=len(passes),
                            notes=[f"Filed {len(urls)} intake(s), handed to the harvest"],
                            issue_urls=list(urls))

    monkeypatch.setattr(module.review_pr, "run_review", fake)
    return passes


def _ci(monkeypatch: pytest.MonkeyPatch, module, state: routing.CiVerdict) -> None:
    monkeypatch.setattr(module, "wait_for_ci", lambda pr, **kw: True)
    monkeypatch.setattr(module, "ci_verdict", lambda pr, **kw: (state, []))


# --- 1. the inner boundary, all five parents -------------------------------------

def _build_pass(notes, issue_urls, *, correction):
    return build._refine_then_dispose(
        BuildInput(description="d"), "d", "67", Path("/repo"), Path("/wt"), "wt",
        notes, issue_urls, correction=correction)


def _build_minor_pass(notes, issue_urls, *, correction):
    return build_minor._refine_then_dispose(
        BuildInput(description="d"), "d", "67", Path("/repo"), Path("/wt"), "wt",
        notes, issue_urls, correction=correction)


def _plan_pass(notes, issue_urls, *, correction):
    return plan._refine_size_and_dispose(
        component=Path("/repo/c"), repo_root=Path("/repo"), worktree=Path("/wt"),
        worktree_name="wt", sprint_path=Path("/repo/s.md"),
        candidates_path=Path("/repo/c.md"), pr="67", repo_target=None,
        notes=notes, issue_urls=issue_urls, correction_pass=correction, verbose=False)


def _plan_project_pass(notes, issue_urls, *, correction):
    return plan_project._dispose("67", Path("/repo"), None, "wt", notes, issue_urls, False)


def _research_pass(notes, issue_urls, *, correction):
    return research._verify_then_dispose(
        Path("/repo/r"), "67", Path("/repo"), Path("/wt"), "wt",
        notes, issue_urls, False, correction=correction)


# --- the whole parent, its pre-gate collaborators at their boundaries ------------
#
# Each wires what the OUTER function runs before its dispose loop — the slug and
# base-ref reads, the worktree cut, the authoring child (returning the PR URL
# the real one returns) — calls it, and returns the intakes read STRICTLY off
# the returned shape: the dataclass field, the tuple unpacked at its full
# width, the dict key by subscript. Never `.get`, never `getattr` with a
# default: a shape that dropped the field must fail HERE, not read as "none
# filed". The dispose children, the CI gate and the reviewer are the test's
# to fake, through `_silence_children`, `_ci` and `_reviewer_filing`.

def _isolation(monkeypatch: pytest.MonkeyPatch, act, tmp_path: Path) -> None:
    monkeypatch.setattr(act, "base_ref", lambda pr, repo_root: "main")
    monkeypatch.setattr(act, "worktree_add", lambda *a, **k: tmp_path / "wt")


def _wire_build_parent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`run_build`'s pre-loop collaborators; level 2 reuses this and runs the parent itself."""
    monkeypatch.setattr(build, "task_text", lambda task, repo_root: "the task")
    monkeypatch.setattr(build.act, "repo_slug", lambda repo_root: REPO_SLUG)
    _isolation(monkeypatch, build.act, tmp_path)
    monkeypatch.setattr(build.act, "clock_now", lambda: 0.0)
    monkeypatch.setattr(build.act, "chain_cost_usd", lambda repo_root, since: (0.0, 0))
    monkeypatch.setattr(build.draft, "run_draft", lambda **kw: PR_URL)


def _build_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    _wire_build_parent(monkeypatch, tmp_path)
    result = build.run_build(BuildInput(description="the task"), tmp_path, "build-1")
    assert isinstance(result, BuildResult)
    return result.issue_urls


def _build_minor_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    monkeypatch.setattr(build_minor, "task_text", lambda task, repo_root: "the task")
    monkeypatch.setattr(build_minor.act, "repo_slug", lambda repo_root: REPO_SLUG)
    _isolation(monkeypatch, build_minor.act, tmp_path)
    monkeypatch.setattr(build_minor.act, "clock_now", lambda: 0.0)
    monkeypatch.setattr(build_minor.act, "chain_cost_usd", lambda repo_root, since: (0.0, 0))
    monkeypatch.setattr(build_minor.draft, "run_draft_minor", lambda **kw: PR_URL)
    result = build_minor.run_build_minor(BuildInput(description="the task"), tmp_path, "build-1")
    assert isinstance(result, BuildResult)
    return result.issue_urls


def _plan_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    monkeypatch.setattr(plan.act, "repo_slug", lambda repo_root: REPO_SLUG)
    _isolation(monkeypatch, plan.act, tmp_path)
    monkeypatch.setattr(plan.plan_draft, "run_plan_draft", lambda **kw: PR_URL)
    _pr_url, _verdict, _notes, issue_urls = plan.run_plan(
        component=tmp_path / "c", repo_root=tmp_path, worktree_name="wt",
        sprint_path=tmp_path / "s.md", candidates_path=tmp_path / "c.md")
    return issue_urls


def _plan_project_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    monkeypatch.setattr(plan_project._shared, "repo_slug", lambda repo_root: REPO_SLUG)
    _isolation(monkeypatch, plan_project.act, tmp_path)
    monkeypatch.setattr(plan_project.triage, "run_triage_candidates", lambda **kw: PR_URL)
    monkeypatch.setattr(plan_project.own, "scaffold_candidate_components",
                        lambda *a, **k: plan_project.own.Scaffolded(
                            created=[], resumed=[], extends=[], unnamed=[],
                            not_a_feature=[], unsized=[]))
    _pr_url, _verdict, _loops, _notes, issue_urls = plan_project.run_plan_project(
        repo_root=tmp_path, worktree_name="wt",
        candidates_path=tmp_path / "c.md", research_dir=tmp_path / "r")
    return issue_urls


def _research_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    monkeypatch.setattr(research, "repo_slug", lambda repo_root: REPO_SLUG)
    _isolation(monkeypatch, research.act, tmp_path)
    monkeypatch.setattr(research.draft, "run_research_draft", lambda **kw: PR_URL)
    result = research.run_research(research_dir=tmp_path / "r", repo_root=tmp_path,
                                   worktree_name="wt")
    return result["issue_urls"]


# (module, the children the dispose function runs BEFORE the gate — faked to
#  nothing, each returning the PR URL its real counterpart returns — the
#  dispose call, the whole-parent call)
PARENTS = [
    pytest.param(build, ("refine.run_refine", "refine_minor.run_refine_minor"),
                 _build_pass, _build_run, id="build"),
    pytest.param(build_minor, ("refine.run_refine_minor",), _build_minor_pass,
                 _build_minor_run, id="build_minor"),
    pytest.param(plan, ("plan_refine.run_plan_refine", "sprint.run_plan_sprint"),
                 _plan_pass, _plan_run, id="plan"),
    pytest.param(plan_project, (), _plan_project_pass, _plan_project_run,
                 id="plan_project"),
    pytest.param(research, ("verify.run_verify",), _research_pass, _research_run,
                 id="research"),
]


def _silence_children(monkeypatch: pytest.MonkeyPatch, module, children: tuple[str, ...]) -> None:
    for dotted in children:
        owner, name = dotted.split(".")
        monkeypatch.setattr(getattr(module, owner), name, lambda *a, **k: PR_URL)


@pytest.mark.parametrize("module, children, one_pass, whole_run", PARENTS)
def test_the_dispose_pass_CARRIES_the_reviewer_s_intakes_to_its_caller(
        module, children, one_pass, whole_run, monkeypatch: pytest.MonkeyPatch) -> None:
    """The boundary that dropped them: the dispose function returns a verdict
    and the URLs must leave through the accumulator beside the notes."""
    _silence_children(monkeypatch, module, children)
    _ci(monkeypatch, module, routing.CiVerdict.GREEN)
    passes = _reviewer_filing(monkeypatch, module, (INTAKE,))
    notes: list[str] = []
    issue_urls: list[str] = []

    verdict = one_pass(notes, issue_urls, correction=False)

    assert len(passes) == 1, "the reviewer did not run — the gate held before it"
    assert verdict.value == routing.Verdict.MERGE.value
    assert any("handed to the harvest" in n for n in notes), notes
    assert issue_urls == [INTAKE], (
        f"the reviewer returned {[INTAKE]} and the caller holds {issue_urls} — "
        f"the banner says 'handed to the harvest' and the harvest is handed nothing")


@pytest.mark.parametrize("module, children, one_pass, whole_run", PARENTS)
def test_a_LOOP_BACK_that_files_again_ACCUMULATES(
        module, children, one_pass, whole_run, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two passes, two intakes, both in the accumulator in the order filed.
    A pass that replaced the list would harvest only the last reviewer's."""
    _silence_children(monkeypatch, module, children)
    _ci(monkeypatch, module, routing.CiVerdict.GREEN)
    _reviewer_filing(monkeypatch, module, (INTAKE,), (SECOND,))
    notes: list[str] = []
    issue_urls: list[str] = []

    one_pass(notes, issue_urls, correction=False)
    one_pass(notes, issue_urls, correction=True)

    assert issue_urls == [INTAKE, SECOND]


@pytest.mark.parametrize("module, children, one_pass, whole_run", PARENTS)
def test_a_CI_HOLD_runs_no_reviewer_and_files_nothing(
        module, children, one_pass, whole_run, monkeypatch: pytest.MonkeyPatch) -> None:
    """The gate's arm: a red tree returns a HOLD before the reviewer, so the
    accumulator is untouched — not None, not a stale value, empty."""
    _silence_children(monkeypatch, module, children)
    _ci(monkeypatch, module, routing.CiVerdict.RED)
    passes = _reviewer_filing(monkeypatch, module, (INTAKE,))
    issue_urls: list[str] = []

    verdict = one_pass([], issue_urls, correction=False)

    assert passes == [], "a red tree reached the reviewer"
    assert verdict.value != routing.Verdict.MERGE.value
    assert issue_urls == []


# --- 1b. the outer return, all five parents --------------------------------------

@pytest.mark.parametrize("module, children, one_pass, whole_run", PARENTS)
def test_the_WHOLE_PARENT_returns_the_reviewer_s_intakes_on_its_result(
        module, children, one_pass, whole_run, monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path) -> None:
    """The line level 1 stops short of: the accumulator the dispose pass filled
    must be ON the value the parent returns, because that value is the only
    thing the entrypoint holds when it hands the harvest its refs. Level 1
    proves the list was filled; this proves the parent did not return without
    it — which two of the five shapes let it do with nothing red."""
    _silence_children(monkeypatch, module, children)
    _ci(monkeypatch, module, routing.CiVerdict.GREEN)
    passes = _reviewer_filing(monkeypatch, module, (INTAKE,))

    issue_urls = whole_run(monkeypatch, tmp_path)

    assert len(passes) == 1, "the reviewer did not run — the gate held before it"
    assert issue_urls == [INTAKE], (
        f"the reviewer returned {[INTAKE]}, the dispose pass carried it, and the "
        f"parent's RESULT holds {issue_urls} — the entrypoint harvests from the "
        f"result, so this is the line that hands the harvest nothing")


# --- 2. the real nesting: real `run_review` inside real `run_build` ---------------

def _block_only_intake(*urls: str) -> str:
    """The live shape: the block lists the intake, the printed line never
    reached the parent. `filed_intakes:` LAST, as `disposition.md` shows it."""
    return (_FakeWorkflow.DEFAULT_BLOCK + "  redispatched: false\n  filed_intakes:\n"
            + "".join(f"    - {u}\n" for u in urls))


def test_the_REAL_reviewer_s_block_only_cross_repo_intake_leaves_the_REAL_build_on_its_result(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`_FakeWorkflow` fakes the reviewer's I/O only — `run_review` parses the
    block, selects it by nonce, unions the two surfaces and builds its
    `ReviewResult` for real; `run_build` loops and disposes for real. What
    comes out the top is what `run_build.py` hands the harvest. The parent's
    collaborators are wired exactly as level 1b wires them, with the dispose
    children silenced and the gate green; nothing between them is faked."""
    _wire_build_parent(monkeypatch, tmp_path)
    _silence_children(monkeypatch, build, ("refine.run_refine", "refine_minor.run_refine_minor"))
    _ci(monkeypatch, build, routing.CiVerdict.GREEN)
    fake = _FakeWorkflow(_record(run_id="@ISSUED@"), "VERDICT: MERGE\n",
                         block=_block_only_intake(INTAKE), block_carries_nonce=True)
    fake.install(monkeypatch, tmp_path)

    result = build.run_build(BuildInput(description="the task"), tmp_path, "build-1")

    assert fake.ran, "the real reviewer never ran"
    assert result.verdict is BuildVerdict.MERGE
    assert any("(0 on the printed FILED-INTAKE line, 1 in the posted block" in n
               for n in result.notes), result.notes
    assert result.issue_urls == [INTAKE], (
        f"the reviewer's note reached the build's banner and its URL did not "
        f"reach the build's result: {result.issue_urls}")


# --- 3. the entrypoint, live: the body lands in the bag, or a gap does -----------

# One id per live test: the sandbox is session-wide, and a second run under
# the first's id would adopt the first's bag and read its events as its own.
RUN_ID_LANDS = "b" * 32
RUN_ID_GAPS = "c" * 32


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real repository for preflight; no `origin`, so `default_repo` is None
    and every ref the harvest reads must be a full URL — which they are."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("seed\n", encoding="utf-8")
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "t@example.com"],
                ["git", "config", "user.name", "t"],
                ["git", "add", "-A"],
                ["git", "commit", "-qm", "seed"]):
        subprocess.run(cmd, cwd=root, check=True, capture_output=True)
    return root


class _Gh:
    """`gh api` by endpoint: the PR and, unless withheld, the cross-repo issue."""

    def __init__(self, *, issue_readable: bool) -> None:
        self.issue_readable = issue_readable
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess:
        self.calls.append(list(args))
        endpoint = next((a for a in args if a.startswith("repos/") or a == "user"), "")
        if endpoint == "user":
            return _reply("fleet-bot\n")
        path = endpoint.split("?")[0]
        if "/comments" in path:
            return _reply("[]")
        if path == f"repos/{REPO_SLUG}/issues/67":
            return _reply(json.dumps(_surface(PR_URL, "the PR body")))
        if path == "repos/other-org/planning/issues/32" and self.issue_readable:
            return _reply(json.dumps(_surface(INTAKE, INTAKE_BODY)))
        return _reply(code=1, stderr=f"gh: Not Found (HTTP 404) {path}")


def _reply(stdout: str = "", code: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(["gh"], returncode=code, stdout=stdout, stderr=stderr)


def _surface(url: str, body: str) -> dict:
    return {"title": "a title", "body": body, "user": {"login": "fleet-bot"},
            "html_url": url, "created_at": "2026-09-14T01:45:00Z",
            "updated_at": "2026-09-14T01:45:00Z", "comments": 0}


def _run_live(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, repo: Path,
              journal_root: Path, gh: _Gh, run_id: str) -> tuple[int, Path]:
    """`run_build.main()` on the live path, its workflow returning what the
    real one returns for this shape, its `gh` answered by `gh`. The bag opens
    under `journal_root` — the session sandbox `conftest.py` points every
    entrypoint at by CONFIG, which is why no environment is set here."""
    monkeypatch.setattr(run_build, "run_build", lambda task, repo_root, name: BuildResult(
        pr_number="67", pr_url=PR_URL, verdict=BuildVerdict.MERGE,
        notes=["Filed 1 intake(s), handed to the harvest"], issue_urls=[INTAKE]))
    monkeypatch.setattr(harvest_activities, "gh_runner", lambda cwd: gh)
    (tmp_path / "task.md").write_text("the task\n", encoding="utf-8")
    code = run_build.main(["--task-file", str(tmp_path / "task.md"),
                           "--repo", str(repo), "--run-id", run_id])
    bag = journal_root / run_id
    assert bag.is_dir(), f"no bag at {bag}: the run opened its bag elsewhere"
    return code, bag


def _flags(bag: Path) -> dict[str, str]:
    return dict(read_tag_file(bag / "bag-info.txt"))


def _harvest_events(bag: Path) -> list:
    events = []
    for path in sorted((bag / "data").rglob(EVENTS_FILE)):
        events += [decode_event(line) for line in
                   path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return events


def test_LIVE_the_intake_s_body_lands_in_the_bag_with_the_issue_as_its_destination(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, repo: Path,
        _journal_root_is_never_the_operators: Path, capsys) -> None:
    """r1. The event the live bag was missing: destination = the issue URL,
    content = the body the reviewer authored, verbatim."""
    gh = _Gh(issue_readable=True)
    code, bag = _run_live(monkeypatch, tmp_path, repo,
                          _journal_root_is_never_the_operators, gh, RUN_ID_LANDS)

    assert code == 0
    assert any("repos/other-org/planning/issues/32" in a
               for call in gh.calls for a in call), (
        f"the harvest never asked for the intake: {gh.calls}")
    by_dest = {e.destination.address: e for e in _harvest_events(bag)
               if e.kind is EventKind.COMPLETION and e.write_path.endswith(":body")}
    assert INTAKE in by_dest, f"no body event for {INTAKE}; bodies harvested: {sorted(by_dest)}"
    assert by_dest[INTAKE].content == INTAKE_BODY
    assert PR_URL in by_dest, "the PR pair stopped being harvested"
    assert LABEL_INCOMPLETE not in _flags(bag)
    out = capsys.readouterr().out
    assert f"harvest: {INTAKE}" in out, out


def test_LIVE_an_intake_gh_cannot_read_leaves_a_TYPED_GAP_naming_it_and_marks_the_bag(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, repo: Path,
        _journal_root_is_never_the_operators: Path, capsys) -> None:
    """r5. The other half of NEVER NEITHER: the ref was handed over, the read
    failed, and the failure is a gap event whose destination is the issue —
    not a silent absence — with the bag `incomplete` and the PR still read."""
    gh = _Gh(issue_readable=False)
    code, bag = _run_live(monkeypatch, tmp_path, repo,
                          _journal_root_is_never_the_operators, gh, RUN_ID_GAPS)

    assert code == 0, "an unreadable intake must not fail a run whose PR is posted"
    gaps = [e for e in _harvest_events(bag) if e.kind is EventKind.GAP]
    assert [g.destination.address for g in gaps] == [INTAKE], (
        f"expected exactly one gap, for the intake: {[(g.destination.address, g.gap_class) for g in gaps]}")
    assert gaps[0].gap_class is GapClass.SURFACE_UNREADABLE
    assert gaps[0].content == "", "the reply's text reached the record"
    assert _flags(bag)[LABEL_INCOMPLETE] == "true"
    bodies = {e.destination.address for e in _harvest_events(bag)
              if e.kind is EventKind.COMPLETION and e.write_path.endswith(":body")}
    assert bodies == {PR_URL}, "the PR beside the unreadable intake was not harvested"
    out = capsys.readouterr().out
    assert f"harvest: {INTAKE} NOT READ" in out, out
