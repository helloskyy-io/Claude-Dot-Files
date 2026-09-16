"""Capture reads a file another actor writes, and nothing bound the two together.

WHY THIS EXISTS. `capture_cited_sources` reports `NOT RUN — no citations.json` and
never fails the run, which is correct: the paper is the deliverable and a rotted
link must not cost it. But the same property makes the whole capture path fail
SILENTLY. Rename the sidecar in the prompt, rename a field, or delete the call at
the entrypoint, and offline citation capture is off for every run afterwards with
nothing red — the exact silent decay the memory protocol exists to prevent.

THE SURFACES THAT HAVE TO AGREE, and none of them can see the others:

  * EVERY `run_research*.py` entrypoint — the parent and both standalone
    children — must CALL the capture; otherwise nothing reads what that run wrote;
  * it must be against the WORKTREE the run wrote into, not the main checkout
    `research_dir` names — the sidecar is written where the run is;
  * `research-analyst.md` must name the FILE the sweep opens;
  * it must name every FIELD the sweep reads out of each row;
  * the PARENT prompts (`draft.md`, `refine.md`) must relay the obligation and
    `draft.md`'s write boundary must PERMIT the file.

THE LAST TWO WERE ADDED AFTER skyynet-master-planning#36, and they are the
reason the first three passed while production wrote nothing. The analyst's
definition carried the instruction; the parent that dispatched it listed its
"binding §3 obligations" without the sidecar and declared a write boundary of
`raw/`, `synthesis.md` and `topics.md` — forbidding the file. And the entrypoint
captured against the main checkout, where no run writes, so even an obedient
analyst's sidecar would have gone unread. Twenty-eight cited sources, empty
store, green suite.

EVERY EXPECTATION IS DERIVED FROM THE READER, never listed here. A test carrying
its own copy of the filename and the field names is a fourth surface that drifts
with the other three, and it would pass while agreeing only with itself.

WHAT THIS DELIBERATELY DOES NOT ASSERT: that any pool on disk HAS a sidecar. The
25 papers in this corpus predate the mechanism, so requiring one would be a false
alarm on legitimate history rather than a finding. The end-to-end demonstration is
`tests/integration/test_pr36_citations_end_to_end.py`: #36's real (url, span, sha)
tuples as the sidecar, the reader filling a store, `verify` resolving it with the
network denied — and the reverse, a cited paper with no sidecar tripping the gap.

⚠ AND THE LIMIT WORTH READING BEFORE TRUSTING THIS: IT CHECKS MENTION, NOT
INSTRUCTION. It proves the spec block names the file and the fields the reader
uses. It cannot prove a research run actually WRITES one — only a real run shows
that, and running research to prove a capture path is the waste this fleet
declined. So this is a PROXY, chosen because the authoritative value is not
available rather than because it was cheaper: the pattern SN-PM2 correctly warned
about when a guard's real subject is expensive to check. Named here so nobody
reads a green suite as "capture is working".
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

TEMPORAL = Path(__file__).resolve().parents[2]
REPO = TEMPORAL.parents[2]
READER = TEMPORAL / "modules/assistant/research/capture_cited_sources.py"
ENTRYPOINT = TEMPORAL / "scripts/run_research.py"
#: EVERY research entrypoint, DERIVED from the tree rather than listed: each one
#: opens a bag, cuts a worktree and dispatches a prompt that writes the sidecar,
#: so each one owes the capture. The standalone children were missed on the
#: first pass because the guard named `run_research.py` alone (#36's shape on a
#: supported path); a fourth entrypoint added tomorrow joins this set unasked.
ENTRYPOINTS = sorted((TEMPORAL / "scripts").glob("run_research*.py"))
#: The one function every entrypoint calls; the reader owns it, and it is where
#: the anchor, the sweep and the gap live once instead of per caller.
HELPER = "capture_into_the_run_bag("
WRITER = REPO / "config/agents/research-analyst.md"
PARENTS = (TEMPORAL / "modules/assistant/research/research_draft/prompts/draft.md",
           TEMPORAL / "modules/assistant/research/research_refine/prompts/refine.md")
DRAFT_PROMPT = PARENTS[0]
WORKFLOW = TEMPORAL / "modules/assistant/research/research/research_workflow.py"
#: The spec is read out of a MARKED BLOCK, not out of the whole file, and that is
#: this guard's own correction. Matching field names anywhere in the prompt was
#: measured VACUOUS on 2026-09-10: deleting the entire sidecar instruction left
#: `quote` and `url` appearing four times each in unrelated prose, so two of the
#: three field arms passed on a prompt that no longer asked for a sidecar at all.
#: Only `claim_id` caught it, by the accident of being a unique string.
#: Scoping also removes the other half of the fragility — a legitimate rewording
#: outside the block can no longer fail the build.
BLOCK_START = "<!-- CITATIONS-SIDECAR-SPEC"
BLOCK_END = "<!-- END CITATIONS-SIDECAR-SPEC -->"


def _spec_block() -> str:
    """The marked spec, or a refusal naming what is missing."""
    text = WRITER.read_text(encoding="utf-8")
    if BLOCK_START not in text or BLOCK_END not in text:
        raise AssertionError(
            f"`{WRITER.name}` carries no {BLOCK_START} block. That block is the "
            f"instruction telling the agent to write the sidecar `capture_cited_sources` "
            f"reads; without it, citation capture reports `NOT RUN` on every research "
            f"run and nothing else goes red.")
    return text[text.index(BLOCK_START):text.index(BLOCK_END)]


def _reader_source() -> str:
    assert READER.is_file(), f"{READER} is gone — the sweep this binds no longer exists"
    return READER.read_text(encoding="utf-8")


def _sidecar_name() -> str:
    """The filename the sweep opens, read off its own constant."""
    tree = ast.parse(_reader_source())
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and any(getattr(t, "id", "") == "SIDECAR_NAME" for t in node.targets)
                and isinstance(node.value, ast.Constant)):
            return str(node.value.value)
    raise AssertionError("SIDECAR_NAME is not a literal assignment in the reader — "
                         "this guard derives the filename from it and cannot")


def _fields_read() -> set[str]:
    """Every key the sweep pulls out of a citation row."""
    return set(re.findall(r'row\.get\(\s*"([^"]+)"', _reader_source()))


def test_EVERY_ENTRYPOINT_STILL_CALLS_THE_SWEEP() -> None:
    """Delete the call and capture is off for that run, with nothing red.

    The population is every `scripts/run_research*.py`, floored at the three
    that exist so a glob that stops matching is red rather than vacuous."""
    assert len(ENTRYPOINTS) >= 3, (
        f"expected the parent and its two standalone children under scripts/; the "
        f"glob found {[e.name for e in ENTRYPOINTS]} — the guard's population is gone")
    for entrypoint in ENTRYPOINTS:
        src = entrypoint.read_text(encoding="utf-8")
        assert HELPER in src, (
            f"{entrypoint.name} no longer calls {HELPER}. It opens a bag and dispatches "
            f"a prompt that writes the sidecar; without this call nothing reads the "
            f"sidecar THAT run wrote, and because the capture never fails a run, "
            f"nothing would have gone red. Measured on skyynet-master-planning#36.")
    reader = READER.read_text(encoding="utf-8")
    assert "capture_cited_sources(" in reader[reader.index("def " + HELPER):], (
        f"the helper in {READER.name} no longer runs the sweep")


def test_THE_WRITER_IS_TOLD_TO_WRITE_THE_FILE_THE_READER_OPENS() -> None:
    """The rename case, and it is the one SN-PM2 named."""
    name = _sidecar_name()
    assert name, "the reader's SIDECAR_NAME is empty — nothing to bind"
    prompt = _spec_block()
    assert name in prompt, (
        f"`{WRITER.name}` does not mention `{name}`, which is the file "
        f"`capture_cited_sources` opens. Either the agent was told to write a "
        f"different filename or the instruction was dropped — both leave capture "
        f"reporting `NOT RUN` forever, silently, on every research run.")


def test_THE_WRITER_IS_TOLD_EVERY_FIELD_THE_READER_READS() -> None:
    """A renamed field is the same silent failure one level down: the file is
    written, parses, and every row is skipped for being incomplete."""
    fields = _fields_read()
    assert fields, (
        "no `row.get(\"...\")` calls found in the reader — the derivation is "
        "broken, so this test would pass while checking nothing")
    prompt = _spec_block()
    missing = sorted(f for f in fields if f not in prompt)
    assert not missing, (
        f"the sidecar spec block in `{WRITER.name}` never names {missing}, which "
        f"`capture_cited_sources` "
        f"reads out of every citation row. A row missing any of them is SKIPPED, "
        f"so the sidecar would be written, parse cleanly, and capture nothing.")


def test_THE_DERIVATION_ITSELF_IS_EXERCISED() -> None:
    """⚠ THE CONTROL. Every assertion above rests on two derivations; if either
    silently returned an empty answer the tests would pass by agreeing with
    nothing. This pins what they actually derived.
    """
    assert _sidecar_name().endswith(".json"), (
        f"the derived sidecar name is {_sidecar_name()!r}, which is not a JSON "
        f"file — the constant moved and this guard is reading the wrong thing")
    assert _spec_block().strip(), "the spec block is empty — nothing is being checked"
    assert len(_fields_read()) >= 3, (
        f"only derived {_fields_read()} from the reader; a citation needs a claim, "
        f"a quoted span and a source, and fewer means the regex stopped matching")


# --- the parent prompts, the boundary, and the anchor -------------------------------

def _write_boundary_line() -> str:
    """The one sentence in `draft.md` that enumerates what the run may write."""
    for line in DRAFT_PROMPT.read_text(encoding="utf-8").splitlines():
        if line.startswith("**WRITE BOUNDARY (binding).**"):
            return line
    raise AssertionError(
        f"`{DRAFT_PROMPT.name}` has no line starting `**WRITE BOUNDARY (binding).**` — "
        f"this guard reads the permitted-files list off it and cannot")


def test_EVERY_PARENT_PROMPT_RELAYS_THE_SIDECAR() -> None:
    """The analyst is dispatched with a list of binding obligations the parent
    writes; an obligation absent from that list is one the analyst can drop."""
    name = _sidecar_name()
    for prompt in PARENTS:
        text = prompt.read_text(encoding="utf-8")
        assert name in text, (
            f"`{prompt.name}` never names `{name}`. The parent relays the analyst's "
            f"binding obligations and the fixer repairs spans; a prompt that does not "
            f"know the sidecar exists leaves it unwritten or stale.")
        for field in sorted(_fields_read()):
            assert f'"{field}"' in text, (
                f"`{prompt.name}` names the sidecar but not its `{field}` field, which "
                f"the reader pulls out of every row")


def test_THE_DRAFT_WRITE_BOUNDARY_PERMITS_THE_FILE_IT_DEMANDS() -> None:
    """THE #36 DEFECT, exactly. The boundary read `only raw/, synthesis.md and
    topics.md` — a binding prohibition on the file the analyst's own definition
    told it to write, and the prohibition won."""
    line = _write_boundary_line()
    assert _sidecar_name() in line, (
        f"`draft.md`'s write boundary does not permit `{_sidecar_name()}`:\n  {line}\n"
        f"An analyst told to write a file its parent forbids writes nothing, and the "
        f"store stays empty with nothing red.")


def test_EVERY_ENTRYPOINT_CAPTURES_AGAINST_THE_WORKTREE_NOT_THE_MAIN_CHECKOUT() -> None:
    """`research_dir` is `repo_root / <arg>` — the main checkout. The run writes
    into the worktree it cut. A capture over the former reads a directory no run
    has touched, and `NOT RUN` is the only thing it can ever report.

    The anchor lives in the helper, so the check is in two halves: every caller
    hands the helper its `worktree=`, and the helper re-anchors through
    `in_worktree` and records the gap. Read over the WHOLE source, not a slice to
    the first `)` — that slice landed inside a nested call and a kwarg reorder
    would have made it vacuous."""
    for entrypoint in ENTRYPOINTS:
        src = entrypoint.read_text(encoding="utf-8")
        assert "pool_dir=research_dir" not in src, (
            f"{entrypoint.name} captures against `research_dir`, the MAIN-CHECKOUT "
            f"path. The sidecar is in the worktree; this is the anchor mismatch "
            f"`in_worktree` exists to remove, and it makes every capture a NOT RUN.")
        call = src[src.index(HELPER):]
        call = call[:call.index("bag=")]
        assert "worktree=" in call, (
            f"{entrypoint.name} calls {HELPER} without `worktree=` — there is nothing "
            f"to anchor the capture to")
    helper = READER.read_text(encoding="utf-8")
    helper = helper[helper.index("def " + HELPER):]
    assert "in_worktree(" in helper, (
        f"{HELPER} in {READER.name} no longer re-anchors the pool into the worktree")
    assert "record_capture_gap(" in helper, (
        f"{HELPER} in {READER.name} never records the capture gap — an empty store "
        f"for a cited paper is back to being a note nobody reads")
    parent = ENTRYPOINT.read_text(encoding="utf-8")
    assert 'worktree=result["worktree"]' in parent, (
        "run_research.py does not hand the helper the worktree its workflow returned")
    assert '"worktree": worktree' in WORKFLOW.read_text(encoding="utf-8"), (
        f"{WORKFLOW.name} no longer returns its worktree; the entrypoint has nothing "
        f"to anchor the capture to")
