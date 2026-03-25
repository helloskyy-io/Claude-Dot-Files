#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Claude Code Dotfiles — install.sh
# Creates targeted symlinks from config/ into ~/.claude/
# Safe to re-run (idempotent). Never deletes without backing up first.
# =============================================================================

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

# Check for authentication
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

# Check for jq (needed by hook scripts in Phase 2+)
if command -v jq &>/dev/null; then
    info "jq is installed"
else
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

echo ""
echo "Next steps:"
echo "  • Edit config/CLAUDE.md with your global instructions"
echo "  • Edit config/settings.json with your global settings"
echo "  • Run 'claude' to verify everything works"
echo ""