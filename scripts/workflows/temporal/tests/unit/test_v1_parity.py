"""Turn caps: ONE authority, read by both fleets, hardcoded by neither.

Exists because of a specific production failure: the V2 port RE-DECLARED V1's
constants instead of sharing them, a draft ran at MAX_TURNS=120 against V1's
250, and a full budget was spent producing nothing recoverable. V1's logs
already held the answer — the same task class had completed in 130 turns, so
the cap was set below a known-good measurement that existed at authoring time.

WHAT CHANGED, 2026-08-10. The first fix was `v1_constant()`: the Python fleet
recovered these integers by running a regex over the V1 bash scripts at
runtime. It did make divergence impossible, but it made the Python fleet unable
to START if the bash fleet were deleted — pointing the dependency at precisely
the fleet that is meant to go away — and it parsed an executable as data. The
authority is now `config.yaml`'s `max_turns:` map. Both fleets read it; neither
reads the other; deleting the bash fleet removes a reader, not a dependency.

The protection is unchanged and these tests still enforce it: **no cap is
stated as a literal anywhere**, and a missing one FAILS rather than defaults.
What changed is only where the single copy lives.

The module keeps its filename because six other files cite it by name.

The sibling files carry the rest of what the original single parity module
asserted: `test_isolation_invariants.py` (worktree isolation and observed
outcomes), `test_prompt_completeness.py` (every ${VAR} has a supplier) and
`test_delegated_contract.py` (the five variables run-claude.sh demands).

Section 4 is the other half of this module's job and is not about turn caps at
all: it is the EXECUTABILITY sweep, the class-level guard against a name that is
used but never imported. It lives here because it arrived here — it was added to
the single parity module and has to survive the split into siblings.
"""

from __future__ import annotations

import inspect
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from modules.assistant import assistant_activities as act
from modules.assistant.build.build_draft import build_draft_workflow as draft
from modules.assistant.build.build_refine import build_refine_workflow as refine
from modules.assistant.plan.plan_revision import plan_revision_workflow as plan_revision
from modules.assistant.review_pr import review_pr_activities as rpa

REPO_ROOT = Path(__file__).resolve().parents[5]
CONFIG = REPO_ROOT / "config.yaml"
WORKFLOWS = REPO_ROOT / "scripts" / "workflows"

# (module, its max_turns key, the value config declares today)
TURN_CAP_OWNERS = [
    pytest.param(draft, "build-draft", 250, id="build-draft"),
    pytest.param(refine, "build-refine", 300, id="build-refine"),
    pytest.param(rpa, "review-pr", 120, id="review-pr"),
    # Top-level in V1, not a child of `children/` — both locations are covered
    # by §2's bash-resolver test, which is where that distinction now lives.
    pytest.param(plan_revision, "plan-revision", 300, id="plan-revision"),
]


def _max_turns_map() -> dict:
    return yaml.safe_load(CONFIG.read_text())["max_turns"]


def _hardcodes_a_turn_cap(source: str) -> bool:
    """True when the source states a turn cap as a literal instead of reading it.

    Matches the two literal prefixes any realistic cap starts with (1xx, 2xx).
    Kept as a named predicate so the positive control below can prove it fires.
    """
    return "max_turns=1" in source or "max_turns=2" in source


# --- 1. The map is the single authority, and it is not empty ------------------

def test_the_max_turns_map_is_populated() -> None:
    """Vacuity guard for every other test in this file.

    Each check below reads the map. If `max_turns:` were renamed, emptied or
    dropped, the parametrized cases would collapse to nothing and the file
    would report green while asserting about an empty corpus. This test is the
    thing that fails first when that happens.
    """
    caps = _max_turns_map()
    assert len(caps) >= 13, f"max_turns: has only {len(caps)} entries — did the map get truncated?"
    assert all(isinstance(v, int) and v > 0 for v in caps.values()), (
        f"every cap must be a positive int: {caps}"
    )


@pytest.mark.parametrize(("_module", "key", "expected"), TURN_CAP_OWNERS)
def test_turn_cap_comes_from_config(_module, key: str, expected: int) -> None:
    assert act.max_turns(key) == expected, (
        f"config.yaml max_turns.{key} is now {act.max_turns(key)}, this suite expected "
        f"{expected}. If it changed deliberately, update the expectation here WITH a "
        "reason; a cap set below a known-good measurement burns a full budget for nothing."
    )


