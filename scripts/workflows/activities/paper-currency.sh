#!/usr/bin/env bash
#
# paper-currency.sh — ACTIVITY: compute which research papers are past their
# revalidation window, in bash, and render it for a prompt.
#
# ACTIVITY LAYER: workflow-agnostic, single responsibility, idempotent — it
# reads headers and computes, mutating nothing.
#
# WHY THIS IS NOT THE MODEL'S JOB. A research run marked four papers "past
# window" when only one was; every flag was correct against a "today" of
# 2026-08-22 or later, while the real date was 08-03. That is not bad
# arithmetic — it is CORRECT arithmetic against an anchor the run did not
# actually know. A model asked "is this date more than four weeks ago" must
# supply both the anchor and the subtraction, and it will answer confidently
# either way. The consequence was three current papers marked untrusted and a
# synthesis that contradicted research-refresh.sh's mechanical gate on the same
# pool.
#
# So the run is TOLD, never asked: today's date and a per-paper verdict,
# computed with the same rule research-refresh.sh gates on —
#   due when  today − "Last validated"  >  the first "<N> week(s)|month(s)"
#             on the "Revalidate" line.
#
# Usage:  source activities/paper-currency.sh
#         CURRENCY_BLOCK="$(render_paper_currency "<research-dir>")"
# Prints nothing and returns 0 when the directory has no papers.

render_paper_currency() {
    local dir="$1"
    local raw="${dir}/raw"
    [[ -d "$raw" ]] || return 0

    local today today_epoch out due_count=0 total=0
    today=$(date +%Y-%m-%d)
    today_epoch=$(date -d "$today" +%s)
    out=""

    local p name lv rev num unit due_date due_epoch status
    for p in "$raw"/*.md; do
        [[ -e "$p" ]] || continue
        name="$(basename "$p")"
        total=$((total + 1))
        lv=$(grep -m1 -oE 'Last validated:[[:space:]]*[0-9]{4}-[0-9]{2}-[0-9]{2}' "$p" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' || true)
        rev=$(grep -m1 -oE 'Revalidate:.*' "$p" || true)
        num=$(grep -oE '[0-9]+[[:space:]]+(week|month)' <<<"$rev" | head -1 | grep -oE '[0-9]+' || true)
        unit=$(grep -oE '[0-9]+[[:space:]]+(week|month)' <<<"$rev" | head -1 | grep -oE '(week|month)' || true)

        if [[ -z "$lv" || -z "$num" || -z "$unit" ]]; then
            # A paper the mechanical gate cannot read is a finding, not a silent skip.
            out+="| \`raw/${name}\` | — | — | **UNPARSEABLE HEADER** |"$'\n'
            continue
        fi
        if grep -qiE 'Revalidate:[[:space:]]*retired' <<<"$rev"; then
            out+="| \`raw/${name}\` | ${lv} | retired | RETIRED — provenance only, not an input |"$'\n'
            continue
        fi

        due_date=$(date -d "${lv} + ${num} ${unit}s" +%Y-%m-%d)
        due_epoch=$(date -d "$due_date" +%s)
        if (( today_epoch > due_epoch )); then
            status="**PAST WINDOW** (due ${due_date})"; due_count=$((due_count + 1))
        else
            status="current (due ${due_date})"
        fi
        out+="| \`raw/${name}\` | ${lv} | ${num} ${unit}s | ${status} |"$'\n'
    done

    [[ -n "$out" ]] || return 0

    printf '%s\n' "--- paper currency (computed in bash — AUTHORITATIVE) ---"
    printf '%s\n\n' "Today is ${today}. ${due_count} of ${total} papers are past their revalidation window."
    printf '%s\n%s\n' "| Paper | Last validated | Interval | Status |" "|---|---|---|---|"
    printf '%s' "$out"
    cat <<'NOTE'

**Use these verdicts verbatim. Do NOT recompute them.** This table is produced by the
same rule `research-refresh.sh` gates on, so the two mechanisms cannot disagree about
the same pool. A paper marked `current` is current — do not mark it stale, do not
caveat its claims for age, and do not describe it as untrusted. A paper marked
`UNPARSEABLE HEADER` does not conform to the standard's §3 contract; say so.
--- end paper currency ---
NOTE
}
