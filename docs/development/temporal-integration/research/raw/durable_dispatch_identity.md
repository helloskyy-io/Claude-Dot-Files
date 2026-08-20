# Durable Dispatch Identity and the Per-Subsystem Restart-Recovery Contract

```
Topic:          Where durable dispatch state should live, what a durable dispatch identity must
                contain to work as an idempotency key across a restart, what a per-subsystem
                restart-recovery contract must specify so it is designed once rather than three
                times, and what shape both must take so they survive the bash → Python → Temporal
                port without being rewritten.
Feeds:          docs/development/sprint.md § "Sprint: Temporal Integration" line 188 — "A
                restart-recovery contract — a durable dispatch id and per-subsystem recovery,
                designed once. Retrofitting one onto running workers is a rewrite, so it lands
                with them rather than after" → the Temporal Integration phase doc's recovery
                design. CORRECTED 2026-08-19 — this paper was written for the "Sprint: Fleet
                Reliability" section, which dissolved when this pool moved to
                `docs/development/temporal-integration/research/`; the milestone itself survived
                unchanged and moved with it into Temporal Integration. The paper's content is
                unaffected — only the destination pointer was stale.
Last validated: 2026-08-07
Revalidate:     high — 4 weeks
Confidence:     DEFINITIVE for every identity-model claim about an external system: Temporal's
                Workflow Id / Run Id semantics and both id policies come from raw first-party
                sources returned as exact characters (`workflow.proto` from `temporalio/api`, and
                a whole-file reproduction of `workflowid-runid.mdx`); GitHub Actions, GitLab CI,
                systemd, Kafka, RabbitMQ, SQLite, git, RFC 9562, the IETF Idempotency-Key draft,
                Stripe and AWS SQS likewise came back as exact spans from raw or plain-text forms.
                DEFINITIVE for the Claude Code session/resume surface (§2.6, §4.1, §7 item 5) —
                first-party markdown from `code.claude.com`, reproduced whole — but this is the
                FASTEST-DECAYING material in the paper and drives the header tier (§0.3).
                DEFINITIVE for what this repo's code does today: every statement about
                `run-claude.sh`, the workflow scripts and `assistant_activities.py` is read from
                the files and quoted.
                DERIVED — and marked as such at each site — for the six-part identity model (§2.7),
                the state-store recommendation (§3.6), the recovery-contract table (§4), the
                migration-safe shape and the throw-away/carry-forward split (§5), and the ruling
                on the status-quo argument (§7). Each names its input claims.
                REDUCED CONFIDENCE where a fetch summarized rather than reproduced: the AWS
                Builders' Library article and the IETF datatracker status page are rendered pages
                and are quoted only in short spans; Temporal's default Activity retry policy is
                NOT asserted from my own fetch (it summarized) and is cited to the upstream pool.
                ALSO REDUCED: Candea & Fox's "Crash-Only Software" (§1.1, §3.6) was read as PAGE
                IMAGES of a PDF, so its spans are transcribed visually rather than returned as
                characters; it corroborates and carries nothing (§7.5, §8 gap 4).
                UNVERIFIED at the behavioural level: nothing was executed. No dispatch was run
                with `--session-id`, no resume was attempted, no Temporal workflow was started.
                §9 is the handoff.
                ONE COUNT is asserted (§7.3, the log enumeration) and it is stated as a FLOOR with
                its method; the 0.9% (4/443) figure in the code is quoted as an in-repo assertion
                and explicitly NOT corroborated (§7.3 is a negative finding).
Critic:         PASS-WITH-FIXES (extended three silently-truncated quotations to their source
                sentence ends — the `assistant_activities.py` docstring in §1.2 and both
                `sessions.md` spans in §2.6, all re-fetched before rewriting; withdrew the
                Candea & Fox "unretrievable" negative finding after re-fetching the EPFL PDF and
                reading it through a page renderer, and rewrote §0.4, §1.1, §3.6, §7.5 and §8
                gap 4 around the now-cited source; corrected §0.3's `headless.md` version
                enumeration from 8 to 11 point releases; named SQS's source form explicitly in
                §2.4. One critic finding DISPUTED with evidence: SQS is not a rendered-page
                source — both its `.md` and `.html` paths return the same markdown, see §2.4)
                — 2026-08-07
```

> ## Headline — the status-quo comment is right about resume and silent about identity, and those are different decisions
>
> `run-claude.sh` declines recovery machinery in a comment that is unusually well-formed: it states
> a measured rate, names the failure modes recovery would add, names its own reopen condition, and
> names the fix it would prefer instead.[^runclaude] **This paper grants it.** Auto-resume is the
> wrong build today, and the strongest argument against it is one the comment does not even use:
> Claude Code's own documentation states that a resumed session does **not** restore
> `bypassPermissions`, `--mcp-config`, `--settings`, `--plugin-dir` or `--add-dir`,[^sessions] so a
> resumed dispatch is not the same dispatch — it is a differently-configured one wearing the same
> name.
>
> **But a durable dispatch identity is not recovery machinery.** It is an input. Nothing acts on
> it, so it adds no failure mode of the kind the comment names — no unverified commit, no salvage
> loop. Separating *identity* from *resume* is the whole move, and once separated, three things
> follow that the comment does not address:
>
> - **The comment's own reopen condition is currently unmeasurable.** It reopens "if the rate
>   climbs under unattended/pooled operation."[^runclaude] A `Glob` of `.claude/logs/*.jsonl` in the
>   main checkout returned a list I enumerated and counted: **57 files** — against a stated
>   denominator of 443. `.gitignore` line 2 is `.claude/`,[^gitignore] so logs never leave the
>   machine that made them, and the denominator is not reconstructible from any one machine. **The
>   identity is what makes the comment's own trigger measurable.** (§7.3)
> - **The other four Fleet Reliability items each need a per-dispatch key to write against.** A
>   credential-expiry verdict, a false-completion verdict, a stalled/looping/stranded classification
>   and a notifier message are all statements *about a dispatch*. Without an id they have no subject.
> - **Today's de-facto identity is generated inside the activity from `datetime.now()`** — in bash
>   as `TIMESTAMP=$(date +%Y%m%d-%H%M%S)`,[^planew] and re-derived independently in the Python port
>   as `stamp = datetime.now().strftime("%Y%m%d-%H%M%S")`.[^activities] **Under Temporal that is a
>   fresh identity on every retry**, which is precisely the defect the durable-dispatch-identifier
>   rule exists to prevent. Moving that one line from *inside the activity* to *the activity's
>   input* is the single highest-leverage pre-port change in this paper, and it costs one parameter.
>
> **What is throw-away and what carries forward is unusually clean** (§5). Throw away: any
> claim/lease/TTL/boot-reconciler you might build — Temporal replaces all of it, and both surveyed
> prior-art systems show that is where the complexity lives. Carry forward: the identity function,
> the request fingerprint, the reference-not-payload rule, and the per-subsystem table itself,
> which becomes the activity design document. **The identity you write today becomes the Temporal
> Workflow Id verbatim — if and only if it is not a timestamp.**

---

## 0. Scope, altitude, and how to read the confidence marks

### 0.1 Altitude

**COMPONENT.** The question is *how* to build a recovery contract already committed to by
`sprint.md` line 181. Whether the contract should exist, and whether Temporal is the right
substrate, are settled elsewhere and are not reopened here.[^sprint][^synthesis] Anything found
that bears on what the project *believes* rather than how this component is built is quarantined in
**§10 Escalation** and not acted on.

### 0.2 What is cited rather than re-derived

Per dispatch, four upstream papers in `docs/standards/architecture/research/` are treated as
settled inputs and cited, not re-researched:

| Upstream finding | Where | Used here for |
|---|---|---|
| Per-subsystem restart-recovery contract as a *documentation artifact*; the durable dispatch identifier rule; **it must land before workers are written** | `openclaw_assessment.md` §3.1, §4.4, §6 items 3–4 | §4's table shape; §5's sequencing |
| Three-guard liveness — extend-on-live-PID, reclaim-on-dead-PID, absolute runtime cap | `hermes_assessment.md` §5.4, §7 item 4 | §4.5, §5.5 (what NOT to build now) |
| Durable-execution fundamentals; event sourcing; the ~30-minute threshold below which the discipline is net cost | `durable_execution.md` §1, §5, §6 | §5.1, §7.5 |
| Temporal specifics; default retry policy is unlimited max attempts | `temporal.md`; `synthesis.md` candidate 29 | §5.3 (asserted to upstream, NOT to my own fetch — §8 gap 6) |
| "Plan the three pre-worker recovery items as ONE design session, not three" | `synthesis.md` candidate 9 | §4's premise |

### 0.3 Volatility and the revalidation interval (§5 of the Research Standard)

The paper spans three volatility classes. Per the mixed-volatility rule the header takes the
highest present.

| Material | Class | Why |
|---|---|---|
| **§2.6, §4.1, §7 item 5, §8 gaps 1–3 — the Claude Code session/resume surface** | **HIGH** | Both source documents record behaviour changes at **point-release** granularity. `sessions.md` names v2.1.169, .196, .198, .211, .221 and .223 as boundaries where behaviour differed; `headless.md` names v2.1.163, .169, .182, .203, .204, .205, .211, .214, .219, .221 and .223 — **eleven distinct point releases in one document**. *(Method for both lists: each document was re-fetched whole, I asked the fetch layer to ENUMERATE every `v2.1.NNN` occurrence with its containing sentence rather than to total them, and I reduced the enumeration to distinct versions myself. An earlier draft of this row omitted `headless.md`'s .169, .203 and .223 — the .169–.203 batch-delivery window that v2.1.204 closed, and the cross-directory session-ID lookup boundary — which understated the very volatility this row argues for.)*[^sessions][^headless] A surface documenting that many changes inside one minor version is the fastest-decaying evidence here. |
| §2.1–§2.5, §3, §5 — Temporal identity semantics, state-store trade-offs, the port shape | Medium–Low | `WorkflowIdReusePolicy` is a stable protobuf enum; the only recent change is a *deprecation* with a stated replacement.[^proto] SQLite's and git's constraints are decade-stable. |
| §4, §6 — the contract shape itself | Low | It is a design artifact, not a fact about a vendor. |

**`Revalidate: high — 4 weeks`**, justified: the high band is 2–6 weeks and the Claude Code CLI
surface is demonstrably moving at point-release granularity, which argues for the tight half of
the band; four rather than two because nothing in §2.6 is a *pricing* or *availability* fact that
can vanish overnight — the flags exist and the risk is semantic drift, not disappearance. **A
refresh should re-verify §2.6, §4.1 and §8 gaps 1–3 first and may treat §2.1–§2.5, §3 and §5 as
slow-moving.**

### 0.4 Sourcing discipline, stated because it constrains what this paper may assert

Every claim below about an external system was fetched from a **raw or plain-text** form where one
existed: `raw.githubusercontent.com` for Temporal's protos and docs, GitHub's and GitLab's docs
repos, systemd's man-page XML and git's AsciiDoc; `www.ietf.org/archive/id/*.txt` and
`rfc-editor.org/rfc/*.txt` for the standards; `code.claude.com/docs/en/*.md` and
`docs.stripe.com/api/*` for the markdown forms of those docs. **Default branches were confirmed
from the GitHub contents API before any raw fetch** — `temporalio/api`, `temporalio/temporal`,
`temporalio/documentation`, `temporalio/sdk-python`, `github/docs`, `systemd/systemd` and
`rabbitmq/rabbitmq-website` all report `"default_branch": "main"`; **`apache/kafka` reports
`"default_branch": "trunk"`** and was fetched on `trunk` accordingly.[^ghapi-temporal-api][^ghapi-kafka]

**Three fetches summarized rather than reproduced and are marked down throughout:** Temporal's
`retry-policies.mdx` (so its numbers are cited to the upstream pool instead, §8 gap 6), the AWS
Builders' Library article (rendered; quoted only in the short spans the layer returned inside
quotation marks), and the IETF datatracker status page (rendered). Two directory listings were
obtained by asking the API to **enumerate entries**, never for a total.

