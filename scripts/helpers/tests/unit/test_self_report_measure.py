"""The self-report and recurrence, measured (Self Improvement Phase 2): its three rates.

Built on FIXTURE journals and a FIXTURE planning corpus, for the reason
`test_journal_baseline.py` states: the live corpus moves with every dispatch,
and a count asserted against it is a count at one moment. The live figures are
taken once and recorded in the phase doc's § Runtime Verification.

Each property the phase doc makes checkable is asserted with the input that
would break it:

  * r1 — a finding is STATED only by what the producing runs wrote BEFORE the
         pass's own comment (a later reflection is the control's, not the
         rate's); a run that wrote nothing is EXCLUDED and counted, not NEW;
         a record whose bag has no harvest is read from the FORGE and says so;
  * r2 — a claim is corroborated by a tracked `count` >= 2 or a finding id two
         passes carried, and by nothing else; a fenced `pr_review:` block is
         not a reflection sentence;
  * r3 — recurrence is read per LINE, a watch-criterion is not an event, a
         `→ SHIPPED` amendment is not a recurrence, 90 days is the horizon,
         and the three groups sum to the population;
  * r6 — a hypothesis never enters the computed figure; a claim the sweep
         cannot quote verbatim is refused; a calibration link is checked for
         position and marker;
  * r5 — nothing in the fleet's prompts or triage rules ranks a finding by
         how strongly it was asserted (a guard over the live tree);
  * r4 — no path semantics above the two read interfaces.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_MEASURE = Path(__file__).resolve().parents[2] / "measure"
if str(_MEASURE) not in sys.path:
    sys.path.insert(0, str(_MEASURE))

import journal_evidence as je  # noqa: E402
import planning_evidence as pe  # noqa: E402
import self_report_measure as srm  # noqa: E402

_REPO = Path(__file__).resolve().parents[4]
TODAY = __import__("datetime").date(2026, 9, 24)
DAY = "2026-09-20"
R1, R2, R3 = "1" * 32, "2" * 32, "3" * 32


# --- fixture builders -------------------------------------------------------------

def _bag_event(run_id: str, write_path: str, address: str, content: str, *, seq: int = 0,
           at: str = f"{DAY}T00:00:00Z") -> str:
    return json.dumps({
        "content": content, "content_bytes": len(content.encode()),
        "destination": {"address": address, "store": "filesystem"}, "edge_id": "edge-test",
        "event_id": hashlib.sha256(f"{run_id}|{write_path}|{address}|{seq}".encode()).hexdigest()[:32],
        "gap_class": None, "key_epoch": "none", "kind": "completion",
        "lineage": {"input_index": None, "input_ref": None}, "outcome": None,
        "provenance": "fleet_authored", "recorded_at": at, "run_id": run_id,
        "schema_version": 1, "sequence": seq, "terminal_state": None, "write_path": write_path,
    }, sort_keys=True)


def _review_transcript(nonce: str, pr_url: str, findings) -> str:
    so = {"schema_version": "1", "run_id": nonce, "outcome": "hold", "hold_kind": "redispatch",
          "completion_ref": {"substrate": "github", "kind": "pull", "id": "7", "uri": pr_url},
          "findings": [{"id": i, "disposition": d} for i, d in findings]}
    return "\n".join(json.dumps(x) for x in (
        {"type": "system", "subtype": "init"},
        {"type": "result", "num_turns": 3, "structured_output": so})) + "\n"


def _block(nonce: str, items) -> str:
    lines = ["```yaml", "pr_review:", "  pr: 7", f"  run_id: {nonce}", "  findings:"]
    for fid, title in items:
        lines += [f"    - id: {fid}", f"      title: {title}", "      disposition: fixed"]
    return "\n".join(lines + ["```"])


def _bag(root: Path, run_id: str, *, reviews=(), threads=(), day=DAY) -> Path:
    """`reviews`: (nonce, pr_url, findings). `threads`: (repo, pr, body, [(cid, text)])."""
    bag = root / run_id
    (bag / "data" / "harvest").mkdir(parents=True)
    (bag / "bagit.txt").write_text("BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n")
    (bag / "bag-info.txt").write_text(
        f"External-Identifier: {run_id}\nEvent-Schema-Version: 1\nJournal-Workflow: review-pr\n"
        f"Journal-Origin-Repo: {root.parent / 'repos' / 'alpha'}\nJournal-Worktree: review-pr-1\n")
    (bag / "data" / "harvest" / "index.json").write_text(json.dumps({"surfaces": []}))
    lines = []
    for k, (nonce, url, findings) in enumerate(reviews):
        address = f"/logs/review-pr-20260920-000000-{run_id}{k:02d}.jsonl"
        lines.append(_bag_event(run_id, "cli-transcript", address, _review_transcript(nonce, url, findings),
                            at=f"{day}T00:00:00Z"))
        lines.append(_bag_event(run_id, "run-log:run_resources", address,
                            json.dumps({"type": "run_resources", "workflow_key": "review-pr"}),
                            at=f"{day}T00:00:00Z"))
    (bag / "data" / "events.jsonl").write_text("\n".join(lines) + "\n")
    harvest = []
    for repo, pr, body, comments in threads:
        stem = f"harvest:github:{repo}#{pr}"
        url = f"https://github.com/{repo}/pull/{pr}"
        harvest.append(_bag_event(run_id, f"{stem}:body", url, body, at=f"{day}T01:00:00Z"))
        for cid, text in comments:
            harvest.append(_bag_event(run_id, f"{stem}:comment:{cid}", url, text, seq=cid, at=f"{day}T01:00:00Z"))
    if harvest:
        (bag / "data" / "harvest" / "events.jsonl").write_text("\n".join(harvest) + "\n")
    return bag


PR_URL = "https://github.com/o/r/pull/7"
REFLECT = ("## Post-Run Reflection\n- **Friction:** the widget parser crashes on empty input and "
           "nothing in the suite exercised that path at all.\n")
TITLES = [("alpha-bug", "widget parser crashes on empty input"),
          ("beta-gap", "the quota ledger omits refunds entirely"),
          ("gamma-new", "a stale fixture masks the retry path")]
AFTER = ("## Post-Run Reflection\n- **Friction:** the quota ledger omits refunds entirely, "
         "which this correction pass then had to fix.\n")


def _standard_journal(root: Path) -> None:
    """One pass: the run stated alpha BEFORE the pass; beta only AFTER it; gamma never."""
    _bag(root, "a" * 32,
         reviews=[(R1, PR_URL, [("alpha-bug", "fixed"), ("beta-gap", "deferred"), ("gamma-new", "hold")])],
         threads=[("o/r", 7, "body", [(100, REFLECT), (200, _block(R1, TITLES) + "\n### Post-Run Reflection\n"),
                                      (300, AFTER)])])


def _planning(tmp_path: Path, cpi: str, items: dict[str, str]) -> Path:
    root = tmp_path / "planning"
    (root / "development" / "common").mkdir(parents=True)
    (root / "development" / "common" / "cpi-decisions.md").write_text(cpi)
    for store in ("candidates", "issues", "standards", "operations"):
        (root / "tracked" / store).mkdir(parents=True)
    for name, text in items.items():
        store = {"C": "candidates", "I": "issues", "S": "standards", "O": "operations"}[name[0]]
        (root / "tracked" / store / f"{name}.md").write_text(text)
    return root


def _item(ident: str, count, filed: str) -> str:
    return (f"---\nid: {ident}\ntitle: t\nstatus: open\ncount: {count}\nfiled: {filed}\n"
            f"filed_by: review-pr\n---\nbody\n")


CPI = """# CPI Decisions Log

