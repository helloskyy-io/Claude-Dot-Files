"""INTAKE — how a decide-only run places a tracked item without committing.

THE PROBLEM THIS EXISTS FOR, stated because the mechanism looks like a
workaround until you know it. A **file** surface needs an edit, a commit and a
push, so only a run that produces a PR can write one. `review_pr` is decide-only
by design — it never touches the branch it is judging, because `author ≠ judge`
is the whole reason its verdict is worth anything — and it is also the platform's
largest producer of findings. When all four stores became file surfaces,
`review_pr` could place NOTHING: a correctly classified finding survived in a PR
body and died at merge, which is the exact failure the stores were built to end.

THE ANSWER IS NOT TO GIVE THE REVIEWER A COMMIT. A reviewer that can commit to
the branch under review mutates the diff it is judging; one that can commit
anywhere else needs a branch, a PR and a merge of its own for every finding.
Instead an **API** surface is reintroduced deliberately and bounded:
`Tracked Items Standard` §5.0 exempts a GitHub issue used purely as an INTAKE.

THE THREE CONDITIONS ARE THE WHOLE OF THE EXEMPTION, and this module is built to
keep them true rather than to assume them:

  1. **A named harvest cadence exists.** `harvest()` is it, and `/standup` calls
     it. An intake with no harvest is a second store and a §8 violation.
  2. **The intake is never read as a store.** Nothing cites an intake issue as
     the record; the record is the file the harvest produced. The closing comment
     points AT the file, so a reader who follows the issue lands on the store.
  3. **It empties.** Every harvested issue is closed in the same pass.

THE INTAKE BODY *IS* THE ITEM, which is the design decision worth keeping. Rather
than inventing a transport format that has to be kept in step with §3, the issue
body carries the item's own frontmatter and body, missing only the `id` — which
`harvest` mints, because minting is a pure write and the filer cannot know what
the store holds. So there is nothing to keep in sync: a change to §3 changes both
ends at once, and `tracked_items` remains the single writer.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from .. import assistant_activities as shared
from . import tracked_items as ti

#: Applied by the filer, queried by the harvest. The label IS the intake — an
#: issue without it is an ordinary issue and the harvest never touches it.
INTAKE_LABEL = "tracked-intake"

_STORE_LINE = re.compile(r"^store:\s*(\S+)\s*$", re.M)


class IntakeError(RuntimeError):
    """An intake issue that cannot be harvested, named so a human can fix it."""


def render_intake(store: ti.Store, title: str, body: str,
                  filed_by: str, extras: dict[str, str] | None = None) -> str:
    """The issue body a filer writes. Frontmatter plus prose, `id` absent."""
    fields = {"store": store.name, "status": "open", "filed_by": filed_by}
    fields.update(extras or {})
    block = "\n".join(f"{k}: {v}" for k, v in fields.items())
    return f"---\n{block}\n---\n\n{body.strip()}\n"


def parse_intake(issue_body: str) -> tuple[ti.Store, dict[str, str], str]:
    """Split an intake body into its store, its fields and its prose.

    EVERY FAILURE HERE IS LOUD AND NAMED. An intake that cannot be parsed must
    not be silently skipped: the finding it carries has already left the run
    that produced it, so a skipped intake is a lost finding — the failure mode
    the whole store design exists to end. It stays OPEN and is reported.
    """
    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", issue_body.strip() + "\n", re.S)
    if not match:
        raise IntakeError(
            "no frontmatter block — an intake body opens with `---`, the store "
            "and its fields, then `---`")

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise IntakeError(f"frontmatter line is not `key: value`: {line!r}")
        fields[key.strip()] = value.strip()

    name = fields.pop("store", "")
    store = ti.STORES.get(name)
    if store is None:
        raise IntakeError(
            f"`store: {name or '(missing)'}` is not one of "
            f"{sorted(ti.STORES)} — §1 names four and there is no fifth")

    forbidden = set(fields) & set(store.operator_only)
    if forbidden:
        raise IntakeError(
            f"{sorted(forbidden)} is the operator's alone (§4); an autonomous "
            f"filer may not set it")

    return store, fields, match.group(2).strip()


def _gh(*args: str, cwd: Path | None = None) -> str:
    """Every `gh` call this module makes, through the fleet's single launch point.

    ADDRESSED BY `cwd` AND NEVER BY `--repo`. `gh --repo` wants `OWNER/REPO`,
    while every `--repo` in this fleet is a FILESYSTEM PATH — so passing one
    through fails with a message about slug format, and the caller reads that as
    an unreadable repo rather than as a bad address. `run_bounded` also supplies
    the wall-clock ceiling that keeps a hung `gh` from parking the dispatch.
    """
    done = shared.run_bounded(["gh", *args], cwd=cwd)
    if done.returncode != 0:
        raise IntakeError(f"`gh {' '.join(args)}` failed: {done.stderr.strip()}")
    return done.stdout


def open_intakes(cwd: Path | None = None) -> list[dict]:
    """Every open intake issue, oldest first, so harvest order is filing order."""
    issues = json.loads(_gh(
        "issue", "list", "--label", INTAKE_LABEL, "--state", "open",
        "--limit", "200", "--json", "number,title,body,createdAt",
        cwd=cwd) or "[]")
    return sorted(issues, key=lambda i: i["createdAt"])


def harvest(root: Path, *, cwd: Path | None = None,
            dry_run: bool = False) -> tuple[list[tuple[int, Path]], list[tuple[int, str]]]:
    """Move every open intake into its store and close it. Returns (moved, failed).

    ORDER MATTERS AND IS CHOSEN: the file is written FIRST, and only then is the
    issue closed. A crash between the two leaves the item filed and the intake
    open, which the next pass resolves by seeing the item already exists. The
    other order loses the finding outright.

    IDEMPOTENT BY THE POINTER IT WRITES. Each item records the intake number it
    came from, so a re-run over an issue that was written but not closed finds
    the existing item and closes the issue rather than filing a second copy.
    """
    moved: list[tuple[int, Path]] = []
    failed: list[tuple[int, str]] = []

    for issue in open_intakes(cwd):
        number = issue["number"]
        try:
            store, fields, body = parse_intake(issue["body"] or "")

            existing = _already_filed(root, number)
            if existing is not None:
                path = existing
            else:
                status = fields.pop("status", "open")
                filed_by = fields.pop("filed_by", "review-pr")
                if dry_run:
                    moved.append((number, Path(f"{store.name}/(dry-run)")))
                    continue
                path = ti.file_item(
                    root, store, title=issue["title"], filed_by=filed_by,
                    status=status, extras=fields,
                    body=f"{body}\n\n*Filed via intake `#{number}` and harvested "
                         f"on {date.today().isoformat()}.*\n",
                    today=date.fromisoformat(issue["createdAt"][:10]))

            # REPO-RELATIVE, NEVER ABSOLUTE. This comment is public and is read
            # on someone else's machine: an absolute path leaks the harvester's
            # filesystem layout and resolves for nobody. Measured on the first
            # end-to-end run, which posted `/home/<user>/Repos/...`.
            try:
                shown = path.relative_to(root.parent)
            except ValueError:                      # a root outside the repo
                shown = path
            _gh("issue", "close", str(number), "--comment",
                f"Harvested to `{shown.as_posix()}`. The file is the record; "
                f"this intake carried it and is now empty, per Tracked Items "
                f"Standard §5.0.", cwd=cwd)
            moved.append((number, path))
        except IntakeError as exc:
            # LEFT OPEN DELIBERATELY. A malformed intake is a finding that has
            # already left its run; closing it would lose the finding to tidy up
            # the queue, which is the trade this design refuses to make.
            failed.append((number, str(exc)))

    return moved, failed


def _already_filed(root: Path, number: int) -> Path | None:
    """The item a previous partial harvest wrote for this intake, if any."""
    needle = f"intake `#{number}`"
    for store in ti.STORES.values():
        for path in (root / store.name).glob("*.md"):
            if needle in path.read_text():
                return path
    return None
