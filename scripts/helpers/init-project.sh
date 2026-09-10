#!/usr/bin/env bash
#
# init-project.sh — Initialize a new project with standard scaffolding
#
# Pure bash utility (no AI, no Claude, zero tokens). Creates the mechanical
# foundation the tooling expects: git repo, GitHub remote, folder structure,
# the four tracked-item stores, .gitignore, and minimal entry-point files.
#
# Fully idempotent — safe to run multiple times. Skips anything already set up.
#
# STANDALONE, AND THAT IS THE RULING RATHER THAN AN OBSERVATION. This line used
# to say it was "called automatically by plan-new.sh". `plan-new.sh` is in the
# FROZEN bash fleet and nothing under scripts/workflows/temporal/ references
# this script, so its only integration point no longer runs — a live script
# whose caller is frozen. Creating a repository is an OPERATOR act, not a
# dispatch act: nothing in the Python fleet creates repos, and nothing should,
# because a dispatch is pointed AT a tree it did not make. So: an operator runs
# this, by hand, once, before any dispatch is aimed at the result.
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
#   - No requirements, architecture, or planning — a `plan` dispatch does that,
#     pointed at the repo this creates
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
Then point a planning dispatch at the result to define requirements and roadmap.
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
# Preflight: a usable git identity must exist BEFORE anything is written
# ---------------------------------------------------------------------------
# `git commit` (Step 6) derives its author from GIT_AUTHOR_IDENT, which honours
# GIT_AUTHOR_* / GIT_COMMITTER_* env vars as well as user.name/user.email config
# — a `git config user.name` probe would miss the env-supplied case. Checked
# HERE, before Step 1 writes anything, so a missing identity refuses on an empty
# directory rather than leaving a half-scaffolded repo with no commit.
if ! git var GIT_AUTHOR_IDENT >/dev/null 2>&1; then
    echo "✗ No usable git identity — git cannot determine an author." >&2
    echo "  Set user.name and user.email (or GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL) and re-run;" >&2
    echo "  refusing to scaffold ${PROJECT_NAME} before an author is known." >&2
    exit 1