## 2026-05-01 — cycle one

### DEFERRED — watch-list

- **TS-1 — thing one that recurs**
  - **Watch-criteria:** ship on second occurrence
- **TS-2 — thing two that never does**
  - Evidence: one
- **TS-3 — thing three, amended**
  - Evidence: one
  > 🔁 recurred 2026-05-30 in a third repo

### DEFERRED — a single named deferral long enough to cite

Deferred for want of evidence.

## 2026-05-20 — cycle two
- **TS-1** recurred in both repos this cycle.
- Reasoning: the same logic as TS-2, ship on second occurrence.
- **TS-2** closed without incident.
- **TS-9** recurred, unrelated to anything above.

## 2026-09-10 — recent
### WATCH — a young item not yet watchable for long

Count today: 1.

### DEFERRED — a deferral that a later phase simply built

> → SHIPPED 2026-09-12 by a planned phase.
"""


@pytest.fixture
def world(tmp_path: Path):
    journal = tmp_path / "journal"
    journal.mkdir()
    (tmp_path / "repos").mkdir()
    planning = _planning(tmp_path, CPI, {
        "C-aaaaaaaa": _item("C-aaaaaaaa", 2, "2026-09-01"),
        "C-bbbbbbbb": _item("C-bbbbbbbb", 1, "2026-01-01"),
        "C-cccccccc": _item("C-cccccccc", 1, "2026-09-01"),
        "I-dddddddd": "no frontmatter at all\n",
    })
    return journal, planning


def _run(world, *args, capsys, stdin=None, runner=None) -> tuple[int, str]:
    journal, planning = world
    code = srm.main(["--root", str(journal), "--planning", str(planning), *args],
                    today=TODAY, runner=runner, stdin=stdin)
    out = capsys.readouterr()
    return code, out.out + out.err


def _line(out: str, needle: str) -> str:
    hits = [line for line in out.splitlines() if needle in line]
    assert hits, f"no line containing {needle!r}"
    return hits[0]


# --- r1: E1b ------------------------------------------------------------------------

def test_E1b_counts_only_what_was_said_BEFORE_the_pass(world, capsys):
    """alpha was said before the pass (STATED), beta only after it (NEW here,
    STATED under the control's no-cut rule), gamma never (NEW)."""
    _standard_journal(world[0])
    code, out = _run(world, "--no-forge", capsys=capsys)
    assert code == 0, out
    assert "E1b new to the judge               2/3" in out
    assert "E1b already stated                 1/3" in out
    assert "new to the judge: 1/3" in _line(out, "new to the judge:")      # the control, no cut


def test_a_run_that_wrote_NOTHING_is_excluded_and_counted_not_NEW(world, capsys):
    _bag(world[0], "a" * 32, reviews=[(R1, PR_URL, [("alpha-bug", "fixed")])],
         threads=[("o/r", 7, "body", [(200, _block(R1, TITLES[:1]))])])
    code, out = _run(world, "--no-forge", capsys=capsys)
    assert "EXCLUDED no-self-account : 1" in out
    assert "E1b new to the judge" not in out


def test_a_pass_whose_comment_is_MISSING_is_unclassifiable_with_its_reason(world, capsys):
    _bag(world[0], "a" * 32, reviews=[(R2, PR_URL, [("alpha-bug", "fixed")])],
         threads=[("o/r", 7, "body", [(100, REFLECT), (200, _block(R1, TITLES))])])
    code, out = _run(world, "--no-forge", capsys=capsys)
    assert "EXCLUDED unclassifiable  : 1" in out
    assert "the pass's own comment is not in the thread" in out


def test_a_record_whose_bag_has_NO_HARVEST_is_read_from_the_FORGE(world, capsys):
    _bag(world[0], "a" * 32, reviews=[(R1, PR_URL, [("alpha-bug", "fixed"), ("gamma-new", "hold")])])
    calls = []

    def runner(args):
        calls.append(args)
        if args[:2] == ["api", "repos/o/r/issues/7"]:
            body = {"html_url": PR_URL, "title": "t", "user": {"login": "x"}, "created_at": "c",
                    "updated_at": "u", "body": "b", "comments": 2}
        else:
            body = [[{"id": cid, "html_url": f"{PR_URL}#c{cid}", "user": {"login": "x"},
                      "created_at": "c", "updated_at": "u", "body": text}
                     for cid, text in ((100, REFLECT), (200, _block(R1, TITLES)))]]
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(body), stderr="")
    code, out = _run(world, capsys=capsys, runner=runner)
    assert code == 0, out
    assert "thread source, per PR : harvest 0, forge 1" in out
    assert "E1b new to the judge               1/2" in out
    assert calls, "the forge was never asked"


