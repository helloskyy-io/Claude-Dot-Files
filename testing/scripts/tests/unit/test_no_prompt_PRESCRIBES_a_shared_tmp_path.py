"""A prompt may not send every dispatch to the same file in a shared directory.

THE DEFECT CLASS. `/tmp` is shared by every dispatch on the machine. A prompt that
names a FIXED path there hands two concurrent runs one file, and the loser of the
race reads or publishes the winner's content — silently, with no error, because
both writes succeed.

MEASURED, TWICE, ON ONE NIGHT:

  * `/tmp/pr-comments.json` — PRESCRIBED by `fidelity_read_and_compare`, which
    `build_refine` and `build_refine_minor` load. 19 `build-refine*` runs on
    2026-08-19/20 produced **13 overlapping pairs**. The loser reviews another
    PR's comment history believing it is its own.
  * `/tmp/claude-pr-body.md` — only an EXAMPLE, in a re-read rule, and worse for
    it: the logs show that exact path copied **verbatim 133 times across 45
    runs**. An example in a prompt is a prescription in practice. This one
    PUBLISHES — the PR gets another PR's body.

WHY THE GUARD AND NOT CARE. The commit that fixed the class reintroduced it in
the same commit. Its sweep DETECTED on the bare path and REPLACED on a backticked
one, so it found four files, changed two, and reported four — and that count went
into the commit message as a completeness claim. Two prompts derived from shell
heredocs carry ESCAPED backticks (``\\`path\\```), which the replacement could not
express. `review-pr` found the two survivors; nothing in the suite could.

WHAT COUNTS AS SAFE. A path is per-dispatch when its name carries something that
differs between concurrent runs — `${PR_NUMBER}`, `$$`, a branch, a timestamp.
`review_pr`'s own `/tmp/claude-review-pr-${PR_NUMBER}-<ts>.md` is the shape to
copy, and is why reviews were never exposed to this and can run concurrently.

WHAT THIS DOES NOT LOOK AT:
  * Paths built at runtime in Python. This reads PROMPTS — the instructions a
    model follows — not the fleet's own file handling.
  * Whether a per-dispatch name is actually unique. `${PR_NUMBER}` collides
    between two runs on the SAME PR; that is a different and much rarer race.
  * Directories other than `/tmp`. A repo-relative scratch path is not shared
    between machines and is not this class.
  * A prescribed shared file with NO EXTENSION — a lock, a marker, a pid file.
    `TMP_PATH` anchors on an extension because that is what separates a path
    from a bare directory mention, so `/tmp/claude-lock` reads as no match. That
    is a real hole in the same class, deliberately left open rather than traded
    for false positives on every `/tmp` mention. Nothing in the tree exploits it.
  * `docs/`. It is INVENTORIED below, not enforced — see `DOCS_RESIDUE`.
  * A path a file EXPLAINS rather than prescribes. `EXPLANATORY` forgives one,
    and it is the ONLY way past this guard, so it is stated here rather than
    left for a reader to find in the predicate. It was once path-keyed and
    global: `/tmp/pr-comments.json` — the path whose collision this module
    exists for — was exempt on every walked surface, so a full regression of
    `fidelity_read_and_compare` read clean. An exemption is now no wider than
    the judgement that earned it, in all three dimensions it was wider in: the
    FILE, the PROSE, and the COUNT. See `EXPLANATORY`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import pytest

REPO = Path(__file__).resolve().parents[4]

import sys as _s  # noqa: E402
_s.path.insert(0, str(REPO / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import PLANNING_ROOT  # noqa: E402

import sys as _cg_sys  # noqa: E402
from pathlib import Path as _cg_Path  # noqa: E402
_cg_sys.path.insert(0, str(_cg_Path(__file__).resolve().parents[4]
                           / "scripts" / "workflows" / "temporal" / "tests"))
from planning_corpus import require_planning_corpus  # noqa: E402


# EVERY SURFACE THAT PRESCRIBES A PATH TO SOMEONE, not only the prompts a model
# reads. The first version of this guard walked `modules/assistant` alone, and
# `review-pr` immediately found the class still live on the two surfaces it
# excluded: `run_plan_revision.py`'s `--help` example and the
# `workflow-dispatch` skill both showed `--task-file /tmp/context.md`. An
# OPERATOR copying that from help text collides exactly as a model does, and on
# a machine this PR measures at 19 dispatches in one night.
SURFACES = (
    REPO / "scripts" / "workflows" / "temporal" / "modules" / "assistant",
    REPO / "scripts" / "workflows" / "temporal" / "scripts",
    REPO / "config" / "skills",
    REPO / "config" / "commands",
)
SUFFIXES = (".md", ".py", ".sh")

# A `/tmp` path with a file extension. The extension is what separates a PATH
# from a bare directory mention — `/tmp` alone, or `/tmp/claude-1000/...` as a
# scratch ROOT, is not a prescription to write one named file.
#
# `/` IS IN THE CHARACTER CLASS, AND THE FIRST VERSION LEFT IT OUT. Without it
# the pattern stopped at the first slash, so `/tmp/claude-scratch/output.json` —
# a fixed directory holding a fixed file, the same collision one level down —
# read as no match at all. Found by mutation, not by reading: the module's
# controls all used flat paths, so every one of them passed over the hole.
TMP_PATH = re.compile(r"/tmp/[A-Za-z0-9_.${}<>/-]*\.[a-z]{2,5}")

# What makes a name differ between two concurrent dispatches: a PLACEHOLDER, of
# any spelling. This is a SHAPE and it used to be a list of literal spellings —
# `("${PR_NUMBER}", "$$", "<branch>", "<ts>", "<timestamp>", "${RUN_ID}",
# "<name>", "{pr}")` — matched with `tok in m`.
#
# WHY THAT CHANGED, AND IT IS THE SAME LESSON AS THE `/` ABOVE. A spelling list
# closes the spellings someone thought of. This repo's own `terminal-output.md`
# sanctions a SECOND spelling of the identical per-task concept —
# `/tmp/claude-<descriptive-name>.sh` — and `"<name>" in "<descriptive-name>"`
# is False, because the substring needs `<` immediately before `name`. A prompt
# author following that half of the convention would have been failed by CI for
# a path with no collision risk, and the cheapest way out is to copy `<name>`
# rather than write what they meant. Keying on the shape ends that class:
# `<run-id>`, `<pr>`, `<slug>` and every spelling nobody has written yet are
# per-dispatch without an edit here.
PER_DISPATCH = re.compile(
    r"<[^<>/]+>"      # a prompt/doc placeholder: <branch>, <ts>, <descriptive-name>
    r"|\$\{[^}]+\}"   # a shell variable: ${PR_NUMBER}, ${RUN_ID}
    r"|\{[^{}/]+\}"   # a Python `.format()` field: `PR_RUNWAY_TASK` uses `{pr}`
    r"|\$\$"          # the shell's own pid
)

# Shown in the failure message. These ILLUSTRATE; `PER_DISPATCH` DECIDES — and
# the test below asserts every one of them is still accepted by it, so an
# example can never drift out of the shape it is teaching.
PER_DISPATCH_EXAMPLES = ("${PR_NUMBER}", "$$", "<branch>", "<ts>", "<name>", "{pr}")

# THE REPLACEMENT SHAPE THE FAILURE MESSAGE TELLS AN AUTHOR TO COPY. It is a
# constant, and asserted below, because a REMEDY that names a path in the class
# it is remedying is a defect of its own — and one that reads as authoritative,
# since it arrives attached to the check. That is not hypothetical: issue #137's
# step 1 prescribed `/tmp/claude-build-task.md`, a filled-in constant this very
# predicate flags, and whoever executed it would have edited two live docs into
# the class while every gate stayed green. This is the same shape on the surface
# a test CAN reach.
SHAPE_TO_COPY = "/tmp/claude-review-pr-${PR_NUMBER}-<ts>.md"


class Exemption(NamedTuple):
    """What a file may say about a fixed `/tmp` path without being told off.

    `anchor` is the prose that EARNS the exemption and `occurrences` is how many
    times that file may name the path. Both are part of the exemption's SCOPE,
    not documentation of it — see `_fixed_paths`.
    """
    anchor: str
    occurrences: int
    reason: str


# A path named only to EXPLAIN the defect — prose about the old fixed form, not
# an instruction to use it. Each entry states why, because an exemption without
# a reason is how this list grows until the guard means nothing.
#
# KEYED ON `(file, path)`, PINNED TO PROSE AND TO A COUNT — AND IT SHIPPED AS A
# BARE `{path: reason}` APPLIED EVERYWHERE. That is the defect this module was
# built to catch, living inside the module: `/tmp/pr-comments.json` is the path
# whose collision produced the 13 overlapping pairs, and it was exempt on every
# walked surface. Measured, all three arms:
#
#   * ANOTHER FILE. Any of the four walked surfaces could PRESCRIBE any of these
#     three paths and `_fixed_paths` returned `[]`, while an unlisted path in the
#     same position was flagged — so the exemption was the only thing suppressing
#     it. The FILE key closes this.
#   * THE PROSE GONE. Reverting `fidelity_read_and_compare`'s instruction to the
#     fixed path AND deleting the explaining sentence — the "a later editor
#     tidies away the redundant warning" scenario the PR body names as the reason
#     that prose exists — still read clean, because the exemption did not depend
#     on the explanation. FILE-scoping alone does NOT close this one: the
#     regression is IN the file that earned the exemption. `anchor` closes it.
#   * ONE MORE OCCURRENCE. A prescription added BESIDE the surviving explanation
#     is the same path in the same file, so neither of the above sees it.
#     `occurrences` closes it.
#
# `test_every_EXEMPTION_is_still_present_and_still_explanatory` did not close any
# of the three: it asserted the path appeared SOMEWHERE in the corpus, which a
# prescription satisfies exactly as well as an explanation. Its own docstring
# named the failure mode — "exempt by inheritance" — and closed only the case
# where the prose vanishes entirely.
#
# THE SHAPE IS BORROWED, NOT INVENTED. `test_convergence`'s `REPORTING_ONLY` keys
# its exemptions `(file, function)` — the granularity of the judgement — and that
# is the exemplar this now follows.
#
# ROOT CAUSE, AND IT IS WHY THE KEY CHANGED RATHER THAN THE ENTRIES: an exemption
# granted at a coarser scope than the judgement that earned it. Every reason below
# already named its file, its prose and its single occurrence — in prose, where
# nothing enforced them. A new entry cannot now be written without stating all
# three, so the next member of this class fails to be expressible rather than
# waiting to be found.
EXPLANATORY: dict[tuple[str, str], Exemption] = {
    ("scripts/workflows/temporal/modules/assistant/prompts/fidelity_read_and_compare.md",
     "/tmp/pr-comments.json"): Exemption(
        "THE FILENAME CARRIES THE PR NUMBER because this path is shared by every "
        "concurrent dispatch.",
        1,
        "named in `fidelity_read_and_compare`'s own warning about why the "
        "filename carries ${PR_NUMBER}. The INSTRUCTION beside it is already "
        "per-dispatch; removing the prose would delete the reason.",
    ),
    ("scripts/workflows/temporal/modules/assistant/build/build_activities.py",
     "/tmp/shared/notes.md"): Exemption(
        "which is not a sibling of the repo",
        1,
        "the WORKED EXAMPLE in `build_activities`'s docstring for why an escaping "
        "relative argument is rendered as its resolved absolute path — it is the "
        "path the fleet would WRONGLY have opened. Nothing writes it.",
    ),
    ("scripts/workflows/temporal/scripts/run_plan_sprint.py",
     "/tmp/x/candidates.md"): Exemption(
        "was handed to the prompt, and was read and written by a run executing under",
        1,
        "the tail of the traversal string `../../../../tmp/x/candidates.md` that "
        "`run_plan_sprint`'s comment records as having escaped an `.exists()` "
        "check. It is the attack that was demonstrated, not a path to use.",
    ),
}


# `ids` FOR BOTH `EXPLANATORY` PARAMETRIZATIONS, AS A LIST AND NOT A CALLABLE.
# A callable is invoked once per ARGNAME, not once per paramset — so it was
# handed the `Exemption` as well as the key, and `Exemption` is a NamedTuple,
# hence a `tuple`, so an `isinstance(k, tuple)` guard did not discriminate them.
# `k[0]` on the exemption is its ANCHOR, and every test id carried a full
# sentence of prose. Confirmed by `--collect-only`, not reasoned. The list form
# is applied once per paramset and cannot see the values at all.
EXEMPTION_IDS = [f.split("/")[-1] for f, _ in EXPLANATORY]


class Residue(NamedTuple):
    """One `docs/` file's fixed `/tmp` paths, and the judgement recorded on them."""

    paths: frozenset[str]
    reason: str


