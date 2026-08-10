#!/usr/bin/env python3
"""Replay the SHIPPED convergence predicate over the archived `pr_review:` blocks.

WHY THIS IS KEPT: `phase5_convergence_stopping.md` step 6 requires the predicate
to be validated against the archive *before it gates anything live*, and the
archive grows with every reviewed PR. The numbers in that doc are a snapshot
with a date; this is how the next reader re-takes them rather than re-deriving
the method. Phase 1 E7's headline figure went stale in one day — 38 PRs to 41,
and a second `converged: true` block appeared — so re-running is not optional
before quoting any of it.

IT IMPORTS THE PREDICATE RATHER THAN PINNING A COPY, WHICH IS THE OPPOSITE OF
`replay_completion_predicate.py`, AND THE DIFFERENCE IS DELIBERATE. That tool
measures the historical miss rate of an INCUMBENT gate, so its number must stay
reproducible against the same logs and a live import would silently re-measure a
changed rule. This tool validates a CANDIDATE predicate before it is trusted, so
importing the shipped one is the whole point — a pinned copy here would validate
a copy and certify a rule nobody runs. The consequence is stated rather than
hidden: re-running after a predicate change re-measures the NEW rule, which is
what step 6 wants, and the report prints the predicate's own vocabulary so a
reader can see which rule produced the numbers.

WHAT IT READS, AND THE ASYMMETRY WITH THE LIVE PATH. Every pass here comes from
its durable `pr_review:` block, parsed as prose. In the live workflow the pass
under assessment comes from the TYPED exit record instead, with the render↔record
invariant guaranteeing the two carry identical `(id, disposition)` pairs. So this
replay measures the predicate over the channel that survived, which is the only
channel a historical pass has — a Kind 2 record's lifetime is one parent
invocation.

Reads only `gh` output. Writes nothing.

Usage:  python3 scripts/helpers/measure/replay_convergence_predicate.py [OWNER/REPO]
        python3 scripts/helpers/measure/replay_convergence_predicate.py --json FILE

The second form replays a saved `replay_pr_review_blocks.py` dump, so the
extraction is paid once when both tools are run together.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
_CONVERGENCE = _REPO / "scripts" / "workflows" / "temporal" / "modules" / \
    "assistant" / "convergence.py"
_EXTRACTOR = _HERE / "replay_pr_review_blocks.py"

DEFAULT_REPO = "helloskyy-io/Claude-Dot-Files"


def _load(path: Path, name: str):
    """Load a module BY PATH.

    `convergence.py` is dependency-free precisely so this works: it imports no
    sibling, so it needs no package context and this tool needs no `sys.path`
    surgery. A predicate that had to be imported as `modules.assistant.…` would
    drag the whole workflow tree — and its `temporalio` import — into a
    measurement helper.

    REGISTERED IN `sys.modules` BEFORE EXECUTION, and that line is load-bearing
    rather than tidy. `@dataclass` resolves its own module out of
    `sys.modules[cls.__module__]` to detect `KW_ONLY`; a path-loaded module that
    is not registered has `sys.modules.get(...) is None` and the decorator dies
    with `AttributeError: 'NoneType' object has no attribute '__dict__'` — an
    error naming neither the dataclass nor the loader.
    """
    assert path.exists(), f"the declaration moved: {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def extract(repo: str) -> list[dict]:
    """Run the block extractor and parse its dump.

    Delegated rather than re-implemented: `replay_pr_review_blocks.py` owns the
    fence-anchored address and the per-finding disposition parse, and both are
    gated against `review_pr_helper` by `test_exit_record.py`. A second
    extractor here would be a fourth declaration of the marker that already has
    an open issue (#68) for having had three.
    """
    out = subprocess.run(
        [sys.executable, str(_EXTRACTOR), repo],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def _passes(blocks: list[dict]) -> list[dict]:
    """The dump's blocks in COMMENT-CREATION ORDER, which is the predicate's contract.

    THE EXTRACTOR IS SHARED AND ITS ORDERING IS NOT THIS PREDICATE'S.
    `replay_pr_review_blocks.py` sorts by `(pass, created)`, which serves its own
    consumers. `convergence.assess` forbids exactly that: sequence comes from the
    order the passes are handed in and NEVER from the `pass:` integer, which is
    producer-written and which issue #68 measured wrong on the most recently
    reviewed PR in the repo. A dump whose labels disagree with creation time
    would hand the predicate a mis-ordered history, making a cumulative later
    block look like an earlier one that dropped findings.

    RE-SORTED HERE RATHER THAN IN THE EXTRACTOR, deliberately. That dump is read
    by two other tools, one of which reports a historical figure that must stay
    reproducible; re-sorting it at the source would move a published number to
    fix a consumer's contract. The consumer that HAS the contract enforces it.

    It moves no number on today's archive — no PR's labels disagree with its
    comment order — which is exactly why it has to be code rather than a
    checked-once observation.

    WHAT THIS DELIBERATELY DOES NOT DO, because the dump cannot support it. The
    LIVE reader (`review_pr_activities.thread_snapshot`) returns one entry per
    PASS, taking the last block within a comment, because a quoted block is a
    restatement of a pass already in the window rather than a pass. This dump
    has already lost within-comment body order to the `pass:` sort above, so the
    same collapse here would have to guess which of two same-timestamp blocks is
    the quote. `report()` warns instead, and the archive has never contained the
    shape — see `_multi_block_comments`.
    """
    return sorted(blocks, key=lambda b: b.get("created") or "")


def _multi_block_comments(archive: list[dict]) -> list[tuple[int, str]]:
    """PRs whose dump carries two blocks under one comment timestamp.

    The one shape under which a replayed denominator would over-count passes.
    Reported rather than silently corrected: a corrected number nobody was told
    about is the same defect as a wrong one.
    """
    seen: list[tuple[int, str]] = []
    for pr in archive:
        stamps = [b.get("created") for b in pr["blocks"] if b.get("created")]
        seen += [(pr["pr"], s) for s in sorted(set(stamps))
                 if stamps.count(s) > 1]
    return seen


def replay(archive: list[dict], convergence) -> dict:
    """Assess every consecutive-pass position in the archive.

    ONE ASSESSMENT PER BLOCK FROM PASS 2 ONWARD, with the history being every
    block up to and including it. Pass 1 is included too and lands in the
    residual arm (`no_prior_pass`), because reporting only the assessable
    positions would quietly shrink the denominator — the honest denominator is
    "blocks the predicate would have seen", not "blocks it could rule on".
    """
    rows: list[dict] = []
    for pr in archive:
        blocks = _passes(pr["blocks"])
        for i, block in enumerate(blocks):
            history = [
                tuple((f["id"], f["disposition"] or "") for f in b["findings"])
                for b in blocks[: i + 1]
            ]
            # `pass_evaluable=True` for every archived block, and that is an
            # ASSUMPTION this report states rather than a fact it measured. The
            # live gate is the pass's typed exit record routing to something
            # other than undetermined, and no archived block carries one — the
            # typed channel did not exist when they were written. A block that
            # exists at all was posted by a pass that completed far enough to
            # post it, which is weaker evidence than the live check and is the
            # best this corpus supports.
            assessment = convergence.assess(history, pass_evaluable=True)
            rows.append({
                "pr": pr["pr"],
                "index": i + 1,
                "labelled_pass": block["pass"],
                "verdict": block["verdict"],
                "asserted_converged": block["converged"],
                "state": assessment.state.value,
                "reason": assessment.reason.value if assessment.reason else None,
                "open": len(assessment.open_ids),
                "opened": len(assessment.opened),
                "closed": len(assessment.closed),
                "added_ids": len(assessment.added_ids),
                "escalated_open": len(assessment.escalated_open),
                "stalled": assessment.stalled,
            })
    return {"rows": rows, "archive_prs": len(archive),
            "multi_block_comments": _multi_block_comments(archive)}


def report(result: dict, convergence) -> None:
    rows = result["rows"]
    multi = [r for r in rows if r["index"] > 1]
    states = Counter(r["state"] for r in rows)
    reasons = Counter(r["reason"] for r in rows if r["reason"])

    print("# Convergence predicate replay")
    print()
    print(f"Predicate states  : {[s.value for s in convergence.ConvergenceState]}")
    print(f"Closed dispositions: {sorted(convergence.CLOSED_DISPOSITIONS)}")
    print(f"Open dispositions  : {sorted(convergence.OPEN_DISPOSITIONS)}")
    print()
    print(f"PRs in archive             : {result['archive_prs']}")
    print(f"Blocks assessed            : {len(rows)}")
    print(f"Blocks with a prior pass   : {len(multi)}")
    print(f"States                     : {dict(states)}")
    print(f"Residual-arm reasons       : {dict(reasons)}")
    doubled = result.get("multi_block_comments") or []
    print(f"Comments carrying >1 block : {len(doubled)}"
          + (f" — {doubled}; each over-counts a pass in the rows below, because "
             f"this dump cannot say which block was the quote" if doubled else
             " (so no pass in this replay is a quoted restatement)"))
    print()

    # WOULD IT HAVE FIRED, AND WOULD IT HAVE FIRED EARLY? Step 6 asks for three
    # numbers and this is where they come from.
    #
    # EARLY IS REPORTED TWICE, AND ONLY THE SECOND ONE IS EVIDENCE.
    #
    # `early_self_reported` scores a fire against the block's OWN `verdict:` —
    # and that verdict is written by the same actor, in the same block, on the
    # same pass, as the dispositions the predicate reads. The mode this phase
    # names as UNMITIGATED is a reviewer marking `fixed` what is not fixed; such
    # a reviewer emits `MERGE` too, so this counter cannot move for the failure
    # it is supposed to alarm on. A gate expressed in its units ("60 blocks with
    # 0 early fires") would be measuring a quantity held at zero by construction.
    #
    # `early_observed` is model-independent: the predicate said CONVERGED at
    # index i, and some LATER block on the same PR carries a non-empty open set.
    # That is the loop demonstrably not being over, established by a subsequent
    # pass rather than by the same pass's self-assessment. It can only be scored
    # where a later block exists, so its denominator is stated separately —
    # a fire on a PR's last block is unfalsifiable from this corpus and is
    # counted as such rather than as a pass.
    fired = [r for r in multi if r["state"] == "converged"]
    # `!= "MERGE"` deliberately includes an unparseable `verdict: None`: this
    # figure over-counts on purpose, so a zero under it is the stronger claim.
    early_self = [r for r in fired if r["verdict"] != "MERGE"]
    by_pr: dict = {}
    for r in rows:
        by_pr.setdefault(r["pr"], []).append(r)
    def _later_open(r: dict) -> list[dict]:
        return [s for s in by_pr[r["pr"]] if s["index"] > r["index"] and s["open"]]
    scorable = [r for r in fired if any(s["index"] > r["index"] for s in by_pr[r["pr"]])]
    early_obs = [r for r in scorable if _later_open(r)]
    never = {r["pr"] for r in multi} - {r["pr"] for r in fired}
    print(f"Would have FIRED           : {len(fired)} of {len(multi)} assessable blocks")
    print(f"  ... on PRs               : {sorted({r['pr'] for r in fired})}")
    print(f"Fired EARLY (observed)     : {len(early_obs)} of {len(scorable)} fires that "
          f"HAVE a later block — a later pass reopened work")
    print(f"  ... unfalsifiable        : {len(fired) - len(scorable)} fire(s) on a PR's "
          f"last block; nothing after them to contradict")
    print(f"Fired EARLY (self-reported): {len(early_self)} — CONVERGED against a "
          f"non-MERGE verdict the SAME pass wrote. Circular; secondary only")
    print(f"Multi-pass PRs it NEVER fired on: {sorted(never)}")
    print()

    # THE SHADOW AGAINST THE INCUMBENT. Phase 1 E7's ruling is that the shipped
    # `converged` flag is a label the computation should reproduce; this is the
    # cross-tab that says whether it does. `None` is kept distinct from `False`
    # because absence dates a block to before the flag shipped.
    cross: Counter = Counter()
    for r in multi:
        asserted = r["asserted_converged"]
        if asserted is None or r["state"] == "indeterminate":
            cross[("n/a", r["state"])] += 1
        else:
            cross[(str(asserted).lower(), r["state"])] += 1
    print("Incumbent `converged:` x computed state (assessable blocks):")
    for (asserted, state), n in sorted(cross.items()):
        print(f"  asserted={asserted:<5} computed={state:<14} {n}")
    disagree = [
        r for r in multi
        if r["asserted_converged"] is not None and r["state"] != "indeterminate"
        and r["asserted_converged"] != (r["state"] == "converged")
    ]
    print(f"  DISAGREEMENTS: {len(disagree)} — "
          f"{[(r['pr'], r['index']) for r in disagree] or 'none'}")
    print()

    print("Per-block:")
    header = ("pr", "n", "label", "verdict", "conv", "state", "reason",
              "open", "opened", "closed", "added", "esc", "stalled")
    print("  " + " | ".join(f"{h}" for h in header))
    for r in rows:
        print("  " + " | ".join(str(x) for x in (
            r["pr"], r["index"], r["labelled_pass"], r["verdict"],
            r["asserted_converged"], r["state"], r["reason"] or "-",
            r["open"], r["opened"], r["closed"], r["added_ids"],
            r["escalated_open"], r["stalled"],
        )))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default=DEFAULT_REPO)
    parser.add_argument("--json", dest="dump", type=Path, default=None,
                        help="replay a saved replay_pr_review_blocks.py dump")
    args = parser.parse_args(argv)

    convergence = _load(_CONVERGENCE, "_convergence")
    archive = json.loads(args.dump.read_text()) if args.dump else extract(args.repo)
    report(replay(archive, convergence), convergence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
