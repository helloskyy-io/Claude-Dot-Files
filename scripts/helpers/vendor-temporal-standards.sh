#!/usr/bin/env bash
#
# vendor-temporal-standards.sh — re-copy the Temporal standards from their
# canonical home into docs/standards/temporal/.
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
#   docs/standards/temporal/README.md                     applicability — what binds now vs at port time
#   docs/standards/temporal/claude-dot-files-addendum.md  rules that are genuinely OURS
#
# Usage:
#   scripts/helpers/vendor-temporal-standards.sh            re-vendor from source
#   scripts/helpers/vendor-temporal-standards.sh --check    verify no local drift (exit 1 if drifted)

set -euo pipefail

FILES=(temporal_standard worker_deployment_standard stateful_patterns)
DEST="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/docs/standards/temporal"

# The canonical repo lives in different places on workstations vs VMs.
SRC=""
for candidate in "$HOME/Repos/mdc-master-planning" /opt/skyy-net/mdc-master-planning; do
    if [[ -d "$candidate/standards/development/temporal" ]]; then SRC="$candidate"; break; fi
done
if [[ -z "$SRC" ]]; then
    echo "Error: mdc-master-planning not found in ~/Repos or /opt/skyy-net." >&2
    echo "       Clone it, or pass its path as \$1." >&2
    [[ -n "${1:-}" && -d "${1}/standards/development/temporal" ]] && SRC="$1" || exit 1
fi
SRC_DIR="${SRC}/standards/development/temporal"

CHECK_ONLY=false
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=true

SHA=$(git -C "$SRC" rev-parse HEAD)
DATE=$(git -C "$SRC" log -1 --format=%ad --date=short)
fail=0

for f in "${FILES[@]}"; do
    src="${SRC_DIR}/${f}.md"
    dst="${DEST}/${f}.md"
    [[ -f "$src" ]] || { echo "Error: missing upstream file: $src" >&2; exit 1; }

    if $CHECK_ONLY; then
        # Compare only the body — the header carries provenance and is ours.
        n=$(grep -n '^---$' "$dst" | head -1 | cut -d: -f1)
        if [[ -z "$n" ]] || ! diff -q <(tail -n +$((n + 2)) "$dst") "$src" >/dev/null; then
            echo "✗ ${f}.md has DRIFTED from upstream (or was edited locally)"
            fail=1
        fi
        continue
    fi

    {
        printf '<!-- VENDORED — DO NOT EDIT LOCALLY -->\n'
        printf '> **Vendored from `helloskyy-io/MDC-Master-Planning`** · `standards/development/temporal/%s.md` · `%s` (%s)\n>\n' "$f" "${SHA:0:7}" "$DATE"
        printf '> This file is a **verbatim copy**. Do not edit it here — corrections and amendments go upstream, then re-vendor.\n'
        printf '> Local additions belong in [`README.md`](README.md) (applicability) or [`claude-dot-files-addendum.md`](claude-dot-files-addendum.md) (what is genuinely ours).\n>\n'
        printf '> Re-vendor with: `scripts/helpers/vendor-temporal-standards.sh`\n\n---\n\n'
        cat "$src"
    } > "$dst"
    echo "✓ vendored ${f}.md"
done

if $CHECK_ONLY; then
    [[ $fail -eq 0 ]] && echo "✓ vendored Temporal standards match upstream ${SHA:0:7}"
    exit $fail
fi

echo
echo "Vendored from ${SRC} @ ${SHA:0:7} (${DATE})"
echo "Review the diff before committing — an upstream change may invalidate something built here."