# THE SAME CLASS, ONE SURFACE OVER, RECORDED RATHER THAN ENFORCED.
#
# `docs/` is not in `SURFACES` and this entry does not put it there: nothing in
# `docs/` has to change for the suite to stay green. What the test below asserts
# is that this INVENTORY still matches the tree, PATH BY PATH — so a NEW shared
# path in `docs/` fails here instead of being found by a later review pass, even
# when the file it lands in is already recorded, and a FIXED one forces this
# record to be updated at the moment the work is done.
#
# THE `paths` FIELD IS WHY, AND THE RECORD SHIPPED WITHOUT IT. This was a
# `{file: reason}` mapping compared on its KEY SET, while three surfaces — this
# comment, `docs/file_structure.txt` and #137 — all said a new path in `docs/`
# would fail here. Measured, both arms: appending a fixed `/tmp` path to an
# UNRECORDED file redded the inventory; appending the identical line to a file
# already in this record left the suite green. The producing pass ran only the
# first arm. The two fix-class files are precisely the ones #137 exists to get
# edited, so the blind window was the window where someone is editing them.
# Recording the PATHS rather than the filenames is what makes the claim true,
# and it is a class fix rather than a spelling fix: the comparison now keys on
# the granularity of the thing being judged, so no future entry can reopen it.
#
# WHY AN INVENTORY IN THE TREE AND NOT A LIST IN THE ISSUE. #137 recorded this
# residue by hand, from a `--task-file`-shaped search, and therefore named the
# two files that carried `--task-file` out of the seven that carry the class. A
# hand-written enumeration of a class is stale the moment the tree moves, and
# nothing tells anyone. This one is derived from the guard's own predicate on
# every run.
#
# EACH ENTRY SAYS WHICH KIND IT IS, because "add `docs/` to SURFACES" is NOT a
# one-line remedy: NONE of these is fix-class any more — the last one,
# `workflow-scripts.md`'s `--task-file /tmp/task.md`, was fixed under human
# review on 2026-08-24 and its entry dropped, which closed #137. What is left
# is five entries the mechanical predicate cannot tell from a defect: records
# of the past, a quote of a third party's docs, an illustration of a REJECTED
# approach, and a vendored mirror this repo may not edit. They are INVENTORIED
# so a NEW one is visible, and deliberately NOT enforced — enforcement here
# would need five exemptions for prose, which is how an exemption list grows
# until the guard means nothing.
#
# DO NOT RETYPE THE `paths` SETS. They are the output of `_fixed_paths` over
# `git ls-files docs`, and the test below is what reconciles them.
DOCS_RESIDUE: dict[str, Residue] = {
    "standards/temporal/worker_deployment_standard.md": Residue(
        frozenset({"/tmp/claude-deploy-new-workers.sh"}),
        "NOT FIX-CLASS, and this is the entry that makes the remedy non-mechanical. "
        "Two reasons, and NEITHER is 'it conforms to the naming convention' — that "
        "was this entry's stated reason for one revision and it is the wrong test. "
        "`/tmp/claude-deploy-new-workers.sh` is a filled-in constant: it carries no "
        "placeholder, so two concurrent dispatches DO collide on it, and the control "
        "below asserts the predicate still flags it. Following the naming convention "
        "and differing between concurrent dispatches are different properties, and "
        "conflating them is what put a path from this very class into #137's own "
        "remedy. The reasons the line stays: (1) the file is a vendored MIRROR this "
        "repo may not edit; (2) the line is a SHAPE-REFERENCE inside a standard's "
        "prose rather than an instruction a dispatch copies — the `EXPLANATORY` "
        "shape. The inventory records a human judgement the predicate cannot make; "
        "that is why the two verdicts differ without contradicting.",
    ),
    "guide/claude_code_orchestration.md": Residue(
        frozenset({"/tmp/workflow/plan.md", "/tmp/workflow/plan-v2.md",
                   "/tmp/workflow/security.md"}),
        "NOT FIX-CLASS. `/tmp/workflow/*.md` inside a hypothetical `plan-draft.sh` "
        "in an options comparison, and principle 4 of the same document explicitly "
        "retires the pattern: 'The original said `/tmp/workflow/*.md`… the handoff "
        "between stages is the PR'. Illustration of a rejected approach.",
    ),
    "development/common/reviews/review-skyy-command-2026-07-24.md": Residue(
        frozenset({"/tmp/claude-pr-body.md"}),
        "NOT FIX-CLASS. A dated review recording that `/tmp/claude-pr-body.md` was "
        "the file 43% of read-before-Edit failures concentrated on. A record of "
        "what happened, which is the `EXPLANATORY` shape.",
    ),
    "development/common/reviews/review-mdc-master-planning-2026-05-03.md": Residue(
        frozenset({"/tmp/claude-migration-sprint1.sed"}),
        "NOT FIX-CLASS. A dated review quoting the `sed` invocation that was run. "
        "A record of what happened.",
    ),
    "standards/architecture/research/raw/code_routed_control_flow.md": Residue(
        frozenset({"/tmp/argo_arg_N.txt"}),
        "NOT FIX-CLASS. Quotes Argo's own documentation (`@/tmp/argo_arg_N.txt`) "
        "while describing a third-party tool's parameter passing. Not ours to "
        "prescribe or to fix.",
    ),
}

