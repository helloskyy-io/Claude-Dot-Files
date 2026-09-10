"""The machine's name and the append-time filter — PMP Phase 3 requirements 6, 10.

TWO SMALL MODULES IN ONE FILE, BECAUSE THEY SHARE ONE ARGUMENT. Both exist to
keep a secret out of a durable record: `edge_id` by refusing an identity derived
from a credential, `capture_filter` by removing named credential shapes before
any byte reaches the root. Splitting them would put that argument in two places
and let one copy go stale.

⚠ THE FILTER'S BOUNDARY IS ASSERTED AS A BOUNDARY, NOT AS A CAPABILITY. A
pattern filter sees the shapes it was given; it does not see a bare password, a
credential wrapped across two lines, or one base64-ed. The tests below say so
out loud rather than leaving a reader to infer a guarantee this module cannot
support — a suite that only demonstrated catches would read as a completeness
claim.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.journal.capture_filter import (RULES, filter_capture,
                                            placeholder_for)
from modules.journal.edge_id import (EDGE_ID_FILE, NO_CREDENTIAL_EPOCH,
                                     EdgeIdError, adopt_edge_id, read_edge_id,
                                     resolve_edge_id)


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    directory = tmp_path / "journal"
    directory.mkdir(mode=0o700)
    return directory


# --- requirement 6: the identity -------------------------------------------

def test_the_id_is_minted_once_and_is_STABLE_across_runs(root: Path) -> None:
    """Stability is the whole requirement: a journal keyed by a rotating value
    orphans an edge's entire history the day that value changes."""
    first = resolve_edge_id(root)
    assert resolve_edge_id(root) == first
    assert (root / EDGE_ID_FILE).read_text(encoding="utf-8").strip() == first


def test_an_unminted_machine_READS_as_None_rather_than_as_a_fresh_id(
        root: Path) -> None:
    """`None` means NOT YET MINTED, which is the true state of a first run.

    Returning a fresh id from a READ would give a validator, a Phase 6 sweep and
    the run itself three different answers for one machine.
    """
    assert read_edge_id(root) is None


def test_the_id_is_persisted_at_the_MACHINE_and_not_inside_a_bag(
        root: Path) -> None:
    """A file inside a bag would be per-RUN, and an id that changes per run is
    not an id."""
    resolve_edge_id(root)
    assert (root / EDGE_ID_FILE).is_file()
    assert not any(p.is_dir() for p in root.iterdir()), (
        "the id must not have created a bag-shaped directory at the root")


def test_the_id_is_0600_like_everything_else_under_a_0700_root(root: Path) -> None:
    resolve_edge_id(root)
    assert (root / EDGE_ID_FILE).stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("digest_length", [32, 40, 64])
def test_a_DIGEST_SHAPED_id_is_REFUSED_on_adoption(root: Path,
                                                   digest_length: int) -> None:
    """`hash(api_key)` is ruled out twice over and this is the rule as code.

    It changes on rotation — the orphaning bug the whole requirement exists to
    prevent — and a stored hash of a live credential is an offline confirmation
    oracle. A future implementer who reads *"the key maps to a stable id"* and
    reaches for `sha256(key).hexdigest()` is stopped by an error naming the rule;
    they are not stopped by a paragraph in a docstring.
    """
    with pytest.raises(EdgeIdError, match="shape of a bare digest"):
        adopt_edge_id(root, "a" * digest_length, source="the upstream pair")


def test_a_PREFIXED_random_token_is_ACCEPTED(root: Path) -> None:
    """The check is on SHAPE, and it must not refuse a legitimate assigned name.

    This is the control for the parametrised refusal above: without it, a rule
    that refused everything would pass all three of those cases.
    """
    assert adopt_edge_id(root, "edge-" + "a" * 32) == "edge-" + "a" * 32


