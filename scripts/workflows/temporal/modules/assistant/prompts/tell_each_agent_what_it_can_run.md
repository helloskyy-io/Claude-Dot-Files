**TELL EACH AGENT WHAT IT CAN RUN, AND THAT YOU CAN RUN THE REST.** Verified
against their definitions: `architect`, `planner`, `security-auditor`,
`standards-architect` and `quality-control` hold **Read, Grep and Glob only** —
none of them has Bash. They cannot run a command, a test, a mutation or a `git`
invocation. Put this in the dispatch, in these two parts:
