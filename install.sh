#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Claude Code Dotfiles — install.sh
# Places TWO tiers of Claude Code configuration:
#   1. the USER tier — targeted symlinks from config/ into ~/.claude/
#   2. the MANAGED FLOOR — root-owned copies under /etc/claude-code/, which
#      Claude Code ranks above every user/project/CLI setting and which nothing
#      in ~/.claude/ can loosen (Workflow Decomposition Phase 7)
# Safe to re-run (idempotent). Never deletes without backing up first.
# =============================================================================

# --- Parse flags --------------------------------------------------------------

INTERACTIVE=true
INSTALL_SERVICES=false
PLACE_MANAGED_FLOOR=true
for arg in "$@"; do
    case "$arg" in
        --non-interactive|-n) INTERACTIVE=false ;;
        --with-services) INSTALL_SERVICES=true ;;
        # An EXPLICIT opt-out, and the only way to end up without the floor and
        # exit 0. Named in the output every time it is used, so a machine
        # without the floor is one somebody chose, never one that fell through.
        --without-managed-floor) PLACE_MANAGED_FLOOR=false ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

# --- Config -------------------------------------------------------------------

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="$REPO_DIR/config"
CLAUDE_DIR="$HOME/.claude"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$CLAUDE_DIR/backups/pre-install-$TIMESTAMP"

# Items to symlink: config/<item> → ~/.claude/<item>
SYMLINK_TARGETS=(
    "settings.json"
    "CLAUDE.md"
    "agents"
    "commands"
    "hooks"
    "rules"
    "skills"
)

# The managed floor: config/<item> → $MANAGED_DIR/<item>, as root-owned COPIES.
#
# COPIES, NOT SYMLINKS, AND NOT IN SYMLINK_TARGETS. A symlink from /etc into a
# checkout the operator can edit is a floor the operator can lower from below,
# which is the one property the managed tier exists to provide. So the hook is
# copied to a path only root writes, and the drop-in names THAT copy — not
# ~/.claude/hooks/. A stale copy is re-placed on every run (Step 4 compares
# byte-for-byte), so editing config/hooks/block-dangerous.sh and re-running the
# installer is how the floor is updated. SYMLINK_TARGETS is read by the config
# digest and the hook-wiring tests as "what becomes the user tier"; the floor is
# deliberately a separate list so neither reads it as a user-tier item.
#
# Two entries only, by the 2026-09-18 ruling: a permissive user tier over a
# THIN floor carrying the non-negotiable few — the safety hook and the deny set
# (empty since 2026-08-15; see the drop-in and README § Safety).
#
# ORDER MATTERS: the hook script BEFORE the drop-in that declares it. Entries
# are placed in array order and a failure on entry N stops the run with the
# earlier entries already on disk, root-owned. Placed in this order, a partial
# run can leave a hook nothing declares (harmless); in the other order it could
# leave a root-owned declaration of a script that is not there. Every source is
# checked for existence before ANY entry is written, for the same reason.
#
# Format: "<source relative to config/>:<destination relative to MANAGED_DIR>:<mode>"
MANAGED_FLOOR=(
    "hooks/block-dangerous.sh:hooks/block-dangerous.sh:0755"
    "managed-settings.d/claude-dot-files.json:managed-settings.d/claude-dot-files.json:0644"
)

# /etc/claude-code is the ONLY directory Claude Code reads the managed tier
# from on Linux. The override exists so the tests can exercise placement and
# refusal without root; pointing it anywhere else places a floor Claude Code
# will never read, and the installer says so.
MANAGED_DIR="${CDF_MANAGED_DIR:-/etc/claude-code}"
MANAGED_DIR_REAL="/etc/claude-code"
# Both sides are CANONICALISED before they are ever compared — trailing and
# doubled slashes, `.`/`..` segments and symlinks all collapse (`readlink -m`
# does not need the path to exist). A string comparison would read
# `/etc//claude-code` as a test override while every syscall reads it as the
# live directory, and the owner seam below is honoured only on an override —
# so the spelling of the path would have been a way to relax the live floor.
# The one decision "live or override?" is made here, once, and reused.
MANAGED_DIR="$(readlink -m -- "$MANAGED_DIR")"
MANAGED_DIR_REAL="$(readlink -m -- "$MANAGED_DIR_REAL")"
MANAGED_DIR_IS_OVERRIDE=false
[ "$MANAGED_DIR" = "$MANAGED_DIR_REAL" ] || MANAGED_DIR_IS_OVERRIDE=true
# The uid the floor must be OWNED BY. On the live directory it is root and it
# is not configurable — a floor the invoking user owns is one that user can
# rewrite, and the installer would be certifying the property it exists to
# provide. Under the test override the tests cannot produce a root-owned file
# without root, so they name the owner they can produce; the default stays
# root there too, so a test that forgets is refused rather than passed.
MANAGED_OWNER_UID=0
if [ "$MANAGED_DIR_IS_OVERRIDE" = true ] && [ -n "${CDF_MANAGED_OWNER_UID:-}" ]; then
    MANAGED_OWNER_UID="$CDF_MANAGED_OWNER_UID"