def test_a_FORGE_refusal_is_counted_never_a_crash(world, capsys):
    _bag(world[0], "a" * 32, reviews=[(R1, PR_URL, [("alpha-bug", "fixed")])])
    code, out = _run(world, capsys=capsys,
                     runner=lambda a: subprocess.CompletedProcess(a, 1, stdout="", stderr="HTTP 404"))
    assert code == 0, out
    assert "thread unreached (forge refused)" in out
    assert "forge refused 1" in out


def test_a_finding_an_earlier_pass_carried_is_split_out(world, capsys):
    _bag(world[0], "a" * 32,
         reviews=[(R1, PR_URL, [("alpha-bug", "fixed")]),
                  (R2, PR_URL, [("alpha-bug", "fixed"), ("gamma-new", "hold")])],
         threads=[("o/r", 7, "body", [(100, REFLECT), (200, _block(R1, TITLES[:1])),
                                      (300, _block(R2, [TITLES[0], TITLES[2]]))])])
    code, out = _run(world, "--no-forge", capsys=capsys)
    assert "new, carried from an earlier pass: 0/1" in out
    assert "new, first raised on this pass: 1/2" in out


def test_no_typed_record_is_a_REFUSAL_not_a_quiet_report(world, capsys):
    code, out = _run(world, "--no-forge", capsys=capsys)
    assert code == 2 and "measured nothing" in out


