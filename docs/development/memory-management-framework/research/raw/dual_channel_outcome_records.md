# Dual-channel outcome records: how production systems relate a durable human record to a typed machine record

```
Topic:          When one unit of work must leave BOTH a durable human-readable record AND a typed
                machine-readable record, how do production systems relate the two — is the machine
                channel derived from the human record, is the human record rendered from the machine
                channel, or are they authored independently — and what goes wrong in each arrangement?
Feeds:          docs/development/memory-management-framework/roadmap.md — specifically
                § "What this component is", which holds the Kind 1 / Kind 2 relationship decision,
                and § "Phase 2 — Document Kind 1 as a framework".
Last validated: 2026-08-06
Revalidate:     medium — 3 months
Confidence:     Definitive on the arrangement inventory and on every quoted first-party span (all
                quotations were returned by fetches of raw `.md` / `.adoc` / `.rst` / `.txt` / JSON /
                GitHub-API forms — no rendered HTML page is quoted anywhere in this paper). Derived on
                the four-arrangement taxonomy itself, on the "which channel wins" column, on the
                lifecycle-mismatch analysis (§5), and on every recommendation in §6 — those are this
                paper's inferences across the cited sources, not statements any source makes. Seven
                explicit gaps in §7.1 (N1–N7), each with its search method — count reached by
                enumerating the N-markers in that section and counting the enumeration.
Critic:         PASS-WITH-FIXES — 2026-08-06. A critic pass re-fetched every source and checked every
                quoted span at byte level — all 26 external sources, all 3 sibling-paper citations,
                all 4 local-script citations — and found no fabricated source, no miscitation, and no
                confidence inflation. Two counts were wrong and are corrected in this revision: this
                header's §7.1 gap count (read "six", enumerates to seven), and N7's Argo occurrence
                count and characterisation (read "four mentions … all table rows", enumerates to five,
                of which three are table rows). Both corrected counts were re-derived by my own
                enumeration, not taken from the critic.
```

**Revalidate justification (§3 mixed-volatility rule, §5 bounds).** The prior art here is
standards-grade and slow: SARIF 2.1.0 is a frozen OASIS committee specification, the Kubernetes API
conventions and git's trailer semantics change on the order of years, and Conventional Commits v1.0.0
is versioned and stable. That argues for **low — 3–6 months**. Two things pull it up one tier. First,
the paper's §6 recommendations reference a **high-volatility** dependency: Claude Code's
`--json-schema` / `structured_output` surface. That fact is **inherited, not asserted here** — it is
cited from `claude_code_integration_surface.md`, which carries its own high-tier window, so a refresh
of *that* paper is the trigger, not a scheduled sweep of this one. Second, the *newest* prior art
(CTRF, Open Test Reporting) is actively evolving and could change the "what replaced JUnit XML" read.
Net: **medium — 3 months**, the bottom of the medium band. §2 (§2.1–§2.4, §3) is the slow material and
a refresh may skip re-verifying it absent a specification bump; §6 and §7 are the parts to re-read.

---

## 0. Headline for the phase doc

Across 26 external sources, **no located production system routes control flow by parsing prose out of
a durable human-readable record.** Every system that branches in code on a work outcome reads a typed
value from a channel it controls: an object field, a JSON artifact written at process exit, a label, or
a signed envelope. Where a human-readable record exists alongside it, that record is in one of three
relationships — *rendered from* the typed one, *authored beside* it under a shared identifier, or
*parsed into* it under a **write-time gate**. The third is the only arrangement in which a human
artifact is the source of a machine value, and every located instance of it pairs the parse with an
enforcement mechanism that rejects malformed input at authoring time (Gerrit refuses the push;
Kubernetes applies a `do-not-merge/...` label). *(derived — see §3 for the per-source evidence.)*

This repo's current arrangement is the third **without** the gate: `build.sh` recovers a routing token
by `grep -oE` over the child's whole stdout log [L1], and the typed `pr_review:` block that already
exists lives inside a human-authored PR comment [L2] that the parent never reads. The lifecycle
mismatch the phase doc has to design around — durable human record, machine channel needed seconds
after the child exits — is **not addressed by any located upstream source** (§7.1 N1), but it is
*dissolved* rather than solved by the arrangement the evidence supports: emit the typed record on the
child's exit channel, render the human record from it, and archive the typed record into the durable
surface as a by-product. §6 states this as three concrete moves against the two shipped scripts.

---

## 1. Primer: "two channels" is really four questions

A unit of work that must leave two records raises four separable questions. Conflating them is where
most of the confusion in this space lives.

1. **Authoring** — how many times does a human/agent write the outcome down? Once, or twice?
2. **Derivation** — if once, which direction does the other channel come from? Machine→human,
   human→machine, or neither (independent authoring under a shared key)?
3. **Location** — do the two channels live in one artifact (two regions of one document) or two?
4. **Lifecycle** — when is each written, when is each readable, and when does each expire?

The literature and the shipped systems answer (2) and (3) explicitly and (4) mostly by accident. (1) is
almost never stated, which matters, because **double authoring is the mechanism by which two channels
drift**; derivation in either direction reduces authoring to one act and makes drift a bug in the
deriver rather than a difference of opinion between two prose passages. *(derived.)*

A fifth question — *which one wins when they disagree* — is a **consequence** of (2), not an
independent choice. Where derivation runs machine→human, the typed record wins by construction; where
it runs human→machine, the human text wins and the derived artifact is regenerable; where neither
derives, the answer must be declared or it does not exist. *(derived; the per-arrangement evidence is
in §3.)*

---

## 2. The specific models the landscape offers

### 2.1 Machine→human: the typed record is the artifact, the human view is a projection

**SARIF + GitHub code scanning.** SARIF is the archetype the dispatch brief nominated, and it holds up
— but not in the shape it is usually described. The typed record does not sit *beside* a human record;
it **contains** the human record. In the OASIS SARIF 2.1.0 JSON schema, a `result` object carries both
the routing value and the prose, as sibling properties [S6, raw JSON]:

> "A value specifying the severity level of the result."   — description of `result.level`

> "A message that describes the result. The first sentence of the message only will be displayed when
> visible space is limited."   — description of `result.message`

`level` is a closed enum. Enumerating the schema's allowed values gives **four**: `none`, `note`,
`warning`, `error` [S6]. So one record, one authoring act, a typed field for the machine and a prose
field for the human — and the prose field's own description is written in awareness of the *rendering*
("the first sentence … when visible space is limited"). *(definitive on the quoted descriptions and on
the four-value enumeration; the count was reached by enumerating the enum, not by asking for a total.)*

The consumer side is where the failure mode lives. GitHub's first-party docs are explicit that it
implements a **subset** [S8, raw md]:

> "Any valid SARIF 2.1.0 output file can be uploaded, however, {% data
> variables.product.prodname_code_scanning %} will only use the following supported properties."

> "Note that the rest of the supported fields are ignored."

And the human rendering is conditional on something the producer does not control [S8, raw md]:

> "{% data variables.product.prodname_code_scanning_caps %} will also display alerts in pull request
> check results when all the lines of code identified by the alert exist in the pull request diff."

There is a documented payload cap, consistent with the caps enumerated upstream in
`code_routed_control_flow.md` §2.4.1 / P4 [I1] [S8, raw md]:

> "For each gzip-compressed SARIF file, SARIF upload supports a maximum size of 10 MB. Any uploads over
> this limit will be rejected."

