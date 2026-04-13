#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Claude Code Dotfiles — install.sh
# Creates targeted symlinks from config/ into ~/.claude/
# Safe to re-run (idempotent). Never deletes without backing up first.
# =============================================================================

# --- Parse flags --------------------------------------------------------------

INTERACTIVE=true
INSTALL_SERVICES=false
for arg in "$@"; do
    case "$arg" in
        --non-interactive|-n) INTERACTIVE=false ;;
        --with-services) INSTALL_SERVICES=true ;;
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

# --- Step 4: Services (opt-in) -----------------------------------------------

if [ "$INSTALL_SERVICES" = true ]; then
    echo ""
    echo "Step 4: Services"
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

    # Verify config.yaml exists
    if [ -f "$CONFIG_YAML" ]; then
        info "config.yaml — found (edit gh-monitor settings there)"
    else
        warn "config.yaml not found at repo root — gh-monitor will use defaults"
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
fi

echo ""
if [ "$all_good" = true ]; then
    echo "Next steps:"
    echo "  • Edit config/CLAUDE.md with your global instructions"
    echo "  • Edit config/settings.json with your global settings"
    if [ "$INSTALL_SERVICES" = false ]; then
        echo "  • Run './install.sh --with-services' to set up the GitHub monitor"
    fi
    echo "  • Run 'claude' to verify everything works"
fi
echo ""