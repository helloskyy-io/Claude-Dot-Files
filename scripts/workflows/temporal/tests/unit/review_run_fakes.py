"""The shared fakes the `review_pr` parent's tests run against.

A HELPER MODULE, NOT A TEST MODULE, AND THAT DISTINCTION IS THE WHOLE POINT.
`test_convergence.py` used to import these four names out of `test_exit_record.py`
in nine places — the only cross-test-module import in the repo. Three things were
wrong with that and none of them was loud:

  * the `_` prefix said "private to this file" while the names were a contract
    between two files, so an edit made for exit-record reasons broke a different
    module with a traceback naming neither;
  * it resolved only under pytest's default `prepend` import mode, which
    `pytest.ini` does not pin — `--import-mode=importlib` breaks all nine at
    once, and the break is an `ImportError` AT COLLECTION;
  * a collection failure is the one failure `testing/scripts/mutate.sh` cannot
    read (issue #72: it exits 2 and prints MUTATION DEMONSTRATED). This phase's
    entire guard evidence is a mutation loop, so a latent collection break sat
    directly underneath it.

`tests/conftest.py` puts this directory on `sys.path`, which is what makes the
import independent of pytest's mode rather than incidental to it. The names are
unchanged so no call site moved — the module name now carries the scope signal
the underscore was carrying wrongly.

The name is component-prefixed and repo-unique, per the Testing Standard's
binding rule for helper modules imported BY NAME.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from modules.assistant.review_pr import exit_record as er


RUN_ID = "aaaabbbbccccdddd"

# The dispatch's own repository, as `gh repo view --json nameWithOwner` answers.
REPO_SLUG = "owner/repo"

# The `completion_ref` rule R5b compares against — built by the PARENT from the
# PR it dispatched and the slug of the repo it is operating in, never from
# anything the child said. `_record()`'s default matches it, so every test that
# is not ABOUT R5b passes through it unchanged and R5b's happy path is exercised
# by all of them rather than by one.
EXPECTED_REF = {
    "substrate": "github", "kind": "pull", "id": "67",
    "uri": "https://github.com/owner/repo/pull/67",
}


def _record(**overrides) -> dict:
    """A record that routes cleanly. Every test using it mutates ONE thing."""
    base = {
        "schema_version": er.SCHEMA_VERSION,
        "run_id": RUN_ID,
        "outcome": "merge",
        "completion_ref": dict(EXPECTED_REF),
        "findings": [{"id": "a-stable-slug", "disposition": "fixed"}],
    }
    base.update(overrides)
    return base


def _nonce_in(prompt: str) -> str:
    """The 32-hex nonce `render_prompt` substituted into the prompt."""
    m = re.search(r"\b[0-9a-f]{32}\b", prompt)
    assert m, "the parent did not substitute a run_id into the prompt"
    return m.group(0)


class _FakeWorkflow:
    """The `run_review` collaborators, replaced at their real boundaries.

    Nothing here fakes `route` or `parse_verdict` — those are the code under
    test. What is faked is the I/O: `gh`, the worktree, the model invocation and
    the log the record arrives in.
    """

    # The durable block the child is presumed to have posted. Default renders
    # the same one finding `_record()` carries — id AND disposition, because the
    # invariant compares pairs — so it holds unless a test deliberately breaks it.
    DEFAULT_BLOCK = ("pr_review:\n  pr: 67\n  findings:\n"
                     "    - id: a-stable-slug\n      disposition: fixed\n")

    def __init__(self, record: dict | None, prose: str, denials: list | None = None,
                 block: str | None = DEFAULT_BLOCK, prior_blocks: int = 0,
                 posts_block: bool = True, block_carries_nonce: bool = False,
                 after_blocks: tuple[str, ...] = ()):
        self.record = record
        self.prose = prose
        self.denials = denials if denials is not None else []
        self.block = block
        # DEFAULT FALSE, WHICH IS THE ARCHIVE'S SHAPE. Every block posted before
        # Phase 4 carries no `run_id:`, so the default exercises the POSITIONAL
        # fallback and the nonce path is opted into by the tests that are about
        # it. Flipping the default would make every existing test silently
        # exercise the new path and leave the fallback — the one that runs on
        # every mid-thread PR at merge — with no coverage at all.
        self.block_carries_nonce = block_carries_nonce
        # Blocks that land on the thread AFTER this pass's own — the race the
        # run nonce closes. A third party posting a fenced `pr_review:` example
        # (a reflection, a brief quoting the wire format) between the child's
        # comment and the parent's read is not a pass, and positional selection
        # cannot tell the difference.
        self.after_blocks = after_blocks
        self.invocation_id: str | None = None
        # THE THREAD IS STATEFUL, and modelling that is the point. The invariant
        # asks whether THIS pass posted a block, so a fake returning one constant
        # count could not express "pass 2 ran and posted nothing" — which is the
        # case the invariant exists to catch and the case it used to pass.
        self.prior_blocks = prior_blocks
        self.posts_block = posts_block
        self.ran = False

    def install(self, monkeypatch, tmp_path: Path):
        from modules.assistant.review_pr import review_pr_activities as act
        from modules.assistant.review_pr import review_pr_workflow as wf

        monkeypatch.setattr(act, "fetch_pr", lambda *a, **k: {"headRefName": "build/x"})
        monkeypatch.setattr(act, "count_prior_passes", lambda *a, **k: self._blocks())
        monkeypatch.setattr(act, "load_shared_block", lambda *a, **k: "guard")
        monkeypatch.setattr(wf._shared, "worktree_add",
                            lambda *a, **k: tmp_path / "pr-tree")
        monkeypatch.setattr(wf._shared, "claude_log_path",
                            lambda *a, **k: tmp_path / "run.jsonl")
        # The identity half of rule R5b. Faked at its own boundary — it is a
        # `gh repo view` — so the comparison itself stays code under test.
        monkeypatch.setattr(wf._shared, "repo_slug", lambda *a, **k: REPO_SLUG)

        def _run(prompt, *a, **k):
            # The nonce is issued by the parent and reaches the child ONLY
            # through the prompt, so capturing it here is the same path the
            # real child reads it on. `prompt` is the REAL disposition.md
            # rendered, so this also proves `${RUN_ID}` is in the shipped prompt
            # and gets substituted — not just that the helper accepts a kwarg.
            self.invocation_id = _nonce_in(prompt)
            self.ran = True
            return ""

        monkeypatch.setattr(act, "run_disposition", _run)
        # `thread_snapshot` is the ONE `gh` read the workflow makes for the
        # thread; the two projections above it are patched as well so a test
        # calling either directly still sees this fake's thread. The count and
        # the window stay independently settable — that is what lets the fake
        # express "pass 2 ran and posted nothing", the case the invariant exists
        # to catch.
        monkeypatch.setattr(act, "pr_review_blocks", lambda *a, **k: self._window())
        monkeypatch.setattr(act, "thread_snapshot",
                            lambda *a, **k: (self._blocks(), self._window()))
        monkeypatch.setattr(wf._shared, "result_event",
                            lambda *a, **k: self._envelope())
        monkeypatch.setattr(wf._shared, "assistant_text", lambda *a, **k: self.prose)
        return wf

    def _blocks(self) -> int:
        """Blocks on the thread now: one more once this pass posted its own."""
        return self.prior_blocks + (1 if self.ran and self.posts_block else 0)

    def _window(self) -> list[str]:
        """The thread's block window, one entry per pass.

        The nonce is stamped HERE and not in `__init__` because the parent
        issues it at run time — the same reason `_run` captures it out of the
        rendered prompt rather than being handed it.
        """
        if self.block is None:
            return list(self.after_blocks)
        block = self.block
        if self.block_carries_nonce and self.invocation_id:
            block = block.replace("pr_review:\n", f"pr_review:\n  run_id: {self.invocation_id}\n", 1)
        return [block] + list(self.after_blocks)

    def _envelope(self) -> dict:
        event = {"type": "result", "subtype": "success",
                 "permission_denials": self.denials}
        if self.record is not None:
            record = dict(self.record)
            if record.get("run_id") == "@ISSUED@":
                record["run_id"] = self.invocation_id
            event["structured_output"] = record
        return event


def _no_sleep(monkeypatch) -> list[float]:
    """Replace the backoff with a recorder, so the retries are observable."""
    from modules.assistant.review_pr import review_pr_workflow as wf
    slept: list[float] = []
    monkeypatch.setattr(wf.time, "sleep", slept.append)
    return slept


def _with_comments(monkeypatch, bodies: list[str]):
    """Replace `gh` at its own boundary; everything above it is the code under test."""
    from modules.assistant.review_pr import review_pr_activities as act
    monkeypatch.setattr(
        act._shared, "gh",
        lambda *a, **k: json.dumps({"comments": [{"body": b} for b in bodies]}),
    )
    return act
