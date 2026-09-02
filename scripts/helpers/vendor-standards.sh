#!/usr/bin/env bash
#
# vendor-standards.sh — re-copy vendored standards from their canonical
# home in MDC-Master-Planning into docs/standards/.
#
# Governed by Documentation Standard § "Cross-ecosystem vendored standards —
# mirror/fork provenance (binding)": a separate-ecosystem repo COPIES a standard
# in rather than live-referencing it, and every copy carries a provenance +
# INTENT flag (MIRROR or FORK). All copies here are MIRROR.
#
# WHY VENDOR RATHER THAN REFERENCE: claude-dot-files deploys standalone to
# workstations and VMs that may not have mdc-master-planning checked out, and a
# standard you cannot read is not binding. Vendoring makes it readable
# everywhere.
#
# WHY VERBATIM, AND WHY YOU MUST NOT EDIT THE COPIES: the alternative to a
# reference is a FORK, and a fork drifts silently — two repos with the same
# section numbers saying different things is worse than not having the file at
# all. Local edits are therefore forbidden. Amendments go upstream, then
# re-vendor with this script. `--check` fails if a copy has drifted, so the
# drift is loud rather than discovered months later.
#
# WHAT BELONGS LOCALLY INSTEAD:
#   /opt/skyy-net/skyynet-master-planning/standards/temporal/README.md                     applicability — what binds now vs at port time
#   /opt/skyy-net/skyynet-master-planning/standards/temporal/claude-dot-files-addendum.md  rules that are genuinely OURS
#
# Usage:
#   scripts/helpers/vendor-standards.sh            re-vendor from source
#   scripts/helpers/vendor-standards.sh --check    verify no local drift (exit 1 if drifted)

set -euo pipefail

# source-subpath:dest-name — add a line to vendor another standard
# owner:source-relative-path:destination-relative-path
#
# THE OWNER COLUMN IS NEW ON 2026-09-02, and it is the whole point of this pass.
# Three of these moved from vendored-from-MDC to OWNED IN skyynet-master-planning,
# because each governs a surface the TOOLING reads and writes rather than a
# platform's runtime: the four tracked stores, the planning-doc conventions, and
# the research contract — the last of which already declared itself binding for
# both platforms before anyone asked.
#
# TESTING JOINED THEM ON 2026-09-02, after MDC-PM3 argued the deferral was the
# wrong shape and was right. I had proposed SPLITTING it and my table covered 9
# of its 19 sections, leaving the hardest call unassigned. Thirteen-plus are
# tooling contract; the four that are not are `how MDC tests its deployments` —
# a different subject wearing the same filename. So it MOVES WHOLE and MDC
# carries `testing_standard-mdc-addendum.md`, which is the mechanism our own
# vendoring banner already names. There is no boundary to get wrong when one
# owner holds the core and everything else is additive.
#
# The Temporal three stay MDC's — they govern a runtime that does not exist here.
FILES=(
  "SN:documentation/documentation_standard.md:documentation/documentation_standard.md"
  "SN:documentation/tracked_items_standard.md:documentation/tracked_items_standard.md"
  "SN:research/research_standard.md:research/research_standard.md"
  "MDC:temporal/temporal_standard.md:temporal/temporal_standard.md"
  "MDC:temporal/worker_deployment_standard.md:temporal/worker_deployment_standard.md"
  "MDC:temporal/stateful_patterns.md:temporal/stateful_patterns.md"
  "SN:testing/testing_standard.md:testing/testing_standard.md"
)
# TWO SOURCES AND A TARGET. Each entry names its owner; each owner has a root.
# `--target <repo>` writes the mirrors into any consumer — that is what lets a
# product repo like `image-manager` hold drift-checkable copies instead of
# hand-maintained ones.
_CDF="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# THE SIBLINGS DIRECTORY IS THE MAIN CHECKOUT'S PARENT, NOT THIS TREE'S. Every
# autonomous dispatch runs from a linked worktree under
# `<main checkout>/.claude/worktrees/<name>`, where `$_CDF/..` is `.claude/
# worktrees/` and no sibling repo is there — so `--check` exited 1 with
# "skyynet-master-planning not found" for exactly the caller that runs it most.
# `--git-common-dir` is git's own answer to "which checkout is this a worktree
# of": in the main checkout it is that repo's `.git`, and in a linked worktree it
# is still the MAIN repo's `.git`, so one expression covers both. Falls back to
# the plain parent when git cannot answer, which is the pre-existing behaviour.
# NOT CORRECT FOR A BARE REPOSITORY, where `--git-common-dir` is the repo
# directory itself and going up twice overshoots by one. Named rather than
# handled: a bare repo has no working tree, so nothing can run this script
# from inside one.
_COMMON_GIT_DIR="$(git -C "$_CDF" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
if [[ -n "$_COMMON_GIT_DIR" && -d "$_COMMON_GIT_DIR" ]]; then
    _SIBLINGS="$(cd "$_COMMON_GIT_DIR/../.." && pwd)"
