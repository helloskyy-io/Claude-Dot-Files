"""The PR-URL address — one declaration, host-anchored, and an IDENTITY check.

WHY THIS FILE EXISTS AS A CLASS GATE RATHER THAN AS THREE ASSERTIONS. Issue #34
is the precedent and it is the warning: `parse_verdict` was typed twice, the
issue NAMED BOTH COPIES, and it was closed with only one fixed — the survivor
being in the module whose comparator exists to notice channel divergence. The
PR-URL address arrived at Phase 4 in the same shape and one degree worse:

  * `assistant_activities.PR_URL` and `build/build_helper._PR_URL` were
    byte-identical ANCHORED copies;
  * `routing.pr_number_from_url` was `re.search(r"/pull/(\\d+)", url)` with NO
    host anchor at all, consumed by three parents;
  * `research_workflow` and `research_refresh_parent_workflow` each derived the
    number with `pr_url.rstrip("/").rsplit("/", 1)[-1]` — no validation of any
    kind. `phase4_fleet_migration.md` named ONE of those two, which is the same
    half-enumeration defect one layer up.

The host pin held only BY COMPOSITION: the anchored extractor ran first. So every
gate below is on the SHAPE across the tree, not on the five sites that were found.

AND ANCHORING IS NOT IDENTITY, which is the second half of this file.
`https://github\\.com/[^\\s)]+/pull/(\\d+)`'s `[^\\s)]+` IS the owner/repo
segment, so `https://github.com/someone-else/other-repo/pull/12` passes it and
yields `12` — a number then used against THIS dispatch's repo.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

from modules.assistant import assistant_activities as shared
from modules.assistant import routing
from modules.assistant.build import build_helper
from modules.assistant.plan import plan_activities

_MODULES = Path(routing.__file__).resolve().parents[1]      # …/modules
_TEMPORAL = Path(routing.__file__).resolve().parents[3]     # …/workflows/temporal
OWNER = Path(routing.__file__).resolve()


# ---------------------------------------------------------------------------
# One declaration, gated on the class.
# ---------------------------------------------------------------------------

# Names that PARSE a PR URL. A body for any of these outside `routing.py` is a
# second declaration whatever it is called locally.
_ADDRESS_FUNCTIONS = {"extract_pr_url", "pr_number_from_url", "pr_identity"}


def _v2_python_files() -> list[Path]:
    return sorted(p for p in _TEMPORAL.rglob("*.py")
                  if "tests" not in p.relative_to(_TEMPORAL).parts)


def test_the_pr_url_address_is_declared_exactly_once_in_the_whole_tree() -> None:
    """A `def` that parses a PR URL lives in `routing.py` and nowhere else.

    AST rather than a substring scan, for the reason the `parse_verdict` gate
    gives: `"def extract_pr_url" in text` matches a docstring, a comment, or a
    line of prose describing the defect — and three of the modules touched here
    contain exactly such prose now.
    """
    definitions: list[tuple[str, str]] = []
    scanned = 0
    for path in _v2_python_files():
        scanned += 1
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name in _ADDRESS_FUNCTIONS and path != OWNER:
                definitions.append((str(path.relative_to(_TEMPORAL)), node.name))

    assert scanned > 20, (
        f"the scan visited only {scanned} files under {_TEMPORAL} — the gate is "
        f"reporting on a tree it did not read"
    )
    assert definitions == [], (
        f"the PR-URL address is declared more than once: {definitions}. Its owner "
        f"is `routing.py`, which carries the host anchor and the owner/repo "
        f"capture; every other consumer re-exports. Issue #34 is what a second "
        f"body costs — it stays green in its own tests while the rule applied to "
        f"the owner never reaches it."
    )


def test_no_second_regex_in_the_tree_matches_a_pull_URL() -> None:
    """The pattern half of the same rule, and the one that actually drifted.

    Two of the three declarations were regexes rather than functions, and the
    third strength — no host anchor — was also a regex. This walks every
    `re.compile(...)` literal in the V2 tree.

    `COMPLETION_PATTERN` IS EXCLUDED BY NAME AND THAT IS NOT A LOOPHOLE. Those
    nine are an ERE handed to `grep -qE` inside `run-claude.sh` — a different
    contract on a different side of a process boundary, checked against this one
    by `test_the_completion_ERE_and_the_extractor_agree` below rather than
    merged into it.
    """
    offenders: list[str] = []
    for path in _v2_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and node.args
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "compile"):
                continue
            arg = node.args[0]
            if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                continue
            if "/pull/" in arg.value and path != OWNER:
                offenders.append(f"{path.relative_to(_TEMPORAL)}:{node.lineno} {arg.value!r}")
    assert offenders == [], (
        f"a second PR-URL regex is compiled outside routing.py: {offenders}. "
        f"Re-export `routing.PR_URL`; a copy is one edit from having a different "
        f"strength, which is exactly how the unanchored one survived."
    )


def test_every_consumer_of_the_pr_url_address_holds_the_OWNING_object() -> None:
    """Re-export, not re-implementation — the half an AST scan cannot see.

    A `lambda`, a `functools.partial` or a thin wrapper would satisfy the gates
    above and still be a second body. Identity is what makes "one declaration"
    mean the object rather than the name — FOR THE FUNCTIONS.

    AND IT DOES NOT MEAN THAT FOR THE PATTERN, which a mutation measured rather
    than a reading found. `re.compile` CACHES on `(pattern, flags)`, so replacing
    `PR_URL = routing.PR_URL` with a byte-identical `re.compile(...)` returns
    THE SAME OBJECT and this assertion stays green. Predicted two reds for that
    mutation; got one. So the pattern's one-declaration property is held by
    `test_no_second_regex_in_the_tree_matches_a_pull_URL` above and by nothing
    here, and the line below is a same-object statement rather than a guard.
    Recorded because an `is` assertion on a compiled pattern READS like the
    strongest check in the file and is the weakest.
    """
    assert shared.PR_URL is routing.PR_URL
    assert shared.extract_pr_url is routing.extract_pr_url
    assert build_helper.extract_pr_url is routing.extract_pr_url
    assert build_helper.pr_number_from_url is routing.pr_number_from_url
    assert build_helper.pr_identity is routing.pr_identity
    assert plan_activities.extract_pr_url is routing.extract_pr_url


# Every place in the V2 tree that takes a path segment off a string by splitting,
# with what it is splitting. THREE ad-hoc PR-URL parses used to be in this set —
# `research_workflow`, `research_refresh_parent_workflow` and
# `run_plan_project`'s completion banner — and `phase4_fleet_migration.md`
# enumerated ONE of the three. That is the same half-enumeration defect the
# address itself had, which is why the gate is an exact set over the SHAPE and
# not a list of the sites somebody found.
#
# ASSERTED AS AN EXACT SET, so it fails both when a new split appears and when a
# listed one goes away — a list that only grows is a gate that widens itself.
DECLARED_SPLITS = {
    ("resource_telemetry.py", "_read_anon"),         # a /proc line, not a URL
    # MOVED, not new: `plan_activities` -> `plan_project_activities` under §10.1
    # rule 3. Still a markdown heading's em-dash, still not a URL.
    ("plan_project_activities.py", "new_sprint_sections"),
    # git's own NUL-separated output under `-z`. A worktree path, not a URL, and
    # `-z` is what makes the split safe: it turns OFF the C-style quoting that
    # would otherwise put backslash escapes inside a path.
    #
    # THIS ENTRY REPLACED `sprint_files_touched`, which split a porcelain rename
    # line on `" -> "` and kept only the destination — so renaming `sprint.md`
    # AWAY produced a path matching nothing and the guard passed over it. The
    # rewrite uses `--no-renames`, so there is no arrow to parse at all.
    ("plan_activities.py", "worktree_state"),
}


def test_no_module_derives_a_path_segment_from_a_url_by_splitting() -> None:
    """The shape, not the two sites — `rsplit` on a URL is a parse with no check.

    `pr_url.rstrip("/").rsplit("/", 1)[-1]` returns the last segment of whatever
    it is handed: a bare sentence yields a word, and the word reaches `gh` as a
    PR number. It also cannot see the repository, so it is the weakest of the
    five declarations that existed and it was in the two workflows nobody
    enumerated.
    """
    found: set[tuple[str, str]] = set()
    sites: list[str] = []
    scanned = 0
    for path in _v2_python_files():
        scanned += 1
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        owner: dict[int, str] = {}
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for node in ast.walk(fn):
                    owner[id(node)] = fn.name
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in {"split", "rsplit"}:
                where = (path.name, owner.get(id(node), "<module>"))
                found.add(where)
                sites.append(f"{path.relative_to(_TEMPORAL)}:{node.lineno}")

    assert scanned > 20, f"the scan visited only {scanned} files — it read nothing"
    assert found == DECLARED_SPLITS, (
        f"string splitting moved. New sites: {sorted(found - DECLARED_SPLITS)}; "
        f"declared sites that are gone: {sorted(DECLARED_SPLITS - found)}. All "
        f"sites: {sites}. If it is a URL, use `routing.pr_identity`; if it is "
        f"not, add it here with what it splits — that edit IS the gate."
    )


# ---------------------------------------------------------------------------
# Capability parity — BOTH bounds, because a floor alone certifies a regression.
# ---------------------------------------------------------------------------

# The pattern this replaced, verbatim off `git show HEAD:…assistant_activities.py`.
_INCUMBENT = re.compile(r"https://github\.com/[^\s)]+/pull/(\d+)")

# URLs the fleet actually handles. Every one must survive the narrowing.
_REAL = [
    "https://github.com/helloskyy-io/Claude-Dot-Files/pull/78",
    "https://github.com/o/r/pull/1",
    "see https://github.com/o/r/pull/12 for context",
    "[the PR](https://github.com/o/r/pull/12)",
    "https://github.com/o/r/pull/12/files",
    "https://github.com/o-with-dash/r.with.dots/pull/9",
]


@pytest.mark.parametrize("text", _REAL)
def test_the_narrowed_pattern_accepts_EVERY_url_the_incumbent_accepted(text: str) -> None:
    """THE CEILING. A parity claim asserting only that the new path still fails
    closed passes while measuring the wrong thing; the other bound is that it
    does not fail closed on inputs the incumbent accepted.
    """
    assert _INCUMBENT.search(text), "fixture error: the incumbent rejected this"
    assert routing.extract_pr_url(text) is not None, text
    assert routing.pr_number_from_url(text, expected_repo=None) \
        == _INCUMBENT.search(text).group(1)


def test_the_narrowing_rejects_only_strings_that_are_not_pr_urls() -> None:
    """THE FLOOR, stated as what it costs rather than as what it protects.

    `[^\\s/)]+/[^\\s/)]+` is exactly two path segments, so a three-segment path is
    no longer matched. That IS a behaviour change from the incumbent and it is a
    declared parity line item: `github.com/a/b/c/pull/1` is not a PR URL, and
    accepting it was what let the owner/repo segment be unreadable.
    """
    assert _INCUMBENT.search("https://github.com/a/b/c/pull/1"), (
        "fixture error: this is the input the incumbent accepted"
    )
    assert routing.extract_pr_url("https://github.com/a/b/c/pull/1") is None


def test_the_number_is_never_taken_without_the_repo_being_visible() -> None:
    """The cross-repo shape parses, and parsing it exposes the repo it names.

    This is the whole distinction requirement 6 draws: the pattern was never
    wrong about the NUMBER. It was silent about WHOSE PR it was.
    """
    other = "https://github.com/someone-else/other-repo/pull/12"
    assert _INCUMBENT.search(other).group(1) == "12", (
        "fixture error: the incumbent yielded a usable number for this"
    )
    assert routing.pr_identity(other) == ("someone-else/other-repo", "12")


@pytest.mark.parametrize("text", [
    "", "no url here", "https://github.com/o/r/pull/", "/pull/12",
    "https://gitlab.com/o/r/pull/12", "http://github.com/o/r/pull/12",
])
def test_a_non_pr_url_raises_rather_than_yielding_a_number(text: str) -> None:
    """`/pull/12` is the one that matters: the unanchored parser accepted it.

    It is what `pr_number_from_url` matched before Phase 4, out of ANY string,
    with the host pin supplied only by whoever happened to call the anchored
    extractor first.
    """
    assert routing.extract_pr_url(text) is None
    with pytest.raises(ValueError):
        routing.pr_number_from_url(text, expected_repo=None)


# ---------------------------------------------------------------------------
# The repo half of the handoff — the derivation that actually reaches `gh`.
#
# R5b compares the TYPED record's `completion_ref`, which routes nothing else.
# The value that reaches `wait_for_ci`, `run_review` and `--pr` on a refine
# child is this one: a number taken out of a PRIOR CHILD'S STDOUT. Until Phase 4
# it was taken with the owner/repo half discarded, so a URL the child merely
# quoted from a comment yielded a number used against THIS repository — and R5b
# is structurally blind to it, because R5b's right-hand side is built FROM that
# number and would be compared against itself.
# ---------------------------------------------------------------------------


def test_a_url_naming_ANOTHER_REPOSITORY_is_refused_rather_than_yielding_a_number() -> None:
    """The threat, at the site where the number is live rather than inert."""
    other = "https://github.com/someone-else/other-repo/pull/12"
    with pytest.raises(ValueError, match="someone-else/other-repo"):
        routing.pr_number_from_url(other, expected_repo="helloskyy-io/Claude-Dot-Files")


def test_the_repo_check_does_not_reject_the_dispatch_s_OWN_pr() -> None:
    """THE CEILING. A guard that refuses everything satisfies the floor."""
    mine = "https://github.com/helloskyy-io/Claude-Dot-Files/pull/81"
    assert routing.pr_number_from_url(
        mine, expected_repo="helloskyy-io/Claude-Dot-Files") == "81"
    # And the shapes the parity audit measured still survive the extra check.
    assert routing.pr_number_from_url(
        "see https://github.com/o/r/pull/7/files for the diff",
        expected_repo="o/r") == "7"


def test_expected_repo_has_NO_default() -> None:
    """A keyword defaulting to None is a check that skips itself.

    Same discipline as `exit_record.route`'s `expected_ref`, and for the same
    reason: this is the parameter most likely to acquire a convenience default
    at the next call site.
    """
    param = inspect.signature(routing.pr_number_from_url).parameters["expected_repo"]
    assert param.default is inspect.Parameter.empty
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
    with pytest.raises(TypeError):
        routing.pr_number_from_url("https://github.com/o/r/pull/1")


def test_every_production_caller_of_pr_number_from_url_states_its_expected_repo() -> None:
    """THE GATE IS ON THE TREE, so a SEVENTH call site fails here.

    Six exist today and five pass a real slug read before their child ran. The
    sixth (`scripts/run_plan_project.py`) passes None and is allowed to, because
    `plan_project_workflow` already checked this exact string with the slug —
    which is why the allowance is a NAMED exception here and not a predicate
    anyone can satisfy by writing `None`.
    """
    tree_root = Path(routing.__file__).resolve().parents[2]     # …/temporal
    allowed_none = {"run_plan_project.py"}
    callers: list[str] = []
    scanned = 0
    for path in sorted(tree_root.rglob("*.py")):
        if "tests" in path.parts:
            continue
        scanned += 1
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(parsed):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "pr_number_from_url"):
                continue
            kwargs = {k.arg: k.value for k in node.keywords}
            assert "expected_repo" in kwargs, (
                f"{path.name}:{node.lineno} calls pr_number_from_url() without "
                f"stating an expected_repo — the number it returns reaches `gh` "
                f"against THIS repository, and the URL it came from is a child's"
            )
            value = kwargs["expected_repo"]
            if isinstance(value, ast.Constant) and value.value is None:
                assert path.name in allowed_none, (
                    f"{path.name}:{node.lineno} passes expected_repo=None. A "
                    f"parent that dispatched a child into a repository knows "
                    f"which one; passing None there is the pre-Phase-4 gap "
                    f"under a new name."
                )
            callers.append(f"{path.name}:{node.lineno}")

    assert scanned > 20, f"the scan visited only {scanned} files — it read nothing"
    assert len(callers) >= 6, f"the scan found only {callers} — it is not reading the tree"


# Where each parent reads its own repo slug, and the child call it must precede.
# `(module, enclosing function, the child dispatch it must come BEFORE)`.
_SLUG_BEFORE_CHILD = [
    ("review_pr/review_pr_workflow.py", "run_review", "run_disposition"),
    ("build/build/build_workflow.py", "run_build", "run_draft"),
    ("build/build_minor/build_minor_workflow.py", "run_build_minor", "run_draft_minor"),
    # The FIRST child, not merely A child. Since the triage split this parent
    # dispatches two producers, and `run_plan_sprint` is the second — naming it
    # here would leave the slug read unchecked against everything before it,
    # which is the entire window the ordering protects.
    ("plan/plan_project/plan_project_workflow.py", "run_plan_project", "run_triage_candidates"),
    ("research/research/research_workflow.py", "run_research", "run_write"),
    ("research/research_refresh_parent/research_refresh_parent_workflow.py",
     "run_research_refresh", "run_refresh"),
]


@pytest.mark.parametrize("module,function,child", _SLUG_BEFORE_CHILD)
def test_the_repo_slug_is_read_BEFORE_the_child_runs(
        module: str, function: str, child: str) -> None:
    """THE ORDERING IS THE FIX AND WITHOUT THIS IT IS UNGATED.

    `repo_slug` is a `gh` round trip on the path whose named failure mode is
    rate limiting. Read before the child, a `gh` failure costs a dispatch that
    has produced nothing. Read after, an unretried network call sits between a
    completed multi-hour child and the durable record of what it decided — and a
    transient 5xx destroys a review that already ran, already posted and already
    routed. `review_pr_workflow` shipped exactly that in the first cut of this
    phase, and it read as correct because the value is only USED afterwards.

    A line-order assertion is crude and it is what the property is: nothing
    about the value forces the ordering, so only its position can hold it.
    """
    path = _MODULES / "assistant" / module
    parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    func = next((n for n in ast.walk(parsed)
                 if isinstance(n, ast.FunctionDef) and n.name == function), None)
    assert func is not None, f"{module} no longer defines {function}()"

    def _lineno_of(name: str) -> int | None:
        # BOTH CALL SHAPES. Two of the six parents import `repo_slug` by name
        # (`from ...assistant_activities import repo_slug`) rather than through
        # a module alias, so an Attribute-only walk reported them as not reading
        # the slug at all — a gate that reds on conforming code, which is how a
        # gate gets deleted rather than fixed.
        for node in ast.walk(func):
            if not isinstance(node, ast.Call):
                continue
            called = node.func
            if (isinstance(called, ast.Attribute) and called.attr == name) \
                    or (isinstance(called, ast.Name) and called.id == name):
                return node.lineno
        return None

    slug_at = _lineno_of("repo_slug")
    child_at = _lineno_of(child)
    assert slug_at is not None, (
        f"{module}:{function} no longer reads its repo slug — the number it "
        f"takes out of a child's URL is then unchecked against this repository"
    )
    assert child_at is not None, f"fixture stale: {function} no longer calls {child}"
    assert slug_at < child_at, (
        f"{module}:{function} reads the repo slug at line {slug_at}, AFTER "
        f"dispatching {child} at line {child_at}. A `gh` failure there destroys "
        f"a child that already finished."
    )


# ---------------------------------------------------------------------------
# The completion ERE and the extractor must agree, or the gate admits a URL the
# parent cannot parse.
# ---------------------------------------------------------------------------

_COMPLETION_ASSIGN = re.compile(r"^COMPLETION_PATTERN\s*=\s*r?[\"'](.+?)[\"']\s*$", re.M)


def _declared_completion_patterns() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in _v2_python_files():
        for m in _COMPLETION_ASSIGN.finditer(path.read_text(encoding="utf-8")):
            out[str(path.relative_to(_TEMPORAL))] = m.group(1)
    return out


# The one V2 workflow whose completion contract is DELIBERATELY wider, with the
# reason. `plan-revision` has two terminal outcomes — a plan PR, or a STOP that
# files an issue and prints its URL as the final line — and `stages_1_to_5.md`
# makes the issue URL the STOP's completion signal in those words. Its workflow
# already resolves the two by POSITION (`_completion_url`), so the wider ERE is
# matched by a wider consumer rather than by a gate nobody widened.
# NO LITERALS REMAIN. Both completion EREs now live in `routing.py` beside the
# parser they must agree with: `PR_URL_COMPLETION_ERE` for the eight PR-only
# workflows and `PR_OR_ISSUE_COMPLETION_ERE` for `plan-revision`, whose STOP
# files an issue and prints its URL as the completion signal.
#
# THE ALTERNATION IS WHAT IS WIDER — THE PATH SEGMENTS ARE NOT, and getting that
# wrong is what this file exists to catch. `plan-revision` kept `[^ )]+` through
# the first fix pass, so its gate still accepted `…/a/b/c/pull/1` while the
# parent refused it; a completed run that opened its PR was reported as lost.
# The guard could not see it because the old exclusion filtered this workflow
# out of its own probes — an exemption that removed the one case left to check.
_WIDER_BY_DESIGN: dict[str, str] = {}


def _pr_only_completion_ere() -> str:
    """The single PR-only completion ERE, RESOLVED rather than scraped.

    It used to be scraped from source, which was correct while every workflow
    spelled its own — and nine of them spelled it `[^ )]+`, which spans `/` and
    accepted URLs `routing.PR_URL` refuses. There is now ONE declaration, beside
    the parser it must agree with, so this reads the value and the check below
    asserts no module has re-declared it. Scraping for a literal would silently
    find nothing the moment the duplication was fixed — which is exactly what
    it did.
    """
    literals = {k: v for k, v in _declared_completion_patterns().items()
                if "pull" in v and k not in _WIDER_BY_DESIGN}
    assert not literals, (
        f"a workflow re-declared the PR completion ERE as a literal instead of "
        f"referencing `routing.PR_URL_COMPLETION_ERE`: {literals}. Nine copies "
        f"diverged from the parser once already."
    )
    return routing.PR_URL_COMPLETION_ERE


def test_the_pr_url_completion_patterns_are_ONE_string_plus_ONE_declared_wider() -> None:
    """Nine workflows REFERENCE one PR-URL contract; the tenth declares a wider one.

    COLLAPSED INTO A SHARED CONSTANT ON 2026-08-11, REVERSING THIS TEST'S OWN
    EARLIER DECISION, and the reversal is recorded rather than quietly made.
    The previous version said a shared constant was "not this phase's scope" and
    that per-workflow declaration "is the shape `run-claude.sh`'s env-var
    interface expects". **The second half does not hold** — the value is passed
    as an env var either way, so referencing a constant changes nothing about
    that interface. And the cost of nine copies was paid the same day: they
    spelled `[^ )]+`, which spans `/`, so the completion gate accepted
    `…/a/b/c/pull/1` and the parent then refused it — a finished run reported as
    lost. The agreement guard that should have caught it was parametrized over
    two-segment inputs only and could not fail.

    So the copies are gone and `routing.PR_URL_COMPLETION_ERE` sits beside the
    parser it must agree with. What this test now asserts is that nobody
    re-declares it as a literal.

    THE NINTH IS DECLARED RATHER THAN EXCLUDED. `plan-revision` accepts an issue
    URL as well, because a STOP files an issue and that is its completion
    signal. Writing the test as "they are all identical" would have forced
    either a false claim or a silent skip, and this is the shape that makes the
    exception cost an edit here.
    """
    literals = {k: v for k, v in _declared_completion_patterns().items() if "pull" in v}

    assert literals == _WIDER_BY_DESIGN, (
        f"every PR-URL completion contract must reference "
        f"`routing.PR_URL_COMPLETION_ERE`, except the one declared wider. "
        f"Found these literals instead: {sorted(set(literals) - set(_WIDER_BY_DESIGN))}"
    )

    referencing = sorted(
        str(path.relative_to(_TEMPORAL))
        for path in _v2_python_files()
        if "COMPLETION_PATTERN = routing.PR_URL_COMPLETION_ERE" in path.read_text(encoding="utf-8")
    )
    # 10 since triage_candidates landed (2026-08-12), split out of plan-sprint;
    # 9 since research_write_minor (2026-08-11). This census is hand-maintained
    # ON PURPOSE: a new workflow that opens a PR must reference the shared
    # constant, and an edit here is how a human confirms it does rather than
    # having re-declared the literal that once cost a finished run. It fired on
    # exactly that event when triage_candidates was added, which is the census
    # working and not a chore.
    assert len(referencing) == 10, (
        f"expected 10 V2 workflows referencing the shared PR completion ERE, found "
        f"{len(referencing)}: {referencing}. The eleventh is plan-revision (wider, "
        f"declared above); the twelfth is review-pr, whose contract is `^VERDICT:`."
    )

# THE ADVERSARIAL HALF. The list was `_REAL` plus two negatives, and every entry
# was two-segment — so the test could not observe the one disagreement that
# actually existed, and passed while the defect shipped. A guard whose inputs
# cannot distinguish the behaviours is a guard that reports on nothing.
_STRUCTURAL_PROBES = [
    "https://github.com/a/b/c/pull/1",          # three path segments
    "https://github.com/a/b/c/d/pull/1",        # four
    "https://github.com/a/pull/1",              # one
    "https://github.com/a/b/pulls/1",           # wrong verb
    "https://github.com/a/b/pull/",             # no number
    "https://github.com/a/b/pull/1x",           # trailing junk on the number
]


@pytest.mark.parametrize("text", _STRUCTURAL_PROBES)
def test_the_WIDER_ere_is_wider_only_in_its_VERB(text: str) -> None:
    """`plan-revision`'s ERE accepts an extra verb, NOT an extra path shape.

    This is the case the previous guard exempted itself from checking, and the
    exemption is why a completed run was reported as lost. Every structural
    probe that the PR-only ERE refuses must also be refused here — the only
    permitted difference is `issues` alongside `pull`.
    """
    wide = routing.PR_OR_ISSUE_COMPLETION_ERE
    narrow = routing.PR_URL_COMPLETION_ERE
    assert bool(re.search(wide, text)) == bool(re.search(narrow, text)), (
        f"{text!r} is treated differently by the wider ERE, but the only "
        f"intended difference is the verb"
    )


def test_the_WIDER_ere_accepts_an_issue_url_and_the_narrow_one_does_not() -> None:
    """The one intended difference, asserted so the narrowing cannot eat it."""
    issue = "https://github.com/o/r/issues/12"
    assert re.search(routing.PR_OR_ISSUE_COMPLETION_ERE, issue)
    assert not re.search(routing.PR_URL_COMPLETION_ERE, issue)


@pytest.mark.parametrize("text", _REAL + ["no url here", "/pull/12"] + _STRUCTURAL_PROBES)
def test_the_completion_ERE_and_the_extractor_agree(text: str) -> None:
    """A gate that accepts what the parser cannot read is a gate that lies.

    `run-claude.sh` decides a run COMPLETED by grepping its final text for the
    ERE; the parent then extracts the URL from the same output with
    `routing.PR_URL`. If the two disagree, a run passes its completion contract
    and the parent raises "produced no PR URL" — a completed run reported as
    unfinished, or the reverse.

    The two spellings are not identical and cannot be: the ERE goes to `grep -E`,
    which has no `\\s`. What must hold is that they accept the same inputs.
    """
    ere = _pr_only_completion_ere()
    assert bool(re.search(ere, text)) == bool(routing.extract_pr_url(text)), (
        f"the completion ERE {ere!r} and `routing.PR_URL` disagree on {text!r}"
    )


# ---------------------------------------------------------------------------
# Requirement 3: the prompt's EMIT INSTRUCTION corresponds to the field the
# parent reads. For the nine deferred children that field is the PR URL on the
# final line, and the parent reads it through the completion gate.
# ---------------------------------------------------------------------------

_FINAL_LINE_URL = re.compile(r"URL.*FINAL line|FINAL line.*URL", re.IGNORECASE)


def _instruction_surface(workflow_file: Path) -> list[Path]:
    """Everything that can carry this workflow's emit instruction.

    SCOPED WIDER THAN `prompts/` ON PURPOSE, and the narrow version was wrong.
    A first cut of this check looked only in each workflow's `prompts/` folder
    and reported FOUR workflows — `plan-sprint`, `research-write`,
    `research-verify`, `research-refresh` — as gating on a PR URL they never
    ask for. They do ask: the instruction is CODE-BORNE, built by
    `<family>_activities.submit_prompt()` and interpolated as `${SUBMIT_PROMPT}`.
    A conformance check that cannot see half the prompt surface manufactures
    findings, which is worse than missing them.
    """
    package = workflow_file.parent
    family = package.parent
    return (sorted(package.rglob("*.md")) + sorted(package.glob("*.py"))
            + sorted(family.glob("*_activities.py")) + sorted(family.glob("*_helper.py")))


def test_every_workflow_gating_on_a_pr_url_ASKS_ITS_CHILD_FOR_ONE() -> None:
    """The gate and the instruction are two artifacts and nothing bound them.

    `COMPLETION_PATTERN` decides whether `exit 0` means finished; the prompt is
    what makes the child emit the thing it matches. Delete the instruction and
    the gate fails EVERY run of that workflow — loudly, but with a message about
    headless early-stop that names neither the prompt nor the missing line. Add
    a workflow with a copied `COMPLETION_PATTERN` and no instruction and it
    never completes at all.
    """
    missing: list[str] = []
    for rel in _declared_completion_patterns():
        if "pull" not in _declared_completion_patterns()[rel]:
            continue
        workflow_file = _TEMPORAL / rel
        if not any(_FINAL_LINE_URL.search(p.read_text(encoding="utf-8"))
                   for p in _instruction_surface(workflow_file)):
            missing.append(rel)
    assert missing == [], (
        f"these workflows gate on a PR URL and nothing in their prompt surface "
        f"asks the child to print one: {missing}"
    )


def test_the_instruction_check_can_actually_FAIL(tmp_path: Path) -> None:
    """Verified negative control — the surface scan must discriminate.

    A check that walks a tree can pass vacuously when its own scoping is wrong,
    and this one nearly did in the other direction. Here the predicate is run
    over a surface that carries no instruction, and it must come back negative.
    """
    (tmp_path / "family").mkdir()
    (tmp_path / "family" / "wf").mkdir()
    (tmp_path / "family" / "wf" / "wf_workflow.py").write_text("COMPLETION_PATTERN = 1\n")
    (tmp_path / "family" / "wf" / "notes.md").write_text("no instruction here\n")
    (tmp_path / "family" / "family_activities.py").write_text("x = 1\n")
    surface = _instruction_surface(tmp_path / "family" / "wf" / "wf_workflow.py")
    assert surface, "the scan found no files at all — it would pass vacuously"
    assert not any(_FINAL_LINE_URL.search(p.read_text()) for p in surface)
    # …and it goes positive the moment the instruction appears, in EITHER half.
    (tmp_path / "family" / "family_activities.py").write_text(
        'return "report its URL as your FINAL line"\n')
    assert any(_FINAL_LINE_URL.search(p.read_text())
               for p in _instruction_surface(tmp_path / "family" / "wf" / "wf_workflow.py"))
