"""Every configured hook declares a timeout.

WHY THIS EXISTS. A hook sits on the critical path of the event it matches — a
`PreToolUse` hook runs before EVERY matching tool call, and nothing proceeds
until it answers. With no `timeout` declared, "does not answer" has no upper
bound.

MEASURED 2026-08-14: `block-dangerous.sh` ran 8m44s at 99.9% CPU on a single
11 KB tool call and was still going when it was killed by hand. It held a live
build for the whole of it, and the run had already been going 4h18m. Neither
hook declared a timeout, so nothing in the system was ever going to stop it.

WHAT THIS TEST IS NOT. It is not a claim that any current hook is slow — the
cause of that incident is fixed and `test_the_hook_stays_fast_on_a_large_command`
holds the line on cost. This is the second, independent guarantee: even a hook
whose cost nobody has measured, or one that blocks on a network call or a lock,
gives the session back within a bounded time.

THE TWO GUARDS ARE DELIBERATELY DIFFERENT SHAPES. A latency test says "this
known hook is fast on this known input". A declared timeout says "no hook, on
any input, hangs forever". The first cannot cover an input nobody thought of;
the second cannot tell you a hook got slower. Neither subsumes the other.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SETTINGS = REPO_ROOT / "config" / "settings.json"

# A hook that has not answered in this long is not answering. Generous on
# purpose: the point is to bound the pathological case, not to police normal
# cost, and a ceiling tight enough to fire on a slow machine would get raised
# until it meant nothing.
MAX_REASONABLE_TIMEOUT_SECONDS = 120


def _configured_hooks() -> list[tuple[str, dict]]:
    """Every hook entry in settings.json, as (event_name, hook_dict)."""
    settings = json.loads(SETTINGS.read_text())
    found: list[tuple[str, dict]] = []
    for event, matchers in (settings.get("hooks") or {}).items():
        for matcher in matchers:
            for hook in matcher.get("hooks") or []:
                found.append((event, hook))
    return found


def test_settings_json_is_parseable() -> None:
    """A malformed settings.json silently disables EVERY setting in the file.

    Asserted first and on its own, because every other test here would
    otherwise fail with a JSONDecodeError that buries the real cause.
    """
    settings = json.loads(SETTINGS.read_text())
    assert isinstance(settings.get("hooks"), dict), (
        f"{SETTINGS} parsed but declares no `hooks` object. If hooks were "
        f"deliberately removed, delete this suite in the same commit — a guard "
        f"over an empty set passes forever while guaranteeing nothing."
    )


def test_every_configured_hook_declares_a_timeout() -> None:
    hooks = _configured_hooks()
    assert hooks, (
        "no hooks found in settings.json — this guard would pass vacuously. "
        "Either hooks moved, or the structure changed under this scanner."
    )

    unbounded = [
        (event, hook.get("command") or hook.get("prompt") or hook.get("url") or "?")
        for event, hook in hooks
        if hook.get("timeout") is None
    ]
    assert not unbounded, (
        "these hooks declare no `timeout`, so they can hang the session with no "
        "upper bound:\n"
        + "\n".join(f"  {event}: {what}" for event, what in unbounded)
        + f"\n\nAdd `\"timeout\": <seconds>` to each. On 2026-08-14 an unbounded "
        f"`PreToolUse` hook burned 8m44s of a single tool call at 99.9% CPU and "
        f"had to be killed by hand, holding a live build."
    )


def test_no_hook_timeout_is_so_large_it_is_not_a_bound() -> None:
    """A ceiling nobody would ever reach is a declaration, not a guarantee.

    Split from the presence check deliberately: they fail for different reasons
    and want different fixes. Bundling them would report "add a timeout" for a
    hook that already has one.
    """
    excessive = [
        (event, hook.get("command", "?"), hook["timeout"])
        for event, hook in _configured_hooks()
        if hook.get("timeout") is not None
        and hook["timeout"] > MAX_REASONABLE_TIMEOUT_SECONDS
    ]
    assert not excessive, (
        f"these hooks declare a timeout above {MAX_REASONABLE_TIMEOUT_SECONDS}s:\n"
        + "\n".join(f"  {event}: {cmd} ({t}s)" for event, cmd, t in excessive)
        + "\n\nA hook blocking a session for minutes is the failure this bound "
        "exists to prevent, whether or not a number was written down. If a hook "
        "genuinely needs that long, it should be `async` instead of blocking."
    )
