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
import tempfile
from pathlib import Path
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
LINT = REPO_ROOT / "scripts" / "helpers" / "lint-prompts.sh"


# Everything `lint-prompts.sh` reaches for as an external command.
#
# THIS LIST IS HAND-MAINTAINED. It said "DERIVED FROM THE SCRIPT" and gave a
# regeneration command, and that claim was false in the way this whole file is
# about: the command was
#   grep -oE '\b(awk|basename|bash|…|wc)\b' scripts/helpers/lint-prompts.sh | sort -u
# whose alternation IS this list. It confirms the listed tools are still used and
# CANNOT surface an unlisted one — measured by appending `sort /dev/null` to a
# copy of the script and re-running it: `sort` does not appear in the output. So
# the recipe answered a question nobody asked, under a heading claiming it
# answered the one that matters. A comment that says "derived" is read as a
# guarantee that the list cannot go stale, which is exactly when nobody rechecks
# it.
#
# WHAT DISCOVERS AN ADDITION IS EXECUTION, NOT A GREP, and it is
# `test_the_declared_tool_list_is_SUFFICIENT_and_NAMES_what_is_missing` below —
# it runs the lint under a PATH built from this list alone and extracts any
# `<cmd>: command not found` the run produces.
#
# THE TELL, because the failure mode is misleading and has already cost a
# debugging cycle: the first hand-written list omitted `env`, and the failure
# surfaced as "env: command not found" SIXTEEN TIMES, nested inside a
# sandbox-construction error. That names the lint, not the fixture, so it reads
# as a defect in the thing under test. If tests in this file fail with
# "<cmd>: command not found", the fixture is missing <cmd> — add it here.
#
# `cat` earns its place twice: the script also links it into its own `env -i`
# sandbox, which is the one thing reachable from inside a constructed block.
#
# `find` WAS LISTED HERE AND IS NOT USED. The script never invokes it; the only
# occurrence of the word is inside a comment ("a block whose closing `)` the scan
# could not find"). The deleted recipe *confirmed* it — the grep matched the
# comment — so the circular command did not merely fail to discover an addition,
# it actively vouched for an entry that was never real. Removed.
_LINT_NEEDS = ("awk", "basename", "bash", "cat", "dirname", "env",
               "grep", "ln", "mktemp", "rm", "sed", "wc")


def _path_without_yq() -> str:
    """A PATH that resolves everything the lint needs and NOT `yq`.

    BUILT BY SELECTION, NOT BY SUBTRACTION, and the difference is a CI outage.
    The first version took the real PATH and dropped every directory containing
    a `yq`. That is host-coupled in a way that is invisible on a workstation and
    fatal on a runner: here `yq` sits alone in /usr/local/bin, so dropping it
    costs nothing — but ubuntu-latest ships `yq` in the SAME directory as `bash`,
    `sed` and `awk`, so the subtraction took the shell out with it and eight
    tests failed on the merge gate with "bash is not on the stripped PATH" while
    the whole suite was green locally. A test about a missing `yq` must not be
    able to remove anything else.

    So: one directory of symlinks to the tools the lint needs, resolved from the
    real PATH, with no `yq` link made. Nothing else is reachable, which is also
    a tighter control — the lint cannot quietly satisfy Pass 3 through some other
    yaml reader.
    """
    sanitized = Path(tempfile.mkdtemp(prefix="lint-path-no-yq-"))
    for tool in _LINT_NEEDS:
        real = shutil.which(tool)
        assert real, f"{tool} is not installed — the lint cannot run at all"
        (sanitized / tool).symlink_to(real)
    path = str(sanitized)
    assert shutil.which("yq", path=path) is None, (
        f"the stripped PATH still resolves yq — this test would assert the "
        f"skip branch while running the pass: {path}"
    )
    for tool in _LINT_NEEDS:
        assert shutil.which(tool, path=path), f"{tool} is not on the sanitized PATH"
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


# ---------------------------------------------------------------------------
# THE CLASS, NOT THE REASON. Every way pass 3 can fail to run, driven.
#
# Pass 3 has THREE ways to not run, and only one of them — a missing `yq` — was
# driven. The other two shipped with nothing behind them, and one of those was
# shipped deliberately: a Decision Log entry recorded that its diagnostic was
# "currently unreachable — the summary it feeds only prints when `fail -eq 0`",
# so there was "no observable behaviour to drive". That premise was false. The
# STRICT branch reads the same variable and is NOT gated on `$fail`, and CI sets
# STRICT — so the untested thing was on the merge path the whole time.
#
# Enumerating the two missing reasons would close them and leave the fourth
# reason, whenever it is written, in exactly the position these two were in. So
# the population is DERIVED FROM THE SHIPPED SCRIPT: every `p3_skip="…"` it can
# assign must have a fixture here that produces it, and the enumeration test
# fails when a new reason is added without one.
# ---------------------------------------------------------------------------

