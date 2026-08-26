---
id: C-xf0j16sq
title: Give `workflow-scripts.md` a section naming `RepoPathParser.add_repo_path` as the required way a Python entrypoint declares an operator-supplied repo path, so the rule is discoverable before a test enforces it
status: open
count: 1
filed: 2026-08-26
filed_by: triage-candidates
component: workflow-decomposition
---

**The mechanism is now mandatory and enforced — `test_no_runner_joins_an_UNRESOLVED_operator_path.py` fails any `run_*.py` that joins an argparse attribute onto a root — and no standards document mentions it.** Verified by reading `workflow-scripts.md` end to end, including its *Validate Inputs* section: `add_repo_path`, `RepoPathParser` and `parse_with_preflight` appear nowhere in `docs/standards/`. **The consequence is that the eleventh runner's author meets this rule as a red test rather than as a documented convention**, and the failure they see names a join in their own file rather than the mechanism they were supposed to use — the specific reason this PR chose a guard whose message spells out the remedy. That is a mitigation, not a substitute for the rule being findable by someone reading the standards before writing code. **Filed rather than fixed because `standards-governance.md` bars an autonomous run from writing standards content**, which is the correct rule and is being followed rather than worked around; `candidates.md` is the working surface that carries a proposal to the architecture session without a standards edit. **Done-state today: yes** — one section in `workflow-scripts.md`, plus a decision on whether `preflight`'s two other public helpers belong in the same section. **Not an expansion of C-oapy6vg8** (deriving hand-maintained control sets — that is test-side bookkeeping) **and not of C-p8klz6zk** (observer registries for the build and research families — that is a mechanism to build, this is a rule to write down). **Raised by `standards-auditor` at Info on this PR, which explicitly declined to propose the edit itself for the same governance reason.**

**Source:** PR #93 `plan-verify` (build-refine, 2026-08-16)

*Migrated from `docs/standards/architecture/research/candidates.md` on 2026-08-26, preserving its id.*
