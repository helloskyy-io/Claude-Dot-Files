---
id: I-cyavezck
title: `similar-candidates.py` ranks by rare-term overlap without normalising for length, so the one 4 KB item outranks better matches and the recurrence check points at the wrong candidate
status: open
count: 1
filed: 2026-08-28
filed_by: review-pr
repo: claude-dot-files
---

**DEFECT — measured on PR #145 by `plan-verify`, unprompted.**

> *"`similar-candidates.py` returned `C-523klr8n` as the top hit for two unrelated queries. Its body is ~4 KB of accumulated recurrence prose, which is presumably why it dominates rare-term ranking."*

**The mechanism is the tool's own design working against it.** `recurrence.similar()` ranks on rare shared terms (IDF). An item whose body has grown through repeated recurrence notes contains more rare terms than any other item, so it wins more comparisons — **and the items that grow that way are exactly the ones that recur, which is what makes this self-reinforcing rather than random.**

**Consequence:** the check exists so a filer finds the item their finding is a recurrence OF. Pointed at the wrong candidate, a filer either opens a duplicate or increments the wrong `count` — and `count` now outranks age in triage, so a wrong increment mis-ranks the queue it was built to rank.

**Remedy:** normalise the score by body length (or cap the per-item term contribution) and re-measure against the same two queries. Shipped `c23a0bd`; this is its first defect from live use.
