"""The typed exit record — schema, vocabulary and fail-safe contract.

THE ONE DECLARATION. `/opt/skyy-net/skyynet-master-planning/standards/workflows/exit-protocol.md` §6 requires the record's
schema *and its address* to be declared once and loaded, never re-typed per
consumer; this module is that declaration for the V2 tree. The string handed to
the CLI's `--json-schema` is SERIALISED FROM the same object the router
validates against, so the producer's contract and the consumer's contract cannot
disagree without this file contradicting itself.

SCOPE, RULED AND NOT INHERITED. This is scoped to the V2 tree because there is
no second envelope. The V1 bash fleet is FROZEN (`exit-protocol.md` §7) — not
migrated and not retired, kept as the working fallback with nothing invested in
upgrading it — so it keeps emitting prose and has no envelope to diverge from.
That is a stated carve-out, not an omission, and no cross-tree conformance test
is built: a gate between a tree that will change and a tree nobody will change
can only ever go red because someone edited the frozen fleet, which is already
forbidden. Re-open this if the freeze is lifted.

DEPENDENCY-FREE ON PURPOSE, like its sibling `routing.py` — no I/O, no clock,
and no third-party validator. **ONE sibling import, added by Phase 4 and stated
rather than quietly taken:** `routing`, which owns the PR-URL address the same
way it owns `parse_verdict`. R5b compares a `completion_ref` against the one the
parent expects, and re-typing that parse here would be a second declaration of
the address INSIDE the module written to forbid second declarations — the exact
defect §6 exists to prevent, and the one this module already committed once at
`as_prose_verdict`. `routing` is itself dependency-free, so nothing is pulled in
behind it and the "any workflow may import this without a family" property that
made both modules leaves is untouched. `jsonschema` is importable
on this workstation but is declared in no manifest in this repo, and a routing
contract that silently depends on whatever happens to be installed is a contract
that fails on the first host that differs. `_validate` WALKS `CHILD_SCHEMA`
rather than restating it, so the "one declaration" property survives having a
validator at all.

WHY THE THREE STRATA. `exit-protocol.md` §2 splits the record by who can
PHYSICALLY produce each value, not by taxonomy: the child authors what only the
child knows (§2.1, arriving via `structured_output`), the runtime produces what
the child cannot see (§2.2, `permission_denials` — measured on a run that exited
0 with `is_error: false` while the fleet's only in-run safety control had
fired), and the parent computes what neither is entitled to decide (§2.3,
`routed_outcome`). `route()` below is the entire parent stratum.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from .. import routing

__all__ = [
    "SCHEMA_VERSION", "SUPPORTED_SCHEMA_VERSIONS", "CHILD_SCHEMA", "SCHEMA_BYTE_BOUND",
    "Outcome", "HoldKind", "RoutedOutcome", "UndeterminedReason",
    "ExitRecord", "schema_argument", "route", "routes_to_redispatch",
]


# The version the child writes today. A single integer as a string: additive
# changes do NOT bump it (that is what "additive" means, and a bump on every
# added field would route every skewed worktree to a human for no reason). It
# bumps only when a field changes type, changes meaning, or is removed.
SCHEMA_VERSION = "1"

# The parent supports exactly the versions it has code for. A SET, not a range:
# a parent on `main` reads records written by children in worktrees cut from
# older revisions, so skew is the normal case here, not the edge case.
SUPPORTED_SCHEMA_VERSIONS = frozenset({"1"})

# The schema is an ARGUMENT VALUE, so its own size is a build-time cost for
# every caller — a constraint the availability framing missed and Phase 1 E1(g)
# surfaced. Bounded at Tekton's 4096 bytes, the one corroborated cap figure in
# this evidence base. Asserted by a test, because an over-large schema fails at
# the process boundary where the error names neither the schema nor the field
# that grew it.
SCHEMA_BYTE_BOUND = 4096


class Outcome(str, Enum):
    """What the CHILD asserts about the work. Never written by a parent."""

    MERGE = "merge"
    HOLD = "hold"


class HoldKind(str, Enum):
    """The sub-kind every parent branches on — `hold` alone does not route.

    NEEDS_RULING is the ASSERTED abstention arm: the evaluation completed and
    the answer is that a human must decide. It stays a model assertion by
    construction — a predicate that could detect "this needs a human" would be
    the ground truth it is asking for.
    """

    REDISPATCH = "redispatch"
    NEEDS_RULING = "needs_ruling"


class RoutedOutcome(str, Enum):
    """What the PARENT decided. Never written by a child.

    UNDETERMINED is the COMPUTED abstention arm — could-not-check. It is absent
    from the schema the child is given, so a child cannot assert it even by
    trying. That is what makes the two arms separately countable: a rise in
    UNDETERMINED is a statement about the machinery, a rise in NEEDS_RULING is a
    statement about the work.
    """

    MERGE = "merge"
    HOLD = "hold"
    UNDETERMINED = "undetermined"


class UndeterminedReason(str, Enum):
    """Why the parent could not evaluate. Required iff UNDETERMINED.

    The residual arm is a NAMED STATE THAT IS RECORDED, never a silent
    fall-through — every surveyed system has an answer for the unmatched case
    and none of them is "fall through".
    """

    PERMISSION_DENIED = "permission_denied"
    # SEPARATE FROM PERMISSION_DENIED ON PURPOSE, and the separation is the
    # instrument rather than a nicety. The computed arm's rate is `undetermined`
    # GROUPED BY this field, so "the safety control asserted" and "the key was
    # absent or was not a list" must not share a bin: if a CLI change renames or
    # drops `permission_denials`, a shared bin reports 100% of runs as a
    # fleet-wide safety trip and an operator reads a control firing where none
    # did. Routing is identical — both arms are the human — so nothing about
    # R1's primacy is weakened by naming the two conditions apart. Same defect
    # class as `route(None)` reporting `permission_denied`, one rule below.
    DENIALS_UNREADABLE = "denials_unreadable"
    # THE SAME ARGUMENT ONE LEVEL UP, and it is the third instance of it in this
    # enum. `denials_unreadable` separates "could not check the key" from "the
    # key said yes"; this separates "could not read the ENVELOPE AT ALL" from
    # either. A `result` event that is not an object is a CLI shape change, and
    # folding it into `record_absent` would report it as the highest-frequency
    # machinery failure there is — a run killed mid-stream — on 100% of runs.
    # An operator would read a fleet dying mid-stream while the actual cause is
    # that the envelope stopped being a dict. Routing is unchanged (the human
    # arm), so this buys nothing in routing and everything in diagnosis.
    ENVELOPE_UNREADABLE = "envelope_unreadable"
    RECORD_ABSENT = "record_absent"
    RECORD_UNPARSEABLE = "record_unparseable"
    SCHEMA_VERSION_UNKNOWN = "schema_version_unknown"
    RECORD_STALE = "record_stale"
    # R5b. SEPARATE FROM RECORD_STALE, and the two are different questions about
    # identity: `record_stale` says the record belongs to a different
    # INVOCATION, this says a well-formed record of THIS invocation points at a
    # different DURABLE RECORD. Sharing a bin with `record_stale` would report a
    # cross-repo reference as a worktree-skew problem and send the operator to
    # the wrong place, which is the same argument this enum already makes three
    # times. The threat itself is argued once, at `routing.PR_URL`, and is not
    # restated here — it was, in four production files, and three of the four
    # copies said the derived number reaches `gh`, which is true of
    # `routing.pr_number_from_url`'s call sites and not of this field.
    COMPLETION_REF_MISMATCH = "completion_ref_mismatch"
    UNMATCHED = "unmatched"


# ---------------------------------------------------------------------------
# The child's stratum, as a JSON Schema. This object is BOTH the argument passed
# to `--json-schema` and the thing `_validate` walks.
#
# EVERY REQUIRED FIELD MUST BE ONE THE CHILD CAN ALWAYS FILL. Phase 1 E2(c)
# measured that `--json-schema` is a tool the model CHOOSES to call: a schema it
# finds unsatisfiable produces SILENCE on a clean run (exit 0, subtype success,
# is_error false, populated .result, no structured_output key) rather than an
# error. An over-constrained required field is therefore a self-inflicted
# absence, which is why `hold_kind` is required only alongside `outcome: hold`
# and why the abstention vocabulary is load-bearing rather than decorative.
# ---------------------------------------------------------------------------
CHILD_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "run_id", "outcome", "completion_ref", "findings"],
    "properties": {
        "schema_version": {"type": "string"},
        # Opaque nonce the PARENT generated and put in the prompt. Model-echoed,
        # so it proves nothing on its own — rule R5 compares it against the value
        # the parent issued. A record cannot report its own absence, and it
        # cannot vouch for its own identity either.
        "run_id": {"type": "string"},
        "outcome": {"type": "string", "enum": ["merge", "hold"]},
        "hold_kind": {"type": "string", "enum": ["redispatch", "needs_ruling"]},
        # The substrate-agnostic reference to this record's working record
        # (`exit-protocol.md` §1). NOT typed as a PR URL: a component whose work
        # product is not code in git has no PR to point at, and this fleet is
        # going there. `substrate` is what lets a reader resolve the address
        # without inferring the binding from the shape of a string.
        "completion_ref": {
            "type": "object",
            "additionalProperties": False,
            "required": ["substrate", "kind", "id", "uri"],
            "properties": {
                "substrate": {"type": "string", "enum": ["github"]},
                "kind": {"type": "string", "enum": ["pull", "issue"]},
                # STRING, not integer. Phase 1 E6 typed this `integer`; both
                # consumers hold it as a string today (`routing.py`'s
                # `match.group(1)`, and bash `${PR_URL##*/}`), and an integer
                # presumes a substrate whose record ids are numeric.
                "id": {"type": "string"},
                "uri": {"type": "string"},
            },
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "disposition"],
                "properties": {
                    "id": {"type": "string"},
                    "disposition": {
                        "type": "string",
                        "enum": ["hold", "fixed", "deferred", "rejected",
                                 "noted", "escalated", "dissolved"],
                    },
                },
            },
        },
    },
}


def schema_argument() -> str:
    """The exact string handed to `claude --json-schema`.

    Compact separators: the schema crosses a process boundary as an argument
    value, so every byte is a build-time cost for the caller.
    """
    return json.dumps(CHILD_SCHEMA, separators=(",", ":"))


@dataclass(frozen=True)
class ExitRecord:
    """One assembled exit record — all three strata, provenance preserved.

    `outcome` is the child's assertion CARRIED VERBATIM and never overwritten;
    `routed_outcome` is the policy-adjusted value routing reads. That is the
    GitHub Actions `outcome`/`conclusion` shape, adopted because it costs one
    field and preserves the option to change the ruling later. NO COMPOSITION
    MACHINERY sits between them: Phase 1 E3(a) measured the off-diagonal cells
    empty BY CONSTRUCTION — the asserted verdict rides in the same envelope key
    that is absent on every run where the runtime reports failure, so the two
    rows cannot both be populated for one run at any N.
    """

    routed_outcome: RoutedOutcome
    undetermined_reason: UndeterminedReason | None = None
    outcome: Outcome | None = None
    hold_kind: HoldKind | None = None
    completion_ref: dict | None = None
    findings: tuple[dict, ...] = ()
    permission_denials: tuple[dict, ...] = ()
    schema_version: str | None = None

    def __post_init__(self) -> None:
        """`undetermined_reason` is required IFF `routed_outcome` is UNDETERMINED.

        The invariant was documented on `UndeterminedReason` and enforced
        nowhere, which left `review_pr_workflow`'s reason-reporting one None
        away from an AttributeError raised INSIDE the code that exists to
        explain machinery failures. Enforced at construction, in the local
        `ReviewInput.__post_init__` shape.
        """
        undetermined = self.routed_outcome is RoutedOutcome.UNDETERMINED
        if undetermined and self.undetermined_reason is None:
            raise ValueError(
                "an undetermined route must name its reason: the residual arm is a "
                "named state that is RECORDED, never a silent fall-through"
            )
        if not undetermined and self.undetermined_reason is not None:
            raise ValueError(
                f"routed_outcome={self.routed_outcome.value} carries "
                f"undetermined_reason={self.undetermined_reason.value}; a reason "
                f"belongs only to the computed abstention arm"
            )


def _validate(value, schema: dict, path: str) -> str | None:
    """Walk CHILD_SCHEMA against a value. Returns the first error, or None.

    Deliberately partial — it implements exactly the keywords CHILD_SCHEMA uses
    (`type`, `required`, `properties`, `additionalProperties`, `enum`, `items`)
    and nothing else. A general JSON Schema implementation would be a second
    declaration of what this schema is allowed to contain.
    """
    expected = schema["type"]
    if expected == "object":
        if not isinstance(value, dict):
            return f"{path}: expected object, got {type(value).__name__}"
        for key in schema.get("required", []):
            if key not in value:
                return f"{path}.{key}: required field missing"
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    return f"{path}.{key}: unknown field (additionalProperties is false)"
        for key, sub in props.items():
            if key in value:
                err = _validate(value[key], sub, f"{path}.{key}")
                if err:
                    return err
        return None
    if expected == "array":
        if not isinstance(value, list):
            return f"{path}: expected array, got {type(value).__name__}"
        for i, item in enumerate(value):
            err = _validate(item, schema["items"], f"{path}[{i}]")
            if err:
                return err
        return None
    if expected == "string":
        # bool is an int, not a str — no isinstance trap here, but state the
        # check positively so a future numeric type does not inherit one.
        if not isinstance(value, str):
            return f"{path}: expected string, got {type(value).__name__}"
        allowed = schema.get("enum")
        if allowed is not None and value not in allowed:
            return f"{path}: {value!r} is outside the closed vocabulary {allowed}"
        return None
    raise AssertionError(f"CHILD_SCHEMA uses an unsupported type at {path}: {expected!r}")


# THE FIELDS R5b COMPARES EXACTLY, DERIVED FROM THE SCHEMA RATHER THAN RETYPED.
# A hand-written tuple here would be a second declaration of `completion_ref`'s
# field set inside the module whose thesis is one declaration — and the failure
# is silent in the dangerous direction: a fifth required field would pass R3
# validation and simply not be compared, NARROWING a safety check with nothing
# going red. This function has already been measured with a hole of exactly that
# shape (removing the `id` comparison turned zero tests red, because every
# fixture moved `id` and `uri` together). `uri` is excluded because it is the
# one field compared by IDENTITY rather than byte-for-byte, below.
_REF_EXACT_FIELDS = tuple(
    k for k in CHILD_SCHEMA["properties"]["completion_ref"]["required"] if k != "uri")


def _ref_matches(actual: dict, expected: dict) -> bool:
    """Is `actual` the SAME durable record as `expected`? Identity, not shape.

    Every required field of `completion_ref` except `uri` compares exactly, and
    the list is `_REF_EXACT_FIELDS` — read off `CHILD_SCHEMA`, not retyped.
    `uri` compares by the identity it names rather than byte-for-byte, because a
    trailing slash, a `/files` suffix or a query string are the same PR and
    failing a correct review on one would be a guard failing on correct input.
    The parse is `routing.pr_identity` — the one declaration of the address —
    and it returns `(owner/repo, number)`, so a `uri` naming ANOTHER REPOSITORY
    fails here even when it carries the right number. `routing.PR_URL` carries
    the argument for why that is the threat; it is not restated here.

    FAIL-SAFE WHEN IT CANNOT PARSE, IN BOTH DIRECTIONS AND FOR DIFFERENT
    REASONS. `CHILD_SCHEMA` constrains `substrate` to `github`, so `pr_identity`
    is the right parser for every record that reaches R3; if that enum is ever
    widened without widening this, a non-github `uri` raises `ValueError` here
    and returns False — the human arm — rather than comparing two things it does
    not understand. An unparseable EXPECTED `uri` is a parent-side fault and is
    refused before this is reached: `review_pr_helper.expected_completion_ref`
    validates what it built, so a bad `repo_slug` fails as a parent error rather
    than arriving here and being reported as the child naming a wrong record.
    """
    for key in _REF_EXACT_FIELDS:
        if actual.get(key) != expected.get(key):
            return False
    try:
        return routing.pr_identity(actual.get("uri", "")) == \
            routing.pr_identity(expected.get("uri", ""))
    except ValueError:
        return False


def route(result_event: dict | None, *, expected_invocation_id: str,
          expected_ref: dict | None) -> ExitRecord:
    """The fail-safe contract. Ordered rules, first match wins, R9 is the default.

    Shape borrowed from Kubernetes `podFailurePolicy` and cited rather than
    designed — routing on values the model did not author is mature and boring
    outside the agent corpus, and treating it as a design novelty is the error
    this protocol exists to avoid.

    TOTAL OVER ITS OWN INPUTS, not just over the record. Three rules read values
    that can themselves be missing, and each resolves toward the human arm.

    AND THE PARAMETER'S OWN TYPE IS ONE OF THOSE INPUTS. The annotation says
    `dict | None` and an annotation is not a check: for one pass this function
    guarded `None` and then called `.get` on whatever else arrived, so a list, a
    str, an int or a bool raised `AttributeError` FROM INSIDE THE ROUTING
    CONTRACT, where the caller's error handler does not catch it. It was latent
    only because `result_event()` filters `isinstance(event, dict)` in a
    DIFFERENT FILE — a guarantee asserted nowhere at this boundary, and Phase 4's
    entire content is adding call sites that each bring their own reader. The
    identical docstring phrase sits on `_redact` below, whose identical gap was
    closed one pass earlier; the child was fixed and the parent left. `route` is
    the function that IS the contract, so it validates at its own boundary rather
    than by delegation to whoever happens to call it today. The claim is now
    machine-checked — see `test_every_function_claiming_totality_is_total`.

    `result_event` is the CLI's `result` event as a dict, or None when the log
    carried none at all.

    `expected_ref` is the `completion_ref` this invocation is ABOUT — the working
    record the parent dispatched against — or None when the caller genuinely has
    none to compare. IT HAS NO DEFAULT ON PURPOSE. A keyword with a default of
    None is a check that skips itself, and every rule in this module exists
    because a check that skips itself is indistinguishable from one that passed.
    Passing None is a caller stating it cannot check identity, which is a real
    state and a visible one; `test_every_production_caller_of_route_states_its_
    expected_ref` is what keeps it from becoming the quiet default.
    """
    # R2, REACHED BEFORE R1 IN EXACTLY ONE CASE: there is no `result` event at
    # all. No event implies no key, so the condition is absence of the record,
    # not inability to check the safety control — and the DIFFERENCE IS THE
    # WHOLE POINT OF THE REASON STRING. A run killed mid-stream (turn cap,
    # SIGTERM, crash) is the highest-frequency machinery failure there is;
    # reporting it as `permission_denied` sends an operator hunting for a denied
    # tool call that never happened, and mis-bins every one of them in the
    # per-reason rate `phase3_typed_exit_record.md` step 4 defines. Routing is
    # identical either way — both arms are the human — so nothing about R1's
    # primacy over any ROUTING decision is weakened by naming this correctly.
    if result_event is None:
        return ExitRecord(RoutedOutcome.UNDETERMINED, UndeterminedReason.RECORD_ABSENT)

    # R0, AND IT IS BEFORE R1 RATHER THAN AFTER IT. Every rule below reads a key
    # off this object; an envelope that is not a mapping cannot answer the safety
    # question either, so "could not check whether the control fired" is the
    # honest state and it must be reached before the rule that assumes it can.
    # Its own bin rather than `record_absent`: see `UndeterminedReason`.
    if not isinstance(result_event, dict):
        return ExitRecord(RoutedOutcome.UNDETERMINED, UndeterminedReason.ENVELOPE_UNREADABLE)

    envelope = result_event

    # R1 — SAFETY DOMINATES ROUTING, so it is first and nothing can reach past
    # it. Auto-redispatching a child that just tripped the fleet's only in-run
    # safety control is an unbounded retry loop against the one control there is.
    #
    # An ABSENT key is not an empty list. "I could not check whether the safety
    # control fired" and "it fired" get the SAME ROUTING and DIFFERENT REASONS:
    # the arm is the human either way, and the reason is the payload the
    # computed arm is grouped by. A shared reason would make a CLI that renamed
    # or dropped the key indistinguishable from a fleet that tripped the control
    # on every run — see `UndeterminedReason.DENIALS_UNREADABLE`.
    denials = envelope.get("permission_denials")
    if denials is None or not isinstance(denials, list):
        return ExitRecord(RoutedOutcome.UNDETERMINED, UndeterminedReason.DENIALS_UNREADABLE)
    if denials:
        return ExitRecord(
            RoutedOutcome.UNDETERMINED, UndeterminedReason.PERMISSION_DENIED,
            permission_denials=_redact(denials),
        )
    published_denials = _redact(denials)

    # R2 — ABSENCE, and it is NOT conditioned on the exit status. Phase 1 E2
    # measured a run that completed with exit 0, subtype success, is_error
    # false, a populated .result and NO structured_output key: the model
    # declined to call the tool and asked a clarifying question instead. This
    # rule may not read "absent record implies the run died" — that run did not
    # die, and every other signal said clean.
    record = envelope.get("structured_output")
    if record is None:
        return ExitRecord(RoutedOutcome.UNDETERMINED, UndeterminedReason.RECORD_ABSENT,
                          permission_denials=published_denials)

    # R3 — present but does not validate. Nothing downstream may read a field
    # off an object that failed validation.
    if _validate(record, CHILD_SCHEMA, "structured_output") is not None:
        return ExitRecord(RoutedOutcome.UNDETERMINED, UndeterminedReason.RECORD_UNPARSEABLE,
                          permission_denials=published_denials)

    # R4 — unknown schema_version, BEFORE identity. A record whose version is
    # unknown has no guaranteed typing, so its invocation id is not yet a value
    # one may compare. Never ignored and never guessed at.
    version = record["schema_version"]
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        return ExitRecord(RoutedOutcome.UNDETERMINED, UndeterminedReason.SCHEMA_VERSION_UNKNOWN,
                          schema_version=version, permission_denials=published_denials)

    # R5 — STALENESS. The record is well-formed and belongs to a different
    # invocation. Freshness by path allocation and identity in the payload are
    # two independent checks; this is the one that catches a record arriving on
    # a CORRECT path from a DIFFERENT invocation.
    # `record["run_id"]` IS THE WIRE SPELLING AND STAYS — the parameter beside it
    # does not. Phase 9 r1 puts every Python identifier holding the per-model
    # nonce on `invocation_id`; the JSONL key keeps `run_id` because records
    # already written carry it, and the roadmap schedules that field's meaning
    # change for Phase 3's cut-over. The seam is here, on one line, rather than
    # smeared across a parameter name that reads like the run's own id.
    if record["run_id"] != expected_invocation_id:
        return ExitRecord(RoutedOutcome.UNDETERMINED, UndeterminedReason.RECORD_STALE,
                          schema_version=version, permission_denials=published_denials)

    # R5b — REFERENCE IDENTITY, and it is the second half of R5 rather than a
    # new kind of rule. R5 asks *is this record from the invocation I issued*;
    # this asks *is it about the record I dispatched against*. Both are answered
    # by comparison against a value the parent generated, because a record
    # cannot vouch for its own identity — the same reason R5 is a comparison and
    # not a presence test.
    #
    # WHY IT IS NOT SATISFIED BY THE ANCHORED PATTERN. The pattern pins the host
    # and guarantees digits; `https://github.com/someone-else/other-repo/pull/12`
    # passes it and yields `12`, which is then used against THIS dispatch's repo
    # in `gh pr view`, `gh pr comment` and `--pr` on a downstream child that
    # checks out and commits to that PR's branch. It needs no adversarial child:
    # children are instructed to read prior PR comments, which routinely contain
    # other PRs' URLs.
    if expected_ref is not None and not _ref_matches(record["completion_ref"], expected_ref):
        return ExitRecord(
            RoutedOutcome.UNDETERMINED, UndeterminedReason.COMPLETION_REF_MISMATCH,
            schema_version=version, completion_ref=record["completion_ref"],
            findings=tuple(record["findings"]), permission_denials=published_denials,
        )

    # From here the CHILD'S ASSERTION DECIDES and the parent adds nothing. That
    # is the precedence rule in one line: the computed observable GATES (R1-R5),
    # the asserted verdict DECIDES (R6-R8).
    outcome = Outcome(record["outcome"])
    hold_kind = HoldKind(record["hold_kind"]) if "hold_kind" in record else None
    common = dict(
        outcome=outcome, hold_kind=hold_kind, schema_version=version,
        completion_ref=record["completion_ref"],
        findings=tuple(record["findings"]),
        permission_denials=published_denials,
    )

    # R6 — and the `hold_kind is None` guard is load-bearing, not defensive.
    # CHILD_SCHEMA deliberately does NOT bind `hold_kind` to `outcome` (an
    # `if/then` would be a required-field constraint the child could fail to
    # satisfy, and E2(c) measured that as SILENCE on a clean run). The schema is
    # relaxed on purpose, SO THE ROUTER OWNS THE WHOLE CONDITIONAL. Without this
    # guard `{"outcome": "merge", "hold_kind": "needs_ruling"}` — a record whose
    # own author said a human must decide — validates, passes R1-R5 and routes
    # MERGE, with the prose shadow agreeing because `merge` renders `MERGE`.
    # That cell belongs to R9, which §4 says exists precisely because R6-R8 do
    # not exhaust `outcome` x `hold_kind`.
    if outcome is Outcome.MERGE and hold_kind is None:
        return ExitRecord(RoutedOutcome.MERGE, **common)
    # R7, R8 — one rule each in the protocol, one branch here because they
    # differ only in a field already carried.
    if outcome is Outcome.HOLD and hold_kind is not None:
        return ExitRecord(RoutedOutcome.HOLD, **common)

    # R9 — the documented default. Reachable in practice: R6-R8 do not exhaust
    # the product of outcome x hold_kind (a `hold` with no `hold_kind` validates
    # against the schema and matches nothing above), and a widened supported
    # version set with un-widened rules lands here too.
    return ExitRecord(RoutedOutcome.UNDETERMINED, UndeterminedReason.UNMATCHED, **common)


def _redact(denials: list) -> tuple[dict, ...]:
    """Drop `tool_input` at READ TIME, so there is no copy to leak.

    Entries carry literal command lines and absolute worktree paths;
    `code_routed_control_flow.md` P13 (definitive) records redaction as the
    documented control here. Publishing them verbatim would put the run's
    command history and filesystem layout permanently in a PR comment.

    Dropped rather than marked internal deliberately: a field that exists in the
    routing copy and is filtered on the way out is one edit away from being
    published by a renderer that does not know why it was filtered.

    TOTAL OVER ITS OWN INPUT, like everything else here — AND TOTAL OVER THE
    FIELDS, not only over the entries. R1 checks that `permission_denials` is a
    list; it cannot check what is IN the list. An entry that is not an object —
    a bare string from a CLI that changed shape — would raise AttributeError
    from inside the routing contract, and the caller's error handler does not
    catch it. The count stays honest because an unreadable entry is still an
    entry. The `str()` calls are that same argument one level down: guarding the
    entry type and then handing an unguarded `d.get(...)` to the consumer stops
    one level short of the claim this paragraph makes. `review_pr_workflow`
    builds a `set` of `tool_name` and joins it, so a `tool_name` that is a dict
    raises `TypeError: unhashable type` and one that is an int raises in
    `join` — from inside the routing contract, uncaught, exactly the shape this
    paragraph was written about.

    THE PUBLISHED KEYS ARE THE MEASURED ONES. `matched_rule` was carried here
    until Phase 3's correction pass and was **always empty**: the one observed
    denial entry (`phase1_measure_the_channel.md`, "`permission_denials[]`
    non-empty, observed once") is `{tool_name, tool_use_id, tool_input}` and the
    CLI emits no `matched_rule` at all, so `.get("matched_rule", "")` made its
    absence silent while the field's documented job — *why* it fired — stayed
    unanswerable on every real envelope. `tool_use_id` replaces it: measured
    present, and it is the key that locates the denied call in the run log,
    which is the question an operator asks after a trip. `tool_input` stays
    dropped; dropping it is what this function is for.
    """
    return tuple(
        {"tool_name": str(d.get("tool_name", "")),
         "tool_use_id": str(d.get("tool_use_id", ""))}
        if isinstance(d, dict) else
        {"tool_name": "<unreadable denial entry>", "tool_use_id": ""}
        for d in denials
    )


def routes_to_redispatch(record: ExitRecord) -> bool:
    """The one predicate that distinguishes the two HOLD shapes.

    Deliberately NOT a function returning a prose token. The prose vocabulary is
    declared in `routing.py` and re-typing its three strings here would be a
    second declaration of it — the defect §6 exists to prevent, in the module
    written to enforce §6. The translation lives at ONE call site,
    `review_pr_helper.verdict_from_record`, and it reads this.
    """
    return (record.routed_outcome is RoutedOutcome.HOLD
            and record.hold_kind is HoldKind.REDISPATCH)
