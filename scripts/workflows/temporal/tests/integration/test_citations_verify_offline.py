"""A verify pass over a real journal on THIS machine, and it must not need a network.

TWO TIERS, TWO QUESTIONS. The unit tier proves each rule in isolation against
fixtures it built; this tier asks whether the whole thing works against whatever
the operator's journal actually holds — the same split `test_a_real_bag_validates`
keeps for the bag validator one question over.

⚠ REQUIREMENT 2 IS ONLY PARTIALLY MET BY THIS FILE AND THE GAP IS NAMED RATHER
THAN PAPERED OVER. The requirement asks for a demonstration "on a run captured at
read time", and no run in this fleet captures at read time yet: a research
citation is read by a model inside a `claude -p` child through the model's own
tooling, and nothing routes that read through fleet code. Phase 2 rules that
boundary onto post-exit harvest, so what exists today to verify is a bag this
tier writes through the real capture activity. That IS a read-time capture for
everything that goes through the boundary — and it is NOT the same as a research
run's own sources having gone through it. The phase's PR says so plainly.

SKIPPED, DISTINCTLY FROM PASSING, WHERE THERE IS NO JOURNAL. A clone has no
journal and there is nothing for this tier to read; a skip and a pass must never
look alike.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from modules.journal.bag import BAGIT_FILE, open_bag
from modules.journal.content_activities import capture_fetched_source
from modules.journal.content_store import object_path
from modules.journal.journal_activities import load_journal_config
from modules.journal.root import JournalRootError, resolve_journal_root
from modules.journal.verify import (EXIT_MISSING, EXIT_OK, EXIT_SPAN_MISSING,
                                    EXIT_TAMPERED, MISSING, SPAN_MISSING,
                                    TAMPERED, VERIFIED, verify_bag)

# `parents[2]`, not `[1]`: this file sits at `tests/integration/`, so the
# component root is two levels up. The component conftest resolves `[1]` because
# it sits one level shallower, and copying its expression here pointed the
# entrypoint at `tests/scripts/` — which python reported as an exit code with no
# output, a failure that names nothing.
COMPONENT_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = COMPONENT_ROOT / "scripts" / "verify_citations.py"

assert ENTRYPOINT.is_file(), f"the entrypoint under test is not at {ENTRYPOINT}"

PAGE = (b"<html><body><p>Every mature system draws this line, and each drew it "
        b"after being hurt.</p></body></html>\n")
QUOTE = "Every mature system draws this line, and each drew it after being hurt."


def _operator_bags() -> list[Path]:
    """Bags under the root THIS machine's config resolves to, or an empty list.

    ⚠ RESOLVED AT MODULE SCOPE, AND THAT IS LOAD-BEARING RATHER THAN STYLE.
    `tests/conftest.py` installs a session-wide autouse fixture that repoints
    `journal_activities.CONFIG_PATH` at a sandbox, so that the suite can never
    write into the operator's journal. Asking for the root INSIDE a test body
    therefore returns the sandbox, and this tier would skip with "no journal on
    this machine" on a machine holding forty-eight bags — a vacuous pass wearing
    a skip's clothes. Module scope runs at collection, before the fixture, which
    is exactly how `test_a_real_bag_validates.py` beside this file does it.
    (Measured: this file shipped the inside-the-body version first and skipped
    silently while `verify_citations.py` found 48 bags from the command line.)
    """
    try:
        root = resolve_journal_root(config=load_journal_config(), create=False)
    except (JournalRootError, RuntimeError):
        return []
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir()
                  if p.is_dir() and (p / BAGIT_FILE).is_file())


BAGS = _operator_bags()


@pytest.mark.skipif(not BAGS, reason="no journal on this machine — no dispatch has run here")
def test_every_bag_on_this_machine_verifies_its_citations() -> None:
    """The real corpus, whatever it holds. Today most bags cite nothing.

    A bag with no citations is reported as zero and not as a failure, so a green
    run here is compatible with the fleet not yet capturing anything — which is
    honest, and is exactly why the offline demonstration below builds its own
    corpus rather than asserting over this one. What this tier does prove today
    is that the reader survives every real bag on disk: a malformed or
    unreadable citation file anywhere under the root is a structural finding.
    """
    bad = []
    for path in BAGS:
        report = verify_bag(path)
        if not report.ok:
            bad.append((path.name, report.counts(), report.structural))
    assert not bad, f"citations failed to verify in the operator's journal: {bad}"


@pytest.mark.skipif(not BAGS, reason="no journal on this machine — no dispatch has run here")
def test_this_tier_actually_READ_the_operators_journal() -> None:
    """VACUITY CONTROL. A sweep over an empty list passes exactly like a clean one.

    The test above asserts an ABSENCE across a collection, which is the shape
    that reports success when its scoping is wrong — and that is not
    hypothetical here, it is what this file shipped. Naming a non-zero count is
    what makes the absence mean something.
    """
    assert len(BAGS) > 0
    assert all((path / BAGIT_FILE).is_file() for path in BAGS)


def _demo_bag(root: Path):
    """A bag holding one of each outcome, built through the real capture activity."""
    bag = open_bag(root, "verify-offline-demo")
    good = capture_fetched_source(bag=bag, stage="draft", claim_id="good",
                                  quote=QUOTE, source_ref="https://example.org/a",
                                  data=PAGE)
    absent = capture_fetched_source(bag=bag, stage="draft", claim_id="absent",
                                    quote=QUOTE, source_ref="https://example.org/b",
                                    data=PAGE + b"<!-- second source -->")
    altered = capture_fetched_source(bag=bag, stage="draft", claim_id="altered",
                                     quote=QUOTE, source_ref="https://example.org/c",
                                     data=PAGE + b"<!-- third source -->")
    wrong = capture_fetched_source(bag=bag, stage="critic", claim_id="wrongquote",
                                   quote="a sentence that was never on that page",
                                   source_ref="https://example.org/d",
                                   data=PAGE + b"<!-- fourth source -->")

    object_path(bag.path, absent.page_content_hash).unlink()

    target = object_path(bag.path, altered.page_content_hash)
    data = bytearray(target.read_bytes())
    data[0] ^= 0x01
    target.write_bytes(bytes(data))
    return bag, (good, absent, altered, wrong)


def test_a_bag_holding_one_of_each_outcome_reports_all_four(tmp_path: Path) -> None:
    from modules.journal.bag import DIR_MODE
    root = tmp_path / "journal"
    root.mkdir(mode=DIR_MODE)
    bag, _ = _demo_bag(root)
    counts = verify_bag(bag.path).counts()
    assert counts == {VERIFIED: 1, MISSING: 1, TAMPERED: 1, SPAN_MISSING: 1}


# --- the network-off demonstration ----------------------------------------------

_DENY_SOCKET_C = r"""
#define _GNU_SOURCE
#include <errno.h>
#include <netdb.h>
#include <sys/socket.h>

