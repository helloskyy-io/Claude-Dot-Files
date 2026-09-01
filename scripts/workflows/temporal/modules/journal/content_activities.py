"""Capture and resolve — the content store's two I/O boundaries.

REQUIREMENT 8, AND IT IS PHASE 1 REQUIREMENT 11's ARGUMENT APPLIED TO THIS
STORE'S TWO I/O BOUNDARIES. A source read through a path that does not capture is
a citation nobody can re-check offline, and it fails silently — there is no
error, no missing file, and nothing to notice until somebody tries to verify a
claim and finds no bytes behind it. Temporal Standard §3 puts I/O in the
activities layer, which is why these live here and not in `content_store.py`:
that module is layout and hashing, and it does no network and makes no decisions
about a run.

⚠ AND AN ACTIVITY BOUNDARY DOES NOT MAKE THE CALL HAPPEN — the same caveat
`journal_activities` states about bag-open, and it is more acute here. Nothing
forces a workflow to capture before it cites. What supplies the guarantee is
`verify` FAILING CLOSED: a citation naming a digest with no stored bytes is
reported `missing` with a non-zero exit, so a read path that skipped capture
shows up as a finding rather than as silence.

WHAT IS BUILDABLE TODAY AND WHAT IS PORT-TIME, so neither half is claimed
falsely. Layer placement, invocation, fail-stop and idempotency are here.
Orchestrator-driven retry and recorded execution belong to a worker that does not
exist yet, and the port carries them. Idempotency is free rather than designed:
capturing the same bytes twice computes the same digest and writes the same
path, which is §7.1 satisfied by content addressing.

⚠ THE READ-SIDE BOUNDARY IS THE HONEST GAP, AND IT IS RULED RATHER THAN HIDDEN.
In this fleet a research citation is read by a model inside a `claude -p` child,
through the model's own tooling. Adding a fetcher here does not reach that read,
because nothing routes the model's reads through fleet code — the same structural
problem the emit rule found for writes, applied to reads. Of the two arms the
phase names, this build takes the one that stays inside the component:

  * `capture_fetched_source` — bytes already in hand are stored. The caller
    states its own provenance, so the day a fleet-side read path exists it
    passes `capture="read-time"` and the guarantee is the strong one with no
    stored record rewritten.
  * `capture_source` — this module fetches under `source_fetch`'s policy and
    stores. Used post-exit to harvest what a run cited, which is the shape the
    model-issued harvest already uses for writes, and it defaults to
    `capture="harvest"` because that is what it is.

The weaker guarantee is recorded on each row rather than amended into a global
sentence, so a `verify` result reports the provenance it read instead of
asserting one. See `citations.py` § r7(c).
"""

from __future__ import annotations

from pathlib import Path

from .bag import PAYLOAD_DIR, Bag, contained_relpath, safe_payload_segment
from .citations import (CAPTURE_HARVEST, CAPTURE_READ_TIME, CAPTURE_KINDS,
                        Citation, CitationError, is_git_ref, new_citation,
                        record_citation)
from .content_store import load_object, store_bytes
from .source_fetch import FetchPolicy, fetch_source

__all__ = ["capture_source", "capture_fetched_source", "capture_code_citation",
           "resolve_citation"]


def _writer_directory(bag: Bag, stage: str) -> Path:
    """The directory this stage's citation rows are appended to.

    ADOPTED WHEN IT ALREADY EXISTS, ALLOCATED WHEN IT DOES NOT, and the
    difference from `Bag.writer_dir` matters. That method allocates a name no
    other writer can be handed, which is right for a writer claiming a workspace
    and wrong here: a stage capturing its second source must append to the file
    its first source created, not to `<stage>-2`. So the exact directory is used
    when it is already there.

    ⚠ AND THE STAGE IS A CALLER-SUPPLIED STRING, WHICH THIS COMPOSED ONTO THE
    PAYLOAD PATH DIRECTLY UNTIL `test_journal_containment` SAID SO. That is the
    fifth instance of this package's own escape class, written by the pass that
    had just read the module documenting the other four. It goes through
    `safe_payload_segment` (no separator survives, no bare `..`) and then through
    `contained_relpath` (proven to stay under `data/`) — the same two rules
    `Bag.writer_dir` keeps, reached by name rather than re-implemented.
    """
    candidate = bag.path / contained_relpath(
        f"{PAYLOAD_DIR}/{safe_payload_segment(stage)}")
    if candidate.is_dir():
        return candidate
    return bag.writer_dir(stage)