else
    _SIBLINGS="$(cd "$_CDF/.." && pwd)"
fi

CHECK_ONLY=false
TARGET=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --check)  CHECK_ONLY=true; shift ;;
        --target) TARGET="$2"; shift 2 ;;
        *)        MDC_OVERRIDE="$1"; shift ;;
    esac
done

# Ours. Not discovered by probing for a Temporal directory the way MDC is —
# this is the repo that OWNS three of the entries, so its absence is fatal
# rather than a fallback.
SN_SRC="${_SIBLINGS}/skyynet-master-planning"
[[ -d "${SN_SRC}/standards" ]] || {
    echo "Error: skyynet-master-planning not found at ${SN_SRC}." >&2; exit 1; }

MDC_SRC=""
for candidate in "${MDC_OVERRIDE:-}" "$HOME/Repos/mdc-master-planning" /opt/skyy-net/mdc-master-planning; do
    [[ -n "$candidate" && -d "$candidate/standards" ]] && { MDC_SRC="$candidate"; break; }
done
if [[ -z "$MDC_SRC" ]]; then
    echo "Error: mdc-master-planning not found in ~/Repos or /opt/skyy-net." >&2
    echo "       Clone it, or pass its path as an argument." >&2
    exit 1
fi

# DEFAULT TARGET IS THE SKYYNET PLANNING REPO, which is also the SOURCE of the
# `SN:` entries. Vendoring a file onto itself would overwrite the original with a
# mirror banner and destroy it, so self-owned entries are SKIPPED there — stated
# out loud in the run's output rather than silently passed over.
DEST_REPO="${TARGET:-$SN_SRC}"
[[ -d "$DEST_REPO" ]] || { echo "Error: target not found: $DEST_REPO" >&2; exit 1; }

# THE TARGET'S OWN LAYOUT DECIDES, because two are live in this ecosystem and
# neither is wrong. A planning repo mirrors MDC's shape and keeps `standards/` at
# the root; a product repo built by `init-project.sh` keeps `docs/standards/`.
# Probing for the one that EXISTS is what lets one tool serve both without
# settling a layout question that belongs to the operator, not to a vendoring
# script. If neither exists the target has never held standards, and the caller
# is told which two paths were looked for rather than left with an exit code —
# this returned a bare `exit 2` under `set -e` on the first real `--target` run,
# which is precisely the silent failure this repo keeps paying for.
if [[ -d "${DEST_REPO}/standards" ]]; then
    DEST="${DEST_REPO}/standards"
elif [[ -d "${DEST_REPO}/docs/standards" ]]; then
    DEST="${DEST_REPO}/docs/standards"
else
    echo "Error: ${DEST_REPO} has neither standards/ nor docs/standards/." >&2
    echo "       Create the one its layout uses, then re-run." >&2
    exit 1
fi



