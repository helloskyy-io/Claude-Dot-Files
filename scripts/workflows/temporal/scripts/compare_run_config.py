#!/usr/bin/env python3
"""Did these two runs use the same configuration? Answered from their bags alone.

    compare_run_config.py <bag-a> <bag-b>

WORKFLOW DECOMPOSITION PHASE 5 r3, AND THE NAMED CONSUMER OF `Journal-Config-Digest`.
The tag is the producer; this is its reader. The pairing is deliberate — the
phase ships both together rather than leaving a recorded value with nobody
reading it, which is the failure `phase6_every_producer_names_its_consumer.md`
exists to catch.

⚠ THIS READER IS INVOKED ON DEMAND. IT HAS NO CADENCE AND NO TERMINATION, AND
THAT IS RECORDED PLAINLY RATHER THAN DRESSED UP. Nothing schedules it; a person
runs it when two runs are suspected to disagree. Its population — the bags under
a journal root — accumulates and is never edited after sealing, so the surface
neither empties nor terminates. Phase 6's candidate producer definition requires
a named cadence and an emptying surface, so this pair FAILS that definition. It
is that phase's test case rather than its exemplar, tracked at `C-k3nd8vwp`, and
inventing a schedule here to make the pair look conformant would destroy the
evidence the ruling needs.

NO NETWORK AND NO LIVE FILESYSTEM READ OF THE CONFIGURATION. It opens exactly two
`bag-info.txt` files. A reader that re-read `~/.claude/` would be answering
*what is installed now*, which is a different question from *what did these two
runs absorb*, and on a machine whose configuration has since changed the two
answers differ.

IT REPORTS SAME-OR-DIFFERENT, NEVER WHICH ONE WAS RIGHT. Two runs disagreeing is
a fact; which configuration should have been in force is a policy question this
phase does not own and this tool does not answer.

EXIT CODES ARE A CONTRACT:
    0  both bags recorded a digest and the digests MATCH
    1  both bags recorded a digest and they DIFFER
    2  usage error, or a bag that could not be read
    3  at least one bag has nothing to compare — the tag is absent (a bag written
       before this tag existed) or records `unavailable`

3 IS SEPARATE FROM 1 ON PURPOSE. "These runs differed" and "I cannot tell whether
they differed" are different answers, and collapsing them would report an
unknown as a divergence — which is exactly the confidently-wrong shape the digest
was built to remove.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.journal.bag import BAG_INFO_FILE, read_tag_file  # noqa: E402
from modules.journal.config_digest import (  # noqa: E402
    DIGEST_ALGORITHM, LABEL_CONFIG_DIGEST, parse_tag_value)

USAGE = "usage: compare_run_config.py <bag-a> <bag-b>"


@dataclass(frozen=True)
class BagDigest:
    """What one bag had to say about the configuration its run absorbed.

    `fatal` separates "this is not a run bag" from "this bag has nothing to
    say". The first is the operator pointing the tool at the wrong directory
    and is a usage error; the second is a real, honest unknown about a real
    bag. They are different next actions, so they are different exit codes —
    and carrying the distinction as a FIELD rather than re-deriving it from the
    text of `problem` is what keeps the two from drifting apart when a message
    is reworded.
    """

    path: Path
    digest: str | None
    fields: dict[str, tuple[str, ...]]
    problem: str | None
    fatal: bool = False


def _read_digest(bag_dir: Path) -> BagDigest:
    """One bag's `Journal-Config-Digest`, or why there is nothing to compare."""
    info = bag_dir / BAG_INFO_FILE
    if not info.is_file():
        return BagDigest(bag_dir, None, {},
                         f"{bag_dir}: no {BAG_INFO_FILE} — not a run bag",
                         fatal=True)
    try:
        rows = read_tag_file(info)
    except OSError as exc:
        return BagDigest(bag_dir, None, {},
                         f"{info}: could not be read — {exc.strerror}",
                         fatal=True)

    values = [value for label, value in rows if label == LABEL_CONFIG_DIGEST]
    if not values:
        return BagDigest(bag_dir, None, {}, (
            f"{bag_dir}: no {LABEL_CONFIG_DIGEST} tag — this bag predates the "
            f"tag, so what its run absorbed was never recorded and cannot be "
            f"recovered from it"))
    # THERE SHOULD NEVER BE MORE THAN ONE. The tag is written once at bag-open
    # and a bag is never edited afterwards, so a second line means the file was
    # tampered with or a writer broke that contract. Refusing to pick one is
    # more useful than silently taking the first and reporting a confident
    # answer about metadata that is not trustworthy.
    if len(values) > 1:
        return BagDigest(bag_dir, None, {}, (
            f"{bag_dir}: {len(values)} {LABEL_CONFIG_DIGEST} lines — the tag is "
            f"written once and never edited, so this bag's metadata is not "
            f"trustworthy"), fatal=True)

    digest, fields = parse_tag_value(values[0])
    if digest is None:
        reason = ",".join(fields.get("reason", ())) or "unstated"
        return BagDigest(bag_dir, None, fields,
                         f"{bag_dir}: recorded no digest (reason={reason})")
    return BagDigest(bag_dir, digest, fields, None)


def _render(bag: BagDigest) -> list[str]:
    lines = [f"  {bag.path}: {DIGEST_ALGORITHM}:{bag.digest}"]
    for key in ("targets", "absent", "unreadable"):
        if key in bag.fields:
            lines.append(f"      {key}: {', '.join(bag.fields[key]) or 'none'}")
    return lines


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print(USAGE, file=sys.stderr)
        return 2

    read = [_read_digest(Path(a)) for a in args]
    for bag in read:
        if bag.problem is not None:
            print(bag.problem, file=sys.stderr)
    if any(bag.fatal for bag in read):
        return 2
    if any(bag.digest is None for bag in read):
        print("UNKNOWN — at least one bag recorded no digest to compare.")
        return 3

    same = read[0].digest == read[1].digest
    print("SAME" if same else "DIFFERENT")
    for bag in read:
        print("\n".join(_render(bag)))
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
