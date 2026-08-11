#!/usr/bin/env python3
"""The RUN LOG surface — one declaration of what it holds and how it is read.

WHAT THIS IS. Three phases each added a PARENT-WRITTEN observable to the per-run
JSONL log under `<main checkout>/.claude/logs/`: `parent_route` (Phase 3),
`convergence` (Phase 5) and `run_resources` (Phase 4's telemetry). Together they
are a memory surface — three member event types, a join key, a reader family with
its own written discipline (`README.md`) and a rule for adding a fourth. It had
every property of a surface except a name, and no committed tool read any of it.

THE PROSE HOME IS THE `memory-model.md` AMENDMENT drafted as candidate 10 of the
Memory Management Framework roadmap, which is the operator's to ratify. THIS
module is the machine-checkable half: the member set below is the one a test
compares against the `_append_run_event` call sites, so a fourth event type fails
here rather than waiting years for somebody to notice it has no reader.

WHY A SHARED MODULE RATHER THAN THREE COPIES. `assistant_activities._log_events`
already carries the rule that a run log's stream interleaves non-JSON and a
reader must SKIP a malformed line rather than raise. Three replay tools each
re-deriving that is three chances to get it differently, and the surface's whole
problem was that its rules lived in one member's docstring.

DEPENDENCY-FREE ON PURPOSE, like `convergence.py`. It imports no sibling, so a
tool can load it by path without dragging the workflow tree — and its
`temporalio` import — into a measurement helper.

PUBLISH CLASSIFICATION — THE RULE, NOT A NOTE. Two of the three member types
share a file with the CLI's own transcript, so this surface is co-resident with
prompt text, tool inputs and tool results. Readers here route their output into
committed docs and PR comments.

  * PUBLISHABLE: any value drawn from a vocabulary declared in THIS repo's code
    or config — enums, booleans, counts, byte totals, timestamps, `run_id`s, log
    file names, config keys.
  * NOT PUBLISHABLE: any value whose text was authored by the model or arrived
    from a tool input or result — finding `id` slugs, titles, prose.

`PUBLISHABLE_FIELDS` below states it per event type and
`test_run_log.py` fails on a reader that emits anything else. The control one
level over is `exit_record._redact()`, which drops `tool_input` at read time for
the same reason: publishing verbatim would put a run's command history and
filesystem layout permanently in a PR comment.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# --- the surface -------------------------------------------------------------

# THE MEMBER SET. Adding a fourth event type means adding it here, and
# `test_run_log_surface.py` fails in BOTH directions — an undeclared writer, and
# a declared type nobody writes.
MEMBER_EVENT_TYPES = frozenset({"parent_route", "run_resources", "convergence"})

# THE JOIN KEY. All three members carry it. Its VALUE was out of conformance
# until this phase: `run_resources` wrote `log_file.stem`
# (`{model_key}-{stamp}-{nonce}`) against the other two's bare `uuid4().hex`, so
# the surface's own join key joined nothing. See `CUTOVERS['bare_run_id']`.
JOIN_KEY = "run_id"

# Fields a reader may emit. Everything else in a payload is either derived from
# these or is model-authored text — `convergence`'s id lists are the live hazard,
# because they read like identifiers and are model-authored slugs.
PUBLISHABLE_FIELDS = {
    "parent_route": frozenset({
        "type", "run_id", "pr", "routed_outcome", "undetermined_reason",
        "hold_kind", "shadow_verdict", "shadow_parseable", "channels_agree",
    }),
    "run_resources": frozenset({
        "type", "run_id", "model_key", "workflow_key", "started_at", "ended_at",
        "measured", "unmeasured_reason", "peak_anon", "peak_total", "mean_total",
        "pids_peak", "high_events", "oom_kills", "tool_result_bytes",
        "subagents_spawned", "samples", "limits",
    }),
    # `state`, `reason`, `stalled`, `asserted_converged` and `agrees` are typed
    # values the parent computed. `passes` is a count. Every `*_ids` list is
    # model-authored and is deliberately ABSENT: a reader reports its LENGTH.
    "convergence": frozenset({
        "type", "run_id", "pr", "state", "reason", "passes", "stalled",
        "asserted_converged", "agrees",
    }),
}

# --- cutovers ----------------------------------------------------------------
#
# A DENOMINATOR THAT STARTS SOMEWHERE, STATED AS A COMMIT AND A CLOCK. Every
# figure over this surface runs over a corpus that changed shape underneath it,
# and a rate quoted across a cutover is a rate over two different measurements.
#
# The clock is the LOG FILE'S OWN STAMP, which `claude_log_path` writes as local
# `%Y%m%d-%H%M%S`, compared as a string against the commit's local time. The
# direction is sound: a process imports its Python at start, so a log stamped
# BEFORE a commit ran the pre-commit code whatever time it finished, and one
# stamped after is guaranteed post-commit. It is a stated cutover rather than an
# inference from the payload — the difference `memory-model.md` §6.1 draws
# between an ADDRESS and a LOCATION.
CUTOVERS = {
    # `a623c25` — the sampler read `/proc/PID/cgroup` before systemd had migrated
    # the child, so it measured the CALLER'S SESSION SCOPE. Records before this
    # are not this fleet's telemetry at all; they are the editor session, and
    # they are large and plausible, which is why they have to be excluded by
    # name rather than left to look like outliers.
    "child_scope_measured": ("a623c25", "20260810-170915"),
    # `b8d7aa7` — `run_id`, `model_key`, `started_at`, `ended_at` on the report.
    # Figure 4 (overlapping-run aggregate) is zero before it.
    "identity_fields": ("b8d7aa7", "20260810-181431"),
    # THIS PHASE. `workflow_key` on the payload, `run_id` carrying the bare
    # nonce, and the sub-agent counter matching the tool the CLI actually emits.
    # Left as None until it lands: a cutover stamp invented in advance is a
    # figure with a fabricated derivation.
    "bare_run_id": ("this phase", None),
    "workflow_key": ("this phase", None),
    "subagent_counter_fixed": ("this phase", None),
}


# --- reading -----------------------------------------------------------------

def default_log_dir(start: Path | None = None) -> Path:
    """The archive, which lives in the MAIN CHECKOUT and never in a worktree.

    `.claude/` is globally gitignored, so a worktree has no `logs/` and a tool
    defaulting to its own tree reports an empty corpus — loud, but it diagnoses
    badly. `replay_completion_predicate.py`'s docstring records the same trap.
    This walks UP out of `.claude/worktrees/<name>/` when it finds itself
    inside one, so the normal dispatch shape resolves the real archive.
    """
    here = (start or Path(__file__)).resolve()
    parts = here.parts
    if ".claude" in parts and "worktrees" in parts:
        root = Path(*parts[: parts.index(".claude")])
    else:
        root = Path(__file__).resolve().parents[3]
    return root / ".claude" / "logs"


def logs(log_dir: Path) -> list[Path]:
    return sorted(log_dir.glob("*.jsonl"))


def stamp_of(path: Path) -> str | None:
    """`review-pr-20260810-193251-27add0….jsonl` -> `20260810-193251`.

    None when the name does not carry one — the V1 fleet's shape is
    `{key}-{stamp}` and predates every member of this surface, so a name with no
    stamp is a log with no parent-written events and is skipped rather than
    guessed at.
    """
    parts = path.stem.split("-")
    for i in range(len(parts) - 1):
        if len(parts[i]) == 8 and parts[i].isdigit() and \
                len(parts[i + 1]) == 6 and parts[i + 1].isdigit():
            return f"{parts[i]}-{parts[i + 1]}"
    return None


def model_key_of(path: Path) -> str | None:
    """The log name's leading segment, which `claude_log_path` writes as the
    MODEL key. It is NOT the workflow key — `config.yaml`'s comment above
    `research-write:` states the two are not 1:1 — which is exactly why this
    phase adds `workflow_key` to the payload instead of parsing harder.
    """
    stamp = stamp_of(path)
    if stamp is None:
        return None
    head = path.stem.split("-" + stamp.split("-")[0])[0]
    return head or None


def workflow_keys_by_model_key(repo_root: Path) -> dict[str, list[str]]:
    """`{model_key: [workflow_key, ...]}`, DERIVED from the workflow modules.

    NOT RESTATED AS A LITERAL, and not read out of `config.yaml` either. The
    pairing lives in the modules — each declares `MODEL_KEY` and `WORKFLOW_KEY`
    side by side — and `config.yaml`'s `models:` map has one `research:` row
    against two workflows, so it cannot answer this question at all. Deriving it
    means a NEW colliding pair is picked up by every reader on the day it is
    written, instead of on the day somebody remembers to update a tuple.

    A model key with more than one entry is AMBIGUOUS: a record carrying only
    `model_key` cannot be attributed to a workflow, and a per-workflow figure
    must name those records as excluded rather than bin them arbitrarily.
    """
    pattern_model = re.compile(r'^MODEL_KEY = "([^"]+)"', re.M)
    pattern_workflow = re.compile(r'^WORKFLOW_KEY = "([^"]+)"', re.M)
    found: dict[str, list[str]] = {}
    root = repo_root / "scripts" / "workflows" / "temporal" / "modules" / "assistant"
    for path in sorted(root.rglob("*.py")):
        if "tests" in path.parts:
            continue
        text = path.read_text(errors="replace")
        model = pattern_model.search(text)
        workflow = pattern_workflow.search(text)
        if not workflow:
            continue
        # `review-pr` declares the two in SIBLING modules (`review_pr_helper`
        # holds MODEL_KEY, `review_pr_activities` holds WORKFLOW_KEY), so a
        # module with a workflow key and no model key falls back to its own key
        # as the model key. That is true for every such module today and the
        # test asserts the derived map against the tree rather than trusting it.
        key = model.group(1) if model else workflow.group(1)
        found.setdefault(key, [])
        if workflow.group(1) not in found[key]:
            found[key].append(workflow.group(1))
    return {k: sorted(v) for k, v in found.items()}


def before(path: Path, cutover: str) -> bool | None:
    """Was this log written before `cutover` landed? None if unknowable.

    None rather than False: a log with no stamp cannot be placed on either side,
    and scoring it as "after" would silently admit a pre-fix record into a
    post-fix denominator.
    """
    _, at = CUTOVERS[cutover]
    stamp = stamp_of(path)
    if at is None or stamp is None:
        return None
    return stamp < at


def events(log_dir: Path, event_type: str) -> list[tuple[Path, dict]]:
    """Every `event_type` event in the archive, with the log it came from.

    ONE DECLARATION OF HOW A RUN LOG IS READ, mirroring
    `assistant_activities._log_events`: the stream interleaves non-JSON on stderr
    paths, so a malformed line is SKIPPED rather than raised on. A reader that
    raised would lose a whole run's figures to one stray warning.
    """
    if event_type not in MEMBER_EVENT_TYPES:
        raise ValueError(
            f"{event_type!r} is not a member of the run-log surface. Members: "
            f"{sorted(MEMBER_EVENT_TYPES)}. A reader asking for an undeclared "
            f"type is either a typo or a fourth observable that was never "
            f"declared here — and the second is the failure this module exists "
            f"to make loud."
        )
    found: list[tuple[Path, dict]] = []
    for path in logs(log_dir):
        for event in _decoded(path):
            if event.get("type") == event_type:
                found.append((path, event))
    return found


def _decoded(path: Path):
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def assert_publishable(event_type: str, event: dict, emitted: dict) -> None:
    """Raise if a reader is carrying an UNPUBLISHABLE PAYLOAD VALUE into its output.

    CHECKED ON VALUES, NOT ON KEY NAMES, and the difference is what makes this a
    control rather than bookkeeping. A reader's row is mostly derived — counts,
    ratios, a log file name, a cutover verdict — so an allowlist of its KEYS
    would have to enumerate every one of them, and enumerating a reader's own
    output is not a check on anything. What actually has to be true is narrower:
    **no value that arrived in a non-publishable payload field may appear in the
    output.**

    The hazard is not hypothetical. A `convergence` event carries `open_ids`,
    `opened`, `closed`, `added_ids` and `escalated_open` — lists of MODEL-AUTHORED
    finding slugs that read exactly like identifiers. A reader that carried one
    forward would move transcript-derived text out of a gitignored machine-local
    file into a public PR comment, which is the failure `exit_record._redact()`
    exists to prevent one surface over. Readers emit their LENGTHS.
    """
    allowed = PUBLISHABLE_FIELDS[event_type]
    tainted: dict[str, object] = {}
    for key, value in event.items():
        if key in allowed:
            continue
        for text in _strings(value):
            tainted[text] = key
    for key, value in emitted.items():
        for text in _strings(value):
            if text in tainted:
                raise ValueError(
                    f"a {event_type} reader is emitting {key}={text!r}, which "
                    f"arrived in the non-publishable payload field "
                    f"{tainted[text]!r}. The run log is CO-RESIDENT with the CLI "
                    f"transcript; readers emit derived figures, run_ids and log "
                    f"file names, never event payload text. Emit a LENGTH, or "
                    f"add the field to PUBLISHABLE_FIELDS with the reason it is "
                    f"not model-authored."
                )


def _strings(value: object) -> list[str]:
    """Every non-trivial string inside `value`.

    Short strings are ignored: a one- or two-character token collides by chance
    across unrelated fields, and a check that fires on a coincidence gets
    disabled rather than fixed.
    """
    if isinstance(value, str):
        return [value] if len(value) > 2 else []
    if isinstance(value, (list, tuple)):
        return [s for item in value for s in _strings(item)]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _strings(item)]
    return []


# --- sub-agent counting, recomputed ------------------------------------------

# THE TOOL IS NAMED `Agent`, AND `resource_telemetry` COUNTED `Task`. Measured
# 2026-08-11 over the 153-log archive: 272 `"name":"Agent"` invocations and ZERO
# `"name":"Task"`, so the emitted `subagents_spawned` is 0 on 13 of 13 records —
# not because no run spawned a sub-agent, but because the counter could not move.
# That is `high_events`/`oom_kills` a third time, on the field figure 3 reads.
#
# BOTH SPELLINGS ARE MATCHED rather than just the live one. The CLI renamed the
# tool; a log written under either name records the same fact, and a reader that
# only knew today's name would silently drop tomorrow's rename the same way.
SUBAGENT_TOOL_NAMES = frozenset({"Agent", "Task"})


def subagents_in(path: Path) -> int:
    """Sub-agent spawns counted from the log itself, not from the payload.

    RECOMPUTED RATHER THAN READ, and it is why figure 3 has a denominator over
    the whole archive instead of one starting at this phase. Fixing the emitter
    fixes runs from here on; the 13 records already written keep their zero, and
    the logs beside them still carry the evidence. `tool_result_bytes` is NOT
    recomputed — its emitted value is sound, and a second parser for a correct
    field is a second thing that can disagree.

    COUNTED STRUCTURALLY, over decoded `tool_use` blocks, and NOT by the string
    scan the emitter uses. A tool name can appear inside a tool RESULT — a run
    that greps its own logs puts the literal text there — and a replay reporting
    a rate must not count a quotation as a spawn. The emitter stays a regex
    because it runs on every dispatch; this is the one that has to be right, and
    `test_run_log.py` asserts the two agree over the live archive.

    NOT CONCURRENCY, for the same reason `resource_telemetry.from_log` says so:
    five sequential sub-agents and five simultaneous ones give the same number.
    `pids_peak` is the concurrency signal and it comes from the kernel.
    """
    total = 0
    for event in _decoded(path):
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use" \
                    and block.get("name") in SUBAGENT_TOOL_NAMES:
                total += 1
    return total