fi

# --- Helpers ------------------------------------------------------------------

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No color

info()  { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}!${NC} $1"; }
error() { echo -e "  ${RED}✗${NC} $1"; }

backup_needed=false

backup_item() {
    local target="$1"
    if [ "$backup_needed" = false ]; then
        mkdir -p "$BACKUP_DIR"
        backup_needed=true
    fi
    mv "$target" "$BACKUP_DIR/"
    warn "Backed up $(basename "$target") → backups/pre-install-$TIMESTAMP/"
}

# --- Step 1: Prerequisites ----------------------------------------------------

echo ""
echo "Claude Code Dotfiles — Installer"
echo "================================="
echo ""
echo "Step 1: Prerequisites"
echo ""

# Check for Claude Code
if command -v claude &>/dev/null; then
    info "Claude Code is installed ($(which claude))"
else
    if [ "$INTERACTIVE" = false ]; then
        error "Claude Code is not installed. Exiting."
        exit 1
    fi
    echo ""
    warn "Claude Code is not installed."
    echo ""
    echo "  Install it with:"
    echo "    npm install -g @anthropic-ai/claude-code"
    echo ""
    echo "  Or see: https://docs.anthropic.com/en/docs/claude-code"
    echo ""
    read -rp "  Press Enter after installing Claude Code (or Ctrl+C to abort)... "
    echo ""
    if command -v claude &>/dev/null; then
        info "Claude Code detected."
    else
        error "Claude Code still not found in PATH. Exiting."
        exit 1
    fi
fi

# Check for authentication (skip in non-interactive — auth requires a browser)
if [ "$INTERACTIVE" = true ]; then
    if [ -f "$CLAUDE_DIR/.credentials.json" ]; then
        info "Claude Code is authenticated"
    else
        echo ""
        warn "Claude Code is not authenticated."
        echo ""
        echo "  In another terminal, run:"
        echo "    claude login"
        echo ""
        echo "  Complete the OAuth flow in your browser, then come back here."
        echo ""
        read -rp "  Press Enter after authenticating (or Ctrl+C to abort)... "
        echo ""
        if [ -f "$CLAUDE_DIR/.credentials.json" ]; then
            info "Authentication detected."
        else
            error "Still no credentials found at $CLAUDE_DIR/.credentials.json. Exiting."
            exit 1
        fi
    fi
fi

# Check for jq (needed by hook scripts in Phase 2+)
if command -v jq &>/dev/null; then
    info "jq is installed"
else
    if [ "$INTERACTIVE" = false ]; then
        error "jq is not installed. Exiting."
        exit 1
    fi
    echo ""
    warn "jq is not installed (needed for hook scripts in Phase 2+)."
    read -rp "  Install jq now? [y/N] " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        sudo apt install -y jq
        info "jq installed."
    else
        warn "Skipping jq — you'll need it before setting up hooks."
    fi
fi

# Check for yq (needed by services to read config.yaml)
if command -v yq &>/dev/null; then
    info "yq is installed"
else
    if [ "$INTERACTIVE" = false ]; then
        error "yq is not installed. Exiting."
        exit 1
    fi
    echo ""
    warn "yq is not installed (needed by services to read config.yaml)."
    yq_arch=""
    case "$(uname -m)" in
        x86_64)  yq_arch="amd64" ;;
        aarch64) yq_arch="arm64" ;;
        armv7l)  yq_arch="arm" ;;
        *)       yq_arch="" ;;
    esac
    echo "  Install from: https://github.com/mikefarah/yq"
    if [[ -n "$yq_arch" ]]; then
        echo "  Or let this installer download the ${yq_arch} binary."
        read -rp "  Install yq now via wget? [y/N] " response
    else
        echo "  Unsupported architecture $(uname -m) — install yq manually."
        read -rp "  Press Enter to continue without yq... " response
        response="n"
    fi
    if [[ "$response" =~ ^[Yy]$ ]]; then
        sudo wget -qO /usr/local/bin/yq "https://github.com/mikefarah/yq/releases/latest/download/yq_linux_${yq_arch}"
        sudo chmod +x /usr/local/bin/yq
        info "yq installed."
    else
        warn "Skipping yq — you'll need it before running services."
    fi
