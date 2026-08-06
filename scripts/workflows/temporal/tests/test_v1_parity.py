"""V1/V2 parity assertions.

Exists because of a specific production failure: the V2 port RE-DECLARED V1's
constants instead of deriving from them, a draft ran at MAX_TURNS=120 against
V1's 250, and a full budget was spent producing nothing recoverable. V1's logs
already held the answer — the same task class had completed in 130 turns, so the
cap was set below a known-good measurement that existed at authoring time.

These tests convert silent divergence into a red test. A deliberate difference
is allowed but must be DECLARED here with a reason, never left implied.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.assistant import assistant_activities as act  # noqa: E402
from modules.assistant.build.build_draft import build_draft_workflow as draft  # noqa: E402
from modules.assistant.build.build_refine import build_refine_workflow as refine  # noqa: E402
from modules.assistant.review_pr import review_pr_activities as rpa  # noqa: E402
from modules.assistant.build.build import build_workflow as parent  # noqa: E402
from modules.assistant.build.build_minor import build_minor_workflow as parent_minor  # noqa: E402

PASS, FAIL = [], []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(f"{name}{': ' + detail if detail else ''}")


# --- 1. Every V2 workflow DERIVES its turn cap; none hardcodes one ------------
for mod, script, expected in [(draft, "build-draft.sh", 250),
                              (refine, "build-refine.sh", 250),
                              (rpa, "review-pr.sh", 120)]:
    derived = int(act.v1_constant(script, "MAX_TURNS"))
    check(f"{script} derives MAX_TURNS={expected}", derived == expected, f"got {derived}")
    src = inspect.getsource(mod)
    check(f"{script} has no hardcoded max_turns literal",
          "max_turns=1" not in src and "max_turns=2" not in src)

# --- 2. Derivation FAILS LOUD rather than guessing ----------------------------
for bad, why in [("nonexistent.sh", "missing script"), ("build-draft.sh", "missing constant")]:
    try:
        act.v1_constant(bad, "MAX_TURNS" if bad == "nonexistent.sh" else "NO_SUCH_CONST")
        check(f"raises on {why}", False, "returned instead of raising")
    except (FileNotFoundError, ValueError):
        check(f"raises on {why}", True)

# --- 3. Isolation is UNCONDITIONAL — no ternary may skip the worktree ---------
# The regression this guards: `worktree_name=None if pr_number else worktree_name`
# put a --pr run on the operator's live working tree with no discard path.
# Isolation is established ONCE BY THE PARENT and passed down. Two children
# creating the same named worktree is `fatal: already exists`, which killed the
# draft->refine handoff — the round-1 fix was right in principle and applied at
# the wrong altitude.
for mod, name in [(draft, "build_draft"), (refine, "build_refine")]:
    src = inspect.getsource(mod)
    check(f"{name} does NOT create its own worktree", "act.worktree_add(" not in src)  # a CALL, not a mention in prose
    check(f"{name} receives a worktree path", "worktree: Path" in src)
    check(f"{name} does not conditionally skip isolation", "None if pr_number" not in src)

for mod, name in [(parent, "build"), (parent_minor, "build_minor")]:
    src = inspect.getsource(mod)
    check(f"{name} parent establishes isolation", "act.worktree_add(" in src)

# A negative outcome must be OBSERVED, never asserted — a banner once claimed
# nothing was pushed when 9 files had landed, costing a duplicate full run.
obs = inspect.getsource(act.observe_outcome)
check("observe_outcome reads git log", '"log"' in obs)
check("observe_outcome reads git status", '"status"' in obs)
check("observe_outcome refuses to guess when it cannot read",
      "cannot determine" in obs or "do not assume" in obs)
check("failure path reports observed state",
      "observed git state" in inspect.getsource(act.run_claude))

# --- 3b. PROMPT COMPLETENESS — every ${VAR} has a supplier -------------------
# Three prompt bodies once shipped MISSING behind 46 passing assertions, and a
# run then completed cleanly on two-thirds of its instructions. Exit 0 is not
# evidence a prompt arrived intact; only a check against the source is.
# MIGRATION-SCOPED: the reference is the bash original, so this retires with it.
import re as _re
_ASSISTANT = Path(__file__).resolve().parents[1] / "modules" / "assistant"
_PLACEHOLDER = _re.compile(r"\$\{([A-Z_][A-Z_0-9]*)\}")

for _prompt in sorted(_ASSISTANT.rglob("prompts/*.md")):
    _rel = str(_prompt).split("modules/assistant/")[-1]
    _names = set(_PLACEHOLDER.findall(_prompt.read_text()))
    # A supplier is either the workflow beside it or a promoted shared prompt.
    _wf_dir = _prompt.parent.parent
    _src = "".join(f.read_text() for f in _wf_dir.glob("*.py")) if _wf_dir.exists() else ""
    _shared = {p.stem.upper() for p in (_ASSISTANT / "prompts").glob("*.md")}
    _sibling = {p.stem.upper() for p in _prompt.parent.glob("*.md")}
    for _n in sorted(_names):
        _supplied = (f'"{_n}"' in _src) or (_n in _shared) or (_n in _sibling)
        check(f"{_rel}: ${{{_n}}} has a supplier", _supplied)
    # A wrapper prompt that references a stage body must find that body present.
    for _n in _names:
        if _n.startswith("STAGES_"):
            # The workflow may select a VARIANT (stages_1_to_4_from_plan.md),
            # so require a file whose stem starts with the placeholder name.
            check(f"{_rel}: a {_n.lower()}*.md body exists beside it",
                  any(f.stem.startswith(_n.lower()) for f in _prompt.parent.glob("*.md")))

# --- 4. The delegated contract's five variables are all supplied --------------
run_src = inspect.getsource(act.run_claude)
for var in ("LOG_FILE", "MAX_TURNS", "VERBOSE", "FORMATTER", "MODEL_KEY"):
    check(f"run_claude supplies {var}", f'"{var}"' in run_src)
check("env is built BEFORE the source line",
      run_src.index("LOG_FILE") < run_src.index('source "{runner}"'))
# Logs must never be written inside a worktree — they vanish with it, which
# made cost accounting impossible for two of five pipeline legs.
check("run_claude refuses a worktree as its log root", ".claude/worktrees" in run_src)
# review-pr must read the PR's branch, not the repo's checkout — V1 does
# `git worktree add -f ... origin/$PR_BRANCH` for exactly this reason.
from modules.assistant.review_pr import review_pr_workflow as _rpw  # noqa: E402
_rp = inspect.getsource(_rpw)
check("review_pr checks out the PR branch", "worktree_add(" in _rp and "headRefName" in _rp)
check("run_claude separates exec dir from log dir", "cwd = worktree or repo_root" in run_src)
check("run_claude STREAMS rather than capturing silently",
      "Popen" in run_src and "for line in proc.stdout" in run_src)  # a CALL, not prose

# --- 6. EXECUTABILITY — a name used but never imported ----------------------
# Tests import modules; they do not CALL into every branch. A NameError in an
# unexercised path stays invisible until a real run reaches it — which is how
# `_shared.worktree_add` crashed the LAST leg of a 40-minute pipeline, after the
# engineer had already flagged it and correctly declined to fix it in scope.
import shutil as _shutil  # noqa: E402
import subprocess as _sp  # noqa: E402

_root = Path(__file__).resolve().parents[1]
if _shutil.which("ruff"):
    _r = _sp.run(["ruff", "check", "--select", "F821", "--no-cache", "-q",
                  str(_root / "modules"), str(_root / "scripts"), str(_root / "tests")],
                 capture_output=True, text=True)
    check("no undefined names (ruff F821)", _r.returncode == 0, _r.stdout.strip()[:200])
else:
    check("ruff present for the F821 sweep", False, "install ruff or this guard is inert")


def test_all() -> None:
    """pytest entry — the module-level checks above populate PASS/FAIL.

    Wrapped rather than left as a module-level SystemExit: script-style tests
    crash pytest at COLLECTION with INTERNALERROR, so the whole suite ran zero
    tests while each file passed standalone. A guard that only fires when someone
    remembers to invoke it directly is a guard on borrowed time.
    """
    assert not FAIL, "\n".join(FAIL)


if __name__ == "__main__":
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAIL  {f}")
    raise SystemExit(1 if FAIL else 0)