*(definitive on all four quoted spans, from the raw markdown source of GitHub's docs repo; the liquid
`{% data %}` templates are reproduced as they appear in the raw file.)*

**Open Test Reporting.** The JUnit team's replacement for the JUnit XML format states the
machine→human derivation as an explicit design goal [S23, raw adoc]:

> "Both XML formats are designed to complement each other such that the event-based format can be
> mechanically converted into the hierarchical one."

with the event-based format aimed at the write path and the hierarchical at the read path:

> "The event-based XML format is suitable for writing test events to a file or streaming them over a
> local socket or network connection."

> "The hierarchical XML format is meant to be closer to existing representations of test results that
> users are familiar with."

Its stated grievance with the incumbent is a schema grievance, not a rendering one:

> "However, it's based on the concept of test classes and methods, so using it for frameworks and tools
> where those elements are not present is awkward at best. Moreover, it does not support nested
> structures beyond a simple parent-child relationship. Finally, it is not extensible."

*(definitive on the quoted spans, from the raw `README.adoc`.)*

**Prow.** Kubernetes' own CI writes a typed artifact per run alongside the log bundle [S4, raw md]:

> "Two of these artifacts that are present in each run are `started.json` and `finished.json`
> which contain a host of information pertaining to the job/run."

with a typed outcome field — the PodUtils variant's `finished.json` carries `"passed|bool"` and
`"result|SUCCESS, ABORTED, FAILURE"` [S4, raw md]. The reporting path back to the human surface is a
separate component: **crier** [S5, raw md]

> "**crier** reports back the status of the ProwJob back to the various external services like GitHub
> (e.g., as a green check-mark on the PR where the original `/test all` comment was made)."

*(definitive on the quoted spans. Note the shape: the typed record is written by the job at exit to
object storage; a *different* process projects it onto the human surface. Two writers, one source.)*

### 2.2 Independent authoring under a shared key: Kubernetes conditions vs. Events

This is the sharpest analogue in the brief's list and it earns the billing, but the lesson it carries is
not the one the brief anticipated.

The Kubernetes API conventions define conditions as the typed, controller-consumable channel [S1, raw
md]:

> "Conditions provide a standard mechanism for higher-level status reporting from a controller."

> "They are an extension mechanism which allows tools and other controllers to collect summary
> information about resources without needing to understand resource-specific status details."

> "Conditions should be added to explicitly convey properties that users and components care about
> rather than requiring those properties to be inferred from other observations."

Conditions are API surface, with API-grade compatibility obligations:

> "Once defined, the meaning of a Condition can not be changed arbitrarily - it becomes part of the
> API, and has the same backwards- and forwards-compatibility concerns of any other part of the API."

> "Objects may report multiple conditions, and new types of conditions may be added in the future or by
> 3rd party controllers."

> "For known conditions, the absence of a condition `status` should be interpreted the same as
> `Unknown`, and typically indicates that reconciliation has not yet finished (or that the resource
> state may not yet be observable)."

And — the single most transferable sentence in this paper:

> "Without further knowledge of the conditions, it is not possible to compute a generic summary of the
> conditions on a resource."

Events are the *other* channel, and the conventions state the relationship in one sentence [S1, raw
md]:

> "Events are complementary to status information, since they can provide some historical information
> about status and occurrences in addition to current or previous status."

with authoring guidance aimed squarely at humans:

> "Generate events for situations users or administrators should be alerted about."

> "Accumulate repeated events in the client, especially for frequent events, to reduce data volume,
> load on the system, and noise exposed to users."

*(definitive on all quoted spans, from the raw markdown of `kubernetes/community`. **Unverified process
note, not evidence:** two separate targeted fetches of the same raw file returned the conditions spans
consistently. That is a report about this paper's own fetch history — no later reader can check it, and
it is recorded for transparency only. It adds no confidence beyond what the quoted spans carry on their
own, and nothing in this paper rests on it.)*

**The lifecycle inversion — the finding.** In Kubernetes, the *human narrative* channel is the
**ephemeral** one and the *typed* channel is the durable one. The kube-apiserver reference documents
[S2, raw md]:

> `--event-ttl duration`   Default: `1h0m0s`   — "Amount of time to retain events."

Conditions live on the object and persist as long as the object does. So the arrangement Kubernetes
ships is the **mirror image** of this repo's constraint: typed = durable + authoritative, narrative =
expiring + advisory. That inversion is why no upstream source addresses the phase doc's mismatch
directly (§7.1 N1) — nobody upstream has a *durable* human record and a *transient* machine need.
*(**derived** from [S1] + [S2]; neither document states the comparison.)*

### 2.3 Human→machine: parsing a typed value out of a human-authored artifact

This is the arrangement this repo currently runs, and it is the only one of the four with a large,
mature body of prior art — all of it converging on the same two safeguards.

**Git trailers.** The mechanism is RFC-822-shaped lines at the end of a free-form message [S15, raw
adoc]:

> "Add or parse _trailer_ lines that look similar to RFC 822 e-mail headers, at the end of the
> otherwise free-form part of a commit message."

The extraction rule is worth reading in full, because it is a **heuristic**, and it is the clearest
statement in the corpus of what it costs to embed a machine channel inside free text [S15, raw adoc]:

> "Existing trailers are extracted from the input by looking for a group of one or more lines that (i)
> is all trailers, or (ii) contains at least one Git-generated or user-configured trailer and consists
> of at least 25% trailers. The group must be preceded by one or more empty (or whitespace-only) lines.
> The group must either be at the end of the input or be the last non-whitespace lines before a line
> that starts with `---` (followed by a space or the end of the line)."

*(definitive. A 25%-density threshold is not a parser; it is a guess that is usually right.)*

**The Linux kernel** documents the consequence directly: the *human* formatting rule is relaxed to
protect the *machine* parse [S18, raw rst]:

> "Do not split the tag across multiple lines, tags are exempt from the 'wrap at 75 columns' rule in
> order to simplify parsing scripts."

and the `Fixes:` tag's format is specified to the character [S18, raw rst]:

> "If your patch fixes a bug in a specific commit, e.g. you found an issue using ``git bisect``, please
> use the 'Fixes:' tag with at least the first 12 characters of the SHA-1 ID, and the one line
> summary."

> "This tag also assists the stable kernel team in determining which stable kernel versions should
> receive your fix."

*(definitive.)*

**Gerrit's Change-Id** adds the safeguard the trailer heuristic lacks — a **write-time gate** [S17, raw
txt]:

> "To be picked up by Gerrit, a Change-Id line must be in the footer (last paragraph) of a commit
> message."

> "By default, Gerrit will prevent pushing for review if no Change-Id is provided, with the following
> message: ! [remote rejected] HEAD -> refs/for/master (missing Change-Id in commit message footer)"

> "With this Change-Id, Gerrit can automatically associate a new version of a change back to its
> original review, even across cherry-picks and rebases."

*(definitive.)*

**Kubernetes release notes** are the closest structural match to this repo's `pr_review:` block: a
machine-parsed region inside a human-authored PR description, with a **derived label** carrying the
gate [S3, raw md]:

> "To add a release-note section to the pull request description, add your release note beneath the
> question *Does this PR introduce a user-facing change?*"

> "If you don't add release notes in the pull request template, the `do-not-merge/release-note-label-needed`
> label is added to your pull request automatically after you create it."

