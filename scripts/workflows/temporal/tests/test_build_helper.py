"""Layer-2 tests. No mocks, no I/O, no fixtures — that is the point.

If any test here needs a mock, the helper is doing something it should not and
the layer boundary has leaked.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.assistant.build import build_helper as helper  # noqa: E402
from modules.assistant.build.build_inputs import (  # noqa: E402
    ChildResult,
    BuildInput,
    Verdict,
)

PASS, FAIL = [], []


def check(name: str, got, want) -> None:
    (PASS if got == want else FAIL).append(f"{name}: got {got!r}, want {want!r}")


# --- completion contract -----------------------------------------------------
out = "opened https://github.com/o/r/pull/12\nfinal https://github.com/o/r/pull/42\n"
check("last URL wins", helper.extract_pr_url(out), "https://github.com/o/r/pull/42")
check("no URL -> None", helper.extract_pr_url("nothing here"), None)
check("pr number", helper.pr_number_from_url("https://github.com/o/r/pull/42"), "42")

# --- verdict parsing, and the fail-safe --------------------------------------
check("merge", helper.parse_verdict("VERDICT: MERGE"), (Verdict.MERGE, True))
check(
    "redispatch",
    helper.parse_verdict("noise\nVERDICT: HOLD - redispatch\n"),
    (Verdict.HOLD_REDISPATCH, True),
)
check(
    "UNPARSEABLE FAILS SAFE TO HUMAN",
    helper.parse_verdict("the run died"),
    (Verdict.HOLD_NEEDS_ASSISTANCE, False),
)
check(
    "prose mentioning the token does not match (anchored)",
    helper.parse_verdict("we could emit VERDICT: MERGE here")[1],
    False,
)
check(
    "last verdict wins on a re-review",
    helper.parse_verdict("VERDICT: HOLD - redispatch\nVERDICT: MERGE")[0],
    Verdict.MERGE,
)

# --- routing -----------------------------------------------------------------
check("redispatch loops once", helper.should_loop_back(Verdict.HOLD_REDISPATCH, 0), True)
check("budget spent", helper.should_loop_back(Verdict.HOLD_REDISPATCH, 1), False)
check("needs-assistance NEVER loops", helper.should_loop_back(Verdict.HOLD_NEEDS_ASSISTANCE, 0), False)
check("merge never loops", helper.should_loop_back(Verdict.MERGE, 0), False)

# --- input validation at the boundary ----------------------------------------
try:
    BuildInput()
    check("no task source rejected", "accepted", "ValueError")
except ValueError:
    check("no task source rejected", "ValueError", "ValueError")

try:
    BuildInput(description="x", task_file="/tmp/y")
    check("both task sources rejected", "accepted", "ValueError")
except ValueError:
    check("both task sources rejected", "ValueError", "ValueError")

# --- arg compilation ---------------------------------------------------------
task = BuildInput(description="fix auth", repo_target="/opt/x", verbose=True)
check(
    "flags first, positional last",
    helper.draft_args(task),
    ["--repo", "/opt/x", "--verbose", "fix auth"],
)
check(
    "correction pass carries both flags",
    helper.refine_args(task, "42", correction_pass=True, ci_unsettled=True),
    ["--repo", "/opt/x", "--verbose", "--correction-pass", "--ci-unsettled", "--pr", "42", "fix auth"],
)
check(
    "task-file bypasses shell parsing",
    helper.task_args(BuildInput(task_file="/tmp/t.md")),
    ["--task-file", "/tmp/t.md"],
)

# --- handoff validation ------------------------------------------------------
try:
    helper.draft_handoff(ChildResult(exit_code=1, output="https://github.com/o/r/pull/1"))
    check("nonzero exit rejected even WITH a URL", "accepted", "RuntimeError")
except RuntimeError:
    check("nonzero exit rejected even WITH a URL", "RuntimeError", "RuntimeError")

try:
    helper.draft_handoff(ChildResult(exit_code=0, output="done, no url"))
    check("exit 0 without a URL rejected", "accepted", "RuntimeError")
except RuntimeError:
    check("exit 0 without a URL rejected", "RuntimeError", "RuntimeError")

check(
    "valid handoff returns the URL",
    helper.draft_handoff(ChildResult(exit_code=0, output="https://github.com/o/r/pull/7")),
    "https://github.com/o/r/pull/7",
)

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print(f"  FAIL  {f}")
raise SystemExit(1 if FAIL else 0)