# The rule whose scope decides whether a `DOCS_RESIDUE` entry may be DEFERRED to
# a human-reviewed edit rather than fixed on the spot. Read, not copied — see
# `test_no_RESIDUE_ENTRY_defers_behind_a_GATE_THAT_DOES_NOT_REACH_IT`.
GOVERNANCE_RULE = REPO / "config" / "rules" / "standards-governance.md"


def _prompts() -> list[Path]:
    found = sorted(f for root in SURFACES for f in root.rglob("*")
                   if f.is_file() and f.suffix in SUFFIXES)
    assert len(found) > 40, (
        f"only {len(found)} files found across {[str(s) for s in SURFACES]} — the "
        f"walk is wrong and every assertion below would pass vacuously")
    return found


def _mentions(text: str, path: str) -> int:
    """How many times `text` names exactly `path`, AS THE DETECTOR SEES IT.

    Not `text.count(path)`. A longer path that merely STARTS with `path` —
    `/tmp/pr-comments.json.bak` — is a DIFFERENT path, and `TMP_PATH` matches it
    whole; a substring count charges it against `path`'s exemption and reds a
    file that has not regressed. It cannot let a prescription through either: a
    mention this does not count is one the main filter has already flagged under
    its own name.
    """
    return TMP_PATH.findall(text).count(path)