> "For pull requests that don't need to be mentioned at release time, use the `/release-note-none` Prow
> command to add the `release-note-none` label to the PR."

> "You can also write the string "NONE" as a release note in your PR description."

*(definitive on the quoted spans. Two things to notice. First: the gate is a **label**, not a re-parse —
the typed state is projected out of the human artifact into a first-class queryable field, and merge
automation branches on the label. Second: the same semantic ("no release note") has **two** authoring
paths, a Prow command and a magic string, which is exactly the redundancy that makes a parse fragile.)*

**Conventional Commits** is the purest human→machine derivation and states its own purpose as tooling
enablement [S14, raw md]:

> "The Conventional Commits specification is a lightweight convention on top of commit messages. It
> provides an easy set of rules for creating an explicit commit history; which makes it easier to write
> automated tools on top of."

The listed payoffs are all derived artifacts [S14, raw md]: "Automatically generating CHANGELOGs.",
"Automatically determining a semantic version bump (based on the types of commits landed).",
"Triggering build and publish processes."

Its documented failure mode is the one that matters here — the derivation is **one-way and the source
is immutable after merge** [S14, raw md]:

> "Prior to merging or releasing the mistake, we recommend using `git rebase -i` to edit the commit
> history."

> "In a worst case scenario, it's not the end of the world if a commit lands that does not meet the
> Conventional Commits specification."

*(definitive on the quoted spans. **Derived** consequence: the spec's own remedy for a bad machine value
is *rewrite the human artifact* — which is available for an unmerged branch and not available for a
merged commit, a posted PR comment, or a closed issue. A human→machine arrangement inherits the human
artifact's mutability, and this repo's human artifacts are append-only-in-practice PR comments.)*

**git notes** is the escape hatch the corpus offers for exactly that immutability problem [S16, raw
adoc]:

> "Adds, removes, or reads notes attached to objects, without touching the objects themselves."

> "A typical use of notes is to supplement a commit message without changing the commit itself."

> "By default, notes are saved to and read from `refs/notes/commits`, but this default can be
> overridden."

*(definitive on the quoted spans. Whether notes propagate on fetch/push by default was **NOT FOUND** in
this document — see §7.1 N4; do not assume either way.)*

### 2.4 Envelope + opaque payload: the supply-chain model

in-toto and SLSA answer a related question — how a typed record stays routable while its contents stay
free — and their answer is **layering**. The in-toto Statement [S9, raw md]:

> "The Statement is the middle layer of the attestation, binding it to a particular subject and
> unambiguously identifying the types of the Predicate."

> "Identifier for the schema of the Statement. Always `https://in-toto.io/Statement/v1` for this version
> of the spec."   — `_type`

> "URI identifying the type of the Predicate."   — `predicateType`

> "Additional parameters of the Predicate. Unset is treated the same as set-but-empty. MAY be omitted if
> `predicateType` fully describes the predicate."   — `predicate`

SLSA states the *reason* for the split [S10, raw md]:

> "Binds the attestation to a particular set of artifacts. This is a separate layer to allow for
> predicate-agnostic processing and storage/lookup."

and the consumer procedure reads **only the envelope layer** [S12, raw md]:

> "1.  [Verify][validation-model] the envelope's signature using the roots of trust, resulting in a list
> of recognized public keys (or equivalent).
> 2.  [Verify][validation-model] that statement's `subject` matches the digest of the artifact in
> question.
> 3.  Verify that the `predicateType` is `https://slsa.dev/provenance/v1`.
> 4.  Look up the SLSA Build Level in the roots of trust, using the recognized public keys and the
> `builder.id`, defaulting to SLSA Build L1."

with an explicitly bounded warrant [S12, raw md]:

> "SLSA Build L3 does **not** cover compromise of the build platform itself, such as by a malicious
> insider."

> "Note that SLSA v1.0 does not have any requirements on the completeness or verification of
> `resolvedDependencies`."

and the purpose framing [S11, raw md]:

> "In SLSA 'provenance' refers to verifiable information that can be used to track an artifact back,
> through all the moving parts in a complex supply chain, to where it came from."

*(definitive on all quoted spans. **Derived** and directly applicable: the routing consumer branches on
a *small, stable, versioned outer layer* — type URI, subject, predicate type, builder id — and never on
the rich inner payload. That is the same shape as `code_routed_control_flow.md`'s reading of Tekton
TEP-0074 [I1 §2.4.2]: the field's one attempt at a rich typed handoff object between independently
authored steps was withdrawn, and what survived was small and dumb.)*

Note also what SLSA does *not* claim: nothing in the located spec text ties the attestation to human
release notes, or says which wins if a release note and a provenance record disagree. The two are
independently authored and bound only by the artifact digest. *(§7.1 N3 records the search method for
that absence.)*

### 2.5 Two regions of one record: CloudEvents and OpenTelemetry

CloudEvents separates a routable metadata layer from an unconstrained payload [S13, raw md]:

> "Context metadata will be encapsulated in the Context Attributes."

> "Domain-specific information about the occurrence (i.e. the payload). This might include information
> about the occurrence, details about the data that was changed, or more."   — Data

> "The event payload. This specification does not place any restriction on the type of this
> information."

*(definitive on the quoted spans, from the raw `spec.md`.)*

OpenTelemetry's log data model draws the same line but leaves the body deliberately permissive [S19,
raw md]:

> "A value containing the body of the log record. Can be for example a human-readable string message
> (including multi-line) describing the event in a free form or it can be a structured data composed of
> arrays and maps of other values."

> "Additional information about the specific event occurrence. Unlike the Resource field, which is fixed
> for a particular source, Attributes can vary for each occurrence of the event coming from the same
> source."   — Attributes

The one piece of *routing-relevant* placement guidance located is in the semantic-conventions repo's
events doc [S20, raw md]:

> "Include attributes that users are likely to filter, group, aggregate, or correlate on."

> "Prefer flat attributes when the value can be represented clearly without structure. Use complex
> attributes only when the structure is part of the event semantics and a flat representation would be
> awkward or lossy."

> "Semantic conventions MUST NOT define a value for body except to represent a string display message of
> the event."

*(definitive on the quoted spans. The last one is the strongest statement in the corpus that the
**human-facing region is display-only and carries no semantics a consumer may depend on**. The general
"what goes in body vs. attributes" comparative guidance the brief anticipated was **NOT FOUND** in the
two other documents checked — §7.1 N2.)*

### 2.6 The negative datapoint: JUnit XML

JUnit XML is the field's most widely consumed machine test-result format and it **has no normative
specification**. A first-party JUnit-team issue titled "Define an offical XSD for JUnit XML test
reports" (created 2021-05-26, state `closed`) records the practical consequence in the reporter's own
words [S24, GitHub API JSON]:

> "In trying to provide this capability, we keep bumping up against the question of what, exactly, is
> the junit format."

> "But the standard we adopted for our logger was the Ant unit schema (which I picked b/c of comments
> suggesting it was the de-facto standard which I found a while ago in this or the junit4 repo/docs)."

*(**directional**, not definitive: this is a first-party *informal* artifact — an issue thread — and per
§3's authority/formality split it does not rise to definitive without a documented corroborating
artifact. The corroboration that does exist is indirect but documented: the JUnit team's own replacement
format states the incumbent "is not extensible" and lacks nested structure [S23], and CTRF exists as "An
open standard for JSON test reporting" [S22, GitHub API] whose stated aim is that "By standardizing the
output of test execution, it enables results to be shared, validated, aggregated, and analyzed
consistently across tools and platforms." [S22, raw md]. The issue's `state` and `created_at` values ARE
definitive — they came from the API JSON.)*

