# Personal Tooling

Autonomous workflow scripts live at `~/Repos/claude-dot-files/scripts/workflows/`.

Run `/get-started` at session start for the workflow inventory, role definitions, and dispatch guidance. Full reference at `~/Repos/claude-dot-files/docs/guide/workflows.md`.

## The bash fleet is FROZEN REFERENCE. It is not a topic.

`scripts/workflows/*.sh` and `scripts/workflows/children/*.sh` are kept **only** as a working backup while the Python fleet under `scripts/workflows/temporal/` is under construction. The operator deletes them when they stop being needed. That is the whole story.

**Binding:**

- **Never modify them.** Not to fix a defect, not to keep them in sync, not to "tidy" them.
- **Never make the Python fleet depend on them** — no reading their source for a value, no invoking them.
- **Never raise them as a consideration.** Do not report a defect that exists only there, do not propose migrating them, do not ask whether a change should also apply to them, and do not frame an answer around which fleet something is in. **If a fix belongs in the Python tree, just say where it goes and put it there.**

**Why this is stated this bluntly:** it has been re-explained several times in a single session — once after a brief wrongly asserted the bash children were load-bearing (they are not; nothing under `temporal/` invokes them), and again after an answer was framed as a V1-versus-V2 comparison when the fix was simply "in the Python tree". Each time it cost the operator a correction and taught nothing new. **The question "what about the bash fleet?" has one permanent answer — nothing — so stop asking it.**
