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
from modules.assistant.build_draft import build_draft_workflow as draft  # noqa: E402
from modules.assistant.build_refine import build_refine_workflow as refine  # noqa: E402
from modules.assistant.review_pr import review_pr_activities as rpa  # noqa: E402

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
for mod, name in [(draft, "build_draft"), (refine, "build_refine")]:
    src = inspect.getsource(mod)
    check(f"{name} creates a worktree", "worktree_add" in src)
    check(f"{name} does not conditionally skip isolation",
          "None if pr_number" not in src)

# --- 4. The delegated contract's five variables are all supplied --------------
run_src = inspect.getsource(act.run_claude)
for var in ("LOG_FILE", "MAX_TURNS", "VERBOSE", "FORMATTER", "MODEL_KEY"):
    check(f"run_claude supplies {var}", f'"{var}"' in run_src)
check("env is built BEFORE the source line",
      run_src.index("LOG_FILE") < run_src.index('source "{runner}"'))

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print(f"  FAIL  {f}")
raise SystemExit(1 if FAIL else 0)