def test_a_finding_slug_is_never_PRINTED(world, capsys):
    _standard_journal(world[0])
    code, out = _run(world, "--no-forge", capsys=capsys)
    for fid, _ in TITLES:
        assert fid not in out


# --- r2: recurrence claims --------------------------------------------------------------

@pytest.mark.parametrize("sentence, expected", [
    ("This bit us again on C-aaaaaaaa.", ("corroborated", "count")),
    ("This bit us again on C-cccccccc.", ("uncorroborated", "")),
    ("The widget-parser-crash came back again.", ("corroborated", "finding id")),
    ("This happened again, as everyone noticed.", ("uncorroborated", "")),
])
def test_a_claim_is_corroborated_ONLY_by_a_count_or_a_recurring_id(sentence, expected):
    status, by, _note = srm.corroborate(sentence, {"C-aaaaaaaa": 2, "C-cccccccc": 1},
                                        {"widget-parser-crash"})
    assert (status, by) == expected


def test_a_finding_id_recurs_when_TWO_passes_carry_it():
    rec = lambda i, fids: je.ReviewRecord("b", i, DAY, "o/r", 7, tuple((f, "fixed") for f in fids))  # noqa: E731
    assert srm.recurring_finding_ids([rec("x", ["a-b", "c-d"]), rec("y", ["a-b"])]) == {"a-b"}
    # one pass naming an id twice is ONE pass
    assert srm.recurring_finding_ids([rec("x", ["a-b", "a-b"])]) == set()


def test_a_FENCED_block_inside_a_reflection_is_not_a_sentence():
    text = ("### Post-Run Reflection\n- **Friction:** the gate went red again after the merge.\n"
            "```yaml\npr_review:\n  findings:\n    - title: a thing that recurred again\n```\n")
    sections = srm.reflection_sections(text)
    claims = [s for sec in sections for s in srm.sentences(sec) if srm.CLAIM.search(s)]
    assert len(claims) == 1 and "gate went red" in claims[0]


