#!/usr/bin/env bash
# actions-runner.sh — the organisation's self-hosted GitHub Actions runner, on
# this host. One per organisation is enough; every private repository reaches
# it through `runs-on: self-hosted`, and a public one never does.
#
# Usage (as root — the user, the directory and the system unit need it):
#   sudo scripts/services/actions-runner.sh --token <org registration token>
#   sudo scripts/services/actions-runner.sh --status
#
# The token is minted by an organisation admin at Settings → Actions → Runners
# → New runner, is valid for an hour, and is used once here. It is never
# written anywhere; on a host that is already registered it is not needed.
#
# IDEMPOTENT. Every step reports whether it did something or found it done,
# and a second run on an installed host changes nothing.
#
# VERSION AND CHECKSUM ARE READ FROM THE RELEASE, NOT TYPED. The release body
# of actions/runner carries the linux-x64 asset's SHA256 between markers; this
# script downloads the latest release and refuses an archive whose digest does
# not match what the release states. The runner keeps itself current after
# that, so a typed pin here would be stale by the next job.
#
# See /opt/skyy-net/skyynet-master-planning/standards/services/services.md for the conventions this script follows,
# and development/common/continuous-integration/phase1_the_runner.md for why it exists.

set -euo pipefail

ORG_URL="https://github.com/helloskyy-io"
RUNNER_USER="actions-runner"
RUNNER_HOME="/opt/skyy-net/actions-runner"
NODE_BIN_DEFAULT="/opt/skyy-net/.node/bin/node"
RELEASES_API="https://api.github.com/repos/actions/runner/releases/latest"

TOKEN=""
MODE="install"
while [ $# -gt 0 ]; do
    case "$1" in
        --token) TOKEN="${2:?--token needs a value}"; shift 2 ;;
        --status) MODE="status"; shift ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "actions-runner.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
done

info() { echo "  ✓ $1"; }
die()  { echo "actions-runner.sh: $1" >&2; exit 1; }

unit_name() {
    # svc.sh names the unit from the org and the runner name; read it back
    # rather than re-deriving the vendor's scheme.
    [ -f "$RUNNER_HOME/.service" ] && cat "$RUNNER_HOME/.service" || true
}

if [ "$MODE" = "status" ]; then
    if [ ! -f "$RUNNER_HOME/.runner" ]; then echo "not registered"; exit 1; fi
    unit="$(unit_name)"
    [ -n "$unit" ] || die "registered but no service unit recorded — run the install again"
    systemctl is-active "$unit" && echo "$unit"
    exit 0
fi

[ "$(id -u)" -eq 0 ] || die "run as root: the user, $RUNNER_HOME and the system unit need it"

# --- user and directory -----------------------------------------------------
if id "$RUNNER_USER" >/dev/null 2>&1; then
    info "user $RUNNER_USER — exists"
else
    useradd --system --create-home --home-dir "$RUNNER_HOME" --shell /usr/sbin/nologin "$RUNNER_USER"
    info "user $RUNNER_USER → created (system account, no login shell, no sudo)"
fi
mkdir -p "$RUNNER_HOME"
chown "$RUNNER_USER:$RUNNER_USER" "$RUNNER_HOME"
chmod 750 "$RUNNER_HOME"

# --- the runner binary, verified against the release ------------------------
if [ -x "$RUNNER_HOME/config.sh" ]; then
    info "runner binary — present"
else
    command -v curl >/dev/null || die "curl is required"
    command -v python3 >/dev/null || die "python3 is required"
    release_json="$(curl -fsSL "$RELEASES_API")"
    tag="$(printf '%s' "$release_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')"
    version="${tag#v}"
    expected="$(printf '%s' "$release_json" | python3 -c '
import json,re,sys
m = re.search(r"<!-- BEGIN SHA linux-x64 -->([0-9a-f]{64})<!-- END SHA linux-x64 -->", json.load(sys.stdin)["body"])
print(m.group(1) if m else "")')"
    [ -n "$expected" ] || die "release $tag states no linux-x64 SHA256 — refusing to install an unverifiable archive"
    archive="actions-runner-linux-x64-${version}.tar.gz"
    tmp="$(mktemp -d)"
    curl -fsSL -o "$tmp/$archive" "https://github.com/actions/runner/releases/download/${tag}/${archive}"
    actual="$(sha256sum "$tmp/$archive" | cut -d' ' -f1)"
    [ "$actual" = "$expected" ] || die "checksum mismatch for $archive: release states $expected, archive is $actual"
    tar -xzf "$tmp/$archive" -C "$RUNNER_HOME"
    chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_HOME"
    rm -rf "$tmp"
    info "runner $tag → installed, SHA256 verified against the release"
    # The vendor's script probes libicu versions newest-first and prints
    # "Unable to locate package" for each miss before the one this release of
    # Ubuntu ships; only a non-zero exit is a failure, so the probing is kept
    # out of the operator's terminal and shown when it matters.
    if deps_log="$("$RUNNER_HOME/bin/installdependencies.sh" 2>&1)"; then
        info "runner dependencies → installed"
    else
        printf '%s\n' "$deps_log" >&2
        die "runner dependencies failed to install — see above"
    fi
fi

# --- what the jobs find on the machine --------------------------------------
# The planning checks run the tooling's planning-ui.sh, which needs Node 18+;
# the runner reads .env into every job's environment.
if [ -x "$NODE_BIN_DEFAULT" ]; then
    if grep -qs "^NODE_BIN=" "$RUNNER_HOME/.env"; then
        info ".env — NODE_BIN already set"
    else
        echo "NODE_BIN=$NODE_BIN_DEFAULT" >> "$RUNNER_HOME/.env"
        chown "$RUNNER_USER:$RUNNER_USER" "$RUNNER_HOME/.env"
        info ".env → NODE_BIN=$NODE_BIN_DEFAULT"
    fi
else
    echo "  ! $NODE_BIN_DEFAULT is not on this host — planning checks that need Node will fail on this runner until it is" >&2
fi

# --- registration, once -----------------------------------------------------
if [ -f "$RUNNER_HOME/.runner" ]; then
    info "registration — already registered as $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["agentName"])' "$RUNNER_HOME/.runner")"
else
    [ -n "$TOKEN" ] || die "not registered and no --token given: mint an organisation registration token at $ORG_URL (Settings → Actions → Runners → New runner) and pass it with --token"
    # config.sh refuses to run as root; it runs as the runner user, unattended,
    # and --replace re-registers a runner of this name if one was left behind.
    sudo -u "$RUNNER_USER" -H bash -c "cd '$RUNNER_HOME' && ./config.sh --url '$ORG_URL' --token '$TOKEN' --name '$(hostname -s)' --unattended --replace"
    info "registration → $ORG_URL as $(hostname -s)"
fi

# --- the system unit --------------------------------------------------------
unit="$(unit_name)"
if [ -n "$unit" ] && systemctl is-enabled "$unit" >/dev/null 2>&1; then
    info "service $unit — installed and enabled"
else
    (cd "$RUNNER_HOME" && ./svc.sh install "$RUNNER_USER" >/dev/null)
    unit="$(unit_name)"
    info "service $unit → installed (enabled at boot)"
fi
if systemctl is-active "$unit" >/dev/null 2>&1; then
    info "service $unit — active"
else
    (cd "$RUNNER_HOME" && ./svc.sh start >/dev/null)
    info "service $unit → started"
fi

echo ""
echo "The runner is online for every private repository in $ORG_URL. Confirm at"
echo "$ORG_URL/settings/actions/runners, and that the default runner group does NOT allow public repositories."
