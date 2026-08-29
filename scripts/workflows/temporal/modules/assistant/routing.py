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

THE CI GATE JOINED IT FOR THE SAME REASON, ONE PROMOTION LATER. `CiVerdict`,
`POLICY_PATH` and `ci_gate` lived in the BUILD family, so the plan and research
parents could not read a CI verdict without importing `build/` — a layering
inversion, and the reason four parents dispatched `review-pr` with the verdict
never read. §10.1 rule 3 decides it mechanically: six consumers across three
families promotes to their common parent, which is here. The gate is PURE and
returns a `Verdict`, so it belongs on this side of the layer boundary; the reads
it consumes (`ci_verdict`, `wait_for_ci`) are I/O and went to
`assistant_activities`.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

__all__ = [
    "Verdict", "MAX_LOOPS", "parse_verdict", "should_loop_back",
    "PR_URL", "extract_pr_url", "pr_number_from_url", "pr_identity",
    "CiVerdict", "POLICY_PATH", "ci_gate",
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
# STEP 3 OF THE OPERATOR'S EARNING RAMP, set 2026-08-12. The steps: (1) one
# loop, prove the mechanism — done; (2) a turn cap so a runaway cannot spin —
# done; (3) THREE loops, observe what it costs and what it finds — here;
# (4) unbounded, watched. Autonomy is earned, not switched on.
#
# AND THIS IS WHAT MAKES PHASE 5'S CONDITION 1 MEASURABLE AT ALL. Convergence
# is not in `should_loop_back` below, so raising this runs passes PAST the point
# the predicate called converged — which is the one corpus shape the archive
# could never produce. At 1, every fire landed on its PR's last block with
# nothing after it: 4 fires, 0 scorable, unfalsifiable by construction. At 3, a
# later pass either contradicts a fire or confirms it, and the denominator
# stops being zero.
#
# The research family keeps its own `MAX_LOOPS = 1` deliberately: convergence is
# measured over `review-pr` on build PRs, and a research loop is the most
# expensive dispatch in the fleet.
MAX_LOOPS = 3


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


# WHICH CHECKS GATE MERGE IS A FACT ABOUT THE REPO, NOT ABOUT THIS PARENT.
# The parent is generic across many repos; a constant enumerating each
# consumer's job names is the parent knowing things about its consumers, and
# the failure is silent-by-default — the next repo's checks match nothing, the
# gate reports a skip, and the only signal is a line someone has to be reading.
#
# MEASURED IMMEDIATELY: this shipped as `BLOCKING_CHECKS = ("suite",)` and the
# MDC side's gating job is named `master-test-tier`. Every one of their PRs
# would have returned NO_CHECKS — the gate adopted, none of it received.
#
# So the repo declares, and the parent reads. Onboarding a repo becomes adding
# one file TO THAT REPO, which is the correct ownership direction and the
# reason this scales past the second consumer.
POLICY_PATH = Path("testing") / "check-policy.yaml"


class CiVerdict(str, Enum):
    """Five states, and the last three are the ones that get fudged.

    NO_CHECKS AND GATE_DID_NOT_RUN WERE ONE STATE UNTIL 2026-08-13, AND
    COLLAPSING THEM COST TWO PRs THEIR MERGE GATE. Both mean "no blocking check
    reported", and the causes are opposites:

      - NO_CHECKS       — the repo declares no blocking checks. There is no gate
                          to wait for, and proceeding is correct.
      - GATE_DID_NOT_RUN — the repo DOES declare blocking checks and none of them
                          reported. The gate exists and produced nothing, which
                          is not a pass and must stop the run.

    The usual cause of the second is a conflicted PR: `pull_request` workflows
    run against the merge ref, GitHub cannot compute one for a conflicted PR, so
    no run is created at all. Zero runs render as zero failures.

    UNREADABLE_CHECKS IS THE SAME LESSON ONE LAYER OUT, AND IT COST PR #92
    THREE REBUILDS ON 2026-08-14. `UNREADABLE_POLICY` already says that a
    declaration which cannot be READ is a different fact from one that does not
    exist. The CHECK LIST had no such state: a failed `gh pr checks` returns an
    empty stdout, which became `[]`, which is indistinguishable from "the gate
    reported nothing" — so a broken read rendered as GATE_DID_NOT_RUN, which is
    HOLD_REDISPATCH, which rebuilds. Three passes of build-refine ran against a
    PR that was OPEN, MERGEABLE and green on all four checks the entire time.

    The distinction earns its place because THE REMEDIES ARE OPPOSITE. A gate
    that did not run is usually a conflicted PR, and redispatching an engineer
    to resolve it is the right move. A gate that cannot be READ is an
    environment failure, and redispatching cannot fix it — it can only spend the
    loop budget discovering that again.
    """

    GREEN = "green"
    RED = "red"
    NO_CHECKS = "no_checks"
    GATE_DID_NOT_RUN = "gate_did_not_run"
    UNREADABLE_POLICY = "unreadable_policy"
    UNREADABLE_CHECKS = "unreadable_checks"


def ci_gate(state: CiVerdict, extra: list[str], *, pr: str,
            repo_target: str | None) -> tuple[Verdict | None, list[str]]:
    """Map a settled CI read to a HOLD (or None) plus the operator-facing notes.

    PURE, AND SHARED BY EVERY PARENT THAT DISPATCHES `review-pr`, which is the
    whole reason it is here rather than inline. The cascade below lived in
    `build_workflow` only, so `build_minor` reached `review-pr` with the CI
    verdict never read — the light tier could return MERGE on a red tree, which
    is exactly the hole removing branch protection opened and which this gate was
    written to close. One parent got the gate and its sibling was never updated:
    a whole block present in one copy and absent from its sibling, the reportable
    drift pattern under `tests/unit/fork_vs_parameterize.py` S3, in the category
    that module's own contract calls `operational-safety` — *a cheaper run is not
    a run permitted to be less careful*.

    THEN THE SAME DEFECT WAS FOUND ONE ALTITUDE UP. Promoting it to
    `build_helper` fixed the build family and left FOUR MORE parents — one plan,
    three research — dispatching `review-pr` on an unread verdict, because
    reaching the gate from outside `build/` meant importing the build family.
    Promotion to `routing` removed that inversion; the gate is now wired into all
    six. The LOGIC did not change in that move: same six states, same note text,
    same HOLD kinds.

    IT IS NOT TRUE THAT A MARKDOWN-ONLY FAMILY HAS NOTHING TO GATE. This repo's
    `.github/workflows/tests.yml` carries NO `paths:` filter, deliberately — its
    own comment says a filtered gate "can only ever skip something it should have
    caught" — so a plan or research PR that touches only `.md` still runs the
    full suite, and this suite greps prompts and docs. A markdown edit turning
    the tree red is an ordinary outcome here, not a hypothetical.

    WHY THE GATE IS IN A PARENT AND NOT A PROMPT: telling a review agent to check
    and withhold MERGE is a convention, and an agent can reason past a convention
    — "unrelated failure, proceeding" is the shape being guarded against. Here the
    agent never gets a verdict to give.

    HOLD, NEVER `exit 1`: killing the run discards a diff two passes just built.
    HOLD keeps the work and hands the failure back in the format the pipeline
    already consumes.

    Returns `(None, notes)` when the gate does not stop the run — the notes may
    still be non-empty, because two non-blocking states are reported out loud
    rather than passed silently.
    """
    where = f" in {repo_target}" if repo_target else ""
    if state is CiVerdict.UNREADABLE_CHECKS:
        # NEEDS_ASSISTANCE, NOT REDISPATCH, AND THE DIFFERENCE IS THE WHOLE
        # POINT. A gate that did not RUN is usually a conflicted PR, and sending
        # an engineer back to resolve it is right. CI that cannot be READ is an
        # environment failure — a redispatch cannot fix it and can only spend the
        # loop budget rediscovering that. Which is exactly what happened: a failed
        # `gh pr checks` read as GATE_DID_NOT_RUN and PR #92 rebuilt three times
        # while it was OPEN, MERGEABLE and green throughout.
        return Verdict.HOLD_NEEDS_ASSISTANCE, [
            f"CI GATE: HOLD — the CI status of PR {pr} could not be READ{where} "
            "(`gh pr checks` returned nothing parseable). This is NOT the same "
            "as the gate not running, and a redispatch cannot fix it: check `gh "
            "auth status`, rate limits, and network. review-pr was NOT dispatched."
        ]

    if state is CiVerdict.UNREADABLE_POLICY:
        # A declaration that EXISTS and cannot be read is a different fact from
        # no declaration, and collapsing them is how the skip path becomes the
        # new exit. Same discipline the JSON parse already follows: unreadable
        # input fails into the state that STOPS.
        return Verdict.HOLD_NEEDS_ASSISTANCE, [
            f"CI GATE: HOLD — {POLICY_PATH} exists and could not be parsed. "
            "A broken declaration is not the same as no declaration; fix the file. "
            "review-pr was NOT dispatched."
        ]

    notes: list[str] = []
    # GATE_DID_NOT_RUN is excluded because its `extra` carries the names of the
    # gate that is ABSENT, not of checks that ran. Reading it here reported
    # `suite` as unclassified in the same breath as the branch below reported it
    # as declared blocking — two contradictory lines from one run, on 2026-08-14.
    if extra and state not in (CiVerdict.RED, CiVerdict.GATE_DID_NOT_RUN):
        # A check that ran and is declared NEITHER blocking nor advisory is the
        # third state the Testing Standard says does not exist. Reported by name,
        # never silently gated — a check the repo has not classified must not halt
        # the fleet, and must not hide either.
        #
        # `CI NOTE (not a hold)`, NOT `CI GATE:`, AND THE PREFIX IS THE FIX. This
        # note opened with the same four characters as the four branches that DO
        # hold, so an operator reading a run's output could not tell a report from
        # a stop. MEASURED on skyy-command#281, 2026-08-29: `build` looped three
        # times, this note printed on every pass, and the analyst reading it
        # concluded the GATE had held four times and filed a handoff proposing a
        # routing fix for it. The gate never held — `review-pr` did, on its own
        # findings — and the whole diagnosis followed from four characters.
        notes.append(
            f"CI NOTE (not a hold): UNDECLARED CHECKS — {', '.join(extra)} ran and appear in neither "
            f"the blocking nor the advisory list of {POLICY_PATH}. The Testing Standard "
            "admits no third state; classify them."
        )

    if state is CiVerdict.RED:
        notes.append(
            f"CI GATE: HOLD — blocking checks failed: {', '.join(extra)}. "
            "review-pr was NOT dispatched; a red tree cannot produce a MERGE verdict. "
            "Fix the checks and redispatch; the diff is intact on the branch."
        )
        return Verdict.HOLD_REDISPATCH, notes

    if state is CiVerdict.GATE_DID_NOT_RUN:
        notes.append(
            f"CI GATE: HOLD — {POLICY_PATH} declares {', '.join(extra)} blocking, and "
            f"NONE of them reported on PR {pr}{where}. The gate exists and produced "
            "nothing, which is not a pass. review-pr was NOT dispatched. The usual "
            "cause is a CONFLICTED PR: `pull_request` workflows run against the merge "
            "ref, GitHub cannot compute one for a conflicted PR, so no run is created "
            "at all — check `git ls-remote origin refs/pull/<N>/merge` against the "
            "current head. Resolve, push, and let the checks run before redispatching; "
            "the diff is intact on the branch."
        )
        return Verdict.HOLD_REDISPATCH, notes

    if state is CiVerdict.NO_CHECKS:
        # NOT green, and named rather than silent. A repo with no workflows, or a
        # PR whose workflows were all path-filtered out, reports nothing — and
        # "no checks reported" reading as pass is how a filtered gate would get
        # here. The run says so out loud; it does not stop on it, because a repo
        # may legitimately have none.
        notes.append(
            f"CI NOTE (not a hold): no check declared blocking in {POLICY_PATH} "
            f"reported on PR {pr}{where}. This is NOT a pass. Either the repo has "
            "no such gate, or its workflows were filtered out of this change."
        )

    return None, notes
