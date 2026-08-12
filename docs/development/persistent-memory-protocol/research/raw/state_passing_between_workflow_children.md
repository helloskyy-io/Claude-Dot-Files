# Passing state between `claude -p` children on one machine

```
Topic:          How does a workflow pass what it knows between `claude -p` child
                processes that share no memory — on ONE machine, within a single local
                dispatch? Four facets: (1) what must pass and what actually does,
                (2) one location or many, (3) format and classification per kind,
                (4) what survives the run and for how long.
Feeds:          A NOT-YET-TAKEN decision on whether this becomes a phase of the Memory
                Management Framework (docs/development/memory-management-framework/) or its
                own component. This paper is validating evidence for that decision; it does
                NOT take it — §5.1 states why no source could.
                It also answers three operator questions directly: consolidation (§4.2),
                format and best practice (§4.3), post-run persistence (§4.4).
Last validated: 2026-08-12
Revalidate:     high — 6 weeks
Confidence:     DEFINITIVE (first-party, raw source, exact bytes returned by fetch or by
                `git`/`grep` against the working tree): Temporal's per-event blob limits,
                Event-History ceiling, Memo guidance and Retention/Archival split; Airflow
                XCom sizing, addressing, retry-clearing and object-storage backend; Argo's
                parameter/artifact split and 1 MB etcd ceiling; LangGraph's checkpoint /
                thread_id / checkpoint_id model; Claude Code's `--resume`, `--fork-session`,
                `--session-id` and `--json-schema` flags; the Claim-Check pattern; NDJSON
                §3.2 parsing rule; git trailers; Linux MAX_ARG_STRLEN; and every claim about
                this repo's own code, which was read from the working tree.
                DERIVED (this paper's inference across the above, named at each site): the
                by-value/by-reference rule (§4.1); "consolidate the ADDRESS, not the STORE"
                (§4.2); the format-selection axes (§4.3); the two-tier retention read (§4.4);
                the claim that the Kind-1/Kind-2 taxonomy is not a partition of the fleet's
                channels (§4.3.3).
                UNVERIFIED / GAPS, with search method stated at each: the chaining semantics
                and cost of `--resume` under `-p` (§6, G1); any documented prompt-size limit
                in the Claude Code CLI (G2); vendor confirmation that `--json-schema` output
                may be absent on a clean run (G3).
                NOTHING in this paper is directional — no roadmap or stated-intent claim is
                load-bearing anywhere in it.
Critic:         not-yet-verified — 2026-08-12
```

> **Scope, stated up front because a prior paper on this exact-sounding topic missed it.**
> [`cross_node_memory_protocol.md`](cross_node_memory_protocol.md) in this same directory
> answered *"how do distributed systems handle nodes that come and go"*. This paper answers
> *"how does one Python parent hand state to its next `claude -p` child on one machine"*.
> **Nothing below concerns a second machine, node, edge, placement, replication or
> reconciliation.** Where two machines share files they share them through git and GitHub,
> and git surfaces conflicts to a human — solved, and not this paper's subject.
>
> The prior paper is cited here **for provenance only**. Its three findings that survive the
> scope correction are each **re-grounded in primary evidence in this paper** rather than
> inherited: the single-value-store property is re-derived from Temporal heartbeat details
> (§4.1, C-EX); the `candidates.md`/`direction.md` opposite-lifecycle evidence is taken
> directly from [`memory-model.md`](../../../../guide/memory-model.md) §2.4–§2.5 and the files
> themselves (§4.3.3); the "three observables, no reader" finding is taken directly from
> [`run_log.py`](../../../../../scripts/helpers/measure/run_log.py)'s own docstring (§4.4).

---

## 1 · Primer — the gap, stated exactly

A workflow here is a **Python parent** (Temporal workflow code) that invokes a sequence of
`claude -p` children. The parent calls no model; every branch is a pure decision and every
side effect is a child dispatch or an activity. Each child starts with **zero** memory of the
previous one: nothing carries over in-process, because there is no process in common. The
child is a fresh `execve`.

So anything child N+1 needs from child N **must have been written somewhere and read back**.
That sentence is the entire subject. The question is not *whether* to write it down — the
fleet already writes several things down — but **which channel, in which format, with which
address, retained for how long, and by what rule.**

Two framings that are *not* the problem, named so they stop being reached for:

- **This is not a distributed-systems problem.** One writer, one host, one dispatch. There is
  no partition to tolerate and no conflict to reconcile.
- **This is not context management.** The child's context window is a separate concern. The
  question here is what crosses the process boundary, not what fits inside one.

The nearest first-party statement of the same gap comes from Airflow, whose XCom mechanism
exists because, in its own words, *"Tasks are entirely isolated and may be running on entirely
different machines"* [S8]. Strip the second clause — this fleet's children share a host — and the first
clause is exactly this fleet's condition. **Isolation, not distribution, is what creates the
channel requirement**, which is why the relevant literature is workflow engines and agent
checkpointers rather than consensus protocols. *(Derived from [S8]; the fleet-side half is
observation of the code in §2.)*

---

## 2 · The specific model — what this fleet actually passes today

**Method:** read from the working tree, not from a doc's claim about it. Every row below cites
the file and the construct.

### 2.1 · The channel enumeration

Nine rows. **Eight of them cross a `claude -p` process boundary**; row 9 is listed because it
is where run knowledge actually accumulates and it crosses nothing.