def capture_fetched_source(*, bag: Bag, stage: str, claim_id: str, quote: str,
                           source_ref: str, data: bytes,
                           capture: str = CAPTURE_READ_TIME,
                           media_type: str | None = None) -> Citation:
    """Store bytes already in hand and record the citation naming them.

    THE ENTRY POINT A ROUTED READ PATH USES, and it is why r7(c)'s expensive arm
    stays reachable at no cost: a caller that obtained the bytes AS THE SOURCE
    WAS READ passes them here with the default provenance, and the citation
    carries the strong guarantee. Nothing about the store changes between the
    two arms — only who calls, when, and what they say about it.
    """
    if capture not in CAPTURE_KINDS:
        raise CitationError(
            f"capture {capture!r} is not one of {', '.join(CAPTURE_KINDS)}. It "
            f"records which guarantee the row carries and has no default here.")
    digest = store_bytes(bag.path, data)
    citation = new_citation(claim_id=claim_id, stage=stage, quote=quote,
                            source_ref=source_ref, capture=capture,
                            page_content_hash=digest, media_type=media_type)
    record_citation(_writer_directory(bag, stage), citation)
    return citation


def capture_source(*, bag: Bag, stage: str, claim_id: str, quote: str, url: str,
                   capture: str = CAPTURE_HARVEST,
                   policy: FetchPolicy | None = None) -> Citation:
    """Fetch one source under the policy, store its bytes, record the citation.

    THE ONLY PLACE THIS PACKAGE REACHES THE NETWORK, and it is deliberately not
    on `verify`'s INTRA-PACKAGE import closure: the checker resolves from the
    store alone, which is requirement 2, and keeping the fetcher out of that
    graph is what makes the property structural rather than a promise.

    ⚠ THE QUALIFIER IS LOAD-BEARING AND WAS MISSING. `modules/journal/__init__`
    imports this module eagerly, so a process entering through the PACKAGE — and
    `scripts/verify_citations.py` does — has `urllib` loaded whether or not
    `verify` reaches it. The closure is what the guard asserts and what a
    reviewer can check; process-level absence is NOT claimed, and is not what
    requirement 2 asks for. The demonstration that settles it is the run with the
    network denied at the C library, where the fetcher IS imported and the
    verifier returns every verdict regardless.

    ⚠ THE REDIRECT CHAIN IS NOT DURABLE, DELIBERATELY. `FetchedSource.hops`
    records every URL visited and only `final_url` reaches the citation row, so
    a source that arrived via a redirect reads on disk as though it had been
    fetched directly. Carrying `hops` would be a v1 schema field with no reader,
    and this record refuses fields nothing consumes; the operator-facing place
    for the chain is the refusal message when a hop is rejected, which names it.

    ⚠ THE SPAN IS NOT CHECKED HERE, AND THAT IS NOT AN OVERSIGHT. Refusing to
    record a citation whose quote is absent from the fetched bytes would move a
    finding out of `verify` and into the capture path, where it becomes an error
    a run has to handle mid-flight rather than a reported outcome an operator
    reads. `span-missing` exists as a distinct exit code precisely so that a
    wrong quotation is a FINDING about the record, not a failure of capture.
    """
    fetched = fetch_source(url, policy=policy)
    return capture_fetched_source(bag=bag, stage=stage, claim_id=claim_id,
                                  quote=quote, source_ref=fetched.final_url,
                                  data=fetched.data, capture=capture,
                                  media_type=fetched.media_type)


def capture_code_citation(*, bag: Bag, stage: str, claim_id: str, quote: str,
                          commit_sha: str, path: str | None = None) -> Citation:
    """Record a code citation as a commit sha. Stores nothing. Requirement 6.

    NO BYTES ARE WRITTEN, WHICH IS THE REQUIREMENT AND NOT A SHORTCUT. Git is
    already content-addressed, so copying a diff into the store would be a second
    name for one guarantee and the copy is the one that can drift from the
    repository it came from. `verify` resolves these through `git cat-file`.
    """
    source_ref = f"git:{commit_sha}" + (f":{path}" if path else "")
    if not is_git_ref(source_ref):
        raise CitationError(
            f"{commit_sha!r} is not a full 40-character commit sha. An "
            f"abbreviated sha is a prefix search whose answer can change as a "
            f"repository grows objects, and a citation must name one object "
            f"permanently.")
    citation = new_citation(claim_id=claim_id, stage=stage, quote=quote,
                            source_ref=source_ref, capture=CAPTURE_READ_TIME)
    record_citation(_writer_directory(bag, stage), citation)
    return citation


def resolve_citation(*, bag: Bag, citation: Citation) -> bytes:
    """The stored bytes behind one citation, re-hashed on the way out.

    r7(d) — THIS IS `content_store.load_object` AND NOT A SECOND RESOLVER. It
    exists as an activity so a workflow reaching into the store crosses a
    declared I/O boundary rather than importing a layout module, and it adds no
    behaviour of its own: adding any would create the second read path r7(d)
    exists to prevent.

    A git citation is refused rather than silently resolved from a repository
    this function was not given, because guessing which checkout a sha belongs to
    is exactly the wrong answer. `verify.verify_citation` takes an explicit
    `repo_root` and is where that resolution belongs.
    """
    if is_git_ref(citation.source_ref):
        raise CitationError(
            f"claim {citation.claim_id} cites code ({citation.source_ref}), "
            f"which resolves from a git object database rather than from the "
            f"content store. Use `verify.git_blob` with the repository it "
            f"belongs to — this function will not guess which checkout that is.")
    return load_object(bag.path, citation.page_content_hash)