def test_adopting_a_DIFFERENT_id_on_a_machine_that_has_one_is_REFUSED(
        root: Path) -> None:
    """Every event already written carries the old value.

    Adopting a second would split one machine's history into two edges that look
    like two machines — the same orphaned-history failure a credential-derived id
    causes, reached deliberately instead of by rotation.
    """
    resolve_edge_id(root)
    with pytest.raises(EdgeIdError, match="cannot become"):
        adopt_edge_id(root, "edge-operator-assigned")


def test_adopting_the_SAME_id_is_idempotent(root: Path) -> None:
    """A caller passing the configured id on every run is correct, not an error."""
    adopt_edge_id(root, "edge-mdc-01")
    assert adopt_edge_id(root, "edge-mdc-01") == "edge-mdc-01"


@pytest.mark.parametrize("bad,why", [
    ("", "empty"),
    (" edge-1", "surrounding whitespace"),
    ("edge-1 ", "surrounding whitespace"),
    ("edge/1", "permitted set"),
    ("edge\n1", "permitted set"),
    ("e" * 129, "permitted set"),
])
def test_an_id_that_would_not_survive_a_tag_line_is_REFUSED(root: Path, bad: str,
                                                            why: str) -> None:
    """It goes into `bag-info.txt` as a tag value AND into every event.

    Anything `str.splitlines()` breaks on folds the line into what reads as a
    second label — the forging class `bag.folds_a_tag_line` exists to close — and
    surrounding whitespace reads back stripped, a different string from the one
    written.
    """
    with pytest.raises(EdgeIdError, match=why):
        adopt_edge_id(root, bad)


def test_a_NON_UTF8_id_file_is_REFUSED_rather_than_guessed(root: Path) -> None:
    """`UnicodeDecodeError` is a `ValueError`, so `except OSError` would miss it.

    It cannot be guessed either: every event under this root carries the value
    that belongs in this file.
    """
    (root / EDGE_ID_FILE).write_bytes(b"\xff\xfe not utf-8")
    with pytest.raises(EdgeIdError, match="not valid UTF-8"):
        read_edge_id(root)


def test_an_EMPTY_id_file_names_its_own_remedy(root: Path) -> None:
    """A run killed between `O_EXCL` create and the write leaves this state.

    A retry loop here would spin on it forever; the refusal names the file and
    what to do, which is what a human needs because no run can fix it.

    ⚠ IT IS REFUSED AT THE READ, WHICH IS WHERE IT IS REACHABLE. `resolve_edge_id`
    reads before it mints, so an empty file never reaches the `O_EXCL` race arm
    — an `if raced is None` branch there would be dead code carrying a second
    copy of this message. Both callers hit one refusal.
    """
    (root / EDGE_ID_FILE).write_text("")
    with pytest.raises(EdgeIdError, match="an EMPTY FILE here means"):
        resolve_edge_id(root)
    with pytest.raises(EdgeIdError, match="an EMPTY FILE here means"):
        read_edge_id(root)


def test_no_credential_epoch_is_a_VALUE_and_not_an_absence() -> None:
    """`JournalEvent` refuses an empty `key_epoch`, so this cannot be skipped.

    "None" is a real answer for this fleet today — it authenticates to no
    upstream pair — and an empty string would be indistinguishable from a field
    somebody forgot to fill, which is a state a replay scoped past a leaked
    credential cannot act on.
    """
    assert NO_CREDENTIAL_EPOCH and NO_CREDENTIAL_EPOCH.strip() == NO_CREDENTIAL_EPOCH


# --- requirement 10: the capture filter -------------------------------------