def _fixed_paths(text: str, source: str = "") -> list[str]:
    """`/tmp` paths in `text` whose names cannot differ between two dispatches.

    `source` is the repo-relative file `text` came from, and it is what makes an
    `EXPLANATORY` entry apply. The exemption is recomputed FROM `text` on every
    call rather than read off the table, so it lapses the moment the prose that
    earned it goes or the file starts saying the path more often than the entry
    allows. DEFAULTING TO `""` IS DELIBERATE: a caller that does not say where
    the text came from — every synthetic control below — gets no exemptions at
    all, which is the strict reading and cannot mask a shape bug.
    """
    exempt = {path for (f, path), e in EXPLANATORY.items()
              if f == source and e.anchor in text
              and _mentions(text, path) == e.occurrences}
    return [m for m in TMP_PATH.findall(text)
            if not PER_DISPATCH.search(m)
            and m not in exempt]


def _residue_under(docs: Path, base: Path) -> dict[str, set[str]]:
    """`{path relative to `base` -> its fixed `/tmp` paths}` for every file under `docs`.

    Takes its root as an argument so the control below can run it over a
    synthetic tree. A helper hard-wired to `REPO` would have forced the control
    to mutate the real `docs/` — which is how the arm that mattered went unrun
    the first time.
    """
    found: dict[str, set[str]] = {}
    for f in sorted(docs.rglob("*")):
        if not (f.is_file() and f.suffix in SUFFIXES):
            continue
        # NO `source` — the `docs/` inventory takes no exemptions, and cannot:
        # `EXPLANATORY` is keyed on a WALKED surface and `docs/` is not one, which
        # the staleness test asserts. Passing a source here would be code that can
        # never grant anything, which reads as a scope this record does not have.
        paths = set(_fixed_paths(f.read_text()))
        if paths:
            found[str(f.relative_to(base))] = paths
    return found


def _inventory_mismatch(found: dict[str, set[str]],
                        recorded: dict[str, set[str]]) -> str:
    """The three ways the record can disagree with the tree, or `""` if it agrees.

    Split out from the assertion so the control can exercise it directly, and
    so each state names its own remedy — "a path is GONE" means someone did the
    work, and the record plus #137 are what has to move.
    """
    if found == recorded:
        return ""
    new_files = sorted(set(found) - set(recorded))
    gone_files = sorted(set(recorded) - set(found))
    new_paths = {f: sorted(found[f] - recorded[f])
                 for f in sorted(set(found) & set(recorded))
                 if found[f] - recorded[f]}
    gone_paths = {f: sorted(recorded[f] - found[f])
                  for f in sorted(set(found) & set(recorded))
                  if recorded[f] - found[f]}
    return (
        f"  NEW file, recorded nowhere:        {new_files or 'none'}\n"
        f"  NEW path in a RECORDED file:       {new_paths or 'none'}\n"
        f"  RECORDED file gone from the tree:  {gone_files or 'none'}\n"
        f"  RECORDED path gone from its file:  {gone_paths or 'none'}\n"
    )


def test_no_prompt_SENDS_EVERY_DISPATCH_to_one_file() -> None:
    offenders = [(p.relative_to(REPO), m)
                 for p in _prompts()
                 for m in _fixed_paths(p.read_text(), str(p.relative_to(REPO)))]
    assert not offenders, (
        "these prompts name a FIXED path in `/tmp`, which every dispatch on the "
        "machine shares:\n"
        + "\n".join(f"  {p}: {m}" for p, m in offenders)
        + "\n\nTwo concurrent runs get one file and the loser silently reads or "
          "publishes the winner's content. Carry something per-dispatch in the "
          f"name — a placeholder of any spelling, e.g. {list(PER_DISPATCH_EXAMPLES)}. "
          f"`review_pr`'s `{SHAPE_TO_COPY}` is the shape to copy.\n"
          "If the path is only being DESCRIBED, add it to EXPLANATORY keyed by "
          "`(this file, the path)`, with the sentence that explains it, how many "
          "times this file says it, and a reason. An exemption is scoped to the "
          "judgement that earned it; there is no global one."
    )


