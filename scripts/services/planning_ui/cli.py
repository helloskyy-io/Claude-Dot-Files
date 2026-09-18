"""Generate the corpus views, check the committed ones are current, or serve
the two diagram pages.

**Two verbs and one shared derivation.** ``generate`` writes what the corpus
says; ``--check`` derives the same thing and compares, exiting non-zero when
they differ. They must never diverge, so they call one function and differ
only in what they do with the result — a check that re-implements the
generator is a check that can pass while the generator is wrong.

**Four artifacts, one walk.** The graph, the consistency report, the
decisions page and the viewer's inputs are rendered from a single
:func:`extract` result; no page walks the corpus a second time, so the four
cannot disagree about what the corpus contains.

**A third verb, ``serve``, is a third caller of the same derivation.** It
starts the process that serves the two diagram pages (:mod:`planning_ui.serve`)
and derives afresh on every request, so a refresh of the page is a re-read of
the corpus. It writes nothing and gates nothing.

`repo_layout.md` §1.1 requires the pairing: *"a viewer that derives a graph
commits it and carries a --check that fails when it drifts from the corpus.
Deriving on demand cannot go stale but also cannot be reviewed; a committed
artifact keeps the never-disagree property and makes an edge appearing or
disappearing visible in a pull-request diff."*

**The answer does not depend on where the checkout sits.** Link resolution
reads the link text alone (:mod:`.plan_extractor.safe_paths`), and the one
path-dependent string a page carried is gone, so ``--check`` on a pull-request
runner agrees with any developer's checkout. That is what lets the check
run on a runner at all.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

from planning_ui.decisions import assemble
from planning_ui.decisions.history import merge_heads
from planning_ui.decisions import render_markdown as render_decisions
from planning_ui.plan_extractor import ExtractionResult, extract
from planning_ui.plan_extractor.contract import CORPUS_FILE, unmet_condition
from planning_ui.plan_extractor import render_markdown as render_report
from planning_ui.views import assemble_views
from planning_ui.views.stores import assemble_stores

#: The corpus read when the caller names none: the directory the command was
#: run from. Hosted in the tooling, this package is beside no corpus — its own
#: grandparent is `scripts/services/` — so the only honest default is where
#: the caller is standing, and the contract refusal below catches a wrong one
#: by name rather than deriving an empty graph.
def default_root() -> Path:
    return Path.cwd().resolve()


#: The service's declared defaults — THE carrier. `config.template.yaml`'s
#: `planning-ui:` section is generated from `--print-default-config`, never
#: typed, so the template and the service cannot drift (Services Standard
#: § Centralized config.yaml). Kebab-case keys per that standard.
DEFAULT_CONFIG: dict[str, object] = {
    "enabled": True,
    "bind": "127.0.0.1",
    "port": 8765,
}

CONFIG_SECTION = "planning-ui"


def default_config_yaml() -> str:
    """The template section, as the scaffold writes it. Hand-rendered rather
    than dumped: the comments are part of the contract and a YAML dumper
    drops them."""
    d = DEFAULT_CONFIG
    return (
        f"# {CONFIG_SECTION} — the planning-corpus viewer, one instance per planning repo\n"
        f"{CONFIG_SECTION}:\n"
        f"  enabled: {str(d['enabled']).lower()}      # read first; false → the installer installs nothing\n"
        f"  bind: {d['bind']}       # loopback by default — a developer's process, reachable only to them\n"
        f"  port: {d['port']}             # this repo's port; override here only on a collision with another repo\n"
    )

#: The environment overrides, one per key, named as the Services Standard's
#: exemplar names gh-monitor's: `<SERVICE>_<KEY>`. Precedence is flag > env
#: > config.yaml > the defaults above.
ENV_PREFIX = "PLANNING_UI_"


class ConfigError(RuntimeError):
    """`config.yaml` exists and cannot be read as this service's settings."""


