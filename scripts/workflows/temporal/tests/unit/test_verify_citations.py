"""Four outcomes, four exit codes, and a checker that never opens a socket.

THE DISTINCTIONS ARE THE PRODUCT. Requirement 3 names verified / missing /
tampered and requirement 4 splits span-missing out of them, because each has a
different remedy: re-capture the source, distrust the store, or correct the
claim. A verifier that returned one boolean would invite exactly the over-reading
the phase doc spends three paragraphs refusing.

OFFLINE IS ASSERTED STRUCTURALLY, NOT PROMISED. `test_the_verifier_reaches_no
_fetcher` walks the import graph, because a docstring saying "no network" is the
kind of claim that survives the module quietly gaining an import.

WHAT THIS FILE DOES NOT LOOK AT: it does not check the fetch policy at all
(`test_source_fetch.py`), and it takes the store's hashing as given
(`test_content_store.py`). It answers what a verdict MEANS and which number the
process exits with.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from modules.journal import verify as verifymod
from modules.journal.bag import open_bag
from modules.journal.citations import (CAPTURE_HARVEST, CAPTURE_READ_TIME,
                                       CITATIONS_FILE, Citation, new_citation,
                                       record_citation)
from modules.journal.content_activities import capture_fetched_source
from modules.journal.content_store import object_path, store_bytes
from modules.journal.verify import (EXIT_MISSING, EXIT_OK, EXIT_SPAN_MISSING,
                                    EXIT_TAMPERED, EXIT_USAGE, MISSING,
                                    SPAN_MISSING, TAMPERED, VERIFIED,
                                    exit_code_for, render_report, span_occurs_in,
                                    split_args, verify_bag, verify_citation)

PAGE = b"<p>The store proves the bytes, not the claim.</p>\n"
QUOTE = "The store proves the bytes, not the claim."


@pytest.fixture
def bag(root: Path):
    return open_bag(root, "run-verify")


def cite(bag, claim_id="c1", *, quote=QUOTE, stage="draft", data=PAGE,
         capture=CAPTURE_READ_TIME) -> Citation:
    digest = store_bytes(bag.path, data)
    citation = new_citation(claim_id=claim_id, stage=stage, quote=quote,
                            source_ref="https://example.org/a", capture=capture,
                            page_content_hash=digest)
    directory = bag.payload_dir / stage
    if not directory.is_dir():
        directory = bag.writer_dir(stage)
    record_citation(directory, citation)
    return citation


# --- the four outcomes ----------------------------------------------------------

def test_intact_bytes_holding_the_quote_are_VERIFIED(bag) -> None:
    citation = cite(bag)
    assert verify_citation(bag.path, citation).outcome == VERIFIED
    report = verify_bag(bag.path)
    assert report.ok and report.counts()[VERIFIED] == 1


def test_bytes_that_were_never_stored_are_MISSING(bag) -> None:
    """The check could not be MADE. That is a different fact from a failed check."""
    citation = cite(bag)
    object_path(bag.path, citation.page_content_hash).unlink()
    result = verify_citation(bag.path, citation)
    assert result.outcome == MISSING
    assert "MISSING" in result.detail


def test_bytes_that_no_longer_hash_to_their_name_are_TAMPERED(bag) -> None:
    """The STORE failed. The citation may be perfectly good, and the report says so."""
    citation = cite(bag)
    target = object_path(bag.path, citation.page_content_hash)
    data = bytearray(target.read_bytes())
    data[0] ^= 0x01
    target.write_bytes(bytes(data))
    assert verify_citation(bag.path, citation).outcome == TAMPERED


def test_an_ABSENT_QUOTE_over_INTACT_BYTES_is_its_own_outcome(bag) -> None:
    """REQUIREMENT 4, AND THE DISTINCTION IS THE WHOLE POINT OF IT.

    A source can change without invalidating a quote, and a quote can vanish
    from an UNCHANGED source only if the citation was wrong to begin with. That
    is an epistemic finding about the record, not an integrity finding about the
    store — so it must not share an exit code with an altered hash.
    """
    citation = cite(bag, quote="a sentence that was never on that page")
    result = verify_citation(bag.path, citation)
    assert result.outcome == SPAN_MISSING
    assert "the store is fine" in result.detail.lower()


def test_a_tampered_object_is_reported_as_TAMPERED_not_as_a_missing_span(bag) -> None:
    """ORDER OF THE TWO CHECKS IS THE DIAGNOSIS.

    Corrupting the stored bytes also destroys the quote in them. A verifier that
    looked for the span first would report a wrong citation when the real
    finding is a corrupt store — the diagnosis would point at the innocent half.
    """
    citation = cite(bag)
    object_path(bag.path, citation.page_content_hash).write_bytes(b"different entirely")
    assert verify_citation(bag.path, citation).outcome == TAMPERED


# --- the span check -------------------------------------------------------------

def test_a_quote_survives_its_source_being_RE_WRAPPED() -> None:
    """The overwhelmingly common shape of a quote copied out of rendered text."""
    assert span_occurs_in("one two three", b"one\n  two\tthree\n")


def test_a_quote_that_is_not_there_is_not_there() -> None:
    assert not span_occurs_in("four five", b"one two three")


def test_a_source_that_is_not_valid_utf8_still_gets_a_SPAN_ANSWER() -> None:
    """A decode failure reported as an integrity problem would be a wrong diagnosis."""
    assert span_occurs_in("hello", b"\xff\xfe hello \xff")


# --- requirement 6: code resolves from git ------------------------------------

def test_a_code_citation_resolves_from_the_repository(bag, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e",
           "HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}
    (repo / "f.py").write_text("def marked_function():\n    return 1\n")
    for args in (["init", "-q"], ["add", "f.py"], ["commit", "-qm", "x"]):
        subprocess.run(["git", *args], cwd=repo, env=env, check=True,
                       capture_output=True, timeout=30)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, env=env,
                         capture_output=True, text=True, check=True,
                         timeout=30).stdout.strip()

    citation = Citation(claim_id="c1", stage="draft", quote="def marked_function():",
                        source_ref=f"git:{sha}:f.py", capture=CAPTURE_READ_TIME)
    assert verify_citation(bag.path, citation, repo_root=repo).outcome == VERIFIED

    wrong = Citation(claim_id="c2", stage="draft", quote="def absent():",
                     source_ref=f"git:{sha}:f.py", capture=CAPTURE_READ_TIME)
    assert verify_citation(bag.path, wrong, repo_root=repo).outcome == SPAN_MISSING

    absent = Citation(claim_id="c3", stage="draft", quote="x",
                      source_ref=f"git:{'0' * 40}:f.py", capture=CAPTURE_READ_TIME)
    assert verify_citation(bag.path, absent, repo_root=repo).outcome == MISSING


def test_a_code_citation_with_no_repository_is_MISSING_and_says_why(bag) -> None:
    """Honest: this run could not make the check. Not that the check failed."""
    citation = Citation(claim_id="c1", stage="draft", quote="q",
                        source_ref=f"git:{'a' * 40}", capture=CAPTURE_READ_TIME)
    result = verify_citation(bag.path, citation)
    assert result.outcome == MISSING
    assert "repository" in result.detail


# --- exit codes -----------------------------------------------------------------

def test_each_outcome_class_has_its_own_exit_code(bag) -> None:
    """SIX, not five. `structural` shared 2 with usage and that made a real
    finding indistinguishable from a wrong invocation."""
    assert len({EXIT_OK, EXIT_MISSING, EXIT_TAMPERED, EXIT_SPAN_MISSING,
                EXIT_USAGE, verifymod.EXIT_STRUCTURAL}) == 6


def test_a_mixed_run_exits_on_the_MOST_SEVERE_outcome(bag) -> None:
    """Ordered by how much of the report the outcome invalidates.

    A tampered object means every other verdict in the same run is provisional;
    a missing one means one check could not be made; a span-missing is a
    complete, trustworthy check with a negative answer.
    """
    def report_with(*outcomes):
        results = tuple(verifymod.CitationResult(
            claim_id=f"c{i}", stage="s", outcome=o, capture=CAPTURE_READ_TIME,
            source_ref="https://example.org/a")
            for i, o in enumerate(outcomes))
        return verifymod.VerifyReport(path=bag.path, results=results)

    assert exit_code_for([report_with(VERIFIED)]) == EXIT_OK
    assert exit_code_for([report_with(VERIFIED, SPAN_MISSING)]) == EXIT_SPAN_MISSING
    assert exit_code_for([report_with(SPAN_MISSING, MISSING)]) == EXIT_MISSING
    assert exit_code_for([report_with(MISSING, TAMPERED)]) == EXIT_TAMPERED
    assert exit_code_for([report_with(SPAN_MISSING, MISSING, TAMPERED)]) == EXIT_TAMPERED


def test_an_unparseable_citation_file_is_STRUCTURAL_not_one_bad_claim(bag) -> None:
    """The record of what was claimed is unreadable — reporting it per-row would
    understate it, and `ok` must be False even with zero results.

    ⚠ THIS ASSERTED `EXIT_USAGE` AND THAT WAS THE DEFECT, NOT THE PIN. A record
    that cannot be read is a REAL FINDING and it exited with the number the
    entrypoint documents as "you invoked me wrong", so automation treating 2 as
    a usage error discarded it. `EXIT_STRUCTURAL` is its own code and outranks
    `tampered`, because an unreadable record means the citations were never
    enumerated at all.
    """
    writer = bag.writer_dir("draft")
    (writer / CITATIONS_FILE).write_text("{ not json\n")
    report = verify_bag(bag.path)
    assert report.structural and not report.ok
    assert report.worst == verifymod.STRUCTURAL
    assert exit_code_for([report]) == verifymod.EXIT_STRUCTURAL
    # AND IT OUTRANKS EVERY CITATION OUTCOME IN THE SAME RUN. A sweep holding
    # one unreadable record and one tampered object used to exit 2 and report
    # neither; the ranking is what makes the severest class decide.
    tampered_elsewhere = verifymod.VerifyReport(
        path=bag.path,
        results=(verifymod.CitationResult(
            claim_id="c9", stage="draft", outcome=TAMPERED, capture="harvest",
            source_ref="https://example.org/z"),))
    assert exit_code_for([report, tampered_elsewhere]) == verifymod.EXIT_STRUCTURAL


def test_a_bag_with_no_citations_is_not_a_failure(bag) -> None:
    """Most runs cite nothing. A checker that called them broken is unreadable."""
    report = verify_bag(bag.path)
    assert report.ok and report.results == ()
    assert exit_code_for([report]) == EXIT_OK


# --- the report -----------------------------------------------------------------

def test_the_report_prints_every_outcome_class_even_at_zero(bag) -> None:
    """A reader of `tampered: 0` learns something; a reader of an omitted line
    cannot tell zero from not-looked-for."""
    cite(bag)
    text = render_report(verify_bag(bag.path))
    for outcome in (VERIFIED, MISSING, TAMPERED, SPAN_MISSING):
        assert f"{outcome}:" in text
    assert "result     : PASS" in text


def test_the_report_names_the_CAPTURE_PROVENANCE_of_a_failing_row(bag) -> None:
    """r7(c)'s ruling surfaces in the output rather than in a global sentence.

    A harvested row's hash proves its bytes matched AT HARVEST, not that the
    claim was made against them. The verifier reports which, per row, so no
    result can over-claim.
    """
    cite(bag, quote="never on that page", capture=CAPTURE_HARVEST)
    text = render_report(verify_bag(bag.path))
    assert CAPTURE_HARVEST in text
    assert "result     : FAIL" in text


def test_the_report_exposes_the_evidence_set_hash_PER_STAGE(bag) -> None:
    """Requirement 5: computed and exposed. Nothing here routes on it."""
    cite(bag, "c1", stage="draft")
    cite(bag, "c2", stage="critic", data=b"a different source entirely",
         quote="different source")
    report = verify_bag(bag.path)
    assert set(report.evidence_hashes) == {"draft", "critic"}
    assert report.evidence_hashes["draft"] != report.evidence_hashes["critic"]
    assert "evidence_set_hash[draft]" in render_report(report)


def test_ok_is_DERIVED_and_cannot_be_constructed_to_disagree(bag) -> None:
    """A PASS printed above a tampered object is the worst thing a checker emits."""
    assert "ok" not in verifymod.VerifyReport.__dataclass_fields__
    assert isinstance(verifymod.VerifyReport.ok, property)


# --- offline is structural ------------------------------------------------------

def _intra_package_closure(start: str) -> set[str]:
    """Every module in this package `start` reaches, following relative imports.

    STATIC, AND THAT IS THE WHOLE POINT. A `sys.modules` check after importing
    `modules.journal.verify` measures the PACKAGE's `__init__`, which eagerly
    imports every submodule — so it reports the fetcher as reached no matter
    what `verify.py` itself does, and would keep reporting it after a genuine
    regression was fixed. Walking the import statements answers the question
    that matters: is there a path from `verify` to a module that can open a
    socket.
    """
    package = Path(verifymod.__file__).parent
    seen: set[str] = set()
    frontier = [start]
    while frontier:
        name = frontier.pop()
        if name in seen:
            continue
        seen.add(name)
        source = (package / f"{name}.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                if node.module:
                    frontier.append(node.module)
                else:
                    frontier.extend(alias.name for alias in node.names)
    return seen


def test_the_verifier_reaches_no_fetcher() -> None:
    """REQUIREMENT 2 AS A PROPERTY OF THE IMPORT GRAPH.

    `verify` resolves from the store alone, so nothing on its code path may be
    able to fetch. Asserted over the modules `verify` actually imports, because
    that is the code that runs when a citation is checked.

    ⚠ WHAT THIS DOES NOT LOOK AT, and it is the reason the first version of this
    test failed on a tree with no defect in it: the PACKAGE's `__init__` imports
    every submodule eagerly, so `import modules.journal.verify` does pull
    `urllib.request` into the process. That is an import, not a fetch — nothing
    on the resolve path calls it — and the property worth guarding is the code
    path rather than the process's module table. A run that wants the stronger
    property imports `modules.journal.verify` as a file rather than through the
    package, and the network-off demonstration is what proves the whole thing
    end to end regardless.
    """
    reached = _intra_package_closure("verify")
    assert "source_fetch" not in reached, (
        f"`verify` now reaches the fetcher. Its closure: {sorted(reached)}")
    assert "content_activities" not in reached, (
        "the activities module imports the fetcher, so reaching it reaches that")
    assert {"content_store", "citations", "bag"} <= reached, (
        f"the walk found {sorted(reached)} — a closure missing the modules "
        f"`verify` demonstrably uses means the walk read nothing and its "
        f"absence claim proves nothing")


def test_the_import_walk_can_SEE_a_fetcher_edge() -> None:
    """DISCRIMINATOR. The absence above is only evidence if a presence is visible.

    `content_activities` is the module that legitimately imports the fetcher, so
    its closure is the positive control — and it is a SEPARATE starting point
    rather than a mutation of `verify.py`, so the control cannot pass by
    breaking something the assertion would have caught by accident.
    """
    assert "source_fetch" in _intra_package_closure("content_activities")


# --- the argument grammar, which had two parses and one of them was wrong ------

def test_the_repo_flags_VALUE_is_not_mistaken_for_a_TARGET() -> None:
    """⚠ THE DEFECT THIS PINS SHIPPED IN THE ENTRYPOINT AND WAS FOUND BY RUNNING IT.

    `verify_citations.py` decides whether to fall back to the configured journal
    root by asking whether any target was named. It asked that with a filter over
    the raw argument list, which counted `--repo`'s own path as a target — so
    `verify_citations.py --repo <path>` printed a usage message instead of
    verifying the configured root. One grammar, written twice, and the second
    copy was wrong on arrival. `split_args` is now the only parse.
    """
    assert split_args(["--repo", "/r"]) == (Path("/r"), [])
    assert split_args(["--repo", "/r", "/bag"]) == (Path("/r"), ["/bag"])
    assert split_args(["/bag", "--repo", "/r"]) == (Path("/r"), ["/bag"])
    assert split_args(["/bag"]) == (None, ["/bag"])
    assert split_args([]) == (None, [])


def test_a_repo_flag_with_no_path_is_a_usage_error_not_a_crash() -> None:
    with pytest.raises(ValueError):
        split_args(["--repo"])


def test_the_entrypoint_and_the_module_share_ONE_parse() -> None:
    """The extraction is the fix; a second correct copy would decay the same way.

    ASSERTED OVER THE AST, NOT OVER THE TEXT. A substring check went red on the
    COMMENT explaining why the second parse was removed — which is a guard that
    forbids describing the defect it exists for. Docstrings are excluded for the
    same reason: the usage line legitimately names the flag.
    """
    path = Path(verifymod.__file__).parents[2] / "scripts" / "verify_citations.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                  if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
                  and node.body and isinstance(node.body[0], ast.Expr)
                  and isinstance(node.body[0].value, ast.Constant)}
    literals = [n for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and n.value == "--repo"
                and id(n) not in docstrings]
    assert not literals, (
        f"the entrypoint names `--repo` in code at line(s) "
        f"{[n.lineno for n in literals]} — that is a second parse of a grammar "
        f"`verify.split_args` owns, and the second copy is what shipped wrong")

    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "split_args"]
    assert calls, "the entrypoint no longer calls the shared parse at all"


# --- the outcome comes from the TYPE, and the sweep survives the bag ------------

def test_a_run_id_containing_the_word_TAMPERED_still_reports_MISSING(tmp_path) -> None:
    """⚠ THE CLASSIFIER READ THE MESSAGE, AND THE MESSAGE CARRIES THE RUN ID.

    `verify_citation` chose its outcome with `"TAMPERED" in str(exc)`. The
    `missing` message embeds `store_dir(bag_path)`, which embeds the run id, and
    `RUN_ID_PERMITTED` allows those letters — so a run named `TAMPERED-2026`
    reported every genuinely ABSENT object as a corrupted one: exit 4, and a
    verdict the module documents as "nothing else in the journal should be
    trusted". A legal run id silently inverted the store's own diagnosis.

    The remedy is that the outcome is a fact about WHAT FAILED and is carried by
    the exception type, so it cannot be undone by rewording a sentence.
    """
    from modules.journal.bag import DIR_MODE
    root = tmp_path / "journal"
    root.mkdir(mode=DIR_MODE)
    bag = open_bag(root, "TAMPERED-2026")
    citation = capture_fetched_source(
        bag=bag, stage="draft", claim_id="c1", quote="a quoted span",
        source_ref="https://example.org/a", data=b"a quoted span lives here")
    object_path(bag.path, citation.page_content_hash).unlink()

    report = verify_bag(bag.path)
    assert report.counts()[MISSING] == 1, (
        "an absent object was classified by reading a sentence that contains "
        f"the run id: {[ (r.outcome, r.detail) for r in report.results ]}")
    assert report.counts()[TAMPERED] == 0


def test_an_object_that_is_PRESENT_and_UNREADABLE_is_not_reported_as_MISSING(tmp_path) -> None:
    """`missing` MEANS "re-capture the source", WHICH IS DESTRUCTIVE ADVICE HERE.

    The third branch of `load_object` — a generic `OSError` from a permission
    failure, a failing disk, or a path that has become a directory — contained
    neither of the two words the old substring test looked for, so it fell
    through to `missing`. The bytes may be perfectly intact behind that error,
    and re-capturing would overwrite a record rather than repair it. It belongs
    in the class that means "the store is not currently to be trusted".
    """
    from modules.journal.bag import DIR_MODE
    root = tmp_path / "journal"
    root.mkdir(mode=DIR_MODE)
    bag = open_bag(root, "unreadable")
    citation = capture_fetched_source(
        bag=bag, stage="draft", claim_id="c1", quote="a quoted span",
        source_ref="https://example.org/a", data=b"a quoted span lives here")
    target = object_path(bag.path, citation.page_content_hash)
    target.unlink()
    target.mkdir()

    report = verify_bag(bag.path)
    assert report.counts()[TAMPERED] == 1
    assert report.counts()[MISSING] == 0


@pytest.mark.parametrize("wreck", ["non-utf8", "unreadable-file"])
def test_a_bag_that_cannot_be_READ_is_a_FINDING_not_a_raised_exception(tmp_path, wreck) -> None:
    """⚠ `verify_bag` CAUGHT ONLY `CitationError`, SO ONE BAD BAG KILLED THE SWEEP.

    `read_citations` reaches `read_text(encoding="utf-8")`, which raises
    `UnicodeDecodeError` (a `ValueError`) on non-UTF-8 bytes and `OSError` on a
    permission failure or a file that vanished between `rglob` and the read.
    Neither is a `CitationError`, so both propagated out of a whole-journal run
    and it reported nothing about any of the other bags.

    This is verbatim the regression `validate.py` records against ITSELF — "one
    such bag killed the whole sweep" — and the fix there was not carried across.
    """
    from modules.journal.bag import DIR_MODE
    root = tmp_path / "journal"
    root.mkdir(mode=DIR_MODE)
    broken = open_bag(root, "broken")
    writer = broken.writer_dir("draft")
    target = writer / CITATIONS_FILE
    if wreck == "non-utf8":
        target.write_bytes(b"\xff\xfe not utf-8 at all\n")
    else:
        target.write_text("{}\n")
        target.chmod(0o000)

    healthy = open_bag(root, "healthy")
    capture_fetched_source(bag=healthy, stage="draft", claim_id="ok",
                          quote="a quoted span",
                          source_ref="https://example.org/a",
                          data=b"a quoted span lives here")

    reports = [verify_bag(broken.path), verify_bag(healthy.path)]
    try:
        assert reports[0].structural and not reports[0].ok
        # THE OTHER BAG IS STILL REPORTED. That is the whole point: the sweep
        # continued, which is what an exception took away.
        assert reports[1].ok and len(reports[1].results) == 1
        assert exit_code_for(reports) == verifymod.EXIT_STRUCTURAL
    finally:
        if wreck == "unreadable-file":
            target.chmod(0o600)


def test_a_target_that_is_NOT_THERE_is_USAGE_and_not_a_structural_finding(tmp_path) -> None:
    """The two must stay separable, which is why `EXIT_STRUCTURAL` exists.

    A path the operator named that does not exist is a wrong invocation; a bag
    that exists and whose record cannot be read is a finding. Collapsing them is
    what put a real finding behind the usage code in the first place, and
    splitting the code without splitting these would just move the collapse.
    """
    assert verifymod.main([str(tmp_path / "no-such-directory")]) == EXIT_USAGE