_P3_SKIP_ASSIGNMENT = re.compile(r'p3_skip="([^"]+)"')

class _Fixture(NamedTuple):
    """How to build the tree that makes pass 3 report one particular reason.

    A NAMED TUPLE RATHER THAN A KWARGS DICT, because `strip_yq` is a property of
    the RUN (which PATH to use), not of the TREE, so a dict splatted into
    `_fixture_tree` had to be copied and popped at the call site first. The next
    reason added with a run-level knob would have repeated that, or raised an
    unhelpful TypeError when someone forgot.
    """
    config: bool
    model_key: bool
    strip_yq: bool


# Reason prefix -> the fixture that produces it. Prefixes, because two of the
# three reasons interpolate an absolute path that only exists at run time.
_DID_NOT_RUN_FIXTURES = {
    "yq is not installed": _Fixture(config=True, model_key=True, strip_yq=True),
    "no config.yaml at ": _Fixture(config=False, model_key=True, strip_yq=False),
    "no MODEL_KEY declarations found under ":
        _Fixture(config=True, model_key=False, strip_yq=False),
}


def _fixture_tree(tmp_path: Path, *, config: bool, model_key: bool,
                  pass1_fails: bool = False) -> Path:
    """A self-contained tree with a copy of the shipped script. Returns the copy.

    SELF-CONTAINED, NOT THE REPO'S OWN — the repo tree has a config.yaml and
    twelve MODEL_KEYs, so two of the three reasons below cannot be produced
    against it at all, and a control that shares a fixture with the thing it
    probes cannot tell its own effect from the fixture's.

    Pass 1 and pass 2 are given real work in every variant, because a tree that
    fails the vacuous-scan guard exits before pass 3 is ever summarised and the
    test would pass on the wrong exit path.
    """
    helpers = tmp_path / "scripts" / "helpers"
    helpers.mkdir(parents=True)
    wf = tmp_path / "scripts" / "workflows"
    wf.mkdir()
    if config:
        (tmp_path / "config.yaml").write_text('models:\n  build: "claude-opus-5"\n')

    lines = []
    if model_key:
        lines.append('MODEL_KEY="build"')
    lines.append('PROMPT=$(cat <<EOF\nhello\nEOF\n)')
    if pass1_fails:
        # An unescaped backtick in a multi-line double-quoted assignment: pass 1
        # reports it by line number and pass 2's sandbox cannot construct it.
        lines.append('NOTE="a line with `landmine` in it\nand a second line"')
    (wf / "a.sh").write_text("\n".join(lines) + "\n")

    copy = helpers / "lint-prompts.sh"
    shutil.copy2(LINT, copy)
    return copy


def _reasons_the_script_can_emit() -> tuple[str, ...]:
    reasons = tuple(sorted(set(_P3_SKIP_ASSIGNMENT.findall(LINT.read_text()))))
    assert reasons, (
        "no `p3_skip=\"…\"` assignment was found in lint-prompts.sh — either pass "
        "3 stopped recording why it did not run (in which case the summary is "
        "back to claiming a pass it may not have run) or this regex no longer "
        "matches how it records it. Both make the cases below vacuous."
    )
    return reasons


def test_every_DID_NOT_RUN_reason_the_SCRIPT_can_emit_IS_DRIVEN() -> None:
    """The enumeration check, in both directions.

    Forward: a reason the script can emit with no fixture here is a skip path
    nothing exercises — the position all three were in before, and the position
    two of them were still in after the first fix. Backward: a fixture for a
    reason the script can no longer emit is a test asserting against a deleted
    branch, which passes forever while covering nothing.
    """
    emitted = _reasons_the_script_can_emit()
    undriven = [r for r in emitted
                if not any(r.startswith(k) for k in _DID_NOT_RUN_FIXTURES)]
    assert not undriven, (
        f"pass 3 can report these reasons for not running, and no fixture below "
        f"produces them: {undriven}. Add one — an un-run pass that nothing drives "
        f"is how the STRICT branch shipped untested."
    )
    unreachable = [k for k in _DID_NOT_RUN_FIXTURES
                   if not any(r.startswith(k) for r in emitted)]
    assert not unreachable, (
        f"these fixtures produce reasons the script no longer emits: {unreachable}"
    )


@pytest.mark.skipif(shutil.which("yq") is None,
                    reason="two of the three reasons require yq to be present")