@pytest.mark.parametrize(("module", "key", "_expected"), TURN_CAP_OWNERS)
def test_no_workflow_hardcodes_a_turn_cap(module, key: str, _expected: int) -> None:
    source = inspect.getsource(module)
    assert not _hardcodes_a_turn_cap(source), (
        f"{module.__name__} states a turn cap as a literal instead of calling "
        f"act.max_turns({key!r}). Re-declaration is what let V2 run at 120 against "
        "V1's 250 — one authority makes divergence impossible rather than merely "
        "detectable."
    )


def test_no_bash_workflow_hardcodes_a_turn_cap() -> None:
    """The other half of the fleet, checked the same way.

    Both fleets read the same map, so both can break it the same way. Checking
    only the Python side would leave the bash side free to drift back to a
    literal — which is where all twelve of these values started.
    """
    offenders = [
        p.relative_to(REPO_ROOT)
        for p in WORKFLOWS.rglob("*.sh")
        if re.search(r"^MAX_TURNS=[0-9]", p.read_text(), re.M)
    ]
    assert not offenders, (
        f"these bash workflows hardcode a turn cap instead of reading config.yaml: {offenders}"
    )


def test_every_bash_workflow_cap_resolves_to_a_real_key() -> None:
    """A `config-value.sh` call naming a key the map does not have.

    The script fails loud at runtime, but at runtime means mid-dispatch, after
    a worktree and a branch already exist. This catches it at test time.
    """
    caps = _max_turns_map()
    bad = []
    for p in WORKFLOWS.rglob("*.sh"):
        for key in re.findall(r'config-value\.sh" max_turns ([\w-]+)', p.read_text()):
            if key not in caps and key not in _RETIRED_KEYS:
                bad.append((p.relative_to(REPO_ROOT), key))
    assert not bad, (
        f"bash workflows reference max_turns keys that do not exist: {bad}. "
        f"If the V2 workflow behind the key was RETIRED, declare the key in "
        f"`_RETIRED_KEYS` with the date and what absorbed it — the bash fleet is "
        f"frozen reference and is never edited to satisfy this check."
    )


#: Keys a V1 script still names because its V2 counterpart was RETIRED. The bash
#: fleet is FROZEN REFERENCE — it is never edited, not to fix a defect and not
#: to keep it in sync — so a workflow that no longer exists in V2 leaves a
#: dangling key here rather than a change there. Declared, dated, and with what
#: absorbed it, so the entry can be removed when the operator deletes the script.
_RETIRED_KEYS = {
    # 2026-08-28: `research-refresh` merged into `research-draft`, which now
    # computes the due set in code and routes each due topic to
    # `research-currency` itself. No V2 workflow owns this key.
    "research-refresh",
}


def test_hardcoded_cap_predicate_positive_control() -> None:
    """Positive control for the structural check above.

    Testing Standard § Structural tests need a positive control: without this,
    a rename or a changed call shape turns the grep into a permanent pass and
    nothing signals that it stopped looking.
    """
    assert _hardcodes_a_turn_cap("act.run_claude(prompt, max_turns=250)") is True
    assert _hardcodes_a_turn_cap("act.run_claude(prompt, max_turns=120)") is True
    assert _hardcodes_a_turn_cap("max_turns=act.max_turns('build-draft')") is False


# --- 2. Resolution FAILS LOUD rather than guessing ----------------------------

def test_python_resolution_raises_on_an_unknown_key() -> None:
    """A silent default here is the whole failure mode: a guessed cap looks like
    a working run right up until the budget is gone.
    """
    with pytest.raises(KeyError):
        act.max_turns("no-such-workflow")


