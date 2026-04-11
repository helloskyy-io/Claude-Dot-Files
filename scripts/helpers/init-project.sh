#!/usr/bin/env bash
#
# init-project.sh — Initialize a new project with standard scaffolding
#
# Pure bash utility (no AI, no Claude, zero tokens). Creates the mechanical
# foundation that plan-new.sh and other workflows expect: git repo, GitHub
# remote, folder structure, .gitignore, and minimal entry-point files.
#
# Fully idempotent — safe to run multiple times. Skips anything already set up.
#
# Called automatically by plan-new.sh when no git repo is detected, but can
# also be run standalone for manual project initialization.
#
# Usage:
#   ./init-project.sh "project-name"
#   ./init-project.sh "project-name" --org helloskyy-io
#   ./init-project.sh "project-name" --org helloskyy-io --public
#
# Flags:
#   --org <name>    GitHub organization (default: prompts interactively)
#   --public        Create a public repo (default: private)
#   --skip-remote   Skip GitHub repo creation (local only)
#
# What it creates:
#   - Git repo with 'main' as default branch
#   - GitHub remote (private by default, SSH)
#   - .gitignore (sensible multi-language defaults)
#   - Four-bucket docs layout (architecture, development, standards, guide)
#   - Minimal CLAUDE.md and README.md
#   - .claude/ directory for worktrees, logs, state
#   - Initial commit + push
#
# What it does NOT do:
#   - No AI invocation (zero tokens)
#   - No requirements, architecture, or planning (that's plan-new.sh)
#   - No tech stack decisions
#   - No detailed documentation content

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    cat <<EOF
Usage: $(basename "$0") "project-name" [options]

Options:
  --org <name>    GitHub organization (default: prompts interactively)
  --public        Create a public repo (default: private)
  --skip-remote   Skip GitHub repo creation (local only)

Examples:
  $(basename "$0") "my-project"
  $(basename "$0") "my-project" --org helloskyy-io
  $(basename "$0") "my-project" --org helloskyy-io --public

This creates the bare-minimum scaffolding for a new project.
Run plan-new.sh afterwards to define requirements, architecture, and roadmap.
EOF
    exit 1
fi

PROJECT_NAME="$1"
shift

GH_ORG=""
VISIBILITY="private"
SKIP_REMOTE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --org)
            if [[ $# -lt 2 ]]; then
                echo "Error: --org requires an organization name" >&2
                exit 1
            fi
            GH_ORG="$2"
            shift 2
            ;;
        --public)
            VISIBILITY="public"
            shift
            ;;
        --skip-remote)
            SKIP_REMOTE=true
            shift
            ;;
        *)
            echo "Error: unknown option '$1'" >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------
if ! command -v git &>/dev/null; then
    echo "Error: 'git' not found in PATH" >&2
    exit 1
fi

if [[ "$SKIP_REMOTE" == "false" ]] && ! command -v gh &>/dev/null; then
    echo "Error: 'gh' not found in PATH (needed for GitHub repo creation). Use --skip-remote to skip." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo "================================================================"
echo "  INIT-PROJECT"
echo "================================================================"
echo "  Project   : ${PROJECT_NAME}"
echo "  Visibility: ${VISIBILITY}"
if [[ -n "$GH_ORG" ]]; then
    echo "  Org       : ${GH_ORG}"
fi
echo "  Remote    : $(if $SKIP_REMOTE; then echo 'skip'; else echo 'create'; fi)"
echo "================================================================"
echo

# ---------------------------------------------------------------------------
# Step 1: Git init
# ---------------------------------------------------------------------------
if git rev-parse --show-toplevel &>/dev/null; then
    echo "✓ Git repo already initialized — skipping"
else
    echo "→ Initializing git repo..."
    git init --initial-branch=main
    echo "✓ Git repo initialized (branch: main)"
fi

# Ensure we're on main
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
if [[ "$CURRENT_BRANCH" != "main" && -n "$CURRENT_BRANCH" ]]; then
    echo "→ Renaming branch '${CURRENT_BRANCH}' to 'main'..."
    git branch -m main
fi

