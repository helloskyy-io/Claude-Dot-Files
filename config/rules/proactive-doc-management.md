# Proactive Documentation Management

Documentation is a living artifact. When work shifts system reality, docs must shift with it. The PM is responsible for keeping docs current as work proceeds — without being asked.

## Triggers — recognize and initiate without prompting

- **After completing implementation work in session:** update phase doc / epic checkboxes for verifiably-done items; reword phase doc substance if the implemented solution diverged from what the doc describes; verify implementation conforms to applicable standards.

- **When user says "let's update docs" / "we're done [with X]" / "let's wrap up" / similar:** immediately initiate the FULL pass — checkbox reconciliation, substance reconciliation, standards verification, /guide doc updates (if user-facing behavior changed), cross-reference verification.

- **After significant PR lands:** same full pass.

- **After standards substance changes:** invoke `doc-manager` in COORDINATE mode to propagate references through CLAUDE.mds and other docs; surface breakages.

- **At natural session wrap-up:** audit what was done; surface anything that needed doc updates that didn't happen.

## How to execute

Invoke the `doc-manager` agent in the appropriate mode (AUTHOR / COORDINATE / AUDIT / MAINTAIN). Typical wrap-up pass: AUDIT → MAINTAIN → AUTHOR (drafts) → operator reviews → COORDINATE.

## Authority

Substance edits ALWAYS go through human review — doc-manager drafts, operator approves. Mechanical maintenance is bounded by doc-manager's authority levels (see `documentation-management` skill).

## Anti-patterns

- "Done, moving on" without doc review
- Assuming operator will remember to ask
- Treating checkbox updates as polish
- Deferring doc updates to "later session" — loose-ends-as-LAST-option applies
- "It's obvious" instead of verifying standards conformance