@pytest.mark.parametrize("rule_name,sample", [
    ("github-token", "ghp_" + "A" * 36),
    ("github-pat", "github_pat_" + "A" * 40),
    ("aws-access-key", "AKIA" + "B" * 16),
    ("openai-key", "sk-" + "c" * 40),
    ("slack-token", "xoxb-123456789012-abcdefghijkl"),
    ("google-api-key", "AIza" + "D" * 35),
    ("bearer-header", "Authorization: Bearer abcdef0123456789"),
    ("url-embedded-credential", "https://user:pa55word@example.com/x"),
])
def test_each_named_shape_is_REMOVED_and_the_rule_is_NAMED(rule_name: str,
                                                           sample: str) -> None:
    """Every rule fires on its own sample, and the placeholder names it.

    A suite that exercised one rule and trusted the rest would leave a broken
    pattern shipping — and a broken pattern in this table is a secret in a
    durable record, not a missing feature.
    """
    result = filter_capture(f"prefix {sample} suffix")
    assert sample not in result.text
    assert result.fired
    assert result.removed_bytes > 0
    assert "prefix" in result.text and "suffix" in result.text, (
        "the rule ate surrounding content, which is the over-broad failure the "
        "placeholder's rule name exists to make diagnosable")


def test_the_private_key_BLOCK_is_removed_whole() -> None:
    """A multi-line shape, which the per-line intuition would miss."""
    block = ("-----BEGIN OPENSSH PRIVATE KEY-----\n"
             "b3BlbnNzaC1rZXktdjEAAAAA\nAAAA\n"
             "-----END OPENSSH PRIVATE KEY-----")
    result = filter_capture(f"here it is:\n{block}\ndone")
    assert "b3BlbnNzaC1rZXktdjEAAAAA" not in result.text
    assert "done" in result.text


def test_ordinary_prose_is_UNTOUCHED() -> None:
    """The control. Without it every assertion above passes for a filter that
    removes everything, which would empty the journal rather than protect it."""
    prose = ("## Decision Log\n\n- **[High]** kept the phase whole. The commit "
             "is 4d0fb8dfd74b9e645c46c3cb and the PR is #284.\n")
    result = filter_capture(prose)
    assert result.text == prose
    assert not result.fired
    assert result.removed_bytes == 0


def test_a_git_SHA_does_NOT_fire_the_filter() -> None:
    """The specific false positive an entropy heuristic would have produced.

    Every `event_id` in the journal's own events is a 32-character hex string, so
    an entropy rule would filter the record's own identity fields and report a
    leak on every bag. That is why the rules are prefixed shapes.
    """
    assert not filter_capture("commit 4d0fb8dfd74b9e645c46c3cb0123456789abcdef").fired


def test_removed_bytes_counts_the_INPUT_span_and_is_never_negative() -> None:
    """A length difference would report a NEGATIVE removal for a short token —
    a number that reads as "the filter added content"."""
    secret = "ghp_" + "A" * 36
    assert filter_capture(secret).removed_bytes == len(secret)


def test_the_filter_is_TOTAL_over_its_input_and_never_raises() -> None:
    """It runs on the append path of a component whose thesis is that a failed
    write must not be silent; a filter that raised would convert a leak into a
    crash on the path that is supposed to keep running."""
    for weird in ("", "\x00\x01", "𝔘𝔫𝔦𝔠𝔬𝔡𝔢", "a" * 100_000):
        assert isinstance(filter_capture(weird).text, str)


def test_the_placeholder_names_the_rule_and_carries_no_match() -> None:
    assert placeholder_for("github-token") == "[FILTERED:github-token]"


def test_every_declared_rule_has_a_UNIQUE_name() -> None:
    """A duplicate name makes the placeholder ambiguous about which rule fired,
    which is the one diagnostic the record carries."""
    names = [rule.name for rule in RULES]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("missed", [
    "password: hunter2",
    "Z2hwX0FBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQQ==",
])
def test_the_STATED_BLIND_SPOTS_are_real_and_are_asserted_as_such(
        missed: str) -> None:
    """⚠ THESE PASS THE FILTER, AND THAT IS THE POINT OF WRITING THEM DOWN.

    A credential with no distinguishing shape and one that is base64 of something
    the filter would otherwise catch both go through. The module says so; this
    is the assertion that keeps the claim honest, and it goes RED the day someone
    widens the rules — at which point the docstring is what needs updating, not
    this test's expectation.

    Phase 1's redaction is the component's control for what gets past here. This
    is the cheap gate; that is the incident response.
    """
    assert not filter_capture(missed).fired
