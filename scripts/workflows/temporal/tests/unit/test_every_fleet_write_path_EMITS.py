"""Requirement 1, wired: every inventoried fleet-code write path emits.

⚠ THE BAR IS REQUIREMENT 1'S OWN, AND IT IS NARROWER THAN THE HEADLINE. *"Every
write path to every store"* carries two readings an order of magnitude apart —
the envelope proven on one path, versus every path in the fleet — and the phase
doc states the bar precisely because the sibling component already paid for that
ambiguity at a measured factor of ten. **The bar is: the inventory is complete,
and every inventoried path emits.** So this file has two halves:

  * a CENSUS that fails when a store write appears with no emit beside it, which
    is what keeps the inventory complete; and
  * a BEHAVIOURAL test per inventoried path, which is what proves each emits.

THE CENSUS IS THE HALF THAT MATTERS AFTER THIS PHASE CLOSES. A snapshot goes
stale the first time a write path is added, and Phase 4's rebuild test is the
guard the phase doc names for that — this is the cheaper one that fires at
authoring time rather than at rebuild time. **It is not a substitute for Phase 4
and does not claim to be**: it can only see the shapes it enumerates, and a write
through a shape nobody listed is invisible to it exactly as it is to a grep.

⚠ AND IT REACHES FLEET-CODE WRITES ONLY. When the child itself runs
`gh pr comment`, there is no call site in this process at all — that half is
Phase 10's post-exit harvest, and nothing here can or should assert about it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.journal.bag import open_bag
from modules.journal.emit import Emitter, emitting_into
from modules.journal.events import EVENTS_FILE, EventKind, decode_event

MODULES = Path(__file__).resolve().parents[2] / "modules"

#: Requirement 9's fleet-code half, as `(module path, the write it performs)`.
#: ENUMERATED HERE AND NOWHERE ELSE in the test tree, so the phase doc's table
#: and this list are two renderings of one census rather than two lists.
FLEET_CODE_WRITE_PATHS: dict[str, str] = {
    "assistant/assistant_activities.py":
        "every `gh` mutation — pr create/comment/edit, issue create/comment/close",
    "assistant/tracked/tracked_items.py":
        "the four `tracked/` stores — file_item, expand, increment",
    "assistant/merge/merge_pr.py":
        "`gh pr merge`, which cannot go through the retrying choke point",
    "assistant/plan/plan_project/plan_project_activities.py":
        "the planning corpus — one research-pool synthesis seed",
}


def _emitter(tmp_path: Path) -> Emitter:
    root = tmp_path / "journal"
    root.mkdir(mode=0o700)
    return Emitter.for_run(open_bag(root, "run-1"), writer=None,
                           journal_root=root)


def _events(emitter: Emitter) -> list:
    path = emitter.writer_dir / EVENTS_FILE
    if not path.is_file():
        return []
    return [decode_event(line) for line
            in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# --- the census -------------------------------------------------------------

@pytest.mark.parametrize("relpath", sorted(FLEET_CODE_WRITE_PATHS))
def test_every_inventoried_module_BINDS_the_emit_boundary(relpath: str) -> None:
    """Each inventoried module imports the emit, asked of its IMPORTS.

    Not of its text: three of these four explain in prose why they emit, so a
    substring check would pass on a file that only talked about emitting.
    """
    source = (MODULES / relpath).read_text(encoding="utf-8")
    modules_named = [f"{'.' * n.level}{n.module or ''}"
                     for n in ast.walk(ast.parse(source))
                     if isinstance(n, ast.ImportFrom)]
    assert any(m.endswith("journal") or m.endswith("journal.events")
               for m in modules_named), (
        f"{relpath} is inventoried as a fleet-code write path and binds no "
        f"journal module. Either it emits, or it is no longer a write path and "
        f"belongs out of `FLEET_CODE_WRITE_PATHS` — a row for a module that "
        f"does not write is what makes the next reader trust the list without "
        f"checking it.")


def test_no_UNINVENTORIED_module_reaches_a_store_write_shape() -> None:
    """THE CENSUS. A store write with no emit beside it fails here.

    ⚠ THE SHAPE IS NAMED AND IT IS THE LIMIT OF THE CLAIM. This walks for ONE
    thing: a subprocess launched with `gh` as its first argv element, from a
    module not on the inventory. **It deliberately does NOT walk for a bare
    `write_text`** — the fleet writes prompts, temp files and worktree scratch
    that way, so that walk would be almost entirely false positives and would
    teach a reader to add exemptions rather than to stop reaching. It also does
    not see a write through `shutil`, through a shell string, or through any
    shape nobody listed.

    **So this is the cheap guard, not the complete one.** Phase 4's rebuild test
    is the guard for the class this cannot see — a write path nobody wrapped —
    and saying so here is what stops this file reading as a completeness proof.

    A NON-ZERO EXAMINED COUNT IS ASSERTED, because a walk that scoped itself
    wrongly reports a clean sweep over nothing.
    """
    examined = 0
    offenders: list[str] = []
    for path in sorted(MODULES.rglob("*.py")):
        if "journal" in path.parts:
            continue                    # the journal writes ITSELF; see below
        examined += 1
        relpath = str(path.relative_to(MODULES))
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            launches_gh = (
                node.args
                and isinstance(node.args[0], (ast.List, ast.Tuple))
                and node.args[0].elts
                and isinstance(node.args[0].elts[0], ast.Constant)
                and node.args[0].elts[0].value == "gh")
            if launches_gh and relpath not in FLEET_CODE_WRITE_PATHS:
                offenders.append(f"{relpath}:{node.lineno} launches `gh` directly")
    assert examined > 20, (
        f"the walk examined {examined} modules; a census over nothing proves "
        f"nothing about coverage")
    assert not offenders, (
        f"these launch `gh` outside an inventoried write path, so a mutation "
        f"through one would reach a store with nothing recording it: "
        f"{offenders}. Route it through `assistant_activities.gh_attempt`, or "
        f"add the module to `FLEET_CODE_WRITE_PATHS` with the emit it performs.")


def test_the_journal_package_is_EXCLUDED_from_the_census_deliberately() -> None:
    """It is the record, not a store, so its writes are not writes-to-a-store.

    Stated as a test rather than as a comment because the exclusion is the one
    line of this file a reader would suspect of hiding something: if the journal
    package could reach `gh`, the exclusion WOULD be hiding something.
    """
    offenders = [str(p) for p in (MODULES / "journal").rglob("*.py")
                 if '"gh"' in p.read_text(encoding="utf-8")]
    assert not offenders, (
        f"the journal package launches `gh`, so excluding it from the census "
        f"above hides a real write path: {offenders}")


# --- one behavioural test per inventoried path ------------------------------

def test_a_gh_MUTATION_emits_and_a_gh_READ_does_not(tmp_path: Path,
                                                    monkeypatch) -> None:
    """The discriminator that makes this assertion worth anything.

    Emitting on reads would put every `gh pr view` in the journal — thousands of
    events per run, and the completeness claim would drown in them. Emitting on
    neither would look identical to emitting on both in a test that only checked
    "some events exist".
    """
    from modules.assistant import assistant_activities as act

    class _Done:
        returncode, stdout, stderr = 0, "https://github.com/o/r/pull/1#c1\n", ""

    monkeypatch.setattr(act, "run_bounded", lambda *a, **k: _Done())
    emitter = _emitter(tmp_path)
    body = tmp_path / "comment.md"
    body.write_text("## Decision Log\n\nkept it whole.\n", encoding="utf-8")

    with emitting_into(emitter):
        act.gh_attempt(["pr", "view", "1", "--json", "state"], tmp_path)
        assert _events(emitter) == [], "a READ must not emit"

        act.gh_attempt(["pr", "comment", "1", "--body-file", str(body)], tmp_path)

    intent, done = _events(emitter)
    assert intent.kind is EventKind.INTENT and done.kind is EventKind.COMPLETION
    assert intent.write_path == "gh:pr:comment"
    assert intent.content == "## Decision Log\n\nkept it whole.\n", (
        "the `--body-file` was recorded as a PATH rather than read — a pointer "
        "to bytes outside the journal is not the verbatim content")
    assert done.destination.address == "https://github.com/o/r/pull/1#c1"


def test_a_gh_write_that_FAILS_records_a_store_write_failure(tmp_path: Path,
                                                             monkeypatch) -> None:
    """And `gh_attempt` still RETURNS the failure rather than raising it.

    Two callers depend on that contract — `gh issue list` degrading to a note,
    and `ci_verdict` classifying by parsing a non-zero `gh pr checks`. The raise
    exists only inside the closure, so `paired_write` can see the store write
    fail.
    """
    from modules.assistant import assistant_activities as act

    class _Failed:
        returncode, stdout, stderr = 1, "", "HTTP 422"

    monkeypatch.setattr(act, "run_bounded", lambda *a, **k: _Failed())
    emitter = _emitter(tmp_path)
    with emitting_into(emitter):
        result = act.gh_attempt(["pr", "comment", "1", "--body", "hi"], tmp_path)

    assert result.returncode == 1, "gh_attempt must not raise on a non-zero exit"
    assert [e.kind for e in _events(emitter)] == [
        EventKind.INTENT, EventKind.STORE_WRITE_FAILURE]


def test_a_tracked_item_FILING_emits(tmp_path: Path) -> None:
    from modules.assistant.tracked import tracked_items as ti

    emitter = _emitter(tmp_path)
    stores = tmp_path / "tracked"
    with emitting_into(emitter):
        ti.file_item(stores, ti.STORES["candidates"], title="a proposal",
                     filed_by="build-draft", status="open",
                     body="the reasoning")

    intent = _events(emitter)[0]
    assert intent.write_path == "tracked:candidates:file"
    assert intent.destination.store == "tracked_candidates"
    assert "the reasoning" in intent.content
    assert _events(emitter)[-1].destination.address.endswith(".md")


def test_a_tracked_item_INCREMENT_emits(tmp_path: Path) -> None:
    """`count` is the recurrence signal triage sorts on, so its write is a write."""
    from modules.assistant.tracked import tracked_items as ti

    stores = tmp_path / "tracked"
    path = ti.file_item(stores, ti.STORES["issues"], title="a defect",
                        filed_by="review-pr", status="open", body="what broke")
    emitter = _emitter(tmp_path)
    with emitting_into(emitter):
        assert ti.increment(path, "seen again on PR #300") == 2

    assert _events(emitter)[0].write_path == "tracked:issues:increment"


def test_a_research_pool_SEED_emits(tmp_path: Path) -> None:
    """The write that does not look like one — no `gh`, no `tracked/` item.

    That is the class requirement 9's enumeration exists to find.
    """
    from modules.assistant.plan.plan_project import plan_project_activities as ppa

    emitter = _emitter(tmp_path)
    seeded = tmp_path / "pool" / "synthesis.md"
    seeded.parent.mkdir(parents=True)
    with emitting_into(emitter):
        ppa._write_seed(seeded, "# synthesis\n\nnot yet researched\n")

    intent = _events(emitter)[0]
    assert intent.write_path == "planning:research-pool:seed"
    assert intent.destination.store == "planning_corpus"
    assert seeded.read_text(encoding="utf-8") == "# synthesis\n\nnot yet researched\n"


def test_a_write_path_OUTSIDE_a_run_still_performs_its_write(tmp_path: Path) -> None:
    """`current_emitter()` answers `None` for a helper script or a unit test.

    That is a real state and not an error — manufacturing an emitter would write
    a bag for a process that is not a run, under a `run_id` nobody minted. The
    STORE WRITE must still happen, or the emit rule would have broken every
    non-run caller in the fleet.
    """
    from modules.assistant.tracked import tracked_items as ti

    path = ti.file_item(tmp_path / "tracked", ti.STORES["issues"],
                        title="filed outside a run", filed_by="a test",
                        status="open", body="body")
    assert path.is_file() and "filed outside a run" in path.read_text()


def test_the_case_d_REPORT_is_the_one_write_that_does_not_emit(tmp_path: Path,
                                                               monkeypatch) -> None:
    """⚠ THE STATED EXCEPTION TO REQUIREMENT 1'S INVARIANT AND TO CASE (b).

    The durable report IS a store write, and case (b) says a store write does not
    happen unless its intent landed first — but in case (d) the journal is
    unwritable by definition, so the intent can never land. Read literally, this
    component's own ordering rule suppresses the only durable signal that the
    component is broken. A build that implements case (b) as an unconditional
    wrapper without this exception ships the failure path silently broken, which
    is exactly what this test exists to catch.
    """
    from modules.assistant import assistant_activities as act
    from modules.journal.emit import (UNWRITABLE_JOURNAL_MARKER,
                                      JournalUnwritable,
                                      unwritable_journal_report)

    class _Done:
        returncode, stdout, stderr = 0, "https://github.com/o/r/pull/1#c9\n", ""

    monkeypatch.setattr(act, "run_bounded", lambda *a, **k: _Done())
    emitter = _emitter(tmp_path)
    report = unwritable_journal_report(JournalUnwritable("root is gone"))
    line = f"{report['marker']}: {report['detail']}"

    with emitting_into(emitter):
        act.gh_attempt(["pr", "comment", "1", "--body", line], tmp_path)

    assert _events(emitter) == [], (
        "the case-(d) report emitted, which means a run whose journal is "
        "unwritable would fail to publish the report saying so")
    assert UNWRITABLE_JOURNAL_MARKER in line


def test_an_ORDINARY_comment_still_emits_so_the_exception_is_NARROW(
        tmp_path: Path, monkeypatch) -> None:
    """The discriminator for the exception above.

    Without it, a bug that skipped the emit for EVERY comment would pass that
    test — and the completeness claim would be false for the single most
    important surface this component records.
    """
    from modules.assistant import assistant_activities as act

    class _Done:
        returncode, stdout, stderr = 0, "https://github.com/o/r/pull/1#c9\n", ""

    monkeypatch.setattr(act, "run_bounded", lambda *a, **k: _Done())
    emitter = _emitter(tmp_path)
    with emitting_into(emitter):
        act.gh_attempt(["pr", "comment", "1", "--body", "an ordinary comment"],
                       tmp_path)
    assert len(_events(emitter)) == 2


def test_a_TRANSIENT_failure_on_a_WRITE_is_not_retried_and_emits_ONE_pair(
        tmp_path: Path, monkeypatch) -> None:
    """⚠ THIS TEST'S FIRST VERSION ASSERTED A RETRY AND THE FLEET DOES NOT RETRY
    WRITES — the correction is the finding, and it is a property worth pinning.

    `gh_attempt` refuses to repeat a mutation past a transient server-side
    failure: a 502 on a write may mean the write LANDED and only the reply was
    lost, and nothing in the reply distinguishes that from a write that never
    ran. So the risk the original test was written against — an emit inside the
    retry loop producing one intent per attempt, and three duplicate rows in a
    Phase 4 rebuild — is unreachable for writes by construction, and reachable
    only for reads, which do not emit at all.

    What IS assertable, and what this now asserts: one call produces exactly one
    intent and one `store_write_failure`, and the transient reply drove exactly
    one attempt.
    """
    from modules.assistant import assistant_activities as act

    attempts: list[int] = []

    def _transient(*_a, **_k):
        attempts.append(1)

        class _Reply:
            returncode, stdout, stderr = 1, "", "HTTP 503"
        return _Reply()

    monkeypatch.setattr(act, "run_bounded", _transient)
    emitter = _emitter(tmp_path)
    with emitting_into(emitter):
        act.gh_attempt(["issue", "create", "--title", "t", "--body", "b"],
                       tmp_path)

    assert attempts == [1], (
        "a mutation was repeated past a transient failure, which may apply the "
        "write twice")
    assert [e.kind for e in _events(emitter)] == [
        EventKind.INTENT, EventKind.STORE_WRITE_FAILURE]
