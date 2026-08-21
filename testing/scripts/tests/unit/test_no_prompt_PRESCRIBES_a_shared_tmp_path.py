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


# THE SAME CLASS, ONE SURFACE OVER, RECORDED RATHER THAN ENFORCED.
#
# `docs/` is not in `SURFACES` and this entry does not put it there: nothing in
# `docs/` has to change for the suite to stay green. What the test below asserts
# is that this INVENTORY still matches the tree — so a NEW shared path in `docs/`
# fails here instead of being found by a later review pass, and a FIXED one
# forces this record to be updated at the moment the work is done.
#
# WHY AN INVENTORY IN THE TREE AND NOT A LIST IN THE ISSUE. #137 recorded this
# residue by hand, from a `--task-file`-shaped search, and therefore named the
# two files that carried `--task-file` out of the seven that carry the class. A
# hand-written enumeration of a class is stale the moment the tree moves, and
# nothing tells anyone. This one is derived from the guard's own predicate on
# every run.
#
# EACH ENTRY SAYS WHICH KIND IT IS, because "add `docs/` to SURFACES" is NOT a
# one-line remedy: only two of these are fix-class, and the mechanical predicate
# cannot tell the other five from a defect.
DOCS_RESIDUE = {
    "docs/standards/workflow-scripts.md":
        "FIX-CLASS. `--task-file /tmp/task.md` in a worked example, in a live "
        "binding standard — the strongest prescription shape in the repo. Needs "
        "a human-reviewed edit under `standards-governance.md`, which is why it "
        "is recorded rather than fixed. Tracked in #137.",
    "docs/guide/operations.md":
        "FIX-CLASS. `--task-file /tmp/claude-task.md`, and the SAME FILE nineteen "
        "lines up already prescribes `/tmp/claude-<name>.md` — the example "
        "contradicts its own rule. Tracked in #137.",
    "docs/standards/temporal/worker_deployment_standard.md":
        "NOT FIX-CLASS, and this is the entry that makes the remedy non-mechanical. "
        "`/tmp/claude-deploy-new-workers.sh` is a FILLED-IN instance of exactly what "
        "`config/rules/terminal-output.md` prescribes (`/tmp/claude-<descriptive-"
        "name>.sh`). The predicate cannot distinguish a descriptive per-task name "
        "from a generic one — `/tmp/claude-task.md` and this look the same to it. "
        "The file is also a vendored MIRROR this repo may not edit.",
    "docs/guide/claude_code_orchestration.md":
        "NOT FIX-CLASS. `/tmp/workflow/*.md` inside a hypothetical `plan-feature.sh` "
        "in an options comparison, and principle 4 of the same document explicitly "
        "retires the pattern: 'The original said `/tmp/workflow/*.md`… the handoff "
        "between stages is the PR'. Illustration of a rejected approach.",
    "docs/development/reviews/review-skyy-command-2026-07-24.md":
        "NOT FIX-CLASS. A dated review recording that `/tmp/claude-pr-body.md` was "
        "the file 43% of read-before-Edit failures concentrated on. A record of "
        "what happened, which is the `EXPLANATORY` shape.",
    "docs/development/reviews/review-mdc-master-planning-2026-05-03.md":
        "NOT FIX-CLASS. A dated review quoting the `sed` invocation that was run. "
        "A record of what happened.",
    "docs/standards/architecture/research/raw/code_routed_control_flow.md":
        "NOT FIX-CLASS. Quotes Argo's own documentation (`@/tmp/argo_arg_N.txt`) "
        "while describing a third-party tool's parameter passing. Not ours to "
        "prescribe or to fix.",
}


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
          "`review_pr`'s "
          "`/tmp/claude-review-pr-${PR_NUMBER}-<ts>.md` is the shape to copy.\n"
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
    """
    found = {str(f.relative_to(REPO))
             for f in (REPO / "docs").rglob("*")
             if f.is_file() and f.suffix in SUFFIXES and _fixed_paths(f.read_text())}
    recorded = set(DOCS_RESIDUE)

    assert found == recorded, (
        "the `docs/` residue recorded in `DOCS_RESIDUE` no longer matches the tree.\n"
        f"  NEW, recorded nowhere: {sorted(found - recorded) or 'none'}\n"
        f"  RECORDED but gone:     {sorted(recorded - found) or 'none'}\n\n"
        "`docs/` is INVENTORIED, not enforced — a new entry here is not "
        "automatically a defect, and five of the seven originals are not. Read the "
        "line, decide which kind it is, and write that as the entry's reason. If a "
        "path was FIXED, drop its entry and update issue #137, which is the "
        "operator-facing home for this residue."
    )
