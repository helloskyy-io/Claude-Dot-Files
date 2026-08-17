"""Every workflow's MODEL_KEY resolves to an entry in `config.yaml`.

WHY THIS EXISTS. `plan-sprint` shipped with no `config.yaml` entry. It was
caught at dispatch by `run-claude`'s own guard, which refuses to run on an
inherited default — but that guard is the LAST line, not the first. A key
missing here is a workflow that cannot launch at all, and it costs a burned
worktree and a dead run to discover. `build-minor` shipped unlaunchable the
same way.

WHY IT IS NOT COVERED ELSEWHERE. `lint-prompts.sh` performs this check for the
BASH fleet and has no knowledge of the Python tree — it does not glob
`modules/`, so every V2 workflow is invisible to it. Nothing else reads
`config.yaml` at test time.

This module carries § 7 of the pre-split root-level `test_v1_parity.py`. The
other sections of that file landed in this directory's siblings; this one is
here rather than appended to `test_v1_parity.py` because it is not a parity
assertion — it does not compare V2 against V1, it checks a V2 module against a
config file V1 never had a stake in.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
CONFIG = REPO_ROOT / "config.yaml"
ASSISTANT = Path(__file__).resolve().parents[2] / "modules" / "assistant"

_MODEL_KEY = re.compile(r'MODEL_KEY = "([a-z0-9-]+)"')


def _declared_keys() -> list[tuple[str, Path]]:
    """Every (key, declaring file) pair in the assistant tree.

    Both `*_workflow.py` and `*_activities.py` are swept: a key may be declared
    in either, and a sweep that missed one file class would report green over
    exactly the gap it exists to find.
    """
    found: list[tuple[str, Path]] = []
    for module in sorted(ASSISTANT.rglob("*_workflow.py")) + sorted(ASSISTANT.rglob("*_activities.py")):
        for key in _MODEL_KEY.findall(module.read_text()):
            found.append((key, module))
    return found


def _config_has(key: str, text: str) -> bool:
    """True when `key` appears as a two-space-indented mapping key.

    Anchored to the indent because a bare substring match would accept the key
    appearing inside a comment or a longer key, and this check is only worth
    having if a pass means the dispatcher will actually resolve it.
    """
    return re.search(rf"^  {re.escape(key)}:", text, re.M) is not None


def test_config_is_findable_from_the_test_suite() -> None:
    """Guards the path, not the keys.

    If `config.yaml` moves, every check below would silently pass on an empty
    key list rather than failing — the exact shape of a guard going inert.
    """
    assert CONFIG.is_file(), f"{CONFIG} is missing — the models map moved"


def test_at_least_one_model_key_was_discovered() -> None:
    """Positive control on the sweep itself.

    A regex that matched nothing would make every parametrised case below
    vacuous and the suite would report green over zero coverage. The assertion
    is only that the sweep finds SOME, so adding or removing a workflow does not
    make this test wrong.

    NO COUNT IS STATED HERE, and the sentence that used to state one was wrong.
    It read *"Eight keys are declared today"* against a real 13 declaring pairs
    over 12 distinct keys — a number nothing derives, in a docstring nothing can
    check, inoculated with the word *today* and stale anyway. The parametrised
    cases below enumerate the real set at collection time, so a reader who wants
    the count reads `pytest --collect-only` rather than a sentence.
    """
    assert _declared_keys(), (
        f"no MODEL_KEY declarations found under {ASSISTANT} — the sweep is inert, "
        f"which is indistinguishable from every key resolving"
    )


@pytest.mark.parametrize(
    ("key", "module"),
    _declared_keys(),
    ids=[f"{k}:{m.stem}" for k, m in _declared_keys()],
)
def test_model_key_resolves_in_config(key: str, module: Path) -> None:
    assert _config_has(key, CONFIG.read_text()), (
        f"{module.relative_to(REPO_ROOT)} declares MODEL_KEY '{key}', which has no "
        f"entry in config.yaml. This workflow CANNOT LAUNCH — run-claude refuses to "
        f"run on an inherited default. Add `  {key}: <model>` under `models:`."
    )


def test_a_missing_key_is_actually_detected() -> None:
    """Positive control on the predicate.

    `_config_has` returning True unconditionally would make every case above
    pass while checking nothing. This pins the failing direction, which is the
    one that matters.
    """
    text = CONFIG.read_text()
    assert not _config_has("a-key-no-workflow-declares", text)
