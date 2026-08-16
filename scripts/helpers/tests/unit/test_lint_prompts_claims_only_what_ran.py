"""`lint-prompts.sh` reports the passes that RAN, and never one that did not.

THE DEFECT (issue #57). The script ended with an unconditional literal —
"✓ prompt lint clean — every prompt block constructs, every MODEL_KEY resolves"
— printed whenever nothing had failed. Pass 3, the MODEL_KEY resolution check,
was guarded on `yq` being installed. On a machine without yq the pass did not
run and the line still claimed it had.

THE CONSEQUENCE IS THE PASS'S OWN USE CASE. Pass 3 exists to catch a RENAME:
`revision.sh` -> `revision-minor.sh` moved a script and its `config.yaml` key
apart while `MODEL_KEY` kept the old name, leaving the workflow unlaunchable and
silent about it until someone tried to dispatch. `workflow-scripts.md` tells an
operator to run this lint before committing exactly such a change. So the false
tick landed on the one situation it was written for. `cpi-decisions.md:536`:
*a gate that passes a broken file is worse than no gate*, because it converts
"I should test this" into "the gate says it's fine."

BOTH DIRECTIONS ARE ASSERTED, and one of them is why this file is not just a
grep for the removed string. A summary that stopped claiming anything would pass
a one-directional test while making the gate useless — so the pass that DID run
must still be claimed, with a non-zero count, and the pass that did not must be
named as not-run.

THE SCRIPT IS EXECUTED, NOT READ. A test that re-implemented the reporting logic
would pass forever against a script whose reporting had changed; `PATH` is the
real lever the defect rode in on, so the tests pull it.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
LINT = REPO_ROOT / "scripts" / "helpers" / "lint-prompts.sh"


def _path_without_yq() -> str:
    """The real PATH with every directory holding a `yq` removed.

    NOT a hardcoded `/usr/bin:/bin`. That happens to work on this workstation
    and encodes where yq is installed today into a test about yq being absent —
    and it would silently start testing something else the day a runner put yq
    in /usr/bin. Directories are dropped until `which` comes back empty, and the
    result is asserted, so the test cannot run green against a PATH that still
    resolves yq.
    """
    entries = os.environ.get("PATH", "").split(os.pathsep)
    kept = [e for e in entries if e and not (Path(e) / "yq").exists()]
    path = os.pathsep.join(kept)
    assert shutil.which("yq", path=path) is None, (
        f"the stripped PATH still resolves yq — this test would assert the "
        f"skip branch while running the pass: {path}"
    )
    # The lint needs a shell, awk, sed, grep, mktemp and cat. If stripping yq
    # took those out, the run would fail for an unrelated reason and the
    # assertions below would be reading noise.
    for tool in ("bash", "awk", "sed", "grep", "mktemp", "cat", "wc"):
        assert shutil.which(tool, path=path), f"{tool} is not on the stripped PATH"
    return path


def _run(*, path: str | None = None, strict: str | None = None,
         script: Path = LINT) -> subprocess.CompletedProcess:
    env = {**os.environ}
    if path is not None:
        env["PATH"] = path
    if strict is not None:
        env["LINT_PROMPTS_STRICT"] = strict
    else:
        env.pop("LINT_PROMPTS_STRICT", None)
    return subprocess.run([str(script)], capture_output=True, text=True, env=env)


# The claim's SHAPE, not the wording that happened to be wrong. A summary line
# that says a number of MODEL_KEYs resolved is the assertion Pass 3 is entitled
# to make; anything matching this while the pass did not run is the defect,
# whatever it is spelled like next time.
_RESOLVED_CLAIM = re.compile(r"(\d+)\s+MODEL_KEY\(?s?\)?\s+resolve", re.IGNORECASE)


# ---------------------------------------------------------------------------
# The state that produced the false report: Pass 3 cannot run.
# ---------------------------------------------------------------------------

def test_with_no_yq_the_summary_makes_no_MODEL_KEY_claim() -> None:
    """The defect, as an assertion. Exit stays 0 — the skip is not a failure."""
    r = _run(path=_path_without_yq())
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout + r.stderr
    assert not _RESOLVED_CLAIM.search(out), (
        f"the lint claimed MODEL_KEY resolution with yq absent — Pass 3 could "
        f"not have run:\n{out}"
    )
    assert "DID NOT RUN" in out and "yq is not installed" in out, out


def test_the_skip_names_the_class_it_leaves_uncovered() -> None:
    """A skip an operator cannot act on is a skip they will read past.

    The report has to say what is now unchecked and what to do, or the honest
    version of the defect is just a quieter version of it.
    """
    out = _run(path=_path_without_yq()).stdout
    assert "RENAME" in out, out
    assert "LINT_PROMPTS_STRICT=1" in out, out


def test_STRICT_turns_an_unrunnable_pass_into_a_failure() -> None:
    """The ruling lives in the script, so CI does not re-derive it.

    `.github/workflows/tests.yml` used to hand-roll `command -v yq || exit 1`
    around this lint precisely because the lint self-skipped. That is a second
    declaration of the script's own precondition, and second declarations drift.
    """
    r = _run(path=_path_without_yq(), strict="1")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "DID NOT RUN" in r.stdout, r.stdout
    assert not _RESOLVED_CLAIM.search(r.stdout + r.stderr)


# ---------------------------------------------------------------------------
# The state the report legitimately describes: Pass 3 runs.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("yq") is None, reason="Pass 3 needs yq to run")
def test_with_yq_the_summary_claims_the_keys_it_actually_resolved() -> None:
    """A gate that claims nothing is not a fix.

    The count is asserted NON-ZERO, which is the half a "did it stop lying"
    test cannot supply: Pass 3 skips any file with no `MODEL_KEY=` line, so a
    scoping mistake there yields a pass that examined nothing and reports a
    truthful, useless zero.
    """
    r = _run()
    assert r.returncode == 0, r.stdout + r.stderr
    m = _RESOLVED_CLAIM.search(r.stdout)
    assert m, f"the lint stopped claiming MODEL_KEY resolution with yq present:\n{r.stdout}"
    assert int(m.group(1)) > 0, r.stdout
    assert "DID NOT RUN" not in r.stdout, r.stdout


@pytest.mark.skipif(shutil.which("yq") is None, reason="Pass 3 needs yq to run")
def test_STRICT_is_a_no_op_when_every_pass_can_run() -> None:
    """STRICT must gate the SKIP, not the lint. If it failed here it would be
    an unusable flag and CI could not carry it."""
    assert _run(strict="1").returncode == 0


def test_every_pass_reports_a_population_it_examined() -> None:
    """Counts, not ticks — so the claim is checkable by eye.

    Shape-matched: every summary line under the tick either carries a number or
    says DID NOT RUN. A pass that reports neither is claiming a property with
    nothing behind it, which is this issue with a different subject.
    """
    lines = [ln for ln in _run().stdout.splitlines() if ln.startswith("    pass ")]
    assert len(lines) == 3, f"expected one line per pass, got: {lines}"
    for line in lines:
        assert re.search(r"\d+", line) or "DID NOT RUN" in line, line


# ---------------------------------------------------------------------------
# The same defect one layer down: a scan that examined nothing.
# ---------------------------------------------------------------------------

def test_a_scan_that_examined_NOTHING_is_a_failure_not_a_tick(tmp_path: Path) -> None:
    """Passes 1 and 2 iterate a glob, and a glob that matches nothing is a loop
    that runs zero times and falls through to the clean report.

    THE FIXTURE IS SELF-CONTAINED — a copy of the shipped script over an empty
    workflows/ tree, not the repo's own. A control that shares a fixture with
    the thing it is probing cannot tell its own effect from the fixture's.
    """
    helpers = tmp_path / "scripts" / "helpers"
    helpers.mkdir(parents=True)
    (tmp_path / "scripts" / "workflows").mkdir()
    (tmp_path / "config.yaml").write_text("models: {}\n")
    copy = helpers / "lint-prompts.sh"
    shutil.copy2(LINT, copy)

    r = _run(script=copy)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "examined nothing" in r.stdout, r.stdout
    assert "prompt lint clean" not in r.stdout, r.stdout


# ---------------------------------------------------------------------------
# The flag's OFF switch must switch it off.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("off", ["0", "false", "no", ""])
def test_the_STRICT_flag_is_OFF_for_every_spelling_of_off(off: str) -> None:
    """`LINT_PROMPTS_STRICT=false` used to turn strict mode ON.

    The first version read `STRICT="${LINT_PROMPTS_STRICT:-0}"` and gated on
    `!= "0"`, so every spelling but `0` enabled it — including `false`, which is
    the natural one: the script this sits beside in the fleet spells its booleans
    that way (`run-claude.sh`'s `VERBOSE` is "true"/"false", executed as a
    literal). A gate whose off-switch turns it on is this file's own subject with
    a different subject line — the flag reports a state the caller never asked
    for.

    Driven with yq ABSENT, because that is the only state where the flag's value
    changes the outcome; with yq present both settings exit 0 and the test would
    pass against the defect.
    """
    r = _run(path=_path_without_yq(), strict=off)
    assert r.returncode == 0, (
        f"LINT_PROMPTS_STRICT={off!r} was treated as ON:\n{r.stdout}{r.stderr}"
    )
    assert "DID NOT RUN" in r.stdout, r.stdout


@pytest.mark.parametrize("on", ["1", "true", "yes"])
def test_an_UNRECOGNISED_value_does_not_silently_disable_the_gate(on: str) -> None:
    """The error direction is chosen deliberately: unknown means ON.

    A typo'd value must not quietly turn a CI gate off — that failure is silent
    and green, which is the worse of the two.
    """
    assert _run(path=_path_without_yq(), strict=on).returncode == 1


def test_an_UNDELIMITABLE_prompt_block_FAILS_rather_than_vanishing(tmp_path: Path) -> None:
    """Pass 2's extractor used to `continue` past a block it could not delimit.

    Silently: no count, no message, no failure. So a block whose closing `)` the
    scan never found simply left the population, the summary's block count went
    down by one, and nothing said a prompt had gone unchecked. That is this
    script's own subject one layer down — a report that does not mention what it
    failed to look at — and the case it hides is the worst one, an unterminated
    heredoc.

    SELF-CONTAINED FIXTURE: a copy of the shipped script over a purpose-built
    workflows/ tree, so the control cannot be reading the repo's own health.
    """
    helpers = tmp_path / "scripts" / "helpers"
    helpers.mkdir(parents=True)
    wf = tmp_path / "scripts" / "workflows"
    wf.mkdir()
    (tmp_path / "config.yaml").write_text("models: {}\n")
    # One well-formed block so the vacuous-scan guard is satisfied and this test
    # reads the drop rather than the empty-tree failure, and one whose closing
    # `)` never arrives.
    (wf / "good.sh").write_text('PROMPT=$(cat <<EOF\nhello\nEOF\n)\n')
    (wf / "truncated.sh").write_text('PROMPT=$(cat <<EOF\nhello\nEOF\n')
    copy = helpers / "lint-prompts.sh"
    shutil.copy2(LINT, copy)

    r = _run(script=copy)
    assert r.returncode == 1, f"an unchecked prompt block was reported clean:\n{r.stdout}"
    assert "closing ')' was never found" in r.stdout, r.stdout
    assert "truncated.sh" in r.stdout, r.stdout
    assert "prompt lint clean" not in r.stdout, r.stdout