@pytest.mark.parametrize(
    ("args", "expected_code"),
    [
        # Disjoint and deterministic, so each case names the ONE code it must
        # return. An over-broad assertion would still pass if a future edit
        # swapped which branch returns which.
        pytest.param(["max_turns", "no-such-workflow"], 1, id="unknown-key"),
        pytest.param(["no_such_map", "build-draft"], 1, id="unknown-map"),
        pytest.param(["max_turns"], 2, id="wrong-arity"),
    ],
)
def test_bash_resolution_exits_nonzero_rather_than_guessing(
    args: list[str], expected_code: int
) -> None:
    result = subprocess.run(
        [str(WORKFLOWS / "common" / "config-value.sh"), *args],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert result.returncode == expected_code, (
        f"config-value.sh {args} returned {result.returncode}, expected {expected_code}; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert not result.stdout.strip(), (
        f"a failing resolution must print NOTHING on stdout — a caller does "
        f"`MAX_TURNS=$(...)` and would assign the message: {result.stdout!r}"
    )


@pytest.mark.parametrize("key", ["build-draft", "plan-revision"])
def test_bash_and_python_resolve_the_same_value(key: str) -> None:
    """The two readers must agree, which is the property that replaced derivation.

    `build-draft` lives in `children/`, `plan-revision` at the workflows root —
    the two locations the old resolver had to search. Both now read one map, so
    location cannot make them disagree; this proves it.
    """
    result = subprocess.run(
        [str(WORKFLOWS / "common" / "config-value.sh"), "max_turns", key],
        capture_output=True, text=True, check=True, timeout=30,
    )
    assert int(result.stdout.strip()) == act.max_turns(key)


# --- 3. The bash fleet is deletable -------------------------------------------

def test_python_fleet_does_not_read_the_bash_fleet() -> None:
    """The regression this whole change exists to prevent.

    `v1_constant()` made the Python fleet unable to start if `children/*.sh`
    were deleted. The operator's stated intent is to delete the bash fleet when
    they stop using it, so any Python module that reads a `.sh` for a VALUE
    puts that back. Invoking shared infra (`run-claude.sh`, `format-stream.sh`)
    is a different thing and is not what this looks for.
    """
    component = Path(__file__).resolve().parents[2] / "modules"
    offenders = []
    for p in component.rglob("*.py"):
        for line in p.read_text().splitlines():
            if line.lstrip().startswith("#"):
                continue
            if re.search(r'(read_text|open|re\.search|regex)\b.*\.sh\b', line):
                offenders.append(f"{p.relative_to(component)}: {line.strip()[:90]}")
    assert not offenders, (
        "Python modules reading values out of bash scripts — this is the "
        f"v1_constant coupling coming back:\n" + "\n".join(offenders)
    )


# --- 4. EXECUTABILITY — a name that is used but never imported ----------------
#
# Tests IMPORT modules; they do not CALL into every branch. A NameError in an
# unexercised path stays invisible until a real run reaches it — which is how
# `_shared.worktree_add` crashed the LAST leg of a 40-minute pipeline, after the
# draft and refine legs had both completed real work and after the engineer who
# found it had correctly declined to fix it out of scope.
#
# ruff's F821 sweep closes the class without executing anything: it resolves
# every name in every module, including the branches no test reaches.

COMPONENT_ROOT = Path(__file__).resolve().parents[2]

# Everything this component ships that Python has to be able to resolve.
SWEEP_TARGETS = [COMPONENT_ROOT / name for name in ("modules", "scripts", "tests")]


# Wall-clock backstop. The sweep takes well under a second on this tree, so any
# value here is generous — the point is that an unbounded `subprocess.run` in
# test infrastructure that gates autonomous dispatch does not FAIL a stage when
# it goes wrong, it WEDGES one, and a wedged stage burns its whole turn budget
# with nothing to show. Same reason the root conftest bounds memory: a runaway
# must fail AS A TEST.
_RUFF_TIMEOUT_S = 60


def _ruff_f821(*targets: Path) -> subprocess.CompletedProcess[str]:
    """ruff's undefined-name check over `targets`, returncode 0 iff clean."""
    return subprocess.run(
        ["ruff", "check", "--select", "F821", "--no-cache", "-q", *(str(t) for t in targets)],
        capture_output=True,
        text=True,
        check=False,
        timeout=_RUFF_TIMEOUT_S,
    )


def test_ruff_is_installed_so_the_sweep_is_not_inert() -> None:
    """Absent ruff FAILS rather than skips.

    A skip here would report a green suite for a guard that never ran, which is
    the exact shape of the problem the sweep exists to remove. An inert guard is
    worse than no guard: it occupies the slot where a real one would go.
    """
    assert shutil.which("ruff"), (
        "ruff is not on PATH — the F821 executability sweep below cannot run. "
        "Install ruff (`pip install ruff`); do not skip this test."
    )


def test_no_undefined_names_in_the_component() -> None:
    result = _ruff_f821(*SWEEP_TARGETS)
    assert result.returncode == 0, (
        "ruff F821 found a name used but never bound — this is a live NameError "
        "waiting on the first run that reaches that branch, not a lint nit:\n"
        f"{result.stdout.strip()}"
    )


def test_the_sweep_detects_an_undefined_name(tmp_path: Path) -> None:
    """Positive control for the sweep above.

    Testing Standard § Structural tests need a positive control. Without it a
    changed flag, a renamed rule or a target list that stopped resolving turns
    the sweep into a permanent pass and nothing signals that it stopped looking.
    The probe reproduces the original defect verbatim: `_shared` used, never
    imported.
    """
    probe = tmp_path / "probe.py"
    probe.write_text("def crash():\n    return _shared.worktree_add()\n")

    result = _ruff_f821(probe)

    assert result.returncode != 0, "the F821 sweep did not fire on a known undefined name"
    assert "F821" in result.stdout, f"expected an F821 diagnostic, got: {result.stdout!r}"