def test_THE_WALK_HAS_A_POPULATION_and_the_detector_SEES_BOTH_BACKTICK_FORMS() -> None:
    """POSITIVE CONTROL, and the escaped form is first because it is what escaped.

    The sweep this guard replaces detected on the bare path and replaced on a
    backticked one, so two heredoc-derived prompts carrying ``\\`path\\``` were
    counted as fixed and left unfixed. A control that only exercised the plain
    form would reproduce exactly that blind spot.
    """
    cases = {
        "escaped backticks": r"revising a /tmp staging file (e.g. \`/tmp/claude-pr-body.md\`) later",
        # This used to have to avoid the names in `EXPLANATORY`, because the
        # exemption was global and a control reusing one tested the exemption
        # rather than the shape — a defect met while authoring a test and routed
        # around instead of closed. It no longer has to: `_fixed_paths` grants
        # nothing without a `source`. The name stays neutral anyway, so that this
        # control keeps testing only the SHAPE.
        "plain backticks": "write it to `/tmp/some-fetch.json`, then read it",
        "bare": "gh pr view > /tmp/some-thing.json",
        "in a command": "gh api ... > /tmp/claude-review.md && cat /tmp/claude-review.md",
        # NESTED, and it is the shape the first version of this module missed:
        # both the directory and the leaf are fixed, so two dispatches collide
        # exactly as they do on a flat path. `/` was absent from the pattern's
        # character class and every control here used a flat path, so nothing
        # in the module could see it.
        "nested, both segments fixed": "stage it under /tmp/claude-scratch/output.json first",
    }
    for name, src in cases.items():
        assert _fixed_paths(src), f"the detector missed the {name} form: {src!r}"

    for name, src in {
        "pr-numbered": "write to `/tmp/claude-review-pr-${PR_NUMBER}-<ts>.md`",
        "branch-named": r"revising \`/tmp/claude-pr-body-<branch>.md\` several turns later",
        "pid": "use /tmp/pr-$$.json",
        "a scratch ROOT, not a file": "your scratchpad is /tmp/claude-1000/session/scratchpad",
    }.items():
        assert not _fixed_paths(src), (
            f"the detector fires on {name}, which is SAFE — it would fail a "
            f"correct tree and teach the next reader to delete it: {src!r}")


@pytest.mark.parametrize("key,exemption", list(EXPLANATORY.items()),
                         ids=EXEMPTION_IDS)
def test_every_EXEMPTION_is_still_present_and_still_explanatory(
        key: tuple[str, str], exemption: Exemption) -> None:
    """An exemption for prose nobody wrote any more is a lie that survives.

    This list may only shrink. If the prose that earned the exemption is gone,
    the entry goes with it — otherwise the next fixed path with that name is
    exempt by inheritance.

    THE PREDECESSOR ASSERTED THE WRONG THING, and asserting it is what made the
    entry look checked. It required only that the path appear SOMEWHERE across
    the walked surfaces — which a PRESCRIPTION satisfies exactly as well as an
    explanation, in any file, however many times. Its own docstring named the
    failure mode it was closing ("exempt by inheritance") while closing only the
    case where every mention vanishes. Each of the three things it did not check
    is now part of the exemption's scope, so this test checks each of them.
    """
    source, path = key
    f = REPO / source
    assert f in _prompts(), (
        f"{source} is the file {path} is exempted in, but it is not a walked "
        f"surface — so the exemption applies to nothing and is dead weight. It "
        f"was: {exemption.reason}")

    text = f.read_text()
    assert exemption.anchor in text, (
        f"the prose that EARNS {path}'s exemption in {source} is gone:\n"
        f"  {exemption.anchor!r}\n"
        f"Either restore it or drop the entry — an exemption outliving its own "
        f"justification is how a prescription inherits one. It was: {exemption.reason}")
    assert _mentions(text, path) == exemption.occurrences, (
        f"{source} names {path} {_mentions(text, path)} times; the exemption covers "
        f"{exemption.occurrences}. Read the new occurrence: if it EXPLAINS, raise "
        f"the count; if it PRESCRIBES, it is the defect this module exists for.")


@pytest.mark.parametrize("key,exemption", list(EXPLANATORY.items()),
                         ids=EXEMPTION_IDS)
def test_an_EXEMPTION_does_not_TRAVEL_beyond_the_judgement_that_earned_it(
        key: tuple[str, str], exemption: Exemption) -> None:
    """THE CONTROL THIS MODULE SHIPPED WITHOUT, and the hole was its own headline.

    `_fixed_paths` filtered with `m not in EXPLANATORY` — a global, path-keyed
    set — so `/tmp/pr-comments.json`, the path whose collision produced the 13
    overlapping pairs this module exists for, was exempt on every walked surface
    and in any quantity. A full regression of `fidelity_read_and_compare` read
    clean. The guard could not detect the defect it was built for.

    THE ARMS ARE DRIVEN FROM `EXPLANATORY` ITSELF, NOT FROM THE THREE ENTRIES IN
    IT. That is the difference between closing a class and closing an instance:
    an entry added next year is exercised on all three arms without an edit here,
    and an entry that cannot pass them cannot be written. Each arm reds against
    exactly one widening — file, prose, count — so a partial revert is
    attributable rather than merely red.
    """
    source, path = key
    text = (REPO / source).read_text()

    assert path not in _fixed_paths(text, source), (
        f"{source} does not currently earn its exemption for {path}, so every arm "
        f"below is vacuous — they all assert the path IS flagged")

    # ARM 0 — NO SOURCE AT ALL. Every synthetic control below calls
    # `_fixed_paths` with one argument, so "unattributed text is judged strictly"
    # is load-bearing for the whole module and not merely a default.
    #
    # BOTH SPELLINGS, and the omitted one is the one that matters: the controls
    # call `_fixed_paths(src)` with a single argument, so the property belongs to
    # the DEFAULT and not to the empty string someone happened to pass. Pinning
    # only `source=""` leaves a default that names a real file green.
    assert path in _fixed_paths(text, ""), (
        f"{path} is exempt in text attributed to no file. The default would then "
        f"forgive every control in this module, and a shape bug would hide behind "
        f"an exemption nobody passed.")
    assert path in _fixed_paths(text), (
        f"{path} is exempt when `source` is OMITTED, which is how every synthetic "
        f"control in this module calls the predicate")

    # ARM 1 — ANOTHER FILE. The widening that shipped: the exemption applied
    # wherever the path appeared, so any walked surface could PRESCRIBE it.
    #
    # THE EARNING FILE'S OWN TEXT IS WHAT GETS RE-JUDGED, and a bespoke sentence
    # is what the first draft used — which meant the ANCHOR was missing from it
    # too, so arm 2 was answering and dropping the `f == source` term left every
    # arm green. Measured. Holding prose and count fixed is the only way this arm
    # is about the FILE.
    others = [str(f.relative_to(REPO)) for f in _prompts()
              if str(f.relative_to(REPO)) != source]
    assert others, "only one walked file — arm 1 cannot distinguish anything"
    for other in (others[0], others[-1]):
        assert path in _fixed_paths(text, other), (
            f"the exemption {source} earned for {path} also applies in {other}, "
            f"which earned nothing. A path PRESCRIBED on any other walked surface "
            f"is the class this module exists to catch.")

    # ARM 2 — THE PROSE GONE. The measured scenario, and the one FILE-SCOPING
    # ALONE DOES NOT CLOSE: the regression happens INSIDE the file that earned
    # the exemption, when a later editor tidies away the warning as redundant.
    without = text.replace(exemption.anchor, "")
    assert without != text and path in without, (
        f"removing {exemption.anchor!r} also removed every mention of {path} from "
        f"{source}, so this arm asserts nothing — anchor on prose that can outlive "
        f"the path, not on the path itself")
    assert path in _fixed_paths(without, source), (
        f"{path} is still exempt in {source} after the prose that earns it was "
        f"deleted. An exemption that outlives its own justification is inherited "
        f"by whatever takes its place.")

    # ARM 3 — ONE MORE OCCURRENCE. Neither of the above sees a PRESCRIPTION added
    # beside a surviving explanation: same path, same file, prose intact.
    beside = text + f"\n\nstage it at {path} first\n"
    assert path in _fixed_paths(beside, source), (
        f"a second mention of {path} in {source} rode in on the exemption earned "
        f"by the first. The entry covers {exemption.occurrences}; read the new one "
        f"and either raise the count or fix it.")