| # | Channel | Direction | Value or reference | Declared at |
|---|---|---|---|---|
| 1 | **The prompt string** | parent → child | **by value**, one `execve` argument | `assistant_activities.run_claude`: `argv = ["bash", "-c", f'source "{runner}"; run_claude "$1"', "_", prompt]`; `run-claude.sh:142` `claude -p "$prompt"` |
| 2 | **The worktree path** | parent → child | **by reference** (a `Path`) | `research_workflow.py:42` `worktree = act.worktree_add(...)`, then passed to every child |
| 3 | **The worktree contents** — files, commits, the diff | child N → child N+1 | **by reference**, implicit | same `worktree` handed to `write`, `verify`, `review-pr` (`research_workflow.py:48-93`) |
| 4 | **The child's final stdout** — the completion contract | child → parent | **by value**, one line | `run-claude.sh:299-345` (`COMPLETION_PATTERN` over `.result` or the last assistant text); `research_workflow.py:48` returns `pr_url` |
| 5 | **The typed exit record** (`structured_output`) — **wired on the `review-pr` child only**; `exit_record_schema` is passed from exactly one call site | child → parent | **by value**, typed, once at exit | `exit_record.CHILD_SCHEMA`; `review_pr_workflow.py:135`; `run-claude.sh:155` `claude_cmd+=(--json-schema "$EXIT_RECORD_SCHEMA")` |
| 6 | **The run-log JSONL** — `run_resources` fleet-wide, `parent_route` and `convergence` on the `review-pr` path | parent → later tooling | **by value**, append-only | `run_log.MEMBER_EVENT_TYPES = frozenset({"parent_route", "run_resources", "convergence"})`, joined on `JOIN_KEY = "run_id"` |
| 7 | **The PR thread / `pr_review:` yaml block** | child → parent, and child → later runs | **by reference** (fetched by `gh`) | [`memory-model.md`](../../../../guide/memory-model.md) §4 |
| 8 | **The other four Kind-1 surfaces** — Issues, standup tracker, `direction.md`, `candidates.md` | run → later runs (cross-**run**, not within-run) | **by reference** | [`memory-model.md`](../../../../guide/memory-model.md) §2 |
| 9 | *(crosses nothing)* the parent's `notes: list[str]` | parent → parent | in-process, dies at exit | `research_workflow.py:38` `notes: list[str] = []`, returned in the typed result at `:77-78` |

**Counted from the enumeration above: 9 rows, 8 boundary-crossing.** Rows 7 and 8 together are
the five surfaces `memory-model.md` §2 documents; row 5 is the Kind 2 record. **Rows 1, 2, 3,
4 and 6 — five of the eight — are covered by neither kind.** That count is used again in
§4.3.3 and it is the enumeration, not an estimate.

### 2.2 · What actually crosses, traced through one real parent

`research_workflow.py` is 95 lines and the whole trace fits in a paragraph. The parent creates
the worktree once (`:42`) and hands the same `Path` to every child. The `write` child returns a
**PR URL string** (`:48`), parsed **through the owner** — `routing.pr_number_from_url(pr_url,
expected_repo=slug)` (`:56`), never a raw `rsplit`, with the reason stated in the code: the
naive parse *"returns the last path segment of whatever it is handed, so a child that printed a
bare sentence yields a word and it reaches `gh` as a PR number."* The resulting `pr` identifier
goes to every subsequent child. `notes` is accumulated **by the parent** and returned.

**Exactly one value produced by a child crosses to a later child: the PR number.** Everything
else a later child needs, it re-derives by reading the worktree or by fetching the PR.

`build_workflow.py` has the same shape: `worktree` by reference (`:51`), `pr_url` → `pr`
(`:62-66`), a `task_file` **path** handed to `refine` (`:101`), and one parent-computed boolean
`ci_unsettled=not ci_settled` (`:101`). Two independent parents, one rule.

### 2.3 · The by-value payload, sized

`review_pr_workflow.assemble_prompt` composes core + universal addenda + exactly one
type-criteria file. Enumerated by `ls` over `review_pr/prompts/`, five files, byte counts read
from the filesystem:

| File | Bytes |
|---|---|
| `disposition.md` | 72,002 |
| `criteria_research.md` | 3,112 |
| `criteria_planning.md` | 1,392 |
| `criteria_build.md` | 1,388 |
| `core_corpus_rule.md` | 1,112 |

A research-type disposition child therefore receives **72,002 + 1,112 + 3,112 = 76,226 bytes**
of template, plus two joining separators, before substitution. `review_pr_helper.render_prompt`
then substitutes **six** placeholders — `PR_NUMBER`, `PR_BRANCH`, `THIS_PASS`, `PRIOR_PASS`,
`HEADLESS_EXECUTION_GUARD`, `RUN_ID` — of which five are scalars and one is a shared prose
fragment.

**So ~76 KB of that payload is instruction and a few dozen bytes of it are state.** The PR
thread, the diff and the papers are not in it; the child fetches them itself. This is the
by-reference rule (§4.1) already in force, arrived at independently.