---

## 3. Comparative landscape — the arrangements, by derivation direction

Every column below is sourced; the taxonomy itself and the "who wins" column are **derived**.

| # | Arrangement | Direction | Located instances | Where the machine value is read from | Documented / evidenced failure mode | Who wins on disagreement |
|---|---|---|---|---|---|---|
| **A** | Typed record is the artifact; human view is **rendered** from it | machine → human | SARIF → code-scanning alerts + PR check results [S6][S8]; Prow `finished.json` → crier → GitHub check [S4][S5]; Open Test Reporting event XML → hierarchical XML [S23] | The typed file / object field | Consumer implements a **subset** and silently drops the rest — "will only use the following supported properties" / "the rest of the supported fields are ignored" [S8]; rendering is conditional on state the producer does not control (alerts shown only when the lines "exist in the pull request diff") [S8]; payload caps (10 MB gzip [S8]; and see [I1 §2.4.1] for Tekton 4 KB / Argo 1 MB) | Typed record, by construction — the human view has no independent content |
| **B** | Human artifact authored; machine value **parsed out** of it | human → machine | git trailers [S15]; kernel `Fixes:` / `Signed-off-by:` [S18]; Gerrit `Change-Id` [S17]; Kubernetes release-note block → label [S3]; Conventional Commits → CHANGELOG/semver [S14]; **this repo's `grep -oE` for `VERDICT:`** [L1] | The human artifact's text | Extraction is **heuristic** (git's "at least 25% trailers" rule [S15]); human formatting rules must be **bent to protect the parser** ("tags are exempt from the 'wrap at 75 columns' rule in order to simplify parsing scripts" [S18]); the remedy for a wrong value is to **rewrite the human artifact** ("`git rebase -i` to edit the commit history" [S14]), which is unavailable once it is merged/posted; redundant authoring paths for one semantic (`/release-note-none` **or** the string "NONE" [S3]) | Human text is the source of truth; the derived artifact is **regenerable**, so drift is a deriver bug, not a dispute |
| **C** | One record, **two regions** (typed field + prose field) | neither — co-authored in one act | SARIF `result.level` + `result.message` [S6]; CloudEvents context attributes + data [S13]; OTel attributes + body [S19][S20]; **this repo's `pr_review:` yaml + disposition table in one PR comment** [L2] | The typed region of the same record | The prose region may carry semantics a consumer depends on — which OTel forbids outright ("Semantic conventions MUST NOT define a value for body except to represent a string display message" [S20]); the typed region's extractability still depends on the surrounding artifact's formatting | Typed region, **if declared** — none of the sources define a precedence rule, because none of them lets the prose region mean anything |
| **D** | Two artifacts, **independently authored**, bound by a shared key | neither | Kubernetes conditions vs. Events [S1]; in-toto/SLSA attestation vs. human release notes [S9][S11] | The typed artifact, addressed by key (object name; artifact digest) | Divergence is unpoliced by construction; **lifecycle mismatch is real and documented in the inverse direction** — Events default TTL `1h0m0s` [S2] while conditions persist with the object; no generic aggregation is possible over the typed channel ("Without further knowledge of the conditions, it is not possible to compute a generic summary" [S1]) | Undefined unless declared. Kubernetes declares it implicitly by making conditions API surface with compatibility guarantees [S1] and Events expiring [S2] |

**Two cross-cutting patterns, both derived:**

- **Arrangement B never ships without a write-time gate.** Gerrit rejects the push [S17]; Kubernetes
  applies `do-not-merge/release-note-label-needed` [S3]; Conventional Commits' remedy presupposes a
  pre-merge edit window [S14]; the kernel changes its own style rules to keep the parse unambiguous
  [S18]. *(derived from four sources; no located instance of B relies on best-effort extraction with no
  producer-side enforcement.)*
- **Arrangement B is always used for *metadata about* a human artifact, never for *routing the outcome
  of a process*.** Change-Id identifies a review; `Fixes:` identifies a commit; a release-note block
  produces a document. In every located case where a *process outcome* routes a *subsequent process*,
  the arrangement is A or D — Prow's `finished.json` [S4], SARIF's uploaded file [S8], a condition on an
  object [S1], an attestation envelope [S12]. *(derived; this is the single most decision-relevant
  generalisation in the paper, and it is a generalisation over an enumerated set of located instances,
  not a claim that no counterexample exists.)*

---

## 4. What this provides — enumerated, citable properties

**P1. The typed record and the human prose are usually ONE artifact, not two.** SARIF puts `level` and
`message` on the same `result` object [S6]; CloudEvents puts context attributes and data in one event
[S13]; OTel puts attributes and body on one log record [S19]. *(definitive.)*

**P2. Where the two ARE separate artifacts, the derivation runs machine→human in every located CI/code
-scanning instance.** Prow writes `finished.json` and a separate component projects it to GitHub
[S4][S5]; SARIF is uploaded and GitHub renders alerts and PR check results from it [S8]; Open Test
Reporting's event format "can be mechanically converted into the hierarchical one" [S23]. *(definitive
on each instance; the "every located instance" scope is **derived** over the enumerated set.)*

**P3. The consumer of a typed record implements a documented SUBSET and ignores the rest.** GitHub:
"will only use the following supported properties" … "Note that the rest of the supported fields are
ignored." [S8]. *(definitive.)* **Derived consequence for a phase doc: the parent's contract is the
subset it reads, and that subset should be written down separately from the producer's full schema —
otherwise every field the producer adds looks load-bearing.**

**P4. A generic consumer cannot summarise a typed multi-item status; the producer must aggregate.**
Kubernetes states it flatly: "Without further knowledge of the conditions, it is not possible to compute
a generic summary of the conditions on a resource." [S1]. This repo's `review-pr` prompt already
independently reached the same rule and says so in as many words — the routing token "is a decision, and
it is YOURS to make — do not leave it to be re-derived" [L2]. *(definitive on both quotes; the
convergence is **derived**.)*

**P5. Routing consumers read a small, stable, versioned OUTER layer and never the rich payload.** SLSA
verification checks signature, `subject` digest, `predicateType`, and `builder.id` [S12]; the layering
exists "to allow for predicate-agnostic processing and storage/lookup" [S10]. Corroborated in kind by
`code_routed_control_flow.md` §2.4.2's account of Tekton withdrawing `PipelineResources` in favour of
plain results [I1]. *(definitive on the quotes; **derived** on the "and never the rich payload"
generalisation.)*

**P6. Embedding a machine channel in free text makes extraction heuristic, and the corpus pays for it in
authoring rules.** git's trailer block is identified by a 25%-density rule plus blank-line and `---`
boundary conditions [S15]; the kernel exempts tags from its own line-wrap rule "in order to simplify
parsing scripts" [S18]. *(definitive.)*

**P7. Every located human→machine arrangement pairs the parse with a write-time gate.** Gerrit blocks
the push on a missing `Change-Id` [S17]; Kubernetes auto-applies a blocking label when the release-note
block is absent [S3]. *(definitive per instance; the "every located" scope is **derived** over the
enumerated set — see §7.1 N5 for what was searched.)*