fi

# --- Step 2: Create symlinks --------------------------------------------------

echo ""
echo "Step 2: Symlinks"
echo ""

# Ensure ~/.claude/ exists
mkdir -p "$CLAUDE_DIR"

# Track results for summary
declare -A RESULTS

for item in "${SYMLINK_TARGETS[@]}"; do
    source_path="$CONFIG_DIR/$item"
    target_path="$CLAUDE_DIR/$item"

    # Verify source exists in repo
    if [ ! -e "$source_path" ]; then
        error "$item — missing from config/ (skipped)"
        RESULTS[$item]="missing"
        continue
    fi

    # Already a correct symlink — skip
    if [ -L "$target_path" ] && [ "$(readlink -f "$target_path")" = "$(readlink -f "$source_path")" ]; then
        info "$item — already linked"
        RESULTS[$item]="ok"
        continue
    fi

    # Exists but is not our symlink — back up first
    if [ -e "$target_path" ] || [ -L "$target_path" ]; then
        backup_item "$target_path"
        RESULTS[$item]="backed-up-and-linked"
    else
        RESULTS[$item]="linked"
    fi

    # Create symlink
    ln -s "$source_path" "$target_path"
    info "$item → linked"
done

# --- Step 3: Verify + Report -------------------------------------------------

echo ""
echo "Step 3: Verification"
echo ""

all_good=true
for item in "${SYMLINK_TARGETS[@]}"; do
    target_path="$CLAUDE_DIR/$item"
    source_path="$CONFIG_DIR/$item"

    if [ -L "$target_path" ] && [ "$(readlink -f "$target_path")" = "$(readlink -f "$source_path")" ]; then
        info "$item ✓"
    else
        error "$item — symlink verification failed!"
        all_good=false
    fi
done

echo ""
if [ "$all_good" = true ]; then
    echo -e "${GREEN}All symlinks verified. Installation complete.${NC}"
else
    echo -e "${RED}Some symlinks failed verification. Check the output above.${NC}"
    exit 1
fi

if [ "$backup_needed" = true ]; then
    echo ""
    echo "  Backups saved to: $BACKUP_DIR"
fi

# --- Step 4: Managed floor ----------------------------------------------------
#
# ORDER IS DELIBERATE: the user tier is placed and verified BEFORE this step, so
# a refusal here leaves a machine with the user-tier guard already firing. The
# user tier declares the same safety hook the floor does — a host that lacks
# the floor is less un-loosenable, never unguarded.

echo ""
echo "Step 4: Managed floor ($MANAGED_DIR)"
echo ""

# Can this user write the managed directory without escalating? Asked of the
# NEAREST EXISTING ANCESTOR, because `install -D` creates missing parents and
# `-w` on a path that does not exist yet is simply false — which would send a
# writable-but-absent test directory down the sudo path.
managed_dir_writable() {
    local probe="$MANAGED_DIR"
    while [ ! -e "$probe" ]; do
        probe="$(dirname "$probe")"
    done
    [ -w "$probe" ]
}

# Run a command with whatever privilege the managed directory needs. Direct
# when already root or when the target is writable (the test override);
# otherwise sudo — non-interactive with `-n` where no prompt can be answered,
# so a missing password surfaces as a refusal rather than a hang.
as_root() {
    if [ "$(id -u)" = 0 ] || managed_dir_writable; then
        "$@"
    elif [ "$INTERACTIVE" = true ]; then
        sudo "$@"
    else
        sudo -n "$@"
    fi
}

