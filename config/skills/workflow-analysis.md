---
name: workflow-analysis
description: Methodology for analyzing Claude Code workflow logs to identify patterns, inefficiencies, and improvement opportunities. Use when reviewing workflow runs, analyzing logs, or producing continuous improvement reports.
---

# Workflow Analysis

This skill defines **how to turn workflow logs into actionable improvements**. It covers what patterns to look for, how to score confidence, and how to structure findings so a human can review and act on them efficiently.

## Principles

1. **Real data, not speculation** — every recommendation must cite specific log evidence
2. **Confidence scoring** — rate each finding by how confident you are and how many observations support it
3. **Actionable output** — findings must lead to concrete changes (prompt edits, skill additions, workflow adjustments)
4. **Cost awareness** — the analysis should not cost more in tokens than it saves in workflow improvements
5. **Sample size matters** — don't recommend changes based on a single observation; note when more data is needed

## What to Look For

### Inefficiencies
- Unnecessary tool calls (reading files that aren't used, redundant searches)
- Scope creep (agent doing work beyond its brief)
- Redundant work (same search or analysis repeated across stages)
- Excessive back-and-forth (many small reads when one large read would suffice)
- Token waste (verbose output that adds no value)

### Repeated Failures
- Same error encountered multiple times across runs
- Patterns of confusion (agent misunderstanding instructions consistently)
- Tool calls that consistently fail or return unhelpful results
- Tests that fail repeatedly for the same reason

### Manual Corrections
- User corrections that recur ("no, not that way" patterns)
- Feedback that should be baked into prompts or skills
- Workflow steps where the user consistently overrides the default behavior

### Missed Opportunities
- Places where a skill could have guided better output
- Agent spawning that could be parallelized
- Information available earlier in the run that isn't used until later

### Successes Worth Preserving
- Approaches that worked particularly well
- Patterns that consistently produce good results
- Efficient tool usage patterns worth replicating

## Confidence Scoring

Rate each finding on a three-level scale:

| Level | Meaning | Action |
|-------|---------|--------|
| **High** | Pattern observed in 3+ runs, clear cause-effect | Ready to act on |
| **Medium** | Pattern observed in 2 runs, or strong single observation | Worth watching, consider acting |
| **Low** | Single observation, possible coincidence | Note for future tracking |

Always state the evidence count: "Observed in N of M runs analyzed."

## Analysis Process

1. **Gather logs** — identify which log files to analyze (by date range or count)
2. **Scan for patterns** — read through each log looking for the categories above
3. **Cross-reference** — compare findings across multiple runs to identify recurring patterns
4. **Score confidence** — assign confidence levels based on frequency and clarity
5. **Formulate recommendations** — turn patterns into specific, actionable changes
6. **Estimate impact** — for each recommendation, estimate effort vs. benefit

## Red Flags

Watch for these signals that indicate systemic issues:

- **Rising turn counts** — workflows taking more turns over time (drift/degradation)
- **Increasing token usage** — same tasks costing more tokens without added value
- **Recurring user corrections** — the same feedback given across multiple sessions
- **Silent failures** — steps that appear to succeed but produce low-quality output
- **Workaround accumulation** — growing number of special cases and exceptions

## Output Format

Structure analysis reports consistently:

```
## Workflow Analysis Report — [date range]

### Runs Analyzed
- [count] runs from [start date] to [end date]
- Workflow types: [list of workflow types observed]

### High-Confidence Findings
- **[Finding title]** — [description]. Observed in [N/M] runs.
  - Evidence: [specific log references]
  - Recommendation: [concrete action]
  - Impact: [estimated benefit]

### Medium-Confidence Findings
- **[Finding title]** — [description]. Observed in [N/M] runs.
  - Evidence: [specific log references]
  - Recommendation: [concrete action]
  - Needs: [what additional data would increase confidence]

### Low-Confidence Findings
- **[Finding title]** — [description]. Observed in [N/M] runs.
  - Watch for: [what to look for in future runs]

### Patterns Resolved Since Last Review
- [Pattern]: [what was done, whether it helped]

### Metrics
- Average turns per workflow: [N]
- Average token usage: [N]
- Most common failure type: [type]
- Improvement trend: [better/worse/stable vs. previous period]

### Summary
[2-3 sentences: overall health of workflows, top priority action, trend direction]
```

## Methodology Rules

These rules govern the analysis process itself:

1. **Explicit audit trail** — every recommendation must be traceable back to the log evidence that motivated it
2. **Reversible recommendations** — recommended changes must be reversible; no one-way doors
3. **Sample size honesty** — always disclose how many runs support a finding
4. **No invented patterns** — if the logs look clean, say so; don't manufacture findings to fill a report
