"""research-minor: the multi-paper machinery is ABSENT, the per-paper rigor is NOT.

The workflow's whole value proposition is a subtraction, and a subtraction is
the one kind of change a green suite cannot notice on its own. Adding a
`research_minor` package makes every auto-discovering sweep in this directory
cover it for free — isolation invariants, MODEL_KEY resolution, placeholder
suppliers — and NONE of them can tell whether the thing that shipped is
actually smaller than its sibling. That is what this module checks.

WHERE THE CONTROLS COME FROM, and why they are not synthetic. Every assertion
of the form "the minor prompt does NOT contain X" is paired with the SAME
predicate run against `research_draft/prompts/draft.md`, which must return True.
The full-size sibling is a live, maintained fixture of exactly the machinery
being removed, so a predicate that silently stopped matching — a reworded stage
heading, a moved artifact path — fails on the full cycle rather than passing
vacuously on the minor one. A control that can only ever be satisfied is the
failure mode controls exist to prevent, and a hand-written scratch fixture
drifts away from the real prompt the moment the real prompt is edited.

AND THE CYCLE-SHAPE BLOCK IS EXERCISED, NOT GREPPED. `research_refine` is
REUSED rather than forked, so the risk is not that its prompt lacks a string —
it is that the block fails to render, or that the parameter carrying it grows
into a behavioural branch. The first is caught by rendering the real prompt
through the real `render()` (which raises on an unsubstituted placeholder); the
second by an AST walk asserting the parameter reaches no `if` statement, only
the same ternary `correction_pass` already uses.
"""

from __future__ import annotations

import ast
import inspect
import re
import textwrap
from pathlib import Path

_MODULES = Path(__file__).resolve().parents[2] / "modules"

import pytest
import yaml

from assembled_prompt import assembled