**And there is a hard ceiling nobody has named.** The prompt is a single `execve` argument.
Linux caps one argument at `#define MAX_ARG_STRLEN (PAGE_SIZE * 32)` [S17]; `getconf PAGESIZE`
on this workstation returns `4096`, so the ceiling is **131,072 bytes**. The largest fixed
template already sits at **58% of it**, and the substituted blocks — `CONTEXT_BLOCK` in
`research_write_workflow.py:57`, assembled from operator context plus an upstream block plus a
currency table — are **unbounded by construction**. *(Derived: the kernel constant is
definitive [S17], the page size and the byte counts are measured here, the combination is this
paper's.)* Consequence for this fleet: a sufficiently large operator task file does not degrade
the child, it **fails the dispatch at `execve` with `E2BIG`**, at a boundary whose error names
neither the prompt nor the block that grew it.

### 2.4 · The fleet's own by-reference rule, already written down and already measured

`research_activities.upstream_block` states it outright, in code, with a number:

> *"A POINTER, not the content: inlining the synthesis cost 48k characters and tripled the
> prompt, and it is inconsistent with how the rest of this prompt works — the research
> standard, `topics.md` and the existing papers are all pointed at and read in Stage 1. **Only
> COMPUTED values are inlined, because those are the ones a run cannot obtain by reading.**"*

That last sentence is the selection rule, and §4.1 shows it is the same rule four external
systems converged on.

---

## 3 · Comparative landscape — how mature systems pass state between steps

Each row is first-party and raw-sourced. The fourth column is the property this fleet can
actually use.

| System | By-value channel | By-reference channel | The rule it states |
|---|---|---|---|
| **Temporal** [S1–S3] | Activity results and inputs in **Event History**; `memo`; search attributes | payload references the user constructs | History capped: *"The Workflow Execution's Event History is limited to 51,200 Events or 50 MB and will warn you after 10,240 Events or 10 MB"* [S2]. Per-event blob: `"limit.blobSize.error"` default `2*1024*1024`, warn at `512*1024` [S1] |
| **Temporal, side channel** [S3] | `memo` — *"a non-indexed set of Workflow Execution metadata"*, 40 KB on Cloud | — | *"Memos shouldn't store data that's critical to the execution of a Workflow"*; *"Memos lack type safety"*; *"subject to eventual consistency"*; *"Excessive reliance on Memos hides mutable state from the Workflow Execution History"* [S3] |
| **Temporal, checkpoint channel** [S4, S5] | heartbeat **details** — *"an application layer payload that can be used to _save_ Activity Execution progress"* [S4] | — | Scoped to retries of the **same** activity: *"the next Activity Task can access and continue with that payload"* [S4]; *"persisted and available to retry attempts, enabling resumption from the last checkpoint"* [S5] |
| **Apache Airflow** [S8] | **XCom** — *"only designed for small amounts of data; do not use them to pass around large values, like dataframes"* | object-storage XCom backend | Addressed by `key` + `task_id` + `dag_id` (+ `run_id` when crossing DAGs). *"XComs will be cleared to make the task run idempotent. XComs therefore can't be used to persist state across task retries"* |
| **Argo Workflows** [S9–S11] | **parameters** — *"use the result of a step as a parameter (and not just as an artifact)"* [S10] | **artifacts** — *"the output artifacts of one step may be used as input artifacts to a subsequent step"* [S9] | The state object lives in etcd: *"This creates a limit to their size as resources must be under 1MB"*, then compression, then SQL offload — and *"Offloading is expensive and often unnecessary, so we only offload when we need to"* [S11] |
| **LangGraph** [S12] | **checkpoint** — *"a snapshot of the graph state at a given point in time"*, saved *"at every superstep"* | pluggable serde/backends | Addressed by `thread_id` + optional `checkpoint_id`. Partial-failure recovery is explicit: *"LangGraph stores pending checkpoint writes from any other nodes that completed successfully at that superstep, so that whenever we resume ... we don't re-run the successful nodes"* |
| **Claude Code CLI** [S13] | `--json-schema` — *"Get validated JSON output matching a JSON Schema after the agent completes its workflow (print mode only)"* | `--resume` / `--continue` / `--fork-session` / `--session-id` — a whole prior transcript, addressed by id | The one channel in this table that carries **conversation**, not data |
| **Claim-Check** [S14] | the token | the external store | *"Store a large message payload in an external data store and send only a reference token"*; *"The messaging system never sees or stores the payload"*; and conditionally: apply it *"if the message size surpasses the messaging system's limit"* |

**The convergence is the finding, and it is unanimous across six independent systems:** every
one runs **at least two channels** — a small typed by-value channel with a stated ceiling, and
a by-reference channel for anything larger — and every one **states a size rule for choosing
between them.** None of them consolidates to a single store.

---

## 4 · What this provides — the four facets, answered

### 4.1 · Facet 1 — what must pass, what does, and the rule for by-value vs by-reference

**Answer (derived from [S1]–[S14] and §2):** the mature rule is *pass by value only what the
receiver cannot obtain by reading, and keep it under the channel's stated ceiling; pass
everything else by reference.* Four properties a plan can rely on:

**P1 — By-value channels are for identifiers, scalars and computed values, not for content.**
Every system in §3 says so in its own words, and each states a ceiling: Temporal 2 MiB per
event blob and 50 MB per history [S1, S2]; Temporal Cloud 40 KB per memo [S3]; Argo 1 MB per
Workflow object [S11]; Airflow "small amounts of data" with an object-storage escape hatch
[S8]. **This fleet's ceiling is 131,072 bytes and comes from the kernel, not from a policy**
(§2.3) — the only ceiling in the set that was never chosen. *Consequence:* the fleet enjoys the
loosest by-value budget in the comparison and the least control over it, and the failure at the
boundary is a hard `execve` error rather than a warn-then-error ramp like Temporal's.

**P2 — The by-reference channel needs a lifecycle rule, and this fleet's does not have one.**
The Claim-Check pattern's first stated consideration is *"Delete consumed messages"*, with a
synchronous and an asynchronous strategy named [S14]. Argo offloads to SQL; Airflow's custom
backends expose a `purge` method [S8]. This fleet's by-reference store is the **git worktree**,
whose lifecycle is git's, and the **run log**, which has none (§4.4). *Consequence:* the
by-reference channel this fleet leans on hardest is the one with no stated pruning rule.

**P3 — A one-value-per-key channel cannot hold a reasoning trail.** Temporal heartbeat details
are the cleanest instance: only the **last** heartbeat is available to the next attempt [S4,
S5], so the channel is structurally last-write-wins and the discarded values are gone by
contract, not by accident. This re-grounds — from a first-party workflow-engine source rather
than from a messaging analogy — the finding carried forward from the superseded paper. *Fleet
consequence:* the exit record (row 5) is written **once at exit** and is therefore a
one-value-per-invocation channel. It can carry a verdict; it structurally cannot carry the
authored reasoning [`memory-model.md`](../../../../guide/memory-model.md) §7.2 enumerates as
fourteen items, three of which have no field at all today. That is not a schema gap to be
closed by adding fields — a single-shot record has room for the fields but no room for a
*trail*.

**P4 — The by-value channel is where partial progress is lost, and every mature system has a
named answer.** LangGraph persists pending writes from nodes that already succeeded so a resume
does not re-run them [S12]; Temporal replays Event History; Airflow deliberately does the
opposite, clearing XComs on retry to force idempotency [S8]. **This fleet has no equivalent.**
A child that dies mid-run leaves its worktree (recoverable) and its log (partial); the parent's
`notes` list dies with the parent process (row 9). *Consequence:* the fleet's answer today is
Airflow's — re-run the child from the top — which is defensible for a model call and is
**unstated anywhere**, so nobody can tell a design choice from an omission.

**The cost of getting P1 wrong, sized on this fleet:** 48,000 characters and a tripled prompt,
measured and recorded in `research_activities.upstream_block`'s own docstring (§2.4). That is
the only measured by-value cost figure this fleet has, and it is on the correct side of the
rule already.

### 4.2 · Facet 2 — one location or many

> **Operator's question, verbatim:** *"should we be consolidating all memory store to a
> specific file structure in a specific location and everything references back to it?"*

**Answered, and the prior art contradicts the implied direction — while endorsing the second
half of the sentence.**

**On "one store": no, and no surveyed system does it.** §3's table has six systems and every
one runs multiple channels *on purpose*, with the reason stated at the channel. Temporal is the
strongest evidence because it is this fleet's own substrate and it deliberately ships a channel
it then warns you off: memo exists, and the docs say it *"shouldn't store data that's critical
to the execution of a Workflow"* and that over-use *"hides mutable state from the Workflow
Execution History"* [S3]. That is not an apology for having two stores; it is a **selection
rule** attached to one of them. SQLite makes the same point from the other direction, as a
first-party authority on single-file storage: a pile-of-files format *"essentially uses the
filesystem as a key/value database"* and *"gives the advantage of making the content more
accessible to common utility programs such as text editors or \"awk\" or \"grep\""*, at the
cost that it *"breaks the \"document metaphor\": there is no one file that a user can point to
that is \"the document\""* [S15]. Both shapes are legitimate; neither is free.

**On "everything references back to it": yes — consolidate the ADDRESS, not the store.**
*(Derived from [S1]–[S14].)* Every system in §3 has exactly one join key spanning all of its
channels: Temporal's Workflow Id / Run Id; Airflow's `dag_id` + `task_id` + `run_id` + `key`
[S8]; LangGraph's `thread_id` + `checkpoint_id` [S12]. **That, not a single store, is what
makes multiple surfaces coherent.**

**And this fleet already has the mechanism — with a measured history of it not working.**
`run_log.JOIN_KEY = "run_id"`, and the module's own comment records the defect precisely:

> *"THE JOIN KEY. All three members carry it. Its VALUE was out of conformance until this
> phase: `run_resources` wrote `log_file.stem` (`{model_key}-{stamp}-{nonce}`) against the
> other two's bare `uuid4().hex`, so the surface's own join key joined nothing."*

**How far the key actually reaches was checked per call site, not assumed, because the answer
is uneven.** `grep`ing the tree for `run_id=`, `RUN_ID` and `exit_record_schema` gives:

| Channel | Carries `run_id`? | Where |
|---|---|---|
| 1 · prompt | **only on the `review-pr` path** | `review_pr_helper.render_prompt`'s `"RUN_ID": run_id`; the placeholder appears in `disposition.md:255` and nowhere else in the prompt corpus |
| 5 · typed exit record | **only on the `review-pr` path** | `exit_record_schema=exit_record.schema_argument()` is passed from exactly one site, `review_pr_workflow.py:135` |
| 6 · run log | **on every dispatch, partially** | every dispatch gets a `run_id` (`assistant_activities.py:589`, `uuid4().hex` when the caller supplies none) and the log file is named with it; `run_resources` carries it fleet-wide, while `parent_route` and `convergence` are written on the `review-pr` path |
| 7 · `pr_review:` block | **yes, where emitted** | [`memory-model.md`](../../../../guide/memory-model.md) §4.1 — the block's first addressing field, with an explicit ordering fallback for blocks that predate it |
| 2, 3, 4, 8 | **no** | worktree path, worktree contents, completion-contract stdout, the four cross-run surfaces |

**So the join key is complete on exactly one of the fleet's child types (`review-pr`) and is
one field wide — the log file's name — on all the others.** *(Derived from the call-site
enumeration above; each row is a grep anyone can re-run.)* The parent-issues / child-echoes /
parent-compares loop is real and is rule R5, with `exit_record`'s own caution attached:
*"Model-echoed, so it proves nothing on its own."*

