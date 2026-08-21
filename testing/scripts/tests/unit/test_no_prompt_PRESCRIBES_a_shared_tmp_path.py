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
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import pytest

REPO = Path(__file__).resolve().parents[4]

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

# A path named only to EXPLAIN the defect — prose about the old fixed form, not
# an instruction to use it. Each entry states why, because an exemption without
# a reason is how this list grows until the guard means nothing.
EXPLANATORY = {
    "/tmp/pr-comments.json":
        "named in `fidelity_read_and_compare`'s own warning about why the "
        "filename carries ${PR_NUMBER}. The INSTRUCTION beside it is already "
        "per-dispatch; removing the prose would delete the reason.",
    "/tmp/shared/notes.md":
        "the WORKED EXAMPLE in `build_activities`'s docstring for why an escaping "
        "relative argument is rendered as its resolved absolute path — it is the "
        "path the fleet would WRONGLY have opened. Nothing writes it.",
    "/tmp/x/candidates.md":
        "the tail of the traversal string `../../../../tmp/x/candidates.md` that "
        "`run_plan_sprint`'s comment records as having escaped an `.exists()` "
        "check. It is the attack that was demonstrated, not a path to use.",
}


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
# one-line remedy: only one of these is still fix-class, and the mechanical
# predicate cannot tell the other five from a defect.
#
# DO NOT RETYPE THE `paths` SETS. They are the output of `_fixed_paths` over
# `git ls-files docs`, and the test below is what reconciles them.
DOCS_RESIDUE: dict[str, Residue] = {
    "docs/standards/workflow-scripts.md": Residue(
        frozenset({"/tmp/task.md"}),
        "FIX-CLASS. `--task-file /tmp/task.md` in a worked example, in a live "
        "binding standard — the strongest prescription shape in the repo. Needs "
        "a human-reviewed edit under `standards-governance.md`, whose scope "
        "(that rule's own line: `docs/standards/`, `docs/standards/architecture/`) "
        "does reach this file, which is why it is recorded rather than fixed. "
        "Tracked in #137.",
    ),
    "docs/standards/temporal/worker_deployment_standard.md": Residue(
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
    "docs/guide/claude_code_orchestration.md": Residue(
        frozenset({"/tmp/workflow/plan.md", "/tmp/workflow/plan-v2.md",
                   "/tmp/workflow/security.md"}),
        "NOT FIX-CLASS. `/tmp/workflow/*.md` inside a hypothetical `plan-feature.sh` "
        "in an options comparison, and principle 4 of the same document explicitly "
        "retires the pattern: 'The original said `/tmp/workflow/*.md`… the handoff "
        "between stages is the PR'. Illustration of a rejected approach.",
    ),
    "docs/development/reviews/review-skyy-command-2026-07-24.md": Residue(
        frozenset({"/tmp/claude-pr-body.md"}),
        "NOT FIX-CLASS. A dated review recording that `/tmp/claude-pr-body.md` was "
        "the file 43% of read-before-Edit failures concentrated on. A record of "
        "what happened, which is the `EXPLANATORY` shape.",
    ),
    "docs/development/reviews/review-mdc-master-planning-2026-05-03.md": Residue(
        frozenset({"/tmp/claude-migration-sprint1.sed"}),
        "NOT FIX-CLASS. A dated review quoting the `sed` invocation that was run. "
        "A record of what happened.",
    ),
    "docs/standards/architecture/research/raw/code_routed_control_flow.md": Residue(
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


def _fixed_paths(text: str) -> list[str]:
    """`/tmp` paths in `text` whose names cannot differ between two dispatches."""
    return [m for m in TMP_PATH.findall(text)
            if not PER_DISPATCH.search(m)
            and m not in EXPLANATORY]


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
                 for p in _prompts() for m in _fixed_paths(p.read_text())]
    assert not offenders, (
        "these prompts name a FIXED path in `/tmp`, which every dispatch on the "
        "machine shares:\n"
        + "\n".join(f"  {p}: {m}" for p, m in offenders)
        + "\n\nTwo concurrent runs get one file and the loser silently reads or "
          "publishes the winner's content. Carry something per-dispatch in the "
          f"name — a placeholder of any spelling, e.g. {list(PER_DISPATCH_EXAMPLES)}. "
          f"`review_pr`'s `{SHAPE_TO_COPY}` is the shape to copy.\n"
          "If the path is only being DESCRIBED, add it to EXPLANATORY with a reason."
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
        # NOT a name from EXPLANATORY: the exemption list filters the detector,
        # so a control reusing an exempted name tests the exemption rather than
        # the shape. Caught by this control failing on its first run.
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


@pytest.mark.parametrize("path,reason", sorted(EXPLANATORY.items()))
def test_every_EXEMPTION_is_still_present_and_still_explanatory(path: str, reason: str) -> None:
    """An exemption for a path nobody mentions any more is a lie that survives.

    This list may only shrink. If the prose that earned the exemption is gone,
    the entry goes with it — otherwise the next fixed path with that name is
    exempt by inheritance.
    """
    assert any(path in p.read_text() for p in _prompts()), (
        f"{path} is exempted in EXPLANATORY but appears in no prompt. Remove the "
        f"entry — its stated reason was: {reason}")


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
    found = _residue_under(REPO / "docs", REPO)
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
    assert "/tmp/claude-brandnew-collision.md" in mismatch, (
        "a NEW fixed path in an already-recorded file did not red the inventory. "
        "That is the exact blind spot this control exists for, and three shipped "
        "surfaces claim it cannot happen:\n" + (mismatch or "  (no mismatch at all)"))
    assert "NEW path in a RECORDED file" in mismatch

    # ARM 2 — the same path in a file NOBODY recorded. Caught by both versions,
    # kept so a regression that breaks only one arm is attributable.
    (docs / "recorded.md").write_text("run it with --task-file /tmp/fixed-one.md\n")
    (docs / "fresh.md").write_text("stage it at /tmp/claude-brandnew-collision.md\n")
    mismatch = _inventory_mismatch(_residue_under(docs, tmp_path), recorded)
    assert "docs/fresh.md" in mismatch and "NEW file" in mismatch

    # ARM 3 — a path that was FIXED. The record must not silently shrink either.
    (docs / "fresh.md").unlink()
    (docs / "recorded.md").write_text("run it with --task-file /tmp/claude-<name>.md\n")
    mismatch = _inventory_mismatch(_residue_under(docs, tmp_path), recorded)
    assert "docs/recorded.md" in mismatch and "gone" in mismatch


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
