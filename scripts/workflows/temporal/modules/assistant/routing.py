"""The routing vocabulary every parent branches on — declared ONCE.

Promoted here per §10.1 rule 3: three consumers (`build`, `review_pr`,
`plan_project`), and the promotion rule is consumer count, never taste.

WHY IT MOVED. `Verdict` and its parser were typed twice — byte-identical
members, byte-identical regex, differing only in docstring prose — and issue #34
recorded the consequence: the copy that decides whether a PR MERGES had zero
tests while its twin had twenty. `build` bridged the two with
`Verdict(result.verdict.value)`, converting an enum into an identical enum,
which is the `derive != declare` seam failing in plain sight. Adding a third
parent would have made it three copies.

This module is deliberately dependency-free — no I/O, no imports from siblings —
so any workflow may import it without pulling in a family it does not belong to.
"""

from __future__ import annotations

import re
from enum import Enum

__all__ = [
    "Verdict", "MAX_LOOPS", "parse_verdict", "should_loop_back",
    "PR_URL", "extract_pr_url", "pr_number_from_url", "pr_identity",
]


class Verdict(str, Enum):
    """The routing token `review-pr` emits on its terminal line.

    THIS IS THE INTERFACE between the disposition child and any caller. The
    child aggregates per-finding `hold_kind` values into one token so a caller
    never re-derives a judgement the reviewer already made.
    """

    MERGE = "MERGE"
    HOLD_REDISPATCH = "HOLD - redispatch"
    HOLD_NEEDS_ASSISTANCE = "HOLD - needs-assistance"


# Anchored and exhaustive: an unanchored match would find the token inside prose
# quoting a previous verdict, and a run that discusses its own history would
# route on the sentence it wrote about itself.
_VERDICT = re.compile(
    r"^VERDICT: (MERGE|HOLD - (?:redispatch|needs-assistance))$",
    re.MULTILINE,
)

# EXACTLY ONE loop-back, for every parent. Not a knob, and deliberately not
# configurable. Self-correction plateaus at roughly 3-5 passes: the same model
# carries the same blind spots, and past the plateau it stops correcting and
# starts justifying. Watched directly on this fleet — one PR reached EIGHT
# review passes, and pass 8 reviewed the same tree as pass 7 with no commits
# between them. Counting correction passes across the PIPELINE rather than
# within any one child, one loop-back lands at four, inside the band.
MAX_LOOPS = 1


def parse_verdict(output: str) -> tuple[Verdict, bool]:
    """Return (verdict, was_parseable).

    FAILS SAFE TO THE HUMAN BRANCH. An unparseable verdict becomes
    HOLD_NEEDS_ASSISTANCE, never MERGE and never a redispatch — the routing
    contract's rule is that ambiguity routes to the branch requiring a person,
    because the cost of wrongly merging is unbounded and the cost of wrongly
    asking is one message.

    The LAST match wins: a disposition comment may quote an earlier pass's
    verdict while reaching a different one of its own.

    The boolean is returned rather than logged here so the caller can report the
    degradation; a helper that printed would not be pure.
    """
    matches = _VERDICT.findall(output)
    if not matches:
        return Verdict.HOLD_NEEDS_ASSISTANCE, False
    return Verdict(matches[-1]), True


def should_loop_back(verdict: Verdict, loops_used: int) -> bool:
    """Only a redispatch verdict loops, and only while the budget holds.

    needs-assistance never loops at any count: a human ruling is not something
    more passes can produce, so spending them is pure waste.
    """
    return verdict is Verdict.HOLD_REDISPATCH and loops_used < MAX_LOOPS


# THE ONE DECLARATION of the PR-URL address, for the same reason `parse_verdict`
# has one: it was typed THREE times with two different strengths, and the weak
# one is the one that survives the migration.
#
#   - `assistant_activities.PR_URL` and `build/build_helper._PR_URL` were
#     byte-identical anchored copies (`https://github\.com/[^\s)]+/pull/(\d+)`);
#   - `pr_number_from_url` was `re.search(r"/pull/(\d+)", url)` — NO HOST ANCHOR
#     AT ALL. Its consumers were `build_workflow`, `build_minor_workflow` and
#     `plan_project_workflow`; Phase 4 raised that to SIX by replacing three
#     ad-hoc `rsplit` derivations (`research_workflow`,
#     `research_refresh_parent_workflow`, `scripts/run_plan_project`) with it.
#     The count matters because this comment is where an audit of the
#     child-supplied-URL surface starts, and the first version of it named half.
#
# The host pin held only BY COMPOSITION: the anchored extractor ran first and
# handed its output on. `phase4_fleet_migration.md` requirement 6 moves the URL
# onto a typed field, which takes the anchored extractor off that path — so the
# unanchored parser would have become the only one, and a migration written to
# strengthen the URL would have shipped weaker than what it replaced.
#
# OWNER/REPO IS A CAPTURE GROUP, NOT PART OF A GREEDY WILDCARD, and that is the
# whole of the identity check. `[^\s)]+` in the old pattern IS the owner/repo
# segment, so `https://github.com/someone-else/other-repo/pull/12` matched and
# yielded `12` — a number then used against THIS dispatch's repo. The pattern
# pins the host and guarantees digits; it never pinned identity, and nothing
# else did either.
#
# `)` is excluded because these URLs arrive inside markdown links; `/` is
# excluded from the two identity segments because a real PR URL has exactly two
# path segments before `/pull/`. That narrowing is a deliberate parity line item
# — see `phase4_fleet_migration.md` §Capability Parity — and it rejects only
# strings that are not PR URLs.
PR_URL = re.compile(r"https://github\.com/([^\s/)]+/[^\s/)]+)/pull/(\d+)")

