"""Shared I/O for the assistant edge's workflows — promoted per §10.1 rule 3.

Sits at module level because more than one workflow uses it: consumer count
decides, never taste. Anything here is shared BY DEFINITION, so a reader never
opens a file to learn its scope.

NOT IDEMPOTENT (§7.1 / addendum §A1): these push commits and open PRs. Under
Temporal a retry is a NEW ATTEMPT, not a replay — register with a retry policy
that reflects that.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import os
import uuid
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

_WORKFLOWS = Path(__file__).resolve().parents[3]          # scripts/workflows
_SHARED_PROMPTS = Path(__file__).resolve().parent / "prompts"

PR_URL = re.compile(r"https://github\.com/[^\s)]+/pull/(\d+)")


def v1_constant(script: str, name: str) -> str:
    """Read a constant from the V1 bash script rather than re-declaring it.

    THIS FUNCTION EXISTS BECAUSE RE-DECLARATION CAUSED THREE PRODUCTION FAILURES.
    The V2 port restated V1's constants and contracts instead of deriving from
    them, so divergence was silent and only surfaced at runtime — most expensively
    when a draft ran at MAX_TURNS=120 against V1's 250 and burned a full budget
    producing nothing recoverable. V1's own logs already held the answer: the same
    task class had completed in 130 turns.

    Deriving makes divergence impossible rather than merely detectable. Delete
    this only when the V1 script it reads is deleted.

    V1 SCRIPTS LIVE IN TWO PLACES and the name is searched in both. Children sit
    in `children/`; top-level workflows sit at the workflows root. An earlier
    version branched on whether the name contained a "/" and could resolve
    NEITHER — `v1_constant("plan-revision.sh", ...)` looked only under
    `children/`, and the `"../research.sh"` spelling one caller adopted to work
    around that went to `scripts/research.sh`, which does not exist. That caller
    never invoked it, so the break stayed latent; the next one to try would have
    had to re-declare the constant, which is the failure this whole function
    exists to prevent.

    PASS A BARE FILENAME. Widening the search to two locations also made `../`
    spellings start working, which is worse than the raise they replaced: the
    first candidate `children/../research.sh` resolves through a real directory
    to a real file, so a stale declaration nobody calls turns from a loud
    FileNotFoundError into a quiet wrong answer. That is not hypothetical — it
    is why `research_write_workflow.py` now carries an explicit comment saying
    it has no `V1_SCRIPT` and why one must not be added back. Relative spellings
    are not part of this contract; both locations are searched for you.
    """
    for candidate in (_WORKFLOWS / "children" / script, _WORKFLOWS / script):
        if candidate.exists():
            path = candidate
            break
    else:
        raise FileNotFoundError(
            f"V1 script not found for constant derivation: {script} is in neither "
            f"{_WORKFLOWS / 'children'} nor {_WORKFLOWS}"
        )
    m = re.search(rf"^{name}=(\S+)", path.read_text(), re.M)
    if not m:
        raise ValueError(f"{name} not found in {path} — V1 changed shape; do not guess a value")
    return m.group(1).strip("\"'")


def worktree_add(repo_root: Path, name: str, ref: str) -> Path:
    """Create an isolated worktree, matching V1's behaviour exactly.

    ISOLATION IS AN INVARIANT, NOT A PARAMETER. An earlier V2 skipped the
    worktree on `--pr` runs via a ternary, which put a run directly on the
    operator's main working tree — a live host here. A run dying mid-write would
    leave that tree dirty on a checked-out foreign branch with no discard path.
    V1 always creates one (`git worktree add -f` on the PR branch); so does this.

    A FAILED FETCH IS FATAL WHEN THE REF IS A REMOTE ONE. V1 ran its fetch under
    `set -euo pipefail`, so a fetch that failed aborted the script. Here it was
    unchecked, and the silent case is the dangerous one: when `origin/<branch>`
    already exists locally from an earlier run, `git worktree add` then SUCCEEDS
    against stale content and the run plans on top of a base that has moved —
    the kind of wrong answer that gets acted on. The check is scoped to
    `origin/`-prefixed refs because the other callers pass a local ref (`HEAD`,
    a bare branch name) that resolves without the network, and V1's own
    new-branch path did no fetch at all.

    STRIP THE PREFIX, NOT THE SUBSTRING. `removeprefix` and not `replace` here:
    branch names legitimately contain "origin/" mid-string (`sync-origin/main`,
    `team/origin/legacy-migration`), and `replace` would fetch a ref that does
    not exist. Paired with the fatal check above that turns a mangled name into
    a hard failure whose message names the wrong branch — wrong AND misleading.
    """
    wt = repo_root / ".claude" / "worktrees" / name
    remote_branch = ref.removeprefix("origin/")
    f = subprocess.run(["git", "fetch", "-q", "origin", remote_branch],
                       cwd=str(repo_root), capture_output=True, text=True)
    if f.returncode != 0 and ref.startswith("origin/"):
        raise RuntimeError(
            f"git fetch origin {remote_branch} failed: {f.stderr.strip()}. "
            f"Refusing to cut a worktree from {ref} — a stale local copy of that ref "
            f"would succeed here and put the run on a base that has already moved."
        )
    r = subprocess.run(["git", "worktree", "add", "-f", str(wt), ref],
                       cwd=str(repo_root), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"worktree add failed for {ref}: {r.stderr.strip()}")
    return wt


def observe_outcome(worktree: Path, branch: str | None = None) -> str:
    """Read what git ACTUALLY did. Never assert a negative without reading.

    THIS EXISTS BECAUSE A FAILURE BANNER LIED. A run that exhausted its turn cap
    printed "NOTHING was committed or pushed" — and it had committed and pushed,
    9 files and +798/-111, landing on the PR branch. The operator read the banner,
    concluded the work was lost, and dispatched a second full-budget run against
    work that was already there.

    The banner asserted what the harness BELIEVED rather than reading what git
    DID, because the turn-cap path exits before observing state. A false negative
    on the failure path is worse than a crash: a crash is obviously wrong, while
    a confident wrong answer gets acted on.

    Returns a human-readable observation. If it cannot determine the state it
    SAYS SO — it never reports a negative it did not verify.
    """
    def _git(*args: str) -> tuple[int, str]:
        r = subprocess.run(["git", *args], cwd=str(worktree),
                           capture_output=True, text=True)
        return r.returncode, r.stdout.strip()

    if not worktree.exists():
        return f"Worktree {worktree} no longer exists — cannot determine what landed."

    lines: list[str] = []
    rc, head = _git("log", "-1", "--format=%h %s")
    if rc != 0:
        return f"Could not read git state in {worktree}. Inspect it by hand before re-running."
    lines.append(f"HEAD in worktree: {head}")

    rc, dirty = _git("status", "--porcelain")
    lines.append(f"Uncommitted changes: {'YES — ' + str(len(dirty.splitlines())) + ' file(s)' if dirty else 'none'}")

    if branch:
        rc, unpushed = _git("log", f"origin/{branch}..HEAD", "--oneline")
        if rc == 0:
            lines.append(
                f"Commits NOT yet on origin/{branch}: {len(unpushed.splitlines()) if unpushed else 0}"
                + (f"\n  {unpushed}" if unpushed else "")
            )
        else:
            lines.append(f"Could not compare against origin/{branch} — do not assume either way.")

    lines.append(f"Worktree retained at: {worktree}")
    return "\n".join(lines)


def load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"prompt file missing: {path}")
    return path.read_text()


def shared_prompt(name: str) -> str:
    """Load a promoted, module-level prompt fragment by stem."""
    return load_prompt(_SHARED_PROMPTS / f"{name}.md")


def render(template: str, values: dict[str, str], *,
           opaque: frozenset[str] = frozenset()) -> str:
    """Substitute ${NAME} placeholders and fail loud on any left over.

    Deliberately not str.format/f-strings: these prompts carry JSON, yaml and
    shell, all full of literal braces. An unsubstituted placeholder reaches the
    model as an instruction about a variable, so it raises rather than ships.

    `opaque` names keys whose VALUE IS OPERATOR CONTENT rather than a prompt
    fragment. Those are inserted last, in one pass, and never re-scanned.
    """
    # PASS 1 — fragments only, substituted TO A FIXED POINT. A prompt fragment
    # can itself contain placeholders (a stages file carries ${PR_NUMBER}), so a
    # single pass leaves them unresolved whenever the block is inserted after
    # its own placeholders were processed. Bash had no such problem: it expanded
    # the whole string at once. Iterate until stable, bounded so a
    # self-referential fragment fails loudly rather than spinning.
    fragments = {k: v for k, v in values.items() if k not in opaque}
    out = template
    for _ in range(10):
        before = out
        for k, v in fragments.items():
            out = out.replace("${" + k + "}", str(v))
        if out == before:
            break
    else:
        raise ValueError("prompt substitution did not converge — check for a self-referential fragment")

    # THE GUARD RUNS BEFORE OPERATOR CONTENT GOES IN, and that ordering is the
    # whole point. [A-Z_0-9] — DIGITS MATTER: an earlier [A-Z_]+ silently missed
    # ${STAGES_1_TO_4}, so a prompt shipped with its entire stage body replaced
    # by a literal placeholder and this check raised nothing.
    # An opaque key is legitimately still present here — pass 2 fills it — so
    # exclude those and only those. Everything else must already be resolved.
    still_expected = {"${" + k + "}" for k in opaque}
    leftover = sorted(set(re.findall(r"\$\{[A-Z_][A-Z_0-9]*\}", out)) - still_expected)
    if leftover:
        raise ValueError(f"unsubstituted prompt placeholders: {leftover}")

    # PASS 2 — operator content, ONE pass, never re-scanned and never checked.
    #
    # WHY THIS IS SEPARATE. A task file is prose a human wrote, and prose about
    # this system routinely contains a literal ${LIKE_THIS} token — describing
    # the placeholder bug, quoting a prompt, explaining the guard. Scanned with
    # everything else, that token either gets SUBSTITUTED into the model's task
    # statement (silently changing what was asked) or trips the leftover check
    # and kills the dispatch. Both happened: two runs died the same afternoon,
    # both on briefs that were *describing* this exact mechanism, and there was
    # no way to escape a token.
    #
    # Inserting last and not re-scanning means operator text is passed through
    # LITERALLY, which is the only correct behaviour for content the system did
    # not author.
    for k in opaque:
        if k in values:
            out = out.replace("${" + k + "}", str(values[k]))
    return out

def extract_pr_url(output: str) -> str | None:
    """Last PR URL in a run's output — the completion contract's payload.

    Last, not first: a run may mention an existing PR before opening its own.
    """
    matches = [m.group(0) for m in PR_URL.finditer(output)]
    return matches[-1] if matches else None


def claude_log_path(repo_root: Path, model_key: str, *, run_id: str) -> Path:
    """RESERVE a fresh log path for one invocation. Unique by construction.

    THE LOG IS THE CHANNEL, and that is not obvious from the transport ruling.
    `structured_output` rides in the CLI's own stdout, so the CHILD writes
    nothing outside its worktree — but `run-claude.sh` redirects that stdout
    into $LOG_FILE, so a path exists and the PARENT owns it. "The transport has
    no staleness class" is a claim about the transport; the fleet's channel is
    transport plus plumbing (`phase3_typed_exit_record.md` step 3).

    FRESHNESS IS ENFORCED, NOT ASSUMED. `build_workflow` invokes `review-pr`
    twice in one run, either side of the loop-back. If one path were reused, a
    second child that died before writing would leave pass 1's record in place
    and the parent would route on a pass that produced nothing — making the
    absent-record arm unreachable in exactly the scenario it exists for.

    IT WAS ENFORCED ONE LEVEL ABOVE WHERE IT WAS CLAIMED, AND THAT IS THIS
    FUNCTION'S OWN DEFECT CLASS. For one pass this checked `exists()` and
    returned, RESERVING NOTHING: the file is created later, by a DIFFERENT
    PROCESS, at `run-claude.sh`'s `> "$LOG_FILE"` — `O_TRUNC`. The name was
    `{model_key}-{second-granular stamp}`, and `MODEL_KEY` is a constant shared
    by every PR that workflow reviews, while `run_review_pr` sets
    `worktree = repo_root` and `build_workflow` passes `repo_root` — so the log
    directory is SHARED ACROSS CONCURRENT DISPATCHES, not per-worktree. Two
    dispatches entering in the same wall-clock second both saw no file, both
    proceeded, and one truncated the other's log. R5's identity check stops the
    foreign record deciding a merge, so the observable outcome was a COMPLETED
    run binned as `record_absent` — indistinguishable from a mid-stream death in
    the very per-reason rate this phase exists to produce. Corrupted in the
    direction that looks normal.

    TWO INDEPENDENT FIXES, BOTH DELIBERATE:

    1. **The name carries the run nonce, so it is unique BY CONSTRUCTION.** Not
       a wider timestamp — a finer clock only shrinks the window that a
       check-then-create leaves open. `run_id` is the identity the parent
       already issues and the child already echoes into the record, so the log's
       filename now greps against the record inside it; truncating the nonce
       would break exactly that.
    2. **The name is RESERVED atomically** (`O_CREAT|O_EXCL` via
       `touch(exist_ok=False)`), because check-then-create across a process
       boundary is TOCTOU by construction whatever the name looks like. This is
       what makes the docstring's promise true rather than probable: on the
       residual collision the allocation FAILS LOUD instead of silently
       truncating. The reserved file is empty, which every reader here already
       handles — `_log_events` yields nothing from it and R2 fires.

    The `FileExistsError` is an `OSError`, which `run_review_pr` catches as an
    operator-facing runtime state rather than a traceback.
    """
    log_dir = repo_root / ".claude" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = log_dir / f"{model_key}-{stamp}-{run_id}.jsonl"
    try:
        path.touch(exist_ok=False)
    except FileExistsError as exc:
        raise FileExistsError(
            f"refusing to reuse an existing run log: {path}. A second invocation "
            f"landing on one path either truncates the first run's record or leaves "
            f"a stale one for this run's parent to read. The name carries this "
            f"run's nonce, so reaching this means the nonce was reused."
        ) from exc
    return path


def _log_events(log_file: Path) -> Iterator[dict]:
    """Decoded JSONL events from a run log, in order. Missing log yields nothing.

    ONE DECLARATION OF "how a run log is read", because the invariant is not
    obvious and both readers below depend on it: the stream interleaves non-JSON
    on stderr paths, so a routing read must SKIP a malformed line rather than
    raise. Losing the record to a stray warning would route a clean run to a
    human for a reason that has nothing to do with the run.
    """
    if not log_file.exists():
        return
    for line in log_file.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def result_event(log_file: Path) -> dict | None:
    """The CLI's `result` event from a run log, or None if the log has none.

    None is a REAL answer, not an error: a run killed before it emitted one has
    no result event, and the fail-safe contract's R2 fires on it — `record_absent`,
    because no event implies no key.
    """
    found = None
    for event in _log_events(log_file):
        if event.get("type") == "result":
            found = event          # last wins; there is one, but do not assume it
    return found


def assistant_text(log_file: Path) -> str:
    """This run's own assistant text blocks, in order, newline-joined.

    THIS IS WHERE THE MODEL'S PROSE LIVES WHEN A SCHEMA IS DECLARED. Measured on
    CLI 2.1.224: `--json-schema` replaces `.result` with the serialised
    structured output, so a prose shadow read from `.result` would find nothing
    on every conforming run and report a disagreement that is an artifact of
    where it looked. `run-claude.sh`'s completion gate reads the same surface,
    for the same reason.

    SUB-AGENT TURNS ARE EXCLUDED. A `Task` sub-agent's assistant events carry a
    `parent_tool_use_id`; the top-level model's carry null. A sub-agent quoting
    or proposing a verdict line is not this run's verdict, and admitting one
    would let a nested agent decide the parent's route.
    """
    chunks: list[str] = []
    for event in _log_events(log_file):
        if event.get("type") != "assistant":
            continue
        if event.get("parent_tool_use_id") is not None:
            continue
        for block in (event.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                chunks.append(block.get("text", ""))
    return "\n".join(chunks)


def append_parent_route(log_file: Path, event: dict) -> None:
    """Append the PARENT-COMPUTED stratum to the run log, as one JSONL event.

    WITHOUT THIS THE COMPUTED ABSTENTION ARM HAS NO RATE.
    `phase3_typed_exit_record.md` step 4 specifies both arms as predicates over
    a run's events — the asserted arm reads `structured_output.hold_kind`, which
    the child writes, and the computed arm reads `routed_outcome` grouped by
    `undetermined_reason`, which NOTHING wrote. `exit-protocol.md` §2.3's two
    parent-computed fields lived only in a return value that dies with the
    process and in free-text operator notes, so the arm the protocol calls the
    reliable one was the one Phase 4 could not count.

    The log is the natural home: it already carries the child's stratum, so both
    predicates evaluate over one artifact rather than two. `type` is namespaced
    away from the CLI's own event types so a future CLI cannot collide with it,
    and appending keeps the CLI's own stream byte-identical.

    WHAT THIS WRITES IS FROZEN WHILE PHASE 4 IS GATED ON IT.
    `phase4_fleet_migration.md` reads the run set these events produce, so the
    keys and the `parent_route` type string are not a refactoring surface. A
    later phase adding its OWN observable adds its OWN event type beside this
    one — see `append_convergence` — rather than widening this payload, and
    `test_exit_record.py` asserts the line this function writes byte for byte.
    """
    _append_run_event(log_file, "parent_route", event)


def append_convergence(log_file: Path, event: dict) -> None:
    """Append Phase 5's COMPUTED CONVERGENCE observable, as its own JSONL event.

    A SEPARATE EVENT TYPE, NOT A WIDER `parent_route`. Phase 4 is gated on the
    run set `append_parent_route` produces, so the cheapest way to guarantee
    this addition disturbs nothing is for it to share no payload with that one.
    The two join on `run_id`, which both carry.

    WITHOUT THIS THE PREDICATE HAS NO DENOMINATOR. The convergence assessment
    lives in a return value that dies with the process; the archive's
    `pr_review:` blocks carry the model's ASSERTED flag but nothing carries the
    computed one, so an agreement rate between the two could only ever be
    reconstructed by a second offline reader — the duplicated-parser defect this
    component exists to remove. That is the same gap
    `phase3_typed_exit_record.md` step 4 closed for the computed abstention arm,
    and it is closed here at the same time as the signal is first emitted rather
    than a phase later.
    """
    _append_run_event(log_file, "convergence", event)


def _append_run_event(log_file: Path, event_type: str, event: dict) -> None:
    """One appender for every parent-written run-log event.

    The two public callers above differ only in their `type`, and typing the
    open-append-serialise sequence twice is how the second one acquires a
    different encoding or a missing newline. `type` is written FIRST and from
    the parameter, so a caller cannot shadow it through `event`.
    """
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": event_type, **event}) + "\n")


def run_claude(prompt: str, *, model_key: str, completion_pattern: str,
               repo_root: Path, worktree: Path | None = None,
               max_turns: int = 120, verbose: bool = False,
               exit_record_schema: str | None = None,
               log_file: Path | None = None) -> str:
    """Invoke the model via the existing bash activity.

    Delegates rather than reimplementing model invocation, logging and the
    completion-contract check — one implementation of the contract, not two
    that can disagree mid-migration.

    TWO LOCATIONS, TWO JOBS. `repo_root` is where LOGS live and MUST be the real
    repository — never a worktree, or the log is deleted with the worktree it sat
    inside and cost accounting for that leg becomes impossible. `worktree` is
    where the model EXECUTES. An earlier version passed the worktree as
    repo_root, which buried every V2 log and reproduced a defect already reported
    against review-pr.

    CONTRACT ORDER MATTERS. `run-claude.sh` asserts LOG_FILE, MAX_TURNS,
    VERBOSE, FORMATTER and MODEL_KEY with `: "${VAR:?...}"` at SOURCE time, so
    every one must be exported BEFORE the source line. An earlier version
    sourced first and assigned after, which tripped the guard at source time and
    exited 127 — the delegation did not satisfy the contract it delegated to.
    """
    runner = _WORKFLOWS / "activities" / "run-claude.sh"
    formatter = _WORKFLOWS / "common" / "format-stream.sh"
    for required in (runner, formatter):
        if not required.exists():
            raise FileNotFoundError(f"required activity not found: {required}")

    if ".claude/worktrees" in str(repo_root):
        raise ValueError(
            f"repo_root must be the REPOSITORY, not a worktree: {repo_root}. "
            f"Logs written inside a worktree are deleted with it."
        )
    cwd = worktree or repo_root
    # A caller that needs to READ the record allocates the path itself, so it
    # knows where to read it from AND can bind the log's name to the nonce it
    # issued. A caller that does not still gets a name unique by construction —
    # the nonce is generated here rather than defaulted away, because a default
    # is how the shared-name collision got written in the first place.
    log_file = log_file or claude_log_path(repo_root, model_key, run_id=uuid.uuid4().hex)

    env = {
        **os.environ,
        "LOG_FILE": str(log_file),
        "MAX_TURNS": str(max_turns),
        "VERBOSE": "true" if verbose else "false",
        "FORMATTER": str(formatter),
        "MODEL_KEY": model_key,
        "COMPLETION_PATTERN": completion_pattern,
    }
    # SET **OR CLEARED**, never merely set. `env` starts from `os.environ`, so
    # an ambient `EXIT_RECORD_SCHEMA` — exported by an operator, or inherited by
    # a dispatch launched from inside a schema-declaring run — would reach the
    # child even when this caller declared none. That hands `--json-schema` to
    # the FROZEN V1 fleet (`exit-protocol.md` §7), whose whole guarantee is that
    # its command line is byte-identical when the variable is unset, and flips
    # its completion gate onto the assistant-text branch, where V1's
    # `COMPLETION_PATTERN` (a PR URL) does not appear — turning successful V1
    # runs into false early-stop failures. "Unset" has to be something this
    # caller controls, not something the environment gets a vote on.
    if exit_record_schema:
        env["EXIT_RECORD_SCHEMA"] = exit_record_schema
    else:
        env.pop("EXIT_RECORD_SCHEMA", None)
    # STREAM AND CAPTURE. `capture_output=True` produced a 70-minute run with
    # zero visible output, so --verbose did nothing and an operator could not
    # distinguish a working run from a hung one — the reported symptom was
    # "it's not working" when it was. Popen lets output be watched live AND
    # collected for the completion-contract check.
    print(f"→ {model_key}  log: {log_file}", flush=True)
    print(f"→ {model_key}  exec: {cwd}  (max_turns={max_turns})", flush=True)
    proc = subprocess.Popen(
        ["bash", "-c", f'source "{runner}"; run_claude "$1"', "_", prompt],
        cwd=str(cwd), env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    captured: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        captured.append(line)
        if verbose:
            sys.stdout.write(line)
            sys.stdout.flush()
    code = proc.wait()
    output = "".join(captured)

    if code != 0:
        # OBSERVE before reporting. A turn-cap exit may have committed and
        # pushed real work; asserting otherwise costs a duplicate full-budget run.
        raise RuntimeError(
            f"{model_key} FAILED (exit {code}). Log: {log_file}\n"
            f"--- observed git state (read, not assumed) ---\n"
            f"{observe_outcome(cwd)}\n"
            f"--- end observed state ---\n"
            f"{output[-2000:]}"
        )
    return output


def gh(args: list[str], repo_root: Path) -> str:
    """Run `gh` INSIDE the target repo rather than passing --repo.

    `--repo` in our CLIs is a FILESYSTEM PATH; `gh --repo` wants an OWNER/NAME
    slug. Conflating them is how an earlier version passed None to gh and let it
    derive the repo from the process cwd — which is exactly what the flag's own
    documentation promises never happens. Setting cwd keeps the identity
    explicit without needing to parse a remote URL into a slug.
    """
    r = subprocess.run(["gh", *args], cwd=str(repo_root),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed in {repo_root}: {r.stderr.strip()}")
    return r.stdout


def gh_json(args: list[str], repo_root: Path):
    """`gh` plus its parse, so a `gh` FAILURE IS ONE EXCEPTION TYPE.

    ONE FAILURE SURFACE, BECAUSE CALLERS GUARD AGAINST A TYPE AND NOT AN EVENT.
    `gh` above raises `RuntimeError` on a non-zero exit and validates nothing
    about stdout, so every caller that then ran `json.loads` had a SECOND way to
    fail — `json.JSONDecodeError`, which is a `ValueError` and shares no base
    class with the first. That is not a hypothetical distinction: the retry in
    `review_pr_workflow._read_thread_for_invariant` exists precisely so a flaky
    `gh` read cannot discard a completed review, it catches `RuntimeError`, and a
    zero-exit reply with a truncated or non-JSON body therefore skipped the retry
    entirely — zero attempts — and crashed the parent build loop, which catches
    `(RuntimeError, FileNotFoundError)` and not `ValueError`. The fix belongs
    HERE rather than in each caller's except-clause: a caller cannot be expected
    to know which exception families this function's implementation can emit, and
    the next `gh` reader would have re-acquired the same gap by writing the
    obvious two lines.

    The raw body is quoted (truncated) into the message, because "expecting value
    at line 1 column 1" says nothing about whether the answer was an HTML error
    page, an empty string or a half-written array.
    """
    raw = gh(args, repo_root)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"gh {' '.join(args)} in {repo_root} exited 0 but did not return JSON: "
            f"{exc}. First 200 bytes of the reply: {raw[:200]!r}"
        ) from exc


def pr_branch(pr_number: str, repo_root: Path) -> str:
    return gh(["pr", "view", pr_number, "--json", "headRefName",
               "-q", ".headRefName"], repo_root).strip()
