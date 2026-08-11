"""The run-log surface's declaration, and the checks that keep it honest.

`run_log.py` is the machine-checkable half of what
`phase6_read_what_it_writes.md` names: a per-run JSONL log with three
parent-written member event types, a join key, a publish classification and a
rule for adding a fourth. Four properties make that declaration mean something
rather than describe something, and each is asserted here with an input that
breaks it:

  * the DECLARED member set equals the set the fleet actually writes, in BOTH
    directions — an undeclared new type and a declared type with no writer are
    different failures and both are silent;
  * the publish check fires on a MODEL-AUTHORED VALUE reaching the output, not
    on a key name — a key-name allowlist would be an inventory of each reader's
    own output and could not fail;
  * the model-key-to-workflow-key map is DERIVED from the tree, so the one
    ambiguous pair is found rather than remembered;
  * the recomputed sub-agent count agrees with the shipped emitter's regex over
    the live archive, so the two parsers cannot drift apart quietly.

Flat comment-delimited functions, matching the sibling test modules in this
directory.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]
_TOOL = _REPO / "scripts" / "helpers" / "measure" / "run_log.py"
_ACTIVITIES = _REPO / "scripts" / "workflows" / "temporal" / "modules" / \
    "assistant" / "assistant_activities.py"
_TELEMETRY = _REPO / "scripts" / "workflows" / "temporal" / "modules" / \
    "assistant" / "resource_telemetry.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _rl():
    return _load(_TOOL, "_run_log_under_test")


# --- the declared member set equals what the fleet writes --------------------

def _written_event_types() -> set[str]:
    """Every string literal handed to `_append_run_event` as its `event_type`.

    AN AST WALK, NOT A GREP, because a grep for the type strings would find them
    in the docstrings that discuss them and report a set that includes words
    nobody writes. This reads the second positional argument of every call to
    the appender, which is the only place a member type comes into existence.
    """
    tree = ast.parse(_ACTIVITIES.read_text())
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        name = target.id if isinstance(target, ast.Name) else \
            getattr(target, "attr", None)
        if name != "_append_run_event" or len(node.args) < 2:
            continue
        literal = node.args[1]
        if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
            found.add(literal.value)
    return found


def test_the_declared_member_set_is_EXACTLY_what_the_fleet_writes() -> None:
    """Both directions, because they are different failures and both are silent.

    An UNDECLARED new type is a fourth observable added with no reader — the
    exact admission failure Phase 6 exists for, and the way `run_resources`
    shipped. A DECLARED type with NO WRITER is the opposite and just as bad: a
    reader iterating the member set gets an empty corpus for it and reports a
    denominator of zero, which reads as "measured, nothing happened".
    """
    declared = set(_rl().MEMBER_EVENT_TYPES)
    written = _written_event_types()
    assert written, (
        "the AST walk found no `_append_run_event` call sites at all, so this "
        "gate would pass vacuously. The appender moved or was renamed."
    )
    assert declared == written, (
        f"the run log's declared member set and its actual writers disagree.\n"
        f"  declared but never written: {sorted(declared - written)}\n"
        f"  written but not declared  : {sorted(written - declared)}\n"
        f"A new parent-written observable is declared in run_log.py in the same "
        f"change that starts writing it, and it ships with a reader or a placed "
        f"candidate carrying a named trigger."
    )


def test_asking_for_an_undeclared_event_type_RAISES() -> None:
    """A reader cannot quietly read a type the surface has not declared."""
    rl = _rl()
    with pytest.raises(ValueError, match="not a member of the run-log surface"):
        rl.events(Path("/nonexistent"), "some_future_observable")


# --- the publish classification fires on VALUES ------------------------------

def test_a_MODEL_AUTHORED_finding_slug_reaching_the_output_RAISES() -> None:
    """The live hazard, and the reason the check is on values and not on keys.

    `convergence` events carry `open_ids` — lists of finding slugs the MODEL
    wrote. A reader that carried one forward would move transcript-derived text
    out of a gitignored machine-local file into a public PR comment.
    """
    rl = _rl()
    event = {"type": "convergence", "run_id": "abc123",
             "open_ids": ["lead-claim-still-carries-the-miscount"]}
    with pytest.raises(ValueError, match="non-publishable payload field"):
        rl.assert_publishable("convergence", event,
                              {"run_id": "abc123",
                               "worst": "lead-claim-still-carries-the-miscount"})


def test_emitting_the_LENGTH_of_a_slug_list_is_permitted() -> None:
    """The control on the other side: the check must not forbid the remedy.

    Without this, a check that raised on everything would pass the test above
    and be useless — and every reader would be rewritten to work around it.
    """
    rl = _rl()
    event = {"type": "convergence", "run_id": "abc123",
             "open_ids": ["lead-claim-still-carries-the-miscount"]}
    rl.assert_publishable("convergence", event, {"run_id": "abc123", "n_open": 1})


def test_a_declared_publishable_field_passes_through() -> None:
    """`state` is a parent-computed enum, so it is publishable and must not trip."""
    rl = _rl()
    event = {"type": "convergence", "run_id": "abc123", "state": "not_converged"}
    rl.assert_publishable("convergence", event,
                          {"run_id": "abc123", "state": "not_converged"})


def test_a_slug_JOINED_INTO_A_SENTENCE_still_RAISES() -> None:
    """The leak that actually gets written is not a bare field, and equality misses it.

    A reader summarising `", ".join(open_ids)` into one cell, or interpolating a
    slug into a sentence, carries recognisable transcript text into a PR comment
    while emitting a string that is byte-different from the one that arrived. An
    equality check passes it, and the docstring's promise — *no value that
    arrived in a non-publishable field may appear in the output* — would be
    false for the most likely shape of the failure.
    """
    rl = _rl()
    event = {"type": "convergence", "run_id": "abc123",
             "open_ids": ["lead-claim-still-carries-the-miscount"]}
    with pytest.raises(ValueError, match="non-publishable payload field"):
        rl.assert_publishable(
            "convergence", event,
            {"run_id": "abc123",
             "summary": "1 open: lead-claim-still-carries-the-miscount"})


def test_a_slug_TRUNCATED_FOR_A_COLUMN_still_RAISES() -> None:
    """The other direction, and the one a fixed-width report invites.

    `slug[:20]` is not the slug, so containment has to be checked both ways or a
    column-width truncation launders the leak past the check.
    """
    rl = _rl()
    event = {"type": "convergence", "run_id": "abc123",
             "open_ids": ["lead-claim-still-carries-the-miscount"]}
    with pytest.raises(ValueError, match="non-publishable payload field"):
        rl.assert_publishable("convergence", event,
                              {"run_id": "abc123", "worst": "lead-claim-still-c"})


def test_a_SHORT_coincidental_overlap_does_NOT_raise() -> None:
    """The control on the other side, because a check that fires on chance dies.

    Containment carries a length floor: below it, one string appearing inside
    another says nothing — `hold` inside `threshold`. Without this test the
    remedy for the two above is "match any substring", which fires on ordinary
    output and gets deleted rather than fixed.
    """
    rl = _rl()
    event = {"type": "convergence", "run_id": "abc123", "open_ids": ["hold"]}
    rl.assert_publishable("convergence", event,
                          {"run_id": "abc123", "note": "below threshold"})


def test_every_member_type_has_a_publish_classification() -> None:
    """A member with no entry would KeyError inside a reader at print time."""
    rl = _rl()
    assert set(rl.PUBLISHABLE_FIELDS) == set(rl.MEMBER_EVENT_TYPES)


def test_no_ID_LIST_field_is_classified_publishable() -> None:
    """The classification itself is checked, not just its enforcement.

    A future author widening `PUBLISHABLE_FIELDS` to quiet a raise would defeat
    the whole control, and the raise gives them the idea. Any `*_ids` field, and
    the three `convergence` list fields spelled without that suffix, are
    model-authored by construction.
    """
    rl = _rl()
    banned = {"open_ids", "added_ids", "opened", "closed", "escalated_open",
              "unknown_dispositions"}
    for event_type, fields in rl.PUBLISHABLE_FIELDS.items():
        leaked = {f for f in fields if f.endswith("_ids")} | (set(fields) & banned)
        assert not leaked, (
            f"{event_type} classifies {sorted(leaked)} as publishable. These carry "
            f"MODEL-AUTHORED finding slugs; readers emit their LENGTH."
        )


def test_every_member_type_declares_which_of_its_fields_may_be_ABSENT() -> None:
    """The other half of the classification, and the one that cost four defects.

    `PUBLISHABLE_FIELDS` says what a reader MAY emit. `NULLABLE_FIELDS` says what
    a reader may not assume is THERE — and before it existed, answering that
    meant re-deriving it from a dataclass two directories away, which is why one
    population got read as "carries numbers" at four separate sites.
    """
    rl = _rl()
    assert set(rl.NULLABLE_FIELDS) == set(rl.MEMBER_EVENT_TYPES)


def test_the_run_resources_NULLABLE_SET_is_the_EMITTERS_own(monkeypatch) -> None:
    """Declared here, DERIVED from the emitter, compared in both directions.

    `ResourceReport`'s fields defaulting to `None` are exactly the fields a
    record may arrive without. Deriving the set means a NEW nullable field on the
    emitter fails HERE — in a declaration a reader author reads — instead of
    failing in a figure months later as a plausible zero. `limits` is excluded:
    it defaults to a dict, so it is never absent.

    The other two member types have no dataclass to derive from — they are built
    inline from `.get()` calls — so their entries are stated and unchecked, and
    `run_log.py` says so rather than letting a table of four checked entries and
    two unchecked ones look uniform.
    """
    import dataclasses
    rl = _rl()
    rt = _load(_TELEMETRY, "_resource_telemetry_for_nullables")
    derived = {f.name for f in dataclasses.fields(rt.ResourceReport)
               if f.default is None}
    declared = set(rl.NULLABLE_FIELDS["run_resources"])
    assert declared == derived, (
        f"declared-but-not-nullable: {sorted(declared - derived)}; "
        f"nullable-but-undeclared: {sorted(derived - declared)}. The second is "
        f"the dangerous direction — a reader author checking this declaration "
        f"would conclude the field is always present."
    )


def test_only_the_SCORED_cutover_is_ever_passed_to_before() -> None:
    """A table of cutovers reads as a table of checks, and only one is checked.

    Four of the five entries are prose labels a report prints ("Zero before
    b8d7aa7, which added started_at/ended_at") and nothing compares them against
    record content. That is sound for the additive ones — a field that did not
    exist cannot appear on an earlier record — but a reader assuming `before()`
    covers all five would be assuming a control that is not there.
    """
    rl = _rl()
    def _scores_a_cutover(node: ast.AST) -> bool:
        """`before(path, "key")` or `rl.before(path, "key")` — either spelling."""
        if not isinstance(node, ast.Call):
            return False
        func = node.func
        name = func.id if isinstance(func, ast.Name) else \
            func.attr if isinstance(func, ast.Attribute) else None
        return name == "before" and len(node.args) > 1 \
            and isinstance(node.args[1], ast.Constant)

    called_with: set[str] = set()
    for source in [_TOOL, *sorted(_TOOL.parent.glob("replay_*.py"))]:
        called_with |= {node.args[1].value
                        for node in ast.walk(ast.parse(source.read_text()))
                        if _scores_a_cutover(node)}
    assert called_with <= set(rl.CUTOVERS), (
        f"a reader scores a cutover that is not declared: "
        f"{sorted(called_with - set(rl.CUTOVERS))}"
    )
    assert called_with == set(rl.SCORED_CUTOVERS), (
        f"SCORED_CUTOVERS says {sorted(rl.SCORED_CUTOVERS)} is compared against "
        f"record content; the tree actually compares {sorted(called_with)}. "
        f"Either a cutover gained a check and the declaration did not, or one "
        f"lost its check and the declaration still promises it."
    )


# --- the model-key map is derived, not remembered ----------------------------

def test_the_workflow_map_is_derived_and_finds_the_AMBIGUOUS_pair() -> None:
    """`research-write` and `research-verify` share the model key `research`.

    That collision is the entire reason `workflow_key` was added to the payload,
    and it is derived from the modules rather than hardcoded so that a SECOND
    colliding pair is found on the day it is written.
    """
    rl = _rl()
    found = rl.workflow_keys_by_model_key(_REPO)
    assert len(found) >= 8, (
        f"the scan found only {len(found)} model keys, so it is not visiting the "
        f"workflow tree and a per-workflow figure would silently bin everything "
        f"as unattributable"
    )
    assert found.get("research") == ["research-verify", "research-write"], found
    unambiguous = [k for k, v in found.items() if len(v) == 1]
    assert len(unambiguous) >= 7, found


def test_every_module_that_DISPATCHES_declares_a_WORKFLOW_KEY() -> None:
    """A module that calls `run_claude` must declare the key it bins its runs by.

    `run_claude` makes `workflow_key` a required keyword with no default, so a
    missing one is a TypeError at dispatch rather than a silent hole — this gate
    catches it at test time instead of at 3am.

    SCOPED BY THE CALL, NOT BY THE FILENAME. It used to glob `*_workflow.py` and
    look for the literal `act.run_claude(`, which made it blind to the one
    dispatcher in the tree that is neither — `review_pr_activities.py` calls
    `_shared.run_claude(` and is where `review-pr`'s WORKFLOW_KEY actually
    lives. A gate that cannot see the exception in the tree today would not see
    the next one either, and the call is what needs the argument.
    """
    root = _REPO / "scripts" / "workflows" / "temporal" / "modules" / "assistant"
    call = re.compile(r"\w+\.run_claude\(")
    missing, dispatchers = [], []
    for path in sorted(root.rglob("*.py")):
        if "tests" in path.parts:
            continue
        text = path.read_text()
        if not call.search(text):
            continue
        dispatchers.append(str(path.relative_to(_REPO)))
        if "WORKFLOW_KEY" not in text:
            missing.append(str(path.relative_to(_REPO)))
    assert len(dispatchers) >= 10, (
        f"the scan found only {len(dispatchers)} dispatching modules, so it is "
        f"not reading the workflow tree and would pass vacuously: {dispatchers}"
    )
    assert not missing, f"modules dispatching without a WORKFLOW_KEY: {missing}"


# --- the two sub-agent parsers agree -----------------------------------------

def test_the_recomputed_subagent_count_agrees_with_the_SHIPPED_emitter() -> None:
    """Two parsers for one number, so they are compared rather than trusted.

    `resource_telemetry.from_log` scans lines with a regex because it runs on
    every dispatch; `run_log.subagents_in` walks decoded `tool_use` blocks
    because a replay reporting a rate must not count a quotation as a spawn. They
    are allowed to differ — the structural one is authoritative — but a
    divergence has to surface as a red test rather than as a drifting figure.

    RUN OVER THE LIVE ARCHIVE and skipped when there is none, because a
    synthetic fixture would only prove the two agree on input this file wrote.
    """
    rl = _rl()
    rt = _load(_TELEMETRY, "_resource_telemetry_under_test")
    log_dir = rl.default_log_dir()
    if not log_dir.is_dir():
        pytest.skip(f"no run-log archive at {log_dir}")
    logs = rl.logs(log_dir)
    if not logs:
        pytest.skip(f"archive at {log_dir} is empty")
    examined = disagreed = spawns = 0
    for path in logs:
        structural = rl.subagents_in(path)
        _, scanned = rt.from_log(path)
        examined += 1
        spawns += structural
        if scanned != structural:
            disagreed += 1
    assert examined > 0
    assert spawns > 0, (
        f"the structural counter found ZERO sub-agent spawns across {examined} "
        f"archived logs. Either the archive genuinely has none — check with "
        f"`grep -c '\"name\":\"Agent\"'` — or this counter is reading a tool name "
        f"the CLI does not emit, which is the defect it was written to fix."
    )
    assert disagreed == 0, (
        f"the two sub-agent parsers disagree on {disagreed} of {examined} logs. "
        f"The structural walk is authoritative; the emitter's regex needs the "
        f"same tool-name set."
    )


# --- cutovers and addressing -------------------------------------------------

def test_a_log_with_no_stamp_is_UNPLACEABLE_rather_than_scored_as_recent() -> None:
    """None, not False. Scoring it "after" admits a pre-fix record silently.

    The V1 fleet's name shape carries a stamp too, but a log named by anything
    else cannot be placed on either side of a cutover, and a figure that counted
    it as post-fix would be a denominator with an unknown contaminant.
    """
    rl = _rl()
    assert rl.before(Path("not-a-run-log.jsonl"), "child_scope_measured") is None
    assert rl.stamp_of(Path("not-a-run-log.jsonl")) is None


def test_the_cutovers_bracket_the_records_they_claim_to() -> None:
    """The stamps are compared as strings, so their SHAPE has to match the names.

    A cutover written as `2026-08-10 17:09` rather than `20260810-170915` would
    compare as less than every log name and silently classify the whole archive
    as post-fix — a change that moves every figure and breaks no test.
    """
    rl = _rl()
    for name, (commit, stamp) in rl.CUTOVERS.items():
        if stamp is None:
            continue
        assert len(stamp) == 15 and stamp[8] == "-", (
            f"cutover {name} ({commit}) is spelled {stamp!r}; it must match the "
            f"log-name shape YYYYMMDD-HHMMSS or every comparison is wrong"
        )
    early = Path("review-pr-20260810-164130-abc.jsonl")
    late = Path("review-pr-20260810-225854-abc.jsonl")
    assert rl.before(early, "child_scope_measured") is True
    assert rl.before(late, "child_scope_measured") is False


def test_the_log_dir_resolves_OUT_of_a_worktree() -> None:
    """`.claude/` is gitignored, so a worktree has no `logs/`.

    A tool defaulting to its own tree reports an empty corpus — loud, but it
    diagnoses badly, and `replay_completion_predicate.py`'s docstring records a
    run losing time to exactly that.
    """
    rl = _rl()
    inside = Path("/repo/.claude/worktrees/build-123/scripts/helpers/measure/run_log.py")
    assert rl.default_log_dir(inside) == Path("/repo/.claude/logs")
    # AND THE OTHER BRANCH, from the same argument. It used to re-derive from
    # `__file__` and ignore `start` entirely, so half the function was
    # unreachable from a test and the parameter governed one branch of two.
    outside = Path("/elsewhere/scripts/helpers/measure/run_log.py")
    assert rl.default_log_dir(outside) == Path("/elsewhere/.claude/logs")