@pytest.mark.parametrize("key,exemption", list(EXPLANATORY.items()),
                         ids=EXEMPTION_IDS)
def test_a_LONGER_PATH_is_not_CHARGED_TO_THE_EXEMPTION_it_merely_starts_with(
        key: tuple[str, str], exemption: Exemption) -> None:
    """`_mentions` counts what the DETECTOR sees; `str.count` counts substrings.

    `/tmp/pr-comments.json.bak` is a DIFFERENT path — `TMP_PATH` matches it whole
    and it gets flagged under its own name. A substring count charges it against
    `/tmp/pr-comments.json`'s exemption, so the file's count goes 1 -> 2, the
    exemption lapses, and the untouched explanatory mention is reported as a
    defect beside the real one. A guard that reds on the wrong line teaches the
    next reader to delete the wrong thing.

    NOTHING IN THE TREE EXERCISES THIS, which is exactly why it is written down:
    reverting `_mentions` to `text.count` is green against the whole suite
    without it, so the helper's entire justification would be prose.
    """
    source, path = key
    text = (REPO / source).read_text()
    sibling = f"{path}.bak"

    assert _mentions(sibling, path) == 0 and sibling.count(path) == 1, (
        f"{sibling!r} is supposed to be the case where the two counts DISAGREE; "
        f"if they agree this test cannot distinguish them")

    widened = text + f"\n\nand keep the previous one at {sibling}\n"
    assert path not in _fixed_paths(widened, source), (
        f"adding the unrelated {sibling} to {source} cost {path} the exemption it "
        f"still earns — the count is charging a different path against it")
    assert sibling in _fixed_paths(widened, source), (
        f"{sibling} is a fixed path nothing exempts and it was not flagged, so "
        f"the arm above passes for the wrong reason")


def test_a_FULL_REGRESSION_of_the_defect_this_module_EXISTS_FOR_is_caught() -> None:
    """The exact scenario measured on PR #135, on the real file rather than a fixture.

    `fidelity_read_and_compare` is the prompt whose fixed `/tmp/pr-comments.json`
    gave 19 `build-refine*` runs 13 overlapping pairs in one night. The regression
    is not hypothetical and not exotic: revert the instruction to the fixed path
    and delete the sentence explaining why it carries `${PR_NUMBER}` — the
    "a later editor tidies away the redundant warning" path the module docstring
    already names. Under the shipped global exemption this read CLEAN.

    Kept separate from the parametrized arms above because it pins the FILE and
    the PATH by name. If this prompt is ever renamed or restructured, this test
    is supposed to be the thing that notices.
    """
    source = ("scripts/workflows/temporal/modules/assistant/prompts/"
              "fidelity_read_and_compare.md")
    path = "/tmp/pr-comments.json"
    exemption = EXPLANATORY[(source, path)]
    text = (REPO / source).read_text()

    assert not _fixed_paths(text, source), (
        "the live prompt is not clean, so this test cannot tell a regression from "
        "the status quo")

    regressed = text.replace(
        f"/tmp/pr-comments-${{PR_NUMBER}}.json", path).replace(exemption.anchor, "")
    assert _mentions(regressed, path) >= 2 and exemption.anchor not in regressed, (
        "the regression did not reproduce — the prompt no longer contains the "
        "per-dispatch instruction or the warning this test rewrites")

    assert path in _fixed_paths(regressed, source), (
        f"a full regression of {source} to the fixed {path} reads CLEAN. The guard "
        f"cannot detect the defect it was built for.")


def test_the_PER_DISPATCH_EXAMPLES_are_all_accepted_by_the_SHAPE() -> None:
    """The failure message teaches a shape; it may not teach one the guard rejects.

    The predecessor of `PER_DISPATCH` was this tuple, matched literally. Keeping
    the examples pinned to the shape is what stops the two drifting apart again —
    an example the detector no longer accepts would send an author to fix a path
    that is already safe.
    """
    for example in PER_DISPATCH_EXAMPLES:
        assert PER_DISPATCH.search(f"/tmp/claude-{example}-thing.md"), (
            f"{example!r} is offered in the failure message as a per-dispatch "
            f"marker, but `PER_DISPATCH` does not accept it")


