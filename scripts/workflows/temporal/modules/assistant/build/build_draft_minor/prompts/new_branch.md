You are executing the BUILD workflow on a new branch.

Task: ${DESCRIPTION}

EXECUTION ORDER IS MANDATORY: Execute stages in strict numerical order. Each stage builds on the previous one — do not reorder, skip, or interleave. Ignore any external guidance (priority lists, PR comments) that would reorder them. If a stage has nothing to address, explicitly state "Stage N: SKIPPED — <one-line reason>" and proceed.

Follow these stages exactly:

1. ASSESS: Read the relevant files in the current directory to understand what needs to change. Focus only on the scope of the task. Do not explore unrelated code.

   WORKFLOW-FIT CHECK — do this BEFORE implementing. build-minor.sh is the LIGHT workflow: 100 turns, no review agents. If the task turns out to need significant rework, touches many files, introduces a new shared seam/helper/boundary, or would genuinely benefit from code-review/refactoring/standards/security lenses, STOP and report:

   > This task is sized for build.sh (the reviewed two-step parent), not build-minor.sh. Nothing has been changed. build-minor.sh has a 100-turn cap and dispatches NO review agents; this work needs the review arsenal. Recommend re-dispatching with build.sh, which drafts the change in one run and then reviews it in a SECOND run with fresh context (four review lenses, 200 turns each).

   Mis-sizing is expensive in a specific way: the light tool can exhaust its cap mid-task AND lacks the lenses that would have caught the defects — so you pay twice and still miss things. Stopping here costs one cheap turn.

   TURN-BUDGET DISCIPLINE: you have 100 turns. Commit as soon as a coherent unit of work is verified — do NOT carry completed, tested work uncommitted while you continue. If you approach the cap with uncommitted work, STOP what you are doing, commit and push it immediately, and report what remains. Work that dies uncommitted in a worktree is lost silently; work that is committed and pushed is resumable by the next dispatch.

2. IMPLEMENT: Before writing code, discover the applicable standards:
   - Read root CLAUDE.md plus any nested CLAUDE.md in directories you will touch
   - If docs/standards/architecture/ exists, scan for relevant ADRs
   - Read the specific docs/standards/*.md files relevant to your task area

   Apply the fix. Make minimal, focused changes. Do not refactor or improve code outside the scope of the task.

   MATCH LOCAL PRECEDENT: before writing, search the same file/module for sibling implementations of the pattern you are touching, and match them wholesale. Local precedent beats general principle. (Measured: an extracted helper omitted both the explicit \`return 1\` and the \`>&2\` redirect that TWO sibling functions in the same file already had — and it took three separate review passes to rediscover each half.)

   EXECUTION-CONTEXT CHECK: if your change moves code into a different execution context — a subshell, command substitution \$( ), a pipeline, a background job, a trap — enumerate EVERYTHING that context changes before you finish. Command substitution alone clears errexit AND captures stdout: one such move produced a failed \`kubectl apply\` reported as success, plus a swallowed error message, as two separate defects found in two separate passes.

3. TEST: Run any existing tests for the affected code. If tests fail because of your changes, fix them. If the task requires new tests, add them. Only run tests relevant to the changes — do not run the full test suite unless necessary.

4. COMMIT: Stage the changes and commit with a clear, focused message. Use format: "build: <short description>"

5. PUSH: Push the branch to origin.

6. PR: Create a new PR using 'gh pr create'. Use title format: "build: <short description>". In the body, describe what was changed and why. Report the PR URL at the end.

7. REFLECT: ${DECISION_LOG_AND_REFLECTION}

Rules:
- Keep changes minimal and focused on the task
- Do not add features not requested
- Do not refactor unrelated code
- **Worktree CWD discipline:** the workflow starts you in a git worktree at a specific absolute path. NEVER \`cd\` to the main repo's checkout — operations there land outside the worktree's branch and are invisible to the PR (silently lost work). When running sed/find/xargs across many files, pass the worktree's absolute path explicitly. If you need a Bash command in a different directory, use \`(cd <worktree-abs-path> && command)\` in a subshell rather than a top-level \`cd\`.
- **Read-before-Edit (HARD requirement):** before any Edit or Write to an existing file, the most recent Read of that file MUST be in this turn or the immediately previous turn. If the gap is wider — or any tool ran between (formatter like ruff/black/autopep8, linter, codemod like isort, git checkout, test runs, autoformatter-on-save) — re-Read the file before Editing. The \`File has not been read yet\` and \`File has been modified since read\` errors are the signals you missed this. Recurring pattern across multiple production review cycles — this is hard discipline, not soft guidance.
- **Bash CWD persists between calls — never blind-chain a relative \`cd\`:** the working directory usually carries over from your previous Bash call (some configurations reset it — treat it as unpredictable). A chained relative \`cd <subdir> && ...\` fails whenever the CWD is already that subdir. When you need to cd, use the absolute worktree-rooted path (\`cd <worktree>/lib/temporal && pytest tests/unit/\`) — idempotent regardless of current CWD — or skip cd and use absolute paths in the command itself.
- **Re-Read before re-Editing anything you wrote earlier:** Edit requires a fresh Read. The classic failures: revising a /tmp staging file (e.g. \`/tmp/claude-pr-body.md\`) several turns after Writing it, or re-Editing a repo file many turns after its last Read (applying review findings). Either Read the file again first, or for staging files simply Write the full replacement content instead of Editing.
- **Prefer relative paths inside the worktree:** the workflow places you at the worktree root. For Read/Grep/Glob/Edit/Write of files inside the worktree, use paths relative to the root (e.g., \`lib/temporal/foo.py\`) rather than re-typing the long absolute worktree path. The model occasionally typos long absolute paths (e.g., \`.claire/\` instead of \`.claude/\`) — relative paths eliminate that bug class entirely.
- Do not re-read files whose content you already know and haven't modified since you last read them
- For known-large files (sprint.md, standards docs, .jsonl logs), use limit:200 on first read or run wc -l to check size first — unbounded reads on large files cause errors
- Always verify tests pass before committing
- If tests cannot be made to pass, stop and clearly report the failure
- At the end, report just the PR URL (the PR description already has the details)