fi

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
                echo "Architecture standards and system design. The WHY." >> "docs/${bucket}/README.md"
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
│   ├── architecture/              # THE WHY: architecture standards, system design
│   ├── development/               # THE WHAT: roadmap, phases, features
│   ├── standards/                 # THE HOW: conventions, patterns
│   ├── guide/                     # OPERATING MANUAL: user-facing docs
│   └── file_structure.txt         # This file
│
├── tracked/                       # The four tracked-item stores — one file per item
│   ├── issues/                    # Defects in live code (I-)
│   ├── operations/                # Operating notes (O-) — HUMAN-ONLY
│   ├── candidates/                # Proposals (C-)
│   └── standards/                 # Amendments to a named standard (S-)
│
├── testing/                       # Suite runners, and check-policy.yaml
│
├── .github/workflows/             # checks.yml — the repo-general checks on the merge path
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
- \`/opt/skyy-net/skyynet-master-planning/standards/architecture\` — THE WHY: architecture standards, system design
- \`docs/development/\` — THE WHAT: roadmap, phases, features
- \`docs/standards/\` — THE HOW: conventions, patterns
- \`docs/guide/\` — OPERATING MANUAL: user-facing docs

## Getting Started

This project was scaffolded by \`init-project.sh\`. Point a planning dispatch at it to define requirements, architecture and roadmap.

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

> Project scaffolded by [init-project.sh](https://github.com/helloskyy-io/Claude-Dot-Files). Point a planning dispatch at it to define this project.

## Documentation

See \`docs/\` for architecture decisions, development roadmap, standards, and user guide.

## License

TBD
READMEMD
    echo "✓ README.md created"
fi

# ---------------------------------------------------------------------------
# Step 4b: the four tracked-item stores
#
# WHY THE SCAFFOLD OWES THESE. `--candidates` defaults to `tracked/candidates`
# on every planning entry point, so without them each dispatch needs the flag and
# the failure an operator sees is a bare missing path they read as a typo. They
# are also where `harvest-intake.py` writes, so a repo without them cannot drain
# its own intake.
#
# ROOT-RELATIVE, NOT UNDER docs/. `tracked/issues/` resolves identically in every
# repo, which is what lets ONE implementation serve all of them.
# ---------------------------------------------------------------------------
if [[ -d "tracked" ]]; then
    echo "✓ tracked/ already exists — skipping"
else
    mkdir -p tracked/{issues,operations,candidates,standards}
    for store in issues operations candidates standards; do
        : > "tracked/${store}/.gitkeep"
    done
    cat > tracked/README.md <<'TRACKEDMD'
# Tracked items

Four stores, per the **Tracked Items Standard**. **The folder's initial letter IS
the id prefix.**

- `issues/` — defects in live code, found out of scope (`I-`)
- `operations/` — human-in-the-loop operating notes (`O-`) — **human-only; no autonomous write, ever**
- `candidates/` — proposals: capability that does not exist yet (`C-`)
- `standards/` — amendments to a named standard, with an anchor (`S-`)

One file per item, random ids so any filer can write without coordinating, and a
recurrence **increments `count`** on the existing item rather than opening a
second one. `count` is what triage sorts on first.
TRACKEDMD
    echo "✓ tracked/ created (issues, operations, candidates, standards)"
fi

# ---------------------------------------------------------------------------
# Step 4c: testing/
#
# `check-policy.yaml` IS DELIBERATELY NOT CREATED, and an empty one is worse than
# none. With no file the tooling reports the TRUE sentence — "declares no check
# policy; nothing was gated on and nothing was expected to be." With an empty
# file it reports "declares a policy and none of it reported, so its workflows
# may have been filtered out of this change", which is false, and false on EVERY
# run until CI exists.
# ---------------------------------------------------------------------------
if [[ -d "testing" ]]; then
    echo "✓ testing/ already exists — skipping"
else
    mkdir -p testing
    cat > testing/README.md <<'TESTINGMD'
# Testing

Per the **Testing Standard**.

## `check-policy.yaml` — written WITH the workflow, which is why it is here

**The rule is that a policy never exists without a workflow**, and this repo was
scaffolded with both, so the rule is satisfied by construction rather than by
anyone remembering. With no workflows, no policy file is the *true* statement —
the tooling reports *"declares no check policy; nothing was gated on and nothing
was expected to be."* An empty policy would report *"declares a policy and none
of it reported"*, implying workflows were filtered out of the change. **Wrong
sentence, and wrong on every run.**

**If you delete `.github/workflows/`, delete this file with it.** The two are one
statement about the repo, and half of it is a lie.

The Testing Standard's clause binds this file: an automated check that can fail
is either on the merge path or declared advisory, and there is no third state.
TESTINGMD
    echo "✓ testing/ created (README.md)"
fi

# ---------------------------------------------------------------------------
# NOT SCAFFOLDED: the sprint file.
#
# `--sprint` defaults to `development/sprints.md`, which is the PLANNING-repo
# layout. This scaffold writes `docs/development/`, the product-repo layout. The
# two disagree, and which one a new product repo should carry depends on whether
# product repos EMBED their planning or POINT AT a planning repo — an
# organisation-level question under discussion, not something to settle by
# picking one here. Until it is ruled, pass `--sprint <path>`; preflight already
# names the file it found when the default misses.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Step 4d: CI — the checks, and the policy that says which of them gate
# ---------------------------------------------------------------------------
# WHY THIS IS SCAFFOLDED RATHER THAN LEFT TO THE FIRST ENGINEER. Measured
# 2026-09-10 across four live repos: two had no CI at all, and one of those was
# the planning repo holding every standard the platform ratifies. Every check
# protecting it ran from a suite in a DIFFERENT repo, on one machine, when
# somebody remembered. A control with no cadence is the failure this fleet keeps
# rediscovering — an unread intake queue, an unswept worktree set, an audit with
# only fixture tests. A repo that gets its checks on day one never acquires it.
#
# THE POLICY IS WRITTEN WITH THE WORKFLOW, NEVER BEFORE IT, which is the rule
# testing/README.md states above: with no workflows, no policy file is the TRUE
# sentence. The moment a workflow exists that sentence becomes false, so the two
# land together or the tooling reports a state that is not real.
#
# THE TOOLING IS CHECKED OUT, NOT VENDORED. `Claude-Dot-Files` is public, so this
# needs no token — and a copy of these scripts in every repo is a copy that
# drifts from the one that is maintained.
if [[ -f ".github/workflows/checks.yml" ]]; then
    echo "✓ .github/workflows/checks.yml already exists — skipping"
else
    mkdir -p .github/workflows
    cat > .github/workflows/checks.yml <<'CHECKSYML'
# The repo-general checks, run on the merge path.
#
# Each step says what it DID, including when it had nothing to look at — a step
# that stays silent on an empty population reads as a pass it never earned.
name: checks

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  repo-checks:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4

      # PUBLIC, so no token. Pinned to a ref rather than floating on main: a
      # tooling change should not turn this repo red without anyone touching it.
      - name: Fetch the tooling
        uses: actions/checkout@v4
        with:
          repository: helloskyy-io/Claude-Dot-Files
          ref: main
          path: .tooling

      - name: Standards carry their header and are indexed
        run: |
          if ls docs/standards/**/*.md standards/**/*.md >/dev/null 2>&1; then
            python3 .tooling/scripts/helpers/standards_index.py --repo-root . --check
          else
            echo "no standards in this repo yet — nothing to audit, and nothing asserted"
          fi

      - name: Vendored standards have not drifted from their source
        run: |
          if [[ -f .vendored-standards ]]; then
            bash .tooling/scripts/helpers/vendor-standards.sh --target . --check
          else
            echo "this repo vendors no standards — nothing to check, and nothing asserted"
          fi

      - name: The repo map is one line per entry and names things that exist
        run: |
          if [[ -f docs/file_structure.txt ]]; then
            python3 .tooling/scripts/helpers/file_structure_check.py --repo-root . --check
          else
            echo "no docs/file_structure.txt — nothing to check, and nothing asserted"
          fi

      - name: This repo's own suite
        run: |
          if [[ -x testing/run-all.sh ]]; then
            ./testing/run-all.sh
          else
            echo "no testing/run-all.sh yet — this repo has no suite, and nothing asserted"
          fi
CHECKSYML

    cat > testing/check-policy.yaml <<'POLICYYML'
# Which of this repo's CI checks gate a merge, and which are advisory.
#
# READ BY THE BUILD PARENT between refine and review-pr. A red BLOCKING check
# means review-pr is never dispatched, so MERGE is unreachable on a red tree.
#
# The Testing Standard's clause is binding here: an automated check that can
# fail is EITHER on the merge path OR declared advisory, and there is no third
# state. A check that runs and appears in neither list is a detectable
# violation, and the parent reports it by name.

blocking:
  # The repo-general checks and this repo's own suite, all in one job. Every
  # step is a correctness claim about the tree, so a red one means the tree is
  # wrong rather than merely untidy.
  - repo-checks

advisory: []
POLICYYML
    echo "✓ .github/workflows/checks.yml + testing/check-policy.yaml created"
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
echo "  run_plan_draft.py --repo \"$(pwd)\" docs/development/<component>"
echo "  Or start working interactively: claude"
echo