def test_a_placeholder_SPELLING_NOBODY_LISTED_is_still_per_dispatch() -> None:
    """The regression this shape exists for, and it was live in the repo.

    `<descriptive-name>` is `terminal-output.md`'s own spelling and the literal
    token list did not contain it, so the guard would have failed a path that
    follows the repo's own binding convention. The others are spellings nobody
    has written yet — which is the point: they cost no edit here.
    """
    for spelling in ("<descriptive-name>", "<run-id>", "<pr>", "<slug>",
                     "${WORKFLOW}", "{run_id}"):
        assert not _fixed_paths(f"write it to /tmp/claude-{spelling}.md"), (
            f"{spelling!r} is a placeholder — a name carrying it differs between "
            f"concurrent dispatches — but the guard reads it as a fixed path")

    # ...and the shape must still REFUSE a name with no placeholder in it, or it
    # would accept everything and the guard would be decorative.
    assert _fixed_paths("write it to /tmp/claude-deploy-new-workers.sh"), (
        "a filled-in descriptive name carries no placeholder and cannot differ "
        "between two concurrent dispatches — the shape must still flag it")


def test_the_DOCS_RESIDUE_inventory_still_MATCHES_THE_TREE() -> None:
    """`docs/` is not enforced, but the RECORD of what is there must not rot.

    This is the check the class needed and did not have. #137's enumeration was
    written by hand from a narrower search than the class it claims to cover, and
    nothing could tell anyone it had gone stale. Now the tree tells you — in both
    directions, because a residue record that silently shrinks is as misleading as
    one that silently grows.

    PATH BY PATH, NOT FILE BY FILE. The first version compared key sets, so a new
    fixed path landing in a file already on the list was invisible — while this
    module, `docs/file_structure.txt` and #137 all told the reader it would red
    here. The record is a judgement about PATHS; comparing it at file granularity
    asserts less than it claims.
    """
    require_planning_corpus()
    found = _residue_under(PLANNING_ROOT, PLANNING_ROOT)
    recorded = {f: set(e.paths) for f, e in DOCS_RESIDUE.items()}

    assert not _inventory_mismatch(found, recorded), (
        "the `docs/` residue recorded in `DOCS_RESIDUE` no longer matches the "
        "tree.\n"
        + _inventory_mismatch(found, recorded)
        + "\n`docs/` is INVENTORIED, not enforced — a new entry here is not "
          "automatically a defect, and five of the six recorded are not. Read the "
          "line, decide which kind it is, and write that as the entry's reason. "
          "If a path is GONE, someone FIXED it: drop it from the entry (and the "
          "entry with it, if that was its last path) and update issue #137, which "
          "is the operator-facing home for this residue.\n"
          "Derive the sets, do not retype them — `_residue_under(REPO / 'docs', "
          "REPO)` is exactly what this compares against."
    )


def _category(mismatch: str, label: str) -> str:
    """The one line of `_inventory_mismatch`'s report that `label` names.

    The arms below assert against THIS rather than against the whole report,
    and the difference is not cosmetic: the report prints all four category
    labels unconditionally, so `"gone" in mismatch` — which is what one arm
    checked for a revision — is true of every non-empty report and would pass
    with the gone-detection wholly broken. A label that is always present is
    not evidence, and that is the same overclaim this module was just corrected
    for, one layer down.
    """
    lines = [ln for ln in mismatch.splitlines() if ln.strip().startswith(label)]
    assert len(lines) == 1, (
        f"{label!r} names {len(lines)} lines of the mismatch report, so an "
        f"assertion against it is ambiguous:\n{mismatch}")
    # RETURN THE PAYLOAD, NOT THE LINE. Returning anything wider — the line with
    # its label, or the whole report — lets a caller's `x in _category(...)` pass
    # on a payload that fired under a DIFFERENT label, which is the vacuity this
    # helper exists to remove rather than relocate. Mutating the selection to
    # return the whole report is green against a version that returns `lines[0]`
    # and red against this one.
    assert "\n" not in lines[0], (
        f"a category is ONE line of the report; {label!r} selected "
        f"{len(lines[0].splitlines())} of them, so narrowing bought nothing")
    _, _, payload = lines[0].partition(":")
    assert payload, f"{label!r} selected a line with no payload: {lines[0]!r}"
    return payload


