"""research-minor: the multi-paper machinery is ABSENT, the per-paper rigor is NOT.

The workflow's whole value proposition is a subtraction, and a subtraction is
the one kind of change a green suite cannot notice on its own. Adding a
`research_minor` package makes every auto-discovering sweep in this directory
cover it for free — isolation invariants, MODEL_KEY resolution, placeholder
suppliers — and NONE of them can tell whether the thing that shipped is
actually smaller than its sibling. That is what this module checks.

WHERE THE CONTROLS COME FROM, and why they are not synthetic. Every assertion
of the form "the minor prompt does NOT contain X" is paired with the SAME
predicate run against `research_write/prompts/write.md`, which must return True.
The full-size sibling is a live, maintained fixture of exactly the machinery
being removed, so a predicate that silently stopped matching — a reworded stage
heading, a moved artifact path — fails on the full cycle rather than passing
vacuously on the minor one. A control that can only ever be satisfied is the
failure mode controls exist to prevent, and a hand-written scratch fixture
drifts away from the real prompt the moment the real prompt is edited.

AND THE CYCLE-SHAPE BLOCK IS EXERCISED, NOT GREPPED. `research_verify` is
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

import pytest
import yaml

from modules.assistant.research import research_activities as act
from modules.assistant.research.research import research_workflow as full_parent
from modules.assistant.research.research_minor import research_minor_workflow as parent
from modules.assistant.research.research_verify import research_verify_workflow as verify
from modules.assistant.research.research_write_minor import (
    research_write_minor_workflow as child,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
CONFIG = REPO_ROOT / "config.yaml"
_RESEARCH = Path(__file__).resolve().parents[2] / "modules" / "assistant" / "research"

MINOR_PROMPT = _RESEARCH / "research_write_minor" / "prompts" / "write_minor.md"
FULL_PROMPT = _RESEARCH / "research_write" / "prompts" / "write.md"
VERIFY_PROMPT = _RESEARCH / "research_verify" / "prompts" / "verify.md"


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


# (label, predicate) — each must be FALSE for the minor prompt and TRUE for the
# full one. The pairing is the evidence; either half alone proves nothing.
MACHINERY = [
    ("topics.md-as-a-write-target",
     lambda t: _writes_artifact_at_contract_path(t, "topics.md")),
    ("synthesis.md-as-a-write-target",
     lambda t: _writes_artifact_at_contract_path(t, "synthesis.md")),
    ("a-SIZE-stage", lambda t: _has_stage_titled(t, "SIZE")),
    ("a-SYNTHESIZE-stage", lambda t: _has_stage_titled(t, "SYNTHESIZE")),
    ("a-per-topic-fan-out", _fans_out_per_topic),
]


@pytest.mark.parametrize(("label", "predicate"), MACHINERY, ids=[m[0] for m in MACHINERY])
def test_the_minor_prompt_does_not_carry(label: str, predicate) -> None:
    assert predicate(MINOR_PROMPT.read_text()) is False, (
        f"write_minor.md carries {label}. The minor cycle's entire value is that "
        "this machinery is absent — a one-paper run that still emits a topic list "
        "or a synthesis is the full cycle wearing a smaller name."
    )


@pytest.mark.parametrize(("label", "predicate"), MACHINERY, ids=[m[0] for m in MACHINERY])
def test_the_full_prompt_still_carries_it(label: str, predicate) -> None:
    """THE CONTROL, and it is the load-bearing half.

    Without it, every assertion above is satisfied by a predicate that stopped
    matching anything — a reworded stage heading or a moved artifact path turns
    the whole section into a permanent pass while the machinery it names could
    quietly return to the minor prompt.
    """
    assert predicate(FULL_PROMPT.read_text()) is True, (
        f"the predicate for {label} no longer fires on research_write's own "
        "prompt, so it can no longer prove that prompt's absence from the minor "
        "one. The check has gone blind, not green."
    )


def test_the_minor_cycle_has_exactly_three_stages() -> None:
    """Discover -> one paper -> submit. Nothing between.

    Counted rather than named so a renamed stage does not silently become a
    fourth: the shape is the claim, and a fourth stage in a workflow whose
    premise is 'fewer artifacts' is the regression worth catching.
    """
    titles = _stage_titles(MINOR_PROMPT.read_text())
    assert len(titles) == 3, f"expected 3 stages, found {len(titles)}: {titles}"
    assert len(_stage_titles(FULL_PROMPT.read_text())) == 5, (
        "research_write no longer has 5 stages — the comparison this suite draws "
        "between the two shapes is against a moved reference"
    )


def test_the_minor_child_dispatches_exactly_one_analyst() -> None:
    """The fan-out is the cost, and one analyst is the whole point."""
    text = MINOR_PROMPT.read_text()
    assert "ONE analyst. Not two" in text, (
        "write_minor.md lost its explicit one-analyst bound. Absence of a "
        "per-topic loop is not the same as a stated ceiling: a model handed a "
        "two-part question will split it into two analysts unless told not to."
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
    assert _states(MINOR_PROMPT.read_text(), token), (
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
    and reviewer's surfaces, and `candidates.md` / `direction.md` are the product
    pool's triage queues that `plan-sprint` consumes. Wiring the scaled-down
    shape into the surface that steers the whole product is the coupling this
    workflow most needs not to have.
    """
    text = MINOR_PROMPT.read_text()
    assert "WRITE BOUNDARY (binding)" in text
    assert "candidates.md" in text and "direction.md" in text, (
        "write_minor.md no longer names candidates.md/direction.md as out of "
        "bounds. It does not carry the ALTITUDE fragments that would let it "
        "maintain them, so a run told nothing may improvise."
    )