fail=0
skipped=0
for entry in "${FILES[@]}"; do
    owner="${entry%%:*}"; rest="${entry#*:}"
    rel="${rest%%:*}"; dst_rel="${rest##*:}"

    if [[ "$owner" == "SN" ]]; then
        src_repo="$SN_SRC"; src="${SN_SRC}/standards/${rel}"; label="helloskyy-io/skyynet-master-planning"
    else
        src_repo="$MDC_SRC"; src="${MDC_SRC}/standards/${rel}"; label="helloskyy-io/MDC-Master-Planning"
    fi
    # THE DESTINATION PATH IS RESOLVED IN THE TARGET, NOT COPIED FROM OURS.
    #
    # `dst_rel` encodes THIS ecosystem's shape (`testing/testing_standard.md`).
    # MDC nests development standards one tier deeper
    # (`development/testing/testing_standard.md`), so writing `dst_rel` there
    # created a SECOND copy at a path nobody reads while the original stayed
    # authoritative-looking and stale — and reported `✓ mirrored` while doing it.
    # Two of four matched only because `documentation/` happens to sit at the
    # same depth in both repos.
    #
    # SO: if the target already holds this standard, mirror OVER IT, wherever it
    # is. Probing beats a per-repo manifest here because the answer is already on
    # disk and a manifest is one more thing to be wrong on a new machine.
    # AMBIGUITY IS REFUSED rather than guessed — two files of the same name in
    # one target means a human has to say which is the standard.
    base="$(basename "$dst_rel")"
    mapfile -t existing < <(find "$DEST" -type f -name "$base" 2>/dev/null | sort)
    case "${#existing[@]}" in
        0) dst="${DEST}/${dst_rel}" ;;
        1) dst="${existing[0]}" ;;
        *) echo "✗ ${base}: ${#existing[@]} copies in ${DEST} — ${existing[*]}." >&2
           echo "  Refusing to guess which is the standard. Remove the stale one." >&2
           fail=1; continue ;;
    esac

    # NEVER MIRROR A FILE ONTO ITSELF — it would overwrite the source with a
    # banner-wrapped copy of itself and the original would be gone.
    if [[ "$(cd "$src_repo" && pwd)" == "$(cd "$DEST_REPO" && pwd)" ]]; then
        echo "· ${dst_rel} is OWNED here — not mirrored onto itself"
        skipped=$((skipped + 1)); continue
    fi

    [[ -f "$src" ]] || { echo "Error: missing source file: $src" >&2; exit 1; }
    sha=$(git -C "$src_repo" rev-parse HEAD)
    date=$(git -C "$src_repo" log -1 --format=%ad --date=short)

    if $CHECK_ONLY; then
        # `|| n=""` BECAUSE A PRE-MIRROR DESTINATION IS AN ORIGINAL: no banner,
        # so no `^---$`, so `grep` exits 1, `pipefail` propagates it and `set -e`
        # killed the script — exit 2, no output, with the `[[ -z "$n" ]]` guard
        # on the very next line UNREACHABLE. A check that dies silently on a
        # first-time destination is worse than one that fails loudly: it reads as
        # "nothing to report" when it means "did not run".
        n=$(grep -n '^---$' "$dst" 2>/dev/null | head -1 | cut -d: -f1) || n=""
        if [[ ! -f "$dst" ]]; then
            echo "✗ ${dst_rel} is MISSING from ${DEST_REPO}"; fail=1
        elif [[ -z "$n" ]] || ! diff -q <(tail -n +$((n + 2)) "$dst") "$src" >/dev/null; then
            echo "✗ ${dst_rel} has DRIFTED from ${label} (or was edited locally)"; fail=1
        fi
        continue
    fi

    mkdir -p "$(dirname "$dst")"
    {
        printf '<!-- VENDORED — DO NOT EDIT LOCALLY -->\n'
        printf '> *Vendored from `%s` · `standards/%s` on %s (`%s`).*\n' "$label" "$rel" "$date" "${sha:0:7}"
        printf '> *Intent: **MIRROR** — this copy tracks the source. A general improvement made here is retrofitted upstream in the same work; anything specific to this ecosystem does not belong in this file at all.*\n>\n'
        printf '> Per Documentation Standard § *Cross-ecosystem vendored standards (binding)*. **Do not edit this file.** Amendments go to the owner, then re-mirror.\n'
        printf '> Ecosystem-specific content belongs in the sibling `README.md` (applicability) or an `*-addendum.md`.\n>\n'
        printf '> Re-mirror with: `scripts/helpers/vendor-standards.sh --target <repo>`\n\n---\n\n'
        cat "$src"
    } > "$dst"
    echo "✓ mirrored ${dst_rel}  <- ${label}"
done

if $CHECK_ONLY; then
    [[ $fail -eq 0 ]] && echo "✓ every mirror in ${DEST_REPO} matches its owner (${skipped} owned here, not mirrored)"
    exit $fail
fi

echo
echo "Target: ${DEST_REPO}"
echo "Sources: ${SN_SRC} (owned) · ${MDC_SRC} (consumed)"
echo "Review the diff before committing — an upstream change may invalidate something built here."