def load_service_config(root: Path) -> dict[str, object]:
    """The `planning-ui:` section of ``<root>/config.yaml``, or ``{}``.

    ABSENT IS THE DESIGNED PATH AND MALFORMED IS A REFUSAL. The file is
    deployment-scoped and gitignored: a fresh clone has the template and no
    file, and the installer writes one — so no file means "the defaults",
    never a fault. A file that exists and does not parse, or parses to
    something other than a mapping, means the operator's intent is
    unreadable, and serving on the defaults past it would put the viewer on a
    port they did not choose.

    PyYAML is imported HERE, not at module top. `serve` is the only verb with
    settings, and it runs on a developer host where the fleet already needs
    PyYAML; `--check` runs on every planning repository's CI runner, where
    nothing installs it and nothing needs it. An import at the top would make
    the merge gate depend on a parser the gate never uses.
    """
    path = root / "config.yaml"
    if not path.is_file():
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise ConfigError(
            f"{path} exists, and reading it needs PyYAML, which this python3 does not have "
            "(the fleet's own dependency: `pip install pyyaml`)."
        ) from exc
    try:
        document = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc
    if document is None:
        return {}
    if not isinstance(document, dict):
        raise ConfigError(f"{path} must be a mapping of sections, not {type(document).__name__}")
    section = document.get(CONFIG_SECTION)
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ConfigError(
            f"{path}: `{CONFIG_SECTION}:` must be a mapping, not {type(section).__name__}"
        )
    return dict(section)


def resolve_serve_settings(
    root: Path,
    *,
    bind: str | None = None,
    port: int | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, object]:
    """`enabled`, `bind` and `port` for ``serve``, resolved flag > env > file > default.

    A flag is the operator's explicit word on this one run, so it outranks
    the file; the environment outranks the file for the same reason the
    standard gives — a machine-specific override without editing it.
    """
    env = os.environ if environ is None else environ
    file = load_service_config(root)
    settings: dict[str, object] = {}
    for key, default in DEFAULT_CONFIG.items():
        value: object = file.get(key, default)
        override = env.get(ENV_PREFIX + key.upper())
        if override is not None:
            value = override
        settings[key] = value
    if bind is not None:
        settings["bind"] = bind
    if port is not None:
        settings["port"] = port
    settings["enabled"] = _as_bool(settings["enabled"], "enabled")
    settings["port"] = _as_port(settings["port"])
    settings["bind"] = str(settings["bind"])
    return settings


def _as_bool(value: object, key: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "yes", "on", "1"):
        return True
    if text in ("false", "no", "off", "0"):
        return False
    raise ConfigError(f"`{CONFIG_SECTION}.{key}` must be true or false, not {value!r}")


def _as_port(value: object) -> int:
    if isinstance(value, bool):  # `port: true` would otherwise read as port 1
        raise ConfigError(f"`{CONFIG_SECTION}.port` must be an integer, not {value!r}")
    try:
        port = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ConfigError(f"`{CONFIG_SECTION}.port` must be an integer, not {value!r}") from None
    if not 1 <= port <= 65535:
        raise ConfigError(f"`{CONFIG_SECTION}.port` must be 1–65535, not {port}")
    return port


#: DERIVED output, committed deliberately — hence not `build/` or `dist/`,
#: which read as throwaway and are conventionally git-ignored, and not
#: `generated/`, which says how the files got here rather than what they are.
#: It sits beside the corpus rather than beside this package: the artifacts
#: belong to the repository whose corpus they describe, and the package that
#: derives them is moving to the tooling.
def derived_dir(root: Path) -> Path:
    return root / "development" / "derived"




#: The viewer's derived inputs — the component neighbourhood index and the
#: sprint boards. Committed and `--check`-gated like the graph (phase 3 doc
#: § What is committed); the drawing itself is never committed.