**P8. Human→machine derivation inherits the human artifact's mutability, and Conventional Commits'
documented remedy is only available pre-merge.** "Prior to merging or releasing the mistake, we
recommend using `git rebase -i` to edit the commit history." [S14]. *(definitive on the quote;
**derived** on the consequence for posted PR comments, which this repo cannot rebase.)*

**P9. The human narrative channel is the EXPIRING one in the sharpest analogue.** Kubernetes Events
default to `--event-ttl 1h0m0s` [S2] while conditions persist on the object and carry API
compatibility obligations [S1]. *(definitive on both facts; **derived** on the framing that this inverts
the phase doc's constraint.)*

**P10. A typed channel's semantics become API surface the moment a controller branches on them.** "Once
defined, the meaning of a Condition can not be changed arbitrarily - it becomes part of the API, and has
the same backwards- and forwards-compatibility concerns of any other part of the API." [S1]. This is the
same hazard `code_routed_control_flow.md` P12 records for Temporal workflow definitions and Tekton
TEP-0074 [I1]. *(definitive on the quote.)*

**P11. Absence must be given a meaning in the typed channel, and Kubernetes gives it one.** "For known
conditions, the absence of a condition `status` should be interpreted the same as `Unknown`" [S1]. This
is the same total-function requirement as `code_routed_control_flow.md` P5 (Step Functions errors
without a `Default`; Microsoft's switch-case safety net) [I1]. This repo's `build.sh` already implements
it — a missing VERDICT line becomes `HOLD - needs-assistance` [L1]. *(definitive on the quote; the
alignment is **derived**.)*

**P12. Human-facing prose in a two-region record is display-only by convention.** "Semantic conventions
MUST NOT define a value for body except to represent a string display message of the event." [S20];
SARIF's `message` description is written for truncated display [S6]. *(definitive on the quotes;
**derived** on the generalisation.)*

**P13. Typed comparable records are already a precondition for a mechanism this repo wants
independently.** `convergence_stopping.md` P11 establishes that convergence detection requires typed,
comparable finding records [I2]. That case does not depend on the routing argument at all.
*(**derived**, citing [I2] P11 — do not re-open it here.)*

**P14. This repo already has a structured read path and does not use it at the routing boundary.**
`activities/run-claude.sh` extracts the child's final result with
`jq -r 'select(.type == "result") | .result // ""'` and tests it against `COMPLETION_PATTERN` [L3],
while `build.sh` recovers the routing token with `grep -oE '^VERDICT: …'` over the whole tee'd stdout of
the child *script* [L1]. Two extraction paths, different reliability, same repo. *(definitive — read
directly from the shipped scripts.)*

**P15. A first-class typed exit channel from a Claude Code child is documented and available.**
`claude_code_integration_surface.md` §1 records that `--json-schema '<JSON Schema>'` with
`--output-format json` adds a **validated `structured_output` field**, that an invalid schema fails
non-zero, and that `format` is accepted as an annotation only; §7 covers the `stream-json` `result`
message fields [I3]. *(**inherited** from [I3] — cited, not re-derived here. [I3]'s header records
`Last validated: 2026-07-25`, `Critic: PASS`. It is a high-volatility surface; re-check it there, not
here.)*

---

## 5. The lifecycle mismatch — the part no upstream source answers

The phase doc's constraint: **the human record is durable and lifecycle-bound** (a PR closes at merge;
an issue closes when ruled; the standup tracker never closes and is pruned [L4]) **while the machine
channel must be readable by a parent process seconds after the child exits.**

No located source addresses this configuration (§7.1 N1). What the corpus does supply is the shape of
the four sub-problems and how each is handled where it *does* occur:

1. **Read latency.** In every located A-arrangement the typed record is written to a store the consumer
   can read immediately and independently: `finished.json` to job artifact storage at pod exit [S4], a
   condition to the object [S1], a SARIF file to an upload endpoint [S8]. None of them require the
   consumer to wait on, or read through, the human surface. *(derived.)*
2. **Durability.** Where the two channels have different lifetimes, the corpus's instance runs the
   *other* way — Events expire at 1 h, conditions persist [S1][S2]. So the corpus offers **no
   precedent** for "typed channel more ephemeral than human channel," which is what an exit-time-only
   machine record would be. *(derived.)*
3. **Which one closes the loop.** Kubernetes' answer is that *neither* closes it: a condition is current
   state, an Event is history [S1]. This repo's Kind 1 uses **open/closed as the to-do bit** [L4], which
   is a state machine the typed channel would have to either mirror or defer to. Nothing upstream tells
   you which. *(derived; genuinely open — see §8 T3.)*
4. **Reconciling one authoring act with two retention policies.** The corpus's answer wherever it comes
   up is *derive, don't re-author*: Open Test Reporting converts the streaming form into the archival
   form mechanically [S23]; crier projects `finished.json` onto the PR [S4][S5]. Nothing is written
   twice. *(derived.)*

**The derived resolution.** The mismatch is a *storage* mismatch, not a *content* mismatch, and it
dissolves under arrangement A: write the typed record once, at exit, to a channel the parent owns
(fast, transient, sufficient for routing); then **archive that same typed record into the durable human
surface** as part of producing the human record from it. The typed record then has two copies with two
lifetimes and one author, and the durable copy is a by-product rather than a second authoring act. This
is what Prow does — the typed artifact lives in job storage while its projection lives on the PR
[S4][S5] — and it is what this repo *almost* does today, since the `pr_review:` block is already posted
to the durable surface [L2]; the missing half is that nothing typed reaches the parent at exit. *(fully
derived; no source states this, and §8 lists what would falsify it.)*

---

## 6. Recommendations, stated against the two shipped surfaces

Each is derived; each names the evidence it rests on and what would change it.

**R1 — Move the routing token off the prose channel and onto a typed exit channel. (P2, P6, P14, P15.)**
`build.sh`'s `grep -oE '^VERDICT: …'` over the child's whole stdout [L1] is arrangement B with no
write-time gate — the configuration the corpus never ships (P7). The minimum change that leaves it
arrangement A is: `review-pr.sh` writes a small JSON object to a path the parent passes in (or the run
uses `--output-format json --json-schema` and the parent reads `structured_output` [I3]), and the parent
branches on that. *Cost:* the child must know a file path or the run must change output format. *What
would change this:* if `structured_output` proves unavailable in the child's invocation shape, the
file-path variant carries the same properties with no dependency on a high-volatility surface.

**R2 — Keep what the parent reads TINY, and version it. (P3, P5, P10.)** SLSA's verifier reads four
things [S12]; Tekton retreated from a rich handoff object [I1 §2.4.2]. The parent's contract should be
an envelope of roughly `{schema_version, verdict, hold_kind, pass, pr}` — and *not* the findings array.
The rich `pr_review:` payload stays a payload the parent never branches on. Write the parent's subset
down as its own contract (P3): every field the parent does not read is explicitly not load-bearing.

**R3 — Keep aggregation in the producer. (P4.)** This is already correct in `review-pr.sh` [L2] and
Kubernetes independently states the general rule [S1]. Do not let a future refactor move `hold_kind`
aggregation into the parent, and say so in the phase doc with the reason attached.