def test_the_minor_child_supplies_no_altitude_machinery() -> None:
    """The code half of the same claim.

    The ALTITUDE fragments are what turn a research run into a maintainer of
    `candidates.md`; not rendering them is what makes the prompt's boundary
    above true by construction rather than by instruction.
    """
    source = inspect.getsource(child)
    assert "ALTITUDE_BLOCK" not in source and "CANDIDATE_CEILING" not in source, (
        "research_write_minor renders altitude machinery. It has no altitude "
        "fragments to render, so this would trip render()'s leftover guard at "
        "dispatch time — after a worktree and a branch already exist."
    )
    assert "upstream_block" in source, (
        "research_write_minor stopped pointing at the product pool. That block is "
        "a read-only POINTER, not machinery, and without it a minor run "
        "re-derives an answer the product pool already settled."
    )


def _render_write_minor(monkeypatch, tmp_path: Path) -> str:
    """Drive the REAL run_write_minor and return the merged prompt it built.

    THE PROMPT FILE IS NOT THE PROMPT. Every other check in this module reads
    `write_minor.md` in isolation, and `${CONTEXT_BLOCK}` is assembled in Python
    from three pieces this workflow does not author — so a contradiction between
    the file and an injected block is invisible to all of them. That is not
    hypothetical: `upstream_block`'s directives named `research_write`'s stages
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
    child.run_write_minor(
        research_dir=research_dir, repo_root=tmp_path, worktree=tmp_path,
    )
    assert captured.prompt is not None, "run_write_minor never reached run_claude"
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
        "research_write's and must be supplied by the caller, not defaulted."
    )
    assert "sizing in Stage 2" not in prompt, (
        "the merged minor prompt orders a Stage 2 sizing assessment. Stage 2 of "
        "this workflow is 'RESEARCH — ONE PAPER', and the prompt file explicitly "
        "forbids writing a sizing assessment at all."
    )


def test_the_full_cycle_still_gets_the_sizing_directives() -> None:
    """THE CONTROL, and it is the load-bearing half.

    `upstream_block`'s directives became parameters. If the defaults were also
    changed, the assertions above would pass because the sentences no longer
    exist ANYWHERE — a vacuous green — and `research_write`'s prompt would have
    been silently edited by a change that must not touch it.
    """
    default = inspect.signature(act.upstream_block).parameters
    assert default["read_directive"].default == "READ THIS IN STAGE 1, BEFORE YOU SIZE"
    assert default["coverage_directive"].default == (
        "Your sizing in Stage 2 must state which topics upstream already covers."
    )


# --- 3. research_verify is REUSED: a rendered block, not a behavioural flag ----

_MANDATED = "MINOR CYCLE — one paper, no synthesis. The paper IS the deliverable."

# The block VERBATIM, so the differ below can subtract it exactly. Kept beside
# the fragment above rather than derived from the workflow: a copy the workflow
# could not silently change is the point — deriving it from `run_verify` would
# make the comparison true by construction.
_BLOCK = (
    "**MINOR CYCLE — one paper, no synthesis. The paper IS the deliverable.** "
    "Stage 1 verifies it exactly as always. **Stages 2 and 3 emit "
    "`SKIPPED — minor cycle, no synthesis exists`.** Do not create one, and "
    "do not treat its absence as a defect."
)


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


def test_the_cycle_shape_block_renders_for_a_minor_cycle(monkeypatch, tmp_path) -> None:
    prompt = _render_verify(monkeypatch, tmp_path, minor_cycle=True)
    assert _MANDATED in prompt, (
        "the minor-cycle block did not reach the prompt. verify.md opens by "
        "asserting 'you did not write this synthesis', which presupposes one "
        "exists — a run reading that against a directory with none will stall or "
        "INVENT one, and inventing is the exact failure this child guards against."
    )
    assert "SKIPPED — minor cycle, no synthesis exists" in prompt, (
        "the block no longer tells stages 2 and 3 what to emit, so their skip "
        "becomes the model's improvisation rather than the parent's instruction"
    )


def test_the_block_is_empty_by_default(monkeypatch, tmp_path) -> None:
    """The full cycle must be BYTE-UNAFFECTED by this addition.

    `research_verify` is shared. If the default were anything but empty, adding
    the minor cycle would have changed the prompt every full research cycle
    receives — a silent edit to a verified path, made by a feature that is not
    supposed to touch it.
    """
    prompt = _render_verify(monkeypatch, tmp_path)
    assert "MINOR CYCLE" not in prompt
    assert "${CYCLE_SHAPE_NOTE}" not in prompt, (
        "the placeholder survived rendering as literal text — render()'s leftover "
        "guard should have raised, so the supplier name has drifted"
    )


def test_the_two_renders_differ_by_exactly_the_block(monkeypatch, tmp_path) -> None:
    """The precise claim, not 'MINOR CYCLE is absent'.

    `research_verify` is SHARED. The risk worth pinning is not that the block
    fails to appear — the test above covers that — it is that adding it
    perturbed the prompt every FULL research cycle receives: a reordered
    section, a displaced heading, a supplier renamed out from under a sibling
    placeholder. Deleting the block from the minor render must reproduce the
    default render exactly, modulo the blank line an empty substitution leaves.
    """
    default = _render_verify(monkeypatch, tmp_path)
    minor = _render_verify(monkeypatch, tmp_path, minor_cycle=True)

    assert minor != default, "requesting the minor shape changed nothing"
    assert " ".join(minor.replace(_BLOCK, "").split()) == " ".join(default.split()), (
        "removing the cycle-shape block from the minor render does not reproduce "
        "the default render. Adding it perturbed the prompt that every full "
        "research cycle receives, which this change must not touch."
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


@pytest.mark.parametrize("param", ["minor_cycle", "correction_pass"])
def test_the_flag_reaches_no_if_statement(param: str) -> None:
    """`correction_pass` is the model and is checked alongside deliberately.

    It is the shape `minor_cycle` was built to copy, so running both through one
    predicate proves the predicate describes the EXISTING convention rather than
    having been fitted to the new parameter.
    """
    assert _param_reaches_only_a_ternary(verify.run_verify, param), (
        f"`{param}` reaches an `if` statement in run_verify. A flag that alters "
        "which artifacts a workflow emits is a behavioural branch inside a prompt, "
        "and prompt branches are where drift lives."
    )


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
    """The reused child's own stages are untouched.

    The block states a fact about the cycle; it must not have grown a fourth
    stage or a conditional stage heading in the prompt itself.
    """
    titles = _stage_titles(VERIFY_PROMPT.read_text())
    assert len(titles) == 4, f"research_verify's stage count changed: {titles}"
    assert not any("MINOR" in t.upper() for t in titles), (
        "verify.md grew a minor-specific stage. The reuse is the design: one set "
        "of stages, one of them told what the cycle produced."
    )


# --- 4. The parent's shape matches the family ---------------------------------

def test_the_loop_back_bound_matches_the_full_cycle() -> None:
    assert parent.MAX_LOOPS == full_parent.MAX_LOOPS == 1, (
        f"research_minor caps loop-backs at {parent.MAX_LOOPS} against the full "
        f"cycle's {full_parent.MAX_LOOPS}. Self-correction plateaus at 3-5 passes; "
        "the bound is a property of that plateau, not of the cycle's size."
    )


def test_the_parent_calls_no_model() -> None:
    """A parent is pure decision plus children. It has no prompt and no cap."""
    source = inspect.getsource(parent)
    assert "run_claude" not in source, "research_minor calls a model directly"
    assert "MODEL_KEY" not in source and "MAX_TURNS" not in source, (
        "research_minor declares a model key or turn cap. A parent that needs "
        "either has stopped being a parent."
    )


def test_the_parent_asks_verify_for_the_minor_shape() -> None:
    assert "minor_cycle=True" in inspect.getsource(parent), (
        "research_minor no longer tells research_verify what it produced. verify "
        "would then read 'you did not write this synthesis' against a directory "
        "with none."
    )


def test_the_parent_reuses_the_shared_children() -> None:
    """The critic gate stays. It is the reason this is not a bare research call.

    Dropping to a single deep-research invocation was the alternative considered,
    and `research-critic` — which fetches every cited source and has repeatedly
    caught fabrications — is the reason it was rejected. It reaches this cycle
    through `research_verify`, so reusing that child IS keeping the gate.
    """
    source = inspect.getsource(parent)
    assert "research_verify_workflow" in source, "research_minor forked verification"
    assert "review_pr_workflow" in source, "research_minor has no disposition stage"
    assert "ReviewType.RESEARCH" in source, (
        "research_minor no longer dispositions as a research PR — candidates would "
        "be read as findings rather than as cargo"
    )


def test_research_critic_reaches_the_minor_cycle_unchanged() -> None:
    """The gate is invoked by the prompt this cycle reuses verbatim."""
    assert "research-critic" in VERIFY_PROMPT.read_text(), (
        "verify.md no longer dispatches research-critic — the anti-hallucination "
        "gate is gone from every research cycle, minor and full alike"
    )


# --- 5. The turn cap is declared, resolvable, and labelled an estimate ---------

def test_the_turn_cap_resolves() -> None:
    assert act.max_turns("research-write-minor") == 80, (
        f"config.yaml max_turns.research-write-minor is now "
        f"{act.max_turns('research-write-minor')}, this suite expected 80. If it "
        "changed deliberately, update the expectation here WITH a reason."
    )


def test_the_cap_is_below_its_full_size_sibling() -> None:
    """The claim the workflow makes about itself, checked.

    A minor cycle is a strict subset of a full one — no topics.md, no fan-out,
    no synthesis. A cap at or above research-write's would mean the subtraction
    was never made, or was never believed.
    """
    caps = yaml.safe_load(CONFIG.read_text())["max_turns"]
    assert caps["research-write-minor"] < caps["research-write"], (
        f"research-write-minor is capped at {caps['research-write-minor']} against "
        f"research-write's {caps['research-write']}"
    )


def test_the_estimate_is_labelled_as_one() -> None:
    """An unlabelled number is indistinguishable from a measured one.

    `plan-sprint` sets the precedent — 'NOT measured — an estimate, stated as
    one' — and the reason is that the next reader of this map has no other way to
    tell which values may be revised freely and which encode a real observation.

    SCOPED TO THE CAP'S OWN COMMENT BLOCK BY STRUCTURE, NOT BY A DELIMITER.
    The first version narrowed with `split("\\n  research", 1)` — the next
    `research*` key — and `research-write-minor` is the LAST key under
    `max_turns:`, so that delimiter never matched and the search ran to EOF.
    Caught by mutation: stripping the label from this cap while any later line
    in the file said "NOT MEASURED" left all 40 tests green. A check that reads
    a neighbour's evidence is not scoped, and the docstring claiming otherwise
    is what makes it dangerous. Continuation lines are `#`-only, so the block
    ends at the first line that is not one — a property of the file's shape
    rather than of which key happens to come next.
    """
    lines = CONFIG.read_text().splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.strip().startswith("research-write-minor: 80")]
    assert len(starts) == 1, "the research-write-minor cap is no longer declared exactly once as 80"

    block = [lines[starts[0]]]
    for ln in lines[starts[0] + 1:]:
        if not ln.strip().startswith("#"):
            break
        block.append(ln)

    assert "NOT MEASURED" in "\n".join(block).upper(), (
        "the research-write-minor cap no longer states that it is an estimate. "
        "Nothing has run this workflow; a bare integer here reads as measured."
    )


def test_the_model_key_is_its_own() -> None:
    """Keyed separately from `research`, which is the point of the cheap shape.

    `test_model_keys_resolve.py` already proves the key resolves. This proves it
    is a DIFFERENT key — sharing `research` would tie the minor cycle's cost to
    the full one's opus, and cost is the entire reason this workflow exists.
    """
    assert child.MODEL_KEY == "research-write-minor"
    models = yaml.safe_load(CONFIG.read_text())["models"]
    assert models["research-write-minor"] != models["research"], (
        "research-write-minor resolves to the same model as the full research "
        "cycle, so the scaled-down shape costs the same per turn as the shape it "
        "was built to replace"
    )