#: The corpus inputs whose git HISTORY the decisions page reads (`git log` for
#: item ages and triage passes, `git blame` for § Sprint: Unplaced). An
#: uncommitted edit to one of these is invisible to that history, so a page
#: generated beside it reads the PREVIOUS commit's dates — and `--check` on
#: the committed result then reports drift. Warned on, never silently absorbed.
HISTORY_READ_INPUTS = ("tracked/", "development/sprints.md")


#: Artifact filename by key, in the order `--check` reports them.
ARTIFACT_NAMES: tuple[str, ...] = (
    "plan-graph.json",
    "consistency-report.md",
    "decisions.md",
    "view-inputs.json",
    "view-stores.json",
)


def artifacts(root: Path) -> dict[str, Path]:
    """Where each derived artifact lives for ``root``.

    Keyed rather than five module constants, because the constants were only
    ever correct for one repository and this package now reads any.
    """
    directory = derived_dir(root)
    return {name: directory / name for name in ARTIFACT_NAMES}


def derive(root: Path | None = None) -> ExtractionResult:
    """The single derivation every verb uses."""
    return extract(root or default_root())


def _serialise(graph: dict) -> str:
    """Stable bytes for a stable diff.

    ``sort_keys`` and a trailing newline are not cosmetic: an artifact whose
    key order wanders produces a diff on every run, and a diff that is always
    noisy is a diff nobody reads — which would cost exactly the reviewability
    §1.1 committed the artifact to buy.
    """
    return json.dumps(graph, indent=2, sort_keys=True, default=str) + "\n"


def render(result: ExtractionResult, as_of: date, root: Path) -> dict[Path, str]:
    """Every artifact from one derivation, keyed by destination.

    The store tables are their own file rather than a key in `view-inputs`:
    that one is rewritten by every planning commit in every lane, and the
    store rows change on a different rhythm and are read by one page.
    """
    where = artifacts(root)
    return {
        where["plan-graph.json"]: _serialise(result.graph),
        where["consistency-report.md"]: render_report(result) + "\n",
        where["decisions.md"]: render_decisions(assemble(result, as_of)) + "\n",
        where["view-inputs.json"]: _serialise(assemble_views(result)),
        where["view-stores.json"]: _serialise(assemble_stores(result, as_of)),
    }


#: Provenance fields that record WHERE the artifact came from, not WHAT it says.
#:
#: They are excluded from the `--check` comparison because including them makes
#: the gate unsatisfiable: generating at commit X and committing the artifact
#: creates commit Y, so the next derivation stamps Y, compares against the
#: committed X, and reports drift. No commit can ever turn that green — and this
#: check is a BLOCKING merge gate, so every pull request in the repository is
#: refused. Observed live once the gate was declared.
#:
#: The stamp stays in the file. It says which commit the graph was derived from,
#: which is exactly the question a reader asks of it. What it must not do is
#: decide whether the graph AGREES WITH THE CORPUS, which is a question about
#: content.
_PROVENANCE_NOT_COMPARED = ("commit", "commit_date")

#: The same two stamps as the markdown pages render them — one bullet each,
#: at the top of the page.
_MARKDOWN_STAMP_RE = re.compile(r"^- \*\*Commit (?:read|date):\*\* .*\n", re.MULTILINE)

#: The decisions page states the date its age columns count back to. `--check`
#: reads it back so the comparison is like with like: the page is a pure
#: function of the checkout AND this one date, and a check that substituted
#: today's date would report every committed page stale by tomorrow.
_AS_OF_RE = re.compile(r"^- \*\*Ages counted back to:\*\* (\d{4}-\d{2}-\d{2})$", re.MULTILINE)


def _comparable(payload: str) -> str:
    """A JSON artifact with its where-from stamp removed, for drift comparison.

    The graph and the view inputs both carry the same `provenance` block, so
    one rule covers both."""
    graph = json.loads(payload)
    for field in _PROVENANCE_NOT_COMPARED:
        graph.get("provenance", {}).pop(field, None)
    return _serialise(graph)


