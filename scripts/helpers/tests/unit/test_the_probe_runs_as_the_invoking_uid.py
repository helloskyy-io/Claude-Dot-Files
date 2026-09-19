"""The managed-tier probe runs its container as the INVOKING user's uid, derived
from `id -u` — never a literal.

WHY THIS IS A CONTROL AND NOT A STYLE CHECK. `probe.sh` bind-mounts the trial
directories from the host, owned by whoever runs it, and `~/.claude` among them
is 0700. A container user with any other uid hits `Permission denied` before
the first trial. The probe shipped with `-u 1001:1001` and `useradd -u 1001`,
ran clean on the uid-1001 host that wrote it, and failed on the first uid-1000
host (review-pr finding F3 on PR #205). The probe cannot run here — it needs
docker, root-free but real, and a logged-in `claude` — so the property is held
statically: every place the uid reaches docker is a variable, and the variable
is set from `id -u`.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PROBE_DIR = REPO_ROOT / "scripts" / "helpers" / "managed-tier-probe"
PROBE = PROBE_DIR / "probe.sh"
DOCKERFILE = PROBE_DIR / "Dockerfile"

# Any user flag whose value is a bare number, anywhere in the probe: `-u 1001`,
# `-u1001`, `--user 1001`, `--user=1001`. Deliberately NOT anchored to the
# `docker run` line — the probe already splits that command across
# continuation lines, so a `-u` moved to its own line must still be seen.
_LITERAL_RUN_UID = re.compile(r"(?<![\w-])(?:-u|--user)[ =]*['\"]?\d+")
# Any uid flag whose value is a bare number, anywhere in the image: `-u 1001`,
# `-u1001`, `--uid 1001`, `--uid=1001`.
_LITERAL_USERADD_UID = re.compile(r"(?<![\w-])(?:-u|--uid)[ =]*['\"]?\d+")


def _literal_uid_sites(probe_text: str, dockerfile_text: str) -> list[str]:
    """Every place a numeric uid is written where the host's should be derived."""
    found = []
    found += [m.group(0) for m in _LITERAL_RUN_UID.finditer(probe_text)]
    found += [m.group(0) for m in _LITERAL_USERADD_UID.finditer(dockerfile_text)]
    return found


def test_no_uid_reaches_docker_as_a_literal() -> None:
    sites = _literal_uid_sites(PROBE.read_text(), DOCKERFILE.read_text())
    assert not sites, (
        f"a numeric uid is hardcoded where the invoking user's must be derived: {sites}. "
        f"The probe only runs on the host whose uid that is.")


def test_the_uid_is_derived_from_id_u_and_handed_to_both_build_and_run() -> None:
    probe = PROBE.read_text()
    assert re.search(r'^PROBE_UID="\$\(id -u\)"$', probe, re.M), "probe.sh does not derive PROBE_UID from `id -u`"
    assert re.search(r'^PROBE_GID="\$\(id -g\)"$', probe, re.M), "probe.sh does not derive PROBE_GID from `id -g`"
    run_lines = [ln for ln in probe.splitlines() if "docker run" in ln]
    assert run_lines, "probe.sh no longer runs a container; this control guards nothing"
    for ln in run_lines:
        assert '-u "$PROBE_UID:$PROBE_GID"' in ln, f"docker run does not use the derived uid:gid: {ln.strip()}"
    build_lines = [ln for ln in probe.splitlines() if "docker build" in ln]
    assert build_lines, "probe.sh no longer builds the image"
    for ln in build_lines:
        assert '--build-arg "PROBE_UID=$PROBE_UID"' in ln, f"the image is built without the uid: {ln.strip()}"
    dockerfile = DOCKERFILE.read_text()
    assert re.search(r"^ARG PROBE_UID$", dockerfile, re.M), "the Dockerfile declares no PROBE_UID build-arg"
    assert re.search(r'useradd\b[^\n]*-u "\$PROBE_UID"', dockerfile), "useradd does not take the uid from the build-arg"


def test_the_probe_refuses_to_run_as_root() -> None:
    """The container user is built from the derived uid, so uid 0 would have
    the image build remove root; and bypass mode refuses root regardless."""
    probe = PROBE.read_text()
    assert re.search(r'if \[\[ "\$PROBE_UID" = 0 \]\]; then', probe), "no root guard on the derived uid"


def test_the_control_fires_on_the_shipped_hardcoding() -> None:
    """The control on the control: the exact lines the probe shipped with, and
    what a later edit could put back, are what the patterns must catch."""
    shipped_run = '  docker run --rm -u 1001:1001 -e HOME=/home/probe \\\n'
    shipped_useradd = "RUN useradd -m -u 1001 probe\n"
    assert _literal_uid_sites(shipped_run, "") == ["-u 1001"]
    assert _literal_uid_sites("", shipped_useradd) == ["-u 1001"]
    assert _literal_uid_sites('  docker run --rm -u "1000:1000" x\n', "RUN useradd -u '1000' p\n") == [
        '-u "1000', "-u '1000"]
    # The forms a later edit could reach for: the flag on its own continuation
    # line, the long flag, the attached short form, the `=` form.
    assert _literal_uid_sites('  docker run --rm \\\n    -u 1001:1001 \\\n    x\n', "") == ["-u 1001"]
    assert _literal_uid_sites('  docker run --rm --user 1001 x\n', "RUN useradd --uid 1001 p\n") == [
        "--user 1001", "--uid 1001"]
    assert _literal_uid_sites('  docker run --rm -u1001 x\n', "RUN useradd --uid=1001 p\n") == [
        "-u1001", "--uid=1001"]
    # And the derived form is not a false positive — nor is `id -u` itself.
    assert _literal_uid_sites('PROBE_UID="$(id -u)"\n  docker run --rm -u "$PROBE_UID:$PROBE_GID" x\n',
                              'RUN useradd -m -u "$PROBE_UID" probe\n') == []
