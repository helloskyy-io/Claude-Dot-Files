---
id: I-8er4h8ve
title: The anchor validator excludes in-page anchors by construction, so five dead links in the operator's own sprint file sit under a green suite — and rule 8 made that class permanent
status: open
count: 1
filed: 2026-08-28
filed_by: review-pr
repo: claude-dot-files
---

**DEFECT — the anchor validator excludes in-page anchors by design, which is the only shape that is actually broken.**

**MEASURED IN THIS REPO, RIGHT NOW: five in-page anchors in `docs/development/sprint.md` resolve to nothing** — `#sprint-assistant-workflow-design--🔵-not-scheduled-needs-research-then-planning` and four siblings. `plan-sprint` found them on two separate runs and escalated them both times (`sprint-anchors-dead`); the suite has been green throughout.

**Why it cannot see them.** `test_every_link_ANCHOR_resolves` keys on:

```python
ANCHORED = re.compile(r"\[[^\]]+\]\((?!https?:|mailto:|#|/)([^)\s#]+\.md)#([a-z0-9][a-z0-9-]*)\)")
```

The negative lookahead **excludes `#`**, so a link to a heading in the SAME file is out of population by construction — its own docstring says so. And `[a-z0-9-]` cannot match an emoji, so even without the lookahead the broken anchors would not match the pattern. **Two independent reasons the guard is blind to the exact class that failed.**

**THE CLASS IS PERMANENT NOW, AND THAT IS THE PART THAT CHANGES THE PRIORITY.** Documentation Standard rule 8 puts a **mutable status marker inside the heading text**, and markdown anchors derive from heading text. So **every marker transition breaks every inbound anchor to that heading** — `🟠 PLANNED → 🟡 IN PROGRESS` is a link break, forever, on every phase that starts or finishes. Before rule 8 this was incidental; now it is scheduled.

**INDEPENDENTLY HIT BY MDC PM3 ON PR #171 (their RC3), harder than here:** adding markers to five headings *"silently killed 8 inbound links."* They fixed it with explicit `<a id="…">` anchors above each phase heading, which survive any marker change, and recommend the same to us.

**Consequence:** a reader following a cross-reference in the sprint file — the operator's own planning surface — lands nowhere, and nothing in 3,682 tests notices. The guard's greenness is what makes it worse than having none.

**Remedy, two parts:**
1. **Widen the validator's population to in-page anchors and to non-ASCII heading text.** The vacuity floor matters more than usual here: assert the in-page population is non-empty, or the widening can be silently reverted by a stricter pattern.
2. **Adopt PM3's `<a id="…">` convention on phase and sprint headings** so an anchor survives a marker transition — and propose it as a rule 8 amendment upstream, since rule 8 is what made the class permanent.

*(Filed separately from `sprint-anchors-dead`, which is the five live links and is the operator's — `sprint.md` is human-only. This item is the guard that should have caught them.)*
