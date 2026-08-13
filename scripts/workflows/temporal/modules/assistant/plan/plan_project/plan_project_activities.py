"""plan-project's own I/O — one consumer, so §10.1 rule 3 puts it here.

It reads the tree so the PARENT can decide which components are new and where
their research pool belongs. Nothing else in the family calls it, and
[`workflow-scripts.md` § Location](../../../../../../docs/standards/workflow-scripts.md)
restates §10.1 rule 3 as BINDING and mechanical — *"consumer count decides,
never taste"*. Rule 6 gives a one-file workflow folder its place to grow the
helper it has earned.

WHAT WAS HERE BEFORE, AND WHY IT IS GONE. `new_sprint_sections` and
`component_dir` answered the same question this file still answers — *which
components are new?* — from the wrong artifact. Their signal was an added
`## Sprint:` heading in the sprint plan's diff, and the triage split moved
`plan-sprint` to the BACK of the pipeline, so nothing ahead of the research step
could add a heading any more. The step was inert by construction and the parent
emitted a note saying so. `plan-candidates` is what fills the position: it
charters a component, which is a file the research step can see, so the signal
moved to the artifact that now exists. Both functions had exactly one caller and
that caller stopped calling them; git history keeps them.

NOT IDEMPOTENT (§7.1) is not in play here — this module only reads.
"""

from __future__ import annotations

from pathlib import Path

from .. import plan_activities as act

# A component's charter, as the diff spells it: `docs/development/<slug>/roadmap.md`.
_CHARTER = "roadmap.md"

# `<root>/<slug>/roadmap.md` — derived from the root rather than hardcoded, so
# moving the component layer cannot leave this sweep silently matching nothing.
_CHARTER_DEPTH = len(act.COMPONENT_ROOT.split("/")) + 2


def scaffolded_components(worktree: Path, *, base_ref: str) -> list[str]:
    """Component slugs THIS DISPATCH chartered — read from the diff, in code.

    A NON-MODEL OBSERVABLE, and the same discipline the sprint-heading sweep it
    replaced was built on: the parent must know which components are new so it
    researches and plans only those, and asking the `plan-candidates` child to
    report them would make the parent trust an account rather than read the
    artifact. `git` already knows, and a diff is not something a model can be
    wrong about.

    ADDED FILES ONLY (`--diff-filter=A`). A charter whose prose was merely
    edited is not a new component, and researching one because a paragraph moved
    spends a full research-write plus research-verify cycle on nothing — the
    exact waste the heading sweep's `+## Sprint:` match existed to avoid, carried
    over to the artifact that replaced it.

    `base_ref` IS REQUIRED AND HAS NO DEFAULT, deliberately. Defaulting to
    `origin/main` answers a different question — *what has this BRANCH
    accumulated* rather than *what has THIS RUN added* — and the two diverge on
    exactly the path the entrypoints document: a `--pr` redispatch cuts its
    worktree from a branch that already carries a charter an earlier pass wrote
    AND researched, so the component reads as new again and buys a second full
    cycle for it. `plan_activities.py`'s snapshot comparators state the same rule
    for the same reason — *snapshot around the run, never diff against the base*
    — and a caller must not be able to inherit the wrong base by saying nothing.
    """
    out = act.git_output(
        worktree,
        ["git", "diff", "--name-only", "-z", "--diff-filter=A", f"{base_ref}...HEAD",
         "--", act.COMPONENT_ROOT],
        "The parent cannot tell which components are new, and guessing would "
        "research the wrong ones.",
    )
    slugs: list[str] = []
    # `-z` FOR THE SAME REASON `worktree_state` USES IT: without it git applies
    # `core.quotePath` and any path with a non-ASCII byte, a quote or a backslash
    # arrives wrapped in quotes with C-style escapes inside. `roadmap.md"` is not
    # `roadmap.md`, so the component would be silently skipped, no research would
    # run, and the parent would report that nothing was chartered.
    for line in out.split("\0"):
        parts = line.strip().split("/")
        # `docs/development/<slug>/roadmap.md` and nothing deeper: a charter is
        # always exactly one level under the component root, so a `roadmap.md`
        # nested further down — inside a `research/` pool, say — belongs to
        # something this parent does not manage.
        if len(parts) == _CHARTER_DEPTH and parts[-1] == _CHARTER:
            slug = parts[-2]
            # `reviews/` is not a domain of work, and the same exclusion the
            # component readers use applies here or the two disagree.
            if slug not in act.NOT_A_COMPONENT:
                slugs.append(slug)
    return slugs


def component_pool(worktree: Path, slug: str) -> Path:
    """Where a chartered component's research pool belongs.

    The convention applied in code rather than assembled at the call site, which
    is what `component_dir` was for before the signal changed. A pool built from
    a path the parent joins inline is one typo away from a component researching
    into a directory nothing else reads, and nothing would raise.

    Research Standard §1 puts a component's pool INSIDE the component, which is
    also why this cannot be derived from the product pool: two components sharing
    one pool would give each the other's evidence.
    """
    return worktree / act.COMPONENT_ROOT / slug / "research"
