## Stage 1: VERIFY + DISCOVER
FIRST: verify the task targets THIS repo. If ${RESEARCH_DIR} or the context references a DIFFERENT repository than the one your worktree belongs to, STOP immediately — report "DISPATCH MISCONFIGURATION: task targets <repo X>, worktree is in <repo Y>; re-dispatch with --repo <path>" as your final output and do no further work. Do NOT self-rescue into another repo.