**One presentational convention, stated so it is not mistaken for drift:** where a source's text
lives in a markdown table, this paper reproduces the row with **inter-column padding whitespace
normalized** and nothing else changed (GitLab §2.2, Claude Code §2.6). Where a cell's content is a
template include rather than prose, the include's target file is fetched and quoted separately
rather than spliced into the row — see §2.2.

**One source is a PDF, and it is quoted from page images rather than from a character stream.**
Candea & Fox's *Crash-Only Software* was recorded in an earlier draft as unretrievable; a re-check
retrieved it — not by finding a new URL but by reading the downloaded PDF through a page renderer
instead of a prose-summarizing fetch layer (§8 gap 4, which records the withdrawal and the two legs
that remain contested). Its spans are therefore transcribed **visually**, marked at reduced
confidence in §11, and used only to corroborate §3.6 and §2.7. Every other antecedent here is
industrial and first-party.

**One presentational convention for quoted source code:** where a docstring or comment is quoted
from a Python or bash file, the source's hard line wraps are joined with single spaces and nothing
else is changed (§1.2, §4.3). Elisions inside any quotation in this paper are marked; a quotation
that runs to a closing punctuation mark runs to the source's own sentence end.

---

## 1. Primer — the problem, and what this fleet actually has today

### 1.1 What a durable dispatch identity is for

A dispatch is a unit of work handed to a worker that may die. Three questions must be answerable
after the death, by a process that did not witness it:

1. **Is this the same work as that work?** (deduplication)
2. **Did the side effects already happen?** (idempotency)
3. **What was this run, as distinct from the logical job it is an attempt at?** (attribution)

A single opaque string answers none of them reliably. Every system surveyed in §2 answers them
with the *same two-level shape* — a caller-owned logical identifier plus a system-owned per-attempt
identifier — plus, in the systems that take retries seriously, three further components most
hand-rolled designs omit.

**The academic antecedent, added on re-check** *(§8 gap 4; source read as page images, so **reduced
confidence on exact characters** — §0.4).* Candea & Fox's *Crash-Only Software* (HotOS-IX, 2003)
states the design stance this entire contract assumes — that recovery is the normal path, not the
exceptional one: *"Recovery code deals with exceptional situations, and must run flawlessly.
Unfortunately, exceptional situations are difficult to handle, occur seldom, and are not trivial to
simulate during development; this often leads to unreliable recovery code. In crash-only systems,
however, recovery code is exercised every time the system starts up, which should ultimately improve
its reliability."*[^crashonly] It also names, in 2003, two of the components §2.7 finds missing from
this fleet: it requires *"self-describing requests that carry a time-to-live and information on
whether they are idempotent"* — component #4's fingerprint and component #5's horizon, in one clause
— and that *"all important non-volatile state be kept in dedicated state stores"*, which is §3.6's
tier split stated twenty-three years earlier.[^crashonly] **It corroborates; nothing here rests on
it** (§7.5).

### 1.2 What this fleet is, read from the code

**The dispatch activity.** `scripts/workflows/activities/run-claude.sh` defines `run_claude`, which
builds and executes:[^runclaude]

```
    local claude_cmd=(
        claude -p "$prompt"
        --model "$WORKFLOW_MODEL"
        --output-format stream-json
        --verbose
        --max-turns "$MAX_TURNS"
        --dangerously-skip-permissions
        "${extra_args[@]}"
    )
```

Output is `tee`'d to `$LOG_FILE` when `VERBOSE`, and redirected with `>` otherwise. Model identity
is already treated as an explicit, never-derived input — the file's own header states the rule as
"**Every dispatch runs with an EXPLICIT `--model`**" and the resolution order ends in "FAIL LOUD —
never dispatch on an inherited default."[^runclaude] **That principle is exactly the one this
paper extends from *model* to *identity*.**

**The de-facto dispatch identity today** is a filename. **At least twelve** bash scripts under
`scripts/workflows/` independently compute `TIMESTAMP=$(date +%Y%m%d-%H%M%S)` and build the log
path — and, in most of them, the worktree name — from it. *(A floor, not a total: I enumerated the
matches a content search returned and counted twelve distinct files; I cannot certify the search
was exhaustive.)* E.g. `WORKTREE_NAME="plan-new-${TIMESTAMP}"` and
`LOG_FILE="${LOG_DIR}/plan-new-${TIMESTAMP}.jsonl"`.[^planew] The Python port re-derives the same
scheme from a different authority: `stamp = datetime.now().strftime("%Y%m%d-%H%M%S")` and
`log_file = log_dir / f"{model_key}-{stamp}.jsonl"` — **named after the model key, not the
workflow**.[^activities]

**Where state lives today.** Logs go to `${REPO_ROOT}/.claude/logs`; work happens in
`.claude/worktrees/<name>`. `.gitignore` line 2 is `.claude/`.[^gitignore] **Nothing under
`.claude/` is version-controlled, so nothing under `.claude/` crosses a machine boundary.** The
Python port encodes the one durability rule that already exists here, in a docstring: `repo_root`
"is where LOGS live and MUST be the real repository — never a worktree, or the log is deleted with
the worktree it sat inside and cost accounting for that leg becomes impossible." It is enforced by a
guard that raises on `".claude/worktrees" in str(repo_root)`.[^activities]

**The completion contract already exists, and it already knows exit codes lie.** `run-claude.sh`
comments that "**exit 0 must mean the workflow actually finished**" because a headless run "ends on
ANY text-only turn, including a premature 'waiting on dispatched agents…' message: the harness
reports exit 0 with nothing produced," and fails loud when `COMPLETION_PATTERN` is absent from the
final result.[^runclaude] The Python port states the same invariant as a type: `ChildResult`'s
docstring reads "`exit_code == 0` is necessary but NOT sufficient — a child must also satisfy its
completion contract, which is a pattern in its terminal output."[^buildinputs] **This is the
receipt primitive the recovery contract needs (§4.3, rule R3); it exists and is unrecorded.**

### 1.3 The status quo this paper argues with

The turn-cap block is the position to beat, quoted in full because §7 grants most of it:[^runclaude]

```
    # Turn-cap termination — make a silent death LOUD. Deliberately visibility
    # only: no commit, no push, no state file, no resume. Measured rate is
    # 0.9% (4/443 runs, 3 of them from April), every occurrence so far with a
    # human watching, so recovery machinery would add failure modes
    # (unverified commits pushed onto a healthy-looking PR, salvage loops) to
    # serve a sub-1% event that a message already resolves — hand recovery
    # took ~10 minutes once the operator knew where to look. Reopen only if
    # the rate climbs under unattended/pooled operation, and even then the
    # fix is louder signalling, not resume.
```

---

## 2. What a durable dispatch identity must contain — the survey

Six established systems, each fetched first-party. The pattern is consistent enough that the
divergences are the interesting part.

### 2.1 Temporal — the two-level shape, plus two orthogonal policies

`workflowid-runid.mdx`, reproduced whole from the docs repo, states the model directly:[^wfid]

- *"Each Workflow Execution is associated with a user-defined [Workflow ID](#workflow-id), a value
  which typically carries some business meaning (such as an order number or customer number)."*
- *"Temporal guarantees that there can be at most one Workflow Execution with a given ID running at
  any point in time, a constraint that helps to protect against unexpected duplication."*
- *"A Run Id is a globally unique, platform-level identifier for a [Workflow Execution](/workflow-execution)."*
- *"The current Run Id is mutable and can change during a [Workflow Retry](/encyclopedia/retry-policies).
  You shouldn't rely on storing the current Run Id, or using it for any logical choices, because a
  Workflow Retry changes the Run Id and can lead to non-determinism issues."*