def test_a_reflection_section_ENDS_at_the_next_heading_of_its_level():
    text = ("## Decision Log\n- again outside\n## Post-Run Reflection\n- again inside\n"
            "### Friction\n- again nested\n## Deferred Work\n- again after\n")
    [section] = srm.reflection_sections(text)
    assert "inside" in section and "nested" in section
    assert "outside" not in section and "after" not in section


def test_r2_reads_the_repo_with_the_most_harvested_threads_and_says_so(world, capsys):
    _standard_journal(world[0])
    code, out = _run(world, "--no-forge", capsys=capsys)
    assert "## r2 — the recurrence-claim check, repo o/r" in out
    assert "threads read : 1 (harvest 1)" in out


# --- r3: the calibration ratio ------------------------------------------------------------

def test_the_three_groups_SUM_to_the_DEFERRED_count(world, capsys):
    """7 CPI entries: TS-1 recurred (line), TS-3 recurred (amended in place),
    TS-2 and the single named one NEVER (May, over 90 days), the young one
    CENSORED, the built one UNCLASSIFIED (→ SHIPPED is not a recurrence)."""
    _standard_journal(world[0])
    code, out = _run(world, "--no-forge", capsys=capsys)
    assert ("CPI DEFERRED entries     recurred    2 : never-recurred    2  -> ratio 1.00;"
            "  unclassified    2; total 6 (= 2 + 2 + 2)") in out
    assert "tracked items            recurred    1 : never-recurred    1" in out
    assert "total 4 (= 1 + 1 + 2)" in _line(out, "tracked items            recurred")


def test_a_WATCH_CRITERION_is_not_a_recurrence_and_neither_is_a_NEIGHBOURS_line(world):
    """TS-2 is cited on a criterion line ('ship on second occurrence') and sits
    one line from TS-9's 'recurred' — per-paragraph matching would call it
    recurred; per-line with the criterion rule does not."""
    sections, deferrals = pe.open_planning(str(world[1])).cpi_log()
    groups = {g.label[:4]: g for g in srm.cpi_groups(sections, deferrals, TODAY)}
    assert groups["TS-1"].group == "recurred"
    assert groups["TS-2"].group == "never"
    assert groups["TS-3"].group == "recurred" and "amended" in groups["TS-3"].reason


def test_a_deferral_a_phase_BUILT_is_unclassified_not_recurred(world):
    sections, deferrals = pe.open_planning(str(world[1])).cpi_log()
    built = [g for g in srm.cpi_groups(sections, deferrals, TODAY) if "simply built" in g.label]
    assert [g.group for g in built] == ["unclassified"] and "SHIPPED" in built[0].reason


@pytest.mark.parametrize("filed, group", [("2026-06-26", "never"), ("2026-06-27", "unclassified")])
def test_the_censoring_horizon_is_90_days_AT_THE_BOUNDARY(filed, group):
    [g] = srm.tracked_groups([pe.TrackedItem("C-x", "candidates", "open", 1, filed)], [], TODAY)
    assert g.group == group


def test_an_unparseable_tracked_item_is_LISTED_not_dropped(world, capsys):
    _standard_journal(world[0])
    code, out = _run(world, "--no-forge", capsys=capsys)
    assert "the item would not parse" in out and "I-dddddddd" in out


def test_the_cpi_parser_reads_every_ENTRY_SHAPE_the_log_writes():
    lines = ["## 2026-08-01 — x", "### DEFERRED — watch-criteria stated", "",
             "**A bold paragraph entry.** body", "", "1. **A numbered entry.** body",
             "**Watch (all three):** a label, not an entry", "- **A list entry**",
             "  - **Nested:** never an entry", "### SHIPPED — not a deferral", "- **Not deferred**"]
    titles = [d.title for d in pe._deferrals(lines)]
    assert titles == ["A bold paragraph entry.", "A numbered entry.", "A list entry"]


# --- r6: hypotheses and the hand check ------------------------------------------------------

