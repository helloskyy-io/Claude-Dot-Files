"""Capture the sources a research paper cited, inside the run that cited them.

WHY IN-WINDOW RATHER THAN AT HARVEST. The content store's guarantee is that the
bytes on disk are the bytes a claim can be re-checked against. With model-native
reads that can never be a READ-TIME guarantee — the analyst reads an EXTRACTION
returned by its fetch tool, and fleet code never sees it — so the honest
guarantee is fetch-time, recorded as `capture="harvest"`. What in-window capture
buys is the WINDOW: seconds after the claim was made, inside the run that made
it, instead of whenever a later harvest happens to run. That does not change the
guarantee's kind; it shrinks the interval in which a source can change or vanish.

THE INPUT IS A SIDECAR, NOT THE PAPER'S PROSE, AND THAT IS THE DESIGN DECISION
HERE. The store REFUSES a citation with no quoted span — "a citation with no
quoted span has nothing for `verify` to re-check, which is the whole reason the
bytes were stored" — so a URL alone is not capturable. Papers carry URLs and
carry verbatim spans, but nothing pairs them machine-readably, and pairing them
by proximity would be a GUESS that produces a citation whose span is not in the
bytes: a guaranteed `span-missing` finding manufactured by the capture path. The
run writes the pairs it already knows.

⚠ CAPTURE MUST NEVER FAIL THE RESEARCH RUN. The paper is the deliverable; the
capture is evidence about it. A source that 404s, times out, redirects to a
refused address or trips any other part of the fetch policy is a RECORDED
capture-failure on that citation. A dead research run because a footnote link
rotted is the wrong failure, and it is the one this module is written to make
impossible: every per-citation error is caught, and the sweep returns a report
rather than raising.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

#: The run's machine-readable citation list, at the root of the pool it wrote.
#: ONE PER RUN rather than one per paper: a run may touch several papers, and a
#: single list is what the run can write once at the end without re-opening each.
SIDECAR_NAME = "citations.json"


@dataclass
class CaptureReport:
    """What the sweep did, in a shape a parent can put in its notes."""
    captured: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)   # (url, reason)
    skipped: int = 0
    sidecar: Path | None = None
    parse_error: str = ""

    def as_note(self) -> str:
        if self.parse_error:
            return (f"source capture: NOT RUN — {self.parse_error}. The paper is "
                    f"unaffected; no citation was captured for this run.")
        if self.sidecar is None:
            return ("source capture: NOT RUN — no `citations.json` beside the paper. "
                    "The run cited sources it did not pair with quoted spans, so "
                    "nothing could be stored against a claim.")
        bits = [f"{self.captured} captured"]
        if self.failed:
            bits.append(f"{len(self.failed)} failed")
        if self.skipped:
            bits.append(f"{self.skipped} skipped")
        note = "source capture: " + ", ".join(bits) + "."
        for url, reason in self.failed[:5]:
            note += f"\n  FAILED {url} — {reason}"
        if len(self.failed) > 5:
            note += f"\n  … and {len(self.failed) - 5} more"
        return note


def read_sidecar(pool_dir: Path) -> tuple[list[dict], str]:
    """`(rows, error)` — never raises, because a malformed sidecar is a finding.

    A run that wrote unparseable JSON has produced a bad artifact, not a reason
    to lose the paper it also produced.
    """
    side = pool_dir / SIDECAR_NAME
    if not side.is_file():
        return [], ""
    try:
        loaded = json.loads(side.read_text(encoding="utf-8"))
    except Exception as e:
        return [], f"{SIDECAR_NAME} is not readable JSON ({e})"
    if not isinstance(loaded, list):
        return [], f"{SIDECAR_NAME} must be a JSON array of citation objects"
    return [r for r in loaded if isinstance(r, dict)], ""


def capture_cited_sources(*, pool_dir: Path, bag, stage: str,
                          capture_fn=None, policy=None) -> CaptureReport:
    """Fetch and store every source the run paired with a quoted span.

    `capture_fn` IS INJECTED so this module can be driven without a network and
    without importing the fetcher into a test's process. Production passes
    `journal.capture_source`; the default resolves it lazily for the same reason
    the fetcher is kept off `verify`'s import closure.
    """
    report = CaptureReport()
    rows, err = read_sidecar(pool_dir)
    if err:
        report.parse_error = err
        return report
    if not rows:
        return report
    report.sidecar = pool_dir / SIDECAR_NAME

    if capture_fn is None:                       # pragma: no cover - thin binding
        from ...journal import capture_source as capture_fn      # noqa: PLC0415

    for row in rows:
        url = str(row.get("url") or "").strip()
        quote = str(row.get("quote") or "").strip()
        claim_id = str(row.get("claim_id") or "").strip()
        if not (url and quote and claim_id):
            # NOT A FAILURE ROW: nothing was attempted, so reporting it as a
            # failed fetch would misdescribe what happened. An incomplete row is
            # the run's own artifact defect and is counted separately.
            report.skipped += 1
            continue
        try:
            capture_fn(bag=bag, stage=stage, claim_id=claim_id, quote=quote,
                       url=url, policy=policy)
            report.captured += 1
        except Exception as e:                   # noqa: BLE001 - the whole point
            # EVERY exception, deliberately. The fetch policy raises its own
            # refusals, the store raises its own, and a bug in either is still
            # not a reason to lose a completed paper. The reason is recorded so
            # an operator can tell a rotted link from a policy refusal.
            report.failed.append((url, f"{type(e).__name__}: {e}"))
    return report
