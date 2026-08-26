"""INTAKE — the exemption is conditional, so the conditions get tests.

`Tracked Items Standard` §5.0 exempts a GitHub issue used purely as an intake
from §5's retirement, and the exemption is **conditional**: a named harvest
cadence, never read as a store, and it empties. *"An intake with no harvest is a
second store, and that is a §8 violation — not a grey area."*

So the tests here are not only "does the parser work". They pin the properties
that keep the exemption legal, and the one ordering decision that decides
whether a finding can be lost.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from modules.assistant.tracked import intake as own
from modules.assistant.tracked import tracked_items as ti


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    for store in ti.STORES.values():
        (tmp_path / store.name).mkdir(parents=True)
    return tmp_path


# --------------------------------------------------------------- round trip

def test_what_a_filer_writes_is_what_the_harvest_reads() -> None:
    """THE INTAKE BODY *IS* THE ITEM, minus the id the harvest mints.

    There is deliberately no transport format to keep in step with §3 — a change
    to the core changes both ends at once. This asserts the two halves are one
    format rather than two that happen to agree today.
    """
    text = own.render_intake(
        ti.STORES["standards"],
        title="ignored here — the ISSUE title is the item title",
        body="The argument.", filed_by="review-pr",
        extras={"target": "docs/standards/workflow-scripts.md", "anchor": "§ Composition"})
    store, fields, body = own.parse_intake(text)
    assert store.name == "standards"
    assert fields == {"status": "open", "filed_by": "review-pr",
                      "target": "docs/standards/workflow-scripts.md",
                      "anchor": "§ Composition"}
    assert body == "The argument."


@pytest.mark.parametrize("store", ["issues", "candidates", "standards"])
def test_every_store_a_MACHINE_may_file_into_round_trips(store: str) -> None:
    """The three §1.2 permits. `operations/` is absent on purpose — see below."""
    text = own.render_intake(ti.STORES[store], title="t", body="b",
                             filed_by="review-pr")
    parsed, _, _ = own.parse_intake(text)
    assert parsed.name == store


# ------------------------------------------------------------- loud failure

@pytest.mark.parametrize("body,expect", [
    ("no frontmatter at all", "no frontmatter"),
    ("---\nstore: nonesuch\n---\n\nbody", "not one of"),
    ("---\nstore\n---\n\nbody", "not `key: value`"),
    ("---\nstatus: open\n---\n\nbody", "(missing)"),
])
def test_a_malformed_intake_fails_LOUDLY_and_by_name(body: str, expect: str) -> None:
    """A SKIPPED INTAKE IS A LOST FINDING.

    The finding has already left the run that produced it — there is no second
    copy anywhere. So a parse failure must name what is wrong, and the harvest
    must leave the issue OPEN rather than swallow it.
    """
    with pytest.raises(own.IntakeError, match=expect):
        own.parse_intake(body)


def test_an_autonomous_filer_CANNOT_set_an_operator_only_field() -> None:
    """§4 and §1.2 together: the intake is a machine surface, so the two
    operator-only fields are refused at the door as well as in the writer.

    Enforced in BOTH places deliberately. The writer's refusal protects a direct
    caller; this one protects the path a model actually takes, where the field
    would arrive as text in an issue body that no Python caller ever typed.
    """
    for store, field in (("operations", "ready"), ("standards", "ratification")):
        with pytest.raises(own.IntakeError, match="operator's alone"):
            own.parse_intake(f"---\nstore: {store}\n{field}: yes\n---\n\nbody")


# ------------------------------------------------------- the harvest itself

class _FakeGh:
    """Records `gh` calls so ORDER can be asserted, which is the point."""

    def __init__(self, issues: list[dict], fail_close: bool = False) -> None:
        self.issues = issues
        self.fail_close = fail_close
        self.calls: list[str] = []

    def __call__(self, *args: str, **kw) -> str:
        self.calls.append(args[1])
        if args[1] == "list":
            import json
            return json.dumps(self.issues)
        if args[1] == "close":
            if self.fail_close:
                raise own.IntakeError("close failed")
            self.issues = [i for i in self.issues
                           if str(i["number"]) != args[2]]
            return ""
        return ""


def _issue(number: int, store: str, title: str = "t") -> dict:
    return {"number": number, "title": title,
            "body": own.render_intake(ti.STORES[store], title=title,
                                      body="why it matters", filed_by="review-pr"),
            "createdAt": "2026-08-20T10:00:00Z"}


def test_harvest_files_the_item_and_then_EMPTIES_the_intake(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CONDITION 3: it empties. A harvest that files without closing builds the
    second store the exemption forbids."""
    gh = _FakeGh([_issue(1, "issues"), _issue(2, "candidates")])
    monkeypatch.setattr(own, "_gh", gh)

    moved, failed = own.harvest(root)

    assert failed == []
    assert len(moved) == 2
    assert gh.calls.count("close") == 2, "every harvested intake is closed"
    assert len(list((root / "issues").glob("*.md"))) == 1
    assert len(list((root / "candidates").glob("*.md"))) == 1