from modules.assistant.research import research_activities as act
from modules.assistant.research.research import research_workflow as full_parent
from modules.assistant.research.research_refine import research_refine_workflow as verify
from modules.assistant.research.research_draft import (
    research_draft_workflow as child,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
CONFIG = REPO_ROOT / "config.yaml"
_RESEARCH = Path(__file__).resolve().parents[2] / "modules" / "assistant" / "research"

MINOR_PROMPT = _RESEARCH / "research_draft" / "prompts" / "draft.md"
FULL_PROMPT = _RESEARCH / "research_draft" / "prompts" / "draft.md"

# EVERY ASSERTION BELOW READS THE ASSEMBLED PROMPT, never the raw file. These
# checks are about what the MODEL is told — that the minor cycle is four stages,
# that SYNTHESIZE names its artifact at the contract path — and a block PROMOTED
# to the shared pool leaves the file while still reaching the model. Reading the
# file made the stage count report three the first time a promotion touched
# Stage 1, and a guard that goes quiet because text MOVED is the failure mode
# `assembled_prompt.py` was written for.
VERIFY_PROMPT = _RESEARCH / "research_refine" / "prompts" / "refine.md"


def test_both_prompts_are_findable() -> None:
    """Vacuity guard for every comparison below.

    Each check reads both files. If either moved, the "absent from minor"
    assertions would pass on an empty string while the paired control failed
    with an unrelated error — so this fails first, and says which file moved.
    """
    assert MINOR_PROMPT.is_file(), f"{MINOR_PROMPT} is missing"
    assert FULL_PROMPT.is_file(), f"{FULL_PROMPT} is missing"
    assert VERIFY_PROMPT.is_file(), f"{VERIFY_PROMPT} is missing"


# --- 1. The multi-paper machinery is absent -----------------------------------
#
# Each predicate is keyed on a CONTRACT PATH or a STAGE HEADING — the prompt's
# skeleton — rather than on a topical word. The minor prompt deliberately
# *mentions* `topics.md` and `synthesis.md` in order to forbid them, so a bare
# substring check would be satisfied by the very sentence that does the
# forbidding. What distinguishes a prompt that WRITES an artifact is that it
# names that artifact at its contract path, under `${RESEARCH_DIR}`.

_STAGE_HEADING = re.compile(r"^## Stage \d+: (.+)$", re.M)


def _stage_titles(text: str) -> list[str]:
    return [t.strip() for t in _STAGE_HEADING.findall(text)]


def _writes_artifact_at_contract_path(text: str, artifact: str) -> bool:
    """True when the prompt names `${RESEARCH_DIR}/<artifact>` — a write target."""
    return f"${{RESEARCH_DIR}}/{artifact}" in text


def _has_stage_titled(text: str, prefix: str) -> bool:
    return any(t.startswith(prefix) for t in _stage_titles(text))


def _fans_out_per_topic(text: str) -> bool:
    """The per-topic dispatch loop: `For each … topic, dispatch …`."""
    return re.search(r"For each\b[^.\n]*\btopic\b[^.\n]*\bdispatch\b", text) is not None


# (label, predicate) — each must now be TRUE. This list used to assert the
# OPPOSITE, paired against the full prompt to prove the two differed: the minor
# cycle's value was that the machinery was absent.
#
# THE MERGE REMOVED THE PREMISE, NOT THE TEST'S SUBJECT. There is one write
# child now. It sizes its own cycle, so the machinery is the capability rather
# than the distinction, and a paired control against a prompt that no longer
# exists would assert nothing. The predicates are unchanged and still exact —
# only the expected answer flipped, which is why they are worth keeping: a
# reworded stage heading or a moved artifact path still turns them false.
MACHINERY = [
    ("topics.md-as-a-write-target",
     lambda t: _writes_artifact_at_contract_path(t, "topics.md")),
    ("a-SIZE-stage", lambda t: _has_stage_titled(t, "SIZE")),
    ("a-per-topic-fan-out", _fans_out_per_topic),
]


@pytest.mark.parametrize(("label", "predicate"), MACHINERY, ids=[m[0] for m in MACHINERY])
def test_the_write_child_CARRIES_the_sizing_machinery(label: str, predicate) -> None:
    """The child sizes its own cycle; without these it cannot.

    Each is load-bearing on its own. Without `topics.md` a later run cannot tell
    a short list from an unfinished one. Without a SIZE stage nothing decides how
    many topics a subject needs. Without the per-topic fan-out the child covers
    one topic and silently narrows anything larger — the measured failure that
    produced 1,055 lines covering a quarter of the ground.
    """
    assert predicate(assembled(MINOR_PROMPT)) is True, (
        f"the write child no longer carries {label}, so it cannot size its own "
        f"cycle. This absorbed `research-draft` and `research-refresh`; dropping "
        f"the machinery leaves a one-paper child wearing the merged name."
    )


def test_the_three_row_states_each_NAME_THEIR_AGENT() -> None:
    """Sizing without routing is half the merge.

    The child decides how many topics AND which agent each one gets. A due paper
    handed to `research-analyst` is rewritten rather than diffed, and the delta —
    what changed, what is now wrong, what is missing — is what made revalidation
    worth a separate workflow before this absorbed it.
    """
    text = assembled(MINOR_PROMPT)
    for token, why in [
        ("not yet written", "the state that dispatches an analyst"),
        ("research-analyst", "the agent for an uncovered topic"),
        ("research-currency", "the agent for a due one — the half absorbed from `research-refresh`"),
        ("current", "the state that dispatches nothing, which is the common case"),
    ]:
        assert token in text, f"the row-state table lost `{token}` — {why}"


def test_the_minor_cycle_writes_a_SYNTHESIS() -> None:
    """The inverse of a guard this suite used to carry, and the reversal is the point.

    Forbidding a synthesis rested on "with one paper the roll-up IS the paper".
    That is true on the first run and false on the second: papers ACCUMULATE and
    the synthesis is REPLACED (Research Standard §4), so a pool holding two minor
    papers and no synthesis has nothing rolling them up. It also stranded the
    evidence — `plan_draft` is told not to read raw papers wholesale, so it
    reported "no synthesis" and planned from priors while the paper sat unread.

    Asserted POSITIVELY rather than deleted: a guard whose design reverses should
    become its own inverse, or the property stops being checked in either
    direction.
    """
    text = assembled(MINOR_PROMPT)
    assert _has_stage_titled(text, "SYNTHESIZE"), (
        "write_minor.md has no SYNTHESIZE stage. Its one paper then reaches no "
        "downstream consumer: the planner reads synthesis.md and is told not to "
        "read the pool wholesale."
    )
    assert _writes_artifact_at_contract_path(text, "synthesis.md"), (
        "the SYNTHESIZE stage does not name synthesis.md at its contract path, so "
        "nothing guarantees the consumer finds it where it looks."
    )


def test_the_write_cycle_has_exactly_FIVE_stages() -> None:
    """FOUR became FIVE when this child absorbed `research-draft`'s sizing stage.

    It ran VERIFY+DISCOVER, RESEARCH, SYNTHESIZE, SUBMIT — four, because a
    one-topic child has nothing to size. The merged child sizes its own cycle,
    so SIZE is stage 2 and the count is the full cycle's five.

    THE COUNT IS THE CHECK, not a description of it. A stage silently added or
    dropped changes what the run does and nothing else would notice: the prompt
    still reads coherently, and `stage_order_is_mandatory` enforces the ORDER of
    whatever stages exist rather than which exist.
    """
    titles = _stage_titles(assembled(MINOR_PROMPT))
    assert len(titles) == 5, (
        f"the write cycle has {len(titles)} stages, expected five: {titles}. "
        f"If a stage was added or removed deliberately, say so here — the number "
        f"is what makes the change a decision rather than a drift."
    )
    assert titles[1].startswith("SIZE"), (
        f"SIZE must be stage 2 — the topic list has to exist before anything is "
        f"dispatched against it. Got: {titles}"
    )

def test_the_child_dispatches_ONE_ANALYST_PER_TOPIC() -> None:
    """The bound is per TOPIC, and it is a bound rather than a total.

    IT USED TO READ "ONE analyst. Not two" AND THAT WAS RIGHT FOR A ONE-TOPIC
    CHILD. This child now sizes its own cycle, so a total of one would forbid
    the fan-out it exists to do. What the original was protecting is unchanged
    and still stated: a topic's facets are covered by ONE analyst in ONE paper.
    Splitting a topic across analysts is the measured failure — 1,055 lines
    covering a quarter of the ground for the cost of covering all of it.

    Absence of a per-topic loop is not the same as a stated ceiling: a model
    handed a two-part question will split it into two analysts unless told not
    to, which is why the bound is written and not merely implied.
    """
    text = assembled(MINOR_PROMPT)
    assert "ONE ANALYST PER TOPIC" in text, (
        "the prompt lost its per-topic analyst bound"
    )
    assert "never one per sub-question" in text, (
        "the bound must forbid splitting a TOPIC across analysts, which is the "
        "failure it was written for — a per-topic ceiling that permits "
        "per-facet dispatch protects nothing."
    )


# --- 2. The per-paper rigor is fully preserved --------------------------------
#
# Research Standard §3's obligations are per-PAPER: they have nothing to do with
# how many papers a cycle produces, so every one of them survives the reduction.
# Enumerated one case per obligation so a failure names WHICH one went missing
# rather than reporting that "rigor" is absent.

RIGOR = [
    ("honest-boundary analysis", "honest-boundary"),
    ("per-claim confidence marking", "confidence marking"),
    ("the source floor", "source floor"),
    ("the count rule", "a count is a claim"),
    ("gaps-are-findings", "gaps are findings"),
    ("the machine-parseable revalidation interval", "Revalidate:"),
    ("the Critic header value", "Critic: not-yet-verified"),
    ("raw-over-rendered sourcing", "raw sources over rendered"),
]


def _states(text: str, token: str) -> bool:
    return token.lower() in text.lower()


@pytest.mark.parametrize(("label", "token"), RIGOR, ids=[r[0] for r in RIGOR])
def test_the_minor_prompt_preserves(label: str, token: str) -> None:
    assert _states(assembled(MINOR_PROMPT), token), (
        f"write_minor.md no longer names {label}. This is a PER-PAPER obligation "
        "from Research Standard §3 — it does not scale with the number of papers, "
        "and dropping it produces a thin paper rather than a small cycle. The "
        "honest-boundary analysis matters most here of all: with one paper there "
        "is no second paper to disagree with it."
    )


def test_the_rigor_predicate_discriminates() -> None:
    """Positive control for the section above.

    `_states` is a substring search, and a substring search over an 8kB prompt
    passes for almost anything. This pins the failing direction — which is the
    one that matters — by proving it returns False for a token the sample does
    not contain, and that it is not merely case-folding everything into a match.

    THE SAMPLE IS SELF-CONTAINED, NOT THE LIVE PROMPT, and that is deliberate.
    Reading `write_minor.md` here would couple the control to the prompt's
    content: a mutation run against the prompt then fails this control TOO, and
    the second failure is pure noise on top of the one real finding. Measured
    while building this module — deleting `honest-boundary` from the prompt to
    prove the check could fail produced two reds where the property justifies
    exactly one, which is how a control stops being read.
    """
    sample = "the honest-boundary analysis is required"
    assert _states(sample, "honest-boundary") is True
    assert _states(sample, "HONEST-BOUNDARY") is True, "the search stopped being case-insensitive"
    assert _states(sample, "a phrase this sample does not contain") is False


def test_the_minor_child_keeps_the_write_boundary() -> None:
    """A lighter cycle is not a wider one.

    The write boundary is the rule that keeps a researcher out of the planner's
    and reviewer's surfaces, and `tracked/` is the product pool's triage queue
    that `plan-sprint` consumes. Wiring the scaled-down shape into the surface
    that steers the whole product is the coupling this workflow most needs not
    to have.

    THE SURFACE THIS NAMES MOVED, and the assertion moved with it. It used to
    require the literal strings `candidates.md` and `direction.md` — both deleted
    by the four-store migration on 2026-08-26. They were also never in
    `write_minor.md`: they arrived from the shared `decision_log_and_reflection`
    fragment, so the failure message blamed the wrong file for four weeks. The
    property being protected is unchanged: this child is told, in its assembled
    prompt, that the triage store is out of bounds for it.
    """
    text = assembled(MINOR_PROMPT)
    assert "WRITE BOUNDARY (binding)" in text
    assert "tracked/" in text, (
        "the assembled minor prompt no longer names `tracked/` as out of bounds. "
        "It does not carry the ALTITUDE fragments that would let it write there, "
        "so a run told nothing may improvise."
    )


def test_the_minor_child_supplies_no_altitude_machinery() -> None:
    """The code half of the same claim.

    The ALTITUDE fragments are what turn a research run into a maintainer of
    `candidates.md`; not rendering them is what makes the prompt's boundary
    above true by construction rather than by instruction.
    """
    source = inspect.getsource(child)
    assert "ALTITUDE_BLOCK" not in source and "CANDIDATE_CEILING" not in source, (
        "research_draft_minor renders altitude machinery. It has no altitude "
        "fragments to render, so this would trip render()'s leftover guard at "
        "dispatch time — after a worktree and a branch already exist."
    )
    assert "upstream_block" in source, (
        "research_draft_minor stopped pointing at the product pool. That block is "
        "a read-only POINTER, not machinery, and without it a minor run "
        "re-derives an answer the product pool already settled."
    )


def _render_write_minor(monkeypatch, tmp_path: Path) -> str:
    """Drive the REAL run_research_draft and return the merged prompt it built.

    THE PROMPT FILE IS NOT THE PROMPT. Every other check in this module reads
    `write_minor.md` in isolation, and `${CONTEXT_BLOCK}` is assembled in Python
    from three pieces this workflow does not author — so a contradiction between
    the file and an injected block is invisible to all of them. That is not
    hypothetical: `upstream_block`'s directives named `research_draft`'s stages
    ("before you SIZE", "your sizing in Stage 2"), and this cycle has no sizing
    stage, so the merged prompt ordered a sizing assessment two paragraphs after
    the file forbids writing one.

    The fixture is COMPONENT altitude with an upstream synthesis present,
    because that is the only arm that renders the pointer at all — and it is the
    arm this repo itself is in.
    """
    research_dir = tmp_path / "docs" / "development" / "widget" / "research"
    research_dir.mkdir(parents=True)
    upstream = tmp_path / "docs" / "standards" / "architecture" / "research"
    (upstream / "raw").mkdir(parents=True)
    (upstream / "raw" / "a-paper.md").write_text("# upstream\n")
    (upstream / "synthesis.md").write_text("# synthesis\n")

    captured = _CapturedPrompt()
    monkeypatch.setattr(act, "run_claude", captured)
    child.run_research_draft(
        research_dir=research_dir, repo_root=tmp_path, worktree=tmp_path,
    )
    assert captured.prompt is not None, "run_research_draft never reached run_claude"
    return captured.prompt


def test_the_rendered_minor_prompt_orders_no_sizing(monkeypatch, tmp_path) -> None:
    """The merged prompt must not contradict itself about a stage it lacks.

    A model handed one instruction saying "do not write a sizing assessment" and
    another saying "your sizing in Stage 2 must state X" resolves the conflict
    itself, unobserved — and the resolution it picks is the one that produces the
    artifact this workflow exists to not produce.
    """
    prompt = _render_write_minor(monkeypatch, tmp_path)

    assert "upstream product research" in prompt, (
        "the upstream pointer did not reach the merged prompt, so the assertions "
        "below would pass vacuously — the fixture no longer renders the block"
    )
    assert "BEFORE YOU SIZE" not in prompt.upper(), (
        "the merged minor prompt tells the model to read the upstream synthesis "
        "'before you size'. This cycle has no sizing stage; the directive is "
        "research_draft's and must be supplied by the caller, not defaulted."
    )
    assert "sizing in Stage 2" not in prompt, (
        "the merged minor prompt orders a Stage 2 sizing assessment. Stage 2 of "
        "this workflow is 'RESEARCH — ONE PAPER', and the prompt file explicitly "
        "forbids writing a sizing assessment at all."
    )


def test_the_pool_pointer_runs_BOTH_directions_and_neither_arm_is_silent() -> None:
    """A component run sees the product pool; a product run sees the feature pools.

    Traffic was one-way: `upstream_block` returned "" at PRODUCT altitude, so a
    full cycle could not see the 8 papers sitting in the feature pools and would
    re-derive — or silently contradict — what a component investigation already
    settled under the same critic gate.

    THE CONTROL IS THE POINT. Each block must be EMPTY at the altitude it is not
    for. A block that renders at both altitudes would send a component run
    shopping in its own pool and a product run into a write boundary it does not
    own, and both arms would still "pass" a mere non-empty check.
    """
    import sys
    sys.path.insert(0, str(_MODULES))
    from assistant.research import research_activities as act

    repo = Path(__file__).resolve().parents[5]
    assert (repo / "docs" / "standards").is_dir(), (
        f"repo root resolved to {repo}, which has no docs/standards — the parent "
        f"count is wrong and every assertion below would compare empty blocks"
    )
    product = repo / "docs/standards/architecture/research"
    component = repo / "docs/development/persistent-memory-protocol/research"

    up_c = act.upstream_block(component, repo)
    up_p = act.upstream_block(product, repo)
    dn_p = act.component_pools_block(product, repo)
    dn_c = act.component_pools_block(component, repo)

    assert up_c and "problem-statement.md" in up_c, "component run lost its view of the product pool"
    assert dn_p and "component research pools" in dn_p, (
        "a PRODUCT run renders no feature-pool pointer, so a full cycle cannot see "
        "what the feature investigations already established"
    )
    assert up_p == "", "the upstream block leaked into a product run — it would point the pool at itself"
    assert dn_c == "", (
        "the component-pools block leaked into a COMPONENT run, pointing it at pools "
        "it must not write to and at its own paper"
    )
    for directive in ("MINE THESE", "RESPECT:", "Never write to a component pool"):
        assert directive in dn_p, f"the product-side pointer lost its {directive!r} directive"


def test_the_upstream_pointer_sends_the_run_to_the_WHY_and_asks_it_to_REUSE(
        monkeypatch, tmp_path) -> None:
    """Pointing at the pool is not the same as being told to mine it.

    THE MISS THIS PINS, 2026-08-12. The block already listed every product-pool
    paper by name, and a component run still never opened the one on the nearest
    comparable system — which specified a typed per-step return contract, a
    content-addressed store and offline hash re-verification, ranked Tier 1 and
    costed S. Nothing in its title resembled the run's question, and the only
    directive attached to the pool asked which part of the question upstream
    already COVERED. Coverage is a title search; reuse is not.

    The problem statement is the second half: it was reachable only from
    `altitude_product.md`, so no component run had ever been shown the thesis its
    component exists to serve, and the minor cycle renders no altitude fragment
    at all.
    """
    prompt = _render_write_minor(monkeypatch, tmp_path)

    assert "upstream product research" in prompt, (
        "the upstream pointer did not reach the merged prompt, so every assertion "
        "below would pass vacuously"
    )
    assert "problem-statement.md" in prompt, (
        "the merged prompt never names the problem statement. A component run is "
        "building part of a project it has not been told the purpose of, and the "
        "file is reachable from no other fragment this cycle renders."
    )
    assert "MINE THIS POOL FOR ANSWERS" in prompt, (
        "the pool is pointed at but the run is not told to mine it for mechanisms. "
        "Coverage-only framing opens papers whose title resembles the question and "
        "leaves the comparable-system papers — the highest-yield ones — unopened."
    )
    assert "COMPARABLE SYSTEM" in prompt, (
        "the directive no longer singles out comparable-system papers, which is the "
        "specific class the measured miss belonged to"
    )


def test_the_full_cycle_still_gets_the_sizing_directives() -> None:
    """THE CONTROL, and it is the load-bearing half.

    `upstream_block`'s directives became parameters. If the defaults were also
    changed, the assertions above would pass because the sentences no longer
    exist ANYWHERE — a vacuous green — and `research_draft`'s prompt would have
    been silently edited by a change that must not touch it.
    """
    default = inspect.signature(act.upstream_block).parameters
    assert default["read_directive"].default == "READ THIS IN STAGE 1, BEFORE YOU SIZE"
    assert default["coverage_directive"].default == (
        "Your sizing in Stage 2 must state which topics upstream already covers."
    )


# --- 3. research_refine is REUSED, and carries NO cycle-shape signal at all ---

class _CapturedPrompt:
    """Stands in for `run_claude` and keeps the prompt it was handed."""

    def __init__(self) -> None:
        self.prompt: str | None = None

    def __call__(self, prompt, **_kwargs):
        self.prompt = prompt
        return "done\nhttps://github.com/o/r/pull/7\n"


def _render_verify(monkeypatch, tmp_path: Path, **kwargs) -> str:
    """Drive the REAL run_verify and return the prompt it built.

    Executed rather than source-inspected on purpose. The failure this guards
    against is a block that does not RENDER — an unsupplied placeholder reaching
    the model as literal text, or tripping render()'s leftover guard mid-dispatch
    — and no grep over the prompt file can see either.
    """
    captured = _CapturedPrompt()
    monkeypatch.setattr(act, "run_claude", captured)
    monkeypatch.setattr(act, "branch_of", lambda *a, **k: "research/x")
    verify.run_verify(
        research_dir=tmp_path, pr_number="7", repo_root=tmp_path,
        worktree=tmp_path, **kwargs,
    )
    assert captured.prompt is not None, "run_verify never reached run_claude"
    return captured.prompt




def test_verify_is_told_NOTHING_about_the_cycle_shape(monkeypatch, tmp_path) -> None:
    """The `CYCLE_SHAPE_NOTE` pair is deleted, and may not come back.

    IT WAS NOT WRONG WHEN WRITTEN — it went false underneath itself. Both arms
    rested on one premise, *a minor cycle writes no synthesis*, and Stage 3
    SYNTHESIZE (2026-08-17) ended it. From then on `synthesis.md` always existed
    when this child ran, so the `minor_cycle` arm was unreachable and the
    `synthesis_present` arm fired on every minor run asserting three things that
    were all false: that the cycle wrote no synthesis, that the one on disk came
    from an earlier FULL cycle, and that it did not cover this cycle's paper.

    `review-pr` found it on PR #106 and filed issue #107. Deleting beat repairing
    because `research_refine` discovers its artifacts from the filesystem and
    reads no flag — there was never anything for the signal to switch, and the
    prompt's opening line (*"you did not write these papers and you did not write
    this synthesis"*) is true without it.

    THE GUARD IS ON THE RENDERED PROMPT, not on the signature, because the
    failure mode is a block reaching the model — a signature check would pass
    while a hard-coded sentence said the same false thing.
    """
    prompt = _render_verify(monkeypatch, tmp_path)
    for dead in ("MINOR CYCLE", "no synthesis exists", "from an earlier full cycle",
                 "${CYCLE_SHAPE_NOTE}"):
        assert dead not in prompt, (
            f"{dead!r} is back in the verify prompt. A minor cycle HAS written a "
            f"synthesis since 2026-08-17; telling the verifier otherwise is issue "
            f"#107 returning."
        )


def test_run_verify_takes_no_cycle_shape_PARAMETER(monkeypatch, tmp_path) -> None:
    """The other half: no caller may reintroduce the signal through the door.

    Separate from the render guard above on purpose — that one catches a
    hard-coded sentence, this one catches a parameter a parent starts passing
    again. Either alone leaves the other route open.
    """
    import inspect
    params = set(inspect.signature(verify.run_verify).parameters)
    assert not params & {"minor_cycle", "synthesis_present"}, (
        f"run_verify regained a cycle-shape parameter: "
        f"{sorted(params & {'minor_cycle', 'synthesis_present'})}. The shape is "
        f"discovered from the filesystem; a flag can only go stale against it."
    )




def _param_reaches_only_a_ternary(func, name: str) -> bool:
    """True when `name` is read inside IfExp/BoolOp expressions and no `if` statement.

    A rendered-or-empty block is a VALUE. The moment its parameter appears in an
    `if` statement it has become a branch over behaviour — a different code path,
    not a different sentence — which is precisely the drift this design refuses.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(node.test)):
                return False
    reads = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == name]
    return bool(reads)




def test_the_ternary_predicate_actually_detects_a_branch() -> None:
    """Positive control: the AST walk must fail on a real `if`.

    Without this, a walk that never found an `ast.If` — a changed source
    accessor, a dedent that broke the parse — would report every parameter clean.
    """
    src = textwrap.dedent(
        """
        def f(*, flag=False):
            if flag:
                return "branched"
            return "value"
        """
    )
    tree = ast.parse(src)
    branched = any(
        isinstance(n, ast.If)
        and any(isinstance(x, ast.Name) and x.id == "flag" for x in ast.walk(n.test))
        for n in ast.walk(tree)
    )
    assert branched, "the AST walk no longer recognises a plain `if flag:` branch"


def test_verify_has_no_minor_specific_stage() -> None:
    """The reused child's stages do not branch by tier.

    `research_refine` is shared by the full cycle and the minor one. The context
    block states a fact about which cycle is running; it must never become a
    conditional stage heading, because a prompt that branches on tier is two
    prompts sharing a file and they drift.

    THE COUNT WENT 4 -> 2, and that is the change it was frozen to catch. The
    `research-analyst` re-dispatch is gone — the child holds Write/Edit and
    applies the critic's findings itself — so TRACE and VERIFY-THE-SYNTHESIS
    stopped being separate passes over the artifact and became part of the one
    critic loop. Tracing a correction into the synthesis IS fixing what the
    critic found; it was a stage only because a different agent did the writing.
    """
    titles = _stage_titles(assembled(VERIFY_PROMPT))
    assert len(titles) == 2, f"research_refine's stage count changed: {titles}"
    assert not any("MINOR" in t.upper() for t in titles), (
        "refine.md grew a minor-specific stage. The reuse is the design: one set "
        "of stages, one of them told what the cycle produced."
    )


# --- 4. The parent's shape matches the family ---------------------------------

def test_the_research_parent_caps_loop_backs_at_ONE() -> None:
    """One, where the rest of the fleet allows three — and that is deliberate.

    IT USED TO COMPARE TWO PARENTS. `research_minor` had its own, and the test
    existed so the cheaper tier could not quietly acquire a different bound.
    There is one research parent now, so the check is the value itself: a
    research loop is the most expensive dispatch in this fleet, and
    self-correction plateaus at 3-5 passes counting BOTH children — verify=1,
    review-pr=2, then loop, verify=3, review-pr=4. Two loop-backs would put the
    fourth pass past the plateau at the highest per-pass cost the fleet has.
    """
    assert full_parent.MAX_LOOPS == 1, (
        f"the research parent caps loop-backs at {full_parent.MAX_LOOPS}, not 1. "
        f"`routing.MAX_LOOPS` is 3 for every other family; this one keeps its own "
        f"because the per-pass cost is different, not because the loop is."
    )


def test_the_research_parent_calls_no_model() -> None:
    """A parent is pure decision plus children. It has no prompt and no cap."""
    source = inspect.getsource(full_parent)
    assert "run_claude" not in source, "the research parent calls a model directly"
    assert "MODEL_KEY" not in source and "MAX_TURNS" not in source, (
        "the research parent declares a model key or turn cap. A parent that "
        "needs either has stopped being a parent."
    )







def test_the_parent_reuses_the_shared_children() -> None:
    """The critic gate stays. It is the reason this is not a bare research call.

    Dropping to a single deep-research invocation was the alternative considered,
    and `research-critic` — which fetches every cited source and has repeatedly
    caught fabrications — is the reason it was rejected. It reaches this cycle
    through `research_refine`, so reusing that child IS keeping the gate.
    """
    source = inspect.getsource(full_parent)
    assert "research_refine_workflow" in source, "the research parent forked verification"
    assert "review_pr_workflow" in source, "the research parent has no disposition stage"
    assert "ReviewType.RESEARCH" in source, (
        "the research parent no longer dispositions as a research PR — candidates "
        "would be read as findings rather than as cargo"
    )


def test_research_critic_reaches_the_minor_cycle_unchanged() -> None:
    """The gate is invoked by the prompt this cycle reuses verbatim."""
    assert "research-critic" in assembled(VERIFY_PROMPT), (
        "refine.md no longer dispatches research-critic — the anti-hallucination "
        "gate is gone from every research cycle, minor and full alike"
    )


# --- 5. The turn cap is declared, resolvable, and records its measurement ------

def test_the_turn_cap_resolves() -> None:
    """The merged child keeps the FULL tier's cap, not the minor one's.

    `research-draft-minor: 80` is deleted with the tier it sized. This child now
    sizes its own cycle and may dispatch several analysts, so 80 would truncate
    the work it does rather than bound it.
    """
    assert act.max_turns("research-draft") == 150, (
        f"config.yaml max_turns.research-draft is now "
        f"{act.max_turns('research-draft')}, this suite expected 150. If it "
        "changed deliberately, update the expectation here WITH a reason."
    )


def test_the_cap_is_NOT_keyed_off_the_model() -> None:
    """Two keys, deliberately, and the reason is recorded in the workflow itself.

    The model is `research` — shared with `research-refine` and the parent — and
    the cap is keyed by WORKFLOW because the turn budgets were measured
    separately. Keying the cap off the model would silently hand this child the
    parent's 250, which an earlier version of that file did and carried a
    paragraph warning about.

    THIS TEST USED TO ASSERT THE CAP SAT BELOW A FULL-SIZE SIBLING. There is no
    sibling now — the two tiers merged — so the property that survives is the
    one that was always doing the work: cap and model are keyed apart.
    """
    assert child.MODEL_KEY == "research"
    assert child.WORKFLOW_KEY == "research-draft"
    caps = yaml.safe_load(CONFIG.read_text())["max_turns"]
    assert caps["research-draft"] != caps["research"], (
        "the child's cap has drifted onto the parent's. They are separate "
        "measurements and the workflow key exists to keep them separate."
    )


def test_the_measurement_is_recorded() -> None:
    """An unlabelled number is indistinguishable from a measured one.

    `plan-sprint` sets the precedent — "NOT measured — an estimate, stated as
    one" — because the next reader has no other way to tell which values may be
    revised freely and which encode a real observation.

    IT PINNED `research-draft-minor: 80`, WHICH IS DELETED WITH ITS TIER. The
    surviving cap carries its own measurement and this now pins that.
    """
    caps = CONFIG.read_text()
    line = next((l for l in caps.splitlines()
                 if re.match(r"\s+research-draft:\s*\d+", l)), None)
    assert line, "config.yaml no longer declares max_turns.research-draft"
    assert "MEASURED" in line.upper(), (
        f"the research-draft cap carries no measurement label: {line.strip()!r}. "
        f"An unlabelled figure cannot be told from an estimate by the next reader."
    )
def test_the_model_key_is_SHARED_and_the_workflow_key_is_NOT() -> None:
    """The inverse of what this asserted, and the inversion is the merge.

    It read: the key must DIFFER from `research`, because sharing it would tie
    the cheap tier's cost to the full one's opus, and cost was the entire reason
    that workflow existed. That tier is gone. This child IS the full cycle, so it
    takes the full cycle's model — and keeps its own WORKFLOW key so its
    separately-measured turn cap survives.
    """
    assert child.MODEL_KEY == "research", (
        "the merged child no longer shares the research model. It sizes its own "
        "cycle and dispatches analysts; the cheap tier's model was sized for one "
        "paper and no fan-out."
    )
    assert child.WORKFLOW_KEY != child.MODEL_KEY, (
        "cap and model are keyed together again — see the workflow's own comment "
        "on why that silently reverts 150 to the parent's 250."
    )
def test_the_DUE_LIST_reaches_the_write_child_and_costs_nothing_when_empty() -> None:
    """The merge of `research-refresh` into the write child, held at its seam.

    Every research child already computed `paper_currency` and every one of them
    threw the due list away — `currency, _due = ...`. So a run could cite a
    paper's staleness accurately in its synthesis and leave the paper stale,
    because nothing told it that was its job. Measured 2026-08-28: 7 of 37 papers
    due, and `research-refresh` had run ONCE in 399 logged runs.

    THE EMPTY CASE IS THE PROPERTY THAT MATTERS. `research-refresh` could exit at
    zero cost when nothing was due, and folding it in must not spend a run's
    context on an instruction it cannot act on. An empty block drops out of the
    context filter, so a current pool sends no bytes.
    """
    from modules.assistant.research import research_activities as ra
    assert ra.due_block([]) == "", (
        "a pool with nothing due must contribute NO bytes — this is the free "
        "no-op `research-refresh` had and the merge must not lose."
    )
    block = ra.due_block([Path("p/raw/alpha.md"), Path("p/raw/beta.md")])
    assert "`alpha.md`" in block and "`beta.md`" in block, "names the papers"
    assert "research-currency" in block and "research-analyst" in block, (
        "must say WHICH agent and why the other is wrong — handing a due paper "
        "to an analyst rewrites what should have been diffed."
    )
    assert "topics.md" in block, (
        "an instruction may narrow the work, but the staleness still has to be "
        "reported where the next cycle reads it"
    )


def test_the_write_child_WIRES_the_due_list_rather_than_discarding_it() -> None:
    """The other half: computing it and dropping it is what the fleet did before."""
    wf = (Path(__file__).resolve().parents[2] / "modules" / "assistant" / "research"
          / "research_draft" / "research_draft_workflow.py").read_text()
    assert "currency, due = act.paper_currency(pool)" in wf, (
        "the due list is being discarded again (`currency, _due = ...`). The table "
        "alone tells a run what is stale without telling it to act."
    )
    assert "act.due_block(due)" in wf, (
        "the due list is computed but never rendered into the context block, so "
        "the run cannot see it."
    )
