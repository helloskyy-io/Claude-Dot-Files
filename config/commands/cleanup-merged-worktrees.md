Scan all Claude Code worktrees in this repo and clean up any whose associated pull requests have been merged or closed.

Process:

1. Run `git worktree list` to get all active worktrees
2. For each worktree (skip the main working directory):
   - Identify the branch name
   - Use `gh pr list --head <branch> --state all --json number,state,title` to find the associated PR
   - If the PR state is `MERGED` or `CLOSED`:
     - Report what you're about to clean up
     - Remove the worktree: `git worktree remove <path>`
     - Delete the local branch: `git branch -D <branch>`
     - Delete the remote branch: `git push origin --delete <branch>`
   - If no PR exists for the branch, skip it and report "No PR found, leaving alone"
   - If the PR is still open, skip it and report "PR still open, leaving alone"

3. After processing all worktrees, print a summary:
   - How many worktrees were cleaned up
   - How many were skipped (and why)
   - Any errors encountered

Safety rules:
- NEVER remove the main working directory
- NEVER delete a branch whose PR is still open
- If any step fails, stop and report the error — don't continue blindly
- Ask for confirmation before cleaning up more than 5 worktrees in one run

$ARGUMENTS