def _stdin(obj) -> io.StringIO:
    return io.StringIO(json.dumps(obj))


def test_an_E1b_hypothesis_NEVER_moves_the_rate(world, capsys):
    _standard_journal(world[0])
    _, bare = _run(world, "--no-forge", capsys=capsys)
    code, out = _run(world, "--no-forge", "--stdin", capsys=capsys, stdin=_stdin({"hypotheses": {"e1b": [
        {"pr": "o/r#7", "finding_id": "gamma-new", "claim": "stated"},
        {"pr": "o/r#7", "finding_id": "alpha-bug", "claim": "stated"}]}}))
    assert _line(out, "E1b new to the judge") == _line(bare, "E1b new to the judge")
    assert "'computation agrees': 1" in out and "'computation disagrees': 1" in out


def test_a_sweep_claim_must_be_VERBATIM_and_is_corroborated_by_the_SAME_rule(world, capsys):
    _bag(world[0], "a" * 32, reviews=[(R1, PR_URL, [("alpha-bug", "fixed")])],
         threads=[("o/r", 7, "b", [(100, REFLECT + "- The ledger keeps dropping refunds, see C-aaaaaaaa.\n"),
                                   (200, _block(R1, TITLES[:1]))])])
    code, out = _run(world, "--no-forge", "--stdin", capsys=capsys, stdin=_stdin({"hypotheses": {"recurrence": [
        {"pr": "o/r#7", "comment_id": 100, "sentence": "The ledger keeps dropping refunds, see C-aaaaaaaa."},
        {"pr": "o/r#7", "comment_id": 100, "sentence": "An invented sentence that was never written."}]}}))
    assert "'added': 1" in out
    assert "not verbatim in that comment's reflection\": 1" in out
    assert "claims corroborated (computed + sweep-added population): 1/1" in out
    assert "changed the computed result: YES" in _line(out, "changed the computed result")
    assert "the computed rate has no denominator" in out               # the computed population is empty


def test_a_calibration_link_is_checked_for_POSITION_and_MARKER(world, capsys):
    _standard_journal(world[0])
    cpi = CPI.splitlines()
    single = 1 + next(i for i, l in enumerate(cpi) if "single named deferral" in l)
    ts9 = 1 + next(i for i, l in enumerate(cpi) if "TS-9" in l)
    closed = 1 + next(i for i, l in enumerate(cpi) if "closed without incident" in l)
    code, out = _run(world, "--no-forge", "--stdin", capsys=capsys, stdin=_stdin({"hypotheses": {"calibration": [
        {"entry_line": single, "evidence_line": ts9},        # later, marked: accepted
        {"entry_line": single, "evidence_line": closed},     # later, no marker: refused
        {"entry_line": single, "evidence_line": 3},          # earlier section: refused
        {"entry_line": 2, "evidence_line": ts9}]}}))         # not an entry: refused
    tally = _line(out, "WITH THE SWEEP'S DEFERRALS")
    for part in ("'reclassified recurred': 1", "carries no recurrence marker': 1",
                 "not in a later section': 1", "is not a DEFERRED entry': 1"):
        assert part in tally
    # the COMPUTED figure is untouched; the sweep's is printed beside it
    assert "CPI DEFERRED entries     recurred    2 : never-recurred    2" in out
    assert "both, with the sweep     recurred    4 : never-recurred    2" in out


def test_the_hand_check_prints_disagreements_AND_their_direction(world, capsys):
    _standard_journal(world[0])
    code, out = _run(world, "--no-forge", "--stdin", capsys=capsys, stdin=_stdin({"hand": {"e1b": {
        f"{R1}:0": "new", f"{R1}:1": "new", f"{R1}:2": "new", "nonexistent:0": "new"}}}))
    assert "hand sample n=3 (1 labels matched nothing), disagreements 1 (33%" in out
    assert "moves {'stated->new': 1}" in out