**So the honest answer to the operator is: the question as posed ("one location") is the one
the prior art rejects, and the question underneath it ("everything references back to it") is
the one it endorses — and this fleet has already built the endorsed half on its most complex
child and not yet on the others, having recently fixed the case where the key existed and
joined nothing.** *Consequence:* consolidating stores would cost a migration and buy what a
join key already buys; extending `run_id` to the remaining child types is the cheaper form of
the same property, and the uneven coverage above is the map of what that would cost.

### 4.3 · Facet 3 — format and classification

> **Operator's question, verbatim:** *"What format do the various files use, and what's best
> practice here?"*

#### 4.3.1 · The axes that actually decide it

*(Derived across [S8], [S12], [S14], [S15], [S16], [S18] and the fleet's own five formats.)*
Four axes, each with a first-party instance:

1. **Reader latency** — code within seconds (the exit record; heartbeat details [S4]) vs a
   human in six weeks (a PR thread; `candidates.md`). This is the axis
   [`memory-model.md`](../../../../guide/memory-model.md) already cuts Kind 1 from Kind 2 on.
2. **Write pattern** — append-only stream (the run log; NDJSON [S18]) vs one mutable record
   updated in place (`candidates.md`'s `status:` column; Airflow's XCom row).
3. **Typing** — schema-validated (the exit record; `--json-schema` [S13]) vs freeform (a
   reflection comment).
4. **Size** — under the channel ceiling (by value) vs over it (by reference / claim check
   [S14]).

#### 4.3.2 · Does any single format serve humans and machines equally well? No — and the mature
answer is not a format at all

**Answer: no format does both well, and two proven arrangements exist instead.** *(Derived from
[S15], [S16], [S13] and this fleet's `pr_review:` block.)*

- **Arrangement 1 — a human-authored document with a machine-parseable REGION.** The canonical
  first-party instance is git trailers: *"Add or parse trailer lines that look similar to RFC
  822 e-mail headers, at the end of the otherwise free-form part of a commit message"* [S16].
  The document stays a document; a fixed, addressable region inside it is parseable. **This
  fleet already runs it**: the `pr_review:` fenced yaml block inside a prose disposition
  comment ([`memory-model.md`](../../../../guide/memory-model.md) §4), and the markdown tables
  in `candidates.md` / `direction.md`. Its known failure mode is also already measured here:
  the block marker was *"written down three incompatible ways"* and two of the three
  over-matched, producing durably wrong `pass:` numbers (§6.4 of that document). **A parseable
  region is only as good as the one declaration of where it starts.**
- **Arrangement 2 — a typed store with a rendered human view.** `--json-schema` [S13] plus a
  renderer. Its cost is stated exactly in
  [`memory-model.md`](../../../../guide/memory-model.md) §7 — *everything the human reads must
  be expressible in the typed record, or the render loses it* — and §7.2 enumerates fourteen
  authored items, three of which have no field today.

**Neither arrangement is a compromise format; each is a two-part system.** The recurring
mistake the evidence warns against is expecting one artifact to be simultaneously
schema-validated and free-form — SQLite's framing of the same trade-off is that a custom format
is an *"opaque blob"* accessible only to purpose-built tools, while a pile-of-files is grep-able
and loses the document [S15].

#### 4.3.3 · Per-format guidance, and one live conformance defect

| Need | Format the evidence supports | Instance |
|---|---|---|
| Append-only stream of typed events, read by code | JSONL / NDJSON [S18] | the run log |
| One-shot typed handoff, read by code within seconds | JSON validated against a declared schema [S13] | `exit_record.CHILD_SCHEMA` |
| One mutable record, both audiences, low volume | markdown table with a status column, or a trailer-style region [S16] | `candidates.md`, `direction.md`, `pr_review:` |
| Anything over the channel ceiling | a reference, not the content [S14] | the worktree path; `upstream_block` |
| Queries over accumulated history | a database file; SQLite's stated niche is the application file format, where *"Updates happen automatically as application content is revised so the File/Save menu option becomes superfluous"* [S15] | **nothing in this fleet today** — see §4.4 for why that may be about to matter |

**The live defect:** NDJSON §3.2 states *"If the JSON text is not parsable, the parser SHOULD
raise an error"* [S18]. `run_log._decoded` and `assistant_activities._log_events` both **skip**
malformed lines instead. The deviation is deliberate and documented — the log file is
co-resident with non-JSON output, and *"A reader that raised would lose a whole run's figures to
one stray warning"* — and NDJSON's own next sentence permits documented deviation for empty
lines only, not for unparsable ones. *Consequence, and it is small but real:* the fleet's
run log is **JSONL-shaped but not NDJSON-conformant**, so a general NDJSON tool pointed at it
will behave differently from the fleet's own readers, and silently. Worth stating once in
whatever document owns the surface; not worth changing the readers.

#### 4.3.4 · Does the Kind-1 / Kind-2 cut land in the right place? Unsettled — with evidence

**Two observations, both from enumeration, and they point the same way.**

*Observation A — the taxonomy is not a partition of the channels.* §2.1 enumerated eight
boundary-crossing channels. Kind 1 covers three of them (rows 7 and 8, i.e. the five
documented surfaces); Kind 2 covers one (row 5). **Five of eight are covered by neither**: the
prompt, the worktree path, the worktree contents, the completion-contract stdout line, and the
run log. The run log is the sharpest case: it is durable, addressed by `run_id`, and read by
tooling — but it has **no to-do bit**, so it fails
[`memory-model.md`](../../../../guide/memory-model.md) §1 property 4 outright, and its
PUBLISHABLE/NOT-PUBLISHABLE rule deliberately **excludes model-authored text**, so it also
cannot satisfy property 3 (outcome *and* reasoning). It is a real memory surface that the
taxonomy has no slot for.

*Observation B — the pair the prior paper flagged discriminates on lifecycle, not on audience.*
`candidates.md` never deletes a row; `direction.md` rotates a ruled row out at 90 days
([`memory-model.md`](../../../../guide/memory-model.md) §2.4, §2.5, §3.2). Both are Kind 1,
both are markdown tables in one directory, both are read by machines and humans. **The property
that separates them is lifecycle shape, and that document already has the vocabulary for it** —
§3.1's Transactional / Task / Continuous. So the axis that predicts a surface's behaviour is
already written down, and it is not the axis the two *kinds* are named on.

**This paper does not rule on the cut**, and stating why is part of the finding: whether "Kind
1 / Kind 2" should be re-cut is a naming-and-scope decision about a framework, and the same
class of decision as §5.1's. What the evidence supports is narrower and checkable: **the
current two kinds do not enumerate the fleet's channels, and lifecycle shape discriminates
where audience does not.** Both halves are counts and comparisons anyone can re-run.

### 4.4 · Facet 4 — what survives the run, and for how long

> **Operator's framing, verbatim:** *"the logs and memory persist even after its complete to
> some extent for later review."*

**To what extent — measured, not estimated.** Enumerated with
`ls .claude/logs/*.jsonl | wc -l` over a list, and `du -sh`:

| | |
|---|---|
| Run-log files | **175** |
| Total size | **262 MB** |
| Oldest (from the filename stamp) | `20260409` |
| Newest | `20260812` |
| Span | **125 days** |
| Pruning code found | **none** — `grep -n "unlink\|prune\|rotate"` over `run_log.py` and `assistant_activities.py` returns nothing |
| In git? | **no** — `git check-ignore -v .claude/logs` returns `.gitignore:2:.claude/` |

**The prior art says retention is a stated per-store policy, usually in two tiers.** Temporal:
*"Retention Period is the duration for which the Temporal Service stores data associated with
closed Workflow Executions on a Namespace in the Persistence store"*, minimum 1 day [S6] — and
a second tier, Archival, which *"enables Workflow Execution data to persist beyond retention
without overwhelming the Temporal Service persistence store"* [S7]. Airflow clears XComs on
retry and exposes `purge` on custom backends [S8]. Claim-Check names deletion as its first
consideration, with synchronous and asynchronous strategies [S14].

**The fleet's five documented surfaces each have a stated rule**
([`memory-model.md`](../../../../guide/memory-model.md) §3.2): PR threads permanent, Issues
closed-is-the-bound, tracker lines pruned at `resolved` + 14 days, `direction.md` rows rotated
at 90 days **with the precondition that the reasoning already lives somewhere that never
deletes**, `candidates.md` never. That precondition is the best retention design in this
system and it is worth naming: **a record may be deleted once its reasoning has been written
down somewhere permanent.** It is the exact mechanism Temporal's Archival provides
generically [S7], invented locally and stated more precisely.

**The run log has none of that, and it is the surface with the most machine-readable content.**
Three defects stack, all first-party:

1. **No retention rule.** 175 files, 262 MB, 125 days, no pruning code. It is the only memory
   surface here that grows without a bound *and* without a stated reason for not having one.
2. **No reader, for weeks.** `run_log.py`'s own opening: *"It had every property of a surface
   except a name, and no committed tool read any of it."* Against
   [`memory-model.md`](../../../../guide/memory-model.md) §1.2 — *"A record with no reader is
   not memory, it is exhaust"* — that is the documented local failure mode, on the fleet's own
   terms.
3. **Not durable in the sense property 1 requires.** `.claude/` is gitignored, so the archive
   survives the *run* but not the *machine*, and it is invisible to every consumer that reads
   the repo. *(Restated deliberately as a single-machine durability claim; nothing here is
   about a second machine.)*

**Consequence for this fleet, stated as a single sentence:** the channel that carries the
typed, parent-computed evidence — the routing decisions, the resource telemetry, the
convergence signal — is the only one that is neither pruned nor committed nor, until
recently, read; so the fleet's most machine-legible memory is also its most perishable, and
that inversion is the finding this facet exists to surface.

Two smaller retention facts worth carrying, both first-party: Temporal's Archival is *"not
supported when running Temporal through Docker"* and is disabled by default on manual installs
[S7] — so a self-hosted deployment that wants beyond-retention history must switch it on
deliberately, and the upstream product paper on Temporal
([`temporal.md`](../../../../standards/architecture/research/raw/temporal.md), last validated
2026-08-05, Critic: PASS-WITH-FIXES) owns the vendor-commitment question; this paper does not
re-open it.

---

## 5 · Honest boundary analysis

### 5.1 · The decision this paper feeds is not one any source could settle — and this section
exists because a prior paper on this topic paid for that lesson

**Whether this becomes a phase of the Memory Management Framework or its own component is
categorically outside what research can determine.** It is a scope-and-ownership choice about
this fleet's own planning artifacts. There is no source that could be found, because the
subject of the question is a preference of the operator's about how his own work is
partitioned. **This is not a gap a wider search would close**, and a paper that dressed a
preference as a finding here would be doing the exact thing this brief already paid for once.

What the evidence *does* supply for that decision, and nothing more:

- The subject is **not** cross-node memory (the superseded paper's frame); it is single-host
  channel design. Anyone sizing the work should size it on §2.1's eight channels.
- Five of those eight are outside the Memory Management Framework's current Kind-1/Kind-2
  taxonomy (§4.3.3). That is a **scope fact**, relevant to the phase-versus-component question,
  and it is a count anyone can re-run — it is not an argument for either answer.

### 5.2 · The strongest case against this paper's own thesis

**The thesis:** children share no memory, so the channels between them need a stated rule per
channel — selection, address, format, retention.

**The case against it, and it is a real one.** §2.2 traced two production parents and found
that **exactly one child-produced value crosses to a later child: the PR number.** Everything
else is re-derived by reading the worktree or fetching the PR. On that evidence, this fleet
*does not currently have a state-passing problem* — it has a state-passing **discipline**
(re-derive from the durable artifact) that happens to work, and the mature-systems machinery in
§3 solves a problem the fleet has largely designed away. **Building a framework for a channel
that carries one integer would be speculative generality**, and this repo's own standards call
that out by name.

Three things weaken but do not eliminate that counter-case, and each is stated with its
strength:

- **It holds for the two parents examined and was not tested beyond them.** Two of the fleet's
  parents were traced end to end (`research_workflow.py`, `build_workflow.py`). Whether a
  parent exists that passes more was **not** established; the honest statement is that the
  claim covers the two parents read, not the fleet. *(Gap G4, §6.)*
- **The re-derive discipline has a cost that is measured elsewhere in this system.** Reading
  the durable artifact instead of being handed it is what
  [`memory-model.md`](../../../../guide/memory-model.md) §6.3 measures at **858 KB read to
  extract 15 records**, worst case 177 KB on a single thread. Re-derivation is not free; it
  moves the cost from the by-value channel to the retrieval path. That is a trade, not a win.
- **The counter-case does not touch facet 4 at all.** Even a fleet that passes nothing between
  children still produces 262 MB of run log with no reader and no pruning rule (§4.4). The
  retention finding survives the strongest attack on the rest of the paper — which is the main
  reason it is stated as the sharpest one.

### 5.3 · The alternative this paper does not take, stated fairly

**`--resume` / `--continue` / `--fork-session` would make the gap disappear by not having it.**
The CLI documents resuming *"a specific session by ID or name"* and, with `--fork-session`,
*"create a new session ID instead of reusing the original"* [S13]. A parent could hand child
N+1 the whole of child N's transcript. That is a genuine architecture, not a straw man, and it
is the only channel in §3's table that carries **conversation** rather than data.

Two reasons this fleet does not use it, one strong and one weak, stated separately:

- **Strong, and it is doctrinal rather than technical:** the fleet deliberately wants a fresh
  context per child. `research_write_workflow.py`'s own docstring — *"A separate fresh-context
  run verifies the papers, applies corrections and traces each one through to it — because the
  run that wrote an artifact defends it"* — is `author ≠ judge`, and resuming a session
  destroys it by construction. This is a fleet commitment, and no external source bears on it.
- **Weak, because it is unmeasured:** resuming presumably re-ingests the prior transcript at
  full input cost. **This paper found no first-party figure for that** (gap G1), so the cost
  argument against `--resume` is *plausible and unverified*, and should not be leaned on until
  someone measures it.

### 5.4 · Where the comparative evidence does not transfer

Every system in §3 passes state between steps that are **programs the author wrote**. This
fleet's steps are **model invocations**, and two consequences do not carry over:

- **A schema is not a contract with a model the way it is with a function.** `exit_record.py`
  records the fleet's own measurement of this — an over-constrained required field produces
  *silence* on a clean run rather than an error. No surveyed engine has this failure mode, and
  **no vendor documentation confirming it was found** (gap G3).
- **The prompt is both instruction and state, and the surveyed systems separate those
  completely.** 76 KB of instruction and a few dozen bytes of state travel on the same argv
  string (§2.3). Nothing in the prior art models a channel with that shape, so P1's ceiling
  guidance transfers but its *sizing* guidance does not — a 2 MiB budget for an activity result
  says nothing about how much instruction a model should be handed.

---

## 6 · Gaps — each with the search method that established it

**G1 — no first-party cost or chaining semantics for `--resume` under `-p`.** Searched: the
Claude Code CLI reference fetched as raw markdown (`docs.claude.com/en/docs/claude-code/
cli-reference.md`, 106,498 bytes) and grepped for `--resume`, `--continue`, `--fork-session`,
`--session-id`. **The flags are documented; what a resumed session costs in input tokens, and
how it behaves when chained non-interactively, is not.** Consequence: §5.3's cost argument is
unverified and is marked so.

**G2 — no documented prompt-size limit in the Claude Code CLI.** Same search, same file. The
only ceiling found anywhere is the OS one, from the kernel header [S17]. Consequence: §2.3's
131,072-byte ceiling is real but is the *platform's* limit, not the tool's, and could be lower
in practice for reasons no document states.

**G3 — no vendor confirmation that `--json-schema` output may be absent on a successful run.**
Searched the CLI reference raw markdown; the flag's description states what it produces, not
what happens when the model declines to produce it. The fleet asserts the absence case from its
own Phase 1 E2(c) measurement (`exit_record.py`). Consequence: the fail-safe arms in
`exit_record.route()` rest on a fleet measurement, not on a documented vendor guarantee —
correct engineering, but it should be revalidated against the CLI on every version bump.

**G4 — the "one value crosses" claim covers two parents, not the fleet.** Method: read
`research_workflow.py` and `build_workflow.py` end to end. A full enumeration of every parent
in the tree was not performed. Consequence: §5.2's counter-case is as strong as its sample,
which is two.

**G5 — no source found on retention policy for agent-run transcripts specifically.** Searched
first-party workflow-engine and agent-framework documentation ([S1]–[S13]); retention is
covered for *workflow state* (Temporal [S6, S7], Airflow [S8]) and not for *model-run
transcripts*. Consequence: §4.4's guidance is transferred by analogy from workflow state, and
is marked derived rather than definitive.

---

## 7 · Test plan — what only an experiment can settle

1. **Enumerate every parent in the tree and count, per parent, how many child-produced values
   cross to a later child.** Closes G4 and decides §5.2's counter-case. Cheap: a read of every
   `*_workflow.py`.
2. **Measure the assembled prompt size per child per workflow across ten real dispatches**, and
   compare the maximum against 131,072. Settles whether §2.3's ceiling is theoretical or one
   large task file away.
3. **Measure the input-token cost of `--resume` against a fresh child handed a pointer.** The
   only way to close G1. One controlled pair of runs.
4. **Attempt a join across all eight channels on five archived runs using `run_id` alone.**
   Confirms or refutes §4.2's four-of-eight claim empirically, and finds out what a joined view
   is actually good for.
5. **Write one reader for the run log that answers a question somebody has**, and record which
   fields it needs. The surface's documented failure was having no reader; a reader is the only
   instrument that distinguishes a needed field from a written one.
6. **Replay: how often is a run log older than 30 days actually read?** Determines whether the
   correct retention rule is a 30-day prune, a two-tier archive [S7], or none — and no source
   can answer it for this fleet.
7. **Take the three ⚠ authored items from
   [`memory-model.md`](../../../../guide/memory-model.md) §7.2 and attempt to express them in a
   typed record.** Decides §4.3.2's arrangement 1 vs arrangement 2 by construction rather than
   by argument.

---

## 8 · Citations

**Source accounting, stated rather than left to be counted.** **18 external sources**, listed
below as `[S1]`–`[S18]` with no number skipped and none reused; the figure is the count of that
list. The Research Standard §3 floor is 10–20 for medium+ topics with *proportionally fewer*
for small ones, and this is a small, single-concern topic — so 18 is **above** the proportional
target and the reason is stated rather than hidden: **seven of the eighteen are one vendor's
documentation set (Temporal, [S1]–[S7]), read as the fleet's own substrate rather than as an
alternative**, and the topic's four facets each needed their own prior art. Excluding the
substrate set leaves **eleven** sources across four facets, which is inside the proportional
target. The binding ceiling for this dispatch was 20 and is not breached. **Local repository
artifacts are the object of study rather than sources about it**, so they are enumerated
separately below (fourteen) and are not counted against the external total.

Sixteen of the eighteen were fetched as **raw** sources (`raw.githubusercontent.com`, raw
`.mdx`/`.rst`/`.md`/`.adoc`/`.go`/`.h`, or a documentation site's `.md` form). Two — [S15] and
the SQLite page it sits with — exist only as rendered HTML and were fetched with `curl` and
tag-stripped locally, so the character sequences quoted are exact but inline emphasis is not
preserved; they are quoted conservatively and marked here.

### External

- **[S1]** Temporal Server — `common/dynamicconfig/constants.go` (raw). `BlobSizeLimitError`
  `"limit.blobSize.error"` default `2*1024*1024`; `BlobSizeLimitWarn` `"limit.blobSize.warn"`
  default `512*1024`.
  https://raw.githubusercontent.com/temporalio/temporal/main/common/dynamicconfig/constants.go
- **[S2]** Temporal docs — Workflow Execution limits (raw `.mdx`).
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workflow/workflow-execution/limits.mdx
- **[S3]** Temporal docs — Workflow Execution, § *What is a Memo?* (raw `.mdx`).
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/workflow/workflow-execution/workflow-execution.mdx
- **[S4]** Temporal docs — Detecting Activity failures, § *Activity Heartbeat* (raw `.mdx`).
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/detecting-activity-failures.mdx
- **[S5]** Temporal docs — design pattern, *Long-Running Activity* (raw `.mdx`).
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/design-patterns/long-running-activity.mdx
- **[S6]** Temporal docs — Temporal Server, § *What is a Retention Period?* (raw `.mdx`).
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/temporal-service/temporal-server.mdx
- **[S7]** Temporal docs — Archival (raw `.mdx`).
  https://raw.githubusercontent.com/temporalio/documentation/main/docs/encyclopedia/temporal-service/archival.mdx
- **[S8]** Apache Airflow — *XComs* (raw `.rst`).
  https://raw.githubusercontent.com/apache/airflow/main/airflow-core/docs/core-concepts/xcoms.rst
- **[S9]** Argo Workflows — walk-through, *Artifacts* (raw `.md`).
  https://raw.githubusercontent.com/argoproj/argo-workflows/main/docs/walk-through/artifacts.md
- **[S10]** Argo Workflows — walk-through, *Output Parameters* (raw `.md`).
  https://raw.githubusercontent.com/argoproj/argo-workflows/main/docs/walk-through/output-parameters.md
- **[S11]** Argo Workflows — *Offloading Large Workflows* (raw `.md`).
  https://raw.githubusercontent.com/argoproj/argo-workflows/main/docs/offloading-large-workflows.md
- **[S12]** LangGraph — `libs/checkpoint/README.md` (raw). Checkpoint, thread, `thread_id` /
  `checkpoint_id`, serde, pending writes.
  https://raw.githubusercontent.com/langchain-ai/langgraph/main/libs/checkpoint/README.md
- **[S13]** Anthropic — Claude Code CLI reference, fetched in its `.md` form.
  `--resume`, `--continue`, `--fork-session`, `--session-id`, `--json-schema`,
  `--output-format`. https://docs.claude.com/en/docs/claude-code/cli-reference.md
- **[S14]** Microsoft — *Claim-Check pattern* (raw `.md` source of the Azure Architecture
  Center page).
  https://raw.githubusercontent.com/MicrosoftDocs/architecture-center/main/docs/patterns/claim-check-content.md
- **[S15]** SQLite — *SQLite As An Application File Format*, § pile-of-files formats.
  **Rendered HTML only**; fetched with `curl` and tag-stripped locally.
  https://sqlite.org/appfileformat.html · companion: https://sqlite.org/whentouse.html
- **[S16]** Git — `git-interpret-trailers` documentation (raw `.adoc`). **Quoting note:** the
  source wraps the quoted sentence across three lines and marks the word *trailer* with
  asciidoc emphasis underscores; §4.3.2 reflows it to one line and drops the two underscore
  characters. No word is added, removed or reordered.
  https://raw.githubusercontent.com/git/git/master/Documentation/git-interpret-trailers.adoc
- **[S17]** Linux kernel — `include/uapi/linux/binfmts.h` (raw).
  `#define MAX_ARG_STRLEN (PAGE_SIZE * 32)`.
  https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/linux/binfmts.h
- **[S18]** NDJSON specification 1.0.0, §3.1–§3.2 (raw `.md`).
  https://raw.githubusercontent.com/ndjson/ndjson-spec/master/README.md

*(Two notes on how the list was counted, so the figure is reproducible. [S15] is **one** source
cited with a companion URL on the same first-party site, not two. [S9] and [S10] are **two**
sources — two separate files of one project's documentation, each quoted separately. The
seven-member substrate set is [S1]–[S7]; the remaining eleven are [S8]–[S18].)*

### Local repository artifacts (the object of study, read from the working tree)

- `docs/guide/memory-model.md` — the five Kind-1 surfaces, the interface's five properties, the
  three lifecycle shapes (§3.1), the `pr_review:` consumer map (§4), the addressing convention
  and its retrieval cost (§6.1–§6.4), the Kind 2 seam and its fourteen authored items (§7.2).
- `docs/development/persistent-memory-protocol/research/raw/cross_node_memory_protocol.md` —
  superseded; cited for provenance only, per the scope note at the head of this paper.
- `scripts/helpers/measure/run_log.py` — `MEMBER_EVENT_TYPES`, `JOIN_KEY`, `PUBLISHABLE_FIELDS`,
  `_decoded`'s skip-malformed discipline, and the "no committed tool read any of it" docstring.
- `scripts/workflows/temporal/modules/assistant/review_pr/exit_record.py` — `SCHEMA_VERSION`,
  `SUPPORTED_SCHEMA_VERSIONS`, `CHILD_SCHEMA`, the three strata, `Outcome` / `HoldKind` /
  `RoutedOutcome` / `UndeterminedReason`.
- `scripts/workflows/temporal/modules/assistant/research/research/research_workflow.py` — the
  traced parent (§2.2).
- `scripts/workflows/temporal/modules/assistant/build/build/build_workflow.py` — the second
  traced parent.
- `scripts/workflows/temporal/modules/assistant/research/research_write/research_write_workflow.py`
  — `CONTEXT_BLOCK` assembly; the fresh-context doctrine quoted in §5.3.
- `scripts/workflows/temporal/modules/assistant/research/research_activities.py` —
  `upstream_block`'s pointer-not-content rule and its 48k-character measurement.
- `scripts/workflows/temporal/modules/assistant/assistant_activities.py` — `run_claude`'s argv
  construction, `claude_log_path`, `assistant_text`, `append_parent_route`.
- `scripts/workflows/activities/run-claude.sh` — `claude -p "$prompt"` (`:142`), `--json-schema`
  (`:155`), the completion contract (`:299-345`).
- `scripts/workflows/temporal/modules/assistant/review_pr/review_pr_workflow.py` —
  `assemble_prompt`.
- `scripts/workflows/temporal/modules/assistant/review_pr/review_pr_helper.py` —
  `render_prompt`'s six placeholders.
- `.claude/logs/` — enumerated for §4.4 (175 files, 262 MB, span `20260409`–`20260812`).
- `docs/standards/architecture/research/raw/temporal.md` (last validated 2026-08-05, Critic:
  PASS-WITH-FIXES) and `docs/standards/architecture/research/raw/edge_identity_trust.md` (last
  validated 2026-08-06, Critic: PASS at round 2) — upstream product-altitude papers whose
  ground this paper cites and does not re-research.

### Volatility note (§3 mixed-volatility rule)

The header takes the **highest** tier present. [S13] is AI-agent tooling (high band, 2–6
weeks) and [S1] tracks a moving `main` (high). [S2]–[S12] and [S14] are framework capabilities
(medium, 2–4 months). [S15]–[S18] are fundamentals (low, 3–6 months) — §2.3's kernel constant,
§4.3's format guidance and §4.1's claim-check reasoning can be skipped on a refresh. Because
only two of eighteen sources sit in the high band, the interval takes that band's **maximum**
rather than its minimum: **high — 6 weeks**.
