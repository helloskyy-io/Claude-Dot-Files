"""Fixtures for the corpus viewer's tests.

Placed here per Testing Standard § Shared fixtures — pytest's tree-walking
conftest model makes these available to every test below without per-file
duplication.
"""

from __future__ import annotations

from pathlib import Path

import pytest

#: The deliberately-malformed miniature corpus. Fixtures rather than live
#: corpus files, precisely because the corpus must not be damaged to test the
#: tool that reads it.
FIXTURE_CORPUS = Path(__file__).resolve().parent / "fixtures" / "corpus"

#: The live corpus is THIS REPOSITORY, and that is the whole point of the move.
#:
#: This used to resolve three ways — an environment variable, an in-pod mount
#: at ``/app/master-planning``, and a sibling checkout — and to SKIP loudly
#: when none of them existed. That machinery was correct while the tool lived
#: in `example-app`, where the corpus was a foreign repo that might genuinely
#: be absent: a standing assertion over a sibling working tree would have made
#: that repo's suite depend on this checkout being present and in a particular
#: state, which the Testing Standard names as breakage.
#:
#: `repo_layout.md` §1.1 rule 1 dissolved it — *"its only input is that
#: repository's own corpus."* The corpus cannot be missing, because the test
#: file asking for it is committed inside it. So the resolution is one line and
#: the drift checks are unconditional rather than skippable.
LIVE_CORPUS = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def fixture_corpus() -> Path:
    return FIXTURE_CORPUS


@pytest.fixture(scope="session")
def live_corpus() -> Path:
    return LIVE_CORPUS


@pytest.fixture(scope="session")
def live_result(live_corpus):
    """One derivation over the live corpus, shared by the read-only checks.

    The census walks every markdown file in the repo, so re-deriving per test
    turns a ~1s suite into a ~15s one for no additional coverage. Tests that
    genuinely need two derivations — the run-twice determinism check — call
    ``extract`` themselves.
    """
    from planning_ui.plan_extractor import extract

    return extract(live_corpus)