# ---------------------------------------------------------------------------
# Step 2: .gitignore
# ---------------------------------------------------------------------------
if [[ -f ".gitignore" ]]; then
    echo "✓ .gitignore already exists — skipping"
else
    echo "→ Creating .gitignore..."
    cat > .gitignore <<'GITIGNORE'
# ---- Secrets & Environment ----
.env
.env.*
!.env.example
*.key
*.pem
*.p12
credentials.json

# ---- Claude Code ----
.claude/

# ---- Python ----
__pycache__/
*.py[cod]
*$py.class
*.so
.venv/
venv/
.eggs/
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
.tox/

# ---- Node / JavaScript / TypeScript ----
node_modules/
.next/
.nuxt/
dist/
*.tsbuildinfo
.npm/
.yarn/

# ---- Go ----
/vendor/

# ---- Rust ----
/target/
Cargo.lock

# ---- IDE ----
.vscode/
.idea/
*.swp
*.swo
*~
.project
.classpath

# ---- OS ----
.DS_Store
Thumbs.db
desktop.ini

# ---- Build artifacts ----
*.log
*.tmp
*.bak
GITIGNORE
    echo "✓ .gitignore created"
fi

# ---------------------------------------------------------------------------
# Step 3: Documentation scaffolding (four-bucket layout)
# ---------------------------------------------------------------------------
DOCS_CREATED=false

for bucket in architecture development standards guide; do
    if [[ -d "docs/${bucket}" ]]; then
        echo "✓ docs/${bucket}/ already exists — skipping"
    else
        mkdir -p "docs/${bucket}"
        # Create a README explaining the bucket's purpose
        case "$bucket" in
            architecture)
                echo "# Architecture" > "docs/${bucket}/README.md"
                echo "" >> "docs/${bucket}/README.md"
                echo "Architectural decisions (ADRs) and system design. The WHY." >> "docs/${bucket}/README.md"
                ;;
            development)
                echo "# Development" > "docs/${bucket}/README.md"
                echo "" >> "docs/${bucket}/README.md"
                echo "Roadmap, phase docs, and feature plans. The WHAT." >> "docs/${bucket}/README.md"
                ;;
            standards)
                echo "# Standards" > "docs/${bucket}/README.md"
                echo "" >> "docs/${bucket}/README.md"
                echo "Coding conventions and patterns. The HOW." >> "docs/${bucket}/README.md"
                ;;
            guide)
                echo "# Guide" > "docs/${bucket}/README.md"
                echo "" >> "docs/${bucket}/README.md"
                echo "User-facing documentation. The OPERATING MANUAL." >> "docs/${bucket}/README.md"
                ;;
        esac
        echo "✓ docs/${bucket}/ created with README"
        DOCS_CREATED=true
    fi
done

# file_structure.txt
if [[ -f "docs/file_structure.txt" ]]; then
    echo "✓ docs/file_structure.txt already exists — skipping"
else
    cat > docs/file_structure.txt <<FSTRUCT
${PROJECT_NAME}/
├── docs/
│   ├── architecture/              # THE WHY: ADRs, system design
│   ├── development/               # THE WHAT: roadmap, phases, features
│   ├── standards/                 # THE HOW: conventions, patterns
│   ├── guide/                     # OPERATING MANUAL: user-facing docs
│   └── file_structure.txt         # This file
│
├── .gitignore                     # Git ignore rules
├── CLAUDE.md                      # Project instructions for Claude
└── README.md                      # Repo documentation
FSTRUCT
    echo "✓ docs/file_structure.txt created"
    DOCS_CREATED=true
fi

# ---------------------------------------------------------------------------
# Step 4: Project entry points
# ---------------------------------------------------------------------------
if [[ -f "CLAUDE.md" ]]; then
    echo "✓ CLAUDE.md already exists — skipping"
else
    cat > CLAUDE.md <<CLAUDEMD
# ${PROJECT_NAME}

## Documentation

