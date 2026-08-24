"""`block-detached-dispatch.sh` blocks `nohup` in COMMAND POSITION and nothing else.

THE CLAIMS IN THE HOOK ARE EXECUTABLE. Its header carries `MUST BLOCK:` and
`MUST ALLOW:` lines; this module parses them out and drives each one through the
real hook. A claim that stops being true fails here rather than sitting in a
comment being wrong — the same mechanism `test_block_dangerous.py` uses next
door, and for the same reason: the four boundary defects that mechanism found in
its neighbour were all in the ALLOW direction, where an unchecked claim reads
exactly like a checked one.

WHY THE ALLOW HALF IS THE HALF THAT MATTERS HERE. The rule this hook enforces is
discussed all over this repository — the memory file says "NEVER nohup",
`personal-tooling.md` describes the failure, the hook's own header uses the word
nineteen times. A substring match would deny `grep -rn nohup`, and would deny
editing any of them. **The blocking half of this hook is easy and the boundary is
the entire design**, which is why the MUST ALLOW corpus below is deliberately
made of real commands someone would actually run while working ON this rule.

WHAT THIS DOES NOT ASSERT, stated so the gap is visible rather than assumed:

  * That `&`, `setsid`, `disown`, `screen -dm` or `tmux new -d` are blocked.
    They are NOT, deliberately. The operator ruled on 2026-08-24 to cover the
    observed failure only — `nohup` — rather than the whole detach class, on
    the same reasoning applied to the build family's write boundary two days
    earlier: do not build for a failure that has not happened. `&` is the one
    with a real argument behind it, because it is an independent path rather
    than a substitute a blocked run would reach for. If it is observed, it goes
    here, and the deny message is already written.
  * That the hook is WIRED. `test_hook_settings.py` owns that question for the
    whole hooks directory; a hook that works and is not registered is that
    module's finding, not this one's.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
HOOK = REPO / "config" / "hooks" / "block-detached-dispatch.sh"
HOOK_TIMEOUT_S = 15

_CLAIM = re.compile(r"^\s*#\s*(?P<kind>MUST BLOCK|MUST ALLOW):\s*(?P<command>.+?)\s*$")


@dataclass(frozen=True)
class HookResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def decision(self) -> str:
        """`deny`, or `allow` when the hook emitted nothing.

        Silence IS allow for a PreToolUse hook that exits 0, so this collapses
        the two shapes a permitted command can take into the one word the
        assertions read.
        """
        if not self.stdout.strip():
            return "allow"
        payload = json.loads(self.stdout)
        return payload["hookSpecificOutput"]["permissionDecision"]


def run_hook_raw(stdin: str, env: dict[str, str] | None = None) -> HookResult:
    proc = subprocess.run([str(HOOK)], input=stdin, capture_output=True,
                          text=True, timeout=HOOK_TIMEOUT_S, env=env)
    return HookResult(proc.returncode, proc.stdout, proc.stderr)


def run_hook(command: str, tool_name: str = "Bash") -> HookResult:
    return run_hook_raw(json.dumps({"tool_name": tool_name,
                                    "tool_input": {"command": command}}))


def _claims(kind: str) -> list[str]:
    return [m.group("command") for line in HOOK.read_text().splitlines()
            if (m := _CLAIM.match(line)) and m.group("kind") == kind]


# --- the corpus is real, before anything is asserted about it ----------------

def test_the_hook_exists_and_is_executable() -> None:
    """If it moves or loses its bit, every assertion below passes against nothing."""
    assert HOOK.is_file(), f"{HOOK} is where this module's subject lives"
    assert HOOK.stat().st_mode & 0o111, f"{HOOK} is not executable, so the hook cannot run"


def test_BOTH_CLAIM_KINDS_ARE_PRESENT_IN_USEFUL_NUMBERS() -> None:
    """A vacuity floor, and the ALLOW half carries the higher bar on purpose.

    A parser that silently stops matching turns every parametrized test below
    into zero test cases, which reports as a pass. The floors are what make that
    failure loud. ALLOW is floored higher than BLOCK because this hook's whole
    difficulty is the boundary: blocking `nohup x` is one regex, and not blocking
    the eleven places this repo TALKS about `nohup` is the design.
    """
    must_block, must_allow = _claims("MUST BLOCK"), _claims("MUST ALLOW")
    assert len(must_block) >= 4, (
        f"only {len(must_block)} MUST BLOCK claims parsed out of {HOOK.name} — "
        f"either the claims were removed or `_CLAIM` stopped matching them")
    assert len(must_allow) >= 5, (
        f"only {len(must_allow)} MUST ALLOW claims parsed out of {HOOK.name}. "
        f"The ALLOW direction is where this hook can go wrong without anyone "
        f"noticing, so it carries the higher floor.")


@pytest.mark.parametrize("command", _claims("MUST BLOCK"))
def test_every_MUST_BLOCK_claim_is_actually_BLOCKED(command: str) -> None:
    assert run_hook(command).decision == "deny", (
        f"the hook's header claims this is blocked and it is not: {command!r}")


@pytest.mark.parametrize("command", _claims("MUST ALLOW"))
def test_every_MUST_ALLOW_claim_is_actually_ALLOWED(command: str) -> None:
    assert run_hook(command).decision == "allow", (
        f"the hook's header claims this passes and it was DENIED: {command!r}. "
        f"A false positive here blocks someone working on this very rule.")


# --- the boundary, beyond the claims -----------------------------------------

@pytest.mark.parametrize("command", [
    "nohup ./x &",
    "true && nohup ./x",
    "true || nohup ./x",
    "true | nohup ./x",
    "true ; nohup ./x",
    "$(nohup ./x)",
    "  nohup ./x",
    "true\nnohup ./x",          # second LINE of a multi-line command
])
def test_COMMAND_POSITION_is_reached_through_every_separator(command: str) -> None:
    """A separator the pattern misses is a hole, and a multi-line command is the
    likeliest one: the second command of a heredoc-free two-liner sits at a line
    start the pattern must anchor to, not at the start of the string."""
    assert run_hook(command).decision == "deny", f"reached command position undetected: {command!r}"


def test_a_BACKTICK_IS_NOT_A_SEPARATOR_and_this_hook_proved_it_on_itself() -> None:
    """THE REGRESSION. A backtick WAS in the separator class for one commit.

    The reasoning was that a backtick opens legacy command substitution, which is
    true and almost never how anyone writes it. What a backtick actually opens in
    this repository is inline code, and backtick-word-space is how every
    document, commit message and comment here refers to a command.

    So the hook denied THE COMMIT THAT INTRODUCED IT — the message quoted the
    command inline — and the thirty-five tests written alongside it all passed,
    because every ALLOW case had the word preceded by a SPACE. The corpus was
    real and the shape was missing, which is the failure this whole module is
    shaped against.

    `$(...)` is the substitution form in use and `(` still covers it, so the
    true positive traded away costs nothing measurable and the false positive
    removed was guaranteed.
    """
    assert run_hook(f"echo 'see {chr(96)}nohup ./x{chr(96)} above'").decision == "allow", (
        "backtick-quoted inline code is a MENTION; it was denied for one commit")
    assert run_hook(f"$(nohup ./x)").decision == "deny", (
        "`$(...)` is the substitution form actually in use and must still deny")


@pytest.mark.parametrize("command", [
    "echo nohup",
    "cat notes-about-nohup.md",
    "python -c \"print('nohup')\"",
    "sed -i 's/nohup/run_in_background/' README.md",
    "rg --files-with-matches nohup",
    "echo 'the pattern denies `nohup ./x` in command position'",
    "git commit -m 'quoting `nohup ./build.sh &` inline'",
])
def test_a_MENTION_of_nohup_is_not_a_USE_of_it(command: str) -> None:
    """The failure mode that narrowed the neighbouring hook from 59 patterns to 5.

    Seven of eight denials it recorded on 2026-08-15 were dangerous text
    appearing as DATA. Every command here is one a person would run while
    reading, writing or fixing this rule, and denying any of them makes the hook
    the obstacle it exists to remove.
    """
    assert run_hook(command).decision == "allow", f"denied a MENTION, not a use: {command!r}"


# --- it fails OPEN, which is the opposite of its neighbour -------------------

@pytest.mark.parametrize("stdin,label", [
    ("", "empty stdin"),
    ("   ", "whitespace only"),
    ("not json at all", "unparseable"),
    ("[1,2,3]", "a JSON array, not an object"),
    ('{"tool_input":{"command":"nohup x"}}', "no tool_name"),
    ('{"tool_name":"Bash"}', "no tool_input"),
    ('{"tool_name":"Bash","tool_input":{"command":["nohup","x"]}}', "command is not a string"),
])
def test_an_UNREADABLE_EVENT_passes_through(stdin: str, label: str) -> None:
    """Deliberate, and the direction follows the CONSEQUENCE rather than convention.

    `block-dangerous.sh` denies what it cannot parse because it guards
    UNRECOVERABLE actions: a missed deny is a disaster, a wrong deny is an
    inconvenience. Here the sign is reversed. A missed deny costs one detached
    process the operator can find and kill; a wrong deny halts ordinary work to
    prevent nothing. Two hooks, two directions, and the reason is written in each.
    """
    result = run_hook_raw(stdin)
    assert result.decision == "allow", f"{label}: should pass through, got {result.stdout!r}"
    assert result.returncode == 0, f"{label}: exited {result.returncode}"


def test_a_NON_BASH_TOOL_is_not_policed() -> None:
    """`nohup` inside a file being written is not a command being run."""
    assert run_hook("nohup ./x &", tool_name="Write").decision == "allow"


def test_the_DENY_MESSAGE_NAMES_THE_REPLACEMENT() -> None:
    """A refusal that does not say what to do instead gets worked around.

    This hook exists because an INSTRUCTION was ignored — the operator's memory
    file has said "NEVER nohup" for weeks. The message is the part that has to do
    better than the instruction did, so it is asserted rather than assumed.
    """
    reason = json.loads(run_hook("nohup ./x &").stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "run_in_background" in reason, "the message must name the replacement, not just refuse"
    assert "true" in reason, "it must give the value too — `run_in_background: true`"
    for why in ("notifies", "output", "track"):
        assert why in reason.lower(), (
            f"the message should say what detaching COSTS ({why!r}); a bare "
            f"prohibition teaches nothing and gets rediscovered next week")