def test_emit_samples_carries_the_text_the_hand_check_NEEDS(world, capsys):
    _standard_journal(world[0])
    code, out = _run(world, "--no-forge", "--emit", "samples", "--sample-size", "2", capsys=capsys)
    rows = [json.loads(line) for line in out.splitlines()]
    e1b = [r for r in rows if r["check"] == "e1b"]
    assert len(e1b) == 2 and all(r["title"] and r["self_account_bullets"] for r in e1b)
    assert {r["check"] for r in rows} == {"e1b", "calibration"}


# --- r5: nothing weights model-asserted priority -------------------------------------------

#: The CLAIM SHAPE of ranking by assertion strength — a sort/rank/priority verb
#: keyed on how strongly, how confidently or how emphatically something was
#: said. WHAT IT DOES NOT LOOK AT: synonyms outside this list, test files,
#: anything outside `config/` and `scripts/workflows/`, and SEVERITY
#: labels (`Critical`, `High`), which are a judge's classification of the
#: defect rather than a run's conviction about its own claim — deliberately
#: out of scope, and named here so a reader can tell a boundary from an
#: oversight.
_ASSERTED_PRIORITY = re.compile(
    r"\b(?:rank|sort|order|priorit[iy]\w*|weight)\w*\b[^.\n]{0,40}\bby\b[^.\n]{0,20}"
    r"\b(?:how strongly|conviction|emphasis|confidence|strength of (?:the )?(?:assertion|claim)|"
    r"(?:asserted|stated|felt) (?:priority|importance|strength))", re.I)
_PROMPT_SURFACES = ("config/agents", "config/commands", "config/rules", "config/skills",
                    "scripts/workflows/temporal/modules", "scripts/workflows")


def _prompt_files() -> list[Path]:
    seen: set[Path] = set()
    for surface in _PROMPT_SURFACES:
        for suffix in ("*.md", "*.sh", "*.py"):         # .py: a triage rule can be code
            seen |= {p for p in (_REPO / surface).rglob(suffix) if "/tests/" not in str(p)}
    return sorted(seen)


def test_NOTHING_in_the_fleet_ranks_a_finding_by_how_strongly_it_was_ASSERTED():
    files = _prompt_files()
    assert len(files) > 200, f"vacuity floor: only {len(files)} prompt/rule/code files found"
    hits = [f"{p.relative_to(_REPO)}: {m.group(0)}" for p in files
            for m in _ASSERTED_PRIORITY.finditer(p.read_text(errors="replace"))]
    assert hits == [], "a prompt or triage rule weights model-asserted priority — Phase 2 r5:\n" + "\n".join(hits)


@pytest.mark.parametrize("text", [
    "Triage sorts candidates by how strongly the run asserted them.",
    "Rank findings by confidence, highest first.",
    "prioritise items by stated priority",
])
def test_the_asserted_priority_guard_FIRES(text):
    assert _ASSERTED_PRIORITY.search(text)


def test_the_asserted_priority_guard_leaves_COUNT_ordering_alone():
    assert not _ASSERTED_PRIORITY.search("`count` is what triage sorts on, and recurrence outranks age.")


# --- r4: no path semantics above the interfaces ----------------------------------------------

def test_the_figure_module_reaches_BOTH_interfaces_and_no_path():
    """THE AST GUARD ITSELF IS `test_journal_baseline.py`'s, which scans this
    module because its `_CONSUMERS` names it — asserted here from that file's
    TEXT (a test module is collected, never imported). This adds the vacuity
    floor for the planning half: the module really reaches both interfaces."""
    consumers = re.search(r"^_CONSUMERS = \((.*?)\)$",
                          (Path(__file__).parent / "test_journal_baseline.py").read_text(), re.M)
    assert consumers and '"self_report_measure.py"' in consumers.group(1)
    tree = ast.parse((_MEASURE / "self_report_measure.py").read_text())
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert {"open_journal", "units", "read", "review_records", "threads",
            "open_planning", "tracked_items", "cpi_log"} <= names