This project follows the four-bucket documentation layout:
- \`docs/architecture/\` — THE WHY: ADRs, system design
- \`docs/development/\` — THE WHAT: roadmap, phases, features
- \`docs/standards/\` — THE HOW: conventions, patterns
- \`docs/guide/\` — OPERATING MANUAL: user-facing docs

## Getting Started

This project was scaffolded by \`init-project.sh\`. Run \`plan-new.sh\` to define requirements, architecture, and roadmap.

## Rules

- Do not create files outside the documented structure without asking first.
- Keep \`docs/file_structure.txt\` updated when adding new files or directories.
CLAUDEMD
    echo "✓ CLAUDE.md created"
fi

if [[ -f "README.md" ]]; then
    echo "✓ README.md already exists — skipping"
else
    cat > README.md <<READMEMD
# ${PROJECT_NAME}

> Project scaffolded by [init-project.sh](https://github.com/helloskyy-io/Claude-Dot-Files). Run \`plan-new.sh\` to define this project.

## Documentation

See \`docs/\` for architecture decisions, development roadmap, standards, and user guide.

## License

TBD
READMEMD
    echo "✓ README.md created"
fi

# ---------------------------------------------------------------------------
# Step 5: .claude directory (for worktrees, logs, state)
# ---------------------------------------------------------------------------
if [[ -d ".claude" ]]; then
    echo "✓ .claude/ already exists — skipping"
else
    mkdir -p .claude/{logs,state}
    echo "✓ .claude/ created (logs, state)"
fi

# ---------------------------------------------------------------------------
# Step 6: Initial commit
# ---------------------------------------------------------------------------
# Check if there are any commits yet
if git rev-parse HEAD &>/dev/null; then
    echo "✓ Commits already exist — skipping initial commit"
else
    echo "→ Creating initial commit..."
    git add -A
    git commit -m "feat: initialize ${PROJECT_NAME} project scaffolding"
    echo "✓ Initial commit created"
fi

# ---------------------------------------------------------------------------
# Step 7: GitHub remote
# ---------------------------------------------------------------------------
if [[ "$SKIP_REMOTE" == "true" ]]; then
    echo "✓ Remote creation skipped (--skip-remote)"
else
    if git remote get-url origin &>/dev/null; then
        echo "✓ Remote 'origin' already set — skipping"
    else
        echo "→ Creating GitHub repository..."

        # Build the repo name
        if [[ -n "$GH_ORG" ]]; then
            REPO_FULL="${GH_ORG}/${PROJECT_NAME}"
        else
            # Prompt for org
            echo "  GitHub organization (leave empty for personal account):"
            read -r GH_ORG_INPUT
            if [[ -n "$GH_ORG_INPUT" ]]; then
                REPO_FULL="${GH_ORG_INPUT}/${PROJECT_NAME}"
            else
                REPO_FULL="${PROJECT_NAME}"
            fi
        fi

        # Create the repo
        if [[ "$VISIBILITY" == "public" ]]; then
            gh repo create "$REPO_FULL" --public --source=. --remote=origin
        else
            gh repo create "$REPO_FULL" --private --source=. --remote=origin
        fi

        # Fix remote to SSH if it was set to HTTPS
        REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
        if [[ "$REMOTE_URL" == https://* ]]; then
            SSH_URL="git@github.com:${REPO_FULL}.git"
            git remote set-url origin "$SSH_URL"
            echo "  → Fixed remote to SSH: ${SSH_URL}"
        fi

        echo "✓ GitHub repo created: ${REPO_FULL}"
    fi

    # Push if we have commits and a remote
    if git remote get-url origin &>/dev/null && git rev-parse HEAD &>/dev/null; then
        REMOTE_HEAD=$(git ls-remote --heads origin main 2>/dev/null | wc -l)
        if [[ "$REMOTE_HEAD" -eq 0 ]]; then
            echo "→ Pushing to remote..."
            git push -u origin main
            echo "✓ Pushed to origin/main"
        else
            echo "✓ Remote already has commits — skipping push"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo
echo "================================================================"
echo "  INIT-PROJECT COMPLETE"
echo "================================================================"
echo
echo "Project '${PROJECT_NAME}' is ready."
echo
echo "Next steps:"
echo "  plan-new.sh \"${PROJECT_NAME}\" \"description of the project\""
echo "  Or start working interactively: claude"
echo