@pytest.mark.parametrize("reason", sorted(_DID_NOT_RUN_FIXTURES))
def test_each_DID_NOT_RUN_reason_is_NAMED_and_is_STRICT_failable(
    tmp_path: Path, reason: str,
) -> None:
    """Both directions per reason, which is what makes this more than coverage.

    Honest-skip direction: exit 0, and the report NAMES this reason rather than
    a generic one — collapsing them would tell an operator to install yq on a
    machine where yq is fine and the config file is what moved.
    Failure direction: under STRICT the same state is exit 1. A reason that is
    named but that STRICT cannot fail on is a gate declaration with nothing
    behind it.
    """
    spec = _DID_NOT_RUN_FIXTURES[reason]
    script = _fixture_tree(tmp_path, config=spec.config, model_key=spec.model_key)
    path = _path_without_yq() if spec.strip_yq else None

    skipped = _run(script=script, path=path)
    assert skipped.returncode == 0, (
        f"the honest skip for {reason!r} was not a skip:\n{skipped.stdout}"
    )
    assert "DID NOT RUN" in skipped.stdout, skipped.stdout
    assert reason in skipped.stdout, (
        f"pass 3 did not run and the report did not say it was because of "
        f"{reason!r}:\n{skipped.stdout}"
    )
    assert not _RESOLVED_CLAIM.search(skipped.stdout), skipped.stdout

    strict = _run(script=script, path=path, strict="1")
    assert strict.returncode == 1, (
        f"STRICT did not fail on {reason!r} — a pass that cannot run is a "
        f"failure:\n{strict.stdout}"
    )
    assert reason in strict.stdout, strict.stdout


@pytest.mark.skipif(shutil.which("yq") is None, reason="the fixture needs yq present")
def test_pass_3s_own_diagnostic_SURVIVES_an_unrelated_pass_1_failure(
    tmp_path: Path,
) -> None:
    """The reason `p3_seen` exists, and the case its `$fail` keying suppressed.

    The diagnostic used to be keyed on the GLOBAL `$fail`, which passes 1 and 2
    also write. So on a run where pass 1 failed AND pass 3 examined nothing, the
    "examined nothing" diagnostic was suppressed — a state that WAS established
    and then not reported because an unrelated check happened to have failed.
    That is this file's subject inverted, and it is the broken-checkout shape the
    whole summary redesign exists for: several things wrong at once.

    DRIVEN THROUGH STRICT, WHICH IS THE MERGE PATH. `.github/workflows/tests.yml`
    sets LINT_PROMPTS_STRICT=1, and the STRICT branch is not gated on `$fail`, so
    this output is on the gate rather than in a summary that a failing run never
    prints. The Decision Log entry that shipped this fix untested reasoned from
    the summary alone and concluded there was nothing observable to drive.
    """
    script = _fixture_tree(tmp_path, config=True, model_key=False, pass1_fails=True)
    r = _run(script=script, strict="1")

    assert r.returncode == 1, r.stdout
    assert "unescaped backtick" in r.stdout, (
        f"the fixture was supposed to fail pass 1 — without that this test "
        f"passes against the old $fail keying:\n{r.stdout}"
    )
    assert "pass 3" in r.stdout and "DID NOT RUN" in r.stdout, r.stdout
    assert "no MODEL_KEY declarations found" in r.stdout, (
        f"a pass-1 failure suppressed pass 3's report that it examined "
        f"nothing:\n{r.stdout}"
    )


# ---------------------------------------------------------------------------
# The fixture's own dependency list, checked by execution rather than asserted.
# ---------------------------------------------------------------------------

def test_the_declared_tool_list_is_SUFFICIENT_and_NAMES_what_is_missing() -> None:
    """`_LINT_NEEDS` is hand-maintained, so something has to discover additions.

    THE DISCRIMINATOR IS THE PAIR OF RUNS, NOT THE OUTPUT OF EITHER. A lint that
    fails under the sanitized PATH is either a broken tree or a short tool list,
    and the failure text cannot tell them apart — a missing fixture tool surfaces
    INSIDE a sandbox-construction error, which is the shape of a genuine prompt
    defect. Running the same script under the real PATH separates them: same
    tree, same script, only PATH differs, so a clean real run plus a failing
    sanitized run isolates the cause to this list.
    """
    real = _run()
    assert real.returncode == 0, (
        f"the repo's own prompts do not lint clean under the real PATH. That is "
        f"a TREE defect, not a fixture defect, and it has to be fixed before "
        f"this test can discriminate:\n{real.stdout}{real.stderr}"
    )

    sanitized = _run(path=_path_without_yq())
    missing = sorted(set(re.findall(
        r"\b([A-Za-z0-9_.-]+): command not found", sanitized.stdout + sanitized.stderr
    )))
    assert sanitized.returncode == 0 and not missing, (
        f"lint-prompts.sh reaches for {missing or 'a command'} that _LINT_NEEDS "
        f"does not provide. THIS IS A FIXTURE DEFECT, NOT A LINT DEFECT: the same "
        f"script exits 0 under the real PATH. Add {missing or 'it'} to "
        f"_LINT_NEEDS.\n{sanitized.stdout}{sanitized.stderr}"
    )