# The SAME grammar, spelled for `grep -E`, which has no `\s`. `run-claude.sh`
# decides a run COMPLETED by grepping its final text for this; the parent then
# extracts with `PR_URL` above. **They must accept exactly the same inputs** —
# a gate that accepts what the parser cannot read reports a finished run as
# lost, which is a destroyed dispatch rather than a cosmetic mismatch.
#
# IT LIVES BESIDE THE PARSER BECAUSE NINE COPIES DIVERGED FROM IT. Every V2
# workflow declared its own `[^ )]+`, which spans `/` and therefore matched
# `…/a/b/c/pull/1` — a shape `PR_URL` refuses. The agreement test existed and
# could not fail, because its inputs were all two-segment. One declaration
# removes the class; the test now carries structural probes that would catch a
# tenth copy.
PR_URL_COMPLETION_ERE = r"https://github\.com/[^ )/]+/[^ )/]+/pull/[0-9]+"

# `plan-revision` alone accepts an ISSUE url too: a STOP files an issue and prints
# it as the completion signal. The ALTERNATION is what is wider — the path
# segments are not, and spelling them `[^ )]+` there left the same defect the
# narrowing above removed: a completed plan-revision run that opened its PR was
# reported to the operator as lost, because the gate accepted a URL
# `extract_pr_url` refuses. Fixed on the second review pass; the first closed
# eight of nine and the guard then filtered this one out of its own probes.
PR_OR_ISSUE_COMPLETION_ERE = r"https://github\.com/[^ )/]+/[^ )/]+/(pull|issues)/[0-9]+"


def extract_pr_url(output: str) -> str | None:
    """Last PR URL in a run's output — the completion contract's payload.

    Last, not first: a run may mention an existing PR before opening its own.

    Returns the matched URL and not the whole line, so a caller never has to
    re-parse. `assistant_activities.extract_pr_url` and
    `build.build_helper.extract_pr_url` re-export THIS object; a body typed
    there would be a second copy that stays green in its own tests.
    """
    matches = [m.group(0) for m in PR_URL.finditer(output)]
    return matches[-1] if matches else None


def pr_identity(url: str) -> tuple[str, str]:
    """`(owner/repo, number)` from a PR URL. Raises when it is not one.

    THE POINT OF RETURNING BOTH IS THAT A CALLER CANNOT TAKE THE NUMBER WITHOUT
    SEEING THE REPO. A child is instructed to read prior PR comments, which
    routinely contain other PRs' URLs; a `pr_url` naming a different repository
    needs no adversarial child, and the derived number flows into `gh pr view`,
    `gh pr comment` and `--pr` on a downstream child that checks out and commits
    to that PR's branch. `pr_number_from_url` below discards the repo half
    deliberately and is only safe where the caller has already established
    identity some other way — which is why the typed path compares the whole
    reference rather than calling it.
    """
    match = PR_URL.search(url)
    if not match:
        raise ValueError(
            f"not a github PR URL: {url!r}. Expected "
            f"https://github.com/<owner>/<repo>/pull/<number>."
        )
    return match.group(1), match.group(2)


def pr_number_from_url(url: str, *, expected_repo: str | None) -> str:
    """The PR number a child reported, as its caller's handoff key.

    Raises rather than returning a sentinel: a parent that cannot identify the
    PR cannot review it, and a silent empty string would surface later as a
    confusing `gh` error against PR number ''.

    HOST-ANCHORED SINCE PHASE 4, via `pr_identity`. It used to be a bare
    `/pull/(\\d+)` search, which accepted `/pull/12` out of any string at all.

    `expected_repo` IS `owner/name` AND HAS NO DEFAULT, for the same reason
    `exit_record.route`'s `expected_ref` has none: this is the parameter most
    likely to acquire a convenience default at the next call site, and a keyword
    defaulting to None is a check that skips itself. Passing None is a caller
    STATING it cannot check, which is a real answer and a visible one;
    `test_every_production_caller_of_pr_number_from_url_states_its_expected_repo`
    is what stops it becoming the quiet default.

    WHY THE REPO HALF IS CHECKED HERE AND NOT LEFT TO THE TYPED RECORD. THIS is
    the derivation that reaches `gh`. `url` is a CHILD'S stdout — children are
    instructed to read prior PR comments and bodies, which routinely quote other
    PRs' URLs, and `extract_pr_url` takes the LAST match. Until Phase 4 this
    function discarded the owner/repo half outright, so
    `https://github.com/someone-else/other-repo/pull/12` yielded `"12"`, which
    then reached `wait_for_ci`, `run_review` and `--pr` on a refine child that
    checks out and commits to that PR's branch — all with `cwd=repo_root`, i.e.
    against THIS repository's unrelated PR #12. `exit_record`'s rule R5b cannot
    see it: R5b's right-hand side is built FROM this number, so a wrong number
    is compared against itself.
    """
    repo, number = pr_identity(url)
    if expected_repo is not None and repo != expected_repo:
        raise ValueError(
            f"a child reported a PR URL in {repo!r} while this dispatch is "
            f"operating in {expected_repo!r}: {url!r}. Refusing to hand "
            f"#{number} on: the number would be used against THIS repository, "
            f"so a PR the child merely quoted becomes a PR this dispatch "
            f"reviews, comments on and commits to."
        )
    return number