# Why a path in the floor can be rewritten from below, or nothing when it
# cannot. Three properties, each named on failure so the refusal is
# actionable: owned by the required uid; no group/other write bit (a
# directory here matters as much as a file — a writable parent lets the user
# rename their own copy over the root-owned one); and, when the invoking
# user is not that owner, not writable by them at all, which is what catches
# an ACL the mode bits do not show. Root skips the last test because root
# can write anything, and ownership plus mode bits are the whole property
# for root.
floor_path_loosenable() {
    local path="$1" owner mode
    if ! owner="$(stat -c %u "$path" 2>/dev/null)"; then
        echo "not reachable by $(id -un) (uid $(id -u)): $(stat -c %u "$path" 2>&1 >/dev/null | sed 's/.*: //')"
        return
    fi
    mode="$(stat -c %a "$path")"
    if [ "$owner" != "$MANAGED_OWNER_UID" ]; then
        echo "owned by uid $owner, not uid $MANAGED_OWNER_UID"
    elif [ $(( 8#$mode & 8#022 )) -ne 0 ]; then
        echo "mode $mode is group- or world-writable"
    elif [ "$(id -u)" != "$MANAGED_OWNER_UID" ] && [ -w "$path" ]; then
        echo "writable by $(id -un) (uid $(id -u)), who does not own it"
    fi
}

# Why a path in the floor cannot be LOADED from below, or nothing when it
# can. The mirror of the check above: that one asks whether a user below
# root can change the floor, this one asks whether they can read it at all.
# A root-owned 0750 directory — what a CIS-hardened host's root umask of 027
# leaves when `/etc/claude-code/` pre-exists — passes every loosenability
# test and holds a floor no non-root session ever loads: the guard silently
# absent behind a green banner. Two tests, because they catch different
# things. The other-read bit (plus other-execute on a directory, which is
# what makes it traversable and its drop-ins discoverable, and on a hook,
# which is what makes it runnable — a 0754 hook is one the session can open
# and never execute) is the property every user on the host needs, and the
# only one with teeth when the installer runs as root, for whom `-r`/`-x`
# are always true. `-r`/`-x` by the invoking user then catches an ACL the
# mode bits do not show. The declared mode says which shape a file is.
# A path `stat` cannot reach is named as such rather than read as a blank
# mode: an ancestor the invoking user cannot traverse is the same property,
# one level up, and the sweep below names that ancestor on its own line.
floor_path_unreadable() {
    local path="$1" declared="${2:-}" mode
    if ! mode="$(stat -c %a "$path" 2>/dev/null)"; then
        echo "not reachable by $(id -un) (uid $(id -u)): $(stat -c %a "$path" 2>&1 >/dev/null | sed 's/.*: //')"
        return
    fi
    if [ -d "$path" ]; then
        if [ $(( 8#$mode & 8#005 )) -ne $(( 8#005 )) ]; then
            echo "mode $mode is not readable and traversable by other users (needs o+rx)"
        elif [ ! -r "$path" ] || [ ! -x "$path" ]; then
            echo "not readable and traversable by $(id -un) (uid $(id -u))"
        fi
    elif [ "$declared" = "0755" ]; then
        if [ $(( 8#$mode & 8#005 )) -ne $(( 8#005 )) ]; then
            echo "mode $mode is not readable and executable by other users (needs o+rx)"
        elif [ ! -r "$path" ] || [ ! -x "$path" ]; then
            echo "not readable and executable by $(id -un) (uid $(id -u))"
        fi
    elif [ $(( 8#$mode & 8#004 )) -eq 0 ]; then
        echo "mode $mode is not readable by other users (needs o+r)"
    elif [ ! -r "$path" ]; then
        echo "not readable by $(id -un) (uid $(id -u))"
    fi
}

# "Already placed" means identical bytes AND, for a hook, executable AND not
# rewritable from below AND readable from below — a byte-identical copy with
# its x-bit stripped is a hook that never runs, a byte-identical copy the
# user owns or can write is a floor the user can lower, and a byte-identical
# copy the user cannot read is a floor that never loads. One predicate, used
# both to decide whether to write and to verify afterwards, so the two can
# never disagree about what "placed" means: a tampered copy is re-placed as
# root, the same way a stale one is.
floor_entry_placed() {
    local source="$1" target="$2" mode="$3"
    [ -f "$target" ] && cmp -s "$source" "$target" \
        && { [ "$mode" != "0755" ] || [ -x "$target" ]; } \
        && [ -z "$(floor_path_loosenable "$target")" ] \
        && [ -z "$(floor_path_unreadable "$target" "$mode")" ]
}

# The refusal. Names the resolved path and the privilege it lacked, states
# what IS placed, and exits non-zero — the floor must never be believed placed
# because the installer stayed quiet about not placing it.
refuse_managed_floor() {
    local target="$1" why="$2"
    echo ""
    error "MANAGED FLOOR NOT PLACED"
    error "  could not write: $target"
    error "  needs: root (this user is $(id -un), uid $(id -u); $why)"
    echo ""
    echo "  The user tier IS placed and verified above, and its copy of the safety"
    echo "  hook fires. What is missing is the root-owned floor that ~/.claude/"
    echo "  cannot loosen. Re-run with sudo access, or run this installer with"
    echo "  --without-managed-floor to state that this machine goes without it."
    echo ""
    echo -e "${RED}Installation INCOMPLETE: managed floor not placed.${NC}"
    exit 1
}

if [ "$PLACE_MANAGED_FLOOR" = false ]; then
    warn "MANAGED FLOOR NOT PLACED — by --without-managed-floor"
    warn "  $MANAGED_DIR carries no floor from this repo; only the user tier guards this machine"
else
    if [ "$MANAGED_DIR_IS_OVERRIDE" = true ]; then
        warn "CDF_MANAGED_DIR overrides the managed directory: $MANAGED_DIR"
        warn "  Claude Code reads the managed tier ONLY from $MANAGED_DIR_REAL —"
        warn "  a floor placed here is for testing the installer, not for a live machine"
        if [ "$MANAGED_OWNER_UID" != 0 ]; then
            warn "CDF_MANAGED_OWNER_UID overrides the required owner: uid $MANAGED_OWNER_UID, not root — a test-only relaxation"
        fi
    fi

    if [ "$MANAGED_DIR_IS_OVERRIDE" = false ] && [ -n "${CDF_MANAGED_OWNER_UID:-}" ]; then
        echo ""
        error "MANAGED FLOOR NOT PLACED"
        error "  CDF_MANAGED_OWNER_UID=$CDF_MANAGED_OWNER_UID is set, but the owner of $MANAGED_DIR_REAL is root and is not configurable"
        error "  that variable exists for the CDF_MANAGED_DIR test override only. Unset it; nothing was written."
        echo ""
        echo -e "${RED}Installation INCOMPLETE: managed floor not placed.${NC}"
        exit 1
    fi

    if ! command -v sudo >/dev/null 2>&1 && [ "$(id -u)" != 0 ] && ! managed_dir_writable; then
        refuse_managed_floor "$MANAGED_DIR" "sudo is not installed"
    fi

    # Every source must exist BEFORE anything is written: a floor placed from
    # a list with a hole in it is a partial floor, and the drop-in must never
    # be written when the script it declares cannot be.
    floor_all_good=true
    for entry in "${MANAGED_FLOOR[@]}"; do
        IFS=: read -r rel_source rel_target mode <<< "$entry"
        if [ ! -f "$CONFIG_DIR/$rel_source" ]; then
            error "$rel_target — source missing from config/: $CONFIG_DIR/$rel_source"
            floor_all_good=false
        fi
    done
    if [ "$floor_all_good" != true ]; then
        echo ""
        echo -e "${RED}Managed floor NOT placed: a source is missing from config/. Nothing was written.${NC}"
        exit 1
    fi

    for entry in "${MANAGED_FLOOR[@]}"; do
        IFS=: read -r rel_source rel_target mode <<< "$entry"
        source_path="$CONFIG_DIR/$rel_source"
        target_path="$MANAGED_DIR/$rel_target"

        if floor_entry_placed "$source_path" "$target_path" "$mode"; then
            info "$rel_target — already placed"
            continue
        fi

        if [ -f "$target_path" ]; then
            what="re-placed (was stale)"
        else
            what="placed"
        fi

        # `install -D` creates the parent directories, sets the mode, and
        # writes atomically enough for a config file; run as root it leaves
        # every path component root-owned, which is the property wanted.
        # stderr is captured so the refusal can quote sudo's own reason.
        if ! err_out="$(as_root install -D -m "$mode" "$source_path" "$target_path" 2>&1)"; then
            refuse_managed_floor "$target_path" "${err_out:-privilege escalation failed}"
        fi
        info "$rel_target → $what"
    done

    # Verify byte-for-byte, that a hook copy is executable, that nothing in
    # the floor can be rewritten from below, and that all of it can be read
    # from below. A floor that differs from config/ enforces something other
    # than what the repo says; a floor the invoking user owns or can write is
    # not a floor at all — the direct-write branch above is reachable by a
    # non-root user on a misconfigured live directory, and the bytes would
    # match; a floor the runtime user cannot read is one Claude Code never
    # loads. All are refusals, never a banner.
    for entry in "${MANAGED_FLOOR[@]}"; do
        IFS=: read -r rel_source rel_target mode <<< "$entry"
        source_path="$CONFIG_DIR/$rel_source"
        target_path="$MANAGED_DIR/$rel_target"
        if floor_entry_placed "$source_path" "$target_path" "$mode"; then
            info "$rel_target ✓"
        # `stat` failing is "missing" OR "an ancestor is not traversable by
        # this user", and the two need different fixes — so the reason is
        # the kernel's own, never a guess between them.
        elif ! stat_err="$(stat -c %a "$target_path" 2>&1 >/dev/null)"; then
            error "$rel_target — verification failed: cannot reach $target_path as $(id -un): ${stat_err##*: }"
            floor_all_good=false
        elif [ ! -f "$target_path" ] || ! cmp -s "$source_path" "$target_path"; then
            error "$rel_target — verification failed (not a regular file, or differs from config/)"
            floor_all_good=false
        elif [ "$mode" = "0755" ] && [ ! -x "$target_path" ]; then
            error "$rel_target — placed but NOT executable; a hook that cannot run never fires"
            floor_all_good=false
        elif why="$(floor_path_loosenable "$target_path")" && [ -n "$why" ]; then
            error "$rel_target — placed but REWRITABLE FROM BELOW: $target_path is $why"
            floor_all_good=false
        else
            error "$rel_target — placed but UNREADABLE FROM BELOW: $target_path is $(floor_path_unreadable "$target_path" "$mode")"
            floor_all_good=false
        fi
    done

    # Every directory from the managed directory down to each placed file,
    # once each. `install -D` creates the missing ones as the placing user at
    # 0755 regardless of umask; a pre-existing one is whatever the host had.
    # An array, not a delimited string: under the override the path is
    # operator-supplied and may carry a space or a glob character.
    floor_dirs=()
    for entry in "${MANAGED_FLOOR[@]}"; do
        IFS=: read -r _ rel_target _ <<< "$entry"
        dir_path="$(dirname "$MANAGED_DIR/$rel_target")"
        while :; do
            seen=false
            for known in "${floor_dirs[@]}"; do
                [ "$known" != "$dir_path" ] || { seen=true; break; }
            done
            [ "$seen" = true ] || floor_dirs+=("$dir_path")
            [ "$dir_path" != "$MANAGED_DIR" ] || break
            dir_path="$(dirname "$dir_path")"
        done
    done
    for dir_path in "${floor_dirs[@]}"; do
        if ! stat_err="$(stat -c %a "$dir_path" 2>&1 >/dev/null)"; then
            error "$dir_path — verification failed: cannot reach it as $(id -un): ${stat_err##*: }"
            floor_all_good=false
        elif [ ! -d "$dir_path" ]; then
            error "$dir_path — verification failed (not a directory)"
            floor_all_good=false
        elif why="$(floor_path_loosenable "$dir_path")" && [ -n "$why" ]; then
            error "$dir_path — directory REWRITABLE FROM BELOW: $why; a user who can write it can rename a copy over the floor"
            floor_all_good=false
        elif why="$(floor_path_unreadable "$dir_path")" && [ -n "$why" ]; then
            error "$dir_path — directory UNREADABLE FROM BELOW: $why; a floor Claude Code cannot read from a user session never loads"
            floor_all_good=false
        else
            rel_dir="${dir_path#"$MANAGED_DIR"}"
            rel_dir="${rel_dir#/}"
            info "${rel_dir:-.}/ ✓ (directory, owned by uid $MANAGED_OWNER_UID, not writable from below, readable from below)"
        fi
    done

    if [ "$floor_all_good" = true ]; then
        echo ""
        echo -e "${GREEN}Managed floor verified at $MANAGED_DIR.${NC}"
    else
        echo ""
        echo -e "${RED}Managed floor verification failed — a floor that differs from config/, that a non-root user can rewrite, or that a user session cannot read, is not a floor. Check the output above.${NC}"
        exit 1
    fi
fi

# --- Step 5: Services (opt-in) -----------------------------------------------

if [ "$INSTALL_SERVICES" = true ]; then
    echo ""
    echo "Step 5: Services"
    echo ""

    SYSTEMD_DIR="$HOME/.config/systemd/user"
    SERVICES_DIR="$REPO_DIR/scripts/services"
    CONFIG_YAML="$REPO_DIR/config.yaml"

    mkdir -p "$SYSTEMD_DIR"

    # Generate service unit with correct path for THIS machine
    # (not symlinked — the path differs between workstation and VMs)
    MONITOR_PATH="${SERVICES_DIR}/gh-monitor.sh"
    cat > "$SYSTEMD_DIR/gh-monitor.service" <<SVCEOF
[Unit]
Description=GitHub monitor for @claude PR comment automation
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=${MONITOR_PATH}
Environment=HOME=/home/%u
Environment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
SVCEOF
    info "gh-monitor.service → generated (path: ${MONITOR_PATH})"

    # Timer can be symlinked — no path references
    if [ -L "$SYSTEMD_DIR/gh-monitor.timer" ] && [ "$(readlink -f "$SYSTEMD_DIR/gh-monitor.timer")" = "$(readlink -f "$SERVICES_DIR/gh-monitor.timer")" ]; then
        info "gh-monitor.timer — already linked"
    else
        ln -sf "$SERVICES_DIR/gh-monitor.timer" "$SYSTEMD_DIR/gh-monitor.timer"
        info "gh-monitor.timer → linked"
    fi

    # config.yaml is THIS INSTANCE'S configuration and is never committed: it is
    # written once from config.template.yaml (the committed defaults) and then
    # edited per machine. Never overwritten here — an operator's values survive
    # every install run. Services Standard § Centralized config.yaml.
    if [ -f "$CONFIG_YAML" ]; then
        info "config.yaml — present (this instance's settings; not overwritten)"
    else
        cp "$REPO_DIR/config.template.yaml" "$CONFIG_YAML"
        info "config.yaml → written from config.template.yaml (edit it for this machine)"
    fi

    # Enable user lingering — CRITICAL for reboot survival.
    # User-mode systemd services only run while the user has an active session.
    # Without lingering, the timer exists only when the user is logged in via
    # SSH/console — on reboot, the timer doesn't start until someone logs in.
    # loginctl enable-linger makes the user's systemd instance run 24/7
    # regardless of login state, so timers survive reboots cleanly.
    if loginctl show-user "$USER" 2>/dev/null | grep -q "^Linger=yes$"; then
        info "user lingering — already enabled"
    else
        echo ""
        warn "user lingering is not enabled — gh-monitor.timer will NOT survive reboots"
        echo "    Enabling with sudo (you may be prompted for your password)..."
        if sudo loginctl enable-linger "$USER"; then
            info "user lingering enabled — timer will survive reboots"
        else
            error "Failed to enable lingering. Timer will stop on logout/reboot."
            error "Fix manually with: sudo loginctl enable-linger $USER"
        fi
    fi

    # Reload systemd and enable timer
    systemctl --user daemon-reload
    info "systemd daemon reloaded"

    if systemctl --user enable gh-monitor.timer 2>&1; then
        info "gh-monitor.timer enabled"
    else
        warn "Failed to enable gh-monitor.timer — check systemd user session"
    fi

    if systemctl --user start gh-monitor.timer 2>&1; then
        info "gh-monitor.timer started"
    else
        warn "Failed to start gh-monitor.timer — check systemd user session"
    fi

    echo ""
    echo "  Service management commands:"
    echo "    systemctl --user status gh-monitor.timer    # check timer"
    echo "    systemctl --user status gh-monitor.service  # check last run"
    echo "    journalctl --user -u gh-monitor.service -f  # follow logs"
    echo "    systemctl --user stop gh-monitor.timer      # stop polling"
    echo "    systemctl --user disable gh-monitor.timer   # disable on boot"
    echo ""
    echo "  Reboot verification:"
    echo "    loginctl show-user $USER | grep Linger       # should show Linger=yes"
    echo "    (After reboot, timer should be active without SSH login)"
fi

echo ""
if [ "$all_good" = true ]; then
    echo "Next steps:"
    echo "  • Edit config/CLAUDE.md with your global instructions"
    echo "  • Edit config/settings.json with your global settings"
    echo "  • The managed floor is root-owned: edit config/managed-settings.d/ or"
    echo "    config/hooks/block-dangerous.sh, then re-run ./install.sh to update it"
    if [ "$INSTALL_SERVICES" = false ]; then
        echo "  • Run './install.sh --with-services' to set up the GitHub monitor"
    fi
    echo "  • Run 'claude' to verify everything works"
fi
echo ""