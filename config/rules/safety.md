# Safety

- Never commit files containing secrets (.env, credentials, tokens, API keys).
- Never hardcode secrets — use environment variables.
- Never force push without explicit approval. **A task that instructs you to REBASE an already-pushed branch IS that approval** — the rebase rewrites history the remote already has, so `--force-with-lease` is the only way to deliver what was asked. Use `--force-with-lease`, never bare `--force`: the lease is what makes it refuse when someone else has pushed in the meantime. *(Added 2026-08-09: two consecutive autonomous runs hit the apparent conflict between this rule and a rebase instruction. A headless run cannot ask, so it either stalls or guesses.)*
- Never run destructive commands (rm -rf, DROP TABLE, git reset --hard) without confirmation.