def test_the_item_is_WRITTEN_BEFORE_the_intake_is_closed(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """THE ORDERING DECISION, AND IT DECIDES WHETHER A FINDING CAN BE LOST.

    Write-then-close means a crash between the two leaves the item filed and the
    intake open — recoverable, and the next pass sees it. Close-then-write loses
    the finding outright with nothing to recover from. Asserted by making the
    close fail and checking the file survives.
    """
    gh = _FakeGh([_issue(7, "issues")], fail_close=True)
    monkeypatch.setattr(own, "_gh", gh)

    moved, failed = own.harvest(root)

    assert moved == [] and [n for n, _ in failed] == [7], (
        "a close failure is REPORTED, not raised — one bad intake must not "
        "abort the harvest of every other")
    assert len(list((root / "issues").glob("*.md"))) == 1, (
        "the item must exist even though closing failed — the other order "
        "would have lost the finding")


def test_re_harvesting_a_written_but_unclosed_intake_files_no_SECOND_copy(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Idempotence, keyed on the pointer the item itself carries.

    This is the recovery path for the crash the ordering above allows: the
    second pass must close the intake without duplicating the item.
    """
    gh = _FakeGh([_issue(7, "issues")], fail_close=True)
    monkeypatch.setattr(own, "_gh", gh)
    assert own.harvest(root)[1], "first pass must fail to close"

    gh.fail_close = False
    moved, failed = own.harvest(root)

    assert failed == []
    assert len(moved) == 1
    assert len(list((root / "issues").glob("*.md"))) == 1, "no second copy"


def test_a_malformed_intake_is_left_OPEN_and_reported(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A bad intake must not be closed. Closing it to tidy the queue loses the
    finding, which is the trade this refuses to make."""
    bad = {"number": 3, "title": "t", "body": "nothing parseable",
           "createdAt": "2026-08-20T10:00:00Z"}
    gh = _FakeGh([bad, _issue(4, "candidates")])
    monkeypatch.setattr(own, "_gh", gh)

    moved, failed = own.harvest(root)

    assert [n for n, _ in moved] == [4]
    assert [n for n, _ in failed] == [3]
    assert gh.calls.count("close") == 1, "the malformed one was NOT closed"


def test_harvest_order_is_FILING_order(root: Path,
                                       monkeypatch: pytest.MonkeyPatch) -> None:
    """Oldest first, so a queue that backs up drains in the order it filled."""
    a = _issue(9, "issues"); a["createdAt"] = "2026-08-22T10:00:00Z"
    b = _issue(8, "issues"); b["createdAt"] = "2026-08-19T10:00:00Z"
    monkeypatch.setattr(own, "_gh", _FakeGh([a, b]))

    moved, _ = own.harvest(root)
    assert [n for n, _ in moved] == [8, 9]


def test_the_harvested_item_keeps_the_INTAKE_date_not_the_harvest_date(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`filed:` records when the finding was MADE. A queue that backs up for a
    week must not restamp every item as filed today — recurrence and pruning
    both run off this date."""
    monkeypatch.setattr(own, "_gh", _FakeGh([_issue(5, "issues")]))
    own.harvest(root)
    path = next((root / "issues").glob("*.md"))
    fields, _ = ti.parse(path)
    assert fields["filed"] == "2026-08-20"


def test_the_closing_comment_points_AT_the_file(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CONDITION 2: the intake is never read as a store. A reader who follows
    the closed issue must land on the record, not be told it is the record."""
    captured: list[tuple[str, ...]] = []

    class _Gh(_FakeGh):
        def __call__(self, *args: str, **kw) -> str:
            captured.append(args)
            return super().__call__(*args, **kw)

    monkeypatch.setattr(own, "_gh", _Gh([_issue(6, "candidates")]))
    own.harvest(root)

    comment = next(a for a in captured if a[1] == "close")[-1]
    assert "candidates/C-" in comment and ".md" in comment
    assert "the file is the record" in comment.lower()
    # AND THE PATH IS REPO-RELATIVE. The first end-to-end run posted an ABSOLUTE
    # path into a public comment — it leaked the harvester's home directory and
    # resolved for nobody else. A reader following this comment must land on the
    # record, which is condition 2 of the exemption.
    assert not comment.split("`")[1].startswith("/"), (
        f"absolute path in a public comment: {comment.split('`')[1]}")
