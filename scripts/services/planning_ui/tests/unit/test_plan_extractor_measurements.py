"""The structural measurements — specifically, what the broken-link sweep counts.

Only this row's own predicate is asserted here — the fence mask, the inline
code-span mask, and what an unterminated fence costs. A figure's VALUE on a
real corpus is that corpus's to assert, in its own live-corpus tier; a fixture
corpus can only assert the row's shape, and it does.
"""

from __future__ import annotations

from pathlib import Path

from planning_ui.plan_extractor.measurements import count_broken_relative_links
from planning_ui.plan_extractor.model import UNPARSED_LINE, Collector


#: The synthetic host path the scratch corpora below declare. A link written
#: against it is host-absolute BY THE CORPUS'S OWN DECLARATION, which is the
#: only sense in which any link is.
HOST = "/srv/example/planning"


def corpus(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "corpus"
    root.mkdir(parents=True, exist_ok=True)
    (root / "corpus.toml").write_text(f'[corpus]\ncanonical_checkout = "{HOST}"\n')
    for rel, text in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


def test_a_link_inside_a_fence_is_a_placeholder_and_is_not_counted(tmp_path: Path):
    """The corpus documents the convention it is measured by.

    ``standards/documentation/documentation_standard.md`` shows the binding
    cross-reference form as ``[Standard Name §N](relative/path/to/standard.md)``
    inside a fence, twice. Counted literally, the corpus's own documentation
    inflates the figure — 9 of 114 occurrences on 2026-09-06 — and the row exists
    to reproduce a real link-hygiene number, not to count its own examples.

    This extends the ``S-4ukckstc`` ruling (a marker inside a fence *"is prose
    about the convention"*) from markers to links. **The recorded method text is
    amended in lockstep by hand in ``MDC-Master-Planning#230``**; without that
    half, this change would make the tool's stated method false.
    """
    root = corpus(
        tmp_path,
        {
            "standards/example.md": (
                "# Example\n\n"
                "The canonical form:\n\n"
                "```\n"
                "[Standard Name §N](relative/path/to/standard.md)\n"
                "```\n\n"
                "And a genuinely broken reference: [Gone](./gone.md)\n"
            )
        },
    )
    assert count_broken_relative_links(root) == (1, 1)


def test_a_real_link_after_a_closed_fence_is_still_counted(tmp_path: Path):
    """The negative half — the mask must end where the fence does.

    A mask that leaks past its closing delimiter silently deletes the rest of
    the file from the sweep, which looks exactly like a clean corpus.
    """
    root = corpus(
        tmp_path,
        {
            "standards/example.md": (
                "```\n[Placeholder](relative/path/to/standard.md)\n```\n\n"
                "[One](./one.md) and [Two](./two.md)\n"
            )
        },
    )
    assert count_broken_relative_links(root) == (2, 2)


def test_an_unterminated_fence_masks_the_remainder_and_says_what_it_swallowed(
    tmp_path: Path,
):
    """The stated direction of error, asserted so it is a decision and not a bug.

    An unterminated fence has no honest end, so the sweep under-counts rather
    than counting placeholders as references — **and reports that it did**.

    This test used to justify the silence by pointing at the dependency
    contract's own unterminated-fence finding. That claim was false, and this
    fixture is why: the sweep reads every markdown file under the root, the
    dependency contract reads only ``roadmap.md``, and ``standards/example.md``
    is not one. All 4 files carrying an unterminated fence on the live corpus
    are non-roadmaps, so the borrowed report covered none of them.
    """
    root = corpus(
        tmp_path,
        {"standards/example.md": "```\n[Placeholder](x.md)\n\n[Also swallowed](y.md)\n"},
    )
    collector = Collector()
    assert count_broken_relative_links(root, collector) == (0, 0)

    fence_findings = [f for f in collector.findings if f.code == UNPARSED_LINE]
    assert len(fence_findings) == 1
    finding = fence_findings[0]
    assert finding.provenance.file == "standards/example.md"
    assert finding.provenance.line == 1  # the fence that never closed
    assert "2 link(s)" in finding.summary


def test_a_balanced_fence_reports_nothing_at_all(tmp_path: Path):
    """The other half — the report fires on the condition, not on every fence.

    A row that emitted a finding for every fenced block would bury the four
    files that actually swallow something under several hundred that do not.
    """
    root = corpus(
        tmp_path,
        {"standards/example.md": "```\n[Placeholder](x.md)\n```\n\n[Gone](./gone.md)\n"},
    )
    collector = Collector()
    assert count_broken_relative_links(root, collector) == (1, 1)
    assert [f for f in collector.findings if f.code == UNPARSED_LINE] == []


def test_an_unterminated_fence_over_nothing_countable_stays_quiet(tmp_path: Path):
    """The condition alone is not the finding — what it COST is.

    4 of 400 files on the live corpus open a fence the tool's own delimiter
    never closes, and none of the 4 swallows a link that resolves to nothing.
    Reporting the fence rather than the loss would put 4 permanently-unactionable
    rows in the section the phase doc calls the spine.
    """
    root = corpus(
        tmp_path,
        {
            "standards/example.md": (
                "[Real](./real.md)\n\n```\njust code, no links\nmore code\n"
            ),
            "standards/real.md": "# Real\n",
        },
    )
    collector = Collector()
    assert count_broken_relative_links(root, collector) == (0, 0)
    assert [f for f in collector.findings if f.code == UNPARSED_LINE] == []


def test_the_same_broken_target_in_two_files_is_two_occurrences_and_two_pairs(
    tmp_path: Path,
):
    """Uniqueness is per ``(file, target)`` — the recorded method's own wording."""
    root = corpus(
        tmp_path,
        {
            "standards/a.md": "[Gone](./gone.md) and again [Gone](./gone.md)\n",
            "standards/b.md": "[Gone](./gone.md)\n",
        },
    )
    assert count_broken_relative_links(root) == (2, 3)


def test_a_link_inside_an_inline_code_span_is_a_placeholder_too(tmp_path: Path):
    """The other half of the ruling the companion PR's method text states.

    ``S-4ukckstc`` covers a fenced block **and an inline code span** in one
    sentence, and ``MDC-Master-Planning#230``'s amended row reads *"links inside
    fenced code blocks and inline code spans are EXCLUDED"*. Masking only fences
    left the tool under-excluding by 13 occurrences against its own recorded
    method — the same code/method divergence the mask was added to remove,
    pointing the other way.
    """
    root = corpus(
        tmp_path,
        {
            "standards/example.md": (
                "Write it as `[Standard Name §N](relative/path/to/standard.md)`.\n\n"
                "And a genuinely broken reference: [Gone](./gone.md)\n"
            )
        },
    )
    assert count_broken_relative_links(root) == (1, 1)


def test_a_stray_backtick_does_not_blank_the_rest_of_the_document(tmp_path: Path):
    """The span mask is applied PER LINE, and that is load-bearing.

    ``CODE_SPAN_RE`` is ``DOTALL``. Run over a whole document, one unmatched
    backtick pairs with the next one several pages away and blanks every link
    between them — a silent drop arrived at while removing one. Masking line by
    line is the scope ``roadmaps.py`` already uses, so both readers of a line
    agree about it.
    """
    root = corpus(
        tmp_path,
        {
            "standards/example.md": (
                "A stray ` backtick opens nothing.\n\n"
                "[One](./one.md)\n\n"
                "Another stray ` here.\n\n"
                "[Two](./two.md)\n"
            )
        },
    )
    assert count_broken_relative_links(root) == (2, 2)


# ---------------------------------------------------------------------------
# Phase 6 · host-absolute links, reported per file for their owner to fix
# ---------------------------------------------------------------------------
def _host_absolute_findings(root: Path) -> list:
    from planning_ui.plan_extractor.model import LINK_HOST_ABSOLUTE

    collector = Collector()
    count_broken_relative_links(root, collector)
    return [f for f in collector.findings if f.code == LINK_HOST_ABSOLUTE]


def test_a_host_absolute_link_is_a_named_finding_with_every_line(tmp_path: Path):
    """One finding per file; every line named; the relative form stated.

    Per file rather than per link because enumerated per link the live report
    was 617 KiB and GitHub would not render it. Nothing is dropped: the line
    list is the whole population for that file.
    """
    root = corpus(
        tmp_path,
        {
            "standards/x.md": "# X\n",
            "development/common/widget/roadmap.md": (
                "# Widget\n\n"
                "See [X](/srv/example/planning/standards/x.md#section).\n"
                "\n"
                "Relative and fine: [X](../../../standards/x.md)\n"
                "\n"
                "Also [X again](/srv/example/planning/standards/x.md)\n"
            ),
        },
    )
    findings = _host_absolute_findings(root)
    assert len(findings) == 1, findings
    finding = findings[0]
    assert finding.provenance.file == "development/common/widget/roadmap.md"
    assert finding.provenance.line == 3
    assert "2 link(s)" in finding.summary
    assert "L3, L7" in finding.summary
    # The remedy: what the FIRST link would be, written relatively, anchor kept.
    assert "`../../../standards/x.md#section`" in finding.expected


def test_a_host_absolute_link_that_resolves_is_not_also_a_broken_link(tmp_path: Path):
    """The two classes are reported separately: the resolver reads through the
    prefix, so the graph keeps the edge and the broken-link row does not count
    it. Before the fix this link was a broken pair from every checkout but one."""
    root = corpus(
        tmp_path,
        {
            "standards/x.md": "# X\n",
            "development/a.md": "[X](/srv/example/planning/standards/x.md)\n",
        },
    )
    assert count_broken_relative_links(root) == (0, 0)
    assert len(_host_absolute_findings(root)) == 1


def test_a_host_absolute_link_inside_a_code_span_or_fence_is_not_reported(tmp_path: Path):
    """The same mask as the broken-link row: prose ABOUT the path is not a link."""
    root = corpus(
        tmp_path,
        {
            "development/a.md": (
                "Write `[X](/srv/example/planning/standards/x.md)` nowhere.\n"
                "```\n"
                "[X](/srv/example/planning/standards/x.md)\n"
                "```\n"
            ),
        },
    )
    assert _host_absolute_findings(root) == []


def test_a_link_into_a_sibling_repo_is_not_host_absolute_here(tmp_path: Path):
    """`/srv/example/CLAUDE.md` names a file this repository does not hold.
    Stripping the prefix would invent a repo-relative path; it stays a broken
    link, which it is from every checkout alike."""
    root = corpus(
        tmp_path,
        {"development/a.md": "[W](/srv/example/CLAUDE.md)\n"},
    )
    assert _host_absolute_findings(root) == []
    assert count_broken_relative_links(root) == (1, 1)