/* Denies the process the ability to reach a network, below the language the
 * code under test is written in. Not a mock: the C library entry points
 * themselves refuse, so nothing importable can route around them. */
int socket(int domain, int type, int protocol) {
    (void)domain; (void)type; (void)protocol;
    errno = EACCES;
    return -1;
}

int connect(int fd, const struct sockaddr *addr, socklen_t len) {
    (void)fd; (void)addr; (void)len;
    errno = EACCES;
    return -1;
}

int getaddrinfo(const char *node, const char *service,
                const struct addrinfo *hints, struct addrinfo **res) {
    (void)node; (void)service; (void)hints; (void)res;
    return EAI_FAIL;
}
"""


def _network_denier(tmp_path: Path) -> Path | None:
    """Compile the denial shim, or `None` if this machine has no compiler.

    ⚠ WHY THIS AND NOT A NETWORK NAMESPACE. `unshare -rn` is the obvious tool and
    it is unavailable to an unprivileged process here:
    `/proc/sys/kernel/apparmor_restrict_unprivileged_userns` is 1 on this host,
    so writing `/proc/self/uid_map` is refused and every `unshare` variant exits
    non-zero without root. `LD_PRELOAD` denies the same capability at the C
    library boundary, which is below the code under test and outside its control
    — the property requirement 2 asks for. It is recorded here rather than in a
    commit message because "how the network was disabled" is a checklist item.
    """
    source = tmp_path / "deny_socket.c"
    source.write_text(_DENY_SOCKET_C)
    library = tmp_path / "deny_socket.so"
    try:
        probe = subprocess.run(
            ["cc", "-shared", "-fPIC", "-o", str(library), str(source)],
            capture_output=True, timeout=120)
    except FileNotFoundError:
        return None
    if probe.returncode != 0:
        return None
    return library


def test_verify_runs_with_THE_NETWORK_ACTUALLY_DENIED(tmp_path: Path) -> None:
    """REQUIREMENT 2, DEMONSTRATED RATHER THAN ASSERTED.

    The checker runs as a subprocess whose `socket`, `connect` and `getaddrinfo`
    are denied by the C library, and it must still return every verdict. The
    control is the second half: the SAME denial must make a fetch impossible, or
    the run proves only that nothing tried.
    """
    library = _network_denier(tmp_path)
    if library is None:
        pytest.skip("no C compiler here — the denial shim cannot be built")

    from modules.journal.bag import DIR_MODE
    root = tmp_path / "journal"
    root.mkdir(mode=DIR_MODE)
    bag, _ = _demo_bag(root)

    env = dict(os.environ, LD_PRELOAD=str(library))

    # THE CONTROL FIRST. If this does not fail, the denial is not in force and
    # the verify run below would prove nothing at all.
    control = subprocess.run(
        [sys.executable, "-c",
         "import urllib.request;"
         "urllib.request.urlopen('https://example.com', timeout=5).read(16)"],
        env=env, capture_output=True, timeout=120)
    assert control.returncode != 0, (
        "the denial shim did not take effect — a fetch SUCCEEDED under it, so "
        "the verify run below would be evidence of nothing")

    verified = subprocess.run(
        [sys.executable, str(ENTRYPOINT), str(bag.path)],
        env=env, capture_output=True, text=True, timeout=120)

    assert verified.returncode == EXIT_TAMPERED, (
        f"expected the most severe outcome to decide the exit code.\n"
        f"stdout:\n{verified.stdout}\nstderr:\n{verified.stderr}")
    for outcome in (VERIFIED, MISSING, TAMPERED, SPAN_MISSING):
        assert f"{outcome}: 1" in verified.stdout, (
            f"{outcome} not reported offline:\n{verified.stdout}")
    assert "evidence_set_hash[draft]" in verified.stdout


def test_the_exit_code_tracks_the_worst_outcome_present(tmp_path: Path) -> None:
    """Each class on its own, so the mixed-run test above cannot pass by accident."""
    from modules.journal.bag import DIR_MODE

    def bag_with(mutate) -> int:
        root = tmp_path / f"journal-{mutate.__name__}"
        root.mkdir(mode=DIR_MODE)
        bag = open_bag(root, "one-outcome")
        citation = capture_fetched_source(
            bag=bag, stage="draft", claim_id="c1", quote=QUOTE,
            source_ref="https://example.org/a", data=PAGE)
        mutate(bag, citation)
        probe = subprocess.run([sys.executable, str(ENTRYPOINT), str(bag.path)],
                               capture_output=True, text=True, timeout=120)
        return probe.returncode

    def untouched(bag, citation):
        return None

    def removed(bag, citation):
        object_path(bag.path, citation.page_content_hash).unlink()

    def flipped(bag, citation):
        target = object_path(bag.path, citation.page_content_hash)
        data = bytearray(target.read_bytes())
        data[-1] ^= 0x01
        target.write_bytes(bytes(data))

    def rewritten(bag, citation):
        object_path(bag.path, citation.page_content_hash).write_bytes(
            b"intact bytes that simply do not contain the quote")
        # Re-file under the new digest so the object is INTACT and only the span
        # is gone — otherwise this reproduces `flipped` and proves nothing new.
        from modules.journal.content_store import store_bytes
        digest = store_bytes(bag.path, b"intact bytes without the quote")
        writer = bag.payload_dir / "draft"
        rows = (writer / "citations.jsonl").read_text()
        (writer / "citations.jsonl").write_text(
            rows.replace(citation.page_content_hash, digest))
        object_path(bag.path, citation.page_content_hash).unlink()

    assert bag_with(untouched) == EXIT_OK
    assert bag_with(removed) == EXIT_MISSING
    assert bag_with(flipped) == EXIT_TAMPERED
    assert bag_with(rewritten) == EXIT_SPAN_MISSING
