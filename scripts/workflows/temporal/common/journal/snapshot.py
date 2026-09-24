"""The starting snapshot — what each in-test store held at one moment, in the journal.

PMP PHASE 4 REQUIREMENT 2, AND IT LIVES IN THE JOURNAL PACKAGE BECAUSE IT IS A
JOURNAL ARTIFACT. Phase 5 retains it, measures it under the budget alongside the
bags, and stops a deletion at it; this package is what knows the root's layout.
What it does NOT know is what a `tracked/` store is — the materialisation
arrives here as DATA (`{store: {filename: text}}`) from
`modules.assistant.tracked.rebuild`, which owns the store contract, so the
one-way import rule (`common/journal/` imports no workflow module) holds.

WHY A FILE AT THE ROOT AND NOT A DIRECTORY. `validate.main`, `verify.main` and
the integration tier each treat EVERY DIRECTORY under the root as a bag —
`sorted(p for p in root.iterdir() if p.is_dir())` — and a `snapshots/` folder
would be reported as a structurally broken bag by all three. `edge-id` set the
precedent: per-root state that is not a run is a file beside the bags, and
every root walker already ignores files. Phase 5 r8's "only the most recent
snapshot is retained" is then a rule about files matching `SNAPSHOT_NAME_RE`.

TWO NAMED SECTIONS AND A VERSION, BECAUSE PHASE 5 CHANGES THE CONTENT LATER.
Phase 5 r8 carries retention, gap and redaction events forward from bags it has
rotated out, into this same artifact. This component's own rule — never change a
written artifact, upcast on read — means the shape has to be right BEFORE that
content exists:

  (a) `store_materialisation` — what each covered store held. **Replay applies
      this section and only this section.**
  (b) `carried_events` — journal-meta events preserved from rotated bags. EMPTY
      at Phase 4, and **replay never applies it as a store write**: a housekeeping
      record materialised into `tracked/candidates/` is exactly the junk the
      separation exists to prevent. `Snapshot.__post_init__` refuses a carried
      event that carries store content, so the rule is a check and not a hope.

`excluded_stores` IS THE THIRD FIELD AND IT IS NOT A SECTION. Phase 5 r1: *"a
store Phase 4 could not rebuild is not silently snapshotted as though it could
be"*. So a store outside coverage is NAMED here with its reason rather than
absent, and a reader of the snapshot can tell "not covered" from "was empty".

`taken_at` IS RECORDED BEFORE THE STORES ARE READ, and the ordering is what
makes replay-from-here correct rather than approximately correct. Replay applies
every write whose COMPLETION is recorded at or after `taken_at`; a write that
landed while the stores were being read is therefore applied AGAIN over a
materialisation that already reflects it — which is harmless, because every
tracked-store event carries the WHOLE file and applying it twice writes the
same bytes. Recording `taken_at` after the read would instead lose any write in
that window. **So `write_snapshot` takes `taken_at` FROM THE CALLER and does not
mint it**: the first draft stamped it inside this function, after
`take_snapshot` had read every store and walked every bag to count them — the
exact inversion this paragraph forbids, caught in review, and now held by
`test_the_snapshot_is_STAMPED_before_the_stores_are_read`.

THE VERSION IS REFUSED, NOT GUESSED, when it is one this code has no upcaster
for — the same rule `events.decode_event` applies to an event. A v2 snapshot
read with v1 field meanings would seed a replay with a confidently wrong
baseline, which is worse than an unreadable one.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .bag import FILE_MODE, JOURNAL_SCHEMA_VERSION
from .edge_id import read_edge_id

__all__ = ["SNAPSHOT_VERSION", "SNAPSHOT_NAME_RE", "Snapshot", "SnapshotError",
           "write_snapshot", "load_snapshot", "snapshot_paths",
           "latest_snapshot"]

#: Bumped when a field's MEANING changes or a section is added. Phase 5 r8 adds
#: content to section (b) without changing its meaning, so it stays at 1 there.
SNAPSHOT_VERSION = 1

_PREFIX = "snapshot-"
_SUFFIX = ".json"

#: `snapshot-<UTC stamp>-<8 hex>.json`. `\A`/`\Z` and not `^`/`$`: a trailing
#: newline in a name read off a listing must not match (test_journal_regex_anchors).
SNAPSHOT_NAME_RE = re.compile(
    r"\Asnapshot-(\d{8}T\d{6}Z)-([0-9a-f]{8})\.json\Z")


class SnapshotError(RuntimeError):
    """A snapshot could not be written, found or read. `RuntimeError` for the
    reason every other refusal in this package is: entrypoints already catch it."""


@dataclass(frozen=True)
class Snapshot:
    """One starting point for a replay. Written once, never edited.

    `bags_at_snapshot` is the count of bags under the root when the snapshot was
    taken — the "bags rotated out behind the snapshot" term of Phase 4
    § *Measurement*'s third figure, recorded now so Phase 5 has the number to
    subtract from rather than an estimate.

    `store_contract` is the Tracked Items §7 contract version the
    materialisation was read under. A rebuild records the version it rebuilt
    against (requirement 1) and this is where that version comes from for the
    snapshot half of the input.
    """

    snapshot_version: int
    snapshot_id: str
    taken_at: str
    edge_id: str
    journal_schema_version: int
    store_contract: str
    bags_at_snapshot: int
    store_materialisation: dict[str, dict[str, str]]
    excluded_stores: dict[str, str]
    carried_events: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.snapshot_version != SNAPSHOT_VERSION:
            raise SnapshotError(
                f"snapshot version {self.snapshot_version!r} is not "
                f"{SNAPSHOT_VERSION}, and no upcaster exists for it. Refusing "
                f"rather than seeding a replay from a baseline whose fields "
                f"this build reads with the wrong meanings.")
        if not self.snapshot_id or not self.taken_at or not self.edge_id:
            raise SnapshotError(
                "a snapshot carries an id, a timestamp and the edge that took "
                "it; one of the three is empty. Without them a rebuild cannot "
                "say which baseline it started from or where that baseline "
                "came from (requirement 9).")
        overlap = set(self.store_materialisation) & set(self.excluded_stores)
        if overlap:
            raise SnapshotError(
                f"{sorted(overlap)} appear both as materialised and as "
                f"excluded. A store is covered or it is named as not covered; "
                f"one that is both would let a replay apply a baseline the "
                f"snapshot itself says it cannot vouch for.")
        for event in self.carried_events:
            if event.get("content"):
                raise SnapshotError(
                    "a carried-forward journal-meta event carries store "
                    "content. Section (b) holds retention, gap and redaction "
                    "records preserved from rotated bags (Phase 5 r8); a "
                    "store write does not belong there, because replay never "
                    "applies section (b) and content placed in it would be "
                    "content nothing ever applies.")

    @property
    def name(self) -> str:
        stamp = self.taken_at.replace("-", "").replace(":", "")
        return f"{_PREFIX}{stamp}-{self.snapshot_id}{_SUFFIX}"


def write_snapshot(root: Path, *, taken_at: str, store_contract: str,
                   store_materialisation: Mapping[str, Mapping[str, str]],
                   excluded_stores: Mapping[str, str],
                   bags_at_snapshot: int) -> Path:
    """Write one snapshot at the journal root and return its path.

    `taken_at` IS THE CALLER'S, stamped before it read anything (module
    docstring). This function only records it.

    `O_EXCL` AND `FILE_MODE` AT CREATION, for the reason `Emitter._append`
    gives: the materialisation is the verbatim text of every covered store, and
    a world-readable file holding it must never exist even for the duration of
    a `chmod`. `O_NOFOLLOW` so a planted link at the name cannot redirect the
    write out of the root.

    THE EDGE ID IS READ, NEVER RESOLVED. `resolve_edge_id` would mint one on a
    root that has none, and a snapshot is not the place a machine acquires an
    identity — an `edge-id` file is what every run under this root already
    wrote, and a root with none has had no run and therefore nothing to snapshot
    against. Refusing says so.
    """
    edge = read_edge_id(root)
    if not edge:
        raise SnapshotError(
            f"{root} carries no edge-id file, so no run has ever opened a bag "
            f"under it. A snapshot is the point a replay STARTS from; a root "
            f"with no runs has nothing to replay, and stamping an identity here "
            f"would give this machine a name outside the one place that mints "
            f"them (edge_id.resolve_edge_id).")
    snapshot = Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        snapshot_id=secrets.token_hex(4),
        taken_at=taken_at,
        edge_id=edge,
        journal_schema_version=JOURNAL_SCHEMA_VERSION,
        store_contract=store_contract,
        bags_at_snapshot=bags_at_snapshot,
        store_materialisation={s: dict(files) for s, files
                               in store_materialisation.items()},
        excluded_stores=dict(excluded_stores),
    )
    # The name is composed from this module's own prefix and suffix, a
    # timestamp this module produced, and 8 hex characters from `secrets` — no
    # caller-supplied value reaches it, which is the reason the join is
    # trusted (test_journal_containment's `_TRUSTED_JOINS` carries the row).
    path = root / snapshot.name
    payload = json.dumps(asdict(snapshot), sort_keys=True, ensure_ascii=False,
                         indent=1)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 FILE_MODE)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return path


def load_snapshot(path: Path) -> Snapshot:
    """Read one snapshot back, refusing a version this build cannot upcast."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SnapshotError(f"{path} does not hold a JSON object")
    try:
        return Snapshot(
            snapshot_version=raw["snapshot_version"],
            snapshot_id=raw["snapshot_id"],
            taken_at=raw["taken_at"],
            edge_id=raw["edge_id"],
            journal_schema_version=raw["journal_schema_version"],
            store_contract=raw["store_contract"],
            bags_at_snapshot=raw["bags_at_snapshot"],
            store_materialisation=raw["store_materialisation"],
            excluded_stores=raw["excluded_stores"],
            carried_events=tuple(raw.get("carried_events", ())),
        )
    except KeyError as exc:
        raise SnapshotError(
            f"{path} is missing the {exc} field. A snapshot with a field "
            f"absent is not an older shape this code can upcast — every "
            f"version-1 field is required — so it is refused rather than "
            f"read with a default nobody wrote.") from exc


def snapshot_paths(root: Path) -> list[Path]:
    """Every snapshot under the root, oldest first by name (the name carries the stamp)."""
    return sorted(p for p in root.iterdir()
                  if p.is_file() and not p.is_symlink()
                  and SNAPSHOT_NAME_RE.match(p.name))


def latest_snapshot(root: Path) -> Snapshot | None:
    """The most recent snapshot, or `None` when the root has never been snapshotted.

    `None` IS A REAL ANSWER AND THE CALLER DECIDES WHAT IT MEANS. For a rebuild
    it is a refusal — there is no baseline to replay from — and the refusal
    names the command that creates one. For Phase 5's pass it is step 2's
    "if no snapshot exists, write one". Deciding here would be deciding for
    both.
    """
    paths = snapshot_paths(root)
    if not paths:
        return None
    return load_snapshot(paths[-1])