- *"A Workflow Execution can be uniquely identified across all Namespaces by its
  [Namespace](/namespaces), Workflow Id, and [Run Id](#run-id)."*

Two further properties matter for a hand-rolled design.

**(a) Uniqueness is bounded by a retention horizon, not forever.** *"For example, given a default
Retention Period, the Temporal Service can only check the Workflow Id of the spawning Workflow
Execution based on the Workflow Id Reuse Policy against the Closed Workflow Executions for the last
_30 days_."*[^wfid]

**(b) "Can I reuse this id?" and "what if one is running?" are TWO policies, not one.** The
protobuf enums, fetched as exact characters from `temporalio/api`:[^proto]

```protobuf
// Defines whether to allow re-using a workflow id from a previously *closed* workflow.
// If the request is denied, the server returns a `WorkflowExecutionAlreadyStartedFailure` error.
//
// See `WorkflowIdConflictPolicy` for handling workflow id duplication with a *running* workflow.
enum WorkflowIdReusePolicy {
    WORKFLOW_ID_REUSE_POLICY_UNSPECIFIED = 0;
    // Allow starting a workflow execution using the same workflow id.
    WORKFLOW_ID_REUSE_POLICY_ALLOW_DUPLICATE = 1;
    // Allow starting a workflow execution using the same workflow id, only when the last
    // execution's final state is one of [terminated, cancelled, timed out, failed].
    WORKFLOW_ID_REUSE_POLICY_ALLOW_DUPLICATE_FAILED_ONLY = 2;
    // Do not permit re-use of the workflow id for this workflow. Future start workflow requests
    // could potentially change the policy, allowing re-use of the workflow id.
    WORKFLOW_ID_REUSE_POLICY_REJECT_DUPLICATE = 3;
```

```protobuf
// Defines what to do when trying to start a workflow with the same workflow id as a *running* workflow.
// Note that it is *never* valid to have two actively running instances of the same workflow id.
//
// See `WorkflowIdReusePolicy` for handling workflow id duplication with a *closed* workflow.
enum WorkflowIdConflictPolicy {
    WORKFLOW_ID_CONFLICT_POLICY_UNSPECIFIED = 0;
    // Don't start a new workflow; instead return `WorkflowExecutionAlreadyStartedFailure`.
    WORKFLOW_ID_CONFLICT_POLICY_FAIL = 1;
    // Don't start a new workflow; instead return a workflow handle for the running workflow.
    WORKFLOW_ID_CONFLICT_POLICY_USE_EXISTING = 2;
    // Terminate the running workflow before starting a new one.
    WORKFLOW_ID_CONFLICT_POLICY_TERMINATE_EXISTING = 3;
}
```

The deprecated fourth reuse value carries the migration note verbatim: *"Deprecated. Instead, set
`WorkflowIdReusePolicy` to `ALLOW_DUPLICATE` and `WorkflowIdConflictPolicy` to
`TERMINATE_EXISTING`. Note that `WorkflowIdConflictPolicy` requires Temporal Server v1.24.0 or
later."*[^proto] **The direction of travel is toward *more* separation of the two questions, not
less** — which is the strongest available argument for writing them down separately now.

*(All of §2.1: **definitive**.)*

### 2.2 GitHub Actions and GitLab CI — the same two levels, and an explicit uniqueness scope

GitHub Actions exposes three, from the `github` context table in `github/docs`. **The two texts
come from two different files and are quoted separately rather than spliced into one row**, because
the context table does not contain the `run_id` prose — its cell is the literal
`{% data reusables.actions.run_id_description %}`, which I then fetched:[^ghcontexts][^ghrunid]

- `github.run_id`, whole content of `data/reusables/actions/run_id_description.md`:
  *"A unique number for each workflow run within a repository. This number does not change if you
  re-run the workflow run."*
- `github.run_attempt`, the third cell of its row in `contexts.md` (prose present inline there):
  *"A unique number for each attempt of a particular workflow run in a repository. This number
  begins at 1 for the workflow run's first attempt, and increments with each re-run."*

That is Temporal's shape with a counter instead of a UUID: `run_id` is stable across re-runs,
`run_attempt` distinguishes them. GitLab CI adds the axis Temporal calls Namespace and makes it
explicit in the *name*:[^gitlabvars]

```
| `CI_PIPELINE_ID`  | Job-only | The instance-level ID of the current pipeline. This ID is unique across all projects on the GitLab instance. |
| `CI_PIPELINE_IID` | Pipeline | The project-level IID (internal ID) of the current pipeline. This ID is unique only in the current project. |
```

**Two identifiers for the same object, differing only in the scope of their uniqueness, and the
scope is in the name.** *(definitive)*

### 2.3 systemd — the per-attempt id, named for what it is

systemd's journal-field man page defines the invocation ID as *"A randomized, unique 128-bit ID
identifying each runtime cycle of the unit"*,[^journalfields] and the `sd_id128` page states it is
*"the invocation ID of the currently executed service"*, sourced from *"The `$INVOCATION_ID`
environment variable that the service manager sets when activating a service"* and guaranteed to be
*"UUID Variant 1 Version 4 compatible."*[^sdid128]

The pairing is the point: **the logical identifier is the unit name (stable, operator-chosen); the
per-attempt identifier is the invocation ID (random, regenerated every start).** A supervised
long-lived process — which is what the fleet's own deployment target is, per the upstream
pool[^openclaw] — gets exactly the two-level identity for free, and this fleet gets neither because
it is not a unit.

*(definitive)*

### 2.4 Message queues — where identity is deliberately NOT durable, and what that costs

RabbitMQ's delivery tag is the anti-pattern, stated first-party: it *"uniquely identifies the
delivery on a channel"*, *"Delivery tags are therefore scoped per channel"*, and they *"are
monotonically growing positive integers"*; consumers *"must be prepared to handle redeliveries and
otherwise be implemented with idempotence in mind."*[^rabbit] **A session-scoped monotonic counter
is not an identity — it is a cursor, and the protocol pushes the deduplication burden onto the
consumer.** Today's `<workflow>-<timestamp>` is closer to a delivery tag than to a Workflow Id.

Kafka closes the same gap the way Temporal does — by pairing a producer-level id with a
per-message counter. `docs/design/design.md` on `trunk`: *"Since 0.11.0.0, the Kafka producer also
supports an idempotent delivery option which guarantees that resending will not result in duplicate
entries in the log"*, and *"To achieve this, the broker assigns each producer an ID and deduplicates
messages using a sequence number that is sent by the producer along with every message."*[^kafka]

AWS SQS supplies the third component the two-level shape does not carry — **a bounded horizon**.
`MessageDeduplicationId` *"is a token used only in Amazon SQS FIFO queues to prevent duplicate
message delivery. It ensures that within a 5-minute deduplication window, only one instance of a
message with the same deduplication ID is processed and delivered."*[^sqs]

*(definitive, and the source form is now stated per system rather than in one blanket tag. RabbitMQ
and Kafka: raw `.md` fetches that added their own headings around the quoted spans — the spans are
exact, the framing is the layer's. **SQS: also a markdown document, and the claim was contested and
re-checked** — a critic pass reported that no raw form exists because a non-redirect-following
request to the `.md`-suffixed path returns `301`. On re-fetch I retrieved **both** the `.md` and the
`.html` path and each returned the **same markdown source** — `<a name="using-messagededuplicationid-property"></a>`
anchors and `.md`-suffixed cross-links in the "Topics" list, which a rendered-HTML page would not
carry — with the span above character-exact in both. The `301` is real and is a redirect to the
markdown, not evidence of its absence, so SQS stays in the raw/plain-text tier. §11's entry records
both URL forms.)*

### 2.5 HTTP idempotency keys — the fingerprint, the expiry, and a standards gap

The IETF draft, fetched as plain text, is the closest thing to a general statement of the rules —
and it is **not a ratified standard**:[^ietf07]

```
2.2.  Uniqueness of Idempotency Key

   The idempotency key MUST be unique and MUST NOT be reused with
   another request with a different request payload.

   Uniqueness of the key MUST be defined by the resource owner and MUST
   be implemented by the clients of the resource.  It is RECOMMENDED
   that a UUID [RFC4122] or a similar random identifier be used as an
   idempotency key.

2.3.  Idempotency Key Validity and Expiry

   The resource MAY require time based idempotency keys to be able to
   purge or delete a key upon its expiry.  The resource SHOULD define
   such expiration policy and publish it in the documentation.

2.4.  Idempotency Fingerprint

   An idempotency fingerprint MAY be used in conjunction with an
   idempotency key to determine the uniqueness of a request.  Such a
   fingerprint is generated from request payload data by the resource.
```

**Standardization status is a finding, not a footnote.** The `-07` header reads `Expires: 18 April
2026` against a date of `15 October 2025`,[^ietf07] and the datatracker page for the draft reports
the document as expired and archived.[^datatracker] *(The status line is from a rendered page —
**reduced confidence**; the expiry date is from the plain-text draft — **definitive**.)* **There is
no ratified cross-vendor standard for idempotency keys**, which means the convergent practice below
is the evidence, not a spec.

Two implementations corroborate the same three rules from opposite ends of the industry:

- **Stripe.** *"A client generates an idempotency key, which is a unique key that the server uses
  to recognize subsequent retries of the same request."* — and, in the sentence immediately
  following it, *"How you create unique keys is up to you, but we suggest using V4 UUIDs, or another
  random string with enough entropy to avoid collisions."* On horizon and mismatch:
  *"You can remove keys from the system
  automatically after they're at least 24 hours old. We generate a new request if a key is reused
  after the original is pruned. The idempotency layer compares incoming parameters to those of the
  original request and errors if they're not the same to prevent accidental misuse."*[^stripe]
- **AWS** (Malcolm Featonby, Builders' Library — *rendered page, quoted only in spans*): *"At
  Amazon, our preferred approach is to incorporate a unique caller-provided client request
  identifier into our API contract."* On horizon: *"We have found that, for EC2 instances, it works
  to limit the time period to the lifetime of the resource, plus an interval after which it is
  reasonable to assume that any late arriving requests would either have arrived or would no longer
  be valid."* On mismatch: *"We find that it is safest to assume that the customer intended a
  different outcome, and that this might not be the same request. In response to this situation, we
  return a validation error indicating a parameter mismatch between idempotent requests."*[^aws]

**Three independent sources agree that a key with a *different payload* must ERROR, not replay.**
That is the component with no analogue anywhere in this fleet today.

### 2.6 The one this fleet actually dispatches — Claude Code already accepts a caller-supplied identity

This is the highest-value discovery in the paper, and it is first-party documented. From the CLI
reference — quoted as the exact cell text of three flag rows, with inter-column whitespace
normalized and nothing else altered:[^cli]

- **`--session-id`** — *"Use a specific session ID for the conversation (must be a valid UUID)"*,
  with the example `claude --session-id "550e8400-e29b-41d4-a716-446655440000"`.
- **`--resume`, `-r`** — *"Resume a specific session by ID or name, or show an interactive picker to
  choose a session."* and, later in the same cell, *"When you pass a session ID, Claude Code
  searches the current project directory and its git worktrees, then every other project on this
  machine."* *(Two separate sentences from one cell; intervening and following text about the picker
  and about pre-v2.1.223 behaviour is omitted, not elided inside a quotation.)*
- **`--fork-session`** — *"When resuming, create a new session ID instead of reusing the original
  (use with `--resume` or `--continue`)"*.

And from `sessions.md`, reproduced whole:[^sessions]

- *"Sessions created with [`claude -p`](/docs/en/headless) or the [Agent SDK](/docs/en/agent-sdk/overview)
  don't appear in the session picker, but you can still resume one by passing its session ID to
  `claude --resume <session-id>`."*
- *"By default, transcripts are stored as JSONL at `~/.claude/projects/<project>/<session-id>.jsonl`,
  where `<project>` is your working directory path with non-alphanumeric characters replaced by `-`."*
- Retention is *"the 30-day retention"*, configurable via `cleanupPeriodDays`; storage relocatable
  via `CLAUDE_CONFIG_DIR`; writes suppressible per-run via `--no-session-persistence`.
- **The constraint that decides §7**, both spans carried to the source's own sentence end, with the
  inline markdown link targets left intact so the characters are the document's:
  *"Permission mode: the mode the session was in. `plan` and `bypassPermissions` are never restored;
  [bypassing permissions](/docs/en/permission-modes#skip-all-checks-with-bypasspermissions-mode) must
  be enabled again at launch, with one of its launch flags or `permissions.defaultMode:
  "bypassPermissions"` in [settings](/docs/en/settings#permission-settings)."* — and —
  *"If the session depended on `--mcp-config`, `--settings`, `--plugin-dir`, `--fallback-model`, or
  directories added with `--add-dir`, pass them again when you resume; directories added mid-session
  with `/add-dir` aren't restored either, though the session picker still uses them to locate the
  session."*
- **The constraint that decides §3:** the cross-project ID search covers *"every other project on
  this machine"* — there is no documented cross-machine resolution.

**Four consequences, all definitive:**

1. The dispatch subsystem **already accepts a caller-supplied UUID identity**. Nothing needs to be
   invented to give a dispatch a stable per-attempt id; a flag needs to be passed.
2. Resume **is** available for `claude -p` runs. The status quo's "no resume" is therefore a
   *policy*, not a capability ceiling — which strengthens §7's case-against, because a deliberate
   refusal of an available feature is a stronger position than an unexamined absence.
3. **A resumed session runs in a different configuration than the one it resumes** unless every
   launch flag is re-passed — and `--dangerously-skip-permissions` is specifically among the ones
   never restored. Any resume the fleet ever builds must re-supply the full launch vector.
4. Transcript state is **machine-local and 30-day-expiring**. A dispatch record that outlives its
   transcript points at nothing (§5.6).

### 2.7 The model — six components, derived

*(**derived** — inputs: §2.1 Temporal's Workflow Id/Run Id/Namespace and the two policies; §2.2
GitHub's `run_id`/`run_attempt` and GitLab's ID/IID scope split; §2.3 systemd's unit-name /
invocation-ID pairing; §2.4 RabbitMQ's channel scoping, Kafka's producer-id + sequence, SQS's
5-minute window; §2.5 the IETF draft's uniqueness/expiry/fingerprint sections, Stripe's
parameter-comparison rule and AWS's caller-provided-identifier and horizon rules. The synthesis
across them is mine; no single source states all six.)*

| # | Component | Owned by | Every surveyed system's version | This fleet today |
|---|---|---|---|---|
| 1 | **Logical id** — deterministic from the work, stable across every retry | the **caller** | Temporal Workflow Id · GH `run_id` · systemd unit name · Kafka producer id | ❌ generated inside the activity from wall-clock time |
| 2 | **Attempt id** — unique per execution, never used for logic | the **system** | Temporal Run Id · GH `run_attempt` · systemd `$INVOCATION_ID` · Kafka sequence number | ❌ none; the timestamp is doing both jobs |
| 3 | **Uniqueness scope**, named | design-time | Temporal Namespace · GitLab ID vs IID · RabbitMQ channel | ❌ implicit: one repo's log dir on one machine |
| 4 | **Request fingerprint** — same key + different payload ⇒ **error** | the **store** | IETF §2.4 · Stripe parameter comparison · AWS parameter-mismatch validation error | ❌ none |
| 5 | **Retention horizon**, bounded and stated | the **store** | Temporal ~30 d · Stripe 24 h · SQS 5 min · AWS "lifetime + interval" | ❌ unbounded in intent, unreliable in fact (§7.3) |
| 6 | **Two conflict rulings** — one for *closed*, one for *running* | design-time | Temporal's two orthogonal enums | ❌ none; concurrent same-second runs share a log path, and `>` clobbers |

**The two omissions that matter most are #1 and #6.** #1 is a one-parameter change with a large
downstream consequence (§5.2). #6 is free — it is a written ruling, not code — and it is the one
Temporal will ask for by name on day one of the port.

**On the shape of the attempt id (#2): use UUIDv7, not a timestamp string.** RFC 9562 §5.7:
*"UUIDv7 features a time-ordered value field derived from the widely implemented and well-known
Unix Epoch timestamp source, the number of milliseconds since midnight 1 Jan 1970 UTC, leap seconds
excluded"*, with the remaining bits random *"to provide uniqueness"*, and the standard states
*"Implementations SHOULD utilize UUIDv7 instead of UUIDv1 and UUIDv6 if possible."*[^rfc9562]
*(derived from that text plus §2.6: it sorts chronologically the way today's filenames do — the one
property the current scheme actually buys — while being globally unique, and it satisfies
`--session-id`'s "must be a valid UUID" requirement without a second identifier.)*

---

## 3. Where the state should live — the comparative landscape

Four candidates, judged against the constraint that actually binds: **multiple machines, one
operator, one subscription, no server today, a Temporal server on a backed-up VM later.**

### 3.1 Option A — a filesystem state directory

Zero dependencies, trivially greppable, matches the existing `.claude/logs/` habit, and atomic
enough for a single writer via `rename(2)`.

**The disqualifying fact is one line long:** `.gitignore` line 2 is `.claude/`.[^gitignore]
Anything written there is invisible to every other machine, forever. A state dir *outside*
`.claude/` and committed would work — but then it is Option C wearing a different name, and it
inherits merge conflicts without inheriting git's compare-and-swap.

**Verdict: correct for Tier 2 (bulk transcripts), disqualified for Tier 1 (the record).**

### 3.2 Option B — SQLite

The obvious choice on prior art: the largest comparator in the upstream pool runs on it, with
per-agent and shared databases and boot-time reconciliation.[^openclaw]

**SQLite's own documentation rules it out for the fleet-wide tier**, and the reason is corruption,
not performance:[^sqlite]

```
If there are many client programs sending SQL to the same database over a network, then use a
client/server database engine instead of SQLite. SQLite will work over a network filesystem, but
because of the latency associated with most network filesystems, performance will not be great.
Also, file locking logic is buggy in many network filesystem implementations (on both Unix and
Windows). If file locking does not work correctly, two or more clients might try to modify the same
part of the same database at the same time, resulting in corruption. Because this problem results
from bugs in the underlying filesystem implementation, there is nothing SQLite can do to prevent it.
```

```
A good rule of thumb is to avoid using SQLite in situations where the same database will be accessed
directly (without an intervening application server) and simultaneously from many computers over a
network.
```

**Verdict: SQLite solves multi-*process*-on-one-*machine*, which is not this fleet's problem.**
*(derived — inputs: the two quoted passages; the multi-machine constraint in the dispatch; the
upstream finding that the comparator running on SQLite is explicitly single-Gateway-per-host.[^openclaw])*
It remains a perfectly good **per-machine** store if one is ever wanted, and it is a strictly worse
one than a directory of JSON files until there is a concurrency problem to solve.

### 3.3 Option C — git-native

**The only candidate that already crosses machines with zero new infrastructure**, because the
fleet already pushes to GitHub on every dispatch. Three sub-shapes, and they are not equivalent.

**(i) Refs (`refs/dispatch/<id>`), written with `git update-ref`.** This is the strong form, because
git gives compare-and-swap directly:[^updateref]

```
Given three arguments, stores the <new-oid> in the <ref>, possibly dereferencing the symbolic refs,
after verifying that the current value of the <ref> matches <old-oid>.
```

```
If all <ref>s can be locked with matching <old-oid>s simultaneously, all modifications are performed.
Otherwise, no modifications are performed.  Note that while each individual <ref> is updated or
deleted atomically, a concurrent reader may still see a subset of the modifications.
```

A per-dispatch ref under a dedicated namespace is a natural fit for component #6: creating
`refs/dispatch/<logical-id>` with `<old-oid>` = zero **is** the conflict policy, enforced by git.
Cost: refs outside `refs/heads/*` and `refs/tags/*` need explicit refspecs to travel.

**(ii) Notes (`refs/notes/*`).** Attractive for attaching a verdict to a commit, and the wrong
default for concurrent writers. `git-notes` states: *"The default notes merge strategy is `manual`,
which checks out conflicting notes in a special work tree for resolving notes conflicts
(`.git/NOTES_MERGE_WORKTREE`), and instructs the user to resolve the conflicts in that work
tree."*[^gitnotes] `union` and `cat_sort_uniq` exist and are line-oriented, which fits an
append-only event log and not a mutable record. **A notes-based store defaults to blocking on a
human, which is the opposite of what a recovery contract is for.**

**(iii) GitHub issues / PR comments.** Server-side-serialized, already the operator's reading
surface, already the routing target the Research Standard names for no-change outcomes.[^standard]
Costs a network round-trip and an API dependency on the recovery path — which is the wrong
dependency to hold at exactly the moment things are failing.

**Verdict: (i) for the machine-readable record, (iii) for the operator-facing notification. Not (ii).**

### 3.4 Option D — the workflow engine's own history

Only available after the port, and **Temporal's own documentation declines the job.**
`search-attributes.mdx`, on where business state goes:[^searchattrs]

```
For business logic in which you need to get information about a Workflow Execution, consider one of the following:

- Storing state in a local variable and exposing it with a Query.
- Storing state in an external datastore through Activities and fetching it directly from the store.
```

And the history is capacity-bounded: *"the Workflow Execution's Event History is limited to 51,200
Events or 50 MB and will warn you after 10,240 Events or 10 MB"*, with per-workflow caps of
*"2,000 for each type"* of incomplete Activity, Child Workflow, Signal or Cancellation
request.[^limits]

**Verdict: Temporal's history is an execution log, not the state store. Even post-port, Tier 1
needs a home outside it** — which is why choosing that home now is not wasted work.

### 3.5 Comparison

| | A — `.claude/` state dir | B — SQLite | C(i) — git refs | C(iii) — GitHub issues | D — Temporal history |
|---|---|---|---|---|---|
| Crosses machines | ❌ gitignored[^gitignore] | ❌ corruption risk over network FS[^sqlite] | ✅ with an explicit refspec | ✅ | ✅ (post-port) |
| Concurrency control | single-writer only | one writer, one machine[^sqlite] | ✅ CAS via `<old-oid>`[^updateref] | ✅ server-side | ✅ |
| Available today | ✅ | ✅ | ✅ | ✅ | ❌ |
| Survives worktree removal | ✅ if in repo root, ❌ if in the worktree[^activities] | ✅ | ✅ | ✅ | ✅ |
| Operator reads it without tooling | ✅ | ❌ | ~ (`git log`/`show`) | ✅ | ~ (engineer-facing UI) |
| Suitable for bulk transcripts | ✅ | ❌ | ❌ | ❌ | ❌ (§3.4 limits) |
| Survives the port unchanged | ✅ as Tier 2 | ❌ replaced | ✅ as Tier 1 | ✅ | n/a |

### 3.6 Recommendation — two tiers, and the split is the finding

*(**derived** — inputs: §3.1–§3.5; §2.6's machine-local, 30-day transcript storage; the upstream
finding that Temporal's External Payload Storage keeps large payloads out of history and lands
"only references" in it;[^durexec] Candea & Fox's requirement that *"all important non-volatile
state be kept in dedicated state stores"*, which is the same split reached from the
crash-only direction.[^crashonly])*

- **Tier 1 — the dispatch RECORD.** Small, fixed-schema, one per logical dispatch. Contains the six
  components of §2.7 plus pointers. Lives **git-native** (`refs/dispatch/*` with CAS creation), and
  is therefore the only fleet state that crosses a machine boundary. **This is what becomes the
  Temporal Workflow Id + memo/search attributes.**
- **Tier 2 — the BULK.** The `stream-json` log, the Claude Code transcript, the worktree. Stays a
  **local file, referenced by `(machine-id, absolute path)` and never moved.** Under Temporal this
  is unchanged: activities return references, not payloads.

**The record must never contain a payload, and the payload must never contain the identity.** That
inversion is the single rule that makes the two tiers portable, and it is the rule the current
design breaks by putting the identity *in the filename of the payload*.

---

## 4. The per-subsystem recovery contract — what it must specify, once

Upstream established the *artifact* — a table answering, per subsystem, "what state exists, where
it is stored, what happens to it on boot" — and established that it must be written **before**
workers are.[^openclaw] Upstream also established that the three pre-worker recovery items should
be **one** design session, not three.[^synthesis] This section states what the table's columns must
be for this fleet, and enumerates the rows.

### 4.1 The columns

The three-column shape is necessary and not sufficient here. Three more columns are needed because
this fleet's failure modes differ from a resident gateway's:

| Column | Why it is needed here |
|---|---|
| 1. **Subsystem** | — |
| 2. **What state exists** | — |
| 3. **Where it is stored** | — |
| 4. **Tier** (record / bulk, per §3.6) | Decides whether it crosses a machine. Absent, every row silently defaults to "machine-local," which is today's bug. |
| 5. **Is the side effect replayable?** | The fleet's side effects include `git push` and `gh pr create`, which are **not** idempotent. Upstream calls this the *"is this side effect replayable?"* audit the activity/workflow seam assumes but does not enumerate.[^openclaw] |
| 6. **What the operator sees** | The sprint's notifier item[^sprint] is the consumer of this column; without it, the notifier has to re-derive per-subsystem semantics. |

### 4.2 The rows

*(**derived** — inputs: the code read in §1.2; §2.6's session/transcript facts; upstream's
enumeration of a comparable system's subsystems.[^openclaw] The row set is mine and is a **floor**
— it covers what the current fleet has, not everything a future fleet will.)*

| Subsystem | State | Where | Tier | Replayable? | Operator sees |
|---|---|---|---|---|---|
| **Dispatch (`claude -p`)** | conversation transcript | `~/.claude/projects/<project>/<session-id>.jsonl`, machine-local, 30-day default retention[^sessions] | bulk | **conditionally** — `--resume <id>` works but does not restore `bypassPermissions`, `--mcp-config`, `--settings`, `--add-dir`[^sessions] | the log path + terminal reason |
| **Run log** | `stream-json` JSONL | `${REPO_ROOT}/.claude/logs/<name>.jsonl`, gitignored[^gitignore] | bulk | n/a (append-only artifact) | the path, already printed[^activities] |
| **Worktree** | uncommitted work | `.claude/worktrees/<name>`, gitignored[^gitignore] | bulk | n/a | `cd <wt> && git status`, already printed[^runclaude] |
| **Git side effects** | commits, pushes | the repo / the remote | record | **push: yes** (same commits) | branch state |
| **PR side effects** | the PR, its comments | GitHub | record | **NO** — a second `gh pr create` makes a second PR | the PR URL, which is the completion contract's payload[^activities] |
| **Parent sequencing** | which child ran, verdict, loop count | **in memory only** — bash variables in V1; `BuildResult.loops_used`/`.notes` in V2[^buildinputs] | record | n/a | nothing today |
| **Guard: credential expiry** | probe result + timestamp | **nowhere yet** | record | yes (pure probe) | notifier |
| **Guard: false completion** | contract-satisfied verdict | **nowhere yet** — computed in `run_claude` and discarded[^runclaude] | record | yes (pure predicate) | notifier |
| **Guard: safety-hook wiring** | wiring-test result | **nowhere yet** | record | yes (pure probe) | notifier |

**Three rows read "nowhere yet," and they are exactly the sprint's three cheap guards.** That is
the concrete answer to "designed once, not three times": **each guard is a ROW in one table, not a
design of its own.** What is designed once is the record schema, the identity, and the six columns;
what each guard supplies is a value.

**One row is the most under-appreciated:** *Parent sequencing* is state that exists only in a live
process. A parent that dies between child #2 and child #3 loses the knowledge that #1 and #2
succeeded, and the only durable trace is two log files whose names encode a wall-clock time. **This,
not the turn cap, is the largest recoverability gap in the current fleet** *(derived — inputs: the
V1 scripts' use of shell variables for loop state; `BuildResult`'s in-memory fields;[^buildinputs]
the absence of any state file in `run-claude.sh`[^runclaude])*.

### 4.3 The three rules, adopted verbatim and translated

The upstream paper mined three rules from a shipping system; I re-fetched them at source to hold
their exact characters. From `docs/gateway/restart-recovery.md`:[^restartrecovery]

1. *"Every retry reuses one durable dispatch identifier, so an ambiguous connection failure cannot
   start the same recovery twice."*
2. *"Recovery never replays a hook interrupted mid-call."*
3. *"Recovery completes a delivered receipt without rerunning tools."*

Translated to this fleet *(**derived** — inputs: those three sentences; the row table in §4.2;
§1.2's completion-contract mechanism)*:

- **R1 — one id per logical dispatch, forever.** A new id means new work. A retry, a resume and a
  reconciliation all reuse the id. *This is component #1 of §2.7 and it is the only rule that
  requires a code change today.*
- **R2 — never re-run a non-replayable side effect without observing first.** The non-replayable set
  is enumerated in §4.2 column 5 and today has exactly one member: PR creation. The pattern already
  exists in the codebase — the Python port raises with observed git state attached, under the
  comment "OBSERVE before reporting. A turn-cap exit may have committed and pushed real work;
  asserting otherwise costs a duplicate full-budget run."[^activities] **R2 generalises that one
  instance into a rule.**
- **R3 — record the receipt when the contract is satisfied, not when the process exits.** The
  completion-contract check already computes exactly this verdict and then discards
  it.[^runclaude][^buildinputs] Persisting it costs one write and converts "the harness died, state
  unknown" into "the work completed, the harness died."

### 4.4 What "all three guards" means — and the ambiguity that must be resolved in the phase doc

The sprint milestone says the contract must cover "all three guards."[^sprint] **The sprint
contains two different triples**, and a third exists upstream:

| Triple | Where | Members |
|---|---|---|
| **A — the three cheap guards** | `sprint.md` line 180 | credential expiry · false completion · safety-hook wiring test |
| B — the three-legged liveness predicate | `sprint.md` line 182 | stalled · looping · stranded |
| C — three-guard liveness (prior art) | `hermes_assessment.md` §5.4, §7 item 4 | extend-on-live-PID · reclaim-on-dead-PID · absolute runtime cap[^hermes] |

**This paper reads "all three guards" as A**, because it is the immediately preceding bullet in the
same sprint section and is the only one the sprint calls "guards." **The contract designed here
serves all three triples**, because each member of each is a row in §4.2's table plus a value in
the record — but the phase doc should state which reading it adopts rather than inherit the
ambiguity. *(Flagged as a planning-artifact wording item in §10; a research run does not edit
planning artifacts.[^standard])*

### 4.5 What the contract must NOT specify yet

Upstream supplies a liveness triple — claim TTL with extension on a live PID, reclamation on a dead
one, and an absolute wall-clock cap "regardless of PID liveness"[^hermes] — and it is genuinely
good design. **It is also precisely the layer Temporal replaces** (§5.5). The contract should
*name* the three liveness predicates as record fields (so the guards have somewhere to write) and
**not** specify the claim/lease mechanism that consumes them.

---

## 5. The port constraint — what Temporal gives, what it does not, and what is thrown away

### 5.1 What Temporal already provides

*(definitive except where marked; the fundamentals are cited upstream rather than re-derived.[^durexec])*

| Component of §2.7 | Temporal's answer | Source |
|---|---|---|
| #1 Logical id | Workflow Id — caller-supplied, *"meant to be a business-process identifier"* | [^wfid] |
| #2 Attempt id | Run Id — *"globally unique, platform-level"*, mutable, explicitly not for logic | [^wfid] |
| #3 Scope | Namespace; *"uniquely identified across all Namespaces by its Namespace, Workflow Id, and Run Id"* | [^wfid] |
| #5 Horizon | the Namespace Retention Period, worked example *"the last _30 days_"* | [^wfid] |
| #6 Two rulings | `WorkflowIdReusePolicy` (closed) and `WorkflowIdConflictPolicy` (running) | [^proto] |
| At-most-one-running | *"there can be at most one Workflow Execution with a given ID running at any point in time"* | [^wfid] |
| Retry + timeouts | per-activity retry policy and timeouts | [^actexec][^durexec] |

### 5.2 What Temporal does NOT provide — and the trap this fleet is already standing in

**(a) Activity idempotency is the application's job.** *"Temporal guarantees that an Activity Task
either runs or timeouts. There are multiple failure scenarios when an Activity Task is lost. It can
be lost during delivery to a Worker or after the Activity Function is called and the Worker
crashed. Temporal doesn't detect task loss directly. It relies on Start-To-Close timeout."*[^actexec]
An activity that creates a PR can therefore be invoked twice. **Component #4 (the fingerprint) is
not supplied by Temporal and must be built either way.**

**(b) A business state store is not supplied** — §3.4; Temporal's own docs point at *"an external
datastore through Activities."*[^searchattrs]

**(c) Determinism is a constraint on the author, not a free property.** The upstream Temporal paper
already records this;[^synthesis] the concrete instance here is `datetime.now()`.

**(d) THE TRAP, stated plainly.** The identity is currently minted **inside** the thing that
retries:

```python
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"{model_key}-{stamp}.jsonl"
```

— in `assistant_activities.run_claude`, the function the port's Stage B will decorate with
`@activity.defn`.[^activities] **Every Temporal retry of that activity produces a different
identity and a different log file.** Temporal's default Activity retry policy has unlimited maximum
attempts (cited upstream, not re-fetched — §8 gap 6),[^synthesis] so the failure mode is not one
duplicate but an unbounded fan of them. *(derived — inputs: the quoted code; Temporal's activity
retry semantics;[^actexec] the upstream default-retry finding.)* **Fixing this before Stage B is
the paper's top recommendation and it is a one-parameter change: the identity becomes an input.**

### 5.3 The migration-safe shape

*(**derived** — inputs: §2.7's six components; §2.1's Temporal semantics; §2.6's `--session-id`;
§3.6's two tiers; RFC 9562 §5.7.[^rfc9562] The mapping is mine.)*

| Component | Today (bash + Python, pre-Temporal) | After the port | Rewrite cost |
|---|---|---|---|
| #1 Logical id | a **caller-computed string** passed as an argument: `<workflow>/<repo-slug>/<task-fingerprint>` | **becomes the Workflow Id verbatim** | **zero** |
| #2 Attempt id | a **UUIDv7** minted by the caller, passed to `claude --session-id`[^cli][^rfc9562] | **Temporal's Run Id supersedes it** for orchestration; the UUID stays as the Claude Code session handle | zero — nothing keys logic on it, per Temporal's own warning[^wfid] |
| #3 Scope | `(machine-id, repo)` written into the record | `(Namespace, Task Queue)` | small — a field moves |
| #4 Fingerprint | a hash over the task inputs, stored in the record | **unchanged** — Temporal does not supply it[^actexec] | **zero** |
| #5 Horizon | stated in the record schema; **must be ≥ the transcript's 30-day default**[^sessions] | Namespace Retention Period, default worked example 30 days[^wfid] | zero if aligned now |
| #6 Two rulings | two written policy lines per dispatch class | **two `StartWorkflowOptions` fields**[^proto] | **zero — the ruling is the deliverable** |
| Tier 1 store | `refs/dispatch/*` with CAS[^updateref] | still needed — Temporal declines the job[^searchattrs] | zero |
| Tier 2 store | local files, referenced | unchanged; matches the external-payload pattern[^durexec] | zero |

**Recommended default for #6**, and it should be written as a ruling now:
`WORKFLOW_ID_REUSE_POLICY_ALLOW_DUPLICATE_FAILED_ONLY` + `WORKFLOW_ID_CONFLICT_POLICY_FAIL` — a
*completed* dispatch is never silently re-run under the same id, and a duplicate launch while one is
live **fails loudly** rather than starting a second run against the same worktree. *(**derived** —
the enum names and their semantics are definitive from the proto;[^proto] the choice is mine, and
it follows from §4.2's non-replayable PR row and from the worktree being a single-writer
resource. The alternative, `USE_EXISTING`, is attractive for an idempotent re-dispatch and should be
revisited once the parent can attach to a running dispatch — it cannot today.)*

### 5.4 What gets thrown away

*(**derived** — inputs: §5.1's table; the upstream liveness triple;[^hermes] `durable_execution.md`
§5's enumeration of what the substrate provides.[^durexec])*

Anything that **schedules, leases, times, reclaims or reconciles**:

- a claim/lease table and its TTL; extension-on-live-PID; reclamation-on-dead-PID
- a boot-time reconciler that scans for orphans
- retry bookkeeping, backoff, attempt counters
- timers, cron scheduling, and wake-ups
- any hand-rolled "is this worker alive" probe

**Building any of it now is building the thing the port deletes.** The upstream liveness triple is
worth *recording as a design input to the `claude_cli` activity* — which is exactly how upstream
frames it ("a sequencing constraint, not a work item")[^hermes] — and not worth implementing.

### 5.5 What carries forward

- **The identity function** — the rule that computes the logical id from the task. Becomes the
  Workflow Id.
- **The fingerprint** — Temporal does not supply it (§5.2a).
- **The reference-not-payload rule** — matches Temporal's external-payload pattern.[^durexec]
- **The per-subsystem table itself** — upstream's framing is that a worker/activity design *"that
  cannot fill in this table is not finished."*[^openclaw] The table **is** the activity design doc.
- **The two rulings of #6** — they become constructor arguments.
- **The git-native operator surface** — Temporal's UI is engineer-facing and per-namespace; the
  operator reads GitHub, and the sprint's notifier item targets an inbox, not a dashboard.[^sprint]

### 5.6 One non-obvious alignment finding

Claude Code transcripts default to **30-day** retention (`cleanupPeriodDays`),[^sessions] and
Temporal's reuse-policy check is bounded by the Namespace Retention Period, whose worked example in
the docs is *"the last _30 days_."*[^wfid] **The dispatch record's own horizon (component #5) must
be chosen against both**, or the fleet acquires records that point at transcripts already deleted.
*(derived — inputs: those two facts. The failure is silent: the record resolves, the pointer does
not, and the operator discovers it only while investigating an incident.)*

---

## 6. What this provides — the enumerated, plannable list

Each row is a distinct decision the phase doc can cite. Costs are **derived** and name their basis.

| # | Item | Where it lands | Cost | Dependency |
|---|---|---|---|---|
| 1 | **Move identity generation out of the activity** — the logical id and attempt id become inputs to `run_claude`, in both the bash and Python paths[^activities][^planew] | `activities/run-claude.sh`, `assistant_activities.py` | **hours** | none — and it must precede Stage B (§5.2d) |
| 2 | **Write the two conflict rulings** (`REUSE` for closed, `CONFLICT` for running), per dispatch class | phase doc | **hours (a ruling)** | none |
| 3 | **The six-component identity schema** (§2.7), with UUIDv7 as the attempt id | phase doc + record schema | ~half a day | #1 |
| 4 | **The per-subsystem table** (§4.2) with all six columns, three rows initially empty for the guards | phase doc — **before workers**[^openclaw] | **hours (design), constrains build** | none |
| 5 | **The three rules R1–R3** (§4.3) adopted as rules, not notes | phase doc / workflow standard candidate | hours | #4 |
| 6 | **Tier 1 store: `refs/dispatch/*` with CAS creation**[^updateref] | new helper in `scripts/workflows/common/` | **1–2 days** incl. the refspec question (§9 T5) | #3 |
| 7 | **Tier 2 stays local, referenced by `(machine-id, path)`** — a rule, plus a machine-id source | phase doc + one helper | hours | #3 |
| 8 | **Persist the completion-contract verdict** (R3) — the value is already computed and discarded[^runclaude] | `run-claude.sh` | **hours** | #6 |
| 9 | **The fingerprint** — a hash over task inputs, and the rule that a mismatch is an ERROR[^ietf07][^stripe][^aws] | record schema | ~half a day | #3 |
| 10 | **Retention horizon ≥ 30 days**, aligned to both Claude Code and Temporal defaults (§5.6) | phase doc | hours (a ruling) | #3 |
| 11 | **Guard rows** — credential expiry, false completion, safety-hook wiring each become a record field, not a design | phase doc | **zero marginal** once #4 exists | #4 |
| — | ***Explicitly NOT built:*** claim/lease/TTL, boot reconciler, retry bookkeeping, timers (§5.4) | — | **negative cost** | — |
| — | ***Constraint, not a build item:*** any resume must re-supply the full launch vector including `--dangerously-skip-permissions`[^sessions] | phase doc | zero | — |

---

## 7. Honest boundary — the case against, taken seriously

### 7.1 The status-quo argument is well-formed, and most of it survives

The comment quoted in §1.3 makes five claims, and four of them stand.[^runclaude]

1. **"Recovery machinery would add failure modes."** True and specific. It names *"unverified
   commits pushed onto a healthy-looking PR"* and *"salvage loops."* §4.2's column 5 confirms the
   first: PR creation is the fleet's one non-replayable side effect, and it is precisely what a
   naive salvage would touch.
2. **"A message already resolves it."** True. `run-claude.sh` prints the worktree path and the
   inspect command; hand recovery took ~10 minutes.
3. **"The fix is louder signalling, not resume."** **This paper agrees, and adds first-party support
   the comment does not have:** a resumed session does not restore `bypassPermissions`,
   `--mcp-config`, `--settings`, `--plugin-dir` or `--add-dir`.[^sessions] Auto-resume would
   silently run a *differently-configured* dispatch under the original's name — a worse failure than
   the one it fixes, and invisible in the PR.
4. **"Every occurrence so far with a human watching."** Accepted as stated. It is also, by
   construction, a property of the past.
5. **"Measured rate is 0.9% (4/443 runs)."** — see §7.3.

### 7.2 Where a durable dispatch id is genuinely not worth it

*(derived — inputs: §7.1; `durable_execution.md` §6's boundary analysis, including the ~30-minute
task-duration threshold below which the discipline is net cost.[^durexec])*

A durable dispatch identity is **overhead with no return** when all of these hold:

- one machine, one operator, one repo;
- at most one dispatch in flight at a time;
- no automated guard needs to record a per-dispatch verdict;
- the operator is present for the run;
- nothing downstream needs to name a specific past dispatch.

**That describes the fleet as it ran in April 2026**, and the comment was correct for that fleet.
It stops being correct at the first of: a second machine dispatching against the same repo; a guard
that must record a verdict; two dispatches concurrently in flight; a notifier that must name the
blocked work. **The Fleet Reliability sprint introduces three of the four.**[^sprint]

### 7.3 The denominator is not reconstructible — a negative finding, with method

The 0.9% figure is an **in-repo assertion in a code comment**, not a linked dataset. To test whether
it can be re-measured — which the comment's own reopen condition requires — I enumerated the log
population.

**Method.** `Glob` for `.claude/logs/*.jsonl` against `/home/puma/Repos/claude-dot-files` (the main
checkout, not this worktree). I counted the returned list myself rather than asking any layer for a
total: **57 entries**, earliest `revision-20260409-193933.jsonl`, latest
`research-20260807-101449.jsonl`. **This is a FLOOR, not a certified total** — I cannot establish
that the listing tool did not cap its output, so §3's sourcing rule requires stating it as such.

**Three findings follow, and the third is the sharpest:**

1. **57 ≪ 443.** The population on this machine cannot yield the stated denominator. Logs are
   written per-repo (`${REPO_ROOT}/.claude/logs`)[^planew][^activities] and `.claude/` is
   gitignored,[^gitignore] so the 443 runs — if fleet-wide across repos and machines — have no
   single place they can be counted from. **This is not a challenge to the figure's honesty; it is
   the observation that it cannot be re-derived, which is exactly what its own reopen condition
   demands.**
2. **The identity in the surviving record names scripts that no longer exist.** I sub-counted the
   enumerated list by prefix: **19** of the 57 are named `revision-*` or `revision-major-*` (the
   single `plan-revision-*` entry is excluded — it belongs to a script that still exists). A `Glob`
   of `scripts/workflows/**/*.sh`
   returns no `revision.sh` or `revision-major.sh` — the current names are `build.sh` and
   `build-minor.sh`. *(derived — inputs: the two enumerations; the rename is inferred from the name
   change and the date boundary, not from a commit I read.)* **Identity-by-filename does not survive
   a rename**, which is component #1's failure mode made concrete in this repo's own history.
3. **Two naming authorities already disagree.** V1 names the log after a per-script literal
   (`plan-new-${TIMESTAMP}`);[^planew] V2 names it after `model_key`
   (`f"{model_key}-{stamp}"`).[^activities] The enumeration contains `plan-sprint-*` logs, and
   `scripts/workflows/` contains no `plan-sprint.sh` — only `temporal/scripts/plan_sprint.sh`,
   confirming V2 writes into the same directory under a different convention. **The identity scheme
   has already forked, silently, mid-port.**

### 7.4 The strongest counter-argument to this paper's own thesis

**Temporal supplies most of §2.7 for free, so why write any of it now?** If Stage B lands soon,
components #1, #2, #3, #5 and #6 all arrive from the substrate, and every hour spent on a
hand-rolled equivalent is deleted.

**The honest answer has three parts, and the first concedes:**

- **Conceded:** the *mechanism* half — claim, lease, reconcile, retry — should not be built. §5.4
  says so explicitly, and that is the majority of the work a naive reading of "restart-recovery
  contract" would produce.
- **Not conceded, on timing:** the port is *"Gated on Workflow Decomposition and the Memory
  Management Framework"* and Fleet Reliability *"lands before workers"* because *"a restart-recovery
  contract retrofitted onto running workers is a rewrite."*[^sprint] Upstream reaches the same
  conclusion independently from a second system.[^openclaw][^hermes]
- **Not conceded, on substance:** components **#4 (fingerprint)** and the **Tier 1 store** are
  *never* supplied by Temporal (§5.2a, §3.4), and component **#1** is actively **broken by** the
  port unless fixed first (§5.2d). Those three are not early work; they are work the port makes
  harder, not easier.

### 7.5 Where this paper is weakest

- **No behavioural verification.** Nothing was executed. Every claim about `--session-id`,
  `--resume`, ref CAS under concurrent writers, and Temporal's behaviour on a killed worker is
  documentation-derived. §9 is the handoff and it is not optional.
- **The academic leg is thin, and its single member is visually transcribed.** An earlier draft
  claimed this paper's antecedents were *entirely* industrial because the recovery-oriented-design
  literature could not be retrieved; that claim is **withdrawn** — Candea & Fox is retrievable and
  is now cited (§1.1, §3.6, §8 gap 4). The honest residue is smaller but real: it is **one** paper,
  obtained as **page images** rather than as a character stream, so I can see the spans I quote but
  cannot certify them character-exact the way a raw `.md` fetch certifies the rest of §2. It is used
  as **corroboration only** — it supports §3.6's tier split and §2.7's fingerprint component;
  neither rests on it, and removing it changes no recommendation. A second, independently retrieved
  academic source would strengthen the lineage; this paper does not have one.
- **The row set in §4.2 is a floor.** It enumerates the subsystems the current fleet has; a fleet
  with a notifier, a queue or a scheduler will have more, and the table must be re-opened then
  rather than assumed complete.
- **The `~30-minute threshold` caveat applies.** Upstream records a community-sourced heuristic that
  below roughly thirty minutes of task duration the durable-execution discipline is net
  cost.[^durexec] The fleet's dispatches run 10–60 minutes, so it sits **on** that line, not
  comfortably above it.

---

## 8. Gaps — stated as findings, each with its search method

1. **`--session-id` collision behaviour is undocumented.** What happens when the supplied UUID
   already names a session — reuse, error, or clobber — is not stated. *Method:* `cli-reference.md`,
   `sessions.md` and `headless.md` were each fetched from `code.claude.com` and read in full; the
   only documented not-found path is the inverse (*"No conversation found with session ID:
   <session-id>"*).[^cli][^sessions][^headless] **This blocks §6 item 1's design; it is §9 T3.**
2. **The flag matrix for `-p` + `--session-id` + `--dangerously-skip-permissions` + worktree is not
   stated.** `headless.md` documents conflicts only for `--bg` and `--cloud`.[^headless] *Method:*
   same three documents. **§9 T1.**
3. **No documented cross-machine session portability.** The ID search is scoped to *"every other
   project on this machine"*; no mechanism to move or replicate a session across machines is
   described. *Method:* same three documents. **This is a hard constraint on any future resume
   design, not merely a gap.**[^sessions]
4. **WITHDRAWN on re-check — the academic antecedent WAS retrievable and is now cited** (§1.1,
   §3.6). Candea & Fox, *Crash-Only Software* — the page-1 header reads *"Appears in Proceedings of
   the 9th Workshop on Hot Topics in Operating Systems (HotOS-IX), May 2003"* — was sought as a
   peer-reviewed antecedent for recovery-as-the-normal-path, and an earlier draft of this gap
   asserted it could not be obtained. *Original method:* `usenix.org` legacy PDF **403**,
   `usenix.org` legacy HTML **403**, `web.stanford.edu/~candea/...` **404**,
   `dslab.epfl.ch/pubs/crashonly.pdf` returned an unextractable binary PDF,
   `api.semanticscholar.org` **429**. A critic pass reported that three of those five legs resolve
   cleanly under `curl` + `pdftotext`. *Re-check method, run for this correction round:* both
   `usenix.org` legacy URLs returned **403 again** from my tooling, so **those two legs did not
   reproduce the critic's result and remain contested** — the difference is the client, not the
   document. `dslab.epfl.ch/pubs/crashonly.pdf` returned the same 132.4 KB binary my prose-fetch
   layer still could not parse — **but the binary was retained on disk, and reading it through a PDF
   page renderer produced legible pages 1–3.** The route the original run missed was therefore not a
   different URL but a different **reader**, and "unextractable binary PDF" was a statement about my
   tooling that I wrote as a statement about the source. **The negative finding is withdrawn.** What
   survives is narrower and is stated at §7.5 and §11: the text arrived as **page images**, so its
   spans are transcribed visually and cannot be certified character-exact.
5. **The 0.9% denominator is not reconstructible.** §7.3, with method.
6. **Temporal's default Activity retry policy is not asserted from my own fetch.** The
   `retry-policies.mdx` fetch returned fetch-layer prose with its own headings rather than a
   reproduction, so it does not satisfy the verbatim rule. The claim used in §5.2d (unlimited
   maximum attempts by default) is cited to the upstream pool, which verified it.[^synthesis]
   *Method:* one raw fetch of the `.mdx`, which summarized.
7. **No prior art was found for idempotency-key design in a client-side-only setting.** Every
   surveyed scheme assumes a **server** owns the key store — Temporal's service, GitHub's and
   GitLab's runners, Stripe's API, AWS's control plane, Kafka's broker, SQS. *Method:* the IETF
   httpapi draft, Stripe, AWS Builders' Library, AWS SQS, Kafka, RabbitMQ, Temporal, GitHub Actions,
   GitLab CI and systemd were each fetched and read for this specific property; none describes a
   design where the *only* durable store is the client's. **This fleet has no server today, which is
   why §3.6 puts Tier 1 in git — git is the closest thing to a server the fleet already has.**
8. **Whether `refs/dispatch/*` survives the fleet's normal push/fetch flow is not established.**
   `git-notes.adoc`'s DESCRIPTION does not address transfer behaviour, and I did not locate a
   first-party statement of default refspec coverage for non-`heads`/`tags` refs. *Method:*
   `git-notes.adoc` and `git-update-ref.adoc` fetched raw and read. **§9 T5.**

---

## 9. Test plan — what research cannot settle

| # | Question | Experiment | Blocks |
|---|---|---|---|
| **T1** | Does `claude -p --session-id <uuid> --dangerously-skip-permissions -w <worktree>` accept the combination and produce a session resumable by that UUID? | one 2-turn dispatch, then `claude --resume <uuid> -p "echo"` | §6 item 1 |
| **T2** | On a turn-capped run, does `--resume` continue mid-task, and does re-passing `--dangerously-skip-permissions` restore the original behaviour? Does it re-enter the worktree? | force a turn cap with `MAX_TURNS=3`, then resume with the full launch vector | any future resume; §7.1 claim 3 |
| **T3** | What does Claude Code do when `--session-id` names an existing session? | invoke twice with the same UUID | §8 gap 1 |
| **T4** | What is the real turn-cap rate with an identity in place, over 30 days, with a reconstructible denominator? | ship §6 items 1+8, then count | §7.3; the comment's own reopen condition |
| **T5** | Do `refs/dispatch/*` travel on the fleet's normal push/fetch without an explicit refspec? What happens when two machines create the same ref concurrently? | create from two clones, push both, inspect | §6 item 6; §8 gap 8 |
| **T6** | Does a fingerprint lookup before `gh pr create` actually prevent a duplicate PR under retry? | simulate a retry after a successful create | §4.3 R2; §6 item 9 |
| **T7** | Under Temporal, does passing the precomputed id as an activity **input**, with `ALLOW_DUPLICATE_FAILED_ONLY` + `FAIL`, produce the intended behaviour when a worker is killed mid-activity? | replay test on the Stage B wrapper | §5.3 |
| **T8** | Does a 31-day-old dispatch record still resolve to its transcript under default `cleanupPeriodDays`? | age a record; check `~/.claude/projects/.../<id>.jsonl` | §5.6; §6 item 10 |
| **T9** | Does the parent-sequencing row (§4.2) actually recover a mid-sequence parent death, or does the child-level record suffice? | kill a parent between children; attempt reconstruction from records alone | §4.2's largest gap |

---

## 10. Escalation — outside COMPONENT altitude, stated and not acted on

Two items bear on what the project *believes* or on planning artifacts rather than on how this
component is built. Per the dispatch's altitude constraint and the Research Standard's consumption
rules,[^standard] they are named here and nothing is written outside `research/`.

1. **`sprint.md`'s "all three guards" is ambiguous between two triples in the same sprint section**
   (§4.4). This is a planning-artifact wording item, not a belief item, and it decides the scope of
   a milestone. **Consequence if unresolved:** the phase doc inherits the ambiguity and the recovery
   contract is scoped to the wrong triple — either omitting the credential/false-completion/hook
   guards' record fields, or over-building liveness machinery §5.4 says not to build.
   **Remedy:** the phase doc states which reading it adopts in one line; the operator confirms.
2. **The upstream pool's SQLite data point does not transfer to a multi-machine fleet** (§3.2).
   The comparator that runs on SQLite is explicitly one-owner-per-host, and SQLite's own docs rule
   out direct multi-machine access.[^sqlite][^openclaw] Nothing in the pool claims otherwise — this
   is a *clarification* that would prevent a future planning run from reading "SQLite plus boot-time
   reconciliation" as a portable recommendation. **Consequence if unresolved:** a later component
   picks SQLite for fleet-wide state and inherits a corruption risk. **Remedy:** a one-line note in
   whichever synthesis next touches the durability axis; not this paper's to write.

---

## 11. Citations

**First-party, raw or plain-text (exact characters returned):**

[^proto]: `temporal/api/enums/v1/workflow.proto` — `WorkflowIdReusePolicy` and `WorkflowIdConflictPolicy`, fetched raw on the confirmed default branch `main`. https://raw.githubusercontent.com/temporalio/api/main/temporal/api/enums/v1/workflow.proto

[^wfid]: Temporal documentation, *Workflow Id and Run Id* — whole-file reproduction. https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workflow/workflow-execution/workflowid-runid.mdx

[^actexec]: Temporal documentation, *Activity Execution* — whole-file reproduction. https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/activities/activity-execution.mdx

[^limits]: Temporal documentation, *Workflow Execution limits* — whole-file reproduction. https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workflow/workflow-execution/limits.mdx

[^searchattrs]: Temporal documentation, *Search Attributes* — the "For business logic…" sentence and its complete bullet list, reproduced verbatim. https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/visibility/search-attributes.mdx

[^ghcontexts]: GitHub docs, *Contexts* — the `github.run_id` / `github.run_number` / `github.run_attempt` table rows, reproduced with their Liquid includes intact. https://raw.githubusercontent.com/github/docs/main/content/actions/reference/workflows-and-actions/contexts.md

[^ghrunid]: GitHub docs, reusable `run_id_description`. https://raw.githubusercontent.com/github/docs/main/data/reusables/actions/run_id_description.md

[^gitlabvars]: GitLab docs, *Predefined CI/CD variables reference* — `CI_JOB_ID`, `CI_PIPELINE_ID`, `CI_PIPELINE_IID`, `CI_CONCURRENT_ID` rows. https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/ci/variables/predefined_variables.md

[^journalfields]: systemd, `man/systemd.journal-fields.xml` — `INVOCATION_ID=` / `_SYSTEMD_INVOCATION_ID=` entries. https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.journal-fields.xml

[^sdid128]: systemd, `man/sd_id128_get_machine.xml` — `sd_id128_get_invocation()`. https://raw.githubusercontent.com/systemd/systemd/main/man/sd_id128_get_machine.xml

[^kafka]: Apache Kafka, `docs/design/design.md` on the confirmed default branch `trunk` — message delivery semantics and the idempotent producer. https://raw.githubusercontent.com/apache/kafka/trunk/docs/design/design.md

[^rabbit]: RabbitMQ, `docs/confirms.md` — delivery tags and consumer idempotence. https://raw.githubusercontent.com/rabbitmq/rabbitmq-website/main/docs/confirms.md

[^sqlite]: SQLite, *Appropriate Uses For SQLite* — "Client/Server Applications" and "High Concurrency". https://www.sqlite.org/whentouse.html

[^gitnotes]: git, `Documentation/git-notes.adoc` — DESCRIPTION and NOTES MERGE STRATEGIES. https://raw.githubusercontent.com/git/git/master/Documentation/git-notes.adoc

[^updateref]: git, `Documentation/git-update-ref.adoc` — atomicity, `--stdin` transactions, and the `<old-oid>` compare-and-swap. https://raw.githubusercontent.com/git/git/master/Documentation/git-update-ref.adoc

[^ietf07]: J. Jena, S. Dalal, *The Idempotency-Key HTTP Header Field*, `draft-ietf-httpapi-idempotency-key-header-07`, 15 October 2025, `Expires: 18 April 2026`, Intended status: Standards Track — §§2.2–2.4 reproduced verbatim from the plain-text draft. https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.txt

[^rfc9562]: RFC 9562, *Universally Unique IDentifiers (UUIDs)*, Standards Track, May 2024 — §5.7 UUID Version 7. https://www.rfc-editor.org/rfc/rfc9562.txt

[^sqs]: AWS, *Using the message deduplication ID in Amazon SQS* — fetched at BOTH the `.md` and the `.html` path; both returned the identical markdown source (anchor tags and `.md` cross-links intact), and the quoted span is character-exact in both. See §2.4's tag for the contested-and-re-checked note. `…/using-messagededuplicationid-property.md` and https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/using-messagededuplicationid-property.html

[^stripe]: Stripe API reference, *Idempotent requests* — returned as markdown. https://docs.stripe.com/api/idempotent_requests

[^cli]: Claude Code, *CLI reference* — `--session-id`, `--resume`, `--continue`, `--fork-session`, `--replay-user-messages` rows. https://code.claude.com/docs/en/cli-reference.md

[^sessions]: Claude Code, *Manage sessions* — reproduced whole; resume semantics, what a resumed session restores and does not, transcript storage path, 30-day retention. https://code.claude.com/docs/en/sessions.md

[^headless]: Claude Code, *Run Claude Code programmatically* — reproduced whole; `-p` flag conflicts, structured output, continuing conversations. https://code.claude.com/docs/en/headless.md

[^restartrecovery]: OpenClaw, `docs/gateway/restart-recovery.md` — the three recovery rules, re-fetched at source for this paper and matching the upstream pool's quotations. https://raw.githubusercontent.com/openclaw/openclaw/main/docs/gateway/restart-recovery.md

[^ghapi-temporal-api]: GitHub REST API repository metadata, used to confirm default branches before every raw fetch: `temporalio/api`, `temporalio/temporal`, `temporalio/documentation`, `temporalio/sdk-python`, `github/docs`, `systemd/systemd`, `rabbitmq/rabbitmq-website` — all `"default_branch": "main"`. https://api.github.com/repos/temporalio/api

[^ghapi-kafka]: GitHub REST API repository metadata for `apache/kafka` — `"default_branch": "trunk"`. https://api.github.com/repos/apache/kafka

**Rendered pages and page-image sources — reduced confidence, quoted only in short spans:**

[^crashonly]: G. Candea, A. Fox, *Crash-Only Software*, Stanford University — *"Appears in Proceedings of the 9th Workshop on Hot Topics in Operating Systems (HotOS-IX), May 2003"* (page-1 header). **Retrieval method, stated because it bounds the confidence:** `usenix.org`'s legacy PDF and HTML both returned **403** to my fetcher on two separate rounds; the EPFL mirror returned the PDF as a 132.4 KB binary that the prose-fetch layer could not parse, and the retained binary was then read through a PDF **page renderer**, yielding legible images of pages 1–3. The quoted spans are therefore **transcribed visually, not returned as a character stream**, and are not claimed as character-exact. Used for corroboration only (§1.1, §3.6); no recommendation depends on it. https://dslab.epfl.ch/pubs/crashonly.pdf

[^aws]: M. Featonby, *Making retries safe with idempotent APIs*, Amazon Builders' Library. https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/

[^datatracker]: IETF Datatracker, `draft-ietf-httpapi-idempotency-key-header` document page — status reported as expired and archived; latest revision 07. https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/

**In-repo evidence (read, not fetched):**

[^runclaude]: `scripts/workflows/activities/run-claude.sh` — the `run_claude` command construction, the model-resolution rule, the turn-cap termination block and its rationale comment, and the completion-contract check.

[^planew]: `scripts/workflows/plan-new.sh` lines 212–216. The same `TIMESTAMP`-derived naming scheme appears in eleven further scripts I enumerated by content search: `build-phase.sh`, `plan-revision.sh`, `research.sh`, `research-refresh.sh`, `review-runs.sh`, `review-sprint.sh`, `children/build-draft.sh`, `children/build-draft-minor.sh`, `children/build-refine.sh`, `children/build-refine-minor.sh` and `children/review-pr.sh`. (`review-runs.sh` derives only the log path from it, not a worktree name.)

[^activities]: `scripts/workflows/temporal/modules/assistant/assistant_activities.py` — `run_claude()`: the `repo_root`-vs-`worktree` docstring and guard, the `stamp`/`log_file` derivation (lines 252–253), the delegated-env contract, and the "OBSERVE before reporting" failure path.

[^buildinputs]: `scripts/workflows/temporal/modules/assistant/build/build_inputs.py` — `ChildResult`'s "`exit_code == 0` is necessary but NOT sufficient" docstring, and `BuildResult`'s in-memory `loops_used` / `notes`.

[^gitignore]: `.gitignore` line 2 — `.claude/`.

[^sprint]: `docs/development/sprint.md` § "Sprint: Fleet Reliability" (lines 172–184) and § "Sprint: Temporal Integration" (lines 186–198).

**Upstream research pool (cited, not re-derived — `docs/standards/architecture/research/`):**

[^openclaw]: `raw/openclaw_assessment.md` — §3.1 (durability, the per-subsystem table, the durable dispatch identifier), §4.4 (the contract as a documentation shape), §6 items 3–4. Last validated 2026-08-06; **Critic: PASS (two rounds)**.

[^hermes]: `raw/hermes_assessment.md` — §5.4 and §7 item 4, the three-guard liveness triple. Last validated per that paper's header.

[^durexec]: `raw/durable_execution.md` — §1 (event sourcing, deterministic replay), §3 (External Payload Storage; the ~30-minute threshold), §5 (what the substrate provides), §6 (honest boundary). Last validated 2026-07-27; **Critic: PASS**.

[^synthesis]: `synthesis.md` — candidate 9 ("plan the three pre-worker recovery items as ONE design session"), candidate 29 (Temporal's default retry policy is unlimited max attempts, resting on `raw/temporal.md` §2.2/§5).

[^standard]: `docs/standards/research/research_standard.md` — §3 (the mini-paper contract and sourcing rules), §5 (volatility bands), §7 (consumption; a research run writes nothing outside `research/`).
