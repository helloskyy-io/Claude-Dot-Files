**BEFORE YOU PLAN ANYTHING, CHECK WHETHER AN OPEN PR ALREADY IMPLEMENTS THIS WORK — and if one does, STOP.**

```
gh pr list --state open --search "<the phase name, or three distinctive words of the task>" --json number,title,headRefName
```

**If a PR comes back that is plausibly this same work, do not implement. Report it and stop**, naming the exact invocation that continues it rather than duplicating it:

> *"PR #<n> `<title>` already implements this. Re-dispatch with `--pr <n>` to update it in place, or say explicitly that a second PR is intended."*

**Name the remedy, not only the problem.** A run that says *"an open PR exists"* gets read past; one that hands over the flag gets followed.

**This is one API call at the point where the alternative is most expensive.** Measured: a phase was built on 2026-09-04 as PR #284 (~4,000 lines), rescoped by the operator, then re-dispatched on 2026-09-06 **without `--pr`** — producing PR #285 (~1,700 lines) implementing the same phase. Both were clean and mergeable, and **both bumped one schema version 1→2 with different payloads**, so a consumer pinned to `"2"` could not know which shape it had. The reviewer correctly refused to rule and escalated. Roughly $40 of the first PR's work was discarded rather than revised, and the flag that would have prevented it was available, documented, and read before dispatch.

**A `--pr` you were given is not this check.** Being pointed at a PR proves the operator knew of one; it does not prove there is not a SECOND. Run the search either way and say what it returned, including when it returned nothing.
