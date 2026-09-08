"""The header audit, driven on fixtures that discriminate rather than on the corpus.

CI depends on this check, and a check that cannot fail is worse than none — it reports a
corpus clean forever. Each predicate below is exercised on a case that must fire AND one
that must not.

THE THREE DISTINCTIONS THAT CARRY THE WEIGHT, each of which would silently ruin the audit:

  * A `**Read when:**` written INSIDE a section is not a header. A substring search over the
    file would count it and report a standard conformant that has no header at all.
  * A VENDORED standard's header is its OWNER's to write. Mixing mirrors into this repo's
    worklist hands an operator findings they are forbidden to act on — measured: MDC's audit
    reports four such files, and all four are ours.
  * A retired file is NOT filtered out. MDC carries two `OLD_*` standards that should be
    deleted; skipping them would report the corpus clean while a session could still read
    them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import standards_index as si

HEAD = ("**Binding scope:** any chart under `deployments/`\n"
        "**Read when:** writing a chart\n"
        "**Breaking it looks like:** an image tag pinned to `latest`\n")


def _std(root: Path, rel: str, body: str) -> Path:
    p = root / "standards" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def test_a_complete_header_is_READ(tmp_path: Path) -> None:
    p = _std(tmp_path, "a/x.md", f"# X\n\n{HEAD}\n## Body\n")
    s = si.read_standard(p)
    assert s.missing == []
    assert s.fields["Read when"].strip() == "writing a chart"


@pytest.mark.parametrize("drop", si.REQUIRED)
def test_EACH_required_line_is_reported_when_absent(tmp_path: Path, drop: str) -> None:
    head = "".join(l + "\n" for l in HEAD.splitlines() if not l.startswith(f"**{drop}:**"))
    p = _std(tmp_path, "a/x.md", f"# X\n\n{head}\n## Body\n")
    assert si.read_standard(p).missing == [drop]


def test_A_FIELD_INSIDE_A_SECTION_IS_NOT_A_HEADER(tmp_path: Path) -> None:
    """The distinction between a parsed contract and a substring search.

    The contract puts the header above the first `##`. A `Read when:` written in the body
    is prose about when to read something, and counting it would report a standard with no
    header at all as conformant.
    """
    p = _std(tmp_path, "a/x.md",
             "# X\n\n**Binding scope:** everywhere\n\n"
             "## Guidance\n\n**Read when:** you are curious\n"
             "**Breaking it looks like:** nothing\n")
    missing = si.read_standard(p).missing
    assert "Read when" in missing and "Breaking it looks like" in missing
    assert "Binding scope" not in missing


def test_A_VENDORED_STANDARD_IS_NOT_THIS_REPOS_WORK(tmp_path: Path) -> None:
    _std(tmp_path, "a/mine.md", "# Mine\n\n## Body\n")
    _std(tmp_path, "b/theirs.md",
         "<!-- VENDORED — DO NOT EDIT LOCALLY -->\n> *Vendored from `x/y`*\n\n# Theirs\n\n## Body\n")
    items = si.standards_in(tmp_path)
    owned = [s for s in items if not s.vendored]
    mirrors = [s for s in items if s.vendored]
    assert [s.path.name for s in owned] == ["mine.md"]
    assert [s.path.name for s in mirrors] == ["theirs.md"]
    assert mirrors[0].missing, "a mirror still HAS the gap — it is just not ours to close"


def test_A_RETIRED_FILE_IS_NOT_FILTERED_AWAY(tmp_path: Path) -> None:
    """It surfaces as a finding; DELETING it is the operator's call, not this script's."""
    _std(tmp_path, "django/OLD_Thing.md", "# Old\n\n## Body\n")
    assert [s.path.name for s in si.standards_in(tmp_path)] == ["OLD_Thing.md"]


def test_A_README_IS_NOT_A_STANDARD(tmp_path: Path) -> None:
    _std(tmp_path, "a/README.md", "# Readme\n")
    _std(tmp_path, "a/real.md", f"# R\n\n{HEAD}\n## B\n")
    assert [s.path.name for s in si.standards_in(tmp_path)] == ["real.md"]


def test_AN_UNINDEXED_STANDARD_IS_UNREACHABLE(tmp_path: Path) -> None:
    _std(tmp_path, "a/listed.md", f"# L\n\n{HEAD}\n## B\n")
    _std(tmp_path, "a/orphan.md", f"# O\n\n{HEAD}\n## B\n")
    (tmp_path / "CLAUDE.md").write_text(
        "# Repo\n\n- [Listed](standards/a/listed.md) — **read when** ever\n", encoding="utf-8")
    items = si.standards_in(tmp_path)
    assert [s.path.name for s in si.unindexed(tmp_path, items)] == ["orphan.md"]


def test_NO_CLAUDE_MD_REPORTS_NOTHING_RATHER_THAN_EVERYTHING(tmp_path: Path) -> None:
    """A repo with no index has no unindexed-standard finding to make.

    Reporting all of them would bury the header findings under noise in exactly the repos
    least likely to have an index yet.
    """
    _std(tmp_path, "a/x.md", f"# X\n\n{HEAD}\n## B\n")
    assert si.unindexed(tmp_path, si.standards_in(tmp_path)) == []


def test_THE_EXIT_CODE_ONLY_FAILS_UNDER_CHECK(tmp_path: Path, capsys) -> None:
    _std(tmp_path, "a/x.md", "# X\n\n## B\n")
    assert si.main(["--repo-root", str(tmp_path)]) == 0
    assert si.main(["--repo-root", str(tmp_path), "--check"]) == 1
    out = capsys.readouterr().out
    assert "MISSING HEADER LINES" in out


def test_A_CLEAN_CORPUS_PASSES_CHECK(tmp_path: Path) -> None:
    _std(tmp_path, "a/x.md", f"# X\n\n{HEAD}\n## B\n")
    (tmp_path / "CLAUDE.md").write_text("- [X](standards/a/x.md)\n", encoding="utf-8")
    assert si.main(["--repo-root", str(tmp_path), "--check"]) == 0


def test_AN_EMPTY_CORPUS_IS_A_REFUSAL_NOT_A_PASS(tmp_path: Path) -> None:
    """Exit 2, never 0: a corpus this cannot find is not a corpus with no findings."""
    (tmp_path / "standards").mkdir()
    assert si.main(["--repo-root", str(tmp_path), "--check"]) == 2
