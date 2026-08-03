# claude-dot-files addendum to the Temporal Standards

**This is the only file in this folder that may be edited locally.** Everything else is vendored verbatim — see [`README.md`](README.md).

Its scope is narrow by design: rules that are **genuinely ours** because the upstream standards were written for infrastructure management and do not reach our shape. Anything that is merely *our restatement* of an upstream rule belongs in `docs/standards/workflow-scripts.md` instead, and anything that should apply to both systems belongs **upstream**, not here.

> **Status: mostly empty, deliberately.** Entries are added as they are decided, not anticipated. An addendum that fills up with speculation before the port starts is a fork wearing a different hat.

---

## §A1 Long-running non-deterministic activities — 📋 OPEN

A `claude -p` invocation runs 10–60 minutes and returns prose. Upstream activities are seconds-to-minutes and return structured results, so nothing upstream covers this.

Known work, not yet decided:

- **Heartbeating** — an activity of this length must heartbeat or Temporal will consider the worker dead. Cadence and what constitutes progress are undecided.
- **Payload limits** — full transcripts will exceed Temporal's payload limits. The likely shape is transcript-to-file with a reference on the result, matching `stateful_patterns.md` §1's persistence-boundary reasoning and Tekton's lesson that this channel carries **references, not payloads**.
- **Retry semantics** — an LLM run is not deterministic, so a retry is a *new attempt*, not a replay of the same work. Whether that is safe depends entirely on whether the activity is idempotent (§7.1), and for anything that pushes commits or opens PRs, it is not.

## §A2 A producer that can be confidently wrong — 📋 OPEN

Every upstream activity either succeeds, fails, or times out. Ours can **return a plausible-looking but incorrect result** — a fabricated citation, an attested-but-unverified pointer, a verdict that does not match its own findings.

No upstream pattern defends against this, because no upstream producer has the failure mode. Ours are recorded in `docs/standards/workflow-scripts.md`:

- Routing contracts **fail safe to the branch requiring a human**, never to the permissive one.
- Verification is **by fetch, never by plausibility** — a pointer that was not opened is a guess dressed as a citation.
- An account is not the artifact: a run's own summary is a claim *about* its work, to be checked against the work.

**If any of these generalize beyond our use of LLM producers, they belong upstream.** They are here only because upstream has no LLM producers to protect.

## §A3 Machine-axis queue naming — 📋 OPEN

`worker_deployment_standard.md` §2 governs task-queue naming for workers segmented by capability. Ours are additionally segmented by **machine**, because Claude Code must run on the machine that holds the repo — a repo-locality constraint with no upstream equivalent.

Read §2 before naming anything. Queue names are expensive to change once workers are deployed against them.