def test_a_NEW_PATH_IN_AN_ALREADY_RECORDED_FILE_is_not_invisible(tmp_path: Path) -> None:
    """THE ARM THE PRODUCING PASS DID NOT RUN, and the one that was blind.

    A membership check has two arms and only one of them tests the granularity
    the record claims. Appending a fixed `/tmp` path to an UNRECORDED file reds
    either version; appending it to a RECORDED one was invisible to the key-set
    comparison that shipped. This control reproduces both, on a synthetic tree,
    and pins the difference: it FAILS if anyone reverts the comparison to file
    granularity, which is the class rather than the two files that carried it.
    """
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "recorded.md").write_text("run it with --task-file /tmp/fixed-one.md\n")
    recorded = {"docs/recorded.md": {"/tmp/fixed-one.md"}}

    assert _residue_under(docs, tmp_path) == recorded, (
        "the synthetic tree does not reproduce the recorded state, so neither "
        "arm below tests anything")
    assert not _inventory_mismatch(_residue_under(docs, tmp_path), recorded)

    # ARM 1 — a new path in a file ALREADY on the record. Invisible at file
    # granularity; this is the arm that was never run.
    (docs / "recorded.md").write_text(
        "run it with --task-file /tmp/fixed-one.md\n"
        "and stage the body at /tmp/claude-brandnew-collision.md\n")
    found = _residue_under(docs, tmp_path)
    assert set(found) == set(recorded), (
        "the arms are not distinguishable — this mutation was supposed to leave "
        "the FILE SET identical, which is what made it invisible")
    mismatch = _inventory_mismatch(found, recorded)
    assert "/tmp/claude-brandnew-collision.md" in _category(
        mismatch, "NEW path in a RECORDED file"), (
        "a NEW fixed path in an already-recorded file did not red the inventory. "
        "That is the exact blind spot this control exists for, and three shipped "
        "surfaces claim it cannot happen:\n" + (mismatch or "  (no mismatch at all)"))

    # ARM 2 — the same path in a file NOBODY recorded. Caught by both versions,
    # kept so a regression that breaks only one arm is attributable.
    (docs / "recorded.md").write_text("run it with --task-file /tmp/fixed-one.md\n")
    (docs / "fresh.md").write_text("stage it at /tmp/claude-brandnew-collision.md\n")
    mismatch = _inventory_mismatch(_residue_under(docs, tmp_path), recorded)
    assert "docs/fresh.md" in _category(mismatch, "NEW file")

    # ARM 3 — a file's LAST recorded path was fixed, so the file leaves the tree.
    # The record must not silently shrink either.
    (docs / "fresh.md").unlink()
    (docs / "recorded.md").write_text("run it with --task-file /tmp/claude-<name>.md\n")
    mismatch = _inventory_mismatch(_residue_under(docs, tmp_path), recorded)
    assert "docs/recorded.md" in _category(mismatch, "RECORDED file gone")

    # ARM 4 — THE MIRROR OF ARM 1, and it was missing for the same reason arm 1
    # was: one of a file's paths is fixed while the file keeps others, so the
    # file stays in both dicts and only the SET shrinks. `gone_paths` is the only
    # branch that sees it, and a fix that never reds the record is a fix nobody
    # is told to write down — which is how #137 went stale in the first place.
    (docs / "recorded.md").write_text(
        "one at /tmp/fixed-one.md and another at /tmp/fixed-two.md\n")
    two = {"docs/recorded.md": {"/tmp/fixed-one.md", "/tmp/fixed-two.md"}}
    assert not _inventory_mismatch(_residue_under(docs, tmp_path), two)
    (docs / "recorded.md").write_text(
        "one at /tmp/fixed-one.md and another at /tmp/claude-<name>.md\n")
    found = _residue_under(docs, tmp_path)
    assert set(found) == set(two), (
        "this arm is only meaningful while the FILE stays on both sides — "
        "otherwise it is arm 3 again")
    mismatch = _inventory_mismatch(found, two)
    assert "/tmp/fixed-two.md" in _category(mismatch, "RECORDED path gone"), (
        "a path FIXED inside a file that keeps its other paths did not red the "
        "record. Nothing would then tell anyone to update #137:\n"
        + (mismatch or "  (no mismatch at all)"))


def test_the_SHAPE_the_failure_message_TELLS_AN_AUTHOR_TO_COPY_is_accepted() -> None:
    """A remedy may not name a path in the class it is remedying.

    Measured, on the operator-facing half of this same record: issue #137's step 1
    prescribed `/tmp/claude-build-task.md` as the fix for two live docs, and this
    predicate flags it — a filled-in constant carries no placeholder, so the two
    dispatches still collide and the issue closes clean. That instance was off-tree
    and no test could reach it; this one is the same shape on the surface a test
    CAN reach, and it arrives attached to the check, which is where a wrong remedy
    is most likely to be believed.
    """
    assert not _fixed_paths(f"write it to {SHAPE_TO_COPY}"), (
        f"the failure message offers {SHAPE_TO_COPY!r} as the shape to copy, but "
        f"this guard flags it — an author following the remedy would be sent "
        f"straight back into the class")

    # ...and the message attributes it to `review_pr`, so that has to still be
    # true. Same freshness discipline as `EXPLANATORY` and
    # `PER_DISPATCH_EXAMPLES`: a constant that quotes a live surface is a claim
    # about that surface, and an unchecked one goes stale silently.
    assert any(SHAPE_TO_COPY in p.read_text() for p in _prompts()), (
        f"the failure message credits `review_pr` with {SHAPE_TO_COPY!r}, but no "
        f"walked surface names it any more. Re-quote the live shape or drop the "
        f"attribution — an exemplar nobody uses teaches a shape nobody reviews.")


def test_no_RESIDUE_ENTRY_defers_behind_a_GATE_THAT_DOES_NOT_REACH_IT() -> None:
    """A deferral is only a deferral if the gate it names actually applies.

    `docs/guide/operations.md` was carried across four review passes as needing
    "a human-reviewed edit under `standards-governance.md`". That rule scopes
    itself to `docs/standards/` and `docs/standards/architecture/`; a guide is not
    in it, so the deferral had no gate and the one-string fix was simply owed. The
    check keys on the CLASS — any entry citing that rule for a file outside its
    stated scope — rather than on the file that happened to carry it.

    The scope is READ FROM THE RULE, not copied here: a copy drifts, and the
    drift would be silent in exactly the direction that reopens this.
    """
    scoped = [ln for ln in GOVERNANCE_RULE.read_text().splitlines()
              if "curated product" in ln]
    assert len(scoped) == 1, (
        f"expected exactly one scope sentence in {GOVERNANCE_RULE.name}, found "
        f"{len(scoped)}. The rule was reworded — re-read it and re-anchor this "
        f"check rather than deleting it.")
    scope = tuple(re.findall(r"`(docs/[A-Za-z0-9_./-]*/)`", scoped[0]))
    assert scope, (
        f"no scope paths parsed out of {GOVERNANCE_RULE.name}'s scope sentence: "
        f"{scoped[0]!r}. Silently empty scope would exempt every entry.")

    ungated = [(f, e.reason) for f, e in DOCS_RESIDUE.items()
               if "standards-governance" in e.reason and not f.startswith(scope)]
    assert not ungated, (
        "these entries defer to `standards-governance.md`, but that rule scopes "
        f"itself to {list(scope)} and these files are outside it:\n"
        + "\n".join(f"  {f}" for f, _ in ungated)
        + "\n\nThere is no human-review gate on this file, so the deferral is a "
          "fix that has not been done. Do it, drop the entry, and update #137."
    )