**R4 — Render the human disposition table from the typed record, or gate the co-authoring. (P8, P12,
arrangement C.)** Today the table and the yaml are two prose regions written in one authoring act [L2] —
arrangement C without a declared precedence rule, which is the one thing none of the C-instances in §3
permit. Two acceptable resolutions, in preference order: **(a)** the child emits the typed record first
and renders the table from it, so there is one source; **(b)** if co-authoring persists, add a
mechanical invariant — every table row has a matching finding `id` in the yaml and vice versa — checked
before the comment is posted. (b) is the Gerrit/Kubernetes pattern of a write-time gate (P7) applied to
this repo's shape. Whichever is chosen, **declare in the phase doc that the typed region wins**, because
no source lets the prose region carry semantics (P12).

**R5 — Archive the typed record into the durable surface as a by-product, not a second write. (§5.)**
The `pr_review:` block already lands on the PR [L2]; keep that, but make it a *copy of* the exit-channel
record rather than an independent composition. That preserves Kind 1 exactly as it stands — `/standup`
keeps parsing the same block [L2][L4] — while giving Kind 2 a channel with the right latency.

**R6 — Give absence a declared meaning and keep the fail-closed default. (P11.)** `build.sh` already
does this [L1] and Kubernetes documents the same discipline for conditions [S1]. Carry it into the typed
channel: a missing or unparseable typed record must map to `needs-assistance`, not to an optimistic
default.

**R7 — Do not put the machine channel in the git-notes / trailer family for this use case. (P6, §7.1
N4.)** Trailers and notes are arrangement-B metadata *about* a durable artifact, and the corpus never
uses them to route a process outcome (§3, second cross-cutting pattern). Notes additionally have a
transfer-semantics question this paper did **not** resolve (N4), which is a reason to avoid, not a
reason to assume.

---

## 7. Honest boundary analysis — where this thesis is weak or wrong

**7.0.1 The strongest case against Kind 2 existing at all: the incumbent works.** `build.sh`'s prose
grep is fail-closed [L1], the vocabulary is three closed tokens, and `review-pr.sh` prints the line as
its final output under a `COMPLETION_PATTERN` contract that already fails loud on absence [L2][L3]. No
evidence in this paper shows that arrangement producing a wrong route. `code_routed_control_flow.md`
§6.6 reaches an "ordinary as stated" verdict on the surrounding routing design [I1], and the same
skepticism applies here: **the case for a typed channel in this repo is currently a robustness and
measurement argument, not a demonstrated-defect argument.** A phase doc that claims the current
arrangement is broken is overclaiming. What the evidence supports is narrower: it is the one arrangement
the corpus never ships without a gate (P7), and it is the arrangement whose failure mode is silent (a
prose format change moves the token, and the fail-closed default converts that into a spurious
`needs-assistance` rather than an error).

**7.0.2 The measurement argument is stronger than the routing argument, and it is not this paper's.**
[I2] P11 already establishes that convergence detection needs typed comparable records [I2]. If the
phase doc wants the strongest justification for Kind 2, it is that one — and this paper's contribution
there is only P5/R2: keep the typed record layered so the routing envelope and the convergence payload
can evolve at different rates.

**7.0.3 Arrangement A has a real cost this paper should not hide.** In A, everything the human reads
must be expressible in the typed record. GitHub's subset behaviour [S8] is the general shape of the
loss: whatever the schema does not model, the render cannot show. A reviewing agent's prose currently
carries nuance (the `reframe:` / `bp:` working shown to the operator [L2]) that a schema would have to
model explicitly or lose. If the phase doc adopts A, it must enumerate the prose the human record needs
and confirm the schema carries it — or accept R4(b), the gated co-authoring, as the honest compromise.

**7.0.4 The "no located counterexample" claims are enumerations, not proofs.** P2, P7 and the second
cross-cutting pattern in §3 are generalisations over the instances this paper located. They are stated
as such deliberately. A single counterexample — a production system that routes a process outcome by
parsing an unvalidated human artifact — would not overturn the recommendations, but it would soften P7
from "always" to "usually," and the phase doc should not cite them as universals.

**7.0.5 The two sharpest analogues are both inverted relative to this repo's constraint.** Kubernetes'
human channel expires and its typed channel persists [S1][S2]; SLSA's typed channel is durable and
signed while human release notes are unbound. Neither has a *durable human record whose machine
counterpart is needed transiently*. §5's resolution is therefore an extrapolation, and it is marked
derived throughout.

**7.0.6 SARIF is a weaker analogue than the brief assumed.** It is not "one outcome, two renderings" —
it is one record with a typed field and a prose field (P1), i.e. arrangement **C**, not A. What makes
GitHub's use of it look like A is the *consumer* side: GitHub renders alerts and PR check results from
the uploaded file [S8]. The transferable lesson is the subset contract (P3) and the payload cap, not the
two-channel split. Saying so is a finding: the phase doc should not cite SARIF as precedent for
splitting a record in two.

**7.0.7 Conventional Commits is a poor analogue for this repo and should not be cited as one.** Its
whole model presupposes a mutable pre-merge artifact [S14] and a *derived, regenerable* output. This
repo's human record is a posted PR comment and a lifecycle-bound issue — neither is rebaseable, and the
derived artifact (a routing decision already acted on) is not regenerable after the fact. It is
excellent evidence for arrangement B's *failure mode* and poor evidence for adopting B.

**7.0.8 Where a phase doc should NOT introduce Kind 2 at all.** If a workflow's only machine need is
"did the child finish," the existing `COMPLETION_PATTERN` check over the `result` message [L3] already
answers it structurally, and a typed record adds a schema to maintain (P10: it becomes API surface the
moment anything branches on it) for no new capability. Kind 2 earns its cost only where a parent must
make a *multi-way* decision or where convergence must be *measured* across passes [I2].

### 7.1 Negative findings and their search method

**N1 — No source located addresses a durable human record paired with a transient machine-read
requirement.** Search method: targeted raw fetches of the Kubernetes API conventions [S1], kube-apiserver
flag reference [S2], SLSA `verifying-artifacts.md` and `attestation-model.md` [S10][S12], in-toto
`statement.md` [S9], CloudEvents `spec.md` [S13], OTel logs data model [S19] and semconv events/logs
[S20][S21], Prow `metadata-artifacts.md` and `life-of-a-prow-job.md` [S4][S5], each prompted explicitly
for lifecycle/retention/durability statements. The only retention statement located anywhere is the
Events TTL [S2], which runs the other way. **Stated as a gap, not filled by inference** — §5's
resolution is labelled derived.

**N2 — OpenTelemetry's comparative "what belongs in attributes vs. body" guidance was not located in the
two documents where it was expected.** Search method: raw fetches of
`opentelemetry-specification/specification/logs/data-model.md` [S19] and
`semantic-conventions/docs/general/logs.md` [S21], each prompted for placement guidance; [S21] returned
NOT FOUND for both placement and structured-vs-unstructured guidance. The guidance that *was* located
lives in `semantic-conventions/docs/general/events.md` [S20] and concerns flat-vs-complex **attributes**
plus the body-is-display-only rule — not a general placement rubric. Do not cite OTel for a general
"structured data goes in attributes, prose goes in body" rule on this paper's authority.

**N3 — No source located states a precedence rule between a signed attestation and human release
notes.** Search method: raw fetches of SLSA `provenance.md`, `attestation-model.md`,
`verifying-artifacts.md` [S10][S11][S12] and in-toto `statement.md` [S9], prompted for consumer/verifier
behaviour and for limits. The verification procedure [S12] never mentions human-authored release
documentation. The two are treated as unrelated artifacts; "which wins" is not a question the specs pose.

