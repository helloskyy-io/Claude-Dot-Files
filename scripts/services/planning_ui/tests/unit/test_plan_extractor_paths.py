"""Unit tests for path resolution confined to the checkout root.

A resolved path that escapes the root is reported as a finding and **never
opened**. Today the exposure is near-zero; it stops being near-zero the moment
the drift gate gets a CI home, because a pull-request-authored link becomes
untrusted input to a path-reading process.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from planning_ui.plan_extractor.safe_paths import (
    PathEscape,
    is_external,
    is_host_absolute,
    resolve_within_root,
    split_anchor,
)


#: A SYNTHETIC canonical host path. These are pure-text resolver tests, but
#: the host-absolute prefix is now the corpus's own declaration, so the root
#: they name must carry a `corpus.toml` saying so — and must NOT be a path
#: that happens to exist on one developer's machine, or the tests pass there
#: by accident and fail on every runner.
HOST = "/srv/example/planning"


@pytest.fixture(scope="module")
def ROOT(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("corpus")
    (root / "corpus.toml").write_text(f'[corpus]\ncanonical_checkout = "{HOST}"\n')
    return root


def test_a_relative_link_resolves_against_the_source_files_directory(ROOT):
    assert (
        resolve_within_root(ROOT, "development/common/planning_ui/roadmap.md", "phase1_x.md")
        == "development/common/planning_ui/phase1_x.md"
    )
    assert (
        resolve_within_root(ROOT, "development/common/planning_ui/roadmap.md", "../../sprints.md")
        == "development/sprints.md"
    )


def test_a_dot_dot_chain_that_leaves_the_root_raises(ROOT):
    """The escape the module exists for."""
    with pytest.raises(PathEscape):
        resolve_within_root(
            ROOT, "development/common/planning_ui/roadmap.md", "../../../../etc/passwd"
        )


def test_a_sibling_repo_link_is_an_escape_not_a_silent_skip(ROOT):
    """The corpus really carries one of these (service/monitoring/roadmap.md).

    Silently skipping it would leave no trace, which is the file-layer version of
    the never-silently-drop failure.
    """
    with pytest.raises(PathEscape):
        resolve_within_root(
            ROOT, "development/service/monitoring/roadmap.md", "../../../../sibling/docs/x.md"
        )


@pytest.mark.parametrize("where", ["canonical", "runner", "worktree"])
def test_a_host_absolute_link_resolves_the_same_from_any_checkout_location(where, tmp_path):
    """A corpus may link its standards by a host path in thousands of places.
    The answer must depend on what the corpus DECLARES, never on where this
    checkout happens to sit — a derivation that differed by checkout location
    could never run on a runner. Three checkouts of one corpus, three
    locations, one answer.
    """
    root = tmp_path / where
    root.mkdir()
    (root / "corpus.toml").write_text(f'[corpus]\ncanonical_checkout = "{HOST}"\n')
    assert (
        resolve_within_root(
            root, "development/x/roadmap.md",
            "/srv/example/planning/standards/architecture/architectural_standard.md",
        )
        == "standards/architecture/architectural_standard.md"
    )


def test_a_host_absolute_link_is_classified_from_its_text_alone(ROOT):
    assert is_host_absolute("/srv/example/planning/standards/x.md", ROOT) is True
    assert is_host_absolute("/srv/example/planning", ROOT) is True
    # Another repo under the same convention is NOT this checkout: stripping the
    # prefix would invent a repo-relative path for a file that is not here.
    assert is_host_absolute("/srv/example/CLAUDE.md", ROOT) is False
    assert is_host_absolute("/srv/example/planning-old/x.md", ROOT) is False
    assert is_host_absolute("standards/x.md", ROOT) is False


def test_a_dot_dot_chain_inside_a_host_absolute_link_is_still_an_escape(ROOT):
    with pytest.raises(PathEscape):
        resolve_within_root(
            ROOT, "development/x/roadmap.md",
            "/srv/example/planning/../sibling/docs/x.md",
        )


def test_an_absolute_path_outside_the_root_falls_back_to_root_relative(ROOT):
    """Two readings exist in the corpus and both are CHECKED, never guessed.

    A `/standards/...` link is root-relative in some documents and a host path in
    others. Resolving it as root-relative means the existence check decides,
    rather than the tool assuming.
    """
    assert (
        resolve_within_root(ROOT, "development/x/roadmap.md", "/standards/foo.md")
        == "standards/foo.md"
    )


def test_url_encoded_spaces_are_decoded_before_resolution(ROOT):
    """`%20` appears in real corpus links; not decoding makes a live file unresolvable."""
    assert (
        resolve_within_root(ROOT, "development/x/roadmap.md", "docs/05.%20Internal/a.md")
        == "development/x/docs/05. Internal/a.md"
    )


@pytest.mark.parametrize(
    "target,external",
    [
        ("https://example.com", True),
        ("http://example.com", True),
        ("mailto:a@b.c", True),
        ("#an-anchor", True),
        ("", True),
        ("./phase1_x.md", False),
        ("../sprints.md", False),
        # Deliberately NOT external: an absolute path is resolved and CHECKED, so
        # an escape is reported rather than skipped without a trace.
        ("/srv/example/planning/standards/x.md", False),
    ],
)
def test_is_external_marks_only_non_filesystem_targets(target, external):
    assert is_external(target) is external


def test_split_anchor_separates_the_fragment():
    assert split_anchor("roadmap.md#the-finding") == ("roadmap.md", "the-finding")
    assert split_anchor("roadmap.md") == ("roadmap.md", "")
    assert split_anchor("#bare") == ("", "bare")


def test_a_file_scheme_url_is_external_not_a_relative_path():
    """`file:///opt/...` is a URL scheme, not a path relative to the source file.

    Treating it as relative resolves it against the source file's DIRECTORY,
    finds nothing, and counts the miss in a measurement whose stated method is
    "relative markdown links" — inflating a figure the tool is required to
    reproduce by method. Three such links exist on `main` today.
    """
    assert is_external("file:///srv/example/tooling/config/rules/x.md") is True
    assert is_external("FILE://Some/Where.md") is True
    # And the discriminator: a genuine absolute filesystem path is still checked,
    # so an escape is reported rather than silently skipped.
    assert is_external("/srv/example/planning/standards/x.md") is False