def _comparable_markdown(text: str) -> str:
    """A markdown page with its where-from stamp removed, for drift comparison."""
    return _MARKDOWN_STAMP_RE.sub("", text)


def comparable(path: Path, payload: str) -> str:
    return _comparable(payload) if path.suffix == ".json" else _comparable_markdown(payload)


def read_as_of(page: str) -> date | None:
    """The reference date a committed decisions page states, or ``None``."""
    match = _AS_OF_RE.search(page)
    return date.fromisoformat(match.group(1)) if match else None


def _uncommitted_history_inputs(root: Path) -> list[str] | None:
    """Paths under :data:`HISTORY_READ_INPUTS` with changes the history cannot see.

    Read-only ``git status``. ``None`` when the question could not be asked —
    ``git`` absent, or ``git status`` refusing (a lock held, an unreadable
    ``.git``) — which the caller says, rather than reading it as "nothing
    pending": the two are different facts and only one of them is reassuring.
    A checkout with no ``.git`` is the refusal case too, and there the answer
    is moot since there is no history for an edit to be missing from.

    During a merge, what the merge itself staged is NOT pending: the decisions
    page walks the log from ``MERGE_HEAD`` as well as ``HEAD`` (`history.py`),
    so the incoming side's commits are visible. Only an edit outside the index
    — or a file git does not know — is invisible until committed.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--", *HISTORY_READ_INPUTS],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    merging = bool(merge_heads(root))
    pending: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        index_state, worktree_state = line[0], line[1]
        if merging and index_state != "?" and worktree_state == " ":
            continue  # staged by the merge, and visible through MERGE_HEAD
        pending.append(line[3:])
    return pending


#: Everything the derivation reads, for the working-tree note above. Not
#: `development/derived/` — that is the output, and it is always pending
#: right after a generate.
CORPUS_INPUTS = ("development/", "standards/", "tracked/", CORPUS_FILE)


def _uncommitted_corpus_edits(root: Path) -> list[str]:
    """Corpus inputs whose working-tree state differs from the commit.

    MEASURED, ON THE DAY THE VIEWER WAS ADOPTED IN A SHARED CHECKOUT: another
    session's uncommitted phase-doc edit was read into the artifacts, the
    artifacts were committed, and `--check` on a fresh clone of that very
    commit named all five STALE. The generator cannot refuse — a working tree
    is a legitimate thing to look at — but it can say what it read. ``[]``
    when git cannot answer: the history note above already covers that case.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--", *CORPUS_INPUTS],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    derived = _rel(derived_dir(root), root) + "/"
    return [
        line[3:] for line in result.stdout.splitlines()
        if line.strip() and not line[3:].startswith(derived)
    ]


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="planning-ui.sh",
        description="Derive the planning-corpus views from this checkout.")
    ap.add_argument("verb", nargs="?", choices=["serve"],
                    help="`serve`: start the process that serves the two diagram "
                         "pages from this checkout, deriving afresh on every "
                         "request. With no verb, generate the committed artifacts.")
    ap.add_argument("--bind", metavar="ADDR",
                    help="(serve) address to listen on, overriding config.yaml; the "
                         f"loopback by default ({DEFAULT_CONFIG['bind']}) — this is a "
                         "developer's process, reachable only to them")
    ap.add_argument("--port", type=int,
                    help="(serve) port to listen on, overriding config.yaml "
                         f"(default: {DEFAULT_CONFIG['port']})")
    ap.add_argument("--check", action="store_true",
                    help="derive and compare against the committed artifacts; "
                         "exit 1 on drift, naming each artifact that drifted, "
                         "and write nothing")
    ap.add_argument("--repo-root", metavar="PATH",
                    help="the planning repository to read (default: the one this "
                         "package sits in). Refused by name if it does not "
                         "satisfy the corpus contract")
    ap.add_argument("--print-default-config", action="store_true",
                    help="print this service's config.yaml section with its defaults "
                         "and exit; the scaffold generates config.template.yaml from it")
    ap.add_argument("--as-of", type=date.fromisoformat, metavar="YYYY-MM-DD",
                    help="the date the decisions page's age columns count back "
                         "to (default: today in UTC when generating; the "
                         "committed page's own date when checking)")
    args = ap.parse_args(argv)

    if args.print_default_config:
        # Before the root is resolved: the defaults are a property of the
        # service, not of any repository, and the scaffold asks for them
        # before a repository exists.
        print(default_config_yaml(), end="")
        return 0

    root = Path(args.repo_root).resolve() if args.repo_root else default_root()
    unmet = unmet_condition(root)
    if unmet:
        # Named, never read as an empty corpus. A missing `development/` is not
        # zero components.
        print(f"REFUSED {root} is not a planning repository: {unmet}")
        return 2

    if args.verb == "serve":
        if args.check:
            ap.error("`serve` derives per request and checks nothing; drop --check")
        try:
            settings = resolve_serve_settings(root, bind=args.bind, port=args.port)
        except ConfigError as exc:
            print(f"REFUSED {exc}")
            return 2
        if not settings["enabled"]:
            # The master kill switch, read before anything is bound. Exit 0:
            # a deliberately disabled service is a configuration state, not a
            # failure (Services Standard § Master kill switch).
            print(f"{CONFIG_SECTION} is disabled in {root / 'config.yaml'} (`enabled: false`); nothing to serve.")
            return 0
        from planning_ui.serve import serve

        return serve(settings["bind"], settings["port"], root)

    where = artifacts(root)
    decisions = where["decisions.md"]
    if args.check:
        as_of = args.as_of or (read_as_of(decisions.read_text()) if decisions.exists() else None)
        if as_of is None:
            # Either the page is missing or it no longer states its date —
            # both mean there is nothing to compare like with like.
            as_of = datetime.now(tz=timezone.utc).date()
    else:
        as_of = args.as_of or datetime.now(tz=timezone.utc).date()

    rendered = render(derive(root), as_of, root)

    if not args.check:
        derived_dir(root).mkdir(parents=True, exist_ok=True)
        for path, payload in rendered.items():
            path.write_text(payload)
            print(f"wrote {_rel(path, root)}")
        pending = _uncommitted_history_inputs(root)
        if pending is None:
            print(
                f"NOTE could not ask git whether {', '.join(HISTORY_READ_INPUTS)} carry "
                f"uncommitted changes; {_rel(decisions, root)} reads their history, so confirm "
                "they are committed before committing the artifacts."
            )
        elif pending:
            print(
                f"NOTE {_rel(decisions, root)} reads git history, and these inputs have "
                f"uncommitted changes the history cannot see yet: {', '.join(pending)}. "
                "Commit them, then run `planning-ui.sh` again before committing the "
                "artifacts, or `--check` will report the page stale."
            )
        edited = _uncommitted_corpus_edits(root)
        if edited:
            print(
                f"NOTE the artifacts describe this WORKING TREE, and it differs from the commit: "
                f"{', '.join(edited[:5])}{' …' if len(edited) > 5 else ''} carr"
                f"{'ies' if len(edited) == 1 else 'y'} uncommitted changes. Committed as they "
                "are, `--check` on the committed tree — a fresh clone, the CI runner — reads "
                "every artifact STALE. Commit those edits first, or generate from a clean tree."
            )
        return 0

    drifted = 0
    for path, payload in rendered.items():
        if not path.exists():
            print(f"MISSING {_rel(path, root)} — run `planning-ui.sh`")
            drifted += 1
            continue
        if comparable(path, path.read_text()) != comparable(path, payload):
            print(f"STALE {_rel(path, root)} — the corpus has moved since it was generated. "
                  f"Run `planning-ui.sh` and commit.")
            drifted += 1
            continue
        print(f"current {_rel(path, root)}")
    return 1 if drifted else 0