**N4 — Whether git notes are transferred on fetch/push by default was NOT FOUND.** Search method: raw
fetch of `git/git` `Documentation/git-notes.adoc` on the confirmed default branch `master`, prompted
explicitly for transfer/fetch behaviour; the fetch returned NOT FOUND for that item while returning the
other requested spans. Not asserted in either direction. This is a live consideration for anyone
proposing notes as a machine channel (R7).

**N5 — No counterexample to P7 was found, but the search was bounded.** Search method: the human→machine
instances examined were git trailers [S15], kernel tags [S18], Gerrit Change-Id [S17], Kubernetes
release-note blocks [S3], and Conventional Commits [S14]. No systematic survey of other
comment-command systems (e.g. other bots' slash-command grammars) was performed. P7 is a
generalisation over five located instances, and it is stated that way.

**N6 — GitHub Checks API `conclusion` values and annotation semantics were NOT obtained from a raw
first-party source, and are therefore not asserted anywhere in this paper.** Search method: raw fetch of
`github/docs` `content/rest/checks/runs.md` on the confirmed default branch `main` [S26], which returned
frontmatter only — the prose is generated from `github/rest-api-description` OpenAPI, which was not
fetched (a single summarizing fetch of a multi-megabyte description would not have supported verbatim
quotation). Nothing in §3–§6 depends on the Checks API.

**N7 — The Argo Workflows "keep useful logs, export only specific JSON" distinction named in the
research brief was not corroborated at the location checked.** Search method: raw fetch of
`argoproj/argo-workflows` `docs/variables.md` [S25] on default branch `main`, confirmed as
`"default_branch": "main"` via the repos API before the fetch. **The fetch layer's own enumeration of
this file proved unstable** — three enumeration prompts against the same raw URL returned three
different lists, and one of them reported as a verbatim matching line a sentence that does not contain
the search string at all. The population was therefore established a different way: the document was
reproduced **verbatim in four contiguous chunks covering it end to end** (start → `### Simple`;
`### Expression` → end of its `#### Examples`; `## Reference` → the line before
`### Container/Script Templates`; `### Container/Script Templates` → last line), and the occurrences
were counted from that reproduction rather than from any layer-reported total.

Enumerating the literal string `outputs.result` across the full reproduction gives **five** occurrences:

1. *Template Tag Kinds → Expression*, inline example — "…`inputs.parameters['my-param']` or
   `steps['my-step'].outputs.result`."
2. *Reference → Steps Templates*, table row — `` | `steps.<STEPNAME>.outputs.result` | Output result of any previous container, script, or HTTP step | ``
3. *Reference → DAG Templates*, table row — `` | `tasks.<TASKNAME>.outputs.result` | Output result of any previous container, script, or HTTP task | ``
4. *Reference → Outputs of Skipped and Omitted Nodes*, prose — "References to its declared output
   parameters and `outputs.result` resolve as follows:"
5. *Metrics*, table row — `` | `outputs.result` | Output result of the metric-emitting template | ``

So **three** are table rows, not four; the other two are an inline expression example and a prose
sentence. **Neither non-table-row occurrence bears on the size-limit / stdout question this finding is
about.** (1) is syntax guidance for hyphenated names and map indexing. (4) heads an
**absence-semantics** rule, gated "> v3.7.16, v4.0.7, and after", whose substance is that a skipped or
omitted node's outputs resolve to a declared `valueFrom.default` or else are *absent*: "Otherwise the
output is *absent*, which is not the same as an empty string." That is relevant **in kind** to P11
(absence must be given a declared meaning) and says nothing about payload size or stdout capture.

Across the full verbatim reproduction there is **no size limit, no byte limit, no truncation statement
and no stdout warning anywhere in the document** — this is now a NOT FOUND read off the complete text,
not off a summarizing layer's negative answer. A follow-up raw fetch of `docs/script-templates.md`
returned HTTP 404 at that path (re-confirmed on this pass, on the same confirmed default branch). Argo's
*size* caps are separately documented and already recorded upstream in `code_routed_control_flow.md`
§2.4.1 [I1] — cite that, not this paper, for Argo.

---

## 8. Test plan — what research cannot settle

**T1 — Does `claude -p --output-format json --json-schema` actually deliver a validated
`structured_output` in this repo's child-invocation shape?** [I3] documents the flag; nothing here
verifies it under `--dangerously-skip-permissions`, inside a worktree, at `review-pr`'s turn budget.
*Experiment:* run `children/review-pr.sh` once with the flag on a known PR and diff the emitted object
against the schema. *Decides:* R1's mechanism (structured_output vs. a parent-supplied file path).

**T2 — Does the typed record survive a turn-cap death?** A run killed at its cap leaves no comment and
possibly no final result [L1][L3]. *Experiment:* force `--max-turns` low and observe whether any typed
artifact exists. *Decides:* whether R6's fail-closed default is the only absence path, or whether a
partial typed record can appear (which would be worse than none).

**T3 — Which channel owns the to-do bit?** Kind 1 uses open/closed [L4]; a typed record would carry a
verdict. *Experiment:* enumerate the last N `pr_review:` blocks against their PRs' open/closed state and
count disagreements. *Decides:* §5 sub-problem 3, on which no source speaks.

**T4 — Can the human disposition table be rendered from the typed record without losing what the
operator uses?** *Experiment:* take three recent disposition comments, attempt to reconstruct each table
from its own `pr_review:` block alone, and have the operator mark what went missing. *Decides:* R4(a)
vs. R4(b) — this is the boundary in §7.0.3 and it is an empirical question, not a research one.

**T5 — How often does the current prose grep actually miss?** *Experiment:* replay archived
`.claude/logs/` JSONL through the `grep -oE` predicate and count runs where the fail-closed default
fired despite a real verdict being present in the log. *Decides:* whether §7.0.1's "no demonstrated
defect" still holds, and therefore how strongly the phase doc may state the case for Kind 2.

**T6 — What is the smallest envelope that routes every parent this repo has or plans?** R2 proposes
roughly five fields from one caller. *Experiment:* enumerate the branch points in `build.sh` and every
planned parent, and take the union of the values they need. *Decides:* R2's concrete schema, and guards
against P10 (a field that becomes API surface the moment something branches on it).

---

## 9. Citations

### 9.1 Sourcing note

Every quoted span in this paper was returned by a fetch of a **raw or structured** form — 
`raw.githubusercontent.com` `.md` / `.adoc` / `.rst` / `.txt`, a spec JSON schema, or a
`api.github.com` JSON response. **No rendered HTML page is quoted anywhere in this paper**, and no claim
rests on one. Where a fetch returned prose rather than the exact spans requested, the material is
presented as description, not quotation, or recorded as a gap in §7.1. Directory listings used to locate
files were obtained by asking the GitHub contents API to **enumerate** entries; those listings are
discovery methodology and no claim rests on them (S7 is the one such listing in the citation table, and
it is marked as such).

**Every count this paper asserts was reached by enumerating the population and counting the
enumeration** — never by asking a retrieval layer for a total:

- SARIF's **four** `level` values (§2.1) — from the enum members in the raw JSON schema [S6].
- **Five** occurrences of `outputs.result` in Argo's `variables.md` (§7.1 N7) — the fetch layer's own
  enumerations disagreed across three attempts, so the count was taken from a verbatim end-to-end
  reproduction of the document instead; the instability and the four reproduction chunks are recorded
  in N7.
- **26** external sources (§9.2) — from the rows of the citation table.
- **Five** human→machine instances underwriting P7 (§7.1 N5) — from the enumerated instance list.
- **Seven** negative findings in §7.1 (header `Confidence:`) — from the enumerated N-markers N1–N7.

### 9.2 External sources

| id | Source | Form fetched |
|---|---|---|
| S1 | Kubernetes API Conventions, `kubernetes/community` `contributors/devel/sig-architecture/api-conventions.md` — https://raw.githubusercontent.com/kubernetes/community/main/contributors/devel/sig-architecture/api-conventions.md (default branch `main`, confirmed via contents API) | raw md |
| S2 | `kube-apiserver` command-line reference, `kubernetes/website` — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/reference/command-line-tools-reference/kube-apiserver.md | raw md |
| S3 | Kubernetes contributor guide, release notes — https://raw.githubusercontent.com/kubernetes/community/main/contributors/guide/release-notes.md | raw md |
| S4 | Prow, "Metadata Artifacts" — https://raw.githubusercontent.com/kubernetes-sigs/prow/main/site/content/en/docs/metadata-artifacts.md | raw md |
| S5 | Prow, "Life of a Prow Job" — https://raw.githubusercontent.com/kubernetes-sigs/prow/main/site/content/en/docs/life-of-a-prow-job.md | raw md |
| S6 | OASIS SARIF 2.1.0 JSON schema — https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/prose/sarif-schema-2.1.0.json | raw JSON |
| S7 | **Discovery methodology only — no claim in this paper is sourced to S7, and it is deliberately not cited inline.** OASIS `sarif-spec` repository contents, used to locate S6's path — https://api.github.com/repos/oasis-tcs/sarif-spec/contents/ and `/sarif-2.1`, `/sarif-2.1/prose` | GitHub contents API |
| S8 | GitHub Docs, "SARIF support for code scanning" — https://raw.githubusercontent.com/github/docs/main/content/code-security/reference/code-scanning/sarif-files/sarif-support.md | raw md |
| S9 | in-toto Attestation Framework, Statement layer v1 — https://raw.githubusercontent.com/in-toto/attestation/main/spec/v1/statement.md | raw md |
| S10 | SLSA, "Attestation model" — https://raw.githubusercontent.com/slsa-framework/slsa/main/spec/attestation-model.md | raw md |
| S11 | SLSA, "Provenance" — https://raw.githubusercontent.com/slsa-framework/slsa/main/spec/provenance.md | raw md |
| S12 | SLSA, "Verifying artifacts" — https://raw.githubusercontent.com/slsa-framework/slsa/main/spec/verifying-artifacts.md | raw md |
| S13 | CloudEvents specification — https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md | raw md |
| S14 | Conventional Commits v1.0.0 — https://raw.githubusercontent.com/conventional-commits/conventionalcommits.org/master/content/v1.0.0/index.md (default branch `master`, confirmed via repos API) | raw md |
| S15 | `git-interpret-trailers(1)` — https://raw.githubusercontent.com/git/git/master/Documentation/git-interpret-trailers.adoc | raw adoc |
| S16 | `git-notes(1)` — https://raw.githubusercontent.com/git/git/master/Documentation/git-notes.adoc | raw adoc |
| S17 | Gerrit Code Review, "Change-Id Lines" — https://raw.githubusercontent.com/GerritCodeReview/gerrit/master/Documentation/user-changeid.txt | raw txt |
| S18 | Linux kernel, "Submitting patches" — https://raw.githubusercontent.com/torvalds/linux/master/Documentation/process/submitting-patches.rst | raw rst |
| S19 | OpenTelemetry specification, Logs Data Model — https://raw.githubusercontent.com/open-telemetry/opentelemetry-specification/main/specification/logs/data-model.md | raw md |
| S20 | OpenTelemetry semantic conventions, general events — https://raw.githubusercontent.com/open-telemetry/semantic-conventions/main/docs/general/events.md | raw md |
| S21 | OpenTelemetry semantic conventions, general logs (negative finding N2) — https://raw.githubusercontent.com/open-telemetry/semantic-conventions/main/docs/general/logs.md | raw md |
| S22 | CTRF — https://api.github.com/repos/ctrf-io/ctrf (description) and https://raw.githubusercontent.com/ctrf-io/ctrf/main/README.md | GitHub API JSON + raw md |
| S23 | Open Test Reporting (JUnit team) — https://raw.githubusercontent.com/ota4j-team/open-test-reporting/main/README.adoc (root enumerated via contents API to confirm `README.adoc`, not `README.md`) | raw adoc |
| S24 | junit-team issue #2625, "Define an offical XSD for JUnit XML test reports" — https://api.github.com/repos/junit-team/junit-framework/issues/2625 | GitHub API JSON |
| S25 | Argo Workflows, "Workflow Variables" (negative finding N7) — https://raw.githubusercontent.com/argoproj/argo-workflows/main/docs/variables.md | raw md |
| S26 | GitHub Docs, REST checks/runs (negative finding N6) — https://raw.githubusercontent.com/github/docs/main/content/rest/checks/runs.md | raw md |

Counting the enumerated rows above: **26 external sources** (S1–S26).

### 9.3 Internal evidence cited, not re-derived

| id | Artifact | Header state as recorded in that file |
|---|---|---|
| I1 | `docs/standards/architecture/research/raw/code_routed_control_flow.md` — §2.4.1 payload caps, §2.4.2 Tekton TEP-0074 withdrawal, P4, P5, P12, P13, §6.6 | `Last validated: 2026-08-03`, `Critic: PASS-WITH-FIXES` (round 3) |
| I2 | `docs/standards/architecture/research/raw/convergence_stopping.md` — P11 (convergence needs typed comparable records) | `Last validated: 2026-08-03`, `Critic: PASS` |
| I3 | `docs/standards/architecture/research/raw/claude_code_integration_surface.md` — §1 `--json-schema` / `structured_output`, §7 `stream-json` `result` fields | `Last validated: 2026-07-25`, `Critic: PASS` |

*(Header states are quoted as supplied in this paper's dispatch and as read from those files; this paper
asserts no currency verdict about them beyond what their own headers say.)*

### 9.4 Local surfaces read directly

| id | Path | What was read |
|---|---|---|
| L1 | `scripts/workflows/build.sh` (~L259–L363) | `run_pr_review()` — `grep -oE '^VERDICT: (MERGE\|HOLD - (redispatch\|needs-assistance))$'` over the tee'd child log, the fail-closed default to `HOLD - needs-assistance`, and the `case` that routes on `VERDICT_LINE` |
| L2 | `scripts/workflows/children/review-pr.sh` (~L186, L300–L441) | `COMPLETION_PATTERN`; Stage 5's two-part comment (human disposition table + fenced `pr_review:` yaml); Stage 6's verdict rule and the "aggregate it yourself" instruction |
| L3 | `scripts/workflows/activities/run-claude.sh` (~L130–L220) | `--output-format stream-json`; `jq -r 'select(.type == "result") \| .result // ""'` completion-contract check; turn-cap detection |
| L4 | `docs/guide/operations.md` § *The memory model* | The three Kind 1 surfaces, their lifecycles, and "open IS the to-do bit" |
