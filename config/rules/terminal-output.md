# Terminal Commands & Prompts

When generating shell commands for the user to copy-paste:

- NEVER use heredoc syntax (`$(cat <<'EOF'...)`, `<<'CONTEXT'`, etc.). Heredocs break on copy-paste every time.
- ALWAYS use a single double-quoted string on one line for prompts.
- ALWAYS use absolute paths to scripts (the user may be in a different repo).
- For long or multi-paragraph task/context inputs, write the payload to `/tmp/claude-<name>.md` first, then pass `--task-file /tmp/claude-<name>.md`. This bypasses command-line parsing entirely — quotes, newlines, backticks, and special characters all pass through literally.
- **ALL commands given to the user must be a SINGLE LINE.** No exceptions. No multi-line code blocks, no embedded newlines, no `sudo bash -c '...'` blocks spanning lines. If a command can't fit on one line, write it to `/tmp/claude-<descriptive-name>.sh` and give the user `sudo bash /tmp/claude-<descriptive-name>.sh` as the single-line invocation. This applies to EVERYTHING: workflow dispatches, operational commands, diagnostic commands, git sequences. Terminal whitespace handling corrupts multi-line pastes every time. Chain 2-3 simple related commands with `&&` on one line when script-to-tmp is overkill.

## Commands YOU run: a pipe throws away the exit status, and the run reports success

**Never put a command whose success you will rely on upstream of a pipe.** `cmd | tail -40`
exits with `tail`'s status, so a command that failed — or never existed — reports **0**.

**This is not theoretical and it is not somebody else's habit.** Measured twice on 2026-09-08:

| | |
|---|---|
| A backgrounded dispatch ran `python3 run_<name>.py … 2>&1 \| tail -35` against a runner that **does not exist**. `python3` exited 2, `tail` exited 0, and the harness reported the task **completed successfully having executed nothing.** | PM1 |
| `standards_index.py --check` on a corpus with 13 incomplete standards. True exit **1**. Reported through `\| tail -40`: **0** — the refusal the tool exists to raise, silently inverted into a pass, by the session that had just built the tool. | this session |

**What to do instead** — redirect, then read the file:

```
cmd > /tmp/claude-1001/run.log 2>&1; echo "exit=$?"; tail -40 /tmp/claude-1001/run.log
```

`echo "exit=$?"` **after a pipe measures the pipe** and is worse than nothing: it prints a
number that looks like verification. Either redirect as above, or put `set -o pipefail;`
in front of the pipeline.

**Where this bites hardest:** any `--check`, any `--dry-run`, any test runner, any dispatch —
every command whose *whole purpose* is to exit non-zero. Filtering their output is exactly
when you reach for a pipe, so the failure concentrates in the commands that can least afford it.

**A missing runner is separately guarded and this is NOT that fix.**
`test_shim_usage_names_itself.py` already asserts every `*.sh` shim has its `run_*.py` beside
it, at CI time. That guard cannot reach the case above, because a command naming a script that
never existed has no shim to check — and would still exit 0 behind the pipe if it did.


For workflow dispatch invocation shape, ordering rules, and the `--task-file` pattern, see `~/Repos/claude-dot-files/docs/guide/workflows.md`.
