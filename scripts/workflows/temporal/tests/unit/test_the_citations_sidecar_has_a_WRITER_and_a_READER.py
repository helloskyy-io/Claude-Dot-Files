"""Capture reads a file another actor writes, and nothing bound the two together.

WHY THIS EXISTS. `capture_cited_sources` reports `NOT RUN — no citations.json` and
never fails the run, which is correct: the paper is the deliverable and a rotted
link must not cost it. But the same property makes the whole capture path fail
SILENTLY. Rename the sidecar in the prompt, rename a field, or delete the call at
the entrypoint, and offline citation capture is off for every run afterwards with
nothing red — the exact silent decay the memory protocol exists to prevent.

THE THREE SURFACES THAT HAVE TO AGREE, and none of them can see the others:

  * `run_research.py` must CALL the sweep — otherwise nothing reads anything;
  * `research-analyst.md` must name the FILE the sweep opens;
  * it must name every FIELD the sweep reads out of each row.

EVERY EXPECTATION IS DERIVED FROM THE READER, never listed here. A test carrying
its own copy of the filename and the field names is a fourth surface that drifts
with the other three, and it would pass while agreeing only with itself.

WHAT THIS DELIBERATELY DOES NOT ASSERT: that any pool on disk HAS a sidecar. The
25 papers in this corpus predate the mechanism, so requiring one would be a false
alarm on legitimate history rather than a finding. The end-to-end demonstration is
owned by PMP phase 4, where real run-bag data is already under test.

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
WRITER = REPO / "config/agents/research-analyst.md"
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


def test_THE_ENTRYPOINT_STILL_CALLS_THE_SWEEP() -> None:
    """Delete the call and capture is off for every run, with nothing red."""
    src = ENTRYPOINT.read_text(encoding="utf-8")
    assert "capture_cited_sources(" in src, (
        f"{ENTRYPOINT.name} no longer calls capture_cited_sources. Nothing else "
        f"reads the sidecar, so citation capture is off for every research run — "
        f"and because the sweep never fails a run, nothing would have gone red.")


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
